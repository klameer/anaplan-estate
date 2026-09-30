"""Thin, odd and hostile input: every optional column missing in turn and all at once, tiny models, formulas that do
not parse, names that carry markup, and the same input twice. Nothing may crash, every test must still be reported,
and no uploaded name may reach the page as markup."""
import sys, pathlib, csv, io, json, re
import pytest
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "src"))
from anaplan_estate import fleet, report, report_html, checks

EX = pathlib.Path(__file__).resolve().parents[1] / "examples" / "caldergate-estate"
FPA = EX / "2 Caldergate FP&A"


def _read(path):
    with open(path, encoding="utf-8-sig", newline="") as f:
        r = csv.DictReader(f)
        return list(r), list(r.fieldnames)


def _write(path, rows, cols):
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=cols, extrasaction="ignore")
        w.writeheader(); w.writerows(rows)


def _full_run(root, names=None):
    """The whole pipeline, as the CLI and the web service run it."""
    er = fleet.run(root, names=names)
    rep = report.build(er)
    html = report_html.render(rep, csv_text=report.register_csv(rep))
    md = report.render_markdown(er)
    json.dumps(rep, default=str)
    assert len(rep["checks"]["results"]) == len(checks.CHECKS)
    assert {r["status"] for r in rep["checks"]["results"]} <= {"found", "clear", "not run"}
    assert all(x["checks"] for x in rep["findings"])
    assert "<title>" in html and "## Action plan" in md
    return er, rep, html


LI_ROWS, LI_COLS = _read(FPA / "Line Items.csv")
OPTIONAL = [c for c in LI_COLS if c not in ("", "Formula")]


@pytest.mark.parametrize("col", OPTIONAL)
def test_each_optional_column_can_be_absent(tmp_path, col):
    _write(tmp_path / "M" / "Line Items.csv", LI_ROWS, [c for c in LI_COLS if c != col])
    er, rep, html = _full_run(tmp_path)
    res = {r["key"]: r for r in rep["checks"]["results"]}
    needs = {"Cell Count": "cell-concentration", "Calculation Effort": "effort-concentration", "Summary": "ratio-summed", "Referenced By": "referenced-by-agreement"}
    if col in needs:                                          # a test that lost its column says so; it is never reported clear
        assert res[needs[col]]["status"] == "not run" and res[needs[col]]["not_run"], col
    base = _baseline()
    lost = [k for k, r in res.items() if base[k] == "found" and r["status"] == "clear"]
    assert not lost, f"without '{col}' these tests went from found to clear instead of not run: {lost}"


_BASE = {}


def _baseline():
    """Status of every test on the full FP&A export, to compare a thinner export against."""
    if not _BASE:
        import tempfile
        d = pathlib.Path(tempfile.mkdtemp(prefix="estate-test-"))
        _write(d / "M" / "Line Items.csv", LI_ROWS, LI_COLS)
        _BASE.update({r["key"]: r["status"] for r in _full_run(d)[1]["checks"]["results"]})
        import shutil; shutil.rmtree(d, ignore_errors=True)
    return _BASE


def test_two_folders_that_clean_to_one_name_stay_two_models(tmp_path):
    for folder in ("1 FPA", "2 FPA"):
        _write(tmp_path / folder / "Line Items.csv", LI_ROWS, LI_COLS)
    er, rep, html = _full_run(tmp_path)
    one = _full_run(FPA.parent)                                # the whole example, for a per-model count to compare with
    assert [m.name for m in er.models] == ["FPA", "FPA (2)"]
    keys = [c["key"] for c in rep["plan"]["candidates"]]
    assert len(keys) == len(set(keys))
    for r in rep["checks"]["results"]:                         # each model reports its own hits: two identical models, identical counts
        if r["scope"] == "model" and r["by_model"]:
            assert len(r["by_model"]) == 2 and r["by_model"][0]["hits"] == r["by_model"][1]["hits"], r["key"]


def test_a_plan_size_below_one_means_no_cap():
    from anaplan_estate import plan
    er = fleet.run(EX)
    every = plan.select(er, top=None)
    assert len(every["actions"]) == every["met_bar"] > 0
    for top in (0, -1):
        assert [a["key"] for a in plan.select(er, top=top)["actions"]] == [a["key"] for a in every["actions"]]


