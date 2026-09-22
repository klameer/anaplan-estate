"""Analytical failure modes, each on a small in-memory fixture.

Automated tests over the parser, rules and comparison logic. None of this
was validated in a live Anaplan model; documented behaviour is quoted from
help.anaplan.com (consulted 2026-09-22) in lint.DOCS.
"""
import sys, pathlib, csv, io
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "src"))
from anaplan_estate.model import Model, LineItem, Module, load_line_items
from anaplan_estate.graph import build_graph
from anaplan_estate.lint import lint, RULES, DOCS
from anaplan_estate import redundancy, fleet, findings
from anaplan_estate.estate import Estate, Action, Process

NUM = '{"dataType":"NUMBER"}'


def model(items, modules=None, has_modules=False):
    """items: (module, name, formula, applies, extra) ; extra keys: cells, ts, tr, vers, fmt, summary, scope, refby."""
    m = Model(name="T")
    for it in items:
        mod, name, formula, applies = it[:4]
        x = it[4] if len(it) > 4 else {}
        m.modules.setdefault(mod, Module(name=mod))
        li = LineItem(module=mod, name=name, formula=formula, format_type=x.get("fmt", "NUMBER"), applies_to=tuple(applies),
                      time_scale=x.get("ts", "Month"), versions=x.get("vers", "All"), summary=x.get("summary", "SUM"), cell_count=x.get("cells", 100000),
                      time_range=x.get("tr", "Model Calendar"), formula_scope=x.get("scope", "All Versions"), referenced_by_raw=x.get("refby", ""))
        m.line_items[li.key] = li
        m.modules[mod].line_items.append(name)
        m.dimensions.update(applies)
    for mod, dims in (modules or {}).items():
        m.modules.setdefault(mod, Module(name=mod)).applies_to = tuple(dims)
    m.has_modules_export = has_modules or bool(modules)
    return m


def run_rules(m, rule=None):
    g = build_graph(m)
    r = lint(m, g)
    return [f for f in r.findings if rule is None or f.rule == rule], g


# ---- A. division

def test_plain_division_is_not_flagged_and_divide_fn_is_info():
    m = model([("M", "A", "", ("L",)), ("M", "B", "", ("L",)), ("M", "R1", "A / B", ("L",)), ("M", "R2", "DIVIDE(A, B)", ("L",))])
    fs, _ = run_rules(m)
    assert "F-DIVIDE" not in RULES
    assert not any(f.line_item == "R1" for f in fs if f.rule.startswith("F-DIVIDE"))
    d = [f for f in fs if f.rule == "F-DIVIDE-FN"]
    assert len(d) == 1 and d[0].line_item == "R2" and d[0].severity == "info"
    assert "returns zero" in DOCS["operators"][2] and "Infinity" in DOCS["divide"][2]
    assert "paste" not in d[0].fix.lower() and "DIVIDE(a, b)" not in d[0].fix


# ---- B. mixed clause

def test_lookup_with_select_does_not_trigger_mixed_rule():
    m = model([("S", "Map", "", ("L",), {"fmt": "ENTITY"}), ("M", "A", "", ("L",)),
               ("M", "R", "A[LOOKUP: 'S'.Map][SELECT: VERSIONS.Actual]", ("L",))])
    fs, _ = run_rules(m, "F-MIXED-CLAUSE")
    assert fs == []


def test_sum_with_lookup_or_select_triggers_mixed_rule_even_in_separate_brackets():
    m = model([("S", "Map", "", ("L",), {"fmt": "ENTITY"}), ("M", "A", "", ("L",)),
               ("M", "R1", "A[SUM: 'S'.Map, LOOKUP: 'S'.Map]", ("L",)),
               ("M", "R2", "A[SUM: 'S'.Map][SELECT: VERSIONS.Actual]", ("L",)),
               ("M", "R3", "A[SUM: 'S'.Map]", ("L",))])
    fs, _ = run_rules(m, "F-MIXED-CLAUSE")
    got = {f.line_item: f.message for f in fs}
    assert set(got) == {"R1", "R2"}
    assert "same bracket" in got["R1"] and "separate brackets" in got["R2"]
    assert all("guarantee" not in f.fix for f in fs)


