// Öz video arxivi (sahib, 2026-11-23: «həqiqi Gəncənin yeni stadionu olan videolardan istifadə etmək lazımdır. digərləri də belə»):
// .github/scripts/video-arxiv.cjs, data/video-arxiv.json, montajda arxiv (video-ssenari.cjs goruntu). Şəbəkə, ffmpeg və Gemini saxtadır.
const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("fs"), path = require("path"), os = require("os");
const VA = require("../.github/scripts/video-arxiv.cjs");
const VS = require("../.github/scripts/video-ssenari.cjs");
const VH = require("../.github/scripts/video-hava.cjs");
const root = path.join(__dirname, "..");
const read = f => fs.readFileSync(path.join(root, f), "utf8");
const quiet = () => {};
const DAY = "2026-11-23", NOW = Date.parse("2026-11-23T12:00:00Z");

const bank = (id, yer, extra = {}) => ({ id: `pixabay-${id}`, menbe: "Pixabay", menbeId: id, sehife: `https://pixabay.com/videos/id-${id}/`, muellifId: 7,
  lisenziya: VA.LISENZIYA.Pixabay, yer, seher: VA.seherOf(yer), obyekt: VA.obyektOf(yer), adlar: [], movzu: ["skyline"], hava: "gunesli", insan: false,
  olcu: [1920, 1080], muddet: 20, keyfiyyet: 4, yoxlama: { tarix: DAY, model: "gemini-sinaq", kadr: 4, teq: [VA.seherOf(yer) || "azerbaijan"], eminlik: 0.9,
    gorunen: yer.join(", "), izah: "sınaq", statik: "temiz" }, baxildi: DAY, ...extra });
const sahibE = (name, yer, extra = {}) => ({ id: VA.sahibId(name), menbe: "Sahib", fayl: VA.SAHIB_URL + name, asset: 1, rozet: "r1", setir: `${name} | … | öz çəkilişim`,
  icaze: "oz-cekilis", kim: "8ulduz", kredit: "8ulduz.az", lisenziya: VA.ICAZE["oz-cekilis"], yer, seher: VA.seherOf(yer), obyekt: VA.obyektOf(yer), adlar: [],
  movzu: ["stadium"], hava: "gunesli", insan: false, olcu: [1920, 1080], muddet: 15, keyfiyyet: 4,
  yoxlama: { tarix: DAY, model: "gemini-sinaq", kadr: 4, suNisani: false, ekran: false, statik: "temiz", izah: "" }, ...extra });

const LIB = [
  sahibE("gence-stadion.mp4", ["Ganja City Stadium", "Ganja", "Azerbaijan"]),
  bank(101, ["Ganja", "Azerbaijan"]),
  bank(102, ["Flame Towers", "Baku", "Azerbaijan"]),
  bank(103, ["Baku", "Azerbaijan"], { hava: "yagisli", movzu: ["rain", "street"] }),
  bank(104, ["Azerbaijan"], { movzu: ["flag"] }),
  bank(105, ["Palace of Shaki Khans", "Sheki", "Azerbaijan"]),
  bank(106, ["Yanar Dag", "Absheron", "Azerbaijan"]),
  bank(107, ["Baku", "Azerbaijan"], { insan: true }),
];

test("arxiv: the library file is metadata only, passes the schema and stays a small editorial selection", () => {
  const raw = JSON.parse(read("data/video-arxiv.json"));
  assert.ok(Array.isArray(raw.klipler) && raw.klipler.length <= VA.ARXIV_MAX, "kitabxana ≤ 400 klip (bankın nüsxəsi deyil)");
  const ids = new Set();
  for (const e of raw.klipler) { assert.equal(VA.kecerli(e), "", `${e.id}: ${VA.kecerli(e)}`); assert.ok(!ids.has(e.id), `təkrar ${e.id}`); ids.add(e.id); }
  const s = JSON.stringify(raw);
  assert.ok(!/\.(mp4|mov|webm)["?]/.test(s.replace(/https:\/\/github\.com\/8ulduz\/8ulduz\/releases\/download\/video-arxiv\/[^"]+/g, "")), "bankın fayl ünvanı saxlanmır (montaj ID ilə təzə soruşur)");
  assert.ok(!/"(user|tags|userImageURL|video_files)"/.test(s), "bankın müəllif adı və tam etiketləri saxlanmır (Pixabay/Pexels şərtləri §8)");
  assert.ok(!fs.readdirSync(path.join(root, "data")).some(f => /\.(mp4|mov|webm|m4v)$/i.test(f)), "repoya video yazılmır");
  for (const e of LIB) assert.equal(VA.kecerli(e), "", `sınaq sətri ${e.id}: ${VA.kecerli(e)}`);
});

