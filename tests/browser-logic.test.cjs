const { test } = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const path = require('node:path');
const root = path.join(__dirname, '..');

function app(extra = {}) {
  const context = vm.createContext({
    console, Map, Set, URL, Date, AbortController, setTimeout, clearTimeout, addEventListener() {},
    localStorage: { getItem() { throw Error('blocked'); }, setItem() { throw Error('quota'); }, removeItem() { throw Error('blocked'); } },
    location: { hash: '#/' }, navigator: { onLine: true },
    window: { addEventListener() {} },
    document: { documentElement: { dataset: {} }, addEventListener() {}, querySelector() { return null; }, createElement() { return {}; } },
    matchMedia: () => ({ matches: false }), ...extra,
  });
  const source = fs.readFileSync(path.join(root, 'assets/app.js'), 'utf8').split(/\r?\napplyPrefs\(\);\r?\n/)[0];
  vm.runInContext(source, context);
  vm.runInContext(`render = () => {}; renderTopbar = () => {}; loadOg = async () => { S.og = {}; };
    checkBreaking = () => {}; globalThis.api = {safeHref, policyViolation, altForbidden, publishNews, savedView, latestBlock, homeView, storage, applyPrefs, route, loadNews, requestJSON, pollNews, resumeNews, freshUrl, isFresh, withinHour, footballBlock, S, heroPick, searchView, searchTopics, ratesView, leagueView, installBtn, trackEvent, savedLang, LANG_KEY, tidy, ordTur, fold, searchWords, hlRegex, orderedSocialPosts, socialBlock, isAppointment, prezHome, tickerLabel, card, altPop, catSection, articleView, languagePicker, imageCandidates, heroBlock, prezBlock, localRoadItems, trackedSources, sectionView, clubMatches, requestRender, readerBusy, withArchive, loadArchive, showBreaking};`, context);
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
  assert.ok(urls.filter(u=>!u.includes('/live/m/')).every(u=>u.includes('&r=')));
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
test('an update waits while the reader is busy: open video, open popup, typing, or scrolled down',()=>{
  const busy=(selector,extra={})=>{
    const ctx=app({document:{documentElement:{dataset:{}},addEventListener(){},createElement(){return {};},querySelector:s=>s.includes(selector)?{}:null,...extra},scrollY:0});
    let rendered=0;
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
  assert.ok(clubs<=32,'düymə sayı: '+clubs);
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
  const ctx=app(),{S,sectionView}=ctx.api;
  S.data={articles:[]};S.club=null;S.sportTab=null;
  const top=sectionView('idman');
  for(const name of ['Hamısı','Futbol','Basketbol','Formula 1','Tennis','Şahmat'])assert.ok(top.includes('>'+name+'<'),name);
  assert.ok(!top.includes('data-club="Qarabağ"'),'komandalar bağlıdır');
  S.club='Futbol';S.sportTab='Futbol';
  const foot=sectionView('idman');
  for(const name of ['Qarabağ','Galatasaray','Real Madrid'])assert.ok(foot.includes('data-club="'+name+'"'),name);
  assert.ok(!foot.includes('data-club="NBA"'));
  S.club='NBA';S.sportTab='Basketbol';
  const bb=sectionView('idman');
  assert.ok(bb.includes('data-club="Avroliqa"'));
  assert.ok(!bb.includes('data-club="Qarabağ"'));
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
  await showBreaking({id:'1',title:'Son xəbər',sourceUrl:'https://apa.az/1'});
  assert.equal(shown[0][0],'Son dəqiqə');
  assert.equal(shown[0][1].data.url,'https://apa.az/1');
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
  assert.ok(ids.includes('a') && ids.includes('d') && !ids.includes('b')); // AZƏRTAC və Cross Media var, Oxu.az yalnız «Hamısı»nda
  assert.deepEqual(ids, ['a', 'c', 'd']); // ən yenidən köhnəyə
  const html = ctx.api.prezBlock(ctx.api.prezHome(prez));
  assert.ok(html.includes('<a class="pcard has-img"') && html.includes('src="https://crossmedia.az/storage/news/a.jpeg"'));
  assert.ok(html.includes('<a class="pcard" data-cat="prezident"')); // şəkilsiz xəbər şəkil yeri tutmur
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
  const context = vm.createContext({URL, Request, Response, Headers, console, AbortController, setTimeout, clearTimeout,
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
  for (const file of ['status.json', 'latest.json', 'markets.json']) {
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
  const res = await vm.runInContext("networkFirstShell(new Request('https://example.com/8ulduz/assets/app.js'))", context);
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
  const pending = vm.runInContext("networkFirstShell(new Request('https://example.com/8ulduz/mexfilik/index.html'.replace('index.html','')))", context);
  await new Promise(r => setImmediate(r));
  answer(new Response('privacy page'));
  assert.equal(await (await pending).text(), 'privacy page');
});

test('new code wins over the cached copy when the network answers in time', async () => {
  const {context} = worker();
  context.fetch = async () => new Response('new code');
  context.caches.open = async () => ({match: async () => new Response('cached code'), put: async () => {}});
  const res = await vm.runInContext("networkFirstShell(new Request('https://example.com/8ulduz/assets/app.js'))", context);
  assert.equal(await res.text(), 'new code');
});

test('a hanging network does not leave a blank page when a copy is saved', async () => {
  const {context} = worker();
  context.fetch = () => new Promise(() => {});
  context.caches.open = async () => ({match: async () => new Response('cached code')});
  vm.runInContext('globalThis.setTimeout = (fn) => { fn(); return 0; };', context);
  const res = await vm.runInContext("networkFirstShell(new Request('https://example.com/8ulduz/assets/app.js'))", context);
  assert.equal(await res.text(), 'cached code');
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

test('home keeps slider stories after the sixth in the lists below', () => {
  const ctx=app(),{S,homeView}=ctx.api,at=new Date().toISOString();
  const words=['alma','armud','banan','qovun','heyva','nar','gilas','albali','erik','saftali','limon','portagal','anar','zeytun','incir','xurma','zoğal','böyürtkən'];
  S.lang=null;S.og={};S.latestCount=30;S.data={articles:words.map((w,i)=>({id:String(i),title:w+'lər '+w+'ları '+i,category:'gundem',lang:'az',source:'APA',sourceUrl:'https://apa.az/'+i,publishedAt:at}))};
  const page=homeView(),below=page.slice(page.indexOf('latest-grid'));
  assert.equal((page.match(/class="hero-main"/g)||[]).length,15);
  const slides=[...new Set([...page.slice(0,page.indexOf('latest-grid')).matchAll(/apa\.az\/(\d+)/g)].map(m=>m[1]))];
  assert.equal(slides.length,15);
  assert.ok(!below.includes('apa.az/'+slides[0]+'"'),'ilk xəbər aşağıda təkrarlanmır');
  assert.ok(below.includes('apa.az/'+slides[10]+'"'),'11-ci xəbər aşağıda da qalır');
});
test('cards can be shared, except stories with an unsafe link', () => {
  const ctx=app(),{card}=ctx.api,at=new Date().toISOString();
  ctx.api.S.og={};
  const row=url=>({id:'1',title:'Xəbər',lang:'az',category:'gundem',source:'APA',sourceUrl:url,publishedAt:at});
  assert.ok(card(row('https://apa.az/1')).includes('data-share="https://apa.az/1"'));
  assert.ok(!card(row('javascript:alert(1)')).includes('data-share'));
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
test('the install button appears only when installing is possible', () => {
  const ctx=app(),{S,installBtn}=ctx.api;
  assert.equal(installBtn(),'');
  S.installEvt={};
  assert.ok(installBtn().includes('data-act="install"'));
  const iphone=app({navigator:{onLine:true,userAgent:'iPhone'}});
  assert.ok(iphone.api.installBtn().includes('data-act="install"'));
  const home=app({navigator:{onLine:true,userAgent:'iPhone',standalone:true}});
  assert.equal(home.api.installBtn(),'');
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
  const ctx=app(); const stories=Array.from({length:18},(_,i)=>({id:String(i),title:'News '+i,category:'gundem',source:'Source',sourceUrl:'https://example.com/'+i,publishedAt:new Date().toISOString()}));
  const hero=ctx.api.heroBlock(stories),prez=ctx.api.prezBlock(stories.slice(0,8));
  assert.ok(hero.includes('class="hero-row"'));
  assert.equal((hero.match(/class="hero-main"/g)||[]).length,15);
  assert.ok(!hero.includes('row-card'),'slayderin xəbərləri altında təkrarlanmır');
  assert.ok(prez.includes('data-prez-lent'));
  assert.equal((prez.match(/class="pcard"/g)||[]).length,8);
});
