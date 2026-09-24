"""Upload the exports, get the report: a small web front on the same engine the CLI runs.

    uvicorn anaplan_estate.web:app --port 8000

One page: upload either a zip of the estate folder (one folder per model holding
'Line Items*.csv' and optionally 'Actions*.csv' and 'Modules*.csv'), or add models one
by one with their files. The server writes the files to a temporary folder, runs the
analysis, returns the self-contained HTML report and deletes the folder before the
response leaves. Nothing is stored, no account exists, file names and model contents
are never logged. Anyone who would rather not upload can clone the repository and run
the same command locally; the page says so.

Limits (environment variables): ESTATE_MAX_MB (default 80), ESTATE_MAX_MODELS (default
12), ESTATE_TIMEOUT_S (default 180). Links shown in the report and the page come from
ESTATE_FEEDBACK_URL, ESTATE_SOURCE_URL, ESTATE_HELP_URL; absent means omitted.
"""
from __future__ import annotations
import html, io, os, re, shutil, tempfile, zipfile, concurrent.futures
from pathlib import Path
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse, PlainTextResponse
from . import fleet, report, report_html
from .model import InputError

MAX_MB = float(os.environ.get("ESTATE_MAX_MB", "80"))
MAX_MODELS = int(os.environ.get("ESTATE_MAX_MODELS", "12"))
TIMEOUT_S = float(os.environ.get("ESTATE_TIMEOUT_S", "180"))
LINKS = {"feedback_url": os.environ.get("ESTATE_FEEDBACK_URL", ""), "source_url": os.environ.get("ESTATE_SOURCE_URL", ""), "help_url": os.environ.get("ESTATE_HELP_URL", "")}
EXAMPLE = Path(__file__).resolve().parents[2] / "examples" / "caldergate-estate"
_POOL = concurrent.futures.ThreadPoolExecutor(max_workers=2)

app = FastAPI(title="Anaplan estate review", docs_url=None, redoc_url=None)

PAGE_CSS = """
:root{--bg:#F7F8F6;--ink:#1B2430;--muted:#5C6773;--rule:#D9DED9;--soft:#EEF1EE;--accent:#0E5E6F;--card:#fff;--notice:#FFF7E6}
@media (prefers-color-scheme:dark){:root{--bg:#0F1416;--ink:#E6EBE8;--muted:#9AA6A0;--rule:#2E393C;--soft:#1B2427;--accent:#5FB3C1;--card:#161D20;--notice:#2A2416}}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--ink);font-family:"IBM Plex Sans","Helvetica Neue",Arial,sans-serif;font-size:15px;line-height:1.5}
.page{max-width:860px;margin:0 auto;padding:32px 24px 60px}h1{font-size:28px;margin:0 0 6px;font-weight:600}h2{font-size:18px;margin:26px 0 8px}
p{max-width:72ch;margin:6px 0}.muted{color:var(--muted)}.fnote{font-size:12.5px;color:var(--muted)}
.card{background:var(--card);border:1px solid var(--rule);border-radius:8px;padding:14px 16px;margin:12px 0}
.notice{background:var(--notice);border-radius:6px;padding:8px 12px;font-size:13.5px;margin:10px 0}
label{display:block;font-size:13px;margin:8px 0 2px;color:var(--muted)}input[type=text],input[type=file]{font:inherit;font-size:13.5px;padding:6px 8px;border:1px solid var(--rule);border-radius:6px;background:var(--bg);color:var(--ink);width:100%}
.row{display:grid;grid-template-columns:1fr 1fr 1fr 1fr;gap:8px;align-items:end;border-top:1px solid var(--rule);padding-top:8px;margin-top:8px}
@media (max-width:640px){.row{grid-template-columns:1fr}}
button{font:inherit;font-size:14px;padding:8px 14px;border:1px solid var(--rule);border-radius:6px;background:var(--card);color:var(--ink);cursor:pointer}button.primary{background:var(--accent);color:#fff;border-color:var(--accent)}
a{color:var(--accent)}code{font-family:Consolas,monospace;font-size:12.5px;background:var(--soft);padding:1px 4px;border-radius:3px}pre{background:var(--soft);padding:10px;border-radius:6px;overflow-x:auto;font-size:12.5px}
footer{margin-top:36px;border-top:1px solid var(--rule);padding-top:10px;font-size:12.5px;color:var(--muted)}
"""


def _e(s) -> str:
    return html.escape(str(s), quote=True)


def _page(body: str, title: str = "Anaplan estate review") -> str:
    return f"<!doctype html><html lang=en><head><meta charset=utf-8><meta name=viewport content='width=device-width,initial-scale=1'><title>{_e(title)}</title><style>{PAGE_CSS}</style></head><body><div class=page>{body}</div></body></html>"