test("arxiv: the schema guards the rules — two proofs of place, a license, the owner's own release only, no TV/X/platform, no watermark", () => {
  const b = LIB[2];
  assert.match(VA.kecerli({ ...b, yoxlama: { ...b.yoxlama, teq: [] } }), /etiket sübutu/);
  assert.match(VA.kecerli({ ...b, yoxlama: { ...b.yoxlama, eminlik: 0.5 } }), /əminlik/);
  assert.match(VA.kecerli({ ...b, yoxlama: { ...b.yoxlama, statik: "nisan" } }), /su nişanı/);
  assert.match(VA.kecerli({ ...b, lisenziya: "CC BY" }), /lisenziya/);
  assert.match(VA.kecerli({ ...b, yer: ["Stepanakert", "Azerbaijan"] }), /siyasi/);
  const s = LIB[0];
  for (const fayl of ["https://video.twimg.com/ext_tw_video/1.mp4", "https://example.com/gence.mp4", `${VA.SAHIB_URL}../x.mp4`, "https://github.com/someone/x/releases/download/video-arxiv/a.mp4"])
    assert.match(VA.kecerli({ ...s, fayl }), /Release/, fayl);
  assert.match(VA.kecerli({ ...s, kim: "AzTV", kredit: "AzTV" }), /üçüncü tərəf/);
  assert.match(VA.kecerli({ ...s, kredit: "Instagram @kimse" }), /üçüncü tərəf/);
  assert.match(VA.kecerli({ ...s, yoxlama: { ...s.yoxlama, suNisani: undefined } }), /su nişanı yoxlanmayıb/);
  assert.match(VA.kecerli({ ...s, icaze: "dostumdan" }), /icazə növü/);
  assert.match(VA.kecerli({ ...s, icaze: "yazili-icaze", kim: "Elçin Məmmədov", kredit: "Elçin Məmmədov" }), /icazənin tarixi/);
  assert.equal(VA.kecerli({ ...s, icaze: "yazili-icaze", kim: "Elçin Məmmədov", kredit: "Elçin Məmmədov", icazeTarixi: "2026-11-20" }), "");
  assert.match(VA.kecerli({ ...s, olcu: [640, 360] }), /ölçü/);
  // Pozulmuş sətir montaja düşmür, qalanlar işləyir.
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), "arxiv-")), file = path.join(dir, "a.json");
  fs.writeFileSync(file, JSON.stringify({ klipler: [LIB[1], { ...s, fayl: "https://video.twimg.com/x.mp4" }, LIB[1]] }));
  const logs = [];
  assert.deepEqual(VA.yukle(file, x => logs.push(x)).map(e => e.id), ["pixabay-101"]);
  assert.ok(logs.some(x => /Release/.test(x)) && logs.some(x => /təkrar id/.test(x)));
  assert.deepEqual(VA.yukle(path.join(dir, "yoxdur.json")), [], "fayl yoxdursa boş — video adi axtarışla davam edir");
  fs.rmSync(dir, { recursive: true, force: true });
});

test("arxiv: Azerbaijani place names reach the montage's English names; landmark names must share the head word", () => {
  assert.equal(VA.norm("Gəncə şəhər stadionu"), "ganja city stadium");
  assert.equal(VA.norm("Alov qüllələri"), "flame towers");
  assert.equal(VA.norm("Şəki Xan sarayı"), "sheki khan palace");
  assert.equal(VA.norm("İçərişəhər"), "icherisheher");
  assert.equal(VA.seherOf(["Gəncə stadionu"]), "ganja", "şəhər adın içindən də tanınır");
  assert.equal(VA.seherOf(["Tofiq Bahramov Republican Stadium", "Baku", "Azerbaijan"]), "baku");
  assert.ok(VA.obyektUygun("Ganja City Stadium", "Ganja Stadium"));
  assert.ok(VA.obyektUygun("Gəncə şəhər stadionu", "Ganja City Stadium"));
  assert.ok(!VA.obyektUygun("Heydar Aliyev Center", "Heydar Aliyev Park"), "eyni ad, başqa obyekt");
  assert.ok(!VA.obyektUygun("Baku Olympic Stadium", "Ganja City Stadium"), "eyni növ, başqa şəhər");
  assert.ok(VA.obyektUygun("Olympic Stadium", "Baku Olympic Stadium"));
  assert.ok(VA.obyektUygun("Palace of Shaki Khans", "Sheki Khan Palace"), "söz sırası və şəhərin başqa yazılışı");
  assert.ok(VA.obyektUygun("Icherisheher", "İçərişəhər") && VA.obyektUygun("Maiden Tower", "Qız qalası"));
  assert.ok(!VA.obyektUygun("Baku TV Tower", "Flame Towers") && !VA.obyektUygun("Nizami Mausoleum", "Nizami Street"));
  // Böyütmə planı: Bakı, Gəncə, Sumqayıt, Şəki, Şuşa, Qəbələ, Lənkəran, Naxçıvan və başqaları; hər şəhər SEHERLER-dədir (yad yer qaydası).
  const seh = new Set(VA.PLAN.map(p => VA.seherOf(p.yer)).filter(Boolean));
  for (const s of ["baku", "ganja", "sumqayit", "sheki", "shusha", "gabala", "lankaran", "nakhchivan", "quba", "mingachevir", "shamakhi"]) assert.ok(seh.has(s), s);
  for (const p of VA.PLAN) assert.ok(p.axtar.length && VA.planTeq(p).length, p.yer[0]);
  assert.ok(["Flame Towers", "Baku Boulevard", "Icherisheher", "Heydar Aliyev Center", "Baku Olympic Stadium"].every(o => VA.PLAN.some(p => p.yer[0] === o)));
});

