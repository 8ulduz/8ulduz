// Sürət ölçüsü (qırmızı xətt 3, sahib 2026-11-05: «gözqırpımı sürət» — bütün bölmə, alt bölmə və onların alt bölmələri).
// Başsız Chrome-da telefon şəraiti: 412×915 ekran, prosessor 4 dəfə yavaş (orta Android), mobil şəbəkə.
// Hər səviyyə ölçülür: soyuq açılış, 14 bölmə, xidmət səhifələri, idmanın alt bölmələri və onların alt düymələri, liqa və komanda
// səhifələri, Bölgələrin regionları və rayonları, xəbər səhifəsi, axtarış. Əlavə paket yoxdur (Node 22+: WebSocket, fetch).
//
//   node .github/scripts/speed.cjs https://8ulduz.az/            # canlı sayt
//   node .github/scripts/speed.cjs http://localhost:8773/ --budget # büdcəni keçən varsa çıxış kodu 1 (CI)
//   CHROME=/path/to/chrome  SPEED_CPU=4  SPEED_JSON=speed.json
"use strict";
const { spawn } = require("child_process");
const fs = require("fs"), os = require("os"), path = require("path");

const BASE = (process.argv[2] || "https://8ulduz.az/").replace(/\/?$/, "/");
const BUDGET = process.argv.includes("--budget");
const CPU = Number(process.env.SPEED_CPU || 4);
const QUICK = !!process.env.SPEED_QUICK; // A/B üçün qısa dövrə: hər səviyyədən bir neçə nümunə
const REPS = Math.max(1, Number(process.env.SPEED_REPS || 1)); // ünvan keçidləri və soyuq açılış neçə dəfə (median)
const median = xs => { const v = xs.filter(x => typeof x === "number").sort((a, b) => a - b); return v.length ? v[Math.floor((v.length - 1) / 2)] : null; };
// Büdcə (4× yavaş prosessorda, ms). Keçid: düyməyə/ünvana basandan yeni məzmunun görünməsinə qədər.
// Yerli fayllar şəbəkəsiz gəlir; ilk ziyarətdə liqa faylı kimi şəbəkə gözləməsi «net» kimi ayrıca sayılır.
// Uzun iş 300: Bölgələrdə ilk seçim 14 arxivin mətnini sessiyada bir dəfə hazırlayır (~265 ms, 4×); qalan hamısı ≤ 200.
const LIMITS = { cold: 4000, nav: 300, sub: 300, longTask: 300, dom: 2500 };

const sleep = ms => new Promise(r => setTimeout(r, ms));
function chromePath() {
  if (process.env.CHROME) return process.env.CHROME;
  for (const p of ["C:/Program Files/Google/Chrome/Application/chrome.exe", "/usr/bin/google-chrome", "/usr/bin/google-chrome-stable", "/usr/bin/chromium", "/usr/bin/chromium-browser"]) if (fs.existsSync(p)) return p;
  throw new Error("Chrome tapılmadı (CHROME=...)");
}

async function launch() {
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), "speed-"));
  const proc = spawn(chromePath(), ["--headless=new", "--remote-debugging-port=0", `--user-data-dir=${dir}`, "--no-first-run", "--no-default-browser-check", "--disable-extensions", "--mute-audio", "--no-sandbox", "about:blank"], { stdio: "ignore" });
  const portFile = path.join(dir, "DevToolsActivePort");
  for (let i = 0; i < 100 && !fs.existsSync(portFile); i++) await sleep(100);
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

// Səhifəyə yerləşən ölçü köməkçisi: keçidi başladır, #view-da ilk dəyişikliyi və sabitləşməni, uzun işləri qeyd edir.
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

