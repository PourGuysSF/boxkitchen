#!/usr/bin/env python3
"""
Behaviour guard for the Last done line on Tempest Prep and Tempest Line
(tempest_prep.html, tempest_line.html), Slice 1 of docs/last-done.md.

Every scenario runs on BOTH pages: tempest_prep.html with team=kitchen
fixtures, tempest_line.html with team=line fixtures (plus Line PM's 11 kit
rows, so SHEET -> is there).

What counts as done (Stephen, 2026-11-21, Slice 1b): a tick WITH a name in
Who. A tick with no name means "not needed" and is left out, by the server
(assigned_to=neq.) and, for a name of only spaces, by the page.

Its promises:
  - the read: one GET through the page's own api(), right after the day's
    list is drawn, for every non-Specials task (ids ascending),
    completed=eq.true, assigned_to=neq., the 14 days before the VIEWED day (gte / lt), four
    columns, newest first, limit 1000, paged by offset while a page is full,
    at most 5 pages;
  - the words, counted by calendar from the viewed day, in Los Angeles time,
    across a clock change: "Last done: yesterday · Jose",
    "Last done: Tue 11/17 · 3 days ago", "Not done in the last 2 weeks";
    nothing at all when the read failed, was cut short or hasn't landed;
  - a late answer (the day changed) is dropped; the line is filled in place
    (no redraw: a Qty being typed keeps its focus and value; no row moves);
  - .last-done is the last child of .task, never in .task-info, and on no
    Specials row; at a 390px phone its text starts under .task-name in staff
    and manager mode, on its own line, grey, at least 12px, no side scroll;
  - checking a box is the same one POST as before and doesn't change the
    line; AM/PM sends nothing; loading sends GETs only, to the four tables;
  - the JS between // LAST DONE start/end and the CSS between
    /* LAST DONE start/end */ are byte-identical in the two pages.

Slice 2 (Line only): KIT READY on a Line AM row whose kit (KIT_MAKE pair) was
ticked WITH a name, pill not on MAKE, 1 or 2 days before the viewed day, and
the morning row not ticked with a name after the kit's day ("on" the same day
still shows). Both names must keep the pair's word (and not its `not` word);
677 has no pair. The tag replaces the row's Last done line, stays once the row
is ticked today, never shows on PM, is filled in place (no new request, a Qty
being typed keeps focus), and at 390px is whole, ink-outlined with no fill, at
least 12px, and leaves the line the height of an untagged one. Prep has no
KIT_MAKE and no tag.

The pages are live in every service, so the REAL page is loaded with
XMLHttpRequest (and fetch, sendBeacon) replaced by a stub BEFORE any page
script parses. The stub answers prep_logs like the server (filters, order,
limit/offset, never more than 1,000 rows), refuses every write (403) and
records every request. Date is pinned per scenario and Chrome runs with
TZ=America/Los_Angeles, so CI (UTC) sees what the kitchen sees. Manager mode
is set by localStorage: the PIN is never used. Same shape as check_line.py.

    python3 scripts/check_last_done.py      # ONLY=words,past  PAGES=line

Exit 0 = clean. Exit 1 = a regression, with the failing assertion named.
"""
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
from datetime import date, timedelta

CHROME_CANDIDATES = [
    "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
    "/Applications/Chromium.app/Contents/MacOS/Chromium",
    "/usr/bin/google-chrome",
    "/usr/bin/google-chrome-stable",
    "/usr/bin/chromium",
    "/usr/bin/chromium-browser",
]
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PAGES = {"prep": ("tempest_prep.html", "kitchen"), "line": ("tempest_line.html", "line")}
SCENARIOS = ("words", "past", "paged", "cut", "fail", "failp2", "race", "typing",
             "dst", "dst2", "phone", "phonemgr", "tap",
             "kits", "kitpast", "kitrename", "kittyping", "kitphone", "kitphonemgr")
LINE_ONLY = ("kits", "kitpast", "kitrename", "kittyping", "kitphone", "kitphonemgr")
WINDOW = {"phone": "500,900", "phonemgr": "500,900", "kitphone": "500,900", "kitphonemgr": "500,900"}  # pinned to 390px, as check_line.py
READS = ("prep_items", "staff", "prep_sections", "prep_logs")
NOT = "Not done in the last 2 weeks"


def find_chrome():
    env = os.environ.get("CHROME")
    if env:
        return env if os.path.exists(env) else None
    for c in CHROME_CANDIDATES:
        if os.path.exists(c):
            return c
    for name in ("google-chrome", "google-chrome-stable", "chromium", "chromium-browser"):
        p = shutil.which(name)
        if p:
            return p
    return None


def item(i, name, team, shift="AM", cat="daily", station="salad", day=None, sort=None):
    return {"id": i, "name": name, "shift": shift, "category": cat, "station": station,
            "sort_order": sort if sort is not None else i, "team": team,
            "location": "Tempest", "day_specific": day}


KIT_NAMES = [(668, "Kit - Mac and Cheese"), (669, "Kit - Buffalo sauce"), (670, "Kit - Pork belly"),
             (671, "Kit - Gastrique"), (672, "Kit - Chicken & Dumpling soup"), (678, "Kit - Dumpling"),
             (673, "Kit - Spicy green sauce"), (674, "Kit - Pickle onions& peppers"),
             (675, "Kit - Suadero"), (676, "Kit- Chilorio"), (677, "Kit- New prep coming soon")]
