// Media qaydası (sahib, 2026-11-27). Sahib mətbuatın ümumi qadağalarını istədi; ona «Media haqqında» Qanunun 14.1, 15.1 və 21-ci maddələri,
// Meta-nın qrafik məzmun qaydaları və beş təklif göstərildi, cavab: «Hamısını əlavə et» (docs/sosial-video.md «Media qaydası»).
//   1) azyaşlı zərərçəkən və şübhəlinin adı (15.1.5), 2) təqsirsizlik prezumpsiyası (14.1.14), 3) söyüş (14.1.6), 4) intiharın üsulu,
//   5) çılpaqlıq (14.1.13) və azyaşlının üzü — kadrda.
// Mətn qaydaları video-qayda.cjs-dədir, hər diktor mətni VS.checkText ilə ondan keçir. Kadr yoxlaması seçimin içindədir (X, kanal,
// dünya videosu, mənbə videolu xəbər). Şəbəkə, Gemini və ffmpeg burada işləmir: hamısı saxtadır.
"use strict";
const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("fs"), os = require("os"), path = require("path");

const VQ = require("../.github/scripts/video-qayda.cjs");
const VS = require("../.github/scripts/video-ssenari.cjs");
const VD = require("../.github/scripts/video-dunya.cjs");
const K = require("../.github/scripts/video-kanal.cjs");
const M = require("../.github/scripts/video-menbe.cjs");
const SV = require("../.github/scripts/sosial-video.cjs");
const DL = require("../.github/scripts/video-dil.cjs");
const root = path.resolve(__dirname, "..");
const read = f => fs.readFileSync(path.join(root, f), "utf8").replace(/\r\n/g, "\n");
const tmp = () => fs.mkdtempSync(path.join(os.tmpdir(), "qayda-"));
const NOW = Date.parse("2026-11-27T10:00:00Z");
const ENV = { GEMINI_API_KEY: "g", VIDEO_GEMINI_WAIT_MS: "0" };
const JPG = [Buffer.from("k1"), Buffer.from("k2"), Buffer.from("k3"), Buffer.from("k4"), Buffer.from("k5")];
const ok = s => assert.equal(VQ.yoxla(s), "", s);
const red = (s, re) => assert.match(VQ.yoxla(s), re, s);
async function withOutput(fn) {
  const old = process.env.GITHUB_OUTPUT;
  process.env.GITHUB_OUTPUT = path.join(tmp(), "out.txt");
  try { return await fn(); } finally { if (old === undefined) delete process.env.GITHUB_OUTPUT; else process.env.GITHUB_OUTPUT = old; }
}
// Gemini sınağı: j — cavab (obyekt, mətn və ya null: cavab vermir); seen.parts — son sorğunun hissələri.
const gem = (j, seen = {}) => async (url, o = {}) => {
  if (/models\?pageSize/.test(url)) return { ok: true, json: async () => ({ models: [] }) };
  seen.parts = JSON.parse(o.body).contents[0].parts;
  const a = typeof j === "function" ? j(seen.parts[0].text) : j;
  return a == null ? { ok: false, status: 400, json: async () => ({}) } : { ok: true, status: 200, json: async () => ({ candidates: [{ content: { parts: [{ text: typeof a === "string" ? a : JSON.stringify(a) }] } }] }) };
};

