// Şəkil keşi (.github/img-worker/worker.js, Cloudflare Workers + R2): img.8ulduz.az saytın wsrv.nl sorğusunun eynisini qəbul edir,
// şəkli əvvəl düyünün keşindən, sonra R2-dən, yoxdursa wsrv.nl-dən verir (sahib, 2026-11-27: «Bəli, qur»; docs/img-worker.md).
const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs"), path = require("node:path"), { pathToFileURL } = require("node:url");
const root = path.join(__dirname, "..");
const load = () => import(pathToFileURL(path.join(root, ".github/img-worker/worker.js")).href);
const read = f => fs.readFileSync(path.join(root, f), "utf8");

const SRC = "https://apa.az/storage/news/2026/11/27/şəkil (1).jpg?a=1&b=2";
// Saytın öz sırası (app.js sized): url, w, we, output, q.
const siteQuery = (src = SRC, w = 640) => `url=${encodeURIComponent(src)}&w=${w}&we&output=webp&q=70`;
const WEBP = new Uint8Array([82, 73, 70, 70, 36, 0, 0, 0, 87, 69, 66, 80, 86, 80, 56, 32]); // «RIFF....WEBPVP8 »
const pic = (type = "image/webp", body = WEBP, extra = {}) => new Response(body, { status: 200, headers: { "Content-Type": type, ...extra } });

// fetch əvəzi: ünvan → cavab (və ya funksiya); soruşulan ünvanlar `seen`-də. Siyahıda olmayan ünvan 404.
function world(routes = {}) {
  const seen = [];
  globalThis.fetch = async (url, opts = {}) => {
    seen.push(String(url));
    assert.ok(opts.signal instanceof AbortSignal, "wsrv.nl sorğusunun vaxt həddi var");
    const r = routes[String(url)] ?? routes["*"];
    if (r instanceof Error) throw r;
    if (typeof r === "function") return r(url, opts);
    return r || new Response("not found", { status: 404, headers: { "Content-Type": "application/json" } });
  };
  return seen;
}
function memoryCache() {
  const store = new Map(), log = [];
  globalThis.caches = { default: {
    match: async req => { log.push("match " + req.url); const r = store.get(req.url); return r && r.clone(); },
    put: async (req, res) => { log.push("put " + req.url); store.set(req.url, res); },
  } };
  return { store, log };
}
function memoryR2() {
  const store = new Map(), log = [];
  const SEKIL = {
    get: async k => { log.push("get " + k); const v = store.get(k); return v ? { httpMetadata: v.meta, arrayBuffer: async () => v.body.slice(0) } : null; },
    put: async (k, body, opts) => { log.push("put " + k); store.set(k, { body: new Uint8Array(body).slice(0), meta: opts?.httpMetadata }); },
  };
  return { store, log, env: { SEKIL } };
}
// Bir sorğu və onun waitUntil-ləri (yazılar bitənə qədər gözlənilir).
async function call(w, u, env = {}, init = {}) {
  const waited = [];
  const res = await w.default.fetch(new Request(u, init), env, { waitUntil: p => waited.push(p) });
  await Promise.all(waited);
  return res;
}
const img = (q = siteQuery()) => `https://img.8ulduz.az/?${q}`;
test.beforeEach(() => { delete globalThis.caches; });

test("img-worker 1: /saglam answers ok for the deploy check; other paths and methods are refused without touching the network", async () => {
  const w = await load();
  const seen = world({ "*": () => pic() });
  let r = await call(w, "https://img.8ulduz.az/saglam");
  assert.equal(r.status, 200);
  assert.equal(await r.text(), "ok");
  assert.equal(r.headers.get("Cache-Control"), "no-store");
  r = await call(w, "https://img.8ulduz.az/favicon.ico");
  assert.equal(r.status, 404);
  r = await call(w, img(), {}, { method: "POST", body: "x" });
  assert.equal(r.status, 405);
  assert.equal(r.headers.get("Allow"), "GET, HEAD");
  assert.deepEqual(seen, [], "heç biri wsrv.nl-ə getmir");
});

