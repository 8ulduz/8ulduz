// Maraqlı videolar (sahib, 2026-11-24: X-in «Sizin üçün» lentindən 20 ekran şəkli — «bu kimi həm xəbər tipli, həm də digər çox maraqlı
// videolar», «mənə maraqlı deyil sən haradan tapacaqsan», «əsas odur onlar kimi sən də tap o cür maraqlı videolar»).
//
// Sosial hesablarımıza X-in videosu yüklənmir (xəbər saytlarının görüntüsü 2026-11-26-dan götürülür: video-menbe.cjs): YouTube Content ID və Meta Rights Manager onu tanıyır, video silinir,
// hesaba xəbərdarlıq gəlir (docs/sosial-video.md «Müəllif hüququ»). Ona görə «Maraqlı» rubrikası istifadə hüququmuz olan görüntüdən
// qurulur: Pixabay/Pexels klipləri (pulsuz lisenziya, dəyişdirmək və paylaşmaq olar) + Vikipediyanın faktları (fakt müəllif əsəri
// deyil; mətni özümüz yazırıq, mənbə göstərilir) + SARA səsi. Video xəbər videosunun eyni montajıdır (video-xeber.cjs: tam boy kadr,
// başlıq, altyazı, brend), eyni yoxlamadan və paylaşmadan keçir (sosial-video.cjs: Facebook, Instagram, TikTok, YouTube).
//
// Mövzular MOVZULAR-dadır: heyvanlar, təbiət hadisələri, kosmos — Pixabay-da bol görüntüsü olan, hər yaşda maraqlı. Hər mövzu üçün:
//   1) Vikipediyanın ingiliscə məqaləsi (fakt mənbəyi, ilk ~5000 simvol);
//   2) Gemini Azərbaycan dilində başlıq (ən heyrətamiz fakt) və 5–7 cümləlik diktor mətni yazır; mətndəki hər rəqəm məqalədə
//      olmalıdır, saytın qaydası (policyViolation) keçməlidir (video-ssenari.cjs checkText) — keçməsə növbəti mövzu;
//   3) klip mövzunun öz adı ilə axtarılır (video-ssenari.cjs goruntu: uyğunluq, yad yer, montaj redaktoru); KLIP_MIN-dən azdırsa növbəti mövzu.
// Mövzu növbəsi gündən asılıdır (hər gün başqa yerdən başlayır), son 3 gündə işlənən mövzu təkrarlanmır (sosial-video.cjs state.m).
// Dil profili (2026-11-26, video-dil.cjs): mətnin dili, yad əlifba, rubrikanın və qrupların adları .github/video-dil/<VIDEO_DIL>.json-dandır.
// Mövzu siyahısının azərbaycanca adları (MOVZULAR «az») yalnız göstərişdə və jurnalda gedir; fakt mənbəyi ingiliscə Vikipediyadır.
"use strict";
const fs = require("fs"), path = require("path");
const VS = require("./video-ssenari.cjs");
const { dil, fmt } = require("./video-dil.cjs");

const LINK = "https://8ulduz.az/";
const UA = "8ulduz-bot/1.0 (+https://8ulduz.az/haqqinda/)";
const SOURCE_MAX = 5000, SOURCE_MIN = 400, TITLE = [20, 100], KLIP_MIN = 2, CEHD = 3;
const clean = s => String(s ?? "").replace(/<[^>]+>/g, " ").replace(/\s+/g, " ").trim();
const wikiUrl = t => `https://en.wikipedia.org/wiki/${encodeURIComponent(String(t).replace(/ /g, "_"))}`;
const apiUrl = t => `https://en.wikipedia.org/w/api.php?action=query&prop=extracts&explaintext=1&redirects=1&format=json&formatversion=2&titles=${encodeURIComponent(t)}`;

// Qayda (sahib, 2026-11-24: «qaydanı dəyiş», «1-i də et»). İkisi birlikdə:
//  1) maraqlı video hava videosu kimi öz videomuzdur: saytın qaydası «8ULDUZ» mənbəsi ilə yoxlanır (video-hava.cjs policyRow);
//  2) qırmızı xətt 2 mənbə siyahısından asılı olmadan: başlıqda və mətndə Azərbaycan və rəhbərlik mövzusu (content-policy.js azTerms,
//     leaderTerms) olan video olmur. Vikipediya isə 2026-11-24-dən icazəli dünya mənbəyidir (worldSources): video.json-da mənbə kimi
//     qalır, montaj (video-xeber.cjs), YouTube və TikTok yükləyicisi onu saytın policyViolation qaydası ilə yenə yoxlayır.
const POLICY = (() => { const t = fs.readFileSync(path.join(__dirname, "..", "..", "assets", "content-policy.js"), "utf8"); return JSON.parse(t.slice(t.indexOf("{"), t.lastIndexOf("}") + 1)); })();
const AZ_TERMS = new RegExp(POLICY.azTerms, "i"), LEADER_TERMS = new RegExp(POLICY.leaderTerms, "i");
function qayda(a, policy = () => false) {
  const text = `${clean(a.title)} ${clean(a.summary)}`;
  return AZ_TERMS.test(text) || LEADER_TERMS.test(text) || Boolean(policy({ ...a, source: "8ULDUZ", sourceUrl: LINK, category: "maraqli", lang: dil().kod }));
}

