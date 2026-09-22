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
from .model import Model, load_model
from .graph import Graph, build_graph
from .lint import lint, LintResult, RULES
from .cluster import cluster, Cluster
from .estate import Estate, load_actions, _split
from . import redundancy as redund
from . import actions as actionlist

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

    def to_dict(self):
        return {"generated": self.generated,
                "actions": [a.to_dict() for a in self.actions],
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
    """Our edges vs Anaplan's Referenced By column. Anaplan's column is the
    reverse index (who uses me); ours is g.rev. Counts agree / ours-only /
    anaplan-only, over line items that have either."""
    agree = ours_only = theirs_only = 0
    for k, li in m.line_items.items():
        if li.is_header:
            continue
        theirs = set()
        for ref in _split(li.referenced_by_raw):
            if "." in ref:
                mod, _, name = ref.partition(".")
                theirs.add((mod.strip("'"), name.strip("'")))
            else:
                # bare name = same module; a bare MODULE name means "used as a driver", not a formula edge
                r = ref.strip("'")
                if (li.module, r) in m.line_items:
                    theirs.add((li.module, r))
        ours = set(g.rev.get(k, ()))
        if not theirs and not ours:
            continue
        agree += len(theirs & ours); ours_only += len(ours - theirs); theirs_only += len(theirs - ours)
    tot = agree + ours_only + theirs_only
    return {"agree": agree, "ours_only": ours_only, "anaplan_only": theirs_only,
            "agreement": round(agree / tot, 3) if tot else None}


def _actions_facts(e: Estate, stale_months: int) -> dict:
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
    orphans = [a.name for a in imports + exports if a.name not in in_proc and not a.processes]
    stale = [(a.name, a.last_run[:10] or "never") for a in imports + exports if not a.last_run or (cutoff and a.last_run[:10] < cutoff)]
    slow = sorted(((a.name, a.duration_ms) for a in acts if a.duration_ms), key=lambda x: -x[1])[:10]
    sources = defaultdict(list)
    for a in imports:
        mm = _FROM.search(a.name)
        if mm:
            sources[mm.group(1).strip()].append(a.name)
    return {"actions": len(acts), "imports": len(imports), "exports": len(exports), "processes": len(e.processes),
            "latest_run": latest[:10], "stale_cutoff": cutoff,
            "imports_by_target": by_target.most_common(20),
            "process_steps": sorted(((p.name, len(p.steps)) for p in e.processes.values()), key=lambda x: -x[1])[:15],
            "orphans": orphans[:40], "orphan_count": len(orphans),
            "stale": stale[:40], "stale_count": len(stale), "slow": slow,
            "sources": {k: v for k, v in sources.items()}}


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
        "has_effort": has_effort, "effort_top10_share": top10_share,
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
    return ModelRun(spec["name"], spec["folder"], m, g, lr, cl, e, facts, red)


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
        e["phrases"] = sorted(e["phrases"]); e["targets"] = e["targets"][:12]; e["basis"] = "inferred from import action names"
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
    er.actions = actionlist.build(er)
    return er


# ---------- rendering ----------

def _slug(t: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", t.lower()).strip("-")


def _headlines(er: EstateRun) -> list[str]:
    """The report in ten sentences, each computed from the facts and each
    pointing at the section that shows the working. Plain words, no verdicts."""
    ms = er.models
    big = max(ms, key=lambda m: m.facts["cells"])
    total_cells = sum(m.facts["cells"] for m in ms)
    total_li = sum(m.facts["line_items"] for m in ms)
    h = []
    top_mod = big.facts["cells_by_module"][0] if big.facts["cells_by_module"] else ("", 0, 0)
    h.append(f"**{len(ms)} models, {_n(total_li)} line items, {_c(total_cells)} cells.** {big.name} is {round(100 * big.facts['cells'] / total_cells) if total_cells else 0}% of the estate by cells; "
             f"its largest module alone holds {_c(top_mod[1])} ({top_mod[0]}). [Estate at a glance](#the-estate-at-a-glance)")
    if er.edges:
        feeders = Counter()
        for e in er.edges:
            feeders[e["from"]] += e["actions"]
        hub, n = feeders.most_common(1)[0]
        h.append(f"**{hub} is the hub.** It feeds {', '.join(e['to'] for e in er.edges if e['from'] == hub)} through {n} import actions; "
                 f"{len(er.edges)} feeds between models in all, read off the import action names. [How the models connect](#how-the-models-connect-inferred)")
    if er.external:
        top = sorted(er.external.items(), key=lambda kv: -len(kv[1]))[0]
        h.append(f"**Outside data arrives from {len(er.external)} named sources**, the busiest being {top[0]} with {len(top[1])} imports. [External sources](#how-the-models-connect-inferred)")
    eff = [m for m in ms if m.facts["has_effort"]]
    if eff:
        w = max(eff, key=lambda m: m.facts["cells"])
        top = w.facts["effort_top"][0]
        h.append(f"**Calculation time is concentrated.** In {w.name}, ten line items carry {w.facts['effort_top10_share']}% of the model's effort; the single largest is {top[0]} at {top[1]:.1f}%. "
                 f"[Where the time goes](#{_slug(w.name)})")
    unref = sum(m.facts["unreferenced"] for m in ms)
    if unref:
        w = max(ms, key=lambda m: m.facts["unreferenced"])
        h.append(f"**{_n(unref)} calculated line items feed nothing.** {w.name} has {_n(w.facts['unreferenced'])} of them: formulas that run on every recalculation and are read by no other formula. "
                 f"Some are outputs read by pages or exports, which the exports do not show. [{w.name}](#{_slug(w.name)})")
    stale = sum((m.facts["actions"] or {}).get("stale_count", 0) for m in ms)
    orph = sum((m.facts["actions"] or {}).get("orphan_count", 0) for m in ms)
    if stale or orph:
        h.append(f"**{stale} imports and exports have not run inside the stale window, and {orph} sit outside any process.** Either is a candidate for retirement, or a load nobody schedules. "
                 f"[Actions, per model](#{_slug(ms[0].name)})")
    if er.duplicates:
        d = er.duplicates[0]
        h.append(f"**{len(er.duplicates)} formulas are copied between models.** {d['line_item']} appears in {', '.join(d['models'])} with the same logic; a change to one must be repeated in the others. "
                 f"[Logic duplicated across models](#logic-duplicated-across-models)")
    faults = sum(m.facts["cycles_fault"] for m in ms); bal = sum(m.facts["cycles_balance"] for m in ms)
    if faults or bal:
        h.append(f"**{bal + faults} circular reference{'s' if bal + faults != 1 else ''}**: {bal} through a time offset (the opening-balance pattern, normal) and {faults} without (a parser misread or a real fault).")
    pats = sum(m.facts["patterns"] for m in ms); finds = sum(m.facts["findings"] for m in ms)
    h.append(f"**{_n(finds)} rule findings collapse to {pats} patterns.** A pattern is one decision copied across modules or line items; fix the template and the copies follow. "
             f"None of this says whether a finding matters for this estate. That is a review, and this report is its evidence. [Procedures performed](#procedures-performed)")
    agree = [(m.name, m.facts["referenced_by_check"]["agreement"]) for m in ms if m.facts["referenced_by_check"]["agreement"] is not None]
    if agree:
        h.append("**How far to trust the graph.** Every formula parsed. Our dependency edges agree with Anaplan's own Referenced By column at "
                 + ", ".join(f"{n} {a:.0%}" for n, a in agree)
                 + "; the gap is line-item subsets through COLLECT(), which the export does not describe.")
    return h


def _toc(er: EstateRun) -> list[str]:
    rows = [("The estate at a glance", "One row per model. Size, how much of it is calculated, how many imports and processes, when it last ran."),
            ("How the models connect (inferred)", "Which model feeds which, read off the names of import actions, plus the outside systems those names mention. Inferred, and labelled so."),
            ("Logic duplicated across models", "The same line item with the same formula in more than one model. One change, several places."),
            ("Dimensions shared across models", "Lists that appear in more than one model. Where a hierarchy change ripples.")]
    for m in er.models:
        f = m.facts
        rows.append((m.name, f"{f['modules']} modules, {_n(f['line_items'])} line items, {_c(f['cells'])} cells. Where its calculation time goes, what everything depends on, its actions, and its patterns."))
    rows.append(("Procedures performed", "Every rule that ran and its source, so you know exactly what was and was not checked."))
    rows.insert(0, ("Actions in detail", "One section per action: why, steps, verify, evidence."))
    rows.insert(1, ("The estate", "One row per model, how the models connect, logic and dimensions shared across them."))
    out = ["| Section | What it tells you |", "|---|---|"]
    for t, d in rows:
        out.append(f"| [{t}](#{_slug(t)}) | {d} |")
    return out


GLOSSARY = [
    "**Cells** are what Anaplan bills for and what makes a model slow to open: every line item multiplied out over its dimensions and time. 10.9B means ten thousand million.",
    "**Calculation effort** is Anaplan's own measure of where the engine spends its time, as a share of the model, exported from Blueprint. Ten line items usually carry most of it.",
    "**Patterns** are findings grouped by the decision behind them. A formula copied into 96 month columns is one pattern, not 96 problems.",
    "**Referenced By agreement** is our dependency graph checked against the column Anaplan exports. High means the graph can be trusted; the gap is explained where it appears.",
    "**Inferred** means read off names, not off a system table. Anaplan does not export which model imports from which; the action names usually say.",
]


def _n(x):
    return f"{x:,}" if isinstance(x, int) else str(x)


def _c(x) -> str:
    """Compact scale for cell counts: 10.9B, 222M, 8.9M, 720. Exact values stay in the JSON."""
    if not isinstance(x, (int, float)):
        return str(x)
    for div, suf in ((1e9, "B"), (1e6, "M"), (1e3, "K")):
        if abs(x) >= div:
            v = x / div
            return f"{v:.0f}{suf}" if v >= 100 else f"{v:.1f}{suf}"
    return f"{x:,}"


def render_markdown(er: EstateRun, max_patterns: int = 20) -> str:
    red_items = sum(m.facts["redundancy"]["exact_redundant"] + m.facts["redundancy"]["aliases"] for m in er.models)
    red_cells = sum(m.facts["redundancy"]["exact_cells"] + m.facts["redundancy"]["alias_cells"] for m in er.models)
    out = [f"# Anaplan estate: {len(er.models)} model{'s' if len(er.models) != 1 else ''}", "",
           f"Generated {er.generated} from each model's Line Items and Actions exports. Deterministic; no opinion. "
           "Model-to-model links are inferred from import action names and say so.", "",
           "## What to do", "",
           f"{len(er.actions)} actions in {len(actionlist.by_category(er.actions))} categories, biggest reclaim first. Click a category for its actions ranked by impact, "
           "and an action for the why, the steps, how to verify, and the evidence. Every action says what the exports prove and what they cannot: "
           "formulas, imports and exports are in the files; pages and saved views are not, so anything that needs a page check says so.", ""]
    out += actionlist.render_summary(er.actions)
    out += ["", "## The estate in one page", ""]
    out += [f"{i}. {h}" for i, h in enumerate(_headlines(er), 1)]
    if red_items:
        out.append(f"{len(_headlines(er)) + 1}. **{_n(red_items)} line items repeat a calculation already made in the same model** ({_c(red_cells)} cells stored twice): "
                   "same resolved formula and dimensions under another name, or a plain copy of another line item. [Actions](#what-to-do)")
    out += ["", "## How to read this report", "",
            "Three parts. The action list above and its detail chapter. Then the estate: how the models connect, what is shared, and one chapter per model, all the same shape, so you can compare them. "
            "The last section lists what was checked. In the HTML view each chapter is folded; a link opens the one it points to.", ""]
    out += _toc(er)
    out += ["", "A few words that carry weight here:", ""] + [f"- {g}" for g in GLOSSARY]
    out += ["", "# Actions in detail", "",
            "One section per category, each a ranked table and then every action: why, in the words of the exports; the steps; how to prove it worked; and the evidence. "
            "Nothing here says whether an action is worth taking for this business. That is a review, and this is its evidence.", ""]
    out += actionlist.render_detail(er.actions)
    out += ["", "# The estate", "",
           "## The estate at a glance", "",
           "| Model | Modules | Line items | Calculated | Cells | Parse | Imports | Exports | Processes | Latest run | Patterns |",
           "|---|---|---|---|---|---|---|---|---|---|---|"]
    for m in er.models:
        f = m.facts; a = f["actions"] or {}
        out.append(f"| {m.name} | {f['modules']} | {_n(f['line_items'])} | {_n(f['calculated'])} | {_c(f['cells'])} | {f['parse_rate']:.1%} | "
                   f"{a.get('imports', '')} | {a.get('exports', '')} | {a.get('processes', '')} | {a.get('latest_run', '')} | {f['patterns']} |")
    out += ["", "## How the models connect (inferred)", ""]
    if er.edges:
        out += ["| From | To | Import actions | Into (sample) | Named as |", "|---|---|---|---|---|"]
        for e in er.edges:
            out.append(f"| {e['from']} | {e['to']} | {e['actions']} | {', '.join(e['targets'][:4])} | {', '.join(e['phrases'][:3])} |")
        out += ["", "```mermaid", "flowchart LR"]
        ids = {m.name: f"M{i}" for i, m in enumerate(er.models)}
        for m in er.models:
            out.append(f"  {ids[m.name]}[\"{m.name}\"]")
        for e in er.edges:
            out.append(f"  {ids[e['from']]} -->|{e['actions']}| {ids[e['to']]}")
        out.append("```")
    else:
        out.append("No import action names matched another model in the set.")
    if er.external:
        out += ["", "External sources named in import actions (not a model in this set):", ""]
        for src, acts in sorted(er.external.items(), key=lambda kv: -len(kv[1]))[:25]:
            out.append(f"- **{src}**: {len(acts)} action(s), e.g. {acts[0]}")
    if er.duplicates:
        out += ["", "## Logic duplicated across models", "",
                "Same line item name with the same formula tree in more than one model. One change must be made in each.", "",
                "| Line item | Models | Copies | Formula |", "|---|---|---|---|"]
        for d in er.duplicates[:25]:
            out.append(f"| {d['line_item']} | {', '.join(d['models'])} | {d['copies']} | `{d['formula'][:90]}` |")
    if er.shared_dims:
        out += ["", "## Dimensions shared across models", "", ", ".join(f"{d} ({len(ms)})" for d, ms in er.shared_dims[:40])]
    for m in er.models:
        out += ["", "---", "", *_render_model(m, max_patterns)]
    out += ["", "## Procedures performed", "",
            "Every formula parsed with anaplan-grammar; dependency graph built from the parse trees and checked against Anaplan's Referenced By column; "
            "rules below run where the inputs allow; findings grouped into patterns. No opinion is expressed; nothing here says whether a finding matters for this model.", "",
            "| Rule | Severity | Source | Description |", "|---|---|---|---|"]
    for rid, r in RULES.items():
        out.append(f"| {rid} {r.title} | {r.severity} | {r.source} | {r.description[:110]} |")
    return "\n".join(out)


def _render_model(m: ModelRun, max_patterns: int) -> list[str]:
    f = m.facts; a = f["actions"]
    out = [f"# {m.name}", "",
           f"| | |", "|---|---|",
           f"| Modules | {f['modules']} |", f"| Line items | {_n(f['line_items'])} ({_n(f['calculated'])} calculated, {_n(f['inputs'])} input) |",
           f"| Cells (as exported) | {_c(f['cells'])} ({_n(f['cells'])}) |", f"| Dimensions | {len(f['dimensions'])} |",
           f"| Formulas parsed | {f['parse_rate']:.2%} ({f['parse_errors']} failed) |",
           f"| References | {_n(f['edges'])} line-item edges, {_n(f['module_edges'])} module edges |",
           f"| Agreement with Anaplan's Referenced By | {f['referenced_by_check']['agreement']} (ours only {f['referenced_by_check']['ours_only']}, Anaplan only {f['referenced_by_check']['anaplan_only']}; "
           f"Anaplan-only edges are mostly line-item subsets via COLLECT(), which the export does not describe) |",
           f"| Circular references | {f['cycles']} ({f['cycles_balance']} through a time offset, {f['cycles_fault']} without) |",
           f"| Pass-through chains | {f['daisy_chains']} |", f"| Calculated but unreferenced | {_n(f['unreferenced'])} |",
           f"| Line items with notes | {f['notes_coverage']:.0%} |",
           f"| Inputs used | Line Items{' + Modules' if f['has_modules_export'] else ''}{' + Actions' if a else ''}; rules skipped: {', '.join(f['rules_skipped']) or 'none'} |"]
    if f["has_effort"]:
        out += ["", f"## Where the calculation time goes (top 10 line items = {f['effort_top10_share']}% of the model's effort)", "",
                "| Line item | Effort | Cells | Formula |", "|---|---|---|---|"]
        for name, eff, cells, formula in f["effort_top"][:15]:
            out.append(f"| {name} | {eff:.2f}% | {_c(cells)} | `{formula[:80]}` |")
        out += ["", "By module: " + ", ".join(f"{n} {v:.1f}%" for n, v in f["effort_by_module"][:8])]
    else:
        out += ["", "_No Calculation Effort column in this export (Blueprint > Calculation Effort, Classic engine, from March 2025)._"]
    out += ["", "## Largest modules by cells", "", "| Module | Cells | Share |", "|---|---|---|"]
    for n, c, p in f["cells_by_module"][:8]:
        out.append(f"| {n} | {_c(c)} | {p}% |")
    out += ["", "## Most depended-on line items", "", "| Line item | Direct dependents |", "|---|---|"]
    for n, c in f["hubs"][:8]:
        out.append(f"| {n} | {c} |")
    if a:
        out += ["", "## Actions", "",
                f"{a['imports']} imports, {a['exports']} exports, {a['processes']} processes. Latest run {a['latest_run'] or 'unknown'}; "
                f"stale = not run since {a['stale_cutoff'] or 'n/a'}.", "",
                f"- Imports not in any process: {a['orphan_count']}" + (f" (e.g. {', '.join(a['orphans'][:4])})" if a["orphans"] else ""),
                f"- Stale or never-run imports and exports: {a['stale_count']}" + (f" (e.g. {', '.join(f'{n} [{d}]' for n, d in a['stale'][:4])})" if a["stale"] else ""),
                "- Slowest actions: " + ", ".join(f"{n} {ms / 1000:.0f}s" for n, ms in a["slow"][:5]),
                "- Most imported-into: " + ", ".join(f"{t} ({n})" for t, n in a["imports_by_target"][:6])]
    out += ["", f"## Patterns ({f['findings']} findings in {f['patterns']} patterns)", ""]
    from .cluster import render_markdown as rc
    out.append(rc(m.clusters, max_rows=max_patterns))
    return out