test("img-worker 2: only the site's own query is accepted — its parameters, its widths, webp, q=70 and an http(s) source; everything else is 400", async () => {
  const w = await load();
  const seen = world({ "*": () => pic() });
  const enc = encodeURIComponent(SRC);
  const bad = [
    "", "url=" + enc, `url=${enc}&w=640&we&output=webp`, // çatışmayan
    `url=${enc}&w=640&we&output=webp&q=70&h=630`, `url=${enc}&w=640&we&output=webp&q=70&fit=cover`, // artıq parametr
    `url=${enc}&w=640&w=480&we&output=webp&q=70`, `url=${enc}&url=${enc}&w=640&we&output=webp&q=70`, // təkrar
    `url=${enc}&w=640&we&output=jpg&q=70`, `url=${enc}&w=640&we&output=png&q=70`, `url=${enc}&w=640&we&q=70&output=webp%20`, // yalnız webp
    `url=${enc}&w=640&we&output=webp&q=90`, `url=${enc}&w=640&we=1&output=webp&q=70`, // q=70, we bayraqdır
    `url=${enc}&w=641&we&output=webp&q=70`, `url=${enc}&w=4000&we&output=webp&q=70`, `url=${enc}&w=0640&we&output=webp&q=70`, `url=${enc}&w=-640&we&output=webp&q=70`, `url=${enc}&w=640.0&we&output=webp&q=70`, // en
    siteQuery("ftp://apa.az/a.jpg"), siteQuery("javascript:alert(1)"), siteQuery("data:image/png;base64,AAAA"), siteQuery("//apa.az/a.jpg"), siteQuery("/assets/a.jpg"), siteQuery("apa.az/a.jpg"), // yalnız http(s)
    siteQuery("https://user:pass@apa.az/a.jpg"), siteQuery("https://"), siteQuery("https://apa.az/a\nb.jpg"), siteQuery("https://apa.az/" + "a".repeat(2100)),
    siteQuery("https://img.8ulduz.az/?url=x"), siteQuery("https://wsrv.nl/?url=https%3A%2F%2Fapa.az%2Fa.jpg"), // proksinin özü: dövrə yox
  ];
  for (const q of bad) {
    const r = await call(w, img(q));
    assert.equal(r.status, 400, q.slice(0, 120));
    assert.equal(r.headers.get("Cache-Control"), "no-store");
    assert.match(r.headers.get("Content-Type"), /^text\/plain/);
  }
  assert.deepEqual(seen, [], "yararsız sorğu wsrv.nl-ə getmir");
  for (const ok of [siteQuery(), siteQuery("http://report.az/a.png", 360), siteQuery("HTTPS://Oxu.az/A.JPG", 168)]) assert.equal((await call(w, img(ok))).status, 200, ok);
});

test("img-worker 3: every width the site's code asks for is allowed (app.js, futbol.js, komanda.js, lent.js, vlent.js), and the query is the one they build", async () => {
  const { WIDTHS } = await load();
  const used = new Set();
  const nums = (src, re, k = 1) => { for (const m of src.matchAll(re)) for (const n of m.slice(1)) if (n) used.add(+n * k); };
  const app = read("assets/app.js"), futbol = read("assets/futbol.js"), komanda = read("assets/komanda.js"), lent = read("assets/lent.js"), vlent = read("assets/vlent.js");
  const call = /\b(?:sized|img)\((?:[^()]|\((?:[^()]|\([^()]*\))*\))*?,\s*(\d{2,4})\s*(?:,\s*1\s*)?\)/g; // sized(…, 360), img(a, "", …, 960)
  for (const src of [app, futbol, komanda]) nums(src, call);
  nums(app, /function img\([^)]*width = (\d+)/g);                         // img()-in standart eni
  nums(app, /function heroPicWidth[\s\S]*?\? (\d+) : (\d+);/g);            // slayd: 640 / 480
  nums(komanda, /\blogo\([^()]*?,\s*(\d+)\s*(?:,|\))/g, 2);                // komanda loqosu: sized(url, size * 2, 1)
  nums(lent, /\bpx\([^()]*?,\s*(\d+)\)/g);                                // Videolent posteri
  nums(vlent, /&w=(\d+)&we&output=webp&q=70/g);                           // video kartı
  for (const w of [640, 480, 360, 168, 960, 720, 96]) assert.ok(used.has(w), `axtarış ${w}-i tapmadı: ifadəni yeniləyin`);
  assert.deepEqual([...used].filter(w => !WIDTHS.has(w)).sort((a, b) => a - b), [], "saytın istədiyi en Worker-də yoxdur: şəkil 400 alıb wsrv.nl-ə düşər — WIDTHS-ə əlavə edin");
  // Sorğu forması: saytın üç qurucusu eyni sırada; Worker də wsrv.nl-ə bu sıra ilə gedir.
  assert.ok(app.includes("?url=${encodeURIComponent(url)}&w=${width}&we&output=webp&q=70`"), "app.js sized");
  assert.ok(lent.includes("?url=${encodeURIComponent(u)}&w=${w}&we&output=webp&q=70`"), "lent.js px");
  assert.ok(vlent.includes("?url=${encodeURIComponent(u)}&w=360&we&output=webp&q=70`"), "vlent.js");
});

