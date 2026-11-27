// Xəbər videosunun seçimi (sahib, 2026-11-27, «A B ni də»): bir hadisə bir dəfə sayılır, öz görüntülü xəbərə 2 mənbə bəs edir və o,
// X və dünya videosundan əvvəl gedir, gecənin xəbəri səhər yenə namizəddir (.github/scripts/sosial-video.cjs hadiseler, pick, sec).
// Səbəb: Baku.ws-in «"Beşiktaş"ın 10-dan çox azarkeşi saxlanılıb» Reels-i (stadionun öz kadrı) — bizdə heç olmadı.
// Şəbəkə və ffmpeg yoxdur: səhifələr, Gemini və fayl saxtadır; mənbə videosu video-menbe.cjs-in öz kodu ilə tapılır.
"use strict";
const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("fs"), os = require("os"), path = require("path");
const SV = require("../.github/scripts/sosial-video.cjs");
const S = require("../.github/scripts/social.cjs");
const MV = require("../.github/scripts/video-menbe.cjs");

const FX = JSON.parse(fs.readFileSync(path.join(__dirname, "fixtures", "video-besiktas.json"), "utf8"));
const tmp = () => fs.mkdtempSync(path.join(os.tmpdir(), "secim-"));
const mp4 = (n = 200e3) => { const b = Buffer.alloc(n); b.write("ftypisom", 4, "latin1"); return b; };
const FILLER = "Hadisə yerinə polis əməkdaşları və təcili yardım briqadaları cəlb olunub. Azarkeşlərin bir hissəsi tribunadan çıxarılıb və ərazidə nəzarət gücləndirilib. " +
  "Oyun bir müddət dayandıqdan sonra yenidən bərpa olunub. Rəsmilər hadisənin bütün təfərrüatlarını araşdırdıqlarını bildiriblər. " +
  "Zərər çəkənlərə yerindəcə tibbi yardım göstərilib. Klubun rəhbərliyi hadisə ilə bağlı ayrıca bəyanat yayacağını açıqlayıb.";
// Saxta Gemini (video-ssenari.cjs): uyğun, 6 cümlə + mənbənin son cümləsi.
const gemini = (url, o) => {
  if (/models\?pageSize/.test(url)) return { ok: true, json: async () => ({ models: [] }) };
  const src = (JSON.parse(o.body).contents[0].parts[0].text.split("Mənbə mətni:\n")[1] || "").trim();
  return { ok: true, status: 200, json: async () => ({ candidates: [{ content: { parts: [{ text: JSON.stringify({ uygun: true, text: `${FILLER} ${src.split(/(?<=\.)\s+/).pop()}`, axtar: [] }) }] } }] }) };
};
const html = (title, body, extra = "") => `<html><head><meta property="og:title" content="${title}"><meta property="og:description" content="${body}"></head><body><h1>${title}</h1><p>${body}</p>${extra}</body></html>`;
const sehife = a => html(a.title, `${S.clean(a.title)}. Hadisə barədə ətraflı məlumat verilib, araşdırma davam edir və yeni təfərrüatlar gözlənilir.`);
// Lentin bütün səhifələri (YouTube pəncərəsi ilə — fayl yoxdur); Bizim.Media-nın səhifəsində öz faylı; saytın baş səhifəsində yox.
function net(articles, { fayl = {} } = {}) {
  const pages = new Map(), calls = [];
  for (const a of articles) {
    pages.set(a.sourceUrl, sehife(a).replace("</body>", '<iframe src="https://www.youtube.com/embed/x1"></iframe></body>'));
    for (const x of a.alts || []) if (x.sourceUrl && !pages.has(x.sourceUrl)) pages.set(x.sourceUrl, sehife({ title: x.title || a.title }));
  }
  for (const [u, file] of Object.entries(fayl)) pages.set(u, pages.get(u).replace("</body>", `<video src="${file}"></video></body>`));
  const f = async (url, o = {}) => {
    calls.push(url);
    if (/generativelanguage\.googleapis\.com/.test(url)) return gemini(url, o);
    if (Object.values(fayl).includes(url)) { const b = mp4(); return { ok: true, status: 200, headers: { get: k => (k === "content-length" ? String(b.length) : "video/mp4") }, arrayBuffer: async () => b }; }
    if (pages.has(url)) return { ok: true, status: 200, text: async () => pages.get(url) };
    if (/^https:\/\/[^/]+\/$/.test(url)) return { ok: true, status: 200, text: async () => "<html><body>baş səhifə</body></html>" };
    return { ok: false, status: 404, text: async () => "" };
  };
  return { f, calls };
}
async function withOutput(fn) {
  const dir = tmp(), old = process.env.GITHUB_OUTPUT;
  process.env.GITHUB_OUTPUT = path.join(dir, "out.txt");
  try { return await fn(dir); } finally { if (old === undefined) delete process.env.GITHUB_OUTPUT; else process.env.GITHUB_OUTPUT = old; }
}
const out = dir => (fs.existsSync(path.join(dir, "out.txt")) ? fs.readFileSync(path.join(dir, "out.txt"), "utf8") : "");