FILLER_IDS = list(range(120, 130))
# Line AM rows that make each kit's recipe (real ids and names, read 2026-11-22); KIT_MAKE's pairs.
MORNING = [(571, "Make - Mac and cheese", "saute"), (583, "Buffalo sauce", "grill"),
           (573, "Cook pork belly", "saute"), (615, "Bacon Gastrique", "grill"),
           (620, "Make - Chicken and Dumpling soup", "saute"), (570, "Make - Dumpling", "saute"),
           (567, "Make - Spicy green sauce", "saute"), (568, "Make - Pickle peppers & onions", "saute"),
           (759, "Cook Suadero", "saute"), (596, "Cook Chilorio pork", "saute")]
PAIRS = {668: 571, 669: 583, 670: 573, 671: 615, 672: 620, 678: 570, 673: 567, 674: 568, 675: 759, 676: 596}


def items_for(page):
    team = PAGES[page][1]
    it = [
        item(101, "Yesterday Jose", team), item(102, "Three days blank", team),
        item(103, "Unticked then Gilberto", team), item(104, "Never done", team),
        item(105, "Fourteen days", team), item(106, "Fifteen days", team),
        item(107, "Ticked today only", team), item(108, "Duplicate rows", team),
        item(109, "Weekly Friday", team, cat="weekly", day="FRI"),
        item(110, "Special", team, cat="special"),
        item(111, "Ticked 11/16 and 11/19", team), item(112, "Ticked 11/20 only", team),
        item(113, "Page two P", team), item(114, "Ticked 11/18 only", team),
        item(115, "Bare tick then Pablo", team), item(116, "Spaces-only name", team),
        item(117, "Ticked daily, never named", team), item(118, "Shared entry", team),
        item(130, "PM harness row", team, shift="PM"),
    ] + [item(i, "Filler %d" % i, team) for i in FILLER_IDS]
    if page == "line":
        it += [item(i, n, team, shift="PM", station="kits", sort=s * 10)
               for s, (i, n) in enumerate(KIT_NAMES)]
        it += [item(i, n, team, station=st) for i, n, st in MORNING]
    return it


_id = [5000]


def log(pid, d, done=True, who="", qty="", **kw):
    _id[0] += 1
    r = {"id": kw.pop("id", _id[0]), "prep_item_id": pid, "date": d, "completed": done,
         "assigned_to": who, "quantity": qty, "notes": "", "mode": None, "special_text": None}
    r.update(kw)
    return r


BASE_LOGS = [
    log(101, "2026-11-19", who="Jose"),
    log(102, "2026-11-17", who="Rubi"),
    log(103, "2026-11-19", done=False, who="Ana", qty="2"),
    log(103, "2026-11-16", who="Gilberto"),
    log(105, "2026-11-06", who="Chepe"),
    log(106, "2026-11-05", who="Chepe"),
    log(107, "2026-11-20", who="Jose"),
    log(108, "2026-11-19", who="Jose", id=6001),   # older id: arrives second
    log(108, "2026-11-19", who="", id=6002),       # newer id, blank Who: arrives first
    log(109, "2026-11-13", who="Ismael"),
    log(110, "2026-11-19", who="Old special"),
    log(110, "2026-11-20", completed=False, special_text="Harness special of the day"),
    log(111, "2026-11-16", who="Ana"), log(111, "2026-11-19", who="Ana"),
    log(112, "2026-11-20", who="Ana"),
    log(114, "2026-11-18", who="Ana"),
    log(115, "2026-11-19"), log(115, "2026-11-15", who="Pablo"),
    log(116, "2026-11-19", who="  "),
    log(118, "2026-11-19", who="Gilberto, Vidalio & Evelin"),
] + [log(117, "2026-11-%02d" % d) for d in range(7, 20)] + [
    log(668, "2026-11-19", who="Harness PM"),
]


def fillers(n, first, last):
    d0, days = date.fromisoformat(first), (date.fromisoformat(last) - date.fromisoformat(first)).days + 1
    return [log(FILLER_IDS[k % len(FILLER_IDS)], (d0 + timedelta(days=k % days)).isoformat(), who="Filler")
            for k in range(n)]


KIT_LOGS = [
    log(668, "2026-11-19", who="Gilberto"), log(571, "2026-11-20", who="Rubi"),   # built last night; 571 ticked today
    log(672, "2026-11-19", who="Evelin"), log(620, "2026-11-19", who="Rubi"),     # made yesterday, built last night
    log(670, "2026-11-18", who="Pablo"), log(573, "2026-11-17", who="Ana"),       # built 2 nights ago, not made
    log(671, "2026-11-18", who="Eddy"), log(615, "2026-11-19", who="Ana"),        # built 2 nights ago, made yesterday
    log(674, "2026-11-17", who="Gilberto"),                                       # too old
    log(669, "2026-11-19", who="Eddy"), log(583, "2026-11-19"),                   # made yesterday, no name
    log(678, "2026-11-19"),                                                       # built with no name
    log(675, "2026-11-19", who="Chepe", mode="make"),                             # pill on MAKE
    log(676, "2026-11-19", done=False, who="Chepe"),                              # Who, no tick
    log(677, "2026-11-19", who="Harness PM"),                                     # placeholder, no pair
]
KIT_WORDS = {571: "KIT READY Kit built yesterday · Gilberto", 620: "KIT READY Kit built yesterday · Evelin",
             573: "KIT READY Kit built Wed 11/18 · 2 days ago · Pablo", 615: "Last done: yesterday · Ana",
             568: "Not done in the last 2 weeks", 583: "KIT READY Kit built yesterday · Eddy",
             570: "Not done in the last 2 weeks", 759: "Not done in the last 2 weeks",
             596: "Not done in the last 2 weeks", 567: "Not done in the last 2 weeks"}