def _footer() -> str:
    bits = ["Free and open source. Maintained by CodelessOps; contributions welcome."]
    if LINKS["source_url"]:
        bits.append(f'<a href="{_e(LINKS["source_url"])}">Source</a>.')
    if LINKS["feedback_url"]:
        bits.append(f'Something missing or not quite right? <a href="{_e(LINKS["feedback_url"])}">Suggest an improvement</a>.')
    return "<footer><p>" + " ".join(bits) + "</p></footer>"


def _local_instructions() -> str:
    src = LINKS["source_url"] or "the repository"
    return f"""<h2 id=local>Rather not upload? Run it on your own machine</h2>
<p>The same engine, the same report, nothing leaves your computer. You need Python 3.10 or newer.</p>
<pre>pip install "https://github.com/klameer/anaplan-grammar/archive/refs/heads/main.zip"
pip install "https://github.com/klameer/anaplan-estate/archive/refs/heads/main.zip"
anaplan-estate my-estate-folder --html estate.html</pre>
<p class=fnote>Put one folder per model inside <code>my-estate-folder</code>, each holding its <code>Line Items.csv</code> and, if you have them, <code>Actions.csv</code> and <code>Modules.csv</code>. Then open <code>estate.html</code>. Source: {(_e(src) if not LINKS["source_url"] else f'<a href="{_e(src)}">{_e(src)}</a>')}.</p>"""


@app.get("/", response_class=HTMLResponse)
def index():
    rows = "".join(f"""<div class=row><div><label>Model name</label><input type=text name=model_name placeholder="e.g. FP&amp;A"></div>
<div><label>Line Items export (required)</label><input type=file name=line_items accept=".csv,text/csv"></div>
<div><label>Actions export (optional)</label><input type=file name=actions accept=".csv,text/csv"></div>
<div><label>Modules export (optional)</label><input type=file name=modules accept=".csv,text/csv"></div></div>""" for _ in range(3))
    body = f"""<h1>Anaplan estate review</h1><p class=muted>Find what to improve in Anaplan. See what a change could affect.</p>
<p>Upload the grid exports of one or more models and get a self-contained report: an action plan in plain language, a change-impact explorer, and every finding with its evidence. Nothing to install, no account.</p>
<div class=notice><strong>What happens to your files.</strong> They are written to a temporary folder on the server for the few seconds the analysis takes, then deleted before the report is sent. Nothing is stored, and file names, model names and formulas are never logged. If that is still more than you want to share, <a href="#local">run it locally instead</a>.</div>
<h2>How to export</h2><p>In each model, as a workspace administrator: <strong>Model Settings &gt; Modules &gt; Line Items tab &gt; Export</strong> (every column; this is the required file), and optionally <strong>Model Settings &gt; Actions &gt; Export</strong> and the <strong>Modules</strong> grid export. English column headers; comma, semicolon or tab delimited.</p>
<form method="post" action="/report" enctype="multipart/form-data" class="card">
<label>Report title (the estate name)</label><input type=text name=title placeholder="e.g. Acme Anaplan estate" maxlength=120>
<h2 style="margin-top:14px">Option A: one zip of the whole estate</h2><p class=fnote>One folder per model inside the zip, each holding that model's <code>Line Items*.csv</code> and optionally <code>Actions*.csv</code> and <code>Modules*.csv</code>. Folder names become model names.</p>
<input type=file name=estate_zip accept=".zip,application/zip">
<h2 style="margin-top:18px">Option B: add models one by one</h2><div id=rows>{rows}</div>
<p><button type=button onclick="var r=document.querySelector('#rows .row').cloneNode(true);r.querySelectorAll('input').forEach(function(i){{i.value=''}});document.getElementById('rows').appendChild(r)">Add another model</button></p>
<p class=fnote>Limits: {MAX_MB:.0f} MB in total, {MAX_MODELS} models, about {TIMEOUT_S:.0f} seconds of analysis. Very large estates: run locally.</p>
<p><button type=submit class=primary>Build the report</button> <a href="/example" style="margin-left:12px">or see the report for a fictional example estate</a></p>
</form>
{_local_instructions()}
<p class=fnote>The findings and the change-impact explorer apply to any model the exports describe. The action cards match a small set of known patterns and will be few or absent on an estate whose problems lie elsewhere; the report says so. Rules and ranking were developed on a small number of estates and are a hypothesis to test, not a verdict.</p>
{_footer()}"""
    return HTMLResponse(_page(body))


@app.get("/health", response_class=PlainTextResponse)
def health():
    return "ok"


def _error(status: int, msg: str) -> HTMLResponse:
    body = f"<h1>Could not build the report</h1><div class=notice>{_e(msg)}</div><p><a href='/'>Back</a></p>{_local_instructions()}{_footer()}"
    return HTMLResponse(_page(body, "Could not build the report"), status_code=status)


