"""Assemble the report from an EstateRun.

Action plan   the estate title, one scope and freshness line, at most three
              suggested actions (plan.select), the coverage notices that affect
              them. The default reading path.
Change impact the embedded dependency data (impact.graph_data) the explorer
              and the change-review download rest on.
Evidence      the complete findings catalogue by decision area, the model map
              and feed table, inventory, coverage, dependency evidence,
              methodology, glossary, register.

`build` returns a plain dict (JSON-safe) that both renderers read, so the
Markdown and the HTML say the same thing. Links (feedback, source, help)
appear only when configured with a valid http(s) URL; nothing is invented.
"""
from __future__ import annotations
import csv, io, re, datetime
from collections import Counter
from .lint import RULES, PLANUAL, DOCS
from .findings import AREAS, AREA_LABEL, STRENGTH_TEXT, by_area, _c, _pl
from . import plan as planmod, impact

DESCRIPTION = "Automated findings and candidate recommendations from each model's Line Items, Modules and Actions exports."

GLOSSARY = [
    ("Cells", "Every line item multiplied out over its dimensions and time, as the export counts them. Workspace size and model open time follow cells; contractual cost does not follow from cells alone."),
    ("Calculation effort", "Anaplan's own measure of where the engine spends its time, per line item, as a share of one model. Classic measures the whole model at open; Polaris measures a rolling ten-minute window. The exports do not say which engine produced the column, and shares are never added across models."),
    ("No consumer detected", "No formula in the export references the object and, where an Actions export was supplied, no export action reads its module (otherwise action usage is not assessed). Pages, saved views, line item subsets, filters, access drivers and integrations are not in the exports and can hold consumers; incomplete parsing can hide a reader. Not the same as unused."),
    ("Referenced By agreement", "Agreement between two observed edge sets: edges present in both the parsed dependency graph and Anaplan's Referenced By column, over edges present in either. It measures how far the two agree, not what share of every dependency is known; 100% does not establish complete coverage of the estate. Discrepancies are listed by cause."),
    ("Observed footprint", "The cells of the objects reached or named, each counted once. Not a saving, a changed value or a predicted runtime; those are measured after a validated change."),
    ("Inferred", "Read off names, not off a system table. Model-to-model feeds come from the words after 'from' in import action names; the same words give the source-name candidates."),
    ("Footprint", "What objects occupy now. A conditional benefit is what would be released if an investigation confirms they can go. A measured improvement needs a before-and-after reading in the model; this report contains none."),
    ("Evidence strength", "Confirmed: everything relied on is in the exports. Partial: formulas and actions are, pages and subsets are not. Inferred: rests on names or on a comparison the exports cannot fully resolve."),
]


def _n(x):
    return f"{x:,}" if isinstance(x, int) else str(x)


