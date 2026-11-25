// Video xəbər (sahib, 2026-11-22): .github/scripts/video-xeber.cjs (video) və .github/scripts/sosial-video.cjs (seçim, FB/IG Reels).
// ffmpeg burada işləmir: video planı, ASS yazıları və ffmpeg arqumentləri yoxlanır; real video PR-da sosial-video.yml-də hazırlanır.
const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("fs"), path = require("path"), os = require("os");
const V = require("../.github/scripts/video-xeber.cjs");
const SV = require("../.github/scripts/sosial-video.cjs");
const S = require("../.github/scripts/social.cjs");
const root = path.join(__dirname, "..");
const read = f => fs.readFileSync(path.join(root, f), "utf8").replace(/\r\n/g, "\n");

const NOW = Date.parse("2026-11-22T10:00:00Z");   // Bakı vaxtı 14:00
const ago = m => new Date(NOW - m * 60e3).toISOString();
const art = (id, o = {}) => ({ id: id.padEnd(16, "0"), title: `Xəbər ${id}`, summary: "Qısa xülasə.", category: "gundem", lang: "az", source: "APA",
  sourceUrl: `https://apa.az/${id}`, publishedAt: ago(10), alts: [{ source: "Report" }, { source: "Oxu.az" }, { source: "Trend" }], ...o });
const fixture = JSON.parse(read("tests/fixtures/video-xeber.json"));
const cats = [{ slug: "cemiyyet", label: "Cəmiyyət" }, { slug: "gundem", label: "Gündəm" }, { slug: "prezident", label: "Zuğulba Xronikası" }];

test("video: the plan — big headline that fits, full sentences only, captions of at most 3 lines, Baku time, sources", () => {
  const p = V.prepare(fixture, { cats });
  assert.equal(p.label, "CƏMİYYƏT", "bölmə adı böyük hərflə, Azərbaycan qaydası ilə (İ, Ə)");
  assert.equal(p.when, "22 noyabr, 13:14", "Bakı vaxtı (UTC+4)");
  assert.equal(p.source, "Mənbə: Day.Az, Azpolitika.info və daha 11 sayt");
  // Sahib 2026-11-24: «Başlıqları oxumasın»; 2026-11-25: «8ulduz videolarında başlıq oxunmamalı idi» — başlıq ekrandadır, səsdə yoxdur.
  assert.ok(p.quietHead && !p.say.includes(fixture.title) && !p.say.some(x => x.includes(fixture.title)), "başlıq oxunmur");
  assert.deepEqual(p.say.slice(0, -1), p.chunks, "səs izahın birinci altyazısı ilə başlayır");
  // Sahib 2026-11-25: «baxış var, lakin baxanlar hesaba abunə olmurlar» — sonluq sayta yox, abunəyə çağırır; hər növün öz vədi.
  assert.equal(p.say.at(-1), "Abunə olun, ən vacib xəbərlər hər gün burada.", "sonda abunə çağırışı səslənir");
  assert.equal(p.say.at(-1), V.abune("xeber").say);
  const fact = V.prepare({ ...fixture, tur: "maraqli", bolme: "Maraqlı" }, { cats });
  assert.equal(fact.say.at(-1), "Abunə olun, hər gün yeni maraqlı faktlar burada.");
  assert.equal(fact.label, "BİLİRDİNİZMİ?", "maraqlı videonun nişanı rubrikanın adıdır");
  assert.equal(p.head.lines.join(" "), fixture.title, "başlıq kəsilmir");
  for (const l of p.head.lines) assert.ok(V.textWidth(l, p.head.size, "black") <= V.W - 2 * 72, `sətir sığır: ${l}`);
  assert.ok(p.head.lines.length * p.head.size <= V.L.headMaxH);
  assert.equal(p.chunks.join(" "), fixture.summary, "izahın hamısı altyazıdadır, söz itmir");
  for (const c of p.chunks) assert.ok(V.wrap(c, 62, "medium", V.W - 2 * 72 - 32).length <= 3, `altyazı ≤ 3 sətir: ${c}`);
  assert.ok(!p.chunks.some(c => /Ərçivan$/.test(c)), "ad birləşməsi («Ərçivan qəsəbəsindən») bölünmür");
  // Çox uzun başlıq: ən kiçik ölçü, son sətir «…».
  const long = V.prepare({ ...fixture, title: "Söz ".repeat(120).trim() }, { cats });
  assert.equal(long.head.size, 60);
  assert.ok(long.head.lines.at(-1).endsWith("…") && long.head.lines.length * 60 <= V.L.headMaxH);
  assert.throws(() => V.prepare({ ...fixture, title: " " }), /başlıq yoxdur/);
});

test("video: the explanation is cut at whole sentences; a source's «…» tail never reaches the video", () => {
  assert.equal(V.bodyText({ title: "B", summary: "Birinci cümlə tamdır. İkinci cümlə yarımçıq qal..." }), "Birinci cümlə tamdır.");
  assert.equal(V.bodyText({ title: "B", summary: "Yarımçıq…" }), "");
  const many = Array.from({ length: 24 }, (_, i) => `Bu, ${i + 1}-ci tam cümlədir və bir az uzundur.`).join(" ");
  const b = V.bodyText({ title: "B", text: many });
  // Sahib 2026-11-22: «Xəbər uzun olsun biraz», «4-7 cümlədə olsun. uzun da olsun» — 360 → 750 simvol (≈ 5–7 cümlə, 35–45 s).
  assert.ok(b.length <= 750 && b.length > 600 && /\.$/.test(b), `izah ≤ 750 simvol, tam cümlə ilə bitir: ${b.length}`);
  assert.equal(V.bodyText({ title: "Eyni mətn.", summary: "Eyni mətn." }), "", "başlığın təkrarı izah deyil");
  assert.equal(V.bodyText({ title: "B", text: "İzah  <b>var</b>." }), "İzah var.", "HTML təmizlənir");
  assert.deepEqual(V.captionChunks("Prezident İ. Əliyev qəbul edib. Görüş Bakıda olub."), ["Prezident İ. Əliyev qəbul edib.", "Görüş Bakıda olub."], "inisial cümləni bölmür");
});

// Sahib 2026-11-25: «yeni videolarda sətirdən sətrə keçəndə mənasız pauza verir oxunuşda». Altyazının böldüyü cümlə səsdə bir
// mətndir (video_ses.py groups): prepare().davam hansı hissənin əvvəlkinin davamı olduğunu deyir — böyük hərflə başlasa da.
test("video: parts of one sentence split by captions are marked as one breath for the voice (davam)", () => {
  const p = V.prepare(fixture, { cats });
  assert.equal(p.davam.length, p.say.length);
  assert.deepEqual(p.davam, [false, true, false, false], "«…yol-nəqliyyat hadisəsi | nəticəsində…» bir cümlədir");
  assert.deepEqual(V.captionSentences(fixture.summary).flat(), V.captionChunks(fixture.summary), "altyazılar dəyişmir");
  const long = "Məhkəmədə ağır cinayətdə təqsirləndirilən və həbsdə saxlanılan keçmiş məmur Xudat Məmmədovun barəsindəki qərardan şikayət verilib, iş apellyasiya məhkəməsinə göndərilib. Növbəti iclas dekabrda olacaq.";
  const q = V.prepare({ ...fixture, summary: long }, { cats });
  const s = V.captionSentences(long);
  assert.ok(s[0].length > 1, "uzun cümlə bir neçə altyazıdır");
  assert.deepEqual(q.davam, [...s.flatMap(x => x.map((_, j) => j > 0)), false]);
  assert.ok(q.davam.slice(0, -1).some(Boolean) && !q.davam[0] && !q.davam.at(-1), "birinci cümlə və sonluq ayrıca səslənir");
  assert.ok(read(".github/scripts/video-xeber.cjs").includes("davam: p.davam"), "voice() səs hissələrinə davam yazır");
});