// Axtarış ifadəsinin SONUNCU sözü klipin etiketində olmalıdır (video-ssenari.cjs relevance): ifadələr mövzunun öz adı ilə bitir.
const M = (id, az, wiki, axtar, qrup) => ({ id, az, wiki, axtar, qrup });
const MOVZULAR = [
  // Heyvanlar
  M("gepard", "Gepard", "Cheetah", ["cheetah"], "heyvan"),
  M("sir", "Şir", "Lion", ["lion", "lioness"], "heyvan"),
  M("peleng", "Pələng", "Tiger", ["tiger"], "heyvan"),
  M("fil", "Fil", "Elephant", ["elephant"], "heyvan"),
  M("zurafe", "Zürafə", "Giraffe", ["giraffe"], "heyvan"),
  M("zebr", "Zebr", "Zebra", ["zebra"], "heyvan"),
  M("kenquru", "Kenquru", "Kangaroo", ["kangaroo"], "heyvan"),
  M("koala", "Koala", "Koala", ["koala"], "heyvan"),
  M("panda", "Böyük panda", "Giant panda", ["panda"], "heyvan"),
  M("qutb-ayisi", "Qütb ayısı", "Polar bear", ["polar bear"], "heyvan"),
  M("qonur-ayi", "Qonur ayı", "Brown bear", ["brown bear", "bear"], "heyvan"),
  M("canavar", "Canavar", "Wolf", ["wolf"], "heyvan"),
  M("tulku", "Tülkü", "Red fox", ["fox"], "heyvan"),
  M("deve", "Dəvə", "Camel", ["camel"], "heyvan"),
  M("at", "At", "Horse", ["horse"], "heyvan"),
  M("delfin", "Delfin", "Dolphin", ["dolphin"], "heyvan"),
  M("balina", "Donqarlı balina", "Humpback whale", ["humpback whale", "whale"], "heyvan"),
  M("kopekbaligi", "Köpəkbalığı", "Shark", ["shark"], "heyvan"),
  M("meduza", "Meduza", "Jellyfish", ["jellyfish"], "heyvan"),
  M("sekkizayaq", "Səkkizayaq", "Octopus", ["octopus"], "heyvan"),
  M("deniz-tisbagasi", "Dəniz tısbağası", "Sea turtle", ["sea turtle", "turtle"], "heyvan"),
  M("deniz-ati", "Dəniz atı", "Seahorse", ["seahorse"], "heyvan"),
  M("pinqvin", "Pinqvin", "Penguin", ["penguin"], "heyvan"),
  M("qartal", "Qartal", "Eagle", ["eagle"], "heyvan"),
  M("bayqus", "Bayquş", "Owl", ["owl"], "heyvan"),
  M("kolibri", "Kolibri", "Hummingbird", ["hummingbird"], "heyvan"),
  M("flaminqo", "Flaminqo", "Flamingo", ["flamingo"], "heyvan"),
  M("tovuz", "Tovuz quşu", "Peafowl", ["peacock"], "heyvan"),
  M("tutuqusu", "Tutuquşu", "Parrot", ["parrot"], "heyvan"),
  M("qu", "Qu quşu", "Swan", ["swan"], "heyvan"),
  M("ari", "Bal arısı", "Western honey bee", ["honey bee", "bee"], "heyvan"),
  M("qarisqa", "Qarışqa", "Ant", ["ant"], "heyvan"),
  M("kepenek", "Kəpənək", "Butterfly", ["butterfly"], "heyvan"),
  M("parabuzen", "Parabüzən", "Coccinellidae", ["ladybug"], "heyvan"),
  M("circirama", "Cırcırama", "Dragonfly", ["dragonfly"], "heyvan"),
  M("horumcek", "Hörümçək", "Spider", ["spider web", "spider"], "heyvan"),
  M("buqelemun", "Buqələmun", "Chameleon", ["chameleon"], "heyvan"),
  M("qurbaga", "Qurbağa", "Frog", ["frog"], "heyvan"),
  M("timsah", "Timsah", "Crocodile", ["crocodile"], "heyvan"),
  M("kirpi", "Kirpi", "Hedgehog", ["hedgehog"], "heyvan"),
  M("dele", "Dələ", "Squirrel", ["squirrel"], "heyvan"),
  M("yarasa", "Yarasa", "Bat", ["bat"], "heyvan"),
  M("qorilla", "Qorilla", "Gorilla", ["gorilla"], "heyvan"),
  M("simpanze", "Şimpanze", "Chimpanzee", ["chimpanzee"], "heyvan"),
  M("maral", "Maral", "Deer", ["deer"], "heyvan"),
  M("ilbiz", "İlbiz", "Snail", ["snail"], "heyvan"),
  M("xerceng", "Xərçəng", "Crab", ["crab"], "heyvan"),
  M("deniz-ulduzu", "Dəniz ulduzu", "Starfish", ["starfish"], "heyvan"),
  M("pisik", "Pişik", "Cat", ["kitten", "cat"], "heyvan"),
  M("it", "İt", "Dog", ["puppy", "dog"], "heyvan"),
  // Təbiət hadisələri və bitkilər
  M("vulkan", "Vulkan", "Volcano", ["volcano", "lava"], "tebiet"),
  M("ildirim", "İldırım", "Lightning", ["lightning", "thunderstorm"], "tebiet"),
  M("qutb-parltisi", "Qütb parıltısı", "Aurora", ["aurora", "northern lights"], "tebiet"),
  M("goy-qursagi", "Göy qurşağı", "Rainbow", ["rainbow"], "tebiet"),
  M("selale", "Şəlalə", "Waterfall", ["waterfall"], "tebiet"),
  M("buzlaq", "Buzlaq", "Glacier", ["glacier", "iceberg"], "tebiet"),
  M("tornado", "Tornado", "Tornado", ["tornado"], "tebiet"),
  M("sehra", "Səhra", "Desert", ["sand dunes", "desert"], "tebiet"),
  M("mercan", "Mərcan rifi", "Coral reef", ["coral reef", "coral"], "tebiet"),
  M("geyzer", "Geyzer", "Geyser", ["geyser"], "tebiet"),
  M("magara", "Mağara", "Cave", ["cave"], "tebiet"),
  M("qar", "Qar dənəciyi", "Snowflake", ["snowflake", "snow"], "tebiet"),
  M("dalga", "Okean dalğaları", "Wind wave", ["ocean waves", "waves"], "tebiet"),
  M("tropik-mese", "Tropik meşə", "Tropical rainforest", ["rainforest", "jungle"], "tebiet"),
  M("gunebaxan", "Günəbaxan", "Common sunflower", ["sunflower"], "tebiet"),
  M("kaktus", "Kaktus", "Cactus", ["cactus"], "tebiet"),
  M("gobelek", "Göbələk", "Mushroom", ["mushroom"], "tebiet"),
  M("bambuk", "Bambuk", "Bamboo", ["bamboo"], "tebiet"),
  // Kosmos
  M("ay", "Ay", "Moon", ["full moon", "moon"], "kosmos"),
  M("gunes", "Günəş", "Sun", ["sun"], "kosmos"),
  M("sud-yolu", "Süd Yolu", "Milky Way", ["milky way", "starry sky"], "kosmos"),
  M("yer", "Yer planeti", "Earth", ["earth from space", "planet earth"], "kosmos"),
  M("kosmik-stansiya", "Beynəlxalq Kosmik Stansiya", "International Space Station", ["space station"], "kosmos"),
  M("raket", "Raket", "Rocket", ["rocket launch", "rocket"], "kosmos"),
  M("saturn", "Saturn", "Saturn", ["saturn"], "kosmos"),
  M("mars", "Mars", "Mars", ["mars planet", "mars"], "kosmos"),
  M("tutulma", "Günəş tutulması", "Solar eclipse", ["solar eclipse", "eclipse"], "kosmos"),
  M("dumanliq", "Dumanlıq", "Nebula", ["nebula"], "kosmos"),
];
// Qrupların adı profildədir (maraqli.qruplar); QRUP — az profilininki.
const QRUP = dil("az").maraqli.qruplar;

