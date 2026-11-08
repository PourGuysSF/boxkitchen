#!/usr/bin/env python3
"""
Behaviour guard for the Kits page (tempest_kits.html), docs/kits.md.

Slice 2's promises: every line of all 8 kits lands where "The 8 kits" says
(written out by hand below); the longest keyword wins; a keyword listed twice
picks up lines in recipe order; the list shows the 8 in Line PM order with
their container counts; each address opens its own kit, and Back, the
browser's back, a bad address and no address all behave; moving between kits
sends no second request, and nothing is ever written.

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
SCENARIOS = ("ok", "amount", "renamed", "headings", "twogarlic",
             # slice 2 - all 8 kits, the list, the addresses
             "all8", "list", "direct", "nope", "reorder",
             # slice 3 - when the recipe or the wifi lets it down
             "missing", "archived", "lost", "emptied", "fail", "e500", "hang", "failaddr",
             # slice 4 - the paper backup
             "print")
# Slice 1's scenarios open Spicy Green Sauce by its address; the scenario
# itself rides in the query string, because the address now picks the kit.
SLICE1 = ("ok", "amount", "renamed", "headings", "twogarlic")
HASH = {"missing": "", "archived": "", "lost": "", "emptied": "", "fail": "", "e500": "",
        "hang": "", "failaddr": "mac-and-cheese", "reorder": "", "direct": "mac-and-cheese", "nope": "no-such-kit", "list": "", "all8": "", "print": ""}


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
# Recipes 5, 54, 43, 14, 19, 24 and 46 exactly as the live table held them on
# 2026-11-05 (a read-only GET). Escaped so the file stays plain ASCII.
LIVE = {
    5: "1 ea. butter\n1 c. garlic\n1 jug. honey\n1 tube harissa paste\n4 ea. lemon juice\n1 ea. Frank's Red Hot",
    54: "2 each pork belly\n6 each white onion\n6 each carrot\n6 each celery\n4 each heads of garlic, halved\n4 each bay leaf\n1 cup salt\n\u00bd cup black peppercorns\nparsley stems\npork or veg stock to cover\nthyme (for roasting)\nrosemary (for roasting)\ngarlic cloves (for roasting)\n4 cups cooking liquid (reserved from braise)\nsalt\npepper",
    43: "1 piece slab bacon, roasted and small diced\n2 qt. sliced shallots\n1 bottle red wine\n4 c. red wine vinegar\n2 c. sugar\nbundle of thyme and rosemary\n2 bay leaves\n2 cup horseradish",
    14: "\u2014 DRY \u2014\n4 tsp. baking powder\n\u00bd tsp. baking soda\n2 tsp. salt\n\u00bd tsp. black pepper\n2 cup flour\n\n\u2014 WET & ASSEMBLY \u2014\n6 TB. butter\n1\u00bc cup buttermilk",
    19: "5# chicken thigh\n1 qt. carrots, small dice\n1 qt. celery, small dice\n2 qt. white onion, small dice\n\u00bd pint garlic, sliced\n\u00bd bunch thyme\n2 ea. bay leaf\nSalt\nBlack pepper\n\u00bd cup olive oil\n\u00bd cup butter\n1 cup flour\n6 qt. chicken stock",
    24: "\u2014 PEPPERS \u2014\n2 quart Red onion, thin julienne\n2 bag Mini peppers, sliced\n10 cloves Garlic, sliced\n\n\u2014 PICKLING LIQUID \u2014\n1.5 qt Water\n1.5 qt Cider vinegar\n\u00be cup Sugar\n1 Tbsp Salt\n1 Tbsp Coriander",
    46: "\u2014 CHEESE BASE \u2014\n1.5 qt. half & half\n2.5 lb. Velveeta cheese\n4 c. mixed cheese\n\u00bd can chipotle peppers and juice, minced\n2 tsp. salt\n\u00bd tsp. chipotle chili powder\n\u00bd tsp. ancho chili powder\n\n\u2014 ROUX BASE \u2014\n8 oz. butter\n2 ea. white onion\n2 Tb. roasted garlic\n\u00bc c. flour\n4 c. half & half\n1 bu. chives\n\u00bc bu. parsley\n\n\u2014 NOODLES & ASSEMBLY \u2014\n2 qt. dried macaroni noodles\n\u00bd c. salt",
}
NAMES = {5: "Honey Harissa Buffalo", 54: "Pork Belly", 43: "Bacon Shallot Gastrique",
         14: "Dumpling", 19: "Chicken & Dumpling (Soup Base)", 25: "Spicy Green Sauce",
         24: "Pickled Onion & Pepper", 46: "Mac & Cheese"}
RECIPES = [
    {"id": 25, "location": "Tempest", "name": "Spicy Green Sauce", "status": "active"},
] + [{"id": i, "location": "Tempest", "name": NAMES[i], "status": "active", "ingredients": LIVE[i]}
     for i in (5, 54, 43, 14, 19, 24, 46)] + [
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

# All 8 kits, written out by hand from docs/kits.md "The 8 kits" - NOT by
# running the page's own sort - so this is a second opinion, not an echo.
# boxes: [part, name, keep, [lines]]; out: [line, why]; side: next to the pan.
OWN, TOG, SIDE = "own container", "together", "next to the pan, labelled"
KITS8 = [
    {"slug": "buffalo-sauce", "name": "Buffalo sauce", "recipe": "Honey Harissa Buffalo", "boxes": [
        ["", "Butter", "own container, melts first", ["1 ea. butter"]],
        ["", "Harissa + garlic", TOG, ["1 c. garlic", "1 tube harissa paste"]],
        ["", "Honey", SIDE, ["1 jug. honey"]],
        ["", "Lemon juice", OWN, ["4 ea. lemon juice"]],
        ["", "Frank\u2019s Red Hot", SIDE, ["1 ea. Frank's Red Hot"]]],
     "out": [], "side": ["Honey", "Frank\u2019s Red Hot"]},
    {"slug": "pork-belly", "name": "Pork belly", "recipe": "Pork Belly", "boxes": [
        ["", "Braise veg", TOG, ["6 each white onion", "6 each carrot", "6 each celery", "4 each heads of garlic, halved"]],
        ["", "Braise seasoning", TOG, ["4 each bay leaf", "1 cup salt", "\u00bd cup black peppercorns", "parsley stems"]],
        ["", "Roasting herbs", TOG, ["thyme (for roasting)", "rosemary (for roasting)", "garlic cloves (for roasting)"]]],
     "out": [["2 each pork belly", "raw meat \u2014 pull from the meat shelf"],
             ["pork or veg stock to cover", "to cover, at the stove"],
             ["4 cups cooking liquid (reserved from braise)", "comes from the braise"],
             ["salt", "to finish, at the stove"], ["pepper", "to finish, at the stove"]], "side": []},
    {"slug": "gastrique", "name": "Gastrique", "recipe": "Bacon Shallot Gastrique", "boxes": [
        ["", "Bacon", OWN, ["1 piece slab bacon, roasted and small diced"]],
        ["", "Shallots", OWN, ["2 qt. sliced shallots"]],
        ["", "Herbs", TOG, ["bundle of thyme and rosemary", "2 bay leaves"]],
        ["", "Red wine", SIDE, ["1 bottle red wine"]],
        ["", "Red wine vinegar", OWN, ["4 c. red wine vinegar"]],
        ["", "Sugar", OWN, ["2 c. sugar"]],
        ["", "Horseradish", OWN, ["2 cup horseradish"]]],
     "out": [], "side": ["Red wine"]},
    {"slug": "dumpling", "name": "Dumpling", "recipe": "Dumpling", "boxes": [
        ["", "Dry mix", TOG, ["4 tsp. baking powder", "\u00bd tsp. baking soda", "2 tsp. salt", "\u00bd tsp. black pepper", "2 cup flour"]],
        ["", "Butter", OWN, ["6 TB. butter"]],
        ["", "Buttermilk", OWN, ["1\u00bc cup buttermilk"]]],
     "out": [], "side": []},
    {"slug": "chicken-dumpling-soup", "name": "Chicken & dumpling soup", "recipe": "Chicken & Dumpling (Soup Base)", "boxes": [
        ["", "Olive oil", OWN, ["\u00bd cup olive oil"]],
        ["", "Butter", OWN, ["\u00bd cup butter"]],
        ["", "Aromatics", TOG, ["\u00bd bunch thyme", "2 ea. bay leaf"]],
        ["", "Vegetables", TOG, ["1 qt. carrots, small dice", "1 qt. celery, small dice", "2 qt. white onion, small dice", "\u00bd pint garlic, sliced"]],
        ["", "Flour", OWN, ["1 cup flour"]]],
     "out": [["5# chicken thigh", "raw meat \u2014 pull from the meat shelf"],
             ["Salt", "to taste, at the stove"], ["Black pepper", "to taste, at the stove"],
             ["6 qt. chicken stock", "cans, from the shelf"]], "side": []},
    {"slug": "spicy-green-sauce", "name": "Spicy green sauce", "recipe": "Spicy Green Sauce", "boxes": [
        ["", "Spices", "measure together", ["2 Tbsp Ground coriander", "4 tsp Ground cumin", "4 tsp Salt"]],
        ["", "Herbs & veg", TOG, ["2 cups Parsley leaves, rough chop", "2 cups Cilantro leaves, rough chop",
                                  "2 each Jalape\u00f1o, seeded, small diced", "10 each Garlic, smashed and rough chopped"]],
        ["", "Olive oil blend", OWN, ["2 cups Olive oil blend"]],
        ["", "Lemon juice", OWN, ["2 Tbsp Lemon juice"]],
        ["", "Greek yogurt", OWN, ["2 cups Greek yogurt"]]],
     "out": [], "side": []},
    {"slug": "pickled-onions-peppers", "name": "Pickled onions & peppers", "recipe": "Pickled Onion & Pepper", "boxes": [
        ["", "Veg", TOG, ["2 quart Red onion, thin julienne", "2 bag Mini peppers, sliced", "10 cloves Garlic, sliced"]],
        ["", "Pickling spices", TOG, ["\u00be cup Sugar", "1 Tbsp Salt", "1 Tbsp Coriander"]],
        ["", "Cider vinegar", OWN, ["1.5 qt Cider vinegar"]]],
     "out": [["1.5 qt Water", "from the tap"]], "side": []},
    {"slug": "mac-and-cheese", "name": "Mac & cheese", "recipe": "Mac & Cheese", "boxes": [
        ["Cheese base", "Half & half", "labelled \u201ccheese base\u201d", ["1.5 qt. half & half"]],
        ["Cheese base", "Cheeses", TOG, ["2.5 lb. Velveeta cheese", "4 c. mixed cheese"]],
        ["Cheese base", "Seasoning", TOG, ["\u00bd can chipotle peppers and juice, minced", "2 tsp. salt",
                                           "\u00bd tsp. chipotle chili powder", "\u00bd tsp. ancho chili powder"]],
        ["Roux base", "Butter", OWN, ["8 oz. butter"]],
        ["Roux base", "Onion", OWN, ["2 ea. white onion"]],
        ["Roux base", "Roasted garlic", OWN, ["2 Tb. roasted garlic"]],
        ["Roux base", "Flour", OWN, ["\u00bc c. flour"]],
        ["Roux base", "Half & half", "labelled \u201croux\u201d", ["4 c. half & half"]],
        ["Noodles & assembly", "Macaroni", OWN, ["2 qt. dried macaroni noodles"]],
        ["Noodles & assembly", "Salt for the water", OWN, ["\u00bd c. salt"]],
        ["Noodles & assembly", "Herbs", TOG, ["1 bu. chives", "\u00bc bu. parsley"]]],
     "out": [], "side": []},
]
LIST_COUNTS = [5, 3, 7, 3, 5, 5, 3, 11]


def swap(text, a, b):
    """the recipe with lines a and b changed places"""
    assert a in text and b in text
    return text.replace(a, "\0").replace(b, a).replace("\0", b)

# 'reorder': in today's text the shorter keyword's line always comes first, so
# a page that ignored longest-first would still pass. Here the longer one's
# line comes first; only longest-first keeps each line in its own container.
REORDER = {43: swap(LIVE[43], "1 bottle red wine", "4 c. red wine vinegar"),
           14: swap(LIVE[14], "6 TB. butter", "1\u00bc cup buttermilk")}
ALL_IDS = "5,54,43,14,19,25,24,46"

# ------------------------------------------------------------ page surgery --
GATE_RE = re.compile(r"window\.location\.replace\('index\.html'\)")

HARNESS = r"""
<script>
/* ---- test harness: installed BEFORE the page script parses ---- */
(function(){
  var SCEN=(/[?&]scen=([a-z0-9]+)/.exec(location.search)||[0,'ok'])[1];
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
    reqs.push({method:x._m,url:x._u,body:body==null?null:String(body),headers:x._h,timeout:x.timeout});
    var fate=FX.plan.shift();
    /* 'err' = no answer at all; 'hang' = nothing, until the page's own timeout */
    if(fate==='err'){setTimeout(function(){if(x.onerror)x.onerror();},20);return;}
    if(fate==='hang'){if(x.timeout>0)setTimeout(function(){if(x.ontimeout)x.ontimeout();},50);return;}
    setTimeout(function(){
      var m=x._u.match(/\/rest\/v1\/([A-Za-z_]+)/),t=m?m[1]:'',q=query(x._u),rows=[];
      if(fate==='e500'){x.status=500;x.responseText='{"message":"harness: the server says no"}';}
      else if(x._m!=='GET'){x.status=403;x.responseText='{"message":"harness: writes are not allowed"}';}
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
  /* --- every scenario, checked at the very end: nothing but the one read --- */
  function common(){
    ok('no write request of any kind', H.reqs.every(function(r){return r.method==='GET'&&!r.body;}), H.reqs);
    ok('nothing but fetch-free XHR GETs', H.reqs.every(function(r){return !r.via;}), H.reqs);
    var want=H.wantReqs||1;
    ok('exactly '+want+' request(s), however many kits were opened', H.reqs.length===want, H.reqs.length);
    ok('every read is Recipes, all 8 ids, for Tempest, four columns only', H.reqs.every(function(r){var u=r.url;return u.indexOf('/rest/v1/Recipes?id=in.('+H.fx.ids+')&location=eq.Tempest&select=id,name,status,ingredients')>-1&&/ingredients$/.test(u);}), H.reqs.map(function(r){return r.url;}));
    ok('no header asks for a write', H.reqs.every(function(r){return !r.headers.Prefer&&!r.headers['Content-Type'];}), H.reqs);
    ok('the page has no inputs', document.querySelectorAll('input,select,textarea').length===0);
  }
  /* one kit sheet against its hand-written expectation */
  function sheet(K){
    var app=document.getElementById('appBody'),tag=K.slug+': ';
    var got=[].map.call(document.querySelectorAll('.kit-box'),function(b){
      var part=null,p=b.previousElementSibling;
      while(p){if(p.classList.contains('kit-part')){part=txt(p);break;}p=p.previousElementSibling;}
      return [part||'',txt(b.querySelector('.kit-name')),txt(b.querySelector('.kit-keep')),
              [].map.call(b.querySelectorAll('.kit-line'),txt),txt(b.querySelector('.kit-num'))];});
    ok(tag+'its own sheet opened', txt(document.querySelector('.kit-title'))===K.name&&txt(document.querySelector('.kit-from'))==='from '+K.recipe, txt(document.querySelector('.kit-title')));
    ok(tag+'every container, keep line and recipe line exactly as "The 8 kits"',
       JSON.stringify(got.map(function(g){return g.slice(0,4);}))===JSON.stringify(K.boxes), {got:got,want:K.boxes});
    ok(tag+'numbered 1 to '+K.boxes.length+' straight through the parts', got.every(function(g,i){return g[4]===String(i+1);}), got.map(function(g){return g[4];}));
    var outs=[].map.call(document.querySelectorAll('.kit-out'),function(o){return [txt(o.querySelector('.kit-line')),txt(o.querySelector('.kit-why'))];});
    var wantOut=K.out.slice().sort(),gotOut=outs.slice().sort();
    ok(tag+'"Not in the kit" holds exactly its lines, each with its reason', JSON.stringify(gotOut)===JSON.stringify(wantOut), {got:outs,want:K.out});
    ok(tag+'"Not in the kit" only when it has something', K.out.length?/Not in the kit/.test(txt(app)):!/Not in the kit/.test(txt(app)));
    ok(tag+'nothing in "Not sorted yet"', !document.getElementById('unsorted'));
    var pan=txt(document.getElementById('pan')),inPan=K.boxes.length-K.side.length;
    ok(tag+'pan: all '+inPan+' in the pan', pan.indexOf('All '+inPan+' container'+(inPan===1?'':'s')+' into one hotel pan')===0, pan);
    ok(tag+'pan: each next-to-the-pan item named, and no other',
       K.side.every(function(n){return pan.indexOf('Next to the pan, labelled: '+n)>-1;})&&(pan.match(/Next to the pan, labelled:/g)||[]).length===K.side.length, pan);
    var parts=[].map.call(document.querySelectorAll('.kit-part'),txt),wantParts=[];
    K.boxes.forEach(function(b){if(b[0]&&wantParts.indexOf(b[0])<0)wantParts.push(b[0]);});
    ok(tag+'sub-headings are the kit\u2019s own parts', JSON.stringify(parts)===JSON.stringify(wantParts), parts);
    ok(tag+'a Back link to the list', !!document.getElementById('backLink')&&document.getElementById('backLink').getAttribute('href')==='#');
    return got;
  }
  function kitBy(slug){return H.fx.kits.filter(function(k){return k.slug===slug;})[0];}
  function isList(){
    var items=[].map.call(document.querySelectorAll('.kit-item'),function(a){return [a.getAttribute('data-slug'),txt(a.querySelector('.kit-item-name')),txt(a.querySelector('.kit-item-n'))];});
    return items;
  }
  function listChecks(tag){
    var items=isList(),K=H.fx.kits,C=H.fx.counts;
    ok(tag+'the list is showing, and no sheet', items.length>0&&!document.getElementById('pan'), txt(document.getElementById('appBody')).slice(0,200));
    ok(tag+'8 kits, in Line PM order', JSON.stringify(items.map(function(i){return i[0];}))===JSON.stringify(K.map(function(k){return k.slug;})), items);
    ok(tag+'each with its name and its container count', items.every(function(it,i){return it[1]===K[i].name&&it[2]===C[i]+' containers';}), items);
    ok(tag+'each links to its own address', [].every.call(document.querySelectorAll('.kit-item'),function(a,i){return a.getAttribute('href')==='#'+K[i].slug;}));
    ok(tag+'each is a big tap target (\u226544px)', [].every.call(document.querySelectorAll('.kit-item'),function(a){return a.getBoundingClientRect().height>=44;}));
  }
  /* --- Slice 4: print. Chrome headless cannot switch to print media from
     inside the page, so printOn() lifts every @media print rule (the page's
     own and kitchen.css's) into a plain <style>, which is what print media
     does; printOff() takes it away. Needs --allow-file-access-from-files. --- */
  function printOn(){
    var css='';
    [].forEach.call(document.styleSheets,function(sh){
      var rules;try{rules=sh.cssRules;}catch(e){fails.push('print: cannot read the rules of '+sh.href);return;}
      [].forEach.call(rules,function(r){
        if(r.type===CSSRule.MEDIA_RULE&&/\bprint\b/.test(r.media.mediaText))[].forEach.call(r.cssRules,function(x){css+=x.cssText+'\n';});
      });
    });
    var st=document.createElement('style');st.id='__printSim';st.textContent=css;document.head.appendChild(st);
  }
  function printOff(){var st=document.getElementById('__printSim');if(st)st.remove();}
  function shown(el){return !!el&&el.getClientRects().length>0&&getComputedStyle(el).visibility!=='hidden';}
  var PRINTED=/^Printed (Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec) \d{1,2}, \d{4} · from the Recipe Database$/;
  function printChecks(tag, want, label){
    var own=[].map.call(document.querySelectorAll('head style'),function(x){return x.textContent;}).join('\n');
    ok(tag+'the page’s own <style> has an @media print block', /@media\s+print\s*\{/.test(own));
    var btn=document.getElementById('printBtn');
    ok(tag+'a Print button says "'+label+'"', !!btn&&btn.tagName==='BUTTON'&&btn.type==='button'&&txt(btn)===label&&shown(btn), btn&&txt(btn));
    ok(tag+'the Print button is a big tap target (≥44px)', !!btn&&btn.getBoundingClientRect().height>=44, btn&&btn.getBoundingClientRect().height);
    ok(tag+'on screen the printed-on line is hidden', [].every.call(document.querySelectorAll('.kit-printed'),function(e){return !shown(e);}));
    ok(tag+'on screen the all-kits print sheets are hidden', !shown(document.getElementById('printAll')));
    printOn();
    try{
      var sheets=[].filter.call(document.querySelectorAll('.kit-sheet'),shown);
      var slugs=sheets.map(function(x){return x.getAttribute('data-slug');});
      ok(tag+'in print: exactly '+want.length+' sheet(s), the right one(s), in order', JSON.stringify(slugs)===JSON.stringify(want), slugs);
      ok(tag+'in print: the list is hidden', !shown(document.getElementById('kitList'))&&!document.querySelector('.kit-item')||[].every.call(document.querySelectorAll('.kit-item'),function(a){return !shown(a);}));
      ok(tag+'in print: the Print button, Back link and header are hidden', !shown(btn)&&!shown(document.getElementById('backLink'))&&!shown(document.querySelector('.header')));
      ok(tag+'in print: each sheet after the first starts a new page', sheets.every(function(x,i){var b=getComputedStyle(x).breakBefore;return i===0?b!=='page':b==='page';}), sheets.map(function(x){return getComputedStyle(x).breakBefore;}));
      ok(tag+'in print: every sheet carries the printed-on line', sheets.length>0&&sheets.every(function(x){var l=x.querySelector('.kit-printed');return shown(l)&&PRINTED.test(txt(l));}), sheets.map(function(x){return txt(x.querySelector('.kit-printed'));}));
      var filled=[].filter.call(document.body.querySelectorAll('*'),function(e){
        if(!shown(e))return false;var cs=getComputedStyle(e),bg=cs.backgroundColor;
        return cs.backgroundImage!=='none'||!(bg==='rgba(0, 0, 0, 0)'||bg==='transparent'||bg==='rgb(255, 255, 255)');
      }).map(function(e){return e.className+' '+getComputedStyle(e).backgroundColor;});
      ok(tag+'in print: nothing that prints has a background fill', filled.length===0, filled.slice(0,5));
      var rings=[].filter.call(document.querySelectorAll('.kit-num'),shown);
      ok(tag+'in print: rings keep their digit and an ink border', rings.every(function(n){var cs=getComputedStyle(n);return /^\d+$/.test(txt(n))&&parseFloat(cs.borderTopWidth)>=2&&cs.borderTopStyle==='solid'&&cs.borderTopColor!=='rgba(0, 0, 0, 0)';}));
      var loud=[].filter.call(document.querySelectorAll('.kit-unsorted'),shown);
      ok(tag+'in print: "Not sorted yet" / "Recipe not found" keep the heavy border', loud.every(function(u){return parseFloat(getComputedStyle(u).borderTopWidth)>=3;}));
      H.printLoud=loud.length;H.printRings=rings.length;
    }finally{printOff();}
    /* the button prints and asks the server nothing */
    var n=0,orig=window.print,before=H.reqs.length;window.print=function(){n++;};
    if(btn)btn.click();
    window.print=orig;
    ok(tag+'the Print button calls window.print() once, and sends no request', n===1&&H.reqs.length===before, [n,H.reqs.length-before]);
  }
  var ALL8=H.fx.kits.map(function(k){return k.slug;});
  /* steps run in order, each after the page has had time to redraw */
  function steps(list){
    var i=0;(function next(){if(i>=list.length){common();finish();return;}var f=list[i++];f();setTimeout(next,150);})();
  }
  function run(){
    var S=H.scen,E=H.fx.expect;
    function flag(slug){var a=document.querySelector('.kit-item[data-slug="'+slug+'"] .kit-item-n');return a?[txt(a),parseInt(getComputedStyle(a).fontWeight,10),getComputedStyle(a).color]:null;}
    var MSG='Could not load the recipes. Check the signal, then try again.';
    function failed(tag){
      var e=document.querySelector('.empty'),b=e&&e.querySelector('button.link-btn');
      ok(tag+'the plain message, and no sheet or list', !!e&&txt(e).indexOf(MSG)===0&&!document.getElementById('pan')&&!document.querySelector('.kit-item'), txt(document.getElementById('appBody')));
      ok(tag+'a Try again button', !!b&&txt(b)==='Try again');
      return b;
    }
    if(S==='print'){
      return steps([
        function(){printChecks('print, list: ',ALL8,'Print all 8 kits');ok('print, list: rings print on every sheet',H.printRings===H.fx.counts.reduce(function(a,b){return a+b;},0),H.printRings);},
        function(){location.hash='pork-belly';},
        function(){printChecks('print, pork-belly: ',['pork-belly'],'Print this kit');},
        function(){location.hash='mac-and-cheese';},
        function(){printChecks('print, mac-and-cheese: ',['mac-and-cheese'],'Print this kit');ok('print, mac-and-cheese: all 11 rings print',H.printRings===11,H.printRings);},
        function(){document.getElementById('backLink').click();},
        function(){printChecks('print, back on the list: ',ALL8,'Print all 8 kits');}
      ]);
    }
    if(S==='missing'||S==='archived'){
      var slug=S==='missing'?'gastrique':'dumpling',K=kitBy(slug);
      return steps([
        function(){printChecks(S+', list: ',ALL8,'Print all 8 kits');ok(S+': its printed sheet says "tell a manager" too',H.printLoud===1);},
        function(){
          var f=flag(slug),ink=getComputedStyle(document.body).color;
          ok(S+': the list marks it "Recipe not found", in bold ink', !!f&&f[0]==='Recipe not found'&&f[1]>=700&&f[2]===ink, f);
          ok(S+': the other 7 still show their counts', H.fx.kits.every(function(k,i){var g=flag(k.slug);return k.slug===slug||(g&&g[0]===H.fx.counts[i]+' containers');}));
          document.querySelector('.kit-item[data-slug="'+slug+'"]').click();
        },
        function(){
          var nf=document.getElementById('notFound');
          ok(S+': its sheet says "Recipe not found in the Recipe Database — tell a manager."', !!nf&&txt(nf)==='Recipe not found in the Recipe Database — tell a manager.', txt(document.getElementById('appBody')));
          ok(S+': never an empty sheet - no containers, no pan step', !document.querySelector('.kit-box')&&!document.getElementById('pan'));
          ok(S+': the kit still says which kit it is', txt(document.querySelector('.kit-title'))===K.name);
          ok(S+': no stray filler under the title', txt(document.querySelector('.kit-from'))==='');
          document.getElementById('backLink').click();
        },
        function(){ok(S+': Back returns to the list', document.querySelectorAll('.kit-item').length===8);}
      ]);
    }
    if(S==='lost'){
      function names(){return [].map.call(document.querySelectorAll('.kit-box'),function(b){return [txt(b.querySelector('.kit-num')),txt(b.querySelector('.kit-name'))];});}
      return steps([
        function(){
          ok('lost: the list counts what is left (3, 6, 10)', flag('pork-belly')[0]==='3 containers'&&flag('gastrique')[0]==='6 containers'&&flag('mac-and-cheese')[0]==='10 containers', [flag('pork-belly'),flag('gastrique'),flag('mac-and-cheese')]);
          location.hash='pork-belly';
        },
        function(){
          var b=boxes();
          ok('lost: a deleted line just goes - its container keeps the rest', b.length===3&&JSON.stringify(b[0][1])===JSON.stringify(["6 each white onion","6 each carrot","4 each heads of garlic, halved"]), b);
          ok('lost: and nothing goes to "Not sorted yet"', !document.getElementById('unsorted'));
          location.hash='gastrique';
        },
        function(){
          var n=names();
          ok('lost: an emptied container disappears and the numbers close up', JSON.stringify(n)===JSON.stringify([["1","Bacon"],["2","Shallots"],["3","Herbs"],["4","Red wine"],["5","Red wine vinegar"],["6","Horseradish"]]), n);
          ok('lost: the pan counts what is left (5 in, red wine beside)', txt(document.getElementById('pan')).indexOf('All 5 containers into one hotel pan')===0, txt(document.getElementById('pan')));
          location.hash='mac-and-cheese';
        },
        function(){
          var n=names(),parts=[].map.call(document.querySelectorAll('.kit-part'),txt);
          ok('lost: Mac & Cheese closes up to 10, no Macaroni', n.length===10&&n.every(function(x,i){return x[0]===String(i+1)&&x[1]!=='Macaroni';}), n);
          ok('lost: Noodles & assembly keeps its other two', n[8][1]==='Salt for the water'&&n[9][1]==='Herbs'&&JSON.stringify(parts)===JSON.stringify(['Cheese base','Roux base','Noodles & assembly']), {n:n,parts:parts});
        }
      ]);
    }
    if(S==='emptied'){
      return steps([
        function(){
          var f=flag('pickled-onions-peppers');
          ok('emptied: the list says "Needs sorting", in bold', !!f&&f[0]==='Needs sorting'&&f[1]>=700, f);
          location.hash='pickled-onions-peppers';
        },
        function(){
          var un=document.getElementById('unsorted'),app=txt(document.getElementById('appBody'));
          ok('emptied: every unmatched line is in "Not sorted yet"', !!un&&JSON.stringify([].map.call(un.querySelectorAll('.kit-line'),txt))===JSON.stringify(['1 cup Skyr','2 Tbsp Za’atar']), un&&txt(un));
          ok('emptied: it says to tell a manager', /tell a manager/.test(txt(un)));
          ok('emptied: no containers and no pan step', !document.querySelector('.kit-box')&&!document.getElementById('pan'));
          ok('emptied: never "All 0 containers"', !/All 0 container/.test(app), app);
          ok('emptied: "Not in the kit" still shows the water', /Not in the kit/.test(app)&&/1\.5 qt Water/.test(app));
        }
      ]);
    }
    if(S==='fail'||S==='e500'||S==='hang'||S==='failaddr'){
      H.wantReqs=2;
      return steps([
        function(){
          var b=failed(S+': ');
          if(S==='hang')ok('hang: the read carries a timeout, at most 60s', H.reqs[0]&&H.reqs[0].timeout>0&&H.reqs[0].timeout<=60000, H.reqs[0]&&H.reqs[0].timeout);
          ok(S+': one request so far', H.reqs.length===1, H.reqs.length);
          if(b)b.click();
        },
        function(){
          if(S==='failaddr')ok('failaddr: Try again lands on the kit you were on', location.hash==='#mac-and-cheese'&&txt(document.querySelector('.kit-title'))==='Mac & cheese'&&!!document.getElementById('pan'), txt(document.getElementById('appBody')).slice(0,120));
          else ok(S+': Try again works - the list is back', document.querySelectorAll('.kit-item').length===8&&!document.querySelector('.empty'), txt(document.getElementById('appBody')).slice(0,120));
        }
      ]);
    }
    if(S==='reorder'){
      return steps([
        function(){location.hash='gastrique';},
        function(){sheet(kitBy('gastrique'));},
        function(){location.hash='dumpling';},
        function(){sheet(kitBy('dumpling'));}
      ]);
    }
    if(S==='all8'){
      /* open every kit by its address, one after another, as a cook would */
      var st=[];
      H.fx.kits.forEach(function(K){
        st.push(function(){location.hash=K.slug;});
        st.push(function(){
          var got=sheet(K);
          function lineIn(name,line,idx){return got.some(function(g,i){return g[1]===name&&(idx===undefined||i===idx)&&g[3].indexOf(line)>-1;});}
          if(K.slug==='gastrique'){
            ok('longest first: red wine vinegar is not taken by "red wine"', lineIn('Red wine vinegar','4 c. red wine vinegar')&&!lineIn('Red wine','4 c. red wine vinegar'), got);
          }
          if(K.slug==='dumpling'){
            ok('longest first: buttermilk is not taken by "butter"', lineIn('Buttermilk','1\u00bc cup buttermilk')&&!lineIn('Butter','1\u00bc cup buttermilk'), got);
          }
          if(K.slug==='pork-belly'){
            ok('longest first: peppercorns are not taken by "pepper"', lineIn('Braise seasoning','\u00bd cup black peppercorns'), got);
            ok('twice: the first salt goes to the braise seasoning', lineIn('Braise seasoning','1 cup salt'), got);
            ok('twice: the second salt goes to "Not in the kit"', [].some.call(document.querySelectorAll('.kit-out .kit-line'),function(l){return txt(l)==='salt';}));
          }
          if(K.slug==='mac-and-cheese'){
            ok('twice: half & half in recipe order - 1 gets 1.5 qt', lineIn('Half & half','1.5 qt. half & half',0), got);
            ok('twice: half & half in recipe order - 8 gets 4 c.', lineIn('Half & half','4 c. half & half',7), got);
          }
        });
        st.push(function(){document.getElementById('backLink').click();});
        st.push(function(){ok(K.slug+': Back returns to the list', isList().length===8&&!document.getElementById('pan'), txt(document.getElementById('appBody')).slice(0,120));});
      });
      st.push(function(){history.back();});
      st.push(function(){ok('the browser\u2019s own back works too', !!document.getElementById('pan')&&txt(document.querySelector('.kit-title'))==='Mac & cheese', txt(document.querySelector('.kit-title')));});
      return steps(st);
    }
    if(S==='list'){
      return steps([
        function(){ok('no address: the list', !location.hash);listChecks('list: ');},
        function(){document.querySelector('.kit-item[data-slug="pork-belly"]').click();},
        function(){ok('list: tapping a kit opens it, at its address', location.hash==='#pork-belly'&&txt(document.querySelector('.kit-title'))==='Pork belly', location.hash);},
        function(){location.hash='also-not-a-kit';},
        function(){listChecks('list, then a bad address: ');}
      ]);
    }
    if(S==='direct'){
      return steps([function(){sheet(kitBy('mac-and-cheese'));}]);
    }
    if(S==='nope'){
      return steps([function(){listChecks('nope: ');}]);
    }
    var b=boxes(),un=document.getElementById('unsorted');
    ok('the sheet was drawn', !!document.getElementById('pan'), txt(document.getElementById('appBody')).slice(0,200));
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
      printChecks('renamed: ',['spicy-green-sauce'],'Print this kit');
      ok('renamed: "Not sorted yet" prints with its heavy border', H.printLoud===1, H.printLoud);
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
    common();
    finish();
  }
  /* wait for the sheet or the list (or 5s), then assert */
  var t0=Date.now();
  (function wait(){
    if(document.getElementById('pan')||document.querySelector('.kit-item')||document.querySelector('.empty')||Date.now()-t0>5000)setTimeout(run,100);
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
    recipes = RECIPES
    if scen == "reorder":
        recipes = [dict(r, ingredients=REORDER.get(r["id"], r.get("ingredients"))) for r in RECIPES]
    if scen == "missing":      # Gastrique's recipe is gone from the table
        recipes = [r for r in RECIPES if r["id"] != 43]
    if scen == "archived":     # Dumpling's recipe is archived
        recipes = [dict(r, status="archived") if r["id"] == 14 else r for r in RECIPES]
    if scen == "lost":         # lines deleted from three recipes
        cut = {54: "6 each celery\n", 43: "2 c. sugar\n", 46: "2 qt. dried macaroni noodles\n"}
        recipes = []
        for r in RECIPES:
            if r["id"] in cut:
                assert cut[r["id"]] in r["ingredients"]
                r = dict(r, ingredients=r["ingredients"].replace(cut[r["id"]], ""))
            recipes.append(r)
    if scen == "emptied":      # Pickled rewritten so no container keyword matches
        recipes = [dict(r, ingredients="\u2014 BRINE \u2014\n1 cup Skyr\n2 Tbsp Za\u2019atar\n1.5 qt Water")
                   if r["id"] == 24 else r for r in RECIPES]
    plan = {"fail": ["err"], "e500": ["e500"], "hang": ["hang"], "failaddr": ["err"]}.get(scen, [])
    fixtures = {"recipes": recipes, "text": TEXTS.get(scen, GREEN), "expect": EXPECT,
                "kits": KITS8, "counts": LIST_COUNTS, "ids": ALL_IDS, "slice1": list(SLICE1), "plan": plan}
    src = src.replace(marker, HARNESS.replace("__FIXTURES__", json.dumps(fixtures)) + marker, 1)
    # no network, ever: the webfont links would otherwise leave the machine
    src = re.sub(r'<link rel="preconnect"[^>]*>\s*', '', src)
    src = re.sub(r'<link rel="stylesheet" href="https://fonts[^>]*>\s*', '', src)
    return src.replace("</body>", RUNNER + "</body>", 1)


RESULT_RE = re.compile(r'<div id="harnessResults">(.*?)</div>', re.S)


def run_scenario(chrome, path, scen):
    """One Chrome per scenario; poll --dump-dom output for the results div."""
    url = "file://" + path + "?scen=" + scen + "#" + (
        "spicy-green-sauce" if scen in SLICE1 else HASH[scen])
    dom = os.path.join(os.path.dirname(path), "dom-" + scen + ".html")
    err = os.path.join(os.path.dirname(path), "err-" + scen + ".txt")
    with open(dom, "w") as fo, open(err, "w") as fe:
        proc = subprocess.Popen(
            [chrome, "--headless=new", "--disable-gpu", "--no-sandbox",
             "--no-first-run", "--disable-extensions",
             "--disable-background-networking", "--disable-component-update",
             "--disable-default-apps", "--disable-sync",
             "--allow-file-access-from-files",   # print: read kitchen.css's @media print rules
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
