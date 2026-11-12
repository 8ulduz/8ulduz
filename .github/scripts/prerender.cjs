#!/usr/bin/env node
// Sürət (qırmızı xətt 3, docs/qirmizi-xetler.md): baş səhifənin ilk ekranı (slayder, Zuğulba, «Son xəbərlər») index.html-ə
// hazır HTML kimi yazılır. Brauzer onu CSS gələn kimi çəkir, app.js gələndə eyni görünüşü təzə məlumatla əvəz edir (patchView).
// pipeline.sh (publish_main) hər main yazılışında işlədir: node .github/scripts/prerender.cjs <repo>
// HTML ayrı şablondan deyil, app.js-in öz homeView()-undan çıxır (data/first.json, S.partial): sayt və hazır nüsxə eyni koddur.
// Telefon eni (390) üçün çəkilir: ilk şəkil 640 px-dir və HTML-dən dərhal yüklənir; kompüterdə də 640 qalır (app.js heroPicWidth;
// 2026-11-09-a qədər app.js onu 800 ilə əvəz edirdi — eyni şəkil ikinci dəfə yüklənirdi).
// Yalnız ekranda görünən hissə saxlanır (3 slayd, 8 Zuğulba kartı, 4 son xəbər): tam blok 104 KB (24 KB gzip) idi və ilk
// çəkilişi gecikdirirdi; qalanı app.js tam siyahı ilə doldurur (44 Zuğulba kartı qaydası səhifənin özündə dəyişmir).
"use strict";
const fs = require("node:fs"), path = require("node:path"), vm = require("node:vm");