def test_test_counts_match_what_the_report_lists():
    er, rep, html = _full_run(EX)
    res = {r["key"]: r for r in rep["checks"]["results"]}
    by_id = {x["id"]: x for x in rep["findings"]}
    # 2.3 counts the line items its finding lists, model by model, and nothing the finding does not show
    unread = res["unread-line-items"]
    assert unread["findings"] and {p["model"] for p in unread["by_model"]} == {by_id[i]["model"] for i in unread["findings"]}
    # one object is one hit, however many ways a rule caught it
    for m in er.models:
        for c in checks.CHECKS:
            if c.rules and c.counted == "rules":
                objs = {x.object for x in m.lint.findings if x.rule in c.rules}
                got = next((p["hits"] for p in res[c.key]["by_model"] if p["model"] == m.name), 0)
                extra = sum(fd.hits.get(c.num, 0) for fd in er.findings if fd.model == m.name)
                assert got == len(objs) + extra, (c.key, m.name)


def test_only_the_two_required_columns(tmp_path):
    _write(tmp_path / "M" / "Line Items.csv", LI_ROWS, ["", "Formula"])
    er, rep, html = _full_run(tmp_path)
    assert rep["scope"]["line_items"] > 0 and rep["input_notices"]
    res = {r["key"]: r["status"] for r in rep["checks"]["results"]}
    assert res["cell-concentration"] == res["ratio-summed"] == res["effort-concentration"] == res["over-dimensioned"] == "not run"


@pytest.mark.parametrize("rows", [
    [{"": "Only", "Format": '{"dataType":"NUMBER"}', "Formula": "", "Module Name": "M"}],
    [{"": "A", "Format": '{"dataType":"NUMBER"}', "Formula": "A", "Module Name": "M"}],                       # refers to itself
    [{"": "A", "Format": '{"dataType":"NUMBER"}', "Formula": "((( IF THEN", "Module Name": "M"},            # does not parse
     {"": "B", "Format": '{"dataType":"NUMBER"}', "Formula": "'No Such Module'.X / 0", "Module Name": "M"},
     {"": "C", "Format": "not json", "Formula": "B / B", "Summary": "also not json", "Cell Count": "lots", "Calculation Effort": "n/a", "Module Name": "M"}],
    [{"": f"L{i}", "Format": '{"dataType":"NUMBER"}', "Formula": "", "Module Name": ""} for i in range(3)],   # no module at all
])
def test_tiny_and_broken_models_do_not_crash(tmp_path, rows):
    _write(tmp_path / "M" / "Line Items.csv", rows, ["", "Format", "Formula", "Summary", "Applies To", "Cell Count", "Calculation Effort", "Referenced By", "Module Name"])
    _full_run(tmp_path)


def test_empty_actions_and_modules_exports_do_not_crash(tmp_path):
    _write(tmp_path / "M" / "Line Items.csv", LI_ROWS, LI_COLS)
    (tmp_path / "M" / "Actions.csv").write_text(",Action,Start Date and Time (UTC)\n", encoding="utf-8")
    (tmp_path / "M" / "Modules.csv").write_text(",Functional Area,Applies To\n", encoding="utf-8")
    _full_run(tmp_path)


HOSTILE = ['<script>alert(1)</script>', '"><img src=x onerror=alert(2)>', "</script><script>alert(3)</script>", "'; DROP TABLE x; --", "{{7*7}} ${7*7} OLD"]


def test_names_and_formulas_from_the_upload_never_reach_the_page_as_markup(tmp_path):
    """Module, line item, action and model names, notes and formulas are whatever the uploader typed."""
    fmt = '{"dataType":"NUMBER","unitsType":"PERCENTAGE"}'
    summ = '{"summaryMethod":"SUM","timeSummaryMethod":"SUM","timeSummarySameAsMainSummary":true}'
    rows = []
    for i, h in enumerate(HOSTILE):
        mod = f"Mod {h}"
        rows += [{"": f"A {h}", "Format": fmt, "Formula": "", "Summary": summ, "Applies To": "L", "Cell Count": "60000000", "Calculation Effort": "10", "Notes": h, "Module Name": mod},
                 {"": f"B {h}", "Format": fmt, "Formula": f"'A {h}' / 'A {h}' + 1.23", "Summary": summ, "Applies To": "L, K", "Cell Count": "60000000", "Calculation Effort": "10", "Notes": h, "Module Name": mod},
                 {"": f"C {h}", "Format": '{"dataType":"TEXT"}', "Formula": f'"{h}" & NAME(ITEM(L))', "Summary": summ, "Applies To": "L, K", "Cell Count": "60000000", "Calculation Effort": "10", "Module Name": mod}]
    d = tmp_path / "1 Model"                                  # the model name is set below: Windows refuses markup in a folder name, a zip on Linux does not
    _write(d / "Line Items.csv", rows, ["", "Format", "Formula", "Summary", "Applies To", "Cell Count", "Calculation Effort", "Notes", "Module Name"])
    acts = [",Action,Start Date and Time (UTC),Most recent duration (ms),Notes,Used in Processes,Used in Dashboards", "Imports,,,,,,"]
    acts += [f'"Import {h.replace(chr(34), chr(34) * 2)}","Import into \'Mod {h.replace(chr(34), chr(34) * 2)}\'",2020-01-01 10:00:00,5,,,' for h in HOSTILE]
    (d / "Actions.csv").write_text("\n".join(acts) + "\n", encoding="utf-8")
    er, rep, html = _full_run(tmp_path, names={"Model": 'Model <b>bold</b> & "quoted"'})
    assert er.models[0].name.startswith("Model <b>") and rep["findings"] and rep["plan"]["candidates"]      # the names are in findings, cards and tables, so the check below means something
    body = html[:html.index('<script type="application/json" id="report-data">')]
    data = html[html.index('<script type="application/json" id="report-data">'):]
    for bad in ("<script>alert", "<img src=x", "onerror=alert(2)>", "<b>bold</b>"):
        assert bad not in body, bad
    assert "&lt;script&gt;alert(1)&lt;/script&gt;" in body    # present, as text
    payload = data[data.index(">") + 1:data.index("</script>")]
    assert "</script" not in payload.lower() and json.loads(payload)   # the embedded data cannot close its own script element