test("video: timing — reading speed without voice, the voice's own timing with it, never longer than 59 s", () => {
  const p = V.prepare(fixture, { cats });
  const t = V.timeline(p, null);
  assert.ok(t.duration >= V.MIN_S && t.duration <= V.MAX_S, String(t.duration));
  assert.equal(t.chunks.length, p.chunks.length);
  for (let i = 1; i < t.chunks.length; i++) assert.ok(t.chunks[i].at[0] >= t.chunks[i - 1].at[1], "altyazılar üst-üstə düşmür");
  assert.ok(t.chunks.every(c => c.at[1] - c.at[0] >= 2.4), "hər altyazı oxunacaq qədər qalır");
  assert.ok(t.outro[0] >= t.chunks.at(-1).at[1] && t.duration >= t.outro[1]);
  // Səsli: hissələrin vaxtı səs faylından; səs dərhal (0,35 s) birinci altyazı ilə başlayır — başlıq üçün səssiz an yoxdur
  // (2026-11-25, YouTube Studio: baxanların 60,6%-i ilk saniyələrdə ötürür; ilk saniyə sükutla getmir).
  const parts = p.say.map((_, i) => [i * 3, i * 3 + 2.5]);
  const tv = V.timeline(p, { parts });
  assert.deepEqual(tv.head, [0, 0.35]);
  assert.equal(tv.lead, 0.35);
  assert.deepEqual(tv.chunks[0].at, [0.35, 2.85]);
  assert.equal(tv.voiceCut.outroFrom, 0.35 + (p.say.length - 1) * 3);
  assert.deepEqual(t.head, [0, 0.35], "səssiz planda da birinci altyazı 0,35 s-də başlayır");
  assert.equal(t.chunks[0].at[0], 0.35);
  // Çox uzun səs: sondakı altyazılar düşür, sonluq qalır, video ≤ 59 s.
  // (başlıq səsdə yoxdur — hissə bir azdır: 17 s-lik hissələr 59 s-i keçir)
  const slow = V.timeline(p, { parts: p.say.map((_, i) => [i * 17, i * 17 + 16]) });
  assert.ok(slow.duration <= V.MAX_S && slow.chunks.length < p.chunks.length && slow.chunks.length > 0);
  assert.ok(slow.outro[0] < slow.voiceCut.outroFrom, "sonluq səsi sonluğun başlanğıcına sürüşür");
  assert.equal(V.timeline(p, { parts: [[0, 1]] }).voiceCut, null, "hissə sayı uyğun deyilsə səs işlənmir (səssiz plan)");
  // ASS-də altyazılar heç vaxt eyni anda görünmür (2026-11-22, CI kadrı: səsli videoda 0,25 s iki altyazı üst-üstə idi).
  const sec = s => { const [h, m, x] = s.split(":"); return +h * 3600 + +m * 60 + +x; };
  for (const plan of [t, tv]) {
    const caps = V.ass(p, plan).split("\n").filter(l => /^Dialogue: 4,/.test(l)).map(l => l.split(",").slice(1, 3).map(sec));
    assert.equal(caps.length, p.chunks.length);
    for (let i = 1; i < caps.length; i++) assert.ok(caps[i][0] >= caps[i - 1][1], `altyazı ${i}: ${caps[i - 1]} / ${caps[i]}`);
    assert.ok(caps.at(-1)[1] <= plan.outro[0] + 0.01, "sonuncu altyazı sonluqdan əvvəl çəkilir");
  }
});

test("video: «8ulduz.az» is burned in at the top from the first to the last frame, inside the feed's 4:5 crop", () => {
  const p = V.prepare(fixture, { cats }), t = V.timeline(p, null), a = V.ass(p, t);
  const ev = a.split("\n").filter(l => l.startsWith("Dialogue:"));
  const span = l => l.split(",").slice(1, 3);
  const end = l => span(l)[1];
  const D = `0:00:${String(Math.floor(t.duration)).padStart(2, "0")}.${String(Math.round(t.duration * 100) % 100).padStart(2, "0")}`;
  const az = ev.find(l => /\}\.az$/.test(l));
  assert.ok(az && span(az)[0] === "0:00:00.00" && end(az) === D, "«.az» yazısı 0-dan sona qədər (loqo şəkli ilə «8ULDUZ.az»)");
  const bar = ev.find(l => /\\pos\(0,300\)/.test(l));
  assert.ok(bar && span(bar)[0] === "0:00:00.00" && end(bar) === D, "brend zolağı başdan sona");
  assert.ok(ev.some(l => /Ətraflı: \{\\1c&H0AA3F5&\}8ulduz\{\\1c&HFFFFFF&\}\.az$/.test(l)), "sonluqda sayt adı qalır: «Ətraflı: 8ulduz.az»");
  // Abunə çağırışı (sahib, 2026-11-25): sonluqda vəd və «ABUNƏ OL» düyməsi; videonun içində zolağın sağında kiçik nişan
  // (3-cü saniyədən sonluğa qədər — çox baxan sona çatmır).
  const sub = ev.filter(l => l.split(",")[3] === "Sub" && l.endsWith("}ABUNƏ OL"));
  assert.equal(sub.length, 2, "nişan və düymə");
  const [badge, button] = sub;
  assert.ok(span(badge)[0] === "0:00:03.00" && /\\an6\\pos\(996,360\)\\fs34/.test(badge), "nişan zolaqdadır (y 300…420), sağ kənarı mətn sahəsində (x ≤ 1008)");
  const sec = s => { const [h, m, x] = s.split(":"); return +h * 3600 + +m * 60 + +x; };
  assert.ok(Math.abs(sec(span(button)[0]) - t.outro[0]) < 0.011 && end(button) === D && /\\pos\(540,900\)/.test(button), "düymə sonluqda, ortada");
  assert.ok(ev.some(l => l.endsWith("}Ən vacib xəbərlər hər gün") && span(l)[0] === span(button)[0]), "düymənin üstündə növün vədi");
  assert.match(a, /^Style: Sub,Roboto Black,88,&H0026140B,&H0026140B,&H000AA3F5,.*,3,28,0,5,72,72,0,1$/m, "narıncı qutuda tünd yazı (saytın rəngləri)");
  assert.ok(!/OutroBig/.test(a), "köhnə sonluq üslubu qalmayıb");
  // Çox qısa videoda (nişana 2 s qalmır) nişan yoxdur, düymə var.
  const short = V.ass(p, { ...t, outro: [4, 7], duration: 7.3, chunks: t.chunks.slice(0, 1) }).split("\n").filter(l => l.endsWith("}ABUNƏ OL"));
  assert.equal(short.length, 1);
  // ffmpeg: loqo şəkli bütün video boyu (enable/zaman şərti yoxdur), zolağın içində.
  const args = V.ffmpegArgs({ tl: t, assFile: "video.ass", logo: "assets/logo.png", voiceFile: null, out: "o.mp4" });
  const fc = args[args.indexOf("-filter_complex") + 1];
  assert.match(fc, /\[t\]\[lg\]overlay=72:320:format=rgb/);
  assert.ok(!/enable=/.test(fc));
  // Bütün mövqelər lentin 4:5 kəsiyində (y 285…1635) və şəbəkə düymələrindən uzaqda (y ≤ 1480).
  for (const l of ev) {
    const m = l.match(/\\(?:pos|move)\((\d+(?:\.\d+)?),(\d+(?:\.\d+)?)/);
    if (!m || /\\p1/.test(l)) continue;   // fon formaları istisna
    assert.ok(+m[2] >= 300 && +m[2] <= 1480, `y=${m[2]}: ${l.slice(0, 80)}`);
  }
});