WORDS = {101: "Last done: yesterday · Jose", 102: "Last done: Tue 11/17 · 3 days ago · Rubi",
         103: "Last done: Mon 11/16 · 4 days ago · Gilberto", 104: NOT,
         105: "Last done: Fri 11/6 · 14 days ago · Chepe", 106: NOT, 107: NOT,
         108: "Last done: yesterday · Jose", 109: "Last done: Fri 11/13 · 7 days ago · Ismael", 112: NOT,
         115: "Last done: Sun 11/15 · 5 days ago · Pablo", 116: NOT, 117: NOT,
         118: "Last done: yesterday · Gilberto, Vidalio & Evelin"}

# scenario -> clock [y, m(1-12), d, h, min], extra logs, expectations
SCEN = {
    "words": {"logs": BASE_LOGS, "expect": WORDS},
    "past": {"logs": BASE_LOGS},
    "paged": {"logs": BASE_LOGS + fillers(1500, "2026-11-10", "2026-11-19") + [log(113, "2026-11-07", who="Pablo")],
              "expect": {113: "Last done: Sat 11/7 · 13 days ago · Pablo"}},
    "cut": {"logs": BASE_LOGS + fillers(5200, "2026-11-08", "2026-11-19")},
    "fail": {"logs": BASE_LOGS},
    "failp2": {"logs": BASE_LOGS + fillers(1500, "2026-11-10", "2026-11-19")},
    "race": {"logs": BASE_LOGS},
    "typing": {"logs": BASE_LOGS},
    "dst": {"clock": [2027, 3, 20, 0, 30],
            "logs": [log(101, "2027-03-13", who="Jose"), log(102, "2027-03-19", who="Rubi")],
            "expect": {101: "Last done: Sat 3/13 · 7 days ago · Jose", 102: "Last done: yesterday · Rubi"}},
    "dst2": {"clock": [2026, 11, 2, 8, 0], "logs": [log(101, "2026-10-31", who="Jose")],
             "expect": {101: "Last done: Sat 10/31 · 2 days ago · Jose"}},
    "phone": {"logs": BASE_LOGS},
    "phonemgr": {"logs": BASE_LOGS},
    "tap": {"logs": BASE_LOGS},
    "kits": {"logs": BASE_LOGS[:-1] + KIT_LOGS},
    "kitpast": {"logs": BASE_LOGS[:-1] + KIT_LOGS},
    "kitrename": {"logs": BASE_LOGS[:-1] + [log(673, "2026-11-19", who="Ana"), log(678, "2026-11-19", who="Ana")],
                  "renamed": {"673": "Kit - Nachos", "570": "Make - Dumpling soup"}},
    "kittyping": {"logs": BASE_LOGS[:-1] + KIT_LOGS},
    "kitphone": {"logs": BASE_LOGS[:-1] + KIT_LOGS},
    "kitphonemgr": {"logs": BASE_LOGS[:-1] + KIT_LOGS},
}
# Line words: BASE_LOGS has 668 ticked 11/19 by "Harness PM", so 571 carries the tag.
WORDS_LINE = {571: "KIT READY Kit built yesterday · Harness PM"}

GATE_RE = re.compile(r"window\.location\.replace\('index\.html'\)")

HARNESS = r"""
<script>
/* ---- test harness: installed BEFORE any page script parses ---- */
(function(){
  var FX=__FIXTURES__,SCEN=FX.scen,reqs=[];
  window.__h={scen:SCEN,page:FX.page,reqs:reqs,fx:FX,loadN:null};
  FX.items.forEach(function(r){if(FX.renamed[r.id])r.name=FX.renamed[r.id];});
  /* the clock: new Date() and Date.now() give the scenario's time; all else is the real Date */
  var RD=Date,c=FX.clock,NOW=new RD(c[0],c[1]-1,c[2],c[3],c[4]).getTime();
  function D(){
    if(!(this instanceof D))return new RD(NOW).toString();
    if(!arguments.length)return new RD(NOW);
    var a=[null].concat([].slice.call(arguments));return new (Function.prototype.bind.apply(RD,a))();
  }
  D.prototype=RD.prototype;D.now=function(){return NOW;};D.UTC=RD.UTC;D.parse=RD.parse;
  window.Date=D;
  if(/phone/.test(SCEN))document.write('<style>html{width:390px!important;max-width:390px!important}</style>');
  try{if(/phonemgr$/.test(SCEN))localStorage.setItem('boxkitchen.mgr','1');else localStorage.removeItem('boxkitchen.mgr');}catch(e){}
  function qp(q,re){var m=re.exec(q);return m?m[1]:null;}
  /* prep_logs, answered like the server */
  function prepLogs(q){
    var d=qp(q,/(?:^|&)date=eq\.([0-9-]+)/);
    if(d)return{rows:FX.logs.filter(function(r){return r.date===d;}),ld:false};
    var ids=(qp(q,/prep_item_id=in\.\(([^)]*)\)/)||'').split(',').map(Number),
        gte=qp(q,/date=gte\.([0-9-]+)/),lt=qp(q,/date=lt\.([0-9-]+)/),lte=qp(q,/date=lte\.([0-9-]+)/),
        comp=/completed=eq\.true/.test(q),named=/assigned_to=neq\.(&|$)/.test(q),lim=Math.min(1000,+(qp(q,/limit=(\d+)/)||1000)),off=+(qp(q,/offset=(\d+)/)||0);
    var rows=FX.logs.filter(function(r){return ids.indexOf(r.prep_item_id)>-1&&(!comp||r.completed)&&(!named||(r.assigned_to!=null&&r.assigned_to!==''))&&(!gte||r.date>=gte)&&(!lt||r.date<lt)&&(!lte||r.date<=lte);});
    rows.sort(function(a,b){return a.date<b.date?1:a.date>b.date?-1:b.id-a.id;});
    var sel=(qp(q,/select=([^&]*)/)||'').split(',');
    rows=rows.slice(off,off+lim).map(function(r){var o={};sel.forEach(function(k){o[k]=r[k];});return o;});
    return{rows:rows,ld:true,off:off,lt:lt};
  }
  function Stub(){this.readyState=0;this.status=0;this.responseText='';this._h={};}
  Stub.prototype.open=function(m,u){this._m=String(m).toUpperCase();this._u=String(u);};
  Stub.prototype.setRequestHeader=function(k,v){this._h[k]=v;};
  Stub.prototype.abort=function(){};
  Stub.prototype.send=function(body){
    var x=this,m=x._u.match(/\/rest\/v1\/([A-Za-z_]+)\??(.*)$/),t=m?m[1]:'',q=m?m[2]:'',rec={method:x._m,url:x._u,table:t,query:q,body:body==null?null:String(body),headers:x._h};
    reqs.push(rec);
    var delay=20,status=200,text='[]';
    if(x._m!=='GET'){status=403;text='{"message":"harness: writes are not allowed"}';}
    else if(t==='prep_items')text=JSON.stringify(FX.items);
    else if(t==='staff')text=JSON.stringify(FX.staff);
    else if(t==='prep_logs'){
      var a=prepLogs(q);text=JSON.stringify(a.rows);rec.ld=a.ld;
      if(a.ld){
        rec.off=a.off;rec.lt=a.lt;delay=600;
        if(SCEN==='race'&&a.lt==='2026-11-19')delay=1800;
        if(SCEN==='fail'||(SCEN==='failp2'&&a.off===1000)){status=500;text='{"code":"57014","message":"harness: server error"}';}
      }
    }
    setTimeout(function(){x.status=status;x.responseText=text;x.readyState=4;if(x.onload)x.onload();},delay);
  };
  window.XMLHttpRequest=Stub;
  window.fetch=function(u,o){reqs.push({method:((o&&o.method)||'GET').toUpperCase(),url:String(u),via:'fetch'});return new Promise(function(){});};
  if(navigator.sendBeacon)navigator.sendBeacon=function(u){reqs.push({method:'POST',url:String(u),via:'beacon'});return true;};
})();
</script>
"""

