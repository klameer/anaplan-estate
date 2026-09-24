"""Turn facts and rule results into findings a team can act on.

A finding is an observation from the exports, why it matters, what it
affects, what benefit is supportable (or that none is), how strong the
evidence is and what is missing, one next step, and the reasons the current
design may be right. Observations, hypotheses and recommendations are kept
apart: `observed` is what the files show; `why` and `next_step` are the
analyst's reading; `keep_design` is the case against the change.

Benefit vocabulary:
  footprint    what the objects occupy now (cells; share of measured
               calculation effort in THEIR model). Not a saving.
  conditional  what would be released if the investigation confirms the
               objects can go. Stated as "if confirmed".
  none         not quantified from the exports; said so.

Effort figures are per model and never added across models: Classic measures
effort across the whole model at open; Polaris measures a rolling ten-minute
window; the exports do not say which engine produced the column.

Overlapping findings (retire a module vs review its size) are linked as
alternatives and only one carries the footprint.

Ordering within an area is by importance (high, medium, low), then by
evidence strength, then by footprint. No numeric score is shown.
"""
from __future__ import annotations
from dataclasses import dataclass, field, asdict
from collections import defaultdict, Counter
import re
from anaplan_grammar.parser import parse
from anaplan_grammar.unparse import unparse
from .lint import RULES, DOCS

AREAS = [
    ("capacity", "Potential capacity or performance improvements", "Where cells and measured calculation effort concentrate, and what could be released if an investigation confirms it."),
    ("usage", "Usage and retirement investigations", "Objects with no consumer detected in the inspected dependency types. Pages, saved views and subsets are not in the exports, so each carries outstanding checks."),
    ("dependency", "Dependencies and change impact", "Where a change spreads widest: hubs, chains, cross-model feeds."),
    ("maintain", "Maintainability and consistency", "Repeated logic, hard-coded assumptions, long formulas, structure that the next builder has to decode."),
    ("integration", "Integration and operational review", "Imports, exports and processes: what runs, what has no recorded run, what feeds what."),
]
AREA_LABEL = {k: t for k, t, _ in AREAS}
LEGACY_CATEGORY = {"retire": "usage", "merge": "maintain", "collapse": "maintain", "schedule": "integration", "fix": "capacity",
                   "refactor": "maintain", "tidy": "maintain", "dedupe": "maintain", "hub": "dependency", "capacity": "capacity"}
IMPORTANCE_ORDER = {"high": 0, "medium": 1, "low": 2}
STRENGTH_ORDER = {"confirmed": 0, "partial": 1, "inferred": 2}

STRENGTH_TEXT = {
    "confirmed": "Everything this finding relies on is in the exports and was checked against Anaplan's Referenced By column.",
    "partial": "Formulas, imports and exports are in the exports; pages, saved views, line item subsets and integrations are not, and can hold consumers.",
    "inferred": "Rests on names or on a comparison the exports cannot fully resolve. A hypothesis to test, not an observation.",
}


@dataclass
class Finding:
    id: str
    area: str                 # key of AREAS
    kind: str                 # legacy category: retire | merge | collapse | schedule | fix | refactor | tidy | dedupe | hub | capacity
    title: str                # short, descriptive, no object names
    model: str
    objects: list[str]        # full technical names
    observed: str             # what the exports show
    why: str                  # why it matters to the team
    scope: str                # affected scope, in words
    benefit: str              # supportable benefit, or "not quantified from the exports"
    benefit_kind: str         # footprint | conditional | none
    strength: str             # confirmed | partial | inferred
    basis: str                # what the strength rests on
    missing: list[str]        # what the exports cannot tell, object-specific where possible
    next_step: str            # one practical step
    keep_design: str          # when keeping the current design is reasonable
    importance: str           # high | medium | low
    complexity: str           # low | medium | high (change complexity)
    evidence: list[str] = field(default_factory=list)   # markdown lines; tables allowed; complete
    validation: list[str] = field(default_factory=list) # how to prove a change worked
    rules: list[str] = field(default_factory=list)
    related: list[str] = field(default_factory=list)    # ids of alternative or overlapping findings
    footprint_cells: int | None = None                   # None = not applicable or not measured (never a zero)
    footprint_effort: float | None = None                # share of THIS model's measured effort; None = unavailable
    counts_benefit: bool = True                          # False when an alternative carries the footprint
    summary: str = ""                                    # one sentence for the compact view (defaults to the first sentence of observed)
    object_label: str = ""                               # accurate count label, e.g. "217 groups; 512 duplicate line items"
    implementation: list[str] = field(default_factory=list)  # change guidance with explicit prerequisites; kept apart from the next investigation step
    kind_label: str = "review candidate"                 # observation | review candidate
    preview: list[str] = field(default_factory=list)     # the few objects shown before the full list; never the scope itself
    preview_label: str = ""                              # "Showing 3 of 32 modules" / "All 4 modules"
    unit: str = "objects"                                # noun for counts of `objects`
    action_usage: str = "none detected"                  # none detected | not assessed (no Actions export) | n/a
    uid: str = ""                                        # report-scoped stable identity (model + rules + leading object); survives renumbering

    def to_dict(self):
        return asdict(self)


def _c(x) -> str:
    if not isinstance(x, (int, float)):
        return str(x)
    for div, suf in ((1e9, "B"), (1e6, "M"), (1e3, "K")):
        if abs(x) >= div:
            v = x / div
            return f"{v:.0f}{suf}" if v >= 100 else f"{v:.1f}{suf}"
    return f"{x:,}"


def _pl(n, word):
    return f"{n:,} {word}{'' if n == 1 else 's'}"


def _q(name: str) -> str:
    return f"`{name}`"


def _footprint(cells: int, effort: float, model: str, has_effort: bool) -> str:
    parts = []
    if cells:
        parts.append(f"{_c(cells)} cells as exported")
    if effort and has_effort:
        parts.append(f"{effort:.1f}% of {model}'s measured calculation effort")
    return "; ".join(parts) if parts else "no footprint measured"


def _effort_note(m) -> str:
    return ("Effort shares are Anaplan's Calculation Effort column for this model only. The engine is not in the export: "
            "Classic measures across the whole model at open, Polaris over the last ten minutes. A share of effort is not a promise of faster recalculation after removal.")


# ---------------------------------------------------------------- per model

def _exports_on(m, module: str) -> list[str]:
    return [a.name for a in m.actions.actions.values() if a.kind == "export" and a.target == module]


def _readers_outside(g, keys, module=None) -> int:
    return sum(1 for k in keys for a in g.rev.get(k, ()) if module is None or a[0] != module)