test("video: text cannot break the ASS script, and only our own material goes into the video (no third-party media)", () => {
  const p = V.prepare({ ...fixture, title: "Başlıq {\\an8\\pos(0,0)} və C:\\yol", text: "İzah {\\fs200}x\\Ny." }, { cats });
  const ev = V.ass(p, V.timeline(p, null)).split("\n").filter(l => l.startsWith("Dialogue:"));
  const texts = ev.map(l => l.replace(/\{[^}]*\}/g, ""));
  assert.ok(!texts.some(x => /\\an8|\\fs200|\\pos\(0,0\)/.test(x)), "mətndəki { } \\ etiket kimi işləmir");
  assert.ok(ev.some(l => l.replace(/\\N/g, " ").includes("Başlıq (/an8/pos(0,0))")), "mötərizə və «/» ilə əvəz olunur");
  // Girişlər: rəngli fon, saytın loqosu, səs (SARA) və ya sükut — xəbərin şəkli/videosu, musiqi yoxdur.
  const t = V.timeline(p, null);
  const inputs = a => a.filter((x, i) => a[i - 1] === "-i");
  assert.deepEqual(inputs(V.ffmpegArgs({ tl: t, assFile: "v.ass", logo: "L.png", voiceFile: null, out: "o.mp4" })),
    [`color=c=0x0B1426:s=1080x1920:r=30:d=${t.duration.toFixed(2)}`, "L.png", "anullsrc=channel_layout=stereo:sample_rate=48000"]);
  assert.deepEqual(inputs(V.ffmpegArgs({ tl: t, assFile: "v.ass", logo: "L.png", voiceFile: "ses.wav", out: "o.mp4" })).slice(1), ["L.png", "ses.wav"]);
  const src = read(".github/scripts/video-xeber.cjs");
  assert.ok(!/imageUrl|\.xv\b|reels\.json|twimg|oz_x/.test(src), "video modulu xəbərin şəklini/videosunu işlətmir (müəllif hüququ, docs/sosial-video.md)");
});

test("video: encoder settings match Facebook/Instagram Reels and TikTok (9:16, H.264 yuv420p, 30 fps, AAC 48 kHz, faststart)", () => {
  const p = V.prepare(fixture, { cats }), t = V.timeline(p, null);
  const a = V.ffmpegArgs({ tl: t, assFile: "v.ass", logo: "L.png", voiceFile: "ses.wav", out: "o.mp4" }), at = k => a[a.indexOf(k) + 1];
  assert.equal(at("-c:v"), "libx264"); assert.equal(at("-pix_fmt"), "yuv420p"); assert.equal(at("-r"), "30"); assert.equal(at("-g"), "60");
  assert.equal(at("-c:a"), "aac"); assert.equal(at("-ar"), "48000"); assert.equal(at("-ac"), "2"); assert.equal(at("-movflags"), "+faststart");
  assert.equal(at("-t"), t.duration.toFixed(2));
  assert.match(a[a.indexOf("-filter_complex") + 1], /adelay=350:all=1/, "səs dərhal (0,35 s) başlayır: başlıq oxunmur, ilk saniyə sükutla getmir");
  assert.match(a[a.indexOf("-filter_complex") + 1], /loudnorm=I=-16/, "səs səviyyəsi sosial şəbəkə normasında");
  assert.equal(a.at(-1), "o.mp4");
  assert.equal(at("-metadata"), "comment=8ulduz.az", "öz videomuzun nişanı (TikTok yükləyicisi yalnız bunu göndərir)");
  // <çıxış>.json-da xəbərin sahələri (TikTok yükləyicisi oxuyur): own yalnız bu modulun videosunda.
  const s = V.storyFields({ ...fixture, text: "İzah <b>tam</b>." });
  assert.deepEqual(s, { id: fixture.id, own: true, title: fixture.title, summary: fixture.summary, text: "İzah tam.", source: "Day.Az",
    sourceUrl: fixture.sourceUrl, category: "cemiyyet", lang: "az", publishedAt: fixture.publishedAt });
  assert.equal(V.storyFields({ ...fixture, text: "" }).text, fixture.summary, "izah yoxdursa xülasə");
});

test("video: a story that breaks the site's source rule (red line 2) never becomes a video", async () => {
  await assert.rejects(V.render(fixture, path.join(os.tmpdir(), "x.mp4"), { policy: () => "foreign_about_azerbaijan", cats, log: () => {} }), /qaydasından keçmir/);
  await assert.rejects(V.render({ ...fixture, text: "pis izah" }, path.join(os.tmpdir(), "x.mp4"), { policy: a => (a.summary === "pis izah" ? "x" : ""), cats, log: () => {} }), /izah/);
});

test("sosial-video: owner 2026-11-24 — ten times more own videos: every 30-minute window, at most 30 a day (Facebook limit)", () => {
  assert.deepEqual(SV.options({}), { minSources: 4, maxAgeH: 3, gapMin: 30, perDay: 30, from: 8, to: 23 });
  const st = SV.readState("/yoxdur", NOW), opt = SV.options({});
  assert.equal(SV.due({ ...st, _last: NOW / 1000 - 25 * 60 }, NOW, opt), "", "hər 30 dəqiqəlik pəncərədə video (dözüm 7 dəq)");
  const v = Object.fromEntries(Array.from({ length: 30 }, (_, i) => [`v${i}`, NOW / 1000 - i * 1800]));
  assert.match(SV.due({ ...st, v }, NOW, opt), /24 saatda 30 video/);
});

test("sosial-video: when a video goes — Baku day hours, 2 hours apart, at most 8 a day (all owner-tunable)", () => {
  // Mexanika 2026-11-24-dək standart olan rəqəmlərlə (120 dəqiqə, gündə 8) yoxlanır.
  const opt = SV.options({ VIDEO_MIN_GAP_MIN: "120", VIDEO_GUNDE: "8" });
  assert.deepEqual(opt, { minSources: 4, maxAgeH: 3, gapMin: 120, perDay: 8, from: 8, to: 23 });
  assert.deepEqual(SV.options({ VIDEO_SAAT: "7-22", VIDEO_MIN_GAP_MIN: "90", VIDEO_GUNDE: "12", SOCIAL_MIN_SOURCES: "3" }), { minSources: 3, maxAgeH: 3, gapMin: 90, perDay: 12, from: 7, to: 22 });
  const st = SV.readState("/yoxdur", NOW);
  assert.equal(SV.due(st, NOW, opt), "");
  assert.match(SV.due(st, Date.parse("2026-11-22T01:00:00Z"), opt), /Bakı vaxtı 5:00/, "gecə video getmir");
  assert.match(SV.due({ ...st, _last: NOW / 1000 - 30 * 60 }, NOW, opt), /30 dəq əvvəl, növbəti 80 dəq/);
  // Pəncərələr 30 dəqiqədən birdir (:17, :47), iş bir-iki dəqiqə gec başlayır: 2026-11-23 23:47-də «119 dəq əvvəl» video ötürüldü,
  // axşamın son pəncərəsi itdi. 10 dəqiqə dözüm: dördüncü pəncərə həmişə keçir, üçüncü (~90 dəq) keçmir.
  const ago = m => ({ ...st, _last: NOW / 1000 - m * 60 });
  assert.equal(SV.due(ago(119), NOW, opt), "", "119 dəqiqə — dördüncü pəncərə, video gedir");
  assert.equal(SV.due(ago(110), NOW, opt), "");
  assert.match(SV.due(ago(109), NOW, opt), /109 dəq əvvəl, növbəti 1 dəq/);
  assert.match(SV.due(ago(92), NOW, opt), /növbəti 18 dəq/, "üçüncü pəncərə gözləyir");
  // Dözüm fasilənin ¼-indən çox deyil: 30 dəqiqəlik fasilə 23 dəqiqədən qısa olmur.
  const o30 = SV.options({ VIDEO_MIN_GAP_MIN: "30" });
  assert.match(SV.due(ago(22), NOW, o30), /növbəti 1 dəq/);
  assert.equal(SV.due(ago(23), NOW, o30), "");
  const v = Object.fromEntries(Array.from({ length: 8 }, (_, i) => [`v${i}`, NOW / 1000 - i * 3600]));
  assert.match(SV.due({ ...st, v }, NOW, opt), /24 saatda 8 video/);
});

