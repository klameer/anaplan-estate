"""Self-contained HTML: Action plan | Change impact | Evidence.

Rendered from the report dict (report.build), not from Markdown, so the catalogue
search, filters, review statuses, notes, the working register and the change-impact
explorer work on structured data. No external requests: fonts and tokens are
embedded when a theme stylesheet is supplied, links are same-document fragments
or the configured http(s) links, the findings and graph JSON are embedded for the
page's own script. Navigation fragments carry internal identifiers only (finding
ids, node numbers), never model contents.

Without JavaScript the three views are shown one after another, every finding is
readable inside a <details>, and the explorer says what it needs.

Review statuses and notes are the reader's, not the analysis's. They live in the
browser's localStorage under a key derived from the report title and generation
date, keyed by each finding's stable uid, and can be downloaded as a working
register. Nothing is stored anywhere else; a blocked localStorage disables only
the remembering, not the analysis or the downloads.
"""
from __future__ import annotations
import html, json, re
from .findings import AREA_LABEL, _c

CSS = r"""
:root{--bg:#F7F8F6;--ink:#1B2430;--muted:#5C6773;--rule:#D9DED9;--soft:#EEF1EE;--accent:#0E5E6F;--card:#FFFFFF;
--high:#A6301C;--med:#B7791F;--low:#4B6B5C;--conf:#0E5E6F;--part:#7A5F1F;--inf:#6B5A7A;--notice:#FFF7E6;
--sans:"Geist Sans","IBM Plex Sans","Helvetica Neue",Arial,sans-serif;--mono:"Geist Mono","IBM Plex Mono",Consolas,monospace}
@media (prefers-color-scheme:dark){:root:not([data-theme="light"]){--bg:#0F1416;--ink:#E6EBE8;--muted:#9AA6A0;--rule:#2E393C;--soft:#1B2427;--accent:#5FB3C1;--card:#161D20;
--high:#E07A63;--med:#D9A441;--low:#8FB8A6;--conf:#5FB3C1;--part:#D9A441;--inf:#B39DDB;--notice:#2A2416}}
:root[data-theme="dark"]{--bg:#0F1416;--ink:#E6EBE8;--muted:#9AA6A0;--rule:#2E393C;--soft:#1B2427;--accent:#5FB3C1;--card:#161D20;--high:#E07A63;--med:#D9A441;--low:#8FB8A6;--conf:#5FB3C1;--part:#D9A441;--inf:#B39DDB;--notice:#2A2416}
*{box-sizing:border-box}html{scroll-behavior:smooth}
body{background:var(--bg);color:var(--ink);font-family:var(--sans);font-size:15px;line-height:1.5;margin:0}
.page{max-width:1040px;margin:0 auto;padding:28px 24px 60px}
a{color:var(--accent)}a:focus-visible,button:focus-visible,input:focus-visible,select:focus-visible,summary:focus-visible,textarea:focus-visible,[tabindex]:focus-visible{outline:2px solid var(--accent);outline-offset:2px}
header.top{border-bottom:1px solid var(--rule);padding-bottom:12px;margin-bottom:14px}
header.top h1{font-size:28px;line-height:1.15;margin:0 0 4px;letter-spacing:-.01em;font-weight:600}
header.top .attrib{display:flex;align-items:center;gap:8px;font-size:12px;color:var(--muted);margin:0 0 6px}
header.top .attrib svg,header.top .attrib img{height:18px;width:auto}
header.top .lead{color:var(--muted);font-size:13.5px;margin:0}
nav.views{position:sticky;top:0;background:var(--bg);z-index:5;border-bottom:1px solid var(--rule);padding:6px 0;margin-bottom:16px;display:flex;gap:6px;flex-wrap:wrap;align-items:center}
nav.views [role=tab]{font:inherit;font-size:14px;padding:6px 12px;border:1px solid var(--rule);border-radius:999px;background:var(--card);color:var(--ink);cursor:pointer}
nav.views [role=tab][aria-selected=true]{background:var(--accent);color:#fff;border-color:var(--accent)}
nav.views .right{margin-left:auto;display:flex;gap:6px;flex-wrap:wrap}
button.btn{white-space:nowrap;font:inherit;font-size:13px;padding:5px 10px;border:1px solid var(--rule);border-radius:6px;background:var(--card);color:var(--ink);cursor:pointer}
button.btn.primary{border-color:var(--accent);color:var(--accent)}
h2{font-size:20px;font-weight:600;margin:26px 0 8px;letter-spacing:-.01em}
h3{font-size:16px;font-weight:600;margin:20px 0 6px}
h4{font-size:14px;font-weight:600;margin:12px 0 4px}
p{max-width:78ch;margin:6px 0}
.muted{color:var(--muted)}.fnote{font-size:12.5px;color:var(--muted)}
.view{margin-bottom:24px}
ol.actions{list-style:none;padding:0;margin:0}
li.action{background:var(--card);border:1px solid var(--rule);border-left:4px solid var(--accent);border-radius:8px;padding:12px 16px;margin:10px 0}
li.action h2{margin:0 0 4px;font-size:17px}li.action h2 .n{color:var(--muted)}
li.action .role{margin:0 0 8px}li.action .model{display:inline-block;background:var(--accent);color:#fff;font-size:12.5px;font-weight:600;padding:2px 9px;border-radius:999px}
li.action dl{margin:0}li.action dt{font-weight:600;font-size:12.5px;text-transform:uppercase;letter-spacing:.05em;color:var(--muted);margin-top:8px}li.action dd{margin:2px 0 0}
li.action ol{margin:2px 0 0;padding-left:20px}li.action ol li{margin:2px 0}
li.action .notice{background:var(--notice);border-radius:6px;padding:6px 10px;font-size:13px;margin:8px 0 0}
li.action table.det{font-size:12.5px}li.action table.det code{font-size:11.5px;white-space:pre-wrap}li.action .wrap{margin:4px 0}
li.action.below{border-left-color:var(--rule);opacity:.92}li.action .notice.below{background:var(--soft)}h3.group-h{margin-top:22px;font-size:17px}
.banner{background:var(--notice);border:1px solid var(--rule);border-radius:8px;padding:8px 12px;font-size:13px;margin:0 0 12px}.banner ul{margin:4px 0 0;padding-left:18px}
.summary{margin:4px 0 14px}table.sum{font-size:14px}table.sum td,table.sum th{padding:5px 8px}table.sum tr.tot td{font-weight:600;border-top:2px solid var(--rule)}
li.action .links{font-size:12.5px;margin:8px 0 0}li.action .links a{margin-right:10px}
.badge{display:inline-block;font-family:var(--mono);font-size:10.5px;letter-spacing:.06em;text-transform:uppercase;padding:2px 7px;border-radius:999px;border:1px solid var(--rule);color:var(--muted);margin-right:4px;white-space:nowrap}
.badge.imp-high{border-color:var(--high);color:var(--high)}.badge.imp-medium{border-color:var(--med);color:var(--med)}.badge.imp-low{border-color:var(--low);color:var(--low)}
.badge.st-confirmed{border-color:var(--conf);color:var(--conf)}.badge.st-partial{border-color:var(--part);color:var(--part)}.badge.st-inferred{border-color:var(--inf);color:var(--inf)}
.map{margin:12px 0;overflow-x:auto}.map svg{max-width:100%;height:auto;font-family:var(--sans)}
.controls{display:flex;flex-wrap:wrap;gap:8px;align-items:center;background:var(--soft);padding:10px;border-radius:8px;margin:10px 0 12px}
.controls input,.controls select,.controls button,.controls textarea{font:inherit;font-size:13px;padding:5px 8px;border:1px solid var(--rule);border-radius:6px;background:var(--card);color:var(--ink)}
.controls input[type=search],.controls input[type=text]{min-width:200px;flex:1}.controls .count{font-size:12.5px;color:var(--muted);margin-left:auto}
.wrap{overflow-x:auto;max-width:100%;border:1px solid var(--rule);border-radius:6px}
table{border-collapse:collapse;width:100%;font-size:13px}th,td{text-align:left;vertical-align:top;padding:6px 8px;border-bottom:1px solid var(--rule)}
th{font-size:11.5px;text-transform:uppercase;letter-spacing:.06em;color:var(--muted);background:var(--soft)}
td{word-break:break-word}td code{white-space:pre-wrap}
table.cat tr[data-id]{cursor:pointer}table.cat tr[data-id]:hover td{background:var(--soft)}table.cat tr.sel td{background:var(--soft);border-left:3px solid var(--accent)}
table.cat td.t{min-width:220px}table.cat select{font:inherit;font-size:12px;padding:2px 4px;border:1px solid var(--rule);border-radius:4px;background:var(--bg);color:var(--ink)}
code{font-family:var(--mono);font-size:12px;background:var(--soft);padding:1px 4px;border-radius:3px}
.formula{display:flex;gap:6px;align-items:flex-start}.formula button{font-size:11px;padding:1px 6px;border:1px solid var(--rule);border-radius:4px;background:var(--bg);color:var(--muted);cursor:pointer}
article.f{background:var(--card);border:1px solid var(--rule);border-radius:8px;padding:12px 16px;margin:10px 0}
article.f header{display:flex;flex-wrap:wrap;gap:8px;align-items:baseline}article.f header h3{margin:0;font-size:15.5px;flex:1 1 320px}
article.f .objs{font-family:var(--mono);font-size:12px;color:var(--muted);word-break:break-word;margin:6px 0 8px}article.f .objs code{background:none;padding:0}
article.f .review{display:flex;flex-wrap:wrap;gap:8px;align-items:flex-start;margin:8px 0;font-size:13px}
article.f .review select,article.f .review textarea{font:inherit;font-size:12.5px;border:1px solid var(--rule);border-radius:6px;background:var(--bg);color:var(--ink);padding:4px 6px}
article.f .review textarea{flex:1 1 260px;min-height:34px}
dl.fields{display:grid;grid-template-columns:max-content 1fr;gap:4px 14px;margin:8px 0;font-size:14px}
dl.fields dt{color:var(--muted);font-size:12px;text-transform:uppercase;letter-spacing:.06em;padding-top:3px}dl.fields dd{margin:0;max-width:80ch}dl.fields ul{margin:0;padding-left:18px}
details{margin:8px 0}summary{cursor:pointer;font-weight:600;font-size:13.5px}details.ev>div{margin-top:8px}
.idx{display:none}.hit{font-size:12px;color:var(--accent);margin:4px 0}.sr{position:absolute;left:-9999px}
#cat-detail:empty{display:none}#cat-detail{margin:12px 0}
.subnav{display:flex;flex-wrap:wrap;gap:4px 14px;font-size:13px;margin:0 0 10px}
footer{margin-top:36px;border-top:1px solid var(--rule);padding-top:12px;font-size:12.5px;color:var(--muted)}footer p{margin:4px 0}
/* explorer */
.ix-grid{display:grid;grid-template-columns:1fr;gap:12px}
#ix-results{list-style:none;padding:0;margin:4px 0;max-height:220px;overflow:auto;border:1px solid var(--rule);border-radius:6px;background:var(--card)}
#ix-results li{padding:4px 8px;font-size:13px;cursor:pointer;border-bottom:1px solid var(--rule)}#ix-results li:hover,#ix-results li:focus{background:var(--soft)}
#ix-results:empty{display:none}
.ix-summary{background:var(--card);border:1px solid var(--rule);border-radius:8px;padding:10px 14px;font-size:13.5px}
.ix-summary .big{font-size:20px;font-weight:600;margin-right:4px}.ix-summary .stats{display:flex;flex-wrap:wrap;gap:6px 18px;margin:4px 0 8px}
.ix-cols{display:flex;gap:10px;overflow-x:auto;padding:6px 0}
.ix-col{flex:0 0 240px;background:var(--soft);border-radius:8px;padding:8px}
.ix-col h4{margin:0 0 6px;font-size:12px;text-transform:uppercase;letter-spacing:.06em;color:var(--muted)}
.ix-mod{background:var(--card);border:1px solid var(--rule);border-radius:6px;padding:6px 8px;margin:4px 0;font-size:12.5px}
.ix-mod summary{font-weight:600;font-size:12.5px}.ix-mod ul{margin:4px 0 0;padding-left:16px;font-family:var(--mono);font-size:11.5px}
.ix-mod ul li a{cursor:pointer}.ix-mod .n{color:var(--muted);font-weight:400}
.ix-start{background:var(--card);border:2px solid var(--accent);border-radius:6px;padding:6px 8px;font-size:12.5px;font-family:var(--mono)}
.legend{font-size:12px;color:var(--muted);display:flex;flex-wrap:wrap;gap:6px 16px;margin:6px 0}
.legend .k{display:inline-block;width:22px;border-top:2px solid var(--accent);vertical-align:middle;margin-right:4px}.legend .k.dash{border-top-style:dashed}.legend .k.dot{border-top-style:dotted}
.path{font-family:var(--mono);font-size:12px;background:var(--soft);padding:6px 8px;border-radius:6px;margin:6px 0;word-break:break-word}
.ixd-wrap{overflow-x:auto;background:var(--card);border:1px solid var(--rule);border-radius:8px;padding:6px}svg.ixd{display:block;min-width:600px;max-width:100%;height:auto;font-family:var(--sans)}
svg.ixd rect.ixd-n{fill:var(--soft);stroke:var(--rule)}svg.ixd rect.ixd-sel{fill:var(--accent);stroke:var(--accent)}svg.ixd a:hover rect.ixd-n{stroke:var(--accent)}
svg.ixd rect.ixd-more{fill:none;stroke:var(--rule);stroke-dasharray:3 3}svg.ixd text{fill:var(--ink)}svg.ixd rect.ixd-sel+text{fill:#fff}
@media (max-width:640px){dl.fields{grid-template-columns:1fr}nav.views{position:static}.ix-col{flex-basis:200px}}
@media print{
 :root{--bg:#fff;--ink:#111;--muted:#444;--rule:#bbb;--soft:#f2f2f2;--accent:#0E5E6F;--card:#fff;--notice:#f7f2e6}
 @page{size:A4;margin:12mm 14mm}
 body{background:#fff;color:#111;font-size:10.5pt;line-height:1.3}.page{max-width:none;padding:0}p{margin:3px 0}
 nav.views,.controls,.noprint,.review,.hit,#ix-results,footer .links-help,body:not(.print-full) footer{display:none!important}
 header.top{margin-bottom:6px;padding-bottom:4px}header.top h1{font-size:17pt;margin:0}header.top .attrib,header.top .lead{font-size:9.5pt;margin:2px 0}
 li.action{padding:5px 9px;margin:5px 0;page-break-inside:avoid;border:1px solid #bbb;border-left:3px solid #0E5E6F}li.action h2{font-size:12pt;margin:0 0 2px}li.action .role{margin:0 0 3px}li.action .model{font-size:9pt;background:#0E5E6F;color:#fff}
 li.action dt{margin-top:3px;font-size:8.5pt}li.action dd,li.action ol li,li.action .notice,li.action .links{font-size:10pt}li.action .notice{padding:3px 8px;margin:4px 0 0}li.action .links{margin:4px 0 0}li.action ol li{margin:1px 0}
 #plan>.fnote{font-size:9pt;margin:4px 0}footer{margin-top:10px;padding-top:6px;font-size:9pt}
 body:not(.print-full) #impact,body:not(.print-full) #evidence{display:none!important}
 body.print-full .view{display:block!important}#plan{display:block!important}
 body.print-full #cat-articles{display:block!important}body.print-full #cat-detail{display:none}
 body.print-full details.ev:not([open]){display:block}body.print-full details.ev:not([open])>div{display:none}
 thead{display:table-header-group}.wrap{overflow:visible;border:none}table{font-size:9pt}td code{white-space:pre-wrap;word-break:break-all}
 a{color:#111;text-decoration:none}
}
"""

