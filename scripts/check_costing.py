#!/usr/bin/env python3
"""
Behaviour guard for the Recipe Costing picker (tempest_costing.html, slice 1).

Slice 1's promise is that nothing is ever picked for you and that what you
save is the row you tapped. That promise is invisible to check_styling.py and
untestable against the live database - ingredient_costs is a production table
and the whole point of the slice is the write path.

So: load the REAL page, neutralise the site-password gate in the <head>,
replace XMLHttpRequest with a stub BEFORE the page's own <script> parses (so
api() can only ever reach a fixture and no request can leave the machine),
then drive it with headless Chrome and assert on real DOM clicks.

    python3 scripts/check_costing.py

Exit 0 = clean. Exit 1 = a regression, with the failing assertion named.

Each scenario is one Chrome run: the page decides its fixture from the URL
hash, runs its assertions, and parks the results in #harnessResults, which
--dump-dom hands back. --virtual-time-budget fast-forwards the setTimeout()s
the page uses for focus, so the suite finishes without wall-clock sleeps.

Trap worth remembering (see docs/costing-bulk-entry.md, "How to verify
without touching live data"): --window-size does not set the layout viewport.
Nothing here measures layout, which is why that does not bite - if you add a
layout assertion, wrap it in a width:390px element and measure inside it.
"""
import json
import os
import re
import subprocess
import sys
import tempfile
import time

CHROME = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
PAGE = "tempest_costing.html"

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# ---------------------------------------------------------------- fixtures --
# Two "Slab bacon" rows on purpose: the whole of slice 1 is that the id we
# POST is the id of the row that was tapped, and a name-matched harness would
# pass while the page saved against the wrong vendor.
ORDER_ITEMS = [
    {"id": 169, "location": "Tempest", "name": "Slab bacon", "vendor": "Asia Intl",
     "unit": "CS", "sort_order": 1, "active": True},
    {"id": 88, "location": "Tempest", "name": "Slab bacon", "vendor": "Birite",
     "unit": "CS", "sort_order": 1, "active": True},
    {"id": 12, "location": "Tempest", "name": "Distilled white vinegar",
     "vendor": "Birite", "unit": "EA", "sort_order": 2, "active": True},
]
INGREDIENT_COSTS = [
    # linked but unpriced - must stay in the picker, marked "needs price"
    {"id": 501, "location": "Tempest", "order_item_id": 12,
     "name": "Distilled white vinegar", "invoice_alias": None, "pack_qty": None,
     "pack_unit": None, "pack_price": None, "active": True},
    {"id": 502, "location": "Tempest", "order_item_id": None, "name": "Sea salt",
     "invoice_alias": None, "pack_qty": 2, "pack_unit": "lb", "pack_price": 10,
     "active": True},
]

# ------------------------------------------------------------ page surgery --

GATE_RE = re.compile(
    r"<script>\s*//\s*Site-password gate.*?</script>", re.S)

