"""Upload the exports, get the report: a small web front on the same engine the CLI runs.

    uvicorn anaplan_estate.web:app --port 8000

One page: upload either a zip of the estate folder (one folder per model holding
'Line Items*.csv' and optionally 'Actions*.csv' and 'Modules*.csv'), or add models one
by one with their files. Nothing is stored, no account exists, file names and model
contents are never logged. Anyone who would rather not upload can clone the repository
and run the same command locally; the page says so.

How a request is handled, in order, so that bad uploads fail in milliseconds and good
ones cost as little as possible:

  1. Rate limit per client address (ESTATE_RATE_PER_HOUR, default 30): 429 before any byte is read.
  2. Files are streamed to a temporary folder in chunks with a running total; the first byte
     over ESTATE_MAX_MB (default 80) ends the request with 413. Nothing is held in memory.
  3. A zip is inspected before extraction: it must contain a 'Line Items*.csv', only .csv
     entries are extracted, paths are sanitised, and the declared expanded size is capped.
  4. Every Line Items file is checked in one read of its first 64 KB: a header row, a sniffed
     delimiter and a 'Formula' column. Missing means 400 with the columns found, before any
     analysis runs.
  5. The analysis runs in its own subprocess, so several users are served in parallel on
     separate cores, the memory of a run is returned to the system when it ends, and a run
     over ESTATE_TIMEOUT_S (default 180) is terminated rather than left running. At most
     ESTATE_WORKERS (default: CPUs, capped at 4) run at once; a request that cannot get a
     worker within ESTATE_QUEUE_WAIT_S (default 20) gets 503 instead of a long hang.
  6. The report is written to a file by the subprocess and streamed back; the temporary
     folder is removed after the response is sent.

The example report is built once per process and cached. Links come from
ESTATE_FEEDBACK_URL, ESTATE_SOURCE_URL, ESTATE_HELP_URL; absent means omitted.
"""
from __future__ import annotations
import asyncio, csv, html, io, json, multiprocessing, os, re, secrets, shutil, tempfile, threading, time, zipfile
from collections import deque
from pathlib import Path
from fastapi import FastAPI, Request
from fastapi.responses import FileResponse, HTMLResponse, PlainTextResponse, RedirectResponse, Response
from starlette.background import BackgroundTask
from . import usage as usage_mod
from .usage import usage

MAX_MB = float(os.environ.get("ESTATE_MAX_MB", "80"))
MAX_MODELS = int(os.environ.get("ESTATE_MAX_MODELS", "12"))
TIMEOUT_S = float(os.environ.get("ESTATE_TIMEOUT_S", "180"))
WORKERS = int(os.environ.get("ESTATE_WORKERS", str(min(4, os.cpu_count() or 1))))
QUEUE_WAIT_S = float(os.environ.get("ESTATE_QUEUE_WAIT_S", "20"))
RATE_PER_HOUR = int(os.environ.get("ESTATE_RATE_PER_HOUR", "30"))
LINKS = {"feedback_url": os.environ.get("ESTATE_FEEDBACK_URL", ""), "source_url": os.environ.get("ESTATE_SOURCE_URL", ""), "help_url": os.environ.get("ESTATE_HELP_URL", "")}
CONTACT_URL = os.environ.get("ESTATE_CONTACT_URL", "")          # a private way to reach the maintainer, for people who do not use GitHub
BRAND_URL = os.environ.get("ESTATE_BRAND_URL", "https://codelessops.com")
EXAMPLE_TARGET = ("CAL03 Opex", "Forecast Opex")               # the line item the example opens on: "what could changing this affect?"
STATIC = Path(__file__).resolve().parent / "static"
def _find_example() -> Path:
    """The fictional example estate: ESTATE_EXAMPLE_DIR, else the checkout the service runs from, else next to the source tree."""
    here = Path(__file__).resolve()
    for c in (Path(os.environ.get("ESTATE_EXAMPLE_DIR", "")), here.parent / "example" / "caldergate-estate", Path.cwd() / "examples" / "caldergate-estate", here.parents[2] / "examples" / "caldergate-estate"):
        if str(c) not in ("", ".") and c.is_dir():
            return c
    return Path(__file__).resolve().parents[2] / "examples" / "caldergate-estate"


