"""The catalogue of checks: every test the engine runs on an estate, numbered by category.

This is the one place the list lives. The home page, the README (docs/CHECKS.md is generated
from here), the report's "Checks run" table and the check numbers on each finding all read it,
so what a visitor is told will be tested is what is tested.

Numbers are append-only: a published number never moves to another check. A new check takes the
next number in its category.

A check is tied to the engine in one of three ways:
  rules   lint rule ids (lint.RULES); hits are the rule's findings
  tags    ids carried by findings built outside the lint rules (findings.py, redundancy.py)
  fact    a model or estate fact computed in fleet.py, reported without a finding

`needs` names what the check cannot run without: "actions", "modules" (the optional exports),
"effort", "cells", "referenced_by", "summary" (columns of the Line Items export).
"""
from __future__ import annotations
from dataclasses import dataclass


@dataclass(frozen=True)
class Category:
    num: int
    key: str
    title: str
    blurb: str


@dataclass(frozen=True)
class Check:
    num: str                       # "4.16"
    key: str                       # stable slug; code refers to checks by key, never by number
    title: str                     # plain language, what is looked for
    what: str                      # one sentence: exactly what is tested, with the threshold
    rules: tuple[str, ...] = ()    # lint rule ids
    tags: tuple[str, ...] = ()     # finding rule tags outside lint
    fact: str = ""                 # fact key, for checks reported without a finding
    needs: tuple[str, ...] = ()
    planual: tuple[str, ...] = ()
    scope: str = "model"           # model | estate (needs two or more models)

    @property
    def category(self) -> int:
        return int(self.num.split(".")[0])


CATEGORIES = [
    Category(1, "performance", "Performance and size", "Where calculation time and cells go, and the formula patterns Anaplan documents as expensive."),
    Category(2, "usage", "Usage and leftovers", "What nothing appears to read: candidates to ask about, never verdicts."),
    Category(3, "dependencies", "Dependencies and change impact", "What depends on what, inside a model and between models."),
    Category(4, "maintainability", "Correctness and maintainability", "Totals that may be wrong, repeated logic, and formulas the next builder has to decode."),
    Category(5, "integration", "Imports, exports and processes", "What loads the model, what has stopped running, what sits outside every process."),
    Category(6, "quality", "How far to trust the analysis", "Checks the report runs on itself, so every finding says how strong its evidence is."),
]

NEEDS_TEXT = {"actions": "the Actions export", "modules": "the Modules export", "effort": "the Calculation Effort column", "cells": "the Cell Count column",
              "referenced_by": "the Referenced By column", "summary": "the Summary column"}

