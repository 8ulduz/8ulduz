// Gündəlik hava videosu (sahib, 2026-11-23: «öz gündəlik hava videomuzu ən peşəkar səviyyədə qur»). Hər axşam sabahkı proqnoz:
// Bakı (temperatur, külək, yağıntı), 8 bölgə şəhəri kartlarda, xəbərdarlıq dəyərində hallar (güclü külək, şaxta, istilik, qar, leysan,
// ildırım). Video xəbər videosu ilə eyni brenddir (video-xeber.cjs: loqo zolağı, SARA səsi, sözbəsöz altyazı, kodlaşdırma) və eyni
// axınla Facebook/Instagram Reels, YouTube Shorts, TikTok-a gedir (sosial-video.cjs, sosial-video.yml). Sənəd: docs/sosial-video.md
// «Hava videosu».
//
// Dəqiqlik (qırmızı xətt): mətn və rəqəmlər BİRBAŞA Open-Meteo məlumatından, deterministik şablonla qurulur. Gemini mətnə toxunmur
// (görüntü seçimində montaj redaktoru kimi iştirak edə bilər, rəqəmə yox). yoxla() hər rəqəmi məlumatla yenidən tutuşdurur:
// mətndə məlumatda olmayan və ya başqa şəhərin rəqəmi varsa video olmur. Yuvarlaqlaşdırma saytın hava səhifələri ilə eynidir
// (updater.py round: yarımda cüt tərəfə), vahidlər də (m/san, °C, mm, sm).
// Şəhər siyahısı və koordinatlar saytın özündəndir (assets/app.js CITIES; updater.py-nin hava səhifələri ilə eyni, testlə qorunur).
// Xəbərdarlıq hədləri oz_hava.py ilə eynidir (tests/video-hava.test.cjs yoxlayır). Bu, model proqnozudur, rəsmi xəbərdarlıq deyil:
// videoda və mətndə belə yazılır (saytın hava səhifəsi kimi).
//
// Hüquq: hava məlumatı Open-Meteo (CC BY 4.0: «Open-Meteo.com» kreditlə, lisenziyaya keçid; pulsuz API qeyri-kommersiya istifadə üçündür
// — OPEN_METEO_API_KEY verilsə ödənişli ünvan işləyir), görüntü yalnız Pixabay/Pexels pulsuz lisenziyası ilə (video-ssenari.cjs goruntu),
// videoda və mətndə «Hava: Open-Meteo», «Görüntü: Pixabay». Xəbər saytlarının, TV-nin və X-in görüntüsü yoxdur.
//
// İşlədilmə:  node .github/scripts/video-hava.cjs <giriş.json> <çıxış.mp4>
//   giriş — sosial-video.cjs-in yazdığı plan (tur: "hava", plan(): mətn, kartlar, xəbərdarlıqlar) + istəyə bağlı klipler/goruntuMenbe
//   çıxış — video-xeber.cjs ilə eyni müqavilə: <çıxış>.mp4 (comment=8ulduz.az), <çıxış>.json (id, own: true, kind: "hava", url, title,
//           summary, text, …), <çıxış>.jpg (örtük kadrı).
"use strict";
const fs = require("fs"), path = require("path"), os = require("os");
const V = require("./video-xeber.cjs");

const ROOT = path.resolve(__dirname, "../..");
const OM = "https://api.open-meteo.com/v1/forecast", OM_PAID = "https://customer-api.open-meteo.com/v1/forecast";
const OM_SITE = "https://open-meteo.com/";
// Keçid birbaşa sayta: www.8ulduz.az paylaşma serveridir (Worker), xəbər nömrəsi olmayan yolu ana səhifəyə yönləndirir (docs/x-worker.md).
const LINK = "https://8ulduz.az/bolme/hava/";
// Bakı + 8 bölgə (oz_hava.py-nin şəhərləri + Mingəçevir): Abşeron, qərb, mərkəz, şimal-qərb, şimal, cənub, Naxçıvan, Qarabağ.
const SEHERLER = ["Bakı", "Sumqayıt", "Gəncə", "Mingəçevir", "Şəki", "Quba", "Lənkəran", "Naxçıvan", "Şuşa"];
// Open-Meteo gündəlik sahələri və gözlənilən vahidləri: vahid başqadırsa (km/s, °F) məlumat qəbul olunmur.
const DAILY = { weather_code: "wmo code", temperature_2m_max: "°C", temperature_2m_min: "°C", precipitation_sum: "mm",
  precipitation_probability_max: "%", snowfall_sum: "cm", wind_speed_10m_max: "m/s", wind_gusts_10m_max: "m/s", wind_direction_10m_dominant: "°" };
const LIMITS = { weather_code: [0, 99], temperature_2m_max: [-60, 60], temperature_2m_min: [-60, 60], precipitation_sum: [0, 500],
  precipitation_probability_max: [0, 100], snowfall_sum: [0, 500], wind_speed_10m_max: [0, 100], wind_gusts_10m_max: [0, 100], wind_direction_10m_dominant: [0, 360] };
const REQUIRED = new Set(["weather_code", "temperature_2m_max", "temperature_2m_min"]);
// Xəbərdarlıq hədləri — oz_hava.py «Təhlükəli hava həddi» ilə eyni (GUST, FROST, FROST_BAKU, HEAT, SNOW, SNOW_LOW, MOUNTAIN); leysan saytın
// hava zolağı ilə eyni (app.js loadWarnings: yağıntı ≥ 20 mm).
const GUST = 20, FROST = -10, FROST_BAKU = -5, HEAT = 38, SNOW = 10, SNOW_LOW = 5, RAIN_HEAVY = 20;
const MOUNTAIN = ["Şəki", "Quba", "Naxçıvan", "Şuşa"];
const MONTHS = ["yanvar", "fevral", "mart", "aprel", "may", "iyun", "iyul", "avqust", "sentyabr", "oktyabr", "noyabr", "dekabr"];
const WEEKDAYS = ["bazar", "bazar ertəsi", "çərşənbə axşamı", "çərşənbə", "cümə axşamı", "cümə", "şənbə"];   // getUTCDay
const clean = V.clean;

// --- Məlumat ---------------------------------------------------------------------------------------------------------------
// Saytın şəhər siyahısından (app.js CITIES) adı verilən şəhərlər: { name, lat, lon }. Siyahıda olmayan ad — xəta (koordinat təkrar yazılmır).
function cities(app, names = SEHERLER) {
  const all = new Map((app?.CITIES || []).map(c => [String(c[0]), [Number(c[1]), Number(c[2])]]));
  return names.map(name => {
    const c = all.get(name);
    if (!c || !c.every(Number.isFinite)) throw new Error(`hava: «${name}» saytın şəhər siyahısında (app.js CITIES) yoxdur`);
    return { name, lat: c[0], lon: c[1] };
  });
}
function url(list, key = "") {
  return `${key ? OM_PAID : OM}?latitude=${list.map(c => c.lat).join(",")}&longitude=${list.map(c => c.lon).join(",")}`
    + `&daily=${Object.keys(DAILY).join(",")}&wind_speed_unit=ms&timezone=Asia%2FBaku&forecast_days=3${key ? `&apikey=${encodeURIComponent(key)}` : ""}`;
}
// Bir sorğu, ən çox 3 cəhd. Ünvan jurnala yazılmır (ödənişli açar ünvandadır).
async function fetchData(list, { fetch: f = globalThis.fetch, env = process.env, wait = 5000 } = {}) {
  let last = "";
  for (let i = 0; i < 3; i++) {
    try {
      const r = await f(url(list, env.OPEN_METEO_API_KEY || ""), { signal: AbortSignal.timeout(20000) });
      if (r?.ok) return await r.json();
      last = `HTTP ${r?.status}`;
      if (r?.status && r.status < 500 && r.status !== 429) break;
    } catch (e) { last = `${e?.name || "xəta"}${e?.cause?.code ? ` ${e.cause.code}` : ""}`; }   // «TypeError ECONNRESET»: səbəb jurnalda görünsün
    if (i < 2) await new Promise(ok => setTimeout(ok, wait * 3 * (i + 1)));   // 15 s, 30 s
  }
  throw new Error(`Open-Meteo cavab vermədi (${last})`);
}

