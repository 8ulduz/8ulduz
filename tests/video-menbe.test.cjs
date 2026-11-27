// Mənbə saytının öz videosu (video-menbe.cjs) və dünya videoları tərcümə ilə (video-dunya.cjs) — sahib, 2026-11-26:
// «Bir çox xəbər saytı hesabı eyni görüntünü verir… biz də verək. Qaydalarımızda bunu əngəlləyən nəsə varsa sil»,
// «dünya saytlarından lazım olan tipli videoları götürüb tərcümə ilə azərbaycan dilində verilsin».
// Şəbəkə və ffmpeg burada işləmir: səhifələr, siyahılar, Gemini və fayllar saxtadır.
"use strict";
const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("fs"), os = require("os"), path = require("path");

const M = require("../.github/scripts/video-menbe.cjs");
const VD = require("../.github/scripts/video-dunya.cjs");
const SV = require("../.github/scripts/sosial-video.cjs");
const V = require("../.github/scripts/video-xeber.cjs");
const VS = require("../.github/scripts/video-ssenari.cjs");
const root = path.resolve(__dirname, "..");
const read = f => fs.readFileSync(path.join(root, f), "utf8");

const NOW = Date.parse("2026-11-26T10:00:00Z");
const tmp = () => fs.mkdtempSync(path.join(os.tmpdir(), "menbe-"));
// MP4 imzalı saxta fayl (4-cü baytdan «ftyp»), n bayt.
const mp4 = (n = 200e3) => { const b = Buffer.alloc(n); b.write("ftypisom", 4, "latin1"); return b; };
const res = { text: s => ({ ok: true, status: 200, text: async () => s }), file: (b, type = "video/mp4") => ({ ok: true, status: 200, headers: { get: k => (k === "content-length" ? String(b.length) : type) }, arrayBuffer: async () => b }) };
const net = map => async url => (Object.prototype.hasOwnProperty.call(map, url) ? (typeof map[url] === "string" ? res.text(map[url]) : map[url]) : { ok: false, status: 404, text: async () => "" });

test("mənbə videosu: links — own files and player frames; platforms, X, ads and site furniture are never taken", () => {
  const html = `<iframe src="//player.bizim.media/?v=59956"></iframe><iframe src="https://www.youtube.com/embed/abcDEF12345"></iframe>
    <iframe src="https://lent.az/banner/web/x/index.html"></iframe><iframe src="https://ad.adriver.ru/cgi-bin/erle.cgi?"></iframe>
    <video><source src="//cdn.sayt.az/video/2026/11/25/59956.mov" type="video/mp4"></video>
    <source src="//radio.sayt.az/8002/stream" type="audio/mpeg">
    <script>var v={"file":"https:\\/\\/cdn.sayt.az\\/v\\/1_360p.mp4","hd":"https:\\/\\/cdn.sayt.az\\/v\\/1_720p.mp4\\/"};</script>
    <video src="https://video.twimg.com/amplify_video/1/vid/a.mp4"></video><a href="https://sayt.az/manifest/site.webm">x</a>
    <a href="https://sayt.az/reklam/promo.mp4">r</a><blockquote data-instgrm-permalink="https://www.instagram.com/reel/Dg/"></blockquote>`;
  const l = M.linkler(html, "https://sayt.az/az/idman/1/");
  assert.deepEqual(l.fayl, ["https://cdn.sayt.az/v/1_720p.mp4/", "https://cdn.sayt.az/v/1_360p.mp4", "https://cdn.sayt.az/video/2026/11/25/59956.mov"], "keyfiyyətlisi əvvəl; səs axını, X, reklam və bəzək yoxdur");
  assert.deepEqual(l.cercive, ["https://player.bizim.media/?v=59956"], "yalnız pleyer çərçivəsi (YouTube, banner, reklam yox)");
  assert.deepEqual(M.linkler("", "https://sayt.az/"), { fayl: [], cercive: [] });
  assert.ok(M.videodur(mp4()) && !M.videodur(Buffer.from("<html><body>404</body></html>")) && M.videodur(Buffer.from([0x1A, 0x45, 0xDF, 0xA3, 0, 0, 0, 0, 0, 0, 0, 0])));
  // X videoları yalnız yerləşdirilir (docs/youtube.md): mənbə modulu onları və saytın öz səhifələrini oxumur.
  const src = read(".github/scripts/video-menbe.cjs");
  assert.ok(/twimg/.test(src) && /8ULDUZ/.test(src) && !/reels\.json|oz_x\.json/.test(src));
});

test("mənbə videosu: the story's own footage from the source's player, credited; site-wide files, non-video replies and broadcast footage are refused", async () => {
  const a = { id: "a1".padEnd(16, "0"), title: "Ceyhun Bayramov litvalı həmkarı ilə “Sabah” – “Barselona” matçını izlədi - Video", source: "Bizim.Media",
    sourceUrl: "https://bizim.media/az/idman/649732/x/", alts: [{ source: "Oxu.az", sourceUrl: "https://oxu.az/idman/x", title: "… izləyiblər - Video" }] };
  const page = `<iframe src="//player.bizim.media/?v=59956"></iframe><video autoplay muted loop><source src="https://bizim.media/img/fon.mp4"></video>`;
  const file = mp4(), dir = tmp(), logs = [];
  const f = net({ "https://player.bizim.media/?v=59956": `<video><source src="//cdn.bizim.media/video/2026/11/25/59956.mov" type="video/mp4"/></video>`,
    "https://bizim.media/": `<video autoplay muted loop><source src="https://bizim.media/img/fon.mp4"></video>`,
    "https://bizim.media/img/fon.mp4": res.file(mp4()), "https://cdn.bizim.media/video/2026/11/25/59956.mov": res.file(file, "video/quicktime") });
  // Səhifənin öz faylı (fon.mp4) baş səhifədə də var: bəzəkdir, atılır — xəbərin videosu pleyer çərçivəsindən gəlir.
  const r = await M.menbeVideo(a, page, { env: {}, fetch: f, log: s => logs.push(s), dir });
  assert.deepEqual({ ...r, bytes: 0 }, { file: "klip-menbe.mp4", url: "https://cdn.bizim.media/video/2026/11/25/59956.mov", sehife: a.sourceUrl, kredit: "Bizim.Media", bytes: 0 });
  assert.equal(fs.readFileSync(path.join(dir, M.FAYL)).length, file.length);
  // Yalnız bəzək faylı olan səhifə: götürülmür (baş səhifədə də var).
  const d2 = tmp();
  assert.equal(await M.menbeVideo({ ...a, alts: [] }, `<video autoplay muted loop><source src="https://bizim.media/img/fon.mp4"></video>`, { env: {}, fetch: f, log: () => {}, dir: d2 }), null);
  assert.ok(!fs.existsSync(path.join(d2, M.FAYL)));
  // Video əvəzinə HTML (xəta səhifəsi) və ya kiçik fayl: saxlanmır.
  const bad = net({ "https://s.az/": "", "https://s.az/v/1.mp4": res.file(Buffer.from("<html>404</html>".repeat(20000))), "https://s.az/v/2.mp4": res.file(mp4(1000)) });
  const l3 = [];
  assert.equal(await M.menbeVideo({ ...a, source: "S", sourceUrl: "https://s.az/x", alts: [] }, `<video src="https://s.az/v/1.mp4"></video><video src="https://s.az/v/2.mp4"></video>`, { env: {}, fetch: bad, log: s => l3.push(s), dir: d2 }), null);
  assert.ok(l3.some(s => /video faylı deyil/.test(s)) && l3.some(s => /fayl kiçikdir/.test(s)));
  // Liqaların oyun kadrı (qol, icmal) götürülür (sahib 2026-11-26: «liqaların oyun kadrını niyə götürmürük?» → «3 et»).
  // Film, serial, klip, treyler kadrı götürülmür; MENBE_YAYIM=1 ilə açılır. MENBE_VIDEO=0 hər şeyi söndürür. Öz səhifələrimiz (X videoları) oxunmur.
  const qol = { ...a, title: "“Sabah” fərqi azaltdı: qol və oyunun icmalı - Video" };
  assert.equal((await M.menbeVideo(qol, page, { env: {}, fetch: f, log: () => {}, dir: tmp() }))?.kredit, "Bizim.Media", "oyun kadrı");
  const serial = { ...a, title: "Yeni serialın ilk kadrları yayıldı - Video" };
  assert.equal(await M.menbeVideo(serial, page, { env: {}, fetch: f, log: s => logs.push(s), dir: tmp() }), null);
  assert.ok(logs.some(s => /yayım kadrı ola bilər \(film, serial, klip\)/.test(s)));
  assert.equal((await M.menbeVideo(serial, page, { env: { MENBE_YAYIM: "1" }, fetch: f, log: () => {}, dir: tmp() }))?.kredit, "Bizim.Media");
  assert.equal(await M.menbeVideo(a, page, { env: { MENBE_VIDEO: "0" }, fetch: f, log: () => {}, dir: tmp() }), null);
  assert.equal(await M.menbeVideo({ ...a, source: "8ULDUZ", sourceUrl: "https://8ulduz.az/x/1.html", alts: [] }, `<video src="https://8ulduz.az/v/1.mp4"></video>`, { env: {}, fetch: f, log: () => {}, dir: tmp() }), null);
});

