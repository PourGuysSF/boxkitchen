#!/usr/bin/env python3
"""
Behaviour guard for the Recipe Costing page (tempest_recipe_costing.html),
docs/recipe-costing.md, Slice 2: the recipes, read-only, unlinked.

    python3 scripts/check_recipe_costing.py           # fixtures (CI runs this)
    python3 scripts/check_recipe_costing.py --live    # LOCAL ONLY, never in CI:
        # reads the live Recipes rows with one GET, then renders every one of
        # them in the page with every write blocked, and checks the counts
        # (expected 43 recipes / 340 lines / 15 part headers on 2026-11-09; override with
        # LIVE_RECIPES=.. LIVE_LINES=.. LIVE_HEADERS=..)

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

# Slice 3: the price list, the order guide and stored links.
ORDERS = [
    {"id": 11, "name": "Half & half", "vendor": "Birite"},
    {"id": 12, "name": "Velveeta", "vendor": "Birite"},
    {"id": 13, "name": "Butter", "vendor": "Birite"},
    {"id": 14, "name": "Macaroni noodles", "vendor": "Cooks"},
    {"id": 15, "name": "Kosher salt", "vendor": "Birite"},
    {"id": 16, "name": "Cider vinegar", "vendor": "Birite"},
    {"id": 17, "name": "Bay leaves", "vendor": "Cooks"},
]
COSTS = [
    {"id": 1, "name": "Half & half", "order_item_id": 11, "pack_qty": 1, "pack_unit": "1/2 gal", "pack_price": 6, "active": True},
    {"id": 2, "name": "Velveeta", "order_item_id": 12, "pack_qty": 5, "pack_unit": "lb", "pack_price": 18.47, "active": True},
    {"id": 3, "name": "Butter", "order_item_id": 13, "pack_qty": 36, "pack_unit": "lb", "pack_price": 72, "active": True},
    {"id": 4, "name": "Macaroni noodles", "order_item_id": 14, "pack_qty": 20, "pack_unit": "lb", "pack_price": 30, "active": True},
    {"id": 5, "name": "Kosher salt", "order_item_id": 15, "pack_qty": 3, "pack_unit": "lb", "pack_price": None, "active": True},
    {"id": 6, "name": "Old onion", "order_item_id": None, "pack_qty": 50, "pack_unit": "lb", "pack_price": 30, "active": False},
    {"id": 7, "name": "Cider vinegar", "order_item_id": 16, "pack_qty": 1, "pack_unit": "gal", "pack_price": 16.40, "active": True},
    {"id": 8, "name": "Soy sauce", "order_item_id": None, "pack_qty": 1, "pack_unit": "gal", "pack_price": 20, "active": True},
]
def L(i, text, qty=None, unit=None, cost=None, skip=False, occ=1, comp=None, name=None):
    return {"id": i, "recipe_id": 104, "line_text": text, "occurrence": occ, "component": comp,
            "qty": qty, "unit": unit, "ingredient_cost_id": cost, "sub_recipe_id": None,
            "skip": skip, "linked_name": name, "active": True}
LINKS = [
    L(1, "1.5 qt. half & half", 1.5, "qt", 1, comp="— CHEESE BASE —", name="Half & half"),
    L(2, "2.5 lb. Velveeta cheese", 2.5, "lb", 2, comp="— CHEESE BASE —", name="Velveeta"),
    L(3, "8 oz. butter", 8, "oz", 3, comp="— CHEESE BASE —", name="Butter"),
    L(4, "2 qt. dried macaroni noodles", 2, "qt", 4, comp="— NOODLES —", name="Macaroni noodles"),
    L(5, "½ c. salt", 0.5, "cup", 5, comp="— NOODLES —", name="Kosher salt"),
    L(6, "2 bay leaves", skip=True, comp="— NOODLES —"),
]

# Step 4: the guards. A renamed item, a retired price, an edited line, a skipped
# line edited away, and the second of two identical lines.
LINKS_GUARDS = [
    L(1, "1 qt. half & half", 1, "qt", 1, comp="— CHEESE BASE —", name="Half & half"),
    L(2, "2.5 lb. Velveeta cheese", 2.5, "lb", 2, comp="— CHEESE BASE —", name="Heirloom tomato"),
    L(3, "8 oz. butter", 8, "oz", 3, comp="— CHEESE BASE —", name="  BUTTER "),
    L(4, "5# <b>onion</b>", 5, "lb", 6, comp="— NOODLES —", name="Old onion"),
    L(5, "old skipped line", skip=True),
    dict(L(6, "salt", 1, "tsp", 5, occ=2, name="Kosher salt"), recipe_id=105),
]
PORK = {"id": 105, "name": "Pork Belly", "category": "Protein", "station": "Grill",
        "status": "active", "ingredients": "salt\n2 each carrot\nsalt"}

# Slice 4: conversions. One price (Macaroni noodles, 20 lb for $30) linked by
# volume in two recipes, by weight once, and once on an orphan line (its text is
# gone from the recipe, so the "used by" count must leave it out).
PASTA = {"id": 106, "name": "Pasta Salad", "category": "Side", "station": "Garde",
         "status": "active", "ingredients": "1 cup macaroni\n1 lb macaroni\nparsley"}
LINKS_CONV = [
    L(1, "2 qt. dried macaroni noodles", 2, "qt", 4, comp="— NOODLES —", name="Macaroni noodles"),
    L(2, "8 oz. butter", 8, "oz", 3, comp="— CHEESE BASE —", name="Butter"),
    dict(L(3, "1 cup macaroni", 1, "cup", 4, name="Macaroni noodles"), recipe_id=106),
    dict(L(4, "1 lb macaroni", 1, "lb", 4, name="Macaroni noodles"), recipe_id=106),
    dict(L(5, "gone macaroni line", 1, "cup", 4, name="Macaroni noodles"), recipe_id=106),
    dict(L(6, "parsley", skip=True), recipe_id=106),
]
CONV_OLD = {"id": 900, "location": "Tempest", "ingredient_cost_id": 4, "from_kind": "volume",
            "from_qty": 1, "from_unit": "qt", "to_qty": 0.8, "to_unit": "lb",
            "estimate": True, "note": "dry", "updated_at": "2026-11-01T00:00:00Z"}

SCENARIOS = ("ok", "fail", "gate", "links", "guards",
             # step 5: the write path
             "write", "hang", "lost", "retry", "reject", "oldlink", "oldfail", "dismiss",
             # Slice 4: conversions
             "conv", "convask", "convlost", "convstale", "convoz")
CONV_SCEN = '{conv:1,convask:1,convlost:1,convstale:1,convoz:1}'
CONV_OLD_SCEN = '{convask:1,convstale:1,convoz:1}'

# Deliberate breaks of the conversion write path, each of which must be caught.
BREAKS = [
    ("the double-tap guard removed", "convSaving||!cv", "!cv", ("conv",)),
    ("the magnitude ask skipped", "if(ask){showAsk(ask);return;}", "", ("convask",)),
    ("the ask kept after the number changes", "if(cv.asking&&!convSaving)showAsk(null);", "", ("convask",)),
    ("a pre-filled answer", "document.getElementById('cvQty').value='';",
     "document.getElementById('cvQty').value=old?String(old.to_qty):'';", ("convask", "convstale")),
]

GATE_RE = re.compile(r"<script>\s*//\s*Site-password gate.*?</script>", re.S)

HARNESS = r"""
<script>
/* ---- test harness: installed BEFORE the page script parses ----
   A stateful recipe_lines, so a write that lands is there for the next read,
   and per-write fates (consumed in order) to lose, refuse or hold a write:
     'ok'      lands, answers 201 with the row
     'lost'    lands, the answer never comes (onerror)
     'drop'    lost before the table: nothing written, onerror
     'reject'  the server says no (400), nothing written
     'gateway' lands, a gateway answers 502
     'hang'    held, unanswered, until __h.release() lands it
   nextGet: fates for recipe_lines GETs made after the first load ('fail'). */
