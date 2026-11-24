// «Dinlə» işçisi (worker.js) üçün Saranın oxunuş qaydaları: .github/ses-server/az_text.py-nin verbalize/for_voice hissəsinin
// JavaScript nüsxəsi (sahib, 2026-11-23: «saytda da düzgün oxunsun»). Eyni girişdən eyni nəticə çıxmalıdır: tests/fixtures/
// ses-oxunus.json hər iki dildə yoxlanır (tests/test_ses_server.py, tests/ses-worker.test.cjs). Qaydanı Python-da dəyişəndə
// burada da dəyişin və fiksturu yeniləyin: SES_OXUNUS_YENILE=1 python3 -m unittest tests.test_ses_server
// Python-un «\b»-si Unicode sözünü tanıyır, JavaScript-inki yox («ə», «ş» söz hərfi sayılmır): söz sərhədi açıq yazılır (B, E).

const ONES = ["", "bir", "iki", "üç", "dörd", "beş", "altı", "yeddi", "səkkiz", "doqquz"];
const TENS = ["", "on", "iyirmi", "otuz", "qırx", "əlli", "altmış", "yetmiş", "səksən", "doxsan"];
const SCALES = [[1e12, "trilyon"], [1e9, "milyard"], [1e6, "milyon"], [1000, "min"]];
const MONTHS = ["yanvar", "fevral", "mart", "aprel", "may", "iyun", "iyul", "avqust", "sentyabr", "oktyabr", "noyabr", "dekabr"];
const ORDINAL = { bir: "birinci", iki: "ikinci", "üç": "üçüncü", "dörd": "dördüncü", "beş": "beşinci", "altı": "altıncı",
  yeddi: "yeddinci", "səkkiz": "səkkizinci", doqquz: "doqquzuncu", on: "onuncu", iyirmi: "iyirminci",
  otuz: "otuzuncu", "qırx": "qırxıncı", "əlli": "əllinci", "altmış": "altmışıncı", "yetmiş": "yetmişinci",
  "səksən": "səksəninci", doxsan: "doxsanıncı", "yüz": "yüzüncü", min: "mininci", milyon: "milyonuncu",
  milyard: "milyardıncı", trilyon: "trilyonuncu", "sıfır": "sıfırıncı" };
const UNITS = { "%": "faiz", "₼": "manat", "$": "dollar", "€": "avro", "£": "funt", "₽": "rubl" };
const WORD_UNITS = { azn: "manat", usd: "dollar", eur: "avro", km: "kilometr", kq: "kiloqram", kg: "kiloqram",
  mln: "milyon", mlrd: "milyard", "min.": "min", sm: "santimetr", mm: "millimetr", "°c": "dərəcə" };
export const ALLOWED = new Set("abcçdeəfgğhxıijkqlmnoöprsştuüvyz -");

const UP = "A-ZÇƏĞIİÖŞÜ", LO = "a-zçəğıiöşü", SP = String.fromCharCode(0xa0, 0x202f);   // bölünməz boşluqlar (rəqəm qruplarında)
const VOWELS = new Set("aıoueəiöü"), BACK = new Set("aıou");
const LETTERS = { a: "a", b: "be", c: "ce", "ç": "çe", d: "de", e: "e", "ə": "ə", f: "fe", g: "ge", "ğ": "ğe",
  h: "he", x: "xe", "ı": "ı", i: "i", j: "je", k: "ka", q: "qe", l: "el", m: "em", n: "en",
  o: "o", "ö": "ö", p: "pe", r: "er", s: "es", "ş": "şe", t: "te", u: "u", "ü": "ü", v: "ve",
  y: "ye", z: "ze", w: "dubl ve" };
