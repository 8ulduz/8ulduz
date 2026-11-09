// Çəkiliş xərci qoruyucuları (sahib, 2026-11-09: «gələcəkdə əlavələr də sürəti azaltmasın»). Tam lentin JS hissəsi (publishNews + homeView)
// telefonda 4× yavaş prosessorda ~600 ms idi; 2026-11-05-də kartlara düşən 764 paylaşma işarəsi HTML-i +140 KB, DOM-u +400 düyün böyütdü
// (TBT +300 ms) və yalnız əl ilə A/B-də tapıldı. Burada: eyni sintetik lent (1 200 sətir, toxum sabit) üzərində
//  1) HTML və teq sayı DƏQİQ sayılır (hər kartda bir əlavə düymə belə görünür);
//  2) vaxt «5-dən ən yaxşısı» ilə ölçülür (səs-küy vaxtı yalnız artırır); hədd bu PC-dəki medianın 4–6 qatıdır (GitHub runner ~2× yavaş, fayllar paralel);
//  3) app.js-də yerləşdirmə oxuyan API-lərin sayı yalnız azala bilər (ratchet): çəkilişin içində oxumaq məcburi yerləşdirmədir (viewWidth + near 370 ms, 4×).
// Rəqəmlər docs/qirmizi-xetler.md §3-də; hədd yalnız sahibin qərarı ilə dəyişir.
const { test } = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs"), vm = require("node:vm"), path = require("node:path");
const root = path.join(__dirname, "..");
const read = f => fs.readFileSync(path.join(root, f), "utf8").replace(/\r\n/g, "\n");
const APP = read("assets/app.js");
const CPU = require("./budce.json").cpu;

// Toxumlu sintetik lent: 14 bölmə, 6 mənbə (hamısı qayda siyahısında), 25%-də 1–3 alt mənbə, hər 10-cu başlıq əvvəlkinin «davamı»
// (clusterArticles/collapseExact işləsin), 70%-də şəkil, xülasə 120–220 simvol, son 24 saat.
function rows(n = 1200) {
  let s = 20261109; const rnd = () => { s = (s + 0x6D2B79F5) | 0; let t = Math.imul(s ^ (s >>> 15), 1 | s); t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t; return ((t ^ (t >>> 14)) >>> 0) / 4294967296; };
  const CATS = ["prezident", "sondeqiqe", "gundem", "siyaset", "cemiyyet", "iqtisadiyyat", "dunya", "idman", "medeniyyet", "heyat", "sosial", "bolgeler", "tehsil", "video"];
  const SRC = [["APA", "apa.az"], ["Report", "report.az"], ["AZƏRTAC", "azertag.az"], ["Trend", "trend.az"], ["Oxu.az", "oxu.az"], ["Qafqazinfo", "qafqazinfo.az"]];
  const W = ["Bakıda", "Prezident", "İlham Əliyev", "nazirlik", "məktəb", "yol", "qiymət", "futbol", "Qarabağ", "Neftçi", "manat", "dollar", "hava", "Gəncə", "Sumqayıt", "sərgi", "konsert", "müqavilə", "layihə", "rayon", "icra", "səhiyyə", "universitet", "tədbir", "görüş", "səfər", "açılış", "qərar", "fərman", "sərəncam"];
  const word = () => W[Math.floor(rnd() * W.length)];
  const out = [];
  const t0 = Date.UTC(2026, 10, 9, 12, 0, 0);
  for (let i = 0; i < n; i++) {
    const [source, host] = SRC[i % SRC.length], cat = CATS[i % CATS.length];
    const base = i % 10 === 9 ? out[i - 1].title : `${word()} ${word()} ${word()} ${word()} ${i}`;
    const a = { id: (0x1000000000000 + i * 7919).toString(16).padStart(16, "0").slice(-16), title: i % 10 === 9 ? base + " — davamı" : base, summary: (`${word()} ${word()} ${word()} ${word()} ${word()} ${word()} ${word()} ${word()} ${word()} ${word()}. `).repeat(3).slice(0, 120 + Math.floor(rnd() * 100)),
      category: cat, source, sourceUrl: `https://${host}/news/${i}`, publishedAt: new Date(t0 - Math.floor(rnd() * 86400e3)).toISOString(), lang: "az", author: "", video: cat === "video" ? `https://www.youtube.com/watch?v=v${i}` : "" };
    if (rnd() < 0.7) a.imageUrl = `https://${host}/img/${i}.jpg`;
    if (rnd() < 0.25) a.alts = Array.from({ length: 1 + Math.floor(rnd() * 3) }, (_, k) => { const [sn, sh] = SRC[(i + k + 1) % SRC.length]; return { source: sn, sourceUrl: `https://${sh}/n/${i}-${k}`, title: a.title }; });
    out.push(a);
  }
  return out;
}

