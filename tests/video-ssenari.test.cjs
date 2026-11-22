// Video xəbərin ssenarisi və görüntüsü (sahib, 2026-11-22: «Xəbər uzun olsun biraz və videogörüntü olsun o xəbərə uyğun»):
// .github/scripts/video-ssenari.cjs (Gemini mətni, Pexels klipləri) və video-xeber.cjs-in görüntülü rejimi. Şəbəkə saxtadır.
const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("fs"), path = require("path"), os = require("os");
const VS = require("../.github/scripts/video-ssenari.cjs");
const V = require("../.github/scripts/video-xeber.cjs");
const SV = require("../.github/scripts/sosial-video.cjs");
const root = path.join(__dirname, "..");
const fixture = JSON.parse(fs.readFileSync(path.join(root, "tests/fixtures/video-xeber.json"), "utf8"));
const cats = [{ slug: "cemiyyet", label: "Cəmiyyət" }, { slug: "gundem", label: "Gündəm" }];
const quiet = () => {};

const SOURCE = "Bakıda 12 yeni məktəb binası istifadəyə verilib. Layihəyə 45,5 milyon manat ayrılıb. Məktəblərdə 3600 şagird təhsil alacaq. "
  + "Binalarda idman zalı, kitabxana və laboratoriyalar var. Tikinti işləri 2025-ci ildə başlayıb və plana uyğun bitib.";
const GOOD = "Bakıda 12 yeni məktəb binası istifadəyə verilib. Layihəyə 45,5 milyon manat vəsait ayrılıb. Yeni məktəblərdə 3600 şagird "
  + "təhsil alacaq. Hər binada idman zalı, kitabxana və laboratoriyalar yaradılıb. Tikinti işlərinə 2025-ci ildə başlanılıb və işlər plana uyğun "
  + "başa çatdırılıb. Məktəblərin həyətləri də abadlaşdırılıb və yaşıllıq zolaqları salınıb. Məktəblər yeni tədris ilindən fəaliyyət göstərəcək.";

test("ssenari: the narration is checked — every number from the source, no Cyrillic, links, exclamations, relative days, site rule", () => {
  const a = { title: "Bakıda yeni məktəblər açılıb", category: "cemiyyet" };
  assert.equal(VS.checkText(GOOD, SOURCE, a), "");
  assert.match(VS.checkText(GOOD.replace("3600", "4200"), SOURCE, a), /mənbədə olmayan rəqəm: 4200/);
  assert.match(VS.checkText(GOOD + " Это тест.", SOURCE, a), /kiril/);
  // Lite modellər «ə» yerinə kiril «ә» yazır: oxşar hərflər latına çevrilir, əsl kiril sözü qalır və düşür.
  assert.equal(VS.latin("Bakıda yeni mәktәb binası, Әliyev"), "Bakıda yeni məktəb binası, Əliyev");
  assert.match(VS.checkText(VS.latin(GOOD + " Это тест."), SOURCE, a), /kiril/);
  assert.match(VS.checkText(GOOD.replace("ayrılıb.", "ayrılıb!"), SOURCE, a), /nida/);
  assert.match(VS.checkText(GOOD.replace("Bakıda", "Bu gün Bakıda"), SOURCE, a), /nisbi gün/);
  assert.match(VS.checkText("Qısa mətn.", SOURCE, a), /uzunluq/);
  // Sahib: «4-7 cümlədə olsun. uzun da olsun» — 3 uzun cümlə qəbul olunmur.
  const long = "Bakıda yeni məktəb binaları istifadəyə verilib və binalarda idman zalı, kitabxana, laboratoriyalar, geniş sinif otaqları yaradılıb";
  const three = `${long}. ${long}, həyətlər də abadlaşdırılıb və yaşıllıq zolaqları salınıb. ${long}, məktəblər yeni tədris ilindən fəaliyyət göstərəcək.`;
  assert.match(VS.checkText(three, SOURCE, a), /cümlə sayı 3/);
  assert.match(VS.checkText(GOOD, SOURCE, a, () => "qadağan"), /qaydasından keçmir/);
  assert.equal(VS.checkText(GOOD.replace("3600", "3 600").replace("45,5", "45.5"), SOURCE.replace("3600", "3 600"), a), "", "minlik boşluğu və onluq vergül/nöqtə eyni rəqəmdir");
  // 2026-11-22 nümunə videosu: «Cey. Di. Vensin» altyazıda üç hissəyə bölündü, «Di.» ekranda tək qaldı.
  assert.match(VS.checkText(GOOD.replace("Məktəblər yeni", "Cey. Di. Vens bildirib ki, məktəblər yeni"), SOURCE, a), /inisial/);
  assert.equal(VS.checkText(GOOD.replace("Məktəblər yeni", "ABŞ vitse-prezidenti Vens bildirib ki, məktəblər yeni"), SOURCE, a), "");
});