const ACRONYMS = {
  nato: "nato", uefa: "uefa", fifa: "fifa", socar: "sokar", azal: "azal", opec: "opek", tass: "tass",
  apa: "apa", yap: "yap", covid: "kovid", unesco: "yunesko", unicef: "yunisef", nasa: "nasa", xin: "xin",
  din: "din", cop: "kop", asan: "asan", kvan: "kvan", sima: "sima", "azərtac": "azərtac", azertac: "azərtac",
  cnn: "si-en-en", bbc: "bi-bi-si", aiib: "a-i-i-be", noaa: "en-o-a-a", eevza: "e-e-ve-ze-a", usa: "yu-es-ey",
  ok: "okey", pr: "piar", it: "ay-ti", sms: "es-em-es", gps: "ci-pi-es", vip: "vip", dj: "di-cey",
};
const SHORT_WORDS = new Set(`a ə o u bu o nə kim var yox son ilk hər biz siz onu ona bəs ya da də ki mən sən gün ay il su od yol ev baş göz
əl qan can tez çox az üç iki bir on beş ana ata qız ər ad yaş iş dil şər xoş pis isti qar buz yağ dağ daş bağ qol ayaq ölü
yeni sağ sol ağ boz göy qəm dəm vay oh ah hə yox biz ilə ola oldu ki və qaz vaz ram ege yaz qış`.split(/\s+/));
const FOREIGN = {
  google: "qugl", youtube: "yutub", whatsapp: "vatsap", instagram: "instaqram", facebook: "feysbuk",
  iphone: "ayfon", ipad: "aypad", apple: "eppl", microsoft: "maykrosoft", windows: "vindovs",
  washington: "vaşinqton", trump: "tramp", news: "nyus", bloomberg: "blumberq", wall: "uoll",
  street: "strit", reels: "rils", photos: "fotos", group: "qrup", steel: "stil", philadelphia: "filadelfiya",
  milwaukee: "miluoki", bucks: "baks", anthropic: "entropik", telegram: "teleqram", twitter: "tvitter",
  tiktok: "tiktok", openai: "open ay ay", chatgpt: "çat ci-pi-ti", samsung: "samsunq", huawei: "huavey",
  playstation: "pleysteyşn", netflix: "netfliks", nvidia: "nvidiya", manchester: "mançester",
  chelsea: "çelsi", liverpool: "liverpul", barcelona: "barselona", juventus: "yuventus", psj: "pe-es-je",
  airways: "eyrveyz", online: "onlayn", show: "şou",
};
const DOMAIN_TLD = { com: "kom", gov: "qov", org: "orq", edu: "edu", net: "net", info: "info", io: "ay-o", ws: "ve-es" };
const ROMAN = { I: 1, V: 5, X: 10, L: 50, C: 100 };

// Sahib, 2026-11-24 («noyabrın 25-də» → «noyabrın iyirmibeşdə» oxuyur): az_text.py-dəki yeni qaydaların nüsxəsi.
const MONTHS_CI = MONTHS.map(m => `[${m[0].replace("i", "İ").toUpperCase()}${m[0]}]${m.slice(1)}`).join("|");
const MONTH_GEN = "(?:[Yy]anvarın|[Ff]evralın|[Mm]artın|[Aa]prelin|[Mm]ayın|[İi]yunun|[İi]yulun|[Aa]vqustun|[Ss]entyabrın|" +
  "[Oo]ktyabrın|[Nn]oyabrın|[Dd]ekabrın|[Aa]yın)";
const ORD_RE = /^(?:ci|cı|cu|cü|nci|ncı|ncu|ncü|inci|ıncı|uncu|üncü)$/u;
const YEAR_WORD = "il(?:in|də|dən|ədək|inə|ini|dir|ində|indən)?";
const YEAR_CASE = { da: "ildə", "də": "ildə", dan: "ildən", "dən": "ildən", "dək": "ilədək", "dakı": "ildəki", "dəki": "ildəki" };
const ABBR_AFTER = { "ş": "şəhəri", r: "rayonu", "küç": "küçəsi", pr: "prospekti", "qəs": "qəsəbəsi" };
const ABBR_BEFORE = { prof: "professor", dos: "dosent", akad: "akademik", dr: "doktor", st: "sent" };
const SQUARE = { km: "kvadrat kilometr", sm: "kvadrat santimetr", m: "kvadrat metr" };
const POWER = { kvt: "kilovat", mvt: "meqavat", qvt: "qiqavat" };
const ONSETS = new Set(["tr", "dr", "kr", "qr", "pr", "br", "fr", "st", "sp", "sk", "kl", "pl", "bl", "fl", "kv", "sm", "sn", "şt", "sv", "tv"]);
const has = (o, k) => Object.prototype.hasOwnProperty.call(o, k);