test("img-worker 4: the key is canonical — parameter order and «we» ↔ «we=» give one cache entry, one R2 object and one wsrv.nl query in the site's order", async () => {
  const w = await load();
  const enc = encodeURIComponent(SRC);
  const variants = [siteQuery(), `w=640&we&output=webp&q=70&url=${enc}`, `q=70&output=webp&we=&w=640&url=${enc}`, `url=${enc}&we&w=640&q=70&output=webp`];
  const seen = world({ [`https://wsrv.nl/?${siteQuery()}`]: () => pic() });
  const c = memoryCache(), b = memoryR2();
  for (const q of variants) {
    const a = w.canonical(new URLSearchParams(q));
    assert.equal(a.query, siteQuery(), q);
    assert.equal(a.src, SRC);
    assert.equal(a.w, 640);
  }
  for (const q of variants) assert.equal((await call(w, img(q), b.env)).status, 200, q);
  assert.deepEqual(seen, [`https://wsrv.nl/?${siteQuery()}`], "wsrv.nl bir dəfə, saytın öz sırası ilə (onun keşindəki nüsxə də işə yarayır)");
  assert.deepEqual([...c.store.keys()], [img()], "bir keş girişi");
  assert.deepEqual([...b.store.keys()], [await w.r2Key(siteQuery())], "bir R2 obyekti");
  assert.match(await w.r2Key(siteQuery()), /^v1\/[0-9a-f]{64}$/);
  assert.notEqual(await w.r2Key(siteQuery(SRC, 360)), await w.r2Key(siteQuery()), "hər en ayrı obyektdir");
  // Mənbə ünvanı olduğu kimi qalır (yalnız kodlanır): sayt encodeURIComponent ilə göndərir, Worker eyni sətri qaytarır.
  assert.equal(w.canonical(new URLSearchParams(siteQuery("https://a.az/x+y z.jpg?q=1&r=%2F"))).query, siteQuery("https://a.az/x+y z.jpg?q=1&r=%2F"));
});

test("img-worker 5: lookup order — edge cache first, then R2, then wsrv.nl; a fetched picture goes to R2 and the edge in waitUntil", async () => {
  const w = await load();
  let fetched = 0;
  const seen = world({ [`https://wsrv.nl/?${siteQuery()}`]: () => { fetched++; return pic(); } });
  const c = memoryCache(), b = memoryR2();
  const name = await w.r2Key(siteQuery());
  // Soyuq: keş → R2 → wsrv.nl; cavab dərhal, yazılar waitUntil-də.
  const waited = [];
  let r = await w.default.fetch(new Request(img()), b.env, { waitUntil: p => waited.push(p) });
  assert.equal(r.status, 200);
  assert.equal(r.headers.get("X-Sekil"), "wsrv");
  assert.deepEqual(new Uint8Array(await r.arrayBuffer()), WEBP);
  assert.equal(waited.length, 1, "R2 və keş yazısı cavabı gözlətmir");
  await Promise.all(waited);
  assert.deepEqual(c.log, [`match ${img()}`, `put ${img()}`]);
  assert.deepEqual(b.log, [`get ${name}`, `put ${name}`]);
  assert.equal(b.store.get(name).meta.contentType, "image/webp");
  assert.deepEqual(b.store.get(name).body, WEBP);
  // İsti düyün: yalnız keş, nə R2, nə wsrv.nl.
  c.log.length = 0; b.log.length = 0;
  r = await call(w, img(), b.env);
  assert.equal(r.headers.get("X-Sekil"), "edge");
  assert.deepEqual(new Uint8Array(await r.arrayBuffer()), WEBP);
  assert.deepEqual(b.log, [], "keşdə olanda R2 soruşulmur");
  assert.equal(fetched, 1);
  // Başqa düyün (keşi boş): R2-dən, wsrv.nl-siz; nüsxə həmin düyünün keşinə yazılır.
  const c2 = memoryCache();
  b.log.length = 0;
  r = await call(w, img(), b.env);
  assert.equal(r.status, 200);
  assert.equal(r.headers.get("X-Sekil"), "r2");
  assert.equal(r.headers.get("Content-Type"), "image/webp");
  assert.deepEqual(new Uint8Array(await r.arrayBuffer()), WEBP);
  assert.deepEqual(b.log, [`get ${name}`], "R2-dən oxunur, yenidən yazılmır");
  assert.deepEqual(c2.log, [`match ${img()}`, `put ${img()}`]);
  assert.equal(fetched, 1, "wsrv.nl ikinci dəfə soruşulmur");
  assert.equal(seen.length, 1);
});

