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

The page runs STYLED. assets/ is copied into the temp directory beside it,
so its relative assets/kitchen.css link resolves; the first check in the "ok"
scenario fails if it ever stops resolving. Before that fix every run was
unstyled, and a CSS rule that hid the picker or the chosen line - the two
things slice 1 exists to show - would have passed. Assertions on inline
style.display and field values never needed CSS; the "css:" ones do.

Layout traps (see docs/costing-bulk-entry.md, "How to verify without
touching live data"): --window-size does not set the layout viewport, so
measure widths inside a width:390px wrapper; a position:fixed modal escapes
that wrapper and vh follows the real window, so modal HEIGHT cannot be
measured here at all - judge it from a screenshot in a tall window. The
"css:" checks here are visibility and tap-target height, which neither trap
touches.
"""
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time

# Overridable so this runs somewhere other than one particular Mac - CI has
# Chrome on PATH under a different name entirely.
CHROME_CANDIDATES = [
    "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
    "/Applications/Chromium.app/Contents/MacOS/Chromium",
    "/usr/bin/google-chrome",
    "/usr/bin/google-chrome-stable",
    "/usr/bin/chromium",
    "/usr/bin/chromium-browser",
]
PAGE = "tempest_costing.html"


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

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

SCENARIOS = ("ok", "slow", "fail", "empty", "ledgerslow", "ledgerfail",
             "inflight", "retry",
             # slice 2 - mistakes can be undone
             "relink", "retired", "histfail", "magnitude")

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
    # slice 2: these two are held only by RETIRED ledger rows, so the picker
    # must offer them as fresh - retiring a mis-linked row is the repair, and
    # it must not remove the guide item forever.
    {"id": 77, "location": "Tempest", "name": "Butter", "vendor": "Birite",
     "unit": "CS", "sort_order": 3, "active": True},
    {"id": 44, "location": "Tempest", "name": "Cornstarch", "vendor": "Birite",
     "unit": "EA", "sort_order": 4, "active": True},
]
INGREDIENT_COSTS = [
    # linked but unpriced - must stay in the picker, marked "needs price"
    {"id": 501, "location": "Tempest", "order_item_id": 12,
     "name": "Distilled white vinegar", "invoice_alias": None, "pack_qty": None,
     "pack_unit": None, "pack_price": None, "active": True},
    {"id": 502, "location": "Tempest", "order_item_id": None, "name": "Sea salt",
     "invoice_alias": None, "pack_qty": 2, "pack_unit": "lb", "pack_price": 10,
     "active": True},
    # retired AND priced: must not hide guide item 77 from the picker
    {"id": 503, "location": "Tempest", "order_item_id": 77, "name": "Butter",
     "invoice_alias": None, "pack_qty": 36, "pack_unit": "lb", "pack_price": 108,
     "active": False},
    # retired AND unpriced: must not show as "needs price" and tap through
    # into a retired row (m10)
    {"id": 504, "location": "Tempest", "order_item_id": 44, "name": "Cornstarch",
     "invoice_alias": None, "pack_qty": None, "pack_unit": None,
     "pack_price": None, "active": False},
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
  /* The ledger is stateful, like the real table: a GET answers with what
     existed when it was SENT, so a slow GET is genuinely stale by the time it
     lands. A static fixture would hide the M-a bug (a superseded load wiping
     a row saved after it was sent). */
  var server=JSON.parse(JSON.stringify(COSTS));
  function snap(){return JSON.stringify(server);}
  window.__h={scen:SCEN,reqs:reqs,fails:[],log:[],confirms:0,confirmReturn:true,
    /* per-request overrides, consumed in order: 'err' fails now, 'defer'
       holds the response, 'defer-err' holds a failure, 'defer-empty' holds
       an empty-but-successful guide */
    nextGuide:[],nextLedger:[],
    /* every ingredient_costs write fails (after being held, in inflight) */
    failWrites:false,
    /* slice 2: the price-history POST fails while the ledger write succeeds */
    failHistory:false,
    /* what confirm() was actually asked - the magnitude check has to SAY
       what it is warning about, or it is just a speed bump */
    confirmMsgs:[]};
  if(SCEN==='retry'){window.__h.nextGuide.push('err');window.__h.nextLedger.push('defer');}
  function planned(q,ok,empty){
    var p=q.shift();
    if(p==='err')return {err:true};
    if(p==='defer')return {defer:true,res:ok};
    if(p==='defer-err')return {defer:true,res:{err:true}};
    if(p==='defer-empty')return {defer:true,res:empty};
    return ok;
  }

  function route(m,u,body){
    if(m==='GET'&&u.indexOf('/order_items')>-1){
      if(SCEN==='fail')return {err:true};
      if(SCEN==='empty')return {status:200,text:'[]'};
      var guide={status:200,text:JSON.stringify(ORDER_ITEMS)};
      if(SCEN==='slow')return {defer:true,res:guide};
      return planned(window.__h.nextGuide,guide,{status:200,text:'[]'});
    }
    if(m==='GET'&&u.indexOf('/ingredient_costs')>-1){
      /* M1: the ledger arrives in the SECOND request. A picker that calls
         itself loaded on the first one offers priced items as new. */
      if(SCEN==='ledgerfail')return {err:true};
      var ledger={status:200,text:snap()};
      if(SCEN==='ledgerslow')return {defer:true,res:ledger};
      return planned(window.__h.nextLedger,ledger,ledger);
    }
    if(m==='GET'&&u.indexOf('/ingredient_price_history')>-1)
      return {status:200,text:'[]'};
    if(m==='POST'&&u.indexOf('/ingredient_costs')>-1){
      var row=JSON.parse(JSON.stringify(body));row.id=nextId++;
      var added=window.__h.failWrites?{err:true}:{status:201,text:JSON.stringify([row])};
      if(!window.__h.failWrites)server.push(row);
      /* B2: hold the write open so the harness can cancel, or open another
         item, before the callback runs. */
      if(SCEN==='inflight')return {defer:true,res:added};
      return added;
    }
    if(m==='PATCH'&&u.indexOf('/ingredient_costs')>-1){
      var p=JSON.parse(JSON.stringify(body));p.id=Number((u.match(/id=eq\.(\d+)/)||[])[1]);
      var patched=window.__h.failWrites?{err:true}:{status:200,text:JSON.stringify([p])};
      if(!window.__h.failWrites)for(var k=0;k<server.length;k++)
        if(server[k].id===p.id)for(var f in p)server[k][f]=p[f];
      if(SCEN==='inflight')return {defer:true,res:patched};
      return patched;
    }
    if(m==='POST'&&u.indexOf('/ingredient_price_history')>-1)
      return window.__h.failHistory?{err:true}:{status:201,text:'[{"id":1}]'};
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
    if(r&&r.defer){deferred.push(function(){deliver(r.res);});return;}
    setTimeout(function(){deliver(r);},0);
  };
  window.XMLHttpRequest=Fake;
  window.__h.releaseDeferred=function(){var d=deferred.slice();deferred.length=0;
    for(var i=0;i<d.length;i++)d[i]();};
  /* release only the oldest held response - the first save, not the second */
  window.__h.releaseOne=function(){var f=deferred.shift();if(f)f();};

  var realConfirm=window.confirm;
  window.confirm=function(msg){window.__h.confirms++;
    window.__h.confirmMsgs.push(String(msg==null?'':msg));
    return window.__h.confirmReturn;};
})();
</script>
"""

RUNNER = r"""
<script>
(function(){
  var H=window.__h, F=H.fails;
  var ORDER_ITEM_COUNT=__ORDER_ITEM_COUNT__;
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
  function hist(){return H.reqs.filter(function(r){return r.m==='POST'&&r.u.indexOf('/ingredient_price_history')>-1;});}
  function set(id,v){var e=$(id);e.value=v;e.dispatchEvent(new Event('input',{bubbles:true}));}
  function shown(){return $('editModal').className.indexOf('show')>-1;}
  function toast(){return $('toast').textContent;}
  function count(){return $('countTag').textContent;}
  /* really on screen: laid out, not display:none / visibility:hidden, and a
     real tap target. Only true when kitchen.css has loaded AND not hidden it. */
  function visible(el){
    if(!el)return false;
    var r=el.getBoundingClientRect(),cs=getComputedStyle(el);
    return r.height>0&&r.width>0&&cs.visibility!=='hidden'&&cs.display!=='none'&&Number(cs.opacity)>0;
  }

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
    /* slice 1: the picker is opened while the order-guide GET is still in flight. */
    step(function(){ openAdd(); });
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

  if(H.scen==='ledgerslow'){
    /* M1: the guide lands in the first request, the ledger in the second.
       In the gap costRowFor() finds nothing, so a priced item is offered as
       new - and saving it POSTs a duplicate the unique index rejects, which
       reads to the user as "Add failed - try again", forever. */
    step(function(){ openAdd(); });
    step(function(){
      var t=$('pickList').textContent;
      ok('M1: says loading until the ledger lands', /Loading/i.test(t), t);
      ok('M1: nothing tappable before the ledger lands', pickRows().length===0);
      ok('M1: no Custom row before the ledger lands', !$('pickList').querySelector('.pick-custom'));
      ok('M1: does not claim an empty guide', t.indexOf('No order-guide items match')<0, t);
    });
    step(function(){ H.releaseDeferred(); });
    step(function(){
      ok('M1: the picker fills in when the ledger lands', !!rowFor('Asia Intl','Slab bacon'));
      ok('M1: the ledger is applied, not ignored',
         !!rowFor('Birite','Distilled white vinegar').querySelector('.pick-badge'));
      ok('M1: Custom appears once both have landed', !!$('pickList').querySelector('.pick-custom'));
    });
  }

  if(H.scen==='ledgerfail'){
    /* M1: a ledger failure gets the same error-with-Retry the guide failure
       already has - never a picker that looks usable. */
    step(function(){ openAdd(); });
    step(function(){
      var t=$('pickList').textContent;
      ok('M1: a failed ledger shows an error', !!$('pickList').querySelector('.pick-error'), t);
      ok('M1: a failed ledger offers Retry', !!$('pickList').querySelector('.pick-retry'));
      ok('M1: a failed ledger is not tappable', pickRows().length===0);
      ok('M1: a failed ledger does not say "no match"',
         t.indexOf('No order-guide items match')<0, t);
    });
    step(function(){ H.reqs.length=0; $('pickList').querySelector('.pick-retry').click(); });
    step(function(){
      ok('M1: Retry re-runs init()', H.reqs.some(function(r){return r.u.indexOf('/order_items')>-1;}));
    });
  }

  if(H.scen==='inflight'){
    /* B2: every write here is held open until releaseDeferred(). The callback
       must use the id captured when the request was sent, never the shared
       editId, which by then belongs to whatever the user did next. */

    /* both fixture GETs have to have landed before an id means anything -
       each takes a tick, and so does each step. */
    step(function(){});
    step(function(){ ok('inflight: fixtures loaded', items.length===4, 'items='+items.length); });

    /* (a) save, then Cancel before the response */
    step(function(){ H.reqs.length=0; openEdit(502); });
    step(function(){ set('fPrice','999'); });
    step(function(){ $('saveBtn').click(); });
    step(function(){ closeEdit(); });
    step(function(){ H.releaseDeferred(); });
    step(function(){
      var hp=hist();
      ok('B2: cancel-before-response still logs a price', hp.length===1, 'saw '+hp.length);
      ok('B2: cancelled save logs against 502, not null',
         hp[0]&&hp[0].body.ingredient_cost_id===502,
         hp[0]&&JSON.stringify(hp[0].body.ingredient_cost_id));
      var it=findItem(502);
      ok('B2: the cancelled save still updates its own row', it&&Number(it.pack_price)===999,
         it&&String(it.pack_price));
    });

    /* (b) save, then open ANOTHER item before the response */
    step(function(){ H.reqs.length=0; openEdit(502); });
    step(function(){ set('fPrice','777'); });
    step(function(){ $('saveBtn').click(); });
    step(function(){ openEdit(501); });
    step(function(){ H.releaseDeferred(); });
    step(function(){
      var hp=hist();
      ok('B2: item A price does not land on item B',
         hp[0]&&hp[0].body.ingredient_cost_id===502,
         hp[0]&&JSON.stringify(hp[0].body.ingredient_cost_id));
      ok('B2: item A row is the one updated', findItem(502)&&Number(findItem(502).pack_price)===777,
         String(findItem(502)&&findItem(502).pack_price));
      ok('B2: item B row is untouched', findItem(501)&&findItem(501).pack_price==null,
         JSON.stringify(findItem(501)&&findItem(501).pack_price));
      /* B-new: A's response must not close B, which is what is on screen */
      ok('B-new: A\'s response leaves B open', shown()&&editId===501, 'shown='+shown()+' editId='+editId);
      ok('B-new: B\'s name is still in the field', $('fName').value==='Distilled white vinegar', $('fName').value);
      ok('B-new: the toast names A, not "Saved"', toast()==='✓ Sea salt saved', toast());
    });

    /* (c) the ADD branch, same sequence */
    step(function(){ H.reqs.length=0; closeEdit(); openAdd(); });
    step(function(){ rowFor('Asia Intl','Slab bacon').click(); });
    step(function(){ set('fQty','40'); set('fUnit','lb'); set('fPrice','120'); });
    step(function(){ $('saveBtn').click(); });
    step(function(){ closeEdit(); });
    step(function(){ H.releaseDeferred(); });
    step(function(){
      var p=posts(), hp=hist();
      ok('B2: the add wrote once', p.length===1, 'saw '+p.length);
      ok('B2: the add logs a price', hp.length===1, 'saw '+hp.length);
      ok('B2: the add logs against the new row, not null',
         hp[0]&&typeof hp[0].body.ingredient_cost_id==='number',
         hp[0]&&JSON.stringify(hp[0].body.ingredient_cost_id));
      ok('B-new: a cancelled add\'s toast names it', toast()==='✓ Slab bacon (Asia Intl) added', toast());
    });

    /* B-new (d): the mispick corrected mid-save. Save Asia Intl, Change, pick
       Birite, type its numbers. The Asia Intl response must not close Birite,
       clear what was typed, or claim success for what is on screen. */
    step(function(){ H.reqs.length=0; closeEdit(); openAdd(); });
    step(function(){ rowFor('Birite','Slab bacon').click(); });
    step(function(){ set('fQty','12'); set('fUnit','lb'); set('fPrice','88.50'); });
    step(function(){ $('saveBtn').click(); });
    step(function(){
      ok('B-new: Save says it is saving', $('saveBtn').textContent==='Saving…'&&$('saveBtn').disabled,
         $('saveBtn').textContent+' disabled='+$('saveBtn').disabled);
    });
    step(function(){ $('pickChosen').querySelector('.pick-change').click(); });
    step(function(){
      ok('B-new: after Change, Save is live again', $('saveBtn').disabled===false&&$('saveBtn').textContent==='Save',
         $('saveBtn').textContent+' disabled='+$('saveBtn').disabled);
    });
    step(function(){ rowFor('Birite','Distilled white vinegar').click(); });
    step(function(){
      ok('B-new: picked the second item', editId===501, String(editId));
      set('fQty','4'); set('fUnit','gal'); set('fPrice','19.96');
    });
    step(function(){ H.releaseOne(); });
    step(function(){
      ok('B-new: the first response does not close the second item', shown(), 'modal closed');
      ok('B-new: still showing the second item', editId===501&&$('pickChosenN').textContent==='Distilled white vinegar',
         'editId='+editId+' chosen='+$('pickChosenN').textContent);
      ok('B-new: the second item\'s qty survives', $('fQty').value==='4', $('fQty').value);
      ok('B-new: the second item\'s unit survives', $('fUnit').value==='gal', $('fUnit').value);
      ok('B-new: the second item\'s price survives', $('fPrice').value==='19.96', $('fPrice').value);
      ok('B-new: the toast names the first item', toast()==='✓ Slab bacon (Birite) added', toast());
      ok('B-new: the first item is in the ledger', !!costRowFor(88));
      ok('B-new: Save is live for the second item', $('saveBtn').disabled===false);
    });
    step(function(){ $('saveBtn').click(); });
    step(function(){ H.releaseDeferred(); });
    step(function(){
      var p=H.reqs.filter(function(r){return r.m==='PATCH';});
      ok('B-new: the second save wrote the second item', p.length===1&&/id=eq\.501/.test(p[0].u),
         p.map(function(x){return x.u;}).join(','));
      ok('B-new: the second item\'s own response closes it', !shown());
      ok('B-new: and names it', toast()==='✓ Distilled white vinegar (Birite) saved', toast());
    });

    /* B-new (e): a FAILED save, then Cancel, and a different item on screen
       when the failure lands. The toast names the item that failed; the item
       on screen is untouched. Between them: reopening the failing item and
       saving again must not send a second write while the first is out. */
    function patches(){return H.reqs.filter(function(r){return r.m==='PATCH';});}
    step(function(){ H.reqs.length=0; H.failWrites=true; openEdit(502); });
    step(function(){ set('fPrice','555'); });
    step(function(){ $('saveBtn').click(); });
    step(function(){ closeEdit(); openEdit(502); });
    step(function(){ set('fPrice','556'); });
    step(function(){ $('saveBtn').click(); });
    step(function(){
      ok('B-new: no second write for an item still saving', patches().length===1, 'saw '+patches().length);
      ok('B-new: and it says why', toast()==='⚠ Sea salt is still saving', toast());
      ok('B-new: the typed value stays', $('fPrice').value==='556', $('fPrice').value);
    });
    step(function(){ closeEdit(); openEdit(costRowFor(169).id); });
    step(function(){ set('fPrice','130'); });
    step(function(){ H.releaseDeferred(); H.failWrites=false; });
    step(function(){
      ok('B-new: the failure names the item that failed', toast()==='⚠ Sea salt failed — try again', toast());
      ok('B-new: the failure does not close the other item', shown()&&editId===costRowFor(169).id,
         'shown='+shown()+' editId='+editId);
      ok('B-new: the other item\'s typed value survives', $('fPrice').value==='130', $('fPrice').value);
      ok('B-new: the failed row is not changed locally', Number(findItem(502).pack_price)===777,
         String(findItem(502).pack_price));
    });
    step(function(){ closeEdit(); openEdit(502); });
    step(function(){ set('fPrice','556'); });
    step(function(){ $('saveBtn').click(); });
    step(function(){ H.releaseDeferred(); });
    step(function(){
      ok('B-new: the retry goes through', !shown()&&Number(findItem(502).pack_price)===556,
         String(findItem(502).pack_price));
    });
  }

  if(H.scen==='retry'){
    /* M-a. The first load's guide fails and its ledger is held. Retry starts
       a second load, which succeeds; an item is saved; THEN the first load's
       ledger lands. It predates the save. If it is applied, the saved row
       vanishes, the count reads zero, and re-adding hits the unique index. */
    step(function(){ openAdd(); });
    step(function(){ ok('M-a: first load shows Retry', !!$('pickList').querySelector('.pick-retry')); });
    step(function(){ $('pickList').querySelector('.pick-retry').click(); });
    step(function(){});
    step(function(){ ok('M-a: Retry loads the picker', !!rowFor('Asia Intl','Slab bacon')); });
    step(function(){ rowFor('Asia Intl','Slab bacon').click(); });
    step(function(){ set('fQty','40'); set('fUnit','lb'); set('fPrice','120'); });
    step(function(){ $('saveBtn').click(); });
    step(function(){ ok('M-a: the save landed', !!costRowFor(169)&&/^3 items/.test(count()), count()); });
    step(function(){ H.releaseDeferred(); });
    step(function(){
      ok('M-a: a superseded ledger does not wipe the saved row', !!costRowFor(169), 'items='+items.length);
      ok('M-a: the count is not reset', count()==='3 items · 2 priced', count());
      ok('M-a: the stale ledger raised no error', ledgerLoaded&&!ledgerError);
    });
    step(function(){ openAdd(); });
    step(function(){ ok('M-a: the saved item stays out of the picker', !rowFor('Asia Intl','Slab bacon')); closeEdit(); });

    /* the guide's error path: a superseded guide failure lands late */
    step(function(){ H.nextGuide.push('defer-err'); init(); init(); });
    step(function(){});
    step(function(){ H.releaseDeferred(); });
    step(function(){ openAdd(); });
    step(function(){
      ok('M-a: a superseded guide failure is ignored', !guideError&&!$('pickList').querySelector('.pick-error'));
      ok('M-a: the picker still works after it', !!rowFor('Birite','Slab bacon'));
      closeEdit();
    });

    /* the guide's success path: a superseded EMPTY guide lands late */
    step(function(){ H.nextGuide.push('defer-empty'); init(); init(); });
    step(function(){});
    step(function(){ H.releaseDeferred(); });
    step(function(){
      ok('M-a: a superseded guide does not replace the guide', orderItems.length===ORDER_ITEM_COUNT, 'orderItems='+orderItems.length);
    });

    /* the ledger's error path */
    step(function(){ H.nextLedger.push('defer-err'); init(); });
    step(function(){ init(); });
    step(function(){});
    step(function(){ H.releaseDeferred(); });
    step(function(){
      ok('M-a: a superseded ledger failure is ignored', ledgerLoaded&&!ledgerError);
      ok('M-a: the ledger survives it', !!costRowFor(169)&&count()==='3 items · 2 priced', count());
    });
  }

  /* ---------------------------------------------------------- SLICE 2 --
     "Mistakes can be undone". Four guards, one per promise. */

  if(H.scen==='relink'){
    /* (1) RE-LINK ON EDIT. openEdit() hid pickWrap, so a row bound to the
       wrong guide item could never be corrected - only retired, which (2)
       then blocked that guide item forever. */
    step(function(){});
    step(function(){ ok('relink: fixtures loaded', items.length===4, 'items='+items.length); });

    step(function(){ openEdit(502); });
    step(function(){
      ok('S2-1: edit shows the picker at all', visible($('pickWrap')),
         'display='+$('pickWrap').style.display);
      ok('S2-1: edit shows what the row is linked to', visible($('pickChosen')));
      ok('S2-1: an off-guide row says so', $('pickChosenV').textContent==='Off-guide items',
         $('pickChosenV').textContent);
      ok('S2-1: the chosen line names the row', $('pickChosenN').textContent==='Sea salt',
         $('pickChosenN').textContent);
      ok('S2-1: Change is reachable on an edit', visible($('pickChange')));
    });
    step(function(){ $('pickChange').click(); });
    step(function(){
      ok('S2-1: Change opens the chooser', visible($('pickChoose')));
      /* a guide item already held by an ACTIVE row is not a legal re-link
         target - the partial unique index would reject it */
      ok('S2-1: a guide item held by an active row is not offered',
         !rowFor('Birite','Distilled white vinegar'));
      ok('S2-1: a free guide item is offered', !!rowFor('Birite','Slab bacon'));
    });
    step(function(){
      /* the numbers must survive: the price is RIGHT, the link is WRONG -
         that is the whole repair */
      ok('S2-1: Change on an edit keeps the qty', $('fQty').value==='2', $('fQty').value);
      ok('S2-1: Change on an edit keeps the unit', $('fUnit').value==='lb', $('fUnit').value);
      ok('S2-1: Change on an edit keeps the price', $('fPrice').value==='10', $('fPrice').value);
      rowFor('Birite','Slab bacon').click();
    });
    step(function(){
      ok('S2-1: re-linking takes the tapped id', pickId===88, String(pickId));
      ok('S2-1: re-linking renames to the new item', $('fName').value==='Slab bacon',
         $('fName').value);
      ok('S2-1: re-linking shows the new vendor', $('pickChosenV').textContent==='Birite',
         $('pickChosenV').textContent);
      ok('S2-1: re-linking still keeps the numbers',
         $('fQty').value==='2'&&$('fUnit').value==='lb'&&$('fPrice').value==='10',
         $('fQty').value+'/'+$('fUnit').value+'/'+$('fPrice').value);
      H.reqs.length=0;
    });
    step(function(){ $('saveBtn').click(); });
    step(function(){
      var pt=H.reqs.filter(function(r){return r.m==='PATCH';});
      ok('S2-1: the re-link is written', pt.length===1, 'saw '+pt.length);
      ok('S2-1: it PATCHes the row being edited', pt[0]&&/id=eq\.502/.test(pt[0].u), pt[0]&&pt[0].u);
      ok('S2-1: it writes the new order_item_id', pt[0]&&pt[0].body.order_item_id===88,
         pt[0]&&JSON.stringify(pt[0].body.order_item_id));
      ok('S2-1: it writes the new name', pt[0]&&pt[0].body.name==='Slab bacon',
         pt[0]&&JSON.stringify(pt[0].body.name));
      ok('S2-1: it keeps the price it was repairing', pt[0]&&Number(pt[0].body.pack_price)===10,
         pt[0]&&JSON.stringify(pt[0].body.pack_price));
    });

    /* re-link the other way: a linked row can be sent off-guide */
    step(function(){ H.reqs.length=0; openEdit(501); });
    step(function(){
      ok('S2-1: a linked row shows its vendor', $('pickChosenV').textContent==='Birite',
         $('pickChosenV').textContent);
      $('pickChange').click();
    });
    step(function(){ $('pickList').querySelector('.pick-custom').click(); });
    step(function(){
      ok('S2-1: Custom unlinks the row', pickId==='custom', String(pickId));
      ok('S2-1: unlinking re-enables the name field', $('fName').disabled===false);
      set('fName','White vinegar (off guide)'); set('fQty','4'); set('fUnit','gal'); set('fPrice','20');
    });
    step(function(){ $('saveBtn').click(); });
    step(function(){
      var pt=H.reqs.filter(function(r){return r.m==='PATCH';});
      ok('S2-1: unlinking writes a null order_item_id', pt[0]&&pt[0].body.order_item_id===null,
         pt[0]&&JSON.stringify(pt[0].body.order_item_id));
      ok('S2-1: unlinking keeps the typed name',
         pt[0]&&pt[0].body.name==='White vinegar (off guide)', pt[0]&&JSON.stringify(pt[0].body.name));
    });

    /* a pending re-link is unsaved work: the backdrop must ask */
    step(function(){ H.confirms=0; openEdit(502); });
    step(function(){ $('pickChange').click(); });
    step(function(){ rowFor('Asia Intl','Slab bacon').click(); });
    step(function(){ $('editModal').click(); });
    step(function(){
      ok('S2-1: discarding a pending re-link asks first', H.confirms===1, 'confirms='+H.confirms);
    });
  }

  if(H.scen==='retired'){
    /* (2) RETIRED ROWS STOP BLOCKING THE PICKER. Retiring a mis-linked row
       is the documented repair; costedOrderIds() counted retired rows, so
       the repair removed that guide item from + Add forever. */
    step(function(){});
    step(function(){ ok('retired: fixtures loaded', items.length===4, 'items='+items.length); });
    step(function(){ openAdd(); });
    step(function(){
      ok('S2-2: a guide item held only by a RETIRED priced row is offered again',
         !!rowFor('Birite','Butter'));
      ok('S2-2: a guide item held only by a RETIRED unpriced row is offered again',
         !!rowFor('Birite','Cornstarch'));
      /* m10: it must be offered as FRESH, not as an existing row to edit */
      ok('S2-2: the retired unpriced row is not labelled "needs price"',
         !rowFor('Birite','Cornstarch').querySelector('.pick-badge'));
      ok('S2-2: the retired priced row is not labelled "needs price"',
         !rowFor('Birite','Butter').querySelector('.pick-badge'));
      /* the ACTIVE unpriced row still is - slice 1's promise is untouched */
      ok('S2-2: an active unpriced row is still marked',
         !!rowFor('Birite','Distilled white vinegar').querySelector('.pick-badge'));
      H.reqs.length=0;
      rowFor('Birite','Cornstarch').click();
    });
    step(function(){
      ok('S2-2: tapping it starts a new row, not the retired one', pickId===44, String(pickId));
      ok('S2-2: tapping it does not open the retired row', editId===null, String(editId));
      set('fQty','1'); set('fUnit','lb'); set('fPrice','3.50');
    });
    step(function(){ $('saveBtn').click(); });
    step(function(){
      ok('S2-2: the add is not refused as already costed', posts().length===1, 'saw '+posts().length);
      ok('S2-2: it adds against the right guide item', posts()[0]&&posts()[0].body.order_item_id===44,
         posts()[0]&&String(posts()[0].body.order_item_id));
      ok('S2-2: no "already costed" toast', toast().indexOf('already costed')<0, toast());
    });
    /* and the retired PRICED one, which used to vanish from the list entirely */
    step(function(){ H.reqs.length=0; openAdd(); });
    step(function(){ rowFor('Birite','Butter').click(); });
    step(function(){ set('fQty','36'); set('fUnit','lb'); set('fPrice','110'); });
    step(function(){ $('saveBtn').click(); });
    step(function(){
      ok('S2-2: re-adding a retired-and-priced guide item works',
         posts().length===1&&posts()[0].body.order_item_id===77,
         'posts='+posts().length+' toast='+toast());
    });
  }

  if(H.scen==='histfail'){
    /* (3) logPrice GETS A CALLBACK. The ledger write is the source of truth
       and is never rolled back - but a price with no trail must not pass in
       silence. */
    step(function(){});
    step(function(){ H.failHistory=true; openEdit(502); });
    step(function(){ set('fPrice','14'); });
    step(function(){ $('saveBtn').click(); });
    step(function(){
      var pt=H.reqs.filter(function(r){return r.m==='PATCH';});
      ok('S2-3: the ledger write still happens', pt.length===1, 'saw '+pt.length);
      ok('S2-3: the history write was attempted', hist().length===1, 'saw '+hist().length);
      ok('S2-3: the price is not rolled back', Number(findItem(502).pack_price)===14,
         String(findItem(502).pack_price));
    });
    step(function(){
      ok('S2-3: a failed history write is surfaced', /histor/i.test(toast()), toast());
      ok('S2-3: the failure names the item', toast().indexOf('Sea salt')>-1, toast());
      ok('S2-3: it reads as a warning, not a success',
         $('toast').className.indexOf('err')>-1, $('toast').className);
    });
    /* and when it succeeds, it says nothing extra */
    step(function(){ H.failHistory=false; H.reqs.length=0; openEdit(502); });
    step(function(){ set('fPrice','15'); });
    step(function(){ $('saveBtn').click(); });
    /* the history POST answers a tick after the save does - without this the
       "quiet" assertion passes before the toast it is looking for could have
       appeared, and a logPrice that always complains would sail through */
    step(function(){});
    step(function(){
      ok('S2-3: a successful history write stays quiet', /histor/i.test(toast())===false, toast());
      ok('S2-3: the save still confirms itself', /saved/i.test(toast()), toast());
    });
  }

  if(H.scen==='magnitude'){
    /* (4) MAGNITUDE CHECK ON EDIT, and m20: priceChanged was blind to a
       unit-only edit - the single change that most reliably swings unit
       cost (lb -> oz is 16x) wrote no history row at all. */
    step(function(){});

    /* m20 first: a unit-only edit must write history */
    step(function(){ H.reqs.length=0; H.confirms=0; H.confirmMsgs=[]; openEdit(502); });
    step(function(){ set('fUnit','oz'); });
    step(function(){ $('saveBtn').click(); });
    step(function(){
      ok('m20: a unit-only edit writes a history row', hist().length===1, 'saw '+hist().length);
      ok('m20: the history row carries the new unit',
         hist()[0]&&hist()[0].body.pack_unit==='oz', hist()[0]&&JSON.stringify(hist()[0].body.pack_unit));
      ok('S2-4: a unit-only edit asks before saving', H.confirms===1, 'confirms='+H.confirms);
      ok('S2-4: the question names both units',
         /lb/.test(H.confirmMsgs[0]||'')&&/oz/.test(H.confirmMsgs[0]||''), H.confirmMsgs[0]);
    });

    /* a 20x price jump must ask, and No must not write */
    step(function(){ H.reqs.length=0; H.confirms=0; H.confirmMsgs=[]; H.confirmReturn=false;
                     openEdit(502); });
    step(function(){ set('fPrice','200'); });
    step(function(){ $('saveBtn').click(); });
    step(function(){
      ok('S2-4: a 20x unit cost asks first', H.confirms===1, 'confirms='+H.confirms);
      ok('S2-4: the question names the item', (H.confirmMsgs[0]||'').indexOf('Sea salt')>-1,
         H.confirmMsgs[0]);
      ok('S2-4: the question shows the old and new unit cost',
         /5\.00/.test(H.confirmMsgs[0]||'')&&/100\.00/.test(H.confirmMsgs[0]||''), H.confirmMsgs[0]);
      ok('S2-4: answering No writes nothing',
         H.reqs.filter(function(r){return r.m==='PATCH';}).length===0);
      ok('S2-4: answering No keeps the modal open', shown());
      ok('S2-4: answering No leaves Save usable', $('saveBtn').disabled===false);
    });
    /* 1/10th is the other side of the same gate */
    step(function(){ H.reqs.length=0; H.confirms=0; H.confirmMsgs=[]; H.confirmReturn=true;
                     closeEdit(); openEdit(502); });
    step(function(){ set('fPrice','0.40'); });
    step(function(){ $('saveBtn').click(); });
    step(function(){
      ok('S2-4: a 1/10th unit cost asks too', H.confirms===1, 'confirms='+H.confirms);
      ok('S2-4: answering Yes does write',
         H.reqs.filter(function(r){return r.m==='PATCH';}).length===1);
    });
    /* an ordinary price move must NOT ask - a gate that always fires is a
       gate nobody reads */
    step(function(){ H.reqs.length=0; H.confirms=0; openEdit(502); });
    step(function(){ set('fPrice','0.44'); });
    step(function(){ $('saveBtn').click(); });
    step(function(){
      ok('S2-4: an ordinary price change does not ask', H.confirms===0, 'confirms='+H.confirms);
      ok('S2-4: an ordinary price change still saves',
         H.reqs.filter(function(r){return r.m==='PATCH';}).length===1);
    });
    /* an ADD has nothing to compare against, so it must never ask */
    step(function(){ H.reqs.length=0; H.confirms=0; openAdd(); });
    step(function(){ rowFor('Asia Intl','Slab bacon').click(); });
    step(function(){ set('fQty','1'); set('fUnit','lb'); set('fPrice','9999'); });
    step(function(){ $('saveBtn').click(); });
    step(function(){
      ok('S2-4: an add never asks - there is no previous cost', H.confirms===0,
         'confirms='+H.confirms);
      ok('S2-4: the add is written', posts().length===1, 'saw '+posts().length);
    });
  }

  if(H.scen==='ok'){
    /* nothing is ever selected on your behalf */
    step(function(){ openAdd(); });
    step(function(){
      /* M-c: the suite once ran with no stylesheet at all. .pick-list's
         overflow-y:auto exists only in kitchen.css. */
      ok('css: kitchen.css is loaded', getComputedStyle($('pickList')).overflowY==='auto',
         'overflowY='+getComputedStyle($('pickList')).overflowY);
      var r=rowFor('Asia Intl','Slab bacon');
      ok('css: a pick row is really on screen', visible(r));
      ok('css: a pick row is a 44px tap target', r&&r.getBoundingClientRect().height>=44,
         r&&String(r.getBoundingClientRect().height));
      ok('css: the filter computes to 16px', getComputedStyle($('pickFilter')).fontSize==='16px',
         getComputedStyle($('pickFilter')).fontSize);
    });
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

    /* slice 1, rule 1: the app never chooses an item on your behalf - not on
       open, and not on any keystroke in the filter. Typing narrows the list;
       it never picks the survivor, even when only one survives. */
    step(function(){ set('pickFilter','asia'); });
    step(function(){
      ok('slice1: filtering to one row picks nothing', pickId===null);
      ok('slice1: filtering leaves the chooser up', $('pickChosen').style.display==='none');
      ok('slice1: the filter really did narrow', pickRows().length<4, 'rows='+pickRows().length);
      ok('slice1: filtering fills no field', $('fName').value===''&&$('fQty').value==='');
    });
    step(function(){ set('pickFilter','vinegar'); });
    step(function(){
      ok('slice1: re-filtering picks nothing', pickId===null);
      ok('slice1: re-filtering leaves the chooser up', $('pickChosen').style.display==='none');
    });
    step(function(){ set('pickFilter',''); });
    step(function(){
      ok('slice1: clearing the filter picks nothing', pickId===null);
      ok('slice1: clearing the filter leaves the chooser up', $('pickChosen').style.display==='none');
      ok('slice1: all rows back after clearing', !!rowFor('Asia Intl','Slab bacon'));
    });

    /* B1: an unpriced linked row opens its edit - and must still say WHICH
       item that is. Both Slab bacons unpriced would otherwise open the same
       modal reading only "Slab bacon". */
    step(function(){ rowFor('Birite','Distilled white vinegar').click(); });
    step(function(){
      ok('B1: needs-price tap keeps the chosen line', $('pickWrap').style.display!=='none',
         'pickWrap display='+$('pickWrap').style.display);
      ok('B1: needs-price tap shows the chosen row', $('pickChosen').style.display!=='none');
      ok('B1: needs-price tap keeps the vendor', $('pickChosenV').textContent==='Birite',
         $('pickChosenV').textContent);
      ok('B1: needs-price tap keeps the name',
         $('pickChosenN').textContent==='Distilled white vinegar', $('pickChosenN').textContent);
      ok('B1: needs-price tap opens that ledger row', editId===501, String(editId));
      ok('css: the chosen line is really on screen', visible($('pickChosen')));
      ok('css: the chosen vendor is really on screen', visible($('pickChosenV')));
    });
    step(function(){ closeEdit(); });

    /* slice 1: Change clears the numbers with the pick, so one item's pack
       price can never be carried onto another. */
    step(function(){ openAdd(); });
    step(function(){
      rowFor('Asia Intl','Slab bacon').click();
    });
    step(function(){
      set('fQty','40'); set('fUnit','lb'); set('fPrice','120'); set('fAlias','SLAB BCN 40#');
    });
    step(function(){ $('pickChosen').querySelector('.pick-change').click(); });
    step(function(){
      ok('slice1: Change clears the pick', pickId===null);
      ok('slice1: Change clears qty', $('fQty').value==='', $('fQty').value);
      ok('slice1: Change clears unit', $('fUnit').value==='', $('fUnit').value);
      ok('slice1: Change clears price', $('fPrice').value==='', $('fPrice').value);
      ok('slice1: Change clears alias', $('fAlias').value==='', $('fAlias').value);
      ok('slice1: Change returns to the chooser', $('pickChosen').style.display==='none');
    });

    /* the id we POST is the id of the row that was tapped - Asia Intl 169 */
    step(function(){ H.reqs.length=0; rowFor('Asia Intl','Slab bacon').click(); });
    step(function(){
      ok('css: the chosen line after a new pick is on screen', visible($('pickChosen')));
      ok('ok: tapping picks that row', pickId===169);
      ok('ok: unit is never auto-filled', $('fUnit').value==='');
      ok('ok: the order unit CS is never borrowed', $('fUnit').value!=='CS');
      ok('ok: name is filled from the tapped row', $('fName').value==='Slab bacon');
      set('fQty','40'); set('fPrice','120');
    });
    /* M3: slice 1 says unit is a required field. "40 . $120" with no unit
       previews "$3.00 / unit" and costs every recipe below it wrongly. */
    step(function(){ $('saveBtn').click(); });
    step(function(){
      ok('M3: a unit-less save writes nothing', posts().length===0, 'saw '+posts().length);
      ok('M3: a unit-less save keeps the modal open', $('editModal').className.indexOf('show')>-1);
      ok('M3: a unit-less save keeps the pick', pickId===169);
      ok('M3: a unit-less save keeps the numbers', $('fQty').value==='40'&&$('fPrice').value==='120');
      ok('M3: the save button is usable again', $('saveBtn').disabled===false);
      set('fUnit','lb');
    });
    step(function(){ $('saveBtn').click(); });
    step(function(){
      var p=posts();
      ok('ok: one write for one save', p.length===1, 'saw '+p.length);
      ok('ok: Asia Intl row saves order_item_id 169', p[0]&&p[0].body.order_item_id===169,
         p[0]&&String(p[0].body.order_item_id));
      ok('M3: the typed unit is what saves', p[0]&&p[0].body.pack_unit==='lb',
         p[0]&&JSON.stringify(p[0].body.pack_unit));
      ok('ok: modal closed after save', $('editModal').className.indexOf('show')<0);
      ok('B-new: the toast names the item', toast()==='✓ Slab bacon (Asia Intl) added', toast());
      /* slice 1: closeEdit leaves nothing behind */
      ok('slice1: pickId cleared on close', pickId===null);
      ok('slice1: fields cleared on close', $('fName').value===''&&$('fQty').value===''&&$('fPrice').value==='');
      ok('slice1: fName re-enabled on close', $('fName').disabled===false);
      ok('slice1: filter cleared on close', $('pickFilter').value==='');
      ok('slice1: chosen display reset on close', $('pickChosen').style.display==='none');
    });

    /* and the other Slab bacon - Birite 88 */
    step(function(){ H.reqs.length=0; openAdd(); });
    step(function(){
      ok('ok: the priced row drops out of the picker', !rowFor('Asia Intl','Slab bacon'));
      rowFor('Birite','Slab bacon').click();
    });
    step(function(){
      ok('ok: tapping the second row picks 88', pickId===88);
      set('fQty','12'); set('fUnit','lb'); set('fPrice','88.50');
    });
    step(function(){ $('saveBtn').click(); });
    step(function(){
      var p=posts();
      ok('ok: Birite row saves order_item_id 88', p[0]&&p[0].body.order_item_id===88,
         p[0]&&String(p[0].body.order_item_id));
      ok('ok: the second save carries its own unit', p[0]&&p[0].body.pack_unit==='lb');
    });

    /* slice 1: tapping the backdrop no longer discards typed values */
    step(function(){ H.confirms=0; openEdit(502); });
    step(function(){
      ok('slice1: edit populates the name', $('fName').value==='Sea salt');
      $('editModal').click();
    });
    step(function(){
      ok('slice1: untouched edit does not prompt', H.confirms===0, 'confirms='+H.confirms);
      ok('slice1: untouched edit closes', $('editModal').className.indexOf('show')<0);
    });
    step(function(){ H.confirms=0; openEdit(502); });
    step(function(){ set('fPrice','999'); $('editModal').click(); });
    step(function(){
      ok('slice1: a changed field does prompt', H.confirms===1, 'confirms='+H.confirms);
    });
    /* slice 1: a fresh Add with nothing typed must not prompt either */
    step(function(){ H.confirms=0; openAdd(); });
    step(function(){ $('editModal').click(); });
    step(function(){ ok('slice1: empty Add does not prompt', H.confirms===0, 'confirms='+H.confirms); });
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
    src = src.replace("</body>",
                      RUNNER.replace("__ORDER_ITEM_COUNT__", str(len(ORDER_ITEMS)))
                      + "</body>", 1)
    return src


RESULT_RE = re.compile(r'<div id="harnessResults">(.*?)</div>', re.S)


def run_scenario(chrome, path, scen):
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
            [chrome, "--headless=new", "--disable-gpu", "--no-sandbox",
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
    chrome = find_chrome()
    if not chrome:
        sys.exit("check_costing: no Chrome found. Set CHROME=/path/to/chrome.")
    page = build_page()
    fails, total = [], 0
    with tempfile.TemporaryDirectory() as td:
        path = os.path.join(td, "costing_under_test.html")
        with open(path, "w", encoding="utf-8") as f:
            f.write(page)
        # the page links assets/kitchen.css relatively; without this copy
        # every scenario runs unstyled and no CSS fault can be caught
        shutil.copytree(os.path.join(ROOT, "assets"), os.path.join(td, "assets"))
        for scen in SCENARIOS:
            res, err = run_scenario(chrome, path, scen)
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
    print("costing guard: clean (%d assertions, %d scenarios, %s)" % (total, len(SCENARIOS), PAGE))
    return 0


if __name__ == "__main__":
    sys.exit(main())