test("video: protocol news (receptions, meetings, phone calls, congratulations) never becomes a stock-footage video", () => {
  assert.ok(VS.protokol({ title: "İlham Əliyev ABŞ-nin daxili təhlükəsizlik nazirini qəbul edib", category: "siyaset" }));
  assert.ok(VS.protokol({ title: "Ceyhun Bayramov fransalı həmkarı ilə telefon danışığı aparıb", category: "siyaset" }));
  assert.ok(VS.protokol({ title: "Dövlət başçısı Türkiyə Prezidentini təbrik edib", category: "dunya" }));
  assert.ok(VS.protokol({ title: "Bakıda yeni yol açılıb", category: "prezident" }), "Prezident bölməsi");
  assert.ok(!VS.protokol({ title: "Bakıda 12 yeni məktəb açılıb", category: "cemiyyet" }));
  assert.ok(!VS.protokol({ title: "Rusiya Ukraynanın enerji obyektlərinə dron hücumu edib", category: "dunya" }));
  assert.match(VS.PROMPT, /"uygun": false YALNIZ xəbər protokol/, "Gemini də yoxlayır, yalnız protokolu rədd edir (lite model cinayət xəbərini də rədd edirdi)");
  assert.match(VS.PROMPT, /Şübhə olanda true/);
  assert.doesNotMatch(VS.PROMPT, /məsələn[^\n]*national flags/, "adsız bayraqlar yad ölkəni göstərə bilər");
  assert.ok(!Object.values(VS.EHTIYAT).flat().some(q => /national flags/.test(q)));
});

test("ssenari: Gemini writes the script (key in a header, never in the URL); a bad answer skips the story, no key → null", async () => {
  const calls = [];
  const fake = answer => async (u, o = {}) => {
    calls.push({ u, o });
    if (/models\?pageSize/.test(u)) return { ok: true, status: 200, json: async () => ({ models: [
      { name: "models/gemini-3.6-flash", supportedGenerationMethods: ["generateContent"] },
      { name: "models/gemini-3.6-flash-lite", supportedGenerationMethods: ["generateContent"] },
      { name: "models/gemini-3.5-flash", supportedGenerationMethods: ["generateContent"] }] }) };
    return { ok: true, status: 200, json: async () => ({ candidates: [{ content: { parts: [{ text: answer }] } }] }) };
  };
  const a = { title: "Bakıda yeni məktəblər açılıb", category: "cemiyyet", summary: SOURCE };
  const page = `<html><body>${SOURCE.split(". ").map(s => `<p>${s}. Bu abzas mənbənin tam mətnidir.</p>`).join("")}</body></html>`;
  const env = { GEMINI_API_KEY: "gizli-acar-123" };
  const ok = await VS.ssenari(a, page, { env, fetch: fake(JSON.stringify({ text: GOOD, axtar: ["School building", "Baku city skyline", "Бакy", "a", "classroom desks"] })), log: quiet });
  assert.equal(ok.text, GOOD);
  assert.deepEqual(ok.axtar, ["school building", "baku city skyline", "classroom desks"], "yalnız latın, 2+ hərf, kiçik hərflə");
  const gen = calls.find(c => /:generateContent$/.test(c.u));
  assert.match(gen.u, /gemini-3\.6-flash:generateContent$/, "ən yeni flash (lite yox)");
  assert.equal(gen.o.headers["x-goog-api-key"], "gizli-acar-123");
  assert.ok(!calls.some(c => c.u.includes("gizli-acar-123")), "açar ünvanda yoxdur");
  assert.match(JSON.parse(gen.o.body).contents[0].parts[0].text, /Mənbə mətni:\n[\s\S]*3600 şagird/, "Gemini-yə mənbənin mətni gedir");
  // Uydurma rəqəm, JSON olmayan cavab: bu xəbərdən video olmur (başqa xəbər). Açarsız: null (Gemini yoxdur).
  const bad = await VS.ssenari(a, page, { env, fetch: fake(JSON.stringify({ text: GOOD.replace("3600", "9999") })), log: quiet });
  assert.equal(bad.uygun, false);
  assert.match(bad.sebeb, /9999/);
  assert.equal((await VS.ssenari(a, page, { env, fetch: fake("bağışlayın"), log: quiet })).uygun, false);
  assert.equal(await VS.ssenari(a, page, { env: {}, fetch: () => { throw new Error("şəbəkə olmamalı idi"); }, log: quiet }), null);
});

test("ssenari: a daily-quota 429 moves on to the next model at once; flash-lite models are the reserve; no answer at all → null", async () => {
  const daily = { error: { code: 429, status: "RESOURCE_EXHAUSTED", details: [{ "@type": "type.googleapis.com/google.rpc.QuotaFailure",
    violations: [{ quotaId: "GenerateRequestsPerDayPerProjectPerModel-FreeTier", quotaValue: "20" }] }] } };
  const calls = [], logs = [];
  const fake = liteWorks => async (u) => {
    if (/models\?pageSize/.test(u)) return { ok: true, status: 200, json: async () => ({ models: ["gemini-3.8-flash", "gemini-3.7-flash", "gemini-3.6-flash", "gemini-3.5-flash",
      "gemini-3.8-flash-lite", "gemini-3.6-flash-lite", "gemini-3.5-flash-lite"].map(n => ({ name: `models/${n}`, supportedGenerationMethods: ["generateContent"] })) }) };
    const model = u.match(/models\/([^:]+):/)[1];
    calls.push(model);
    if (!/lite/.test(model) || !liteWorks) return { ok: false, status: 429, json: async () => daily };
    return { ok: true, status: 200, json: async () => ({ candidates: [{ content: { parts: [{ text: JSON.stringify({ uygun: true, text: GOOD, axtar: ["school building"] }) }] } }] }) };
  };
  const a = { title: "Bakıda yeni məktəblər açılıb", category: "cemiyyet", summary: SOURCE };
  const page = `<html><body>${SOURCE.split(". ").map(s => `<p>${s}. Bu abzas mənbənin tam mətnidir.</p>`).join("")}</body></html>`;
  const env = { GEMINI_API_KEY: "k", VIDEO_GEMINI_WAIT_MS: "0" };
  const ok = await VS.ssenari(a, page, { env, fetch: fake(true), log: quiet });
  assert.equal(ok.text, GOOD);
  assert.deepEqual(calls, ["gemini-3.8-flash", "gemini-3.7-flash", "gemini-3.6-flash", "gemini-3.8-flash-lite"],
    "gündəlik limitdə eyni model təkrar soruşulmur; 3 flash, sonra lite");
  calls.length = 0;
  assert.equal(await VS.ssenari(a, page, { env, fetch: fake(false), log: s => logs.push(s) }), null, "heç bir model cavab vermədi");
  assert.equal(calls.length, 5, "3 flash + 2 lite, hərəsinə bir sorğu");
  assert.match(logs.join("\n"), /429 günlük limit 20/);
});