// --- 1. Azyaşlı zərərçəkən və şübhəli (Qanun 15.1.5) --------------------------------------------------------------------------------
test("media qaydası 1: a minor + victim/suspect + a person's name together → no video; an unnamed (rescued) child, a named adult or a named minor without an incident pass", () => {
  red("Sumqayıtda 15 yaşlı Əli Məmmədov bıçaqlanıb.", /azyaşlı zərərçəkən və ya şübhəlinin adı var .*15\.1\.5/);
  red("Murad adlı yeniyetmə polis tərəfindən saxlanılıb.", /azyaşlı/);
  red("Şagird Aysel Həsənova itkin düşüb, axtarışlar davam edir.", /azyaşlı/);
  red("Polis Rəşad Elman oğlu Məmmədovu saxlayıb, o, 16 yaşlıdır.", /azyaşlı/);
  red("Məktəbli qız döyülüb. Hadisədə Nigar Quliyevanın adı çəkilir.", /azyaşlı/, "ad başqa cümlədə olsa da");
  red("Azyaşlı uşağa təcavüz edən şəxs saxlanılıb, zərərçəkən Leyla Nəsirlidir.", /azyaşlı/);
  // Adı jurnala yazılmır (iş jurnalı açıqdır).
  assert.ok(!VQ.yoxla("Sumqayıtda 15 yaşlı Əli Məmmədov bıçaqlanıb.").includes("Məmmədov"));
  ok("Yanğında 5 yaşlı uşaq xilas edilib, xəsarət alan yoxdur.");
  ok("Polis 5 yaşlı uşağı itkin düşdüyü yerdən tapıb, uşaq ailəsinə qaytarılıb.");
  ok("15 yaşlı Nigar Quliyeva olimpiadada qalib gəlib.");
  ok("Əli Məmmədov saxlanılıb.");
  ok("21 yaşlı Əli Məmmədov saxlanılıb.");
  ok("Azərbaycan Milli Məclisinin deputatı uşaqların xəsarət almasından danışıb.");
  ok("Bakıda uşaq bağçasında yanğın olub, Əli Məmmədov xəsarət alıb.");
  ok("Respublika Daxili İşlər Nazirliyi 16 yaşlı yeniyetmənin saxlanıldığını bildirib.");
});

// --- 2. Təqsirsizlik prezumpsiyası (14.1.14) ------------------------------------------------------------------------------------------
test("media qaydası 2: person labels (qatil, dələduz, cinayətkar…) only after a court verdict; crime nouns and organisations pass", () => {
  for (const s of ["Polis qatili saxlayıb.", "QATİL SAXLANILDI", "Dələduzlar tutulub.", "Cinayətkar dəstənin üzvləri saxlanılıb.", "Oğrunu kamera görüntüləri ilə tapıblar.",
    "Quldurların biri yaralanıb.", "Manyak qadınlara hücum edib.", "Terrorçular saxlanılıb.", "Narkotacir saxlanılıb.", "Qaçaqmalçılar yaxalanıb.", "Pedofil həbs olunub.",
    "Təcavüzkar saxlanılıb.", "Qızı zorlayan şəxs saxlanılıb.", "Rüşvətxor məmur saxlanılıb."]) red(s, /məhkəmə hökmü olmadan .*14\.1\.14/);
  assert.match(VQ.yoxla("Dələduzlar tutulub."), /«şübhəli», «təqsirləndirilən» yazılmalıdır/);
  for (const s of ["Dələduzluq faktı ilə bağlı cinayət işi başlanıb, oğurluq və qətl araşdırılır.", "Terrorçu təşkilatın üzvləri saxlanılıb.", "Terrorçuluq ittihamı ilə saxlanılıb.",
    "Qaçaqmalçılıq və pedofiliya ilə mübarizə gücləndirilib.", "Təcavüzkar Ermənistan illərlə torpaqlarımızı işğal altında saxlayıb.", "Oğrun-oğrun baxırdı.",
    "Qatılıb", "Şübhəli saxlanılıb, ona təqsirləndirilən qismində ittiham elan olunub.", "Fırıldaqçılar bank əməkdaşı kimi təqdim olunur."]) ok(s);
  ok("Məhkəmədə hökm oxunub: qatil 15 il azadlıqdan məhrum edilib.");
  ok("Dələduz məhkum edilib.");
});

// --- 3. Söyüş (14.1.6) --------------------------------------------------------------------------------------------------------------
test("media qaydası 3: strong Azerbaijani, Turkish and Russian obscenities (blyat variants included) — with word boundaries, so sikkə, musiqi, Sumqayıt, qəhvə, sükut… pass", () => {
  for (const s of ["O, sikdir dedi.", "siktir git", "Blyat dedi.", "blyad", "BLJAT", "Qəhbə.", "amk", "Yarrak", "блять", "бля", "Ana səni götveren", "orospu çocuğu", "qancıq",
    "fuck", "пиздец", "dalbayob"]) red(s, /söyüş var .*14\.1\.6/);
  for (const s of ["Sikkə zərb olunub.", "Siklon yaxınlaşır.", "Musiqi festivalı başlayıb.", "Sumqayıtda yeni park açılıb.", "Qəhvə qiyməti artıb.", "Zalda sükut yarandı.",
    "Yükü götürüb apardılar.", "Ordu yaraq-yasaqla təmin olunub.", "Amina adlı qız qalib gəlib.", "Sakinlər şikayət edib.", "Pizza bayramı keçirilib.", "Blyakher hesabat verib.",
    "Göytəpədə qar yağıb.", "Əsgər silahı götürdü."]) ok(s);
});