// Oxunuş lüğəti (ses-lugat.json və həftəlik əlavələr): worker.js özü gətirir. Əlavə əvvəl, əsas lüğət onun üstünə yazılır.
export const LEXICON = new Map();
export function setLexicon(...sources) {
  LEXICON.clear();
  for (const data of sources) {
    for (const [k, v] of Object.entries((data && data.sozler) || {})) {
      if (typeof v === "string" && v.trim() && [...v].every(c => ALLOWED.has(c))) LEXICON.set(k, v.trim());
    }
  }
  return LEXICON.size;
}

const W = String.raw`[\p{L}\p{N}_]`, B = `(?<!${W})`, E = `(?!${W})`;
const rx = (s, flags = "") => new RegExp(s, "gu" + flags);

export const lowerAz = s => s.replace(/I/g, "ı").replace(/İ/g, "i").toLowerCase();
const upperAz = s => s.replace(/i/g, "İ").replace(/ı/g, "I").toUpperCase();

function lexiconWord(token) {
  if (LEXICON.has(token)) return LEXICON.get(token);
  if (token.length > 1 && token === upperAz(token) && token !== lowerAz(token)) return LEXICON.get(token[0] + lowerAz(token.slice(1))) ?? null;
  return null;
}

function underThousand(n) {
  const h = Math.floor(n / 100), r = n % 100, t = Math.floor(r / 10), o = r % 10, words = [];
  if (h) words.push(...(h === 1 ? [] : [ONES[h]]), "yüz");
  if (t) words.push(TENS[t]);
  if (o) words.push(ONES[o]);
  return words;
}

export function numberWords(n) {
  if (n === 0) return "sıfır";
  const words = [];
  for (const [value, name] of SCALES) {
    const q = Math.floor(n / value);
    n %= value;
    if (q) words.push(...(q === 1 && name === "min" ? [] : numberWords(q).split(" ")), name);
  }
  words.push(...underThousand(n));
  return words.join(" ");
}

function ordinalWords(n) {
  const words = numberWords(n).split(" ");
  const last = words[words.length - 1];
  words[words.length - 1] = has(ORDINAL, last) ? ORDINAL[last] : last;
  return words.join(" ");
}

function decimalWords(whole, frac) {
  const denom = { 1: "onda", 2: "yüzdə", 3: "mində" }[frac.length];
  if (!denom) return numberWords(+whole) + " " + [...frac].map(d => numberWords(+d)).join(" ");
  return `${numberWords(+whole)} tam ${denom} ${numberWords(+frac)}`;
}

function lastVowel(word) {
  for (const ch of [...word].reverse()) if (VOWELS.has(ch)) return ch;
  return "ə";
}

const INVARIANT = ["ki", "kən", "dək", "sa", "sə", "ca", "cə"];

function harmonize(word, suffix) {
  if (INVARIANT.some(p => suffix.startsWith(p))) return suffix;
  let last = lastVowel(word), out = "";
  for (let ch of suffix) {
    if ("aə".includes(ch)) ch = BACK.has(last) ? "a" : "ə";
    else if ("ıiuü".includes(ch)) ch = { a: "ı", "ı": "ı", o: "u", u: "u", e: "i", "ə": "i", i: "i", "ö": "ü", "ü": "ü" }[last];
    if (VOWELS.has(ch)) last = ch;
    out += ch;
  }
  return out;
}

function attach(word, suffix, harmony = false) {
  suffix = lowerAz(suffix);
  if (!suffix) return word;
  const end = word.slice(-1);
  if (suffix.startsWith("dək")) {
    const dat = BACK.has(lastVowel(word)) ? "a" : "ə";
    return word + (VOWELS.has(end) ? "y" : "") + dat + suffix;
  }
  if (!VOWELS.has(end) && suffix.length > 1 && suffix[0] === "n" && VOWELS.has(suffix[1])) suffix = suffix.slice(1);
  else if (harmony && VOWELS.has(end) && "ıiuü".includes(suffix[0])) suffix = "n" + suffix;
  else if (VOWELS.has(end) && VOWELS.has(suffix[0])) suffix = "y" + suffix;
  return word + (harmony ? harmonize(word, suffix) : suffix);
}

