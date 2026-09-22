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


def _investigations(er) -> list[dict]:
    """Up to three distinct investigations, each backed by findings:
      1 principal calculation hotspots in the model with the largest measured effort concentration;
      2 whether the large modules with no consumer detected remain necessary (all models, one card, details per model);
      3 the largest exact-duplicate calculation group.
    A card is only produced when the evidence exists; nothing is manufactured. They can proceed independently."""
    fs = er.findings
    out = []
    eff = [x for x in fs if x.kind == "capacity" and x.rules == ["EFFORT"]]
    if eff:
        m = next(mm for mm in er.models if mm.name == eff[0].model)
        top = m.facts["effort_top"][0]
        related = [x.id for x in fs if x.model == m.name and x.kind in ("fix", "refactor") and x.footprint_effort]
        out.append({"key": "hotspots", "title": f"Investigate {m.name}'s principal calculation hotspots",
                    "sentence": f"Ten line items carry {m.facts['effort_top10_share']}% of {m.name}'s measured calculation effort, led by {top[0]} at {top[1]:.1f}%.",
                    "who": "model builder who owns " + m.name, "next": "Read the formulas of the top five and match each against the findings that name it; choose one to trial in a development copy.",
                    "ids": [eff[0].id] + related[:3], "model": m.name})
    usage = [x for x in fs if x.area == "usage" and "with no consumer detected in the inspected" in x.title and x.counts_benefit]
    if usage:
        usage.sort(key=lambda x: -(x.footprint_cells or 0))
        cells = sum(x.footprint_cells or 0 for x in usage); n = sum(int(x.object_label.split()[0]) for x in usage)
        per_model = [{"model": x.model, "id": x.id, "modules": int(x.object_label.split()[0]), "cells": x.footprint_cells or 0, "effort": x.footprint_effort, "top": x.objects[:2], "strength": x.strength} for x in usage]
        out.append({"key": "usage", "title": "Establish whether the large modules nothing reads remain necessary",
                    "sentence": f"{n} modules across {len(usage)} model{'s' if len(usage) != 1 else ''} hold {_c(cells)} cells with no formula or export consumer in the exports; each needs a consumer check before any keep-or-retire decision.",
                    "who": "model owner with a page builder", "next": "Complete the consumer and retention checks for the largest modules in each model, then record a keep-or-retire recommendation per module.",
                    "ids": [x.id for x in usage], "per_model": per_model, "model": "all models"})
    dup = [x for x in fs if x.kind == "merge" and x.rules == ["REDUNDANT-EXACT"]]
    if dup:
        dup.sort(key=lambda x: -(x.footprint_cells or 0))
        x = dup[0]
        m = next(mm for mm in er.models if mm.name == x.model)
        g = m.redundancy.exact[0]
        out.append({"key": "duplicates", "title": "Validate one substantial duplicate-calculation group",
                    "sentence": f"In {x.model}, {x.object_label}; the largest group repeats {g['items'][0]['key']} {len(g['items']) - 1} more time{'s' if len(g['items']) != 2 else ''} ({_c(g['redundant_cells'])} cells).",
                    "who": "model builder who owns " + x.model, "next": "Validate equivalence and the reasons for separate objects in that group, then decide whether consolidation is appropriate.",
                    "ids": [x.id], "model": x.model})
    return out


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
        out.append(f"No Actions export for {', '.join(no_actions)}: imports, exports and feeds not analysed there.")
    out.append("Export date unknown for every file; the latest recorded action run is not an export date.")
    return out


def _summary_text(er, rep) -> list[str]:
    ms = er.models
    total_li = sum(m.facts["line_items"] for m in ms); total_cells = sum(m.facts["cells"] for m in ms)
    snaps = [m.facts["coverage"]["snapshot_actions"] for m in ms if m.facts["coverage"]["snapshot_actions"]]
    p1 = (f"{len(ms)} Anaplan model{'s' if len(ms) != 1 else ''}, {_n(total_li)} line items, {_c(total_cells)} cells as exported. "
          f"Export date unknown. " + (f"Latest recorded action run: {max(snaps)}. " if snaps else "") + f"Analysis generated {rep['generated']}. "
          "Read from the exports only; pages, saved views and subsets are not in them, so 'no consumer detected' is a question, not a saving.")
    p2 = ("The investigations below were chosen for footprint and evidence strength and can proceed independently. "
          "Reference findings are hidden until asked for.")
    return [p1, p2]


