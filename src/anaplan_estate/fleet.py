"""An estate of Anaplan models from two exports per model: the Line Items
grid and the Actions grid. Everything here is deterministic and runs
offline; the output is a Markdown report and a JSON bundle that an
architect (human or model) reads.

Per model:
  inventory     modules, line items, cells, dimensions, parse rate
  effort        the line items and modules that carry the calculation time
                (Anaplan's own Calculation Effort column, when exported)
  graph         hubs, unreferenced calculations, cycles, pass-through chains,
                and a check of our edges against Anaplan's Referenced By column
  actions       imports by target, exports, processes, orphans, stale, slow,
                external sources
  patterns      rule findings grouped into the design decisions behind them

Across models:
  edges         which model feeds which, inferred from import action names
                ("Import from FP&A Model - Departments"); always labelled inferred
  duplicates    the same line item name with the same formula tree in more
                than one model
  shared_dims   dimension names used in more than one model
"""
from __future__ import annotations
import re, datetime
from dataclasses import dataclass, field
from collections import Counter, defaultdict
from pathlib import Path
from anaplan_grammar.parser import parse
from anaplan_grammar.unparse import unparse
from .model import Model, load_model, COLUMN_ROLES
from .graph import Graph, build_graph
from .lint import lint, LintResult, RULES
from .cluster import cluster, Cluster
from .estate import Estate, load_actions, _split
from . import redundancy as redund
from . import findings as findlist

_FROM = re.compile(r"\bfrom\s+(.+?)(?:\s+(?:into|to)\b|\s+-\s|$)", re.I)
_DIRNUM = re.compile(r"^\d+\s+")
NEEDS_MODULES = ("A-SUBSIDIARY", "H-NOTES")   # rules that return nothing without the Modules export
_DIRTAIL = re.compile(r"\s+(Model\s+)?Documentation$|\s+Model$", re.I)


@dataclass
class ModelRun:
    name: str
    folder: str
    model: Model
    graph: Graph
    lint: LintResult
    clusters: list[Cluster]
    actions: Estate
    facts: dict
    redundancy: redund.Redundancy = field(default_factory=redund.Redundancy)


@dataclass
class EstateRun:
    models: list[ModelRun]
    edges: list[dict]              # inferred model-to-model import edges
    external: dict[str, list[str]] # source phrase -> [model.action]
    duplicates: list[dict]
    shared_dims: list[tuple[str, list[str]]]
    generated: str = field(default_factory=lambda: datetime.date.today().isoformat())
    actions: list = field(default_factory=list)
    findings: list = field(default_factory=list)

    def to_dict(self):
        return {"generated": self.generated,
                "findings": [a.to_dict() for a in self.findings],
                "models": [{"name": m.name, "folder": m.folder, "facts": m.facts, "redundancy": m.redundancy.to_dict(),
                            "patterns": [c.to_dict() for c in m.clusters],
                            "findings_by_rule": m.lint.counts["by_rule"]} for m in self.models],
                "edges": self.edges, "external_sources": self.external,
                "duplicates": self.duplicates, "shared_dimensions": self.shared_dims}


# ---------- discovery ----------

def clean_name(dirname: str) -> str:
    n = _DIRNUM.sub("", dirname)
    return _DIRTAIL.sub("", n).strip() or dirname


def discover(root: str | Path) -> list[dict]:
    """Each model is a folder holding a 'Line Items*.csv' somewhere beneath it
    (Anaplan's export name) and optionally 'Actions*.csv' and 'Modules*.csv'.
    The root itself counts as one model if it holds the file directly."""
    root = Path(root)

    def spec(d: Path):
        li = sorted(d.glob("**/Line Items*.csv"))
        if not li:
            return None
        acts = sorted(d.glob("**/Actions*.csv")); mods = sorted(d.glob("**/Modules*.csv"))
        return {"name": clean_name(d.name), "folder": str(d), "line_items": str(li[0]),
                "actions": str(acts[0]) if acts else None, "modules": str(mods[0]) if mods else None}

    found = [s for s in (spec(d) for d in sorted(p for p in root.iterdir() if p.is_dir())) if s]
    if not found:
        s = spec(root)
        found = [s] if s else []
    return found