test("arxiv: the montage gets the story's own place — owner's clip and exact landmark first, then the city; another city never", () => {
  const ids = r => r.map(x => `${x.e.id}:${x.level}${x.ilk ? "*" : ""}`);
  const G = VS.yerPlan(["Ganja City Stadium", "Ganja", "Azerbaijan"]);
  assert.deepEqual(ids(VA.namizedler(LIB, { yer: ["Ganja City Stadium", "Ganja", "Azerbaijan"], icaze: G.icaze, axtar: ["football stadium"] })),
    ["sahib-gence-stadion:obyekt*", "pixabay-101:seher", "pixabay-104:olke"], "Gəncənin stadionu (sahibin öz görüntüsü) başlıqda; Bakı, Şəki, Yanardağ yoxdur");
  const B = VS.yerPlan(["Flame Towers", "Baku", "Azerbaijan"]);
  assert.deepEqual(ids(VA.namizedler(LIB, { yer: ["Flame Towers", "Baku", "Azerbaijan"], icaze: B.icaze })).slice(0, 2), ["pixabay-102:obyekt*", "pixabay-103:seher"]);
  assert.ok(!VA.namizedler(LIB, { yer: ["Flame Towers", "Baku", "Azerbaijan"], icaze: B.icaze }).some(x => /101|105|106|sahib/.test(x.e.id)), "Gəncə, Şəki və Yanardağ Bakı xəbərinə getmir");
  // Yalnız ölkə: paytaxt və ümumi klip (ən çox 2), başqa şəhər yox.
  const A = VA.namizedler(LIB, { yer: ["Azerbaijan"], icaze: VS.yerPlan(["Azerbaijan"]).icaze });
  assert.ok(A.length === 2 && A.every(x => x.level === "olke" && !x.ilk && /10[2347]/.test(x.e.id)), JSON.stringify(ids(A)));
  // Yer bilinmirsə arxiv işlənmir.
  assert.deepEqual(VA.namizedler(LIB, { yer: [], icaze: VS.yerPlan([]).icaze }), []);
  // İşlənmiş klip (son 3 gün, state.klip) yenidən götürülmür.
  assert.ok(!VA.namizedler(LIB, { yer: ["Flame Towers", "Baku", "Azerbaijan"], icaze: B.icaze, istifade: new Set(["Pixabay:102"]) }).some(x => x.e.id === "pixabay-102"));
  // Hava videosu (video-hava.cjs arxivSecim): sabah Bakıda yağış — yalnız yağışda çəkilmiş Bakı klipi, başlıq kadrı.
  const yagis = VH.arxivSecim({ baki: { kind: "yagis" } }), acik = VH.arxivSecim({ baki: { kind: "acik" } });
  assert.deepEqual(yagis, { yer: ["Baku", "Azerbaijan"], hava: ["yagisli"] });
  assert.deepEqual(ids(VA.namizedler(LIB, { yer: yagis.yer, icaze: VS.yerPlan(["Azerbaijan"]).icaze, hava: yagis.hava })), ["pixabay-103:seher*"]);
  assert.ok(VA.namizedler(LIB, { yer: acik.yer, icaze: VS.yerPlan(["Azerbaijan"]).icaze, hava: acik.hava }).every(x => x.e.hava === "gunesli"));
  assert.deepEqual(VA.namizedler(LIB.map(e => (e.id === "pixabay-103" ? { ...e, rengli: false } : e)), { yer: yagis.yer, icaze: VS.yerPlan(["Azerbaijan"]).icaze, hava: yagis.hava }), [], "ağ-qara klip hava videosuna getmir");
  for (const k of Object.keys(VH.ARXIV_HAVA)) assert.ok(VH.ARXIV_HAVA[k].every(h => VA.HAVA.includes(h) && h !== "gece"), k);
  // Mənfi xəbər: şəhər klipi başlığa məcburi qoyulmur, yaxın planda insan olan klip yoxdur.
  assert.ok(VA.menfi({ category: "hadise" }) && VA.menfi({ title: "Bakıda yol qəzası: 2 nəfər həlak olub" }) && !VA.menfi({ title: "Bakıda yeni park açılıb" }));
  const N = VA.namizedler(LIB, { yer: ["Baku", "Azerbaijan"], icaze: VS.yerPlan(["Baku", "Azerbaijan"]).icaze, menfi: true });
  assert.ok(N.length && N.every(x => !x.ilk && !x.e.insan));
});

