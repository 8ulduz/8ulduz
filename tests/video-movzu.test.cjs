// Video mövzuları (sahibin qərarı, 2026-11-26, «hamısına bəli»; docs/sosial-video.md «Video mövzuları»):
//   A) «Maraqlı» rubrikası (heyvan, təbiət, kosmos faktları) söndürülüb; X və dünya videolarından heyvan, təbiət, kosmos çıxıb (heyvan
//      yalnız insan hadisəsinin içində); xəbər, X və dünya videosunun seçimi böyük Azərbaycan Instagram hesablarının 15 istiqaməti ilə.
//   B) «Çox baxılan» X videosunun səsində baxış sayı yoxdur; şərh paylaşımın öz faktlarındandır (ən az 3 cümlə, 2026-11-27), kadrlar
//      mətnlə tutuşdurulur.
// Şəbəkə, Gemini və ffmpeg burada işləmir: hamısı saxtadır.
"use strict";
const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("fs"), os = require("os"), path = require("path"), cp = require("child_process");

const SV = require("../.github/scripts/sosial-video.cjs");
const VD = require("../.github/scripts/video-dunya.cjs");
const DL = require("../.github/scripts/video-dil.cjs");
const root = path.resolve(__dirname, "..");
const read = f => fs.readFileSync(path.join(root, f), "utf8").replace(/\r\n/g, "\n");
const NOW = Date.parse("2026-11-26T10:00:00Z");   // Bakı vaxtı 14:00
const tmp = () => fs.mkdtempSync(path.join(os.tmpdir(), "movzu-"));
const art = (title, o = {}) => ({ id: "a".padEnd(16, "0"), title, summary: "", category: "gundem", lang: "az", ...o });
const near = (a, b) => Math.abs(a - b) < 1e-9;
// GITHUB_OUTPUT (CI) testin öz faylına yazılsın.
async function withOutput(fn) {
  const old = process.env.GITHUB_OUTPUT;
  process.env.GITHUB_OUTPUT = path.join(tmp(), "out.txt");
  try { return await fn(); } finally { if (old === undefined) delete process.env.GITHUB_OUTPUT; else process.env.GITHUB_OUTPUT = old; }
}

