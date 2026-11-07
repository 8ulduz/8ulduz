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
  const [now, later = ''] = html.split('<template data-late>');
  assert.equal((now.match(/apa\.az\/\d+/g) || []).length > 0, true);
  assert.equal(new Set(now.match(/apa\.az\/\d+"/g)).size, 6, 'ilk çəkilişdə 6 kart (telefon ekranında 2–3 görünür)');
  assert.equal(new Set(later.match(/apa\.az\/\d+"/g)).size, 42, 'qalanı şablonda: brauzer yerləşdirmir');
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
