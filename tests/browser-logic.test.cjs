const { test } = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const path = require('node:path');
const root = path.join(__dirname, '..');

function app() {
  const context = vm.createContext({
    console, Map, Set, URL, Date, setTimeout, clearTimeout, addEventListener() {},
    localStorage: { getItem() { throw Error('blocked'); }, setItem() { throw Error('quota'); }, removeItem() { throw Error('blocked'); } },
    location: { hash: '#/' }, navigator: { onLine: true },
    window: { addEventListener() {} },
    document: { documentElement: { dataset: {} }, addEventListener() {}, querySelector() { return null; }, createElement() { return {}; } },
    matchMedia: () => ({ matches: false }),
  });
  const source = fs.readFileSync(path.join(root, 'assets/app.js'), 'utf8').split(/\r?\napplyPrefs\(\);\r?\n/)[0];
  vm.runInContext(source, context);
  vm.runInContext(`render = () => {}; renderTopbar = () => {}; loadOg = async () => { S.og = {}; };
    checkBreaking = () => {}; globalThis.api = {storage, applyPrefs, route, loadNews, isFresh, withinHour, footballBlock, S, heroPick, savedLang, LANG_KEY, tidy, ordTur, fold, searchWords, hlRegex, orderedSocialPosts, socialBlock, frontAppointments, isAppointment, prezHome, tickerLabel, card, altPop, catSection, articleView, languagePicker, imageCandidates, heroBlock, prezBlock, localRoadItems, trackedSources};`, context);
  return context;
}

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