EXAMPLE = _find_example()
CHUNK = 1024 * 256

app = FastAPI(title="Anaplan estate review", docs_url=None, redoc_url=None, openapi_url=None)
_slots = asyncio.Semaphore(WORKERS)
_rate: dict[str, deque] = {}
_rate_lock = threading.Lock()
_example_cache: dict[str, str] = {}
_ctx = multiprocessing.get_context("spawn")

PAGE_CSS = """
:root{--bg:#fcfcfc;--ink:#1a1a1a;--muted:#5f6b66;--rule:#e6e8e7;--soft:#eceeed;--accent:#047857;--accent-fg:#fff;--card:#fff;--notice:#fffbeb;--err:#dc2626;
--sans:"Geist Sans",system-ui,-apple-system,"Segoe UI",Arial,sans-serif;--mono:"Geist Mono",Consolas,monospace}
@media (prefers-color-scheme:dark){:root{--bg:#0b0e0d;--ink:#e8ebe9;--muted:#9aa5a0;--rule:#222a27;--soft:#1c2320;--accent:#34d399;--accent-fg:#05140e;--card:#141917;--notice:#2a2416;--err:#f87171}}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--ink);font-family:var(--sans);font-size:15px;line-height:1.5}
.page{max-width:760px;margin:0 auto;padding:40px 24px 60px}h1{font-size:30px;line-height:1.2;margin:0 0 10px;font-weight:600;letter-spacing:-.01em}h2{font-size:17px;margin:32px 0 8px;font-weight:600}
p{max-width:64ch;margin:6px 0}.muted{color:var(--muted)}.fnote{font-size:12.5px;color:var(--muted)}.lead{font-size:16px;color:var(--muted);max-width:60ch}
.card{background:var(--card);border:1px solid var(--rule);border-radius:6px;padding:16px 18px;margin:12px 0}
.notice{background:var(--notice);border-radius:6px;padding:8px 12px;font-size:13.5px;margin:10px 0}
label{display:block;font-size:13px;margin:0 0 4px;color:var(--muted)}input[type=text],input[type=file]{font:inherit;font-size:13.5px;padding:7px 9px;border:1px solid var(--rule);border-radius:6px;background:var(--bg);color:var(--ink);width:100%}
.row.model{border-top:1px solid var(--rule);padding-top:14px;margin-top:14px}.row.model:first-child{border-top:0;padding-top:0;margin-top:0}
.row .name{margin-bottom:12px;max-width:320px}.row .files{display:grid;grid-template-columns:1fr 1fr 1fr;gap:12px;align-items:start}
@media (max-width:640px){.row .files{grid-template-columns:1fr}}
button{font:inherit;font-size:14px;padding:8px 14px;border:1px solid var(--rule);border-radius:6px;background:var(--card);color:var(--ink);cursor:pointer}button.primary{background:var(--accent);color:var(--accent-fg);border-color:var(--accent);font-weight:600}
a{color:var(--accent)}code{font-family:var(--mono);font-size:12.5px;background:var(--soft);padding:1px 4px;border-radius:3px}pre{background:var(--soft);padding:10px;border-radius:6px;overflow-x:auto;font-size:12.5px;font-family:var(--mono)}
footer{margin-top:40px;border-top:1px solid var(--rule);padding-top:10px;font-size:12.5px;color:var(--muted)}
.brand{font-family:var(--mono);font-size:12px;letter-spacing:.14em;text-transform:uppercase;color:var(--muted);margin:0 0 14px}.brand a{color:var(--accent);text-decoration:none;font-weight:500}
.cta{margin:18px 0 8px}.btn{display:inline-block;font:inherit;font-size:14px;padding:8px 14px;border:1px solid var(--rule);border-radius:6px;background:var(--card);color:var(--ink);cursor:pointer;text-decoration:none}
.btn.primary{background:var(--accent);color:var(--accent-fg);border-color:var(--accent);font-weight:600}.cta .btn{font-size:15px;padding:10px 18px;margin-right:8px}
#review{scroll-margin-top:12px}.req{color:var(--accent);font-size:11px;text-transform:uppercase;letter-spacing:.06em;margin-left:4px}.opt{color:var(--muted);font-size:11px;text-transform:uppercase;letter-spacing:.06em;margin-left:4px}
.hint{display:block;font-size:11.5px;color:var(--muted);margin-top:3px}.row.missing input.li{outline:2px solid var(--err);outline-offset:1px}
.err{color:var(--err);font-weight:600}details{margin:10px 0}details summary{cursor:pointer;font-weight:600;font-size:14px}details .card{margin-top:8px}
"""