def _if_mapping(formula: str) -> list[tuple[str, str]] | None:
    try:
        n = parse(formula)
    except Exception:
        return None
    rows = []
    while isinstance(n, dict) and n.get("t") == "if":
        c = n["c"]
        if not (c.get("t") == "bin" and c["op"] == "=" and c["l"].get("t") == "call" and c["l"]["f"] == "ITEM" and c["r"].get("t") == "ref"):
            return None
        rows.append((".".join(c["r"]["path"]), unparse(n["a"])))
        n = n["b"]
    return rows if len(rows) >= 3 else None


def _usage_checks(mod: str, has_modules: bool, imported_into: bool, exported: bool) -> list[str]:
    out = [f"UX pages and classic dashboards that show {_q(mod)} (no export exists; the page builder or the Modules export's Used in Dashboards column for classic dashboards" + (")" if has_modules else "; the Modules export was not supplied)")]
    out.append(f"saved views on {_q(mod)}: another model can import from a saved view without any export action existing here")
    out.append(f"line item subsets that include line items of {_q(mod)} (COLLECT sources are not in the export)")
    out.append("filters, access drivers, DCA and integration (CloudWorks, API) references")
    if imported_into:
        out.append(f"{_q(mod)} is an import target: retained data may be needed even if no formula reads it")
    return out


def _agreement_ok(m) -> bool:
    a = m.facts["referenced_by_check"]["agreement"]
    return a is None or a >= 0.95


