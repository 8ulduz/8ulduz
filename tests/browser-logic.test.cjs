const { test } = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const path = require('node:path');
const root = path.join(__dirname, '..');

// Kiçildilmiş kodda yuxarı adlar qısadır (kicilt.cjs, 2026-11-13): eyni funksiyalar ad cədvəli ilə çağırılır. Mənbə üçün heç nə dəyişmir.
const MIN = 'assets/app.min.js';
let minNames;
const namesOf = file => file === MIN ? (minNames ||= require('../.github/kicilt/kicilt.cjs').buildSync(fs.readFileSync(path.join(root, 'assets/app.js'), 'utf8')).names) : null;
// Koddakı yuxarı adları (sətir sabitlərinin içi və «.xassə» istisna) fayldakı adlara çevirir.
const tr = (code, file) => { const names = namesOf(file); return names ? code.replace(/("(?:[^"\\]|\\.)*"|'(?:[^'\\]|\\.)*')|(?<![.\w$])[A-Za-z_$][\w$]*/g, (w, str) => str ? w : Object.hasOwn(names, w) ? names[w] : w) : code; };
function app(extra = {}, file = 'assets/app.js') {
  const context = vm.createContext({
    console, Map, Set, URL, Date, AbortController, TextEncoder, btoa, setTimeout, clearTimeout, addEventListener() {},
    localStorage: { getItem() { throw Error('blocked'); }, setItem() { throw Error('quota'); }, removeItem() { throw Error('blocked'); } },
    location: { hash: '#/' }, navigator: { onLine: true },
    window: { addEventListener() {} },
    document: { documentElement: { dataset: {} }, addEventListener() {}, querySelector() { return null; }, createElement() { return {}; } },
    matchMedia: () => ({ matches: false }), ...extra,
  });
  const source = fs.readFileSync(path.join(root, file), 'utf8').split(/\r?\napplyPrefs\(\);\r?\n/)[0];
  vm.runInContext(source, context);
  const API = ["scanArchives", "sized", "img", "subNav", "navPopHtml", "popLeft", "safeHref", "policyViolation", "altForbidden", "publishNews", "savedView", "latestBlock", "homeView", "storage", "applyPrefs", "route", "loadNews", "requestJSON", "pollNews", "resumeNews", "freshUrl", "isFresh", "withinHour", "footballBlock", "S", "heroPick", "searchView", "searchTopics", "sectionView", "languagePicker", "renderNav", "ratesView", "leagueView", "installBtn", "trackEvent", "countVisit", "flushVisits", "enableAnalytics", "savedLang", "LANG_KEY", "tidy", "ordTur", "fold", "searchWords", "hlRegex", "orderedSocialPosts", "socialBlock", "isAppointment", "prezHome", "tickerLabel", "card", "altPop", "catSection", "articleView", "languagePicker", "imageCandidates", "heroBlock", "prezBlock", "localRoadItems", "trackedSources", "sectionView", "clubMatches", "requestRender", "readerBusy", "withArchive", "loadArchive", "showBreaking", "teamSlug", "loadShared", "shareRow", "loadCached", "loadFirst", "heavyImage", "cardAt", "imgFail", "renderView", "img"];
  vm.runInContext(tr(`render = () => {}; renderTopbar = () => {}; loadOg = async () => { S.og = {}; };
    checkBreaking = () => {};`, file) + ` globalThis.api = {${[...new Set(API)].map(n => `${n}: ${tr(n, file)}`).join(', ')}};`, context);
  return context;
}

test('rush hour uses Baku time (UTC+4) without Intl',()=>{
  const rush=vm.runInContext('bakuRush',app());
  assert.equal(rush(new Date('2026-11-03T05:30:00Z')),true,'çərşənbə axşamı 09:30');
  assert.equal(rush(new Date('2026-11-03T12:00:00Z')),false,'16:00');
  assert.equal(rush(new Date('2026-11-03T14:10:00Z')),true,'18:10');
  assert.equal(rush(new Date('2026-11-07T05:30:00Z')),false,'şənbə');
  assert.equal(rush(new Date('2026-11-02T20:30:00Z')),false,'bazar ertəsi gecə 00:30');
});
test('Baku traffic excludes foreign disasters, condolences and stale reports',()=>{
  const {localRoadItems}=app().api;
  const stamp=new Date().toISOString();
  const rows=['Bakıda bu yolda tıxac var','İspaniyada qatar qəzası baş verdi','Bakıda helikopter qəzaya uğradı','Prezident qatar qəzasına görə başsağlığı verdi','Gəncədə yolda qəza baş verdi'].map((title,id)=>({id,title,publishedAt:stamp,lang:'az'}));
  rows.push({title:'Bakıda tıxac var',publishedAt:'2020-01-01',lang:'az'});
  assert.deepEqual(Array.from(localRoadItems(rows),a=>a.id),[0]);
});
test('source count uses the monitored feed registry, including temporarily empty sources',()=>{
  const {S,trackedSources}=app().api;
  S.data={articles:[{source:'APA',title:'Xəbər'}]};
  S.sources={sources:[{name:'APA'},{name:'Oxu.az'},{name:'AZƏRTAC'}]};
  assert.deepEqual(Array.from(trackedSources()).sort(),['APA','AZƏRTAC','Oxu.az'].sort());
});

test('blocked browser storage still allows preferences and saving', () => {
  const ctx = app();
  ctx.api.applyPrefs();
  assert.equal(ctx.document.documentElement.dataset.theme, 'dark');
  ctx.api.storage.setItem('8ulduz-theme', 'light');
  ctx.api.applyPrefs();
  assert.equal(ctx.document.documentElement.dataset.theme, 'light');
  ctx.api.storage.removeItem('8ulduz-theme');
  assert.equal(ctx.api.storage.getItem('8ulduz-theme'), null);
});

test('first visit follows the phone theme, the reader choice wins, unknown is dark (owner, 2026-11-06)', () => {
  for (const [sys, saved, want] of [[true, null, 'light'], [false, null, 'dark'], [undefined, null, 'dark'], [true, 'dark', 'dark'], [false, 'light', 'light']]) {
    const ctx = app(sys === undefined ? {} : { matchMedia: q => ({ matches: q.includes('light') && sys, addEventListener() {} }) });
    if (saved) ctx.api.storage.setItem('8ulduz-theme', saved);
    ctx.api.applyPrefs();
    assert.equal(ctx.document.documentElement.dataset.theme, want, `sistem ${sys}, seçim ${saved}`);
  }
  const index = fs.readFileSync(path.join(root, 'index.html'), 'utf8');
  assert.ok(index.includes('t === "light" || t === "dark" ? t : matchMedia("(prefers-color-scheme: light)").matches ? "light" : "dark"'), 'ilk çəkilişdə də eyni qayda (ekran yanıb-sönmür)');
});

test('broken percent-encoded route does not break the page', () => {
  const ctx = app();
  ctx.location.hash = '#/axtar?q=100%';
  assert.equal(ctx.api.route().q, '100%');
  ctx.location.hash = '#/axtar?q=%C4%B0lham';
  assert.equal(ctx.api.route().q, 'İlham');
});

// Sahib, 2026-11-13: «Saytda standart şrifti indiki A+-ın 2 kliki boyda et». Standart pillə 2-dən 4-ə keçdi (ölçülər yerində
// qaldı: saxlanmış seçim eyni ölçünü göstərir), üstünə iki yeni pillə (5, 6) əlavə olundu ki, A+ standartdan da böyütsün.
test('reader font starts at the former two-click size and adjusts in both directions without losing saved sizes', () => {
  const ctx = app({requestAnimationFrame() {}});
  vm.runInContext('setupMarquees = () => {};', ctx);
  ctx.api.applyPrefs();
  assert.equal(ctx.document.documentElement.dataset.fs, '4');
  vm.runInContext('setPref("fs-up"); setPref("fs-up"); setPref("fs-up");', ctx);
  assert.equal(ctx.document.documentElement.dataset.fs, '6', 'upper bound');
  assert.equal(ctx.api.storage.getItem('8ulduz-fs'), '6');
  ctx.document.documentElement.dataset.fs = '';
  ctx.api.applyPrefs();
  assert.equal(ctx.document.documentElement.dataset.fs, '6', 'saved size restored');
  vm.runInContext('for(let i=0;i<8;i++) setPref("fs-down");', ctx);
  assert.equal(ctx.document.documentElement.dataset.fs, '0', 'lower bound');
  for (const saved of ['0','1','2','3','4','5','6']) {
    ctx.api.storage.setItem('8ulduz-fs', saved);
    ctx.api.applyPrefs();
    assert.equal(ctx.document.documentElement.dataset.fs, saved, 'existing choice kept');
  }
  for (const bad of ['broken', '7', '-1', '']) {
    ctx.api.storage.setItem('8ulduz-fs', bad);
    ctx.api.applyPrefs();
    assert.equal(ctx.document.documentElement.dataset.fs, '4');
  }
});

test('the default typography is the former two-click size and every earlier size keeps its level', () => {
  const css = fs.readFileSync(path.join(root, 'assets/app.css'), 'utf8');
  const tokens = block => Object.fromEntries([...block.matchAll(/--((?:fs|lh)-[\w-]+):([^;}]+)/g)].map(m=>[m[1],m[2]]));
  const level = n => tokens(css.match(new RegExp('html\\[data-fs="' + n + '"\\]\\{([^}]+)\\}'))[1]);
  const row = (a,b,c,d,e,f,g,h,i,j) => ({'fs-display':a+'px','lh-display':b+'px','fs-title':c+'px','lh-title':d+'px',
    'fs-headline':e+'px','lh-headline':f+'px','fs-body':g+'px','lh-body':h+'px','fs-meta':i+'px','lh-meta':j+'px'});
  assert.deepEqual(tokens(css.match(/:root\{([^}]+)\}/)[1]), row(30,38,26,34,25,34,22,32,16,23), 'reference: html[data-fs="4"] before this change');
  assert.deepEqual(level(0), row(22,27,18,24,17,23,15,22,12,16));
  assert.deepEqual(level(1), row(24,30,20,26,19,26,17,25,13,18));
  assert.deepEqual(level(2), row(26,32,22,28,21,28,18,26,14,20), 'reference: the default before this change');
  assert.deepEqual(level(3), row(28,35,24,31,23,31,20,29,15,22));
  assert.ok(!css.includes('html[data-fs="4"]{'), 'level 4 is the default: it has no block of its own');
  const five = level(5), six = level(6);
  for (const k of Object.keys(five)) assert.ok(parseInt(six[k]) > parseInt(five[k]) && parseInt(five[k]) > parseInt(row(30,38,26,34,25,34,22,32,16,23)[k]), k + ' grows with the level');
  // Böyük pillələrdə (standart daxil) üst zolaq sətirə sığmır: sarınır. Kiçik pillələr (0–2) əvvəlki kimidir.
  assert.ok(css.includes('html:not([data-fs="0"],[data-fs="1"],[data-fs="2"]) .hrow>.topbar>.wrap{flex-wrap:wrap;height:auto}'));
  assert.ok(!/data-fs="[34]"\]\) \.hrow/.test(css), 'the wrap rule is not tied to a list of large levels');
  // Alt zolağın yazısı standartdan böyümür: 320 px ekranda «Seçilmişlər» 18 px-də öz xanasına (80 px) sığmırdı.
  assert.ok(css.includes('html:is([data-fs="5"],[data-fs="6"]) .tabbar a{font-size:16px}'));
});

test('the first paint and the app agree on the default font level', () => {
  const read = p => fs.readFileSync(path.join(root, p), 'utf8').replace(/\r\n/g, '\n');
  const app = read('assets/app.js');
  const std = app.match(/const FS_STD = "(\d)";/)[1];
  assert.equal(std, '4');
  assert.ok(read('index.html').includes('document.documentElement.dataset.fs = /^[0-6]$/.test(f || "") ? f : "' + std + '";'), 'baş səhifənin ilk skripti');
  assert.ok(read('assets/app.min.js').includes('/^[0-6]$/'), 'kiçildilmiş nüsxə yenidən qurulub');
  // xeber/<id>/ və bolme/<ad>/ səhifələrinin (updater.py şablonları) ilk skripti əvvəlki «2»-ni qoyur və qəsdən dəyişdirilməyib:
  // şablon dəyişsə minlərlə səhifə yenidən yazılmalıdır (STORY_VER). O səhifələrdə pilləni tətbiq düzəldir, ona görə applyPrefs()
  // ilk çəkilişlə (shell(); render()) eyni sinxron blokda və ondan əvvəl qalmalıdır: arada boya olsa statik mətn 18 → 22 px sıçrayar.
  const prefs = app.indexOf('\napplyPrefs();\n'), draw = app.indexOf('\nshell(); render();\n');
  assert.ok(prefs > 0 && draw > prefs, 'applyPrefs() ilk çəkilişdən əvvəldir');
  const between = app.slice(prefs, draw).split('\n').filter(l => /^\S/.test(l) && !/^(?:async )?function /.test(l));
  assert.ok(!between.some(l => /\bawait\b/.test(l)), 'arada üst səviyyədə gözləmə (await) yoxdur');
});

test('invalid JSON response does not poison ETag; same response can recover', async () => {
  const ctx = app();
  let valid = false;
  ctx.fetch = async () => ({ ok: true, headers: new Headers({etag: 'one'}), json: async () => valid ? {updatedAt: 'now', articles: []} : {} });
  await ctx.api.loadNews();
  assert.equal(ctx.api.S.etag, null);
  assert.ok(ctx.api.S.error);
  valid = true;
  await ctx.api.loadNews();
  assert.equal(ctx.api.S.etag, 'one');
  assert.equal(ctx.api.S.error, null);
});

test('cached news do not claim a new network sync', async () => {
  const ctx = app();
  ctx.fetch = async () => ({ok: true, headers: new Headers({'X-8ulduz-data': 'cache'}), json: async () => ({articles: []})});
  await ctx.api.loadNews();
  assert.equal(ctx.api.S.offline, true);
  assert.equal(ctx.api.S.lastSync, null);
});

test('future articles are not breaking news', () => {
  assert.equal(app().api.isFresh({publishedAt: new Date(Date.now() + 3600000).toISOString()}), false);
});

test('a suspended mobile fetch and a stalled JSON body both time out',async()=>{
  const ctx=app();
  ctx.fetch=()=>new Promise(()=>{});
  await assert.rejects(ctx.api.requestJSON('news',{},5),/vaxtı bitdi/);
  ctx.fetch=async()=>({ok:true,json:()=>new Promise(()=>{})});
  await assert.rejects(ctx.api.requestJSON('news',{},5),/vaxtı bitdi/);
});
test('forced refresh cancels a stuck request and an older request cannot overwrite recovery',async()=>{
  const ctx=app(); let calls=0;
  ctx.fetch=async()=>{
    if(++calls===1)return new Promise(()=>{});
    return {ok:true,headers:new Headers({etag:'recovered'}),json:async()=>({updatedAt:'new',articles:[]})};
  };
  const stuck=ctx.api.loadNews();
  await ctx.api.loadNews(true);
  await stuck;
  assert.equal(ctx.api.S.data.updatedAt,'new');
  assert.equal(ctx.api.S.newsLoading,false);
  assert.equal(ctx.api.S.etag,'recovered');
});
test('a forced refresh refetches news even if a CDN repeats the same status stamp',async()=>{
  const ctx=app(),{S}=ctx.api,urls=[];
  S.data={updatedAt:'old',articles:[]};S.status={checkedAt:'same'};S.newsStamp='same';S.newsCheckedAt=Date.now();
  ctx.fetch=async url=>{urls.push(url);return {ok:true,headers:new Headers(),json:async()=>url.includes('status')?{checkedAt:'same'}:{updatedAt:'fresh',articles:[]}};};
  await ctx.api.pollNews(true);
  assert.equal(S.data.updatedAt,'fresh');
  assert.ok(urls.filter(u=>!u.includes('/live/m/')).every(u=>/[?&]r=/.test(u)),'əllə yeniləmə öz açarı ilə (?r=); dəqiqəlik ?t= yoxdur (2026-11-09)');
});
test('returning to the tab checks the small file at once and does not download the whole feed',async()=>{
  const ctx=app(),{S}=ctx.api,urls=[];
  S.data={updatedAt:'old',articles:[]};S.rawNews=[];S.rawMeta={};S.status={checkedAt:'same'};S.newsStamp='same';S.newsCheckedAt=Date.now();S.latestAt=Date.now();
  ctx.fetch=async url=>{urls.push(url);return {ok:true,headers:new Headers(),json:async()=>url.includes('status')?{checkedAt:'same'}:{articles:[]}};};
  await ctx.api.pollNews(false,true);
  assert.ok(urls.some(u=>u.includes('latest.json')));
  assert.ok(!urls.some(u=>u.includes('news.json')));
});
test('red line 1: an unchanged status stamp cannot hold back the feed for more than 90 seconds',async()=>{
  const ctx=app(),{S}=ctx.api,urls=[];
  S.data={articles:[]};S.rawNews=[];S.rawMeta={};S.status={checkedAt:'same'};S.newsStamp='same';S.newsCheckedAt=Date.now();S.latestAt=Date.now()-91e3;
  ctx.fetch=async url=>{urls.push(url);return {ok:true,headers:new Headers(),json:async()=>url.includes('status')?{checkedAt:'same'}:{articles:[]}};};
  await ctx.api.pollNews();
  assert.ok(urls.some(u=>u.includes('latest.json')));
});
test('red line 1: a visitor without a service worker reads the one-minute channel, and falls back to the site',async()=>{
  const ctx=app(),{requestJSON}=ctx.api,urls=[];
  ctx.fetch=async url=>{urls.push(url);return url.includes('/live/m/')?{ok:false,status:404}:{ok:true,headers:new Headers(),json:async()=>({from:'site'})};};
  const first=await requestJSON('data/latest.json?t=1');
  assert.equal(first.d.from,'site');
  assert.equal(urls.filter(u=>u.includes('/live/m/')).length,3);
  urls.length=0;
  const ctx2=app({navigator:{onLine:true,serviceWorker:{controller:{}}}});
  ctx2.fetch=async url=>{urls.push(url);return {ok:true,headers:new Headers(),json:async()=>({from:'site'})};};
  await ctx2.api.requestJSON('data/latest.json?t=1');
  assert.ok(!urls.some(u=>u.includes('/live/m/')),'service worker varsa sıranı o idarə edir');
  urls.length=0;
  const ctx3=app();
  ctx3.fetch=async url=>{urls.push(url);return {ok:true,headers:new Headers(),json:async()=>({})};};
  await ctx3.api.requestJSON('data/news.json?t=1');
  assert.ok(!urls.some(u=>u.includes('/live/m/')),'tam lent saytdan gəlir');
});
test('red line 3: the minute feed is asked per language when the channel offers it, and falls back to the shared file', async () => {
  const run = async (lang, answer, status = {checkedAt: 'x', langs: ['az', 'en', 'ru', 'tr']}) => {
    const ctx = app({navigator: {onLine: true, serviceWorker: {controller: {}}}}), {S} = ctx.api, urls = [];
    S.lang = lang; S.status = status; S.rawNews = []; S.rawMeta = {}; S.og = {};
    ctx.fetch = async url => { urls.push(url.split('?')[0]); return answer(url); };
    await vm.runInContext('loadLatest()', ctx);
    return urls;
  };
  const ok = (extra = {}) => ({ok: true, headers: new Headers(extra), json: async () => ({articles: []})});
  assert.deepEqual(await run('az', () => ok()), ['data/latest.az.json'], 'yalnız öz dilinin faylı');
  assert.deepEqual(await run('ru', () => ok()), ['data/latest.ru.json']);
  assert.deepEqual(await run(null, () => ok()), ['data/latest.json'], '«Hamısı» ümumi faylı çəkir');
  assert.deepEqual(await run('az', () => ok(), {checkedAt: 'x'}), ['data/latest.json'], 'kanal dil fayllarını bildirməyibsə (köhnə pipeline) ümumi fayl');
  assert.deepEqual(await run('az', url => url.includes('latest.az') ? {ok: false, status: 404, headers: new Headers()} : ok()), ['data/latest.az.json', 'data/latest.json'], 'dil faylı alınmasa ümumi fayl');
  assert.deepEqual(await run('az', url => url.includes('latest.az') ? ok({'X-8ulduz-data': 'cache'}) : ok()), ['data/latest.az.json', 'data/latest.json'], 'keşdən gələn dil faylı canlı kanalın yoxluğudur: ümumi fayl soruşulur');
  const src = fs.readFileSync(path.join(root, 'assets/app.js'), 'utf8');
  assert.ok(src.includes('LIVE_FILE = /^data\\/(?:status|latest(?:\\.[a-z]{2})?|markets)\\.json/'), 'service worker-siz ziyarətçi də dil faylını dəqiqəlik kanaldan oxuyur');
  const sw = fs.readFileSync(path.join(root, 'sw.js'), 'utf8');
  assert.ok(sw.includes('latest(?:\\.[a-z]{2})?|markets'), 'sw.js dil faylını canlı kanaldan verir');
  const pipeline = fs.readFileSync(path.join(root, '.github/scripts/pipeline.sh'), 'utf8');
  assert.ok(pipeline.includes('for name in status latest latest.az latest.en latest.ru latest.tr markets'), 'push_live dil fayllarını yazır');
  assert.ok(pipeline.includes('rm -f "$REPO_DIR"/data/latest.??.json'), 'main-ə yazılmır: tarixçə şişməsin');
  assert.ok(pipeline.includes('export LATEST_LANG_FILES=1'), 'status.json bayrağı yalnız yeni pipeline ilə');
});
test('red line 3: the full feed is asked per language when status offers it, «Hamısı» merges every file, Azerbaijani always gets news.json', async () => {
  const run = async (lang, answer, status = {checkedAt: 'x', newsLangs: ['en', 'ru', 'tr']}) => {
    const ctx = app({navigator: {onLine: true, serviceWorker: {controller: {}}}}), {S} = ctx.api, urls = [];
    S.lang = lang; S.status = status; S.og = {};
    ctx.fetch = async url => { const name = url.split('?')[0]; urls.push(name); return answer(name); };
    await ctx.api.loadNews(true);
    return {urls, S};
  };
  const row = (id, lang) => ({id, title: 'Xəbər başlığı ' + id, category: 'gundem', lang, source: 'APA', sourceUrl: 'https://apa.az/' + id, publishedAt: new Date().toISOString()});
  const ok = (rows, extra = {}) => ({ok: true, headers: new Headers(extra), json: async () => ({updatedAt: 'x', articles: rows})});
  assert.deepEqual((await run('az', () => ok([]))).urls, ['data/news.json'], 'azərbaycanca oxucu həmişə news.json (azərbaycanca + xarici idman)');
  assert.deepEqual((await run('en', () => ok([]))).urls, ['data/news.en.json'], 'yalnız öz dilinin faylı');
  assert.deepEqual((await run('en', () => ok([]), {checkedAt: 'x'})).urls, ['data/news.json'], 'bayraq yoxdursa (köhnə pipeline) ümumi fayl');
  assert.deepEqual((await run('ru', name => name.endsWith('news.ru.json') ? {ok: false, status: 404, headers: new Headers()} : ok([]))).urls, ['data/news.ru.json', 'data/news.json'], 'dil faylı alınmasa ümumi fayl');
  const files = {'data/news.json': [row('a', 'az'), row('s', 'ru')], 'data/news.en.json': [row('e', 'en')], 'data/news.ru.json': [row('s', 'ru'), row('r', 'ru')], 'data/news.tr.json': [row('t', 'tr')]};
  const all = await run(null, name => ok(files[name], {etag: name}));
  assert.deepEqual([...all.urls].sort(), Object.keys(files).sort(), '«Hamısı» bütün faylları çəkir');
  assert.deepEqual([...all.S.rawNews.map(a => a.id)].sort(), ['a', 'e', 'r', 's', 't'], 'hər dil gəlir, eyni keçid bir dəfə');
  assert.equal(all.S.etag.split('|').length, 4, 'etiket bütün faylların birləşməsidir');
  const first = await run('en', name => name.endsWith('status.json') ? {ok: true, headers: new Headers(), json: async () => ({checkedAt: 'x', newsLangs: ['en', 'ru', 'tr']})} : ok([]), null);
  assert.deepEqual(first.urls, ['data/status.json', 'data/news.en.json'], 'status hələ yoxdursa (ilk açılış) əvvəl o soruşulur');
  const src = fs.readFileSync(path.join(root, 'assets/app.js'), 'utf8');
  assert.ok(src.includes('if (!S.lang) loadNews(true);'), '«Hamısı»ya keçəndə başqa dillərin faylları gəlir');
  const sw = fs.readFileSync(path.join(root, 'sw.js'), 'utf8');
  assert.ok(sw.includes('news(?:\\.[a-z]{2})?'), 'sw.js dil faylının ilişib-ilişmədiyinə də baxır');
  const pipeline = fs.readFileSync(path.join(root, '.github/scripts/pipeline.sh'), 'utf8');
  assert.ok(pipeline.includes('export NEWS_LANG_FILES=1'), 'bölgü və status.json bayrağı yalnız yeni pipeline ilə');
  assert.ok(!pipeline.includes('news.??.json'), 'dil faylları main-dədir: publish_main onları silmir');
  const index = fs.readFileSync(path.join(root, 'index.html'), 'utf8');
  assert.ok(index.includes('"data/news." + lang + ".json"'), 'index.html ingilis/rus/türk oxucu üçün erkən dil faylını istəyir');
});
test('an update waits while the reader is busy: open video, open popup, typing, or scrolled down',()=>{
  const busy=(selector,extra={})=>{
    const ctx=app({setTimeout:fn=>{fn();return 0;},document:{documentElement:{dataset:{}},addEventListener(){},createElement(){return {};},querySelector:s=>s.includes(selector)?{}:null,...extra},scrollY:0});
    let rendered=0;
    ctx.api.S.data={articles:[]};
    vm.runInContext('render = () => { globalThis.rendered = (globalThis.rendered || 0) + 1; }; renderView = render;',ctx);
    ctx.api.requestRender();
    rendered=ctx.rendered||0;
    return {rendered,pending:ctx.api.S.renderPending};
  };
  assert.deepEqual(busy('#nothing'),{rendered:1,pending:false});
  assert.deepEqual(busy('iframe'),{rendered:0,pending:true});
  assert.deepEqual(busy('altpop'),{rendered:0,pending:true});
  assert.deepEqual(busy('#nothing',{activeElement:{closest:()=>({})}}),{rendered:0,pending:true});
  const ctx=app({scrollY:900});
  ctx.api.requestRender();
  assert.equal(ctx.api.S.renderPending,true);
});
test('phone headings use short names so they fit three rows, screen readers keep the full name',()=>{
  const ctx=app();
  const label=vm.runInContext('navLabel',ctx);
  assert.ok(label({slug:'heyat',label:'Sağlamlıq və həyat'}).includes('nav-s">Sağlamlıq<'));
  assert.ok(label({slug:'heyat',label:'Sağlamlıq və həyat'}).includes('nav-f">Sağlamlıq və həyat<'));
  assert.equal(label({slug:'gundem',label:'Gündəm'}),'Gündəm');
});
test('owner 2026-11-10: opened from the home screen, the phone row shows Gündəm and Dünya again instead of «Ana ekrana»', () => {
  const els = {};
  const doc = { documentElement: { dataset: {} }, addEventListener() {}, createElement() { return {}; }, querySelectorAll() { return []; }, querySelector: s => s === '#nav' ? (els.nav ||= { innerHTML: '' }) : null };
  const ctx = app({ document: doc, requestAnimationFrame: () => 0, matchMedia: q => ({ matches: /standalone|hover:none/.test(q) }) });
  vm.runInContext('renderNav()', ctx);
  const h = els.nav.innerHTML, row = h.split('<details class="nav-more">')[0];
  const phone = [...row.matchAll(/<a href="\/bolme\/([a-z]+)\/" class="[^"]*\bph\b/g)].map(m => m[1]);
  assert.deepEqual(phone, ['gundem', 'idman', 'bolgeler', 'dunya']);
  assert.ok(row.includes('class="nav-inst" data-act="install" hidden>'), 'ana ekranda düymə gizlidir');
  assert.ok(fs.readFileSync(path.join(root, 'assets/app.css'), 'utf8').includes('nav.main .nav-inst,nav.main a.ph:is([href$="gundem/"],[href$="dunya/"]){order:-1}'), 'Gündəm, Dünya qabaqda');
});
test('phone nav: one row of four sections and ☰ that opens every section in a list, then the Telegram line (owner, 2026-11-06)', () => {
  const els = {};
  const doc = { documentElement: { dataset: {} }, addEventListener() {}, createElement() { return {}; }, querySelectorAll() { return []; }, querySelector: s => s === '#nav' ? (els.nav ||= { innerHTML: '' }) : null };
  const ctx = app({ document: doc, requestAnimationFrame: () => 0 }), { S } = ctx.api;
  const html = () => { vm.runInContext('renderNav()', ctx); return els.nav.innerHTML; };
  let h = html();
  const [row, rest] = h.split('<details class="nav-more">');
  const phone = [...row.matchAll(/<a href="\/bolme\/([a-z]+)\/" class="[^"]*\bph\b/g)].map(m => m[1]);
  // sahib 2026-11-07: İdmanın yanında Zuğulba yox, Bölgələr (Zuğulba aşağıda öz blokunda, bağlı başlıq)
  // sahib 2026-11-07 (sonra): «Gündəm sonra Dünya»; «Son dəqiqə» ☰-də (qırmızı zolaq və «Son xəbərlər» onu təkrarlayırdı)
  // sahib 2026-11-10: «Ana ekrana» açıq görünsün, yer yoxdursa Gündəm və Dünya ☰-ə keçsin
  assert.deepEqual(phone, ['idman', 'bolgeler'], 'telefonda sətirdə 2 bölmə + «Ana ekrana» (masaüstü menyu dəyişmir)');
  const list = (rest.split('</details>')[0].match(/<a href="\/bolme\//g) || []).length;
  assert.equal(list, (h.match(/<a href="\/bolme\/[a-z]+\/" class="[^"]*"[^>]*>/g) || []).length - list, '☰ siyahısında bütün bölmələr var');
  assert.ok(rest.includes('<summary aria-label="Bütün bölmələr">☰ Hamısı</summary>'));
  assert.ok(h.includes('<button type="button" class="nav-inst" data-act="install" hidden>'), 'quraşdırma mümkün deyilsə düymə gizlidir');
  assert.ok(row.includes('class="nav-inst"') && !rest.split('</details>')[0].includes('class="nav-inst"'), '«Ana ekrana» sətirdədir, ☰-in içində deyil');
  S.installEvt = {};
  h = html();
  assert.ok(h.includes('class="nav-inst" data-act="install">'), 'Chrome təklif verəndə düymə görünür');
  assert.ok(h.includes('<span class="ni-s">📲 Ana ekrana</span><span class="ni-f">📲 Ana ekrana əlavə et</span>'), 'dar ekranda qısa, 400 px-dən enli ekranda tam yazı');
  assert.ok(h.indexOf('class="nav-tg" href="https://t.me/sekkizulduz_az"') > h.indexOf('</details>'), 'Telegram çağırışı ☰-dan sonra, öz sətrində');
  const css = fs.readFileSync(path.join(root, 'assets/app.css'), 'utf8');
  assert.ok(css.includes('.nav-inst{display:none}nav.main .nav-tg{display:none}'), 'masaüstündə nə düymə, nə çağırış');
  assert.ok(css.includes('nav.main>a:not(.ph,.nav-tg){display:none}'), 'telefonda qalan bölmələr ☰-dadır');
  assert.ok(css.includes('nav.main .nav-more-pop{position:fixed;inset:auto 0 0;') && css.includes('grid-template-columns:1fr 1fr'), 'siyahı aşağıdan, iki sütun alt-alta');
  assert.ok(css.includes('nav.main .nav-tg{display:flex;flex:1 0 100%'), 'çağırış yalnız telefonda, öz sətrində');
  assert.ok(/nav\.main \.nav-inst\{display:inline-flex[^}]*background:var\(--primary\)/.test(css), 'düymə öz rəngində');
});
test('Zuğulba always shows 44 stories: official and state sites first, then others',()=>{
  const ctx=app(),{prezHome,prezBlock}=ctx.api,at=i=>new Date(Date.now()-i*3600e3).toISOString();
  const row=(id,source,i,lang='az')=>({id,source,lang,category:'prezident',title:'Prezident İlham Əliyev xəbəri '+id,sourceUrl:'https://x.az/'+id,publishedAt:at(i)});
  const rows=[...Array.from({length:10},(_,i)=>row('r'+i,'Report',i)),...Array.from({length:60},(_,i)=>row('o'+i,'Axar.az',i)),...Array.from({length:5},(_,i)=>row('p'+i,'Prezident.az',200+i))];
  const out=[...prezHome(rows)];
  assert.equal(out.length,44);
  for(let i=0;i<5;i++)assert.ok(out.some(a=>a.id==='p'+i),'köhnə rəsmi xəbər qalır');
  assert.equal(out.filter(a=>a.source==='Report').length,10,'dövlət saytı digərlərindən əvvəl');
  assert.equal(new Set(out.map(a=>a.id)).size,44,'təkrar yoxdur');
  const few=[...prezHome(rows.slice(0,3),rows)];
  assert.equal(few.length,44,'seçilmiş dildə az olsa da 44');
  const html=prezBlock(out);
  assert.ok(html.includes('Son <b>44</b> xəbər'),'yazı');
  const foreign=[...prezHome([row('r0','Report',1),{...row('y','Axar.az',2),title:'Husilər prezident sarayına zərbələr endirdi'},{...row('f','Sportinfo',3),title:'Fənərbağçanın prezidenti danışdı'}])];
  assert.deepEqual(foreign.map(a=>a.id),['r0'],'yad xəbərlə doldurulmur');
  assert.equal(html.split('<article class="pcard').length-1,44,'44 kartın hamısı');
  assert.ok(!html.includes('<template>'));
  const pics=prezBlock(out.map(a=>({...a,imageUrl:'https://x.az/'+a.id+'.jpg'})));
  assert.equal(pics.split('<article class="pcard').length-1,44,'şəkilli 44 kart');
  assert.equal(pics.split('<img src=').length-1,8,'ilk açılışda yalnız 8 şəkil yüklənir');
  assert.equal(pics.split('<img data-src=').length-1,36,'qalan şəkillər lent sürüşəndə gəlir');
});
const firstRow=id=>({id,title:'Xəbər başlığı '+id,category:'gundem',lang:'az',source:'APA',sourceUrl:'https://apa.az/'+id,publishedAt:new Date().toISOString()});
function firstApp(files){
  const ctx=app(),seen=[];
  ctx.fetch=async url=>{const name=String(url).split('?')[0];seen.push(name);const body=files[name];if(!body)return {ok:false,status:404,headers:new Headers()};return {ok:true,headers:new Headers(),json:async()=>body};};
  vm.runInContext('globalThis.paints=[]; render = () => { paints.push(S.data ? S.data.articles.length + (S.partial ? " ilk" : " tam") : "boş"); }; globalThis.boot = () => { S.firstReady = loadFirst(); return loadNews(); };',ctx);
  return {ctx,seen};
}
test('first screen paints from first.json, the full list is asked after it and replaces it even with the same stamp',async()=>{
  const {ctx,seen}=firstApp({'data/first.json':{updatedAt:'x',articles:[firstRow('a')]},'data/news.json':{updatedAt:'x',articles:[firstRow('a'),firstRow('b')]},'data/og.json':{}});
  await ctx.boot();
  assert.ok(seen.indexOf('data/first.json')<seen.indexOf('data/news.json'));
  assert.equal(ctx.paints[0],'1 ilk');
  assert.equal(ctx.api.S.partial,false);
  assert.equal(ctx.api.S.data.articles.length,2);
});
test('first screen uses its own image list and asks for the whole og file after painting',async()=>{
  const {ctx,seen}=firstApp({'data/first.json':{updatedAt:'x',articles:[firstRow('a')],og:{'https://apa.az/a':'https://apa.az/a.jpg'}},'data/news.json':{updatedAt:'x',articles:[firstRow('a')]},'data/og.json':{}});
  vm.runInContext('const realRender = render; render = () => { globalThis.imageAtPaint ??= S.data.articles[0].imageUrl; realRender(); };',ctx);
  await ctx.boot();
  assert.equal(ctx.imageAtPaint,'https://apa.az/a.jpg');
  assert.ok(seen.indexOf('data/first.json')<seen.indexOf('data/news.json'));
});
test('first screen: without the file the full list still loads',async()=>{
  const {ctx}=firstApp({'data/news.json':{updatedAt:'x',articles:[firstRow('a'),firstRow('b')]},'data/og.json':{}});
  await ctx.boot();
  assert.equal(ctx.api.S.data.articles.length,2);
  assert.ok(!ctx.api.S.partial);
  assert.equal(ctx.paints[0],'2 tam');
});
// 2026-11-06 (sahib: sürət birinci qırmızı xəttdir): bölmə keçidi də ilk lentlə açılır (aşağıdakı test); qalan səhifələr, dillər və axtarış tam lenti gözləyir.
test('first screen: other pages and languages wait for the full list, a short list is never shown',async()=>{
  for(const set of ["location.hash='#/bolme/valyuta'","location.hash='#/menbeler'","location.hash='#/bolme/idman';S.lang='ru'","S.lang='ru'","S.q='neft'"]){
    const {ctx,seen}=firstApp({'data/first.json':{updatedAt:'x',articles:[firstRow('a')]},'data/news.json':{updatedAt:'x',articles:[firstRow('a'),firstRow('b')]},'data/og.json':{}});
    vm.runInContext(set,ctx);
    await ctx.boot();
    assert.ok(!seen.includes('data/first.json'),set);
    assert.equal(ctx.paints[0],'2 tam',set);
  }
});
test('speed: a section link (Telegram, Facebook) paints from the first list, then the full list replaces it',async()=>{
  const {ctx,seen}=firstApp({'data/first.json':{updatedAt:'x',articles:[firstRow('a')]},'data/news.json':{updatedAt:'x',articles:[firstRow('a'),firstRow('b')]},'data/og.json':{}});
  vm.runInContext("location.hash='#/bolme/gundem'",ctx);
  await ctx.boot();
  assert.ok(seen.indexOf('data/first.json')>=0 && seen.indexOf('data/first.json')<seen.indexOf('data/news.json'),'kiçik fayl əvvəl (birbaşa keçid telefonda 3–6 s gözləyirdi)');
  assert.equal(ctx.paints[0],'1 ilk');
  assert.equal(ctx.api.S.partial,false,'sonra tam lent');
});
test('speed: a section absent from the first list shows the skeleton, never «no news»; league and team pages do not wait for the feed',()=>{
  const ctx=app(),{S,sectionView}=ctx.api;
  S.partial=true;S.data={articles:[firstRow('a')]};S.og={};S.archive={};
  const html=sectionView('medeniyyet');
  assert.ok(html.includes('class="skel"') && !html.includes('hələ xəbər yoxdur'));
  const src=fs.readFileSync(path.join(root,'assets/app.js'),'utf8');
  assert.ok(src.includes('const shared = r.name === "team" || r.name === "article"'),'liqa birbaşa keçidi 7,5 s lent gözləyirdi');
});
test('first screen: if the full list fails the reader keeps the first screen and sees the error',async()=>{
  const {ctx}=firstApp({'data/first.json':{updatedAt:'x',articles:[firstRow('a')]},'data/og.json':{}});
  await ctx.boot();
  assert.equal(ctx.api.S.partial,true);
  assert.ok(ctx.api.S.error);
  assert.equal(ctx.api.S.data.articles.length,1);
});
test('first screen stops under the latest list: sections arrive with the full list, breaking alerts wait for it too',()=>{
  const ctx=app(),{S,homeView,publishNews}=ctx.api;
  let alerts=0;
  vm.runInContext('checkBreaking = () => { globalThis.alerts = (globalThis.alerts || 0) + 1; };',ctx);
  S.rawNews=[firstRow('a'),firstRow('b')];S.rawMeta={};S.partial=true;S.lang='az';
  publishNews();
  assert.equal(ctx.alerts,undefined,'qısa siyahı bildiriş yaddaşını korlamasın');
  const short=homeView();
  S.partial=false;
  publishNews();
  assert.equal(ctx.alerts,1);
  const full=homeView();
  assert.ok(!short.includes('service-panel')&&full.includes('service-panel'));
  assert.ok(full.startsWith(short),'yuxarı hissə eynidir');
});
test('a story whose link is dead leaves the screen within a minute, moves to another source, and returns when fixed',async()=>{
  const ctx=app(),{S}=ctx.api;
  const main=firstRow('a'),other={...firstRow('b'),alts:[{source:'Report',sourceUrl:'https://report.az/b',title:'Report başlığı',publishedAt:new Date().toISOString()}]},plain=firstRow('c');
  let dead=[];
  ctx.fetch=async()=>({ok:true,headers:new Headers(),json:async()=>({updatedAt:'x',articles:[],dead})});
  vm.runInContext('requestRender = () => { globalThis.redrawn = (globalThis.redrawn || 0) + 1; };',ctx);
  S.rawNews=[main,other,plain];S.rawMeta={};S.lang='az';
  ctx.api.publishNews();
  dead=['https://apa.az/a','https://apa.az/b'];
  await ctx.loadLatest();
  const urls=()=>[...S.data.articles].map(a=>a.sourceUrl).sort();
  assert.deepEqual(urls(),['https://apa.az/c','https://report.az/b']);
  assert.equal(S.data.articles.find(a=>a.sourceUrl==='https://report.az/b').title,'Report başlığı');
  assert.equal(ctx.redrawn,1);
  await ctx.loadLatest();
  assert.equal(ctx.redrawn,1,'dəyişiklik yoxdursa ekrana toxunulmur');
  dead=[];
  await ctx.loadLatest();
  assert.deepEqual(urls(),['https://apa.az/a','https://apa.az/b','https://apa.az/c']);
});
test('language order: Azerbaijani, Turkish, Russian, English',()=>{
  const ctx=app();
  assert.deepEqual(Array.from(vm.runInContext('LANGS.map(l=>l.code)',ctx)),['az','tr','ru','en']);
});
test('speed red line: the waiting redraw runs as soon as the files have arrived',()=>{
  const ctx=app();
  vm.runInContext('render = () => { globalThis.rendered = (globalThis.rendered || 0) + 1; }; renderView = render; flush = flushRender;',ctx);
  const {S,requestRender}=ctx.api;
  S.data={articles:[]};S.firstRenderAt=Date.now();
  requestRender();
  assert.equal(ctx.rendered||0,0);
  ctx.flush();
  assert.equal(ctx.rendered,1);
  ctx.flush();
  assert.equal(ctx.rendered,1,'gözləyən çəkiliş yoxdursa heç nə etmir');
});
test('light theme: on phones the slider text sits on the photo, so «Dinlə» and «N mənbə» keep dark-theme colors (owner 2026-11-08: «işıqlı temada seçilmir slayderdə»)', () => {
  const css = fs.readFileSync(path.join(root, 'assets/app.css'), 'utf8').replace(/\r\n/g, '\n');
  const m = css.match(/@media\(max-width:900px\)\{:root\[data-theme=light\] \.hero-main \.share\[data-act=dinle\]\{([^}]*)\}:root\[data-theme=light\] \.hero-main \.bd\.out\{([^}]*)\}\}/);
  assert.ok(m, 'işıqlı tema slayder qaydası yoxdur');
  const gold = css.match(/:root\{[^}]*--primary:(#[0-9a-f]+)/)[1];
  assert.ok(m[1].includes(`color:${gold}`) && m[1].includes(`border-color:${gold}`), 'Dinlə qaranlıq temanın qızılı rəngində');
  assert.ok(/color:#fff/.test(m[2]) && /background:#000/.test(m[2]), '«N mənbə» ağ yazı, tünd fon (açıq fotoda da oxunur)');
  assert.ok(!/@media\(min-width:901px\)[^@]*data-theme=light\] \.hero-main \.share/.test(css), 'masaüstündə yazı şəkil üstündə deyil: rəng dəyişmir');
});
test('speed red line: the page code stays within its size limit',()=>{
  // Ölçü yayımdakı kimi (LF): Windows-da CRLF ilə açılan nüsxə hər sətirə bir bayt artıq olur.
  // Hədd oxucuya gedən kiçildilmiş nüsxəyədir (sahib 2026-11-08: 170 000; əvvəl mənbə app.js-ə 220 000): mənbədəki şərh telefona getmir.
  const size=p=>Buffer.byteLength(fs.readFileSync(path.join(root,p),'utf8').replace(/\r\n/g,'\n'));
  const B=require('./budce.json'); // büdcələr bir yerdə (sahib, 2026-11-09)
  assert.ok(size('assets/app.min.js')<B.kod['app.min.js'],'app.min.js '+size('assets/app.min.js')+' ≥ '+B.kod['app.min.js']+' (tests/budce.json)');
  assert.ok(size('assets/app.css')<B.kod['app.css'],'app.css '+size('assets/app.css')+' ≥ '+B.kod['app.css']+' (tests/budce.json)');
});
test('speed red line: the minified code is built from the current app.js and renders every page the same',async()=>{
  const {build,SRC,OUT}=require('../.github/kicilt/kicilt.cjs');
  const want=await build(fs.readFileSync(path.join(root,SRC),'utf8'));
  assert.ok(fs.readFileSync(path.join(root,OUT),'utf8').replace(/\r\n/g,'\n')===want,`${OUT} köhnədir: node .github/kicilt/kicilt.cjs işlədin`);
  // Eyni an, eyni lent: kiçildilmiş kod mənbə ilə hərfbəhərf eyni HTML verməlidir (terser-in sıxması bir şeyi dəyişsə burada görünür).
  const T=Date.parse('2026-11-08T10:00:00Z');
  class D extends Date{constructor(...a){super(...(a.length?a:[T]));} static now(){return T;}}
  const j=f=>{try{return JSON.parse(fs.readFileSync(path.join(root,'data',f),'utf8'));}catch{return null;}};
  const files={data:j('news.json'),sports:j('sports.json'),video:j('video.json'),markets:j('markets.json')?.items,social:j('social.json'),ads:j('ads.json'),sources:j('sources.json'),status:j('status.json')};
  const pages=file=>{
    // decode() <textarea> ilə açır: test mühitində sadə əvəzi (hər iki kod üçün eyni), yoxsa «&» olan başlıqda axtarış düşür.
    const ent={amp:'&',lt:'<',gt:'>',quot:'"','#39':"'"},document={documentElement:{dataset:{}},addEventListener(){},querySelector(){return null;},
      createElement:()=>({set innerHTML(v){this.value=String(v).replace(/&(amp|lt|gt|quot|#39);/g,(m,e)=>ent[e]);}})};
    const ctx=app({Date:D,document},file),{S}=ctx.api;
    S.lang=null;S.og={};Object.assign(S,JSON.parse(JSON.stringify(files)));
    const id=S.data.articles[0]?.id,run=code=>{try{return vm.runInContext(tr(code,file),ctx);}catch(e){return 'xəta: '+e.constructor.name;}};
    const out={home:run('homeView()'),shell:JSON.stringify(shellParts(file)),skel:run('skeleton("")'),saved:run('savedView()'),art:run(`articleView(${JSON.stringify(id)})`),video:run('videosView()'),rates:run('ratesView()')};
    for(const s of ['gundem','siyaset','idman','dunya','iqtisadiyyat','bolgeler','video'])out[s]=run(`sectionView(${JSON.stringify(s)})`);
    S.q='Bakı';run('loadArchive=()=>{}');out.search=run('searchView()');
    return out;
  };
  const a=pages(SRC),b=pages(OUT);
  assert.ok(a.home.length>20e3&&!a.home.startsWith('xəta'),'mənbə baş səhifəni çəkir');
  for(const k of Object.keys(a))assert.ok(a[k]===b[k],`${k}: kiçildilmiş kod fərqli HTML verir`);
  for(const k of Object.keys(a))assert.ok(!String(a[k]).startsWith('xəta')&&String(a[k]).length>(k==='skel'?50:200),`${k}: səhifə həqiqətən çəkilir (ad cədvəli səhv olsa hər iki tərəf eyni «xəta» verə bilməz, amma boş müqayisə də olmasın)`);
  // qısa adlar brauzerin öz adlarını örtmür və «applyPrefs();» sərhədi yerindədir
  const {names}=require('../.github/kicilt/kicilt.cjs').buildSync(fs.readFileSync(path.join(root,SRC),'utf8'));
  assert.ok(Object.keys(names).length>400&&names.homeView&&names.homeView.length<=3&&!names.applyPrefs,'yuxarı adlar qısalır, applyPrefs qalır');
  for(const g of ['document','window','fetch','location','history','navigator','scrollTo','caches','crypto','performance','localStorage','top','name','open','close','event','status','self','parent','origin','length'])assert.ok(!Object.values(names).includes(g),`«${g}» qısa ad kimi işlədilmir`);
});
test('speed red line: files arriving together cause one redraw, not one each',async()=>{
  const ctx=app();
  vm.runInContext('render = () => { globalThis.rendered = (globalThis.rendered || 0) + 1; }; renderView = render;',ctx);
  const {S,requestRender}=ctx.api;
  requestRender();
  await new Promise(r=>setTimeout(r,450));
  assert.equal(ctx.rendered||0,0,'xəbər yoxdursa çəkilmir, birinci çəkiliş hamısını götürür');
  S.data={articles:[]};
  for(let i=0;i<8;i++)requestRender(i%2===0);
  await new Promise(r=>setTimeout(r,500));
  assert.equal(ctx.rendered,1);
});
test('speed red line: far sections of the home page are kept out of the page until needed',()=>{
  const ctx=app(),{S,homeView}=ctx.api,at=new Date().toISOString();
  S.lang=null;S.og={};S.data={articles:Array.from({length:30},(_,i)=>({id:String(i),title:'Xəbər başlığı nömrə '+i,category:i%2?'siyaset':'iqtisadiyyat',lang:'az',source:'APA',sourceUrl:'https://apa.az/'+i,publishedAt:at}))};
  const page=homeView();
  assert.ok(page.includes('<div class="lazy-sec" data-lazy="'),'bölmələr səhifə sətrində deyil, açarlı qutudadır (lazyHtml)');
  assert.ok(!page.includes('Bütün xəbərlər'),'bölmənin məzmunu səhifə sətrinə girmir (şablon təhlili kiçilir)');
  assert.ok(vm.runInContext('[...lazyHtml.values()].join("")',ctx).includes('Bütün xəbərlər'),'məzmun lazyHtml-dədir, yaxınlaşanda qurulur');
});
test('home: a section with a multi-source story is kept whole (owner 2026-11-08: the AZƏRTAC title fell out of the Gündəm strip, its picture stayed behind)',()=>{
  const ctx=app(),{S,homeView}=ctx.api,at=new Date().toISOString();
  S.lang=null;S.og={};S.data={articles:Array.from({length:30},(_,i)=>({id:(i+'').padStart(16,'a'),title:'Xəbər başlığı nömrə '+i,category:i%2?'gundem':'siyaset',lang:'az',source:'AZƏRTAC',sourceUrl:'https://azertag.az/'+i,imageUrl:'https://azertag.az/'+i+'.jpg',publishedAt:at,alts:[{source:'APA',sourceUrl:'https://apa.az/'+i}]}))};
  const page=homeView(),lazy=vm.runInContext('lazyHtml',ctx);
  const secs=[...page.matchAll(/<div class="lazy-sec" data-lazy="([^"]+)"><\/div>/g)].map(m=>lazy.get(m[1]));
  assert.ok(secs.length&&secs.every(Boolean)&&secs.some(h=>h.includes('class="altpop"')),'bölmədə çox mənbəli xəbər var (HTML lazyHtml-dədir)');
  for(const h of secs){assert.ok(h.endsWith('</section>'),'bölmə tam götürülür: '+h.slice(-60));assert.equal((h.match(/<article/g)||[]).length,(h.match(/<\/article>/g)||[]).length);}
  assert.ok(!/lazy-sec"><template>/.test(page),'bölmənin HTML-i səhifə sətrində deyil');
});
test('video: every video has Paylaş with the site link, a shared link opens that video first (owner 2026-11-08: «videolarda paylaş yoxdur»)',()=>{
  const ctx=app(),{S}=ctx.api;
  S.og={};S.video={items:[{videoId:'abcDEF12345',channel:'ARB 24',title:'Birinci video',imageUrl:'https://i.ytimg.com/a.jpg'},{videoId:'xyz_-987654',channel:'Report',title:'İkinci',imageUrl:''}]};
  let html=vm.runInContext('videosView()',ctx);
  assert.equal((html.match(/data-act="share"/g)||[]).length,2);
  assert.ok(html.includes('data-share="https://8ulduz.az/#/videolent?v=abcDEF12345"')&&!html.includes('youtube.com/watch'),'YouTube yox, saytın keçidi');
  assert.ok(html.includes('data-title="İkinci"'),'paylaşılan mətndə videonun adı');
  assert.ok(!/<button[^>]*class="yt"/.test(html),'düymənin içində düymə olmur');
  ctx.location.hash='#/videolent?v=xyz_-987654';
  html=vm.runInContext('videosView()',ctx);
  assert.ok(html.indexOf('data-yt="xyz_-987654"')<html.indexOf('data-yt="abcDEF12345"'),'paylaşılan video birinci');
  assert.ok(!html.includes('<iframe'),'oynadıcı açılışda yüklənmir (ağırdır, ekranın yenilənməsini saxlayır)');
  ctx.location.hash='#/videolent?v=unknownVid1';
  html=vm.runInContext('videosView()',ctx);
  assert.ok(html.indexOf('data-yt="unknownVid1"')<html.indexOf('data-yt="abcDEF12345"')&&html.includes('i.ytimg.com/vi/unknownVid1/hqdefault.jpg'),'lentdən çıxmış video da birinci, şəkli ilə');
  ctx.location.hash='#/';
  const block=vm.runInContext(`unifiedVideo([{id:'a'.repeat(16),title:'Video xəbər',source:'Axar.az',sourceUrl:'https://axar.az/1',imageUrl:'https://axar.az/1.jpg',publishedAt:new Date().toISOString(),category:'gundem',video:true,lang:'az'}])`,ctx);
  assert.equal((block.match(/data-yt=/g)||[]).length,2);
  assert.ok(/class="card vcard/.test(block)&&block.includes('data-act="dinle"')&&(block.match(/data-act="share"/g)||[]).length===3,'video xəbərdə də Dinlə və Paylaş');
});
test('speed red line: images are resized and the original stays as the fallback',()=>{
  const ctx=app(),{S,sized,img,card}=ctx.api;
  S.og={};
  const url='https://apa.az/a b.jpg';
  assert.equal(sized(url,480),'https://wsrv.nl/?url='+encodeURIComponent(url)+'&w=480&we&output=webp&q=70');
  assert.equal(sized('https://apa.az/a.svg',480),'https://apa.az/a.svg');
  assert.equal(sized('https://apa.az/a.gif?x=1',480),'https://apa.az/a.gif?x=1');
  assert.equal(sized('https://metbuat.az/a.jpg',480),'https://metbuat.az/a.jpg','wsrv 404 verən sayt birbaşa');
  assert.equal(sized('https://cdn.sporx.com/a.jpg',480),'https://cdn.sporx.com/a.jpg');
  assert.ok(sized('https://files.modern.az/a.jfif',320).includes('wsrv.nl'),'jfif kiçildilir');
  const html=img({imageUrl:'https://apa.az/a.jpg',category:'gundem'});
  assert.ok(html.includes('wsrv.nl'));
  assert.ok(html.includes('data-image-alternatives="[&quot;https://apa.az/a.jpg&quot;]"'),'alınmasa əsl ünvan');
  assert.ok(!html.includes('image-fallback'),'şəkli olan kartda ehtiyat loqo yoxdur');
  assert.equal(img({category:'gundem'}),'','şəkli olmayanda qutu yoxdur');
  const bare=card({id:'1',title:'Başlıq',category:'gundem',source:'APA',sourceUrl:'https://apa.az/1',publishedAt:new Date().toISOString()});
  assert.ok(bare.includes('class="card noimg"') && !bare.includes('<img') && !bare.includes('<p'),'şəkilsiz kart yalnız mətndir, xülasə yoxdur');
  assert.ok(bare.includes('target="_blank"'),'kart mənbəni yeni vərəqədə açır');
  const eager=img({imageUrl:'https://apa.az/a.jpg',category:'gundem'},'',true,true,828,false);
  assert.ok(eager.includes('fetchpriority="high"') && !eager.includes('loading="lazy"'),'slayderin ilk şəkli dərhal yüklənir');
  assert.ok(img({imageUrl:'https://apa.az/a.jpg'},'',false,true,828,true).includes('data-src='),'uzaq slayd sonra yüklənir');
  assert.ok(img({imageUrl:'https://apa.az/a.jpg'}).includes('loading="lazy"') && img({imageUrl:'https://apa.az/a.jpg'}).includes('decoding="async"'));
  S.proxyFails=8;
  assert.equal(sized(url,480),url,'xidmət işləmirsə birbaşa mənbədən');
});
test('phone cards also open the source in a new tab', () => {
  const ctx = app({ matchMedia: q => ({ matches: String(q).includes('hover:none') }) });
  const at = new Date().toISOString();
  const html = ctx.api.card({ id: '1', title: 'Başlıq', category: 'gundem', source: 'APA', sourceUrl: 'https://apa.az/1', publishedAt: at, imageUrl: 'https://apa.az/a.jpg' });
  assert.ok(html.includes('target="_blank" rel="noopener noreferrer"'));
});
test('Turkish home still lists stories and does not leave Zuğulba at zero', () => {
  const ctx = app(), { S, homeView } = ctx.api;
  const at = new Date().toISOString();
  const tr = (id) => ({ id, title: 'Türkiye haberi ' + id, lang: 'tr', category: 'dunya', source: 'CNN Türk', sourceUrl: 'https://cnnturk.com/' + id, publishedAt: at, imageUrl: 'https://img.example/' + id + '.jpg' });
  S.lang = 'tr'; S.og = {};
  S.data = { articles: [...Array.from({ length: 10 }, (_, i) => tr('t' + i)), { id: 'p', title: 'Prezident İlham Əliyev qəbul edib', lang: 'az', category: 'prezident', source: 'Prezident.az', sourceUrl: 'https://president.az/p', publishedAt: at }] };
  const html = homeView();
  assert.ok(html.includes('class="pcard'), 'Zuğulba boş qalmır');
  assert.ok(!html.includes('Son <b>0</b>'));
  const latest = html.slice(html.indexOf('latest-grid'), html.indexOf('</section>', html.indexOf('latest-grid')));
  assert.ok((latest.match(/<article/g) || []).length >= 1, 'Son xəbərlər doludur');
  assert.ok(!html.includes('image-fallback') && !html.includes('logo-80'), 'şəkilsiz yerdə loqo bloku yoxdur');
});
test('a broken secondary block cannot freeze the news list',()=>{
  const ctx=app(),{S,homeView}=ctx.api;
  const at=new Date().toISOString();
  S.data={articles:[{id:'1',title:'Bakıda yeni park açılıb bu gün',category:'gundem',lang:'az',source:'APA',sourceUrl:'https://apa.az/1',publishedAt:at}]};
  S.football={leagues:[{results:[{home:'A',away:'B'}]}]};
  const html=homeView();
  assert.ok(html.includes('apa.az/1'));
});
test('a full reload keeps minute-channel stories and does not count them twice',async()=>{
  const ctx=app(),{S,loadNews}=ctx.api;
  const at=new Date().toISOString();
  const row=(id,title)=>({id,title,category:'gundem',lang:'az',source:'APA',sourceUrl:'https://apa.az/'+id,publishedAt:at});
  S.data={articles:[]};S.og={};S.rawNews=[row('new','Dəqiqəlik kanaldan gələn tam yeni xəbər')];S.overlay=[{a:S.rawNews[0],at:Date.now()}];
  ctx.fetch=async()=>({ok:true,headers:new Headers(),json:async()=>({updatedAt:'x',articles:[row('old','Tam lentdəki başqa bir köhnə xəbər')]})});
  await loadNews(true);
  assert.deepEqual([...S.rawNews.map(a=>a.id)].sort(),['new','old']);
  S.overlay[0].at=Date.now()-31*60e3;
  ctx.fetch=async()=>({ok:true,headers:new Headers(),json:async()=>({updatedAt:'y',articles:[row('old','Tam lentdəki başqa bir köhnə xəbər')]})});
  await loadNews(true);
  assert.deepEqual([...S.rawNews.map(a=>a.id)],['old'],'yarım saatdan sonra tam lentdə olmalıdır, yoxdursa çıxarılıb');
});
test('sport buttons: short list, every topic finds its news in every language, no false friends',()=>{
  const ctx=app(),{clubMatches}=ctx.api;
  const yes=(club,title,extra={})=>assert.equal(clubMatches({title,...extra},club),true,club+': '+title);
  const no=(club,title,extra={})=>assert.equal(clubMatches({title,...extra},club),false,club+': '+title);
  yes('Qarabağ','Qarabağ qalib gəldi');no('Qarabağ','Qarabağ Dirçəliş Fondu QHT-lər üçün qrant müsabiqəsi elan edib');no('Qarabağ','Qarabağ Universitetində yeni fakültə');
  yes('Sabah','"Sabah" səfərdə "Turan Tovuz"a məğlub oldu');yes('Sabah','Dambrauskas "Sabah"ın məğlubiyyətini şərh etdi');no('Sabah','Sabah Şahbuzda işıq olmayacaq');no('Sabah','Oyun sabah başlayır');
  yes('Araz-Naxçıvan','“Araz-Naxçıvan” “Zirə”yə qarşı');no('Araz-Naxçıvan','Araz çayında balıq ovu');
  yes('Galatasaray',"Galatasaray'da yeni transfer");yes('Galatasaray','Super Liqa: "Qalatasaray" darmadağına sevindi');yes('Galatasaray','Защитник «Галатасарая» получил травму');
  yes('Fenerbahçe','Fənərbaxça qalib gəldi');yes('Fenerbahçe','«Фенербахче» уступил');
  yes('Real Madrid','Hazard joins Real Madrid');yes('Real Madrid','Тренер «Реала» объяснил поражение');no('Real Madrid','Реальная угроза для клуба');no('Real Madrid','Real problem in midfield');
  yes('Barcelona','Вратарь «Барселоны» травмирован');yes('Bayern','Игрок «Баварии» забил');yes('Liverpool','«Ливерпуль» обыграл');yes('Man United','Carrick tells Manchester United players');
  no('İnter','International tournament');yes('İnter','«Интер» обыграл');
  yes('Avroliqa','Евролига: результаты матчей');yes('Avroliqa','Avroliqada Fənərbaxça uduzdu');yes('Avroliqa','Dorsey stays',{source:'Eurohoops'});
  yes('NBA','LeBron sinks clutch in NBA');yes('NBA','Лейкерс в НБА');no('NBA','Bakıda basketbol turniri');
  yes('Formula 1','Verstappen penalized',{source:'Motorsport F1'});yes('Formula 1','Formula-1: Hamilton birinci oldu');yes('Formula 1','Льюис Хэмилтон и «Формула-1»'.replace('«Формула-1»','Формула-1'));no('Formula 1','Yeni formula təklif edildi');
  yes('Tennis','Tennisçimiz qalib gəldi');yes('Şahmat','Şahmatçılarımız medal qazandı');yes('Boks və UFC','UFC champion Makhachev');yes('Güləş və cüdo','Cüdoçumuz Avropa çempionu oldu');
  no('İnter','Messi scores twice for Inter Miami');no('Milan','Inter Milan beat Roma');no('Milan','Olimpia Milan wins in EuroLeague');yes('Milan','Pulişiç daha 5 il “Milan”da');
  no('Formula 1','Гран-при России по фигурному катанию');yes('Formula 1','Verstappen wins the Mexico Grand Prix');no('Güləş və cüdo','Ферстаппен: борьба за позицию была жёсткой');yes('Güləş və cüdo','Борец завоевал золото');
  no('Futbol','Real Madrid routs Fenerbahce in Euroleague');no('Futbol','«Барселона» в Евролиге обыграла «Монако»');
  no('Real Madrid','«Реал Бетис» обыграл');yes('Real Madrid','Hazard joins Real Madrid');
  yes('Barcelona','Матч с Барселоной');yes('Bayern','Победа над Баварией');yes('Avroliqa','Перед Евролигой');
  yes('Qarabağ','"Qarabağ"ın futbolçusu bərpa olundu');yes('Milli komanda','Azərbaycan milli komandası qalib gəldi');yes('Milli komanda','Azərbaycan millisinə çağırış');yes('Futbol','Çempionlar Liqasına yollandı');
  const src=fs.readFileSync(path.join(root,'assets/app.js'),'utf8');
  const clubs=src.slice(src.indexOf('const SPORT_TEAMS'),src.indexOf('const CITIES')).match(/name: "/g).length;
  assert.ok(clubs<=35,'düymə sayı: '+clubs);
  yes('Futbol','Galatasaray kazandı');yes('Futbol','Yeni futbol mövsümü');yes('Futbol','Verstappen?',{source:'BBC Futbol'});no('Futbol','Verstappen wins in Mexico');
  yes('Basketbol','Лейкерс в НБА');yes('Basketbol','Basketbolçumuz qalib gəldi');no('Basketbol','Galatasaray kazandı');
});
test('sport shows every language whatever language is chosen, also inside a team',()=>{
  const ctx=app(),{S,sectionView}=ctx.api;
  S.lang='az';
  const at=new Date().toISOString();
  S.data={articles:[['az','Qalatasaray qalib gəldi'],['ru','Галатасарай победил'],['tr','Galatasaray kazandı'],['en','Galatasaray win']].map(([lang,title],i)=>({id:String(i),title,lang,category:'idman',source:'APA Sport',sourceUrl:'https://apasport.az/'+i,publishedAt:at}))};
  for(const club of [null,'Galatasaray']){S.club=club;for(const a of S.data.articles)assert.ok(sectionView('idman').includes(a.title),a.title);}
  S.club='Liverpool';
  assert.ok(sectionView('idman').includes('Bu mövzuda son 5 gündə xəbər tapılmadı'));
});
test('sport sub-sections open their own teams and close when you leave',()=>{
  const ctx=app(),{S,sectionView,subNav}=ctx.api;
  S.data={articles:[]};S.club=null;S.sportTab=null;
  const page=sectionView('idman');
  assert.ok(page.indexOf('data-club="Futbol"')>page.indexOf('</h1>')&&page.indexOf('data-club="Futbol"')<page.indexOf('class="empty"'),'alt başlıqlar səhifə başlığı ilə kartların arasındadır');
  assert.equal(subNav('siyaset'),'');
  const top=subNav('idman');
  for(const name of ['Hamısı','Futbol','Basketbol','Formula 1','Tennis','Şahmat'])assert.ok(top.includes('>'+name+'<'),name);
  assert.ok(!top.includes('data-club="Qarabağ"'),'komandalar bağlıdır');
  S.club='Futbol';S.sportTab='Futbol';S.milli=[{id:'ml-d',name:'Millətlər Liqası D',teams:['Azərbaycan','Litva']},{id:'asiya-kuboku',name:'Asiya Kuboku 2027',teams:['Səudiyyə Ərəbistanı','İraq']}];
  const foot=subNav('idman');
  for(const name of ['Galatasaray','Real Madrid'])assert.ok(foot.includes('data-club="'+name+'"'),name);
  // sahib 2026-11-07 (ikinci qeyd): liqaların yanında «Milli komandalar» — altında ölkələr yox, yarışlar (liqalar kimi)
  assert.ok(!foot.includes('data-club="Milli komanda"')&&foot.includes('href="#/komanda/ml-d"')&&foot.includes('<span>Asiya Kuboku 2027</span>'),'Milli komandalar');
  assert.ok(!foot.includes('href="#/komanda/milli-komandalar/azerbaycan"')&&!foot.includes('>Azərbaycan</a>'),'menyuda ölkə adları yoxdur');
  assert.ok(foot.includes('href="#/komanda/premyer-liqa"'),'Azərbaycan klubları liqadan açılır');
  assert.ok(!foot.includes('data-club="Qarabağ"'));
  assert.ok(!foot.includes('data-club="NBA"'));
  S.club='NBA';S.sportTab='Basketbol';
  const bb=subNav('idman');
  assert.ok(bb.includes('data-club="Avroliqa"'));
  assert.ok(!bb.includes('data-club="Qarabağ"'));
});
test('hover menu: one list for the section, a second list only for a tab with its own items',()=>{
  const ctx=app(),{S,navPopHtml}=ctx.api;
  S.data={articles:[]};S.club=null;S.sportTab=null;
  const closed=navPopHtml('idman',null);
  assert.equal(closed.split('pop-col').length-1,1,'bir siyahı');
  assert.ok(closed.includes('data-club="Futbol"'));
  assert.ok(!closed.includes('class="pill on"'),'başqa səhifədə heç nə seçili görünmür');
  S.milli=[{id:'ml-d',name:'Millətlər Liqası D',teams:['Azərbaycan','Litva']},{id:'asiya-kuboku',name:'Asiya Kuboku 2027',teams:['Səudiyyə Ərəbistanı','İraq']}];
  const football=navPopHtml('idman','Futbol');
  assert.ok(football.includes('pop-col two'),'Futbol ikinci siyahını açır');
  for(const name of ['Galatasaray','Real Madrid'])assert.ok(football.includes('data-club="'+name+'"'),name);
  // Yarışın üstünə gələndə liqa kimi: iştirakçı ölkələr və «cədvəl və komandalar ›»
  const nat=navPopHtml('idman','Futbol','asiya-kuboku');
  for(const [slug,name] of [['seudiyye-erebistani','Səudiyyə Ərəbistanı'],['iraq','İraq']])assert.ok(nat.includes('href="#/komanda/asiya-kuboku/'+slug+'">'+name+'</a>'),name);
  assert.ok(nat.includes('href="#/komanda/asiya-kuboku">Asiya Kuboku 2027: cədvəl və komandalar ›</a>'),'yarışın səhifəsi');
  assert.ok(!(S.sportTab='Futbol',ctx.api.subNav('idman')).includes('>İraq</a>'),'telefonda başlığın altında yarışlar, ölkələr yox');
  S.sportTab=null;
  assert.ok(!football.includes('data-club="Qarabağ"'),'Azərbaycan klubları liqadan açılır');
  assert.ok(football.includes('class="pill on" data-club="Futbol"'));
  assert.ok(!navPopHtml('idman','Tennis').includes('pop-col two'),'siyahısı olmayan başlıq');
  const region=navPopHtml('bolgeler','Qarabağ');
  assert.ok(region.includes('pop-col two')&&region.includes('data-club="Xankəndi"'),'bölgələr də eyni cür açılır');
  const more=navPopHtml('more');
  assert.ok(more.includes('href="#/secilmis"')&&more.includes('href="/bolme/dunya/"'));
  assert.ok(!more.includes('href="/bolme/idman/"'),'menyuda görünən bölmə təkrarlanmır');
});
test('merged sections: old links, old cached stories and saved stories land in the new section',async()=>{
  const ctx=app(),{S,route,publishNews,sectionView,catSection}=ctx.api;
  ctx.location.hash='#/bolme/sehiyye';
  assert.equal(route().slug,'heyat');
  ctx.location.hash='#/bolme/texnologiya';
  assert.equal(route().slug,'tehsil');
  const at=new Date().toISOString();
  S.og={};S.rawMeta={};S.rawNews=[{id:'1',title:'Həkimlər yeni üsul tapdı',category:'sehiyye',lang:'az',source:'APA',sourceUrl:'https://apa.az/1',publishedAt:at},{id:'2',title:'Yeni smartfon təqdim olundu',category:'texnologiya',lang:'az',source:'APA',sourceUrl:'https://apa.az/2',publishedAt:at}];
  publishNews();
  assert.ok(sectionView('heyat').includes('apa.az/1'));
  assert.ok(sectionView('tehsil').includes('apa.az/2'));
  assert.ok(sectionView('heyat').includes('Sağlamlıq və həyat'));
  assert.ok(sectionView('tehsil').includes('Təhsil və elm'));
  assert.ok(sectionView('sehiyye').includes('Bölmə tapılmadı'),'ünvan route-da çevrilir, siyahıda iki başlıq qalmır');
});
test('club filter sees names next to punctuation',()=>{
  const {clubMatches}=app().api;
  for(const title of ['«Qarabağ» qalib gəldi','"Sabah" səfərdə uduzdu: Qarabağ, Neftçi','Oyun (Qarabağ) başa çatdı','Qarabağ: yeni transfer'])assert.equal(clubMatches({title},'Qarabağ'),true,title);
  assert.equal(clubMatches({title:'Qarabağlı alim mükafat aldı'},'Qarabağ'),false);
});
test('saved stories survive a second tab',()=>{
  const memory=new Map();
  const shared={getItem:k=>memory.has(k)?memory.get(k):null,setItem:(k,v)=>memory.set(k,String(v)),removeItem:k=>memory.delete(k)};
  const a=app({localStorage:shared}).api.storage,b=app({localStorage:shared}).api.storage;
  a.setItem('k','bir');
  assert.equal(b.getItem('k'),'bir');
  b.setItem('k','iki');
  assert.equal(a.getItem('k'),'iki');
});
test('notifications use the service worker where the page API is not allowed',async()=>{
  const ctx=app(),{S,showBreaking}=ctx.api,shown=[];
  S.swReg={showNotification:async(title,options)=>{shown.push([title,options]);}};
  await showBreaking({id:'1',title:'Son xəbər',category:'gundem',sourceUrl:'https://apa.az/1'});
  assert.equal(shown[0][0],'Son dəqiqə');
  assert.equal(shown[0][1].data.url,'https://8ulduz.az/#/xeber/1?b=gundem','klik mənbəyə yox, saytın xəbər səhifəsinə aparır');
  assert.deepEqual([shown[0][1].data.id,shown[0][1].data.cat],['1','gundem']);
});
test('a notification click opens the story on the site, in the open page when there is one',async()=>{
  const {listeners,context}=worker();
  const opened=[],messages=[];let focused=0;
  context.self.clients.openWindow=async u=>{opened.push(u);};
  let windows=[];
  context.self.clients.matchAll=async()=>windows;
  const click=data=>{let done;listeners.notificationclick({notification:{close(){},data},waitUntil(p){done=p;}});return done;};
  await click({id:'7',cat:'gundem',url:'https://apa.az/7'});
  assert.deepEqual(opened,['https://example.com/8ulduz/#/xeber/7?b=gundem'],'səhifə açıq deyilsə saytın xəbər səhifəsi açılır (mənbə yox)');
  windows=[{url:'https://example.com/8ulduz/#/',focus:async()=>{focused++;},postMessage:m=>messages.push(m)}];
  await click({id:'8',url:'https://apa.az/8'});
  assert.equal(opened.length,1,'açıq səhifə varsa yeni pəncərə açılmır');
  assert.equal(focused,1);
  assert.equal(JSON.stringify(messages),JSON.stringify([{type:'open-story',id:'8'}]),'açıq səhifəyə xəbərin id-si göndərilir'); // obyekt başqa vm kontekstindəndir
  await click({});
  assert.equal(opened[1],'https://example.com/8ulduz/','id-siz bildiriş baş səhifəni açır');
  await click({id:'on',cat:'',url:'https://example.com/8ulduz/#/xeber/on'});
  assert.equal(opened[2],'https://example.com/8ulduz/','«Bildiriş aktivdir…» nümunəsi xəbər deyil: baş səhifə açılır, «xəbər tapılmadı» səhifəsi yox');
  assert.equal(messages.length,1,'nümunə üçün açıq səhifəyə open-story göndərilmir');
  const src=fs.readFileSync(path.join(root,'assets/app.js'),'utf8');
  assert.ok(src.includes('e.data?.type === "open-story" && e.data.id) { location.hash = detailUrl({ id: e.data.id }); return; }'),'səhifə open-story mesajı ilə xəbər səhifəsinə keçir');
  assert.ok(src.includes('n.onclick = () => { window.focus(); location.hash = detailUrl(a); };'),'səhifə bildirişinin kliki də saytın xəbər səhifəsinə aparır');
});
test('section pages reach back through the archive without repeating or leaking',async()=>{
  const ctx=policyApp(),{S,sectionView,loadArchive}=ctx.api;
  const at=h=>new Date(Date.now()-h*3600e3).toISOString();
  const row=(id,h,source='APA',host='apa.az',title='Məktəblərdə yeni dərs ili başladı')=>({id,title,category:'tehsil',lang:'az',source,sourceUrl:`https://${host}/${id}`,publishedAt:at(h)});
  S.data={articles:[row('now',1)]};
  ctx.fetch=async()=>({ok:true,headers:new Headers(),json:async()=>({articles:[row('now',1),row('old',50),row('bad',40,'Azadlıq','azadliq.org')]})});
  await loadArchive('tehsil');
  const html=sectionView('tehsil');
  assert.ok(html.includes('apa.az/old'),'köhnə xəbər');
  assert.equal(html.split('apa.az/now').length-1>=1,true);
  assert.ok(html.indexOf('apa.az/now')<html.indexOf('apa.az/old'),'ən yeni üstdə');
  assert.ok(!html.includes('azadliq'),'qayda arxivə də tətbiq olunur');
  await loadArchive('prezident');
  assert.equal(S.archive.prezident,undefined);
});

test('the real university foundation copies occupy one card after merging the archive',()=>{
  const fixture=JSON.parse(fs.readFileSync(path.join(__dirname,'fixtures/education-duplicates.json'),'utf8'));
  const ctx=policyApp(),{S,withArchive}=ctx.api;
  const other={...fixture.live[0],id:'other',sourceUrl:'https://apa.az/different-school',title:'Şuşada başqa məktəb binasının açılışı keçirildi',alts:[]};
  const live=[...fixture.live,other];
  S.data={articles:live};S.archive={tehsil:{at:Date.now(),rows:fixture.groupedArchive}};
  const before=JSON.stringify([live,S.archive]);
  const result=withArchive('tehsil',live);
  assert.equal(result.length,2,'təməlqoyma + ayrıca məktəb açılışı');
  const card=result.find(x=>x.sourceUrl!==other.sourceUrl);
  const expected=new Set(fixture.groupedArchive.flatMap(a=>[a,...a.alts||[]]).map(x=>x.source));
  assert.deepEqual(new Set([card,...card.alts].map(x=>x.source)),expected,'hər mənbə bir dəfə qalır');
  assert.equal(JSON.stringify([live,S.archive]),before,'arxiv lentin özünü dəyişmir');
});

test('an archive group joins both existing groups through their actual article links',()=>{
  const {S,withArchive}=app().api,at=new Date().toISOString();
  const row=(source,url,title)=>({source,sourceUrl:url,title,publishedAt:at});
  const a=row('APA','https://apa.az/a','Birinci başlıq tam fərqlidir');
  const b=row('Report','https://report.az/b','İkinci başlıq başqa formada yazılıb');
  const c={...row('AZƏRTAC','https://azertag.az/c','Hadisənin arxivdəki başlığı'),alts:[a,b]};
  S.archive={tehsil:{rows:[c,{...b,sourceUrl:'https://www.report.az/b'}]}};
  const result=withArchive('tehsil',[a,b]);
  assert.equal(result.length,1,'sondan gələn qrup əvvəlki iki kartı da birləşdirir');
  assert.equal(new Set([result[0],...result[0].alts].map(x=>x.source)).size,3);
  assert.equal(result[0].alts.length,2,'www nüsxəsi əlavə mənbə sayılmır');
});

test('a story grouped under another category keeps all its sources in the original section',()=>{
  const {S,withArchive}=app().api,at=new Date().toISOString();
  const a={id:'a',title:'Qarabağ Universitetində kitabxananın təməli qoyuldu',category:'tehsil',source:'APA',sourceUrl:'https://apa.az/a',publishedAt:at};
  const official={...a,id:'p',category:'prezident',source:'Prezident.az',sourceUrl:'https://president.az/az/articles/view/12345',alts:[a,{...a,source:'AZƏRTAC',sourceUrl:'https://azertag.az/a'}]};
  S.data={articles:[official]};S.archive={tehsil:{rows:[a]}};
  const cards=withArchive('tehsil',[]);
  assert.equal(cards.length,1,'bölmə əsas kartın kateqoriyası dəyişəndə boşalmır');
  assert.equal(cards[0].source,'Prezident.az','rəsmi mənbə prioriteti qalır');
  assert.equal(cards[0].alts.length,2,'digər kateqoriyadakı mənbələr itmir');
});

test('archive equality respects the 36-hour window and does not guess from a similar subject',()=>{
  const {S,withArchive}=app().api;
  const row=(id,title,h)=>({id,title,source:id,sourceUrl:`https://apa.az/${id}`,publishedAt:new Date(Date.UTC(2026,10,7)-h*3600e3).toISOString()});
  const a=row('a','Qarabağ Universitetində kitabxananın təməli qoyuldu',0);
  S.archive={tehsil:{rows:[row('b',a.title,1),row('c',a.title,40),row('d','Qarabağ Universitetində yeni fakültə yaradıldı',0)]}};
  const result=withArchive('tehsil',[a]);
  assert.equal(result.length,3,'yalnız eyni vaxtdakı eyni başlıq birləşir');
});

test('cached duplicate identities refresh when a story headline, link or date changes',()=>{
  const {S,withArchive}=app().api;
  const a={title:'Qarabağ Universitetində yeni kitabxana yaradıldı',source:'APA',sourceUrl:'https://apa.az/a',publishedAt:'2026-11-07T07:00:00Z'};
  const b={...a,source:'Report',sourceUrl:'https://report.az/b'};
  S.archive={tehsil:{rows:[b]}};
  assert.equal(withArchive('tehsil',[a]).length,1);
  b.title='Şuşada peşə məktəbinin yeni binası açıldı';
  assert.equal(withArchive('tehsil',[a]).length,2,'köhnə başlıq yaddaşda qalmır');
  b.title=a.title;b.publishedAt='2026-11-01T07:00:00Z';
  assert.equal(withArchive('tehsil',[a]).length,2,'tarix pəncərəsi təzədən hesablanır');
  b.sourceUrl=a.sourceUrl;
  assert.equal(withArchive('tehsil',[a]).length,1,'eyni xəbər keçidi başlıq/tarixdən asılı olmadan tanınır');
});

test('a grouped official story uses its news photo rather than the generic administration logo',()=>{
  const {imageCandidates,S}=app().api;
  const logo='https://static.president.az/assets/president-administration-abcd.png';
  S.og={'https://president.az/1':logo};
  const a={sourceUrl:'https://president.az/1',imageUrl:logo,alts:[{imageUrl:'https://apa.az/news-photo.jpg'}]};
  assert.deepEqual(Array.from(imageCandidates(a)),['https://apa.az/news-photo.jpg']);
});

test('league views reuse the same merged sports pool until data, archive or withdrawals change',()=>{
  const ctx=app(),{S,withArchive}=ctx.api;
  const a={id:'live',title:'Qarabağ yeni mövsümə hazırlaşır',source:'APA',sourceUrl:'https://apa.az/live',publishedAt:new Date().toISOString()};
  const b={...a,id:'old',title:'Neftçi məşqlərini davam etdirir',sourceUrl:'https://apa.az/archive'};
  S.data={articles:[a]};S.archive={idman:{rows:[b]}};
  const first=withArchive('idman',S.data.articles);
  assert.equal(withArchive('idman',S.data.articles),first,'cədvəl, xəbərlər və sayğac eyni hazır siyahını işlədir');
  S.archive.idman.rows=[{...b}];
  const second=withArchive('idman',S.data.articles);
  assert.notEqual(second,first,'arxiv yenilənəndə yenidən');
  S.data={articles:[{...a,title:'Qarabağ yeni baş məşqçisini təqdim etdi'}]};
  const third=withArchive('idman',S.data.articles);
  assert.notEqual(third,second,'lent yenilənəndə yenidən');
  vm.runInContext('addRemovals({one:{ids:["old"]}})',ctx);
  const last=withArchive('idman',S.data.articles);
  assert.notEqual(last,third,'geri çəkilmə də yaddaşı etibarsız edir');
  assert.equal(last.length,1);
  assert.equal(last[0].id,'live');
});

test('archive alternatives pass the same source policy as live alternatives',async()=>{
  const ctx=policyApp(),{S,loadArchive}=ctx.api;
  const a={id:'a',title:'Məktəblərdə yeni dərs ili başladı',category:'tehsil',lang:'az',source:'APA',sourceUrl:'https://apa.az/a',publishedAt:new Date().toISOString(),alts:[
    {source:'Azadlıq',sourceUrl:'https://azadliq.org/b'},
    {source:'Report',sourceUrl:'https://report.az/a',title:'Məktəblərdə yeni dərs ili başladı',lang:'az'}]};
  ctx.fetch=async()=>({ok:true,headers:new Headers(),json:async()=>({articles:[a]})});
  await loadArchive('tehsil');
  assert.deepEqual(Array.from(S.archive.tehsil.rows[0].alts,x=>x.source),['Report']);
});
test('an editorial withdrawal hides an old saved story, archive card and shared article immediately', () => {
  const ctx = app(), {S} = ctx.api;
  const row={id:'withdrawn-id',source:'APA',sourceUrl:'https://apa.az/old-title-12345',title:'WITHDRAWN',category:'sosial',publishedAt:new Date().toISOString()};
  S.archive={sosial:{at:Date.now(),rows:[row]}};S.data={articles:[]};S.archiveScan=row.id;S.sharedStory={id:row.id,row};
  ctx.api.storage.setItem('8ulduz-saved',JSON.stringify([row]));
  vm.runInContext(`addRemovals({one:{ids:['withdrawn-id'],urls:['https://apa.az/old-title-12345'],keys:['apa.az#12345']}})`,ctx);
  assert.equal(ctx.api.withArchive('sosial',[]).length,0);
  assert.ok(!ctx.api.articleView(row.id).includes('WITHDRAWN'));
  assert.ok(!ctx.api.savedView().includes('WITHDRAWN'));
  assert.equal(ctx.api.policyViolation({...row,id:'changed',sourceUrl:'https://apa.az/new-title-12345'}),true);
  assert.equal(ctx.api.policyViolation({...row,id:'other',sourceUrl:'https://apa.az/new-title-12346'}),false);
});

function policyApp() {
  const src = fs.readFileSync(path.join(root, 'assets/content-policy.js'), 'utf8');
  return app({CONTENT_POLICY: JSON.parse(src.slice(src.indexOf('{'), src.lastIndexOf('}') + 1))});
}
test('red line 1: polling needs only the small latest file between full refreshes, and new stories appear', async () => {
  const ctx = app(), {S} = ctx.api, urls = [];
  S.data = {articles: []}; S.rawNews = [{id: 'a', title: 'Köhnə xəbər başlığı', sourceUrl: 'https://x.az/a', publishedAt: '2026-10-30T05:00:00Z', lang: 'az'}]; S.rawMeta = {updatedAt: 'x'};
  S.status = {checkedAt: 'old'}; S.newsStamp = 'old'; S.newsCheckedAt = Date.now(); S.og = {};
  ctx.fetch = async url => { urls.push(url); return {ok: true, headers: new Headers(), json: async () => url.includes('status') ? {checkedAt: 'new'}
    : {updatedAt: 'y', articles: [{id: 'b', title: 'Tamamilə yeni başqa xəbər', sourceUrl: 'https://x.az/b', publishedAt: '2026-10-30T06:00:00Z', lang: 'az'}]}}; };
  await ctx.api.pollNews();
  assert.ok(urls.every(u => !u.includes('news.json')));
  assert.equal(S.data.articles.length, 2);
  assert.equal(S.newsStamp, 'new');
  await ctx.api.pollNews();
  assert.equal(urls.filter(u => u.includes('latest.json')).length, 1); // status dəyişməyib
});
test('red line 1: the page checks at least twice a minute', () => {
  const src = fs.readFileSync(path.join(root, 'assets/app.js'), 'utf8');
  assert.ok(Number(src.match(/const POLL_MS = (\d+)e3/)[1]) <= 30);
});
test('red line 2: foreign stories about Azerbaijan, unknown sites and blocked hosts never reach the screen, even from old cache', async () => {
  const ctx = policyApp(), {S} = ctx.api;
  const stamp = new Date().toISOString(), row = (id, source, sourceUrl, title, extra = {}) => ({id, source, sourceUrl, title, lang: 'az', category: 'dunya', publishedAt: stamp, ...extra});
  const articles = [
    row('ok', 'APA', 'https://apa.az/1', 'Bakıda yeni park açıldı'),
    row('world', 'BBC News', 'https://www.bbc.co.uk/1', 'Storm hits northern Europe coast'),
    row('f1', 'BBC News', 'https://www.bbc.co.uk/2', 'Azerbaijan signs a new agreement'),
    row('f2', 'TASS', 'https://tass.ru/2', 'Алиев принял делегацию'),
    row('f3', 'Hürriyet', 'https://hurriyet.com.tr/3', 'Azərbaycan açıklaması geldi'),
    row('f4', 'TASS', 'https://tass.ru/4', 'Алиев поздравил футболистов', {category: 'idman'}),
    row('sport', 'Match TV', 'https://matchtv.ru/5', 'Карабах вышел в плей-офф', {category: 'idman'}),
    row('unknown', 'Yeni Sayt', 'https://yenisayt.az/6', 'Naməlum saytdan başlıq'),
    row('blocked', 'Azadlıq', 'https://www.azadliq.org/7', 'Bloklanmış saytdan başlıq'),
    row('spoof', 'APA', 'https://meydan.tv/8', 'Saxta mənbə adı ilə başlıq'),
  ];
  ctx.fetch = async () => ({ok: true, headers: new Headers(), json: async () => ({updatedAt: 'u', articles})});
  await ctx.api.loadNews();
  assert.deepEqual([...S.data.articles.map(a => a.id)].sort(), ['ok', 'sport', 'world']);
});
test('red line 2: the sport exception is for sport sites, capital letters and links cannot slip through', () => {
  const {api} = policyApp();
  const row = (source, sourceUrl, title, category = 'dunya') => ({source, sourceUrl, title, category, summary: ''});
  assert.equal(api.policyViolation(row('BBC News', 'https://bbc.co.uk/1', 'Azerbaijan to transfer detainees', 'idman')), true);
  assert.equal(api.policyViolation(row('Match TV', 'https://matchtv.ru/1', 'Карабах вышел в плей-офф', 'idman')), false);
  assert.equal(api.policyViolation(row('Match TV', 'https://matchtv.ru/1', 'Алиев поздравил футболистов', 'idman')), true);
  assert.equal(api.policyViolation(row('Hürriyet', 'https://hurriyet.com.tr/1', 'ALİYEV açıklama yaptı')), true);
  assert.equal(api.policyViolation(row('Hürriyet', 'https://hurriyet.com.tr/1', 'Bakırköy\'de kaza')), false);
  assert.equal(api.policyViolation(row('AZƏRTAC', 'javascript://azertag.az/%0aalert(1)', 'Başlıq')), true);
  const story = row('APA', 'https://apa.az/1', 'Azərbaycan Prezidenti qəbul edib', 'siyaset');
  assert.equal(api.altForbidden(story, {source: 'Report', sourceUrl: 'https://report.az/1', title: 'Qəbul'}), false);
  assert.equal(api.altForbidden(story, {source: 'TASS', sourceUrl: 'https://tass.ru/1', title: 'Прием'}), true);
});
test('red line 2: a saved story from a forbidden source is not shown', () => {
  const ctx = policyApp();
  ctx.api.storage.setItem('8ulduz-saved', JSON.stringify([
    {id: 'a', title: 'Yaxşı xəbər başlığı', source: 'APA', sourceUrl: 'https://apa.az/1', category: 'gundem', publishedAt: new Date().toISOString()},
    {id: 'b', title: 'Qadağan saytdan', source: 'Azadlıq', sourceUrl: 'https://www.azadliq.org/1', category: 'gundem', publishedAt: new Date().toISOString()},
  ]));
  const html = ctx.api.savedView();
  assert.ok(html.includes('apa.az/1') && !html.includes('azadliq.org'));
});
test('a bad regular expression in the policy cannot take the whole site down', () => {
  const ctx = app({CONTENT_POLICY: {azSources: {}, worldSources: {}, blockedHosts: [], azTerms: '(', leaderTerms: '('}});
  assert.equal(typeof ctx.api.policyViolation, 'function');
});
test('feed links can only be web addresses', () => {
  const {api} = app();
  assert.equal(api.safeHref('javascript://azertag.az/%0aalert(1)'), '#');
  assert.equal(api.safeHref(' JaVaScRiPt:alert(1)'), '#');
  assert.equal(api.safeHref('data:text/html,x'), '#');
  assert.equal(api.safeHref('https://apa.az/1?a=1&b=2'), 'https://apa.az/1?a=1&amp;b=2');
  const src = fs.readFileSync(path.join(root, 'assets/app.js'), 'utf8');
  assert.ok(!/href="\$\{esc\((?:a|r|s|p|fb)\.[\w.]+/.test(src), 'lent keçidi esc ilə birbaşa yazılmasın');
});
test('app left in background for over an hour reloads on return, short absence only refetches',()=>{
  const ctx=app(),{S}=ctx.api;let reloads=0,polls=0;
  ctx.location.reload=()=>{reloads++;};
  ctx.pollNews=()=>{polls++;};
  ctx.document.hidden=true;ctx.api.resumeNews();
  S.hiddenAt=Date.now()-61*60e3;ctx.document.hidden=false;ctx.api.resumeNews();
  assert.equal(reloads,1);assert.equal(polls,0);
  ctx.document.hidden=true;ctx.api.resumeNews();
  ctx.document.hidden=false;ctx.api.resumeNews();
  assert.equal(reloads,1);assert.equal(polls,1);
});
test('the request index.html started early is used once, later polls fetch again',async()=>{
  const ctx=app();let fetches=0;
  ctx.fetch=async()=>{fetches++;return {ok:true,headers:new Headers(),json:async()=>({n:'net'})};};
  ctx.__early={'data/news.json?t=1':Promise.resolve({ok:true,headers:new Headers(),json:async()=>({n:'early'})})};
  assert.equal((await ctx.api.requestJSON('data/news.json?t=1')).d.n,'early');
  assert.equal(fetches,0);
  assert.equal((await ctx.api.requestJSON('data/news.json?t=1')).d.n,'net');
  ctx.__early={'data/news.json?t=1':Promise.resolve({ok:true,headers:new Headers(),json:async()=>({n:'early'})})};
  assert.equal((await ctx.api.requestJSON('data/news.json?t=2')).d.n,'early','dəqiqə dəyişsə də erkən cavab işlənir');
  ctx.__early={'data/news.json?t=1':Promise.resolve({ok:true,headers:new Headers(),json:async()=>({n:'early'})})};
  assert.equal((await ctx.api.requestJSON('data/news.json?t=2&r=1-1')).d.n,'net','əllə yeniləmə təzəsini istəyir');
  ctx.__early={'data/og.json?t=1':Promise.reject(new Error('offline'))};
  assert.equal((await ctx.api.requestJSON('data/og.json?t=1')).d.n,'net');
});
test('unchanged news still acknowledges a new successful check',async()=>{
  const ctx=app(),{S}=ctx.api;
  S.data={updatedAt:'same',articles:[]};S.status={checkedAt:'new-check'};S.etag='unchanged';
  ctx.fetch=async()=>({ok:true,headers:new Headers({etag:'unchanged'}),json:async()=>({updatedAt:'same',articles:[]})});
  await ctx.api.loadNews();
  assert.equal(S.newsStamp,'new-check');
});

test('basketball national team does not appear in football block', () => {
  const ctx = app();
  ctx.api.S.football = { table: [{ pos: 1, team: 'Qarabağ', pts: 30, p: 10, w: 9, d: 3, l: 0, gf: 20, ga: 5, gd: 15 }], results: [] };
  const html = ctx.api.footballBlock([
    {title: "A Milli Kadın Basketbol Takımı", category: 'idman', publishedAt: '2026-10-26T12:00:00Z'},
    {title: 'Futbol: Qarabağ qalib gəldi', category: 'idman', publishedAt: '2026-10-26T12:00:00Z'},
  ]);
  assert.ok(html.includes('Qarabağ'));
  assert.ok(!html.includes('Basketbol'));
});

test('football block renders results, fixtures and the ordinal round suffix', () => {
  const ctx = app();
  ctx.api.S.football = {
    league: 'Misli Premyer Liqası', season: '2026-2027', roundPlayed: '9', roundNext: '10',
    table: [{ pos: 1, team: 'Qarabağ', pts: 22, p: 9, w: 7, d: 1, l: 1, gf: 18, ga: 6, gd: 12 }],
    results: [{ home: 'Sabah', away: 'Qarabağ', hs: 0, as: 0, date: '2026-10-25T18:00+04:00', played: true }],
    fixtures: [{ home: 'Qəbələ', away: 'Qarabağ', hs: 0, as: 0, date: '2026-10-31T17:30+04:00', played: false }],
    scorers: [{ name: 'Rikardo Apolinario', club: 'Şamaxı', goals: 3 }],
  };
  let html = ctx.api.footballBlock([]);
  assert.ok(html.includes('9-cu'));
  assert.ok(html.includes('10-cu'));
  assert.ok(html.includes('0 : 0'));
  ctx.api.S.fbTab = 'fixtures';
  html = ctx.api.footballBlock([]);
  assert.ok(html.includes('Qəbələ') && html.includes('31 okt'));
  ctx.api.S.fbTab = 'scorers';
  assert.ok(ctx.api.footballBlock([]).includes('3 qol'));
  assert.equal(ctx.api.ordTur(3), '3-cü');
  assert.equal(ctx.api.ordTur(6), '6-cı');
  assert.equal(ctx.api.ordTur(20), '20-ci');
});

test('world leagues appear after the Azerbaijani ones with their own tables', () => {
  const ctx = app();
  ctx.api.S.football = { leagues: [{ project: 1, short: 'Premyer Liqa', league: 'Misli Premyer Liqası', table: [{ pos: 1, team: 'Sabah', pts: 20, p: 9, w: 6, d: 2, l: 1, gf: 15, ga: 7, gd: 8 }], results: [], fixtures: [] }] };
  ctx.api.S.sports = { leagues: [
    { id: 'eng.1', sport: 'football', name: 'Premyer Liqa (İngiltərə)', short: 'İngiltərə', season: '2026/27', asof: '2026-10-31', url: 'https://en.wikipedia.org/wiki/2026%E2%80%9327_Premier_League', groups: [{ name: 'Premier League', rows: [{ pos: 1, team: 'Man City', full: 'Manchester City', logo: '', p: 8, w: 7, d: 0, l: 1, gf: 20, ga: 9, gd: 11, pts: 21, note: 'Champions League', color: '#81D6AC' }] }] },
    { id: 'nba', sport: 'basketball', name: 'NBA', short: 'NBA', season: '2026-27', groups: [{ name: 'Eastern Conference', rows: [{ pos: 1, team: 'Celtics', w: 4, l: 0, p: 4, pct: 1, gb: '-' }] }, { name: 'Western Conference', rows: [{ pos: 1, team: 'Lakers', w: 3, l: 1, p: 4, pct: 0.75, gb: '-' }] }] },
  ] };
  let html = ctx.api.footballBlock([]);
  assert.ok(html.includes('data-fbleague="2"') && html.includes('İngiltərə') && html.includes('NBA'));
  ctx.api.S.fbLeague = 1; ctx.api.S.fbTab = 0;
  html = ctx.api.footballBlock([]);
  assert.ok(html.includes('Man City') && html.includes('Vikipediya') && html.includes('wikipedia.org/wiki/2026') && html.includes('31 oktyabr oyunlarına qədər') && html.includes('<h2>Futbol</h2>'));
  ctx.api.S.fbLeague = 2; ctx.api.S.fbTab = 1;
  html = ctx.api.footballBlock([]);
  assert.ok(html.includes('<h2>Basketbol</h2>') && html.includes('Qərb') && html.includes('Lakers') && !html.includes('Celtics'));
});

test('football block offers every league and keeps the cup without a table', () => {
  const ctx = app();
  ctx.api.S.football = { leagues: [
    { project: 1, short: 'Premyer Liqa', league: 'Misli Premyer Liqası', table: [{ pos: 1, team: 'Sabah', pts: 20, p: 9, w: 6, d: 2, l: 1, gf: 15, ga: 7, gd: 8 }], results: [], fixtures: [] },
    { project: 5, short: 'Kubok', league: 'Azərbaycan Kuboku', elimination: true, table: [], results: [], fixtures: [{ home: 'Şəki', away: 'Qarabağ', hs: 0, as: 0, date: '2026-11-05T15:00+04:00', played: false }] },
  ] };
  let html = ctx.api.footballBlock([]);
  assert.ok(html.includes('data-fbleague="1"') && html.includes('Kubok'));
  ctx.api.S.fbLeague = 1; ctx.api.S.fbTab = 'table';
  html = ctx.api.footballBlock([]);
  assert.ok(html.includes('Azərbaycan Kuboku'));
  assert.ok(!html.includes('fb-table'));        // kubokda cədvəl tabı yoxdur
  assert.ok(html.includes('noteams'));           // komanda kartları yoxdur
  ctx.api.S.fbTab = 'fixtures';
  assert.ok(ctx.api.footballBlock([]).includes('Şəki'));
});

test('football block is hidden while the league table is unavailable', () => {
  const ctx = app();
  ctx.api.S.football = { table: [], events: [{ home: 'Sabah Baku', away: 'Qarabag', hs: '0', as: '0', date: '2026-10-25' }], note: 'yoxdur' };
  assert.equal(ctx.api.footballBlock([{ title: 'Futbol: Qarabağ qalib gəldi', category: 'idman', publishedAt: '2026-10-26T12:00:00Z' }]), '');
});

test('search folds Azerbaijani letters and ignores punctuation', () => {
  const ctx = app();
  assert.equal(ctx.api.fold('İlham Əliyev Qarabağ Şəki Naxçıvan'), 'ilham eliyev qarabag seki naxcivan');
  assert.deepEqual([...ctx.api.searchWords('"Neft", (qaz)! #2026 a')], ['neft', 'qaz', '2026']);
  const rx = ctx.api.hlRegex(ctx.api.searchWords('qarabag'));
  assert.ok(rx.test('Qarabağ qalib gəldi'));
  assert.equal(ctx.api.route.call(null) && (ctx.location.hash = '#/yoxdur', ctx.api.route().name), 'notfound');
});

test('social posts are ordered by time only and show the reporting source', () => {
  const ctx = app();
  ctx.api.S.social = { posts: [
    { who: 'prezident', name: 'Prezident', network: 'YouTube', text: 'köhnə', url: 'u1', publishedAt: '2026-10-26T10:00:00+00:00' },
    { who: 'birinci-xanim', name: 'Mehriban Əliyeva', network: 'X', text: 'yeni', url: 'u2', publishedAt: '2026-10-28T10:00:00+00:00', via: 'Report.az' },
    { who: 'prezident', name: 'Prezident', network: 'X', text: 'orta', url: 'u3', publishedAt: '2026-10-27T10:00:00+00:00' },
  ] };
  assert.deepEqual([...ctx.api.orderedSocialPosts(8).map(p => p.text)], ['yeni', 'orta', 'köhnə']);
  assert.deepEqual([...ctx.api.orderedSocialPosts(2).map(p => p.text)], ['yeni', 'orta']);
  const html = ctx.api.socialBlock(true);
  assert.ok(html.includes('<span class="via">Report.az</span>'));
  assert.ok(html.indexOf('yeni') < html.indexOf('orta'));
  // sahib 2026-11-06: sosial yazının da «Paylaş» düyməsi var, yazının qutusunun içində; paylaşılan keçid 8ulduz-dur (YouTube/X yox)
  // keçid həmin yazıya aparır: #/bolme/prezident?s=<id> (WhatsApp-da 8ulduz şəkli qalır; sahib 2026-11-06)
  Object.assign(ctx.api.S.social.posts[1], { id: '56ba6f3455e532b6', url: 'https://x.com/1st_Lady_AZ/status/1' });
  ctx.api.S.data = { sharePages: true, articles: [] };
  let soc = ctx.api.socialBlock(false);
  assert.ok(soc.includes('href="https://x.com/1st_Lady_AZ/status/1"'));
  // sahib 2026-11-07: paylaşımda kimə aiddirsə adı başlığın önündə — «İlham Əliyev: …» / «Mehriban Əliyeva: …»; keçid yazının öz
  // og səhifəsidir (bolme/prezident/s/<id>, updater.write_social_share_pages), oradan dərhal #/bolme/prezident?s=<id>
  assert.ok(soc.includes('</a><button type="button" class="share" data-act="share" data-share="https://8ulduz.az/bolme/prezident/s/56ba6f3455e532b6" data-title="Mehriban Əliyeva: yeni" title="Paylaş">Paylaş</button></article>'));
  assert.ok(soc.includes('data-share="https://8ulduz.az/#/bolme/prezident" data-title="İlham Əliyev: '), 'id-siz yazı Zuğulbaya aparır');
  const nf = fs.readFileSync(path.join(__dirname, '..', '404.html'), 'utf8');
  assert.ok(nf.includes('s=p.match(/\\/bolme\\/prezident\\/s\\/([0-9a-f]{16})$/)') && nf.includes('location.replace("/#/bolme/prezident?s="+s[1])'), 'səhifə hələ yayımlanmayıbsa Zuğulbada həmin yazı');
  assert.ok(!soc.includes('data-share="https://x.com'));
  ctx.api.S.data = { articles: [] };
  soc = ctx.api.socialBlock(false, '56ba6f3455e532b6');
  assert.ok(soc.startsWith('<aside') && soc.indexOf('<article class="soc-r on">') === soc.indexOf('<article'), 'keçiddən gələndə yazı seçili və siyahının başında (sürüşmə/sıçrama yoxdur)');
  assert.ok(soc.includes('data-share="https://8ulduz.az/bolme/prezident/s/56ba6f3455e532b6"'));
  assert.ok(!fs.readFileSync(path.join(__dirname, "..", "assets/app.js"), "utf8").includes("soc-on"), "scrollIntoView yoxdur");
  // Zuğulba səhifəsi xronika ilə açılır: sosial şəbəkələr bağlı bölmədədir; menyuda «Sosial müdafiə» tam yazılır
  const src = fs.readFileSync(path.join(__dirname, '..', 'assets/app.js'), 'utf8');
  assert.ok(src.includes('extra = `<details class="social-details"${s ? " open" : ""}><summary>'), 'bağlı bölmə; yazının keçidindən gələndə açıq');
  assert.ok(src.includes("const socNow = /[?&]s=[0-9a-f]{16}/.test(location.hash) && loadSocial();"), "keçiddən gələndə sosial yazılar xəbərlə paralel yüklənir (sürət)");
  assert.ok(!/NAV_SHORT = \{[^}]*sosial/.test(src));
  const css = fs.readFileSync(path.join(__dirname, '..', 'assets/app.css'), 'utf8');
  assert.ok(css.includes('.card :is(h2,h3){margin:0') && css.includes('.card h2,.card h3,'), 'bölmə kartının başlığı (h2) sətir hündürlüyü alır');
  assert.ok(css.includes('nav.main .nav-more-pop a{font-size:var(--fs-body)'));
});

test('appointment and dismissal news are recognised; Zuğulba includes state sites with thumbnails', () => {
  const ctx = app();
  const now = Date.now();
  const at = h => new Date(now - h * 3600e3).toISOString();
  assert.ok(ctx.api.isAppointment({ title: 'Yeni icra başçısı təyin edilib' }));
  assert.ok(ctx.api.isAppointment({ title: 'Nazir vəzifəsindən azad olunub' }));
  assert.ok(!ctx.api.isAppointment({ title: 'Girov azad edilib' }));
  const prez = [
    { id: 'a', category: 'prezident', source: 'AZƏRTAC', title: 'Prezident İlham Əliyev təbrik edib', publishedAt: at(2) },
    { id: 'b', category: 'prezident', source: 'Oxu.az', title: 'Prezident qəbul edib', publishedAt: at(1) },
    { id: 'd', category: 'prezident', source: 'Cross Media', title: 'Prezident İlham Əliyev fərman imzalayıb', publishedAt: at(4), imageUrl: 'https://crossmedia.az/storage/news/a.jpeg' },
    { id: 'c', category: 'prezident', source: 'Prezident.az', title: 'İlham Əliyev sərəncam imzalayıb: yeni rəis təyin edilib', publishedAt: at(3) },
  ];
  const ids = [...ctx.api.prezHome(prez).map(a => a.id)];
  assert.ok(ids.includes('a') && ids.includes('d') && !ids.includes('b')); // Oxu.az xəbərində rəhbərliyin adı yoxdur
  assert.deepEqual(ids, ['a', 'c', 'd']); // ən yenidən köhnəyə
  const html = ctx.api.prezBlock(ctx.api.prezHome(prez));
  assert.ok(html.includes('<article class="pcard has-img"') && html.includes(encodeURIComponent('https://crossmedia.az/storage/news/a.jpeg')));
  assert.ok(html.includes('<article class="pcard" data-cat="prezident"')); // şəkilsiz xəbər şəkil yeri tutmur
});

test('every news list is newest first: an old appointment story is not pinned above fresh news', () => {
  const ctx = app(), {S} = ctx.api;
  const at = h => new Date(Date.now() - h * 3600e3).toISOString();
  const row = (id, h, title, category = 'gundem') => ({ id, title, category, lang: 'az', source: 'APA', sourceUrl: 'https://apa.az/' + id, publishedAt: at(h) });
  const old = row('old', 4, 'Rektor vəzifəsindən azad edilib');
  const fresh = row('fresh', 0.1, 'Bakıda yeni park açılıb'), mid = row('mid', 1, 'Sumqayıtda yeni məktəb tikilir');
  const order = html => ['fresh', 'mid', 'old'].map(id => html.indexOf('apa.az/' + id)).filter(i => i >= 0);
  const sorted = xs => [...xs].every((v, i, l) => !i || l[i - 1] < v);
  const latest = ctx.api.latestBlock([old, mid, fresh]);
  assert.equal(order(latest).length, 3);
  assert.ok(sorted(order(latest)), 'Son xəbərlər');
  S.data = {articles: [old, mid, fresh]};
  for (const slug of ['gundem']) assert.ok(sorted(order(ctx.api.sectionView(slug))), 'bölmə');
  const src = fs.readFileSync(path.join(root, 'assets/app.js'), 'utf8');
  assert.ok(!src.includes('frontAppointments'), 'siyahını qabağa çəkən qayda geri qayıtmasın');
});
test('Zuğulba stays newest first even though both groups keep their place', () => {
  const ctx = app();
  const at = h => new Date(Date.now() - h * 3600e3).toISOString();
  const prez = [
    { id: 'lady', category: 'prezident', source: 'Mehriban Əliyeva', title: 'Birinci xanım tədbirdə iştirak edib', publishedAt: at(30) },
    { id: 'p1', category: 'prezident', source: 'Prezident.az', title: 'İlham Əliyev qəbul edib', publishedAt: at(2) },
    { id: 'p2', category: 'prezident', source: 'Prezident.az', title: 'İlham Əliyev təbrik edib', publishedAt: at(1) },
  ];
  assert.deepEqual([...ctx.api.prezHome(prez).map(a => a.id)], ['p2', 'p1', 'lady']);
});
test('the "most sources" tab keeps its own order on purpose', () => {
  const ctx = app(), {S} = ctx.api;
  const at = h => new Date(Date.now() - h * 3600e3).toISOString();
  const row = (id, h, alts) => ({ id, title: 'Başlıq ' + id, category: 'gundem', lang: 'az', source: 'APA', sourceUrl: 'https://apa.az/' + id, publishedAt: at(h), alts });
  S.latestOrder = 'sources';
  const html = ctx.api.latestBlock([row('fresh', 0.1, []), row('wide', 3, [{source: 'Report', sourceUrl: 'https://report.az/1'}, {source: 'Trend', sourceUrl: 'https://trend.az/1'}])]);
  assert.ok(html.indexOf('apa.az/wide') < html.indexOf('apa.az/fresh'));
});
test('one state site cannot fill the Zuğulba block: at most 3 cards per non-official source when the block is full', () => {
  const ctx = app();
  const at = h => new Date(Date.now() - h * 3600e3).toISOString();
  const prez = [1, 2, 3, 4, 5].map(i => ({ id: 'r' + i, category: 'prezident', source: 'Report', title: 'İlham Əliyev: sitat ' + i, publishedAt: at(i) }));
  for (let i = 0; i < 44; i++) prez.push({ id: 'o' + i, category: 'prezident', source: 'Prezident.az', title: 'İlham Əliyev səfiri qəbul edib ' + i, publishedAt: at(9 + i) });
  const ids = [...ctx.api.prezHome(prez).map(a => a.id)];
  assert.deepEqual(ids.filter(i => i.startsWith('r')), ['r1', 'r2', 'r3']); // ən yeni 3 Report
  assert.equal(ids.length, 44);
});

test('raw links are stripped from headlines', () => {
  const ctx = app();
  assert.equal(ctx.api.tidy('Harri Keyn mükafat qazanıb https://report.az/futbol/abc'), 'Harri Keyn mükafat qazanıb');
});

function worker(cacheNames = [], open) {
  const listeners = {}, deleted = [];
  const context = vm.createContext({URL, Request, Response, Headers, console, AbortController, setTimeout, clearTimeout,
    self: {location: new URL('https://example.com/8ulduz/sw.js'), addEventListener: (name, fn) => listeners[name] = fn,
      clients: {claim: async () => {}}, registration: {}},
    caches: {keys: async () => cacheNames, delete: async key => deleted.push(key),
      open: open || (async () => ({match: async () => null}))},
    fetch: async () => { throw Error('offline'); },
  });
  vm.runInContext(fs.readFileSync(path.join(root, 'sw.js'), 'utf8'), context);
  return {context, listeners, deleted};
}

test('service worker does not intercept GoatCounter', () => {
  const {listeners} = worker();
  let called = false;
  for (const url of ['https://8ulduz.goatcounter.com/count?p=%2F', 'https://gc.zgo.at/count.v4.js']) {
    listeners.fetch({request: new Request(url), respondWith() { called = true; }});
  }
  assert.equal(called, false);
});
test('service worker retains caches belonging to other sites', async () => {
  const version = fs.readFileSync(path.join(root,'sw.js'),'utf8').match(/const VERSION = "([^"]+)"/)[1];
  const {listeners, deleted} = worker(['other-app-v1', '8ulduz-static-v15', '8ulduz-data-v15', '8ulduz-static-'+version]);
  let done;
  listeners.activate({waitUntil(p) { done = p; }});
  await done;
  assert.deepEqual(deleted.sort(), ['8ulduz-data-v15', '8ulduz-static-v15']);
});

// Xidmət işçisinin məlumat axını: ziyarətçinin DNS-i domeni tapmasa da lent donmamalıdır.
function dataWorker(fetchImpl, seed = {}) {
  const listeners = {}, store = new Map(Object.entries(seed)), calls = [];
  const context = vm.createContext({URL, Request, Response, Headers, console, AbortController, Date,
    setTimeout: fn => setTimeout(fn, 1), clearTimeout,
    self: {location: new URL('https://example.com/sw.js'), addEventListener: (name, fn) => listeners[name] = fn,
      clients: {claim: async () => {}}, registration: {}},
    caches: {keys: async () => [], delete: async () => {},
      open: async () => ({match: async key => store.get(String(key))?.clone(), put: async (key, r) => { store.set(String(key), r); }})},
    fetch: (input, init) => { const url = input.url || String(input); calls.push(url); return fetchImpl(url, init || {}); },
  });
  vm.runInContext(fs.readFileSync(path.join(root, 'sw.js'), 'utf8'), context);
  const get = async file => {
    let answer;
    listeners.fetch({request: new Request('https://example.com/data/' + file), respondWith: p => { answer = p; }});
    return answer;
  };
  return {get, calls, store};
}
const json = (body, headers = {}) => new Response(JSON.stringify(body), {status: 200, headers: {'content-type': 'application/json; charset=utf-8', ...headers}});
const RAW = 'https://raw.githubusercontent.com/8ulduz/8ulduz/main/data/';

test('when the domain does not resolve, data comes from the mirror and the page is not told it is offline', async () => {
  const {get, calls, store} = dataWorker(async url => {
    if (url.startsWith('https://example.com/')) throw new TypeError('ERR_NAME_NOT_RESOLVED');
    return new Response('{"from":"mirror"}', {status: 200, headers: {'content-type': 'text/plain; charset=utf-8'}});
  });
  const r = await get('news.json?t=5');
  assert.equal(r.headers.get('X-8ulduz-data'), 'mirror');
  assert.equal(r.headers.get('content-type'), 'application/json; charset=utf-8');
  assert.deepEqual(await r.json(), {from: 'mirror'});
  assert.equal(calls[1], RAW + 'news.json?t=5');
  assert.ok(store.has('https://example.com/data/news.json'));
});
test('a healthy site never touches the mirror', async () => {
  const {get, calls} = dataWorker(async () => json({from: 'site'}, {'last-modified': new Date().toUTCString()}));
  const r = await get('news.json');
  assert.equal(r.headers.get('X-8ulduz-data'), 'network');
  assert.equal(calls.length, 1);
});
test('a hanging site falls over to the mirror instead of waiting forever', async () => {
  const {get} = dataWorker((url, init) => url.startsWith(RAW) ? Promise.resolve(json({from: 'mirror'}))
    : new Promise((_, reject) => init.signal.addEventListener('abort', () => reject(new Error('aborted')))));
  assert.equal((await get('status.json')).headers.get('X-8ulduz-data'), 'mirror');
});
test('a site error page or html is not stored as news', async () => {
  for (const bad of [new Response('<html>', {status: 200, headers: {'content-type': 'text/html'}}), new Response('no', {status: 503})]) {
    const {get} = dataWorker(async url => url.startsWith(RAW) ? json({from: 'mirror'}) : bad.clone());
    assert.equal((await get('news.json')).headers.get('X-8ulduz-data'), 'mirror');
  }
});
test('stuck Pages deployment: live files come from the mirror, static ones stay on the site', async () => {
  const old = new Date(Date.now() - 40 * 60e3).toUTCString();
  const stuck = async url => url.startsWith(RAW) ? json({from: 'mirror'}) : json({from: 'site'}, {'last-modified': old});
  assert.equal((await dataWorker(stuck).get('news.json')).headers.get('X-8ulduz-data'), 'mirror');
  const ads = dataWorker(stuck);
  assert.equal((await ads.get('ads.json')).headers.get('X-8ulduz-data'), 'network');
  assert.equal(ads.calls.length, 1);
  const noMirror = async url => { if (url.startsWith(RAW)) throw new TypeError('down'); return json({from: 'site'}, {'last-modified': old}); };
  assert.deepEqual(await (await dataWorker(noMirror).get('news.json')).json(), {from: 'site'});
});
const LIVE = 'https://raw.githubusercontent.com/8ulduz/8ulduz/live/m/';
test('red line 1: status, latest and markets come from the one-minute live channel first', async () => {
  for (const file of ['status.json', 'latest.json', 'latest.az.json', 'markets.json']) {
    const {get, calls} = dataWorker(async url => { assert.ok(url.startsWith(LIVE)); return json({from: 'live'}); });
    const r = await get(file + '?t=1');
    assert.equal(r.headers.get('X-8ulduz-data'), 'live');
    assert.equal(calls.length, 1);
    assert.match(calls[0], new RegExp('^' + LIVE + '\\d+/' + file.replace('.', '\\.') + '$'));
  }
});
test('red line 1: the page asks only for a minute that is already written, and falls back to earlier minutes', async () => {
  const realNow = Date.now;
  Date.now = () => Date.UTC(2026, 9, 30, 7, 10, 44); // 07:10:44: 07:10 dəqiqəsi hələ yazılmış sayılmır
  try {
    const slot = Math.floor(Date.UTC(2026, 9, 30, 7, 9) / 60000);
    const {get, calls} = dataWorker(async url => url.includes('/' + (slot - 1) + '/') ? json({from: 'live'}) : new Response('', {status: 404}));
    const r = await get('status.json');
    assert.equal(r.headers.get('X-8ulduz-data'), 'live');
    assert.deepEqual(calls, [LIVE + slot + '/status.json', LIVE + (slot - 1) + '/status.json']);
  } finally { Date.now = realNow; }
});
test('red line 1: when the stream is not writing, the site channel answers and the live channel rests a minute', async () => {
  const {get, calls} = dataWorker(async url => url.startsWith(LIVE) ? new Response('', {status: 404}) : json({from: 'site'}, {'last-modified': new Date().toUTCString()}));
  assert.equal((await get('status.json')).headers.get('X-8ulduz-data'), 'network');
  await get('status.json');
  assert.equal(calls.filter(u => u.startsWith(LIVE)).length, 3);
});
test('red line 1: a broken live channel falls back to the site at once, and a rate limit pauses it', async () => {
  const down = dataWorker(async url => { if (url.startsWith(LIVE)) throw new TypeError('down'); return json({from: 'site'}, {'last-modified': new Date().toUTCString()}); });
  assert.equal((await down.get('status.json')).headers.get('X-8ulduz-data'), 'network');
  const limited = dataWorker(async url => url.startsWith(LIVE) ? new Response('slow', {status: 429}) : json({from: 'site'}, {'last-modified': new Date().toUTCString()}));
  await limited.get('status.json');
  await limited.get('status.json');
  assert.equal(limited.calls.filter(u => u.startsWith(LIVE)).length, 1);
});
test('only when site and mirror both fail does the page get saved news, marked as such', async () => {
  const down = async () => { throw new TypeError('offline'); };
  const saved = dataWorker(down, {'https://example.com/data/news.json': json({from: 'saved'})});
  const r = await saved.get('news.json?t=9');
  assert.equal(r.headers.get('X-8ulduz-data'), 'cache');
  assert.deepEqual(await r.json(), {from: 'saved'});
  assert.equal((await dataWorker(down).get('news.json')).status, 503);
});

test('sport ignores the global language choice and club aliases cover Russian and Latin headlines',()=>{
  const ctx=app(),{S,sectionView,clubMatches}=ctx.api;
  S.lang='az';S.club=null;
  S.data={articles:[['az','Qarabağ qalib gəldi'],['ru','Карабах победил'],['en','Qarabag wins'],['tr','Qarabağ kazandı']].map(([lang,title],i)=>({id:String(i),title,lang,category:'idman',source:'Source',sourceUrl:'https://example.com/'+i,publishedAt:new Date().toISOString()}))};
  for(const a of S.data.articles)assert.ok(sectionView('idman').includes(a.title));
  S.club='Qarabağ';
  for(const a of S.data.articles)assert.ok(sectionView('idman').includes(a.title));
  assert.equal(clubMatches({title:'Qarabağın növbəti oyunu'},'Qarabağ'),true);
  assert.equal(clubMatches({title:'International tournament'},'İnter'),false);
});

test('offline without cached data is a failure, not an empty successful feed', async () => {
  const {context} = worker();
  const res = await vm.runInContext("networkFirstData(new Request('https://example.com/8ulduz/data/news.json'))", context);
  assert.equal(res.status, 503);
});

test('new application code replaces a cached version while online', async () => {
  const {context} = worker();
  let stored;
  context.fetch = async () => new Response('new code');
  context.caches.open = async () => ({match: async () => undefined, put: async (_key, response) => { stored = await response.text(); }});
  const res = await vm.runInContext("cachedShell(new Request('https://example.com/8ulduz/assets/app.js'))", context);
  assert.equal(await res.text(), 'new code');
  await new Promise(r => setImmediate(r));
  assert.equal(stored, 'new code');
});

test('a slow first visit to another page waits for that page instead of showing index.html at the wrong path', async () => {
  const {context} = worker();
  let answer;
  context.fetch = () => new Promise(r => { answer = r; });
  context.caches.open = async () => ({match: async (req) => String(req).includes('index.html') ? new Response('shell') : undefined, put: async () => {}});
  vm.runInContext('globalThis.setTimeout = (fn) => { fn(); return 0; };', context);
  const pending = vm.runInContext("cachedShell(new Request('https://example.com/8ulduz/mexfilik/index.html'.replace('index.html','')))", context);
  await new Promise(r => setImmediate(r));
  answer(new Response('privacy page'));
  assert.equal(await (await pending).text(), 'privacy page');
});

// Sürət (qırmızı xətt 3): təkrar açılış şəbəkəni gözləmir. Saxlanmış qabıq dərhal verilir, təzəsi arxada saxlanır və
// kod dəyişibsə açıq səhifələrə bildirilir (app.js səhifəni yeniləyir).
test('the saved shell answers at once; changed code is stored for the next visit and announced', async () => {
  const {context} = worker();
  let stored, messages = [];
  // Şəbəkə səhifə keşdəki cavabı oxuyandan SONRA gəlir (əsl brauzerdə həmişə belədir): müqayisə yenə işləməlidir.
  context.fetch = () => new Promise(r => setTimeout(() => r(new Response('new code')), 5));
  context.caches.open = async () => ({match: async () => new Response('cached code'), put: async (_key, response) => { stored = await response.text(); }});
  context.self.clients.matchAll = async () => [{postMessage: m => messages.push(m)}];
  const res = await vm.runInContext("cachedShell(new Request('https://example.com/8ulduz/assets/app.js'))", context);
  assert.equal(await res.text(), 'cached code');
  await new Promise(r => setTimeout(r, 15));
  for (let i = 0; i < 20 && !messages.length; i++) await new Promise(r => setImmediate(r));
  assert.equal(stored, 'new code');
  assert.deepEqual(messages.map(m => m.type), ['shell-updated']);
});
test('unchanged code and a changed index.html are stored quietly', async () => {
  for (const [url, saved, fresh] of [['assets/app.js', 'same', 'same'], ['', '<p>old</p>', '<p>new</p>']]) {
    const {context} = worker();
    let stored, messages = [];
    context.fetch = async () => new Response(fresh);
    context.caches.open = async () => ({match: async () => new Response(saved), put: async (_key, response) => { stored = await response.text(); }});
    context.self.clients.matchAll = async () => [{postMessage: m => messages.push(m)}];
    const res = await vm.runInContext("cachedShell(new Request('https://example.com/8ulduz/" + url + "'))", context);
    assert.equal(await res.text(), saved);
    for (let i = 0; i < 20 && stored === undefined; i++) await new Promise(r => setImmediate(r));
    assert.equal(stored, fresh);
    assert.deepEqual(messages, []);
  }
});

// Çoxdan gəlməyən oxucu (sahib, 2026-11-13): Facebook-un daxili brauzeri saytın 3 gün əvvəl saxlanmış nüsxəsini göstərdi
// (10 noyabrda çıxarılmış 6 düyməli alt zolaqla). Saxlanmış nüsxə 36 saatdan köhnədirsə əvvəl təzəsi gözlənilir.
const savedAt = (text, hoursAgo) => new Response(text, {headers: {date: new Date(Date.now() - hoursAgo * 3600e3).toUTCString()}});
test('a saved shell older than a day and a half gives way to the fresh one, quietly', async () => {
  for (const url of ['assets/app.js', 'assets/app.css', '']) {
    const {context} = worker();
    let stored, messages = [];
    context.fetch = () => new Promise(r => setTimeout(() => r(new Response('fresh')), 5));
    context.caches.open = async () => ({match: async () => savedAt('three days old', 72), put: async (_key, response) => { stored = await response.text(); }});
    context.self.clients.matchAll = async () => [{postMessage: m => messages.push(m)}];
    const res = await vm.runInContext("cachedShell(new Request('https://example.com/8ulduz/" + url + "'))", context);
    assert.equal(await res.text(), 'fresh', url + ': oxucu təzə nüsxəni görür');
    for (let i = 0; i < 20 && stored === undefined; i++) await new Promise(r => setImmediate(r));
    assert.equal(stored, 'fresh', 'təzə nüsxə növbəti açılış üçün saxlanır');
    await new Promise(r => setTimeout(r, 10));
    assert.deepEqual(messages, [], 'səhifə artıq təzə kodu alıb: yenidən açılma xəbəri getmir');
  }
});
test('red line 1: a saved shell from the last day and a half still answers at once', async () => {
  for (const hours of [0, 1, 24, 35]) {
    const {context} = worker();
    let answer, messages = [];
    context.fetch = () => new Promise(r => { answer = r; });
    context.caches.open = async () => ({match: async () => savedAt('saved code', hours), put: async () => {}});
    context.self.clients.matchAll = async () => [{postMessage: m => messages.push(m)}];
    const res = await vm.runInContext("cachedShell(new Request('https://example.com/8ulduz/assets/app.js'))", context);
    assert.equal(await res.text(), 'saved code', hours + ' saat: şəbəkə gözlənilmir');
    answer(new Response('new code'));
    for (let i = 0; i < 20 && !messages.length; i++) await new Promise(r => setImmediate(r));
    assert.deepEqual(messages.map(m => m.type), ['shell-updated'], 'təzə kod əvvəlki kimi bildirilir');
  }
});
test('an old saved shell is still shown when the network is slow, failing or answers with an error', async () => {
  // Yavaş şəbəkə: gözləmə bitir, saxlanmış nüsxə verilir; təzəsi sonra gələndə səhifəyə bildirilir.
  const slow = worker().context;
  let answer, messages = [];
  slow.fetch = () => new Promise(r => { answer = r; });
  slow.caches.open = async () => ({match: async () => savedAt('old code', 72), put: async () => {}});
  slow.self.clients.matchAll = async () => [{postMessage: m => messages.push(m)}];
  vm.runInContext('globalThis.setTimeout = (fn) => { fn(); return 0; };', slow);
  const late = await vm.runInContext("cachedShell(new Request('https://example.com/8ulduz/assets/app.js'))", slow);
  assert.equal(await late.text(), 'old code');
  answer(new Response('new code'));
  for (let i = 0; i < 20 && !messages.length; i++) await new Promise(r => setImmediate(r));
  assert.deepEqual(messages.map(m => m.type), ['shell-updated']);
  // Şəbəkə yoxdur və ya server xəta verir: boş səhifə yox, saxlanmış nüsxə.
  for (const fetch of [async () => { throw new TypeError('offline'); }, async () => new Response('Server Error', {status: 500})]) {
    const {context} = worker();
    context.fetch = fetch;
    context.caches.open = async () => ({match: async () => savedAt('old code', 72), put: async () => { throw Error('xətalı cavab saxlanmamalıdır'); }});
    const res = await vm.runInContext("cachedShell(new Request('https://example.com/8ulduz/assets/app.js'))", context);
    assert.equal(await res.text(), 'old code');
  }
  const sw = fs.readFileSync(path.join(root, 'sw.js'), 'utf8');
  assert.match(sw, /const SHELL_MAX_AGE_MS = 36 \* 3600e3, SHELL_WAIT_MS = 2500;/, 'hədlər: 36 saat, ən çox 2,5 s gözləmə');
});

test('a navigation with a query string reads and stores the shell under the path only', async () => {
  const {context} = worker();
  const seen = {match: [], put: []};
  context.fetch = async (req) => { seen.fetched = req.url; return new Response('<p>fresh</p>'); };
  context.caches.open = async () => ({match: async (key, opts) => { seen.match.push([String(key), opts?.ignoreSearch]); return new Response('<p>saved</p>'); }, put: async (key) => { seen.put.push(String(key)); }});
  context.navReq = { url: 'https://example.com/8ulduz/?utm_source=whatsapp#/xeber/1', mode: 'navigate', method: 'GET' };
  const res = await vm.runInContext("cachedShell(navReq)", context);
  assert.equal(await res.text(), '<p>saved</p>');
  for (let i = 0; i < 20 && !seen.put.length; i++) await new Promise(r => setImmediate(r));
  assert.deepEqual(seen.match, [['https://example.com/8ulduz/', false]], 'sorğu sətri açara düşmür, ignoreSearch yoxdur');
  assert.deepEqual(seen.put, ['https://example.com/8ulduz/'], 'təzə nüsxə eyni açarın üstünə yazılır');
  assert.equal(seen.fetched, 'https://example.com/8ulduz/');
});
// Kod faylı da: bir dəfə app.js?c=… istənəndə (yoxlama sorğusu) ayrı nüsxə yaranırdı və ignoreSearch həmişə onu qaytarırdı —
// arxa yoxlama sorğusuz açarı təzələsə də oxucu köhnə kodda qalırdı (sw v39, 4 noyabr).
test('a code file asked with a query string is read and stored under the path only', async () => {
  const {context} = worker();
  const seen = {match: [], put: []};
  context.fetch = async (req) => { seen.fetched = req.url || String(req); return new Response('fresh code'); };
  context.caches.open = async () => ({match: async (key, opts) => { seen.match.push([String(key), opts?.ignoreSearch]); return new Response('saved code'); }, put: async (key) => { seen.put.push(String(key)); }});
  context.self.clients.matchAll = async () => [];
  const res = await vm.runInContext("cachedShell(new Request('https://example.com/8ulduz/assets/app.js?c=1793809578259'))", context);
  assert.equal(await res.text(), 'saved code');
  for (let i = 0; i < 20 && !seen.put.length; i++) await new Promise(r => setImmediate(r));
  assert.deepEqual(seen.match, [['https://example.com/8ulduz/assets/app.js', false]], 'sorğu sətri açara düşmür, ignoreSearch yoxdur');
  assert.deepEqual(seen.put, ['https://example.com/8ulduz/assets/app.js'], 'təzə nüsxə sorğusuz açarın üstünə yazılır');
  assert.equal(seen.fetched, 'https://example.com/8ulduz/assets/app.js', 'şəbəkəyə də sorğusuz yol gedir');
});

test('a hanging network does not leave a blank page when a copy is saved', async () => {
  const {context} = worker();
  context.fetch = () => new Promise(() => {});
  context.caches.open = async () => ({match: async () => new Response('cached code')});
  vm.runInContext('globalThis.setTimeout = (fn) => { fn(); return 0; };', context);
  const res = await vm.runInContext("cachedShell(new Request('https://example.com/8ulduz/assets/app.js'))", context);
  assert.equal(await res.text(), 'cached code');
});

test('application code is still available offline', async () => {
  const {context} = worker();
  context.caches.open = async () => ({match: async () => new Response('cached code')});
  const res = await vm.runInContext("cachedShell(new Request('https://example.com/8ulduz/assets/app.js'))", context);
  assert.equal(await res.text(), 'cached code');
});

test('full cache does not discard fresh network news', async () => {
  const {context} = worker();
  context.fetch = async () => new Response('{"articles":[]}');
  context.caches.open = async () => ({put: async () => { throw Error('quota'); }});
  const res = await vm.runInContext("networkFirstData(new Request('https://example.com/8ulduz/data/news.json'))", context);
  assert.equal(res.status, 200);
  assert.equal(res.headers.get('X-8ulduz-data'), 'network');
});

test('"Son dəqiqə" badge covers 15 minutes, the section covers an hour', () => {
  const ctx = app();
  const at = min => ({publishedAt: new Date(Date.now() - min * 60000).toISOString()});
  assert.equal(ctx.api.isFresh(at(5)), true);
  assert.equal(ctx.api.isFresh(at(30)), false);
  assert.equal(ctx.api.withinHour(at(30)), true);
  assert.equal(ctx.api.withinHour(at(90)), false);
});

test('default language filter is Azerbaijani; "all" and a chosen language persist', () => {
  const ctx = app();
  assert.equal(ctx.api.S.lang, 'az');
  ctx.api.storage.setItem(ctx.api.LANG_KEY, '');
  assert.equal(ctx.api.savedLang(), null);
  ctx.api.storage.setItem(ctx.api.LANG_KEY, 'ru');
  assert.equal(ctx.api.savedLang(), 'ru');
  ctx.api.storage.setItem(ctx.api.LANG_KEY, 'xx');
  assert.equal(ctx.api.savedLang(), 'az');
});

test('hero picks the most-covered recent stories, not merely the newest', () => {
  const ctx = app();
  const h = n => new Date(Date.now() - n * 3600000).toISOString();
  const list = [
    {id: 'new', publishedAt: h(0.1), alts: []},
    {id: 'big', publishedAt: h(6), alts: [1, 2, 3, 4]},
    {id: 'mid', publishedAt: h(2), alts: [1]},
    {id: 'old', publishedAt: h(40), alts: [1, 2, 3, 4, 5, 6]},
  ];
  assert.equal(ctx.api.heroPick(list, 3).map(a => a.id).join(), 'big,mid,new');
  assert.equal(ctx.api.heroPick(list, 4).map(a => a.id).join(), 'old,big,mid,new');
});

test('ticker is called "Son xəbərlər" when nothing is fresh', () => {
  const ctx = app();
  assert.equal(ctx.api.tickerLabel(0), 'Son xəbərlər');
  assert.equal(ctx.api.tickerLabel(3), 'Son dəqiqə');
});


test('article routes and source controls are independent', () => {
  const ctx = app();
  ctx.location.hash = '#/xeber/item-1#sources';
  assert.equal(ctx.api.route().name, 'article');
  assert.equal(ctx.api.route().id, 'item-1');
  const article = {id:'item-1',title:'Test',source:'One',sourceUrl:'https://one.example',publishedAt:new Date().toISOString(),category:'gundem',lang:'az',alts:[{source:'Two',sourceUrl:'https://two.example'}]};
  const html = ctx.api.card(article);
  assert.ok(html.includes('class="card-hit" href="https://one.example" target="_blank"'));
  assert.ok(!html.includes('href="#/xeber/item-1"'));
  assert.ok(html.includes('2 mənbə'));
  assert.ok(html.includes('https://two.example'));
  assert.ok(html.includes('https://one.example'));
  assert.ok(!html.includes('>AZ</span>'));
});

test('category carousels keep twelve stories accessible with arrows', () => {
  const ctx=app();
  const list=Array.from({length:7},(_,i)=>({id:String(i),title:'Test',source:'One',sourceUrl:'https://one.example',category:'gundem',publishedAt:new Date().toISOString()}));
  const html=ctx.api.catSection({slug:'gundem',label:'Gündəm'},list);
  assert.equal((html.match(/<article /g)||[]).length,7);
  assert.ok(html.includes('class="strip category-strip"'));
});


test('saved article remains readable after it leaves the live feed', () => {
  const ctx=app();
  ctx.api.S.data={articles:[]};
  const saved={id:'archived',title:'Saved story',summary:'Saved summary',source:'Archive source',sourceUrl:'https://example.com/story',publishedAt:'2026-10-01T10:00:00Z'};
  ctx.api.storage.setItem('8ulduz-saved',JSON.stringify([saved]));
  const html=ctx.api.articleView('archived');
  assert.ok(html.includes('Saved story'));
  assert.ok(!html.includes('Saved summary'));
  assert.ok(html.includes('https://example.com/story'));
  assert.ok(!html.includes('artıq lentdə yoxdur'));
  ctx.api.S.data.articles=[{...saved,title:'Updated live title'}];
  assert.ok(ctx.api.articleView('archived').includes('Updated live title'));
  ctx.api.S.archiveScan='missing';
  assert.ok(ctx.api.articleView('missing').includes('artıq lentdə yoxdur'));
});


test('photo fallback tries OG and alternate source photos in order', () => {
  const ctx=app(); ctx.api.S.og={'https://one.example':'https://img.example/og.jpg','https://two.example':'https://img.example/alt-og.jpg'};
  const images=ctx.api.imageCandidates({imageUrl:'https://img.example/rss.jpg',sourceUrl:'https://one.example',alts:[{imageUrl:'https://img.example/alt.jpg',sourceUrl:'https://two.example'}]});
  assert.deepEqual(Array.from(images),['https://img.example/rss.jpg','https://img.example/og.jpg','https://img.example/alt.jpg','https://img.example/alt-og.jpg']);
});

test('home keeps slider stories after the sixth in the lists below', () => {
  const ctx=app(),{S,homeView}=ctx.api,at=new Date().toISOString();
  const words=['alma','armud','banan','qovun','heyva','nar','gilas','albali','erik','saftali','limon','portagal','anar','zeytun','incir','xurma','zoğal','böyürtkən'];
  const rows=words.map((w,i)=>({id:String(i),title:w+'lər '+w+'ları '+i,category:'gundem',lang:'az',source:'APA',sourceUrl:'https://apa.az/'+i,imageUrl:'https://img.example/'+i+'.jpg',publishedAt:at}));
  rows.push({id:'bare',title:'Şəkilsiz xəbər lentdə qalır',category:'gundem',lang:'az',source:'APA',sourceUrl:'https://apa.az/bare',publishedAt:at,imageUrl:''});
  S.lang=null;S.og={};S.latestCount=30;S.data={articles:rows};
  const page=homeView(),below=page.slice(page.indexOf('latest-grid'));
  assert.equal((page.match(/class="hero-main"/g)||[]).length,15);
  assert.ok(!page.slice(0,page.indexOf('latest-grid')).includes('apa.az/bare'),'şəkilsiz xəbər slayderə düşmür');
  assert.ok(below.includes('apa.az/bare') && below.includes('class="card noimg"'),'şəkilsiz xəbər siyahıda mətndir');
  const slides=[...new Set([...page.slice(0,page.indexOf('latest-grid')).matchAll(/apa\.az\/(\d+)/g)].map(m=>m[1]))];
  assert.equal(slides.length,15);
  assert.ok(!below.includes('apa.az/'+slides[0]+'"'),'ilk xəbər aşağıda təkrarlanmır');
  assert.ok(below.includes('apa.az/'+slides[10]+'"'),'11-ci xəbər aşağıda da qalır');
});
test('cards can be shared, except stories with an unsafe link', () => {
  const ctx=app(),{card}=ctx.api,at=new Date().toISOString();
  ctx.api.S.og={};
  const row=url=>({id:'1',title:'Xəbər',lang:'az',category:'gundem',source:'APA',sourceUrl:url,publishedAt:at});
  // h: xəbərin saatı (sahib 2026-11-07: köhnə keçid arxiv budağından açılır, .github/scripts/arxiv.cjs)
  assert.ok(card(row('https://apa.az/1')).includes(`data-share="https://8ulduz.az/#/xeber/1?b=gundem&amp;h=${at.slice(2, 13).replace(/\D/g, '')}"`),'keçid saytımıza aparır');
  assert.ok(!card(row('javascript:alert(1)')).includes('data-share'));
});
test('a shared link still opens after its story was grouped into another one', async () => {
  const id=require('node:crypto').createHash('sha1').update('https://x.az/1').digest('hex').slice(0,16);
  const ctx=app({crypto:require('node:crypto').webcrypto,TextEncoder});
  const {S,articleView,scanArchives}=ctx.api;
  S.data={articles:[{id:'esas',title:'Əsas xəbər',source:'APA',sourceUrl:'https://apa.az/1',publishedAt:'2026-10-31T10:00:00Z',alts:[{source:'X',sourceUrl:'https://x.az/1',title:'Qruplaşan'}]}]};
  await scanArchives(id);
  const html=articleView(id);
  assert.ok(html.includes('Əsas xəbər')&&html.includes('https://x.az/1'),'qrupun səhifəsi açılır, mənbə keçidi var');
});
test('a shared link searches the archives while it looks for an old story', async () => {
  const ctx=app();
  const {S,articleView}=ctx.api;
  S.data={articles:[]};
  assert.ok(articleView('kohne').includes('Xəbər axtarılır'));
  await new Promise(r=>setTimeout(r,20));
  assert.ok(articleView('kohne').includes('artıq lentdə yoxdur'),'heç yerdə yoxdursa bunu deyir');
});
test('service addresses open their own views and old section links stay', () => {
  const ctx=app(),{route}=ctx.api;
  const at=hash=>{ctx.location.hash=hash;return route();};
  assert.equal(at('#/bolme/valyuta').name,'rates');
  assert.equal(at('#/bolme/cedvel').name,'league');
  assert.equal(at('#/bolme/tixac').name,'traffic');
  assert.equal(at('#/tixac').name,'traffic');
  assert.equal(at('#/bolme/idman').slug,'idman');
});
test('the rates page names each source and marks the direction', () => {
  const ctx=app(),{S,ratesView}=ctx.api;
  S.markets=null;
  assert.ok(ratesView().includes('yüklənir'));
  S.markets=[{label:'Dollar',value:1.7,dec:4,unit:'AZN',changePct:0,src:'AMB',asOf:'2026-10-31'},{label:'Avro',value:1.9019,dec:4,unit:'AZN',changePct:0.39,src:'AMB'},{label:'Rubl <b>',value:2.09,dec:4,unit:'AZN',changePct:-0.92,src:'ExchangeRate-API'}];
  const html=ratesView();
  assert.ok(html.includes('1.7000 AZN'));
  assert.ok(html.includes('+0.39%'));
  assert.ok(html.includes('class="down"'));
  assert.ok(html.includes('ExchangeRate-API'));
  assert.ok(html.includes('Rubl &lt;b&gt;'));
});
test('install hint module explains the manual way per browser', async () => {
  const {hint}=await import(require('url').pathToFileURL(path.join(root,'assets/ana-ekran.js')).href);
  const fb='Mozilla/5.0 (Linux; Android 14; wv) [FBAN/EMA;FBAV/400.0]';
  assert.match(hint(fb,false,'intent://8ulduz.az/#Intent;end'),/daxili brauzer.*Chrome-da aç/);
  assert.match(hint('Mozilla/5.0 (Linux; Android 14) SamsungBrowser/26.0',false),/Səhifəni əlavə et/);
  assert.match(hint('Mozilla/5.0 (Linux; Android 14) Chrome/130.0 Mobile',false),/Ana ekrana əlavə et/);
  assert.match(hint('iPhone FBAN',true),/Safari-də aç/);
  assert.ok(!hint(fb,false,'a"b').includes('a"b'),'ünvan qaçırılır');
});
test('the install button appears only when installing is possible', () => {
  const ctx=app(),{S,installBtn}=ctx.api;
  assert.equal(installBtn(),'');
  S.installEvt={};
  assert.ok(installBtn().includes('data-act="install"'));
  const iphone=app({navigator:{onLine:true,userAgent:'iPhone'}});
  assert.ok(iphone.api.installBtn().includes('data-act="install"'));
  const home=app({navigator:{onLine:true,userAgent:'iPhone',standalone:true}});
  assert.equal(home.api.installBtn(),'');
  // sahib 2026-11-10: telefonda həmişə görünsün; brauzer təklif vermirsə yolu göstərir
  const ua=u=>app({navigator:{onLine:true,userAgent:u},matchMedia:q=>({matches:q==='(hover:none)'})}).api;
  for(const u of ['Mozilla/5.0 (Linux; Android 14) SamsungBrowser/26.0','Mozilla/5.0 (Linux; Android 14; wv) [FBAN/EMA;FBAV/400.0]','Mozilla/5.0 (Android 14; Mobile) Firefox/130.0'])
    assert.ok(ua(u).installBtn().includes('data-act="install"'),u);

});
test('counting a click never breaks the page', () => {
  const ctx=app(),{trackEvent}=ctx.api;
  trackEvent('share-copy');
  const seen=[];ctx.window.goatcounter={count:o=>seen.push(o)};
  trackEvent('share-copy');
  assert.equal(seen[0].path,'share-copy');
  assert.equal(seen[0].event,true);
  ctx.window.goatcounter={count(){throw Error('x');}};
  trackEvent('share-copy');
});
test('each route is a page view with its own path and title', () => {
  const ctx=app(),{countVisit,flushVisits,S}=ctx.api;
  ctx.window.SITE_CONFIG={goatcounter:'8ulduz'};
  ctx.location.pathname='/'; ctx.location.search=''; ctx.location.hash='#/';
  ctx.document.title='8ulduz — Son xəbərlər';
  const seen=[];
  ctx.window.goatcounter={count:o=>seen.push({...o})};
  countVisit();
  assert.deepEqual(seen,[{path:'/',title:'8ulduz — Son xəbərlər'}]);
  countVisit();
  assert.equal(seen.length,1,'eyni yol təkrar sayılmır');
  ctx.location.hash='#/bolme/idman'; ctx.document.title='İdman — 8ulduz';
  countVisit();
  assert.equal(seen[1].path,'/#/bolme/idman');
  assert.equal(seen[1].title,'İdman — 8ulduz');
  assert.equal(seen[1].event,undefined);
  ctx.location.search='?utm_source=android'; ctx.location.hash='#/secilmis'; ctx.document.title='Seçilmişlər — 8ulduz';
  countVisit();
  assert.equal(seen[2].path,'/#/secilmis','android kampaniyası yolu ikiyə bölmür');
  ctx.location.search=''; ctx.location.hash='#/axtar?q=neft'; ctx.document.title='Axtarış: neft — 8ulduz';
  countVisit();
  assert.equal(seen[3].path,'/#/axtar?q=neft');
  assert.equal(seen[3].title,'Axtarış: neft — 8ulduz');
  ctx.location.hash='#/xeber/abc'; S.archiveScanning=true;
  countVisit();
  assert.equal(seen.length,4,'başlıq hazır olmamış xəbər sayılmır');
  S.data={articles:[]}; S.archiveScanning=false; ctx.document.title='Xəbər — 8ulduz';
  countVisit();
  assert.equal(seen[4].path,'/#/xeber/abc');
  assert.equal(seen[4].title,'Xəbər — 8ulduz');
  ctx.location.hash='#/komanda/premyer-liqa/qarabag'; S.teamPage=null; S.teamFailedAt=0;
  countVisit();
  assert.equal(seen.length,5,'komanda səhifəsi açılmamış sayılmır');
  S.teamPage={}; ctx.document.title='Qarabağ — 8ulduz';
  countVisit();
  assert.equal(seen[5].title,'Qarabağ — 8ulduz');
  const queued=app();
  queued.window.SITE_CONFIG={goatcounter:'8ulduz'};
  queued.location.pathname='/'; queued.location.search=''; queued.location.hash='#/haqqinda';
  queued.document.title='Haqqımızda — 8ulduz';
  queued.api.countVisit();
  const late=[]; queued.window.goatcounter={count:o=>late.push(o)};
  queued.api.flushVisits();
  assert.equal(late[0].path,'/#/haqqinda');
  assert.equal(late[0].title,'Haqqımızda — 8ulduz');
  const off=app();
  off.window.SITE_CONFIG={goatcounter:''};
  off.location.pathname='/'; off.location.search=''; off.location.hash='#/';
  off.document.title='8ulduz';
  off.api.countVisit();
  off.window.goatcounter={count(){throw Error('sent');}};
  off.api.flushVisits();
});
test('the counter script is https and skips the canonical page load', () => {
  const ctx=app(), scripts=[];
  ctx.document.createElement=()=>({dataset:{},addEventListener(){}});
  ctx.document.head={appendChild(s){scripts.push(s);}};
  ctx.window.SITE_CONFIG={goatcounter:'8ulduz'};
  ctx.api.enableAnalytics();
  assert.equal(scripts[0].src,'https://gc.zgo.at/count.v4.js');
  assert.equal(scripts[0].dataset.goatcounter,'https://8ulduz.goatcounter.com/count');
  assert.equal(scripts[0].dataset.goatcounterSettings,'{"no_onload":true}');
  assert.match(scripts[0].integrity,/sha384-/);
  const view=fs.readFileSync(path.join(root,'assets/app.js'),'utf8');
  const body=view.slice(view.indexOf('function renderView'), view.indexOf('function sourceLevel'));
  assert.ok(body.includes('countVisit()'));
  assert.match(fs.readFileSync(path.join(root,'assets/config.js'),'utf8'), /goatcounter:\s*"8ulduz"/);
});
test('every city and district has its button and finds its stories', () => {
  const ctx=app(),{S,sectionView,subNav,clubMatches}=ctx.api,at=new Date().toISOString();
  const row=(id,title,category='gundem')=>({id,title,lang:'az',category,source:'APA',sourceUrl:'https://apa.az/'+id,publishedAt:at});
  S.lang=null;S.og={};S.shown=50;S.sportTab=null;S.club=null;
  S.data={articles:[row('a','Şəkidə yeni park açılıb'),row('b','Şəkildə görünən şəxs tapılıb'),row('c','Qazaxıstanda seçki keçirilib'),row('d','Qazaxın mərkəzində körpü tikilib','bolgeler'),row('e','Məhəmməd Füzuli haqqında kitab çıxıb'),row('f','Füzulidə məktəb açılıb')]};
  let html=sectionView('bolgeler');
  for(const name of ['Bakı','Şəki-Zaqatala','Şərqi Zəngəzur','Naxçıvan MR','Abşeron-Xızı'])assert.ok(subNav('bolgeler').includes('data-club="'+name+'"'),name);
  assert.ok(html.includes('apa.az/d'),'bölgə səhifəsi öz xəbərlərini göstərir');
  S.sportTab='Şəki-Zaqatala';
  assert.ok(subNav('bolgeler').includes('data-club="Zaqatala"'),'rayonlar açılır');
  S.club='Şəki';
  html=sectionView('bolgeler');
  assert.ok(html.includes('apa.az/a'),'başqa bölmədəki xəbər də tapılır');
  assert.ok(!html.includes('apa.az/b'));
  S.data.articles.push(row('g','"Şəki" futbolçusu qol vurdu','idman'));
  assert.ok(!sectionView('bolgeler').includes('apa.az/g'),'klub xəbəri rayon düyməsində deyil');
  const hit=(title,name)=>clubMatches(row('x',title),name);
  assert.equal(hit('Qazaxıstanda seçki keçirilib','Qazax'),false);
  assert.equal(hit('Qazaxda körpü tikilib','Qazax'),true);
  assert.equal(hit('Məhəmməd Füzuli haqqında kitab','Füzuli'),false);
  assert.equal(hit('Füzulidə məktəb açılıb','Füzuli'),true);
  assert.equal(hit('Şəki rayonunda yağış','Şəki-Zaqatala'),true);
  assert.equal(hit('В Гяндже открыли парк','Gəncə'),true);
  assert.equal(hit('Ordubadda yol təmir olunur','Naxçıvan MR'),true,'bölgə düyməsi bütün rayonlarını əhatə edir');
  assert.equal(hit('Bakıda yol təmir olunur','Bakı'),true);
});
test('all fourteen economic regions and their places are listed once', () => {
  const src=fs.readFileSync(path.join(root,'assets/app.js'),'utf8');
  const block=src.slice(src.indexOf('const REGION_TABS = ['),src.indexOf('const SUB_TABS'));
  const groups=[...block.matchAll(/\{ name: "([^"]+)", groups:/g)].map(m=>m[1]);
  assert.equal(groups.length,13,'Bakı öz düyməsidir, üstəgəl 13 iqtisadi rayon');
  const places=[...block.matchAll(/\{ name: "([^"]+)", keys:/g)].map(m=>m[1]);
  assert.ok(!groups.some(g=>places.includes(g)),'bölgə ilə şəhərin adı eyni olmasın');
  assert.equal(new Set(places).size,places.length,'təkrar yoxdur');
  for(const city of ['Bakı','Gəncə','Naxçıvan','Sumqayıt','Lənkəran','Mingəçevir','Naftalan','Xankəndi','Şəki','Şirvan','Yevlax'])assert.ok(places.includes(city),city);
});
test('language buttons show flags and keep the choice', () => {
  const ctx=app(),{S,languagePicker}=ctx.api;
  S.lang='tr';
  const html=languagePicker();
  assert.equal((html.match(/class="flag"/g)||[]).length,4);
  assert.ok(html.includes('data-lang="tr" aria-pressed="true"'));
  assert.ok(html.includes('data-lang="" aria-pressed="false"'));
});
test('the rates page shows a flag for currencies and a symbol for the rest', () => {
  const ctx=app(),{S,ratesView}=ctx.api;
  S.markets=[{id:'USD',label:'Dollar',value:1.7,dec:4,unit:'AZN'},{id:'BTC',label:'Bitcoin',value:7,dec:0,unit:'USD'},{id:'NEW',label:'Yeni',value:1,dec:0,unit:'USD'}];
  const html=ratesView();
  assert.ok(html.includes('class="flag"'));
  assert.ok(html.includes('₿'));
});
test('a team search finds every spelling, in every language, including the archive', () => {
  const ctx=app(),{S,searchView,searchTopics}=ctx.api,at=new Date().toISOString();
  const row=(id,title,lang,extra={})=>({id,title,lang,category:'idman',source:'APA',sourceUrl:'https://apa.az/'+id,publishedAt:at,...extra});
  S.lang='az';S.og={};S.club=null;S.shown=50;
  S.data={articles:[row('a','Fənərbağça məşqçisini dəyişdi','az'),row('b','Fenerbahçe transferi açıkladı','tr'),row('c','Фенербахче проиграл','ru'),row('d','Dünyada xəbər var','az')]};
  S.archive={idman:{at:Date.now(),rows:[row('e','Fənərbaxçanın köhnə oyunu','az')]}};
  for(const said of ['Fənərbaxça','Fənərbağça','fenerbahçe','Fənərbaxça xəbərləri']){
    S.q=said;
    assert.deepEqual(Array.from(searchTopics(said)),['Fenerbahçe'],said);
    const html=searchView();
    for(const id of 'abce')assert.ok(html.includes('apa.az/'+id),said+' '+id);
    assert.ok(!html.includes('apa.az/d'),said);
  }
});
test('an ordinary word is not taken for a team and keeps the language filter', () => {
  const ctx=app(),{S,searchView,searchTopics}=ctx.api,at=new Date().toISOString();
  assert.deepEqual(Array.from(searchTopics('sabah hava necə olacaq')),[]);
  assert.deepEqual(Array.from(searchTopics('fənər')),[]);
  S.lang='az';S.og={};S.club=null;S.shown=50;S.q='hava';
  S.data={articles:[{id:'a',title:'Sabah hava soyuyacaq',lang:'az',category:'gundem',source:'APA',sourceUrl:'https://apa.az/a',publishedAt:at},{id:'b',title:'Yarın hava soğuyacak',lang:'tr',category:'gundem',source:'NTV',sourceUrl:'https://ntv.com.tr/b',publishedAt:at}]};
  const html=searchView();
  assert.ok(html.includes('apa.az/a'));
  assert.ok(!html.includes('ntv.com.tr/b'));
});
test('hero and Zugulba retain multiple articles for their moving feeds', () => {
  const ctx=app(); const stories=Array.from({length:18},(_,i)=>({id:String(i),title:'News '+i,category:'gundem',source:'Source',sourceUrl:'https://example.com/'+i,imageUrl:'https://img.example/'+i+'.jpg',publishedAt:new Date().toISOString()}));
  const hero=ctx.api.heroBlock(stories),prez=ctx.api.prezBlock(stories.slice(0,8).map(s=>({...s,imageUrl:''})));
  assert.ok(hero.includes('class="hero-row"'));
  assert.equal((hero.match(/class="hero-main"/g)||[]).length,15);
  assert.ok(hero.includes('fetchpriority="high"') && (hero.match(/loading="lazy"/g)||[]).length>=1,'ilk slayd dərhal, qalanı tənbəl');
  assert.equal(ctx.api.heroBlock(stories.map(s=>({...s,imageUrl:''}))),'','şəkilsiz xəbər slayderə düşmür');
  const mixed=ctx.api.heroBlock([stories[0],{...stories[1],imageUrl:''},stories[2]]);
  assert.equal((mixed.match(/class="hero-main"/g)||[]).length,2);
  assert.ok(!mixed.includes('example.com/1"'),'şəkilsiz slayd yoxdur');
  assert.ok(!hero.includes('row-card'),'slayderin xəbərləri altında təkrarlanmır');
  assert.ok(prez.includes('data-prez-lent'));
  assert.equal((prez.match(/class="pcard"/g)||[]).length,8);
});

// Saytın dili: assets/dil.js, lüğətlər assets/dil-<kod>.js.
function dilModule(file) {
  const src = fs.readFileSync(path.join(root, file), 'utf8').replace(/^export default /m, 'globalThis.__d = ').replace(/^export (async )?function/gm, '$1function');
  const ctx = vm.createContext({ globalThis: {} });
  ctx.globalThis = ctx;
  vm.runInContext(src, ctx);
  return ctx;
}
test('site language: interface words and dates change, a news headline does not', () => {
  const mod = dilModule('assets/dil.js');
  const ru = dilModule('assets/dil-ru.js').__d;
  const tr = mod.makeTr(ru);
  assert.equal(tr('Baş səhifə'), 'Главная');
  assert.equal(tr('Hamısı →'), 'Все →', 'kənar işarə qalır');
  assert.equal(tr('14 dəqiqə əvvəl'), '14 мин. назад');
  assert.equal(tr('2 saat əvvəl'), '2 ч. назад');
  assert.equal(tr('4 mənbə'), '4 источн.');
  assert.equal(tr('9-cu tur'), '9-й тур');
  assert.equal(tr('Namaz · Bakı'), 'Намаз · Баку');
  assert.equal(tr('Yeniləndi: indicə'), 'Обновлено: только что');
  assert.equal(tr('3 noyabr 2026'), '3 ноября 2026');
  assert.equal(tr('9 sen, 23:00'), '9 сен, 23:00');
  assert.equal(tr('Sentyabr 2026'), 'Сентябрь 2026');
  assert.equal(tr('↑ 3 yeni xəbər'), '↑ 3 новых');
  assert.equal(tr('21 Cümadəl-ula'), '21 Джумада аль-уля');
  assert.ok(tr('«Bildiriş» düyməsi brauzerdən icazə istəyir; bildiriş yalnız səhifə açıq olanda, cihazın özündə yaranır, heç bir serverə göndərilmir.').startsWith('Кнопка'));
  assert.equal(tr('Bazar ertəsi, 2 noyabr 2026'), 'Понедельник, 2 ноября 2026');
  assert.equal(tr('Süper Liq oyunları hələ əlavə olunmayıb.'), 'Матчи турнира «Суперлига» пока не добавлены.');
  const head = 'Prezident İlham Əliyev Ankarada görüş keçirib';
  assert.equal(tr(head), head, 'xəbər başlığı tərcümə olunmur');
  assert.equal(tr(tr('Baş səhifə')), 'Главная', 'tərcümə ikinci dəfə dəyişmir');
});
test('site language: all three dictionaries have the same keys and no empty word by accident', () => {
  const [ru, tr, en] = ['ru', 'tr', 'en'].map(c => dilModule(`assets/dil-${c}.js`).__d);
  assert.deepEqual(Object.keys(tr.w), Object.keys(ru.w));
  assert.deepEqual(Object.keys(en.w), Object.keys(ru.w));
  for (const d of [ru, tr, en]) {
    assert.equal(d.mon.length, 12); assert.equal(d.monN.length, 12); assert.equal(d.mon3.length, 12); assert.equal(d.days.length, 7);
    assert.ok(['min', 'minS', 'mins', 'hm', 'hrs', 'hour', 'day', 'src', 'round', 'place', 'stage', 'checked', 'noGames', 'until', 'count', 'more', 'allSrc', 'page', 'noTeamNews', 'tracked', 'form', 'copy', 'fresh'].every(k => d.t[k]));
    assert.ok(Object.entries(d.w).every(([k, v]) => v || k === 'seçiminə basın'), 'boş tərcümə yoxdur');
  }
});
test('site language: every time the site writes («5 dəq əvvəl» on phones, the prayer countdown) changes language (owner 2026-11-08: «XX dəq əvvəl dil dəyişmir»)', () => {
  const mod = dilModule('assets/dil.js');
  const shown = new Set();
  for (const innerWidth of [390, 1280]) {
    const ctx = app({ innerWidth }), ago = vm.runInContext('ago', ctx), left = vm.runInContext('prayLeft', ctx);
    for (const m of [0, 1, 5, 59, 60, 61, 125, 1439, 1440, 3000]) { shown.add(ago(new Date(Date.now() - m * 60e3 - 5e3).toISOString())); shown.add(left(m)); }
  }
  assert.ok(shown.has('5 dəq əvvəl') && shown.has('5 dəqiqə əvvəl') && shown.has('2 saat 5 dəq'), [...shown].join(' | '));
  // Türkcədə «saat», «gün» eyni sözdür: orada yalnız Azərbaycan dilinə məxsus olanlar axtarılır.
  const AZ = { en: /ə|dəq|saat|gün|indi/, ru: /ə|dəq|saat|gün|indi/, tr: /ə|dəq|\bindi/ };
  for (const code of ['en', 'ru', 'tr']) {
    const tr = mod.makeTr(dilModule(`assets/dil-${code}.js`).__d);
    for (const s of shown) assert.ok(!AZ[code].test(tr(s)), `${code}: «${s}» → «${tr(s)}»`);
  }
  const [en, ru, tr] = ['en', 'ru', 'tr'].map(c => mod.makeTr(dilModule(`assets/dil-${c}.js`).__d));
  assert.deepEqual(['14 dəq əvvəl', '5 dəq', '2 saat 15 dəq', '3 saat', 'indi'].map(en), ['14 min ago', '5 min', '2 h 15 min', '3 h', 'now']);
  assert.deepEqual(['14 dəq əvvəl', '5 dəq', '2 saat 15 dəq', '3 saat', 'indi'].map(ru), ['14 мин. назад', '5 мин.', '2 ч. 15 мин.', '3 ч.', 'сейчас']);
  assert.deepEqual(['14 dəq əvvəl', '5 dəq', '2 saat 15 dəq', '3 saat', 'indi'].map(tr), ['14 dk önce', '5 dk', '2 sa 15 dk', '3 saat', 'şimdi']);
  assert.equal(en('yoxlanıb 11 dəq əvvəl'), 'checked 11 min ago', 'liqa səhifəsindəki «yoxlanıb» da');
});
test('site language: sports sub-sections read like the Azerbaijani ones — national teams, their competitions, groups and countries (owner 2026-11-08: «İdmanın alt bölmələri AZ dakı kimi deyil»)', () => {
  const mod = dilModule('assets/dil.js'), region = vm.runInContext('REGION', mod);
  // data/milli-menyu.json-un 2026-11-08 komandaları. Yeni komanda gələndə onun ISO kodunu dil.js REGION-a yazın.
  const TEAMS = ["Meksika","Cənubi Afrika","Cənubi Koreya","Çexiya","İsveçrə","Kanada","Bosniya və Herseqovina","Qətər","Braziliya","Mərakeş","Şotlandiya","Haiti","ABŞ","Avstraliya","Paraqvay","Türkiyə","Almaniya","Kot-d'İvuar","Ekvador","Kürasao","Hollandiya","Yaponiya","İsveç","Tunis","Belçika","Misir","İran","Yeni Zelandiya","İspaniya","Kabo-Verde","Uruqvay","Səudiyyə Ərəbistanı","Fransa","Norveç","Seneqal","İraq","Argentina","Avstriya","Əlcəzair","İordaniya","Kolumbiya","Portuqaliya","Konqo DR","Özbəkistan","İngiltərə","Xorvatiya","Qana","Panama","İtaliya","Yunanıstan","Serbiya","Danimarka","Uels","Sloveniya","Şimali Makedoniya","Şimali İrlandiya","Macarıstan","Ukrayna","Gürcüstan","Kosovo","İrlandiya","İsrail","Polşa","Rumıniya","Albaniya","Belarus","Finlandiya","San-Marino","Monteneqro","Kipr","Ermənistan","Latviya","Slovakiya","Farer adaları","Moldova","Qazaxıstan","İslandiya","Estoniya","Bolqarıstan","Lüksemburq","Malta","Cəbəllütariq","Andorra","Azərbaycan","Litva","Lixtenşteyn","Küveyt","Oman","Fələstin","Bəhreyn","Şimali Koreya","Suriya","Qırğızıstan","Çin","Tacikistan","Sinqapur","BƏƏ","Vyetnam","Yəmən","Tailand","İndoneziya","Qabon","Niger","Lesoto","Anqola","Malavi","Cənubi Sudan","Qambiya","Somali","Qvineya","Keniya","Eritreya","Zimbabve","Ekvatorial Qvineya","Syerra-Leone","Benin","Burkina-Faso","Mavritaniya","Mərkəzi Afrika Respublikası","Kamerun","Komor adaları","Namibiya","Konqo","Uqanda","Botsvana","Liviya","Zambiya","Toqo","Burundi","Mozambik","Sudan","Efiopiya","Ruanda","Mali","Liberiya","Qvineya-Bisau","Nigeriya","Madaqaskar","Tanzaniya","Dominikan Respublikası","Kosta-Rika","Trinidad və Tobaqo","Nikaraqua","Qvatemala","Yamayka","Surinam","Honduras","Martinika","Salvador","Qayana","Puerto-Riko","Kayman adaları","Dominika","Barbados","Sent-Lüsiya","Qvadelupa","Bermud adaları","Kuba","Sent-Kits və Nevis","Bonayre","Qrenada","Sent-Vinsent və Qrenadinlər","Fransız Qvianası","Beliz","Sint-Marten","Monserrat","Törks və Kaykos adaları","Britaniya Virgin adaları","Antiqua və Barbuda","Aruba","Angilya","Sen-Marten","ABŞ Virgin adaları","Baham adaları"];
  const LABELS = ['Milli komandalar', 'Pro Liqa', 'Dünya Çempionatı 2026', 'Avropa Çempionatı 2028: seçmə', 'Millətlər Liqası A', 'Millətlər Liqası D', 'Asiya Kuboku 2027', 'Afrika Millətlər Kuboku 2027: seçmə', 'KONKAKAF Millətlər Liqası C', 'Qrup A', 'Qrup 4', 'Dünya Çempionatı 2026: xəbərlər', 'Misli Premier League: xəbərlər'];
  for (const code of ['en', 'ru', 'tr']) {
    const d = dilModule(`assets/dil-${code}.js`).__d, tr = mod.makeTr(d, code);
    for (const s of LABELS) assert.ok(!/ə|Liqası|Kuboku|Çempionat|Qrup|seçmə|komandalar|xəbərlər/.test(tr(s)), `${code}: «${s}» → «${tr(s)}»`);
    for (const s of TEAMS) {
      assert.ok(d.w[s] !== undefined || region[s], `«${s}»: nə lüğətdə, nə REGION-da`);
      assert.ok(!/ə/.test(tr(s)), `${code}: «${s}» → «${tr(s)}»`);
    }
    assert.equal(tr('Seriya A'), d.w['Seriya A'], 'lüğətdəki tam ad qaydadan əvvəldir');
    assert.equal(tr('Prezident İlham Əliyev Ankarada görüş keçirib'), 'Prezident İlham Əliyev Ankarada görüş keçirib', 'xəbər başlığı tərcümə olunmur');
  }
  const [en, ru, tr] = ['en', 'ru', 'tr'].map(c => mod.makeTr(dilModule(`assets/dil-${c}.js`).__d, c));
  assert.deepEqual(['Dünya Çempionatı 2026', 'Millətlər Liqası A: xəbərlər', 'Qrup K', 'Meksika', 'Uels'].map(en), ['World Cup 2026', 'Nations League A: news', 'Group K', 'Mexico', 'Wales']);
  assert.deepEqual(['Afrika Millətlər Kuboku 2027: seçmə', 'Cənubi Koreya'].map(ru), ['Кубок африканских наций 2027: отбор', 'Южная Корея']);
  assert.deepEqual(['Milli komandalar', 'Uels', 'Bosniya və Herseqovina'].map(tr), ['Milli takımlar', 'Galler', 'Bosna-Hersek']);
});
test('Telegram top 10: the header link and words follow the site language; other languages go to the bot in their own language (owner 2026-11-08: «günün 10 əsas xəbəri teleqramda digər dillərə dəyişmir»)', () => {
  const ctx = app({ window: { addEventListener() {}, SITE_CONFIG: { tgBot: 'sekkizulduz_xeber_bot', telegram: 'https://t.me/sekkizulduz_az' } } });
  const link = vm.runInContext('tgDigest', ctx), { S } = ctx.api;
  S.lang = 'az'; assert.equal(link(), 'https://t.me/sekkizulduz_az', 'Azərbaycan dili: kanal');
  S.lang = null; assert.equal(link(), 'https://t.me/sekkizulduz_az', '«Hamısı»: kanal');
  const bot = require('../.github/scripts/izle.cjs');
  for (const l of ['en', 'ru', 'tr']) {
    S.lang = l; assert.equal(link(), `https://t.me/sekkizulduz_xeber_bot?start=g_${l}`);
    assert.ok(bot.DIGEST_LANGS[l] && bot.catalog(bot.loadApp ? bot.loadApp(root) : require('../.github/scripts/topics.cjs').loadApp(root)).has(`g_${l}`), `bot g_${l} açarını tanıyır`);
  }
  const src = fs.readFileSync(path.join(root, 'assets/app.js'), 'utf8');
  assert.ok(src.includes('<a class="nav-tg" href="${esc(tgDigest())}"'), 'başlıqdakı keçid dilə görə');
  const mod = dilModule('assets/dil.js');
  const want = { en: 'Top 10 stories of the day — on Telegram', ru: '10 главных новостей дня — в Telegram', tr: "Günün en önemli 10 haberi — Telegram'da" };
  for (const l of ['en', 'ru', 'tr']) {
    const tr = mod.makeTr(dilModule(`assets/dil-${l}.js`).__d, l);
    assert.equal(tr('📩 Günün 10 əsas xəbəri — Telegram-da'), '📩 ' + want[l]);
    assert.ok(!/ə/.test(tr('Hər gün 09:00 və 19:00')), l + ': düymənin izahı');
  }
});
test('site language: a section without news in that language is hidden, sports never', () => {
  const { emptySections } = dilModule('assets/dil.js');
  const list = [{ category: 'bolgeler', lang: 'az' }, { category: 'dunya', lang: 'ru' }, { category: 'dunya', lang: 'az' }, { category: 'idman', lang: 'az' }, { category: 'gundem' }];
  assert.deepEqual([...emptySections(list, 'ru')].sort(), ['bolgeler', 'gundem']);
  assert.deepEqual([...emptySections(list, 'en')].sort(), ['bolgeler', 'dunya', 'gundem']);
  assert.deepEqual([...emptySections(null, 'ru')], []);
  // Bölmə keçidləri /bolme/<ad>/ ünvanıdır: köhnə «#/bolme/» seçicisi heç nə tapmırdı və boş bölmə gizlənmirdi
  const dil = fs.readFileSync(path.join(root, 'assets/dil.js'), 'utf8'), shell = fs.readFileSync(path.join(root, 'index.html'), 'utf8');
  assert.ok(dil.includes(`querySelectorAll('a[href^="/bolme/"]')`) && dil.includes('.slice(7).split(/[/?#]/)[0]'), 'gizlətmə əsl keçidləri seçir');
  assert.ok(/<a href="\/bolme\/[a-z-]+\/"/.test(shell) && !shell.includes('href="#/bolme/'), 'saytın bölmə keçidləri həmin şəkildədir');
});
test('site language: a headline word that is also an Object.prototype name is not «translated»', () => {
  const mod = dilModule('assets/dil.js');
  for (const code of ['en', 'ru', 'tr']) {
    const tr = mod.makeTr(dilModule(`assets/dil-${code}.js`).__d, code);
    for (const s of ['F1: constructor', 'X, valueOf', 'constructor', 'toString', '__proto__', 'hasOwnProperty 2026', 'toString A']) assert.equal(tr(s), s, code + ': ' + s);
  }
});
test('site language: Azerbaijani visitors do not load the translation', () => {
  const src = fs.readFileSync(path.join(root, 'assets/app.js'), 'utf8'), index = fs.readFileSync(path.join(root, 'index.html'), 'utf8');
  assert.ok(!index.includes('dil.js') && !fs.readFileSync(path.join(root, 'sw.js'), 'utf8').includes('dil.js'), 'əvvəlcədən yüklənmir');
  assert.equal(src.split('import("./dil.js")').length - 1, 1);
  const at = src.indexOf('import("./dil.js")');
  assert.ok(src.slice(at - 260, at).includes('if (uiLang(S.lang))'), 'yalnız başqa dil seçiləndə');
  for (const f of ['assets/dil.js', 'assets/dil-ru.js', 'assets/dil-tr.js', 'assets/dil-en.js']) assert.ok(fs.statSync(path.join(root, f)).size < 60e3, f);
});
// Sürət (qırmızı xətt 3): index.html qabığı statik daşıyır — CSS gələn kimi başlıq, bölmələr və skelet çəkilir, JS gözlənilmir.
// Statik nüsxə app.js shell()-in çıxışı ilə eynidir ki, JS gələndə səhifə atlamasın.
function shellParts(file) {
  const els = {};
  const el = id => els[id] ||= { id, _html: '', set innerHTML(v) { this._html = v; }, get innerHTML() { return this._html; }, addEventListener() {}, classList: { toggle() {}, add() {}, remove() {} }, querySelector() { return null; }, querySelectorAll() { return []; }, focus() {}, dataset: {}, style: {}, setAttribute() {}, set onclick(f) {}, hidden: false };
  const ctx = app({
    location: { hash: '#/', href: 'https://8ulduz.az/' }, history: { replaceState() {} },
    window: { addEventListener() {}, SITE_CONFIG: { goatcounter: '', telegram: '', contact: '' } },
    document: { documentElement: { dataset: {}, style: {} }, hidden: false, activeElement: null, addEventListener() {}, querySelector(s) { const m = s.match(/^#([\w-]+)$/); return m ? el(m[1]) : null; }, querySelectorAll() { return []; }, createElement() { return { set innerHTML(v) { this._v = v; }, content: {}, children: [] }; } },
    requestAnimationFrame: () => 0,
  }, file);
  vm.runInContext(tr('shell(); renderNav(); renderLangs();', file), ctx);
  return { app: els.app.innerHTML, nav: els.nav.innerHTML, inst: els.inst.innerHTML, skeleton: vm.runInContext(tr('skeleton()', file), ctx) };
}
test('speed red line: index.html carries the same shell app.js builds, with nav and skeleton filled', () => {
  const index = fs.readFileSync(path.join(root, 'index.html'), 'utf8').replace(/\r\n/g, '\n');
  const parts = shellParts();
  const m = index.match(/<div id="app" data-shell="1">([\s\S]*?)<\/div>\n  <\/body>/);
  assert.ok(m, 'index.html-də data-shell qabığı yoxdur');
  let want = parts.app;
  want = want.replace(/(<nav class="main" id="nav" aria-label="Bölmələr">)(<\/nav>)/, (_, a, b) => a + parts.nav + b);
  want = want.replace(/(<span class="inst" id="inst">)(<\/span>)/, (_, a, b) => a + parts.inst + b);
  // #view: ya statik skelet, ya da pipeline-ın hazır ilk ekranı (.github/scripts/prerender.cjs); qabığın qalanı eyni olmalıdır.
  const got = m[1].match(/(<div class="wrap" id="view" tabindex="-1">)([\s\S]*?)(<noscript>Saytı görmək üçün JavaScript-i aktiv edin\.<\/noscript><\/div><\/main>)/);
  assert.ok(got, 'index.html-də #view bloku və noscript yoxdur');
  const pre = /^<div class="pre-skel" data-prerender="[^"]+">[\s\S]*<section class="hero">[\s\S]*<\/div>$/.test(got[2]);
  assert.ok(pre || got[2] === '<div class="pre-skel">' + parts.skeleton + '</div>', '#view-də skelet və ya hazır ilk ekran olmalıdır');
  want = want.replace(/(<div class="wrap" id="view" tabindex="-1">)(<\/div>)/, (_, a, b) => a + got[2] + '<noscript>Saytı görmək üçün JavaScript-i aktiv edin.</noscript>' + b);
  // #topbar: ya boş, ya da pipeline-ın hazır yuxarı zolağı (lupa düyməsi JS gələndə sıçramasın); qabığın qalanı eyni olmalıdır.
  const tb = m[1].match(/<div class="wrap" id="topbar">([^\n]*)<\/div><\/div>$/m);
  assert.ok(tb && (tb[1] === '' || (tb[1].includes('data-act="theme"') && tb[1].includes('class="wx'))), '#topbar boş və ya hazır zolaq olmalıdır');
  // #mk: ya boş («pending»), ya da pipeline-ın hazır valyuta kartları (sahib 2026-11-14: açılışda sıçramasın).
  const mk = m[1].match(/<div class="markets( pending)?" id="markets"><div class="wrap mk-wrap"><div class="mk-grid" id="mk">([^\n]*?)<\/div><p class="mk-note"/);
  assert.ok(mk && (mk[1] ? mk[2] === '' : mk[2].includes('class="mk"')), '#mk boş (pending) və ya hazır valyuta kartları olmalıdır');
  const shellOf = s => s.replace(tb[0], '<div class="wrap" id="topbar"></div></div>').replace(mk[0], '<div class="markets pending" id="markets"><div class="wrap mk-wrap"><div class="mk-grid" id="mk"></div><p class="mk-note"');
  assert.equal(shellOf(m[1]), want, 'index.html qabığı app.js shell() ilə eyni deyil');
  const src = fs.readFileSync(path.join(root, 'assets/app.js'), 'utf8');
  assert.ok(src.includes('if (!$("#app").dataset?.shell) $("#app").innerHTML'), 'shell() statik qabığı silməməlidir');
});
test('speed red line: no web font is downloaded; header has no backdrop blur', () => {
  const index = fs.readFileSync(path.join(root, 'index.html'), 'utf8'), css = fs.readFileSync(path.join(root, 'assets/app.css'), 'utf8'), sw = fs.readFileSync(path.join(root, 'sw.js'), 'utf8'), updater = fs.readFileSync(path.join(root, 'updater.py'), 'utf8');
  for (const [name, text] of [['index.html', index], ['sw.js', sw], ['updater.py', updater], ['app.css', css]]) assert.ok(!/fonts\.css|as="font"|woff2|@font-face/.test(text), name + ' şrift yükləyir');
  assert.ok(!fs.existsSync(path.join(root, 'assets/fonts')), 'assets/fonts qovluğu qalıb');
  assert.ok(!/backdrop-filter/.test(css), 'backdrop-filter telefonda sürüşməni ağırlaşdırır');
  assert.ok(index.includes('<link rel="preconnect" href="https://raw.githubusercontent.com" crossorigin />'), 'canlı kanalın hostu əvvəlcədən açılmalıdır');
});
test('speed red line: a shared link renders the story from the share index before the full feed', async () => {
  const ctx = app({ location: { hash: '#/xeber/0a0a0a0a0a0a0a0a' } });
  const { S, loadShared, articleView } = ctx.api;
  const asked = [];
  ctx.asked = asked;
  vm.runInContext(`requestJSON = async url => { asked.push(url.split("?")[0]); return { d: { parts: 256, articles: [
    { id: "0a0a0a0a0a0a0a0a", of: "0b0b0b0b0b0b0b0b" },
    { id: "0b0b0b0b0b0b0b0b", title: "Pensiyalar artırılır", source: "APA", sourceUrl: "https://apa.az/x", publishedAt: new Date().toISOString(), category: "sosial", lang: "az" } ] } }; };
    renderView = () => { globalThis.rendered = (globalThis.rendered || 0) + 1; };`, ctx);
  await loadShared('0a0a0a0a0a0a0a0a');
  assert.deepEqual(asked, ['data/paylas/10.json', 'data/paylas/11.json'], '0a→hissə 10, of ilə 0b→hissə 11 (256 hissə: id-nin ilk iki hex rəqəmi)');
  assert.equal(S.sharedStory.row.title, 'Pensiyalar artırılır');
  assert.equal(ctx.rendered, 1, 'tam lent olmadan çəkilir');
  assert.equal(S.data, null);
  assert.ok(articleView('0a0a0a0a0a0a0a0a').includes('Pensiyalar artırılır'), 'xəbər səhifəsi tam lentsiz qurulur');
  const index = fs.readFileSync(path.join(root, 'index.html'), 'utf8');
  assert.ok(index.includes('files.unshift("data/paylas/" + parseInt(art[1].slice(0, 2), 16) + ".json")'), 'index.html paylaşma hissəsini (256-dan birini) erkən istəyir');
});
test('speed 2026-11-09: share list 32 → 256 parts — the old part (>> 3) is read only while the file is missing or still in the old split', async () => {
  const row = id => ({ id, title: 'Köhnə bölgüdən', source: 'APA', sourceUrl: 'https://apa.az/' + id, publishedAt: new Date().toISOString(), category: 'sosial', lang: 'az' });
  const run = async (id, files) => {
    const ctx = app({ location: { hash: '#/xeber/' + id } });
    ctx.asked = []; ctx.files = files;
    vm.runInContext(`requestJSON = async url => { const p = url.split("?")[0]; asked.push(p); if (!(p in files)) throw new Error("HTTP 404"); return { d: files[p] }; };`, ctx);
    return { asked: ctx.asked, row: await ctx.api.shareRow(id) };
  };
  // Sayt yeni, updater köhnə: 90.json yoxdur (404) → köhnə hissə 11 (0x5a >> 3).
  let got = await run('5a5a5a5a5a5a5a5a', { 'data/paylas/11.json': { articles: [row('5a5a5a5a5a5a5a5a')] } });
  assert.deepEqual(got.asked, ['data/paylas/90.json', 'data/paylas/11.json']); assert.equal(got.row?.title, 'Köhnə bölgüdən');
  // 0x0a = 10: fayl var, amma köhnə bölgülü (parts yoxdur) → köhnə hissə 1.
  got = await run('0a0a0a0a0a0a0a0a', { 'data/paylas/10.json': { articles: [] }, 'data/paylas/1.json': { articles: [row('0a0a0a0a0a0a0a0a')] } });
  assert.deepEqual(got.asked, ['data/paylas/10.json', 'data/paylas/1.json']); assert.equal(got.row?.title, 'Köhnə bölgüdən');
  // Yeni bölgü (parts 256) sətri tapmır → ikinci sorğu yoxdur (arxiv budağı növbətidir).
  got = await run('0a0a0a0a0a0a0a0a', { 'data/paylas/10.json': { parts: 256, articles: [] }, 'data/paylas/1.json': { articles: [row('0a0a0a0a0a0a0a0a')] } });
  assert.deepEqual(got.asked, ['data/paylas/10.json']); assert.equal(got.row, null);
  // Hər iki fayl alınmır (şəbəkə): əvvəlki kimi xəta qalxır, çağıran (loadShared/scanArchives) tutur. Hissə 0: köhnə və yeni hissə eynidir, təkrar sorğu yoxdur.
  const ctx0 = app({ location: { hash: '#/xeber/0101010101010101' } }); ctx0.asked = [];
  vm.runInContext(`requestJSON = async url => { asked.push(url.split("?")[0]); throw new Error("HTTP 404"); };`, ctx0);
  await assert.rejects(ctx0.api.shareRow('0101010101010101'), /HTTP 404/);
  assert.deepEqual(ctx0.asked, ['data/paylas/1.json', 'data/paylas/0.json']);
  got = await run('0000000000000000', {});
  assert.deepEqual(got.asked, ['data/paylas/0.json']); assert.equal(got.row, null);
  const up = fs.readFileSync(path.join(root, 'updater.py'), 'utf8');
  assert.ok(up.includes('SHARE_KEEP_S, SHARE_PARTS = 25 * 3600, 256') && up.includes('return int(sid[:2], 16) if re.fullmatch') && up.includes('"parts": SHARE_PARTS'), 'updater 256 hissə yazır və faylda bölgünü deyir');
});
test('owner 2026-11-07: an old shared link (?h=hour) opens from the archive branch even if the feed arrives meanwhile', async () => {
  const ctx = app({ location: { hash: '#/xeber/0c0c0c0c0c0c0c0c?b=sosial&h=26110713' } });
  const { S, loadShared, articleView } = ctx.api;
  const asked = [];
  ctx.asked = asked;
  vm.runInContext(`requestJSON = async url => { asked.push(url.split("?")[0]); if (url.includes("/arxiv/")) { S.data = { articles: [] };
    return { d: { articles: [{ id: "0c0c0c0c0c0c0c0c", title: "Köhnə xəbər", source: "APA", sourceUrl: "https://apa.az/k", publishedAt: "2026-11-07T13:05:00Z", category: "sosial", lang: "az" }] } }; }
    return { d: { parts: 256, articles: [] } }; };
    renderView = () => {};`, ctx);
  await loadShared('0c0c0c0c0c0c0c0c');
  assert.deepEqual(asked, ['data/paylas/12.json', 'https://raw.githubusercontent.com/8ulduz/8ulduz/arxiv/saat/26110713.json'], 'əvvəl paylaşma siyahısı, sonra saatın arxiv faylı');
  assert.ok(articleView('0c0c0c0c0c0c0c0c').includes('Köhnə xəbər'), 'lent arada gəlsə də xəbər açılır');
});
test('speed red line: the cached feed is shown before the network answers and then replaced', async () => {
  const first = { updatedAt: 'old', articles: [{ id: 'c1', title: 'Keşdən xəbər', source: 'APA', sourceUrl: 'https://apa.az/1', publishedAt: new Date().toISOString(), category: 'gundem', lang: 'az' }] };
  const matched = [];
  const ctx = app({ location: { hash: '#/', href: 'https://8ulduz.az/' }, caches: { keys: async () => ['8ulduz-static-v33', '8ulduz-data-v33'], open: async name => ({ match: async url => { matched.push(name + ' ' + url); return url.endsWith('/data/first.json') ? { json: async () => first } : undefined; } }) } });
  const { S, loadCached, loadFirst } = ctx.api;
  await loadCached();
  // 2026-11-13: ilk ekranın faylından sonra keşdəki dəqiqəlik lent də oxunur (dilin faylı, yoxdursa ümumi) — eyni keşdən, şəbəkəsiz.
  assert.deepEqual(matched, ['8ulduz-data-v33 https://8ulduz.az/data/first.json', '8ulduz-data-v33 https://8ulduz.az/data/latest.az.json', '8ulduz-data-v33 https://8ulduz.az/data/latest.json']);
  assert.equal(S.data.articles[0].title, 'Keşdən xəbər');
  assert.equal(S.partial, true);
  ctx.fetch = async () => ({ ok: true, headers: new Headers(), json: async () => ({ updatedAt: 'new', articles: [{ id: 'n1', title: 'Şəbəkədən xəbər', source: 'APA', sourceUrl: 'https://apa.az/2', publishedAt: new Date().toISOString(), category: 'gundem', lang: 'az' }] }) });
  await loadFirst();
  assert.equal(S.data.articles[0].title, 'Şəbəkədən xəbər', 'şəbəkədən gələn ilk ekran keşdəkini əvəz edir');
  assert.equal(S.fromCache, false);
});
// Sahib 2026-11-13 (telefon videosu): yeniləyəndə ən yeni xəbərlər ~1,5 s itib köhnə siyahı görünür, sonra qayıdırdı. İlk ekranın faylı
// 10 dəqiqəlikdir; ondan sonra çıxan sətirlər keşdəki dəqiqəlik lentdən üstə qoyulur və şəbəkədən gələn ilk ekran onları silmir.
test('owner 2026-11-13: a reload keeps the newest stories — cached minute feed rows sit on top of the cached first screen and survive the network one', async () => {
  const at = Date.parse('2026-11-13T12:36:30Z'), iso = ms => new Date(at + ms).toISOString();
  const row = (id, title, ms, source = 'APA') => ({ id, title, source, sourceUrl: 'https://apa.az/' + id, publishedAt: iso(ms), category: 'gundem', lang: 'az' });
  const first = { updatedAt: iso(0), articles: [row('f1', 'İlk ekrandakı xəbər', -60e3)] };
  const latest = { updatedAt: iso(120e3), articles: [row('l1', 'Dəqiqəlik lentin yeni xəbəri', 90e3), row('f1', 'İlk ekrandakı xəbər', -60e3), row('l0', 'Çoxdankı xəbər', -3600e3),
    { ...row('x1', 'Azadlıq xəbəri', 95e3), source: 'Azadlıq', sourceUrl: 'https://www.azadliq.org/a/1.html' }] };
  const open = files => async () => ({ match: async url => { const f = files[url.split('/data/')[1]]; return f ? { json: async () => f } : undefined; } });
  const start = files => { const ctx = app({ location: { hash: '#/', href: 'https://8ulduz.az/' }, caches: { keys: async () => ['8ulduz-data'], open: open(files) } }); vm.runInContext('globalThis.renders = 0; render = () => { renders++; };', ctx); return ctx; };
  const titles = S => Array.from(S.data.articles, a => a.title);

  let ctx = start({ 'first.json': first, 'latest.az.json': latest });
  let { S, loadCached, loadFirst } = ctx.api;
  await loadCached();
  assert.deepEqual(titles(S), ['Dəqiqəlik lentin yeni xəbəri', 'İlk ekrandakı xəbər'], 'yeni sətir üstdədir; ilk ekranda olan təkrarlanmır, köhnə və qadağan mənbə düşmür');
  assert.equal(S.partial, true); assert.equal(S.fromCache, true);
  // Şəbəkədən daha təzə ilk ekran gəlir: keşdən üstə qoyulan sətir qalır, şəbəkə nüsxəsində də varsa bir dəfə görünür.
  ctx.fetch = async () => ({ ok: true, headers: new Headers(), json: async () => ({ updatedAt: iso(60e3), articles: [row('f2', 'Şəbəkədən xəbər', 30e3), row('f1', 'İlk ekrandakı xəbər', -60e3)] }) });
  await loadFirst();
  assert.deepEqual(titles(S), ['Dəqiqəlik lentin yeni xəbəri', 'Şəbəkədən xəbər', 'İlk ekrandakı xəbər']);
  assert.equal(S.fromCache, false);

  // Dil faylı yoxdursa ümumi dəqiqəlik lent; ilk ekrandan köhnə dəqiqəlik lent işlədilmir.
  ctx = start({ 'first.json': first, 'latest.json': latest }); await ctx.api.loadCached();
  assert.equal(titles(ctx.api.S)[0], 'Dəqiqəlik lentin yeni xəbəri');
  ctx = start({ 'first.json': first, 'latest.az.json': { ...latest, updatedAt: iso(-120e3) } }); await ctx.api.loadCached();
  assert.deepEqual(titles(ctx.api.S), ['İlk ekrandakı xəbər']);
  // Şəbəkə keşi qabaqlayır (ilk ekranın faylı keş oxunuşundan tez gəlir): yeni sətirlər yenə üstdədir.
  ctx = start({ 'first.json': first, 'latest.az.json': latest });
  ctx.fetch = async () => ({ ok: true, headers: new Headers(), json: async () => ({ updatedAt: iso(60e3), articles: [row('f2', 'Şəbəkədən xəbər', 30e3)] }) });
  const slow = ctx.api.loadCached(); await ctx.api.loadFirst(); await slow;
  assert.deepEqual(titles(ctx.api.S), ['Dəqiqəlik lentin yeni xəbəri', 'Şəbəkədən xəbər', 'İlk ekrandakı xəbər'], 'dəqiqəlik lentin son 10 dəqiqəlik sətirləri: şəbəkə nüsxəsində olmayan da');
});
test('speed red line: un-proxied originals are still shown, but never with high priority', () => {
  const phone = app({ matchMedia: q => ({ matches: q === '(hover:none)' }) }).api, desktop = app().api;
  const heavy = { id: 'h', title: 'Ağır şəkil', source: 'Qafqazinfo', sourceUrl: 'https://qafqazinfo.az/a', imageUrl: 'https://qafqazinfo.az/uploads/1/tramp.jpg', publishedAt: new Date().toISOString(), category: 'gundem' };
  const light = { ...heavy, id: 'l', sourceUrl: 'https://apa.az/a', imageUrl: 'https://apa.az/img/1.jpg' };
  assert.equal(phone.heavyImage(heavy.imageUrl), true);
  assert.equal(phone.heavyImage('https://wsrv.nl/?url=x'), false);
  for (const ctx of [phone, desktop]) {
    assert.ok(ctx.cardAt(heavy, 'h3').includes('qafqazinfo.az/uploads/1/tramp.jpg'), 'şəkil həmişə görünür («şəkil gəlmir» olmasın)');
    assert.ok(ctx.cardAt(light, 'h3').includes('https://wsrv.nl/'), 'kiçildilən şəkil proksidən gəlir');
    assert.ok(ctx.img(heavy, '', true).includes('loading="lazy"') && !ctx.img(heavy, '', true).includes('fetchpriority'), 'ağır orijinal yüksək prioritet almır');
    assert.ok(ctx.img(light, '', true).includes('fetchpriority="high"'), 'kiçildilən ilk şəkil yüksək prioritetdədir');
  }
  const { imageCandidates } = desktop;
  assert.deepEqual([...imageCandidates({ imageUrl: 'https://qafqazinfo.az/1.jpg', alts: [{ imageUrl: 'https://apa.az/2.jpg' }] })], ['https://apa.az/2.jpg', 'https://qafqazinfo.az/1.jpg'], 'proksidən keçməyən sayt sona düşür');
});

// CSP: daxili skript yalnız hash ilə, daxili hadisə işləyicisi yoxdur.
test('content security policy allows only the page own inline script', () => {
  const crypto = require('crypto');
  const read = p => fs.readFileSync(path.join(root, p), 'utf8').replace(/\r\n/g, '\n');
  const index = read('index.html');
  const policy = index.match(/http-equiv="Content-Security-Policy" content="([^"]+)"/)[1];
  assert.ok(!policy.includes('unsafe-inline'));
  assert.ok(!/connect-src|default-src/.test(policy), 'canlı kanal CSP ilə bloklanmamalıdır');
  assert.ok(policy.includes('https://gc.zgo.at') && policy.includes('https://8ulduz.goatcounter.com'));
  const inline = [...index.matchAll(/<script>([\s\S]*?)<\/script>/g)].map(m => m[1]);
  assert.equal(inline.length, 1);
  const hash = crypto.createHash('sha256').update(inline[0], 'utf8').digest('base64');
  assert.ok(policy.includes("'sha256-" + hash + "'"), 'inline skript dəyişib, CSP hash-i yenilənməlidir');
  const updater = read('updater.py');
  const template = updater.match(/_CSP = "([^"]+)"/)[1].replace('{hashes}', "'sha256-" + hash + "'");
  assert.equal(template, policy);
  for (const p of ['index.html', 'assets/app.js', 'assets/komanda.js', 'assets/dil.js', 'assets/reader.js', 'assets/assistant.js', 'assets/sehife.js'])
    assert.ok(!/\son(error|load|click|change|input|submit)=["']/.test(read(p)), p + ' daxili hadisə işləyicisi saxlayır');
});

// Komanda səhifəsi: assets/komanda.js modulu eyni kontekstdə, app.js-in köməkçiləri ilə işləyir.
function teamPage(files, articles = []) {
  const ctx = app({ history: { pushState() {}, back() {} }, Promise, RegExp, WeakMap });
  const source = fs.readFileSync(path.join(root, 'assets/komanda.js'), 'utf8').replace(/^export /gm, '');
  vm.runInContext(source, ctx);
  ctx.files = files; ctx.articles = articles; ctx.renders = 0; ctx.asked = [];
  vm.runInContext(`S.data = { articles }; S.shown = 48;
    requestJSON = async url => { const p = url.split("?")[0]; asked.push(p); if (!files[p]) throw Error("404"); return { d: files[p] }; };
    globalThis.team = mountTeam({ S, esc, card, byDate, sized, shortDT, ordinal: ordTur, ago, decode, clubMatches, topics: SPORT_TEAMS.flatMap(g => g.items).filter(t => t.name !== "Milli komanda"), withArchive, loadArchive: () => {}, months: MONTHS, requestJSON: (...a) => requestJSON(...a), freshUrl, requestRender: () => { renders++; } });`, ctx);
  return ctx;
}
const TEAM_INDEX = { checked: { 'premyer-liqa': '2026-11-01T07:00:00+00:00' }, leagues: [
  { id: 'premyer-liqa', name: 'Misli Premyer Liqası', short: 'Premyer Liqa', source: 'pfl.az', ready: [{ key: '2026', label: '2026-27' }, { key: '2025', label: '2025-26' }], teams: ['qarabag', 'sabah', 'sefa'], heyet: [] },
  { id: 'kubok', name: 'Azərbaycan Kuboku', short: 'Kubok', source: 'pfl.az', ready: [{ key: '2026', label: '2026-27' }], teams: ['qarabag', 'sumqayit'], heyet: [] },
  { id: 'evezediciler', name: 'Əvəzedicilər Liqası', short: 'Əvəzedicilər', source: 'pfl.az', reserve: true, ready: [{ key: '2026', label: '2026-27' }], teams: ['qarabag'], heyet: [] },
  { id: 'turkiye', name: 'Türkiyə Süper Liqası', short: 'Türkiyə', source: 'ESPN', ready: [{ key: '2026', label: '2026-27' }], teams: ['fenerbahce', 'besiktas'], heyet: ['fenerbahce'] },
] };
const PREMYER = { id: 'premyer-liqa', name: 'Misli Premyer Liqası', short: 'Premyer Liqa', source: 'pfl.az', key: '2026', season: '2026-27',
  teams: { qarabag: { name: 'Qarabağ', logo: 'https://pfl.az/q.png' }, sabah: { name: 'Sabah', logo: '' }, sefa: { name: 'Şəfa', logo: '' } },
  groups: [{ name: '', rows: [{ pos: 1, team: 'sabah', p: 2, w: 2, d: 0, l: 0, gf: 3, ga: 0, gd: 3, pts: 6 }, { pos: 2, team: 'qarabag', p: 2, w: 1, d: 0, l: 1, gf: 2, ga: 1, gd: 1, pts: 3 }, { pos: 3, team: 'sefa', p: 2, w: 0, d: 0, l: 2, gf: 0, ga: 4, gd: -4, pts: 0 }] }],
  games: [
    { home: 'qarabag', away: 'sefa', hs: 2, as: 0, date: '2026-08-14T19:30+04:00', played: true, round: '1' },
    { home: 'sabah', away: 'qarabag', hs: 1, as: 0, date: '2026-08-21T19:30+04:00', played: true, round: '2' },
    { home: 'qarabag', away: 'sabah', date: '2099-11-06T18:00+04:00', played: false, round: '3' },
    { home: 'sefa', away: 'qarabag', date: '2020-01-01T18:00+04:00', played: false, state: 'off', round: '4' },
  ] };
const KUBOK = { id: 'kubok', name: 'Azərbaycan Kuboku', short: 'Kubok', source: 'pfl.az', key: '2026', season: '2026-27', teams: { qarabag: { name: 'Qarabağ', logo: '' }, sumqayit: { name: 'Sumqayıt', logo: '' } }, groups: [], games: [{ home: 'sumqayit', away: 'qarabag', date: '2099-12-01T18:00+04:00', played: false, round: '1/8 final' }] };
const TURKIYE = { id: 'turkiye', name: 'Türkiyə Süper Liqası', short: 'Türkiyə', source: 'ESPN', key: '2026', season: '2026-27', teams: { fenerbahce: { name: 'Fenerbahçe', logo: '', id: '436' }, besiktas: { name: 'Beşiktaş', logo: '', id: '1895' } },
  groups: [{ name: 'Lig', rows: [{ pos: 1, team: 'fenerbahce', p: 1, w: 1, d: 0, l: 0, gf: 1, ga: 0, gd: 1, pts: 3, note: 'Champions League', color: '#81D6AC' }, { pos: 2, team: 'besiktas', p: 1, w: 0, d: 0, l: 1, gf: 0, ga: 1, gd: -1, pts: 0, note: 'Relegation', color: 'red;background:url(x)' }] }], games: [] };
const teamFiles = () => ({ 'data/futbol/index.json': TEAM_INDEX, 'data/futbol/premyer-liqa.json': PREMYER, 'data/futbol/kubok.json': KUBOK, 'data/futbol/turkiye.json': TURKIYE,
  'data/futbol/heyet-turkiye.json': { teams: { fenerbahce: { players: [{ name: 'Mert Günok', pos: 'gk', no: '34', age: 37 }, { name: 'Dusan Tadic', pos: 'mf', no: '10' }] } } } });
const tick = () => new Promise(done => setImmediate(done));
// Fayllar gələnə qədər səhifə yükləmə göstərir; hər çağırış çatmayan faylı istəyir.
async function teamHtml(ctx, r) {
  const route = { tab: '', season: '', ...r };
  let html = '';
  for (let i = 0; i < 5; i++) { ctx.route_ = route; html = vm.runInContext('team.view(route_)', ctx); await tick(); }
  return html;
}

test('team route: league, club, tab and season come from the address', () => {
  const ctx = app();
  const at = hash => { ctx.location.hash = hash; return ctx.api.route(); };
  assert.equal(at('#/komanda/premyer-liqa/qarabag').name, 'team');
  assert.equal(at('#/komanda/premyer-liqa/qarabag').team, 'qarabag');
  assert.equal(at('#/komanda/premyer-liqa/qarabag/cedvel').tab, 'cedvel');
  assert.equal(at('#/komanda/turkiye/fenerbahce/cedvel?s=2025').season, '2025');
  assert.equal(at('#/komanda/turkiye').team, '');
  assert.equal(at('#/komanda/turkiye?s=2025').season, '2025');
  assert.equal(at('#/komanda').name, 'notfound');
  assert.equal(at('#/komanda/a/b/c/d').name, 'notfound');
});
test('team slug gives the same address as updater.py', () => {
  const { teamSlug } = app().api;
  for (const [name, slug] of [['Qarabağ', 'qarabag'], ['Araz-Naxçıvan', 'araz-naxcivan'], ['İmişli', 'imisli'], ['Əvəzedicilər', 'evezediciler'], ['Türkiyə', 'turkiye'], ['İngiltərə', 'ingiltere'], ['ÇL', 'cl'], ['I Liqa', 'i-liqa'], ['II Liqa', 'ii-liqa'], ['Bodo/Glimt', 'bodo-glimt'], ['Atlético Madrid', 'atletico-madrid'], ['Fenerbahçe', 'fenerbahce']]) assert.equal(teamSlug(name), slug);
});
test('world league with games: credits every source, marks a late result and opens the squad', async () => {
  const league = { id: 'almaniya', name: 'Bundesliqa', short: 'Almaniya', sport: 'football', source: 'OpenLigaDB (www.openligadb.de), ODbL 1.0 lisenziyası', ready: [{ key: '2026', label: '2026/27' }], teams: ['bayern-munich', 'sabah'], heyet: ['bayern-munich'] };
  const doc = { id: 'almaniya', name: 'Bundesliqa', short: 'Almaniya', sport: 'football', source: league.source, source_url: 'https://www.openligadb.de/', url: 'https://en.wikipedia.org/wiki/x', key: '2026', season: '2026/27',
    teams: { 'bayern-munich': { name: 'Bayern Munich', short: 'Bayern', logo: '' }, sabah: { name: 'Sabah', logo: '' } },
    groups: [{ name: '', rows: [{ pos: 1, team: 'bayern-munich', p: 1, w: 1, d: 0, l: 0, gf: 2, ga: 0, gd: 2, pts: 3, note: 'Çempionlar Liqası', color: '#BBF3BB' }] }],
    games: [{ home: 'bayern-munich', away: 'sabah', date: '2020-02-02T18:30:00+00:00', played: false, round: '1' }] };
  const ctx = teamPage({ 'data/futbol/index.json': { leagues: [league], checked: {} }, 'data/futbol/almaniya.json': doc,
    'data/futbol/heyet-almaniya.json': { teams: { 'bayern-munich': { wiki: 'FC Bayern Munich', players: [{ no: '1', pos: 'gk', name: 'Manuel Neuer' }] } } } });
  const table = await teamHtml(ctx, { liga: 'almaniya', team: 'bayern-munich', tab: 'cedvel' });
  assert.ok(table.includes('href="https://www.openligadb.de/"') && table.includes('ODbL 1.0'), 'lisenziyanın istədiyi mənbə qeydi');
  assert.ok(table.includes('href="https://en.wikipedia.org/wiki/x"'), 'cədvəlin mənbəyi də qalır');
  assert.ok(!table.includes('<img') && table.includes('>B</span>'), 'loqo yoxdursa adın ilk hərfi');
  const squad = await teamHtml(ctx, { liga: 'almaniya', team: 'bayern-munich', tab: 'heyet' });
  assert.ok(squad.includes('Manuel Neuer'));
  assert.ok(squad.includes('https://en.wikipedia.org/wiki/FC_Bayern_Munich') && squad.includes('CC BY-SA 4.0'), 'heyətin mənbəyi və lisenziyası');
  const games = await teamHtml(ctx, { liga: 'almaniya', team: 'bayern-munich', tab: 'oyunlar' });
  assert.ok(games.includes('Nəticə gözlənilir'), 'vaxtı keçib nəticəsi gəlməyən oyun');
  assert.ok(!(await teamHtml(ctx, { liga: 'almaniya', team: 'sabah', tab: 'heyet' })).includes('Manuel Neuer'), 'heyəti olmayan klubda Heyət tabı açılmır');
  const both = teamPage({ 'data/futbol/index.json': { leagues: [{ ...TEAM_INDEX.leagues[0], ready: [TEAM_INDEX.leagues[0].ready[0]], teams: ['sabah'] }, league], checked: {} }, 'data/futbol/premyer-liqa.json': PREMYER, 'data/futbol/almaniya.json': doc });
  const sabah = await teamHtml(both, { liga: 'premyer-liqa', team: 'sabah' });
  assert.ok(sabah.includes('pfl.az') && sabah.includes('ODbL 1.0'), 'iki yarışın oyunu varsa iki mənbə göstərilir');
});
test('speed red line: the home page loads no team page code or data', () => {
  const src = fs.readFileSync(path.join(root, 'assets/app.js'), 'utf8');
  assert.ok(!src.includes('data/futbol'), 'məlumat yalnız komanda.js-dən istənir');
  assert.equal(src.split('import("./komanda.js")').length - 1, 1, 'modul bir yerdən (teamModule) yüklənir');
  assert.equal(src.split('komanda.js').length - 1, 2, 'import + idman bölməsində modulepreload (preTeam)');
  const body = src.slice(src.indexOf('function teamView'), src.indexOf('function trafficView'));
  assert.ok(body.includes('teamModule(r)') && body.includes('komanda.css'), 'kod və üslub bu funksiyadan gəlir');
  assert.ok(src.includes('if (r.name === "section" && r.slug === "idman") preTeam();'), 'idman bölməsi açılanda modul, üslub və index əvvəlcədən yüklənir');
  const km = fs.readFileSync(path.join(root, 'assets/komanda.js'), 'utf8');
  assert.ok(km.includes('export function prefetch(d, r)') && km.includes('fileOf(d.S, `${DIR}index.json`);') && km.includes('fileOf(d.S, `${DIR}${r.liga}.json`)'), 'komanda.js index və liqanın faylını birlikdə istəyir');
  assert.equal(src.split('teamView(').length - 1, 2, 'tərif və renderView-da komanda ünvanı');
  assert.ok(src.includes('r.name === "team" ? teamView(r)'));
  const index = fs.readFileSync(path.join(root, 'index.html'), 'utf8'), sw = fs.readFileSync(path.join(root, 'sw.js'), 'utf8');
  // index.html-də hazır ilk ekranın xəbər mətni «komanda» sözünü daşıya bilər; yoxlanan kod və məlumat keçidləridir.
  // 2026-11-06: erkən skript yalnız liqa/komanda keçidində (#/komanda/...) liqa fayllarını və modulu istəyir; ana səhifə yalnız first.json.
  const early = index.match(/<script>([\s\S]*?)<\/script>/)[1], rest = index.replace(early, '');
  assert.ok(!/komanda\.(?:js|css)|data\/futbol|#\/komanda\//.test(rest) && !sw.includes('komanda'), 'ilk açılışda və service worker quraşdırılanda da yüklənmir');
  assert.ok(early.includes('var team = !home && location.hash.match(/^#\\/komanda\\/([a-z0-9-]+)/);') && early.includes('var files = home ? ["data/first.json"] :'), 'skriptdə yalnız liqa/komanda keçidində');
  assert.ok(fs.statSync(path.join(root, 'assets/komanda.js')).size < 30e3, 'komanda.js');
  assert.ok(fs.statSync(path.join(root, 'assets/komanda.css')).size < 12e3, 'komanda.css');
});
test('team page helpers: form, next games, standing line and zones', () => {
  const ctx = teamPage(teamFiles());
  const run = code => vm.runInContext(code, ctx);
  ctx.doc = PREMYER;
  assert.deepEqual(Array.from(run('formOf(gamesOf(doc, "qarabag"), "qarabag")')), ['w', 'l']);
  assert.equal(run('standingLine(doc, "qarabag", ordTur)'), 'Misli Premyer Liqası, 2-ci yer');
  assert.equal(run('standingLine(doc, "yoxdur", ordTur)'), 'Misli Premyer Liqası');
  const split = run('splitGames(gamesOf(doc, "qarabag"))');
  assert.equal(split.played.length, 2);
  assert.equal(split.next.length, 1, 'təxirə salınmış oyun növbəti sayılmır');
  // Saatı bilinməyən oyun (day: true) 12:00 UTC ilə yazılır: o an başlanğıc deyil, oyun günü 16:00-da (Bakı) siyahıdan çıxmamalıdır
  ctx.dayGames = [{ home: 'a', away: 'b', date: '2026-12-05T12:00:00+00:00', day: true }, { home: 'a', away: 'c', date: '2026-12-05T12:00:00+00:00' }];
  const nextAt = iso => Array.from(run(`splitGames(dayGames, Date.parse("${iso}")).next`)).map(g => g.away);
  assert.deepEqual(nextAt('2026-12-05T11:59:00Z'), ['b', 'c']);
  assert.deepEqual(nextAt('2026-12-05T12:01:00Z'), ['b'], 'saatı məlum oyun başlayıb, saatsız oyun hələ qarşıdadır');
  assert.deepEqual(nextAt('2026-12-06T12:01:00Z'), [], 'ertəsi gün o da keçmiş sayılır');
  ctx.rows = TURKIYE.groups[0].rows;
  assert.deepEqual(JSON.parse(run('JSON.stringify(zonesOf(rows))')), [{ note: 'Çempionlar Liqası', color: '#81D6AC' }, { note: 'Aşağı liqaya düşmə', color: 'red;background:url(x)' }]);
  ctx.index = TEAM_INDEX;
  assert.deepEqual(Array.from(run('otherLeagues(index, index.leagues[0], "qarabag").map(l => l.id)')), ['kubok'], 'əvəzedicilər qarışmır');
  assert.equal(run('otherLeagues(index, index.leagues[2], "qarabag").length'), 0);
  const rx = run('nameRx(["Sumqayıt", "Nice"])');
  assert.ok(rx.test('Sumqayıtın qələbəsi'));
  assert.ok(rx.test('Nice qalib gəldi'));
  assert.ok(!rx.test('a nice goal'), 'kiçik hərflə başqa sözdür');
  assert.ok(!rx.test('Sumqayıtlı gənc'));
});
test('team page: title line, tabs and a highlighted table row, no squad tab without data', async () => {
  const ctx = teamPage(teamFiles());
  const html = await teamHtml(ctx, { liga: 'premyer-liqa', team: 'qarabag', tab: 'cedvel' });
  assert.ok(html.includes('<h1>Qarabağ</h1>'));
  assert.ok(html.includes('>Misli Premyer Liqası</a>, 2-ci yer</p>'));
  assert.deepEqual(html.match(/(?<=<nav class="tm-tabs".*?)>(Baxış|Oyunlar|Cədvəl|Heyət|Xəbərlər)</g).map(x => x.slice(1, -1)), ['Baxış', 'Oyunlar', 'Cədvəl', 'Xəbərlər'], 'pfl.az heyət vermir: tab yoxdur');
  assert.match(html, /<tr class="me" aria-current="true"><td class="pos">2<\/td><td class="club"><a href="#\/komanda\/premyer-liqa\/qarabag">/);
  assert.ok(html.includes('href="#/komanda/premyer-liqa/sabah"'), 'hər klub öz səhifəsinə aparır');
  assert.ok(html.includes('data-tm-go'), 'mövsüm seçicisi');
  assert.ok(html.includes('?s=2025'));
  assert.ok(html.includes('Mənbə: pfl.az'));
  assert.ok(!html.includes('tm-legend'), 'zona məlumatı olmayan liqada izah yoxdur');
  const squad = await teamHtml(ctx, { liga: 'premyer-liqa', team: 'qarabag', tab: 'heyet' });
  assert.ok(squad.includes('<a href="#/komanda/premyer-liqa/qarabag" class="on"'), 'yoxdursa Baxışa düşür');
});
test('team page: the table fits a phone without sideways scrolling', async () => {
  const css = fs.readFileSync(path.join(root, 'assets/komanda.css'), 'utf8');
  const phone = css.slice(css.indexOf('@media(max-width:699px)'));
  assert.ok(phone.includes('min-width:0') && phone.includes('table-layout:fixed'), 'sabit 600 px eni telefonda yoxdur');
  assert.ok(phone.includes('.tm-table .goals{display:none}') && phone.includes('.tm-table .form{display:none}'));
  const ctx = teamPage(teamFiles());
  const html = await teamHtml(ctx, { liga: 'premyer-liqa', team: 'qarabag', tab: 'cedvel' });
  assert.ok(html.includes('<th class="goals">Qol</th>') && html.includes('<td class="goals">2:1</td>'), 'kompüterdə Qol qalır');
});
test('team page: zone bars and squad for a league that has them', async () => {
  const ctx = teamPage(teamFiles());
  const table = await teamHtml(ctx, { liga: 'turkiye', team: 'fenerbahce', tab: 'cedvel' });
  assert.ok(table.includes('box-shadow:inset 3px 0 0 #81D6AC'));
  assert.ok(!table.includes('url(x)'), 'rəng yoxlanılır: üslub içinə başqa şey düşmür');
  assert.ok(table.includes('Çempionlar Liqası'));
  const squad = await teamHtml(ctx, { liga: 'turkiye', team: 'fenerbahce', tab: 'heyet' });
  assert.ok(squad.includes('>Heyət<'));
  assert.ok(squad.includes('Qapıçılar') && squad.includes('Mert Günok') && squad.includes('37 yaş'));
  assert.ok(ctx.asked.includes('data/futbol/heyet-turkiye.json'));
  const other = await teamHtml(ctx, { liga: 'turkiye', team: 'besiktas', tab: '' });
  assert.ok(!other.includes('>Heyət<'), 'siyahısı olmayan komandada tab yoxdur');
});
test('team page: games from all competitions, cards with date and a full list sheet', async () => {
  const ctx = teamPage(teamFiles());
  const html = await teamHtml(ctx, { liga: 'premyer-liqa', team: 'qarabag' });
  assert.ok(ctx.asked.includes('data/futbol/kubok.json'), 'digər yarış da gəlir');
  assert.ok(!ctx.asked.includes('data/futbol/evezediciler.json'), 'əvəzedicilər gəlmir');
  assert.ok(!ctx.asked.includes('data/futbol/heyet-turkiye.json') && !ctx.asked.includes('data/futbol/turkiye.json'), 'lazım olmayan fayl istənmir');
  assert.ok(html.includes('data-tm-sheet'));
  assert.ok(html.includes('<time datetime="2099-11-06T18:00+04:00">'), 'tarix və vaxt');
  assert.ok(html.includes('3-cü tur') && html.includes('Azərbaycan Kuboku'));
  const sheet = vm.runInContext('S.teamSheet', ctx);
  assert.equal(sheet.title, 'Qarabağ: bütün oyunlar');
  assert.equal(sheet.html.split('class="tm-game"').length - 1, 5, 'tam siyahı, kubok da daxil');
  assert.ok(sheet.html.includes('Təxirə salınıb'));
  const list = await teamHtml(ctx, { liga: 'premyer-liqa', team: 'qarabag', tab: 'oyunlar' });
  assert.ok(list.includes('Avqust 2026'), 'aylara bölünür');
});
test('team page: the games tab shows only the chosen competition', async () => {
  const ctx = teamPage(teamFiles());
  const league = await teamHtml(ctx, { liga: 'premyer-liqa', team: 'qarabag', tab: 'oyunlar' });
  assert.equal(league.split('class="tm-game"').length - 1, 4, 'yalnız Premyer Liqa');
  assert.ok(!league.includes('tm-comp">Azərbaycan Kuboku'), 'kubok oyunu qarışmır');
  assert.ok(league.includes('data-tm-go') && league.includes('Azərbaycan Kuboku'), 'kubok seçimdə qalır');
  assert.ok(!ctx.asked.includes('data/futbol/kubok.json'), 'seçilməyən yarışın faylı gəlmir');
  const cup = await teamHtml(ctx, { liga: 'kubok', team: 'qarabag', tab: 'oyunlar' });
  assert.ok(cup.includes('tm-comp">Azərbaycan Kuboku') && !cup.includes('tm-comp">Misli Premyer Liqası'), 'kubok seçiləndə yalnız kubok');
  const files = teamFiles();
  files['data/futbol/premyer-liqa.json'] = { ...PREMYER, games: [] };
  const empty = teamPage(files);
  const none = await teamHtml(empty, { liga: 'premyer-liqa', team: 'qarabag', tab: 'oyunlar' });
  assert.ok(none.includes('Misli Premyer Liqası oyunları hələ əlavə olunmayıb.'), 'oyunu olmayan yarışda başqa yarışın oyunu görünmür');
  assert.ok(!none.includes('class="tm-game"'));
  const look = await teamHtml(empty, { liga: 'premyer-liqa', team: 'qarabag' });
  assert.ok(look.includes('tm-comp">Azərbaycan Kuboku'), 'baxışda bütün yarışlar qalır');
});
test('team page: news reuse club topics and stay away from other meanings and sports', async () => {
  const row = (id, title, extra = {}) => ({ id, title, category: 'idman', lang: 'az', source: 'APA', sourceUrl: `https://apa.az/${id}`, publishedAt: '2026-11-01T06:00:00Z', ...extra });
  const ctx = teamPage(teamFiles(), [
    row('a', 'Qarabağın yeni transferi'), row('b', '"Sabah" FK qalib gəldi'), row('c', 'Sabah hava yağışlı olacaq', { category: 'heyat' }), row('d', 'Sabah oyun var'),
    row('e', 'Qarabağ basketbol komandası qalib gəldi'), row('f', 'Qarabağ dirçəliş proqramı', { category: 'gundem' }), row('g', 'Sumqayıt güləş yarışı'), row('h', 'Sumqayıtın futbolçusu'),
  ]);
  const ids = team => Array.from(vm.runInContext(`team.newsOf({ name: ${JSON.stringify(team)} }).map(a => a.id)`, ctx));
  assert.deepEqual(ids('Qarabağ'), ['a']);
  assert.deepEqual(ids('Sabah'), ['b'], '«sabah» sözü komanda deyil');
  assert.deepEqual(ids('Sumqayıt'), ['h'], 'mövzusuz komanda adla axtarılır, başqa idman düşmür');
  assert.equal(vm.runInContext('team.topicFor("Internazionale")', ctx), 'İnter');
  assert.equal(vm.runInContext('team.topicFor("Manchester City")', ctx), 'Man City');
  assert.equal(vm.runInContext('team.topicFor("Real Betis")', ctx), null);
  const html = await teamHtml(ctx, { liga: 'premyer-liqa', team: 'qarabag', tab: 'xeberler' });
  assert.ok(html.includes('https://apa.az/a') && !html.includes('https://apa.az/e'));
});
test('team page: a national cup from Wikipedia opens the games tab and the competition picker', async () => {
  const files = teamFiles();
  files['data/futbol/index.json'] = { ...TEAM_INDEX, leagues: [...TEAM_INDEX.leagues.map(l => l.id === 'turkiye' ? { ...l, source: 'Vikipediya' } : l), { id: 'turkiye-kuboku', name: 'Türkiyə Kuboku', short: 'Türkiyə Kuboku', source: 'Vikipediya (kubok)', cup: true, sport: 'football', ready: [{ key: '2026', label: '2026/27' }], teams: ['fenerbahce'] }] };
  files['data/futbol/turkiye.json'] = { ...TURKIYE, source: 'Vikipediya', games: [] };
  files['data/futbol/turkiye-kuboku.json'] = { id: 'turkiye-kuboku', name: 'Türkiyə Kuboku', short: 'Türkiyə Kuboku', source: 'Vikipediya (kubok)', key: '2026', season: '2026/27', groups: [], teams: { fenerbahce: { name: 'Fenerbahçe', logo: '' }, bursaspor: { name: 'Bursaspor', logo: '' } },
    games: [{ home: 'bursaspor', away: 'fenerbahce', hs: 0, as: 2, played: true, date: '2026-10-27T18:00:00+03:00', round: '4-cü mərhələ' }] };
  const ctx = teamPage(files);
  const look = await teamHtml(ctx, { liga: 'turkiye', team: 'fenerbahce' });
  assert.ok(look.includes('/oyunlar'), 'liqada oyun olmasa da Oyunlar tabı açılır');
  assert.ok(look.includes('Türkiyə Kuboku · 4-cü mərhələ'));
  const tab = await teamHtml(ctx, { liga: 'turkiye', team: 'fenerbahce', tab: 'oyunlar' });
  assert.ok(tab.includes('<option value="#/komanda/turkiye-kuboku/fenerbahce/oyunlar"'), 'kubok Yarış seçimindədir');
});
test('team page: missing data never breaks the page', async () => {
  const noIndex = teamPage({});
  assert.ok((await teamHtml(noIndex, { liga: 'premyer-liqa', team: 'qarabag' })).includes('Komanda məlumatı açılmadı'));
  const ctx = teamPage(teamFiles());
  assert.ok((await teamHtml(ctx, { liga: 'yoxdur', team: 'x' })).includes('Bu liqanın səhifəsi yoxdur'), 'məlumatı alınmayan liqa');
  const gone = await teamHtml(ctx, { liga: 'premyer-liqa', team: 'xyz' });
  assert.ok(gone.includes('bu mövsüm komanda bu yarışda deyil') && gone.includes('tm-table'), 'liqanın cədvəli göstərilir');
  const league = await teamHtml(ctx, { liga: 'premyer-liqa', team: '' });
  assert.ok(league.includes('<h1>Misli Premyer Liqası</h1>') && !league.includes('class="me"'));
  const cup = await teamHtml(ctx, { liga: 'kubok', team: 'qarabag', tab: 'cedvel' });
  assert.ok(!cup.includes('>Cədvəl<'), 'kubokda cədvəl tabı yoxdur');
  assert.ok(cup.includes('Azərbaycan Kuboku'));
});
test('team page: the league name above the club opens the league with all its clubs', async () => {
  const ctx = teamPage(teamFiles());
  const html = await teamHtml(ctx, { liga: 'turkiye', team: 'fenerbahce' });
  assert.match(html, /<p><a class="tm-league" href="#\/komanda\/turkiye">Türkiyə Süper Liqası<\/a>, 1-ci yer<\/p><h1>Fenerbahçe<\/h1>/);
  const past = await teamHtml(ctx, { liga: 'premyer-liqa', team: 'qarabag', season: '2025' });
  assert.ok(past.includes('Komanda məlumatı açılmadı'), 'keçmiş mövsüm faylı olmayanda səhifə sınmır');
  const league = await teamHtml(ctx, { liga: 'turkiye', team: '' });
  assert.ok(league.includes('href="#/komanda/turkiye/fenerbahce"') && league.includes('href="#/komanda/turkiye/besiktas"'), 'hər klub açılır');
  const cup = await teamHtml(ctx, { liga: 'kubok', team: '' });
  assert.ok(cup.includes('class="tm-clubs"') && cup.includes('href="#/komanda/kubok/sumqayit"'), 'cədvəli olmayan yarışda klub siyahısı');
  assert.ok(!cup.includes('tm-table'));
});
test('football tables link only to the team pages that exist: Azerbaijani leagues', () => {
  const { S, footballBlock } = app().api;
  S.football = { leagues: [{ league: 'Misli Premyer Liqası', short: 'Premyer Liqa', table: [{ pos: 1, team: 'Qarabağ', p: 1, w: 1, d: 0, l: 0, gf: 1, ga: 0, gd: 1, pts: 3 }], results: [], fixtures: [] }] };
  S.fbLeague = 0; S.fbTab = 'table';
  const az = footballBlock([]);
  assert.equal(az.split('href="#/komanda/premyer-liqa/qarabag"').length - 1, 2, 'kart və cədvəl');
  assert.ok(az.includes('<a href="#/komanda/premyer-liqa/qarabag" class="fb-team"'));
  S.football = null; S.fbTab = null;
  S.sports = { leagues: [{ id: 'tur.1', sport: 'football', short: 'Türkiyə', name: 'Süper Liq', groups: [{ name: 'x', rows: [{ pos: 1, team: 'Fenerbahce', full: 'Fenerbahce', p: 1, w: 1, d: 0, l: 0, gf: 1, ga: 0, gd: 1, pts: 3 }] }] }] };
  const world = footballBlock([]);
  assert.ok(world.includes('<a href="#/komanda/turkiye/fenerbahce" class="fb-team"'), 'dünya klubunun kartı öz səhifəsinə aparır');
});
test('sports menu stays put: place is from its widest form', () => {
  const { popLeft } = app().api;
  assert.equal(popLeft(300, 1280, 800), 300);
  assert.equal(popLeft(600, 1280, 800), 472, 'üçüncü sütun açılanda da sığır, açılanda yeri dəyişmir');
  assert.equal(popLeft(420, 593, 460), 125);
  assert.equal(popLeft(20, 300, 460), 8, 'ekrandan sola çıxmır');
});
test('transfer news: own tab first, football and basketball inside, empty basketball hidden', () => {
  const { S, navPopHtml, subNav, clubMatches } = app().api;
  const art = (title, source = 'APA', extra = {}) => ({ id: title, title, source, category: 'idman', lang: 'az', publishedAt: new Date().toISOString(), ...extra });
  const foot = art('Qarabağın yeni transfer hədəfi'), bb = art('Avroliqa klubu transfer etdi'), site = art('Player transfer news', 'Sportando'), ru = art('Трансфер Зенита'), volley = art('Voleybol klubunun transferi'), money = art('Pul transferi ilə bağlı xəbər'), plain = art('Neftçi qalib gəldi'), turk = art('Galatasaray kiralık oyuncu aldı');
  const all = 'Transfer xəbərləri', f = 'Futbol transferləri', b = 'Basketbol transferləri';
  for (const a of [foot, ru, turk]) { assert.ok(clubMatches(a, all), a.title); assert.ok(clubMatches(a, f), a.title); assert.ok(!clubMatches(a, b), a.title); }
  for (const a of [bb, site]) { assert.ok(clubMatches(a, all), a.title); assert.ok(clubMatches(a, b), a.title); assert.ok(!clubMatches(a, f), a.title); }
  for (const a of [volley, money, plain]) assert.ok(!clubMatches(a, all), a.title);
  S.club = null; S.data = { articles: [foot] };
  const first = navPopHtml('idman', null);
  assert.ok(first.indexOf('data-club="Transfer xəbərləri"') < first.indexOf('data-club="Futbol"'), 'Hamısıdan sonra birinci');
  let pop = navPopHtml('idman', all);
  assert.ok(pop.includes('data-club="Futbol transferləri"') && pop.includes('>Futbol</button>'));
  assert.ok(!pop.includes('data-club="Basketbol transferləri"'), 'xəbəri yoxdursa düymə yoxdur');
  S.data = { articles: [foot, bb] };
  pop = navPopHtml('idman', all);
  assert.ok(pop.includes('data-club="Basketbol transferləri"') && pop.includes('>Basketbol</button>'));
  S.sportTab = all;
  assert.ok(subNav('idman').includes('data-club="Basketbol transferləri"'), 'telefonda eyni');
});
test('sports menu: leagues instead of clubs, clubs open from the league', () => {
  const { S, navPopHtml, subNav } = app().api;
  S.data = { articles: [] }; S.club = null;
  const rows = names => [{ rows: names.map(([team, full]) => ({ team, full })) }];
  S.football = { leagues: [{ short: 'Premyer Liqa', table: [{ team: 'Qarabağ' }, { team: 'Sabah' }] }] };
  S.sports = null; S.sportsAsked = true;
  assert.ok(navPopHtml('idman', 'Futbol').includes('data-club="Galatasaray"'), 'məlumat çatana qədər klubların düymələri qalır');
  assert.ok(navPopHtml('idman', 'Basketbol').includes('data-club="NBA"'));
  S.sports = { leagues: [
    { id: 'eng.1', sport: 'football', short: 'İngiltərə', name: 'Premyer Liqa (İngiltərə)', groups: rows([['Man City', 'Manchester City']]) },
    { id: 'tur.1', sport: 'football', short: 'Türkiyə', name: 'Süper Liq', groups: rows([['Galatasaray'], ['Fenerbahce']]) },
    { id: 'uefa.champions', sport: 'football', short: 'ÇL', name: 'Çempionlar Liqası', groups: rows([['PSG', 'Paris Saint-Germain']]) },
    { id: 'nba', sport: 'basketball', short: 'NBA', name: 'NBA', groups: rows([['Lakers', 'Los Angeles Lakers']]) },
  ] };
  for (const html of [navPopHtml('idman', 'Futbol'), (S.sportTab = 'Futbol', subNav('idman'))]) {
    for (const liga of ['premyer-liqa', 'i-liqa', 'ii-liqa', 'kubok', 'evezediciler', 'ingiltere', 'turkiye', 'cl']) assert.ok(html.includes('href="#/komanda/' + liga + '"'), liga);
    assert.ok(html.includes('<span>Süper Liq</span><small>Türkiyə</small>'), 'liqanın adı, yanında ölkəsi');
    assert.ok(html.includes('<span>Premyer Liqa</span><small>İngiltərə</small>'));
    assert.ok(html.includes('<span>Çempionlar Liqası</span></a>'));
    for (const club of ['Neftçi', 'Galatasaray', 'Real Madrid']) assert.ok(!html.includes('data-club="' + club + '"'), club);
    assert.ok(!html.includes('Milli komandalar') && !html.includes('data-club="Milli komanda"'), 'yarışların siyahısı gəlməyibsə başlıq da yoxdur');
  }
  S.milli = [{ id: 'dc-2026', name: 'Dünya Çempionatı 2026', teams: ['Braziliya', 'ABŞ'] }];
  const withNat = navPopHtml('idman', 'Futbol');
  assert.ok(withNat.includes('Milli komandalar</span>') && withNat.includes('href="#/komanda/dc-2026" data-liga="dc-2026"><span>Dünya Çempionatı 2026</span></a>'), 'sahib 2026-11-07: Milli komandalar liqaların yanında, yarışlarla');
  const pop = navPopHtml('idman', 'Futbol', 'Türkiyə');
  assert.ok(pop.includes('class="pop-col clubs"') && pop.includes('href="#/komanda/turkiye/galatasaray"') && pop.includes('href="#/komanda/turkiye/fenerbahce"'));
  assert.ok(navPopHtml('idman', 'Futbol').includes('href="#/komanda/premyer-liqa/qarabag"'), 'açılanda birinci liqanın klubları');
  assert.ok(!subNav('idman').includes('pop-col clubs'), 'telefonda klublar liqanın səhifəsindədir');
  const bb = navPopHtml('idman', 'Basketbol', 'NBA');
  assert.ok(bb.includes('href="#/komanda/nba/los-angeles-lakers"') && !bb.includes('data-club="NBA"'));
  assert.ok(!navPopHtml('idman', 'Basketbol').includes('turkiye'), 'basketbolda futbol liqası yoxdur');
  assert.ok(!navPopHtml('bolgeler', 'Bakı').includes('#/komanda/'));
});

// Sürət (qırmızı xətt 3): pipeline baş səhifənin ilk ekranını index.html-ə hazır yazır (.github/scripts/prerender.cjs),
// brauzer onu CSS ilə birgə çəkir, app.js gələndə eyni görünüşü təzə məlumatla əvəz edir.
function firstFixture(now) {
  const stamp = new Date(now - 5 * 60e3).toISOString();
  // 1-ci başlıqda HTML işarəsi: brauzerdə decode() textarea ilə açır, prerender-də cədvəl (açılmasa «&amp;amp;» çıxır)
  const art = i => ({ id: 'a0a0a0a0a0a0a0a' + i.toString(16), title: i === 1 ? 'Neft &amp; qaz barədə yeni1 açıqlama1' : `Mövzu${i} barədə yeni${i} açıqlama${i}`, summary: '', source: 'APA', sourceUrl: 'https://apa.az/' + i, publishedAt: stamp, category: i % 3 ? 'sosial' : 'iqtisadiyyat', lang: 'az', imageUrl: 'https://apa.az/' + i + '.jpg' });
  return { updatedAt: stamp, count: 16, og: {}, articles: [...Array(16)].map((_, i) => art(i)) };
}
test('speed red line: the first screen is prerendered from first.json with app.js itself, for phone widths, first picture eager', () => {
  const { homeHtml, firstScreen, validate, KEEP } = require(path.join(root, '.github/scripts/prerender.cjs'));
  const now = Date.parse('2026-11-03T12:00:00Z');
  const full = homeHtml(root, firstFixture(now), { now, width: 390 });
  assert.ok(full.includes('Neft &amp; qaz') && !full.includes('&amp;amp;'), 'başlıqdakı HTML işarəsi brauzerdəki kimi açılır');
  assert.equal((full.match(/class="hero-main"/g) || []).length, 15, 'tam slayder 15 slayd');
  const html = firstScreen(full);
  validate(html);
  assert.equal((html.match(/class="hero-main"/g) || []).length, KEEP.slides, 'görünən hissə: slaydlar');
  assert.ok((html.match(/class="pcard/g) || []).length <= KEEP.prez && (html.match(/<article class="card/g) || []).length <= KEEP.latest, 'görünən hissə: Zuğulba və son xəbər kartları');
  assert.deepEqual(KEEP, { slides: 2, prez: 4, latest: 2, alts: 2 }, 'telefon ekranına sığan qədər (sürət, 2026-11-05)');
  for (const m of html.matchAll(/data-image-alternatives="\[([^"]*)\]"/g)) assert.ok(m[1].split('&quot;,&quot;').length <= 2, 'hazır nüsxədə ehtiyat şəkil siyahısı 2-yə qədər');
  // Kəsilmiş siyahı da JSON qalmalıdır (imgFail JSON.parse edir): əvvəl 3+ ünvanlı siyahının son dırnağı itirdi
  const cut = firstScreen('<img data-image-alternatives="[&quot;https://a/1.jpg&quot;,&quot;https://b/2.jpg&quot;,&quot;https://c/3.jpg&quot;]"><img data-image-alternatives="[&quot;https://a/1.jpg&quot;]"><img data-image-alternatives="[]">');
  const lists = [...cut.matchAll(/data-image-alternatives="([^"]*)"/g)].map(m => JSON.parse(m[1].replace(/&quot;/g, '"')));
  assert.deepEqual(lists, [['https://a/1.jpg', 'https://b/2.jpg'], ['https://a/1.jpg'], []], 'kəsilmiş ehtiyat siyahısı düzgün JSON-dur');
  assert.ok(fs.readFileSync(path.join(root, 'assets/app.js'), 'utf8').includes('alt="" loading="lazy" fetchpriority="low" decoding="async"'), 'Zuğulba kiçik şəkilləri aşağı prioritetlə: slayder şəkli birinci keçir (fikstürdə şəkil yoxdur, mənbə yoxlanır)');
  assert.ok(html.includes('Neft &amp; qaz'), 'ilk slayd qalır');
  assert.ok(html.includes('<section class="hero">') && html.includes('Son xəbərlər') && html.includes('Zuğulba'), 'slayder, Son xəbərlər, Zuğulba');
  assert.ok(/5 dəq(?:iqə)? əvvəl/.test(html), 'vaxt hazırlanma anına görədir (telefonda «dəq»)');
  assert.ok(/w=640&amp;we&amp;output=webp[^>]*fetchpriority="high"/.test(html), 'telefon ölçüsü (640), ilk şəkil yüksək prioritetlə');
  assert.ok(!html.includes('lazy-sec') && !html.includes('service-panel'), 'yalnız ilk ekran: bölmələr tam lentlə gəlir');
  assert.ok(!/<script\b/i.test(html), 'daxili skript yoxdur: CSP hash-ı dəyişməz qalır');
  // Eyni mənbə qaydası (qırmızı xətt 2): content-policy.js yüklənir, mənbə siyahısında olmayan sayt hazır nüsxəyə düşmür.
  const bad = firstFixture(now); bad.articles[0] = { ...bad.articles[0], source: 'Azadlıq', sourceUrl: 'https://azadliq.org/x' };
  assert.ok(!homeHtml(root, bad, { now, width: 390 }).includes('azadliq.org'));
});
test('speed red line: prerender rewrites only the #view block of index.html and is idempotent', () => {
  const { prerender } = require(path.join(root, '.github/scripts/prerender.cjs'));
  const os = require('node:os');
  const tmp = fs.mkdtempSync(path.join(os.tmpdir(), '8ulduz-pre-'));
  for (const d of ['assets', 'data', '.github/scripts']) fs.mkdirSync(path.join(tmp, d), { recursive: true });
  for (const f of ['index.html', 'assets/app.js', 'assets/content-policy.js']) fs.copyFileSync(path.join(root, f), path.join(tmp, f));
  const now = Date.parse('2026-11-03T12:00:00Z');
  fs.writeFileSync(path.join(tmp, 'data/first.json'), JSON.stringify(firstFixture(now)));
  const before = fs.readFileSync(path.join(tmp, 'index.html'), 'utf8');
  const viewRe = /(<div class="wrap" id="view" tabindex="-1">)([\s\S]*?)(<noscript>Saytı görmək üçün JavaScript-i aktiv edin\.<\/noscript><\/div><\/main>)/;
  const tbRe = /(<div class="wrap" id="topbar">)([^\n]*)(<\/div><\/div>\r?)$/m;
  const r1 = prerender(tmp, { now, width: 390 });
  const after = fs.readFileSync(path.join(tmp, 'index.html'), 'utf8');
  assert.equal(r1.changed, true);
  assert.ok(after.includes('<div class="pre-skel" data-prerender="' + firstFixture(now).updatedAt + '">'), 'hazır blokun vaxt möhürü');
  const tb = after.match(tbRe)[2]; // yuxarı zolaq hazır: açılışdakı quruluş (hava «—», dil düyməsi, rejim düyməsi), bir sətirdə, skriptsiz
  assert.ok(tb.includes('<b>—</b>') && tb.includes('class="ldd"') && tb.includes('data-act="theme"') && tb.includes('data-act="pray"') && !/<script/.test(tb), 'hazır yuxarı zolaq: ' + tb.slice(0, 200));
  assert.equal(before.replace(viewRe, '$1$3').replace(tbRe, '$1$3'), after.replace(viewRe, '$1$3').replace(tbRe, '$1$3'), '#view və #topbar-dan başqa heç nə dəyişməməlidir (CSP, qabıq, sətir sonları)');
  assert.equal((after.match(/<script>/g) || []).length, 1, 'daxili skript sayı dəyişməz');
  assert.equal(prerender(tmp, { now, width: 390 }).changed, false, 'ikinci dəfə eyni nəticə, fayl yazılmır');
  fs.rmSync(tmp, { recursive: true, force: true });
});
test('speed red line: the prerendered first screen stays until data arrives; the skeleton and the error do not wipe it', () => {
  let html = '<div class="pre-skel" data-prerender="x">hazır</div>';
  const view = { querySelector: s => s === '.pre-skel[data-prerender]' && html.includes('data-prerender') ? {} : null, set innerHTML(v) { html = v; }, get innerHTML() { return html; }, insertAdjacentHTML(_, h) { html = h + html; } };
  const ctx = app({ document: { documentElement: { dataset: {} }, title: '', addEventListener() {}, querySelector: s => s === '#view' ? view : s === '#cta' ? {} : null, querySelectorAll: () => [], createElement: () => ({}) } });
  vm.runInContext('syncQuery = () => {}; pageMeta = () => {}; countVisit = () => {}; highlightSearch = () => {};', ctx);
  ctx.api.renderView();
  assert.equal(html, '<div class="pre-skel" data-prerender="x">hazır</div>', 'skelet hazır ekranı silməməlidir');
  ctx.api.S.error = 'şəbəkə';
  ctx.api.renderView();
  assert.ok(html.startsWith('<div class="err"') && html.endsWith('hazır</div>'), 'xəta yuxarıda, hazır ekran qalır');
  ctx.api.S.error = null;
  ctx.location.hash = '#/bolme/sosial';
  ctx.api.renderView();
  assert.ok(html.includes('class="skel"') && !html.includes('hazır'), 'başqa səhifə hazır ekranı gözləmir, skelet çəkilir');
  const src = fs.readFileSync(path.join(root, 'assets/app.js'), 'utf8');
  assert.ok(src.includes('const pre = v.querySelector?.(":scope > .pre-skel");') && src.includes('pre.replaceWith(...kids)'), 'patchView sarğını açır, kartlar yerində qalır');
  const pipeline = fs.readFileSync(path.join(root, '.github/scripts/pipeline.sh'), 'utf8');
  assert.ok(pipeline.includes('prerender.cjs') && pipeline.includes('bolme index.html'), 'pipeline hər main yazılışında ilk ekranı hazırlayır və commit edir');
});

// Sahibin telefon qeydləri (2026-11-04): Zuğulbada paylaş, «yeni xəbər» düyməsi, boş qalmayan bölmə, slayder, açılan panellər,
// dörd valyuta, namaz/hava pəncərələri, konum, liqadan İdmana qayıdış.
test('Zuğulba card is a link with a share button outside the link; the latest list has an anchor', () => {
  const ctx = app(), { prezBlock, prezHome, latestBlock } = ctx.api;
  const at = new Date().toISOString();
  const prez = [{ id: 'p1', category: 'prezident', source: 'Prezident.az', sourceUrl: 'https://president.az/1', title: 'İlham Əliyev sərəncam imzalayıb', publishedAt: at, imageUrl: 'https://president.az/a.jpg', lang: 'az' }];
  const html = prezBlock(prezHome(prez));
  assert.ok(html.includes('<article class="pcard has-img" data-cat="prezident"><a class="pcard-hit" href="https://president.az/1"'), 'kart keçiddir');
  assert.ok(/<\/a><button type="button" class="share" data-act="dinle" data-id="p1">Dinlə<\/button><button type="button" class="share" data-act="share" data-share="https:\/\/8ulduz\.az\/#\/xeber\/p1[^"]*"[^>]*>Paylaş<\/button><\/article>/.test(html), 'Paylaş düyməsi keçidin kənarındadır');
  assert.ok(!html.match(/<a class="pcard-hit"[^>]*>([\s\S]*?)<\/a>/)[1].includes('<button'), 'keçidin içində düymə yoxdur');
  ctx.api.S.latestOrder = 'latest';
  assert.ok(latestBlock([]).startsWith('<section id="son-xeberler">'), '«N yeni xəbər» düyməsi bura sürüşdürür');
});
test('a home section never vanishes: shown stories stay in it, an empty category falls back to its archive', () => {
  const ctx = app(), { S, homeView } = ctx.api;
  const at = new Date().toISOString();
  const sos = Array.from({ length: 5 }, (_, i) => ({ id: 's' + i, title: 'Pensiya artımı barədə yeni qərar ' + i, category: 'sosial', lang: 'az', source: 'APA', sourceUrl: 'https://apa.az/s' + i, publishedAt: at }));
  S.lang = 'az'; S.og = {}; S.partial = false;
  S.data = { articles: sos }; // hamısı «Son xəbərlər»dədir
  // Uzaq bölmələrin HTML-i lazyHtml-dədir (lazySection): tam mətn üçün açarlı qutular məzmunla əvəz olunur
  const full = () => homeView().replace(/<div class="lazy-sec" data-lazy="([^"]+)"><\/div>/g, (_, k) => vm.runInContext('lazyHtml', ctx).get(k) || '');
  let html = full();
  assert.ok(html.includes('<h2>Sosial müdafiə</h2>') && html.includes('5 xəbər'), 'blok var, xəbərlər «Son xəbərlər»də olsa da');
  S.data = { articles: [{ id: 'g', title: 'Bakıda yeni park açılıb bu gün', category: 'gundem', lang: 'az', source: 'APA', sourceUrl: 'https://apa.az/g', publishedAt: at }] };
  S.archive = { sosial: { at: Date.now(), rows: sos } };
  html = full();
  assert.ok(html.includes('<h2>Sosial müdafiə</h2>'), 'lentdə yoxdursa arxivdən dolur');
  assert.ok(!html.includes('<h2>Video</h2>') || html.includes('ytrow'), 'video bölməsi arxiv istəmir');
  S.partial = true;
  assert.ok(!homeView().includes('lazy-sec'), 'ilk ekran dəyişmir');
});
test('phone fixes are in place: slider does not stop for good, panels close on outside click, four currencies fit, popups are not clipped', () => {
  const src = fs.readFileSync(path.join(root, 'assets/app.js'), 'utf8');
  assert.ok(!src.includes('_userStop') && src.includes('hoverUI && node.matches(":hover")') && src.includes('hero._holdUntil = Date.now() + 12000'), 'toxunuş slayderi 12 saniyə saxlayır, həmişəlik yox');
  assert.ok(src.includes('row.children[at + 2], row.children[0]') && src.includes('row._near?.(to)'), 'növbəti slaydların şəkli əvvəlcədən yüklənir');
  assert.ok(src.includes('details.service-panel[open], details.social-details[open]') && src.includes('S.svcOpen = false; if (!kept)'), 'açılan bölmələr kənara basanda və səhifə dəyişəndə bağlanır');
  assert.ok(src.includes('r.slug === S.clubSlug') && src.includes('r.name === "team" ? "idman"'), 'liqadan geri qayıdanda Futbol sırası qalır, nav İdmanı göstərir');
  assert.ok(src.includes('function jumpToLatest()') && src.includes('S.latestOrder = "latest"; S.latestCount = 8; } render(); jumpToLatest();'), '«yeni xəbər» düyməsi Son xəbərlər → Ən yeni');
  assert.ok(src.includes('navigator.permissions?.query?.({ name: "geolocation" })') && src.includes('data-act="geo"') && !src.includes('getCurrentPosition(applyGeo, undefined'), 'konum yalnız düymə ilə və ya əvvəl verilmiş icazə ilə');
  assert.ok(src.includes('yandexSrc(area)') && src.includes('wazeApp(area)') && src.includes('data-act="tix-yandex"'), 'telefonda Waze xəritəsi, ehtiyat Yandex, «Waze tətbiqində aç»');
  const css = fs.readFileSync(path.join(root, 'assets/app.css'), 'utf8');
  // Sahib, 2026-11-06: üç kart + › sınandı, əvvəlki dörd kartlı format qaytarıldı.
  assert.ok(css.includes('.mk:nth-child(-n+4){flex:0 0 calc((100% - 18px)/4)') && css.includes('.mk:nth-child(-n+4) .c span:last-child{display:none}'), 'dörd valyuta bir ekranda');
  // Sahib, 2026-11-06 (axşam): 3 rəng qaydası — kartlar bir rəngdə; telefonda faiz yerinə ox, qiymət yaşıl/qırmızı (2 rəqəm tam görünür)
  assert.ok(!css.includes('[data-fx=XAU]{--mk-a') && !css.includes('--mh:'), 'valyuta kartları ayrı-ayrı rənglənmir');
  assert.ok(css.includes('.mk .c{display:none}.mk .v::after{content:attr(data-ar)') && css.includes('.mk[data-d=up] .v{color:var(--up)}.mk[data-d=down] .v{color:var(--down)}'), 'telefonda ox və rəng');
  assert.ok(src.includes('data-d="${cls}"') && src.includes('data-ar="${has ? (i.changePct > 0 ? "↑"'), 'kart istiqaməti bilir');
  assert.ok(css.includes('--bg:#f6f4ee;--fg:#172b4d;--card:#fff;') && !css.includes('#229ED9'), 'açıq fon ağımtıl, Telegram sətri saytın göy rəngində');
  assert.ok(css.includes('.topbar{position:relative}') && css.includes('.topbar .wrap{position:static}'), 'namaz və hava pəncərələri zolağın içində kəsilmir');
  assert.ok(css.includes('.pcard .share{position:absolute'), 'Zuğulba paylaş düyməsi kartın küncündədir');
  assert.ok(!/\.pcard \[data-act=dinle\]\{[^}]*left:6px/.test(css) && css.includes('.pcard [data-act=dinle]{right:calc(10px + 4.2em)}'), 'Zuğulba kartında «Dinlə» enə uzanmır, «Paylaş»ın solundadır (sahib, 2026-11-08 telefon şəkli)');
  assert.ok(src.includes('</time><span class="acts">${shareBtn(a)}</span></div>') && css.includes('.acts{display:inline-flex;flex:none;margin-left:auto}') && css.includes('.hero-main .meta,.pcard .meta{flex-wrap:wrap}') && css.includes('.pcard.has-img:not(.noimg) .pcard-hit{align-self:stretch}'), 'dar yerdə «Dinlə» + «Paylaş» birlikdə növbəti sətrə keçir, mənbə adı sıxılmır; Zuğulba şəkli yuxarıda');
  const index = fs.readFileSync(path.join(root, 'index.html'), 'utf8');
  assert.ok(/frame-src [^"]*https:\/\/yandex\.com/.test(index), 'CSP Yandex xəritəsinə icazə verir');
});
test('location: nearest city within Azerbaijan, none abroad; traffic centres on it until the reader picks an area', () => {
  const ctx = app(), { S } = ctx.api;
  const nearestCity = vm.runInContext('nearestCity', ctx), tixArea = vm.runInContext('tixArea', ctx), savedPrayCity = vm.runInContext('savedPrayCity', ctx), geoCity = vm.runInContext('geoCity', ctx);
  assert.equal(nearestCity(40.59, 49.67)[0], 'Sumqayıt');
  assert.equal(nearestCity(40.68, 46.36)[0], 'Gəncə');
  assert.equal(nearestCity(41.01, 28.97), null, 'İstanbul: şəhər seçilmir');
  assert.equal(tixArea().id, 'merkez');
  S.geo = { lat: 40.59, lon: 49.67, city: 'Sumqayıt', at: Date.now() };
  assert.equal(tixArea().id, 'konum', 'konum tapılıbsa xəritə ona mərkəzlənir');
  S.tixArea = 'hava'; S.tixUser = true;
  assert.equal(tixArea().id, 'hava', 'oxucunun seçimi üstündür');
  assert.equal(savedPrayCity(), 'Sumqayıt', 'şəhər seçilməyibsə namaz konumun şəhərinə görədir');
  assert.equal(geoCity()[0], 'Sumqayıt');
  S.geo = { lat: 41.01, lon: 28.97, city: null, at: Date.now() };
  assert.equal(geoCity()[0], 'Bakı', 'xaricdə hava və namaz Bakıya görə qalır');
});

// 2026-11-04, sahibin 14 qeydi: başlıq sırası, dil seçimi, paylaşma ikonları, hərəkət düyməsi, Zuğulba süzgəci, nadir səhifələr ayrıca modulda.
test('owner notes: the logo row comes first with the install slot and a search button, the utility bar second; old language and filter rows are gone', () => {
  const app_ = shellParts().app;
  assert.ok(app_.indexOf('id="sitehead"') < app_.indexOf('id="topbar"'), 'loqo sətri yuxarı zolaqdan əvvəldir');
  assert.ok(app_.includes('<span class="inst" id="inst"></span>') && app_.includes('class="qbtn" data-act="find"'), 'quraşdırma yeri və lupa düyməsi başlıq sətrindədir');
  assert.ok(!app_.includes('langstick') && !app_.includes('id="langs"') && !app_.includes('class="filters"'), 'köhnə dil və süzgəc sətirləri yoxdur');
  const css = fs.readFileSync(path.join(root, 'assets/app.css'), 'utf8');
  assert.ok(css.includes('.inst .install-btn{background:var(--primary)'), '«Ana ekrana əlavə et» seçilən rəngdədir');
  // 2026-11-14 (sahibin ekran şəkli): kartın hündürlüyü yalnız 3 başlıq sətrini sayırdı; mənbə və vaxt iki sətirə düşəndə başlığın üstü
  // və vaxt kəsilirdi (standart şriftdə 150 px məzmun 114 px yerə). İndi 3 başlıq + 2 meta sətri; lent = 2 kart + 8 px ara.
  assert.ok(css.includes('.prez-lent>.pcard{box-sizing:border-box;height:calc(3*var(--lh-body) + 2*var(--lh-meta) + 24px);overflow:hidden}') && css.includes('.prez-lent{height:calc(6*var(--lh-body) + 4*var(--lh-meta) + 56px)!important}'), 'telefonda Zuğulba kartları bərabər, lent düz iki kart + ara (üçüncü kartın kəsiyi görünmür)');
  assert.ok(/@media\(max-width:600px\)\{[^@]*\.mk \.n\{font-size:12px\}/.test(css), 'telefonda məzənnə adı («100 Rubl») xanaya sığır');
  // 2026-11-14 (sahibin ekran şəkli, 412 px, işıqlı rejim): «Tünd» sözü sığmır, rejim və A−/A+ düymələri loqonun altına düşürdü.
  // Sonra (sahib, eyni gün): «A− A+ az kiçilt, əvvəlki kimi İşıqlı/Tünd yazıları olsun» — söz qayıdır, A−/A+ və dil düyməsi kiçilir,
  // işıqlı rejimin loqo lövhəsi dar ekranda bir az kiçik; 340–440 px-də hər iki rejimdə bir sətir (brauzerdə ölçülüb). Söz yalnız ≤335 px-də gizlidir.
  assert.ok(!css.includes('@media(max-width:411px){.topbar .theme-btn span+span{display:none}}') && !css.includes('@media(max-width:440px){:root[data-theme="light"] .topbar .theme-btn span+span{display:none}}'), 'telefonda rejim düyməsində «İşıqlı»/«Tünd» sözü var');
  assert.ok(css.includes('.topbar .prefs [data-act^="fs-"] .face{min-width:26px;padding:0 3px;font-size:.74rem}') && css.includes('@media(max-width:392px){.hrow>.logo{zoom:.78}') && css.includes('@media(max-width:335px){.topbar .theme-btn span+span{display:none}}'), 'A−/A+ kiçik, loqo dar ekranda kiçilir: düymələr loqo sətrindədir');
  assert.ok(!css.includes('.theme-btn .face>span:last-child{display:none}'), 'rejim düyməsinin «İşıqlı»/«Tünd» sözü gizlədilmir (yalnız ≤370 px-də böyük işarə)');
  assert.ok(css.includes('#son-xeberler{padding-bottom:16px;border-bottom:3px solid var(--primary)}'), '«Son xəbərlər» aydın xətlə ayrılır');
  assert.ok(!css.includes('.shr .sh{display:grid') && !css.includes('.sh{display:none'), 'telefonda da «Paylaş» düyməsi, yerində işarə yoxdur (sahib, 2026-11-05)');
});
test('owner notes: the utility bar carries the language dropdown with flag and code; a bad sync shows a retry button there', () => {
  const els = {};
  const el = id => els[id] ||= { id, _html: '', set innerHTML(v) { this._html = v; }, get innerHTML() { return this._html; }, classList: { toggle() {}, add() {}, remove() {} }, dataset: {}, style: {} };
  const ctx = app({ document: { documentElement: { dataset: {} }, activeElement: null, addEventListener() {}, querySelector(s) { const m = s.match(/^#([\w-]+)$/); return m ? el(m[1]) : null; }, querySelectorAll() { return []; }, createElement() { return {}; } } });
  const src = fs.readFileSync(path.join(root, 'assets/app.js'), 'utf8');
  vm.runInContext(src.slice(src.indexOf('\nfunction renderTopbar() {'), src.indexOf('\nconst NAV_PRIMARY')), ctx); // harness-in boş renderTopbar-ı əvəzinə əsli
  const { S } = ctx.api;
  S.lang = 'ru';
  vm.runInContext('renderTopbar()', ctx);
  let html = els.topbar.innerHTML;
  assert.ok(html.includes('class="ldd"') && html.includes('data-act="lang"') && html.includes('<b>RU</b>') && html.includes('class="flag"') && !html.includes('data-lang='), 'bağlı dil seçimi: bayraq + kod + ox');
  assert.ok(html.includes('class="wcity"') && /<span>İşıqlı<\/span>/.test(html), 'hava şəhəri ayrıca, rejim düyməsində söz');
  S.langOpen = true;
  vm.runInContext('renderTopbar()', ctx);
  html = els.topbar.innerHTML;
  assert.ok(html.includes('data-lang="ru" aria-pressed="true"') && html.includes('data-lang="" aria-pressed="false"'), 'açıq: dil düymələri');
  S.lang = null; S.langOpen = false; S.error = 'x';
  vm.runInContext('renderTopbar()', ctx);
  html = els.topbar.innerHTML;
  assert.ok(html.includes('<b>Hamısı</b>') && html.includes('class="retry" data-act="refresh"'), '«Hamısı» və xəta olanda «Yenilə»');
});
test('owner notes: share — every card carries the «Paylaş» button only (phone icons withdrawn 2026-11-05), the panel lists F, X, W, T, copy; every target is a web address', () => {
  const ctx = app(), { card, prezBlock, prezHome, S } = ctx.api, at = new Date().toISOString();
  S.og = {};
  const html = card({ id: '1', title: 'Xəbər', lang: 'az', category: 'gundem', source: 'APA', sourceUrl: 'https://apa.az/1', publishedAt: at });
  assert.ok(html.includes(`<button type="button" class="share" data-act="share" data-share="https://8ulduz.az/#/xeber/1?b=gundem&amp;h=${at.slice(2, 13).replace(/\D/g, '')}" title="Paylaş">Paylaş</button>`), '«Paylaş» düyməsi');
  assert.ok(!html.includes('class="sh"') && !html.includes('class="shr"') && !/SHR_ICONS|\.shr/.test(fs.readFileSync(path.join(root, 'assets/app.js'), 'utf8')), 'kartda yerində işarə yoxdur, kodda qalığı da (sahib, 2026-11-05)');
  const prez = prezBlock(prezHome([{ id: 'p1', category: 'prezident', source: 'Prezident.az', sourceUrl: 'https://president.az/1', title: 'İlham Əliyev sərəncam imzalayıb', publishedAt: at, lang: 'az' }]));
  assert.ok(prez.includes('class="share"') && prez.includes('data-prez-pause'), 'Zuğulba kartında da düymə; başlıqda dayandır düyməsi');
  const to = vm.runInContext('SHARE_TO', ctx);
  assert.deepEqual(Object.keys(to), ['fb', 'x', 'wa', 'tg', 'in', 'mail']);
  for (const [k, v] of Object.entries(to)) { const u = v[1]('https%3A%2F%2Fwww.8ulduz.az%2F0123456789abcdef', 'B'); assert.ok(/^(https:\/\/|mailto:)/.test(u) && u.includes('8ulduz.az'), k); }
  assert.ok(!card({ id: '1', title: 'Xəbər', lang: 'az', category: 'gundem', source: 'APA', sourceUrl: 'javascript:alert(1)', publishedAt: at }).includes('data-to='), 'təhlükəli keçid paylaşılmır');
});
test('owner notes: motion can be stopped and restarted; the system reduced-motion setting stops it by default and the button overrides it', () => {
  const off = (reduce, stored) => { const ctx = app({ matchMedia: q => ({ matches: reduce && /reduced-motion/.test(q) }) }); if (stored) ctx.api.storage.setItem('8ulduz-motion', stored); return vm.runInContext('motionOff()', ctx); };
  assert.equal(off(false, null), false);
  assert.equal(off(true, null), true, 'hərəkəti azalt → dayanıq');
  assert.equal(off(true, 'on'), false, 'düymə ilə açılıb');
  assert.equal(off(false, 'off'), true, 'düymə ilə dayandırılıb');
  const ctx = app();
  assert.ok(vm.runInContext('motionBtn()', ctx).includes('data-act="motion" aria-pressed="false"'));
  const src = fs.readFileSync(path.join(root, 'assets/app.js'), 'utf8');
  assert.ok(src.includes('if (motionOff() || !el.classList.contains("vmarquee")) return;') && src.includes('document.hidden || motionOff() ||') && src.replace(/\r\n/g, '\n').includes('if (motionOff()) return;\n  const half'), 'addım, slayder və lent eyni açarı dinləyir');
  assert.ok(src.includes('const KEYED = ".hero-row,.prez-lent"') && src.includes('restoreAnchor(box, anchor)'), 'yenilənmə sürüşən siyahıda oxunan kartı yerində saxlayır');
  assert.ok(src.includes("Date.now() - (S.touchAt || 0) < 8000"), 'oxucu toxunduqdan sonra 8 saniyə ekran dəyişmir');
});
test('owner notes: Zuğulba filter — another country\'s first lady is not ours, our leadership is', () => {
  const ctx = app(), f = vm.runInContext('aboutOurLeaders', ctx), at = new Date().toISOString();
  assert.equal(f({ title: 'ABŞ-nin birinci xanımı Oleşkidə atəşkəslə bağlı diplomatik görüş təşkil edəcək' }), false);
  assert.equal(f({ title: 'Özbəkistanın birinci xanımına kömək etdi' }), false);
  assert.equal(f({ title: 'Birinci xanım Mehriban Əliyeva Şuşada olub' }), true);
  assert.equal(f({ title: 'Azərbaycanın birinci xanımı sərgi ilə tanış olub' }), true);
  assert.equal(f({ title: 'Birinci xanım Bakıda sərgi ilə tanış olub' }), true);
  const foreign = [{ id: 'f', category: 'prezident', source: 'Baku.ws', sourceUrl: 'https://baku.ws/x', title: 'ABŞ-nin birinci xanımı Oleşkidə atəşkəslə bağlı diplomatik görüş təşkil edəcək', publishedAt: at, lang: 'az' }];
  assert.equal(ctx.api.prezHome(foreign).length, 0, 'yad xanım Zuğulbaya düşmür');
});
test('owner notes: turning notifications on shows a confirmation notification at once', async () => {
  const shown = [];
  const ctx = app({ window: { addEventListener() {}, Notification: { permission: 'granted' } }, Notification: { permission: 'granted' } });
  vm.runInContext('renderTicker = () => {};', ctx);
  ctx.api.S.swReg = { showNotification: async (title, o) => { shown.push([title, o]); } };
  await vm.runInContext('armNotify()', ctx);
  assert.equal(ctx.api.storage.getItem('8ulduz-notify'), '1');
  assert.ok(shown.length === 1 && shown[0][0] === 'Son dəqiqə' && /Bildiriş aktivdir/.test(shown[0][1].body), 'aktiv edən kimi nümunə bildiriş gəlir');
});
test('owner notes: slider images are all fetched as soon as the reader touches the slider; the Zuğulba list looks further ahead', () => {
  const src = fs.readFileSync(path.join(root, 'assets/app.js'), 'utf8');
  assert.ok(src.includes('row.addEventListener("pointerdown", all, { once: true, passive: true })') && src.includes('row.children[at - 1], row.children[at]'), 'slayder: toxunanda hamısı, əvvəlki slayd da əvvəlcədən');
  assert.ok(src.includes('lent.clientHeight + 900') && src.includes('lent.addEventListener("touchstart", loadNear'), 'Zuğulba: 900 px irəli, toxunanda dərhal');
});
test('owner notes: rare pages (sources, about, sections) live in sehife.js, are asked only when opened and still render with the helpers', () => {
  const src = fs.readFileSync(path.join(root, 'assets/app.js'), 'utf8');
  assert.equal(src.split('import("./sehife.js")').length - 1, 1);
  assert.ok(!src.includes('<h1>Haqqımızda</h1>') && !src.includes('<h1>Mənbə vəziyyəti</h1>') && !src.includes('<ul class="mine">'), 'səhifə mətnləri app.js-də deyil');
  const mod = fs.readFileSync(path.join(root, 'assets/sehife.js'), 'utf8').replace(/\r\n/g, '\n');
  for (const n of ['sourcesView', 'aboutView', 'sectionsView']) assert.ok(mod.includes(`export function ${n}(d)`), n);
  const ctx = app(), { S } = ctx.api;
  const m = vm.runInContext('(function(){' + mod.replace(/^export /gm, '') + '\nreturn { sourcesView, aboutView, sectionsView }; })()', ctx);
  S.data = { articles: [{ id: 'a', title: 'Xəbər', source: 'APA', sourceUrl: 'https://apa.az/1', category: 'gundem', lang: 'az', publishedAt: new Date().toISOString() }] };
  S.sources = { sources: [{ name: 'APA', url: 'https://apa.az/rss', count: 3, okAt: new Date().toISOString() }] };
  vm.runInContext('globalThis.__deps = { S, esc, sourceName, shownSource, removedSource, sourceLevel, ago, trackedSources, sectionPref, CATS, ASSISTANT_ON, DRIVER_ON, config: { contact: "a@b.az", goatcounter: "x" } };', ctx);
  const d = ctx.__deps;
  assert.ok(m.aboutView(d).includes('<h1>Haqqımızda</h1>') && m.aboutView(d).includes('a@b.az'));
  assert.ok(m.sourcesView(d).includes('<h1>Mənbə vəziyyəti</h1>') && m.sourcesView(d).includes('src-row ok'));
  assert.ok(m.sectionsView(d).includes('<h1>Mənim bölmələrim</h1>') && m.sectionsView(d).includes('data-act="sec-toggle"'));
  assert.equal(ctx.api.homeView.name, 'homeView');
  assert.ok(vm.runInContext('aboutView()', ctx).includes('Yüklənir'), 'modul gələnə qədər yüklənir yazısı');
});
test('owner notes: share icons come from one sprite file, the phone install chip sits inside the section rows, the language list is one row per language', () => {
  const sprite = fs.readFileSync(path.join(root, 'assets/sosial.svg'), 'utf8');
  for (const id of ['fb', 'x', 'wa', 'tg', 'in', 'mail', 'cp']) assert.ok(sprite.includes(`<symbol id="${id}"`), id);
  assert.ok(!/<script|on\w+=/i.test(sprite), 'sprite-də skript yoxdur');
  const ctx = app(), { card, S } = ctx.api, at = new Date().toISOString();
  S.og = {};
  const html = card({ id: '1', title: 'Xəbər', lang: 'az', category: 'gundem', source: 'APA', sourceUrl: 'https://apa.az/1', publishedAt: at });
  const shIcon = vm.runInContext('shIcon', ctx); // panelin işarələri sprite-dandır
  assert.equal(shIcon('fb'), '<svg aria-hidden="true"><use href="./assets/sosial.svg#fb"/></svg>', 'işarə <use> ilə çəkilir, hərf yoxdur');
  assert.ok(html.includes('class="share"') && !html.includes('class="sh"'), 'kartda yalnız düymə');
  // telefon: yuxarı zolağın qutusu açılır, dil + rejim + şrift loqo sətrində, Namaz + hava + lupa + «Ana ekrana əlavə et» ikinci sətirdə
  const css = fs.readFileSync(path.join(root, 'assets/app.css'), 'utf8');
  assert.ok(css.includes('.hrow>.topbar,.hrow>.topbar>.wrap{display:contents}') && css.includes('.hrow .ldd{order:2;margin-left:auto}') && css.includes('.hrow .prefs{order:3') && css.includes('.hrow::after{content:"";order:4;flex:1 0 100%') && css.includes('.inst{order:8;margin-left:auto}'), 'telefon sətirləri sahibin sırası ilə');
  assert.ok(css.includes('.ticker .lbl .bell svg{display:block;width:14px;height:14px;fill:currentColor}') && fs.readFileSync(path.join(root, 'assets/sosial.svg'), 'utf8').includes('<symbol id="bell"') && css.includes('.ticker .lbl .bell{font-size:0'), 'telefonda «Bildiriş» sözü yox, zəng işarəsi');
  assert.ok(css.includes('.mk{display:grid;grid-template-columns:minmax(0,1fr) auto'), 'məzənnə kartı iki sətir');
  const src = fs.readFileSync(path.join(root, 'assets/app.js'), 'utf8');
  assert.ok(src.includes('const dec = Math.min(i.dec ?? 2, 2);') && src.includes('${fmt(i.value, dec)}'), 'kartda nöqtədən sonra ən çox 2 rəqəm');
  const list = ctx.api.languagePicker();
  assert.equal((list.match(/class="ldm/g) || []).length, 5, 'dörd dil + «Hamısı», hər biri öz sətrində');
  assert.ok(list.indexOf('data-lang="az"') < list.indexOf('data-lang=""'), '«Hamısı» sonda');
  assert.ok(css.includes('.ldd-btn .flag,.lang-list .flag{width:22px;height:22px;border-radius:50%') && css.includes('.ldd-pop{') && css.includes('background:#fff;color:#0a1120'), 'dairəvi bayraq, fərqli fonlu kart');
});
test('follow stays in the header; the channel promotion and duplicate footer follow control are removed', () => {
  const cfg = fs.readFileSync(path.join(root, 'assets/config.js'), 'utf8');
  assert.ok(cfg.includes('telegram: "https://t.me/') && !cfg.includes('telegram: "https://t.me/"'), 'config.js-də Telegram ünvanı var');
  const els = {};
  const el = id => els[id] ||= { id, _html: '', set innerHTML(v) { this._html = v; }, get innerHTML() { return this._html; }, addEventListener() {}, classList: { toggle() {}, add() {}, remove() {} }, querySelector() { return null; }, querySelectorAll() { return []; }, focus() {}, dataset: id === 'app' ? { shell: '1' } : {}, style: {}, setAttribute() {}, set onclick(f) {}, hidden: false };
  const ctx = app({
    location: { hash: '#/', href: 'https://8ulduz.az/' }, history: { replaceState() {} },
    window: { addEventListener() {}, SITE_CONFIG: { goatcounter: '', telegram: 'https://t.me/kanal', contact: '' } },
    document: { documentElement: { dataset: {}, style: {} }, hidden: false, activeElement: null, addEventListener() {}, querySelector(s) { const m = s.match(/^#([\w-]+)$/); return m ? el(m[1]) : null; }, querySelectorAll() { return []; }, createElement() { return { set innerHTML(v) { this._v = v; }, content: {}, children: [] }; } },
    requestAnimationFrame: () => 0,
  });
  vm.runInContext('shell()', ctx);
  assert.equal(els.app.innerHTML, '', 'statik qabıq (data-shell) yenidən yazılmır');
  const index = fs.readFileSync(path.join(root, 'index.html'), 'utf8');
  assert.ok(!index.includes('id="cta"'), 'kanala qoşulma kartı yoxdur');
  assert.equal((index.match(/class="follow-btn"/g) || []).length, 1, 'yalnız başlıqdakı izləmə düyməsi qalır');
  vm.runInContext('S.data = {articles: []}; renderFooter();', ctx);
  assert.ok(!els.footer.innerHTML.includes('data-act="follow"'), 'altlıqda təkrar izləmə yoxdur');
  assert.ok(els.footer.innerHTML.includes('Haqqımızda'), 'faydalı altlıq keçidləri saxlanır');
});

// Sahibin 4 noyabr videoları (08.mp4, 09.mp4): yenidən açılışda hazır ilk ekranda Zuğulbanın ilk kartı rusca idi (Day.Az),
// hava «—» → Bakı 19° → şəhər 15° titrəyirdi, «2 yeni xəbər» düyməsi səhifənin başında asılı qalırdı (sahib aşağı çəkib yenilədi).
test('Zuğulba: the reader\'s language comes first; other languages only fill the tail', () => {
  const ctx = app(), { prezHome, S } = ctx.api;
  const at = i => new Date(Date.now() - i * 3600e3).toISOString();
  const row = (id, i, lang, title) => ({ id, lang, category: 'prezident', source: lang === 'az' ? 'Günün Səsi' : 'Day.Az', title, sourceUrl: 'https://x.az/' + id, publishedAt: at(i) });
  const az = Array.from({ length: 5 }, (_, i) => row('a' + i, i + 2, 'az', 'İlham Əliyev təbrik edib ' + i));
  const ru = Array.from({ length: 50 }, (_, i) => row('r' + i, i, 'ru', 'Ильхам Алиев принял посла ' + i));
  S.lang = 'az';
  const out = [...prezHome(az, [...ru, ...az])];
  assert.equal(out.length, 44, 'say qaydası qalır: dil çatmayanda başqa dil doldurur');
  assert.deepEqual(out.slice(0, 5).map(a => a.id), ['a0', 'a1', 'a2', 'a3', 'a4'], 'oxucunun dili əvvəl, rusca daha təzə olsa da');
  assert.ok(out.slice(5).every(a => a.lang === 'ru'), 'başqa dil yalnız sonda');
  const many = Array.from({ length: 50 }, (_, i) => row('m' + i, i + 2, 'az', 'İlham Əliyev qəbul edib ' + i));
  assert.ok([...prezHome(many, [...ru, ...many])].every(a => a.lang === 'az'), 'dil dolursa başqa dil heç girmir');
});
test('pending render re-arms while the reader is busy: new stories apply after the last touch, not at the next minute poll', () => {
  const ctx = app(), { S, requestRender } = ctx.api;
  const timers = []; ctx.timers = timers;
  vm.runInContext('globalThis.setTimeout = (fn, ms) => { timers.push([fn, ms]); return timers.length; }; globalThis.clearTimeout = () => {};', ctx);
  S.data = { articles: [] }; S.touchAt = Date.now(); S.pendingNew = 3;
  requestRender();
  assert.equal(S.renderPending, true);
  let [fn, ms] = timers.pop(); assert.equal(ms, 8500);
  fn(); // hələ məşğuldur: əvvəl burada dayanırdı, növbəti dəqiqəyə qalırdı
  [fn, ms] = timers.pop(); assert.equal(ms, 2000, 'məşğul qalıbsa 2 saniyədən bir yoxlanır');
  assert.equal(S.renderPending, true);
  S.touchAt = 0; fn();
  assert.equal(S.renderPending, false, 'toxunma kəsilən kimi çəkilir');
  assert.equal(S.pendingNew, 0, 'düymə sönür');
});
test('weather and prayer times wait for the known location: no Bakı-then-city flicker, last weather restored from storage', async () => {
  const store = new Map(), ls = { getItem: k => store.has(k) ? store.get(k) : null, setItem: (k, v) => store.set(k, String(v)), removeItem: k => store.delete(k) };
  const wxJson = { current: { temperature_2m: 15, apparent_temperature: 14, relative_humidity_2m: 50, precipitation: 0, weathercode: 1, surface_pressure: 1010, wind_speed_10m: 3 } };
  const make = (state, urls) => app({ localStorage: ls,
    navigator: { onLine: true, geolocation: { getCurrentPosition: ok => ok({ coords: { latitude: 40.6828, longitude: 46.3606 } }) }, permissions: { query: async () => ({ state }) } },
    fetch: async u => { urls.push(String(u)); return { ok: true, json: async () => /current=temperature_2m/.test(u) ? wxJson : /aladhan/.test(u) ? { data: { timings: { Fajr: '05:55' } } } : {} }; } });
  const settle = async () => { for (let i = 0; i < 20; i++) await new Promise(r => setImmediate(r)); };
  // Konum icazəsi əvvəl verilib: əvvəl şəhər, sonra hava və namaz — Bakı sorğusu heç getmir
  let urls = [];
  const ctx = make('granted', urls);
  ctx.api.storage.setItem('8ulduz-geo', '1');
  await vm.runInContext('loadLocal()', ctx); await settle();
  const wx = urls.filter(u => /current=temperature_2m/.test(u)), pray = urls.filter(u => /aladhan/.test(u));
  assert.equal(wx.length, 1, 'bir hava sorğusu'); assert.ok(wx[0].includes('latitude=40.6828'), 'birbaşa Gəncə: ' + wx[0]);
  assert.equal(pray.length, 1); assert.ok(pray[0].includes('latitude=40.6828'), 'namaz da Gəncə');
  assert.equal(ctx.api.S.wx.city, 'Gəncə'); assert.equal(ctx.api.S.wx.temp, 15);
  // Növbəti açılış: son hava yaddaşdan dərhal («—» yerinə)
  const next = make('granted', []);
  vm.runInContext('restoreLocal()', next);
  assert.equal(next.api.S.wx?.temp, 15, 'yaddaşdakı hava'); assert.equal(next.api.S.wx.city, 'Gəncə');
  // İcazə yoxdursa (soruşulmamış): Bakı ilə gəlir, konum soruşulmur
  urls = []; store.delete('8ulduz-geo');
  const plain = make('prompt', urls);
  await vm.runInContext('loadLocal()', plain); await settle();
  const wx2 = urls.filter(u => /current=temperature_2m/.test(u));
  assert.equal(wx2.length, 1); assert.ok(wx2[0].includes('latitude=40.4093'), 'Bakı');
  assert.ok(!plain.api.S.geo, 'konum soruşulmayıb');
});

// Sahibin 4 noyabr qeydləri (telefon): sosial hesablar alt-alta, X/Facebook-dan geri sayta, Facebook paylaşımında xəbər görünsün,
// kopyalanan keçiddə xəbər bilinsin və geri sayta qayıtsın.
test("owner's share notes (2026-11-08): every 16-hex story shares www.8ulduz.az/ID — minute-feed stories too, no flag needed (the Worker builds the og page); non-hex ids keep the hash link; copy carries the title", async () => {
  const ctx = app(), { card, S } = ctx.api, at = new Date().toISOString();
  S.og = {};
  const row = (id, extra = {}) => ({ id, title: 'Xəbər', lang: 'az', category: 'gundem', source: 'APA', sourceUrl: 'https://apa.az/' + id, publishedAt: at, ...extra });
  S.data = { articles: [] };
  assert.ok(card(row('0123456789abcdef')).includes(`data-share="https://www.8ulduz.az/0123456789abcdef?h=${at.slice(2, 13).replace(/\D/g, '')}"`), 'bayraqsız da: keçid Worker-ə, o səhifəni tapır və ya qurur (docs/x-worker.md)');
  S.data = { articles: [], sharePages: true };
  assert.ok(card(row('0123456789abcdef')).includes(`data-share="https://www.8ulduz.az/0123456789abcdef?h=${at.slice(2, 13).replace(/\D/g, '')}"`), 'main-dəki xəbər');
  assert.ok(card(row('0123456789abcdef', { live: 1 })).includes(`data-share="https://www.8ulduz.az/0123456789abcdef?h=${at.slice(2, 13).replace(/\D/g, '')}"`), 'dəqiqəlik kanaldan gələn təzə xəbər də eyni ünvan: səhifəsi yoxdursa Worker lentdən qurur');
  assert.ok(card(row('0123456789abcdef', { publishedAt: '' })).includes('data-share="https://www.8ulduz.az/0123456789abcdef"'), 'vaxtsız sətirdə h yoxdur');
  assert.ok(card(row('1')).includes(`data-share="https://8ulduz.az/#/xeber/1?b=gundem&amp;h=${at.slice(2, 13).replace(/\D/g, '')}"`), '16 rəqəmli olmayan nömrə');
  const src = fs.readFileSync(path.join(root, 'assets/app.js'), 'utf8'); assert.ok(!src.includes('8ulduz.az/x/') && !src.includes('a.live') && !src.includes('sharePages && '), 'köhnə /x/ yolu, dəqiqəlik işarə və bayraq şərti koddan çıxıb (yer: app.js 220 000 həddindədir)');
  const written = [];
  ctx.navigator.clipboard = { writeText: async s => { written.push(s); } };
  const btn = { dataset: { to: 'cp' }, classList: { contains: () => true }, textContent: 'c', closest: () => ({ dataset: { share: 'https://8ulduz.az/x/0123456789abcdef', title: 'Neft bahalaşdı' } }) };
  await vm.runInContext('shareTo', ctx)(btn);
  assert.deepEqual(written, ['Neft bahalaşdı\nhttps://8ulduz.az/x/0123456789abcdef'], 'kopyada başlıq + keçid');
});

test("owner's share notes: on Android share targets open the app in place, official accounts open in a Chrome tab (Back returns to the site)", () => {
  const ctx = app({ navigator: { onLine: true, userAgent: 'Mozilla/5.0 (Linux; Android 14) Chrome/130 Mobile' }, location: { hash: '#/', href: 'https://8ulduz.az/' } });
  const appLink = vm.runInContext('appLink', ctx);
  assert.equal(appLink('https://x.com/presidentaz'), 'intent://x.com/presidentaz#Intent;scheme=https;package=com.twitter.android;S.browser_fallback_url=https%3A%2F%2Fx.com%2Fpresidentaz;end');
  assert.ok(appLink('https://www.facebook.com/sharer/sharer.php?u=https%3A%2F%2F8ulduz.az%2Fx%2F1').startsWith('intent://www.facebook.com/sharer/sharer.php?u=https%3A%2F%2F8ulduz.az%2Fx%2F1#Intent;scheme=https;package=com.facebook.katana;'), 'Facebook paylaşımı tətbiqdə');
  assert.ok(appLink('https://wa.me/?text=B%0Ahttps%3A%2F%2F8ulduz.az').includes('package=com.whatsapp;') && appLink('https://t.me/share/url?url=u').includes('package=org.telegram.messenger;') && appLink('https://www.youtube.com/@presidentaz').includes('package=com.google.android.youtube;'));
  assert.equal(appLink('https://president.az/az'), '', 'tətbiqi olmayan sayt əvvəlki kimi');
  assert.equal(appLink('http://x.com/a'), '', 'yalnız https');
  assert.equal(vm.runInContext('appLink', app())('https://x.com/presidentaz'), '', 'Android deyilsə yeni vərəq (window.open)');
  let prevented = false;
  const a = { href: 'https://www.instagram.com/presidentaz/', closest: sel => sel === '.soc-g a' ? a : null };
  vm.runInContext('onClick', ctx)({ target: a, preventDefault() { prevented = true; } });
  assert.equal(ctx.location.href, 'intent://www.instagram.com/presidentaz/#Intent;scheme=https;package=com.android.chrome;S.android.support.customtabs.extra.SESSION=;S.browser_fallback_url=https%3A%2F%2Fwww.instagram.com%2Fpresidentaz%2F;end', 'rəsmi hesab: Chrome Custom Tab kimi (saytın tapşırığında; tətbiqdən və adi vərəqdən geri baş ekrana düşürdü), geri sayta');
  assert.ok(prevented);
  assert.equal(vm.runInContext('chromeLink', ctx)('http://x.com/a'), '', 'yalnız https');
  const btn = { dataset: { to: 'fb' }, classList: { contains: () => true }, closest: () => ({ dataset: { share: 'https://8ulduz.az/x/0123456789abcdef', title: 'B' } }) };
  vm.runInContext('shareTo', ctx)(btn);
  assert.ok(ctx.location.href.startsWith('intent://www.facebook.com/sharer/sharer.php?u=https%3A%2F%2F8ulduz.az%2Fx%2F0123456789abcdef#Intent;'), 'paylaşma düyməsi də');
});

test("owner's share notes: a story opened from a shared link gets the home page under it so Back returns to the site", () => {
  const calls = [];
  const ctx = app({ location: { hash: '#/xeber/0123456789abcdef?b=gundem' }, history: { length: 1, replaceState: (s, t, u) => calls.push(['replace', u]), pushState: (s, t, u) => calls.push(['push', u]) } });
  vm.runInContext('backHome()', ctx);
  assert.deepEqual(calls, [['replace', '#/'], ['push', '#/xeber/0123456789abcdef?b=gundem']]);
  calls.length = 0; ctx.history.length = 3;
  vm.runInContext('backHome()', ctx);
  assert.deepEqual(calls, [], 'saytın içindən açılan xəbərdə tarixçə dəyişmir');
  assert.ok(fs.readFileSync(path.join(root, 'assets/app.js'), 'utf8').includes('else loadShared(r0.id); backHome(); }'), 'açılışda paylaşılan keçiddə çağırılır');
});

test("owner's share notes: the worker leaves /x/ID to the browser, 404.html sends an expired share page to the story, phone CSS stacks the accounts", () => {
  const {listeners} = worker();
  let called = false;
  listeners.fetch({request: {url: 'https://example.com/8ulduz/x/0123456789abcdef', mode: 'navigate', method: 'GET'}, respondWith() { called = true; }});
  assert.equal(called, false, 'paylaşma səhifəsi işçinin keşinə düşmür');
  const nf = fs.readFileSync(path.join(root, '404.html'), 'utf8');
  const code = nf.match(/<script>([^<]*location\.replace[^<]*)<\/script>/)[1];
  const hash = require('crypto').createHash('sha256').update(code).digest('base64');
  assert.ok(nf.includes(`'sha256-${hash}'`), '404 səhifəsinin yönləndirmə skripti CSP-dədir');
  assert.ok(code.includes('/\\/x\\/([0-9a-f]{16})$/') && code.includes('location.replace("/#/xeber/"+m[1]+q)') && code.includes('location.replace("/xeber/"+x[1]+"/"+q)'), '/x/ID → #/xeber/ID (tarixçədə iz qoymur)');
  const css = fs.readFileSync(path.join(root, 'assets/app.css'), 'utf8').replace(/\r\n/g, '\n');
  const phone = css.slice(css.lastIndexOf('@media(max-width:600px)'));
  assert.ok(phone.includes('.prez .soc-links{flex-direction:column') && phone.includes('.prez .soc-g{flex-direction:row;flex-wrap:wrap') && !phone.includes('attr(title)'), 'telefonda iki sətir: üstdə İlham Əliyev, altda Mehriban Əliyeva, işarələr əvvəlki kimi');
  assert.ok(css.includes('.soc-g a svg,.soc-ic svg{width:16px;height:16px;fill:currentColor}'), 'işarələr sprite-dan ölçülənir');
  const svg = fs.readFileSync(path.join(root, 'assets/sosial.svg'), 'utf8');
  assert.ok(svg.includes('<symbol id="ig"') && svg.includes('<symbol id="yt"'), 'Instagram və YouTube işarələri sprite-dadır');
  const { profileRows } = { profileRows: vm.runInContext('profileRows', app()) };
  const rows = profileRows();
  assert.ok(rows.includes('sosial.svg#ig') && !rows.includes('class="hd"') && !rows.includes('<path') && rows.indexOf('İlham Əliyev') < rows.indexOf('Mehriban Əliyeva'), 'hesab sətri: sprite işarəsi, ad yoxdur, İlham Əliyev əvvəl');
});

test("owner's share video (2026-11-05): on a phone «Paylaş» opens the system share sheet with title and link; the desktop keeps the panel", () => {
  const shared = [];
  const ctx = app({ navigator: { onLine: true, userAgent: 'Mozilla/5.0 (Linux; Android 14) Chrome/130 Mobile', share: o => { shared.push(o); return Promise.resolve(); } }, matchMedia: q => ({ matches: q === '(hover:none)' }) });
  const art = { querySelector: () => ({ textContent: ' Neft bahalaşdı ' }) };
  const btn = { dataset: { share: 'https://8ulduz.az/x/0123456789abcdef' }, closest: sel => sel === 'article' ? art : null };
  vm.runInContext('shareStory', ctx)(btn);
  assert.deepEqual(JSON.parse(JSON.stringify(shared)), [{ title: 'Neft bahalaşdı', text: 'Neft bahalaşdı', url: 'https://8ulduz.az/x/0123456789abcdef' }], 'telefonda sistem pəncərəsi: başlıq + keçid (tətbiq paylaşımdan sonra sayta qayıdır)');
  const pops = [];
  const desk = app({ navigator: { onLine: true, share: o => { shared.push(o); return Promise.resolve(); } }, matchMedia: () => ({ matches: false }) });
  vm.runInContext('showPop = (b, h) => { __pops.push(h); return { dataset: {} }; }', Object.assign(desk, { __pops: pops }));
  vm.runInContext('shareStory', desk)(btn);
  assert.equal(shared.length, 1); assert.equal(pops.length, 1); assert.ok(pops[0].includes('data-to="x"') && pops[0].includes('data-to="sys"'), 'kompüterdə panel, «Başqa…» ilə');
});
test('article page lists up to 3 related stories by rare shared title words, not by common names',()=>{
  const ctx=app(), {S,articleView}=ctx.api, t=new Date().toISOString();
  const row=(id,title,lang='az')=>({id,title,lang,source:'APA',sourceUrl:'https://apa.az/'+id,publishedAt:t,category:'gundem'});
  const filler=Array.from({length:200},(_,i)=>row('f'+i,`İlham Əliyev görüş keçirib nömrə${i} mövzu${i} xəbər${i}`));
  S.data={articles:[row('a','Bakıda Xəzər sahilində yeni park açılıb'),row('b','Xəzər sahilində açılan park sakinləri sevindirib'),row('c','Bakı metrosunda qatarlar gecikir'),row('d','Xəzər parkı haqqında yeni qərar: sahilində kafe olmayacaq'),row('e','Xəzər parkı haqqında yeni qərar: sahilində kafe olmayacaq - FOTO'),...filler]};
  const html=articleView('a');
  assert.match(html,/Bu barədə daha çox/);
  assert.match(html,/href="\/xeber\/b\/"/); // kanonik səhifə; klik #/xeber/b olur
  assert.equal((html.match(/href="\/xeber\/[de]\/"/g)||[]).length,1,'eyni başlığın ikinci nüsxəsi təkrarlanmır');
  assert.doesNotMatch(html,/xeber\/c\//,'yalnız «Bakı» ortaqdır');
  assert.doesNotMatch(html,/xeber\/f\d/,'İlham Əliyev çox işlənir, əlaqə sayılmır');
  S.data.articles.push(row('g','Şuşa əməliyyatı ilə bağlı mühüm DETAL AÇIQLANDI'),row('h','Nazirdən məktəblərlə bağlı MÜHÜM AÇIQLAMA'));
  S.data.articles.push(row('i','İtkin düşənlərə həsr olunan tədbir keçirilib'),row('j','Zəfər Gününə həsr olunan mini-futbol turniri keçirilib'));
  assert.doesNotMatch(articleView('i'),/xeber\/j\//,'«həsr olunan tədbir» əlaqə deyil');
  assert.doesNotMatch(articleView('g'),/xeber\/h\//,'«mühüm açıqlama» kimi ümumi sözlər əlaqə deyil');
  assert.doesNotMatch(articleView('f0'),/xeber\/f\d+\//,'eyni adlı fərqli görüşlər bir-birinə bağlanmır');
});
test('owner 2026-11-07: on a phone the Zuğulba block is a closed header that opens on tap; ☰ is gold', () => {
  const ctx = app(), { S } = ctx.api;
  const block = vm.runInContext('prezBlock', ctx);
  assert.match(block([]), /^<section class="prez"><div class="prez-h">/);
  S.prezOpen = true;
  assert.match(block([]), /^<section class="prez open">/, 'açıq qalır (yenidən çəkilişdə bağlanmır)');
  const css = fs.readFileSync(path.join(root, 'assets/app.css'), 'utf8'), js = fs.readFileSync(path.join(root, 'assets/app.js'), 'utf8');
  assert.ok(css.includes('.prez-h h2{font-size:clamp(15px,6vw,25px);letter-spacing:0;min-width:0}') && css.includes('.prez:not(.open) .prez-body{display:none}'), 'telefonda bağlı: bir sırada ad, say və ox (kart böyümür)');
  assert.ok(js.includes('<span class="prez-long">Zuğulba Xronikası</span>') && css.includes('.prez:not(.open) .prez-n,.prez:not(.open) .prez-h .btn{display:none}') && js.includes('href="/bolme/prezident/">Hamısı →</a>') && !css.includes('@media(max-width:420px),(min-width:901px){.prez-long'), 'sahib: bağlı halda yalnız «Zuğulba Xronikası», açılanda say və «Hamısı →»');
  assert.ok(js.includes('const h = innerWidth <= 600 && e.target.closest?.(".prez-h"); if (h && !e.target.closest(".btn"))'), 'başlığa basanda açılır, «Hamısı →» bölməyə aparır');
  assert.ok(css.includes('nav.main .nav-more>summary{display:flex;align-items:center;') && css.includes('nav.main .nav-more>summary::before{content:"";width:26px;height:4px;background:currentColor;box-shadow:0 -9px,0 9px;color:var(--primary)}') && css.includes('nav.main{position:relative;padding-right:42px}nav.main .nav-more{display:flex;position:absolute;right:0;top:3px;bottom:3px}'), '☰ fonsuz, sağda iki sətir hündürlüyündə, üstdən-altdan bir az içəri (sahib 2026-11-10)');
});
test('owner 2026-11-07: a shared social post opens hours/days later (archive, selected post first)', () => {
  const ctx = app(), { S, socialBlock } = ctx.api;
  const post = (n, h) => ({ id: String(n).repeat(16), who: 'prezident', name: 'Prezident', network: 'Facebook', text: 'Yazı ' + n, url: 'https://facebook.com/' + n, publishedAt: new Date(Date.now() - h * 3600e3).toISOString() });
  S.social = { posts: [...Array.from({ length: 9 }, (_, i) => post(i + 1, i)), post('a', 300)] };
  const html = socialBlock(false, 'a'.repeat(16));
  assert.ok(html.indexOf('Yazı a') > 0 && html.indexOf('Yazı a') < html.indexOf('Yazı 1'), 'köhnə (9-cudan sonrakı) yazı birinci və seçili');
  assert.match(html, /class="soc-r on"/);
  assert.ok(!socialBlock(false).includes('Yazı a') && (socialBlock(false).match(/class="soc-r/g) || []).length === 8, 'adi baxışda son 8 yazı');
  const js = fs.readFileSync(path.join(root, 'assets/app.js'), 'utf8');
  assert.ok(js.includes('!S.social.posts.some(p => p.id === s) && (await requestJSON(freshUrl("data/social-arxiv.json"))).d?.posts?.find(p => p.id === s)'), 'social.json-da yoxdursa arxivdən, yalnız onda');
});
test('owner 2026-11-14: a new story does not move the ticker line being read; a held ticker is not rebuilt until released', () => {
  // Zolaq: hər keçid 200 px; yeni xəbər əvvələ düşəndə köhnə keçidlər 200 px sağa gedir. Oxunan xəbər ekranda eyni yerdə qalmalıdır.
  let anim = null;
  const build = hrefs => { const all = [...hrefs, ...hrefs]; return { children: all.map((h, i) => ({ offsetLeft: 8 + i * 200, getAttribute: () => h })), scrollWidth: all.length * 200, style: {}, animate: (k, o) => (anim = { currentTime: 0, playState: 'running', cancel() {}, play() { this.playState = 'running'; }, pause() { this.playState = 'paused'; }, o }) }; };
  let track = build(['a', 'b', 'c', 'd']);
  const run = {};
  const ctx = app({ document: { documentElement: { dataset: {} }, addEventListener() {}, querySelector: s => s === '#ticker .run' ? run : s === '#ticker .track' ? track : null, createElement() { return {}; } } });
  const start = vm.runInContext('startTicker', ctx), anchor = vm.runInContext('tickerAnchor', ctx), S = ctx.api.S;
  start();
  const dur = anim.o.duration, half = 800;
  anim.currentTime = 350 / half * dur; // «c» (400–600) zolağın sol hissəsində, x = 50
  const pin = anchor();
  assert.deepEqual({ ...pin }, { href: 'c', x: 50 });
  track = build(['n', 'a', 'b', 'c', 'd']); S.tickAnchor = pin; start();
  const shift = anim.currentTime / anim.o.duration * 1000;
  assert.ok(Math.abs(600 - shift - 50) < 0.01, 'yeni zolaqda «c» yenə x = 50-dədir');
  track = build(['x', 'y']); S.tickAnchor = { href: 'c', x: 50 }; start();
  assert.ok(Number.isFinite(anim.currentTime), 'oxunan xəbər çıxıbsa zolaq köhnə fazadan davam edir');
  const src = fs.readFileSync(path.join(root, 'assets/app.js'), 'utf8');
  assert.ok(src.includes('if (tickAnim?.playState === "paused" && !motionOff()) { S.tickerLater = true; return; }') && src.includes('if (S.tickerLater) renderTicker();'), 'barmaqla saxlanan zolaq buraxılanda yenilənir');
});
test('owner 2026-11-14: the currency strip keeps its scroll on refresh and is prerendered like prayer and weather', () => {
  const src = fs.readFileSync(path.join(root, 'assets/app.js'), 'utf8'), pre = require(path.join(root, '.github/scripts/prerender.cjs'));
  assert.ok(src.includes('if (S.mkHtml !== html) { S.mkHtml = html; const x = S.mkMoved ? grid.scrollLeft : 0; grid.innerHTML = html; if (x) grid.scrollLeft = x; }'), 'eyni qiymət yenidən yazılmır, sürüşdürülən yer saxlanır');
  const first = JSON.parse(fs.readFileSync(path.join(root, 'data/first.json'), 'utf8'));
  const items = [{ id: 'USD', label: 'Dollar', value: 1.7, unit: 'AZN', src: 'AMB', change: 0, changePct: 0 }, { id: 'EUR', label: 'Avro', value: 1.88, unit: 'AZN', src: 'AMB', change: -0.01, changePct: -0.5 }];
  const home = pre.renderHome(root, first, { now: Date.parse(first.updatedAt) || Date.now(), markets: items });
  assert.equal((home.markets.match(/class="mk"/g) || []).length, 2); assert.ok(home.markets.includes('1.88'));
  pre.validateMarkets(home.markets);
  const shell = '<div class="markets pending" id="markets"><div class="wrap mk-wrap"><div class="mk-grid" id="mk"></div><p class="mk-note" id="mk-note" hidden></p>';
  const out = shell.replace(pre.MARKETS_RE, (_, a, b, c, d) => a + b + home.markets + d);
  assert.ok(out.startsWith('<div class="markets" id="markets">') && out.includes('1.88'), 'hazır nüsxədə «pending» yoxdur, kartlar var');
  assert.equal(out.replace(pre.MARKETS_RE, (_, a, b, c, d) => a + b + home.markets + d), out, 'ikinci dəfə eyni');
});
test('owner 2026-11-07: «N yeni xəbər» counts only the news of the page you are on', () => {
  const pill = { hidden: true, textContent: '' };
  const ctx = app({ document: { documentElement: { dataset: {} }, addEventListener() {}, querySelector: s => s === '#newpill' ? pill : null, createElement() { return {}; } } });
  const { S } = ctx.api, sync = vm.runInContext('syncNewPill', ctx);
  const row = (id, category, title = 'Xəbər ' + id) => ({ id, category, title, source: 'APA', sourceUrl: 'https://apa.az/' + id, publishedAt: new Date().toISOString(), lang: 'az' });
  S.pendingNew = [row('1', 'idman', 'Qarabağ qələbə qazandı'), row('2', 'idman', 'Neftçi məğlub oldu'), row('3', 'siyaset'), row('4', 'dunya')];
  // 2026-11-14 (sahib: «az dilində 29 yeni xəbər yazır, klik edirsən 2 xəbər çıxır»): başqa dilin xəbəri və başqa xəbərə mənbə kimi
  // qoşulan (ayrıca kartı olmayan) sətir sayılmır.
  S.pendingNew.push({ ...row('5', 'dunya', 'Breaking news from London'), lang: 'en' }, { ...row('6', 'dunya', 'Новости дня'), lang: 'ru' }, row('7', 'idman', 'Qarabağ qələbə qazandı — təfərrüat'));
  S.lang = 'az'; S.data = { articles: ['1', '2', '3', '4', '5', '6'].map(id => ({ id, sourceUrl: 'https://apa.az/' + id })) };
  ctx.location.hash = '#/'; sync();
  assert.equal(pill.hidden, false); assert.equal(pill.textContent, '↑ 4 yeni xəbər', 'baş səhifədə seçilmiş dilin ayrıca kartları');
  S.lang = null; sync();
  assert.equal(pill.textContent, '↑ 6 yeni xəbər', '«Hamısı» seçiləndə bütün dillər'); S.lang = 'az';
  ctx.location.hash = '#/bolme/idman'; S.club = null; sync();
  assert.equal(pill.textContent, '↑ 2 yeni İdman xəbəri', 'İdmanda yalnız idman');
  S.club = 'Qarabağ'; sync();
  assert.equal(pill.textContent, '↑ 1 yeni Qarabağ xəbəri', 'alt düymədə yalnız onun xəbəri');
  S.club = null; ctx.location.hash = '#/bolme/tehsil'; sync();
  assert.equal(pill.hidden, true, 'bölmədə yeni xəbər yoxdursa düymə görünmür');
  ctx.location.hash = '#/xeber/1'; sync();
  assert.equal(pill.hidden, true, 'xəbəri oxuyanda düymə yoxdur');
});
test('owner 2026-11-14: «Tıxac» stays our page and shows the Waze map at once — on a phone too, with Yandex only as a fallback', () => {
  for (const touch of [true, false]) {
    const tab = { href: '#/tixac', classList: { toggle() {} }, setAttribute() {}, closest: () => ({}) };
    const ctx = app({ matchMedia: q => ({ matches: touch && q === '(hover:none)' }), document: { documentElement: { dataset: {} }, addEventListener() {}, querySelector() { return null; }, querySelectorAll: s => (s === '.tix-btn' ? [tab] : []), createElement() { return {}; } } });
    vm.runInContext('syncTixDot', ctx)();
    assert.equal(tab.href, '#/tixac', 'alt düymə saytın tıxac səhifəsidir (oxucu saytdan çıxmır)');
    const view = vm.runInContext('trafficView', ctx), S = ctx.api.S;
    let html = view();
    assert.ok(html.includes('src="https://embed.waze.com/iframe?zoom=12&amp;lat=40.4093&amp;lon=49.8671"') || html.includes('src="https://embed.waze.com/iframe?zoom=12&lat=40.4093&lon=49.8671"'), 'Waze xəritəsi düyməsiz, dərhal');
    assert.ok(!html.includes('data-act="tix-open"') && !html.includes('yandex.com'), 'əvvəlki «Xəritəni aç» addımı və Yandex yoxdur');
    if (touch) {
      assert.ok(html.includes('data-act="tix-yandex"') && html.includes('Waze tətbiqində aç'), 'telefonda ehtiyat Yandex və tətbiq düyməsi');
      S.tixYandex = true; html = view();
      assert.ok(html.includes('yandex.com/map-widget') && !html.includes('embed.waze.com') && html.includes('Waze xəritəsinə qayıt'), 'oxucu istəsə Yandex, geri qayıtmaq olur');
    } else assert.ok(!html.includes('data-act="tix-yandex"'), 'kompüterdə Yandex düyməsi yoxdur');
  }
  const css = fs.readFileSync(path.join(root, 'assets/app.css'), 'utf8');
  assert.ok(css.includes('.tix-map iframe{height:max(420px,calc(100svh - 230px))}'), 'telefonda xəritə ekran boyu');
});
test('owner 2026-11-10: the bottom bar has four buttons — Bölmələr and Axtar removed (☰ and 🔍 stay above)', () => {
  const js = fs.readFileSync(path.join(root, 'assets/app.js'), 'utf8'), html = fs.readFileSync(path.join(root, 'index.html'), 'utf8');
  for (const src of [js, html]) {
    assert.ok(src.includes('<a href="/bolme/video/" data-tab="video"><b>▶</b><span>Video</span></a>'), 'aşağı zolaqda Video');
    assert.ok(src.includes('<a href="#/tixac" data-tab="traffic" class="tix-btn"><b>⛗</b><span>Tıxac</span></a>'), 'Tıxac qalır');
    assert.equal((src.match(/<nav class="tabbar"[\s\S]*?<\/nav>/)[0].match(/<(?:a|button)\b/g) || []).length, 4, 'aşağıda 4 düymə: Əsas, Video, Tıxac, Seçilmişlər');
    const bar = src.match(/<nav class="tabbar"[\s\S]*?<\/nav>/)[0];
    assert.ok(!bar.includes('data-tab="sections"') && !bar.includes('data-act="find"'), 'Bölmələr və Axtar aşağıda yoxdur');
  }
  assert.ok(js.includes('r.name === "section" && r.slug === "video" ? "video"'), 'Video səhifəsində düymə seçili');
});
test('owner 2026-11-07: the article ends with «Telegram-da izlə» for its district, club or section; the follow panel offers any topic', () => {
  const ctx = app(), { S, articleView } = ctx.api, at = new Date().toISOString();
  const row = (id, category, title) => ({ id, category, title, source: 'APA', sourceUrl: 'https://apa.az/' + id, publishedAt: at, lang: 'az' });
  S.data = { articles: [row('g1', 'bolgeler', 'Gəncədə yeni park açılıb'), row('f1', 'idman', 'Fənərbağça qələbə qazandı'), row('d1', 'dunya', 'Bakıda beynəlxalq forum'), row('s1', 'sondeqiqe', 'Təcili xəbər')] };
  assert.ok(!articleView('g1').includes('tg-izle'), 'botun adı yoxdursa düymə yoxdur');
  ctx.window.SITE_CONFIG = { tgBot: 'SekkizUlduzBot' };
  assert.ok(articleView('g1').includes('?start=r_gence"') && articleView('g1').includes('📩 Gəncə: Telegram-da izlə'), 'rayon');
  assert.ok(articleView('f1').includes('?start=i_fenerbahce"'), 'komanda');
  assert.ok(articleView('d1').includes('?start=b_dunya"'), 'başqa bölmədə rayon yox, bölmə');
  assert.ok(!articleView('s1').includes('tg-izle'), 'Son dəqiqə mövzu deyil');
  const f = fs.readFileSync(path.join(root, 'assets/follow.js'), 'utf8');
  assert.ok(f.includes('lang + "-" : ""}movzu') && f.includes('📩 İstədiyiniz mövzunu Telegram-da izləyin'), 'izlə pəncərəsində bot (saytın dili ilə)');
});
test('owner 2026-11-08: on the English, Russian and Turkish site «Telegram-da izlə» is translated and passes the site language to the bot', () => {
  const ctx = app(), { S, sectionView, searchView } = ctx.api;
  S.data = { articles: [] }; ctx.window.SITE_CONFIG = { tgBot: 'SekkizUlduzBot' }; S.club = null;
  for (const [lang, pre] of [['az', ''], [null, ''], ['en', 'en-'], ['ru', 'ru-'], ['tr', 'tr-']]) {
    S.lang = lang;
    assert.ok(sectionView('dunya').includes(`href="https://t.me/SekkizUlduzBot?start=${pre}b_dunya"`), `${lang}: bölmə`);
  }
  S.lang = 'en'; S.club = 'Fenerbahçe';
  assert.ok(sectionView('idman').includes('?start=en-i_fenerbahce"'), 'komanda/klub');
  S.club = null;
  const bot = require('../.github/scripts/izle.cjs'), q44 = 'ə'.repeat(22);   // 44 bayt: şəkilsiz sığır, «en-» ilə Telegram-ın 64 simvolunu keçir
  S.q = q44; S.lang = 'az'; assert.ok(searchView().includes(`?start=${bot.keyOf(q44)}"`));
  S.lang = 'en'; assert.ok(!searchView().includes('tg-izle'), 'şəkilçi ilə sığmayan söz düymə vermir');
  S.q = 'Iran'; assert.ok(searchView().includes(`?start=en-${bot.keyOf('Iran')}"`));
  assert.ok(`en-${bot.keyOf('ə'.repeat(21))}`.length <= 64);
  const kom = fs.readFileSync(path.join(root, 'assets/komanda.js'), 'utf8'), fol = fs.readFileSync(path.join(root, 'assets/follow.js'), 'utf8');
  assert.ok(kom.includes('?start=${S.lang && S.lang !== "az" ? S.lang + "-" : ""}i_'), 'komanda səhifəsi');
  assert.ok(fol.includes('?start=${/^(en|ru|tr)$/.test(lang) ? lang + "-" : ""}movzu'), 'izlə paneli');
  const cat = bot.catalog(require('../.github/scripts/topics.cjs').loadApp(root)), st = bot.newState();
  bot.handle(st, { update_id: 1, message: { chat: { id: 5, type: 'private' }, text: '/start ru-b_dunya' } }, cat);
  assert.deepEqual([st.subs[5], st.lang[5]], [['b_dunya'], 'ru'], 'bot şəkilçili açarı tanıyır');
  const mod = dilModule('assets/dil.js');
  for (const [l, follow] of [['en', 'Follow on Telegram'], ['ru', 'Следить в Telegram'], ['tr', "Telegram'da takip et"]]) {
    const tr = mod.makeTr(dilModule(`assets/dil-${l}.js`).__d, l);
    assert.equal(tr('📩 Fenerbahçe: Telegram-da izlə'), `📩 ${tr('Fenerbahçe')}: ${follow}`);
    assert.ok(!/ə/.test(tr('📩 İstədiyiniz mövzunu Telegram-da izləyin')), l + ': izlə paneli');
    assert.ok(bot.TEXT[l].all.includes(follow), l + ': botun mətnindəki düymə adı saytdakı ilə eynidir');
  }
});
test('owner 2026-11-07: any topic — a search result offers «Telegram-da izlə» with the search words for the bot', () => {
  const ctx = app(), { S, searchView } = ctx.api;
  S.data = { articles: [] };
  ctx.window.SITE_CONFIG = { tgBot: 'SekkizUlduzBot' };
  S.q = 'İran Amerika';
  const { keyOf } = require('../.github/scripts/izle.cjs');
  assert.ok(searchView().includes(`href="https://t.me/SekkizUlduzBot?start=${keyOf('İran Amerika')}"`) && searchView().includes('📩 «İran Amerika»: Telegram-da izlə'));
  S.q = 'x'.repeat(50);
  assert.ok(!searchView().includes('tg-izle'), 'Telegram start parametrinə sığmayan söz düymə vermir');
});
test('owner 2026-11-07: «Telegram-da izlə» on section pages opens the bot with the section or the chosen club/district', () => {
  const ctx = app(), { S, sectionView } = ctx.api;
  S.data = { articles: [] };
  assert.ok(!sectionView('idman').includes('tg-izle'), 'botun adı yoxdursa düymə yoxdur');
  ctx.window.SITE_CONFIG = { tgBot: 'SekkizUlduzBot' };
  S.club = null;
  assert.ok(sectionView('dunya').includes('href="https://t.me/SekkizUlduzBot?start=b_dunya"'), 'bölmə');
  S.club = 'Fenerbahçe';
  assert.ok(sectionView('idman').includes('href="https://t.me/SekkizUlduzBot?start=i_fenerbahce"') && sectionView('idman').includes('📩 Fenerbahçe: Telegram-da izlə'), 'komanda');
  S.club = 'Quba';
  assert.ok(sectionView('bolgeler').includes('?start=r_quba"'), 'rayon');
  S.club = null;
  assert.ok(!sectionView('sondeqiqe').includes('tg-izle'), 'Son dəqiqə mövzu deyil');
  const { catalog } = require('../.github/scripts/izle.cjs'), { loadApp } = require('../.github/scripts/topics.cjs');
  const cat = catalog(loadApp(root));
  for (const k of ['b_dunya', 'i_fenerbahce', 'r_quba']) assert.ok(cat.has(k), 'bot açarı tanıyır: ' + k);
});
test('speed 2026-11-07: topic text uses a plain class for Latin/Cyrillic and gives exactly the \p{L} result, rare letters included', () => {
  const ctx = app(), { topicKey, fold } = { topicKey: vm.runInContext('topicKey', ctx), fold: vm.runInContext('fold', ctx) };
  const ref = s => { s = String(s || '').toLowerCase().replace(/[əıöüğşç]/g, ch => ({ ə: 'e', ı: 'i', ö: 'o', ü: 'u', ğ: 'g', ş: 's', ç: 'c' })[ch]);
    return (/[\u00c0-\u024f\u0300-\u036fйё]/.test(s) ? s.normalize('NFD').replace(/[\u0300-\u036f]/g, '') : s).replace(/[^\p{L}\p{N}]+/gu, ' ').trim(); };
  for (const t of ['Qarabağ 2:1 × Neftçi ÷ ²³ µ', 'Карабах — ёлка «ура» “x” … ‰ Йошкар-Ола', 'Ελλάδα ١٢٣ 中国', 'İLHAM ƏLİYEV İnter', 'a҂b҃c', 'naïve café', 'x\u00a0y', '', '⚽️ Fənərbağça ➡ “Qalatasaray”', 'Реал — «Барселона» 3:0'])
    assert.equal(topicKey(t), ref(t), t);
  assert.equal(fold('Йошкар ёж İnter'), 'иошкар еж inter');
});

test('owner 2026-11-08 «1 dəq öncə Mehriban Əliyeva Youtubda paylaşımı bizdə yoxdur»: official posts come from the minute channel, fetched only when the status stamp changes', async () => {
  const urls = [];
  let stamp = 'r1', liveMissing = false;
  const ctx = app({ fetch: async u => {
    const s = String(u); urls.push(s);
    if (liveMissing && /\/live\/m\/\d+\/social\.json$/.test(s)) return { ok: false, status: 404, json: async () => ({}) };
    return { ok: true, status: 200, json: async () => /status\.json/.test(s) ? { social: stamp } : { rev: stamp, posts: [] } };
  } });
  const { S } = ctx.api, run = c => vm.runInContext(c, ctx), tick = () => new Promise(r => setTimeout(r, 5));
  const social = () => urls.filter(u => /social\.json/.test(u)), LIVE = /^https:\/\/raw\.githubusercontent\.com\/8ulduz\/8ulduz\/live\/m\/\d+\/social\.json$/;
  await run('loadStatus()'); await tick();
  assert.equal(social().length, 0, 'açılışda sosial yazılar xəbərlərdən sonra (afterNews) çəkilir: status onları qabağa salmır');
  S.status = {}; await run('loadSocial()');
  assert.equal(social().at(-1), 'data/social.json', 'möhür yoxdur (köhnə pipeline): saytın faylı, əvvəlki kimi (sorğu açarı yoxdur, CDN nüsxəsi)');
  await run('loadStatus()'); await tick();
  assert.match(social().at(-1), LIVE, 'möhür gəldi: dəqiqəlik kanal');
  assert.equal(S.socialRev, 'r1');
  const n = social().length;
  await run('loadStatus()'); await tick();
  assert.equal(social().length, n, 'möhür dəyişməyibsə sorğu yoxdur');
  stamp = 'r2'; await run('loadStatus()'); await tick();
  assert.equal(social().length, n + 1, 'yeni yazı: bir sorğu');
  assert.match(social().at(-1), LIVE);
  liveMissing = true; stamp = 'r3'; await run('loadStatus()'); await tick(); await tick();
  assert.equal(social().at(-1), 'data/social.json', 'dəqiqəlik kanalda yoxdursa saytın faylı');
  assert.equal(S.socialRev, 'r3', 'eyni möhürə təkrar sorğu yoxdur');
  // Service worker-li oxucu: status/latest sw.js ilə, sosial isə birbaşa dəqiqəlik kanaldan.
  const sw = app({ navigator: { onLine: true, serviceWorker: { controller: {} } }, fetch: async u => { urls.push('sw:' + u); return { ok: true, json: async () => ({ posts: [] }) }; } });
  sw.api.S.status = { social: 'x' };
  await vm.runInContext('loadSocial()', sw);
  assert.match(urls.at(-1), /^sw:https:\/\/raw\.githubusercontent\.com\/8ulduz\/8ulduz\/live\/m\/\d+\/social\.json$/);
  const src = fs.readFileSync(path.join(root, 'assets/app.js'), 'utf8');
  assert.ok(src.includes('setInterval(() => S.status?.social || loadSocial(), 5 * 60e3);'), 'möhürsüz (köhnə pipeline) 5 dəqiqədən bir, əvvəlki kimi');
  assert.ok(src.includes('if (!any && (navigator.serviceWorker?.controller || !LIVE_FILE.test(url)) || Date.now() < liveSkipUntil) return null;'),
    'status/latest üçün qayda dəyişmir');
});

// Sürət, 2026-11-09 (agent C tapıntıları): yayımdan sonrakı açılış keşsiz qalmasın, işçi tam lenti gözləməsin, eyni yayım ikinci dəfə çəkilməsin.
test('speed: the data cache survives a deploy — version-free name, legacy copy migrated once, only old caches deleted (2026-11-09)', async () => {
  const SW = fs.readFileSync(path.join(root, 'sw.js'), 'utf8');
  const version = SW.match(/const VERSION = "([^"]+)"/)[1];
  assert.ok(SW.includes('const DATA = "8ulduz-data";'), 'məlumat keşinin adı versiyadan asılı deyil (hər yayımda silinirdi)');
  const u = p => 'https://example.com/8ulduz/data/' + p;
  const stores = { '8ulduz-data-v15': new Map([[u('first.json'), 'köhnə first'], [u('news.json'), 'köhnə news']]), '8ulduz-data': new Map([[u('news.json'), 'yeni news']]) };
  const open = async name => { const m = stores[name] ||= new Map(); const key = r => typeof r === 'string' ? r : r.url;
    return { keys: async () => [...m.keys()].map(k => new Request(k)), match: async r => m.has(key(r)) ? new Response(m.get(key(r))) : undefined, put: async (r, res) => { m.set(key(r), await res.text()); } }; };
  const {listeners, deleted} = worker(['other-app-v1', '8ulduz-static-v15', '8ulduz-data-v15', '8ulduz-data', '8ulduz-static-' + version], open);
  let done; listeners.activate({waitUntil(p) { done = p; }}); await done;
  assert.deepEqual(deleted.sort(), ['8ulduz-data-v15', '8ulduz-static-v15'], 'versiyasız məlumat keşi və yeni kod keşi qalır');
  assert.deepEqual([...stores['8ulduz-data'].entries()].sort(), [[u('first.json'), 'köhnə first'], [u('news.json'), 'yeni news']], 'köhnə keşdən yalnız yeni adda olmayan açar köçür');
});
test('speed: loadCached reads the version-free data cache first, a legacy one only as fallback', async () => {
  const first = { updatedAt: 'x', articles: [{ id: 'c1', title: 'Keşdən', source: 'APA', sourceUrl: 'https://apa.az/1', publishedAt: new Date().toISOString(), category: 'gundem', lang: 'az' }] };
  for (const [names, want] of [[['8ulduz-static-v141', '8ulduz-data-v141', '8ulduz-data'], '8ulduz-data'], [['8ulduz-static-v141', '8ulduz-data-v141'], '8ulduz-data-v141']]) {
    const matched = [];
    const ctx = app({ location: { hash: '#/', href: 'https://8ulduz.az/' }, caches: { keys: async () => names, open: async name => ({ match: async url => { matched.push(name); return url.endsWith('/data/first.json') ? { json: async () => first } : undefined; } }) } });
    await ctx.api.loadCached();
    assert.deepEqual([...new Set(matched)], [want]);
    assert.equal(ctx.api.S.data.articles[0].title, 'Keşdən');
  }
});
test('speed: a network first screen identical to the cached one is not drawn twice (same updatedAt); the full feed still follows', async () => {
  const first = { updatedAt: '2026-11-09T10:00:00.123456+00:00', articles: [{ id: 'c1', title: 'Keşdən xəbər', source: 'APA', sourceUrl: 'https://apa.az/1', publishedAt: new Date().toISOString(), category: 'gundem', lang: 'az' }] };
  const ctx = app({ location: { hash: '#/', href: 'https://8ulduz.az/' }, caches: { keys: async () => ['8ulduz-data'], open: async () => ({ match: async url => url.endsWith('/data/first.json') ? { json: async () => first } : undefined }) } });
  const { S, loadCached, loadFirst } = ctx.api;
  vm.runInContext('globalThis.renders = 0; render = () => { renders++; };', ctx);
  await loadCached();
  assert.equal(ctx.renders, 1);
  assert.ok(S.firstRenderAt > 0, 'keşdən çəkiliş də ilk çəkilişdir (FIRST_RENDER_HOLD_MS ondan sayılır)');
  ctx.fetch = async () => ({ ok: true, headers: new Headers(), json: async () => ({ ...first, og: { 'https://apa.az/1': 'https://apa.az/i.jpg' } }) });
  await loadFirst();
  assert.equal(ctx.renders, 1, 'eyni yayım ikinci dəfə çəkilmir (telefonda ~0,7 s uzun iş idi)');
  assert.equal(S.fromCache, false);
  assert.equal(S.partial, true, 'tam lent (loadNews) yenə gözlənilir');
  assert.deepEqual(S.og, { 'https://apa.az/1': 'https://apa.az/i.jpg' }, 'og xəritəsi şəbəkədəkindən');
});
test('speed: a deploy notice while the feed is on screen waits for the tab to hide; only an empty page restarts at once (2026-11-09)', () => {
  const calls = [];
  const ctx = app({ sessionStorage: { getItem: () => null, setItem() {} }, performance: { now: () => 900 }, location: { hash: '#/', reload: () => calls.push('reload') }, scrollY: 0,
    navigator: { onLine: true, serviceWorker: { addEventListener: n => calls.push('listen:' + n), startMessages: () => calls.push('start') } } });
  const { S } = ctx.api;
  vm.runInContext('listenWorker()', ctx);
  assert.deepEqual(calls, ['listen:message', 'start'], 'dinləyici qoyulur, növbədəki mesajlar başladılır');
  calls.length = 0;
  const on = vm.runInContext('onWorkerMessage', ctx);
  on({ data: { type: 'shell-updated' } });
  assert.deepEqual(calls, ['reload'], 'ekranda heç nə yoxdur: dərhal yenidən açılır');
  calls.length = 0; S.reloadWhenHidden = false; S.rawNews = [{ id: 'a' }];
  on({ data: { type: 'shell-updated' } });
  assert.deepEqual(calls, [], 'lent ekrandadır: məzmun → boş → məzmun yoxdur');
  assert.equal(S.reloadWhenHidden, true, 'yeni kod səhifə gözdən itəndə');
  on({ data: { type: 'open-story', id: '0123456789abcdef' } });
  assert.ok(String(ctx.location.hash).includes('#/xeber/0123456789abcdef'), 'bildiriş kliki xəbəri açır');
  const APP = fs.readFileSync(path.join(root, 'assets/app.js'), 'utf8').replace(/\r\n/g, '\n');
  const start = APP.slice(APP.indexOf('\napplyPrefs();\n'));
  assert.ok(start.indexOf('\nlistenWorker();\n') > 0 && start.indexOf('\nlistenWorker();\n') < start.indexOf('\nshell(); render();\n'), 'dinləyici açılışda, ilk çəkilişdən əvvəl');
  assert.ok(start.includes('firstReady.then(() => (globalThis.requestIdleCallback || (f => setTimeout(f, 1000)))(registerWorker, { timeout: 4000 }));') && !/afterNews\([^\n]*registerWorker/.test(start), 'işçi ilk ekrandan sonra boş anda qurulur, tam lentdən sonra deyil (telefonda 10 s idi)');
  assert.ok(!/navigator\.serviceWorker\.addEventListener\("message"/.test(start.slice(start.indexOf('function registerWorker'))), 'registerWorker-də ikinci dinləyici yoxdur');
});

test('speed: on a first visit (no worker yet) the page itself keeps first.json for the next visit, under the key the worker uses', async () => {
  const puts = [];
  const first = { updatedAt: 'x', articles: [{ id: 'n1', title: 'Şəbəkədən', source: 'APA', sourceUrl: 'https://apa.az/1', publishedAt: new Date().toISOString(), category: 'gundem', lang: 'az' }] };
  const ctx = app({ location: { hash: '#/', href: 'https://8ulduz.az/' }, Response, requestIdleCallback: f => f(), caches: { keys: async () => [], open: async name => ({ match: async () => undefined, put: async (k, r) => { puts.push([name, k, await r.json()]); } }) } });
  ctx.fetch = async () => ({ ok: true, headers: new Headers(), json: async () => first });
  await ctx.api.loadFirst();
  await new Promise(r => setTimeout(r, 10));
  assert.equal(puts.length, 1);
  assert.deepEqual(puts[0].slice(0, 2), ['8ulduz-data', 'https://8ulduz.az/data/first.json'], 'versiyasız keş, sorğusuz açar (sw.js networkFirstData bare ilə eyni)');
  assert.equal(puts[0][2].articles[0].title, 'Şəbəkədən');
  puts.length = 0;
  const sw = app({ location: { hash: '#/', href: 'https://8ulduz.az/' }, Response, requestIdleCallback: f => f(), navigator: { onLine: true, serviceWorker: { controller: {} } }, caches: { keys: async () => [], open: async () => ({ match: async () => undefined, put: async (k, r) => { puts.push(k); } }) } });
  sw.fetch = async () => ({ ok: true, headers: new Headers(), json: async () => first });
  await sw.api.loadFirst();
  await new Promise(r => setTimeout(r, 10));
  assert.deepEqual(puts, [], 'işçi idarə edəndə yazan odur (networkFirstData), səhifə yox');
});

test('speed: the cached first screen is not drawn over a prerendered one of the same or a newer deploy; an older prerender is replaced after the first frame', async () => {
  const first = { updatedAt: '2026-11-09T10:00:00.000000+00:00', articles: [{ id: 'c1', title: 'Keşdən xəbər', source: 'APA', sourceUrl: 'https://apa.az/1', publishedAt: new Date().toISOString(), category: 'gundem', lang: 'az' }] };
  const mk = pre => {
    const ctx = app({ location: { hash: '#/', href: 'https://8ulduz.az/' }, caches: { keys: async () => ['8ulduz-data'], open: async () => ({ match: async url => url.endsWith('/data/first.json') ? { json: async () => first } : undefined }) },
      document: { documentElement: { dataset: {} }, addEventListener() {}, querySelector: s => String(s).includes('.pre-skel') ? { dataset: { prerender: pre } } : null, createElement() { return {}; } } });
    vm.runInContext('globalThis.renders = 0; render = () => { renders++; };', ctx);
    return ctx;
  };
  for (const pre of ['2026-11-09T10:00:00.000000+00:00', '2026-11-09T10:10:00.000000+00:00']) {
    const ctx = mk(pre);
    await ctx.api.loadCached();
    assert.equal(ctx.renders, 0, pre + ': hazır ilk ekran eyni və ya təzə yayımdandır, keşdəki çəkilmir');
    assert.equal(ctx.api.S.rawNews, undefined, 'şəbəkə nüsxəsi adi yolla gələcək');
  }
  const ctx = mk('2026-11-09T09:50:00.000000+00:00');
  await ctx.api.loadCached();
  assert.equal(ctx.renders, 1, 'hazır ilk ekran köhnədir: keşdəki çəkilir (ilk kadrdan sonra)');
  assert.equal(ctx.api.S.cachedShown, true);
  assert.equal(ctx.api.S.fromCache, true);
});

test('speed: site data is asked without a per-minute key (CDN copy; forced refresh keeps its own key) — owner decision 2026-11-09', () => {
  const ctx = app(), { freshUrl } = { freshUrl: vm.runInContext('freshUrl', ctx) };
  assert.equal(freshUrl('data/first.json'), 'data/first.json', 'dəqiqəlik ?t= hər faylı CDN-də «tapılmadı» edirdi (+150–250 ms)');
  assert.match(freshUrl('data/news.json', true), /^data\/news\.json\?r=\d+-\d+$/, 'əllə yeniləmə təzəsini istəyir');
  const html = fs.readFileSync(path.join(root, 'index.html'), 'utf8');
  assert.ok(!/\?t=/.test(html.match(/<script>([\s\S]*?)<\/script>/)[1]), 'erkən sorğular da açarsız');
});

// 2026-11-13 yoxlaması: aşağıdakı xətaların hər biri canlı kodda idi.
test('road rules see Azerbaijani suffixes and upper-case headlines (\\w is ASCII-only, /iu does not fold I↔ı)', () => {
  const ctx = app(), run = code => vm.runInContext(code, ctx);
  ctx.titles = ['Sabah Bakıda bu küçələr bağlanacaq', 'Bakıda bəzi yolları bağlanıb', 'Bakıda körpüsü bağlandı', 'Bakı-Sumqayıt yolunda BÖYÜK TIXAC', 'BAKIDA TƏMİR: prospektdə hərəkət məhdudlaşır'];
  assert.deepEqual(Array.from(run('titles.map(t => roadKind(t)?.kind)')), ['bagli', 'bagli', 'bagli', 'tixac', 'bagli']);
  assert.equal(run('roadKind("Qəzalı binada sakinlər köçürülür")'), null, '«qəzalı» yol hadisəsi deyil');
  ctx.rows = ctx.titles.map((title, i) => ({ id: 'r' + i, title, lang: 'az', publishedAt: new Date(Date.now() - 6e5).toISOString() }));
  assert.equal(run('S.lang = null; localRoadItems(rows).length'), 5, 'böyük hərflə yazılmış «BAKIDA» da yerli sayılır');
  assert.ok(!fs.readFileSync(path.join(root, 'assets/app.js'), 'utf8').includes('WARN_RE ='), 'işlənməyən qayda oxucuya getmir');
});
test('next prayer and day-only fixture dates use Baku time for a reader abroad', () => {
  const tz = process.env.TZ;
  try {
    for (const zone of ['Asia/Baku', 'Europe/Istanbul', 'Europe/Berlin', 'America/New_York']) {
      process.env.TZ = zone;
      const now = Date.parse('2026-11-27T11:45:00Z'); // Bakıda 15:45
      const D = class extends Date { constructor(...a) { super(...(a.length ? a : [now])); } static now() { return now; } };
      const ctx = app({ Date: D }), run = code => vm.runInContext(code, ctx);
      const next = run('nextPrayer({ Fajr: "05:50", Dhuhr: "12:30", Asr: "15:15", Maghrib: "17:40", Isha: "19:00" })');
      assert.deepEqual([next.key, next.time, next.mins], ['Maghrib', '17:40', 115], zone);
      assert.equal(run('shortDT("2026-11-27T00:00+04:00")'), '27 noy', zone + ': saatsız oyunun günü');
      assert.equal(run('shortDT("2026-11-27")'), '27 noy', zone);
    }
    process.env.TZ = 'Asia/Baku';
    assert.equal(vm.runInContext('shortDT("2026-11-27T17:30:00+04:00")', app()), '27 noy, 17:30', 'saatı olan oyun əvvəlki kimi');
  } finally { if (tz === undefined) delete process.env.TZ; else process.env.TZ = tz; }
});
test('Futbol tab is not emptied by a surname that contains «nba»; the converter keeps one precision', () => {
  const ctx = app(), run = code => vm.runInContext(code, ctx);
  const row = (title, summary = '') => ({ id: title, title, summary, source: 'Sports.kz', lang: 'ru' });
  ctx.a = row('Футбол: сборная вызвала новичка', 'Главный тренер Аманбаева рассказала о составе');
  ctx.b = row('Футбол и НБА: итоги недели');
  ctx.c = row('Donbass derbisində futbol oyunu təxirə salındı');
  assert.deepEqual(Array.from(run('[a, b, c].map(x => clubMatches(x, "Futbol"))')), [true, false, true]);
  const src = fs.readFileSync(path.join(root, 'assets/app.js'), 'utf8');
  assert.equal(src.split('S.fxTo === "BTC" ? 6 : 2').length - 1, 2, 'çeviricinin iki yeri eyni dəqiqliklə yazır (5 dəqiqəlik yeniləmədə BTC «0.00» olurdu)');
});
test('desktop nav hover reads the real /bolme/ links; a world-league group tab does not blank the local league', () => {
  const ctx = app(), run = code => vm.runInContext(code, ctx);
  ctx.link = href => ({ getAttribute: () => href });
  assert.equal(run('hashOf(link("/bolme/idman/"))'), '#/bolme/idman');
  assert.equal(run('hashOf(link("#/komanda/pl/arsenal"))'), '#/komanda/pl/arsenal');
  assert.equal(run('hashOf(null)'), undefined);
  const src = fs.readFileSync(path.join(root, 'assets/app.js'), 'utf8');
  assert.ok(src.includes('const h = hashOf(item);') && src.includes('const href = h?.match(/^#\\/bolme\\/(.+)$/)?.[1];'), 'mouseover /bolme/<ad>/ keçidini tanıyır');
  // qrup nişanı sətirdir ("1"): yerli liqaya qayıdanda «results» olmalıdır
  assert.ok(src.includes('|| S.fbTab >= 0 ? "results" : S.fbTab;') && !src.includes('typeof S.fbTab === "number"'));
  for (const [v, want] of [[0, true], ['1', true], ['results', false], ['table', false], [undefined, false]]) assert.equal(v >= 0, want, String(v));
});
test('search highlight marks the h2 headings and never matches inside an escaped entity', () => {
  const heads = [{ textContent: "O'zbekiston 39 & 39" }, { textContent: 'Başqa başlıq' }];
  const ctx = app(), run = code => vm.runInContext(code, ctx);
  ctx.asked = [];
  ctx.document.querySelectorAll = sel => { ctx.asked.push(sel); return heads; };
  run('route = () => ({ name: "search" }); S.hl = hlRegex(["39"]); highlightSearch();');
  assert.deepEqual(Array.from(ctx.asked), ['#view .card h2']);
  assert.equal(heads[0].innerHTML, 'O&#39;zbekiston <mark>39</mark> &amp; <mark>39</mark>');
  assert.equal(heads[1].innerHTML, undefined, 'uyğun gəlməyən başlığa toxunulmur');
  assert.ok(fs.readFileSync(path.join(root, 'assets/app.css'), 'utf8').includes('.card h2 mark{'));
});
test('a failed archive request is retried after a minute, not after thirty', async () => {
  const ctx = app(), { S, loadArchive } = ctx.api;
  let calls = 0;
  S.data = { articles: [] };
  ctx.fetch = async () => { calls++; throw new Error('şəbəkə'); };
  await loadArchive('tehsil');
  assert.equal(calls >= 1, true);
  const asked = calls, age = Date.now() - S.archive.tehsil.at;
  assert.ok(age > 28 * 60e3 && age < 30 * 60e3, 'bir dəqiqə sonra yenidən soruşula bilər');
  await loadArchive('tehsil');
  assert.equal(calls, asked, 'dərhal təkrar sorğu yoxdur (sectionView hər çəkilişdə çağırır)');
  S.archive.tehsil.at -= 61e3;
  ctx.fetch = async () => { calls++; return { ok: true, headers: new Headers(), json: async () => ({ articles: 'yox' }) }; };
  await loadArchive('tehsil');
  assert.ok(calls > asked && Date.now() - S.archive.tehsil.at > 28 * 60e3, 'zədəli cavab da uğursuzluq sayılır');
});
test('an old story link opened in a running tab is looked up on the arxiv branch', async () => {
  const id = 'abcdef0123456789', ctx = policyApp(), { S, scanArchives } = ctx.api, urls = [];
  const old = { id, title: 'Köhnə xəbər', category: 'gundem', lang: 'az', source: 'APA', sourceUrl: 'https://apa.az/kohne', publishedAt: '2026-10-01T10:00:00+00:00' };
  S.data = { articles: [] };
  ctx.fetch = async url => {
    urls.push(String(url));
    const json = String(url).includes('/arxiv/idx/ab.json') ? { [id]: '26100110' } : String(url).includes('/arxiv/saat/26100110.json') ? { articles: [old] } : String(url).includes('data/paylas/') ? { parts: 256, articles: [] } : { articles: [] };
    return { ok: true, headers: new Headers(), json: async () => json };
  };
  await scanArchives(id);
  assert.equal(S.sharedStory?.row?.sourceUrl, 'https://apa.az/kohne');
  assert.ok(urls.some(u => u.includes('raw.githubusercontent.com/8ulduz/8ulduz/arxiv/saat/26100110.json')));
  S.sharedStory = null; urls.length = 0;
  await scanArchives('on');
  assert.ok(!urls.some(u => u.includes('/arxiv/')), 'xəbər id-si olmayan ünvan üçün arxiv budağı soruşulmur');
});
test('service worker: a redirected shell response is never cached or handed to a navigation; the sample notification is not a story', () => {
  const sw = fs.readFileSync(path.join(root, 'sw.js'), 'utf8');
  assert.ok(sw.includes('if (saved?.redirected) saved = undefined;'), 'keşdəki yönləndirilmiş nüsxə işlədilmir');
  const at = sw.indexOf('if (fresh.redirected) return req.mode === "navigate" ? Response.redirect(fresh.url, 302) : fresh;');
  assert.ok(at > 0 && at < sw.indexOf('await cache.put(key, copy)'), 'yönləndirilmiş cavab keşə yazılmazdan əvvəl qaytarılır');
  assert.ok(sw.includes('const id = d.id === "on" ? "" : d.id;') && sw.includes('if (open && id) {'), 'nümunə bildiriş («on») id-siz bildiriş kimi baş səhifəni açır');
});

// 2026-11-13, sahibin qeydi: «sayta girəndə və içində açılışlar atılma ilə olur» (telefon, paylaşım keçidi). Brauzer ölçüsü dörd mənbə
// göstərdi: zolağa və valyuta sətrinə ayrılan yer real hündürlükdən az idi (telefonda 49 px, kompüterdə 17 px), slayd nöqtələri yaranıb
// silinirdi (12 px), qayıdışda «köhnəlib» sətri çıxıb itirdi (22 px), «Yeniləndi» yazısı sonradan çıxırdı (planşetdə 36 px).
test('no jump on open: the ticker and markets rows reserve their real height at every font size', () => {
  const css = fs.readFileSync(path.join(root, 'assets/app.css'), 'utf8').replace(/\/\*[\s\S]*?\*\//g, '');
  // qaydanın hansı @media içində olduğu: mötərizə dərinliyi ilə
  const where = rule => { const at = css.indexOf(rule); assert.ok(at >= 0, 'qayda yoxdur: ' + rule); let depth = 0, media = ''; for (let i = 0; i < at; i++) { if (css[i] === '{') { if (!depth) media = css.slice(css.lastIndexOf('\n', i) + 1, i).trim(); depth++; } else if (css[i] === '}') { depth--; if (!depth) media = ''; } } return depth ? media : ''; };
  assert.equal(where('#ticker:empty{min-height:calc(var(--lh-body) + 15px)}'), '', 'zolağın yeri bütün enlərdə ayrılır (əvvəl telefonda yalnız ≤340 px-də idi: 41 px atılma)');
  assert.equal(where('.markets.pending{height:calc(3*var(--lh-body) + 24px);visibility:hidden}'), '', 'valyuta sətri: üç sətirlik kart + kənarlar');
  assert.match(where('#ticker:empty{min-height:calc(var(--lh-body) + 17px)}'), /max-width:340px/, 'dar telefonda zolaq 2 px hündürdür');
  assert.match(where('.markets.pending{height:calc(var(--lh-body) + .9857rem + 14px)}'), /^@media/, 'telefon düzülüşündə kart iki sətirdir');
  assert.ok(!/\.markets\.pending\{height:\d+px/.test(css) && !/#ticker:empty\{min-height:\d+px/.test(css), 'sabit piksel yoxdur: yer şrift ölçüsü (A−/A+) ilə birgə dəyişir');
  // düsturun dayaqları: kartın ölçüləri dəyişsə düstur da dəyişməlidir (brauzer ölçüsü: 2026-11-13, 5 şrift × 10 en, fərq 0)
  for (const k of ['.ticker .run{flex:1;overflow:hidden;padding:7px 0;', '.ticker{display:flex;border-bottom:1px solid var(--border);', '.mk-grid{display:flex;flex-wrap:wrap;justify-content:center;gap:6px;max-width:920px;margin:0 auto;padding:6px 0}', '.mk-grid{padding:4px 0}', '.mk .v{font-size:.8571rem}', '.mk .v{padding-bottom:1px;line-height:1.15}'])
    assert.ok(css.includes(k), 'ayrılan yerin düsturu bu qaydaya söykənir, o dəyişibsə düsturu yenidən ölçün: ' + k);
  assert.equal(where('.hero-strip:not([data-pages]){padding-bottom:12px}'), '', 'slayd nöqtələrinin yeri (6 + 6 px) JS onları qoyana qədər ayrılır');
  assert.ok(css.includes('.st-dots{display:flex;justify-content:center;gap:5px;padding:6px 0 0}') && css.includes('.st-dots button{width:6px;height:6px;'), 'nöqtə sırası 12 px-dir');
  // telefonda naviqasiya JS-dən əvvəl də son düzülüşdədir: hazır HTML-də «Ana ekrana» düyməsi gizlidir (qabıq telefonu tanımır), JS onu ~0,4 s
  // sonra açanda «İdman» və «Bölgələr» yana atılırdı; ana ekrandan açılanda Gündəm və Dünya sonradan çıxırdı (brauzer ölçüsü: 330/360/412 px)
  assert.match(where('@media(hover:none) and (display-mode:browser){nav.main .nav-inst[hidden]{display:inline-flex!important}}'), /max-width:600px/, 'toxunma ekranında, brauzer vərəqində düymə JS-siz də görünür (app.js installBtn ilə eyni şərt)');
  assert.match(where('@media(display-mode:standalone){nav.main>a:is([href$="gundem/"],[href$="dunya/"]){display:flex;order:-1;flex:1 1 0;min-width:0;overflow:hidden}}'), /max-width:600px/, 'ana ekrandan açılanda Gündəm və Dünya JS-siz də yerindədir (.ph ilə eyni ölçü)');
  assert.ok(css.indexOf('nav.main .nav-inst[hidden]{display:inline-flex!important}') > css.indexOf('nav.main>a:not(.ph,.nav-tg){display:none}'), 'bu qaydalar gizlədən qaydalardan sonra gəlir');
  assert.ok(css.includes('[hidden]{display:none!important}'), 'ümumi [hidden] qaydası !important-dır: düymənin qaydası da elə olmalıdır');
  const appJs = fs.readFileSync(path.join(root, 'assets/app.js'), 'utf8');
  assert.ok(appJs.includes('const isPhone = () => isIOS() || matchMedia("(hover:none)").matches;') && appJs.includes('if (isStandalone() || (!S.installEvt && !isPhone())) return "";'), 'CSS şərti bu JS şərtinin əksidir: biri dəyişsə o biri də dəyişməlidir');
  // planşet (≥601 px, toxunma): «Ana ekrana əlavə et» düyməsi #inst-ə JS ilə düşür; yeri eyni ölçülü görünməz qutu ilə əvvəlcədən ayrılır
  // (brauzer ölçüsü: 601–1100 px × 3 şrift, başlıq JS-dən əvvəl və sonra eyni; əvvəl 5–36 px böyüyür, axtarış qutusu 173 px sola sürüşürdü)
  const instRule = '.inst:empty::before{content:"Ana ekrana əlavə et";visibility:hidden;min-height:28px;padding:0 12px;border:1px solid;font-size:.82rem;font-weight:700;white-space:nowrap}';
  assert.equal(where(instRule).replace(/\s/g, ''), '@media(min-width:601px)and(hover:none)and(display-mode:browser)', 'yer yalnız düymənin çıxacağı halda ayrılır (kompüterdə brauzer təklif verməyincə düymə yoxdur)');
  assert.ok(css.includes('.install-btn{min-height:30px;padding:0 12px;border:1px solid var(--border);') && css.includes('font:inherit;font-size:.82rem;font-weight:700;white-space:nowrap;cursor:pointer}'), 'görünməz qutu düymənin ölçülərini təkrarlayır (28 + 2 px kənar = 30): düymə dəyişsə o da dəyişməlidir');
  assert.ok(appJs.includes('return `<button type="button" class="install-btn" data-act="install">Ana ekrana əlavə et</button>`;'), 'yazı eynidir');
  assert.match(where('.inst:has(>.install-btn:only-child){display:none}'), /max-width:600px/, 'telefonda içində yalnız gizli düymə olan qutu yer tutmur («8ULDUZ-u izlə» 4 px sürüşürdü)');
  // namaz vaxtı gələndə düymə .pray-wrap içinə düşür: blok sarğı sətir hündürlüyü qədər (26,9 px) olurdu, düymə 25 px — bütün səhifə 2 px (A+ ilə 7 px) atılırdı
  assert.ok(css.includes('.pray-wrap{position:relative;display:flex}'), 'sarğı düymənin öz hündürlüyündədir');
  // paylaşılan keçid: skeletin üst boşluğu xəbərin özününkü ilə eynidir (14 px idi: xəbər gələndə #view 10 px aşağı düşürdü, CLS 0,31)
  const js = fs.readFileSync(path.join(root, 'assets/app.js'), 'utf8');
  assert.ok(css.includes('.article-detail{max-width:860px;margin:24px auto}') && js.includes('<div class="skel" style="height:30px;margin:24px 0 10px"></div>'), 'xəbər skeleti və xəbər eyni yerdən başlayır');
});
test('no jump inside: a patched slider keeps its arrows and dots; they are rebuilt only when the slide count changes', () => {
  const ctx = app();
  class El {
    constructor(cls, html, kids = []) { this.className = cls; this.outerHTML = html; this.children = kids; this.style = {}; this.scrollLeft = 0; this.offsetLeft = 0; this.offsetWidth = 100; this.isConnected = true; for (const k of kids) k.parent = this; }
    matches(sel) { return sel.split(',').some(s => this.className.split(' ').includes(s.trim().slice(1))); }
    get firstElementChild() { return this.children[0]; }
    get firstChild() { return this.children[0]; }
    remove() { const a = this.parent.children; a.splice(a.indexOf(this), 1); this.isConnected = false; }
    replaceWith(n) { const a = this.parent.children; a[a.indexOf(this)] = n; n.parent = this.parent; }
    insertBefore(n, ref) { if (n.parent) n.parent.children.splice(n.parent.children.indexOf(n), 1); const a = this.children, i = ref ? a.indexOf(ref) : a.length; a.splice(i, 0, n); n.parent = this; }
    querySelectorAll() { return []; }
  }
  const slide = n => new El('hero-main', `<article>${n}</article>`);
  const strip = (slides, extra = []) => new El('strip hero-strip', `<div class="strip hero-strip">${slides.map(s => s.outerHTML).join('')}</div>`, [new El('hero-row', '<div class="hero-row">' + slides.map(s => s.outerHTML).join('') + '</div>', slides), ...extra]);
  ctx.El = El; ctx.t = { slide, strip };
  const run = code => vm.runInContext(code, ctx);
  // 1) slaydlar eynidir, yalnız sarğının sətri fərqlidir (tam lent gələndə belə olurdu): oxlar və nöqtələr yerində qalır
  ctx.old = strip([slide(1), slide(2)], [new El('st-btn st-prev', ''), new El('st-btn st-next', ''), new El('st-dots', ''), new El('qalıq', '')]);
  run('rememberSrc(old); old.children[0]._src = "köhnə"; changed = []; patchChildren(old, [t.strip([t.slide(1), t.slide(2)]).children[0]], changed)');
  assert.deepEqual(ctx.old.children.map(n => n.className), ['hero-row', 'st-btn st-prev', 'st-btn st-next', 'st-dots'], 'oxlar və nöqtələr silinmir, başqa artıq düyün silinir');
  assert.equal(ctx.changed.length, 0, 'slayd sayı dəyişməyib: yenidən qurmağa ehtiyac yoxdur');
  // 2) bir slayd çıxıb, yenisi yoxdur: zolaq yenidən qurulmalıdır (nöqtə sayı)
  ctx.old = strip([slide(1), slide(2), slide(3)], [new El('st-dots', '')]);
  run('rememberSrc(old); old.children[0]._src = "köhnə"; changed = []; patchChildren(old, [t.strip([t.slide(1), t.slide(3)]).children[0]], changed)');
  assert.deepEqual(ctx.old.children[0].children.map(n => n.outerHTML), ['<article>1</article>', '<article>3</article>']);
  assert.ok(ctx.changed.includes(ctx.old.children[0]), 'say dəyişəndə sıra «dəyişən»lərə düşür: wire() zolağın nöqtələrini yenidən qurur');
  assert.equal(ctx.old.children[1].className, 'st-dots', 'nöqtələr yenidən qurulana qədər yerində qalır (altındakı məzmun oynamır)');
});
test('no jump on return: the «köhnəlib» line waits 20 s for the refresh, and the «Yeniləndi» slot exists before the time is known', () => {
  const els = {};
  const el = id => els[id] ||= { id, _html: '', set innerHTML(v) { this._html = v; }, get innerHTML() { return this._html; }, classList: { toggle() {}, add() {}, remove() {} }, dataset: {}, style: {} };
  const ctx = app({ document: { documentElement: { dataset: {} }, activeElement: null, addEventListener() {}, querySelector(s) { const m = s.match(/^#([\w-]+)$/); return m ? el(m[1]) : null; }, querySelectorAll() { return []; }, createElement() { return {}; } } });
  const src = fs.readFileSync(path.join(root, 'assets/app.js'), 'utf8');
  vm.runInContext(src.slice(src.indexOf('\nfunction renderTopbar() {'), src.indexOf('\nconst NAV_PRIMARY')), ctx);
  const { S } = ctx.api, draw = () => { vm.runInContext('renderTopbar()', ctx); return els.topbar.innerHTML; };
  let html = draw();
  assert.ok(html.includes('<span class="yenilendi" style="visibility:hidden">') && !html.includes('sync-state'), 'vaxt bilinmir: yazının yeri görünməz ayrılır (hazır HTML də belədir: prerender eyni funksiyanı işlədir)');
  S.status = { checkedAt: new Date(Date.now() - 60e3).toISOString(), ok: true };
  html = draw();
  assert.ok(html.includes('<span class="yenilendi"><span class="dot live"') && html.includes('Yeniləndi: 1 ') && !html.includes('köhnəlib'), 'təzə lent: yazı görünür');
  // vərəq 7 dəqiqə arxa planda qalıb: status təzədir, bu ekrana son məlumat 7 dəqiqə əvvəl çatıb
  S.latestAt = Date.now() - 7 * 60e3;
  S.lastResumeAt = Date.now() - 3e3;
  html = draw();
  assert.ok(!html.includes('köhnəlib') && !html.includes('sync-state'), 'qayıdışdan sonra yoxlama gedir: sətir çıxıb-itmir (bütün səhifə 22 px aşağı-yuxarı atılırdı)');
  S.lastResumeAt = Date.now() - 25e3;
  html = draw();
  assert.ok(html.includes('Xəbər lenti köhnəlib') && html.includes('class="retry" data-act="refresh"'), '20 saniyədən sonra hələ köhnədirsə xəbərdarlıq və «Yenilə» düyməsi çıxır');
  S.lastResumeAt = Date.now(); S.error = 'x';
  assert.ok(draw().includes('Xəbərlər yenilənmədi'), 'xəta gözləmir: dərhal yazılır');
});

// Sahib, 2026-11-14: «son xəbərlər və zuğulbada şəkillər yazılara uyğun hündürlükdə olurdu. indi standart ölçüdədir. düzəlt.»
// Şəklin hündürlüyü mətn sətirlərinə bağlıdır (3 sətir); eni də onunla böyüyür ki, eninə çəkilmiş şəkil yanlardan az kəsilsin.
test('phone list and Zuğulba pictures are as tall as three lines of text', () => {
  const css = fs.readFileSync(path.join(root, 'assets/app.css'), 'utf8');
  assert.ok(css.includes('grid-area:i;align-self:start;width:min(38vw,calc(4*var(--lh-body) + 40px));height:calc(3*var(--lh-body) + 30px);aspect-ratio:auto;border-radius:8px}'), 'siyahı şəkli');
  assert.ok(css.includes('.grid>*~.card:not(.noimg)>.img{align-self:stretch;width:auto;height:auto}'), 'bölmə siyahısında şəkil kartın boyundadır');
  assert.ok(css.includes('.prez-lent>.pcard.has-img:not(.noimg) .img{width:min(28vw,calc(3.5*var(--lh-body)));height:calc(3*var(--lh-body))}'), 'Zuğulba şəkli');
  assert.ok(css.includes('.prez-lent>.pcard .meta .src{max-width:100%;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}'), 'mənbə adı bir sətirdədir: kart daşmır');
  assert.ok(!css.includes('aspect-ratio:3/2;border-radius:8px'), 'sabit 3:2 qutu qalmayıb');
});
