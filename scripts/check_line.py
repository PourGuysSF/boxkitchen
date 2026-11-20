#!/usr/bin/env python3
"""
Behaviour guard for the Tempest Line page (tempest_line.html), for the Kits
Line PM link (docs/kits-line-link.md).

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
rows, read 2026-11-08, plus one other PM row and one AM row), then drive it in
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
SCENARIOS = ("plain", "pm")
HASH = {"plain": "", "pm": "pm"}


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


# The 11 kit rows on Line PM, as read (read-only) on 2026-11-08.
KIT_ROWS = [
    row(668, "Kit - Mac and Cheese", "PM", "kits", 10),
    row(669, "Kit - Buffalo sauce", "PM", "kits", 20),
    row(670, "Kit - Pork belly", "PM", "kits", 30),
    row(671, "Kit - Gastrique", "PM", "kits", 40),
    row(672, "Kit - Chicken & Dumpling soup", "PM", "kits", 50),
    row(678, "Kit - Dumpling", "PM", "kits", 60),
    row(673, "Kit - Spicy green sauce", "PM", "kits", 70),
    row(674, "Kit - Pickle onions& peppers", "PM", "kits", 80),
    row(675, "Kit - New prep soon", "PM", "kits", 90),
    row(676, "Kit- New prep coming soon", "PM", "kits", 100),
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
  window.__h={scen:SCEN,reqs:reqs,fx:FX};
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
    ok('no write request of any kind', H.reqs.every(function(r){return r.method==='GET'&&!r.body;}), H.reqs.map(function(r){return r.method+' '+r.url;}));
    ok('nothing but fetch-free XHR GETs', H.reqs.every(function(r){return !r.via;}), H.reqs);
    ok('no header asks for a write', H.reqs.every(function(r){return !r.headers.Prefer&&!r.headers['Content-Type'];}), H.reqs);
    ok('reads only the four tables it always has', H.reqs.length>0&&H.reqs.every(function(r){var m=r.url.match(/\/rest\/v1\/([A-Za-z_]+)/);return m&&H.fx.reads.indexOf(m[1])>-1;}), H.reqs.map(function(r){return r.url;}));
  }
  function active(){return [].map.call(document.querySelectorAll('.shift-btn.active'),txt);}
  function stations(){return [].map.call(document.querySelectorAll('.station-title'),function(e){var m=/\bst-([a-z]+)\b/.exec(e.className);return m?m[1]:'';});}
  function rowIds(){return [].map.call(document.querySelectorAll('.task[data-id]'),function(e){return parseInt(e.getAttribute('data-id'),10);});}
  var KIT=H.fx.items.filter(function(r){return r.station==='kits';}).map(function(r){return r.id;});
  function run(){
    var S=H.scen,ids=rowIds();
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
    common();
    finish();
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
    fixtures = {"items": ITEMS, "staff": STAFF, "reads": list(READS)}
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
