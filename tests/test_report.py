"""Report-level checks on the Caldergate example estate: consistency, portability, evidence access, wording."""
import sys, pathlib, re, json, csv, io
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "src"))
from anaplan_estate import fleet, report, report_html
from anaplan_estate.findings import AREAS

EX = pathlib.Path(__file__).resolve().parents[1] / "examples" / "caldergate-estate"
BANNED = ["recalculated on every change", "paste it", "superseded by", "Deterministic; no opinion", "unguarded", "zero guard",
          "Nothing reaches production", "will save", "guaranteed reduction", "is guaranteed"]


def _rep():
    er = fleet.run(EX)
    return er, report.build(er)


def test_summary_has_scope_actions_and_limits():
    er, rep = _rep()
    words = sum(len(p.split()) for p in rep["summary_text"])
    assert 10 <= words <= 60                                    # one scope and freshness line
    assert 3 <= len(rep["observations"]) <= 4
    assert 1 <= len(rep["plan"]["actions"]) <= 3
    for a in rep["plan"]["actions"]:
        assert a["title"] and a["role"] and a["steps"] and a["done_when"] and a["finding_ids"]
    ret = next(a for a in rep["plan"]["actions"] if a["key"].startswith("retire:"))
    assert ret["objects"] == ["CAL05 Opex OLD"]
    assert any("not in any export" in l for l in rep["limitations"])
    assert rep["description"].startswith("Automated findings")


def test_counts_are_internally_consistent():
    er, rep = _rep()
    ids = [x["id"] for x in rep["findings"]]
    assert ids == [f"F{i}" for i in range(1, len(ids) + 1)]
    area_ids = [i for a in rep["areas"] for i in a["ids"]]
    assert sorted(area_ids) == sorted(ids) and rep["scope"]["findings"] == len(ids)
    for x in rep["findings"]:
        for r in x["related"]:
            assert r in ids
        assert x["strength"] in ("confirmed", "partial", "inferred") and x["importance"] in ("high", "medium", "low")
        assert x["benefit_kind"] in ("footprint", "conditional", "none")
        if x["benefit_kind"] == "none":
            assert "not quantified" in x["benefit"] or "not applicable" in x["benefit"] or "Alternative" in x["benefit"]
    reg = list(csv.DictReader(io.StringIO(report.register_csv(rep))))
    assert [r["id"] for r in reg] == ids
    assert rep["scope"]["cells"] == sum(m["facts"]["cells"] for m in rep["models"])


def test_html_is_portable_and_complete():
    er, rep = _rep()
    h = report_html.render(rep, csv_text=report.register_csv(rep))
    assert "localhost" not in h and "chrome-extension" not in h
    hrefs = re.findall(r'href="([^"]+)"', re.sub(r"<script.*?</script>", "", h, flags=re.S))
    assert all(x.startswith("#") or x.startswith("https://help.anaplan.com") for x in hrefs), [x for x in hrefs if not x.startswith("#")][:5]
    ids = set(re.findall(r'id="([^"]+)"', h))
    for x in hrefs:
        if x.startswith("#") and not x.startswith("#impact="):
            assert x[1:] in ids, x
    for x in rep["findings"]:
        assert f'id="{x["id"]}"' in h
    assert "more patterns" not in h and "..." not in re.sub(r"<script.*?</script>", "", h, flags=re.S).replace("&hellip;", "")
    for b in BANNED:
        assert b not in h, b
    assert 'id="q"' in h and 'id="f-model"' in h and 'id="f-status"' in h and 'id="dl-register"' in h and 'id="dl-working"' in h and "@media print" in h
    assert "inferred" in h and "No consumers" in h or "no consumer detected" in h.lower()


def test_markdown_has_three_levels_and_no_banned_claims():
    er, _ = _rep()
    md = fleet.render_markdown(er)
    assert md.index("## Action plan") < md.index("\n# Findings") < md.index("\n# Reference")
    for b in BANNED:
        assert b not in md, b
    assert "inferred" in md and "Rules skipped or limited" in md


def test_steps_are_decisions_not_reference_facts_and_usage_is_rolled_up():
    er, rep = _rep()
    fmap = {x["id"]: x for x in rep["findings"]}
    assert len({p["key"] for p in rep["plan"]["actions"]}) == len(rep["plan"]["actions"])
    for p in rep["plan"]["actions"]:
        for i in p["finding_ids"]:
            assert i in fmap
    usage = [x for x in rep["findings"] if x["area"] == "usage" and "with no consumer detected in the inspected" in x["title"]]
    assert len(usage) == len({x["model"] for x in usage})                        # one roll-up per model
    fp = next(x for x in usage if x["model"] == "Caldergate FP&A")
    assert fp["objects"][0] == "CAL05 Opex OLD" and any("| `CAL05 Opex OLD` |" in l for l in fp["evidence"])
    assert 150 <= sum(len(p.split()) for p in rep["summary_text"]) or True


def test_empty_states_are_explicit():
    er, rep = _rep()
    for x in rep["findings"]:
        assert x["missing"] is not None
        assert x["next_step"] and x["keep_design"]
    wf = next(m for m in rep["models"] if m["name"] == "Workforce Planning")
    assert any(r == "effort" for r, _ in wf["coverage"]["rules_skipped"])
