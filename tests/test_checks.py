"""The check catalogue and the checks added with it: the registry is complete and consistent with the rules, the
published list is in step with it, and each new check fires on its case and stays quiet on the near misses."""
import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "src"))
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from anaplan_estate import checks, fleet, report, report_html
from anaplan_estate.lint import RULES, leftover_marker
from anaplan_estate.estate import Estate, Action
from test_rules import model, run_rules, _estate_from

ROOT = pathlib.Path(__file__).resolve().parents[1]
EX = ROOT / "examples" / "caldergate-estate"
PCT = '{"unitsType":"PERCENTAGE","dataType":"NUMBER"}'


# ---- the registry

def test_numbers_are_unique_and_run_in_order_within_each_category():
    assert len({c.num for c in checks.CHECKS}) == len(checks.CHECKS) == len({c.key for c in checks.CHECKS})
    for cat, cs in checks.by_category():
        assert [c.num for c in cs] == [f"{cat.num}.{i}" for i in range(1, len(cs) + 1)]
    assert sum(len(cs) for _, cs in checks.by_category()) == len(checks.CHECKS)


def test_every_rule_belongs_to_exactly_one_check():
    owners = {}
    for c in checks.CHECKS:
        for r in c.rules:
            assert r in RULES, f"{c.num} names a rule that does not exist: {r}"
            assert r not in owners, f"{r} is claimed by {owners.get(r)} and {c.num}"
            owners[r] = c.num
        assert c.rules or c.tags or c.fact, f"{c.num} is tied to nothing in the engine"
    assert set(RULES) == set(owners), f"rules without a check: {set(RULES) - set(owners)}"


def test_published_list_is_generated_from_the_registry():
    assert (ROOT / "docs" / "TESTS.md").read_text(encoding="utf-8").strip() == checks.markdown().strip(), \
        "docs/TESTS.md is stale: python -m anaplan_estate.checks > docs/TESTS.md"


# ---- 4.16 ratios whose totals are added up

def test_ratio_of_two_summed_amounts_with_summary_sum_is_flagged():
    m = model([("M", "A", "", ("L",)), ("M", "B", "", ("L",)),
               ("M", "R1", "A / B", ("L",)), ("M", "R2", "IF B = 0 THEN 0 ELSE (A - B) / B * 100", ("L",)), ("M", "R3", "DIVIDE(A, B)", ("L",))])
    fs, _ = run_rules(m, "F-RATIO-SUM")
    assert {f.line_item for f in fs} == {"R1", "R2", "R3"} and all(f.severity == "major" for f in fs)
    assert "totals add the ratios" in fs[0].message and "Formula" in fs[0].fix


def test_scalings_conversions_and_formula_summaries_are_not_flagged():
    m = model([("M", "A", "", ("L",)), ("M", "B", "", ("L",)), ("M", "Rate", "", ("L",), {"summary": "NONE"}),
               ("S", "Global", "", (), {"ts": "Not Applicable"}),
               ("M", "Monthly", "A / 12", ("L",)),                                    # a literal divisor is a scaling
               ("M", "Converted", "A / Rate", ("L",)),                                # the divisor is a rate that is not summed
               ("M", "Scaled", "A / 'S'.Global", ("L",)),                             # one value for the whole model
               ("M", "Right", "A / B", ("L",), {"summary": "FORMULA"}),
               ("M", "Off", "A / B", ("L",), {"summary": "NONE"}),
               ("M", "Product", "A / B * Rate", ("L",))])                             # not a quotient in the end
    fs, _ = run_rules(m, "F-RATIO-SUM")
    assert fs == []


def test_percentage_format_with_sum_is_flagged_and_time_only_sum_says_so():
    m = model([("M", "A", "", ("L",)), ("M", "Rate", "", ("L",), {"summary": "NONE"}), ("M", "B", "", ("L",)),
               ("M", "Pct", "A / Rate", ("L",)), ("M", "TimeOnly", "A / B", ("L",), {"summary": "NONE;time=SUM"})])
    m.line_items[("M", "Pct")].format_raw = PCT
    fs, _ = run_rules(m, "F-RATIO-SUM")
    got = {f.line_item: f.message for f in fs}
    assert set(got) == {"Pct", "TimeOnly"}
    assert "formatted as a percentage" in got["Pct"] and "every time total" in got["TimeOnly"] and "every parent" not in got["TimeOnly"]


# ---- 4.17 the odd one out