// Open-Meteo cavabı → günün sətirləri [{ name, code, tmax, tmin, precip, prob, snow, wind, gust, dir }] (xam ədədlər, şəhərlərin sırası ilə).
// Hər şəhər yoxlanır: saat qurşağı, koordinat (model xanası 0,3°-dən uzaq deyil), vahidlər, gün, hədlər, tmax ≥ tmin. Yoxlamadan keçməyən
// şəhər atılır (səbəb why-da); Bakı keçməsə — xəta (video olmur).
function parse(raw, list, day) {
  let data = typeof raw === "string" ? JSON.parse(raw) : raw;
  if (data && !Array.isArray(data)) data = [data];
  if (!Array.isArray(data) || data.length !== list.length) throw new Error(`Open-Meteo: ${list.length} nöqtə gözlənilirdi, ${Array.isArray(data) ? data.length : 0} gəldi`);
  const rows = [], why = [];
  data.forEach((o, i) => {
    const c = list[i], bad = s => why.push(`${c.name}: ${s}`);
    if (o?.timezone !== "Asia/Baku") return bad("saat qurşağı Asia/Baku deyil");
    if (!(Math.hypot(Number(o.latitude) - c.lat, Number(o.longitude) - c.lon) <= 0.3)) return bad("koordinat uyğun deyil");
    const units = o.daily_units || {}, d = o.daily || {};
    const wrong = Object.keys(DAILY).find(k => units[k] !== DAILY[k]);
    if (wrong) return bad(`vahid: ${wrong} ${units[wrong] ?? "yoxdur"}`);
    const idx = Array.isArray(d.time) ? d.time.indexOf(day) : -1;
    if (idx < 0) return bad(`${day} günü yoxdur`);
    const v = {};
    for (const k of Object.keys(DAILY)) {
      const x = Array.isArray(d[k]) ? d[k][idx] : undefined;
      if (x == null) { if (REQUIRED.has(k)) return bad(`${k} yoxdur`); v[k] = null; continue; }
      const n = Number(x), [lo, hi] = LIMITS[k];
      if (typeof x === "boolean" || !Number.isFinite(n) || n < lo || n > hi) return bad(`${k} = ${x}`);
      v[k] = n;
    }
    if (v.temperature_2m_max < v.temperature_2m_min) return bad("maksimum minimumdan aşağıdır");
    rows.push({ name: c.name, code: Math.round(v.weather_code), tmax: v.temperature_2m_max, tmin: v.temperature_2m_min, precip: v.precipitation_sum,
      prob: v.precipitation_probability_max, snow: v.snowfall_sum, wind: v.wind_speed_10m_max, gust: v.wind_gusts_10m_max, dir: v.wind_direction_10m_dominant });
  });
  if (!rows.length || rows[0].name !== list[0].name) throw new Error(`Open-Meteo: ${list[0].name} məlumatı yoxlamadan keçmədi (${why.join("; ")})`);
  return { rows, why };
}

// --- Rəqəmlər ---------------------------------------------------------------------------------------------------------------
// Python round() kimi (yarımda cüt tərəfə: 14,5 → 14, 15,5 → 16): saytın hava səhifələri (updater.py) eyni rəqəmi göstərsin.
function rnd(x) {
  const f = Math.floor(x), d = x - f;
  const r = Math.abs(d - 0.5) < 1e-9 ? (f % 2 === 0 ? f : f + 1) : Math.round(x);
  return r === 0 ? 0 : r;   // −0 yox
}
const r1 = x => Math.round(x * 10) / 10;
// Ekranda: «+17°», «−3°», «0°». Mənfi işarə tipoqrafik minusdur.
const deg = t => `${t > 0 ? "+" : t < 0 ? "−" : ""}${Math.abs(t)}°`;
// Yağıntı: 10 mm-dən az — onda bir dəqiqliklə (3,4), yoxsa tam ədəd. Vergüllə (Azərbaycan yazısı).
const mmText = x => (x >= 10 ? String(rnd(x)) : String(r1(x)).replace(".", ","));
// Sabahkı günün sabit rəqəmləri: mətn, kartlar və yoxlama yalnız bunlardan istifadə edir.
function nums(r) {
  return { tmax: rnd(r.tmax), tmin: rnd(r.tmin), wind: r.wind == null ? null : rnd(r.wind), gust: r.gust == null ? null : rnd(r.gust),
    precip: r.precip == null ? null : mmText(r.precip), snow: r.snow == null ? null : rnd(r.snow), prob: r.prob == null ? null : rnd(r.prob) };
}

// --- Hava növü (WMO kodu) ---------------------------------------------------------------------------------------------------
function kind(c) {
  if (c === 0) return "acik";
  if (c === 1) return "esasen";
  if (c === 2) return "qismen";
  if (c === 3) return "bulud";
  if (c === 45 || c === 48) return "duman";
  if (c >= 51 && c <= 55) return "ciskin";
  if ([56, 57, 66, 67].includes(c)) return "dondurucu";
  if (c >= 61 && c <= 65) return c === 65 ? "gucluyagis" : "yagis";
  if (c === 80 || c === 81) return "arabir";
  if (c === 82) return "leysan";
  if (c >= 71 && c <= 77) return c === 75 ? "gucluqar" : "qar";
  if (c === 85 || c === 86) return "arabirqar";
  if (c >= 95) return c === 95 ? "ildirim" : "dolu";
  return "deyisken";
}
const YAGINTI = new Set(["ciskin", "dondurucu", "yagis", "arabir", "gucluyagis", "leysan", "qar", "arabirqar", "gucluqar", "ildirim", "dolu"]);
const QAR = new Set(["qar", "arabirqar", "gucluqar"]);
// Başlıqdakı ifadə («Sabah Bakıda buludlu hava») və Bakı cümləsi («Bakıda hava buludlu olacaq»).
const IFADE = { acik: "açıq hava", esasen: "əsasən açıq hava", qismen: "qismən buludlu hava", bulud: "buludlu hava", duman: "dumanlı hava",
  ciskin: "çiskin", dondurucu: "dondurucu yağış", yagis: "yağış", arabir: "arabir yağış", gucluyagis: "güclü yağış", leysan: "leysan", qar: "qar",
  arabirqar: "arabir qar", gucluqar: "güclü qar", ildirim: "ildırım", dolu: "ildırım və dolu", deyisken: "dəyişkən hava" };
const CUMLE = { acik: "hava açıq olacaq", esasen: "hava əsasən açıq olacaq", qismen: "hava qismən buludlu olacaq", bulud: "hava buludlu olacaq",
  duman: "duman olacaq", ciskin: "çiskin yağacaq", dondurucu: "dondurucu yağış yağacaq", yagis: "yağış yağacaq", arabir: "arabir yağış yağacaq",
  gucluyagis: "güclü yağış yağacaq", leysan: "leysan yağacaq", qar: "qar yağacaq", arabirqar: "arabir qar yağacaq", gucluqar: "güclü qar yağacaq",
  ildirim: "ildırım çaxacaq, yağış yağacaq", dolu: "ildırım çaxacaq, dolu düşə bilər", deyisken: "hava dəyişkən olacaq" };
// Ehtimal azdırsa (50%-dən az) «yağacaq» yox, «yağa bilər».
const ehtimal = (s, prob) => (prob != null && prob < 50 ? s.replace(/yağacaq/g, "yağa bilər").replace(/çaxacaq/g, "çaxa bilər") : s);

