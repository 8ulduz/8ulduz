// Video xəbərin ssenarisi və görüntüsü. Sahib, 2026-11-22: «Videolar tam olaraq biabırçılıqdır. Belə video olmaz. Xəbər uzun
// olsun biraz və videogörüntü olsun o xəbərə uyğun.» Əvvəl video tünd fonda başlıq və bir cümlə idi (~15 s).
//
//   ssenari()  Gemini mənbə səhifəsinin mətnindən 5–7 cümləlik diktor mətni (ən az 4 cümlə, 450–700 simvol, ~35–45 s; sahib: «4-7 cümlədə olsun. uzun da olsun») və video bankı üçün 4–6 ingiliscə
//              axtarış ifadəsi yazır; «uygun: false» — xəbəri ümumi kadrla göstərmək olmur (görüş, qəbul), başqa xəbər seçilir. Mətn yoxlanır: hər rəqəm mənbədə olmalıdır, kiril/keçid/nida yoxdur, media qaydasından
//              (video-qayda.cjs, başlıqla birlikdə) və saytın qaydasından (policyViolation) keçir. Keçməsə başqa xəbər; Gemini işləməsə (limit) bu dövrədə video hazırlanmır.
//   goruntu()  Pexels və ya Pixabay video bankından (pulsuz lisenziya: kommersiya istifadəsi, dəyişdirmə, sosial şəbəkə —
//              https://www.pexels.com/license/, https://pixabay.com/service/license-summary/) ifadələrə uyğun 4–5 klip yükləyir.
//              2026-11-22: Pexels yeni API açarı vermir, ona görə Pixabay da var (açarı olan mənbə işləyir). Əvvəl şaquli (portrait), yoxdursa üfüqi klip (video modulu onu tam enində ortada göstərir).
//              Pexels lisenziyası tanınan insanı pis işıqda göstərməyi qadağan edir: mənfi xəbərdə (cinayət, qəza, ölüm) ifadələr
//              insansız səhnələrdir (Gemini-yə tapşırıq + kateqoriya ehtiyatı). Videoda «Görüntü: Pixabay» (və ya Pexels) yazılır.
// Açarlar: GEMINI_API_KEY (x_yazici.py ilə eyni), PIXABAY_API_KEY və/və ya PEXELS_API_KEY. Biri yoxdursa həmin hissə ötürülür, video yenə hazırlanır.
// Gemini və Pexels açarı başlıqda gedir; Pixabay yalnız ünvanda qəbul edir — ünvan heç vaxt jurnala yazılmır.
// Dil profili (2026-11-26, video-dil.cjs): diktor mətninin dili, yoxlaması (hərflər, yad əlifba, nisbi gün sözləri), etiketlər və
// protokol xəbərinin sözləri .github/video-dil/<VIDEO_DIL>.json-dandır. Montaj redaktorunun (kadr yoxlaması) göstərişi daxili işdir, azərbaycancadır.
"use strict";
const fs = require("fs"), path = require("path");
const S = require("./social.cjs");
const { dil, fmt } = require("./video-dil.cjs");
const VQ = require("./video-qayda.cjs");

const GEMINI = "https://generativelanguage.googleapis.com/v1beta/models";
const FALLBACK_MODELS = ["gemini-3.6-flash", "gemini-3.5-flash", "gemini-flash-latest", "gemini-flash-lite-latest"];   // siyahı alınmasa
const TEXT_MIN = 350, TEXT_MAX = 750, SOURCE_MAX = 5000, SENT_MIN = 4, SENT_MAX = 8;
const KLIP_SAY = 8, SPARE_MIN = 3, KLIP_MAX_BYTES = 60e6;   // 8 klip: ~45 s-lik videoda kadr 3–6 s-dən bir dəyişir (video-xeber.cjs shotPlan)
const wait = ms => new Promise(ok => setTimeout(ok, ms));
const clean = s => String(s ?? "").replace(/<[^>]+>/g, " ").replace(/\s+/g, " ").trim();

// --- Gemini ------------------------------------------------------------------------------------------------------------------
async function models(key, f) {
  try {
    const r = await f(`${GEMINI}?pageSize=200`, { headers: { "x-goog-api-key": key }, signal: AbortSignal.timeout(20000) });
    const j = r?.ok ? await r.json() : {};
    const nums = s => (s.match(/\d+/g) || []).map(Number);
    const names = (j.models || []).filter(m => (m.supportedGenerationMethods || []).includes("generateContent") && /flash/.test(m.name || "")
      && !/image|tts|audio|live|exp|preview|thinking/.test(m.name)).map(m => m.name.split("/").pop())
      .sort((a, b) => { const x = nums(a), y = nums(b); for (let i = 0; i < Math.max(x.length, y.length); i++) { const d = (y[i] || 0) - (x[i] || 0); if (d) return d; } return 0; });
    // Əvvəl ən yeni 3 flash, sonra 2 flash-lite. 2026-11-22: pulsuz səviyyənin gündəlik limitini X yazıcısı (hər 20 dəqiqə, lite
    // işlətmir) axşama qədər bitirir — lite modellərin limiti ayrıdır, video üçün qalır.
    return [...names.filter(n => !/lite/.test(n)).slice(0, 3), ...names.filter(n => /lite/.test(n)).slice(0, 2)];
  } catch { return []; }
}

// 429-un səbəbi: gündəlik limit (o model bu gün daha cavab verməz — dərhal növbəti model) və ya dəqiqəlik (gözləyib təkrar).
async function quota(r) {
  const e = await r.json().catch(() => ({}));
  const det = e?.error?.details || [];
  const v = det.flatMap(d => d?.violations || []);
  return { daily: v.some(x => /PerDay/i.test(x?.quotaId || "")), limit: v.map(x => x?.quotaValue).find(Boolean) || "" };
}

// Mətn və ya null (heç bir model cavab vermədi: açar, limit, şəbəkə). Boş sətir — model cavab verdi, amma mətn yoxdur.
// prompt: mətn və ya hazır hissələr ([{ text }, { inline_data }] — redaktorun şəkilləri).
// info: cavab verən modelin adı (info.model) — video arxivinin yoxlama sübutu üçün (video-arxiv.cjs).
async function gemini(prompt, key, f, log, env = process.env, info = {}) {
  const listed = await models(key, f);
  const order = [...new Set([env.GEMINI_MODEL, ...(listed.length ? listed : FALLBACK_MODELS)].filter(Boolean))].slice(0, 6);
  const body = JSON.stringify({ contents: [{ role: "user", parts: Array.isArray(prompt) ? prompt : [{ text: prompt }] }],
    generationConfig: { temperature: 0.3, maxOutputTokens: 8000, responseMimeType: "application/json" } });
  const tried = [];
  for (const model of order) {
    for (let attempt = 0; attempt < 3; attempt++) {
      let r;
      try {
        r = await f(`${GEMINI}/${model}:generateContent`, { method: "POST", body, signal: AbortSignal.timeout(120000),
          headers: { "x-goog-api-key": key, "content-type": "application/json" } });
      } catch (e) { tried.push(`${model}: ${e?.name || "xəta"}`); break; }
      if (r.status === 429) {
        const q = await quota(r);
        tried.push(`${model}: 429${q.daily ? ` günlük limit${q.limit ? ` ${q.limit}` : ""}` : ""}`);
        if (q.daily) break;
        await wait(Number(env.VIDEO_GEMINI_WAIT_MS ?? 10000) * (attempt + 1)); continue;
      }
      if (r.status >= 500) { tried.push(`${model}: ${r.status}`); await wait(Number(env.VIDEO_GEMINI_WAIT_MS ?? 10000) * (attempt + 1)); continue; }
      if (!r.ok) { tried.push(`${model}: ${r.status}`); break; }
      const j = await r.json().catch(() => ({}));
      const parts = j?.candidates?.[0]?.content?.parts || [];
      log(`video: ssenari modeli ${model}`);
      info.model = model;
      return parts.filter(p => !p.thought).map(p => p.text || "").join("");
    }
  }
  log(`video: Gemini cavab vermədi (${tried.join(", ") || "model yoxdur"})`);
  return null;
}

// Mənbə səhifəsinin xəbər mətni: abzaslar (social.cjs pageParagraphs), başlığa yaxın yerdən; yoxdursa xülasə + izah.
function sourceText(a, page, fallback = "") {
  const paras = page ? S.pageParagraphs(page, dil().re.herf) : [];
  const text = clean(paras.join("\n"));
  return (text.length >= 200 ? text : clean([a.summary, fallback].filter(Boolean).join("\n"))).slice(0, SOURCE_MAX);
}

