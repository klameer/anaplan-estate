"""The upload front: a zip or per-model files in, the same report out, temp files gone, errors as plain pages."""
import sys, pathlib, io, zipfile, os
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


def test_index_explains_privacy_and_local_option():
    r = client.get("/")
    assert r.status_code == 200 and "What happens to your files" in r.text and "run it locally" in r.text.lower() and 'action="/report"' in r.text
    assert client.get("/health").text == "ok"


def test_zip_upload_returns_the_report_and_cleans_up(tmp_path):
    before = set(p.name for p in pathlib.Path(web.tempfile.gettempdir()).glob("estate-*"))
    data = _zip([EX / "1 Caldergate Data Hub", EX / "2 Caldergate FP&A"])
    r = client.post("/report", data={"title": "Test estate"}, files={"estate_zip": ("estate.zip", data, "application/zip")})
    assert r.status_code == 200 and "<title>Test estate</title>" in r.text and 'id="plan"' in r.text and "Caldergate FP&amp;A" in r.text
    assert "inline" in r.headers["content-disposition"]
    after = set(p.name for p in pathlib.Path(web.tempfile.gettempdir()).glob("estate-*"))
    assert after <= before


def test_per_model_upload():
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
    bad = "Line Items,Format,Applies To\nA,NUMBER,L\n".encode()
    r = client.post("/report", data={"model_name": ["M"]}, files=[("line_items", ("Line Items.csv", bad, "text/csv"))])
    assert r.status_code == 400 and "Formula" in r.text


def test_size_limit(monkeypatch):
    monkeypatch.setattr(web, "MAX_MB", 0.0001)
    data = _zip([EX / "1 Caldergate Data Hub"])
    r = client.post("/report", files={"estate_zip": ("estate.zip", data, "application/zip")})
    assert r.status_code == 413


def test_example_route():
    r = client.get("/example")
    assert r.status_code == 200 and "fictional example" in r.text