def _e(s) -> str:
    return html.escape(str(s), quote=True)


def _page(body: str, title: str = "Anaplan estate review") -> str:
    return f"<!doctype html><html lang=en><head><meta charset=utf-8><meta name=viewport content='width=device-width,initial-scale=1'><title>{_e(title)}</title><style>{PAGE_CSS}</style></head><body><div class=page>{body}</div></body></html>"


def _footer() -> str:
    bits = [f'Free and open source. Maintained by <a href="{_e(BRAND_URL)}">CodelessOps</a>; contributions welcome.']
    if LINKS["source_url"]:
        bits.append(f'<a href="{_e(LINKS["source_url"])}">Source</a>.')
    if LINKS["feedback_url"]:
        bits.append(f'Something missing or not quite right? <a href="{_e(LINKS["feedback_url"])}">Suggest an improvement</a> (public, needs a GitHub account)' + (f' or <a href="{_e(CONTACT_URL)}">get in touch privately</a>.' if CONTACT_URL else "."))
    elif CONTACT_URL:
        bits.append(f'Something missing or not quite right? <a href="{_e(CONTACT_URL)}">Get in touch</a>.')
    return "<footer><p>" + " ".join(bits) + "</p></footer>"


def _local_instructions() -> str:
    src = LINKS["source_url"]
    return f"""<section><h2 id=local>Rather not upload? Run this same page on your own machine</h2>
<p>The same engine, the same page, nothing leaves your computer. You need Python 3.10 or newer.</p>
<pre>pip install "https://github.com/klameer/anaplan-grammar/archive/refs/heads/master.zip"
pip install "anaplan-estate[web] @ https://github.com/klameer/anaplan-estate/archive/refs/heads/master.zip"
anaplan-estate-web</pre>
<p class=fnote>Then open <a href="http://localhost:8000">localhost:8000</a> and use it exactly as here. For a command-line run instead: <code>anaplan-estate my-estate-folder --html estate.html</code>, with one folder per model inside <code>my-estate-folder</code>.{(f' Source: <a href="{_e(src)}">{_e(src)}</a>.' if src else '')}</p></section>"""