# ---------- per model ----------

def _ref_check(m: Model, g: Graph) -> dict:
    """Dependency completeness, checked against Anaplan's own Referenced By column.

    For every line item with at least one edge on either side: Anaplan's set = the
    line items its Referenced By column names; ours = the line items whose parsed
    formula references it (g.rev). agreement = |both| / |either|, i.e. edges present
    in both over edges present in at least one. Not the same as parse rate: a formula
    can parse and still miss an edge the platform knows about.

    Anaplan-only edges are classified by the referencing formula:
      collect    the referencing line item uses COLLECT(): the platform records the
                 line item subset relationship, which the export does not describe
      unparsed   the referencing formula did not parse
      other      unexplained; listed for investigation
    Ours-only edges are references the platform did not list (usually a name that
    resolves to a line item here but is a list or property in the model)."""
    agree = ours_only = theirs_only = 0
    why = Counter(); examples = {"collect": [], "unparsed": [], "other": [], "ours_only": []}
    if not m.has("Referenced By"):
        return {"agree": 0, "ours_only": 0, "anaplan_only": 0, "agreement": None,
                "definition": "Referenced By column absent from the export: not checkable", "anaplan_only_by_cause": {}, "examples": examples}
    for k, li in m.line_items.items():
        if li.is_header:
            continue
        theirs = set()
        for ref in _split(li.referenced_by_raw):
            if "." in ref:
                mod, _, name = ref.partition(".")
                theirs.add((mod.strip("'"), name.strip("'")))
            else:
                r = ref.strip("'")
                if (li.module, r) in m.line_items:
                    theirs.add((li.module, r))
        ours = set(g.rev.get(k, ()))
        if not theirs and not ours:
            continue
        agree += len(theirs & ours); ours_only += len(ours - theirs); theirs_only += len(theirs - ours)
        for t in theirs - ours:
            src = m.line_items.get(t)
            cls = "collect" if src and "COLLECT" in src.formula.upper() else "unparsed" if t in g.parse_errors else "other"
            why[cls] += 1
            if len(examples[cls]) < 12:
                examples[cls].append(f"{t[0]}.{t[1]} -> {k[0]}.{k[1]}")
        for t in ours - theirs:
            if len(examples["ours_only"]) < 12:
                examples["ours_only"].append(f"{t[0]}.{t[1]} -> {k[0]}.{k[1]}")
    tot = agree + ours_only + theirs_only
    return {"agree": agree, "ours_only": ours_only, "anaplan_only": theirs_only,
            "agreement": round(agree / tot, 3) if tot else None,
            "definition": "edges present in both the parsed graph and Anaplan's Referenced By, over edges present in either",
            "anaplan_only_by_cause": dict(why), "examples": examples}


GENERIC_SOURCE_WORDS = {"hierarchy", "import", "export", "list", "module", "data", "file", "csv", "model", "the", "all", "new", "old", "current", "prior"}


