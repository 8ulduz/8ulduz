// Kanal videoları (video-kanal.cjs) və xəbər səhifəsindəki Telegram pəncərəsi (video-menbe.cjs) — sahib, 2026-11-27:
// «A B ni də.. B tək oxuaz la məhdud qalmasın», «qutab bölməsi ilə razı deyiləm. Baku VS də sosil şəbəkələrdən götürüb öz komentini
// verib. Biz bunu da etməliyik». Telegram səhifələri real nümunədir (tests/fixtures/telegram-kanal.html — t.me/s/modern_azz,
// telegram-embed.html — t.me/oxuaze/201842?embed=1, 2026-11-27, qısaldılıb). Instagram cavabı Graph API Business Discovery-nin
// quruluşundadır, mətnlər uydurmadır. Şəbəkə, Gemini və ffmpeg burada işləmir.
"use strict";
const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("fs"), os = require("os"), path = require("path");

const K = require("../.github/scripts/video-kanal.cjs");
const M = require("../.github/scripts/video-menbe.cjs");
const SV = require("../.github/scripts/sosial-video.cjs");
const V = require("../.github/scripts/video-xeber.cjs");
const VS = require("../.github/scripts/video-ssenari.cjs");
const root = path.resolve(__dirname, "..");
const read = f => fs.readFileSync(path.join(root, f), "utf8");
const app = require("../.github/scripts/topics.cjs").loadApp(root);
const policy = a => app.policyViolation(a);

const NOW = Date.parse("2026-11-27T06:00:00Z");
const KANAL = read("tests/fixtures/telegram-kanal.html"), EMBED = read("tests/fixtures/telegram-embed.html");
const tmp = () => fs.mkdtempSync(path.join(os.tmpdir(), "kanal-"));
const mp4 = (n = 200e3) => { const b = Buffer.alloc(n); b.write("ftypisom", 4, "latin1"); return b; };
const ENV = { GEMINI_API_KEY: "g", VIDEO_GEMINI_WAIT_MS: "0" };

// Sınaq siyahısı: iki Telegram kanalı və iki Instagram hesabı (biri faylı yoxlanmış, biri yox).
function cfgFile(o = {}) {
  const base = JSON.parse(read(".github/video-kanal.json"));
  const j = { ...base, telegram: [{ ad: "Modern.az", kanal: "modern_azz", yoxlama: "sınaq" }, { ad: "Oxu.az", kanal: "oxuaze", yoxlama: "sınaq" }],
    instagram: [{ ad: "Baku.ws", hesab: "baku.ws_official", fayl: true, yoxlama: "sınaq" }, { ad: "Axar.az", hesab: "axar.az", fayl: null, yoxlama: "sınaq" }], ...o };
  const f = path.join(tmp(), "video-kanal.json");
  fs.writeFileSync(f, JSON.stringify(j));
  return f;
}

// Gemini və Telegram/Instagram sınaq şəbəkəsi. yaz: başlıq+mətn (və ya funksiya: prompt → cavab, null — Gemini cavab vermir).
const BESIKTAS = { uygun: true, basliq: "Beşiktaş azarkeşləri ilə polis arasında toqquşma oyunu dayandırdı",
  text: "Gürcüstanda keçirilən UEFA Avropa Liqası oyununda «Beşiktaş» ilə «Hapoel Beer-Şeva» arasındakı matç yarımçıq dayandırılıb. «Beşiktaş»ın azarkeşləri tribunada Fələstin bayrağı açıblar. Bundan sonra polis tribunaya müdaxilə edib və azarkeşlərlə polis arasında toqquşma yaşanıb.",
  etiket: ["Beşiktaş", "futbol", "UEFA"] };
const QUTAB_CAP = "Bakının mərkəzindəki kiçik restoranda qutabı ana və qızı birlikdə bişirirlər.\nRestoranın sahibi deyir ki, xəmiri hər səhər əl ilə yoğururlar, içliyi isə təzə göyərtidən hazırlayırlar.\nGörüntülər sosial şəbəkələrdə geniş yayılıb.\n📹 @foto_by_gunew\n#qutab #baku";
const QUTAB = { uygun: true, basliq: "Bakıda ana və qızın sevgi ilə bişirdiyi qutab sosial şəbəkələrdə yayılıb",
  text: "Bakının mərkəzindəki kiçik restoranda qutabı ana və qızı birlikdə bişirirlər. Restoranın sahibi bildirib ki, xəmiri hər səhər əl ilə yoğururlar. Qutabın içliyi təzə göyərtidən hazırlanır. Bu görüntülər sosial şəbəkələrdə geniş yayılıb.",
  etiket: ["qutab", "Bakı", "mətbəx"] };
const reel = (id, o = {}) => ({ id, caption: QUTAB_CAP, media_product_type: "REELS", media_type: "VIDEO", media_url: `https://scontent.cdninstagram.com/v/${id}.mp4?efg=x`,
  permalink: `https://www.instagram.com/reel/R${id}/`, timestamp: "2026-11-27T02:00:00+0000", like_count: 900, comments_count: 40, view_count: 47000, ...o });
const IG = { "baku.ws_official": { business_discovery: { username: "baku.ws_official", followers_count: 900000, media: { data: [
  reel("1801"), reel("1802", { media_url: undefined, view_count: 900000 }), reel("1803", { timestamp: "2026-11-24T02:00:00+0000" }),
  reel("1804", { caption: "Prezident İlham Əliyev Litva Respublikasının xarici işlər nazirini qəbul edib. Görüşdə iki ölkə arasında əməkdaşlığın genişləndirilməsi, nəqliyyat və enerji layihələri müzakirə olunub. Tərəflər gələcək təmaslar barədə də fikir mübadiləsi aparıblar.", view_count: 500000 }),
  { id: "1805", caption: "Şəkil", media_product_type: "FEED", media_type: "IMAGE", media_url: "https://scontent.cdninstagram.com/v/1805.jpg", timestamp: "2026-11-27T03:00:00+0000" }] } } },
  "axar.az": { error: { message: "Invalid OAuth access token - EAAsinaqTOKEN1234567890 is not valid", code: 190 } } };
