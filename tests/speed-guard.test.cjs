// Sürət qoruyucuları (sahib 2026-11-06: «gözqırpımı sürət … eyni problem bir daha təkrarlanmasın»).
// Hər test gecə ölçülən (.github/scripts/speed.cjs, telefon, 4× yavaş prosessor) bir səbəbi bağlayır; rəqəmlər docs/qirmizi-xetler.md-də.
const { test } = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const path = require('node:path');
const root = path.join(__dirname, '..');
const APP = fs.readFileSync(path.join(root, 'assets/app.js'), 'utf8').replace(/\r\n/g, '\n');
const KOMANDA = fs.readFileSync(path.join(root, 'assets/komanda.js'), 'utf8').replace(/\r\n/g, '\n');

function app(extra = {}) {
  const context = vm.createContext({
    console, Map, Set, URL, Date, AbortController, setTimeout, clearTimeout, addEventListener() {},
    localStorage: { getItem() { return null; }, setItem() {}, removeItem() {} },
    location: { hash: '#/' }, navigator: { onLine: true },
    window: { addEventListener() {} },
    document: { documentElement: { dataset: {} }, addEventListener() {}, querySelector() { return null; }, querySelectorAll() { return []; }, createElement() { return {}; } },
    matchMedia: () => ({ matches: false }), ...extra,
  });
  vm.runInContext(APP.split(/\napplyPrefs\(\);\n/)[0], context);
  vm.runInContext('render = () => {}; renderTopbar = () => {};', context);
  return context;
}
const phone = () => app({ matchMedia: q => ({ matches: String(q).includes('hover:none') }) });
const at = new Date().toISOString();
const story = (i, extra = {}) => ({ id: 'id' + i, title: 'Xəbər başlığı ' + i, category: 'gundem', lang: 'az', source: 'APA', sourceUrl: 'https://apa.az/' + i, publishedAt: at, ...extra });

