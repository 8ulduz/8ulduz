// Sürət ölçüsü (qırmızı xətt 3, sahib 2026-11-05: «gözqırpımı sürət» — bütün bölmə, alt bölmə və onların alt bölmələri).
// Başsız Chrome-da telefon şəraiti: 412×915 ekran, prosessor 4 dəfə yavaş (orta Android), mobil şəbəkə.
// Hər səviyyə ölçülür: soyuq açılış, 14 bölmə, xidmət səhifələri, idmanın alt bölmələri və onların alt düymələri, liqa və komanda
// səhifələri, Bölgələrin regionları və rayonları, xəbər səhifəsi, axtarış. Əlavə paket yoxdur (Node 22+: WebSocket, fetch).
//
// v2 (2026-11-09; PR #142-nin dərsləri — köhnə alət real reqressiyanı görmürdü):
//  • isti brauzer, soyuq keş: hər soyuq ölçüdən əvvəl 404.html (2,5 KB, saytın kodu yoxdur) açılır — təzə prosesin ilk yerləşdirməsi
//    Windows-da şrift işinə 1,2–1,6 s (4×) itirirdi («yavaş» yalançı idi); sonra HTTP keşi, xidmət işçisi və yaddaş silinir;
//  • sənəd başlanğıcından müşahidə (Page.addScriptToEvaluateOnNewDocument): ilk boya (FCP), CLS, LCP, ilk boyadan əvvəlki uzun
//    tapşırıqlar (köhnə köməkçi yüklənmədən sonra qoyulurdu və onları görmürdü), görünən ilk məzmun məcburi yerləşdirməsiz;
//  • şəbəkə hadisələri: sorğu sayı, bayt, slayder şəklinin təkrar yüklənməsi (heroLoads: kompüterdə 640 → 800 px iki dəfə gəlirdi);
//  • mənbəyə gedib qayıtmaq: geri-irəli keşi (bfcache) — qayıtmasa Chrome-un səbəbləri (NetworkRequestRedirected …);
//  • paylaşılan xəbər keçidi (#/xeber/<id>?b=&h=) və kompüter keçidi (CLS, heroLoads);
//  • --ab <baza>: baza nüsxəsi eyni anda, A, B, A, B, A, B növbəsi ilə — eyni kod runner-də 3,5 Lighthouse balı / 1 157 ms TBT oynayır,
//    mütləq büdcə +500 ms reqressiyanı keçirirdi; indi median(B) − median(A) > max(spread(A), pay × median(A), min) olanda qırmızı;
//  • gecə: --third-party (səhifə açıq olarkən soruşulan ünvanlar yönləndirməz — bfcache), --pages (xeber/<id>/ şablon versiyası),
//    --data (canlı məlumat fayllarının gzip ölçüsü tests/budce.json «melumat» tavanlarına qarşı).
// Bütün büdcələr tests/budce.json «speed» qrupundadır (sahib: bir yerdə; docs/qirmizi-xetler.md §3 «Büdcə cədvəli» ilə test tutuşdurur).
// Yeni ölçülər (fcp, cls, bfcache …) ilk 10 planlı dövrədə (yeni.sert tarixinədək) yalnız xəbərdarlıqdır — runner-in səs-küyü görülsün.
//
//   node .github/scripts/speed.cjs https://8ulduz.az/                                        # canlı sayt
//   node .github/scripts/speed.cjs http://localhost:8080/ --budget                           # büdcəni keçən varsa çıxış kodu 1 (CI)
//   node .github/scripts/speed.cjs http://localhost:8080/ --budget --ab http://localhost:8081/   # PR: baza nüsxəsi ilə A/B
//   node .github/scripts/speed.cjs https://8ulduz.az/ --budget --third-party --pages --data  # gecə dövrəsi
//   CHROME=/path/to/chrome  SPEED_CPU=4  SPEED_REPS=3  SPEED_QUICK=1  SPEED_JSON=speed.json  SPEED_NO_BROWSER=1 (yalnız gecə yoxlamaları)
//   SPEED_COLD_ONLY=1 (yalnız soyuq açılışlar, bfcache, A/B — A/A sınağı üçün)
//   GH_TOKEN=… (--pages: STORY_VER artımının vaxtı GitHub API-dən)
"use strict";
const { spawn } = require("child_process");
const fs = require("fs"), os = require("os"), path = require("path"), http = require("http"), https = require("https"), zlib = require("zlib");

const ROOT = path.join(__dirname, "..", "..");
const B = JSON.parse(fs.readFileSync(path.join(ROOT, "tests/budce.json"), "utf8"));
const LIMITS = B.speed; // bütün büdcələr tests/budce.json-da (sahib, 2026-11-09)
const ARGS = process.argv.slice(2);
const BASE = (ARGS[0] && !ARGS[0].startsWith("--") ? ARGS[0] : "https://8ulduz.az/").replace(/\/?$/, "/");
const BUDGET = ARGS.includes("--budget");
const AB = ARGS.includes("--ab") && ARGS[ARGS.indexOf("--ab") + 1] ? ARGS[ARGS.indexOf("--ab") + 1].replace(/\/?$/, "/") : null;
const NIGHT = { third: ARGS.includes("--third-party"), pages: ARGS.includes("--pages"), data: ARGS.includes("--data") };
const CPU = Number(process.env.SPEED_CPU || 4);
const QUICK = !!process.env.SPEED_QUICK; // A/B üçün qısa dövrə: hər səviyyədən bir neçə nümunə
const COLD_ONLY = !!process.env.SPEED_COLD_ONLY; // yalnız soyuq sətirlər, bfcache və A/B (A/A sınağı üçün: eyni nüsxə iki portda, 5 dəfə)
const REPS = Math.max(1, Number(process.env.SPEED_REPS || 1)); // ünvan keçidləri və soyuq açılış neçə dəfə (median)
const REPO = process.env.GITHUB_REPOSITORY || "8ulduz/8ulduz";
const TOKEN = process.env.GH_TOKEN || process.env.GITHUB_TOKEN || "";
const UA_PHONE = "Mozilla/5.0 (Linux; Android 14; Pixel 7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0 Mobile Safari/537.36";
const UA_DESK = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0 Safari/537.36";
const UA_TOOL = "8ulduz-speed (+https://8ulduz.az)";
// Mobil şəbəkə (Lighthouse «slow 4G»-dən bir az yaxşı): 100 ms RTT, 6 Mbit/s.
const NET_PHONE = { offline: false, latency: 100, downloadThroughput: 6e6 / 8, uploadThroughput: 2e6 / 8 };
const NET_FREE = { offline: false, latency: 0, downloadThroughput: -1, uploadThroughput: -1 };
// Sayğaclar ölçünün özündə qalır (saytın real işi), amma alətin öz 404.html ziyarətləri statistikaya düşməsin.
const ANALYTICS = ["*gc.zgo.at*", "*goatcounter.com*", "*google-analytics.com*"];
// Yeni ölçülər ilk 10 planlı dövrədə (gündə 4) yalnız xəbərdarlıqdır; tests/budce.json speed.yeni.sert tarixindən sonra sərt.
// Gecə yoxlamaları (--third-party, --pages, --data) səs-küysüzdür və öz qaydası ilə dərhal qırmızıdır (--pages: versiya artımından 24 saat).
const NEW = ["fcp", "fcpAfterCss", "preFcpLongTaskMax", "preFcpLongTaskSum", "cls", "heroLoads", "bfcache", "storyCold", "requests"];
const WARN_ONLY = new Set(Date.now() < Date.parse(LIMITS["yeni.sert"]) ? NEW : []);
// A/B-də tutuşdurulan ölçülər (ana səhifənin soyuq açılışı).
const AB_KEYS = { fcp: "ilk boya", first: "görünmə", preFcpLongTaskSum: "boyadan əvvəl uzun işlər", lcp: "LCP", lt: "uzun işlər (5 s)" };