test("goruntu: Pexels clips matching the story — portrait first, landscape if none, one clip per query, files saved, key in a header", async () => {
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), "klip-"));
  const vid = (id, w, h, extra = {}) => ({ id, duration: 12, user: { name: `Müəllif ${id}` }, video_files: [
    { link: `https://videos.pexels.com/${id}-sd.mp4`, file_type: "video/mp4", width: Math.round(w / 2), height: Math.round(h / 2) },
    { link: `https://videos.pexels.com/${id}-hd.mp4`, file_type: "video/mp4", width: w, height: h }], ...extra });
  const seen = [];
  const f = async (u, o = {}) => {
    seen.push({ u, o });
    if (u.startsWith("https://api.pexels.com/videos/search")) {
      const q = new URL(u).searchParams;
      if (q.get("query") === "baku city skyline" && q.get("orientation") === "portrait") return { ok: true, json: async () => ({ videos: [vid(1, 1080, 1920)] }) };
      if (q.get("query") === "school building" && q.get("orientation") === "portrait") return { ok: true, json: async () => ({ videos: [] }) };
      if (q.get("query") === "school building" && q.get("orientation") === "landscape") return { ok: true, json: async () => ({ videos: [vid(2, 1920, 1080), vid(3, 3840, 2160)] }) };
      return { ok: true, json: async () => ({ videos: [vid(100 + seen.length, 1080, 1920)] }) };
    }
    return { ok: true, arrayBuffer: async () => new Uint8Array(20000).buffer };
  };
  const got = await VS.goruntu(["baku city skyline", "school building"], dir, { env: { PEXELS_API_KEY: "pex-acar" }, fetch: f, log: quiet, say: 3, category: "cemiyyet" });
  assert.deepEqual(got.map(g => g.file), ["klip-1.mp4", "klip-2.mp4", "klip-3.mp4"]);
  assert.deepEqual(got.slice(0, 2).map(g => [g.id, g.w, g.h, g.q]), [[1, 1080, 1920, "baku city skyline"], [2, 1920, 1080, "school building"]],
    "şaquli 1080×1920; şaqulisi yoxdursa üfüqi 1080p (4K yox)");
  assert.ok(got.every(g => fs.statSync(path.join(dir, g.file)).size === 20000));
  const api = seen.filter(s => s.u.startsWith("https://api.pexels.com/"));
  assert.ok(api.every(s => s.o.headers.authorization === "pex-acar" && !s.u.includes("pex-acar")), "açar başlıqda");
  assert.deepEqual(await VS.goruntu(["x y"], dir, { env: {}, fetch: () => { throw new Error("şəbəkə olmamalı idi"); }, log: quiet }), [], "açarsız: görüntüsüz");
  fs.rmSync(dir, { recursive: true, force: true });
});

test("goruntu: Pixabay (Pexels stopped issuing keys, 2026-11-22) — relevant clips only, vertical first among equals, ≥1080 renditions, the key never reaches the log", async () => {
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), "klip-px-"));
  const hit = (id, w, h, extra = {}) => ({ id, duration: 15, user: `pxu${id}`, tags: "school, building, education", pageURL: `https://pixabay.com/videos/school-building-${id}/`, videos: {
    large: { url: `https://cdn.pixabay.com/${id}_large.mp4`, width: w * 2, height: h * 2, size: 90e6 },
    medium: { url: `https://cdn.pixabay.com/${id}_medium.mp4`, width: w, height: h, size: 8e6 },
    small: { url: `https://cdn.pixabay.com/${id}_small.mp4`, width: w / 1.5, height: h / 1.5, size: 3e6 } }, ...extra });
  const urls = [], logs = [];
  const f = async (u) => {
    urls.push(u);
    if (u.startsWith("https://pixabay.com/api/videos/")) return { ok: true, json: async () => ({ hits: [
      hit(9, 1080, 1920, { tags: "squirrel, animal, nature", pageURL: "https://pixabay.com/videos/squirrel-animal-nature-9/" }),
      hit(1, 1920, 1080), hit(2, 1080, 1920), hit(3, 1280, 720, { videos: { medium: { url: "https://cdn.pixabay.com/3_medium.mp4", width: 1280, height: 720, size: 2e6 } } })] }) };
    return { ok: true, arrayBuffer: async () => new Uint8Array(15000).buffer };
  };
  const got = await VS.goruntu(["school building"], dir, { env: { PIXABAY_API_KEY: "pxb-acar" }, fetch: f, log: s => logs.push(s), say: 2, category: "cemiyyet" });
  assert.deepEqual(got.map(g => [g.p, g.id, g.w, g.h]), [["Pixabay", 2, 1080, 1920], ["Pixabay", 1, 1920, 1080]],
    "uyğunsuz şaquli klip (dələ) atılır; uyğunlar arasında şaquli əvvəl; 1920×1080 medium (90 MB-lıq 4K yox); 720p götürülmür");
  const api = new URL(urls.find(u => u.startsWith("https://pixabay.com/api/videos/")));
  assert.equal(api.searchParams.get("safesearch"), "true");
  assert.equal(api.searchParams.get("q"), "school building");
  assert.ok(!logs.join("\n").includes("pxb-acar"), "açar jurnalda yoxdur");
  assert.equal(VS.pixabayFile({ videos: { medium: { url: "x", width: 1280, height: 720 } } }), null);
  fs.rmSync(dir, { recursive: true, force: true });
});