// --- Dil ------------------------------------------------------------------------------------------------------------------
// «Bakıda», «Gəncədə», «Sumqayıtda»: şəkilçi son saitə görə (updater.py _locative ilə eyni).
function loc(name) {
  for (const ch of [...String(name).toLocaleLowerCase("az")].reverse()) {
    if ("aıou".includes(ch)) return `${name}da`;
    if ("eəiöü".includes(ch)) return `${name}də`;
  }
  return `${name}da`;
}
const birlesdir = list => (list.length < 2 ? list.join("") : `${list.slice(0, -1).join(", ")} və ${list[list.length - 1]}`);
const boyuk = s => s.charAt(0).toLocaleUpperCase("az") + s.slice(1);
// Səs mənfi işarəni oxumur (az_text): mənfi temperatur Azərbaycan proqnoz dilində «N dərəcə şaxta»dır, müsbət «N dərəcə isti».
const dereceSoz = t => (t < 0 ? `${-t} dərəcə şaxta` : t > 0 ? `${t} dərəcə isti` : "0 dərəcə");
function geceGunduz(n, x) {
  if (n > 0 && x > 0) return `Gecə ${n}, gündüz ${x} dərəcə isti olacaq`;
  if (n < 0 && x < 0) return `Gecə ${-n}, gündüz ${-x} dərəcə şaxta olacaq`;
  return `Gecə ${dereceSoz(n)}, gündüz ${dereceSoz(x)} olacaq`;
}
// [[«Gəncədə», 16], …] → «Gəncədə 16, Şəkidə 17 dərəcə isti, Şuşada 2 dərəcə şaxta»: vahid işarə dəyişəndə və sonda deyilir.
function siyahi(items) {
  return items.map(([l, t], i) => {
    const s = Math.sign(t), next = items[i + 1], same = next && Math.sign(next[1]) === s && s !== 0;
    return `${l} ${Math.abs(t)}${same ? "" : s > 0 ? " dərəcə isti" : s < 0 ? " dərəcə şaxta" : " dərəcə"}`;
  }).join(", ");
}
const YON = ["Şimal", "Şimal-şərq", "Şərq", "Cənub-şərq", "Cənub", "Cənub-qərb", "Qərb", "Şimal-qərb"];
const sector = d => Math.round(((d % 360) + 360) % 360 / 45) % 8;
// Bakı küləyinin xalq adı: şimal küləyi — xəzri, cənub küləyi — gilavar (yalnız bu iki istiqamətdə).
function kulekCumle(n, r, baki) {
  if (n.wind == null) return "";
  if (n.wind < 4) return "Külək zəif olacaq.";
  const s = r.dir == null ? -1 : sector(r.dir);
  const ad = s < 0 ? "Külək" : `${YON[s]} küləyi${baki && s === 0 ? " (xəzri)" : baki && s === 4 ? " (gilavar)" : ""}`;
  const g = n.gust != null && n.gust >= n.wind + 3 ? `, ani küləklərdə ${n.gust} metrə` : "";
  return `${ad} əsəcək, sürəti saniyədə ${n.wind} metrə${g} çatacaq.`;
}
function yagintiCumle(n, r) {
  if (r.snow != null && n.snow >= 1) return `${n.snow} santimetr qar yağacaq.`;
  if (r.precip != null && r.precip >= 0.1) return `Yağıntının miqdarı ${n.precip} millimetr olacaq.`;
  return "";
}
// Şəhərdə yağıntı varmı (bölgə cümləsi): ehtimal ≥ 50% (bilinmirsə sayılır) və ≥ 1 mm və ya ≥ 1 sm qar.
const yagir = r => (r.prob == null || r.prob >= 50) && ((r.precip ?? 0) >= 1 || (r.snow ?? 0) >= 1);
const qarir = r => (r.snow ?? 0) >= 1 || QAR.has(kind(r.code));

// Xəbərdarlıqlar: xam ədədlə hədd (oz_hava.py kimi), ekranda və səsdə yuvarlaq ədəd. Növ sırası: külək, leysan, qar, şaxta, isti, ildırım.
const XEB = [
  { k: "kulek", hit: r => r.gust != null && r.gust >= GUST, v: n => n.gust, sort: -1, label: "Ani külək", unit: " m/san",
    say: it => `ani küləklərin sürəti ${it.map(([l, v], i) => `${l} ${i ? "" : "saniyədə "}${v}`).join(", ")} metrə çatacaq` },
  { k: "leysan", hit: r => r.precip != null && r.precip >= RAIN_HEAVY && !qarir(r), v: n => n.precip, sort: -1, label: "Güclü yağış", unit: " mm",
    say: it => `${it.map(([l, v]) => `${l} ${v}`).join(", ")} millimetr yağıntı gözlənilir` },
  { k: "qar", hit: r => r.snow != null && r.snow >= (MOUNTAIN.includes(r.name) ? SNOW : SNOW_LOW), v: n => n.snow, sort: -1, label: "Qar", unit: " sm",
    say: it => `${it.map(([l, v]) => `${l} ${v}`).join(", ")} santimetr qar yağacaq` },
  { k: "saxta", hit: r => r.tmin <= (r.name === "Bakı" ? FROST_BAKU : FROST), v: n => n.tmin, sort: 1, label: "Şaxta", fmt: deg,
    say: it => `gecə ${it.map(([l, v]) => `${l} ${-v}`).join(", ")} dərəcə şaxta olacaq` },
  { k: "isti", hit: r => r.tmax >= HEAT, v: n => n.tmax, sort: -1, label: "İstilik", fmt: deg,
    say: it => `${it.map(([l, v]) => `${l} ${v}`).join(", ")} dərəcəyə qədər isti olacaq` },
  { k: "ildirim", hit: r => r.code >= 95 && (r.prob == null || r.prob >= 50), v: () => null, sort: 0, label: "İldırım",
    say: it => `${birlesdir(it.map(([l]) => l))} ildırım çaxacaq` },
];
function xeberdarliq(rows) {
  const out = [];
  for (const w of XEB) {
    const hit = rows.filter(w.hit).map(r => ({ r, n: nums(r) })).sort((a, b) => w.sort * ((w.v(a.n) ?? 0) - (w.v(b.n) ?? 0))).slice(0, 2);
    if (!hit.length) continue;
    const items = hit.map(({ r, n }) => [loc(r.name), w.v(n)]);
    const line = `${w.label}: ${hit.map(({ r, n }) => (w.v(n) == null ? r.name : `${r.name} ${w.fmt ? w.fmt(w.v(n)) : w.v(n)}`)).join(", ")}${w.fmt || w.v(hit[0].n) == null ? "" : w.unit}`;
    out.push({ k: w.k, seher: hit.map(h => h.r.name), say: w.say(items), line });
  }
  return out.slice(0, 3);
}

// --- Plan: ekranda və səsdə nə gedir ------------------------------------------------------------------------------------------
// rows: parse() nəticəsi (Bakı birinci). day: «2026-11-24». label: kodun saytdakı adı (app.js wxCode).
function plan(rows, day, { label = c => kind(c), now = Date.now() } = {}) {
  const [bakiRow, ...rest] = rows;
  if (!bakiRow || bakiRow.name !== "Bakı") throw new Error("hava: Bakı məlumatı yoxdur");
  const d = new Date(`${day}T00:00:00Z`);
  if (!Number.isFinite(d.getTime())) throw new Error(`hava: gün tanınmadı (${day})`);
  const date = `${d.getUTCDate()} ${MONTHS[d.getUTCMonth()]}`, weekday = WEEKDAYS[d.getUTCDay()];
  const card = r => ({ name: r.name, code: r.code, kind: kind(r.code), label: label(r.code), dir: r.dir == null ? null : sector(r.dir), ...nums(r) });
  const baki = card(bakiRow), bn = nums(bakiRow), warn = xeberdarliq(rows);
  // Bakının əsas halı: Bakıda xəbərdarlıq varsa o («güclü külək»), yoxsa hava növü.
  const bw = warn.find(w => w.seher.includes("Bakı"));
  const ifade = bw ? { kulek: "güclü külək", leysan: "güclü yağış", qar: "qar", saxta: "şaxta", isti: "istilik", ildirim: "ildırım" }[bw.k] : IFADE[baki.kind];
  const headline = `Sabah Bakıda ${ifade}`;
  const title = `Hava proqnozu, ${date}: Bakıda ${ifade}, ${deg(baki.tmin)}…${deg(baki.tmax)}`;
  // Bakı cümləsi: hava növü (ehtimal azdırsa «yağa bilər»), yağıntısız gündə «yağıntı gözlənilmir».
  let hal = ehtimal(CUMLE[baki.kind], bakiRow.prob);
  if (!YAGINTI.has(baki.kind) && (bakiRow.precip ?? 0) < 0.1 && (bakiRow.prob == null || bakiRow.prob < 30)) hal += ", yağıntı gözlənilmir";
  const parts = [
    { sahne: "giris", text: `Sabah, ${date}, ${weekday}, hava belə olacaq.` },
    { sahne: "baki", text: `Bakıda ${hal}. ${geceGunduz(bn.tmin, bn.tmax)}.` },
    { sahne: "baki", text: [kulekCumle(bn, bakiRow, true), yagintiCumle(bn, bakiRow)].filter(Boolean).join(" ") },
  ];
  if (warn.length) parts.push({ sahne: "diqqet", text: warn.map((w, i) => (i ? `${boyuk(w.say)}.` : `Diqqət: ${w.say}.`)).join(" ") });
  const pages = [];
  for (let i = 0; i < rest.length && pages.length < 2; i += 4) if (rest.slice(i, i + 4).length >= 2) pages.push(rest.slice(i, i + 4));
  pages.forEach((pg, i) => {
    const t = siyahi(pg.map(r => [loc(r.name), rnd(r.tmax)]));
    const rain = pg.filter(r => yagir(r) && !qarir(r)).map(r => loc(r.name)), snow = pg.filter(r => yagir(r) && qarir(r)).map(r => loc(r.name));
    // Səhifənin bütün şəhərlərində eyni yağıntı: adlar təkrar sadalanmır («Hamısında yağış yağacaq»), video qısa qalır.
    const all = (list, what) => (list.length === pg.length && pg.length > 2 ? `Hamısında ${what} yağacaq.` : `${birlesdir(list)} ${what} yağacaq.`);
    const extra = [rain.length ? all(rain, "yağış") : "", snow.length ? all(snow, "qar") : ""].filter(Boolean).join(" ");
    parts.push({ sahne: `bolge${i}`, text: `${i ? `${t} gözlənilir` : `Gündüz ${t} olacaq`}.${extra ? ` ${extra}` : ""}` });
  });
  // Altyazı hissələri: hər hissə ən çox 3 sətir (video-xeber.cjs captionChunks), hər biri səsin bir parçasıdır.
  const chunks = parts.filter(p => p.text).flatMap(p => V.captionChunks(p.text).map(text => ({ sahne: p.sahne, text })));
  const text = parts.map(p => p.text).filter(Boolean).join(" ");
  const hashtags = ["havaproqnozu", "hava", "Bakı"];
  return { tur: "hava", id: `hava-${day}`, day, date, weekday, title, headline, link: LINK, text, hashtags, baki,
    bolgeler: pages.map(pg => pg.map(card)), xeberdarliq: warn.map(w => ({ k: w.k, seher: w.seher, line: w.line })), parts: chunks,
    kredit: "Hava: Open-Meteo, model proqnozu", publishedAt: new Date(now).toISOString() };
}