// --- 4. İntihar -----------------------------------------------------------------------------------------------------------------------
test("media qaydası 4: suicide may be reported, but never the method, means or place", () => {
  ok("Gənc qadın intihar edib, hadisə araşdırılır.");
  ok("Ailə üzvləri onun həyatına son qoyduğunu bildiriblər, polis araşdırma aparır.");
  red("Gənc qız özünü 9-cu mərtəbədən atıb.", /intiharın üsulu, vasitəsi və ya yeri/);
  red("Kişi intihar edib, onu evində kəndirdən asılmış tapıblar.", /kəndir/);
  red("Gənc özünü asıb.", /intiharın üsulu/);
  red("Tələbə intihar edib: dərman içib.", /intiharın üsulu/);
  red("Kişi körpüdən tullanaraq intihar edib.", /intiharın üsulu/);
  red("Qadın özünü yandırıb.", /intiharın üsulu/);
});

// --- Hər mətn yolundan keçir: checkText, başlıq, profil -------------------------------------------------------------------------------
test("media qaydası: VS.checkText runs it on the title plus the voice text (site news titles come from the source); the test language has no rules", () => {
  const T = "Sumqayıt şəhərində yeniyetmə bıçaqlanıb və xəstəxanaya çatdırılıb. Hadisə axşam saatlarında şəhərin mərkəzi küçələrindən birində baş verib. "
    + "Polis əməkdaşları hadisə yerinə dərhal gəlib və ərazini mühasirəyə alıblar. Yaralı yeniyetmənin vəziyyəti həkimlər tərəfindən orta ağır kimi qiymətləndirilir. "
    + "Faktla bağlı cinayət işi başlanıb və araşdırma davam etdirilir. Hüquq-mühafizə orqanları şahidlərin ifadələrini toplayır.";
  const a = { title: "Sumqayıtda yeniyetmə bıçaqlanıb", category: "hadise" };
  assert.equal(VS.checkText(T, "16", a), "", "adsız yeniyetmə olar");
  assert.match(VS.checkText(T.replace("yeniyetmə bıçaqlanıb", "16 yaşlı Əli Məmmədov bıçaqlanıb"), "16", a), /^media qaydası: azyaşlı/);
  assert.match(VS.checkText(T, "16", { ...a, title: "Sumqayıtda 16 yaşlı Əli Məmmədov bıçaqlanıb" }), /^media qaydası: azyaşlı/, "başlıq da yoxlanır");
  assert.match(VS.checkText(T, "", { ...a, title: "Sumqayıtda qatil saxlanılıb" }), /^media qaydası: məhkəmə hökmü olmadan «qatil»/);
  assert.match(VS.checkText(T.replace("Hüquq-mühafizə", "Şahid «blyat» deyib, hüquq-mühafizə"), "", a), /^media qaydası: söyüş/);
  // Sınaq dili: profilin «qayda» sözləri boşdur — qayda işləmir (yeni dil öz sözlərini öz faylında verir).
  const keep = process.env.VIDEO_DIL_QOVLUQ;
  process.env.VIDEO_DIL_QOVLUQ = path.join(__dirname, "fixtures", "video-dil");
  try { assert.equal(VQ.yoxla("Sumqayıtda 15 yaşlı Əli Məmmədov bıçaqlanıb. Qatil saxlanılıb. Blyat.", DL.dil("xx")), ""); }
  finally { if (keep === undefined) delete process.env.VIDEO_DIL_QOVLUQ; else process.env.VIDEO_DIL_QOVLUQ = keep; }
  assert.deepEqual(Object.keys(DL.dil("az").qayda).sort(), ["ad", "azyasli", "etiket", "hadise", "hokm", "intihar", "soyus", "usul"]);
  // Mətni yoxlayan hər yol checkText-dən keçir: xəbər (ssenari), dünya (sec), X (xMetn), kanal (metnYaz).
  assert.match(read(".github/scripts/video-ssenari.cjs"), /checkText\(text, `\$\{source\}\\n\$\{clean\(a\.title\)\}`, a, policy\)/);
  const vd = read(".github/scripts/video-dunya.cjs"), vk = read(".github/scripts/video-kanal.cjs");
  assert.ok(/VS\.checkText\(text, c\.source, az, policy\)/.test(vd) && /VS\.checkText\(text, `\$\{esli\} \$\{izah\}`, a, policy, X_HED\)/.test(vd));
  assert.match(vk, /VS\.checkText\(text, `\$\{c\.metn\}\\n\$\{c\.esli\}`, a, policy, HED\)/);
});

