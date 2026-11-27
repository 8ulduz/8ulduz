// Şəkil keşinin isidilməsi (.github/scripts/sekil-isit.cjs; docs/img-worker.md): yavaş dövrə ilk ekranın təzə şəkillərini img Worker-dən
// bir dəfə soruşur ki, R2-yə düşsün. Yalnız IMG_HOST ilə; az paralel, sərt vaxt hədləri; xəbər dövrəsinə toxunmur (qırmızı xətt 1).
const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs"), os = require("node:os"), path = require("node:path");
const root = path.join(__dirname, "..");
const I = require("../.github/scripts/sekil-isit.cjs");
const P = require("../.github/scripts/prerender.cjs");
const HOST = "img.8ulduz.az";
const first = JSON.parse(fs.readFileSync(path.join(root, "data/first.json"), "utf8"));
const tmp = () => fs.mkdtempSync(path.join(os.tmpdir(), "isit-"));
const webp = () => new Response(new Uint8Array([1, 2, 3]), { status: 200, headers: { "Content-Type": "image/webp", "X-Sekil": "wsrv" } });

test("sekil-isit 1: dormant until IMG_HOST is set — no rendering, no request", async () => {
  let asked = 0;
  for (const env of [{}, { IMG_HOST: "" }, { IMG_HOST: "  " }]) {
    const r = await I.main([root, "/yoxdur/first.json"], env, { fetchImpl: async () => { asked++; return webp(); } });
    assert.equal(r.skipped, "IMG_HOST yoxdur");
  }
  assert.equal(asked, 0);
  await assert.rejects(I.main([root], { IMG_HOST: "img.8ulduz.az/../x" }), /yararsız/);
});

test("sekil-isit 2: it asks for the first screen exactly as app.js builds it — every picture of the prerendered first screen, hero 640, «Son xəbərlər» 360, Zuğulba 168", () => {
  const urls = I.targets(root, first, HOST);
  assert.ok(urls.length > 0 && urls.length <= I.MAX_PER_RUN, String(urls.length));
  assert.equal(new Set(urls).size, urls.length, "təkrarsız");
  for (const u of urls) assert.match(u, /^https:\/\/img\.8ulduz\.az\/\?url=[^&]+&w=\d+&we&output=webp&q=70$/, u);
  const widths = new Set(urls.map(u => +new URL(u).searchParams.get("w")));
  for (const w of [640, 360, 168]) assert.ok(widths.has(w), "en " + w);
  assert.deepEqual([...widths].filter(w => ![640, 480, 360, 168].includes(w)), [], "yalnız ilk ekranın enləri");
  // Hazır ilk ekranın (index.html, prerender.cjs) hər şəkli isidilir — telefonda brauzerin HTML-dən dərhal istədiyi ünvanlar.
  const pre = P.firstScreen(P.renderHome(root, first, { width: 390 }).view);
  const shown = [...pre.matchAll(/<img\b[^>]*?\s(?:data-)?src="([^"]+)"/g)].map(m => I.toHost(m[1].replace(/&amp;/g, "&"), HOST)).filter(Boolean);
  assert.ok(shown.length >= 3);
  assert.deepEqual(shown.filter(u => !urls.includes(u)), [], "hazır ilk ekranın şəkli isidilmir");
  assert.equal(urls[0], shown[0], "birinci slayd şəkli birinci soruşulur");
  // «Son xəbərlər»in kartları (telefon və kompüter, 360).
  const latest = P.renderHome(root, first, { width: 390 }).view.split('<div class="latest-grid">')[1] || "";
  const cards = [...latest.matchAll(/<img\b[^>]*?\ssrc="([^"]+&amp;w=360[^"]*)"/g)].slice(0, 8).map(m => I.toHost(m[1].replace(/&amp;/g, "&"), HOST));
  assert.ok(cards.length >= 4);
  assert.deepEqual(cards.filter(u => !urls.includes(u)), [], "«Son xəbərlər» kartları");
});

test("sekil-isit 3: only the site's resized-picture query is mapped to the image host; originals and other wsrv queries are left alone", () => {
  assert.equal(I.toHost("https://wsrv.nl/?url=https%3A%2F%2Fa.az%2F1.jpg&w=640&we&output=webp&q=70", HOST), "https://img.8ulduz.az/?url=https%3A%2F%2Fa.az%2F1.jpg&w=640&we&output=webp&q=70");
  assert.equal(I.toHost("https://img.8ulduz.az/?url=https%3A%2F%2Fa.az%2F1.jpg&w=360&we&output=webp&q=70", HOST), "https://img.8ulduz.az/?url=https%3A%2F%2Fa.az%2F1.jpg&w=360&we&output=webp&q=70");
  for (const u of ["https://a.az/1.jpg", "https://wsrv.nl/?url=https%3A%2F%2Fa.az%2F1.jpg&w=1080&h=1080&fit=cover&a=attention&output=jpg&q=80", "https://wsrv.nl/x?url=a&w=1&output=webp", "http://wsrv.nl/?url=a&w=1&output=webp", "https://evil.az/?url=a&w=640&output=webp", "nə"]) assert.equal(I.toHost(u, HOST), "", u);
});

