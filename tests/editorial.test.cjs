const {test} = require('node:test');
const assert = require('node:assert/strict');
const {pathToFileURL} = require('node:url');
const path = require('node:path');
const ready = import(pathToFileURL(path.join(__dirname, '../assets/editorial-store.js')));
const policy = {azSources:{APA:['apa.az'],Nocomment:['nocomment.az']},worldSources:{},blockedHosts:[]};
const text = 'window.CONTENT_POLICY = ' + JSON.stringify(policy) + ';';
const response = (data, status=200) => ({ok:status<400,status,json:async()=>data});
const file = (content, sha='first') => ({encoding:'base64',content:Buffer.from(content).toString('base64'),sha});

test('withdrawal identity survives changed titles and slugs without matching another publisher', async () => {
  const {removalKey} = await ready;
  assert.equal(removalKey('https://www.nocomment.az/cemiyyet/new-title-555222?utm_source=x'), 'nocomment.az#555222');
  assert.notEqual(removalKey('https://apa.az/new-title-555222'), 'nocomment.az#555222');
  assert.equal(removalKey('https://apa.az/date-20261105/news'), 'https://apa.az/date-20261105/news');
  for (const u of ['javascript:alert(1)','https://user:pass@apa.az/12345','https://apa.az/']) assert.throws(()=>removalKey(u));
});
test('a grouped withdrawal includes its original ID, alternative URLs and their shared-link IDs', async () => {
  const {makeRemoval} = await ready;
  const record = await makeRemoval({id:'group-id',title:'Başlıq',sourceUrl:'https://nocomment.az/title-555222',alts:[{sourceUrl:'https://apa.az/story-12345'}]}, 'owner', policy, 'now');
  assert.deepEqual(record.keys, ['nocomment.az#555222','apa.az#12345']);
  assert.equal(record.ids.length, 3); assert.ok(record.ids.includes('group-id'));
  await assert.rejects(()=>makeRemoval({sourceUrl:'https://apa.az.evil.test/story-12345'},'owner',policy));
});
test('a retry preserves other withdrawals and source rules; an identical withdrawal is idempotent', async () => {
  const {makeRemoval,mergeRemoval,parsePolicy} = await ready;
  const a = await makeRemoval({sourceUrl:'https://apa.az/title-12345'},'owner',policy,'now');
  const b = await makeRemoval({sourceUrl:'https://apa.az/title-12346'},'owner',policy,'now');
  const first = mergeRemoval(text,a), next = mergeRemoval(first.text,b);
  assert.equal(mergeRemoval(next.text,a).changed,false);
  const data = parsePolicy(next.text).data;
  assert.deepEqual(data.azSources,policy.azSources);assert.equal(Object.keys(data.removedArticles).length,2);
});
test('a reader account cannot perform editorial writes and its session is discarded', async () => {
  const {GithubEditor} = await ready; let writes=0;
  const editor = new GithubEditor(async(url,options)=>{if(options.method)writes++;return response(url.endsWith('/user')?{login:'reader'}:{permissions:{push:false}});});
  await assert.rejects(()=>editor.login('test-only'),/yazma/);assert.equal(editor.user,null);
  await assert.rejects(()=>editor.remove({sourceUrl:'https://apa.az/1'}));assert.equal(writes,0);
});
test('a simultaneous GitHub update is retried with the new file SHA, preserving the other decision', async () => {
  const {GithubEditor,mergeRemoval,makeRemoval,parsePolicy} = await ready;
  const other=await makeRemoval({sourceUrl:'https://apa.az/other-12346'},'another-owner',policy,'now');
  let puts=0,latest=text;
  const editor = new GithubEditor(async(url,options)=>{
    assert.equal(options.redirect,'error');assert.equal(options.headers.Authorization,'Bearer test-only');
    if(url.endsWith('/user'))return response({login:'owner'});
    if(!url.includes('/contents/'))return response({permissions:{push:true}});
    if(options.method==='PUT'){
      puts++;const body=JSON.parse(options.body);assert.ok(!options.body.includes('test-only'));
      if(puts===1){latest=mergeRemoval(text,other).text;return response({},409);}
      assert.equal(body.sha,'second');latest=Buffer.from(body.content,'base64').toString('utf8');return response({commit:{sha:'committed'}});
    }
    return response(file(latest,puts?'second':'first'));
  });
  await editor.login('test-only');const result=await editor.remove({sourceUrl:'https://apa.az/title-12345',title:'Başlıq'});
  assert.equal(result.commit,'committed');assert.equal(puts,2);assert.equal(Object.keys(parsePolicy(latest).data.removedArticles).length,2);
  editor.logout();await assert.rejects(()=>editor.policy());
});
test('a forbidden write is reported as a failure, never as a completed deletion', async () => {
  const {GithubEditor} = await ready;
  const editor=new GithubEditor(async(url,options)=>response(url.endsWith('/user')?{login:'owner'}:!url.includes('/contents/')?{permissions:{push:true}}:options.method==='PUT'?{}:file(text),options.method==='PUT'?403:200));
  await editor.login('test-only');await assert.rejects(()=>editor.remove({sourceUrl:'https://apa.az/title-12345'}),/icazəsi yoxdur/);
});