function romanValue(s) {
  if (!s || [...s].some(c => !has(ROMAN, c))) return null;
  let total = 0, prev = 0;
  for (const c of [...s].reverse()) {
    const v = ROMAN[c];
    total = v < prev ? total - v : total + v;
    prev = Math.max(prev, v);
  }
  let canon = "", n = total;
  for (const [v, sym] of [[100, "C"], [90, "XC"], [50, "L"], [40, "XL"], [10, "X"], [9, "IX"], [5, "V"], [4, "IV"], [1, "I"]]) {
    while (n >= v) { canon += sym; n -= v; }
  }
  return canon === s && total > 0 && total < 40 ? total : null;
}

const spell = token => [...token].map(c => (has(LETTERS, c) ? LETTERS[c] : c)).join("-");

function pronounceable(word) {
  const chars = [...word], vowels = chars.filter(c => VOWELS.has(c)).length;
  if (!vowels) return false;
  let run = 0, best = 0;
  for (const c of chars) { run = VOWELS.has(c) ? 0 : run + 1; best = Math.max(best, run); }
  if (best >= 3 && vowels <= 1) return false;
  const onset = word.match(/^[^aıoueəiöü]+/u);
  return !(onset && onset[0].length >= 2 && !ONSETS.has(onset[0].slice(0, 2)));
}

function acronym(token) {
  const r = romanValue(token);
  if (r && token.length >= 2) return ordinalWords(r);
  const low = lowerAz(token);
  for (const key of [low, low.replace(/ı/g, "i")]) {
    if (has(ACRONYMS, key)) return ACRONYMS[key];
    if (has(FOREIGN, key)) return FOREIGN[key];
  }
  if (SHORT_WORDS.has(low)) return low;
  if (low.length <= 3 || !pronounceable(low)) return spell(low);
  return low;
}

function foreign(word) {
  const low = lowerAz(word);
  for (const key of [low, low.replace(/ı/g, "i")]) if (has(FOREIGN, key)) return FOREIGN[key];
  if (!low.includes("w")) return word;
  let s = low;
  for (const [a, b] of [["sh", "ş"], ["ch", "ç"], ["th", "t"], ["ph", "f"], ["ck", "k"], ["oo", "u"], ["ee", "i"], ["wh", "v"], ["w", "v"]]) s = s.split(a).join(b);
  return s;
}

function isForeign(word) {
  const low = lowerAz(word);
  return has(FOREIGN, low) || has(FOREIGN, low.replace(/ı/g, "i")) || low.includes("w");
}

const SUFFIX = String.raw`(?:-|[’'])([${LO}]+)${E}`;
const SUFFIX_START = new Set("dnlysıiuüaətc");
const NUMBER_WORDS = [...ONES, ...TENS, "yüz", "min", "milyon", "milyard", "trilyon", "sıfır"].filter(Boolean);

function glue(word, suffix, harmony = false) {
  if (SUFFIX_START.has(suffix.slice(0, 1)) && suffix.length <= 7 && !NUMBER_WORDS.some(w => suffix.startsWith(w))) return attach(word, suffix, harmony);
  return word + "-" + suffix;
}

function knownWord(word, suffix) {
  let said = lexiconWord(word);
  if (said == null && isForeign(word)) said = foreign(word);
  if (said == null) return null;
  return suffix ? glue(said, suffix, true) : said;
}

const GROUPED = new RegExp(String.raw`^\d{1,3}(?:[ ${SP}.]\d{3})+$`, "u");
function sayNumber(s) {
  let m = s.match(/^(\d{1,2}):(\d{2})$/u);
  if (m) return `${numberWords(+m[1])} ${+m[2] ? (+m[2] < 10 ? "sıfır " : "") + numberWords(+m[2]) : ""}`.trim();   // 14:05 → on dörd sıfır beş
  if (GROUPED.test(s)) return numberWords(+s.replace(new RegExp(`[ ${SP}.]`, "gu"), ""));
  m = s.match(/^(\d+)[.,](\d{1,3})$/u);
  if (m) return decimalWords(m[1], m[2]);
  return s.length <= 15 ? numberWords(+s) : [...s].map(d => numberWords(+d)).join(" ");
}