def _actions_facts(e: Estate, stale_months: int) -> dict:
    """Facts from the Actions export. The export carries each action's most recent run
    ('Start Date and Time'), whatever triggered it (process, page, Actions pane or API).
    The latest run date in the file is the closest thing to a snapshot date the export
    gives. 'No recorded run since <cutoff>' is relative to that snapshot; it is not
    proof of non-use (expected frequency and the snapshot age matter). An action outside
    every process can still be run from a page, the Actions pane or the API."""
    acts = list(e.actions.values())
    dated = [a for a in acts if a.last_run]
    latest = max((a.last_run for a in dated), default="")
    cutoff = ""
    if latest:
        try:
            d = datetime.datetime.strptime(latest[:10], "%Y-%m-%d")
            cutoff = (d - datetime.timedelta(days=30 * stale_months)).strftime("%Y-%m-%d")
        except ValueError:
            pass
    in_proc = {s for p in e.processes.values() for s in p.steps}
    imports = [a for a in acts if a.kind == "import"]
    exports = [a for a in acts if a.kind == "export"]
    by_target = Counter(a.target for a in imports if a.target)
    not_in_process = [a.name for a in imports + exports if a.name not in in_proc and not a.processes]
    never_recorded = [a.name for a in imports + exports if not a.last_run]
    no_recent_run = [(a.name, a.last_run[:10]) for a in imports + exports if a.last_run and cutoff and a.last_run[:10] < cutoff]
    slow = sorted(((a.name, a.duration_ms) for a in acts if a.duration_ms), key=lambda x: -x[1])[:10]
    sources = defaultdict(list)
    for a in imports:
        mm = _FROM.search(a.name)
        if mm:
            phrase = mm.group(1).strip()
            if phrase.lower() in GENERIC_SOURCE_WORDS or len(phrase) < 3:
                continue
            sources[phrase].append(a.name)
    return {"actions": len(acts), "imports": len(imports), "exports": len(exports), "processes": len(e.processes),
            "latest_run": latest[:10], "snapshot": latest[:10], "stale_cutoff": cutoff, "stale_months": stale_months,
            "imports_by_target": by_target.most_common(),
            "import_targets": sorted({a.target for a in imports if a.target}), "export_sources": sorted({a.target for a in exports if a.target}),
            "process_steps": sorted(((p.name, len(p.steps)) for p in e.processes.values()), key=lambda x: -x[1]),
            "not_in_process": not_in_process, "not_in_process_count": len(not_in_process),
            "never_recorded": never_recorded, "no_recent_run": no_recent_run, "no_recent_run_count": len(no_recent_run) + len(never_recorded),
            # kept for readers of the old keys
            "orphans": not_in_process, "orphan_count": len(not_in_process),
            "stale": no_recent_run + [(n, "no recorded run") for n in never_recorded], "stale_count": len(no_recent_run) + len(never_recorded),
            "slow": slow, "sources": {k: v for k, v in sources.items()}}


def analyse(spec: dict, stale_months: int = 12, overrides: dict | None = None) -> ModelRun:
    m = load_model(spec["line_items"], spec.get("modules"), name=spec["name"])
    g = build_graph(m)
    lr = lint(m, g, overrides=overrides)
    cl = cluster(lr.findings)
    e = Estate()
    if spec.get("actions"):
        load_actions(spec["actions"], e)
    lis = [li for li in m.line_items.values() if not li.is_header]
    st = g.stats()
    total_cells = sum(li.cell_count for li in lis)
    by_mod_cells = Counter(); by_mod_eff = Counter()
    for li in lis:
        by_mod_cells[li.module] += li.cell_count; by_mod_eff[li.module] += li.calc_effort
    eff = sorted(lis, key=lambda li: -li.calc_effort)
    has_effort = any(li.calc_effort for li in lis)
    top10_share = round(sum(li.calc_effort for li in eff[:10]), 1) if has_effort else None
    cyc = g.cycles()
    cyc_sev = Counter(f.severity for f in lr.findings if f.rule == "G-CYCLE")
    facts = {
        "modules": len([n for n, mod in m.modules.items() if mod.line_items]),
        "line_items": len(lis), "calculated": st["with_formula"], "inputs": len(lis) - st["with_formula"],
        "cells": total_cells, "dimensions": sorted(m.dimensions), "edges": st["edges"], "module_edges": st["module_edges"],
        "parse_errors": st["parse_errors"], "parse_rate": round(1 - st["parse_errors"] / max(st["with_formula"], 1), 4),
        "notes_coverage": round(sum(1 for li in lis if li.notes.strip()) / max(len(lis), 1), 3),
        "has_effort": has_effort, "effort_top10_share": top10_share, "has_cells": m.has("Cell Count"),
        "warnings": list(m.warnings) + [w for w in getattr(e, "warnings", [])],
        "missing_columns": [f"{c}: {COLUMN_ROLES[c]}" for c in m.missing_columns if c != "Module Name"],
        "effort_top": [(str(li), li.calc_effort, li.cell_count, li.formula[:120]) for li in eff[:20] if li.calc_effort],
        "effort_by_module": [(n, round(v, 2)) for n, v in by_mod_eff.most_common(10) if v],
        "cells_by_module": [(n, c, round(100 * c / total_cells, 1) if total_cells else 0) for n, c in by_mod_cells.most_common(10)],
        "hubs": [(f"{k[0]}.{k[1]}", n) for k, n in g.hubs(10)],
        "unreferenced": len(g.unused()), "cycles": len(cyc),
        "cycles_balance": cyc_sev.get("info", 0), "cycles_fault": cyc_sev.get("critical", 0),
        "daisy_chains": len(g.daisy_chains()),
        "referenced_by_check": _ref_check(m, g),
        "findings": len(lr.findings), "patterns": len(cl),
        "rules_skipped": [r for r in RULES if r not in lr.rules_run or (r in NEEDS_MODULES and not m.has_modules_export)],
        "has_modules_export": m.has_modules_export,
        "actions": _actions_facts(e, stale_months) if spec.get("actions") else None,
    }
    red = redund.analyse(m, g, export_sources={a.target for a in e.actions.values() if a.kind == "export"},
                         import_targets={a.target for a in e.actions.values() if a.kind == "import"})
    facts["redundancy"] = red.counts()
    facts["coverage"] = _coverage(spec, m, g, lr, facts)
    return ModelRun(spec["name"], spec["folder"], m, g, lr, cl, e, facts, red)


