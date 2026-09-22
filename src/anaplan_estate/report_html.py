"""Self-contained HTML for the three-level report.

Rendered from the report dict (report.build), not from Markdown, so search,
filters, sorting, review statuses and the register download can work on
structured data. No external requests: fonts and tokens are embedded when a
theme stylesheet is supplied, all links are same-document fragments, and the
findings JSON is embedded for the page's own script.

Review statuses are the reader's, not the analysis's. They live in the
browser's localStorage under a key derived from the report title and
generation date, and can be exported as JSON from the page. Nothing is
stored anywhere else.
"""
from __future__ import annotations
import html, json, re
from .findings import AREA_LABEL, _c

CSS = r"""
:root{--bg:#F7F8F6;--ink:#1B2430;--muted:#5C6773;--rule:#D9DED9;--soft:#EEF1EE;--accent:#0E5E6F;--card:#FFFFFF;
--high:#A6301C;--med:#B7791F;--low:#4B6B5C;--conf:#0E5E6F;--part:#7A5F1F;--inf:#6B5A7A;
--sans:"Geist Sans","IBM Plex Sans","Helvetica Neue",Arial,sans-serif;--mono:"Geist Mono","IBM Plex Mono",Consolas,monospace}
@media (prefers-color-scheme:dark){:root:not([data-theme="light"]){--bg:#0F1416;--ink:#E6EBE8;--muted:#9AA6A0;--rule:#2E393C;--soft:#1B2427;--accent:#5FB3C1;--card:#161D20;
--high:#E07A63;--med:#D9A441;--low:#8FB8A6;--conf:#5FB3C1;--part:#D9A441;--inf:#B39DDB}}
:root[data-theme="dark"]{--bg:#0F1416;--ink:#E6EBE8;--muted:#9AA6A0;--rule:#2E393C;--soft:#1B2427;--accent:#5FB3C1;--card:#161D20;--high:#E07A63;--med:#D9A441;--low:#8FB8A6;--conf:#5FB3C1;--part:#D9A441;--inf:#B39DDB}
*{box-sizing:border-box}html{scroll-behavior:smooth}
body{background:var(--bg);color:var(--ink);font-family:var(--sans);font-size:15px;line-height:1.55;margin:0}
.page{max-width:1040px;margin:0 auto;padding:36px 24px 80px}
a{color:var(--accent)}a:focus-visible,button:focus-visible,input:focus-visible,select:focus-visible,summary:focus-visible{outline:2px solid var(--accent);outline-offset:2px}
.kicker{font-family:var(--mono);font-size:11px;letter-spacing:.18em;text-transform:uppercase;color:var(--muted)}
header.top{border-bottom:1px solid var(--rule);padding-bottom:14px;margin-bottom:22px}
header.top h1{font-size:30px;line-height:1.15;margin:8px 0 4px;letter-spacing:-.01em;font-weight:600}
header.top .lead{color:var(--muted);font-size:13.5px;margin:0}
nav.jump{position:sticky;top:0;background:var(--bg);z-index:5;border-bottom:1px solid var(--rule);padding:8px 0;margin-bottom:18px;display:flex;gap:14px;flex-wrap:wrap;font-size:13px}
nav.jump a{text-decoration:none;color:var(--ink);padding:2px 0;border-bottom:2px solid transparent}nav.jump a:hover{border-bottom-color:var(--accent)}
h2{font-size:21px;font-weight:600;margin:34px 0 10px;letter-spacing:-.01em}
h3{font-size:16px;font-weight:600;margin:22px 0 8px}
h4{font-size:14px;font-weight:600;margin:14px 0 4px}
p{max-width:78ch;margin:8px 0}
.muted{color:var(--muted)}
.tiles{display:grid;grid-template-columns:repeat(auto-fit,minmax(140px,1fr));gap:10px;margin:14px 0 18px}
.tile{background:var(--card);border:1px solid var(--rule);border-radius:8px;padding:10px 12px}
.tile .v{font-size:22px;font-weight:600;letter-spacing:-.01em}.tile .k{font-size:11.5px;color:var(--muted);text-transform:uppercase;letter-spacing:.08em}
.cards{display:grid;grid-template-columns:repeat(auto-fit,minmax(260px,1fr));gap:12px;margin:12px 0 18px}
.card{background:var(--card);border:1px solid var(--rule);border-left:4px solid var(--accent);border-radius:8px;padding:12px 14px}
.card h3{margin:0 0 6px;font-size:15px}.card p{font-size:13.5px;margin:6px 0}.card .lab{font-weight:600;color:var(--muted);font-size:11.5px;text-transform:uppercase;letter-spacing:.06em}
.badge{display:inline-block;font-family:var(--mono);font-size:10.5px;letter-spacing:.06em;text-transform:uppercase;padding:2px 7px;border-radius:999px;border:1px solid var(--rule);color:var(--muted);margin-right:4px;white-space:nowrap}
.badge.imp-high{border-color:var(--high);color:var(--high)}.badge.imp-medium{border-color:var(--med);color:var(--med)}.badge.imp-low{border-color:var(--low);color:var(--low)}
.badge.st-confirmed{border-color:var(--conf);color:var(--conf)}.badge.st-partial{border-color:var(--part);color:var(--part)}.badge.st-inferred{border-color:var(--inf);color:var(--inf)}
.invite{background:var(--soft);border-radius:8px;padding:12px 14px;margin:18px 0;font-size:14px}
.limits li{margin:4px 0}
.map{margin:12px 0;overflow-x:auto}.map svg{max-width:100%;height:auto;font-family:var(--sans)}
.controls{display:flex;flex-wrap:wrap;gap:8px;align-items:center;background:var(--soft);padding:10px;border-radius:8px;margin:10px 0 16px;position:sticky;top:38px;z-index:4}
.controls input,.controls select,.controls button{font:inherit;font-size:13px;padding:5px 8px;border:1px solid var(--rule);border-radius:6px;background:var(--card);color:var(--ink)}
.controls input{min-width:220px;flex:1}.controls .count{font-size:12.5px;color:var(--muted);margin-left:auto}
.area{margin-top:26px}.area>p{color:var(--muted);font-size:13.5px}
article.f{background:var(--card);border:1px solid var(--rule);border-radius:8px;padding:12px 16px;margin:10px 0}
article.f header{display:flex;flex-wrap:wrap;gap:8px;align-items:baseline}
article.f header h3{margin:0;font-size:15.5px;flex:1 1 320px}
article.f .objs{font-family:var(--mono);font-size:12px;color:var(--muted);word-break:break-word;margin:6px 0 8px}
article.f .objs code{background:none;padding:0}
article.f .status{margin-left:auto}article.f .status select{font-size:12px;padding:3px 6px;border:1px solid var(--rule);border-radius:6px;background:var(--bg);color:var(--ink)}
dl.fields{display:grid;grid-template-columns:max-content 1fr;gap:4px 14px;margin:8px 0;font-size:14px}
dl.fields dt{color:var(--muted);font-size:12px;text-transform:uppercase;letter-spacing:.06em;padding-top:3px}dl.fields dd{margin:0;max-width:80ch}
dl.fields ul{margin:0;padding-left:18px}
details{margin:8px 0}summary{cursor:pointer;font-weight:600;font-size:13.5px}
details.ev>div{margin-top:8px}
.wrap{overflow-x:auto;max-width:100%;border:1px solid var(--rule);border-radius:6px}
table{border-collapse:collapse;width:100%;font-size:13px}th,td{text-align:left;vertical-align:top;padding:6px 8px;border-bottom:1px solid var(--rule)}
th{font-size:11.5px;text-transform:uppercase;letter-spacing:.06em;color:var(--muted);background:var(--soft);position:sticky;top:0}
td{word-break:break-word}td code{white-space:pre-wrap}
code{font-family:var(--mono);font-size:12px;background:var(--soft);padding:1px 4px;border-radius:3px}
.formula{display:flex;gap:6px;align-items:flex-start}.formula button{font-size:11px;padding:1px 6px;border:1px solid var(--rule);border-radius:4px;background:var(--bg);color:var(--muted);cursor:pointer}
table.reg th[data-sort]{cursor:pointer}table.reg th[data-sort]:after{content:" \2195";opacity:.5}
.back{font-size:12.5px}.back a{margin-right:12px}
.empty{color:var(--muted);font-style:italic;padding:12px}
footer{margin-top:40px;border-top:1px solid var(--rule);padding-top:12px;font-size:12.5px;color:var(--muted)}
.sr{position:absolute;left:-9999px}
.hit{font-size:12px;color:var(--accent);margin:4px 0}
.per{font-size:13px;margin:6px 0 0;padding-left:18px}
.idx{display:none}
.metric{display:flex;flex-wrap:wrap;gap:6px 18px;font-size:15px;margin:10px 0 14px}.metric b{font-size:22px;font-weight:600;margin-right:4px}
.example{border:1px solid var(--rule);border-radius:8px;padding:10px 14px;margin:12px 0;font-size:13.5px}.example dt{font-weight:600;margin-top:6px}.example dd{margin:0}
.fnote{font-size:12.5px;color:var(--muted)}
@media (max-width:640px){dl.fields{grid-template-columns:1fr}.controls{position:static}nav.jump{position:static}}
@media print{
 :root{--bg:#fff;--ink:#111;--muted:#444;--rule:#bbb;--soft:#f2f2f2;--accent:#0E5E6F;--card:#fff}
 body{background:#fff;color:#111;font-size:11px}.page{max-width:none;padding:0}
 nav.jump,.controls,.status,.formula button,#dl-register,#dl-status,.noprint{display:none!important}
 h2{page-break-before:always}#summary h2{page-break-before:avoid}
 article.f,.card,.tile,tr{page-break-inside:avoid}
 thead{display:table-header-group}th{position:static}
 .wrap{overflow:visible;border:none}table{font-size:9.5px}td code{white-space:pre-wrap;word-break:break-all}
 details.ev:not([open]){display:block}details.ev:not([open])>div{display:none}
 body.print-summary #findings,body.print-summary #reference{display:none}
 a{color:#111;text-decoration:none}
}
"""

