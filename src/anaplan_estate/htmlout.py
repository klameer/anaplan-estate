"""Render the estate Markdown as one self-contained HTML page.

A small converter for the Markdown this package emits (headings,
paragraphs, bullet and numbered lists, tables, bold, inline code, fenced
mermaid), so the page is the tool's output and not a copy of it.

Theming: a neutral built-in stylesheet, or pass `css` to replace it
(a brand kit's tokens, embedded fonts, whatever). `logo_svg` and `brand`
put a mark and a kicker line on the cover. Flowcharts are drawn as inline
SVG (offline, deterministic); `mermaid=True` loads the mermaid script
instead for charts the SVG drawer does not cover. Print stylesheet included,
so a browser's print-to-PDF gives the PDF.
"""
from __future__ import annotations
import html, re

CSS = """
:root{--bg:#F7F8F6;--ink:#1B2430;--muted:#5C6773;--rule:#D9DED9;--soft:#EEF1EE;--accent:#0E5E6F;--crit:#A6301C;--major:#B7791F;
--sans:"IBM Plex Sans","Helvetica Neue",Arial,sans-serif;--mono:"IBM Plex Mono",Consolas,"Courier New",monospace}
@media (prefers-color-scheme:dark){:root:not([data-theme="light"]){--bg:#141A1C;--ink:#E6EBE8;--muted:#9AA6A0;--rule:#2E393C;--soft:#222C2F;--accent:#5FB3C1;--crit:#E07A63;--major:#D9A441}}
*{box-sizing:border-box}body{background:var(--bg);color:var(--ink);font-family:var(--sans);font-size:15px;line-height:1.55;margin:0}
.page{max-width:900px;margin:0 auto;padding:44px 28px 72px}
.cover{display:flex;align-items:center;gap:14px;margin-bottom:28px;padding-bottom:18px;border-bottom:1px solid var(--rule)}
.cover svg,.cover img{height:36px;width:36px;flex:none}
.kicker{font-family:var(--mono);font-size:11px;letter-spacing:.18em;text-transform:uppercase;color:var(--muted)}
h1{font-weight:600;font-size:30px;line-height:1.15;margin:32px 0 6px;letter-spacing:-.01em}
h1:first-of-type{margin-top:0}
h2{font-weight:600;font-size:19px;margin:36px 0 10px;letter-spacing:-.01em}
h3{font-size:15px;font-weight:600;margin:22px 0 6px}
p{max-width:76ch;margin:8px 0}
.lead{color:var(--muted);font-size:13.5px}
table{border-collapse:collapse;width:100%;font-size:13px;margin:10px 0}
th{text-align:left;font-family:var(--mono);font-size:11px;letter-spacing:.12em;text-transform:uppercase;color:var(--muted);font-weight:500;padding:8px 10px 8px 0;border-bottom:1px solid var(--rule)}
td{padding:7px 10px 7px 0;border-bottom:1px solid var(--rule);vertical-align:top}
td:last-child,th:last-child{padding-right:0}
td.num{font-family:var(--mono);font-variant-numeric:tabular-nums;text-align:right;white-space:nowrap}
th.num{text-align:right}
.wrap{overflow-x:auto}
code{font-family:var(--mono);font-size:12px;background:var(--soft);padding:1px 4px;border-radius:3px}
ul,ol{max-width:76ch;padding-left:22px}li{margin:4px 0}
hr{border:0;border-top:1px solid var(--rule);margin:36px 0}
pre{background:var(--soft);padding:12px;border-radius:6px;overflow-x:auto;font-family:var(--mono);font-size:12px}
pre.mermaid{background:transparent}
strong{font-weight:600}
details.chapter{border-top:1px solid var(--rule);margin-top:28px;padding-top:8px}
details.chapter>summary{cursor:pointer;list-style:none;display:flex;justify-content:space-between;align-items:baseline;padding:10px 0}
details.chapter>summary::-webkit-details-marker{display:none}
details.chapter .h1{font-weight:600;font-size:24px;letter-spacing:-.01em}
details.chapter .hint{font-family:var(--mono);font-size:11px;letter-spacing:.14em;text-transform:uppercase;color:var(--accent)}
details.chapter[open] .hint::after{content:"ed"}
a{color:var(--accent);text-decoration:none;border-bottom:1px solid var(--rule)}
#in-one-page+ol>li{margin:10px 0;max-width:80ch}
@media print{details.chapter>summary .hint{display:none}}
.sev-critical{color:var(--crit);font-family:var(--mono);font-size:11px;letter-spacing:.1em;text-transform:uppercase}
.sev-major{color:var(--major);font-family:var(--mono);font-size:11px;letter-spacing:.1em;text-transform:uppercase}
.sev-minor,.sev-info{color:var(--muted);font-family:var(--mono);font-size:11px;letter-spacing:.1em;text-transform:uppercase}
@media print{body{font-size:12px}.page{max-width:none;padding:0}h1{page-break-before:always;font-size:24px}h1:first-of-type{page-break-before:avoid}table{font-size:10.5px}tr,pre{page-break-inside:avoid}.wrap{overflow:visible}}
"""

