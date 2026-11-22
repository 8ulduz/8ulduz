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
  + "başa çatdırılıb. Məktəblər yeni tədris ilindən fəaliyyət göstərəcək.";

test("ssenari: the narration is checked — every number from the source, no Cyrillic, links, exclamations, relative days, site rule", () => {
  const a = { title: "Bakıda yeni məktəblər açılıb", category: "cemiyyet" };
  assert.equal(VS.checkText(GOOD, SOURCE, a), "");
  assert.match(VS.checkText(GOOD.replace("3600", "4200"), SOURCE, a), /mənbədə olmayan rəqəm: 4200/);
  assert.match(VS.checkText(GOOD + " Это тест.", SOURCE, a), /kiril/);
  assert.match(VS.checkText(GOOD.replace("ayrılıb.", "ayrılıb!"), SOURCE, a), /nida/);
  assert.match(VS.checkText(GOOD.replace("Bakıda", "Bu gün Bakıda"), SOURCE, a), /nisbi gün/);
  assert.match(VS.checkText("Qısa mətn.", SOURCE, a), /uzunluq/);
  assert.match(VS.checkText(GOOD, SOURCE, a, () => "qadağan"), /qaydasından keçmir/);
  assert.equal(VS.checkText(GOOD.replace("3600", "3 600").replace("45,5", "45.5"), SOURCE.replace("3600", "3 600"), a), "", "minlik boşluğu və onluq vergül/nöqtə eyni rəqəmdir");
});

test("ssenari: Gemini writes the script (key in a header, never in the URL); bad or missing answers fall back to the source's own sentences", async () => {
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
  // Uydurma rəqəm, boş cavab, JSON olmayan cavab, açarsız: null (köhnə qayda).
  assert.equal(await VS.ssenari(a, page, { env, fetch: fake(JSON.stringify({ text: GOOD.replace("3600", "9999") })), log: quiet }), null);
  assert.equal(await VS.ssenari(a, page, { env, fetch: fake("bağışlayın"), log: quiet }), null);
  assert.equal(await VS.ssenari(a, page, { env: {}, fetch: () => { throw new Error("şəbəkə olmamalı idi"); }, log: quiet }), null);
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
  assert.deepEqual(inputs, ["a.mp4", "b.mp4", "c.mp4", "L.png", "ses.wav"]);
  assert.equal(args.filter(x => x === "-stream_loop").length, 3, "qısa klip dövrə vurur");
  const fc = args[args.indexOf("-filter_complex") + 1];
  assert.match(fc, /\[0:v\]scale=1080:1920:force_original_aspect_ratio=increase[^;]*crop=1080:1920/);
  assert.match(fc, /\[c0\]\[c1\]\[c2\]concat=n=3:v=1:a=0/);
  assert.match(fc, /\[3:v\]scale=-1:80/, "loqo klipdən sonrakı girişdir");
  assert.match(fc, /\[4:a\]/, "səs loqodan sonrakı girişdir");
  const plan = V.clipPlan(["a", "b", "c", "d", "e"], 14);
  assert.equal(plan.length, 3, "hər klip ən azı 4 s");
  assert.ok(Math.abs(plan.reduce((s, c) => s + c.d, 0) - 14) < 0.02, "hissələr videonun uzunluğunu tam örtür");
  // Kliplər olmadan əvvəlki kimi: rəngli fon, loqo [1], səs [2].
  const plain = V.ffmpegArgs({ tl: t, assFile: "v.ass", logo: "L.png", voiceFile: null, out: "o.mp4" });
  assert.match(plain[plain.indexOf("-filter_complex") + 1], /^\[0:v\]format=rgb24,ass=v\.ass\[t\];\[1:v\]scale[\s\S]*\[2:a\]aformat/);
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