def _per_model(er, m, nid) -> list[Finding]:
    out: list[Finding] = []
    g, model, f, red = m.graph, m.model, m.facts, m.redundancy
    has_effort = f["has_effort"]
    by_rule = defaultdict(list)
    for x in m.lint.findings:
        by_rule[x.rule].append(x)
    export_sources = set((f.get("actions") or {}).get("export_sources", []))
    has_actions = bool(f.get("actions"))
    action_usage = "none detected" if has_actions else "not assessed (no Actions export)"
    export_clause = "no export action reads them" if has_actions else "export-action usage is not assessed (no Actions export was supplied)"
    has_modules = model.has_modules_export
    agree = f["referenced_by_check"]["agreement"]
    coverage_note = (f"Dependency coverage for {m.name}: parsed-formula edges agree with Anaplan's Referenced By at {agree:.0%} "
                     f"({f['referenced_by_check']['anaplan_only']} edges Anaplan lists that the parse did not)." if agree is not None else "Referenced By column absent: dependency completeness not checkable.")
    weak_graph = not _agreement_ok(m)

    def new(**kw):
        nid[0] += 1
        fd = Finding(id=f"F{nid[0]}", model=m.name, **kw)
        out.append(fd)
        return fd

    # ---- usage: one finding per model for every module with no consumer detected (overlap and plain), table inside
    mods = red.overlap + red.orphan_modules
    if mods:
        mods = sorted(mods, key=lambda s: -s["cells"])
        strength = "partial" if not weak_graph else "inferred"
        total_cells = sum(s["cells"] for s in mods); total_eff = round(sum(s["effort"] for s in mods), 2)
        rows = ["| Module | Line items | Cells | Effort share | Exact twin in a read module | Coverage | Unmatched | Import target | Unparsed / COLLECT | Note |", "|---|---|---|---|---|---|---|---|---|---|"]
        for s in mods:
            twin = s.get("target") or ""
            cov = f"{s['matched_source']} of {s['calculated']} ({s['coverage']:.0%})" if twin else ""
            rows.append(f"| {_q(s['module'])} | {s['line_items']} | {_c(s['cells'])} | {s['effort']:.1f}% | {_q(twin) if twin else ''} | {cov} | {len(s['unmatched']) if twin else ''} | {'yes' if s['imported_into'] else ''} | {s['unparsed']} / {s['collect']} | {s['notes'][:120]} |")
        top = mods[:5]
        with_twin = [s for s in mods if s.get("target")]
        complete = [s for s in with_twin if s["complete"]]
        matched_items = sum(s["matched_source"] for s in with_twin)
        missing = _usage_checks("each listed module", has_modules, any(s["imported_into"] for s in mods), False)
        if any(s["unparsed"] for s in mods):
            missing.append("modules with unparsed formulas (table) have references missing from the graph")
        if any(s["collect"] for s in mods):
            missing.append("modules using COLLECT() draw on line item subsets the export does not describe")
        fd = new(area="usage", kind="retire", title=f"{_pl(len(mods), 'module')} with no consumer detected in the inspected dependency types",
                 objects=[s["module"] for s in mods], preview=[s["module"] for s in top], unit="modules", action_usage=action_usage,
                 observed=f"No formula outside these modules reads any of their line items, and {export_clause}. Together they hold {_c(total_cells)} cells"
                          + (f" and {total_eff:.1f}% of {m.name}'s measured calculation effort" if has_effort and total_eff else "") + f". The five largest: {', '.join(_q(s['module']) for s in top)}."
                          + (f" {len(with_twin)} of them contain line items whose formula and context match a line item in a module that is read ({matched_items} matching line items); {len(complete)} match line for line, so no module is a proven duplicate of another." if with_twin else ""),
                 why="No consumer was detected in the inspected relationships (parsed formula references" + (", export actions" if has_actions else "") + "). Pages, saved views, subsets and integrations are not in the exports, and incomplete parsing or missing metadata can hide a reader, so a consumer remains possible. The footprint says which to ask about first.",
                 scope=f"{_pl(len(mods), 'module')}, {sum(s['line_items'] for s in mods)} line items",
                 benefit=f"If no consumer is found: {_footprint(total_cells, total_eff, m.name, has_effort)} would no longer be held or measured. Per module in the table.",
                 benefit_kind="conditional", strength=strength,
                 basis=f"No formula consumer detected (parsed references, checked against Referenced By); export actions: {action_usage}. {coverage_note}",
                 missing=missing,
                 next_step="Complete the consumer and retention checks (pages, saved views, line item subsets, integrations, access drivers, retained data) for the largest module first, then the rest of the five largest, and record a keep-or-retire recommendation for each.",
                 keep_design="A module read only by pages, a view another model imports, or an audit-retained snapshot is doing its job with no formula reader. Retained data in an import target may be needed for history. A module containing matching line items is not a duplicate of the module they match until the unmatched line items and the consumers are accounted for.",
                 summary=f"{_pl(len(mods), 'module')} holding {_c(total_cells)} cells" + (f" and {total_eff:.1f}% of measured effort" if has_effort and total_eff else "") + " have no formula or export consumer in the exports.",
                 object_label=f"{_pl(len(mods), 'module')}, {sum(s['line_items'] for s in mods):,} line items",
                 implementation=["Prerequisites: every consumer check returned none, retained data is not needed, and the model owner has accepted the recommendation.",
                                 "Then: in a development copy, make the proposed change (retire or repoint) while keeping the original module intact for comparison and recovery; reconcile the outputs the owner names against production over a full cycle; obtain owner sign-off; only then apply in production.",
                                 "A module containing matching line items: repoint any page from the module to the matching line items first, and account for the unmatched line items separately."],
                 importance="high" if (total_cells >= 50_000_000 or total_eff >= 5) else "medium" if (total_cells >= 1_000_000 or total_eff >= 1) else "low",
                 complexity="medium", evidence=rows, rules=["G-UNUSED", "REDUNDANT-EXACT"],
                 validation=["After a removal, the Line Items export no longer lists the module and every page listed in the check opens without a blank card. Cell counts are an observed footprint; any memory or open-time change is measured in the workspace, not assumed from cells."],
                 footprint_cells=total_cells, footprint_effort=(total_eff if has_effort else None))
        fd._modules = {s["module"] for s in mods}

    # ---- usage: unreferenced line items outside those modules
    big = [u for u in red.unknown if u["cells"] >= 50_000]
    if big:
        rows = ["| Module | Line items with no formula consumer | Cells | Effort share |", "|---|---|---|---|"]
        for u in big:
            rows.append(f"| {_q(u['module'])} | {', '.join(_q(x) for x in u['items'])} | {_c(u['cells'])} | {u['effort']:.1f}% |")
        n = sum(len(u["items"]) for u in big); cells = sum(u["cells"] for u in big); eff = sum(u["effort"] for u in big)
        new(area="usage", kind="retire", title="Calculated line items with no consumer detected, outside output modules",
            objects=[u["module"] for u in big], unit="modules", action_usage=action_usage,
            observed=f"{n} calculated line items in {len(big)} modules are read by no formula, " + ("are not read by an export action, " if has_actions else "have export-action usage not assessed (no Actions export), ") + "are not in an output-style module and have no matching line item elsewhere.",
            why="Each is computed and stored; if nothing reads it the footprint is spare. If a page reads it, it is an output that lives in a calculation module.",
            scope=f"{_pl(n, 'line item')} in {_pl(len(big), 'module')}",
            benefit=f"If no consumer is found: {_footprint(cells, eff, m.name, has_effort)}.", benefit_kind="conditional",
            strength="partial" if not weak_graph else "inferred", basis=f"Parsed references and export actions only. {coverage_note}",
            missing=["pages, saved views, line item subsets and integrations for each listed module", "the " + str(len(red.output_like)) + " unreferenced line items that look like outputs by module name, format or time scale are not listed here"],
            next_step="Complete the consumer and retention checks (pages, saved views, subsets, integrations, retained data) for the largest module's line items, then record a keep-or-retire recommendation for each.",
            implementation=["Prerequisites: consumer checks returned none and the owner accepts. Then make the proposed change in a development copy with the originals kept for comparison, reconcile named outputs over a cycle, owner sign-off, apply."],
            keep_design="A line item read only by a page is not spare. A calculation kept for audit or reconciliation can be right to keep even if nothing reads it now.",
            importance="medium" if cells >= 10_000_000 else "low", complexity="medium", evidence=rows, rules=["G-UNUSED"],
            validation=["Re-run this report after removal: the list shrinks to the line items a page needs."], footprint_cells=cells, footprint_effort=(eff if has_effort else None))

    # ---- maintain: exact duplicates
    if red.exact:
        c = red.counts()
        rows = ["| Kept (most read) | Also computed as | Context | Summary methods | Redundant cells | Readers to repoint |", "|---|---|---|---|---|---|"]
        for e in red.exact:
            keep, rest = e["items"][0], e["items"][1:]
            ctx = f"{e['dims']}; {keep['time_scale']}; {keep['versions']}; {keep['format']}"
            rows.append(f"| {_q(keep['key'])} | {', '.join(_q(i['key']) for i in rest)} | {ctx} | {', '.join(sorted({i['summary'] for i in e['items']}))} | {_c(e['redundant_cells'])} | {e['readers_to_repoint']} |")
        rows += ["", "Formulas (one per group):", ""] + [f"- {_q(e['items'][0]['key'])}: `{e['formula']}`" for e in red.exact]
        new(area="maintain", kind="merge", title="Same calculation made more than once under different names",
            objects=[e["items"][0]["key"] for e in red.exact], unit="groups (kept line item named)",
            observed=f"{c['exact_redundant']} calculated line items in {c['exact_groups']} groups have the same resolved formula and the same context (dimensions, time scale, time range, versions, data type, summary, formula scope) as another line item in the model. Together the copies hold {_c(c['exact_cells'])} cells.",
            why="Two copies of one calculation drift apart when one is changed. Where a page or process needs the second name, the copy is doing a job; where it does not, readers can share one.",
            scope=f"{_pl(c['exact_redundant'], 'line item')} in {_pl(c['exact_groups'], 'group')}; {sum(e['readers_to_repoint'] for e in red.exact)} formulas would be re-pointed",
            benefit=f"Footprint of the copies: {_c(c['exact_cells'])} cells. Released only for copies that no page, view or process needs.", benefit_kind="footprint",
            strength="confirmed" if not weak_graph else "partial", basis="Resolved formula text and every context field agree; COLLECT() formulas and items with blank context are excluded and listed separately.",
            missing=["pages and views that show the copy under its own name", "access boundaries and reporting contracts that justify a separate object"],
            next_step="Validate equivalence and the reasons for separate objects in the largest group (access boundaries, a reporting contract on the copy's name, a page that shows it), then decide whether consolidation is appropriate.",
            keep_design="Different access (DCA or selective access) on the two modules, a reporting contract on the copy's name, or a deliberately separate process are reasons to keep both. Summary methods already match within a group, so they do not explain the copy.",
            summary=f"{c['exact_redundant']} line items in {c['exact_groups']} groups repeat a calculation already made with the same formula and context; the copies hold {_c(c['exact_cells'])} cells.",
            object_label=f"{_pl(c['exact_groups'], 'group')}; {_pl(c['exact_redundant'], 'duplicate line item')} plus one kept line item per group",
            implementation=["Prerequisites: equivalence validated for the group, the reason for the second object ruled out, the owner accepts.",
                            "Then: repoint each reader of the copy to the kept line item in a development copy, reconcile the outputs that read it, owner sign-off, remove the copy."],
            importance="medium" if c["exact_cells"] >= 10_000_000 else "low", complexity="medium", evidence=rows, rules=["REDUNDANT-EXACT"],
            validation=["Re-run this report: the group count falls; no page shows a blank; no export loses a column."], footprint_cells=c["exact_cells"])
        out[-1].objects = [e["items"][0]["key"] for e in red.exact]

    # ---- maintain: same text, unresolved context
    if red.same_text:
        rows = ["| Formula | Why not compared | Line items |", "|---|---|---|"]
        for e in red.same_text:
            rows.append(f"| `{e['formula']}` | {e['why']} | {', '.join(_q(i['key']) for i in e['items'])} |")
        n = sum(len(e["items"]) for e in red.same_text)
        new(area="maintain", kind="merge", title="Identical formula text whose context the exports cannot resolve",
            objects=[e["items"][0]["key"] for e in red.same_text],
            observed=f"{n} line items in {len(red.same_text)} groups share identical formula text but were not compared: COLLECT() results depend on the line item subset and its source membership, and some rows have a blank context field.",
            why="Listed so nobody reads them as duplicates. Whether any two are the same calculation needs the subset definitions, which are not exported.",
            scope=f"{_pl(n, 'line item')}", benefit="not quantified from the exports", benefit_kind="none", strength="inferred",
            basis="Formula text only; context unresolved.", missing=["line item subset membership for every COLLECT() module", "the blank context fields"],
            next_step="No action from this report. If consolidation is being considered, export the line item subsets first.",
            keep_design="COLLECT() modules dimensioned by different subsets are different calculations by construction.",
            importance="low", complexity="high", evidence=rows, rules=["REDUNDANT-SAME-TEXT"])

    # ---- maintain: aliases
    if red.aliases:
        c = red.counts()
        rows = ["| Alias | Copies | Cells | Readers to repoint | Summary (alias / source) | Module exported |", "|---|---|---|---|---|---|"]
        for a in red.aliases:
            rows.append(f"| {_q(a['item'])} | {_q(a['target'])} | {_c(a['cells'])} | {a['readers']} | {a['summary']} / {a['target_summary']} | {('yes' if a['exported'] else 'no') if has_actions else 'not assessed'} |")
        new(area="maintain", kind="collapse", title="Line items that only copy another line item",
            objects=[a["item"] for a in red.aliases], unit="copy line items", action_usage=action_usage,
            observed=f"{c['aliases']} line items have the formula `B = A` with the same context as A. Together they hold {_c(c['alias_cells'])} cells.",
            why="A copy gives a page a friendlier name, moves a value into a module with different access, or provides a stable name for an export. Where none of those applies, its readers could read the source.",
            scope=f"{_pl(c['aliases'], 'line item')}; {sum(a['readers'] for a in red.aliases)} formulas read them",
            benefit=f"Footprint of the copies: {_c(c['alias_cells'])} cells. Released only for copies without a page, export or access reason.", benefit_kind="footprint",
            strength="confirmed" if not weak_graph else "partial", basis="Single-reference formulas with identical context.",
            missing=["pages that show the alias under its name", "exports and views that read the alias module (the 'module exported' column shows export actions only)"],
            next_step="For the largest copies, establish what shows or exports them under their own name and whether access differs, then decide which copies are interfaces to keep.",
            object_label=f"{_pl(c['aliases'], 'copy line item')}",
            implementation=["Prerequisites: no page, export or access reason for the copy; owner accepts. Then repoint readers in a development copy, reconcile, sign-off, remove."],
            keep_design="An alias that is an interface (a reporting name, an export column, an access boundary) is a good alias.",
            importance="low" if c["alias_cells"] < 50_000_000 else "medium", complexity="low", evidence=rows, rules=["REDUNDANT-ALIAS"],
            validation=["Re-run this report: aliases that remain are the ones kept on purpose."], footprint_cells=c["alias_cells"])

    # ---- maintain: near twins
    cross = [n for n in red.near if not n["same_module"]]
    if cross:
        rows = ["| Line item | Near twin | The one difference | Formula A | Formula B |", "|---|---|---|---|---|"]
        for n in cross:
            rows.append(f"| {_q(n['a'])} | {_q(n['b'])} | `{n['differs'][0]}` vs `{n['differs'][1]}` | `{n['formula_a']}` | `{n['formula_b']}` |")
        new(area="maintain", kind="merge", title="Formulas that differ in exactly one place",
            objects=[n["a"] for n in cross], unit="pairs (first line item named)",
            observed=f"{len(cross)} pairs of line items in different modules share a formula skeleton and context and differ in one leaf: a constant, a reference or a list item.",
            why="This is what copy, paste and tweak leaves behind. The difference may be exactly the point (a different rate, a different driver) or drift between two versions of one rule. The exports cannot say which.",
            scope=f"{_pl(len(cross), 'pair')}", benefit="not quantified from the exports", benefit_kind="none", strength="inferred",
            basis="Structural comparison of parsed formulas; intent is not in the export.",
            missing=["the reason for each difference (notes are mostly blank)"],
            next_step="For the largest pairs, establish whether the one difference is intended; record it in the name or a note, or treat the pair as a duplicate candidate.",
            keep_design="A one-leaf difference is often the whole business rule. Neither side is presumed stale.",
            importance="low", complexity="low", evidence=rows, rules=["REDUNDANT-NEAR"])

    # ---- dependency: chains
    chains = g.daisy_chains()
    if chains:
        rows = ["| Head | Steps | Reads, in the end | Intermediates |", "|---|---|---|---|"]
        for ch in chains:
            rows.append(f"| {_q(ch[0][0] + '.' + ch[0][1])} | {len(ch)} | {_q(ch[-1][0] + '.' + ch[-1][1])} | {', '.join(_q(k[0] + '.' + k[1]) for k in ch[1:-1])} |")
        cells = sum(model.line_items[k].cell_count for ch in chains for k in ch[1:-1] if k in model.line_items)
        new(area="dependency", kind="collapse", title="Pass-through chains", objects=[f"{ch[0][0]}.{ch[0][1]}" for ch in chains], unit="chains (head named)",
            observed=f"{len(chains)} chains where A copies B copies C. Intermediate line items hold {_c(cells)} cells.",
            why="Each step is a stored copy and a place a change of source must be repeated. Anaplan's checklist advises against chains. An intermediate can also be a deliberate interface: a reporting layer, a security boundary, a stable import source for another model.",
            scope=f"{_pl(len(chains), 'chain')}", benefit=f"Footprint of the intermediates: {_c(cells)} cells.", benefit_kind="footprint",
            strength="confirmed" if not weak_graph else "partial", basis="Single-reference formulas in sequence.",
            missing=["whether an intermediate is read by a page, a view or another model's import"],
            next_step="For each chain, establish what each intermediate is for (page, export, access boundary); decide which intermediates are interfaces to keep.",
            implementation=["Prerequisites: the intermediate has no consumer and no interface role; owner accepts. Then repoint the head in a development copy, reconcile, sign-off."],
            keep_design="A pass-through that is an interface (OUT module read by pages, source of an export, access boundary) should stay.",
            importance="low", complexity="low", evidence=rows, rules=["A-DAISY"], footprint_cells=cells)

    # ---- dependency: hubs
    hubs = [(k, n) for k, n in g.hubs(20) if n >= 25]
    if hubs:
        rows = ["| Line item | Direct readers | Downstream (transitive) | Modules downstream |", "|---|---|---|---|"]
        for k, n in hubs:
            imp = g.impact(k)
            rows.append(f"| {_q(k[0] + '.' + k[1])} | {n} | {len(imp)} | {len({x[0] for x in imp})} |")
        new(area="dependency", kind="hub", title="Line items with the widest change impact", objects=[f"{k[0]}.{k[1]}" for k, _ in hubs], unit="line items",
            observed=f"{len(hubs)} line items are read directly by 25 or more formulas.",
            why="A change to any of these moves numbers across the model. Not a fault: a fact for change control and for choosing what to test after a release.",
            scope=f"{_pl(len(hubs), 'line item')}", benefit="not applicable", benefit_kind="none", strength="confirmed" if not weak_graph else "partial",
            basis="Parsed references, checked against Referenced By.", missing=["page and export consumers, which widen the impact further"],
            next_step="Include these in the change-impact check for every release that touches them.",
            keep_design="Hubs are by design; the action is awareness, not change.", importance="medium", complexity="low", evidence=rows, rules=["G-HUB"], kind_label="observation",
            object_label=f"{_pl(len(hubs), 'line item')}")

    # ---- capacity: effort concentration (observed footprint only)
    if has_effort and f["effort_top"]:
        rows = ["| Line item | Effort share | Cells | Formula |", "|---|---|---|---|"]
        for name, eff, cells, formula in f["effort_top"]:
            li = model.line_items.get(tuple(name.split(".", 1))) if "." in name else None
            rows.append(f"| {_q(name)} | {eff:.2f}% | {_c(cells)} | `{(li.formula if li else formula)}` |")
        rows += ["", "By module: " + ", ".join(f"{_q(n)} {v:.1f}%" for n, v in f["effort_by_module"])]
        new(area="capacity", kind="capacity", title="Where measured calculation effort concentrates",
            objects=[name for name, *_ in f["effort_top"]], preview=[name for name, *_ in f["effort_top"][:3]], unit="line items",
            observed=f"Ten line items carry {f['effort_top10_share']}% of {m.name}'s measured calculation effort; the largest is {_q(f['effort_top'][0][0])} at {f['effort_top'][0][1]:.1f}%.",
            why="Effort is where a redesign would show. " + _effort_note(m),
            scope=f"top {len(f['effort_top'])} line items by effort share (the ten largest are summarised)", benefit="Observed footprint only; no reduction is claimed.", benefit_kind="footprint",
            strength="confirmed", basis="Anaplan's Calculation Effort column as exported.", missing=["engine (Classic or Polaris)", "when the measurement was taken"],
            next_step="Read the formulas of the top five and match each against the other findings that name it (SUM with LOOKUP, IF chains, text in large modules); decide which one to trial in a development copy first.",
            keep_design="High effort in the line item that does the model's main job is expected.", importance="medium", complexity="medium", evidence=rows, rules=["EFFORT"], kind_label="observation",
            summary=f"Ten line items carry {f['effort_top10_share']}% of {m.name}'s measured calculation effort, led by {_q(f['effort_top'][0][0])} at {f['effort_top'][0][1]:.1f}%; a concentration to investigate, not a saving.",
            object_label=f"top {len(f['effort_top'])} line items by effort share; ten summarised", footprint_effort=None)

    # ---- capacity: SUM with LOOKUP/SELECT
    if by_rule.get("F-MIXED-CLAUSE"):
        xs = by_rule["F-MIXED-CLAUSE"]
        rows = ["| Line item | Combination | Effort share | Formula |", "|---|---|---|---|"]
        for x in xs:
            li = model.line_items.get((x.module, x.line_item))
            rows.append(f"| {_q(x.object)} | {x.message} | {(f'{li.calc_effort:.2f}%' if li and has_effort else 'n/a')} | `{li.formula if li else ''}` |")
        eff = sum(model.line_items[(x.module, x.line_item)].calc_effort for x in xs if (x.module, x.line_item) in model.line_items)
        new(area="capacity", kind="fix", title="SUM combined with LOOKUP or SELECT in one formula", objects=[x.object for x in xs], unit="formulas",
            observed=f"{len(xs)} formulas combine SUM with LOOKUP or SELECT. Anaplan's documentation: \"{DOCS['lookup'][2]}\" and \"{DOCS['select'][2].split('.')[0]}.\"",
            why="The documented concern is calculation time. Whether splitting a particular formula helps is not guaranteed; the documented approach is one line item to aggregate and another to look up or select from it.",
            scope=f"{_pl(len(xs), 'formula')}" + (f"; together {eff:.1f}% of {m.name}'s measured effort" if has_effort else ""),
            benefit="Observed: the listed effort shares. Improvement would have to be measured after the change.", benefit_kind="footprint",
            strength="confirmed", basis="Parsed clause kinds per formula; official guidance quoted.", missing=["measured effort after a trial split"],
            next_step="Take the formula with the largest effort share; split it in a sandbox copy; compare Calculation Effort before and after.",
            keep_design="A formula with a small effort share that reads clearly can stay as it is; the guidance targets calculation time, not style.",
            importance="medium" if eff >= 5 else "low", complexity="low", evidence=rows, rules=["F-MIXED-CLAUSE"], footprint_effort=(eff if has_effort else None),
            implementation=["Prerequisites: a development copy and a Calculation Effort reading before the change. Then split, reconcile values cell for cell, read effort again; keep the split only if it pays."])

    # ---- capacity: text, FINDITEM, joins, system fns
    heavy = [x for r in ("A-TEXT-FORMAT", "A-FINDITEM", "A-TEXT-JOIN", "A-SYSTEMS-FN") for x in by_rule.get(r, [])]
    if heavy:
        rows = ["| Line item | What | Cells | Effort share | Formula |", "|---|---|---|---|---|"]
        for x in heavy:
            li = model.line_items.get((x.module, x.line_item))
            rows.append(f"| {_q(x.object)} | {RULES[x.rule].title} | {_c(li.cell_count) if li else ''} | {(f'{li.calc_effort:.2f}%' if li and has_effort else 'n/a')} | `{li.formula if li else ''}` |")
        new(area="capacity", kind="tidy", title="Text, FINDITEM and per-item functions in large multi-dimensional line items", objects=[x.object for x in heavy], unit="line items",
            observed=f"{len(heavy)} line items compute a text value, a FINDITEM, a text join or a per-item function (ITEM, PARENT, NAME, CODE) in a line item with many cells.",
            why="Computed once per cell here; computed once per list item in a one-dimension system module. Anaplan's checklist recommends the system module.",
            scope=f"{_pl(len(heavy), 'line item')}", benefit="Observed footprint only; improvement would be measured after the change.", benefit_kind="footprint",
            strength="confirmed", basis="Parsed function calls and exported cell counts.", missing=["measured effort after the change"],
            next_step="Start with the largest by cells; compute it once in a SYS module dimensioned by the list it depends on.",
            keep_design="A small line item, or one that genuinely varies per cell, is fine where it is.", importance="low", complexity="low", evidence=rows,
            rules=["A-TEXT-FORMAT", "A-FINDITEM", "A-TEXT-JOIN", "A-SYSTEMS-FN"])

    # ---- maintain: IF chains (mapping table artefact)
    for x in by_rule.get("A-IF-COUNT", []):
        li = model.line_items.get((x.module, x.line_item))
        mapping = _if_mapping(li.formula) if li else None
        rows = [f"Formula: `{li.formula if li else ''}`", ""]
        if mapping:
            lst = mapping[0][0].split(".")[0]
            rows += [f"| {lst} item | Value |", "|---|---|"] + [f"| {k.split('.', 1)[1] if '.' in k else k} | `{v}` |" for k, v in mapping]
        new(area="maintain", kind="refactor", title="IF chain that encodes a lookup table" if mapping else "Formula with many IF branches", objects=[x.object],
            observed=f"{x.message}." + (f" The branches map {mapping[0][0].split('.')[0]} items to values; the table below is what the formula encodes." if mapping else ""),
            why="Every branch is evaluated for every cell, and every new case is a formula edit. Anaplan's checklist: refactor above 10 IF conditions." + (f" This line item carries {li.calc_effort:.1f}% of the model's measured effort." if li and has_effort and li.calc_effort else ""),
            scope="1 line item; " + _pl(len(g.rev.get((x.module, x.line_item), ())), "reader"),
            benefit="Observed effort share only; improvement would be measured after the change.", benefit_kind="footprint" if li and li.calc_effort else "none",
            strength="confirmed", basis="Parsed formula.", missing=["whether the mapping is stable enough to hold in a module"],
            next_step=("Load the table into a mapping module and replace the chain with one LOOKUP; compare values before and after." if mapping else "Split the conditions into named Boolean line items."),
            keep_design="A short, stable chain that a finance user can read may be clearer than a mapping module.", importance="medium" if li and li.calc_effort >= 5 else "low", complexity="medium",
            evidence=rows, rules=["A-IF-COUNT"], footprint_effort=(li.calc_effort if li and has_effort and li.calc_effort else None), validation=["Export the line item before and after; every cell equal."],
            implementation=["Prerequisites: the mapping is stable and the owner accepts a module in place of the formula. Then build the mapping module in a development copy, replace the formula, reconcile every cell, sign-off."])

    # ---- maintain: hard-coded constants
    if by_rule.get("F-HARDCODE"):
        xs = by_rule["F-HARDCODE"]
        rows = ["| Line item | Constants | Formula |", "|---|---|---|"]
        for x in xs:
            li = model.line_items.get((x.module, x.line_item))
            rows.append(f"| {_q(x.object)} | {x.value.replace(',', ', ')} | `{li.formula if li else ''}` |")
        vals = Counter(v for x in xs for v in x.value.split(",") if v)
        new(area="maintain", kind="refactor", title="Numeric literals inside formulas", objects=[x.object for x in xs], unit="formulas",
            observed=f"{len(xs)} formulas contain numeric literals other than the usual structural ones (0, 1, 12, 100 and the like). Most repeated: {', '.join(f'{v} ({n})' for v, n in vals.most_common(5))}.",
            why="A literal that is an assumption (a rate, a threshold, a conversion) cannot be seen or changed without a builder. The same literal can mean different things in different formulas, so each occurrence needs its own reading before anything is shared.",
            scope=f"{_pl(len(xs), 'formula')}", benefit="not quantified from the exports", benefit_kind="none", strength="confirmed", basis="Parsed numeric leaves.",
            missing=["the meaning of each literal"], next_step="Read the formulas with the most repeated literal; where a literal is a business assumption, give it a named input with a note.",
            keep_design="Structural numbers (months in a year, a unit conversion fixed by definition) are fine inline. Unrelated occurrences of the same value must not share one input.",
            importance="low", complexity="low", evidence=rows, rules=["F-HARDCODE"])

    # ---- maintain: subsidiary views
    if by_rule.get("A-SUBSIDIARY"):
        xs = by_rule["A-SUBSIDIARY"]
        rows = ["| Line item | Applies to | Module applies to | Readers |", "|---|---|---|---|"]
        for x in xs:
            li = model.line_items.get((x.module, x.line_item)); mod = model.modules.get(x.module)
            rows.append(f"| {_q(x.object)} | {', '.join(li.applies_to) if li else ''} | {', '.join(mod.applies_to) if mod else ''} | {x.value} |")
        new(area="maintain", kind="tidy", title="Subsidiary views used in calculation", objects=[x.object for x in xs], unit="line items",
            observed=f"{len(xs)} line items are dimensioned differently from their module and are read by formulas.",
            why="The line item's dimensions are not visible at module level, so a reader can misjudge what a reference returns, and the engine maps between the two dimension sets on every read. Anaplan's checklist: display and export only.",
            scope=f"{_pl(len(xs), 'line item')}; {sum(int(x.value or 0) for x in xs)} readers", benefit="not quantified from the exports", benefit_kind="none",
            strength="confirmed", basis="Line item Applies To versus module Applies To (Modules export).", missing=[],
            next_step="For each, decide whether a module dimensioned as the line item is would make its readers clearer.",
            keep_design="A single small flag in an otherwise consistent module can be the least confusing option.", importance="low", complexity="medium", evidence=rows, rules=["A-SUBSIDIARY"])

    # ---- maintain: summaries on
    if by_rule.get("A-SUMMARY-ON"):
        xs = by_rule["A-SUMMARY-ON"]
        rows = ["| Line item | Summary | Cells |", "|---|---|---|"] + [f"| {_q(x.object)} | {x.value} | {_c(model.line_items[(x.module, x.line_item)].cell_count) if (x.module, x.line_item) in model.line_items else ''} |" for x in xs]
        new(area="maintain", kind="tidy", title="Summary methods on large line items no formula reads", objects=[x.object for x in xs], unit="line items",
            observed=f"{len(xs)} number line items with 10,000 cells or more have a summary method set and no formula reader.",
            why="Summaries are calculated on every parent of every dimension. Only a page or export could need the totals; the exports cannot show whether one does.",
            scope=f"{_pl(len(xs), 'line item')}", benefit="not quantified from the exports", benefit_kind="none", strength="partial",
            basis="Summary column and parsed references; pages not in the export.", missing=["pages and exports that show totals for each line item"],
            next_step="Check the largest ones on their pages; where no total is shown, set the summary to None.",
            keep_design="A total a page shows is the reason the summary is on.", importance="low", complexity="low", evidence=rows, rules=["A-SUMMARY-ON"])

    # ---- maintain: large modules, empty modules, long formulas, select-time, divide-fn
    for x in by_rule.get("A-LI-COUNT", []):
        keys = [(x.module, n) for n in model.modules[x.module].line_items]
        fd = new(area="maintain", kind="tidy", title="Module with more than 50 line items", objects=[x.module],
                 observed=f"{_q(x.module)} has {x.value} line items.",
                 why="Anaplan's checklist suggests reviewing modules above 50: many line items can mean mixed purposes. It can also be a deliberate input grid that users know.",
                 scope=f"1 module; {_readers_outside(g, keys, x.module)} readers outside it" + (f"; {_pl(len(_exports_on(m, x.module)), 'export')}" if _exports_on(m, x.module) else ""),
                 benefit="not quantified from the exports", benefit_kind="none", strength="confirmed", basis="Line item count.", missing=[],
                 next_step="Group the line items by what reads them; if the groups have different purposes, consider a split. Reducing the count is not the goal.",
                 keep_design="A module users open as one grid is easier to keep as one grid.", importance="low", complexity="medium", rules=["A-LI-COUNT"])
        fd._module = x.module
    if by_rule.get("G-EMPTY-MODULE"):
        xs = by_rule["G-EMPTY-MODULE"]
        new(area="maintain", kind="tidy", title="Modules with no line items", objects=[x.module for x in xs], unit="modules",
            observed=f"{len(xs)} modules have no line items.", why="Usually a leftover from a build that moved on.", scope=f"{_pl(len(xs), 'module')}",
            benefit="not applicable", benefit_kind="none", strength="confirmed", basis="Line Items export.", missing=[], next_step="Confirm nothing is planned for them, then decide whether to remove them.",
            keep_design="A placeholder for planned work, if noted.", importance="low", complexity="low", rules=["G-EMPTY-MODULE"])
    if by_rule.get("F-LONG"):
        xs = by_rule["F-LONG"]
        rows = ["| Line item | Tokens | Formula |", "|---|---|---|"] + [f"| {_q(x.object)} | {x.value} | `{model.line_items[(x.module, x.line_item)].formula if (x.module, x.line_item) in model.line_items else ''}` |" for x in xs]
        new(area="maintain", kind="refactor", title="Very long formulas", objects=[x.object for x in xs], unit="formulas",
            observed=f"{len(xs)} formulas exceed 120 tokens.", why="Hard to review and to test. Anaplan's checklist: a formula should be explainable in one sentence.",
            scope=f"{_pl(len(xs), 'formula')}", benefit="not quantified from the exports", benefit_kind="none", strength="confirmed", basis="Token count.", missing=[],
            next_step="Add a note to each explaining what it does; split only where a named intermediate would help a reader.",
            keep_design="A long formula that is correct, documented and rarely touched is a known quantity; splitting it has its own risk.", importance="low", complexity="medium", evidence=rows, rules=["F-LONG"])
    if by_rule.get("F-SELECT-TIME"):
        xs = by_rule["F-SELECT-TIME"]
        rows = ["| Line item | Selection | Formula |", "|---|---|---|"] + [f"| {_q(x.object)} | {x.message} | `{model.line_items[(x.module, x.line_item)].formula if (x.module, x.line_item) in model.line_items else ''}` |" for x in xs]
        new(area="maintain", kind="refactor", title="Hard-coded time period or version selections", objects=[x.object for x in xs], unit="formulas",
            observed=f"{len(xs)} formulas select a specific time period or version with SELECT.",
            why=f"Anaplan's SELECT page: \"{DOCS['select'][2].split('. ')[2] if len(DOCS['select'][2].split('. ')) > 2 else 'not recommended with non-generic time periods'}.\" The hard-coded element must be revisited when the timescale or versions change.",
            scope=f"{_pl(len(xs), 'formula')}", benefit="not quantified from the exports", benefit_kind="none", strength="confirmed", basis="Parsed SELECT clauses.", missing=[],
            next_step="Where the period is a moving concept (current year, prior year), hold it in a time-formatted line item and use LOOKUP.",
            keep_design="A fixed historical period (a base year that never moves) is legitimately hard-coded.", importance="low", complexity="low", evidence=rows, rules=["F-SELECT-TIME"])
    if by_rule.get("F-DIVIDE-FN"):
        xs = by_rule["F-DIVIDE-FN"]
        rows = ["| Line item | Formula |", "|---|---|"] + [f"| {_q(x.object)} | `{model.line_items[(x.module, x.line_item)].formula if (x.module, x.line_item) in model.line_items else ''}` |" for x in xs]
        new(area="maintain", kind="fix", title="DIVIDE() where a zero divisor shows Infinity", objects=[x.object for x in xs], unit="formulas",
            observed=f"{len(xs)} formulas use DIVIDE(). Anaplan's documentation: \"{DOCS['operators'][2]}\" and \"{DOCS['divide'][2]}\"",
            why="Neither behaviour is an error. Where a divisor can be zero, the page shows Infinity or NaN with DIVIDE() and zero with /. This is a display decision for the owner, not a defect.",
            scope=f"{_pl(len(xs), 'formula')}", benefit="not applicable", benefit_kind="none", strength="confirmed", basis="Official documentation, consulted 2026-09-22; function calls parsed.", missing=[],
            next_step="Confirm for each whether Infinity or NaN is acceptable on the pages that show it; no change is needed where it is.",
            keep_design="DIVIDE() is the right choice where a zero result would be misleading and Infinity signals a data gap.", importance="low", complexity="low", evidence=rows, rules=["F-DIVIDE-FN"])

    # ---- integration: actions
    a = f.get("actions")
    if a and (a["not_in_process"] or a["no_recent_run"] or a["never_recorded"]):
        rows = ["| Action | Kind | Most recent recorded run | In a process | Target or source |", "|---|---|---|---|---|"]
        listed = set(a["not_in_process"]) | {n for n, _ in a["no_recent_run"]} | set(a["never_recorded"])
        acts = m.actions.actions
        for name in sorted(listed, key=lambda n: (acts.get(n).last_run if acts.get(n) else "")):
            act = acts.get(name)
            rows.append(f"| {_q(name)} | {act.kind if act else ''} | {act.last_run[:10] if act and act.last_run else 'none recorded'} | {'no' if name in a['not_in_process'] else 'yes'} | {_q(act.target) if act and act.target else ''} |")
        new(area="integration", kind="schedule", title="Imports and exports with no recent recorded run or outside every process", objects=sorted(listed), unit="actions",
            observed=f"Export date unknown. Latest recorded action run: {a['snapshot'] or 'none'}. {len(a['no_recent_run'])} imports and exports have no recorded run since {a['stale_cutoff'] or 'n/a'} ({a['stale_months']} months before the latest recorded run), {len(a['never_recorded'])} have no recorded run at all, and {len(a['not_in_process'])} are not in any process.",
            why="An action outside a process can still run from a page, the Actions pane or the API; a run date older than the window may be right for a quarterly or annual load. What the list gives is the set to ask about, not a verdict.",
            scope=f"{_pl(len(listed), 'action')}", benefit="not quantified from the exports", benefit_kind="none", strength="partial",
            basis=f"Actions export: most recent run per action, process membership. {DOCS['actions'][2]}",
            missing=["how each action is triggered (page, API, CloudWorks, by hand)", "the expected frequency of each load", "run history beyond the most recent run"],
            next_step="For each action with no recorded run in the window, ask the owner how and how often it runs; document the answer in the action's notes.",
            keep_design="Year-end loads, ad-hoc reloads and API-driven actions legitimately show no recent run and no process. Retiring an import does not by itself justify removing its target module or the data it loaded.",
            importance="low", complexity="low", evidence=rows, rules=["ACTIONS"])

    # ---- limitation: unparsed formulas
    if by_rule.get("F-PARSE"):
        xs = by_rule["F-PARSE"]
        rows = ["| Line item | Parser message | Formula |", "|---|---|---|"] + [f"| {_q(x.object)} | {x.message} | `{model.line_items[(x.module, x.line_item)].formula if (x.module, x.line_item) in model.line_items else ''}` |" for x in xs]
        new(area="dependency", kind="fix", title="Formulas the parser did not follow (analysis limitation)", objects=[x.object for x in xs], unit="formulas",
            observed=f"{len(xs)} formulas were not parsed, so their references are missing from the dependency graph.",
            why="Counts of readers, hubs and 'no consumer detected' that touch these line items are incomplete. This is a limitation of the analysis; it is not evidence of a model defect.",
            scope=f"{_pl(len(xs), 'formula')}", benefit="not applicable", benefit_kind="none", strength="confirmed", basis="Parser output.", missing=["the references inside these formulas"],
            next_step="Treat any finding that names one of these line items as unverified until the parser covers the shape.", keep_design="Nothing to change in the model.",
            importance="low", complexity="low", evidence=rows, rules=["F-PARSE"], kind_label="observation")

    # link alternatives: module usage finding vs module size finding on the same module
    rollup = next((fd for fd in out if hasattr(fd, "_modules")), None)
    for fd in out:
        if hasattr(fd, "_module") and rollup and fd._module in rollup._modules:
            fd.related = [rollup.id]
            rollup.related = sorted(set(rollup.related) | {fd.id})
            fd.counts_benefit = False
            fd.benefit = f"Alternative to {rollup.id} for {_q(fd._module)}; footprint counted there."
    for fd in out:
        for attr in ("_module", "_modules"):
            if hasattr(fd, attr):
                delattr(fd, attr)
    return out


