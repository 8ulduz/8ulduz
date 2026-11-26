// 8ulduz.az-ın öz video arxivi. Sahib, 2026-11-23: «həqiqi Gəncənin yeni stadionu olan videolardan istifadə etmək lazımdır.
// digərləri də belə». Xəbər və hava videosunda görüntü xəbərin həqiqi yerindən olsun.
//
// Kitabxana: tarixçəsiz «video-arxiv» budağında video-arxiv.json (başlanğıc nüsxə: data/video-arxiv.json, PR ilə) — yalnız metadata
// (klip faylı repoya yazılmır, repo-olcu.yml). Hər klipin yeri iki ayrı sübutla
// təsdiqlənib: (1) bankın etiketində yerin adı, (2) klipin 4 kadrına Gemini-nin multimodal baxışı (etiketsiz: «kadrda nə görürsən»).
// Su nişanı, telekanal nişanı, titr və başqa ölkənin bayrağı olan klip, separatçı adla etiketlənmiş klip qəbul olunmur.
// İki növ klip:
//   Pixabay / Pexels — pulsuz lisenziyalı bank kliplərı: ID, səhifə, lisenziya, yer, mövzu, keyfiyyət, yoxlama sübutu. Faylın
//                      ünvanı saxlanmır: montaj klipi ID ilə bankdan təzə soruşur (silinibsə ötürülür). Müəllifin adı saxlanmır
//                      (şərtlər §8: üzv adları toplanmır), yalnız istifadəçi nömrəsi (eyni çəkilişin seriyası üçün).
//   Sahib            — saytın öz çəkilişi və ya yazılı icazə ilə verilmiş görüntü. Fayl GitHub Release «video-arxiv»-dədir,
//                      sahib sətri Release-in təsvirinə yazır (docs/sosial-video.md «Video arxivi»). Üçüncü tərəfin, TV-nin, X-in videosu,
//                      platformanın faylı (TikTok, Instagram…) və su nişanlı görüntü kodla qəbul edilmir.
// Montaj (video-ssenari.cjs goruntu): xəbərin yeri məlum olanda əvvəl arxiv (əvvəl sahibin görüntüsü, sonra dəqiq obyekt, sonra
// şəhər), sonra adi axtarış. Yad yer qaydası (yadYer) arxivə də şamildir.
//
// Mənbə qaydaları (araşdırma 2026-11-23, docs/sosial-video.md «Video arxivi»): Pixabay — dəqiqədə ≤100 sorğu, sorğu ≥24 saat
// keşlənir, «çoxlu avtomatik sorğu» və sistemli kütləvi yükləmə yoxdur; Pexels — saatda 200, ayda 20 000 sorğu. Ona görə:
// eyni axtarış 30 gündə bir, bir işdə ≤25 axtarış və ≤20 yoxlama, kitabxana ≤400 klip (redaktə seçimidir, bankın nüsxəsi deyil),
// yoxlama üçün yalnız ən kiçik nüsxə (tiny, ~1–3 MB) bir dəfə yüklənir və silinir.
//
//   node video-arxiv.cjs yoxla [fayl]                     kitabxananın sxemi (CI); fayl — budağın nüsxəsi, yoxdursa data/video-arxiv.json
//   node video-arxiv.cjs boyut [fayl] [--say N] [--kadr qovluq]   yeni klip axtarır, yoxlayır, əlavə edir; köhnələrin bankda olduğunu yoxlayır
//   node video-arxiv.cjs sahib [fayl] [--kadr qovluq]     Release «video-arxiv»-dəki sahib görüntülərini qeyd edir / silir
// Açarlar: PIXABAY_API_KEY (ünvanda; ünvan jurnala yazılmır), PEXELS_API_KEY (başlıqda), GEMINI_API_KEY, GITHUB_TOKEN (Release).
// Xəbər yazmır (struktur 6): klip metadatası yazır, xəbərin mətnini və başlığını işlətmir.
"use strict";
const fs = require("fs"), path = require("path"), os = require("os"), cp = require("child_process");
const VS = require("./video-ssenari.cjs");

const ROOT = path.resolve(__dirname, "../..");
// Kitabxana main-dən kənardadır: tarixçəsiz «video-arxiv» budağında video-arxiv.json (video-arxiv.yml yazır, hər yazı valideynsiz bir
// commit — .github/scripts/arxiv.cjs kimi). Repodakı data/video-arxiv.json yalnız PR ilə gələn başlanğıc nüsxədir: budaq ilk dəfə ondan
// yaranır, budaq oxunmasa montaj ona düşür. Sahibin birbaşa main-ə yazma icazəsi yalnız X yazıcısının növbə faylı üçündür.
const FAYL = path.join(ROOT, "data/video-arxiv.json");
const BUDAQ = "video-arxiv", BUDAQ_FAYL = "video-arxiv.json";
const REPO = "8ulduz/8ulduz", RELEASE = "video-arxiv";
const SAHIB_URL = `https://github.com/${REPO}/releases/download/${RELEASE}/`;
// SORGU_TAVAN: əl ilə ilk doldurmada (--sorgu) belə bir işdə ən çox 60 axtarış (Pixabay: dəqiqədə 100, «çoxlu avtomatik sorğu» yox).
const ARXIV_MAX = 400, BOYUT_SAY = 20, SORGU_MAX = 25, SORGU_TAVAN = 60, SORGU_KLIP = 5, AXTARIS_GUN = 30, REDD_GUN = 180, REDD_MAX = 3000, BAXIS_SAY = 15;
const SEHER_MAX = { baku: 120 }, SEHER_MAX_DIGER = 30;
const ARXIV_NAMIZED = 6;   // montajda bir videoya ən çox 6 arxiv namizədi (hər biri bankda bir ID sorğusu)
const EMINLIK_MIN = 0.9, OBYEKT_EMINLIK = 0.85, KEYFIYYET_MIN = 3, SAHIB_KEYFIYYET_MIN = 2, MUDDET_MIN = 5, SAHIB_MUDDET_MIN = 3, SAHIB_OLCU_MIN = 720;
const KICIK_MAX_BYTES = 30e6, SAHIB_MAX_BYTES = 300e6;
const LISENZIYA = { Pixabay: "Pixabay Content License — https://pixabay.com/service/license-summary/", Pexels: "Pexels License — https://www.pexels.com/license/" };
// "menbe" (sahib, 2026-11-26: «bir çox xəbər saytı hesabı eyni görüntünü verir… biz də verək. Qaydalarımızda bunu əngəlləyən nəsə
// varsa sil»): telekanalın, saytın və ya sosial şəbəkə hesabının görüntüsü, mənbəsi göstərilməklə — sətirdə «mənbə: Ad».
const ICAZE = { "oz-cekilis": "Saytın öz çəkilişi", "yazili-icaze": "Müəllifin yazılı icazəsi", menbe: "Mənbə göstərilməklə (sahibin qərarı, 2026-11-26)" };
// Klipin havası (yoxlamada Gemini yazır). Hava videosu sabahkı Bakı halına uyğun havaları verir (video-hava.cjs arxivSecim).
const HAVA = ["gunesli", "buludlu", "yagisli", "qarli", "dumanli", "gece", "qapali", "bilinmir"];
const clean = s => String(s ?? "").replace(/\s+/g, " ").trim();
const gun = (now = Date.now()) => new Date(now).toISOString().slice(0, 10);
const yasGun = (d, now = Date.now()) => (Date.parse(d) ? (now - Date.parse(d)) / 86400e3 : Infinity);
const r2 = x => Math.round(x * 100) / 100;
const wait = ms => new Promise(ok => setTimeout(ok, ms));

// --- Yer adları: Azərbaycan dilində yazılanı montajın ingiliscə yer adlarına (video-ssenari.cjs SEHERLER) gətirir -----------------
const TRANSLIT = { "ə": "e", "ı": "i", "ş": "sh", "ç": "ch", "ğ": "gh", "ö": "o", "ü": "u" };
const AZ_YER = { baki: "baku", gence: "ganja", sumqayit: "sumqayit", sheki: "sheki", shusha: "shusha", qebele: "gabala", lenkeran: "lankaran",
  naxchivan: "nakhchivan", quba: "quba", qusar: "qusar", mingechevir: "mingachevir", shamaxi: "shamakhi", xankendi: "khankendi", aghdam: "aghdam",
  zaqatala: "zaqatala", masalli: "masalli", astara: "astara", lerik: "lerik", shirvan: "shirvan", naftalan: "naftalan", qobustan: "gobustan",
  fuzuli: "fuzuli", lachin: "lachin", kelbecer: "kalbajar", cebrayil: "jabrayil", zengilan: "zangilan", xachmaz: "khachmaz", balaken: "balakan",
  ismayilli: "ismayilli", goychay: "goychay", goygol: "goygol", berde: "barda", yevlax: "yevlakh", xizi: "khizi", siyezen: "siyazan",
  tovuz: "tovuz", qazax: "gazakh", aghstafa: "agstafa", salyan: "salyan", neftchala: "neftchala", imishli: "imishli", sabirabad: "sabirabad",
  beyleqan: "beylagan", azerbaycan: "azerbaijan", qarabagh: "karabakh", xinaliq: "khinalug", shahdagh: "shahdag" };
const AZ_IFADE = { "alov qulleleri": "flame towers", "qiz qalasi": "maiden tower", "icheri sheher": "icherisheher", "heyder eliyev merkezi": "heydar aliyev center",
  "xan sarayi": "khan palace", "hava limani": "airport", "deniz kenari": "seaside", "olimpiya stadionu": "olympic stadium", "kristal zal": "crystal hall" };
const AZ_SOZ = { stadion: "stadium", stadionu: "stadium", sheher: "city", sheherin: "city", qala: "fortress", qalasi: "fortress", meydan: "square",
  meydani: "square", parki: "park", bulvar: "boulevard", bulvari: "boulevard", korpu: "bridge", korpusu: "bridge", mescid: "mosque", mescidi: "mosque",
  qulle: "tower", qullesi: "tower", saray: "palace", sarayi: "palace", muzey: "museum", muzeyi: "museum", gol: "lake", golu: "lake", dagh: "mountain",
  daghi: "mountain", chay: "river", chayi: "river", deniz: "sea", liman: "port", limani: "port", vaghzal: "station", vaghzali: "station",
  xestexana: "hospital", xestexanasi: "hospital", mekteb: "school", mektebi: "school", universitet: "university", zavod: "factory", merkez: "center",
  merkezi: "center", kompleks: "complex", kompleksi: "complex", idman: "sports", olimpiya: "olympic", yeni: "new", kohne: "old", kend: "village",
  kendi: "village", sahil: "coast", sahili: "coast", ada: "island", adasi: "island", kuchesi: "street", kuche: "street", prospekti: "avenue", zal: "hall" };
