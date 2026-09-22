"""Reader-journey checks: opening length and distinctness, compact findings, search index, sorting values, terminology."""
import sys, pathlib, re, csv, io
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "src"))
from anaplan_estate import fleet, report, report_html

EX = pathlib.Path(__file__).resolve().parents[1] / "examples" / "caldergate-estate"


def _rep():
    er = fleet.run(EX)
    rep = report.build(er)
    return er, rep, report_html.render(rep, csv_text=report.register_csv(rep))


def _words(html_fragment):
    return len(re.sub(r"<[^>]+>", " ", html_fragment).split())


def test_opening_is_short_with_up_to_three_distinct_investigations():
    er, rep, h = _rep()
    inv = rep["investigations"]
    assert 1 <= len(inv) <= 3 and len({p["key"] for p in inv}) == len(inv)
    for p in inv:
        assert p["title"] and p["sentence"] and p["who"] and p["next"] and p["ids"]
    usage = [p for p in inv if p["key"] == "usage"]
    assert usage and len(usage) == 1 and len(usage[0]["per_model"]) >= 2          # one card, model details underneath
    summary = h[h.index('<section id="summary">'):h.index('<section id="findings">')]
    visible = re.sub(r"<details.*?</details>", " ", summary, flags=re.S)
    visible = re.sub(r"<svg.*?</svg>", " ", visible, flags=re.S)
    assert 250 <= _words(visible) <= 520, _words(visible)
    assert "release checklist" not in visible.lower()


def test_metrics_distinguish_review_first_from_reference():
    er, rep, h = _rep()
    mt = rep["metrics"]
    assert mt["review_first"] + mt["reference"] == len(rep["findings"]) and mt["validated_defects"] == 0
    assert f'<b>{mt["review_first"]}</b> findings to review first' in h and "formulas parsed" not in h[:h.index('<section id="findings">')]


def test_compact_finding_shows_at_most_three_examples_and_full_list_in_details():
    er, rep, h = _rep()
    for x in rep["findings"]:
        art = h[h.index(f'id="{x["id"]}"'):]
        art = art[:art.index("</article>")]
        compact = art[:art.index('<details class="full">')]
        objs = compact[compact.index('<div class="objs">'):compact.index("</div>", compact.index('<div class="objs">'))]
        assert objs.count("<code>") <= 3
        assert x["object_label"] in compact
        full = art[art.index('<details class="full">'):]
        for o in x["objects"]:
            assert f"<code>{report_html._e(o)}</code>" in full
        if len(x["objects"]) > 3:
            assert f"and {len(x['objects']) - 3} more" in compact
    big = max(rep["findings"], key=lambda x: len(x["objects"]))
    art = h[h.index(f'id="{big["id"]}"'):]
    compact = art[:art.index('<details class="full">')]
    assert _words(compact) <= 260


def test_next_step_is_investigation_not_deletion():
    er, rep, h = _rep()
    for x in rep["findings"]:
        assert "wait one cycle" not in x["next_step"] and "wait a cycle" not in x["next_step"] and "delete" not in x["next_step"].lower()
        if x["area"] == "usage":
            assert "consumer" in x["next_step"] and "keep-or-retire" in x["next_step"]
            for imp in x["implementation"]:
                assert "Prerequisites" in imp or "Then" in imp or "repoint" in imp


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
    deep = [l for l in fp["evidence"] if l.startswith("| `")][-1].split("`")[1]        # a module named only in the evidence table
    art = h[h.index(f'id="{fp["id"]}"'):]
    art = art[:art.index("</article>")]
    idx = art[art.index('<div class="idx">'):art.index("</div>", art.index('<div class="idx">'))]
    assert deep in idx and f"object: {deep}" in idx.replace("&amp;", "&")
    dup = next((x for x in rep["findings"] if x["rules"] == ["REDUNDANT-EXACT"]), None)
    if dup:
        art = h[h.index(f'id="{dup["id"]}"'):]
        art = art[:art.index("</article>")]
        idx = art[art.index('<div class="idx">'):]
        assert "formula:" in idx and "object:" in idx


def test_sort_values_distinguish_unavailable_from_zero():
    er, rep, h = _rep()
    eff = next(x for x in rep["findings"] if x["rules"] == ["EFFORT"])
    assert eff["footprint_effort"] is None and eff["kind_label"] == "observation"
    art = h[h.index(f'id="{eff["id"]}"'):h.index("</header>", h.index(f'id="{eff["id"]}"'))]
    assert 'data-effort=""' in art
    reg = list(csv.DictReader(io.StringIO(report.register_csv(rep))))
    row = next(r for r in reg if r["id"] == eff["id"])
    assert row["footprint_effort"] == "" and row["kind_label"] == "observation"
    assert "unavailable last" in h and "Sort within category" in h


def test_commercial_action_configured_or_reported():
    er, rep, h = _rep()
    assert "Have a change planned in this estate?" in h and "Illustrative example" in h
    assert "Request route: not configured" in h                      # no service url passed here
    rep2 = report.build(er, service_url="https://example.invalid/review")
    h2 = report_html.render(rep2, csv_text=report.register_csv(rep2))
    assert 'href="https://example.invalid/review"' in h2 and "Request route: not configured" not in h2