test("seçim: the Beşiktaş fight (2026-11-26) — 7 small clusters are one event, its own Bizim.Media footage is found and it goes ahead of a due world/X video", async () => {
  const now = Date.parse(FX.now), opt = SV.options({}), arts = FX.articles;
  const bizim = arts.find(a => a.id === FX.menbe);
  // Əvvəlki qayda: hər parça ayrı xəbərdir; öz faylı olan Bizim.Media (2 mənbə) namizəd deyil, ən böyük xəbər yanğındır.
  const old = S.candidates(arts, now, { ...opt, lang: "az", weight: a => SV.cekisi(a) });
  assert.ok(!old.some(a => a.id === bizim.id), "4 mənbə həddi: öz görüntülü xəbər düşmürdü");
  assert.equal(old[0].title, "Bakıda yaşayış binasında yanğın oldu");
  // Bir hadisə: 7 parça, mənbələr bir dəfə sayılır.
  const g = SV.hadiseler(arts, now, opt).find(x => x.uzv.some(y => y.a.id === bizim.id));
  assert.equal(g.uzv.length, 7);
  assert.equal(g.say, 15);
  const dist = new Set(g.uzv.flatMap(y => [y.a.source, ...y.a.alts.map(z => z.source)]));
  assert.equal(g.say, dist.size, "hər sayt bir dəfə");
  await withOutput(async dir => {
    const state = SV.readState("/yoxdur", now), logs = [], { f } = net(arts, { fayl: { [bizim.sourceUrl]: FX.mp4 } });
    let dunya = 0, xv = 0;
    const args = t => ({ articles: arts, env: { VIDEO_ACAR: "1", GEMINI_API_KEY: "g", MARAQLI_VIDEO: "0" }, now: t, state, fetch: f, cats: [{ slug: "idman", label: "İdman" }], dir, log: s => logs.push(s),
      dunya: async () => { dunya++; return { id: "d1".padEnd(16, "0"), tur: "dunya", title: "Dünya", text: "Mətn." }; },
      xvideo: async () => { xv++; return { id: "x1".padEnd(16, "0"), tur: "x", title: "X", text: "Mətn." }; } });
    // X və dünya videosunun vaxtıdır (siyahı boşdur) — amma öz görüntülü yerli xəbər əvvəl gedir.
    const x = await SV.sec(args(now));
    assert.equal(x.id, bizim.id, `nümayəndə faylı olan xəbərdir — ${logs.join(" | ")}`);
    assert.equal(x.title, bizim.title.replace(/ - Video$/, ""), "başlığın « - Video» nişanı videoya yazılmır");
    assert.deepEqual([dunya, xv], [0, 0], "dünya və X videosu soruşulmadı");
    assert.equal(x.menbeVideo.url, FX.mp4);
    assert.equal(x.menbeVideo.kredit, "Bizim.Media");
    assert.equal(x.menbeVideo.sehife, bizim.sourceUrl);
    assert.ok(fs.statSync(path.join(dir, MV.FAYL)).size > 100e3, "fayl qovluqdadır");
    assert.equal(1 + x.alts.length, 15, "videoda bütün hadisənin mənbələri");
    assert.ok(state.v[x.id] && state._last, "gündəlik həddə və fasiləyə sayılır");
    assert.equal(Object.keys(state.q).length, 6, "qalan 6 parça bir də video olmur");
    assert.equal(out(dir), "hazir=1\n", "xəbər videosu (tur yoxdur)");
    assert.ok(logs.some(s => /öz görüntülü xəbər — 15 mənbə \(7 xəbər bir hadisə\), görüntü: Bizim\.Media/.test(s)), logs.join("\n"));
    // Növbəti pəncərə: hadisə artıq video olub — X videosu öz növbəsi ilə gedir (həddi və arası dəyişmir).
    const y = await SV.sec(args(now + 31 * 60e3));
    assert.equal(y.tur, "x");
    assert.deepEqual([dunya, xv], [0, 1]);
  });
});