_SAFE = re.compile(r"[^A-Za-z0-9 _.&()+-]")


def _safe_name(s: str, default: str) -> str:
    s = _SAFE.sub("", (s or "").strip())[:80].strip(" .")
    return s or default


def _extract_zip(data: bytes, root: Path) -> None:
    with zipfile.ZipFile(io.BytesIO(data)) as z:
        total = 0
        for info in z.infolist():
            if info.is_dir():
                continue
            total += info.file_size
            if total > MAX_MB * 1024 * 1024:
                raise HTTPException(413, f"The zip expands to more than {MAX_MB:.0f} MB.")
            name = info.filename.replace("\\", "/")
            parts = [p for p in name.split("/") if p not in ("", ".", "..")]
            if not parts or not parts[-1].lower().endswith(".csv"):
                continue
            dest = root.joinpath(*parts)
            dest.parent.mkdir(parents=True, exist_ok=True)
            with z.open(info) as src, open(dest, "wb") as out:
                shutil.copyfileobj(src, out)


def _build(root: Path, title: str) -> str:
    er = fleet.run(root)
    rep = report.build(er, **LINKS)
    if title:
        rep["title"] = title
    return report_html.render(rep, csv_text=report.register_csv(rep))


def _run_with_timeout(root: Path, title: str) -> str:
    fut = _POOL.submit(_build, root, title)
    return fut.result(timeout=TIMEOUT_S)


def _files(form, key) -> list:
    """Every part under `key` as an UploadFile or None: a browser sends an empty part for an untouched file input."""
    return [v if (hasattr(v, "filename") and v.filename) else None for v in form.getlist(key)]


@app.post("/report", response_class=HTMLResponse)
async def build_report(request: Request):
    form = await request.form()
    title = str(form.get("title") or "")
    zips = _files(form, "estate_zip"); estate_zip = zips[0] if zips else None
    model_name = [str(v) for v in form.getlist("model_name")]
    line_items, actions, modules = _files(form, "line_items"), _files(form, "actions"), _files(form, "modules")
    tmp = Path(tempfile.mkdtemp(prefix="estate-"))
    try:
        total = 0
        root = tmp / "estate"; root.mkdir()
        if estate_zip is not None:
            data = await estate_zip.read(); total += len(data)
            if total > MAX_MB * 1024 * 1024:
                return _error(413, f"The upload is larger than {MAX_MB:.0f} MB. Run the tool locally for very large estates.")
            try:
                _extract_zip(data, root)
            except zipfile.BadZipFile:
                return _error(400, "That file is not a zip archive.")
            except HTTPException as e:
                return _error(e.status_code, e.detail)
        n = 0
        for i, li in enumerate(line_items):
            if li is None:
                continue
            n += 1
            if n > MAX_MODELS:
                return _error(400, f"More than {MAX_MODELS} models in one request; split the estate or run locally.")
            name = _safe_name(model_name[i] if i < len(model_name) else "", f"Model {n}")
            d = root / name; d.mkdir(parents=True, exist_ok=True)
            for up, fname in ((li, "Line Items.csv"), (actions[i] if i < len(actions) else None, "Actions.csv"), (modules[i] if i < len(modules) else None, "Modules.csv")):
                if up is None:
                    continue
                data = await up.read(); total += len(data)
                if total > MAX_MB * 1024 * 1024:
                    return _error(413, f"The upload is larger than {MAX_MB:.0f} MB. Run the tool locally for very large estates.")
                (d / fname).write_bytes(data)
        if not any(root.rglob("Line Items*.csv")):
            return _error(400, "No 'Line Items*.csv' was found. Upload a zip with one folder per model, or add a model with its Line Items export.")
        try:
            page = _run_with_timeout(root, _safe_name(title, ""))
        except concurrent.futures.TimeoutError:
            return _error(504, f"The analysis took longer than {TIMEOUT_S:.0f} seconds. Run the tool locally for this estate.")
        except InputError as e:
            return _error(400, str(e))
        except SystemExit as e:
            return _error(400, str(e))
        return HTMLResponse(page, headers={"Content-Disposition": 'inline; filename="estate.html"', "Cache-Control": "no-store"})
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


@app.get("/example", response_class=HTMLResponse)
def example():
    if not EXAMPLE.is_dir():
        return _error(404, "The example estate is not installed on this server.")
    page = _run_with_timeout(EXAMPLE, "Caldergate Distribution Group: Anaplan estate (fictional example)")
    return HTMLResponse(page, headers={"Cache-Control": "no-store"})


def main():
    import uvicorn
    uvicorn.run("anaplan_estate.web:app", host="0.0.0.0", port=int(os.environ.get("PORT", "8000")))