JS = r"""
(function(){
 var data=JSON.parse(document.getElementById('report-data').textContent);
 var key='anaplan-estate-status:'+data.key;
 function load(){try{return JSON.parse(localStorage.getItem(key)||'{}')}catch(e){return {}}}
 function save(o){try{localStorage.setItem(key,JSON.stringify(o))}catch(e){}}
 var st=load();
 document.querySelectorAll('article.f').forEach(function(a){
   var sel=a.querySelector('select.stsel');if(!sel)return;
   var id=a.dataset.id; if(st[id]) sel.value=st[id]; a.dataset.status=sel.value;
   sel.addEventListener('change',function(){st[id]=sel.value;a.dataset.status=sel.value;save(st);apply()});
 });
 function openTo(){var h=location.hash&&document.getElementById(decodeURIComponent(location.hash.slice(1)));if(!h)return;
   var d=h.closest('details');while(d){d.open=true;d=d.parentElement&&d.parentElement.closest('details')}
   var art=h.closest('article.f');if(art){art.hidden=false}h.scrollIntoView();}
 addEventListener('hashchange',openTo);openTo();
 var fl=document.getElementById('f-low');var q=document.getElementById('q'),fm=document.getElementById('f-model'),fa=document.getElementById('f-area'),fs=document.getElementById('f-strength'),fst=document.getElementById('f-status'),so=document.getElementById('f-sort'),cnt=document.getElementById('f-count');
 var IMP={high:0,medium:1,low:2},STR={confirmed:0,partial:1,inferred:2};
 function apply(){
   var t=(q.value||'').toLowerCase().trim(),n=0;
   var arts=Array.prototype.slice.call(document.querySelectorAll('article.f'));
   arts.forEach(function(a){
     var ok=true;var hit=a.querySelector('.hit');if(hit){hit.hidden=true;hit.textContent=''}
     if(t){var head=(a.dataset.search||'').indexOf(t)>=0;var idx=a.querySelector('.idx');var body=idx?idx.textContent.toLowerCase():'';var pos=body.indexOf(t);ok=head||pos>=0;
       if(ok&&!head&&hit){var line=body.slice(Math.max(0,body.lastIndexOf('\n',pos)+1),body.indexOf('\n',pos)>0?body.indexOf('\n',pos):body.length);
         hit.textContent='Matched in '+(line.indexOf('formula:')===0?'a formula':line.indexOf('object:')===0?'an affected object':'the evidence')+': '+line.replace(/^(formula|object|evidence|text):\s*/,'').slice(0,140);hit.hidden=false;
         var d=a.querySelector('details.full');if(d)d.open=true}}
     if(ok&&fm.value&&a.dataset.model!==fm.value)ok=false;
     if(ok&&fa.value&&a.dataset.area!==fa.value)ok=false;
     if(ok&&fs.value&&a.dataset.strength!==fs.value)ok=false;
     if(ok&&fst.value&&(a.dataset.status||'To review')!==fst.value)ok=false;
     if(ok&&!fl.checked&&!t&&a.dataset.importance==='low')ok=false;
     a.hidden=!ok; if(ok)n++;
   });
   var s=so.value;
   function num(v){return v===''?null:parseFloat(v)}
   function descNullLast(a,b){if(a===null&&b===null)return 0;if(a===null)return 1;if(b===null)return -1;return b-a}
   document.querySelectorAll('section.area').forEach(function(sec){
     var list=Array.prototype.slice.call(sec.querySelectorAll('article.f'));
     list.sort(function(x,y){
       if(s==='importance')return (IMP[x.dataset.importance]-IMP[y.dataset.importance])||(STR[x.dataset.strength]-STR[y.dataset.strength])||descNullLast(num(x.dataset.cells),num(y.dataset.cells));
       if(s==='cells')return descNullLast(num(x.dataset.cells),num(y.dataset.cells))||(IMP[x.dataset.importance]-IMP[y.dataset.importance]);
       if(s==='effort')return x.dataset.model.localeCompare(y.dataset.model)||descNullLast(num(x.dataset.effort),num(y.dataset.effort));
       if(s==='model')return x.dataset.model.localeCompare(y.dataset.model)||(IMP[x.dataset.importance]-IMP[y.dataset.importance]);
       if(s==='strength')return (STR[x.dataset.strength]-STR[y.dataset.strength])||(IMP[x.dataset.importance]-IMP[y.dataset.importance]);
       return parseInt(x.dataset.id.slice(1))-parseInt(y.dataset.id.slice(1));});
     list.forEach(function(a){sec.appendChild(a)});
     var vis=list.some(function(a){return !a.hidden});var e=sec.querySelector('.empty');if(e)e.hidden=vis;
   });
   var active=[];if(fm.value)active.push('model');if(fa.value)active.push('category');if(fs.value)active.push('evidence');if(fst.value)active.push('status');
   cnt.textContent=n+' of '+arts.length+' findings shown'+((!fl.checked&&!t)?' (reference findings hidden)':'')+(active.length?' with filters on '+active.join(', ')+' (Clear removes them)':'')+(t?' for "'+t+'" (searched across all evidence)':'');
 }
 [q,fm,fa,fs,fst,so,fl].forEach(function(el){el.addEventListener('input',apply);el.addEventListener('change',apply)});
 apply();
 document.getElementById('f-clear').addEventListener('click',function(){q.value='';fm.value='';fa.value='';fs.value='';fst.value='';so.value='importance';fl.checked=false;apply();q.focus()});
 document.querySelectorAll('.copy').forEach(function(b){b.addEventListener('click',function(){var t=b.previousElementSibling.textContent;
   if(navigator.clipboard){navigator.clipboard.writeText(t).then(function(){b.textContent='copied';setTimeout(function(){b.textContent='copy'},1200)})}})});
 function dl(name,text,type){var a=document.createElement('a');a.href='data:'+type+';charset=utf-8,'+encodeURIComponent(text);a.download=name;document.body.appendChild(a);a.click();a.remove()}
 document.getElementById('dl-register').addEventListener('click',function(){dl('findings-register.csv',data.csv,'text/csv')});
 document.getElementById('dl-status').addEventListener('click',function(){var o={report:data.key,exported:new Date().toISOString(),statuses:load()};dl('review-statuses.json',JSON.stringify(o,null,1),'application/json')});
 document.getElementById('print-summary').addEventListener('click',function(){document.body.classList.add('print-summary');window.print();setTimeout(function(){document.body.classList.remove('print-summary')},500)});
 document.getElementById('expand-all').addEventListener('click',function(){document.querySelectorAll('#findings details').forEach(function(d){d.open=true})});
 document.getElementById('collapse-all').addEventListener('click',function(){document.querySelectorAll('#findings details').forEach(function(d){d.open=false})});
 var reg=document.querySelector('table.reg');if(reg){reg.querySelectorAll('th[data-sort]').forEach(function(th,i){th.addEventListener('click',function(){
   var rows=Array.prototype.slice.call(reg.tBodies[0].rows),num=th.dataset.sort==='num',asc=th.dataset.asc!=='1';th.dataset.asc=asc?'1':'0';
   rows.sort(function(a,b){var x=a.cells[i].hasAttribute('data-v')?a.cells[i].dataset.v:a.cells[i].textContent,y=b.cells[i].hasAttribute('data-v')?b.cells[i].dataset.v:b.cells[i].textContent;if(num){if(x===''&&y==='')return 0;if(x==='')return 1;if(y==='')return -1;x=parseFloat(x);y=parseFloat(y);return asc?x-y:y-x}return asc?x.localeCompare(y):y.localeCompare(x)});
   rows.forEach(function(r){reg.tBodies[0].appendChild(r)})})})}
})();
"""