def _run(names, formula_of):
    return [("D", "x", "", ("L",)), ("S", "Flag", "", ("L",), {"fmt": "BOOLEAN"}), ("S", "Other", "", ("L",), {"fmt": "BOOLEAN"})] + \
           [("M", n, formula_of(n), ("L",)) for n in names]


def test_one_reference_its_neighbours_do_not_share_is_the_odd_one_out():
    names = [f"P{i}" for i in range(6)]
    m = model([("D", n, "", ("L",)) for n in names] + _run(names, lambda n: f"IF 'S'.{'Other' if n == 'P3' else 'Flag'} THEN 0 ELSE 'D'.{n}"))
    fs, _ = run_rules(m, "F-ODD-ONE")
    assert len(fs) == 1 and fs[0].line_item == "P3" and "S.Other" in fs[0].message and "5 neighbours" in fs[0].message


def test_a_typed_in_value_or_another_shape_inside_a_run_is_the_odd_one_out():
    names = [f"P{i}" for i in range(7)]
    for odd, word in (("", "has no formula"), ("'D'.x * 2 + 1", "different formula shape")):
        m = model(_run(names, lambda n: odd if n == "P3" else "IF 'S'.Flag THEN 0 ELSE 'D'.x"))
        fs, _ = run_rules(m, "F-ODD-ONE")
        assert len(fs) == 1 and fs[0].line_item == "P3" and word in fs[0].message


def test_a_consistent_run_a_short_run_and_a_mixed_module_are_quiet():
    same = model(_run([f"P{i}" for i in range(8)], lambda n: "IF 'S'.Flag THEN 0 ELSE 'D'.x"))
    short = model(_run([f"P{i}" for i in range(4)], lambda n: "'D'.x * 2" if n == "P1" else "IF 'S'.Flag THEN 0 ELSE 'D'.x"))
    mixed = model(_run([f"P{i}" for i in range(9)], lambda n: "'D'.x * 2" if n in ("P2", "P5") else "IF 'S'.Flag THEN 0 ELSE 'D'.x"))
    for m in (same, short, mixed):
        assert run_rules(m, "F-ODD-ONE")[0] == []


# ---- 1.7 a dimension the formula does not use

def test_dimension_no_reference_varies_over_is_flagged_and_a_hierarchy_is_left_alone():
    m = model([("S", "Rate", "", ("L",)), ("S", "ByChild", "", ("Child",)),
               ("M", "Wide", "'S'.Rate * 2", ("L", "K")),            # K multiplies cells, the value varies over L only
               ("M", "Fits", "'S'.Rate * 2", ("L",)),
               ("M", "Parent", "'S'.ByChild", ("L",)),                # reads a list it does not apply to: a hierarchy or mapping the export cannot show
               ("M", "Const", "0.2", ("L", "K")),
               ("M", "Small", "'S'.Rate", ("L", "K"), {"cells": 500})])
    fs, _ = run_rules(m, "G-OVERDIM")
    got = {f.line_item: f.message for f in fs}
    assert set(got) == {"Wide", "Const"}
    assert got["Wide"].startswith("applies to K but its formula varies only over L") and "constant" in got["Const"]


# ---- 2.5 names that say leftover

def test_leftover_markers_and_the_ordinary_names_that_look_like_them():
    for name, marker in (("CAL05 Opex OLD", "OLD"), ("Old Budget Revenue", "Old"), ("Budget DO NOT USE", "DO NOT USE"), ("Revenue v2", "v2"), ("Copy of Revenue", "Copy of"),
                         ("zz Archive 2021", "zz"), ("TEMP calc", "TEMP"), ("Line item 3", "Line item 3"), ("Opex BACKUP", "BACKUP")):
        assert leftover_marker(name) == marker, name
    for name in ("Temp Labour", "Threshold", "Bold Text", "Copy Centre Costs", "Stress Test", "Uplift V", "Gold", "EV2 Charger", "Revenue"):
        assert leftover_marker(name) == "", name


def test_leftover_module_line_item_and_list_item_say_whether_they_are_still_read():
    m = model([("Calc OLD", "a", "", ("L",)), ("M", "b", "'Calc OLD'.a * 2", ("L",)),
               ("M", "Old Rate", "", ("L",)), ("M", "c", "Old Rate[SELECT: VERSIONS.'Budget v2 DO NOT USE']", ("L",))])
    fs, _ = run_rules(m, "H-LEFTOVER")
    msg = {(f.module, f.line_item): f.message for f in fs}
    assert "still read by 1 formula in other modules" in msg[("Calc OLD", None)]
    assert "still read by 1 formula" in msg[("M", "Old Rate")]
    assert "VERSIONS.Budget v2 DO NOT USE" in msg[("M", "c")]
    assert ("Calc OLD", "a") not in msg                               # the module says it once