// --- Rəqəm yoxlaması (kodda; sahibin qırmızı xətti: məlumat dəqiq olmalıdır) ----------------------------------------------------
// 1) plan rows ilə qurulubsa (rows verilsə) hər kartın rəqəmləri məlumatın yuvarlağıdır; 2) mətndəki hər rəqəm bu rəqəmlərdəndir
// (və ya tarixdir); 3) «Gəncədə 16» kimi şəhər + rəqəm cütü həmin şəhərin öz rəqəmidir. Səbəb (sətir) və ya "" — keçdi.
const NUM = /\d+(?:,\d+)?/g;
function yoxla(p, rows = null) {
  const cards = [p.baki, ...(p.bolgeler || []).flat()];
  if (rows) {
    for (const c of cards) {
      const r = rows.find(x => x.name === c.name);
      if (!r) return `${c.name}: məlumatda yoxdur`;
      const n = nums(r);
      for (const k of Object.keys(n)) if (n[k] !== c[k]) return `${c.name}: ${k} ${c[k]} ≠ məlumat ${n[k]}`;
      if (c.code !== r.code) return `${c.name}: kod ${c.code} ≠ ${r.code}`;
    }
  }
  const own = c => new Set([c.tmax, c.tmin, c.wind, c.gust, c.precip, c.snow, c.prob].filter(x => x != null).map(x => String(x).replace("-", "")));
  const allowed = new Set([String(Number(p.day?.slice(8, 10)))]);
  for (const c of cards) for (const x of own(c)) allowed.add(x);
  const texts = [p.title, p.headline, p.text, ...(p.parts || []).map(x => x.text), ...(p.xeberdarliq || []).map(w => w.line)];
  for (const t of texts) {
    for (const m of String(t || "").replace(/8ulduz/g, "").matchAll(NUM)) if (!allowed.has(m[0])) return `mətndə məlumatda olmayan rəqəm: ${m[0]} («${t}»)`;
  }
  // Şəhər + rəqəm: «Gəncədə 16», «Bakıda saniyədə 22».
  for (const c of cards) {
    const re = new RegExp(`${loc(c.name)} (?:saniyədə )?(\\d+(?:,\\d+)?)`, "g"), mine = own(c);
    for (const t of texts) for (const m of String(t || "").matchAll(re)) if (!mine.has(m[1])) return `${c.name}: mətndə ${m[1]}, məlumatda yoxdur`;
  }
  if (!/^Hava proqnozu, \d{1,2} [a-zə]+: Bakıda /.test(p.title || "")) return "başlıq şablona uyğun deyil";
  return "";
}

// --- Görüntü: hava şəraitinə uyğun səhnə (Pixabay/Pexels, video-ssenari.cjs goruntu) -------------------------------------------
// Əvvəl Bakının həqiqi görüntüsü həmin havada («baku rain»: etiketində həm «baku», həm «rain» olmalıdır — relevance), sonra yer adı
// olmayan təbiət səhnələri (göy, yağış damcıları, qar, duman). Şəhər küçəsi səhnəsi yoxdur: yad şəhərin yazısı, lövhəsi düşə bilər.
// Yad yerin etiketli klipi kodla atılır (yadYer; icazə: Azərbaycan və Bakı), şəkli redaktor yoxlayır (yerUygun).
const SAHNE = {
  acik: ["baku azerbaijan", "baku skyline", "baku boulevard", "blue sky clouds timelapse", "sunny sky sun"],
  esasen: ["baku azerbaijan", "baku skyline", "blue sky clouds timelapse", "sun clouds sky", "sunny sky sun"],
  qismen: ["baku skyline", "clouds timelapse sky", "sun clouds sky", "baku azerbaijan", "blue sky clouds timelapse"],
  bulud: ["baku clouds", "clouds timelapse", "overcast sky clouds", "grey clouds sky", "dark clouds sky"],
  duman: ["baku fog", "fog morning", "mist fog trees", "fog lake morning", "foggy forest"],
  ciskin: ["baku rain", "rain drops window", "rain drops glass", "wet leaves rain", "rain puddle"],
  yagis: ["baku rain", "rain drops window", "rain drops glass", "rain puddle", "rain clouds sky"],
  ildirim: ["lightning storm", "thunderstorm clouds", "lightning night sky", "storm clouds", "rain drops window"],
  qar: ["baku snow", "snow falling", "snowfall trees", "snowflakes falling", "snow forest"],
};
SAHNE.dondurucu = SAHNE.yagis; SAHNE.arabir = SAHNE.yagis; SAHNE.gucluyagis = SAHNE.yagis; SAHNE.leysan = SAHNE.yagis;
SAHNE.arabirqar = SAHNE.qar; SAHNE.gucluqar = SAHNE.qar; SAHNE.dolu = SAHNE.ildirim; SAHNE.deyisken = SAHNE.qismen;
const KULEK_SAHNE = ["caspian sea waves", "sea waves wind", "trees wind"];
// Öz video arxivi (video-arxiv.cjs; sahib, 2026-11-23: «həqiqi … videolardan istifadə etmək lazımdır»): əvvəl Bakının yeri kadrlarla
// yoxlanmış, sabahkı havada çəkilmiş klipi (başlıq kadrı), sonra yuxarıdakı səhnələr. Arxiv klipinin havası (yoxlamada Gemini yazır)
// sabahkı Bakı halına uyğun olmalıdır: yağışda yağış, qarda qar; gecə klipi gündüz proqnozuna getmir.
const ARXIV_HAVA = { acik: ["gunesli"], esasen: ["gunesli"], qismen: ["gunesli", "buludlu"], deyisken: ["gunesli", "buludlu"], bulud: ["buludlu"],
  duman: ["dumanli"], ciskin: ["yagisli"], yagis: ["yagisli"], arabir: ["yagisli"], gucluyagis: ["yagisli"], leysan: ["yagisli"], dondurucu: ["yagisli"],
  ildirim: ["yagisli"], dolu: ["yagisli"], qar: ["qarli"], arabirqar: ["qarli"], gucluqar: ["qarli"] };