test("goruntu: a clip must match the query — the samples showed a squirrel for a border wall, a Japanese castle and the Empire State for the Capitol", () => {
  assert.equal(VS.relevance("us mexico border wall", "squirrel, animal, nature squirrel-animal-nature-310086"), 0);
  assert.equal(VS.relevance("washington dc capitol building", "castle, japan, osaka, building, night"), 0, "yalnız ümumi «building» bəs etmir");
  assert.equal(VS.relevance("us mexico border wall", "wall, brick, texture"), 0, "3+ sözdə bir təsadüfi söz bəs etmir");
  assert.ok(VS.relevance("us mexico border wall", "border, wall, fence, mexico") > 0);
  assert.ok(VS.relevance("washington dc capitol building", "capitol, washington, dome") > 0);
  assert.ok(VS.relevance("baku city skyline", "baku, azerbaijan, flame towers") > 0, "ilk konkret söz (yer adı) bəs edir");
  assert.ok(VS.relevance("police lights at night", "police, siren, lights") > 0, "cəm və tək eyni sözdür");
  assert.equal(VS.relevance("city street traffic", "street, cars"), 0);
  // Dördüncü nümunə: «Mexico City» etiketli dələ və Empire State binası keçmişdi — ifadənin əsas sözü («wall», «capitol») olmalıdır.
  assert.equal(VS.relevance("us mexico border wall", "nature, green, chipmunk, city, tree, animal, mammal, country, Mexico City, Mexico"), 0);
  assert.equal(VS.relevance("united states capitol", "empire state, skyline, manhattan, new york, the usa, building, america, united states"), 0);
  assert.ok(VS.relevance("united states capitol", "capitol, washington, dome") > 0, "«united states» ümumi sözdür, «capitol» bəs edir");
  assert.equal(VS.relevance("white house washington", "washington, forest, trees"), 0);
  // 2026-11-23: güllə izləri axtarışına tikinti işçisi keçmişdi (4 sözdən 2-si) — indi 3-ü lazımdır.
  assert.equal(VS.relevance("bullet holes car window", "construction, remodeling, hammer, brick, window, hole, worker, building"), 0);
  assert.ok(VS.relevance("bullet holes car window", "car, window, bullet, hole, crime") > 0);
});

test("goruntu: negative stories get people-free fallback scenes; the prompt forbids identifiable people (Pexels license)", () => {
  assert.ok(VS.ehtiyat({ category: "hadise" }).every(q => !/people|man|woman|person/.test(q)));
  assert.match(VS.PROMPT, /insansız səhnələr/);
  assert.match(VS.PROMPT, /Yalnız aşağıdakı mənbə mətnindəki faktlar/);
  assert.equal(VS.bestFile({ video_files: [{ link: "x", file_type: "video/mp4", width: 720, height: 1280 }] }, true).height, 1280);
  assert.equal(VS.bestFile({ video_files: [{ link: "x", file_type: "video/mp4", width: 640, height: 360 }] }, false), null, "çox kiçik üfüqi klip götürülmür");
});