RUNNER = r"""
<script>
(function(){
  var H=window.__h,FX=H.fx,S=H.scen,log=[],fails=[];
  function ok(name,cond,detail){log.push(name);if(!cond)fails.push(name+(detail===undefined?'':' :: '+JSON.stringify(detail)));}
  function finish(){var d=document.createElement('div');d.id='harnessResults';d.textContent=JSON.stringify({log:log,fails:fails});document.body.appendChild(d);}
  function later(ms,f){setTimeout(f,ms);}
  function row(id){return document.querySelector('.task[data-id="'+id+'"]');}
  function ld(id){var r=row(id);return r?r.querySelector('.last-done'):null;}
  function ldt(id){var e=ld(id);return e?e.textContent:null;}
  function lines(){return [].slice.call(document.querySelectorAll('.last-done'));}
  function ldReqs(){return H.reqs.filter(function(r){return r.ld;});}
  function lastLd(){var a=ldReqs();return a[a.length-1];}
  function expectAll(tag,exp){Object.keys(exp).forEach(function(id){ok(tag+': '+id+' reads "'+exp[id]+'"', ldt(id)===exp[id], ldt(id));});}
  function allEmpty(tag){var L=lines();ok(tag+': every line is drawn and empty', L.length>0&&L.every(function(e){return e.textContent==='';}), L.map(function(e){return e.textContent;}).filter(String).slice(0,5));}
  function noToast(tag){var t=document.getElementById('toast');ok(tag+': no toast showing', !t||!t.classList.contains('show'), t&&t.textContent);}
  function click(sel){var e=document.querySelector(sel);if(e)e.click();return !!e;}
  function shift(s){[].forEach.call(document.querySelectorAll('.shift-btn'),function(b){if(b.textContent.indexOf(s)>-1)b.click();});}

  /* structure, on whatever is drawn */
  function structure(tag){
    [].forEach.call(document.querySelectorAll('.task[data-id]'),function(t){
      var id=t.getAttribute('data-id'),sp=FX.special.indexOf(+id)>-1,L=t.querySelectorAll('.last-done');
      if(sp){ok(tag+': Specials row '+id+' has no line', L.length===0);return;}
      ok(tag+': row '+id+' has exactly one line, its last child', L.length===1&&t.lastElementChild===L[0]);
      ok(tag+': row '+id+' line is not in .task-info', L.length===1&&!L[0].closest('.task-info'));
      var ni=document.getElementById('ni'+id);
      ok(tag+': #ni'+id+' still follows its .task-name', ni&&ni.previousElementSibling&&ni.previousElementSibling.classList.contains('task-name'));
    });
  }
  function common(){
    var R=H.reqs.slice(0,H.loadN==null?H.reqs.length:H.loadN);
    ok('load: GETs only, no body', R.every(function(r){return r.method==='GET'&&!r.body;}), R.map(function(r){return r.method+' '+r.url;}));
    ok('load: no fetch, no sendBeacon', R.every(function(r){return !r.via;}));
    ok('load: no write headers', R.every(function(r){return !r.headers||(!r.headers.Prefer&&!r.headers['Content-Type']);}));
    ok('load: only the four tables', R.length>0&&R.every(function(r){return FX.reads.indexOf(r.table)>-1;}), R.map(function(r){return r.table;}));
  }
  function landed(f){later(1500,f);} /* last-done answers take 600ms per page */

  function tags(){return [].map.call(document.querySelectorAll('.kit-ready'),function(e){return +e.closest('.task').getAttribute('data-id');});}
  function kits(){
    expectAll('kits',FX.kitwords);
    var T=tags().sort();
    ok('kits: tags on exactly 571 573 583 620', JSON.stringify(T)===JSON.stringify([571,573,583,620]), T);
    ok('kits: one .kit-ready in 571', ld(571)&&ld(571).querySelectorAll('.kit-ready').length===1);
    ok('kits: the tag reads KIT READY', !!(ld(571)&&ld(571).querySelector('.kit-ready'))&&ld(571).querySelector('.kit-ready').textContent==='KIT READY');
    ok('kits: 571 ticked today and struck through, tag stays', row(571).classList.contains('done')&&/^KIT READY/.test(ldt(571)));
    ok('kits: 677 keeps its own line', ldt(677)===null||ldt(677)==='Last done: yesterday · Harness PM', ldt(677));
    var R=H.reqs.slice(0,H.loadN);
    /* the same requests as a page with no kits ticked: one day read, one last-done read (Line reads staff twice on load, as before) */
    ok('kits: no extra request (one day read, one last-done read)', R.filter(function(r){return r.ld;}).length===1&&R.filter(function(r){return r.table==='prep_logs'&&!r.ld;}).length===1&&R.length===H.fx.loadCount, R.map(function(r){return r.method+' '+r.table;}));
    common();
    shift('PM');
    ok('kits: no tag on PM', document.querySelectorAll('.kit-ready').length===0);
    ok('kits: PM kit rows keep their own line', ldt(668)==='Last done: yesterday · Gilberto'&&ldt(677)==='Last done: yesterday · Harness PM', [ldt(668),ldt(677)]);
    shift('AM');
    ok('kits: AM tags back', tags().length===4);
    finish();
  }
  function kitpast(){
    click('[onclick*="changeDate(-1)"]');
    landed(function(){
      expectAll('kitpast 11/19',{573:'KIT READY Kit built yesterday · Pablo',615:'KIT READY Kit built yesterday · Eddy',571:FX.not,620:FX.not,583:FX.not});
      finish();
    });
  }
  function kitrename(){
    ok('kitrename: no tag on 567 (kit renamed Nachos)', ldt(567)===FX.not, ldt(567));
    ok('kitrename: no tag on 570 (renamed Dumpling soup)', ldt(570)===FX.not, ldt(570));
    ok('kitrename: no tag anywhere', tags().length===0, tags());
    common();finish();
  }
  function kitphone(){
    var mgr=S==='kitphonemgr',tag=document.querySelector('.task[data-id="571"] .kit-ready');
    var probe=document.createElement('span');probe.style.color='var(--ink)';document.body.appendChild(probe);var ink=getComputedStyle(probe).color;probe.remove();
    var plain=ld(101).getBoundingClientRect().height;
    ok(S+': no side scroll', document.documentElement.scrollWidth<=window.innerWidth);
    tags().forEach(function(id){
      var L=ld(id),lr=L.getBoundingClientRect(),t=L.querySelector('.kit-ready'),tr=t.getBoundingClientRect(),cs=getComputedStyle(t);
      ok(S+': '+id+' tag whole inside its line', tr.width>0&&tr.right<=lr.right+0.5&&tr.left>=lr.left-0.5, [tr.left,tr.right,lr.right]);
      ok(S+': '+id+' line height equals an untagged line', Math.abs(lr.height-plain)<0.5, [lr.height,plain]);
      ok(S+': '+id+' tag inside the line vertically', tr.top>=lr.top-0.5&&tr.bottom<=lr.bottom+0.5, [tr.top,tr.bottom,lr.top,lr.bottom]);
      ok(S+': '+id+' row height equals an untagged row', Math.abs(row(id).getBoundingClientRect().height-row(101).getBoundingClientRect().height)<0.5);
      ok(S+': '+id+' border solid ink', cs.borderTopStyle==='solid'&&cs.borderTopColor===ink, [cs.borderTopStyle,cs.borderTopColor]);
      ok(S+': '+id+' no fill', cs.backgroundColor==='rgba(0, 0, 0, 0)'&&cs.backgroundImage==='none', cs.backgroundColor);
      ok(S+': '+id+' ink text', cs.color===ink, cs.color);
      ok(S+': '+id+' at least 12px', parseFloat(cs.fontSize)>=12, cs.fontSize);
    });
    ok(S+': tags present', tags().length===4, tags());
    finish();
  }
  var steps={
    words:function(){
      structure('words');
      var a=ldReqs();
      ok('words: exactly one last-done read', a.length===1, a.length);
      ok('words: the query is exact', a[0]&&a[0].query===FX.query, a[0]&&a[0].query);
      expectAll('words',FX.expect);
      expectAll('words',FX.wordsline);
      if(FX.page==='prep'){
        ok('words: Prep has no KIT READY', document.querySelectorAll('.kit-ready').length===0);
        ok('words: Prep has no KIT_MAKE', typeof window.KIT_MAKE==='undefined');
      }
      ok('words: 107 is ticked today', row(107)&&row(107).querySelector('.checkbox').classList.contains('checked'));
      ok('words: the special is drawn', !!row(110));
      common();finish();
    },
    past:function(){
      for(var i=0;i<3;i++)click('[onclick*="changeDate(-1)"]');
      landed(function(){
        var q=lastLd()&&lastLd().query||'';
        ok('past: last read asks gte.2026-11-03', /date=gte\.2026-11-03&/.test(q), q);
        ok('past: last read asks lt.2026-11-17', /date=lt\.2026-11-17&/.test(q), q);
        expectAll('past',{111:'Last done: yesterday · Ana',112:FX.not,102:FX.not,103:'Last done: yesterday · Gilberto'});
        structure('past');
        click('[onclick*="goToday"]');
        landed(function(){expectAll('past back',FX.words);finish();});
      });
    },
    paged:function(){
      var a=ldReqs();
      ok('paged: exactly two last-done reads', a.length===2, a.map(function(r){return r.off;}));
      ok('paged: offsets 0 and 1000', a.length===2&&a[0].off===0&&a[1].off===1000);
      expectAll('paged',FX.expect);common();finish();
    },
    cut:function(){
      var a=ldReqs();
      ok('cut: five reads, no sixth', a.length===5, a.length);
      allEmpty('cut');common();finish();
    },
    fail:function(){
      allEmpty('fail');noToast('fail');
      ok('fail: 107 still ticked', row(107).querySelector('.checkbox').classList.contains('checked'));
      ok('fail: progress shows', /\d+\/\d+/.test(document.getElementById('progressText').textContent));
      common();finish();
    },
    failp2:function(){
      ok('failp2: two reads', ldReqs().length===2, ldReqs().length);
      allEmpty('failp2');noToast('failp2');common();finish();
    },
    race:function(){
      H.loadN=H.reqs.length;
      /* two taps 0.1s apart: 11/19's day read has answered and its last-done read is out */
      click('[onclick*="changeDate(-1)"]');
      later(100,function(){click('[onclick*="changeDate(-1)"]');});
      later(300,function(){
        allEmpty('race before 11/18 lands');
        later(700,function(){
          expectAll('race 11/18',{101:FX.not,102:'Last done: yesterday · Rubi',114:FX.not});
          later(1500,function(){
            ok('race: a read for 11/19 went out and answered last', ldReqs().some(function(r){return r.lt==='2026-11-19';}), ldReqs().map(function(r){return r.lt;}));
            expectAll('race after the late answer',{101:FX.not,102:'Last done: yesterday · Rubi',114:FX.not});
            finish();
          });
        });
      });
    }
  };
  /* scenarios that act before the read lands */
  function early(){
    if(S==='typing'){
      var q=row(101).querySelector('.qty'),h0=row(101).getBoundingClientRect().height;
      ok('typing: line empty before the read', ldt(101)==='');
      q.focus();q.value='3';var n0=H.reqs.length;
      landed(function(){
        ok('typing: the line filled', ldt(101)===FX.words[101], ldt(101));
        ok('typing: the Qty box keeps focus', document.activeElement===q);
        ok('typing: and its "3"', q.value==='3', q.value);
        ok('typing: no request went out', H.reqs.length===n0, H.reqs.slice(n0).map(function(r){return r.method+' '+r.url;}));
        ok('typing: row height unchanged', Math.abs(row(101).getBoundingClientRect().height-h0)<0.5, [h0,row(101).getBoundingClientRect().height]);
        common();finish();
      });
      return true;
    }
    if(S==='race'){steps.race();return true;}
    if(S==='kittyping'){
      var kq=row(571).querySelector('.qty');
      ok('kittyping: no tag before the read', ldt(571)==='');
      kq.focus();kq.value='3';var k0=H.reqs.length;
      landed(function(){
        ok('kittyping: the tag filled in place', ldt(571)===FX.kitwords[571], ldt(571));
        ok('kittyping: the Qty box keeps focus and "3"', document.activeElement===kq&&kq.value==='3');
        ok('kittyping: no request went out', H.reqs.length===k0);
        finish();
      });
      return true;
    }
    return false;
  }
  function phone(){
    var mgr=S==='phonemgr';
    function check(tag){
      ok(tag+': no side scroll', document.documentElement.scrollWidth<=window.innerWidth, [document.documentElement.scrollWidth,window.innerWidth]);
      var probe=document.createElement('span');probe.style.color='var(--grey)';document.body.appendChild(probe);var grey=getComputedStyle(probe).color;probe.remove();
      [].forEach.call(document.querySelectorAll('.task[data-id]'),function(t){
        var id=t.getAttribute('data-id');if(FX.special.indexOf(+id)>-1)return;
        var L=t.querySelector('.last-done'),cs=getComputedStyle(L),lr=L.getBoundingClientRect(),nm=t.querySelector('.task-name').getBoundingClientRect();
        var cb=t.querySelector('.checkbox').getBoundingClientRect(),fs=t.querySelector('.task-fields'),fr=fs.getBoundingClientRect();
        var start=lr.left+parseFloat(cs.paddingLeft);
        ok(tag+': '+id+' line below checkbox and Who', lr.top>=cb.bottom-4.5&&lr.top>=fr.bottom-4.5, [lr.top,cb.bottom,fr.bottom]);
        ok(tag+': '+id+' text starts under the name', Math.abs(start-nm.left)<=1, [start,nm.left]);
        var line1=[cb].concat([].map.call(fs.querySelectorAll('.who-select,.qty,.note-btn'),function(e){return e.getBoundingClientRect();}));
        ok(tag+': '+id+' checkbox, Who, Qty, note on the first line', line1.every(function(r){return r.bottom<=lr.top+4.5&&r.top<cb.bottom;}), line1.map(function(r){return [r.top,r.bottom];}));
        ok(tag+': '+id+' at least 12px', parseFloat(cs.fontSize)>=12, cs.fontSize);
        ok(tag+': '+id+' grey', cs.color===grey, [cs.color,grey]);
        ok(tag+': '+id+' one line tall', lr.height>0&&lr.height<20, lr.height);
      });
      if(FX.page==='line'&&tag.indexOf('PM')>-1){
        FX.kits.forEach(function(id){
          var ni=document.getElementById('ni'+id);
          ok(tag+': #ni'+id+' still follows its .task-name', ni&&ni.previousElementSibling&&ni.previousElementSibling.classList.contains('task-name'));
        });
        var A=[].slice.call(document.querySelectorAll('.kit-sheet-link'));
        ok(tag+': 7 SHEET buttons', A.length===7, A.length);
        A.forEach(function(a){
          var r=a.getBoundingClientRect(),i=a.closest('.task-info'),ir=i?i.getBoundingClientRect():null,t=a.closest('.task').getBoundingClientRect();
          ok(tag+': SHEET in .task-info, 44px, inside its row', !!i&&r.height>=44&&r.left>=t.left-0.5&&r.right<=t.right+0.5&&r.bottom<=t.bottom+0.5, [r.height,r.left,r.right,t.right]);
          /* staff mode: wholly inside .task-info too. In manager mode at 390px the name column is
             ~39px and SHEET (59px) already spills past it on main (ad3ee57), before this slice:
             pre-existing, recorded in docs/last-done.md, not this slice's to fix. */
          if(!mgr)ok(tag+': SHEET wholly inside .task-info', r.left>=ir.left-0.5&&r.right<=ir.right+0.5&&r.bottom<=ir.bottom+0.5, [r.left,r.right,ir.left,ir.right]);
        });
      }
    }
    check(S+' AM');
    shift('PM');check(S+' PM');shift('AM');
    common();finish();
  }
  function tap(){
    H.loadN=H.reqs.length;
    var before=ldt(104),nLd=ldReqs().length;
    row(104).querySelector('.checkbox').click();
    later(400,function(){
      var w=H.reqs.slice(H.loadN).filter(function(r){return r.method!=='GET';}),b=w[0]&&w[0].body?JSON.parse(w[0].body):{};
      ok('tap: exactly one write attempt', w.length===1, w.map(function(r){return r.method+' '+r.url;}));
      ok('tap: a POST to prep_logs, completed, item 104, today', w.length===1&&w[0].method==='POST'&&w[0].table==='prep_logs'&&b.completed===true&&b.prep_item_id===104&&b.date==='2026-11-20', b);
      ok('tap: its line is unchanged', ldt(104)===before&&before===FX.not, [before,ldt(104)]);
      ok('tap: no new last-done read', ldReqs().length===nLd);
      var n=H.reqs.length;shift('PM');
      ok('tap: PM rows have lines', !!ld(130)&&ldt(130)===FX.not, ldt(130));
      shift('AM');
      ok('tap: AM/PM sends no request', H.reqs.length===n, H.reqs.slice(n).map(function(r){return r.url;}));
      ok('tap: AM lines still there', ldt(101)===FX.words[101]);
      finish();
    });
  }
  function run(){
    if(H.loadN==null)H.loadN=H.reqs.length;
    if(S==='dst'||S==='dst2'){
      var q=ldReqs()[0]&&ldReqs()[0].query||'';
      if(S==='dst')ok('dst: asks gte.2027-03-06 and lt.2027-03-20', /date=gte\.2027-03-06&date=lt\.2027-03-20&/.test(q), q);
      expectAll(S,FX.expect);common();finish();return;
    }
    if(S==='phone'||S==='phonemgr'){phone();return;}
    if(S==='tap'){tap();return;}
    if(S==='kits'){kits();return;}
    if(S==='kitpast'){kitpast();return;}
    if(S==='kitrename'){kitrename();return;}
    if(S==='kitphone'||S==='kitphonemgr'){kitphone();return;}
    steps[S]();
  }
  /* wait for the rows, act early where the scenario needs it, then let the read land */
  var t0=Date.now(),waited=0;
  (function wait(){
    if(document.querySelector('.task[data-id]')||waited>5000){
      setTimeout(function(){
        if(S!=='race'&&S!=='typing'&&S!=='kittyping'){
          ok('first draw: lines drawn and empty before the read lands', lines().length>0&&lines().every(function(e){return e.textContent==='';}));
        }
        if(early())return;
        var h0=row(101)?row(101).getBoundingClientRect().height:0;
        setTimeout(function(){
          if(row(101))ok('rows do not jump when the line fills', Math.abs(row(101).getBoundingClientRect().height-h0)<0.5, [h0,row(101).getBoundingClientRect().height]);
          run();
        },S==='cut'?3600:1500);
      },100);
    }else{waited+=50;setTimeout(wait,50);}
  })();
})();
</script>
"""