// --- A1: «Maraqlı» rubrikası -----------------------------------------------------------------------------------------------------
test("maraqlı: off by default (owner 2026-11-26) — never made on schedule, a manual run only previews, the share step refuses it", async () => {
  assert.equal(SV.maraqliOptions({}).on, false);
  assert.equal(SV.maraqliOptions({ MARAQLI_VIDEO: "0" }).on, false);
  assert.equal(SV.maraqliOptions({ MARAQLI_VIDEO: "1" }).on, true, "yalnız sahibin açıq göstərişi ilə (Variables)");
  assert.match(SV.maraqliDue(SV.readState("/yoxdur", NOW), NOW, SV.maraqliOptions({})), /söndürülüb.*MARAQLI_VIDEO=1/);
  await withOutput(async () => {
    let asked = 0;
    const maraqli = async () => { asked++; return { id: "m".padEnd(16, "0"), tur: "maraqli", kind: "maraqli", title: "Gepard saatda yüz kilometr qaça bilir", text: "Mətn.", movzu: "gepard", klip: [], sourceUrl: "https://en.wikipedia.org/wiki/Cheetah" }; };
    const base = { articles: [], now: NOW, fetch: async () => ({ ok: false }), cats: [], log: () => {}, maraqli };
    // Cədvəl üzrə (avtomatik): uyğun xəbər yoxdur, pəncərə boş qalır — maraqlı video doldurmur.
    const logs = [];
    assert.equal(await SV.sec({ ...base, env: { VIDEO_ACAR: "1", X_VIDEO: "0", DUNYA_VIDEO: "0" }, state: SV.readState("/yoxdur", NOW), dir: tmp(), log: s => logs.push(s) }), null);
    assert.equal(asked, 0);
    assert.ok(logs.some(s => /maraqlı video söndürülüb/.test(s)), logs.join(" | "));
    // Əl ilə «tur: maraqli» paylaşma ilə: hazırlanmır.
    assert.equal(await SV.sec({ ...base, env: { VIDEO_ACAR: "1", VIDEO_TUR: "maraqli" }, state: SV.readState("/yoxdur", NOW), dir: tmp() }), null);
    assert.equal(asked, 0, "paylaşım yolu bağlıdır");
    // Önizləmə (paylas=false): sınaq yolu qalır.
    const st = SV.readState("/yoxdur", NOW), x = await SV.sec({ ...base, env: { VIDEO_PAYLAS: "0", VIDEO_TUR: "maraqli" }, state: st, dir: tmp() });
    assert.equal(x?.tur, "maraqli");
    assert.equal(asked, 1);
    assert.deepEqual([st.v, st.m, st._last], [{}, {}, 0], "önizləmə siyahını dəyişmir");
  });
  // Hazır maraqlı video şəbəkəyə getmir (Facebook/Instagram sorğusu yoxdur), MARAQLI_VIDEO=1 olmadan.
  const dir = tmp();
  fs.writeFileSync(path.join(dir, "xeber.json"), JSON.stringify({ ...JSON.parse(read("tests/fixtures/video-maraqli.json")), tur: "maraqli", kind: "maraqli" }));
  fs.writeFileSync(path.join(dir, "video.mp4"), Buffer.alloc(1000));
  fs.writeFileSync(path.join(dir, "video.json"), "{}");
  const calls = [], logs = [], state = SV.readState("/yoxdur", NOW);
  const r = await SV.paylas({ dir, env: { FB_PAGE_ID: "1470", FB_PAGE_TOKEN: "TOKEN1234567890" }, now: NOW, state, fetch: async u => { calls.push(u); return { ok: false }; }, log: s => logs.push(s) });
  assert.deepEqual(r, { posted: [], failed: [] });
  assert.deepEqual(calls, []);
  assert.ok(logs.some(s => /paylaşılmır/.test(s)));
  // İş axını: TikTok/YouTube və «Paylaş» maraqlı videoda bağlıdır; PR nümunəsi (sınaq yolu) qalır; paylaşma addımı dəyişəni görür.
  const wf = read(".github/workflows/sosial-video.yml");
  const gate = "(steps.sec.outputs.tur != 'maraqli' || vars.MARAQLI_VIDEO == '1')";
  assert.ok(wf.includes(`paylas: \${{ steps.sec.outputs.hazir == '1' && github.event_name != 'pull_request' && (github.event_name != 'workflow_dispatch' || inputs.paylas) && ${gate} && '1' || '0' }}`));
  const pay = wf.slice(wf.indexOf("      - name: Paylaş\n"), wf.indexOf("      - name: Siyahını saxla"));
  assert.ok(pay.includes(`inputs.paylas) && ${gate}\n`) && pay.includes("MARAQLI_VIDEO: ${{ vars.MARAQLI_VIDEO }}"), pay);
  assert.ok(wf.includes(`'["xeber","hava","maraqli"]'`), "PR-da maraqlı nümunə (paylaşılmır) qalır");
});

