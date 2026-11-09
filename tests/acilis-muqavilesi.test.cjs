// Açılış müqaviləsi (sahib, 2026-11-09: «gələcəkdə sayta əlavələr də sürəti azaltmasın»). struktur.test.cjs HANSI faylların yükləndiyini
// pinləyir; bu testlər açılışda HANSI İŞİN getdiyini pinləyir: üst səviyyədə yeni yük çağırışı, yeni xarici ünvan, yönləndirən API
// (bfcache sönür), unload dinləyicisi, index.html-də daxili CSS və ya üçüncü preload — hər biri ölçülmüş xərcdir, hər biri burada qırmızı olur.
// Qaydanı yumşaltmaq yalnız sahibin açıq göstərişi ilə (docs/qirmizi-xetler.md §3).
const { test } = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs"), path = require("node:path");
const root = path.join(__dirname, "..");
const read = f => fs.readFileSync(path.join(root, f), "utf8").replace(/\r\n/g, "\n");
const APP = read("assets/app.js"), SW = read("sw.js"), HTML = read("index.html");
const pageFiles = () => fs.readdirSync(path.join(root, "assets")).filter(f => f.endsWith(".js") && !f.endsWith(".min.js"));

// Gövdəsi sonraya aid olan çağırışlar (afterNews, setTimeout, dinləyicilər) balanslı mötərizə ilə çıxarılır: qalan mətn açılışın özüdür.
function stripCalls(src, re) {
  let out = "", i = 0;
  for (;;) {
    re.lastIndex = i; const m = re.exec(src); if (!m) { out += src.slice(i); break; }
    out += src.slice(i, m.index) + m[0].replace(/\($/, "(…)");
    let j = m.index + m[0].length, depth = 1, q = null;
    for (; j < src.length && depth; j++) {
      const c = src[j];
      if (q) { if (c === "\\") j++; else if (c === q) q = null; continue; }
      if (c === '"' || c === "'" || c === "`") q = c; else if (c === "(") depth++; else if (c === ")") depth--;
    }
    i = j;
  }
  return out;
}
const DEFER = /\b(?:afterNews|setInterval|setTimeout|addEventListener|document\.addEventListener|newsReady\.then|firstReady\.then|requestIdleCallback)\(/g;

test("startup contract: the top-level startup block issues only the known loads — new work goes to afterNews() or a lazy module", () => {
  const start = APP.split("\napplyPrefs();\n")[1];
  assert.ok(start, "applyPrefs(); açılış blokunun başlanğıcıdır (testlər və prerender bu sətirlə bölür)");
  const top = stripCalls(start, DEFER);
  const calls = [...new Set([...top.matchAll(/\b(load\w+|fetch|requestJSON|navigator\.sendBeacon)\(/g)].map(m => m[1]))].sort();
  assert.deepEqual(calls, ["loadCached", "loadFirst", "loadLatest", "loadMarkets", "loadNews", "loadShared", "loadSocial", "loadStatus"],
    "açılışda yeni yük: ilk ekranla eyni xətti bölüşür (telefonda hər sorğu ~100 ms RTT + ötürmə). afterNews(() => …) içinə qoyun (lent gələndən sonra) və ya tənbəl modul edin, sonra speed.cjs ilə ölçün");
  assert.deepEqual([...top.matchAll(/import\(\s*[`'"][^`'"]*?([\w-]+\.js)/g)].map(m => m[1]).sort(), ["dil.js"], "açılışda yalnız şərti dil modulu (bayram.js setTimeout ilə sonradır)");
  const idx = start.indexOf("\nlistenWorker();\n");
  assert.ok(idx > 0 && idx < start.indexOf("\nshell(); render();\n") && start.includes("firstReady.then(() => (globalThis.requestIdleCallback"), "işçinin mesajları açılışdan dinlənir, işçi ilk ekrandan sonra boş anda qurulur (2026-11-09)");
});

test("startup contract: every third-party host in the page code is registered with when it is used; nothing asked while the page is open redirects (bfcache)", () => {
  const reg = JSON.parse(read("tests/fixtures/ucuncu-terefler.json"));
  const hosts = new Set();
  for (const f of pageFiles()) for (const m of read("assets/" + f).matchAll(/https:\/\/([a-z0-9.-]+\.[a-z]{2,})/g)) hosts.add(m[1]);
  for (const h of hosts) assert.ok(reg[h], `${h}: tests/fixtures/ucuncu-terefler.json-a yazın (vaxt: açılış|sonra|klik|keçid|mətn; yonlendirir: false yalnız curl ilə yoxlanandan sonra)`);
  for (const [h, r] of Object.entries(reg)) {
    if (h === "_") continue;
    assert.ok(hosts.has(h), `${h} kodda yoxdur: siyahıdan silin`);
    assert.ok(["açılış", "sonra", "klik", "keçid", "mətn"].includes(r.vaxt), `${h}: vaxt`);
    if (r.vaxt === "açılış" || r.vaxt === "sonra") assert.equal(r.yonlendirir, false, `${h}: səhifə açıq olarkən soruşulan ünvan yönləndirməməlidir — 3xx cavab bütün səhifəni bfcache-dən çıxarır (mənbədən geri qayıdış 667 ms, 2026-11-09 ölçüsü); yönləndirməyən ünvanı tapın və ya sorğunu oxucunun klikinə keçirin`);
    if (r.vaxt === "açılış" || r.vaxt === "sonra") assert.ok(/^https:\/\//.test(r.numune || ""), `${h}: numune — gecə ölçüsü (speed.cjs --third-party) bu nümunə sorğunu redirect: "manual" ilə yoxlayır ({tarix} = gg-aa-iiii)`);
  }
  assert.deepEqual(Object.keys(reg).filter(h => reg[h].vaxt === "açılış").sort(), ["raw.githubusercontent.com", "wsrv.nl"], "açılışda yalnız şəkil proksisi və canlı kanal: yeni xarici sorğu ilk ekranla yarışır");
  assert.ok(!/api\.aladhan\.com\/v1\/timings\?/.test(APP), "namaz vaxtı tarixli yolla (/v1/timings/<gg-aa-iiii>?…): tarixsiz yol 302 ilə tarixliyə yönləndirir");
});

test("startup contract: nothing in the page code or the worker disqualifies the page from the back/forward cache", () => {
  const all = pageFiles().map(f => read("assets/" + f)).join("\n") + "\n" + SW;
  assert.ok(!/\b(?:beforeunload|unload)\b|BroadcastChannel|window\.opener/.test(all), "unload/beforeunload, BroadcastChannel, window.opener bfcache-i söndürür — pagehide/visibilitychange işlədin");
  const activate = SW.slice(SW.indexOf('self.addEventListener("activate"'), SW.indexOf('self.addEventListener("fetch"'));
  assert.equal((SW.match(/clients\.claim\(\)/g) || []).length, 1);
  assert.ok(activate.includes("clients.claim()"), "clients.claim() yalnız activate-də");
  assert.ok(!/Cache-Control[^\n]*no-store/i.test(SW) || /networkFirstData/.test(SW), "cavab başlığında no-store yoxdur");
});

test("startup contract: index.html carries no inline CSS, one inline script, one modulepreload and at most two preconnects", () => {
  assert.equal((HTML.match(/<style\b/g) || []).length, 0, "daxili CSS yoxdur: app.css-in nüsxəsi ikinci dəfə gəlir, stil işi artır; «kritik CSS» lazımdırsa sahiblə razılaşdırılıb ayrıca qurulur");
  assert.equal((HTML.match(/<script\b(?![^>]*\b(?:src=|type="application\/))/g) || []).length, 1, "bir daxili skript (CSP hash ilə pinlənir); ld+json məlumatdır, kod deyil");
  assert.equal((HTML.match(/rel="modulepreload"/g) || []).length, 1, "yalnız app.min.js əvvəlcədən");
  assert.ok((HTML.match(/rel="preload"/g) || []).length <= 1, "ən çoxu bir preload (ilk şəkil)");
  assert.ok((HTML.match(/rel="preconnect"/g) || []).length <= 2, "ən çoxu iki preconnect: hər biri ilk ekranla yarışır");
});