test("video: footage mode — clips fill 9:16 behind a dark headline band, captions low, «Görüntü: Pexels» credit, inputs in the right order", () => {
  const p = V.prepare(fixture, { cats, footage: true }), t = V.timeline(p, null);
  assert.ok(p.footage && p.head.size <= 76 && p.head.lines.length * p.head.size <= V.LF.headMaxH, "başlıq kiçik zolağa sığır");
  assert.match(p.source, / · Görüntü: Pexels$/);
  const ev = V.ass(p, t).split("\n").filter(l => l.startsWith("Dialogue:"));
  assert.ok(!ev.some(l => /\\blur90/.test(l)), "görüntülü videoda süni işıq formaları yoxdur");
  assert.ok(ev.some(l => /\\pos\(0,420\)\\p1.*\\1a&H50&/.test(l)), "başlığın arxasında yarımşəffaf zolaq");
  assert.ok(ev.filter(l => /^Dialogue: 4,/.test(l)).every(l => l.includes(`\\pos(88,${V.LF.capY + 16})`)), "altyazılar aşağıda");
  for (const l of ev) {
    const m = l.match(/\\(?:pos|move)\((\d+(?:\.\d+)?),(\d+(?:\.\d+)?)/);
    if (!m || /\\p1/.test(l)) continue;
    assert.ok(+m[2] >= 300 && +m[2] <= 1480, `y=${m[2]} lentin 4:5 kəsiyində: ${l.slice(0, 80)}`);
  }
  const args = V.ffmpegArgs({ tl: t, assFile: "v.ass", logo: "L.png", voiceFile: "ses.wav", out: "o.mp4", clips: ["a.mp4", "b.mp4", "c.mp4"] });
  const inputs = args.filter((x, i) => args[i - 1] === "-i");
  // 25 s-lik nümunədə 5 kadr (başlıq + altyazılar), 3 klip: sıra ilə, sonra təkrar.
  assert.deepEqual(inputs, ["a.mp4", "b.mp4", "c.mp4", "a.mp4", "b.mp4", "L.png", "ses.wav"]);
  assert.equal(args.filter(x => x === "-stream_loop").length, 5, "qısa klip dövrə vurur");
  const fc = args[args.indexOf("-filter_complex") + 1];
  assert.match(fc, /\[0:v\][^;]*scale=1080:1920:force_original_aspect_ratio=increase[^;]*crop=1080:1920/);
  assert.match(fc, /\[c0\]\[c1\]\[c2\]\[c3\]\[c4\]concat=n=5:v=1:a=0/);
  // Ölçüsü məlum üfüqi klip kəsilmir: tam enində (1080×608) KLIP_Y-də, arxada bulanıq nüsxəsi; şaquli klip ekranı doldurur.
  const mixed = V.ffmpegArgs({ tl: t, assFile: "v.ass", logo: "L.png", voiceFile: null, out: "o.mp4",
    clips: [{ file: "a.mp4", w: 1920, h: 1080 }, { file: "b.mp4", w: 1080, h: 1920 }, "c.mp4"] });
  const mf = mixed[mixed.indexOf("-filter_complex") + 1];
  assert.deepEqual(mixed.filter((x, i) => mixed[i - 1] === "-i").slice(0, 3), ["a.mp4", "b.mp4", "c.mp4"]);
  assert.match(mf, /\[0:v\][^;]*split=2\[b0\]\[f0\];\[b0\][^;]*boxblur[^;]*\[g0\];\[f0\]scale=1080:608[^;]*\[h0\];\[g0\]\[h0\]overlay=0:740/);
  assert.ok(!/\[0:v\][^;]*crop=1080:1920/.test(mf), "üfüqi klip 9:16-ya kəsilmir");
  assert.match(mf, /\[1:v\][^;]*crop=1080:1920,setsar=1\[c1\]/);
  assert.match(mf, /\[2:v\][^;]*crop=1080:1920,setsar=1\[c2\]/, "ölçü bilinmirsə əvvəlki kimi doldurulur");
  assert.ok(V.KLIP_Y + 608 <= 1920 && V.KLIP_Y >= 732, "klip başlıq zolağının altından başlayır");
  // 3 sətirlik başlıqda zolaq uzanır: klip onun altından (2026-11-23 nümunəsində klipin üstü zolağın altında qalmışdı).
  const p3 = V.prepare({ ...fixture, title: "Qurban Qurbanov: \"Gəncədə özümüzü Avropa stadionunda hiss edirdik\"" }, { cats, footage: true });
  assert.equal(p3.head.lines.length, 3);
  const low = V.ffmpegArgs({ tl: t, assFile: "v.ass", logo: "L.png", voiceFile: null, out: "o.mp4", clips: [{ file: "a.mp4", w: 1920, h: 1080 }], clipY: Math.max(V.KLIP_Y, V.bandBottom(p3)) });
  assert.match(low[low.indexOf("-filter_complex") + 1], new RegExp(`overlay=0:${V.bandBottom(p3)},`));
  assert.ok(V.bandBottom(p3) > V.KLIP_Y && V.bandBottom(p3) + 608 <= V.LF.srcY, "klip mənbə sətrinə çatmır");
  assert.ok(V.bandBottom(V.prepare(fixture, { cats, footage: true })) <= V.KLIP_Y, "2 sətirdə əvvəlki yer");
  assert.match(fc, /\[5:v\]scale=-1:80/, "loqo kadrlardan sonrakı girişdir");
  assert.match(fc, /\[6:a\]/, "səs loqodan sonrakı girişdir");
  // Kliplər olmadan əvvəlki kimi: rəngli fon, loqo [1], səs [2].
  const plain = V.ffmpegArgs({ tl: t, assFile: "v.ass", logo: "L.png", voiceFile: null, out: "o.mp4" });
  assert.match(plain[plain.indexOf("-filter_complex") + 1], /^\[0:v\]format=rgb24,ass=v\.ass\[t\];\[1:v\]scale[\s\S]*\[2:a\]aformat/);
});

test("goruntu: clips keep the edit order; a query with no clip is never filled with a generic scene unless fewer than 3 clips; recent clips are skipped", async () => {
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), "klip-sira-"));
  const hit = (id, tags) => ({ id, duration: 15, user: `u${id}`, tags, pageURL: `https://pixabay.com/videos/x-${id}/`,
    videos: { medium: { url: `https://cdn.pixabay.com/${id}.mp4`, width: 1080, height: 1920, size: 5e6 } } });
  const db = { "oil pump jack": [hit(1, "oil, pump, jack"), hit(2, "oil, pump, jack, field")], "gas price board": [],
    "tanker ship sea": [hit(3, "tanker, ship, sea")], "business district skyline": [hit(9, "business, district, skyline")] };
  const asked = [];
  const f = async (u) => {
    if (u.startsWith("https://pixabay.com/api/videos/")) { const q = new URL(u).searchParams.get("q"); asked.push(q); return { ok: true, json: async () => ({ hits: db[q] || [] }) }; }
    return { ok: true, arrayBuffer: async () => new Uint8Array(15000).buffer };
  };
  const got = await VS.goruntu(["oil pump jack", "gas price board", "tanker ship sea"], dir,
    { env: { PIXABAY_API_KEY: "k" }, fetch: f, log: quiet, say: 3, category: "iqtisadiyyat", istifade: new Set(["Pixabay:1"]) });
  assert.deepEqual(got.map(g => [g.q, g.id]), [["oil pump jack", 2], ["tanker ship sea", 3], ["business district skyline", 9]],
    "işlənmiş klip (1) atılır; ifadələrin klipləri sıra ilə; cəmi 2 uyğun klip olduğuna görə sonda bir ümumi səhnə");
  assert.equal(asked.filter(q => q === "oil pump jack").length, 1, "ifadə bir dəfə soruşulur");
  // 3 uyğun klip varsa ümumi səhnə işlənmir (2026-11-23: Gürcüstan xəbərinin başlığına Bakı düşmüşdü), boş yer doldurulmur.
  db["oil pump jack"].push(hit(4, "oil, pump, jack, sunset"));
  const enough = await VS.goruntu(["oil pump jack", "gas price board", "tanker ship sea"], dir,
    { env: { PIXABAY_API_KEY: "k" }, fetch: f, log: quiet, say: 8, category: "iqtisadiyyat", istifade: new Set(["Pixabay:1"]) });
  assert.deepEqual(enough.map(g => g.id), [2, 3, 4], "əsas səhnənin ikinci klipi əlavə olunur, ümumi səhnə yox");
  fs.rmSync(dir, { recursive: true, force: true });
});