HARNESS = r"""
<script>
/* ---- test harness: installed BEFORE the page script parses ---- */
(function(){
  var SCEN=(location.hash||'#ok').slice(1);
  var ORDER_ITEMS=__ORDER_ITEMS__, COSTS=__COSTS__;
  var reqs=[], deferred=[], nextId=900;
  window.__h={scen:SCEN,reqs:reqs,fails:[],log:[],confirms:0,confirmReturn:true};

  function route(m,u,body){
    if(m==='GET'&&u.indexOf('/order_items')>-1){
      if(SCEN==='fail')return {err:true};
      if(SCEN==='empty')return {status:200,text:'[]'};
      if(SCEN==='slow')return 'defer';
      return {status:200,text:JSON.stringify(ORDER_ITEMS)};
    }
    if(m==='GET'&&u.indexOf('/ingredient_costs')>-1)
      return {status:200,text:JSON.stringify(COSTS)};
    if(m==='GET'&&u.indexOf('/ingredient_price_history')>-1)
      return {status:200,text:'[]'};
    if(m==='POST'&&u.indexOf('/ingredient_costs')>-1){
      var row=JSON.parse(JSON.stringify(body));row.id=nextId++;
      return {status:201,text:JSON.stringify([row])};
    }
    if(m==='PATCH'&&u.indexOf('/ingredient_costs')>-1){
      var p=JSON.parse(JSON.stringify(body));p.id=Number((u.match(/id=eq\.(\d+)/)||[])[1]);
      return {status:200,text:JSON.stringify([p])};
    }
    if(m==='POST')return {status:201,text:'[]'};
    return {status:200,text:'[]'};
  }

  function Fake(){this.status=0;this.responseText='';}
  Fake.prototype.open=function(m,u){this._m=m;this._u=u;};
  Fake.prototype.setRequestHeader=function(){};
  Fake.prototype.send=function(b){
    var self=this,parsed=null;
    if(b){try{parsed=JSON.parse(b);}catch(e){}}
    reqs.push({m:this._m,u:this._u,body:parsed});
    var r=route(this._m,this._u,parsed);
    var deliver=function(res){
      if(res.err){if(self.onerror)self.onerror();return;}
      self.status=res.status;self.responseText=res.text;
      if(self.onload)self.onload();
    };
    if(r==='defer'){deferred.push(function(){deliver({status:200,text:JSON.stringify(ORDER_ITEMS)});});return;}
    setTimeout(function(){deliver(r);},0);
  };
  window.XMLHttpRequest=Fake;
  window.__h.releaseDeferred=function(){var d=deferred.slice();deferred.length=0;
    for(var i=0;i<d.length;i++)d[i]();};

  var realConfirm=window.confirm;
  window.confirm=function(){window.__h.confirms++;return window.__h.confirmReturn;};
})();
</script>
"""

