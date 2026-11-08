#!/usr/bin/env python3
"""
Behaviour guard for the Recipe Costing page (tempest_recipe_costing.html),
docs/recipe-costing.md, Slice 2: the recipes, read-only, unlinked.

    python3 scripts/check_recipe_costing.py           # fixtures (CI runs this)
    python3 scripts/check_recipe_costing.py --live    # LOCAL ONLY, never in CI:
        # reads the live Recipes rows with one GET, then renders every one of
        # them in the page with every write blocked, and checks the counts
        # (expected 37 recipes / 280 lines on 2026-11-08; override with
        # LIVE_RECIPES=.. LIVE_LINES=..)

On the check_costing.py pattern: load the REAL page, neutralise the
site-password gate, replace XMLHttpRequest with a stub BEFORE the page script
parses (so no request can leave the machine), drive it in headless Chrome,
STYLED (assets/ is copied beside it), and read the results back from
#harnessResults.

Slice 2 promises: the page writes nothing - so every scenario asserts that no
request other than a GET was ever made; archived recipes are left out; every
line appears, in order, under its part, with the amount and unit RecipeMath
reads and "not linked".

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
import urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PAGE = "tempest_recipe_costing.html"

CHROME_CANDIDATES = [
    "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
    "/Applications/Chromium.app/Contents/MacOS/Chromium",
    "/usr/bin/google-chrome",
    "/usr/bin/google-chrome-stable",
    "/usr/bin/chromium",
    "/usr/bin/chromium-browser",
]


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


# Fixtures, in the order the server returns them (order=name.asc).
RECIPES = [
    {"id": 101, "name": "Basil Aioli", "category": "Sauce", "station": "Garde",
     "status": "archived", "ingredients": "2 cups mayo\n1 bunch basil"},
    {"id": 102, "name": "Chilorio Sauce", "category": "Sauce", "station": None,
     "status": "active",
     "ingredients": "6 oz. dried ancho chiles\n1 Tbsp + 1 tsp dried Mexican oregano\n1⅓ cups cider vinegar\n\nSalt TT"},
    {"id": 103, "name": "Empty Draft", "category": None, "station": None,
     "status": "active", "ingredients": None},
    {"id": 104, "name": "Mac & Cheese", "category": "Side", "station": "Saute",
     "status": "active",
     "ingredients": "— CHEESE BASE —\r\n1.5 qt. half & half\r\n2.5 lb. Velveeta cheese\r\n  8 oz. butter  \r\n— NOODLES —\r\n2 qt. dried macaroni noodles\r\n½ c. salt\r\n5# <b>onion</b>\r\n2 bay leaves"},
]

# What the page must show for Mac & Cheese, in order: (header?, text, reads)
MAC = [
    (True, "— CHEESE BASE —", None),
    (False, "1.5 qt. half & half", "reads: 1.5 qt"),
    (False, "2.5 lb. Velveeta cheese", "reads: 2.5 lb"),
    (False, "8 oz. butter", "reads: 8 oz"),
    (True, "— NOODLES —", None),
    (False, "2 qt. dried macaroni noodles", "reads: 2 qt"),
    (False, "½ c. salt", "reads: 0.5 cup"),
    (False, "5# <b>onion</b>", "reads: 5 lb"),
    (False, "2 bay leaves", "reads: 2 each — no unit word"),
]
CHILORIO = [
    (False, "6 oz. dried ancho chiles", "reads: 6 oz"),
    (False, "1 Tbsp + 1 tsp dried Mexican oregano", "reads: no amount — two amounts on one line"),
    (False, "1⅓ cups cider vinegar", "reads: 1.333 cup"),
    (False, "Salt TT", "reads: no amount"),
]

SCENARIOS = ("ok", "fail", "gate")

GATE_RE = re.compile(r"<script>\s*//\s*Site-password gate.*?</script>", re.S)

HARNESS = r"""
<script>
/* ---- test harness: installed BEFORE the page script parses ---- */
(function(){
  var SCEN=(location.hash||'#ok').slice(1);
  var ROWS=__ROWS__;
  window.__h={scen:SCEN,reqs:[],writes:[],fails:[],log:[]};
  try{ if(SCEN==='gate')sessionStorage.removeItem('boxkitchen_mgr'); else sessionStorage.setItem('boxkitchen_mgr','1'); }catch(e){}
  function X(){this.status=0;this.responseText='';this.timeout=0;}
  X.prototype.open=function(m,u){this.m=m;this.u=u;};
  X.prototype.setRequestHeader=function(){};
  X.prototype.send=function(body){
    var self=this;
    window.__h.reqs.push({m:self.m,u:self.u});
    if(self.m!=='GET'){window.__h.writes.push(self.m+' '+self.u);setTimeout(function(){self.onerror&&self.onerror();},5);return;}
    setTimeout(function(){
      if(SCEN==='fail'){self.onerror&&self.onerror();return;}
      if(/\/rest\/v1\/Recipes\?/.test(self.u)){self.status=200;self.responseText=JSON.stringify(ROWS);}
      else{self.status=404;self.responseText='[]';}
      self.onload&&self.onload();
    },10);
  };
  window.XMLHttpRequest=X;
})();
</script>
"""

RUNNER = r"""
<script>
/* ---- assertions: run after the page has loaded and rendered ---- */
setTimeout(function(){
  var H=window.__h, MAC=__MAC__, CHILORIO=__CHILORIO__, LIVE=__LIVE__;
  function ok(c,m){H.log.push(m);if(!c)H.fails.push(m);}
  function txt(el){return el?el.textContent.replace(/\s+/g,' ').trim():'';}
  function shown(el){return !!el&&getComputedStyle(el).display!=='none';}
  function rendered(){
    var out=[],ch=document.getElementById('recipeBody').children;
    for(var i=0;i<ch.length;i++){
      var c=ch[i];
      if(c.classList.contains('vhead'))out.push([true,txt(c),null,false]);
      else if(c.classList.contains('rc-line')){
        var u=c.querySelector('.ing-pack.unset');
        var rd=txt(c.querySelector('.rc-read')).replace(/\s*not linked$/,'');
        out.push([false,txt(c.querySelector('.rc-text')),rd,!!u&&txt(u)==='not linked']);
      }
    }
    return out;
  }
  function checkRecipe(id,want,label){
    openRecipe(id);
    var got=rendered();
    ok(shown(document.getElementById('recipeBody'))&&!shown(document.getElementById('listBody')),label+': opening a recipe shows it in place of the list');
    ok(got.length===want.length,label+': '+want.length+' rows shown, got '+got.length);
    for(var i=0;i<want.length;i++){
      var g=got[i]||[];
      ok(g[0]===want[i][0]&&g[1]===want[i][1],label+' row '+i+': '+JSON.stringify(want[i][1])+' in order, got '+JSON.stringify(g[1]));
      if(!want[i][0]){
        ok(g[2]===want[i][2],label+' row '+i+': '+JSON.stringify(want[i][2])+', got '+JSON.stringify(g[2]));
        ok(g[3],label+' row '+i+': says "not linked"');
      }
    }
    closeRecipe();
  }
  try{
    var gate=document.getElementById('gate');
    // styled: kitchen.css hides .gate.hide; unstyled, the gate would show
    if(H.scen!=='gate')ok(!shown(gate),'css: kitchen.css resolved (unlocked gate is hidden)');

    if(H.scen==='gate'){
      ok(shown(gate),'gate: without manager mode the PIN gate shows');
      ok(H.reqs.length===0,'gate: nothing is read before the PIN, got '+H.reqs.length+' requests');
      var gi=document.getElementById('gateInput');
      ok(parseFloat(getComputedStyle(gi).fontSize)>=16,'css: the PIN box is at least 16px');
    }

    if(H.scen==='fail'){
      ok(/Could not load recipes/.test(txt(document.getElementById('listBody'))),'fail: a failed load says so');
      var b=document.querySelector('#listBody button');
      ok(!!b,'fail: offers Try again');
      if(b){b.click();}
    }

    if(H.scen==='ok'){
      var rows=document.querySelectorAll('#listBody .ing-row');
      var names=[].map.call(rows,function(r){return txt(r.querySelector('.ing-name'));});
      ok(JSON.stringify(names)===JSON.stringify(['Chilorio Sauce','Empty Draft','Mac & Cheese']),'list: the active recipes in order, archived left out; got '+JSON.stringify(names));
      ok(txt(document.getElementById('countTag'))==='3 recipes','list: count says 3 recipes, got '+txt(document.getElementById('countTag')));
      ok(/Saute · 7 lines$/.test(txt(rows[2]&&rows[2].querySelector('.ing-pack'))),'list: Mac & Cheese shows its 7 lines');
      ok(parseFloat(getComputedStyle(rows[0]).height)>=44,'css: a recipe row is a 44px tap target');
      var r=H.reqs[0]||{u:''};
      ok(H.reqs.length===1,'read: exactly one request, got '+H.reqs.length);
      ok(/\/rest\/v1\/Recipes\?/.test(r.u),'read: it reads Recipes');
      ok(/select=id,name,category,station,status,ingredients(&|$)/.test(r.u),'read: select= names the columns');
      ok(/location=eq\.Tempest(&|$)/.test(r.u),'read: location=eq.Tempest');
      checkRecipe(104,MAC,'Mac & Cheese');
      var back=document.querySelector('#recipeBody .rc-back');
      openRecipe(104);back=document.querySelector('#recipeBody .rc-back');
      ok(back&&parseFloat(getComputedStyle(back).height)>=44,'css: ← Recipes is a 44px tap target');
      var un=document.querySelector('#recipeBody .ing-pack.unset');
      ok(un&&getComputedStyle(un).backgroundColor!=='rgba(0, 0, 0, 0)','css: "not linked" carries the yellow highlighter');
      ok(!document.querySelector('#recipeBody .rc-text b'),'escape: recipe text is shown as text, never as markup');
      back&&back.click();
      ok(shown(document.getElementById('listBody')),'back: ← Recipes returns to the list');
      checkRecipe(102,CHILORIO,'Chilorio');
      openRecipe(103);
      ok(/No ingredients/.test(txt(document.getElementById('recipeBody'))),'empty: a recipe with no ingredients says so');
      closeRecipe();
      ok(typeof openRecipe(101)==='undefined'&&!shown(document.getElementById('recipeBody')),'archived: an archived recipe cannot be opened');
    }

    if(H.scen==='live'){
      var lr=document.querySelectorAll('#listBody .ing-row');
      ok(lr.length===LIVE.recipes,'live: '+LIVE.recipes+' recipes listed, got '+lr.length);
      var all=[];
      LIVE.ids.forEach(function(id){openRecipe(id);rendered().forEach(function(x){all.push([id].concat(x));});closeRecipe();});
      var lines=all.filter(function(x){return !x[1];}), heads=all.filter(function(x){return x[1];});
      ok(lines.length===LIVE.lines,'live: '+LIVE.lines+' lines rendered, got '+lines.length);
      ok(lines.every(function(x){return x[4];}),'live: every line says "not linked"');
      ok(lines.every(function(x){return /^reads: /.test(x[3]);}),'live: every line shows what it reads');
      var flat=all.map(function(x){return [x[0],x[1],x[2]];});
      ok(JSON.stringify(flat)===JSON.stringify(LIVE.expect),'live: every line and header, in order, under its recipe');
      H.live={recipes:lr.length,lines:lines.length,headers:heads.length};
    }
  }catch(e){H.fails.push('threw: '+e);}
  setTimeout(function(){
    if(H.scen==='fail')ok(H.reqs.length===2,'fail: Try again reads again, got '+H.reqs.length+' requests');
    ok(H.writes.length===0,'writes: no request other than a GET, got '+JSON.stringify(H.writes));
    ok(H.reqs.every(function(q){return q.m==='GET';}),'writes: every request is a GET');
    var d=document.createElement('div');d.id='harnessResults';d.textContent=JSON.stringify({fails:H.fails,log:H.log,live:H.live||null});document.body.appendChild(d);
  },300);
},600);
</script>
"""


def build_page(rows, live=None):
    src = open(os.path.join(ROOT, PAGE), encoding="utf-8").read()
    src, n = GATE_RE.subn("<!-- gate neutralised by check_recipe_costing.py -->", src)
    if n != 1:
        sys.exit("check_recipe_costing: could not find the site-password gate in " + PAGE)
    marker = "<script>\nvar SB="
    if marker not in src:
        sys.exit("check_recipe_costing: could not find the page script in " + PAGE)
    src = src.replace(marker, HARNESS.replace("__ROWS__", json.dumps(rows)) + marker, 1)
    src = re.sub(r'<link rel="preconnect"[^>]*>\s*', '', src)
    src = re.sub(r'<link rel="stylesheet" href="https://fonts[^>]*>\s*', '', src)
    runner = (RUNNER.replace("__MAC__", json.dumps(MAC))
                    .replace("__CHILORIO__", json.dumps(CHILORIO))
                    .replace("__LIVE__", json.dumps(live)))
    return src.replace("</body>", runner + "</body>", 1)


RESULT_RE = re.compile(r'<div id="harnessResults">(.*?)</div>', re.S)


def run_scenario(chrome, path, scen):
    url = "file://" + path + "#" + scen
    td = os.path.dirname(path)
    dom = os.path.join(td, "dom-" + scen + ".html")
    err = os.path.join(td, "err-" + scen + ".txt")
    with open(dom, "w") as fo, open(err, "w") as fe:
        proc = subprocess.Popen(
            [chrome, "--headless=new", "--disable-gpu", "--no-sandbox",
             "--no-first-run", "--disable-extensions",
             "--disable-background-networking", "--disable-component-update",
             "--disable-default-apps", "--disable-sync", "--window-size=390,844",
             "--user-data-dir=" + os.path.join(td, "cd-" + scen),
             "--virtual-time-budget=8000", "--dump-dom", url],
            stdout=fo, stderr=fe)
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
        return None, "no results div after 120s\n" + open(err, encoding="utf-8", errors="replace").read()[-600:]
    body = (m.group(1).replace("&amp;", "&").replace("&lt;", "<")
            .replace("&gt;", ">").replace("&quot;", '"'))
    return json.loads(body), None


def run_all(chrome, page, scenarios):
    fails, total, live = [], 0, None
    with tempfile.TemporaryDirectory() as td:
        path = os.path.join(td, "recipe_costing_under_test.html")
        open(path, "w", encoding="utf-8").write(page)
        shutil.copytree(os.path.join(ROOT, "assets"), os.path.join(td, "assets"))
        for scen in scenarios:
            res, err = run_scenario(chrome, path, scen)
            if res is None:
                fails.append("%s: harness never reported\n%s" % (scen, err))
                continue
            total += len(res["log"])
            fails += ["%s: %s" % (scen, x) for x in res["fails"]]
            live = res.get("live") or live
    return fails, total, live


def fetch_live():
    """One read-only GET of the live Recipes rows, with the page's own key and query."""
    src = open(os.path.join(ROOT, PAGE), encoding="utf-8").read()
    sb = re.search(r"var SB='([^']+)'", src).group(1)
    sk = re.search(r"SK='([^']+)'", src).group(1)
    q = "select=id,name,category,station,status,ingredients&location=eq.Tempest&order=name.asc"
    req = urllib.request.Request(sb + "/rest/v1/Recipes?" + q, method="GET",
                                 headers={"apikey": sk, "Authorization": "Bearer " + sk})
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.loads(r.read().decode("utf-8"))