// Bu gün sınanacaq mövzular, sıra ilə: hər gün başqa yerdən başlayır (gün × 7), son 3 gündə işlənənlər (istifade: mövzu id-ləri) yoxdur.
function novbe(now, istifade = new Set(), list = MOVZULAR) {
  const day = Math.floor((now + 4 * 3600e3) / 86400e3), start = (day * 7) % list.length;
  return [...list.slice(start), ...list.slice(0, start)].filter(m => !istifade.has(m.id));
}

// Vikipediyanın ingiliscə məqaləsinin düz mətni (fakt mənbəyi). Alınmasa "".
async function fakt(wiki, f = globalThis.fetch) {
  try {
    const r = await f(apiUrl(wiki), { headers: { "user-agent": UA, accept: "application/json" }, signal: AbortSignal.timeout(20000) });
    const j = r?.ok ? await r.json() : null;
    const p = j?.query?.pages?.[0];
    if (!p || p.missing || !p.extract) return "";
    // Bölmə başlıqları («== Taxonomy ==») və «See also»dan sonrası atılır.
    const text = String(p.extract).split(/\n==\s*(?:See also|References|External links|Notes|Further reading)\s*==/)[0]
      .replace(/\n=+[^=\n]+=+\n/g, "\n").replace(/\n{2,}/g, "\n").trim();
    return text.slice(0, SOURCE_MAX);
  } catch { return ""; }
}