test("mənbə videosu: only the story's own part of the page and the site's own files — another story's video further down (Publika.az 2026-11-26: a court verdict got a 2022 forest-fire video) and another site's file are refused", async () => {
  // Publika.az quruluşu: loqo <h1>-dir, xəbərin başlığı <h1 itemprop="headline">, altında köhnə xəbərlər öz <h1>-i və videosu ilə
  // (TRT faylı Publika-nın hər xəbər səhifəsinin aşağısındadır).
  const head = `<html><head><title>Namizəd Səfərova hökm oxundu | Publika.az</title><meta property="og:title" content="Namizəd Səfərova hökm oxundu" /></head><body>
    <h1 class="mvp-logo-title">Publika.az</h1><article><h1 class="mvp-post-title entry-title" itemprop="headline">Namizəd Səfərova hökm oxundu</h1>
    <div id="mvp-content-main"><p>Bakı Ağır Cinayətlər Məhkəməsində hökm oxunub.</p>`;
  const sonra = `</div><div class="mvp-post-add-main"><h1 class="mvp-post-title left">Marmarisdə vəziyyət gərginləşdi - VİDEO</h1>
    <iframe src="https://www.trthaber.com/dosyalar/videolar/fa539b.mp4"></iframe><video src="https://publika.az/uploads/2022/marmaris.mp4"></video>
    <iframe src="https://www.dailymotion.com/embed/video/x8bwgw9"></iframe></div></article></body></html>`;
  const page = head + sonra;
  const m = M.meqale(page);
  assert.ok(m.includes("hökm oxunub") && !/trthaber|marmaris|dailymotion/.test(m), "sonrakı xəbər kəsilir");
  assert.deepEqual(M.linkler(m, "https://publika.az/news/x/1.html"), { fayl: [], cercive: [] });
  // og:title yoxdursa <title>; loqonun <h1>-i («Publika.az», 2 söz) başlıq sayılmır. Başlıqdan əvvəlki əsas video xəbərindir.
  const noOg = page.replace(/<meta property="og:title"[^>]*>/, "").replace("<article>", `<article><video src="https://publika.az/v/esas.mp4"></video>`);
  assert.ok(M.meqale(noOg).includes("esas.mp4") && !M.meqale(noOg).includes("marmaris"));
  assert.equal(M.meqale(`<h1>Başqa başlıq burada</h1><video src="https://s.az/1.mp4"></video>`), `<h1>Başqa başlıq burada</h1><video src="https://s.az/1.mp4"></video>`, "başlıq tapılmasa səhifə bütöv");
  const a = { id: "s1".padEnd(16, "0"), title: "Namizəd Səfərova hökm oxundu", source: "Publika.az", sourceUrl: "https://publika.az/news/nida_xeber/650276.html", alts: [] };
  const files = { "https://publika.az/": "<html></html>", "https://www.trthaber.com/dosyalar/videolar/fa539b.mp4": res.file(mp4()), "https://publika.az/uploads/2022/marmaris.mp4": res.file(mp4()),
    "https://www.trthaber.com/v/x.mp4": res.file(mp4()), "https://cdn.publika.az/v/oz.mp4": res.file(mp4()), "https://bax.tv/embed/7": `<video src="https://cdn.baxtv-video.net/7.mp4"></video>`,
    "https://cdn.baxtv-video.net/7.mp4": res.file(mp4()) };
  const logs = [];
  assert.equal(await M.menbeVideo(a, page, { env: {}, fetch: net(files), log: s => logs.push(s), dir: tmp() }), null, "Publika: video yoxdur — bank klipləri");
  // Xəbərin öz hissəsində başqa saytın faylı: götürülmür (görüntü onlarındır, «Görüntü: Publika.az» yanlış olardı), jurnala yazılır.
  const yad = head + `<iframe src="https://www.trthaber.com/v/x.mp4"></iframe>` + sonra;
  assert.equal(await M.menbeVideo(a, yad, { env: {}, fetch: net(files), log: s => logs.push(s), dir: tmp() }), null);
  assert.ok(logs.some(s => /Publika\.az — başqa saytın faylı və pleyeri götürülmür \(trthaber\.com\)/.test(s)));
  // Saytın öz faylı (alt domen) və platforma pleyeri (bax.tv; faylı onun öz CDN-indədir) götürülür.
  const oz = await M.menbeVideo(a, head + `<video src="https://cdn.publika.az/v/oz.mp4"></video>` + sonra, { env: {}, fetch: net(files), log: () => {}, dir: tmp() });
  assert.deepEqual([oz.url, oz.kredit], ["https://cdn.publika.az/v/oz.mp4", "Publika.az"]);
  const bax = await M.menbeVideo(a, head + `<iframe src="https://bax.tv/embed/7"></iframe>` + sonra, { env: {}, fetch: net(files), log: () => {}, dir: tmp() });
  assert.equal(bax.url, "https://cdn.baxtv-video.net/7.mp4");
  assert.deepEqual(["https://cdn.bizim.media/x", "https://www.trthaber.com/x", "https://video.report.com.az/x", "https://player.bax.tv/e/1", "yox"].map(M.sayt),
    ["bizim.media", "trthaber.com", "report.com.az", "bax.tv", ""]);
});

test("mənbə videosu: selection keeps bank clips as a fallback, goes ahead on the source video alone, and video stories rank higher", async () => {
  const src = n => Array(n - 1).fill({ source: "X" });
  const art = (id, o = {}) => ({ id: id.padEnd(16, "0"), title: `Xəbər ${id}`, summary: "Qısa xülasə.", category: "gundem", lang: "az", source: "APA", sourceUrl: `https://apa.az/${id}`,
    publishedAt: new Date(NOW - 10 * 60e3).toISOString(), alts: src(4), ...o });
  assert.equal(SV.cekisi(art("a1", { video: true })), 1.3, "videolu xəbər");
  assert.equal(SV.cekisi(art("a2", { alts: [{ source: "Y", title: "Hadisə - Video" }] })), 1.3, "digər mənbədə video");
  assert.equal(SV.cekisi(art("a3")), 1);
  const FILL = "Layihə sakinlərin rahatlığı üçün nəzərdə tutulub və uzun müddət xidmət göstərəcək. Tikinti işləri müasir standartlara uyğun aparılıb. Ərazidə abadlıq işləri də görülüb və yaşıllıq zolaqları salınıb. Yeni obyekt ətraf məhəllələrin sakinləri üçün də əlçatan olacaq. Rəsmilər bildirib ki, oxşar layihələr digər bölgələrdə də davam etdiriləcək. Sakinlər yeni obyektin açılışını müsbət qarşılayıblar.";
  const a = art("a1", { title: "Bakıda yeni metro stansiyası açılıb - Video", video: true, alts: src(8) });
  const body = "Bakıda yeni metro stansiyası sərnişinlərin istifadəsinə verilib. Stansiyanın tikintisində müasir texnologiyalardan istifadə olunub, platformalar geniş salınıb. Stansiya Xətai rayonundadır.";
  const f = async (url, o = {}) => (/generativelanguage/.test(url)
    ? (/models\?pageSize/.test(url) ? { ok: true, json: async () => ({ models: [] }) } : { ok: true, status: 200, json: async () => ({ candidates: [{ content: { parts: [{ text: JSON.stringify({ uygun: true, text: `${FILL} Stansiya Xətai rayonundadır.`, axtar: [] }) }] } }] }) })
    : url === a.sourceUrl ? res.text(`<html><head><meta property="og:description" content="${body}"></head><body><p>${body}</p></body></html>`) : { ok: false, text: async () => "" });
  const dir = tmp(), old = process.env.GITHUB_OUTPUT;
  process.env.GITHUB_OUTPUT = path.join(dir, "out.txt");
  try {
    const mv = { file: "klip-menbe.mp4", url: "https://cdn.apa.az/v/1.mp4", sehife: a.sourceUrl, kredit: "APA", bytes: 1 };
    // Bank açarı yoxdur: video mənbənin öz görüntüsü ilə gedir, xeber.json-da menbeVideo var.
    const st = SV.readState("/yoxdur", NOW);
    const x = await SV.sec({ articles: [a], env: { VIDEO_ACAR: "1", GEMINI_API_KEY: "g", DUNYA_VIDEO: "0", X_VIDEO: "0", MARAQLI_VIDEO: "0" }, now: NOW, state: st, fetch: f, cats: [{ slug: "gundem", label: "Gündəm" }], dir, log: () => {}, menbe: async () => mv });
    assert.equal(x.id, a.id);
    assert.deepEqual(JSON.parse(fs.readFileSync(path.join(dir, "xeber.json"), "utf8")).menbeVideo, mv);
    // Mənbə videosu tapılmayanda əvvəlki kimi (sahə yoxdur).
    const st2 = SV.readState("/yoxdur", NOW);
    await SV.sec({ articles: [a], env: { VIDEO_ACAR: "1", GEMINI_API_KEY: "g", DUNYA_VIDEO: "0", X_VIDEO: "0", MARAQLI_VIDEO: "0" }, now: NOW, state: st2, fetch: f, cats: [], dir, log: () => {}, menbe: async () => null });
    assert.equal(JSON.parse(fs.readFileSync(path.join(dir, "xeber.json"), "utf8")).menbeVideo, undefined);
  } finally { if (old === undefined) delete process.env.GITHUB_OUTPUT; else process.env.GITHUB_OUTPUT = old; }
});