const num = x => typeof x === "number" && Number.isFinite(x);
const median = xs => { const v = xs.filter(num).sort((a, b) => a - b); return v.length ? v[Math.floor((v.length - 1) / 2)] : null; };
const spread = xs => { const v = xs.filter(num); return v.length ? Math.max(...v) - Math.min(...v) : null; };
const fmt = v => v == null ? "-" : num(v) ? (Number.isInteger(v) ? String(v) : String(Math.round(v * 1000) / 1000)) : String(v);
const sleep = ms => new Promise(r => setTimeout(r, ms));
const get = (url, init = {}) => fetch(url, { redirect: "follow", ...init, signal: AbortSignal.timeout(init.timeout || 20000), headers: { "user-agent": UA_TOOL, ...(init.headers || {}) } });

// ---- nəticələr -------------------------------------------------------------------------------------------------------------------
const rows = [], fail = [], warn = [];
function add(kind, name, r, over = [], soft = []) {
  const row = { kind, name, ...r, over, soft };
  rows.push(row);
  if (over.length) fail.push(`${kind} ${name}: ${over.join(", ")}`);
  if (soft.length) warn.push(`${kind} ${name}: ${soft.join(", ")}`);
  console.log(line(row));
  return row;
}
function line(r) {
  const p = (v, w) => String(v == null ? "-" : v).padStart(w);
  const tail = (r.over.length ? "  ✗ " + r.over.join("; ") : "") + (r.soft.length ? "  ⚠ " + r.soft.join("; ") : "");
  const head = `${r.kind.padEnd(7)} ${r.name.slice(0, 42).padEnd(42)}`;
  if (r.kind === "cold") return `${head} görünmə ${p(r.first, 5)} fcp ${p(r.fcp, 5)} css→ ${p(r.fcpAfterCss, 4)} öncə ${p(r.preFcpLongTaskMax, 4)}/${p(r.preFcpLongTaskSum, 4)} lcp ${p(r.lcp, 5)} cls ${p(fmt(r.cls), 5)} uzun ${p(r.lt, 4)}/${p(r.ltMax, 4)} sorğu ${p(r.requests, 3)} ${p(Math.round((r.bytes || 0) / 1024), 4)} KB slayd ${p(r.heroLoads, 1)} dom ${p(r.dom, 5)}${r.fallback ? " (köhnə görünmə yoxlaması)" : ""}${tail}`;
  if (r.kind === "ab") return `${head} ${Object.entries(r.cmp).map(([k, c]) => `${AB_KEYS[k]} ${c.A}→${c.B} (hədd +${c.tol})`).join("  ")}${tail}`;
  if (r.kind === "bfcache") return `${head} ${r.value}${r.ilk ? ` (yavaşlatma ilə: ${r.ilk})` : ""}${num(r.back) ? `  geri ${r.back} ms` : ""}${tail}`;
  if (r.kind === "ucuncu") return `${head} ${r.status}${r.location ? " → " + r.location : ""}${tail}`;
  if (r.kind === "sehife") return `${head} v${r.ver}: köhnə ${r.old}/${r.total} (${(r.share * 100).toFixed(1)}%)  nümunə ${(r.sample || []).length}: app.min.js ${(r.sample || []).filter(s => s.min).length}, app.js ${(r.sample || []).filter(s => s.src).length}${r.bump && r.bump.at ? `  versiya artımı ${r.bump.at}` : ""}${tail}`;
  if (r.kind === "data") return `${head} ${p(r.bytes, 7)} B gzip / ${r.limit} (${r.file || "-"}, ${r.wire || "-"})${tail}`;
  return `${head} ilk ${p(r.first, 5)} kadr ${p(r.vis, 5)} dom0 ${p(r.firstDom, 4)} sabit ${p(r.stable, 5)} uzun ${p(r.lt ?? 0, 4)}/${p(r.ltMax ?? 0, 4)} dom ${p(r.dom, 5)}${(r.net || []).length ? "  şəbəkə: " + r.net.join(", ").slice(0, 120) : ""}${tail}`;
}

// ---- Chrome / CDP ----------------------------------------------------------------------------------------------------------------
function chromePath() {
  if (process.env.CHROME) return process.env.CHROME;
  for (const p of ["C:/Program Files/Google/Chrome/Application/chrome.exe", "/usr/bin/google-chrome", "/usr/bin/google-chrome-stable", "/usr/bin/chromium", "/usr/bin/chromium-browser"]) if (fs.existsSync(p)) return p;
  throw new Error("Chrome tapılmadı (CHROME=...)");
}
// Chrome yavaş runner-də (GitHub qəzasından sonra, 2026-11-09) 10 s-də açılmadı: xəta atıldı, amma açıq qalan proses işi 40 dəqiqə
// asılı saxladı. İndi 30 s gözləyir, alınmasa prosesi öldürüb bir dəfə yenidən cəhd edir; main xətası prosesi dərhal bitirir.
async function launch(attempt = 1) {
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), "speed-"));
  const proc = spawn(chromePath(), ["--headless=new", "--remote-debugging-port=0", `--user-data-dir=${dir}`, "--no-first-run", "--no-default-browser-check", "--disable-extensions", "--mute-audio", "--no-sandbox", "--enable-features=BackForwardCache", "about:blank"], { stdio: "ignore" });
  const portFile = path.join(dir, "DevToolsActivePort");
  for (let i = 0; i < 300 && !fs.existsSync(portFile) && proc.exitCode === null; i++) await sleep(100);
  if (!fs.existsSync(portFile)) {
    try { proc.kill("SIGKILL"); } catch {}
    if (attempt < 2) { console.log("Chrome 30 s-də açılmadı, yenidən cəhd…"); return launch(attempt + 1); }
    throw new Error("Chrome açılmadı (DevToolsActivePort yoxdur)");
  }
  const [port, wsPath] = fs.readFileSync(portFile, "utf8").split("\n");
  return { proc, dir, ws: `ws://127.0.0.1:${port}${wsPath.trim()}` };
}
function cdp(url) {
  const ws = new WebSocket(url);
  let id = 0; const wait = new Map(), handlers = [];
  ws.onmessage = ev => {
    const m = JSON.parse(ev.data);
    if (m.id && wait.has(m.id)) { const { ok, no } = wait.get(m.id); wait.delete(m.id); m.error ? no(new Error(m.error.message)) : ok(m.result); }
    else handlers.forEach(h => h(m));
  };
  const send = (method, params = {}, sessionId) => new Promise((ok, no) => { const i = ++id; wait.set(i, { ok, no }); ws.send(JSON.stringify({ id: i, method, params, sessionId })); });
  return new Promise(ok => { ws.onopen = () => ok({ send, on: h => handlers.push(h), close: () => ws.close() }); });
}