function norm(s) {
  let t = String(s ?? "").toLocaleLowerCase("az").replace(/[əışçğöü]/g, ch => TRANSLIT[ch]).normalize("NFKD").replace(/[̀-ͯ]/g, "")
    .replace(/[^a-z\s'-]/g, " ").replace(/['-]/g, " ").replace(/\s+/g, " ").trim();
  for (const [a, b] of Object.entries(AZ_IFADE)) t = t.replace(new RegExp(`(^| )${a}( |$)`, "g"), `$1${b}$2`);
  return t.split(" ").filter(Boolean).map(w => AZ_YER[w] || AZ_SOZ[w] || w).join(" ");
}
const YER_ADI = new Set([...VS.SEHERLER, ...VS.OLKELER]);
const isYerAdi = n => YER_ADI.has(VS.lat(n));
// Yerin şəhəri: əvvəl tam şəhər adı («Gəncə»), yoxsa adın içindəki şəhər («Gəncə stadionu»).
const seherOf = yer => {
  const ns = (yer || []).map(n => VS.lat(norm(n)));
  return ns.find(n => VS.SEHERLER.includes(n)) || VS.SEHERLER.find(g => ns.some(n => VS.hasName(n, g))) || "";
};
const obyektOf = yer => (yer?.[0] && !isYerAdi(norm(yer[0])) ? clean(yer[0]) : "");
const BAS = s => s.replace(/(^|\s)\S/g, x => x.toUpperCase());

// Obyektin adı eynidirmi. Ad üç hissəyə bölünür: növ («stadium», «palace», «tower»), xüsusi sözlər («olympic», «khan») və şəhər.
// Növ eyni, şəhər (hər ikisində varsa) eyni, xüsusi sözlərin ən azı 2-si (bir sözlük addasa 1-i) üst-üstə düşməlidir.
// «Heydar Aliyev Center» ≠ «Heydar Aliyev Park», «Baku Olympic Stadium» ≠ «Ganja City Stadium», «Palace of Shaki Khans» = «Sheki Khan Palace».
const OBY_STOP = new Set(["the", "of", "and", "de", "national", "state", "republican", "city", "named", "after"]);
const TIP = new Set(["stadium", "center", "centre", "tower", "park", "square", "palace", "mosque", "museum", "hall", "street", "avenue", "lake", "mountain",
  "bridge", "port", "station", "fortress", "castle", "temple", "mausoleum", "boulevard", "arena", "complex", "school", "hospital", "airport", "university",
  "market", "theatre", "theater", "gate", "monument", "church", "caravanserai", "metro", "bay", "island", "village", "resort", "waterfall", "beach", "house"]);
const tek = w => (TIP.has(w.replace(/s$/, "")) ? w.replace(/s$/, "") : w.length > 4 ? w.replace(/s$/, "") : w);
const obySoz = s => norm(s).split(" ").filter(w => w.length > 1 && !OBY_STOP.has(w) && !YER_ADI.has(w)).map(tek);
function obyParca(s) {
  const ws = norm(s).split(" ").filter(w => w.length > 1 && !OBY_STOP.has(w));
  const city = new Set();
  for (const w of ws) if (YER_ADI.has(w)) { city.add(w); (VS.LAQEB[w] || []).forEach(x => city.add(x)); }
  const rest = ws.filter(w => !YER_ADI.has(w)).map(tek);
  const tip = [...rest].reverse().find(w => TIP.has(w)) || rest[rest.length - 1] || "";
  return { tip, spec: rest.filter(w => w !== tip), city };
}
function obyektUygun(a, b) {
  const A = obyParca(a), B = obyParca(b);
  if (!A.tip || A.tip !== B.tip) return false;
  if (A.city.size && B.city.size && ![...A.city].some(c => B.city.has(c))) return false;
  // Yalnız növ qalıbsa («Ganja City Stadium»): şəhər lazımdır; xüsusi ad özüdürsə («Icherisheher») — kifayətdir.
  if (!A.spec.length || !B.spec.length) return !A.spec.length && !B.spec.length && (!TIP.has(A.tip) || A.city.size > 0 || B.city.size > 0);
  return A.spec.filter(w => B.spec.includes(w)).length >= Math.min(2, A.spec.length, B.spec.length);
}

// Mənfi xəbər (qəza, ölüm, cinayət): arxivin şəhər klipi başlıq kadrına məcburi qoyulmur, yaxın planda insan olan klip götürülmür.
const MENFI = /(qəza|həlak|ölüb|öldü|ölüm|yaral|yanğın|partlayış|cinayət|qətl|öldürül|məhkəmə|həbs|zəlzələ|daşqın|sel |fəlakət|intihar|itkin)/iu;
const menfi = ({ category = "", title = "" } = {}) => category === "hadise" || MENFI.test(String(title));

// --- Kitabxananın sxemi --------------------------------------------------------------------------------------------------------
// Üçüncü tərəfin mənbəyi (TV, sosial şəbəkə, xəbər saytı): sahibin görüntüsünün «kim/icazə» sahəsində qəbul edilmir.
const QADAGAN = new RegExp(`(?<![\\p{L}\\p{N}])(${["tv", "telekanal", "kanal", "aztv", "itv", "atv", "xəzər tv", "xezer tv", "space tv", "arb", "cbc", "real tv",
  "baku tv", "ictimai", "apa", "report", "oxu\\.az", "qafqazinfo", "azərtac", "azertac", "trend", "president\\.az", "x\\.com", "twitter", "twimg",
  "youtube", "youtu\\.be", "tiktok", "instagram", "facebook", "fb\\.watch", "telegram", "whatsapp", "reels?", "efir", "reportaj"].join("|")})(?![\\p{L}\\p{N}])`, "iu");
// Separatçı və ya erməni adları (Xankəndi əvəzinə «Stepanakert» və s.): belə etiketli klip işğal dövrünün görüntüsü ola bilər.
const SIYASI = /(?<![a-z])(artsakh|stepanakert|shushi|nagorno|karabakh republic|armenia|armenian|hayastan|yerevan)(?![a-z])/i;
// Etiketi şəhər adı ilə eyni olan başqa mənalar: «ganja» — kənaf.
const SES_KUY = /(?<![a-z])(cannabis|marijuana|weed|hemp|joint|smoking|drug)(?![a-z])/i;