test("goruntu: the story's real place comes first (city always with its country), clips tagged with another country or city are never used", async () => {
  // Sahib, 2026-11-23: «həqiqi Gəncənin yeni stadionu olan videolardan istifadə etmək lazımdır. digərləri də belə».
  const P = VS.yerPlan(["Ganja City Stadium", "Ganja", "Azerbaijan"]);
  assert.deepEqual(P.axtar, ["ganja city stadium azerbaijan", "ganja azerbaijan"], "«ganja» tək axtarılmır (ingiliscədə kənafdır)");
  assert.equal(VS.yadYer("stadium, field, football, city, architecture, batumi, georgia", P.icaze), "batumi", "nümunədə Gəncə xəbərinə Batumi stadionu düşmüşdü");
  assert.equal(VS.yadYer("architecture, azerbaijan, baku, boulevard", P.icaze), "baku", "Gəncə xəbərində Bakı yox");
  assert.equal(VS.yadYer("ganja, azerbaijan, city", P.icaze), "");
  assert.equal(VS.yadYer("soccer, football, goal, stadium", P.icaze), "", "yersiz ümumi klip olar");
  assert.equal(VS.yadYer("kaohsiung city, school hall", VS.yerPlan([]).icaze), "kaohsiung", "yer bilinməsə də tanınan yad şəhər olmaz");
  assert.equal(VS.yadYer("the usa, flag, america, american", VS.yerPlan(["White House", "Washington", "United States"]).icaze), "", "eyni ölkənin adları");
  assert.ok(VS.yerPlan(["Azerbaijan"]).icaze.has("baku"), "yalnız ölkə varsa paytaxt olar");
  assert.ok(!VS.yerPlan(["Qardabani", "Georgia"]).icaze.has("tbilisi"), "kənd xəbərində paytaxt olmaz");
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), "klip-yer-"));
  const hit = (id, tags) => ({ id, duration: 15, user: `u${id}`, tags, pageURL: `https://pixabay.com/videos/x-${id}/`,
    videos: { medium: { url: `https://cdn.pixabay.com/${id}.mp4`, width: 1920, height: 1080, size: 5e6 } } });
  const db = { "ganja azerbaijan": [hit(5, "ganja, azerbaijan, city, park")], "football stadium lights": [hit(7, "stadium, football, lights, night, batumi, georgia"), hit(8, "stadium, football, lights")] };
  const asked = [];
  const f = async (u) => {
    if (u.startsWith("https://pixabay.com/api/videos/")) { const q = new URL(u).searchParams.get("q"); asked.push(q); return { ok: true, json: async () => ({ hits: db[q] || [] }) }; }
    return { ok: true, arrayBuffer: async () => new Uint8Array(15000).buffer };
  };
  const logs = [];
  const got = await VS.goruntu(["football stadium lights"], dir, { env: { PIXABAY_API_KEY: "k" }, fetch: f, log: s => logs.push(s), say: 2, category: "idman",
    yer: ["Ganja City Stadium", "Ganja", "Azerbaijan"] });
  assert.deepEqual(got.map(g => g.id), [5, 8], "əvvəl Gəncənin özü, sonra ümumi klip; Batumi atılır");
  assert.equal(asked[0], "ganja city stadium azerbaijan", "əvvəl ən dəqiq yer");
  assert.ok(logs.some(s => /başqa yer \(batumi\)/.test(s)));
  fs.rmSync(dir, { recursive: true, force: true });
});