def expected_flat(rows):
    out = []
    for r in rows:
        if r.get("status") == "archived":
            continue
        for l in re.split(r"\r?\n", r.get("ingredients") or ""):
            t = re.sub(r"\s+", " ", l).strip()
            if t:
                out.append([r["id"], bool(re.match(r"^—.+—$", t)), t])
    return out


def main():
    chrome = find_chrome()
    if not chrome:
        sys.exit("check_recipe_costing: no Chrome found. Set CHROME=/path/to/chrome.")
    if "--live" in sys.argv:
        if os.environ.get("CI"):
            sys.exit("check_recipe_costing: --live is local only, never in CI")
        rows = fetch_live()
        want_r = int(os.environ.get("LIVE_RECIPES", "37"))
        want_l = int(os.environ.get("LIVE_LINES", "280"))
        live = {"recipes": want_r, "lines": want_l,
                "ids": [r["id"] for r in rows if r.get("status") != "archived"],
                "expect": expected_flat(rows)}
        fails, total, got = run_all(chrome, build_page(rows, live), ["live"])
        if fails:
            print("recipe costing guard (live): %d failure(s) of %d assertions\n" % (len(fails), total))
            for x in fails:
                print("  " + x)
            return 1
        print("recipe costing guard (live): clean - %d recipes, %d lines, %d part headers rendered, no writes (%d assertions)"
              % (got["recipes"], got["lines"], got["headers"], total))
        return 0

    fails, total, _ = run_all(chrome, build_page(RECIPES), SCENARIOS)
    if fails:
        print("recipe costing guard: %d failure(s) of %d assertions\n" % (len(fails), total))
        for x in fails:
            print("  " + x)
        print("\nsee docs/recipe-costing.md, Slice 2")
        return 1
    print("recipe costing guard: clean (%d assertions, %d scenarios, %s)" % (total, len(SCENARIOS), PAGE))
    return 0


if __name__ == "__main__":
    sys.exit(main())
