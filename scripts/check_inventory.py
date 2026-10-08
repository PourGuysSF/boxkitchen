#!/usr/bin/env python3
"""
Behaviour guard for the Inventory Guide count sheet (tempest_inventory.html).

Slice 1's promises: the sheet is drawn place by place in walking order, every
item gets the boxes its pack size calls for, every box renders at 16px (#135 -
check_styling.py cannot see these boxes, because they are built at runtime),
and staff only ever READ.

Slice 2's promises: manager set-up writes only behind the PIN, one write at a
time, and every write ends in a fresh read - so the screen shows what the table
holds. Drag reorders within a place and nowhere else. An item is never left in
neither the count nor the left-off list. A new order-guide item is listed until
a manager decides.

None of that can be checked against the live database without writing to it,
so: load the REAL page, neutralise the site-password redirect, replace
XMLHttpRequest with a stub BEFORE the page's own <script> parses (so api() can
only reach an in-memory table and no request can leave the machine), then
drive it in headless Chrome and assert on the DOM and on every request.

The stub is STATEFUL, like the real tables: a write changes what the next read
returns, and it enforces the same unique keys (one active row per item per
place; one active left-off row per item; one place per name, retired or not),
answering 409 as PostgREST would.

    python3 scripts/check_inventory.py          # ONLY=mgr,move to run a few

Exit 0 = clean. Exit 1 = a regression, with the failing assertion named.

Each scenario is one Chrome run: the page reads its fixture's behaviour from
the URL hash, the runner parks its results in #harnessResults, and
--dump-dom hands them back. The page runs STYLED - assets/ and vendor/ are
copied beside it - so font sizes, layout and SortableJS are the real ones.

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

SCENARIOS = (
    # slice 1 - the sheet, read-only
    "ok", "slow", "fail", "packfail", "hang", "empty", "orphan",
    # slice 2 - set-up, manager
    "mgr", "drag", "dragfail", "move", "remove", "newitems", "places", "busy", "lost",
    # slice 3 - counting saves
    "start", "count", "inflight", "countlost", "countclosed", "who")


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
# Tempest's Line is empty on purpose, as Tempest's is.
PLACES = [
    {"id": 1, "location": "Tempest", "label": "Vegetable cooler", "sort_order": 10, "active": True},
    {"id": 6, "location": "Tempest", "label": "Dry storage", "sort_order": 60, "active": True},
    {"id": 8, "location": "Tempest", "label": "Vinegar shelf", "sort_order": 80, "active": True},
    {"id": 10, "location": "Tempest", "label": "Line", "sort_order": 100, "active": True},
    # retired: its name is still taken, as the real unique index keeps it
    {"id": 11, "location": "Tempest", "label": "Old walk-in", "sort_order": 110, "active": False},
]


def g(i, name, vendor, category, unit, active=True):
    return {"id": i, "location": "Tempest", "name": name, "vendor": vendor,
            "category": category, "unit": unit, "active": active}

# The order guide. Every box rule is here:
#   210 Ginger         pack 30 lb      -> Full x 30 lb + Loose lb
#   171 Cilantro       no pack         -> one box, order unit BU
#   44  Mayo           pack 1 Each     -> one box, Each
#   24  Cider vinegar  pack 4 GAL, in TWO places
#   60  Old flour      retired from the order guide, still counted
#   61  Zero pack      pack_qty 0      -> not a pack
#   62  Blank unit     pack_unit ""    -> not a pack
#   63  Long unit      pack 12 bunch   -> the widest two-box row
#   64  Escaped        a name with markup in it
# and for set-up:
#   500, 501  new on the guide - neither counted nor left off
#   600, 601  left off on purpose
#   700       retired from the guide and not counted - must appear nowhere
#   77        counted in a retired place (the orphan scenario only)
GUIDE = [
    g(210, "Ginger", "Cooks Produce", "Veggies", "lb"),
    g(171, "Cilantro", "Cooks Produce", "Herbs", "BU"),
    g(63, "Long unit thing", "Cooks Produce", "Misc", "CS"),
    g(64, "Tom <b>bold</b> & co", "Birite", "Dry Grocery", "EA"),
    g(44, "Mayo", "Birite", "Dry Grocery", "CS"),
    g(24, "Apple cider vinegar", "Birite", "Liquid", "GAL"),
    g(60, "Old flour", "Birite", "Flour & Baking", "BAG", active=False),
    g(61, "Zero pack", "Birite", "Dry Grocery", "CS"),
    g(62, "Blank unit", "Birite", "Dry Grocery", "EA"),
    g(77, "Lost in a retired place", "Birite", "Dry Grocery", "EA"),
    g(500, "Brand new thing", "Birite", "Cooler", "CS"),
    g(501, "Another new one", "Cooks Produce", "Fruit", "lb"),
    g(600, "Paper towel", "Birite", "Paper Goods", "CS"),
    g(601, "Staff coffee", "Birite", "Dry Grocery", "EA"),
    g(700, "Gone from the guide", "Birite", "Dry Grocery", "EA", active=False),
]


def it(i, oid, place, sort):
    return {"id": i, "location": "Tempest", "order_item_id": oid, "place_id": place,
            "sort_order": sort, "active": True}

ITEMS = [
    it(101, 210, 1, 10), it(102, 171, 1, 20), it(103, 63, 1, 30), it(104, 64, 1, 40),
    it(201, 44, 6, 10), it(202, 24, 6, 20), it(203, 60, 6, 30), it(204, 61, 6, 40), it(205, 62, 6, 50),
    it(301, 24, 8, 10),
]
ORPHAN = it(999, 77, 11, 5)   # place 11 is retired
LEFT_OFF = [
    {"id": 1, "location": "Tempest", "order_item_id": 600, "active": True},
    {"id": 2, "location": "Tempest", "order_item_id": 601, "active": True},
    # an old, undone decision - inactive rows never count
    {"id": 3, "location": "Tempest", "order_item_id": 500, "active": False},
]
# pack_price is in the fixture on purpose: the page must never draw it even
# if the table hands one back.
def cost(oid, qty, unit, price, active=True):
    return {"location": "Tempest", "order_item_id": oid, "pack_qty": qty, "pack_unit": unit,
            "pack_price": price, "active": active}

COSTS = [
    cost(210, 30, "lb", 54.5), cost(44, 1, "Each", 9.25), cost(24, 4, "GAL", 31),
    cost(61, 0, "lb", 10), cost(62, 6, "  ", 10), cost(63, 12, "bunch", 18),
    # a retired price-list row must not give Cilantro a pack
    cost(171, 6, "bunch", 12, active=False),
]

STAFF = [
    {"name": "Maria", "location": "Tempest", "active": True},
    {"name": "Jose", "location": "Tempest", "active": True},
    {"name": "Maria", "location": "Tempest", "active": True},    # a second shift: one entry, not two
    {"name": "Ana", "location": "Tempest", "active": False},     # retired: never offered
]
OPEN_COUNT = {"id": 7, "location": "Tempest", "period": "2026-10-01", "status": "open"}


def line(i, item, full, loose, snap_qty, snap_unit, by):
    return {"id": i, "location": "Tempest", "count_id": 7, "inventory_item_id": item,
            "full_qty": full, "loose_qty": loose, "pack_qty_snap": snap_qty,
            "pack_unit_snap": snap_unit, "counted_by": by, "updated_at": "2026-10-07T18:00:00Z"}

LINES = [
    line(900, 201, 3, None, 1, "Each", "Jose"),        # Mayo: counted
    line(901, 204, None, None, None, "CS", "Maria"),   # Zero pack: counted, then cleared
    line(902, 101, 1, 4, 40, "lb", "Maria"),           # Ginger: counted against a 40 lb pack,
                                                       # which the price list has since made 30
]
COUNT_SCENARIOS = ["count", "inflight", "countlost", "countclosed", "who"]

# ------------------------------------------------------------ page surgery --

GATE_RE = re.compile(r"window\.location\.replace\('index\.html'\)")

HARNESS = r"""
<script>
/* ---- test harness: installed BEFORE the page script parses ---- */
(function(){
  var SCEN=(location.hash||'#ok').slice(1);
  var FX=__FIXTURES__;
  var reqs=[], deferred=[], hung=[];
  /* the tables, stateful: a write changes what the next read returns */
  var T={
    inventory_places:FX.places,
    inventory_items:SCEN==='empty'?[]:(SCEN==='orphan'?FX.items.concat([FX.orphan]):FX.items),
    inventory_left_off:FX.leftOff,
    order_items:SCEN==='orphan'?FX.guide:FX.guide.filter(function(r){return r.id!==77;}),
    ingredient_costs:FX.costs,
    staff:FX.staff,
    inventory_counts:FX.countScens.indexOf(SCEN)>-1?[FX.openCount]:[],
    inventory_count_lines:FX.countScens.indexOf(SCEN)>-1?FX.lines:[],
    inventory_count_log:[]
  };
  /* 'start': last month already has a (closed) count, so starting it again must be refused */
  if(SCEN==='start')T.inventory_counts.push({id:6,location:'Tempest',period:FX.lastMonth,status:'closed'});
  if(SCEN==='empty')T.inventory_places=[];
  var nextId=5000;
  window.__h={scen:SCEN,reqs:reqs,fails:[],log:[],tables:T,fx:FX,confirmMsgs:[],confirmReturn:true,
    /* per-table read plans, consumed in order: 'err' = no answer (onerror),
       'e500' = the server says no, 'hang' = nothing until timeoutAll() */
    next:{inventory_places:[],inventory_items:[],ingredient_costs:[],order_items:[],inventory_left_off:[]},
    /* write fates, consumed in order by POST/PATCH:
       'e500' nothing written, a 500; 'lost' written, but the answer never
       comes; 'drop' not written, no answer; 'defer' written, answer held
       until releaseDeferred() */
    nextWrite:[]};
  var N=window.__h.next;
  if(SCEN==='fail')N.inventory_items.push('err');
  if(SCEN==='packfail')N.ingredient_costs.push('e500');
  if(SCEN==='hang'){N.inventory_places.push('hang');N.inventory_items.push('hang');N.ingredient_costs.push('hang');}

  function clone(x){return JSON.parse(JSON.stringify(x));}
  function table(u){var m=u.match(/\/rest\/v1\/([a-z_]+)/);return m?m[1]:'';}
  function query(u){var q={},s=u.split('?')[1]||'';s.split('&').forEach(function(kv){var i=kv.indexOf('=');if(i>0)q[kv.slice(0,i)]=decodeURIComponent(kv.slice(i+1));});return q;}
  function guideRow(oid){for(var i=0;i<T.order_items.length;i++)if(T.order_items[i].id===oid)return T.order_items[i];return null;}

  function read(t,q){
    var rows=(T[t]||[]).filter(function(r){
      if(q.location&&r.location!==undefined&&('eq.'+r.location)!==q.location)return false;
      if(q.active==='eq.true'&&r.active!==true)return false;
      if(q.order_item_id==='not.is.null'&&r.order_item_id==null)return false;
      if(q.status&&('eq.'+r.status)!==q.status)return false;
      if(q.count_id&&('eq.'+r.count_id)!==q.count_id)return false;
      return true;
    }).map(clone);
    if(t==='inventory_items')rows.forEach(function(r){var g=guideRow(r.order_item_id);
      r.order_items=g?{name:g.name,vendor:g.vendor,unit:g.unit,active:g.active}:null;});
    if(t==='inventory_places'||t==='inventory_items')rows.sort(function(a,b){return a.sort_order-b.sort_order||a.id-b.id;});
    return rows;
  }
  /* the real unique keys, as the 409s PostgREST would send */
  function clash(t,row,selfId){
    return (T[t]||[]).some(function(o){
      if(o.id===selfId)return false;
      if(t==='inventory_items')return o.active&&row.active!==false&&o.place_id===row.place_id&&o.order_item_id===row.order_item_id;
      if(t==='inventory_left_off')return o.active&&row.active!==false&&o.location===row.location&&o.order_item_id===row.order_item_id;
      if(t==='inventory_places')return o.location===row.location&&o.label===row.label;
      if(t==='inventory_counts')return o.location===row.location&&(o.period===row.period||(o.status==='open'&&row.status!=='closed'));
      return false;
    });
  }
  function countOpen(cid){return T.inventory_counts.some(function(c){return c.id===cid&&c.status==='open';});}
  function write(m,t,q,body){
    if(['inventory_items','inventory_left_off','inventory_places','inventory_counts','inventory_count_lines','inventory_count_log'].indexOf(t)<0)
      return {status:403,text:'{"message":"harness: '+m+' to '+t+' is not allowed"}'};
    if(t==='inventory_count_log'&&m!=='POST')return {status:403,text:'{"message":"the log is append-only"}'};
    if(t==='inventory_count_lines'){
      /* RLS: a line can be added or changed only while its count is open */
      if(!countOpen(body&&body.count_id))return {status:403,text:'{"code":"42501","message":"new row violates row-level security policy"}'};
      if(m!=='POST')return {status:405,text:'{"message":"harness: lines are saved by upsert only"}'};
      var hit=null;for(var i=0;i<T[t].length;i++){var o=T[t][i];if(o.count_id===body.count_id&&o.inventory_item_id===body.inventory_item_id)hit=o;}
      if(hit){
        if(q.on_conflict!=='count_id,inventory_item_id')return {status:409,text:'{"code":"23505"}'};
        for(var k in body)hit[k]=body[k];return {status:201,text:JSON.stringify([clone(hit)])};
      }
      var nl=clone(body);nl.id=nextId++;T[t].push(nl);return {status:201,text:JSON.stringify([nl])};
    }
    if(m==='POST'){
      var row=clone(body);if(row.active===undefined)row.active=true;row.id=nextId++;
      if(t==='inventory_counts'&&!row.status)row.status='open';   // the column default
      if(clash(t,row,null))return {status:409,text:'{"code":"23505"}'};
      T[t].push(row);return {status:201,text:JSON.stringify([row])};
    }
    if(m==='PATCH'){
      var id=parseInt((q.id||'').replace('eq.',''),10),target=null;
      for(var i=0;i<T[t].length;i++)if(T[t][i].id===id)target=T[t][i];
      if(!target)return {status:200,text:'[]'};
      var next=clone(target);for(var k in body)next[k]=body[k];
      if(clash(t,next,id))return {status:409,text:'{"code":"23505"}'};
      for(var k in body)target[k]=body[k];
      return {status:200,text:JSON.stringify([clone(target)])};
    }
    return {status:405,text:'{"message":"harness: '+m+' not supported"}'};
  }

  function route(m,u,body){
    var t=table(u),q=query(u);
    if(m==='GET'){
      var plan=(N[t]||[]).shift();
      if(plan==='err')return {err:true};
      if(plan==='e500')return {status:500,text:'{"message":"boom"}'};
      if(plan==='hang')return {hang:true};
      if(!T[t])return {status:404,text:'{"message":"harness: unknown table '+t+'"}'};
      var res={status:200,text:JSON.stringify(read(t,q))};
      if(SCEN==='slow')return {defer:true,res:res};
      return res;
    }
    var fate=window.__h.nextWrite.shift();
    if(fate==='e500')return {status:500,text:'{"message":"boom"}'};
    if(fate==='drop')return {err:true};
    var w=write(m,t,q,body);
    if(fate==='lost')return {err:true};
    if(fate==='empty')return {status:201,text:'[]'};   // written, but the answer holds no row
    if(fate==='defer')return {defer:true,res:w};
    return w;
  }

  function Fake(){this.status=0;this.responseText='';this.timeout=0;this._h={};}
  Fake.prototype.open=function(m,u){this._m=m;this._u=u;};
  Fake.prototype.setRequestHeader=function(k,v){this._h[k]=v;};
  Fake.prototype.send=function(b){
    var self=this,parsed=null;
    if(b){try{parsed=JSON.parse(b);}catch(e){}}
    reqs.push({m:this._m,u:this._u,t:table(this._u),body:parsed,timeout:this.timeout,prefer:this._h.Prefer||''});
    var r=route(this._m,this._u,parsed);
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
  window.__h.deferredCount=function(){return deferred.length;};
  window.__h.timeoutAll=function(){var d=hung.slice();hung.length=0;for(var i=0;i<d.length;i++)if(d[i].ontimeout)d[i].ontimeout();};
  window.__h.hungCount=function(){return hung.length;};
  window.confirm=function(msg){window.__h.confirmMsgs.push(String(msg));return window.__h.confirmReturn;};
})();
</script>
"""

RUNNER = r"""
<script>
(function(){
  var H=window.__h, F=H.fails, T=H.tables;
  function ok(name,cond,extra){if(!cond)F.push(name+(extra!=null?' :: '+extra:''));H.log.push((cond?'PASS ':'FAIL ')+name);}
  function byId(id){return document.getElementById(id);}
  function all(sel,root){return Array.prototype.slice.call((root||document).querySelectorAll(sel));}
  function inputs(){return all('.stock-input');}
  function heads(){return all('.stock-place-hd .cat-label').map(function(e){return e.textContent;});}
  var SETUP=['New on the order guide','Left off on purpose','Not in an active place'];
  function placeHeads(){return heads().filter(function(h){return SETUP.indexOf(h)<0;});}
  /* rows under a heading: everything up to the next heading, nested or not */
  function rowsUnder(label){
    var out=[],hd=all('.stock-place-hd').filter(function(h){return h.querySelector('.cat-label').textContent===label;})[0];
    for(var n=hd&&hd.nextElementSibling;n&&!n.classList.contains('stock-place-hd');n=n.nextElementSibling){
      if(n.classList.contains('stock-row'))out.push(n);
      else out=out.concat(all('.stock-row',n));
    }
    return out;
  }
  function nameOf(r){return r.querySelector('.count-name').textContent;}
  function names(label){return rowsUnder(label).map(nameOf);}
  function rowNamed(label,name){return rowsUnder(label).filter(function(r){return nameOf(r)===name;})[0];}
  function units(row){return all('.stock-unit',row).map(function(e){return e.textContent;});}
  function parts(row){return all('.stock-input',row).map(function(e){return e.getAttribute('data-part');});}
  function body(){return byId('appBody').textContent;}
  function writes(){return H.reqs.filter(function(r){return r.m!=='GET';});}
  function reads(t){return H.reqs.filter(function(r){return r.m==='GET'&&(!t||r.t===t);});}
  function toast(){return byId('toast').textContent;}
  function toastIsError(){return /\berror\b/.test(byId('toast').className);}
  function btn(row,text){return all('button',row).filter(function(b){return b.textContent===text;})[0];}
  function row(t,id){for(var i=0;i<T[t].length;i++)if(T[t][i].id===id)return T[t][i];return null;}
  function shown(id){return byId(id).classList.contains('show');}
  function pickBtn(label){return all('#pickList .stock-pick').filter(function(b){return b.textContent.indexOf(label)===0;})[0];}
  function visible(el){if(!el)return false;var r=el.getBoundingClientRect(),cs=getComputedStyle(el);return r.height>0&&r.width>0&&cs.display!=='none'&&cs.visibility!=='hidden';}

  var steps=[];
  function step(fn){steps.push(fn);}
  function tick(){step(function(){});}
  function run(){
    if(!steps.length){
      var out=document.createElement('div');out.id='harnessResults';
      out.textContent=JSON.stringify({scen:H.scen,fails:F,log:H.log});
      document.body.appendChild(out);return;
    }
    var fn=steps.shift(),wait=0;
    try{wait=fn();}catch(e){F.push('threw in step: '+(e&&e.message));}
    setTimeout(run,typeof wait==='number'?wait:0);
  }

  /* every scenario: staff never write; and every read is Tempest's */
  function readOnly(tag){
    ok(tag+': no request but GET', writes().length===0, JSON.stringify(writes()));
    ok(tag+': every request is scoped to Tempest',
       H.reqs.every(function(r){return r.u.indexOf('location=eq.Tempest')>-1||r.m==='PATCH';}),
       JSON.stringify(H.reqs.map(function(r){return r.u;})));
  }
  /* unlock through the real gate. The PIN is read out of the page's own
     variable and never printed anywhere. */
  function unlock(){
    step(function(){ byId('mgrSwitch').click(); });
    step(function(){ byId('pinInput').value=MANAGER_PIN; byId('pinInput').dispatchEvent(new KeyboardEvent('keydown',{key:'Enter',bubbles:true})); });
    tick();
  }

  /* ============================== slice 1 ============================== */
  if(H.scen==='ok'){
    step(function(){
      ok('ok: kitchen.css loaded (the page runs styled)', getComputedStyle(document.querySelector('.header')).position==='sticky');
      ok('ok: five reads - places, items, pack sizes, the open count, the staff list', H.reqs.length===5&&['inventory_places','inventory_items','ingredient_costs','inventory_counts','staff'].every(function(t){return reads(t).length===1;}), JSON.stringify(H.reqs.map(function(r){return r.t;})));
      ok('ok: with no count open, no lines are asked for', reads('inventory_count_lines').length===0);
      ok('ok: with no count open, staff see no name bar', byId('nameBar').style.display==='none');
      ok('ok: ...and the intro says no count is open', /No count is open yet/.test(byId('introBar').textContent), byId('introBar').textContent);
      ok('ok: staff never read the order guide or the left-off list', reads('order_items').length===0&&reads('inventory_left_off').length===0);
      ok('ok: every read has the 60s load timeout', H.reqs.every(function(r){return r.timeout===60000;}),
         JSON.stringify(H.reqs.map(function(r){return r.timeout;})));
      var cost=reads('ingredient_costs')[0]||{u:''};
      ok('ok: the price list is asked for pack size only, never a price',
         /select=order_item_id,pack_qty,pack_unit(&|$)/.test(cost.u)&&cost.u.indexOf('price')<0, cost.u);
      ok('ok: retired places and items are not asked for',
         reads().filter(function(r){return /inventory_(places|items)/.test(r.t);}).every(function(r){return r.u.indexOf('active=eq.true')>-1;}));
      readOnly('ok');

      ok('ok: places in walking order', JSON.stringify(heads())===JSON.stringify(['Vegetable cooler','Dry storage','Vinegar shelf','Line']), JSON.stringify(heads()));
      var counts=all('.stock-place-n').map(function(e){return e.textContent;});
      ok('ok: each place says how many items', JSON.stringify(counts)===JSON.stringify(['4 items','5 items','1 item','0 items']), JSON.stringify(counts));
      ok('ok: an empty place says so', rowsUnder('Line').length===0&&body().indexOf('Nothing is stored here yet.')>-1);
      ok('ok: items in their order within a place', JSON.stringify(names('Vegetable cooler'))===JSON.stringify(['Ginger','Cilantro','Long unit thing','Tom <b>bold</b> & co']), JSON.stringify(names('Vegetable cooler')));

      var gr=rowNamed('Vegetable cooler','Ginger');
      ok('ok: a pack of 30 lb gets Full and Loose', gr&&JSON.stringify(parts(gr))==='["full","loose"]', gr&&JSON.stringify(parts(gr)));
      ok('ok: ...labelled x 30 lb and lb', gr&&JSON.stringify(units(gr))==='["× 30 lb","lb"]', gr&&JSON.stringify(units(gr)));
      ok('ok: ...with Full and Loose captions', gr&&all('.stock-lbl',gr).map(function(e){return e.textContent;}).join('/')==='Full/Loose');
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
      ok('ok: ...and each says where else it is', v1&&v2&&v1.textContent.indexOf('also in Vinegar shelf')>-1&&v2.textContent.indexOf('also in Dry storage')>-1);
      ok('ok: ...and the other rows do not', rowNamed('Dry storage','Mayo').textContent.indexOf('also in')<0);
      ok('ok: a vendor is shown', rowNamed('Dry storage','Mayo').querySelector('.count-par').textContent==='Birite');
      ok('ok: an item retired from the order guide says so', rowNamed('Dry storage','Old flour').textContent.indexOf('no longer on the order guide')>-1);

      var e=rowNamed('Vegetable cooler','Tom <b>bold</b> & co');
      ok('ok: a name with markup in it is shown as text, not run as HTML', e&&!e.querySelector('.count-name b'));
      ok('ok: no dollar figure anywhere on the page', document.body.innerText.indexOf('$')<0&&body().indexOf('54.5')<0&&body().indexOf('9.25')<0);
      ok('ok: staff see no manager controls', all('.drag-handle').length===0&&all('.row-mgr-actions').length===0&&!document.querySelector('.manager-mode'));
      ok('ok: no drag lists for staff', all('.stock-place-body').every(function(l){return !Sortable.get(l);}));

      var ins=inputs(), bad=ins.filter(function(i){return parseFloat(getComputedStyle(i).fontSize)<16;});
      ok('ok: every box computes to 16px or more (#135)', ins.length===14&&bad.length===0,
         ins.length+' boxes; small: '+bad.map(function(i){return i.getAttribute('aria-label')+'='+getComputedStyle(i).fontSize;}).join(', '));
      ok('ok: every box is a 44px tap target', ins.every(function(i){return i.getBoundingClientRect().height>=44;}));
      ok('ok: every box is text with a decimal keypad', ins.every(function(i){return i.type==='text'&&i.getAttribute('inputmode')==='decimal';}));
      ok('ok: every box is locked - nothing can be typed in a preview', ins.every(function(i){return i.disabled;}));
      ok('ok: every box is named for a screen reader', ins.every(function(i){return (i.getAttribute('aria-label')||'').length>3;}));
      ok('ok: a locked box still shows a visible edge (dashed, --edge)', ins.every(function(i){var s=getComputedStyle(i);
         return s.borderTopStyle==='dashed'&&s.borderTopColor==='rgb(142, 140, 132)';}), getComputedStyle(ins[0]).borderTopColor);
      var lefts=all('.stock-row').filter(function(r){return all('.stock-input',r).length===1;})
        .map(function(r){return Math.round(r.querySelector('.stock-input').getBoundingClientRect().left);});
      ok('ok: one-box rows line their boxes up in one column', lefts.length===6&&Math.max.apply(null,lefts)-Math.min.apply(null,lefts)<=1, JSON.stringify(lefts));
      ok('ok: the summary counts items, not rows', byId('sheetSummary').textContent==='9 items · 4 places', byId('sheetSummary').textContent);
      ok('ok: the intro says how many items have a pack size', /4 of 9 items have a pack size/.test(byId('introBar').textContent), byId('introBar').textContent);
      /* the markup inputs check_styling.py also measures - checked here so a
         fault shows up in this guard's own run */
      ['pinInput','nameInput'].forEach(function(id){
        ok('ok: #'+id+' computes to 16px or more (#135)', parseFloat(getComputedStyle(byId(id)).fontSize)>=16, getComputedStyle(byId(id)).fontSize);
      });
    });
    [390,320].forEach(function(w){
      step(function(){ document.body.style.width=w+'px'; });
      step(function(){
        var over=all('.stock-row').filter(function(r){
          var rr=r.getBoundingClientRect();
          return r.scrollWidth>r.clientWidth+1||all('.stock-input,.stock-unit',r).some(function(x){return x.getBoundingClientRect().right>rr.right+0.5;});
        });
        ok('ok: at '+w+'px no row runs off the edge', over.length===0, over.map(nameOf).join(', '));
        var gi=all('.stock-input',rowNamed('Vegetable cooler','Ginger'));
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
      ok('slow: a second load while loading sends nothing', H.reqs.length===5, H.reqs.length);
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
      ok(tag+': the toast is an error, not a success', toastIsError(), byId('toast').className);
      ok(tag+': no summary', byId('sheetSummary').textContent==='');
      var b=all('#appBody button')[0];
      ok(tag+': offers Try again', !!b&&/Try again/.test(b.textContent));
      if(b)b.click();
    });
    step(function(){
      ok(tag+': Try again loads it', inputs().length===14, inputs().length);
      ok(tag+': ...with five fresh reads', H.reqs.length===10, H.reqs.length);
      readOnly(tag);
    });
  }

  if(H.scen==='hang'){
    step(function(){
      ok('hang: still loading while nothing answers', /Loading the count sheet/.test(body())&&inputs().length===0);
      ok('hang: the three hung reads are waiting', H.hungCount()===3, H.hungCount());
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
    unlock();
    step(function(){
      var r=rowNamed('Not in an active place','Lost in a retired place');
      ok('orphan: in manager mode it can be moved into a place', !!(r&&btn(r,'Move')));
      ok('orphan: ...but has no grip - it is in no list to sort', r&&!r.querySelector('.drag-handle'));
    });
  }

  /* ============================== slice 2 ============================== */
  if(H.scen==='mgr'){
    step(function(){ byId('mgrSwitch').click(); });
    step(function(){
      ok('mgr: the switch asks for the PIN', shown('pinModal'));
      byId('pinInput').value='0000'===MANAGER_PIN?'1111':'0000';
      byId('pinInput').dispatchEvent(new KeyboardEvent('keydown',{key:'Enter',bubbles:true}));
    });
    step(function(){
      ok('mgr: a wrong PIN is refused, and says so', shown('pinModal')&&byId('pinErr').classList.contains('show')&&!document.querySelector('.manager-mode'));
      ok('mgr: ...and reads nothing extra', reads('order_items').length===0);
      byId('pinInput').value=MANAGER_PIN;
      byId('pinInput').dispatchEvent(new KeyboardEvent('keydown',{key:'Enter',bubbles:true}));
    });
    tick();
    step(function(){
      ok('mgr: the right PIN unlocks it', !shown('pinModal')&&!!document.querySelector('.manager-mode')&&byId('mgrSwitch').getAttribute('aria-checked')==='true');
      var g=reads('order_items')[0]||{u:''};
      ok('mgr: unlocking reads the order guide and left-off list, once each', reads('order_items').length===1&&reads('inventory_left_off').length===1);
      ok('mgr: the order guide is asked for no price either', g.u.indexOf('price')<0&&/active=eq\.true/.test(g.u), g.u);
      ok('mgr: unlocking writes nothing', writes().length===0);
      ok('mgr: the sheet stays on screen while it reloads (no spinner flash)', !document.querySelector('#appBody .loading'));

      ok('mgr: every row in a place has a grip', all('.stock-place-body .stock-row').every(function(r){return !!r.querySelector('.drag-handle');}));
      ok('mgr: every row has Move and Remove', all('.stock-place-body .stock-row').every(function(r){return btn(r,'Move')&&btn(r,'Remove');}));
      ok('mgr: the count boxes give way to the controls', inputs().every(function(i){return !visible(i);}));
      ok('mgr: one drag list per place, grabbed only by its grip',
         all('.stock-place-body').length===4&&all('.stock-place-body').every(function(l){var s=Sortable.get(l);return s&&s.options.handle==='.drag-handle'&&!s.options.disabled;}));
      ok('mgr: a drag list cannot reach another place (no shared group)', all('.stock-place-body').every(function(l){var gp=Sortable.get(l).options.group;return !(gp&&gp.name);}));
      ok('mgr: the intro explains set-up', /Manager set-up/.test(byId('introBar').textContent));
      ok('mgr: the Places button is there', /Places/.test((document.querySelector('.mgr-add-btn')||{}).textContent||''));

      ok('mgr: new guide items are listed, by name', JSON.stringify(names('New on the order guide'))===JSON.stringify(['Brand new thing','Another new one']), JSON.stringify(names('New on the order guide')));
      ok('mgr: ...each with Add and Don’t count', rowsUnder('New on the order guide').every(function(r){return btn(r,'Add')&&btn(r,'Don’t count');}));
      ok('mgr: an undone left-off decision does not hide a new item', names('New on the order guide').indexOf('Brand new thing')>-1);
      ok('mgr: an item retired from the guide is never "new"', body().indexOf('Gone from the guide')<0);
      ok('mgr: left-off items are not "new"', names('New on the order guide').indexOf('Paper towel')<0);
      var lo=all('.stock-place-hd').filter(function(h){return /Left off on purpose/.test(h.textContent);})[0];
      ok('mgr: the left-off list is there, collapsed, with its count', !!lo&&/2 items/.test(lo.textContent)&&rowsUnder('Left off on purpose').length===0);
      byId('leftOffBtn').click();
    });
    step(function(){
      ok('mgr: Show opens it', JSON.stringify(names('Left off on purpose'))===JSON.stringify(['Staff coffee','Paper towel']), JSON.stringify(names('Left off on purpose')));
      ok('mgr: ...each with Count it', rowsUnder('Left off on purpose').every(function(r){return !!btn(r,'Count it');}));
      ok('mgr: ...and the button says what it does now', byId('leftOffBtn').textContent==='Hide the list'&&byId('leftOffBtn').getAttribute('aria-expanded')==='true');
      ok('mgr: still nothing written', writes().length===0);
      byId('mgrSwitch').click();
    });
    step(function(){
      ok('mgr: switching off returns the plain sheet', !document.querySelector('.manager-mode')&&all('.drag-handle').length===0&&inputs().length===14&&inputs().every(visible));
      ok('mgr: ...with no drag list left alive', all('.stock-place-body').every(function(l){return !Sortable.get(l);}));
      ok('mgr: ...and no set-up sections', heads().indexOf('New on the order guide')<0&&heads().indexOf('Left off on purpose')<0);
      byId('mgrSwitch').click();
    });
    tick();
    step(function(){
      ok('mgr: unlocked once, the switch goes straight back on this session', !!document.querySelector('.manager-mode')&&!shown('pinModal'));
      ok('mgr: ...without reading the set-up lists again', reads('order_items').length===1, reads('order_items').length);
    });
  }

  function dragTo(placeId,from,to){
    var list=document.querySelector('.stock-place-body[data-place-id="'+placeId+'"]'),rows=all('.stock-row',list);
    var moving=rows[from];
    if(to<from)list.insertBefore(moving,rows[to]);else list.insertBefore(moving,rows[to].nextSibling);
    Sortable.get(list).options.onEnd({item:moving,from:list,to:list,oldIndex:from,newIndex:to});
  }

  if(H.scen==='drag'){
    unlock();
    step(function(){
      H.nextWrite.push('defer','defer');
      dragTo(1,1,0);   // Cilantro above Ginger
      var w=writes();
      ok('drag: only the rows whose number changed are saved', w.length===2&&w.every(function(r){return r.m==='PATCH'&&r.t==='inventory_items';}), JSON.stringify(w));
      var by={};w.forEach(function(r){by[r.u.split('id=eq.')[1]]=r.body;});
      ok('drag: ...renumbered 10 and 20, nothing else in the payload', JSON.stringify(by['102'])==='{"sort_order":10}'&&JSON.stringify(by['101'])==='{"sort_order":20}', JSON.stringify(by));
      ok('drag: while it saves, every drag list is locked', all('.stock-place-body').every(function(l){return Sortable.get(l).options.disabled===true;}));
      H.releaseDeferred();
    });
    tick();
    step(function(){
      ok('drag: saved, it says so', /Order saved/.test(toast())&&!toastIsError(), toast());
      ok('drag: ...and the lists unlock', all('.stock-place-body').every(function(l){return Sortable.get(l).options.disabled===false;}));
      ok('drag: the table now holds the new order', row('inventory_items',102).sort_order===10&&row('inventory_items',101).sort_order===20);
      ok('drag: other places untouched', row('inventory_items',201).sort_order===10&&row('inventory_items',301).sort_order===10);
      var before=writes().length;
      dragTo(1,2,2);
      ok('drag: a drop back where it started saves nothing', writes().length===before);
      dragTo(6,4,0);   // Blank unit to the top of Dry storage: every row there renumbers
      var w=writes().slice(before);
      ok('drag: moving the last row to the top renumbers the whole place, and only it', w.length===5&&w.every(function(r){return ['201','202','203','204','205'].indexOf(r.u.split('id=eq.')[1])>-1;}), JSON.stringify(w.map(function(r){return r.u;})));
    });
    tick();
    step(function(){
      ok('drag: the screen shows the saved order', JSON.stringify(names('Dry storage'))===JSON.stringify(['Blank unit','Mayo','Apple cider vinegar','Old flour','Zero pack']), JSON.stringify(names('Dry storage')));
      var srv=T.inventory_items.filter(function(r){return r.place_id===6&&r.active;}).sort(function(a,b){return a.sort_order-b.sort_order;}).map(function(r){return r.id;});
      ok('drag: ...and the table agrees', JSON.stringify(srv)==='[205,201,202,203,204]', JSON.stringify(srv));
    });
  }

  if(H.scen==='dragfail'){
    unlock();
    step(function(){
      H.nextWrite.push('e500');
      var r0=reads().length;
      H.r0=r0;
      dragTo(1,1,0);
    });
    tick();tick();
    step(function(){
      ok('dragfail: a failed save says so', /Could not save/.test(toast())&&toastIsError(), toast());
      ok('dragfail: ...and re-reads the sheet rather than trusting the screen', reads('inventory_items').length>=2&&reads().length>H.r0);
      ok('dragfail: ...which shows what the table really holds (half saved)', JSON.stringify(names('Vegetable cooler'))===JSON.stringify(['Ginger','Cilantro','Long unit thing','Tom <b>bold</b> & co'])
         ||JSON.stringify(names('Vegetable cooler'))===JSON.stringify(['Cilantro','Ginger','Long unit thing','Tom <b>bold</b> & co']), JSON.stringify(names('Vegetable cooler')));
      var srv=T.inventory_items.filter(function(r){return r.place_id===1&&r.active;}).sort(function(a,b){return a.sort_order-b.sort_order||a.id-b.id;}).map(function(r){return r.id;});
      var scr=rowsUnder('Vegetable cooler').map(function(r){return parseInt(r.getAttribute('data-id'),10);});
      ok('dragfail: the screen matches the table exactly', JSON.stringify(srv)===JSON.stringify(scr), JSON.stringify(srv)+' vs '+JSON.stringify(scr));
      ok('dragfail: the lists unlock again', all('.stock-place-body').every(function(l){return Sortable.get(l).options.disabled===false;}));
    });
  }

  if(H.scen==='move'){
    unlock();
    step(function(){ btn(rowNamed('Vegetable cooler','Ginger'),'Move').click(); });
    step(function(){
      ok('move: the picker opens, titled for the item', shown('pickModal')&&/^Move Ginger/.test(byId('pickTitle').textContent), byId('pickTitle').textContent);
      ok('move: ...says where it is now', /Vegetable cooler/.test(byId('pickSub').textContent));
      ok('move: ...offers Move and Also count, Move chosen', byId('pickToggle').style.display!=='none'&&byId('pickMoveBtn').classList.contains('active'));
      ok('move: its own place cannot be picked', pickBtn('Vegetable cooler').disabled);
      ok('move: every other place can', !pickBtn('Dry storage').disabled&&!pickBtn('Line').disabled);
      ok('move: retired places are not offered', !pickBtn('Old walk-in'));
      ok('move: opening it writes nothing', writes().length===0);
      var m=document.querySelector('#pickModal .modal');
      ok('move: nothing in the picker pokes out of the modal', m.scrollWidth<=m.clientWidth&&m.getBoundingClientRect().width<=381, m.scrollWidth+'/'+m.clientWidth);
      ok('move: every place button is a full tap target', all('#pickList .stock-pick').every(function(b){return b.getBoundingClientRect().height>=48;}));
      pickBtn('Dry storage').click();
    });
    step(function(){
      var w=writes();
      ok('move: one write - the row changes place, to the bottom of it', w.length===1&&w[0].m==='PATCH'&&w[0].u.indexOf('inventory_items?id=eq.101')>-1&&JSON.stringify(w[0].body)==='{"place_id":6,"sort_order":60}', JSON.stringify(w));
    });
    tick();
    step(function(){
      ok('move: it says where it went', /Moved to Dry storage/.test(toast()), toast());
      ok('move: after the re-read it is in Dry storage, last', names('Dry storage')[names('Dry storage').length-1]==='Ginger'&&names('Vegetable cooler').indexOf('Ginger')<0, JSON.stringify(names('Dry storage')));
      btn(rowNamed('Dry storage','Mayo'),'Move').click();
    });
    step(function(){
      byId('pickAlsoBtn').click();
      ok('move: Also count retitles the picker', /^Also count Mayo/.test(byId('pickTitle').textContent)&&byId('pickAlsoBtn').classList.contains('active'));
      pickBtn('Line').click();
    });
    step(function(){
      var w=writes().slice(1);
      ok('move: Also count adds a second row, leaving the first', w.length===1&&w[0].m==='POST'&&w[0].t==='inventory_items'&&
         JSON.stringify(w[0].body)==='{"location":"Tempest","order_item_id":44,"place_id":10,"sort_order":10}', JSON.stringify(w));
    });
    tick();
    step(function(){
      ok('move: ...and Mayo is now in both places', !!rowNamed('Dry storage','Mayo')&&!!rowNamed('Line','Mayo')&&/also in Line/.test(rowNamed('Dry storage','Mayo').textContent));
      btn(rowNamed('Dry storage','Apple cider vinegar'),'Move').click();
    });
    step(function(){
      ok('move: a place where the item is already counted cannot be picked', pickBtn('Vinegar shelf').disabled&&/counted here already/.test(pickBtn('Vinegar shelf').textContent));
      byId('pickModal').click();   // the backdrop
      ok('move: tapping the backdrop closes it, writing nothing', !shown('pickModal')&&writes().length===2);
    });
  }

  if(H.scen==='remove'){
    unlock();
    step(function(){
      H.confirmReturn=false;
      btn(rowNamed('Dry storage','Apple cider vinegar'),'Remove').click();
      ok('remove: asks first', H.confirmMsgs.length===1&&/Vinegar shelf/.test(H.confirmMsgs[0]), H.confirmMsgs[0]);
      ok('remove: Cancel writes nothing', writes().length===0);
      H.confirmReturn=true;
      btn(rowNamed('Dry storage','Apple cider vinegar'),'Remove').click();
      var w=writes();
      ok('remove: in a second place, one write retires just this row', w.length===1&&w[0].m==='PATCH'&&w[0].u.indexOf('inventory_items?id=eq.202')>-1&&JSON.stringify(w[0].body)==='{"active":false}', JSON.stringify(w));
    });
    tick();tick();
    step(function(){
      ok('remove: ...and it is still counted on the vinegar shelf', !rowNamed('Dry storage','Apple cider vinegar')&&!!rowNamed('Vinegar shelf','Apple cider vinegar'));
      btn(rowNamed('Vegetable cooler','Cilantro'),'Remove').click();
      ok('remove: in its last place, the question says where it goes', /Left off on purpose/.test(H.confirmMsgs[H.confirmMsgs.length-1]), H.confirmMsgs[H.confirmMsgs.length-1]);
    });
    tick();tick();
    step(function(){
      var w=writes().slice(1);
      ok('remove: recorded as left off FIRST, then removed - never in neither', w.length===2&&w[0].m==='POST'&&w[0].t==='inventory_left_off'&&
         JSON.stringify(w[0].body)==='{"location":"Tempest","order_item_id":171}'&&w[1].m==='PATCH'&&w[1].u.indexOf('inventory_items?id=eq.102')>-1, JSON.stringify(w));
    });
    tick();
    step(function(){
      ok('remove: it leaves the count', !rowNamed('Vegetable cooler','Cilantro'));
      ok('remove: ...is not "new"', names('New on the order guide').indexOf('Cilantro')<0);
      byId('leftOffBtn').click();
    });
    step(function(){
      ok('remove: ...and can be found in the left-off list', names('Left off on purpose').indexOf('Cilantro')>-1, JSON.stringify(names('Left off on purpose')));
      H.nextWrite.push('e500');
      btn(rowNamed('Vegetable cooler','Long unit thing'),'Remove').click();
    });
    tick();tick();
    step(function(){
      var w=writes().slice(3);
      ok('remove: if left off could not be recorded, it is NOT removed', w.length===1&&w[0].t==='inventory_left_off', JSON.stringify(w));
      ok('remove: ...it is still counted, and the toast says it failed', !!rowNamed('Vegetable cooler','Long unit thing')&&toastIsError(), toast());
    });
  }

  if(H.scen==='newitems'){
    unlock();
    step(function(){ btn(rowNamed('New on the order guide','Brand new thing'),'Add').click(); });
    step(function(){
      ok('newitems: Add opens the picker, titled to count it', shown('pickModal')&&/^Count Brand new thing in/.test(byId('pickTitle').textContent), byId('pickTitle').textContent);
      ok('newitems: ...with no Move/Also toggle', byId('pickToggle').style.display==='none');
      ok('newitems: ...every place open', all('#pickList .stock-pick').every(function(b){return !b.disabled;}));
      pickBtn('Line').click();
    });
    step(function(){
      var w=writes();
      ok('newitems: one write - a count row in that place', w.length===1&&w[0].m==='POST'&&w[0].t==='inventory_items'&&JSON.stringify(w[0].body)==='{"location":"Tempest","order_item_id":500,"place_id":10,"sort_order":10}', JSON.stringify(w));
    });
    tick();
    step(function(){
      ok('newitems: it leaves the new list and joins the place', names('New on the order guide').indexOf('Brand new thing')<0&&names('Line').indexOf('Brand new thing')>-1);
      ok('newitems: the summary grows by one', byId('sheetSummary').textContent==='10 items · 4 places', byId('sheetSummary').textContent);
      btn(rowNamed('New on the order guide','Another new one'),"Don’t count").click();
    });
    step(function(){
      var w=writes().slice(1);
      ok('newitems: Don’t count is one left-off write', w.length===1&&w[0].m==='POST'&&w[0].t==='inventory_left_off'&&JSON.stringify(w[0].body)==='{"location":"Tempest","order_item_id":501}', JSON.stringify(w));
    });
    tick();
    step(function(){
      ok('newitems: nothing new now, and it says so', rowsUnder('New on the order guide').length===0&&/Nothing new/.test(body()));
      byId('leftOffBtn').click();
    });
    step(function(){
      ok('newitems: ...it is in the left-off list instead', names('Left off on purpose').indexOf('Another new one')>-1);
      btn(rowNamed('Left off on purpose','Paper towel'),'Count it').click();
    });
    step(function(){
      ok('newitems: Count it opens the picker', shown('pickModal')&&/^Count Paper towel in/.test(byId('pickTitle').textContent));
      pickBtn('Dry storage').click();
    });
    tick();tick();
    step(function(){
      var w=writes().slice(2);
      ok('newitems: Count it adds the count row FIRST, then undoes the left-off decision', w.length===2&&w[0].m==='POST'&&w[0].t==='inventory_items'&&
         w[1].m==='PATCH'&&w[1].u.indexOf('inventory_left_off?id=eq.1')>-1&&JSON.stringify(w[1].body)==='{"active":false}', JSON.stringify(w));
    });
    tick();
    step(function(){
      ok('newitems: Paper towel is counted in Dry storage, and off the left-off list', !!rowNamed('Dry storage','Paper towel')&&names('Left off on purpose').indexOf('Paper towel')<0);
      H.mark=writes().length;
      H.nextWrite.push('e500');   // the count row cannot be written
      btn(rowNamed('Left off on purpose','Staff coffee'),'Count it').click();
    });
    step(function(){ pickBtn('Dry storage').click(); });
    tick();tick();
    step(function(){
      var w=writes().slice(H.mark);
      ok('newitems: if Count it cannot add the count row, the left-off decision is NOT undone', w.length===1&&w[0].t==='inventory_items'&&row('inventory_left_off',2).active===true, JSON.stringify(w));
      ok('newitems: ...so Staff coffee is still left off, not in neither', names('Left off on purpose').indexOf('Staff coffee')>-1&&toastIsError());
    });
  }

  if(H.scen==='places'){
    unlock();
    step(function(){ document.querySelector('.mgr-add-btn').click(); });
    step(function(){
      var rows=all('#placesList .stock-prow');
      ok('places: listed in walking order, with item counts', rows.length===4&&/Vegetable cooler/.test(rows[0].textContent)&&/4 items/.test(rows[0].textContent)&&/Line/.test(rows[3].textContent)&&/0 items/.test(rows[3].textContent));
      ok('places: a retired place is not listed', byId('placesList').textContent.indexOf('Old walk-in')<0);
      ok('places: the first cannot go up, the last cannot go down', btn(rows[0],'▲').disabled&&btn(rows[3],'▼').disabled);
      ok('places: a place with items cannot be retired, and says why', btn(rows[0],'Retire').disabled&&/Move its items out/.test(rows[0].textContent));
      H.confirmReturn=true;
      retirePlace(1);   // as a stale or tampered button would
      ok('places: ...and the page itself refuses, even if the button were live', writes().length===0&&H.confirmMsgs.length===0);
      ok('places: an empty place can be', !btn(rows[3],'Retire').disabled);
      var off=[btn(rows[0],'▲'),btn(rows[0],'Retire'),btn(rows[3],'▼')],on=[btn(rows[1],'▲'),btn(rows[3],'Retire')];
      ok('places: a button that cannot be used looks it (dashed, faint) - not just inert',
         off.every(function(b){var c=getComputedStyle(b);return c.borderTopStyle==='dashed'&&c.color==='rgb(169, 167, 160)';})
         &&on.every(function(b){return getComputedStyle(b).borderTopStyle==='solid';}),
         off.concat(on).map(function(b){var c=getComputedStyle(b);return b.textContent+':'+c.borderTopStyle+'/'+c.color;}).join(' '));
      var m=document.querySelector('#placesModal .modal'),wide=all('#placesModal .modal *').filter(function(e){return e.getBoundingClientRect().right>m.getBoundingClientRect().right-1;});
      ok('places: nothing in the list pokes out of the modal', m.scrollWidth<=m.clientWidth&&wide.length===0, wide.map(function(e){return e.className||e.tagName;}).join(','));
      ok('places: opening it writes nothing', writes().length===0);
      btn(rows[0],'▼').click();
    });
    step(function(){
      var w=writes(),by={};H.mark=w.length;w.forEach(function(r){by[r.u.split('id=eq.')[1]]=r.body;});
      ok('places: ▼ renumbers the places, saving only the changed ones', w.length>=2&&w.every(function(r){return r.m==='PATCH'&&r.t==='inventory_places';})&&by['6']&&by['6'].sort_order===10&&by['1']&&by['1'].sort_order===20, JSON.stringify(w));
    });
    tick();
    step(function(){
      ok('places: the sheet follows the new order', placeHeads()[0]==='Dry storage'&&placeHeads()[1]==='Vegetable cooler', JSON.stringify(placeHeads()));
      ok('places: ...and so does the open list', /Dry storage/.test(all('#placesList .stock-prow')[0].textContent));
      btn(all('#placesList .stock-prow')[0],'Rename').click();
    });
    step(function(){
      ok('places: Rename opens with the name filled in', shown('nameModal')&&byId('nameInput').value==='Dry storage');
      byId('nameInput').value='  vinegar   SHELF ';
      byId('nameSaveBtn').click();
      ok('places: a name already in use is refused before any write (any case, any spacing)', byId('nameErr').classList.contains('show')&&/already a place called Vinegar shelf/.test(byId('nameErr').textContent)&&writes().length===H.mark, byId('nameErr').textContent);
      byId('nameInput').value='   ';byId('nameSaveBtn').click();
      ok('places: a blank name is refused', /Give the place a name/.test(byId('nameErr').textContent)&&writes().length===H.mark);
      byId('nameInput').value='Dry   store';byId('nameSaveBtn').click();
    });
    step(function(){
      var w=writes().slice(H.mark);H.mark=writes().length;
      ok('places: rename is one write, spaces tidied', w.length===1&&w[0].m==='PATCH'&&w[0].u.indexOf('inventory_places?id=eq.6')>-1&&JSON.stringify(w[0].body)==='{"label":"Dry store"}', JSON.stringify(w));
    });
    tick();
    step(function(){
      ok('places: the sheet shows the new name', heads().indexOf('Dry store')>-1&&heads().indexOf('Dry storage')<0);
      document.querySelector('#placesModal .modal-btn.save').click();   // + New place
    });
    step(function(){
      ok('places: + New place opens an empty name box', shown('nameModal')&&byId('nameInput').value==='');
      byId('nameInput').value='Old walk-in';byId('nameSaveBtn').click();
    });
    step(function(){
      ok('places: a retired place’s name comes back as a plain message, the box stays open', shown('nameModal')&&/retired place/.test(byId('nameErr').textContent), byId('nameErr').textContent);
      byId('nameInput').value='Walk-in freezer';byId('nameSaveBtn').click();
    });
    step(function(){
      var w=writes().slice(H.mark);H.mark=writes().length;
      ok('places: the refused name and the new place are one POST each', w.length===2&&w.every(function(r){return r.m==='POST'&&r.t==='inventory_places';}), JSON.stringify(w));
      ok('places: a new place goes to the end of the walk (after the last ACTIVE place)', JSON.stringify(w[1].body)==='{"location":"Tempest","label":"Walk-in freezer","sort_order":50}', JSON.stringify(w[1]&&w[1].body));
    });
    tick();
    step(function(){
      ok('places: the new place is on the sheet, last, empty', placeHeads()[placeHeads().length-1]==='Walk-in freezer'&&rowsUnder('Walk-in freezer').length===0, JSON.stringify(placeHeads()));
      H.confirmReturn=false;
      var lineRow=all('#placesList .stock-prow').filter(function(r){return /Line/.test(r.textContent);})[0];
      btn(lineRow,'Retire').click();
      ok('places: Retire asks first, and Cancel writes nothing', /Retire Line/.test(H.confirmMsgs[H.confirmMsgs.length-1])&&writes().length===H.mark, writes().length);
      H.confirmReturn=true;
      btn(lineRow,'Retire').click();
    });
    step(function(){
      var w=writes().slice(-1)[0];
      ok('places: Retire is one write', w.m==='PATCH'&&w.u.indexOf('inventory_places?id=eq.10')>-1&&JSON.stringify(w.body)==='{"active":false}', JSON.stringify(w));
    });
    tick();
    step(function(){
      ok('places: a retired place leaves the sheet', placeHeads().indexOf('Line')<0);
    });
  }

  if(H.scen==='busy'){
    unlock();
    step(function(){
      H.nextWrite.push('defer');
      btn(rowNamed('Vegetable cooler','Ginger'),'Move').click();
    });
    step(function(){ pickBtn('Line').click(); });
    step(function(){
      ok('busy: the write is in flight', writes().length===1&&H.deferredCount()===1);
      btn(rowNamed('Dry storage','Mayo'),'Move').click();
      btn(rowNamed('Dry storage','Mayo'),'Remove').click();
      btn(rowNamed('New on the order guide','Brand new thing'),"Don’t count").click();
      document.querySelector('.mgr-add-btn').click();
      ok('busy: nothing else can start a write meanwhile', writes().length===1&&!shown('pickModal')&&!shown('placesModal'), writes().length);
      ok('busy: ...and it says why', /Still saving/.test(toast()), toast());
      ok('busy: ...and drag is locked', all('.stock-place-body').every(function(l){return Sortable.get(l).options.disabled===true;}));
      H.releaseDeferred();
    });
    tick();
    step(function(){
      ok('busy: once saved, controls work again', all('.stock-place-body').every(function(l){return Sortable.get(l).options.disabled===false;}));
      btn(rowNamed('Dry storage','Mayo'),'Move').click();
      ok('busy: ...the picker opens', shown('pickModal'));
    });
  }

  if(H.scen==='lost'){
    unlock();
    step(function(){
      H.nextWrite.push('lost');   // the table takes it; the answer never comes
      btn(rowNamed('Vegetable cooler','Ginger'),'Move').click();
    });
    step(function(){ pickBtn('Line').click(); });
    tick();tick();
    step(function(){
      ok('lost: no answer is not reported as saved', toastIsError()&&/No answer/.test(toast()), toast());
      ok('lost: ...the re-read shows it did land', !!rowNamed('Line','Ginger')&&!rowNamed('Vegetable cooler','Ginger'));
      H.nextWrite.push('drop');   // lost before the table
      btn(rowNamed('Dry storage','Mayo'),'Move').click();
    });
    step(function(){ pickBtn('Line').click(); });
    tick();tick();
    step(function(){
      ok('lost: ...and when it did not land, the re-read shows that too', !!rowNamed('Dry storage','Mayo')&&!rowNamed('Line','Mayo')&&/No answer/.test(toast()));
    });
  }


  /* ============================== slice 3 ============================== */
  function inputIn(r,part){return r.querySelector('.stock-input[data-part="'+part+'"]');}
  function typeIn(r,part,v){var i=inputIn(r,part);i.value=v;i.dispatchEvent(new Event('input',{bubbles:true}));}
  function leave(r,part){inputIn(r,part).dispatchEvent(new Event('change',{bubbles:true}));}
  function state(r){var e=r&&r.querySelector('.stock-state');return e?e.textContent:'';}
  function lineWrites(){return writes().filter(function(w){return w.t==='inventory_count_lines';});}
  function lastBody(){var w=lineWrites();var b=w.length?JSON.parse(JSON.stringify(w[w.length-1].body)):null;if(b)delete b.updated_at;return JSON.stringify(b);}
  function serverLines(item){return T.inventory_count_lines.filter(function(l){return l.count_id===7&&(item==null||l.inventory_item_id===item);});}
  function pickName(n){var s=byId('countedBy');s.value=n;s.dispatchEvent(new Event('change',{bubbles:true}));}
  function head(label){var h=all('.stock-place-hd').filter(function(h){return h.querySelector('.cat-label').textContent===label;})[0];return h?h.querySelector('.stock-place-n').textContent:'';}
  function mlabel(iso){var mn=['January','February','March','April','May','June','July','August','September','October','November','December'],p=iso.split('-');return mn[parseInt(p[1],10)-1]+' '+p[0];}
  function body3(item,full,loose,sq,su,by){return JSON.stringify({location:'Tempest',count_id:7,inventory_item_id:item,full_qty:full,loose_qty:loose,pack_qty_snap:sq,pack_unit_snap:su,counted_by:by});}

  if(H.scen==='count'){
    step(function(){
      var lr=reads('inventory_count_lines')[0]||{u:''};
      ok('count: the open count’s lines are read, once, scoped to it', reads('inventory_count_lines').length===1&&/count_id=eq\.7/.test(lr.u)&&/location=eq\.Tempest/.test(lr.u), lr.u);
      ok('count: six reads in all, none of them a price', H.reqs.length===6&&H.reqs.every(function(r){return r.u.indexOf('price')<0;}), H.reqs.length);
      ok('count: the title names the month', byId('sheetTitle').textContent==='October 2026 count', byId('sheetTitle').textContent);
      ok('count: the summary counts saved rows', byId('sheetSummary').textContent==='2 of 10 counted', byId('sheetSummary').textContent);
      ok('count: each place says how many are counted', head('Vegetable cooler')==='1 of 4 counted'&&head('Dry storage')==='1 of 5 counted'&&head('Line')==='0 of 0 counted', head('Vegetable cooler')+' / '+head('Dry storage'));
      var opts=all('#countedBy option').map(function(o){return o.textContent;});
      ok('count: the name list is the active staff, once each', JSON.stringify(opts)===JSON.stringify(['Pick your name…','Maria','Jose']), JSON.stringify(opts));
      ok('count: the name box computes to 16px (#135)', parseFloat(getComputedStyle(byId('countedBy')).fontSize)>=16, getComputedStyle(byId('countedBy')).fontSize);
      ok('count: no box can be typed in before a name is picked', inputs().every(function(i){return i.disabled;}));
      ok('count: ...and the intro says why', /Pick your name/.test(byId('introBar').textContent));
      var m=rowNamed('Dry storage','Mayo');
      ok('count: a saved count is shown, filled', inputIn(m,'full').value==='3'&&inputIn(m,'full').classList.contains('filled'));
      ok('count: ...with who counted it', state(m)==='✓ Counted by Jose', state(m));
      var gr=rowNamed('Vegetable cooler','Ginger');
      ok('count: a row counted against an old pack keeps that pack’s boxes (40 lb, not today’s 30)', JSON.stringify(units(gr))==='["× 40 lb","lb"]'&&inputIn(gr,'full').value==='1'&&inputIn(gr,'loose').value==='4', JSON.stringify(units(gr)));
      var z=rowNamed('Dry storage','Zero pack');
      ok('count: a cleared line shows as not counted - empty, no tick', inputIn(z,'full').value===''&&state(z)==='');
      ok('count: nothing written on load', writes().length===0);
      pickName('Maria');
    });
    step(function(){
      ok('count: picking a name shows it, with Change', byId('whoName').textContent==='Maria'&&visible(byId('whoName'))&&visible(byId('whoChange'))&&!visible(byId('countedBy'))&&byId('whoLabel').textContent==='Counting as');
      var kept='';try{kept=sessionStorage.getItem('boxkitchen_inv_who');}catch(e){}
      ok('count: ...and this page remembers it until it is closed', kept==='Maria', kept);
      ok('count: the boxes open', inputs().every(function(i){return !i.disabled;}));
      typeIn(rowNamed('Vegetable cooler','Cilantro'),'full','3');
      ok('count: typing says it is not saved yet, and sends nothing at once', state(rowNamed('Vegetable cooler','Cilantro'))==='Not saved yet'&&writes().length===0);
      return 1400;   // past the pause after typing
    });
    step(function(){
      var w=lineWrites()[0]||{u:'',prefer:''};
      ok('count: a pause after typing saves it - one request', lineWrites().length===1, lineWrites().length);
      ok('count: ...as an upsert on (count, item), so a retry can never add a second line', /on_conflict=count_id,inventory_item_id/.test(w.u)&&/resolution=merge-duplicates/.test(w.prefer)&&w.m==='POST', w.u+' | '+w.prefer);
      ok('count: ...with exactly what was counted, in which units, and by whom', lastBody()===body3(102,3,null,null,'BU','Maria'), lastBody());
      ok('count: ...stamped with a real time', !isNaN(Date.parse((w.body||{}).updated_at)));
      var c=rowNamed('Vegetable cooler','Cilantro');
      ok('count: saved, it shows a tick and the name', state(c)==='✓ Counted by Maria', state(c));
      ok('count: ...and the place and summary move on', head('Vegetable cooler')==='2 of 4 counted'&&byId('sheetSummary').textContent==='3 of 10 counted', head('Vegetable cooler')+' / '+byId('sheetSummary').textContent);
      var g=rowNamed('Vegetable cooler','Ginger');
      typeIn(g,'loose','');typeIn(g,'full','2');leave(g,'full');
    });
    tick();
    step(function(){
      ok('count: leaving a box saves at once; a blank beside a filled box is 0; the old pack is kept', lastBody()===body3(101,2,0,40,'lb','Maria'), lastBody());
      ok('count: ...and the 0 comes back into the empty box', inputIn(rowNamed('Vegetable cooler','Ginger'),'loose').value==='0');
      var l=rowNamed('Vegetable cooler','Long unit thing');typeIn(l,'loose','5');leave(l,'loose');
    });
    tick();
    step(function(){
      ok('count: loose only - the Full box is 0, against today’s 12-bunch pack', lastBody()===body3(103,0,5,12,'bunch','Maria'), lastBody());
      var t=rowNamed('Vegetable cooler','Tom <b>bold</b> & co');typeIn(t,'full','0');leave(t,'full');
    });
    tick();
    step(function(){
      ok('count: 0 is a count, and is saved as one', lastBody()===body3(104,0,null,null,'EA','Maria')&&state(rowNamed('Vegetable cooler','Tom <b>bold</b> & co'))==='✓ Counted by Maria', lastBody());
      H.n=lineWrites().length;
      var b=rowNamed('Dry storage','Blank unit');typeIn(b,'full','2 cs');leave(b,'full');
    });
    tick();
    step(function(){
      var b=rowNamed('Dry storage','Blank unit');
      ok('count: words are refused, in words, and nothing is sent', lineWrites().length===H.n&&/Numbers only/.test(state(b)), state(b));
      typeIn(b,'full','2,5');leave(b,'full');
    });
    tick();
    step(function(){
      ok('count: a comma is read as a decimal point', lastBody()===body3(205,2.5,null,null,'EA','Maria'), lastBody());
      var m=rowNamed('Dry storage','Mayo');typeIn(m,'full','');leave(m,'full');
    });
    tick();
    step(function(){
      var m=rowNamed('Dry storage','Mayo');
      ok('count: clearing a saved count sends blanks - not counted, nothing deleted', lastBody()===body3(201,null,null,1,'Each','Maria')&&serverLines(201).length===1, lastBody());
      ok('count: ...and the row shows as not counted again', state(m)===''&&!inputIn(m,'full').classList.contains('filled'));
      ok('count: ...and the place count drops', head('Dry storage')==='1 of 5 counted', head('Dry storage'));
      H.n=lineWrites().length;
      var o=rowNamed('Dry storage','Old flour');typeIn(o,'full','1');typeIn(o,'full','');leave(o,'full');
      var c=rowNamed('Vegetable cooler','Cilantro');typeIn(c,'full','3');leave(c,'full');
    });
    tick();
    step(function(){
      ok('count: typed and erased before saving sends nothing; retyping the saved value sends nothing', lineWrites().length===H.n, lineWrites().length-H.n);
      var ids={},dup=false;serverLines().forEach(function(l){if(ids[l.inventory_item_id])dup=true;ids[l.inventory_item_id]=1;});
      ok('count: the table holds one line per row - never two', !dup&&serverLines().length===7, serverLines().length);
      ok('count: no write to anything but the count lines', writes().every(function(w){return w.t==='inventory_count_lines';}));
      H.n=lineWrites().length;
      typeIn(rowNamed('Dry storage','Zero pack'),'full','7');   // typed, not saved yet...
      loadAll({quiet:true,force:true});                           // ...and the sheet refreshes underneath it
    });
    tick();tick();
    step(function(){
      var z=rowNamed('Dry storage','Zero pack');
      ok('count: a refresh never wipes a number typed but not yet saved', inputIn(z,'full').value==='7'&&state(z)==='Not saved yet', inputIn(z,'full').value+' / '+state(z));
      return 1400;
    });
    step(function(){
      ok('count: ...and it still saves after the refresh', lastBody()===body3(204,7,null,null,'CS','Maria'), lastBody());
    });
    unlock();
    step(function(){
      var bar=document.querySelector('.stock-countbar');
      ok('count: once anything is counted, the month cannot be changed', !!bar&&!/Wrong month/.test(bar.textContent), bar&&bar.textContent);
      H.n=writes().length;H.confirmReturn=true;
      switchMonth('2026-09-01');
      ok('count: ...and the page itself refuses, even if asked', writes().length===H.n);
    });
  }

  if(H.scen==='inflight'){
    step(function(){ pickName('Maria'); });
    step(function(){
      H.nextWrite.push('defer');
      var c=rowNamed('Vegetable cooler','Cilantro');typeIn(c,'full','1');leave(c,'full');
    });
    tick();
    step(function(){
      var c=rowNamed('Vegetable cooler','Cilantro');
      ok('inflight: the first save is on its way', lineWrites().length===1&&state(c)==='Saving…', state(c));
      typeIn(c,'full','12');leave(c,'full');
    });
    tick();
    step(function(){
      ok('inflight: an edit while it is saving does not send a second request alongside it', lineWrites().length===1, lineWrites().length);
      ok('inflight: ...and the row says the edit is not saved yet', state(rowNamed('Vegetable cooler','Cilantro'))==='Not saved yet', state(rowNamed('Vegetable cooler','Cilantro')));
      H.releaseDeferred();
    });
    tick();tick();
    step(function(){
      ok('inflight: when the first lands, the newer value is sent', lineWrites().length===2&&lineWrites()[1].body.full_qty===12, JSON.stringify(lineWrites().map(function(w){return w.body.full_qty;})));
      ok('inflight: the table ends with the newer value, on one line', serverLines(102).length===1&&serverLines(102)[0].full_qty===12);
      ok('inflight: and the row says it is saved', state(rowNamed('Vegetable cooler','Cilantro'))==='✓ Counted by Maria');
    });
  }

  if(H.scen==='countlost'){
    step(function(){ pickName('Maria'); });
    step(function(){
      H.nextWrite.push('lost');   // the table takes it; the answer never comes
      var c=rowNamed('Vegetable cooler','Cilantro');typeIn(c,'full','3');leave(c,'full');
    });
    tick();
    step(function(){
      var c=rowNamed('Vegetable cooler','Cilantro'),b=c.querySelector('button.stock-state');
      ok('countlost: no answer is not a tick - it says so, and how to fix it', !!b&&/Not saved — no answer from the server\. Tap to try again/.test(b.textContent), state(c));
      ok('countlost: ...in the error colour, as a 44px button', !!b&&getComputedStyle(b).color==='rgb(180, 35, 24)'&&b.getBoundingClientRect().height>=44);
      ok('countlost: ...and it is not counted in the summary, though the table has it', byId('sheetSummary').textContent==='2 of 10 counted'&&serverLines(102).length===1);
      ok('countlost: the typed value stays in the box', inputIn(c,'full').value==='3');
      b.click();
    });
    tick();
    step(function(){
      ok('countlost: tapping retries, and the table still has ONE line for it', lineWrites().length===2&&serverLines(102).length===1&&serverLines(102)[0].full_qty===3);
      ok('countlost: ...now ticked', state(rowNamed('Vegetable cooler','Cilantro'))==='✓ Counted by Maria');
      H.nextWrite.push('drop');   // lost before the table
      var t=rowNamed('Vegetable cooler','Tom <b>bold</b> & co');typeIn(t,'full','2');leave(t,'full');
    });
    tick();
    step(function(){
      ok('countlost: lost before it landed - not saved, nothing in the table', /Not saved/.test(state(rowNamed('Vegetable cooler','Tom <b>bold</b> & co')))&&serverLines(104).length===0);
      rowNamed('Vegetable cooler','Tom <b>bold</b> & co').querySelector('button.stock-state').click();
    });
    tick();
    step(function(){
      ok('countlost: the retry saves it, once', serverLines(104).length===1&&serverLines(104)[0].full_qty===2&&state(rowNamed('Vegetable cooler','Tom <b>bold</b> & co'))==='✓ Counted by Maria');
      H.nextWrite.push('empty');   // a success code, but no row in the answer
      var l=rowNamed('Vegetable cooler','Long unit thing');typeIn(l,'full','1');leave(l,'full');
    });
    tick();
    step(function(){
      var st=state(rowNamed('Vegetable cooler','Long unit thing'));
      ok('countlost: a success code with no row in it is not a tick - only a confirmed row is', /Not saved — the server did not confirm it/.test(st), st);
    });
  }

  if(H.scen==='countclosed'){
    step(function(){ pickName('Maria'); });
    step(function(){
      T.inventory_counts[0].status='closed';   // closed on another device meanwhile
      var c=rowNamed('Vegetable cooler','Cilantro');typeIn(c,'full','3');leave(c,'full');
    });
    tick();tick();tick();
    step(function(){
      ok('countclosed: the table refuses a line for a closed count', serverLines(102).length===0&&lineWrites().length===1);
      ok('countclosed: the page re-reads and stops offering boxes', byId('sheetTitle').textContent==='Count sheet'&&inputs().every(function(i){return i.disabled;})&&byId('nameBar').style.display==='none', byId('sheetTitle').textContent);
      ok('countclosed: ...and says no count is open', /No count is open yet/.test(byId('introBar').textContent));
    });
  }

  if(H.scen==='who'){
    step(function(){ pickName('Maria'); });
    step(function(){
      typeIn(rowNamed('Vegetable cooler','Cilantro'),'full','3');   // typed, not yet saved
      byId('whoChange').click();
      ok('who: Change sends what was typed, under the name it was typed under', lineWrites().length===1&&lineWrites()[0].body.counted_by==='Maria', JSON.stringify(lineWrites().map(function(w){return w.body.counted_by;})));
      var kept='x';try{kept=sessionStorage.getItem('boxkitchen_inv_who');}catch(e){}
      ok('who: ...then forgets the name', kept===null&&visible(byId('countedBy'))&&!visible(byId('whoName')), kept);
      ok('who: ...and closes the boxes until a name is picked', inputs().every(function(i){return i.disabled;}));
      pickName('Jose');
    });
    tick();
    step(function(){
      var t=rowNamed('Vegetable cooler','Tom <b>bold</b> & co');typeIn(t,'full','1');leave(t,'full');
    });
    tick();
    step(function(){
      ok('who: the next person’s counts carry their name', lastBody()===body3(104,1,null,null,'EA','Jose'), lastBody());
      ok('who: the earlier row still says who counted it', state(rowNamed('Vegetable cooler','Cilantro'))==='✓ Counted by Maria', state(rowNamed('Vegetable cooler','Cilantro')));
    });
  }

  if(H.scen==='start'){
    var TM=H.fx.thisMonth,LM=H.fx.lastMonth;
    unlock();
    step(function(){
      var bar=document.querySelector('.stock-countbar');
      ok('start: manager mode says no count is open', !!bar&&/No count is open/.test(bar.textContent));
      ok('start: ...and offers this month and last month', !!btn(bar,'Start '+mlabel(TM))&&!!btn(bar,'Start '+mlabel(LM)), bar&&bar.textContent);
      ok('start: the name bar shows in manager mode', byId('nameBar').style.display!=='none');
      btn(bar,'Start '+mlabel(TM)).click();
      ok('start: not without a name', writes().length===0&&/Pick your name first/.test(toast()), toast());
      pickName('Maria');
    });
    step(function(){
      btn(document.querySelector('.stock-countbar'),'Start '+mlabel(LM)).click();
      ok('start: it asks first, naming the month', /Start the .* count\?/.test(H.confirmMsgs[H.confirmMsgs.length-1])&&H.confirmMsgs[H.confirmMsgs.length-1].indexOf(mlabel(LM))>-1, H.confirmMsgs[H.confirmMsgs.length-1]);
    });
    tick();tick();
    step(function(){
      var w=writes();
      ok('start: a month that already has a count is refused by the table, and said so', w.length===1&&w[0].t==='inventory_counts'&&JSON.stringify(w[0].body)===JSON.stringify({location:'Tempest',period:LM})&&/There is already/.test(toast())&&toastIsError(), JSON.stringify(w));
      btn(document.querySelector('.stock-countbar'),'Start '+mlabel(TM)).click();
    });
    tick();tick();tick();
    step(function(){
      var w=writes().slice(1);
      ok('start: a count is one write, then the log says who started it', w.length===2&&w[0].t==='inventory_counts'&&JSON.stringify(w[0].body)===JSON.stringify({location:'Tempest',period:TM})&&
         w[1].t==='inventory_count_log'&&w[1].body.action==='start'&&w[1].body.by_name==='Maria'&&w[1].body.count_id===T.inventory_counts[T.inventory_counts.length-1].id, JSON.stringify(w.map(function(x){return x.body;})));
      var bar=document.querySelector('.stock-countbar');
      ok('start: the bar now says it is open, and nothing is counted', !!bar&&/count is open — 0 of 10 counted/.test(bar.textContent), bar&&bar.textContent);
      ok('start: no Start buttons while one is open', !btn(bar,'Start '+mlabel(TM))&&!btn(bar,'Start '+mlabel(LM)));
      ok('start: the title names the month', byId('sheetTitle').textContent===mlabel(TM)+' count', byId('sheetTitle').textContent);
      var wm=all('.stock-countbar button').filter(function(b){return /Wrong month/.test(b.textContent);})[0];
      ok('start: before anything is counted, the month can be changed', !!wm&&wm.textContent.indexOf(mlabel(LM))>-1);
      if(wm)wm.click();
    });
    tick();tick();
    step(function(){
      var w=writes().slice(3);
      ok('start: changing to a month that already has a count is refused, and said so', w.length===1&&w[0].m==='PATCH'&&JSON.stringify(w[0].body)===JSON.stringify({period:LM})&&/There is already/.test(toast()), JSON.stringify(w));
      ok('start: ...and the count keeps its month', byId('sheetTitle').textContent===mlabel(TM)+' count');
      byId('mgrSwitch').click();
    });
    step(function(){
      ok('start: out of manager mode, staff can count straight away', inputs().length>0&&inputs().every(function(i){return !i.disabled;})&&byId('whoName').textContent==='Maria');
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
    import datetime
    today = datetime.date.today()
    last = (today.replace(day=1) - datetime.timedelta(days=1)).replace(day=1)
    fixtures = {"places": PLACES, "items": ITEMS, "orphan": ORPHAN, "leftOff": LEFT_OFF,
                "guide": GUIDE, "costs": COSTS, "staff": STAFF, "openCount": OPEN_COUNT,
                "lines": LINES, "countScens": COUNT_SCENARIOS,
                "thisMonth": today.replace(day=1).isoformat(), "lastMonth": last.isoformat()}
    src = src.replace(marker, HARNESS.replace("__FIXTURES__", json.dumps(fixtures)) + marker, 1)

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
    scens = os.environ['ONLY'].split(',') if os.environ.get('ONLY') else SCENARIOS
    with tempfile.TemporaryDirectory() as td:
        path = os.path.join(td, "inventory_under_test.html")
        with open(path, "w", encoding="utf-8") as f:
            f.write(page)
        # the page links assets/kitchen.css and vendor/sortablejs relatively;
        # without these copies every scenario runs unstyled and undraggable
        shutil.copytree(os.path.join(ROOT, "assets"), os.path.join(td, "assets"))
        shutil.copytree(os.path.join(ROOT, "vendor"), os.path.join(td, "vendor"))
        for scen in scens:
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
        print("\nsee docs/inventory-guide.md, Slices 1 and 2")
        return 1
    print("inventory guard: clean (%d assertions, %d scenarios, %s)" % (total, len(scens), PAGE))
    return 0


if __name__ == "__main__":
    sys.exit(main())