// Sənəd başlanğıcında qoyulan müşahidəçi (Page.addScriptToEvaluateOnNewDocument, hər yeni sənəddə): ilk boya (FCP), yerləşdirmə
// sürüşmələri (CLS — oxucu girişi olmayanların cəmi), LCP, uzun tapşırıqlar (başlanğıc vaxtı ilə — ilk boyadan əvvəlkilər ayrıca),
// geri-irəli keşindən qayıdış (pageshow.persisted) və görünən ilk məzmun: #view-da ilk xəbər kartı / slayd / cədvəl (xəbər səhifəsində
// h1) ekrana düşən an — IntersectionObserver ilə, məcburi yerləşdirməsiz (köhnə alət hər 50 ms checkVisibility() soruşurdu və
// yüklənmənin içində yerləşdirmə məcbur edirdi). CSS gəlməmiş səhifə boyanmır: ondan əvvəl heç nə görünən sayılmır.
const MON = `(() => {
  const m = window.__m = { lt: [], fcp: null, lcp: null, cls: 0, visible: null, h1: null, persisted: false, cssAt: null };
  const obs = (type, fn) => { try { new PerformanceObserver(l => l.getEntries().forEach(fn)).observe({ type, buffered: true }); } catch (e) {} };
  obs("longtask", e => m.lt.push([Math.round(e.startTime), Math.round(e.duration)]));
  obs("paint", e => { if (e.name === "first-contentful-paint") m.fcp = Math.round(e.startTime); });
  obs("layout-shift", e => { if (!e.hadRecentInput) m.cls += e.value; });
  obs("largest-contentful-paint", e => { m.lcp = Math.round(e.startTime); });
  addEventListener("pageshow", e => { if (e.persisted) m.persisted = true; });
  const SEL = "article,.card,.hero-main,.tm-sec,.tm-table,table,h1", pending = [];
  const cssReady = () => m.cssAt != null || !!(document.querySelector('link[href*="app.css"]') || {}).sheet;
  document.addEventListener("load", e => { const l = e.target; if (l && l.rel === "stylesheet" && /app\\.css/.test(l.href || "")) { m.cssAt = Math.round(performance.now()); pending.splice(0).forEach(el => io.observe(el)); } }, true);
  const story = () => /^#\\/xeber\\//.test(location.hash);
  const done = () => m.visible != null && (m.h1 != null || !story());
  const io = new IntersectionObserver(es => {
    for (const e of es) {
      if (!e.isIntersecting) continue;
      const el = e.target; io.unobserve(el);
      if (!cssReady()) { pending.push(el); continue; }
      if (el.closest(".skel,.skeleton,.sr-only")) continue;
      const k = el.tagName === "H1" ? "h1" : "visible";
      if (m[k] == null && (k === "visible" || el.textContent.trim())) m[k] = Math.round(e.time);
    }
    if (done()) { io.disconnect(); mo.disconnect(); }
  });
  const look = n => {
    if (n.nodeType !== 1 || done()) return;
    const scope = n.closest("#view") ? n : n.querySelector("#view");
    if (!scope) return;
    if (scope.matches(SEL)) io.observe(scope);
    scope.querySelectorAll(SEL).forEach(el => io.observe(el));
  };
  const mo = new MutationObserver(rs => { for (const r of rs) for (const n of r.addedNodes) look(n); });
  mo.observe(document, { childList: true, subtree: true });
})()`;
// +5 s-də oxunur: ilk boya, app.css-in gəlişi (resource timing responseEnd), ilk boyadan əvvəlki uzun tapşırıqlar, CLS, LCP, DOM.
const READ = `(() => {
  const m = window.__m || {}, lt = m.lt || [];
  const css = performance.getEntriesByType("resource").find(e => /\\/assets\\/app\\.css/.test(e.name));
  const pre = m.fcp == null ? [] : lt.filter(x => x[0] < m.fcp).map(x => x[1]);
  return { fcp: m.fcp, lcp: m.lcp, cls: Math.round((m.cls || 0) * 1000) / 1000, visible: m.visible, h1: m.h1, cssEnd: css ? Math.round(css.responseEnd) : null,
    preFcpLongTaskMax: Math.max(0, ...pre), preFcpLongTaskSum: pre.reduce((a, b) => a + b, 0),
    lt: lt.reduce((a, x) => a + x[1], 0), ltMax: Math.max(0, ...lt.map(x => x[1])), dom: document.querySelectorAll("#view *").length,
    navType: (performance.getEntriesByType("navigation")[0] || {}).type, persisted: !!m.persisted };
})()`;
// Köhnə görünmə yoxlaması (ehtiyat: IntersectionObserver 3 s görmədisə, saniyədə bir): ekranda görünən ilk məzmun — xəbər kartı, slayd
// və ya cədvəl (gizli hazır HTML və skelet sayılmır), yalnız app.css yüklənəndən sonra.
const OLD_VISIBLE = `(() => { const v = document.querySelector("#view"), css = (document.querySelector('link[href*="app.css"]') || {}).sheet; return !!v && !!css && [...v.querySelectorAll("article,.card,.hero-main,.tm-sec,.tm-table,table")].some(e => e.checkVisibility() && !e.closest(".skel,.skeleton")) && Math.round(performance.now()); })()`;

// Səhifəyə yerləşən ölçü köməkçisi (keçidlər): keçidi başladır, #view-da ilk dəyişikliyi və sabitləşməni, uzun işləri qeyd edir.
const HELPER = `(() => {
  if (window.__nav) return;
  window.__lt = [];
  try { new PerformanceObserver(l => l.getEntries().forEach(e => __lt.push(e.duration))).observe({ type: "longtask", buffered: true }); } catch {}
  performance.setResourceTimingBufferSize(5000);
  window.__nav = async (fn, quiet = 600, max = 8000) => {
    const v = document.querySelector("#view"); const t0 = performance.now(); const lt0 = __lt.length;
    performance.clearResourceTimings();
    let first = null, last = t0, firstDom = null, vis = null;
    const mo = new MutationObserver(() => { const t = performance.now(); if (first == null) { first = t; firstDom = v.querySelectorAll("*").length; requestAnimationFrame(() => setTimeout(() => { vis = performance.now(); })); } last = t; });
    mo.observe(v, { childList: true, subtree: true, characterData: true });
    fn();
    while (performance.now() - t0 < max) { await new Promise(r => setTimeout(r, 30)); if (first != null && vis != null && performance.now() - last > quiet) break; }
    mo.disconnect();
    const net = performance.getEntriesByType("resource").filter(e => !/wsrv\\.nl|\\.(jpe?g|png|webp|gif|svg)(\\?|$)|goatcounter|ytimg|yandex|googlevideo/.test(e.name));
    const lts = __lt.slice(lt0);
    return { first: first == null ? null : Math.round(first - t0), vis: vis == null ? null : Math.round(vis - t0), firstDom, stable: Math.round(last - t0), lt: Math.round(lts.reduce((s, x) => s + x, 0)), ltMax: Math.round(Math.max(0, ...lts)),
      dom: v.querySelectorAll("*").length, title: (v.querySelector("h1,h2")?.textContent || "").trim().slice(0, 40),
      net: net.map(e => e.name.replace(location.origin, "").replace(/\\?.*/, "") + " " + Math.round(e.duration) + "ms") };
  };
})()`;