test("media qaydası: every Gemini text prompt (site news, world, X, kanal) carries the rule; the world and kanal prompts also refuse nudity", () => {
  const g = VQ.GOSTERIS;
  for (const w of ["adını, soyadını, məktəbini, ünvanını yazma", "«15 yaşlı yeniyetmə»", "Məhkəmə hökmü olmadan", "«şübhəli», «təqsirləndirilən»", "Söyüş, kobud söz və jarqon", "İntihar xəbərində üsulu, vasitəni və yeri yazma"]) assert.ok(g.includes(w), w);
  assert.ok(VS.PROMPT.includes(g), "xəbər videosu");
  const pool = [{ a: { source: "Sınaq TV" }, m: { dil: "en" }, source: "A dog was rescued." }];
  assert.ok(VD.promptOf(pool).includes(g) && /çılpaqlıq və ya cinsi\nsəhnə görünən video; azyaşlı zərərçəkənin və ya şübhəlinin üzü görünən video/.test(VD.promptOf(pool)), "dünya videosu");
  assert.ok(VD.xPromptOf("İzah.", "Post", "hesab").includes(g), "X videosu");
  const kp = K.promptOf({ m: { ad: "Oxu.az" }, platforma: "telegram", metn: "Mətn" });
  assert.ok(kp.includes(g) && /çılpaqlıq və ya cinsi səhnə varsa/.test(kp), "kanal videosu");
});

// --- 5. Kadr: qan, çılpaqlıq (14.1.13), azyaşlının üzü (15.1.5) ------------------------------------------------------------------------
test("kadr qaydası: one verdict for X, kanal and source-video checks — blood/corpse, nudity or a sexual scene, a minor victim's or suspect's face; the prompt says «əmin deyilsənsə false yaz»", () => {
  assert.equal(VQ.kadrHokmu({}), "");
  assert.equal(VQ.kadrHokmu({ qan: false, cilpaq: false, usaq: false }), "");
  assert.equal(VQ.kadrHokmu({ qan: "true" }), "", "yalnız true");
  assert.equal(VQ.kadrHokmu({ qan: true }), "kadrda ölüm anı, qan və ya meyit görünür");
  assert.match(VQ.kadrHokmu({ cilpaq: true }), /çılpaqlıq və ya cinsi səhnə .*14\.1\.13/);
  assert.match(VQ.kadrHokmu({ usaq: true }), /azyaşlı zərərçəkənin və ya şübhəlinin üzü .*15\.1\.5/);
  for (const w of ['"cilpaq": true', "cinsi səhnə", '"usaq": true', "18 yaşından kiçik", "xilas edilən və ya sağ-salamat tapılan uşaq sayılmır", "əmin deyilsənsə false yaz"]) assert.ok(VQ.KADR_SETIRLER.includes(w), w);
  for (const p of [VD.X_KADR_PROMPT, K.KADR_PROMPT, M.KADR_PROMPT]) assert.ok(p.includes(VQ.KADR_SETIRLER) && p.includes(VQ.KADR_JSON));
});

