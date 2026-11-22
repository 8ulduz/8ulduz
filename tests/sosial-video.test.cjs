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
  assert.deepEqual(p.say[0], fixture.title, "səs başlıqla başlayır");
  assert.match(p.say.at(-1), /səkkiz ulduz nöqtə az/, "sonda sayt adı səslənir");
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

test("video: timing — reading speed without voice, the voice's own timing with it, never longer than 59 s", () => {
  const p = V.prepare(fixture, { cats });
  const t = V.timeline(p, null);
  assert.ok(t.duration >= V.MIN_S && t.duration <= V.MAX_S, String(t.duration));
  assert.equal(t.chunks.length, p.chunks.length);
  for (let i = 1; i < t.chunks.length; i++) assert.ok(t.chunks[i].at[0] >= t.chunks[i - 1].at[1], "altyazılar üst-üstə düşmür");
  assert.ok(t.chunks.every(c => c.at[1] - c.at[0] >= 2.4), "hər altyazı oxunacaq qədər qalır");
  assert.ok(t.outro[0] >= t.chunks.at(-1).at[1] && t.duration >= t.outro[1]);
  // Səsli: hissələrin vaxtı səs faylından, 0,35 s gecikmə ilə.
  const parts = p.say.map((_, i) => [i * 3, i * 3 + 2.5]);
  const tv = V.timeline(p, { parts });
  assert.deepEqual(tv.head, [0.35, 2.85]);
  assert.deepEqual(tv.chunks[0].at, [3.35, 5.85]);
  assert.equal(tv.voiceCut.outroFrom, 0.35 + (p.say.length - 1) * 3);
  // Çox uzun səs: sondakı altyazılar düşür, sonluq qalır, video ≤ 59 s.
  const slow = V.timeline(p, { parts: p.say.map((_, i) => [i * 14, i * 14 + 13]) });
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
  assert.ok(ev.some(l => /8ulduz\{\\1c&HFFFFFF&\}\.az$/.test(l)), "sonluqda böyük «8ulduz.az»");
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
  assert.match(a[a.indexOf("-filter_complex") + 1], /adelay=350:all=1/, "səs 0,35 s sonra başlayır (başlıq görünəndə)");
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

test("sosial-video: when a video goes — Baku day hours, 2 hours apart, at most 8 a day (all owner-tunable)", () => {
  const opt = SV.options({});
  assert.deepEqual(opt, { minSources: 4, maxAgeH: 3, gapMin: 120, perDay: 8, from: 8, to: 23 });
  assert.deepEqual(SV.options({ VIDEO_SAAT: "7-22", VIDEO_MIN_GAP_MIN: "90", VIDEO_GUNDE: "12", SOCIAL_MIN_SOURCES: "3" }), { minSources: 3, maxAgeH: 3, gapMin: 90, perDay: 12, from: 7, to: 22 });
  const st = SV.readState("/yoxdur", NOW);
  assert.equal(SV.due(st, NOW, opt), "");
  assert.match(SV.due(st, Date.parse("2026-11-22T01:00:00Z"), opt), /Bakı vaxtı 5:00/, "gecə video getmir");
  assert.match(SV.due({ ...st, _last: NOW / 1000 - 30 * 60 }, NOW, opt), /30 dəq əvvəl, növbəti 90 dəq/);
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
  assert.ok(loop.includes("gh_t workflow run sosial-video.yml --ref main") && loop.includes('select(.status != "completed")') && loop.includes("--branch main"),
    "yalnız dispatch, main-də gedən iş varsa yox");
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