def test_hardcoded_time_select_is_a_separate_finding():
    m = model([("M", "A", "", ("L",)), ("M", "R", "A[SELECT: TIME.'Jan 21']", ("L",))])
    fs, _ = run_rules(m, "F-SELECT-TIME")
    assert len(fs) == 1 and "TIME.Jan 21" in fs[0].message


# ---- C. duplicates and equivalence

def test_collect_in_different_contexts_is_not_declared_equivalent():
    m = model([("M1", "COLLECT", "COLLECT()", ("LISS A",)), ("M2", "COLLECT", "COLLECT()", ("LISS B",)), ("M3", "COLLECT", "COLLECT()", ("LISS A",))])
    g = build_graph(m)
    r = redundancy.analyse(m, g)
    assert r.exact == []
    assert r.same_text and "COLLECT" in r.same_text[0]["why"]


def test_inherited_dimensions_are_resolved_before_comparison():
    m = model([("M1", "A", "", ()), ("M1", "X", "A * 2", ()), ("M2", "Y", "'M1'.A * 2", ())], modules={"M1": ("L",), "M2": ("L", "P")})
    g = build_graph(m)
    r = redundancy.analyse(m, g)
    assert r.exact == []                       # different effective dims -> not the same calculation
    m2 = model([("M1", "A", "", ()), ("M1", "X", "A * 2", ()), ("M2", "Y", "'M1'.A * 2", ())], modules={"M1": ("L",), "M2": ("L",)})
    r2 = redundancy.analyse(m2, build_graph(m2))
    assert len(r2.exact) == 1


def test_missing_metadata_is_not_treated_as_matching():
    m = model([("M1", "A", "", ("L",)), ("M1", "X", "A * 2", ("L",), {"tr": ""}), ("M2", "Y", "'M1'.A * 2", ("L",), {"tr": ""})])
    r = redundancy.analyse(m, build_graph(m))
    assert r.exact == [] and r.unresolved_context == 2 and r.same_text and "blank" in r.same_text[0]["why"]


def test_unique_matched_counts_cannot_exceed_source_and_partial_match_is_not_supersession():
    items = [("T", "a", "", ("L",))]
    for i in range(5):
        items.append(("T", f"t{i}", f"a * {i + 2}", ("L",)))
        items.append(("O", f"o{i}", f"'T'.a * {i + 2}", ("L",)))
    items.append(("O", "extra", "'T'.a + 99", ("L",)))
    items.append(("R", "r", "'T'.t0 + 'T'.t1", ("L",)))     # T is read from outside; O is not
    m = model(items)
    r = redundancy.analyse(m, build_graph(m))
    ov = [o for o in r.overlap if o["module"] == "O"]
    assert len(ov) == 1
    o = ov[0]
    assert o["matched_source"] == 5 and o["calculated"] == 6 and o["coverage"] <= 1.0 and o["unmatched"] == ["extra"] and not o["complete"]
    fs = findings.build(_estate_from(m))
    txt = " ".join(f.title + f.observed + f.why for f in fs)
    assert "supersed" not in txt.lower() and "5 of its 6" in txt


# ---- D. dependency coverage

def test_unresolved_coverage_lowers_strength_of_retirement_findings():
    items = [("T", "a", "", ("L",)), ("O", "x", "'T'.a * 3", ("L",), {"cells": 60_000_000}), ("O", "y", "'T'.a * 4", ("L",), {"cells": 60_000_000})]
    m = model(items)
    for li in m.line_items.values():
        li.referenced_by_raw = "'Z'.q, 'Z'.r, 'Z'.s"      # Anaplan lists readers the parse cannot see
    er = _estate_from(m)
    fs = [f for f in er.findings if f.area == "usage"]
    assert fs and fs[0].strength == "inferred"
    assert any("Referenced By" in x for x in [fs[0].basis])
    assert "no consumer detected" in fs[0].title.lower() and "unused" not in fs[0].title.lower()
    assert any("saved views" in x for x in fs[0].missing) and any("subset" in x for x in fs[0].missing)