// --- A3: 15 istiqamət ----------------------------------------------------------------------------------------------------------
// Böyük Azərbaycan Instagram hesablarının (baku.es, maraqli.tv, oxuaz, crossmedia) ən çox baxılan Reels-ləri, sahibin sırası ilə.
const NUMUNE = [
  ["ordu", "Allah bütün əsgərlərimizi qorusun"], ["taninmis", "Elmira Şabanova dünyasını dəyişdi"], ["insan", "İtkin düşən kişini gənclər tapdı"],
  ["polis", "7 nəfər narkotik satışına görə saxlanıldı"], ["firildaq", "AZS Company adından işə düzəltmə fırıldağı"], ["qeza", "Bakıda zəncirvari qəza"],
  ["seher", "Xəzər rayonunda evləri su basdı"], ["hava", "Quba-Qusarda ilk qar yağdı"], ["yerli_idman", "«Qarabağ» 5 oyundur uda bilmir"],
  ["xarici_futbol", "Real Madrid Çempionlar Liqasında qalib gəldi"], ["avto_yaris", "MotoGP yarışında pilot təhlükəli manevr etdi"],
  ["konsert", "Block3 konsertindən sonra Bayraq meydanı"], ["turkiye", "İstanbulda qaçan şir"], ["texnologiya", "GTA 6 nə vaxt çıxacaq"],
  ["ekstremal", "Uçurumun kənarında son anda xilas olundu"],
];
test("istiqamətlər: the profile carries the owner's 15 directions in his order; each matches its Instagram example", () => {
  const D = DL.dil("az"), g = require("../.github/video-dil/az.json").lent.ceki.guclu;
  assert.deepEqual(g.map(x => x.ad), NUMUNE.map(x => x[0]), "sahibin nömrələri: 1 ordu … 15 ekstremal");
  for (const x of g) assert.ok(x.emsal > 1 && x.emsal <= 1.6, `${x.ad}: əmsal`);
  for (const [ad, t] of NUMUNE) assert.ok(D.re.guclu.find(x => x.ad === ad).re.test(t), `${ad}: ${t}`);
  // X və dünyada önə keçənlər (sahib): xarici futbol, avto yarış (və yarış qəzaları), qəzalar, ekstremal hadisələr — ən böyük X əmsalı.
  const xEmsal = Object.fromEntries(g.map(x => [x.ad, x.x || x.emsal])), top = Math.max(...Object.values(xEmsal));
  assert.deepEqual(Object.keys(xEmsal).filter(k => xEmsal[k] === top).sort(), ["avto_yaris", "ekstremal", "qeza", "xarici_futbol"]);
  assert.equal(DL.istiqamet("Formula 1 yarışında qəza", D, { x: true }).emsal, top, "yarış qəzası");
  // Söz sərhədi və oxşar sözlər: «sabah» (sabahkı gün) klub deyil, «şirin» şir deyil, «tələbə» tələ deyil, «Brentford» zəif deyil.
  for (const t of ["Sabah qar yağacaq", "Şirin tort resepti", "Tələbələr imtahan verdi", "Noyabr ayı isti keçdi", "Qaziyev nazir oldu"]) assert.equal(DL.istiqamet(t, D), null, t);
  assert.equal(D.re.cixar.test("Şirin tort resepti"), false);
  assert.equal(D.re.zeif.test("Brentford Arsenalı məğlub etdi"), false);
});

test("istiqamətlər: news video order — strong directions up, official events down (owner's weak list), animal/nature/space facts down", () => {
  // Zəif (sahib): rəsmi səfər/görüş, nazir görüşü, bəyanat, statistika, neft qiyməti, ildönümü, yubiley.
  for (const t of ["Nazir səfirlə görüşüb", "XİN bəyanat yayıb", "Statistika Komitəsi: əhalinin sayı artıb", "Neftin qiyməti bahalaşıb",
    "Universitetin 100 illik yubileyi", "Zəfərin ildönümü qeyd olunub", "Rəsmi səfər çərçivəsində memorandum imzalanıb"]) assert.equal(SV.cekisi(art(t)), 0.6, t);
  // Güclü: əmsal bölmə əmsalına vurulur; bir neçə istiqamət varsa ən böyüyü.
  assert.equal(SV.cekisi(art("Bakıda zəncirvari qəza")), 1.5);
  assert.ok(near(SV.cekisi(art("Tanınmış müğənninin konserti ləğv olunub", { category: "medeniyyet" })), 1.4 * 1.6));
  assert.ok(near(SV.cekisi(art("Millimiz Macarıstanı məğlub edib", { category: "idman" })), 1.3 * 1.3));
  assert.equal(SV.cekisi(art("Xəbər", { summary: "Hadisə yerinə polis çağırılıb." })), 1.5, "xülasə də sayılır");
  // Rəsmi tədbirdə güclü söz olsa da əmsal verilmir (Şəhidlər xiyabanı ziyarəti bəyanatla).
  assert.equal(SV.cekisi(art("Şəhid ailələri ilə görüş keçirilib")), 0.6);
  // Heyvan, təbiət, kosmos: insan hadisəsi yoxdursa zəif; hadisədirsə güclü (İstanbulda qaçan şir, itlərin hücumu).
  assert.equal(SV.cekisi(art("Zooparka yeni zürafə gətirildi")), 0.6);
  assert.equal(SV.cekisi(art("NASA-nın teleskopu yeni planet tapdı")), 0.6);
  assert.equal(SV.cekisi(art("İstanbulda qaçan şir")), 1.25);
  assert.equal(SV.cekisi(art("Sahibsiz itlər yeniyetməyə hücum etdi")), 1.5);
  // 4 mənbəli qəza 6 mənbəli sammiti qabaqlayır; mənbə həddi əmsalsızdır.
  const S = require("../.github/scripts/social.cjs"), src = n => Array(n - 1).fill({ source: "X" });
  const at = new Date(NOW - 10 * 60e3).toISOString();
  const list = [art("Bakıda beynəlxalq sammit keçiriləcək", { id: "b".padEnd(16, "0"), alts: src(6), publishedAt: at }),
    art("Xırdalanda avtobus çuxura düşdü", { id: "c".padEnd(16, "0"), alts: src(4), publishedAt: at }),
    art("Bakıda zəncirvari qəza", { id: "d".padEnd(16, "0"), alts: src(3), publishedAt: at })];
  assert.deepEqual(S.candidates(list, NOW, { minSources: 4, maxAgeH: 3, weight: a => SV.cekisi(a) }).map(a => a.id[0]), ["c", "b"]);
  // Sınaq dili: istiqamətlər profildəndir.
  assert.equal(require("../.github/video-dil/az.json").lent.ceki.guclu.length, 15);
});

