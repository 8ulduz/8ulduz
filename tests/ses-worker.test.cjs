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

test("ses-worker: junk under the article is not read (owner: «xəbərin altındakı lazımsız şeyləri də oxuyur»)", async () => {
  const { extract } = await load();
  const page = '<article><p>Bakıda bu gün g&amp;uuml;n ərzində yağış yağıb. ' + para + '</p><p>İkinci abzas: ' + para + para + '</p>' +
    '<p>Xəbər xoşunuza gəldi? Sosial şəbəkələrdə paylaşın</p><p>Ən son xəbərləri bizim WhatsApp kanalımızda izləyin @media</p>' +
    '<p>Mətndə səhv varsa, onu qeyd edib Ctrl+Enter düyməsini basaraq bizə göndərin.</p>' +
    '<p class="bold-title">Dövlət və hökumət rəsmiləri Zəfər Tağı abidəsini ziyarət etdilər</p>' +
    '<p>Nazir: Ərazi bütövlüyünün bərpası Azərbaycanın qüdrətini daha da artırdı</p>' +
    '<p>The web server is not returning a connection. As a result, the web page is not displaying.</p>' +
    '<p>Oxşar xəbərlər</p><p>Bu abzas oxşar xəbərlər bölməsindədir və oxunmamalıdır, çünki xəbərin özü deyil. ' + para + '</p></article>';
  const t = extract(page);
  assert.ok(t.includes("İkinci abzas") && t.includes("gün ərzində"), t.slice(0, 120));
  for (const junk of ["paylaşın", "WhatsApp", "Ctrl", "Zəfər Tağı", "Ərazi bütövlüyünün", "web server", "oxunmamalıdır", "&"]) assert.ok(!t.includes(junk), junk);
  assert.ok(extract('<p>Son xəbərlərə görə, ' + para + '</p><p>' + para + para + '</p>').startsWith("Son xəbərlərə görə"), "«Son xəbərlərə görə» ilə başlayan cümlə kəsilmir");
  const ld = '<script type="application/ld+json">' + JSON.stringify({ "@type": "NewsArticle", articleBody: para.repeat(3) + "Hörmətli istifadəçi, ödənişli xəbərləri əldə etmək üçün qeydiyyatdan keçin. {{photo-big-1}}" }) + "</script>";
  assert.equal(extract(ld), para.repeat(3).trim());
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

test("ses-worker /ses: not prepared yet → the full source text in Microsoft's official Babək voice (Azure), streamed; the title starts at once and the rest follows", async () => {
  const { default: w } = await load();
  const env = cfEnv([[/sportinfo\.az/, () => new Response(page, { headers: { "content-type": "text/html" } })],
    [/westeurope\.tts\.speech\.microsoft\.com/, () => new Response(new Uint8Array(8000), { status: 200, headers: { "content-type": "audio/mpeg" } })]]);
  try {
    const r = await w.fetch(ses("u=" + encodeURIComponent("https://sportinfo.az/1") + "&id=aaaaaaaaaaaaaaaa&t=Klub%20prezidenti&s=Sportinfo"), { AZURE_KEY: "k" }, env.ctx);
    assert.equal(r.status, 200); assert.equal((await r.arrayBuffer()).byteLength, 16000, "başlıq + mətnin qalanı bir axında");
    const az = env.calls.filter(c => /tts\.speech\.microsoft\.com/.test(c.u));
    assert.equal(az[0].o.headers["Ocp-Apim-Subscription-Key"], "k");
    assert.ok(az[0].o.body.includes("az-AZ-BabekNeural") && az[0].o.body.includes("Klub prezidenti. Sportinfo xəbər verir.</voice>"), "əvvəl yalnız başlıq + mənbə — dərhal");
    assert.ok(az[1].o.body.includes(">Napoli klubunun"), "mətnin qalanı arxasınca, başlıq təkrarlanmadan");
    await env.done();
    const again = await w.fetch(ses("u=" + encodeURIComponent("https://sportinfo.az/1") + "&id=aaaaaaaaaaaaaaaa"), { AZURE_KEY: "k" }, env.ctx);
    assert.equal(again.status, 200); assert.equal(env.calls.filter(c => /tts\.speech/.test(c.u)).length, 2, "ikinci dinləyici keşdən alır");
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

// Sahib, 2026-11-12: «dinləməni tam düzəlt hər bir saytda» — reader_content.py-nin DenseTextTest sınaqlarının eynisi:
// hazır səs (ses.py) və anında səs (bu server) eyni mətni oxumalıdır.
const P1 = "Dövlət Sosial Müdafiə Fondu noyabrın 25-də Ucar rayonunda sığortaedənlər üçün təlim keçirəcək. Təlimdə yeni qaydalar izah olunacaq.";
const P2 = "Tədbirdə iştirak etmək istəyənlər Fondun qəbul şöbəsinə yaxınlaşa bilərlər. Qeydiyyat noyabrın 24-dək davam edir.";
const P3 = "Fonddan bildirilib ki, belə görüşlər digər rayonlarda da keçiriləcək və vətəndaşların sualları yerində cavablandırılacaq.";

test("ses-worker: sites with unknown class names are read from the block with most prose (DSMF, Teleqraf, Reyting, Aia.az)", async () => {
  const { extract } = await load();
  let t = extract(`<header><p>${P1} menyu.</p></header><div class="tarih">12 NOYABR 2026</div><h1>Başlıq oxunmur</h1>` +
    `<div class="inner__text"><p>${P1}</p><p>${P2}</p><div class="ads"></div><p>${P3}</p><p>Teqlər: DSMF   Ucar   təlim</p></div>` +
    `<div class="widget"><p>${para.repeat(5)}</p></div><div class="related"><p>${para.repeat(5)}</p></div>`);
  assert.ok(t.startsWith("Dövlət Sosial Müdafiə Fondu") && t.endsWith("cavablandırılacaq."), t);
  for (const junk of ["NOYABR 2026", "Başlıq oxunmur", "Teqlər", "menyu", "ətraflı məlumat"]) assert.ok(!t.includes(junk), junk);
  t = extract(`<div class="xeber"><span class="short" style="text-align: justify">${P1}<br><br>${P2}<br>${P3}</span></div><div class="altyazi1">© Copyright 2015. Bütün hüquqlar qorunur.</div>`);
  assert.ok(t.includes("yaxınlaşa bilərlər") && !t.includes("Copyright"), "<br> ilə ayrılmış mətn (Aia.az)");
});

test("ses-worker: the block matching the page's own description wins; dates, view counts and headline feeds are not read", async () => {
  const { extract } = await load();
  const t = extract(`<meta property="og:description" content="${P1}"><div class="other"><p>${para.repeat(5)}</p><p>${para.repeat(6)}</p></div><div class="project_info"><p>${P1}</p><p>${P2}</p></div>`);
  assert.ok(t.startsWith("Dövlət Sosial Müdafiə Fondu") && !t.includes("ətraflı məlumat"), "Ordu.az: məqalədən uzun «digər xəbərlər» bloku seçilirdi");
  const feed = [1, 2, 3, 4, 5, 6].map(i => `<li>1${i}:40 Premyer Liqanın ${i}-ci turunda mübahisəli anlar çox olub. Səhv kimdədir?</li>`).join("");
  assert.equal(extract(`<div class="news-content"><div>12 noyabr 2026 Xəbərlərimizi Google-da izləyin. Abunə ol. 254 baxış.</div><ul>${feed}</ul></div>`), "", "Baku TV video səhifəsi: tarix və baxış sayı oxunmur");
  assert.equal(extract(`<div class="news-content"><ul>${feed.replaceAll("<li>1", "<li>11 Noyabr 1")}</ul></div>`), "", "Sportinfo: saatlı xəbər lenti mətn deyil");
  const short = "Aktyor Natiq Fərzəliyevin səhhətində problem yaranıb. Onun əməliyyat olunduğu və özünü yaxşı hiss etdiyi bildirilib.";
  assert.equal(extract(`<div class="x"><p>${short}</p></div>`), "");
  assert.equal(extract(`<meta name="description" content="${short}"><div class="x"><p>${short}</p></div>`), short, "qısa xəbər yalnız səhifənin öz təsviridirsə");
  assert.equal(extract(`<title>${short} - Sayt</title><meta name="description" content="${short}"><div class="x"><p>${short}</p></div>`), "", "təsvir başlığın özüdürsə mətni göstərmir");
});

test("ses-worker: the tokenizer skips scripts and comments and survives broken markup", async () => {
  const { tokenize, extract } = await load();
  const toks = tokenize(`<div class='a b' id=x><!-- <p>şərh</p> --><script>var s = "<p>kod</p>";</script><br/>mətn < 5<p class="t">bir</p></div>`);
  assert.deepEqual(toks.filter(t => t[0] !== "t").map(t => t[0] + t[1]), ["odiv", "obr", "cbr", "op", "cp", "cdiv"]);
  assert.deepEqual(toks[0][2], { class: "a b", id: "x" });
  assert.ok(!toks.some(t => t[0] === "t" && /kod|şərh/.test(t[2])));
  assert.equal(extract("<div><p>" + P1 + "</p><p>" + P2 + "</div></span></p><<<"), `${P1} ${P2}`);
});