const page = body => `<html><head><meta property="og:description" content="${body}"></head><body><p>${body}</p></body></html>`;
// Saxta Gemini (video-ssenari.cjs): rəqəmsiz 6 cümlə + mənbənin son cümləsi. Gemini-siz video hazırlanmır (sahib, 2026-11-22).
const FILLER = ["Layihə sakinlərin rahatlığı üçün nəzərdə tutulub və uzun müddət xidmət göstərəcək.", "Tikinti işləri müasir standartlara uyğun aparılıb.",
  "Ərazidə abadlıq işləri də görülüb və yaşıllıq zolaqları salınıb.", "Yeni obyekt ətraf məhəllələrin sakinləri üçün də əlçatan olacaq.",
  "Rəsmilər bildirib ki, oxşar layihələr digər bölgələrdə də davam etdiriləcək.", "Sakinlər yeni obyektin açılışını müsbət qarşılayıblar."];
const gemini = (url, o) => {
  if (/models\?pageSize/.test(url)) return { ok: true, json: async () => ({ models: [] }) };
  const src = (JSON.parse(o.body).contents[0].parts[0].text.split("Mənbə mətni:\n")[1] || "").trim();
  const text = `${FILLER.join(" ")} ${src.split(/(?<=\.)\s+/).pop()}`;
  return { ok: true, status: 200, json: async () => ({ candidates: [{ content: { parts: [{ text: JSON.stringify({ uygun: true, text, axtar: [] }) }] } }] }) };
};
const pageFetch = map => async (url, o = {}) => (/generativelanguage\.googleapis\.com/.test(url) ? gemini(url, o)
  : map[url] ? { ok: true, text: async () => map[url] } : { ok: false, text: async () => "" });

test("sosial-video: picks the biggest story with an explanation, never twice, never the same topic; no key — nothing is made", async () => {
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), "sv-"));
  const out = path.join(dir, "out.txt");
  const old = process.env.GITHUB_OUTPUT;
  process.env.GITHUB_OUTPUT = out;
  try {
    const a = art("a1", { title: "Bakıda yeni metro stansiyası açılıb", alts: Array(8).fill({ source: "X" }) });
    const b = art("b1", { title: "Gəncədə yeni park salınıb" });
    const c = art("c1", { title: "Sumqayıtda yeni məktəb tikilib", alts: Array(5).fill({ source: "Y" }) });
    const f = pageFetch({ [a.sourceUrl]: page("Bakıda yeni metro stansiyası sərnişinlərin istifadəsinə verilib. Stansiyanın tikintisində müasir texnologiyalardan istifadə olunub, platformalar geniş salınıb. Stansiya Xətai rayonundadır."),
      [b.sourceUrl]: page("Gəncədə yeni park salınıb və sakinlərin istifadəsinə verilib. Parkda gəzinti yolları, fəvvarə və oturacaqlar quraşdırılıb, ağaclar əkilib. Parkda uşaq meydançası var.") });
    const logs = [];
    let st = SV.readState("/yoxdur", NOW);
    assert.equal(await SV.sec({ articles: [a], env: {}, now: NOW, state: st, fetch: f, cats, dir, log: s => logs.push(s) }), null);
    assert.ok(logs.some(s => /açar yoxdur/.test(s)) && !fs.existsSync(path.join(dir, "xeber.json")), "açar yoxdursa video hazırlanmır");
    const env = { VIDEO_ACAR: "1", GEMINI_API_KEY: "g" };
    const x = await SV.sec({ articles: [b, c, a], env, now: NOW, state: st, fetch: f, cats, dir, log: s => logs.push(s) });
    assert.equal(x.id, a.id, "ən çox mənbəli");
    const saved = JSON.parse(fs.readFileSync(path.join(dir, "xeber.json"), "utf8"));
    assert.match(saved.link, /^https:\/\/www\.8ulduz\.az\/a100000000000000\?h=\d{8}$/, "saytdakı xəbərin paylaşma keçidi");
    assert.match(saved.text, /Xətai rayonundadır\.$/);
    assert.equal(saved.bolme, "Gündəm");
    assert.equal(fs.readFileSync(out, "utf8"), "hazir=1\n");
    assert.equal(st._last, NOW / 1000, "seçim videonu sayır: alınmasa da eyni xəbər hər 30 dəqiqədə təkrar hazırlanmır");
    // 2 saat sonra: a getdi, c-nin izahı yoxdur (ötürülür, yadda qalır), b.
    st = { ...st, topics: [{ ...S.topicOf(a, NOW / 1000), posted: NOW / 1000 }] };
    const later = NOW + 121 * 60e3;
    const y = await SV.sec({ articles: [a, b, c].map(r => ({ ...r, publishedAt: new Date(later - 20 * 60e3).toISOString() })), env, now: later, state: st, fetch: f, cats, dir, log: s => logs.push(s) });
    assert.equal(y.id, b.id);
    assert.ok(st.skip[c.id] && logs.some(s => /izah tapılmadı, ötürülür — Sumqayıtda/.test(s)));
    // Eyni hadisə başqa başlıqla (social.cjs mövzu qaydası) video olmur.
    const st2 = SV.readState("/yoxdur", NOW);
    st2.topics.push({ ...S.topicOf(a, NOW / 1000), posted: NOW / 1000 });
    const same = art("d1", { title: "Bakıda yeni metro stansiyası istifadəyə verilib", summary: a.summary, sourceUrl: a.sourceUrl, alts: Array(9).fill({ source: "Z" }) });
    assert.equal(await SV.sec({ articles: [same], env, now: NOW, state: st2, fetch: f, cats, dir, log: s => logs.push(s) }), null);
    assert.ok(logs.some(s => /eyni mövzuda video var/.test(s)));
    // Əl ilə önizləmə (paylaşmadan): fasilə gözləmir, siyahıya yazmır.
    const st3 = { ...SV.readState("/yoxdur", NOW), _last: NOW / 1000 - 60 };
    const z = await SV.sec({ articles: [a], env: { VIDEO_PAYLAS: "0", GEMINI_API_KEY: "g" }, now: NOW, state: st3, fetch: f, cats, dir, log: () => {} });
    assert.equal(z.id, a.id);
    assert.equal(st3.v[a.id], undefined);
  } finally {
    if (old === undefined) delete process.env.GITHUB_OUTPUT; else process.env.GITHUB_OUTPUT = old;
  }
});

