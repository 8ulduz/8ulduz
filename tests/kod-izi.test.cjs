// Kod izləri (assets/kod.json, sw.js v184; sahib 2026-11-27: «saytın çox sürətli işləyişini hərtərəfli təmin etmək»).
// GitHub Pages hər yayımda bütün faylların ETag-ını dəyişir, botlar gündə 100+ dəfə yazır: işçinin arxa yoxlaması dəyişməyən app.min.js,
// app.css … faylını hər yayımdan sonra tam endirirdi (~90 KB gzip). İndi işçi kod.json-u soruşur və izi eyni olan faylı endirmir.
// Bu testlər: siyahı köhnə qalmır (köhnə qalsa oxucu yeni kodu almaz), iz sw.js və kicilt-də eynidir, işçinin bütün zəmanətləri
// (saxlanmış nüsxə dərhal, yeni kod gəlir və bildirilir, 36 saat qaydası, oflayn) kod.json yolunda da qalır.
const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs"), path = require("node:path"), vm = require("node:vm");
const root = path.join(__dirname, "..");
const read = f => fs.readFileSync(path.join(root, f), "utf8").replace(/\r\n/g, "\n");
const kod = require("../.github/kicilt/kod.cjs");
const SW = read("sw.js");
const SITE = "https://8ulduz.az/", KOD_URL = SITE + "assets/kod.json";

test("kod.json is current: every listed file has the fingerprint of its bytes now (run node .github/kicilt/kicilt.cjs)", () => {
  assert.equal(read(kod.KOD), kod.build(root), "assets/kod.json köhnədir — oxucu yeni kodu almaz: node .github/kicilt/kicilt.cjs işlədin");
  const list = JSON.parse(read(kod.KOD));
  for (const [f, h] of Object.entries(list)) {
    assert.match(h, /^[A-Za-z0-9_-]{16}$/, f);
    const b = fs.readFileSync(path.join(root, f));
    assert.ok(Buffer.from(b.toString("utf8"), "utf8").equals(b), f + " düzgün UTF-8 deyil: iz brauzerdəki mətnlə tutmaz");
  }
});