def test_reference_check_metric_definition_and_causes():
    m = model([("M", "A", "", ("L",), {"refby": "B, 'X'.COLLECT"}), ("M", "B", "A * 2", ("L",)), ("X", "COLLECT", "COLLECT()", ("LISS",))])
    g = build_graph(m)
    rc = fleet._ref_check(m, g)
    assert rc["agree"] == 1 and rc["anaplan_only"] == 1 and rc["anaplan_only_by_cause"] == {"collect": 1}
    assert rc["agreement"] == 0.5 and "over edges present in either" in rc["definition"]


# ---- G. actions

def test_actions_outside_processes_are_not_presumed_unused_and_snapshot_is_separate():
    e = Estate()
    e.actions["Import X"] = Action(name="Import X", kind="import", target="M", last_run="2025-01-10 10:00:00")
    e.actions["Export Y"] = Action(name="Export Y", kind="export", target="M", last_run="2025-06-01 10:00:00", processes=("P",))
    e.processes["P"] = Process(name="P", steps=["Export Y"])
    a = fleet._actions_facts(e, 3)
    assert a["snapshot"] == "2025-06-01" and a["stale_cutoff"] == "2025-03-03"
    assert a["not_in_process"] == ["Import X"] and a["no_recent_run"] == [("Import X", "2025-01-10")]
    m = model([("M", "A", "", ("L",))])
    er = _estate_from(m, e)
    fs = [f for f in er.findings if f.area == "integration"]
    assert fs and "can still run from a page" in fs[0].why and "obsolete" not in fs[0].observed
    assert "every action" not in " ".join(fs[0].validation).lower()


def test_generic_words_are_not_external_sources():
    e = Estate()
    e.actions["Import from Hierarchy"] = Action(name="Import from Hierarchy", kind="import", target="M")
    e.actions["Import from NetSuite - GL"] = Action(name="Import from NetSuite - GL", kind="import", target="M")
    a = fleet._actions_facts(e, 12)
    assert list(a["sources"]) == ["NetSuite"]


# ---- F. constants, near matches, large modules

def test_identical_constants_are_not_consolidated():
    m = model([("M", "A", "", ("L",)), ("M", "X", "A * 5", ("L",)), ("N", "Y", "'M'.A / 5", ("L",))])
    er = _estate_from(m)
    fs = [f for f in er.findings if "literal" in f.title.lower()]
    assert fs and "different things" in fs[0].why and "must not share" in fs[0].keep_design


def test_near_match_is_not_presumed_stale():
    m = model([("M", "A", "", ("L",)), ("M", "B", "", ("L",)), ("M", "C", "", ("L",)), ("M", "X", "A * B + C * 7", ("L",)), ("N", "Y", "'M'.A * 'M'.B + 'M'.C * 8", ("L",))])
    er = _estate_from(m)
    fs = [f for f in er.findings if "differ in exactly one place" in f.title]
    assert fs and fs[0].strength == "inferred" and "presumed stale" in fs[0].keep_design


def test_large_module_is_review_not_target():
    items = [("Big", f"li{i}", "", ("L",)) for i in range(55)] + [("Big", "c", "li1 + li2", ("L",))]
    fs, _ = run_rules(model(items), "A-LI-COUNT")
    assert fs and fs[0].severity == "minor" and "Review" in fs[0].fix and "Split into" not in fs[0].fix


# ---- E. overlapping alternatives

def test_overlapping_alternatives_do_not_double_count():
    items = [("T", "a", "", ("L",))] + [("Big", f"li{i}", "", ("L",), {"cells": 2_000_000}) for i in range(55)] + [("Big", "c", "'T'.a * 2", ("L",), {"cells": 2_000_000}), ("Big", "d", "'T'.a * 3", ("L",), {"cells": 2_000_000})]
    er = _estate_from(model(items))
    big = [f for f in er.findings if "Big" in f.objects]
    assert len(big) == 2
    counted = [f for f in big if f.counts_benefit]
    assert len(counted) == 1 and counted[0].area == "usage"
    other = [f for f in big if not f.counts_benefit][0]
    assert counted[0].id in other.related and "Alternative to" in other.benefit