// Meta Graph API-nin saxta cavabları: hər sorğu yazılır.
function meta({ fail = {}, quota = 10, igAccount = "1784" } = {}) {
  const calls = [];
  let published = false, igUploads = 0;
  const res = (status, body) => ({ ok: status < 400, status, json: async () => body, text: async () => JSON.stringify(body) });
  const f = async (url, init = {}) => {
    const body = typeof init.body === "string" ? Object.fromEntries(new URLSearchParams(init.body)) : init.body;
    calls.push({ url, method: init.method || "GET", headers: init.headers || {}, body });
    if (/\/1470\?fields=access_token,instagram_business_account/.test(url)) return res(200, { access_token: "PAGEtoken123456", instagram_business_account: igAccount ? { id: igAccount } : undefined, id: "1470" });
    if (/\/1470\/video_reels$/.test(url) && body.upload_phase === "start") return fail.fbStart ? res(400, { error: { message: "no permission PAGEtoken123456" } }) : res(200, { video_id: "777", upload_url: "https://rupload.facebook.com/video-upload/v27.0/777" });
    if (url === "https://rupload.facebook.com/video-upload/v27.0/777") return res(200, { success: true });
    if (/\/1470\/video_reels$/.test(url) && body.upload_phase === "finish") return res(200, { success: true });
    if (/\/777\?fields=status/.test(url)) return res(200, { status: { video_status: "ready" } });
    if (/\/777\/comments$/.test(url)) return fail.comment ? res(403, { error: { message: "(#200) requires pages_manage_engagement" } }) : res(200, { id: "c1" });
    if (/\/1784\/content_publishing_limit/.test(url)) return res(200, { data: [{ quota_usage: quota, config: { quota_total: 100 } }] });
    if (/\/1784\/media$/.test(url)) return res(200, { id: "555", uri: "https://rupload.facebook.com/ig-api-upload/v27.0/555" });
    if (url === "https://rupload.facebook.com/ig-api-upload/v27.0/555") return (fail.igUpload > igUploads++)
      ? res(400, { debug_info: { retriable: false, type: "ProcessingFailedError", message: "Request processing failed" } }) : res(200, { success: true, message: "Upload successful." });
    if (/\/555\?fields=status_code/.test(url)) return res(200, { status_code: published ? "PUBLISHED" : "FINISHED" });
    if (/\/1784\/media_publish$/.test(url) && (published = true)) return fail.igPublish ? res(400, { error: { code: 2207051, message: "Application request limit reached" } }) : res(200, { id: "IG1" });
    return res(404, { error: { message: "gözlənilməz " + url } });
  };
  return { f, calls };
}
function readyDir() {
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), "svp-"));
  const x = { ...art("e1", { title: "Bakıda yeni metro stansiyası açılıb" }), text: "Stansiya Xətai rayonundadır. Sərnişinlər üçün açıqdır." };
  fs.writeFileSync(path.join(dir, "xeber.json"), JSON.stringify({ ...x, link: S.shareUrl(x) }));
  fs.writeFileSync(path.join(dir, "video.mp4"), Buffer.alloc(4321, 7));
  fs.writeFileSync(path.join(dir, "video.json"), JSON.stringify({ cover_s: 1.5 }));
  return { dir, x };
}
const ENV = { FB_PAGE_ID: "1470", FB_PAGE_TOKEN: "EAAuserTOKEN123456", VIDEO_POLL_MS: "1", VIDEO_FB_WAIT_S: "1", VIDEO_IG_WAIT_S: "1" };

test("sosial-video: Facebook Reels — uploaded straight to Meta (no public file), the post text links to the story, link also as first comment", async () => {
  const { dir, x } = readyDir(), { f, calls } = meta(), state = SV.readState("/yoxdur", NOW), logs = [];
  const r = await SV.paylas({ dir, env: { ...ENV, VIDEO_INSTAGRAM: "0" }, now: NOW, state, fetch: f, log: s => logs.push(s) });
  assert.deepEqual(r, { posted: ["facebook"], failed: [] });
  const start = calls.find(c => c.body?.upload_phase === "start"), up = calls.find(c => c.url.startsWith("https://rupload.facebook.com/video-upload/"));
  const fin = calls.find(c => c.body?.upload_phase === "finish"), com = calls.find(c => /\/comments$/.test(c.url));
  assert.ok(start && up && fin && com && calls.indexOf(start) < calls.indexOf(up) && calls.indexOf(up) < calls.indexOf(fin) && calls.indexOf(fin) < calls.indexOf(com));
  assert.equal(start.body.access_token, "PAGEtoken123456", "istifadəçi açarından alınmış səhifə açarı");
  assert.deepEqual([up.headers.authorization, up.headers.offset, up.headers.file_size], ["OAuth PAGEtoken123456", "0", "4321"]);
  assert.equal(up.body.length, 4321, "fayl birbaşa yüklənir");
  assert.equal(fin.body.video_state, "PUBLISHED");
  assert.ok(fin.body.description.startsWith("Bakıda yeni metro stansiyası açılıb\n\nStansiya Xətai rayonundadır."));
  assert.ok(fin.body.description.includes(`Ətraflı: ${S.shareUrl(x)}`), "Facebook mətnində saytdakı xəbərin keçidi");
  assert.ok(fin.body.description.includes("Ən vacib xəbərlər hər gün — səhifəmizi izləyin."), "Facebook mətnində abunə çağırışı (sahib, 2026-11-25)");
  assert.equal(com.body.message, `Ətraflı: ${S.shareUrl(x)}`);
  assert.ok(state.facebook[x.id] && state.v[x.id] && state.t[S.titleKey(x)] && state.topics.length === 1);
  // Şərh icazəsi yoxdursa (pages_manage_engagement) post yenə uğurludur, jurnalda səbəb yazılır.
  const m2 = meta({ fail: { comment: true } }), logs2 = [];
  const r2 = await SV.paylas({ dir, env: { ...ENV, VIDEO_INSTAGRAM: "0" }, now: NOW, state: SV.readState("/yoxdur", NOW), fetch: m2.f, log: s => logs2.push(s) });
  assert.deepEqual(r2.posted, ["facebook"]);
  assert.ok(logs2.some(s => /pages_manage_engagement/.test(s)));
});