(function(){
  var SCEN=(location.hash||'#ok').slice(1);
  var READ_ONLY={ok:1,fail:1,gate:1,links:1,guards:1,live:1};
  var ROWS=__ROWS__, COSTS=__COSTS__, ORDERS=__ORDERS__, CONVS=__CONVS__;
  var GUARDS=__LINKS_GUARDS__;
  var CS=CONV_SCEN[SCEN];
  var LINKS=(SCEN==="links")?__LINKS__:CS?__LINKS_CONV__:(GUARDS_SCEN[SCEN]?GUARDS:[]);
  if(GUARDS_SCEN[SCEN])ROWS=ROWS.concat([__PORK__]);
  if(CS){ROWS=ROWS.concat([__PASTA__]);if(CONV_OLD_SCEN[SCEN])CONVS=[__CONV_OLD__];}
  /* a pack re-entered: in another kind (lb -> case), or within its kind (lb -> oz) */
  if(SCEN==='convstale'||SCEN==='convoz')COSTS=COSTS.map(function(c){
    if(c.id!==4)return c;c=JSON.parse(JSON.stringify(c));
    if(SCEN==='convstale'){c.pack_qty=1;c.pack_unit='case';}else{c.pack_qty=320;c.pack_unit='oz';}return c;});
  var convs=JSON.parse(JSON.stringify(CONVS)), nextConvId=950;
  var server=JSON.parse(JSON.stringify(LINKS)), nextId=500, loads=0;
  var H=window.__h={scen:SCEN,reqs:[],writes:[],bad:[],fails:[],log:[],nextWrite:[],nextGet:[],nextConvGet:[],held:[],server:server,convs:convs,checks:[]};
  try{ if(SCEN==='gate')sessionStorage.removeItem('boxkitchen_mgr'); else sessionStorage.setItem('boxkitchen_mgr','1'); }catch(e){}
  function param(u,k){var m=new RegExp('[?&]'+k+'=eq\\.([^&]*)').exec(u);return m?decodeURIComponent(m[1]):null;}
  /* ingredient_conversions as the database holds it: one row per
     (ingredient_cost_id, from_kind), and the table's checks enforced */
  function applyConv(w){
    var b=w.body,row=null;
    if(!(b.from_qty===1&&b.to_qty>0&&/^(weight|volume|each|[a-z]+)$/.test(b.from_kind)))H.checks.push('check failed: '+JSON.stringify(b));
    for(var i=0;i<convs.length;i++)if(Number(convs[i].ingredient_cost_id)===b.ingredient_cost_id&&convs[i].from_kind===b.from_kind)row=convs[i];
    if(row){for(var k in b)row[k]=b[k];}
    else{row={id:nextConvId++};for(var k2 in b)row[k2]=b[k2];convs.push(row);}
    return JSON.parse(JSON.stringify(row));
  }
  function apply(w){
    if(/ingredient_conversions\?/.test(w.u))return applyConv(w);
    if(w.m==='POST'){
      var b=w.body,row=null;
      for(var i=0;i<server.length;i++){var s=server[i];
        if(Number(s.recipe_id)===b.recipe_id&&s.line_text===b.line_text&&Number(s.occurrence)===b.occurrence)row=s;}
      if(row){for(var k in b)row[k]=b[k];}
      else{row={id:nextId++,sub_recipe_id:null};for(var k2 in b)row[k2]=b[k2];server.push(row);}
      return JSON.parse(JSON.stringify(row));
    }
    var id=Number(param(w.u,'id'));
    for(var j=0;j<server.length;j++)if(server[j].id===id){for(var k3 in w.body)server[j][k3]=w.body[k3];return JSON.parse(JSON.stringify(server[j]));}
    return null;
  }
  function X(){this.status=0;this.responseText='';this.timeout=0;this.hdr={};}
  X.prototype.open=function(m,u){this.m=m;this.u=u;};
  X.prototype.setRequestHeader=function(k,v){this.hdr[k]=v;};
  X.prototype.send=function(body){
    var self=this;
    H.reqs.push({m:self.m,u:self.u});
    if(self.m!=='GET'){
      var w={m:self.m,u:self.u,body:body?JSON.parse(body):null,prefer:self.hdr.Prefer||''};
      H.writes.push(w);
      var okTable=CS?/\/rest\/v1\/ingredient_conversions\?/.test(self.u)&&self.m==='POST':/\/rest\/v1\/recipe_lines\?/.test(self.u);
      if(READ_ONLY[SCEN]||self.m==='DELETE'||!okTable){H.bad.push(self.m+' '+self.u);setTimeout(function(){self.onerror&&self.onerror();},5);return;}
      var fate=H.nextWrite.shift()||'ok';
      function answer(){var row=apply(w);self.status=self.m==='POST'?201:200;self.responseText=JSON.stringify(row?[row]:[]);self.onload&&self.onload();}
      if(fate==='hang'){H.held.push(answer);return;}
      setTimeout(function(){
        if(fate==='ok')answer();
        else if(fate==='lost'){apply(w);self.onerror&&self.onerror();}
        else if(fate==='drop'){self.onerror&&self.onerror();}
        else if(fate==='reject'){self.status=400;self.responseText='{"message":"refused"}';self.onload&&self.onload();}
        else if(fate==='gateway'){apply(w);self.status=502;self.responseText='bad gateway';self.onload&&self.onload();}
      },10);
      return;
    }
    setTimeout(function(){
      if(SCEN==='fail'){self.onerror&&self.onerror();return;}
      var m=/\/rest\/v1\/(\w+)\?/.exec(self.u),t=m&&m[1],rows;
      if(t==='recipe_lines'){
        if(loads++>0&&H.nextGet.shift()==='fail'){self.onerror&&self.onerror();return;}
        rows=server.filter(function(s){
          if(/active=eq\.true/.test(self.u)&&s.active!==true)return false;
          var f={id:1,recipe_id:1,occurrence:1};
          for(var k in f){var v=param(self.u,k);if(v!==null&&Number(s[k])!==Number(v))return false;}
          var lt=param(self.u,'line_text');if(lt!==null&&s.line_text!==lt)return false;
          return true;});
      }else if(t==='ingredient_conversions'){
        if(param(self.u,'ingredient_cost_id')!==null&&H.nextConvGet.shift()==='fail'){self.onerror&&self.onerror();return;}
        rows=convs.filter(function(c){
          var ci=param(self.u,'ingredient_cost_id'),fk=param(self.u,'from_kind');
          return (ci===null||Number(c.ingredient_cost_id)===Number(ci))&&(fk===null||c.from_kind===fk);});
        rows=JSON.parse(JSON.stringify(rows));
      }else rows={Recipes:ROWS,ingredient_costs:COSTS,order_items:ORDERS}[t];
      if(rows){self.status=200;self.responseText=JSON.stringify(rows);}
      else{self.status=404;self.responseText='[]';}
      self.onload&&self.onload();
    },10);
  };
  H.release=function(){var a=H.held.splice(0);a.forEach(function(f){f();});};
  window.XMLHttpRequest=X;
})();
</script>
""".replace("GUARDS_SCEN", '{guards:1,oldlink:1,oldfail:1,dismiss:1}').replace("CONV_OLD_SCEN", CONV_OLD_SCEN).replace("CONV_SCEN", CONV_SCEN)


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
      var tabs=H.reqs.map(function(q){return (/\/rest\/v1\/(\w+)\?/.exec(q.u)||[])[1];}).sort().join(',');
      ok(tabs==='Recipes,ingredient_conversions,ingredient_costs,order_items,recipe_lines','read: Recipes, the price list, the order guide, recipe_lines and the conversions, once each; got '+tabs);
      ok(/select=id,name,category,station,status,ingredients(&|$)/.test((H.reqs[0]||{}).u),'read: Recipes select= names the columns');
      H.reqs.forEach(function(q){
        ok(/[?&]select=[a-z_,]+(&|$)/.test(q.u)&&!/select=\*/.test(q.u),'read: select= names the columns: '+q.u.split('?')[0]);
        ok(/[?&]location=eq\.Tempest(&|$)/.test(q.u),'read: location=eq.Tempest: '+q.u.split('?')[0]);
      });
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

    if(H.scen==='links'){
      /* Slice 3, read side: each line's state, and the editor. */
      openRecipe(104);
      var ls=[].map.call(document.querySelectorAll('#recipeBody .rc-line'),function(el){return [].map.call(el.querySelector('.rc-read').children,txt).join(' ');});
      var want=[
        [/^Half & half · Birite · 1\.5 qt \$4\.50$/,'costed by volume'],
        [/^Velveeta · Birite · 2\.5 lb \$9\.24$/,'costed by weight, shown to the cent'],
        [/^Butter · Birite · 8 oz \$1\.00$/,'oz costed against lb, as weight'],
        [/^Macaroni noodles · Cooks · 2 qt needs a conversion Set conversion$/,'qt against lb: needs a conversion'],
        [/^Kosher salt · Birite · 0\.5 cup no price yet Price →$/,'linked, no price: no price yet · Price →'],
        [/not linked$/,'no stored link: not linked'],
        [/^not costed on purpose$/,'skip: not costed on purpose']];
      // Mac & Cheese order: 1.5 qt, 2.5 lb, 8 oz, 2 qt, ½ c, 5# onion, 2 bay leaves
      var expect=want;
      for(var i=0;i<expect.length;i++)ok(expect[i][0].test(ls[i]||''),'state: '+expect[i][1]+'; got '+JSON.stringify(ls[i]));
      var pl=document.querySelector('#recipeBody .rc-price-link');
      ok(pl&&pl.getAttribute('href')==='tempest_costing.html','state: Price → goes to the price list, no filter in the address');
      var c1=document.querySelectorAll('#recipeBody .rc-line')[0];
      ok(parseFloat(getComputedStyle(c1).height)>=44,'css: a line is a 44px tap target');
      ok(!/\$0\.00/.test(txt(document.getElementById('recipeBody'))),'state: no line shows $0.00');

      // the editor on a not-linked line whose filter matches exactly ONE row
      openRecipe(102);
      openLink(2);                               // 1⅓ cups cider vinegar
      var mod=document.getElementById('linkModal');
      ok(shown(mod),'editor: tapping a line opens the editor');
      ok(txt(document.getElementById('lkTitle'))==='1⅓ cups cider vinegar','editor: titled with the line exactly as written');
      ok(document.getElementById('pickFilter').value==='cider vinegar','editor: the filter starts with the line\'s words; got '+JSON.stringify(document.getElementById('pickFilter').value));
      var tap=document.querySelectorAll('#pickList .pick-row:not(.pick-off)');
      ok(tap.length===1,'editor: exactly one row matches, got '+tap.length);
      ok(pickId===null&&shown(document.getElementById('pickChoose'))&&!shown(document.getElementById('pickChosen')),'NOTHING PICKED: one match is still not picked for you');
      ok(document.getElementById('lkSave').disabled,'editor: Save is off until something is picked');
      ok(document.getElementById('lkQty').value==='1.333'&&document.getElementById('lkUnit').value==='cup','editor: amount and unit pre-filled from the reader; got '+document.getElementById('lkQty').value+' '+document.getElementById('lkUnit').value);
      ['pickFilter','lkQty','lkUnit'].forEach(function(id){
        ok(parseFloat(getComputedStyle(document.getElementById(id)).fontSize)>=16,'css: #'+id+' renders at 16px or more (#135), got '+getComputedStyle(document.getElementById(id)).fontSize);});
      var units=[].map.call(document.querySelectorAll('#lkUnit option'),function(o){return o.value;}).filter(Boolean);
      ok(units.join(',')===RecipeMath.units().map(function(u){return u.unit;}).join(','),'editor: the unit box offers RecipeMath.units()');
      tap[0].click();
      ok(pickId===7&&shown(document.getElementById('pickChosen')),'editor: a tap is the pick');
      ok(/Cider vinegar/.test(txt(document.getElementById('pickChosenN'))),'editor: the chosen line names the item');
      ok(/→ \$1\.37$/.test(txt(document.getElementById('lkPreview'))),'editor: the preview costs it; got '+txt(document.getElementById('lkPreview')));
      ok(!document.getElementById('lkSave').disabled,'editor: Save is on once picked with an amount and unit');
      document.getElementById('pickChange').click();
      ok(pickId===null&&document.getElementById('lkQty').value===''&&document.getElementById('lkUnit').value===''&&shown(document.getElementById('pickChoose')),'Change: clears the pick and the amount');
      ok(document.getElementById('lkSave').disabled,'Change: Save is off again');

      // unpriced rows and order-guide items are listed but cannot be picked; retired rows are not listed
      var f=document.getElementById('pickFilter');
      f.value='salt';renderPick();
      var off=document.querySelector('#pickList .pick-row.pick-off');
      ok(off&&/no price yet — price it first/.test(txt(off)),'picker: an unpriced row says no price yet — price it first');
      off&&off.click();
      ok(pickId===null,'picker: an unpriced row cannot be picked');
      f.value='bay';renderPick();
      ok(/Bay leaves/.test(txt(document.getElementById('pickList')))&&!!document.querySelector('#pickList .pick-row.pick-off'),'picker: an order-guide item with no price row is listed, unpickable');
      f.value='old onion';renderPick();
      ok(!document.querySelector('#pickList .pick-row'),'picker: a retired row is not listed');
      f.value='';renderPick();
      ok(document.querySelectorAll('#pickList .pick-row').length===8,'picker: 7 active rows + 1 guide item with no row, got '+document.querySelectorAll('#pickList .pick-row').length);
      ok(pickId===null,'NOTHING PICKED: clearing the filter picks nothing');
      closeLink();
      ok(!shown(mod),'editor: Cancel closes it');

      // a two-amounts line opens with the amount box empty
      openLink(1);
      ok(document.getElementById('lkQty').value===''&&document.getElementById('lkUnit').value==='','editor: a two-amounts line opens with amount and unit empty');
      closeLink();

      // the oz hint
      openLink(0);                               // 6 oz. dried ancho chiles
      f.value='soy';renderPick();
      var soy=document.querySelector('#pickList .pick-row:not(.pick-off)');soy&&soy.click();
      ok(shown(document.getElementById('lkOzHint'))&&/fluid ounces/.test(txt(document.getElementById('lkOzHint'))),'oz hint: oz against a price sold by volume asks about fl oz');
      ok(document.getElementById('lkUnit').value==='oz','oz hint: words only - the unit is not changed for you');
      document.getElementById('lkUnit').value='fl oz';showLinkState();
      ok(!shown(document.getElementById('lkOzHint')),'oz hint: gone once the unit is fl oz');
      closeLink();

      // an existing link opens showing its own earlier pick
      openRecipe(104);openLink(2);               // 2.5 lb. Velveeta cheese
      ok(pickId===2&&/Velveeta/.test(txt(document.getElementById('pickChosenN')))&&document.getElementById('lkQty').value==='2.5','editor: an existing link opens with what it is linked to');
      closeLink();
    }

    if(H.scen==='guards'){
      /* Slice 3, step 4: each guard stops the line counting, with its reason. */
      function states(){return [].map.call(document.querySelectorAll('#recipeBody .rc-line.tap'),function(el){return [].map.call(el.querySelector('.rc-read').children,txt).join(' ');});}
      openRecipe(104);
      var g=states();
      ok(/not linked$/.test(g[0]),'match: an edited line (1 qt -> 1.5 qt) is not linked; got '+JSON.stringify(g[0]));
      ok(g[1]==='2.5 lb renamed — linked as Heirloom tomato, now Velveeta — check','renamed: says what it was linked as and what it is now; got '+JSON.stringify(g[1]));
      ok(/^Butter · Birite · 8 oz \$1\.00$/.test(g[2]),'renamed: case and spacing alone are not a rename; got '+JSON.stringify(g[2]));
      ok(/price retired — relink$/.test(g[5]),'retired: a retired price row says price retired — relink; got '+JSON.stringify(g[5]));
      ok(!/\$/.test(g[1])&&!/\$/.test(g[5]),'guards: a renamed or retired line shows no cost');
      var gone=[].map.call(document.querySelectorAll('#recipeBody .rc-gone'),function(el){return txt(el.querySelector('.rc-text'));});
      ok(JSON.stringify(gone)===JSON.stringify(['1 qt. half & half','old skipped line']),'No longer in the recipe: lists the unmatched stored lines; got '+JSON.stringify(gone));
      ok(document.querySelectorAll('#recipeBody .rc-gone .rc-dismiss').length===2,'No longer in the recipe: each has Dismiss');
      ok(/No longer in the recipe/.test(txt(document.querySelector('#recipeBody .rc-gone-head'))),'No longer in the recipe: headed as such');
      var dm=document.querySelector('#recipeBody .rc-dismiss');
      ok(dm&&parseFloat(getComputedStyle(dm).height)>=44,'css: Dismiss is a 44px tap target');
      ok(dm&&getComputedStyle(dm).color!==getComputedStyle(document.documentElement).getPropertyValue('--danger'),'css: Dismiss is not drawn as destructive');

      // Use the old link: offered on the NOT LINKED line, fills only
      openLink(1);
      var olds=document.querySelectorAll('#lkOld .lk-old-btn');
      ok(olds.length===1&&txt(olds[0])==='Use the old link: Half & half · Birite, 1 qt','old link: one offer, the linked old line only (not the skipped one); got '+[].map.call(olds,txt).join(' | '));
      ok(pickId===null&&shown(document.getElementById('pickChoose')),'NOTHING PICKED: the old link is offered, never applied');
      olds[0]&&olds[0].click();
      ok(pickId===1&&document.getElementById('lkQty').value==='1'&&document.getElementById('lkUnit').value==='qt'&&lk.oldId===1,'old link: a tap fills pick, amount and unit');
      ok(shown(mod=document.getElementById('linkModal'))&&!document.getElementById('lkSave').disabled,'old link: the editor stays open; Save is still yours');
      document.getElementById('pickChange').click();
      ok(lk.oldId===null&&pickId===null,'old link: Change forgets it');
      closeLink();
      openLink(2);
      ok(!shown(document.getElementById('lkOld')),'old link: not offered on a line that already has a link');
      closeLink();
      openLink(7);                                // 5# <b>onion</b>, linked to a retired row
      ok(pickId===null&&shown(document.getElementById('pickChoose')),'retired: the editor opens on the chooser, nothing picked');
      closeLink();

      // identical lines are told apart by occurrence
      openRecipe(105);
      var p=states();
      ok(/not linked$/.test(p[0])&&/not linked$/.test(p[1])&&/no price yet/.test(p[2]),'occurrence: the second "salt" holds the link, the first does not; got '+JSON.stringify(p));
      ok(!document.querySelector('#recipeBody .rc-gone'),'occurrence: a matched second line is not "no longer in the recipe"');
    }

    /* ---- Slice 3, step 5: the write path ---- */
    function posts(){return H.writes.filter(function(w){return w.m==='POST';});}
    function patches(){return H.writes.filter(function(w){return w.m==='PATCH';});}
    function rowsFor(rid,text,occ){return H.server.filter(function(s){return Number(s.recipe_id)===rid&&s.line_text===text&&Number(s.occurrence)===(occ||1);});}
    function lineStates(){return [].map.call(document.querySelectorAll('#recipeBody .rc-line.tap'),function(el){return [].map.call(el.querySelector('.rc-read').children,txt).join(' ');});}
    function pick(word){var f=document.getElementById('pickFilter');f.value=word;renderPick();var r=document.querySelector('#pickList .pick-row:not(.pick-off)');r&&r.click();}
    function toast(){return txt(document.getElementById('toast'));}
    function keysOf(w){return JSON.stringify(Object.keys(w.body).sort());}
    var LINK_KEYS=JSON.stringify(['active','component','ingredient_cost_id','line_text','linked_name','location','occurrence','qty','recipe_id','skip','unit','updated_at']);
    function checkUpsert(w,label){
      ok(/\/rest\/v1\/recipe_lines\?on_conflict=recipe_id,line_text,occurrence$/.test(w.u),label+': POST recipe_lines?on_conflict=recipe_id,line_text,occurrence; got '+w.u);
      ok(/resolution=merge-duplicates/.test(w.prefer),label+': Prefer: resolution=merge-duplicates; got '+w.prefer);
      ok(keysOf(w)===LINK_KEYS,label+': exactly the columns of ruling 7, never sub_recipe_id; got '+keysOf(w));
      ok(typeof w.body.updated_at==='string'&&!isNaN(Date.parse(w.body.updated_at)),label+': updated_at is a timestamp');
    }
    var steps=[];
    function step(f){steps.push(f);}

    if(H.scen==='write'){
      // LINK: the not-linked "1⅓ cups cider vinegar", picked by a tap
      step(function(){openRecipe(102);openLink(2);pick('cider vinegar');
        ok(pickId===7,'link: picked by a tap');document.getElementById('lkSave').click();});
      step(function(){
        var w=posts()[0]||{body:{}};
        ok(posts().length===1,'link: one POST, got '+posts().length);
        checkUpsert(w,'link');
        var b=w.body;
        ok(b.location==='Tempest'&&b.recipe_id===102&&b.line_text==='1⅓ cups cider vinegar'&&b.occurrence===1&&b.component===null,'link: recipe, line exactly as written, occurrence 1, no part; got '+JSON.stringify(b));
        ok(Math.abs(b.qty-4/3)<1e-12&&b.qty!==1.333,'link: qty saved UNROUNDED (1⅓, not the 1.333 on screen); got '+b.qty);
        ok(b.unit==='cup'&&b.ingredient_cost_id===7&&b.linked_name==='Cider vinegar'&&b.skip===false&&b.active===true,'link: unit, price row, its name at that moment, skip false, active');
        ok(!shown(document.getElementById('linkModal')),'link: the editor closes once saved');
        ok(/^Cider vinegar · Birite · 1\.333 cup \$1\.37$/.test(lineStates()[2]),'link: the line now shows its cost; got '+JSON.stringify(lineStates()[2]));
        ok(/Linked/.test(toast()),'link: says so');
        // SKIP: "Salt TT"
        openLink(3);document.getElementById('lkSkip').click();
      });
      step(function(){
        var w=posts()[1]||{body:{}};
        checkUpsert(w,'skip');
        var b=w.body;
        ok(b.skip===true&&b.qty===null&&b.unit===null&&b.ingredient_cost_id===null&&b.linked_name===null&&b.line_text==='Salt TT','skip: skip true and no target; got '+JSON.stringify(b));
        ok(lineStates()[3]==='not costed on purpose','skip: the line says not costed on purpose; got '+JSON.stringify(lineStates()[3]));
        // CHANGE: re-open the linked cider line, Change, pick soy, 2 cup
        openLink(2);
        ok(pickId===7,'change: the linked line opens with its pick');
        document.getElementById('pickChange').click();
        ok(pickId===null&&document.getElementById('lkQty').value==='','change: Change clears the pick and the amount');
        pick('soy');document.getElementById('lkQty').value='2';document.getElementById('lkUnit').value='cup';showLinkState();
        document.getElementById('lkSave').click();
      });
      step(function(){
        var w=posts()[2]||{body:{}};
        checkUpsert(w,'change');
        ok(w.body.ingredient_cost_id===8&&w.body.qty===2&&w.body.linked_name==='Soy sauce','change: the new pick and amount; got '+JSON.stringify(w.body));
        ok(rowsFor(102,'1⅓ cups cider vinegar').length===1&&rowsFor(102,'1⅓ cups cider vinegar')[0].ingredient_cost_id===8,'change: still ONE row for the line, now pointing at the new item');
        ok(H.server.length===2,'link + skip + change = 2 rows, got '+H.server.length);
      });
    }

    if(H.scen==='hang'){
      // DOUBLE TAP and the in-flight lock
      step(function(){openRecipe(102);openLink(0);pick('soy');
        H.nextWrite.push('hang');
        var s=document.getElementById('lkSave');s.click();s.click();saveLink();skipLine();});
      step(function(){
        ok(posts().length===1,'double tap: one write, got '+posts().length);
        ['lkQty','lkUnit','pickFilter','pickChange','lkSkip','lkSave','lkCancel'].forEach(function(id){ok(document.getElementById(id).disabled,'in flight: #'+id+' is locked');});
        ok(document.getElementById('pickList').classList.contains('is-saving'),'in flight: the pick list is locked');
        closeLink();
        ok(shown(document.getElementById('linkModal')),'in flight: Cancel / closing does nothing');
        document.getElementById('linkModal').dispatchEvent(new MouseEvent('click',{bubbles:true}));
        ok(shown(document.getElementById('linkModal')),'in flight: a tap outside does nothing');
        changePick();pickItem(7);
        ok(pickId===8,'in flight: the pick cannot be changed');
        showLinkState();
        ok(document.getElementById('lkSave').disabled,'in flight: Save cannot be re-enabled by a redraw');
        var pk=document.getElementById('pickChange');
        ok(/dashed/.test(getComputedStyle(pk).borderStyle)&&getComputedStyle(pk).color!==getComputedStyle(document.getElementById('lkSkip')).borderColor,'css: locked reads as a dashed edge');
        H.release();
      });
      step(function(){
        ok(posts().length===1&&H.server.length===1,'double tap: one row, got '+H.server.length);
        ok(!shown(document.getElementById('linkModal')),'released: saved and closed');
        ok(/needs a conversion Set conversion$/.test(lineStates()[0]),'saved oz against a gal price: needs a conversion (oz is weight); got '+JSON.stringify(lineStates()[0]));
      });
    }

    if(H.scen==='lost'){
      // the write LANDS but its answer is lost: the page looks, finds it, says saved - no second POST
      step(function(){openRecipe(102);openLink(2);pick('cider');H.nextWrite.push('lost');document.getElementById('lkSave').click();});
      step(function(){
        ok(posts().length===1,'lost answer: no second POST, got '+posts().length);
        var rb=H.reqs.filter(function(q){return q.m==='GET'&&/recipe_lines\?/.test(q.u)&&/line_text=eq\./.test(q.u);});
        ok(rb.length===1&&/recipe_id=eq\.102/.test(rb[0].u)&&/occurrence=eq\.1/.test(rb[0].u)&&/location=eq\.Tempest/.test(rb[0].u),'lost answer: the page reads that line back by its key');
        ok(!shown(document.getElementById('linkModal'))&&/Cider vinegar/.test(lineStates()[2]),'lost answer: found landed, so it is saved and shown');
        ok(H.server.length===1,'lost answer: one row');
        // a 502 from a gateway after the row committed: the same
        openLink(1);pick('cider');document.getElementById('lkQty').value='4';document.getElementById('lkUnit').value='tsp';showLinkState();
        H.nextWrite.push('gateway');document.getElementById('lkSave').click();
      });
      step(function(){
        ok(posts().length===2&&H.server.length===2&&!shown(document.getElementById('linkModal')),'gateway 502 after landing: read back, saved, one row');
        ok(/4 tsp/.test(lineStates()[1]),'a two-amounts line saved with the amount the person typed (4 tsp); got '+JSON.stringify(lineStates()[1]));
      });
    }

    if(H.scen==='retry'){
      // DROPPED response AND the read-back fails: the page cannot know, says so, unlocks; the retry is the same upsert -> one row
      step(function(){openRecipe(102);openLink(2);pick('cider');H.nextWrite.push('lost');H.nextGet.push('fail');document.getElementById('lkSave').click();});
      step(function(){
        ok(shown(document.getElementById('linkModal'))&&!document.getElementById('lkSave').disabled,'unconfirmed: the editor stays open and unlocks');
        ok(/Could not confirm/.test(toast())&&/cannot make a second row/.test(toast()),'unconfirmed: says it could not confirm, and that a retry is safe; got '+JSON.stringify(toast()));
        ok(!/Linked/.test(toast()),'unconfirmed: never claims it saved');
        document.getElementById('lkSave').click();
      });
      step(function(){
        var p=posts();
        ok(p.length===2,'retry: a second POST, got '+p.length);
        ok(p.length===2&&p[0].u===p[1].u&&p[0].body.recipe_id===p[1].body.recipe_id&&p[0].body.line_text===p[1].body.line_text&&p[0].body.occurrence===p[1].body.occurrence,'retry: the same upsert key both times');
        ok(H.server.length===1,'DROPPED RESPONSE + RETRY: one row, got '+H.server.length);
        ok(!shown(document.getElementById('linkModal')),'retry: saved and closed');
        // dropped before the table: nothing landed - the page reads back, finds nothing, does not claim it saved
        openLink(3);H.nextWrite.push('drop');document.getElementById('lkSkip').click();
      });
      step(function(){
        ok(shown(document.getElementById('linkModal'))&&rowsFor(102,'Salt TT').length===0,'dropped before the table: not saved, editor open');
        ok(/Not saved|Could not confirm/.test(toast()),'dropped: says not saved; got '+JSON.stringify(toast()));
        document.getElementById('lkSkip').click();
      });
      step(function(){ok(rowsFor(102,'Salt TT').length===1&&H.server.length===2,'dropped then retried: one row');});
    }

    if(H.scen==='reject'){
      step(function(){openRecipe(102);openLink(2);pick('cider');H.nextWrite.push('reject');document.getElementById('lkSave').click();});
      step(function(){
        ok(shown(document.getElementById('linkModal'))&&!document.getElementById('lkSave').disabled&&pickId===7,'refused: editor open, unlocked, pick kept');
        ok(/refused/.test(toast())&&document.getElementById('toast').classList.contains('error'),'refused: an error toast says so');
        ok(H.server.length===0&&posts().length===1,'refused: nothing written, and no automatic retry');
      });
    }

    if(H.scen==='oldlink'||H.scen==='oldfail'){
      step(function(){openRecipe(104);openLink(1);
        var b=document.querySelector('#lkOld .lk-old-btn');b&&b.click();
        if(H.scen==='oldfail'){H.nextWrite.push('ok');H.nextWrite.push('reject');}
        document.getElementById('lkSave').click();});
      step(function(){
        var p=posts()[0]||{body:{}},q=patches()[0]||{body:{},u:''};
        checkUpsert(p,'old link');
        ok(p.body.line_text==='1.5 qt. half & half'&&p.body.qty===1&&p.body.unit==='qt'&&p.body.ingredient_cost_id===1,'old link: saved on the NEW line with the old pick and amount');
        ok(patches().length===1&&/\/rest\/v1\/recipe_lines\?id=eq\.1&location=eq\.Tempest$/.test(q.u),'old link: a second write to the old row, by id; got '+q.u);
        ok(JSON.stringify(Object.keys(q.body).sort())==='["active","updated_at"]'&&q.body.active===false,'old link: it sets active false, nothing else');
        var gone=[].map.call(document.querySelectorAll('#recipeBody .rc-gone .rc-text'),txt);
        if(H.scen==='oldlink')ok(JSON.stringify(gone)==='["old skipped line"]','old link: the old row leaves No longer in the recipe; got '+JSON.stringify(gone));
        else{
          ok(JSON.stringify(gone)==='["1 qt. half & half","old skipped line"]','old link, clear failed: the old row stays under No longer in the recipe; got '+JSON.stringify(gone));
          ok(/old link could not be cleared/.test(toast()),'old link, clear failed: says so on screen; got '+JSON.stringify(toast()));
        }
        ok(/Half & half · Birite · 1 qt/.test(lineStates()[0]),'old link: the new line is linked');
      });
    }

    if(H.scen==='dismiss'){
      step(function(){openRecipe(104);
        var b=document.querySelectorAll('#recipeBody .rc-dismiss')[1];
        H.nextWrite.push('hang');b.click();b.click();dismissLink(5);});
      step(function(){
        ok(patches().length===1,'dismiss: a double tap is one write, got '+patches().length);
        var b=document.querySelector('.rc-dismiss[data-id="5"]');
        ok(b&&b.disabled,'dismiss: its button is locked in flight');
        var q=patches()[0]||{u:'',body:{}};
        ok(/recipe_lines\?id=eq\.5&location=eq\.Tempest$/.test(q.u)&&q.body.active===false,'dismiss: PATCH that row active false');
        H.release();
      });
      step(function(){
        var gone=[].map.call(document.querySelectorAll('#recipeBody .rc-gone .rc-text'),txt);
        ok(JSON.stringify(gone)==='["1 qt. half & half"]','dismiss: it leaves the list; got '+JSON.stringify(gone));
        ok(H.server.length===6&&H.server.filter(function(s){return s.id===5;})[0].active===false,'dismiss: the row is kept, inactive - nothing deleted');
      });
    }


    /* ---- Slice 4: conversions ---- */
    function convPosts(){return H.writes.filter(function(w){return /ingredient_conversions\?/.test(w.u);});}
    function convBtns(){return [].slice.call(document.querySelectorAll('#recipeBody .rc-conv-btn'));}
    function cvShown(){return document.getElementById('convModal').classList.contains('show');}
    function typeConv(q){var e=document.getElementById('cvQty');e.value=q;showConvState();}
    function askShown(){return shown(document.getElementById('cvAsk'));}
    function checkConvPayload(w,want,label){
      var b=(w||{}).body||{};
      ok(JSON.stringify(Object.keys(b).sort())==='["estimate","from_kind","from_qty","from_unit","ingredient_cost_id","location","note","to_qty","to_unit","updated_at"]',label+': exactly the ten fields; got '+JSON.stringify(Object.keys(b).sort()));
      ok(/\/rest\/v1\/ingredient_conversions\?on_conflict=ingredient_cost_id,from_kind$/.test((w||{}).u||''),label+': POST ingredient_conversions?on_conflict=ingredient_cost_id,from_kind; got '+(w||{}).u);
      ok(/resolution=merge-duplicates/.test((w||{}).prefer||''),label+': Prefer resolution=merge-duplicates');
      ok(b.location==='Tempest',label+': location Tempest');
      ok(b.from_qty===1,label+': from_qty 1');
      ok(typeof b.updated_at==='string'&&!isNaN(Date.parse(b.updated_at)),label+': the page sends updated_at');
      for(var k in want)ok(b[k]===want[k],label+': '+k+' = '+JSON.stringify(want[k])+', got '+JSON.stringify(b[k]));
    }
    function noLineWrites(label){ok(!H.writes.some(function(w){return /recipe_lines\?/.test(w.u);}),label+': the conversion window never writes recipe_lines');}

    if(H.scen==='conv'){
      step(function(){
        openRecipe(104);
        var st=lineStates();
        ok(/Macaroni noodles · Cooks · 2 qt needs a conversion Set conversion$/.test(st[3]||''),'conv: 2 qt against a lb price needs a conversion; got '+JSON.stringify(st[3]));
        var b=convBtns()[0];b&&b.click();
        ok(cvShown()&&!shown(document.getElementById('linkModal')),'conv: Set conversion opens the conversion window, not the link editor');
        ok(txt(document.getElementById('cvTitle'))==='Set conversion','conv: titled Set conversion');
        ok(document.getElementById('cvQty').value==='','conv: the answer box opens empty');
        ok(document.getElementById('cvFromUnit').value==='qt'&&document.getElementById('cvToUnit').value==='lb','conv: asks about 1 qt, answered in lb');
        ok(!shown(document.getElementById('cvWas')),'conv: no "Was" when there is no old conversion');
        ok(txt(document.getElementById('cvUsed'))==='Used by 2 lines in 2 recipes: Mac & Cheese, Pasta Salad','conv: used by counts volume lines only, orphans and skips out; got '+JSON.stringify(txt(document.getElementById('cvUsed'))));
        ok(document.getElementById('cvSave').disabled,'conv: Save is off with no answer');
        typeConv('0');ok(document.getElementById('cvSave').disabled,'conv: a zero answer cannot be saved');
        typeConv('-1');ok(document.getElementById('cvSave').disabled,'conv: a negative answer cannot be saved');
        typeConv('0.8');ok(!document.getElementById('cvSave').disabled,'conv: a real answer can');
        document.getElementById('cvNote').value='  cooked weight ';
        H.nextWrite.push('hang');
        document.getElementById('cvSave').click();document.getElementById('cvSave').click();saveConv();writeConv();
      });
      step(function(){
        ok(convPosts().length===1,'conv: a double tap (and direct calls) make one write, got '+convPosts().length);
        ['cvFromUnit','cvQty','cvToUnit','cvEst','cvNote','cvCancel','cvSave'].forEach(function(id){ok(document.getElementById(id).disabled,'conv: '+id+' locked in flight');});
        closeConv();ok(cvShown(),'conv: cannot be closed while saving');
        H.release();
      });
      step(function(){
        checkConvPayload(convPosts()[0],{ingredient_cost_id:4,from_kind:'volume',from_unit:'qt',to_qty:0.8,to_unit:'lb',estimate:false,note:'cooked weight'},'conv payload');
        ok(H.convs.length===1,'conv: one row');
        ok(!cvShown(),'conv: saved and closed');
        ok(/Conversion saved/.test(toast()),'conv: says saved; got '+JSON.stringify(toast()));
        var st=lineStates();
        ok(/2 qt \$2\.40 via 1 qt = 0\.8 lb as bought Change conversion$/.test(st[3]||''),'conv: Mac & Cheese costs at once, $2.40; got '+JSON.stringify(st[3]));
        closeRecipe();openRecipe(106);st=lineStates();
        ok(/1 cup \$0\.30 via 1 qt = 0\.8 lb as bought/.test(st[0]||''),'conv: Pasta Salad costs too, $0.30; got '+JSON.stringify(st[0]));
        ok(/1 lb \$1\.50$/.test(st[1]||''),'conv: the weight line is untouched; got '+JSON.stringify(st[1]));
        noLineWrites('conv');
      });
    }

    if(H.scen==='convask'){
      step(function(){
        openRecipe(104);
        ok(/2 qt \$2\.40 via 1 qt = 0\.8 lb as bought · estimate Change conversion$/.test(lineStates()[3]||''),'convask: costed through the stored conversion, marked estimate; got '+JSON.stringify(lineStates()[3]));
        convBtns()[0].click();
        ok(txt(document.getElementById('cvTitle'))==='Change conversion','convask: titled Change conversion');
        ok(txt(document.getElementById('cvWas'))==='Was: 1 qt = 0.8 lb as bought · estimate','convask: shows the old one as words');
        ok(document.getElementById('cvQty').value==='','convask: the answer box opens EMPTY even with an old row');
        typeConv('8');saveConv();
        ok(askShown()&&txt(document.getElementById('cvAskText'))==="That's 10× the old conversion (1 qt = 0.8 lb). Save anyway?",'convask: 10x asks; got '+JSON.stringify(txt(document.getElementById('cvAskText'))));
        ok(!shown(document.getElementById('cvBtns')),'convask: Save/Cancel hidden while asking');
        saveConv();
        typeConv('9');
        ok(!askShown()&&shown(document.getElementById('cvBtns')),'convask: changing the number takes the ask away (it was about the old number)');
        typeConv('8');saveConv();
        document.getElementById('cvAskBack').click();
      });
      step(function(){
        ok(convPosts().length===0&&!askShown()&&cvShown(),'convask: Go back writes nothing and keeps the window');
        typeConv('0.08');saveConv();
        ok(askShown()&&/^That's about a 10× drop from the old conversion \(1 qt = 0\.8 lb\)\. Save anyway\?$/.test(txt(document.getElementById('cvAskText'))),'convask: 1/10 asks; got '+JSON.stringify(txt(document.getElementById('cvAskText'))));
        document.getElementById('cvAskBack').click();
        typeConv('7.2');saveConv();
        ok(!askShown(),'convask: a 9x change does not ask');
      });
      step(function(){
        ok(convPosts().length===1&&!cvShown(),'convask: 9x saved without asking');
        checkConvPayload(convPosts()[0],{ingredient_cost_id:4,from_kind:'volume',from_unit:'qt',to_qty:7.2,to_unit:'lb',estimate:true,note:'dry'},'convask payload');
        ok(H.convs.length===1&&H.convs[0].id===900&&H.convs[0].to_qty===7.2,'convask: a change overwrites the same row');
        convBtns()[0].click();typeConv('80');saveConv();
        ok(askShown()&&/^That's 11×/.test(txt(document.getElementById('cvAskText'))),'convask: asks against the new old row (80 vs 7.2)');
        document.getElementById('cvAskYes').click();
      });
      step(function(){
        ok(convPosts().length===2&&!cvShown()&&H.convs.length===1&&H.convs[0].to_qty===80,'convask: Save anyway saves, still one row');
        noLineWrites('convask');
      });
    }

    if(H.scen==='convlost'){
      step(function(){openRecipe(104);convBtns()[0].click();typeConv('0.8');H.nextWrite.push('lost');document.getElementById('cvSave').click();});
      step(function(){
        var rb=H.reqs.filter(function(q){return q.m==='GET'&&/ingredient_conversions\?/.test(q.u)&&/ingredient_cost_id=eq\./.test(q.u);});
        ok(convPosts().length===1&&rb.length===1&&/ingredient_cost_id=eq\.4/.test(rb[0].u)&&/from_kind=eq\.volume/.test(rb[0].u)&&/location=eq\.Tempest/.test(rb[0].u),'convlost: a lost answer is read back by its key, no second POST');
        ok(!cvShown()&&/Conversion saved/.test(toast())&&H.convs.length===1,'convlost: found landed, so saved');
        convBtns()[0].click();typeConv('0.9');H.nextWrite.push('lost');H.nextConvGet.push('fail');document.getElementById('cvSave').click();
      });
      step(function(){
        ok(cvShown()&&!document.getElementById('cvSave').disabled,'convlost: unconfirmed - window open and unlocked');
        ok(/Could not confirm/.test(toast())&&/cannot make a second row/.test(toast()),'convlost: says it could not confirm, retry is safe; got '+JSON.stringify(toast()));
        document.getElementById('cvSave').click();
      });
      step(function(){
        var p=convPosts();
        ok(p.length===3&&p[1].u===p[2].u&&p[1].body.ingredient_cost_id===p[2].body.ingredient_cost_id&&p[1].body.from_kind===p[2].body.from_kind,'convlost: the retry is the same upsert key');
        ok(H.convs.length===1&&!cvShown(),'DROPPED RESPONSE + RETRY: one conversion row, got '+H.convs.length);
        convBtns()[0].click();typeConv('1');H.nextWrite.push('reject');document.getElementById('cvSave').click();
      });
      step(function(){
        ok(cvShown()&&!document.getElementById('cvSave').disabled&&document.getElementById('cvQty').value==='1','convlost: refused - window open, unlocked, answer kept');
        ok(/refused/.test(toast())&&document.getElementById('toast').classList.contains('error'),'convlost: refused says so in an error toast');
        ok(convPosts().length===4&&H.convs[0].to_qty===0.9,'convlost: refused wrote nothing, no automatic retry');
        noLineWrites('convlost');
      });
    }

    if(H.scen==='convstale'){
      step(function(){
        openRecipe(104);
        var s3=lineStates()[3]||'';
        ok(/conversion no longer matches — was lb, now case Fix conversion$/.test(s3)&&!/\$/.test(s3),'convstale: pack changed kind - no longer matches, was lb now case, no cost; got '+JSON.stringify(s3));
        closeRecipe();openRecipe(106);
        ok(/conversion no longer matches/.test(lineStates()[0]||''),'convstale: every line relying on it, in every recipe');
        convBtns()[0].click();
        ok(txt(document.getElementById('cvTitle'))==='Fix conversion','convstale: titled Fix conversion');
        ok(txt(document.getElementById('cvWas'))==='Was: 1 qt = 0.8 lb as bought · estimate','convstale: shows the old one as words');
        ok(document.getElementById('cvQty').value===''&&document.getElementById('cvToUnit').value==='case','convstale: answer empty, unit set to the new pack unit');
        ok(!document.getElementById('cvEst').checked&&document.getElementById('cvNote').value==='','convstale: a stale estimate and note are not carried over');
        document.getElementById('cvFromUnit').value='qt';typeConv('0.05');saveConv();
      });
      step(function(){
        ok(!askShown()&&convPosts().length===1,'convstale: a fix across kinds is not compared, so it does not ask');
        checkConvPayload(convPosts()[0],{ingredient_cost_id:4,from_kind:'volume',from_unit:'qt',to_qty:0.05,to_unit:'case',estimate:false,note:null},'convstale payload');
        ok(H.convs.length===1&&H.convs[0].id===900,'convstale: Fix overwrites the same key');
        ok(/1 cup \$/.test(lineStates()[0]||'')&&!/no longer matches/.test(lineStates()[0]||''),'convstale: costs again after the fix; got '+JSON.stringify(lineStates()[0]));
        noLineWrites('convstale');
      });
    }

    if(H.scen==='convoz'){
      openRecipe(104);
      ok(/2 qt \$2\.40 via 1 qt = 0\.8 lb as bought/.test(lineStates()[3]||''),'convoz: a pack re-entered within its kind (lb -> oz) still costs; got '+JSON.stringify(lineStates()[3]));
      closeRecipe();
    }
    if(steps.length){
      H.async=true;
      (function run(i){
        if(i>=steps.length){H.finish();return;}
        try{steps[i]();}catch(e){H.fails.push('threw in step '+i+': '+e);}
        setTimeout(function(){run(i+1);},250);
      })(0);
    }

    if(H.scen==='live'){
      var lr=document.querySelectorAll('#listBody .ing-row');
      ok(lr.length===LIVE.recipes,'live: '+LIVE.recipes+' recipes listed, got '+lr.length);
      var all=[];
      LIVE.ids.forEach(function(id){openRecipe(id);rendered().forEach(function(x){all.push([id].concat(x));});closeRecipe();});
      var lines=all.filter(function(x){return !x[1];}), heads=all.filter(function(x){return x[1];});
      ok(lines.length===LIVE.lines,'live: '+LIVE.lines+' lines rendered, got '+lines.length);
      ok(heads.length===LIVE.headers,'live: '+LIVE.headers+' part headers rendered, got '+heads.length);
      ok(lines.every(function(x){return x[4];}),'live: every line says "not linked"');
      ok(lines.every(function(x){return /^reads: /.test(x[3]);}),'live: every line shows what it reads');
      var flat=all.map(function(x){return [x[0],x[1],x[2]];});
      ok(JSON.stringify(flat)===JSON.stringify(LIVE.expect),'live: every line and header, in order, under its recipe');
      H.live={recipes:lr.length,lines:lines.length,headers:heads.length};
    }
  }catch(e){H.fails.push('threw: '+e);}
  H.finish=function(){
    if(H.scen==='fail')ok(H.reqs.length===10,'fail: Try again reads all five again, got '+H.reqs.length+' requests');
    if(!H.async){
      ok(H.writes.length===0,'writes: a read-only scenario makes no request other than a GET, got '+JSON.stringify(H.writes.map(function(w){return w.m+' '+w.u;})));
      ok(H.reqs.every(function(q){return q.m==='GET';}),'writes: every request is a GET');
    }
    ok(H.bad.length===0,'writes: only the table this window may write (recipe_lines, or ingredient_conversions from the conversion window), never DELETE; got '+JSON.stringify(H.bad));
    ok(H.checks.length===0,'writes: every conversion passes the table checks; got '+JSON.stringify(H.checks));
    ok(H.writes.every(function(w){return w.m!=='DELETE';}),'writes: nothing is ever deleted');
    var d=document.createElement('div');d.id='harnessResults';d.textContent=JSON.stringify({fails:H.fails,log:H.log,live:H.live||null});document.body.appendChild(d);
  };
  if(!H.async)setTimeout(H.finish,300);
},600);
</script>
"""