test("mənbə videosu kadrı: the generic check for world videos and site news with the source's own video — refuses blood, nudity, a minor's face; can't check → the video goes", async () => {
  const x = { title: "Bakıda yanğın olub", text: "Bakının Xətai rayonunda yaşayış binasında yanğın baş verib. Yanğınsöndürənlər sakinləri təxliyə ediblər.", source: "APA",
    menbeVideo: { file: "klip-menbe.mp4", kredit: "APA" } };
  const seen = {}, files = [];
  const opt = (j, o = {}) => ({ dir: tmp(), env: ENV, fetch: gem(j, seen), log: () => {}, deps: { kadrlar: f => (files.push(f), JPG) }, ...o });
  assert.deepEqual(await M.kadrYoxla(x, opt({ qan: false, cilpaq: false, usaq: false })), { ok: true });
  assert.ok(files[0].endsWith("klip-menbe.mp4"));
  assert.equal(seen.parts.filter(p => p.inline_data).length, 4, "4 kadr");
  for (const w of ["Başlıq: Bakıda yanğın olub", `Mətn: ${x.text}`, "öz videosundandır (APA)", "Azərbaycan ədəbi dilində", VQ.KADR_SETIRLER]) assert.ok(seen.parts[0].text.includes(w), w);
  assert.deepEqual(await M.kadrYoxla(x, opt({ qan: true })), { dayan: "kadrda ölüm anı, qan və ya meyit görünür" });
  assert.match((await M.kadrYoxla(x, opt({ cilpaq: true, sebeb: "Çimərlikdə çılpaq adam" }))).dayan, /çılpaqlıq .*\(Çimərlikdə çılpaq adam\)/);
  assert.match((await M.kadrYoxla(x, opt({ usaq: true }))).dayan, /azyaşlı/);
  assert.deepEqual(await M.kadrYoxla(x, opt({}, { env: {} })), { kecdi: "GEMINI_API_KEY yoxdur" });
  assert.match((await M.kadrYoxla(x, opt({}, { deps: { kadrlar: () => { throw new Error("ffmpeg yoxdur"); } } }))).kecdi, /kadrlar alınmadı: ffmpeg yoxdur/);
  assert.deepEqual(await M.kadrYoxla(x, opt({}, { deps: { kadrlar: () => [] } })), { kecdi: "kadr yoxdur" });
  assert.deepEqual(await M.kadrYoxla(x, opt(null)), { kecdi: "Gemini cavab vermir" });
  assert.deepEqual(await M.kadrYoxla(x, opt("bu JSON deyil")), { kecdi: "cavab JSON deyil" });
  // X və kanal videosu da eyni qərarı verir (yeni sahələr).
  const X = { text: "Yük maşını dar dağ yolunda dönməyə çalışır. Hadisə Peru dağlarında, uçurumun kənarındakı dar yolda baş verib. Sürücü maşını bir neçə cəhddən sonra döndərə bilib və yola davam edib.", metn: "paylasim" };
  assert.match((await VD.xKadrYoxla(X, opt({ gorunur: true, cilpaq: true }))).dayan, /çılpaqlıq/);
  assert.match((await VD.xKadrYoxla(X, opt({ gorunur: true, usaq: true }))).dayan, /azyaşlı/);
  assert.match((await K.kadrYoxla({ ...X, source: "Baku.ws", platforma: "instagram" }, opt({ yazi: false, usaq: true }))).dayan, /azyaşlı/);
});

// --- Seçimin içində: dünya videosu və mənbə videolu xəbər ------------------------------------------------------------------------------
const M1 = { ad: "Sınaq TV", dil: "en", lent: "https://tv.example/rss", nov: "mrss", istiqamet: [3, 15], sertler: "sınaq" };
const RSS = `<rss><channel><item><title>Dog rescued from frozen lake</title><link>https://tv.example/v/1</link><pubDate>Fri, 27 Nov 2026 08:00:00 GMT</pubDate>
<description>Firefighters pulled a dog from a frozen lake in Oslo after hours on the ice. The dog was returned to its owner who had searched all night. Crews used a ladder and ropes to reach the animal, officials said.</description>
<media:content url="https://cdn.tv.example/v/1.mp4" type="video/mp4"/></item></channel></rss>`;
test("dünya videosu: the frames are checked inside the pick, after the download — refused → skipped for good, file removed, the pick falls through to the next kind; can't check → goes", async () => {
  const file = path.join(tmp(), "menbeler.json");
  fs.writeFileSync(file, JSON.stringify({ menbeler: [M1] }));
  const TEXT = "Osloda yanğınsöndürənlər donmuş göldə qalan iti xilas ediblər. Heyvan buzun üstündə saatlarla qalıb. Xilasedicilər itə nərdivan və kəndirlərin köməyi ilə çatıblar. İt sahibinə qaytarılıb.";
  const deps = k => ({ oxu: async () => RSS, sec: async pool => ({ c: pool[0], title: "Osloda donmuş göldən it xilas edildi", text: TEXT, istiqamet: 15 }),
    indir: async (u, f) => (fs.writeFileSync(f, Buffer.from("ftypisom")), ""), kadrYoxla: k });
  const policy = () => false, asked = [];
  const st = SV.readState("/yoxdur", NOW), dir = tmp(), logs = [];
  const r = await VD.hazirla({ now: NOW, state: st, env: ENV, fetch: async () => ({ ok: false }), policy, dir, log: s => logs.push(s), file,
    deps: deps(async (x, o) => { asked.push([x.title, x.text, x.source, typeof o.dir]); return { dayan: "kadrda ölüm anı, qan və ya meyit görünür" }; }) });
  assert.equal(r, null);
  assert.deepEqual(asked, [["Osloda donmuş göldən it xilas edildi", TEXT, "Sınaq TV", "string"]]);
  assert.equal(Object.keys(st.skip).length, 1, "bir də sınanmır");
  assert.ok(!fs.existsSync(path.join(dir, M.FAYL)), "fayl silinir");
  assert.ok(logs.some(s => /dünya videosu: ötürülür \(kadrda ölüm anı, qan və ya meyit görünür\) — Sınaq TV/.test(s)), logs.join(" | "));
  // Yoxlanmadı — video gedir.
  const s2 = SV.readState("/yoxdur", NOW), l2 = [];
  const y = await VD.hazirla({ now: NOW, state: s2, env: ENV, fetch: async () => ({ ok: false }), policy, dir: tmp(), log: s => l2.push(s), file, deps: deps(async () => ({ kecdi: "kadr yoxdur" })) });
  assert.equal(y.tur, "dunya");
  assert.ok(l2.some(s => /kadrlar yoxlanmadı \(kadr yoxdur\) — video gedir/.test(s)));
  // Rədd olunanda seçim növbəti növə keçir (dünya → xəbər): pəncərə boş qalmır, iş qırmızı olmur.
  await withOutput(async () => {
    let dunya = 0;
    const x = await SV.sec({ articles: [], env: { VIDEO_ACAR: "1", X_VIDEO: "0", MARAQLI_VIDEO: "0", TELEGRAM_VIDEO: "0", INSTAGRAM_VIDEO: "0" }, now: NOW, state: SV.readState("/yoxdur", NOW),
      fetch: async () => ({ ok: false }), cats: [], dir: tmp(), log: () => {}, dunya: async () => { dunya++; return null; } });
    assert.deepEqual([x, dunya], [null, 1]);
  });
});