const ORD_SUFFIX = ORD_RE;
const MINUS = s => (s && "−-".includes(s) ? "mənfi " : "");

// Ayın günü mənsubiyyətlə (az_text.day_case): «beş» + «də» → «beşində», «iyirmi» + «dən» → «iyirmisindən», «otuz» + «u» → «otuzu».
const DAY_CASES = [[/^d[aə]$/u, "də"], [/^d[aə]k[ıi]$/u, "dəki"], [/^d[aə]n$/u, "dən"], [/^[aə]$/u, "ə"], [/^(?:[aə])?d[aə]k$/u, "ədək"], [/^[ıiuü]$/u, "i"], [/^[ıiuü]n$/u, "in"]];
export function dayCase(word, suffix) {
  const s = lowerAz(suffix), m = s.match(/^s?[ıiuü](?=n|$)/u), rest = m ? s.slice(m[0].length) : s;
  let kase;
  if (m && !rest) kase = "";
  else {
    const core = "ny".includes(rest.slice(0, 1)) && rest ? rest.slice(1) : rest;
    const hit = DAY_CASES.find(([re]) => re.test(core));
    if (!hit) return null;
    kase = hit[1];
  }
  const base = word + (VOWELS.has(word.slice(-1)) ? "s" : "") + harmonize(word, "i");
  if (!kase) return base;
  if (kase === "ədək") return base + harmonize(base, "nə") + "dək";
  return base + harmonize(base, "n" + kase);
}

function monthDay(m0, month, a, b, suffix) {
  const day = +(b || a);
  if (ORD_RE.test(lowerAz(suffix)) || day < 1 || day > 31) return m0;
  const said = dayCase(numberWords(day), suffix);
  if (said == null) return m0;
  return `${month} ${b ? numberWords(+a) + "-" : ""}${said}`;
}

function yearDate(m0, day, month, year, word, suffix) {
  if (word) return `${day} ${month} ${year}-ci ${word}`;
  if (suffix == null) return `${day} ${month} ${year}-ci il`;
  if (ORD_RE.test(lowerAz(suffix))) return m0;
  const il = has(YEAR_CASE, lowerAz(suffix)) ? YEAR_CASE[lowerAz(suffix)] : null;
  return il ? `${day} ${month} ${year}-ci ${il}` : m0;
}

function timeRange(m0, a, b, suffix, between) {
  if (between) return `${sayNumber(a)} ilə ${sayNumber(b)}`;
  return `${attach(sayNumber(a), "dan", true)} ${attach(sayNumber(b), suffix || "dək", true)}`;
}

const unit = (word, suffix) => (suffix ? glue(word, suffix, true) : word);

// Babək üçün fasilə yerləri (az_text.pauses): mötərizə və boşluqlu tire vergül olur, rəqəm aralığı toxunulmur.
export function pauses(text) {
  return String(text)
    .replace(/\s*[()]\s*/gu, ", ")
    .replace(/(?<![\d°%])\s+[–—-]\s+(?![\d+−-])/gu, ", ")
    .replace(/\s*,(?:\s*,)+/gu, ",")
    .replace(/\s*,\s*(?=[.!?…:;»”]|$)/gu, "")
    .replace(/(^|[.!?…:;]\s|[«“])\s*,\s*/gu, "$1")
    .trim();
}