const NOSCRIPT = "<noscript>Saytı görmək üçün JavaScript-i aktiv edin.</noscript>";
const VIEW_RE = /(<div class="wrap" id="view" tabindex="-1">)([\s\S]*?)(<noscript>Saytı görmək üçün JavaScript-i aktiv edin\.<\/noscript><\/div><\/main>)/;
// Telefon ekranına sığan qədər (2026-11-05 ölçüsü: 31,5 KB → ~15 KB; böyük statik DOM slayder şəklinin boyanmasını ləngidirdi).
// Ehtiyat şəkil siyahısı (data-image-alternatives) hazır nüsxədə 2 ünvana qədər: JS gələndə tam siyahı qayıdır.
const KEEP = { slides: 2, prez: 4, latest: 2, alts: 2 };
const esc = s => String(s).replace(/&/g, "&amp;").replace(/"/g, "&quot;").replace(/</g, "&lt;");

// app.js decode() başlıqdakı HTML işarələrini <textarea> ilə açır; burada brauzer yoxdur, eyni işi bu cədvəl görür.
const NAMED = { amp: "&", lt: "<", gt: ">", quot: '"', apos: "'", nbsp: " ", ndash: "–", mdash: "—", laquo: "«", raquo: "»", hellip: "…", bdquo: "„", ldquo: "“", rdquo: "”", lsquo: "‘", rsquo: "’", copy: "©", shy: "­" };
const decodeEntities = s => String(s).replace(/&(#x[0-9a-f]+|#\d+|[a-z]+);/gi, (m, e) => {
  if (e[0] === "#") { const n = e[1] === "x" || e[1] === "X" ? parseInt(e.slice(2), 16) : parseInt(e.slice(1), 10); return Number.isFinite(n) && n > 0 && n < 0x110000 ? String.fromCodePoint(n) : m; }
  return NAMED[e.toLowerCase()] ?? m;
});

// app.js-in brauzer mühiti: shellgen/test harness ilə eyni saxta DOM. Yalnız HTML qurulur, heç nə çəkilmir.
// Baş səhifənin ilk ekranı (#view) və yuxarı zolaq (#topbar). Zolaq boş qalanda JS onu dolduran kimi lupa düyməsi 119 px sağa,
// bölmələr 4 px aşağı sürüşürdü (Lighthouse CLS 0,118, 2026-11-05 izi); hazır zolaq açılışdakı ilə eyni quruluşdadır (hava «—», dil «Hamısı»).
function homeHtml(root, first, opts) { return renderHome(root, first, opts).view; }
const oneLine = s => String(s).replace(/\s*\n\s*/g, " ").trim();
function renderHome(root, first, { now = 0, width = 390 } = {}) {
  const els = {};
  const el = id => els[id] ||= { id, _html: "", set innerHTML(v) { this._html = v; }, get innerHTML() { return this._html; }, addEventListener() {}, classList: { toggle() {}, add() {}, remove() {} }, querySelector() { return null; }, querySelectorAll() { return []; }, focus() {}, dataset: {}, style: {}, setAttribute() {}, set onclick(f) {}, hidden: false };
  // Sabit vaxt (testlər üçün): «5 dəqiqə əvvəl» və slayder pəncərəsi həmin ana görə hesablanır.
  const D = now ? class extends Date { constructor(...a) { super(...(a.length ? a : [now])); } static now() { return now; } } : Date;
  const context = vm.createContext({
    console: { ...console, log() {}, warn() {}, info() {} }, Map, Set, URL, Date: D, AbortController, setTimeout, clearTimeout, performance, innerWidth: width,
    addEventListener() {}, localStorage: { getItem() { return null; }, setItem() {}, removeItem() {} },
    location: { hash: "#/", href: "https://8ulduz.az/" }, navigator: { onLine: true }, history: { replaceState() {} },
    document: { documentElement: { dataset: {}, style: {} }, hidden: false, activeElement: null, title: "", addEventListener() {}, querySelector(s) { const m = s.match(/^#([\w-]+)$/); return m ? el(m[1]) : null; }, querySelectorAll() { return []; },
      // textarea (decode) və template (patchView) üçün: value işarələri açır
      createElement() { return { _v: "", set innerHTML(v) { this._v = String(v); }, get innerHTML() { return this._v; }, get value() { return decodeEntities(this._v); }, content: {}, children: [] }; } },
    matchMedia: () => ({ matches: false }), requestAnimationFrame: () => 0,
    SITE_CONFIG: { goatcounter: "", telegram: "", contact: "" },
  });
  context.window = context; // content-policy.js window.CONTENT_POLICY yazır, app.js globalThis.CONTENT_POLICY oxuyur: mənbə qaydası (qırmızı xətt 2) burada da işləyir
  vm.runInContext(fs.readFileSync(path.join(root, "assets/content-policy.js"), "utf8"), context);
  const source = fs.readFileSync(path.join(root, "assets/app.js"), "utf8").split(/\r?\napplyPrefs\(\);\r?\n/)[0];
  vm.runInContext(source, context);
  vm.runInContext("const __topbar = renderTopbar; render = () => {}; renderTopbar = () => {}; checkBreaking = () => {}; primeHeroImage = () => {}; requestRender = () => {};", context);
  context.__first = first;
  const view = vm.runInContext("S.og = __first.og || {}; S.rawNews = __first.articles; S.rawMeta = { ...__first, articles: undefined }; S.partial = true; publishNews(); homeView();", context);
  const topbar = oneLine(vm.runInContext("__topbar(); document.querySelector('#topbar').innerHTML", context));
  return { view, topbar };
}
const TOPBAR_RE = /(<div class="topbar"><div class="wrap" id="topbar">)([^\n]*)(<\/div><\/div>\r?)$/m;
function validateTopbar(html) {
  if (typeof html !== "string" || html.length < 300 || html.length > 8000) throw Error("yuxarı zolaq ölçüsü: " + (html && html.length));
  if (/<script\b|\n/i.test(html)) throw Error("yuxarı zolaqda skript və ya sətir sonu var");
  for (const k of ['class="wx', 'data-act="theme"', 'class="ldd"', 'data-act="pray"']) if (!html.includes(k)) throw Error("yuxarı zolaqda yoxdur: " + k);
}

// Ekranda görünən hissə: slayderin ilk slaydları, Zuğulbanın ilk kartları, «Son xəbərlər»in ilk kartları. Kartların içində
// eyni teq yuvalanmır (app.js heroBlock/prezBlock/cardAt), ona görə ardıcıl kəsmək kifayətdir.
function firstScreen(html, keep = KEEP) {
  const trim = (s, re, n) => { let i = 0; return s.replace(re, m => (++i > n ? "" : m)); };
  let out = trim(html, /<article class="hero-main"[\s\S]*?<\/article>/g, keep.slides);
  out = trim(out, /<article class="pcard[\s\S]*?<\/article>/g, keep.prez);
  const at = out.indexOf('<div class="latest-grid">');
  if (at >= 0) out = out.slice(0, at) + trim(out.slice(at), /<article class="card[\s\S]*?<\/article>/g, keep.latest);
  // Siyahı kəsiləndə son dırnaq da qayıtmalıdır: «["a","b]» JSON deyil, imgFail onu oxuya bilmir və ehtiyat ünvana keçmək əvəzinə şəkli silir.
  if (keep.alts != null) out = out.replace(/data-image-alternatives="\[([^"]*)\]"/g, (all, list) => {
    const urls = list.split("&quot;,&quot;");
    return urls.length <= keep.alts ? all : `data-image-alternatives="[${urls.slice(0, keep.alts).join("&quot;,&quot;")}&quot;]"`;
  });
  return out;
}

function validate(html) {
  if (typeof html !== "string" || html.length < 3000) throw Error("ilk ekran qısadır: " + (html && html.length));
  if (html.length > 120000) throw Error("ilk ekran böyükdür: " + html.length);
  if (!html.includes('<section class="hero">')) throw Error("slayder yoxdur");
  if (!html.includes("Son xəbərlər")) throw Error("«Son xəbərlər» bloku yoxdur");
  if (/<script\b/i.test(html)) throw Error("hazır HTML-də skript var (CSP hash-ı dəyişməlidir)"); // index.html-in CSP-si yalnız bir daxili skriptə icazə verir
  if (/<noscript/i.test(html)) throw Error("hazır HTML-də noscript var");
  if (/&amp;amp;/.test(html)) throw Error("başlıqdakı işarələr açılmayıb");
}

// index.html-in #view blokunu yenidən yazır. Qalan hər şey (qabıq, CSP, sətir sonları) toxunulmur. Dəyişiklik varsa true.
function prerender(root, opts = {}) {
  const file = path.join(root, "index.html");
  const index = fs.readFileSync(file, "utf8");
  if ((index.match(/id="view"/g) || []).length !== 1) throw Error('index.html-də #view bir dəfə olmalıdır');
  const m = index.match(VIEW_RE);
  if (!m) throw Error("index.html-də #view bloku və noscript tapılmadı");
  const first = JSON.parse(fs.readFileSync(path.join(root, "data/first.json"), "utf8"));
  if (!Array.isArray(first.articles) || first.articles.length < 10) throw Error("first.json-da xəbər azdır");
  if ((index.match(/id="topbar"/g) || []).length !== 1 || !TOPBAR_RE.test(index)) throw Error('index.html-də #topbar sətri bir dəfə olmalıdır');
  const home = renderHome(root, first, opts), html = firstScreen(home.view);
  validate(html);
  validateTopbar(home.topbar);
  const block = `${m[1]}<div class="pre-skel" data-prerender="${esc(first.updatedAt || "")}">${html}</div>${m[3]}`;
  const out = (index.slice(0, m.index) + block + index.slice(m.index + m[0].length)).replace(TOPBAR_RE, (_, a, b, c) => a + home.topbar + c);
  if (out === index) return { changed: false, bytes: Buffer.byteLength(out), view: html.length };
  const tmp = file + ".tmp";
  fs.writeFileSync(tmp, out); // yarımçıq fayl qalmasın: əvvəl kənara, sonra yerinə
  fs.renameSync(tmp, file);
  return { changed: true, bytes: Buffer.byteLength(out), view: html.length };
}

module.exports = { homeHtml, renderHome, firstScreen, prerender, validate, validateTopbar, decodeEntities, VIEW_RE, TOPBAR_RE, NOSCRIPT, KEEP };

if (require.main === module) {
  const root = process.argv[2] || process.cwd();
  process.env.TZ = "Asia/Baku"; // yuxarı zolağın tarixi (app.js today()): runner UTC-dədir, 00:00–04:00 arası hazır nüsxədə dünənki gün yazılırdı
  try {
    const r = prerender(root);
    console.log(`ilk ekran index.html-də: ${r.changed ? "yeniləndi" : "dəyişmədi"}, ${r.view} simvol, fayl ${r.bytes} bayt`);
  } catch (e) {
    console.error("prerender alınmadı:", e.message);
    process.exit(1);
  }
}