const art = (id, o = {}) => ({ id: id.padEnd(16, "0"), title: `Xəbər ${id}`, summary: "", category: "gundem", lang: "az", source: "APA", sourceUrl: `https://apa.az/${id}`,
  publishedAt: new Date(Date.parse(FX.now) - 20 * 60e3).toISOString(), alts: [], ...o });
const alts = (...names) => names.map((source, i) => ({ source, sourceUrl: `https://${source.toLowerCase().replace(/[^a-z]/g, "")}.az/${i}`, title: "" }));
const ENV = { VIDEO_ACAR: "1", GEMINI_API_KEY: "g", MARAQLI_VIDEO: "0", X_VIDEO: "0", DUNYA_VIDEO: "0" };
const mvOf = a => ({ file: MV.FAYL, url: "https://cdn.apa.az/v/1.mp4", sehife: a.sourceUrl, kredit: a.source, bytes: 1 });

test("seçim: own footage lowers the bar to 2 sources; without a file 4 are still needed; pages are read only for the top-ranked video stories", async () => {
  const now = Date.parse(FX.now), D = require("../.github/scripts/video-dil.cjs").dil();
  assert.equal(D.lent.min_menbe, 4, "həddin özü dəyişmir");
  assert.equal(D.lent.min_menbe_kadr, 2);
  // Çəki: öz faylı tapılıb — ×1,6 (əvvəl videolu ×1,3); «VİDEO» başlığı da videoludur.
  assert.equal(SV.cekisi(art("c1"), D, { kadr: true }), 1.6);
  assert.equal(SV.cekisi(art("c2", { alts: [{ source: "Oxu.az", title: "Qəza anı - VİDEO" }] })), 1.3);
  const run = async (articles, menbe) => withOutput(async dir => {
    const state = SV.readState("/yoxdur", now), logs = [], probed = [];
    const x = await SV.sec({ articles, env: ENV, now, state, fetch: net(articles).f, cats: [], dir, log: s => logs.push(s), menbe: async a => { probed.push(a.id); return menbe(a); } });
    return { x, probed, logs, state };
  });
  const v = (id, n, o = {}) => art(id, { title: `Gəncədə avtobus aşıb, ${id} - Video`, video: true, alts: alts(...["Report", "Oxu.az", "Trend", "Qafqazinfo", "Milli.az"].slice(0, n - 1)), ...o });
  // Faylı olan 2 mənbəli xəbər gedir (öz görüntüsü ilə); 1 mənbə — yox.
  let r = await run([v("a2", 2)], a => mvOf(a));
  assert.equal(r.x?.id, v("a2", 2).id);
  assert.ok(r.x.menbeVideo);
  r = await run([v("a1", 1)], a => mvOf(a));
  assert.equal(r.x, null);
  assert.deepEqual(r.probed, [], "1 mənbəli xəbərin səhifəsi oxunmur");
  // Faylı yoxdursa 3 mənbə bəs deyil; 4 mənbəli xəbər əvvəlki kimi gedir, səhifəsi ikinci dəfə yoxlanmır.
  r = await run([v("b3", 3)], () => null);
  assert.equal(r.x, null);
  assert.deepEqual(r.probed, [v("b3", 3).id]);
  assert.ok(r.logs.some(s => /uyğun xəbər yoxdur/.test(s)));
  r = await run([v("b4", 4)], () => null);
  assert.equal(r.x?.id, v("b4", 4).id);
  assert.equal(r.x.menbeVideo, undefined);
  assert.deepEqual(r.probed, [v("b4", 4).id], "bir dəfə");
  // Videosuz xəbərin səhifəsi fayl üçün oxunmur.
  r = await run([art("d3", { title: "Gəncədə avtobus aşıb", alts: alts("Report", "Oxu.az") })], a => mvOf(a));
  assert.equal(r.x, null);
  assert.deepEqual(r.probed, []);
  // Xərc: yalnız sıranın ilk SECIM_MAX (4) hadisəsindən videolu olanlar. Dörd böyük xəbər öndədirsə 2 mənbəli videolu xəbərə baxılmır;
  // seçilən adi xəbərin səhifəsinə isə əvvəlki kimi bir dəfə baxılır (montajdan əvvəl).
  const big = ["Sumqayıt", "Şəki", "Lənkəran", "Quba"].map((c, i) => art(`9${i}`, { title: `${c} rayonunda yeni məktəb tikilib`, alts: alts("Report", "Oxu.az", "Trend", "Qafqazinfo", "Milli.az", "Metbuat", "Axar.az") }));
  r = await run([...big, v("c3", 2)], a => (a.id === v("c3", 2).id ? mvOf(a) : null));
  assert.equal(r.x?.id, big[0].id, "adi xəbər gedir");
  assert.deepEqual(r.probed, [big[0].id]);
  assert.equal(r.x.menbeVideo, undefined);
  // Altı videolu xəbər: dövrədə ən çox 4 səhifə yoxlanır.
  r = await run(["Bərdə", "Tərtər", "Ağdam", "Füzuli", "Zaqatala", "Qəbələ"].map((c, i) => v(`7${i}`, 2, { title: `${c}da avtobus aşıb - Video` })), () => null);
  assert.equal(r.probed.length, 4);
  assert.equal(r.x, null);
});