def build_page(page, scen):
    fname, team = PAGES[page]
    src = open(os.path.join(ROOT, fname), encoding="utf-8").read()
    src, n = GATE_RE.subn("void 0 /* gate neutralised by check_last_done.py */", src)
    if n != 1:
        sys.exit("check_last_done: entry redirect not found exactly once in " + fname)
    sc = SCEN[scen]
    its = items_for(page)
    ids = sorted(i["id"] for i in its if i["category"] != "special")
    fx = {
        "scen": scen, "page": page, "items": its, "logs": sc["logs"],
        "clock": sc.get("clock", [2026, 11, 20, 10, 0]),
        "staff": [{"id": 1, "name": "Harness AM", "shift": "AM", "active": True, "sort_order": 1, "location": "Tempest"},
                  {"id": 2, "name": "Harness PM", "shift": "PM", "active": True, "sort_order": 1, "location": "Tempest"}],
        "reads": list(READS), "expect": {str(k): v for k, v in sc.get("expect", {}).items()},
        "words": {str(k): v for k, v in WORDS.items()}, "not": NOT,
        "special": [i["id"] for i in its if i["category"] == "special"],
        "kits": [i for i, _ in KIT_NAMES] if page == "line" else [],
        "kitwords": {str(k): v for k, v in KIT_WORDS.items()},
        "wordsline": {str(k): v for k, v in WORDS_LINE.items()} if page == "line" else {},
        "pairs": {str(k): v for k, v in PAIRS.items()}, "loadCount": 6 if page == "line" else 5, "renamed": sc.get("renamed", {}),
        "query": "prep_item_id=in.(" + ",".join(map(str, ids)) + ")&completed=eq.true&assigned_to=neq.&date=gte.2026-11-06"
                 "&date=lt.2026-11-20&select=prep_item_id,date,assigned_to,mode&order=date.desc,id.desc&limit=1000&offset=0",
    }
    src = src.replace("<head>", "<head>" + HARNESS.replace("__FIXTURES__", json.dumps(fx)), 1)
    src = re.sub(r'<link rel="preconnect"[^>]*>\s*', '', src)
    src = re.sub(r'<link rel="stylesheet" href="https://fonts[^>]*>\s*', '', src)
    return src.replace("</body>", RUNNER + "</body>", 1)


