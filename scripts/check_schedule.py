#!/usr/bin/env python3
"""
Behaviour guard for the weekly staff schedule (tempest_schedule.html).

Slice 1's promises: the page only ever READS; a week renders right in both the
Day and the Week view (a shift, OFF, REQUEST, Training and an empty box each
read differently, and empty never reads as OFF); the right dates sit under the
right days across a month end (Nov 29 - Dec 5, 2026) and a year end (Dec 27,
2026 - Jan 2, 2027); a retired person shows only in a week where they have a
box; text from the database is escaped; "Updated ..." shows the latest save
and hides when there is none; a failed load offers Try again.

As check_inventory.py does it: load the REAL page, neutralise the site-password
redirect, install a stub XMLHttpRequest (and a fixed clock) BEFORE the page's
own <script> parses, drive it in headless Chrome and assert on the DOM and on
every request. Nothing can leave the machine.

Chrome runs with TZ=America/Los_Angeles and the clock at 5:30 PM, when UTC is
already tomorrow: a date key built with toISOString() would land a day late.

    python3 scripts/check_schedule.py          # ONLY=ok,monthend to run a few

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

CHROME_CANDIDATES = [
    "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
    "/Applications/Chromium.app/Contents/MacOS/Chromium",
    "/usr/bin/google-chrome",
    "/usr/bin/google-chrome-stable",
    "/usr/bin/chromium",
    "/usr/bin/chromium-browser",
]
PAGE = "tempest_schedule.html"
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCENARIOS = ("ok", "monthend", "yearend", "fail", "empty")


def find_chrome():
    env = os.environ.get("CHROME")
    if env:
        return env if os.path.exists(env) else shutil.which(env)
    for p in CHROME_CANDIDATES:
        if os.path.exists(p):
            return p
    for n in ("google-chrome", "google-chrome-stable", "chromium", "chromium-browser", "chrome"):
        found = shutil.which(n)
        if found:
            return found
    return None

# ---------------------------------------------------------------- fixtures --
# Served in the order the page asks for (crew, then sort_order).
PEOPLE = [
    {"id": 1, "location": "Tempest", "name": "Jose V.", "crew": "day", "sort_order": 10, "active": True},
    {"id": 2, "location": "Tempest", "name": "Rubidia", "crew": "day", "sort_order": 20, "active": True},
    {"id": 3, "location": "Tempest", "name": "Tom <b>&amp;</b> Co", "crew": "day", "sort_order": 30, "active": True},
    {"id": 5, "location": "Tempest", "name": "Eddy V.", "crew": "night", "sort_order": 10, "active": True},
    {"id": 6, "location": "Tempest", "name": "Pablo", "crew": "night", "sort_order": 20, "active": True},
    # retired: a box only in the week of Nov 8
    {"id": 9, "location": "Tempest", "name": "Old Timer", "crew": "night", "sort_order": 90, "active": False},
]
SHIFTS = [
    # Tuesday 11/17
    {"person_id": 1, "work_date": "2026-11-17", "kind": "shift", "shift_text": "9am-3pm", "training": False, "updated_at": "2026-11-14T23:12:00Z"},
    {"person_id": 2, "work_date": "2026-11-17", "kind": "off", "shift_text": None, "training": False, "updated_at": "2026-11-14T22:00:00Z"},
    {"person_id": 5, "work_date": "2026-11-17", "kind": "shift", "shift_text": "4pm-CL", "training": True, "updated_at": "2026-11-14T22:00:00Z"},
    {"person_id": 6, "work_date": "2026-11-17", "kind": "request", "shift_text": None, "training": False, "updated_at": "2026-11-14T22:00:00Z"},
    # Sunday 11/15: a shift with markup in it
    {"person_id": 1, "work_date": "2026-11-15", "kind": "shift", "shift_text": "10am<i>-</i>4pm & on", "training": False, "updated_at": "2026-11-14T21:00:00Z"},
    # a cleared box (kind null) is empty, and its save time still counts
    {"person_id": 3, "work_date": "2026-11-18", "kind": None, "shift_text": None, "training": False, "updated_at": "2026-11-13T21:00:00Z"},
    # week of Nov 8: the retired person's box
    {"person_id": 9, "work_date": "2026-11-10", "kind": "shift", "shift_text": "5pm-CL", "training": False, "updated_at": "2026-11-07T20:00:00Z"},
]
NOTES = [
    {"location": "Tempest", "note_date": "2026-11-17", "note": "49ers <home> & party", "updated_at": "2026-11-15T01:45:00Z"},
    {"location": "Tempest", "note_date": "2026-11-19", "note": "   ", "updated_at": "2026-11-13T20:00:00Z"},
]
STANDING = [
    {"id": 1, "location": "Tempest", "label": "Trash out by 8pm", "weekdays": [0, 2, 4], "sort_order": 10, "active": True},
    {"id": 2, "location": "Tempest", "label": "Compost out", "weekdays": [1], "sort_order": 20, "active": True},
    {"id": 3, "location": "Tempest", "label": "Retired note", "weekdays": [2], "sort_order": 30, "active": False},
]
# the clock each scenario runs at, local (Los Angeles) time: y, m(0-based), d, h, min
CLOCKS = {
    "ok": [2026, 10, 17, 17, 30],        # Tue Nov 17, 5:30 PM = already Wed in UTC
    "monthend": [2026, 11, 1, 17, 30],   # Tue Dec 1
    "yearend": [2026, 11, 31, 17, 30],   # Thu Dec 31 = already 2027 in UTC
    "fail": [2026, 10, 17, 9, 0],
    "empty": [2026, 10, 17, 9, 0],
}

GATE_RE = re.compile(r"window\.location\.replace\('index\.html'\)")

HARNESS = r"""
<script>
/* ---- test harness: installed BEFORE the page script parses ---- */
(function(){
  var SCEN=(location.hash||'#ok').slice(1);
  var FX=__FIXTURES__;
  try{localStorage.removeItem('boxkitchen_schedule_view');}catch(e){}
  /* a fixed clock: new Date() and Date.now() say the scenario's moment */
  var RD=Date,c=FX.clocks[SCEN],NOW=new RD(c[0],c[1],c[2],c[3],c[4]).getTime();
  function FD(){
    if(!(this instanceof FD))return new RD(NOW).toString();
    if(!arguments.length)return new RD(NOW);
    var a=[null].concat(Array.prototype.slice.call(arguments));
    return new (Function.prototype.bind.apply(RD,a))();
  }
  FD.prototype=RD.prototype;FD.now=function(){return NOW;};FD.parse=RD.parse;FD.UTC=RD.UTC;
  window.Date=FD;

  var T={schedule_people:SCEN==='empty'?[]:FX.people,schedule_shifts:SCEN==='empty'?[]:FX.shifts,
         schedule_day_notes:SCEN==='empty'?[]:FX.notes,schedule_standing:FX.standing};
  var reqs=[],plan={schedule_people:SCEN==='fail'?['err']:[]};
  window.__h={scen:SCEN,reqs:reqs,fails:[],log:[],tables:T};

  function table(u){var m=u.match(/\/rest\/v1\/([a-z_]+)/);return m?m[1]:'';}
  function params(u){var out=[],s=u.split('?')[1]||'';s.split('&').forEach(function(kv){var i=kv.indexOf('=');if(i>0)out.push([kv.slice(0,i),decodeURIComponent(kv.slice(i+1))]);});return out;}
  function match(r,k,v){
    if(k==='select'||k==='order'||k==='limit')return true;
    if(!(k in r))return true;
    var x=r[k];
    if(v.indexOf('eq.')===0)return String(x)===v.slice(3);
    if(v.indexOf('gte.')===0)return String(x)>=v.slice(4);
    if(v.indexOf('lte.')===0)return String(x)<=v.slice(4);
    if(v.indexOf('in.(')===0)return v.slice(4,-1).split(',').indexOf(String(x))>=0;
    return true;
  }
  function Stub(){this.readyState=0;this.status=0;this.responseText='';this.timeout=0;}
  Stub.prototype.open=function(m,u){this.m=m;this.u=u;};
  Stub.prototype.setRequestHeader=function(){};
  Stub.prototype.send=function(body){
    var self=this,t=table(this.u),q=params(this.u);
    reqs.push({m:this.m,t:t,u:this.u,body:body});
    if(this.m!=='GET'){setTimeout(function(){self.status=405;self.responseText='[]';self.onload&&self.onload();},5);return;}
    var fate=(plan[t]||[]).shift();
    setTimeout(function(){
      if(fate==='err'){self.onerror&&self.onerror();return;}
      var rows=(T[t]||[]).filter(function(r){return q.every(function(p){return match(r,p[0],p[1]);});});
      self.status=200;self.responseText=JSON.stringify(rows);self.onload&&self.onload();
    },5);
  };
  window.XMLHttpRequest=Stub;
})();
</script>
"""

RUNNER = r"""
<script>
(function(){
  var H=window.__h,F=H.fails;
  function ok(name,cond,extra){if(!cond)F.push(name+(extra!=null?' :: '+extra:''));H.log.push((cond?'PASS ':'FAIL ')+name);}
  function byId(id){return document.getElementById(id);}
  function all(sel,root){return Array.prototype.slice.call((root||document).querySelectorAll(sel));}
  function txt(el){return el?el.textContent.replace(/\s+/g,' ').trim():'';}
  function writes(){return H.reqs.filter(function(r){return r.m!=='GET';});}
  function reads(t){return H.reqs.filter(function(r){return r.m==='GET'&&(!t||r.t===t);});}
  function label(){return txt(byId('weekLabel'));}
  function strip(){return all('#dayStrip .sched-day').map(function(b){return txt(b.querySelector('.dd'));});}
  function dayHead(){return txt(document.querySelector('.sched-dayhead'));}
  function dayRows(){return all('.sched-row').map(function(r){return {name:txt(r.querySelector('.sched-name')),box:r.querySelector('.sched-box')};});}
  function rowFor(n){return dayRows().filter(function(r){return r.name===n;})[0];}
  function notes(){return all('.sched-note').map(txt);}
  function crews(){return all('.cat-label').map(txt);}
  function heads(){return all('.sched-grid thead th').slice(1);}
  function gridRow(n){return all('.sched-grid tbody tr').filter(function(tr){return txt(tr.querySelector('th'))===n;})[0];}
  function cells(n){var r=gridRow(n);return r?all('td',r):[];}
  function updated(){return txt(byId('updatedLine'));}
  function expectUpdated(iso){var d=new Date(iso),h=d.getHours(),ap=h<12?'AM':'PM';h=h%12||12;
    return 'Updated '+['Sun','Mon','Tue','Wed','Thu','Fri','Sat'][d.getDay()]+' '+h+':'+String(d.getMinutes()).padStart(2,'0')+' '+ap;}
  function isEmptyBox(el){var s=el&&el.querySelector('.sched-empty');return !!s&&s.getAttribute('aria-label')==='not scheduled yet'&&!/OFF/.test(el.textContent);}

  var steps=[];
  function step(fn){steps.push(fn);}
  function run(){
    if(!steps.length){
      ok(H.scen+': no request but GET, ever',writes().length===0,JSON.stringify(writes()));
      var out=document.createElement('div');out.id='harnessResults';
      out.textContent=JSON.stringify({scen:H.scen,fails:F,log:H.log});
      document.body.appendChild(out);return;
    }
    var fn=steps.shift(),wait=0;
    try{wait=fn();}catch(e){F.push('threw in step: '+(e&&e.message));}
    setTimeout(run,typeof wait==='number'?wait:0);
  }
  /* wrap the page at phone width, as the other guards do */
  document.body.style.width='390px';

  if(H.scen==='ok'){
    step(function(){return 200;});
    step(function(){
      ok('ok: the week is Sunday to Saturday',label()==='Nov 15 – 21, 2026',label());
      ok('ok: opens on Day view',byId('viewDayBtn').classList.contains('active')&&!byId('viewWeekBtn').classList.contains('active'));
      ok('ok: the day strip is the seven dates',strip().join(',')==='15,16,17,18,19,20,21',strip().join(','));
      var act=all('#dayStrip .sched-day.active'),tod=all('#dayStrip .sched-day.today');
      ok('ok: today is chosen and marked, in local time (5:30 PM is not tomorrow)',act.length===1&&tod.length===1&&act[0]===tod[0]&&txt(act[0].querySelector('.dd'))==='17');
      ok('ok: the day heading',dayHead()==='TUESDAY · MARTES · 11/17',dayHead());
      ok('ok: standing note on its day, day note escaped; other days\' and retired notes absent',
         notes().join('|')==='Trash out by 8pm|49ers <home> & party',notes().join('|'));
      ok('ok: day crew then night crew',crews().join('|')==='DAY CREW|NIGHT CREW',crews().join('|'));
      ok('ok: people in order; retired person absent this week',
         dayRows().map(function(r){return r.name;}).join('|')==='Jose V.|Rubidia|Tom <b>&amp;</b> Co|Eddy V.|Pablo',dayRows().map(function(r){return r.name;}).join('|'));
      ok('ok: a name with markup is text, not markup',all('.sched-name b').length===0);
      var j=rowFor('Jose V.').box,r=rowFor('Rubidia').box,e=rowFor('Eddy V.').box,p=rowFor('Pablo').box,t=rowFor('Tom <b>&amp;</b> Co').box;
      ok('ok: a shift reads as its text, in ink',txt(j)==='9am-3pm'&&!!j.querySelector('.sched-shift'));
      ok('ok: OFF reads OFF, grey',txt(r)==='OFF'&&!!r.querySelector('.sched-off'));
      ok('ok: OFF is grey, the shift is ink',getComputedStyle(r.querySelector('.sched-off')).color!==getComputedStyle(j.querySelector('.sched-shift')).color);
      ok('ok: REQUEST reads REQUEST, on the highlighter',txt(p)==='REQUEST'&&getComputedStyle(p.querySelector('.sched-req')).backgroundColor!=='rgba(0, 0, 0, 0)');
      ok('ok: Training is a word under the shift',txt(e)==='4pm-CLTRAINING'&&!!e.querySelector('.sched-shift + .sched-train'));
      ok('ok: an empty box reads — and says "not scheduled yet", never OFF',isEmptyBox(t)&&txt(t)==='—',t&&t.innerHTML);
      ok('ok: "Updated" is the latest save, notes included, in local time',updated()===expectUpdated('2026-11-15T01:45:00Z'),updated());
      var q=reads('schedule_shifts')[0];
      ok('ok: shifts asked for by every person (retired too) and this week\'s dates',
         !!q&&/person_id=in\.\(1,2,3,5,6,9\)/.test(q.u)&&/work_date=gte\.2026-11-15/.test(q.u)&&/work_date=lte\.2026-11-21/.test(q.u),q&&q.u);
      ok('ok: every read is Tempest\'s',reads().filter(function(r){return r.t!=='schedule_shifts';}).every(function(r){return /location=eq\.Tempest/.test(r.u);}));
      ok('ok: standing notes read active only',/active=eq\.true/.test(reads('schedule_standing')[0].u));
      all('#dayStrip .sched-day')[3].click();
    });
    step(function(){
      ok('ok: picking Wednesday shows Wednesday',dayHead()==='WEDNESDAY · MIERCOLES · 11/18',dayHead());
      ok('ok: a cleared box (kind null) is empty, not OFF',isEmptyBox(rowFor('Tom <b>&amp;</b> Co').box));
      ok('ok: a blank day note shows nothing',notes().length===0,notes().join('|'));
      all('#dayStrip .sched-day')[0].click();
    });
    step(function(){
      var j=rowFor('Jose V.').box;
      ok('ok: shift text with markup is escaped',txt(j)==='10am<i>-</i>4pm & on'&&!j.querySelector('i'),j.innerHTML);
      byId('viewWeekBtn').click();
    });
    step(function(){
      var v=null;try{v=localStorage.getItem('boxkitchen_schedule_view');}catch(e){}
      ok('ok: Week view is remembered on this device',v==='week',v);
      ok('ok: the day strip hides in Week view',getComputedStyle(byId('dayStrip')).display==='none');
      var h=heads().map(txt);
      ok('ok: column headers, English + Spanish + date',h.join('|')==='SUNDAYDOMINGO11/15|MONDAYLUNES11/16|TUESDAYMARTES11/17|WEDNESDAYMIERCOLES11/18|THURSDAYJUEVES11/19|FRIDAYVIERNES11/20|SATURDAYSABADO11/21',h.join('|'));
      ok('ok: only today\'s column header is filled',heads().filter(function(x){return x.classList.contains('today');}).map(txt).join()==='TUESDAYMARTES11/17');
      ok('ok: the name column is pinned',getComputedStyle(document.querySelector('.sched-grid .sticky')).position==='sticky');
      ok('ok: the grid scrolls inside its box, not the page',document.querySelector('.sched-gridwrap').scrollWidth>document.querySelector('.sched-gridwrap').clientWidth&&document.documentElement.scrollWidth<=window.innerWidth+1,
         document.querySelector('.sched-gridwrap').scrollWidth+' / '+document.documentElement.scrollWidth);
      ok('ok: Jose\'s week: Sun escaped shift, Tue shift',txt(cells('Jose V.')[0])==='10am<i>-</i>4pm & on'&&txt(cells('Jose V.')[2])==='9am-3pm');
      ok('ok: week Tue column: OFF / REQUEST / Training',txt(cells('Rubidia')[2])==='OFF'&&txt(cells('Pablo')[2])==='REQUEST'&&txt(cells('Eddy V.')[2])==='4pm-CLTRAINING');
      ok('ok: an empty box in Week is an empty box labelled "not scheduled yet"',isEmptyBox(cells('Rubidia')[0])&&txt(cells('Rubidia')[0])==='');
      ok('ok: retired person absent from Week too',!gridRow('Old Timer'));
      ok('ok: standing notes on their days only',cells('Trash out by 8pm').map(txt).join('|')==='Trash out by 8pm||Trash out by 8pm||Trash out by 8pm||'&&cells('Compost out').map(txt).join('|')==='|Compost out|||||');
      ok('ok: day notes row, escaped, blank shows nothing',cells('Games & events').map(txt).join('|')==='||49ers <home> & party||||'&&!document.querySelector('.sched-grid td home'),cells('Games & events').map(txt).join('|'));
      document.querySelectorAll('.date-arrow')[0].click();
    });
    step(function(){return 100;});
    step(function(){
      ok('ok: ◀ goes back a week',label()==='Nov 8 – 14, 2026',label());
      ok('ok: the retired person shows in a week where they have a box',txt(cells('Old Timer')[2])==='5pm-CL');
      ok('ok: "Updated" follows the week shown',updated()===expectUpdated('2026-11-07T20:00:00Z'),updated());
      document.querySelectorAll('.date-arrow')[0].click();
    });
    step(function(){return 100;});
    step(function(){
      ok('ok: a week with no saves hides "Updated"',updated()==='',updated());
      ok('ok: an empty week still lists the active people, every box empty',cells('Jose V.').length===7&&cells('Jose V.').every(isEmptyBox)&&!gridRow('Old Timer'));
      byId('viewDayBtn').click();
      byId('thisWeekLink').click();
    });
    step(function(){return 100;});
    step(function(){
      ok('ok: This week returns to today',label()==='Nov 15 – 21, 2026'&&dayHead()==='TUESDAY · MARTES · 11/17',label()+' / '+dayHead());
      all('#dayStrip .sched-day')[5].click();
      H.before=reads().length;
      document.dispatchEvent(new Event('visibilitychange'));
    });
    step(function(){return 100;});
    step(function(){
      ok('ok: coming back to the page reloads the week',reads().length>=H.before+4,reads().length+' vs '+H.before);
      ok('ok: ...and keeps the view and the day',byId('viewDayBtn').classList.contains('active')&&dayHead()==='FRIDAY · VIERNES · 11/20',dayHead());
      document.querySelectorAll('.date-arrow')[1].click();
    });
    step(function(){return 100;});
    step(function(){
      ok('ok: ▶ keeps the same weekday',label()==='Nov 22 – 28, 2026'&&dayHead()==='FRIDAY · VIERNES · 11/27',label()+' / '+dayHead());
      byId('mgrSwitch').click();
      ok('ok: Manager asks for the PIN',byId('pinModal').classList.contains('show'));
      ok('ok: the PIN box renders at 16px or more',parseFloat(getComputedStyle(byId('pinInput')).fontSize)>=16,getComputedStyle(byId('pinInput')).fontSize);
    });
  }

  if(H.scen==='monthend'){
    step(function(){return 200;});
    step(function(){
      ok('monthend: label across months',label()==='Nov 29 – Dec 5, 2026',label());
      ok('monthend: strip dates',strip().join(',')==='29,30,1,2,3,4,5',strip().join(','));
      ok('monthend: today is Tue 12/1',dayHead()==='TUESDAY · MARTES · 12/1',dayHead());
      var q=reads('schedule_shifts')[0];
      ok('monthend: reads Nov 29 to Dec 5',!!q&&/work_date=gte\.2026-11-29/.test(q.u)&&/work_date=lte\.2026-12-05/.test(q.u),q&&q.u);
      ok('monthend: no saves, no "Updated"',updated()==='');
      byId('viewWeekBtn').click();
    });
    step(function(){
      var h=heads().map(function(x){return x.lastChild.textContent;});
      ok('monthend: Week headers carry the right dates',h.join(',')==='11/29,11/30,12/1,12/2,12/3,12/4,12/5',h.join(','));
      ok('monthend: today\'s header is Tuesday 12/1',heads()[2].classList.contains('today'));
      document.querySelectorAll('.date-arrow')[1].click();
    });
    step(function(){return 100;});
    step(function(){ok('monthend: ▶ to the next week',label()==='Dec 6 – 12, 2026',label());});
  }

  if(H.scen==='yearend'){
    step(function(){return 200;});
    step(function(){
      ok('yearend: label across years',label()==='Dec 27, 2026 – Jan 2, 2027',label());
      ok('yearend: strip dates',strip().join(',')==='27,28,29,30,31,1,2',strip().join(','));
      ok('yearend: today is Thu 12/31 (5:30 PM is still 2026 here)',dayHead()==='THURSDAY · JUEVES · 12/31',dayHead());
      var q=reads('schedule_day_notes')[0];
      ok('yearend: reads Dec 27 to Jan 2',!!q&&/note_date=gte\.2026-12-27/.test(q.u)&&/note_date=lte\.2027-01-02/.test(q.u),q&&q.u);
      all('#dayStrip .sched-day')[6].click();
    });
    step(function(){ok('yearend: Saturday is 1/2',dayHead()==='SATURDAY · SABADO · 1/2',dayHead());});
  }

  if(H.scen==='fail'){
    step(function(){return 200;});
    step(function(){
      var b=document.querySelector('.sched-err button');
      ok('fail: a failed load says so and offers Try again, never a blank page',!!b&&/Try again/.test(b.textContent)&&/Couldn/.test(txt(byId('appBody'))));
      ok('fail: no "Updated" on a failed load',updated()==='');
      b&&b.click();
    });
    step(function(){return 200;});
    step(function(){ok('fail: Try again loads the week',dayRows().length===5&&!document.querySelector('.sched-err'),dayRows().length);});
  }

  if(H.scen==='empty'){
    step(function(){return 200;});
    step(function(){
      ok('empty: no people says so',/No one on the schedule yet/.test(txt(byId('appBody'))));
      ok('empty: no shifts asked for when there are no people',reads('schedule_shifts').length===0);
    });
  }

  window.addEventListener('load',function(){setTimeout(run,0);});
})();
</script>
"""


def build_page():
    src = open(os.path.join(ROOT, PAGE), encoding="utf-8").read()
    src, n = GATE_RE.subn("void 0 /* gate neutralised by check_schedule.py */", src)
    if n != 1:
        sys.exit("check_schedule: could not find the site-password redirect in " + PAGE)
    marker = "<script>\nvar SB="
    if marker not in src:
        sys.exit("check_schedule: could not find the page script in " + PAGE)
    fixtures = {"people": PEOPLE, "shifts": SHIFTS, "notes": NOTES, "standing": STANDING, "clocks": CLOCKS}
    src = src.replace(marker, HARNESS.replace("__FIXTURES__", json.dumps(fixtures)) + marker, 1)
    src = re.sub(r'<link rel="preconnect"[^>]*>\s*', '', src)
    src = re.sub(r'<link rel="stylesheet" href="https://fonts[^>]*>\s*', '', src)
    return src.replace("</body>", RUNNER + "</body>", 1)


RESULT_RE = re.compile(r'<div id="harnessResults">(.*?)</div>', re.S)


def run_scenario(chrome, path, scen):
    url = "file://" + path + "#" + scen
    dom = os.path.join(os.path.dirname(path), "dom-" + scen + ".html")
    err = os.path.join(os.path.dirname(path), "err-" + scen + ".txt")
    env = dict(os.environ, TZ="America/Los_Angeles")
    with open(dom, "w") as fo, open(err, "w") as fe:
        proc = subprocess.Popen(
            [chrome, "--headless=new", "--disable-gpu", "--no-sandbox",
             "--no-first-run", "--disable-extensions",
             "--disable-background-networking", "--disable-component-update",
             "--disable-default-apps", "--disable-sync",
             "--host-resolver-rules=MAP * ~NOTFOUND",
             "--user-data-dir=" + os.path.join(os.path.dirname(path), "cd-" + scen),
             "--virtual-time-budget=30000", "--dump-dom", url],
            stdout=fo, stderr=fe, env=env)
        deadline = time.time() + 120
        m = None
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
        tail = open(err, encoding="utf-8", errors="replace").read()[-600:]
        return None, "no results div after 120s\n" + tail
    body = (m.group(1).replace("&amp;", "&").replace("&lt;", "<")
            .replace("&gt;", ">").replace("&quot;", '"'))
    return json.loads(body), None


def main():
    chrome = find_chrome()
    if not chrome:
        sys.exit("check_schedule: no Chrome found. Set CHROME=/path/to/chrome.")
    page = build_page()
    fails, total = [], 0
    scens = os.environ['ONLY'].split(',') if os.environ.get('ONLY') else SCENARIOS
    with tempfile.TemporaryDirectory() as td:
        path = os.path.join(td, "schedule_under_test.html")
        with open(path, "w", encoding="utf-8") as f:
            f.write(page)
        shutil.copytree(os.path.join(ROOT, "assets"), os.path.join(td, "assets"))
        for scen in scens:
            res, err = run_scenario(chrome, path, scen)
            if res is None:
                fails.append("%s: harness never reported\n%s" % (scen, err))
                continue
            total += len(res["log"])
            fails += ["%s: %s" % (scen, x) for x in res["fails"]]
    if fails:
        print("schedule guard: %d failure(s) of %d assertions\n" % (len(fails), total))
        for x in fails:
            print("  " + x)
        print("\nsee docs/schedule.md, Slice 1")
        return 1
    print("schedule guard: clean (%d assertions, %d scenarios, %s)" % (total, len(scens), PAGE))
    return 0


if __name__ == "__main__":
    sys.exit(main())
