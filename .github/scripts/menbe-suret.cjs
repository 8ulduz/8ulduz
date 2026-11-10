// Mənbə saytlarının açılma sürəti (sahib, 2026-11-10: «saytdan mənbə ağır açılır … əla fikirdir»).
// Lentdəki hər Azərbaycan mənbəsinin ən təzə xəbər səhifəsi telefon şəraitində açılır: 412×915 ekran, 4G (150 ms, 9 Mbit),
// prosessor 4× yavaş, boş keş. Ölçü — ilk görüntü (FCP): oxucunun mətni gördüyü an. Hər mənbə RUNS dəfə, median.
// Nəticə {at, ms: {host: fcp}} — sayt (app.js swift) «N mənbə» kartında keçidi ən sürətli mənbəyə yönəldir; kartın nömrəsi,
// başlığı, şəkli dəyişmir. Fayl «suret» budağına yazılır (iş axını menbe-suret.yml), main-ə və sayta heç nə yazılmır.
// Əlavə paket yoxdur (Node 22+: WebSocket). Ölçülə bilməyən mənbə fayla düşmür — sayt onun keçidinə toxunmur.
//
//   node .github/scripts/menbe-suret.cjs data/news.json menbe-suret.json      CHROME=/path/to/chrome  RUNS=2
"use strict";
const { spawn } = require("child_process");
const fs = require("fs"), os = require("os"), path = require("path");

const RUNS = Number(process.env.RUNS || 2), PAR = 3, WAIT_MS = 15000;
const sleep = ms => new Promise(r => setTimeout(r, ms));
const host = u => { try { return new URL(u).hostname.replace(/^www\./, "").toLowerCase(); } catch { return ""; } };

// Hər host üçün ən təzə xəbər keçidi (əsas sətirlər və «N mənbə» siyahıları), yalnız Azərbaycan dili və https.
function pages(feed) {
  const by = new Map();
  for (const a of feed) {
    if ((a.lang || "az") !== "az") continue;
    for (const r of [a, ...(a.alts || [])]) {
      if (!/^https:\/\//.test(r.sourceUrl || "") || (r.lang || "az") !== "az") continue;
      const h = host(r.sourceUrl), t = Date.parse(r.publishedAt || a.publishedAt) || 0;
      if (h && (!by.has(h) || t > by.get(h).t)) by.set(h, { h, url: r.sourceUrl, t });
    }
  }
  return [...by.values()];
}

const median = v => { v = v.filter(x => x > 0).sort((a, b) => a - b); return v.length ? v[Math.floor((v.length - 1) / 2)] : 0; };

function chromePath() {
  if (process.env.CHROME) return process.env.CHROME;
  for (const p of ["/usr/bin/google-chrome", "/usr/bin/chromium", "C:/Program Files/Google/Chrome/Application/chrome.exe"]) if (fs.existsSync(p)) return p;
  throw new Error("Chrome tapılmadı (CHROME=…)");
}
async function launch() {
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), "suret-"));
  const proc = spawn(chromePath(), ["--headless=new", "--remote-debugging-port=0", `--user-data-dir=${dir}`, "--no-first-run", "--no-default-browser-check",
    "--disable-extensions", "--mute-audio", "--no-sandbox"], { stdio: "ignore" });
  const portFile = path.join(dir, "DevToolsActivePort");
  for (let i = 0; i < 300 && !fs.existsSync(portFile) && proc.exitCode === null; i++) await sleep(100);
  if (!fs.existsSync(portFile)) { try { proc.kill("SIGKILL"); } catch {} throw new Error("Chrome açılmadı"); }
  const [port, wsPath] = fs.readFileSync(portFile, "utf8").split("\n");
  return { proc, ws: `ws://127.0.0.1:${port}${wsPath.trim()}` };
}
function cdp(url) {
  const ws = new WebSocket(url);
  let id = 0; const wait = new Map();
  ws.onmessage = ev => { const m = JSON.parse(ev.data); if (m.id && wait.has(m.id)) { const { ok, no } = wait.get(m.id); wait.delete(m.id); m.error ? no(new Error(m.error.message)) : ok(m.result); } };
  const send = (method, params = {}, sessionId) => new Promise((ok, no) => { const i = ++id; wait.set(i, { ok, no }); ws.send(JSON.stringify({ id: i, method, params, sessionId })); });
  return new Promise(ok => { ws.onopen = () => ok({ send, close: () => ws.close() }); });
}

// Bir ölçü: təzə kontekst (boş keş, kukisiz), telefon şəraiti, FCP gözlənilir (WAIT_MS-dək). Alınmasa 0.
async function fcp(c, url) {
  const { browserContextId } = await c.send("Target.createBrowserContext");
  try {
    const { targetId } = await c.send("Target.createTarget", { url: "about:blank", browserContextId });
    const { sessionId: s } = await c.send("Target.attachToTarget", { targetId, flatten: true });
    await c.send("Network.enable", {}, s);
    await c.send("Network.setCacheDisabled", { cacheDisabled: true }, s);
    await c.send("Network.emulateNetworkConditions", { offline: false, latency: 150, downloadThroughput: 9e6 / 8, uploadThroughput: 1.5e6 / 8 }, s);
    await c.send("Emulation.setCPUThrottlingRate", { rate: 4 }, s);
    await c.send("Emulation.setDeviceMetricsOverride", { width: 412, height: 915, deviceScaleFactor: 2.6, mobile: true }, s);
    await c.send("Emulation.setUserAgentOverride", { userAgent: "Mozilla/5.0 (Linux; Android 14; Pixel 7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0 Mobile Safari/537.36" }, s);
    await c.send("Page.enable", {}, s);
    await c.send("Page.navigate", { url }, s);
    for (let t = 0; t < WAIT_MS; t += 250) {
      await sleep(250);
      const r = await c.send("Runtime.evaluate", { expression: "(performance.getEntriesByName('first-contentful-paint')[0]||{}).startTime||0", returnByValue: true }, s).catch(() => null);
      const v = Math.round(r?.result?.value || 0);
      if (v > 0) return v;
    }
    return 0;
  } finally { await c.send("Target.disposeBrowserContext", { browserContextId }).catch(() => {}); }
}

async function main() {
  const [feedFile = "data/news.json", outFile = "menbe-suret.json"] = process.argv.slice(2);
  const raw = JSON.parse(fs.readFileSync(feedFile, "utf8"));
  const list = pages(raw.articles || raw);
  const { proc, ws } = await launch();
  const c = await cdp(ws);
  const ms = {};
  let i = 0;
  async function worker() {
    while (i < list.length) {
      const p = list[i++], runs = [];
      for (let r = 0; r < RUNS; r++) runs.push(await fcp(c, p.url).catch(() => 0));
      const m = median(runs);
      if (m) ms[p.h] = m;
      console.log(`${p.h.padEnd(28)} ${m ? m + " ms" : "ölçülmədi"}`);
    }
  }
  try { await Promise.all(Array.from({ length: PAR }, worker)); } finally { c.close(); try { proc.kill("SIGKILL"); } catch {} }
  const n = Object.keys(ms).length;
  if (n < Math.max(5, list.length / 2)) throw new Error(`yalnız ${n}/${list.length} mənbə ölçüldü — köhnə fayl qalır`);
  fs.writeFileSync(outFile, JSON.stringify({ at: new Date().toISOString(), ms }));
  console.log(`${n}/${list.length} mənbə → ${outFile}`);
}

if (require.main === module) main().catch(e => { console.error(e); process.exit(1); });
module.exports = { pages, median, host };