test("sosial-video: Instagram Reels — resumable upload, waits for FINISHED, caption says «Ətraflı: 8ulduz.az» without a dead link", async () => {
  const { dir, x } = readyDir(), { f, calls } = meta(), state = SV.readState("/yoxdur", NOW);
  const r = await SV.paylas({ dir, env: { ...ENV, VIDEO_FACEBOOK: "0" }, now: NOW, state, fetch: f, log: () => {} });
  assert.deepEqual(r, { posted: ["instagram"], failed: [] });
  const init = calls.find(c => /\/1784\/media$/.test(c.url)), up = calls.find(c => c.url.includes("/ig-api-upload/")), pub = calls.find(c => /media_publish$/.test(c.url));
  assert.equal(init.body.media_type, "REELS"); assert.equal(init.body.upload_type, "resumable"); assert.equal(init.body.thumb_offset, "1500");
  assert.ok(init.body.caption.includes("Ən vacib xəbərlər hər gün — abunə olun: @8ulduz.az"), "Instagram mətnində abunə çağırışı: @ad basılır");
  assert.ok(init.body.caption.includes("Ətraflı: 8ulduz.az (keçid profildədir)") && !/https?:\/\//.test(init.body.caption), "Instagram-da keçid basılmır");
  assert.ok(init.body.caption.startsWith(x.title));
  assert.deepEqual([up.headers.authorization, up.headers.offset, up.headers.file_size], ["OAuth PAGEtoken123456", "0", "4321"]);
  assert.ok(calls.indexOf(up) < calls.findIndex(c => /\/555\?fields=status_code/.test(c.url)) && pub.body.creation_id === "555");
  assert.ok(state.instagram[x.id]);
  // Dərc cavabı 2207051, konteyner isə PUBLISHED: post çıxıb (social.cjs-dəki Instagram xüsusiyyəti).
  const m2 = meta({ fail: { igPublish: true } });
  assert.deepEqual((await SV.paylas({ dir, env: { ...ENV, VIDEO_FACEBOOK: "0" }, now: NOW, state: SV.readState("/yoxdur", NOW), fetch: m2.f, log: () => {} })).posted, ["instagram"]);
  // 24 saatlıq hədd dolubsa yüklənmir; hesab bağlı deyilsə sakitcə ötürülür.
  const m3 = meta({ quota: 100 }), logs = [];
  assert.deepEqual(await SV.paylas({ dir, env: { ...ENV, VIDEO_FACEBOOK: "0" }, now: NOW, state: SV.readState("/yoxdur", NOW), fetch: m3.f, log: s => logs.push(s) }), { posted: [], failed: [] });
  assert.ok(logs.some(s => /hədd dolub/.test(s)) && !m3.calls.some(c => /\/media$/.test(c.url)));
  // 2026-11-22: rupload «ProcessingFailedError» (retriable: false) — yeni konteyner, bir dəfə təkrar; iki dəfə alınmasa xəta.
  const m5 = meta({ fail: { igUpload: 1 } }), logs5 = [];
  assert.deepEqual((await SV.paylas({ dir, env: { ...ENV, VIDEO_FACEBOOK: "0", VIDEO_IG_RETRY_MS: "0" }, now: NOW, state: SV.readState("/yoxdur", NOW), fetch: m5.f, log: s => logs5.push(s) })).posted, ["instagram"]);
  assert.equal(m5.calls.filter(c => /\/1784\/media$/.test(c.url)).length, 2, "ikinci cəhd yeni konteynerlə");
  assert.ok(logs5.some(s => /yeni konteynerlə təkrar/.test(s)));
  const m6 = meta({ fail: { igUpload: 2 } });
  assert.deepEqual(await SV.paylas({ dir, env: { ...ENV, VIDEO_FACEBOOK: "0", VIDEO_IG_RETRY_MS: "0" }, now: NOW, state: SV.readState("/yoxdur", NOW), fetch: m6.f, log: () => {} }), { posted: [], failed: ["instagram"] });
  assert.equal(m6.calls.filter(c => c.url.includes("/ig-api-upload/")).length, 2, "ən çox iki cəhd");
  const m4 = meta({ igAccount: "" });
  assert.deepEqual(await SV.paylas({ dir, env: { ...ENV, VIDEO_FACEBOOK: "0" }, now: NOW, state: SV.readState("/yoxdur", NOW), fetch: m4.f, log: () => {} }), { posted: [], failed: [] });
});

test("sosial-video: one network failing does not stop the other; tokens never reach the log; no key — no network", async () => {
  const { dir } = readyDir(), { f } = meta({ fail: { fbStart: true } }), logs = [];
  const r = await SV.paylas({ dir, env: ENV, now: NOW, state: SV.readState("/yoxdur", NOW), fetch: f, log: s => logs.push(s) });
  assert.deepEqual(r, { posted: ["instagram"], failed: ["facebook"] });
  assert.ok(logs.some(s => /facebook: video alınmadı — başlanğıc: .*no permission \*\*\*/.test(s)), logs.join("\n"));
  assert.ok(!logs.join("\n").includes("PAGEtoken123456") && !logs.join("\n").includes("EAAuserTOKEN123456"));
  assert.deepEqual(SV.networks({}), []);
  assert.deepEqual(SV.networks({ FB_PAGE_ID: "1", FB_PAGE_TOKEN: "t", INSTAGRAM: "0" }).map(n => n.name), ["facebook"], "INSTAGRAM=0 videonu da söndürür");
});

test("sosial-video: the news job starts the video workflow every 30 minutes (its cron never fired, 2026-11-22), never twice at once, dispatch only", () => {
  const sh = read(".github/scripts/pipeline.sh");
  const at = sh.indexOf("video_loop() {"), loop = sh.slice(at, sh.indexOf("\n}\n", at));
  assert.ok(at > 0 && loop.includes("- 1020) / 1800 ))"), "30 dəqiqəlik pəncərə, :17 və :47");
  assert.ok(loop.includes("gh_t workflow run sosial-video.yml --ref main") && loop.includes('select(.status != "completed"') && loop.includes("--branch main"),
    "yalnız dispatch, main-də gedən iş varsa yox");
  // Dövrə hər saat yenidən başlayır (yaddaşı sıfır): pəncərədə artıq başlamış iş də sayılır (2026-11-23: 04:17 və 04:36).
  assert.ok(loop.includes("start=$(( slot * 1800 + 1020 ))") && loop.includes("(.createdAt | fromdateiso8601) >= '\"$start\"'"),
    "eyni pəncərədə ikinci iş yoxdur");
  assert.ok(!/GEMINI|PIXABAY|FB_PAGE|curl |node |python/.test(loop), "açar və şəbəkə işi bu döngüdə yoxdur");
  assert.ok(sh.includes("video_loop &\nVIDEO_PID=$!") && sh.includes('kill "$VIDEO_PID"'));
});

test("sosial-video.yml: separate, read-only workflow; secrets only in the posting step; PR runs render a sample and never post", () => {
  const wf = read(".github/workflows/sosial-video.yml");
  assert.match(wf, /^permissions:\n  contents: read$/m);
  assert.ok(!/contents: write|git push|pages: write/.test(wf), "repoya və sayta yazmır");
  assert.equal(wf.match(/secrets\.FB_PAGE_TOKEN/g).length, 2, "açar yalnız «Paylaş» addımında (seçim yalnız var/yox bilir)");
  const post = wf.slice(wf.indexOf("- name: Paylaş"), wf.indexOf("- name: Siyahını saxla"));
  assert.match(post, /github\.event_name != 'pull_request'/);
  assert.match(post, /FB_PAGE_TOKEN: \$\{\{ secrets\.FB_PAGE_TOKEN \}\}/);
  assert.match(wf, /numune tests\/fixtures\/video-xeber\.json video-out/);
  assert.match(wf, /fonts-roboto-unhinted/);
  assert.match(wf, /retention-days: 3/);
  assert.match(wf, /timeout-minutes: 25/);
  assert.match(wf, /moov əvvəldə deyil/, "faststart yoxlanır");
  // Sürətli dövrəyə (update.yml/pipeline.sh) toxunmur: video işi oradan çağırılmır. Yeganə istisna — ayrıca fon döngüsü video_loop,
  // o yalnız iş axınını dispatch edir (cron işləmədi, 2026-11-22; yuxarıdakı test). Ondan başqa heç bir yerdə ad çəkilmir.
  const sh = read(".github/scripts/pipeline.sh"), at = sh.indexOf("video_loop() {"), note = sh.lastIndexOf("\n# Video xəbər (sosial-video.yml", at);
  assert.ok(note > 0 && at - note < 1200, "döngünün şərhi düz onun üstündədir");
  const rest = sh.slice(0, note) + sh.slice(sh.indexOf("\n}\n", at)).replace("video_loop &\nVIDEO_PID=$!", "");
  assert.ok(!/sosial-video|video-xeber|video_ses|ffmpeg/.test(rest + read(".github/workflows/update.yml")));
  assert.match(read("docs/sosial-video.md"), /## Sahibin əlavə etməli olduğu icazələr/);
});

// --- Gündəlik hava videosu (video-hava.cjs; sahib, 2026-11-23) -------------------------------------------------------------
const HAVA = JSON.parse(read("tests/fixtures/video-hava.json"));
const APP = require("../.github/scripts/topics.cjs").loadApp(root);
const baku = (d, hm) => Date.parse(`${d}T${hm}:00+04:00`);
const omFetch = (ok = true) => async url => (/api\.open-meteo\.com\/v1\/forecast/.test(url)
  ? (ok ? { ok: true, status: 200, json: async () => HAVA.response } : { ok: false, status: 503, json: async () => ({}) })
  : { ok: false, status: 404, text: async () => "", json: async () => ({}) });

test("sosial-video: the weather video has its own slot — first window after 20:45 Baku, once a day, not counted as a news video (owner-tunable)", () => {
  const ho = SV.havaOptions({});
  assert.deepEqual(ho, { on: true, from: 20 * 60 + 45, to: 23 });
  assert.deepEqual(SV.havaOptions({ HAVA_VAXT: "19:15", VIDEO_SAAT: "8-22" }), { on: true, from: 19 * 60 + 15, to: 22 });
  assert.equal(SV.havaOptions({ HAVA_VAXT: "25:99" }).from, 20 * 60 + 45, "yanlış dəyər — standart");
  const st = SV.readState("/yoxdur", NOW);
  assert.match(SV.havaDue(st, baku("2026-11-24", "20:17"), ho), /20:45–23:59 arası/, "20:17 pəncərəsi xəbərindir");
  assert.equal(SV.havaDue(st, baku("2026-11-24", "20:47"), ho), "", "20:47 pəncərəsi (pipeline.sh :17/:47)");
  assert.equal(SV.havaDue(st, baku("2026-11-24", "23:47"), ho), "", "alınmasa gecəyə qədər hər pəncərədə yenidən");
  assert.match(SV.havaDue(st, baku("2026-11-25", "00:17"), ho), /arası/);
  assert.match(SV.havaDue({ ...st, hava: { "2026-11-24": 1 } }, baku("2026-11-24", "21:17"), ho), /bu günün hava videosu hazırlanıb/);
  assert.match(SV.havaDue(st, baku("2026-11-24", "21:17"), SV.havaOptions({ HAVA_VIDEO: "0" })), /söndürülüb/);
  // Xəbər videosunun fasiləsi və gündəlik həddi hava videosunu saymır.
  assert.equal(SV.due({ ...st, hava: { "2026-11-24": baku("2026-11-24", "20:47") / 1000 } }, baku("2026-11-24", "21:17"), SV.options({})), "");
  assert.deepEqual(SV.bakuClock(Date.parse("2026-11-24T20:30:00Z")), { day: "2026-11-25", min: 30, h: 0 }, "Bakı günü UTC+4 ilə");
});

test("sosial-video: in its window the run makes the weather video (the news waits one window); Open-Meteo down — the news goes", async () => {
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), "svh-")), out = path.join(dir, "out.txt"), old = process.env.GITHUB_OUTPUT;
  process.env.GITHUB_OUTPUT = out;
  try {
    const now = Date.parse(HAVA.now), env = { VIDEO_ACAR: "1", HAVA_WAIT_MS: "0" }, logs = [];
    const st = SV.readState("/yoxdur", now), last = st._last;
    const x = await SV.sec({ articles: [], env, now, state: st, fetch: omFetch(), cats, dir, app: APP, policy: a => APP.policyViolation(a), log: s => logs.push(s) });
    assert.equal(x.tur, "hava"); assert.equal(x.id, "hava-2026-11-25");
    assert.equal(fs.readFileSync(out, "utf8"), "hazir=1\ntur=hava\n");
    const saved = JSON.parse(fs.readFileSync(path.join(dir, "xeber.json"), "utf8"));
    assert.equal(saved.title, "Hava proqnozu, 25 noyabr: Bakıda güclü külək, +7°…+14°");
    assert.equal(saved.link, "https://8ulduz.az/bolme/hava/");
    assert.ok(!saved.klipler, "görüntü açarı yoxdur — brend fonu");
    assert.equal(st.hava["2026-11-24"], now / 1000, "gündə bir: seçim günü sayır");
    assert.equal(st._last, last, "xəbər videosunun fasiləsi dəyişmir");
    assert.deepEqual(st.v, {});
    // Eyni gün yenidən: hava yox, xəbər yolu (lent boşdur).
    fs.writeFileSync(out, "");
    assert.equal(await SV.sec({ articles: [], env, now: now + 30 * 60e3, state: st, fetch: omFetch(), cats, dir, app: APP, log: s => logs.push(s) }), null);
    assert.ok(logs.some(s => /bu günün hava videosu hazırlanıb/.test(s)) && logs.some(s => /uyğun xəbər yoxdur/.test(s)));
    // Open-Meteo cavab vermir: xəbərdarlıq, gün sayılmır (növbəti pəncərədə yenidən), bu pəncərədə xəbər yolu.
    const st2 = SV.readState("/yoxdur", now), logs2 = [];
    assert.equal(await SV.sec({ articles: [], env, now, state: st2, fetch: omFetch(false), cats, dir, app: APP, log: s => logs2.push(s) }), null);
    assert.ok(logs2.some(s => /::warning::hava videosu alınmadı — Open-Meteo cavab vermədi \(HTTP 503\)/.test(s)), logs2.join("\n"));
    assert.ok(!st2.hava["2026-11-24"] && logs2.some(s => /uyğun xəbər yoxdur/.test(s)));
    // Əl ilə: tur=hava — vaxt gözləmədən (önizləmə, siyahıya yazmır); tur=xeber — pəncərədə də yalnız xəbər.
    const st3 = SV.readState("/yoxdur", NOW);
    const y = await SV.sec({ articles: [], env: { VIDEO_PAYLAS: "0", VIDEO_TUR: "hava", HAVA_WAIT_MS: "0" }, now: baku("2026-11-24", "12:00"), state: st3, fetch: omFetch(), cats, dir, app: APP, log: () => {} });
    assert.equal(y.tur, "hava"); assert.deepEqual(st3.hava, {});
    const logs4 = [];
    assert.equal(await SV.sec({ articles: [], env: { ...env, VIDEO_TUR: "xeber" }, now, state: SV.readState("/yoxdur", now), fetch: omFetch(), cats, dir, app: APP, log: s => logs4.push(s) }), null);
    assert.ok(!logs4.some(s => /hava/.test(s)));
    // Paylaşma rejimində əl ilə ikinci dəfə (eyni gün) — getmir.
    const logs5 = [];
    assert.equal(await SV.sec({ articles: [], env: { ...env, VIDEO_TUR: "hava" }, now, state: st, fetch: omFetch(), cats, dir, app: APP, log: s => logs5.push(s) }), null);
    assert.ok(logs5.some(s => /artıq paylaşılıb/.test(s)));
  } finally {
    if (old === undefined) delete process.env.GITHUB_OUTPUT; else process.env.GITHUB_OUTPUT = old;
  }
});