_NODE = re.compile(r'^\s*(\w+)\["(.+)"\]\s*$')
_EDGE = re.compile(r'^\s*(\w+)\s*-->\|([^|]*)\|\s*(\w+)\s*$')


def flow_svg(src: str) -> str | None:
    """A flowchart LR with A["label"] nodes and A -->|n| B edges, drawn as
    inline SVG: nodes on a circle, straight arrows, edge labels at the
    midpoint. Deterministic and offline; no script needed."""
    import math
    nodes, edges = {}, []
    for ln in src.splitlines():
        m = _NODE.match(ln)
        if m:
            nodes[m.group(1)] = m.group(2); continue
        m = _EDGE.match(ln)
        if m and m.group(1) in nodes and m.group(3) in nodes:
            edges.append((m.group(1), m.group(2), m.group(3)))
    if not nodes:
        return None
    n = len(nodes); W, H = 760, 120 + 90 * min(n, 6); cx, cy = W / 2, H / 2; r = min(W, H) / 2 - 70
    pos = {}
    for i, k in enumerate(nodes):
        a = -math.pi / 2 + 2 * math.pi * i / n
        pos[k] = (cx + r * math.cos(a), cy + r * math.sin(a)) if n > 1 else (cx, cy)
    out = [f'<svg viewBox="0 0 {W} {H}" width="100%" style="max-width:{W}px;font-family:var(--mono);font-size:12px" role="img" aria-label="model feed graph">',
           '<defs><marker id="arr" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="8" markerHeight="8" orient="auto-start-reverse"><path d="M0 0L10 5L0 10z" fill="var(--accent)"/></marker></defs>']
    bw, bh = 150, 34
    for a, lbl, b in edges:
        (x1, y1), (x2, y2) = pos[a], pos[b]
        dx, dy = x2 - x1, y2 - y1; d = math.hypot(dx, dy) or 1
        ox, oy = dx / d, dy / d
        # start/end at box borders, offset sideways so A->B and B->A do not overlap
        sx, sy = -oy * 10, ox * 10
        tx = min(abs((bw / 2) / (ox or 1e-9)), abs((bh / 2) / (oy or 1e-9)))
        ax, ay = x1 + ox * tx + sx, y1 + oy * tx + sy
        bx, by = x2 - ox * (tx + 4) + sx, y2 - oy * (tx + 4) + sy
        mx, my = (ax + bx) / 2 + sx * 1.2, (ay + by) / 2 + sy * 1.2
        out.append(f'<line x1="{ax:.1f}" y1="{ay:.1f}" x2="{bx:.1f}" y2="{by:.1f}" stroke="var(--accent)" stroke-width="1.2" marker-end="url(#arr)"/>')
        out.append(f'<text x="{mx:.1f}" y="{my:.1f}" fill="var(--muted)" text-anchor="middle" dominant-baseline="middle" style="paint-order:stroke;stroke:var(--bg);stroke-width:4px">{html.escape(lbl)}</text>')
    for k, (x, y) in pos.items():
        out.append(f'<rect x="{x - bw / 2:.1f}" y="{y - bh / 2:.1f}" width="{bw}" height="{bh}" rx="6" fill="var(--card, var(--soft))" stroke="var(--rule)"/>')
        out.append(f'<text x="{x:.1f}" y="{y:.1f}" fill="var(--ink)" text-anchor="middle" dominant-baseline="middle" style="font-family:var(--sans);font-size:13px">{html.escape(nodes[k])}</text>')
    out.append("</svg>")
    return "\n".join(out)


_NUM_CELL = re.compile(r"^-?[\d,]+(\.\d+)?[KMB]?%?$|^\d+\.\d+$|^[\d,]+ \(.*\)$|^[\d.]+[KMB] \([\d,]+\)$")
_SEV = {"critical", "major", "minor", "info"}


def _inline(s: str) -> str:
    s = html.escape(s, quote=False)
    s = re.sub(r"`([^`]+)`", r"<code>\1</code>", s)
    s = re.sub(r"\*\*([^*]+)\*\*", r"<strong>\1</strong>", s)
    s = re.sub(r"\[([^\]]+)\]\((#[^)]+)\)", r'<a href="\2">\1</a>', s)
    s = re.sub(r"(?<![\w])_([^_]+)_(?![\w])", r"<em>\1</em>", s)
    return s


def _cell(c: str) -> str:
    if c in _SEV:
        return f'<td><span class="sev-{c}">{c}</span></td>'
    if _NUM_CELL.match(c):
        return f'<td class="num">{_inline(c)}</td>'
    return f"<td>{_inline(c)}</td>"


