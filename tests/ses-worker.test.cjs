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
    const again = await w.fetch(ses("u=" + encodeURIComponent("https://sportinfo.az/1") + "&id=aaaaaaaaaaaaaaaa&t=Klub%20prezidenti&s=Sportinfo"), { AZURE_KEY: "k" }, env.ctx);
    assert.equal(again.status, 200); assert.equal(env.calls.filter(c => /tts\.speech/.test(c.u)).length, 2, "ikinci dinləyici keşdən alır");
    // Keş açarı başlığı, mənbəni və id-ni də əhatə edir: başqa başlıqla (saxta Referer ilə) gələn sorğu bu dinləyicinin keşinə düşmür
    await env.done();
    const forged = await w.fetch(ses("u=" + encodeURIComponent("https://sportinfo.az/1") + "&id=aaaaaaaaaaaaaaaa&t=SAXTA%20BA%C5%9ELIQ&s=Sportinfo"), { AZURE_KEY: "k" }, env.ctx);
    await forged.arrayBuffer(); await env.done();
    const said = env.calls.filter(c => /tts\.speech/.test(c.u)).map(c => c.o.body);
    assert.ok(said.length > 2 && said.slice(2).some(b => b.includes("SAXTA BAŞLIQ")), "başqa başlıq öz səsini alır");
    const reader = await w.fetch(ses("u=" + encodeURIComponent("https://sportinfo.az/1") + "&id=aaaaaaaaaaaaaaaa&t=Klub%20prezidenti&s=Sportinfo"), { AZURE_KEY: "k" }, env.ctx);
    assert.equal(reader.status, 200); await reader.arrayBuffer(); await env.done();
    assert.equal(env.calls.filter(c => /tts\.speech/.test(c.u)).length, said.length, "əsl başlıqlı sorğu yenə öz keşindən (saxta səs ona verilmir)");
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

// Sahib, 2026-11-12: «Bütün mənbələr tam və düzgün oxunsun!» — rus, ingilis və türk xəbərlərinin də tam mətni (cihazın o dildəki səsi ilə).
const RU = "Сегодня в городе открыли новый мост через реку. Движение по нему начнётся уже в понедельник, сообщили в мэрии. ";
const EN = "The city opened a new bridge across the river today. Traffic will start on Monday, the mayor's office said in a statement. ";
const TR = "Şehirde bugün nehir üzerindeki yeni köprü açıldı. Belediyeden yapılan açıklamaya göre trafik pazartesi günü başlayacak. ";

test("ses-worker: Russian, English and Turkish stories keep their full text when the language is given; junk of that language is dropped", async () => {
  const { extract } = await load();
  const page = (p, junk) => `<div class="story"><p>${p.repeat(2)}</p><p>${p}</p><p>${junk}</p></div>`;
  assert.equal(extract(page(RU, "Подписывайтесь на наш Telegram-канал."), "az"), "", "dil verilməyəndə əvvəlki qayda: Azərbaycan hərfi olmayan abzas oxunmur");
  const ru = extract(page(RU, "Подписывайтесь на наш Telegram-канал."), "ru");
  assert.ok(ru.startsWith("Сегодня в городе") && ru.endsWith("сообщили в мэрии.") && !ru.includes("Подписывайтесь"), ru);
  const en = extract(page(EN, "Subscribe to our newsletter for more stories."), "en");
  assert.ok(en.startsWith("The city opened") && !/Subscribe/.test(en), en);
  const tr = extract(page(TR, "Haberin devamı için tıklayın."), "tr");
  assert.ok(tr.startsWith("Şehirde bugün") && !/tıklayın/.test(tr), tr);
  assert.equal(extract(`<div class="paywall"><p>${EN.repeat(3)}</p></div>`, "en"), "", "ödənişli blok oxunmur");
  assert.equal(extract(`<script type="application/ld+json">{"@type":"NewsArticle","isAccessibleForFree":false}</script><div><p>${EN.repeat(3)}</p></div>`, "en"), "", "ödənişli xəbər oxunmur");
});