def _e(s) -> str:
    return html.escape(str(s), quote=True)


def _inline(s: str) -> str:
    """Inline markdown subset: `code`, **bold**, [text](#anchor)."""
    s = _e(s)
    s = re.sub(r"`([^`]*)`", lambda m: f"<code>{m.group(1)}</code>", s)
    s = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", s)
    s = re.sub(r"\[([^\]]+)\]\((#[^)]+)\)", r'<a href="\2">\1</a>', s)
    return s


def _cell(c: str) -> str:
    if c.startswith("`") and c.endswith("`") and len(c) > 2 and c.count("`") == 2:
        return f'<td><div class="formula"><code>{_e(c[1:-1])}</code><button type="button" class="copy">copy</button></div></td>'
    return f"<td>{_inline(c)}</td>"


def md_fragment(lines: list[str]) -> str:
    """Tables, bullet lists, numbered lists and paragraphs from the evidence lines. Complete, never truncated."""
    out = []; i = 0; para = []; lst = None
    def flush_p():
        nonlocal para
        if para:
            out.append(f"<p>{_inline(' '.join(para))}</p>"); para = []
    def flush_l():
        nonlocal lst
        if lst:
            out.append(f"<{lst[0]}>" + "".join(f"<li>{_inline(x)}</li>" for x in lst[1]) + f"</{lst[0]}>"); lst = None
    while i < len(lines):
        ln = lines[i]
        if ln.startswith("|") and i + 1 < len(lines) and re.match(r"^\|[\s:|-]+\|$", lines[i + 1]):
            flush_p(); flush_l()
            hdr = [c.strip() for c in ln.strip("|").split("|")]
            j = i + 2; rows = []
            while j < len(lines) and lines[j].startswith("|"):
                rows.append([c.strip() for c in lines[j].strip("|").split("|")]); j += 1
            t = ['<div class="wrap"><table><thead><tr>' + "".join(f"<th>{_inline(h)}</th>" for h in hdr) + "</tr></thead><tbody>"]
            for r in rows:
                t.append("<tr>" + "".join(_cell(c) for c in r) + "</tr>")
            t.append("</tbody></table></div>")
            out.append("".join(t)); i = j; continue
        m = re.match(r"^\s*[-*]\s+(.*)", ln)
        if m:
            flush_p()
            if not lst or lst[0] != "ul": flush_l(); lst = ("ul", [])
            lst[1].append(m.group(1)); i += 1; continue
        m = re.match(r"^\d+\.\s+(.*)", ln)
        if m:
            flush_p()
            if not lst or lst[0] != "ol": flush_l(); lst = ("ol", [])
            lst[1].append(m.group(1)); i += 1; continue
        if not ln.strip():
            flush_p(); flush_l(); i += 1; continue
        flush_l(); para.append(ln.strip()); i += 1
    flush_p(); flush_l()
    return "\n".join(out)


