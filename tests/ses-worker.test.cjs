// «Dinlə» mətn serveri (.github/ses-worker/worker.js, Cloudflare Workers): basılan anda xəbərin tam mətni (sahib, 2026-11-08).
const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs"), path = require("node:path"), { pathToFileURL } = require("node:url");
const load = () => import(pathToFileURL(path.join(__dirname, "..", ".github/ses-worker/worker.js")).href);
const para = "Bu xəbərin mətni kifayət qədər uzundur və oxucuya hadisə haqqında ətraflı məlumat verir. ";

test("ses-worker: article text comes from JSON-LD first, then from the article's paragraphs; paywalled stories give nothing", async () => {
  const { extract } = await load();
  assert.equal(extract(`<script type="application/ld+json">{"@type":"NewsArticle","articleBody":"${para.repeat(4)}"}</script>`), para.repeat(4).trim());
  assert.equal(extract(`<script type="application/ld+json">{"@type":"NewsArticle","isAccessibleForFree":false,"articleBody":"${para.repeat(4)}"}</script>`), "");
  const html = `<nav><p>${para}menyu</p></nav><article><h1>Başlıq</h1><p>${para}${para}</p><p>${para}ikinci</p><p>© Bütün hüquqlar qorunur, bu mətn çox uzun olsa da</p></article>`;
  const t = extract(html);
  assert.ok(t.includes("ikinci") && !t.includes("menyu") && !t.includes("Bütün hüquqlar"));
});

test("ses-worker: paragraphs glued by the source get a space so the voice pauses between sentences", async () => {
  const { clean } = await load();
  assert.equal(clean("Zəfər günüdür.Bu gün bayramdır!Ölkə sevinir."), "Zəfər günüdür. Bu gün bayramdır! Ölkə sevinir.");
  assert.equal(clean("Qiymət 1.75 manatdır, sayt report.az-dır."), "Qiymət 1.75 manatdır, sayt report.az-dır.");
});

test("ses-worker: only requests from 8ulduz.az are served and only https source addresses", async () => {
  const { default: w } = await load();
  const call = (u, ref) => w.fetch(new Request(`https://x.workers.dev/?u=${encodeURIComponent(u)}`, { headers: ref ? { Referer: ref } : {} }), {}, { waitUntil() {} });
  assert.equal((await call("https://apa.az/1", "https://evil.example/")).status, 403);
  assert.equal((await call("https://apa.az/1")).status, 403);
  assert.equal((await call("http://127.0.0.1/admin", "https://8ulduz.az/")).status, 400);
  assert.equal((await call("https://localhost/x", "https://8ulduz.az/")).status, 400);
});

// Cloudflare mühitinin kiçik əvəzi: keş və şəbəkə.
function cfEnv(routes) {
  const store = new Map(), calls = [];
  globalThis.caches = { default: { match: async r => store.get(r.url)?.clone(), put: async (r, res) => { store.set(r.url ?? r, res); } } };
  const real = globalThis.fetch;
  globalThis.fetch = async (u, o = {}) => { calls.push({ u: String(u), o }); for (const [re, fn] of routes) if (re.test(String(u))) return fn(String(u), o); return new Response("", { status: 404 }); };
  const waits = [];
  return { calls, ctx: { waitUntil: p => waits.push(p) }, done: () => Promise.all(waits), restore: () => { globalThis.fetch = real; } };
}
const ses = (q, ref = "https://8ulduz.az/") => new Request(`https://dinle.x/ses?${q}`, { headers: { Referer: ref } });
const page = `<script type="application/ld+json">{"@type":"NewsArticle","articleBody":"${"Napoli klubunun prezidenti baş məşqçi ilə görüşüb və vəziyyəti müzakirə edib. ".repeat(4)}"}</script>`;