test("goruntu: archive first — owner's footage from the site's own release, bank clips asked again by ID (fresh file, deleted ones skipped), credit names the owner", async () => {
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), "klip-arxiv-"));
  const hit = (id, tags) => ({ id, duration: 15, user: `u${id}`, user_id: 70 + id, tags, pageURL: `https://pixabay.com/videos/x-${id}/`,
    videos: { medium: { url: `https://cdn.pixabay.com/${id}.mp4`, width: 1920, height: 1080, size: 5e6 }, tiny: { url: `https://cdn.pixabay.com/${id}-t.mp4`, width: 960, height: 540, thumbnail: `https://cdn.pixabay.com/${id}.jpg` } } });
  const urls = [], logs = [];
  const gone = new Set();
  const f = async (u) => {
    urls.push(u);
    if (u.startsWith("https://pixabay.com/api/videos/")) {
      const q = new URL(u).searchParams;
      if (q.get("id")) return { ok: true, json: async () => ({ hits: gone.has(q.get("id")) ? [] : [hit(Number(q.get("id")), "ganja, azerbaijan, city")] }) };
      return { ok: true, json: async () => ({ hits: [hit(301, "stadium, football, field"), hit(302, "stadium, football, batumi, georgia")] }) };
    }
    return { ok: true, arrayBuffer: async () => new Uint8Array(20000).buffer };
  };
  const opt = { env: { PIXABAY_API_KEY: "pxb-acar" }, fetch: f, log: s => logs.push(s), say: 4, category: "idman", yer: ["Ganja City Stadium", "Ganja", "Azerbaijan"], arxiv: LIB };
  const got = await VS.goruntu(["football stadium"], dir, opt);
  assert.deepEqual(got.map(g => g.arxiv || `${g.p}:${g.id}`), ["sahib-gence-stadion", "pixabay-101", "pixabay-104", "Pixabay:301"],
    "əvvəl sahibin Gəncə stadionu (başlıq), sonra arxivin Gəncəsi, sonra adi axtarış; Batumi və Bakı yox");
  assert.ok(urls.includes(`${VA.SAHIB_URL}gence-stadion.mp4`), "sahibin faylı öz Release-indən");
  assert.ok(urls.some(u => /[?&]id=101(&|$)/.test(u)) && !urls.some(u => /[?&]id=10[2357]/.test(u)), "yalnız uyğun arxiv klipi bankdan ID ilə soruşulur");
  assert.equal(got[0].kredit, "8ulduz.az");
  assert.equal(VS.kredit(got), "8ulduz.az, Pixabay", "kredit: əvvəl saytın öz görüntüsü, sonra bank");
  assert.ok(logs.some(s => /ARXİV obyekt «Ganja City Stadium»/.test(s)), "jurnalda arxivdən gələn klip görünür");
  assert.ok(!logs.join("\n").includes("pxb-acar"), "açar jurnalda yoxdur");
  // Bankda silinmiş arxiv klipi ötürülür, video adi axtarışla davam edir.
  gone.add("101"); logs.length = 0;
  const got2 = await VS.goruntu(["football stadium"], dir, { ...opt, istifade: new Set(["Sahib:sahib-gence-stadion"]) });
  assert.ok(!got2.some(g => g.arxiv === "pixabay-101" || g.arxiv === "sahib-gence-stadion"));
  assert.ok(logs.some(s => /arxiv klipi alınmadı — pixabay-101/.test(s)));
  // Arxivsiz (köhnə çağırış) heç nə dəyişmir.
  const plain = await VS.goruntu(["football stadium"], dir, { ...opt, arxiv: undefined });
  assert.ok(plain.every(g => !g.arxiv));
  fs.rmSync(dir, { recursive: true, force: true });
});

// Saxta boz kadrlar: hərəkət edən səs-küy; istəyə görə küncdə yerində duran loqo və ya aşağıda titr.
function frames({ logo = false, titr = false, still = false, w = 160, h = 90 } = {}) {
  let seed = 7;
  const rnd = () => ((seed = (Math.imul(seed, 1103515245) + 12345) >>> 0) >>> 8) / (1 << 24);
  const base = Uint8Array.from({ length: w * h }, () => Math.floor(rnd() * 255));
  return Array.from({ length: 12 }, () => {
    const fr = still ? Uint8Array.from(base) : Uint8Array.from({ length: w * h }, () => Math.floor(rnd() * 255));
    for (let y = 0; y < h; y++) for (let x = 0; x < w; x++) {
      if (logo && x >= 120 && x < 152 && y >= 3 && y < 16) fr[y * w + x] = ((x >> 1) + (y >> 1)) % 2 ? 250 : 10;
      if (titr && y >= 78 && y < 88) fr[y * w + x] = ((x >> 1) + (y >> 1)) % 2 ? 245 : 20;
    }
    return fr;
  });
}
test("arxiv: a static overlay (logo, watermark, channel bug, ticker) on a moving picture is caught without Gemini", () => {
  assert.deepEqual(VA.statikQat(frames({ logo: true }), 160, 90).qerar, "nisan");
  assert.equal(VA.statikQat(frames({ logo: true }), 160, 90).yer, "sağ yuxarı künc");
  assert.equal(VA.statikQat(frames({ titr: true }), 160, 90).yer, "aşağı zolaq (titr)");
  assert.equal(VA.statikQat(frames(), 160, 90).qerar, "temiz");
  assert.equal(VA.statikQat(frames({ still: true }), 160, 90).qerar, "bilinmir", "səhnə dayanıbsa qərar Gemini-nindir");
  assert.equal(VA.statikQat(frames().slice(0, 3), 160, 90).qerar, "bilinmir");
});

// Böyütmə: saxta bank, kadrlar və Gemini.
function fakeBank(db) {
  const asked = [];
  const f = async (u) => {
    if (u.startsWith("https://pixabay.com/api/videos/")) {
      const q = new URL(u).searchParams;
      asked.push(q.get("id") ? `id:${q.get("id")}` : q.get("q"));
      if (q.get("id")) return { ok: true, json: async () => ({ hits: (db.byId || {})[q.get("id")] ? [db.byId[q.get("id")]] : [] }) };
      return { ok: true, json: async () => ({ hits: db[q.get("q")] || [] }) };
    }
    return { ok: true, arrayBuffer: async () => new Uint8Array(20000).buffer };
  };
  return { f, asked };
}
const phit = (id, tags, extra = {}) => ({ id, duration: 20, user: `u${id}`, user_id: 500 + id, tags, pageURL: `https://pixabay.com/videos/${tags.split(",")[0].replace(/\s+/g, "-")}-${id}/`,
  videos: { medium: { url: `https://cdn.pixabay.com/${id}.mp4`, width: 1920, height: 1080, size: 6e6 }, tiny: { url: `https://cdn.pixabay.com/${id}-tiny.mp4`, width: 960, height: 540, size: 1e6 } }, ...extra });