def md_to_html(md: str, title: str, css: str | None = None, logo_svg: str | None = None, brand: str | None = None,
               mermaid: bool = False, collapse: bool = True) -> str:
    """`collapse`: every top-level chapter after the first becomes a <details> block, closed by default; print opens them all."""
    out = [f"<title>{html.escape(title)}</title>", f"<style>{css or CSS}</style>"]
    if mermaid:
        out.append('<script src="https://cdnjs.cloudflare.com/ajax/libs/mermaid/11.4.1/mermaid.min.js"></script>'
                   '<script>if(window.mermaid){mermaid.initialize({startOnLoad:true,theme:document.documentElement.dataset.theme==="dark"||matchMedia("(prefers-color-scheme: dark)").matches?"dark":"neutral"})}</script>')
    out.append('<script>addEventListener("beforeprint",()=>document.querySelectorAll("details").forEach(d=>d.open=true))</script><div class="page">')
    if logo_svg or brand:
        out.append('<div class="cover">' + (logo_svg or "") + (f'<div class="kicker">{html.escape(brand)}</div>' if brand else "") + "</div>")
    lines = md.split("\n")
    i = 0
    para: list[str] = []
    lst = None
    seen_h1 = [False]; open_details = [False]

    def flush_para():
        nonlocal para
        if para:
            text = " ".join(para)
            cls = ' class="lead"' if text.startswith(("Generated ", "Same line item", "Every formula parsed", "Written by ")) else ""
            out.append(f"<p{cls}>{_inline(text)}</p>")
            para = []

    def flush_list():
        nonlocal lst
        if lst:
            tag, items = lst
            out.append(f"<{tag}>" + "".join(f"<li>{_inline(x)}</li>" for x in items) + f"</{tag}>")
            lst = None

    while i < len(lines):
        ln = lines[i]
        if ln.startswith("```"):
            flush_para(); flush_list()
            kind = ln[3:].strip()
            j = i + 1; buf = []
            while j < len(lines) and not lines[j].startswith("```"):
                buf.append(lines[j]); j += 1
            body = html.escape("\n".join(buf), quote=False)
            svg = flow_svg("\n".join(buf)) if kind == "mermaid" else None
            out.append(svg if svg else (f'<pre class="mermaid">{body}</pre>' if kind == "mermaid" and mermaid else f"<pre><code>{body}</code></pre>"))
            i = j + 1; continue
        if ln.startswith("|") and i + 1 < len(lines) and re.match(r"^\|[\s:|-]+\|$", lines[i + 1]):
            flush_para(); flush_list()
            hdr = [c.strip() for c in ln.strip("|").split("|")]
            j = i + 2; rows = []
            while j < len(lines) and lines[j].startswith("|"):
                rows.append([c.strip() for c in lines[j].strip("|").split("|")]); j += 1
            numcol = [all(_NUM_CELL.match(r[k]) or not r[k] for r in rows if k < len(r)) and any(k < len(r) and r[k] for r in rows) for k in range(len(hdr))]
            t = ['<div class="wrap"><table><tr>' + "".join(f'<th{" class=num" if numcol[k] else ""}>{_inline(h)}</th>' for k, h in enumerate(hdr)) + "</tr>"]
            for r in rows:
                t.append("<tr>" + "".join(_cell(c) for c in r) + "</tr>")
            t.append("</table></div>")
            out.append("".join(t)); i = j; continue
        m = re.match(r"^(#{1,3})\s+(.*)", ln)
        if m:
            flush_para(); flush_list()
            lvl = len(m.group(1)); text = m.group(2)
            hid = re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")
            if lvl == 1 and seen_h1[0] and collapse:
                if open_details[0]:
                    out.append("</details>")
                out.append(f'<details class="chapter" id="{hid}"><summary><span class="h1">{_inline(text)}</span><span class="hint">open</span></summary>')
                open_details[0] = True
            else:
                out.append(f'<h{lvl} id="{hid}">{_inline(text)}</h{lvl}>')
            if lvl == 1:
                seen_h1[0] = True
            i += 1; continue
        if ln.strip() == "---":
            flush_para(); flush_list(); out.append("<hr>"); i += 1; continue
        m = re.match(r"^(\s*)[-*]\s+(.*)", ln)
        if m:
            flush_para()
            if not lst or lst[0] != "ul": flush_list(); lst = ("ul", [])
            lst[1].append(("&nbsp;&nbsp;" * (len(m.group(1)) // 2)) + m.group(2)); i += 1; continue
        m = re.match(r"^\d+\.\s+(.*)", ln)
        if m:
            flush_para()
            if not lst or lst[0] != "ol": flush_list(); lst = ("ol", [])
            lst[1].append(m.group(1)); i += 1; continue
        if not ln.strip():
            flush_para(); flush_list(); i += 1; continue
        flush_list(); para.append(ln.strip()); i += 1
    flush_para(); flush_list()
    if open_details[0]:
        out.append("</details>")
    out.append("</div>")
    return "\n".join(out)