def _slug(t: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", t.lower()).strip("-")


# ---------------------------------------------------------------- level 1

def _observations(er) -> list[str]:
    """Three short observations computed from the inputs: footprint, effort concentration, feeds. Repeated calculation
    and no-consumer footprint are carried by the investigations, not repeated here."""
    ms = er.models
    total_cells = sum(m.facts["cells"] for m in ms) or 1
    obs = []
    big = max(ms, key=lambda m: m.facts["cells"])
    top_mod = big.facts["cells_by_module"][0] if big.facts["cells_by_module"] else None
    s = f"{big.name} holds {round(100 * big.facts['cells'] / total_cells)}% of the estate's {_c(total_cells)} exported cells"
    obs.append(s + (f"; {top_mod[0]} alone holds {_c(top_mod[1])}." if top_mod else "."))
    eff = [m for m in ms if m.facts["has_effort"] and m.facts["effort_top"]]
    if eff:
        w = max(eff, key=lambda m: m.facts["cells"])
        obs.append(f"Ten line items carry {w.facts['effort_top10_share']}% of {w.name}'s measured calculation effort (per model; the engine is not in the export).")
    if er.edges:
        feeders = Counter()
        for e in er.edges:
            feeders[e["from"]] += e["actions"]
        hub, n = feeders.most_common(1)[0]
        obs.append(f"{hub} feeds {', '.join(e['to'] for e in er.edges if e['from'] == hub)} through {n} import actions; all {len(er.edges)} feeds are inferred from action names.")
    return obs[:3]


def _limitations(er) -> list[str]:
    ms = er.models
    out = ["Pages, saved views, line item subsets, filters, access drivers and integrations are not in any export; each 'no consumer detected' finding lists the checks that remain."]
    agree = [(m.name, m.facts["referenced_by_check"]["agreement"]) for m in ms if m.facts["referenced_by_check"]["agreement"] is not None]
    low = [(n, a) for n, a in agree if a < 0.95]
    if low:
        causes = Counter()
        for m in ms:
            causes.update(m.facts["referenced_by_check"]["anaplan_only_by_cause"])
        out.append("Dependency coverage is incomplete in " + ", ".join(f"{n} ({a:.0%})" for n, a in low) + " (agreement with Referenced By); findings there are marked partial or inferred.")
    no_actions = [m.name for m in ms if not m.facts.get("actions")]
    if no_actions:
        out.append(f"No Actions export for {', '.join(no_actions)}: import, export and process usage is not assessed there (not zero); feeds from those models are unknown.")
    unparsed = [(m.name, m.facts["parse_errors"]) for m in ms if m.facts["parse_errors"]]
    if unparsed:
        out.append("Formulas not parsed: " + ", ".join(f"{n} ({k})" for n, k in unparsed) + "; their references are absent from the graph.")
    out.append("Export date unknown for every file; the latest recorded action run is not an export date.")
    return out


def _summary_text(er, rep) -> list[str]:
    ms = er.models
    total_li = sum(m.facts["line_items"] for m in ms); total_cells = sum(m.facts["cells"] for m in ms)
    snaps = [m.facts["coverage"]["snapshot_actions"] for m in ms if m.facts["coverage"]["snapshot_actions"]]
    p1 = (f"{len(ms)} Anaplan model{'s' if len(ms) != 1 else ''}, {_n(total_li)} line items, {_c(total_cells)} cells as exported. "
          f"Export date unknown. " + (f"Latest recorded action run {max(snaps)}. " if snaps else "") + f"Analysis generated {rep['generated']}.")
    return [p1]


def _suggested_selection(er, gd) -> dict | None:
    """A starting selection for the Change impact view: the most-read line item of the largest model, by node id."""
    ms = [m for m in er.models if m.facts["hubs"]]
    if not ms:
        return None
    m = max(ms, key=lambda x: x.facts["cells"])
    mi = [x.name for x in er.models].index(m.name)
    name, n = m.facts["hubs"][0]
    idx = impact.node_index(gd)
    for k in m.model.line_items:
        if f"{k[0]}.{k[1]}" == name and (mi, k[0], k[1]) in idx:
            return {"id": idx[(mi, k[0], k[1])], "model": m.name, "module": k[0], "name": k[1], "direct_readers": n}
    return None


_URL = re.compile(r"^https?://[^\s\"'<>]+$")


def _url(u: str | None) -> str:
    """Only a plain http(s) URL is used; anything else is dropped without a trace in the report (the CLI reports it)."""
    return u.strip() if u and _URL.match(u.strip()) else ""


# ---------------------------------------------------------------- build

def build(er, service_url: str | None = None, contact: str | None = None, feedback_url: str | None = None, source_url: str | None = None,
          help_url: str | None = None, generator: str = "CodelessOps Estate Review") -> dict:
    ms = er.models
    fs = er.findings
    rep = {"title": f"Anaplan estate: {len(ms)} model{'s' if len(ms) != 1 else ''}", "generated": er.generated, "description": DESCRIPTION,
           "generator": generator,
           "links": {"help": _url(help_url or service_url), "feedback": _url(feedback_url), "source": _url(source_url), "contact": (contact or "").strip()},
           "service_url": _url(help_url or service_url), "contact": (contact or "").strip()}
    rep["scope"] = {"models": len(ms), "line_items": sum(m.facts["line_items"] for m in ms), "calculated": sum(m.facts["calculated"] for m in ms),
                    "cells": sum(m.facts["cells"] for m in ms), "findings": len(fs),
                    "parse_rate": round(1 - sum(m.facts["parse_errors"] for m in ms) / max(sum(m.facts["calculated"] for m in ms), 1), 4)}
    rep["observations"] = _observations(er)
    rep["plan"] = planmod.select(er)
    rep["investigations"] = rep["plan"]["actions"]
    rep["metrics"] = {"models": len(ms), "review_first": sum(1 for x in fs if x.importance in ("high", "medium")),
                      "reference": sum(1 for x in fs if x.importance == "low"), "validated_defects": 0,
                      "observations": sum(1 for x in fs if x.kind_label == "observation")}
    rep["graph"] = impact.graph_data(er)
    rep["graph"]["suggested"] = _suggested_selection(er, rep["graph"])
    rep["limitations"] = _limitations(er)
    rep["summary_text"] = _summary_text(er, rep)
    rep["freshness"] = {"export_date": None, "latest_action_run": (max((m.facts["coverage"]["snapshot_actions"] for m in ms if m.facts["coverage"]["snapshot_actions"]), default=None)),
                        "analysis_date": er.generated, "actions_missing": [m.name for m in ms if not m.facts.get("actions")]}
    rep["map"] = {"nodes": [{"name": m.name, "cells": m.facts["cells"], "line_items": m.facts["line_items"]} for m in ms],
                  "edges": [{"from": e["from"], "to": e["to"], "actions": e["actions"], "targets": e["targets"], "basis": e["basis"], "confirmed": False} for e in er.edges],
                  "external": {k: v for k, v in er.external.items()}}
    rep["areas"] = [{"key": k, "label": l, "blurb": b, "ids": [x.id for x in xs]} for k, l, b, xs in by_area(fs)]
    rep["findings"] = [x.to_dict() for x in fs]
    rep["models"] = []
    for m in ms:
        f = m.facts
        rep["models"].append({"name": m.name, "folder": m.folder, "facts": {k: v for k, v in f.items() if k not in ("coverage",)},
                              "coverage": f["coverage"], "redundancy": m.redundancy.to_dict(),
                              "patterns": [c.to_dict() for c in m.clusters], "findings_by_rule": m.lint.counts["by_rule"],
                              "lint": [{"rule": x.rule, "severity": x.severity, "object": x.object, "message": x.message, "fix": x.fix} for x in m.lint.findings]})
    rep["shared_dims"] = er.shared_dims
    rep["duplicates"] = er.duplicates
    rep["methodology"] = [{"id": rid, "title": r.title, "severity": r.severity, "source": r.source, "description": r.description,
                           "planual": [f"{i} {PLANUAL.get(i, '')}" for i in r.planual], "docs": [{"title": DOCS[d][0], "url": DOCS[d][1], "quote": DOCS[d][2]} for d in r.docs]}
                          for rid, r in RULES.items()]
    rep["methodology"] += [
        {"id": "REDUNDANT-EXACT", "title": "Same calculation under different names", "severity": "info", "source": "GRAPH", "description": "Same resolved formula and same context (dimensions, time scale, time range, versions, data type, summary, formula scope). COLLECT() and blank-context rows excluded.", "planual": [], "docs": [{"title": DOCS["collect"][0], "url": DOCS["collect"][1], "quote": DOCS["collect"][2]}]},
        {"id": "REDUNDANT-ALIAS", "title": "Line item that only copies another", "severity": "info", "source": "GRAPH", "description": "Formula is a single reference to a line item with identical context.", "planual": [], "docs": []},
        {"id": "REDUNDANT-NEAR", "title": "Formulas that differ in one leaf", "severity": "info", "source": "GRAPH", "description": "Same skeleton and context; one constant, reference or list item differs. May be intentional.", "planual": [], "docs": []},
        {"id": "REDUNDANT-SAME-TEXT", "title": "Identical text, unresolved context", "severity": "info", "source": "GRAPH", "description": "Not compared: COLLECT() or blank metadata.", "planual": [], "docs": []},
        {"id": "ACTIONS", "title": "Imports and exports: recorded runs and process membership", "severity": "info", "source": "ACTIONS", "description": "Most recent recorded run per action relative to the export's latest run; process membership. Not a verdict on use.", "planual": [], "docs": [{"title": DOCS["actions"][0], "url": DOCS["actions"][1], "quote": DOCS["actions"][2]}]},
        {"id": "EFFORT", "title": "Calculation Effort concentration", "severity": "info", "source": "ANAPLAN", "description": "Anaplan's per-line-item share, as exported, per model.", "planual": ["2.03-07 Review the calculation effort"], "docs": [{"title": DOCS["line-items"][0], "url": DOCS["line-items"][1], "quote": DOCS["line-items"][2]}]},
        {"id": "DUP-CROSS", "title": "Same name and formula in more than one model", "severity": "info", "source": "GRAPH", "description": "Formula tree equality across models; local data may differ.", "planual": [], "docs": []},
    ]
    rep["glossary"] = GLOSSARY
    rep["strength_text"] = STRENGTH_TEXT
    rep["statuses"] = ["To review", "Investigation in progress", "Accepted exception", "Change planned", "Resolved"]
    rep["validation_note"] = ("Rules, ranking and presentation were developed around a small number of estates; the three-action, 450-word plan is a design choice, "
                              "not an established optimum, and the ordering is a hypothesis to revise. Nothing here was validated in a live Anaplan model.")
    return rep


# ---------------------------------------------------------------- register

REGISTER_COLS = ["id", "uid", "area", "title", "model", "kind_label", "importance", "strength", "complexity", "benefit_kind", "footprint_cells", "footprint_effort", "action_usage", "object_label", "preview_label", "scope", "benefit", "next_step", "preview", "objects", "rules", "related"]


def register_rows(rep: dict) -> list[dict]:
    rows = []
    for x in rep["findings"]:
        r = {k: ("" if x.get(k) is None else x.get(k, "")) for k in REGISTER_COLS}
        r["area"] = AREA_LABEL.get(x["area"], x["area"])
        r["objects"] = "; ".join(x["objects"]); r["preview"] = "; ".join(x["preview"]); r["rules"] = "; ".join(x["rules"]); r["related"] = "; ".join(x["related"])
        rows.append(r)
    return rows


def register_csv(rep: dict) -> str:
    buf = io.StringIO()
    w = csv.DictWriter(buf, fieldnames=REGISTER_COLS, lineterminator="\n")
    w.writeheader()
    for r in register_rows(rep):
        w.writerow(r)
    return buf.getvalue()


# ---------------------------------------------------------------- markdown

def _finding_md(x: dict) -> list[str]:
    ex = x["preview"]
    out = [f"### {x['id']}. {x['title']}", "",
           f"{x['model']} · {x['kind_label']} · importance {x['importance']} · evidence {x['strength']} · complexity {x['complexity']} · export actions: {x['action_usage']}", "",
           f"{x['preview_label']}: {', '.join('`' + o + '`' for o in ex)} ({x['object_label']})", "",
           f"**Observed.** {x['summary']}", "", f"**Why it matters.** {x['why']}", "", f"**Next investigation step.** {x['next_step']}", "",
           "<details><summary>Full assessment and affected objects</summary>", "",
           f"**Observed, in full.** {x['observed']}", "", f"**Affected scope.** {x['scope']}", "", f"**Potential benefit.** {x['benefit']} ({x['benefit_kind']})", "",
           f"**Evidence strength.** {x['strength']}: {x['basis']}", ""]
    if x["missing"]:
        out += ["**Missing information.**", ""] + [f"- {mi}" for mi in x["missing"]] + [""]
    out += [f"**When keeping the current design is reasonable.** {x['keep_design']}", ""]
    if x["implementation"]:
        out += ["**Implementation, with prerequisites.**", ""] + [f"- {v}" for v in x["implementation"]] + [""]
    if x["related"]:
        out += [f"Alternative or related: {', '.join(x['related'])}.", ""]
    out += [f"**All affected objects ({len(x['objects'])} {x['unit']}).** " + ", ".join("`" + o + "`" for o in x["objects"]), ""]
    if x["evidence"]:
        out += ["**Evidence**", ""] + x["evidence"] + [""]
    if x["validation"]:
        out += ["**Validation**", ""] + [f"- {v}" for v in x["validation"]] + [""]
    out += ["</details>", ""]
    return out


def render_markdown(er) -> str:
    rep = build(er)
    fmap = {x["id"]: x for x in rep["findings"]}
    out = [f"# {rep['title']}", "", f"Generated with {rep['generator']}. {rep['summary_text'][0]}", "", "## Action plan", ""]
    pl = rep["plan"]
    if pl["actions"]:
        for i, a in enumerate(pl["actions"], 1):
            out += [f"### {i}. {a['title']}", "", f"**Why.** {a['why']}", "", "**Steps.**", ""] + [f"{j}. {st}" for j, st in enumerate(a["steps"], 1)] + ["",
                    f"**Done when.** {a['done_when']}", "", f"Role: {a['role']}. Evidence: {', '.join(f'[{x}](#{x})' for x in a['finding_ids']) or 'none'}."
                    + (f" Depends on: {', '.join(a['depends_on'])}." if a["depends_on"] else "")]
            out += [f"- Note: {n}" for n in a["notices"]] + [""]
    else:
        out += [pl["none"]["message"], "", f"Next data check: {pl['none']['next_check']}.", ""]
    out += ["Suggested starting points from the supplied exports; the ordering is a hypothesis (see Evidence: how the actions were chosen).", ""]
    out += ["## Coverage", ""] + [f"- {l}" for l in rep["limitations"]] + [""]
    out += ["## Observations", ""] + [f"{i}. {o}" for i, o in enumerate(rep["observations"], 1)] + [""]
    mt = rep["metrics"]
    out += [f"{mt['models']} models reviewed · {mt['review_first']} findings to review first · {mt['reference']} additional reference findings. No finding is a validated defect; all are observations or review candidates.", ""]
    if rep["map"]["edges"]:
        out += ["**Model map (feeds inferred from import action names)**", "", "```mermaid", "flowchart LR"]
        ids = {n["name"]: f"M{i}" for i, n in enumerate(rep["map"]["nodes"])}
        for n in rep["map"]["nodes"]:
            out.append(f"  {ids[n['name']]}[\"{n['name']} ({_c(n['cells'])} cells)\"]")
        for e in rep["map"]["edges"]:
            out.append(f"  {ids[e['from']]} -.->|{e['actions']} inferred| {ids[e['to']]}")
        out += ["```", ""]
    out += ["## How the actions were chosen", "", f"{pl['considered']} candidates were built from the findings; {len(pl['actions'])} met the bar for being worth doing. The number is not fixed.", "",
            "**What counts as worth doing**", ""] + [f"- {r}" for r in pl["worth"]] + ["", "**Order**", ""] + [f"- {r}" for r in pl["ranking"]] + [""]
    if pl["candidates"]:
        out += ["| Rank | Candidate | Evidence | Kind | Scope | Footprint |", "|---|---|---|---|---|---|"]
        for i, c in enumerate(pl["candidates"], 1):
            out.append(f"| {i} | {c['title']} | {c['strength']} | {c['kind']} | {'bounded' if c['bounded'] else 'open'} ({len(c['objects'])}) | {_c(c['footprint_cells']) + ' cells' if c['footprint_cells'] else 'not measured'} |")
        out.append("")
    out += ["# Findings", ""]
    for a in rep["areas"]:
        out += [f"## {a['label']}", "", a["blurb"], ""]
        for fid in a["ids"]:
            out += _finding_md(fmap[fid])
    out += ["# Reference", "", "## Findings register", "", "| ID | Area | Title | Model | Importance | Evidence | Complexity | Footprint cells | Effort share |", "|---|---|---|---|---|---|---|---|---|"]
    for r in register_rows(rep):
        out.append(f"| {r['id']} | {r['area']} | {r['title']} | {r['model']} | {r['importance']} | {r['strength']} | {r['complexity']} | {_c(r['footprint_cells']) if r['footprint_cells'] != '' else 'n/a'} | {r['footprint_effort'] if r['footprint_effort'] != '' else 'n/a'} |")
    out += ["", "## Models and coverage", ""]
    for m in rep["models"]:
        f, cov = m["facts"], m["coverage"]
        out += [f"### {m['name']}", "", "| | |", "|---|---|",
                f"| Files supplied | {', '.join(k for k, v in cov['files'].items() if v)} |",
                f"| Export date | unknown (not in the files) |", f"| Latest recorded action run | {cov['snapshot_actions'] or 'no Actions export'} |",
                f"| Modules / line items / calculated | {f['modules']} / {_n(f['line_items'])} / {_n(f['calculated'])} |",
                f"| Cells as exported | {_n(f['cells'])} |", f"| Formulas parsed | {f['parse_rate']:.2%} ({f['parse_errors']} not parsed) |",
                f"| Referenced By agreement | {f['referenced_by_check']['agreement']} ({f['referenced_by_check']['definition']}) |",
                f"| Anaplan-only edges by cause | {f['referenced_by_check']['anaplan_only_by_cause']} |",
                f"| Rules run | {', '.join(cov['rules_run'])} |",
                f"| Rules skipped or limited | {'; '.join(f'{r}: {why}' for r, why in cov['rules_skipped']) or 'none'} |",
                f"| Confirmed from metadata | {'; '.join(cov['confirmed'])} |", f"| Inferred from names | {'; '.join(cov['inferred']) or 'nothing'} |",
                f"| Missing | {'; '.join(cov['missing'])} |", ""]
    if rep["map"]["external"]:
        out += ["## Source-name candidates (from import action names)", ""] + [f"- {k}: {len(v)} action(s), e.g. {v[0]}" for k, v in sorted(rep["map"]["external"].items(), key=lambda kv: -len(kv[1]))] + [""]
    if rep["shared_dims"]:
        out += ["## Dimensions shared across models", "", ", ".join(f"{d} ({len(ms)})" for d, ms in rep["shared_dims"]), ""]
    out += ["## Methodology", "", "| Rule | Severity | Source | Description | Planual | Documentation |", "|---|---|---|---|---|---|"]
    for r in rep["methodology"]:
        out.append(f"| {r['id']} {r['title']} | {r['severity']} | {r['source']} | {r['description']} | {', '.join(r['planual'])} | {', '.join(f'[{d['title']}]({d['url']})' for d in r['docs'])} |")
    out += ["", "## Glossary", ""] + [f"- **{t}.** {d}" for t, d in rep["glossary"]]
    out += ["", "## Validation status", "", rep["validation_note"], ""]
    links = rep["links"]
    foot = ["Free and open source; maintained by CodelessOps, contributions welcome."]
    if links["source"]:
        foot.append(f"Source: {links['source']}")
    if links["feedback"]:
        foot.append(f"Something missing or not quite right? Help improve this review for everyone: {links['feedback']}")
    if links["help"]:
        foot.append(f"Want another pair of eyes on this change? {links['help']}")
    out += ["---", "", " ".join(foot)]
    return "\n".join(out)