test("xəbər videosu: the source's own video is frame-checked inside the pick — refused → this story is skipped and the next one is taken; a manual pick (VIDEO_XEBER) keeps the story without that video", async () => {
  const FILL = "Layihə sakinlərin rahatlığı üçün nəzərdə tutulub və uzun müddət xidmət göstərəcək. Tikinti işləri müasir standartlara uyğun aparılıb. Ərazidə abadlıq işləri də görülüb və yaşıllıq zolaqları salınıb. Yeni obyekt ətraf məhəllələrin sakinləri üçün də əlçatan olacaq. Rəsmilər bildirib ki, oxşar layihələr digər bölgələrdə də davam etdiriləcək. Sakinlər yeni obyektin açılışını müsbət qarşılayıblar.";
  const body = "Yeni obyekt sakinlərin istifadəsinə verilib. Tikintidə müasir texnologiyalardan istifadə olunub, ərazi geniş salınıb. Obyekt Xətai rayonundadır.";
  const art = (id, title, n) => ({ id: id.padEnd(16, "0"), title, summary: "Qısa xülasə.", category: "gundem", lang: "az", source: "APA", sourceUrl: `https://apa.az/${id}`, video: true,
    publishedAt: new Date(NOW - 10 * 60e3).toISOString(), alts: Array.from({ length: n }, (_, i) => ({ source: `S${i}` })) });
  const a = art("a1", "Bakıda yeni metro stansiyası açılıb - Video", 8), b = art("b1", "Gəncədə yeni idman kompleksi istifadəyə verilib - Video", 5);
  const f = async url => (/models\?pageSize/.test(url) ? { ok: true, json: async () => ({ models: [] }) }
    : /generativelanguage/.test(url) ? { ok: true, status: 200, json: async () => ({ candidates: [{ content: { parts: [{ text: JSON.stringify({ uygun: true, text: FILL, axtar: [] }) }] } }] }) }
    : /^https:\/\/apa\.az\//.test(url) ? { ok: true, status: 200, text: async () => `<html><head><meta property="og:description" content="${body}"></head><body><p>${body}</p></body></html>` }
    : { ok: false, text: async () => "" });
  const mv = { file: "klip-menbe.mp4", url: "https://cdn.apa.az/v/1.mp4", sehife: "", kredit: "APA", bytes: 1 };
  const menbe = async (x, page, o) => { fs.writeFileSync(path.join(o.dir, mv.file), Buffer.from("ftypisom")); return { ...mv, sehife: x.sourceUrl }; };
  const env = { VIDEO_ACAR: "1", GEMINI_API_KEY: "g", DUNYA_VIDEO: "0", X_VIDEO: "0", MARAQLI_VIDEO: "0", TELEGRAM_VIDEO: "0", INSTAGRAM_VIDEO: "0", VIDEO_GEMINI_WAIT_MS: "0" };
  const yoxlandi = [];
  const kadr = async x => { yoxlandi.push(x.title); return /metro/.test(x.title) ? { dayan: "kadrda azyaşlı zərərçəkənin və ya şübhəlinin üzü görünür" } : { ok: true }; };
  await withOutput(async () => {
    const dir = tmp(), st = SV.readState("/yoxdur", NOW);
    const x = await SV.sec({ articles: [a, b], env, now: NOW, state: st, fetch: f, cats: [], dir, log: () => {}, menbe, kadr });
    assert.equal(x.id, b.id, "növbəti xəbər");
    assert.ok(st.skip[a.id] && !st.skip[b.id], "rədd olunan bir də sınanmır");
    assert.deepEqual(yoxlandi.slice(0, 2), [a.title, b.title]);
    assert.equal(JSON.parse(fs.readFileSync(path.join(dir, "xeber.json"), "utf8")).menbeVideo.sehife, b.sourceUrl);
    // Əl ilə seçilən xəbər: video olur, amma rədd olunan mənbə videosu olmadan.
    const d2 = tmp();
    const y = await SV.sec({ articles: [a, b], env: { ...env, VIDEO_XEBER: a.id, VIDEO_PAYLAS: "0" }, now: NOW, state: SV.readState("/yoxdur", NOW), fetch: f, cats: [], dir: d2, log: () => {}, menbe, kadr });
    assert.equal(y.id, a.id);
    assert.equal(y.menbeVideo, undefined);
    assert.ok(!fs.existsSync(path.join(d2, mv.file)), "fayl silinir");
  });
});

