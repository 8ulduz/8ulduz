#!/usr/bin/env node
// IndexNow (2026-11-06): yeni xeber/<id>/ səhifələrini Bing və Yandex-ə dərhal bildirir (Google IndexNow-u qəbul etmir, ona sitemap.xml).
// Sosial iş axınında (social.yml) ayrıca addımdır: xəbər axınına və saytın yükünə toxunmur. Açar kökdəki <açar>.txt faylıdır (gizli deyil,
// protokol belə tələb edir). Bildirilənlər .social/indexnow.json-dadır (actions/cache), 31 gün saxlanır. Səhifə hələ yayımlanmayıbsa
// (Pages gecikməsi) növbəti dövrəyə qalır.
const fs = require("fs"), path = require("path");

const SITE = "https://8ulduz.az/";
const KEEP_S = 31 * 86400;
const MAX = 200;

function keyOf(dir) {
  const f = fs.readdirSync(dir).find(n => /^[0-9a-f]{32}\.txt$/.test(n) && fs.readFileSync(path.join(dir, n), "utf8").trim() === n.slice(0, 32));
  return f ? f.slice(0, 32) : "";
}

// Hələ bildirilməmiş, 31 gündən gənc xəbər səhifələri, ən yenisi birinci.
function pending(index, sent, now) {
  return Object.entries(index || {})
    .filter(([id, row]) => /^[0-9a-f]{16}$/.test(id) && Array.isArray(row) && now / 1000 - row[0] < KEEP_S && !sent[id])
    .sort((a, b) => b[1][0] - a[1][0]).map(([id]) => id);
}

async function run({ index, state, key, now = Date.now(), fetch: f = globalThis.fetch, log = console.log }) {
  const sent = state.sent = Object.fromEntries(Object.entries(state.sent || {}).filter(([, t]) => now / 1000 - t < KEEP_S));
  if (!key) { log("indexnow: açar faylı yoxdur"); return []; }
  const candidates = pending(index, sent, now).slice(0, MAX);
  if (!candidates.length) { log("indexnow: yeni səhifə yoxdur"); return []; }
  // Pages açar faylını yayımlamamış göndəriş başlamasın: xəbər səhifələri əvvəlcədən açıq ola bilər.
  const keyLocation = `${SITE}${key}.txt`;
  const proof = await f(keyLocation, { method: "GET", signal: AbortSignal.timeout(10000) });
  if (proof.status !== 200 || (await proof.text()).trim() !== key) {
    log("indexnow: açar faylı hələ yayımlanmayıb və ya uyğun gəlmir");
    return [];
  }
  const ids = [];
  for (const id of candidates) {
    const ok = await f(`${SITE}xeber/${id}/`, { method: "HEAD", signal: AbortSignal.timeout(10000) }).then(r => r.status === 200, () => false);
    if (ok) ids.push(id);
  }
  if (!ids.length) { log("indexnow: yeni səhifə yoxdur"); return []; }
  const r = await f("https://api.indexnow.org/indexnow", { method: "POST", headers: { "content-type": "application/json; charset=utf-8" },
    body: JSON.stringify({ host: "8ulduz.az", key, keyLocation, urlList: ids.map(id => `${SITE}xeber/${id}/`) }),
    signal: AbortSignal.timeout(20000) });
  if (!(r.status === 200 || r.status === 202)) {
    let code = "";
    try {
      const error = await r.json();
      code = [error.errorCode, error.code].find(v => typeof v === "string" && /^[A-Za-z][A-Za-z0-9_-]{0,79}$/.test(v)) || "";
    } catch {}
    throw new Error(`indexnow: HTTP ${r.status}${code ? ` (${code})` : ""}`);
  }
  for (const id of ids) sent[id] = Math.floor(now / 1000);
  log(`indexnow: ${ids.length} səhifə bildirildi`);
  return ids;
}

async function main() {
  const stateFile = ".social/indexnow.json";
  let state = {};
  try { state = JSON.parse(fs.readFileSync(stateFile, "utf8")) || {}; } catch {}
  let index = {};
  try { index = JSON.parse(fs.readFileSync("xeber/index.json", "utf8")); } catch {}
  await run({ index, state, key: keyOf(".") });
  fs.mkdirSync(path.dirname(stateFile), { recursive: true });
  fs.writeFileSync(stateFile, JSON.stringify(state));
}

module.exports = { pending, run, keyOf };
if (require.main === module) main().catch(e => { console.error(String(e?.message || e)); process.exitCode = 1; });