test('speed: on a phone a list page starts with 6 cards, the other 42 fill in idle time', () => {
  const ctx = phone();
  vm.runInContext('S.shown = 48; S.og = {};', ctx);
  ctx.list = Array.from({ length: 48 }, (_, i) => story(i));
  const html = vm.runInContext('listPage("Gündəm", "", list)', ctx);
  // 2026-11-09: qalan kartların HTML-i səhifə sətrində deyil, yaddaşdadır (LATE_HTML); sətirdə yalnız açarlı boş şablon qalır
  const [now, mark = ''] = html.split('<template data-late="');
  const key = mark.split('"')[0], later = key ? vm.runInContext(`LATE_HTML.get(${JSON.stringify(key)})`, ctx) : '';
  assert.ok(key && mark.startsWith(key + '"></template>'), 'şablon boşdur: patchView 42 kartı təhlil etmir, rememberSrc seriallaşdırmır');
  assert.equal((now.match(/apa\.az\/\d+/g) || []).length > 0, true);
  assert.equal(new Set(now.match(/apa\.az\/\d+"/g)).size, 6, 'ilk çəkilişdə 6 kart (telefon ekranında 2–3 görünür)');
  assert.equal(new Set((later || '').match(/apa\.az\/\d+"/g)).size, 42, 'qalanı yaddaşda: brauzer yerləşdirmir, təhlil etmir');
  assert.equal(new Set(html.match(/apa\.az\/\d+"/g)).size, 6, '42 kart səhifə sətrində yoxdur');
  const desk = app();
  vm.runInContext('S.shown = 48; S.og = {};', desk);
  desk.list = ctx.list;
  assert.ok(!vm.runInContext('listPage("Gündəm", "", list)', desk).includes('data-late'), 'kompüterdə hamısı birdən');
});

test('speed: idle fill is remembered per page and sub-tab, not once for the whole visit', () => {
  const ctx = phone();
  ctx.location.hash = '#/bolme/idman';
  const a = vm.runInContext('lateKey()', ctx);
  vm.runInContext('S.club = "Futbol"', ctx);
  const b = vm.runInContext('lateKey()', ctx);
  ctx.location.hash = '#/bolme/gundem'; vm.runInContext('S.club = null', ctx);
  const c = vm.runInContext('lateKey()', ctx);
  assert.equal(new Set([a, b, c]).size, 3);
  assert.ok(APP.includes('S.lateDone = lateKey();') && APP.includes('if (S.lateDone === lateKey())'), 'yalnız həmin səhifə dolubsa sonrakı çəkiliş tam gəlir');
});

test('speed: rendering does not force layout: nav, footer and the busy check read nothing from the page', () => {
  assert.ok(/function render\(\) \{ clearTimeout\(S\.renderTimer\); S\.renderQueued = false;/.test(APP), 'birbaşa çəkiliş növbədəkini ləğv edir (əvvəlki səhifənin arxiv çəkilişi yeni səhifəni ikinci dəfə çəkirdi)');
  assert.ok(APP.includes('if (h === S.navH) return;'), 'dəyişməyən menyu yenidən yazılmır və ölçülmür (fitNav ilk açılışda 0,8 s idi)');
  assert.ok(APP.includes('if (h !== S.footH) S.footH = $("#footer").innerHTML = h;'), 'altlıq da');
  const busy = APP.slice(APP.indexOf('function readerBusy()'), APP.indexOf('function armBusy'));
  assert.ok(busy.includes('(S.sy ??= globalThis.scrollY || 0) > 400') && busy.split('scrollY').length === 2, 'scrollY hər dəfə oxunmur (məcburi yerləşdirmə), yalnız ilk dəfə');
  assert.ok(APP.includes('window.addEventListener("scroll", () => { S.sy = scrollY;'), 'mövqe sürüşmə hadisəsindən');
});

test('speed: search and Regions merge the feed with 14 archives once, until something changes', () => {
  const ctx = app();
  vm.runInContext('S.data = { articles: [] }; S.archive = {};', ctx);
  ctx.rows = [story(1)];
  vm.runInContext('S.data = { articles: rows }; S.archive = { gundem: { at: Date.now(), rows: [{ ...rows[0], id: "x", title: "Arxivdə başqa müstəqil hadisə", sourceUrl: "https://apa.az/x" }] } };', ctx);
  const one = vm.runInContext('allNews()', ctx), two = vm.runInContext('allNews()', ctx);
  assert.equal(one, two, 'eyni siyahı, yenidən yığılmır');
  assert.equal(one.length, 2);
  vm.runInContext('S.arxV = (S.arxV || 0) + 1', ctx);
  assert.notEqual(vm.runInContext('allNews()', ctx), one, 'arxiv gələndə yenidən');
  vm.runInContext('S.data = { articles: [] }', ctx);
  assert.equal(vm.runInContext('allNews()', ctx).length, 1, 'lent dəyişəndə yenidən');
  assert.ok(APP.includes('S.archive[slug].rows = d.articles.filter(a => !removedSource(a) && !policyViolation(a)).map(a => ({...a, alts: (a.alts || []).filter(alt => !altForbidden(a, alt))})); S.arxV = (S.arxV || 0) + 1;'));
  assert.ok(APP.includes('for (const a of allNews()) {') && APP.includes('list = byDate(allNews().filter('), 'axtarış və Bölgələr eyni birləşməni işlədir');
});

test('speed: a sport word in search checks clubs only on sport stories', () => {
  assert.ok(APP.includes('if (a.category === "idman" && topics.some(name => clubMatches(a, name)))'), '«futbol» axtarışı 5000 xəbəri 20 klubla yoxlayırdı (1,7 s)');
});

test('speed: fold skips Unicode normalisation when nothing is left to strip, with the same result', () => {
  const ctx = app();
  const fold = vm.runInContext('fold', ctx);
  const FOLD = { 'ə': 'e', 'ı': 'i', 'ö': 'o', 'ü': 'u', 'ğ': 'g', 'ş': 's', 'ç': 'c' };
  const old = s => String(s || '').toLowerCase().normalize('NFD').replace(/[̀-ͯ]/g, '').replace(/[əıöüğşç]/g, ch => FOLD[ch]);
  for (const s of ['İLHAM ƏLİYEV', 'Fənərbağça məğlub oldu', 'Ёлка и йогурт', 'São Paulo', 'Ñandú', 'ŞÜŞA', 'Qarabağ — Neftçi 2:1', '', null])
    assert.equal(fold(s), old(s), String(s));
});

test('speed: club logos always come through the image proxy, small (pfl.az originals were 70 KB – 2.2 MB each)', () => {
  const ctx = app();
  const sized = vm.runInContext('sized', ctx);
  vm.runInContext('S.proxyFails = 99', ctx);
  assert.ok(sized('https://pfl.az/storage/clubs/a.PNG', 96, 1).startsWith('https://wsrv.nl/?url='), 'loqo proksidən hətta proksi xətalarından sonra da');
  assert.equal(sized('https://apa.az/a.jpg', 480), 'https://apa.az/a.jpg', 'adi şəkil üçün köhnə qayda qalır');
  assert.ok(!APP.includes('<img src="${esc(t.logo)}"'), 'liqa və cədvəl loqoları proksisiz deyil');
  assert.ok(KOMANDA.includes('sized(url, size * 2, 1)'), 'komanda səhifəsinin loqoları da');
});

test('speed: every remote image in the page code goes through the proxy, except the known small ones', () => {
  const allowed = new Set(['${ASSET}', '${esc(s.image)}', '${esc(v.imageUrl)}']); // öz faylımız, reklam, YouTube önizləməsi (CDN, kiçik)
  for (const [name, code] of [['app.js', APP], ['komanda.js', KOMANDA]]) {
    for (const m of code.matchAll(/<img src="(\$\{[^}]*\}(?:\))?)/g)) {
      const expr = m[1];
      assert.ok(expr.includes('sized(') || allowed.has(expr) || /^\$\{ASSET\}/.test(expr), `${name}: ${expr} proksisiz şəkil`);
    }
  }
});

test('speed: the proxy is blamed only when the original image then loads', () => {
  const fail = APP.slice(APP.indexOf('const imgFail = el =>'), APP.indexOf('const imgFail = el =>') + 1200);
  assert.ok(fail.includes('el.addEventListener("load", () => { if (el.src.startsWith("https://wsrv.nl/")) return; S.proxyFails = (S.proxyFails || 0) + 1;'), 'mənbədə silinmiş şəkil bütün saytı ağır orijinallara keçirmir');
  assert.ok(!/startsWith\("https:\/\/wsrv\.nl\/"\)\) \{[^\n]*\n\s*S\.proxyFails = \(S\.proxyFails \|\| 0\) \+ 1;/.test(fail), 'xəta anında cəza yoxdur');
});

test('speed: address parsing in the policy check is a cheap pattern, not new URL() per story', () => {
  const ctx = app();
  const hostOf = vm.runInContext('hostOf', ctx), removedSource = vm.runInContext('removedSource', ctx);
  assert.equal(hostOf('https://www.APA.az/news/1?x=1#y'), 'apa.az');
  assert.equal(hostOf('https://user:pw@sub.example.com:8080/a'), 'sub.example.com');
  assert.equal(hostOf('not a url'), '');
  assert.equal(removedSource({ sourceUrl: 'https://www.azadliq.org/a' }), true, 'qırmızı xətt 2 qalır');
  assert.equal(removedSource({ sourceUrl: 'https://apa.az/a' }), false);
  const body = APP.slice(APP.indexOf('function removedSource'), APP.indexOf('function removedSource') + 400);
  assert.ok(!body.includes('new URL('));
});

test('speed: the measuring tool emulates a phone (touch media, 4× slower CPU) and checks budgets', () => {
  const tool = fs.readFileSync(path.join(root, '.github/scripts/speed.cjs'), 'utf8');
  assert.ok(tool.includes('{ name: "hover", value: "none" }') && tool.includes('Emulation.setCPUThrottlingRate'), 'telefon yolu (gec doldurma) ölçülür');
  assert.ok(tool.includes('--budget') && tool.includes('LIMITS'), 'büdcəni keçəndə çıxış kodu 1');
});

test('speed 2026-11-09: the first slide picture is 640 px on every screen, so the prerendered image is not fetched again at 800 on a computer', () => {
  const list = [story(1, { imageUrl: 'https://apa.az/1.jpg' }), story(2, { imageUrl: 'https://apa.az/2.jpg' })];
  const desk = app(), phone = app({ innerWidth: 390 });
  desk.list = list; phone.list = list;
  const [d1, d2] = vm.runInContext('heroBlock(list)', desk).match(/<img [^>]*>/g), [p1, p2] = vm.runInContext('heroBlock(list)', phone).match(/<img [^>]*>/g);
  assert.equal(d1, p1, 'ilk slaydın şəkil teqi kompüterdə və telefonda eynidir (hazır HTML-dəki ilə də)');
  assert.ok(/w=640&amp;we/.test(d1) && /fetchpriority="high"/.test(d1), 'ilk şəkil 640, yüksək prioritet');
  assert.ok(/w=640&amp;we/.test(d2) && /w=480&amp;we/.test(p2), 'növbəti slaydlar: kompüterdə 640, telefonda 480');
  assert.equal(vm.runInContext('heroPicWidth(true)', desk), 640, 'primeHeroImage də eyni ünvanı əvvəlcədən yükləyir');
});

test('speed: the early-fetch script in index.html is allowed by its CSP hash (a stale hash silently blocks it: no early files, the home page flashes on deep links)', () => {
  const crypto = require('node:crypto');
  const html = fs.readFileSync(path.join(root, 'index.html'), 'utf8').replace(/\r\n/g, '\n'); // GitHub Pages LF verir
  const body = html.match(/<script>([\s\S]*?)<\/script>/)[1];
  const hash = 'sha256-' + crypto.createHash('sha256').update(body).digest('base64');
  assert.ok(html.match(/script-src[^;"]*/)[0].includes(`'${hash}'`), `CSP-də ${hash} olmalıdır`);
  assert.ok(body.includes('dataset.route = home ? "home" : "other"'), 'birbaşa keçiddə ana səhifənin hazır HTML-i gizlənir');
  assert.ok(body.includes('sec ? ["data/first.json"].concat(full)'), 'bölmə keçidi əvvəlcə ilk lenti istəyir (app.js partialOk ilə eyni)');
  assert.ok(body.includes('team ? ["data/futbol/index.json", "data/futbol/" + team[1] + ".json"].concat(full)') && body.includes('"komanda.js", "modulepreload"'), 'liqa/komanda keçidi öz fayllarını tam lentdən əvvəl istəyir');
});

test('speed: the service worker precaches only first-visit files (sahib v107; 2026-11-09: icons and og-default removed) and names the data cache without a version', () => {
  const SW = fs.readFileSync(path.join(root, 'sw.js'), 'utf8');
  const pre = SW.match(/cache\.addAll\(\[([^\]]*)\]/)[1].match(/"\.\/[^"]*"/g).map(s => JSON.parse(s));
  assert.deepEqual(pre, ['./', './assets/app.css', './assets/app.min.js', './assets/config.js', './assets/content-policy.js', './manifest.webmanifest', './assets/logo-80.png', './assets/icon-192.png'],
    'ilkin keş siyahısı dəyişib: hər fayl hər versiyada yenidən yoxlanır — yalnız ilk açılışın faylları (ikonlar və og şəkli işçidən oxunmur)');
  assert.ok(SW.includes('const DATA = "8ulduz-data";'), 'məlumat keşi versiyasız: yayımdan sonra lent keşdə qalır (gündə 20–40 yayım var)');
  assert.ok(!SW.includes('cache.match("./index.html")'), 'oflayn qabıq ./ açarından (index.html ilkin keşdə deyil)');
});

// publishNews yaddaşı (2026-11-09): dəqiqəlik lent hər dəfə ~1 100 sətri yenidən klonlayıb qaydadan keçirirdi. Çıxış köhnə boru xətti ilə
// bayt-bayt eyni olmalıdır — REF köhnə publishNews-un hazırlıq hissəsidir (yaddaşsız), hər halda yenidən hesablanır.
const REF = `(() => { let articles = S.rawNews.map(a => ({...a, category: SECTION_ALIAS[a.category] || a.category, imageUrl: a.imageUrl || S.og?.[a.sourceUrl] || a.imageUrl}));
  articles = articles.filter(a => !removedSource(a) && !policyViolation(a)).map(a => ({...a, alts: (a.alts || []).filter(alt => !altForbidden(a, alt))}));
  if (S.deadLinks?.size) articles = articles.flatMap(a => { const alts = a.alts.filter(alt => !S.deadLinks.has(alt.sourceUrl)); if (!S.deadLinks.has(a.sourceUrl)) return [{...a, alts}]; if (!alts.length) return []; const [next, ...rest] = alts; return [{...a, source: next.source, sourceUrl: next.sourceUrl, publishedAt: next.publishedAt || a.publishedAt, title: next.title || a.title, lang: next.lang || a.lang, imageUrl: a.imageUrl || next.imageUrl, alts: rest}]; });
  const rows = collapseExact(clusterArticles(articles));
  for (const a of rows) { if (a.imageUrl || !a.alts?.length) continue; const alt = a.alts.find(x => x.imageUrl) || a.alts.find(x => S.og?.[x.sourceUrl]); if (alt) a.imageUrl = alt.imageUrl || S.og?.[alt.sourceUrl]; }
  return JSON.stringify(rows); })()`;
function policyApp() {
  const els = {};
  const el = id => els[id] ||= { id, _html: '', set innerHTML(v) { this._html = v; }, get innerHTML() { return this._html; }, addEventListener() {}, classList: { toggle() {}, add() {}, remove() {}, contains() { return false; } }, querySelector() { return null; }, querySelectorAll() { return []; }, focus() {}, dataset: {}, style: {}, hidden: false, textContent: '' };
  const ctx = vm.createContext({
    console: { ...console, log() {}, warn() {}, info() {} }, Map, Set, URL, Date, AbortController, setTimeout, clearTimeout, performance, TextEncoder, btoa, innerWidth: 390,
    addEventListener() {}, localStorage: { getItem() { return null; }, setItem() {}, removeItem() {} },
    location: { hash: '#/', href: 'https://8ulduz.az/' }, navigator: { onLine: true }, history: { replaceState() {} },
    document: { documentElement: { dataset: {}, style: {} }, hidden: false, activeElement: null, title: '', addEventListener() {}, querySelector(s) { const m = s.match(/^#([\w-]+)$/); return m ? el(m[1]) : null; }, querySelectorAll() { return []; },
      createElement() { return { _v: '', set innerHTML(v) { this._v = String(v); }, get innerHTML() { return this._v; }, get value() { return this._v; }, content: {}, children: [] }; } },
    matchMedia: () => ({ matches: false }), requestAnimationFrame: () => 0,
  });
  ctx.window = ctx;
  vm.runInContext(fs.readFileSync(path.join(root, 'assets/content-policy.js'), 'utf8'), ctx);
  vm.runInContext(APP.split('\napplyPrefs();\n')[0], ctx);
  vm.runInContext('render = () => {}; renderTopbar = () => {}; renderView = () => {}; renderTicker = () => {}; checkBreaking = () => {}; primeHeroImage = () => {}; requestRender = () => {}; loadArchive = async () => {}; loadOg = async () => {};', ctx);
  return ctx;
}
function feed(rows, og) {
  const ctx = policyApp(); ctx.__rows = rows; ctx.__og = og;
  vm.runInContext('S.og = __og; S.rawNews = __rows; S.rawMeta = { updatedAt: "x", count: __rows.length }; S.partial = false; S.lang = "az";', ctx);
  return ctx;
}
const run = (ctx, code) => vm.runInContext(code, ctx);
const same = (ctx, label) => { run(ctx, 'publishNews()'); const got = run(ctx, 'JSON.stringify(S.data.articles)'); assert.equal(got, run(ctx, REF), label + ': publishNews köhnə boru xətti ilə bayt-bayt eyni deyil'); return got; };
const latest = (ctx, d) => { ctx.__d = d; run(ctx, 'latestJSON = async () => ({ r: { headers: { get: () => null } }, d: __d })'); return run(ctx, 'loadLatest()'); };

test('speed 2026-11-09: memoized publishNews is byte-identical to the old pipeline on the real feed through every invalidation path', async () => {
  // Bərabərliyin əsas hissəsi real lentdir (data/news.json + og.json); hər yaddaş sıfırlanma halının öz sətri sintetikdir:
  // lent hər 10 dəqiqə dəyişir, xüsusi hal (şəkilsiz, qruplu, çıxarılan sətir) lentdən seçilsə test sabit olmazdı.
  const stamp = new Date(Date.now() - 3600e3).toISOString();
  const syn = (k, title, extra = {}) => ({ id: 'e0e0e0e0e0e0e0e' + k, title, summary: '', source: 'APA', sourceUrl: `https://apa.az/sinaq-${k}`, publishedAt: stamp, category: 'gundem', lang: 'az', ...extra });
  const real = JSON.parse(fs.readFileSync(path.join(root, 'data/news.json'), 'utf8')).articles, og = JSON.parse(fs.readFileSync(path.join(root, 'data/og.json'), 'utf8'));
  const rows = [...real,
    syn(1, 'Sınaq sətri: og xəritəsindən şəkil sonradan gəlir'),
    syn(2, 'Sınaq sətri: redaksiya bu xəbəri lentdən çıxarır'),
    syn(3, 'Sınaq sətri: əsas keçid ölüdür, alt mənbə qalır', { source: 'Report', sourceUrl: 'https://report.az/sinaq-3', alts: [{ source: 'APA', sourceUrl: 'https://apa.az/sinaq-3-alt', publishedAt: stamp, title: 'Sınaq sətri: alt mənbə ölü keçidi əvəz edir' }] }),
    syn(4, 'Sınaq sətri: şəkil dəqiqəlik lentdə tapılır')];
  const ctx = feed(rows, og);
  const cold = same(ctx, 'soyuq');
  assert.ok(run(ctx, 'S.data.articles.length') >= 100, 'real lent qaydadan keçmir: test heç nə yoxlamır');
  assert.ok(['apa.az/sinaq-1', 'apa.az/sinaq-2', 'report.az/sinaq-3', 'apa.az/sinaq-4'].every(u => cold.includes(u)), 'sınaq sətirləri lentdədir');
  assert.equal(same(ctx, 'isti (ikinci çağırış)'), cold);
  assert.ok(run(ctx, 'S.rawNews.every(a => PREP.has(a))'), 'hər xam sətrin hazır sətri yaddaşdadır');
  // og dəyişir (yeni obyekt): şəkilsiz sətir şəkil qazanır.
  run(ctx, 'S.og = { ...S.og, "https://apa.az/sinaq-1": "https://apa.az/yeni-og.jpg" }');
  assert.ok(same(ctx, 'og dəyişdi').includes('yeni-og.jpg'), 'og-dən gələn şəkil lentdədir');
  // Çıxarılan xəbər (addRemovals): yaddaşdakı hazır sətir qalmır.
  run(ctx, 'addRemovals({ x: { id: "e0e0e0e0e0e0e0e2" } })');
  assert.ok(!same(ctx, 'çıxarılan xəbər').includes('apa.az/sinaq-2'), 'çıxarılan xəbər lentdə qalmır');
  // Ölü keçid (loadLatest → deadChanged): əsas mənbə alt mənbə ilə əvəz olunur.
  const DEAD = ['https://report.az/sinaq-3'];
  await latest(ctx, { articles: [], dead: DEAD });
  assert.equal(run(ctx, 'JSON.stringify(S.data.articles)'), run(ctx, REF), 'ölü keçiddən sonra');
  assert.ok(run(ctx, 'S.data.articles.some(a => a.sourceUrl === "https://apa.az/sinaq-3-alt") && !S.data.articles.some(a => a.sourceUrl === "https://report.az/sinaq-3")'), 'ölü keçid alt mənbə ilə əvəz olunub');
  // Dəqiqəlik lentdən sonradan tapılan şəkil: eyni ölü siyahı (tam sıfırlama yoxdur), yalnız o sətir yaddaşdan silinir (PREP.delete).
  await latest(ctx, { articles: [{ ...syn(4, 'Sınaq sətri: şəkil dəqiqəlik lentdə tapılır'), imageUrl: 'https://apa.az/sonradan.jpg' }], dead: DEAD });
  const late = run(ctx, 'JSON.stringify(S.data.articles)');
  assert.equal(late, run(ctx, REF), 'şəkil sonradan tapılanda');
  assert.ok(late.includes('sonradan.jpg'), 'tapılan şəkil lentdədir');
  // Yeni gələn sətirlər (QIRMIZI XƏTT 2): yaddaş onlara aid deyil — mənbə qaydasından keçirlər.
  const now = new Date().toISOString();
  await latest(ctx, { articles: [
    { id: 'f1f1f1f1f1f1f1f1', title: 'Yeni gələn adi xəbər başlığı', source: 'APA', sourceUrl: 'https://apa.az/yeni-1', publishedAt: now, category: 'gundem', lang: 'az' },
    { id: 'f2f2f2f2f2f2f2f2', title: 'Qadağan mənbədən xəbər', source: 'Azadlıq', sourceUrl: 'https://azadliq.org/x1', publishedAt: now, category: 'gundem', lang: 'az' },
    { id: 'f3f3f3f3f3f3f3f3', title: 'Azerbaijan signs new energy deal', source: 'BBC News', sourceUrl: 'https://www.bbc.com/news/x1', publishedAt: now, category: 'dunya', lang: 'en' }], dead: DEAD });
  const after = run(ctx, 'JSON.stringify(S.data.articles)');
  assert.equal(after, run(ctx, REF), 'yeni sətirlərdən sonra');
  assert.ok(after.includes('apa.az/yeni-1') && !after.includes('azadliq.org/x1') && !after.includes('bbc.com/news/x1'), 'yeni sətir qaydadan keçir: icazəli qalır, qadağan düşür');
  // Fikstür: alt mənbəli real qrup.
  const fixture = JSON.parse(fs.readFileSync(path.join(__dirname, 'fixtures/education-duplicates.json'), 'utf8'));
  const f = feed(fixture.live, {}); assert.equal(same(f, 'fikstür soyuq'), same(f, 'fikstür isti'));
  // Alt mənbəsiz lent: clusterArticles qrupları özü qurur — giriş sətrini dəyişməməlidir (əvvəl primary.alts yazırdı, yaddaşla ikinci çağırış fərqli olardı).
  const plain = Array.from({ length: 30 }, (_, i) => ({ id: 'c' + i, title: `Bakıda yeni məktəb binasının açılışı keçirildi ${Math.floor(i / 2)}`, source: i % 2 ? 'Report' : 'APA', sourceUrl: `https://${i % 2 ? 'report' : 'apa'}.az/${i}`, publishedAt: now, category: 'tehsil', lang: 'az' }));
  const p = feed(plain, {}); const p1 = same(p, 'alt mənbəsiz soyuq');
  assert.ok(run(p, 'S.data.articles.some(a => a.alts?.length)'), 'qruplar qurulub');
  assert.equal(same(p, 'alt mənbəsiz isti'), p1);
  assert.ok(run(p, 'S.rawNews.every(a => !a.alts)'), 'xam sətirlər dəyişməyib');
});

test('speed 2026-11-09: the second publishNews on an unchanged feed costs less than half of the first (per-minute refresh)', t => {
  const rows = JSON.parse(fs.readFileSync(path.join(root, 'data/news.json'), 'utf8')).articles, og = JSON.parse(fs.readFileSync(path.join(root, 'data/og.json'), 'utf8'));
  const ctx = feed(rows, og);
  // Ən yaxşı/7; klonlama ölçüyə daxil deyil. Soyuq: təzə obyektlər (tam lent hər 10 dəqiqə), isti: eyni obyektlər (dəqiqəlik lent).
  const timed = (prep, code) => { let m = Infinity; for (let i = 0; i < 7; i++) { prep(); const t0 = performance.now(); run(ctx, code); m = Math.min(m, performance.now() - t0); } return m; };
  const cold = timed(() => run(ctx, 'S.rawNews = S.rawNews.map(a => ({ ...a }))'), 'publishNews()');
  const warm = timed(() => {}, 'publishNews()');
  t.diagnostic(`publishNews ms (ən yaxşı/7): soyuq ${cold.toFixed(1)}, isti ${warm.toFixed(1)}`);
  assert.ok(warm < cold / 2, `isti ${warm.toFixed(1)} ms ≥ soyuq ${cold.toFixed(1)} / 2 — hazır sətir yaddaşı işləmir`);
});
