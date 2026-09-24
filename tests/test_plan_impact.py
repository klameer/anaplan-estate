"""Action plan selection, change-impact traversal, corrected facts, HTML views and exports.

Mechanics only: passing here shows the code does what it says on the example estate and on
synthetic fixtures, not that the selected actions are the right ones for any real estate."""
import sys, pathlib, re, csv, io, json, subprocess, shutil
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "src"))
from anaplan_estate import fleet, report, report_html, plan, impact
from anaplan_estate.plan import Candidate, rank_key, select
from anaplan_estate.model import Model, LineItem, Module
from anaplan_estate.graph import build_graph

EX = pathlib.Path(__file__).resolve().parents[1] / "examples" / "caldergate-estate"


def _rep(**kw):
    er = fleet.run(EX)
    rep = report.build(er, **kw)
    return er, rep, report_html.render(rep, csv_text=report.register_csv(rep))


def _words(fragment):
    return len(re.sub(r"<[^>]+>", " ", fragment).split())


# ---------------------------------------------------------------- action plan

def test_initial_reading_path_is_short_and_actionable():
    er, rep, h = _rep()
    opening = h[h.index('<header class="top">'):h.index('<section id="impact"')]
    acts = rep["plan"]["actions"]
    assert len(acts) == rep["plan"]["considered"] >= 1
    worth = [a["worth"] for a in acts]
    assert worth == sorted(worth, reverse=True) and rep["plan"]["met_bar"] == sum(worth)     # met-the-bar first, then the rest, each with a reason
    assert all(a["why_not"] for a in acts if not a["worth"]) and all(not a["why_not"] for a in acts if a["worth"])
    groups = rep["plan"]["groups"]
    plan_html = h[h.index('<section id="plan"'):h.index('<section id="impact"')]
    assert plan_html.index('<table class="sum">') < plan_html.index('<li class="action') and f'{rep["plan"]["met_bar"]} of {rep["plan"]["considered"]}' in plan_html
    assert sorted(k for g in groups for k in g["keys"]) == sorted(a["key"] for a in acts) and all(a["group"] for a in acts)
    assert groups[0]["keys"][0] == acts[0]["key"]                          # the group holding the top action comes first
    cards = re.findall(r'<li class="action(?: below)?" id="A\d+">', h)
    assert len(cards) == len(acts)
    for a in acts:
        assert a["title"] and a["why"] and 2 <= len(a["steps"]) <= 3 and a["done_when"] and a["role"]
        assert 100 <= len((a["title"] + " " + a["why"] + " " + " ".join(a["steps"]) + " " + a["done_when"]).split()) <= 300
        first_obj = min(i for i in (a["why"].find("the line item '"), a["why"].find("the module '")) if i >= 0)
        assert first_obj > 80                                          # a plain explanation comes before the first named object
    # no findings catalogue follows the plan on the initial path
    plan_html = h[h.index('<section id="plan"'):h.index('<section id="impact"')]
    assert '<article class="f"' not in plan_html and plan_html.count('<table class="sum">') == 1
    assert 'id="evidence" class="view" role="tabpanel" aria-label="Evidence" hidden' in h
    assert "Request route" not in h and "--service-url" not in h


def test_plan_merges_overlaps_and_names_bounded_objects():
    er, rep, h = _rep()
    acts = rep["plan"]["actions"]
    objs = [tuple(a["objects"]) for a in acts]
    assert len(set(objs)) == len(objs)
    for a in acts:
        assert len(a["objects"]) <= plan.BOUNDED
        for i in a["finding_ids"]:
            assert any(x["id"] == i for x in rep["findings"])
    # the leftover module is a suggested action (a consumer check), stated as footprint not saving
    ret = next(a for a in acts if a["key"].startswith("retire:"))
    assert "CAL05 Opex OLD" in ret["objects"] and "not a saving" in ret["why"] and ret["kind"] == "investigation"
    # the hotspot join names the objects rather than asking the reader to join them, and the card lists them with their formulas
    hot = next(a for a in acts if a["key"].startswith("hotspot-"))
    assert hot["objects"] and all("." in o for o in hot["objects"])
    assert [d["object"] for d in hot["detail"]] == hot["objects"] and all(d["formula"] for d in hot["detail"])
    card = h[h.index(f'<li class="action" id="A{acts.index(hot) + 1}"'):]; card = card[:card.index("</li></ol>") if "</li></ol>" in card else len(card)]
    assert '<table class="det">' in card and report_html._e(hot["detail"][0]["formula"]) in card and "listed under Evidence" not in card