RUNNER = r"""
<script>
(function(){
  var H=window.__h, F=H.fails;
  function ok(name,cond,extra){if(!cond)F.push(name+(extra?' :: '+extra:''));H.log.push((cond?'PASS ':'FAIL ')+name);}
  function $(id){return document.getElementById(id);}
  function pickRows(){return Array.prototype.slice.call($('pickList').querySelectorAll('.pick-row'));}
  function rowFor(vendor,name){
    var rs=pickRows();
    for(var i=0;i<rs.length;i++){
      var v=rs[i].querySelector('.pick-v'),n=rs[i].querySelector('.pick-n');
      if(v&&n&&v.textContent===vendor&&n.textContent===name)return rs[i];
    }
    return null;
  }
  function posts(){return H.reqs.filter(function(r){return r.m==='POST'&&r.u.indexOf('/ingredient_costs')>-1;});}
  function set(id,v){var e=$(id);e.value=v;e.dispatchEvent(new Event('input',{bubbles:true}));}

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

  /* unlock manager mode through the real gate. The PIN is read out of the
     page's own variable and never printed anywhere. */
  step(function(){ $('gateInput').value=MANAGER_PIN; $('gateInput')
      .dispatchEvent(new KeyboardEvent('keydown',{key:'Enter',bubbles:true})); });

  if(H.scen==='slow'){
    /* B2: the picker is opened while the order-guide GET is still in flight. */
    step(function(){ $('openAddProxy')||$('search'); openAdd(); });
    step(function(){
      var t=$('pickList').textContent;
      ok('slow: says loading', /Loading/i.test(t), t);
      ok('slow: does not claim an empty guide', t.indexOf('No order-guide items match')<0, t);
      ok('slow: no Custom row while loading', !$('pickList').querySelector('.pick-custom'));
      ok('slow: nothing tappable while loading', pickRows().length===0);
    });
    step(function(){ H.releaseDeferred(); });
    step(function(){
      ok('slow: open picker fills in when data lands', !!rowFor('Asia Intl','Slab bacon'));
      ok('slow: Custom appears once loaded', !!$('pickList').querySelector('.pick-custom'));
      ok('slow: Custom is last', pickRows()[pickRows().length-1].className.indexOf('pick-custom')>-1);
    });
  }

  if(H.scen==='fail'){
    step(function(){ openAdd(); });
    step(function(){
      var t=$('pickList').textContent;
      ok('fail: shows an error', /didn|error|load/i.test(t)&&$('pickList').querySelector('.pick-error'), t);
      ok('fail: does not say "no match"', t.indexOf('No order-guide items match')<0, t);
      ok('fail: offers Retry', !!$('pickList').querySelector('.pick-retry'));
    });
    step(function(){ H.reqs.length=0; $('pickList').querySelector('.pick-retry').click(); });
    step(function(){
      ok('fail: Retry re-runs init()', H.reqs.some(function(r){return r.u.indexOf('/order_items')>-1;}));
    });
  }

  if(H.scen==='empty'){
    step(function(){ openAdd(); });
    step(function(){
      var t=$('pickList').textContent;
      ok('empty: says the guide is empty', /guide is empty/i.test(t), t);
      ok('empty: not the filter message', t.indexOf('No order-guide items match')<0, t);
      ok('empty: Custom still offered', !!$('pickList').querySelector('.pick-custom'));
    });
  }

  if(H.scen==='ok'){
    /* nothing is ever selected on your behalf */
    step(function(){ openAdd(); });
    step(function(){
      ok('ok: nothing picked on open', pickId===null);
      ok('ok: chooser shown, no chosen row', $('pickChosen').style.display==='none');
      ok('ok: unpriced linked row is reachable', !!rowFor('Birite','Distilled white vinegar'));
      ok('ok: unpriced linked row is marked',
         !!rowFor('Birite','Distilled white vinegar').querySelector('.pick-badge'));
      ok('ok: filter message only with a filter',
         $('pickList').textContent.indexOf('No order-guide items match')<0);
    });
    step(function(){ H.reqs.length=0; $('saveBtn').click(); });
    step(function(){
      ok('ok: saving with no pick writes nothing', posts().length===0);
      ok('ok: still no pick after a blocked save', pickId===null);
    });

    /* the id we POST is the id of the row that was tapped - Asia Intl 169 */
    step(function(){ rowFor('Asia Intl','Slab bacon').click(); });
    step(function(){
      ok('ok: tapping picks that row', pickId===169);
      ok('ok: unit is never auto-filled', $('fUnit').value==='');
      ok('ok: name is filled from the tapped row', $('fName').value==='Slab bacon');
      set('fQty','40'); set('fPrice','120');
    });
    step(function(){ $('saveBtn').click(); });
    step(function(){
      var p=posts();
      ok('ok: one write for one save', p.length===1, 'saw '+p.length);
      ok('ok: Asia Intl row saves order_item_id 169', p[0]&&p[0].body.order_item_id===169,
         p[0]&&String(p[0].body.order_item_id));
      ok('ok: unit saves as null, never CS', p[0]&&p[0].body.pack_unit===null,
         p[0]&&JSON.stringify(p[0].body.pack_unit));
      ok('ok: modal closed after save', $('editModal').className.indexOf('show')<0);
      /* M2: closeEdit resets */
      ok('M2: pickId cleared on close', pickId===null);
      ok('M2: fields cleared on close', $('fName').value===''&&$('fQty').value===''&&$('fPrice').value==='');
      ok('M2: fName re-enabled on close', $('fName').disabled===false);
      ok('M2: filter cleared on close', $('pickFilter').value==='');
      ok('M2: chosen display reset on close', $('pickChosen').style.display==='none');
    });

    /* and the other Slab bacon - Birite 88 */
    step(function(){ H.reqs.length=0; openAdd(); });
    step(function(){
      ok('ok: the priced row drops out of the picker', !rowFor('Asia Intl','Slab bacon'));
      rowFor('Birite','Slab bacon').click();
    });
    step(function(){
      ok('ok: tapping the second row picks 88', pickId===88);
      set('fQty','12'); set('fPrice','88.50');
    });
    step(function(){ $('saveBtn').click(); });
    step(function(){
      var p=posts();
      ok('ok: Birite row saves order_item_id 88', p[0]&&p[0].body.order_item_id===88,
         p[0]&&String(p[0].body.order_item_id));
      ok('ok: second save unit also null', p[0]&&p[0].body.pack_unit===null);
    });

    /* M1: opening an existing item and tapping the backdrop must not prompt */
    step(function(){ H.confirms=0; openEdit(502); });
    step(function(){
      ok('M1: edit populates the name', $('fName').value==='Sea salt');
      $('editModal').click();
    });
    step(function(){
      ok('M1: untouched edit does not prompt', H.confirms===0, 'confirms='+H.confirms);
      ok('M1: untouched edit closes', $('editModal').className.indexOf('show')<0);
    });
    step(function(){ H.confirms=0; openEdit(502); });
    step(function(){ set('fPrice','999'); $('editModal').click(); });
    step(function(){
      ok('M1: a changed field does prompt', H.confirms===1, 'confirms='+H.confirms);
    });
    /* M1: a fresh Add with nothing typed must not prompt either */
    step(function(){ H.confirms=0; openAdd(); });
    step(function(){ $('editModal').click(); });
    step(function(){ ok('M1: empty Add does not prompt', H.confirms===0, 'confirms='+H.confirms); });
  }

  if(document.readyState==='complete')setTimeout(run,0);
  else window.addEventListener('load',function(){setTimeout(run,0);});
})();
</script>
"""