def build_page(rows, live=None, costs=COSTS, orders=ORDERS, convs=(), brk=None):
    src = open(os.path.join(ROOT, PAGE), encoding="utf-8").read()
    if brk:
        if brk[0] not in src:
            sys.exit("check_recipe_costing: break target not found: " + brk[0])
        src = src.replace(brk[0], brk[1])
    src, n = GATE_RE.subn("<!-- gate neutralised by check_recipe_costing.py -->", src)
    if n != 1:
        sys.exit("check_recipe_costing: could not find the site-password gate in " + PAGE)
    marker = "<script>\nvar SB="
    if marker not in src:
        sys.exit("check_recipe_costing: could not find the page script in " + PAGE)
    harness = (HARNESS.replace("__ROWS__", json.dumps(rows)).replace("__COSTS__", json.dumps(costs))
                      .replace("__ORDERS__", json.dumps(orders)).replace("__CONVS__", json.dumps(list(convs))).replace("__LINKS__", json.dumps(LINKS))
                      .replace("__LINKS_GUARDS__", json.dumps(LINKS_GUARDS)).replace("__PORK__", json.dumps(PORK))
                      .replace("__PASTA__", json.dumps(PASTA)).replace("__LINKS_CONV__", json.dumps(LINKS_CONV))
                      .replace("__CONV_OLD__", json.dumps(CONV_OLD)))
    src = src.replace(marker, harness + marker, 1)
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
             "--virtual-time-budget=20000", "--dump-dom", url],
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
        want_r = int(os.environ.get("LIVE_RECIPES", "45"))
        want_l = int(os.environ.get("LIVE_LINES", "352"))
        want_h = int(os.environ.get("LIVE_HEADERS", "13"))
        live = {"recipes": want_r, "lines": want_l, "headers": want_h,
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
    caught = 0
    for name, old, new, scens in BREAKS:
        bf, _, _ = run_all(chrome, build_page(RECIPES, brk=(old, new)), scens)
        if bf:
            caught += 1
        else:
            fails.append("break not caught: " + name)
    if fails:
        print("recipe costing guard: %d failure(s) of %d assertions\n" % (len(fails), total))
        for x in fails:
            print("  " + x)
        print("\nsee docs/recipe-costing.md, Slice 2")
        return 1
    print("recipe costing guard: clean (%d assertions, %d scenarios, %d breaks caught, %s)" % (total, len(SCENARIOS), caught, PAGE))
    return 0


if __name__ == "__main__":
    sys.exit(main())