def _coverage(spec: dict, m: Model, g: Graph, lr: LintResult, facts: dict) -> dict:
    """What was supplied, what ran, what was skipped and why, what is confirmed vs inferred, what is missing."""
    files = {"line_items": Path(spec["line_items"]).name, "modules": Path(spec["modules"]).name if spec.get("modules") else None,
             "actions": Path(spec["actions"]).name if spec.get("actions") else None}
    skipped = []
    if not m.has_modules_export:
        skipped += [(r, "needs the Modules export (module-level Applies To and Notes)") for r in NEEDS_MODULES]
    if not spec.get("actions"):
        skipped.append(("actions", "no Actions export: imports, exports, processes, run dates and model-to-model feeds not analysed"))
    if not facts["has_effort"]:
        skipped.append(("effort", "Calculation Effort column absent or blank: no effort figures for this model"))
    if not facts["has_cells"]:
        skipped.append(("cells", "Cell Count column absent: cell footprints unavailable for this model (not zero)"))
    if not m.has("Referenced By"):
        skipped.append(("referenced-by", "Referenced By column absent: dependency completeness not checkable"))
    run = [r for r in lr.rules_run if r not in {x for x, _ in skipped}]
    confirmed = ["formula references (parsed from Formula)", "Referenced By (Anaplan's column, used as the check)"]
    if m.has_modules_export:
        confirmed.append("module dimensions and notes (Modules export)")
    if spec.get("actions"):
        confirmed += ["import target modules and export source modules (Action column)", "process membership and most recent run per action"]
    inferred = ["model-to-model feeds, from the words after 'from' in import action names", "external source names, from the same words"] if spec.get("actions") else []
    missing = ["pages, dashboards and saved views (no export exists)", "line item subset membership (COLLECT sources)", "filters, access drivers and DCA usage",
               "CloudWorks, API and integration schedules", "engine (Classic or Polaris): not in any export", "cell counts of summary levels (as exported)",
               "the date the Line Items and Modules exports were taken (not in the file)"]
    return {"files": files, "snapshot_actions": (facts.get("actions") or {}).get("snapshot", ""), "rules_run": run, "rules_skipped": skipped,
            "warnings": facts["warnings"], "missing_columns": facts["missing_columns"],
            "confirmed": confirmed, "inferred": inferred, "missing": missing,
            "parse_rate": facts["parse_rate"], "referenced_by_agreement": facts["referenced_by_check"]["agreement"],
            "unresolved_context": facts["redundancy"]["unresolved_context"]}