def _example(er) -> dict | None:
    """Illustrative progression from a proposed change to a validation plan, built from the exports: the widest-read line
    item in the largest model. Labelled illustrative; no analysis beyond the exports has been run."""
    ms = [m for m in er.models if m.facts["hubs"]]
    if not ms:
        return None
    m = max(ms, key=lambda x: x.facts["cells"])
    name, n = m.facts["hubs"][0]
    key = tuple(name.split(".", 1))
    g = m.graph
    imp = g.impact(key) if key in m.model.line_items else {}
    mods = {k[0] for k in imp}
    exports = [a.name for a in m.actions.actions.values() if a.kind == "export" and a.target in mods]
    downstream = sorted({e["to"] for e in er.edges if e["from"] == m.name})
    return {"change": f"Change the formula of {name} in {m.name}.",
            "evidence": f"{n} formulas read it directly and {len(imp)} line items across {len(mods)} modules depend on it transitively (parsed references, checked against Referenced By at {m.facts['referenced_by_check']['agreement']:.0%} agreement)"
                        + (f"; {len(exports)} export action{'s' if len(exports) != 1 else ''} read those modules" if exports else "; no export action reads those modules")
                        + (f"; {m.name} feeds {', '.join(downstream)} by inferred import actions" if downstream else "") + ".",
            "context": "Pages and saved views that show any of the dependent line items; line item subsets that include them; whether the exports feed another model's import; the owner's acceptance criteria for the outputs.",
            "plan": "Compare the dependent outputs the owner names between a development copy and production before and after the change; reconcile the exports read by other models; sign-off by the model owner before promotion.",
            "model": m.name, "hub": name}


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
    rep["investigations"] = _investigations(er)
    rep["steps"] = rep["investigations"]
    rep["priorities"] = rep["investigations"]
    rep["metrics"] = {"models": len(ms), "review_first": sum(1 for x in fs if x.importance in ("high", "medium")),
                      "reference": sum(1 for x in fs if x.importance == "low"), "validated_defects": 0,
                      "observations": sum(1 for x in fs if x.kind_label == "observation")}
    rep["example"] = _example(er)
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

REGISTER_COLS = ["id", "area", "title", "model", "kind_label", "importance", "strength", "complexity", "benefit_kind", "footprint_cells", "footprint_effort", "object_label", "scope", "benefit", "next_step", "objects", "rules", "related"]


def register_rows(rep: dict) -> list[dict]:
    rows = []
    for x in rep["findings"]:
        r = {k: ("" if x.get(k) is None else x.get(k, "")) for k in REGISTER_COLS}
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
    ex = x["objects"][:3]; more = len(x["objects"]) - len(ex)
    out = [f"### {x['id']}. {x['title']}", "",
           f"{x['model']} · {x['kind_label']} · importance {x['importance']} · evidence {x['strength']} · complexity {x['complexity']}", "",
           f"Examples: {', '.join('`' + o + '`' for o in ex)}" + (f" and {more} more ({x['object_label']})" if more > 0 else f" ({x['object_label']})"), "",
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
    out += ["**All affected objects.** " + ", ".join("`" + o + "`" for o in x["objects"]), ""]
    if x["evidence"]:
        out += ["**Evidence**", ""] + x["evidence"] + [""]
    if x["validation"]:
        out += ["**Validation**", ""] + [f"- {v}" for v in x["validation"]] + [""]
    out += ["</details>", ""]
    return out


def render_markdown(er) -> str:
    rep = build(er)
    fmap = {x["id"]: x for x in rep["findings"]}
    out = [f"# {rep['title']}", "", f"{rep['description']} Generated {rep['generated']}.", "", "## Summary", ""]
    out += [p + "\n" for p in rep["summary_text"]]
    out += ["**Observations**", ""] + [f"{i}. {o}" for i, o in enumerate(rep["observations"], 1)] + [""]
    if rep["investigations"]:
        out += ["**Priority investigations**", ""]
        for i, p in enumerate(rep["investigations"], 1):
            out += [f"{i}. **{p['title']}.** {p['sentence']} Who: {p['who']}. Next: {p['next']} Findings: {', '.join(f'[{x}](#{x})' for x in p['ids'])}."]
            for pm in p.get("per_model", []):
                out.append(f"   - {pm['model']}: {pm['modules']} modules, {_c(pm['cells'])} cells" + (f", {pm['effort']:.1f}% effort" if pm['effort'] else "") + f"; largest {', '.join('`' + t + '`' for t in pm['top'])} ([{pm['id']}](#{pm['id']}))")
        out.append("")
    mt = rep["metrics"]
    out += [f"{mt['models']} models reviewed · {mt['review_first']} findings to review first · {mt['reference']} additional reference findings. No finding is a validated defect; all are observations or review candidates.", ""]
    out += ["**Coverage limitations**", ""] + [f"- {l}" for l in rep["limitations"]] + [""]
    if rep["map"]["edges"]:
        out += ["**Model map (feeds inferred from import action names)**", "", "```mermaid", "flowchart LR"]
        ids = {n["name"]: f"M{i}" for i, n in enumerate(rep["map"]["nodes"])}
        for n in rep["map"]["nodes"]:
            out.append(f"  {ids[n['name']]}[\"{n['name']} ({_c(n['cells'])} cells)\"]")
        for e in rep["map"]["edges"]:
            out.append(f"  {ids[e['from']]} -.->|{e['actions']} inferred| {ids[e['to']]}")
        out += ["```", ""]
    out += ["Have a change planned in this estate? Request a review of one proposed change: the dependencies visible in your exports, what still needs checking, and a validation plan with your model owner."
            + (f" Request a change-impact review: {rep['service_url']}" if rep["service_url"] else " (Request route not configured in this report.)"), ""]
    ex = rep.get("example")
    if ex:
        out += ["Illustrative example (from the exports; no further analysis has been run):", "",
                f"- Proposed change: {ex['change']}", f"- Dependency evidence examined: {ex['evidence']}", f"- Additional context required: {ex['context']}", f"- Validation plan that would result: {ex['plan']}", ""]
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
    return "\n".join(out)
