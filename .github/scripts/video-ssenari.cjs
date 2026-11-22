// Video xəbərin ssenarisi və görüntüsü. Sahib, 2026-11-22: «Videolar tam olaraq biabırçılıqdır. Belə video olmaz. Xəbər uzun
// olsun biraz və videogörüntü olsun o xəbərə uyğun.» Əvvəl video tünd fonda başlıq və bir cümlə idi (~15 s).
//
//   ssenari()  Gemini mənbə səhifəsinin mətnindən 5–7 cümləlik diktor mətni (ən az 4 cümlə, 450–700 simvol, ~35–45 s; sahib: «4-7 cümlədə olsun. uzun da olsun») və video bankı üçün 4–6 ingiliscə
//              axtarış ifadəsi yazır; «uygun: false» — xəbəri ümumi kadrla göstərmək olmur (görüş, qəbul), başqa xəbər seçilir. Mətn yoxlanır: hər rəqəm mənbədə olmalıdır, kiril/keçid/nida yoxdur, saytın qaydasından
//              (policyViolation) keçir. Alınmasa null — video köhnə qayda ilə mənbənin öz cümlələrindən hazırlanır.
//   goruntu()  Pexels və ya Pixabay video bankından (pulsuz lisenziya: kommersiya istifadəsi, dəyişdirmə, sosial şəbəkə —
//              https://www.pexels.com/license/, https://pixabay.com/service/license-summary/) ifadələrə uyğun 4–5 klip yükləyir.
//              2026-11-22: Pexels yeni API açarı vermir, ona görə Pixabay da var (açarı olan mənbə işləyir). Əvvəl şaquli (portrait), yoxdursa üfüqi klip (video modulu onu tam enində ortada göstərir).
//              Pexels lisenziyası tanınan insanı pis işıqda göstərməyi qadağan edir: mənfi xəbərdə (cinayət, qəza, ölüm) ifadələr
//              insansız səhnələrdir (Gemini-yə tapşırıq + kateqoriya ehtiyatı). Videoda «Görüntü: Pixabay» (və ya Pexels) yazılır.
// Açarlar: GEMINI_API_KEY (x_yazici.py ilə eyni), PIXABAY_API_KEY və/və ya PEXELS_API_KEY. Biri yoxdursa həmin hissə ötürülür, video yenə hazırlanır.
// Gemini və Pexels açarı başlıqda gedir; Pixabay yalnız ünvanda qəbul edir — ünvan heç vaxt jurnala yazılmır.
"use strict";
const fs = require("fs"), path = require("path");
const S = require("./social.cjs");

const GEMINI = "https://generativelanguage.googleapis.com/v1beta/models";
const FALLBACK_MODELS = ["gemini-3.6-flash", "gemini-3.5-flash", "gemini-flash-latest"];   // x_yazici.py ilə eyni
const TEXT_MIN = 350, TEXT_MAX = 750, SOURCE_MAX = 5000, SENT_MIN = 4, SENT_MAX = 8;
const KLIP_SAY = 5, KLIP_MAX_BYTES = 60e6;
const wait = ms => new Promise(ok => setTimeout(ok, ms));
const clean = s => String(s ?? "").replace(/<[^>]+>/g, " ").replace(/\s+/g, " ").trim();

// --- Gemini ------------------------------------------------------------------------------------------------------------------
async function models(key, f) {
  try {
    const r = await f(`${GEMINI}?pageSize=200`, { headers: { "x-goog-api-key": key }, signal: AbortSignal.timeout(20000) });
    const j = r?.ok ? await r.json() : {};
    const nums = s => (s.match(/\d+/g) || []).map(Number);
    return (j.models || []).filter(m => (m.supportedGenerationMethods || []).includes("generateContent") && /flash/.test(m.name || "")
      && !/lite|image|tts|audio|live|exp|preview|thinking/.test(m.name)).map(m => m.name.split("/").pop())
      .sort((a, b) => { const x = nums(a), y = nums(b); for (let i = 0; i < Math.max(x.length, y.length); i++) { const d = (y[i] || 0) - (x[i] || 0); if (d) return d; } return 0; });
  } catch { return []; }
}