@app.get("/", response_class=HTMLResponse)
def index(request: Request):
    usage.visit(_client(request))
    row = """<div class="row model"><div class=name><label>Model name</label><input type=text name=model_name placeholder="e.g. FP&amp;A"></div>
<div class=files>
<div><label>Line Items export <span class=req>required</span></label><input type=file name=line_items accept=".csv,text/csv" class=li><span class=hint>the one file needed</span></div>
<div><label>Actions export <span class=opt>optional</span></label><input type=file name=actions accept=".csv,text/csv"><span class=hint>adds imports, exports and processes</span></div>
<div><label>Modules export <span class=opt>optional</span></label><input type=file name=modules accept=".csv,text/csv"><span class=hint>adds module notes</span></div>
</div></div>"""
    body = f"""<p class=brand><a href="{_e(BRAND_URL)}">CodelessOps</a> &middot; Anaplan estate review</p>
<h1>Do a quick review on your Anaplan estate</h1>
<p class=lead>Upload your models' line items, actions and modules and get actionable steps on what you can do to improve. Simple and no fuss. No account, nothing installed, nothing kept.</p>
<p class=cta><a class="btn primary" href="/example#plan">Explore an example</a> <a class="btn" href="#review">Review my estate</a></p>
<p class=fnote>The example is a fictional four-model estate. Free and open source; <a href="#local">runs on your own machine</a> if you would rather nothing left it.</p>
<section id=review><h2>Review my estate</h2>
<p>Export each model's <strong>Line Items</strong> grid (Model Settings &gt; Modules &gt; Line Items tab &gt; Export, every column). Actions and Modules exports are optional.</p>
<form method="post" action="/report" enctype="multipart/form-data" class="card" id=f novalidate>
<div id=rows>{row}</div>
<p><button type=button class=btn id=add>Add another model</button></p>
<details id=zipalt><summary>Or upload one zip of the whole estate</summary><p class=fnote>One folder per model inside the zip, each holding that model's <code>Line Items*.csv</code> and optionally <code>Actions*.csv</code> and <code>Modules*.csv</code>. Folder names become model names.</p><input type=file name=estate_zip accept=".zip,application/zip" id=zip></details>
<label>Report title (optional)</label><input type=text name=title placeholder="e.g. Acme Anaplan estate" maxlength=120>
<p class=err id=err role=alert hidden></p>
<p><button type=submit class="btn primary">Build the report</button> <span class=fnote id=busy hidden>Building the report: a few seconds for a small model, up to a minute for a large estate.</span></p>
<p class=fnote>Files are held in a temporary folder for the seconds the analysis takes and deleted as soon as the report is sent. Nothing is stored; file names, model names and formulas are never logged. Limits: {MAX_MB:.0f} MB, {MAX_MODELS} models, about {TIMEOUT_S:.0f} seconds.</p>
</form></section>
<details id=local><summary>Rather not upload? Run it on your own machine</summary>
<div class=card><p>The same engine, the same page, nothing leaves your computer. You need Python 3.10 or newer.</p>
<pre>pip install "https://github.com/klameer/anaplan-grammar/archive/refs/heads/master.zip"
pip install "anaplan-estate[web] @ https://github.com/klameer/anaplan-estate/archive/refs/heads/master.zip"
anaplan-estate-web</pre>
<p class=fnote>Then open <a href="http://localhost:8000">localhost:8000</a> and use it exactly as here. Command line instead: <code>anaplan-estate my-estate-folder --html estate.html</code>, one folder per model inside.</p></div></details>
<p class=fnote>Rules and ranking were developed on a small number of estates: a starting point, not a verdict.</p>
{_footer()}
<script>
(function(){{
 var rows=document.getElementById('rows'),tpl=rows.firstElementChild.cloneNode(true);
 document.getElementById('add').addEventListener('click',function(){{var r=tpl.cloneNode(true);r.querySelectorAll('input').forEach(function(i){{i.value=''}});rows.appendChild(r);r.querySelector('input[type=text]').focus()}});
 var f=document.getElementById('f'),err=document.getElementById('err');
 f.addEventListener('submit',function(e){{
   var zip=document.getElementById('zip'),hasZip=zip&&zip.files&&zip.files.length>0;
   var lis=Array.prototype.slice.call(document.querySelectorAll('input.li')),hasLi=lis.some(function(i){{return i.files&&i.files.length>0}});
   document.querySelectorAll('.row.model').forEach(function(r){{r.classList.remove('missing')}});
   if(!hasZip&&!hasLi){{e.preventDefault();err.hidden=false;err.textContent='Add at least one Line Items export (or a zip of the estate) before building the report.';var r=document.querySelector('.row.model');r.classList.add('missing');r.querySelector('input.li').focus();return}}
   err.hidden=true;document.getElementById('busy').hidden=false;f.querySelector('button[type=submit]').disabled=true;
 }});
 var loc=document.getElementById('local');if(location.hash==='#local'&&loc){{loc.open=true}}
 document.querySelectorAll('a[href="#local"]').forEach(function(a){{a.addEventListener('click',function(){{if(loc)loc.open=true}})}});
}})();
</script>"""
    return HTMLResponse(_page(body))


@app.get("/health", response_class=PlainTextResponse)
def health():
    return "ok"


@app.head("/health", response_class=PlainTextResponse)
def health_head():
    return ""


def _error(status: int, msg: str, retry_after: int | None = None) -> HTMLResponse:
    body = f"<h1>Could not build the report</h1><div class=notice>{_e(msg)}</div><p><a href='/'>Back</a></p>{_local_instructions()}{_footer()}"
    headers = {"Retry-After": str(retry_after)} if retry_after else None
    return HTMLResponse(_page(body, "Could not build the report"), status_code=status, headers=headers)


