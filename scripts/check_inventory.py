#!/usr/bin/env python3
"""
Behaviour guard for the Inventory Guide count sheet (tempest_inventory.html).

Slice 1's promises are that the sheet is drawn place by place in walking
order, that every item gets the boxes its pack size calls for, that every box
renders at 16px (#135 - and check_styling.py cannot see these boxes, because
they are built at runtime), and that the page only ever READS. None of that
can be checked against the live database without risking it, so:

load the REAL page, neutralise the site-password redirect, replace
XMLHttpRequest with a stub BEFORE the page's own <script> parses (so api()
can only ever reach a fixture and no request can leave the machine), then
drive it in headless Chrome and assert on the DOM it builds.

    python3 scripts/check_inventory.py

Exit 0 = clean. Exit 1 = a regression, with the failing assertion named.

Each scenario is one Chrome run: the page reads its fixture's behaviour from
the URL hash, the runner parks its results in #harnessResults, and
--dump-dom hands them back. The page runs STYLED - assets/ is copied beside
it - so the font-size and layout checks measure the real cascade.

Layout trap (docs/costing-bulk-entry.md): --window-size does not set the
layout viewport, so phone widths are simulated by setting the body's width
and measuring inside it.
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
PAGE = "tempest_inventory.html"
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

SCENARIOS = ("ok", "slow", "fail", "packfail", "hang", "empty", "orphan")


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
# Places arrive already sorted, as the page asks the table to sort them; the
# Line is empty on purpose, as Tempest's is.
PLACES = [
    {"id": 1, "label": "Vegetable cooler", "sort_order": 10},
    {"id": 6, "label": "Dry storage", "sort_order": 60},
    {"id": 8, "label": "Vinegar shelf", "sort_order": 80},
    {"id": 10, "label": "Line", "sort_order": 100},
]


def guide(name, vendor, unit, active=True):
    return {"name": name, "vendor": vendor, "unit": unit, "active": active}

# Sorted by sort_order, as the page's query asks for. Every box rule is here:
#   210 Ginger         pack 30 lb      -> Full x 30 lb + Loose lb
#   171 Cilantro       no pack         -> one box, order unit BU
#   44  Mayo           pack 1 Each     -> one box, Each
#   24  Cider vinegar  pack 4 GAL, in TWO places -> two boxes, "also in" both ways
#   60  Old flour      retired from the order guide
#   61  Zero pack      pack_qty 0      -> not a pack: one box, order unit
#   62  Blank unit     pack_unit ""    -> not a pack: one box, order unit
#   63  Long unit      pack 12 bunch   -> the widest two-box row, for the 320px check
#   64  Escaped        a name with markup in it
ITEMS = [
    {"id": 101, "order_item_id": 210, "place_id": 1, "sort_order": 10, "order_items": guide("Ginger", "Cooks Produce", "lb")},
    {"id": 102, "order_item_id": 171, "place_id": 1, "sort_order": 20, "order_items": guide("Cilantro", "Cooks Produce", "BU")},
    {"id": 103, "order_item_id": 63, "place_id": 1, "sort_order": 30, "order_items": guide("Long unit thing", "Cooks Produce", "CS")},
    {"id": 104, "order_item_id": 64, "place_id": 1, "sort_order": 40, "order_items": guide("Tom <b>bold</b> & co", "Birite", "EA")},
    {"id": 201, "order_item_id": 44, "place_id": 6, "sort_order": 10, "order_items": guide("Mayo", "Birite", "CS")},
    {"id": 202, "order_item_id": 24, "place_id": 6, "sort_order": 20, "order_items": guide("Apple cider vinegar", "Birite", "GAL")},
    {"id": 203, "order_item_id": 60, "place_id": 6, "sort_order": 30, "order_items": guide("Old flour", "Birite", "BAG", active=False)},
    {"id": 204, "order_item_id": 61, "place_id": 6, "sort_order": 40, "order_items": guide("Zero pack", "Birite", "CS")},
    {"id": 205, "order_item_id": 62, "place_id": 6, "sort_order": 50, "order_items": guide("Blank unit", "Birite", "EA")},
    {"id": 301, "order_item_id": 24, "place_id": 8, "sort_order": 10, "order_items": guide("Apple cider vinegar", "Birite", "GAL")},
]
# pack_price is in the fixture on purpose: the page must never draw it even
# if the table hands one back.
COSTS = [
    {"order_item_id": 210, "pack_qty": 30, "pack_unit": "lb", "pack_price": 54.5},
    {"order_item_id": 44, "pack_qty": 1, "pack_unit": "Each", "pack_price": 9.25},
    {"order_item_id": 24, "pack_qty": 4, "pack_unit": "GAL", "pack_price": 31},
    {"order_item_id": 61, "pack_qty": 0, "pack_unit": "lb", "pack_price": 10},
    {"order_item_id": 62, "pack_qty": 6, "pack_unit": "  ", "pack_price": 10},
    {"order_item_id": 63, "pack_qty": 12, "pack_unit": "bunch", "pack_price": 18},
]
ORPHAN = {"id": 999, "order_item_id": 77, "place_id": 42, "sort_order": 5,
          "order_items": guide("Lost in a retired place", "Birite", "EA")}

# ------------------------------------------------------------ page surgery --

GATE_RE = re.compile(r"window\.location\.replace\('index\.html'\)")

HARNESS = r"""
<script>
/* ---- test harness: installed BEFORE the page script parses ---- */
(function(){
  var SCEN=(location.hash||'#ok').slice(1);
  var PLACES=__PLACES__, ITEMS=__ITEMS__, COSTS=__COSTS__, ORPHAN=__ORPHAN__;
  var reqs=[], deferred=[], hung=[];
  window.__h={scen:SCEN,reqs:reqs,fails:[],log:[],
    /* per-table overrides, consumed in order: 'err' = no answer (onerror),
       'e500' = the server says no, 'hang' = nothing until timeoutAll() */
    next:{inventory_places:[],inventory_items:[],ingredient_costs:[]}};
  var N=window.__h.next;
  if(SCEN==='fail')N.inventory_items.push('err');
  if(SCEN==='packfail')N.ingredient_costs.push('e500');
  if(SCEN==='hang'){N.inventory_places.push('hang');N.inventory_items.push('hang');N.ingredient_costs.push('hang');}

  function table(u){var m=u.match(/\/rest\/v1\/([a-z_]+)/);return m?m[1]:'';}
  function route(m,u){
    if(m!=='GET')return {status:403,text:'{"message":"harness: this page must not write"}'};
    var t=table(u),plan=(N[t]||[]).shift();
    if(plan==='err')return {err:true};
    if(plan==='e500')return {status:500,text:'{"message":"boom"}'};
    if(plan==='hang')return {hang:true};
    var rows;
    if(t==='inventory_places')rows=SCEN==='empty'?[]:PLACES;
    else if(t==='inventory_items')rows=SCEN==='empty'?[]:(SCEN==='orphan'?ITEMS.concat([ORPHAN]):ITEMS);
    else if(t==='ingredient_costs')rows=COSTS;
    else return {status:404,text:'{"message":"harness: unknown table '+t+'"}'};
    var res={status:200,text:JSON.stringify(rows)};
    if(SCEN==='slow')return {defer:true,res:res};
    return res;
  }

  function Fake(){this.status=0;this.responseText='';this.timeout=0;}
  Fake.prototype.open=function(m,u){this._m=m;this._u=u;};
  Fake.prototype.setRequestHeader=function(){};
  Fake.prototype.send=function(b){
    var self=this;
    reqs.push({m:this._m,u:this._u,body:b||null,timeout:this.timeout});
    var r=route(this._m,this._u);
    if(r.hang){hung.push(self);return;}
    var deliver=function(res){
      if(res.err){if(self.onerror)self.onerror();return;}
      self.status=res.status;self.responseText=res.text;
      if(self.onload)self.onload();
    };
    if(r.defer){deferred.push(function(){deliver(r.res);});return;}
    setTimeout(function(){deliver(r);},0);
  };
  window.XMLHttpRequest=Fake;
  window.__h.releaseDeferred=function(){var d=deferred.slice();deferred.length=0;for(var i=0;i<d.length;i++)d[i]();};
  window.__h.timeoutAll=function(){var d=hung.slice();hung.length=0;for(var i=0;i<d.length;i++)if(d[i].ontimeout)d[i].ontimeout();};
  window.__h.hungCount=function(){return hung.length;};
})();
</script>
"""

RUNNER = r"""
<script>
(function(){
  var H=window.__h, F=H.fails;
  function ok(name,cond,extra){if(!cond)F.push(name+(extra!=null?' :: '+extra:''));H.log.push((cond?'PASS ':'FAIL ')+name);}
  function byId(id){return document.getElementById(id);}
  function all(sel,root){return Array.prototype.slice.call((root||document).querySelectorAll(sel));}
  function inputs(){return all('.stock-input');}
  function heads(){return all('.stock-place-hd .cat-label').map(function(e){return e.textContent;});}
  function rowsUnder(label){
    var out=[],hd=all('.stock-place-hd').filter(function(h){return h.querySelector('.cat-label').textContent===label;})[0];
    for(var n=hd&&hd.nextElementSibling;n&&!n.classList.contains('stock-place-hd');n=n.nextElementSibling)
      if(n.classList.contains('stock-row'))out.push(n);
    return out;
  }
  function rowNamed(label,name){return rowsUnder(label).filter(function(r){return r.querySelector('.count-name').textContent===name;})[0];}
  function units(row){return all('.stock-unit',row).map(function(e){return e.textContent;});}
  function parts(row){return all('.stock-input',row).map(function(e){return e.getAttribute('data-part');});}
  function body(){return byId('appBody').textContent;}
  function writes(){return H.reqs.filter(function(r){return r.m!=='GET';});}

  var steps=[];
  function step(fn){steps.push(fn);}
  function run(){
    if(!steps.length){
      var out=document.createElement('div');out.id='harnessResults';
      out.textContent=JSON.stringify({scen:H.scen,fails:F,log:H.log});
      document.body.appendChild(out);return;
    }
    var fn=steps.shift();
    try{fn();}catch(e){F.push('threw in step: '+(e&&e.message));}
    setTimeout(run,0);
  }

  /* every scenario: the page never writes, and every read is Tempest's */
  function readOnly(tag){
    ok(tag+': no request but GET', writes().length===0, JSON.stringify(writes()));
    ok(tag+': every request is scoped to Tempest',
       H.reqs.every(function(r){return r.u.indexOf('location=eq.Tempest')>-1;}),
       JSON.stringify(H.reqs.map(function(r){return r.u;})));
  }

  if(H.scen==='ok'){
    step(function(){
      ok('ok: kitchen.css loaded (the page runs styled)', getComputedStyle(document.querySelector('.header')).position==='sticky');
      ok('ok: three reads', H.reqs.length===3, H.reqs.length);
      ok('ok: every read has the 60s load timeout', H.reqs.every(function(r){return r.timeout===60000;}),
         JSON.stringify(H.reqs.map(function(r){return r.timeout;})));
      var cost=H.reqs.filter(function(r){return r.u.indexOf('/ingredient_costs')>-1;})[0]||{u:''};
      ok('ok: the price list is asked for pack size only, never a price',
         /select=order_item_id,pack_qty,pack_unit(&|$)/.test(cost.u)&&cost.u.indexOf('price')<0, cost.u);
      ok('ok: retired places and items are not asked for',
         H.reqs.filter(function(r){return /inventory_(places|items)/.test(r.u);}).every(function(r){return r.u.indexOf('active=eq.true')>-1;}));
      readOnly('ok');

      ok('ok: places in walking order', JSON.stringify(heads())===JSON.stringify(['Vegetable cooler','Dry storage','Vinegar shelf','Line']), JSON.stringify(heads()));
      var counts=all('.stock-place-n').map(function(e){return e.textContent;});
      ok('ok: each place says how many items', JSON.stringify(counts)===JSON.stringify(['4 items','5 items','1 item','0 items']), JSON.stringify(counts));
      ok('ok: an empty place says so', rowsUnder('Line').length===0&&body().indexOf('Nothing is stored here yet.')>-1);
      var veg=rowsUnder('Vegetable cooler').map(function(r){return r.querySelector('.count-name').textContent;});
      ok('ok: items in their order within a place', JSON.stringify(veg)===JSON.stringify(['Ginger','Cilantro','Long unit thing','Tom <b>bold</b> & co']), JSON.stringify(veg));

      var g=rowNamed('Vegetable cooler','Ginger');
      ok('ok: a pack of 30 lb gets Full and Loose', g&&JSON.stringify(parts(g))==='["full","loose"]', g&&JSON.stringify(parts(g)));
      ok('ok: ...labelled x 30 lb and lb', g&&JSON.stringify(units(g))==='["× 30 lb","lb"]', g&&JSON.stringify(units(g)));
      ok('ok: ...with Full and Loose captions', g&&all('.stock-lbl',g).map(function(e){return e.textContent;}).join('/')==='Full/Loose');
      var c=rowNamed('Vegetable cooler','Cilantro');
      ok('ok: no pack yet gets one box in the order unit', c&&JSON.stringify(parts(c))==='["full"]'&&JSON.stringify(units(c))==='["BU"]', c&&JSON.stringify(units(c)));
      ok('ok: ...and no Full/Loose caption', c&&all('.stock-lbl',c).length===0);
      var m=rowNamed('Dry storage','Mayo');
      ok('ok: a pack of 1 gets one box in the pack unit', m&&JSON.stringify(parts(m))==='["full"]'&&JSON.stringify(units(m))==='["Each"]', m&&JSON.stringify(units(m)));
      var z=rowNamed('Dry storage','Zero pack'), b=rowNamed('Dry storage','Blank unit');
      ok('ok: a zero pack is not a pack', z&&JSON.stringify(units(z))==='["CS"]', z&&JSON.stringify(units(z)));
      ok('ok: a pack with no unit is not a pack', b&&JSON.stringify(units(b))==='["EA"]', b&&JSON.stringify(units(b)));

      var v1=rowNamed('Dry storage','Apple cider vinegar'), v2=rowNamed('Vinegar shelf','Apple cider vinegar');
      ok('ok: an item in two places is drawn in both, each with its own boxes',
         v1&&v2&&JSON.stringify(units(v1))==='["× 4 GAL","GAL"]'&&JSON.stringify(units(v2))==='["× 4 GAL","GAL"]');
      ok('ok: ...and each says where else it is', v1&&v2&&v1.textContent.indexOf('also in Vinegar shelf')>-1&&v2.textContent.indexOf('also in Dry storage')>-1,
         (v1&&v1.querySelector('.count-par').textContent)+' | '+(v2&&v2.querySelector('.count-par').textContent));
      ok('ok: ...and the other rows do not', rowNamed('Dry storage','Mayo').textContent.indexOf('also in')<0);
      ok('ok: a vendor is shown', rowNamed('Dry storage','Mayo').querySelector('.count-par').textContent==='Birite');
      ok('ok: an item retired from the order guide says so', rowNamed('Dry storage','Old flour').textContent.indexOf('no longer on the order guide')>-1);

      var e=rowNamed('Vegetable cooler','Tom <b>bold</b> & co');
      ok('ok: a name with markup in it is shown as text, not run as HTML', e&&!e.querySelector('.count-name b'));
      ok('ok: no dollar figure anywhere on the page', document.body.innerText.indexOf('$')<0&&body().indexOf('54.5')<0&&body().indexOf('9.25')<0);

      var ins=inputs(), bad=ins.filter(function(i){return parseFloat(getComputedStyle(i).fontSize)<16;});
      ok('ok: every box computes to 16px or more (#135)', ins.length===14&&bad.length===0,
         ins.length+' boxes; small: '+bad.map(function(i){return i.getAttribute('aria-label')+'='+getComputedStyle(i).fontSize;}).join(', '));
      ok('ok: every box is a 44px tap target', ins.every(function(i){return i.getBoundingClientRect().height>=44;}),
         ins.map(function(i){return i.getBoundingClientRect().height;}).join(','));
      ok('ok: every box is text with a decimal keypad', ins.every(function(i){return i.type==='text'&&i.getAttribute('inputmode')==='decimal';}));
      ok('ok: every box is locked - nothing can be typed in a preview', ins.every(function(i){return i.disabled;}));
      ok('ok: every box is named for a screen reader', ins.every(function(i){return (i.getAttribute('aria-label')||'').length>3;}));
      ok('ok: a locked box still shows a visible edge (dashed, --edge)', ins.every(function(i){var s=getComputedStyle(i);
         return s.borderTopStyle==='dashed'&&s.borderTopColor==='rgb(142, 140, 132)';}), getComputedStyle(ins[0]).borderTopColor);
      /* one-box rows with units of different widths (BU, EA, Each, CS, BAG)
         must put their boxes in one column - an empty box is found by
         looking down a single line, not by hunting along each row */
      var lefts=all('.stock-row').filter(function(r){return all('.stock-input',r).length===1;})
        .map(function(r){return Math.round(r.querySelector('.stock-input').getBoundingClientRect().left);});
      ok('ok: one-box rows line their boxes up in one column', lefts.length===6&&Math.max.apply(null,lefts)-Math.min.apply(null,lefts)<=1, JSON.stringify(lefts));
      ok('ok: the summary counts items, not rows', byId('sheetSummary').textContent==='9 items · 4 places', byId('sheetSummary').textContent);
      ok('ok: the intro says how many items have a pack size', /4 of 9 items have a pack size/.test(byId('introBar').textContent), byId('introBar').textContent);
    });
    /* phone widths: nothing may run off the right edge */
    [390,320].forEach(function(w){
      step(function(){ document.body.style.width=w+'px'; });
      step(function(){
        var over=all('.stock-row').filter(function(r){
          var rr=r.getBoundingClientRect();
          return r.scrollWidth>r.clientWidth+1||all('.stock-input,.stock-unit',r).some(function(x){return x.getBoundingClientRect().right>rr.right+0.5;});
        });
        ok('ok: at '+w+'px no row runs off the edge', over.length===0, over.map(function(r){return r.querySelector('.count-name').textContent;}).join(', '));
        var g=rowNamed('Vegetable cooler','Ginger'),gi=all('.stock-input',g);
        ok('ok: at '+w+'px a two-box row keeps both boxes on screen', gi.length===2&&gi.every(function(i){var r=i.getBoundingClientRect();return r.width>=60&&r.left>=0&&r.right<=w;}));
      });
    });
    step(function(){ document.body.style.width=''; });
  }

  if(H.scen==='slow'){
    step(function(){
      ok('slow: says it is loading', /Loading the count sheet/.test(body()), body());
      ok('slow: no box before the data lands', inputs().length===0);
      ok('slow: no summary before the data lands', byId('sheetSummary').textContent==='');
      loadAll();
      ok('slow: a second load while loading sends nothing', H.reqs.length===3, H.reqs.length);
      H.releaseDeferred();
    });
    step(function(){
      ok('slow: draws the sheet once everything lands', inputs().length===14, inputs().length);
      readOnly('slow');
    });
  }

  if(H.scen==='fail'||H.scen==='packfail'){
    var tag=H.scen;
    step(function(){
      ok(tag+': says the sheet could not load', /Could not load the count sheet/.test(body()), body());
      ok(tag+': draws no box at all - never a sheet from part of the data', inputs().length===0&&all('.stock-row').length===0, inputs().length);
      ok(tag+': the toast is an error, not a success', /\berror\b/.test(byId('toast').className), byId('toast').className);
      ok(tag+': no summary', byId('sheetSummary').textContent==='');
      var btn=all('#appBody button')[0];
      ok(tag+': offers Try again', !!btn&&/Try again/.test(btn.textContent));
      if(btn)btn.click();
    });
    step(function(){
      ok(tag+': Try again loads it', inputs().length===14, inputs().length);
      ok(tag+': ...with three fresh reads', H.reqs.length===6, H.reqs.length);
      readOnly(tag);
    });
  }

  if(H.scen==='hang'){
    step(function(){
      ok('hang: still loading while nothing answers', /Loading the count sheet/.test(body())&&inputs().length===0);
      ok('hang: all three reads are waiting', H.hungCount()===3, H.hungCount());
      H.timeoutAll();
    });
    step(function(){
      ok('hang: a timeout ends in a plain failure, not a blank page', /Could not load the count sheet/.test(body()), body());
      ok('hang: after a timeout, no box', inputs().length===0);
      readOnly('hang');
    });
  }

  if(H.scen==='empty'){
    step(function(){
      ok('empty: says nothing is set up', /No places or items are set up for the count yet\./.test(body()), body());
      ok('empty: no box', inputs().length===0);
      readOnly('empty');
    });
  }

  if(H.scen==='orphan'){
    step(function(){
      var r=rowNamed('Not in an active place','Lost in a retired place');
      ok('orphan: an item whose place is retired is still shown, never dropped', !!r);
      ok('orphan: ...under its own heading, after the places', heads()[heads().length-1]==='Not in an active place', JSON.stringify(heads()));
      ok('orphan: ...and it does not count towards the place summary', byId('sheetSummary').textContent==='9 items · 4 places', byId('sheetSummary').textContent);
      readOnly('orphan');
    });
  }

  if(document.readyState==='complete')setTimeout(run,0);
  else window.addEventListener('load',function(){setTimeout(run,0);});
})();
</script>
"""


def build_page():
    src = open(os.path.join(ROOT, PAGE), encoding="utf-8").read()

    # 1. neutralise the site-password redirect, or the page leaves before a
    #    single assertion can run. Matched on the redirect itself, as
    #    check_styling.py does.
    src, n = GATE_RE.subn("void 0 /* gate neutralised by check_inventory.py */", src)
    if n != 1:
        sys.exit("check_inventory: could not find the site-password redirect in " + PAGE)

    # 2. the stub must be parsed BEFORE the page script, or api() captures the
    #    real XMLHttpRequest and a test could reach the network.
    marker = "<script>\nvar SB="
    if marker not in src:
        sys.exit("check_inventory: could not find the page script in " + PAGE)
    harness = (HARNESS.replace("__PLACES__", json.dumps(PLACES))
                      .replace("__ITEMS__", json.dumps(ITEMS))
                      .replace("__COSTS__", json.dumps(COSTS))
                      .replace("__ORPHAN__", json.dumps(ORPHAN)))
    src = src.replace(marker, harness + marker, 1)

    # 3. no network, ever: the webfont links would otherwise leave the machine.
    src = re.sub(r'<link rel="preconnect"[^>]*>\s*', '', src)
    src = re.sub(r'<link rel="stylesheet" href="https://fonts[^>]*>\s*', '', src)

    # 4. assertions go last, so they see the page exactly as it ships.
    return src.replace("</body>", RUNNER + "</body>", 1)


RESULT_RE = re.compile(r'<div id="harnessResults">(.*?)</div>', re.S)


def run_scenario(chrome, path, scen):
    """One Chrome per scenario. --dump-dom writes the DOM and then, on this
    machine, does not exit: so poll the output for the results div and kill
    Chrome once it is there. No div after 120s is a real failure."""
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
             "--virtual-time-budget=8000", "--dump-dom", url],
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
        sys.exit("check_inventory: no Chrome found. Set CHROME=/path/to/chrome.")
    page = build_page()
    fails, total = [], 0
    with tempfile.TemporaryDirectory() as td:
        path = os.path.join(td, "inventory_under_test.html")
        with open(path, "w", encoding="utf-8") as f:
            f.write(page)
        # the page links assets/kitchen.css relatively; without this copy
        # every scenario runs unstyled and the 16px check measures nothing real
        shutil.copytree(os.path.join(ROOT, "assets"), os.path.join(td, "assets"))
        for scen in (os.environ['ONLY'].split(',') if os.environ.get('ONLY') else SCENARIOS):
            res, err = run_scenario(chrome, path, scen)
            if res is None:
                fails.append("%s: harness never reported\n%s" % (scen, err))
                continue
            total += len(res["log"])
            fails += ["%s: %s" % (scen, x) for x in res["fails"]]

    if fails:
        print("inventory guard: %d failure(s) of %d assertions\n" % (len(fails), total))
        for x in fails:
            print("  " + x)
        print("\nsee docs/inventory-guide.md, Slice 1")
        return 1
    print("inventory guard: clean (%d assertions, %d scenarios, %s)" % (total, len(SCENARIOS), PAGE))
    return 0


if __name__ == "__main__":
    sys.exit(main())