def _cand(key, strength, kind, n_objects, cells=None, effort=None):
    return Candidate(key=key, kind=kind, title=key, why="w", steps=["a", "b"], done_when="d", role="r", model="M",
                     objects=[f"o{i}" for i in range(n_objects)], finding_ids=[], strength=strength, footprint_cells=cells, footprint_effort=effort)


def test_ranking_prefers_evidenced_bounded_change_over_huge_unsupported_candidate():
    huge = _cand("huge", "inferred", "investigation", 178, cells=10_000_000_000)
    small = _cand("small", "confirmed", "change", 2, cells=50_000, effort=6.0)
    partial_big = _cand("big-partial", "partial", "investigation", 1, cells=70_000_000, effort=50.0)
    order = sorted([huge, small, partial_big], key=rank_key)
    assert order[-1] is huge and order[0] is small
    assert sorted([huge, partial_big, small], key=rank_key) == order          # independent of input order


def test_select_can_return_fewer_than_three_and_explains_next_check(tmp_path):
    (tmp_path / "M1").mkdir()
    (tmp_path / "M1" / "Line Items.csv").write_text(
        "Line Items,Module Name,Format,Formula,Applies To,Time Scale,Versions,Summary,Cell Count,Referenced By\n"
        "A,Mod,\"{\"\"dataType\"\":\"\"NUMBER\"\"}\",,L,Month,All,SUM,100,\n"
        "B,Mod,\"{\"\"dataType\"\":\"\"NUMBER\"\"}\",A * 2,L,Month,All,SUM,100,\n", encoding="utf-8")
    er = fleet.run(tmp_path)
    sel = select(er)
    assert sel["met_bar"] <= 1
    if not sel["actions"]:
        assert sel["none"]["next_check"] and "Calculation Effort" in sel["none"]["next_check"]


# ---------------------------------------------------------------- corrected facts

def test_missing_actions_are_not_assessed_not_zero(tmp_path):
    shutil.copytree(EX / "2 Caldergate FP&A", tmp_path / "FPA")
    for f in (tmp_path / "FPA").rglob("Actions*.csv"):
        f.unlink()
    er = fleet.run(tmp_path)
    rep = report.build(er)
    m = rep["models"][0]
    assert m["facts"]["actions"] is None and m["coverage"]["files"]["actions"] is None
    usage = [x for x in rep["findings"] if x["area"] == "usage"]
    assert usage and all(x["action_usage"].startswith("not assessed") for x in usage)
    assert all("no export action reads them" not in x["observed"] for x in usage)
    assert any("not assessed" in l and "not zero" in l for l in rep["limitations"])
    gd = rep["graph"]
    assert gd["actions"][0] is None
    h = report_html.render(rep, csv_text=report.register_csv(rep))
    assert "not assessed (no Actions export)" in h
    reg = list(csv.DictReader(io.StringIO(report.register_csv(rep))))
    assert all(r["action_usage"].startswith("not assessed") for r in reg if r["area"].startswith("Usage"))


def test_empty_actions_file_is_assessed_as_zero(tmp_path):
    shutil.copytree(EX / "2 Caldergate FP&A", tmp_path / "FPA")
    for f in (tmp_path / "FPA").rglob("Actions*.csv"):
        f.write_text("Actions,Action,Start Date and Time (UTC),Most recent duration (ms),Used in Processes\n", encoding="utf-8")
    er = fleet.run(tmp_path)
    m = er.models[0]
    assert m.facts["actions"] is not None and m.facts["actions"]["imports"] == 0
    rep = report.build(er)
    assert rep["graph"]["actions"][0] == []
    assert all(x["action_usage"] == "none detected" for x in rep["findings"] if x["area"] == "usage")