const ARXIV_YER = ["Baku", "Azerbaijan"];
// goruntu() üçün arxiv seçimi: { yer, hava } — hava: arxiv klipinin icazəli havaları.
const arxivSecim = p => ({ yer: ARXIV_YER, hava: ARXIV_HAVA[p?.baki?.kind] || ["gunesli", "buludlu"] });
function sahneler(p) {
  const list = [...(SAHNE[p.baki.kind] || SAHNE.qismen)];
  // Dalğa yalnız güclü küləkdə (≥ 14 m/san — Bofort 7, və ya ani külək xəbərdarlığı): adi 10 m/san-da fırtınalı dəniz şişirtmədir.
  if ((p.baki.wind ?? 0) >= 14 || p.xeberdarliq?.some(w => w.k === "kulek")) list.splice(2, 0, ...KULEK_SAHNE.slice(0, 2));
  return [...new Set(list)].slice(0, 7);
}

// --- Qrafika (ASS, 1080×1920) -------------------------------------------------------------------------------------------------
const { W, H, X0, TEXT_W, COLOR } = V;
const C = { ...COLOR, sun: "F5A30A", cloud: "F2F5FA", cloud2: "B9C5D6", cloud3: "8E9CB2", drop: "4DA3FF", fog: "C9D3E0", bolt: "FFC531", warn: "F5A30A" };
// Yerləşmə: brend və bütün yazılar y 300…1480 (video-xeber.cjs ilə eyni: lentdə 4:5 kəsik, Reels düymələri). Kartlar 720…1110,
// altyazı 1150-dən, kredit 1420.
const Y = { chip: 466, head: 548, headMaxH: 160, body: 720, bodyEnd: 1110, cap: 1150, credit: 1420, outro: 900 };
const HEAD_SIZES = [84, 78, 72, 66, 60];
const ms = x => Math.max(0, Math.round(x * 1000));
const f1 = x => Math.round(x * 10) / 10;
// Forma: { x, y, d } — yol (0,0)-dan başlayır, \pos(x,y) ilə qoyulur (libass çəkiliş qutusunun yeri hər iki şərhdə eyni olsun).
function poly(pts) {
  const mx = Math.min(...pts.map(p => p[0])), my = Math.min(...pts.map(p => p[1]));
  return { x: f1(mx), y: f1(my), d: `m ${pts.map(([a, b], i) => `${f1(a - mx)} ${f1(b - my)}${i === 0 ? " l" : ""}`).join(" ")}` };
}
const disc = (cx, cy, r) => ({ x: f1(cx - r), y: f1(cy - r), d: V.circle(f1(r)) });
function rrect(x, y, w, h, r) {
  r = Math.min(r, w / 2, h / 2);
  const k = r * 0.4477, q = v => f1(v);   // bezier: (1 − 0,5523) r
  return { x: q(x), y: q(y), d: `m ${q(r)} 0 l ${q(w - r)} 0 b ${q(w - k)} 0 ${q(w)} ${q(k)} ${q(w)} ${q(r)} l ${q(w)} ${q(h - r)} b ${q(w)} ${q(h - k)} ${q(w - k)} ${q(h)} ${q(w - r)} ${q(h)} `
    + `l ${q(r)} ${q(h)} b ${q(k)} ${q(h)} 0 ${q(h - k)} 0 ${q(h - r)} l 0 ${q(r)} b 0 ${q(k)} ${q(k)} 0 ${q(r)} 0` };
}
// Fırlanmış düzbucaqlı (şüa, ox, qar dənəsinin qolu): mərkəz (cx, cy), uzunluq len, en w, bucaq a (radian, saat əqrəbi ilə, 0 — yuxarı).
function bar(cx, cy, len, w, a) {
  const ux = Math.sin(a), uy = -Math.cos(a), vx = -uy, vy = ux, h = len / 2, e = w / 2;
  return poly([[cx - ux * h - vx * e, cy - uy * h - vy * e], [cx + ux * h - vx * e, cy + uy * h - vy * e], [cx + ux * h + vx * e, cy + uy * h + vy * e], [cx - ux * h + vx * e, cy - uy * h + vy * e]]);
}
// Bulud: üç dairə + yumru əsas. (x, y) qutunun sol yuxarısı, s ölçü, dy yuxarı sürüşmə (yağıntı yeri üçün), k miqyas.
function cloud(x, y, s, color, { dy = 0, k = 1, dx = 0 } = {}) {
  const ox = x + s * (0.5 + dx) - s * 0.5 * k, oy = y + s * dy + s * 0.5 * (1 - k);
  const S = v => v * s * k;
  return [disc(ox + S(0.36), oy + S(0.52), S(0.18)), disc(ox + S(0.56), oy + S(0.42), S(0.23)), disc(ox + S(0.74), oy + S(0.56), S(0.15)),
    rrect(ox + S(0.14), oy + S(0.52), S(0.74), S(0.24), S(0.12))].map(sh => ({ sh, c: color }));
}
function sun(cx, cy, r, color = C.sun) {
  const rays = Array.from({ length: 8 }, (_, i) => ({ sh: bar(cx + Math.sin(i * Math.PI / 4) * r * 1.55, cy - Math.cos(i * Math.PI / 4) * r * 1.55, r * 0.5, r * 0.26, i * Math.PI / 4), c: color, ray: true }));
  return [...rays, { sh: disc(cx, cy, r), c: color }];
}
const drops = (x, y, s, xs, color = C.drop) => xs.map(fx => ({ sh: bar(x + s * fx, y + s * 0.8, s * 0.17, s * 0.05, 0.35), c: color }));
const flake = (cx, cy, r) => [0, Math.PI / 3, 2 * Math.PI / 3].map(a => ({ sh: bar(cx, cy, r * 2, r * 0.32, a), c: C.cloud }));
// İkon: hava növünə görə formalar (arxadan önə). Rəngli emoji libass-da çıxmır — ikonlar vektordur.
function icon(k, x, y, s) {
  const cx = x + s / 2, cy = y + s / 2;
  switch (k) {
    case "acik": return sun(cx, cy, s * 0.21);
    case "esasen": return [...sun(x + s * 0.44, y + s * 0.42, s * 0.19), ...cloud(x, y, s, C.cloud, { k: 0.55, dx: 0.17, dy: 0.2 })];
    case "qismen": case "deyisken": return [...sun(x + s * 0.36, y + s * 0.34, s * 0.16), ...cloud(x, y, s, C.cloud, { k: 0.85, dx: 0.07, dy: 0.1 })];
    case "bulud": return [...cloud(x, y, s, C.cloud2, { k: 0.7, dx: -0.12, dy: -0.12 }), ...cloud(x, y, s, C.cloud, { dy: 0.02 })];
    case "duman": return [[0.34, 0.15, 0.85], [0.47, 0.1, 0.75], [0.6, 0.2, 0.9], [0.73, 0.12, 0.7]].map(([fy, a, b]) => ({ sh: rrect(x + s * a, y + s * fy, s * (b - a), s * 0.075, s * 0.0375), c: C.fog }));
    case "ciskin": return [...cloud(x, y, s, C.cloud, { dy: -0.12 }), ...[[0.33, 0.74], [0.5, 0.82], [0.67, 0.74], [0.42, 0.92], [0.59, 0.92]].map(([fx, fy]) => ({ sh: disc(x + s * fx, y + s * fy, s * 0.03), c: C.drop }))];
    case "yagis": case "arabir": return [...cloud(x, y, s, C.cloud, { dy: -0.12 }), ...drops(x, y, s, [0.34, 0.52, 0.7])];
    case "gucluyagis": case "leysan": return [...cloud(x, y, s, C.cloud2, { dy: -0.12 }), ...drops(x, y, s, [0.26, 0.42, 0.58, 0.74])];
    case "dondurucu": return [...cloud(x, y, s, C.cloud, { dy: -0.12 }), ...drops(x, y, s, [0.34, 0.66]), ...flake(x + s * 0.5, y + s * 0.82, s * 0.07)];
    case "qar": case "arabirqar": case "gucluqar": return [...cloud(x, y, s, C.cloud2, { dy: -0.12 }), ...flake(x + s * 0.33, y + s * 0.8, s * 0.075), ...flake(x + s * 0.53, y + s * 0.88, s * 0.075), ...flake(x + s * 0.72, y + s * 0.78, s * 0.075)];
    case "ildirim": case "dolu": return [...cloud(x, y, s, C.cloud3, { dy: -0.12 }),
      { sh: poly([[0.54, 0.56], [0.38, 0.8], [0.5, 0.8], [0.43, 0.97], [0.65, 0.7], [0.53, 0.7], [0.6, 0.56]].map(([a, b]) => [x + s * a, y + s * b])), c: C.bolt }];
    default: return sun(cx, cy, s * 0.21);
  }
}
// Külək oxu: küləyin ESDİYİ tərəfə (şimal küləyi — aşağı). dir: 0–7 (YON), mərkəz (cx, cy), uzunluq len.
function arrow(dir, cx, cy, len, color = C.white) {
  const a = (dir * 45 + 180) * Math.PI / 180, ux = Math.sin(a), uy = -Math.cos(a), vx = -uy, vy = ux, h = len / 2, w = len * 0.16, hw = len * 0.36;
  const tip = [cx + ux * h, cy + uy * h], base = [cx - ux * h, cy - uy * h], neck = [cx + ux * (h - len * 0.42), cy + uy * (h - len * 0.42)];
  return [{ sh: poly([[base[0] - vx * w, base[1] - vy * w], [neck[0] - vx * w, neck[1] - vy * w], [neck[0] - vx * hw, neck[1] - vy * hw], tip,
    [neck[0] + vx * hw, neck[1] + vy * hw], [neck[0] + vx * w, neck[1] + vy * w], [base[0] + vx * w, base[1] + vy * w]]), c: color }];
}

