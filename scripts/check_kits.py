#!/usr/bin/env python3
"""
Behaviour guard for the Kits page (tempest_kits.html), docs/kits.md.

Slice 1's promises, on one kit (Spicy Green Sauce):
  - with today's recipe text, exactly the 5 containers in "The 8 kits", with
    nothing in "Not sorted yet";
  - a changed amount stays in its container and shows the new amount;
  - a renamed ingredient goes to "Not sorted yet", and the box appears only then;
  - heading lines and blank lines are skipped; "jalapeno" and "jalapeño" both match;
  - a keyword picks up exactly one line: a second "garlic" line goes to
    "Not sorted yet" and nothing else moves;
  - the page sends no write request of any kind.

None of that can be checked against the live database, so: load the REAL page,
neutralise the site-password redirect, replace XMLHttpRequest (and fetch and
sendBeacon) with a stub BEFORE the page's own <script> parses, so no request can
leave the machine, then drive it in headless Chrome and assert on the DOM and on
every request. Same shape as check_inventory.py.

    python3 scripts/check_kits.py          # ONLY=ok,renamed to run a few

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
PAGE = "tempest_kits.html"
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCENARIOS = ("ok", "amount", "renamed", "headings", "twogarlic")


def find_chrome():
    env = os.environ.get("CHROME")
    if env:
        return env if os.path.exists(env) else shutil.which(env)
    for p in CHROME_CANDIDATES:
        if os.path.exists(p):
            return p
    for n in ("google-chrome", "google-chrome-stable", "chromium",
              "chromium-browser", "chrome"):
        found = shutil.which(n)
        if found:
            return found
    return None

# ---------------------------------------------------------------- fixtures --
# Recipe 25 exactly as the live table held it on 2026-11-02 (a read-only GET).
GREEN = "\n".join([
    "2 cups Olive oil blend",
    "2 cups Parsley leaves, rough chop",
    "2 cups Cilantro leaves, rough chop",
    "2 each Jalapeño, seeded, small diced",
    "10 each Garlic, smashed and rough chopped",
    "2 Tbsp Lemon juice",
    "2 Tbsp Ground coriander",
    "4 tsp Ground cumin",
    "4 tsp Salt",
    "2 cups Greek yogurt",
])
# what each scenario's recipe text is
TEXTS = {
    "ok": GREEN,
    # an amount changed in the Recipe Database
    "amount": GREEN.replace("2 cups Greek yogurt", "3 cups Greek yogurt"),
    # an ingredient renamed so no keyword knows it
    "renamed": GREEN.replace("2 cups Greek yogurt", "2 cups Skyr"),
    # parts, blank lines, no ñ, and a curly apostrophe
    "headings": "— DRY —\n2 Tbsp Ground coriander\n4 tsp Ground cumin\n4 tsp Salt\n\n"
                "— WET —\n2 cups Olive oil blend\n2 cups Parsley leaves, rough chop\n"
                "2 cups Cilantro leaves, rough chop\n2 each Jalapeno, seeded, small diced\n"
                "10 each Garlic, smashed and rough chopped\n\n  \n2 Tbsp Lemon juice\n"
                "2 cups Chef’s Greek yogurt",
}
# a second line matching "garlic": the keyword picks up one line only
TEXTS["twogarlic"] = GREEN + "\n2 each garlic, minced"
RECIPES = [
    {"id": 25, "location": "Tempest", "name": "Spicy Green Sauce", "status": "active"},
    # another location's row with the same id range must never be used
    {"id": 99, "location": "Showdown", "name": "Not ours", "status": "active", "ingredients": "1 cup Skyr"},
]
EXPECT = [
    ["Spices", ["2 Tbsp Ground coriander", "4 tsp Ground cumin", "4 tsp Salt"]],
    ["Herbs & veg", ["2 cups Parsley leaves, rough chop", "2 cups Cilantro leaves, rough chop",
                     "2 each Jalapeño, seeded, small diced", "10 each Garlic, smashed and rough chopped"]],
    ["Olive oil blend", ["2 cups Olive oil blend"]],
    ["Lemon juice", ["2 Tbsp Lemon juice"]],
    ["Greek yogurt", ["2 cups Greek yogurt"]],
]

# ------------------------------------------------------------ page surgery --
GATE_RE = re.compile(r"window\.location\.replace\('index\.html'\)")

HARNESS = r"""
<script>
/* ---- test harness: installed BEFORE the page script parses ---- */
(function(){
  var SCEN=(location.hash||'#ok').slice(1);
  var FX=__FIXTURES__;
  var reqs=[];
  window.__h={scen:SCEN,reqs:reqs,fx:FX};
  function query(u){var q={},s=u.split('?')[1]||'';s.split('&').forEach(function(kv){var i=kv.indexOf('=');if(i>0)q[kv.slice(0,i)]=decodeURIComponent(kv.slice(i+1));});return q;}
  function Stub(){this.readyState=0;this.status=0;this.responseText='';this._h={};}
  Stub.prototype.open=function(m,u){this._m=String(m).toUpperCase();this._u=String(u);};
  Stub.prototype.setRequestHeader=function(k,v){this._h[k]=v;};
  Stub.prototype.abort=function(){};
  Stub.prototype.send=function(body){
    var x=this;
    reqs.push({method:x._m,url:x._u,body:body==null?null:String(body),headers:x._h});
    setTimeout(function(){
      var m=x._u.match(/\/rest\/v1\/([A-Za-z_]+)/),t=m?m[1]:'',q=query(x._u),rows=[];
      if(x._m!=='GET'){x.status=403;x.responseText='{"message":"harness: writes are not allowed"}';}
      else if(t!=='Recipes'){x.status=404;x.responseText='[]';}
      else{
        var ids=/^in\.\((.*)\)$/.test(q.id||'')?q.id.slice(4,-1).split(','):null;
        rows=FX.recipes.filter(function(r){
          if(ids&&ids.indexOf(String(r.id))<0)return false;
          if(q.location&&('eq.'+r.location)!==q.location)return false;
          return true;
        }).map(function(r){var c=JSON.parse(JSON.stringify(r));if(c.id===25)c.ingredients=FX.text;return c;});
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
  function boxes(){return [].map.call(document.querySelectorAll('.kit-box'),function(b){
    return [txt(b.querySelector('.kit-name')),[].map.call(b.querySelectorAll('.kit-line'),txt),txt(b.querySelector('.kit-num'))];});}
  function finish(){
    var d=document.createElement('div');d.id='harnessResults';d.textContent=JSON.stringify({log:log,fails:fails});
    document.body.appendChild(d);
  }
  function run(){
    var S=H.scen,E=H.fx.expect;
    var b=boxes(),un=document.getElementById('unsorted');

    /* --- everything, every scenario --- */
    ok('the sheet was drawn', !!document.getElementById('pan'), txt(document.getElementById('appBody')).slice(0,200));
    ok('no write request of any kind', H.reqs.every(function(r){return r.method==='GET'&&!r.body;}), H.reqs);
    ok('nothing but fetch-free XHR GETs', H.reqs.every(function(r){return !r.via;}), H.reqs);
    ok('exactly one request', H.reqs.length===1, H.reqs.length);
    var u=H.reqs[0]?H.reqs[0].url:'';
    ok('the one read is Recipes, by id, for Tempest, four columns only',
       /\/rest\/v1\/Recipes\?id=in\.\(25\)&location=eq\.Tempest&select=id,name,status,ingredients$/.test(u), u);
    ok('no header asks for a write', H.reqs.every(function(r){return !r.headers.Prefer&&!r.headers['Content-Type'];}), H.reqs);
    ok('the page has no inputs', document.querySelectorAll('input,select,textarea').length===0);
    ok('kit name and its recipe', txt(document.querySelector('.kit-title'))==='Spicy green sauce'&&txt(document.querySelector('.kit-from'))==='from Spicy Green Sauce');
    ok('numbers are rings, 1 to N', b.every(function(x,i){return x[2]===String(i+1);})&&
       [].every.call(document.querySelectorAll('.kit-num'),function(n){var cs=getComputedStyle(n);return parseFloat(cs.borderTopWidth)>=2&&cs.borderRadius==='50%';}), b);
    ok('the hotel pan step is there', new RegExp('All '+b.length+' containers into one hotel pan').test(txt(document.getElementById('pan')))&&/Label and date the pan · into the cooler/.test(txt(document.getElementById('pan'))), txt(document.getElementById('pan')));
    ok('no "Not in the kit" section for this kit', !/Not in the kit/.test(txt(document.getElementById('appBody'))));
    /* every recipe line lands in exactly one place */
    var landed=[].map.call(document.querySelectorAll('.kit-line'),txt);
    var src=H.fx.text.split('\n').map(function(s){return s.trim();}).filter(function(s){return s&&!/^—.+—$/.test(s);});
    ok('every recipe line lands exactly once', landed.length===src.length&&src.every(function(s){return landed.indexOf(s.replace(/\s+/g,' '))>-1;}), {landed:landed,src:src});

    if(S==='ok'){
      ok('ok: exactly the 5 containers, each with its lines', JSON.stringify(b.map(function(x){return [x[0],x[1]];}))===JSON.stringify(E), b);
      ok('ok: nothing in "Not sorted yet", and no box', !un&&!/Not sorted yet/.test(txt(document.getElementById('appBody'))));
    }
    if(S==='amount'){
      var y=b.filter(function(x){return x[0]==='Greek yogurt';})[0];
      ok('amount: the yogurt stays in its container with the new amount', !!y&&y[1].length===1&&y[1][0]==='3 cups Greek yogurt', b);
      ok('amount: the old amount is nowhere', !/2 cups Greek yogurt/.test(txt(document.getElementById('appBody'))));
      ok('amount: nothing unsorted', !un);
    }
    if(S==='renamed'){
      ok('renamed: the box appears', !!un&&/Not sorted yet/.test(txt(un)));
      ok('renamed: the line is in it', !!un&&[].some.call(un.querySelectorAll('.kit-line'),function(l){return txt(l)==='2 cups Skyr';}), txt(un));
      ok('renamed: it says to tell a manager', /This is in the recipe but not in the kit yet — tell a manager\./.test(txt(un)));
      ok('renamed: it stands out by border, not colour', !!un&&parseFloat(getComputedStyle(un).borderTopWidth)>=3, un&&getComputedStyle(un).borderTopWidth);
      ok('renamed: the empty container disappears, numbers close up', b.length===4&&b.every(function(x){return x[0]!=='Greek yogurt';})&&b[3][2]==='4', b);
      ok('renamed: the pan counts 4', /All 4 containers/.test(txt(document.getElementById('pan'))));
      ok('renamed: the box comes before the containers', !!un&&!!(un.compareDocumentPosition(document.querySelector('.kit-box'))&Node.DOCUMENT_POSITION_FOLLOWING));
    }
    if(S==='headings'){
      ok('headings: no heading line is shown as an ingredient', !/—/.test(landed.join(' ')), landed);
      ok('headings: blank lines are skipped, nothing unsorted', !un, un&&txt(un));
      var hv=b.filter(function(x){return x[0]==='Herbs & veg';})[0];
      ok('headings: "jalapeno" without the ñ matches', !!hv&&hv[1].indexOf('2 each Jalapeno, seeded, small diced')>-1, b);
      var gy=b.filter(function(x){return x[0]==='Greek yogurt';})[0];
      ok('headings: a curly apostrophe does not stop a match', !!gy&&gy[1][0]==='2 cups Chef’s Greek yogurt', b);
      ok('headings: still 5 containers', b.length===5, b);
    }
    if(S==='twogarlic'){
      var hv2=b.filter(function(x){return x[0]==='Herbs & veg';})[0];
      ok('twogarlic: the original garlic line stays in container 2', !!hv2&&hv2[2]==='2'&&hv2[1].indexOf('10 each Garlic, smashed and rough chopped')>-1, b);
      ok('twogarlic: the new line is not in a container', b.every(function(x){return x[1].indexOf('2 each garlic, minced')<0;}), b);
      ok('twogarlic: the new line shows in "Not sorted yet", alone', !!un&&[].map.call(un.querySelectorAll('.kit-line'),txt).join('|')==='2 each garlic, minced', un&&txt(un));
      ok('twogarlic: nothing else moves', JSON.stringify(b.map(function(x){return [x[0],x[1]];}))===JSON.stringify(E), b);
    }
    finish();
  }
  /* wait for the sheet (or 5s), then assert */
  var t0=Date.now();
  (function wait(){
    if(document.getElementById('pan')||document.querySelector('.empty')||Date.now()-t0>5000)setTimeout(run,100);
    else setTimeout(wait,50);
  })();
})();
</script>
"""


def build_page(scen):
    src = open(os.path.join(ROOT, PAGE), encoding="utf-8").read()
    src, n = GATE_RE.subn("void 0 /* gate neutralised by check_kits.py */", src)
    if n != 1:
        sys.exit("check_kits: could not find the site-password redirect in " + PAGE)
    marker = "<script>\nvar SB="
    if marker not in src:
        sys.exit("check_kits: could not find the page script in " + PAGE)
    fixtures = {"recipes": RECIPES, "text": TEXTS[scen], "expect": EXPECT}
    src = src.replace(marker, HARNESS.replace("__FIXTURES__", json.dumps(fixtures)) + marker, 1)
    # no network, ever: the webfont links would otherwise leave the machine
    src = re.sub(r'<link rel="preconnect"[^>]*>\s*', '', src)
    src = re.sub(r'<link rel="stylesheet" href="https://fonts[^>]*>\s*', '', src)
    return src.replace("</body>", RUNNER + "</body>", 1)


RESULT_RE = re.compile(r'<div id="harnessResults">(.*?)</div>', re.S)


def run_scenario(chrome, path, scen):
    """One Chrome per scenario; poll --dump-dom output for the results div."""
    url = "file://" + path + "#" + scen
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
        sys.exit("check_kits: no Chrome found. Set CHROME=/path/to/chrome.")
    fails, total = [], 0
    scens = os.environ['ONLY'].split(',') if os.environ.get('ONLY') else SCENARIOS
    with tempfile.TemporaryDirectory() as td:
        shutil.copytree(os.path.join(ROOT, "assets"), os.path.join(td, "assets"))
        for scen in scens:
            path = os.path.join(td, "kits_" + scen + ".html")
            with open(path, "w", encoding="utf-8") as f:
                f.write(build_page(scen))
            res, err = run_scenario(chrome, path, scen)
            if res is None:
                fails.append("%s: harness never reported\n%s" % (scen, err))
                continue
            total += len(res["log"])
            fails += ["%s: %s" % (scen, x) for x in res["fails"]]

    if fails:
        print("kits guard: %d failure(s) of %d assertions\n" % (len(fails), total))
        for x in fails:
            print("  " + x)
        print("\nsee docs/kits.md, Slice 1")
        return 1
    print("kits guard: clean (%d assertions, %d scenarios, %s)" % (total, len(scens), PAGE))
    return 0


if __name__ == "__main__":
    sys.exit(main())