// Göstəriş azərbaycancadır (redaksiyanın dili); diktor mətninin dili, yad əlifba və nisbi gün sözləri profildən: {dil}, {yad}, {nisbi}, {etiket_dili}.
const PROMPT_SABLON = `Sən 8ulduz.az xəbər saytının video redaktorusan. Aşağıdakı xəbərdən qısa video xəbər (Reels, Shorts) üçün diktor mətni yaz.
Qaydalar:
- {dil}, 5–7 aydın cümlə (ən az 4), cəmi 450–700 simvol: xəbərin əsas faktları, təfərrüatları və nəticəsi. Başlığı təkrarlama: başlıq ekranda yazılır, oxunmur — birinci cümlə xəbərin əsasını özü desin.
- Yalnız aşağıdakı mənbə mətnindəki faktlar. Mətndə olmayan ad, rəqəm, tarix, səbəb, qiymət və ya rəy ƏLAVƏ ETMƏ.
- Rəqəmləri mənbədəki kimi rəqəmlə yaz. Keçid, emoji, nida və sual işarəsi{yad} yoxdur. {nisbi} yoxdur.
- Neytral xəbər dili. Ən vacib fakt birinci cümlədə. Şərh və qiymətləndirmə yoxdur.
- Adları inisialsız yaz: «Cey. Di. Vens» yox, «ABŞ vitse-prezidenti Vens»; «İ. Əliyev» yox, «İlham Əliyev».
${VQ.GOSTERIS}
Videonun görüntüsü üçün 6–8 ingiliscə axtarış ifadəsi də yaz (Pixabay video bankı, 2–4 söz) — montaj planı kimi, SIRA İLƏ: birinci
ifadə xəbərin əsas səhnəsidir (başlıq ekranda olanda, birinci cümlə ilə görünür), sonra diktor mətninin hər cümləsinə bir səhnə, cümlələrin sırası ilə.
Video bankında çox olan sadə səhnə yaz: 2–3 söz, adi isimlər ("police car lights", "crime scene tape", "night village road") —
çox xüsusi ifadə ("bullet holes car window") tapılmır, onda yanlış kadr gəlir. Hər ifadə xəbərin məkanını, mövzusunu, əşyalarını göstərən səhnədir, məsələn "Baku city skyline", "Hanoi street traffic", "cargo ship port", "oil pump jack", "snow mountain road".
Yer adı varsa onu yaz ("Istanbul Bosphorus", "Baku boulevard"). Bayraq yalnız ölkə adı ilə ("Azerbaijan flag"), "national flags" yox.
İnsanların xəbərdəki hərəkətini (görüş, əl sıxma, imza, çıxış) göstərən səhnə yazma: tamaşaçı onları xəbərin qəhrəmanı sanar.
Xəbərdə olmayan iş, sənət və fəaliyyəti (qazma, qaynaq, dülgərlik, fabrik, mətbəx, idman zalı) göstərən səhnə yazma.
Konkret tanınan insanların adını yazma. Xəbər cinayət, qəza, ölüm, xəstəlik, fəlakət, məhkəmə və ya münaqişə haqqındadırsa, yalnız
insansız səhnələr seç (bina, yol, polis maşınının işıqları, məhkəmə binası, şəhər, kənd). Belə xəbərdə silahı, aləti (bıçaq, balta,
lom, çəkic, mişar, tapança), qanı, meyiti, tabutu və hadisənin özünü göstərən ifadə YAZMA, mətndə adı çəkilsə də: kadr cinayəti təkrar göstərər.
"uygun": false YALNIZ xəbər protokol hadisəsidirsə: rəsmi görüş, qəbul, danışıqlar, telefon danışığı, təbrik, başsağlığı, təyinat, məktub
(ümumi kadr həmin adamları göstərirmiş kimi görünər). Qalan hər xəbər — true: cinayət, qəza, ölüm, yanğın, hadisə, idman, bəyanat, müsahibə,
iqtisadiyyat, qiymət, hava, təbiət, nəqliyyat, tikinti, texnologiya, müharibənin gedişi. Xəbər konkret bir adam haqqında olsa belə, səhnə
onu yox, mövzunu göstərir (atışma — "police car lights night", bəyanat sərhəd haqqında — "US Mexico border wall"). Şübhə olanda true.
"yer": xəbərin baş verdiyi və mətndə adı çəkilən konkret yerlər ingiliscə, Pixabay/Wikipedia yazılışı ilə, dəqiqdən ümumiyə:
məsələn ["Ganja City Stadium", "Ganja", "Azerbaijan"], ["Qardabani", "Georgia"], ["White House", "Washington", "United States"].
Yer yoxdursa []. Video əvvəlcə bu yerlərin əsl görüntüsü ilə axtarılır, başqa ölkənin və şəhərin tanınan görüntüsü götürülmür.
"etiket": postun 3 mövzu etiketi (hashtag), {etiket_dili} və ya xəbərdəki xüsusi adla, boşluqsuz, məsələn "futbol", "PremyerLiqa",
"Qarabağ", "neft", "hava". Partiya, siyasi şüar və təhqir yoxdur.
Yalnız JSON qaytar, başqa heç nə: {"uygun": true, "text": "<diktor mətni>", "axtar": ["...", "..."], "yer": ["...", "..."], "etiket": ["...", "...", "..."]}

Başlıq: {title}
Bölmə: {bolme}
Mənbə mətni:
{source}`;
// Profilin dili ilə göstəriş ({title}, {bolme}, {source} ssenari()-də doldurulur). PROMPT — az profilininki (testlər oxuyur).
const yadQeyd = s => (s.yad_herf ? `, ${s.yad_herf_adi}` : "");
const promptOf = (D = dil()) => fmt(PROMPT_SABLON, { dil: D.ssenari.dil, yad: yadQeyd(D.ssenari), nisbi: D.ssenari.nisbi_gun_misal, etiket_dili: D.ssenari.etiket_dili });
const PROMPT = promptOf(dil("az"));

// Kiril hərfinin latın oxşarı (lite modellər «ə» yerinə kiril «ә» yazır, 2026-11-22 beşinci nümunə). Qalan kiril hərfi yoxlamada düşür.
const LATIN = { "ә": "ə", "Ә": "Ə", "ө": "ö", "Ө": "Ö", "ү": "ü", "Ү": "Ü", "һ": "h", "Һ": "H", "ғ": "ğ", "Ғ": "Ğ", "а": "a", "е": "e", "о": "o",
  "р": "p", "с": "c", "у": "y", "х": "x", "і": "i", "ј": "j", "А": "A", "В": "B", "Е": "E", "К": "K", "М": "M", "Н": "H", "О": "O", "Р": "P",
  "С": "C", "Т": "T", "Х": "X", "І": "I", "Ј": "J" };
const latin = s => String(s).replace(/[әӘөӨүҮһҺғҒаеорсухіјАВЕКМНОРСТХІЈ]/g, ch => LATIN[ch]);
// Yalnız latın əlifbalı dildə (profil: ssenari.latin): kiril əlifbalı dildə «а», «е» öz hərfidir.
const dilLatin = s => (dil().ssenari.latin ? latin(s) : String(s));

