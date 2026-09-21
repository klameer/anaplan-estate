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