def _estate(er, nid) -> list[Finding]:
    out = []
    if er.duplicates:
        rows = ["| Line item | Models | Formula |", "|---|---|---|"] + [f"| {_q(d['line_item'])} | {', '.join(d['models'])} | `{d['formula']}` |" for d in er.duplicates]
        nid[0] += 1
        out.append(Finding(id=f"F{nid[0]}", area="maintain", kind="dedupe", title="Same line item name and formula in more than one model", model="Estate",
                           objects=[d["line_item"] for d in er.duplicates], unit="line item names",
                           observed=f"{len(er.duplicates)} line items appear in more than one model with the same name and the same formula tree.",
                           why="The same text can operate on different local data (a filter over a local list, a local rate), so identical formulas are not automatically one calculation. Where they are one calculation, a change must be made in each copy.",
                           scope=f"{_pl(len(er.duplicates), 'line item')} across {len({mm for d in er.duplicates for mm in d['models']})} models", benefit="not quantified from the exports", benefit_kind="none",
                           strength="inferred", basis="Name and formula text only; the referenced objects live in different models.",
                           missing=["whether the referenced lists and modules hold the same data in each model", "which model is the source of truth for each"],
                           next_step="Pick the copies that are genuinely one rule and record where it is owned; leave local filters and formatting where they are.",
                           keep_design="A rule that must be evaluated locally in each model (a filter, a format, a local flag) is right to repeat.",
                           importance="low", complexity="medium", evidence=rows, rules=["DUP-CROSS"], object_label=f"{_pl(len(er.duplicates), 'line item name')}"))
    return out