// Göstəriş azərbaycancadır; mətnin dili, yad əlifba və nisbi gün sözləri profildən ({dil}, {yad}, {nisbi}, {etiket_dili}).
const PROMPT_SABLON = `Sən 8ulduz.az saytının «Maraqlı» video rubrikasının redaktorusan. Mövzu: {az} (ingiliscə: {wiki}).
Aşağıda Vikipediyanın ingiliscə məqaləsindən çıxarış var. Ondan 35–45 saniyəlik şaquli video (Reels, Shorts, TikTok) üçün
{dil} mətn yaz. Tamaşaçı lentdə sürüşdürür: ilk saniyədə dayanıb baxmalıdır.
- title: 25–90 hərf — mövzunun ən heyrətamiz bir faktı, mövzunun adı ilə (məsələn «Gepard 3 saniyədə saatda 100 kilometr sürətə çatır»).
  Sonunda nöqtə, sual, nida yoxdur.
- text: 5–7 cümlə, 450–700 simvol. Hər cümlə bir maraqlı fakt; sadə, canlı dil, uşaq da başa düşsün. Başlığı təkrarlama.
- Hər rəqəm çıxarışda olmalıdır. Vahidi özün çevirmə: çıxarışda kilometr varsa kilometr yaz, mili kilometrə çevirmə. Çıxarışda olmayan
  fakt yazma, «alimlər hesab edir» kimi ümumi sözlərlə doldurma.
- Nida, sual işarəsi, keçid{yad}, inisial yoxdur. {nisbi} yoxdur.
- Azərbaycan, Ermənistan, Qarabağ, siyasət, din, müharibə, ölüm və qan mövzusu yoxdur.
- etiket: 3 etiket, # işarəsiz, {etiket_dili}, boşluqsuz (məsələn gepard, heyvanlar, maraqlıfaktlar).
Yalnız JSON qaytar: {"title": "...", "text": "...", "etiket": ["...", "...", "..."]}

Çıxarış:
{source}`;
const promptOf = (D = dil()) => fmt(PROMPT_SABLON, { dil: D.ssenari.dil, yad: D.ssenari.yad_herf ? `, ${D.ssenari.yad_herf_adi}` : "",
  nisbi: D.ssenari.nisbi_gun_misal, etiket_dili: D.ssenari.etiket_dili });
const PROMPT = promptOf(dil("az"));

// Başlığın yoxlaması (mətnin yoxlaması video-ssenari.cjs checkText-dir): uzunluq, işarə, kiril, mənbədə olmayan rəqəm, saytın qaydası.
function checkTitle(title, source, policy = () => false) {
  if (title.length < TITLE[0] || title.length > TITLE[1]) return `başlıq ${title.length} hərf (${TITLE[0]}–${TITLE[1]})`;
  if (/[!?]|https?:|www\./.test(title)) return "başlıqda nida, sual və ya keçid";
  const D = dil();
  if (D.re.yadHerf?.test(title)) return `başlıqda ${D.ssenari.yad_herf_adi}`;
  const have = new Set((source.match(/\d+(?:[.,]\d+)*/g) || []).map(n => n.replace(/[.,](?=\d{3}\b)/g, "").replace(",", ".")));
  const extra = (title.match(/\d+(?:[.,]\d+)*/g) || []).map(n => n.replace(/[.,](?=\d{3}\b)/g, "").replace(",", ".")).filter(n => !have.has(n));
  if (extra.length) return `başlıqda mənbədə olmayan rəqəm: ${extra.slice(0, 3).join(", ")}`;
  if (policy({ title, summary: "" })) return "başlıq saytın qaydasından keçmir";
  return "";
}