test("sekil-isit 4: few requests at a time, each with a timeout; a hanging host cannot hold the slow cycle past the total limit", async () => {
  const urls = Array.from({ length: 12 }, (_, i) => `https://${HOST}/?url=https%3A%2F%2Fa.az%2F${i}.jpg&w=360&we&output=webp&q=70`);
  let open = 0, most = 0;
  const done = await I.warm(urls, { fetchImpl: async (u, opts) => {
    assert.ok(opts.signal instanceof AbortSignal, "hər sorğunun vaxt həddi var");
    open++; most = Math.max(most, open);
    await new Promise(r => setTimeout(r, 5));
    open--;
    return webp();
  } });
  assert.equal(done.length, 12);
  assert.ok(done.every(r => r.ok && r.from === "wsrv"));
  assert.ok(most <= I.PARALLEL && I.PARALLEL <= 4, "eyni anda ən çox " + I.PARALLEL);
  assert.ok(I.ASK_MS <= 15000 && I.TOTAL_MS <= 40000, "pipeline-ın 45 s həddindən qısa");
  // Asılan server: hər sorğu öz həddində kəsilir, bütün iş totalMs-də bitir.
  const hang = (u, opts) => new Promise((_, no) => opts.signal.addEventListener("abort", () => no(opts.signal.reason)));
  const t0 = Date.now();
  const slow = await I.warm(urls, { askMs: 150, totalMs: 400, fetchImpl: hang });
  assert.ok(Date.now() - t0 < 1500, "ümumi hədd: " + (Date.now() - t0));
  assert.ok(slow.length < urls.length && slow.every(r => !r.ok && r.status === "vaxt"));
  const bad = await I.warm(urls.slice(0, 2), { fetchImpl: async () => { throw new TypeError("fetch failed"); } });
  assert.deepEqual(bad.map(r => r.status), ["şəbəkə", "şəbəkə"]);
});

test("sekil-isit 5: a warmed picture is not asked again; a failed one is retried in the next slow cycle", async () => {
  const mem = path.join(tmp(), "isit.json"), seen = [];
  const run = fetchImpl => I.main([root, path.join(root, "data/first.json"), mem], { IMG_HOST: HOST }, { fetchImpl: async (u, o) => { seen.push(u); return fetchImpl(u, o); } });
  let fail = "";
  const r1 = await run(async u => { if (!fail) { fail = u; return new Response("1027", { status: 429, headers: { "Content-Type": "text/html" } }); } return webp(); });
  assert.ok(r1.all <= I.MAX_PER_RUN, "bir dövrədə hamısı");
  assert.equal(r1.asked, r1.all);
  assert.equal(r1.ok, r1.all - 1);
  assert.ok(seen.every(u => u.startsWith(`https://${HOST}/?url=`)));
  seen.length = 0;
  const r2 = await run(async () => webp());
  assert.deepEqual(seen, [fail], "yalnız alınmayan şəkil yenidən");
  assert.equal(r2.ok, 1);
  seen.length = 0;
  await run(async () => webp());
  assert.deepEqual(seen, [], "hamısı isidilib");
  // Yaddaş MEMORY_H saatdan sonra unudulur (fayl böyümür).
  seen.length = 0;
  await I.main([root, path.join(root, "data/first.json"), mem], { IMG_HOST: HOST }, { now: Date.now() + 49 * 3600e3, fetchImpl: async u => { seen.push(u); return webp(); } });
  assert.equal(seen.length, r1.all);
});

test("sekil-isit 6: the slow cycle runs it only with IMG_HOST, under a hard timeout, after the slow work; the fast loop does not call it; the workflow passes the repo variable", () => {
  const sh = fs.readFileSync(path.join(root, ".github/scripts/pipeline.sh"), "utf8");
  const fn = sh.match(/\nsekil_isit\(\) \{\n([\s\S]*?)\n\}\n/);
  assert.ok(fn, "sekil_isit funksiyası");
  assert.match(fn[1], /\[ -n "\$\{IMG_HOST:-\}" \]/);
  assert.match(fn[1], /timeout -k 5 45 node "\$REPO_DIR\/\.github\/scripts\/sekil-isit\.cjs" "\$REPO_DIR" "\$WORK\/data\/first\.json" "\$STATE\/sekil-isit\.json"/);
  assert.match(fn[1], /return 0$/, "xəta yavaş dövrəni də dayandırmır");
  const slow = sh.match(/\nslow_loop\(\) \{\n([\s\S]*?)\n\}\n/)[1];
  assert.match(slow, /run_py --slow[^\n]*\n\s*milli_step\n\s*sekil_isit\n/, "yavaş dövrədə, yavaş işdən sonra");
  const fast = sh.slice(sh.indexOf("\nwhile :; do\n  began=$SECONDS"));
  assert.ok(fast.length > 100 && !fast.includes("sekil_isit") && !fast.includes("sekil-isit"), "sürətli dövrəyə şəbəkə işi əlavə olunmur");
  const wf = fs.readFileSync(path.join(root, ".github/workflows/update.yml"), "utf8");
  assert.ok(wf.includes("IMG_HOST: ${{ vars.IMG_HOST }}"), "update.yml repo dəyişənini ötürür");
});
