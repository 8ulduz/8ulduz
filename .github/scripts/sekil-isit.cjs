#!/usr/bin/env node
// Şəkil keşinin isidilməsi (docs/img-worker.md; sahib, 2026-11-27: «Bəli, qur»). img Worker-i (.github/img-worker) hər şəkli bir dəfə
// wsrv.nl-dən alıb R2-yə yazır. Bu skript ilk ekranın təzə şəkillərini oxucudan əvvəl bir dəfə soruşur: ilk oxucu da şəkli soyuq
// wsrv.nl-dən (230–3 400 ms) yox, R2-dən (~60–150 ms) alır.
// Ünvanlar app.js-in öz homeView()-undan çıxır (prerender.cjs renderHome, data/first.json; mənbə qaydası da orada işləyir): telefon
// (ilk slayd 640, qalan slaydlar 480, «Son xəbərlər» 360, Zuğulba 168) və kompüter (slaydlar 640) — sayt hansı ünvanı istəyirsə, eynisi.
// Yalnız IMG_HOST (repo dəyişəni, məs. img.8ulduz.az) qoyulanda işləyir: Worker canlı olana qədər heç nə etmir.
// QIRMIZI XƏTT 1: pipeline.sh-ın yavaş dövrəsində (slow_loop, sekil_isit) işləyir, xəbər dövrəsi onu gözləmir. Az paralel (PARALLEL),
// hər sorğuya və bütün işə sərt vaxt həddi (ASK_MS, TOTAL_MS). Heç nə yazmır və paylaşmır: yalnız şəkil soruşur. Alınan ünvanlar
// yaddaş faylına düşür (MEMORY_H saat) ki, növbəti dövrə onları təkrar soruşmasın; alınmayan növbəti dövrədə yenə soruşulur.
// İşlətmə: node .github/scripts/sekil-isit.cjs <kod kökü (assets/app.js)> [<first.json>] [<yaddaş faylı>]
"use strict";
const fs = require("node:fs"), path = require("node:path");
const { renderHome, firstScreen } = require("./prerender.cjs");

// İlk ekran və bir sürüşmə: 6 slayd, 8 Zuğulba kartı, 8 «Son xəbərlər» kartı (hazır ilk ekrandan çox: app.js tam siyahını çəkir).
const KEEP = { slides: 6, prez: 8, latest: 8 };
const SCREENS = [390, 1280];                  // telefon və kompüter eni (app.js heroPicWidth: 900-dən kiçikdə qalan slaydlar 480)
const PARALLEL = 3, ASK_MS = 10000, TOTAL_MS = 35000, MAX_PER_RUN = 40, MEMORY_H = 48;
const UA = "Mozilla/5.0 (compatible; 8ulduz-isit/1.0; +https://8ulduz.az/)";

