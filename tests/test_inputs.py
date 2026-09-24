"""Input guards: exports that differ from the ones the tool was built on must fail loudly or degrade with a visible notice,
never produce a confident report from misread data."""
import sys, pathlib, csv, shutil
import pytest
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "src"))
from anaplan_estate import fleet, report, report_html
from anaplan_estate.model import InputError, _int, _pct

EX = pathlib.Path(__file__).resolve().parents[1] / "examples" / "caldergate-estate" / "2 Caldergate FP&A"


def _rows():
    src = next(EX.rglob("Line Items*.csv"))
    with open(src, encoding="utf-8-sig", newline="") as f:
        r = csv.DictReader(f)
        return list(r), list(r.fieldnames)


def _write(tmp, rows, cols, delim=",", enc="utf-8-sig"):
    d = tmp / "M"; d.mkdir(parents=True, exist_ok=True)
    with open(d / "Line Items.csv", "w", encoding=enc, newline="") as f:
        w = csv.DictWriter(f, fieldnames=cols, delimiter=delim, extrasaction="ignore"); w.writeheader(); w.writerows(rows)
    return tmp


def _baseline(tmp):
    rows, cols = _rows()
    return fleet.run(_write(tmp / "b", rows, cols)).models[0]


def test_numbers_in_other_locales():
    assert _int("5,017,824") == 5017824 and _int("5.017.824") == 5017824 and _int("5 017 824") == 5017824 and _int("") == 0
    assert _pct("16.04") == 16.04 and _pct("16,04") == 16.04 and _pct("16.04%") == 16.04 and _pct("1 234,5") == 1234.5 and _pct("1,234.5") == 1234.5


def test_semicolon_delimiter_is_sniffed(tmp_path):
    rows, cols = _rows()
    base = _baseline(tmp_path)
    m = fleet.run(_write(tmp_path / "s", rows, cols, delim=";")).models[0]
    assert m.facts["line_items"] == base.facts["line_items"] and m.facts["cells"] == base.facts["cells"]
    assert any("delimiter" in w for w in m.facts["warnings"])


def test_missing_formula_column_stops_with_a_message(tmp_path):
    rows, cols = _rows()
    with pytest.raises(InputError) as e:
        fleet.run(_write(tmp_path / "f", rows, [c for c in cols if c != "Formula"]))
    assert "Formula" in str(e.value) and "Found columns" in str(e.value)


def test_missing_format_column_keeps_input_line_items(tmp_path):
    rows, cols = _rows()
    base = _baseline(tmp_path)
    m = fleet.run(_write(tmp_path / "nf", rows, [c for c in cols if c != "Format"])).models[0]
    assert m.facts["line_items"] == base.facts["line_items"]
    assert any(c.startswith("Format:") for c in m.facts["missing_columns"])


def test_missing_referenced_by_is_not_checkable_not_zero(tmp_path):
    rows, cols = _rows()
    m = fleet.run(_write(tmp_path / "nr", rows, [c for c in cols if c != "Referenced By"])).models[0]
    rc = m.facts["referenced_by_check"]
    assert rc["agreement"] is None and "absent" in rc["definition"]
    assert any(r == "referenced-by" for r, _ in m.facts["coverage"]["rules_skipped"])


def test_missing_cell_count_is_unavailable_not_zero(tmp_path):
    rows, cols = _rows()
    er = fleet.run(_write(tmp_path / "nc", rows, [c for c in cols if c != "Cell Count"]))
    m = er.models[0]
    assert m.facts["has_cells"] is False and any(r == "cells" for r, _ in m.facts["coverage"]["rules_skipped"])
    rep = report.build(er)
    assert any("Cell Count" in n for n in rep["input_notices"])
    h = report_html.render(rep, csv_text=report.register_csv(rep))
    assert "Input notices" in h and "Cell Count" in h[h.index('<section id="plan"'):h.index('<section id="impact"')]


def test_effort_over_100_is_flagged(tmp_path):
    rows, cols = _rows()
    rows = [dict(r, **{"Calculation Effort": str(_pct(r["Calculation Effort"]) * 100) if r["Calculation Effort"] else ""}) for r in rows]   # as if read 100x too large
    m = fleet.run(_write(tmp_path / "e", rows, cols)).models[0]
    assert any("exceed 100%" in w for w in m.facts["warnings"])


def test_cp1252_export_is_read_with_a_notice(tmp_path):
    rows, cols = _rows()
    rows[5][""] = rows[5][""] + " café"
    m = fleet.run(_write(tmp_path / "c", rows, cols, enc="cp1252")).models[0]
    assert any("cp1252" in w for w in m.facts["warnings"]) and any("café" in k[1] for k in m.model.line_items)


def test_large_estate_light_mode_drops_search_index_and_says_so():
    er = fleet.run(EX.parent)
    rep = report.build(er)
    h = report_html.render(rep, csv_text=report.register_csv(rep), light=True)
    assert "Large estate" in h and "search index is left out" in h
    art = h[h.index('<article class="f" id="F1"'):]; art = art[:art.index("</article>")]
    idx = art[art.index('<div class="idx">'):art.index("</div>", art.index('<div class="idx">'))]
    assert "evidence:" not in idx and "object:" in idx
    full = report_html.render(rep, csv_text=report.register_csv(rep))
    assert "Large estate" not in full and report_html.LIGHT_ABOVE == 25_000


def test_subsidiary_views_found_without_modules_export(tmp_path):
    import shutil
    shutil.copytree(EX, tmp_path / "FPA")
    for f in (tmp_path / "FPA").rglob("Modules*.csv"):
        f.unlink()
    m = fleet.run(tmp_path).models[0]
    subs = [x for x in m.lint.findings if x.rule == "A-SUBSIDIARY"]
    assert any(x.line_item == "Launched?" and x.module == "CAL01 Volumes" for x in subs) and all("inferred" in x.message for x in subs)
    assert "A-SUBSIDIARY" not in [r for r, _ in m.facts["coverage"]["rules_skipped"]] and any(r == "H-NOTES" for r, _ in m.facts["coverage"]["rules_skipped"])
    assert any("taken as the dimensions" in c for c in m.facts["coverage"]["confirmed"])


def test_generality_note_is_on_the_plan():
    er = fleet.run(EX.parent)
    rep = report.build(er)
    h = report_html.render(rep, csv_text=report.register_csv(rep))
    plan = h[h.index('<section id="plan"'):h.index('<section id="impact"')]
    assert "pattern-matched" in plan and "catalogue is the place to look" in plan