const OK = (o = {}) => ({ gorunen_yer: "Baku, Azerbaijan", seher_dogru: true, obyekt: "", obyekt_gorunur: true, eminlik: 0.92, rengli: true, su_nisani: false, siyasi: false, insan: false, hava: "gunesli",
  movzu: ["skyline", "towers"], keyfiyyet: 4, izah: "Bakının panoraması, Alov qüllələri görünür.", _model: "gemini-sinaq", ...o });

test("arxiv boyut: tag evidence + Gemini's own look at 4 frames; city and landmark asked apart; wrong place, watermark, separatist tags rejected and remembered; searches cached 30 days", async () => {
  const db = {
    "flame towers baku": [phit(1, "flame towers, baku, azerbaijan, night"), phit(2, "towers, city, night"), phit(3, "flame towers, baku, batumi, georgia")],
    "baku boulevard": [phit(4, "boulevard, baku, sea"), phit(5, "baku, boulevard, people")],
    "baku old city": [phit(6, "old city, baku, architecture"), phit(9, "old city, baku, museum"), phit(10, "old city, baku, panorama")],
    "baku": [phit(8, "baku, azerbaijan, city"), phit(11, "dubai, city, skyline")],
    "shusha azerbaijan": [phit(7, "shushi, artsakh, mountains")],
  };
  const { f, asked } = fakeBank(db);
  // 6: Gemini «İçərişəhər» axtarışında Qız qalasını görür (planın başqa obyekti); 9: Heydər Əliyev Mərkəzini (2026-11-23 ilk işdə belə
  // klip «yer təsdiqlənmədi» ilə rədd olunmuşdu); 10: obyekt görünmür — Bakının klipi kimi qalır; 1: etiket və kadr eyni obyekt.
  const looks = { 1: OK({ obyekt: "Flame Towers" }), 4: OK({ seher_dogru: false, gorunen_yer: "Batumi, Georgia", eminlik: 0.8 }), 5: OK({ su_nisani: true }),
    6: OK({ obyekt: "Maiden Tower", obyekt_gorunur: false, eminlik: 0.95, movzu: ["old town"] }), 8: OK({ obyekt: "Flame Towers", eminlik: 0.95, rengli: false }),
    9: OK({ obyekt: "Heydar Aliyev Center", obyekt_gorunur: false, eminlik: 0.95 }), 10: OK({ obyekt: "", obyekt_gorunur: false, eminlik: 0.9 }) };
  const order = [], prompts = [];
  const deps = {
    kadrlar: async url => { const id = Number(url.match(/(\d+)-tiny/)[1]); order.push(id); return { jpg: [Buffer.from(`k${id}`)], gray: { w: 160, h: 90, frames: frames() }, id }; },
    baxis: async (prompt, jpg) => { prompts.push(prompt); assert.ok(!/flame towers, baku, azerbaijan, night/.test(prompt), "Gemini-yə bankın etiketi verilmir (müstəqil sübut)"); return looks[String(jpg[0]).slice(1)] || OK({ seher_dogru: false, gorunen_yer: "unknown" }); },
    zolaq: () => true,
  };
  const lib = VA.oxu("/yoxdur");
  const rep = await VA.boyut(lib, { env: { PIXABAY_API_KEY: "k", ARXIV_ARA_MS: "0" }, fetch: f, log: quiet, say: 10, now: NOW, deps });
  const byId = Object.fromEntries(lib.klipler.map(e => [e.id, e]));
  assert.deepEqual(Object.keys(byId).sort(), ["pixabay-1", "pixabay-10", "pixabay-6", "pixabay-8", "pixabay-9"]);
  assert.deepEqual(byId["pixabay-1"].yer, ["Flame Towers", "Baku", "Azerbaijan"], "etiket və Gemini obyekti təsdiqlədi");
  assert.deepEqual(byId["pixabay-1"].yoxlama.teq, ["flame towers", "baku"]);
  assert.equal(byId["pixabay-1"].yoxlama.model, "gemini-sinaq");
  assert.equal(byId["pixabay-1"].muellifId, 501);
  assert.ok(!("user" in byId["pixabay-1"]) && !JSON.stringify(byId["pixabay-1"]).includes("u1"), "müəllifin adı saxlanmır");
  assert.equal(VA.kecerli(byId["pixabay-1"]), "");
  assert.deepEqual(byId["pixabay-6"].yer, ["Maiden Tower", "Baku", "Azerbaijan"], "etiket «old city», kadrda Qız qalası — planın o obyekti");
  assert.deepEqual(byId["pixabay-9"].yer, ["Heydar Aliyev Center", "Baku", "Azerbaijan"]);
  assert.deepEqual(byId["pixabay-10"].yer, ["Baku", "Azerbaijan"], "obyekt görünmür: etiketə baxmayaraq şəhər səviyyəsində");
  assert.deepEqual(byId["pixabay-8"].yer, ["Flame Towers", "Baku", "Azerbaijan"], "«baku» axtarışında Gemini Alov qüllələrini çox əmin tanıdı — planın obyekti");
  assert.equal(byId["pixabay-8"].rengli, false);
  assert.ok(prompts.some(p => /Gözlənilən şəhər: Baku, Azerbaijan\. Gözlənilən obyekt: Icherisheher/.test(p)) && prompts.some(p => /Gözlənilən obyekt: —/.test(p)));
  assert.ok(!order.includes(2), "etiketində yer olmayan klip yoxlanmır (sübut yoxdur)");
  assert.ok(!lib.redd["pixabay-11"] && !lib.redd["pixabay-2"], "axtarışa təsadüfən düşən yad klip rədd siyahısına yazılmır (fayl şişmir)");
  assert.match(lib.redd["pixabay-3"], /başqa yer etiketdə \(batumi\)/);
  assert.match(lib.redd["pixabay-4"], /yer təsdiqlənmədi \(Batumi, Georgia\)/);
  assert.match(lib.redd["pixabay-5"], /su nişanı/);
  assert.match(lib.redd["pixabay-7"], /siyasi/);
  assert.ok(lib.axtaris["pixabay:flame towers baku"] === DAY);
  // Montajda ağ-qara klip rənglidən sonra gəlir.
  const N = VA.namizedler(lib.klipler, { yer: ["Flame Towers", "Baku", "Azerbaijan"], icaze: VS.yerPlan(["Flame Towers", "Baku", "Azerbaijan"]).icaze });
  assert.deepEqual(N.filter(x => x.level === "obyekt").map(x => x.e.id), ["pixabay-1", "pixabay-8"]);
  // İkinci iş: eyni gün eyni axtarış təkrarlanmır, rədd edilən klip yenidən yoxlanmır, köhnə klip bankda yoxlanır.
  asked.length = 0; order.length = 0;
  db.byId = { 1: phit(1, "flame towers, baku"), 8: phit(8, "baku") };
  const rep2 = await VA.boyut(lib, { env: { PIXABAY_API_KEY: "k", ARXIV_ARA_MS: "0" }, fetch: f, log: quiet, say: 10, now: NOW + 86400e3, deps });
  assert.ok(!asked.includes("flame towers baku") && !asked.includes("baku boulevard"), "axtarış 30 gündə bir (Pixabay: ≥24 saat keş)");
  assert.ok(asked.includes("id:1") && asked.includes("id:6"));
  assert.deepEqual(rep2.silindi, ["pixabay-6", "pixabay-9", "pixabay-10"], "bankda silinmiş klip arxivdən çıxır");
  assert.match(lib.redd["pixabay-6"], /bankda silinib/, "başlanğıc nüsxədən geri qayıtmasın");
  assert.equal(order.length, 0);
  assert.ok(rep.axtaris <= 25 && rep.elave.length === 5);
  // Gemini cavab vermirsə (limit) dayanır, rədd yazılmır — növbəti işdə yenidən.
  const lib3 = VA.oxu("/yoxdur");
  const rep3 = await VA.boyut(lib3, { env: { PIXABAY_API_KEY: "k", ARXIV_ARA_MS: "0" }, fetch: fakeBank(db).f, log: quiet, say: 10, now: NOW, deps: { ...deps, baxis: async () => null } });
  assert.match(rep3.dayandi, /Gemini/);
  assert.ok(!lib3.redd["pixabay-1"] && !lib3.klipler.length);
  // Açarsız heç nə edilmir.
  assert.equal((await VA.boyut(VA.oxu("/yoxdur"), { env: {}, fetch: () => { throw new Error("şəbəkə olmamalı idi"); }, log: quiet })).dayandi, "açar yoxdur");
  // Yazılan fayl sabit sıradadır və sxemdən keçir.
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), "arxiv-yaz-")), file = path.join(dir, "a.json");
  VA.yaz(lib, file, NOW);
  const again = VA.oxu(file);
  assert.deepEqual(again.klipler.map(e => e.id), ["pixabay-1", "pixabay-8"]);
  VA.yaz(again, file, NOW);
  assert.equal(fs.readFileSync(file, "utf8"), (VA.yaz(VA.oxu(file), file, NOW), fs.readFileSync(file, "utf8")), "eyni məlumat — eyni fayl");
  fs.rmSync(dir, { recursive: true, force: true });
});