// Mövzu + fakt → { title, text, etiket } və ya { uygun: false, sebeb }; Gemini cavab vermirsə null.
async function ssenari(m, source, { env = process.env, fetch: f = globalThis.fetch, policy = () => false, log = console.log } = {}) {
  const key = env.GEMINI_API_KEY;
  if (!key) { log("maraqlı video: GEMINI_API_KEY yoxdur"); return null; }
  if (source.length < SOURCE_MIN) return { uygun: false, sebeb: "Vikipediya mətni qısadır və ya alınmadı" };
  const raw = await VS.gemini(promptOf().replace("{az}", m.az).replace("{wiki}", m.wiki).replace("{source}", source), key, f, log, env);
  if (raw == null) return null;
  let j = null;
  try { j = JSON.parse(String(raw).replace(/^```(?:json)?\s*|\s*```$/g, "")); } catch {}
  const title = VS.dilLatin(clean(j?.title)).replace(/[.。]+$/, ""), text = VS.dilLatin(clean(j?.text));
  const a = { title, category: "maraqli", lang: dil().kod, source: "Vikipediya", sourceUrl: wikiUrl(m.wiki) }, q = x => qayda(x, policy);
  const why = !title || !text ? "cavab boşdur və ya JSON deyil" : checkTitle(title, source, q) || VS.checkText(text, source, a, q);
  if (why) return { uygun: false, sebeb: why };
  const etiket = VS.hashtags(j?.etiket);
  return { title, text, uygun: true, ...(etiket.length && !q({ ...a, summary: etiket.join(" ") }) ? { etiket } : {}) };
}

// Bir maraqlı video üçün <qovluq>/xeber.json. istifade: son günlərin mövzuları (id); klip: işlənmiş kliplər («Pixabay:123»).
// goruntu: testdə yerinə qoyulur. Nəticə xeber.json-un sahələri (+ movzu, klip) və ya null (uyğun mövzu tapılmadı).
async function hazirla({ now = Date.now(), env = process.env, fetch: f = globalThis.fetch, policy = () => false, dir, log = console.log,
  istifade = new Set(), klip: isledilen = new Set(), goruntu = VS.goruntu, cehd = CEHD } = {}) {
  const footage = VS.MENBELER.some(m => env[m.env]);
  if (!footage) { log("maraqlı video: görüntü açarı yoxdur (PIXABAY_API_KEY, PEXELS_API_KEY) — hazırlanmır"); return null; }
  for (const m of novbe(now, istifade).slice(0, cehd)) {
    const source = await fakt(m.wiki, f);
    const sc = await ssenari(m, source, { env, fetch: f, policy, log });
    if (sc == null) { log("maraqlı video: Gemini cavab vermədi — bu dövrədə yoxdur"); return null; }
    if (!sc.uygun) { log(`maraqlı video: ${m.az} ötürülür — ${sc.sebeb}`); continue; }
    fs.mkdirSync(dir, { recursive: true });
    const klip = await goruntu(m.axtar, dir, { env, fetch: f, log, say: 6, category: "maraqli", istifade: isledilen, yer: [],
      xeber: { title: sc.title, text: sc.text, yer: [] } });
    if (klip.length < KLIP_MIN) {
      for (const k of klip) fs.rmSync(path.join(dir, k.file), { force: true });
      log(`maraqlı video: ${m.az} ötürülür — uyğun görüntü ${klip.length} klip (ən az ${KLIP_MIN})`);
      continue;
    }
    const day = new Date(now + 4 * 3600e3).toISOString().slice(0, 10), D = dil();
    return { tur: "maraqli", kind: "maraqli", id: `maraqli-${m.id}-${day}`, movzu: m.id, title: sc.title, text: sc.text, summary: sc.text,
      category: "maraqli", bolme: D.maraqli.bolme, qrup: D.maraqli.qruplar[m.qrup] || "", lang: D.kod, source: "Vikipediya", sourceUrl: wikiUrl(m.wiki),
      link: LINK, url: LINK, publishedAt: new Date(now).toISOString(), ...(sc.etiket ? { hashtags: sc.etiket } : {}), klip };
  }
  log("maraqlı video: uyğun mövzu tapılmadı");
  return null;
}

module.exports = { qayda, MOVZULAR, QRUP, novbe, fakt, ssenari, checkTitle, hazirla, PROMPT, promptOf, LINK, wikiUrl, apiUrl, KLIP_MIN };