function net({ yaz = () => BESIKTAS, s = { "modern_azz": KANAL }, ig = IG, seen = { asked: [], prompts: [] } } = {}) {
  return async (url, o = {}) => {
    seen.asked.push(url);
    if (/models\?pageSize/.test(url)) return { ok: true, json: async () => ({ models: [] }) };
    if (/generativelanguage/.test(url)) {
      const p = JSON.parse(o.body).contents[0].parts[0].text;
      seen.prompts.push(p);
      const j = yaz(p);
      return j == null ? { ok: false, status: 400, json: async () => ({}) } : { ok: true, status: 200, json: async () => ({ candidates: [{ content: { parts: [{ text: JSON.stringify(j) }] } }] }) };
    }
    const tg = url.match(/^https:\/\/t\.me\/s\/([A-Za-z0-9_]+)$/);
    if (tg) return s[tg[1]] ? { ok: true, status: 200, text: async () => s[tg[1]] } : { ok: false, status: 404, text: async () => "" };
    if (url.startsWith("https://graph.facebook.com/")) {
      const u = new URL(url), h = (u.searchParams.get("fields").match(/business_discovery\.username\(([^)]+)\)/) || [])[1];
      return { ok: true, json: async () => ig[h] || { error: { message: "not found", code: 100 } } };
    }
    if (url === "https://t.me/oxuaze/201842?embed=1&mode=tme") return { ok: true, status: 200, text: async () => EMBED };
    return { ok: false, status: 404, text: async () => "" };
  };
}
const indir = got => async (u, f, _f, ref) => { got.push([u, ref]); fs.writeFileSync(f, mp4()); return ""; };

test("kanal: Telegram — the public channel page and the embed page are read into the same posts (real pages, 2026-11-27)", () => {
  const k = K.tgKanal(KANAL);
  assert.deepEqual([k.ad, k.kanal], ["Modern.az", "modern_azz"]);
  assert.match(k.tesvir, /Website: modern\.az/);
  assert.deepEqual(k.postlar.map(p => [p.post, Boolean(p.video), p.dur, p.baxis]), [["modern_azz/95487", false, 0, 150], ["modern_azz/95488", true, 31, 136], ["modern_azz/95490", true, 96, 71]]);
  const b = k.postlar[1];
  assert.equal(b.video, "https://cdn4.telesco.pe/file/660fe4f5ea.mp4?token=sinaq", "albomda birinci video");
  assert.equal(b.at, Date.parse("2026-11-26T18:45:11Z"));
  assert.equal(b.link, "https://t.me/modern_azz/95488");
  assert.equal(K.metnTemiz(b.text), "\"Beşiktaş\" - \"Hapoel Beer-Şeva\" matçı yarımçıq dayandırıldı: Polislə azarkeşlər arasında toqquşma\nUEFA Avropa Liqası çərçivəsində İsrailin \"Hapoel Beer-Şeva\" komandasını Gürcüstanda qəbul edən \"Beşiktaş\"ın azarkeşləri tribunada Fələstin bayrağı açıblar. Bundan sonra polis müdaxilə edib.");
  const e = K.tgPostlar(EMBED);
  assert.deepEqual(e.map(p => [p.post, p.ad, p.video, p.dur, p.baxis]), [["oxuaze/201842", "Oxu.Az", "https://cdn4.telesco.pe/file/959d57012c.mp4?token=sinaq", 29, 1590]]);
  // Böyük faylın postunda («Media is too big») video yoxdur; yönləndirilən post tanınır.
  const big = EMBED.replace(/<video[^>]*><\/video>/, "").replace("tgme_widget_message_author", "tgme_widget_message_forwarded_from accent_color\">Forwarded from <a class=\"tgme_widget_message_forwarded_from_name\" href=\"https://t.me/meydantv\"><span dir=\"auto\">Meydan TV</span></a></div><div class=\"tgme_widget_message_author");
  assert.deepEqual([K.tgPostlar(big)[0].video, K.tgPostlar(big)[0].fwd], ["", { ad: "Meydan TV", kanal: "meydantv" }]);
  assert.deepEqual(["1.59K", "2.1M", "136", "", "x"].map(K.sayi), [1590, 2100000, 136, 0, 0]);
  assert.deepEqual(["0:29", "1:36", "1:02:03", ""].map(K.muddet), [29, 96, 3723, 0]);
  // Mətnin təmizlənməsi: keçid, emoji, heşteq, kanalın çağırış sətirləri.
  assert.equal(K.metnTemiz("🔴 Dağıstanlı pəhləvan rekord qırdı\n\n🔗 Son xəbərlər ℹ Bizimlə əlaqə\nƏtraflı: https://oxu.az/x\n#rekord #idman\n🌍 Haqqin.az"), "Dağıstanlı pəhləvan rekord qırdı");
});

test("kanal: only verified channels of listed sources — the site still has to be named on the channel; opposition names and unlisted sites are dropped", () => {
  const L = K.menbeler();
  const Q = K.qayda();
  assert.ok(L.telegram.length >= 20 && L.instagram.length >= 3, `${L.telegram.length} / ${L.instagram.length}`);
  assert.deepEqual(L.atilan, []);
  for (const m of [...L.telegram, ...L.instagram]) {
    assert.ok(Q.azSources[m.ad], `${m.ad}: azSources`);
    assert.equal(m.sayt, `https://${Q.azSources[m.ad][0]}/`);
    assert.equal(policy({ title: "Neytral", source: m.ad, sourceUrl: m.sayt }), false, m.ad);
  }
  // Koordinatorun sınağı: faylı açıq hesablar; yükləməsi bağlı hesablar söndürülüb. Patrul.az, Maraqli.tv, Baku.es siyahıya sahibin
  // sözü ilə düşüb (2026-11-27: «Yenə əlavə et») — azSources-dadır, hər birinin Telegram kanalı və Instagram hesabı var.
  assert.deepEqual(L.instagram.filter(m => m.fayl === true).map(m => m.hesab), ["baku.ws_official", "oxuaz", "qafqazinfo_az", "patrul.az", "maraqli.tv", "baku.es"]);
  const hamisi = JSON.parse(read(".github/video-kanal.json"));
  assert.ok(hamisi.instagram.filter(m => ["report.az", "baku.tv"].includes(m.hesab)).every(m => m.aktiv === false));
  for (const ad of ["Patrul.az", "Maraqli.tv", "Baku.es"]) {
    assert.ok(Q.azSources[ad], `${ad}: azSources`);
    assert.ok(L.telegram.some(m => m.ad === ad) && L.instagram.some(m => m.ad === ad), ad);
    assert.ok([...hamisi.telegram, ...hamisi.instagram].filter(m => m.ad === ad).every(m => /sahib 2026-11-27 \(«Yenə əlavə et»\)/.test(m.yoxlama)), `${ad}: sahibin qərarı yazılıb`);
  }
  // Siyahıda olmayan sayt, müxalifət adı və yoxlamasız sətir atılır.
  const f = cfgFile({ telegram: [{ ad: "Namelum.az", kanal: "namelumaz", yoxlama: "x" }, { ad: "Oxu.az", kanal: "meydan_tv", yoxlama: "x" }, { ad: "Oxu.az", kanal: "oxuaze" }],
    instagram: [{ ad: "Baku.ws", hesab: "toplum.tv", yoxlama: "x" }] });
  const X = K.menbeler(f);
  assert.deepEqual([X.telegram, X.instagram], [[], []]);
  assert.equal(X.atilan.length, 4);
  // İşləyərkən: kanalın başlığı və ya təsviri saytı yazmalıdır.
  const mod = { ad: "Modern.az", kanal: "modern_azz", domen: "modern.az" };
  assert.equal(K.bizimdir(K.tgKanal(KANAL), mod), true);
  assert.equal(K.bizimdir({ ...K.tgKanal(KANAL), ad: "Kripto siqnalları", tesvir: "Gəlir qazanın" }, mod), false, "kanal satılıb");
  assert.equal(K.bizimdir(K.tgKanal(KANAL), { ...mod, kanal: "oxuaze" }), false, "başqa kanal");
});