test("img-worker 6: only a 200 raster picture under the size cap is stored; wsrv.nl errors pass as error statuses (no-store), so the site's imgFail moves on", async () => {
  const w = await load();
  const big = new Uint8Array(w.MAX_BYTES + 1);
  const cases = [
    [() => new Response('{"status":"error","message":"not found"}', { status: 404, headers: { "Content-Type": "application/json" } }), 404],
    [() => new Response("rate", { status: 429, headers: { "Content-Type": "text/plain" } }), 429],
    [() => new Response("oops", { status: 500, headers: { "Content-Type": "text/html" } }), 502],
    [() => new Response("<html>1027</html>", { status: 200, headers: { "Content-Type": "text/html" } }), 502],
    [() => pic("image/svg+xml", "<svg onload=alert(1)>"), 502],
    [() => pic("application/octet-stream"), 502],
    [() => pic("image/webp", WEBP, { "Content-Length": String(w.MAX_BYTES + 1) }), 502],
    [() => pic("image/webp", big), 502],
    [() => pic("image/webp", new Uint8Array(0)), 502],
    [() => new Response(WEBP, { status: 206, headers: { "Content-Type": "image/webp" } }), 502],
    [() => new Response(null, { status: 302, headers: { Location: "https://wsrv.nl/x" } }), 502],
  ];
  for (const [answer, status] of cases) {
    world({ "*": answer });
    const c = memoryCache(), b = memoryR2();
    const r = await call(w, img(), b.env);
    assert.equal(r.status, status, String(answer));
    assert.equal(r.headers.get("Cache-Control"), "no-store", "xəta keşlənmir");
    assert.notEqual(r.headers.get("Content-Type"), "image/webp", "qırıq şəkil yox, xəta");
    assert.deepEqual(c.log.filter(x => x.startsWith("put")), [], "keşə yazılmır");
    assert.deepEqual(b.log.filter(x => x.startsWith("put")), [], "R2-yə yazılmır");
  }
  for (const type of ["image/jpeg", "image/png", "image/webp; charset=binary"]) {
    world({ "*": () => pic(type) });
    memoryCache();
    const b = memoryR2();
    const r = await call(w, img(), b.env);
    assert.equal(r.status, 200, type);
    assert.equal(r.headers.get("Content-Type"), type.split(";")[0]);
    assert.equal(b.store.size, 1);
  }
});

test("img-worker 7: a wsrv.nl timeout is 504 and a network error 502, nothing is stored; the request carries the timeout signal", async () => {
  const w = await load();
  assert.ok(w.WSRV_MS >= 4000 && w.WSRV_MS <= 8000, "soyuq wsrv.nl 3,4 s-dək çəkir; oxucu da çox gözləməsin");
  let signal;
  world({ "*": (u, opts) => { signal = opts.signal; throw new DOMException("The operation was aborted due to timeout", "TimeoutError"); } });
  let c = memoryCache(), b = memoryR2();
  let r = await call(w, img(), b.env);
  assert.equal(r.status, 504);
  assert.equal(r.headers.get("Cache-Control"), "no-store");
  assert.ok(signal instanceof AbortSignal);
  assert.deepEqual([...c.log, ...b.log].filter(x => x.startsWith("put")), []);
  world({ "*": new TypeError("fetch failed") });
  c = memoryCache(); b = memoryR2();
  r = await call(w, img(), b.env);
  assert.equal(r.status, 502);
  assert.deepEqual([...c.log, ...b.log].filter(x => x.startsWith("put")), []);
  // Gövdə yarıda kəsilir (vaxt həddi gövdəyə də aiddir).
  world({ "*": () => new Response(new ReadableStream({ pull(ctl) { ctl.error(new DOMException("timeout", "TimeoutError")); } }), { status: 200, headers: { "Content-Type": "image/webp" } }) });
  c = memoryCache(); b = memoryR2();
  r = await call(w, img(), b.env);
  assert.equal(r.status, 504);
  assert.deepEqual([...c.log, ...b.log].filter(x => x.startsWith("put")), []);
  // Uğursuzluqdan sonra növbəti sorğu yenidən wsrv.nl-ə gedir (mənfi keş yoxdur).
  let n = 0;
  world({ "*": () => (++n === 1 ? new Response("x", { status: 503, headers: { "Content-Type": "text/plain" } }) : pic()) });
  c = memoryCache(); b = memoryR2();
  assert.equal((await call(w, img(), b.env)).status, 502);
  assert.equal((await call(w, img(), b.env)).status, 200);
  assert.equal(b.store.size, 1);
});

