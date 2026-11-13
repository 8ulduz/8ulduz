// 8ulduz — sayt kodu (build yoxdur; birbaşa GitHub Pages-də).
// Məlumat: data/*.json — updater.py yaradır.

/* ---- sabitlər */
const CATS = [
  { slug: "prezident", label: "Zuğulba Xronikası", description: "Prezident İlham Əliyev və Birinci xanım Mehriban Əliyevanın gündəliyi" },
  { slug: "sondeqiqe", label: "Son dəqiqə", description: "Son bir saatın xəbərləri" },
  { slug: "gundem", label: "Gündəm", description: "Günün əsas hadisələri" },
  { slug: "siyaset", label: "Siyasət", description: "Daxili və xarici siyasət" },
  { slug: "cemiyyet", label: "Cəmiyyət", description: "Sosial həyatdan xəbərlər" },
  { slug: "iqtisadiyyat", label: "İqtisadiyyat", description: "Bazar, maliyyə, enerji" },
  { slug: "dunya", label: "Dünya", description: "Beynəlxalq mətbuat" },
  { slug: "idman", label: "İdman", description: "İdman aləmindən xəbərlər və nəticələr" },
  { slug: "medeniyyet", label: "Mədəniyyət", description: "Kino, musiqi, sənət və mədəni həyat" },
  { slug: "heyat", label: "Sağlamlıq və həyat", description: "Tibb, sağlamlıq, qidalanma, psixologiya" },
  { slug: "sosial", label: "Sosial müdafiə", description: "Pensiya, müavinət, sosial yardım, əlillik, məşğulluq" },
  { slug: "bolgeler", label: "Bölgələr", description: "Rayonlardan və şəhərlərdən xəbərlər" },
  { slug: "tehsil", label: "Təhsil və elm", description: "Məktəb, universitet, elm, texnologiya" },
  { slug: "video", label: "Video", description: "Saytlardakı video xəbərlərə keçidlər" },
];
const SECTION_ALIAS = { sehiyye: "heyat", texnologiya: "tehsil" };
// Axtarış üçün statik səhifəli xidmətlər (updater.py, SERVICE_PAGES).
const SERVICE_ROUTES = { tixac: "traffic", valyuta: "rates", cedvel: "league" };
const LANGS = [
  { code: "az", label: "Azərbaycan dilində" }, { code: "tr", label: "Türkçe" },
  { code: "ru", label: "на русском языке" }, { code: "en", label: "in English" },
];
const LANG_BADGE = { az: "AZ", ru: "RUS", en: "ENG", tr: "TÜRK" };
const flag = inner => `<svg class="flag" viewBox="0 0 30 20" width="18" height="12" preserveAspectRatio="xMidYMid slice" aria-hidden="true">${inner}</svg>`; // slice: dil siyahısında dairəvi kəsilir
const STAR8 = "M21 7.2l.7 1.5 1.6-.6-.6 1.6 1.5.7-1.5.7.6 1.6-1.6-.6-.7 1.5-.7-1.5-1.6.6.6-1.6-1.5-.7 1.5-.7-.6-1.6 1.6.6z";
const FLAGS = {
  az: flag(`<rect width="30" height="20" fill="#ef3340"/><rect width="30" height="6.67" fill="#00b5e2"/><rect y="13.33" width="30" height="6.67" fill="#509e2f"/><circle cx="14" cy="10" r="3" fill="#fff"/><circle cx="15" cy="10" r="2.4" fill="#ef3340"/><path d="${STAR8}" fill="#fff" transform="translate(-3.2 -.2) scale(.97)"/>`),
  tr: flag(`<rect width="30" height="20" fill="#e30a17"/><circle cx="11.5" cy="10" r="5" fill="#fff"/><circle cx="12.8" cy="10" r="4" fill="#e30a17"/><path d="M19.5 10l-3.1 1 1.9-2.6v3.2l-1.9-2.6z" fill="#fff"/>`),
  ru: flag(`<rect width="30" height="20" fill="#fff"/><rect y="6.67" width="30" height="6.67" fill="#0039a6"/><rect y="13.33" width="30" height="6.67" fill="#d52b1e"/>`),
  en: flag(`<rect width="30" height="20" fill="#012169"/><path d="M0 0l30 20M30 0L0 20" stroke="#fff" stroke-width="4"/><path d="M0 0l30 20M30 0L0 20" stroke="#c8102e" stroke-width="1.6"/><path d="M15 0v20M0 10h30" stroke="#fff" stroke-width="6.5"/><path d="M15 0v20M0 10h30" stroke="#c8102e" stroke-width="4"/>`),
  us: flag(`<rect width="30" height="20" fill="#fff"/><path d="M0 1.5h30M0 4.6h30M0 7.7h30M0 10.8h30M0 13.9h30M0 17h30M0 20h30" stroke="#b22234" stroke-width="1.54"/><rect width="13" height="10.8" fill="#3c3b6e"/>`),
  cn: flag(`<rect width="30" height="20" fill="#de2910"/><path d="M7 3.2l1.3 4h4.2l-3.4 2.5 1.3 4L7 11.2l-3.4 2.5 1.3-4L1.5 7.2h4.2z" fill="#ffde00"/><circle cx="15" cy="3.5" r=".9" fill="#ffde00"/><circle cx="17.5" cy="6.5" r=".9" fill="#ffde00"/><circle cx="17.5" cy="10" r=".9" fill="#ffde00"/><circle cx="15" cy="13" r=".9" fill="#ffde00"/>`),
  eu: flag(`<rect width="30" height="20" fill="#039"/><circle cx="15" cy="10" r="5.6" fill="none" stroke="#fc0" stroke-width="1.7" stroke-dasharray="1.7 1.23"/>`),
};
const MARKET_ICON = { USD: FLAGS.us, EUR: FLAGS.eu, RUB100: FLAGS.ru, TRY100: FLAGS.tr, CNY: FLAGS.cn, BRENT: "🛢", WTI: "🛢", XAU: "🥇", XAG: "🥈", BTC: "₿" };
const marketIcon = id => MARKET_ICON[id] ? `<span class="mk-ic">${MARKET_ICON[id]}</span>` : "";
const GROUP_FLAG = { "Azərbaycan": FLAGS.az, "Türkiyə": FLAGS.tr, "Avropa": FLAGS.eu };
const PREZ_LINKS = [
  { name: "president.az", url: "https://president.az/az" },
  { name: "mehriban-aliyeva.az", url: "https://mehriban-aliyeva.az/" },
  { name: "X — @presidentaz", url: "https://x.com/presidentaz" },
];
// Rəsmi hesablar (president.az, mehriban-aliyeva.az).
const PROFILES = [
  { who: "İlham Əliyev", links: [
    ["X", "https://x.com/presidentaz"], ["X (AZ)", "https://x.com/azpresident"],
    ["Instagram", "https://www.instagram.com/presidentaz/"],
    ["Facebook", "https://www.facebook.com/PresidentIlhamAliyev"],
    ["YouTube", "https://www.youtube.com/@presidentaz"],
  ]},
  { who: "Mehriban Əliyeva", links: [
    ["X", "https://x.com/1VicePresident"],
    ["Instagram", "https://www.instagram.com/firstvicepresidentazerbaijan/"],
    ["Facebook", "https://www.facebook.com/FirstvicepresidentofAzerbaijanOfficial"],
    ["YouTube", "https://www.youtube.com/@FirstvicepresidentofAzerbaijan"],
  ]},
];
// «Araz» çaydır), sources: bu mövzunun idman saytı, not: bu söz varsa başqa mövzudur.
const SPORT_TEAMS = [
  { group: "Azərbaycan", items: [
    { name: "Qarabağ", keys: ["qarabağ", "qarabag", "qarabakh", "карабах"], not: ["dirçəliş", "universitet", "bərpa işləri", "yenidənqurma"] },
    { name: "Neftçi", keys: ["neftçi", "neftchi", "нефтчи"] },
    { name: "Sabah", keys: ["sabah fk", "сабах"], quoted: "sabah" },
    { name: "Zirə", keys: ["zirə", "зиря"] },
    { name: "Turan Tovuz", keys: ["turan tovuz", "туран товуз"], quoted: "turan" },
    { name: "Araz-Naxçıvan", keys: ["araz naxçıvan", "араз нахчыван"], quoted: "araz" },
    { name: "Milli komanda", keys: ["azərbaycan millisi", "azərbaycan yığması", "azərbaycan milli komandası", "milli komandamız", "millimiz", "сборная азербайджана", "сборной азербайджана", "сборную азербайджана"] },
  ] },
  { group: "Türkiyə", items: [
    { name: "Galatasaray", keys: ["galatasaray", "qalatasaray", "галатасара"] },
    { name: "Fenerbahçe", keys: ["fenerbahçe", "fənərbaxça", "fenerbaxça", "fənərbağça", "fənərbahça", "фенербахче"] },
    { name: "Beşiktaş", keys: ["beşiktaş", "бешикташ"] },
    { name: "Trabzonspor", keys: ["trabzonspor", "трабзонспор"] },
  ] },
  { group: "Avropa", items: [
    { name: "Real Madrid", keys: ["real madrid", "реал мадрид", "реал"], not: ["real betis", "real sociedad", "реал бетис", "реал сосьедад", "реал сарагоса"] },
    { name: "Barcelona", keys: ["barcelona", "barselona", "barça", "барселон"] },
    { name: "Man City", keys: ["manchester city", "man city", "mançester siti", "манчестер сити"] },
    { name: "Man United", keys: ["manchester united", "man united", "man utd", "mançester yunayted", "манчестер юнайтед", "мю"] },
    { name: "Liverpool", keys: ["liverpool", "liverpul", "ливерпул"] },
    { name: "Arsenal", keys: ["arsenal", "арсенал"], not: ["тульск", "арсенал тула", "нижнего новгорода"] },
    { name: "Chelsea", keys: ["chelsea", "çelsi", "челси"] },
    { name: "Bayern", keys: ["bayern", "bavariya", "бавари"] },
    { name: "İnter", keys: ["inter", "интер"], not: ["inter miami", "интер майами", "майами"] },
    { name: "Milan", keys: ["milan", "милан"], not: ["inter milan", "интер милан", "olimpia", "олимпия", "armani"] },
    { name: "Juventus", keys: ["juventus", "yuventus", "ювентус"] },
    { name: "PSG", keys: ["psg", "psj", "псж", "paris saint germain"] },
  ] },
];
// Alt bölmələr; groups: alt bölmə seçiləndə açılan düymələr.
const TRANSFER_WORDS = { stems: ["transfer", "трансфер"], keys: ["icarəyə verilib", "icarəyə götürüb", "перешел в", "перешёл в", "перейдет в", "перейдёт в", "арендован", "signs for", "joins on loan", "free agent", "kiraladı", "kiralık"] };
const TRANSFER_OTHER = ["voleybol", "volleyball", "волейбол", "həndbol", "handball", "гандбол", "хоккей", "hockey", "futzal", "formula 1", "tennis", "теннис", "ufc", "boks", "бокс", "pul transfer"];
const BASKET_WORDS = ["basketbol", "basketball", "баскетбол", " nba", " нба", "euroleague", "avroliqa", "евролиг"], BASKET_SITES = ["Sportando", "TalkBasket", "Eurohoops"];
const SPORT_TABS = [
  { name: "Transfer xəbərləri", ...TRANSFER_WORDS, not: TRANSFER_OTHER, groups: [{ group: "", items: [
    { name: "Futbol transferləri", label: "Futbol", ...TRANSFER_WORDS, not: [...TRANSFER_OTHER, ...BASKET_WORDS], skip: BASKET_SITES },
    { name: "Basketbol transferləri", label: "Basketbol", ...TRANSFER_WORDS, not: TRANSFER_OTHER, must: BASKET_WORDS, mustSites: BASKET_SITES },
  ] }] },
  { name: "Futbol", not: BASKET_WORDS, stems: ["futbol", "football", "soccer", "футбол"], keys: ["uefa", "fifa", "premyer liqa", "super liqa", "süper lig", "la liga", "bundesliqa", "bundesliga", "premier league", "champions league", "çempionlar liqası", "avropa liqası", "konfrans liqası", "лига чемпионов", "рпл", "апл"], sources: ["BBC Futbol", "Guardian Futbol"], groups: SPORT_TEAMS },
  { name: "Basketbol", stems: ["basketbol", "basketball", "баскетбол"], sources: ["Sportando", "TalkBasket"], groups: [{ group: "", items: [
    { name: "Avroliqa", keys: ["euroleague", "euroliga", "avroliqa", "евролиг"], sources: ["Eurohoops"] },
    { name: "NBA", keys: ["nba", "нба", "lakers", "celtics", "knicks", "warriors", "76ers", "bucks", "nuggets"] },
  ] }] },
    { name: "Formula 1", keys: ["formula 1", "formula one", "f1", "ф1", "формула 1", "формулы 1", "формуле 1", "qran pri", "grand prix", "гран при"], not: ["фигурн", "катан", "figure skating", "cüdo", "judo", "дзюдо", "boks", "бокс"], sources: ["Motorsport F1", "The Race", "F1News"] },
    { name: "Tennis", stems: ["tennis", "tenis", "теннис"], keys: ["atp", "wta", "wimbledon"], sources: ["BBC Tennis"] },
    { name: "Boks və UFC", stems: ["boks", "boxing", "бокс", "ufc", "mma"], sources: ["MMA Fighting"] },
    { name: "Güləş və cüdo", stems: ["güləş", "güreş", "cüdo", "judo", "wrestling", "дзюдо", "борец"], keys: ["вольная борьба", "вольной борьбе", "греко римская борьба"] },
    { name: "Şahmat", stems: ["şahmat", "satranç", "шахмат", "chess"], sources: ["Chess.com"] },
];
const CITIES = [["Bakı",40.4093,49.8671],["Sumqayıt",40.5897,49.6686],["Gəncə",40.6828,46.3606],["Mingəçevir",40.77,47.0286],["Şirvan",39.937,48.929],["Naxçıvan",39.2089,45.4122],["Lənkəran",38.7529,48.85],["Şəki",41.1919,47.1706],["Quba",41.3611,48.5133],["Xaçmaz",41.459,48.802],["Şamaxı",40.631,48.641],["İsmayıllı",40.785,48.15],["Qəbələ",40.98,47.86],["Oğuz",41.071,47.465],["Zaqatala",41.63,46.64],["Balakən",41.726,46.404],["Qax",41.418,46.92],["Şuşa",39.758,46.75],["Ağdam",39.993,46.93],["Füzuli",39.604,47.15],["Cəbrayıl",39.399,47.03],["Kəlbəcər",40.106,46.045],["Laçın",39.638,46.546],["Zəngilan",39.088,46.65],["Qubadlı",39.344,46.58],["Tovuz",40.992,45.628],["Göygöl",40.585,46.306],["Yevlax",40.617,47.15],["Bərdə",40.375,47.126],["Ağsu",40.57,48.4],["Kürdəmir",40.335,48.16],["Ucar",40.52,47.65],["Göyçay",40.65,47.74],["Ağdaş",40.65,47.48],["Zərdab",40.22,47.71],["İmişli",39.87,48.06],["Saatlı",39.93,48.37],["Sabirabad",40.01,48.48],["Salyan",39.596,49],["Neftçala",39.376,49.247],["Hacıqabul",40.04,48.94],["Biləsuvar",39.46,48.55],["Masallı",39.034,48.665],["Astara",38.501,48.875],["Lerik",38.775,48.415],["Yardımlı",38.908,48.24]];
const DAYS = ["bazar", "bazar ertəsi", "çərşənbə axşamı", "çərşənbə", "cümə axşamı", "cümə", "şənbə"];
const MONTHS = ["yanvar", "fevral", "mart", "aprel", "may", "iyun", "iyul", "avqust", "sentyabr", "oktyabr", "noyabr", "dekabr"];
const HOUR = 3600e3, DAY = 24 * HOUR;
const POLL_MS = 30e3;     // QIRMIZI XƏTT 1: lent dəqiqədə bir yazılır, sayt 30 saniyədən bir yoxlayır
const NEWS_FULL_MS = 10 * 60e3; // tam lent bu qədərdən bir; arada yalnız dilin latest faylı
const LATEST_MAX_MS = 90e3;     // status möhürü dəyişməsə də bu qədərdən bir latest.json yoxlanır
// Hər dəqiqə yeni sorğu açarı (Pages keşi)
let freshSequence = 0;
// Service worker-siz ziyarətçi də dəqiqəlik kanalı görsün (sw.js ilə eyni).
const LIVE_BASE = "https://raw.githubusercontent.com/8ulduz/8ulduz/live/m/";
const LIVE_FILE = /^data\/(?:status|latest(?:\.[a-z]{2})?|markets)\.json/;
let liveSkipUntil = 0;
const FS_STD = "4"; // standart şrift pilləsi (0–6): 4 = əvvəlki «A+ iki klik» (sahib, 2026-11-13); index.html-in ilk skriptindəki ilə eyni. xeber/ və bolme/ şablonları köhnə «2»-ni qoyur: orada pilləni applyPrefs() ilk çəkilişdən əvvəl düzəldir (test var)
async function liveDirect(url, signal, any) {
  if (!any && (navigator.serviceWorker?.controller || !LIVE_FILE.test(url)) || Date.now() < liveSkipUntil) return null;
  const name = url.split("?")[0].split("/").pop(), slot = Math.floor((Date.now() / 1000 - 45) / 60);
  for (const minute of [slot, slot - 1, slot - 2]) {
    try {
      const r = await fetch(LIVE_BASE + minute + "/" + name, {cache: "no-store", mode: "cors", credentials: "omit", signal});
      if (r.ok) return r;
      if (r.status === 403 || r.status === 429) liveSkipUntil = Date.now() + 5 * 60e3;
      if (r.status !== 404) return null;
    } catch { return null; }
  }
  liveSkipUntil = Date.now() + 60e3;
  return null;
}
// Sorğu açarı yalnız əllə yeniləmədə (?r=). Dəqiqəlik «?t=» hər faylı CDN-də «tapılmadı» edirdi (Fastly tam ünvanla keşləyir: +150–250 ms
// hər sorğuda — first, news, og, paylaş), halbuki Pages hər yayımda (10 dəq) keşi özü təmizləyir və dəqiqəlik təzəlik canlı kanaldan gəlir;
// yayım ilişsə sw.js pagesStuck (Last-Modified > 15 dəq) ehtiyat kanala keçir. Sahibin qərarı, 2026-11-09. Brauzer keşi yenə yoxdur (no-store).
const freshUrl = (path, force = false) => force ? `${path}?r=${Date.now()}-${++freshSequence}` : path;
async function requestJSON(url, {signal} = {}, timeoutMs = 12000) {
  const controller = new AbortController();
  let timer, cancel;
  const interrupted = new Promise((_, reject) => {
    cancel = () => { controller.abort(); reject(new Error("Sorğu dayandırıldı")); };
    timer = setTimeout(() => { controller.abort(); reject(new Error("Yenilənmə vaxtı bitdi. Yenidən yoxlayın.")); }, timeoutMs);
  });
  signal?.addEventListener("abort", cancel, {once:true});
  try {
    if(signal?.aborted)cancel();
    // index.html-in erkən sorğusu bir dəfə işlənir.
    const earlyKey = /[?&]r=/.test(url) ? null : Object.keys(globalThis.__early || {}).find(k => k.split("?")[0] === url.split("?")[0]);
    const early = earlyKey && globalThis.__early[earlyKey];
    if(early)delete globalThis.__early[earlyKey];
    const response = (async () => {
      const get = async () => (await liveDirect(url, controller.signal)) || fetch(url, {cache:"no-store", signal:controller.signal});
      const r = await (early ? early.catch(get) : get());
      if(!r.ok)throw new Error(`HTTP ${r.status}`);
      return {r, d:await r.json()};
    })();
    return await Promise.race([response, interrupted]);
  } finally { clearTimeout(timer); signal?.removeEventListener("abort", cancel); }
}
// Aktivlərin yolu app.js-in öz ünvanından.
// Səhifə kiçildilmiş app.min.js-i (oxucuya gedən nüsxə), köhnə xəbər səhifəsi isə app.js-i yükləyir: modullar hər ikisində eyni qovluqdan.
const ASSET = (document.querySelector('script[src*="assets/app"]')?.src || "./assets/app.js").replace(/app(?:\.min)?\.js.*$/, "");
const LOGO = `<img src="${ASSET}logo-80.png" alt="8ULDUZ" width="352" height="80" decoding="async">`; // ölçü atributda: şəkil gələnə qədər yer saxlanır (CSS hündürlüyü verir, en nisbətlə)
const PAGE = 48;          // bölmə səhifəsində bir dəfəyə göstərilən xəbər

// Məxfi rejimdə və yaddaş dolanda seçimlər heç olmasa açıq vərəqdə işləsin.
const sessionPrefs = new Map();
const storage = {
  getItem(key) {
    if (sessionPrefs.has(key)) return sessionPrefs.get(key);
    try { return localStorage.getItem(key); } catch { return null; }
  },
  setItem(key, value) {
    try { localStorage.setItem(key, value); sessionPrefs.delete(key); } catch { sessionPrefs.set(key, String(value)); }
  },
  removeItem(key) {
    try { localStorage.removeItem(key); sessionPrefs.delete(key); } catch { sessionPrefs.set(key, null); }
  },
};