// Diktor mətninin yoxlanması. Səbəb (sətir) və ya "" — keçdi.
const NUM = /\d+(?:[.,]\d+)*/g;
const normNum = s => s.replace(/[.,](?=\d{3}\b)/g, "").replace(",", ".");
// Rum rəqəmi (I–LXXXIX) → ədəd; düzgün yazılmayıbsa 0.
function roman(s) {
  const v = { I: 1, V: 5, X: 10, L: 50 };
  let n = 0;
  for (let i = 0; i < s.length; i++) n += v[s[i]] < (v[s[i + 1]] || 0) ? -v[s[i]] : v[s[i]];
  const back = x => [["L", 50], ["XL", 40], ["X", 10], ["IX", 9], ["V", 5], ["IV", 4], ["I", 1]].reduce((acc, [r, k]) => { while (x >= k) { acc += r; x -= k; } return acc; }, "");
  return n > 0 && back(n) === s ? n : 0;
}
// Şərh həddi (sahib, 2026-11-27: «belə çox qısa və şərhi çox az və başa düşülməyən olmasın videolar» — iki cümləlik X videosu
// Instagram və Facebook-dan silindi): diktor mətni ən az SERH_MIN.cumle cümlə və SERH_MIN.simvol simvol. X videosu seçimdə
// (video-dunya.cjs xHazirla) və «Videonu yoxla» addımında (sosial-video.yml, hava videosundan başqa hər video) yoxlanır.
const SERH_MIN = { cumle: 3, simvol: 180 };
function serhAzdir(text, h = SERH_MIN) {
  const t = String(text ?? "").replace(/\s+/g, " ").trim(), n = t ? t.split(/(?<=[.!?…])\s+(?=[\p{Lu}\d«"])/u).filter(Boolean).length : 0;
  return n < h.cumle || t.length < h.simvol ? `şərh azdır: ${n} cümlə, ${t.length} simvol (ən az ${h.cumle} cümlə, ${h.simvol} simvol)` : "";
}
// Qan qadağasının sözü (x.kenar: qanlı, qan içində, meyit, cəsəd, ölüm anı, edam, baş kəsmə) və ya "". JS-in /i bayrağı «İ»-ni «i»
// saymır: mətn həm özü, həm dilin kiçik hərfi ilə yoxlanır («MEYİT»).
const kenarCache = new WeakMap();
function kenarSozu(metn, D = dil()) {
  if (!kenarCache.has(D)) kenarCache.set(D, D.x?.kenar ? new RegExp(D.x.kenar, "iu") : null);
  const re = kenarCache.get(D), s = String(metn ?? "");
  return re ? ((s.match(re) || s.toLocaleLowerCase(D.locale || "az").match(re) || [])[0] || "") : "";
}
// hed: başqa ölçülü mətn üçün hədlər (X videosunun qısa mətni, video-dunya.cjs xGenislet): { min, max, sentMin, sentMax }.
function checkText(text, source, a, policy = () => false, hed = {}) {
  const { min = TEXT_MIN, max = TEXT_MAX, sentMin = SENT_MIN, sentMax = SENT_MAX } = hed;
  if (text.length < min || text.length > max) return `uzunluq ${text.length} (${min}–${max})`;
  // «Cey. Di. Vens»: altyazı hər nöqtədə bölünür, «Di.» ekranda tək qalır (2026-11-22 nümunə videosu).
  if (/(?:^|[\s(])\p{Lu}\p{Ll}{0,2}\.\s+\p{Lu}\p{Ll}{0,2}\./u.test(text)) return "inisial";
  const sent = text.split(/(?<=[.!?…])\s+(?=[\p{Lu}\d«"])/u).filter(Boolean).length;
  if (sent < sentMin || sent > sentMax) return `cümlə sayı ${sent} (${sentMin}–${sentMax})`;
  const D = dil();
  if (D.re.yadHerf?.test(text)) return D.ssenari.yad_herf_adi;
  if (/https?:|www\.|[!?]/.test(text)) return "keçid, nida və ya sual";
  if (D.re.nisbiGun.test(text)) return "nisbi gün sözü";
  if (!D.re.herf.test(text)) return D.ssenari.dil_xetasi;
  // Mənbədəki rum rəqəmi də rəqəmdir: «XII turunda» → «12-ci tur» (2026-11-23: lite model belə yazdı, mətn rədd olunmuşdu).
  const have = new Set([...(source.match(NUM) || []).map(normNum), ...(source.match(/\b[IVXL]{1,7}\b/g) || []).map(roman).filter(Boolean).map(String)]);
  const extra = (text.match(NUM) || []).map(normNum).filter(n => !have.has(n));
  if (extra.length) return `mənbədə olmayan rəqəm: ${extra.slice(0, 3).join(", ")}`;
  // Qan qadağası (sahib, 2026-11-27; profil x.kenar): əvvəl yalnız X, dünya və kanal videosunda idi. Xəbər videosunda yox idi — Nərgiz
  // Nəcəfovanın ölümü videosunun mətnində «meyiti hissələrə bölüblər» keçdi (iş 46036515482). İndi hər diktor mətni, videonun başlığı ilə.
  const qan = kenarSozu([clean(a?.title), text].filter(Boolean).join(". "), D);
  if (qan) return `qan qadağası: «${qan}»`;
  // Media qaydası (sahib, 2026-11-27: «Hamısını əlavə et»; video-qayda.cjs): diktor mətni və videonun başlığı birlikdə. Xəbər videosunun
  // başlığı mənbədəndir — qaydanı pozan başlıqla video olmur.
  const mq = VQ.yoxla([clean(a?.title), text].filter(Boolean).join(". "), D);
  if (mq) return `media qaydası: ${mq}`;
  if (policy({ ...a, summary: text })) return "saytın qaydasından keçmir";
  return "";
}

// Mövzu etiketləri (sahib 2026-11-23: «tam professional»; kəşf üçün): «#» atılır, yalnız hərf, rəqəm, «_», 2–30 simvol, ən çox 3,
// təkrarsız; ümumi etiketlər (#8ulduz #xəbərlər #Azərbaycan) postda onsuz da var. Kiril oxşarı latına çevrilir, qalan kiril atılır.
// Ümumi etiketlər, yad əlifba və kiril→latın çevirməsi profildəndir (ssenari.etiket_umumi, yad_herf, latin).
function hashtags(list) {
  const D = dil(), lc = s => s.toLocaleLowerCase(D.locale), base = new Set(D.ssenari.etiket_umumi), out = [];
  for (const x of Array.isArray(list) ? list : []) {
    const t = dilLatin(String(x ?? "")).replace(/^#+/, "").replace(/[^\p{L}\p{N}_]/gu, "");
    if (t.length < 2 || t.length > 30 || D.re.yadHerf?.test(t) || base.has(lc(t))) continue;
    if (!out.some(o => lc(o) === lc(t))) out.push(t);
  }
  return out.slice(0, 3);
}

// Axtarış ifadələri: yalnız latın hərfi, 2–5 söz, ən çox 8 (montaj planı: başlıq + hər cümlə), sıra saxlanır, təkrarsız.
function queries(list) {
  const out = [];
  for (const q of Array.isArray(list) ? list : []) {
    const s = clean(q).replace(/[^A-Za-z \-']/g, " ").replace(/\s+/g, " ").trim().toLowerCase();
    const n = s.split(" ").length;
    if (s.length >= 3 && s.length <= 60 && n <= 5 && !out.includes(s)) out.push(s);
  }
  return out.slice(0, 8);
}
// Gemini olmayanda bölməyə görə ümumi səhnələr (insansız; Pexels-də çox klip olanlar).
const EHTIYAT = {
  // Yer adı yoxdur: ehtiyat səhnə xəbərin harada olduğunu bilmir (2026-11-23: Gürcüstan xəbərinin başlığında Bakı göründü).
  siyaset: ["government building", "parliament building", "city skyline night", "conference microphones"],
  prezident: ["government building", "parliament building", "city skyline night", "conference microphones"],
  iqtisadiyyat: ["business district skyline", "cargo ship port", "stock market screen", "factory production line"],
  idman: ["football stadium", "sports stadium lights", "running track", "football ball grass"],
  dunya: ["world globe", "city skyline night", "airport airplane", "world map"],
  texnologiya: ["technology circuit", "data center servers", "smartphone screen", "code on screen"],
  elm: ["science laboratory", "microscope laboratory", "space stars", "technology circuit"],
  hadise: ["police car lights night", "city street night", "emergency lights", "road traffic night"],
  cemiyyet: ["city street people walking", "city lights night", "residential buildings", "city street traffic"],
  medeniyyet: ["theater stage lights", "museum hall", "old city architecture", "concert stage lights"],
  // Maraqlı video (video-maraqli.cjs): ümumi səhnə yoxdur — gepard haqqında videoda şəhər görünməsin; klip azdırsa mövzu ötürülür.
  maraqli: [],
};
// Faciə xəbərində bölmədən asılı olmayaraq hadisə səhnələri (insansız): Nərgiz xəbəri «Cəmiyyət»də idi, ehtiyatı «city street people walking» idi.
const ehtiyat = a => (a.facie ? EHTIYAT.hadise : EHTIYAT[a.category]) || ["city skyline night", "city street traffic", "city lights night", "clouds timelapse"];

// Protokol xəbəri (görüş, qəbul, telefon danışığı, təbrik, başsağlığı): ümumi kadr həmin adamları göstərirmiş kimi görünər —
// belə xəbərdən video hazırlanmır (2026-11-22 nümunə videosu: Prezidentin qəbulu, fonda yad əl sıxma və göy). Gemini də yoxlayır («uygun»).
// Sözlər profildədir (ssenari.protokol): başlıq videonun dilindədir.
const protokol = a => a?.category === "prezident" || dil().re.protokol.test(clean(a?.title));

// Ssenari: { text, axtar, uygun: true } — mətn hazırdır; { uygun: false, sebeb } — bu xəbərdən video olmur (kadrla göstərilmir,
// mənbə qısadır, mətn yoxlamadan keçmədi), başqa xəbər seçilir; null — Gemini işləmir (açar yoxdur, limit bitib): bu dövrədə video yoxdur.
// Sahib, 2026-11-22: mənbənin öz cümlələri və ümumi kadrla video «biabırçılıqdır» — Gemini-siz video paylaşılmır.
async function ssenari(a, page, { env = process.env, fetch: f = globalThis.fetch, policy = () => false, log = console.log, fallback = "" } = {}) {
  const key = env.GEMINI_API_KEY;
  if (!key) { log("video: GEMINI_API_KEY yoxdur — ssenari yazılmır"); return null; }
  const source = sourceText(a, page, fallback);
  if (source.length < 120) { log("video: mənbə mətni qısadır — başqa xəbər"); return { uygun: false, sebeb: "mənbə qısadır" }; }
  const prompt = promptOf().replace("{title}", clean(a.title)).replace("{bolme}", clean(a.bolme || a.category || "")).replace("{source}", source);
  const raw = await gemini(prompt, key, f, log, env);
  if (raw == null) return null;
  let j = null;
  try { j = JSON.parse(String(raw).replace(/^```(?:json)?\s*|\s*```$/g, "")); } catch {}
  if (j?.uygun === false) { log("video: Gemini — xəbəri ümumi kadrla yanıltmadan göstərmək olmur (görüş, qəbul), başqa xəbər"); return { uygun: false, sebeb: "kadrla göstərilmir" }; }
  const text = dilLatin(clean(j?.text));
  const why = text ? checkText(text, `${source}\n${clean(a.title)}`, a, policy) : "cavab boşdur və ya JSON deyil";
  if (why) { log(`video: Gemini mətni qəbul olunmadı (${why}) — başqa xəbər`); return { uygun: false, sebeb: why }; }
  const etiket = hashtags(j?.etiket);
  return { text, axtar: queries(j?.axtar), yer: places(j?.yer), uygun: true, ...(etiket.length && !policy({ ...a, summary: etiket.join(" ") }) ? { etiket } : {}) };
}

// --- Görüntü: Pexels və Pixabay ------------------------------------------------------------------------------------------------------------------
// Klipin ən uyğun faylı: şaquli klipdə hündürlüyü 1920-yə ən yaxın (≥1280), üfüqidə hündürlüyü 1440-a ən yaxın (≥1080). Üfüqi klip
// 9:16-ya kəsilir (video-xeber.cjs, ağıllı kəsim): 1080p-dən kəsilən hissə 608×1080-dir və 1,8 dəfə böyüyüb bulanıqlaşırdı; Pixabay-da 4K.
function bestFile(v, portrait) {
  const files = (v?.video_files || []).filter(x => x?.link && /mp4/.test(x.file_type || "") && x.width > 0 && x.height > 0);
  const ok = portrait ? files.filter(x => x.height > x.width && x.height >= 1280) : files.filter(x => x.width >= x.height && x.height >= 1080);
  const want = portrait ? 1920 : 1440;   // Pexels faylın ölçüsünü vermir: 4K adətən KLIP_MAX_BYTES-dan böyükdür, 1440p (810×1440 kəsim) sığır
  ok.sort((x, y) => Math.abs(x.height - want) - Math.abs(y.height - want) || x.width - y.width);
  return ok[0] || null;
}

const enc = encodeURIComponent;
async function getJson(u, headers, f) {
  try {
    const r = await f(u, { headers, signal: AbortSignal.timeout(20000) });
    return r?.ok ? await r.json() : null;
  } catch { return null; }   // ünvan jurnala yazılmır: Pixabay açarı ünvandadır
}
// Pixabay faylı: hər iki ölçüsü ən azı 1080 olan ilk nüsxə (medium adətən 1920×1080, large 3840×2160), ≤ KLIP_MAX_BYTES. Üfüqi klipdə
// əvvəl large: kəsiləcək (bestFile-a bax).
function pixabayFile(v) {
  const s = v?.videos || {};
  return (s.large?.width > s.large?.height ? [s.large, s.medium, s.small] : [s.medium, s.large, s.small]).find(x => x?.url && x.width > 0 && x.height > 0 && Math.min(x.width, x.height) >= 1080
    && !(x.size > KLIP_MAX_BYTES)) || null;
}
// Klipin axtarışa uyğunluğu: klipin təsviri (Pixabay etiketləri, səhifə ünvanının sözləri) axtarış sözləri ilə tutuşdurulur.
// 2026-11-22 üçüncü nümunə: «us mexico border wall» → dələ, «washington dc capitol building» → Yaponiya qalası çıxdı (şaquli klipi
// uyğunluqdan üstün tutmuşdum). 3+ mənalı sözdə ən az 2-si, az sözdə 1-i üst-üstə düşməlidir; düşməsə 0 — klip götürülmür.
const STOP = new Set(["the", "and", "with", "for", "from", "into", "over", "near"]);
const stem = w => (w.length > 4 ? w.replace(/ies$/, "y").replace(/(?<!s)s$/, "") : w);
const words = s => String(s || "").toLowerCase().split(/[^a-z]+/).filter(w => w.length > 2 && !STOP.has(w)).map(stem);
// Qayda: ifadənin əsas sözü — sonuncu konkret (ümumi olmayan) söz, ingiliscədə ad birləşməsinin özəyi («border WALL», «capitol»,
// «baku city skyline»-da «baku») — klipin təsvirində olmalıdır və konkret sözlərin ən az 60%-i (1→1, 2–3→2, 4→3) üst-üstə düşməlidir; 2026-11-23: «bullet holes car window» 2 sözlə tikinti işçisinə keçmişdi.
// Dördüncü nümunə: «Mexico City» etiketli dələ «us mexico border wall»-a, Empire State «united states capitol»-a keçmişdi.
// Cins sözləri (alət, avadanlıq, əşya, qurğu…) də ümumidir (2026-11-27, iş 46036515482): «metal crowbar tool»-da əsas söz «tool» sayılırdı
// və «drill, tool, metal» etiketli qazma klipi lom əvəzinə keçdi; indi əsas söz «crowbar»-dır.
const UMUMI = new Set(["city", "building", "street", "road", "night", "view", "aerial", "people", "traffic", "light", "sky", "skyline",
  "background", "office", "outdoor", "water", "landscape", "modern", "old", "new", "urban", "center", "exterior", "interior", "drone",
  "united", "state", "usa", "america", "american", "world", "international", "national", "country", "global",
  "tool", "equipment", "object", "device", "item", "thing", "machine", "material", "closeup", "detail", "scene", "footage"]);
function relevance(q, desc) {
  const want = [...new Set(words(q))], have = new Set(words(desc));
  if (!want.length) return 1;
  const n = want.filter(w => have.has(w)).length, spec = want.filter(w => !UMUMI.has(w));
  if (!spec.length) return n >= Math.min(2, want.length) ? n : 0;   // yalnız ümumi sözlər («city street traffic»)
  const m = spec.filter(w => have.has(w)).length;
  return have.has(spec[spec.length - 1]) && m >= Math.ceil(spec.length * 0.6) ? n + m : 0;   // 1→1, 2–3→2, 4→3
}
const slug = u => String(u || "").split("?")[0].split("/").filter(Boolean).pop() || "";

// --- Yer (sahib, 2026-11-23: «həqiqi Gəncənin yeni stadionu olan videolardan istifadə etmək lazımdır. digərləri də belə») --------
// Gemini xəbərin konkret yerlərini verir (yer: dəqiqdən ümumiyə). Axtarış əvvəlcə bu yerlərlə aparılır (şəhər həmişə ölkə ilə:
// «ganja» ingiliscədə həm də kənafdır), tapılan əsl yer görüntüsü başlıq kadrına düşür. Etiketində xəbərə aid olmayan ölkə və
// ya şəhər olan klip götürülmür (2026-11-23: Gəncə xəbərində Batumi stadionu, Gürcüstan xəbərində Bakı göründü).
const OLKELER = ["afghanistan", "albania", "algeria", "argentina", "armenia", "australia", "austria", "azerbaijan", "bahrain", "bangladesh",
  "belarus", "belgium", "bolivia", "bosnia", "brazil", "bulgaria", "cambodia", "canada", "chile", "china", "colombia", "croatia", "cuba",
  "cyprus", "czech", "denmark", "egypt", "england", "estonia", "ethiopia", "finland", "france", "georgia", "germany", "greece", "hungary",
  "iceland", "india", "indonesia", "iran", "iraq", "ireland", "israel", "italy", "jamaica", "japan", "jordan", "kazakhstan", "kenya",
  "kosovo", "kuwait", "kyrgyzstan", "latvia", "lebanon", "libya", "lithuania", "luxembourg", "malaysia", "maldives", "malta", "mexico",
  "moldova", "monaco", "mongolia", "montenegro", "morocco", "nepal", "netherlands", "holland", "new zealand", "nigeria", "norway", "oman",
  "pakistan", "palestine", "panama", "peru", "philippines", "poland", "portugal", "qatar", "romania", "russia", "saudi arabia", "scotland",
  "serbia", "slovakia", "slovenia", "somalia", "spain", "sri lanka", "sudan", "sweden", "switzerland", "syria", "taiwan", "tajikistan",
  "tanzania", "thailand", "tunisia", "turkey", "turkiye", "turkmenistan", "uganda", "ukraine", "united arab emirates", "uae", "usa",
  "united states", "america", "american", "united kingdom", "britain", "uruguay", "uzbekistan", "venezuela", "vietnam", "wales", "yemen"];
const SEHERLER = ["new york", "manhattan", "brooklyn", "los angeles", "hollywood", "san francisco", "chicago", "las vegas", "miami", "seattle",
  "boston", "washington", "london", "paris", "rome", "venice", "florence", "milan", "naples", "berlin", "munich", "hamburg", "frankfurt",
  "amsterdam", "rotterdam", "brussels", "barcelona", "madrid", "seville", "lisbon", "porto", "prague", "vienna", "budapest", "warsaw",
  "krakow", "istanbul", "ankara", "antalya", "izmir", "dubai", "abu dhabi", "doha", "riyadh", "mecca", "jerusalem", "tel aviv", "cairo",
  "moscow", "saint petersburg", "kyiv", "kiev", "odesa", "odessa", "kharkiv", "minsk", "tbilisi", "batumi", "yerevan", "tehran", "tabriz",
  "baku", "ganja", "sheki", "shusha", "lankaran", "sumgait", "sumqayit", "nakhchivan", "gabala", "beijing",
  // Azərbaycanın başqa şəhər və yerləri (video arxivi, 2026-11-23): Quba xəbərinə Şəki, Bakı xəbərinə Qəbələ kadrı düşməsin.
  "qabala", "shaki", "nakhichevan", "lenkoran", "quba", "guba", "qusar", "gusar", "khinalug", "shahdag", "mingachevir", "mingechevir",
  "shamakhi", "shamakha", "khankendi", "aghdam", "agdam", "zaqatala", "zagatala", "masalli", "astara", "lerik", "shirvan", "naftalan",
  "gobustan", "qobustan", "fuzuli", "lachin", "kalbajar", "jabrayil", "zangilan", "khachmaz", "balakan", "ismayilli", "goychay", "goygol",
  "barda", "yevlakh", "khizi", "siyazan", "tovuz", "gazakh", "agstafa", "salyan", "neftchala", "imishli", "sabirabad", "beylagan", "shanghai", "hong kong",
  "shenzhen", "tokyo", "osaka", "kyoto", "seoul", "busan", "taipei", "kaohsiung", "bangkok", "phuket", "hanoi", "ho chi minh", "saigon",
  "bali", "jakarta", "manila", "kuala lumpur", "sydney", "melbourne", "toronto", "vancouver", "montreal", "rio de janeiro", "sao paulo",
  "buenos aires", "mexico city", "cancun", "havana", "bogota", "mumbai", "delhi", "kolkata", "kathmandu", "cape town", "johannesburg",
  "nairobi", "marrakech", "oslo", "stockholm", "copenhagen", "helsinki", "reykjavik", "dublin", "edinburgh", "zurich", "geneva",
  "salzburg", "athens", "santorini", "dubrovnik", "belgrade", "bucharest", "sofia", "almaty", "astana", "tashkent", "samarkand",
  "bishkek", "ashgabat", "dushanbe",
  // ABŞ ştatları: «washington» axtarışına Vaşinqton ştatının (Oreqon sərhədi) mənzərəsi gəlmişdi (2026-11-23).
  "oregon", "california", "texas", "florida", "alaska", "hawaii", "colorado", "arizona", "utah", "nevada", "montana", "idaho"];
// Adı başqa yerlə eyni olan yer: axtarışda dəqiq adı (Vaşinqton şəhəri, ştat yox).
const DEQIQ = { washington: "washington dc" };
// Eyni yerin başqa adları; ölkə yeganə yerdirsə (şəhər yoxdur) paytaxtının görüntüsü də uyğundur.
const LAQEB = { "united states": ["usa", "america", "american", "united states"], usa: ["usa", "america", "american", "united states"],
  "united kingdom": ["united kingdom", "britain", "england", "uk"], turkiye: ["turkey", "turkiye"], turkey: ["turkey", "turkiye"],
  ukraine: ["ukraine"], kyiv: ["kyiv", "kiev"], sumqayit: ["sumqayit", "sumgait"], sumgait: ["sumqayit", "sumgait"],
  gabala: ["gabala", "qabala"], qabala: ["gabala", "qabala"], sheki: ["sheki", "shaki"], shaki: ["sheki", "shaki"],
  nakhchivan: ["nakhchivan", "nakhichevan"], nakhichevan: ["nakhchivan", "nakhichevan"], lankaran: ["lankaran", "lenkoran"], lenkoran: ["lankaran", "lenkoran"],
  quba: ["quba", "guba", "khinalug"], guba: ["quba", "guba", "khinalug"], qusar: ["qusar", "gusar", "shahdag"], gusar: ["qusar", "gusar", "shahdag"], shahdag: ["shahdag", "qusar", "gusar"],
  mingachevir: ["mingachevir", "mingechevir"], mingechevir: ["mingachevir", "mingechevir"], shamakhi: ["shamakhi", "shamakha"], shamakha: ["shamakhi", "shamakha"],
  aghdam: ["aghdam", "agdam"], agdam: ["aghdam", "agdam"], zaqatala: ["zaqatala", "zagatala"], zagatala: ["zaqatala", "zagatala"],
  gobustan: ["gobustan", "qobustan"], qobustan: ["gobustan", "qobustan"] };
const PAYTAXT = { azerbaijan: ["baku"], turkey: ["istanbul", "ankara"], turkiye: ["istanbul", "ankara"], russia: ["moscow"], georgia: ["tbilisi"],
  ukraine: ["kyiv", "kiev"], "united states": ["washington", "new york"], usa: ["washington", "new york"], france: ["paris"],
  "united kingdom": ["london"], germany: ["berlin"], iran: ["tehran"], china: ["beijing"], japan: ["tokyo"], italy: ["rome"], israel: ["jerusalem", "tel aviv"] };
const YERLER = [...SEHERLER, ...OLKELER];   // əvvəl şəhər: jurnalda dəqiq ad
const lat = s => clean(s).toLowerCase().replace(/[^a-z\s'-]/g, " ").replace(/\s+/g, " ").trim();
const hasName = (text, name) => new RegExp(`(^|[^a-z])${name.replace(/ /g, "[\\s-]")}([^a-z]|$)`).test(text);
// Gemini-nin yer siyahısı: yalnız latın, 1–5 söz, ən çox 5, sıra saxlanır.
function places(list) {
  const out = [];
  for (const x of Array.isArray(list) ? list : []) {
    const s = clean(x).replace(/[^A-Za-z \-']/g, " ").replace(/\s+/g, " ").trim();
    if (s.length >= 3 && s.length <= 60 && s.split(" ").length <= 5 && !out.some(o => o.toLowerCase() === s.toLowerCase())) out.push(s);
  }
  return out.slice(0, 5);
}
// { axtar: yer ifadələri (şəhər + ölkə), icaze: Set(xəbərə aid yer adları) }.
function yerPlan(yer) {
  const names = places(yer).map(lat);
  const country = names.find(n => OLKELER.includes(n)) || "";
  const icaze = new Set();
  for (const n of names) for (const g of YERLER) if (hasName(n, g)) { icaze.add(g); (LAQEB[g] || []).forEach(x => icaze.add(x)); }
  if (names.length && names.every(n => OLKELER.includes(n))) for (const n of names) (PAYTAXT[n] || []).forEach(x => icaze.add(x));
  const axtar = names.filter(n => !OLKELER.includes(n)).map(n => DEQIQ[n] || (country && !n.includes(country) ? `${n} ${country}` : n));
  return { axtar: queries(axtar), icaze };
}
// Klipin təsvirində xəbərə aid olmayan ölkə və ya şəhər varmı.
function yadYer(desc, icaze) {
  const t = lat(desc);
  return YERLER.find(g => !icaze.has(g) && hasName(t, g)) || "";
}
// --- Mövzu (sahib, 2026-11-27: «nərgizin ölümü videosunda çilingər işləri göstərilir. belə olmaz axı.») ------------------------
// İş 46036515482 (YouTube FvteQ4nJnuw): ölüm xəbərinin diktor mətnində «dəmir linglə zərbələr endirilib» cümləsi vardı. Gemini ondan
// «metal crowbar tool» ifadəsi yazdı, Pixabay qazma (39: drill, tool, metal, drilling, craftsman) və qaynaq (12543: welding, industry,
// worker, factory, metal, tool) kliplərini verdi. Söz uyğunluğu «metal» + «tool» ilə keçdi («crowbar» klipdə yox idi), redaktor ikisini
// seçdi və 51 saniyəlik video 11 kadrda bu iki klipdən quruldu. Klipin xəbərin mövzusuna uyğunluğunu heç bir addım yoxlamırdı.
// Qayda (hər xəbər, kodla): klipin etiketində və ya axtarış ifadəsində fəaliyyət (iş və sənət, mətbəx, tibb, idman zalı, əyləncə)
// varsa, o fəaliyyətin adı xəbərin başlığında və ya diktor mətnində olmalıdır (profil: kadr.movzu). Yoxdursa klip götürülmür:
// uyğun klip çatmırsa yad klip qoyulmur, video olmur (KLIP_MIN). Faciə xəbərində (ölüm, qətl, qəza, fəlakət, məhkəmə; profil:
// kadr.facie) əlavə ehtiyat: silah və alət, qan, meyit, ölüm, qorxu, yaxın planda insan və şən əhval kadrı heç vaxt — belə ifadə
// banka göndərilmir da; ehtiyat səhnələr hadisə bölməsinindir (insansız); montaj redaktoru kadrlara baxmayıbsa bank klipi qoyulmur.
const teqler = list => new Set(list.flatMap(words));
const MOVZU_TEQ = {
  is: teqler(["craft", "crafts", "craftsman", "craftsmanship", "handicraft", "handmade", "workshop", "carpenter", "carpentry", "woodwork",
    "woodworking", "joinery", "locksmith", "welding", "welder", "weld", "drilling", "drill", "driller", "lathe", "grinder", "grinding", "sawing",
    "sawmill", "forge", "forging", "blacksmith", "metalwork", "metalworking", "soldering", "wimble", "factory", "industry", "industrial",
    "manufacturing", "manufacture", "foundry", "machinery"]),
  metbex: teqler(["cooking", "cook", "kitchen", "chef", "recipe", "baking", "bakery", "meal", "cuisine", "dish", "food", "restaurant", "dinner",
    "lunch", "breakfast", "barbecue", "grill", "frying", "salad", "dessert"]),
  tibb: teqler(["surgery", "surgeon", "operating", "doctor", "nurse", "syringe", "injection", "vaccine", "vaccination", "medicine", "medical",
    "clinic", "patient", "pill", "pills", "hospital"]),
  zal: teqler(["fitness", "gym", "workout", "yoga", "exercise", "bodybuilding", "dumbbell", "treadmill", "aerobics", "pilates"]),
  eylence: teqler(["holiday", "vacation", "beach", "tropical", "resort", "party", "celebration", "celebrate", "wedding", "bride", "groom",
    "romantic", "romance", "fireworks", "christmas", "carnival", "cocktail", "picnic", "honeymoon", "sailboat", "yacht", "surfing",
    "sunbathing", "festival", "disco", "nightclub"]),
};
const MOVZU_AD = { is: "iş və sənət", metbex: "mətbəx və yemək", tibb: "tibb", zal: "idman zalı", eylence: "əyləncə və istirahət" };
const FACIE_TEQ = {
  alet: teqler(["knife", "knives", "axe", "hatchet", "cleaver", "crowbar", "hammer", "saw", "chainsaw", "machete", "blade", "sword", "dagger",
    "weapon", "gun", "pistol", "revolver", "rifle", "shotgun", "firearm", "bullet", "ammunition", "cartridge", "rope", "noose", "tool", "drill",
    "wrench", "screwdriver", "pliers", "scissors"]),
  olum: teqler(["blood", "bloody", "bleeding", "corpse", "cadaver", "dead", "death", "deadly", "morgue", "coffin", "casket", "gore", "wound",
    "wounded", "injured", "injury", "murder", "murderer", "killer", "kill", "killing", "victim", "horror", "scary", "creepy", "halloween",
    "zombie", "skull", "skeleton", "body"]),
  insan: teqler(["portrait", "face", "girl", "boy", "woman", "man", "child", "children", "kid", "baby", "teenager", "teen", "couple", "family",
    "selfie", "person", "people"]),
  ehval: new Set([...MOVZU_TEQ.eylence, ...teqler(["happy", "happiness", "smile", "smiling", "laugh", "laughing", "fun", "funny", "joy",
    "joyful", "cheerful", "relax", "relaxing", "relaxation", "peaceful", "love", "sunset"])]),
};
const FACIE_AD = { alet: "silah və ya alət", olum: "qan, meyit, ölüm və ya qorxu", insan: "yaxın planda insan", ehval: "şən və ya istirahət əhvalı" };
// Faciə xəbəridir: hadisə bölməsi və ya başlıqda, diktor mətnində ölüm, qətl, qəza, fəlakət, məhkəmə sözü (profil: kadr.facie).
function facie({ title = "", text = "", category = "" } = {}, D = dil()) {
  if (category === "hadise") return true;
  const s = clean([title, text].filter(Boolean).join(". "));
  return !!(s && D.re.facie && (D.re.facie.test(s) || D.re.facie.test(s.toLocaleLowerCase(D.locale || "az"))));
}
// Klipin (etiketlər) və ya axtarış ifadəsinin mövzusu xəbərə yaddırmı: səbəb (azərbaycanca) və ya "" — uyğundur.
// metn: xəbərin başlığı və diktor mətni (videonun dilində); boşdursa fəaliyyət yoxlanmır (hava videosu: mətn yoxdur, səhnələri koddandır).
// Profildə fəaliyyətin sözü yoxdursa həmin fəaliyyətin klipi götürülmür: xəbərə bağlamaq olmur.
function yadMovzu(tags, { metn = "", facie: F = false } = {}, D = dil()) {
  const have = new Set(words(tags)), tap = set => [...set].filter(w => have.has(w));
  if (F) for (const [k, set] of Object.entries(FACIE_TEQ)) {
    const w = tap(set);
    if (w.length) return `faciə xəbərində ${FACIE_AD[k]} (${w.slice(0, 3).join(", ")})`;
  }
  const s = clean(metn), lc = s.toLocaleLowerCase(D.locale || "az");
  if (!s) return "";
  for (const [k, set] of Object.entries(MOVZU_TEQ)) {
    const w = tap(set), re = D.re.movzu?.[k];
    if (w.length && !(re && (re.test(s) || re.test(lc)))) return `xəbərdə olmayan mövzu: ${MOVZU_AD[k]} (${w.slice(0, 3).join(", ")})`;
  }
  return "";
}

// Uyğunluğa görə (ən uyğun əvvəl), bərabər olanda şaquli əvvəl; uyğun olmayan atılır.
const rank = list => list.filter(x => x.score > 0).sort((a, b) => b.score - a.score || (b.h > b.w) - (a.h > a.w));

// Mənbələr: açarı olan hər biri, sıra ilə. Pexels (2026-11-22: yeni açar verilmir, köhnə açar işləyir) və Pixabay
// (https://pixabay.com/service/license-summary/: pulsuz, kommersiya istifadəsi; API: «nəticənin haradan olduğunu göstərin»).
const MENBELER = [
  { name: "Pexels", env: "PEXELS_API_KEY", async find(q, key, f) {
    for (const orient of ["portrait", "landscape"]) {   // əvvəl şaquli; yoxdursa üfüqi (video modulu tam enində göstərir)
      const j = await getJson(`https://api.pexels.com/videos/search?query=${enc(q)}&orientation=${orient}&size=medium&per_page=15`, { authorization: key }, f);
      // Pexels etiket vermir: təsvir səhifə ünvanındadır (…/video/drone-view-of-baku-123/); ünvan yoxdursa axtarışın sırasına güvənilir.
      const out = rank((j?.videos || []).filter(v => v.duration >= 4).map(v => ({ v, file: bestFile(v, orient === "portrait") })).filter(x => x.file)
        .map(({ v, file }) => ({ id: v.id, user: clean(v.user?.name || ""), link: file.link, w: file.width, h: file.height,
          score: words(slug(v.url)).length ? relevance(q, slug(v.url)) : 1, tags: slug(v.url).replace(/-\d+$/, "").replace(/-/g, ", "),
          thumb: v.image || "" })));
      if (out.length) return out;
    }
    return [];
  } },
  { name: "Pixabay", env: "PIXABAY_API_KEY", async find(q, key, f) {
    const j = await getJson(`https://pixabay.com/api/videos/?key=${enc(key)}&q=${enc(q.slice(0, 100))}&video_type=film&safesearch=true&per_page=20`, {}, f);
    return rank((j?.hits || []).filter(v => v.duration >= 4).map(v => ({ v, file: pixabayFile(v) })).filter(x => x.file)
      .map(({ v, file }) => ({ id: v.id, user: clean(v.user || ""), link: file.url, w: file.width, h: file.height,
        score: relevance(q, `${v.tags || ""} ${slug(v.pageURL)}`), tags: clean(v.tags || ""),
        thumb: v.videos?.tiny?.thumbnail || v.videos?.small?.thumbnail || file.thumbnail || "" })));   // redaktor üçün kadr
  } },
];

// Klipləri <qovluq>/klip-N.mp4-ə yükləyir. Nəticə montaj sırasıdır: [{ file, id, user, q, p (mənbə), w, h }] (bəlkə boş).
// Sıra Gemini-nin ifadələrinin sırasıdır (başlıq, sonra cümlələr; video-xeber.cjs shotPlan kadrları bu sıra ilə götürür), sonra
// eyni ifadələrin ikinci klipləri. Uyğun klip tapılmayan ifadənin yeri ümumi səhnə ilə DOLDURULMUR: yanlış yerin kadrı (2026-11-23:
// Gürcüstan xəbərinin başlığında Bakı) uyğun klipin təkrarından pisdir — montaj klipin başqa hissəsini göstərir. Bölmənin ümumi
// səhnələri yalnız uyğun klip SPARE_MIN-dən azdırsa.
// istifade: son günlərin videolarında işlənmiş kliplər («Pixabay:123») — eyni kadr hər gün təkrarlanmasın (sosial-video.cjs state.klip).
// xeber: { title, text, yer } — varsa namizədləri montaj redaktoru (Gemini, redaktor()) seçir; yoxdursa və ya Gemini cavab vermirsə
// ifadə sırası ilə (hər ifadədən birinci, sonra ikinci…).
const NAMIZED_MAX = 3, SERIYA = 60;
// Öz video arxivi (video-arxiv.cjs, data/video-arxiv.json): yeri kadrlarla yoxlanmış kliplər və sahibin öz görüntüsü. Xəbərin yeri
// məlumdursa əvvəl arxiv, sonra adi axtarış. Yer qaydası (yadYer) arxivə də şamildir. arxiv: kitabxananın klipləri (VA.yukle()),
// hava: arxiv klipinin icazəli havaları (video-hava.cjs arxivSecim) — hava videosunda yalnız sabahkı havada çəkilmiş Bakı klipi.
async function goruntu(axtar, dir, { env = process.env, fetch: f = globalThis.fetch, log = console.log, say = KLIP_SAY, category = "", istifade = new Set(), yer = [], xeber = null, arxiv = [], hava = null } = {}) {
  const menbeler = MENBELER.filter(m => env[m.env]);
  if (!menbeler.length && !(arxiv || []).some(e => e?.menbe === "Sahib")) { log("video: görüntü açarı yoxdur (PEXELS_API_KEY, PIXABAY_API_KEY) — görüntüsüz (köhnə fon)"); return []; }
  // Mövzu (yadMovzu): xəbərin başlığı və diktor mətni; faciə xəbərində əlavə ehtiyat.
  const M = { metn: xeber ? [xeber.title, xeber.text].filter(Boolean).join(". ") : "", facie: facie({ title: xeber?.title, text: xeber?.text, category }) };
  if (M.facie) log("video: faciə xəbəri — silah, alət, qan, meyit, insan və şən kadr götürülmür");
  // Mövzuya yad ifadə banka göndərilmir (faciə xəbərində «metal crowbar tool» — cinayətin aləti).
  const movzulu = q => { const y = yadMovzu(q, M); if (y) log(`video: ifadə ötürüldü — «${q}»: ${y}`); return !y; };
  // Əvvəl xəbərin yerləri (əsl yer görüntüsü başlıq kadrına), sonra Gemini-nin montaj ifadələri.
  const Y = yerPlan(yer), own = [...new Set([...Y.axtar, ...queries(axtar)])].filter(movzulu);
  const spare = ehtiyat({ category, facie: M.facie }).filter(q => !own.includes(q) && yadMovzu(q, M) === "");
  if (Y.axtar.length) log(`video: yer — ${Y.axtar.join("; ")}`);
  const cand = [], seen = new Set(istifade), yadlar = [];
  // 0) Arxiv: xəbərin yerinin yoxlanmış klipləri (əvvəl sahibin öz görüntüsü, sonra dəqiq obyekt, sonra şəhər). Klipin indiki faylı
  // bankdan ID ilə soruşulur (silinibsə ötürülür), sahibinki öz Release-dən.
  const arx = [];
  if (arxiv?.length) {
    const VA = require("./video-arxiv.cjs");
    const menfi = VA.menfi({ category, title: xeber?.title });
    const nm = VA.namizedler(arxiv, { yer: xeber?.yer?.length ? xeber.yer : yer, icaze: Y.icaze, axtar: own, istifade: seen, hava, menfi });
    for (const n of nm) {
      if (arx.length >= VA.ARXIV_NAMIZED) break;
      const c = await VA.hazirla(n.e, { env, fetch: f });
      if (!c) { log(`video: arxiv klipi alınmadı — ${n.e.id} (bankda silinib və ya açar yoxdur)`); continue; }
      seen.add(`${c.p}:${c.id}`);
      const ym = yadMovzu(c.tags || "", M);
      if (ym) { log(`video: arxiv klipi ötürüldü — ${n.e.id}: ${ym}`); continue; }
      arx.push({ m: { name: c.p }, c, q: n.e.obyekt || n.e.yer[0], sira: -1, arxiv: n });
    }
    if (arx.length) log(`video: arxiv — ${arx.map(x => `${x.c.p} ${x.c.id} (${x.arxiv.level}: ${x.q})`).join("; ")}`);
    else if (Y.icaze.size) log("video: arxivdə bu yerin klipi yoxdur — adi axtarış");
  }
  // 1) Namizədlər: hər ifadədən ən uyğun NAMIZED_MAX klip; işlənmiş və yad yerin klipi atılır. Ifadə bir dəfə soruşulur.
  const collect = async (list, per) => {
    for (const q of list) for (const m of menbeler) {
      let k = 0;
      for (const c of await m.find(q, env[m.env], f)) {
        if (k >= per) break;
        const id = `${m.name}:${c.id}`;
        if (seen.has(id)) continue;
        seen.add(id);
        const yad = yadYer(c.tags || "", Y.icaze);
        if (yad) { yadlar.push({ p: m.name, user: c.user, id: Number(c.id) }); log(`video: klip ötürüldü — «${q}» ${m.name} ${c.id}: başqa yer (${yad})`); continue; }
        const ym = yadMovzu(c.tags || "", M);
        if (ym) { log(`video: klip ötürüldü — «${q}» ${m.name} ${c.id}: ${ym}`); continue; }
        cand.push({ m, c, q, sira: k++ });
      }
    }
  };
  await collect(own, NAMIZED_MAX);
  if (cand.length + arx.length < SPARE_MIN) await collect(spare, 2);   // ümumi səhnə yalnız uyğun klip azdırsa (arxiv klipləri də sayılır)
  // Yad yerin klipi ilə eyni çəkilişdən olan klip (eyni müəllif, yaxın nömrə — bir seriya kimi yüklənib): etiketində yer adı
  // olmasa da həmin yeri göstərir (2026-11-23: Batumi stadionu 239973 rədd edildi, eyni seriyadan 239964 keçdi).
  const eyniSeriya = x => yadlar.some(y => y.p === x.m.name && y.user && y.user === x.c.user && Math.abs(y.id - Number(x.c.id)) <= SERIYA);
  for (let i = cand.length - 1; i >= 0; i--) if (eyniSeriya(cand[i])) { log(`video: klip ötürüldü — «${cand[i].q}» ${cand[i].m.name} ${cand[i].c.id}: yad yerin seriyası`); cand.splice(i, 1); }
  // 2) Seçim: montaj redaktoru və ya ifadə sırası. Arxivin dəqiq yer klipi (obyekt; şəhər — mənfi xəbər deyilsə) redaktordan asılı
  // olmadan başlıq kadrıdır (ən çox 2): yeri artıq kadrlarla yoxlanıb. Qalan arxiv klipləri redaktorun siyahısında birincidir.
  const all = [...arx, ...cand];
  const ilk = arx.filter(x => x.arxiv.ilk).slice(0, 2);
  let pick = xeber && env.GEMINI_API_KEY && all.length ? await redaktor(all, xeber, say, { env, fetch: f, log }) : null;
  // Faciə xəbəri: redaktor kadrlara baxmayıbsa (Gemini cavab vermədi, açar yoxdur) klip qoyulmur — yoxlanmamış kadr ölüm xəbərinə düşməsin.
  if (!pick && M.facie && all.length) { log("video: faciə xəbəri — montaj redaktoru kadrlara baxmadı, klip qoyulmur"); pick = []; }
  if (!pick) pick = [...all].sort((a, b) => a.sira - b.sira || all.indexOf(a) - all.indexOf(b)).slice(0, say);
  pick = [...ilk, ...pick.filter(x => !ilk.includes(x))];
  // 3) Yükləmə, seçim sırası ilə.
  const got = [];
  for (const { m, c, q, arxiv: n } of pick) {
    if (got.length >= say) break;
    try {
      const r = await f(c.link, { signal: AbortSignal.timeout(c.maxBytes ? 300000 : 90000) });
      const buf = r?.ok ? Buffer.from(await r.arrayBuffer()) : null;
      if (!buf || buf.length < 10000 || buf.length > (c.maxBytes || KLIP_MAX_BYTES)) continue;
      const name = `klip-${got.length + 1}.mp4`;
      fs.mkdirSync(dir, { recursive: true });
      fs.writeFileSync(path.join(dir, name), buf);
      got.push({ file: name, id: c.id, user: c.user, q, p: m.name, w: c.w, h: c.h, ...(c.kredit ? { kredit: c.kredit } : {}),
        ...(n ? { arxiv: n.e.id, yer: n.e.yer.join(", "), level: n.level } : {}) });
      log(`video: görüntü ${got.length} — ${n ? `ARXİV ${n.level} «${q}» (${n.e.id}; ` : `«${q}» (`}${m.name} ${c.id}, ${c.w}×${c.h}, ${c.user}${c.tags ? `; ${c.tags}` : ""})`);
    } catch {}
  }
  if (!got.length) log(`video: ${menbeler.map(m => m.name).join(", ")}-dən uyğun klip alınmadı`);
  return got;
}

// Montaj redaktoru (2026-11-23): söz uyğunluğu yad şəhəri (siyahıda olmayan «lech poznan»), mənası başqa klipi («empty stadium seats»
// → köhnə divan) buraxırdı. Gemini xəbəri, hər namizədin etiketlərini və bir kadrını (şəkil) görüb montaj sırası ilə seçir; uyğun
// deyilsə az seçir. Yer qaydası kodla da yoxlanır: redaktor hər klipdə gördüyü yeri adlandırır (yerler), xəbərin yeri deyilsə klip
// seçilsə də atılır — ilk canlı videoda (2026-11-23, Bakının tıxacları) redaktor etiketində «kettering» (İngiltərə) olan dairəvi
// yolu seçmişdi; Petrobras məntəqəli (Braziliya) və Asiya yazılı şose kliplərinin isə etiketində yer yox idi, yalnız şəkildə görünürdü.
// Nəticə: seçilmiş namizədlər (bəlkə boş) və ya null — Gemini cavab vermədi, sadə qayda işləsin.
const REDAKTOR = `Sən 8ulduz.az xəbər videosunun montaj redaktorusan. Aşağıda xəbər və video bankında tapılmış kliplər var: nömrə, axtarış
ifadəsi və bankın klipə yazdığı etiketlər; sonra hər klipin bir kadrı şəkil kimi («Klip N»). Videonun kadrları üçün ən çox {n} klip seç,
MONTAJ SIRASI İLƏ: əvvəl xəbərin yerini və ya əsas səhnəsini göstərən, sonra diktor mətninin cümlələrinin sırası ilə.
Əvvəlcə hər klipin yerini (yerler) və kadrda nə göstərildiyini (movzu) müəyyən et, sonra seç (klip).
- movzu: HƏR klip üçün bir sətir. "gosterir" — kadrda nə var (2–5 söz, azərbaycanca: «qazma dəzgahı», «gecə polis maşını»);
  "xeberin_movzusu" — kadr xəbərin mövzusunu və ya xəbərin yerinin ümumi səhnəsini göstərir (true/false). Xəbərdə olmayan iş, sənət
  və fəaliyyət (qazma, qaynaq, dülgərlik, fabrik, mətbəx, idman zalı) — false, axtarış ifadəsinə uyğun olsa da.
- yerler: etiketində və ya şəklində konkret yer görünən HƏR klip üçün bir sətir. Yer: şəhər, ölkə, region, tanınan bina, stadion;
  şəkildə ölkəni göstərən əlamət də sayılır — lövhə və yazının dili (heroqlif, ərəb, kiril…), brend və yanacaq şirkəti, bayraq,
  nömrə nişanı, memarlıq, maşınların yolun hansı tərəfi ilə getməsi (Azərbaycanda sağ tərəf). "yer" — ingiliscə ad (dəqiq yer
  bilinmirsə ölkə: "china", "brazil", "united kingdom"); "xeberin_yeri" — bu yer xəbərin yeridir və ya onun içindədir (true/false).
  Heç bir yer əlaməti olmayan ümumi klipi yazma.
Seçim qaydaları:
- Klip etiketlərinə görə həqiqətən lazım olan səhnəni göstərməlidir. Mənası başqa olan klipi SEÇMƏ (stadion oturacağı əvəzinə divan,
  güllə izi əvəzinə tikinti, futbol əvəzinə uşaq oyunu).
- Yer klipini yalnız etiketləri məhz xəbərin yerini göstərirsə seç: ad eyni olsa da yer başqa ola bilər (Vaşinqton şəhəri xəbərinə
  "washington, oregon, columbia river" — ştatın təbiəti — SEÇMƏ). Şübhə olanda yer klipi əvəzinə mövzu klipini seç.
- Xəbərin yeri olmayan konkret yeri — başqa şəhəri, ölkəni, stadionu, klubu, komandanı, brendi — göstərən klipi SEÇMƏ
  (məsələn Gəncə xəbərinə "lech poznan", "batumi", "barcelona"). Etiketində heç bir yer olmayan ümumi klip olar.
- Klipin əhvalı xəbərə uyğun olmalıdır: partlayış, qəza, müharibə, cinayət, ölüm, fəlakət xəbərində istirahət, turizm, bayram,
  romantika klipini (yelkənli qayıq, çimərlik, gün batımı, "holiday", "peaceful", "tropical") SEÇMƏ.
- Cinayət, qəza, ölüm xəbərində tanınan insan üzü olan klipi seçmə.
- Ölüm, qətl, qəza, fəlakət xəbərində silah və alət (bıçaq, balta, lom, çəkic, mişar, tapança, qazma), qan, meyit, cəsəd, tabut,
  ölüm anı göstərən klipi SEÇMƏ: cinayətin alətini göstərmə, mətndə adı çəkilsə də.
- "xeberin_yeri": false və ya "xeberin_movzusu": false olan klipi SEÇMƏ.
- Uyğun klip azdırsa az seç: yanlış kadr qoymaqdansa klipin təkrarı yaxşıdır. Heç biri uyğun deyilsə boş siyahı.
Yalnız JSON qaytar: {"yerler": [{"klip": nömrə, "yer": "ad", "xeberin_yeri": true}], "movzu": [{"klip": nömrə, "gosterir": "...", "xeberin_movzusu": true}], "klip": [nömrələr]}

Xəbər: {title}
Yer: {yer}
Diktor mətni: {text}
Kliplər:
{list}`;
// Namizədin kadrı (bankın önizləmə şəkli) Gemini üçün: { mime_type, data } və ya null (yoxdur, şəkil deyil, böyükdür).
const SEKIL_MAX = 400000;
async function sekil(url, f) {
  if (!/^https:\/\//.test(url || "")) return null;
  try {
    const r = await f(url, { signal: AbortSignal.timeout(15000) });
    if (!r?.ok) return null;
    const type = String(r.headers?.get?.("content-type") || "").split(";")[0].trim().toLowerCase()
      || ({ jpg: "image/jpeg", jpeg: "image/jpeg", png: "image/png", webp: "image/webp" })[(url.match(/\.(\w+)(?:\?|$)/) || [])[1]?.toLowerCase()] || "";
    if (!/^image\/(jpeg|png|webp)$/.test(type)) return null;
    const buf = Buffer.from(await r.arrayBuffer());
    return buf.length >= 500 && buf.length <= SEKIL_MAX ? { mime_type: type, data: buf.toString("base64") } : null;
  } catch { return null; }
}
// Redaktorun klipdə gördüyü yer xəbərə aiddirmi. Ad xəbərin yerlərindən birini daşıyırsa (və ya əksinə) və ya klipin etiketində
// xəbərin yeri varsa — bəli; ad tanınan yad yerdirsə — xeyr; yoxsa redaktorun öz cavabı (xeberin_yeri).
const BOS_YER = new Set(["unknown", "none", "yoxdur", "naməlum", "ümumi", "generic", "n/a"].map(lat));
function yerUygun(e, tags, x) {
  const ad = lat(e?.yer || "");
  if (ad.length < 3 || BOS_YER.has(ad)) return true;
  const P = yerPlan(x?.yer), bizim = [...new Set([...P.icaze, ...places(x?.yer).map(lat)])].filter(Boolean), t = lat(tags || "");
  if (bizim.some(b => hasName(ad, b) || hasName(b, ad) || hasName(t, b))) return true;
  if (yadYer(ad, P.icaze)) return false;
  return e?.xeberin_yeri !== false;
}
async function redaktor(cand, x, n, { env = process.env, fetch: f = globalThis.fetch, log = console.log } = {}) {
  // Arxiv klipi: yeri kadrlarla yoxlanıb (video-arxiv.cjs) — redaktor bunu bilir, kod onu yer qaydası ilə yenidən atmır.
  const list = cand.map((k, i) => `${i + 1}. ${k.arxiv ? `[ARXİV: yeri yoxlanıb — ${k.arxiv.e.yer.join(", ")}${k.arxiv.e.menbe === "Sahib" ? "; saytın öz görüntüsü" : ""}] ` : ""}«${k.q}» — ${clean(k.c.tags || "etiket yoxdur").slice(0, 160)}`).join("\n");
  const prompt = REDAKTOR.replace("{n}", () => String(n)).replace("{title}", () => clean(x.title)).replace("{yer}", () => places(x.yer).join(", ") || "—")
    .replace("{text}", () => clean(x.text).slice(0, 900)).replace("{list}", () => list);
  const imgs = await Promise.all(cand.map(k => sekil(k.c.thumb, f)));
  const parts = [{ text: prompt }];
  imgs.forEach((img, i) => { if (img) parts.push({ text: `Klip ${i + 1}:` }, { inline_data: img }); });
  let raw = await gemini(parts.length > 1 ? parts : prompt, env.GEMINI_API_KEY, f, log, env);
  if (raw == null && parts.length > 1) { log("video: redaktor şəkilli sorğuya cavab vermədi — yalnız etiketlərlə"); raw = await gemini(prompt, env.GEMINI_API_KEY, f, log, env); }
  if (raw == null) return null;
  let j = null;
  try { j = JSON.parse(String(raw).replace(/^```(?:json)?\s*|\s*```$/g, "")); } catch {}
  if (!Array.isArray(j?.klip)) { log("video: montaj redaktorunun cavabı JSON deyil — sadə qayda"); return null; }
  // Yer qaydası kodla: redaktorun özü seçsə də, xəbərin yeri olmayan yer görünən klip atılır.
  const yad = new Map();
  for (const e of Array.isArray(j.yerler) ? j.yerler : []) {
    const k = Number(e?.klip);
    if (Number.isInteger(k) && k >= 1 && k <= cand.length && !cand[k - 1].arxiv && !yerUygun(e, cand[k - 1].c.tags, x)) yad.set(k, lat(e.yer));
  }
  // Mövzu qaydası kodla (2026-11-27): redaktor klipi «xəbərin mövzusu deyil» adlandırıbsa, seçsə də atılır.
  const yadM = new Map();
  for (const e of Array.isArray(j.movzu) ? j.movzu : []) {
    const k = Number(e?.klip);
    if (Number.isInteger(k) && k >= 1 && k <= cand.length && e?.xeberin_movzusu === false) yadM.set(k, clean(e.gosterir || "").slice(0, 60) || "?");
  }
  const secdi = [...new Set(j.klip.map(Number).filter(k => Number.isInteger(k) && k >= 1 && k <= cand.length))];
  for (const k of secdi) if (yad.has(k)) log(`video: klip ötürüldü — «${cand[k - 1].q}» ${cand[k - 1].m.name} ${cand[k - 1].c.id}: redaktor başqa yer gördü (${yad.get(k)})`);
  for (const k of secdi) if (!yad.has(k) && yadM.has(k)) log(`video: klip ötürüldü — «${cand[k - 1].q}» ${cand[k - 1].m.name} ${cand[k - 1].c.id}: redaktor mövzuya yad gördü (${yadM.get(k)})`);
  const idx = secdi.filter(k => !yad.has(k) && !yadM.has(k)).slice(0, n);
  log(`video: montaj redaktoru ${cand.length} namizəddən (${imgs.filter(Boolean).length} kadr) ${idx.length} klip seçdi`);
  return idx.map(k => cand[k - 1]);
}

// Videoda və post mətnində «Görüntü: …»: əvvəl saytın öz görüntüsünün krediti (sahib), sonra bank (Pixabay, Pexels).
const BANK = ["Pixabay", "Pexels"];
const kredit = klip => [...new Set((klip || []).map(k => clean(k.kredit || k.p)).filter(Boolean))]
  .sort((a, b) => BANK.includes(a) - BANK.includes(b)).join(", ");

module.exports = { ssenari, promptOf, dilLatin, goruntu, kredit, facie, yadMovzu, MOVZU_TEQ, FACIE_TEQ, kenarSozu, UMUMI, OLKELER, SEHERLER, LAQEB, PAYTAXT, hasName, lat, getJson, slug, words, redaktor, REDAKTOR, sekil, yerUygun, roman, protokol, relevance, latin, hashtags, places, yerPlan, yadYer, EHTIYAT, checkText, SERH_MIN, serhAzdir, queries, bestFile, pixabayFile, MENBELER, sourceText, ehtiyat, gemini, PROMPT, TEXT_MIN, TEXT_MAX };