async function gemini(prompt, key, f, log, env = process.env) {
  const listed = await models(key, f);
  const order = [...new Set([env.GEMINI_MODEL, ...(listed.length ? listed : FALLBACK_MODELS)].filter(Boolean))].slice(0, 3);
  const body = JSON.stringify({ contents: [{ role: "user", parts: [{ text: prompt }] }],
    generationConfig: { temperature: 0.3, maxOutputTokens: 8000, responseMimeType: "application/json" } });
  const tried = [];
  for (const model of order) {
    for (let attempt = 0; attempt < 3; attempt++) {
      let r;
      try {
        r = await f(`${GEMINI}/${model}:generateContent`, { method: "POST", body, signal: AbortSignal.timeout(120000),
          headers: { "x-goog-api-key": key, "content-type": "application/json" } });
      } catch (e) { tried.push(`${model}: ${e?.name || "xəta"}`); break; }
      if (r.status === 429 || r.status >= 500) { tried.push(`${model}: ${r.status}`); await wait(Number(env.VIDEO_GEMINI_WAIT_MS ?? 10000) * (attempt + 1)); continue; }
      if (!r.ok) { tried.push(`${model}: ${r.status}`); break; }
      const j = await r.json().catch(() => ({}));
      const parts = j?.candidates?.[0]?.content?.parts || [];
      log(`video: ssenari modeli ${model}`);
      return parts.filter(p => !p.thought).map(p => p.text || "").join("");
    }
  }
  log(`video: Gemini cavab vermədi (${tried.join(", ") || "model yoxdur"})`);
  return "";
}

// Mənbə səhifəsinin xəbər mətni: abzaslar (social.cjs pageParagraphs), başlığa yaxın yerdən; yoxdursa xülasə + izah.
function sourceText(a, page, fallback = "") {
  const paras = page ? S.pageParagraphs(page) : [];
  const text = clean(paras.join("\n"));
  return (text.length >= 200 ? text : clean([a.summary, fallback].filter(Boolean).join("\n"))).slice(0, SOURCE_MAX);
}

const PROMPT = `Sən 8ulduz.az xəbər saytının video redaktorusan. Aşağıdakı xəbərdən qısa video xəbər (Reels, Shorts) üçün diktor mətni yaz.
Qaydalar:
- Azərbaycan ədəbi dilində, 5–7 aydın cümlə (ən az 4), cəmi 450–700 simvol: xəbərin əsas faktları, təfərrüatları və nəticəsi. Başlığı təkrarlama: başlıq videoda ayrıca oxunur.
- Yalnız aşağıdakı mənbə mətnindəki faktlar. Mətndə olmayan ad, rəqəm, tarix, səbəb, qiymət və ya rəy ƏLAVƏ ETMƏ.
- Rəqəmləri mənbədəki kimi rəqəmlə yaz. Keçid, emoji, nida və sual işarəsi, kiril hərfi yoxdur. «bu gün», «dünən», «sabah» yoxdur.
- Neytral xəbər dili. Ən vacib fakt birinci cümlədə. Şərh və qiymətləndirmə yoxdur.
- Adları inisialsız yaz: «Cey. Di. Vens» yox, «ABŞ vitse-prezidenti Vens»; «İ. Əliyev» yox, «İlham Əliyev».
Videonun fonu üçün 4–6 ingiliscə axtarış ifadəsi də yaz (Pixabay video bankı, 2–4 söz): xəbərin məkanını, mövzusunu, əşyalarını
göstərən konkret səhnələr, məsələn "Baku city skyline", "Hanoi street traffic", "cargo ship port", "oil pump jack", "snow mountain road".
Yer adı varsa onu yaz ("Istanbul Bosphorus", "Baku boulevard"). Bayraq yalnız ölkə adı ilə ("Azerbaijan flag"), "national flags" yox.
İnsanların xəbərdəki hərəkətini (görüş, əl sıxma, imza, çıxış) göstərən səhnə yazma: tamaşaçı onları xəbərin qəhrəmanı sanar.
Konkret tanınan insanların adını yazma. Xəbər cinayət, qəza, ölüm, xəstəlik, fəlakət, məhkəmə və ya münaqişə haqqındadırsa, yalnız
insansız səhnələr seç (bina, yol, polis maşınının işıqları, şəhər, təbiət, texnika).
"uygun": video bankının ümumi kadrları bu xəbəri yanıltmadan göstərə bilərmi? Xəbərin mahiyyəti konkret adamların görüşü, qəbulu,
telefon danışığı, bəyanatı, təbriki, müsahibəsi, təyinatı və ya məktubudursa — false (kadr həmin adamları göstərirmiş kimi görünər).
Hadisə, qəza, hava, təbiət, iqtisadiyyat, qiymət, nəqliyyat, tikinti, texnologiya, elm, idman, şəhər həyatı, müharibənin gedişi — true.
Yalnız JSON qaytar, başqa heç nə: {"uygun": true, "text": "<diktor mətni>", "axtar": ["...", "..."]}

Başlıq: {title}
Bölmə: {bolme}
Mənbə mətni:
{source}`;