# ---------------------------------------------------------------- guards

def _client(request: Request) -> str:
    fwd = request.headers.get("x-forwarded-for", "")
    return (fwd.split(",")[0].strip() if fwd else (request.client.host if request.client else "?"))


def _rate_ok(key: str) -> bool:
    now = time.time()
    with _rate_lock:
        q = _rate.setdefault(key, deque())
        while q and q[0] < now - 3600:
            q.popleft()
        if len(q) >= RATE_PER_HOUR:
            return False
        q.append(now)
        if len(_rate) > 10_000:                       # never let the table grow without bound
            for k in [k for k, v in _rate.items() if not v or v[-1] < now - 3600][:5000]:
                _rate.pop(k, None)
        return True


class TooLarge(Exception):
    pass


class Budget:
    def __init__(self, limit: int):
        self.limit = limit; self.used = 0

    def add(self, n: int):
        self.used += n
        if self.used > self.limit:
            raise TooLarge()


async def _stream_to(upload, dest: Path, budget: Budget) -> None:
    with open(dest, "wb") as out:
        while True:
            chunk = await upload.read(CHUNK)
            if not chunk:
                break
            budget.add(len(chunk))
            out.write(chunk)


_SAFE = re.compile(r"[^A-Za-z0-9 _.&()+-]")


def _safe_name(s: str, default: str) -> str:
    s = _SAFE.sub("", (s or "").strip())[:80].strip(" .")
    return s or default


def _extract_zip(path: Path, root: Path, budget: Budget) -> None:
    """Inspect first, extract second: only .csv entries, sanitised paths, declared sizes counted against the budget."""
    with zipfile.ZipFile(path) as z:
        infos = [i for i in z.infolist() if not i.is_dir()]
        names = [i.filename.replace("\\", "/") for i in infos]
        if not any(re.search(r"(^|/)Line Items[^/]*\.csv$", n, re.I) for n in names):
            raise ValueError("The zip holds no 'Line Items*.csv'. Put one folder per model in it, each with that model's Line Items export.")
        for info, name in zip(infos, names):
            parts = [p for p in name.split("/") if p not in ("", ".", "..")]
            if not parts or not parts[-1].lower().endswith(".csv"):
                continue
            budget.add(info.file_size)
            dest = root.joinpath(*parts)
            dest.parent.mkdir(parents=True, exist_ok=True)
            with z.open(info) as src, open(dest, "wb") as out:
                shutil.copyfileobj(src, out, CHUNK)


def _quick_check(path: Path) -> str | None:
    """One read of the first 64 KB: header row, sniffed delimiter, a Formula column. Returns the problem, or None."""
    from .model import DELIMITERS
    raw = path.read_bytes()[:65536]
    if not raw.strip():
        return f"'{path.name}' is empty."
    head = raw.decode("utf-8", "replace")
    for enc in ("utf-8-sig", "cp1252"):
        try:
            head = raw.decode(enc); break
        except UnicodeDecodeError:
            continue
    lines = head.splitlines()
    first = lines[0] if lines else ""
    try:
        delim = csv.Sniffer().sniff(head[:20000], delimiters=DELIMITERS).delimiter
    except csv.Error:
        delim = max(DELIMITERS, key=lambda d: first.count(d)) if first else ","
    cols = next(csv.reader(io.StringIO(first), delimiter=delim), [])
    if "Formula" not in cols:
        shown = ", ".join((c or "(blank)") for c in cols[:10]) or "none"
        return (f"'{path.name}' has no 'Formula' column (columns found: {shown}). It does not look like the Line Items grid export; "
                "export from Model Settings > Modules > Line Items with every column, with English headers.")
    if len(lines) < 2:
        return f"'{path.name}' has a header row but no line items."
    return None


# ---------------------------------------------------------------- the analysis, in its own process