def test_complete_object_sets_previews_counts_and_exports_agree():
    er, rep, h = _rep()
    reg = {r["id"]: r for r in csv.DictReader(io.StringIO(report.register_csv(rep)))}
    for x in rep["findings"]:
        assert x["preview"] == x["objects"][:len(x["preview"])] and len(x["preview"]) <= max(5, 0)
        m = re.match(r"(Showing (\d+) of (\d+)|All (\d+)) ", x["preview_label"])
        assert m, x["preview_label"]
        if m.group(2):
            assert int(m.group(2)) == len(x["preview"]) and int(m.group(3)) == len(x["objects"]) and len(x["preview"]) < len(x["objects"])
        else:
            assert int(m.group(4)) == len(x["objects"])
        assert reg[x["id"]]["objects"].split("; ") == x["objects"]
        art = h[h.index(f'<article class="f" id="{x["id"]}"'):]
        art = art[:art.index("</article>")]
        for o in x["objects"]:
            assert f"<code>{report_html._e(o)}</code>" in art and f"object: {report_html._e(o)}" in art
        assert f"All affected objects ({len(x['objects'])} {report_html._e(x['unit'])})" in art
    usage = next(x for x in rep["findings"] if x["area"] == "usage" and "G-UNUSED" in x["rules"] and x["model"] == "Caldergate FP&A")
    rows = [l for l in usage["evidence"] if l.startswith("| `")]
    assert len(rows) == len(usage["objects"]) and usage["object_label"].startswith(f"{len(usage['objects'])} module")
    eff = next(x for x in rep["findings"] if x["rules"] == ["EFFORT"] and x["model"] == "Caldergate FP&A")
    m = next(mm for mm in rep["models"] if mm["name"] == "Caldergate FP&A")
    assert len(eff["objects"]) == len(m["facts"]["effort_top"]) and eff["object_label"].startswith(f"top {len(eff['objects'])} line items")


def test_no_unsupported_claims():
    er, rep, h = _rep()
    banned = ["workspace size falls", "either read there or by nothing", "the large modules nothing reads", "will save", "guaranteed reduction", "is guaranteed", "Request route", "Prepared by", "Reviewed by"]
    for b in banned:
        assert b not in h, b
    assert "no consumer detected in the inspected" in h.lower() or "no consumer detected" in h.lower()
    assert "Agreement between two observed edge sets" in h
    assert "observed footprint" in h.lower()


def test_stable_uids_survive_renumbering():
    er = fleet.run(EX)
    a = {x.uid: x.title for x in er.findings}
    er2 = fleet.run(EX)
    assert {x.uid: x.title for x in er2.findings} == a and len(a) == len(er.findings)


# ---------------------------------------------------------------- graph traversal

def _synthetic():
    m = Model(name="T")
    def add(mod, name, formula=""):
        m.modules.setdefault(mod, Module(name=mod)); li = LineItem(module=mod, name=name, formula=formula, format_type="NUMBER", applies_to=("L",), cell_count=10)
        m.line_items[li.key] = li; m.modules[mod].line_items.append(name)
    add("S.rc", "a.b", "")                                   # punctuation in names
    add("S.rc", "x", "'S.rc'.'a.b' * 2")
    add("Mid", "x", "'S.rc'.x + 'S.rc'.'a.b'")               # duplicate name x in two modules; diamond
    add("Out", "y", "'Mid'.x + 'S.rc'.x")                    # multiple paths to y
    add("Out", "z", "'Out'.y")
    add("Cyc", "p", "'Cyc'.q + 'Out'.z")
    add("Cyc", "q", "'Cyc'.p")                               # cycle
    add("Alone", "w", "")                                    # disconnected
    return m


