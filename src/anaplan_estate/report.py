"""Assemble the three-level report from an EstateRun.

Level 1  opening summary: scope and freshness, three or four observations
         computed from the inputs, up to three priority investigations, the
         model map, the coverage limitations that matter most.
Level 2  findings grouped by decision area, each with the fields a team needs.
Level 3  full reference: findings register, per-model statistics and coverage,
         dependency evidence, source-name candidates, shared dimensions,
         methodology with rule definitions and documentation references,
         glossary.

`build` returns a plain dict (JSON-safe) that both renderers read, so the
Markdown and the HTML say the same thing.
"""
from __future__ import annotations
import csv, io, re, datetime
from collections import Counter
from .lint import RULES, PLANUAL, DOCS
from .findings import AREAS, AREA_LABEL, STRENGTH_TEXT, by_area, _c, _pl

DESCRIPTION = "Automated findings and candidate recommendations from each model's Line Items, Modules and Actions exports."

GLOSSARY = [
    ("Cells", "Every line item multiplied out over its dimensions and time, as the export counts them. Workspace size and model open time follow cells; contractual cost does not follow from cells alone."),
    ("Calculation effort", "Anaplan's own measure of where the engine spends its time, per line item, as a share of one model. Classic measures the whole model at open; Polaris measures a rolling ten-minute window. The exports do not say which engine produced the column, and shares are never added across models."),
    ("No consumer detected", "No formula in the export references the object and no export action reads its module. Pages, saved views, line item subsets, filters, access drivers and integrations are not in the exports and can hold consumers. Not the same as unused."),
    ("Referenced By agreement", "Edges present in both the parsed dependency graph and Anaplan's Referenced By column, over edges present in either. High means the graph can be trusted for change impact; discrepancies are listed by cause."),
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
    ms = er.models
    total_cells = sum(m.facts["cells"] for m in ms) or 1
    total_li = sum(m.facts["line_items"] for m in ms)
    obs = []
    big = max(ms, key=lambda m: m.facts["cells"])
    top_mod = big.facts["cells_by_module"][0] if big.facts["cells_by_module"] else None
    s = f"{big.name} holds {round(100 * big.facts['cells'] / total_cells)}% of the estate's {_c(total_cells)} exported cells"
    if top_mod:
        s += f"; its largest module, {top_mod[0]}, holds {_c(top_mod[1])} on its own"
    obs.append(s + ".")
    eff = [m for m in ms if m.facts["has_effort"] and m.facts["effort_top"]]
    if eff:
        w = max(eff, key=lambda m: m.facts["cells"])
        obs.append(f"In {w.name}, ten line items carry {w.facts['effort_top10_share']}% of the measured calculation effort, led by {w.facts['effort_top'][0][0]} at {w.facts['effort_top'][0][1]:.1f}%. "
                   "Effort shares are per model and depend on the engine (Classic at open, Polaris over ten minutes), which the export does not name.")
    if er.edges:
        feeders = Counter()
        for e in er.edges:
            feeders[e["from"]] += e["actions"]
        hub, n = feeders.most_common(1)[0]
        obs.append(f"{hub} feeds {', '.join(e['to'] for e in er.edges if e['from'] == hub)} through {n} import actions; {len(er.edges)} feeds between models in all, inferred from import action names and not confirmed by any system table.")
    red_items = sum(m.facts["redundancy"]["exact_redundant"] + m.facts["redundancy"]["aliases"] for m in ms)
    red_cells = sum(m.facts["redundancy"]["exact_cells"] + m.facts["redundancy"]["alias_cells"] for m in ms)
    if red_items:
        obs.append(f"{_n(red_items)} calculated line items repeat a calculation already made in the same model under another name, or copy another line item outright; the copies hold {_c(red_cells)} cells. Some will exist for a page or an access boundary.")
    orphan_cells = sum(x.footprint_cells for x in er.findings if x.area == "usage" and x.counts_benefit)
    if orphan_cells:
        obs.append(f"Objects with no consumer detected in the inspected dependency types hold {_c(orphan_cells)} cells. Pages, saved views and subsets are not in the exports, so this is a set of investigations, not a saving.")
    return obs[:4]


def _priorities(er) -> list[dict]:
    """Up to three investigations: findings that ask for a decision (not reference facts such as effort
    concentration or hubs), highest importance first, evidence strength preferred, footprint next.
    Distinct areas are preferred; none is manufactured when the evidence supports fewer."""
    cands = [x for x in er.findings if x.kind not in ("capacity", "hub") and x.importance in ("high", "medium") and x.strength != "inferred"]
    cands.sort(key=lambda x: ({"high": 0, "medium": 1}[x.importance], {"confirmed": 0, "partial": 1}[x.strength], -x.footprint_effort, -x.footprint_cells))
    out = []; areas = []
    for pref_distinct in (True, False):
        for x in cands:
            if any(p["id"] == x.id for p in out):
                continue
            if pref_distinct and x.area in areas:
                continue
            areas.append(x.area)
            out.append({"id": x.id, "title": x.title, "model": x.model, "objects": x.objects[:3], "observed": x.observed, "why": x.why,
                        "next": x.next_step, "importance": x.importance, "strength": x.strength, "benefit": x.benefit})
            if len(out) == 3:
                return out
    return out


def _limitations(er) -> list[str]:
    ms = er.models
    out = ["Pages, dashboards, saved views, line item subsets, filters, access drivers and integrations are not in any export. Every 'no consumer detected' finding carries the checks that remain."]
    agree = [(m.name, m.facts["referenced_by_check"]["agreement"]) for m in ms if m.facts["referenced_by_check"]["agreement"] is not None]
    low = [(n, a) for n, a in agree if a < 0.95]
    if low:
        causes = Counter()
        for m in ms:
            causes.update(m.facts["referenced_by_check"]["anaplan_only_by_cause"])
        out.append("Dependency coverage is incomplete where the parsed graph disagrees with Anaplan's Referenced By: " + ", ".join(f"{n} {a:.0%}" for n, a in low) +
                   f". Of the edges Anaplan lists that the parse did not, {causes.get('collect', 0)} come from COLLECT() line item subsets, {causes.get('unparsed', 0)} from unparsed formulas and {causes.get('other', 0)} are unexplained. Findings in those models are marked partial or inferred accordingly.")
    no_actions = [m.name for m in ms if not m.facts.get("actions")]
    if no_actions:
        out.append(f"No Actions export for {', '.join(no_actions)}: imports, exports, processes, run dates and feeds were not analysed for {'that model' if len(no_actions) == 1 else 'those models'}.")
    no_eff = [m.name for m in ms if not m.facts["has_effort"]]
    if no_eff:
        out.append(f"No Calculation Effort figures for {', '.join(no_eff)}.")
    out.append("The date the Line Items and Modules exports were taken is not in the files; the Actions export's latest recorded run is the closest thing to a snapshot date. The report generation date is not data freshness.")
    return out


def _summary_text(er, rep) -> list[str]:
    ms = er.models
    total_li = sum(m.facts["line_items"] for m in ms); total_cells = sum(m.facts["cells"] for m in ms)
    snaps = [m.facts["coverage"]["snapshot_actions"] for m in ms if m.facts["coverage"]["snapshot_actions"]]
    p1 = (f"This report reads {len(ms)} Anaplan model{'s' if len(ms) != 1 else ''}: {_n(total_li)} line items and {_c(total_cells)} cells as exported. "
          f"Inputs are the Line Items, Modules and Actions grid exports; "
          + (f"the latest recorded action run across the files is {max(snaps)}, the closest the exports come to a snapshot date. " if snaps else "no Actions export gives a snapshot date. ")
          + f"The analysis was generated on {rep['generated']}. Everything below is an automated reading of those files: observations first, then candidate investigations, never a verdict on what the business needs.")
    p2 = ("What stands out is set out in the observations, and the three investigations that follow are where the evidence is strongest and the footprint largest. "
          "Each says what was observed, why it deserves attention, and what to do next. Where the exports cannot see a consumer, the finding says so and lists the checks that remain, because a module read only by a page is not spare.")
    p3 = ("Two limits shape everything here. The exports carry formulas, dimensions, actions and Anaplan's own Referenced By column, but not pages, saved views, line item subsets or integrations. "
          "And calculation effort is a measurement of where the engine spends time in one model, not a promise of what removal would save. "
          "Findings are labelled confirmed, partial or inferred on exactly that basis, and a benefit is stated only where the exports support it.")
    return [p1, p2, p3]


# ---------------------------------------------------------------- build

def build(er, service_url: str | None = None, contact: str | None = None) -> dict:
    ms = er.models
    fs = er.findings
    rep = {"title": f"Anaplan estate: {len(ms)} model{'s' if len(ms) != 1 else ''}", "generated": er.generated, "description": DESCRIPTION,
           "service_url": service_url or "", "contact": contact or ""}
    rep["scope"] = {"models": len(ms), "line_items": sum(m.facts["line_items"] for m in ms), "calculated": sum(m.facts["calculated"] for m in ms),
                    "cells": sum(m.facts["cells"] for m in ms), "findings": len(fs),
                    "parse_rate": round(1 - sum(m.facts["parse_errors"] for m in ms) / max(sum(m.facts["calculated"] for m in ms), 1), 4)}
    rep["observations"] = _observations(er)
    rep["priorities"] = _priorities(er)
    rep["limitations"] = _limitations(er)
    rep["summary_text"] = _summary_text(er, rep)
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
    return rep


# ---------------------------------------------------------------- register

REGISTER_COLS = ["id", "area", "title", "model", "importance", "strength", "complexity", "benefit_kind", "footprint_cells", "footprint_effort", "scope", "benefit", "next_step", "objects", "rules", "related"]


def register_rows(rep: dict) -> list[dict]:
    rows = []
    for x in rep["findings"]:
        r = {k: x.get(k, "") for k in REGISTER_COLS}
        r["area"] = AREA_LABEL.get(x["area"], x["area"])
        r["objects"] = "; ".join(x["objects"]); r["rules"] = "; ".join(x["rules"]); r["related"] = "; ".join(x["related"])
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
    out = [f"### {x['id']}. {x['title']}", "",
           f"Objects: {', '.join('`' + o + '`' for o in x['objects'])}", "",
           f"| Importance | Evidence | Change complexity | Model |", "|---|---|---|---|",
           f"| {x['importance']} | {x['strength']} | {x['complexity']} | {x['model']} |", "",
           f"**Observed.** {x['observed']}", "", f"**Why it matters.** {x['why']}", "",
           f"**Affected scope.** {x['scope']}", "", f"**Potential benefit.** {x['benefit']}", "",
           f"**Evidence strength.** {x['strength']}: {x['basis']}", ""]
    if x["missing"]:
        out += ["**Missing information.**", ""] + [f"- {mi}" for mi in x["missing"]] + [""]
    out += [f"**Next step.** {x['next_step']}", "", f"**When keeping the current design is reasonable.** {x['keep_design']}", ""]
    if x["related"]:
        out += [f"Alternative to: {', '.join(x['related'])}.", ""]
    if x["evidence"]:
        out += ["**Evidence**", ""] + x["evidence"] + [""]
    if x["validation"]:
        out += ["**Validation**", ""] + [f"- {v}" for v in x["validation"]] + [""]
    return out


def render_markdown(er) -> str:
    rep = build(er)
    fmap = {x["id"]: x for x in rep["findings"]}
    out = [f"# {rep['title']}", "", f"{rep['description']} Generated {rep['generated']}.", "", "## Summary", ""]
    out += [p + "\n" for p in rep["summary_text"]]
    out += ["**Observations**", ""] + [f"{i}. {o}" for i, o in enumerate(rep["observations"], 1)] + [""]
    if rep["priorities"]:
        out += ["**Priority investigations**", ""]
        for p in rep["priorities"]:
            out += [f"- **{p['title']}** ({p['model']}; [{p['id']}](#{p['id']})). Observed: {p['observed']} Why: {p['why']} Next: {p['next']}"]
        out.append("")
    out += ["**Coverage limitations**", ""] + [f"- {l}" for l in rep["limitations"]] + [""]
    if rep["map"]["edges"]:
        out += ["**Model map (feeds inferred from import action names)**", "", "```mermaid", "flowchart LR"]
        ids = {n["name"]: f"M{i}" for i, n in enumerate(rep["map"]["nodes"])}
        for n in rep["map"]["nodes"]:
            out.append(f"  {ids[n['name']]}[\"{n['name']} ({_c(n['cells'])} cells)\"]")
        for e in rep["map"]["edges"]:
            out.append(f"  {ids[e['from']]} -.->|{e['actions']} inferred| {ids[e['to']]}")
        out += ["```", ""]
    out += ["Have a change planned in this area? Use the estate analysis service to investigate affected dependencies, review the evidence and develop a validation plan." + (f" {rep['service_url']}" if rep["service_url"] else ""), ""]
    out += ["# Findings", ""]
    for a in rep["areas"]:
        out += [f"## {a['label']}", "", a["blurb"], ""]
        for fid in a["ids"]:
            out += _finding_md(fmap[fid])
    out += ["# Reference", "", "## Findings register", "", "| ID | Area | Title | Model | Importance | Evidence | Complexity | Footprint cells | Effort share |", "|---|---|---|---|---|---|---|---|---|"]
    for r in register_rows(rep):
        out.append(f"| {r['id']} | {r['area']} | {r['title']} | {r['model']} | {r['importance']} | {r['strength']} | {r['complexity']} | {_c(r['footprint_cells'])} | {r['footprint_effort']} |")
    out += ["", "## Models and coverage", ""]
    for m in rep["models"]:
        f, cov = m["facts"], m["coverage"]
        out += [f"### {m['name']}", "", "| | |", "|---|---|",
                f"| Files supplied | {', '.join(k for k, v in cov['files'].items() if v)} |",
                f"| Actions snapshot (latest recorded run) | {cov['snapshot_actions'] or 'no Actions export'} |",
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
    return "\n".join(out)
