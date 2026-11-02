#!/usr/bin/env python3
"""
Behaviour guard for the Menu Builder (tempest_menu_builder.html), Slice 1.

Slice 1's promises (docs/menu-builder.md): the whole page is behind the
manager PIN; the menu view lists dishes Ready, then Testing, then Idea, by
name, with dropped dishes hidden until "Show dropped"; a dish can be made,
renamed, moved through every status, dropped and restored; every check runs
before any write; one write at a time; a lost answer is looked up by id before
a retry, and a retry re-sends the SAME page-made id as an upsert, so it can
never make a second dish; nothing is ever deleted; every box renders at 16px.

None of that can be checked against the live database without writing to it,
so - as check_inventory.py does - load the REAL page, neutralise the
site-password redirect, replace XMLHttpRequest with a stateful in-memory
menu_drafts BEFORE the page script parses, drive it in headless Chrome, and
assert on the DOM and on every request.

    python3 scripts/check_menu_builder.py        # ONLY=create,lost to run a few

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
PAGE = "tempest_menu_builder.html"
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

SCENARIOS = ("gate", "empty", "loadfail", "list", "create", "createlost",
             "createdrop", "createblind", "edit", "validate", "drop", "restore",
             "unsaved", "busy", "editlost", "editdrop", "fonts")


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


def d(i, name, status, price=None, plates=1, low=26, high=28, notes=None, loc="Tempest"):
    return {"id": "00000000-0000-4000-8000-%012d" % i, "location": loc, "name": name,
            "status": status, "makes_plates": plates, "menu_price": price,
            "target_low": low, "target_high": high, "notes": notes,
            "created_at": "2026-11-02T10:00:00Z", "updated_at": "2026-11-02T10:00:00Z"}

# Every sort rule is here: two Ready, two Testing, two Idea (names out of
# order, one lower-case), two dropped, and one from another location.
DRAFTS = [
    d(1, "Pork Belly Bao", "idea"),
    d(2, "Winter Squash Melt", "testing", 14),
    d(3, "chicken & Dumpling", "ready", 12),
    d(4, "Apple Galette", "idea", None, 8),
    d(5, "Beet Salad", "testing", 11.5),
    d(6, "Zucchini Fritter", "ready", 9),
    d(7, "Old Meatloaf", "dropped", 13),
    d(8, "Fish <b>Taco</b>", "dropped"),
    d(9, "Showdown Burger", "idea", loc="Showdown"),
]

GATE_RE = re.compile(r"window\.location\.replace\('index\.html'\)")

HARNESS = r"""
<script>
/* ---- test harness: installed BEFORE the page script parses ---- */
(function(){
  var SCEN=(location.hash||'#list').slice(1);
  var FX=__FIXTURES__;
  var reqs=[],deferred=[];
  var T={menu_drafts:(SCEN==='empty'||SCEN==='create'||SCEN==='createlost'||SCEN==='createdrop'||SCEN==='createblind')?[]:FX.drafts};
  if(SCEN!=='gate')sessionStorage.setItem('boxkitchen_mgr','1');else sessionStorage.removeItem('boxkitchen_mgr');
  window.__h={scen:SCEN,reqs:reqs,fails:[],log:[],tables:T,confirmMsgs:[],confirmReturn:true,
    next:[],        /* read fates, in order: 'err' no answer */
    nextWrite:[]};  /* write fates: 'e500' nothing written; 'lost' written, no answer;
                       'drop' not written, no answer; 'defer' answer held */
  if(SCEN==='loadfail')window.__h.next.push('err');
  function clone(x){return JSON.parse(JSON.stringify(x));}
  function table(u){var m=u.match(/\/rest\/v1\/([a-z_]+)/);return m?m[1]:'';}
  function query(u){var q={},s=u.split('?')[1]||'';s.split('&').forEach(function(kv){var i=kv.indexOf('=');if(i>0)q[kv.slice(0,i)]=decodeURIComponent(kv.slice(i+1));});return q;}
  function find(id){for(var i=0;i<T.menu_drafts.length;i++)if(T.menu_drafts[i].id===id)return T.menu_drafts[i];return null;}
  /* the table's own checks, as Postgres would answer them (400 = refused) */
  function valid(r){
    if(typeof r.name!=='string'||!r.name.trim())return false;
    if(['idea','testing','ready','dropped'].indexOf(r.status)<0)return false;
    if(!(r.makes_plates>0))return false;
    if(r.menu_price!=null&&!(r.menu_price>0))return false;
    if(!(r.target_low>0&&r.target_low<=r.target_high&&r.target_high<100))return false;
    return true;
  }
  var DEF={location:'Tempest',status:'idea',makes_plates:1,menu_price:null,target_low:26,target_high:28,notes:null};
  function write(m,q,body,prefer){
    if(m==='DELETE')return {status:403,text:'{"message":"permission denied for table menu_drafts"}'};
    if(m==='POST'){
      var hit=body&&find(body.id);
      if(hit){
        if(q.on_conflict!=='id'||prefer.indexOf('resolution=merge-duplicates')<0)return {status:409,text:'{"code":"23505"}'};
        var nx=clone(hit);for(var k in body)nx[k]=body[k];if(!valid(nx))return {status:400,text:'{"code":"23514"}'};
        for(var k2 in body)hit[k2]=body[k2];hit.updated_at=new Date().toISOString();return {status:201,text:JSON.stringify([clone(hit)])};
      }
      var row=clone(DEF);for(var k3 in body)row[k3]=body[k3];
      if(!row.id)return {status:400,text:'{"message":"harness: the page must name its row"}'};
      row.created_at=row.updated_at=new Date().toISOString();
      if(!valid(row))return {status:400,text:'{"code":"23514"}'};
      T.menu_drafts.push(row);return {status:201,text:JSON.stringify([clone(row)])};
    }
    if(m==='PATCH'){
      var id=(q.id||'').replace(/^eq\./,''),target=find(id);
      if(!target||!q.id)return {status:200,text:'[]'};
      var next=clone(target);for(var k4 in body)next[k4]=body[k4];
      if(!valid(next))return {status:400,text:'{"code":"23514"}'};
      for(var k5 in body)target[k5]=body[k5];
      /* the server's own normalisation: the page must render THIS, not what was typed */
      if(target.notes!=null)target.notes=String(target.notes);
      return {status:200,text:JSON.stringify([clone(target)])};
    }
    return {status:405,text:'{"message":"harness: '+m+' not supported"}'};
  }
  function read(q){
    return T.menu_drafts.filter(function(r){
      if(q.location&&('eq.'+r.location)!==q.location)return false;
      if(q.id&&('eq.'+r.id)!==q.id)return false;
      return true;
    }).map(clone);
  }
  function route(m,u,body,prefer){
    var t=table(u),q=query(u);
    if(t!=='menu_drafts')return {status:403,text:'{"message":"harness: '+t+' is not this page\'s table"}'};
    if(m==='GET'){
      var plan=window.__h.next.shift();
      if(plan==='err')return {err:true};
      return {status:200,text:JSON.stringify(read(q))};
    }
    var fate=window.__h.nextWrite.shift();
    if(fate==='e500')return {status:500,text:'{"message":"boom"}'};
    if(fate==='drop')return {err:true};
    var w=write(m,q,body,prefer);
    if(fate==='lost')return {err:true};
    if(fate==='defer')return {defer:true,res:w};
    return w;
  }
  function Fake(){this.status=0;this.responseText='';this.timeout=0;this._h={};}
  Fake.prototype.open=function(m,u){this._m=m;this._u=u;};
  Fake.prototype.setRequestHeader=function(k,v){this._h[k]=v;};
  Fake.prototype.send=function(b){
    var self=this,parsed=null;if(b){try{parsed=JSON.parse(b);}catch(e){}}
    reqs.push({m:this._m,u:this._u,t:table(this._u),q:query(this._u),body:parsed,timeout:this.timeout,prefer:this._h.Prefer||''});
    var r=route(this._m,this._u,parsed,this._h.Prefer||'');
    var deliver=function(res){if(res.err){if(self.onerror)self.onerror();return;}self.status=res.status;self.responseText=res.text;if(self.onload)self.onload();};
    if(r.defer){deferred.push(function(){deliver(r.res);});return;}
    setTimeout(function(){deliver(r);},0);
  };
  window.XMLHttpRequest=Fake;
  window.__h.releaseDeferred=function(){var x=deferred.slice();deferred.length=0;for(var i=0;i<x.length;i++)x[i]();};
  window.confirm=function(msg){window.__h.confirmMsgs.push(String(msg));return window.__h.confirmReturn;};
})();
</script>
"""

RUNNER = r"""
<script>
(function(){
  var H=window.__h,F=H.fails,T=H.tables;
  function ok(name,cond,extra){if(!cond)F.push(name+(extra!=null?' :: '+extra:''));H.log.push((cond?'PASS ':'FAIL ')+name);}
  function byId(id){return document.getElementById(id);}
  function all(sel,root){return Array.prototype.slice.call((root||document).querySelectorAll(sel));}
  function writes(){return H.reqs.filter(function(r){return r.m!=='GET';});}
  function posts(){return H.reqs.filter(function(r){return r.m==='POST';});}
  function patches(){return H.reqs.filter(function(r){return r.m==='PATCH';});}
  function reads(){return H.reqs.filter(function(r){return r.m==='GET';});}
  function rows(){return all('#listBody .ing-row');}
  function names(){return rows().map(function(r){return r.querySelector('.ing-name').textContent;});}
  function liveNames(){return rows().filter(function(r){return !r.classList.contains('retired');}).map(function(r){return r.querySelector('.ing-name').textContent;});}
  function rowNamed(n){return rows().filter(function(r){return r.querySelector('.ing-name').textContent===n;})[0];}
  function toast(){return byId('toast').textContent;}
  function toastIsError(){return byId('toast').classList.contains('error');}
  function shown(id){return byId(id).classList.contains('show');}
  function err(id){return byId(id).classList.contains('show')?byId(id).textContent:'';}
  function set(id,v){var e=byId(id);e.value=v;e.dispatchEvent(new Event('input',{bubbles:true}));}
  function click(el){if(el)el.click();}
  function statusBtn(s){return all('#dStatus .filter-btn').filter(function(b){return b.getAttribute('data-s')===s;})[0];}
  function activeStatus(){var a=all('#dStatus .filter-btn.active');return a.length===1?a[0].getAttribute('data-s'):'('+a.length+' active)';}
  function trow(name){return T.menu_drafts.filter(function(r){return r.name===name;});}
  var UUID=/^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/;

  var steps=[];function step(fn){steps.push(fn);}
  function run(){
    if(!steps.length){
      /* every scenario: nothing deleted, nothing but menu_drafts touched */
      ok('no DELETE was ever sent',H.reqs.every(function(r){return r.m!=='DELETE';}));
      ok('only menu_drafts was asked',H.reqs.every(function(r){return r.t==='menu_drafts';}),JSON.stringify(H.reqs.map(function(r){return r.t;})));
      ok('no write ever went to another location',writes().every(function(r){return r.m!=='POST'||r.body.location==='Tempest';}));
      ok('every read is scoped to Tempest or to one id',reads().every(function(r){return r.q.location==='eq.Tempest'||/^eq\./.test(r.q.id||'');}),JSON.stringify(reads().map(function(r){return r.u;})));
      var out=document.createElement('div');out.id='harnessResults';
      out.textContent=JSON.stringify({scen:H.scen,fails:F,log:H.log});
      document.body.appendChild(out);return;
    }
    var fn=steps.shift(),wait=0;
    try{wait=fn();}catch(e){F.push('threw in step: '+(e&&e.message));}
    setTimeout(run,typeof wait==='number'?wait:30);
  }
  /* open the New dish modal, type a name, tap Save */
  function create(name){click(byId('newBtn'));set('newName',name);click(byId('newSave'));}

  var S=H.scen;
  if(S==='gate'){
    step(function(){
      ok('gate: the PIN gate shows',!byId('gate').classList.contains('hide'));
      ok('gate: the page is hidden behind it',getComputedStyle(byId('app')).display==='none');
      ok('gate: nothing is loaded before the PIN',H.reqs.length===0,H.reqs.length);
      set('gateInput','0000');submitGate();
    });
    step(function(){
      ok('gate: a wrong PIN is refused',byId('gateErr').classList.contains('show')&&!byId('gate').classList.contains('hide'));
      ok('gate: still nothing loaded',H.reqs.length===0);
      set('gateInput',MANAGER_PIN);submitGate();
    });
    step(function(){
      ok('gate: the right PIN opens the page',byId('gate').classList.contains('hide')&&getComputedStyle(byId('app')).display!=='none');
      ok('gate: the shared manager key is set, so other pages do not ask again',sessionStorage.getItem('boxkitchen_mgr')==='1');
      ok('gate: the PIN value is never stored',JSON.stringify(sessionStorage).indexOf(MANAGER_PIN)<0&&JSON.stringify(localStorage).indexOf(MANAGER_PIN)<0);
    });
  }
  if(S==='empty'){
    step(function(){
      ok('empty: the gate is skipped when the shared key is set',byId('gate').classList.contains('hide'));
      ok('empty: says there are no dishes and how to start one',/No draft dishes yet/.test(byId('listBody').textContent)&&/New dish/.test(byId('listBody').textContent),byId('listBody').textContent);
      ok('empty: count line',byId('countTag').textContent==='0 drafts · target 26–28%',byId('countTag').textContent);
      ok('empty: no Show dropped line',!byId('droppedToggle'));
      ok('empty: read only',writes().length===0);
    });
  }
  if(S==='loadfail'){
    step(function(){
      ok('loadfail: says it could not load, with Retry',/Could not load/.test(byId('listBody').textContent)&&/Retry/.test(byId('listBody').textContent));
      ok('loadfail: does not pretend the list is empty',!/No draft dishes yet/.test(byId('listBody').textContent));
      click(all('#listBody button')[0]);
    });
    step(function(){ok('loadfail: Retry loads the list',rows().length===6,rows().length);});
  }
  if(S==='list'){
    step(function(){
      ok('list: Ready, then Testing, then Idea, by name within each',JSON.stringify(names())===JSON.stringify(
        ['chicken & Dumpling','Zucchini Fritter','Beet Salad','Winter Squash Melt','Apple Galette','Pork Belly Bao']),JSON.stringify(names()));
      ok('list: another location is not shown',names().indexOf('Showdown Burger')<0);
      ok('list: dropped are hidden',names().indexOf('Old Meatloaf')<0);
      ok('list: count line',byId('countTag').textContent==='6 drafts · target 26–28%',byId('countTag').textContent);
      var r=rowNamed('Winter Squash Melt');
      ok('list: status word on the row',r&&r.querySelector('.uc').textContent==='Testing');
      ok('list: price and "costs come later" on the second line',r&&r.querySelector('.ing-pack').textContent==='$14.00 · costs come later',r&&r.querySelector('.ing-pack').textContent);
      ok('list: no price says so',rowNamed('Pork Belly Bao').querySelector('.ing-pack').textContent==='no menu price yet · costs come later');
      ok('list: half dollars print as cents',rowNamed('Beet Salad').querySelector('.ing-pack').textContent.indexOf('$11.50')===0);
      ok('list: no cost number anywhere',!/%\s*·|plate/.test(byId('listBody').textContent));
      ok('list: Show dropped (2)',byId('droppedToggle')&&byId('droppedToggle').textContent==='Show dropped (2)');
      click(byId('droppedToggle'));
    });
    step(function(){
      ok('list: Show dropped reveals them',names().indexOf('Old Meatloaf')>-1&&names().indexOf('Fish <b>Taco</b>')>-1,JSON.stringify(names()));
      ok('list: a name is shown as text, never as markup',!document.querySelector('#listBody .ing-name b'));
      ok('list: each dropped row has Restore',all('#listBody .ing-row.retired').every(function(r){return /Restore/.test(r.textContent);})&&all('#listBody .ing-row.retired').length===2);
      ok('list: toggle now says Hide dropped',byId('droppedToggle').textContent==='Hide dropped');
      click(byId('droppedToggle'));
    });
    step(function(){
      ok('list: a second tap hides them again',names().indexOf('Old Meatloaf')<0);
      set('filter','squash  WINTER');
    });
    step(function(){
      ok('list: the filter matches word by word, any order, any case',JSON.stringify(names())==='["Winter Squash Melt"]',JSON.stringify(names()));
      ok('list: filtered count',byId('countTag').textContent==='1 of 6 drafts · target 26–28%',byId('countTag').textContent);
      set('filter','nothing like this');
    });
    step(function(){
      ok('list: no match says so',/No dishes match/.test(byId('listBody').textContent));
      ok('list: filtering never writes',writes().length===0);
    });
  }
  if(S==='create'){
    step(function(){click(byId('newBtn'));});
    step(function(){
      ok('create: the New dish modal opens',shown('newModal'));
      set('newName','   ');click(byId('newSave'));
    });
    step(function(){
      ok('create: a blank name is refused in words, with no write',err('newErr')==='Give the dish a name.'&&writes().length===0);
      set('newName','  Winter Squash Melt ');
      click(byId('newSave'));click(byId('newSave'));   // a double tap
      saveNew();   // and the Enter key, which a disabled button does not stop
    });
    step(function(){
      ok('create: a double tap sends ONE write',posts().length===1,posts().length);
      var p=posts()[0];
      ok('create: the page names the row with a uuid',p&&UUID.test(p.body.id),p&&p.body.id);
      ok('create: upsert on id',p&&p.q.on_conflict==='id');
      ok('create: merge-duplicates and return=representation',p&&/resolution=merge-duplicates/.test(p.prefer)&&/return=representation/.test(p.prefer),p&&p.prefer);
      ok('create: defaults Idea, makes 1, 26-28, Tempest, trimmed name',p&&p.body.status==='idea'&&p.body.makes_plates===1&&p.body.target_low===26&&p.body.target_high===28&&p.body.location==='Tempest'&&p.body.name==='Winter Squash Melt',p&&JSON.stringify(p.body));
      ok('create: one row in the table',T.menu_drafts.length===1);
      ok('create: the dish screen opens on it',shown('dishModal')&&byId('dName').value==='Winter Squash Melt'&&!shown('newModal'));
      ok('create: it opens as Idea, makes 1, 26-28',activeStatus()==='idea'&&byId('dPlates').value==='1'&&byId('dLow').value==='26'&&byId('dHigh').value==='28');
      click(byId('dBack'));
    });
    step(function(){
      ok('create: the list shows it',JSON.stringify(names())==='["Winter Squash Melt"]');
      ok('create: no confirm when nothing changed',H.confirmMsgs.length===0);
      create('Beet Salad');
    });
    step(function(){
      ok('create: a second dish gets its own id',posts().length===2&&posts()[1].body.id!==posts()[0].body.id&&T.menu_drafts.length===2);
      ok('create: no PATCH was needed to create',patches().length===0);
    });
  }
  if(S==='createlost'){
    /* written, but the answer never comes: look it up, do not offer a retry */
    step(function(){H.nextWrite.push('lost');create('Pork Belly Bao');});
    step(function(){},200);
    step(function(){
      ok('createlost: one POST',posts().length===1);
      ok('createlost: it looked the row up by its id',reads().some(function(r){return r.q.id==='eq.'+posts()[0].body.id;}));
      ok('createlost: found it, so it opened the dish',shown('dishModal')&&byId('dName').value==='Pork Belly Bao');
      ok('createlost: one row, not two',trow('Pork Belly Bao').length===1);
      ok('createlost: no error toast',!toastIsError());
    });
  }
  if(S==='createdrop'){
    /* not written, no answer: the look-up says so; the retry uses the SAME id */
    step(function(){H.nextWrite.push('drop');create('Apple Galette');});
    step(function(){},200);
    step(function(){
      ok('createdrop: looked before offering a retry',reads().some(function(r){return r.q.id==='eq.'+posts()[0].body.id;}));
      ok('createdrop: says it did not save, as an error',toastIsError()&&/did not save/.test(toast()),toast());
      ok('createdrop: the modal stays open with the name',shown('newModal')&&byId('newName').value==='Apple Galette');
      ok('createdrop: Save is usable again',!byId('newSave').disabled);
      click(byId('newSave'));
    });
    step(function(){
      ok('createdrop: the retry re-sends the SAME id',posts().length===2&&posts()[1].body.id===posts()[0].body.id);
      ok('createdrop: one row',T.menu_drafts.length===1);
      ok('createdrop: opened',shown('dishModal'));
    });
  }
  if(S==='createblind'){
    /* written, no answer, AND the look-up fails: say "could not confirm"; the
       retry upserts the same id, so the row it already made is updated, not doubled */
    step(function(){H.nextWrite.push('lost');H.next.push('err');create('Chicken & Dumpling');});
    step(function(){},200);
    step(function(){
      ok('createblind: says it could not confirm',toastIsError()&&/Could not confirm/.test(toast()),toast());
      ok('createblind: the row did land',T.menu_drafts.length===1);
      click(byId('newSave'));
    });
    step(function(){
      ok('createblind: retry re-sends the same id',posts().length===2&&posts()[1].body.id===posts()[0].body.id);
      ok('createblind: still ONE dish',T.menu_drafts.length===1,T.menu_drafts.length);
      ok('createblind: and it opens',shown('dishModal'));
    });
  }
  if(S==='edit'){
    var id2='00000000-0000-4000-8000-000000000002';
    step(function(){click(rowNamed('Winter Squash Melt'));});
    step(function(){
      ok('edit: tapping a row opens it',shown('dishModal')&&byId('dName').value==='Winter Squash Melt');
      ok('edit: fields filled from the row',byId('dPrice').value==='14.00'&&byId('dPlates').value==='1'&&byId('dLow').value==='26'&&byId('dHigh').value==='28'&&activeStatus()==='testing',
        [byId('dPrice').value,byId('dPlates').value,activeStatus()].join('|'));
      set('dName','Winter Squash Melt II');set('dPlates','12');set('dPrice','$15.5');set('dLow','25');set('dHigh','29%');set('dNotes','  needs acid  ');
      click(statusBtn('ready'));
    });
    step(function(){
      ok('edit: tapping a status does not save by itself',writes().length===0&&activeStatus()==='ready');
      click(byId('dSave'));click(byId('dSave'));saveDish();
    });
    step(function(){
      ok('edit: a double tap sends ONE PATCH',patches().length===1,patches().length);
      var p=patches()[0];
      ok('edit: PATCHes only this id',p&&p.q.id==='eq.'+id2,p&&p.u);
      ok('edit: sends every field, parsed',p&&p.body.name==='Winter Squash Melt II'&&p.body.makes_plates===12&&p.body.menu_price===15.5&&p.body.target_low===25&&p.body.target_high===29&&p.body.notes==='needs acid'&&p.body.status==='ready',p&&JSON.stringify(p.body));
      ok('edit: sends updated_at',p&&!!p.body.updated_at);
      ok('edit: no POST for an edit',posts().length===0);
      var others=T.menu_drafts.filter(function(r){return r.id!==id2;});
      ok('edit: no other row changed',JSON.stringify(others)===JSON.stringify(H.fx0),'');
      ok('edit: the screen shows the saved row',byId('dPrice').value==='15.50'&&byId('dTitle').textContent==='Winter Squash Melt II'&&byId('dNotes').value==='needs acid');
      ok('edit: says Saved',/Saved/.test(toast())&&!toastIsError());
      click(byId('dBack'));
    });
    step(function(){
      ok('edit: no "leave without saving" after a save',H.confirmMsgs.length===0);
      ok('edit: the list re-sorts (now Ready)',names().slice(0,3).indexOf('Winter Squash Melt II')>-1,JSON.stringify(names()));
      click(rowNamed('Winter Squash Melt II'));
    });
    step(function(){set('dPrice','');click(byId('dSave'));});
    step(function(){
      ok('edit: clearing the price sends null',patches()[1]&&patches()[1].body.menu_price===null);
      ok('edit: and the list says no menu price yet',/no menu price yet/.test(rowNamed('Winter Squash Melt II').textContent));
    });
  }
  if(S==='validate'){
    var BAD=[['dName','  ','eName'],['dPlates','0','ePlates'],['dPlates','','ePlates'],['dPlates','abc','ePlates'],['dPlates','-2','ePlates'],
             ['dPrice','0','ePrice'],['dPrice','-3','ePrice'],['dPrice','14,00','ePrice'],
             ['dLow','30','eTarget'],['dHigh','100','eTarget'],['dLow','0','eTarget'],['dLow','','eTarget']];
    BAD.forEach(function(b){
      step(function(){click(rowNamed('Pork Belly Bao'))||0;if(!shown('dishModal'))click(rowNamed('Pork Belly Bao'));});
      step(function(){
        if(b[0]==='dLow'&&b[1]==='30')set('dHigh','26');
        set(b[0],b[1]);click(byId('dSave'));
      });
      step(function(){
        ok('validate: '+b[0]+'="'+b[1]+'" is refused in words beside the field',!!err(b[2])&&byId(b[0]).classList.contains('bad'),err(b[2]));
        ok('validate: '+b[0]+'="'+b[1]+'" writes nothing',writes().length===0,writes().length);
        H.confirmReturn=true;closeDish(true);
      });
    });
    step(function(){click(rowNamed('Pork Belly Bao'));});
    step(function(){set('dName','  ');click(statusBtn('dropped'));});
    step(function(){
      ok('validate: a bad form is caught before Drop even asks',H.confirmMsgs.length===0&&writes().length===0&&!!err('eName'));
    });
  }
  if(S==='drop'){
    var id1='00000000-0000-4000-8000-000000000001';
    step(function(){click(rowNamed('Pork Belly Bao'));});
    step(function(){H.confirmReturn=false;click(statusBtn('dropped'));});
    step(function(){
      ok('drop: it asks first, in the plan\'s words',H.confirmMsgs[0]==='Drop this dish? It will be hidden, not deleted. You can bring it back from "Show dropped".',H.confirmMsgs[0]);
      ok('drop: saying no writes nothing and keeps the status',writes().length===0&&activeStatus()==='idea');
      H.confirmReturn=true;click(statusBtn('dropped'));
    });
    step(function(){
      ok('drop: asked again on the second try',H.confirmMsgs.length===2);
      var p=patches()[0];
      ok('drop: one PATCH, this id, status dropped',patches().length===1&&p.q.id==='eq.'+id1&&p.body.status==='dropped',p&&JSON.stringify(p.body));
      ok('drop: the row is kept, marked dropped',T.menu_drafts.filter(function(r){return r.id===id1;})[0].status==='dropped');
      ok('drop: back to the list',!shown('dishModal'));
      ok('drop: hidden from the list',names().indexOf('Pork Belly Bao')<0);
      ok('drop: Show dropped (3)',byId('droppedToggle').textContent==='Show dropped (3)');
      ok('drop: count line now 5',byId('countTag').textContent.indexOf('5 drafts')===0);
      ok('drop: no extra "leave without saving"',H.confirmMsgs.length===2);
    });
  }
  if(S==='restore'){
    var id7='00000000-0000-4000-8000-000000000007';
    step(function(){click(byId('droppedToggle'));});
    step(function(){click(all('button',rowNamed('Old Meatloaf'))[0]);});
    step(function(){
      var p=patches()[0];
      ok('restore: one PATCH, that id, status idea',patches().length===1&&p.q.id==='eq.'+id7&&p.body.status==='idea'&&Object.keys(p.body).sort().join()==='status,updated_at',p&&JSON.stringify(p.body));
      ok('restore: Restore does not open the dish',!shown('dishModal'));
      ok('restore: back in the main list as Idea',liveNames().indexOf('Old Meatloaf')>-1&&rowNamed('Old Meatloaf').querySelector('.uc').textContent==='Idea');
      ok('restore: Show dropped count drops to 1',/\(1\)|Hide dropped/.test(byId('droppedToggle').textContent));
      ok('restore: says so',/Restored Old Meatloaf/.test(toast()));
      ok('restore: kept its price',T.menu_drafts.filter(function(r){return r.id===id7;})[0].menu_price===13);
    });
  }
  if(S==='unsaved'){
    step(function(){click(rowNamed('Beet Salad'));});
    step(function(){set('dNotes','try golden beets');H.confirmReturn=false;click(byId('dBack'));});
    step(function(){
      ok('unsaved: ← Menu with changes asks first',H.confirmMsgs.length===1&&/Leave without saving/.test(H.confirmMsgs[0]));
      ok('unsaved: saying no keeps the dish open with the text',shown('dishModal')&&byId('dNotes').value==='try golden beets');
      var bg=byId('dishModal');bg.dispatchEvent(new MouseEvent('click',{bubbles:true}));
    });
    step(function(){
      ok('unsaved: a stray tap outside asks too',H.confirmMsgs.length===2&&shown('dishModal'));
      set('dNotes','');click(statusBtn('ready'));click(byId('dBack'));
    });
    step(function(){
      ok('unsaved: an unsaved status change also asks',H.confirmMsgs.length===3);
      H.confirmReturn=true;click(byId('dBack'));
    });
    step(function(){
      ok('unsaved: saying yes leaves, writing nothing',!shown('dishModal')&&writes().length===0);
    });
  }
  if(S==='busy'){
    step(function(){click(rowNamed('Beet Salad'));});
    step(function(){H.nextWrite.push('defer');set('dNotes','x');click(byId('dSave'));});
    step(function(){
      ok('busy: every box and button on the dish screen is locked',['dName','dPlates','dPrice','dLow','dHigh','dNotes','dBack','dSave'].every(function(i){return byId(i).disabled;})&&all('#dStatus .filter-btn').every(function(b){return b.disabled;}));
      ok('busy: Save says Saving…',byId('dSave').textContent==='Saving…');
      click(byId('dSave'));click(statusBtn('dropped'));closeDish();
      ok('busy: nothing else is sent while one is in flight',writes().length===1&&H.confirmMsgs.length===0);
      ok('busy: the dish cannot be closed mid-save',shown('dishModal'));
      ok('busy: New dish is locked',byId('newBtn').disabled);
      H.releaseDeferred();
    });
    step(function(){
      ok('busy: unlocked when the answer comes',!byId('dSave').disabled&&byId('dSave').textContent==='Save');
      closeDish(true);click(byId('droppedToggle'));
    });
    step(function(){H.nextWrite.push('defer');click(all('button',rowNamed('Old Meatloaf'))[0]);});
    step(function(){
      var other=all('button',rowNamed('Fish <b>Taco</b>'))[0];
      ok('busy: the other Restore is locked while one is in flight',other&&other.disabled);
      click(other);click(rowNamed('Beet Salad'));
      ok('busy: nothing else sent and no dish opened',writes().length===2&&!shown('dishModal'));
      H.releaseDeferred();
    });
  }
  if(S==='editlost'){
    /* written, answer lost: look by id; the row matches, so it is saved */
    step(function(){click(rowNamed('Beet Salad'));});
    step(function(){H.nextWrite.push('lost');set('dPrice','12');click(byId('dSave'));});
    step(function(){},200);
    step(function(){
      ok('editlost: looked the row up by id',reads().some(function(r){return r.q.id==='eq.00000000-0000-4000-8000-000000000005';}));
      ok('editlost: it landed, so it says Saved',/Saved/.test(toast())&&!toastIsError(),toast());
      ok('editlost: one PATCH',patches().length===1);
      ok('editlost: the screen shows the saved price',byId('dPrice').value==='12.00');
    });
  }
  if(S==='editdrop'){
    /* not written, no answer: the look-up shows the old row, so it says it did not save */
    step(function(){click(rowNamed('Beet Salad'));});
    step(function(){H.nextWrite.push('drop');set('dPrice','12');click(byId('dSave'));});
    step(function(){},200);
    step(function(){
      ok('editdrop: says it did not save',toastIsError()&&/did not save/.test(toast()),toast());
      ok('editdrop: what was typed is still there to retry',byId('dPrice').value==='12');
      ok('editdrop: never retried by itself',patches().length===1);
      ok('editdrop: still unsaved, so leaving would ask',dishDirty());
      click(byId('dSave'));
    });
    step(function(){
      ok('editdrop: the retry lands',patches().length===2&&T.menu_drafts.filter(function(r){return r.name==='Beet Salad';})[0].menu_price===12);
    });
    step(function(){H.nextWrite.push('e500');set('dPrice','13');click(byId('dSave'));});
    step(function(){
      ok('editdrop: a 500 is looked up, not reported as a plain failure',reads().filter(function(r){return /^eq\./.test(r.q.id||'');}).length===2);
    });
  }
  if(S==='fonts'){
    step(function(){
      /* --window-size does not set the layout viewport (check_inventory.py's
         note), so a 375px phone is simulated by narrowing the page itself */
      byId('app').style.width='375px';
      var off=all('#app .header *,#app .intro,#listBody .ing-row').filter(function(e){var r=e.getBoundingClientRect();return r.width>0&&r.right>375.5;})
        .map(function(e){return (e.id||e.className||e.tagName)+'@'+Math.round(e.getBoundingClientRect().right);});
      ok('fonts: at 375px nothing in the header or list runs off the right edge',off.length===0,off.slice(0,6).join(', '));
      var nb=byId('newBtn').getBoundingClientRect();
      ok('fonts: ＋ New dish is fully on screen at 375px',nb.left>=0&&nb.right<=375.5&&nb.width>40,Math.round(nb.left)+'-'+Math.round(nb.right));
      byId('app').style.width='';
    });
    step(function(){click(byId('newBtn'));});
    step(function(){
      var small=all('input,textarea').filter(function(e){var r=e.getBoundingClientRect();return r.width>0&&parseFloat(getComputedStyle(e).fontSize)<16;})
        .map(function(e){return (e.id||e.className)+'='+getComputedStyle(e).fontSize;});
      ok('fonts: every box in New dish and the list is 16px or more',small.length===0,small.join(', '));
      closeNew();click(rowNamed('Beet Salad'));
    });
    step(function(){
      var small=all('#dishModal input,#dishModal textarea').filter(function(e){return parseFloat(getComputedStyle(e).fontSize)<16;})
        .map(function(e){return e.id+'='+getComputedStyle(e).fontSize;});
      ok('fonts: every box on the dish screen is 16px or more',small.length===0,small.join(', '));
      ok('fonts: number boxes bring up the decimal keypad',['dPlates','dPrice','dLow','dHigh'].every(function(i){return byId(i).type==='text'&&byId(i).inputMode==='decimal';}));
    });
  }
  H.fx0=JSON.parse(JSON.stringify(T.menu_drafts.filter(function(r){return r.id!=='00000000-0000-4000-8000-000000000002';})));
  setTimeout(run,150);
})();
</script>
"""


def build_page():
    src = open(os.path.join(ROOT, PAGE), encoding="utf-8").read()
    src, n = GATE_RE.subn("void 0 /* gate neutralised by check_menu_builder.py */", src)
    if n != 1:
        sys.exit("check_menu_builder: could not find the site-password redirect in " + PAGE)
    marker = "<script>\nvar SB="
    if marker not in src:
        sys.exit("check_menu_builder: could not find the page script in " + PAGE)
    src = src.replace(marker, HARNESS.replace("__FIXTURES__", json.dumps({"drafts": DRAFTS})) + marker, 1)
    src = re.sub(r'<link rel="preconnect"[^>]*>\s*', '', src)
    src = re.sub(r'<link rel="stylesheet" href="https://fonts[^>]*>\s*', '', src)
    return src.replace("</body>", RUNNER + "</body>", 1)


RESULT_RE = re.compile(r'<div id="harnessResults">(.*?)</div>', re.S)


def run_scenario(chrome, path, scen):
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
             "--virtual-time-budget=60000", "--dump-dom", url],
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


def static_checks():
    """Promises that hold for the file as written, whatever any scenario does."""
    src = open(os.path.join(ROOT, PAGE), encoding="utf-8").read()
    fails = []
    if re.search(r"['\"]DELETE['\"]", src):
        fails.append("static: the page contains a DELETE call")
    if re.search(r"(^|[^-]):root\s*\{", src):
        fails.append("static: the page declares its own :root")
    for t in re.findall(r"api\('[A-Z]+','([a-z_]+)'", src):
        if t != "menu_drafts":
            fails.append("static: the page talks to " + t)
    if "kitchen.css?v=2026-09-19" not in src:
        fails.append("static: kitchen.css is not linked with the site's ?v=")
    if "recipe-math" in src:
        fails.append("static: references recipe-math.js, which is not in this slice")
    return fails


def main():
    chrome = find_chrome()
    if not chrome:
        sys.exit("check_menu_builder: no Chrome found. Set CHROME=/path/to/chrome.")
    page = build_page()
    fails, total = static_checks(), 5
    scens = os.environ['ONLY'].split(',') if os.environ.get('ONLY') else SCENARIOS
    with tempfile.TemporaryDirectory() as td:
        path = os.path.join(td, "menu_under_test.html")
        with open(path, "w", encoding="utf-8") as f:
            f.write(page)
        shutil.copytree(os.path.join(ROOT, "assets"), os.path.join(td, "assets"))
        for scen in scens:
            res, err = run_scenario(chrome, path, scen)
            if res is None:
                fails.append("%s: harness never reported\n%s" % (scen, err))
                continue
            total += len(res["log"])
            fails += ["%s: %s" % (scen, x) for x in res["fails"]]
    if fails:
        print("menu builder guard: %d failure(s) of %d assertions\n" % (len(fails), total))
        for x in fails:
            print("  " + x)
        print("\nsee docs/menu-builder.md, Slice 1")
        return 1
    print("menu builder guard: clean (%d assertions, %d scenarios, %s)" % (total, len(scens), PAGE))
    return 0


if __name__ == "__main__":
    sys.exit(main())