def _theme_bits(theme_css: str | None) -> str:
    """Take only tokens and embedded fonts from a supplied theme; layout stays ours."""
    if not theme_css:
        return ""
    bits = re.findall(r"@font-face\{[^}]*\}", theme_css)
    root = re.findall(r":root\{[^}]*\}", theme_css)
    return "\n".join(bits + root)


def map_svg(nodes: list[dict], edges: list[dict]) -> str:
    """Model map: nodes as boxes sized by label, feeds as dashed arrows (inferred). Deterministic layout: sources left, sinks right."""
    if not nodes:
        return ""
    names = [n["name"] for n in nodes]
    outd = {n: 0 for n in names}; ind = {n: 0 for n in names}
    for e in edges:
        if e["from"] in outd and e["to"] in ind:
            outd[e["from"]] += 1; ind[e["to"]] += 1
    cols = {}
    for n in names:
        cols[n] = 0 if outd[n] and not ind[n] else 2 if ind[n] and not outd[n] else 1
    by_col = {c: [n for n in names if cols[n] == c] for c in (0, 1, 2)}
    W, H = 300, 64; gapx, gapy = 120, 24
    pos = {}
    ncols = [c for c in (0, 1, 2) if by_col[c]]
    height = max(len(by_col[c]) for c in ncols) * (H + gapy)
    for ci, c in enumerate(ncols):
        col_h = len(by_col[c]) * (H + gapy)
        for ri, n in enumerate(by_col[c]):
            pos[n] = (ci * (W + gapx) + 10, (height - col_h) / 2 + ri * (H + gapy) + 10)
    width = len(ncols) * (W + gapx) - gapx + 20
    out = [f'<svg viewBox="0 0 {width} {height + 20}" role="img" aria-label="Model map">',
           '<defs><marker id="arr" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto"><path d="M0,0 L10,5 L0,10 z" fill="currentColor"/></marker></defs>']
    cells = {n["name"]: n["cells"] for n in nodes}
    for e in edges:
        if e["from"] not in pos or e["to"] not in pos:
            continue
        x1, y1 = pos[e["from"]]; x2, y2 = pos[e["to"]]
        if x1 == x2:
            sx, sy, ex, ey = x1 + W / 2, y1 + (H if y2 > y1 else 0), x2 + W / 2, y2 + (0 if y2 > y1 else H)
        else:
            sx, sy, ex, ey = (x1 + W, y1 + H / 2, x2, y2 + H / 2) if x2 > x1 else (x1, y1 + H / 2, x2 + W, y2 + H / 2)
        mx, my = (sx + ex) / 2, (sy + ey) / 2
        out.append(f'<line x1="{sx:.0f}" y1="{sy:.0f}" x2="{ex:.0f}" y2="{ey:.0f}" stroke="currentColor" stroke-dasharray="5 4" stroke-width="1.4" marker-end="url(#arr)" opacity=".8"/>')
        out.append(f'<text x="{mx:.0f}" y="{my - 4:.0f}" font-size="11" text-anchor="middle" fill="currentColor" opacity=".8">{e["actions"]} inferred</text>')
    for n, (x, y) in pos.items():
        out.append(f'<rect x="{x:.0f}" y="{y:.0f}" width="{W}" height="{H}" rx="8" fill="var(--card)" stroke="currentColor" stroke-width="1.2"/>')
        out.append(f'<text x="{x + 12:.0f}" y="{y + 26:.0f}" font-size="14" font-weight="600" fill="currentColor">{_e(n[:34])}</text>')
        out.append(f'<text x="{x + 12:.0f}" y="{y + 46:.0f}" font-size="12" fill="currentColor" opacity=".75">{_c(cells[n])} cells</text>')
    out.append("</svg>")
    return "\n".join(out)