/* ---- köməkçilər */
const $ = (s, r = document) => r.querySelector(s);
const optional = fn => { try { return fn(); } catch (e) { console.warn("blok göstərilmədi:", e); return ""; } };
const ESC = { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" };
const _dec = document.createElement("textarea");
function decode(s) {
  if (!s) return "";
  let cur = String(s);
  for (let i = 0; i < 3 && cur.indexOf("&") >= 0; i++) {
    _dec.innerHTML = cur;
    const next = _dec.value;
    if (next === cur) break;
    cur = next;
  }
  return cur;
}
function esc(s) { return String(s ?? "").replace(/[&<>"']/g, c => ESC[c]); }
const safeHref = u => { const s = String(u ?? "").trim(); return /^https?:\/\//i.test(s) ? esc(s) : "#"; };
function tidy(s) {
  return decode(s).replace(/\s*https?:\/\/\S+/gi, "").replace(/\u00a0/g, " ").replace(/\s+/g, " ").replace(/(?:\s*[-–—|])+\s*$/u, "").trim();
}
const txt = s => esc(tidy(s));
const catLabel = slug => CATS.find(c => c.slug === (SECTION_ALIAS[slug] || slug))?.label ?? slug;
function ago(iso) {
  const t = new Date(iso).getTime(); if (Number.isNaN(t)) return "";
  const m = Math.floor(Math.max(0, Date.now() - t) / 6e4);
  if (m < 1) return "indicə"; if (m < 60) return `${m} ${viewWidth() < 700 ? "dəq" : "dəqiqə"} əvvəl`;
  const h = Math.floor(m / 60); if (h < 24) return `${h} saat əvvəl`;
  const d = Math.floor(h / 24); return d < 30 ? `${d} gün əvvəl` : fullDate(iso);
}
function fullDate(iso) { const d = new Date(iso); return Number.isNaN(d.getTime()) ? "" : `${d.getDate()} ${MONTHS[d.getMonth()]} ${d.getFullYear()}`; }
function today() { const a = new Date(), r = `${DAYS[a.getDay()]}, ${a.getDate()} ${MONTHS[a.getMonth()]} ${a.getFullYear()}`; return r.charAt(0).toLocaleUpperCase("az") + r.slice(1); }
const FRESH_MS = 15 * 60e3; // «Son dəqiqə» nişanı və bildiriş: son 15 dəqiqə (əvvəl 1 saat idi, hər kart nişan alırdı)
const isFresh = a => { const age = Date.now() - new Date(a.publishedAt).getTime(); return age >= 0 && age < FRESH_MS; };
const withinHour = a => { const age = Date.now() - new Date(a.publishedAt).getTime(); return age >= 0 && age < HOUR; };
// Mənbə yeni vərəqədə açılır.
const TOUCH_UI = typeof matchMedia === "function" && matchMedia("(hover:none)").matches;
const OUT = `target="_blank" rel="noopener noreferrer"`;
const netErr = what => `<div class="err" role="alert">${what}. İnternet bağlantınızı yoxlayın. <button class="btn" data-act="retry">Yenidən yoxla</button></div>`;
function langOf(a) { if (a.lang) return a.lang; const s = a.title + " " + a.summary; return /[а-яА-Я]/.test(s) ? "ru" : /[əƏ]/.test(s) ? "az" : /[ığİ]/.test(s) ? "tr" : "az"; }
const flText = s => {
  s = lc(s);
  return s.includes("mehriban") || s.includes("məhriban") || s.includes("мехрибан")
    || s.includes("birinci xanım") || s.includes("birinci xanim") || s.includes("first lady")
    || s.includes("first vice-president") || s.includes("first vice president")
    || s.includes("birinci vitse-prezident") || s.includes("первой леди") || s.includes("первая леди");
};
// Nişan başlığa görədir.
const isFirstLady = a => !!a && flText(a.title);
// Birinci xanım.
const isFlItem = a => !!a && (a.source === "Mehriban Əliyeva" || flText(a.title));
const OFFICIAL_SRC = new Set(["Prezident.az", "Mehriban Əliyeva"]);
// Zuğulba: eyni xəbər bir kartdır.
const STATE_SRC = new Set(["AZƏRTAC", "AZƏRTAC (Regionlar)", "Cross Media", "Xalq qəzeti", "Azərbaycan qəzeti", "Yeni Azərbaycan", "Baku TV",
  "APA", "Report", "Trend", "Azernews", "Day.Az", "News.az", "Xezerxeber"]);
// Təyinat xəbərlərinə əlavə çəki.
const APPT_RX = /təyin (?:edil|olun)|vəzifə(?:sin|y)[əd]|(?:vəzifə(?:sin)?|iş)d[əa]n azad|назначен|освобожд[её]н от должности|appointed|dismissed/iu;
const isAppointment = a => APPT_RX.test(a?.title || "");
// Əsas blok: ən yenidən köhnəyə.
const PREZ_COUNT = 44, PREZ_FIRST_IMAGES = 8; // Sahibin qərarı: blokda həmişə 44 xəbər
// Lentə «prezident» sözü ilə yad xəbər də düşür.
const OUR_LEADERS = /ilham|i̇lham|əliyev|aliyev|алиев|birinci xan|birinci vitse|prezident\s+administ|azərbaycan\s+prezident|dövlət başçı/iu;
const FOREIGN_FL = /birinci xan[ıi]m(?:ı|ın|ına|ını|ında|ından|ının)(?!\p{L})/iu, AZ_CTX = /əliyev|aliyev|алиев|azərbaycan/iu;
const aboutOurLeaders = a => { const t = `${a.title || ""} ${a.summary || ""}`; return OUR_LEADERS.test(t) && !(FOREIGN_FL.test(t) && !AZ_CTX.test(t)); };
function prezHome(list, all = list) {
  const now = Date.now();
  const age = a => now - new Date(a.publishedAt).getTime();
  // Rəsmi mənbələr (STATE_SRC)
  const prez = list.filter(a => a.category === "prezident" && (OFFICIAL_SRC.has(a.source) || STATE_SRC.has(a.source)));
  // Rəsmi səhifələr limitsiz, digər mənbə ən çox 3 kart
  const perSrc = {};
  const capped = l => l.filter(a => OFFICIAL_SRC.has(a.source) || (perSrc[a.source] = (perSrc[a.source] || 0) + 1) <= 3);
  const president = capped(byDate(prez.filter(a => !isFlItem(a) && age(a) < 21 * DAY)));
  const lady = capped(byDate(prez.filter(a => isFlItem(a) && age(a) < 60 * DAY)));
  const head = 4;
  const ladyKeep = lady.length ? Math.min(lady.length, 2) : 0;
  const presHead = Math.min(president.length, head - ladyKeep);
  const ladyHead = Math.min(lady.length, head - presHead);
  const first = [...president.slice(0, presHead), ...lady.slice(0, ladyHead)];
  const rest = [...president.slice(presHead), ...lady.slice(ladyHead)];
  // 44 dolmursa: rəsmi saytlar, digər saytlar, sonda başqa dillər.
  const chosen = new Set([...first, ...rest].map(a => a.id)), take = l => l.filter(a => !chosen.has(a.id) && chosen.add(a.id));
  const ours = l => byDate(l.filter(a => a.category === "prezident" && aboutOurLeaders(a)));
  const own = [...first, ...rest, ...take(byDate(prez)), ...take(ours(list))].slice(0, PREZ_COUNT);
  return [...byDate(own), ...byDate(take(ours(all)).slice(0, PREZ_COUNT - own.length))];
}
const AT = new WeakMap(); // sətir → vaxt damğası: byDate hər müqayisədə new Date açırdı (4 100 sətirdə 14,5 → 7,6 ms, 2026-11-09); sıra eynidir
const atOf = a => { let m = AT.get(a); if (!m || m.at !== a.publishedAt) AT.set(a, m = { at: a.publishedAt, t: new Date(a.publishedAt).getTime() }); return m.t; };
const byDate = list => [...list].sort((x, y) => atOf(y) - atOf(x));
// Ən yenisi əvvəl: bütün publishedAt dəyərləri eyni ISO formatdadır (updater.py yazır, tests/kecid.test.cjs pinləyir) — sadə sətir
// müqayisəsi localeCompare ilə eyni sıranı verir, 3× tez.
const newest = (x, y) => { const a = x.publishedAt || "", b = y.publishedAt || ""; return a < b ? 1 : a > b ? -1 : 0; };
const lc = s => (s || "").toLocaleLowerCase("az");
const GROUP_MS = 36 * HOUR;
const GROUP_STOP = new Set("ve ile the and for from or bir bu da de ki veya icin olan və ilə də o üçün ya news xəbər xeber".split(/\s+/));
const normSeen = new Map();
function normTitle(s) {
  s ||= "";
  let v = normSeen.get(s);
  if (v === undefined) { if (normSeen.size > 8000) normSeen.clear(); normSeen.set(s, v = normTitleRaw(s)); }
  return v;
}
function normTitleRaw(s) {
  return s.toLowerCase().replace(/i̇/g, "i")
    .replace(/ə/g, "e").replace(/â/g, "a").replace(/ı/g, "i").replace(/î/g, "i").replace(/ö/g, "o").replace(/ü/g, "u").replace(/û/g, "u")
    .replace(/ş/g, "s").replace(/ç/g, "c").replace(/ğ/g, "g")
    .replace(/[^\p{L}\p{N}\s]/gu, " ").replace(/\s+/g, " ").trim();
}
function titleTokens(s) {
  return normTitle(s).split(" ").filter(t => t.length > 2 && !GROUP_STOP.has(t) && !/^\d+$/.test(t));
}
function shingles(toks) {
  if (toks.length < 3) return new Set(toks.length ? [toks.join(" ")] : []);
  const out = new Set();
  for (let i = 0; i <= toks.length - 3; i++) out.add(toks.slice(i, i + 3).join(" "));
  return out;
}
function jaccard(a, b) {
  if (!a.size || !b.size) return 0;
  let inter = 0;
  for (const x of a) if (b.has(x)) inter++;
  return inter / (a.size + b.size - inter);
}
function titlesSimilar(toks, sh, other, otherSh) {
  const A = new Set(toks), B = new Set(other);
  if (A.size < 3 || B.size < 3) return false;
  let inter = 0;
  for (const x of A) if (B.has(x)) inter++;
  const tj = jaccard(A, B), sj = jaccard(sh, otherSh);
  const shorter = A.size <= B.size ? A : B, longer = A.size <= B.size ? B : A;
  let contN = 0;
  for (const x of shorter) if (longer.has(x)) contN++;
  const cont = contN / shorter.size;
  const ratio = Math.min(A.size, B.size) / Math.max(A.size, B.size);
  if (inter >= 4 && tj >= 0.55) return true;
  if (inter >= 3 && (tj >= 0.75 || sj >= 0.45) && ratio >= 0.5) return true;
  if (cont >= 0.86 && inter >= 4 && ratio >= 0.62) return true;
  return false;
}
function preferPrimary(a, b) {
  // Rəsmi mənbə həmişə əsas kart olur.
  const ao = OFFICIAL_SRC.has(a.source), bo = OFFICIAL_SRC.has(b.source);
  if (ao !== bo) return ao ? a : b;
  if (!!a.imageUrl !== !!b.imageUrl) return a.imageUrl ? a : b;
  if ((a.summary || "").length !== (b.summary || "").length) return (a.summary || "").length > (b.summary || "").length ? a : b;
  return (a.publishedAt || "") >= (b.publishedAt || "") ? a : b;
}
// updater.py qruplamayıbsa, eyni qayda ilə brauzerdə birləşdir
function clusterArticles(list) {
  if (!list?.length || list.some(a => a.alts?.length)) return list;
  const prepared = list.map(a => {
    const dt = new Date(a.publishedAt).getTime();
    const toks = titleTokens(a.title);
    return { dt: Number.isNaN(dt) ? null : dt, toks, sh: shingles(toks), a };
  }).sort((x, y) => (y.dt ?? 0) - (x.dt ?? 0));
  const clusters = [];
  for (const item of prepared) {
    let placed = false;
    if (item.dt != null && item.toks.length >= 3) {
      for (const members of clusters) {
        const head = members[0].dt;
        if (head == null || Math.abs(item.dt - head) > GROUP_MS) continue;
        if (members.some(m => m.a.source === item.a.source)) continue;
        if (members.some(m => m.dt != null && Math.abs(item.dt - m.dt) <= GROUP_MS && titlesSimilar(item.toks, item.sh, m.toks, m.sh))) {
          members.push(item); placed = true; break;
        }
      }
    }
    if (!placed) clusters.push([item]);
  }
  const out = [];
  for (const members of clusters) {
    let primary = members[0].a;
    for (const m of members.slice(1)) primary = preferPrimary(primary, m.a);
    const alts = members.filter(m => m.a !== primary).map(m => ({ source: m.a.source, sourceUrl: m.a.sourceUrl, publishedAt: m.a.publishedAt, imageUrl: m.a.imageUrl || "" }));
    // Giriş sətri dəyişmir (preparedRow yaddaşında qalır): qrupun alt mənbələri nüsxəyə yazılır.
    out.push(alts.length ? {...primary, alts: alts.sort(newest)} : primary);
  }
  return out.sort(newest);
}
// Eyni keçid və ya 36 saat içində eyni başlıq: lent/arxiv qrupları da birləşir.
const DUP_META = new WeakMap();
function duplicateMeta(a) {
  let m = DUP_META.get(a);
  if (m && m.title === a.title && m.url === a.sourceUrl && m.at === a.publishedAt && m.alts === a.alts) return m;
  const entries = [a, ...a.alts || []];
  const keys = entries.map(x => ({key: normTitle(decode(x.title)).replace(/(?:\s+(?:foto(?:lar)?|video(?:lar)?|yenilenib))+$/, ""), dt: new Date(x.publishedAt || a.publishedAt).getTime()})).filter(x => x.key.length >= 12 && !Number.isNaN(x.dt));
  const urls = entries.map(x => x.sourceUrl?.replace(/^(https?:\/\/)www\./i, "$1")).filter(Boolean);
  DUP_META.set(a, m = {title: a.title, url: a.sourceUrl, at: a.publishedAt, alts: a.alts, keys, urls});
  return m;
}
function collapseExact(list) {
  const groups = [], byKey = new Map(), byUrl = new Map();
  const root = g => { while (g?.parent) g = g.parent; return g; };
  for (const a of list || []) {
    const {keys, urls} = duplicateMeta(a);
    const matches = new Set(urls.map(u => root(byUrl.get(u))).filter(Boolean));
    for (const {key, dt} of keys) {
      const same = byKey.get(key)?.find(x => Math.abs(x.dt - dt) <= GROUP_MS);
      if (same) matches.add(root(same.g));
    }
    let g = matches.values().next().value;
    if (!g) groups.push(g = { items: [] });
    for (const other of matches) if (other !== g) { g.items.push(...other.items); other.items = []; other.parent = g; }
    for (const {key, dt} of keys) { if (!byKey.has(key)) byKey.set(key, []); byKey.get(key).push({dt, g}); }
    g.items.push(a);
    for (const u of urls) byUrl.set(u, g);
  }
  const out = [];
  for (const g of groups) {
    if (!g.items.length) continue;
    let primary = g.items[0];
    for (const a of g.items.slice(1)) primary = preferPrimary(primary, a);
    primary = {...primary}; primary.n = primary.alts?.length; // serverdəki mənbə sayı: xəbərin öz səhifəsi (xeber/<id>/) ona görə yaranır
    const alts = [];
    const urls = new Set([primary.sourceUrl]), sources = new Set([primary.source]);
    const push = (src, url, publishedAt, imageUrl) => {
      if (!url || urls.has(url) || sources.has(src)) return;
      urls.add(url);
      sources.add(src);
      alts.push({ source: src, sourceUrl: url, publishedAt, imageUrl: imageUrl || "" });
    };
    for (const a of g.items) {
      if (a !== primary) push(a.source, a.sourceUrl, a.publishedAt, a.imageUrl);
      for (const alt of a.alts || []) push(alt.source, alt.sourceUrl, alt.publishedAt, alt.imageUrl);
    }
    if (alts.length) primary.alts = alts.sort(newest);
    else delete primary.alts;
    DUP_META.set(primary, {title: primary.title, url: primary.sourceUrl, at: primary.publishedAt, alts: primary.alts,
      keys: g.items.flatMap(a => duplicateMeta(a).keys), urls: g.items.flatMap(a => duplicateMeta(a).urls)});
    out.push(primary);
  }
  return out.sort(newest);
}
const detailUrl = a => `#/xeber/${encodeURIComponent(a.id)}${hourOf(a) && "?h=" + hourOf(a)}`;
const sourceName = name => `${esc(name)}<small class="source-count" data-source-count="${esc(name)}"></small>`;
// Həqiqi keçid yalnız səhifəsi olan xəbərə (updater.story_worthy: Azərbaycan dilində, 3+ mənbə və ya Zuğulba) — qalanı əvvəlki kimi
// tətbiqin içində: səhifəsiz ünvan Google-a 404 verərdi (sahib, 2026-11-11). Səhifə 10 dəqiqəlik dövrədə yaranır, ona görə xəbər ən azı
// 20 dəqiqədir layiq olmalıdır: həm kartın əsas xəbəri (nömrə onundur; yeni mənbə əsas olanda nömrə dəyişir), həm 3-cü mənbə
// 20 dəqiqədən köhnədir (Zuğulbada yalnız əsas xəbər). a.n — serverdəki mənbə sayı.
const hasPage = a => langOf(a) == "az" && Math.max(Date.parse(a.publishedAt), a.category == "prezident" ? 0 : a.n > 1 ? [a, ...a.alts].map(r => Date.parse(r.publishedAt)).sort()[2] : NaN) < Date.now() - 12e5;
const altBadge = a => a.alts?.length ? `<a class="bd out" href="${hasPage(a) ? `/xeber/${a.id}/` : detailUrl(a)}">${1 + a.alts.length} mənbə</a>` : "";
function altPop(a) {
  if (!a.alts?.length) return "";
  const rows = [a, ...a.alts].map(r => `<a href="${safeHref(r.sourceUrl)}" ${OUT}>${sourceName(r.source)}</a>`).join("");
  return `<details class="altpop"><summary class="bd gold">${1 + a.alts.length} mənbə</summary><div><template>${rows}</template></div></details>`;
}
const STAR = `<svg viewBox="0 0 32 32" width="18" height="18" aria-hidden="true"><g fill="currentColor"><rect x="9.5" y="9.5" width="13" height="13" rx="2"/><rect x="9.5" y="9.5" width="13" height="13" rx="2" transform="rotate(45 16 16)"/></g></svg>`;

// Nəticə xəbər obyekti üzrə saxlanır (publishNews hər dəfə yeni obyektlər yaradır; og dəyişəndə yaddaş sıfırlanır): bir çəkilişdə eyni xəbər 4–5 dəfə soruşulur.
let imgMemo = new WeakMap(), imgMemoOg = null;
function imageCandidates(a) {
  if (imgMemoOg !== S.og) { imgMemo = new WeakMap(); imgMemoOg = S.og; }
  const memo = a && typeof a === "object" ? imgMemo.get(a) : null;
  if (memo) return memo;
  const out = imageCandidatesRaw(a);
  if (a && typeof a === "object") imgMemo.set(a, out);
  return out;
}
function imageCandidatesRaw(a) {
  const values = [a?.imageUrl, S.og?.[a?.sourceUrl], ...(a?.alts || []).flatMap(x => [x.imageUrl, S.og?.[x.sourceUrl]])];
  // Qoşa ünvan düzəldilir.
  // Kəsilmiş kiçik şəkil sona.
  const all = [...new Set(values.filter(u => typeof u === "string").map(u => u.replace(/^https?:\/\/[^/]*?(https?:\/\/)/i, "$1")).filter(u => /^https?:\/\//i.test(u) && !/\/(?:resize\/?)?$|static\.president\.az\/assets\/president-administration-/i.test(u)))], cut = u => /_t\.\w+$|\/thumbs?\/|[?&]ratio=|\/fit\/\d/i.test(u);
  // Proksidən keçməyən sayt (PROXY_SKIP) sona.
  const blocked = u => PROXY_SKIP.test(hostOf(u));
  return [...all.filter(u => !cut(u) && !blocked(u)), ...all.filter(u => cut(u) && !blocked(u)), ...all.filter(blocked)];
}
function imgUrl(a) { return imageCandidates(a)[0] || ""; }
// xidmət işləmirsə (8 uğursuz cəhd) bu ziyarətdə birbaşa mənbədən.
const PROXY_MAX_FAILS = 8;
const PROXY_SKIP = /(?:^|\.)metbuat\.az$|(?:^|\.)goygol-ih\.gov\.az$|(?:^|\.)sporx\.com$|(?:^|\.)qafqazinfo\.az$|(?:^|\.)sportinfo\.az$/i;
const proxyBad = new Map();
// Proksidən keçməyən ünvan: sona düşür, əvvəlcədən yüklənmir.
const heavyImage = u => typeof u === "string" && !u.startsWith("https://wsrv.nl/") && (PROXY_SKIP.test(hostOf(u)) || (proxyBad.get(hostOf(u)) || 0) > 0);
function sized(url, width, logo) {
  const host = hostOf(url);
  if (!url || !host || (!logo && ((S.proxyFails || 0) >= PROXY_MAX_FAILS || (proxyBad.get(host) || 0) >= 2)) || PROXY_SKIP.test(host) || /\.(?:svg|gif)(?:[?#]|$)/i.test(url)) return url;
  return `https://wsrv.nl/?url=${encodeURIComponent(url)}&w=${width}&we&output=webp&q=70`;
}
// Ekranın eni bir dəfə oxunur: innerWidth hər oxunuşda məcburi yerləşdirmə edir (Chrome sürüşmə zolağını hesablayır), çəkiliş tapşırığında 4× telefonda 72–195 ms idi (2026-11-09 izi). resize-da yenilənir.
let viewW = globalThis.innerWidth || 0;
function viewWidth() { return viewW || (viewW = globalThis.innerWidth || 1200); }
addEventListener("resize", () => { viewW = globalThis.innerWidth || 1200; }, { passive: true });
// Slayderin ilk şəkli hər ekranda 640: hazır ilk ekran (prerender.cjs, telefon eni) 640 ilə gəlir və brauzer onu HTML-dən dərhal yükləyir;
// kompüterdə 800 istənəndə eyni şəkil ikinci dəfə yüklənirdi (2026-11-09 ölçüsü, Lighthouse kompüter: 2 wsrv sorğusu, LCP 2,5 s).
// Kompüterdə şəkil qutusu (.hero-main>.img: hündürlük ≤ 380 px, 16/9) 1× ekranda ≤ ~640 px-dir; qalan slaydlar kompüterdə elə 640-dır, telefonda 480.
function heroPicWidth(first) {
  return first || viewWidth() >= 900 ? 640 : 480;
}
function img(a, cls = "", eager = false, linked = false, width = 480, later = false) {
  const [url, ...rest] = imageCandidates(a);
  if (!url) return ""; // şəkilsiz xəbər qutu tutmur: kart yalnız mətndir
  const small = sized(url, width), others = small === url ? rest : [url, ...rest];
  const load = later ? "" : eager && !heavyImage(small) ? 'fetchpriority="high"' : 'loading="lazy"'; // ağır orijinal ilk ekranla yarışmır
  const src = `<img ${later ? "data-src" : "src"}="${esc(small)}" data-image-alternatives="${esc(JSON.stringify(others))}" alt="" ${load} decoding="async" referrerpolicy="no-referrer" data-fail="alt">`;
  const tag = linked ? "a" : "div";
  return `<${tag} class="img ${cls}"${linked ? ` href="${safeHref(a.sourceUrl)}" ${OUT} aria-label="${txt(a.title)}"` : ""}>${src}</${tag}>`;
}
function badges(a, withCat = true, alt = "span") {
  const more = !a.alts?.length ? "" : alt === "pop" ? altPop(a) : altBadge(a);
  return `<div class="badges">${withCat ? `<span class="bd" data-cat="${esc(a.category)}"><i class="cdot"></i>${esc(catLabel(a.category))}</span>` : ""}${more}${a.video ? `<span class="bd red">▶ Video</span>` : ""}${a.lang && !S.lang ? `<span class="bd out">${esc(LANG_BADGE[a.lang] ?? a.lang.toUpperCase())}</span>` : ""}</div>`;
}
function shownSource(a) {
  try {
    const host = new URL(a.sourceUrl || "").hostname.replace(/^www\./, "");
    if (host === "sesqazeti.az") return "Sesqazeti.az";
  } catch {}
  return a.source || "";
}
const plainName = s => String(s ?? "").toLocaleLowerCase("az").replace(/[^\p{L}\p{N}]+/gu, "");
const ownAuthor = a => { const w = plainName(a.author); return !!w && ![a.source, shownSource(a), hostOf(a.sourceUrl)].some(n => plainName(n) === w); }; // müəllif mənbənin öz adıdırsa təkrar yazılmır
const meta = a => `<div class="meta"><a class="src" href="${safeHref(a.sourceUrl)}" ${OUT}>${sourceName(shownSource(a))}${ownAuthor(a) ? `<span class="muted"> · ${txt(a.author)}</span>` : ""}</a><time datetime="${esc(a.publishedAt)}">${ago(a.publishedAt)}</time><span class="acts">${shareBtn(a)}</span></div>`;
// Paylaşma keçidi: www.8ulduz.az (Worker) og səhifəni hər dəqiqə verir, oxucunu dərhal sayta keçirir (docs/x-worker.md); b bölmə, h saat (arxiv.cjs hourOf). 2026-11-09-a qədər x.8ulduz.az idi — sahib: saytın adı ilə qarışmasın.
const hourOf = a => (String(a.publishedAt || "").match(/^20(\d\d)-(\d\d)-(\d\d)T(\d\d)/) || []).slice(1).join("");
const shareUrl = (a, h = hourOf(a)) => /^[0-9a-f]{16}$/.test(a.id) ? `https://www.8ulduz.az/${a.id}${h && "?h=" + h}` : `https://8ulduz.az/#/xeber/${encodeURIComponent(a.id)}?b=${encodeURIComponent(a.category || "")}${h && "&h=" + h}`;
const SHARE_TO = { fb: ["Facebook", u => `https://www.facebook.com/sharer/sharer.php?u=${u}`], x: ["X", (u, t) => `https://x.com/intent/post?url=${u}&text=${t}`], wa: ["WhatsApp", (u, t) => `https://wa.me/?text=${t}%0A${u}`], tg: ["Telegram", (u, t) => `https://t.me/share/url?url=${u}&text=${t}`], in: ["LinkedIn", u => `https://www.linkedin.com/sharing/share-offsite/?url=${u}`], mail: ["E-poçt", (u, t) => `mailto:?subject=${t}&body=${t}%0A${u}`] };
// Şəbəkə işarələri sprite-dadır (sosial.svg).
const shIcon = k => `<svg aria-hidden="true"><use href="${ASSET}sosial.svg#${k}"/></svg>`;
const APP_PKG = [[/(?:^|\.)(?:x|twitter)\.com$/, "com.twitter.android"], [/(?:^|\.)facebook\.com$/, "com.facebook.katana"], [/(?:^|\.)instagram\.com$/, "com.instagram.android"], [/(?:^|\.)(?:youtube\.com|youtu\.be)$/, "com.google.android.youtube"], [/^wa\.me$|whatsapp\.com$/, "com.whatsapp"], [/^t\.me$/, "org.telegram.messenger"]];
function appLink(u, pkg, extra = "") {
  if (!/Android/.test(navigator.userAgent || "")) return "";
  try { const x = new URL(u); pkg = x.protocol === "https:" && (pkg || APP_PKG.find(([re]) => re.test(x.hostname))?.[1]); return pkg ? `intent://${x.host}${x.pathname}${x.search}#Intent;scheme=https;package=${pkg};${extra}S.browser_fallback_url=${encodeURIComponent(u)};end` : ""; } catch { return ""; }
}
function openOut(u) { const i = appLink(u); if (i) location.href = i; else window.open(u, "_blank", "noopener,noreferrer"); }
// CCT: geri sayta qayıdır.
const chromeLink = u => appLink(u, "com.android.chrome", "S.android.support.customtabs.extra.SESSION=;");
const shareBtn = a => safeHref(a.sourceUrl) === "#" ? "" : `<button type="button" class="share" data-act="dinle" data-id="${esc(a.id)}">${S.dinOn === a.id ? "■ Bitir" : "Dinlə"}</button><button type="button" class="share" data-act="share" data-share="${esc(shareUrl(a))}" title="Paylaş">Paylaş</button>`;
const starBtn = a => { const on = isSaved(a.id), label = on ? "Saxlanmışlardan çıxar" : "Yadda saxla"; return `<span class="star${on ? " on" : ""}" data-act="star" data-save="${esc(a.id)}" role="button" tabindex="0" aria-pressed="${on ? "true" : "false"}" title="${label}" aria-label="${label}"><span aria-hidden="true">${on ? "★" : "☆"}</span></span>`; };
const card = a => cardAt(a, "h3");
function cardAt(a, hx, cls = "") { const pic = img(a, "", false, true, 360); return `<article class="card${cls}${pic ? "" : " noimg"}" data-cat="${esc(a.category)}">${starBtn(a)}${pic}<div class="b">${badges(a, route().name !== "section", "pop")}<a class="card-hit" href="${safeHref(a.sourceUrl)}" ${OUT}><${hx} lang="${esc(langOf(a))}">${txt(a.title)}</${hx}></a>${meta(a)}</div></article>`; }

// Şəkli sınan slayd çıxarılır.
function dropHeroSlide(slide) {
  const row = slide.parentElement;
  const strip = slide.closest(".strip");
  const section = slide.closest(".hero");
  const width = row?.clientWidth || 0;
  const index = row ? [...row.children].indexOf(slide) : -1;
  const showing = width > 0 && index >= 0 && Math.round(row.scrollLeft / width) === index;
  slide.remove();
  const left = row ? [...row.children] : [];
  if (!left.length) { section?.remove(); return; }
  if (showing) row.scrollLeft = Math.min(index, left.length - 1) * width;
  if (strip) setupStrips([strip]);
  setupHeroImages();
}
const imgFail = el => {
  if (!el?.isConnected) return;
  el.style.visibility = "hidden"; // qırıq ikon görünməsin, növbəti ünvan yoxlanana qədər
  if (String(el.src || "").startsWith("https://wsrv.nl/")) { // cəza yalnız orijinal açılanda (aşağıda)
    let rest0 = []; try { rest0 = JSON.parse(el.dataset.imageAlternatives || "[]"); } catch {}
    const origin = rest0.find(u => typeof u === "string" && !u.includes("wsrv.nl"));
    const host = hostOf(origin || "");
    el.addEventListener("load", () => { if (el.src.startsWith("https://wsrv.nl/")) return; S.proxyFails = (S.proxyFails || 0) + 1; if (host) proxyBad.set(host, (proxyBad.get(host) || 0) + 1); }, { once: true });
  }
  let rest = [];
  try { rest = JSON.parse(el.dataset.imageAlternatives || "[]"); } catch {}
  const next = rest.find(u => typeof u === "string" && u && u !== el.src);
  if (next) {
    el.dataset.imageAlternatives = JSON.stringify(rest.slice(rest.indexOf(next) + 1));
    el.src = next;
    return;
  }
  const slide = el.closest(".hero-main");
  if (slide) { dropHeroSlide(slide); return; }
  const photo = el.closest(".phrow > a");
  if (photo) { photo.remove(); return; }
  const card = el.closest(".card, .pcard");
  const box = el.closest(".img");
  el.remove();
  if (card) card.classList.add("noimg");
  box?.remove();
};
// Şəkil xətası tutma mərhələsində.
// Ölçü CSS-də sabitdir.
document.addEventListener("load", (e) => { const t = e.target; if (t?.tagName === "IMG" && t.dataset?.fail === "alt") { if ((t.naturalWidth || 0) < 2) imgFail(t); else t.style.visibility = ""; } }, true);
document.addEventListener("error", (e) => { const t = e.target, f = t?.dataset?.fail; f === "alt" ? imgFail(t) : f === "rm" ? t.remove() : f === "hide" && t.style && (t.style.visibility = "hidden"); }, true);

/* ---- vəziyyət */
const LANG_KEY = "8ulduz-lang"; // standart: "az"; "" = Hamısı
function savedLang() { const v = storage.getItem(LANG_KEY); if (v === "") return null; return LANGS.some(l => l.code === v) ? v : "az"; }
const S = { sports: null, data: null, error: null, offline: false, lastSync: null, lang: savedLang(), club: null, q: "", shown: PAGE, etag: null, markets: null, social: null, status: null, og: null, video: null, football: null, pray: null, prayOpen: false, warn: [], fxOpen: false, fxFrom: "USD", fxTo: "AZN", fxAmt: 100, wx: null, wxAll: null, wxSel: null, wxOpen: false, ads: null, tixOn: false, tixArea: "merkez", tixUser: false, geo: null, geoBusy: false, geoErr: null };
const HIJRI_AZ = ["", "Məhərrəm", "Səfər", "Rəbiüləvvəl", "Rəbiülaxır", "Cümadəl-ula", "Cümadəl-axır", "Rəcəb", "Şaban", "Ramazan", "Şəvval", "Zilqədə", "Zilhiccə"];
const PRAY_ORDER = [["Fajr", "Sübh"], ["Sunrise", "Günəş"], ["Dhuhr", "Zöhr"], ["Asr", "Əsr"], ["Maghrib", "Məğrib"], ["Isha", "İşa"]];
// Tıxac səhifəsi aşağıdakı ROAD_RULES ilə süzülür.
const HAVA_RE = /hava xəbərdar|güclü külək|güclü yağış|şaxta|çovğun|dolu yağ|yağış xəbərdar|(?:^|[^\p{L}])sel(?:[^\p{L}]|$)/iu;
const TRAFFIC_AREAS = [
  { id: "merkez", label: "Bakı mərkəz", lat: 40.4093, lon: 49.8671, zoom: 12 },
  { id: "sumqayit", label: "Sumqayıt yolu", lat: 40.482, lon: 49.835, zoom: 13 },
  { id: "hava", label: "Hava limanı yolu", lat: 40.45, lon: 50.0, zoom: 13 },
  { id: "abseron", label: "Abşeron", lat: 40.45, lon: 49.95, zoom: 11 },
];
const ROAD_RULES = [
  { icon: "💥", kind: "qeza", re: /qəza(?!lı)/iu },
  { icon: "🚧", kind: "bagli", re: /(?:yol|küçə|prospekt|körpü|tunel|şose)\p{L}{0,6}\s*bağlan|bağlan\p{L}{0,8}\s+(?:yol|küçə|prospekt)|yol bağlı|hərəkət\p{L}{0,4}\s+məhdudlaş|(?:yol|küçə|prospekt|körpü|tunel|şose)\p{L}{0,8}.{0,40}təmir|təmir.{0,32}(?:yol|küçə|prospekt|körpü|tunel|şose)/iu },
  { icon: "🚦", kind: "tixac", re: /tıxac/iu },
  { icon: "🚇", kind: "metro", re: /metro|avtobus/iu },
  { icon: "🌧", kind: "hava", re: HAVA_RE },
];
const ROAD_FALLBACK = /(?:^|[^\p{L}])(?:BNA|DYP)(?:[^\p{L}]|$)|yol polisi|nəqliyyatın hərəkət|avtomobil yol/iu;
function roadKind(title) {
  const t = lc(decode(title || "")); // \w yalnız ASCII-dir, /iu isə I↔ı, İ↔i-ni qatlamır: «küçələr bağlanacaq», «TIXAC» tutulmurdu
  for (const r of ROAD_RULES) if (r.re.test(t)) return r;
  if (ROAD_FALLBACK.test(t)) return { icon: "🚦", kind: "yol" };
  return null;
}
function roadItems(list) {
  return (list || []).filter(a => (a.lang ?? "az") === (S.lang || "az")).flatMap(a => {
    const k = roadKind(a.title);
    return k ? [{ ...a, icon: k.icon, kind: k.kind }] : [];
  }).sort((a, b) => new Date(b.publishedAt) - new Date(a.publishedAt));
}
function localRoadItems(list) {
  const local = /bakı|bakinin|bakının|abşeron|abseron|sumqayıt|sumqayit|hey[dər]+ əliyev prospekt|hava limanı yolu/iu;
  const unrelated = /qatar|dəmir yolu|helikopter|təyyarə|başsağlığı|təbrik/iu;
  return roadItems(list).filter(a => {
    const age = Date.now() - new Date(a.publishedAt).getTime();
    const t = lc(a.title);
    return age >= 0 && age < 2 * HOUR && local.test(t) && !unrelated.test(t);
  });
}
const geoArea = () => S.geo?.lat != null ? { id: "konum", label: "📍 Konumum", lat: S.geo.lat, lon: S.geo.lon, zoom: 13 } : null;
function tixArea() {
  const konum = geoArea();
  if (konum && (S.tixArea === "konum" || !S.tixUser)) return konum;
  return TRAFFIC_AREAS.find(a => a.id === S.tixArea) || TRAFFIC_AREAS[0];
}
function wazeSrc(a) { return `https://embed.waze.com/iframe?zoom=${a.zoom}&lat=${a.lat}&lon=${a.lon}`; }
function wazeLive(a) { return `https://www.waze.com/live-map?ll=${a.lat},${a.lon}&zoom=${a.zoom}`; }
function wazeApp(a) { return `https://www.waze.com/ul?ll=${a.lat}%2C${a.lon}&zoom=${a.zoom}`; }
function yandexSrc(a) { return `https://yandex.com/map-widget/v1/?ll=${a.lon}%2C${a.lat}&z=${a.zoom}&l=map%2Ctrf&lang=en_US`; }
function bakuClock(date = new Date()) {
  const b = new Date(date.getTime() + 4 * HOUR);
  return { wd: ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"][b.getUTCDay()], hour: b.getUTCHours() };
}
function bakuRush(date = new Date()) {
  const { wd, hour } = bakuClock(date);
  return ["Mon", "Tue", "Wed", "Thu", "Fri"].includes(wd) && ((hour >= 8 && hour < 10) || (hour >= 17 && hour < 20));
}
function roadFresh(a) {
  if (a.kind !== "qeza" && a.kind !== "bagli") return false;
  const t = new Date(a.publishedAt).getTime();
  if (Number.isNaN(t)) return false;
  const age = Date.now() - t;
  return age >= -5 * 60e3 && age < HOUR;
}
function roadHot(list) { return bakuRush() || roadItems(list.filter(a => Date.now() - new Date(a.publishedAt) < HOUR)).some(roadFresh); }
// Tam lent gələnədək (açılış, yeniləmə: ilk ekranın faylında yol xəbərləri yoxdur) nöqtə sönüb ~1,5 s sonra yenidən yanırdı (sahib 2026-11-13, video):
// son vəziyyət yaddaşdan, ən çoxu bir saat (yol xəbərinin öz ömrü).
const TIX_KEY = "8ulduz-tix";
function syncTixDot() {
  let hot = roadHot(S.data?.articles || []);
  if (!S.data || S.partial) hot ||= Date.now() - storage.getItem(TIX_KEY) < HOUR;
  else if (hot !== S.tixHot) storage.setItem(TIX_KEY, (S.tixHot = hot) ? Date.now() : 0);
  document.querySelectorAll(".tix-btn").forEach(el => {
    el.classList.toggle("hot", hot);
    el.setAttribute("aria-label", hot ? "Tıxac — pik saat və ya yol hadisəsi" : "Tıxac və yollar");
    el.title = hot ? "Pik saat və ya təzə yol hadisəsi — xəritəyə baxın" : "Tıxac və yollar";
  });
}
const SAVE_KEY = "8ulduz-saved";
// Hər kartın ☆ düyməsi (isSaved) bu siyahını istəyir: tam lentdə 1000+ dəfə JSON açmaq əvəzinə mətn və silinmə siyahısı dəyişməyibsə eyni nəticə qaytarılır. Çağıranlar siyahını dəyişmir (filter/some).
let savedRaw = null, savedRem = -1, savedCache = [];
function savedList() {
  try {
    const raw = storage.getItem(SAVE_KEY) || "[]", rem = removedIds.size + removedUrls.size + removedKeys.size;
    if (raw === savedRaw && rem === savedRem) return savedCache;
    const v = JSON.parse(raw);
    savedRaw = raw; savedRem = rem;
    return savedCache = Array.isArray(v) ? v.filter(a => !removedArticle(a)) : [];
  } catch { return []; }
}
function isSaved(id) { return savedList().some(x => x.id === id); }
function toggleSave(a) {
  const rest = savedList().filter(x => x.id !== a.id);
  if (!isSaved(a.id)) rest.unshift({ id: a.id, title: a.title, source: a.source, sourceUrl: a.sourceUrl, publishedAt: a.publishedAt, category: a.category, imageUrl: a.imageUrl || "" });
  storage.setItem(SAVE_KEY, JSON.stringify(rest.slice(0, 200)));
}
const HOME_FIXED = new Set(["video", "prezident", "sondeqiqe"]);
const SECT_KEY = "8ulduz-sects";
const NOTIFY_KEY = "8ulduz-notify";
const SEEN_KEY = "8ulduz-seen";
function sectionPool() { return CATS.filter(c => !HOME_FIXED.has(c.slug)); }
function sectionPref() {
  const slugs = sectionPool().map(c => c.slug);
  let raw = null;
  try { raw = JSON.parse(storage.getItem(SECT_KEY) || "null"); } catch {}
  let order = Array.isArray(raw?.order) ? raw.order.filter(s => slugs.includes(s)) : slugs.slice();
  for (const s of slugs) if (!order.includes(s)) order.push(s);
  const off = (Array.isArray(raw?.off) ? raw.off : []).filter(s => slugs.includes(s));
  return { order, off };
}
function writeSects(order, off) { storage.setItem(SECT_KEY, JSON.stringify({ order, off })); }
function homeCats() {
  const { order, off } = sectionPref();
  const hide = new Set(off);
  return order.filter(s => !hide.has(s)).map(s => CATS.find(c => c.slug === s)).filter(Boolean);
}
function notifyOn() { return storage.getItem(NOTIFY_KEY) === "1" && "Notification" in window && Notification.permission === "granted"; }
function checkBreaking(articles) {
  if (!notifyOn()) return;
  tellWorkerLang();
  const fresh = (articles || []).filter(isFresh);
  let seen = null;
  try { seen = JSON.parse(storage.getItem(SEEN_KEY) || "null"); } catch {}
  if (!Array.isArray(seen)) {
    storage.setItem(SEEN_KEY, JSON.stringify(fresh.map(a => a.id)));
    return;
  }
  const known = new Set(seen);
  // Bildiriş seçilmiş dildədir; «görülmüş» siyahı bütün dillərdir.
  const novel = filtered(fresh).filter(a => a.id && !known.has(a.id)).slice(0, 3);
  for (const a of novel) showBreaking(a);
  storage.setItem(SEEN_KEY, JSON.stringify(fresh.map(a => a.id)));
}
function tellWorkerLang() { try { navigator.serviceWorker?.controller?.postMessage({ type: "notify-lang", lang: S.lang || "" }); } catch {} }
// Android-də new Notification xəta verir: əvvəl service worker.
async function showBreaking(a) {
  const options = { body: decode(a.title), icon: "./assets/icon-192.png", tag: "break-" + a.id };
  try {
    if (S.swReg?.showNotification) {
      await S.swReg.showNotification("Son dəqiqə", { ...options, data: { id: a.id, cat: a.category || "", url: shareUrl(a) } }); // klik saytın xəbər səhifəsinə aparır, mənbəyə yox
      return;
    }
  } catch {}
  try {
    const n = new Notification("Son dəqiqə", options);
    n.onclick = () => { window.focus(); location.hash = detailUrl(a); }; // saytın öz xəbər səhifəsi
  } catch {}
}
async function armNotify() {
  if (!("Notification" in window)) return;
  let perm = Notification.permission;
  if (perm === "default") { try { perm = await Notification.requestPermission(); } catch { perm = "denied"; } }
  if (perm !== "granted") { storage.removeItem(NOTIFY_KEY); renderTicker(); return; }
  storage.setItem(NOTIFY_KEY, "1");
  tellWorkerLang();
  storage.setItem(SEEN_KEY, JSON.stringify((S.data?.articles || []).filter(isFresh).map(a => a.id)));
  showBreaking({ id: "on", title: "Bildiriş aktivdir: yeni son dəqiqə xəbəri çıxanda bu cür görünəcək.", sourceUrl: "" }); // aktiv edən kimi nəticə görünsün
  try {
    const reg = await navigator.serviceWorker.ready;
    if (reg.periodicSync) await reg.periodicSync.register("breaking", { minInterval: 5 * 60 * 1000 });
  } catch {}
  renderTicker();
}
function adSlots() { return (S.ads?.slots || []).filter(s => s && s.image && s.link); }
function adHtml() {
  const slots = adSlots();
  if (!slots.length) return "";
  const s = slots[Math.floor(Date.now() / 30000) % slots.length];
  return `<section class="ad ad-live" aria-label="Reklam"><a href="${safeHref(s.link)}" target="_blank" rel="sponsored noopener noreferrer"><img src="${esc(s.image)}" alt="${esc(s.alt || "Reklam")}" loading="lazy" decoding="async"></a></section>`;
}
// QIRMIZI XƏTT 2: server qapısından sonra ikinci yoxlama.
const POLICY = globalThis.CONTENT_POLICY;
const removedIds = new Set(), removedUrls = new Set(), removedKeys = new Set(), removedHosts = [];
// Hazır sətirlərin yaddaşı (preparedRow): xam sətir obyekti → 0/1 hazır sətir. Qayda dəyişəndə (çıxarılan xəbər, ölü keçid, og) sıfırlanır.
let PREP = new WeakMap(), prepOg = null;
function addRemovals(rows) {
  const before = removedIds.size + removedUrls.size + removedKeys.size;
  for (const r of Object.values(rows || {})) {
    if (!r || typeof r !== "object") continue;
    const list = k => Array.isArray(r[k]) ? r[k].filter(v => typeof v === "string") : [];
    for (const id of [r.id, ...list("ids")]) if (id) removedIds.add(id);
    for (const u of list("urls")) removedUrls.add(u);
    for (const k of [r.key, ...list("keys")]) if (typeof k === "string") { removedKeys.add(k); const h = k.split("#")[0]; if (k.includes("#") && !removedHosts.includes(h)) removedHosts.push(h); }
  }
  const changed = before !== removedIds.size + removedUrls.size + removedKeys.size;
  if (changed) PREP = new WeakMap(); // çıxarılan xəbər hazır sətirdə qalmasın
  return changed;
}
addRemovals(POLICY?.removedArticles);
function removedArticle(a) {
  if (removedIds.has(a.id) || removedUrls.has(a.sourceUrl)) return true;
  if (!removedHosts.some(h => String(a.sourceUrl || "").includes(h))) return false;
  try { const u = new URL(a.sourceUrl), n = [...u.pathname.matchAll(/(?:\/|[-_])(\d{5,})(?=\.html?|\/|$)/g)].map(m => m[1]).filter(n => !/^(?:19|20)\d{6}$/.test(n)); return !!n.length && removedKeys.has(u.hostname.toLowerCase().replace(/^www\./, "") + "#" + n.at(-1)); } catch { return false; }
}
const policyRx = src => { try { return src ? new RegExp(src, "i") : null; } catch { return null; } };
const POLICY_AZ = policyRx(POLICY?.azTerms), POLICY_LEADER = policyRx(POLICY?.leaderTerms);
// JS i bayrağı İ/ı-ni qatlamır: kiçik hərfli mətn də yoxlanır.
const policyTest = (rx, text) => !!rx && (rx.test(text) || rx.test(text.toLocaleLowerCase("az")));
const hostOf = url => (/^[a-z][\w+.-]*:\/\/(?:[^@/?#]*@)?([^/?#:]+)/i.exec(url || "")?.[1] || "").toLowerCase().replace(/^www\./, "");
const onHost = (host, list) => list.some(d => host === d || host.endsWith("." + d));
function sourceForbidden(a) {
  if (removedArticle(a)) return true;
  if (!POLICY) return false;
  const host = hostOf(a.sourceUrl), domains = POLICY.azSources[a.source] || POLICY.worldSources[a.source];
  return !/^https?:\/\//i.test(String(a.sourceUrl ?? "")) || onHost(host, POLICY.blockedHosts) || !domains || !onHost(host, domains);
}
function policyViolation(a) {
  if (sourceForbidden(a)) return true;
  if (!POLICY?.worldSources[a.source]) return false;
  const text = `${a.title || ""} ${a.summary || ""}`;
  const sport = a.category === "idman" && (POLICY.sportSources || []).includes(a.source);
  return policyTest(sport ? POLICY_LEADER : POLICY_AZ, text);
}
function altForbidden(a, alt) {
  if (removedSource(alt) || sourceForbidden(alt)) return true;
  if (!POLICY?.worldSources[alt.source]) return false;
  if (policyViolation({ ...alt, category: a.category, summary: "" })) return true;
  if (a.category === "idman" && (POLICY.sportSources || []).includes(alt.source)) return false;
  return policyTest(POLICY_AZ, `${a.title || ""} ${a.summary || ""}`);
}
function removedSource(a) {
  if (["azadlıq", "azadliq", "azadliq.org"].includes(String(a.source || a.name || "").toLocaleLowerCase("az"))) return true;
  const host = hostOf(a.sourceUrl || a.url); return host === "azadliq.org" || host.endsWith(".azadliq.org");
}
const byId = new Map();
const urlsOf = list => new Set(list.flatMap(a => [a.sourceUrl, ...(a.alts || []).map(alt => alt.sourceUrl)]));

/* ---- məlumat */
async function loadNews(force = false) {
  if (S.newsLoading && !force) return;
  S.newsAbort?.abort();
  const controller = S.newsAbort = new AbortController();
  const token = S.newsToken = (S.newsToken || 0) + 1;
  const statusStamp = S.status?.checkedAt || null;
  S.newsLoading = true;
  renderTopbar();
  // İlk ekran çəkilənə qədər tam lent xətti tutmur.
  if (S.firstReady) { const wait = S.firstReady; S.firstReady = null; await wait; }
  // İlk ekran görünürsə tam lent əsas axın boşalanda gəlir (ən gec 2 s).
  if (S.partial && !force && token === S.newsToken) await new Promise(r => idle(r, 300, 2000));
  // og.json (55 KB gzip) tam lenti gözlətmir (2026-11-09): sətirlərin şəkli updater (apply_og_cache) ilə artıq içindədir, ilk ekranın
  // xəritəsi first.json-dadır; xəritə lentdən sonra boş anda gəlir (loadOg) və yalnız şəkil qazanan sətir varsa lent yenidən çəkilir.
  try {
    if (S.lang !== "az" && !S.status) await loadStatus(); // dil faylı varmı: status deyir (azərbaycanca həmişə news.json)
    if (token !== S.newsToken) return;
    const {r, d, tag} = await newsJSON(force, controller.signal);
    if(token !== S.newsToken)return;
    if (!Array.isArray(d.articles)) throw new Error("Xəbər məlumatının quruluşu yanlışdır");
    S.offline = r.headers.get("X-8ulduz-data") === "cache";
    if (tag && tag === S.etag && S.data) {
      if (!S.offline) S.lastSync = new Date();
      S.newsStamp = statusStamp; S.newsCheckedAt = Date.now();
      S.error = null; renderTopbar(); return;
    }
    if (!S.offline) S.lastSync = new Date();
    S.error = null;
    if (S.data && !S.partial && S.data.updatedAt === d.updatedAt && S.og) { S.etag = tag; S.newsStamp = statusStamp; S.newsCheckedAt = Date.now(); renderTopbar(); return; }
    S.og ||= {};
    if(token !== S.newsToken || controller.signal.aborted)return;
    const first = !S.data, partial = S.partial;
    S.partial = false;
    // main 10 dəqiqədən bir yazılır.
    const inFull = urlsOf(d.articles);
    S.overlay = (S.overlay || []).filter(o => !inFull.has(o.a.sourceUrl) && Date.now() - o.at < 30 * 60e3);
    S.rawNews = [...S.overlay.map(o => o.a), ...d.articles]; S.rawMeta = {...d, articles: undefined}; S.fromCache = false;
    S.etag = tag; S.newsStamp = statusStamp; S.newsCheckedAt = Date.now();
    publishNews();
    if (first || partial) S.firstRenderAt = Date.now(); // ilk ekrandan sonra bir dəfə yenilənir: dəqiqəlik xəbərlər də gələndə
    if (!first && !partial) idle(() => loadOg(), 1500, 8000); // og xəritəsi 30 dəqiqədə bir, lentdən sonra
    // İlk ekrandan tam lentə: dəyişməyən bloklar qalır.
    if (first || force || (partial && readerBusy())) render(); else requestRender();
    if (!partial) backY();
  } catch (e) { if(token === S.newsToken){ S.error = String(e); S.offline = !navigator.onLine; if (!S.data || S.partial) render(); else renderTopbar(); } }
  finally { if(token === S.newsToken){S.newsLoading = false; S.newsAbort = null; renderTopbar();} }
}

// İlk ekran (data/first.json): baş səhifə və bölmə, azərbaycanca.
const firstScreen = () => route().name === "home" && !S.q && S.lang === "az";
// Bölmə keçidi: tam lenti (223 KB) gözləmək telefonda 3–6 s idi.
const partialOk = () => firstScreen() || route().name === "section" && S.lang === "az";
// İlk çəkiliş slayder şəklini gözləyir (LCP), ən çox 1,5 s.
function heroPainted() {
  const im = route().name === "home" && $("#view .pre-skel[data-prerender] .hero-main img[src]");
  if (!im) return Promise.resolve();
  return new Promise(ok => {
    const go = () => setTimeout(ok, document.hidden ? 0 : 40); // rAF yox: arxa vərəqdə heç gəlmir, səhifə boş qalırdı
    if (im.complete) go(); else { im.addEventListener("load", go, { once: true }); im.addEventListener("error", go, { once: true }); }
    setTimeout(ok, 1500);
  });
}
async function loadFirst() {
  if (!partialOk()) return;
  try {
    const {d} = await requestJSON(freshUrl("data/first.json"), {}, 5000);
    if (!Array.isArray(d?.articles) || !d.articles.length) return;
    keepFirst(d);
    const lat = await S.latestCache; // keşdəki dəqiqəlik lent (loadCached): şəbəkə keşi qabaqlasa da yeni sətirlər itmir
    if (S.rawNews && !S.fromCache) return; // tam lent daha tez gəlib
    // Keşdəki nüsxə ilə eyni yayımdırsa (updatedAt mikrosaniyəyə qədər eynidir) ikinci çəkiliş yoxdur: eyni HTML-i yenidən qurub
    // müqayisə etmək telefonda ~0,7 s uzun iş idi (4×; yayımdan sonra yenidən açılış, 10 dəqiqə içində qayıdış). Tam lent (loadNews) yenə gəlir.
    if (S.fromCache && d.updatedAt && d.updatedAt === S.rawMeta?.updatedAt) {
      S.fromCache = false; S.og = d.og || S.og || {};
      if (!S.cachedShown) { S.cachedShown = true; await heroPainted(); S.firstRenderAt = Date.now(); render(); } // keşdəki hələ çəkilməyibsə (kadr gözləyirdi) indi
      return;
    }
    S.partial = true; S.fromCache = false;
    S.og = d.og || S.og || {};
    const has = urlsOf(d.articles), top = S.overlay?.length ? S.overlay.filter(o => !has.has(o.a.sourceUrl)).map(o => o.a) : cachedTop(lat, d); // keşdəki dəqiqəlik sətirlər qalır
    S.overlay = top.map(a => ({a, at: Date.now()}));
    S.rawNews = [...top, ...d.articles]; S.rawMeta = {...d, articles: undefined};
    publishNews();
    await heroPainted();
    S.firstRenderAt = Date.now();
    render();
    await new Promise(done => setTimeout(done));
  } catch {}
}

// İşçi (sw.js) səhifəni hələ idarə etmirsə — ilk ziyarət, qeydiyyat ilk ekrandan sonradır — ilk ekranın faylı növbəti açılış üçün
// səhifənin özü tərəfindən saxlanır (loadCached oxuyur, eyni açar: sorğusuz yol). İşçi idarə edəndə bunu networkFirstData yazır.
// Boş anda: JSON.stringify ~6 ms (1×). Əvvəl ikinci ziyarət də keşsiz başlayırdı (2026-11-09).
function keepFirst(d) {
  if (typeof caches === "undefined" || navigator.serviceWorker?.controller) return;
  idle(() => {
    try {
      const key = new URL("data/first.json", new URL(ASSET.replace(/assets\/$/, ""), location.href)).href;
      caches.open("8ulduz-data").then(c => c.put(key, new Response(JSON.stringify(d), { headers: { "Content-Type": "application/json; charset=utf-8" } }))).catch(() => {});
    } catch {}
  }, 1500, 5000);
}
// Keşdəki dəqiqəlik lent (sahib 2026-11-13, video: yeniləyəndə son xəbərlər ~1,5 s itib köhnə siyahı görünür, sonra qayıdırdı): ilk ekranın
// faylı 10 dəqiqəlikdir, ondan sonra çıxan sətirlər yalnız latest-dədir. İşçi onu da saxlayır; ilk ekrandan köhnə deyilsə yeni sətirləri üstə qoyulur.
function cachedTop(lat, d) {
  const base = Date.parse(d.updatedAt), has = urlsOf(d.articles);
  return Array.isArray(lat?.articles) && Date.parse(lat.updatedAt) >= base - 60e3 ? lat.articles.filter(a => !has.has(a.sourceUrl) && Date.parse(a.publishedAt) > base - 10 * 60e3).slice(0, 40) : [];
}
async function loadCached() {
  if (!partialOk() || typeof caches === "undefined" || S.rawNews) return;
  let gotLatest; S.latestCache = new Promise(ok => { gotLatest = ok; });
  try {
    const keys = await caches.keys(), key = keys.find(k => k === "8ulduz-data") || keys.find(k => k.startsWith("8ulduz-data-")); // v142-dən versiyasız ad; köhnəsi keçid üçün
    if (!key) return;
    const cache = await caches.open(key);
    const root = new URL(ASSET.replace(/assets\/$/, ""), location.href);
    const hit = (await cache.match(new URL("data/first.json", root).href)) || (await cache.match(new URL("data/news.json", root).href));
    const lat = hit && await ((await cache.match(new URL("data/latest.az.json", root).href)) || (await cache.match(new URL("data/latest.json", root).href)))?.json().catch(() => null);
    gotLatest(lat);
    if (!hit || S.rawNews) return;
    const d = await hit.json();
    if (!Array.isArray(d?.articles) || !d.articles.length || S.rawNews) return;
    // Hazır ilk ekran (index.html — təkrar açılışda işçinin saxladığı nüsxə) keşdəki lentlə eyni yayımdandırsa və ya təzədirsə, keşdəkini çəkməyə
    // dəyməz: ekranda artıq o məzmun var, şəbəkə nüsxəsi gəlir (çəkiliş ilk kadrı 1×-də ~50 ms gecikdirirdi, A/B 2026-11-09).
    const top = cachedTop(lat, d);
    const pre = route().name === "home" && $("#view .pre-skel[data-prerender]")?.dataset?.prerender;
    if (!top.length && pre && d.updatedAt && Date.parse(d.updatedAt) <= Date.parse(pre)) return;
    S.partial = true; S.fromCache = true;
    S.og ||= d.og || {};
    S.overlay = top.map(a => ({a, at: Date.now()}));
    S.rawNews = [...top, ...d.articles]; S.rawMeta = {...d, articles: undefined};
    publishNews();
    await new Promise(done => afterFrame(done)); // əvvəl hazır ilk ekran boyansın (FCP), keşdəki ondan sonra
    if (S.rawNews?.at(-1) !== d.articles.at(-1) || !S.fromCache || S.cachedShown) return; // arada şəbəkə nüsxəsi gəlib: onu çəkən var
    S.cachedShown = true;
    render();
    S.firstRenderAt = Date.now(); // sonrakı çəkilişlər FIRST_RENDER_HOLD_MS gözləyir (şəbəkədən eyni yayım gəlsə ikinci çəkiliş olmur)
  } catch {} finally { gotLatest(null); }
}

// Xam sətirdən hazır sətir: bölmə adı, og şəkli, mənbə qaydası (QIRMIZI XƏTT 2: policyViolation), alt mənbələrin süzgəci, ölü keçidin əvəzi —
// 0 və ya 1 sətirlik massiv, açar sırası əvvəlki boru xətti ilə eynidir (tests/speed-guard.test.cjs bayt-bayt tutuşdurur). Nəticə xam sətir
// obyekti üzrə yaddaşda qalır: dəqiqəlik lent hər dəfə ~1 100 sətrin hamısını yenidən klonlayıb yoxlayırdı (1×-də 40–46 ms, telefonda ~180 ms),
// üstəlik yeni obyektlər DUP_META-nı boşa çıxarırdı. Yaddaş yalnız dəyişməyən sətir üçündür: yeni gələn hər sətir (yeni obyekt) qaydadan keçir.
// Sıfırlanır: S.og dəyişəndə (publishNews), addRemovals yeni çıxarılan tapanda, ölü keçid siyahısı dəyişəndə və şəkli sonradan tapılan sətirdə (loadLatest).
function preparedRow(a) {
  const hit = PREP.get(a);
  if (hit) return hit;
  const row = {...a, category: SECTION_ALIAS[a.category] || a.category, imageUrl: a.imageUrl || S.og?.[a.sourceUrl] || a.imageUrl};
  let out = [];
  if (!removedSource(row) && !policyViolation(row)) {
    const b = {...row, alts: (row.alts || []).filter(alt => !altForbidden(row, alt))};
    if (!S.deadLinks?.size) out = [b];
    else { // Linki 404 verən xəbər.
      const alts = b.alts.filter(alt => !S.deadLinks.has(alt.sourceUrl));
      if (!S.deadLinks.has(b.sourceUrl)) out = [{...b, alts}];
      else if (alts.length) { const [next, ...rest] = alts; out = [{...b, source: next.source, sourceUrl: next.sourceUrl, publishedAt: next.publishedAt || b.publishedAt, title: next.title || b.title, lang: next.lang || b.lang, imageUrl: b.imageUrl || next.imageUrl, alts: rest}]; }
    }
  }
  PREP.set(a, out);
  return out;
}
// Xam lentdən ekrandakı lent: qayda, birləşdirmə, şəkillər; xam siyahı dəyişmir.
function publishNews() {
  const d = {...S.rawMeta};
  if (prepOg !== S.og) { PREP = new WeakMap(); prepOg = S.og; }
  d.articles = collapseExact(clusterArticles(S.rawNews.flatMap(preparedRow)));
  // Şəkil yoxdursa digər mənbədən.
  for (const a of d.articles) {
    if (a.imageUrl || !a.alts?.length) continue;
    const alt = a.alts.find(x => x.imageUrl) || a.alts.find(x => S.og?.[x.sourceUrl]);
    if (alt) a.imageUrl = alt.imageUrl || S.og?.[alt.sourceUrl];
  }
  S.data = d; byId.clear(); for (const a of d.articles) byId.set(a.id, a);
  if (!S.partial) checkBreaking(d.articles);
  primeHeroImage(d.articles);
}
function primeHeroImage(articles) {
  if (route().name !== "home" || S.q) return;
  const a = heroPick((articles || []).filter(x => (S.lang ? langOf(x) === S.lang : true) && x.category !== "prezident" && imgUrl(x)), 1)[0];
  const href = a && sized(imageCandidates(a)[0], heroPicWidth(true));
  if (!href || heavyImage(href) || S.lcpHref === href) return; // ağır orijinal əvvəlcədən yüklənmir
  S.lcpHref = href;
  const head = document.head;
  if (!head?.querySelector || !head.appendChild) return;
  let link = head.querySelector("link[data-lcp]");
  if (!link) { link = document.createElement("link"); link.rel = "preload"; link.as = "image"; link.dataset.lcp = "1"; }
  link.href = href; link.fetchPriority = "high";
  if (!link.isConnected) head.appendChild(link); // href əvvəl, sonra sənədə: boş href xəbərdarlığı olmasın
}

function readerBusy() {
  if ($(".follow-dialog[open]")) return true;
  if ((S.sy ??= globalThis.scrollY || 0) > 400 || Date.now() - (S.touchAt || 0) < 8000) return true; // son 8 saniyədə toxunub, çevirib və ya yazıb: oxuyur, ekran gözləyir
  if ($("#view iframe, #view details.altpop[open]")) return true;
  return !!document.activeElement?.closest?.("#view input, #view select, #view textarea");
}
const RENDER_GAP_MS = 400, FIRST_RENDER_HOLD_MS = 2500;
function armBusy(ms, n = 0) { clearTimeout(S.busyT); S.busyT = setTimeout(() => { if (!S.renderPending) return; if (!readerBusy()) requestRender(S.renderWhole); else if (n < 300) armBusy(2000, n + 1); }, ms); S.busyT?.unref?.(); }
function requestRender(whole = true) {
  S.renderWhole ||= whole;
  if (readerBusy()) { S.renderPending = true; syncNewPill(); armBusy(8500); return; }
  S.renderPending = false; S.pendingNew = 0; syncNewPill();
  if (!S.data) return; // xəbərlər gələndə birinci çəkiliş hamısını götürür
  if (S.renderQueued) return;
  S.renderQueued = true;
  S.renderTimer = setTimeout(flushRender, Math.max(RENDER_GAP_MS, (S.firstRenderAt || 0) + FIRST_RENDER_HOLD_MS - Date.now()));
}
function flushRender() {
  clearTimeout(S.renderTimer);
  if (!S.renderQueued) return;
  const all = S.renderWhole;
  S.renderQueued = false; S.renderWhole = false;
  if (all) render(); else renderView();
}
function syncNewPill() {
  const pill = $("#newpill");
  if (!pill) return;
  // Sahib 2026-11-07: yalnız olduğun bölmənin (alt düymənin) xəbərləri.
  const r = route(), c = r.name === "section" && CATS.find(c => c.slug === r.slug), rows = S.pendingNew || [];
  const mine = r.name === "home" ? rows : c ? rows.filter(a => (r.slug === "sondeqiqe" || (r.slug === "video" ? a.video : a.category === r.slug)) && (!S.club || clubMatches(a, S.club))) : [];
  pill.hidden = !mine.length;
  pill.textContent = `↑ ${mine.length} yeni ${c ? (S.club || c.label) + " xəbəri" : "xəbər"}`;
}
// Dəqiqəlik lent dil üzrə.
async function latestJSON(force) {
  if (S.lang && S.status?.langs?.includes(S.lang)) {
    try {
      const got = await requestJSON(freshUrl(`data/latest.${S.lang}.json`, force), {}, 8000);
      if (Array.isArray(got.d?.articles) && got.r.headers?.get?.("X-8ulduz-data") !== "cache") return got;
    } catch {}
  }
  return requestJSON(freshUrl("data/latest.json", force), {}, 8000);
}
async function newsJSON(force, signal) {
  const file = code => requestJSON(freshUrl(`data/news${code ? "." + code : ""}.json`, force), {signal}), tagOf = got => got.r.headers.get("etag") || got.r.headers.get("last-modified") || "";
  const langs = S.status?.newsLangs || [];
  if (uiLang(S.lang) && langs.includes(S.lang)) { try { const own = await file(S.lang); return {...own, tag: tagOf(own) || null}; } catch (e) { if (signal?.aborted) throw e; } }
  const [main, ...more] = await Promise.all([file(), ...(S.lang ? [] : langs).map(code => file(code).catch(() => null))]), rows = main.d?.articles, tags = [tagOf(main)];
  for (const got of more) if (Array.isArray(rows) && Array.isArray(got?.d?.articles)) {
    const seen = new Set(rows.map(a => a.sourceUrl));
    rows.push(...got.d.articles.filter(a => !seen.has(a.sourceUrl))); tags.push(tagOf(got));
  }
  return {...main, tag: tags.some(Boolean) ? tags.join("|") : null};
}
// Dəqiqəlik axın: oxucu məşğuldursa «N yeni xəbər» düyməsi.
async function loadLatest(force = false) {
  if (S.latestLoading || !S.rawNews) return;
  S.latestLoading = true;
  const statusStamp = S.status?.checkedAt || null;
  try {
    const {r, d} = await latestJSON(force);
    if (!Array.isArray(d?.articles)) return;
    S.offline = r.headers?.get?.("X-8ulduz-data") === "cache";
    if (!S.offline) { S.lastSync = new Date(); S.error = null; }
    S.newsStamp = statusStamp; S.latestAt = Date.now();
    if (addRemovals(d.removed)) { publishNews(); renderView(); renderTicker(); }
    const dead = new Set(d.dead || []), deadChanged = dead.size !== (S.deadLinks?.size || 0) || [...dead].some(u => !S.deadLinks.has(u));
    S.deadLinks = dead;
    if (deadChanged) PREP = new WeakMap(); // ölü keçidin əvəzi hazır sətirdədir
    const known = urlsOf(S.rawNews);
    const fresh = d.articles.filter(a => !known.has(a.sourceUrl));
    // Xəbər şəkilsiz gəlib, şəkli yavaş prosesdən sonra tapılıb.
    const byUrl = new Map(S.rawNews.map(a => [a.sourceUrl, a]));
    let gotImage = false;
    for (const a of d.articles) {
      const row = byUrl.get(a.sourceUrl);
      if (row && !row.imageUrl && a.imageUrl) { row.imageUrl = a.imageUrl; PREP.delete(row); gotImage = true; }
    }
    if ((gotImage || deadChanged) && !fresh.length) { publishNews(); requestRender(false); renderTopbar(); return; }
    if (!fresh.length) { renderTopbar(); return; }
    S.overlay = [...fresh.map(a => ({a, at: Date.now()})), ...(S.overlay || [])];
    S.rawNews = [...fresh, ...S.rawNews];
    publishNews();
    if (readerBusy()) { S.pendingNew = [...fresh, ...(S.pendingNew || [])]; renderTopbar(); renderTicker(); }
    requestRender();
  } catch {} finally { S.latestLoading = false; }
}

// og.json: mənbə → şəkil xəritəsi (alt mənbələrin şəkli, şəkilsiz sətirə ehtiyat). Lentdən sonra boş anda, 30 dəqiqədə bir (əvvəl tam lentlə
// birlikdə gözlənilirdi və 10 dəqiqəlik hər yeniləmədə yenidən gəlirdi: 55 KB gzip). Gələndə yalnız şəkil qazanan sətir varsa lent yenidən çəkilir.
const OG_REFRESH_MS = 30 * 60e3;
async function loadOg(signal) {
  if (S.ogLoadedAt && Date.now() - S.ogLoadedAt < OG_REFRESH_MS) return;
  try {
    const {d} = await requestJSON(freshUrl("data/og.json"), {signal}, 5000);
    S.ogLoadedAt = Date.now();
    const og = d && typeof d === "object" && !Array.isArray(d) ? d : {};
    const gain = (S.rawNews || []).some(a => !a.imageUrl && og[a.sourceUrl]); // yalnız əsas şəkil qazanan sətir üçün yenidən çəkilir (alt mənbələrin şəkli növbəti adi çəkilişdə)
    S.og = { ...(S.og || {}), ...og };
    if (gain && S.data) { publishNews(); requestRender(false); }
  } catch { S.og ||= {}; }
}
async function loadMarkets() {
  // Mənbə: data/markets.json.
  try {
    const r = await fetch(freshUrl("data/markets.json"), { cache: "no-store" });
    if (r.ok) { const d = await r.json(); if (d.items?.length) { S.markets = d.items; renderMarkets(); if (route().name === "rates") requestRender(false); return; } }
  } catch {}
  // Ehtiyat: brauzerdən birbaşa (açarsız, CORS açıq API-lər)
  const items = [];
  try {
    const g = await (await fetch("https://open.er-api.com/v6/latest/USD")).json(), azn = g.rates.AZN;
    items.push({ label: "Dollar", value: azn, dec: 4, unit: "AZN" }, { label: "Avro", value: azn / g.rates.EUR, dec: 4, unit: "AZN" },
      { label: "100 Rubl", value: azn / g.rates.RUB * 100, dec: 4, unit: "AZN" }, { label: "100 Lirə", value: azn / g.rates.TRY * 100, dec: 4, unit: "AZN" }, { label: "Yuan", value: azn / g.rates.CNY, dec: 4, unit: "AZN" });
  } catch {}
  for (const [sym, label, dec] of [["XAU", "Qızıl", 1], ["XAG", "Gümüş", 2]]) {
    try { const x = await (await fetch(`https://api.gold-api.com/price/${sym}`)).json(); x?.price && items.push({ label, value: x.price, dec, unit: "USD" }); } catch {}
  }
  if (items.length) { S.markets = items; renderMarkets(); if (route().name === "rates") requestRender(false); }
  else $("#markets").hidden = true; // heç bir mənbə cavab vermədi: ayrılmış yer boş qalmasın
}

function wxCode(c) {
  return c === 0 ? ["Açıq", "☀️"] : c === 1 ? ["Əsasən açıq", "🌤️"] : c === 2 ? ["Qismən buludlu", "⛅"] : c === 3 ? ["Buludlu", "☁️"]
    : c === 45 || c === 48 ? ["Duman", "🌫️"] : c >= 51 && c <= 57 ? ["Çiskin", "🌦️"] : (c >= 61 && c <= 67) || (c >= 80 && c <= 82) ? ["Yağışlı", "🌧️"]
    : (c >= 71 && c <= 77) || c === 85 || c === 86 ? ["Qarlı", "🌨️"] : c >= 95 ? ["İldırımlı", "⛈️"] : ["Dəyişkən", "🌡️"];
}
async function weather(list) {
  // Open-Meteo bir sorğuda bir neçə koordinatı qəbul edir
  const lat = list.map(c => c[1]).join(","), lon = list.map(c => c[2]).join(",");
  const u = `https://api.open-meteo.com/v1/forecast?latitude=${lat}&longitude=${lon}&current=temperature_2m,apparent_temperature,relative_humidity_2m,precipitation,weathercode,surface_pressure,wind_speed_10m&timezone=Asia%2FBaku`;
  let d = await (await fetch(u)).json(); if (!Array.isArray(d)) d = [d];
  return d.map((x, i) => { const c = x.current, [label, icon] = wxCode(c.weathercode);
    return { city: list[i][0], temp: Math.round(c.temperature_2m), feels: Math.round(c.apparent_temperature), humidity: Math.round(c.relative_humidity_2m),
      wind: Math.round(c.wind_speed_10m), pressure: Math.round(c.surface_pressure), precip: Math.round((c.precipitation ?? 0) * 10) / 10, label, icon }; });
}
const WX_KEY = "8ulduz-wx";
async function loadWeather() { try { S.wx = (await weather([geoCity()]))[0]; storage.setItem(WX_KEY, JSON.stringify({ ...S.wx, at: Date.now() })); renderTopbar(); } catch {} }
// Son hava yaddaşdan dərhal; konum icazəsi varsa əvvəl şəhər.
// Son konum şəhəri və namaz vaxtı da (sahib 2026-11-13, video: hər açılışda «Namaz» vaxtsız çıxır, sonra dolub yanındakıları itələyirdi; konum
// gecikəndə hava və namaz Bakıya qayıdıb sonra yenə dəyişirdi). Yalnız şəhərin adı saxlanır, nöqtə yox.
const bakuDay = () => new Date(Date.now() + 144e5).toISOString().slice(0, 10);
function restoreLocal() {
  try { const c = storage.getItem(GEO_KEY) === "1" && storage.getItem(GEO_CITY_KEY); if (c && CITIES.some(x => x[0] === c)) S.geo = { city: c }; } catch {}
  try { const w = JSON.parse(storage.getItem(WX_KEY) || "null"); if (w && Date.now() - w.at < 3 * HOUR && w.city === geoCity()[0]) S.wx = w; } catch {}
  try { const p = JSON.parse(storage.getItem(PRAY_KEY) || "null"); if (p?.timings && p.day === bakuDay() && p.city === savedPrayCity()) S.pray = p; } catch {}
}
async function loadLocal() { if (!(await autoLocate())) { loadWeather(); loadPrayer(savedPrayCity()); loadWarnings(); } }
async function loadAllWeather() {
  if (S.wxAll) return; renderTopbar();
  try { S.wxAll = (await weather(CITIES)).sort((a, b) => a.city.localeCompare(b.city, "az")); } catch { S.wxAll = []; }
  renderTopbar();
}

/* ---- konum */
// Konum yalnız «Konumum» düyməsi ilə soruşulur.
// Xidmətlərə dəqiq nöqtə getmir.
const GEO_KEY = "8ulduz-geo", GEO_CITY_KEY = "8ulduz-geo-city", PRAY_KEY = "8ulduz-pray";
function nearestCity(lat, lon) {
  const k = Math.cos(lat * Math.PI / 180);
  let best = null, bd = Infinity;
  for (const c of CITIES) { const d = Math.hypot((c[1] - lat) * 111, (c[2] - lon) * 111 * k); if (d < bd) { bd = d; best = c; } }
  return bd <= 80 ? best : null; // xaricdə şəhər seçilmir, yalnız xəritə mərkəzlənir
}
function geoCity() { return (S.geo?.city && CITIES.find(c => c[0] === S.geo.city)) || CITIES[0]; }
function applyGeo(pos) {
  const { latitude: lat, longitude: lon } = pos.coords;
  S.geo = { lat: Math.round(lat * 100) / 100, lon: Math.round(lon * 100) / 100, city: nearestCity(lat, lon)?.[0] || null, at: Date.now() };
  S.geoBusy = false; S.geoErr = null;
  storage.setItem(GEO_KEY, "1"); storage.setItem(GEO_CITY_KEY, S.geo.city || "");
  loadWeather(); loadWarnings();
  loadPrayer(savedPrayCity()); // seçilmiş şəhər qalır
  renderTopbar();
  if (route().name === "traffic") renderView();
}
function locate(ask) {
  if (!navigator.geolocation) { if (ask) { S.geoErr = "Brauzer konumu dəstəkləmir"; renderTopbar(); } return Promise.resolve(false); }
  S.geoBusy = true; S.geoErr = null;
  if (ask) { renderTopbar(); if (route().name === "traffic") renderView(); }
  return new Promise(res => navigator.geolocation.getCurrentPosition(pos => { applyGeo(pos); res(true); }, err => {
    S.geoBusy = false;
    S.geoErr = err?.code === 1 ? "Konuma icazə verilmədi" : "Konum tapılmadı";
    if (ask) { renderTopbar(); if (route().name === "traffic") renderView(); }
    res(false);
  }, { enableHighAccuracy: false, timeout: 10000, maximumAge: 10 * 60e3 }));
}
function autoLocate() { // icazə varsa soruşmadan; alınmasa false (Bakı qalır)
  if (storage.getItem(GEO_KEY) !== "1" || !navigator.geolocation) return Promise.resolve(false);
  return Promise.resolve().then(() => navigator.permissions?.query?.({ name: "geolocation" })).then(p => p.state === "granted" && locate(false)).catch(() => false);
}
const geoBtn = (attrs = "") => `<button type="button" class="geo-btn${S.geo?.city ? " on" : ""}" data-act="geo"${attrs}${S.geoBusy ? " disabled" : ""} title="Konumunuza ən yaxın şəhər">${S.geoBusy ? "Axtarılır…" : S.geo?.city ? `📍 ${esc(S.geo.city)}` : "📍 Konumum"}</button>`;

/* ---- marşrut */
function route() {
  let h = location.hash.replace(/^#/, "") || "/";
  try { h = decodeURIComponent(h); } catch {} // natamam %-kod səhifəni dayandırmasın
  const article = h.match(/^\/xeber\/([^#?]+)/); if (article) return { name: "article", id: article[1] };
  const team = h.match(/^\/komanda\/([^/?]+)(?:\/([^/?]+))?(?:\/([^/?]+))?(?:\?s=(\d{4}))?$/); if (team) return { name: "team", liga: team[1], team: team[2] || "", tab: team[3] || "", season: team[4] || "" };
  if (h === "/menbeler" || h.startsWith("/menbeler?")) return { name: "sources" };
  if (h === "/videolent" || h.startsWith("/videolent?")) return { name: "videos" };
  if (h === "/secilmis" || h.startsWith("/secilmis?")) return { name: "saved" };
  if (h === "/bolmeler" || h.startsWith("/bolmeler?")) return { name: "sections" };
  if (h === "/haqqinda" || h.startsWith("/haqqinda?")) return { name: "about" };
  const m = h.match(/^\/bolme\/([^/?]+)(?:\?m=([^&]+))?/); if (m) return SERVICE_ROUTES[m[1]] ? { name: SERVICE_ROUTES[m[1]] } : { name: "section", slug: SECTION_ALIAS[m[1]] || m[1], m: m[2] || "" };
  if (h === "/tixac" || h.startsWith("/tixac?")) return { name: "traffic" };
  const q = h.match(/^\/axtar(?:\?q=(.*))?$/); if (q) return { name: "search", q: q[1] || "" };
  if (h === "/" || h === "") return { name: "home" };
  return { name: "notfound" };
}

/* ---- render */
function shell() {
  // index.html eyni qabığı statik daşıyır (data-shell).
  if (!$("#app").dataset?.shell) $("#app").innerHTML = `
  <a class="skip" href="#view">Məzmuna keç</a>
  <header class="site" id="sitehead"><div class="wrap hrow">
    <a class="logo" href="#/" aria-label="8ulduz — baş səhifə">${LOGO}</a>
    <nav class="main" id="nav" aria-label="Bölmələr"></nav>
    <label class="search"><span class="sr">Axtar</span>
      <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><circle cx="11" cy="11" r="7"/><path d="m20 20-3.5-3.5"/></svg>
      <input id="q" type="search" placeholder="Xəbər axtar…" autocomplete="off" aria-label="Xəbər axtar" enterkeyhint="search">
      <button type="button" id="mic" class="mic" aria-label="Səslə axtar" title="Səslə axtar" aria-pressed="false" hidden><svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" aria-hidden="true"><rect x="9" y="3" width="6" height="11" rx="3"/><path d="M5 11a7 7 0 0 0 14 0M12 18v3"/></svg></button></label>
    <button type="button" class="qbtn" data-act="find" aria-label="Xəbər axtar" title="Xəbər axtar"><svg width="17" height="17" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" aria-hidden="true"><circle cx="11" cy="11" r="7"/><path d="m20 20-3.5-3.5"/></svg></button><button type="button" class="follow-btn" data-act="follow" aria-haspopup="dialog">8ULDUZ-u izlə</button><span class="inst" id="inst"></span>
    <div class="topbar"><div class="wrap" id="topbar"></div></div>
  </div><div class="nav-pop" id="navpop" hidden></div></header>
  <div id="ticker"></div>
  <div class="markets pending" id="markets"><div class="wrap mk-wrap"><div class="mk-grid" id="mk"></div><p class="mk-note" id="mk-note" hidden></p><div id="fx-slot"></div></div></div>
  <main><div class="wrap" id="view" tabindex="-1"></div></main>
  <footer id="footer"></footer>
  <button class="newpill" id="newpill" data-act="apply-new" aria-live="polite" hidden></button>
  <button class="totop" id="totop" aria-label="Yuxarı qayıt">↑</button>
  <nav class="tabbar" aria-label="Sürətli keçid">
    <a href="#/" data-tab="home"><b>⌂</b><span>Əsas</span></a>
    <a href="/bolme/video/" data-tab="video"><b>▶</b><span>Video</span></a>
    <a href="#/tixac" data-tab="traffic" class="tix-btn"><b>⛗</b><span>Tıxac</span></a>
    <a href="#/secilmis" data-tab="saved"><b>☆</b><span>Seçilmişlər</span></a>
  </nav>`;
  const q = $("#q");
  q.addEventListener("keydown", e => { if (e.key === "Enter") q.blur(); }); // telefonda klaviatura bağlansın
  q.addEventListener("blur", () => { if (!q.value) $("#sitehead")?.classList.remove("q-open"); }); // telefonda boş axtarış qutusu bağlanır
  q.addEventListener("input", () => {
    S.q = q.value.trim(); S.shown = PAGE;
    const want = S.q ? `#/axtar?q=${encodeURIComponent(S.q)}` : "#/";
    if (location.hash !== want) history.replaceState(null, "", want);
    renderNav();
    renderView();
  });
  document.addEventListener("click", onClick);
  if (globalThis.matchMedia?.("(hover:hover) and (pointer:fine)").matches) bindNavPop();
  document.addEventListener("change", e => { if (e.target.matches("[data-language]")) { setLang(e.target.value); } });
  document.addEventListener("input", e => { if (e.target.matches("[data-source-search]")) { const term = e.target.value.toLocaleLowerCase("az"); document.querySelectorAll(".src-row").forEach(row => row.hidden = !row.textContent.toLocaleLowerCase("az").includes(term)); } });
  window.addEventListener("hashchange", () => {
    // Alt başlıq qalır (menyudan seçiləndə, liqa səhifəsindən qayıdanda).
    const r = route(), kept = S.keepClub || r.name === "team" || (S.prevRoute?.name === "team" && r.name === "section" && r.slug === S.clubSlug);
    S.prevRoute = r;
    S.langOpen = false; S.keepClub = false; S.shown = PAGE; S.lateDone = 0; S.svcOpen = false; if (!kept) { S.club = null; S.sportTab = null; S.clubUrl = ""; }
    S.renderPending = false; S.pendingNew = 0; syncNewPill(); syncQuery(); render(); window.scrollTo(0, 0); $("#view")?.focus({ preventScroll: true });
    if ($("#navpop")) $("#navpop").hidden = true;
    if (kept) scrollToClub();
  });
  addEventListener("pagehide", () => { try { sessionStorage.setItem("8y:" + location.hash, scrollY | 0); } catch {} });
  window.addEventListener("scroll", () => { S.sy = scrollY; closeSharePop(); $("#totop").classList.toggle("show", scrollY > 600); }, { passive: true });
  $("#totop").onclick = () => scrollTo({ top: 0, behavior: "smooth" });
  syncQuery();
  const Recognition = window.SpeechRecognition || window.webkitSpeechRecognition; // Firefox-da yoxdur: düymə gizli qalır
  if (Recognition) setTimeout(() => import('./assistant.js').then(({mountVoiceSearch}) => mountVoiceSearch({button: $("#mic"), input: q, Recognition, onDone: () => scrollTo(0, 0)})).catch(() => {}), 3e3); // xəbərlərlə yarışmasın
}
function syncQuery() {
  const r = route();
  const q = $("#q");
  if (r.name === "search") {
    S.q = r.q || "";
    if (q && document.activeElement !== q) q.value = S.q;
  } else {
    S.q = "";
    if (q) q.value = "";
  }
}
const HOME_DESC = document.querySelector('meta[name="description"]')?.getAttribute("content") || "";
function pageMeta() {
  const r = route();
  const md = document.querySelector('meta[name="description"]');
  if (r.name === "home") {
    document.title = "8ulduz — Son xəbərlər";
    if (md && HOME_DESC) md.setAttribute("content", HOME_DESC);
    return;
  }
  let name = "8ulduz";
  let desc = HOME_DESC;
  if (r.name === "section") {
    const c = CATS.find(x => x.slug === r.slug);
    if (c) { name = c.label; desc = c.description; }
    else name = "Bölmə tapılmadı";
  } else if (r.name === "search") {
    name = S.q ? `Axtarış: ${S.q}` : "Axtarış";
    desc = "Başlıq, xülasə və mənbə adına görə axtarış.";
  } else if (r.name === "traffic") { name = "Tıxac və yollar"; desc = "Bakı və Abşeronun canlı yol vəziyyəti."; }
  else if (r.name === "rates") { name = "Valyuta məzənnəsi"; desc = "Dollar, avro, rubl və lirənin manatla məzənnəsi, neft və qızıl qiyməti."; }
  else if (r.name === "league") { name = "Premyer Liqa cədvəli"; desc = "Azərbaycan Premyer Liqasının turnir cədvəli və digər liqalar."; }
  else if (r.name === "saved") { name = "Seçilmişlər"; desc = "Bu cihazda saxlanan xəbərlər."; }
  else if (r.name === "sources") { name = "Mənbə vəziyyəti"; desc = "RSS lentlərinin son yoxlanması."; }
  else if (r.name === "sections") { name = "Mənim bölmələrim"; desc = "Baş səhifə bölmələrinin sırası."; }
  else if (r.name === "videos") { name = "Video xəbərlər"; desc = "Azərbaycan kanallarının video lentləri."; }
  else if (r.name === "about") { name = "Haqqımızda"; desc = "8ulduz nədir, mənbələr, redaksiya prinsipləri, məxfilik və əlaqə."; }
  else if (r.name === "notfound") { name = "Səhifə tapılmadı"; }
  else if (r.name === "team") { name = "Komanda"; }
  document.title = `${name} — 8ulduz`;
  if (md && desc) md.setAttribute("content", desc);
}

// Günün 10 xəbəri: Azərbaycan dilində kanal; ingilis/rus/türk oxucu bota yazılır və öz dilində alır (izle.cjs, start=g_<dil>).
const tgDigest = () => { const bot = window.SITE_CONFIG?.tgBot; return uiLang(S.lang) && bot ? `https://t.me/${bot}?start=g_${S.lang}` : window.SITE_CONFIG?.telegram || "https://t.me/sekkizulduz_az"; };
function renderTopbar() {
  if (document.activeElement?.matches?.("#topbar select")) return; // açıq şəhər siyahısı bağlanmasın; seçimdən sonra yenilənir
  // İlk ekranın faylı 10 dəqiqəyədək köhnə ola bilər.
  const w = S.wx, upd = S.status?.checkedAt || (S.partial ? null : S.data?.updatedAt);
  // 11: status təzə olsa da bu ekrana yeni məlumat çatmayıbsa «indicə» yazılmasın.
  const applied = Math.max(S.newsCheckedAt || 0, S.latestAt || 0);
  // Qayıdışdan sonrakı 20 s yoxlama gedir: «köhnəlib» sətri çıxıb yeni məlumatla dərhal itirdi, səhifə 22 px aşağı-yuxarı atılırdı.
  // «Yeniləndi» yazısının yeri vaxt bilinməmiş də ayrılır (görünməz): 721–800 px enində o sonradan çıxanda düymələr ikinci sətrə düşür, səhifə 36 px atılırdı.
  const now = Date.now(), old = t => t && now - t > 5 * 60e3; // tarix yoxdursa NaN/0: köhnə sayılmır
  const stale = now - (S.lastResumeAt || 0) > 2e4 && (old(+new Date(upd)) || old(applied));
  const syncBad = S.error || S.offline || S.status?.ok === false || stale;
  const syncText = S.offline ? "Oflayn — saxlanmış xəbərlər" : S.error ? "Xəbərlər yenilənmədi" : S.status?.ok === false ? "Mənbələr yoxlanmadı" : stale ? "Xəbər lenti köhnəlib" : S.status?.degraded ? "Bəzi mənbələr açılmır" : "";
  let pop = "";
  if (S.wxOpen) {
    const sel = S.wxSel && (S.wxAll || []).find(x => x.city === S.wxSel);
    pop = `<div class="wx-pop" role="dialog" aria-label="Bölgələr üzrə hava">` + (sel
      ? `<button class="wx-back" data-act="wx-back">← Bölgələrə qayıt</button>
         <div class="wx-now"><span class="wx-emo">${sel.icon}</span><div><b>${esc(sel.city)}</b><div class="muted">${esc(sel.label)}</div></div><b class="wx-temp">${sel.temp}°</b></div>
         <div class="wx-det">${[["Hiss olunur", `${sel.feels}°`], ["Rütubət", `%${sel.humidity}`], ["Külək", `${sel.wind} km/s`], ["Təzyiq", `${sel.pressure} hPa`], ["Yağıntı", `${sel.precip} mm`]].map(([k, v]) => `<div><small>${k}</small><b>${v}</b></div>`).join("")}</div>`
      : `<div class="wx-head"><span>Bölgələr üzrə hava</span>${geoBtn()}<button data-act="wx-close" aria-label="Bağla">✕</button></div>${S.geoErr ? `<p class="geo-err">${esc(S.geoErr)}</p>` : ""}` +
        (!S.wxAll ? `<div class="empty" style="padding:24px 0">Yüklənir…</div>` :
          `<div class="wx-grid">${S.wxAll.map(c => `<button class="wx-city" data-city="${esc(c.city)}"><span>${c.icon} ${esc(c.city)}</span><b>${c.temp}°</b></button>`).join("")}</div>`)) + `</div>`;
  }
  const fs = document.documentElement.dataset.fs || FS_STD;
  const light = document.documentElement.dataset.theme === "light";
  const h = `    <span>${today()}</span>
    ${optional(prayBit)}
    <div class="wx ${S.wxOpen ? "open" : ""}"><button class="wx-btn" data-act="wx" title="Azərbaycanın bölgələri üzrə hava"><span>${w ? w.icon : "🌡️"}</span><span class="wcity">${esc(w?.city || geoCity()[0])}</span><b>${w ? `${w.temp}°` : "—"}</b><span style="opacity:.6">▾</span></button>${pop}</div>
    ${langDD()}
    <span class="sp sync">${S.lastSync ? `Son əlaqə: ${S.lastSync.toLocaleTimeString("az-AZ")}` : ""}</span>
    ${syncText ? `<span class="sync-state${syncBad ? " bad" : ""}" role="status">${syncText}${syncBad ? ' <button type="button" class="retry" data-act="refresh">Yenilə</button>' : ""}</span>` : ""}
    <span class="yenilendi"${upd ? "" : ' style="visibility:hidden"'}><span class="dot${syncBad ? "" : " live"}" style="background:${syncBad ? "var(--red)" : "#34d399"}"></span>Yeniləndi: ${ago(upd || now)}</span>
    <span class="prefs"><button data-act="refresh" title="Xəbərləri yenilə" aria-label="Xəbərləri yenilə" aria-busy="${!!S.newsLoading}" ${S.newsLoading ? "disabled" : ""}><span class="face" aria-hidden="true">↻</span></button><button data-act="theme" class="theme-btn" title="${light ? "Tünd rejimə keç" : "İşıqlı rejimə keç"}"><span class="face"><span aria-hidden="true">${light ? "☾" : "☀"}</span><span>${light ? "Tünd" : "İşıqlı"}</span></span></button><button data-act="fs-down" aria-label="Şrifti kiçilt" ${fs === "0" ? "disabled" : ""}><span class="face" aria-hidden="true">A−</span></button><button data-act="fs-up" aria-label="Şrifti böyüt" ${fs === "6" ? "disabled" : ""}><span class="face" aria-hidden="true">A+</span></button></span>`;
  if (h !== S.topH) S.topH = $("#topbar").innerHTML = h; // dəyişməyən zolaq yenidən yazılmır: hər çəkilişdə (və hər 30 s) yazılırdı — stil işi, çəkilişdən əvvəl çirkli səhifə (D2, 2026-11-09)
  syncTixDot();
}

const NAV_PRIMARY = ["sondeqiqe", "gundem", "siyaset", "iqtisadiyyat", "idman", "bolgeler", "sosial"], NAV_PHONE = ["idman", "bolgeler"]; // sahib, 2026-11-10: Gündəm və Dünya ☰-də, yerinə «Ana ekrana» düyməsi; ana ekrandan açılanda (düymə yoxdur) Gündəm və Dünya qayıdır
// Ölçmə bir dəfə, dəyişikliklərdən sonra.
const afterPaint = fn => globalThis.requestAnimationFrame ? requestAnimationFrame(fn) : fn();
// Kadr boyanandan sonra (rAF kadrdan əvvəldir): ölçü oxuyan kod brauzerin öz yerləşdirməsini işlədir, ikinci yerləşdirmə olmur.
const afterFrame = fn => globalThis.requestAnimationFrame ? requestAnimationFrame(() => setTimeout(fn)) : fn();
// Telefonda qısa ad.
const NAV_SHORT = { prezident: "Zuğulba", heyat: "Sağlamlıq", tehsil: "Təhsil" };
const navLabel = c => NAV_SHORT[c.slug] ? `<span class="nav-f">${esc(c.label)}</span><span class="nav-s">${NAV_SHORT[c.slug]}</span>` : esc(c.label);
function renderNav() {
  const r = route(), cur = r.name === "section" ? r.slug : r.name === "home" ? "/" : r.name === "team" ? "idman" : ""; // liqa və komanda səhifələri İdmanın altındadır
  const navClass = c => [cur === c.slug && "on", SUB_TABS[c.slug] && "has-sub", (NAV_PHONE.includes(c.slug) || isStandalone() && /^(gundem|dunya)$/.test(c.slug)) && "ph"].filter(Boolean).join(" ");
  const link = (c, x = "") => `<a href="/bolme/${c.slug}/" class="${x}${navClass(c)}" aria-label="${esc(c.label)}">${navLabel(c)}</a>`;
  // Telefon: 2 bölmə (.ph), «Ana ekrana» düyməsi və ☰ (hamısı)
  const primary = NAV_PRIMARY;
  const extra = CATS.filter(c => !primary.includes(c.slug)).map(c => link(c, "nav-x ")).join("");
  const h = `<a href="#/" class="${cur === "/" ? "on" : ""}">Baş səhifə</a>` + primary.map(slug => link(CATS.find(c => c.slug === slug))).join("") + extra +
    `<button type="button" class="nav-inst" data-act="install"${installBtn() ? "" : " hidden"}><span class="ni-s">📲 Ana ekrana</span><span class="ni-f">📲 Ana ekrana əlavə et</span></button>` +
    `<details class="nav-more"><summary aria-label="Bütün bölmələr">☰ Hamısı</summary><div class="nav-more-pop">${CATS.map(c => link(c)).join("")}<a href="#/secilmis">☆ Saxlanmış xəbərlər</a><a href="#/bolmeler">Bölmələri tənzimlə</a></div></details>` +
    `<a class="nav-tg" href="${esc(tgDigest())}" ${OUT} title="Hər gün 09:00 və 19:00"><span>📩 Günün 10 əsas xəbəri — Telegram-da</span></a>`;
  if (h === S.navH) return;
  S.navH = $("#nav").innerHTML = h;
  afterPaint(fitNav);
}
// Bölmə səhifəsində alt başlıqlar kartların düz üstündədir.
const subNav = slug => SUB_TABS[slug] ? navRows(slug) : "";
// Kursorla açılan menyu: başlığın altında şaquli siyahı, alt siyahı yanında.
function navPopHtml(slug, tab, liga) {
  if (slug === "more") {
    const r = route(), links = CATS.filter(c => !NAV_PRIMARY.includes(c.slug)).map(c => `<a class="pill ${r.slug === c.slug ? "on" : ""}" href="/bolme/${c.slug}/">${esc(c.label)}</a>`).join("");
    return `<div class="pop-col">${links}<a class="pill" href="#/secilmis">☆ Saxlanmış xəbərlər</a><a class="pill" href="#/bolmeler">Bölmələri tənzimlə</a></div>`;
  }
  const tabs = SUB_TABS[slug], club = route().slug === slug ? S.club || "" : null;
  const pill = (name, label = name, kids = false) => `<button class="pill ${club === name || tab === name ? "on" : ""}" data-club="${esc(name)}"${kids ? " data-kids" : ""}>${esc(label)}</button>`;
  const groups = navGroups(tabs, tab), leagues = navLeagues(slug, tab), on = leagues.flatMap(g => g.items).find(l => l.short === liga) || leagues[0]?.items[0];
  return `<div class="pop-col">${pill("", "Hamısı")}${tabs.map(t => pill(t.name, t.name, !!t.groups)).join("")}</div>` +
    (groups.length || leagues.length ? `<div class="pop-col two">${leagues.map(g => `${leagueHead(g)}${g.items.map(l => leagueLink(l, l === on)).join("")}`).join("")}${groups.map(g => (g.group ? `<span class="chip-h">${GROUP_FLAG[g.group] || ""}${esc(g.group)}</span>` : "") + g.items.map(t => pill(t.name, t.label)).join("")).join("")}</div>` : "") +
    (on?.clubs.length ? `<div class="pop-col clubs"><a class="pill all" href="#/komanda/${teamSlug(on.short)}">${esc(on.label)}: cədvəl və ${on.nat ? "komandalar" : "klublar"} ›</a>${on.clubs.map(([n, full]) => `<a class="pill" href="${teamHref(on, full)}">${esc(n)}</a>`).join("")}</div>` : "");
}
const popLeft = (left, width, widest) => Math.max(8, Math.min(left, width - widest - 8));
// Kursor aşağı enəndə qonşu düymə menyunu dəyişməsin.
function bindNavPop() {
  const pop = $("#navpop");
  let timer, preT;
  const later = (fn, ms) => { clearTimeout(timer); timer = setTimeout(fn, ms); };
  const hide = () => { clearTimeout(timer); pop.hidden = true; };
  let anchor, lastX = 0;
  // Yer yalnız açılanda.
  const place = (slug, from) => {
    const head = $("#sitehead").getBoundingClientRect(), box = from.getBoundingClientRect();
    pop.style.left = `${popLeft(box.left - head.left, head.width, slug === "more" ? 230 : slug === "idman" && innerWidth >= 900 ? 800 : 460)}px`;
    pop.style.top = `${box.bottom - head.top}px`;
    pop.style.setProperty("--pop-h", `${Math.max(200, innerHeight - box.bottom - 84)}px`);
  };
  // Dəyişməyən sütuna toxunulmur.
  const paint = (html, keep) => {
    const next = document.createElement("div");
    next.innerHTML = html;
    S.tr?.(next);
    const cols = [...next.children];
    cols.forEach((col, i) => {
      const old = pop.children[i];
      if (!old) return pop.append(col);
      if (old.outerHTML === col.outerHTML) return;
      const top = old.scrollTop;
      old.replaceWith(col);
      if (keep) col.scrollTop = top;
    });
    while (pop.children.length > cols.length) pop.lastChild.remove();
  };
  const show = (slug, tab, from = anchor, liga = "") => {
    const opening = pop.hidden || pop.dataset.slug !== slug, keep = !opening && pop.dataset.tab === (tab ?? "");
    if (opening) { pop.textContent = ""; place(slug, from); }
    anchor = from; pop.dataset.slug = slug; pop.dataset.tab = tab ?? ""; pop.dataset.liga = liga;
    paint(navPopHtml(slug, tab, liga), keep);
    pop.hidden = false;
  };
  S.navRefresh = () => { if (!pop.hidden && pop.dataset.slug === "idman") show("idman", pop.dataset.tab || null, anchor, pop.dataset.liga); };
  $("#sitehead").addEventListener("mouseover", e => {
    if (e.target.closest("#navpop")) {
      clearTimeout(timer);
      const wait = e.clientX > lastX ? 450 : 160;
      lastX = e.clientX;
      const liga = e.target.closest("[data-liga]")?.dataset.liga;
      if (liga && liga !== pop.dataset.liga) return later(() => show(pop.dataset.slug, pop.dataset.tab, anchor, liga), wait);
      const name = e.target.closest("[data-club]")?.dataset.club, slug = pop.dataset.slug;
      if (name !== undefined && name !== pop.dataset.tab && (!name || SUB_TABS[slug]?.some(t => t.name === name))) later(() => show(slug, name), wait);
      return;
    }
    const item = e.target.closest("#nav a, #nav summary");
    clearTimeout(preT); // niyyətlə əvvəlcədən yükləmə: kursor keçiddə 120 ms dayananda
    if (!item) { if (!pop.hidden) later(hide, 220); return; }
    const h = hashOf(item); // keçidlər /bolme/<ad>/ olandan bəri bu şərt heç vaxt ödənmirdi: kompüterdə İdman/Bölgələr menyusu açılmırdı
    preT = setTimeout(() => preload(h), 120);
    const href = h?.match(/^#\/bolme\/(.+)$/)?.[1];
    const slug = item.matches("summary") ? "more" : SUB_TABS[href] ? href : "";
    if (!pop.hidden && slug && slug === pop.dataset.slug) { clearTimeout(timer); return; }
    if (slug) later(() => show(slug, route().slug === slug ? S.sportTab : null, item), pop.hidden ? 60 : 120);
    else if (!pop.hidden) later(hide, 120);
    else clearTimeout(timer);
  });
  $("#sitehead").addEventListener("mouseleave", () => { clearTimeout(preT); later(hide, 220); });
  $("#sitehead").addEventListener("click", e => {
    if (e.target.closest(".nav-more summary") && !pop.hidden) e.preventDefault(); // kursorla artıq açıqdır, ikinci siyahı açılmasın
    else if (e.target.closest("#nav a")) hide();
  });
  pop.addEventListener("click", hide);
  // Səhifədəki sətirlər də eyni.
  let open, rowTimer;
  $("#view").addEventListener("mouseover", e => {
    const box = e.target.closest(".sub-rows"), slug = route().slug;
    clearTimeout(rowTimer);
    if (!box) {
      if (open !== undefined) rowTimer = setTimeout(() => { open = undefined; const old = $(".sub-rows"); if (old) old.innerHTML = navRows(route().slug); }, 220);
      return;
    }
    const name = e.target.closest("[data-club]")?.dataset.club;
    if (name === undefined || name === (open ?? S.sportTab ?? "") || (name && !SUB_TABS[slug]?.some(t => t.name === name))) return;
    rowTimer = setTimeout(() => { open = name; box.innerHTML = navRows(slug, name); }, 110);
  });
  document.addEventListener("keydown", e => { if (e.key === "Escape") hide(); });
}
// Telefonda menyu sürüşən zolaqdır: seçilmiş bölmə görünən yerdə qalsın.
function fitNav() {
  const nav = $("#nav"), on = nav?.querySelector("a.on");
  if (!on || nav.scrollWidth <= nav.clientWidth) return;
  const n = nav.getBoundingClientRect(), r = on.getBoundingClientRect();
  if (r.left < n.left || r.right > n.right) nav.scrollLeft += r.left - n.left - 16;
}

function renderTicker() {
  const latest = byDate((S.data?.articles ?? []).filter(a => (a.lang ?? "az") === (S.lang || "az")));
  const breaking = latest.filter(isFresh), lang = S.lang || "az";
  let list = (breaking.length ? breaking : latest).slice(0, 12), fresh = breaking.length;
  // Lent hələ gəlməyib (açılış, yeniləmə): zolaq ~0,5 s boş qalırdı (sahib 2026-11-13, video). Son zolağın sətirləri yaddaşdan, mənbə qaydasından
  // (QIRMIZI XƏTT 2) keçməklə; yarım saatdan köhnəsi göstərilmir.
  if (!S.data) try { const t = JSON.parse(storage.getItem(TICK_KEY) || 0); if (t.lang === lang && Date.now() - t.at < 30 * 60e3) { list = t.rows.filter(a => !removedSource(a) && !policyViolation(a)); fresh = list.filter(isFresh).length; } } catch {}
  if (!list.length) { $("#ticker").innerHTML = ""; return; }
  // İkinci dövr: zolağın davamı.
  const items = list.map(a => `<a href="${safeHref(a.sourceUrl)}" ${OUT}>${txt(a.title)}</a>`).join("") +
    list.map(a => `<a href="${safeHref(a.sourceUrl)}" ${OUT} aria-hidden="true" tabindex="-1">${txt(a.title)}</a>`).join("");
  // «Bildiriş»: yeni son-dəqiqə xəbəri üçün brauzer bildirişi
  const on = notifyOn();
  const bell = "Notification" in window
    ? `<button type="button" class="bell${on ? " on" : ""}" data-act="notify" aria-pressed="${on ? "true" : "false"}" title="${on ? "Bildirişi söndür" : "Yeni son-dəqiqə xəbəri çıxanda brauzer bildirişi"}">${shIcon("bell")}${on ? "Bildiriş aktiv" : "Bildiriş"}</button>`
    : "";
  const html = `<div class="ticker"><div class="lbl">⚡<span class="lt"> ${tickerLabel(fresh)}</span>${bell}${motionBtn()}</div><div class="run${motionOff() ? " still" : ""}"><div class="track">${items}</div></div></div>`;
  if (html === S.tickerHtml && $("#ticker .track")) return;
  S.tickerHtml = html;
  if (S.data) idle(() => storage.setItem(TICK_KEY, JSON.stringify({ at: Date.now(), lang, rows: list.map(({ title, summary, source, sourceUrl, category, publishedAt }) => ({ title, summary, source, sourceUrl, category, publishedAt })) })), 1500, 5000);
  $("#ticker").innerHTML = html;
  afterPaint(startTicker);
}
const TICK_SPEED = 55, TICK_KEY = "8ulduz-ticker"; // px/s
let tickAnim = null, tickT = 0, tickMoved = false;
function startTicker() {
  const run = $("#ticker .run"), track = $("#ticker .track");
  if (!run || !track || typeof track.animate !== "function") return;
  track.style.animation = "none";
  const phase = Number(tickAnim?.currentTime) || 0; // yeni xəbər gələndə zolaq olduğu yerdən davam edir
  if (tickAnim) { try { tickAnim.cancel(); } catch {} tickAnim = null; }
  clearTimeout(tickT);
  // Dayandırılıb: zolaq durur, ▶ başladır.
  if (motionOff()) return;
  const half = track.scrollWidth / 2;
  if (!(half > 0)) return;
  const dur = half / TICK_SPEED * 1000;
  const anim = tickAnim = track.animate([{ transform: "translateX(0)" }, { transform: `translateX(${-half}px)` }], { duration: dur, iterations: Infinity });
  anim.currentTime = phase % dur;
  let drag = null;
  const resume = ms => { clearTimeout(tickT); tickT = setTimeout(() => { if (!drag && tickAnim === anim) anim.play(); }, ms); };
  run.onpointerdown = e => { if (e.button) return; drag = { x: e.clientX, t: Number(anim.currentTime) || 0 }; tickMoved = false; clearTimeout(tickT); anim.pause(); };
  run.onpointermove = e => {
    if (!drag) return;
    const dx = e.clientX - drag.x;
    if (Math.abs(dx) > 6) tickMoved = true;
    anim.currentTime = (((drag.t - dx / half * dur) % dur) + dur) % dur; // sağa çəkmək = geriyə
  };
  const end = () => { if (!drag) return; drag = null; resume(1500); };
  run.onpointerup = end; run.onpointercancel = end;
  run.onpointerleave = e => { end(); if (e.pointerType === "mouse") resume(0); };
  run.onpointerenter = e => { if (e.pointerType === "mouse" && matchMedia("(hover:hover)").matches) { clearTimeout(tickT); anim.pause(); } };
  run.onclick = e => { if (tickMoved) { e.preventDefault(); e.stopPropagation(); tickMoved = false; } };
}
// Təzə xəbər yoxdursa «Son xəbərlər».
const tickerLabel = fresh => fresh > 0 ? "Son dəqiqə" : "Son xəbərlər";

function prayIcon(key) {
  return `<span class="pi">${key ? `<svg viewBox="0 0 24 24" aria-hidden="true"><use href="${ASSET}sosial.svg#p-${esc(key)}"/></svg>` : ""}</span>`;
}
function prayLeft(mins) {
  if (mins == null || !Number.isFinite(mins)) return "";
  if (mins < 1) return "indi";
  const h = Math.floor(mins / 60), m = mins % 60;
  if (!h) return `${m} dəq`;
  return m ? `${h} saat ${m} dəq` : `${h} saat`;
}
const PRAY_CITY_KEY = "8ulduz-pray-city";
function savedPrayCity() {
  try {
    const v = storage.getItem(PRAY_CITY_KEY);
    if (CITIES.some(c => c[0] === v)) return v;
  } catch {}
  return S.geo?.city || "Bakı"; // seçilməyibsə konumun şəhəri
}
function prayCityOptions(current) {
  return [...CITIES].sort((a, b) => a[0].localeCompare(b[0], "az")).map(([name]) => `<option value="${esc(name)}"${name === current ? " selected" : ""}>${esc(name)}</option>`).join("");
}
function prayBit() {
  const p = S.pray;
  const city = p?.city || savedPrayCity();
  if (!p) return `<button class="pray" data-act="pray" type="button">Namaz<i class="pc"> · ${esc(city)}</i></button>`;
  const h = p.hijri || {};
  const month = HIJRI_AZ[Number(h.month?.number)] || h.month?.en || "";
  const next = nextPrayer(p.timings);
  const hijri = `${h.day || ""} ${month}`.trim();
  const rows = PRAY_ORDER.map(([k, lab]) => {
    const on = k === next.key;
    const time = esc(String(p.timings[k] || "").slice(0, 5));
    const mark = on ? `<span class="pray-when"><em>növbəti</em><small>${esc(prayLeft(next.mins))}</small></span>` : `<span></span>`;
    return `<div class="pray-row${on ? " next" : ""}">${prayIcon(k)}<span class="pn">${esc(lab)}</span>${mark}<b class="pt">${time}</b></div>`;
  }).join("");
  const pop = S.prayOpen ? `<div class="pray-pop" role="dialog" aria-label="Namaz vaxtları"><div class="pray-h"><b>Namaz</b><span>${esc(hijri)} ${esc(String(h.year || ""))}</span></div><label class="pray-pick"><span>Şəhər</span><select class="pray-city" aria-label="Namaz şəhəri">${prayCityOptions(city)}</select></label><div class="pray-geo">${geoBtn(' data-for="pray"')}${S.geoErr ? `<span class="geo-err">${esc(S.geoErr)}</span>` : ""}</div>${rows}</div>` : "";
  return `<div class="pray-wrap${S.prayOpen ? " open" : ""}"><button class="pray" data-act="pray" type="button" aria-expanded="${S.prayOpen ? "true" : "false"}">${prayIcon(next.key)}<span class="pcity">Namaz<i class="pc"> · ${esc(city)}</i></span><b>${esc(next.lab)}</b><b class="pt">${esc(next.time)}</b><span class="phij">${esc(hijri)}</span><span class="caret" aria-hidden="true">▾</span></button>${pop}</div>`;
}
function nextPrayer(times) {
  if (!times) return { key: "", lab: "Namaz", time: "", mins: null };
  const b = new Date(Date.now() + 144e5), mins = b.getUTCHours() * 60 + b.getUTCMinutes(); // vaxtlar Bakı saatı ilədir, «indi» də (xaricdəki oxucuda səhv namaz seçilirdi)
  for (const [k, lab] of PRAY_ORDER) {
    const [hh, mm] = String(times[k] || "").split(":").map(Number);
    if (!Number.isFinite(hh)) continue;
    const t = hh * 60 + (Number.isFinite(mm) ? mm : 0);
    if (t >= mins) return { key: k, lab, time: String(times[k]).slice(0, 5), mins: t - mins };
  }
  const [hh, mm] = String(times.Fajr || "").split(":").map(Number);
  const left = Number.isFinite(hh) ? (24 * 60 - mins) + hh * 60 + (Number.isFinite(mm) ? mm : 0) : null;
  return { key: "Fajr", lab: "Sübh", time: String(times.Fajr || "").slice(0, 5), mins: left };
}
function fmt(v, dec) { return Number(v).toLocaleString("en-US", { minimumFractionDigits: Math.min(dec, 2), maximumFractionDigits: dec }); }
function aznRate(item) {
  if (!item || item.value == null) return null;
  if (item.unit === "AZN") return String(item.id).endsWith("100") ? item.value / 100 : item.value;
  const usd = (S.markets || []).find(m => m.id === "USD");
  return usd?.value ? item.value * usd.value : null;
}
function convertAmt(amount, fromId, toId) {
  const from = fromId === "AZN" ? 1 : aznRate((S.markets || []).find(m => m.id === fromId));
  const to = toId === "AZN" ? 1 : aznRate((S.markets || []).find(m => m.id === toId));
  if (!from || !to) return null;
  return amount * from / to;
}
function renderMarkets() {
  const m = S.markets; if (!m?.length) return;
  $("#markets").classList.remove("pending");
  $("#mk").innerHTML = m.map(i => {
    const unofficial = i.unit === "AZN" && i.src && i.src !== "AMB";
    const has = !unofficial && i.changePct != null && i.change != null;
    const cls = !has ? "flat" : i.changePct > 0 ? "up" : i.changePct < 0 ? "down" : "flat";
    // «bazar» nişanı alt sətirdədir.
    const dec = Math.min(i.dec ?? 2, 2); // kartda nöqtədən sonra ən çox 2 rəqəm (sahibin qeydi); tam dəqiqlik məzənnə səhifəsindədir
    const chg = has ? `<span>${i.changePct > 0 ? "↑" : i.changePct < 0 ? "↓" : "•"} %${Math.abs(i.changePct).toFixed(2)}</span><span>${i.change > 0 ? "+" : ""}${fmt(i.change, dec)}</span>`
      : `<span${unofficial ? ` class="unoff"` : ""}>${i.unit !== "AZN" ? "qiymət" : unofficial ? "bazar" : "məzənnə"}</span><span>${i.unit === "AZN" ? "AZN" : "$"}</span>`;
    const title = [i.src && `Mənbə: ${i.src}`, unofficial && "AMB rəsmi məzənnəsi alınmadı — bazar məzənnəsi", i.asOf && `Tarix: ${i.asOf}`, i.stale && "son məlum qiymət"].filter(Boolean).join(" · ");
    return `<button type="button" class="mk" data-fx="${esc(i.id)}" data-d="${cls}" title="${esc(title)}"><div class="n">${marketIcon(i.id)}${esc(i.label)}</div><div class="v" data-ar="${has ? (i.changePct > 0 ? "↑" : i.changePct < 0 ? "↓" : "") : ""}">${fmt(i.value, dec)}<small>${i.unit === "AZN" ? "₼" : "$"}</small></div><div class="c ${cls}">${chg}</div></button>`;
  }).join("");
  const note = $("#mk-note");
  if (note) { const un = m.some(i => i.unit === "AZN" && i.src && i.src !== "AMB"); note.hidden = !un; note.textContent = un ? "Valyuta: AMB rəsmi məzənnəsi hazırda alınmır, bazar məzənnəsi göstərilir." : ""; }
  const slot = $("#fx-slot"); if (slot) slot.innerHTML = fxPop();
  const from = $("#fx-from"), to = $("#fx-to"), amt = $("#fx-amt");
  if (from && to && amt) {
    from.value = S.fxFrom; to.value = S.fxTo;
    const sync = () => {
      S.fxFrom = from.value; S.fxTo = to.value; S.fxAmt = Math.max(0, Number(amt.value) || 0);
      const out = convertAmt(S.fxAmt, S.fxFrom, S.fxTo);
      const el = $(".fx-out"); if (el) el.textContent = out == null ? "—" : fmt(out, S.fxTo === "BTC" ? 6 : 2);
    };
    from.onchange = sync; to.onchange = sync; amt.oninput = sync;
  }
}
function fxPop() {
  if (!S.fxOpen) return "";
  const opts = [`<option value="AZN">AZN</option>`].concat((S.markets || []).map(i => `<option value="${esc(i.id)}">${esc(i.label)}</option>`)).join("");
  const out = convertAmt(Number(S.fxAmt) || 0, S.fxFrom, S.fxTo);
  const dec = S.fxTo === "BTC" ? 6 : 2; // sync() ilə eyni
  return `<div class="fx-pop" role="dialog"><div class="fx-h"><b>Çevirici</b><button type="button" data-act="fx-close" aria-label="Bağla">✕</button></div>
    <label>Məbləğ<input id="fx-amt" type="number" min="0" step="any" value="${esc(S.fxAmt)}"></label>
    <div class="fx-row"><select id="fx-from">${opts}</select><span>→</span><select id="fx-to">${opts}</select></div>
    <b class="fx-out">${out == null ? "—" : fmt(out, dec)}</b></div>`;
}

// Dil siyahısı: hər dil öz sətrində, bayraq + kod; «Hamısı» sonda.
function languagePicker() {
  const row = (code, html, title) => `<button type="button" class="ldm${(S.lang || "") === code ? " on" : ""}" data-lang="${code}" aria-pressed="${(S.lang || "") === code}" title="${esc(title)}">${html}</button>`;
  return `<div class="lang-list" role="group" aria-label="Xəbərlərin dili">${LANGS.map(l => row(l.code, `${FLAGS[l.code]}<b>${l.code.toUpperCase()}</b>`, l.label)).join("")}${row("", `<span class="flag globe">🌐</span><b>Hamısı</b>`, "Bütün dillər")}</div>`;
}
const ASSISTANT_ON = window.SITE_CONFIG?.assistant === true;
const DRIVER_ON = window.SITE_CONFIG?.driver === true;
function renderLangs() {
  const driver = storage.getItem('8ulduz-driver') === 'on';
  const row = $("#inst"); if (row) row.innerHTML = (DRIVER_ON ? `<button type="button" class="driver-toggle" data-driver-mode aria-pressed="${driver}">🚗 ${driver ? 'Sürücü: aktiv' : 'Sürücü rejimi'}</button>` : '') + installBtn();
  $(".nav-inst")?.toggleAttribute("hidden", !installBtn());
}
// Dil seçimi: bayraq + kod + ox; idmanda qeyd: idman hər dildədir.
function langDD() {
  const cur = S.lang || "", sport = route().name === "section" && route().slug === "idman";
  const pop = S.langOpen ? `<div class="ldd-pop">${sport ? `<span class="lang-note">İdman xəbərləri bütün dillərdə göstərilir</span>` : ""}${languagePicker()}</div>` : "";
  return `<div class="ldd${S.langOpen ? " open" : ""}"><button type="button" class="ldd-btn" data-act="lang" aria-expanded="${S.langOpen ? "true" : "false"}" title="Xəbərlərin dili">${cur ? FLAGS[cur] : "🌐"}<b>${cur ? cur.toUpperCase() : "Hamısı"}</b><span class="caret" aria-hidden="true">▾</span></button>${pop}</div>`;
}

function filtered(list) { return S.lang ? list.filter(a => langOf(a) === S.lang) : list; }
// Dil dəyişəndə səhifə yenidən açılır.
const uiLang = v => v && v !== "az";
function setLang(v) {
  const was = S.lang;
  S.lang = v || null;
  storage.setItem(LANG_KEY, S.lang || "");
  if (uiLang(was) || uiLang(S.lang)) return location.reload();
  S.shown = PAGE; S.langOpen = false; renderTopbar(); renderView();
  if (!S.lang) loadNews(true); // «Hamısı»: başqa dillərin faylları da gəlsin
}
// fold «й»-ni «и» edir, ona görə «ой/ей» burada «ои/еи» yazılır.
// Bölgələr: 14 iqtisadi rayon və onların şəhər, rayonları.
const REGION_TABS = [
  { name: "Bakı", keys: ["bakı", "baku", "баку"] },
  { name: "Abşeron-Xızı", groups: [{ group: "", items: [{ name: "Sumqayıt", keys: ["sumqayıt", "сумгайыт", "сумгаит"] }, { name: "Abşeron", keys: ["abşeron"] }, { name: "Xırdalan", keys: ["xırdalan"] }, { name: "Xızı", keys: ["xızı"] }] }] },
  { name: "Dağlıq Şirvan", groups: [{ group: "", items: [{ name: "Ağsu", keys: ["ağsu"] }, { name: "İsmayıllı", keys: ["ismayıllı"] }, { name: "Qobustan", keys: ["qobustan"], not: ["qobustan qoruğ"] }, { name: "Şamaxı", keys: ["şamaxı"] }] }] },
  { name: "Gəncə-Daşkəsən", groups: [{ group: "", items: [{ name: "Gəncə", keys: ["gəncə", "гяндж"] }, { name: "Daşkəsən", keys: ["daşkəsən"] }, { name: "Goranboy", keys: ["goranboy"] }, { name: "Göygöl", keys: ["göygöl"] }, { name: "Naftalan", keys: ["naftalan"] }, { name: "Samux", keys: ["samux"] }] }] },
  { name: "Qarabağ", groups: [{ group: "", items: [{ name: "Xankəndi", keys: ["xankəndi", "ханкенди"] }, { name: "Ağcabədi", keys: ["ağcabədi"] }, { name: "Ağdam", keys: ["ağdam"] }, { name: "Bərdə", keys: ["bərdə"] }, { name: "Füzuli", keys: ["füzuli"], not: ["məhəmməd füzuli", "füzuli adına", "füzuli poeziya"] }, { name: "Xocalı", keys: ["xocalı"] }, { name: "Xocavənd", keys: ["xocavənd"] }, { name: "Şuşa", keys: ["şuşa", "шуш"] }, { name: "Tərtər", keys: ["tərtər"] }] }] },
  { name: "Qazax-Tovuz", groups: [{ group: "", items: [{ name: "Ağstafa", keys: ["ağstafa"] }, { name: "Gədəbəy", keys: ["gədəbəy"] }, { name: "Qazax", keys: ["qazax"], not: ["qazaxıstan"] }, { name: "Şəmkir", keys: ["şəmkir"] }, { name: "Tovuz", keys: ["tovuz"] }] }] },
  { name: "Quba-Xaçmaz", groups: [{ group: "", items: [{ name: "Xaçmaz", keys: ["xaçmaz"] }, { name: "Quba", keys: ["quba"] }, { name: "Qusar", keys: ["qusar"] }, { name: "Siyəzən", keys: ["siyəzən"] }, { name: "Şabran", keys: ["şabran"] }] }] },
  { name: "Lənkəran-Astara", groups: [{ group: "", items: [{ name: "Lənkəran", keys: ["lənkəran", "ленкоран", "лянкяран"] }, { name: "Astara", keys: ["astara"] }, { name: "Cəlilabad", keys: ["cəlilabad"] }, { name: "Lerik", keys: ["lerik"] }, { name: "Masallı", keys: ["masallı"] }, { name: "Yardımlı", keys: ["yardımlı"] }] }] },
  { name: "Mərkəzi Aran", groups: [{ group: "", items: [{ name: "Mingəçevir", keys: ["mingəçevir", "мингячевир"] }, { name: "Yevlax", keys: ["yevlax", "евлах"] }, { name: "Ağdaş", keys: ["ağdaş"] }, { name: "Göyçay", keys: ["göyçay"] }, { name: "Kürdəmir", keys: ["kürdəmir"] }, { name: "Ucar", keys: ["ucar"] }, { name: "Zərdab", keys: ["zərdab"] }] }] },
  { name: "Mil-Muğan", groups: [{ group: "", items: [{ name: "Beyləqan", keys: ["beyləqan"] }, { name: "İmişli", keys: ["imişli"] }, { name: "Saatlı", keys: ["saatlı"] }, { name: "Sabirabad", keys: ["sabirabad"] }] }] },
  { name: "Naxçıvan MR", groups: [{ group: "", items: [{ name: "Naxçıvan", keys: ["naxçıvan", "нахчыван", "нахичеван"] }, { name: "Babək", keys: ["babək"], not: ["babək xürrəm", "babək qala"] }, { name: "Culfa", keys: ["culfa"] }, { name: "Kəngərli", keys: ["kəngərli"] }, { name: "Ordubad", keys: ["ordubad"] }, { name: "Sədərək", keys: ["sədərək"] }, { name: "Şahbuz", keys: ["şahbuz"] }, { name: "Şərur", keys: ["şərur"] }] }] },
  { name: "Şəki-Zaqatala", groups: [{ group: "", items: [{ name: "Şəki", keys: ["şəki", "шеки"] }, { name: "Balakən", keys: ["balakən"] }, { name: "Qax", keys: ["qax"] }, { name: "Qəbələ", keys: ["qəbələ"] }, { name: "Oğuz", keys: ["oğuz"], not: ["oğuz xan", "oğuz türk", "oğuz el"] }, { name: "Zaqatala", keys: ["zaqatala"] }] }] },
  { name: "Şərqi Zəngəzur", groups: [{ group: "", items: [{ name: "Cəbrayıl", keys: ["cəbrayıl"] }, { name: "Kəlbəcər", keys: ["kəlbəcər"] }, { name: "Qubadlı", keys: ["qubadlı"] }, { name: "Laçın", keys: ["laçın"] }, { name: "Zəngilan", keys: ["zəngilan"] }] }] },
  { name: "Şirvan-Salyan", groups: [{ group: "", items: [{ name: "Şirvan", keys: ["şirvan"] }, { name: "Biləsuvar", keys: ["biləsuvar"] }, { name: "Hacıqabul", keys: ["hacıqabul"] }, { name: "Neftçala", keys: ["neftçala"] }, { name: "Salyan", keys: ["salyan"] }] }] },
];
// Alt başlığı olan bölmələr.
const SUB_TABS = { idman: SPORT_TABS, bolgeler: REGION_TABS };
const TOPIC_SUFFIX = "(?:in|nin|un|nun|a|e|i|u|ya|ye|ni|nu|na|ne|la|le|dan|den|ndan|nden|da|de|nda|nde|s|а|у|е|я|ю|ы|и|ь|ом|ем|еи|ои)?";
const topicMap = tabs => new Map(tabs.flatMap(t => [t, ...(t.groups || []).flatMap(g => g.items)]).map(t => [t.name, t]));
const SPORT_BY_NAME = topicMap(SPORT_TABS), REGION_BY_NAME = topicMap(REGION_TABS);
const sportTopic = name => SPORT_BY_NAME.get(name) || REGION_BY_NAME.get(name);
// Sürət: latın/kiril mətndə \p{L} əvəzinə eyni nəticəli sinif.
const TK_SLOW = /[^\x00-\x7f«»\u00c0-\u00d6\u00d8-\u00f6\u00f8-\u024f\u0400-\u0481\u048a-\u04ff\u2010-\u2027\u2030-\u205e]/;
const topicKey = s => (s = fold(s), TK_SLOW.test(s) ? s.replace(/[^\p{L}\p{N}]+/gu, " ") : s.replace(/[^a-z0-9\u00c0-\u00d6\u00d8-\u00f6\u00f8-\u024f\u0400-\u0481\u048a-\u04ff]+/g, " ")).trim();
function topicRx(t) {
  if (t.rx) return t.rx;
  // Söz şərti yoxdursa uyğun gəlmir.
  const parts = ["\\b\\B"];
  if (t.keys?.length) parts.push(`(?:${t.keys.map(topicKey).join("|")})${TOPIC_SUFFIX} `);
  if (t.stems?.length) parts.push(`(?:${t.stems.map(topicKey).join("|")})`);
  return t.rx = new RegExp(` (?:${parts.join("|")})`, "u");
}
const TOPIC_TEXT = new WeakMap();
function clubMatches(a, club) {
  const topic = sportTopic(club);
  if (!topic || topic.skip?.includes(a.source)) return false;
  if (topic.sources?.includes(a.source)) return true;
  // Mətn bir dəfə hazırlanır.
  let seen = TOPIC_TEXT.get(a);
  if (!seen) {
    const raw = decode(a.title + ' ' + (a.summary || ''));
    TOPIC_TEXT.set(a, seen = {raw, text: ` ${topicKey(raw)} `});
  }
  // Mövzu sözləri bir dəfə normallaşır.
  if ((topic.notK ||= (topic.not || []).map(w => (w[0] == " " ? " " : "") + topicKey(w))).some(w => seen.text.includes(w))) return false;
  if (topic.must && !topic.mustSites.includes(a.source) && !(topic.mustK ||= topic.must.map(w => ` ${topicKey(w)}`)).some(w => seen.text.includes(w))) return false;
  if (topic.quoted && (topic.quotedRx ||= new RegExp(`["«“'‘„]${topic.quoted}["»”'’]`, "iu")).test(seen.raw)) return true;
  // Word starts allow suffixes (Qarabağın).
  if (topicRx(topic).test(seen.text)) return true;
  return !!topic.groups?.some(g => g.items.some(t => clubMatches(a, t.name)));
}
// Ünvanlar updater.py-dakı team_world_league və _team_sources ilə eynidir.
const AZ_LEAGUES = ["Premyer Liqa", "I Liqa", "II Liqa", "Kubok", "Əvəzedicilər"];
function navLeagues(slug, tab) {
  if (slug !== "idman") return [];
  wantSports();
  const world = sport => (S.sports?.leagues || []).filter(l => l.sport === sport && l.groups?.length).map(l => ({ short: l.short, label: l.name.replace(/ \(.*/, ""), place: l.short === "ÇL" || l.short === "AL" || l.short === "KL" || l.short === l.name ? "" : l.short, clubs: l.groups.flatMap(g => g.rows).map(t => [t.team, t.full || t.team]) }));
  if (tab === "Basketbol") { const items = world("basketball"); return items.length ? [{ label: "Liqalar", items }] : []; }
  if (tab !== "Futbol") return [];
  const az = AZ_LEAGUES.map(short => ({ short, label: short, place: "", clubs: ((S.football?.leagues || []).find(l => l.short === short)?.table || []).map(t => [clubAz(t.team), t.team]) }));
  const items = world("football"), nat = (S.milli || []).map(c => ({ short: c.id, label: c.name, place: "", nat: 1, clubs: c.teams.map(n => [n, n]) }));
  return [{ group: "Azərbaycan", label: "Azərbaycan liqaları", items: az }, ...(items.length ? [{ label: "Dünya liqaları", items }] : []), ...(nat.length ? [{ label: "Milli komandalar", items: nat }] : [])];
}
const leagueHead = g => `<span class="chip-h">${GROUP_FLAG[g.group] || ""}${esc(g.label)}</span>`;
const leagueLink = (l, on) => `<a class="pill${on ? " on" : ""}" href="#/komanda/${teamSlug(l.short)}" data-liga="${esc(l.short)}"><span>${esc(l.label)}</span>${l.place ? `<small>${esc(l.place)}</small>` : ""}</a>`;
function navGroups(tabs, open) {
  const groups = tabs.find(t => t.name === open)?.groups || [];
  if (open === "Transfer xəbərləri") return groups.map(g => ({ ...g, items: g.items.filter(t => t.label !== "Basketbol" || withArchive("idman", S.data?.articles || []).some(a => a.category === "idman" && clubMatches(a, t.name))) }));
  // Məlumat çatana qədər klubların düymələri qalır.
  if (open === "Basketbol") return navLeagues("idman", open).length ? [] : groups;
  if (open !== "Futbol") return groups;
  return groups.flatMap(g => g.group === "Azərbaycan" || S.sports?.leagues?.length ? [] : [g]);
}
function navRows(slug, open = S.sportTab, club = S.club || "") {
  const tabs = SUB_TABS[slug];
  const pill = (name, label = name) => `<button class="pill ${club === name || open === name ? "on" : ""}" data-club="${esc(name)}">${esc(label)}</button>`;
  const groups = navGroups(tabs, open), leagues = navLeagues(slug, open);
  return `<div class="nav-row"><div class="wrap sport-chips"><div class="chips">${pill("", "Hamısı")}${tabs.map(t => pill(t.name)).join("")}</div></div></div>` +
    (groups.length || leagues.length ? `<div class="nav-row two"><div class="wrap sport-chips">${leagues.map(g => `<div class="chips sub">${leagueHead(g)}${g.items.map(l => leagueLink(l)).join("")}</div>`).join("")}${groups.map(g => `<div class="chips sub">${g.group ? `<span class="chip-h">${GROUP_FLAG[g.group] || ""}${esc(g.group)}</span>` : ""}${g.items.map(t => pill(t.name, t.label)).join("")}</div>`).join("")}</div></div>` : "");
}

// Sosial yazılar vaxta görə, ən yenisi üstdə.
function orderedSocialPosts(max = 8) {
  return byDate(S.social?.posts || []).slice(0, max);
}
const NET_KEY = { Instagram: "ig", Facebook: "fb", YouTube: "yt" }; // sosial.svg
const netIcon = name => shIcon(NET_KEY[name] || "x");
function profileRows() {
  const whoOrder = { "İlham Əliyev": 0, "Mehriban Əliyeva": 1 };
  return [...PROFILES].sort((a, b) => (whoOrder[a.who] ?? 9) - (whoOrder[b.who] ?? 9))
    .map(g => `<span class="soc-g"><b>${esc(g.who)}</b>${g.links.map(([n, u]) => `<a href="${u}" ${OUT} title="${esc(n)}" aria-label="${esc(g.who)}, ${esc(n)}">${netIcon(n)}${n === "X (AZ)" ? "<i>AZ</i>" : ""}</a>`).join("")}</span>`).join("");
}
function socialForSide() { return orderedSocialPosts(12); }
function socialBlock(side = false, sel = "") {
  const posts = side ? socialForSide() : [...(S.social?.posts || []).filter(p => p.id === sel), ...orderedSocialPosts(8).filter(p => p.id !== sel)];
  const cards = posts.map(p => { const u = safeHref(p.url), su = /^[0-9a-f]{16}$/.test(p.id) ? "bolme/prezident/s/" + p.id : "#/bolme/prezident", who = { prezident: "İlham Əliyev: ", "birinci-xanim": "Mehriban Əliyeva: " }[p.who] || ""; return `<article class="soc-r${p.id === sel ? " on" : ""}"><a class="soc-p" href="${u}" ${OUT} title="${esc(p.network)} · ${esc(p.name || "")}${p.via ? " · " + esc(p.via) : ""}"><span class="soc-ic">${netIcon(p.network)}</span><span class="t">${txt(p.text)}</span>${p.via ? `<span class="via">${esc(p.via)}</span>` : ""}<time>${ago(p.publishedAt)}</time></a><button type="button" class="share" data-act="share" data-share="https://8ulduz.az/${su}" data-title="${esc(who + decode(p.text))}" title="Paylaş">Paylaş</button></article>`; }).join("");
  const list = side ? `<div class="soc-list" data-marquee data-visible="5">` : `<div class="soc-list">`;
  return `<aside class="soc"><div class="soc-h"><b>Sosial şəbəkələr</b></div><div class="soc-links">${profileRows()}</div>${cards ? `${list}${cards}</div>` : `<p class="soc-empty muted">Yazılar hazırda açılmır — hesablara yuxarıdakı keçidlərdən baxın.</p>`}</aside>`;
}
// DOM 1600 → 800), boş vaxtda açılır (lateFill). Kartların HTML-i yaddaşdadır (LATE_HTML, açar keyOf: eyni məzmun eyni açar), səhifə sətrində yalnız
// açarlı boş şablon: patchView 42 kartı təhlil etmir, rememberSrc onları seriallaşdırmır (2026-11-09).
const LATE_HERO = 3, LATE_LIST = 6, lateKey = () => location.hash + "|" + (S.club || ""), LATE_HTML = new Map();
const recent = (m, k, v, max) => { m.delete(k); m.set(k, v); while (m.size > max) m.delete(m.keys().next().value); }; // son N giriş qalır
const late = (parts, n) => {
  if (!TOUCH_UI || parts.length <= n) return parts.join("");
  const h = parts.slice(n).join(""), k = keyOf(h);
  recent(LATE_HTML, k, h, 40);
  return parts.slice(0, n).join("") + `<template data-late="${k}"></template>`;
};
// Açarın HTML-i sənəd parçası kimi; yaddaşdan düşübsə (arada 40-dan çox çəkiliş — praktikada olmur) səhifə yenidən qurulur.
function lateContent(t) {
  const h = LATE_HTML.get(t.dataset.late), tpl = document.createElement("template");
  if (h == null) { S.viewPage = null; setTimeout(renderView); return; }
  tpl.innerHTML = h; return tpl.content;
}
function lateFill() {
  S.lateDone = lateKey();
  const list = document.querySelectorAll("#view template[data-late]");
  if (!list.length) return;
  list.forEach(t => { const c = lateContent(t); if (!c) return; S.tr?.(c); [...c.children].forEach(rememberSrc); t.replaceWith(c); });
  setupStrips(document.querySelectorAll(".hero-strip")); setupHeroImages(); setupFeatureLents();
}
function prezBlock(list) {
  // Şəkil: öz, alts və ya og keşi.
  const card = (a, i) => {
    const [pic, ...rest] = imageCandidates(a);
    const small = sized(pic, 168);
    const thumb = pic ? `<span class="img"><img ${i < PREZ_FIRST_IMAGES ? "src" : "data-src"}="${esc(small)}" data-image-alternatives="${esc(JSON.stringify(small === pic ? rest : [pic, ...rest]))}" alt="" loading="lazy" fetchpriority="low" decoding="async" referrerpolicy="no-referrer" data-fail="alt"></span>` : "";
    // Kart keçiddir, «Paylaş» kənarda.
    return `<article class="pcard${pic ? " has-img" : ""}" data-cat="${esc(a.category)}"><a class="pcard-hit" href="${safeHref(a.sourceUrl)}" ${OUT}>${thumb}<span class="x"><span class="t">${isFirstLady(a) ? `<em class="tag">Birinci xanım</em>` : ""}${txt(a.title)}</span><span class="meta"><span class="src">${sourceName(shownSource(a))}</span><time>${ago(a.publishedAt)}</time></span></span></a>${shareBtn(a)}</article>`;
  };
  const cards = late(list.map(card), PREZ_FIRST_IMAGES);
  return `<section class="prez${S.prezOpen ? " open" : ""}"><div class="prez-h"><h2>${STAR}<a href="/bolme/prezident/" aria-label="Zuğulba Xronikası"><span class="prez-long">Zuğulba Xronikası</span><span class="prez-short">Zuğulba</span></a></h2>
    <span class="prez-n">Son <b>${list.length}</b> xəbər</span>
    <span class="links">${PREZ_LINKS.map(l => `<a href="${l.url}" ${OUT}>${l.name}</a>`).join("")}</span>
    <button type="button" class="prez-pause" data-prez-pause aria-pressed="false" aria-label="Zuğulba lentini dayandır" title="Lenti dayandır">Ⅱ</button><a class="btn" href="/bolme/prezident/">Hamısı →</a></div>
    <div class="prez-body">${list.length ? `<div class="prez-lent" data-prez-lent tabindex="0" aria-label="Zuğulba xəbərləri">${cards}</div>` : ""}
    <details class="social-details"><summary>Rəsmi sosial hesablar ▾</summary>${socialBlock(false)}</details></div></section>`;
}

const HERO_COUNT = 15, HERO_ONLY = 6; // İlk 6 xəbər yalnız slayderdədir; qalanları aşağıdakı siyahılarda da qalır, çünki slayderdə növbəsi 90 saniyədən bir gəlir.
function heroBlock(list) {
  const slides = list.filter(imgUrl).slice(0, HERO_COUNT); // şəkilsiz xəbər slayderə düşmür, boş kadr olmur
  if (!slides.length) return "";
  return `<section class="hero"><div class="strip hero-strip" aria-label="Əsas xəbərlər"><div class="hero-row">${late(slides.map((a,i) => `<article class="hero-main" data-cat="${esc(a.category)}">${img(a, "", i === 0, true, heroPicWidth(i === 0), i > 1)}<div class="body"><div class="badges">${altBadge(a)}${isFresh(a) && !/son dəqiqə/iu.test(a.title) ? '<span class="bd red">Son dəqiqə</span>' : ""}</div><a href="${safeHref(a.sourceUrl)}" ${OUT}><h2>${txt(a.title)}</h2></a>${meta(a)}</div></article>`), LATE_HERO)}</div><button type="button" class="hero-pause" aria-pressed="false" aria-label="Əsas xəbər lentini dayandır">Ⅱ</button></div></section>`;
}

function alertStrip() {
  const hits = roadItems(S.data?.articles || []).slice(0, 3);
  const wx = (S.warn || []).join(" · ");
  const rush = bakuRush() ? `<a class="rush" href="#/tixac">Pik saat — xəritəyə baxın</a>` : "";
  return `<section class="alerts"><b>Yol və hava</b>${rush}<a class="tix-go" href="#/tixac">Tıxac xəritəsi</a>${wx ? `<span class="wxn">${esc(wx)}</span>` : ""}${hits.map(a => `<a href="${safeHref(a.sourceUrl || "#")}" ${OUT}>${a.icon} ${txt(a.title)}</a>`).join("")}</section>`;
}
function photoStrip(list) {
  const cut = Date.now() - 30 * HOUR;
  const pics = byDate(list.filter(a => a.imageUrl && new Date(a.publishedAt).getTime() > cut)).slice(0, 14);
  if (pics.length < 4) return "";
  return `<section><div class="sec-h"><h2>Foto qalereya</h2><span class="cnt">günün şəkilləri</span></div><div class="strip"><div class="phrow">${pics.map(a => `<a href="${safeHref(a.sourceUrl)}" ${OUT}>${img(a)}<span>${txt(a.title)}</span></a>`).join("")}</div></div></section>`;
}
// TheSportsDB ingilis adlarını azərbaycanca yazır
const CLUB_AZ = { "Sabah Baku": "Sabah", "Sabah FK": "Sabah", "Qarabag": "Qarabağ", "Qarabag FK": "Qarabağ", "Neftci Baku": "Neftçi", "Neftchi Baku": "Neftçi", "Neftchi": "Neftçi",
  "Zira": "Zirə", "Zira FK": "Zirə", "Sumqayit": "Sumqayıt", "Sumgayit": "Sumqayıt", "Kapaz": "Kəpəz", "Shamakhi": "Şamaxı", "Araz-Naxcivan": "Araz-Naxçıvan", "Araz Nakhchivan": "Araz-Naxçıvan",
  "Imisli": "İmişli", "Gabala": "Qəbələ", "Sabail": "Səbail", "Karvan": "Karvan-Yevlax", "Turan Tovuz": "Turan Tovuz", "Sheki": "Şəki", "Mingachevir": "Mingəçevir" };
const clubAz = n => CLUB_AZ[String(n || "").trim()] || n || "";
// Komanda səhifəsinin ünvanı: updater.py team_slug ilə eyni.
const teamSlug = s => topicKey(s).replace(/ /g, "-");
const teamHref = (l, name) => `#/komanda/${teamSlug(l.short || "Premyer Liqa")}/${encodeURIComponent(teamSlug(name))}`;
// football.json: «leagues» siyahısı.
function fbLeagues() {
  const fb = S.football;
  const ls = fb ? (Array.isArray(fb.leagues) && fb.leagues.length ? fb.leagues : [fb]) : [];
  const az = ls.filter(l => l && (l.table?.length || l.results?.length || l.fixtures?.length));
  // Dünya liqaları (sports.json).
  const world = (S.sports?.leagues || []).filter(l => l?.groups?.length).map(l => ({
    world: true, sport: l.sport, id: l.id, short: l.short, league: l.name, season: l.season || "", stale: !!l.stale,
    groups: l.groups, table: l.groups[0].rows, results: [], fixtures: [], scorers: [], link: l.url || "https://en.wikipedia.org/", source: "Vikipediya", asof: l.asof || "",
  }));
  return [...az, ...world];
}
// Cədvəl hansı günün oyunlarına qədərdir.
const asofLabel = d => { const [, m, day] = String(d).split("-").map(Number); return m && day ? `${day} ${MONTHS[m - 1]} oyunlarına qədər` : ""; };
const GROUP_AZ = { "Eastern Conference": "Şərq", "Western Conference": "Qərb", "League Phase": "Liqa mərhələsi" };
const FB_HEAD = '<table class="fb-table"><thead><tr><th>#</th><th>Komanda</th><th>O</th><th>Q</th><th>H</th><th>M</th><th>Qol</th><th>F</th><th>Xal</th></tr></thead><tbody>'; // futbol cədvəlinin başlığı (iki yerdə)
function worldTable(l, g) {
  const rows = g.rows || [];
  if (l.sport === "basketball") return `<table class="fb-table"><thead><tr><th>#</th><th>Komanda</th><th>Q</th><th>M</th><th>%</th><th>Geridə</th></tr></thead><tbody>${rows.map(t => `<tr><td>${esc(t.pos)}</td><td class="nm">${t.logo ? `<img src="${esc(sized(t.logo, 96, 1))}" alt="" loading="lazy" referrerpolicy="no-referrer" data-fail="rm">` : ""}${esc(t.team)}</td><td>${esc(t.w)}</td><td>${esc(t.l)}</td><td>${(t.pct * 100).toFixed(1)}</td><td>${esc(String(t.gb ?? "-"))}</td></tr>`).join("")}</tbody></table>`;
  return `${FB_HEAD}${rows.map(t => `<tr>${t.color ? `<td style="box-shadow:inset 3px 0 0 ${esc(t.color)}" title="${esc(t.note || "")}">` : "<td>"}${esc(t.pos)}</td><td class="nm">${t.logo ? `<img src="${esc(sized(t.logo, 96, 1))}" alt="" loading="lazy" referrerpolicy="no-referrer" data-fail="rm">` : ""}${esc(t.team)}</td><td>${esc(t.p)}</td><td>${esc(t.w)}</td><td>${esc(t.d)}</td><td>${esc(t.l)}</td><td>${esc(t.gf)}:${esc(t.ga)}</td><td>${t.gd > 0 ? "+" : ""}${esc(t.gd)}</td><td><b>${esc(t.pts)}</b></td></tr>`).join("")}</tbody></table>`;
}
function footballBlock(list) {
  const all = fbLeagues();
  const fb = all[Math.min(S.fbLeague || 0, Math.max(0, all.length - 1))];
  const news = byDate(list.filter(a => {
    const title = lc(decode(a.title));
    if (/(?:basketbol|voleybol|həndbol|tennis|cüdo|güləş|boks|futzal)/u.test(title)) return false;
    return a.category === "idman" && /futbol|premyer|liqa|qarabağ|neftçi|qarabag|sabah fk|mill[iı]/iu.test(title);
  })).slice(0, 4);
  // Liqa məlumatı yoxdursa blok yoxdur.
  if (!fb) return "";
  const tab = (S.fbTab === "table" && !fb.table?.length) ? "results" : (S.fbTab || "results");
  const picker = all.length > 1 ? `<div class="fb-leagues" role="tablist" aria-label="Liqalar">${all.map((l, i) => `${i > 0 && (l.world !== all[i - 1].world || l.sport !== all[i - 1].sport) ? `<i class="sep" aria-hidden="true"></i>` : ""}<button type="button" class="pill${l === fb ? " on" : ""}${l.sport === "basketball" ? " bb" : ""}" data-fbleague="${i}" role="tab" aria-selected="${l === fb}">${esc(l.short || l.league || "")}</button>`).join("")}</div>` : "";
  if (fb.world) {
    const groups = fb.groups || [];
    const gi = Math.min(Number(S.fbTab) || 0, groups.length - 1);
    const gtabs = groups.length > 1 ? `<div class="fb-groups">${groups.map((g, i) => `<button type="button" class="pill${i === gi ? " on" : ""}" data-fbtab="${i}">${esc(GROUP_AZ[g.name] || g.name)}</button>`).join("")}</div>` : "";
    const wteams = (groups[gi]?.rows || []).slice(0, 12).map(t => `<a href="${teamHref(fb, t.full || t.team)}" class="fb-team" title="${esc(t.full || t.team)}"><b class="pos">${esc(t.pos)}</b>${t.logo ? `<img src="${esc(sized(t.logo, 96, 1))}" alt="" loading="lazy" decoding="async" referrerpolicy="no-referrer" data-fail="rm">` : ""}<span class="nm">${esc(t.team)}</span><span class="pts"><b>${fb.sport === "basketball" ? `${esc(t.w)}-${esc(t.l)}` : t.pts}</b> ${fb.sport === "basketball" ? "" : "xal"}</span></a>`).join("");
    return `<section class="foot"><div class="sec-h"><h2>${fb.sport === "basketball" ? "Basketbol" : "Futbol"}</h2><span class="cnt">${esc(fb.league)}${fb.season ? ` · ${esc(fb.season)}` : ""}${fb.asof ? ` · ${esc(asofLabel(fb.asof))}` : ""}${fb.stale ? " · köhnə məlumat" : ""}</span><a class="more" href="${safeHref(fb.link)}" target="_blank" rel="noopener noreferrer">Vikipediya ↗</a></div>
      ${picker}
      <div class="strip"><div class="fb-teams">${wteams}</div></div>
      ${gtabs}
      <div class="fb-pane">${groups[gi] ? worldTable(fb, groups[gi]) : ""}</div></section>`;
  }
  const teams = fb.table.map(t => `<a href="${teamHref(fb, t.team)}" class="fb-team" title="${esc(t.team)}: ${esc(t.p)} oyun, ${esc(t.w)} Q · ${esc(t.d)} H · ${esc(t.l)} M, qol ${esc(t.gf)}:${esc(t.ga)}"><b class="pos">${esc(t.pos)}</b>${t.logo ? `<img src="${esc(sized(t.logo, 96, 1))}" alt="" loading="lazy" decoding="async" referrerpolicy="no-referrer" data-fail="rm">` : ""}<span class="nm">${esc(clubAz(t.team))}</span><span class="pts"><b>${esc(t.pts)}</b> xal</span></a>`).join("");
  const tabs = [["results", "Nəticələr", fb.roundPlayed], ["fixtures", "Təqvim", fb.roundNext], ["table", "Turnir cədvəli", ""], ["scorers", "Bombardirlər", ""]]
    .filter(([k]) => k !== "table" || fb.table?.length)
    .map(([k, l, r]) => `<button type="button" class="fb-tab${tab === k ? " on" : ""}" data-fbtab="${k}"><span>${l}${r ? `<small>${esc(/^\d+$/.test(String(r)) ? ordTur(r) + " tur" : String(r))}</small>` : ""}</span><i>→</i></button>`).join("");
  const game = g => `<li><b>${esc(clubAz(g.home))}</b><span>${g.played ? `${esc(g.hs ?? "–")} : ${esc(g.as ?? "–")}` : "–"}</span><b>${esc(clubAz(g.away))}</b><time datetime="${esc(g.date || "")}" title="${esc(g.stadium || "")}">${esc(shortDT(g.date))}</time></li>`;
  let pane = "";
  if (tab === "results") pane = fb.results?.length ? `<ul class="games">${fb.results.map(game).join("")}</ul>` : `<p class="muted foot-note">Nəticə hələ yoxdur.</p>`;
  else if (tab === "fixtures") pane = fb.fixtures?.length ? `<ul class="games">${fb.fixtures.map(game).join("")}</ul>` : `<p class="muted foot-note">Növbəti tur hələ elan olunmayıb.</p>`;
  else if (tab === "table") pane = `${FB_HEAD}${fb.table.map(t => `<tr><td>${esc(t.pos)}</td><td class="nm"><a href="${teamHref(fb, t.team)}">${esc(clubAz(t.team))}</a></td><td>${esc(t.p)}</td><td>${esc(t.w)}</td><td>${esc(t.d)}</td><td>${esc(t.l)}</td><td>${esc(t.gf)}:${esc(t.ga)}</td><td>${t.gd > 0 ? "+" : ""}${esc(t.gd)}</td><td><b>${esc(t.pts)}</b></td></tr>`).join("")}</tbody></table>`;
  else if (tab === "scorers") pane = fb.scorers?.length ? `<ol class="fb-scorers">${fb.scorers.map(s => `<li><b>${esc(s.name)}</b> <span class="muted">${esc(clubAz(s.club))}</span><em>${esc(s.goals)} qol</em></li>`).join("")}</ol>` : `<p class="muted foot-note">Bombardir siyahısı alınmadı.</p>`;
  return `<section class="foot"><div class="sec-h"><h2>Futbol</h2><span class="cnt">${esc(fb.league || "")}${fb.season ? ` · ${esc(fb.season)}` : ""}${fb.stale ? " · köhnə məlumat" : ""}</span><a class="more" href="${safeHref(fb.link || "https://pfl.az/")}" target="_blank" rel="noopener noreferrer">pfl.az ↗</a></div>
    ${picker}
    <div class="fb-top${teams ? "" : " noteams"}">${teams ? `<div class="strip"><div class="fb-teams">${teams}</div></div>` : ""}<nav class="fb-links" aria-label="Futbol bölmələri">${tabs}</nav></div>
    <div class="fb-pane">${pane}</div>
    ${news.length ? `<div class="foot-news">${news.map(a => `<a href="${safeHref(a.sourceUrl)}" ${OUT}>${txt(a.title)}</a>`).join("")}</div>` : ""}</section>`;
}
// 9-cu, 10-cu, 1-ci, 3-cü, 6-cı tur: sıra sayı şəkilçisi
function ordTur(n) {
  const v = Number(n); if (!Number.isFinite(v)) return String(n || "");
  const tens = { 10: "cu", 20: "ci", 30: "cu", 40: "cı", 50: "ci", 60: "cı", 70: "ci", 80: "ci", 90: "cı" };
  const ones = { 1: "ci", 2: "ci", 3: "cü", 4: "cü", 5: "ci", 6: "cı", 7: "ci", 8: "ci", 9: "cu" };
  const suf = v % 10 === 0 ? (tens[v % 100] || "cu") : ones[v % 10];
  return `${v}-${suf}`;
}
// "31 okt, 17:30"
function shortDT(iso) {
  const d = new Date(iso); if (!iso || Number.isNaN(d.getTime())) return "";
  if (!/T(?!00:00)\d\d:\d\d/.test(iso)) { const b = new Date(d.getTime() + 144e5); return `${b.getUTCDate()} ${MONTHS[b.getUTCMonth()].slice(0, 3)}`; } // saatsız oyun: gün Bakı təqvimi ilə (İstanbulda bir gün əvvəl görünürdü)
  return `${d.getDate()} ${MONTHS[d.getMonth()].slice(0, 3)}, ${String(d.getHours()).padStart(2, "0")}:${String(d.getMinutes()).padStart(2, "0")}`;
}
// Videoda saytın keçidi paylaşılır (YouTube-un yox); ?v= ilə video birinci (oynadıcı basanda: iframe ekranı saxlayır, ağırdır).
const ytTile = (v, tag = "") => `<div class="yt" data-yt="${esc(v.videoId)}" role="button" tabindex="0"><span class="thumb">${v.imageUrl ? `<img src="${esc(v.imageUrl)}" alt="" loading="lazy" decoding="async" referrerpolicy="no-referrer" data-fail="rm">` : ""}<i>▶</i></span><span class="cap"><b>${esc(v.channel)}${tag}</b><span>${txt(v.title)}</span></span><button type="button" class="share" data-act="share" data-share="https://8ulduz.az/#/videolent?v=${encodeURIComponent(v.videoId)}" data-title="${txt(v.title)}">Paylaş</button></div>`;
function videosView() {
  const v0 = (location.hash.match(/[?&]v=([\w-]{6,20})/) || [])[1];
  let items = S.video?.items || [];
  if (v0) items = [items.find(v => v.videoId === v0) || { videoId: v0, title: "", imageUrl: `https://i.ytimg.com/vi/${v0}/hqdefault.jpg` }, ...items.filter(v => v.videoId !== v0)];
  const head = `<div class="page-h"><div><h1>Video xəbərlər</h1><p>Azərbaycan kanallarının YouTube lentləri. Video düyməyə basanda açılır.</p></div><span class="cnt">${items.length}</span></div>`;
  if (!items.length) return `${head}<p class="empty">Video lent hazırda açılmır. Bir az sonra yenidən baxın.</p>`;
  return `${head}<div class="ytgrid">${items.map(v => ytTile(v)).join("")}</div>`;
}
function catSection(c, list) {
  if (!list.length) return "";
  list = picFirst(list);
  return `<section><div class="sec-h"><h2>${esc(c.label)}</h2><span class="cnt">${list.length} xəbər</span><a class="more" href="/bolme/${c.slug}/">Bütün xəbərlər →</a></div><div class="strip category-strip"><div class="news-row">${list.slice(0, 12).map(card).join("")}</div></div></section>`;
}

function skeleton(kind) {
  if (kind === "article") return `<div class="skel" style="height:30px;margin:24px 0 10px"></div><div class="skel" style="height:200px"></div>`; // başlıq + şəkil yeri: xəbər gələndə səhifə atlamır (üst boşluq .article-detail ilə eyni: 24 px)
  return `<section class="prez"><div class="skel" style="height:180px"></div></section>
    <section class="hero"><div class="skel" style="height:340px"></div></section>
    <section><div class="grid">${"<div class='skel' style='height:220px'></div>".repeat(4)}</div></section>`;
}
// Əhəmiyyət: neçə mənbə yazıb (alts), bərabərdirsə daha yeni.
function rankBySources(list) {
  return list.map(a => ({ a, n: 1 + (a.alts?.length || 0) + (isAppointment(a) ? 2 : 0) }))
    .sort((x, y) => y.n - x.n || newest(x.a, y.a))
    .map(x => x.a);
}
// Hero: son 18 saatın ən çox mənbəli xəbərləri.
// Eyni hadisənin variantları hero-da təkrarlanmasın.
const heroWords = a => new Set(lc(a.title || "").split(/[^\p{L}\p{N}]+/u).filter(w => w.length >= 5));
function diverse(ranked, need) {
  const out = [], seen = [];
  for (const a of ranked) {
    const w = heroWords(a);
    if (seen.some(s => [...w].filter(x => s.has(x)).length >= 2)) continue;
    out.push(a); seen.push(w);
    if (out.length >= need) break;
  }
  for (const a of ranked) { if (out.length >= need) break; if (!out.includes(a)) out.push(a); }
  return out;
}
function heroPick(list, need = 9) {
  const now = Date.now();
  for (const hours of [18, 48]) {
    const cut = now - hours * HOUR;
    const pool = list.filter(a => { const t = new Date(a.publishedAt).getTime(); return t >= cut && t <= now + 5 * 60e3; });
    if (pool.length >= need) return diverse(rankBySources(pool), need);
  }
  return diverse(rankBySources(list), need);
}

const picFirst = l => [...l.filter(imgUrl), ...l.filter(a => !imgUrl(a))]; // şəkilsiz xəbər ana səhifədə sona
function latestBlock(list) {
  const ranked = picFirst(S.latestOrder === "sources" ? rankBySources(list) : byDate(list));
  const count = S.latestCount || 8;
  return `<section id="son-xeberler"><div class="sec-h"><h2>Son xəbərlər</h2><div class="feed-tabs"><button data-feed="latest" class="pill${S.latestOrder !== "sources" ? " on" : ""}" aria-pressed="${S.latestOrder !== "sources"}">Ən yeni</button><button data-feed="sources" class="pill${S.latestOrder === "sources" ? " on" : ""}" aria-pressed="${S.latestOrder === "sources"}">Ən çox mənbə</button></div></div><div class="latest-grid">${ranked.slice(0, count).map(card).join("")}</div>${ranked.length > count ? '<button class="loadmore" data-act="latest-more">Daha çox xəbər</button>' : ""}</section>`;
}
function unifiedVideo(list) {
  const hosted = (S.video?.items || []).slice(0, 4);
  if (!hosted.length && !list.length) return "";
  return `<section><div class="sec-h"><h2>Video</h2><a class="more" href="#/videolent">Bütün videolar →</a></div><div class="strip"><div class="ytrow">${hosted.map(v => ytTile(v, " · Saytda izlə")).join("")}${list.slice(0, 4).map(a => cardAt(a, "h3", " vcard")).join("")}</div></div></section>`;
}
function homeArchive(slug) {
  if (NO_ARCHIVE.has(slug)) return [];
  (S.archiveHome ||= new Set()).add(slug); loadArchive(slug); // gələndə baş səhifə yenidən çəkilir
  return filtered(S.archive?.[slug]?.rows || []).slice(0, 12);
}
function homeView() {
  const m = filtered(S.data.articles), hero = heroPick(m.filter(a => a.category !== "prezident" && imgUrl(a)), HERO_COUNT);
  const used = new Set(hero.slice(0, HERO_ONLY).map(a => a.id));
  const remaining = m.filter(a => !used.has(a.id) && a.category !== "prezident");
  const top = `<h1 class="sr-only">8ulduz — Azərbaycan və dünyadan son xəbərlər</h1><div class="top2">${heroBlock(hero)}${prezBlock(prezHome(m, S.data.articles))}</div>` + optional(adHtml) + latestBlock(remaining);
  if (S.partial) return top; // qalanı tam lentlə gəlir, görünən hissənin altında
  // Yuxarıda görünən xəbər təkrarlanmır.
  const seen = new Set([...hero, ...picFirst(S.latestOrder === "sources" ? rankBySources(remaining) : byDate(remaining)).slice(0, S.latestCount || 8)].map(a => a.id)), fresh = a => !seen.has(a.id);
  // Slayderdəki xəbər bölmədə də qalır; lentdə yoxdursa arxiv.
  const secs = homeCats().map(c => {
    const all = (c.slug === "idman" ? S.data.articles : remaining).filter(a => a.category === c.slug), own = all.filter(fresh);
    return lazySection(catSection(c, byDate(own.length >= 4 ? own : all.length ? all : homeArchive(c.slug))));
  }).join("");
  return top + secs + optional(() => unifiedVideo(byDate(m.filter(a => a.video)))) + optional(() => photoStrip(m.filter(fresh))) + `<details class="service-panel"${S.svcOpen ? " open" : ""}><summary>İdman nəticələri və cədvəllər ▾</summary>${optional(() => footballBlock(S.data.articles))}</details>` + `<details class="service-panel"><summary>Yol və hava ▾</summary>${optional(alertStrip)}</details>`;
}
// Paylaşma siyahısı (updater.update_share_index): hissə = id-nin ilk iki hex rəqəmi, 256 fayl, biri ~8 KB gzip (2026-11-09-a qədər 32 fayl,
// `>> 3`, biri ~54 KB gzip — bir sətir üçün). Keçid dövrü: fayl yoxdursa və ya "parts" 256 deyilsə (updater hələ köhnə bölgü ilə yazır)
// sətir köhnə hissədə axtarılır; yeni bölgülü fayl sətri tapmayanda ikinci sorğu yoxdur (arxiv budağına keçir).
async function shareRow(id) {
  const part = n => requestJSON(freshUrl(`data/paylas/${n}.json`), {}, 8000).then(x => x.d);
  for (let k = id, hop = 0; hop < 3 && /^[0-9a-f]{16}$/.test(k); hop++) {
    const n = parseInt(k.slice(0, 2), 16);
    let d = await part(n).catch(() => null);
    if (d?.parts !== 256 && n >> 3 !== n) d = await part(n >> 3);
    const row = d?.articles?.find(a => a.id === k);
    if (row?.of) { k = row.of; continue; }
    return row && !removedSource(row) && !policyViolation(row) ? row : null;
  }
  return null;
}
// Köhnə keçid: arxiv budağı.
// Saatsız köhnə keçid: idx/<id[0:2]>.json
async function arxRow(id) {
  const R = "https://raw.githubusercontent.com/8ulduz/8ulduz/arxiv/";
  let h = (location.hash.match(/[?&]h=(\d{8})\b/) || [])[1], k = id;
  if (!h) { const { d } = await requestJSON(`${R}idx/${id.slice(0, 2)}.json`, {}, 8000), v = String(d?.[id] || ""); h = v.slice(0, 8); k = v.slice(8) || id; }
  if (!/^\d{8}$/.test(h)) return null;
  const { d } = await requestJSON(`${R}saat/${h}.json`, {}, 8000);
  const r = d?.articles?.find(a => a.id === k);
  return r && !removedSource(r) && !policyViolation(r) ? r : null;
}
// Paylaşılan keçid.
function backHome() { try { if (history.length <= 1 && route().name === "article") { const h = location.hash; history.replaceState(null, "", "#/"); history.pushState(null, "", h); } } catch {} }
// Geri qayıdış: oxucu mənbədən qayıdanda qaldığı yer.
function backY() {
  if (S.backY) return; S.backY = 1;
  try { const y = +sessionStorage.getItem("8y:" + location.hash); if (y > 0 && performance.getEntriesByType("navigation")[0]?.type === "back_forward" && scrollY < 50) requestAnimationFrame(() => scrollTo(0, y)); } catch {}
}
async function loadShared(id) {
  if (S.data || S.sharedStory?.id === id || !/^[0-9a-f]{16}$/.test(id)) return;
  try {
    const row = await shareRow(id) || await arxRow(id);
    if (row) { S.sharedStory = { id, row }; if (route().name === "article") renderView(); } // lent arada gəlsə də
  } catch {}
}
async function scanArchives(id) {
  S.archiveScanning = true;
  try {
    if (globalThis.crypto?.subtle) for (const a of (S.data?.articles || []).filter(a => a.alts?.length)) for (const alt of a.alts) {
      const hash = await crypto.subtle.digest("SHA-1", new TextEncoder().encode(alt.sourceUrl));
      if ([...new Uint8Array(hash)].map(b => b.toString(16).padStart(2, "0")).join("").slice(0, 16) === id) { S.sharedStory = { id, row: a }; return; }
    }
    const row = await shareRow(id).catch(() => null);
    if (row) { S.sharedStory = { id, row }; return; }
    const hint = (location.hash.split("?")[1] || "").match(/(?:^|&)b=([^&]+)/)?.[1];
    for (const slug of new Set([hint, ...CATS.map(c => c.slug)].filter(Boolean))) {
      await loadArchive(slug);
      if (S.archive?.[slug]?.rows.some(a => String(a.id) === id)) return;
    }
    const old = /^[0-9a-f]{16}$/.test(id) && await arxRow(id).catch(() => 0); // 5 gündən köhnə keçid açıq səhifədə: arxiv budağı
    if (old) S.sharedStory = { id, row: old };
  } finally {
    S.archiveScanning = false;
    if (route().name === "article") renderView();
  }
}
// «Bu barədə daha çox».
function relatedOf(a) {
  const all = S.data?.articles || [], df = new Map(), t = +new Date(a.publishedAt), skip = new Set([a, ...(a.alts || [])].map(x => x.id));
  for (const b of all) for (const w of new Set(titleTokens(b.title))) df.set(w, (df.get(w) || 0) + 1);
  const A = new Set(titleTokens(a.title).filter(w => (df.get(w) || 0) <= Math.max(3, all.length / 40) && !/^(muhum|bagl|aciql|son$|yeni|foto|video|veziyyet|haqq|bared|gore|sonra|daha|olub|edib|edir|kecir|detal|xeber|tecili|hesr|olun|oldu|tedbir|tarix|munasib)/.test(w)));
  return all.filter(b => !skip.has(b.id) && Math.abs(+new Date(b.publishedAt) - t) < GROUP_MS && !removedArticle(b))
    .map(b => [new Set(titleTokens(b.title).filter(w => A.has(w))).size, b]).filter(x => x[0] > 1).sort((x, y) => y[0] - x[0]).map(x => x[1]).reduce((k, b) => (k.length < 3 && !k.some(c => jaccard(new Set(titleTokens(b.title)), new Set(titleTokens(c.title))) > .5) && k.push(b), k), []);
}
function articleView(id) {
  const a = (S.data?.articles || []).find(a => String(a.id) === id) || (S.sharedStory?.id === id && S.sharedStory.row) || Object.values(S.archive || {}).flatMap(x => x.rows).find(a => String(a.id) === id) || savedList().find(a => String(a.id) === id);
  if (!a || removedArticle(a)) {
    if (S.data && S.archiveScan !== id) { S.archiveScan = id; scanArchives(id); }
    if (S.archiveScanning) return '<p class="empty">Xəbər axtarılır…</p>';
    return '<p class="empty">Xəbər artıq lentdə yoxdur. <a href="#/">Baş səhifəyə qayıt</a></p>';
  }
  document.title = tidy(a.title) + " — 8ulduz"; S.art = a;
  return `<article class="article-detail"><a href="#/">← Baş səhifə</a><div class="page-h"><h1>${txt(a.title)}</h1></div>${meta(a)}${imgUrl(a) ? img(a, "", !heavyImage(imgUrl(a)), false, 960) : ""}<a class="btn" href="${safeHref(a.sourceUrl)}" ${OUT}>Xəbərin tam mətnini mənbədə oxu ↗</a><section id="sources"><h2>Bu xəbərin mənbələri (${1 + (a.alts?.length || 0)})</h2>${[a, ...(a.alts || [])].map(r => `<a class="source-entry" href="${safeHref(r.sourceUrl)}" ${OUT}>${esc(r.source)} ↗</a>`).join("")}</section>${optional(() => { const m = relatedOf(a); return m.length ? `<section id="more"><h2>Bu barədə daha çox</h2>${m.map(b => `<a class="source-entry" href="/xeber/${b.id}/">${txt(b.title)}</a>`).join("")}</section>` : ""; })}${optional(() => { const sp = a.category === "idman", t = (sp || a.category === "bolgeler") && [...(sp ? SPORT_BY_NAME : REGION_BY_NAME).keys()].reverse().find(n => clubMatches(a, n)), c = CATS.find(c => c.slug === a.category && c.slug !== "sondeqiqe"); return t ? tgIzle((sp ? "i_" : "r_") + teamSlug(t), t) : c ? tgIzle("b_" + c.slug, c.label) : ""; })}</article>`;
}

// «Telegram-da izlə» (izle.cjs).
// Saytın dili bota ön şəkilçi ilə gedir (en-, ru-, tr-): bot o dildə yazır və o dildəki xəbərləri göndərir. Azərbaycan dilində şəkilçi yoxdur.
const tgPre = () => uiLang(S.lang) ? S.lang + "-" : "";
const tgIzle = (k, who) => { const bot = window.SITE_CONFIG?.tgBot; return bot ? `<a class="pill tg-izle" href="https://t.me/${bot}?start=${tgPre()}${k}" ${OUT}>📩 ${who ? esc(who) + ": " : ""}Telegram-da izlə</a>` : ""; };
function listPage(title, desc, list, extra = "") {
  const shown = list.slice(0, S.shown);
  return `<div class="page-h"><div><h1>${esc(title)}</h1><p>${esc(desc)}</p></div><span class="cnt">${list.length} xəbər</span></div>${extra}` +
    (list.length ? `<div class="grid">${late(shown.map(a => cardAt(a, "h2")), LATE_LIST)}</div>${list.length > shown.length ? `<button class="loadmore" data-act="more">Daha çox (${list.length - shown.length})</button>` : ""}`
      : `<p class="empty">${S.q ? "Axtarışınıza uyğun xəbər tapılmadı. Başqa sözlərlə yoxlayın və ya dil süzgəcini dəyişin." : S.club ? "Bu mövzuda son 5 gündə xəbər tapılmadı." : "Bu bölmədə hələ xəbər yoxdur — növbəti yenilənmədə əlavə olunacaq."}</p>`);
}

// Bölmə arxivi (updater.py): bölmə səhifəsi 5 gün.
const NO_ARCHIVE = new Set(["video", "sondeqiqe", "prezident"]);
async function loadArchive(slug) {
  S.archive ||= {};
  const had = S.archive[slug];
  if (NO_ARCHIVE.has(slug) || (had && Date.now() - had.at < 30 * 60e3)) return;
  const cur = S.archive[slug] = { at: Date.now(), rows: had?.rows || [] };
  try {
    const {d} = await requestJSON(freshUrl(`data/arxiv/${slug}.json`), {}, 8000);
    if (!Array.isArray(d?.articles)) throw 0;
    S.archive[slug].rows = d.articles.filter(a => !removedSource(a) && !policyViolation(a)).map(a => ({...a, alts: (a.alts || []).filter(alt => !altForbidden(a, alt))})); S.arxV = (S.arxV || 0) + 1;
    const r = route();
    if ((r.name === "section" && (r.slug === slug || (r.slug === "bolgeler" && S.club))) || r.name === "search" || (r.name === "home" && S.archiveHome?.has(slug)) || (r.name === "team" && slug === "idman")) requestRender(false);
  } catch { cur.at -= 174e4; } // alınmadı: 30 dəqiqə yox, 1 dəqiqə sonra yenidən
}
function allNews() {
  if (S.allD !== S.data || S.allV !== S.arxV) { S.allD = S.data; S.allV = S.arxV; S.all = collapseExact([...S.data.articles, ...CATS.flatMap(c => S.archive?.[c.slug]?.rows || []).filter(a => !removedArticle(a))]); }
  return S.all;
}
const ARCHIVE_POOLS = new WeakMap();
function withArchive(slug, list) {
  const archive = S.archive?.[slug], rows = archive?.rows;
  if (!rows?.length) return list;
  const full = list === S.data?.articles, rev = removedIds.size + removedUrls.size + removedKeys.size;
  const cache = full ? ARCHIVE_POOLS.get(list) : null, memo = cache?.get(slug);
  if (memo && memo.data === S.data && memo.rows === rows && memo.rev === rev) return memo.pool;
  const saved = rows.filter(a => !removedArticle(a)), known = urlsOf(saved);
  const live = (S.data?.articles || []).filter(a => known.has(a.sourceUrl) || a.alts?.some(x => known.has(x.sourceUrl)));
  const pool = collapseExact([...list, ...live, ...saved]);
  if (full) { const m = cache || new Map(); m.set(slug, {data: S.data, rows, rev, pool}); ARCHIVE_POOLS.set(list, m); }
  return pool;
}
// Bölmə hovuzu (2026-11-09): dəqiqəlik lentdə sətirlər yeni obyektlərdir, amma məzmunca çox vaxt eynidir — hovuz (withArchive →
// collapseExact → byDate, idmanda 1×-də 11–14 ms, telefonda 4×) yalnız bölməyə aid sətirlər, arxiv və ya silinmələr dəyişəndə yenidən qurulur.
const POOLS = new Map();
function catPool(slug, list) {
  if (NO_ARCHIVE.has(slug)) return byDate(list); // arxivsiz bölmədə birləşmə yoxdur; «son dəqiqə» saatla dəyişir
  const rows = S.archive?.[slug]?.rows, rev = removedIds.size + removedUrls.size + removedKeys.size, m = POOLS.get(slug), hit = m && m.rows === rows && m.rev === rev;
  if (hit && m.d === S.data) return m.pool; // eyni lent: «Daha çox», alt düymə, başqa bölmənin arxivi
  const known = hit ? m.known : urlsOf((rows || []).filter(a => !removedArticle(a)));
  // withArchive-in götürdüyü sətirlər (bölmənin özününkülər + keçidi arxivdə olan hər lent sətri), məzmunca: hər sahə və alt mənbə.
  const own = JSON.stringify(rows?.length ? list.concat(S.data.articles.filter(a => a.category !== slug && (known.has(a.sourceUrl) || a.alts?.some(x => known.has(x.sourceUrl))))) : list);
  if (hit && own === m.own) { m.d = S.data; return m.pool; }
  const pool = byDate(withArchive(slug, list));
  POOLS.set(slug, { d: S.data, rows, rev, known, own, pool });
  return pool;
}
function sectionView(slug) {
  const c = CATS.find(x => x.slug === slug);
  if (!c) return `<div class="empty"><h1 style="color:var(--fg)">Bölmə tapılmadı</h1><p>Axtardığınız bölmə mövcud deyil.</p><a href="#/" style="color:var(--primary);font-weight:700">← Baş səhifəyə qayıt</a></div>`;
  const d = S.data.articles;
  let list = slug === "video" ? d.filter(a => a.video) : slug === "sondeqiqe" ? d.filter(withinHour) : d.filter(a => a.category === slug);
  loadArchive(slug);
  list = catPool(slug, list);
  if (S.partial && !list.length) return skeleton();
  // ?m=Quba: topics.cjs səhifəsindən gələn keçid mövzunu seçir
  const um = route().m, tabs = SUB_TABS[slug] || [];
  if (um && sportTopic(um) && S.clubUrl !== location.hash) { S.club = um; S.clubUrl = location.hash; S.sportTab = tabs.find(x => x.name === um || x.groups?.some(g => g.items.some(i => i.name === um)))?.name || null; }
  let extra = SUB_TABS[slug] ? `<div class="sub-rows">${subNav(slug)}</div>` : "";
  if (slug === "idman") {
    if (S.club) list = list.filter(a => clubMatches(a, S.club));
  }
  if (slug === "bolgeler") {
    if (S.club) {
      // Yer seçiləndə bütün lent və arxivlər axtarılır.
      CATS.forEach(x => loadArchive(x.slug));
      // «Qəbələ», «Sabah» həm də klubdur.
      list = byDate(allNews().filter(a => a.category !== "idman" && clubMatches(a, S.club)));
    }
  }
  if (slug === "prezident") {
    const s = location.hash.match(/[?&]s=([0-9a-f]{16})/)?.[1] || "";
    extra = `<details class="social-details"${s ? " open" : ""}><summary>Rəsmi sosial hesablar ▾</summary>${optional(() => socialBlock(false, s))}</details>`;
  }
  if (slug !== "sondeqiqe") extra = tgIzle(S.club ? (slug === "idman" ? "i_" : "r_") + teamSlug(S.club) : "b_" + slug, S.club) + extra;
  return listPage(c.label, slug === 'idman' ? 'Bütün dillərdə idman xəbərləri. Alt bölməni və ya komandanı seçin: son xəbərlər açılır.' : slug === "bolgeler" ? "Bölgəni, sonra şəhər və ya rayonu seçin: son xəbərlər açılır." : c.description, slug === 'idman' ? list : filtered(list), extra);
}

// Axtarış üçün sadələşdirmə: ə→e, ı→i və s.
// й, ё, U+0307 da burada: NFD yalnız nadir hərfdə.
const FOLD = { "ə": "e", "ı": "i", "ö": "o", "ü": "u", "ğ": "g", "ş": "s", "ç": "c", "й": "и", "ё": "е", "\u0307": "" };
function fold(s) { // NFD yalnız lazım olanda (2,7× tez)
  s = String(s || "").toLowerCase().replace(/[əıöüğşçйё\u0307]/g, ch => FOLD[ch]);
  return /[\u00c0-\u024f\u0300-\u036fйё]/.test(s) ? s.normalize("NFD").replace(/[\u0300-\u036f]/g, "") : s;
}
const searchWords = q => fold(q).replace(/[^\p{L}\p{N}]+/gu, " ").split(" ").filter(w => w.length >= 2 || /\p{N}/u.test(w));
// İşarələmə: sözün bütün yazılışlarını tutan regex
const HL_CLASS = { e: "[eəE]", i: "[iıİI]", o: "[oöOÖ]", u: "[uüUÜ]", g: "[gğGĞ]", s: "[sşSŞ]", c: "[cçCÇ]" };
function hlRegex(words) {
  const alts = words.map(w => [...w].map(ch => HL_CLASS[ch] || ch.replace(/[.*+?^${}()|[\]\\]/g, "\\$&")).join(""));
  return alts.length ? new RegExp("(" + alts.join("|") + ")", "giu") : null;
}
// Komanda adı axtarılanda onun xəbərləri gəlir.
function searchTopics(q) {
  const text = ` ${topicKey(q)} `;
  return [...SPORT_BY_NAME.values()].filter(t => (t.keys?.length || t.stems?.length) && topicRx(t).test(text)).map(t => t.name);
}
// Açar id-dir (yoxsa keçid): collapseExact hər qurmada sətri klonlayır, obyekt açarlı yaddaş hər dəfə boşa düşürdü (3 300 sətir üçün
// fold yenidən, 1×-də ~23 ms; 2026-11-09). Başlıq, xülasə və ya mənbə sayı dəyişibsə yenidən qurulur; 20 000-dən sonra təmizlənir.
const SEARCH_TEXT = new Map();
function searchText(a) {
  const k = a.id || a.sourceUrl, n = a.alts?.length || 0;
  let s = SEARCH_TEXT.get(k);
  if (!s || s.title !== a.title || s.sum !== a.summary || s.n !== n) {
    if (SEARCH_TEXT.size >= 2e4) SEARCH_TEXT.clear();
    SEARCH_TEXT.set(k, s = { title: a.title, sum: a.summary, n, t: fold(decode(a.title)), rest: fold(decode((a.summary || "") + " " + a.source + " " + (a.alts || []).map(x => x.source).join(" "))) });
  }
  return s;
}
function searchView() {
  const words = searchWords(S.q);
  if (!words.length) return listPage(`Axtarış: “${S.q}”`, "Ən azı iki hərf yazın", []);
  // Axtarış bölmə arxivlərini də (5 gün) görür.
  CATS.forEach(c => loadArchive(c.slug));
  const topics = searchTopics(S.q), scored = [];
  for (const a of allNews()) {
    if (a.category === "idman" && topics.some(name => clubMatches(a, name))) { scored.push({ a, score: 20 }); continue; } // idman kimi bütün dillərdə, ən yenisi üstdə
    if (S.lang && langOf(a) !== S.lang) continue;
    const {t, rest} = searchText(a);
    let score = 0, hits = 0;
    for (const w of words) {
      if (t.includes(w)) { score += 3; hits++; }
      else if (rest.includes(w)) { score += 1; hits++; }
    }
    if (!hits) continue;
    if (hits === words.length) score += 5; // bütün sözlər var
    scored.push({ a, score });
  }
  scored.sort((x, y) => y.score - x.score || newest(x.a, y.a));
  const list = scored.map(x => x.a);
  const all = scored.filter(x => x.score >= 5).length;
  const desc = topics.length ? `${topics.join(", ")}: bütün dillərdə, son 5 günün xəbərləri.` : words.length > 1 ? `${all} xəbərdə bütün sözlər, ${list.length - all} xəbərdə bəziləri var. Uyğunluğa görə sıralanıb.` : "Başlıq, xülasə və mənbə adına görə, son 5 gün. Uyğunluğa görə sıralanıb.";
  S.hl = hlRegex(words);
  const q = S.q.trim(), b = new TextEncoder().encode(q);
  return listPage(`Axtarış: “${S.q}”`, desc, list, b.length < 46 - tgPre().length ? tgIzle("q_" + btoa(String.fromCharCode(...b)).replace(/\+/g, "-").replace(/\//g, "_").replace(/=/g, ""), `«${q}»`) : "");
}
// Axtarışda uyğun sözlər işarələnir.
function highlightSearch() {
  const rx = route().name === "search" ? S.hl : null;
  if (!rx) return;
  document.querySelectorAll("#view .card h2").forEach(h => { // axtarış kartının başlığı h2-dir (listPage): köhnə h3 seçicisi heç nə tapmırdı
    const text = h.textContent;
    if (!rx.test(text)) return;
    rx.lastIndex = 0;
    h.innerHTML = text.split(rx).map((p, i) => i % 2 ? `<mark>${esc(p)}</mark>` : esc(p)).join(""); // əvvəl esc, sonra işarə: «&#39;» içində rəqəm tutulmasın
  });
}

function ratesView() {
  const items = S.markets || [];
  const rows = items.map(i => {
    const up = Number(i.changePct) > 0, down = Number(i.changePct) < 0;
    return `<tr><th scope="row">${marketIcon(i.id)}${esc(i.label)}</th><td>${esc(Number(i.value).toFixed(i.dec ?? 2))} ${esc(i.unit || "")}</td><td class="${up ? "up" : down ? "down" : ""}">${i.changePct == null ? "—" : `${up ? "+" : ""}${esc(Number(i.changePct).toFixed(2))}%`}</td><td class="muted">${esc(i.src || "")}</td></tr>`;
  }).join("");
  const asOf = items.find(i => i.asOf)?.asOf;
  return `<div class="page-h"><div><h1>Valyuta məzənnəsi</h1><p>Dollar, avro, rubl və lirənin manatla məzənnəsi, neft və qızıl qiyməti${asOf ? ` · ${esc(asOf)}` : ""}.</p></div></div>
    ${rows ? `<div class="svc-wrap"><table class="svc-table"><thead><tr><th>Ad</th><th>Qiymət</th><th>Dəyişmə</th><th>Mənbə</th></tr></thead><tbody>${rows}</tbody></table></div>` : `<p class="empty">Məzənnə məlumatı yüklənir.</p>`}`;
}
function leagueView() {
  wantSports();
  return `<div class="page-h"><div><h1>Premyer Liqa cədvəli</h1><p>Azərbaycan Premyer Liqasının turnir cədvəli və digər liqalar.</p></div></div>${footballBlock(S.data?.articles || [])}`;
}
// Komanda faylı gələn kimi çəkilir (lentin toplama fasiləsi aid deyil).
const teamRender = () => { if (route().name === "team") renderView(); else requestRender(false); };
const teamModule = r => (S.teamMod ||= import("./komanda.js")).then(m => { m.prefetch?.({ S, requestJSON, freshUrl, requestRender: teamRender }, r); return m; });
function preTeam() {
  if (S.teamPre) return;
  S.teamPre = true;
  for (const [f, rel] of [["komanda.js", "modulepreload"], ["komanda.css", "preload"]]) { const l = document.createElement("link"); l.rel = rel; if (rel === "preload") l.as = "style"; l.href = `${ASSET}${f}`; document.head?.append?.(l); }
  teamModule().catch(() => {});
}
function teamView(r) {
  if (S.teamPage) return S.teamPage.view(r);
  if (!S.teamLoading && Date.now() - (S.teamFailedAt || 0) > 30e3) {
    S.teamLoading = true;
    const css = new Promise(done => { const link = document.createElement("link"); link.rel = "stylesheet"; link.href = `${ASSET}komanda.css`; link.onload = link.onerror = done; document.head.append(link); });
    Promise.all([teamModule(r), css]).then(([{ mountTeam }]) => {
      S.teamPage = mountTeam({ S, esc, card, byDate, sized, shortDT, ordinal: ordTur, ago, decode, clubMatches, topics: SPORT_TEAMS.flatMap(g => g.items).filter(t => t.name !== "Milli komanda"), withArchive, loadArchive, months: MONTHS, requestJSON, freshUrl, requestRender: teamRender });
      requestRender(false);
    }).catch(() => { S.teamLoading = false; S.teamMod = null; S.teamFailedAt = Date.now(); requestRender(false); });
  }
  return S.teamFailedAt ? netErr("Komanda səhifəsi açılmadı") : skeleton();
}
function trafficView() {
  const area = tixArea(), konum = geoArea();
  const items = localRoadItems(S.data?.articles || []).slice(0, 40);
  const jump = a => `<button type="button" class="pill${a.id === area.id ? " on" : ""}" data-act="tix-area" data-area="${a.id}" aria-pressed="${a.id === area.id ? "true" : "false"}">${esc(a.label)}</button>`;
  const jumps = (konum ? jump(konum) : `<button type="button" class="pill" data-act="geo"${S.geoBusy ? " disabled" : ""}>${S.geoBusy ? "Konum axtarılır…" : "📍 Konumum"}</button>`) + TRAFFIC_AREAS.map(jump).join("") + (S.geoErr && !konum ? `<span class="geo-err">${esc(S.geoErr)}</span>` : "");
  const rush = bakuRush() ? `<a class="rush" href="#/tixac">Pik saat — xəritəyə baxın</a>` : "";
  // Telefonda tıxac Yandex-dən.
  const map = S.tixOn
    ? TOUCH_UI
      ? `<iframe title="Canlı tıxac xəritəsi (Yandex)" src="${esc(yandexSrc(area))}" loading="lazy" allowfullscreen referrerpolicy="no-referrer-when-downgrade"></iframe>`
      : `<iframe title="Waze canlı xəritə" src="${esc(wazeSrc(area))}" loading="lazy" allowfullscreen referrerpolicy="no-referrer-when-downgrade"></iframe>`
    : `<div class="tix-open"><p>Xəritə yalnız açanda yüklənir.</p><button type="button" class="btn" data-act="tix-open">Xəritəni aç</button></div>`;
  const rows = items.length
    ? `<ul class="tix-list">${items.map(a => `<li><a href="${safeHref(a.sourceUrl || "#")}" ${OUT}><span class="ic" aria-hidden="true">${a.icon}</span><span class="tt">${txt(a.title)}</span><span class="meta">${sourceName(shownSource(a))} · ${ago(a.publishedAt)}</span></a></li>`).join("")}</ul>`
    : `<p class="empty">Son 2 saatda Bakı və Abşeron üzrə uyğun yol xəbəri tapılmadı. Bu, yollarda tıxac olmadığı demək deyil. Cari vəziyyəti xəritədə yoxlayın.</p>`;
  return `<div class="page-h"><div><h1>Tıxac və yollar</h1><p>Bakı və Abşeronun canlı yol vəziyyəti.</p></div><span class="cnt">${items.length} xəbər</span></div>
    <p class="tix-note">${TOUCH_UI ? "Telefonda canlı xəritə Yandex Xəritələrdən açılır; Waze telefonda xəritəni yalnız öz tətbiqində göstərir, aşağıdakı düymə onu açır." : "Xəritə Waze-dən açılır."} Aşağıda yalnız son 2 saatın Bakı və Abşeron üzrə yol xəbərləri göstərilir; bunlar canlı tıxac ölçüləri deyil.</p>
    ${rush}
    <div class="tix-jumps">${jumps}</div>
    <div class="tix-map" id="tix-map">${map}<div class="tix-bar">${TOUCH_UI ? `<a href="${esc(wazeApp(area))}" ${OUT}>Waze-də aç</a>` : `<a href="${esc(wazeLive(area))}" ${OUT}>Xəritəni tam ekranda aç</a>`}</div></div>
    ${rows}`;
}

// Yalnız dəyişən blok yenilənir.
const PATCH_INSIDE = ".top2,.hero,.hero-strip,.hero-row,.prez,.prez-body,.prez-lent";
const KEYED = ".hero-row,.prez-lent"; // sürüşən siyahılar: yeri dəyişən kart köçürülür (şəkli təzədən yüklənmir), oxunan kart ekranda yerində qalır
function rememberSrc(node) {
  node._src = node.outerHTML;
  if (node.matches(PATCH_INSIDE)) [...node.children].forEach(rememberSrc);
}
function anchorOf(box) {
  const x = box.matches(".hero-row"), pos = x ? box.scrollLeft : box.scrollTop;
  const at = n => x ? n.offsetLeft - box.firstElementChild.offsetLeft : n.offsetTop - box.firstElementChild.offsetTop;
  const kid = box.firstElementChild && [...box.children].find(n => at(n) + (x ? n.offsetWidth : n.offsetHeight) > pos + 2);
  return kid && { kid, off: pos - at(kid), x, at };
}
function restoreAnchor(box, a) {
  if (!a || !a.kid.isConnected) return;
  const was = box.style.scrollBehavior; box.style.scrollBehavior = "auto";
  if (a.x) box.scrollLeft = a.at(a.kid) + a.off; else box.scrollTop = a.at(a.kid) + a.off;
  box.style.scrollBehavior = was;
}
function patchChildren(box, fresh, changed) {
  const old = [...box.children], keyed = !!box.matches?.(KEYED), pool = keyed && new Map(old.map(n => [n._src, n])), kept = new Set(), anchor = keyed && anchorOf(box);
  fresh.forEach((node, i) => {
    rememberSrc(node);
    let was = old[i];
    if (keyed) {
      const hit = pool.get(node._src);
      if (hit) { pool.delete(node._src); kept.add(hit); if (box.children[i] !== hit) box.insertBefore(hit, box.children[i] || null); return; }
      was = null;
    }
    if (was && was._src === node._src) return;
    if (was?.matches(PATCH_INSIDE) && was.className === node.className) { was._src = node._src; patchChildren(was, [...node.children], changed); return; }
    // Açılmış bölmə yenilənəndə bağlanmasın.
    if (was?.matches(".lazy-sec") && was.firstChild && node.matches(".lazy-sec")) lazyFill(node);
    if (was) was.replaceWith(node); else box.insertBefore(node, box.children[i] || null);
    changed.push(node);
  });
  // Slayderin oxları və nöqtələri səhifə sətrində yoxdur: silinmir (silinəndə slayd nöqtəsiz qalır, altındakı məzmun 12 px oynayırdı); say dəyişəndə yenidən qurulur.
  if (keyed) { old.forEach(n => kept.has(n) || n.remove()); restoreAnchor(box, anchor); if (old.length !== fresh.length) changed.push(box); } else old.slice(fresh.length).forEach(node => node.matches(".st-btn,.st-dots") || node.remove());
}
function patchView(v, page) {
  const next = document.createElement("template");
  next.innerHTML = page; // uzaq bölmələr səhifə sətrində deyil (lazySection → lazyHtml), yalnız açarlı boş qutular
  if (S.lateDone === lateKey()) next.content.querySelectorAll?.("template[data-late]").forEach(t => { const c = lateContent(t); if (c) t.replaceWith(c); });
  S.tr?.(next.content);
  const changed = [];
  // Hazır ilk ekranın sarğısı açılır, kartlar yerində qalır.
  const pre = v.querySelector?.(":scope > .pre-skel");
  if (pre) {
    v.querySelector(":scope > noscript")?.remove();
    const kids = [...pre.children];
    kids.forEach(rememberSrc);
    pre.replaceWith(...kids);
    changed.push(...kids);
    for (const i of v.querySelectorAll("img[data-fail=alt][src]")) if (i.complete && (i.naturalWidth || 0) < 2) imgFail(i);
  }
  patchChildren(v, [...next.content.children], changed);
  wire(changed);
}
// Yeni (və ya geri qoyulan) düyünlərin qurğuları: slayder oxları və şəkilləri, lentlər, uzaq bölmələr, gec doldurma.
function wire(changed) {
  if (!changed.length) return;
  const has = sel => changed.some(n => n.matches(sel) || n.querySelector(sel));
  if (has("[data-marquee]")) setupMarquees();
  setupStrips(new Set(changed.flatMap(n => [n.closest(".strip"), ...n.querySelectorAll(".strip")]).filter(Boolean))); // içəridən yenilənən slayderin oxları da
  if (has(".hero-strip") || has(".hero-main")) setupHeroImages();
  setupFeatureLents();
  setupLazySections();
  if (has("template[data-late]")) idle(lateFill);
}
const idle = (fn, ms = 200, max = 1500) => (globalThis.requestIdleCallback || (f => setTimeout(f, ms)))(fn, { timeout: max });
// Ana səhifənin DOM-u kənara çıxanda saxlanır, qayıdışda geri qoyulur (2026-11-09). Hər qayıdış homeView()-u yenidən qururdu: ~150 KB
// sətir, şablon təhlili, rememberSrc, telefonda (4×) görünən kadr 336–576 ms. Açarın ilk üç sahəsi (lent, arxiv, dəqiqə) yumşaqdır:
// saxlanan DOM dərhal qayıdır, boş anda adi çəkiliş onu təzələyir; başqa sahə (dil, sıra, seçilmişlər…) fərqlənirsə atılır, köhnə yol.
const homeKey = () => [S.data, S.arxV, Date.now() / 6e4 | 0, S.og, S.lang, S.latestOrder, S.latestCount, S.prezOpen, S.fbTab, S.fbLeague, S.video, S.football, S.sports, S.social, S.warn, S.ads, S.dinOn, S.error, storage.getItem(SAVE_KEY), storage.getItem(SECT_KEY)];
const keyDiff = (a, b) => a.reduce((d, x, i) => x === b[i] ? d : i < 3 ? d || 1 : 2, 0); // 0 eyni, 1 yumşaq, 2 atılır
function keepHome(v) {
  S.homeKeep = null;
  if (!S.data || S.partial || !S.viewPage || !v.firstChild) return;
  const frag = document.createDocumentFragment();
  frag.append(...v.childNodes);
  S.homeKeep = { frag, page: S.viewPage, key: homeKey(), at: Date.now() };
  S.viewPage = null;
}
function restoreHome(v) {
  const k = S.homeKeep;
  if (!k) return false;
  S.homeKeep = null;
  const d = S.data && !S.partial && Date.now() - k.at < NEWS_FULL_MS ? keyDiff(homeKey(), k.key) : 2;
  if (d === 2) return false;
  v.replaceChildren(k.frag);
  S.viewPage = k.page;
  shut("details.altpop[open], details.social-details[open]" + (S.svcOpen ? "" : ", details.service-panel[open]")); // təzə qurulan səhifədəki kimi bağlı
  S.lateDone = v.querySelector("template[data-late]") ? 0 : lateKey(); // dolmuş siyahı yenidən şablona düşməsin
  wire([...v.children]);
  if (d) idle(renderView, 500, 2000); // lent və ya dəqiqə dəyişib: boş anda adi çəkiliş (eyni səhifədirsə DOM-a toxunmur)
  return true;
}
function renderView() {
  syncQuery();
  pageMeta();
  try {
    const v = $("#view");
    const onlyFirst = S.partial && !partialOk();
    const r = route();
    // Paylaşılan keçid: tam lent gözlənilmir (loadShared).
    const shared = r.name === "team" || r.name === "article" && S.sharedStory?.id === r.id;
    // Hazır ilk ekran: məlumat gələnə qədər durur.
    const pre = !S.data && firstScreen() && !!v.querySelector?.(".pre-skel[data-prerender]");
    if (S.error && (!S.data || onlyFirst) && !shared) {
      const alert = netErr("Xəbər lenti yüklənə bilmədi");
      if (pre) { if (!v.querySelector(".err")) v.insertAdjacentHTML("afterbegin", alert); return; }
      S.viewPage = null; v.innerHTML = alert; return;
    }
    if ((!S.data || onlyFirst) && !shared) { if (pre) return; S.viewPage = null; v.innerHTML = skeleton(r.name === "article" ? "article" : ""); return; }
    const err = S.error ? `<div class="err" role="status">Son yenilənmə alınmadı. Saxlanmış xəbərlər göstərilir. <button class="btn" data-act="retry">Yenidən yoxla</button></div>` : "";
    if (r.name === "section" && r.slug === "idman") preTeam();
    const home = r.name === "home" && !S.q;
    if (S.viewHome && !home) keepHome(v); // ana səhifənin DOM-u kənara çıxanda saxlanır (restoreHome)
    if (!home || !restoreHome(v)) {
      const body = r.name === "rates" ? ratesView() : r.name === "league" ? leagueView() : r.name === "article" ? articleView(r.id) : r.name === "sources" ? sourcesView() : r.name === "about" ? aboutView() : r.name === "notfound" ? `<div class="empty"><h1 style="color:var(--fg)">Səhifə tapılmadı</h1><p>Belə ünvan yoxdur.</p><a href="#/" style="color:var(--primary);font-weight:700">← Baş səhifəyə qayıt</a></div>` : r.name === "saved" ? savedView() : r.name === "sections" ? sectionsView() : r.name === "videos" ? videosView() : r.name === "traffic" ? trafficView() : r.name === "team" ? teamView(r) : S.q ? searchView() : r.name === "section" ? sectionView(r.slug) : homeView();
      // Məzmun dəyişməyibsə DOM toxunulmur.
      const page = err + body;
      if (page !== S.viewPage) { S.viewPage = page; patchView(v, page); }
    }
    S.viewHome = home && !S.partial;
    const tab = r.name === "saved" ? "saved" : r.name === "traffic" ? "traffic" : r.name === "section" && r.slug === "video" ? "video" : r.name === "home" && !S.q ? "home" : "";
    document.querySelectorAll(".tabbar [data-tab]").forEach(el => el.classList.toggle("on", el.dataset.tab === tab));
    highlightSearch();
  } finally { countVisit(); }
}

function sourceLevel(s) {
  const t = new Date(s.okAt || 0).getTime();
  const age = Number.isNaN(t) ? Infinity : Date.now() - t;
  if (!s.error && s.count > 0 && age < 6 * HOUR) return "ok";
  if (s.okAt && age < 36 * HOUR) return "warn";
  return "bad";
}

// Nadir səhifələr sehife.js-dədir.
function loadPages() {
  if (S.pages || S.pagesAsked) return;
  S.pagesAsked = true;
  import("./sehife.js").then(m => { S.pages = m; if (["sources", "about", "sections"].includes(route().name)) renderView(); }).catch(() => { S.pagesAsked = false; });
}
function pageView(name) {
  if (S.pages) return S.pages[name]({ S, esc, sourceName, shownSource, removedSource, sourceLevel, ago, trackedSources, sectionPref, CATS, ASSISTANT_ON, DRIVER_ON, config: window.SITE_CONFIG || {} });
  loadPages();
  return `<div class="empty">Yüklənir…</div>`;
}
// Niyyətlə əvvəlcədən yükləmə (2026-11-09): barmaq keçidə toxunan andan (pointerdown) klikə ~100 ms var — bölmənin arxivi, cədvəlin idman
// faylı, nadir səhifələrin modulu, komanda modulu o anda istənir; kompüterdə kursor menyuda 120 ms dayananda (bindNavPop). Açılışa iş düşmür.
function preload(h) {
  const [, p, s] = (h || "").match(/^#\/(bolmeler|bolme|komanda|haqqinda|menbeler)(?:\/([^/?#]+))?/) || [];
  if (p === "komanda") preTeam();
  else if (p === "bolme") { if (s === "cedvel") wantSports(); else if (s && !SERVICE_ROUTES[s] && S.data && !S.partial) loadArchive(SECTION_ALIAS[s] || s); }
  else if (p) loadPages();
}
const hashOf = a => a?.getAttribute("href")?.replace(/^\/(bolme\/[^/?#]+).*/, "#/$1");
document.addEventListener("pointerdown", e => { const h = hashOf(e.target.closest?.("a[href]")); if (h?.[0] == "#") preload(h); }, { passive: true, capture: true });
const sourcesView = () => pageView("sourcesView"), aboutView = () => pageView("aboutView"), sectionsView = () => pageView("sectionsView");
function trackedSources() {
  const rows = S.sources?.sources;
  const names = rows ? rows.filter(s => !removedSource(s)).map(s => s.name) : (S.data?.articles ?? []).flatMap(a => [shownSource(a), ...(a.alts || []).map(x => x.source)]);
  return [...new Set(names.filter(Boolean))].sort((a, b) => a.localeCompare(b, "az"));
}
function renderFooter() {
  const srcs = trackedSources();
  const contact = String(window.SITE_CONFIG?.contact || "").trim();
  const h = `<div class="wrap fgrid">
    <div><div class="logo">${LOGO}</div><p style="margin:0">Azərbaycan və dünyadan son xəbərlər — hər dəqiqə avtomatik yenilənən xəbər lenti. Xəbərləri və eyni hadisə üzrə mənbələri bir yerdə izləyin.</p>${contact ? `<p class="fcontact">Əlaqə: <a href="mailto:${esc(contact)}">${esc(contact)}</a></p>` : ""}</div>
    <div><h4>Bölmələr</h4><div class="fcats">${CATS.map(c => `<a href="/bolme/${c.slug}/">${esc(c.label)}</a>`).join("")}</div></div>
    <div><h4>Xidmətlər</h4><div class="fcats"><a href="/bolme/valyuta/">Valyuta məzənnəsi</a><a href="/bolme/cedvel/">Premyer Liqa cədvəli</a><a href="/bolme/tixac/">Tıxac və yollar</a></div></div>
    <div><h4>İzlənilən mənbələr</h4><div class="srcs">${srcs.slice(0, 12).map(s => `<span>${sourceName(s)}</span>`).join("")}</div><a class="more" href="#/menbeler">Bütün mənbələr (${srcs.length}) →</a></div>
  </div><div class="copy">© ${new Date().getFullYear()} 8ulduz. Bütün xəbər mətnlərinin hüququ müvafiq mənbələrə aiddir. <a href="./haqqinda/">Haqqımızda</a> · <a href="#/menbeler">Mənbə vəziyyəti</a> · <a href="./mexfilik/">Məxfilik siyasəti</a></div>`;
  if (h !== S.footH) S.footH = $("#footer").innerHTML = h;
}


function savedView() {
  const items = savedList().filter(a => !policyViolation(a));
  return `<div class="page-h"><div><h1>Seçilmişlər</h1><p>Ulduzla saxladığınız xəbərlər bu cihazda qalır.</p></div><span class="cnt">${items.length}</span></div>` +
    (items.length ? `<div class="grid">${items.map(card).join("")}</div><p style="margin:14px 0 0"><button type="button" class="loadmore" data-act="clear-saved">Hamısını sil (${items.length})</button></p>` : `<p class="empty">Hələ seçilmiş xəbər yoxdur. Kartdakı ulduza basın.</p>`);
}

// Yalnız ümumi say gedir, şəxsi məlumat yoxdur (source-stats.js).
function trackEvent(path, a) {
  gaQ.push([visitPath(), document.title, void 0, path, a]); gaFlush();
  try { window.goatcounter?.count?.({ path, title: path, event: true, no_session: true, referrer: "" }); } catch {}
}
addEventListener("click", e => { const h = innerWidth <= 600 && e.target.closest?.(".prez-h"); if (h && !e.target.closest(".btn")) { e.preventDefault(); h.parentNode.classList.toggle("open", S.prezOpen = !S.prezOpen); } }, true);
// Orta düymə (auxclick, button 1) də keçiddir; sağ düymə (2) sayılmır. «click» yalnız sol düymədə gəlir: bir klik bir hadisədir.
for (const t of ["click", "auxclick"]) addEventListener(t, e => { const a = e.target.closest?.("a"); if (!a) return; if (a.target === "_blank") { if (a.host && a.host !== location.host && e.button < 2) trackEvent("out-" + a.host, a); return; } if (e.button || e.metaKey || e.ctrlKey || e.shiftKey || e.altKey) return; const m = /^\/((xeber|bolme)\/[^/?#]+)/.exec(a.getAttribute("href")); if (m) { e.preventDefault(); location.hash = "#/" + m[1]; } }, true);
function closeSharePop() { document.querySelector(".sharepop")?.remove(); }
function showPop(btn, html) {
  closeSharePop();
  const box = document.createElement("div"), r = btn.getBoundingClientRect();
  box.className = "sharepop";
  box.innerHTML = html;
  document.body.append(box);
  const w = box.offsetWidth, h = box.offsetHeight;
  box.style.left = `${Math.max(8, Math.min(innerWidth - w - 8, r.right - w))}px`;
  box.style.top = `${r.top - h - 6 < 8 ? r.bottom + 6 : r.top - h - 6}px`;
  return box;
}
const shareTitle = el => el.dataset?.title || el.closest("article")?.querySelector("h2,h3,.t")?.textContent.trim() || ""; // sosial yazı: «İlham Əliyev: …»
function shareStory(btn) {
  if (navigator.share && globalThis.matchMedia?.("(hover:none)").matches) { trackEvent("share-sys"); const title = shareTitle(btn), url = btn.dataset.share; navigator.share({ title, text: title, url }).catch(() => {}); return; }
  const box = showPop(btn, Object.entries(SHARE_TO).map(([k, v]) => `<button type="button" data-to="${k}">${shIcon(k)}${v[0]}</button>`).join("") + `<button type="button" data-to="cp">${shIcon("cp")}Keçidi kopyala</button>` + (navigator.share ? `<button type="button" data-to="sys">Başqa…</button>` : ""));
  box.dataset.share = btn.dataset.share; box.dataset.title = shareTitle(btn);
}
async function shareTo(t) {
  const box = t.closest(".sharepop"), url = box?.dataset.share || "", title = box?.dataset.title ?? shareTitle(t), to = t.dataset.to;
  trackEvent(`share-${to}`);
  if (to === "cp") { // başlıq + keçid: yapışdırılanda hansı xəbər olduğu görünür
    try { await navigator.clipboard.writeText(title ? `${title}\n${url}` : url); t.textContent = "Kopyalandı"; } catch { t.textContent = "Kopyalanmadı"; }
    setTimeout(closeSharePop, 1400);
    return;
  }
  closeSharePop();
  if (to === "sys") { try { await navigator.share({ title, text: title, url }); } catch {} return; }
  const u = SHARE_TO[to]?.[1](encodeURIComponent(url), encodeURIComponent(title));
  if (u) openOut(u);
}
const isStandalone = () => matchMedia("(display-mode: standalone)").matches || navigator.standalone === true;
const isIOS = () => /iPhone|iPad|iPod/.test(navigator.userAgent || "");
// Sahib, 2026-11-10: «Ana ekrana» telefonda həmişə görünsün. Brauzer təklif vermirsə (Facebook/Instagram daxili brauzeri,
// Samsung Internet, Firefox, Chrome-un imtinadan sonrakı fasiləsi) düymə əllə əlavə etmə yolunu göstərir. Kompüterdə yalnız təklif olanda.
const isPhone = () => isIOS() || matchMedia("(hover:none)").matches; // Android telefon da hover:none
function installBtn() {
  if (isStandalone() || (!S.installEvt && !isPhone())) return "";
  return `<button type="button" class="install-btn" data-act="install">Ana ekrana əlavə et</button>`;
}
async function installApp(btn) {
  if (!S.installEvt) {
    trackEvent("install-hint");
    import(`${ASSET}ana-ekran.js`).then(m => showPop(btn, m.hint(navigator.userAgent || "", isIOS()))).catch(() => {});
    return;
  }
  const prompt = S.installEvt;
  S.installEvt = null;
  try {
    prompt.prompt();
    const choice = await prompt.userChoice;
    trackEvent(`install-${choice?.outcome || "unknown"}`);
  } catch {}
  renderLangs();
}
// Son düymə: xəbərlərə keçilir.
// «N yeni xəbər»: «Ən yeni» siyahısına qayıdır.
function jumpToLatest() {
  const sec = route().name === "home" ? document.getElementById("son-xeberler") : null;
  if (!sec) { window.scrollTo(0, 0); return; }
  const head = document.getElementById("sitehead");
  const stuck = head && getComputedStyle(head).position === "sticky" ? head.getBoundingClientRect().height : 0;
  window.scrollTo({ top: Math.max(0, sec.getBoundingClientRect().top + scrollY - stuck - 8), behavior: "smooth" });
}
function scrollToClub() {
  if (S.club && !SUB_TABS[route().slug]?.find(x => x.name === S.club)?.groups) $("#view")?.scrollIntoView({ block: "start" });
}
const shut = sel => document.querySelectorAll(sel).forEach(d => { d.open = false; }); // açıq <details> bağlanır
function onClick(e) {
  if (!e.target.closest(".sharepop")) closeSharePop();
  const soc = e.target.closest(".soc-g a"), app = soc && chromeLink(soc.href); // rəsmi hesab: Android-də Chrome vərəqində, geri sayta
  if (app) { e.preventDefault(); location.href = app; return; }
  if (S.langOpen && !e.target.closest(".ldd")) { S.langOpen = false; renderTopbar(); } // dil siyahısı kənara hər toxunuşda bağlanır
  const t = e.target.closest("[data-feed],[data-id],[data-act],[data-lang],[data-to],[data-club],[data-city],[data-fx],[data-yt],[data-fbtab],[data-fbleague]");
  if (!e.target.closest(".altpop")) shut("details.altpop[open]");
  if (!e.target.closest(".nav-more")) shut(".nav-more[open]");
  // Açılan bölmələr kənara basanda bağlanır
  if (!e.target.closest("details.service-panel, details.social-details")) shut("details.service-panel[open], details.social-details[open]");
  if (!t) {
    let dirty = false;
    if (S.wxOpen && !e.target.closest(".wx")) { S.wxOpen = false; dirty = true; }
    if (S.prayOpen && !e.target.closest(".pray-wrap")) { S.prayOpen = false; dirty = true; }
    if (S.fxOpen && !e.target.closest(".fx-pop") && !e.target.closest("[data-fx]")) { S.fxOpen = false; dirty = true; }
    if (dirty) { renderTopbar(); renderMarkets(); }
    return;
  }
  if (t.dataset.act === "share" || t.dataset.to) {
    e.preventDefault();
    e.stopPropagation();
    if (t.dataset.to) shareTo(t); else shareStory(t);
    return;
  }
  if (t.dataset.act === "dinle") { // «Dinlə» (assets/dinle.js, yalnız basılanda)
    e.preventDefault(); e.stopPropagation();
    t.closest(".hero-strip")?.querySelector('.hero-pause[aria-pressed="false"]')?.click(); // slayder dayanır
    const id = t.dataset.id, a = [...(S.data?.articles || []), ...Object.values(S.archive || {}).flatMap(x => x.rows || []), S.sharedStory?.row, S.art].find(x => x && x.id === id) || S.art;
    (S.dinle ||= import(`${ASSET}dinle.js`).then(m => m.createPlayer({ list: () => byDate(S.data?.articles || []), decode, onState: s => { S.dinOn = s.playing && s.id; for (const b of document.querySelectorAll("[data-act=dinle]")) b.textContent = b.dataset.id === s.id && s.msg || (b.dataset.id === S.dinOn ? "■ Bitir" : "Dinlə"); if (s.msg && !s.playing) setTimeout(() => { for (const b of document.querySelectorAll("[data-act=dinle]")) if (b.textContent === s.msg) b.textContent = "Dinlə"; }, 3e3); } }))).then(p => p.playing && p.id === a?.id ? p.stop() : p.play(a)).catch(() => {}); // 2-ci basış: dayan
    return;
  }
  if (t.dataset.act === "install") {
    e.preventDefault();
    installApp(t);
    return;
  }
  if (t.dataset.act === "star") {
    e.preventDefault();
    e.stopPropagation();
    const id = t.dataset.save;
    const a = byId.get(id) || Object.values(S.archive || {}).flatMap(x => x.rows).find(x => x.id === id) || savedList().find(x => x.id === id);
    if (a) {
      toggleSave(a);
      const on = isSaved(id);
      document.querySelectorAll(`[data-save="${CSS.escape(id)}"]`).forEach(el => {
        el.classList.toggle("on", on);
        el.textContent = on ? "★" : "☆";
        el.setAttribute("aria-pressed", on ? "true" : "false");
        el.setAttribute("aria-label", on ? "Seçimdən çıxar" : "Seçilmişlərə saxla");
      });
      if (route().name === "saved") renderView();
    }
    return;
  }
  if (t.dataset.feed) { S.latestOrder = t.dataset.feed; S.latestCount = 8; renderView(); return; }
  if (t.dataset.yt) {
    const box = t.querySelector(".thumb");
    if (box && !box.querySelector("iframe")) box.innerHTML = `<iframe src="https://www.youtube-nocookie.com/embed/${encodeURIComponent(t.dataset.yt)}?autoplay=1" allow="autoplay; encrypted-media; picture-in-picture" allowfullscreen title="Video"></iframe>`;
    return;
  }
  if (t.dataset.fx && !e.target.closest(".fx-pop")) { S.fxFrom = t.dataset.fx; S.fxTo = "AZN"; S.fxOpen = true; renderMarkets(); return; }
  if (t.dataset.fbtab) { S.fbTab = t.dataset.fbtab; renderView(); return; }
  if (t.dataset.fbleague !== undefined) { S.fbLeague = Number(t.dataset.fbleague) || 0; const L = fbLeagues()[S.fbLeague]; S.fbTab = L?.world ? 0 : (S.fbTab === "table" && !L?.table?.length) || S.fbTab >= 0 ? "results" : S.fbTab; renderView(); return; }
  if (t.dataset.lang !== undefined) { setLang(t.dataset.lang); return; }
  if (t.dataset.club !== undefined) {
    const pop = t.closest(".nav-pop");
    S.club = t.dataset.club || null; S.clubSlug = pop?.dataset.slug || route().slug;
    // Yalnız bu bölmənin başlıqları («Qarabağ» həm komanda, həm bölgədir).
    const tabs = SUB_TABS[pop?.dataset.slug || route().slug] || [];
    if (!S.club) S.sportTab = null; else if (tabs.some(x => x.name === S.club)) S.sportTab = S.club; else if (pop) S.sportTab = pop.dataset.tab;
    if (pop && route().slug !== pop.dataset.slug) { S.keepClub = true; location.hash = `#/bolme/${pop.dataset.slug}`; return; }
    S.shown = PAGE; renderView();
    scrollToClub();
    return;
  }
  if (t.dataset.city) { S.wxSel = t.dataset.city; renderTopbar(); return; }
  const act = t.dataset.act;
  if (act === "latest-more") { S.latestCount = (S.latestCount || 8) + 8; renderView(); }
  else if (act === "wx") { S.wxOpen = !S.wxOpen; S.wxSel = null; renderTopbar(); if (S.wxOpen) loadAllWeather(); }
  else if (act === "wx-close") { S.wxOpen = false; renderTopbar(); }
  else if (act === "wx-back") { S.wxSel = null; renderTopbar(); }
  else if (act === "apply-new") { S.renderPending = false; S.pendingNew = 0; syncNewPill(); if (route().name === "home") { S.latestOrder = "latest"; S.latestCount = 8; } render(); jumpToLatest(); }
  else if (act === "more") { S.shown += PAGE; renderView(); }
  else if (act === "clear-saved") { if (confirm("Bütün seçilmişlər silinsin?")) { storage.removeItem(SAVE_KEY); renderView(); } }
  else if (act === "find") { $("#sitehead")?.classList.add("q-open"); const q = $("#q"); q?.focus(); q?.scrollIntoView({ block: "center" }); }
  else if (act === "follow") import("./follow.js?v=7").then(m => m.openFollow(t, trackEvent, chromeLink)).catch(() => alert("İzləmə paneli açılmadı. Yenidən cəhd edin."));
  else if (act === "lang") { S.langOpen = !S.langOpen; renderTopbar(); }
  else if (act === "motion") toggleMotion();
  else if (act === "tix-open") { S.tixOn = true; renderView(); }
  else if (act === "tix-area") {
    const id = t.dataset.area || "merkez";
    if (id === tixArea().id && S.tixOn) return;
    S.tixArea = id; S.tixUser = true;
    renderView();
  }
  else if (act === "geo") { if (t.dataset.for === "pray") storage.removeItem(PRAY_CITY_KEY); if (route().name === "traffic") S.tixUser = false; locate(true); }
  else if (act === "pray") { S.prayOpen = !S.prayOpen; renderTopbar(); }
  else if (act === "fx-close") { S.fxOpen = false; renderMarkets(); }
  else if (act === "theme" || act === "fs-down" || act === "fs-up") setPref(act);
  else if (act === "notify") { if (notifyOn()) { storage.removeItem(NOTIFY_KEY); S.swReg?.periodicSync?.unregister("breaking").catch(() => {}); renderTicker(); } else armNotify(); }
  else if (act === "retry" || act === "refresh") { pollNews(true); }
  else if (act === "sec-toggle" || act === "sec-up" || act === "sec-down") {
    const slug = t.dataset.slug;
    const pref = sectionPref();
    if (act === "sec-toggle") {
      const off = new Set(pref.off);
      if (off.has(slug)) off.delete(slug); else off.add(slug);
      writeSects(pref.order, [...off]);
    } else {
      const i = pref.order.indexOf(slug);
      const j = act === "sec-up" ? i - 1 : i + 1;
      if (i < 0 || j < 0 || j >= pref.order.length) return;
      const order = pref.order.slice();
      [order[i], order[j]] = [order[j], order[i]];
      writeSects(order, pref.off);
    }
    renderView();
  }
}

const THEME_KEY = "8ulduz-theme", FS_KEY = "8ulduz-fs";
const SYS_LIGHT = globalThis.matchMedia?.("(prefers-color-scheme: light)"); // istinad saxlanır: yoxsa dinləyici itir
SYS_LIGHT?.addEventListener?.("change", () => { if (!storage.getItem(THEME_KEY)) { applyPrefs(); renderTopbar(); } });
function applyPrefs() {
  document.documentElement.dataset.motion = motionOff() ? "off" : "on";
  const saved = storage.getItem(THEME_KEY); // seçim yoxdursa telefonun rejimi (sahib, 2026-11-06); bilinməsə tünd
  const theme = saved === "light" || saved === "dark" ? saved : SYS_LIGHT?.matches ? "light" : "dark";
  document.documentElement.dataset.theme = theme;
  let fs = storage.getItem(FS_KEY);
  if (!/^[0-6]$/.test(fs || "")) fs = FS_STD;
  document.documentElement.dataset.fs = fs;
  const meta = document.querySelector('meta[name="theme-color"]');
  if (meta) meta.content = theme === "light" ? "#f6f4ee" : "#15233b";
}
function setPref(act) {
  if (act === "theme") {
    const next = document.documentElement.dataset.theme === "light" ? "dark" : "light";
    storage.setItem(THEME_KEY, next);
  } else {
    const n = Math.max(0, Math.min(6, Number(document.documentElement.dataset.fs || FS_STD) + (act === "fs-up" ? 1 : -1)));
    storage.setItem(FS_KEY, String(n));
  }
  applyPrefs();
  renderTopbar();
  setupMarquees();
  afterPaint(fitNav);
}
let visitSent = "", gaOn = 0;
const visitQueue = [], gaQ = [];
const gaFlush = () => { const id = window.SITE_CONFIG?.ga4; if (id && gaOn && gaQ.length) import("./ga.js?v=4").then(m => { for (const v of gaQ.splice(0)) m.hit(id, ...v); }).catch(() => {}); };
function visitPath() {
  const base = location.pathname || "/";
  const hash = location.hash || "";
  return !hash || hash === "#" || hash === "#/" ? base : base + hash;
}
function titlePending() {
  const r = route();
  return (r.name === "article" && (!S.data || S.archiveScanning)) || (r.name === "team" && !S.teamPage && !S.teamFailedAt);
}
function countVisit() {
  try {
    if (titlePending()) return;
    const path = visitPath();
    if (path === visitSent) return;
    visitSent = path;
    const vars = { path, title: document.title || "8ulduz" };
    gaQ.push([path, vars.title]); gaFlush();
    if (!String(window.SITE_CONFIG?.goatcounter || "").trim()) return;
    if (typeof window.goatcounter?.count === "function") window.goatcounter.count(vars);
    else visitQueue.push(vars);
  } catch {}
}
function flushVisits() {
  if (typeof window.goatcounter?.count !== "function") return;
  for (const vars of visitQueue.splice(0)) { try { window.goatcounter.count(vars); } catch {} }
}
function enableAnalytics() {
  gaOn = 1; gaFlush();
  const code = String(window.SITE_CONFIG?.goatcounter || "").trim();
  if (!code) return;
  const s = document.createElement("script");
  s.async = true;
  s.src = "https://gc.zgo.at/count.v4.js"; // versiya və həş: skript dəyişsə işləmir, sayt təsirlənmir
  s.integrity = "sha384-nRw6qfbWyJha9LhsOtSb2YJDyZdKvvCFh0fJYlkquSFjUxp9FVNugbfy8q1jdxI+";
  s.crossOrigin = "anonymous";
  s.dataset.goatcounter = `https://${code}.goatcounter.com/count`;
  s.dataset.goatcounterSettings = '{"no_onload":true}';
  s.addEventListener("load", flushVisits);
  document.head.appendChild(s);
}

/* Sakit olanda bir sətir/kart yuxarı keçir (~4s). Kursor, fokus və gizli vərəqədə dayanır. */
const STEP_MS = 4000;
const LEAVE_MS = 2000;
const WHEEL_MS = 3000;
const TOUCH_MS = 5000;
function reducedMotion() { return matchMedia("(prefers-reduced-motion: reduce)").matches; }
// Hərəkət düymə ilə dayanır; «hərəkəti azalt» varsa dayanıq.
const MOTION_KEY = "8ulduz-motion";
function motionOff() { const v = storage.getItem(MOTION_KEY); return v ? v === "off" : reducedMotion(); }
const motionBtn = () => `<button type="button" class="mo" data-act="motion" aria-pressed="${motionOff()}" title="${motionOff() ? "Hərəkəti başlat" : "Hərəkəti dayandır"}">${motionOff() ? "▶" : "Ⅱ"}</button>`;
function toggleMotion() { storage.setItem(MOTION_KEY, motionOff() ? "on" : "off"); applyPrefs(); S.tickerHtml = null; renderTicker(); setupMarquees(); setupFeatureLents(); }
function marqueeNarrow(el) {
  return !!el.closest(".prez") && matchMedia("(max-width: 860px)").matches;
}
function marqueeVisible(el) {
  if (el.classList.contains("prez-grid") && matchMedia("(max-width: 860px)").matches) return Number(el.dataset.visibleNarrow || 3);
  return Number(el.dataset.visible || 4);
}
function marqueeLocks(el) {
  if (marqueeNarrow(el)) return false;
  if (el.classList.contains("hero-side") && !matchMedia("(max-width: 900px)").matches) return false;
  return true;
}
function stepCols(el) {
  return el.classList.contains("prez-grid") && !matchMedia("(max-width: 860px)").matches ? 2 : 1;
}
function spanHeight(items, visible) {
  const n = Math.min(visible, items.length);
  if (n < 1) return 0;
  const top = items[0].offsetTop;
  let bottom = 0;
  for (let i = 0; i < n; i++) bottom = Math.max(bottom, items[i].offsetTop + items[i].offsetHeight);
  return bottom - top;
}
function marqueeUniform(el) {
  return el.classList.contains("prez-grid") || (el.classList.contains("soc-list") && !!el.closest(".prez"));
}
function contentTop(el, item) {
  return item.getBoundingClientRect().top - el.getBoundingClientRect().top + el.scrollTop;
}
function marqueeOf(node) {
  const wrap = node?.closest?.(".step-wrap");
  if (wrap) {
    const el = wrap.querySelector("[data-marquee]");
    if (el?.classList.contains("vmarquee")) return el;
  }
  const el = node?.closest?.("[data-marquee]");
  return el?.classList.contains("vmarquee") ? el : null;
}
function unwrapMarquee(el) {
  const wrap = el.parentElement;
  if (wrap?.classList.contains("step-wrap")) wrap.replaceWith(el);
}
function ensureWrap(el) {
  if (el.parentElement?.classList.contains("step-wrap")) return el.parentElement;
  const wrap = document.createElement("div");
  wrap.className = "step-wrap";
  el.parentNode.insertBefore(wrap, el);
  wrap.appendChild(el);
  return wrap;
}
function rowStops(el) {
  const items = [...el.children];
  if (!items.length) return [0];
  const cols = stepCols(el);
  const max = Math.max(0, el.scrollHeight - el.clientHeight);
  const stops = [0];
  for (let i = cols; i < items.length; i += cols) {
    const y = Math.round(contentTop(el, items[i]));
    if (y > max + 1) break;
    if (y - stops[stops.length - 1] > 2) stops.push(y);
  }
  if (Math.round(max) - stops[stops.length - 1] > 2) stops.push(Math.round(max)); // dib də dayanacaqdır: istifadəçi dibə çəkəndə siyahı geri qaçmır
  return stops;
}
function nearestStop(el) {
  const pos = rowStops(el);
  let best = pos[0], bestD = Infinity;
  for (const p of pos) {
    const d = Math.abs(el.scrollTop - p);
    if (d < bestD) { best = p; bestD = d; }
  }
  return { best, bestD, pos };
}
function pointerHeld(el) {
  if (el._mouse || el._key) return true;
  return false;
}
function autoOn(el) {
  if (!el.classList.contains("vmarquee")) return false;
  if (reducedMotion() || document.hidden || pointerHeld(el)) return false;
  return rowStops(el).length > 1;
}
function scheduleStep(el, delay) {
  clearTimeout(el._stepT);
  if (motionOff() || !el.classList.contains("vmarquee")) return;
  if (document.hidden || pointerHeld(el)) return;
  let wait = delay;
  if (el._holdUntil) wait = Math.max(wait, el._holdUntil - Date.now());
  el._stepT = setTimeout(() => {
    if (!el.classList.contains("vmarquee") || document.hidden || pointerHeld(el)) return;
    const { best, bestD } = nearestStop(el);
    if (bestD > 1) { animateTo(el, best); return; }
    advanceStep(el);
  }, Math.max(0, wait));
}
function cancelMotion(el) {
  el._animToken = (el._animToken || 0) + 1;
  clearTimeout(el._stepT);
  el.classList.remove("stepping");
}
function animateTo(el, to) {
  cancelMotion(el);
  const from = el.scrollTop;
  const dist = to - from;
  const token = el._animToken;
  if (Math.abs(dist) < 1 || motionOff()) {
    el.scrollTop = Math.round(to);
    scheduleStep(el, STEP_MS);
    return;
  }
  el.classList.add("stepping");
  const ms = Math.min(700, Math.max(380, Math.abs(dist) * 6));
  const t0 = performance.now();
  const ease = t => 1 - Math.pow(1 - t, 3);
  const frame = (now) => {
    if (el._animToken !== token) return;
    const p = Math.min(1, (now - t0) / ms);
    el.scrollTop = Math.round(from + dist * ease(p));
    if (p < 1) requestAnimationFrame(frame);
    else { el.scrollTop = Math.round(to); el.classList.remove("stepping"); scheduleStep(el, STEP_MS); }
  };
  requestAnimationFrame(frame);
}
function advanceStep(el) {
  if (!autoOn(el)) return;
  const pos = rowStops(el);
  const next = pos.find(p => p > el.scrollTop + 4);
  animateTo(el, next == null ? pos[0] : next);
}
function stopStep(el, snap) {
  cancelMotion(el);
  if (!snap) return;
  const { best, bestD } = nearestStop(el);
  if (bestD > 1) el.scrollTop = best;
}
// Uzaq bölmə boş qutudur, HTML yaddaşda. Sonu <!--lz-->: «N mənbə» də </template></div> ilə bitir.
const lazyHtml = new Map();
// Açar: eyni məzmun eyni açarı alır, S.viewPage müqayisəsi dəyişməz qalır. HTML səhifə sətrinə girmir: patchView-un şablon təhlili 392 KB-dan
// ~130 KB-a düşür (2026-11-09 ölçüsü, 39 bölmə). Sətrin xeşini brauzer özü hesablayır (Map açarı): JS-də FNV dövrü 105 KB-da 4×-də 2,2 ms,
// testlərin vm mühitində 13 ms idi; Map ilə 0,1 ms (2026-11-09 ölçüsü).
const KEYS = new Map(); let keyN = 0;
const keyOf = h => { const k = KEYS.get(h) || String(++keyN); recent(KEYS, h, k, 200); return k; };
function lazySection(html) {
  if (!html) return "";
  const k = keyOf(html);
  recent(lazyHtml, k, html, 99);
  return `<div class="lazy-sec" data-lazy="${k}"></div>`;
}
function lazyFill(box) {
  const h = lazyHtml.get(box.dataset.lazy);
  if (box.firstChild || h == null) return false;
  const t = document.createElement("template");
  t.innerHTML = h; S.tr?.(t.content); box.replaceChildren(t.content);
  return true;
}
function setupLazySections() {
  S.lazyIO?.disconnect();
  const show = box => {
    if (!lazyFill(box)) return;
    setupStrips(box.querySelectorAll(".strip"));
    if (box.querySelector("[data-marquee]")) setupMarquees();
  };
  const boxes = [...document.querySelectorAll(".lazy-sec")];
  if (!globalThis.IntersectionObserver) { boxes.forEach(show); return; }
  S.lazyIO = new IntersectionObserver(rows => rows.forEach(e => { if (e.isIntersecting) { S.lazyIO.unobserve(e.target); show(e.target); } }), { rootMargin: "900px 0px" });
  boxes.forEach(b => S.lazyIO.observe(b));
}
function setupStrips(list) {
  const strips = [...list];
  if (strips.length) requestAnimationFrame(() => setTimeout(() => {
    const on = strips.filter(s => s.isConnected), syncs = [];
    on.forEach(s => s.querySelectorAll(".st-btn,.st-dots").forEach(el => el.remove()));
    on.map(stripPlan).forEach(put => { const sync = put?.(); if (sync) syncs.push(sync); });
    if (syncs.length) requestAnimationFrame(() => syncs.forEach(f => f()));
  }));
}
function stripPlan(strip) {
    const row = strip.querySelector(".hero-row,.news-row,.ytrow,.phrow,.vrow,.fb-teams");
    if (!row) return;
    // Səhifə = görünən enə sığan kart sayı.
    if (getComputedStyle(row).flexDirection === "column") return () => { strip.dataset.pages = "1"; strip.classList.add("at-end"); }; // telefonda şaquli siyahı
    const kids = [...row.children];
    const gap = parseFloat(getComputedStyle(row).columnGap) || 0;
    const cw = kids[0] ? kids[0].getBoundingClientRect().width : 0;
    const per = Math.max(1, Math.floor((row.clientWidth + gap + 1) / ((cw || row.clientWidth) + gap)));
    const pages = Math.max(1, Math.ceil(kids.length / per));
    const step = per * (cw + gap) || row.clientWidth;
    return () => {
    strip.dataset.pages = String(pages);
    if (pages === 1) { strip.classList.add("at-end"); return; }
    const prev = document.createElement("button"), next = document.createElement("button"), dots = document.createElement("div");
    prev.type = next.type = "button";
    prev.className = "st-btn st-prev"; prev.textContent = "‹"; prev.setAttribute("aria-label", "Əvvəlki");
    next.className = "st-btn st-next"; next.textContent = "›"; next.setAttribute("aria-label", "Növbəti");
    dots.className = "st-dots";
    for (let i = 0; i < pages; i++) { const d = document.createElement("button"); d.type = "button"; d.setAttribute("aria-label", `Səhifə ${i + 1}`); d.dataset.page = String(i); dots.appendChild(d); }
    const go = i => row.scrollTo({ left: Math.max(0, Math.min(i, pages - 1)) * step, behavior: "smooth" });
    const sync = () => {
      const cur = Math.min(pages - 1, Math.round(row.scrollLeft / step));
      const end = row.scrollLeft + row.clientWidth >= row.scrollWidth - 2;
      strip.classList.toggle("at-end", end);
      prev.classList.toggle("off", row.scrollLeft <= 2); next.classList.toggle("off", end);
      [...dots.children].forEach((d, i) => d.classList.toggle("on", i === cur));
    };
    // Oxlar dövrə vurmur.
    const page = () => Math.round(row.scrollLeft / step);
    prev.onclick = () => { if (page() > 0) go(page() - 1); };
    next.onclick = () => { if (page() < pages - 1) go(page() + 1); };
    dots.onclick = e => { const b = e.target.closest("button[data-page]"); if (b) go(Number(b.dataset.page)); };
    if (row._sync) row.removeEventListener("scroll", row._sync); // yenidən qurulan zolaqda köhnə dinləyici qalmasın (ana səhifə geri qoyulanda)
    row.addEventListener("scroll", row._sync = sync, { passive: true });
    strip.append(prev, next, dots);
    return sync;
    };
}
function setupHeroImages() {
  const row = document.querySelector(".hero-strip .hero-row");
  if (!row) return;
  // Növbəti slaydların şəkli əvvəlcədən.
  const near = to => {
    const w = row.querySelector(".hero-main")?.getBoundingClientRect().width || row.clientWidth || 1;
    const at = Number.isInteger(to) ? to : Math.round(row.scrollLeft / w);
    for (const slide of [row.children[at - 1], row.children[at], row.children[at + 1], row.children[at + 2], row.children[0]]) {
      const i = slide?.querySelector("img[data-src]");
      if (i) { i.src = i.dataset.src; delete i.dataset.src; }
    }
  };
  // Slayderə toxunanda qalan şəkillər də gəlir (sahibin qeydi).
  const all = () => row.querySelectorAll("img[data-src]").forEach(i => { i.src = i.dataset.src; delete i.dataset.src; });
  if (row._near) row.removeEventListener("scroll", row._near);
  row._near = near;
  row.addEventListener("scroll", near, { passive: true });
  row.addEventListener("pointerdown", all, { once: true, passive: true });
  row.addEventListener("touchstart", all, { once: true, passive: true });
  afterFrame(near); // ölçü kadr boyanandan sonra: yamaqla eyni tapşırıqda məcburi yerləşdirmə 4× telefonda 120–391 ms idi (2026-11-09 izi)
}
let featureTimers = [];
function setupFeatureLents() {
  featureTimers.forEach(clearInterval); featureTimers = [];
  // Toxunuşdan qalan :hover slayderi dayandırmasın.
  const hoverUI = matchMedia("(hover:hover)").matches;
  const keyFocus = node => { try { return !!node.querySelector(":focus-visible"); } catch { return node.contains(document.activeElement); } };
  const paused = node => document.hidden || motionOff() || (hoverUI && node.matches(":hover")) || keyFocus(node) || Date.now() < (node._holdUntil || 0);
  const hero = document.querySelector(".hero-strip");
  if (hero) {
    const row = hero.querySelector(".hero-row"), button = hero.querySelector(".hero-pause");
      const hold = () => { hero._holdUntil = Date.now() + 12000; };
    row?.addEventListener("pointerdown", hold);
    row?.addEventListener("wheel", hold, { passive: true });
    row?.addEventListener("keydown", hold);
    const show = () => { const on = hero._paused || motionOff(); button.setAttribute("aria-pressed", String(on)); button.textContent = on ? "▶" : "Ⅱ"; button.setAttribute("aria-label", on ? "Əsas xəbər lentini davam etdir" : "Əsas xəbər lentini dayandır"); };
    button.onclick = () => { if (motionOff()) toggleMotion(); else hero._paused = !hero._paused; show(); }; // ümumi dayanıqdırsa ▶ hamısını başladır
    show();
    const slideW = () => row?.querySelector(".hero-main")?.getBoundingClientRect().width || row?.clientWidth || 0;
    const settle = () => { const w = slideW(); if (!(w > 0)) return; const target = Math.round(row.scrollLeft / w) * w; if (Math.abs(row.scrollLeft - target) > 1) row.scrollTo({ left: target }); };
    if (row && "onscrollend" in window) row.addEventListener("scrollend", settle);
    if (row && row.children.length > 1) featureTimers.push(setInterval(() => { if (hero._paused || paused(hero)) return; const w = slideW(); if (!(w > 0)) return; const next = Math.round(row.scrollLeft / w) + 1, to = next >= row.children.length ? 0 : next; row._near?.(to); row.scrollTo({ left: Math.round(to * w), behavior: "smooth" }); }, 6000));
  }
  const lent = document.querySelector("[data-prez-lent]");
  if (lent) {
    const box = lent.closest(".prez");
    const loadNear = () => {
      const edge = lent.scrollTop + lent.clientHeight + 900;
      for (const i of lent.querySelectorAll("img[data-src]")) {
        if (i.closest(".pcard").offsetTop > edge) break;
        i.src = i.dataset.src; delete i.dataset.src;
      }
    };
    lent.onscroll = loadNear; lent.addEventListener("touchstart", loadNear, { once: true, passive: true });
    const step = direction => { const rows=[...lent.children]; const current=rows.findIndex(row => row.offsetTop - rows[0].offsetTop > lent.scrollTop + 3); const next=direction > 0 ? (current < 0 ? 0 : current) : Math.max(0, rows.filter(row=>row.offsetTop-rows[0].offsetTop < lent.scrollTop-3).length-1); lent.scrollTo({top: rows[next] ? rows[next].offsetTop-rows[0].offsetTop : 0, behavior:"smooth"}); };
    const button=box.querySelector("[data-prez-pause]");
    if (button) button.onclick=()=>{lent._paused=!lent._paused;button.setAttribute("aria-pressed",String(lent._paused));button.textContent=lent._paused?"▶":"Ⅱ";button.setAttribute("aria-label",lent._paused?"Zuğulba lentini davam etdir":"Zuğulba lentini dayandır");};
    lent.onpointerdown=()=>{lent._holdUntil=Date.now()+10000;};
    if (TOUCH_UI && !lent._touch) { // eyni lentə ikinci dəst toxunuş dinləyicisi (yenidən qurğu, geri qoyulan ana səhifə) ətaləti ikiqat edərdi
      lent._touch = 1;
      let lastY = null, samples = [], inertia = 0, mode = null, expectedY = 0;
      const atEnd = () => lent.scrollTop + lent.clientHeight >= lent.scrollHeight - 1;
      const atTop = () => lent.scrollTop <= 0;
      const stopInertia = () => { if (inertia) { clearTimeout(inertia); inertia = 0; } };
      lent.addEventListener("touchstart", e => {
        stopInertia();
        lastY = e.touches[0].clientY; samples = [[performance.now(), lastY]]; mode = null; expectedY = window.scrollY;
      }, { passive: true });
      lent.addEventListener("touchmove", e => {
        if (lastY == null) return;
        const y = e.touches[0].clientY, dy = lastY - y; lastY = y;
        samples.push([performance.now(), y]); if (samples.length > 6) samples.shift();
        // overscroll-behavior:none: kənar ötürməsini JS edir;
        // səhifəni brauzer özü tərpədibsə JS dayanır (ikiqat olmasın).
        if (mode === "page") return;
        if (mode === null) mode = "lent";
        if (Math.abs(window.scrollY - expectedY) > 1) { mode = "page"; return; }
        if ((dy > 0 && atEnd()) || (dy < 0 && atTop())) { window.scrollBy(0, dy); expectedY = window.scrollY; }
      }, { passive: true });
      const release = () => {
        if (lastY == null) return;
        lastY = null;
        if (mode === "lent") {
          const now = performance.now(), recent = samples.filter(s => now - s[0] <= 120);
          if (recent.length >= 2) {
            const [t0, y0] = recent[0], [t1, y1] = recent[recent.length - 1];
            let v = (y0 - y1) / Math.max(1, t1 - t0);
            if (Math.abs(v) > 0.25 && ((v > 0 && atEnd()) || (v < 0 && atTop()))) {
              let last = now;  // setTimeout: rAF arxa planda dayanır, bu isə hər yerdə eyni işləyir
              const tick = () => { const t = performance.now(), dt = Math.min(48, t - last); last = t; window.scrollBy(0, v * dt); v *= Math.pow(0.94, dt / 16); inertia = Math.abs(v) > 0.03 ? setTimeout(tick, 16) : 0; };
              inertia = setTimeout(tick, 16);
            }
          }
        }
        samples = []; mode = null;
      };
      lent.addEventListener("touchend", release, { passive: true });
      lent.addEventListener("touchcancel", release, { passive: true });
    }
    if (!TOUCH_UI) featureTimers.push(setInterval(()=>{if(lent._paused || paused(lent) || lent.scrollHeight<=lent.clientHeight+2)return; /* statik siyahıda (toxunma ekranı) addımlama yoxdur */ if(lent.scrollTop+lent.clientHeight>=lent.scrollHeight-2)lent.scrollTo({top:0,behavior:"smooth"});else step(1);},4500));
  }
}

function setupMarquees() {
  document.querySelectorAll("[data-marquee]").forEach(el => {
    cancelMotion(el);
    el._mouse = false;
    el._key = false;
    el.style.height = "";
    el.classList.remove("vmarquee");
    for (const item of el.children) item.style.height = "";
    el.classList.toggle("static-list", matchMedia("(hover: none)").matches || matchMedia("(max-width: 900px)").matches);
    if (el.classList.contains("static-list")) { unwrapMarquee(el); return; }
    if (marqueeNarrow(el)) { unwrapMarquee(el); return; }
    const items = [...el.children];
    if (items.length < 2) { unwrapMarquee(el); return; }
    const visible = marqueeVisible(el);
    if (marqueeUniform(el)) {
      for (const item of items) item.style.height = "";
      let maxH = 0;
      for (const item of items) maxH = Math.max(maxH, item.getBoundingClientRect().height);
      const rowH = Math.ceil(maxH);
      if (rowH > 0) for (const item of items) item.style.height = rowH + "px";
    } else if (el.classList.contains("hero-side") && !matchMedia("(max-width: 900px)").matches) {
      const gap = 8;
      const cardH = (el.clientHeight - gap * (visible - 1)) / visible;
      if (cardH > 48) for (const item of items) item.style.height = cardH + "px";
    } else {
      for (const item of items) item.style.height = "";
    }
    if (marqueeLocks(el) && items.length > visible) {
      const h = spanHeight(items, visible);
      if (h > 0) el.style.height = Math.round(h) + "px";
    }
    const overflows = el.scrollHeight > el.clientHeight + 2;
    if (!overflows) { unwrapMarquee(el); return; }
    el.classList.add("vmarquee");
    const kept = el.scrollTop;
    const aligned = rowStops(el);
    let best = aligned[0], bestD = Infinity;
    for (const p of aligned) { const d = Math.abs(kept - p); if (d < bestD) { best = p; bestD = d; } }
    el.scrollTop = best;
    ensureWrap(el); // hero üçün mövqe konteyneri; ⌃⌄ ox düymələri çıxarılıb — siyahı özü addımlayır, təkər və barmaqla sürüşür
    scheduleStep(el, STEP_MS);
  });
}
document.addEventListener("mouseover", (e) => {
  const el = marqueeOf(e.target);
  if (!el || marqueeOf(e.relatedTarget) === el) return;
  el._mouse = true;
  stopStep(el, true);
});
document.addEventListener("mouseout", (e) => {
  const el = marqueeOf(e.target);
  if (!el || marqueeOf(e.relatedTarget) === el) return;
  el._mouse = false;
  scheduleStep(el, LEAVE_MS);
});
document.addEventListener("focusin", (e) => {
  const el = marqueeOf(e.target);
  if (!el) return;
  el._key = true;
  stopStep(el, true);
});
document.addEventListener("focusout", (e) => {
  const el = marqueeOf(e.target);
  if (!el) return;
  setTimeout(() => {
    const wrap = el.closest(".step-wrap");
    if (el.contains(document.activeElement) || wrap?.contains(document.activeElement)) return;
    el._key = false;
    scheduleStep(el, LEAVE_MS);
  }, 0);
});
const preconnected = new Set();
document.addEventListener("pointerdown", (e) => {
  const a = e.target.closest?.("a[href^=http]");
  if (!a) return;
  try {
    const o = new URL(a.href).origin;
    if (o === location.origin || preconnected.has(o)) return;
    preconnected.add(o);
    const l = document.createElement("link"); l.rel = "preconnect"; l.href = o; l.crossOrigin = ""; document.head.appendChild(l);
  } catch {}
}, { capture: true, passive: true });
document.addEventListener("pointerdown", (e) => {
  if (e.pointerType !== "touch") return;
  const el = marqueeOf(e.target);
  if (!el) return;
  stopStep(el, false);
  el._holdUntil = Date.now() + TOUCH_MS;
  scheduleStep(el, TOUCH_MS);
}, true);
// Təkər: siyahı dibə çatıbsa səhifəni sürüşdürür.
// Brauzerin öz keçidi (scroll chaining) etibarsızdır.
document.addEventListener("wheel", (e) => {
  const el = marqueeOf(e.target);
  if (!el) return;
  stopStep(el, false);
  el._holdUntil = Date.now() + WHEEL_MS;
  scheduleStep(el, WHEEL_MS);
  if (!el.classList.contains("vmarquee") || !e.deltaY || e.ctrlKey) return;
  const dy = e.deltaMode === 1 ? e.deltaY * 16 : e.deltaMode === 2 ? e.deltaY * innerHeight : e.deltaY;
  const max = el.scrollHeight - el.clientHeight;
  const atEnd = dy > 0 ? el.scrollTop >= max - 1 : el.scrollTop <= 1;
  if (!atEnd) return;
  e.preventDefault();
  window.scrollBy({ top: dy, left: 0, behavior: "auto" });
}, { passive: false, capture: true });
document.addEventListener("visibilitychange", () => {
  document.querySelectorAll("[data-marquee].vmarquee").forEach(el => {
    cancelMotion(el);
    if (!document.hidden) scheduleStep(el, LEAVE_MS);
  });
});
let marqueeResizeT = 0;
addEventListener("resize", () => {
  clearTimeout(marqueeResizeT);
  marqueeResizeT = setTimeout(() => { setupMarquees(); setupStrips(document.querySelectorAll(".strip")); setupFeatureLents(); fitNav(); }, 150);
});

// Alt yazı məzmunla birgə gəlir.
function render() { clearTimeout(S.renderTimer); S.renderQueued = false; renderTopbar(); renderNav(); renderTicker(); renderLangs(); renderView(); if (S.data || S.sharedStory || S.error) renderFooter(); syncTixDot(); }

/* ---- start */
async function loadAds() {
  try {
    const r = await fetch(freshUrl("data/ads.json"), { cache: "no-store" });
    if (r.ok) S.ads = await r.json();
  } catch {}
  const el = document.querySelector("main .ad");
  if (el && route().name === "home") el.outerHTML = adHtml();
}
async function loadVideo() {
  try {
    const r = await fetch(freshUrl("data/video.json"), { cache: "no-store" });
    if (r.ok) { S.video = await r.json(); if (uiLang(S.lang) && S.video.items) S.video.items = S.video.items.filter(v => langOf({ title: v.title, summary: "" }) === S.lang); if (route().name === "home" || route().name === "videos") requestRender(false); }
  } catch {}
}
const SPORTS_DELAY_MS = 4000;
function wantSports() { if (S.sports || S.sportsAsked) return; S.sportsAsked = true; loadSports(); requestJSON(freshUrl("data/milli-menyu.json")).then(r => { S.milli = r.d?.comps; S.navRefresh?.(); }, () => {}); }
async function loadSports() {
  try {
    const r = await fetch(freshUrl("data/sports.json"), { cache: "no-store" });
    if (r.ok) { const d = await r.json(); if (Array.isArray(d.leagues)) { S.sports = d; S.navRefresh?.(); if (["home", "league", "section"].includes(route().name) && S.data) requestRender(false); } }
  } catch {}
}
async function loadFootball() {
  try {
    const r = await fetch(freshUrl("data/football.json"), { cache: "no-store" });
    if (r.ok) { S.football = await r.json(); if (["home", "league"].includes(route().name)) requestRender(false); }
  } catch {}
}
async function loadPrayer(city) {
  const name = CITIES.some(c => c[0] === city) ? city : savedPrayCity();
  const c = CITIES.find(x => x[0] === name) || CITIES[0];
  const token = (S.prayToken = (S.prayToken || 0) + 1);
  try {
    // Tarixli ünvan: tarixsiz /timings 302 ilə bura yönlənirdi; gedişdə açıq qalan yönləndirmə Chrome-un geri-irəli keşini (bfcache) bağlayır (NetworkRequestRedirected). Gün Bakı vaxtı ilə.
    const bd = new Date(Date.now() + 144e5), day = `${String(bd.getUTCDate()).padStart(2, "0")}-${String(bd.getUTCMonth() + 1).padStart(2, "0")}-${bd.getUTCFullYear()}`;
    const u = `https://api.aladhan.com/v1/timings/${day}?latitude=${c[1]}&longitude=${c[2]}&method=13`;
    const d = await (await fetch(u)).json();
    if (token !== S.prayToken || !d?.data?.timings) return;
    S.pray = { city: c[0], timings: d.data.timings, hijri: d.data.date?.hijri };
    try { storage.setItem(PRAY_KEY, JSON.stringify({ ...S.pray, day: bakuDay() })); } catch {}
    renderTopbar();
  } catch {}
}
async function loadWarnings() {
  const c = geoCity();
  try {
    const u = `https://api.open-meteo.com/v1/forecast?latitude=${c[1]}&longitude=${c[2]}&daily=weather_code,precipitation_sum,wind_speed_10m_max&timezone=Asia%2FBaku&forecast_days=1`;
    const d = await (await fetch(u)).json();
    const code = d?.daily?.weather_code?.[0];
    const wind = d?.daily?.wind_speed_10m_max?.[0];
    const rain = d?.daily?.precipitation_sum?.[0];
    const bits = [];
    if (code >= 95) bits.push("İldırım ehtimalı");
    else if ([65, 66, 67, 82].includes(code)) bits.push("Güclü yağış");
    else if ([71, 73, 75, 77, 85, 86].includes(code)) bits.push("Qar");
    if (wind >= 50) bits.push(`Külək ${Math.round(wind)} km/s`);
    if (rain >= 20) bits.push(`Yağıntı ${Math.round(rain)} mm`);
    S.warn = bits;
    if (route().name === "home") requestRender(false);
  } catch {}
}
// Sosial yazılar (sahib 2026-11-08: «1 dəq öncə Mehriban Əliyeva Youtubda paylaşımı bizdə yoxdur»): status.social varsa social.json
// dəqiqəlik kanaldadır (pipeline.sh social_loop). Möhür dəyişəndə çəkilir (loadStatus), dəyişməyəndə sorğu yoxdur; alınmasa sayt kanalı.
async function loadSocial() {
  const rev = S.status?.social;
  S.socialRev = null;
  try {
    const r = (rev && await liveDirect("data/social.json", undefined, 1)) || await fetch(freshUrl("data/social.json"), { cache: "no-store" });
    if (r.ok) { S.social = await r.json(); S.socialRev = rev || null; requestRender(); }
    // Köhnə yazı social.json-da yoxdursa arxivdən.
    const s = location.hash.match(/[?&]s=([0-9a-f]{16})/)?.[1], p = s && !S.social.posts.some(p => p.id === s) && (await requestJSON(freshUrl("data/social-arxiv.json"))).d?.posts?.find(p => p.id === s);
    if (p) { S.social.posts.push(p); requestRender(); }
  } catch {}
}
async function loadSources() {
  try {
    const r = await fetch(freshUrl("data/sources.json"), { cache: "no-store" });
    if (r.ok) S.sources = await r.json();
  } catch {}
  if (route().name === "sources") renderView();
  renderFooter();
}
async function loadStatus(force = false) {
  S.statusAbort?.abort();
  const controller = S.statusAbort = new AbortController();
  try {
    const {d} = await requestJSON(freshUrl("data/status.json", force), {signal:controller.signal}, 8000);
    if(!controller.signal.aborted && S.statusAbort === controller && d && typeof d === "object"){S.status = d; if (d.social && S.socialRev !== undefined && d.social !== S.socialRev) loadSocial();}
  } catch {}
  if(S.statusAbort === controller){S.statusAbort = null; renderTopbar();}
}
// Dəqiqəlik yoxlama status.json ilə.
async function pollNews(force = false, resume = false) {
  if (!force && document.hidden) return; // arxa planda məlumat xərcləmirik; qayıdanda resumeNews dərhal yoxlayır
  await loadStatus(force);
  const now = S.status?.checkedAt || null;
  if (force || !S.data || S.error || !now || Date.now() - (S.newsCheckedAt || 0) >= NEWS_FULL_MS) {
    await loadNews(force);
    await loadLatest(force);
  } else if (resume || now !== S.newsStamp || Date.now() - (S.latestAt || 0) >= LATEST_MAX_MS) {
    await loadLatest();
  }
}
const RELOAD_AFTER_HIDDEN_MS = 60 * 60e3;
// Yeni versiya (reloadWhenHidden): vərəq gözdən itən kimi yox, 5 dəqiqə gizli qalandan sonra yenidən açılır (2026-11-09). Mənbəyə keçid
// vərəqi gizlədir: dərhal yenidən açılış oxucunu qayıdanda yüklənən səhifəyə və itirilmiş yerə gətirirdi (yayım günündə hər dönüşdə).
const RELOAD_HIDDEN_WAIT_MS = 5 * 60e3;
function resumeNews() {
  if(document.hidden){
    S.hiddenAt ||= Date.now();
    if(S.reloadWhenHidden){ clearTimeout(S.reloadTimer); S.reloadTimer = setTimeout(() => { if(document.hidden && !globalThis.speechSynthesis?.speaking)location.reload(); }, RELOAD_HIDDEN_WAIT_MS); } // yeni versiya oxucu baxmayanda
    return;
  }
  clearTimeout(S.reloadTimer);
  const away = S.hiddenAt ? Date.now() - S.hiddenAt : 0;
  S.hiddenAt = 0;
  if(away >= RELOAD_AFTER_HIDDEN_MS && !globalThis.speechSynthesis?.speaking){ location.reload(); return; }
  if(Date.now() - (S.lastResumeAt || 0) < 2500)return;
  S.lastResumeAt = Date.now();
  if(S.swReg && Date.now() - (S.swCheckedAt || 0) >= 30 * 60e3){ S.swCheckedAt = Date.now(); S.swReg.update().catch(() => {}); }
  // Tam lent yalnız 10 dəqiqədən köhnədirsə gəlir.
  pollNews(false, true);
}
// İşçinin (sw.js) mesajları açılışdan dinlənir (2026-11-09). Əvvəl dinləyici registerWorker içində idi və o tam lentdən sonra çağırılırdı
// (telefonda ~10 s): brauzer «shell-updated»i növbədə saxlayıb gec verirdi, kompüterdə çəkilmiş səhifə 3-cü saniyədə yenidən açılırdı
// (məzmun → boş → məzmun, sayğacda iki ziyarət). İndi: ekranda hələ lent yoxdursa dərhal yenidən açılır (itirilən heç nə yoxdur),
// lent varsa yeni kod səhifə gözdən itəndə gəlir — VERSION yolu (activated) ilə eyni qayda.
function onWorkerMessage(e) {
  if (e.data?.type === "open-story" && e.data.id) { location.hash = detailUrl({ id: e.data.id }); return; } // bildiriş kliki
  if (e.data?.type !== "shell-updated") return;
  let once = false;
  try { once = !sessionStorage.getItem("8ulduz-reloaded"); if (once) sessionStorage.setItem("8ulduz-reloaded", "1"); } catch {}
  if (once && performance.now() < 4000 && !S.rawNews && (globalThis.scrollY || 0) < 50 && !document.activeElement?.matches?.("input,textarea")) location.reload();
  else S.reloadWhenHidden = true;
}
function listenWorker() {
  const sw = navigator.serviceWorker;
  if (!sw) return;
  sw.addEventListener("message", onWorkerMessage);
  sw.startMessages?.(); // dinləyicidən əvvəl gələn mesajlar növbədədir: indi verilsin
}
applyPrefs();
addEventListener("beforeinstallprompt", e => { e.preventDefault(); S.installEvt = e; renderLangs(); });
addEventListener("appinstalled", () => { S.installEvt = null; trackEvent("install-done"); renderLangs(); });
function registerWorker() {
  if (!("serviceWorker" in navigator)) return;
  // sw.js kod dəyişəndə yenidən açılır (mesajlar: onWorkerMessage, açılışdan dinlənir).
  navigator.serviceWorker.register("./sw.js", {updateViaCache:"none"}).then((reg) => {
    S.swReg = reg;
    if (!navigator.serviceWorker.controller) return;
    reg.addEventListener("updatefound", () => {
      const nw = reg.installing;
      if (!nw) return;
      nw.addEventListener("statechange", () => {
        // Oxucunun qarşısında səhifə birdən yenilənməsin.
        if (nw.state === "activated") { S.reloadWhenHidden = true; if (document.hidden) resumeNews(); } // gizli olsa da dərhal yox: 5 dəqiqəlik gözləmə (resumeNews)
      });
    });
  }).catch(() => {});
}
// «Məzmuna keç»: ünvan dəyişməsin, yoxsa marşrut onu «tapılmadı» sayır.
document.addEventListener("click", (e) => {
  if (!e.target.closest?.(".skip")) return;
  e.preventDefault();
  $("#view")?.focus();
});
document.addEventListener("toggle", (e) => {
  const d = e.target;
  if (d.classList?.contains("service-panel")) S.svcOpen = d.open; // nəticə/cədvəl düyməsi paneli bağlamasın
  if (!d.classList?.contains("altpop") || !d.open) return;
  const t = d.querySelector("template"); if (t) t.replaceWith(t.content);
  document.querySelectorAll("details.altpop[open]").forEach(x => { if (x !== d) x.open = false; });
}, true);
if (uiLang(S.lang)) {
  const page = document.documentElement.style, show = () => { page.visibility = ""; };
  page.visibility = "hidden";
  setTimeout(show, 1500);
  import("./dil.js").then(m => m.startDil(S, S.lang)).catch(() => {}).finally(show);
}
listenWorker();
restoreLocal();
shell(); render();
// Hamısı gələn kimi çəkilir.
// xeber/<id>/ səhifəsi xəbərin sətrini gətirir (#row).
{ const r0 = route(); try { const w = JSON.parse(document.getElementById("row")?.textContent || sessionStorage.getItem("x:" + r0.id) || 0); if (w?.id === r0.id && !policyViolation(w)) S.sharedStory = { id: w.id, row: w }; } catch {} if (r0.name === "article") { if (S.sharedStory) setTimeout(renderView); else loadShared(r0.id); backHome(); } }
// Bayram (bayram.js): yalnız günündə.
{ const d = new Date(Date.now() + 144e5).toISOString().slice(5, 10); if (/^11-0[89]$/.test(d) || /[?&]bayram\b/.test(location.search)) setTimeout(() => import(`${ASSET}bayram.js`).then(m => m.show(d === "11-08" ? d : "11-09")).catch(() => {}), 800); }
loadCached();
const firstReady = S.firstReady = loadFirst();
const newsReady = loadNews().then(() => loadLatest());
const afterNews = run => newsReady.finally(() => setTimeout(run));
afterNews(enableAnalytics);
// İşçi (sw.js) ilk ekran çəkiləndən sonra ilk boş anda qurulur (2026-11-09). Əvvəl tam lentdən sonra idi (telefonda 10–12 s):
// paylaşılan xəbəri oxuyub çıxan oxucuda heç qurulmurdu, hər açılışı soyuq qalırdı; bu ziyarətin lenti də köhnə keşə yazılırdı.
// İlkin keş kiçikdir (yalnız ilk açılış faylları), lentlə yarışmır.
firstReady.then(() => (globalThis.requestIdleCallback || (f => setTimeout(f, 1000)))(registerWorker, { timeout: 4000 }));
newsReady.then(flushRender);
const socNow = /[?&]s=[0-9a-f]{16}/.test(location.hash) && loadSocial();
afterNews(() => { socNow || loadSocial(); loadSources(); loadVideo(); loadFootball(); loadAds(); loadLocal(); });
afterNews(() => setTimeout(wantSports, SPORTS_DELAY_MS));
afterNews(() => idle(() => loadOg(), 1500, 8000)); // og xəritəsi lentdən sonra, boş anda (H1, 2026-11-09)
document.addEventListener("toggle", e => { if (e.target.matches?.(".service-panel")) wantSports(); }, true);
loadMarkets(); loadStatus();
setInterval(() => pollNews(), POLL_MS);
addEventListener("scroll", () => {
  if (S.renderPending && (globalThis.scrollY || 0) < 200) requestRender();
}, {passive: true});
for (const ev of ["pointerdown", "wheel", "touchmove", "keydown"]) addEventListener(ev, () => { S.touchAt = Date.now(); }, { passive: true, capture: true });
// Arxa plandan qayıdanda dərhal yoxla.
// Əks halda saatlarla köhnə lent görünürdü — «sayt yenilənmir» təəssüratı.
document.addEventListener("visibilitychange", resumeNews);
addEventListener("storage", e => { if (e.key === SAVE_KEY && route().name === "saved") requestRender(false); });
addEventListener("pageshow", e => { if (e.persisted) resumeNews(); });
addEventListener("focus", resumeNews);
addEventListener("online", resumeNews);
setInterval(() => S.status?.social || loadSocial(), 5 * 60e3);
setInterval(loadMarkets, 5 * 60e3);
setInterval(() => { loadSources(); loadVideo(); loadFootball(); }, 5 * 60e3);
setInterval(loadSports, 30 * 60e3);
setInterval(() => { if (adSlots().length > 1 && route().name === "home") { const el = document.querySelector("main .ad"); if (el) el.outerHTML = adHtml(); } }, 30e3);
document.addEventListener("change", (e) => {
  const sel = e.target.closest?.("select.pray-city");
  if (!sel) return;
  const city = sel.value;
  if (!CITIES.some(c => c[0] === city)) return;
  try { storage.setItem(PRAY_CITY_KEY, city); } catch {}
  S.prayOpen = true;
  sel.blur();
  loadPrayer(city);
});
document.addEventListener("keydown", (e) => {
  if (e.key !== "Enter" && e.key !== " ") return;
  const star = e.target.closest?.("[data-act=star]") || e.target.matches?.("div[data-yt]") && e.target;
  if (!star) return;
  e.preventDefault();
  e.stopPropagation();
  star.click();
});
setInterval(loadWeather, 30 * 60e3);
setInterval(() => { if (S.data) renderTopbar(); }, 30e3);
let rushWas = bakuRush();
setInterval(() => {
  syncTixDot();
  const rush = bakuRush();
  if (rush === rushWas) return;
  rushWas = rush;
  const n = route().name;
  if ((n === "home" || n === "traffic") && S.data) renderView();
}, 60e3);

if (ASSISTANT_ON) afterNews(() => import("./assistant.js").then(({ mountAssistant }) => mountAssistant({
  getSnapshot: () => ({ articles: S.data?.articles || [], newsAt: S.data?.updatedAt, categories: CATS, cities: CITIES, road: localRoadItems(S.data?.articles || []), sportsAt: S.sports?.updatedAt, leagues: fbLeagues().map(l => ({...l, updatedAt: l.world ? S.sports?.updatedAt : S.football?.updatedAt})) }),
  wxCode,
})).catch(() => {}));
afterNews(() => import('./source-stats.js').then(({mountSourceStats}) => mountSourceStats({code:window.SITE_CONFIG?.goatcounter, getArticles:()=>[...(S.data?.articles || []),...savedList()]})).catch(()=>{}));
if (DRIVER_ON) afterNews(() => import('./reader.js').then(({mountReader}) => mountReader({
  getArticles:()=>[...(S.data?.articles || []),...savedList()],
  driverEnabled:()=>storage.getItem('8ulduz-driver')==='on',
  setDriver:on=>{storage.setItem('8ulduz-driver',on?'on':'off');renderLangs();},
})).catch(()=>{}));