test("kod.json covers the worker's hand-written code and leaves out what is written straight to main", () => {
  const list = Object.keys(JSON.parse(read(kod.KOD)));
  const html = read("index.html");
  const startup = [...html.matchAll(/<(?:script|link)\b[^>]*(?:src|href)="\.\/((?:assets\/)?[\w.-]+\.(?:js|css|webmanifest))"/g)].map(m => m[1]);
  assert.ok(startup.length >= 4, "index.html-də kod faylları tapılmadı");
  for (const f of startup) if (!kod.KENAR.has(f)) assert.ok(list.includes(f), f + " kod.json-da yoxdur");
  const lazy = new Set([...read("assets/app.js").matchAll(/import\(\s*[`'"](?:\$\{ASSET\}|\.\/)([\w-]+\.js)/g)].map(m => "assets/" + m[1]));
  assert.ok(lazy.size >= 5);
  for (const f of lazy) assert.ok(list.includes(f), "tənbəl modul " + f + " kod.json-da yoxdur");
  // İdarə paneli «xəbəri çıxar» qərarını content-policy.js-ə birbaşa main-ə yazır (kicilt işləmir): o siyahıya düşsə, oxucu çıxarılmış
  // xəbəri görməyə davam edərdi. O, əvvəlki kimi hər açılışda yoxlanır.
  assert.match(read("assets/editorial-store.js"), /POLICY_PATH = 'assets\/content-policy\.js'/);
  assert.ok(!list.includes("assets/content-policy.js") && !list.includes("assets/editorial-store.js") && !list.some(f => f.startsWith("idare/")));
  // Botlar main-ə kod yazmır (publish_main yalnız məlumat və səhifələr əlavə edir); yazsaydı, kod.json köhnə qalardı.
  const adds = read(".github/scripts/pipeline.sh").split("\n").filter(l => /git -C "\$REPO_DIR" add /.test(l)).join("\n");
  assert.ok(!/\badd[^\n]*\b(?:assets|ig|manifest\.webmanifest)\b/.test(adds), "bot kod faylı yazır — kod.json onunla yenilənməlidir");
});

// sw.js-in izOf funksiyası kod.cjs iz ilə hərfbəhərf eyni olmalıdır (fərqli olsa, hər fayl həmişə «dəyişib» sayılar — itki yalnız sürətdə).
test("the worker and the build compute the same fingerprint (Azerbaijani letters, emoji, CRLF, a real file)", async () => {
  const { ctx } = worker();
  for (const s of ["", "a", "Xəbər: ğ ı ö ü ş ç ə — «8ULDUZ» 🇦🇿", "line1\r\nline2\n", read("assets/app.min.js")]) {
    assert.equal(await ctx.izOf(s), kod.iz(s), JSON.stringify(s.slice(0, 30)));
  }
});

// --- İşçi (vm): kod.json yolu ---------------------------------------------------------------------------------------------------------
const savedAt = (text, hoursAgo = 1, type = "application/javascript") => new Response(text, { headers: { date: new Date(Date.now() - hoursAgo * 3600e3).toUTCString(), "content-type": type } });
const json = (body, hoursAgo = 0) => new Response(JSON.stringify(body), { headers: { "content-type": "application/json", date: new Date(Date.now() - hoursAgo * 3600e3).toUTCString() } });
const until = async (cond, ms = 2000) => { for (const end = Date.now() + ms; !cond() && Date.now() < end;) await new Promise(r => setTimeout(r, 2)); };
const settle = (ms = 40) => new Promise(r => setTimeout(r, ms)); // iz (WebCrypto) və keş yazısı bitsin
function worker({ seed = {}, net = () => Promise.reject(new TypeError("offline")) } = {}) {
  const store = new Map(Object.entries(seed)), calls = [], messages = [], puts = [];
  const cache = { match: async k => store.get(String(k))?.clone(), put: async (k, r) => { puts.push(String(k)); store.set(String(k), r); } };
  const ctx = vm.createContext({
    URL, Request, Response, Headers, console, AbortController, setTimeout, clearTimeout, Date, crypto: globalThis.crypto, TextEncoder, btoa,
    self: { location: new URL(SITE + "sw.js"), addEventListener() {}, registration: {},
      clients: { claim: async () => {}, matchAll: async () => [{ postMessage: m => messages.push(m.type) }] } },
    caches: { keys: async () => [], delete: async () => {}, open: async () => cache },
    fetch: (input, init) => { const req = new Request(input, init); calls.push({ url: req.url, cache: req.cache }); return net(req.url, req); },
  });
  vm.runInContext(SW, ctx);
  const ask = (file, mode) => ctx.cachedShell(mode ? { url: SITE + file, mode, method: "GET" } : new Request(SITE + file), { waitUntil() {} });
  return { ctx, ask, store, calls, messages, puts, fetched: () => calls.map(c => c.url) };
}
const manifest = (over = {}) => ({ "assets/app.min.js": kod.iz("saved code"), "assets/app.css": kod.iz("saved css"), "manifest.webmanifest": kod.iz("saved manifest"), ...over });

test("unchanged code after a deploy: the saved copy answers at once and only kod.json goes to the network", async () => {
  const w = worker({ seed: { [SITE + "assets/app.min.js"]: savedAt("saved code"), [SITE + "assets/app.css"]: savedAt("saved css", 1, "text/css") },
    net: async url => url === KOD_URL ? json(manifest()) : new Response("bu fayl endirilməməli idi") });
  assert.equal(await (await w.ask("assets/app.min.js")).text(), "saved code");
  assert.equal(await (await w.ask("assets/app.css?v=3")).text(), "saved css");
  await until(() => w.puts.includes(KOD_URL)); await settle();
  assert.deepEqual(w.fetched(), [KOD_URL], "kod faylı endirilmir; bir açılışın sorğuları bir kod.json-u bölüşür");
  assert.equal(w.calls[0].cache, "no-cache", "kod.json hər açılışda yoxlanır");
  assert.deepEqual(w.puts, [KOD_URL], "yalnız kod.json saxlanır (36 saat yoxlaması üçün)");
  assert.deepEqual(w.messages, []);
});

test("changed code still arrives: stored for the next visit and announced (shell-updated) only when it really changed", async () => {
  for (const [label, kodNet] of [["kod.json başqa iz deyir", async () => json(manifest({ "assets/app.min.js": kod.iz("new code") }))],
    ["kod.json yoxdur (404)", async () => new Response("404", { status: 404 })], ["kod.json HTML-dir", async () => new Response("<html>", { headers: { "content-type": "text/html" } })],
    ["kod.json oxunmur", async () => new Response("{")], ["kod.json-a şəbəkə yoxdur", async () => { throw new TypeError("offline"); }]]) {
    const w = worker({ seed: { [SITE + "assets/app.min.js"]: savedAt("saved code") }, net: async (url, req) => url === KOD_URL ? kodNet() : (assert.equal(req.cache, "no-cache"), new Response("new code")) });
    assert.equal(await (await w.ask("assets/app.min.js")).text(), "saved code", label + ": saxlanmış nüsxə dərhal");
    await until(() => w.messages.length > 0);
    assert.deepEqual(w.fetched(), [KOD_URL, SITE + "assets/app.min.js"], label);
    assert.equal(await w.store.get(SITE + "assets/app.min.js").clone().text(), "new code", label + ": növbəti açılış üçün saxlanır");
    assert.deepEqual(w.messages, ["shell-updated"], label);
  }
  // Fayl siyahıda yoxdursa (content-policy.js idarə panelindən birbaşa yazılır) əvvəlki kimi yoxlanır; eyni gəlsə səs yoxdur.
  const w = worker({ seed: { [SITE + "assets/content-policy.js"]: savedAt("policy") }, net: async url => url === KOD_URL ? json(manifest()) : new Response("policy") });
  await w.ask("assets/content-policy.js");
  await until(() => w.puts.includes(SITE + "assets/content-policy.js")); await settle();
  assert.deepEqual(w.fetched(), [KOD_URL, SITE + "assets/content-policy.js"]);
  assert.deepEqual(w.messages, []);
  // manifest.webmanifest dəyişəndə saxlanır, amma səhifə yenidən açılmır (əvvəlki kimi: yalnız .js/.css).
  const m = worker({ seed: { [SITE + "manifest.webmanifest"]: savedAt("saved manifest", 1, "application/manifest+json") }, net: async url => url === KOD_URL ? json(manifest({ "manifest.webmanifest": "x".repeat(16) })) : new Response("new manifest") });
  assert.equal(await (await m.ask("manifest.webmanifest")).text(), "saved manifest");
  await until(() => m.puts.includes(SITE + "manifest.webmanifest")); await settle();
  assert.equal(await m.store.get(SITE + "manifest.webmanifest").clone().text(), "new manifest");
  assert.deepEqual(m.messages, []);
});

test("one kod.json per page load: the navigation asks first, the code files share it, index.html is still refreshed", async () => {
  const w = worker({ seed: { [SITE]: savedAt("<p>saved</p>", 1, "text/html"), [SITE + "assets/app.min.js"]: savedAt("saved code"), [SITE + "assets/app.css"]: savedAt("saved css", 1, "text/css") },
    net: async url => url === KOD_URL ? json(manifest()) : new Response(url === SITE ? "<p>new</p>" : "x", { headers: { "content-type": "text/html" } }) });
  assert.equal(await (await w.ask("?utm_source=x", "navigate")).text(), "<p>saved</p>");
  assert.equal(w.fetched()[0], KOD_URL, "kod.json naviqasiya ilə soruşulur, kod sorğularını gözləmir");
  await w.ask("assets/app.min.js"); await w.ask("assets/app.css");
  await until(() => w.puts.includes(SITE) && w.puts.includes(KOD_URL)); await settle();
  assert.deepEqual(w.fetched().sort(), [SITE, KOD_URL].sort(), "index.html hər açılışda təzələnir, kod faylları endirilmir");
  assert.equal(await w.store.get(SITE).clone().text(), "<p>new</p>");
});

test("red line 1 on the kod.json path: a saved copy answers at once even while kod.json and the file hang", async () => {
  const wait = new Map();
  const w = worker({ seed: { [SITE + "assets/app.min.js"]: savedAt("saved code", 35) }, net: url => new Promise(r => wait.set(url, r)) });
  assert.equal(await (await w.ask("assets/app.min.js")).text(), "saved code", "şəbəkə gözlənilmir");
  await until(() => wait.has(KOD_URL));
  wait.get(KOD_URL)(json(manifest({ "assets/app.min.js": kod.iz("new code") })));
  await until(() => wait.has(SITE + "assets/app.min.js"));
  wait.get(SITE + "assets/app.min.js")(new Response("new code"));
  await until(() => w.messages.length > 0);
  assert.deepEqual(w.messages, ["shell-updated"], "təzə kod əvvəlki kimi bildirilir");
});

test("36 h rule: an old copy that kod.json confirmed within 36 h answers at once; otherwise the fresh file is waited for", async () => {
  // Hər gün gələn oxucu: fayl çoxdan dəyişməyib (saxlanmış nüsxənin tarixi köhnəlir), kod.json dünən alınıb və eyni izi deyir.
  const daily = worker({ seed: { [SITE + "assets/app.min.js"]: savedAt("saved code", 72), [KOD_URL]: json(manifest(), 20) }, net: () => new Promise(() => {}) });
  const t0 = Date.now(), r = await daily.ask("assets/app.min.js");
  assert.equal(await r.text(), "saved code");
  assert.ok(Date.now() - t0 < 1000, "təsdiqlənmiş nüsxə şəbəkəni gözləmir (" + (Date.now() - t0) + " ms)");
  // Çoxdan gəlməyən oxucu (kod.json da köhnədir) və ya kod.json başqa iz deyir: əvvəlki kimi təzəsi gözlənilir və səssiz verilir.
  for (const [label, kodSaved] of [["kod.json 3 gün əvvəl", json(manifest(), 72)], ["kod.json yoxdur", null], ["kod.json başqa iz deyir", json(manifest({ "assets/app.min.js": kod.iz("other") }), 1)]]) {
    const seed = { [SITE + "assets/app.min.js"]: savedAt("saved code", 72) };
    if (kodSaved) seed[KOD_URL] = kodSaved;
    const w = worker({ seed, net: url => new Promise(r => setTimeout(() => r(url === KOD_URL ? json(manifest()) : new Response("fresh")), 5)) });
    assert.equal(await (await w.ask("assets/app.min.js")).text(), "fresh", label);
    await until(() => w.puts.includes(SITE + "assets/app.min.js")); await settle();
    assert.deepEqual(w.messages, [], label + ": səhifə təzə kodu alıb, yenidən açılmır");
  }
});

test("offline and first visits are unchanged on the kod.json path", async () => {
  const off = worker({ seed: { [SITE + "assets/app.min.js"]: savedAt("saved code"), [KOD_URL]: json(manifest(), 1) } });
  assert.equal(await (await off.ask("assets/app.min.js")).text(), "saved code", "oflayn: saxlanmış kod");
  assert.equal(await (await off.ask("", "navigate")).status, 503, "oflayn və saxlanmış səhifə yoxdur: əvvəlki kimi cacheFirst");
  // Nüsxə yoxdur (ilk açılış, yeni tənbəl modul): kod.json gözlənilmədən birbaşa fayl.
  const first = worker({ net: async url => new Response(url === KOD_URL ? "{}" : "lazy module") });
  assert.equal(await (await first.ask("assets/futbol.js")).text(), "lazy module");
  assert.deepEqual(first.fetched(), [SITE + "assets/futbol.js"]);
  // İlk ziyarətin işçi qurulması (install) dəyişmir: kod.json ilkin keşdə deyil.
  assert.ok(!(SW.match(/cache\.addAll\(\[([^\]]*)\]/) || [])[1].includes("kod.json"));
});