CHECKS = [
    # ---- 1 performance
    Check("1.1", "effort-concentration", "Where calculation effort concentrates",
          "The line items and modules carrying the largest share of Anaplan's measured Calculation Effort, and the share held by the top ten.", tags=("EFFORT",), needs=("effort",), planual=("2.03-07",)),
    Check("1.2", "sum-lookup", "SUM combined with LOOKUP or SELECT",
          "A formula that aggregates (SUM) and looks up or selects in the same formula, which Anaplan documents as slow.", rules=("F-MIXED-CLAUSE",), planual=("2.02-08", "2.02-14")),
    Check("1.3", "large-text", "Large text line items", "A text-formatted line item with more than 50,000 cells.", rules=("A-TEXT-FORMAT",), needs=("cells",), planual=("2.03-02",)),
    Check("1.4", "finditem", "FINDITEM on a large line item", "FINDITEM in a line item with 10,000 cells or more.", rules=("A-FINDITEM",), needs=("cells",), planual=("2.02-15",)),
    Check("1.5", "text-join", "Text joins on a large line item", "Text concatenation (&) in a line item with 10,000 cells or more.", rules=("A-TEXT-JOIN",), needs=("cells",), planual=("2.02-04", "2.02-05")),
    Check("1.6", "per-item-functions", "Per-item functions repeated on every cell",
          "PARENT, ITEM, NAME, CODE, START, END and similar in a line item with two or more dimensions and 5,000 cells or more, where a one-dimension system module would compute the answer once.",
          rules=("A-SYSTEMS-FN",), needs=("cells",), planual=("2.01-08", "2.01-09")),
    Check("1.7", "over-dimensioned", "Line items with a dimension their formula does not use",
          "A calculated line item of 10,000 cells or more that applies to a list, Time or Versions that nothing in its formula varies over: the dimension multiplies cells without changing the value.",
          rules=("G-OVERDIM",), needs=("cells",), planual=("2.01-20",)),
    Check("1.8", "cell-concentration", "Where the cells are", "The modules and line items holding the largest share of the model's cells.", tags=("CELLS",), needs=("cells",)),
    # ---- 2 usage
    Check("2.1", "unread-modules", "Modules nothing reads",
          "A module with two or more calculated line items that no formula outside it reads and no export action uses.", tags=("USAGE-MODULE",)),
    Check("2.2", "unread-module-twin", "Unread modules that repeat a module in use",
          "An unread module whose calculated line items match, in formula and context, line items of a module that is read, with the share matched.", tags=("USAGE-TWIN",)),
    Check("2.3", "unread-line-items", "Calculated line items nothing reads",
          "A calculated line item of 50,000 cells or more that no formula reads.", rules=("G-UNUSED",), needs=("cells",)),
    Check("2.4", "import-target-unread", "Data loaded but never read",
          "A module that an import action loads, none of whose line items is read by any formula or used by an export action.", tags=("IMPORT-UNREAD",), needs=("actions",)),
    Check("2.5", "leftover-names", "Names that say leftover",
          "Modules, line items, actions and referenced list items whose name carries a leftover marker (OLD, TEMP, COPY, BACKUP, DO NOT USE, v2, 'Copy of', default names), with whether anything still reads them.",
          rules=("H-LEFTOVER",), tags=("LEFTOVER-ACTION",)),
    # ---- 3 dependencies
    Check("3.1", "hubs", "Line items with the widest change impact", "A line item read directly by 25 or more formulas, with its full downstream reach.", rules=("G-HUB",)),
    Check("3.2", "pass-through-chains", "Pass-through chains", "Three or more line items in a row that only copy the one before.", rules=("A-DAISY",), planual=("2.02-19",)),
    Check("3.3", "circular", "Circular references", "Line items that depend on each other: a balance pattern through a time offset, or a reference the parser may have misread.", rules=("G-CYCLE",)),
    Check("3.4", "model-feeds", "Which model feeds which", "Model-to-model feeds, inferred from the names of import actions.", fact="edges", needs=("actions",), scope="estate"),
    Check("3.5", "shared-dimensions", "Dimensions shared across models", "List names used as a dimension in more than one model.", fact="shared_dims", scope="estate"),
    # ---- 4 correctness and maintainability
    Check("4.1", "exact-duplicates", "The same calculation under two names",
          "Line items with the same resolved formula and the same dimensions, time scale, time range, versions, format, summary and formula scope.", tags=("REDUNDANT-EXACT",)),
    Check("4.2", "aliases", "Line items that only copy another", "A formula that is a single reference to a line item with identical context.", tags=("REDUNDANT-ALIAS",)),
    Check("4.3", "near-twins", "Formulas that differ in exactly one place", "Two line items in different modules with the same formula shape and context, differing in one constant, reference or list item.", tags=("REDUNDANT-NEAR",)),
    Check("4.4", "same-text", "Identical formula text that cannot be compared", "Identical formula text where COLLECT() or a blank context field stops the comparison; listed so it is not read as a duplicate.", tags=("REDUNDANT-SAME-TEXT",)),
    Check("4.5", "cross-model-duplicates", "The same line item and formula in more than one model", "A line item name with the same formula tree in two or more models.", tags=("DUP-CROSS",), scope="estate"),
    Check("4.6", "if-count", "Formulas with more than 10 IFs", "More than 10 IF THEN ELSE in one formula, with the lookup table the chain encodes where there is one.", rules=("A-IF-COUNT",), planual=("2.02-01", "2.02-02")),
    Check("4.7", "hard-coded-numbers", "Hard-coded numbers in formulas", "Numeric literals other than structural ones (0, 1, 12, 100 and similar) and function arguments.", rules=("F-HARDCODE",), planual=("2.01-09", "2.02-12")),
    Check("4.8", "long-formulas", "Very long formulas", "A formula of more than 120 tokens.", rules=("F-LONG",), planual=("2.02-02", "2.02-18")),
    Check("4.9", "select-fixed-period", "SELECT on a fixed period or version", "SELECT naming a specific time period or version.", rules=("F-SELECT-TIME",), planual=("2.02-12", "2.02-14")),
    Check("4.10", "divide-fn", "DIVIDE() where a zero divisor shows Infinity", "DIVIDE() present: it returns Infinity on a zero divisor where / returns zero.", rules=("F-DIVIDE-FN",)),
    Check("4.11", "subsidiary-views", "Subsidiary views used in calculation", "A line item dimensioned differently from its module and read by formulas.", rules=("A-SUBSIDIARY",), planual=("2.01-06",)),
    Check("4.12", "summaries-unread", "Summaries on line items nothing reads", "A number line item of 10,000 cells or more with a summary method and no formula reader.", rules=("A-SUMMARY-ON",), needs=("cells", "summary"), planual=("2.01-10", "2.03-01")),
    Check("4.13", "large-modules", "Modules with more than 50 line items", "A module holding more than 50 line items.", rules=("A-LI-COUNT",), planual=("2.01-12",)),
    Check("4.14", "empty-modules", "Empty modules", "A module with no line items.", rules=("G-EMPTY-MODULE",)),
    Check("4.15", "module-notes", "Modules without notes", "How many modules carry no notes, largest first.", rules=("H-NOTES",), needs=("modules",)),
    Check("4.16", "ratio-summed", "Ratios whose totals are added up",
          "A line item that divides one amount by another (or is formatted as a percentage) and has the summary method Sum, so every total is the sum of the ratios below it and not the ratio of the totals.",
          rules=("F-RATIO-SUM",), needs=("summary",)),
    Check("4.17", "odd-one-out", "The odd one out in a run of matching formulas",
          "Five or more neighbouring line items in a module share one formula shape and exactly one among them differs: a different shape, no formula at all, or one reference its siblings do not share.",
          rules=("F-ODD-ONE",)),
    # ---- 5 integration
    Check("5.1", "actions-outside-process", "Imports and exports outside every process", "An import or export action that is in no process.", tags=("ACTIONS-NO-PROCESS",), needs=("actions",)),
    Check("5.2", "actions-stale", "Imports and exports with no recent run", "No recorded run in the 12 months before the latest run in the export.", tags=("ACTIONS-STALE",), needs=("actions",)),
    Check("5.3", "actions-never-run", "Imports and exports never run", "No recorded run at all.", tags=("ACTIONS-NEVER",), needs=("actions",)),
    Check("5.4", "several-imports-one-target", "Several imports loading one target", "A module or list loaded by two or more import actions, with the last run of each.", tags=("IMPORT-MULTI",), needs=("actions",)),
    # ---- 6 quality
    Check("6.1", "unparsed", "Formulas the parser did not follow", "Formulas whose references are therefore missing from the dependency graph.", rules=("F-PARSE",)),
    Check("6.2", "referenced-by-agreement", "Agreement with Anaplan's own Referenced By",
          "The parsed dependency graph compared edge by edge with Anaplan's Referenced By column; below 95% every dependent finding is downgraded.", fact="referenced_by", needs=("referenced_by",)),
    Check("6.3", "input-guards", "Input checks on the files", "Delimiter, encoding and number format are detected; a missing column disables the checks that need it and is reported as unavailable, never as zero.", fact="input_notices"),
]

