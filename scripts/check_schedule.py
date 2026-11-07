#!/usr/bin/env python3
"""
Behaviour guard for the weekly staff schedule (tempest_schedule.html).

Slice 2's promises (scenario "mgr"): every write happens only in manager mode, as
an upsert whose method, table, on_conflict, Prefer header and body are asserted
exactly; nothing changed = no request; a double tap sends one; a failure keeps
the picker open with the reason and changes nothing on the page; a retry sends
the same upsert on the same key; a quiet reload in flight cannot paint over a
save; both text boxes measure 16px; the empty-box count is right.

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
SCENARIOS = ("ok", "monthend", "yearend", "fail", "empty", "mgr")


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
    # week of Oct 25: history for the quick buttons
    {"person_id": 2, "work_date": "2026-10-26", "kind": "shift", "shift_text": "11am-CL", "training": False, "updated_at": "2026-10-24T20:00:00Z"},
    {"person_id": 2, "work_date": "2026-10-27", "kind": "shift", "shift_text": "11am-CL", "training": False, "updated_at": "2026-10-24T20:00:00Z"},
    {"person_id": 2, "work_date": "2026-10-28", "kind": "shift", "shift_text": "11am-CL", "training": False, "updated_at": "2026-10-24T20:00:00Z"},
    {"person_id": 6, "work_date": "2026-10-26", "kind": "shift", "shift_text": "6pm-CL", "training": False, "updated_at": "2026-10-24T20:00:00Z"},
    {"person_id": 6, "work_date": "2026-10-27", "kind": "shift", "shift_text": "6pm-CL", "training": False, "updated_at": "2026-10-24T20:00:00Z"},
    {"person_id": 5, "work_date": "2026-10-28", "kind": "shift", "shift_text": "6pm-CL", "training": False, "updated_at": "2026-10-24T20:00:00Z"},
    {"person_id": 1, "work_date": "2026-10-28", "kind": "off", "shift_text": None, "training": False, "updated_at": "2026-10-24T20:00:00Z"},
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
    "mgr": [2026, 10, 17, 17, 30],
}

GATE_RE = re.compile(r"window\.location\.replace\('index\.html'\)")

HARNESS = r"""
<script>
/* ---- test harness: installed BEFORE the page script parses ---- */
(function(){
  var SCEN=(location.hash||'#ok').slice(1);
  var FX=__FIXTURES__;
  try{localStorage.removeItem('boxkitchen_schedule_view');}catch(e){}
  /* manager mode is entered as staff do after the PIN once: the session flag, then the switch. The PIN is never typed. */
  try{if(SCEN==='mgr')sessionStorage.setItem('boxkitchen_mgr','1');else sessionStorage.removeItem('boxkitchen_mgr');}catch(e){}
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
  var reqs=[],plan={schedule_people:SCEN==='fail'?['err']:[]},held=[],stamp=0;
  /* write fates, consumed in order: 'err0' no answer; 'e400' refused; 'hold' answer kept until release() */
  window.__h={scen:SCEN,reqs:reqs,fails:[],log:[],tables:T,plan:plan,nextWrite:[],
    release:function(){var h=held.splice(0);h.forEach(function(f){f();});return h.length;}};

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
  Stub.prototype.setRequestHeader=function(k,v){(this.hd=this.hd||{})[k]=v;};
  Stub.prototype.send=function(body){
    var self=this,t=table(this.u),q=params(this.u);
    reqs.push({m:this.m,t:t,u:this.u,body:body,prefer:(this.hd||{}).Prefer||null});
    if(this.m==='POST'&&(t==='schedule_shifts'||t==='schedule_day_notes')){
      var wf=window.__h.nextWrite.shift()||'ok';
      var go=function(){
        if(wf==='err0'){self.onerror&&self.onerror();return;}
        if(wf==='e400'){self.status=400;self.responseText='{"message":"bad"}';self.onload&&self.onload();return;}
        var b=JSON.parse(body),keys=t==='schedule_shifts'?['person_id','work_date']:['location','note_date'];
        var row=T[t].filter(function(r){return keys.every(function(k){return r[k]===b[k];});})[0];
        if(!row){row={};T[t].push(row);}
        Object.keys(b).forEach(function(k){row[k]=b[k];});
        row.updated_at=new RD(Date.UTC(2026,10,18,2,0,++stamp)).toISOString();   /* the trigger's job */
        self.status=201;self.responseText=JSON.stringify([row]);self.onload&&self.onload();
      };
      if(wf==='hold'){held.push(go);return;}
      setTimeout(go,5);return;
    }
    if(this.m!=='GET'){setTimeout(function(){self.status=405;self.responseText='[]';self.onload&&self.onload();},5);return;}
    var fate=(plan[t]||[]).shift();
    /* rows are taken when ASKED, so a held answer is stale by the time it lands */
    var rows=JSON.parse(JSON.stringify((T[t]||[]).filter(function(r){return q.every(function(p){return match(r,p[0],p[1]);});})));
    var answer=function(){
      if(fate==='err'){self.onerror&&self.onerror();return;}
      self.status=200;self.responseText=JSON.stringify(rows);self.onload&&self.onload();
    };
    if(fate==='hold'){held.push(answer);return;}
    setTimeout(answer,5);
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
      if(H.scen!=='mgr')ok(H.scen+': no request but GET, ever',writes().length===0,JSON.stringify(writes()));
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
      ok('ok (staff): no box or note buttons anywhere',all('.sched-boxbtn,.sched-cellbtn,.sched-notebtn').length===0);
      ok('ok (staff): no empty-box count',getComputedStyle(byId('mgrCount')).display==='none'&&txt(byId('mgrCount'))==='');
      ok('ok (staff): exactly Slice 1\'s four reads, no four-week read',reads().length===4&&!reads().some(function(r){return /kind=eq\.shift/.test(r.u);}),reads().map(function(r){return r.t;}).join());
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
      ok('ok (staff): no buttons in Week either',all('.sched-boxbtn,.sched-cellbtn,.sched-notebtn').length===0);
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


  if(H.scen==='mgr'){
    var T=H.tables;
    function body(r){return r?JSON.parse(r.body):null;}
    function same(a,b){function k(o){return JSON.stringify(o,Object.keys(o||{}).sort());}return k(a)===k(b);}
    function posts(){return writes();}
    function lastPost(){var w=writes();return w[w.length-1];}
    var PREFER='resolution=merge-duplicates,return=representation';
    function isUpsert(r,t,conflict){return !!r&&r.m==='POST'&&r.t===t&&r.u.split('?')[1]==='on_conflict='+conflict&&r.prefer===PREFER;}
    function box(n){var r=rowFor(n);return r&&r.box;}
    function open(n){var b=box(n);b&&b.click();}
    function picks(){return all('#boxPicks .sched-pick').map(txt);}
    function pressed(){return all('#boxPicks .sched-pick').filter(function(b){return b.getAttribute('aria-pressed')==='true';}).map(txt);}
    function tap(label){var b=all('#boxPicks .sched-pick').filter(function(x){return txt(x)===label;})[0];b&&b.click();return !!b;}
    function modalOpen(id){return byId(id).classList.contains('show');}
    function other(v){var i=byId('boxOther');i.value=v;i.dispatchEvent(new Event('input'));}
    function rowsFor(pid,d){return T.schedule_shifts.filter(function(r){return r.person_id===pid&&r.work_date===d;});}
    var D='2026-11-17',n0;
    step(function(){return 200;});
    step(function(){
      ok('mgr: staff view first, no write and no four-week read',all('.sched-boxbtn').length===0&&!reads().some(function(r){return /kind=eq\.shift/.test(r.u);}));
      byId('mgrSwitch').click();
      ok('mgr: the session flag unlocks without the PIN box',!byId('pinModal').classList.contains('show')&&byId('mgrSwitch').classList.contains('on'));
      return 50;
    });
    step(function(){
      var q=reads().filter(function(r){return /kind=eq\.shift/.test(r.u);});
      ok('mgr: one four-week read, this week and the three before',q.length===1&&/work_date=gte\.2026-10-25/.test(q[0].u)&&/work_date=lte\.2026-11-21/.test(q[0].u)&&/person_id=in\.\(1,2,3,5,6,9\)/.test(q[0].u),q.map(function(r){return r.u;}).join(' '));
      ok('mgr: every box in Day is a button, labelled',dayRows().every(function(r){return r.box.tagName==='BUTTON';})&&box('Pablo').getAttribute('aria-label')==='Change Pablo, Tuesday 11/17');
      ok('mgr: the empty-box count (5 active × 7, 5 filled)',txt(byId('mgrCount'))==='30 boxes not filled yet',txt(byId('mgrCount')));
      ok('mgr: a Games & events line in manager mode',/^Games & events: 49ers <home> & party$/.test(txt(document.querySelector('.sched-notebtn'))),txt(document.querySelector('.sched-notebtn')));
      n0=writes().length;
      open('Jose V.');
    });
    step(function(){
      ok('mgr: the picker title and what the box says now',txt(byId('boxTitle'))==='Jose V. · Tuesday · Martes 11/17'&&txt(byId('boxNow'))==='Now: 9am-3pm',txt(byId('boxTitle'))+' / '+txt(byId('boxNow')));
      ok('mgr: quick buttons, day crew: four-week favourites first, topped up from the defaults, 8 at most',
         picks().join('|')==='OFF|REQUEST|11am-CL|9am-3pm|10am<i>-</i>4pm & on|10am-5pm|10am-3pm|10am-4pm|9am-2pm|9:30am-3pm',picks().join('|'));
      ok('mgr: the current value starts selected',pressed().join()==='9am-3pm',pressed().join());
      var o=byId('boxOther'),n=byId('noteInput');
      ok('mgr: the Other box renders at 16px or more',parseFloat(getComputedStyle(o).fontSize)>=16,getComputedStyle(o).fontSize);
      ok('mgr: Other box attributes',o.maxLength===20&&o.getAttribute('autocomplete')==='off'&&o.getAttribute('autocapitalize')==='off');
      byId('boxSave').click();
    });
    step(function(){return 30;});
    step(function(){
      ok('mgr: nothing changed + Save = no request, picker closes',writes().length===n0&&!modalOpen('boxModal'));
      open('Tom <b>&amp;</b> Co');
    });
    step(function(){
      ok('mgr: an empty box: "Now: empty", nothing selected, Clear disabled',txt(byId('boxNow'))==='Now: empty'&&pressed().length===0&&byId('boxClear').disabled);
      ok('mgr: Training is unusable with nothing selected',byId('boxTrain').disabled);
      byId('boxSave').click();
    });
    step(function(){return 30;});
    step(function(){
      ok('mgr: an empty box + Save with nothing picked = no request',writes().length===n0&&!modalOpen('boxModal'));
      open('Tom <b>&amp;</b> Co');tap('11am-CL');
      ok('mgr: tapping selects, by fill',pressed().join()==='11am-CL'&&getComputedStyle(all('#boxPicks .sched-pick')[2]).backgroundColor!==getComputedStyle(all('#boxPicks .sched-pick')[0]).backgroundColor);
      ok('mgr: a tap alone saves nothing',writes().length===n0);
      byId('boxSave').click();
    });
    step(function(){return 50;});
    step(function(){
      var r=lastPost();
      ok('mgr: a quick shift is one upsert on (person_id, work_date)',writes().length===n0+1&&isUpsert(r,'schedule_shifts','person_id,work_date'),JSON.stringify(r));
      ok('mgr: ...whose body is exactly the box',same(body(r),{person_id:3,work_date:D,kind:'shift',shift_text:'11am-CL',training:false}),r&&r.body);
      ok('mgr: ...and never updated_at',r&&!('updated_at' in body(r)));
      ok('mgr: the box shows it, the picker closed, a toast',txt(box('Tom <b>&amp;</b> Co'))==='11am-CL'&&!modalOpen('boxModal')&&/Saved/.test(txt(byId('toast'))));
      ok('mgr: the count drops by one',txt(byId('mgrCount'))==='29 boxes not filled yet',txt(byId('mgrCount')));
      ok('mgr: "Updated" moves to the save',updated()===expectUpdated(T.schedule_shifts.filter(function(x){return x.person_id===3&&x.work_date===D;})[0].updated_at),updated());
      open('Rubidia');
    });
    step(function(){
      ok('mgr: OFF starts selected; Training unusable on OFF',pressed().join()==='OFF'&&byId('boxTrain').disabled);
      tap('REQUEST');byId('boxSave').click();return 50;
    });
    step(function(){
      ok('mgr: REQUEST payload',same(body(lastPost()),{person_id:2,work_date:D,kind:'request',shift_text:null,training:false}),lastPost().body);
      ok('mgr: REQUEST reads REQUEST',txt(box('Rubidia'))==='REQUEST');
      open('Rubidia');tap('OFF');byId('boxSave').click();return 50;
    });
    step(function(){
      ok('mgr: OFF payload',same(body(lastPost()),{person_id:2,work_date:D,kind:'off',shift_text:null,training:false}),lastPost().body);
      ok('mgr: one row for the box after three saves',rowsFor(2,D).length===1);
      open('Pablo');
    });
    step(function(){
      ok('mgr: quick buttons, night crew',picks().join('|')==='OFF|REQUEST|6pm-CL|4pm-CL|5pm-CL|10am-4pm|4:30pm-CL|4pm-10',picks().join('|'));
      tap('6pm-CL');
      ok('mgr: Training usable once a shift is picked',!byId('boxTrain').disabled);
      byId('boxTrain').click();
      ok('mgr: Training on is a fill, aria-pressed',byId('boxTrain').getAttribute('aria-pressed')==='true');
      tap('OFF');
      ok('mgr: choosing OFF turns Training off',byId('boxTrain').getAttribute('aria-pressed')==='false'&&byId('boxTrain').disabled);
      tap('6pm-CL');byId('boxTrain').click();byId('boxSave').click();return 50;
    });
    step(function(){
      ok('mgr: shift + Training payload',same(body(lastPost()),{person_id:6,work_date:D,kind:'shift',shift_text:'6pm-CL',training:true}),lastPost().body);
      ok('mgr: Training reads under the shift',txt(box('Pablo'))==='6pm-CLTRAINING');
      open('Jose V.');other('4 pm-cl');
      ok('mgr: typing in Other selects it (quick buttons let go)',pressed().length===0);
      var e=new KeyboardEvent('keydown',{key:'Enter',bubbles:true});byId('boxOther').dispatchEvent(e);return 50;
    });
    step(function(){
      ok('mgr: Other "4 pm-cl" saves as 4pm-CL (Enter = Save)',same(body(lastPost()),{person_id:1,work_date:D,kind:'shift',shift_text:'4pm-CL',training:false}),lastPost().body);
      open('Eddy V.');
      ok('mgr: a box with Training opens with Training on',byId('boxTrain').getAttribute('aria-pressed')==='true'&&pressed().join()==='4pm-CL');
      other('10 AM – 4 PM');byId('boxSave').click();return 50;
    });
    step(function(){
      ok('mgr: Other "10 AM – 4 PM" saves as 10am-4pm, Training kept',same(body(lastPost()),{person_id:5,work_date:D,kind:'shift',shift_text:'10am-4pm',training:true}),lastPost().body);
      open('Tom <b>&amp;</b> Co');other(' Off ');byId('boxSave').click();return 50;
    });
    step(function(){
      ok('mgr: Other "Off" saves as kind off, not a shift',same(body(lastPost()),{person_id:3,work_date:D,kind:'off',shift_text:null,training:false}),lastPost().body);
      ok('mgr: ...and reads OFF in grey',!!box('Tom <b>&amp;</b> Co').querySelector('.sched-off'));
      open('Tom <b>&amp;</b> Co');other('REQUEST');byId('boxSave').click();return 50;
    });
    step(function(){
      ok('mgr: Other "REQUEST" saves as kind request',same(body(lastPost()),{person_id:3,work_date:D,kind:'request',shift_text:null,training:false}),lastPost().body);
      open('Tom <b>&amp;</b> Co');
      ok('mgr: Clear usable on a filled box',!byId('boxClear').disabled);
      byId('boxClear').click();return 50;
    });
    step(function(){
      ok('mgr: Clear sends kind null (the row stays, no delete)',same(body(lastPost()),{person_id:3,work_date:D,kind:null,shift_text:null,training:false})&&isUpsert(lastPost(),'schedule_shifts','person_id,work_date'),lastPost().body);
      ok('mgr: a cleared box reads empty, not OFF',isEmptyBox(box('Tom <b>&amp;</b> Co'))&&rowsFor(3,D).length===1&&rowsFor(3,D)[0].kind===null);
      ok('mgr: the count counts it again',txt(byId('mgrCount'))==='30 boxes not filled yet',txt(byId('mgrCount')));
      /* double tap while in flight */
      n0=writes().length;H.nextWrite.push('hold');
      open('Jose V.');tap('10am-5pm');byId('boxSave').click();byId('boxSave').click();saveBox();
    });
    step(function(){return 30;});
    step(function(){
      ok('mgr: double tap while saving sends exactly one request',writes().length===n0+1,writes().length-n0);
      ok('mgr: buttons disabled while saving',byId('boxSave').disabled&&byId('boxClear').disabled&&all('#boxPicks button').every(function(b){return b.disabled;}));
      byId('boxModal').click();
      ok('mgr: the backdrop cannot close a save in flight',modalOpen('boxModal'));
      H.release();return 30;
    });
    step(function(){
      ok('mgr: the held save lands',txt(box('Jose V.'))==='10am-5pm'&&!modalOpen('boxModal'));
      /* failure: no answer */
      H.nextWrite.push('err0');n0=writes().length;
      open('Rubidia');tap('9am-2pm');byId('boxSave').click();return 50;
    });
    step(function(){
      ok('mgr: no answer: picker stays open with the reason',modalOpen('boxModal')&&txt(byId('boxErr'))==='No answer. Check the wifi and try again.'&&byId('boxErr').classList.contains('show'));
      ok('mgr: ...the box on the page unchanged',txt(box('Rubidia'))==='OFF');
      ok('mgr: ...the buttons work again',!byId('boxSave').disabled&&pressed().join()==='9am-2pm');
      H.firstFail=writes()[n0];
      H.nextWrite.push('e400');byId('boxSave').click();return 50;
    });
    step(function(){
      ok('mgr: refused: the error status is shown',modalOpen('boxModal')&&txt(byId('boxErr'))==='Not saved (error 400). Try again.',txt(byId('boxErr')));
      ok('mgr: ...the box on the page still unchanged',txt(box('Rubidia'))==='OFF');
      byId('boxSave').click();return 50;
    });
    step(function(){
      var r=lastPost(),f=H.firstFail;
      ok('mgr: the retry is the same upsert on the same key',!!f&&r.u===f.u&&r.body===f.body&&r.prefer===f.prefer);
      ok('mgr: ...and the box is one row',rowsFor(2,D).length===1&&rowsFor(2,D)[0].shift_text==='9am-2pm'&&txt(box('Rubidia'))==='9am-2pm');
      ok('mgr: the error line is gone after a save',!byId('boxErr').classList.contains('show'));
      /* the quiet-reload race: a reload asks for shifts (stale), a save lands, the stale answer arrives */
      H.plan.schedule_shifts=['hold'];
      document.dispatchEvent(new Event('visibilitychange'));return 30;
    });
    step(function(){
      open('Pablo');tap('5pm-CL');byId('boxSave').click();return 50;
    });
    step(function(){
      ok('mgr (race): the save shows',txt(box('Pablo'))==='5pm-CLTRAINING');
      H.release();return 50;
    });
    step(function(){
      ok('mgr (race): the reload\'s older answer cannot paint over the save',txt(box('Pablo'))==='5pm-CLTRAINING',txt(box('Pablo')));
      /* day notes */
      n0=writes().length;
      document.querySelector('.sched-notebtn').click();
    });
    step(function(){
      var n=byId('noteInput');
      ok('mgr: the note picker opens on the day with its note',modalOpen('noteModal')&&txt(byId('noteTitle'))==='Games & events · Tuesday 11/17'&&n.value==='49ers <home> & party');
      ok('mgr: the note box renders at 16px or more',parseFloat(getComputedStyle(n).fontSize)>=16,getComputedStyle(n).fontSize);
      ok('mgr: note box maxlength 60',n.maxLength===60);
      all('#notePicks .sched-pick').filter(function(b){return txt(b)==='Football';})[0].click();
      ok('mgr: a quick word adds to the text and saves nothing',n.value==='49ers <home> & party Football'&&writes().length===n0);
      n.value='  49ers   home 1:25 ';byId('noteSave').click();return 50;
    });
    step(function(){
      var r=lastPost();
      ok('mgr: a day note is one upsert on (location, note_date), tidied',isUpsert(r,'schedule_day_notes','location,note_date')&&same(body(r),{location:'Tempest',note_date:D,note:'49ers home 1:25'}),JSON.stringify(r));
      ok('mgr: the note shows',txt(document.querySelector('.sched-notebtn'))==='Games & events: 49ers home 1:25');
      document.querySelector('.sched-notebtn').click();byId('noteSave').click();return 30;
    });
    step(function(){
      ok('mgr: an unchanged note + Save = no request',writes().length===n0+1&&!modalOpen('noteModal'));
      document.querySelector('.sched-notebtn').click();byId('noteClear').click();return 50;
    });
    step(function(){
      ok('mgr: Clear sends an empty note',same(body(lastPost()),{location:'Tempest',note_date:D,note:''}),lastPost().body);
      ok('mgr: an empty note offers "+ Add game or event"',txt(document.querySelector('.sched-notebtn'))==='+ Add game or event');
      H.nextWrite.push('err0');
      document.querySelector('.sched-notebtn').click();byId('noteInput').value='Event';byId('noteSave').click();return 50;
    });
    step(function(){
      ok('mgr: a failed note save keeps its picker open with the reason',modalOpen('noteModal')&&txt(byId('noteErr'))==='No answer. Check the wifi and try again.'&&txt(document.querySelector('.sched-notebtn'))==='+ Add game or event');
      byId('noteModal').click();
      ok('mgr: the backdrop closes a picker that is not saving',!modalOpen('noteModal'));
      byId('viewWeekBtn').click();
    });
    step(function(){
      var cb=all('.sched-cellbtn');
      ok('mgr: Week: a button per box (5 × 7) and per day note (7)',cb.length===42,cb.length);
      ok('mgr: Week buttons at least 44px high',cb.every(function(b){return b.getBoundingClientRect().height>=44;}),Math.min.apply(null,cb.map(function(b){return b.getBoundingClientRect().height;})));
      ok('mgr: Week box button labelled',cells('Pablo')[2].querySelector('button').getAttribute('aria-label')==='Change Pablo, Tuesday 11/17');
      cells('Pablo')[0].querySelector('button').click();
    });
    step(function(){
      ok('mgr: a Week box opens the picker for that day',txt(byId('boxTitle'))==='Pablo · Sunday · Domingo 11/15');
      byId('boxModal').click();
      document.querySelectorAll('.date-arrow')[0].click();return 100;
    });
    step(function(){
      ok('mgr: a retired person\'s box is tappable in the week they show',!!cells('Old Timer')[2]&&!!cells('Old Timer')[2].querySelector('button'));
      ok('mgr: the count is active people only',txt(byId('mgrCount'))==='35 boxes not filled yet',txt(byId('mgrCount')));
      byId('mgrSwitch').click();
    });
    step(function(){
      ok('mgr: Manager off: no buttons, no count',all('.sched-boxbtn,.sched-cellbtn,.sched-notebtn').length===0&&getComputedStyle(byId('mgrCount')).display==='none');
      ok('mgr: every write was an upsert to the two box tables',writes().every(function(r){return r.m==='POST'&&(isUpsert(r,'schedule_shifts','person_id,work_date')||isUpsert(r,'schedule_day_notes','location,note_date'));}));
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
