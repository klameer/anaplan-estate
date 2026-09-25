"""The upload front: a zip or per-model files in, the same report out, temp files gone, bad uploads refused before
any analysis, a busy service says so, errors as plain pages."""
import sys, pathlib, io, zipfile, time, asyncio
import pytest
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "src"))
pytest.importorskip("fastapi"); pytest.importorskip("httpx")
from fastapi.testclient import TestClient
from anaplan_estate import web

EX = pathlib.Path(__file__).resolve().parents[1] / "examples" / "caldergate-estate"
client = TestClient(web.app)


def _zip(folders):
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        for d in folders:
            for f in d.rglob("*.csv"):
                z.write(f, f"{d.name}/{f.name}")
    return buf.getvalue()


def _tmp_dirs():
    return set(p.name for p in pathlib.Path(web.tempfile.gettempdir()).glob("estate-*"))


def test_index_leads_with_the_example_then_the_form():
    r = client.get("/")
    h = r.text
    assert r.status_code == 200 and 'action="/report"' in h and client.get("/health").text == "ok" and client.head("/health").status_code == 200
    assert "Do a quick review on your Anaplan estate" in h
    assert h.index('href="/example#plan"') < h.index("Review my estate") < h.index("id=review") < h.index("deleted as soon as the report is sent")
    assert h.count('class="row model"') == 1 and "Add another model" in h and "Or upload one zip" in h
    assert "adds imports, exports and processes" in h and "adds module notes" in h
    assert "example-impact.png" not in h and "anaplan-estate-web" in h and "localhost:8000" in h    # no hero image; local run still explained
    assert "CodelessOps" in h[h.index("<body"):h.index("<body") + 400]        # the provider is visible at the top


def test_example_change_impact_redirects_to_the_target_line_item():
    web._example_cache.clear()
    r = client.get("/example/change-impact", follow_redirects=False)
    assert r.status_code == 302 and r.headers["location"].startswith("/example#impact=") and r.headers["location"].split("=")[1].isdigit()
    assert client.get("/static/example-impact.png").status_code == 200


def test_zip_upload_returns_the_report_and_cleans_up():
    before = _tmp_dirs()
    data = _zip([EX / "1 Caldergate Data Hub", EX / "2 Caldergate FP&A"])
    r = client.post("/report", data={"title": "Test estate"}, files={"estate_zip": ("estate.zip", data, "application/zip")})
    assert r.status_code == 200 and "<title>Test estate</title>" in r.text and 'id="plan"' in r.text and "Caldergate FP&amp;A" in r.text
    assert "inline" in r.headers["content-disposition"] and r.headers["cache-control"] == "no-store"
    assert _tmp_dirs() <= before


def test_per_model_upload_with_empty_optional_parts():
    li = (EX / "2 Caldergate FP&A" / "Line Items.csv").read_bytes()
    ac = (EX / "2 Caldergate FP&A" / "Actions.csv").read_bytes()
    r = client.post("/report", data={"title": "", "model_name": ["FP&A"]},
                    files=[("line_items", ("Line Items.csv", li, "text/csv")), ("actions", ("Actions.csv", ac, "text/csv")), ("modules", ("", b"", "application/octet-stream"))])
    assert r.status_code == 200 and "FP&amp;A" in r.text and 'id="plan"' in r.text


def test_errors_are_plain_pages():
    r = client.post("/report", data={"title": "x"}, files={"estate_zip": ("x.zip", b"not a zip", "application/zip")})
    assert r.status_code == 400 and "not a zip" in r.text
    r = client.post("/report", data={"title": "x"})
    assert r.status_code == 400 and "Line Items*.csv" in r.text and "was found" in r.text


def test_size_limit(monkeypatch):
    monkeypatch.setattr(web, "MAX_MB", 0.0001)
    data = _zip([EX / "1 Caldergate Data Hub"])
    r = client.post("/report", files={"estate_zip": ("estate.zip", data, "application/zip")})
    assert r.status_code == 413


def test_bad_uploads_fail_fast_without_analysis(monkeypatch):
    calls = []
    monkeypatch.setattr(web, "_run_in_subprocess", lambda *a, **k: calls.append(a) or None)
    t = time.time()
    r = client.post("/report", files=[("line_items", ("Line Items.csv", b"Name,Format,Applies To\nA,NUMBER,L\n", "text/csv"))])
    assert r.status_code == 400 and "no &#x27;Formula&#x27; column" in r.text and "columns found" in r.text
    r = client.post("/report", files=[("line_items", ("Line Items.csv", b"", "text/csv"))])
    assert r.status_code == 400 and "is empty" in r.text
    r = client.post("/report", files=[("line_items", ("Line Items.csv", b"Line Items,Formula\n", "text/csv"))])
    assert r.status_code == 400 and "no line items" in r.text
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as z:
        z.writestr("model/notes.txt", "x")
    r = client.post("/report", files={"estate_zip": ("e.zip", buf.getvalue(), "application/zip")})
    assert r.status_code == 400 and "holds no" in r.text
    assert calls == [] and time.time() - t < 3


def test_rate_limit(monkeypatch):
    monkeypatch.setattr(web, "RATE_PER_HOUR", 2)
    web._rate.clear()
    codes = [client.post("/report", data={"title": "x"}).status_code for _ in range(3)]
    assert codes == [400, 400, 429]
    web._rate.clear()


def test_busy_returns_503_without_running(monkeypatch):
    monkeypatch.setattr(web, "QUEUE_WAIT_S", 0.01)
    monkeypatch.setattr(web, "_slots", asyncio.Semaphore(0))          # every worker taken
    called = []
    monkeypatch.setattr(web, "_run_in_subprocess", lambda *a, **k: called.append(1) or None)
    data = _zip([EX / "4 Board Reporting"])
    r = client.post("/report", files={"estate_zip": ("estate.zip", data, "application/zip")})
    assert r.status_code == 503 and "busy" in r.text and r.headers.get("retry-after") == "60" and not called


def test_example_route_is_cached():
    web._example_cache.clear()
    t = time.time(); r = client.get("/example"); first = time.time() - t
    assert r.status_code == 200 and "fictional example" in r.text
    t = time.time(); r2 = client.get("/example"); second = time.time() - t
    assert r2.text == r.text and second < first


def test_usage_counts_without_personal_data(monkeypatch, tmp_path):
    from anaplan_estate import usage as um
    monkeypatch.setattr(um, "STATS_TOKEN", "t0k")
    monkeypatch.setattr(um, "STATS_DIR", str(tmp_path))
    um.usage.__init__()
    assert client.get("/stats").status_code == 404 and client.get("/stats?token=wrong").status_code == 404
    client.get("/")
    client.post("/report", files={"estate_zip": ("estate.zip", _zip([EX / "4 Board Reporting"]), "application/zip")})
    client.post("/report", data={"title": "x"})
    s = client.get("/stats?token=t0k").json()
    today = s["today"]
    assert today["page_views"] == 1 and today["reports_ok"] == 1 and today["reports"]["400"] == 1 and today["distinct_visitors"] == 1
    assert today["models"] == 1 and today["line_items"] > 0 and today["duration_ms_p50"] is not None
    blob = str(s)
    assert "testclient" not in blob and "127.0.0.1" not in blob and "Board Reporting" not in blob
    um.usage.flush()
    assert (tmp_path / "usage.jsonl").exists() and "reports_ok" in (tmp_path / "usage.jsonl").read_text()
