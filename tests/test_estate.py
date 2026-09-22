import sys, pathlib, json
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "src"))
from anaplan_estate import fleet
from anaplan_estate.cli import main

FX = pathlib.Path(__file__).parent / "fixtures" / "estate"


def test_discover_and_names():
    specs = fleet.discover(FX)
    assert [s["name"] for s in specs] == ["Caldergate Planning", "Caldergate HR"]
    assert all(s["actions"] for s in specs)


def test_estate_run_edges_duplicates_actions():
    er = fleet.run(FX)
    assert [e["from"] + ">" + e["to"] for e in er.edges] == ["Caldergate Planning>Caldergate HR"]
    assert er.edges[0]["actions"] == 2 and "INP01 Headcount" in er.edges[0]["targets"]
    assert "NetSuite" in er.external and "Treasury file" in er.external
    assert er.duplicates and er.duplicates[0]["line_item"] == "Current Period?"
    hr = next(m for m in er.models if m.name == "Caldergate HR")
    a = hr.facts["actions"]
    assert a["orphan_count"] == 1 and a["stale_count"] == 1          # Import Open Roles.csv: no process, never run
    assert hr.facts["has_effort"] and hr.facts["effort_top"][0][0] == "CAL01 Headcount Cost.Cost"
    pl = next(m for m in er.models if m.name == "Caldergate Planning")
    assert pl.facts["actions"]["stale_count"] == 1                    # FX import last run 2024
    rc = pl.facts["referenced_by_check"]; assert rc["agreement"] is not None and rc["agree"] > 0   # fixture column is fictional; real exports score it
    assert "A-SUBSIDIARY" in pl.facts["rules_skipped"]                # no Modules export
    d = er.to_dict(); assert len(d["models"]) == 2 and d["edges"][0]["basis"].startswith("inferred")


def test_render_and_cli(tmp_path, capsys):
    er = fleet.run(FX)
    md = fleet.render_markdown(er)
    for h in ("# Anaplan estate: 2 models", "How the models connect", "flowchart LR", "Logic duplicated", "## Procedures performed", "# Caldergate HR", "Where the calculation time goes"):
        assert h in md
    main([str(FX), "--out", str(tmp_path / "e.md"), "--json", str(tmp_path / "e.json")])
    j = json.loads((tmp_path / "e.json").read_text(encoding="utf-8"))
    assert j["edges"][0]["to"] == "Caldergate HR"
    main([str(FX), "--list"]); assert "Caldergate HR" in capsys.readouterr().out


EX = pathlib.Path(__file__).resolve().parents[1] / "examples" / "caldergate-estate"


def test_example_estate_finds_the_planted_faults():
    """examples/caldergate-estate/PLANTED.md lists what was put in; this keeps the report finding it."""
    er = fleet.run(EX)
    by = {m.name: m for m in er.models}
    assert set(by) == {"Caldergate Data Hub", "Caldergate FP&A", "Workforce Planning", "Board Reporting"}
    assert all(m.facts["parse_rate"] == 1.0 for m in er.models)
    fp = by["Caldergate FP&A"].lint.counts["by_rule"]
    for rule in ("A-LI-COUNT", "A-IF-COUNT", "F-LONG", "F-HARDCODE", "F-DIVIDE", "F-MIXED-CLAUSE", "A-DAISY", "G-CYCLE",
                 "G-HUB", "G-EMPTY-MODULE", "A-SUBSIDIARY", "A-TEXT-FORMAT", "A-FINDITEM", "A-TEXT-JOIN", "A-SUMMARY-ON", "G-UNUSED"):
        assert fp.get(rule), rule
    assert by["Caldergate FP&A"].facts["effort_by_module"][0][0] == "CAL05 Opex OLD"        # the leftover module carries the time
    assert by["Caldergate FP&A"].facts["hubs"][0][0] == "SYS01 Time Settings.Actual?"
    acts = by["Caldergate FP&A"].facts["actions"]
    assert "Import from Caldergate Hub v1 - Cost Centres" in acts["orphans"] and any(s[0] == "Import FX from Treasury file" for s in acts["stale"])
    assert "Caldergate Hub v1" in er.external and len(er.external["Workday"]) == 2
    assert {(e["from"], e["to"]) for e in er.edges} >= {("Caldergate Data Hub", "Caldergate FP&A"), ("Workforce Planning", "Caldergate FP&A"),
                                                        ("Caldergate FP&A", "Board Reporting"), ("Caldergate Data Hub", "Workforce Planning")}
    assert {d["line_item"] for d in er.duplicates} >= {"Employer NI", "Working Days", "Current Period?"}
    assert not by["Workforce Planning"].facts["has_effort"]