const RULES = [
  [new RegExp(`[${SP}]`, "gu"), " "],
  [/\s*\[(?:…|\.\.\.)\]/gu, " "],
  [/(?:^|\s)Source\s*$/u, ""],
  [rx(String.raw`${B}və ([sb])\.(?=(\s+[${UP}]|\s*$)|)`), (m0, c, end) => (c === "s" ? "və sairə" : "və başqaları") + (end !== undefined ? "." : "")],
  [rx(String.raw`${B}([${UP}][${LO}]+) (ş|r|küç|pr|qəs)\.(?=(\s+[${UP}]|\s*$)|)`), (m0, w, a, end) => `${w} ${ABBR_AFTER[a]}${end !== undefined ? "." : ""}`],
  [rx(String.raw`${B}([Pp]rof|[Dd]os|[Aa]kad|[Dd]r|St)\.\s?(?=[${UP}])`), (m0, a) => ABBR_BEFORE[lowerAz(a)] + " "],
  [rx(String.raw`(?<=\d)(\s?)(mln|mlrd|min|kv|km|kq|sm|mm|ha)\.(?=\s+[${LO}\d])`), "$1$2"],
  [/(\d)\s?(km|sm|m)²/gu, (m0, d, u) => `${d} ${SQUARE[u]}`],
  [rx(String.raw`(\d)\s?kv\.?\s?(km|m)${E}`), (m0, d, u) => `${d} ${SQUARE[u]}`],
  [rx(String.raw`(\d)\s?m2${E}`), "$1 kvadrat metr"],
  [/(\d)\s?(sm|m)³/gu, (m0, d, u) => `${d} kub ${u === "sm" ? "santimetr" : "metr"}`],
  [rx(String.raw`(\d)\s?([kKmMqQ][Vv]t)(?:${SUFFIX})?(?![${LO}${UP}])`), (m0, d, u, suf) => `${d} ${unit(POWER[lowerAz(u)], suf)}`],
  [rx(String.raw`(\d)\s?(ha|m)(?:${SUFFIX})?(?=[\s,.;:!?)]|$)`), (m0, d, u, suf) => `${d} ${unit(u === "ha" ? "hektar" : "metr", suf)}`],
  [rx(String.raw`${B}(AZN|USD|EUR|azn|usd|eur|km|kq|kg|mln|mlrd|sm|mm)${E}(?:${SUFFIX})?`), (m0, u, suf) => unit(WORD_UNITS[u.toLowerCase()], suf)],
  [rx(String.raw`${B}(\d{1,2})[./](\d{1,2})[./](\d{4})${E}`), (m0, d, mo, y) => (+mo >= 1 && +mo <= 12 ? `${+d} ${MONTHS[+mo - 1]} ${y}` : m0)],
  [rx(String.raw`${B}(\d{1,2}) (${MONTHS_CI}) ((?:19|20)\d\d)(?!\d|[.,:]\d)(?:\s+(${YEAR_WORD})${E}|(?:-|[’'])([${LO}]+)${E})?`), yearDate],
  [rx(String.raw`${B}(${MONTH_GEN})\s+(\d{1,2})(?:\s?[-–]\s?(\d{1,2}))?(?:-|[’'])([${LO}]+)${E}`), monthDay],
  [/https?:\/\/\S+/gu, " "],
  [rx(String.raw`${B}([${LO}]{2,})\.([${UP}][${LO}A-Za-z0-9]+\.(?:az|com|ru|org|net|tr|info)${E})`), "$1. $2"],
  [rx(String.raw`${B}www\.`, "i"), ""],
  [rx(String.raw`${B}((?:[${LO}${UP}0-9-]+\.)+)(az|com|ru|org|net|gov|tr|edu|io|info|tv|uk|de|ge|ua|kz|ws|media)${E}(?:${SUFFIX})?`, "i"), (m0, labels, tld, suf) => {
    const said = [...labels.replace(/\.+$/u, "").split("."), tld].map(x => (has(DOMAIN_TLD, x.toLowerCase()) ? DOMAIN_TLD[x.toLowerCase()] : x)).join(" nöqtə ");
    return suf ? glue(said, suf, true) : said;
  }],
  [rx(String.raw`${B}([${UP}])\.\s?(?=[${UP}][${LO}])`), (m0, c) => spell(lowerAz(c)) + " "],
  [rx(String.raw`(?<=[${UP}${LO}A-Za-z])(?=\d)`), " "],
  [rx(String.raw`${B}(\d+)([${UP}${LO}]{3,})${E}`), (m0, n, w) => (ORD_SUFFIX.test(w) ? m0 : `${n} ${w}`)],
  [rx(String.raw`${B}(\d{1,3}(?:[ ${SP}]\d{3})+),(\d{1,3})${E}`), (m0, a, b) => decimalWords(a.replace(new RegExp(`[ ${SP}]`, "gu"), ""), b)],
  [rx(String.raw`${B}([${UP}${LO}A-Za-z]+)(?:${SUFFIX})?`), (m0, w, suf) => knownWord(w, suf) || m0],
  [rx(String.raw`(?<=[${LO}])(?=[${UP}])`), " "],
  [rx(String.raw`${B}([${UP}]{2,7})${SUFFIX}`), (m0, a, suf) => glue(acronym(a), suf, true)],
  [rx(String.raw`([+−-]?)(\d+)\s*°(?:\s*C${E})?\s*(?:…|\.\.\.|–|—|-)\s*([+−-]?)(\d+)\s*°(?:\s*C${E})?`), (m0, s1, a, s2, b) => `${MINUS(s1)}${a}-${MINUS(s2)}${b} dərəcə`],
  [rx(String.raw`(?<!${W})[−-](\d+)\s*°(?:\s*C${E})?`), "mənfi $1 dərəcə"],
  [rx(String.raw`\+?(\d+)\s*°(?:\s*C${E})?`), "$1 dərəcə"],
  [/%\s?(\d+(?:[.,]\d+)?)/gu, "$1%"],
  [rx(String.raw`(\d+(?:[.,]\d+)?)\s?%(?:${SUFFIX})?`), (m0, n, suf) => attach(sayNumber(n) + " faiz", suf || "")],
  [rx(String.raw`([$€£₼₽])\s?(\d[\d .,]*\d|\d)(\s?(?:milyon|milyard|trilyon|min)${E})?`), (m0, c, n, scale) => `${n}${scale || ""} ${c}`],
  [rx(String.raw`${B}(\d+)\s?-?\s?(?:ci|cı|cu|cü|nci|ncı|ncu|ncü|inci|ıncı|uncu|üncü)${E}`), (m0, n) => ordinalWords(+n)],
  [rx(String.raw`${B}(\d{1,2}:\d{2})\s?[-–—]\s?(\d{1,2}:\d{2})(?:${SUFFIX}|${E})(?=(\s+ara)|)`), timeRange],
  [rx(String.raw`${B}(\d{1,2}:\d{2}|\d{1,3}(?:[ ${SP}.]\d{3})+|\d+[.,]\d{1,3}|\d+)${SUFFIX}`), (m0, n, suf) => glue(sayNumber(n), suf, n.includes(":"))],
  [rx(String.raw`${B}(\d{1,2}):(\d{2})${E}`), m0 => sayNumber(m0)],
  [rx(String.raw`${B}\d{1,3}(?:[ ${SP}.]\d{3})+(?![.,]?\d)`), m0 => sayNumber(m0)],
  [rx(String.raw`${B}(\d+)[.,](\d{1,3})${E}`), (m0, a, b) => decimalWords(a, b)],
  [/\d+/gu, m0 => sayNumber(m0)],
  [/\s*([%₼$€£₽])/gu, (m0, c) => " " + UNITS[c]],
  [rx(String.raw`${B}(AZN|USD|EUR|azn|usd|eur|km|kq|kg|mln|mlrd|sm|mm)${E}`), (m0, u) => WORD_UNITS[u.toLowerCase()]],
  [rx(String.raw`\s*°\s*C${E}`), " dərəcə"],
  [/№/gu, " nömrə "],
  [/&/gu, " və "],
  [rx(String.raw`${B}[${UP}]{2,}${E}`), m0 => acronym(m0)],
];

// Rəqəmlər, tarixlər, saat, faiz, valyuta, sıra sayları, qısaltma, sayt adı, inisial və lüğət sözləri sözə çevrilir;
// böyük hərf və durğu qalır (az_text.verbalize ilə qayda-qayda eyni, eyni sıra ilə).
export function verbalize(text) {
  let t = String(text ?? "");
  for (const [re, to] of RULES) t = t.replace(re, to);
  return t;
}

// Saytın «Dinlə» səsi (Babək) üçün mətn (az_text.for_voice): durğu və böyük hərf intonasiya üçün qalır, sözün içindəki tire
// boşluq olur («a be şenin» — Whisper ölçməsində «a-be-şenin»-dən aydın).
export function forVoice(text, hyphens = false) {
  let t = verbalize(pauses(text ?? ""));
  if (!hyphens) t = t.replace(rx(String.raw`(?<=[${LO}])-(?=[${LO}])`), " ");
  return t.replace(/\s+/gu, " ").trim();
}
