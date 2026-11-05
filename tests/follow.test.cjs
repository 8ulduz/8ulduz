const {test} = require('node:test');
const assert = require('node:assert/strict');
const {pathToFileURL} = require('node:url');
const path = require('node:path');
const ready = import(pathToFileURL(path.join(__dirname, '../assets/follow.js')));

test('follow links use the existing Telegram and configured accounts in the chosen order', async () => {
  const {followLinks} = await ready;
  const links = followLinks({telegram:'https://t.me/example_channel',follow:{whatsapp:'https://www.whatsapp.com/channel/example',facebook:'https://www.facebook.com/example',instagram:'https://instagram.com/example',linkedin:'https://www.linkedin.com/company/example',googleNews:'https://news.google.com/publications/example?hl=az'}});
  assert.deepEqual(links.map(x=>x.id), ['telegram','whatsapp','facebook','instagram','googleNews','linkedin']);
  assert.equal(links[0].href, 'https://t.me/example_channel');
  assert.deepEqual(followLinks({telegram:'https://t.me/example_channel',follow:{telegram:''}}), []);
});

test('a wrong host, unsafe URL or messaging/search link is never presented as a follow channel', async () => {
  const {followLinks} = await ready;
  for (const url of ['javascript:alert(1)','http://t.me/example','https://t.me.evil.test/example','https://t.me@evil.test/example','https://name:pass@t.me/example','https://t.me:444/example','https://t.me/','not a URL']) {
    assert.deepEqual(followLinks({telegram:url}), [], url);
  }
  for (const follow of [{whatsapp:'https://wa.me/1234'}, {whatsapp:'https://whatsapp.com/send?phone=1234'}, {googleNews:'https://news.google.com/search?q=8ulduz'}, {linkedin:'https://linkedin.com/search/results/all/?keywords=8ulduz'}]) {
    assert.deepEqual(followLinks({follow}), []);
  }
});

test('the owner-supplied personal LinkedIn, Facebook profile, Telegram and X accounts all appear', async () => {
  const {followLinks} = await ready;
  const links = followLinks({telegram:'https://t.me/sekkizulduz',follow:{facebook:'https://www.facebook.com/profile.php?id=61596034210996',linkedin:'https://www.linkedin.com/in/s%C9%99kkiz-ulduz-605537449/',x:'https://x.com/8ulduz'}});
  assert.deepEqual(links.map(x=>x.id), ['telegram','facebook','linkedin','x']);
  assert.ok(links.find(x=>x.id==='facebook').href.endsWith('id=61596034210996'));
  assert.equal(links.find(x=>x.id==='linkedin').href, 'https://www.linkedin.com/in/s%C9%99kkiz-ulduz-605537449/');
});

function fixture({denyHistory=false,delayPop=false}={}) {
  const listeners = new Map(), windowEvents = new Map(), classes = new Set();
  const previous = {article:'keep-me'}, entries=[previous];
  let backCount=0, focusCount=0, removed=false, prevented=false;
  const button={addEventListener:(name, fn)=>listeners.set('button-'+name,fn)};
  const dialog={open:false,addEventListener:(name,fn)=>listeners.set(name,fn),querySelector:()=>button,
    showModal(){this.open=true;}, close(){this.open=false;listeners.get('close')();}, remove(){removed=true;},getBoundingClientRect:()=>({left:10,right:100,top:100,bottom:300})};
  const win={location:{href:'https://8ulduz.az/#/xeber/abc'},document:{documentElement:{classList:{contains:x=>classes.has(x),add:x=>classes.add(x),remove:x=>classes.delete(x)}}},
    addEventListener:(name,fn)=>windowEvents.set(name,fn), removeEventListener:name=>windowEvents.delete(name),
    history:{state:previous,pushState(s,title,url){if(denyHistory)throw Error('private webview');assert.equal(url,win.location.href);entries.push(s);this.state=s;},back(){backCount++;entries.pop();this.state=entries.at(-1);if(!delayPop)windowEvents.get('popstate')?.();}}};
  return {dialog,win,opener:{isConnected:true,focus:()=>focusCount++},listeners,classes,previous,
    escape(){listeners.get('cancel')({preventDefault(){prevented=true;}});},pop(){windowEvents.get('popstate')?.();},
    state:()=>({backCount,focusCount,removed,prevented,entries:entries.length})};
}

test('Escape consumes only the panel history entry and restores the article and focus', async () => {
  const {wireFollowDialog}=await ready, f=fixture();
  wireFollowDialog(f.dialog,f.opener,f.win);
  assert.equal(f.dialog.open,true); assert.ok(f.classes.has('follow-open'));
  assert.equal(f.win.history.state.article,'keep-me');
  f.escape();
  assert.deepEqual(f.state(),{backCount:1,focusCount:1,removed:true,prevented:true,entries:1});
  assert.equal(f.win.history.state,f.previous); assert.ok(!f.classes.has('follow-open'));
});

test('the phone Back button closes the panel without a second Back navigation', async () => {
  const {wireFollowDialog}=await ready, f=fixture();
  wireFollowDialog(f.dialog,f.opener,f.win);
  f.win.history.back();
  assert.equal(f.state().backCount,1); assert.equal(f.state().entries,1); assert.equal(f.dialog.open,false);
});

test('two rapid dismissals cannot navigate past the article', async () => {
  const {wireFollowDialog}=await ready, f=fixture({delayPop:true});
  const close=wireFollowDialog(f.dialog,f.opener,f.win);
  close();close();assert.equal(f.state().backCount,1);
  f.pop();assert.equal(f.state().focusCount,1);assert.equal(f.dialog.open,false);
});

test('a webview that refuses history still has a working close button', async () => {
  const {wireFollowDialog}=await ready, f=fixture({denyHistory:true});
  wireFollowDialog(f.dialog,f.opener,f.win);
  f.listeners.get('button-click')();
  assert.equal(f.state().backCount,0);assert.equal(f.dialog.open,false);assert.equal(f.state().focusCount,1);
});