BY_KEY = {c.key: c for c in CHECKS}
BY_NUM = {c.num: c for c in CHECKS}
_BY_RULE: dict[str, str] = {}
for _c in CHECKS:
    for _r in _c.rules + _c.tags:
        _BY_RULE[_r] = _c.num


def _order(num: str) -> tuple[int, int]:
    a, b = num.split(".")
    return int(a), int(b)


def N(key: str) -> str:
    """The published number of a check, by its key."""
    return BY_KEY[key].num


def for_rules(rules) -> list[str]:
    """Check numbers for a list of rule ids or finding tags, in catalogue order, without repeats."""
    return sorted({_BY_RULE[r] for r in rules if r in _BY_RULE}, key=_order)


def by_category() -> list[tuple[Category, list[Check]]]:
    return [(cat, [c for c in CHECKS if c.category == cat.num]) for cat in CATEGORIES]


def catalogue() -> list[dict]:
    """JSON-safe catalogue for pages and reports."""
    return [{"num": cat.num, "key": cat.key, "title": cat.title, "blurb": cat.blurb,
             "checks": [{"num": c.num, "key": c.key, "title": c.title, "what": c.what, "needs": [NEEDS_TEXT[n] for n in c.needs],
                         "planual": list(c.planual), "scope": c.scope} for c in cs]} for cat, cs in by_category()]


