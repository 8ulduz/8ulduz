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
  // Yayım kadrı (qol, icmal, film, klip): götürülmür; MENBE_YAYIM=1 ilə açılır. MENBE_VIDEO=0 hər şeyi söndürür. Öz səhifələrimiz (X videoları) oxunmur.
  const qol = { ...a, title: "“Sabah” fərqi azaltdı: qol - Video" };
  assert.equal(await M.menbeVideo(qol, page, { env: {}, fetch: f, log: s => logs.push(s), dir: tmp() }), null);
  assert.ok(logs.some(s => /yayım kadrı/.test(s)));
  assert.equal((await M.menbeVideo(qol, page, { env: { MENBE_YAYIM: "1" }, fetch: f, log: () => {}, dir: tmp() }))?.kredit, "Bizim.Media");
  assert.equal(await M.menbeVideo(a, page, { env: { MENBE_VIDEO: "0" }, fetch: f, log: () => {}, dir: tmp() }), null);
  assert.equal(await M.menbeVideo({ ...a, source: "8ULDUZ", sourceUrl: "https://8ulduz.az/x/1.html", alts: [] }, `<video src="https://8ulduz.az/v/1.mp4"></video>`, { env: {}, fetch: f, log: () => {}, dir: tmp() }), null);
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
    const x = await SV.sec({ articles: [a], env: { VIDEO_ACAR: "1", GEMINI_API_KEY: "g", DUNYA_VIDEO: "0", MARAQLI_VIDEO: "0" }, now: NOW, state: st, fetch: f, cats: [{ slug: "gundem", label: "Gündəm" }], dir, log: () => {}, menbe: async () => mv });
    assert.equal(x.id, a.id);
    assert.deepEqual(JSON.parse(fs.readFileSync(path.join(dir, "xeber.json"), "utf8")).menbeVideo, mv);
    // Mənbə videosu tapılmayanda əvvəlki kimi (sahə yoxdur).
    const st2 = SV.readState("/yoxdur", NOW);
    await SV.sec({ articles: [a], env: { VIDEO_ACAR: "1", GEMINI_API_KEY: "g", DUNYA_VIDEO: "0", MARAQLI_VIDEO: "0" }, now: NOW, state: st2, fetch: f, cats: [], dir, log: () => {}, menbe: async () => null });
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
const M1 = { ad: "Sınaq TV", dil: "en", lent: "https://tv.example/rss", nov: "mrss", istiqamet: [1, 2], sertler: "sınaq" };
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
  const good = { sec: 1, istiqamet: 4, basliq: "Osloda donmuş göldən it xilas edildi.", text: AZ, etiket: ["xilasetmə", "Oslo", "#heyvanlar"] };
  const s = await VD.sec(pool, { env: { GEMINI_API_KEY: "g" }, fetch: gem(p => { prompt = p; return JSON.stringify(good); }), policy: leadership, log: () => {} });
  assert.match(prompt, /insan hekayəsi/); assert.match(prompt, /Azərbaycan ədəbi dilində/); assert.match(prompt, /\[1\] Mənbə: Sınaq TV \(en\)\nDog rescued/);
  assert.equal(s.title, "Osloda donmuş göldən it xilas edildi", "başlığın sonundakı nöqtə atılır");
  assert.equal(s.text, AZ); assert.equal(s.istiqamet, 4); assert.deepEqual(s.etiket, ["xilasetmə", "Oslo", "heyvanlar"]);
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
    const got = await SV.sec({ articles: [], env: { VIDEO_ACAR: "1", MARAQLI_VIDEO: "0" }, now: NOW, state: st, fetch: async () => ({ ok: false }), cats: [{ slug: "dunya", label: "Dünya" }], dir, log: () => {},
      dunya: async a => { asked++; assert.equal(typeof a.policy, "function"); return x; } });
    assert.equal(asked, 1);
    assert.equal(got.bolme, "Dünya"); assert.equal(got.link, "https://8ulduz.az/bolme/dunya/"); assert.equal(got.url, got.link);
    assert.ok(st.dv[x.id] && st.v[x.id] && st._last, "gündəlik həddə və fasiləyə sayılır");
    assert.match(fs.readFileSync(process.env.GITHUB_OUTPUT, "utf8"), /hazir=1\ntur=dunya/);
    // Növbəti pəncərə (30 dəq sonra): dünya videosunun arası (90 dəq) dolmayıb — soruşulmur.
    await SV.sec({ articles: [], env: { VIDEO_ACAR: "1", MARAQLI_VIDEO: "0" }, now: NOW + 31 * 60e3, state: st, fetch: async () => ({ ok: false }), cats: [], dir, log: () => {}, dunya: async () => { asked++; return null; } });
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
  assert.match(wf, /options: \[avtomatik, hava, xeber, maraqli, dunya\]/);
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