// Zaman: video-xeber.cjs timeline() ilə eyni (səs varsa onun vaxtı, yoxsa oxuma sürəti; 59 s-dən uzun olmur — sondakı hissələr düşür).
const prepare = p => ({ say: [p.parts[0].text, ...p.parts.slice(1).map(x => x.text), V.abune("hava").say], chunks: p.parts.slice(1).map(x => x.text) });
// Səhnələrin vaxtı: hər səhnə öz ilk hissəsi ilə başlayır, növbəti səhnə başlayanda (sonuncu — sonluqda) bitir.
function scenes(p, tl) {
  const at = [tl.head, ...tl.chunks.map(c => c.at)], out = [];
  at.forEach((span, i) => {
    const s = p.parts[i].sahne, key = s === "giris" ? "baki" : s;
    if (!out.length || out[out.length - 1].key !== key) out.push({ key, from: i === 0 ? 0 : span[0] });
  });
  out.forEach((sc, i) => { sc.to = i + 1 < out.length ? out[i + 1].from : tl.outro[0]; });
  return out;
}

function ass(p, tl, { footage = false } = {}) {
  const D = tl.duration, out = tl.outro[0], ev = [];
  const col = V.assColor, T = V.assTime, txt = V.assText;
  const sc = hex => `&H00${col(hex).slice(2, 8)}`;
  const st = (name, font, size, color, extra = {}) => {
    const o = { outline: 0, outlineColor: "000000", border: 1, align: 7, bold: 0, ...extra };
    return `Style: ${name},${font},${size},${sc(color)},${sc(color)},${sc(o.outlineColor)},${sc("000000")},${o.bold},0,0,0,100,100,0,0,${o.border},${o.outline},0,${o.align},${X0},${X0},0,1`;
  };
  const F = V.FONT;
  const styles = [st("Shape", F, 10, C.white), st("Brand", `${F} Black`, 96, C.white, { bold: -1 }),
    st("Chip", `${F} Black`, 40, C.bg, { bold: -1, border: 3, outline: 12, outlineColor: C.orange }),
    st("Txt", `${F} Medium`, 44, C.white), st("Num", `${F} Black`, 88, C.white, { bold: -1 }), st("Reg", F, 36, C.gray),
    st("Cap", `${F} Medium`, V.CAP_SIZE, C.white, { border: 3, outline: V.CAP_PAD, outlineColor: C.box }),
    st("Outro", `${F} Medium`, 60, C.gray, { align: 5 }), V.SUB_STYLE];
  const dlg = (layer, from, to, style, text) => { if (to - from > 0.02) ev.push(`Dialogue: ${layer},${T(from)},${T(to)},${style},,0,0,0,,${text}`); };
  const shade = "\\bord3\\3c&H000000&\\shad2\\4a&H40&";   // görüntü üstündə yazı: kənar və kölgə
  // Formalar: hər biri ayrıca sətir (üst-üstə düşən dairələr birləşmiş kimi görünür), girişdə yuxarı sürüşür və görünür.
  const shapes = (layer, from, to, list, { alpha = "00", lift = 18, delay = 0, spin = null } = {}) => {
    for (const { sh, c, ray } of list) {
      const t0 = ms(delay), rot = ray && spin ? `\\org(${f1(spin[0])},${f1(spin[1])})\\t(${t0},${ms(to - from)},\\frz-25)` : "";
      dlg(layer, from, to, "Shape", `{\\an7\\move(${sh.x},${f1(sh.y + lift)},${sh.x},${sh.y},${t0},${t0 + 320})\\p1\\bord0\\shad0\\1c${col(c)}\\1a&H${alpha}&\\fad(${t0 ? 0 : 220},220)`
        + `${t0 ? `\\alpha&HFF&\\t(${t0},${t0 + 220},\\alpha&H${alpha}&)` : ""}${rot}}${sh.d}`);
    }
  };
  const text = (layer, from, to, x, y, style, s, extra = "", delay = 0) => {
    const t0 = ms(delay);
    dlg(layer, from, to, style, `{\\an7\\move(${x},${y + 14},${x},${y},${t0},${t0 + 300})\\fad(${t0 ? 0 : 220},220)${t0 ? `\\alpha&HFF&\\t(${t0},${t0 + 220},\\alpha&H00&)` : ""}${extra}}${[].concat(s).map(txt).join("\\N")}`);
  };
  // Fon: görüntü varsa üstündə yüngül tündləşmə (kartlar və yazı oxunsun), sonluqda tam tünd; yoxdursa tünd göy üstündə hərəkətli işıq.
  if (footage) {
    dlg(0, 0, out + 0.3, "Shape", `{\\an7\\pos(0,0)\\p1\\bord0\\shad0\\1c${col(C.bg)}\\1a&HB4&}${V.rect(W, H)}`);
    dlg(0, out, D, "Shape", `{\\an7\\pos(0,0)\\p1\\bord0\\shad0\\1c${col(C.bg)}\\1a&H28&\\fad(300,0)}${V.rect(W, H)}`);
  } else {
    dlg(0, 0, D, "Shape", `{\\an5\\move(180,640,280,760)\\p1\\bord0\\shad0\\1c${col(C.blue)}\\1a&HA8&\\blur90}${V.circle(520)}`);
    dlg(0, 0, D, "Shape", `{\\an5\\move(960,1560,880,1460)\\p1\\bord0\\shad0\\1c${col(C.blue2)}\\1a&HDC&\\blur90}${V.circle(440)}`);
  }
  // Brend zolağı (video-xeber.cjs ilə eyni): loqo ffmpeg-də üstünə qoyulur, yanında «.az»; altında narıncı gediş xətti.
  const L = V.L, py = L.barY + L.barH;
  dlg(1, 0, D, "Shape", `{\\an7\\pos(0,${L.barY})\\p1\\bord0\\shad0\\1c${col(C.bar)}}${V.rect(W, L.barH)}`);
  dlg(2, 0, D, "Brand", `{\\an1\\pos(${V.logoX() + V.logoW() - 4},${V.logoY() + L.logoH + 4})\\fs72}.az`);
  V.subBadge(dlg, out);
  dlg(2, 0, D, "Shape", `{\\an7\\pos(0,${py})\\p1\\bord0\\shad0\\1c${col(C.orange)}\\clip(0,${py},1,${py + 8})\\t(0,${ms(D)},\\clip(0,${py},${W},${py + 8}))}${V.rect(W, 8)}`);
  // Nişan və tarix: başdan sonluğa qədər.
  const chip = "HAVA PROQNOZU";
  dlg(3, 0, out + 0.3, "Chip", `{\\an4\\pos(${X0 + 12},${Y.chip + 30})\\fad(250,300)}${chip}`);
  dlg(3, 0, out + 0.3, "Txt", `{\\an4\\pos(${Math.round(X0 + V.textWidth(chip, 40, "black") + 64)},${Y.chip + 30})\\fs40\\fad(250,300)${footage ? shade : `\\1c${col(C.gray)}`}}${txt(`${p.date}, ${p.weekday}`)}`);
  // Kredit: Open-Meteo (CC BY 4.0) və görüntü bankı — başdan sonluğa qədər, altda.
  const kredit = [p.kredit || "Hava: Open-Meteo", footage ? `Görüntü: ${clean(p.goruntuMenbe) || "Pixabay"}` : ""].filter(Boolean).join(" · ");
  dlg(3, 0, out + 0.3, "Reg", `{\\an7\\pos(${X0},${Y.credit})\\fad(250,300)\\1c${col(C.white)}${shade}}${txt(kredit)}`);

  const list = scenes(p, tl), cardBg = (x, y, w, h, r = 28) => ({ sh: rrect(x, y, w, h, r), c: C.bar });
  for (const s of list) {
    const { from, to } = s;
    // Səhnənin başlığı (y 548…): Bakı — «Sabah Bakıda …», bölgələr, xəbərdarlıq.
    const headText = s.key === "baki" ? p.headline : s.key === "diqqet" ? "Diqqət" : "Bölgələrdə hava";
    const head = V.fitHeadline(headText, HEAD_SIZES, Y.headMaxH);
    dlg(3, from, to, "Num", `{\\an7\\move(${X0},${Y.head + 22},${X0},${Y.head},0,300)\\fs${head.size}\\fad(160,200)${s.key === "diqqet" ? `\\1c${col(C.warn)}` : ""}${shade}}${head.lines.map(txt).join("\\N")}`);
    if (s.key === "baki") {
      const b = p.baki, top = Y.body, h = Y.bodyEnd - top;
      shapes(1, from, to, [cardBg(X0 - 24, top, TEXT_W + 48, h)], { alpha: "48", lift: 0 });
      const ic = icon(b.kind, X0 + 8, top + 22, 236);
      shapes(2, from, to, ic, { lift: 16, delay: 0.1, spin: b.kind === "acik" ? [X0 + 126, top + 140] : null });
      text(2, from, to, 372, top + 24, "Txt", `Bakı · ${b.label}`, "\\fs46", 0.12);
      text(2, from, to, 362, top + 64, "Num", deg(b.tmax), "\\fs170", 0.18);
      text(2, from, to, 372 + Math.round(V.textWidth(deg(b.tmax), 170, "black")) + 18, top + 155, "Txt", `gecə ${deg(b.tmin)}`, `\\fs54\\1c${col(C.gray)}`, 0.24);
      // Göstəricilər: külək (istiqamət oxu ilə), ani külək, yağıntı (və ehtimal) və ya qar.
      const my = top + h - 112;
      shapes(2, from, to, [{ sh: rrect(X0, my - 14, TEXT_W, 2, 1), c: C.gray }], { alpha: "A0", lift: 0, delay: 0.3 });
      const cols = [
        b.wind == null ? null : { label: `Külək${b.dir == null ? "" : ` · ${YON[b.dir].toLocaleLowerCase("az")}`}`, value: `${b.wind} m/san`, arrow: b.dir },
        b.gust == null ? null : { label: "Ani külək", value: `${b.gust} m/san` },
        (b.snow ?? 0) >= 1 ? { label: "Qar", value: `${b.snow} sm` } : b.precip == null ? null : { label: "Yağıntı", value: `${b.precip} mm${b.prob == null ? "" : ` · ${b.prob}%`}` },
      ].filter(Boolean);
      cols.forEach((c, i) => {
        const x = X0 + i * Math.round(TEXT_W / 3), d = 0.34 + i * 0.08;
        text(2, from, to, x, my + 2, "Reg", c.label, `\\fs32`, d);
        const vx = c.arrow == null ? x : x + 50;
        if (c.arrow != null) shapes(2, from, to, arrow(c.arrow, x + 20, my + 66, 40), { lift: 14, delay: d });
        text(2, from, to, vx, my + 38, "Num", c.value, "\\fs50", d);
      });
    } else if (s.key === "diqqet") {
      // Xəbərdarlıq kartı: hündürlük məzmuna görədir (sətirlər üçbucağa görə ortalanır), şrift sığan ən böyüyüdür (54 → 38).
      const top = Y.body, lines = (p.xeberdarliq || []).map(w => w.line), tw = TEXT_W - 190;
      const fits = [54, 48, 42, 38].map(sz => { const w = lines.map(l => V.wrap(l, sz, "bold", tw)); return { fs: sz, w, h: Math.round(w.flat().length * sz * 1.15) + (lines.length - 1) * 22 }; });
      const fit = fits.find(o => o.h <= Y.bodyEnd - top - 120) || fits[fits.length - 1];
      const y0 = top + Math.max(34, Math.round(96 - fit.h / 2)), noteY = Math.max(y0 + fit.h + 18, top + 150);
      const h = Math.min(Y.bodyEnd - top, Math.max(200, noteY - top + 64));
      shapes(1, from, to, [cardBg(X0 - 24, top, TEXT_W + 48, h)], { alpha: "30", lift: 0 });
      shapes(2, from, to, [{ sh: rrect(X0 - 24, top, 12, h, 6), c: C.warn }], { lift: 0 });
      shapes(2, from, to, [{ sh: poly([[X0 + 70, top + 36], [X0 + 140, top + 156], [X0, top + 156]]), c: C.warn }], { delay: 0.08 });
      text(2, from, to, X0 + 62, top + 74, "Num", "!", `\\fs80\\1c${col(C.bar)}`, 0.08);
      let y = y0;
      for (const [i, w] of fit.w.entries()) {
        text(2, from, to, X0 + 180, y, "Num", w, `\\fs${fit.fs}`, 0.14 + i * 0.1);
        y += Math.round(w.length * fit.fs * 1.15) + 22;
      }
      text(2, from, to, X0 + 180, noteY, "Reg", "Model proqnozu, rəsmi xəbərdarlıq deyil", "\\fs30", 0.3);
    } else {
      // Bölgələr: 2×2 kart — şəhər, ikon, gündüz (böyük) və gecə temperaturu.
      const pg = p.bolgeler[Number(s.key.slice(5))] || [], gap = 24, cw = (TEXT_W - gap) / 2, ch = (Y.bodyEnd - Y.body - gap) / 2;
      text(3, from, to, X0, Y.head + 108, "Reg", "Gündüz / gecə temperaturu", `\\fs36\\1c${col(C.white)}${shade}`, 0.05);
      pg.forEach((c, i) => {
        const x = X0 + (i % 2) * (cw + gap), y = Y.body + Math.floor(i / 2) * (ch + gap), d = 0.06 + i * 0.08;
        shapes(1, from, to, [cardBg(x, y, cw, ch, 24)], { alpha: "50", lift: 0, delay: d });
        shapes(2, from, to, [{ sh: rrect(x, y + 22, 8, ch - 44, 4), c: C.orange }], { lift: 0, delay: d });
        text(2, from, to, x + 28, y + 16, "Txt", c.name, "\\fs46", d);
        shapes(2, from, to, icon(c.kind, x + cw - 150, y + (ch - 136) / 2, 136), { lift: 12, delay: d + 0.04 });
        text(2, from, to, x + 26, y + 72, "Num", deg(c.tmax), "\\fs88", d + 0.04);
        text(2, from, to, x + 34 + Math.round(V.textWidth(deg(c.tmax), 88, "black")), y + 106, "Txt", deg(c.tmin), `\\fs46\\1c${col(C.gray)}`, d + 0.08);
      });
    }
  }
  // Altyazılar: deyilən söz narıncı yanır (video-xeber.cjs ilə eyni üsul, wordTimes), hissə növbətisi başlayanda çəkilir.
  const white = col(C.white), lit = col(C.orange);
  const caps = [{ text: p.parts[0].text, at: tl.head }, ...tl.chunks];
  caps.forEach((c, i) => {
    const until = i + 1 < caps.length ? caps[i + 1].at[0] : out, times = V.wordTimes(c.text, c.at[0], c.at[1]);
    let k = 0;
    const lines = V.wrap(c.text, V.CAP_SIZE, "medium", V.CAP_W).map(line => line.split(" ").filter(Boolean).map(w => {
      const [, a, b] = times[k++] || [w, c.at[0], c.at[1]], t1 = ms(a - c.at[0]), t2 = ms(b - c.at[0]);
      return `{\\1c${white}\\t(${t1},${t1 + 60},\\1c${lit})\\t(${t2},${t2 + 60},\\1c${white})}${txt(w)}`;
    }).join(" "));
    dlg(4, c.at[0], until, "Cap", `{\\an7\\pos(${X0 + V.CAP_PAD},${Y.cap + V.CAP_PAD})\\fad(180,120)}${lines.join("\\N")}`);
  });
  // Sonluq: vəd və «ABUNƏ OL» düyməsi (video-xeber.cjs subOutro), hava səhifəsinin ünvanı, kreditlər.
  V.subOutro(dlg, out, D, Y.outro, "hava", "Bütün şəhərlər: 8ulduz.az/bolme/hava");
  dlg(3, out, D, "Outro", `{\\pos(540,${Y.outro + 260})\\fad(300,0)\\fs34}${txt(`Hava: Open-Meteo.com (CC BY 4.0)${footage ? ` · Görüntü: ${clean(p.goruntuMenbe) || "Pixabay"}` : ""}`)}`);
  return ["[Script Info]", "ScriptType: v4.00+", `PlayResX: ${W}`, `PlayResY: ${H}`, "WrapStyle: 2", "ScaledBorderAndShadow: yes", "YCbCr Matrix: TV.709", "",
    "[V4+ Styles]",
    "Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding",
    ...styles, "", "[Events]", "Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text", ...ev, ""].join("\n");
}