test("seçim: one event counts once — fragments add their new sources (each site once) and reach the 4-source bar together; the event never gets a second video", async () => {
  const now = Date.parse(FX.now), opt = SV.options({});
  // Real başlıqlar (lent, 2026-11-26 18:39): eyni qəza iki qrupda. Heç biri 4 mənbəyə çatmır; birlikdə 4 sayt (APA iki dəfə — bir say).
  const a = art("f1", { title: "Xaçmazda avtomobil piyadanı vuraraq öldürüb", source: "Modern.az", sourceUrl: "https://modern.az/x1", alts: alts("APA") });
  const b = art("f2", { title: "Xaçmazda avtomobilin vurduğu piyada ölüb", source: "Nocomment.az", sourceUrl: "https://nocomment.az/x2", alts: alts("Report", "APA") });
  assert.equal(S.candidates([a, b], now, { ...opt, lang: "az" }).length, 0, "əvvəl: video yox");
  const [g] = SV.hadiseler([a, b], now, opt);
  assert.equal(g.uzv.length, 2);
  assert.equal(g.say, 4);
  // Fərqli hadisələr birləşmir (real başlıqlar): ad tək başına, ölkə adları, böyük hərfli söz və «qarşı» kökü bəs deyil.
  const ayri = (...titles) => SV.hadiseler(titles.map((t, i) => art(`8${i}`, { title: t })), now, opt).length;
  assert.equal(ayri("Bakıda yeni metro stansiyası açılıb", "Bakıda yeni məktəb açılıb"), 2);
  assert.equal(ayri("Ukrayna ordusu Hulyaipole şəhərində Rusiya qoşunlarının toplanma məntəqəsini vurub, 20-yə qədər hərbçi öldürülüb - VİDEO",
    "Rusiya Ukraynaya NATO-nun 5-ci maddəsinə bənzər təhlükəsizlik təminatlarının verilməsinə qarşıdır",
    "Almaniyada Rusiya və Ukrayna vətəndaşı Rusiya FTX-nin xeyrinə casusluq etdiyini etiraf edib"), 3);
  assert.equal(ayri("“Beşiktaş”ın İsrail klubu ilə qarşılaşmasında DAVA: oyun yarımçıq dayandırıldı- VİDEO", "İsrail azanın məhdudlaşdırılmasına qarşı çıxdı - Parlamentdə dava düşdü - Video"), 2);
  assert.equal(ayri("Xaçmazda avtomobil piyadanı vuraraq öldürüb", "Xaçmazda park əsaslı şəkildə yenidən qurularaq istifadəyə verilib"), 2);
  // Eyni hadisə: dırnaqdakı iki ad (klub) və ya qısa başlığın yarısı.
  assert.equal(ayri("\"Beşiktaş\" – \"Hapoel\" azarkeşləri arasındakı davaya görə oyun dayandırıldı", "“Beşiktaş” – “Hapoel” matçında insident yarandı - Video"), 1);
  assert.equal(ayri("“Beşiktaş”ın matçında dava düşdü", "Gürcüstanda “Beşiktaş”ın oyununda dava düşdü - Polis müdaxilə etdi"), 1);
  await withOutput(async dir => {
    const state = SV.readState("/yoxdur", now), args = t => ({ articles: [a, b], env: ENV, now: t, state, fetch: net([a, b]).f, cats: [], dir, log: () => {}, menbe: async () => null });
    const x = await SV.sec(args(now));
    assert.equal(x.id, b.id, "çox mənbəli parça");
    assert.deepEqual(x.alts.map(y => y.source).sort(), ["APA", "Modern.az", "Report"], "mənbə siyahısı hadisənindir, APA bir dəfə");
    assert.ok(state.q[a.id], "o biri parça yadda qalır");
    // 3 gün sonra da (siyahı oxunub yazılanda) eyni hadisə ikinci video olmur.
    const file = path.join(dir, "state.json");
    fs.writeFileSync(file, JSON.stringify(state));
    const back = SV.readState(file, now + 31 * 60e3);
    assert.ok(back.q[a.id]);
    assert.equal(await SV.sec({ ...args(now + 31 * 60e3), state: back }), null);
  });
});