test("arxiv sahib: the owner's release lines — own footage or written permission; TV/X/platform files, watermarks and screen recordings refused", async () => {
  const lines = VA.sahibSetirleri([
    "Saytın öz görüntüləri.", "    fayl.mp4 | yer | öz çəkilişim", "`numune.mp4 | Bakı | öz`",
    "gence-stadion.mp4 | Gəncə şəhər stadionu, Gəncə | öz çəkilişim",
    "seki saray.mov | Şəki Xan sarayı, Şəki | icazə: Elçin Məmmədov, 2026-11-20",
    "aztv.mp4 | Bakı | AzTV efiri", "x.mp4 | Bakı | X-dən götürdüm (x.com)", "dost.mp4 | Bakı | dostumdan", "qala.mp4 | Qız qalası | öz çəkilişim",
  ].join("\n"));
  const by = Object.fromEntries(lines.map(l => [l.fayl, l]));
  assert.ok(!by["numune.mp4"], "nümunə sətri (kod bloku) oxunmur");
  assert.equal(by["gence-stadion.mp4"].icaze, "oz-cekilis");
  assert.equal(by["gence-stadion.mp4"].kredit, "8ulduz.az");
  assert.equal(by["seki saray.mov"].kim, "Elçin Məmmədov", "adında boşluq olan fayl");
  assert.equal(by["seki saray.mov"].icazeTarixi, "2026-11-20");
  assert.ok(!by["fayl.mp4"], "təsvirdəki nümunə (4 boşluqla) oxunmur");
  assert.match(by["aztv.mp4"].xeta, /üçüncü tərəf/);
  assert.match(by["x.mp4"].xeta, /üçüncü tərəf/);
  assert.match(by["dost.mp4"].xeta, /icazə yazılmayıb/);
  assert.match(by["qala.mp4"].xeta, /şəhər tanınmadı/);

  const asset = (id, name, size = 5e6) => ({ id, name, size, digest: `sha256:${id}`, updated_at: DAY, browser_download_url: `${VA.SAHIB_URL}${encodeURIComponent(name)}` });
  const rel = { body: ["gence-stadion.mp4 | Gəncə şəhər stadionu, Gəncə | öz çəkilişim", "tiktok.mp4 | Bakı bulvarı, Bakı | öz çəkilişim",
    "nisan.mp4 | Şəki, Şəki | öz çəkilişim", "ekran.mp4 | Bakı | öz çəkilişim", "kicik.mp4 | Bakı | öz çəkilişim",
    "seki.mov | Şəki Xan sarayı, Şəki | icazə: Elçin Məmmədov, 2026-11-20", "yuklenmeyib.mp4 | Bakı | öz çəkilişim"].join("\n"),
    assets: [asset(1, "gence-stadion.mp4"), asset(2, "tiktok.mp4"), asset(3, "nisan.mp4"), asset(4, "ekran.mp4"), asset(5, "kicik.mp4"), asset(6, "seki.mov"), asset(7, "setirsiz.mp4")] };
  const probe = file => {
    const n = path.basename(file);
    if (/-2\./.test(n)) return { w: 1080, h: 1920, dur: 12, tags: "encoder=Lavf vid:v12044 comment=vid:tiktok" };
    if (/-5\./.test(n)) return { w: 640, h: 360, dur: 12, tags: "" };
    return { w: 1920, h: 1080, dur: 14, tags: "encoder=Lavf" };
  };
  const looks = [];
  const deps = {
    release: async () => rel, indir: async (url, file) => fs.writeFileSync(file, "x"), probe,
    kadrlar: file => ({ jpg: [Buffer.from(path.basename(file))], gray: { w: 160, h: 90, frames: frames({ logo: /-3\./.test(file) }) } }),
    baxis: async (prompt, jpg) => { looks.push(prompt); const n = String(jpg[0]);
      if (/-4\./.test(n)) return { su_nisani: false, ekran: true, siyasi: false, ziddiyyet: false, keyfiyyet: 3 };
      if (/-6\./.test(n)) return { su_nisani: false, ekran: false, siyasi: false, ziddiyyet: false, yer_en: ["Palace of Shaki Khans", "Sheki", "Azerbaijan"], hava: "buludlu", movzu: ["palace"], keyfiyyet: 4, izah: "Saray", _model: "g" };
      return { su_nisani: false, ekran: false, siyasi: false, ziddiyyet: false, yer_en: ["Ganja City Stadium", "Ganja", "Azerbaijan"], insan: false, hava: "gunesli", movzu: ["stadium", "football"], keyfiyyet: 4, izah: "Stadion", _model: "g" }; },
    zolaq: () => true,
  };
  const lib = { ...VA.oxu("/yoxdur"), klipler: [sahibE("kohne.mp4", ["Baku", "Azerbaijan"])] };
  const rep = await VA.sahib(lib, { env: {}, log: quiet, now: NOW, deps });
  const S = Object.fromEntries(lib.klipler.map(e => [e.id, e]));
  assert.deepEqual(Object.keys(S).sort(), ["sahib-gence-stadion", "sahib-seki"]);
  assert.deepEqual(S["sahib-gence-stadion"].yer, ["Ganja City Stadium", "Ganja", "Azerbaijan"]);
  assert.equal(S["sahib-gence-stadion"].fayl, `${VA.SAHIB_URL}gence-stadion.mp4`);
  assert.equal(S["sahib-seki"].kredit, "Elçin Məmmədov");
  assert.match(S["sahib-seki"].lisenziya, /yazılı icazə.*Elçin Məmmədov, 2026-11-20/i);
  for (const e of Object.values(S)) assert.equal(VA.kecerli(e), "", e.id);
  const why = Object.fromEntries(rep.redd.map(r => [r.fayl, r.why]));
  assert.match(why["tiktok.mp4"], /platformanın izi \(tiktok\)/);
  assert.match(why["nisan.mp4"], /statik üst qat.*sağ yuxarı künc/);
  assert.match(why["ekran.mp4"], /başqa ekranın çəkilişi/);
  assert.match(why["kicik.mp4"], /ölçü 640×360/);
  assert.deepEqual(rep.silindi, ["sahib-kohne"], "Release-dən silinən fayl arxivdən çıxır");
  assert.ok(rep.qeyd.some(q => /yuklenmeyib\.mp4: fayl Release-ə yüklənməyib/.test(q)) && rep.qeyd.some(q => /setirsiz\.mp4: sətir yazılmayıb/.test(q)));
  assert.ok(looks.every(p => /su_nisani/.test(p) && /ekran/.test(p)), "Gemini su nişanını və ekran çəkilişini yoxlayır");
  // Dəyişməyən fayl yenidən yoxlanmır (Gemini sorğusu yoxdur).
  looks.length = 0;
  await VA.sahib(lib, { env: {}, log: quiet, now: NOW, deps });
  assert.equal(looks.filter(p => /Gəncə/.test(p)).length, 0);
  // Xülasə sahibə nəyin qəbul olunmadığını və niyəsini göstərir.
  assert.match(VA.xulase("Video arxivi", rep, lib.klipler), /tiktok\.mp4 \| faylda platformanın izi/);
});