// prerender.cjs ilə eyni mühit: content-policy.js yüklənir (mənbə qaydası işləsin), DOM yoxdur, yalnız HTML qurulur.
function feedCtx(width, list = rows()) {
  const els = {};
  const el = id => els[id] ||= { id, _html: "", set innerHTML(v) { this._html = v; }, get innerHTML() { return this._html; }, addEventListener() {}, classList: { toggle() {}, add() {}, remove() {}, contains() { return false; } }, querySelector() { return null; }, querySelectorAll() { return []; }, focus() {}, dataset: {}, style: {} };
  const ctx = vm.createContext({
    console: { ...console, log() {}, warn() {}, info() {} }, Map, Set, URL, Date, AbortController, setTimeout, clearTimeout, performance, innerWidth: width, TextEncoder, btoa,
    addEventListener() {}, localStorage: { getItem() { return null; }, setItem() {}, removeItem() {} },
    location: { hash: "#/", href: "https://8ulduz.az/" }, navigator: { onLine: true }, history: { replaceState() {} },
    document: { documentElement: { dataset: {}, style: {} }, hidden: false, activeElement: null, title: "", addEventListener() {}, querySelector(s) { const m = s.match(/^#([\w-]+)$/); return m ? el(m[1]) : null; }, querySelectorAll() { return []; },
      createElement() { return { _v: "", set innerHTML(v) { this._v = String(v); }, get innerHTML() { return this._v; }, get value() { return this._v; }, content: {}, children: [] }; } },
    matchMedia: q => ({ matches: width < 700 && String(q).includes("hover:none") }), requestAnimationFrame: () => 0,
    SITE_CONFIG: { goatcounter: "", telegram: "", contact: "" },
  });
  ctx.window = ctx;
  vm.runInContext(read("assets/content-policy.js"), ctx);
  vm.runInContext(APP.split("\napplyPrefs();\n")[0], ctx);
  vm.runInContext("render = () => {}; renderTopbar = () => {}; checkBreaking = () => {}; primeHeroImage = () => {}; requestRender = () => {}; loadArchive = async () => {}; loadOg = async () => {};", ctx);
  ctx.__rows = list;
  vm.runInContext('S.og = {}; S.rawNews = __rows; S.rawMeta = { updatedAt: "2026-11-09T12:00:00.000000+00:00", count: __rows.length }; S.partial = false; S.lang = "az"; publishNews();', ctx);
  return ctx;
}
const run = (ctx, code) => vm.runInContext(code, ctx);
const best = (fn, n = 5) => { let m = Infinity; for (let i = 0; i < n; i++) { const t = performance.now(); fn(); m = Math.min(m, performance.now() - t); } return Math.round(m * 10) / 10; };
const tags = h => (h.match(/<[a-z]/g) || []).length;
const bytes = h => Buffer.byteLength(h);
const eager = h => h.replace(/<template[\s\S]*?<\/template>/g, ""); // telefonda sonraya saxlanan hissə brauzerə dərhal yerləşdirilmir

test("cpu: publishing and drawing the full feed stays cheap (1 200 rows, best of 5, 1× CPU) — thresholds in tests/budce.json", t => {
  const ctx = feedCtx(390);
  assert.ok(run(ctx, "S.data.articles.length") >= 1100, "sintetik lent mənbə qaydasından keçmir: test heç nə ölçmür");
  const got = {
    publishNews: best(() => run(ctx, "publishNews()")),
    homeView: best(() => run(ctx, "homeView()")),
    "publishNews+homeView": best(() => run(ctx, "publishNews(); homeView()")),
    sectionView: Math.max(...["gundem", "idman", "bolgeler"].map(s => best(() => run(ctx, `sectionView(${JSON.stringify(s)})`)))),
    articleView: best(() => run(ctx, "articleView(S.data.articles[40].id)")),
    collapseExact: best(() => run(ctx, "collapseExact(S.rawNews.map(a => ({ ...a, alts: a.alts || [] })))")),
  };
  run(ctx, 'S.archive = Object.fromEntries(CATS.map(c => [c.slug, { at: Date.now(), rows: S.rawNews.filter(a => a.category === c.slug).slice(0, 200).map(a => ({ ...a, id: a.id + "a", sourceUrl: a.sourceUrl + "?a" })) }])); S.arxV = (S.arxV || 0) + 1; S.q = "bakı";');
  got.searchView = best(() => run(ctx, "S.arxV++; searchView()"));
  t.diagnostic("cpu ms (ən yaxşı/5): " + JSON.stringify(got));
  for (const [k, ms] of Object.entries(got)) assert.ok(ms < CPU[k], `${k}: ${ms} ms ≥ ${CPU[k]} (telefonda 4×: ×4) — çəkiliş funksiyasına ağır iş düşüb; sətir başına işi azaldın və ya nəticəni yaddaşda saxlayın (imageCandidates, savedList kimi)`);
});

test("html: the home page emits a bounded amount of HTML and eager DOM (2026-11-05: +140 KB / +400 nodes from share icons went unnoticed)", t => {
  const phone = run(feedCtx(390), "homeView()"), desk = run(feedCtx(1280), "homeView()");
  const lazy = run(feedCtx(390), "homeView(); [...lazyHtml.values()].join('')");
  const card = run(feedCtx(390), "card(S.data.articles.find(a => a.imageUrl && a.alts?.length))");
  const got = { phoneBytes: bytes(phone), phoneTags: tags(phone), phoneEagerBytes: bytes(eager(phone)), phoneEagerTags: tags(eager(phone)), deskBytes: bytes(desk), deskTags: tags(desk), lazyBytes: bytes(lazy), lazyTags: tags(lazy), cardBytes: bytes(card), cardTags: tags(card), use: (eager(phone).match(/<use /g) || []).length, lazySecs: (phone.match(/class="lazy-sec"/g) || []).length };
  t.diagnostic("html: " + JSON.stringify(got));
  const H = CPU.html;
  for (const k of Object.keys(H)) assert.ok(got[k] <= H[k], `${k}: ${got[k]} > ${H[k]} — səhifə sətri/DOM böyüyüb; işarə və düymə lazımdırsa yaxınlaşanda qoyun (lazySection, late), kartı yox, bölməni dəyişin`);
  assert.ok(!/class="lazy-sec"><template>/.test(phone), "uzaq bölmələrin HTML-i səhifə sətrində deyil (lazyHtml)");
  assert.ok(got.lazySecs >= 6, "uzaq bölmələr yaxınlaşanda qurulur");
});

test("layout: no new forced-layout reads in app.js (ratchet — lower a number when a read moves to an event or requestAnimationFrame)", () => {
  const READS = CPU.layoutReads;
  for (const [k, max] of Object.entries(READS)) {
    const n = (APP.match(new RegExp("\\b" + k + "\\b", "g")) || []).length;
    assert.ok(n <= max, `${k}: ${n} > ${max} — yerləşdirmə oxuması çəkilişin içində məcburi yerləşdirmədir (viewWidth + near 370 ms idi, 4×); ölçünü resize/scroll hadisəsindən və ya afterFrame-dən sonra oxuyun`);
  }
  assert.ok(APP.includes("function viewWidth() { return viewW || (viewW = globalThis.innerWidth || 1200); }"), "viewWidth keşlənmiş eni oxuyur (hər kartda innerWidth 72–195 ms idi)");
  assert.ok(/afterFrame\(near\);/.test(APP), "slayder şəkillərinin yaxınlıq ölçüsü kadrdan sonra (çəkilişin içində getBoundingClientRect 120–391 ms idi)");
});