// --- A2: X videoları ------------------------------------------------------------------------------------------------------------
const xi = (id, o = {}) => ({ id: String(id), a: "TheFigen_", n: "Figen", m: "maraqli", u: `https://video.twimg.com/amplify_video/${id}/vid/a.mp4`, w: 720, h: 1280,
  t: new Date(NOW - 2 * 3600e3).toISOString(), v: 500000, c: "Gənc oğlan küçədə rəqs nümayiş etdirir, izləyicilər onu alqışlayır.", ...o });
test("X: no animals, nature or space (owner 2026-11-26) — the nature group is out, animal/space captions only inside a human event; races, crashes, football and extreme moments lead", () => {
  const w = require("../.github/video-dil/az.json").x.movzular;
  assert.ok(!("tebiet" in w), "heyvan və təbiət qrupu çıxıb");
  assert.ok(w.idman > 1 && w.idman >= w.elm, "idman qalxıb");
  const items = [
    xi(200001, { v: 900000 }),                                                                                       // rəqs: konsert 1,3
    xi(200002, { m: "idman", a: "F1", v: 700000, c: "Formula 1 yarışında maşın divara çırpıldı, pilot son anda salamat çıxdı." }),
    xi(200003, { v: 3000000, c: "Pişik balası ilk dəfə qar görür və sevinclə tullanır, sahibi bunu lentə alıb." }),
    xi(200004, { m: "elm", a: "esa", v: 2000000, c: "Yeni raket kosmosa buraxılıb, start anı minlərlə insanı heyran edib." }),
    xi(200005, { m: "tebiet", a: "HavaForum", v: 4000000, c: "Fırtınada ağac maşının üstünə aşdı, sürücü son anda xilas oldu." }),
    xi(200006, { m: "xeber", a: "bpthaber", v: 300000, c: "İstanbulda zooparkdan qaçan şir küçədə görüldü, polis ərazini bağladı." }),
  ];
  const pool = VD.xNamizedler(items, { state: {}, now: NOW, policy: () => false });
  // 700 000 × 1,3 (idman) × 1,7 (avto yarış / qəza) = 1 547 000 > 900 000 × 1,3 × 1,3 (konsert) = 1 521 000.
  assert.deepEqual(pool.map(c => c.x.id), ["200002", "200001", "200006"]);
  assert.equal(pool[2].ist, "polis", "şir — insan hadisəsinin içində (polis, İstanbul)");
});

test("X: extreme-weather accounts moved to the news group (owner 2026-11-26: «ekstremal hadisələrə də») — a rescue in a storm goes, a nature view does not", () => {
  // Qrup xəritəsi oz_x.py-dadır (VIDEOLENT_QRUPLAR; reels.json-da m = qrup): «tebiet» sosial videoya düşmür, «xeber» düşür.
  const items = [
    xi(200101, { m: "xeber", a: "HavaForum", v: 400000, c: "Fırtınada ağac maşının üstünə aşdı, sürücü son anda xilas oldu." }),
    xi(200102, { m: "xeber", a: "RyanHallYall", v: 900000, c: "Şəlalə üzərində günəşli havada göy qurşağı yaranıb, mənzərə heyran edir." }),
  ];
  const pool = VD.xNamizedler(items, { state: {}, now: NOW, policy: () => false });
  assert.deepEqual(pool.map(c => c.x.id), ["200101"], "xilasetmə keçir, təbiət mənzərəsi keçmir");
  assert.equal(pool[0].ist, "ekstremal");
  const oz = read("oz_x.py"), teb = oz.slice(oz.indexOf('"tebiet": {'), oz.indexOf('"elm": {')), xeb = oz.slice(oz.indexOf('"xeber": {'), oz.indexOf('"idman": {'));
  for (const h of ["HavaForum", "US_Stormwatch", "RyanHallYall", "MaxVelocityWX"]) {
    assert.ok(xeb.includes(`"${h}":`), `${h} xeber qrupunda`);
    assert.ok(!teb.includes(`"${h}":`), `${h} tebiet qrupunda deyil`);
  }
});