// <çıxış>.json: TikTok/YouTube yükləyicilərinin müqaviləsi (docs/tiktok.md §7, docs/youtube.md: kind «hava», url saytın səhifəsi).
// text/summary: diktor mətni + kreditlər (CC BY 4.0 atribusiyası post mətnində də olsun). source/sourceUrl yoxdur: bu, başqa saytın
// xəbəri deyil, öz məlumat məhsulumuzdur (yükləyicilər belə videonu xəbər mənbəyi qaydasına salmır; docs/youtube.md «kind»).
function storyFields(p) {
  const kredit = `Hava məlumatı: Open-Meteo.com, model proqnozu (CC BY 4.0); rəsmi xəbərdarlıq deyil.${p.goruntuMenbe ? ` Görüntü: ${clean(p.goruntuMenbe)}.` : ""}`;
  const text = `${p.text} ${kredit}`;
  return { id: p.id, own: true, kind: "hava", title: p.title, summary: text, text, url: p.link, category: "hava", lang: "az",
    publishedAt: p.publishedAt, createdAt: p.publishedAt, hashtags: (p.hashtags || []).slice(0, 3) };
}
// Saytın qaydası (app.js policyViolation) üçün sətir: mətn öz mənbəmizdəndir («8ULDUZ», content-policy.js azSources).
const policyRow = p => ({ title: p.title, summary: p.text, source: "8ULDUZ", sourceUrl: p.link || LINK, category: "hava", lang: "az" });