test("qırmızı xətt 2: opposition channels, accounts, authors and opposition outlets named as the source are refused; ordinary words are not", () => {
  for (const n of ["meydantv", "Meydan TV", "Azadlıq Radiosu", "radioazadliq", "toplum_tv", "abzasmedia", "mikroskop_media", "turan_agency", "Musavat.com", "OCCRP"]) assert.ok(K.muxalifet(n), n);
  for (const n of ["oxuaze", "Oxu.Az", "baku.ws_official", "qafqazinfo", "foto_by_gunew", "@modern_azz"]) assert.equal(K.muxalifet(n), "", n);
  assert.ok(K.kokler().includes("meydan") && K.kokler().includes("mikroskop"), "bağlı saytların kökləri");
  assert.equal(K.muxalifetMetn("Azadlıq meydanında parad keçirilib, «Turan-Tovuz» qələbə qazanıb, toplum həyatı"), "");
  for (const t of ["Mənbə: Meydan TV", "Abzas Media-nın yaydığı video", "Görüntü: t.me/abzasmedia", "@meydantv paylaşıb", "turan.az yazır"]) assert.ok(K.muxalifetMetn(t), t);
});

test("mənbə videosu: a Telegram post inside the story — widget, frame or link — gives the footage when the site has no file of its own; credit «<Kanal> (Telegram)»", async () => {
  const head = `<html><head><meta property="og:title" content="Beşiktaşın oyunu yarımçıq dayandırıldı"></head><body><h1>Beşiktaşın oyunu yarımçıq dayandırıldı</h1>`;
  const a = { id: "t1".padEnd(16, "0"), title: "Beşiktaşın oyunu yarımçıq dayandırıldı", source: "Oxu.az", sourceUrl: "https://oxu.az/idman/1", alts: [] };
  // Üç yerləşdirmə yolu, saytın hər səhifəsində olan kanal keçidi (post deyil) və sonrakı xəbərin postu (xəbərin hissəsi deyil).
  assert.deepEqual(M.telegramlar(`<script async src="https://telegram.org/js/telegram-widget.js?22" data-telegram-post="oxuaze/201842" data-width="100%"></script>`), ["oxuaze/201842"]);
  assert.deepEqual(M.telegramlar(`<iframe src="https://t.me/oxuaze/201842?embed=1&amp;mode=tme"></iframe><a href="https://t.me/oxuaze">Kanal</a><a href="https://t.me/s/oxuaze/5">s</a><a href="https://t.me/joinchat/abc/1">j</a>`), ["oxuaze/201842"]);
  assert.deepEqual(M.telegramlar(`<p>Video: <a href="https://t.me/bakupost/27991">t.me/bakupost/27991</a></p><a href="https://t.me/x1/1">a</a><a href="https://t.me/yyyy/2">b</a><a href="https://t.me/zzzz/3">c</a>`), ["bakupost/27991", "yyyy/2"]);
  const got = [], logs = [];
  const f = net();
  const page = `${head}<p>Matç dayandırılıb.</p><script data-telegram-post="oxuaze/201842"></script><h1>Başqa xəbər</h1><script data-telegram-post="oxuaze/1"></script></body></html>`;
  const files = new Map();
  const g = async (url, o) => (url === "https://oxu.az/" ? { ok: true, text: async () => "" } : url === "https://cdn4.telesco.pe/file/959d57012c.mp4?token=sinaq" ? (files.set(url, 1), { ok: true, status: 200, headers: { get: () => "200000" }, arrayBuffer: async () => mp4() }) : f(url, o));
  const dir = tmp();
  const r = await M.menbeVideo(a, page, { env: {}, fetch: g, log: s => logs.push(s), dir });
  assert.deepEqual({ ...r, bytes: 0 }, { file: "klip-menbe.mp4", url: "https://cdn4.telesco.pe/file/959d57012c.mp4?token=sinaq", sehife: "https://t.me/oxuaze/201842", kredit: "Oxu.az (Telegram)", telegram: "oxuaze/201842", bytes: 0 });
  assert.ok(fs.existsSync(path.join(dir, M.FAYL)) && files.size === 1);
  // Saytın öz faylı varsa Telegram oxunmur.
  const own = await M.menbeVideo(a, `${head}<video src="https://oxu.az/v/1.mp4"></video><script data-telegram-post="oxuaze/201842"></script>`,
    { env: {}, fetch: async (url, o) => (url === "https://oxu.az/v/1.mp4" ? { ok: true, status: 200, headers: { get: () => "200000" }, arrayBuffer: async () => mp4() } : g(url, o)), log: () => {}, dir: tmp() });
  assert.equal(own.url, "https://oxu.az/v/1.mp4");
  // Başqa kanalın postu (Bakupost başqa kanalı yerləşdirmişdi): kanalın başlığı ilə; müəllif varsa o da.
  const other = EMBED.replace(/oxuaze/g, "bakuxeberleri").replace("Oxu.Az", "Bakı Xəbərləri").replace("toqquşma</b>", "toqquşma</b><br/>📹 @foto_by_gunew");
  const h = async (url, o) => (url === "https://t.me/bakuxeberleri/201842?embed=1&mode=tme" ? { ok: true, status: 200, text: async () => other } : g(url, o));
  const r2 = await K.tgEmbed("bakuxeberleri/201842", { fetch: h, log: () => {}, dir: tmp(), deps: { indir: indir([]) } });
  assert.equal(r2.kredit, "Bakı Xəbərləri (Telegram), @foto_by_gunew");
});