test("arxiv: the library lives outside main — history-less video-arxiv branch; montage reads it and falls back to the PR seed; nothing pushes main", () => {
  // Botlardan main-ə yalnız xəbər axını yazır; X yazıcısı da 2026-11-27-dən növbəni yalnız x-novbe budağına yazır (sahib).
  const wf = read(".github/workflows/video-arxiv.yml");
  assert.ok(!/git add|HEAD:main|refs\/heads\/main"|pull --rebase/.test(wf), "arxiv işi main-ə yazmır");
  const pushes = [...wf.matchAll(/git push[^\n]*/g)].map(m => m[0]);
  assert.deepEqual(pushes, ['git push -q --force origin "$commit:refs/heads/video-arxiv"'], "yalnız öz tarixçəsiz budağı");
  assert.match(wf, /commit-tree "\$tree" -m/, "valideynsiz commit (repo şişmir)");
  assert.match(wf, /YAZ: \$\{\{ github\.event_name != 'pull_request'/, "PR budağa yazmır");
  assert.match(wf, /ls-remote --exit-code --heads origin video-arxiv[\s\S]*"\$code" = 2[\s\S]*exit 1/, "budaq oxunmasa (yox deyil, xəta) iş dayanır, budağa toxunmur");
  assert.match(wf, /cron: "2 9 \* \* 1,4"/);
  assert.ok(!read(".github/scripts/pipeline.sh").includes("video-arxiv"), "xəbər axınına toxunulmur");
  const sv = read(".github/workflows/sosial-video.yml");
  // Budaq tam adı ilə (2026-11-26): «video-arxiv» buraxılışının eyni adlı teqi qısa adda budaqdan öndə gəlir — fetch teqi götürürdü,
  // 2026-11-25-dən arxiv işi düşürdü, video isə budağın kitabxanasını oxumurdu (başlanğıc nüsxə ilə gedirdi).
  assert.match(sv, /git fetch -q --depth 1 origin refs\/heads\/video-arxiv /);
  assert.match(wf, /git fetch -q --depth 1 origin refs\/heads\/video-arxiv\n/);
  for (const [name, y] of [["sosial-video.yml", sv], ["video-arxiv.yml", wf]]) {
    assert.ok(!/git fetch[^\n]* origin video-arxiv\b/.test(y), `${name}: video-arxiv qısa adla çəkilmir (teq budaqdan öndə gəlir)`);
  }
  assert.match(sv, /VIDEO_ARXIV_FAYL=/);
  assert.match(sv, /data\/video-arxiv\.json/);
  assert.match(sv, /\.github\/scripts\/video-arxiv\.cjs/);
  assert.match(read(".github/scripts/sosial-video.cjs"), /arxiv: VA\.kitabxana\(process\.env, console\.log\)/);
  const src = read(".github/scripts/video-arxiv.cjs");
  for (const bad of ["reels.json", "oz_x.json", "video.twimg.com", "youtube.com/watch"]) assert.ok(!src.includes(bad), `arxiv X/TV videosu oxumur: ${bad}`);
  assert.match(read("docs/sosial-video.md"), /## Video arxivi/);
  // Kitabxana: budağın nüsxəsi + başlanğıc nüsxənin yeni klipləri; budaqda rədd/silinmiş klip geri qayıtmır; budaq oxunmasa başlanğıc nüsxə.
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), "arxiv-budaq-")), file = path.join(dir, "video-arxiv.json");
  fs.writeFileSync(file, JSON.stringify({ klipler: [LIB[2], LIB[0]], redd: { "pixabay-103": "2026-11-23 bankda silinib" } }));
  const seed = VA.oxu(VA.FAYL), logs = [];
  const got = VA.kitabxana({ VIDEO_ARXIV_FAYL: file }, x => logs.push(x)).map(e => e.id);
  assert.ok(got.includes("pixabay-102") && got.includes("sahib-gence-stadion"));
  for (const e of seed.klipler) assert.ok(got.includes(e.id) || e.id === "pixabay-103", `başlanğıc nüsxənin klipi ${e.id}`);
  const lib = VA.birlesdir(VA.oxu(file), { klipler: [LIB[3], LIB[4], sahibE("x.mp4", ["Baku", "Azerbaijan"])], redd: {} });
  assert.deepEqual(lib.klipler.map(e => e.id), ["pixabay-102", "sahib-gence-stadion", "pixabay-104"], "rədd edilən və sahibin (Release-siz) klipi qoşulmur");
  fs.writeFileSync(file, "{pozulub");
  assert.deepEqual(VA.kitabxana({ VIDEO_ARXIV_FAYL: file }, x => logs.push(x)).map(e => e.id), VA.yukle(VA.FAYL).map(e => e.id));
  assert.ok(logs.some(x => /budağının nüsxəsi oxunmadı/.test(x)));
  assert.deepEqual(VA.kitabxana({}).map(e => e.id), VA.yukle(VA.FAYL).map(e => e.id));
  fs.rmSync(dir, { recursive: true, force: true });
});