test("X: REELS_PROMPT (the site's Videolent picker) — no animals in «hadise»; the owner's directions with crashes, extreme moments, foreign football and races first", () => {
  const src = read(".github/scripts/x_yazici.py"), p = src.slice(src.indexOf('REELS_PROMPT = """'), src.indexOf('""".replace("{saxta}", SAXTA)\nREEL_META'));
  const hadise = p.slice(p.indexOf("«hadise»"), p.indexOf("«usta»"));
  assert.ok(hadise.length > 200);
  assert.ok(!/heyvanlar|təbiət hadisəsi/.test(hadise), "heyvanlar və təbiət hadisəsi çıxıb");
  for (const w of ["qəzalar", "təbii fəlakətin anı", "Çempionlar Liqası", "Formula 1", "yarış qəzaları", "motokross", "polis və cinayət", "insan hekayəsi",
    "Türkiyədən viral", "konsert və şou", "faktiki hava", "fırıldaq", "Heyvan faktı, təbiət və kosmos sənədli kadrı"]) assert.ok(hadise.includes(w), w);
  assert.ok(hadise.indexOf("qəzalar") < hadise.indexOf("polis və cinayət") && hadise.indexOf("Formula 1") < hadise.indexOf("insan hekayəsi"), "önə keçənlər əvvəldədir");
});

// --- A2/A3: dünya videoları -----------------------------------------------------------------------------------------------------
test("dünya videosu: the owner's numbered directions (no animals, nature, space), crashes/extreme/football/races first; space sources removed; the code re-checks Gemini's pick", async () => {
  assert.deepEqual(VD.DUNYA_ISTIQAMET.slice(0, 4), [6, 15, 10, 11]);
  for (const n of [1, 7, 9]) assert.ok(!VD.DUNYA_ISTIQAMET.includes(n), `yerli istiqamət ${n}`);
  const c = { a: { source: "Sınaq TV" }, m: { dil: "en" }, source: "Firefighters rescue a dog." };
  const p = VD.promptOf([c]);
  for (const s of ["heyvanlar, təbiət;", "elm, kosmos", "4) heyvan"]) assert.ok(!p.includes(s), s);
  assert.ok(p.indexOf("6) avto və digər qəzalar") < p.indexOf("15) ekstremal") && p.indexOf("15) ekstremal") < p.indexOf("10) xarici futbol")
    && p.indexOf("10) xarici futbol") < p.indexOf("11) avto yarışlar və yarış qəzaları") && p.indexOf("11) avto") < p.indexOf("3) insan hekayəsi"));
  assert.match(p, /heyvan faktı, təbiət və kosmos sənədli kadrı/); assert.match(p, /ölüm anı, qan, meyit/);
  const all = JSON.parse(read(".github/video-dunya.json")).menbeler;
  assert.deepEqual(all.filter(m => /^(ESO|ESA\/|NOIRLab)/.test(m.ad)), [], "kosmos mənbələri çıxıb");
  for (const m of all) assert.equal(VD.kecerli(m), "", m.ad);
  // Gemini heyvan sənədli videosunu seçsə də kod atır; insan hadisəsi olan heyvan videosu keçir.
  const gem = j => async (url, o = {}) => (/models\?pageSize/.test(url) ? { ok: true, json: async () => ({ models: [] }) }
    : { ok: true, status: 200, json: async () => ({ candidates: [{ content: { parts: [{ text: JSON.stringify(j) }] } }] }) });
  const TEXT = "Zooparkda pandanın balası ilk dəfə ziyarətçilərə göstərilib və bu an kameraya düşüb. Bala anasının yanında oynayır, ana isə onu bir an da gözdən qoymur. Zooparkın işçiləri balanın sağlam olduğunu və yaxşı qidalandığını deyiblər. Ziyarətçilər onu görmək üçün səhərdən uzun növbədə dayanıblar. Bala bir neçə həftə sonra anası ilə birlikdə açıq meydançaya çıxacaq.";
  const pool = [{ a: { id: "p1", title: "Panda cub", summary: "", category: "dunya", lang: "en", source: "Sınaq TV", sourceUrl: "https://tv.example/v/9" }, m: { dil: "en" }, source: "A panda cub was shown to visitors at the zoo." }];
  const s = await VD.sec(pool, { env: { GEMINI_API_KEY: "g" }, fetch: gem({ sec: 1, istiqamet: 3, basliq: "Zooparkda pandanın balası ilk dəfə göstərildi", text: TEXT }), log: () => {} });
  assert.match(s.yox, /heyvan, təbiət və ya kosmos/);
  const s2 = await VD.sec(pool, { env: { GEMINI_API_KEY: "g" }, fetch: gem({ sec: 1, istiqamet: 99, basliq: "Zooparkdan qaçan panda küçədə polisi təşvişə saldı", text: TEXT.replace("Zooparkda", "Polis zooparkda") }), log: () => {} });
  assert.ok(!s2.yox, s2.yox);
  assert.equal(s2.istiqamet, 0, "siyahıda olmayan nömrə yazılmır");
});