test("qırmızı xətt 2: a Telegram post from an opposition channel, forwarded from one, or citing one is refused; an unlisted channel's post about the leadership is refused too", async () => {
  const embed = (o = {}) => async url => ({ ok: true, status: 200, text: async () => (o.html || EMBED).replace(/oxuaze/g, o.kanal || "oxuaze").replace("Oxu.Az", o.ad || "Oxu.Az")
    .replace("toqquşma</b>", `toqquşma</b>${o.metn || ""}`) });
  const yoxla = async (o, post) => { const logs = [], got = []; const r = await K.tgEmbed(post || `${o.kanal || "oxuaze"}/201842`, { fetch: embed(o), log: s => logs.push(s), dir: tmp(), deps: { indir: indir(got) } }); return { r, logs: logs.join(" | "), got }; };
  let x = await yoxla({ kanal: "meydantv", ad: "Meydan TV" });
  assert.equal(x.r, null); assert.match(x.logs, /müxalifət kanalı və ya mənbəsi \(meydan\)/); assert.deepEqual(x.got, [], "fayl yüklənmir");
  x = await yoxla({ kanal: "bakuxeber", ad: "Bakı xəbər", metn: "<br/>Mənbə: Abzas Media" });
  assert.equal(x.r, null); assert.match(x.logs, /abzas media/);
  x = await yoxla({ html: EMBED.replace("tgme_widget_message_author", "tgme_widget_message_forwarded_from\">Forwarded from <a href=\"https://t.me/toplumtv\"><span dir=\"auto\">Toplum TV</span></a></div><div class=\"tgme_widget_message_author") });
  assert.equal(x.r, null); assert.match(x.logs, /toplum/);
  // Siyahıda olmayan kanal, mətndə rəhbərlik: götürülmür. Siyahıdakı saytın kanalı (Oxu.az) eyni mətnlə: götürülür.
  x = await yoxla({ kanal: "bakuxeber", ad: "Bakı xəbər", metn: "<br/>Prezident İlham Əliyev tədbirdə iştirak edib." });
  assert.equal(x.r, null); assert.match(x.logs, /siyahıda olmayan kanal, mətndə rəhbərlik/);
  x = await yoxla({ metn: "<br/>Prezident İlham Əliyev tədbirdə iştirak edib." });
  assert.equal(x.r?.kredit, "Oxu.az (Telegram)");
  // Videosuz post və oxunmayan post.
  x = await yoxla({ html: EMBED.replace(/<video[^>]*><\/video>/, "") });
  assert.equal(x.r, null); assert.match(x.logs, /götürülə bilən video yoxdur/);
  assert.equal(await K.tgEmbed("yoxdur/1", { fetch: async () => ({ ok: false, status: 404 }), log: () => {}, dir: tmp() }), null);
  assert.equal(await K.tgEmbed("../x/1", { fetch: async () => { throw new Error("soruşulmamalı"); }, log: () => {}, dir: tmp() }), null);
});

test("mənbə videosu: Lent.az and APA are one media group (APA Media Group, proven on both sites) — Lent.az's cdn.apa.az file is its own; other sites stay foreign", () => {
  assert.deepEqual(M.QRUP, [["apa.az", "lent.az"]]);
  assert.equal(M.ozunku("https://cdn.apa.az/storage/apa.az/video-cdn/cb8b33f561ba0baaffb5e43d5ea4b62d.mp4", "https://lent.az/xeber/idman/besiktas-1"), true);
  assert.equal(M.ozunku("https://cdn.lent.az/v/1.mp4", "https://apa.az/idman/1"), true);
  assert.equal(M.ozunku("https://cdn.apa.az/v/1.mp4", "https://oxu.az/idman/1"), false);
  assert.equal(M.ozunku("https://www.trthaber.com/v/x.mp4", "https://lent.az/x"), false);
  assert.match(read(".github/scripts/video-menbe.cjs"), /APA Media Group-un tərkibində fəaliyyət göstərən Lent\.az/, "sübut kodun yanında");
});

test("kanal: the voice text is written from the post's own text only — numbers must be in it, three sentences at least, the site rule and the opposition rule apply", async () => {
  const k = K.tgKanal(KANAL), m = { ad: "Modern.az", kanal: "modern_azz", domen: "modern.az", sayt: "https://modern.az/" };
  const c = K.tgNamized(k.postlar[1], m);
  const seen = { asked: [], prompts: [] };
  const yaz = j => ({ env: ENV, fetch: net({ yaz: () => j, seen }), policy, log: () => {} });
  const s = await K.metnYaz(c, yaz(BESIKTAS));
  assert.deepEqual(s, { title: BESIKTAS.basliq, text: BESIKTAS.text, etiket: ["Beşiktaş", "futbol", "UEFA"] });
  const p = seen.prompts[0];
  assert.match(p, /Modern\.az xəbər saytının Telegram/); assert.match(p, /Yalnız paylaşımın mətnindəki faktlar/); assert.match(p, /3–5 cümlə/);
  assert.match(p, /Paylaşım \(Modern\.az, Telegram\): "Beşiktaş" - "Hapoel Beer-Şeva" matçı/);
  const red = async (j, re) => { const r = await K.metnYaz(c, yaz(j)); assert.ok(r.yox && re.test(r.yox), JSON.stringify(r)); };
  await red({ ...BESIKTAS, text: `${BESIKTAS.text} Polis 15 azarkeşi saxlayıb.` }, /mənbədə olmayan rəqəm: 15/);
  await red({ ...BESIKTAS, text: "Gürcüstanda «Beşiktaş» ilə «Hapoel Beer-Şeva» arasındakı matç yarımçıq dayandırılıb və bundan sonra polis tribunaya müdaxilə edib, toqquşma yaşanıb. Azarkeşlər tribunada Fələstin bayrağı açıblar." }, /cümlə sayı 2|şərh azdır/);
  await red({ ...BESIKTAS, text: `${BESIKTAS.text} Görüntünü Meydan TV yayıb.` }, /müxalifət/);
  await red({ ...BESIKTAS, basliq: "Qısa" }, /başlıq 4 simvol/);
  await red({ ...BESIKTAS, text: `${BESIKTAS.text} Ətraflı @modern_azz kanalında.` }, /@hesab/);
  await red({ uygun: false }, /şərh olmur/);
  await red({ ...BESIKTAS, text: BESIKTAS.text.replace("toqquşma yaşanıb", "döyüş olub") }, /müharibə və ya zorakılıq/);
  // Açar yoxdur və ya Gemini cavab vermir — indi yazılmır, heç nə «yanmır».
  assert.deepEqual(await K.metnYaz(c, { ...yaz(BESIKTAS), env: {} }), { gec: "GEMINI_API_KEY yoxdur" });
  assert.deepEqual(await K.metnYaz(c, yaz(null)), { gec: "Gemini cavab vermir" });
  assert.deepEqual(VS.SERH_MIN, { cumle: 3, simvol: 180 }, "şərh həddi (2026-11-27)");
  assert.deepEqual(K.HED, { min: 180, max: 650, sentMin: 3, sentMax: 6 });
});