function kecerli(e) {
  if (!e || typeof e !== "object") return "obyekt deyil";
  if (!/^[a-z]+-[a-z0-9][a-z0-9-]{0,80}$/.test(String(e.id || ""))) return "id";
  if (!["Pixabay", "Pexels", "Sahib"].includes(e.menbe)) return "mənbə";
  if (!Array.isArray(e.yer) || !e.yer.length || e.yer.length > 5 || e.yer.some(x => typeof x !== "string" || !clean(x))) return "yer";
  if (e.seher && !VS.SEHERLER.includes(e.seher)) return "şəhər";
  if (e.hava && !HAVA.includes(e.hava)) return "hava";
  if (!Array.isArray(e.olcu) || e.olcu.length !== 2 || !e.olcu.every(n => Number.isInteger(n) && n > 0)) return "ölçü";
  if (!(Number(e.keyfiyyet) >= 1 && Number(e.keyfiyyet) <= 5)) return "keyfiyyət";
  const y = e.yoxlama || {};
  if (!/^\d{4}-\d{2}-\d{2}$/.test(String(y.tarix || ""))) return "yoxlama tarixi";
  if (y.statik === "nisan" && e.icaze !== "menbe") return "statik üst qat (su nişanı)";
  if (SIYASI.test(e.yer.join(" "))) return "siyasi ad";
  if (e.menbe === "Sahib") {
    if (!String(e.fayl || "").startsWith(SAHIB_URL) || !/^[^/?#]+\.(mp4|mov|m4v)$/i.test(String(e.fayl).slice(SAHIB_URL.length))) return "fayl saytın öz Release-ində deyil";
    if (!ICAZE[e.icaze]) return "icazə növü";
    if (!clean(e.kredit) || !clean(e.kim)) return "kredit";
    // Mənbəli görüntüdə («mənbə: Ad») ad üçüncü tərəfdir və su nişanı ola bilər; öz çəkiliş və yazılı icazədə əvvəlki yoxlamalar qalır.
    if (e.icaze !== "menbe" && QADAGAN.test(`${e.kim} ${e.kredit} ${e.lisenziya || ""}`)) return "üçüncü tərəfin mənbəyi";
    if (e.icaze === "yazili-icaze" && !/^\d{4}-\d{2}-\d{2}$/.test(String(e.icazeTarixi || ""))) return "icazənin tarixi";
    if (e.icaze !== "menbe" && y.suNisani !== false) return "su nişanı yoxlanmayıb";
    if (Math.min(...e.olcu) < SAHIB_OLCU_MIN) return "ölçü kiçikdir";
    return "";
  }
  if (!Number.isInteger(e.menbeId) || e.menbeId <= 0) return "bank nömrəsi";
  if (!LISENZIYA[e.menbe] || e.lisenziya !== LISENZIYA[e.menbe]) return "lisenziya";
  if (!Array.isArray(y.teq) || !y.teq.length) return "etiket sübutu";
  if (!(Number(y.eminlik) >= EMINLIK_MIN)) return "əminlik";
  if (!y.model) return "yoxlayan model";
  return "";
}

function oxu(file = FAYL) {
  let j = {};
  try { j = JSON.parse(fs.readFileSync(file, "utf8")) || {}; } catch {}
  return { haqqinda: j.haqqinda || HAQQINDA, v: 1, yenilendi: j.yenilendi || "", klipler: Array.isArray(j.klipler) ? j.klipler : [],
    redd: j.redd && typeof j.redd === "object" ? j.redd : {}, axtaris: j.axtaris && typeof j.axtaris === "object" ? j.axtaris : {} };
}
// Başlanğıc nüsxənin budaqda olmayan bank klipləri budağa qoşulur (PR ilə gələn yeni əl seçimi). Budağın rədd siyahısındakı (bankda
// silinib, yoxlamadan keçmədi) klip qoşulmur. Sahibin klipləri yalnız Release-dən gəlir (başlanğıc nüsxədən götürülmür).
function birlesdir(lib, seed) {
  const ids = new Set(lib.klipler.map(e => e?.id));
  for (const e of seed.klipler || []) if (e?.id && e.menbe !== "Sahib" && !ids.has(e.id) && !lib.redd[e.id]) { lib.klipler.push(e); ids.add(e.id); }
  for (const [k, v] of Object.entries(seed.redd || {})) if (!lib.redd[k]) lib.redd[k] = v;
  return lib;
}
// Sxemdən keçən kliplər (pozulmuş və təkrar sətir jurnala yazılıb atılır).
function gecerliler(list, log = () => {}) {
  const ids = new Set(), out = [];
  for (const e of list) {
    const why = kecerli(e) || (ids.has(e?.id) ? "təkrar id" : "");
    if (why) { log(`video: arxiv sətri atıldı — ${e?.id || "?"}: ${why}`); continue; }
    ids.add(e.id); out.push(e);
  }
  return out;
}
// Bir faylın klipləri (fayl yoxdursa və ya pozulubsa boş siyahı — video adi axtarışla davam edir).
const yukle = (file = FAYL, log = () => {}) => gecerliler(oxu(file).klipler, log);
// Montajın kitabxanası: budağın nüsxəsi (VIDEO_ARXIV_FAYL — sosial-video.yml «video-arxiv» budağından endirir) + başlanğıc nüsxə;
// budaq oxunmasa yalnız başlanğıc nüsxə (data/video-arxiv.json).
function kitabxana(env = process.env, log = () => {}) {
  const p = clean(env.VIDEO_ARXIV_FAYL);
  let lib = null;
  if (p) { try { if (Array.isArray(JSON.parse(fs.readFileSync(p, "utf8"))?.klipler)) lib = oxu(p); } catch {} }
  if (p && !lib) log("video: video-arxiv budağının nüsxəsi oxunmadı — repodakı başlanğıc nüsxə");
  const list = gecerliler((lib ? birlesdir(lib, oxu(FAYL)) : oxu(FAYL)).klipler, log);
  log(`video: arxivdə ${list.length} klip (${lib ? "video-arxiv budağı" : "başlanğıc nüsxə"})`);
  return list;
}
const HAQQINDA = "8ulduz.az video arxivi: yeri kadrlarla yoxlanmış kliplərin metadatası (fayl yoxdur). Yazan: .github/workflows/video-arxiv.yml («video-arxiv» budağı; data/video-arxiv.json — başlanğıc nüsxə). Qaydalar: docs/sosial-video.md «Video arxivi».";
// Sabit sıra (şəhər, obyekt, id) və bir klip bir sətir: fərq oxunaqlı olsun.
function yaz(lib, file = FAYL, now = Date.now()) {
  const sira = (a, b) => (a.menbe === "Sahib") - (b.menbe === "Sahib") || String(a.seher).localeCompare(String(b.seher)) || String(a.obyekt).localeCompare(String(b.obyekt)) || a.id.localeCompare(b.id);
  const redd = Object.entries(lib.redd || {}).filter(([, v]) => yasGun(String(v).slice(0, 10), now) < REDD_GUN).sort(([a], [b]) => a.localeCompare(b)).slice(-REDD_MAX);
  const axt = Object.entries(lib.axtaris || {}).sort(([a], [b]) => a.localeCompare(b));
  const kl = [...lib.klipler].sort(sira);
  const body = `{\n "haqqinda": ${JSON.stringify(HAQQINDA)},\n "v": 1,\n "yenilendi": ${JSON.stringify(lib.yenilendi || gun(now))},\n "say": ${kl.length},\n "klipler": [${kl.length ? `\n  ${kl.map(e => JSON.stringify(e)).join(",\n  ")}\n ` : ""}],\n`
    + ` "axtaris": {${axt.length ? `\n  ${axt.map(([k, v]) => `${JSON.stringify(k)}: ${JSON.stringify(v)}`).join(",\n  ")}\n ` : ""}},\n`
    + ` "redd": {${redd.length ? `\n  ${redd.map(([k, v]) => `${JSON.stringify(k)}: ${JSON.stringify(v)}`).join(",\n  ")}\n ` : ""}}\n}\n`;
  fs.mkdirSync(path.dirname(file), { recursive: true });
  fs.writeFileSync(file, body);
}

// --- Montaj: xəbərin yerinə uyğun arxiv klipləri -----------------------------------------------------------------------------------
// yer: xəbərin yerləri (Gemini, dəqiqdən ümumiyə), icaze: xəbərə aid yer adları (yerPlan), axtar: montaj ifadələri (mövzu üçün),
// istifade: son günlərdə işlənmiş kliplər («Pixabay:123», «Sahib:sahib-…»), hava: icazəli havalar (hava videosu), menfi: mənfi xəbər.
// Nəticə: [{ e, level: obyekt | seher | olke, score, ilk }] — ilk: redaktordan asılı olmadan başlıq kadrı (dəqiq obyekt, ən çox 2; yoxdursa
// şəhərin ən yaxşı klipi, mənfi xəbər deyilsə).
const acar = e => `${e.menbe}:${e.menbe === "Sahib" ? e.id : e.menbeId}`;
function namizedler(lib, { yer = [], icaze = null, axtar = [], istifade = new Set(), hava = null, menfi: neg = false } = {}) {
  const names = VS.places(yer).map(n => clean(n)), P = VS.yerPlan(names);
  const ic = icaze && icaze.size ? icaze : P.icaze;
  if (!ic.size || !(lib || []).length) return [];
  const seherler = new Set();
  for (const n of names.map(x => VS.lat(norm(x)))) if (VS.SEHERLER.includes(n)) { seherler.add(n); (VS.LAQEB[n] || []).forEach(x => seherler.add(x)); }
  const obj = names.filter(n => !isYerAdi(norm(n)));
  const want = new Set(VS.queries(axtar).flatMap(q => q.split(" ")).filter(w => w.length > 2 && !YER_ADI.has(w)));
  const hv = Array.isArray(hava) && hava.length ? hava : null;
  const out = [];
  for (const e of lib || []) {
    if (istifade.has(acar(e))) continue;
    if (VS.yadYer([...e.yer, ...(e.adlar || [])].map(norm).join(", "), ic)) continue;
    if (hv && (!hv.includes(e.hava) || e.rengli === false)) continue;   // hava videosu: o havada və rəngli
    if (neg && e.insan) continue;
    const adlar = [e.obyekt, ...(e.adlar || [])].filter(Boolean);
    // olke: xəbərdə şəhər yoxdursa — ölkənin ümumi klipi və ya paytaxt (yerPlan icazəsi); şəhər varsa — yalnız ölkənin ümumi klipi
    // (bayraq). Şəhəri bilinməyən konkret yer (Yanardağ) başqa şəhərin xəbərinə getmir.
    const umumi = e.yer.length === 1 && VS.OLKELER.includes(VS.lat(norm(e.yer[0])));
    const level = obj.length && adlar.some(a => obj.some(o => obyektUygun(a, o))) ? "obyekt" : e.seher && seherler.has(e.seher) ? "seher"
      : umumi || (!seherler.size && e.seher && ic.has(e.seher)) ? "olke" : "";
    if (!level) continue;
    const movzu = new Set([...(e.movzu || []), ...obySoz(e.obyekt || "")].flatMap(m => VS.lat(m).split(" ")));
    const score = { obyekt: 100, seher: 50, olke: 10 }[level] + (e.menbe === "Sahib" ? 40 : 0) + 4 * [...want].filter(w => movzu.has(w)).length + Number(e.keyfiyyet || 3)
      - (e.rengli === false ? 15 : 0);   // ağ-qara klip arxada qalır: rəngli uyğun klip yoxdursa seçilir
    out.push({ e, level, score, ilk: false });
  }
  out.sort((a, b) => b.score - a.score || a.e.id.localeCompare(b.e.id));
  const cap = { obyekt: 3, seher: 4, olke: 2 }, n = { obyekt: 0, seher: 0, olke: 0 };
  const res = out.filter(x => n[x.level]++ < cap[x.level]);
  const ob = res.filter(x => x.level === "obyekt").slice(0, 2);
  if (ob.length) ob.forEach(x => { x.ilk = true; });
  else { const s = res.find(x => x.level === "seher"); if (s && !neg) s.ilk = true; }
  return res;
}

// --- Bank: ID ilə klip (montaj və yoxlama) və axtarış ------------------------------------------------------------------------------
const enc = encodeURIComponent;
const BANK = {
  Pixabay: { env: "PIXABAY_API_KEY",
    // { hit } | { yox: true } (bankda yoxdur: silinib) | null (şəbəkə, açar)
    async byId(id, key, f) {
      const j = await VS.getJson(`https://pixabay.com/api/videos/?key=${enc(key)}&id=${enc(id)}`, {}, f);
      if (!j || !Array.isArray(j.hits)) return null;
      const hit = j.hits.find(h => Number(h?.id) === Number(id));
      return hit ? { hit } : { yox: true };
    },
    async search(q, key, f) {
      const j = await VS.getJson(`https://pixabay.com/api/videos/?key=${enc(key)}&q=${enc(q.slice(0, 100))}&video_type=film&safesearch=true&order=popular&per_page=100`, {}, f);
      return Array.isArray(j?.hits) ? j.hits : null;
    },
    hazir(v) {
      const file = VS.pixabayFile(v);
      return file ? { link: file.url, w: file.width, h: file.height, user: clean(v.user || ""), tags: clean(v.tags || ""),
        thumb: v.videos?.tiny?.thumbnail || v.videos?.small?.thumbnail || file.thumbnail || "" } : null;
    },
    teqler: v => `${v?.tags || ""} ${VS.slug(v?.pageURL).replace(/-\d+$/, "").replace(/-/g, " ")}`,
    kicik: v => [v?.videos?.tiny, v?.videos?.small].find(x => x?.url && !(x.size > KICIK_MAX_BYTES))?.url || "",
    sehife: v => (/^https:\/\/pixabay\.com\//.test(v?.pageURL || "") ? v.pageURL : `https://pixabay.com/videos/id-${v.id}/`),
    muellif: v => (Number.isInteger(v?.user_id) ? v.user_id : 0),
    olcu: v => { const x = VS.pixabayFile(v); return x ? [x.width, x.height] : null; },
  },
  Pexels: { env: "PEXELS_API_KEY",
    async byId(id, key, f) {
      const r = await f(`https://api.pexels.com/videos/videos/${enc(id)}`, { headers: { authorization: key }, signal: AbortSignal.timeout(20000) }).catch(() => null);
      if (r?.status === 404) return { yox: true };
      const v = r?.ok ? await r.json().catch(() => null) : null;
      return v?.id ? { hit: v } : null;
    },
    async search(q, key, f) {
      const j = await VS.getJson(`https://api.pexels.com/videos/search?query=${enc(q)}&per_page=40`, { authorization: key }, f);
      return Array.isArray(j?.videos) ? j.videos : null;
    },
    hazir(v) {
      const portrait = v.height > v.width, file = VS.bestFile(v, portrait) || VS.bestFile(v, !portrait);
      return file ? { link: file.link, w: file.width, h: file.height, user: clean(v.user?.name || ""), tags: VS.slug(v.url).replace(/-\d+$/, "").replace(/-/g, ", "), thumb: v.image || "" } : null;
    },
    teqler: v => `${(v?.tags || []).join(" ")} ${VS.slug(v?.url).replace(/-\d+$/, "").replace(/-/g, " ")}`,
    kicik: v => [...(v?.video_files || [])].filter(x => x?.link && /mp4/.test(x.file_type || "")).sort((a, b) => (a.width || 0) - (b.width || 0))[0]?.link || "",
    sehife: v => (/^https:\/\/www\.pexels\.com\//.test(v?.url || "") ? v.url : `https://www.pexels.com/video/${v.id}/`),
    muellif: v => (Number.isInteger(v?.user?.id) ? v.user.id : 0),
    olcu: v => { const x = VS.bestFile(v, v.height > v.width) || VS.bestFile(v, !(v.height > v.width)); return x ? [x.width, x.height] : null; },
  },
};

// Arxiv klipinin indiki faylı: bank — ID ilə təzə soruşulur (ünvan saxlanmır, silinmiş klip ötürülür); sahib — öz Release ünvanı.
// Nəticə video-ssenari.cjs-in namizəd formasıdır: { p, id, link, w, h, user, tags, thumb, kredit } və ya null.
async function hazirla(e, { env = process.env, fetch: f = globalThis.fetch } = {}) {
  if (e?.menbe === "Sahib") {
    if (kecerli(e)) return null;
    return { p: "Sahib", id: e.id, link: e.fayl, w: e.olcu[0], h: e.olcu[1], user: e.kredit, kredit: e.kredit, tags: e.yer.join(", "), thumb: "", maxBytes: SAHIB_MAX_BYTES };
  }
  const b = BANK[e?.menbe], key = b && env[b.env];
  if (!key) return null;
  const r = await b.byId(e.menbeId, key, f).catch(() => null);
  const c = r?.hit ? b.hazir(r.hit) : null;
  return c ? { p: e.menbe, id: e.menbeId, ...c, kredit: e.menbe } : null;
}

// --- Su nişanı: statik üst qat ------------------------------------------------------------------------------------------------------
// Klip boyu 12 boz kadr (məsələn 160×90). Səhnə hərəkət edir, amma küncdə və ya zolaqda kənarları olan hissə yerindən tərpənmirsə —
// loqo, su nişanı, telekanal nişanı, titr. Yaxınlığındakı sahə də statikdirsə (bina, yol) nişan sayılmır. Səhnənin özü dayanıbsa
// (ştativ, kadr az) qərar «bilinmir» — onda Gemini-nin baxışı qalır.
function statikQat(frames, w, h) {
  const T = (frames || []).length, N = w * h;
  if (T < 6 || frames.some(fr => !fr || fr.length < N)) return { qerar: "bilinmir", sebeb: "kadr azdır" };
  const mean = new Float64Array(N), sd = new Float64Array(N);
  for (const fr of frames) for (let i = 0; i < N; i++) mean[i] += fr[i];
  for (let i = 0; i < N; i++) mean[i] /= T;
  for (const fr of frames) for (let i = 0; i < N; i++) { const d = fr[i] - mean[i]; sd[i] += d * d; }
  let moving = 0;
  for (let i = 0; i < N; i++) { sd[i] = Math.sqrt(sd[i] / T); if (sd[i] > 10) moving++; }
  const hereket = r2(moving / N);
  if (hereket < 0.25) return { qerar: "bilinmir", hereket };
  const st = new Uint8Array(N);
  for (let y = 1; y < h - 1; y++) for (let x = 1; x < w - 1; x++) {
    const i = y * w + x, g = Math.abs(mean[i + 1] - mean[i - 1]) + Math.abs(mean[i + w] - mean[i - w]);
    st[i] = sd[i] < 3 && g > 24 ? 1 : 0;
  }
  const pay = (x0, y0, x1, y1) => {
    let n = 0, a = 0;
    for (let y = Math.floor(y0 * h); y < Math.ceil(y1 * h); y++) for (let x = Math.floor(x0 * w); x < Math.ceil(x1 * w); x++) { a++; n += st[y * w + x]; }
    return a ? n / a : 0;
  };
  const R = [["sol yuxarı künc", [0, 0, 0.3, 0.2], [0.35, 0, 0.65, 0.2]], ["sağ yuxarı künc", [0.7, 0, 1, 0.2], [0.35, 0, 0.65, 0.2]],
    ["sol aşağı künc", [0, 0.8, 0.3, 1], [0.35, 0.8, 0.65, 1]], ["sağ aşağı künc", [0.7, 0.8, 1, 1], [0.35, 0.8, 0.65, 1]],
    ["aşağı zolaq (titr)", [0, 0.84, 1, 1], [0, 0.42, 1, 0.58]], ["yuxarı zolaq", [0, 0, 1, 0.12], [0, 0.42, 1, 0.58]]];
  for (const [ad, r, q] of R) {
    const a = pay(...r), b = pay(...q);
    if (a >= 0.04 && a >= 4 * b + 0.01) return { qerar: "nisan", yer: ad, pay: r2(a), hereket };
  }
  return { qerar: "temiz", hereket };
}

// --- Kadrlar (ffmpeg; yalnız GitHub Actions-da) -------------------------------------------------------------------------------------
const run = (cmd, args, opt = {}) => cp.execFileSync(cmd, args, { stdio: ["ignore", "pipe", "pipe"], maxBuffer: 64 << 20, timeout: 180000, ...opt });
async function indir(url, file, max, f) {
  const r = await f(url, { signal: AbortSignal.timeout(300000) });
  if (!r?.ok) throw new Error(`yükləmə HTTP ${r?.status}`);
  const n = Number(r.headers?.get?.("content-length") || 0);
  if (n > max) throw new Error(`fayl böyükdür (${Math.round(n / 1e6)} MB)`);
  const buf = Buffer.from(await r.arrayBuffer());
  if (buf.length > max) throw new Error(`fayl böyükdür (${Math.round(buf.length / 1e6)} MB)`);
  fs.writeFileSync(file, buf);
  return buf.length;
}
// ffprobe: ölçü (fırlanma nəzərə alınır), müddət, kodek və faylın nişanları (platforma izləri üçün).
function probe(file) {
  const j = JSON.parse(run("ffprobe", ["-v", "error", "-show_entries", "format=duration:format_tags:stream=codec_type,codec_name,width,height:stream_tags:stream_side_data=rotation", "-of", "json", file]).toString());
  const v = (j.streams || []).find(s => s.codec_type === "video") || {};
  const rot = Math.abs(Number(v.side_data_list?.find(d => d.rotation != null)?.rotation ?? v.tags?.rotate ?? 0)) % 180 === 90;
  const tags = [j.format?.tags, ...(j.streams || []).map(s => s.tags)].filter(Boolean).flatMap(t => Object.entries(t).map(([k, x]) => `${k}=${x}`)).join(" ");
  return { w: rot ? v.height : v.width, h: rot ? v.width : v.height, dur: Number(j.format?.duration) || 0, vcodec: v.codec_name || "", tags };
}
// Platformadan endirilmiş faylın izi (TikTok, Instagram, X…): belə fayl sahibin görüntüsü sayılmır.
const PLATFORMA = /(tiktok|douyin|bytedance|instagram|twitter|x\.com|facebook|youtube|snapchat|vk\.com|telegram|whatsapp|kwai|likee)/i;
// 4 rəngli kadr (Gemini üçün, 512 px) və 12 boz kadr (statikQat, 160 px enində). dur: klipin müddəti.
function kadrlar(file, dur, w, h) {
  const tmp = fs.mkdtempSync(path.join(os.tmpdir(), "arxiv-kadr-"));
  try {
    // Rəngli kadrlar klipin 10%-dən başlayır (əvvəldəki qaralma və yazı düşməsin): ~10, 31, 52, 74%.
    const d = Math.max(1, Number(dur) || 10), ss = (d * 0.1).toFixed(2);
    run("ffmpeg", ["-hide_banner", "-loglevel", "error", "-y", "-ss", ss, "-i", file, "-vf", `fps=4/${(d * 0.85).toFixed(2)},scale=512:-2`, "-frames:v", "4", "-q:v", "5", path.join(tmp, "k-%d.jpg")]);
    const jpg = fs.readdirSync(tmp).filter(x => /^k-\d+\.jpg$/.test(x)).sort().map(x => fs.readFileSync(path.join(tmp, x)));
    const gw = (w || 16) >= (h || 9) ? 160 : 90, gh = (w || 16) >= (h || 9) ? 90 : 160;
    const raw = run("ffmpeg", ["-hide_banner", "-loglevel", "error", "-i", file, "-vf", `fps=12/${d},scale=${gw}:${gh},format=gray`, "-frames:v", "12", "-f", "rawvideo", "-"]);
    const frames = [];
    for (let o = 0; o + gw * gh <= raw.length; o += gw * gh) frames.push(raw.subarray(o, o + gw * gh));
    return { jpg, gray: { w: gw, h: gh, frames } };
  } finally { fs.rmSync(tmp, { recursive: true, force: true }); }
}
// Önizləmə zolağı: 4 kadr yan-yana, üstündə yazı (iş səhifəsinin artefaktı; sahib və agent qərarı gözlə görsün).
function zolaq(jpg, out, label) {
  if (!jpg.length) return false;
  const tmp = fs.mkdtempSync(path.join(os.tmpdir(), "arxiv-zolaq-"));
  try {
    const ins = jpg.flatMap((b, i) => { const p = path.join(tmp, `k${i}.jpg`); fs.writeFileSync(p, b); return ["-i", p]; });
    fs.writeFileSync(path.join(tmp, "t.txt"), String(label).slice(0, 150));
    const n = jpg.length, sc = jpg.map((_, i) => `[${i}:v]scale=320:180:force_original_aspect_ratio=decrease,pad=320:180:(ow-iw)/2:(oh-ih)/2,setsar=1[k${i}]`).join(";");
    const st = n > 1 ? `${jpg.map((_, i) => `[k${i}]`).join("")}hstack=${n}[h]` : "[k0]null[h]";
    run("ffmpeg", ["-hide_banner", "-loglevel", "error", "-y", ...ins, "-filter_complex",
      `${sc};${st};[h]pad=iw:ih+40:0:40:color=0x0b1f3a,drawtext=textfile=${path.join(tmp, "t.txt")}:fontcolor=white:fontsize=22:x=10:y=9:font=Roboto[o]`, "-map", "[o]", "-q:v", "4", out]);
    return true;
  } catch { return false; } finally { fs.rmSync(tmp, { recursive: true, force: true }); }
}
function vereq(files, out) {
  if (!files.length) return false;
  try {
    run("ffmpeg", ["-hide_banner", "-loglevel", "error", "-y", ...files.flatMap(f => ["-i", f]), "-filter_complex",
      files.length > 1 ? `${files.map((_, i) => `[${i}:v]`).join("")}vstack=${files.length}[o]` : "[0:v]null[o]", "-map", "[o]", "-q:v", "4", out]);
    return true;
  } catch { return false; }
}

// --- Gemini: kadrlara baxış ---------------------------------------------------------------------------------------------------------
// Etiket verilmir: model yalnız kadrda gördüyünü deyir (etiket ayrıca, kodla yoxlanır — iki müstəqil sübut). gorunen_yer əvvəl gəlir.
// Şəhər və obyekt ayrıca soruşulur (2026-11-23 ilk iş: «İçərişəhər» axtarışında Heydər Əliyev Mərkəzinin klipi «yer təsdiqlənmədi» ilə
// rədd olunmuşdu, bulvarın gecə panoraması isə etiketə görə «İçərişəhər» yazılmışdı).
const YOXLA = `Sən 8ulduz.az xəbər saytının video arxivinin yoxlayıcısısan. Aşağıda video bankından bir klipin {n} kadrı var (klipin
əvvəlindən sonuna). Gözlənilən şəhər: {seher}. Gözlənilən obyekt: {obyekt}. Yalnız kadrlarda GÖRDÜYÜNƏ əsaslan, əmin deyilsənsə false.
- gorunen_yer: kadrda gördüyün yer ingiliscə ("Baku, Azerbaijan", "Batumi, Georgia", "Dubai, UAE"); tanınmırsa "unknown".
- seher_dogru: kadrda məhz {seher} görünür (tanınan panorama, bina, abidə, küçə, sahil, lövhə və yazının dili). Ümumi dağ, meşə, yol,
  göy, dəniz, tunel, metro, bina içi, yaxın plan — şəhər tanınmır: false.
- obyekt: kadrda tanınan bina və ya yer ingiliscə ("Flame Towers", "Baku Boulevard", "Heydar Aliyev Center", "Maiden Tower"); yoxdursa "".
- obyekt_gorunur: gözlənilən obyekt kadrda aydın görünür (obyekt «—»-dirsə false).
- eminlik: seher_dogru-ya əminlik, 0..1.
- rengli: kadr adi rənglidir (ağ-qara və ya bir rəngə boyanmış deyil).
- su_nisani: kadrın üstündə loqo, su nişanı, telekanal nişanı, titr, ekran yazısı, sosial şəbəkə adı, tarix və ya saat yazısı varmı
  (binadakı adi lövhə və reklam sayılmır).
- siyasi: başqa ölkənin dövlət bayrağı, separatçı simvol, partiya plakatı, siyasi şüar varmı (Azərbaycan bayrağı sayılmır).
- insan: yaxın planda tanınan insan üzü varmı.
- hava: "gunesli", "buludlu", "yagisli", "qarli", "dumanli", "gece", "qapali" (bina içi) və ya "bilinmir".
- movzu: 2–5 ingiliscə səhnə sözü (skyline, boulevard, sea, traffic, old town, stadium, mountains, aerial, night, metro, park).
- keyfiyyet: 1–5 (kəskinlik, sabitlik, işıq; 3 — adi, 5 — əla).
- izah: bir cümlə azərbaycanca: kadrda nə görünür və yer hansı əlamətdən tanınır.
Yalnız JSON qaytar: {"gorunen_yer": "...", "seher_dogru": true, "obyekt": "...", "obyekt_gorunur": false, "eminlik": 0.9, "rengli": true,
"su_nisani": false, "siyasi": false, "insan": false, "hava": "...", "movzu": ["..."], "keyfiyyet": 4, "izah": "..."}`;
// Sahibin görüntüsü: yer sahibin sözüdür; yoxlanan — başqasının görüntüsünün əlaməti (nişan, titr, ekran yazısı) və yerin açıq ziddiyyəti.
const SAHIB_YOXLA = `Sən 8ulduz.az xəbər saytının video arxivinin yoxlayıcısısan. Saytın sahibi bu klipi öz çəkilişi və ya icazəli
görüntü kimi əlavə edib, yeri belə yazıb: «{yer}». Aşağıda klipin {n} kadrı var. Yalnız kadrlarda GÖRDÜYÜNƏ əsaslan.
- su_nisani: kadrın üstündə loqo, su nişanı, telekanal nişanı, titr, «canlı/live», ekran yazısı, sosial şəbəkə adı və ya istifadəçi
  adı (@...), tarix/saat yazısı varmı (binadakı adi lövhə sayılmır).
- ekran: bu, başqa ekranın (televizor, telefon, kompüter) çəkilişi və ya ekran yazısıdırmı (çərçivə, interfeys, piksel toru).
- siyasi: başqa ölkənin dövlət bayrağı, separatçı simvol, partiya plakatı, siyasi şüar varmı (Azərbaycan bayrağı sayılmır).
- ziddiyyet: kadrda yazılan yerə açıq zidd olan əlamət varmı (başqa ölkənin yazısı, tanınan yad şəhər) — yalnız əmin olanda true.
- yer_en: yazılan yerlərin ingiliscə adları, dəqiqdən ümumiyə (["Ganja City Stadium", "Ganja", "Azerbaijan"]).
- insan: yaxın planda tanınan insan üzü varmı. hava: "gunesli", "buludlu", "yagisli", "qarli", "dumanli", "gece", "qapali" və ya "bilinmir".
- movzu: 2–5 ingiliscə səhnə sözü. keyfiyyet: 1–5. izah: bir cümlə azərbaycanca.
Yalnız JSON qaytar: {"su_nisani": false, "ekran": false, "siyasi": false, "ziddiyyet": false, "yer_en": ["..."], "insan": false,
"hava": "...", "movzu": ["..."], "keyfiyyet": 4, "izah": "..."}`;
async function baxis(prompt, jpg, env, f, log) {
  const parts = [{ text: prompt }];
  jpg.forEach((b, i) => parts.push({ text: `Kadr ${i + 1}:` }, { inline_data: { mime_type: "image/jpeg", data: Buffer.from(b).toString("base64") } }));
  const info = {};
  const raw = await VS.gemini(parts, env.GEMINI_API_KEY, f, log, env, info);
  if (raw == null) return null;
  try { return { ...JSON.parse(String(raw).replace(/^```(?:json)?\s*|\s*```$/g, "")), _model: info.model || "" }; } catch { return { _xeta: "JSON deyil" }; }
}

// --- Böyütmə planı: Azərbaycanın şəhər və tanınan yerləri -------------------------------------------------------------------------
// yer: dəqiqdən ümumiyə (montajın yer siyahısı kimi), adlar: başqa adlar (azərbaycanca da), axtar: bank ifadələri,
// teq: etiketdə olmalı sözlərdən biri (şəhərin adı həmişə sayılır).
// Sıra: əvvəl şəhərlər (bir işdə ≤25 axtarış: ilk işdə hər şəhər bir dəfə soruşulsun), sonra tanınan yerlər, sonda ölkənin ümumi səhnəsi.
const PLAN = [
  { yer: ["Baku", "Azerbaijan"], axtar: ["baku", "baku azerbaijan", "baku city", "baku skyline", "baku aerial", "baku night", "baku sea", "baku street", "baku traffic",
    "baku sunset", "baku winter", "baku rain", "baku snow", "baku fog", "baku clouds"] },
  { yer: ["Ganja", "Azerbaijan"], adlar: ["Gəncə"], axtar: ["ganja azerbaijan", "ganja city azerbaijan"] },
  { yer: ["Sumqayit", "Azerbaijan"], adlar: ["Sumqayıt", "Sumgait"], axtar: ["sumgait azerbaijan", "sumqayit"] },
  { yer: ["Sheki", "Azerbaijan"], adlar: ["Şəki", "Shaki"], axtar: ["sheki azerbaijan", "sheki", "shaki azerbaijan"] },
  { yer: ["Shusha", "Azerbaijan"], adlar: ["Şuşa"], axtar: ["shusha azerbaijan", "shusha"] },
  { yer: ["Gabala", "Azerbaijan"], adlar: ["Qəbələ", "Qabala"], axtar: ["gabala azerbaijan", "gabala", "qabala"] },
  { yer: ["Lankaran", "Azerbaijan"], adlar: ["Lənkəran", "Lenkoran"], axtar: ["lankaran azerbaijan", "lankaran"] },
  { yer: ["Nakhchivan", "Azerbaijan"], adlar: ["Naxçıvan", "Nakhichevan"], axtar: ["nakhchivan azerbaijan", "nakhchivan"] },
  { yer: ["Quba", "Azerbaijan"], adlar: ["Quba", "Guba"], axtar: ["quba azerbaijan", "quba", "guba azerbaijan"] },
  { yer: ["Khinalug", "Azerbaijan"], adlar: ["Xınalıq"], axtar: ["khinalug"], teq: ["khinalug", "xinaliq"] },
  { yer: ["Shahdag", "Qusar", "Azerbaijan"], adlar: ["Şahdağ"], axtar: ["shahdag azerbaijan", "shahdag"], teq: ["shahdag"] },
  { yer: ["Mingachevir", "Azerbaijan"], adlar: ["Mingəçevir"], axtar: ["mingachevir"] },
  { yer: ["Shamakhi", "Azerbaijan"], adlar: ["Şamaxı"], axtar: ["shamakhi azerbaijan", "shamakhi"] },
  { yer: ["Lerik", "Azerbaijan"], axtar: ["lerik azerbaijan"] },
  { yer: ["Astara", "Azerbaijan"], axtar: ["astara azerbaijan"] },
  { yer: ["Zaqatala", "Azerbaijan"], adlar: ["Zaqatala", "Zagatala"], axtar: ["zaqatala azerbaijan", "zagatala"] },
  { yer: ["Khankendi", "Azerbaijan"], adlar: ["Xankəndi"], axtar: ["khankendi"] },
  { yer: ["Aghdam", "Azerbaijan"], adlar: ["Ağdam"], axtar: ["aghdam azerbaijan"] },
  { yer: ["Naftalan", "Azerbaijan"], axtar: ["naftalan"] },
  { yer: ["Flame Towers", "Baku", "Azerbaijan"], adlar: ["Alov qüllələri"], axtar: ["flame towers baku"], teq: ["flame towers", "flame tower", "flametowers"] },
  { yer: ["Baku Boulevard", "Baku", "Azerbaijan"], adlar: ["Bakı bulvarı", "Dənizkənarı Milli Park", "Seaside Boulevard"], axtar: ["baku boulevard"], teq: ["boulevard", "seaside park"] },
  { yer: ["Icherisheher", "Baku", "Azerbaijan"], adlar: ["İçərişəhər", "Baku Old City", "Old City", "Inner City"], axtar: ["baku old city", "icherisheher"], teq: ["old city", "icherisheher", "inner city", "old town"] },
  { yer: ["Maiden Tower", "Baku", "Azerbaijan"], adlar: ["Qız qalası"], axtar: ["maiden tower baku"], teq: ["maiden tower"] },
  { yer: ["Heydar Aliyev Center", "Baku", "Azerbaijan"], adlar: ["Heydər Əliyev Mərkəzi", "Heydar Aliyev Cultural Center"], axtar: ["heydar aliyev center"], teq: ["heydar aliyev", "aliyev center"] },
  { yer: ["Baku Crystal Hall", "Baku", "Azerbaijan"], adlar: ["Bakı Kristal Zalı", "Crystal Hall"], axtar: ["crystal hall baku"], teq: ["crystal hall"] },
  { yer: ["Baku Olympic Stadium", "Baku", "Azerbaijan"], adlar: ["Bakı Olimpiya Stadionu", "Olympic Stadium"], axtar: ["baku olympic stadium"], teq: ["olympic stadium"] },
  { yer: ["Tofiq Bahramov Republican Stadium", "Baku", "Azerbaijan"], adlar: ["Tofiq Bəhramov adına Respublika stadionu"], axtar: ["tofiq bahramov stadium"], teq: ["bahramov"] },
  { yer: ["Highland Park", "Baku", "Azerbaijan"], adlar: ["Dağüstü park", "Martyrs Lane", "Şəhidlər xiyabanı"], axtar: ["highland park baku"], teq: ["highland park", "martyrs lane", "martyrs alley"] },
  { yer: ["Baku TV Tower", "Baku", "Azerbaijan"], adlar: ["Bakı Teleqülləsi", "Television Tower"], axtar: ["baku tv tower"], teq: ["tv tower", "television tower"] },
  { yer: ["Palace of the Shirvanshahs", "Baku", "Azerbaijan"], adlar: ["Şirvanşahlar sarayı", "Shirvanshah Palace"], axtar: ["shirvanshah palace"], teq: ["shirvanshah", "shirvanshahs"] },
  { yer: ["Baku Metro", "Baku", "Azerbaijan"], adlar: ["Bakı metrosu", "Metro"], axtar: ["baku metro"], teq: ["metro", "subway"] },
  { yer: ["Bibi-Heybat Mosque", "Baku", "Azerbaijan"], adlar: ["Bibiheybət məscidi", "Bibi Heybat Mosque"], axtar: ["bibi heybat mosque"], teq: ["bibi heybat", "bibiheybat"] },
  { yer: ["Azerbaijan Carpet Museum", "Baku", "Azerbaijan"], adlar: ["Xalça muzeyi", "Carpet Museum"], axtar: ["carpet museum baku"], teq: ["carpet museum"] },
  { yer: ["Fountains Square", "Baku", "Azerbaijan"], adlar: ["Fəvvarələr meydanı", "Fountain Square"], axtar: ["fountains square baku"], teq: ["fountain square", "fountains square"] },
  { yer: ["Nizami Street", "Baku", "Azerbaijan"], adlar: ["Nizami küçəsi", "Torgovaya"], axtar: ["nizami street baku"], teq: ["nizami street", "torgovaya"] },
  { yer: ["National Flag Square", "Baku", "Azerbaijan"], adlar: ["Dövlət Bayrağı Meydanı", "Flag Square"], axtar: ["national flag square baku"], teq: ["flag square"] },
  { yer: ["Ateshgah Fire Temple", "Baku", "Azerbaijan"], adlar: ["Atəşgah", "Fire Temple"], axtar: ["ateshgah baku", "fire temple baku"], teq: ["ateshgah", "fire temple"] },
  { yer: ["Yanar Dag", "Absheron", "Azerbaijan"], adlar: ["Yanardağ"], axtar: ["yanar dag"], teq: ["yanar dag", "yanardag", "burning mountain"] },
  { yer: ["Gobustan National Park", "Gobustan", "Azerbaijan"], adlar: ["Qobustan Milli Parkı", "Gobustan Petroglyphs"], axtar: ["gobustan azerbaijan", "gobustan"], teq: ["gobustan", "qobustan"] },
  { yer: ["Nizami Mausoleum", "Ganja", "Azerbaijan"], adlar: ["Nizami Gəncəvi məqbərəsi"], axtar: ["nizami mausoleum ganja"], teq: ["mausoleum"] },
  { yer: ["Palace of Shaki Khans", "Sheki", "Azerbaijan"], adlar: ["Şəki Xan sarayı", "Sheki Khan Palace"], axtar: ["sheki khan palace"], teq: ["khan palace", "khans palace"] },
  { yer: ["Nohur Lake", "Gabala", "Azerbaijan"], adlar: ["Nohur gölü"], axtar: ["nohur lake"], teq: ["nohur"] },
  { yer: ["Goygol Lake", "Goygol", "Azerbaijan"], adlar: ["Göygöl"], axtar: ["goygol lake", "goygol azerbaijan"], teq: ["goygol"] },
  { yer: ["Azerbaijan"], adlar: ["Azərbaycan"], axtar: ["azerbaijan", "azerbaijan flag", "azerbaijan landscape", "azerbaijan mountains", "azerbaijan nature", "azerbaijan village"], teq: ["azerbaijan"] },
];
// Planın yer sübutu: etiketdə olmalı sözlər (plan teq + şəhərin adı və başqa adları).
function planTeq(p) {
  const s = seherOf(p.yer), list = new Set((p.teq || []).map(VS.lat));
  if (s) { list.add(s); (VS.LAQEB[s] || []).forEach(x => list.add(x)); }
  if (!s && !p.teq?.length) list.add("azerbaijan");
  return [...list];
}
const sehifeId = (menbe, id) => `${menbe.toLowerCase()}-${id}`;

// --- Böyütmə: yeni klip axtarışı və yoxlanması --------------------------------------------------------------------------------------
// deps (testdə saxta): kadrlar(url) → { jpg, gray }, baxis(prompt, jpg) → Gemini cavabı | null, zolaq(jpg, out, label).
async function boyut(lib, { env = process.env, fetch: f = globalThis.fetch, log = console.log, say = BOYUT_SAY, sorgu = SORGU_MAX, now = Date.now(), kadrDir = "", deps = {} } = {}) {
  const rep = { elave: [], redd: [], silindi: [], axtaris: 0, yoxlandi: 0, dayandi: "" };
  const banks = Object.entries(BANK).filter(([, b]) => env[b.env]);
  if (!banks.length) { log("arxiv: bank açarı yoxdur (PIXABAY_API_KEY, PEXELS_API_KEY) — heç nə edilmir"); rep.dayandi = "açar yoxdur"; return rep; }
  const today = gun(now);
  const getKadr = deps.kadrlar || (async (url, dur, w, h) => {
    const tmp = path.join(os.tmpdir(), `arxiv-${process.pid}-${Math.random().toString(36).slice(2)}.mp4`);
    try { await indir(url, tmp, KICIK_MAX_BYTES, f); return kadrlar(tmp, dur, w, h); } finally { fs.rmSync(tmp, { force: true }); }
  });
  const look = deps.baxis || ((p, jpg) => baxis(p, jpg, env, f, log));
  const strip = deps.zolaq || zolaq;
  const ara = Number(env.ARXIV_ARA_MS ?? 5000);

  // 1) Köhnə klip hələ bankdadırmı (müəllif silibsə arxivdən də çıxır). Hər işdə ən çox BAXIS_SAY, ən köhnə baxılan əvvəl.
  const banka = lib.klipler.filter(e => e.menbe !== "Sahib" && env[BANK[e.menbe]?.env]).sort((a, b) => String(a.baxildi || "").localeCompare(String(b.baxildi || ""))).slice(0, BAXIS_SAY);
  for (const e of banka) {
    const r = await BANK[e.menbe].byId(e.menbeId, env[BANK[e.menbe].env], f).catch(() => null);
    if (r?.yox) { lib.klipler = lib.klipler.filter(x => x !== e); lib.redd[e.id] = `${today} bankda silinib`; rep.silindi.push(e.id); log(`arxiv: ${e.id} bankda yoxdur — arxivdən çıxdı`); }
    else if (r?.hit) e.baxildi = today;
  }
  // 2) Axtarış: planın 30 gündə soruşulmamış ifadələri, əvvəl heç soruşulmamışlar; yerlər növbə ilə (hər yerdən bir ifadə).
  const seherSay = s => lib.klipler.filter(e => e.seher === s).length;
  const var_ = new Set(lib.klipler.map(e => e.id)), queue = [];
  for (const [bn] of banks) {
    const per = PLAN.map(p => p.axtar.map(q => ({ p, q, bn, k: `${bn.toLowerCase()}:${q}` })).filter(x => yasGun(lib.axtaris[x.k], now) >= AXTARIS_GUN));
    for (let i = 0; per.some(l => l.length > i); i++) for (const l of per) if (l[i]) queue.push(l[i]);
  }
  queue.sort((a, b) => (lib.axtaris[a.k] ? 1 : 0) - (lib.axtaris[b.k] ? 1 : 0));
  const cand = [];
  for (const it of queue) {
    if (rep.axtaris >= Math.min(sorgu, SORGU_TAVAN) || cand.length >= say || lib.klipler.length + cand.length >= ARXIV_MAX) break;
    const s = seherOf(it.p.yer);
    if (s && seherSay(s) >= (SEHER_MAX[s] || SEHER_MAX_DIGER)) continue;
    const b = BANK[it.bn], hits = await b.search(it.q, env[b.env], f);
    rep.axtaris++;
    if (!hits) { log(`arxiv: «${it.q}» ${it.bn} axtarışı alınmadı`); continue; }
    lib.axtaris[it.k] = today;
    const ic = VS.yerPlan(it.p.yer).icaze, teq = planTeq(it.p), sayac = { sub: 0 };
    let k = 0;
    for (const v of hits) {
      if (k >= SORGU_KLIP || cand.length >= say) break;
      const id = sehifeId(it.bn, v.id);
      if (var_.has(id) || lib.redd[id] || cand.some(c => c.id === id)) continue;
      const desc = VS.lat(b.teqler(v));
      const red = why => { lib.redd[id] = `${today} ${why}`; rep.redd.push({ id, q: it.q, why }); };
      if (SES_KUY.test(desc)) continue;
      if (SIYASI.test(desc)) { red("siyasi/separatçı etiket"); continue; }
      if (!(Number(v.duration) >= MUDDET_MIN) || !b.olcu(v)) continue;
      // Etiketdə yer yoxdursa sübut yoxdur: bankın axtarışı uyğun olmayanda başqa ölkənin klipini də qaytarır — belələri yazılmır.
      const sub = teq.filter(t => VS.hasName(desc, t));
      if (!sub.length) continue;
      sayac.sub++;
      const yad = VS.yadYer(desc, ic);
      if (yad) { red(`başqa yer etiketdə (${yad})`); continue; }
      const url = b.kicik(v);
      if (!url) continue;
      cand.push({ id, v, b, bn: it.bn, plan: it.p, q: it.q, sub, url, ic });
      k++;
    }
    log(`arxiv: «${it.q}» ${it.bn} — ${hits.length} nəticə, ${sayac.sub} yer sübutlu, ${k} yeni namizəd`);
  }
  log(`arxiv: ${rep.axtaris} axtarış, ${cand.length} namizəd yoxlanacaq`);
  // 3) Yoxlama: kadrlar → statik üst qat → Gemini (etiketsiz). Gemini cavab vermirsə dayanır (növbəti iş davam edir).
  for (const c of cand) {
    if (rep.yoxlandi && ara) await wait(ara);
    let kd;
    try { kd = await getKadr(c.url, c.v.duration, ...(c.b.olcu(c.v) || [])); } catch (e) { log(`arxiv: ${c.id} kadrlar alınmadı — ${String(e?.message || e).slice(0, 120)}`); continue; }
    if (!kd?.jpg?.length) continue;
    const st = kd.gray ? statikQat(kd.gray.frames, kd.gray.w, kd.gray.h) : { qerar: "bilinmir" };
    const obyekt = obyektOf(c.plan.yer), sAd = c.plan.yer.slice(obyekt ? 1 : 0).join(", ");
    const prompt = YOXLA.replace("{n}", String(kd.jpg.length)).replace(/\{seher\}/g, sAd)
      .replace("{obyekt}", obyekt ? `${obyekt}${c.plan.adlar?.length ? ` (${c.plan.adlar.join(", ")})` : ""}` : "—");
    let v = null;
    if (st.qerar !== "nisan") {
      v = await look(prompt, kd.jpg);
      if (v == null) { rep.dayandi = "Gemini cavab vermir (limit) — qalanı növbəti işdə"; log(`arxiv: ${rep.dayandi}`); break; }
      rep.yoxlandi++;
    }
    const why = st.qerar === "nisan" ? `statik üst qat — ${st.yer}` : qerar(v, c.ic);
    const label = `${why ? "RƏDD" : "QƏBUL"} ${c.id} · ${c.plan.yer[0]} · ${why || `${v.obyekt || v.gorunen_yer} ${v.eminlik}`}`;
    if (kadrDir) { fs.mkdirSync(kadrDir, { recursive: true }); strip(kd.jpg, path.join(kadrDir, `${why ? "redd" : "qebul"}-${c.id}.jpg`), label); }
    if (why) { lib.redd[c.id] = `${today} ${why}`; rep.redd.push({ id: c.id, q: c.q, why, izah: clean(v?.izah).slice(0, 200) }); log(`arxiv: rədd — ${c.id} «${c.q}»: ${why}`); continue; }
    // Obyekt yalnız Gemini onu kadrda görəndə: planın obyekti görünür (adı başqa deyil) və etiket də onu adlandırır və ya Gemini çox
    // əmindir (≥ 0,9). Yoxsa Gemini planın başqa obyektini tanıyıbsa (≥ 0,85: «İçərişəhər» axtarışında Heydər Əliyev Mərkəzi) — o obyekt;
    // heç biri deyilsə klip şəhər səviyyəsində qalır.
    let yer = c.plan.yer, adlar = c.plan.adlar || [];
    const objTeq = (c.plan.teq || []).some(t => VS.hasName(VS.lat(c.b.teqler(c.v)), VS.lat(t)));
    const gObj = clean(v.obyekt), em = Number(v.eminlik) || 0;
    const p2 = gObj && em >= OBYEKT_EMINLIK ? PLAN.find(p => obyektOf(p.yer) && seherOf(p.yer) === seherOf(c.plan.yer)
      && [obyektOf(p.yer), ...(p.adlar || [])].some(a => obyektUygun(a, gObj))) : null;
    const planObj = obyekt && v.obyekt_gorunur === true && (!gObj || [obyekt, ...(c.plan.adlar || [])].some(a => obyektUygun(a, gObj))) && (objTeq || em >= 0.9);
    if (obyekt && !planObj) { yer = p2 ? p2.yer : c.plan.yer.slice(1); adlar = p2 ? p2.adlar || [] : []; }
    else if (!obyekt && p2) { yer = p2.yer; adlar = p2.adlar || []; }
    const [w, h] = c.b.olcu(c.v);
    const e = { id: c.id, menbe: c.bn, menbeId: Number(c.v.id), sehife: c.b.sehife(c.v), muellifId: c.b.muellif(c.v), lisenziya: LISENZIYA[c.bn],
      yer, seher: seherOf(yer), obyekt: obyektOf(yer), adlar, movzu: (Array.isArray(v.movzu) ? v.movzu : []).map(x => VS.lat(x)).filter(Boolean).slice(0, 5),
      hava: HAVA.includes(v.hava) ? v.hava : "bilinmir", insan: v.insan === true, rengli: v.rengli !== false, olcu: [w, h], muddet: Math.round(Number(c.v.duration) || 0),
      keyfiyyet: Math.max(1, Math.min(5, Math.round(Number(v.keyfiyyet) || 3))),
      yoxlama: { tarix: today, model: v._model || "gemini", kadr: kd.jpg.length, teq: c.sub, eminlik: r2(Number(v.eminlik) || 0), gorunen: clean(v.gorunen_yer).slice(0, 80),
        ...(gObj ? { obyekt: gObj.slice(0, 80) } : {}), izah: clean(v.izah).slice(0, 240), statik: st.qerar }, baxildi: today };
    const bad = kecerli(e);
    if (bad) { log(`arxiv: ${c.id} sxemdən keçmədi (${bad})`); continue; }
    lib.klipler.push(e); var_.add(e.id);
    rep.elave.push({ id: e.id, yer: e.yer.join(", "), izah: e.yoxlama.izah, eminlik: e.yoxlama.eminlik });
    log(`arxiv: əlavə — ${e.id} ${e.yer.join(", ")} (${e.olcu.join("×")}, ${e.hava}, əminlik ${e.yoxlama.eminlik}): ${e.yoxlama.izah}`);
  }
  lib.yenilendi = today;
  return rep;
}
// Bank klipinin qərarı: boş sətir — qəbul; yoxsa səbəb.
function qerar(v, ic) {
  if (!v || v._xeta) return `cavab ${v?._xeta || "yoxdur"}`;
  if (v.su_nisani === true) return "su nişanı və ya ekran yazısı";
  if (v.siyasi === true) return "siyasi simvol";
  if (v.seher_dogru !== true) return `yer təsdiqlənmədi (${clean(v.gorunen_yer) || "?"})`;
  if (!(Number(v.eminlik) >= EMINLIK_MIN)) return `əminlik ${v.eminlik}`;
  const yad = VS.yadYer(`${clean(v.gorunen_yer)} ${clean(v.obyekt)}`, ic);
  if (yad) return `kadrda başqa yer (${yad})`;
  if (!(Number(v.keyfiyyet) >= KEYFIYYET_MIN)) return `keyfiyyət ${v.keyfiyyet}`;
  return "";
}

// --- Sahibin görüntüsü: GitHub Release «video-arxiv» -------------------------------------------------------------------------------
// Release-in təsvirində hər fayl üçün bir sətir:  fayl.mp4 | yer (dəqiqdən ümumiyə, vergüllə) | öz çəkilişim
//                                          və ya:  fayl.mp4 | yer | icazə: Ad Soyad, 2026-11-20
// Sətirsiz fayl və faylsız sətir qeyd olunmur (xülasədə yazılır). Release-dən silinən fayl arxivdən də çıxır.
// 4 boşluqla başlayan sətir (təsvirdəki nümunə, kod bloku) oxunmur; faylın adında boşluq ola bilər (GitHub onu nöqtə edir).
const SETIR = /^ {0,3}(?:[-*] +)?([^\s|`<>][^|`<>]*?\.(?:mp4|mov|m4v))\s*\|\s*([^|]+?)\s*\|\s*([^|]+?)\s*$/i;
const adNorm = s => String(s || "").trim().replace(/\s+/g, ".").toLowerCase();   // GitHub faylın adındakı boşluğu nöqtə edir
function sahibSetirleri(body) {
  const out = [];
  for (const line of String(body || "").split(/\r?\n/)) {
    const m = line.match(SETIR);
    if (!m) continue;
    const [, fayl, yerTxt, izn] = m, r = { fayl, setir: clean(line), yer: yerTxt.split(",").map(clean).filter(Boolean).slice(0, 4) };
    let i;
    // Üçüncü tərəfin görüntüsü (TV, sayt, sosial şəbəkə): «mənbə: Ad» — ad videoda «Görüntü: Ad» kimi yazılır.
    if ((i = clean(izn).match(/^m[əe]nb[əe]\s*:\s*(.{2,60})$/i))) i = { icaze: "menbe", kim: clean(i[1]), kredit: clean(i[1]) };
    else if (QADAGAN.test(izn)) { out.push({ ...r, xeta: "üçüncü tərəfin (TV, sosial şəbəkə, sayt) görüntüsü üçün «mənbə: Ad» yazın" }); continue; }
    else if (/^(öz|oz)(\s|$)/i.test(clean(izn))) i = { icaze: "oz-cekilis", kim: "8ulduz", kredit: "8ulduz.az" };
    else if ((i = clean(izn).match(/^icaz[əe]\s*:\s*(.+?)\s*,\s*(\d{4}-\d{2}-\d{2})$/i))) i = { icaze: "yazili-icaze", kim: clean(i[1]), kredit: clean(i[1]), icazeTarixi: i[2] };
    else { out.push({ ...r, xeta: "icazə yazılmayıb: «öz çəkilişim», «icazə: Ad Soyad, 2026-11-20» və ya «mənbə: Ad»" }); continue; }
    if (!r.yer.length) { out.push({ ...r, xeta: "yer yazılmayıb" }); continue; }
    if (!r.yer.some(y => seherOf([y]))) { out.push({ ...r, xeta: "şəhər tanınmadı: yerin sonuna şəhəri də yazın (məsələn «…, Gəncə»)" }); continue; }
    out.push({ ...r, ...i });
  }
  return out;
}
const sahibId = name => `sahib-${String(name).toLowerCase().replace(/\.[a-z0-9]+$/, "").replace(/[^a-z0-9]+/g, "-").replace(/^-+|-+$/g, "").slice(0, 60) || "klip"}`;
const rozet = a => String(a?.digest || `${a?.size}-${a?.updated_at}`);

async function release(env, f, log) {
  const h = { accept: "application/vnd.github+json", ...(env.GITHUB_TOKEN ? { authorization: `Bearer ${env.GITHUB_TOKEN}` } : {}) };
  const r = await f(`https://api.github.com/repos/${REPO}/releases/tags/${RELEASE}`, { headers: h, signal: AbortSignal.timeout(20000) }).catch(() => null);
  if (r?.status === 404) {
    if (env.ARXIV_RELEASE_YARAT !== "1" || !env.GITHUB_TOKEN) { log("arxiv: «video-arxiv» Release-i hələ yoxdur"); return { yox: true }; }
    const c = await f(`https://api.github.com/repos/${REPO}/releases`, { method: "POST", headers: { ...h, "content-type": "application/json" }, signal: AbortSignal.timeout(20000),
      body: JSON.stringify({ tag_name: RELEASE, target_commitish: "main", name: "Video arxivi — saytın öz görüntüləri", body: RELEASE_METN, make_latest: "false" }) }).catch(() => null);
    log(c?.ok ? "arxiv: «video-arxiv» Release-i yaradıldı" : `arxiv: Release yaradılmadı (HTTP ${c?.status})`);
    return c?.ok ? await c.json() : null;
  }
  return r?.ok ? await r.json() : null;
}
const RELEASE_METN = `Saytın öz video görüntüləri (sahibin çəkilişi və ya yazılı icazəli). Bələdçi: docs/sosial-video.md «Video arxivi: öz görüntünüz».

Faylı bu səhifəyə yükləyin (Edit → «Attach binaries»), sonra aşağıya hər fayl üçün bir sətir yazın:

    fayl.mp4 | yer (dəqiqdən ümumiyə, vergüllə) | öz çəkilişim
    fayl.mp4 | yer | icazə: Ad Soyad, 2026-11-20
    fayl.mp4 | yer | mənbə: Baku TV

«mənbə: Ad» — telekanalın, saytın və ya sosial şəbəkə hesabının görüntüsü; ad videoda «Görüntü: Ad» kimi yazılır.

Fayllar:
`;

// deps (testdə saxta): indir(url, file), probe(file), kadrlar(file, dur, w, h), baxis(prompt, jpg), zolaq.
async function sahib(lib, { env = process.env, fetch: f = globalThis.fetch, log = console.log, now = Date.now(), kadrDir = "", deps = {} } = {}) {
  const rep = { elave: [], redd: [], silindi: [], gozleyir: [], qeyd: [] };
  const rel = deps.release ? await deps.release() : await release(env, f, log);
  if (!rel) { rep.qeyd.push("Release oxunmadı — sahib klipləri dəyişmir"); return rep; }
  const today = gun(now), assets = new Map((rel.assets || []).map(a => [adNorm(a.name), a]));
  const lines = rel.yox ? [] : sahibSetirleri(rel.body);
  const byName = new Map(lines.filter(l => !l.xeta).map(l => [adNorm(l.fayl), l]));
  // Release-dən silinən fayl və ya sətir: arxivdən çıxır.
  for (const e of lib.klipler.filter(x => x.menbe === "Sahib")) {
    const name = adNorm(decodeURIComponent(e.fayl.slice(SAHIB_URL.length)));
    if (!assets.has(name) || !byName.has(name)) { lib.klipler = lib.klipler.filter(x => x !== e); rep.silindi.push(e.id); log(`arxiv: sahib klipi çıxdı — ${e.id} (Release-də fayl və ya sətir yoxdur)`); }
  }
  for (const l of lines.filter(x => x.xeta)) rep.redd.push({ fayl: l.fayl, why: l.xeta });
  for (const [name] of assets) if (!byName.has(name) && !lines.some(l => adNorm(l.fayl) === name)) rep.qeyd.push(`${name}: sətir yazılmayıb (yer və icazə)`);
  const load = deps.indir || ((url, file) => indir(url, file, SAHIB_MAX_BYTES, f));
  const pr = deps.probe || probe, kd = deps.kadrlar || kadrlar, look = deps.baxis || ((p, jpg) => baxis(p, jpg, env, f, log)), strip = deps.zolaq || zolaq;
  for (const [name, l] of byName) {
    const a = assets.get(name);
    if (!a) { rep.qeyd.push(`${l.fayl}: fayl Release-ə yüklənməyib`); continue; }
    const id = sahibId(a.name), old = lib.klipler.find(x => x.id === id);
    if (old && old.asset === a.id && old.rozet === rozet(a) && old.setir === l.setir) continue;   // dəyişməyib
    const url = `${SAHIB_URL}${encodeURIComponent(a.name)}`;
    if (a.size > SAHIB_MAX_BYTES) { rep.redd.push({ fayl: a.name, why: `fayl ${Math.round(a.size / 1e6)} MB (ən çox ${SAHIB_MAX_BYTES / 1e6})` }); continue; }
    // Rədd edilmiş fayl (eyni məzmun) hər gün yenidən yoxlanmır; fayl dəyişəndə (yeni rozet) yenidən.
    const rk = `sahib:${a.id}:${rozet(a)}`;
    if (lib.redd[rk]) { rep.redd.push({ fayl: a.name, why: `əvvəl rədd edilib — ${String(lib.redd[rk]).slice(11)}` }); continue; }
    const tmp = path.join(os.tmpdir(), `sahib-${process.pid}-${a.id}${path.extname(a.name) || ".mp4"}`);
    try {
      await load(a.browser_download_url || url, tmp);
      const m = pr(tmp);
      const red = why => { rep.redd.push({ fayl: a.name, why }); lib.redd[rk] = `${today} ${why}`; log(`arxiv: sahib klipi qəbul olunmadı — ${a.name}: ${why}`); };
      const menbeli = l.icaze === "menbe";   // mənbəli görüntü: platforma izi, su nişanı və ekran çəkilişi rədd səbəbi deyil
      if (!menbeli && PLATFORMA.test(m.tags)) { red(`faylda platformanın izi (${(m.tags.match(PLATFORMA) || [])[0]}): başqa saytdan endirilmiş video qəbul edilmir`); continue; }
      if (!m.w || !m.h || Math.min(m.w, m.h) < SAHIB_OLCU_MIN) { red(`ölçü ${m.w}×${m.h} (ən az ${SAHIB_OLCU_MIN} p)`); continue; }
      if (!(m.dur >= SAHIB_MUDDET_MIN)) { red(`müddət ${m.dur} s`); continue; }
      const k = kd(tmp, m.dur, m.w, m.h);
      const st = k.gray ? statikQat(k.gray.frames, k.gray.w, k.gray.h) : { qerar: "bilinmir" };
      if (!menbeli && st.qerar === "nisan") { red(`statik üst qat (loqo, su nişanı və ya titr) — ${st.yer}`); if (kadrDir) strip(k.jpg, path.join(kadrDir, `redd-${id}.jpg`), `RƏDD ${a.name} · su nişanı ${st.yer}`); continue; }
      const v = await look(SAHIB_YOXLA.replace("{yer}", l.yer.join(", ")).replace("{n}", String(k.jpg.length)), k.jpg);
      if (v == null || v._xeta) { rep.gozleyir.push(a.name); log(`arxiv: ${a.name} — Gemini cavab vermir, növbəti işdə yoxlanacaq`); continue; }
      const why = !menbeli && v.su_nisani === true ? "su nişanı, loqo və ya titr" : !menbeli && v.ekran === true ? "başqa ekranın çəkilişi" : v.siyasi === true ? "siyasi simvol"
        : v.ziddiyyet === true ? "kadrda yazılan yerə zidd əlamət" : !(Number(v.keyfiyyet) >= SAHIB_KEYFIYYET_MIN) ? `keyfiyyət ${v.keyfiyyet}` : "";
      if (kadrDir) { fs.mkdirSync(kadrDir, { recursive: true }); strip(k.jpg, path.join(kadrDir, `${why ? "redd" : "qebul"}-${id}.jpg`), `${why ? "RƏDD" : "QƏBUL"} ${a.name} · ${l.yer.join(", ")} · ${why || l.kredit}`); }
      if (why) { red(why); continue; }
      // Yer: sahibin yazdığı (adlar) + Gemini-nin ingiliscə adları; şəhər və ölkə deterministik (AZ_YER).
      const s = seherOf(l.yer), en = (Array.isArray(v.yer_en) ? v.yer_en : []).map(clean).filter(x => x && !SIYASI.test(x)).slice(0, 3);
      const sehAd = BAS(s), objEn = en.find(x => !isYerAdi(norm(x)) && obySoz(x).length > 0) || "";
      const objAz = l.yer.find(y => !seherOf([y]) && !isYerAdi(norm(y))) || "";
      const yer = [...(objEn || objAz ? [objEn || BAS(norm(objAz))] : []), sehAd, "Azerbaijan"];
      const e = { id, menbe: "Sahib", fayl: url, asset: a.id, rozet: rozet(a), setir: l.setir, icaze: l.icaze, kim: l.kim, kredit: l.kredit,
        ...(l.icazeTarixi ? { icazeTarixi: l.icazeTarixi } : {}), lisenziya: `${ICAZE[l.icaze]}${l.icaze === "yazili-icaze" ? `: ${l.kim}, ${l.icazeTarixi}` : ""}`,
        yer, seher: s, obyekt: obyektOf(yer), adlar: [...new Set([...l.yer.filter(y => !seherOf([y])), ...(objAz ? [norm(objAz)] : [])])].slice(0, 4),
        movzu: (Array.isArray(v.movzu) ? v.movzu : []).map(x => VS.lat(x)).filter(Boolean).slice(0, 5), hava: HAVA.includes(v.hava) ? v.hava : "bilinmir",
        insan: v.insan === true, olcu: [m.w, m.h], muddet: Math.round(m.dur), keyfiyyet: Math.max(1, Math.min(5, Math.round(Number(v.keyfiyyet) || 3))),
        yoxlama: { tarix: today, model: v._model || "gemini", kadr: k.jpg.length, suNisani: v.su_nisani === true, ekran: v.ekran === true, statik: st.qerar, izah: clean(v.izah).slice(0, 240) } };
      const bad = kecerli(e);
      if (bad) { red(`sxem: ${bad}`); continue; }
      lib.klipler = lib.klipler.filter(x => x.id !== id);
      lib.klipler.push(e);
      rep.elave.push({ id, fayl: a.name, yer: yer.join(", "), kredit: l.kredit });
      log(`arxiv: sahib klipi qeyd olundu — ${a.name}: ${yer.join(", ")}, kredit «${l.kredit}»`);
    } catch (err) {
      rep.gozleyir.push(a.name);
      log(`arxiv: ${a.name} yoxlanmadı — ${String(err?.message || err).slice(0, 160)}`);
    } finally { fs.rmSync(tmp, { force: true }); }
  }
  lib.yenilendi = today;
  return rep;
}

// --- Xülasə və CLI --------------------------------------------------------------------------------------------------------------
function statistika(list) {
  const by = {};
  for (const e of list) { const k = e.seher || "azerbaijan"; by[k] = (by[k] || 0) + 1; }
  return Object.entries(by).sort((a, b) => b[1] - a[1]).map(([k, n]) => `${k} ${n}`).join(", ");
}
function xulase(title, rep, list) {
  const md = (s = "") => String(s).replace(/\|/g, "/").replace(/\n/g, " ");
  const rows = [`### ${title}`, "", `Arxivdə ${list.length} klip: ${statistika(list) || "—"}`, ""];
  if (rep.elave?.length) rows.push("**Əlavə olundu**", "", "| Klip | Yer | Sübut |", "|---|---|---|", ...rep.elave.map(x => `| ${md(x.fayl || x.id)} | ${md(x.yer)} | ${md(x.kredit || `${x.eminlik} — ${x.izah}`)} |`), "");
  if (rep.redd?.length) rows.push("**Qəbul olunmadı**", "", "| Klip | Səbəb |", "|---|---|", ...rep.redd.slice(0, 60).map(x => `| ${md(x.fayl || x.id)} | ${md(x.why)}${x.izah ? ` — ${md(x.izah)}` : ""} |`), "");
  if (rep.silindi?.length) rows.push(`**Arxivdən çıxdı:** ${rep.silindi.join(", ")}`, "");
  if (rep.gozleyir?.length) rows.push(`**Yoxlanmağı gözləyir:** ${rep.gozleyir.join(", ")}`, "");
  if (rep.qeyd?.length) rows.push(...rep.qeyd.map(q => `- ${md(q)}`), "");
  if (rep.dayandi) rows.push(`_${md(rep.dayandi)}_`, "");
  return rows.join("\n");
}
function summary(text) { if (process.env.GITHUB_STEP_SUMMARY) fs.appendFileSync(process.env.GITHUB_STEP_SUMMARY, `${text}\n`); }
function sheets(dir) {
  if (!dir || !fs.existsSync(dir)) return;
  for (const kind of ["qebul", "redd"]) {
    const files = fs.readdirSync(dir).filter(x => x.startsWith(`${kind}-`) && x.endsWith(".jpg")).sort().map(x => path.join(dir, x));
    for (let i = 0; i < files.length; i += 8) vereq(files.slice(i, i + 8), path.join(dir, `_${kind}-${i / 8 + 1}.jpg`));
  }
}

async function main() {
  const args = process.argv.slice(2), cmd = args[0];
  const opt = (name, d) => { const i = args.indexOf(name); return i > 0 ? args[i + 1] : d; };
  const file = path.resolve(args[1] && !args[1].startsWith("--") ? args[1] : FAYL), kadrDir = opt("--kadr", "");
  if (cmd === "yoxla") {
    const lib = oxu(file), bad = [], ids = new Set();
    for (const e of lib.klipler) { const why = kecerli(e) || (ids.has(e?.id) ? "təkrar id" : ""); if (why) bad.push(`${e?.id || "?"}: ${why}`); ids.add(e?.id); }
    console.log(`arxiv: ${lib.klipler.length} klip (${statistika(lib.klipler)}), ${Object.keys(lib.redd).length} rədd, ${Object.keys(lib.axtaris).length} axtarış`);
    if (bad.length) { console.log(`::error::Video arxivində sxemdən keçməyən sətir: ${bad.join("; ")}`); process.exitCode = 1; }
    if (lib.klipler.length > ARXIV_MAX) { console.log(`::error::Arxivdə ${lib.klipler.length} klip (hədd ${ARXIV_MAX})`); process.exitCode = 1; }
    return;
  }
  if (cmd === "boyut" || cmd === "sahib") {
    // Budağın nüsxəsi yoxdursa (ilk iş) başlanğıc nüsxədən başlanır; varsa başlanğıc nüsxənin yeni klipləri qoşulur.
    const lib = file === FAYL ? oxu(FAYL) : fs.existsSync(file) ? birlesdir(oxu(file), oxu(FAYL)) : oxu(FAYL);
    const rep = cmd === "boyut" ? await boyut(lib, { say: Math.min(60, Number(opt("--say", BOYUT_SAY)) || BOYUT_SAY), sorgu: Number(opt("--sorgu", SORGU_MAX)) || SORGU_MAX, kadrDir }) : await sahib(lib, { kadrDir });
    yaz(lib, file);
    sheets(kadrDir);
    summary(xulase(cmd === "boyut" ? "Video arxivi: yeni kliplər" : "Video arxivi: saytın öz görüntüləri", rep, lib.klipler));
    console.log(`arxiv: +${rep.elave.length}, rədd ${rep.redd.length}, çıxdı ${rep.silindi.length}; cəmi ${lib.klipler.length}`);
    return;
  }
  console.error("İşlədilmə: video-arxiv.cjs yoxla [fayl] | boyut [fayl] [--say N] [--kadr qovluq] | sahib [fayl] [--kadr qovluq]");
  process.exitCode = 2;
}

module.exports = { FAYL, BUDAQ, BUDAQ_FAYL, kitabxana, birlesdir, PLAN, BANK, LISENZIYA, ICAZE, HAVA, SAHIB_URL, ARXIV_MAX, ARXIV_NAMIZED, QADAGAN, SIYASI, PLATFORMA,
  norm, obyektUygun, menfi, kecerli, oxu, yukle, yaz, namizedler, hazirla, statikQat, boyut, qerar, sahib, sahibSetirleri, sahibId, planTeq,
  seherOf, obyektOf, xulase, YOXLA, SAHIB_YOXLA };
if (require.main === module) main().catch(e => { console.error(`arxiv: ${String(e?.message || e)}`); process.exitCode = 1; });