test("mənbə videosu: the post text credits the footage the montage really used (video.json), bank credit otherwise", async () => {
  const dir = tmp();
  const x = { id: "a1".padEnd(16, "0"), title: "Bakıda yeni park açılıb", text: "Park sakinlərin istifadəsinə verilib.", link: "https://www.8ulduz.az/a100000000000000?h=26112610", category: "gundem",
    publishedAt: new Date(NOW).toISOString(), klipler: ["klip-1.mp4"], goruntu: [{ p: "Pixabay", id: 1 }], goruntuMenbe: "Pixabay", menbeVideo: { file: "klip-menbe.mp4", kredit: "Bizim.Media" } };
  // Paylaşma: mətnə gedən giriş montajın nəticəsi (video.json menbeVideo, goruntu) ilə birləşdirilir.
  const sv = read(".github/scripts/sosial-video.cjs");
  assert.ok(/const gorunen = meta\.menbeVideo \? \{ goruntu: \[\{ p: "Mənbə" \}\], goruntuMenbe: meta\.goruntu \} : \{\};/.test(sv) && /net\.post\(\{ \.\.\.x, \.\.\.gorunen,/.test(sv));
  assert.match(SV.fbText({ ...x, goruntu: [{ p: "Mənbə" }], goruntuMenbe: "Bizim.Media" }), /Görüntü: Bizim\.Media/);
  assert.match(SV.igText({ ...x, goruntu: [{ p: "Mənbə" }], goruntuMenbe: "Bizim.Media" }), /Görüntü: Bizim\.Media/);
  assert.match(SV.igText(x), /Görüntü: Pixabay/, "mənbə videosu montajda işlənməyibsə bank krediti");
  // Montaj: mənbə videosu oxunursa yeganə klipdir və video.json-da nişanlanır (koda baxış — ffmpeg burada işləmir).
  const vx = read(".github/scripts/video-xeber.cjs");
  assert.ok(/if \(mv\) \{ clips = \[mv\];/.test(vx) && /menbeVideo: true/.test(vx) && typeof V.menbeKlip === "function");
  assert.equal(V.menbeKlip(path.join(dir, "yoxdur.mp4")), null, "oxunmayan fayl: bank klipləri ilə davam");
  assert.equal(V.storyFields({ id: "d1", title: "T", kind: "dunya", url: "https://8ulduz.az/bolme/dunya/" }).url, "https://8ulduz.az/bolme/dunya/");
});

// --- Dünya videoları ------------------------------------------------------------------------------------------------------------
const M1 = { ad: "Sınaq TV", dil: "en", lent: "https://tv.example/rss", nov: "mrss", istiqamet: [3, 15], sertler: "sınaq" };
const RSS = `<rss><channel>
<item><title><![CDATA[Dog rescued from frozen lake &amp; reunited]]></title><link>https://tv.example/v/1</link><pubDate>Thu, 26 Nov 2026 08:00:00 GMT</pubDate>
<description>&lt;p&gt;Firefighters pulled a dog from a frozen lake in Oslo after 2 hours on the ice. The dog was returned to its owner, a 70-year-old woman who had searched all night. Crews used a ladder and ropes to reach the animal, officials said.&lt;/p&gt;</description>
<media:content url="https://cdn.tv.example/v/1.mp4" type="video/mp4"/></item>
<item><title>President meets PM at summit</title><link>https://tv.example/v/2</link><pubDate>Thu, 26 Nov 2026 07:00:00 GMT</pubDate><description>Leaders discussed trade.</description><enclosure url="https://cdn.tv.example/v/2.mp4" type="video/mp4"/></item>
<item><title>Old item</title><link>https://tv.example/v/3</link><pubDate>Thu, 12 Nov 2026 07:00:00 GMT</pubDate><description>x</description><enclosure url="https://cdn.tv.example/v/3.mp4" type="video/mp4"/></item>
</channel></rss>`;

test("dünya videosu: source list schema; RSS/MRSS, Atom, video sitemap, HTML listing and JSON are read into the same items", () => {
  assert.equal(VD.kecerli(M1), "");
  assert.match(VD.kecerli({ ...M1, lent: "http://tv.example/rss" }), /https/);
  assert.match(VD.kecerli({ ...M1, nov: "html" }), /sec/);
  assert.match(VD.kecerli({ ...M1, nov: "json" }), /JSON/);
  assert.match(VD.kecerli({ ...M1, sertler: "" }), /şərt/);
  assert.match(VD.kecerli({ ...M1, istiqamet: [7] }), /istiqamət/);
  // Sahibin 15 istiqaməti (2026-11-26): yerli istiqamətlər (1 ordu, 7 sakin şikayəti, 9 yerli idman) dünya videosunda yoxdur.
  for (const n of [0, 1, 9, 16]) assert.match(VD.kecerli({ ...M1, istiqamet: [n] }), /istiqamət/, String(n));
  // Repodakı siyahı: hər mənbə sxemdən keçir, adlar təkrarsızdır, «say kifayətdən artıq» (sahib).
  const all = JSON.parse(read(".github/video-dunya.json")).menbeler;
  for (const m of all) assert.equal(VD.kecerli(m), "", `${m.ad}: sxem`);
  assert.equal(new Set(all.map(m => m.ad)).size, all.length, "mənbə adları təkrarsızdır");
  const items = VD.oxuSiyahi(M1, RSS, NOW);
  assert.deepEqual(items.map(x => [x.title, x.link, x.fayl]), [["Dog rescued from frozen lake & reunited", "https://tv.example/v/1", "https://cdn.tv.example/v/1.mp4"],
    ["President meets PM at summit", "https://tv.example/v/2", "https://cdn.tv.example/v/2.mp4"]], "96 saatdan köhnə video düşmür, təzəsi əvvəl");
  assert.match(items[0].desc, /^Firefighters pulled a dog/);
  assert.match(items[0].id, /^[0-9a-f]{16}$/);
  const atom = `<feed><entry><title>Rare snow in the desert</title><link rel="alternate" href="https://a.example/x/1"/><updated>2026-11-26T06:00:00Z</updated><summary>Snow fell.</summary></entry></feed>`;
  assert.deepEqual(VD.oxuSiyahi({ ...M1, nov: "atom" }, atom, NOW).map(x => [x.title, x.link, x.fayl]), [["Rare snow in the desert", "https://a.example/x/1", ""]]);
  const sm = `<urlset><url><loc>https://s.example/video/9</loc><video:video><video:title>Whale freed from net</video:title><video:description>Divers cut the net.</video:description>
    <video:content_loc>https://cdn.s.example/9.mp4</video:content_loc><video:publication_date>2026-11-25T10:00:00+00:00</video:publication_date></video:video></url>
    <url><loc>https://s.example/news/10</loc><lastmod>2026-11-26</lastmod></url></urlset>`;
  assert.deepEqual(VD.oxuSiyahi({ ...M1, nov: "sitemap", sec: "/video/" }, sm, NOW).map(x => [x.title, x.link, x.fayl]), [["Whale freed from net", "https://s.example/video/9", "https://cdn.s.example/9.mp4"]]);
  const html = `<a href="/video/ilginc/1-kedi">a</a><a href="/haber/2">b</a><a href="https://h.example/video/ilginc/1-kedi">təkrar</a><a href="/video/ilginc/3-kopek#x">c</a>`;
  assert.deepEqual(VD.oxuSiyahi({ ...M1, nov: "html", lent: "https://h.example/video/", sec: "/video/ilginc/\\d+-" }, html, NOW).map(x => x.link), ["https://h.example/video/ilginc/1-kedi", "https://h.example/video/ilginc/3-kopek"]);
  const js = JSON.stringify({ collection: { items: [{ href: "https://n.example/asset/1", data: [{ title: "Rocket launch", description: "Liftoff.", date_created: "2026-11-25T00:00:00Z" }], links: [{ href: "https://n.example/1~orig.mp4" }] }] } });
  const jm = { ...M1, nov: "json", json: { siyahi: "collection.items", kecid: "href", basliq: "data.0.title", tesvir: "data.0.description", tarix: "data.0.date_created", fayl: "links.0.href" } };
  assert.equal(VD.kecerli(jm), "");
  assert.deepEqual(VD.oxuSiyahi(jm, js, NOW).map(x => [x.title, x.fayl]), [["Rocket launch", "https://n.example/1~orig.mp4"]]);
  // Növbə: ən çoxdan oxunmayan mənbə əvvəl.
  const l = [{ ...M1, ad: "A" }, { ...M1, ad: "B" }, { ...M1, ad: "C" }];
  assert.deepEqual(VD.novbe(l, { dm: { A: 500, B: 100 } }).map(m => m.ad), ["C", "B", "A"]);
});

test("dünya videosu: one Gemini call picks by direction and translates; the site's rule checks the source text and the translation; numbers must be in the source", async () => {
  const AZ = "Osloda yanğınsöndürənlər donmuş göldə qalan iti xilas ediblər. Heyvan buzun üstündə 2 saat qalıb və sahilə özü çıxa bilməyib. Xilasedicilər itə nərdivan və kəndirlərin köməyi ilə çatıblar. İt bütün gecə onu axtaran 70 yaşlı sahibinə qaytarılıb. Qadın heyvanını görəndə xilasedicilərə təşəkkür edib. Rəsmilər əməliyyatın uğurla başa çatdığını və itin sağlam olduğunu bildiriblər.";
  const gem = j => async (url, o = {}) => (/models\?pageSize/.test(url) ? { ok: true, json: async () => ({ models: [] }) }
    : { ok: true, status: 200, json: async () => ({ candidates: [{ content: { parts: [{ text: typeof j === "function" ? j(JSON.parse(o.body).contents[0].parts[0].text) : JSON.stringify(j) }] } }] }) });
  const feeds = net({ "https://tv.example/rss": RSS });
  const state = SV.readState("/yoxdur", NOW), logs = [];
  const leadership = a => /president/i.test(`${a.title} ${a.summary}`);   // saxta qayda: «President» keçmir
  const pool = await VD.namizedler({ list: [M1], state, now: NOW, fetch: feeds, policy: leadership, log: s => logs.push(s) });
  assert.deepEqual(pool.map(c => c.a.title), ["Dog rescued from frozen lake & reunited"], "qaydadan keçməyən video namizəd olmur");
  assert.ok(logs.some(s => /saytın qaydasından keçmir — Sınaq TV: President meets PM/.test(s)) && state.dm["Sınaq TV"] > 0);
  assert.equal(pool[0].a.lang, "en");
  assert.equal(pool[0].a.category, "dunya");
  // Prompt: istiqamətlər, tərcümə dili, namizədin mətni.
  let prompt = "";
  const good = { sec: 1, istiqamet: 15, basliq: "Osloda donmuş göldən it xilas edildi.", text: AZ, etiket: ["xilasetmə", "Oslo", "#heyvanlar"] };
  const s = await VD.sec(pool, { env: { GEMINI_API_KEY: "g" }, fetch: gem(p => { prompt = p; return JSON.stringify(good); }), policy: leadership, log: () => {} });
  assert.match(prompt, /insan hekayəsi/); assert.match(prompt, /Azərbaycan ədəbi dilində/); assert.match(prompt, /\[1\] Mənbə: Sınaq TV \(en\)\nDog rescued/);
  assert.equal(s.title, "Osloda donmuş göldən it xilas edildi", "başlığın sonundakı nöqtə atılır");
  assert.equal(s.text, AZ); assert.equal(s.istiqamet, 15); assert.deepEqual(s.etiket, ["xilasetmə", "Oslo", "heyvanlar"]);
  // Mənbədə olmayan rəqəm, qaydadan keçməyən tərcümə, uyğun video yoxdur, Gemini cavab vermir.
  const opt = j => ({ env: { GEMINI_API_KEY: "g" }, fetch: gem(j), policy: leadership, log: () => {} });
  assert.match((await VD.sec(pool, opt({ ...good, text: AZ.replace("2 saat", "5 saat") }))).yox, /mənbədə olmayan rəqəm: 5/);
  assert.match((await VD.sec(pool, opt({ ...good, text: AZ.replace("Rəsmilər", "President və rəsmilər") }))).yox, /qayda/);
  assert.match((await VD.sec(pool, opt({ ...good, basliq: "It" }))).yox, /başlıq/);
  assert.equal((await VD.sec(pool, opt({ sec: 0 }))).yox, "istiqamətə uyğun video yoxdur");
  assert.equal(await VD.sec(pool, { env: {}, fetch: gem(good), policy: leadership, log: () => {} }), null, "açar yoxdur");
  // Tam yol: seçim, tərcümə, fayl → giriş. Qayda verilməsə xəta (xarici mətn yoxlanmadan videoya düşməz).
  const dir = tmp(), st = SV.readState("/yoxdur", NOW), file = path.join(dir, "menbeler.json");
  fs.writeFileSync(file, JSON.stringify({ menbeler: [M1, { ...M1, ad: "Söndürülmüş", aktiv: false }, { ...M1, ad: "Yanlış", nov: "x" }] }));
  assert.deepEqual(VD.menbeler(file).map(m => m.ad), ["Sınaq TV"]);
  await assert.rejects(VD.hazirla({ now: NOW, state: st, env: {}, fetch: feeds, dir, log: () => {}, file }), /qaydası/);
  const all = async (url, o) => (/generativelanguage/.test(url) ? gem(good)(url, o) : url === "https://cdn.tv.example/v/1.mp4" ? res.file(mp4()) : feeds(url));
  const x = await VD.hazirla({ now: NOW, state: st, env: { GEMINI_API_KEY: "g" }, fetch: all, policy: leadership, dir, log: () => {}, file });
  assert.deepEqual({ tur: x.tur, kind: x.kind, title: x.title, text: x.text, category: x.category, source: x.source, sourceUrl: x.sourceUrl, menbeVideo: x.menbeVideo, esli: x.esli },
    { tur: "dunya", kind: "dunya", title: "Osloda donmuş göldən it xilas edildi", text: AZ, category: "dunya", source: "Sınaq TV", sourceUrl: "https://tv.example/v/1",
      menbeVideo: { file: "klip-menbe.mp4", url: "https://cdn.tv.example/v/1.mp4", sehife: "https://tv.example/v/1", kredit: "Sınaq TV" }, esli: { title: "Dog rescued from frozen lake & reunited", dil: "en" } });
  assert.match(x.id, /^[0-9a-f]{16}$/);
  assert.ok(fs.existsSync(path.join(dir, M.FAYL)));
  // Fayl alınmasa video yoxdur və bu video bir də sınanmır.
  const st2 = SV.readState("/yoxdur", NOW);
  const nofile = async (url, o) => (/generativelanguage/.test(url) ? gem(good)(url, o) : feeds(url));
  assert.equal(await VD.hazirla({ now: NOW, state: st2, env: { GEMINI_API_KEY: "g" }, fetch: nofile, policy: leadership, dir: tmp(), log: () => {}, file }), null);
  assert.ok(st2.skip[x.id]);
});

test("dünya videosu: its own pace (8 a day, 90 minutes apart), before the news pick, never in the topic list; only in a language that has it", async () => {
  assert.deepEqual(VD.options({}), { on: true, perDay: 8, gapMin: 90 });
  assert.deepEqual(VD.options({ DUNYA_VIDEO: "0", DUNYA_GUNDE: "3", DUNYA_ARA_MIN: "30" }), { on: false, perDay: 3, gapMin: 30 });
  const sec = NOW / 1000, o = VD.options({});
  assert.equal(VD.due({ dv: {} }, NOW, o), "");
  assert.match(VD.due({ dv: { a: sec - 60 * 60 } }, NOW, o), /60 dəq əvvəl \(ara 90 dəq\)/);
  assert.equal(VD.due({ dv: { a: sec - 91 * 60 } }, NOW, o), "");
  assert.match(VD.due({ dv: Object.fromEntries(Array.from({ length: 8 }, (_, i) => [`v${i}`, sec - (i + 2) * 3600])) }, NOW, o), /24 saatda 8 dünya videosu/);
  assert.match(VD.due({ dv: {} }, NOW, VD.options({ DUNYA_VIDEO: "0" })), /söndürülüb/);
  const dir = tmp(), old = process.env.GITHUB_OUTPUT;
  process.env.GITHUB_OUTPUT = path.join(dir, "out.txt");
  try {
    const st = SV.readState("/yoxdur", NOW);
    const x = { id: "d1".padEnd(16, "0"), tur: "dunya", kind: "dunya", title: "Osloda donmuş göldən it xilas edildi", text: "Mətn.", category: "dunya", source: "Sınaq TV", sourceUrl: "https://tv.example/v/1",
      publishedAt: new Date(NOW).toISOString(), menbeVideo: { file: "klip-menbe.mp4", kredit: "Sınaq TV" } };
    let asked = 0;
    const got = await SV.sec({ articles: [], env: { VIDEO_ACAR: "1", X_VIDEO: "0", MARAQLI_VIDEO: "0" }, now: NOW, state: st, fetch: async () => ({ ok: false }), cats: [{ slug: "dunya", label: "Dünya" }], dir, log: () => {},
      dunya: async a => { asked++; assert.equal(typeof a.policy, "function"); return x; } });
    assert.equal(asked, 1);
    assert.equal(got.bolme, "Dünya"); assert.equal(got.link, "https://8ulduz.az/bolme/dunya/"); assert.equal(got.url, got.link);
    assert.ok(st.dv[x.id] && st.v[x.id] && st._last, "gündəlik həddə və fasiləyə sayılır");
    assert.match(fs.readFileSync(process.env.GITHUB_OUTPUT, "utf8"), /hazir=1\ntur=dunya/);
    // Növbəti pəncərə (30 dəq sonra): dünya videosunun arası (90 dəq) dolmayıb — soruşulmur.
    await SV.sec({ articles: [], env: { VIDEO_ACAR: "1", X_VIDEO: "0", MARAQLI_VIDEO: "0" }, now: NOW + 31 * 60e3, state: st, fetch: async () => ({ ok: false }), cats: [], dir, log: () => {}, dunya: async () => { asked++; return null; } });
    assert.equal(asked, 1);
    // Siyahı dv və dm-i saxlayır; paylaşandan sonra mövzu siyahısına düşmür.
    const file = path.join(dir, "state.json");
    fs.writeFileSync(file, JSON.stringify({ ...st, dm: { "Sınaq TV": sec } }));
    const back = SV.readState(file, NOW);
    assert.ok(back.dv[x.id] && back.dm["Sınaq TV"]);
  } finally { if (old === undefined) delete process.env.GITHUB_OUTPUT; else process.env.GITHUB_OUTPUT = old; }
  // İş axını: yeni skriptlər və siyahı qismən yükləmədə (sparse-checkout) var; dəyişənlər seçim addımına verilir.
  const wf = read(".github/workflows/sosial-video.yml");
  for (const f of [".github/scripts/video-menbe.cjs", ".github/scripts/video-dunya.cjs", ".github/video-dunya.json"]) assert.ok(wf.split(f).length >= 3, `${f}: PR yolu və sparse-checkout`);
  for (const v of ["MENBE_VIDEO", "MENBE_YAYIM", "DUNYA_VIDEO", "DUNYA_GUNDE", "DUNYA_ARA_MIN"]) assert.ok(wf.includes(`${v}: \${{ vars.${v} }}`), v);
  assert.match(wf, /options: \[avtomatik, hava, xeber, maraqli, dunya, x, kanal\]/);   // kanal: 2026-11-27, video-kanal.cjs
});

test("arxiv: the owner's release also takes credited third-party footage («mənbə: Ad») — no watermark or platform refusal for it", () => {
  const VA = require("../.github/scripts/video-arxiv.cjs");
  const l = VA.sahibSetirleri(["a.mp4 | Bakı Olimpiya Stadionu, Bakı | mənbə: Bizim.Media", "b.mp4 | Bakı | AzTV efiri", "c.mp4 | Bakı | öz çəkilişim"].join("\n"));
  assert.deepEqual(l.map(x => [x.fayl, x.icaze || "", x.kredit || ""]), [["a.mp4", "menbe", "Bizim.Media"], ["b.mp4", "", ""], ["c.mp4", "oz-cekilis", "8ulduz.az"]]);
  assert.match(l[1].xeta, /«mənbə: Ad» yazın/, "sərbəst yazılmış üçüncü tərəf adı: necə yazmaq lazım olduğu deyilir");
  const e = { id: "sahib-a", menbe: "Sahib", fayl: `${VA.SAHIB_URL}a.mp4`, icaze: "menbe", kim: "Bizim.Media", kredit: "Bizim.Media", yer: ["Baku Olympic Stadium", "Baku", "Azerbaijan"],
    olcu: [1920, 1080], keyfiyyet: 3, yoxlama: { tarix: "2026-11-26", model: "gemini", suNisani: true, ekran: false, statik: "nisan" } };
  assert.equal(VA.kecerli(e), "", "mənbəli görüntüdə su nişanı və üçüncü tərəf adı rədd səbəbi deyil");
  assert.match(VA.kecerli({ ...e, icaze: "oz-cekilis" }), /su nişanı|üçüncü tərəf/, "öz çəkiliş kimi yazılanda əvvəlki yoxlamalar qalır");
  assert.match(VA.kecerli({ ...e, yer: ["Stepanakert", "Azerbaijan"] }), /siyasi/);
});

// --- X videoları: «Çox baxılan» ---------------------------------------------------------------------------------------------------
// Sahib, 2026-11-26: «X qoş… həm sayt həm də sos şəbəkələrdə "çox baxılan" videolar verilməsini təmin et», «instagramda müəyyən
// etdiyimiz çox baxılan istiqamətlərini X-ə tətbiq et».
const xi = (id, o = {}) => ({ id: String(id), a: "TheFigen_", n: "Figen", m: "maraqli", u: `https://video.twimg.com/amplify_video/${id}/vid/avc1/720x1280/a.mp4?tag=21`, i: "https://pbs.twimg.com/x.jpg",
  w: 720, h: 1280, t: new Date(NOW - 2 * 3600e3).toISOString(), q: "h", v: 500000, c: "Yenidoğulmuş əkizlərin bir-birinə sarılaraq yatdığı anlar. Görüntülər milyonlarla insanı təsirləndirib.", ...o });

// X paylaşımının öz mətni (api.fxtwitter.com) və Gemini-nin əlavəsi — sınaq şəbəkəsi. elave: mətn, sorğu → mətn və ya null (Gemini cavab vermir).
const X_POST = "Newborn twins in Brazil keep hugging each other after birth, just like they did in the womb. Their mother filmed them in Sao Paulo https://t.co/abc #twins @someone";
const X_ELAVE = "Əkizlər Braziliyada doğulandan sonra da bir-birini qucaqlamağa davam edirlər, ana bətnində olduğu kimi. Onları San-Pauluda anaları çəkib.";
const xNet = (elave = X_ELAVE, post = X_POST, seen = { asked: [], prompt: "" }) => async (url, o = {}) => {
  seen.asked.push(url);
  if (url.startsWith("https://api.fxtwitter.com/")) return post == null ? { ok: false, status: 404 } : { ok: true, status: 200, json: async () => ({ tweet: { text: post } }) };
  if (/models\?pageSize/.test(url)) return { ok: true, json: async () => ({ models: [] }) };
  if (/generativelanguage/.test(url)) {
    seen.prompt = JSON.parse(o.body).contents[0].parts[0].text;
    const e = typeof elave === "function" ? elave(seen.prompt) : elave;
    return e == null ? { ok: false, status: 400, json: async () => ({}) } : { ok: true, status: 200, json: async () => ({ candidates: [{ content: { parts: [{ text: JSON.stringify({ elave: e }) }] } }] }) };
  }
  return { ok: false, status: 404 };
};
const X_ENV = { GEMINI_API_KEY: "g", VIDEO_GEMINI_WAIT_MS: "0" };

test("X: the most-watched recent videos, weighted by the Instagram directions, league footage included (owner 2026-11-26); big media companies, trailers, war footage and anything the site rule refuses are left out; no topic twice in a row", () => {
  const items = [xi(100001), xi(100002, { m: "xeber", a: "bpthaber", v: 600000, c: "İstanbulda yanğınsöndürənlər balkonda qalan uşağı xilas ediblər, görüntülər yayılıb." }),
    xi(100003, { m: "idman", a: "trtspor", v: 5000000, c: "Arda Güler komandasına qələbə gətirən hərəkəti ilə yadda qaldı, azarkeşlər ayaqda alqışladı." }),
    xi(100004, { v: 90000 }), xi(100005, { t: new Date(NOW - 40 * 3600e3).toISOString() }), xi(100006, { a: "FoxNews", m: "xeber", v: 900000 }),
    xi(100007, { m: "xeber", v: 2000000, c: "Hava limanında təyyarəyə endirilən zərbənin görüntüləri yayılıb, hadisə yerində yanğın başlayıb." }),
    xi(100008, { m: "kino", v: 800000, c: "Yeni filmin treyleri yayımlanıb və qısa vaxtda milyonlarla baxış toplayıb, izləyicilər həyəcanla gözləyir." }),
    xi(100009, { m: "tebiet", a: "AMAZlNGNATURE", v: 450000, c: "Ana fil balasını çaydan çıxarmaq üçün xortumu ilə kömək edir, sürü onları gözləyir." }),
    xi(100010, { c: "Qısa izah." }), xi(100011, { v: 700000, c: "Azərbaycan haqqında xarici mənbənin yaydığı video sosial şəbəkələrdə müzakirə olunur." }), xi("x12")];
  const policy = a => /Azərbaycan/.test(`${a.title} ${a.summary}`) || !/^https:\/\/x\.com\//.test(a.sourceUrl);
  const pool = VD.xNamizedler(items, { state: { xv: {}, v: {}, skip: {} }, now: NOW, policy });
  // Liqaların oyun kadrı (sahib 2026-11-26: «liqaların oyun kadrını niyə götürmürük?» → «3 et»). Sıra baxış × qrup × güclü istiqamət
  // (X əmsalı; sahib, 2026-11-26): 5 000 000 × 1,3 (idman) × 1,7 (xarici futbol: Arda Güler) birincidir; 600 000 × 1,1 (xəbər) × 1,7
  // (qəza/xilasetmə) = 1 122 000 > 500 000 × 1,3 (maraqlı) × 1,5 (insan hekayəsi: əkizlər) = 975 000. Təbiət qrupu (fil) çıxıb
  // («nə heyvan nə təbiət nə kosmos»). Fox News, treyler, müharibə kadrı yoxdur.
  assert.deepEqual(pool.map(c => c.x.id), ["100003", "100002", "100001"]);
  assert.deepEqual(pool.map(c => c.ist), ["xarici_futbol", "qeza", "insan"]);
  assert.equal(VD.xBasliq(pool[2].c), "Yenidoğulmuş əkizlərin bir-birinə sarılaraq yatdığı anlar", "başlıq: izahın birinci cümləsi, nöqtəsiz");
  // Liqa və idman yayımçıları qadağan siyahısında deyil; media şirkətləri qalır.
  const deny = new RegExp(require("../.github/video-dil/az.json").x.qadagan, "i");
  for (const h of ["NBA", "ChampionsLeague", "premierleague", "trtspor", "F1", "ufc", "ESPNNBA", "WWE"]) assert.equal(deny.test(h), false, h);
  for (const h of ["FoxNews", "BBCWorld", "netflix", "redbull", "IGN"]) assert.equal(deny.test(h), true, h);
  // Eyni mövzu dalbadal getmir: son X videosu idmandırsa idman sona keçir (başqa mövzu yoxdursa yenə gedir).
  const sec = NOW / 1000;
  assert.deepEqual(VD.xNamizedler(items, { state: { xm: { idman: sec - 600, maraqli: sec - 9000 } }, now: NOW, policy }).map(c => c.x.id), ["100002", "100001", "100003"]);
  assert.deepEqual(VD.xNamizedler([xi(100003, { m: "idman", a: "trtspor", v: 5000000, c: items[2].c })], { state: { xm: { idman: sec } }, now: NOW, policy }).map(c => c.x.id), ["100003"]);
  // İşlənmiş video bir də getmir.
  assert.deepEqual(VD.xNamizedler(items, { state: { xv: { [VD.xId("100001")]: NOW / 1000 } }, now: NOW, policy }).map(c => c.x.id), ["100003", "100002"]);
  assert.deepEqual(VD.xOptions({}), { on: true, perDay: 6, gapMin: 120, minV: 100000, maxAgeH: 36 });
  assert.match(VD.xDue({ xv: { a: NOW / 1000 - 3600 } }, NOW, VD.xOptions({})), /60 dəq əvvəl \(ara 120 dəq\)/);
  assert.equal(VD.xDue({ xv: {} }, NOW, VD.xOptions({})), "");
  assert.match(VD.xDue({ xv: {} }, NOW, VD.xOptions({ X_VIDEO: "0" })), /söndürülüb/);
});

test("X: the picked video becomes a «Çox baxılan» entry — the clip leads (video lasts as long as the clip), credit to the account; it goes first when due", async () => {
  const dir = tmp(), file = path.join(dir, "reels.json");
  fs.writeFileSync(file, JSON.stringify({ items: [xi(100001), xi(100002, { v: 300000 })] }));
  await assert.rejects(VD.xHazirla({ now: NOW, state: {}, env: {}, dir, log: () => {}, file }), /qaydası/);
  const got = [];
  const x = await VD.xHazirla({ now: NOW, state: { skip: {} }, env: X_ENV, fetch: xNet(), policy: () => false, dir, log: () => {}, file, deps: { indir: async (u, f, _f, ref) => { got.push([u, ref]); fs.writeFileSync(f, mp4()); return ""; } } });
  assert.deepEqual({ tur: x.tur, kind: x.kind, title: x.title, bolme: x.bolme, source: x.source, sourceUrl: x.sourceUrl, baxis: x.baxis, klip_boyu: x.klip_boyu, kredit: x.menbeVideo.kredit, category: x.category },
    { tur: "x", kind: "x", title: "Yenidoğulmuş əkizlərin bir-birinə sarılaraq yatdığı anlar", bolme: "Çox baxılan", source: "Figen (X)", sourceUrl: "https://x.com/TheFigen_/status/100001", baxis: 500000, klip_boyu: 30, kredit: "@TheFigen_ (X)", category: "dunya" });
  assert.equal(x.text, `${xi(100001).c} ${X_ELAVE}`, "izah + paylaşımın faktları; baxış sayı deyilmir (sahib, 2026-11-26)");
  assert.deepEqual([x.izah, x.metn], [xi(100001).c, "paylasim"], "kadr yoxlaması üçün (xKadrYoxla)");
  assert.deepEqual(got, [[xi(100001).u, "https://x.com/"]]);
  // Fayl alınmasa növbəti ən çox baxılan sınanır.
  const st = { skip: {} };
  const y = await VD.xHazirla({ now: NOW, state: st, env: X_ENV, fetch: xNet(), policy: () => false, dir, log: () => {}, file, deps: { indir: async (u, f) => (/100001/.test(u) ? "HTTP 403" : (fs.writeFileSync(f, mp4()), "")) } });
  assert.equal(y.sourceUrl, "https://x.com/TheFigen_/status/100002");
  assert.ok(st.skip[VD.xId("100001")]);
  // Montaj: klip_boyu — mətn qısa olsa da video klip boyu davam edir, sonluq sonda qalır.
  const p = V.prepare({ id: x.id, title: x.title, text: x.izah, category: "dunya", bolme: x.bolme, source: x.source, publishedAt: x.publishedAt, tur: "x", kind: "x" }, { cats: [], footage: true });
  assert.equal(p.label, "ÇOX BAXILAN");
  const qisa = V.timeline(p, null), uzun = V.timeline({ ...p, min_s: 30 }, null);
  assert.ok(qisa.duration < 20 && Math.abs(uzun.duration - 30) < 0.5, `${qisa.duration} → ${uzun.duration}`);
  assert.ok(Math.abs(uzun.outro[1] + 0.3 - uzun.duration) < 0.05, "sonluq (abunə çağırışı) videonun sonundadır");
  assert.equal(V.timeline({ ...p, min_s: 500 }, null).duration <= V.MAX_S, true);
  assert.equal(V.storyFields({ id: "x1", title: "T", kind: "x" }).url, "https://8ulduz.az/#/videolent");
  // Seçim: X vaxtıdırsa birinci gedir, gündəlik həddə və fasiləyə sayılır; 2 saat dolmayınca bir də soruşulmur.
  const old = process.env.GITHUB_OUTPUT; process.env.GITHUB_OUTPUT = path.join(dir, "out.txt");
  try {
    const s2 = SV.readState("/yoxdur", NOW); let asked = 0, dunya = 0;
    const args = now => ({ articles: [], env: { VIDEO_ACAR: "1", MARAQLI_VIDEO: "0" }, now, state: s2, fetch: async () => ({ ok: false }), cats: [], dir, log: () => {},
      xvideo: async a => { asked++; assert.equal(typeof a.policy, "function"); return x; }, dunya: async () => { dunya++; return null; } });
    const r = await SV.sec(args(NOW));
    assert.equal(r.link, "https://8ulduz.az/#/videolent");
    assert.ok(s2.xv[x.id] && s2.v[x.id] && asked === 1 && dunya === 0);
    assert.ok(s2.xm.maraqli, "mövzu yazılır: növbəti X videosu başqa mövzudan olur");
    const fst = path.join(dir, "state-x.json");
    fs.writeFileSync(fst, JSON.stringify(s2));
    assert.ok(SV.readState(fst, NOW).xm.maraqli, "siyahı xm-i saxlayır");
    assert.match(fs.readFileSync(process.env.GITHUB_OUTPUT, "utf8"), /hazir=1\ntur=x/);
    await SV.sec(args(NOW + 31 * 60e3));
    assert.equal(asked, 1, "X-in arası (120 dəq) dolmayıb");
    assert.equal(dunya, 1, "növbə dünya videosundadır");
  } finally { if (old === undefined) delete process.env.GITHUB_OUTPUT; else process.env.GITHUB_OUTPUT = old; }
});

// Sahib, 2026-11-26: «Bəli, uzat» — X-in izahı bir cümlədir, 30 saniyəlik videoda səs ~4 saniyə oxuyurdu. Həmin gün: «Bu video 4 milyondan
// çox dəfə izlənib — nəyə lazımdır?» — baxış sayı səsdən və altyazıdan çıxıb. 2026-11-27: «belə çox qısa və şərhi çox az və başa düşülməyən
// olmasın videolar» — izah və kadr təsvirindən ibarət iki cümləlik video silindi: şərh ən az 3 cümlə və 180 simvoldur, paylaşımın öz
// faktlarından; alınmayan video götürülmür.
test("X: the voice reads the caption and 2–3 facts from the post's own text (Gemini, checked like the world text); too little or unclear → the video is not taken", async () => {
  assert.equal(VD.xBaxis, undefined, "baxış sayı cümləsi yoxdur");
  assert.ok(!("baxis_mln" in require("../.github/video-dil/az.json").x), "profildə də yoxdur");
  const IZAH = "Yenidoğulmuş əkizlərin bir-birinə sarılaraq yatdığı anlar.";
  const c = { id: VD.xId("100001"), x: xi(100001, { c: IZAH, v: 2110507 }), c: IZAH };
  const seen = { asked: [], prompt: "" };
  const opt = (elave, post) => ({ env: X_ENV, fetch: xNet(elave, post, seen), policy: a => /Azərbaycan/.test(`${a.title} ${a.summary}`), log: () => {} });
  assert.deepEqual(await VD.xMetn(c, opt(X_ELAVE)), { text: `${IZAH} ${X_ELAVE}` });
  const prompt = seen.prompt;
  assert.match(prompt, /İzah: Yenidoğulmuş əkizlərin/); assert.match(prompt, /Azərbaycan ədəbi dilində/); assert.match(prompt, /ƏLAVƏ faktlar/);
  assert.match(prompt, /2–3 cümlə/); assert.match(prompt, /Tamaşaçı Azərbaycandadır və mövzunu bilmir/); assert.match(prompt, /yalnız ekran yazısı/);
  assert.match(prompt, /Paylaşım \(@TheFigen_\): Newborn twins in Brazil .* in Sao Paulo twins someone$/, "keçid atılır, heşteq və @ işarəsiz");
  // Yoxlamadan keçməyən əlavə: video götürülmür (yox — səbəbi ilə).
  const UZUN = "Onları San-Pauluda anaları çəkib və görüntünü sosial şəbəkədə paylaşıb.";
  const red = async (elave, re) => { const r = await VD.xMetn(c, opt(elave)); assert.ok(r.yox && re.test(r.yox), `${elave}: ${JSON.stringify(r)}`); };
  await red(`Əkizlər 3 kiloqram çəki ilə Braziliyada doğulublar və bir-birini qucaqlayırlar. ${UZUN}`, /mənbədə olmayan rəqəm: 3/);
  await red(`Əkizlərin videosu Azərbaycanda da çox yayılıb və hamı tərəfindən bəyənilib. ${UZUN}`, /saytın qaydasından keçmir/);
  await red(`Əkizlər cəbhə bölgəsindəki xəstəxanada doğulublar və hələ orada qalırlar. ${UZUN}`, /müharibə/);
  await red("Əkizlər Braziliyada doğulub. Anaları onları çəkib.", /uzunluq/);
  await red("Əkizlər Braziliyada doğulandan sonra da bir-birini qucaqlamağa davam edirlər, ana bətnində olduğu kimi, onları anaları San-Pauluda çəkib.", /cümlə sayı 2/);
  await red("", /aydın fakt yoxdur/);
  // Qısa paylaşım — götürülmür; paylaşım alınmadı, açar yoxdur, Gemini cavab vermir — indi yoxlanmır (növbəti dövrədə yenidən).
  for (const [o, k, re] of [[opt(X_ELAVE, "So cute 😍"), "yox", /qısadır/], [opt(X_ELAVE, null), "gec", /alınmadı/], [{ ...opt(X_ELAVE), env: {} }, "gec", /GEMINI_API_KEY/]]) {
    seen.asked = [];
    const r = await VD.xMetn(c, o);
    assert.ok(re.test(r[k] || ""), JSON.stringify(r));
    assert.ok(!seen.asked.some(u => /generativelanguage/.test(u)), "Gemini soruşulmur");
  }
  assert.deepEqual(await VD.xMetn(c, opt(null)), { gec: "Gemini cavab vermir" });
  // Bütöv yol: xHazirla mətni buradan götürür.
  const dir = tmp(), file = path.join(dir, "reels.json");
  fs.writeFileSync(file, JSON.stringify({ items: [c.x] }));
  const x = await VD.xHazirla({ now: NOW, state: { skip: {} }, env: X_ENV, fetch: xNet(), policy: () => false, dir, log: () => {}, file,
    deps: { indir: async (u, f) => (fs.writeFileSync(f, mp4()), "") } });
  assert.equal(x.text, `${IZAH} ${X_ELAVE}`);
  assert.deepEqual([x.izah, x.metn], [IZAH, "paylasim"]);
  assert.equal(x.title, "Yenidoğulmuş əkizlərin bir-birinə sarılaraq yatdığı anlar", "başlıq izahdır");
});

// Silinən video (2026-11-27, @Breaking911): paylaşımda «Bears-Lions» oyununa təcili xəbərdarlıq yayımının girməsindən başqa fakt yox idi,
// səs iki cümlə idi (izah + kadr təsviri). İndi belə video ötürülür, növbəti namizəd götürülür; fayl yalnız seçiləndə yüklənir.
test("X: a post with too little to say is skipped for good and the next candidate is taken; the clip is downloaded only for the chosen one; no Gemini — nothing is burnt", async () => {
  const dir = tmp(), file = path.join(dir, "reels.json");
  const bears = xi(200001, { a: "Breaking911", n: "Breaking911", m: "xeber", v: 3838656, c: "Bears-Lions matçı zamanı efirə ABŞ-ın təcili xəbərdarlıq sistemi daxil olub." });
  const ikinci = xi(200002, { v: 900000 });
  fs.writeFileSync(file, JSON.stringify({ items: [bears, ikinci] }));
  const st = { skip: {} }, got = [], logs = [];
  const elave = p => (/Bears-Lions/.test(p) ? "" : X_ELAVE);
  const x = await VD.xHazirla({ now: NOW, state: st, env: X_ENV, fetch: xNet(elave), policy: () => false, dir, log: s => logs.push(s), file,
    deps: { indir: async (u, f) => { got.push(u); fs.writeFileSync(f, mp4()); return ""; } } });
  assert.equal(x.sourceUrl, "https://x.com/TheFigen_/status/200002");
  assert.ok(st.skip[VD.xId("200001")], "bir də sınanmır");
  assert.deepEqual(got, [ikinci.u], "ötürülən videonun faylı yüklənmir");
  assert.ok(logs.some(s => /ötürülür \(paylaşımda şərhə yetən aydın fakt yoxdur\) — @Breaking911/.test(s)), logs.join(" | "));
  // Hamısı ötürülür — video yoxdur.
  const st2 = { skip: {} };
  assert.equal(await VD.xHazirla({ now: NOW, state: st2, env: X_ENV, fetch: xNet(""), policy: () => false, dir, log: () => {}, file, deps: { indir: async () => "" } }), null);
  assert.equal(Object.keys(st2.skip).length, 2);
  // Açar yoxdur və ya Gemini cavab vermir: heç nə götürülmür, heç nə «yanmır» (növbəti dövrədə yenidən).
  for (const o of [{ env: {}, fetch: xNet() }, { env: X_ENV, fetch: xNet(null) }]) {
    const s3 = { skip: {} }, g3 = [];
    assert.equal(await VD.xHazirla({ now: NOW, state: s3, ...o, policy: () => false, dir, log: () => {}, file, deps: { indir: async u => (g3.push(u), "") } }), null);
    assert.deepEqual([Object.keys(s3.skip), g3], [[], []]);
  }
  assert.equal(VD.X_CEHD, 5, "bir dövrədə ən çox 5 namizəd");
  // Şərh həddi: silinən videonun mətni keçmir; dünya videosunun mətni keçir.
  assert.match(VS.serhAzdir("Bears-Lions matçı zamanı efirə ABŞ-ın təcili xəbərdarlıq sistemi daxil olub. Stadionda idmançılar yaşıl sahə üzərində dayanaraq oyununu davam etdirirlər."),
    /şərh azdır: 2 cümlə, 153 simvol \(ən az 3 cümlə, 180 simvol\)/);
  assert.equal(VS.serhAzdir("İstanbulun Fatih rayonunda tramvay ilə İETT avtobusu toqquşub. Qəza nəticəsində on beş nəfər xəsarət alıb. Hadisə yerindən gələn məlumata görə yaralananlar müxtəlif xəstəxanalara aparılıb."), "");
  assert.match(VS.serhAzdir(""), /0 cümlə, 0 simvol/);
  assert.deepEqual(VS.SERH_MIN, { cumle: 3, simvol: 180 });
});

test("qırmızı xətt 2: sources outside the feed list (world video, X) pass the foreign-source rule — nothing about Azerbaijan or its leadership, no blocked host", () => {
  const app = require("../.github/scripts/topics.cjs").loadApp(root);
  const t = (title, sourceUrl = "https://x.com/a/status/1", summary = "") => app.xariciPozur({ title, summary, sourceUrl });
  assert.equal(t("Yenidoğulmuş əkizlərin bir-birinə sarılaraq yatdığı anlar."), false);
  assert.equal(t("Dog rescued from frozen lake", "https://tv.example/v/1", "Firefighters pulled a dog from a frozen lake in Oslo."), false);
  assert.equal(t("Azərbaycan Prezidenti İlham Əliyev çıxış edib"), true);
  assert.equal(t("Neytral başlıq", "https://tv.example/v/1", "The president of Azerbaijan met the delegation."), true, "xülasədə də yoxlanır");
  assert.equal(t("Neytral başlıq", "https://www.meydan.tv/az/video/1"), true, "bağlı sayt");
  // Lentin qaydası (policyViolation) siyahıda olmayan mənbəni bütünlüklə rədd edir — dünya və X videoları ona görə ayrıca qaydadan keçir.
  assert.equal(app.policyViolation({ title: "Neytral", source: "Sınaq TV", sourceUrl: "https://tv.example/v/1" }), true);
  // Qayda hər yerdə növə görə seçilir: seçim (sosial-video.cjs), montaj (video-xeber.cjs), YouTube və TikTok (yalnız dünya videosu).
  assert.match(read(".github/scripts/sosial-video.cjs"), /xarici: a => app\.xariciPozur\(a\)/);
  assert.match(read(".github/scripts/video-xeber.cjs"), /x\?\.kind === "dunya" \|\| x\?\.kind === "x" \? app\.xariciPozur\(x\) : app\.policyViolation\(x\)/);
  // YouTube və TikTok (sahib, 2026-11-26: «Bəli, hamısına»): bizim montajımız olan X videosu (kind: "x") gedir; X-in xam videosu,
  // nişansız fayl və növsüz x.com xəbəri əvvəlki kimi getmir.
  const nisanli = Buffer.concat([mp4(4000), Buffer.from("comment=8ulduz.az")]);
  for (const [f, U] of [["youtube.cjs", require("../.github/scripts/youtube.cjs")], ["tiktok.cjs", require("../.github/scripts/tiktok.cjs")]]) {
    const s = read(`.github/scripts/${f}`);
    assert.match(s, /a\?\.kind === "dunya" \|\| a\?\.kind === "x" \? app\.xariciPozur\(a\) : app\.policyViolation\(a\)/, f);
    const m = { id: "ab12".padEnd(16, "0"), own: true, kind: "x", title: "T", sourceUrl: "https://x.com/TheFigen_/status/100001" };
    assert.equal(U.foreignReason(m, nisanli, new Set(["100001"])), "", `${f}: «Çox baxılan» montajı`);
    assert.match(U.foreignReason({ ...m, kind: undefined }, nisanli), /sosial şəbəkədəndir/, `${f}: növsüz x.com xəbəri`);
    assert.match(U.foreignReason({ ...m, id: "100001" }, nisanli, new Set(["100001"])), /X videosudur/, `${f}: xam X videosu`);
    assert.match(U.foreignReason(m, mp4(4000)), /nişanı yoxdur/, `${f}: bizim montaj deyil`);
    assert.match(U.foreignReason({ ...m, own: false }, nisanli), /own: true yoxdur/, f);
  }
});

test("dünya videosu: per-source rules found in the live check — JSON-LD file, skip pattern, bigger rendition, feed-only, sitemap index", async () => {
  const page = `<script type="application/ld+json">{"@type":"VideoObject","contentUrl":"https:\\/\\/cdn.ex.co\\/a\\/720p.mp4","uploadDate":"2026-11-25"}</script>
    <video src="https://cdn.ex.co/playlist/1080p.mp4"></video><video src="https://media.w3.org/2010/05/sintel/trailer.mp4"></video>`;
  assert.deepEqual(VD.fayllar({ fayl: "jsonld" }, page, "https://i.example/tv/1"), ["https://cdn.ex.co/a/720p.mp4"], "səhifədəki başqa videolar yox, öz faylı");
  assert.deepEqual(VD.fayllar({ atla: "w3\\.org|playlist" }, page, "https://i.example/tv/1"), ["https://cdn.ex.co/a/720p.mp4"], "atla: saytın hər səhifəsindəki fayllar düşür");
  assert.deepEqual(VD.fayllar({ deyis: ["480x270_MP4", "1024x576_MP4"] }, `<video src="https://v.example/a/480x270_MP4_1.mp4">`, "https://m.example/"),
    ["https://v.example/a/1024x576_MP4_1.mp4", "https://v.example/a/480x270_MP4_1.mp4"], "iri keyfiyyət əvvəl, olmasa əsli");
  assert.match(VD.kecerli({ ...M1, fayl: "x" }), /fayl qaydası/);
  assert.match(VD.kecerli({ ...M1, deyis: ["a"] }), /deyis/);
  assert.match(VD.kecerli({ ...M1, atla: "(" }), /atla/);
  // Sayt xəritəsinin siyahısı → birinci hissə; sehife: false — fayl yalnız siyahıdan.
  const idx = `<sitemapindex><sitemap><loc>https://s.example/sitemaps/video/2026-11.xml</loc></sitemap><sitemap><loc>https://s.example/sitemaps/video/2026-10.xml</loc></sitemap></sitemapindex>`;
  const part = `<urlset><url><loc>https://s.example/video/yasam/kedi-kurtarildi</loc><video:video><video:title>Kedi itfaiye tarafından kurtarıldı</video:title>
    <video:description>${"Mahalle sakinleri ağaçta mahsur kalan kediyi fark edip itfaiyeye haber verdi. ".repeat(3)}</video:description><video:content_loc>https://cdn.s.example/1_1080p.mp4</video:content_loc>
    <video:publication_date>${new Date(NOW - 3600e3).toISOString()}</video:publication_date></video:video></url></urlset>`;
  const sm = { ...M1, ad: "Xəritə", nov: "sitemap", lent: "https://s.example/sitemap/video.xml", sec: "/video/yasam/" };
  const st = {};
  const pool = await VD.namizedler({ list: [sm], state: st, now: NOW, fetch: net({ [sm.lent]: idx, "https://s.example/sitemaps/video/2026-11.xml": part }), policy: () => false, log: () => {} });
  assert.deepEqual(pool.map(c => [c.a.title, c.fayllar]), [["Kedi itfaiye tarafından kurtarıldı", ["https://cdn.s.example/1_1080p.mp4"]]]);
  // Həddən iri fayl (HEAD content-length) namizəd olmur.
  const big = { ok: true, status: 200, headers: { get: k => (k === "content-length" ? String(200e6) : "video/mp4") }, text: async () => "" };
  const p2 = await VD.namizedler({ list: [sm], state: {}, now: NOW, fetch: net({ [sm.lent]: idx, "https://s.example/sitemaps/video/2026-11.xml": part, "https://cdn.s.example/1_1080p.mp4": big }), policy: () => false, log: () => {} });
  assert.deepEqual(p2, []);
  // Repodakı siyahı: «say kifayətdən artıq» — ən azı 20 aktiv mənbə, üç dildə.
  const act = VD.menbeler();
  assert.ok(act.length >= 20, `aktiv mənbə: ${act.length}`);
  assert.deepEqual([...new Set(act.map(m => m.dil))].sort(), ["en", "ru", "tr"]);
});