test("img-worker 8: headers — the picture is immutable for a year, CORS and timing are open, no sniffing; HEAD has the headers without a body", async () => {
  const w = await load();
  world({ "*": () => pic() });
  memoryCache();
  const b = memoryR2();
  for (const from of ["wsrv", "edge"]) {
    const r = await call(w, img(), b.env);
    assert.equal(r.headers.get("X-Sekil"), from);
    assert.equal(r.headers.get("Cache-Control"), "public, max-age=31536000, immutable");
    assert.equal(r.headers.get("Content-Type"), "image/webp");
    assert.equal(r.headers.get("Access-Control-Allow-Origin"), "*");
    assert.equal(r.headers.get("Timing-Allow-Origin"), "*");
    assert.equal(r.headers.get("X-Content-Type-Options"), "nosniff");
    assert.equal(r.headers.get("Set-Cookie"), null);
  }
  assert.equal(b.store.get(await w.r2Key(siteQuery())).meta.cacheControl, w.KEEP);
  const h = await call(w, img(), b.env, { method: "HEAD" });
  assert.equal(h.status, 200);
  assert.equal(h.headers.get("Content-Type"), "image/webp");
  assert.equal(h.headers.get("Cache-Control"), w.KEEP);
  assert.equal((await h.arrayBuffer()).byteLength, 0);
});

test("img-worker 9: a broken cache or R2 never breaks the picture — each layer falls through to the next; without the R2 binding it is an edge-cached proxy", async () => {
  const w = await load();
  const seen = world({ "*": () => pic() });
  globalThis.caches = { default: { match: async () => { throw new Error("cache down"); }, put: async () => { throw new Error("cache down"); } } };
  const broken = { SEKIL: { get: async () => { throw new Error("r2 down"); }, put: async () => { throw new Error("r2 down"); } } };
  let r = await call(w, img(), broken);
  assert.equal(r.status, 200);
  assert.deepEqual(new Uint8Array(await r.arrayBuffer()), WEBP);
  delete globalThis.caches;
  r = await call(w, img(), {});
  assert.equal(r.status, 200, "R2 bağlaması yoxdursa da işləyir");
  const c = memoryCache();
  r = await call(w, img());
  assert.equal(r.status, 200);
  assert.deepEqual(c.log, [`match ${img()}`, `put ${img()}`]);
  assert.equal(seen.length, 3);
});

test("img-worker 10: the config deploys to the 8ulduz.az zone only (custom domain, no workers.dev) with the R2 binding and no secrets; the docs cover the owner's steps", () => {
  const toml = read(".github/img-worker/wrangler.toml");
  assert.match(toml, /^name = "img"$/m);
  assert.match(toml, /^main = "worker\.js"$/m);
  assert.match(toml, /^workers_dev = false$/m);
  assert.match(toml, /^routes = \[\{ pattern = "img\.8ulduz\.az", custom_domain = true \}\]$/m);
  assert.match(toml, /\[\[r2_buckets\]\]\nbinding = "SEKIL"\nbucket_name = "8ulduz-sekil"/);
  assert.ok(!/\[vars\]|secret|token|api_key|account_id/i.test(toml.replace(/^#.*$/gm, "")), "sirr və hesab nömrəsi yoxdur");
  const code = read(".github/img-worker/worker.js");
  assert.ok(code.includes("env?.SEKIL"));
  // Səhifə açıq olarkən soruşulan ünvan yönləndirməməlidir (3xx bfcache-i söndürür; tests/fixtures/ucuncu-terefler.json «yonlendirir»).
  assert.ok(!/Response\.redirect|status:\s*3\d\d|Location/.test(code), "Worker heç vaxt 3xx vermir");
  const doc = read("docs/img-worker.md");
  for (const k of ["8ulduz-sekil", "SEKIL", "img.8ulduz.az", "/saglam", "30", "lifecycle add 8ulduz-sekil", "--expire-days 30", "wrangler login --browser=false", "IMG_HOST", "1027", "X-Sekil"]) assert.ok(doc.includes(k), "docs/img-worker.md: " + k);
});