test("kanal: the credit names the outlet and the platform, plus the original author when the post credits one; a person merely mentioned is not an author", () => {
  assert.equal(K.muellifOf(QUTAB_CAP, ["baku.ws_official"]), "@foto_by_gunew");
  assert.equal(K.muellifOf("Video: @baku.ws_official", ["baku.ws_official"]), "", "hesabın özü");
  assert.equal(K.muellifOf("Futbolçu @cristiano qol vurdu, stadion ayağa qalxdı"), "", "mətnin içində adı çəkilən");
  assert.equal(K.muellifOf("Hadisə yerindən görüntü\n@sakin_cekib\n"), "@sakin_cekib", "ayrıca sətirdə");
  assert.equal(K.muellifOf("Əlaqə: info@bakupost.az, @haqbot1 vasitəsilə"), "", "e-poçt və bot");
  assert.equal(K.muellifOf("Görüntü: Əli Məmmədov\nHadisə dünən baş verib"), "Əli Məmmədov");
  assert.equal(K.muellifOf("Kəpəz\nMüəllif: Osman Sarıvəlli\nİfa: Zəlimxan Yaqub"), "", "şeirin müəllifi görüntünün sahibi deyil (Kulis.az, 2026-11-27)");
  assert.equal(K.kredit("Oxu.az", "telegram"), "Oxu.az (Telegram)");
  assert.equal(K.kredit("Baku.ws", "instagram", "@foto_by_gunew"), "Baku.ws (Instagram), @foto_by_gunew");
});

test("kanal: Telegram — the channel's recent videos with enough text, ranked by views per hour × the strong directions; the chosen post is written, downloaded and credited", async () => {
  const file = cfgFile(), state = SV.readState("/yoxdur", NOW), got = [], logs = [], seen = { asked: [], prompts: [] };
  const x = await K.hazirla({ now: NOW, state, env: { ...ENV, INSTAGRAM_VIDEO: "0" }, fetch: net({ seen }), policy, dir: tmp(), log: s => logs.push(s), file, deps: { indir: indir(got) } });
  assert.deepEqual({ tur: x.tur, kind: x.kind, platforma: x.platforma, source: x.source, sourceUrl: x.sourceUrl, sayt: x.sayt, title: x.title, kredit: x.menbeVideo.kredit, klip_boyu: x.klip_boyu },
    { tur: "kanal", kind: "kanal", platforma: "telegram", source: "Modern.az", sourceUrl: "https://t.me/modern_azz/95488", sayt: "https://modern.az/", title: BESIKTAS.basliq, kredit: "Modern.az (Telegram)", klip_boyu: 30 });
  assert.equal(x.text, BESIKTAS.text);
  assert.deepEqual(got, [["https://cdn4.telesco.pe/file/660fe4f5ea.mp4?token=sinaq", "https://t.me/"]], "yalnız seçilənin faylı");
  // Qısa mətnli video (95490, ~150 simvol) bir də sınanmır; mətnsiz post (95487) namizəd deyil; oxunmayan kanal (oxuaze) jurnalda.
  assert.ok(state.skip[K.tgNamized(K.tgKanal(KANAL).postlar[2], { kanal: "modern_azz" }).id]);
  assert.ok(logs.some(s => /t\.me\/s\/oxuaze oxunmadı/.test(s)), logs.join(" | "));
  assert.ok(state.km["tg:modern_azz"] && state.km["tg:oxuaze"], "növbə");
  assert.ok(!seen.asked.some(u => u.startsWith("https://graph.facebook.com/")), "Instagram söndürülüb — sorğu yoxdur");
  // Köhnə video (12 saatdan çox) götürülmür; artıq işlənmiş video bir də getmir.
  assert.equal(await K.hazirla({ now: NOW + 3 * 3600e3, state: SV.readState("/yoxdur", NOW), env: { ...ENV, INSTAGRAM_VIDEO: "0" }, fetch: net(), policy, dir: tmp(), log: () => {}, file, deps: { indir: indir([]) } }), null);
  const s2 = SV.readState("/yoxdur", NOW); s2.tv = { [x.id]: NOW / 1000 - 99 * 60 };
  assert.equal(await K.hazirla({ now: NOW, state: s2, env: { ...ENV, INSTAGRAM_VIDEO: "0" }, fetch: net(), policy, dir: tmp(), log: () => {}, file, deps: { indir: indir([]) } }), null);
  // Gemini cavab vermir: heç nə götürülmür, heç nə «yanmır».
  const s3 = SV.readState("/yoxdur", NOW), g3 = [];
  assert.equal(await K.hazirla({ now: NOW, state: s3, env: { ...ENV, INSTAGRAM_VIDEO: "0" }, fetch: net({ yaz: () => null }), policy, dir: tmp(), log: () => {}, file, deps: { indir: indir(g3) } }), null);
  assert.deepEqual([g3, Object.keys(s3.skip).filter(k => k === x.id)], [[], []]);
  // Eyni hadisənin videosu son günlərdə paylaşılıbsa (mövzu siyahısı) götürülmür.
  const s4 = SV.readState("/yoxdur", NOW);
  // (paylaşılmış kanal videosunun mövzusu — sosial-video.cjs paylas onu mətnin özü ilə yazır)
  const metn = K.metnTemiz(K.tgKanal(KANAL).postlar[1].text);
  s4.topics.push({ ...require("../.github/scripts/social.cjs").topicOf({ title: metn.split("\n")[0], summary: metn }, NOW / 1000 - 3600), posted: NOW / 1000 - 3600 });
  assert.equal(await K.hazirla({ now: NOW, state: s4, env: { ...ENV, INSTAGRAM_VIDEO: "0" }, fetch: net(), policy, dir: tmp(), log: () => {}, file, deps: { indir: indir([]) } }), null);
  // Saytdakı eyni xəbər tapılır — keçid ona.
  const art = { id: "abcdef0123456789", title: "\"Beşiktaş\" - \"Hapoel Beer-Şeva\" matçı yarımçıq dayandırıldı", source: "Modern.az", sourceUrl: "https://modern.az/x", publishedAt: "2026-11-26T18:40:00Z" };
  const y = await K.hazirla({ now: NOW, state: SV.readState("/yoxdur", NOW), env: { ...ENV, INSTAGRAM_VIDEO: "0" }, fetch: net(), policy, dir: tmp(), log: () => {}, file, articles: [art, { ...art, id: "0000000000000001", source: "Oxu.az" }], deps: { indir: indir([]) } });
  assert.deepEqual([y.link, y.xeber], ["https://www.8ulduz.az/abcdef0123456789?h=26112618", art.id]);
});