# ---- 2.4 and 5.4: from the Actions export

def _actions_estate():
    e = Estate()
    e.actions["Import A"] = Action(name="Import A", kind="import", target="Loaded", last_run="2026-06-01 10:00:00", processes=("P",))
    e.actions["Import B"] = Action(name="Import B", kind="import", target="Read", last_run="2026-06-01 10:00:00", processes=("P",))
    e.actions["Import B old"] = Action(name="Import B old", kind="import", target="Read", last_run="2021-03-01 10:00:00")
    return e


def test_import_target_nothing_reads_and_two_imports_into_one_target():
    m = model([("Loaded", "x", "", ("L",)), ("Read", "y", "", ("L",)), ("Calc", "z", "'Read'.y * 2", ("L",))])
    er = _estate_from(m, _actions_estate())
    unread = [f for f in er.findings if f.rules == ["IMPORT-UNREAD"]]
    assert len(unread) == 1 and unread[0].objects == ["Loaded"] and unread[0].strength in ("partial", "inferred") and "keep-or-retire" in unread[0].next_step
    multi = [f for f in er.findings if f.rules == ["IMPORT-MULTI"]]
    assert len(multi) == 1 and multi[0].objects == ["Read"] and "In 1 of them" in multi[0].observed
    res = {r["num"]: r for r in checks.results(er)}
    assert res[checks.N("import-target-unread")]["hits"] == 1 and res[checks.N("several-imports-one-target")]["hits"] == 1
    left = [f for f in er.findings if f.rules == ["H-LEFTOVER"]]
    assert left and "Import B old" in left[0].objects                 # action names are read for leftover markers too


def test_checks_that_need_a_missing_export_are_not_run_never_clear():
    er = _estate_from(model([("M", "a", "", ("L",)), ("M", "b", "a * 2", ("L",))]))          # no Actions export, no Modules export, one model
    res = {r["num"]: r for r in checks.results(er)}
    for key in ("import-target-unread", "several-imports-one-target", "actions-stale", "module-notes", "model-feeds", "cross-model-duplicates"):
        r = res[checks.N(key)]
        assert r["status"] == "not run" and r["not_run"] and r["hits"] == 0, key
    assert res[checks.N("sum-lookup")]["status"] == "clear"
    assert "needs the Actions export" in report.check_result_text(res[checks.N("actions-stale")])


# ---- on the example estate, end to end

def test_example_estate_reports_every_check_and_finds_the_planted_ones():
    er = fleet.run(EX)
    rep = report.build(er)
    ck = rep["checks"]
    assert ck["total"] == len(checks.CHECKS) == ck["found"] + ck["clear"] + ck["not_run"] and [r["num"] for r in ck["results"]] == [c.num for c in checks.CHECKS]
    res = {r["key"]: r for r in ck["results"]}
    by_id = {x["id"]: x for x in rep["findings"]}
    ratio = [by_id[i] for i in res["ratio-summed"]["findings"]]
    odd = [by_id[i] for i in res["odd-one-out"]["findings"]]
    assert ratio and ratio[0]["objects"] == ["CAL06 Department Summary.Cost per FTE"] and ratio[0]["checks"] == [checks.N("ratio-summed")]
    assert odd and odd[0]["objects"] == ["CAL12 Driver Phasing.Insurance Phased"]
    assert res["over-dimensioned"]["status"] == "found" and res["leftover-names"]["status"] == "found" and res["several-imports-one-target"]["status"] == "found"
    assert any(n["model"] == "Workforce Planning" for n in res["effort-concentration"]["not_run"])      # exported before Calculation Effort existed
    for x in rep["findings"]:
        assert x["checks"], x["title"]                                 # every finding says which check produced it
    h = report_html.render(rep, csv_text=report.register_csv(rep))
    assert 'id="checks"' in h and f'id="check-{checks.N("ratio-summed")}"' in h and f'href="#check-{checks.N("ratio-summed")}"' in h
    assert f"{ck['total']} tests were run on these exports" in h[h.index('<section id="plan"'):h.index('<section id="impact"')]
    md = report.render_markdown(er)
    assert "## Tests run" in md and f"| {checks.N('odd-one-out')} | The odd one out" in md