test("seçim: night backlog — a story from the no-video night (00:00–07:59 Baku) counts its 3 hours from the 08:00 window, not from publication", async () => {
  const opt = SV.options({}), at = s => Date.parse(s);
  const MORNING = at("2026-11-27T04:17:00Z");   // Bakı 08:17
  const night = at("2026-11-26T23:00:00Z");     // Bakı 03:00
  assert.equal(SV.yasBasi(night, MORNING, opt), at("2026-11-27T04:00:00Z"), "yaş 08:00-dan");
  assert.equal(SV.yasBasi(at("2026-11-26T20:30:00Z"), MORNING, opt), at("2026-11-27T04:00:00Z"), "00:30 da gecədir");
  assert.equal(SV.yasBasi(at("2026-11-26T19:30:00Z"), MORNING, opt), at("2026-11-26T19:30:00Z"), "23:30 pəncərədədir: dərc vaxtından");
  assert.equal(SV.yasBasi(night, at("2026-11-27T03:47:00Z"), opt), night, "07:47 (önizləmə): pəncərə hələ açılmayıb");
  // VIDEO_SAAT=7-22: gecə 23:00–06:59.
  const o7 = SV.options({ VIDEO_SAAT: "7-22" });
  assert.equal(SV.yasBasi(at("2026-11-26T19:30:00Z"), at("2026-11-27T03:17:00Z"), o7), at("2026-11-27T03:00:00Z"));
  const n = art("e1", { title: "Bərdədə yük maşını aşıb, sürücü xəsarət alıb", publishedAt: new Date(night).toISOString(), alts: alts("Report", "Oxu.az", "Trend") });
  const late = art("e2", { title: "Şəkidə yanğın olub", publishedAt: "2026-11-26T19:30:00.000Z", alts: alts("Report", "Oxu.az", "Trend") });
  const ids = t => SV.hadiseler([n, late], t, opt).map(g => g.uzv[0].a.id);
  assert.equal(S.candidates([n], MORNING, { ...opt, lang: "az" }).length, 0, "əvvəl: 5 saatlıq xəbər düşürdü");
  assert.deepEqual(ids(MORNING), [n.id], "08:17: gecənin xəbəri var, axşamın xəbəri yox");
  assert.deepEqual(ids(at("2026-11-27T06:47:00Z")), [n.id], "10:47: hələ 3 saat dolmayıb");
  assert.deepEqual(ids(at("2026-11-27T07:17:00Z")), [], "11:17: 3 saat 08:00-dan doldu");
  await withOutput(async dir => {
    const x = await SV.sec({ articles: [n, late], env: ENV, now: MORNING, state: SV.readState("/yoxdur", MORNING), fetch: net([n, late]).f, cats: [], dir, log: () => {}, menbe: async () => null });
    assert.equal(x.id, n.id, "səhərin ilk pəncərəsində gecənin xəbəri");
  });
});