test("ses-worker: layout wrappers do not block the whole page, real side blocks still do", async () => {
  const { extract, skipClass } = await load();
  for (const c of ["t-content__with-sidebar", "news_in_page with_sidebar_block", "b-header--white b-footer--black--white", "p-default-layout--window-view-x", "a-article-grid a-article-grid--author-right"])
    assert.equal(skipClass("div", c), false, c);
  assert.equal(skipClass("body", "single tag-news sidebar"), false, "body sinfinə görə atılmır");
  for (const c of ["sidebar", "right-sidebar", "post-tags", "news-date", "author-box", "related-news", "social-share", "comments-area", "views"])
    assert.equal(skipClass("div", c), true, c);
  const t = extract(`<html class="b-footer--black--white"><body class="u-header-with-tag-list"><div class="t-content__with-sidebar"><div class="t-content__body"><p>${EN.repeat(2)}</p><p>${EN}</p></div><div class="sidebar"><p>${EN.replaceAll("bridge", "tunnel").repeat(4)}</p></div></div></body></html>`, "en");
  assert.ok(t.includes("bridge") && !t.includes("tunnel"), t);
});

test("ses-worker: a windows-1251 page is decoded before the text is searched (Sport.ru, Interfax)", async () => {
  const { decode, extract } = await load();
  const enc = s => Uint8Array.from([...s].map(ch => { const c = ch.charCodeAt(0); return c < 0x80 ? c : c >= 0x410 && c <= 0x44f ? c - 0x350 : ch === "ё" ? 0xb8 : ch === "Ё" ? 0xa8 : ch === "«" ? 0xab : ch === "»" ? 0xbb : ch === "—" ? 0x97 : 0x3f; }));
  const html = `<html><head><meta charset="windows-1251"></head><body><div><p>${RU.repeat(2)}</p><p>«Ёлка» — ${RU}</p></div></body></html>`;
  const viaMeta = decode(enc(html).buffer), viaHeader = decode(enc(html.replace('<meta charset="windows-1251">', "")).buffer, "text/html; charset=windows-1251");
  assert.ok(viaMeta.includes("Сегодня в городе") && viaMeta.includes("«Ёлка» —"), "kodlaşdırma <meta>-dan");
  assert.ok(viaHeader.includes("Сегодня в городе"), "kodlaşdırma başlıqdan");
  assert.ok(extract(viaMeta, "ru").startsWith("Сегодня в городе"));
  assert.equal(decode(new TextEncoder().encode("Bakıda yağış yağır — şəhər").buffer, "text/html; charset=utf-8"), "Bakıda yağış yağır — şəhər");
});

test("ses-worker /?u=&l=: the language reaches the extractor and each language is cached on its own", async () => {
  const { default: w } = await load();
  const html = `<div class="story"><p>${RU.repeat(2)}</p><p>${RU}</p></div>`;
  const env = cfEnv([[/lenta\.example/, () => new Response(html, { headers: { "content-type": "text/html; charset=utf-8" } })]]);
  const ask = l => w.fetch(new Request("https://dinle.example/?u=" + encodeURIComponent("https://lenta.example/1") + (l ? "&l=" + l : ""), { headers: { Referer: "https://8ulduz.az/" } }), {}, env.ctx);
  try {
    assert.equal((await (await ask("")).json()).text, "", "dil yoxdursa Azərbaycan qaydası");
    assert.ok((await (await ask("ru")).json()).text.startsWith("Сегодня в городе"));
    assert.equal((await (await ask("xx")).json()).text, "", "tanınmayan dil Azərbaycan qaydası ilə");
    await env.done();
    const n = env.calls.length;
    assert.ok((await (await ask("ru")).json()).text.startsWith("Сегодня"));
    assert.equal(env.calls.length, n, "ikinci sorğu keşdən");
  } finally { env.restore(); }
});