class _Run:
    def __init__(self, model):
        self.name = model.name; self.model = model; self.graph = build_graph(model)
        self.facts = {"has_effort": False, "parse_errors": 0, "referenced_by_check": {"agreement": None, "anaplan_only": 0}, "actions": None}
        class _A: actions = {}; processes = {}
        self.actions = _A()


class _ER:
    def __init__(self, model):
        self.models = [_Run(model)]; self.edges = []


def test_traversal_distances_cycles_diamonds_and_disconnected():
    m = _synthetic(); gd = impact.graph_data(_ER(m)); idx = impact.node_index(gd)
    ab = idx[(0, "S.rc", "a.b")]
    s = impact.summarise(gd, ab, "downstream")
    names = {(gd["nodes"][i][2], gd["nodes"][i][3]): d for i, d in s["distance"].items()}
    assert names == {("S.rc", "x"): 1, ("Mid", "x"): 1, ("Out", "y"): 2, ("Out", "z"): 3, ("Cyc", "p"): 4, ("Cyc", "q"): 5}
    assert s["direct"] == 2 and s["indirect"] == 4 and s["total"] == 6 and s["modules"] == 4 and s["max_distance"] == 5
    assert ab not in s["distance"] and s["footprint_cells"] == 60 and s["actions"] is None
    p = idx[(0, "Cyc", "p")]
    up = impact.summarise(gd, p, "upstream")
    assert up["distance"][idx[(0, "Cyc", "q")]] == 1 and up["distance"][ab] == 4 and p not in up["distance"]
    assert impact.summarise(gd, idx[(0, "Alone", "w")], "downstream")["total"] == 0
    lim = impact.summarise(gd, ab, "downstream", depth=2)
    assert set(lim["distance"].values()) == {1, 2} and lim["total"] == 3
    path = impact.path(s["parent"], ab, idx[(0, "Out", "z")])
    assert path[0] == ab and path[-1] == idx[(0, "Out", "z")] and len(path) == 4


def test_explorer_reconciles_with_graph_impact_on_the_example():
    er = fleet.run(EX); gd = impact.graph_data(er); idx = impact.node_index(gd)
    for mi, m in enumerate(er.models):
        for name, n in m.facts["hubs"][:3]:
            key = next(k for k in m.model.line_items if f"{k[0]}.{k[1]}" == name)
            s = impact.summarise(gd, idx[(mi, key[0], key[1])], "downstream")
            imp = m.graph.impact(key)
            assert s["total"] == len(imp) and s["direct"] == n == len(m.graph.rev[key]) and s["modules"] == len({k[0] for k in imp})
            assert s["distance"] == {idx[(mi, k[0], k[1])]: d for k, d in imp.items()}


def test_page_script_traversal_matches_python():
    """The page's BFS is the same algorithm as impact.reach; run it in node when available and compare on the synthetic graph."""
    node = shutil.which("node")
    if not node:
        import pytest; pytest.skip("node not available")
    m = _synthetic(); gd = impact.graph_data(_ER(m)); idx = impact.node_index(gd)
    js = report_html.JS
    fn = js[js.index(" function reach("):js.index(" function pathTo(")]
    adjfn = js[js.index(" function adj("):js.index(" function reach(")]
    script = ("var G=" + json.dumps(gd) + ";var down=null,up=null;" + adjfn + fn +
              "var ab=" + str(idx[(0, 'S.rc', 'a.b')]) + ";var r=reach([ab],'downstream',null);var u=reach([" + str(idx[(0, 'Cyc', 'p')]) + "],'upstream',null);"
              "console.log(JSON.stringify({d:r.dist,u:u.dist,l:reach([ab],'downstream',2).dist}))")
    out = subprocess.run([node, "-e", script], capture_output=True, text=True, check=True).stdout
    got = json.loads(out)
    py = impact.summarise(gd, idx[(0, "S.rc", "a.b")], "downstream")["distance"]
    assert {int(k): v for k, v in got["d"].items()} == py
    assert {int(k): v for k, v in got["u"].items()} == impact.summarise(gd, idx[(0, "Cyc", "p")], "upstream")["distance"]
    assert {int(k): v for k, v in got["l"].items()} == impact.summarise(gd, idx[(0, "S.rc", "a.b")], "downstream", depth=2)["distance"]