def build_page():
    src = open(os.path.join(ROOT, PAGE), encoding="utf-8").read()

    # 1. neutralise the site-password gate - it redirects to index.html before
    #    a single assertion could run.
    src, n = GATE_RE.subn("<!-- gate neutralised by check_costing.py -->", src)
    if n != 1:
        sys.exit("check_costing: could not find the site-password gate in " + PAGE)

    # 2. the stub must be parsed BEFORE the page script, or api() captures the
    #    real XMLHttpRequest and a test could reach the network.
    marker = "<script>\nvar SB="
    if marker not in src:
        sys.exit("check_costing: could not find the page script in " + PAGE)
    harness = (HARNESS.replace("__ORDER_ITEMS__", json.dumps(ORDER_ITEMS))
                      .replace("__COSTS__", json.dumps(INGREDIENT_COSTS)))
    src = src.replace(marker, harness + marker, 1)

    # 3. no network, ever: the webfont links would otherwise leave the machine
    #    and headless Chrome blocks on them until it times out.
    src = re.sub(r'<link rel="preconnect"[^>]*>\s*', '', src)
    src = re.sub(r'<link rel="stylesheet" href="https://fonts[^>]*>\s*', '', src)

    # 4. assertions go last, so they see the page exactly as it ships.
    src = src.replace("</body>", RUNNER + "</body>", 1)
    return src


RESULT_RE = re.compile(r'<div id="harnessResults">(.*?)</div>', re.S)


def run_scenario(path, scen):
    """One Chrome per scenario, harvested rather than waited on.

    --dump-dom writes the finished DOM to stdout and then, on this machine,
    the browser process does not exit. So: stream stdout to a file, poll it
    for the results div, and kill Chrome as soon as it is there. A run that
    never produces the div is a real failure, not a slow machine.
    """
    url = "file://" + path + "#" + scen
    dom = os.path.join(os.path.dirname(path), "dom-" + scen + ".html")
    err = os.path.join(os.path.dirname(path), "err-" + scen + ".txt")
    with open(dom, "w") as fo, open(err, "w") as fe:
        proc = subprocess.Popen(
            [CHROME, "--headless=new", "--disable-gpu", "--no-sandbox",
             "--no-first-run", "--disable-extensions",
             "--disable-background-networking", "--disable-component-update",
             "--disable-default-apps", "--disable-sync",
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
    if not os.path.exists(CHROME):
        sys.exit("check_costing: Chrome not found at " + CHROME)
    page = build_page()
    fails, total = [], 0
    with tempfile.TemporaryDirectory() as td:
        path = os.path.join(td, "costing_under_test.html")
        with open(path, "w", encoding="utf-8") as f:
            f.write(page)
        for scen in ("ok", "slow", "fail", "empty"):
            res, err = run_scenario(path, scen)
            if res is None:
                fails.append("%s: harness never reported\n%s" % (scen, err))
                continue
            total += len(res["log"])
            fails += ["%s: %s" % (scen, x) for x in res["fails"]]

    if fails:
        print("costing guard: %d failure(s) of %d assertions\n" % (len(fails), total))
        for x in fails:
            print("  " + x)
        print("\nsee docs/costing-bulk-entry.md, slice 1")
        return 1
    print("costing guard: clean (%d assertions, 4 scenarios, %s)" % (total, PAGE))
    return 0


if __name__ == "__main__":
    sys.exit(main())