// Sahib, 2026-11-27: «Beşiktaşın oyunundan və videoda arxada stadion top və s göstərilir — bunun yerinə həmin oyundan kadrlar
// göstərilməlidir». Oyun xəbəri yalnız oyunun öz kadrı ilə video olur; başlığın « - Video» nişanı videoya yazılmır.
test("seçim: a sports match story without the game's own footage is not made with stock stadium/ball clips; with its own file it goes; the « - Video» tag is dropped from the title", async () => {
  const now = Date.parse(FX.now);
  const oyun = (id, o = {}) => art(id, { category: "idman", title: 'Batumidə gərgin gecə: "Beşiktaş" qalmaqallı qarşılaşmadan qalib ayrıldı - Video', alts: alts("Report", "Oxu.az", "Trend", "Qafqazinfo"), ...o });
  const run = async (articles, menbe) => withOutput(async dir => {
    const state = SV.readState("/yoxdur", now), logs = [];
    const x = await SV.sec({ articles, env: ENV, now, state, fetch: net(articles).f, cats: [], dir, log: s => logs.push(s), menbe: async a => menbe(a) });
    return { x, logs, state };
  });
  let r = await run([oyun("e1")], () => null);
  assert.equal(r.x, null);
  assert.ok(r.logs.some(s => /idman oyunu: oyunun öz kadrı tapılmadı — bank klipi \(stadion, top\) göstərilmir/.test(s)), r.logs.join(" | "));
  assert.ok(r.state.skip[oyun("e1").id], "bir də sınanmır");
  r = await run([oyun("e2")], a => mvOf(a));
  assert.equal(r.x?.id, oyun("e2").id);
  assert.ok(r.x.menbeVideo, "oyunun öz kadrı ilə gedir");
  assert.equal(r.x.title, 'Batumidə gərgin gecə: "Beşiktaş" qalmaqallı qarşılaşmadan qalib ayrıldı');
  // Oyun olmayan idman xəbəri və başqa bölmə əvvəlki kimidir.
  assert.equal(SV.oyunXeberi({ category: "idman", title: "Oyunçu «Neftçi» ilə müqaviləni uzatdı" }), false);
  assert.equal(SV.oyunXeberi({ category: "gundem", title: "Qarşılaşma 2:1 bitdi" }), false);
  assert.equal(SV.oyunXeberi({ category: "idman", title: "Avropa Liqasının V turunda «Beşiktaş» qalib gəlib" }), true);
  assert.equal(SV.oyunXeberi({ category: "idman", title: "«Qarabağ» «Çelsi» ilə 2:2" }), true);
  assert.equal(SV.nisansiz("Bakıda QƏZA - VİDEO - FOTO"), "Bakıda QƏZA");
  assert.equal(SV.nisansiz("Final - Yenilənir"), "Final");
  assert.equal(SV.nisansiz("Prezident - Ali Baş Komandan"), "Prezident - Ali Baş Komandan");
});