// --- İş axını və sənəd ----------------------------------------------------------------------------------------------------------------
test("media qaydası: every sparse checkout that ships a script needing video-qayda.cjs ships it too; the docs quote the owner and cite the law", () => {
  const dir = path.join(root, ".github/scripts"), cache = new Map();
  const needs = f => {
    if (cache.has(f)) return cache.get(f);
    cache.set(f, false);
    let src = "";
    try { src = fs.readFileSync(path.join(dir, f), "utf8"); } catch { return false; }
    const r = f === "video-qayda.cjs" || [...src.matchAll(/require\("\.\/([\w.-]+\.cjs)"\)/g)].map(m => m[1]).some(needs);
    cache.set(f, r);
    return r;
  };
  let checked = 0;
  for (const wf of fs.readdirSync(path.join(root, ".github/workflows")).filter(f => f.endsWith(".yml"))) {
    for (const m of read(`.github/workflows/${wf}`).matchAll(/sparse-checkout: \|\n([\s\S]*?)\n\s*sparse-checkout-cone-mode/g)) {
      const list = m[1].split("\n").map(s => s.trim()).filter(Boolean);
      if (!list.filter(x => /^\.github\/scripts\/[\w.-]+\.cjs$/.test(x)).map(x => path.basename(x)).some(needs)) continue;
      checked++;
      assert.ok(list.includes(".github/scripts/video-qayda.cjs"), `${wf}: sparse-checkout-da .github/scripts/video-qayda.cjs yoxdur`);
    }
  }
  assert.ok(checked >= 3, `sosial-video, video-arxiv, ses-lugat (${checked})`);
  assert.ok(read(".github/workflows/sosial-video.yml").includes("      - .github/scripts/video-qayda.cjs\n"), "PR yolu");
  const doc = read("docs/sosial-video.md"), i = doc.indexOf("## Media qaydası (sahib, 2026-11-27)");
  assert.ok(i > 0, "bölmə");
  const sec = doc.slice(i, doc.indexOf("\n## ", i + 5));
  for (const w of ["«Hamısını əlavə et»", "14.1.6", "14.1.13", "14.1.14", "15.1.5", "Meta", "video-qayda.cjs", "GOSTERIS", "45960946624"]) assert.ok(sec.includes(w), w);
  assert.ok(!doc.includes("X: kadrları yoxla") && !doc.includes("Kanal: kadrları yoxla"), "köhnə addımlar sənəddə qalmayıb");
});