test("hashtags: Gemini's topic tags are cleaned (no «#», spaces, Cyrillic, duplicates of the house tags) and reach every post text and video.json", () => {
  assert.deepEqual(VS.hashtags(["#futbol", "Premyer Liqa", "#Qarabağ", "8ulduz", "Футбол", "#Futbol", "x"]), ["futbol", "PremyerLiqa", "Qarabağ"]);
  assert.deepEqual(VS.hashtags("futbol"), [], "siyahı deyilsə boş");
  const x = { title: "Başlıq", text: "Mətn.", link: "https://www.8ulduz.az/a?h=1", hashtags: ["futbol", "Qarabağ"] };
  assert.match(SV.fbText(x), /#futbol #Qarabağ #8ulduz #xəbərlər #Azərbaycan$/);
  assert.match(SV.igText(x), /#futbol #Qarabağ #8ulduz #xəbərlər #Azərbaycan #video$/);
  assert.match(SV.fbText({ ...x, hashtags: undefined }), /\n\n#8ulduz #xəbərlər #Azərbaycan$/, "etiket yoxdursa əvvəlki kimi");
  assert.deepEqual(V.storyFields({ ...fixture, hashtags: ["futbol", "Qarabağ"] }).hashtags, ["futbol", "Qarabağ"], "YouTube/TikTok video.json-dan oxuyur");
  assert.equal(V.storyFields(fixture).hashtags, undefined);
  assert.match(VS.PROMPT, /"etiket"/);
});

test("video: shots cut where the narration moves on (headline, then each caption), 2.6–6.5 s each; reused clips continue from an unused part", () => {
  const t = { duration: 40, chunks: [[4, 8.5], [8.7, 10], [10.2, 16], [16.2, 25.5], [25.7, 35]].map(at => ({ text: "x", at })), outro: [35.3, 40] };
  const b = V.shotBounds(t);
  assert.ok(b.every(([s, e]) => e - s >= 2.6 - 1e-9 && e - s <= 6.5 + 1e-9), JSON.stringify(b));
  assert.deepEqual(b.slice(0, 2).map(x => x.map(v => Math.round(v * 10) / 10)), [[0, 4], [4, 10.2]], "kəsim danışığın sərhədində; 1,3 s-lik hissə əvvəlkinə birləşir");
  assert.ok(b.some(([s]) => Math.abs(s - 16.2) < 1e-6) && b.some(([s]) => Math.abs(s - 25.7) < 1e-6), "hər yeni altyazıda yeni kadr");
  const plan = V.shotPlan([{ file: "a", dur: 30 }, { file: "b", dur: 5 }, { file: "c" }], t);
  assert.ok(Math.abs(plan.reduce((x, c) => x + c.d, 0) - 40) < 0.011, "kadrlar videonu tam örtür");
  assert.deepEqual(plan.slice(0, 4).map(c => c.file), ["a", "b", "c", "a"], "kliplər sıra ilə (montaj planı)");
  assert.equal(plan[3].ss, plan[0].d, "a ikinci dəfə işlənməmiş yerindən");
  assert.equal(plan.filter(c => c.file === "b")[1]?.ss ?? 0, 0, "qısa klipdə yer qalmayıbsa əvvəldən");
  assert.equal(plan.find(c => c.file === "c").ss, 0, "uzunluğu bilinməyən klip əvvəldən");
  const args = V.ffmpegArgs({ tl: t, assFile: "v.ass", logo: "L.png", voiceFile: null, out: "o.mp4", clips: [{ file: "a.mp4", dur: 30 }] });
  const p1 = V.shotPlan([{ file: "a.mp4", dur: 30 }], t);
  assert.ok(args.join(" ").includes(`-stream_loop -1 -ss ${p1[1].ss.toFixed(2)} -t ${p1[1].d.toFixed(2)} -i a.mp4`), "ikinci kadr klipin davamından");
});

test("video: the spoken word lights up orange in the caption, then turns white again; timing follows letters, numbers and pauses", () => {
  const w = V.wordTimes("ABŞ 2026-cı ildə, Bakıda.", 1, 5);
  assert.deepEqual(w.map(x => x[0]), ["ABŞ", "2026-cı", "ildə,", "Bakıda."]);
  assert.equal(w[0][1], 1);
  assert.ok(Math.abs(w[3][2] - 5) < 1e-9, "hissənin vaxtını tam örtür");
  const len = i => w[i][2] - w[i][1];
  assert.ok(len(1) > len(3), "rəqəm sözlə oxunur, uzun çəkir");
  assert.ok(len(0) > len(2) * 0.8, "qısaltma hərf-hərf oxunur");
  const p = V.prepare(fixture, { cats, footage: true }), t = V.timeline(p, null);
  const caps = V.ass(p, t).split("\n").filter(l => l.startsWith("Dialogue: 4,"));
  assert.equal(caps.length, t.chunks.length);
  for (const [i, l] of caps.entries()) {
    const words = t.chunks[i].text.split(" ").filter(Boolean).length;
    assert.equal((l.match(/\\t\(\d+,\d+,\\1c&H0AA3F5&\)/g) || []).length, words, "hər söz bir dəfə narıncı olur");
    assert.equal((l.match(/\\t\(\d+,\d+,\\1c&HFFFFFF&\)/g) || []).length, words, "və yenə ağ olur");
  }
  assert.equal(caps[0].match(/\\t\((\d+),/)[1], "0", "ilk söz hissə başlayanda yanır");
});

test("sosial-video: the chosen story gets the Gemini script and Pexels clips in xeber.json; post texts credit Pexels", async () => {
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), "video-sec-"));
  const NOW = Date.parse("2026-11-22T10:00:00Z");
  const a = { id: "a".repeat(16), title: "Bakıda 12 yeni məktəb açılıb", summary: SOURCE, category: "cemiyyet", lang: "az", source: "APA",
    sourceUrl: "https://apa.az/x", publishedAt: new Date(NOW - 20 * 60e3).toISOString(), alts: [{ source: "Report" }, { source: "Oxu.az" }, { source: "Trend" }] };
  const page = `<html><body>${SOURCE.split(". ").map(s => `<p>${s}. Bakıda yeni məktəblər haqqında ətraflı məlumat.</p>`).join("")}</body></html>`;
  const f = async (u) => {
    if (u === a.sourceUrl) return { ok: true, text: async () => page };
    if (/models\?pageSize/.test(u)) return { ok: true, json: async () => ({ models: [{ name: "models/gemini-3.6-flash", supportedGenerationMethods: ["generateContent"] }] }) };
    if (/generateContent/.test(u)) return { ok: true, status: 200, json: async () => ({ candidates: [{ content: { parts: [{ text: JSON.stringify({ text: GOOD, axtar: ["school building"] }) }] } }] }) };
    if (u.startsWith("https://api.pexels.com/")) return { ok: true, json: async () => ({ videos: [{ id: 7, duration: 10, user: { name: "P" }, video_files: [{ link: "https://videos.pexels.com/7.mp4", file_type: "video/mp4", width: 1080, height: 1920 }] }] }) };
    return { ok: true, arrayBuffer: async () => new Uint8Array(30000).buffer };
  };
  const state = SV.readState(path.join(dir, "yox.json"), NOW);
  const env = { VIDEO_ACAR: "1", GEMINI_API_KEY: "g", PEXELS_API_KEY: "p", VIDEO_XEBER: a.id };
  const x = await SV.sec({ articles: [a], env, now: NOW, state, fetch: f, cats, dir, log: quiet });
  assert.equal(x.text, GOOD);
  assert.equal(x.ssenari, "gemini");
  assert.deepEqual(x.klipler, ["klip-1.mp4"]);
  assert.ok(fs.existsSync(path.join(dir, "klip-1.mp4")));
  assert.deepEqual(JSON.parse(fs.readFileSync(path.join(dir, "xeber.json"), "utf8")).klipler, ["klip-1.mp4"]);
  assert.match(SV.fbText(x), /Görüntü: Pexels/);
  assert.match(SV.igText(x), /Görüntü: Pexels/);
  assert.doesNotMatch(SV.fbText({ ...x, goruntu: [] }), /Pexels/);
  fs.rmSync(dir, { recursive: true, force: true });
});

test("sosial-video: protocol news is skipped, and when Gemini says stock footage would mislead («uygun»: false) the next story is used", async () => {
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), "video-uygun-"));
  const NOW = Date.parse("2026-11-22T10:00:00Z");
  const art = (c, title, min) => ({ id: c.repeat(16), title, summary: SOURCE, category: "cemiyyet", lang: "az", source: "APA", sourceUrl: `https://apa.az/${c}`,
    publishedAt: new Date(NOW - min * 60e3).toISOString(), alts: [{ source: "Report" }, { source: "Oxu.az" }, { source: "Trend" }] });
  const qebul = art("a", "Nazir Fransa səfirini qəbul edib", 5), bayanat = art("b", "Deputat Bakıda 12 yeni məktəbin açılışında çıxış edib", 10), mekteb = art("c", "Bakıda 12 yeni məktəb açılıb", 15);
  const page = `<html><body>${SOURCE.split(". ").map(s => `<p>${s}. Bakıda yeni məktəblər haqqında ətraflı məlumat.</p>`).join("")}</body></html>`;
  const asked = [];
  const f = async (u, o = {}) => {
    if (/^https:\/\/apa\.az\//.test(u)) return { ok: true, text: async () => page };
    if (/models\?pageSize/.test(u)) return { ok: true, json: async () => ({ models: [{ name: "models/gemini-3.6-flash", supportedGenerationMethods: ["generateContent"] }] }) };
    if (/generateContent/.test(u)) {
      const prompt = JSON.parse(o.body).contents[0].parts[0].text, deputat = /Deputat/.test(prompt);
      asked.push(deputat ? "b" : /məktəb/.test(prompt) ? "c" : "?");
      return { ok: true, status: 200, json: async () => ({ candidates: [{ content: { parts: [{ text: JSON.stringify(deputat ? { uygun: false } : { uygun: true, text: GOOD, axtar: ["school building"] }) }] } }] }) };
    }
    return { ok: false, status: 404 };
  };
  const state = SV.readState(path.join(dir, "yox.json"), NOW);
  const x = await SV.sec({ articles: [qebul, bayanat, mekteb], env: { VIDEO_ACAR: "1", VIDEO_PAYLAS: "0", GEMINI_API_KEY: "g" }, now: NOW, state, fetch: f, cats, dir, log: quiet });
  assert.equal(x.id, mekteb.id);
  assert.equal(x.text, GOOD);
  assert.deepEqual(asked, ["b", "c"], "qəbul xəbəri Gemini-yə getmir; Gemini rədd etdiyi xəbərdən sonra növbətisi");
  assert.ok(state.skip[qebul.id] && state.skip[bayanat.id], "rədd olunanlar yenidən yoxlanmır");
  // Gemini ümumiyyətlə cavab vermirsə (limit): mənbənin cümlələri ilə video hazırlanmır, xəbər «görülmüş» sayılmır.
  const dir2 = fs.mkdtempSync(path.join(os.tmpdir(), "video-limit-"));
  const state2 = SV.readState(path.join(dir2, "yox.json"), NOW);
  const limit = async (u) => (/^https:\/\/apa\.az\//.test(u) ? { ok: true, text: async () => page }
    : /models\?pageSize/.test(u) ? { ok: true, json: async () => ({ models: [] }) } : { ok: false, status: 429, json: async () => ({}) });
  const none = await SV.sec({ articles: [mekteb], env: { VIDEO_ACAR: "1", VIDEO_PAYLAS: "0", GEMINI_API_KEY: "g", VIDEO_GEMINI_WAIT_MS: "0" },
    now: NOW, state: state2, fetch: limit, cats, dir: dir2, log: quiet });
  assert.equal(none, null);
  assert.ok(!fs.existsSync(path.join(dir2, "xeber.json")));
  assert.ok(!state2.skip[mekteb.id] && !state2.v[mekteb.id], "növbəti dövrədə eyni xəbər yenidən sınanır");
  fs.rmSync(dir, { recursive: true, force: true });
  fs.rmSync(dir2, { recursive: true, force: true });
});