def test_same_input_twice_gives_the_same_report(tmp_path):
    a = _full_run(EX)
    b = _full_run(EX)
    assert a[2] == b[2]
    strip = lambda rep: json.dumps({k: v for k, v in rep.items() if k != "generated"}, default=str, sort_keys=True)
    assert strip(a[1]) == strip(b[1])
    assert [c["key"] for c in a[1]["plan"]["candidates"]] == [c["key"] for c in b[1]["plan"]["candidates"]]


def test_a_large_model_is_analysed_in_seconds(tmp_path):
    """8,000 line items in 80 modules with the shapes the tests look at; the hosted service stops a run at 180 seconds."""
    import time
    fmt, summ = '{"dataType":"NUMBER"}', '{"summaryMethod":"SUM","timeSummaryMethod":"SUM","timeSummarySameAsMainSummary":true}'
    rows = []
    for m in range(80):
        mod = f"CAL{m:02d} Module"
        rows.append({"": "Base", "Format": fmt, "Formula": "", "Summary": summ, "Applies To": "L, K", "Time Scale": "Month", "Versions": "All", "Cell Count": "120000", "Calculation Effort": "0.01", "Module Name": mod})
        for i in range(99):
            prev = "Base" if i == 0 else f"Item {i - 1}"
            f = [f"IF '{prev}' > 0 THEN '{prev}' * 1.05 ELSE 0", f"'{prev}' / Base", f"'{prev}'", f"'CAL{(m + 1) % 80:02d} Module'.Base + '{prev}'"][i % 4]
            rows.append({"": f"Item {i}", "Format": fmt, "Formula": f, "Summary": summ, "Applies To": "L, K", "Time Scale": "Month", "Versions": "All", "Cell Count": "120000", "Calculation Effort": "0.01", "Module Name": mod})
    _write(tmp_path / "Big" / "Line Items.csv", rows, ["", "Format", "Formula", "Summary", "Applies To", "Time Scale", "Versions", "Cell Count", "Calculation Effort", "Module Name"])
    t = time.time()
    er, rep, html = _full_run(tmp_path)
    assert rep["scope"]["line_items"] == 8000 and time.time() - t < 60


def test_every_in_page_link_in_the_report_has_a_target():
    """Test badges, finding links, the top-n table and the 'everything else' table all point somewhere that exists."""
    er, rep, html = _full_run(EX)
    body = html[:html.index('<script type="application/json" id="report-data">')]
    ids = set(re.findall(r'\bid="([^"]+)"', body))
    links = set(re.findall(r'href="?#([^"\s>]+)', body))
    dangling = sorted(l for l in links if l not in ids and not l.startswith("impact"))
    assert not dangling, dangling[:10]
    assert {f"check-{c.num}" for c in checks.CHECKS} <= ids                 # every test has a row to land on
    nodes = {str(n[0]) for n in rep["graph"]["nodes"]}
    for l in links:
        if l.startswith("impact="):
            v = l.split("=", 1)[1]
            assert v in nodes or v.startswith("m"), l


def test_a_saved_report_declares_its_encoding_and_fits_a_phone(tmp_path):
    """The report is one file people save and open from disk: a name with an accent must survive without a server saying UTF-8."""
    rows = [dict(r) for r in LI_ROWS[:40]]
    rows[1][""] = "Coût par région (été) – Größe"
    _write(tmp_path / "M" / "Line Items.csv", rows, LI_COLS)
    er, rep, html = _full_run(tmp_path)
    head = html[:300].lower()
    assert head.startswith("<!doctype html>") and '<meta charset="utf-8">' in head and "width=device-width" in head
    assert "Coût par région (été)" in html