test("sosial-video: weather post text — the weather page link, Open-Meteo CC BY 4.0 credit, footage credit, weather tags; kept out of the news list", async () => {
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), "svhp-"));
  await SV.havaHazirla({ raw: HAVA.response, app: APP, now: Date.parse(HAVA.now), state: SV.readState("/yoxdur", NOW), env: {}, dir, post: false, footage: false, log: () => {} });
  const x = { ...JSON.parse(fs.readFileSync(path.join(dir, "xeber.json"), "utf8")), goruntu: [{ p: "Pixabay", id: 1 }], goruntuMenbe: "Pixabay" };
  fs.writeFileSync(path.join(dir, "xeber.json"), JSON.stringify(x));
  fs.writeFileSync(path.join(dir, "video.mp4"), Buffer.alloc(4321, 7));
  fs.writeFileSync(path.join(dir, "video.json"), JSON.stringify({ cover_s: 1.5 }));
  const fb = SV.fbText(x), ig = SV.igText(x);
  // Abunə çağırışı (sahib, 2026-11-25): keçid sətrindən sonra, növün vədi ilə; Instagram-da @ad, Facebook-da «səhifəmizi izləyin».
  assert.ok(fb.includes("Hava proqnozu hər gün — səhifəmizi izləyin.") && ig.includes("Hava proqnozu hər gün — abunə olun: @8ulduz.az"));
  assert.ok(fb.startsWith(`${x.title}\n\nSabah, 25 noyabr, çərşənbə, hava belə olacaq.`));
  assert.ok(fb.includes("\n\nƏtraflı: https://8ulduz.az/bolme/hava/\n\n"), "Facebook: keçid mətndədir");
  for (const t of [fb, ig]) {
    assert.ok(t.includes("Hava məlumatı: Open-Meteo.com, model proqnozu (CC BY 4.0). Rəsmi proqnozu Milli Hidrometeorologiya Xidməti verir.\nGörüntü: Pixabay"));
    assert.ok(/#havaproqnozu #hava #Bakı #8ulduz #Azərbaycan( #video)?$/.test(t), t.slice(-80));
    assert.ok(!t.includes("#xəbərlər"));
  }
  assert.ok(ig.includes("Ətraflı: 8ulduz.az (keçid profildədir)") && !/https?:\/\//.test(ig), "Instagram-da keçid basılmır");
  const { f, calls } = meta(), state = SV.readState("/yoxdur", NOW);
  const r = await SV.paylas({ dir, env: ENV, now: Date.parse(HAVA.now), state, fetch: f, log: () => {} });
  assert.deepEqual(r, { posted: ["facebook", "instagram"], failed: [] });
  assert.equal(calls.find(c => c.body?.upload_phase === "finish").body.description, fb);
  assert.ok(state.facebook["hava-2026-11-25"] && state.instagram["hava-2026-11-25"]);
  assert.deepEqual([state.v, state.t, state.topics], [{}, {}, []], "xəbər videosunun siyahısına (fasilə, hədd, mövzu) düşmür");
  assert.equal(state.hava["2026-11-24"], Date.parse(HAVA.now) / 1000);
});