// --- B: X videosu: baxış sayı yox; şərh paylaşımın faktlarındandır; kadrlar mətnlə tutuşdurulur ----------------------------------------
// Sahib, 2026-11-27: «belə çox qısa və şərhi çox az və başa düşülməyən olmasın videolar». Kadr təsviri mətnə yazılmır; Gemini yalnız
// deyilən hadisənin kadrlarda görünüb-görünmədiyini və qan, meyit olub-olmadığını deyir.
const METN = "Yük maşını dar dağ yolunda dönməyə çalışır. Hadisə Peru dağlarında, uçurumun kənarındakı dar yolda baş verib. Sürücü maşını bir neçə cəhddən sonra döndərə bilib və yola davam edib.";
const X = { id: VD.xId("300001"), tur: "x", kind: "x", title: "Yük maşını dar dağ yolunda dönməyə çalışır", text: METN, izah: "Yük maşını dar dağ yolunda dönməyə çalışır.",
  metn: "paylasim", source: "Figen (X)", sourceUrl: "https://x.com/TheFigen_/status/300001", baxis: 4200000 };
const JPG = [Buffer.from("k1"), Buffer.from("k2"), Buffer.from("k3"), Buffer.from("k4"), Buffer.from("k5")];
function gemini(answer) {
  const seen = { parts: null, asked: 0 };
  const f = async (url, o = {}) => {
    if (/models\?pageSize/.test(url)) return { ok: true, json: async () => ({ models: [] }) };
    seen.asked++; seen.parts = JSON.parse(o.body).contents[0].parts;
    return { ok: true, status: 200, json: async () => ({ candidates: [{ content: { parts: [{ text: typeof answer === "string" ? answer : JSON.stringify(answer) }] } }] }) };
  };
  return { f, seen };
}
test("X kadrlar: Gemini compares the video's own frames with the voice text — the event not visible, or blood/death → not shared; nothing is added to the text", async () => {
  const { f, seen } = gemini({ gorunur: true, qan: false, sebeb: "" });
  const opt = { dir: tmp(), env: { GEMINI_API_KEY: "g", VIDEO_GEMINI_WAIT_MS: "0" }, fetch: f, log: () => {}, deps: { kadrlar: () => JPG } };
  assert.deepEqual(await VD.xKadrYoxla(X, opt), { ok: true });
  // Sorğu: göstəriş + 4 kadr (şəkil); diktorun bütün mətni.
  assert.equal(seen.parts.filter(p => p.inline_data).length, 4);
  assert.ok(seen.parts.every(p => !p.inline_data || p.inline_data.mime_type === "image/jpeg"));
  const prompt = seen.parts[0].text;
  for (const w of ["\"gorunur\": false", "yalnız ekran yazısı", "teleyayımın xəbərdarlıq zolağı", "Əmin deyilsənsə true yaz", "\"qan\": true", `Mətn: ${METN}`, "Azərbaycan ədəbi dilində"]) assert.ok(prompt.includes(w), w);
  // Silinən video kimi: hadisə görünmür — paylaşılmır, səbəbi ilə.
  assert.deepEqual(await VD.xKadrYoxla(X, { ...opt, fetch: gemini({ gorunur: false, qan: false, sebeb: "Kadrlarda yalnız adi oyun görünür." }).f }),
    { dayan: "deyilən hadisə kadrlarda görünmür (Kadrlarda yalnız adi oyun görünür.)" });
  assert.deepEqual(await VD.xKadrYoxla(X, { ...opt, fetch: gemini({ gorunur: true, qan: true }).f }), { dayan: "kadrda ölüm anı, qan və ya meyit görünür" });
  // Şərh azdır və ya paylaşımın faktı yoxdur — kadra baxılmadan dayanır (seçim onsuz da götürmür; bu ikinci qapıdır).
  const g = gemini({ gorunur: true });
  assert.match((await VD.xKadrYoxla({ ...X, text: `${X.izah} Sürücü sonda yolu keçə bilir.` }, { ...opt, fetch: g.f })).dayan, /şərh azdır: 2 cümlə/);
  assert.match((await VD.xKadrYoxla({ ...X, metn: "basliq" }, { ...opt, fetch: g.f })).dayan, /paylaşımın faktları yoxdur/);
  assert.equal(g.seen.asked, 0);
  // Yoxlamaq mümkün deyil — video gedir (mətni seçimdə yoxlanıb).
  assert.deepEqual(await VD.xKadrYoxla(X, { ...opt, env: {} }), { kecdi: "GEMINI_API_KEY yoxdur" });
  assert.match((await VD.xKadrYoxla(X, { ...opt, deps: { kadrlar: () => { throw new Error("ffmpeg yoxdur"); } } })).kecdi, /kadrlar alınmadı: ffmpeg yoxdur/);
  assert.deepEqual(await VD.xKadrYoxla(X, { ...opt, deps: { kadrlar: () => [] } }), { kecdi: "kadr yoxdur" });
  assert.deepEqual(await VD.xKadrYoxla(X, { ...opt, fetch: gemini("bu JSON deyil").f }), { kecdi: "cavab JSON deyil" });
  const none = async url => (/models\?pageSize/.test(url) ? { ok: true, json: async () => ({ models: [] }) } : { ok: false, status: 400, json: async () => ({}) });
  assert.deepEqual(await VD.xKadrYoxla(X, { ...opt, fetch: none }), { kecdi: "Gemini cavab vermir" });
  assert.equal(VD.xKadrMetn, undefined, "kadr təsviri mətnə yazılmır");
  // Kadrlar video arxivinin yolu ilə çıxarılır (ffprobe + ffmpeg).
  const VA = require("../.github/scripts/video-arxiv.cjs");
  assert.equal(typeof VA.probe, "function"); assert.equal(typeof VA.kadrlar, "function");
});