test("kanal: the filter — only the video's language, no protocol, war, film or animal-only post, no repeat; official events rank lower, the strong directions higher", () => {
  const m = { ad: "Oxu.az", kanal: "oxuaze", domen: "oxu.az", sayt: "https://oxu.az/" }, o = K.options({}).telegram, state = { skip: {}, v: {}, tv: {}, topics: [] };
  const c = (text, x = {}) => ({ id: "c", platforma: "telegram", m, link: "https://t.me/oxuaze/1", video: "https://cdn4.telesco.pe/file/a.mp4", at: NOW - 3600e3, baxis: 1000, dur: 30, fwd: null, esli: text, metn: K.metnTemiz(text), muellif: "", ...x });
  const LONG = " Hadisə yerinə polis və təcili yardım əməkdaşları cəlb olunub, ərazidə nəqliyyatın hərəkəti müvəqqəti dayandırılıb. Faktla bağlı araşdırma aparılır.";
  const suz = x => K.suz(x, { now: NOW, o, state, policy });
  assert.deepEqual(suz(c(`Bakının Xətai rayonunda iki avtomobil toqquşub.${LONG}`)), {});
  assert.match(suz(c(`В Баку столкнулись два автомобиля, движение было временно остановлено полицией, ведётся расследование произошедшего на месте.${" Подробности уточняются.".repeat(3)}`)).yox, /dilində deyil/);
  assert.match(suz(c(`Nazir Litva Respublikasının xarici işlər nazirini qəbul edib.${LONG}`)).yox, /protokol/);
  assert.match(suz(c(`Cəbhə xəttində döyüş gedir, kəndlər atəşə tutulub.${LONG}`)).yox, /müharibə/);
  assert.match(suz(c(`Bakının Xətai rayonunda iki avtomobil toqquşub.${LONG}`, { dur: 2 })).yox, /video 2 s/);
  assert.equal(suz(c(`Bakının Xətai rayonunda iki avtomobil toqquşub.${LONG}`, { at: NOW - 13 * 3600e3 })).bos, "köhnədir");
  assert.match(suz(c(`Bakının Xətai rayonunda iki avtomobil toqquşub.${LONG}`, { fwd: { ad: "", kanal: "" } })).yox, /yönləndirilib/);
  assert.match(suz(c(`Bakının Xətai rayonunda iki avtomobil toqquşub.${LONG}\nMənbə: Meydan TV`)).yox, /müxalifət/);
  assert.match(suz(c(`Bakının Xətai rayonunda iki avtomobil toqquşub.${LONG}`, { muellif: "@meydantv" })).yox, /müxalifət/);
  assert.match(suz(c(`Bakının Xətai rayonunda iki avtomobil toqquşub.${LONG}`, { m: { ...m, ad: "Namelum.az", sayt: "https://namelum.az/" } })).yox, /qaydasından keçmir/);
  // Sıra: eyni baxış sürətində qəza (güclü istiqamət) önə, forum (rəsmi tədbir) geriyə keçir.
  const qeza = K.bal(c(`Bakıda yol qəzası olub, iki avtomobil toqquşub.${LONG}`), NOW), forum = K.bal(c(`Bakıda beynəlxalq forum keçirilir, iştirakçılar toplaşıb.${LONG}`), NOW);
  assert.ok(qeza > 1000 && forum < 1000, `${qeza} / ${forum}`);
});