JS = r"""
(function(){
 var D=JSON.parse(document.getElementById('report-data').textContent);
 var $=function(s,r){return (r||document).querySelector(s)},$$=function(s,r){return Array.prototype.slice.call((r||document).querySelectorAll(s))};
 document.documentElement.classList.add('js');
 function esc(s){return String(s).replace(/[&<>"']/g,function(c){return {'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]})}
 function fmt(n){if(n===null||n===undefined)return 'n/a';if(Math.abs(n)>=1e9)return (n/1e9).toFixed(n/1e9>=100?0:1)+'B';if(Math.abs(n)>=1e6)return (n/1e6).toFixed(n/1e6>=100?0:1)+'M';if(Math.abs(n)>=1e3)return (n/1e3).toFixed(n/1e3>=100?0:1)+'K';return String(n)}
 /* ---- local review state (statuses + notes), keyed by stable uid ---- */
 var key='anaplan-estate-review:'+D.key, storeOk=true;
 function load(){try{return JSON.parse(localStorage.getItem(key)||'{}')}catch(e){storeOk=false;return {}}}
 function save(o){try{localStorage.setItem(key,JSON.stringify(o))}catch(e){storeOk=false}}
 var st=load();
 if(!storeOk){$$('.store-note').forEach(function(e){e.textContent='This browser is not allowing local storage: statuses and notes will not be remembered after you leave, but you can still download the working register.'})}
 /* ---- views ---- */
 var VIEWS=['plan','impact','evidence'];
 function show(v){if(VIEWS.indexOf(v)<0)v='plan';VIEWS.forEach(function(x){var s=document.getElementById(x);if(s)s.hidden=(x!==v);var b=$('[role=tab][data-view='+x+']');if(b){b.setAttribute('aria-selected',x===v?'true':'false');b.tabIndex=(x===v?0:-1)}});}
 $$('[role=tab]').forEach(function(b,i,all){b.addEventListener('click',function(){location.hash='#'+b.dataset.view});
   b.addEventListener('keydown',function(e){var j=(e.key==='ArrowRight')?(i+1)%all.length:(e.key==='ArrowLeft')?(i-1+all.length)%all.length:-1;if(j>=0){all[j].focus();all[j].click();e.preventDefault()}})});
 /* ---- catalogue ---- */
 var arts={},rows={};$$('article.f').forEach(function(a){arts[a.dataset.id]=a});$$('table.cat tr[data-id]').forEach(function(r){rows[r.dataset.id]=r});
 var artBox=$('#cat-articles'),detail=$('#cat-detail');if(artBox)artBox.hidden=true;
 var q=$('#q'),fm=$('#f-model'),fa=$('#f-area'),fs=$('#f-strength'),fst=$('#f-status'),fl=$('#f-low'),so=$('#f-sort'),cnt=$('#f-count'),fmsg=$('#f-msg');
 var IMP={high:0,medium:1,low:2},STR={confirmed:0,partial:1,inferred:2};
 function statusOf(id){var a=arts[id];var r=st[a.dataset.uid];return (r&&r.status)||'To review'}
 function apply(){
   var t=(q.value||'').toLowerCase().trim(),n=0,total=0;
   Object.keys(rows).forEach(function(id){var r=rows[id],a=arts[id];total++;var ok=true;var hit=$('.hit',a);if(hit){hit.hidden=true;hit.textContent=''}
     if(t){var head=(a.dataset.search||'').indexOf(t)>=0;var idx=$('.idx',a);var body=idx?idx.textContent.toLowerCase():'';var pos=body.indexOf(t);ok=head||pos>=0;
       if(ok&&!head&&hit){var line=body.slice(Math.max(0,body.lastIndexOf('\n',pos)+1),body.indexOf('\n',pos)>0?body.indexOf('\n',pos):body.length);
         hit.textContent='Matched in '+(line.indexOf('formula:')===0?'a formula':line.indexOf('object:')===0?'an affected object':'the evidence')+': '+line.replace(/^(formula|object|evidence|text):\s*/,'').slice(0,140);hit.hidden=false}}
     if(ok&&fm.value&&a.dataset.model!==fm.value)ok=false;
     if(ok&&fa.value&&a.dataset.area!==fa.value)ok=false;
     if(ok&&fs.value&&a.dataset.strength!==fs.value)ok=false;
     if(ok&&fst.value&&statusOf(id)!==fst.value)ok=false;
     if(ok&&!fl.checked&&!t&&a.dataset.importance==='low')ok=false;
     r.hidden=!ok;if(ok)n++;});
   var s=so.value,tb=$('table.cat tbody');var list=Object.keys(rows).map(function(id){return rows[id]});
   function num(v){return v===''?null:parseFloat(v)}function dnl(a,b){if(a===null&&b===null)return 0;if(a===null)return 1;if(b===null)return -1;return b-a}
   list.sort(function(x,y){var a=arts[x.dataset.id],b=arts[y.dataset.id];
     if(s==='cells')return dnl(num(a.dataset.cells),num(b.dataset.cells))||(IMP[a.dataset.importance]-IMP[b.dataset.importance]);
     if(s==='model')return a.dataset.model.localeCompare(b.dataset.model)||(IMP[a.dataset.importance]-IMP[b.dataset.importance]);
     if(s==='strength')return (STR[a.dataset.strength]-STR[b.dataset.strength])||(IMP[a.dataset.importance]-IMP[b.dataset.importance]);
     if(s==='id')return parseInt(x.dataset.id.slice(1))-parseInt(y.dataset.id.slice(1));
     return (IMP[a.dataset.importance]-IMP[b.dataset.importance])||(STR[a.dataset.strength]-STR[b.dataset.strength])||dnl(num(a.dataset.cells),num(b.dataset.cells))});
   list.forEach(function(r){tb.appendChild(r)});
   cnt.textContent=n+' of '+total+' findings listed'+((!fl.checked&&!t)?' (low-importance findings hidden)':'')+(t?' for "'+t+'" (search covers every object, evidence row and formula)':'');
 }
 [q,fm,fa,fs,fst,so,fl].forEach(function(el){el.addEventListener('input',apply);el.addEventListener('change',apply)});
 $('#f-clear').addEventListener('click',function(){q.value='';fm.value='';fa.value='';fs.value='';fst.value='';so.value='importance';fl.checked=false;fmsg.textContent='';apply();q.focus()});
 var selected=null;
 function openFinding(id,focus){var a=arts[id];if(!a)return false;
   var cleared=[];if(rows[id]){apply();if(rows[id].hidden){if(q.value){q.value='';cleared.push('search')}if(fm.value&&fm.value!==a.dataset.model){fm.value='';cleared.push('model')}if(fa.value&&fa.value!==a.dataset.area){fa.value='';cleared.push('category')}
     if(fs.value&&fs.value!==a.dataset.strength){fs.value='';cleared.push('evidence')}if(fst.value&&fst.value!==statusOf(id)){fst.value='';cleared.push('status')}if(!fl.checked&&a.dataset.importance==='low'){fl.checked=true;cleared.push('low-importance')}apply()}}
   fmsg.textContent=cleared.length?('Filters on '+cleared.join(', ')+' were cleared to show '+id+'.'):'';
   if(selected&&rows[selected])rows[selected].classList.remove('sel');selected=id;if(rows[id])rows[id].classList.add('sel');
   detail.innerHTML='';detail.appendChild(a);a.hidden=false;$$('details.full',a).forEach(function(d){d.open=true});
   if(focus!==false){a.setAttribute('tabindex','-1');a.focus({preventScroll:true});a.scrollIntoView({block:'start'})}
   return true}
 $$('table.cat tr[data-id]').forEach(function(r){r.addEventListener('click',function(e){if(e.target.closest('select,a,button'))return;location.hash='#'+r.dataset.id});
   r.addEventListener('keydown',function(e){if(e.key==='Enter'||e.key===' '){e.preventDefault();location.hash='#'+r.dataset.id}})});
 /* status + note per finding */
 Object.keys(arts).forEach(function(id){var a=arts[id],uid=a.dataset.uid,rec=st[uid]||{};var sel=$('select.stsel',a),note=$('textarea.note',a),rsel=rows[id]&&$('select.stsel',rows[id]);
   if(rec.status){if(sel)sel.value=rec.status;if(rsel)rsel.value=rec.status}if(note&&rec.note)note.value=rec.note;
   function setStatus(v){st[uid]=st[uid]||{};st[uid].status=v;if(sel)sel.value=v;if(rsel)rsel.value=v;save(st);apply()}
   if(sel)sel.addEventListener('change',function(){setStatus(sel.value)});if(rsel)rsel.addEventListener('change',function(){setStatus(rsel.value)});
   if(note)note.addEventListener('input',function(){st[uid]=st[uid]||{};st[uid].note=note.value;save(st)})});
 /* downloads */
 function dl(name,text,type){var a=document.createElement('a');a.href='data:'+type+';charset=utf-8,'+encodeURIComponent(text);a.download=name;document.body.appendChild(a);a.click();a.remove()}
 function csvq(v){v=(v===null||v===undefined)?'':String(v);return /[",\n\r]/.test(v)?'"'+v.replace(/"/g,'""')+'"':v}
 $('#dl-register').addEventListener('click',function(){dl('findings-register.csv',D.csv,'text/csv')});
 $('#dl-working').addEventListener('click',function(){var cols=D.register_cols.concat(['review_status','review_note']);var out=[cols.join(',')];
   D.register.forEach(function(r){var rec=st[r.uid]||{};out.push(cols.map(function(c){return csvq(c==='review_status'?(rec.status||'To review'):c==='review_note'?(rec.note||''):r[c])}).join(','))});
   dl('working-register.csv',out.join('\n'),'text/csv')});
 $('#dl-status').addEventListener('click',function(){dl('review-state.json',JSON.stringify({report:D.key,exported:new Date().toISOString(),review:st},null,1),'application/json')});
 $$('.copy').forEach(function(b){b.addEventListener('click',function(){var t=b.previousElementSibling.textContent;if(navigator.clipboard){navigator.clipboard.writeText(t).then(function(){b.textContent='copied';setTimeout(function(){b.textContent='copy'},1200)})}})});
 /* print */
 function printAs(cls){document.body.classList.add(cls);if(cls==='print-full'){$$('#evidence details').forEach(function(d){d.open=true})}window.print();setTimeout(function(){document.body.classList.remove(cls)},800)}
 $('#print-plan').addEventListener('click',function(){printAs('print-plan')});$('#print-full').addEventListener('click',function(){printAs('print-full')});
 if(/[?&]print=full/.test(location.search))document.body.classList.add('print-full');
 /* ---- Change impact explorer ---- */
 var G=D.graph,N=G.nodes,NI={};N.forEach(function(n){NI[n[0]]=n});
 var down=null,up=null;
 function adj(dir){if(dir==='downstream'){if(!down){down={};G.edges.forEach(function(e){(down[e[1]]=down[e[1]]||[]).push(e[0])})}return down}if(!up){up={};G.edges.forEach(function(e){(up[e[0]]=up[e[0]]||[]).push(e[1])})}return up}
 function reach(starts,dir,depth){var A=adj(dir),dist={},par={},qq=[],h=0;starts.forEach(function(s){dist[s]=0;qq.push(s)});
   while(h<qq.length){var n=qq[h++],d=dist[n];if(depth!==null&&d>=depth)continue;var xs=A[n]||[];for(var i=0;i<xs.length;i++){var x=xs[i];if(!(x in dist)){dist[x]=d+1;par[x]=n;qq.push(x)}}}
   starts.forEach(function(s){delete dist[s]});return {dist:dist,par:par}}
 function pathTo(par,starts,x){var out=[x];var S={};starts.forEach(function(s){S[s]=1});while(!(out[out.length-1] in S)&&(out[out.length-1] in par))out.push(par[out[out.length-1]]);return out.reverse()}
 var ixq=$('#ix-q'),ixm=$('#ix-model'),ixr=$('#ix-results'),ixdir=$$('input[name=ix-dir]'),ixdepth=$('#ix-depth'),ixsum=$('#ix-summary'),ixg=$('#ix-graph'),ixt=$('#ix-table'),ixp=$('#ix-path'),ixdl=$('#ix-download');
 var cur=null; /* {kind:'item'|'module', ids:[...], mi, module, name} */
 function label(n){return n[2]+'.'+n[3]}
 function search(){var t=(ixq.value||'').toLowerCase().trim(),mi=ixm.value===''?null:parseInt(ixm.value);ixr.innerHTML='';if(t.length<2)return;
   var mods={},out=[];for(var i=0;i<N.length&&out.length<40;i++){var n=N[i];if(mi!==null&&n[1]!==mi)continue;var l=label(n).toLowerCase();
     if(n[2].toLowerCase().indexOf(t)>=0&&!mods[n[1]+'|'+n[2]]){mods[n[1]+'|'+n[2]]=1;out.push({kind:'module',mi:n[1],module:n[2]})}
     if(l.indexOf(t)>=0)out.push({kind:'item',id:n[0]})}
   out.slice(0,40).forEach(function(o){var li=document.createElement('li');li.tabIndex=0;
     if(o.kind==='module'){li.innerHTML='<span class="badge">module</span> '+esc(o.module)+' <span class="muted">'+esc(G.models[o.mi])+'</span>';li.addEventListener('click',function(){location.hash='#impact=m'+o.mi+':'+encodeURIComponent(o.module)})}
     else{var n=NI[o.id];li.innerHTML='<span class="badge">line item</span> '+esc(label(n))+' <span class="muted">'+esc(G.models[n[1]])+'</span>';li.addEventListener('click',function(){location.hash='#impact='+o.id})}
     li.addEventListener('keydown',function(e){if(e.key==='Enter')li.click()});ixr.appendChild(li)})}
 ixq.addEventListener('input',search);ixm.addEventListener('change',search);
 ixdir.forEach(function(r){r.addEventListener('change',render)});ixdepth.addEventListener('change',render);
 function dirNow(){var r=ixdir.filter(function(x){return x.checked})[0];return r?r.value:'downstream'}
 function selectItem(id){var n=NI[id];if(!n)return false;cur={kind:'item',ids:[id],mi:n[1],module:n[2],name:n[3]};ixq.value=label(n);ixr.innerHTML='';render();return true}
 function selectModule(mi,module){var ids=N.filter(function(n){return n[1]===mi&&n[2]===module}).map(function(n){return n[0]});if(!ids.length)return false;cur={kind:'module',ids:ids,mi:mi,module:module,name:null};ixq.value=module;ixr.innerHTML='';render();return true}
 function actionsFor(mi,modset){var acts=G.actions[mi];if(acts===null||acts===undefined)return null;return acts.filter(function(a){return a.module&&modset[a.module]})}
 function diagram(){var D=Math.min(parseInt(ixdepth.value)||2,3);var up=reach(cur.ids,'upstream',D),dn=reach(cur.ids,'downstream',D);
   var CAP=14,ROW=22,COLW=230,GAP=40,cols=[];
   function side(r,sign){for(var d=1;d<=D;d++){var ids=Object.keys(r.dist).filter(function(i){return r.dist[i]===d}).map(Number).sort(function(a,b){return NI[a][2].localeCompare(NI[b][2])||NI[a][3].localeCompare(NI[b][3])});
     if(!ids.length)break;var shown=ids.slice(0,ids.length>CAP?CAP-1:CAP),extra=ids.length-shown.length;cols.push({sign:sign,d:d,ids:shown,extra:extra,all:ids,par:r.par})}}
   side(up,-1);side(dn,1);
   var left=cols.filter(function(c){return c.sign<0}).sort(function(a,b){return b.d-a.d}),right=cols.filter(function(c){return c.sign>0}).sort(function(a,b){return a.d-b.d});
   var order=left.concat([{sign:0,d:0,ids:cur.ids.slice(0,1),extra:0,centre:true}]).concat(right);
   var rows=Math.max.apply(null,order.map(function(c){return c.ids.length+(c.extra?1:0)}).concat([1]));
   var H=rows*ROW+60,W=order.length*(COLW+GAP)+20,pos={};
   order.forEach(function(c,ci){var n=c.ids.length+(c.extra?1:0),y0=30+(rows-n)*ROW/2;c.x=10+ci*(COLW+GAP);c.ids.forEach(function(i,k){pos[i]=[c.x,y0+k*ROW]});c.extraY=y0+c.ids.length*ROW;c.y0=y0});
   var svg=['<svg class="ixd" viewBox="0 0 '+W+' '+H+'" role="img" aria-label="Dependency diagram">'];
   svg.push('<defs><marker id="ixarr" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="6" markerHeight="6" orient="auto"><path d="M0,0 L10,5 L0,10 z" fill="currentColor" opacity=".6"/></marker></defs>');
   order.forEach(function(c){var lbl=c.centre?'selected':(c.sign<0?'depends on, distance '+c.d:'depended on by, distance '+c.d);svg.push('<text x="'+(c.x+COLW/2)+'" y="16" font-size="10.5" text-anchor="middle" fill="currentColor" opacity=".7">'+esc(lbl)+'</text>')});
   function anchor(i,sideRight){var p=pos[i];if(!p)return null;return [p[0]+(sideRight?COLW:0),p[1]+ROW/2-2]}
   function col(i){return order.filter(function(c){return c.ids.indexOf(i)>=0})[0]}
   cols.forEach(function(c){var pool=c.ids.concat(c.extra?['x'+c.sign+c.d]:[]);
     c.all.forEach(function(i){var p=c.par[i];var from=(c.ids.indexOf(i)>=0)?i:('x'+c.sign+c.d);var to=(p in pos)?p:(c.centre?null:null);
       var pc=cols.filter(function(cc){return cc.sign===c.sign&&cc.d===c.d-1})[0];if(c.d===1)to=cur.ids[0];else if(pc){to=(pc.ids.indexOf(p)>=0)?p:('x'+pc.sign+pc.d)}
       if(to===null||to===undefined)return;var key=from+'>'+to;if(c._seen&&c._seen[key])return;c._seen=c._seen||{};c._seen[key]=1;
       var A=(typeof from==='string')?[c.x+(c.sign<0?COLW:0),c.extraY+ROW/2-2]:anchor(from,c.sign<0);
       var B;if(typeof to==='string'){var tc=cols.filter(function(cc){return 'x'+cc.sign+cc.d===to})[0];B=[tc.x+(c.sign<0?0:COLW),tc.extraY+ROW/2-2]}else{B=anchor(to,c.sign>0)}
       if(!A||!B)return;var a=c.sign<0?A:B,b=c.sign<0?B:A;  /* arrows point in the direction data flows: source -> reader */
       svg.push('<path d="M'+a[0]+','+a[1]+' C'+(a[0]+GAP/2)+','+a[1]+' '+(b[0]-GAP/2)+','+b[1]+' '+b[0]+','+b[1]+'" fill="none" stroke="currentColor" stroke-width="1" opacity=".45" marker-end="url(#ixarr)"/>')})});
   function node(x,y,text,title,cls,href){var t=text.length>34?text.slice(0,33)+'…':text;return '<a href="'+href+'"><rect x="'+x+'" y="'+y+'" width="'+COLW+'" height="'+(ROW-4)+'" rx="4" class="'+cls+'"/><text x="'+(x+6)+'" y="'+(y+13)+'" font-size="11" font-family="var(--mono)">'+esc(t)+'<title>'+esc(title)+'</title></text></a>'}
   order.forEach(function(c){c.ids.forEach(function(i){var n=NI[i],p=pos[i];svg.push(node(p[0],p[1],c.centre?(cur.kind==='item'?n[3]:cur.module):n[3],label(n)+' ('+G.models[n[1]]+')',c.centre?'ixd-sel':'ixd-n','#impact='+(c.centre&&cur.kind==='module'?'m'+cur.mi+':'+encodeURIComponent(cur.module):i)))});
     if(c.extra)svg.push('<rect x="'+c.x+'" y="'+c.extraY+'" width="'+COLW+'" height="'+(ROW-4)+'" rx="4" class="ixd-more"/><text x="'+(c.x+6)+'" y="'+(c.extraY+13)+'" font-size="11" fill="currentColor">+'+c.extra+' more (see table)</text>')});
   svg.push('</svg>');
   var note='<p class="fnote">Diagram: what the selection depends on to the left, what depends on it to the right, up to distance '+D+' each way'+(cols.some(function(c){return c.extra})?'; long columns are cut at '+CAP+' with the rest in the table':'')+'. Arrows follow the data: from a source to the line item that reads it. Click a box to re-centre. Line items only; actions and model feeds are listed above.</p>';
   return '<h3>Diagram</h3>'+note+'<div class="ixd-wrap">'+svg.join('')+'</div>'}
 function render(){if(!cur)return;var dir=dirNow(),dv=ixdepth.value,depth=dv==='all'?null:parseInt(dv);
   var full=reach(cur.ids,dir,null),shown=depth===null?full:reach(cur.ids,dir,depth);
   var ids=Object.keys(full.dist).map(Number);var direct=0,indirect=0,cells=0,maxd=0,byd={};
   ids.forEach(function(i){var d=full.dist[i];if(d===1)direct++;else indirect++;cells+=NI[i][4];if(d>maxd)maxd=d;byd[d]=(byd[d]||0)+1});
   var reachedMods={};ids.forEach(function(i){reachedMods[NI[i][2]]=1});
   var modset={};Object.keys(reachedMods).forEach(function(k){modset[k]=1});modset[cur.module]=1;
   var acts=actionsFor(cur.mi,modset);
   var cov=G.coverage[cur.mi],model=G.models[cur.mi];
   var feeds=G.feeds.filter(function(f){return dir==='downstream'?f.from===model:f.to===model});
   var what=cur.kind==='item'?('<code>'+esc(cur.module+'.'+cur.name)+'</code>'):('module <code>'+esc(cur.module)+'</code> ('+cur.ids.length+' line items, all as sources)');
   var h='<p><strong>'+(dir==='downstream'?'What depends on this':'What this depends on')+'</strong>: '+what+' in '+esc(model)+'.</p>';
   h+='<div class="stats"><span><span class="big">'+ids.length+'</span>unique line item'+(ids.length===1?'':'s')+' ('+direct+' direct, '+indirect+' indirect)</span><span><span class="big">'+Object.keys(reachedMods).length+'</span>module'+(Object.keys(reachedMods).length===1?'':'s')+'</span><span><span class="big">'+maxd+'</span>max distance</span></div>';
   h+='<p class="fnote">Distance = shortest number of known formula-reference links from the selection (direct = 1); each line item counted once; the selection is excluded even where a cycle returns to it. Distribution: '+Object.keys(byd).sort(function(a,b){return a-b}).map(function(d){return d+': '+byd[d]}).join(', ')+'.</p>';
   h+='<p><strong>Observed footprint of reachable objects:</strong> '+fmt(cells)+' cells (unique line items, counted once). Not a saving, a changed value or a predicted runtime; a formula change, a rename and a deletion have different consequences.</p>';
   h+='<p><strong>Evidenced reach</strong> counts parsed formula references (ref) only'+(cov.referenced_by?', checked against Referenced By at '+(cov.agreement===null?'n/a':Math.round(cov.agreement*100)+'%')+' agreement (agreement between two observed edge sets, not the share of all dependencies known)':'; no Referenced By column to check against')+(cov.unparsed?'; '+cov.unparsed+' formulas did not parse, so their references are missing':'')+'.</p>';
   if(acts===null)h+='<p><strong>Actions:</strong> not assessed (no Actions export for '+esc(model)+').</p>';
   else if(!acts.length)h+='<p><strong>Actions:</strong> none touch the reached modules (Actions export supplied).</p>';
   else{h+='<p><strong>Identified actions (module level, '+acts.length+'):</strong> an action touching a module does not establish use of every line item in it.</p><ul class="fnote">'+acts.map(function(a){return '<li>'+esc(a.name)+' <span class="badge">'+(a.kind==='import'?'import writes':'export reads')+'</span> <code>'+esc(a.module)+'</code>'+(a.processes.length?' in process '+esc(a.processes.join(', ')):' (in no process)')+(a.last_run?' &middot; last recorded run '+esc(a.last_run):'')+'</li>'}).join('')+'</ul>'}
   if(feeds.length)h+='<p><strong>Reach requiring inferred links:</strong> '+esc(model)+(dir==='downstream'?' feeds ':' is fed by ')+feeds.map(function(f){return esc(dir==='downstream'?f.to:f.from)+' ('+f.actions+' import actions)'}).join(', ')+', inferred from action names. Tracing stops at this boundary: no line-item lineage across an import/export boundary is claimed without mapping evidence.</p>';
   else h+='<p class="fnote">No inferred model-to-model feed '+(dir==='downstream'?'from':'into')+' '+esc(model)+' was found in the action names'+(cov.has_actions?'':' (no Actions export)')+'.</p>';
   ixsum.innerHTML=h;
   /* graph: columns by distance, module cards */
   var sids=Object.keys(shown.dist).map(Number),cols={};sids.forEach(function(i){var d=shown.dist[i],m=NI[i][2];cols[d]=cols[d]||{};(cols[d][m]=cols[d][m]||[]).push(i)});
   var maxShown=depth===null?maxd:Math.min(depth,maxd);
   var g='<p class="fnote">'+(depth!==null&&depth<maxd?('Showing distance 1 to '+depth+' of '+maxd+' (partial view; the totals above are the full known reach).'):('Full known reach: distance 1 to '+maxd+'.'))+' Expand a module to list its line items; select one to re-centre.</p>';
   g+='<div class="legend"><span><span class="k"></span>formula reference (evidenced, line-item level)</span><span><span class="k dash"></span>action on a module (module level)</span><span><span class="k dot"></span>model feed (inferred from names)</span><span>'+(dir==='downstream'?'left to right: each column reads the one before':'left to right: each column is read by the one before')+'</span></div>';
   g+='<div class="ix-cols"><div class="ix-col"><h4>selection</h4><div class="ix-start">'+esc(cur.kind==='item'?cur.module+'.'+cur.name:cur.module+' (module)')+'</div></div>';
   for(var d=1;d<=maxShown;d++){var cd=cols[d]||{};var mods=Object.keys(cd).sort(function(a,b){return cd[b].length-cd[a].length||a.localeCompare(b)});
     var modCard=function(m){return '<details class="ix-mod"><summary>'+esc(m)+' <span class="n">'+cd[m].length+'</span></summary><ul>'+cd[m].slice().sort(function(a,b){return NI[a][3].localeCompare(NI[b][3])}).map(function(i){return '<li><a href="#impact='+i+'">'+esc(NI[i][3])+'</a></li>'}).join('')+'</ul></details>'};
     g+='<div class="ix-col"><h4>distance '+d+' <span class="n">('+mods.reduce(function(s,m){return s+cd[m].length},0)+' line items, '+mods.length+' modules)</span></h4>';
     g+=mods.slice(0,12).map(modCard).join('');
     if(mods.length>12)g+='<details class="ix-mod"><summary>'+(mods.length-12)+' more modules</summary>'+mods.slice(12).map(modCard).join('')+'</details>';
     g+='</div>'}
   g+='</div>';ixg.innerHTML=diagram()+'<h3>By module and distance ('+(dir==='downstream'?'what depends on this':'what this depends on')+')</h3>'+g;
   /* table */
   var LIM=300,sorted=ids.slice().sort(function(a,b){return full.dist[a]-full.dist[b]||label(NI[a]).localeCompare(label(NI[b]))});
   function rowsHtml(lim){return sorted.slice(0,lim).map(function(i){var n=NI[i],p=full.par[i];return '<tr><td><a href="#impact='+i+'">'+esc(n[3])+'</a></td><td>line item</td><td>'+esc(G.models[n[1]])+' / '+esc(n[2])+'</td><td>'+full.dist[i]+'</td><td>'+(p!==undefined?(dir==='downstream'?'reads ':'read by ')+'<code>'+esc(label(NI[p]))+'</code> (formula reference)':'')+'</td><td>'+fmt(n[4])+'</td><td><button type="button" class="btn" data-path="'+i+'">path</button></td></tr>'}).join('')}
   ixt.innerHTML='<div class="wrap"><table><thead><tr><th>Object</th><th>Type</th><th>Model / module</th><th>Distance</th><th>Relationship basis</th><th>Cells</th><th></th></tr></thead><tbody>'+rowsHtml(LIM)+'</tbody></table></div>'+(sorted.length>LIM?'<p class="fnote">'+LIM+' of '+sorted.length+' shown. <button type="button" class="btn" id="ix-more">Show all</button></p>':'');
   function bindPaths(){$$('button[data-path]',ixt).forEach(function(b){b.addEventListener('click',function(){var p=pathTo(full.par,cur.ids,parseInt(b.dataset.path));
     ixp.innerHTML='<div class="path">One shortest path ('+(p.length-1)+' links; other paths may exist): '+p.map(function(i){return esc(label(NI[i]))}).join(dir==='downstream'?' &rarr; ':' &larr; ')+'</div>';ixp.scrollIntoView({block:'nearest'})})})}
   var more=$('#ix-more');if(more)more.addEventListener('click',function(){$('tbody',ixt).innerHTML=rowsHtml(sorted.length);more.parentNode.remove();bindPaths()});
   bindPaths();ixp.innerHTML='';
   ixdl.onclick=function(){var rev={report:D.title,generated:D.generated,tool:D.generator,selection:{kind:cur.kind,model:model,module:cur.module,name:cur.name,line_items:cur.ids.length},direction:dir,
       reach_scope:'full analysed reach, independent of the depth shown on screen',distance_definition:'shortest number of known formula-reference links; selection excluded; each line item once',
       counts:{unique_line_items:ids.length,direct:direct,indirect:indirect,modules:Object.keys(reachedMods).length,max_distance:maxd,by_distance:byd},
       observed_footprint_cells:cells,footprint_note:'observed footprint of reachable objects; not a saving, changed value or predicted runtime',
       edge_types_counted:['ref'],edge_types:G.edge_types,
       reach:sorted.map(function(i){var n=NI[i];return {module:n[2],name:n[3],model:G.models[n[1]],distance:full.dist[i],cells:n[4],via:full.par[i]!==undefined?label(NI[full.par[i]]):null,basis:'formula reference'}}),
       actions:acts===null?'not assessed (no Actions export)':acts,actions_note:'module-level associations; an action touching a module does not establish use of every line item in it',
       feeds_inferred:feeds,feeds_note:'inferred from import action names; no line-item lineage across the boundary',
       coverage:cov,coverage_gaps:[].concat(cov.referenced_by?[]:['no Referenced By column'],cov.unparsed?[cov.unparsed+' formulas not parsed']:[],cov.has_actions?[]:['no Actions export'],['pages, saved views, line item subsets, filters, access drivers and integrations are not in the exports']),
       validation_checks:['Baseline: record the outputs the owner names (and Calculation Effort where relevant) in production before any change.','Make the change in a development copy with the original state kept for comparison and recovery.','Use comparable inputs and scenarios in both copies.','Reconcile every reached output the owner names, plus the modules the identified actions export, cell for cell.','Agree acceptance criteria with the model owner before promotion; a status change in this report is not evidence of success.']};
     dl('change-review.json',JSON.stringify(rev,null,1),'application/json')};
 }
 /* ---- routing ---- */
 function route(){var h='';try{h=decodeURIComponent(location.hash||'')}catch(e){h=location.hash||''}h=h.replace(/^#/,'');
   if(!h){show('plan');return}
   if(VIEWS.indexOf(h)>=0){show(h);if(h==='impact'&&!cur&&G.suggested)selectItem(G.suggested.id);return}
   if(/^F\d+$/.test(h)){show('evidence');if(!openFinding(h))fmsg.textContent='There is no finding '+h+' in this report.';return}
   var m=/^impact=(.*)$/.exec(h);if(m){show('impact');var v=m[1];var mm=/^m(\d+):(.*)$/.exec(v);var ok=mm?selectModule(parseInt(mm[1]),mm[2]):(/^\d+$/.test(v)?selectItem(parseInt(v)):false);if(!ok)ixsum.innerHTML='<p class="fnote">That selection is not in this report.</p>';return}
   if(/^A\d+$/.test(h)){show('plan');var el=document.getElementById(h);if(el){el.setAttribute('tabindex','-1');el.focus();el.scrollIntoView()}return}
   var el2=document.getElementById(h);if(el2){var v2=el2.closest('.view');show(v2?v2.id:'evidence');var d=el2.closest('details');while(d){d.open=true;d=d.parentElement&&d.parentElement.closest('details')}el2.scrollIntoView();return}
   show('plan')}
 addEventListener('hashchange',route);apply();route();
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
        return f'<td><div class="formula"><code>{_e(c[1:-1])}</code><button type="button" class="copy noprint">copy</button></div></td>'
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


def _index_text(x: dict, light: bool = False) -> str:
    """Complete search text for one finding: every affected object, every evidence row and formula, explanatory text.
    One entry per line, prefixed by kind (object / formula / evidence / text) so a hit can say where it matched.
    In light mode (very large estates) only the title text and object names are indexed."""
    if light:
        return "\n".join([f"text: {x['title']} {x['model']}"] + [f"object: {o}" for o in x["objects"]])
    formula_like = re.compile(r"[()\[\]+*/<>=]|\bIF\b|\bTHEN\b")

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


GENERIC_PLAN = ["Baseline: record the outputs the owner names (and Calculation Effort where relevant) in production before any change.",
                "Make the proposed change in a development copy, keeping the original state for comparison and recovery.",
                "Use comparable inputs and scenarios in both copies; reconcile the named outputs cell for cell.",
                "Agree acceptance criteria with the model owner before promotion. A status change in this report is not evidence of success."]


def _node_ref(x: dict, nidx: dict, midx: dict) -> list[tuple[str, str]]:
    """Change impact links for the previewed objects: a line item when the name resolves, else its module."""
    out = []
    mi = midx.get(x["model"])
    if mi is None:
        return out
    mods = midx["_mods"]
    for o in x["preview"][:3]:
        mod, _, name = o.partition(".")
        if (mi, mod, name) in nidx:
            out.append((o, f"#impact={nidx[(mi, mod, name)]}"))
        elif (mi, o) in mods:
            out.append((o, f"#impact=m{mi}:{o}"))
        elif (mi, mod) in mods:
            out.append((mod, f"#impact=m{mi}:{mod}"))
    return out


def _finding(x: dict, rep: dict, nidx: dict, midx: dict) -> str:
    head = " ".join([x["id"], x["title"], x["model"], AREA_LABEL[x["area"]], x["kind_label"]] + x["rules"]).lower()
    status_opts = "".join(f'<option{" selected" if s == "To review" else ""}>{_e(s)}</option>' for s in rep["statuses"])
    ex = x["preview"]
    fb = rep["links"]["feedback"]
    report_link = f' <a class="fnote noprint" href="{_e(fb)}">Report a problem with {x["id"]} (public page; nothing is prefilled)</a>' if fb else ""
    missing = "".join(f"<li>{_inline(m)}</li>" for m in x["missing"])
    related = f'<dt>Related or alternative</dt><dd>{", ".join(f"<a href=#{r}>{r}</a>" for r in x["related"])}</dd>' if x["related"] else ""
    impl = f'<dt>Preconditions and steps</dt><dd><ul>{"".join(f"<li>{_inline(v)}</li>" for v in x["implementation"])}</ul></dd>' if x["implementation"] else ""
    nrows = len([l for l in x["evidence"] if l.startswith("|")]) - 2 if any(l.startswith("|") for l in x["evidence"]) else len(x["evidence"])
    ev = f'<details class="ev"><summary>Evidence ({max(nrows, 0)} rows)</summary><div>{md_fragment(x["evidence"])}</div></details>' if x["evidence"] else ""
    val_items = [_inline(v) for v in x["validation"]] + [_e(v) for v in GENERIC_PLAN]
    val = f'<details><summary>Validation plan</summary><div><ul>{"".join(f"<li>{v}</li>" for v in val_items)}</ul></div></details>'
    deps = _node_ref(x, nidx, midx)
    deplinks = (f'<dt>Dependencies</dt><dd>' + " &middot; ".join(f'<a href="{_e(h)}">{_e(n)}</a>' for n, h in deps) + ' <span class="fnote">(Change impact: what depends on it, what it depends on)</span></dd>') if deps else ""
    cells_v = "" if x["footprint_cells"] is None else x["footprint_cells"]
    eff_v = "" if x["footprint_effort"] is None else x["footprint_effort"]
    benefit = f'<dt>Proposed step and benefit</dt><dd>{_inline(x["next_step"])} <span class="fnote">{_inline(x["benefit"])} ({x["benefit_kind"]})</span></dd>'
    missing_dd = f'<dt>Preconditions and missing information</dt><dd><ul>{missing}</ul></dd>' if missing else ""
    return f'''<article class="f" id="{x["id"]}" data-id="{x["id"]}" data-uid="{_e(x["uid"])}" data-model="{_e(x["model"])}" data-area="{x["area"]}" data-importance="{x["importance"]}" data-strength="{x["strength"]}" data-cells="{cells_v}" data-effort="{eff_v}" data-search="{_e(head)}">
<header><h3><span class="muted">{x["id"]}.</span> {_e(x["title"])}</h3><span class="badge">{x["kind_label"]}</span>{_badges(x)}<span class="badge">export actions: {_e(x["action_usage"])}</span></header>
<div class="objs">{_e(x["model"])} &middot; {" &middot; ".join(f"<code>{_e(o)}</code>" for o in ex)} <span class="muted">({_e(x["preview_label"])}; {_e(x["object_label"])})</span></div>
<p class="hit" hidden></p>
<div class="review noprint"><label>Status <select class="stsel" aria-label="Review status for {x["id"]} (yours, stored in this browser)">{status_opts}</select></label><label style="flex:1 1 260px">Note <textarea class="note" rows="1" aria-label="Your note on {x["id"]} (stored in this browser)" placeholder="your note (kept in this browser only)"></textarea></label></div>
<dl class="fields">
<dt>What was found</dt><dd>{_inline(x["observed"])}</dd>
<dt>Why it matters</dt><dd>{_inline(x["why"])}</dd>
{benefit}
{missing_dd}{impl}{deplinks}
<dt>Evidence strength</dt><dd><strong>{x["strength"]}.</strong> {_inline(x["basis"])}</dd>
<dt>Reasons to keep the design</dt><dd>{_inline(x["keep_design"])}</dd>
{related}
</dl>
<details class="full"><summary>All affected objects ({len(x["objects"])} {_e(x["unit"])})</summary><div class="objs">{" &middot; ".join(f"<code>{_e(o)}</code>" for o in x["objects"])}</div></details>
{ev}{val}{report_link}
<div class="idx">{_e(_index_text(x, rep.get("_light", False)))}</div>
<p class="fnote"><a href="#catalogue">Catalogue</a> &middot; <a href="#area-{x["area"]}">{_e(AREA_LABEL[x["area"]])}</a> &middot; <a href="#plan">Action plan</a></p>
</article>'''


def _action_card(i: int, a: dict, rep: dict, nidx: dict, midx: dict) -> str:
    ex = a.get("explorer")
    dep = ""
    if ex:
        mi, mod, name = ex
        if name and (mi, mod, name) in nidx:
            dep = f'<a href="#impact={nidx[(mi, mod, name)]}">Change impact</a>'
        elif (mi, mod) in midx["_mods"]:
            dep = f'<a href="#impact=m{mi}:{_e(mod)}">Change impact</a>'
    ev = " ".join(f'<a href="#{f}">{f}</a>' for f in a["finding_ids"])
    keys = [x["key"] for x in rep["plan"]["actions"]]
    depends = ""
    if a["depends_on"]:
        nums = [f'<a href="#A{keys.index(k) + 1}">action {keys.index(k) + 1}</a>' for k in a["depends_on"] if k in keys]
        depends = f' &middot; After: {", ".join(nums)}' if nums else ""
    notices = "".join(f'<p class="notice">{_e(n)}</p>' for n in a["notices"])
    det = ""
    if a.get("detail"):
        has_eff = any(d.get("effort") is not None for d in a["detail"]); has_role = any(d.get("role") for d in a["detail"])
        det = ('<dt>The ' + (f'{len(a["detail"])} line items' if len(a["detail"]) != 1 else 'line item') + '</dt><dd><div class="wrap"><table class="det"><thead><tr><th>Line item</th><th>Module</th>'
               + ('<th>Role</th>' if has_role else '') + ('<th>Effort</th>' if has_eff else '') + '<th>Cells</th><th>Formula</th></tr></thead><tbody>'
               + "".join(f'<tr><td>{_e(d["name"] or d["object"])}</td><td>{_e(d["module"])}</td>' + (f'<td>{_e(d.get("role", ""))}</td>' if has_role else '')
                         + (f'<td>{(f"{d["effort"]:.1f}%" if d.get("effort") is not None else "")}</td>' if has_eff else '') + f'<td>{_c(d["cells"])}</td><td><code>{_e(d["formula"])}</code></td></tr>' for d in a["detail"])
               + '</tbody></table></div></dd>')
    if not a.get("worth", True):
        notices = f'<p class="notice below">Below the bar: {_e(a["why_not"])}.</p>' + notices
    return (f'<li class="action{"" if a.get("worth", True) else " below"}" id="A{i}"><h2><span class="n">{i}.</span> {_e(a["title"])}</h2><p class="role"><span class="model">{_e(a["model"])}</span></p>'
            f'<dl><dt>Why</dt><dd>{_e(a["why"])}</dd>{det}<dt>Steps</dt><dd><ol>{"".join(f"<li>{_e(s)}</li>" for s in a["steps"])}</ol></dd><dt>Done when</dt><dd>{_e(a["done_when"])}</dd></dl>'
            f'{notices}<p class="links">Evidence: {ev or "none"}{(" &middot; " + dep) if dep else ""}{depends}</p></li>')


LIGHT_ABOVE = 25_000     # line items; above this the per-finding search index is left out to keep the page usable


def render(rep: dict, theme_css: str | None = None, logo_svg: str | None = None, brand: str | None = None, csv_text: str = "", light: bool | None = None) -> str:
    from .report import register_rows, REGISTER_COLS
    if light is None:
        light = rep["scope"]["line_items"] > LIGHT_ABOVE
    fmap = {x["id"]: x for x in rep["findings"]}
    models = sorted({x["model"] for x in rep["findings"]})
    key = re.sub(r"[^a-z0-9]+", "-", f"{rep['title']} {rep['generated']}".lower())
    gd = rep["graph"]
    nidx = {(n[1], n[2], n[3]): n[0] for n in gd["nodes"]}
    midx = {name: i for i, name in enumerate(gd["models"])}
    midx["_mods"] = {(n[1], n[2]) for n in gd["nodes"]}
    regrows = register_rows(rep)
    rep["_light"] = light
    data = json.dumps({"key": key, "title": rep["title"], "generated": rep["generated"], "generator": rep["generator"], "csv": csv_text,
                       "register": regrows, "register_cols": REGISTER_COLS, "graph": gd}, ensure_ascii=False).replace("</", "<\\/")
    links = rep["links"]
    attrib = brand or f"Generated with {rep['generator']}"
    out = [f"<title>{_e(rep['title'])}</title>", f"<style>{_theme_bits(theme_css)}{CSS}</style>", '<div class="page">']
    out.append('<header class="top">' + f'<h1>{_e(rep["title"])}</h1><p class="attrib">{logo_svg or ""}<span>{_e(attrib)}</span></p>'
               + f'<p class="lead">{_e(rep["summary_text"][0])}</p></header>')
    out.append('<nav class="views" role="tablist" aria-label="Views"><button type="button" role="tab" data-view="plan" aria-selected="true" aria-controls="plan">Action plan</button>'
               '<button type="button" role="tab" data-view="impact" aria-selected="false" aria-controls="impact">Change impact</button>'
               '<button type="button" role="tab" data-view="evidence" aria-selected="false" aria-controls="evidence">Evidence</button>'
               '<span class="right"><button type="button" id="print-plan" class="btn primary noprint">Print action plan</button><button type="button" id="print-full" class="btn noprint">Print evidence</button></span></nav>')
    # ---------------- Action plan
    pl = rep["plan"]
    out.append('<section id="plan" class="view" role="tabpanel" aria-label="Action plan">')
    if rep.get("input_notices"):
        out.append('<div class="banner"><strong>Input notices.</strong> Some of the analysis is limited by what the exports contained:<ul>' + "".join(f"<li>{_e(n)}</li>" for n in rep["input_notices"]) + '</ul></div>')
    if light:
        out.append(f'<div class="banner">Large estate ({rep["scope"]["line_items"]:,} line items): the per-finding search index is left out of this page to keep it usable; search covers titles, models and object names only. The register and JSON hold everything.</div>')
    if pl["actions"]:
        amap = {a["key"]: a for a in pl["actions"]}
        num = {a["key"]: i for i, a in enumerate(pl["actions"], 1)}
        rows = "".join(f'<tr><td><a href="#group-{g["key"]}">{_e(g["title"])}</a></td><td>{g["met_bar"]} of {len(g["keys"])}</td>'
                       f'<td>{_e(", ".join(sorted({amap[k]["model"] for k in g["keys"] if amap[k]["worth"]})) or "none")}</td></tr>' for g in pl["groups"])
        out.append(f'<div class="summary"><table class="sum"><thead><tr><th>Group</th><th>Met the bar</th><th>Models with an action worth doing</th></tr></thead><tbody>{rows}'
                   f'<tr class="tot"><td>All candidates</td><td>{pl["met_bar"]} of {pl["considered"]}</td><td></td></tr></tbody></table></div>')
        for g in pl["groups"]:
            items = [amap[k] for k in g["keys"]]
            out.append(f'<h3 class="group-h" id="group-{g["key"]}">{_e(g["title"])} <span class="muted">({g["met_bar"]} of {len(items)} met the bar)</span></h3><p class="fnote">{_e(g["blurb"])}</p>'
                       '<ol class="actions">' + "".join(_action_card(num[a["key"]], a, rep, nidx, midx) for a in items) + "</ol>")
    else:
        out.append(f'<p><strong>{_e(pl["none"]["message"])}</strong></p><p>Next data check: {_e(pl["none"]["next_check"])}.</p>')
    out.append(f'<p class="fnote">All {pl["considered"]} candidates are shown; {pl["met_bar"]} met the bar for being worth doing. The order is a hypothesis, not a verdict. '
               '<a href="#ranking">How chosen</a> &middot; <a href="#coverage">Coverage</a> &middot; <a href="#catalogue">All findings</a></p>'
               f'<p class="fnote">{_e(rep["generality_note"])}</p></section>')
    # ---------------- Change impact
    out.append('<section id="impact" class="view" role="tabpanel" aria-label="Change impact" hidden><h2>Change impact</h2>'
               '<p>Select a model, module or line item. <strong>What depends on this</strong> follows readers downstream; <strong>what this depends on</strong> follows sources upstream. Links are parsed formula references; actions are shown at module level; model feeds are inferred from names and are a boundary, not a lineage.</p>'
               '<noscript><p class="notice">The explorer needs JavaScript. Without it, the Evidence view lists the most depended-on line items per model and the dependency evidence.</p></noscript>'
               '<div class="controls" role="search"><label class="sr" for="ix-q">Search modules and line items</label><input id="ix-q" type="search" placeholder="Type two or more characters of a module or line item name" autocomplete="off">'
               f'<select id="ix-model" aria-label="Model"><option value="">All models</option>{"".join(f"<option value={i}>{_e(m)}</option>" for i, m in enumerate(gd["models"]))}</select>'
               '<span><label><input type="radio" name="ix-dir" value="downstream" checked> What depends on this</label> <label><input type="radio" name="ix-dir" value="upstream"> What this depends on</label></span>'
               '<label>Show depth <select id="ix-depth"><option value="2">1 to 2</option><option value="1">1</option><option value="3">1 to 3</option><option value="all">all</option></select></label>'
               '<button type="button" id="ix-download" class="btn">Download change review (JSON)</button></div><ul id="ix-results" aria-label="Matches"></ul>')
    sug = gd.get("suggested")
    if sug:
        out.append(f'<p class="fnote">Suggested start: <a href="#impact={sug["id"]}">{_e(sug["module"] + "." + sug["name"])}</a> in {_e(sug["model"])}, the most-read line item there ({sug["direct_readers"]} direct readers).</p>')
    out.append('<div class="ix-grid"><div id="ix-summary" class="ix-summary"><p class="fnote">No selection yet.</p></div><div id="ix-graph"></div><div id="ix-path"></div><div id="ix-table"></div></div></section>')
    # ---------------- Evidence
    out.append('<section id="evidence" class="view" role="tabpanel" aria-label="Evidence" hidden><h2>Evidence</h2>'
               '<nav class="subnav" aria-label="Evidence sections"><a href="#catalogue">Findings catalogue</a><a href="#ranking">How the actions were chosen</a><a href="#coverage">Coverage</a><a href="#models">Models and inventory</a><a href="#map">Model map</a><a href="#dependencies">Dependency evidence</a><a href="#methodology">Methodology</a><a href="#glossary">Glossary</a><a href="#register">Register and downloads</a></nav>')
    # catalogue
    out.append('<h3 id="catalogue">Findings catalogue</h3><p class="muted">Every finding, compact. Open one for the working detail: what was found, the proposed step, preconditions, dependencies, the validation plan, reasons to keep the design, all affected objects and the evidence. Search covers every object name, evidence row and formula. Status and note are yours; <span class="store-note">they are stored in this browser only and travel only through the working register download.</span></p>')
    out.append('<div class="controls noprint" role="search"><label class="sr" for="q">Search findings</label><input id="q" type="search" placeholder="Search titles, IDs, models, object names, formulas">'
               f'<select id="f-model" aria-label="Model"><option value="">All models</option>{"".join(f"<option>{_e(m)}</option>" for m in models)}</select>'
               f'<select id="f-area" aria-label="Decision area"><option value="">All decision areas</option>{"".join(f"<option value={a['key']}>{_e(a['label'])}</option>" for a in rep['areas'])}</select>'
               '<select id="f-strength" aria-label="Evidence status"><option value="">Any evidence</option><option>confirmed</option><option>partial</option><option>inferred</option></select>'
               f'<select id="f-status" aria-label="Review status"><option value="">Any status</option>{"".join(f"<option>{_e(s)}</option>" for s in rep['statuses'])}</select>'
               '<select id="f-sort" aria-label="Sort by"><option value="importance">Sort: importance, evidence, cells (unavailable last)</option><option value="cells">Sort: footprint cells (unavailable last)</option><option value="strength">Sort: evidence strength</option><option value="model">Sort: model</option><option value="id">Sort: ID</option></select>'
               '<label><input type="checkbox" id="f-low"> show low-importance findings</label><button type="button" id="f-clear" class="btn">Clear</button><span class="count" id="f-count"></span></div><p class="fnote" id="f-msg" aria-live="polite"></p>')
    out.append('<div class="wrap"><table class="cat"><thead><tr><th>ID</th><th>Finding</th><th>Model</th><th>Next action</th><th>Evidence</th><th>Status</th></tr></thead><tbody>')
    for x in rep["findings"]:
        status_opts = "".join(f"<option>{_e(s)}</option>" for s in rep["statuses"])
        out.append(f'<tr data-id="{x["id"]}" tabindex="0"><td><a href="#{x["id"]}">{x["id"]}</a></td><td class="t">{_e(x["title"])}<br><span class="fnote">{_e(x["preview_label"])}: {_e(", ".join(x["preview"]))}</span></td><td>{_e(x["model"])}</td>'
                   f'<td>{_e(x["next_step"])}</td><td><span class="badge imp-{x["importance"]}">{x["importance"]}</span><span class="badge st-{x["strength"]}">{x["strength"]}</span><br><span class="fnote">actions: {_e(x["action_usage"])}</span></td>'
                   f'<td class="noprint"><select class="stsel" aria-label="Review status for {x["id"]}">{status_opts}</select></td></tr>')
    out.append('</tbody></table></div><div id="cat-detail" aria-live="polite"></div>')
    out.append('<div id="cat-articles">')
    for a in rep["areas"]:
        out.append(f'<h4 id="area-{a["key"]}">{_e(a["label"])} <span class="muted">({len(a["ids"])})</span></h4><p class="fnote">{_e(a["blurb"])}</p>')
        for fid in a["ids"]:
            out.append(f'<details><summary>{fid}. {_e(fmap[fid]["title"])}</summary>' + _finding(fmap[fid], rep, nidx, midx) + "</details>")
    out.append("</div>")
    # ranking
    out.append(f'<h3 id="ranking">How the actions were chosen</h3><p>{pl["considered"]} candidate{"s were" if pl["considered"] != 1 else " was"} built from the findings and all are shown; {pl["met_bar"]} met the bar for being worth doing, the rest are listed after them with the reason. The number is not fixed.</p>'
               '<h4>What counts as worth doing</h4><ul>' + "".join(f"<li>{_e(r)}</li>" for r in pl["worth"]) + "</ul><h4>Order</h4><ul>" + "".join(f"<li>{_e(r)}</li>" for r in pl["ranking"]) + "</ul>")
    if pl["candidates"]:
        out.append('<details><summary>All candidates in rank order (' + str(len(pl["candidates"])) + ')</summary><div class="wrap"><table><thead><tr><th>#</th><th>Candidate</th><th>Evidence</th><th>Kind</th><th>Scope</th><th>Footprint</th><th>Depends on</th></tr></thead><tbody>'
                   + "".join(f'<tr><td>{i}</td><td>{_e(c["title"])}<br><span class="fnote">{" ".join(f"<a href=#{f}>{f}</a>" for f in c["finding_ids"])}</span></td><td>{c["strength"]}</td><td>{c["kind"]}</td><td>{"bounded" if c["bounded"] else "open"} ({len(c["objects"])})</td>'
                             f'<td>{(_c(c["footprint_cells"]) + " cells") if c["footprint_cells"] else "not measured"}{(f"; {c['footprint_effort']:.1f}% of its model" if c["footprint_effort"] else "")}</td><td>{_e(", ".join(c["depends_on"])) or ""}</td></tr>' for i, c in enumerate(pl["candidates"], 1))
                   + "</tbody></table></div></details>")
    out.append(f'<p class="fnote">{_e(rep["validation_note"])}</p>')
    # coverage + observations + limitations
    out.append('<h3 id="coverage">Coverage and limitations</h3><ul class="limits">' + "".join(f"<li>{_inline(l)}</li>" for l in rep["limitations"]) + "</ul>")
    mt = rep["metrics"]
    out.append(f'<p class="fnote">{mt["models"]} models reviewed &middot; {mt["review_first"]} findings to review first &middot; {mt["reference"]} additional low-importance findings. No finding is a validated defect; all are observations or review candidates.</p>')
    out.append("<h4>Observations</h4><ol>" + "".join(f"<li>{_inline(o)}</li>" for o in rep["observations"]) + "</ol>")
    # models
    out.append('<h3 id="models">Models, inventory and coverage</h3>')
    for m in rep["models"]:
        f, cov, rc = m["facts"], m["coverage"], m["facts"]["referenced_by_check"]
        rows = [("Files supplied", ", ".join(f"{k}: {v}" for k, v in cov["files"].items() if v) + ("" if cov["files"]["actions"] else "; no Actions export (action usage not assessed)") + ("" if cov["files"]["modules"] else "; no Modules export")),
                ("Columns absent", "; ".join(cov.get("missing_columns", [])) or "none of the columns the analyses rely on"),
                ("Input notices", "; ".join(cov.get("warnings", [])) or "none"),
                ("Export date", "unknown (not in the files)"), ("Latest recorded action run", cov["snapshot_actions"] or ("not assessed (no Actions export)" if not cov["files"]["actions"] else "none recorded")), ("Analysis generated", rep["generated"]),
                ("Engine", "not in any export (Classic or Polaris unknown)"),
                ("Modules / line items / calculated", f"{f['modules']} / {_n_(f['line_items'])} / {_n_(f['calculated'])}"), ("Cells as exported", _n_(f["cells"])),
                ("Formulas parsed", f"{f['parse_rate']:.2%} ({f['parse_errors']} not parsed)"),
                ("Referenced By agreement", f"{rc['agreement'] if rc['agreement'] is not None else 'n/a'}: {rc['definition']} (both {rc['agree']}, parse only {rc['ours_only']}, Anaplan only {rc['anaplan_only']}). Agreement between two observed edge sets, not the share of all dependencies known."),
                ("Anaplan-only edges by cause", ", ".join(f"{k} {v}" for k, v in rc["anaplan_only_by_cause"].items()) or "none"),
                ("Rules run", ", ".join(cov["rules_run"])), ("Rules skipped or limited", "; ".join(f"{r}: {why}" for r, why in cov["rules_skipped"]) or "none"),
                ("Confirmed from metadata", "; ".join(cov["confirmed"])), ("Inferred from names", "; ".join(cov["inferred"]) or "nothing"), ("Missing", "; ".join(cov["missing"])),
                ("Calculated line items with a blank context field", str(cov["unresolved_context"]))]
        out.append(f'<details><summary>{_e(m["name"])}</summary><div class="wrap"><table><tbody>' + "".join(f"<tr><th scope=row>{_e(k)}</th><td>{_e(v)}</td></tr>" for k, v in rows) + "</tbody></table></div>")
        if f["has_effort"]:
            out.append("<h4>Where measured calculation effort sits</h4>" + md_fragment(["| Line item | Effort share | Cells | Formula |", "|---|---|---|---|"] + [f"| `{n}` | {e:.2f}% | {_c(c)} | `{fm}` |" for n, e, c, fm in f["effort_top"]]))
        else:
            out.append('<p class="fnote">Calculation Effort: unavailable (column absent or blank), not zero.</p>')
        out.append("<h4>Largest modules by cells</h4>" + md_fragment(["| Module | Cells | Share |", "|---|---|---|"] + [f"| `{n}` | {_c(c)} | {p}% |" for n, c, p in f["cells_by_module"]]))
        out.append("<h4>Most depended-on line items</h4>" + md_fragment(["| Line item | Direct readers |", "|---|---|"] + [f"| `{n}` | {c} |" for n, c in f["hubs"]]))
        if f.get("actions"):
            a = f["actions"]
            out.append("<h4>Actions</h4>" + md_fragment([f"- {a['imports']} imports, {a['exports']} exports, {a['processes']} processes; latest recorded run {a['latest_run'] or 'none recorded'}; window {a['stale_months']} months (cutoff {a['stale_cutoff'] or 'n/a'})",
                                                         f"- Not in any process: {a['not_in_process_count']}; no recorded run since cutoff: {len(a['no_recent_run'])}; no recorded run at all: {len(a['never_recorded'])}",
                                                         "- Slowest recorded: " + (", ".join(f"`{n}` {ms / 1000:.0f}s" for n, ms in a["slow"]) or "none recorded"),
                                                         "- Import targets: " + (", ".join(f"`{t}` ({n})" for t, n in a["imports_by_target"]) or "none")]))
        else:
            out.append('<h4>Actions</h4><p class="fnote">Not assessed: no Actions export was supplied for this model.</p>')
        pats = m["patterns"]
        out.append(f"<h4>Rule findings grouped into patterns ({len(pats)})</h4>" + md_fragment(["| Severity | Rule | Pattern | Count | Example | Suggested reading |", "|---|---|---|---|---|---|"] +
                   [f"| {c['severity']} | {c['rule']} | {c['label']} | {c['count']} | {(c['objects'][0] if c['objects'] else '')}: {c['message']} | {c['fix']} |" for c in pats]))
        out.append(f"<details><summary>All rule findings for {_e(m['name'])} ({len(m['lint'])})</summary>" + md_fragment(["| Rule | Severity | Object | Finding | Suggested reading |", "|---|---|---|---|---|"] +
                   [f"| {l['rule']} | {l['severity']} | `{l['object']}` | {l['message']} | {l['fix']} |" for l in m["lint"]]) + "</details>")
        red = m["redundancy"]
        if red["same_text"]:
            out.append("<h4>Identical text, context unresolved</h4>" + md_fragment(["| Formula | Why not compared | Line items |", "|---|---|---|"] + [f"| `{e['formula']}` | {e['why']} | {', '.join('`' + i['key'] + '`' for i in e['items'])} |" for e in red["same_text"]]))
        out.append("</details>")
    # map
    if rep["map"]["nodes"]:
        out.append('<h3 id="map">Model map</h3><p class="muted">Feeds inferred from import action names (dashed); no export confirms them.</p>'
                   f'<div class="map">{map_svg(rep["map"]["nodes"], rep["map"]["edges"])}</div>')
        if rep["map"]["edges"]:
            out.append('<details><summary>Feed table</summary><div class="wrap"><table><thead><tr><th>From</th><th>To</th><th>Import actions</th><th>Into</th><th>Basis</th></tr></thead><tbody>' +
                       "".join(f'<tr><td>{_e(e["from"])}</td><td>{_e(e["to"])}</td><td>{e["actions"]}</td><td>{_e(", ".join(e["targets"]))}</td><td>{_e(e["basis"])}</td></tr>' for e in rep["map"]["edges"]) + "</tbody></table></div></details>")
    # dependency evidence
    out.append('<h3 id="dependencies">Dependency evidence</h3><p class="muted">Relationship types inspected: line-item references parsed from every formula (checked against Anaplan\'s Referenced By column where present); import target modules and export source modules from the Action column; process membership. '
               'Not inspected because not exported: pages, dashboards, saved views, line item subsets (COLLECT sources), filters, access drivers, CloudWorks and API schedules.</p>')
    for m in rep["models"]:
        rc = m["facts"]["referenced_by_check"]
        if rc["agreement"] is None:
            out.append(f'<p class="fnote">{_e(m["name"])}: no Referenced By column; dependency completeness not checkable.</p>')
            continue
        ex = rc["examples"]
        out.append(f'<details><summary>{_e(m["name"])}: agreement {rc["agreement"]:.0%}; Anaplan-only edges by cause {_e(", ".join(f"{k} {v}" for k, v in rc["anaplan_only_by_cause"].items()) or "none")}</summary>' +
                   md_fragment(["| Cause | Examples (referencing line item -> referenced line item) |", "|---|---|"] + [f"| {k} | {'; '.join('`' + e + '`' for e in v) or 'none'} |" for k, v in ex.items()]) + "</details>")
    if rep["map"]["external"]:
        out.append("<h4>Source-name candidates</h4><p class=\"muted\">Words after \"from\" in import action names that matched no model in the set. Candidates, not confirmed systems; generic words are excluded.</p>" +
                   md_fragment(["| Candidate | Imports | Example |", "|---|---|---|"] + [f"| {k} | {len(v)} | `{v[0]}` |" for k, v in sorted(rep["map"]["external"].items(), key=lambda kv: -len(kv[1]))]))
    if rep["shared_dims"]:
        out.append("<h4>Dimensions shared across models</h4>" + md_fragment(["| Dimension | Models |", "|---|---|"] + [f"| {d} | {', '.join(ms)} |" for d, ms in rep["shared_dims"]]))
    if rep["duplicates"]:
        out.append("<h4>Same name and formula in more than one model</h4>" + md_fragment(["| Line item | Models | Formula |", "|---|---|---|"] + [f"| `{d['line_item']}` | {', '.join(d['models'])} | `{d['formula']}` |" for d in rep["duplicates"]]))
    # methodology
    out.append('<h3 id="methodology">Methodology</h3><p class="muted">Every rule that ran, its source, and the official documentation it rests on (consulted 2026-09-22). Rule results are automated readings of the exports; nothing here was validated in a live Anaplan model.</p>')
    out.append('<details><summary>Rules and documentation (' + str(len(rep["methodology"])) + ')</summary><div class="wrap"><table><thead><tr><th>Rule</th><th>Severity</th><th>Source</th><th>Description</th><th>Planual</th><th>Documentation</th></tr></thead><tbody>' +
               "".join(f'<tr><td>{r["id"]}<br><span class="muted">{_e(r["title"])}</span></td><td>{r["severity"]}</td><td>{r["source"]}</td><td>{_e(r["description"])}</td><td>{_e("; ".join(r["planual"]))}</td>'
                       f'<td>{"<br>".join(f"<a href={_e(d["url"])}>{_e(d["title"])}</a>: <span class=muted>{_e(d["quote"])}</span>" for d in r["docs"])}</td></tr>' for r in rep["methodology"]) + "</tbody></table></div></details>")
    out.append("<h4>Evidence strength labels</h4><ul>" + "".join(f"<li><strong>{k}.</strong> {_e(v)}</li>" for k, v in rep["strength_text"].items()) + "</ul>")
    out.append('<h3 id="glossary">Glossary</h3><ul>' + "".join(f"<li><strong>{_e(t)}.</strong> {_e(d)}</li>" for t, d in rep["glossary"]) + "</ul>")
    # register
    out.append('<h3 id="register">Register and downloads</h3><p class="noprint"><button type="button" id="dl-register" class="btn">Download findings register (CSV)</button> <button type="button" id="dl-working" class="btn">Download working register with your statuses and notes (CSV)</button> <button type="button" id="dl-status" class="btn">Export review state (JSON)</button></p>'
               '<p class="fnote">The register lists every finding with its complete object set. The working register adds your review status and note per finding (identified by a stable id that survives regeneration). Both are built in this page from the embedded data; nothing is sent anywhere. The full evidence print is under the view buttons.</p></section>')
    # footer
    foot = ['<p>Free and open source. Maintained by CodelessOps; contributions welcome.' + (f' <a href="{_e(links["source"])}">Source</a>.' if links["source"] else "") + "</p>"]
    if links["feedback"]:
        foot.append(f'<p>Something missing or not quite right? Help improve this review for everyone. <a href="{_e(links["feedback"])}">Suggest an improvement</a> (public page: say what was missed or wrong, what you expected and why it matters; no code or estate upload needed, nothing is prefilled).</p>')
    if links["help"]:
        foot.append(f'<p class="links-help">Want another pair of eyes on this change? <a href="{_e(links["help"])}">Optional paid help</a>.</p>')
    if links["contact"]:
        foot.append(f'<p>{_inline(links["contact"])}</p>')
    foot.append(f'<p class="attrib-line">{_e(attrib)}. Generated {_e(rep["generated"])}. Review statuses and notes stay in this browser.</p>')
    out.append("<footer>" + "".join(foot) + "</footer>")
    out.append(f'<script type="application/json" id="report-data">{data}</script><script>{JS}</script></div>')
    return "\n".join(out)


def _n_(x):
    return f"{x:,}" if isinstance(x, int) else str(x)