test("X kadrlar: the «x-kadr» step stops an X video with too little text (red, not shared) and leaves xeber.json alone; a non-X video passes; the step sits between ffmpeg and the render", () => {
  const run = dir => cp.spawnSync(process.execPath, [".github/scripts/sosial-video.cjs", "x-kadr", dir], { cwd: root, encoding: "utf8",
    env: Object.fromEntries(Object.entries(process.env).filter(([k]) => !["GEMINI_API_KEY", "GITHUB_OUTPUT"].includes(k))) });
  const dir = tmp(), qisa = JSON.stringify({ ...X, text: `${X.izah} Stadionda idmançılar yaşıl sahə üzərində dayanaraq oyununu davam etdirirlər.` });
  fs.writeFileSync(path.join(dir, "xeber.json"), qisa);
  const r = run(dir);
  assert.equal(r.status, 1, r.stdout + r.stderr);
  assert.match(r.stdout, /::error::X videosu paylaşılmır — şərh azdır: 2 cümlə/);
  assert.equal(fs.readFileSync(path.join(dir, "xeber.json"), "utf8"), qisa, "mətn dəyişmir");
  // Şərhi yetərli, açar yoxdur: yoxlanmır, video gedir.
  const d1 = tmp();
  fs.writeFileSync(path.join(d1, "xeber.json"), JSON.stringify(X));
  const r1 = run(d1);
  assert.equal(r1.status, 0, r1.stdout + r1.stderr);
  assert.match(r1.stdout, /kadrlar yoxlanmadı \(GEMINI_API_KEY yoxdur\)/);
  const d2 = tmp(), xeber = JSON.stringify({ tur: "dunya", text: "Mətn." });
  fs.writeFileSync(path.join(d2, "xeber.json"), xeber);
  assert.equal(run(d2).status, 0);
  assert.equal(fs.readFileSync(path.join(d2, "xeber.json"), "utf8"), xeber);
  const wf = read(".github/workflows/sosial-video.yml");
  const i = { ffmpeg: wf.indexOf("      - name: ffmpeg və şrift"), kadr: wf.indexOf("      - name: 'X: kadrları yoxla'"), render: wf.indexOf("      - name: Video hazırla") };
  assert.ok(i.ffmpeg > 0 && i.ffmpeg < i.kadr && i.kadr < i.render, JSON.stringify(i));
  const step = wf.slice(i.kadr, wf.indexOf("\n      - ", i.kadr + 10));
  assert.ok(step.includes("if: steps.sec.outputs.hazir == '1' && steps.sec.outputs.tur == 'x'") && step.includes("GEMINI_API_KEY: ${{ secrets.GEMINI_API_KEY }}")
    && step.includes("run: node .github/scripts/sosial-video.cjs x-kadr video-out"), step);
  assert.ok(!step.includes("continue-on-error"), "dayanan video: sonrakı addımlar (video, paylaşma) işləmir");
});

