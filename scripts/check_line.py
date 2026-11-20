#!/usr/bin/env python3
"""
Behaviour guard for the Tempest Line page (tempest_line.html), for the Kits
Line PM link (docs/kits-line-link.md).

Slice 2's promises (the SHEET -> button):
  - on PM, exactly 7 kit rows (668 669 670 671 672 678 674) get a
    "SHEET ->" link, each to tempest_kits.html?from=line#<its slug>, no target;
    none on 673 (off the menu), 675/676 (no sheet yet), 677 (placeholder), any
    other row, or anywhere on AM;
  - it sits in .task-info after the rename input, so #ni<id>'s previous
    sibling is still the .task-name (saveN relies on it), and at a 390px
    window it is at least 44px tall and wholly inside its row (not clipped);
  - a row renamed to another dish loses its button, and never links elsewhere;
  - tapping it sends no request and opens no rename box, flips no pill, ticks
    no box, in manager mode or staff; the name and pill still work as before
    (the pill's one write is refused by the stub and never leaves the machine).
    Manager mode is set by localStorage in the harness: the PIN is never used.

Slice 1's promises:
  - tempest_line.html with no address opens on the AM list, exactly as it
    always has: no Kits station, no kit rows;
  - tempest_line.html#pm (the Kits page's "<- Line PM") opens on the PM list:
    the PM SHIFT button active, the Kits station first, all 11 kit rows;
  - opening the page, either way, sends nothing but GETs: no write of any
    kind, no write headers, no fetch or sendBeacon.

Line is live in every service and these promises cannot be checked against
the live database, so: load the REAL page with XMLHttpRequest (and fetch,
sendBeacon) replaced by a stub BEFORE any page script parses, so no request
can leave the machine, answer its reads with small fixtures (the 11 real kit
rows, read 2026-11-16, plus one other PM row and one AM row), then drive it in
headless Chrome and assert on the DOM and on every request. Same shape as
check_kits.py.

    python3 scripts/check_line.py          # ONLY=pm to run one

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
PAGE = "tempest_line.html"
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCENARIOS = ("plain", "pm", "phone", "renamed", "mgr", "staff")
HASH = {"plain": "", "pm": "pm", "phone": "pm", "renamed": "pm", "mgr": "pm", "staff": "pm"}
# Headless Chrome will not open a window narrower than 500px, so the phone
# scenario opens at 500 and pins the page to 390px wide. kitchen.css's only
# width breakpoints are 600 and 760, so 390 and 500 take the same rules.
WINDOW = {"phone": "500,900"}
# The 7 rows with a kit sheet, in Line PM order, and their addresses.
SHEETS = [[668, "mac-and-cheese"], [669, "buffalo-sauce"], [670, "pork-belly"],
          [671, "gastrique"], [672, "chicken-dumpling-soup"], [678, "dumpling"],
          [674, "pickled-onions-peppers"]]
# The renamed scenario: another dish, and the soup's name on the dumpling row.
RENAMED = {"670": "Kit - Short rib", "678": "Kit - Chicken & Dumpling soup"}


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


def row(i, name, shift, station, sort):
    return {"id": i, "name": name, "shift": shift, "category": "daily", "station": station,
            "sort_order": sort, "team": "line", "location": "Tempest", "day_specific": None}


# The 11 kit rows on Line PM, as read (read-only) on 2026-11-16, after the
# November menu change renamed 675 and 676.
KIT_ROWS = [
    row(668, "Kit - Mac and Cheese", "PM", "kits", 10),
    row(669, "Kit - Buffalo sauce", "PM", "kits", 20),
    row(670, "Kit - Pork belly", "PM", "kits", 30),
    row(671, "Kit - Gastrique", "PM", "kits", 40),
    row(672, "Kit - Chicken & Dumpling soup", "PM", "kits", 50),
    row(678, "Kit - Dumpling", "PM", "kits", 60),
    row(673, "Kit - Spicy green sauce", "PM", "kits", 70),
    row(674, "Kit - Pickle onions& peppers", "PM", "kits", 80),
    row(675, "Kit - Suadero", "PM", "kits", 90),
    row(676, "Kit- Chilorio", "PM", "kits", 100),
    row(677, "Kit- New prep coming soon", "PM", "kits", 110),
]
ITEMS = KIT_ROWS + [
    row(9001, "Harness PM salad row", "PM", "salad", 5),
    row(9002, "Harness AM salad row", "AM", "salad", 5),
]
STAFF = [
    {"id": 1, "name": "Harness AM", "shift": "AM", "active": True, "sort_order": 1, "location": "Tempest"},
    {"id": 2, "name": "Harness PM", "shift": "PM", "active": True, "sort_order": 1, "location": "Tempest"},
]
READS = ("prep_items", "staff", "prep_sections", "prep_logs")

GATE_RE = re.compile(r"window\.location\.replace\('index\.html'\)")

HARNESS = r"""
<script>
/* ---- test harness: installed BEFORE any page script parses ---- */
(function(){
  var SCEN=(/[?&]scen=([a-z0-9]+)/.exec(location.search)||[0,'plain'])[1];
  var FX=__FIXTURES__;
  var reqs=[];
  window.__h={scen:SCEN,reqs:reqs,fx:FX,loadN:null};
  if(SCEN==='renamed')FX.items.forEach(function(r){if(FX.renamed[r.id])r.name=FX.renamed[r.id];});
  if(SCEN==='phone')document.write('<style>html{width:390px!important;max-width:390px!important}</style>');
  try{if(SCEN==='mgr')localStorage.setItem('boxkitchen.mgr','1');else localStorage.removeItem('boxkitchen.mgr');}catch(e){}
  function Stub(){this.readyState=0;this.status=0;this.responseText='';this._h={};}
  Stub.prototype.open=function(m,u){this._m=String(m).toUpperCase();this._u=String(u);};
  Stub.prototype.setRequestHeader=function(k,v){this._h[k]=v;};
  Stub.prototype.abort=function(){};
  Stub.prototype.send=function(body){
    var x=this;
    reqs.push({method:x._m,url:x._u,body:body==null?null:String(body),headers:x._h});
    setTimeout(function(){
      var m=x._u.match(/\/rest\/v1\/([A-Za-z_]+)/),t=m?m[1]:'',rows=[];
      if(x._m!=='GET'){x.status=403;x.responseText='{"message":"harness: writes are not allowed"}';}
      else{
        if(t==='prep_items')rows=FX.items;
        else if(t==='staff')rows=FX.staff;
        x.status=200;x.responseText=JSON.stringify(rows);
      }
      x.readyState=4;
      if(x.onload)x.onload();
    },20);
  };
  window.XMLHttpRequest=Stub;
  /* any other way out is recorded as a request, and goes nowhere */
  window.fetch=function(u,o){reqs.push({method:((o&&o.method)||'GET').toUpperCase(),url:String(u),via:'fetch'});return new Promise(function(){});};
  if(navigator.sendBeacon)navigator.sendBeacon=function(u){reqs.push({method:'POST',url:String(u),via:'beacon'});return true;};
})();
</script>
"""

RUNNER = r"""
<script>
(function(){
  var H=window.__h,log=[],fails=[];
  function ok(name,cond,detail){log.push(name);if(!cond)fails.push(name+(detail===undefined?'':' :: '+JSON.stringify(detail)));}
  function txt(el){return el?el.textContent.replace(/\s+/g,' ').trim():'';}
  function finish(){
    var d=document.createElement('div');d.id='harnessResults';d.textContent=JSON.stringify({log:log,fails:fails});
    document.body.appendChild(d);
  }
  /* --- every scenario: opening the page reads, and never writes --- */
  function common(){
    var R=H.reqs.slice(0,H.loadN==null?H.reqs.length:H.loadN);
    ok('no write request of any kind', R.every(function(r){return r.method==='GET'&&!r.body;}), R.map(function(r){return r.method+' '+r.url;}));
    ok('nothing but fetch-free XHR GETs', R.every(function(r){return !r.via;}), R);
    ok('no header asks for a write', R.every(function(r){return !r.headers.Prefer&&!r.headers['Content-Type'];}), H.reqs);
    ok('reads only the four tables it always has', R.length>0&&R.every(function(r){var m=r.url.match(/\/rest\/v1\/([A-Za-z_]+)/);return m&&H.fx.reads.indexOf(m[1])>-1;}), H.reqs.map(function(r){return r.url;}));
  }
  function active(){return [].map.call(document.querySelectorAll('.shift-btn.active'),txt);}
  function stations(){return [].map.call(document.querySelectorAll('.station-title'),function(e){var m=/\bst-([a-z]+)\b/.exec(e.className);return m?m[1]:'';});}
  function rowIds(){return [].map.call(document.querySelectorAll('.task[data-id]'),function(e){return parseInt(e.getAttribute('data-id'),10);});}
  var KIT=H.fx.items.filter(function(r){return r.station==='kits';}).map(function(r){return r.id;});
  function links(){return [].slice.call(document.querySelectorAll('.kit-sheet-link'));}
  function linkOf(id){return document.querySelector('.task[data-id="'+id+'"] .kit-sheet-link');}
  var WANT=H.fx.sheets.map(function(x){return x[0];});
  function sheetChecks(S){
    var L=links();
    ok(S+': exactly 7 SHEET buttons', L.length===7, L.length);
    ok(S+': on 668 669 670 671 672 678 674, in that order', JSON.stringify(L.map(function(a){return parseInt(a.closest('.task').getAttribute('data-id'),10);}))===JSON.stringify(WANT));
    H.fx.sheets.forEach(function(x){
      var a=linkOf(x[0]);
      ok(S+': '+x[0]+' goes to ?from=line#'+x[1], a&&a.getAttribute('href')==='tempest_kits.html?from=line#'+x[1], a&&a.getAttribute('href'));
      ok(S+': '+x[0]+' has no target and reads SHEET', a&&!a.hasAttribute('target')&&/^SHEET/.test(txt(a)));
    });
    [673,675,676,677,9001].forEach(function(id){ok(S+': no button on '+id, !linkOf(id));});
    KIT.forEach(function(id){
      var inp=document.getElementById('ni'+id),a=linkOf(id);
      ok(S+': #ni'+id+' still follows its .task-name', inp&&inp.previousElementSibling&&inp.previousElementSibling.classList.contains('task-name'));
      if(a)ok(S+': '+id+' button is in .task-info, not .task-name', !a.closest('.task-name')&&!!a.closest('.task-info'));
    });
  }
  function tap(el){el.click();}
  function run(){
    var S=H.scen,ids=rowIds();
    H.loadN=H.reqs.length;
    slice1(S,ids);
    if(S==='plain')ok('plain: no SHEET button on AM', links().length===0, links().length);
    if(S==='pm'||S==='mgr')sheetChecks(S);
    if(S==='phone'){
      ok('phone: page is 390px wide', Math.round(document.body.getBoundingClientRect().width)<=390&&document.documentElement.scrollWidth<=window.innerWidth, [document.body.getBoundingClientRect().width,document.documentElement.scrollWidth]);
      ok('phone: 7 buttons', links().length===7, links().length);
      links().forEach(function(a){
        var id=a.closest('.task').getAttribute('data-id'),r=a.getBoundingClientRect(),t=a.closest('.task').getBoundingClientRect(),i=a.closest('.task-info');
        var ir=i?i.getBoundingClientRect():{left:1e9,right:-1,top:1e9,bottom:-1};
        ok('phone: '+id+' button at least 44px tall', r.height>=44, r.height);
        ok('phone: '+id+' button wholly inside its row and .task-info', r.width>0&&r.left>=t.left&&r.right<=t.right&&r.top>=t.top&&r.bottom<=t.bottom&&r.left>=ir.left-0.5&&r.right<=ir.right+0.5&&r.bottom<=ir.bottom+0.5, [r.left,r.right,r.top,r.bottom,ir.left,ir.right,ir.bottom]);
        ok('phone: '+id+' button not clipped by an ancestor', (function(){var e=a.parentElement;while(e&&e!==document.body){var cs=getComputedStyle(e);if(cs.overflow!=='visible'||cs.overflowX!=='visible'){var er=e.getBoundingClientRect();if(r.left<er.left-0.5||r.right>er.right+0.5||r.bottom>er.bottom+0.5)return false;}e=e.parentElement;}return true;})());
      });
    }
    if(S==='renamed'){
      ok('renamed: 670 ("Kit - Short rib") has no button', !linkOf(670));
      ok('renamed: 678 ("Kit - Chicken & Dumpling soup") has no button', !linkOf(678));
      ok('renamed: the other 5 keep theirs', links().length===5, links().length);
      var own={};H.fx.sheets.forEach(function(x){own[x[0]]=x[1];});
      ok('renamed: every button points at its own row\'s sheet', links().every(function(a){var id=a.closest('.task').getAttribute('data-id');return a.getAttribute('href')==='tempest_kits.html?from=line#'+own[id];}));
    }
    common();
    if(S==='mgr'||S==='staff'){
      document.addEventListener('click',function(e){if(e.target.closest&&e.target.closest('a'))e.preventDefault();},true);
      var a=linkOf(670),pill=document.querySelector('.task[data-id="670"] .mode-pill'),box=document.querySelector('.task[data-id="670"] .checkbox'),inp=document.getElementById('ni670');
      ok(S+': 670 has its button', !!a);
      var n0=H.reqs.length;
      if(a)tap(a);
      setTimeout(function(){
        ok(S+': SHEET tap sends no request', H.reqs.length===n0, H.reqs.slice(n0));
        ok(S+': SHEET tap opens no rename box', getComputedStyle(inp).display==='none');
        ok(S+': SHEET tap flips no pill', txt(pill)==='KIT', txt(pill));
        ok(S+': SHEET tap ticks no box', !box.classList.contains('checked'));
        if(S==='staff'){finish();return;}
        var n1=H.reqs.length;
        tap(document.querySelector('.task[data-id="670"] .mode-pill'));
        setTimeout(function(){
          var w=H.reqs.slice(n1),b=w[0]&&w[0].body?JSON.parse(w[0].body):{};
          ok('mgr: pill tap makes exactly one write attempt', w.length===1, w.map(function(r){return r.method+' '+r.url;}));
          ok('mgr: it is a POST to prep_logs with mode make', w.length===1&&w[0].method==='POST'&&/\/rest\/v1\/prep_logs/.test(w[0].url)&&b.mode==='make', w[0]&&[w[0].method,w[0].url,b]);
          var n2=H.reqs.length,inp2=document.getElementById('ni670');
          tap(document.querySelector('.task[data-id="670"] .task-name'));
          setTimeout(function(){
            ok('mgr: name tap opens #ni670', inp2&&getComputedStyle(inp2).display!=='none');
            ok('mgr: name tap sends no request', H.reqs.length===n2, H.reqs.slice(n2));
            finish();
          },300);
        },400);
      },300);
      return;
    }
    finish();
  }
  /* Slice 1's checks */
  function slice1(S,ids){
    if(S==='plain'){
      ok('plain: no address opens on AM SHIFT, and only AM', JSON.stringify(active())==='["AM SHIFT"]', active());
      ok('plain: no Kits station on AM', stations().indexOf('kits')<0, stations());
      ok('plain: no kit row drawn', KIT.every(function(id){return ids.indexOf(id)<0;}), ids);
      ok('plain: the AM row is drawn, the PM row is not', ids.indexOf(9002)>-1&&ids.indexOf(9001)<0, ids);
    }
    if(S==='pm'){
      ok('pm: #pm opens on PM SHIFT, and only PM', JSON.stringify(active())==='["PM SHIFT"]', active());
      ok('pm: the Kits station comes first', stations()[0]==='kits', stations());
      var kitIds=ids.filter(function(id){return KIT.indexOf(id)>-1;});
      ok('pm: all 11 kit rows, in Line PM order', JSON.stringify(kitIds)===JSON.stringify(KIT), kitIds);
      ok('pm: each kit row keeps its KIT/MAKE pill', KIT.every(function(id){return !!document.querySelector('.task[data-id="'+id+'"] .mode-pill');}));
      ok('pm: the PM row is drawn, the AM row is not', ids.indexOf(9001)>-1&&ids.indexOf(9002)<0, ids);
      ok('pm: the address stays #pm', location.hash==='#pm', location.hash);
    }
  }
  /* wait for the rows (or 5s), then let the page settle before asserting */
  var t0=Date.now();
  (function wait(){
    if(document.querySelector('.task[data-id]')||Date.now()-t0>5000)setTimeout(run,400);
    else setTimeout(wait,50);
  })();
})();
</script>
"""


def build_page(scen):
    src = open(os.path.join(ROOT, PAGE), encoding="utf-8").read()
    src, n = GATE_RE.subn("void 0 /* gate neutralised by check_line.py */", src)
    if n != 1:
        sys.exit("check_line: could not find the site-password redirect in " + PAGE)
    if "<head>" not in src:
        sys.exit("check_line: no <head> in " + PAGE)
    fixtures = {"items": ITEMS, "staff": STAFF, "reads": list(READS), "sheets": SHEETS, "renamed": RENAMED}
    src = src.replace("<head>", "<head>" + HARNESS.replace("__FIXTURES__", json.dumps(fixtures)), 1)
    # no network, ever: the webfont links would otherwise leave the machine
    src = re.sub(r'<link rel="preconnect"[^>]*>\s*', '', src)
    src = re.sub(r'<link rel="stylesheet" href="https://fonts[^>]*>\s*', '', src)
    return src.replace("</body>", RUNNER + "</body>", 1)


RESULT_RE = re.compile(r'<div id="harnessResults">(.*?)</div>', re.S)


def run_scenario(chrome, path, scen):
    """One Chrome per scenario; poll --dump-dom output for the results div."""
    url = "file://" + path + "?scen=" + scen + ("#" + HASH[scen] if HASH[scen] else "")
    dom = os.path.join(os.path.dirname(path), "dom-" + scen + ".html")
    err = os.path.join(os.path.dirname(path), "err-" + scen + ".txt")
    with open(dom, "w") as fo, open(err, "w") as fe:
        proc = subprocess.Popen(
            [chrome, "--headless=new", "--disable-gpu", "--no-sandbox",
             "--no-first-run", "--disable-extensions",
             "--disable-background-networking", "--disable-component-update",
             "--disable-default-apps", "--disable-sync",
             "--host-resolver-rules=MAP * ~NOTFOUND",
             "--user-data-dir=" + os.path.join(os.path.dirname(path), "cd-" + scen),
             "--window-size=" + WINDOW.get(scen, "1200,900"),
             "--virtual-time-budget=20000", "--dump-dom", url],
            stdout=fo, stderr=fe)
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
        sys.exit("check_line: no Chrome found. Set CHROME=/path/to/chrome.")
    fails, total = [], 0
    scens = os.environ['ONLY'].split(',') if os.environ.get('ONLY') else SCENARIOS
    with tempfile.TemporaryDirectory() as td:
        shutil.copytree(os.path.join(ROOT, "assets"), os.path.join(td, "assets"))
        shutil.copytree(os.path.join(ROOT, "vendor"), os.path.join(td, "vendor"))
        for scen in scens:
            path = os.path.join(td, "line_" + scen + ".html")
            with open(path, "w", encoding="utf-8") as f:
                f.write(build_page(scen))
            res, err = run_scenario(chrome, path, scen)
            if res is None:
                fails.append("%s: harness never reported\n%s" % (scen, err))
                continue
            total += len(res["log"])
            fails += ["%s: %s" % (scen, x) for x in res["fails"]]

    if fails:
        print("line guard: %d failure(s) of %d assertions\n" % (len(fails), total))
        for x in fails:
            print("  " + x)
        print("\nsee docs/kits-line-link.md")
        return 1
    print("line guard: clean (%d assertions, %d scenarios, %s)" % (total, len(scens), PAGE))
    return 0


if __name__ == "__main__":
    sys.exit(main())