# ---------- across models ----------

def _match_model(phrase: str, names: list[str], aliases: dict[str, str]) -> str | None:
    p = phrase.lower()
    for alias, target in aliases.items():
        if alias.lower() in p:
            return target
    best = None
    for n in names:
        toks = [t for t in re.split(r"\W+", n.lower()) if len(t) > 1]
        if n.lower() in p or (toks and all(t in p for t in toks)):
            best = n if best is None or len(n) > len(best) else best
    return best


def cross(models: list[ModelRun], aliases: dict[str, str]) -> tuple[list[dict], dict]:
    names = [m.name for m in models]
    edges: dict[tuple[str, str], dict] = {}
    external: dict[str, list[str]] = defaultdict(list)
    for m in models:
        if not m.facts.get("actions"):
            continue
        for phrase, acts in m.facts["actions"]["sources"].items():
            src = _match_model(phrase, names, aliases)
            if src and src != m.name:
                e = edges.setdefault((src, m.name), {"from": src, "to": m.name, "actions": 0, "targets": [], "phrases": set()})
                e["actions"] += len(acts); e["phrases"].add(phrase)
                for a in acts:
                    t = m.actions.actions[a].target
                    if t and t not in e["targets"]:
                        e["targets"].append(t)
            else:
                external[phrase].extend(f"{m.name}: {a}" for a in acts)
    out = []
    for e in edges.values():
        e["phrases"] = sorted(e["phrases"]); e["targets"] = e["targets"]; e["basis"] = "inferred from import action names"; e["confirmed"] = False
        out.append(e)
    out.sort(key=lambda e: -e["actions"])
    return out, dict(external)


def duplicates(models: list[ModelRun], min_len: int = 25) -> list[dict]:
    seen: dict[tuple[str, str], list[str]] = defaultdict(list)
    for m in models:
        for li in m.model.line_items.values():
            if li.is_header or len(li.formula) < min_len:
                continue
            try:
                norm = unparse(parse(li.formula))
            except Exception:
                continue
            seen[(li.name, norm)].append(f"{m.name}: {li.module}")
    out = []
    for (name, norm), where in seen.items():
        mods = {w.split(":")[0] for w in where}
        if len(mods) > 1:
            out.append({"line_item": name, "models": sorted(mods), "copies": len(where), "where": where[:8], "formula": norm[:160]})
    out.sort(key=lambda d: (-len(d["models"]), -d["copies"], d["line_item"]))
    return out[:60]


def shared_dimensions(models: list[ModelRun]) -> list[tuple[str, list[str]]]:
    where = defaultdict(list)
    for m in models:
        for d in m.model.dimensions:
            if d not in ("Time", "Versions") and not d.startswith("Time."):
                where[d].append(m.name)
    return sorted(((d, ms) for d, ms in where.items() if len(ms) > 1), key=lambda x: (-len(x[1]), x[0]))


def run(root: str | Path, aliases: dict[str, str] | None = None, stale_months: int = 12, overrides: dict | None = None,
        names: dict[str, str] | None = None, skip: list[str] | None = None) -> EstateRun:
    specs = discover(root)
    if not specs:
        raise SystemExit(f"no 'Line Items*.csv' found under {root}")
    specs = [s for s in specs if s["name"] not in (skip or []) and Path(s["folder"]).name not in (skip or [])]
    for s in specs:
        if names and s["name"] in names:
            s["name"] = names[s["name"]]
    models = [analyse(s, stale_months, overrides) for s in specs]
    edges, external = cross(models, aliases or {})
    er = EstateRun(models, edges, external, duplicates(models), shared_dimensions(models))
    er.findings = findlist.build(er)
    er.actions = er.findings
    return er


# ---------- rendering ----------

def render_markdown(er: EstateRun, max_patterns: int = 0) -> str:
    from . import report
    return report.render_markdown(er)