// Şərh həddi hər videoda (hava videosundan başqa): «Videonu yoxla» addımı paylaşımdan əvvəl, PR nümunəsindən başqa.
test("şərh həddi: the «Videonu yoxla» step refuses any non-weather video with less than 3 sentences / 180 characters of voice text, outside PR samples", () => {
  const wf = read(".github/workflows/sosial-video.yml");
  const a = wf.indexOf("      - name: Videonu yoxla"), step = wf.slice(a, wf.indexOf("\n      - ", a + 10));
  assert.ok(step.includes("EVENT: ${{ github.event_name }}"), "addım hadisəni bilir");
  assert.ok(step.includes(`if (process.env.EVENT !== "pull_request" && process.env.TUR !== "hava") { const az = require("./.github/scripts/video-ssenari.cjs").serhAzdir(m.text); if (az) bad.push(az); }`), step);
  // Addımın skripti eyni yolla işləyir: qısa mətn — xəta, uzun mətn — keçir.
  const js = step.slice(step.indexOf("node -e '") + 9, step.indexOf("\n          '", step.indexOf("node -e '")));
  const yoxla = (text, env, extra = {}) => {
    const d = tmp();
    fs.mkdirSync(path.join(d, "video-out"));
    fs.writeFileSync(path.join(d, "video-out", "video.json"), JSON.stringify({ width: 1080, height: 1920, vcodec: "h264", pix: "yuv420p", fps: "30/1", acodec: "aac", rate: 48000, channels: 2,
      duration: 30, bytes: 2e6, own: true, id: "x1", text, ...extra }));
    fs.writeFileSync(path.join(d, "video-out", "video.mp4"), Buffer.concat([Buffer.from("....ftypisom....moov....8ulduz.az....", "latin1"), Buffer.alloc(1000)]));
    // Skript repo kökündən işləyir: modulu kökdən götürsün, video-out isə sınaq qovluğundadır.
    const kok = js.split("require(\"./.github/scripts/").join(`require("${root.replace(/\\/g, "/")}/.github/scripts/`);
    return cp.spawnSync(process.execPath, ["-e", kok], { cwd: d, encoding: "utf8", env: { ...process.env, ...env } });
  };
  const qisa = "Bears-Lions matçı zamanı efirə ABŞ-ın təcili xəbərdarlıq sistemi daxil olub. Stadionda idmançılar yaşıl sahə üzərində dayanaraq oyununu davam etdirirlər.";
  const r = yoxla(qisa, { EVENT: "workflow_dispatch", TUR: "x" });
  assert.equal(r.status, 1); assert.match(r.stdout, /Video tələbə uyğun deyil: şərh azdır: 2 cümlə, 153 simvol/);
  assert.equal(yoxla(qisa, { EVENT: "pull_request", TUR: "" }).status, 0, "PR nümunəsi (montaj yoxlaması) dayanmır");
  assert.equal(yoxla(`Bakıda hava buludlu olacaq. Open-Meteo.`, { EVENT: "workflow_dispatch", TUR: "hava" }, { kind: "hava", url: "https://8ulduz.az/" }).status, 0, "hava videosunun öz quruluşu var");
  assert.equal(yoxla(`${qisa} Hadisədən sonra oyun bir müddət dayandırılıb, azarkeşlər isə tribunada gözləyiblər.`, { EVENT: "workflow_dispatch", TUR: "x" }).status, 0);
});