def markdown() -> str:
    """docs/CHECKS.md, generated: `python -m anaplan_estate.checks > docs/CHECKS.md`."""
    out = ["# The checks", "",
           f"Every test the engine runs on an estate: {len(CHECKS)} checks in {len(CATEGORIES)} categories. Generated from `src/anaplan_estate/checks.py`; "
           "the report's *Checks run* table shows the result of each one on your exports.", "",
           "A check that needs an optional export or column says so; without it the check is reported as not run, never as clear. "
           "A hit is an observation or a review candidate, not a verdict.", ""]
    for cat, cs in by_category():
        out += [f"## {cat.num}. {cat.title}", "", cat.blurb, "", "| # | Check | What is tested | Needs |", "|---|---|---|---|"]
        for c in cs:
            needs = ", ".join(NEEDS_TEXT[n] for n in c.needs) + ("; two or more models" if c.scope == "estate" else "")
            out.append(f"| {c.num} | {c.title} | {c.what} | {needs.lstrip('; ')} |")
        out.append("")
    return "\n".join(out)


# ---------------------------------------------------------------- results on one estate

def _available(m, need: str) -> bool:
    f = m.facts
    return {"actions": bool(f.get("actions")), "modules": m.model.has_modules_export, "effort": f["has_effort"], "cells": f["has_cells"],
            "referenced_by": m.model.has("Referenced By"), "summary": m.model.has("Summary")}[need]


def results(er) -> list[dict]:
    """One row per check: hits in total and per model, the cells and effort share of the line items hit (per model;
    effort shares are never added across models), and where it could not run and why. The metrics are what a later
    selection of the top checks reads."""
    rows = []
    for c in CHECKS:
        per, not_run, fids = [], [], []
        for m in er.models:
            missing = [NEEDS_TEXT[n] for n in c.needs if not _available(m, n)]
            if missing:
                not_run.append({"model": m.name, "why": "needs " + " and ".join(missing)})
                continue
            hits, keys, objs = 0, set(), set()
            for x in m.lint.findings:
                if x.rule in c.rules:
                    hits += 1
                    objs.update((x.object, x.module))
                    if x.line_item:
                        keys.add((x.module, x.line_item))
            for fd in er.findings:
                if fd.model != m.name or c.num not in fd.checks:
                    continue
                hits += fd.hits.get(c.num, 0)
                if fd.hits.get(c.num, 0) or objs & set(fd.objects):
                    fids.append(fd.id)
            if c.fact == "referenced_by":
                hits = m.facts["referenced_by_check"]["anaplan_only"] + m.facts["referenced_by_check"]["ours_only"]
            elif c.fact == "input_notices":
                hits = len(m.facts["warnings"]) + len([x for x in m.model.missing_columns if x != "Module Name"])
            lis = [m.model.line_items[k] for k in keys if k in m.model.line_items]
            tagged = [fd.footprint_cells for fd in er.findings if fd.model == m.name and c.num in fd.hits and fd.footprint_cells]
            per.append({"model": m.name, "hits": hits, "cells": sum(li.cell_count for li in lis) if lis else (sum(tagged) if tagged else None),
                        "effort": round(sum(li.calc_effort for li in lis), 2) if lis and m.facts["has_effort"] else None})
        estate_hits = 0
        if c.scope == "estate":
            estate_hits = sum(fd.hits.get(c.num, 0) for fd in er.findings if fd.model == "Estate")
            fids += [fd.id for fd in er.findings if fd.model == "Estate" and fd.hits.get(c.num, 0)]
            if c.fact == "edges":
                estate_hits = len(er.edges)
            elif c.fact == "shared_dims":
                estate_hits = len(er.shared_dims)
            if len(er.models) < 2:
                not_run = [{"model": "Estate", "why": "needs two or more models"}]
                per = []
        total = estate_hits if c.scope == "estate" else sum(p["hits"] for p in per)
        ran = bool(per) if c.scope == "model" else len(er.models) >= 2 and not (c.needs and len(not_run) == len(er.models))
        rows.append({"num": c.num, "key": c.key, "category": c.category, "title": c.title, "what": c.what, "scope": c.scope,
                     "status": ("not run" if not ran else "found" if total else "clear"), "hits": total,
                     "by_model": [p for p in per if p["hits"]], "not_run": not_run,
                     "findings": sorted(set(fids), key=lambda i: int(i[1:]))})
    return rows


if __name__ == "__main__":
    import sys
    sys.stdout.reconfigure(encoding="utf-8", newline="\n")
    print(markdown())