# ---- H. coverage

def test_missing_actions_export_gives_accurate_coverage(tmp_path):
    d = tmp_path / "estate" / "1 Solo"
    d.mkdir(parents=True)
    rows = [",Format,Formula,Summary,Applies To,Time Scale,Time Range,Versions,Style,Cell Count,Notes,Referenced By,Module Name",
            "M,,,,,Not Applicable,Not Applicable,Not Applicable,,0,,,",
            f'A,"{NUM}",,,L,Month,Model Calendar,All,,120,,,M', f'B,"{NUM}",A * 2,,L,Month,Model Calendar,All,,120,,,M']
    (d / "Line Items.csv").write_text("\n".join(rows), encoding="utf-8")
    er = fleet.run(tmp_path / "estate")
    cov = er.models[0].facts["coverage"]
    assert cov["files"]["actions"] is None and cov["snapshot_actions"] == ""
    skipped = dict(cov["rules_skipped"])
    assert "actions" in skipped and "A-SUBSIDIARY" in skipped and "H-NOTES" in skipped
    assert cov["inferred"] == [] and er.models[0].facts["actions"] is None


# ---- helper

def _estate_from(m, estate=None):
    """Wrap an in-memory model as a one-model EstateRun and build findings."""
    from anaplan_estate.lint import lint as _lint
    from anaplan_estate.cluster import cluster
    g = build_graph(m)
    lr = _lint(m, g)
    e = estate or Estate()
    facts = fleet_facts(m, g, lr, e)
    red = redundancy.analyse(m, g, export_sources={a.target for a in e.actions.values() if a.kind == "export"},
                             import_targets={a.target for a in e.actions.values() if a.kind == "import"})
    facts["redundancy"] = red.counts()
    facts["coverage"] = fleet._coverage({"line_items": "x/Line Items.csv", "actions": "x/Actions.csv" if estate else None, "modules": None}, m, g, lr, facts)
    mr = fleet.ModelRun("T", "x", m, g, lr, cluster(lr.findings), e, facts, red)
    er = fleet.EstateRun([mr], [], {}, [], [])
    er.findings = findings.build(er)
    return er


def fleet_facts(m, g, lr, e):
    """The facts dict as fleet.analyse builds it, without discovery."""
    from collections import Counter
    lis = [li for li in m.line_items.values() if not li.is_header]
    st = g.stats()
    total = sum(li.cell_count for li in lis)
    by_mod = Counter(); by_eff = Counter()
    for li in lis:
        by_mod[li.module] += li.cell_count; by_eff[li.module] += li.calc_effort
    eff = sorted(lis, key=lambda li: -li.calc_effort)
    has_effort = any(li.calc_effort for li in lis)
    return {"modules": len(m.modules), "line_items": len(lis), "calculated": st["with_formula"], "inputs": len(lis) - st["with_formula"], "cells": total,
            "dimensions": sorted(m.dimensions), "edges": st["edges"], "module_edges": st["module_edges"], "parse_errors": st["parse_errors"],
            "parse_rate": round(1 - st["parse_errors"] / max(st["with_formula"], 1), 4), "notes_coverage": 0.0, "has_effort": has_effort,
            "effort_top10_share": None, "effort_top": [], "effort_by_module": [], "cells_by_module": [(n, c, 0) for n, c in by_mod.most_common()],
            "hubs": [(f"{k[0]}.{k[1]}", n) for k, n in g.hubs(10)], "unreferenced": len(g.unused()), "cycles": 0, "cycles_balance": 0, "cycles_fault": 0,
            "daisy_chains": len(g.daisy_chains()), "referenced_by_check": fleet._ref_check(m, g), "findings": len(lr.findings), "patterns": 0,
            "rules_skipped": [], "has_modules_export": m.has_modules_export,
            "actions": fleet._actions_facts(e, 12) if e.actions else None}