def test_graph_data_keeps_action_direction_and_inference_labels():
    er = fleet.run(EX); gd = impact.graph_data(er)
    fp = gd["models"].index("Caldergate FP&A")
    acts = gd["actions"][fp]
    assert acts and all(a["direction"] == ("writes" if a["kind"] == "import" else "reads") for a in acts)
    assert all(f["basis"].startswith("inferred") for f in gd["feeds"])
    assert gd["edge_types"]["feed"].startswith("model feeds model (inferred")
    assert all(isinstance(n[0], int) for n in gd["nodes"]) and all(len(e) == 2 for e in gd["edges"])


# ---------------------------------------------------------------- html: views, routing, exports, print

def test_html_views_links_and_no_network():
    er, rep, h = _rep(feedback_url="https://github.com/klameer/anaplan-estate/discussions", source_url="https://github.com/klameer/anaplan-estate", help_url="not a url")
    markup = re.sub(r"<script.*?</script>", "", h, flags=re.S)
    hrefs = re.findall(r'href="([^"]+)"', markup)
    assert all(x.startswith("#") or x.startswith("https://help.anaplan.com") or x.startswith("https://github.com/klameer/anaplan-estate") for x in hrefs)
    ids = set(re.findall(r'id="([^"]+)"', h))
    for x in hrefs:
        if x.startswith("#") and not x.startswith("#impact="):
            assert x[1:] in ids, x
    for x in hrefs:
        if x.startswith("#impact="):
            v = x[len("#impact="):]
            assert v.isdigit() or re.match(r"^m\d+:", v)
    assert "Suggest an improvement" in h and "Something missing or not quite right?" in h and "Report a problem with" in h
    assert "Want another pair of eyes" not in h and "not a url" not in h          # invalid help url dropped, silently in the page
    assert "Free and open source" in h and "Maintained by CodelessOps" in h and "Generated with CodelessOps Estate Review" in h
    assert 'role="tablist"' in h and h.count('role="tab"') == 3 and "@media print" in h and "print-full" in h
    assert "localStorage" in h and "not allowing local storage" in h
    assert 'id="dl-working"' in h and 'id="ix-download"' in h and "not assessed (no Actions export" in h


def test_html_without_links_omits_inactive_footer_items():
    er, rep, h = _rep()
    assert "Suggest an improvement" not in h and "Report a problem" not in h and "Want another pair of eyes" not in h and "Source</a>" not in h
    assert "Free and open source" in h


def test_register_and_working_register_carry_full_objects_and_uids():
    er, rep, h = _rep()
    reg = list(csv.DictReader(io.StringIO(report.register_csv(rep))))
    assert [r["id"] for r in reg] == [x["id"] for x in rep["findings"]]
    assert all(r["uid"] and r["preview_label"] and r["action_usage"] for r in reg)
    data = json.loads(h[h.index('id="report-data">') + len('id="report-data">'):h.index("</script>", h.index('id="report-data">'))].replace("<\\/", "</"))
    assert data["register_cols"] == report.REGISTER_COLS and len(data["register"]) == len(reg) and data["register"][0]["uid"] == reg[0]["uid"]
    assert data["graph"]["nodes"] and "suggested" in data["graph"]


def test_markdown_mirrors_plan_and_catalogue():
    er = fleet.run(EX); md = report.render_markdown(er)
    assert md.index("## Action plan") < md.index("## How the actions were chosen") < md.index("\n# Findings") < md.index("\n# Reference")
    assert "Done when." in md and "Free and open source" in md and "Request route" not in md