const unesc = s => s.replace(/&quot;/g, '"').replace(/&#39;/g, "'").replace(/&lt;/g, "<").replace(/&gt;/g, ">").replace(/&amp;/g, "&");

// Saytın kiçildilmiş şəkil sorğusu (wsrv.nl və ya IMG_HOST, ?url=…&w=…&output=webp) → eyni sorğu IMG_HOST-da. Başqa ünvan (orijinal, hekaye.js-in jpg-si) "".
function toHost(u, host) {
  let x;
  try { x = new URL(u); } catch { return ""; }
  if (x.protocol !== "https:" || x.pathname !== "/" || (x.hostname !== "wsrv.nl" && x.hostname !== host)) return "";
  const p = x.searchParams;
  return p.get("output") === "webp" && p.has("url") && p.has("w") ? `https://${host}/${x.search}` : "";
}

// İlk ekranın şəkil ünvanları, sayt çəkiləndəki sıra ilə (slayd, Zuğulba, «Son xəbərlər»), təkrarsız.
function targets(root, first, host) {
  const out = new Set();
  for (const width of SCREENS) {
    const html = firstScreen(renderHome(root, first, { width }).view, KEEP);
    for (const m of html.matchAll(/<img\b[^>]*?\s(?:data-)?src="([^"]+)"/g)) { const u = toHost(unesc(m[1]), host); if (u) out.add(u); }
  }
  return [...out];
}

// Vaxt həddi adi taymerlədir: AbortSignal.timeout-un taymeri prosesi açıq saxlamır (unref) — asılan sorğu qalanda Node hədd
// dolmadan çıxırdı (CI, Linux: «Promise resolution is still pending but the event loop has already resolved»).
async function ask(u, ms, fetchImpl) {
  const c = new AbortController(), t = setTimeout(() => c.abort(new DOMException("vaxt həddi", "TimeoutError")), ms);
  try {
    const r = await fetchImpl(u, { headers: { "User-Agent": UA, "Accept": "image/webp,image/*" }, signal: c.signal });
    const ok = r.status === 200 && /^image\//.test(r.headers.get("content-type") || "");
    try { await r.body?.cancel(); } catch {}    // şəklin özü lazım deyil: Worker onu cavabdan əvvəl alıb, R2-yə waitUntil-də yazır
    return { u, ok, status: r.status, from: r.headers.get("x-sekil") || "" };
  } catch (e) { return { u, ok: false, status: e?.name === "TimeoutError" || e?.name === "AbortError" ? "vaxt" : "şəbəkə" }; }
  finally { clearTimeout(t); }
}

// PARALLEL-dən çox sorğu eyni anda getmir; TOTAL_MS bitəndə yeni sorğu başlamır, gedən sorğu da qalan vaxtla kəsilir.
async function warm(urls, { parallel = PARALLEL, askMs = ASK_MS, totalMs = TOTAL_MS, fetchImpl = globalThis.fetch } = {}) {
  const deadline = Date.now() + totalMs, out = [];
  let i = 0;
  const lane = async () => {
    while (i < urls.length) {
      const left = deadline - Date.now();
      if (left < 200) return;
      out.push(await ask(urls[i++], Math.min(askMs, left), fetchImpl));
    }
  };
  await Promise.all(Array.from({ length: Math.min(parallel, urls.length) }, lane));
  return out;
}

function readMemory(file, now) {
  if (!file) return {};
  try {
    const d = JSON.parse(fs.readFileSync(file, "utf8")), keep = {};
    for (const [u, t] of Object.entries(d || {})) if (typeof t === "number" && now - t < MEMORY_H * 3600e3) keep[u] = t;
    return keep;
  } catch { return {}; }
}
function writeMemory(file, mem) {
  if (!file) return;
  try { fs.mkdirSync(path.dirname(file), { recursive: true }); fs.writeFileSync(file + ".tmp", JSON.stringify(mem)); fs.renameSync(file + ".tmp", file); } catch {}
}

async function main(argv = [], env = process.env, opts = {}) {
  const host = String(env.IMG_HOST || "").trim().toLowerCase();
  if (!host) return { skipped: "IMG_HOST yoxdur" };
  if (!/^[a-z0-9-]+(?:\.[a-z0-9-]+)+$/.test(host)) throw Error("IMG_HOST yararsızdır: " + host);
  const [root = process.cwd(), firstFile = path.join(root, "data/first.json"), memFile = ""] = argv;
  const now = opts.now || Date.now();
  const first = JSON.parse(fs.readFileSync(firstFile, "utf8"));
  const all = targets(root, first, host), mem = readMemory(memFile, now);
  const todo = all.filter(u => !mem[u]).slice(0, MAX_PER_RUN);
  const done = await warm(todo, opts);
  for (const r of done) if (r.ok) mem[r.u] = now;
  writeMemory(memFile, mem);
  const by = {};
  for (const r of done) { const k = r.ok ? r.from || "ok" : String(r.status); by[k] = (by[k] || 0) + 1; }
  return { all: all.length, asked: done.length, ok: done.filter(r => r.ok).length, by };
}

module.exports = { toHost, targets, warm, main, KEEP, SCREENS, PARALLEL, ASK_MS, TOTAL_MS, MAX_PER_RUN };

if (require.main === module) {
  main(process.argv.slice(2)).then(r => {
    if (r.skipped) return;
    console.log(`şəkil isitməsi: ilk ekranda ${r.all}, soruşulan ${r.asked}, alınan ${r.ok}`, JSON.stringify(r.by));
  }, e => { console.error("şəkil isitməsi alınmadı:", e.message); process.exitCode = 1; });
}