test("ses-worker /ses: a story whose prepared voice has no body text (index «q») is read in full from the source first; any failure falls back to the prepared voice", async () => {
  const { default: w } = await load();
  const id = "bbbbbbbbbbbbbbbb", mk = (extra = []) => cfEnv([[/main\/index\.json/, () => new Response(JSON.stringify({ ids: [id], q: [id] }))],
    [/main\/bbbbbbbbbbbbbbbb\.mp3/, () => new Response(new Uint8Array(5000), { status: 200 })], ...extra]);
  const call = (env, key = "k") => w.fetch(ses("u=" + encodeURIComponent("https://report.example/" + Math.random()) + "&id=" + id + "&t=Yeni%20k%C3%B6rp%C3%BC&s=Report"), key ? { AZURE_KEY: key } : {}, env.ctx);
  let env = mk([[/report\.example/, () => new Response(page, { headers: { "content-type": "text/html" } })], [/tts\.speech\.microsoft\.com/, () => new Response(new Uint8Array(9000), { status: 200 })]]);
  try {
    const r = await call(env);
    assert.equal((await r.arrayBuffer()).byteLength, 9000, "tam mətn Babək səsi ilə");
    const az = env.calls.filter(c => /tts\.speech/.test(c.u));
    assert.equal(az.length, 1); assert.ok(az[0].o.body.includes("Yeni körpü. Report xəbər verir.") && az[0].o.body.includes("Napoli klubunun"));
  } finally { env.restore(); }
  env = mk([[/report\.example/, () => new Response("yox", { status: 403 })]]);
  try { assert.equal((await (await call(env)).arrayBuffer()).byteLength, 5000, "mənbə rədd edir → hazır səs"); assert.ok(!env.calls.some(c => /tts\.speech/.test(c.u))); } finally { env.restore(); }
  env = mk([[/report\.example/, () => new Response(page, { headers: { "content-type": "text/html" } })], [/tts\.speech/, () => new Response("quota", { status: 429 })]]);
  try { assert.equal((await (await call(env)).arrayBuffer()).byteLength, 5000, "Azure limiti dolub → hazır səs"); } finally { env.restore(); }
  env = mk([[/report\.example/, () => new Response(page, { headers: { "content-type": "text/html" } })]]);
  try { assert.equal((await (await call(env, "")).arrayBuffer()).byteLength, 5000, "Azure açarı yoxdursa siyahı soruşulmur"); assert.ok(!env.calls.some(c => /index\.json/.test(c.u))); } finally { env.restore(); }
});

test("ses-worker /ses: when the source text cannot be fetched the title-only audio is not cached (the prepared full voice must be served a minute later)", async () => {
  const { default: w } = await load();
  const env = cfEnv([[/westeurope\.tts\.speech\.microsoft\.com/, () => new Response(new Uint8Array(8000), { status: 200, headers: { "content-type": "audio/mpeg" } })]]);
  try {
    const q = "u=" + encodeURIComponent("https://report.az/qapali") + "&id=bbbbbbbbbbbbbbbb&t=H%C9%99qiqi%20ba%C5%9Fl%C4%B1q&s=Report";
    const first = await w.fetch(ses(q), { AZURE_KEY: "k" }, env.ctx);
    assert.equal(first.status, 200); assert.equal((await first.arrayBuffer()).byteLength, 8000, "yalnız başlıq oxunur");
    await env.done();
    const before = env.calls.length;
    const second = await w.fetch(ses(q), { AZURE_KEY: "k" }, env.ctx);
    await second.arrayBuffer(); await env.done();
    assert.ok(env.calls.length > before, "ikinci dinləyici keşdən başlıq-səsi almır: hazır səs yenidən soruşulur");
  } finally { env.restore(); }
});

test("ses-worker: paragraphs without closing tags are all read (same rule as reader_content.py)", async () => {
  const { extract } = await load();
  const names = ["Birinci", "İkinci", "Üçüncü", "Dördüncü"], body = n => `${n} abzas: ${para.repeat(3)}`;
  for (const html of [`<div class="news-text">${names.map(n => "<p>" + body(n)).join("")}</div>`,
    `<div class="story"><ul>${names.map(n => "<li>" + body(n)).join("")}</ul></div>`,
    `<div class="news-text">${names.map(n => "<p><b>Qeyd.</b> " + body(n)).join("")}</div>`]) {
    const t = extract(html);
    for (const n of names) assert.equal(t.split(n + " abzas").length - 1, 1, n + ": " + html.slice(0, 40));
    assert.ok(t.indexOf("Birinci abzas") < t.indexOf("Dördüncü abzas"));
  }
});