def _badges(x: dict) -> str:
    return (f'<span class="badge imp-{x["importance"]}">importance {x["importance"]}</span>'
            f'<span class="badge st-{x["strength"]}">evidence {x["strength"]}</span>'
            f'<span class="badge">complexity {x["complexity"]}</span>')


def _index_text(x: dict) -> str:
    """Complete search text for one finding: every affected object, every evidence row and formula, explanatory text.
    One entry per line, prefixed by kind (object / formula / evidence / text) so a hit can say where it matched."""
    formula_like = re.compile(r"[()\[\]+*/<>=]|IF|THEN")

    def classify(inner: str) -> str:
        return ("formula: " if formula_like.search(inner) else "object: ") + inner

    lines = [f"text: {x['title']} {x['observed']} {x['why']} {x['scope']}"]
    lines += [f"object: {o}" for o in x["objects"]]
    for l in x["evidence"]:
        if not l.strip() or re.match(r"^\|[\s:|-]+\|$", l):
            continue
        for inner in re.findall(r"`([^`]+)`", l):
            lines.append(classify(inner))
        plain = re.sub(r"`", "", l)
        if l.startswith("|"):
            lines.append("evidence: " + " | ".join(c.strip() for c in plain.strip("|").split("|")))
        else:
            lines.append("evidence: " + plain.strip("-* ").strip())
    return "\n".join(lines)


def _finding(x: dict, rep: dict) -> str:
    head = " ".join([x["id"], x["title"], x["model"], AREA_LABEL[x["area"]], x["kind_label"]] + x["rules"]).lower()
    status_opts = "".join(f'<option{" selected" if s == "To review" else ""}>{_e(s)}</option>' for s in rep["statuses"])
    ex = x["objects"][:3]; more = len(x["objects"]) - len(ex)
    svc = ""
    if rep.get("service_url"):
        svc = f'<p class="fnote noprint">Have a change planned here? <a href="{_e(rep["service_url"])}">Request a change-impact review</a>.</p>'
    missing = "".join(f"<li>{_inline(m)}</li>" for m in x["missing"]) or "<li>nothing beyond the exports</li>"
    related = f'<dt>Alternative or related</dt><dd>{", ".join(f"<a href=#{r}>{r}</a>" for r in x["related"])}</dd>' if x["related"] else ""
    impl = f'<dt>Implementation, with prerequisites</dt><dd><ul>{"".join(f"<li>{_inline(v)}</li>" for v in x["implementation"])}</ul></dd>' if x["implementation"] else ""
    nrows = len([l for l in x["evidence"] if l.startswith("|")]) - 2 if any(l.startswith("|") for l in x["evidence"]) else len(x["evidence"])
    ev = f'<details class="ev"><summary>Evidence ({max(nrows, 0)} rows)</summary><div>{md_fragment(x["evidence"])}</div></details>' if x["evidence"] else ""
    val = f'<details><summary>Validation guidance</summary><div><ul>{"".join(f"<li>{_inline(v)}</li>" for v in x["validation"])}</ul></div></details>' if x["validation"] else ""
    cells_v = "" if x["footprint_cells"] is None else x["footprint_cells"]
    eff_v = "" if x["footprint_effort"] is None else x["footprint_effort"]
    return f'''<article class="f" id="{x["id"]}" data-id="{x["id"]}" data-model="{_e(x["model"])}" data-area="{x["area"]}" data-importance="{x["importance"]}" data-strength="{x["strength"]}" data-cells="{cells_v}" data-effort="{eff_v}" data-search="{_e(head)}">
<header><h3><span class="muted">{x["id"]}.</span> {_e(x["title"])}</h3><span class="badge">{x["kind_label"]}</span>{_badges(x)}<label class="status noprint"><span class="sr">Review status for {x["id"]}</span><select class="stsel" aria-label="Review status (yours, stored in this browser)">{status_opts}</select></label></header>
<div class="objs">{_e(x["model"])} &middot; {" &middot; ".join(f"<code>{_e(o)}</code>" for o in ex)}{f" &middot; and {more} more" if more > 0 else ""} <span class="muted">({_e(x["object_label"])})</span></div>
<p class="hit" hidden></p>
<dl class="fields">
<dt>Observed</dt><dd>{_inline(x["summary"])}</dd>
<dt>Why it matters</dt><dd>{_inline(x["why"])}</dd>
<dt>Next investigation step</dt><dd>{_inline(x["next_step"])}</dd>
</dl>
<details class="full"><summary>Full assessment and affected objects ({_e(x["object_label"])})</summary><div>
<dl class="fields">
<dt>Observed, in full</dt><dd>{_inline(x["observed"])}</dd>
<dt>Affected scope</dt><dd>{_inline(x["scope"])}</dd>
<dt>Potential benefit</dt><dd>{_inline(x["benefit"])} <span class="badge">{x["benefit_kind"]}</span></dd>
<dt>Evidence strength</dt><dd><strong>{x["strength"]}.</strong> {_inline(x["basis"])}</dd>
<dt>Missing information</dt><dd><ul>{missing}</ul></dd>
<dt>Keeping the design</dt><dd>{_inline(x["keep_design"])}</dd>
{impl}{related}
<dt>All affected objects</dt><dd class="objs">{" &middot; ".join(f"<code>{_e(o)}</code>" for o in x["objects"])}</dd>
</dl>
{ev}{val}{svc}
</div></details>
<div class="idx">{_e(_index_text(x))}</div>
<p class="back"><a href="#summary">Summary</a><a href="#register">Register</a><a href="#area-{x["area"]}">Area</a></p>
</article>'''