test("ses-worker /ses: «not ready yet» is never cached, so a voice is served the minute it is ready (owner: «anında»)", () => {
  const js = fs.readFileSync(path.join(__dirname, "..", ".github/ses-worker/worker.js"), "utf8");
  assert.ok(js.includes('cacheTtlByStatus: { "200-299": 300, "400-599": -1 }'), "404 keşlənmir");
  assert.ok(js.includes('.mp3?m=${Math.floor(Date.now() / 6e4)}'), "GitHub-ın öz keşindəki köhnə 404 da yan keçilir");
});

test("ses-worker /ses: a prepared voice file is served at once (no Azure call)", async () => {
  const { default: w } = await load();
  const env = cfEnv([[/raw\.githubusercontent\.com\/8ulduz\/ses\/main\/0123456789abcdef\.mp3/, () => new Response(new Uint8Array(5000), { status: 200 })]]);
  try {
    const r = await w.fetch(ses("u=" + encodeURIComponent("https://apa.az/1") + "&id=0123456789abcdef"), { AZURE_KEY: "k" }, env.ctx);
    assert.equal(r.status, 200); assert.equal(r.headers.get("Content-Type"), "audio/mpeg");
    assert.equal((await r.arrayBuffer()).byteLength, 5000);
    assert.ok(!env.calls.some(c => /tts\.speech\.microsoft\.com/.test(c.u)));
  } finally { env.restore(); }
});

test("ses-worker /ses: not prepared yet → the full source text in Microsoft's official Babək voice (Azure), streamed", async () => {
  const { default: w } = await load();
  const env = cfEnv([[/sportinfo\.az/, () => new Response(page, { headers: { "content-type": "text/html" } })],
    [/westeurope\.tts\.speech\.microsoft\.com/, () => new Response(new Uint8Array(8000), { status: 200, headers: { "content-type": "audio/mpeg" } })]]);
  try {
    const r = await w.fetch(ses("u=" + encodeURIComponent("https://sportinfo.az/1") + "&id=aaaaaaaaaaaaaaaa&t=Klub%20prezidenti&s=Sportinfo"), { AZURE_KEY: "k" }, env.ctx);
    assert.equal(r.status, 200); assert.equal((await r.arrayBuffer()).byteLength, 8000);
    const az = env.calls.find(c => /tts\.speech\.microsoft\.com/.test(c.u));
    assert.equal(az.o.headers["Ocp-Apim-Subscription-Key"], "k");
    assert.ok(az.o.body.includes("az-AZ-BabekNeural") && az.o.body.includes("Klub prezidenti. Sportinfo xəbər verir. Napoli klubunun"), az.o.body.slice(0, 200));
    await env.done();
    const again = await w.fetch(ses("u=" + encodeURIComponent("https://sportinfo.az/1") + "&id=aaaaaaaaaaaaaaaa"), { AZURE_KEY: "k" }, env.ctx);
    assert.equal(again.status, 200); assert.equal(env.calls.filter(c => /tts\.speech/.test(c.u)).length, 1, "ikinci dinləyici keşdən alır");
  } finally { env.restore(); }
});

test("ses-worker /ses: without the Azure key (or when the free limit is used up) it answers 503 and the site waits for the prepared voice", async () => {
  const { default: w } = await load();
  const env = cfEnv([[/westeurope\.tts/, () => new Response("quota", { status: 429 })], [/apa\.az/, () => new Response(page, { headers: { "content-type": "text/html" } })]]);
  try {
    assert.equal((await w.fetch(ses("u=" + encodeURIComponent("https://apa.az/2")), {}, env.ctx)).status, 503);
    assert.equal((await w.fetch(ses("u=" + encodeURIComponent("https://apa.az/2")), { AZURE_KEY: "k" }, env.ctx)).status, 503);
    assert.equal((await w.fetch(ses("u=" + encodeURIComponent("https://apa.az/2"), "https://evil.example/"), { AZURE_KEY: "k" }, env.ctx)).status, 403);
  } finally { env.restore(); }
});