test('broken percent-encoded route does not break the page', () => {
  const ctx = app();
  ctx.location.hash = '#/axtar?q=100%';
  assert.equal(ctx.api.route().q, '100%');
  ctx.location.hash = '#/axtar?q=%C4%B0lham';
  assert.equal(ctx.api.route().q, 'İlham');
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

test('world leagues from ESPN appear after the Azerbaijani ones with their own tables', () => {
  const ctx = app();
  ctx.api.S.football = { leagues: [{ project: 1, short: 'Premyer Liqa', league: 'Misli Premyer Liqası', table: [{ pos: 1, team: 'Sabah', pts: 20, p: 9, w: 6, d: 2, l: 1, gf: 15, ga: 7, gd: 8 }], results: [], fixtures: [] }] };
  ctx.api.S.sports = { leagues: [
    { id: 'eng.1', sport: 'football', name: 'Premyer Liqa (İngiltərə)', short: 'İngiltərə', season: '2026-27', groups: [{ name: 'Premier League', rows: [{ pos: 1, team: 'Man City', full: 'Manchester City', logo: '', p: 8, w: 7, d: 0, l: 1, gf: 20, ga: 9, gd: 11, pts: 21, note: 'Champions League', color: '#81D6AC' }] }] },
    { id: 'nba', sport: 'basketball', name: 'NBA', short: 'NBA', season: '2026-27', groups: [{ name: 'Eastern Conference', rows: [{ pos: 1, team: 'Celtics', w: 4, l: 0, p: 4, pct: 1, gb: '-' }] }, { name: 'Western Conference', rows: [{ pos: 1, team: 'Lakers', w: 3, l: 1, p: 4, pct: 0.75, gb: '-' }] }] },
  ] };
  let html = ctx.api.footballBlock([]);
  assert.ok(html.includes('data-fbleague="2"') && html.includes('İngiltərə') && html.includes('NBA'));
  ctx.api.S.fbLeague = 1; ctx.api.S.fbTab = 0;
  html = ctx.api.footballBlock([]);
  assert.ok(html.includes('Man City') && html.includes('ESPN') && html.includes('<h2>Futbol</h2>'));
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
});

test('appointment and dismissal news come first; Zuğulba includes state sites with thumbnails', () => {
  const ctx = app();
  const now = Date.now();
  const at = h => new Date(now - h * 3600e3).toISOString();
  assert.ok(ctx.api.isAppointment({ title: 'Yeni icra başçısı təyin edilib' }));
  assert.ok(ctx.api.isAppointment({ title: 'Nazir vəzifəsindən azad olunub' }));
  assert.ok(!ctx.api.isAppointment({ title: 'Girov azad edilib' }));
  const list = [
    { id: 1, title: 'Hava proqnozu', publishedAt: at(1) },
    { id: 2, title: 'Rektor vəzifəsindən azad edilib', publishedAt: at(5) },
    { id: 3, title: 'Səfir təyin olunub', publishedAt: at(50) }, // 36 saatdan köhnə: adi sırada
  ];
  assert.deepEqual([...ctx.api.frontAppointments(list).map(a => a.id)], [2, 1, 3]);
  const prez = [
    { id: 'a', category: 'prezident', source: 'AZƏRTAC', title: 'Prezident İlham Əliyev təbrik edib', publishedAt: at(2) },
    { id: 'b', category: 'prezident', source: 'Oxu.az', title: 'Prezident qəbul edib', publishedAt: at(1) },
    { id: 'd', category: 'prezident', source: 'Cross Media', title: 'Prezident İlham Əliyev fərman imzalayıb', publishedAt: at(4), imageUrl: 'https://crossmedia.az/storage/news/a.jpeg' },
    { id: 'c', category: 'prezident', source: 'Prezident.az', title: 'İlham Əliyev sərəncam imzalayıb: yeni rəis təyin edilib', publishedAt: at(3) },
  ];
  const ids = [...ctx.api.prezHome(prez).map(a => a.id)];
  assert.ok(ids.includes('a') && ids.includes('d') && !ids.includes('b')); // AZƏRTAC və Cross Media var, Oxu.az yalnız «Hamısı»nda
  assert.equal(ids[0], 'c'); // təyinat önə
  const html = ctx.api.prezBlock(ctx.api.prezHome(prez));
  assert.ok(html.includes('<a class="pcard has-img"') && html.includes('src="https://crossmedia.az/storage/news/a.jpeg"'));
  assert.ok(html.includes('<a class="pcard" data-cat="prezident"')); // şəkilsiz xəbər şəkil yeri tutmur
});

test('one state site cannot fill the Zuğulba block: at most 3 cards per non-official source', () => {
  const ctx = app();
  const at = h => new Date(Date.now() - h * 3600e3).toISOString();
  const prez = [1, 2, 3, 4, 5].map(i => ({ id: 'r' + i, category: 'prezident', source: 'Report', title: 'İlham Əliyev: sitat ' + i, publishedAt: at(i) }));
  prez.push({ id: 'o', category: 'prezident', source: 'Prezident.az', title: 'İlham Əliyev səfiri qəbul edib', publishedAt: at(9) });
  prez.push({ id: 'x', category: 'prezident', source: 'Cross Media', title: 'Prezident İlham Əliyev fərman imzalayıb', publishedAt: at(10) });
  const ids = [...ctx.api.prezHome(prez).map(a => a.id)];
  assert.deepEqual(ids.filter(i => i.startsWith('r')), ['r1', 'r2', 'r3']); // ən yeni 3 Report
  assert.ok(ids.includes('o') && ids.includes('x'));
});

test('raw links are stripped from headlines', () => {
  const ctx = app();
  assert.equal(ctx.api.tidy('Harri Keyn mükafat qazanıb https://report.az/futbol/abc'), 'Harri Keyn mükafat qazanıb');
});

function worker(cacheNames = []) {
  const listeners = {}, deleted = [];
  const context = vm.createContext({URL, Request, Response, Headers, console,
    self: {location: new URL('https://example.com/8ulduz/sw.js'), addEventListener: (name, fn) => listeners[name] = fn,
      clients: {claim: async () => {}}, registration: {}},
    caches: {keys: async () => cacheNames, delete: async key => deleted.push(key),
      open: async () => ({match: async () => null})},
    fetch: async () => { throw Error('offline'); },
  });
  vm.runInContext(fs.readFileSync(path.join(root, 'sw.js'), 'utf8'), context);
  return {context, listeners, deleted};
}

test('service worker retains caches belonging to other sites', async () => {
  const {listeners, deleted} = worker(['other-app-v1', '8ulduz-static-v15', '8ulduz-data-v15', '8ulduz-static-v19']);
  let done;
  listeners.activate({waitUntil(p) { done = p; }});
  await done;
  assert.deepEqual(deleted.sort(), ['8ulduz-data-v15', '8ulduz-static-v15']);
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
  context.caches.open = async () => ({put: async (_key, response) => { stored = await response.text(); }});
  const res = await vm.runInContext("networkFirstShell(new Request('https://example.com/8ulduz/assets/app.js'))", context);
  assert.equal(await res.text(), 'new code');
  assert.equal(stored, 'new code');
});

test('application code is still available offline', async () => {
  const {context} = worker();
  context.caches.open = async () => ({match: async () => new Response('cached code')});
  const res = await vm.runInContext("networkFirstShell(new Request('https://example.com/8ulduz/assets/app.js'))", context);
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
  assert.ok(ctx.api.articleView('missing').includes('artıq lentdə yoxdur'));
});


test('photo fallback tries OG and alternate source photos in order', () => {
  const ctx=app(); ctx.api.S.og={'https://one.example':'https://img.example/og.jpg','https://two.example':'https://img.example/alt-og.jpg'};
  const images=ctx.api.imageCandidates({imageUrl:'https://img.example/rss.jpg',sourceUrl:'https://one.example',alts:[{imageUrl:'https://img.example/alt.jpg',sourceUrl:'https://two.example'}]});
  assert.deepEqual(Array.from(images),['https://img.example/rss.jpg','https://img.example/og.jpg','https://img.example/alt.jpg','https://img.example/alt-og.jpg']);
});

test('hero and Zugulba retain multiple articles for their moving feeds', () => {
  const ctx=app(); const stories=Array.from({length:8},(_,i)=>({id:String(i),title:'News '+i,category:'gundem',source:'Source',sourceUrl:'https://example.com/'+i,publishedAt:new Date().toISOString()}));
  const hero=ctx.api.heroBlock(stories),prez=ctx.api.prezBlock(stories);
  assert.ok(hero.includes('class="hero-row"'));
  assert.equal((hero.match(/class="hero-main"/g)||[]).length,6);
  assert.ok(prez.includes('data-prez-lent'));
  assert.equal((prez.match(/class="pcard"/g)||[]).length,8);
});
