"""Reader-journey checks: the opening is a short action plan, findings open compact with complete object sets
behind a label, the search index covers collapsed evidence, sort values keep unavailable apart from zero, and
wording stays within what the exports support."""
import sys, pathlib, re, csv, io
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "src"))
from anaplan_estate import fleet, report, report_html

EX = pathlib.Path(__file__).resolve().parents[1] / "examples" / "caldergate-estate"


def _rep(**kw):
    er = fleet.run(EX)
    rep = report.build(er, **kw)
    return er, rep, report_html.render(rep, csv_text=report.register_csv(rep))


def _words(html_fragment):
    return len(re.sub(r"<[^>]+>", " ", html_fragment).split())


def _article(h, fid):
    art = h[h.index(f'<article class="f" id="{fid}"'):]
    return art[:art.index("</article>")]


def test_opening_is_a_plan_of_actions_worth_doing():
    er, rep, h = _rep()
    acts = rep["plan"]["actions"]
    assert len(acts) >= 1 and len({a["key"] for a in acts}) == len(acts) and rep["plan"]["considered"] == len(acts) and rep["plan"]["met_bar"] >= 1
    for a in acts:
        assert a["title"] and a["why"] and a["steps"] and a["done_when"] and a["role"] and a["finding_ids"]
    opening = h[h.index('<header class="top">'):h.index('<section id="impact"')]
    assert "release checklist" not in opening.lower() and "health score" not in opening.lower()
    plan_html = h[h.index('<section id="plan"'):h.index('<section id="impact"')]
    assert '<article class="f"' not in plan_html            # the catalogue does not follow the plan


def test_metrics_and_freshness_are_distinct_and_in_evidence():
    er, rep, h = _rep()
    mt = rep["metrics"]
    assert mt["review_first"] + mt["reference"] == len(rep["findings"]) and mt["validated_defects"] == 0
    assert f'{mt["review_first"]} findings to review first' in h
    fr = rep["freshness"]
    assert fr["export_date"] is None and fr["latest_action_run"] and fr["analysis_date"] == rep["generated"]
    assert "Export date unknown" in rep["summary_text"][0] and "Latest recorded action run" in rep["summary_text"][0]


def test_compact_finding_shows_preview_with_label_and_full_list_in_details():
    er, rep, h = _rep()
    for x in rep["findings"]:
        art = _article(h, x["id"])
        compact = art[:art.index('<details class="full">')]
        objs = compact[compact.index('<div class="objs">'):compact.index("</div>", compact.index('<div class="objs">'))]
        assert objs.count("<code>") == len(x["preview"]) <= 5
        assert x["preview_label"] in compact and x["object_label"] in compact
        full = art[art.index('<details class="full">'):]
        for o in x["objects"]:
            assert f"<code>{report_html._e(o)}</code>" in full
        if len(x["objects"]) > len(x["preview"]):
            assert f"Showing {len(x['preview'])} of {len(x['objects'])}" in compact
        else:
            assert f"All {len(x['objects'])}" in compact
        assert "and 2 more" not in compact


def test_next_step_is_investigation_not_deletion():
    er, rep, h = _rep()
    for x in rep["findings"]:
        assert "wait one cycle" not in x["next_step"] and "delete" not in x["next_step"].lower()
        if x["area"] == "usage":
            assert "consumer" in x["next_step"] and "keep-or-retire" in x["next_step"]
            for imp in x["implementation"]:
                assert "Prerequisites" in imp or "Then" in imp or "repoint" in imp
            assert "blank the formulas" not in " ".join(x["implementation"])


def test_terminology_partial_matches_and_export_dates():
    er, rep, h = _rep()
    assert "exact twin" not in h and "closest thing to a snapshot" not in h and "snapshot date" not in h
    assert "Export date unknown" in h and "Latest recorded action run" in h
    for x in rep["findings"]:
        if "twin" in x["observed"]:
            assert "matching line items" in x["observed"] and "match line for line" in x["observed"]


def test_search_index_covers_collapsed_evidence():
    er, rep, h = _rep()
    fp = next(x for x in rep["findings"] if x["model"] == "Caldergate FP&A" and "with no consumer detected in the inspected" in x["title"])
    deep = [l for l in fp["evidence"] if l.startswith("| `")][-1].split("`")[1]
    art = _article(h, fp["id"])
    idx = art[art.index('<div class="idx">'):art.index("</div>", art.index('<div class="idx">'))]
    assert deep in idx and f"object: {deep}" in idx.replace("&amp;", "&")
    dup = next((x for x in rep["findings"] if x["rules"] == ["REDUNDANT-EXACT"]), None)
    if dup:
        art = _article(h, dup["id"])
        idx = art[art.index('<div class="idx">'):].replace("&#x27;", "'").replace("&amp;", "&")
        assert "object:" in idx and dup["evidence"][-1].split("`")[-2] in idx


def test_sort_values_distinguish_unavailable_from_zero():
    er, rep, h = _rep()
    eff = next(x for x in rep["findings"] if x["rules"] == ["EFFORT"])
    assert eff["footprint_effort"] is None and eff["kind_label"] == "observation"
    art = _article(h, eff["id"])
    assert 'data-effort=""' in art[:art.index("<header>")]
    reg = list(csv.DictReader(io.StringIO(report.register_csv(rep))))
    row = next(r for r in reg if r["id"] == eff["id"])
    assert row["footprint_effort"] == "" and row["kind_label"] == "observation"
    assert "unavailable last" in h
    wf = next(m for m in rep["models"] if m["name"] == "Workforce Planning")
    assert not wf["facts"]["has_effort"] and "Calculation Effort: unavailable" in h


def test_help_link_only_when_configured_and_never_a_diagnostic():
    er, rep, h = _rep()
    assert "Want another pair of eyes" not in h and "Request route" not in h and "service-url" not in h
    rep2 = report.build(er, help_url="https://example.invalid/review")
    h2 = report_html.render(rep2, csv_text=report.register_csv(rep2))
    assert 'href="https://example.invalid/review"' in h2 and "Want another pair of eyes on this change?" in h2
    assert h2.count("example.invalid") == 1                                      # one discreet footer link, not repeated panels
    rep3 = report.build(er, help_url="mailto:someone@example.com")
    assert rep3["links"]["help"] == "" and "example.com" not in report_html.render(rep3)
