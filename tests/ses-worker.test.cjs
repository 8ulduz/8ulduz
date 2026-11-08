// «Dinlə» mətn serveri (.github/ses-worker/worker.js, Cloudflare Workers): basılan anda xəbərin tam mətni (sahib, 2026-11-08).
const test = require("node:test");
const assert = require("node:assert/strict");
const path = require("node:path"), { pathToFileURL } = require("node:url");
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

test("ses-worker: only requests from 8ulduz.az are served and only https source addresses", async () => {
  const { default: w } = await load();
  const call = (u, ref) => w.fetch(new Request(`https://x.workers.dev/?u=${encodeURIComponent(u)}`, { headers: ref ? { Referer: ref } : {} }), {}, { waitUntil() {} });
  assert.equal((await call("https://apa.az/1", "https://evil.example/")).status, 403);
  assert.equal((await call("https://apa.az/1")).status, 403);
  assert.equal((await call("http://127.0.0.1/admin", "https://8ulduz.az/")).status, 400);
  assert.equal((await call("https://localhost/x", "https://8ulduz.az/")).status, 400);
});