def build(er) -> list[Finding]:
    nid = [0]
    fs: list[Finding] = []
    for m in er.models:
        fs += _per_model(er, m, nid)
    fs += _estate(er, nid)
    for x in fs:
        if not x.summary:
            first = re.split(r"(?<=[.!?])\s+", x.observed.strip(), maxsplit=1)[0]
            x.summary = first
        if not x.object_label:
            x.object_label = f"{len(x.objects):,} {x.unit}" if x.unit != "objects" else _pl(len(x.objects), "object")
        if not x.preview:
            x.preview = x.objects[:3]
        x.preview_label = (f"All {len(x.objects)} {x.unit}" if len(x.preview) >= len(x.objects) else f"Showing {len(x.preview)} of {len(x.objects)} {x.unit}")
        x.uid = stable_uid(x)
    fs.sort(key=lambda x: (IMPORTANCE_ORDER[x.importance], STRENGTH_ORDER[x.strength], -(x.footprint_cells or 0), -(x.footprint_effort or 0)))
    for i, x in enumerate(fs, 1):
        old = x.id
        x.id = f"F{i}"
        for y in fs:
            y.related = [x.id if r == old else r for r in y.related]
    seen = Counter(x.uid for x in fs)
    dup = {u for u, n in seen.items() if n > 1}
    if dup:
        k = Counter()
        for x in fs:
            if x.uid in dup:
                k[x.uid] += 1; x.uid = f"{x.uid}-{k[x.uid]}"
    return fs


def stable_uid(x: Finding) -> str:
    """Identity that survives renumbering between runs: model, rules, title and the leading object. Two findings that
    share all four in one report get a suffix, so a note never lands on the wrong one within a report."""
    import hashlib
    base = f"{x.model}|{'+'.join(x.rules)}|{x.title}|{x.objects[0] if x.objects else ''}"
    return "u" + hashlib.sha1(base.encode("utf-8")).hexdigest()[:10]


def by_area(fs: list[Finding]):
    out = []
    for key, label, blurb in AREAS:
        xs = [x for x in fs if x.area == key]
        if xs:
            out.append((key, label, blurb, xs))
    return out