// Slayder şəklinin açarı: wsrv.nl sorğusunda url= parametri (640 və 800 px variantları eyni şəkildir), başqa hostda ünvanın özü.
const heroKey = u => { try { const x = new URL(u); return x.hostname === "wsrv.nl" ? x.searchParams.get("url") : x.origin + x.pathname; } catch { return null; } };
const heroCache = new Map();
async function heroOf(base) { // index.html-dəki hazır slayderin ilk şəkli
  if (heroCache.has(base)) return heroCache.get(base);
  let key = null;
  try { const m = (await (await get(base)).text()).match(/<article class="hero-main"[\s\S]*?<img src="([^"]+)"/); if (m) key = heroKey(m[1].replace(/&amp;/g, "&")); } catch {}
  heroCache.set(base, key);
  return key;
}
async function storyOf(base) { // paylaşılan xəbər keçidi: ilk lentin ilk xəbəri, h = yayım saatı (UTC, iiaagg ss)
  try {
    const d = await (await get(base + "data/first.json")).json();
    const a = (d.articles || []).find(a => /^[0-9a-f]{16}$/.test(String(a.id)) && /^\d{4}-\d\d-\d\dT\d\d/.test(a.publishedAt || ""));
    if (!a) return null;
    const p = a.publishedAt;
    return { hash: `#/xeber/${a.id}?b=${encodeURIComponent(a.category || "gundem")}&h=${p.slice(2, 4)}${p.slice(5, 7)}${p.slice(8, 10)}${p.slice(11, 13)}`, title: a.title };
  } catch { return null; }
}

