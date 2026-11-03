#!/usr/bin/env node
// Sürət (qırmızı xətt 3, docs/qirmizi-xetler.md): baş səhifənin ilk ekranı (slayder, Zuğulba, «Son xəbərlər») index.html-ə
// hazır HTML kimi yazılır. Brauzer onu CSS gələn kimi çəkir, app.js gələndə eyni görünüşü təzə məlumatla əvəz edir (patchView).
// pipeline.sh (publish_main) hər main yazılışında işlədir: node .github/scripts/prerender.cjs <repo>
// HTML ayrı şablondan deyil, app.js-in öz homeView()-undan çıxır (data/first.json, S.partial): sayt və hazır nüsxə eyni koddur.
// Telefon eni (390) üçün çəkilir: ilk şəkil 640 px-dir və HTML-dən dərhal yüklənir; kompüterdə app.js onu 800 px ilə əvəz edir.
"use strict";
const fs = require("node:fs"), path = require("node:path"), vm = require("node:vm");

const NOSCRIPT = "<noscript>Saytı görmək üçün JavaScript-i aktiv edin.</noscript>";
const VIEW_RE = /(<div class="wrap" id="view" tabindex="-1">)([\s\S]*?)(<noscript>Saytı görmək üçün JavaScript-i aktiv edin\.<\/noscript><\/div><\/main>)/;
const esc = s => String(s).replace(/&/g, "&amp;").replace(/"/g, "&quot;").replace(/</g, "&lt;");

// app.js-in brauzer mühiti: shellgen/test harness ilə eyni saxta DOM. Yalnız HTML qurulur, heç nə çəkilmir.
function homeHtml(root, first, { now = 0, width = 390 } = {}) {
  const els = {};
  const el = id => els[id] ||= { id, _html: "", set innerHTML(v) { this._html = v; }, get innerHTML() { return this._html; }, addEventListener() {}, classList: { toggle() {}, add() {}, remove() {} }, querySelector() { return null; }, querySelectorAll() { return []; }, focus() {}, dataset: {}, style: {}, setAttribute() {}, set onclick(f) {}, hidden: false };
  // Sabit vaxt (testlər üçün): «5 dəqiqə əvvəl» və slayder pəncərəsi həmin ana görə hesablanır.
  const D = now ? class extends Date { constructor(...a) { super(...(a.length ? a : [now])); } static now() { return now; } } : Date;
  const context = vm.createContext({
    console: { ...console, log() {}, warn() {}, info() {} }, Map, Set, URL, Date: D, AbortController, setTimeout, clearTimeout, performance, innerWidth: width,
    addEventListener() {}, localStorage: { getItem() { return null; }, setItem() {}, removeItem() {} },
    location: { hash: "#/", href: "https://8ulduz.az/" }, navigator: { onLine: true }, history: { replaceState() {} },
    document: { documentElement: { dataset: {}, style: {} }, hidden: false, activeElement: null, title: "", addEventListener() {}, querySelector(s) { const m = s.match(/^#([\w-]+)$/); return m ? el(m[1]) : null; }, querySelectorAll() { return []; }, createElement() { return { set innerHTML(v) { this._v = v; }, content: {}, children: [] }; } },
    matchMedia: () => ({ matches: false }), requestAnimationFrame: () => 0,
    SITE_CONFIG: { goatcounter: "", telegram: "", contact: "" },
  });
  context.window = context; // content-policy.js window.CONTENT_POLICY yazır, app.js globalThis.CONTENT_POLICY oxuyur: mənbə qaydası (qırmızı xətt 2) burada da işləyir
  vm.runInContext(fs.readFileSync(path.join(root, "assets/content-policy.js"), "utf8"), context);
  const source = fs.readFileSync(path.join(root, "assets/app.js"), "utf8").split(/\r?\napplyPrefs\(\);\r?\n/)[0];
  vm.runInContext(source, context);
  vm.runInContext("render = () => {}; renderTopbar = () => {}; checkBreaking = () => {}; primeHeroImage = () => {}; requestRender = () => {};", context);
  context.__first = first;
  return vm.runInContext("S.og = __first.og || {}; S.rawNews = __first.articles; S.rawMeta = { ...__first, articles: undefined }; S.partial = true; publishNews(); homeView();", context);
}

function validate(html) {
  if (typeof html !== "string" || html.length < 3000) throw Error("ilk ekran qısadır: " + (html && html.length));
  if (html.length > 400000) throw Error("ilk ekran böyükdür: " + html.length);
  if (!html.includes('<section class="hero">')) throw Error("slayder yoxdur");
  if (!html.includes("Son xəbərlər")) throw Error("«Son xəbərlər» bloku yoxdur");
  if (/<script\b/i.test(html)) throw Error("hazır HTML-də skript var (CSP hash-ı dəyişməlidir)"); // index.html-in CSP-si yalnız bir daxili skriptə icazə verir
  if (/<noscript/i.test(html)) throw Error("hazır HTML-də noscript var");
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
  const html = homeHtml(root, first, opts);
  validate(html);
  const block = `${m[1]}<div class="pre-skel" data-prerender="${esc(first.updatedAt || "")}">${html}</div>${m[3]}`;
  const out = index.slice(0, m.index) + block + index.slice(m.index + m[0].length);
  if (out === index) return { changed: false, bytes: Buffer.byteLength(out), view: html.length };
  const tmp = file + ".tmp";
  fs.writeFileSync(tmp, out); // yarımçıq fayl qalmasın: əvvəl kənara, sonra yerinə
  fs.renameSync(tmp, file);
  return { changed: true, bytes: Buffer.byteLength(out), view: html.length };
}

module.exports = { homeHtml, prerender, validate, VIEW_RE, NOSCRIPT };

if (require.main === module) {
  const root = process.argv[2] || process.cwd();
  try {
    const r = prerender(root);
    console.log(`ilk ekran index.html-də: ${r.changed ? "yeniləndi" : "dəyişmədi"}, ${r.view} simvol, fayl ${r.bytes} bayt`);
  } catch (e) {
    console.error("prerender alınmadı:", e.message);
    process.exit(1);
  }
}