async function main() {
  const { proc, dir, ws } = await launch();
  const c = await cdp(ws);
  const rows = [], fail = [];
  try {
    const { targetId } = await c.send("Target.createTarget", { url: "about:blank" });
    const { sessionId: s } = await c.send("Target.attachToTarget", { targetId, flatten: true });
    const send = (m, p) => c.send(m, p, s);
    await send("Page.enable"); await send("Runtime.enable"); await send("Network.enable");
    await send("Emulation.setDeviceMetricsOverride", { width: 412, height: 915, deviceScaleFactor: 2.625, mobile: true });
    await send("Emulation.setUserAgentOverride", { userAgent: "Mozilla/5.0 (Linux; Android 14; Pixel 7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0 Mobile Safari/537.36" });
    await send("Emulation.setTouchEmulationEnabled", { enabled: true, maxTouchPoints: 5 });
    await send("Emulation.setEmulatedMedia", { features: [{ name: "hover", value: "none" }, { name: "pointer", value: "coarse" }, { name: "any-hover", value: "none" }] });
    await send("Emulation.setCPUThrottlingRate", { rate: CPU });
    // Mobil şəbəkə (Lighthouse «slow 4G»-dən bir az yaxşı): 100 ms RTT, 6 Mbit/s.
    await send("Network.emulateNetworkConditions", { offline: false, latency: 100, downloadThroughput: 6e6 / 8, uploadThroughput: 2e6 / 8 });
    const evaluate = async (expr, timeout = 30000) => {
      const r = await Promise.race([send("Runtime.evaluate", { expression: expr, awaitPromise: true, returnByValue: true }), sleep(timeout).then(() => ({ result: { value: { timeout: true } } }))]);
      if (r.exceptionDetails) throw new Error(r.exceptionDetails.exception?.description || r.exceptionDetails.text);
      return r.result.value;
    };
    const add = (kind, name, r, limit) => {
      const row = { kind, name, ...r };
      const over = [];
      const shown = r.vis ?? r.first;
      if (limit && shown != null && shown > limit && !(r.net || []).length) over.push(`ekrana çıxma ${shown} > ${limit}`);
      if (r.first == null && kind !== "cold") over.push("məzmun dəyişmədi");
      if (r.ltMax > LIMITS.longTask) over.push(`uzun iş ${r.ltMax} > ${LIMITS.longTask}`);
      if (r.dom > LIMITS.dom) over.push(`DOM ${r.dom} > ${LIMITS.dom}`);
      row.over = over;
      if (over.length) fail.push(`${kind} ${name}: ${over.join(", ")}`);
      rows.push(row);
      console.log(`${kind.padEnd(7)} ${name.slice(0, 42).padEnd(42)} ilk ${String(r.first ?? "-").padStart(5)} kadr ${String(r.vis ?? "-").padStart(5)} dom0 ${String(r.firstDom ?? "-").padStart(4)} sabit ${String(r.stable ?? "-").padStart(5)} uzun ${String(r.lt ?? 0).padStart(4)}/${String(r.ltMax ?? 0).padStart(4)} dom ${String(r.dom ?? "-").padStart(5)}${(r.net || []).length ? "  şəbəkə: " + r.net.join(", ").slice(0, 120) : ""}${over.length ? "  ✗ " + over.join("; ") : ""}`);
    };

    // 1) Soyuq açılış: ünvan → ilk xəbər kartı ekranda.
    // İlk ziyarət: brauzer keşi, xidmət işçisi və onun keşi, yaddaş silinir (yoxsa ikinci «soyuq» açılış əslində isti olur).
    const cold = async (hash, name, warm) => {
      if (!warm) {
        await send("Network.clearBrowserCache");
        await send("Storage.clearDataForOrigin", { origin: new URL(BASE).origin, storageTypes: "all" }).catch(() => {});
        await send("Page.navigate", { url: "about:blank" }); await sleep(300);
      }
      const t0 = Date.now();
      await send("Page.navigate", { url: BASE + hash });
      let ms = null;
      for (let i = 0; i < 300; i++) {
        await sleep(50);
        // Ekranda görünən ilk məzmun: xəbər kartı, slayd və ya cədvəl (gizli hazır HTML və skelet sayılmır).
        // CSS gəlməmiş səhifə boyanmır: yoxlama yalnız app.css yüklənəndən sonra (yoxsa gizli hazır HTML «görünən» sayılırdı).
        const ok = await evaluate(`(() => { const v = document.querySelector("#view"), css = document.querySelector('link[href*="app.css"]')?.sheet; return !!v && !!css && [...v.querySelectorAll("article,.card,.hero-main,.tm-sec,.tm-table,table")].some(e => e.checkVisibility() && !e.closest(".skel,.skeleton")) && Math.round(performance.now()); })()`).catch(() => false);
        if (ok) { ms = ok; break; }
      }
      const lcp = await evaluate(`new Promise(r => { let v = 0; try { new PerformanceObserver(l => { for (const e of l.getEntries()) v = e.startTime; }).observe({ type: "largest-contentful-paint", buffered: true }); } catch {} setTimeout(() => r(Math.round(v)), 300); })`);
      add("cold", name, { first: ms, stable: lcp, lt: 0, ltMax: 0, dom: await evaluate(`document.querySelectorAll("#view *").length`) }, LIMITS.cold);
      return Date.now() - t0;
    };
    for (const [h, name] of [["", "ana səhifə"], ["#/bolme/idman", "idman (birbaşa keçid)"], ["#/bolme/gundem", "gündəm (birbaşa keçid)"], ["#/komanda/premyer-liqa", "liqa (birbaşa keçid)"]]) {
      const before = rows.length; for (let i = 0; i < REPS; i++) await cold(h, name);
      const runs = rows.splice(before); const last = rows.length;
      fail.splice(0, fail.length, ...fail.filter(f => !f.startsWith("cold " + name + ":")));
      add("cold", name, { ...runs[runs.length - 1], first: median(runs.map(r => r.first)), stable: median(runs.map(r => r.stable)) }, LIMITS.cold);
    }
    // Təkrar ziyarət (tətbiq quraşdırılıb, xidmət işçisi keşi ilə): telefon sahibinin hər gün gördüyü açılış.
    await cold("", "ana səhifə (təkrar)", true); await sleep(3000); await cold("", "ana səhifə (təkrar)", true);
    await cold("#/bolme/idman", "idman (təkrar)", true);
    await sleep(2500);
    await evaluate(HELPER);

    const nav = async (kind, name, js, limit, quiet, from) => {
      const runs = [];
      for (let i = 0; i < (from ? REPS : 1); i++) { if (from && i) await go(from, 300); runs.push(await evaluate(`__nav(() => { ${js} }, ${quiet || 600})`)); }
      const r = { ...runs[runs.length - 1] };
      for (const k of ["first", "vis", "firstDom", "stable", "lt", "ltMax"]) r[k] = median(runs.map(x => x[k]));
      add(kind, name, r, limit);
    };
    const go = async (hash, wait = 400) => { await evaluate(`location.hash = ${JSON.stringify(hash)}`); await sleep(wait); };

    // 2) Bölmələr və xidmət səhifələri (tətbiq daxilində keçid).
    const cats = await evaluate(`[...document.querySelectorAll('#nav a[href^="#/bolme/"], .nav-pop a[href^="#/bolme/"]')].map(a => a.getAttribute("href"))`);
    const sections = [...new Set([...(cats || []), "#/bolme/prezident", "#/bolme/sondeqiqe", "#/bolme/gundem", "#/bolme/siyaset", "#/bolme/cemiyyet", "#/bolme/iqtisadiyyat", "#/bolme/dunya", "#/bolme/idman", "#/bolme/medeniyyet", "#/bolme/heyat", "#/bolme/sosial", "#/bolme/bolgeler", "#/bolme/tehsil", "#/bolme/video"])];
    for (const h of [...sections, "#/bolme/valyuta", "#/bolme/cedvel", "#/tixac", "#/menbeler", "#/videolent", "#/secilmis", "#/bolmeler", "#/haqqinda"]) {
      await go(h === "#/haqqinda" ? "#/bolmeler" : "#/haqqinda", 300);
      await nav("bölmə", h.replace("#/", ""), `location.hash = ${JSON.stringify(h)}`, LIMITS.nav, 600, h === "#/haqqinda" ? "#/bolmeler" : "#/haqqinda");
    }
    // 3) Xəbər səhifəsi və axtarış.
    await go("#/", 800);
    const art = await evaluate(`[...document.querySelectorAll('#view a[href^="#/xeber/"]')].map(a => a.getAttribute("href").replace(/#sources$/, ""))[0] || ""`);
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
        for (const tab of ["oyunlar", "cedvel", "xeberler"]) await nav("komanda", t.replace("#/komanda/", "") + "/" + tab, `location.hash = ${JSON.stringify(t + "/" + tab)}`, LIMITS.nav, 400);
      }
    }
  } finally {
    c.close(); proc.kill();
    try { fs.rmSync(dir, { recursive: true, force: true }); } catch {}
  }
  const worst = [...rows].filter(r => r.kind !== "cold").sort((a, b) => (b.first || 0) - (a.first || 0)).slice(0, 8);
  console.log(`\n${rows.length} ölçü, prosessor ${CPU}× yavaş. Ən yavaş keçidlər:`);
  worst.forEach(r => console.log(`  ${r.kind} ${r.name}: ${r.first} ms${r.net.length ? " (şəbəkə)" : ""}`));
  if (process.env.SPEED_JSON) fs.writeFileSync(process.env.SPEED_JSON, JSON.stringify({ base: BASE, cpu: CPU, at: new Date().toISOString(), rows }, null, 1));
  if (fail.length) { console.log(`\nBüdcəni keçənlər (${fail.length}):\n  ` + fail.join("\n  ")); if (BUDGET) process.exitCode = 1; }
  else console.log("\nBütün ölçülər büdcə daxilindədir.");
}
main().catch(e => { console.error(e); process.exitCode = 2; });