// ---- gecə yoxlamaları (brauzersiz) ---------------------------------------------------------------------------------------------------
// Səhifə açıq olarkən soruşulan hər xarici ünvan (tests/fixtures/ucuncu-terefler.json, vaxt açılış/sonra) yönləndirməməlidir: 3xx cavab
// səhifəni bfcache-dən çıxarır (mənbədən geri qayıdış 667 ms, 2026-11-09). Nümunə sorğu qeyddəki «numune» ünvanıdır, redirect: "manual".
async function thirdParty() {
  const reg = JSON.parse(fs.readFileSync(path.join(ROOT, "tests/fixtures/ucuncu-terefler.json"), "utf8"));
  const d = new Date(), tarix = `${String(d.getUTCDate()).padStart(2, "0")}-${String(d.getUTCMonth() + 1).padStart(2, "0")}-${d.getUTCFullYear()}`;
  for (const [host, r] of Object.entries(reg)) {
    if (host === "_" || !["açılış", "sonra"].includes(r.vaxt)) continue;
    const url = String(r.numune || "").replace("{tarix}", tarix);
    if (!url) { add("ucuncu", host, { status: null }, [], ["nümunə sorğu yoxdur (tests/fixtures/ucuncu-terefler.json → numune)"]); continue; }
    let res;
    try { res = await get(url, { redirect: "manual", timeout: 15000 }); } catch (e) { add("ucuncu", host, { url, status: "xəta" }, [], [`sorğu alınmadı: ${e.message}`]); continue; }
    const location = res.headers.get("location"), over = [], soft = [];
    if (res.status >= 300 && res.status < 400) (r.yonlendirir === false ? over : soft).push(`${res.status} → ${location}: səhifə açıq olarkən soruşulan ünvan yönləndirir (bfcache sönür); yönləndirməyən ünvanı tapın və ya sorğunu klikə keçirin`);
    else if (res.status >= 400) soft.push(`cavab ${res.status}`);
    add("ucuncu", host, { url, status: res.status, location }, over, soft);
  }
}
// STORY_VER son N saatda artıbmı (köhnə səhifələrin yazılması dövrədə STORY_REWRITE-la gedir): updater.py-a toxunan son commit-lər,
// hər birinin valideynindəki versiya ilə tutuşdurulur. Bilinməsə null.
async function lastBump(ver) {
  const since = new Date(Date.now() - LIMITS["sehife.saat"] * 3600e3).toISOString();
  const headers = { accept: "application/vnd.github+json" }; if (TOKEN) headers.authorization = "Bearer " + TOKEN;
  const commits = await (await get(`https://api.github.com/repos/${REPO}/commits?path=updater.py&since=${since}&per_page=30`, { headers })).json();
  if (!Array.isArray(commits)) return null;
  for (const c of commits) {
    const parent = c.parents && c.parents[0] && c.parents[0].sha; if (!parent) continue;
    const v = Number(((await (await get(`https://raw.githubusercontent.com/${REPO}/${parent}/updater.py`)).text()).match(/STORY_VER, STORY_REWRITE = (\d+)/) || [])[1]);
    if (v && v < ver) return { at: c.commit.committer.date, recent: true };
  }
  return { at: null, recent: false };
}
// xeber/<id>/ səhifələri: indeksdə versiyası updater.py STORY_VER-dən köhnə olanların payı; 10 təsadüfi səhifə app.min.js yükləməli,
// app.js yox (2026-11-08: şablon dəyişmiş, versiya artmamışdı — ~3 400 səhifə Google-dan gələnə 221 KB mənbə kodu verirdi).
async function pagesCheck() {
  const ver = Number((fs.readFileSync(path.join(ROOT, "updater.py"), "utf8").match(/STORY_VER, STORY_REWRITE = (\d+)/) || [])[1]);
  let idx;
  try { idx = await (await get(BASE + "xeber/index.json")).json(); } catch (e) { return add("sehife", "xeber/index.json", { ver, total: 0, old: 0, share: 0 }, [], [`indeks alınmadı: ${e.message}`]); }
  const ids = Object.keys(idx), verOf = id => Array.isArray(idx[id]) && idx[id].length > 3 ? Number(idx[id][3]) : 1;
  const old = ids.filter(id => verOf(id) < ver), share = ids.length ? old.length / ids.length : 0;
  const sample = [], over = [], soft = [];
  for (const id of ids.map(x => [Math.random(), x]).sort((a, b) => a[0] - b[0]).slice(0, 10).map(x => x[1])) {
    try { const html = await (await get(BASE + "xeber/" + id + "/")).text(); sample.push({ id, ver: verOf(id), min: /assets\/app\.min\.js/.test(html), src: /assets\/app\.js["?]/.test(html) }); }
    catch (e) { sample.push({ id, ver: verOf(id), error: e.message }); }
  }
  // İndeksdə cari versiyalı, amma köhnə şablonlu səhifə = şablon dəyişib, STORY_VER artmayıb (2026-11-08 hadisəsi): dərhal qırmızı.
  // Köhnə versiyalı səhifələrin app.js yükləməsi gözləniləndir — onları aşağıdakı pay qaydası (24 saat) tutur.
  const bad = sample.filter(s => s.ver >= ver && !s.error && (!s.min || s.src));
  if (bad.length) over.push(`${bad.length} səhifə indeksdə cari (v${ver}), amma şablon köhnə (app.min.js yox / app.js var): ${bad.map(s => s.id).join(", ")} — şablon dəyişib, STORY_VER artmayıb`);
  let bump = null;
  if (share > LIMITS["sehife.kohne"]) {
    bump = await lastBump(ver).catch(() => null);
    const msg = `köhnə şablon ${(share * 100).toFixed(1)}% > ${LIMITS["sehife.kohne"] * 100}% (${old.length}/${ids.length} səhifə v<${ver})`;
    if (bump && bump.recent) soft.push(`${msg} — versiya ${bump.at} artıb, ${LIMITS["sehife.saat"]} saat gözlənir`);
    else if (!bump) soft.push(`${msg} — versiya artımının vaxtı bilinmir (GitHub API; GH_TOKEN?)`);
    else over.push(`${msg} — son ${LIMITS["sehife.saat"]} saatda versiya artmayıb, köhnə səhifələr yenidən yazılmır (updater.py STORY_REWRITE)`);
  }
  add("sehife", "xeber/<id>/ şablon versiyası", { ver, total: ids.length, old: old.length, share: Math.round(share * 1000) / 1000, sample, bump }, over, soft);
}
// Canlı məlumat faylının teldəki gzip ölçüsü (Accept-Encoding: gzip; server sıxmasa yerli gzip).
function gzSize(url) {
  return new Promise((ok, no) => {
    const req = (url.startsWith("https") ? https : http).get(url, { headers: { "accept-encoding": "gzip", "user-agent": UA_TOOL } }, res => {
      const gz = (res.headers["content-encoding"] || "") === "gzip"; let n = 0; const chunks = [];
      res.on("data", d => { n += d.length; if (!gz) chunks.push(d); });
      res.on("end", () => ok({ status: res.statusCode, bytes: gz ? n : zlib.gzipSync(Buffer.concat(chunks)).length, wire: gz ? "gzip" : "sıxılmamış (yerli gzip)" }));
    });
    req.on("error", no); req.setTimeout(20000, () => req.destroy(new Error("vaxt bitdi")));
  });
}
async function dataCheck() {
  // Paylaşma siyahısının hissələri nüsxədəki data/paylas/-dan (hissə sayı dəyişə bilər: 32 → 256), canlıdan 8-8 paralel.
  const parts = () => { try { const f = fs.readdirSync(path.join(ROOT, "data/paylas")).filter(f => /^\d+\.json$/.test(f)).map(f => "data/paylas/" + f); if (f.length) return f; } catch {} return Array.from({ length: 32 }, (_, i) => `data/paylas/${i}.json`); };
  for (const [key, limit] of Object.entries(B.melumat)) {
    const files = key === "paylas.json.gz" ? parts() : ["data/" + key.replace(/\.gz$/, "")];
    let worst = { bytes: 0, file: null, wire: null }; const soft = [];
    for (let i = 0; i < files.length; i += 8) {
      await Promise.all(files.slice(i, i + 8).map(async f => {
        try { const r = await gzSize(BASE + f); if (r.status !== 200) { soft.push(`${f}: ${r.status}`); return; } if (r.bytes > worst.bytes) worst = { bytes: r.bytes, file: f, wire: r.wire }; }
        catch (e) { soft.push(`${f}: ${e.message}`); }
      }));
    }
    add("data", key, { ...worst, limit }, worst.bytes >= limit ? [`${worst.file} ${worst.bytes} B gzip ≥ ${limit}: updater.py-də sətir sayı və ya sahə artıb — faylı yox, qaydanı kiçildin (tests/budce.test.cjs)`] : [], soft);
  }
}

// ---- brauzer ölçüləri ---------------------------------------------------------------------------------------------------------------
async function browser() {
  const { proc, dir, ws } = await launch();
  const c = await cdp(ws);
  try {
    const { targetId } = await c.send("Target.createTarget", { url: "about:blank" });
    const { sessionId: s } = await c.send("Target.attachToTarget", { targetId, flatten: true });
    const send = (m, p) => c.send(m, p, s);
    // Şəbəkə hadisələri (sorğu sayı, bayt, slayd şəkli) və bfcache səbəbləri.
    const net = { reqs: new Map(), reset() { this.reqs = new Map(); }, count() { return this.reqs.size; }, bytes() { let n = 0; for (const r of this.reqs.values()) n += r.bytes; return n; }, hero(key) { let n = 0; for (const r of this.reqs.values()) if (key && heroKey(r.url) === key && !r.cached) n++; return n; } }; // yalnız şəbəkədən gələn yükləmə: hazır ilk ekran təzə məlumatla əvəz olunanda eyni şəkil brauzerin keşindən (0 bayt) yenidən soruşulur — o sayılmır (2026-11-09)
    const bf = [], navs = []; // bfcache səbəbləri; əsas çərçivənin naviqasiyaları (type: BackForwardCacheRestore = keşdən qayıdış)
    c.on(m => {
      if (m.sessionId !== s) return;
      if (m.method === "Network.requestWillBeSent") { if (!net.reqs.has(m.params.requestId)) net.reqs.set(m.params.requestId, { url: m.params.request.url, bytes: 0 }); }
      else if (m.method === "Network.requestServedFromCache") { const r = net.reqs.get(m.params.requestId); if (r) r.cached = true; }
      else if (m.method === "Network.responseReceived") { const r = net.reqs.get(m.params.requestId); if (r && (m.params.response.fromDiskCache || m.params.response.fromPrefetchCache || m.params.response.fromServiceWorker)) r.cached = true; }
      else if (m.method === "Network.loadingFinished") { const r = net.reqs.get(m.params.requestId); if (r) { r.bytes = m.params.encodedDataLength || 0; if (!r.bytes) r.cached = true; } }
      else if (m.method === "Page.backForwardCacheNotUsed") bf.push(m.params);
      else if (m.method === "Page.frameNavigated" && !m.params.frame.parentId) navs.push({ url: m.params.frame.url, type: m.params.type, at: Date.now() });
    });
    await send("Page.enable"); await send("Runtime.enable"); await send("Network.enable");
    await send("Page.addScriptToEvaluateOnNewDocument", { source: MON });
    await send("Emulation.setDeviceMetricsOverride", { width: 412, height: 915, deviceScaleFactor: 2.625, mobile: true });
    await send("Emulation.setUserAgentOverride", { userAgent: UA_PHONE });
    await send("Emulation.setTouchEmulationEnabled", { enabled: true, maxTouchPoints: 5 });
    await send("Emulation.setEmulatedMedia", { features: [{ name: "hover", value: "none" }, { name: "pointer", value: "coarse" }, { name: "any-hover", value: "none" }] });
    await send("Emulation.setCPUThrottlingRate", { rate: CPU });
    await send("Network.emulateNetworkConditions", NET_PHONE);
    const evaluate = async (expr, timeout = 30000) => {
      const r = await Promise.race([send("Runtime.evaluate", { expression: expr, awaitPromise: true, returnByValue: true }), sleep(timeout).then(() => ({ result: { value: { timeout: true } } }))]);
      if (r.exceptionDetails) throw new Error(r.exceptionDetails.exception?.description || r.exceptionDetails.text);
      return r.result.value;
    };

    // 1) Soyuq açılış: ünvan → ilk xəbər kartı ekranda; +5 s-də ilk boya, CLS, LCP, uzun tapşırıqlar, sorğular.
    // Əvvəl 404.html (proses isti: şrift, GPU, JIT; sayğac bloklu), sonra ilk ziyarət kimi: brauzer keşi, xidmət işçisi və yaddaş silinir
    // (yoxsa ikinci «soyuq» açılış əslində isti olur).
    const park = async base => { await send("Network.setBlockedURLs", { urls: ANALYTICS }); await send("Page.navigate", { url: base + "404.html" }); await sleep(600); await send("Network.setBlockedURLs", { urls: [] }); };
    const cold = async (base, hash, { warm = false, key = "visible", hero = null } = {}) => {
      await park(base);
      if (!warm) { await send("Network.clearBrowserCache"); await send("Storage.clearDataForOrigin", { origin: new URL(base).origin, storageTypes: "all" }).catch(() => {}); }
      net.reset(); bf.length = 0;
      const t0 = Date.now();
      await send("Page.navigate", { url: base + hash });
      let shown = null, fallback = false;
      for (let i = 1; i <= 150 && shown == null; i++) {
        await sleep(100);
        const v = await evaluate(`window.__m && __m[${JSON.stringify(key)}]`).catch(() => null);
        if (num(v)) shown = v;
        else if (key === "visible" && i >= 30 && i % 10 === 0) { const o = await evaluate(OLD_VISIBLE).catch(() => false); if (num(o)) { shown = o; fallback = true; } }
      }
      await sleep(Math.max(300, t0 + 5000 - Date.now()));
      const m = await evaluate(READ);
      const r = { first: shown, ...m, requests: net.count(), bytes: net.bytes(), heroLoads: hero ? net.hero(hero) : null };
      r.fcpAfterCss = num(m.fcp) && num(m.cssEnd) ? m.fcp - m.cssEnd : null;
      if (fallback) r.fallback = true;
      return r;
    };
    // Büdcə yoxlaması (soyuq sətir). only: yalnız bu açarlar (kompüter keçidi: cls, heroLoads).
    const coldOver = (r, o) => {
      const over = [], soft = [], want = k => !o.only || o.only.includes(k);
      const chk = (key, val, lim, label) => { if (!num(val) || !num(lim) || val <= lim) return; (WARN_ONLY.has(key) ? soft : over).push(`${label} ${fmt(val)} > ${fmt(lim)}`); };
      const storyRow = o.key === "h1", coldKey = storyRow ? "storyCold" : "cold";
      if (want("cold")) { chk(coldKey, r.first, o.limit ?? LIMITS[coldKey], "ekrana çıxma"); if (r.first == null) (WARN_ONLY.has(coldKey) ? soft : over).push("məzmun görünmədi"); }
      if (want("fcp")) { chk("fcp", r.fcp, LIMITS.fcp, "ilk boya"); chk("fcpAfterCss", r.fcpAfterCss, LIMITS.fcpAfterCss, "CSS-dən ilk boyaya"); chk("preFcpLongTaskMax", r.preFcpLongTaskMax, LIMITS.preFcpLongTaskMax, "boyadan əvvəl ən uzun iş"); chk("preFcpLongTaskSum", r.preFcpLongTaskSum, LIMITS.preFcpLongTaskSum, "boyadan əvvəl uzun işlər"); }
      if (want("cls")) chk("cls", r.cls, o.cls ?? LIMITS.cls, "CLS");
      if (want("heroLoads") && o.hero) chk("heroLoads", r.heroLoads, LIMITS.heroLoads, "slayd şəkli yükləmə");
      if (want("requests")) chk("requests", r.requests, LIMITS.requests, "sorğu");
      if (want("dom")) chk("dom", r.dom, LIMITS.dom, "DOM");
      return { over, soft };
    };
    const MED = ["first", "fcp", "lcp", "cls", "cssEnd", "fcpAfterCss", "preFcpLongTaskMax", "preFcpLongTaskSum", "lt", "ltMax", "dom", "requests", "bytes", "heroLoads"];
    const slim = r => ({ first: r.first, fcp: r.fcp, lcp: r.lcp, cls: r.cls, preFcpLongTaskSum: r.preFcpLongTaskSum, lt: r.lt, requests: r.requests, heroLoads: r.heroLoads });
    const rowOf = (name, runs, o = {}) => {
      const r = { ...runs[runs.length - 1] };
      for (const k of MED) r[k] = median(runs.map(x => x[k]));
      if (runs.length > 1) r.runs = runs.map(slim);
      const { over, soft } = coldOver(r, o);
      return add("cold", name, r, over, soft);
    };
    const coldRow = async (name, hash, o = {}) => {
      const runs = [];
      for (let i = 0; i < (o.reps || REPS); i++) runs.push(await cold(o.base || BASE, hash, o));
      return rowOf(name, runs, o);
    };
    // Mənbəyə gedib qayıtmaq: ana səhifə açıq → 404.html (mənbə yerinə) → 1 s → tarixçə ilə geri. Chrome səhifəni geri-irəli keşindən
    // qaytarmalıdır (pageshow.persisted → «restored»); qaytarmasa Page.backForwardCacheNotUsed səbəbləri (NetworkRequestRedirected,
    // ServiceWorkerClaim …). Şəbəkə yavaşlatması özü mane olsa, addım yavaşlatmasız təkrarlanır və ikinci nəticə yazılır.
    const bfcache = async () => {
      const attempt = async () => {
        bf.length = 0;
        await send("Network.setBlockedURLs", { urls: ANALYTICS });
        await send("Page.navigate", { url: BASE + "404.html" }); await sleep(1000);
        const { currentIndex, entries } = await send("Page.getNavigationHistory");
        const back = entries[currentIndex - 1];
        if (!back) return { value: "tarixçə yoxdur" };
        const t0 = Date.now(); let m = {}; navs.length = 0;
        await send("Page.navigateToHistoryEntry", { entryId: back.id });
        // Qayıdış anı naviqasiya hadisəsindən (səhifənin əsas axını qayıdan kimi məşğul ola bilər, evaluate gec cavab verir).
        for (let i = 0; i < 60; i++) { await sleep(50); m = await evaluate(`({ persisted: !!(window.__m && __m.persisted), navType: (performance.getEntriesByType("navigation")[0] || {}).type, visible: window.__m && __m.visible })`).catch(() => ({})); if (m.persisted || (m.navType === "back_forward" && num(m.visible))) break; }
        await sleep(500);
        await send("Network.setBlockedURLs", { urls: [] });
        const ev = navs.find(n => n.url.startsWith(BASE) && !n.url.includes("404.html"));
        const restored = (ev && ev.type === "BackForwardCacheRestore") || m.persisted;
        const reasons = [...new Set(bf.flatMap(e => (e.notRestoredExplanations || []).map(x => x.reason)))];
        return { value: reasons.length ? reasons.join(",") : restored ? "restored" : m.navType === "back_forward" ? "back_forward (keşsiz, səbəb bildirilmədi)" : "naməlum", navType: ev ? ev.type : m.navType, back: ev ? ev.at - t0 : null };
      };
      let r = await attempt();
      if (r.value !== LIMITS.bfcache) {
        const ilk = r.value;
        await send("Network.emulateNetworkConditions", NET_FREE);
        await cold(BASE, "", {});
        r = { ...(await attempt()), ilk, yavaslatmasiz: true };
        await send("Network.emulateNetworkConditions", NET_PHONE);
      }
      const bad = r.value !== LIMITS.bfcache ? [`geri qayıdış keşdən deyil: ${r.value}`] : [];
      add("bfcache", "ana səhifə → mənbə → geri", r, WARN_ONLY.has("bfcache") ? [] : bad, WARN_ONLY.has("bfcache") ? bad : []);
    };

    const hero = await heroOf(BASE), story = await storyOf(BASE);
    // A/B: baza nüsxəsi eyni anda, növbə ilə A, B, A, B, A, B (hər biri REPS dəfə) — dəqiqənin səs-küyü hər ikisinə eyni düşür.
    // Qırmızı: median(B) − median(A) > max(spread(A), ab.pay × median(A), ab.min); spread = A ölçülərinin max − min.
    // Eyni nüsxə iki portda (A/A) qırmızı olmamalıdır. Ana səhifənin soyuq sətri B ölçülərindəndir (ayrıca 3 açılış artıq iş idi).
    if (AB) {
      const runs = { A: [], B: [] }, heroA = await heroOf(AB);
      for (const side of ["A", "B", "A", "B", "A", "B"]) for (let i = 0; i < REPS; i++) runs[side].push(await cold(side === "A" ? AB : BASE, "", { hero: side === "A" ? heroA : hero }));
      rowOf("ana səhifə", runs.B, { hero });
      const over = [], cmp = {};
      for (const [k, label] of Object.entries(AB_KEYS)) {
        const a = runs.A.map(r => r[k]), b = runs.B.map(r => r[k]), mA = median(a), mB = median(b);
        if (!num(mA) || !num(mB)) continue;
        const tol = Math.round(Math.max(spread(a), LIMITS["ab.pay"] * mA, LIMITS["ab.min"]));
        cmp[k] = { A: mA, B: mB, tol, spreadA: spread(a) };
        if (mB - mA > tol) over.push(`${label} ${mB} > baza ${mA} + ${tol}`);
      }
      add("ab", "ana səhifə: baza (A) → bu nüsxə (B)", { base: AB, cmp, runsA: runs.A.map(slim), runsB: runs.B.map(slim) }, over);
    } else await coldRow("ana səhifə", "", { hero });
    await bfcache(); // səhifə bu nüsxənin ana səhifəsidir (A/B-də sonuncu B ölçüsü)
    for (const [h, name] of [["#/bolme/idman", "idman (birbaşa keçid)"], ["#/bolme/gundem", "gündəm (birbaşa keçid)"], ["#/komanda/premyer-liqa", "liqa (birbaşa keçid)"]]) await coldRow(name, h);
    if (story) await coldRow("paylaşılan xəbər", story.hash, { key: "h1" }); else add("cold", "paylaşılan xəbər", { first: null }, [], ["data/first.json-dan xəbər tapılmadı"]);

    if (COLD_ONLY) return;
    // Təkrar ziyarət (tətbiq quraşdırılıb, xidmət işçisi keşi ilə): telefon sahibinin hər gün gördüyü açılış. Əvvəl işçi tam qurulsun.
    await cold(BASE, "", { warm: true }); await sleep(3000);
    await coldRow("ana səhifə (təkrar)", "", { warm: true, reps: 1, only: ["cold", "fcp", "cls", "dom"] });
    await coldRow("idman (təkrar)", "#/bolme/idman", { warm: true, reps: 1, only: ["cold", "fcp", "cls", "dom"] });
    await sleep(2500);
    await evaluate(HELPER);

    const navOver = (r, limit) => {
      const over = [], shown = r.vis ?? r.first;
      if (limit && shown != null && shown > limit && !(r.net || []).length) over.push(`ekrana çıxma ${shown} > ${limit}`);
      if (r.first == null) over.push("məzmun dəyişmədi");
      if (r.ltMax > LIMITS.longTask) over.push(`uzun iş ${r.ltMax} > ${LIMITS.longTask}`);
      if (r.dom > LIMITS.dom) over.push(`DOM ${r.dom} > ${LIMITS.dom}`);
      return over;
    };
    const nav = async (kind, name, js, limit, quiet, from) => {
      const runs = [];
      for (let i = 0; i < (from ? REPS : 1); i++) { if (from && i) await go(from, 300); runs.push(await evaluate(`__nav(() => { ${js} }, ${quiet || 600})`)); }
      const r = { ...runs[runs.length - 1] };
      for (const k of ["first", "vis", "firstDom", "stable", "lt", "ltMax"]) r[k] = median(runs.map(x => x[k]));
      add(kind, name, r, navOver(r, limit));
    };
    const go = async (hash, wait = 400) => { await evaluate(`location.hash = ${JSON.stringify(hash)}`); await sleep(wait); };

    // 2) Bölmələr və xidmət səhifələri (tətbiq daxilində keçid).
    const cats = await evaluate(`[...document.querySelectorAll('#nav a[href*="/bolme/"], .nav-pop a[href*="/bolme/"]')].map(a => { const m = (a.getAttribute("href") || "").match(/bolme\\/([^/?#]+)/); return m ? "#/bolme/" + m[1] : ""; }).filter(Boolean)`);
    const sections = [...new Set([...(cats || []), "#/bolme/prezident", "#/bolme/sondeqiqe", "#/bolme/gundem", "#/bolme/siyaset", "#/bolme/cemiyyet", "#/bolme/iqtisadiyyat", "#/bolme/dunya", "#/bolme/idman", "#/bolme/medeniyyet", "#/bolme/heyat", "#/bolme/sosial", "#/bolme/bolgeler", "#/bolme/tehsil", "#/bolme/video"])];
    for (const h of [...sections, "#/bolme/valyuta", "#/bolme/cedvel", "#/tixac", "#/menbeler", "#/videolent", "#/secilmis", "#/bolmeler", "#/haqqinda"]) {
      await go(h === "#/haqqinda" ? "#/bolmeler" : "#/haqqinda", 300);
      await nav("bölmə", h.replace("#/", ""), `location.hash = ${JSON.stringify(h)}`, LIMITS.nav, 600, h === "#/haqqinda" ? "#/bolmeler" : "#/haqqinda");
    }
    // 3) Xəbər səhifəsi və axtarış.
    await go("#/", 800);
    const art = await evaluate(`[...document.querySelectorAll('#view a[href*="/xeber/"]')].map(a => { const m = (a.getAttribute("href") || "").match(/xeber\\/([0-9a-f]{16})/); return m ? "#/xeber/" + m[1] : ""; }).find(Boolean) || ""`);
    if (art) { await go("#/haqqinda", 300); await nav("xəbər", art.slice(2, 30), `location.hash = ${JSON.stringify(art)}`, LIMITS.nav); }
    for (const q of ["futbol", "Əliyev", "bakı"]) { await go("#/haqqinda", 300); await nav("axtarış", q, `location.hash = ${JSON.stringify("#/axtar?q=" + q)}`, LIMITS.nav, 600, "#/haqqinda"); }

    // 4) Alt bölmələr: idman və Bölgələr (2-ci və 3-cü səviyyə düymələri).
    const clickAll = async (section, kind) => {
      await go("#/bolme/" + section, 900);
      const tops = await evaluate(`[...document.querySelectorAll("#view .sub-rows [data-club]")].map(b => b.dataset.club).filter(Boolean)`);
      for (const t of QUICK ? tops.slice(0, 4) : tops) {
        await nav(kind, t, `[...document.querySelectorAll("#view .sub-rows [data-club]")].find(b => b.dataset.club === ${JSON.stringify(t)})?.click()`, LIMITS.sub);
        const subs = await evaluate(`[...new Set([...document.querySelectorAll("#view .sub-rows [data-club]")].map(b => b.dataset.club))].filter(n => n && !${JSON.stringify(tops)}.includes(n))`);
        for (const d of QUICK ? subs.slice(0, 2) : subs) await nav(kind + "/3", `${t} → ${d}`, `[...document.querySelectorAll("#view .sub-rows [data-club]")].find(b => b.dataset.club === ${JSON.stringify(d)})?.click()`, LIMITS.sub, 400);
        // seçimi geri qaytar ki, növbəti düymə yuxarı sırada qalsın
        await evaluate(`[...document.querySelectorAll("#view .sub-rows [data-club]")].find(b => b.dataset.club === ${JSON.stringify(t)})?.click()`); await sleep(200);
      }
    };
    await clickAll("idman", "idman");
    await clickAll("bolgeler", "bölgə");

    // 5) Liqa və komanda səhifələri (Futbol və Basketbol tabındakı bütün liqalar, hər liqadan iki komanda və komanda tabları).
    await go("#/bolme/idman", 900);
    let leagues = [];
    for (const t of ["Futbol", "Basketbol"]) {
      await evaluate(`[...document.querySelectorAll("#view .sub-rows [data-club]")].find(b => b.dataset.club === ${JSON.stringify(t)})?.click()`); await sleep(500);
      leagues.push(...await evaluate(`[...document.querySelectorAll('#view a[href^="#/komanda/"]')].map(a => a.getAttribute("href"))`));
    }
    leagues = [...new Set(leagues)];
    for (const l of QUICK ? leagues.slice(0, 3) : leagues) {
      await go("#/haqqinda", 300);
      await nav("liqa", l.replace("#/komanda/", ""), `location.hash = ${JSON.stringify(l)}`, LIMITS.nav, 700, "#/haqqinda");
      const teams = (await evaluate(`[...new Set([...document.querySelectorAll('#view a[href^="${l}/"]')].map(a => a.getAttribute("href")))]`)).filter(h => h.split("/").length === 4).slice(0, 2);
      for (const t of teams) {
        await nav("komanda", t.replace("#/komanda/", ""), `location.hash = ${JSON.stringify(t)}`, LIMITS.nav, 700);
        // Yalnız komandanın göstərdiyi tablar (.tm-tabs): oyunu olmayan komandada «Oyunlar» tabı yoxdur və ünvan baxışa qayıdır —
        // gecə ölçüsündə 10 milli komanda «məzmun dəyişmədi» yalançı qırmızı verirdi (2026-11-09). Tab siyahısı tapılmasa köhnə üçlük.
        const shown = await evaluate(`[...document.querySelectorAll("#view .tm-tabs a[href]")].map(a => a.getAttribute("href").split("?")[0]).filter(h => h.startsWith(${JSON.stringify(t + "/")})).map(h => h.slice(${t.length + 1}))`);
        for (const tab of ["oyunlar", "cedvel", "xeberler"].filter(x => !shown.length || shown.includes(x))) await nav("komanda", t.replace("#/komanda/", "") + "/" + tab, `location.hash = ${JSON.stringify(t + "/" + tab)}`, LIMITS.nav, 400);
      }
    }

    // 6) Kompüter keçidi (1280×800, prosessor 1×, hover:hover, yavaşlatmasız): yalnız CLS və slayder şəklinin yükləmə sayı
    // (2026-11-09: hazır HTML 640 px, JS 800 px istəyirdi — şəkil iki dəfə gəlirdi, CLS 0,10).
    await send("Emulation.setDeviceMetricsOverride", { width: 1280, height: 800, deviceScaleFactor: 1, mobile: false });
    await send("Emulation.setUserAgentOverride", { userAgent: UA_DESK });
    await send("Emulation.setTouchEmulationEnabled", { enabled: false });
    await send("Emulation.setEmulatedMedia", { features: [{ name: "hover", value: "hover" }, { name: "pointer", value: "fine" }, { name: "any-hover", value: "hover" }] });
    await send("Emulation.setCPUThrottlingRate", { rate: 1 });
    await send("Network.emulateNetworkConditions", NET_FREE);
    await coldRow("ana səhifə (kompüter)", "", { hero, reps: 1, cls: LIMITS["cls.komputer"], only: ["cls", "heroLoads"] });
  } finally {
    c.close(); proc.kill();
    try { fs.rmSync(dir, { recursive: true, force: true }); } catch {}
  }
}

function summary() {
  const md = [`### Sürət ölçüsü — ${BASE}${AB ? ` (baza: ${AB})` : ""}, prosessor ${CPU}×, ${rows.length} ölçü`];
  const cold = rows.filter(r => r.kind === "cold");
  if (cold.length) {
    md.push("", "| Səhifə | görünmə | ilk boya | CSS→boya | boyadan əvvəl uzun (max/cəm) | LCP | CLS | sorğu | slayd | DOM |", "|---|---|---|---|---|---|---|---|---|---|");
    for (const r of cold) md.push(`| ${r.name} | ${fmt(r.first)} | ${fmt(r.fcp)} | ${fmt(r.fcpAfterCss)} | ${fmt(r.preFcpLongTaskMax)}/${fmt(r.preFcpLongTaskSum)} | ${fmt(r.lcp)} | ${fmt(r.cls)} | ${fmt(r.requests)} | ${fmt(r.heroLoads)} | ${fmt(r.dom)} |`);
  }
  for (const r of rows.filter(r => ["ab", "bfcache", "sehife"].includes(r.kind))) md.push("", "- " + line(r).replace(/\s+/g, " "));
  if (fail.length) md.push("", `**Büdcəni keçənlər (${fail.length})**`, ...fail.map(f => "- ✗ " + f));
  if (warn.length) md.push("", `**Xəbərdarlıqlar (${warn.length}; yeni büdcələr ${String(LIMITS["yeni.sert"]).slice(0, 10)}-dən sərt)**`, ...warn.map(w => "- ⚠ " + w));
  if (!fail.length) md.push("", "Bütün ölçülər büdcə daxilindədir.");
  return md.join("\n") + "\n";
}

async function main() {
  if (NIGHT.third) await thirdParty();
  if (NIGHT.pages) await pagesCheck();
  if (NIGHT.data) await dataCheck();
  if (!process.env.SPEED_NO_BROWSER) await browser();
  const worst = rows.filter(r => !["cold", "ab", "bfcache", "ucuncu", "sehife", "data"].includes(r.kind) && num(r.first)).sort((a, b) => b.first - a.first).slice(0, 8);
  console.log(`\n${rows.length} ölçü, prosessor ${CPU}× yavaş.${worst.length ? " Ən yavaş keçidlər:" : ""}`);
  worst.forEach(r => console.log(`  ${r.kind} ${r.name}: ${r.first} ms${(r.net || []).length ? " (şəbəkə)" : ""}`));
  if (process.env.SPEED_JSON) fs.writeFileSync(process.env.SPEED_JSON, JSON.stringify({ base: BASE, ab: AB, cpu: CPU, at: new Date().toISOString(), warnOnlyUntil: LIMITS["yeni.sert"], rows, fail, warn }, null, 1));
  if (process.env.GITHUB_STEP_SUMMARY) { try { fs.appendFileSync(process.env.GITHUB_STEP_SUMMARY, summary()); } catch {} }
  if (warn.length) { console.log(`\nXəbərdarlıqlar (${warn.length}; yeni büdcələr ${String(LIMITS["yeni.sert"]).slice(0, 10)}-dən sərt):\n  ` + warn.join("\n  ")); if (process.env.GITHUB_ACTIONS) warn.forEach(w => console.log(`::warning::${w}`)); }
  if (fail.length) { console.log(`\nBüdcəni keçənlər (${fail.length}):\n  ` + fail.join("\n  ")); if (process.env.GITHUB_ACTIONS) fail.forEach(f => console.log(`::error::${f}`)); if (BUDGET) process.exitCode = 1; }
  else console.log("\nBütün ölçülər büdcə daxilindədir.");
}
main().catch(e => { console.error(e); process.exit(2); }); // exitCode yox: açıq qalan Chrome prosesi işi asılı saxlayırdı