test("kanal: Instagram — Business Discovery with our key; only reels with a file, fresh, not protocol; ranked by views per hour; the key never reaches the log", async () => {
  const file = cfgFile(), state = SV.readState("/yoxdur", NOW), got = [], logs = [], seen = { asked: [], prompts: [] };
  const env = { ...ENV, TELEGRAM_VIDEO: "0", FB_PAGE_TOKEN: "EAAsinaqTOKEN1234567890", IG_USER_ID: "17841400000000000" };
  const x = await K.hazirla({ now: NOW, state, env, fetch: net({ yaz: () => QUTAB, seen }), policy, dir: tmp(), log: s => logs.push(s), file, deps: { indir: indir(got) } });
  assert.deepEqual({ platforma: x.platforma, source: x.source, sourceUrl: x.sourceUrl, kredit: x.menbeVideo.kredit, muellif: x.muellif, title: x.title },
    { platforma: "instagram", source: "Baku.ws", sourceUrl: "https://www.instagram.com/reel/R1801/", kredit: "Baku.ws (Instagram), @foto_by_gunew", muellif: "@foto_by_gunew", title: QUTAB.basliq });
  assert.deepEqual(got, [["https://scontent.cdninstagram.com/v/1801.mp4?efg=x", "https://www.instagram.com/"]]);
  // Sorğu: bizim hesabın nömrəsi, Business Discovery sahələri, açar ünvanda (Graph API) — jurnalda isə yoxdur.
  const q = seen.asked.filter(u => u.startsWith("https://graph.facebook.com/"));
  assert.equal(q.length, 2, "faylı yoxlanmış hesab + növbədəki bir hesab");
  const u = new URL(q[0]);
  assert.equal(u.pathname, "/v27.0/17841400000000000");
  assert.equal(u.searchParams.get("fields"), "business_discovery.username(baku.ws_official){username,followers_count,media.limit(12){id,caption,media_product_type,media_type,media_url,permalink,timestamp,like_count,comments_count,view_count}}");
  assert.ok(!logs.join("\n").includes("EAAsinaqTOKEN1234567890"), "açar jurnalda yoxdur");
  assert.ok(logs.some(s => /Instagram @axar\.az oxunmadı — Invalid OAuth access token - \*\*\* is not valid \(#190\)/.test(s)), logs.join(" | "));
  assert.ok(logs.some(s => /@baku\.ws_official — 4 video, 3-i faylla/.test(s)));
  // Faylsız (900 min baxış), köhnə (3 gün) və protokol (Prezident qəbul edib) Reels seçilmədi; protokol bir də sınanmır.
  assert.ok(state.skip[K.igNamized(reel("1804"), { hesab: "baku.ws_official" }).id]);
  assert.ok(state.km["ig:baku.ws_official"] && state.km["ig:axar.az"]);
  // Sorğu həddi (#4): o dövrədə Instagram-a bir də sorğu yoxdur. Açar yoxdursa sorğu da yoxdur.
  const s2 = SV.readState("/yoxdur", NOW), seen2 = { asked: [], prompts: [] };
  await K.hazirla({ now: NOW, state: s2, env, fetch: net({ ig: { "baku.ws_official": { error: { message: "Application request limit reached", code: 4 } } }, seen: seen2 }), policy, dir: tmp(), log: () => {}, file, deps: { indir: indir([]) } });
  assert.equal(seen2.asked.filter(u2 => u2.startsWith("https://graph.facebook.com/")).length, 1);
  const seen3 = { asked: [], prompts: [] }, l3 = [];
  assert.equal(await K.hazirla({ now: NOW, state: SV.readState("/yoxdur", NOW), env: { ...ENV, TELEGRAM_VIDEO: "0" }, fetch: net({ seen: seen3 }), policy, dir: tmp(), log: s => l3.push(s), file }), null);
  assert.ok(!seen3.asked.length && l3.some(s => /FB_PAGE_TOKEN yoxdur/.test(s)));
  // IG_USER_ID yoxdursa səhifənin instagram_business_account-u.
  const pg = [];
  assert.equal(await K.igHesab({ FB_PAGE_ID: "1470", FB_PAGE_TOKEN: "t" }, async url => { pg.push(url); return { ok: true, json: async () => ({ instagram_business_account: { id: "1784" } }) }; }), "1784");
  assert.match(pg[0], /^https:\/\/graph\.facebook\.com\/v27\.0\/1470\?fields=instagram_business_account&access_token=t$/);
  assert.equal(K.gizle("x EAAsinaqTOKEN1234567890 y", { FB_PAGE_TOKEN: "EAAsinaqTOKEN1234567890" }), "x *** y");
});

test("kanal: its own pace per platform, counted in the daily 30 and the common gap; TELEGRAM_VIDEO=0 / INSTAGRAM_VIDEO=0 switch it off; VIDEO_TUR=kanal runs it now", async () => {
  assert.deepEqual(K.options({}), { telegram: { on: true, perDay: 6, gapMin: 90, maxAgeH: 12 }, instagram: { on: true, perDay: 6, gapMin: 120, maxAgeH: 48 } });
  const o = K.options({}), sec = NOW / 1000;
  assert.deepEqual(K.sira({ tv: {}, iv: {} }, NOW, o), ["telegram", "instagram"]);
  assert.deepEqual(K.sira({ tv: {}, iv: { a: sec - 200 * 60 }, }, NOW, o), ["telegram", "instagram"]);
  assert.deepEqual(K.sira({ tv: { a: sec - 100 * 60 }, iv: { b: sec - 200 * 60 } }, NOW, o), ["instagram", "telegram"], "ən çoxdan videosu olmayan əvvəl");
  assert.match(K.due({ tv: { a: sec - 60 * 60 }, iv: { b: sec - 60 * 60 } }, NOW, o), /son Telegram videosu 60 dəq əvvəl \(ara 90 dəq\); son Instagram videosu 60 dəq əvvəl \(ara 120 dəq\)/);
  assert.match(K.due({ tv: Object.fromEntries(Array.from({ length: 6 }, (_, i) => [`v${i}`, sec - (i + 2) * 3600])) }, NOW, K.options({ INSTAGRAM_VIDEO: "0" })), /24 saatda 6 Telegram videosu/);
  assert.match(K.due({}, NOW, K.options({ TELEGRAM_VIDEO: "0", INSTAGRAM_VIDEO: "0" })), /TELEGRAM_VIDEO=0.*INSTAGRAM_VIDEO=0/);
  assert.equal(K.due({ tv: { a: sec - 60 } }, NOW, K.options({ INSTAGRAM_VIDEO: "0" }), true), "", "VIDEO_TUR=kanal: ara gözlənmir");

  const dir = tmp(), old = process.env.GITHUB_OUTPUT;
  process.env.GITHUB_OUTPUT = path.join(dir, "out.txt");
  try {
    const st = SV.readState("/yoxdur", NOW);
    const x = { id: "k1".padEnd(16, "0"), tur: "kanal", kind: "kanal", platforma: "telegram", title: BESIKTAS.basliq, text: BESIKTAS.text, category: "", source: "Modern.az",
      sourceUrl: "https://t.me/modern_azz/95488", sayt: "https://modern.az/", publishedAt: new Date(NOW).toISOString(), menbeVideo: { file: "klip-menbe.mp4", kredit: "Modern.az (Telegram)" } };
    let asked = 0, dunya = 0, xv = 0;
    const args = (now, env = {}) => ({ articles: [], env: { VIDEO_ACAR: "1", MARAQLI_VIDEO: "0", ...env }, now, state: st, fetch: async () => ({ ok: false }), cats: [], dir, log: () => {},
      kanal: async a => { asked++; assert.equal(typeof a.policy, "function"); assert.ok(Array.isArray(a.articles)); return x; }, dunya: async () => { dunya++; return null; }, xvideo: async () => { xv++; return null; } });
    const r = await SV.sec(args(NOW));
    assert.equal(r.link, "https://8ulduz.az/"); assert.equal(r.url, r.link);
    assert.ok(st.tv[x.id] && st.v[x.id] && st._last, "gündəlik həddə və ümumi fasiləyə sayılır");
    assert.deepEqual([asked, dunya, xv], [1, 0, 1], "X-dən sonra, dünyadan əvvəl");
    assert.match(fs.readFileSync(process.env.GITHUB_OUTPUT, "utf8"), /hazir=1\ntur=kanal/);
    // Növbəti pəncərə: Telegram-ın arası dolmayıb, Instagram vaxtındadır — yenə soruşulur (o, Instagram-ı yoxlayır).
    await SV.sec(args(NOW + 31 * 60e3, { INSTAGRAM_VIDEO: "0" }));
    assert.equal(asked, 1, "Telegram-ın arası (90 dəq) dolmayıb, Instagram söndürülüb");
    assert.equal(dunya, 1, "növbə dünya videosundadır");
    // Söndürülüb: soruşulmur. VIDEO_TUR=kanal: dərhal, alınmasa başqa növə keçmir.
    await SV.sec(args(NOW + 200 * 60e3, { TELEGRAM_VIDEO: "0", INSTAGRAM_VIDEO: "0" }));
    assert.equal(asked, 1);
    const st2 = SV.readState("/yoxdur", NOW); let a2 = 0, d2 = 0;
    const r2 = await SV.sec({ ...args(NOW, { VIDEO_TUR: "kanal" }), state: st2, kanal: async a => { a2++; assert.equal(a.zorla, true); return null; }, dunya: async () => { d2++; return null; } });
    assert.deepEqual([r2, a2, d2], [null, 1, 0]);
    // Siyahı tv, iv, km-i saxlayır.
    const f = path.join(dir, "state.json");
    fs.writeFileSync(f, JSON.stringify({ ...st, iv: { b: NOW / 1000 }, km: { "tg:oxuaze": NOW / 1000 } }));
    const back = SV.readState(f, NOW);
    assert.ok(back.tv[x.id] && back.iv.b && back.km["tg:oxuaze"]);
    // Paylaşım: mövzu siyahısına düşür — eyni hadisənin xəbər videosu getmir.
    fs.writeFileSync(path.join(dir, "xeber.json"), JSON.stringify({ ...x, link: "https://8ulduz.az/" }));
    fs.writeFileSync(path.join(dir, "video.mp4"), mp4());
    const s3 = SV.readState("/yoxdur", NOW);
    await SV.paylas({ dir, env: {}, now: NOW, state: s3, log: () => {} });
    assert.ok(s3.tv[x.id] && s3.v[x.id] && s3.topics.length === 1);
  } finally { if (old === undefined) delete process.env.GITHUB_OUTPUT; else process.env.GITHUB_OUTPUT = old; }
});

test("kanal: the montage takes the entry under the site's own address; YouTube and TikTok skip it (source rule), only Facebook and Instagram Reels get it", () => {
  const x = { id: "k1".padEnd(16, "0"), tur: "kanal", kind: "kanal", title: BESIKTAS.basliq, text: BESIKTAS.text, category: "", source: "Modern.az", sourceUrl: "https://t.me/modern_azz/95488", sayt: "https://modern.az/" };
  // Montajın qaydası (video-xeber.cjs render): kanal girişi saytın öz ünvanı ilə; sayt yoxdursa və ya başqa saytdırsa — keçmir.
  const vx = read(".github/scripts/video-xeber.cjs");
  assert.match(vx, /x\?\.kind === "kanal" \? app\.policyViolation\(\{ \.\.\.x, sourceUrl: x\.sayt \|\| "" \}\)/);
  const montaj = a => (a?.kind === "kanal" ? app.policyViolation({ ...a, sourceUrl: a.sayt || "" }) : app.policyViolation(a));
  assert.equal(montaj(x), false);
  assert.equal(montaj({ ...x, summary: x.text }), false);
  assert.equal(montaj({ ...x, sayt: "" }), true);
  assert.equal(montaj({ ...x, sayt: "https://meydan.tv/" }), true);
  assert.equal(montaj({ ...x, source: "Namelum.az", sayt: "https://namelum.az/" }), true, "siyahıda olmayan sayt");
  const meta = V.storyFields(x);
  assert.deepEqual([meta.kind, meta.url, meta.sayt, meta.sourceUrl], ["kanal", "https://8ulduz.az/", "https://modern.az/", "https://t.me/modern_azz/95488"]);
  // YouTube və TikTok: öz qaydaları ilə ötürülür — Telegram «mənbə qaydası», Instagram «sosial şəbəkədəndir».
  const nisanli = Buffer.concat([mp4(4000), Buffer.from("comment=8ulduz.az")]);
  const yuk = a => (a?.kind === "dunya" || a?.kind === "x" ? app.xariciPozur(a) : app.policyViolation(a));
  for (const U of [require("../.github/scripts/youtube.cjs"), require("../.github/scripts/tiktok.cjs")]) {
    assert.equal(U.foreignReason(meta, nisanli), "");
    assert.match(U.policyReason(meta, yuk), /mənbə qaydası \(Modern\.az\)/);
    assert.match(U.foreignReason({ ...meta, sourceUrl: "https://www.instagram.com/reel/R1801/", source: "Baku.ws" }, nisanli), /sosial şəbəkədəndir/);
  }
  // Post mətnində «Görüntü: …» montajın krediti ilə.
  assert.match(SV.fbText({ ...x, link: "https://8ulduz.az/", goruntu: [{ p: "Mənbə" }], goruntuMenbe: "Baku.ws (Instagram), @foto_by_gunew" }), /Görüntü: Baku\.ws \(Instagram\), @foto_by_gunew/);
});

test("kanal: the frame check stops a video with another outlet's big title block or overlay, or blood; a small corner logo passes; unchecked means not posted", async () => {
  const x = { tur: "kanal", platforma: "instagram", source: "Baku.ws", text: QUTAB.text };
  const cavab = j => async (url, o) => (/models\?pageSize/.test(url) ? { ok: true, json: async () => ({ models: [] }) }
    : j == null ? { ok: false, status: 400, json: async () => ({}) } : { ok: true, status: 200, json: async () => ({ candidates: [{ content: { parts: [{ text: JSON.stringify(j) }] } }] }) });
  const deps = { kadrlar: () => [Buffer.from("jpg1"), Buffer.from("jpg2")] };
  const y = (j, o = {}) => K.kadrYoxla(x, { dir: tmp(), env: ENV, fetch: cavab(j), log: () => {}, deps, ...o });
  assert.deepEqual(await y({ yazi: false, qan: false }), { ok: true }, "küncdə kiçik loqo");
  assert.match((await y({ yazi: true, qan: false, sebeb: "Yuxarıda Baku.ws-in başlıq bloku var" })).dayan, /başqa saytın başlıq bloku və ya yazı örtüyü var \(Yuxarıda Baku\.ws/);
  assert.match((await y({ yazi: false, qan: true })).dayan, /qan/);
  assert.match((await y(null)).dayan, /kadrlar yoxlanmadı/);
  assert.match((await y({ yazi: false }, { env: {} })).dayan, /GEMINI_API_KEY/);
  assert.match((await y({ yazi: false }, { deps: { kadrlar: () => { throw new Error("ffmpeg yoxdur"); } } })).dayan, /kadrlar alınmadı: ffmpeg yoxdur/);
  assert.match((await K.kadrYoxla({ ...x, text: "Qısa mətn." }, { dir: tmp(), env: ENV, fetch: cavab({}), deps })).dayan, /şərh azdır/);
  assert.match(K.kadrPromptOf(x, 2), /Baku\.ws saytının Instagram paylaşımından/);
  assert.match(K.KADR_PROMPT, /Küncdəki kiçik loqo/);
  assert.match(read(".github/scripts/sosial-video.cjs"), /if \(cmd === "kanal-kadr"\)/);
});

test("kanal: the workflow ships the module and the list, passes the switches and our key to the pick step (documented), and checks the frames before the montage", () => {
  const wf = read(".github/workflows/sosial-video.yml");
  for (const f of [".github/scripts/video-kanal.cjs", ".github/video-kanal.json"]) assert.ok(wf.split(f).length >= 3, `${f}: PR yolu və sparse-checkout`);
  for (const v of ["TELEGRAM_VIDEO", "TELEGRAM_GUNDE", "TELEGRAM_ARA_MIN", "INSTAGRAM_VIDEO", "INSTAGRAM_GUNDE", "INSTAGRAM_ARA_MIN", "IG_USER_ID", "FB_GRAPH_VERSION"]) assert.ok(wf.includes(`${v}: \${{ vars.${v} }}`), v);
  const secStep = wf.slice(wf.indexOf("- name: Xəbər seç"), wf.indexOf("- name: ffmpeg və şrift"));
  assert.ok(secStep.includes("FB_PAGE_TOKEN: ${{ github.event_name != 'pull_request' && secrets.FB_PAGE_TOKEN || '' }}") && /Business Discovery/.test(secStep) && /jurnala düşmür/.test(secStep));
  const kadr = wf.indexOf("- name: 'Kanal: kadrları yoxla'");
  assert.ok(kadr > wf.indexOf("- name: ffmpeg və şrift") && kadr < wf.indexOf("- name: Video hazırla"));
  assert.match(wf.slice(kadr, kadr + 600), /steps\.sec\.outputs\.tur == 'kanal'[\s\S]*GEMINI_API_KEY[\s\S]*sosial-video\.cjs kanal-kadr video-out/);
  assert.match(wf, /options: \[avtomatik, hava, xeber, maraqli, dunya, x, kanal\]/);
  // Sənəd: sahibin sözləri, köhnəlmiş Telegram sətri yoxdur.
  const doc = read("docs/sosial-video.md");
  assert.ok(doc.includes("«qutab bölməsi ilə razı deyiləm. Baku VS də sosil şəbəkələrdən götürüb öz komentini verib. Biz bunu da etməliyik»") && doc.includes("«A B ni də.. B tək oxuaz la məhdud qalmasın»"));
  assert.ok(!doc.includes("**YouTube, Instagram, TikTok, Telegram pəncərəsi**"));
});