RESULT_RE = re.compile(r'<div id="harnessResults">(.*?)</div>', re.S)


def run_scenario(chrome, path, scen):
    dom, err = path + ".dom", path + ".err"
    env = dict(os.environ, TZ="America/Los_Angeles")
    with open(dom, "w") as fo, open(err, "w") as fe:
        proc = subprocess.Popen(
            [chrome, "--headless=new", "--disable-gpu", "--no-sandbox",
             "--no-first-run", "--disable-extensions",
             "--disable-background-networking", "--disable-component-update",
             "--disable-default-apps", "--disable-sync",
             "--host-resolver-rules=MAP * ~NOTFOUND",
             "--user-data-dir=" + path + ".cd",
             "--window-size=" + WINDOW.get(scen, "1200,900"),
             "--virtual-time-budget=30000", "--dump-dom", "file://" + path],
            stdout=fo, stderr=fe, env=env)
        deadline, m = time.time() + 120, None
        try:
            while time.time() < deadline:
                m = RESULT_RE.search(open(dom, encoding="utf-8", errors="replace").read())
                if m or proc.poll() is not None:
                    break
                time.sleep(0.25)
        finally:
            if proc.poll() is None:
                proc.kill()
            proc.wait()
    if not m:
        m = RESULT_RE.search(open(dom, encoding="utf-8", errors="replace").read())
    if not m:
        return None, "no results div\n" + open(err, encoding="utf-8", errors="replace").read()[-600:]
    body = (m.group(1).replace("&amp;", "&").replace("&lt;", "<")
            .replace("&gt;", ">").replace("&quot;", '"'))
    return json.loads(body), None