def _worker(root: str, title: str, links: dict, out_path: str, err_path: str, target=None) -> None:
    try:
        from . import fleet, report, report_html
        er = fleet.run(root)
        rep = report.build(er, **links)
        if title:
            rep["title"] = title
        Path(out_path).write_text(report_html.render(rep, csv_text=report.register_csv(rep)), encoding="utf-8")
        meta = {"models": len(er.models), "line_items": rep["scope"]["line_items"]}
        if target:
            meta["target_id"] = next((n[0] for n in rep["graph"]["nodes"] if (n[2], n[3]) == tuple(target)), None)
        Path(out_path).with_name("meta.json").write_text(json.dumps(meta), encoding="utf-8")
    except BaseException as e:            # SystemExit from the loader included
        Path(err_path).write_text(f"{type(e).__name__}: {e}", encoding="utf-8")


def _run_in_subprocess(root: Path, title: str, out_path: Path, err_path: Path, target=None) -> str | None:
    """Blocking; called from a thread. Returns an error message or None."""
    p = _ctx.Process(target=_worker, args=(str(root), title, LINKS, str(out_path), str(err_path), target), daemon=True)
    p.start(); p.join(TIMEOUT_S)
    if p.is_alive():
        p.terminate(); p.join(5)
        return f"The analysis took longer than {TIMEOUT_S:.0f} seconds and was stopped. Run the tool locally for this estate."
    if err_path.exists():
        msg = err_path.read_text(encoding="utf-8")
        return msg.split(": ", 1)[1] if msg.startswith(("InputError", "SystemExit")) else "The analysis failed on these files. " + msg[:300]
    if not out_path.exists():
        return "The analysis ended without producing a report."
    return None