def render(rep: dict, theme_css: str | None = None, logo_svg: str | None = None, brand: str | None = None, csv_text: str = "") -> str:
    fmap = {x["id"]: x for x in rep["findings"]}
    models = sorted({x["model"] for x in rep["findings"]})
    key = re.sub(r"[^a-z0-9]+", "-", f"{rep['title']} {rep['generated']}".lower())
    data = json.dumps({"key": key, "csv": csv_text, "ids": [x["id"] for x in rep["findings"]]}).replace("</", "<\\/")
    sc = rep["scope"]
    out = [f"<title>{_e(rep['title'])}</title>", f"<style>{_theme_bits(theme_css)}{CSS}</style>", '<div class="page">']
    out.append('<header class="top">' + (logo_svg or "") + (f'<div class="kicker">{_e(brand)}</div>' if brand else "") +
               f'<h1>{_e(rep["title"])}</h1><p class="lead">{_e(rep["description"])} Generated {_e(rep["generated"])}.</p></header>')
    out.append('<nav class="jump" aria-label="Sections"><a href="#summary">Summary</a><a href="#findings">Findings</a><a href="#register">Register</a><a href="#models">Models and coverage</a><a href="#dependencies">Dependency evidence</a><a href="#methodology">Methodology</a><a href="#glossary">Glossary</a>'
               '<span style="margin-left:auto"></span><button type="button" id="print-summary" class="noprint">Print summary</button></nav>')
    # ---- level 1
    out.append('<section id="summary"><h2>Summary</h2>')
    mt = rep["metrics"]
    out.append(f'<div class="metric"><span><b>{mt["models"]}</b> models reviewed</span><span>&middot;</span><span><b>{mt["review_first"]}</b> findings to review first</span><span>&middot;</span><span><b>{mt["reference"]}</b> additional reference findings</span></div>'
               f'<p class="fnote">Findings are observations ({mt["observations"]}) or review candidates; none is a validated defect. Coverage is under Models and coverage.</p>')
    out += [f"<p>{_inline(p)}</p>" for p in rep["summary_text"]]
    out.append("<h3>Observations</h3><ol>" + "".join(f"<li>{_inline(o)}</li>" for o in rep["observations"]) + "</ol>")
    if rep["investigations"]:
        out.append("<h3>Priority investigations</h3><div class=\"cards\">")
        for n, p in enumerate(rep["investigations"], 1):
            per = ""
            if p.get("per_model"):
                per = "<details><summary>Per model</summary><ul class=\"per\">" + "".join(
                    f'<li><a href="#{pm["id"]}">{_e(pm["model"])}</a>: {pm["modules"]} modules, {_c(pm["cells"])} cells' + (f', {pm["effort"]:.1f}% effort' if pm["effort"] else "") + f'; largest {" &middot; ".join(f"<code>{_e(t)}</code>" for t in pm["top"])} <span class="badge st-{pm["strength"]}">evidence {pm["strength"]}</span></li>' for pm in p["per_model"]) + "</ul></details>"
            links = " ".join(f'<a href="#{i_}">{i_}</a>' for i_ in p["ids"])
            out.append(f'<div class="card"><h3><span class="muted">{n}.</span> {_e(p["title"])}</h3><p>{_inline(p["sentence"])}</p>'
                       f'<p><span class="lab">Who</span><br>{_e(p["who"])}</p><p><span class="lab">Next step</span><br>{_inline(p["next"])}</p>{per}<p class="fnote">Findings: {links}</p></div>')
        out.append("</div>")
    else:
        out.append('<p class="muted">No finding met the bar for a priority investigation.</p>')
    action = (f'<p><a href="{_e(rep["service_url"])}"><strong>Request a change-impact review</strong></a></p>' if rep.get("service_url")
              else '<p class="fnote">Request route: not configured in this report (set --service-url when generating).</p>')
    out.append('<div class="invite"><strong>Have a change planned in this estate?</strong><p>Request a review of one proposed change: the dependencies visible in your exports, what still needs checking, and a validation plan with your model owner.</p>' + action + "</div>")
    ex = rep.get("example")
    if ex:
        out.append(f'<details class="example"><summary>Illustrative example: from a proposed change to a validation plan</summary><p class="fnote">Built from the exports; no further analysis has been run.</p><dl>'
                   f'<dt>Proposed change</dt><dd>{_inline(ex["change"])}</dd><dt>Dependency evidence examined</dt><dd>{_inline(ex["evidence"])}</dd>'
                   f'<dt>Additional context required</dt><dd>{_inline(ex["context"])}</dd><dt>Validation plan that would result</dt><dd>{_inline(ex["plan"])}</dd></dl></details>')
    if rep["map"]["nodes"]:
        out.append("<h3>Model map</h3><p class=\"muted\">Feeds inferred from import action names (dashed); no export confirms them.</p>"
                   f'<div class="map">{map_svg(rep["map"]["nodes"], rep["map"]["edges"])}</div>')
        if rep["map"]["edges"]:
            out.append('<details><summary>Feed table</summary><div class="wrap"><table><thead><tr><th>From</th><th>To</th><th>Import actions</th><th>Into</th><th>Basis</th></tr></thead><tbody>' +
                       "".join(f'<tr><td>{_e(e["from"])}</td><td>{_e(e["to"])}</td><td>{e["actions"]}</td><td>{_e(", ".join(e["targets"]))}</td><td>{_e(e["basis"])}</td></tr>' for e in rep["map"]["edges"]) + "</tbody></table></div></details>")
    out.append("<h3>Coverage limitations</h3><ul class=\"limits\">" + "".join(f"<li>{_inline(l)}</li>" for l in rep["limitations"]) + "</ul></section>")
    # ---- level 2
    out.append('<section id="findings"><h2>Findings</h2><p class="muted">Grouped by the decision they inform. Each finding opens compact: observed, why it matters, the next investigation step, three example objects. "Full assessment" holds every affected object, the evidence and formulas, missing checks, reasons to keep the design, and implementation prerequisites. Search covers all of it, collapsed or not. Sorting is within each category. Reference findings are hidden until you tick the box. Review status is yours and is stored only in this browser.</p>')
    out.append('<div class="controls noprint" role="search"><label class="sr" for="q">Search findings</label><input id="q" type="search" placeholder="Search titles, IDs, models, object names, rules">'
               f'<select id="f-model" aria-label="Model"><option value="">All models</option>{"".join(f"<option>{_e(m)}</option>" for m in models)}</select>'
               f'<select id="f-area" aria-label="Category"><option value="">All categories</option>{"".join(f"<option value={a['key']}>{_e(a['label'])}</option>" for a in rep['areas'])}</select>'
               '<select id="f-strength" aria-label="Evidence status"><option value="">Any evidence</option><option>confirmed</option><option>partial</option><option>inferred</option></select>'
               f'<select id="f-status" aria-label="Review status"><option value="">Any status</option>{"".join(f"<option>{_e(s)}</option>" for s in rep['statuses'])}</select>'
               '<select id="f-sort" aria-label="Sort by"><option value="importance">Sort within category: importance, evidence, then cells (unavailable last)</option><option value="cells">Sort within category: footprint cells (unavailable last)</option><option value="effort">Sort within category: model, then effort share within that model (unavailable last)</option><option value="strength">Sort within category: evidence strength</option><option value="model">Sort within category: model</option><option value="id">Sort within category: ID</option></select>'
               '<label><input type="checkbox" id="f-low"> show reference findings (low importance)</label><button type="button" id="f-clear">Clear</button><button type="button" id="expand-all">Expand evidence</button><button type="button" id="collapse-all">Collapse</button><span class="count" id="f-count"></span></div>')
    for a in rep["areas"]:
        out.append(f'<section class="area" id="area-{a["key"]}"><h3>{_e(a["label"])} <span class="muted">({len(a["ids"])})</span></h3><p>{_e(a["blurb"])}</p>')
        for fid in a["ids"]:
            out.append(_finding(fmap[fid], rep))
        out.append('<p class="empty" hidden>No findings match the current filters in this area.</p></section>')
    out.append("</section>")
    # ---- level 3
    out.append('<section id="reference"><h2>Reference</h2>')
    out.append('<h3 id="register">Findings register</h3><p class="noprint"><button type="button" id="dl-register">Download register (CSV)</button> <button type="button" id="dl-status">Export review statuses (JSON)</button> <span class="muted">Statuses live in this browser\'s localStorage; the export is the only copy you can share.</span></p>')
    out.append('<div class="wrap"><table class="reg"><thead><tr><th data-sort="text">ID</th><th data-sort="text">Area</th><th data-sort="text">Title</th><th data-sort="text">Model</th><th data-sort="text">Kind</th><th data-sort="text">Importance</th><th data-sort="text">Evidence</th><th data-sort="text">Complexity</th><th data-sort="num">Footprint cells (n/a last)</th><th data-sort="num">Effort share of its model (n/a last)</th><th data-sort="text">Benefit</th></tr></thead><tbody>')
    for x in rep["findings"]:
        out.append(f'<tr><td><a href="#{x["id"]}">{x["id"]}</a></td><td>{_e(AREA_LABEL[x["area"]])}</td><td>{_e(x["title"])}</td><td>{_e(x["model"])}</td><td>{x["kind_label"]}</td><td>{x["importance"]}</td><td>{x["strength"]}</td><td>{x["complexity"]}</td>'
                   f'<td data-v="{"" if x["footprint_cells"] is None else x["footprint_cells"]}">{_c(x["footprint_cells"]) if x["footprint_cells"] is not None else "n/a"}</td><td data-v="{"" if x["footprint_effort"] is None else x["footprint_effort"]}">{f"{x['footprint_effort']:.1f}%" if x["footprint_effort"] is not None else "n/a"}</td><td>{x["benefit_kind"]}</td></tr>')
    out.append("</tbody></table></div>")
    # models and coverage
    out.append('<h3 id="models">Models and coverage</h3>')
    for m in rep["models"]:
        f, cov, rc = m["facts"], m["coverage"], m["facts"]["referenced_by_check"]
        rows = [("Files supplied", ", ".join(f"{k}: {v}" for k, v in cov["files"].items() if v) + ("" if cov["files"]["actions"] else "; no Actions export") + ("" if cov["files"]["modules"] else "; no Modules export")),
                ("Export date", "unknown (not in the files)"), ("Latest recorded action run", cov["snapshot_actions"] or "no Actions export"), ("Analysis generated", rep["generated"]),
                ("Engine", "not in any export (Classic or Polaris unknown)"),
                ("Modules / line items / calculated", f"{f['modules']} / {_n_(f['line_items'])} / {_n_(f['calculated'])}"), ("Cells as exported", _n_(f["cells"])),
                ("Formulas parsed", f"{f['parse_rate']:.2%} ({f['parse_errors']} not parsed)"),
                ("Referenced By agreement", f"{rc['agreement'] if rc['agreement'] is not None else 'n/a'}: {rc['definition']} (both {rc['agree']}, parse only {rc['ours_only']}, Anaplan only {rc['anaplan_only']})"),
                ("Anaplan-only edges by cause", ", ".join(f"{k} {v}" for k, v in rc["anaplan_only_by_cause"].items()) or "none"),
                ("Rules run", ", ".join(cov["rules_run"])), ("Rules skipped or limited", "; ".join(f"{r}: {why}" for r, why in cov["rules_skipped"]) or "none"),
                ("Confirmed from metadata", "; ".join(cov["confirmed"])), ("Inferred from names", "; ".join(cov["inferred"]) or "nothing"), ("Missing", "; ".join(cov["missing"])),
                ("Calculated line items with a blank context field", str(cov["unresolved_context"]))]
        out.append(f'<details><summary>{_e(m["name"])}</summary><div class="wrap"><table><tbody>' + "".join(f"<tr><th scope=row>{_e(k)}</th><td>{_e(v)}</td></tr>" for k, v in rows) + "</tbody></table></div>")
        if f["has_effort"]:
            out.append("<h4>Where measured calculation effort sits</h4>" + md_fragment(["| Line item | Effort share | Cells | Formula |", "|---|---|---|---|"] + [f"| `{n}` | {e:.2f}% | {_c(c)} | `{fm}` |" for n, e, c, fm in f["effort_top"]]))
        out.append("<h4>Largest modules by cells</h4>" + md_fragment(["| Module | Cells | Share |", "|---|---|---|"] + [f"| `{n}` | {_c(c)} | {p}% |" for n, c, p in f["cells_by_module"]]))
        out.append("<h4>Most depended-on line items</h4>" + md_fragment(["| Line item | Direct readers |", "|---|---|"] + [f"| `{n}` | {c} |" for n, c in f["hubs"]]))
        if f.get("actions"):
            a = f["actions"]
            out.append("<h4>Actions</h4>" + md_fragment([f"- {a['imports']} imports, {a['exports']} exports, {a['processes']} processes; latest recorded run {a['latest_run'] or 'unknown'}; window {a['stale_months']} months (cutoff {a['stale_cutoff'] or 'n/a'})",
                                                         f"- Not in any process: {a['not_in_process_count']}; no recorded run since cutoff: {len(a['no_recent_run'])}; no recorded run at all: {len(a['never_recorded'])}",
                                                         "- Slowest recorded: " + ", ".join(f"`{n}` {ms / 1000:.0f}s" for n, ms in a["slow"]),
                                                         "- Import targets: " + ", ".join(f"`{t}` ({n})" for t, n in a["imports_by_target"])]))
        pats = m["patterns"]
        out.append(f"<h4>Rule findings grouped into patterns ({len(pats)})</h4>" + md_fragment(["| Severity | Rule | Pattern | Count | Example | Suggested reading |", "|---|---|---|---|---|---|"] +
                   [f"| {c['severity']} | {c['rule']} | {c['label']} | {c['count']} | {(c['objects'][0] if c['objects'] else '')}: {c['message']} | {c['fix']} |" for c in pats]))
        out.append(f"<details><summary>All rule findings for {_e(m['name'])} ({len(m['lint'])})</summary>" + md_fragment(["| Rule | Severity | Object | Finding | Suggested reading |", "|---|---|---|---|---|"] +
                   [f"| {l['rule']} | {l['severity']} | `{l['object']}` | {l['message']} | {l['fix']} |" for l in m["lint"]]) + "</details>")
        red = m["redundancy"]
        if red["same_text"]:
            out.append("<h4>Identical text, context unresolved</h4>" + md_fragment(["| Formula | Why not compared | Line items |", "|---|---|---|"] + [f"| `{e['formula']}` | {e['why']} | {', '.join('`' + i['key'] + '`' for i in e['items'])} |" for e in red["same_text"]]))
        out.append("</details>")
    # dependency evidence
    out.append('<h3 id="dependencies">Dependency evidence</h3><p class="muted">Relationship types inspected: line-item references parsed from every formula (checked against Anaplan\'s Referenced By column); import target modules and export source modules from the Action column; process membership. '
               'Not inspected because not exported: pages, dashboards, saved views, line item subsets (COLLECT sources), filters, access drivers, CloudWorks and API schedules.</p>')
    for m in rep["models"]:
        rc = m["facts"]["referenced_by_check"]
        if rc["agreement"] is None:
            continue
        ex = rc["examples"]
        out.append(f'<details><summary>{_e(m["name"])}: agreement {rc["agreement"]:.0%}; Anaplan-only edges by cause {_e(", ".join(f"{k} {v}" for k, v in rc["anaplan_only_by_cause"].items()) or "none")}</summary>' +
                   md_fragment(["| Cause | Examples (referencing line item -> referenced line item) |", "|---|---|"] + [f"| {k} | {'; '.join('`' + e + '`' for e in v) or 'none'} |" for k, v in ex.items()]) + "</details>")
    if rep["map"]["external"]:
        out.append("<h3>Source-name candidates</h3><p class=\"muted\">Words after \"from\" in import action names that matched no model in the set. Candidates, not confirmed systems; generic words are excluded.</p>" +
                   md_fragment(["| Candidate | Imports | Example |", "|---|---|---|"] + [f"| {k} | {len(v)} | `{v[0]}` |" for k, v in sorted(rep["map"]["external"].items(), key=lambda kv: -len(kv[1]))]))
    if rep["shared_dims"]:
        out.append("<h3>Dimensions shared across models</h3>" + md_fragment(["| Dimension | Models |", "|---|---|"] + [f"| {d} | {', '.join(ms)} |" for d, ms in rep["shared_dims"]]))
    if rep["duplicates"]:
        out.append("<h3>Same name and formula in more than one model</h3>" + md_fragment(["| Line item | Models | Formula |", "|---|---|---|"] + [f"| `{d['line_item']}` | {', '.join(d['models'])} | `{d['formula']}` |" for d in rep["duplicates"]]))
    # methodology
    out.append('<h3 id="methodology">Methodology</h3><p class="muted">Every rule that ran, its source, and the official documentation it rests on (consulted 2026-09-22). Rule results are automated readings of the exports; nothing here was validated in a live Anaplan model.</p>')
    out.append('<div class="wrap"><table><thead><tr><th>Rule</th><th>Severity</th><th>Source</th><th>Description</th><th>Planual</th><th>Documentation</th></tr></thead><tbody>' +
               "".join(f'<tr><td>{r["id"]}<br><span class="muted">{_e(r["title"])}</span></td><td>{r["severity"]}</td><td>{r["source"]}</td><td>{_e(r["description"])}</td><td>{_e("; ".join(r["planual"]))}</td>'
                       f'<td>{"<br>".join(f"<a href={_e(d["url"])}>{_e(d["title"])}</a>: <span class=muted>{_e(d["quote"])}</span>" for d in r["docs"])}</td></tr>' for r in rep["methodology"]) + "</tbody></table></div>")
    out.append("<h4>Evidence strength labels</h4><ul>" + "".join(f"<li><strong>{k}.</strong> {_e(v)}</li>" for k, v in rep["strength_text"].items()) + "</ul>")
    out.append('<h3 id="glossary">Glossary</h3><ul>' + "".join(f"<li><strong>{_e(t)}.</strong> {_e(d)}</li>" for t, d in rep["glossary"]) + "</ul></section>")
    out.append(f'<footer>{_e(rep["description"])} Generated {_e(rep["generated"])}. Review statuses are stored in this browser only.</footer>')
    out.append(f'<script type="application/json" id="report-data">{data}</script><script>{JS}</script></div>')
    return "\n".join(out)


def _n_(x):
    return f"{x:,}" if isinstance(x, int) else str(x)