async function render(p, out, opt = {}) {
  const log = opt.log || console.log;
  if (p?.tur !== "hava" || !Array.isArray(p.parts) || !p.parts.length || !p.baki) throw new Error("hava planı deyil");
  const why = yoxla(p);
  if (why) throw new Error(`hava: rəqəm yoxlaması — ${why}`);
  // Qırmızı xətt 2 (forma üçün): öz mətnimiz də saytın qaydasından keçir.
  const policy = opt.policy || (app => x => app.policyViolation(x))(require("./topics.cjs").loadApp(ROOT));
  if (policy(policyRow(p))) throw new Error("hava mətni saytın qaydasından keçmir");
  out = path.resolve(out);
  const clips = (Array.isArray(p.klipler) ? p.klipler : []).map(f => path.resolve(opt.base || path.dirname(out), String(f))).filter(f => fs.existsSync(f))
    .map(file => { try { const m = V.probe(file); return { file, w: m.width || 0, h: m.height || 0, dur: m.duration || 0 }; } catch { return { file }; } });
  const pr = prepare(p), dir = fs.mkdtempSync(path.join(os.tmpdir(), "video-hava-"));
  try {
    const wantVoice = opt.voice ?? (p.ses !== false && process.env.VIDEO_SES !== "0");
    const v = wantVoice ? V.voice(pr, dir, log) : null;
    const tl = V.timeline(pr, v);
    fs.writeFileSync(path.join(dir, "video.ass"), ass(p, tl, { footage: clips.length > 0 }));
    fs.mkdirSync(path.dirname(out), { recursive: true });
    // Hava görüntüsü (göy, bulud, yağış, şəhər panoraması) bütün ekranı doldurur: üfüqi klip ortadan 9:16 kəsilir (ölçü verilmir —
    // video-xeber.cjs clipFilter «doldurma» rejimi). Xəbər videosundakı «ortada kəskin zolaq + bulanıq fon» burada kartların arxasında qalır,
    // zolağın sərt kənarı görünürdü (2026-11-23 ilk önizləmə).
    const fill = clips.map(({ file, dur }) => ({ file, dur }));
    V.run("ffmpeg", V.ffmpegArgs({ tl, assFile: "video.ass", logo: path.join(ROOT, V.LOGO.file), voiceFile: v?.file, out, clips: fill }), { cwd: dir, timeout: 900000 });
    const cover_s = 1.5, base = out.replace(/\.mp4$/i, "");
    V.run("ffmpeg", ["-hide_banner", "-loglevel", "error", "-y", "-ss", String(cover_s), "-i", out, "-frames:v", "1", "-q:v", "3", `${base}.jpg`]);
    const mid = ([s, e]) => Math.round((s + e) * 50) / 100, sc = scenes(p, tl);
    const kadrlar = [cover_s, ...sc.flatMap(s => (s.to - s.from > 7 ? [mid([s.from, (s.from + s.to) / 2]), mid([(s.from + s.to) / 2, s.to])] : [mid([s.from, s.to])])).filter(x => x > cover_s + 0.5), mid([tl.outro[0], tl.duration])];
    const meta = { ...storyFields(p), ...V.probe(out), cover_s, kadrlar, voice: Boolean(v), ...(v?.motor ? { ses: v.motor } : {}), ...(v ? { oxunan: pr.say } : {}), ...(v?.nefes ? { nefes: v.nefes } : {}), parts: 2 + tl.chunks.length, sahneler: sc.map(s => s.key),
      ...(clips.length ? { goruntu: clean(p.goruntuMenbe) || "Pixabay", klip: clips.length } : {}) };
    fs.writeFileSync(`${base}.json`, JSON.stringify(meta, null, 1));
    if (opt.keepAss) fs.copyFileSync(path.join(dir, "video.ass"), `${base}.ass`);
    log(`video: hava — ${meta.width}×${meta.height}, ${meta.duration.toFixed(1)} s, ${(meta.bytes / 1e6).toFixed(1)} MB, ${tl.chunks.length + 1} altyazı, ${v ? `səsli (${v.motor === "babek" ? "Babək" : "SARA"})` : "səssiz"}, ${clips.length ? `${clips.length} klip` : "görüntüsüz"} — ${p.title}`);
    return meta;
  } finally {
    fs.rmSync(dir, { recursive: true, force: true });
  }
}

module.exports = { cities, url, fetchData, parse, plan, yoxla, rnd, deg, mmText, nums, kind, loc, siyahi, geceGunduz, kulekCumle, xeberdarliq, sahneler, arxivSecim, ARXIV_HAVA,
  scenes, prepare, ass, icon, arrow, storyFields, policyRow, render, SEHERLER, LINK, OM_SITE, DAILY, GUST, FROST, FROST_BAKU, HEAT, SNOW, SNOW_LOW, RAIN_HEAVY, MOUNTAIN, Y };

if (require.main === module) {
  const [src, out] = process.argv.slice(2);
  if (!src || !out) { console.error("İşlədilmə: node .github/scripts/video-hava.cjs <giriş.json> <çıxış.mp4>"); process.exit(2); }
  render(JSON.parse(fs.readFileSync(src, "utf8")), out, { keepAss: process.env.VIDEO_ASS === "1" })
    .catch(e => { console.error(`video: hava alınmadı — ${String(e?.message || e)}`); process.exitCode = 1; });
}