def copies():
    """The two copies of the block, JS and CSS, must be byte-identical."""
    out, fails = 0, []
    blocks = {}
    for page, (fname, _) in PAGES.items():
        src = open(os.path.join(ROOT, fname), encoding="utf-8").read()
        for kind, a, b in (("js", "// LAST DONE start", "// LAST DONE end"),
                           ("css", "/* LAST DONE start */", "/* LAST DONE end */")):
            out += 1
            if src.count(a) != 1 or src.count(b) != 1:
                fails.append("copies: %s %s markers not exactly once" % (fname, kind))
                continue
            blocks[(page, kind)] = src[src.index(a):src.index(b)]
    for kind in ("js", "css"):
        out += 1
        if blocks.get(("prep", kind)) is None or blocks.get(("prep", kind)) != blocks.get(("line", kind)):
            fails.append("copies: the %s block differs between tempest_prep.html and tempest_line.html" % kind)
    return out, fails


def main():
    chrome = find_chrome()
    if not chrome:
        sys.exit("check_last_done: no Chrome found. Set CHROME=/path/to/chrome.")
    scens = os.environ["ONLY"].split(",") if os.environ.get("ONLY") else SCENARIOS
    pages = os.environ["PAGES"].split(",") if os.environ.get("PAGES") else list(PAGES)
    total, fails = copies()
    with tempfile.TemporaryDirectory() as td:
        shutil.copytree(os.path.join(ROOT, "assets"), os.path.join(td, "assets"))
        shutil.copytree(os.path.join(ROOT, "vendor"), os.path.join(td, "vendor"))
        for page in pages:
            for scen in scens:
                if page != "line" and scen in LINE_ONLY:
                    continue
                path = os.path.join(td, "%s_%s.html" % (page, scen))
                with open(path, "w", encoding="utf-8") as f:
                    f.write(build_page(page, scen))
                res, err = run_scenario(chrome, path, scen)
                if res is None:
                    fails.append("%s/%s: harness never reported\n%s" % (page, scen, err))
                    continue
                total += len(res["log"])
                fails += ["%s/%s: %s" % (page, scen, x) for x in res["fails"]]
    if fails:
        print("last-done guard: %d failure(s) of %d assertions\n" % (len(fails), total))
        for x in fails:
            print("  " + x)
        print("\nsee docs/last-done.md")
        return 1
    print("last-done guard: clean (%d assertions, %d scenarios on Line, %d on Prep, + copies)"
          % (total, len(scens) if "line" in pages else 0,
             len([x for x in scens if x not in LINE_ONLY]) if "prep" in pages else 0))
    return 0


if __name__ == "__main__":
    sys.exit(main())