// Diktor mətninin yoxlanması. Səbəb (sətir) və ya "" — keçdi.
const NUM = /\d+(?:[.,]\d+)*/g;
const normNum = s => s.replace(/[.,](?=\d{3}\b)/g, "").replace(",", ".");
function checkText(text, source, a, policy = () => false) {
  if (text.length < TEXT_MIN || text.length > TEXT_MAX) return `uzunluq ${text.length} (${TEXT_MIN}–${TEXT_MAX})`;
  // «Cey. Di. Vens»: altyazı hər nöqtədə bölünür, «Di.» ekranda tək qalır (2026-11-22 nümunə videosu).
  if (/(?:^|[\s(])\p{Lu}\p{Ll}{0,2}\.\s+\p{Lu}\p{Ll}{0,2}\./u.test(text)) return "inisial";
  const sent = text.split(/(?<=[.!?…])\s+(?=[\p{Lu}\d«"])/u).filter(Boolean).length;
  if (sent < SENT_MIN || sent > SENT_MAX) return `cümlə sayı ${sent} (${SENT_MIN}–${SENT_MAX})`;
  if (/[Ѐ-ӿ]/.test(text)) return "kiril hərfi";
  if (/https?:|www\.|[!?]/.test(text)) return "keçid, nida və ya sual";
  if (/\b(bu gün|dünən|sabah)\b/i.test(text)) return "nisbi gün sözü";
  if (!/[əğışçöüƏĞŞÇÖÜİ]/.test(text)) return "Azərbaycan dilində deyil";
  const have = new Set((source.match(NUM) || []).map(normNum));
  const extra = (text.match(NUM) || []).map(normNum).filter(n => !have.has(n));
  if (extra.length) return `mənbədə olmayan rəqəm: ${extra.slice(0, 3).join(", ")}`;
  if (policy({ ...a, summary: text })) return "saytın qaydasından keçmir";
  return "";
}

// Axtarış ifadələri: yalnız latın hərfi, 2–5 söz, ən çox 6, təkrarsız.
function queries(list) {
  const out = [];
  for (const q of Array.isArray(list) ? list : []) {
    const s = clean(q).replace(/[^A-Za-z \-']/g, " ").replace(/\s+/g, " ").trim().toLowerCase();
    const n = s.split(" ").length;
    if (s.length >= 3 && s.length <= 60 && n <= 5 && !out.includes(s)) out.push(s);
  }
  return out.slice(0, 6);
}
// Gemini olmayanda bölməyə görə ümumi səhnələr (insansız; Pexels-də çox klip olanlar).
const EHTIYAT = {
  siyaset: ["baku city skyline", "azerbaijan flag", "government building", "baku boulevard"],
  prezident: ["baku city skyline", "azerbaijan flag", "government building", "baku boulevard"],
  iqtisadiyyat: ["business district skyline", "cargo ship port", "stock market screen", "factory production line"],
  idman: ["football stadium", "sports stadium lights", "running track", "football ball grass"],
  dunya: ["world globe", "city skyline night", "airport airplane", "world map"],
  texnologiya: ["technology circuit", "data center servers", "smartphone screen", "code on screen"],
  elm: ["science laboratory", "microscope laboratory", "space stars", "technology circuit"],
  hadise: ["police car lights night", "city street night", "emergency lights", "road traffic night"],
  cemiyyet: ["baku city street", "city street people walking", "school building", "hospital corridor"],
  medeniyyet: ["theater stage lights", "museum hall", "old city architecture", "concert stage lights"],
};
const ehtiyat = a => EHTIYAT[a.category] || ["baku city skyline", "city street traffic", "baku boulevard", "city skyline night"];

// Protokol xəbəri (görüş, qəbul, telefon danışığı, təbrik, başsağlığı): ümumi kadr həmin adamları göstərirmiş kimi görünər —
// belə xəbərdən video hazırlanmır (2026-11-22 nümunə videosu: Prezidentin qəbulu, fonda yad əl sıxma və göy). Gemini də yoxlayır («uygun»).
const PROTOKOL = /(qəbul edib|qəbul etdi|görüşüb|görüşdü|görüşəcək|telefon danışığı|telefonla danışıb|təbrik edib|təbrik məktubu|təbrik etdi|başsağlığı|məktub ünvanlayıb|danışıqlar aparıb)/iu;
const protokol = a => a?.category === "prezident" || PROTOKOL.test(clean(a?.title));

// Ssenari: { text, axtar, model: "gemini" } və ya null.
async function ssenari(a, page, { env = process.env, fetch: f = globalThis.fetch, policy = () => false, log = console.log, fallback = "" } = {}) {
  const key = env.GEMINI_API_KEY;
  if (!key) { log("video: GEMINI_API_KEY yoxdur — ssenari mənbənin öz cümlələrindən"); return null; }
  const source = sourceText(a, page, fallback);
  if (source.length < 120) { log("video: mənbə mətni qısadır — ssenari yazılmır"); return null; }
  const prompt = PROMPT.replace("{title}", clean(a.title)).replace("{bolme}", clean(a.bolme || a.category || "")).replace("{source}", source);
  const raw = await gemini(prompt, key, f, log, env);
  let j = null;
  try { j = JSON.parse(String(raw).replace(/^```(?:json)?\s*|\s*```$/g, "")); } catch {}
  if (j?.uygun === false) { log("video: Gemini — xəbəri ümumi kadrla yanıltmadan göstərmək olmur (görüş, qəbul, bəyanat), başqa xəbər"); return { uygun: false, text: "", axtar: [] }; }
  const text = clean(j?.text);
  const why = text ? checkText(text, `${source}\n${clean(a.title)}`, a, policy) : "cavab boşdur və ya JSON deyil";
  if (why) { log(`video: Gemini mətni qəbul olunmadı (${why}) — mənbənin öz cümlələri`); return null; }
  return { text, axtar: queries(j?.axtar), uygun: j?.uygun !== false };
}

// --- Görüntü: Pexels və Pixabay ------------------------------------------------------------------------------------------------------------------
// Klipin ən uyğun faylı: şaquli klipdə hündürlüyü 1920-yə ən yaxın (≥1280), üfüqidə hündürlüyü ≥1080 olan ən kiçiyi.
function bestFile(v, portrait) {
  const files = (v?.video_files || []).filter(x => x?.link && /mp4/.test(x.file_type || "") && x.width > 0 && x.height > 0);
  const ok = portrait ? files.filter(x => x.height > x.width && x.height >= 1280) : files.filter(x => x.width >= x.height && x.height >= 1080);
  ok.sort((x, y) => Math.abs(x.height - (portrait ? 1920 : 1080)) - Math.abs(y.height - (portrait ? 1920 : 1080)) || x.width - y.width);
  return ok[0] || null;
}

const enc = encodeURIComponent;
async function getJson(u, headers, f) {
  try {
    const r = await f(u, { headers, signal: AbortSignal.timeout(20000) });
    return r?.ok ? await r.json() : null;
  } catch { return null; }   // ünvan jurnala yazılmır: Pixabay açarı ünvandadır
}
// Pixabay faylı: hər iki ölçüsü ən azı 1080 olan ilk nüsxə (medium adətən 1920×1080, large 3840×2160), ≤ KLIP_MAX_BYTES.
function pixabayFile(v) {
  const s = v?.videos || {};
  return [s.medium, s.large, s.small].find(x => x?.url && x.width > 0 && x.height > 0 && Math.min(x.width, x.height) >= 1080
    && !(x.size > KLIP_MAX_BYTES)) || null;
}
// Mənbələr: açarı olan hər biri, sıra ilə. Pexels (2026-11-22: yeni açar verilmir, köhnə açar işləyir) və Pixabay
// (https://pixabay.com/service/license-summary/: pulsuz, kommersiya istifadəsi; API: «nəticənin haradan olduğunu göstərin»).
const MENBELER = [
  { name: "Pexels", env: "PEXELS_API_KEY", async find(q, key, f) {
    for (const orient of ["portrait", "landscape"]) {   // əvvəl şaquli; yoxdursa üfüqi (ortadan 9:16 kəsilir)
      const j = await getJson(`https://api.pexels.com/videos/search?query=${enc(q)}&orientation=${orient}&size=medium&per_page=15`, { authorization: key }, f);
      const out = (j?.videos || []).filter(v => v.duration >= 4).map(v => ({ v, file: bestFile(v, orient === "portrait") })).filter(x => x.file)
        .map(({ v, file }) => ({ id: v.id, user: clean(v.user?.name || ""), link: file.link, w: file.width, h: file.height }));
      if (out.length) return out;
    }
    return [];
  } },
  { name: "Pixabay", env: "PIXABAY_API_KEY", async find(q, key, f) {
    const j = await getJson(`https://pixabay.com/api/videos/?key=${enc(key)}&q=${enc(q.slice(0, 100))}&video_type=film&safesearch=true&per_page=20`, {}, f);
    return (j?.hits || []).filter(v => v.duration >= 4).map(v => ({ v, file: pixabayFile(v) })).filter(x => x.file)
      .map(({ v, file }) => ({ id: v.id, user: clean(v.user || ""), link: file.url, w: file.width, h: file.height }))
      .sort((a, b) => (b.h > b.w) - (a.h > a.w));   // şaquli klip əvvəl
  } },
];

// Klipləri <qovluq>/klip-N.mp4-ə yükləyir. Nəticə: [{ file, id, user, q, p (mənbə), w, h }] (bəlkə boş).
async function goruntu(axtar, dir, { env = process.env, fetch: f = globalThis.fetch, log = console.log, say = KLIP_SAY, category = "" } = {}) {
  const menbeler = MENBELER.filter(m => env[m.env]);
  if (!menbeler.length) { log("video: görüntü açarı yoxdur (PEXELS_API_KEY, PIXABAY_API_KEY) — görüntüsüz (köhnə fon)"); return []; }
  const list = [...queries(axtar), ...ehtiyat({ category })].filter((q, i, all) => all.indexOf(q) === i);
  const got = [], seen = new Set();
  for (const pass of [1, 2]) {   // birinci keçid: hər ifadədən bir klip; ikinci: çatmırsa ikinci klip
    for (const q of list) {
      if (got.length >= say) break;
      for (const m of menbeler) {
        const c = (await m.find(q, env[m.env], f)).find(x => !seen.has(`${m.name}:${x.id}`));
        if (!c) continue;
        seen.add(`${m.name}:${c.id}`);
        try {
          const r = await f(c.link, { signal: AbortSignal.timeout(90000) });
          const buf = r?.ok ? Buffer.from(await r.arrayBuffer()) : null;
          if (!buf || buf.length < 10000 || buf.length > KLIP_MAX_BYTES) continue;
          const name = `klip-${got.length + 1}.mp4`;
          fs.mkdirSync(dir, { recursive: true });
          fs.writeFileSync(path.join(dir, name), buf);
          got.push({ file: name, id: c.id, user: c.user, q, p: m.name, w: c.w, h: c.h });
          log(`video: görüntü ${got.length} — «${q}» (${m.name} ${c.id}, ${c.w}×${c.h}, ${c.user})`);
          break;
        } catch {}
      }
    }
    if (got.length >= say || pass === 2 && got.length) break;
  }
  if (!got.length) log(`video: ${menbeler.map(m => m.name).join(", ")}-dən klip alınmadı — görüntüsüz (köhnə fon)`);
  return got;
}

module.exports = { ssenari, goruntu, protokol, EHTIYAT, checkText, queries, bestFile, pixabayFile, MENBELER, sourceText, ehtiyat, gemini, PROMPT, TEXT_MIN, TEXT_MAX };