async def _analyse(root: Path, title: str, tmp: Path):
    out_path, err_path = tmp / "estate.html", tmp / "error.txt"
    try:
        await asyncio.wait_for(_slots.acquire(), timeout=QUEUE_WAIT_S)
    except asyncio.TimeoutError:
        return _error(503, "The service is busy right now. Try again in a minute, or run the tool locally.", retry_after=60)
    try:
        err = await asyncio.to_thread(_run_in_subprocess, root, title, out_path, err_path)
    finally:
        _slots.release()
    if err:
        return _error(504 if err.startswith("The analysis took") else 400, err)
    resp = FileResponse(out_path, media_type="text/html; charset=utf-8", headers={"Content-Disposition": 'inline; filename="estate.html"', "Cache-Control": "no-store"},
                        background=BackgroundTask(shutil.rmtree, tmp, ignore_errors=True))
    try:
        resp.usage_meta = json.loads((tmp / "meta.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        resp.usage_meta = {}
    return resp


def _files(form, key) -> list:
    """Every part under `key` as an UploadFile or None: a browser sends an empty part for an untouched file input."""
    return [v if (hasattr(v, "filename") and v.filename) else None for v in form.getlist(key)]


@app.post("/report")
async def build_report(request: Request):
    """Counts the request for the usage summary (outcome, sizes, duration; never content), then hands over."""
    t = time.time(); client = _client(request)
    resp = await _build_report(request, client)
    meta = getattr(resp, "usage_meta", {}) or {}
    cl = request.headers.get("content-length", "")
    usage.report(client, "ok" if resp.status_code == 200 else str(resp.status_code), models=meta.get("models", 0), line_items=meta.get("line_items", 0),
                 upload_bytes=int(cl) if cl.isdigit() else 0, duration_ms=int((time.time() - t) * 1000))
    return resp


@app.get("/stats")
def stats(request: Request):
    """Usage summary for the operator: today in memory plus the daily history file. Off unless ESTATE_STATS_TOKEN is set."""
    token = usage_mod.STATS_TOKEN
    given = request.query_params.get("token") or request.headers.get("x-stats-token", "")
    if not token or not secrets.compare_digest(given, token):
        return PlainTextResponse("not found", status_code=404)
    return {"today": usage.summary(), "history": usage.history(), "note": "no personal data: outcomes, counts, size buckets, durations; visitors counted with a daily random key that is never stored"}


@app.router.on_shutdown.append
def _flush_usage():
    usage.flush()


async def _build_report(request: Request, client: str):
    if not _rate_ok(client):
        return _error(429, f"More than {RATE_PER_HOUR} reports from this address in an hour. Try again later, or run the tool locally.", retry_after=600)
    cl = request.headers.get("content-length")
    if cl and cl.isdigit() and int(cl) > MAX_MB * 1024 * 1024 * 1.05:
        return _error(413, f"The upload is larger than {MAX_MB:.0f} MB. Run the tool locally for very large estates.")
    form = await request.form()
    title = _safe_name(str(form.get("title") or ""), "")
    zips = _files(form, "estate_zip"); estate_zip = zips[0] if zips else None
    model_name = [str(v) for v in form.getlist("model_name")]
    line_items, actions, modules = _files(form, "line_items"), _files(form, "actions"), _files(form, "modules")
    tmp = Path(tempfile.mkdtemp(prefix="estate-"))
    budget = Budget(int(MAX_MB * 1024 * 1024))
    ok = False
    try:
        root = tmp / "estate"; root.mkdir()
        if estate_zip is not None:
            zpath = tmp / "upload.zip"
            await _stream_to(estate_zip, zpath, budget)
            try:
                _extract_zip(zpath, root, budget)
            except zipfile.BadZipFile:
                return _error(400, "That file is not a zip archive.")
            except ValueError as e:
                return _error(400, str(e))
            finally:
                zpath.unlink(missing_ok=True)
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
                if up is not None:
                    await _stream_to(up, d / fname, budget)
        found = list(root.rglob("Line Items*.csv"))
        if not found:
            return _error(400, "No 'Line Items*.csv' was found. Upload a zip with one folder per model, or add a model with its Line Items export.")
        if len({f.parent for f in found}) > MAX_MODELS:
            return _error(400, f"More than {MAX_MODELS} models in one request; split the estate or run locally.")
        for f in found:                                   # fail before any analysis starts
            problem = _quick_check(f)
            if problem:
                return _error(400, problem)
        resp = await _analyse(root, title, tmp)
        ok = isinstance(resp, FileResponse)              # the file response removes tmp after sending
        return resp
    except TooLarge:
        return _error(413, f"The upload is larger than {MAX_MB:.0f} MB. Run the tool locally for very large estates.")
    finally:
        if not ok:
            shutil.rmtree(tmp, ignore_errors=True)


async def _ensure_example():
    if "html" in _example_cache:
        return None
    if not EXAMPLE.is_dir():
        return "The example estate is not installed on this server."
    tmp = Path(tempfile.mkdtemp(prefix="estate-ex-"))
    try:
        out_path, err_path = tmp / "estate.html", tmp / "error.txt"
        err = await asyncio.to_thread(_run_in_subprocess, EXAMPLE, "Caldergate Distribution Group: Anaplan estate (fictional example)", out_path, err_path, EXAMPLE_TARGET)
        if err:
            return err
        _example_cache["html"] = out_path.read_text(encoding="utf-8")
        try:
            _example_cache["target_id"] = json.loads((tmp / "meta.json").read_text(encoding="utf-8")).get("target_id")
        except (OSError, ValueError):
            _example_cache["target_id"] = None
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    return None


@app.get("/example", response_class=HTMLResponse)
async def example():
    err = await _ensure_example()
    if err:
        return _error(500 if "not installed" not in err else 404, err)
    return HTMLResponse(_example_cache["html"], headers={"Cache-Control": "public, max-age=3600"})


@app.get("/example/change-impact")
async def example_change_impact():
    """The example opened on one concrete question: what could changing Forecast Opex affect?"""
    err = await _ensure_example()
    if err:
        return _error(500 if "not installed" not in err else 404, err)
    tid = _example_cache.get("target_id")
    return RedirectResponse(f"/example#impact={tid}" if tid is not None else "/example#impact", status_code=302)


@app.get("/static/example-impact.png")
def example_screenshot():
    f = STATIC / "example-impact.png"
    if not f.exists():
        return Response(status_code=404)
    return FileResponse(f, media_type="image/png", headers={"Cache-Control": "public, max-age=86400"})


def main():
    import uvicorn
    uvicorn.run("anaplan_estate.web:app", host="0.0.0.0", port=int(os.environ.get("PORT", "8000")))