test("sosial-video.yml: the weather video — PR renders both samples; same check, artifact and TikTok/YouTube jobs; previews never write the list", () => {
  const wf = read(".github/workflows/sosial-video.yml");
  // 2026-11-24: üçüncü nümunə — maraqlı video (video-maraqli.cjs; sahib: «əsas odur onlar kimi sən də tap o cür maraqlı videolar»).
  assert.ok(wf.includes(`tur: \${{ fromJSON(github.event_name == 'pull_request' && '["xeber","hava","maraqli"]' || '["avto"]') }}`));
  assert.match(wf, /numune-maraqli tests\/fixtures\/video-maraqli\.json video-out/);
  assert.ok(/            \.github\/scripts\/video-maraqli\.cjs\n/.test(wf) && /            tests\/fixtures\/video-maraqli\.json\n/.test(wf), "sparse-checkout: maraqlı");
  assert.ok(/      - \.github\/scripts\/video-maraqli\.cjs\n/.test(wf) && /      - tests\/fixtures\/video-maraqli\.json\n/.test(wf), "PR yolları: maraqlı");
  assert.match(wf, /m\.kind !== "maraqli"/, "maraqlı videonun müqaviləsi yoxlanır");
  assert.ok(wf.includes("MARAQLI_GUNDE: ${{ vars.MARAQLI_GUNDE }}") && wf.includes("MARAQLI_VIDEO: ${{ vars.MARAQLI_VIDEO }}"));
  assert.match(wf, /numune-hava tests\/fixtures\/video-hava\.json video-out/);
  assert.match(wf, /node \.github\/scripts\/video-hava\.cjs video-out\/xeber\.json video-out\/video\.mp4/);
  assert.ok(/            \.github\/scripts\/video-hava\.cjs\n/.test(wf) && /            tests\/fixtures\/video-hava\.json\n/.test(wf), "sparse-checkout");
  assert.ok(/      - \.github\/scripts\/video-hava\.cjs\n/.test(wf) && /      - tests\/fixtures\/video-hava\.json\n/.test(wf), "PR yolları");
  assert.match(wf, /options: \[avtomatik, hava, xeber, maraqli\]/);
  assert.ok(wf.includes("name: ${{ matrix.tur == 'avto' && 'video-xeber' || format('video-{0}', matrix.tur) }}"), "main-də artefakt video-xeber (tiktok.yml, youtube.yml)");
  assert.equal((wf.match(/artifact: video-xeber/g) || []).length, 2);
  assert.ok(wf.includes("OPEN_METEO_API_KEY: ${{ secrets.OPEN_METEO_API_KEY }}"));
  assert.match(wf, /m\.kind !== "hava"/, "hava videosunun müqaviləsi yoxlanır");
  // Önizləmə öz növbəsində: paylaşmanı gözlətmir; siyahını yazmır.
  assert.ok(wf.includes("group: sosial-video-${{ (github.event_name == 'pull_request' || (github.event_name == 'workflow_dispatch' && !inputs.paylas)) && github.ref || 'main' }}"));
  assert.ok(wf.slice(wf.indexOf("- name: Siyahını saxla")).includes("        if: always() && github.event_name != 'pull_request' && (github.event_name != 'workflow_dispatch' || inputs.paylas)\n"));
  // Pəncərə qaydası (PR 303) dəyişmir: hava videosu eyni dispatch-lə, ayrıca döngü yoxdur.
  assert.ok(!/hava/i.test(read(".github/scripts/pipeline.sh").match(/video_loop\(\) \{[\s\S]*?\n\}\n/)[0]));
});

// Sahib 2026-11-25: «8ulduz videolarında başlıq oxunmamalı idi». Xəbər və maraqlı videoda (prepare: quietHead) başlıq yalnız ekrandadır;
// hava videosunun birinci hissəsi başlıq deyil, giriş cümləsidir («Sabah, … hava belə olacaq.») — o, əvvəlki kimi oxunur.
test("video: the headline is shown, never voiced; the weather video's spoken intro keeps its place", () => {
  const p = V.prepare(fixture, { cats });
  const parts = p.say.map((_, i) => [i * 2, i * 2 + 1.8]);
  const tl = V.timeline(p, { parts });
  assert.equal(tl.chunks.length, p.chunks.length, "hər altyazının öz səsi var, başlığa səs hissəsi ayrılmır");
  const a = V.ass(p, tl);
  assert.ok(a.split("\n").some(l => /^Dialogue: 3,0:00:00\.00,/.test(l) && l.includes(p.head.lines[0])), "başlıq birinci kadrdan ekrandadır");
  const hava = { say: ["Sabah, 26 noyabr, cümə axşamı, hava belə olacaq.", "Bakıda hava buludlu olacaq.", "Ətraflı."], chunks: ["Bakıda hava buludlu olacaq."] };
  const th = V.timeline(hava, { parts: [[0, 3], [3, 5], [5, 7]] });
  assert.deepEqual(th.head, [0.35, 3.35], "hava videosu: giriş cümləsi oxunur (başlıq deyil)");
  assert.equal(th.lead, 0.35);
  assert.deepEqual(th.chunks[0].at, [3.35, 5.35]);
  const src = read(".github/scripts/video-ssenari.cjs");
  assert.ok(src.includes("başlıq ekranda yazılır, oxunmur") && !src.includes("ayrıca oxunur"), "diktor mətni başlığın oxunduğunu güman etmir");
});
