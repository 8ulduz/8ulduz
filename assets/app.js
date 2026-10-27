// 8ulduz — sayt kodu (build tələb olunmur; birbaşa GitHub Pages-də işləyir).
// Məlumat: data/news.json (xəbərlər), data/markets.json (valyuta/neft/qızıl) — hər ikisini updater.py yaradır.

/* ---------------------------------------------------------------- sabitlər */
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
  { slug: "heyat", label: "Həyat", description: "Sağlamlıq və həyat tərzi" },
  { slug: "video", label: "Video", description: "Saytlardakı video xəbərlərə keçidlər" },
];
const LANGS = [
  { code: "az", label: "Azərbaycan dilində" }, { code: "ru", label: "на русском языке" },
  { code: "en", label: "in English" }, { code: "tr", label: "Türkçe" },
];
const LANG_BADGE = { az: "AZ", ru: "RUS", en: "ENG", tr: "TÜRK" };
const PREZ_LINKS = [
  { name: "president.az", url: "https://president.az/az" },
  { name: "mehriban-aliyeva.az", url: "https://mehriban-aliyeva.az/" },
  { name: "X — @presidentaz", url: "https://x.com/presidentaz" },
];
// Rəsmi hesablar (president.az və mehriban-aliyeva.az səhifələrindəki keçidlər). Telegram kanalı yoxdur.
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
const CLUBS = [
  ["Qarabağ", ["qarabağ", "qarabag"]], ["Sabah", ["sabah fk", "sabah"]], ["Neftçi", ["neftçi", "neftci"]],
  ["Turan", ["turan"]], ["Zirə", ["zirə", "zire"]], ["Sumqayıt", ["sumqayıt fk", "sumqayıt"]], ["Araz", ["araz"]],
  ["Şamaxı", ["şamaxı fk", "şamaxı"]], ["Galatasaray", ["galatasaray"]], ["Fenerbahçe", ["fenerbahçe", "fenerbahce"]],
  ["Beşiktaş", ["beşiktaş", "besiktas"]], ["Trabzonspor", ["trabzonspor"]], ["Başakşehir", ["başakşehir", "basaksehir"]],
  ["Samsunspor", ["samsunspor"]], ["Man City", ["manchester city", "man city"]], ["Man United", ["manchester united", "man united"]],
  ["Liverpool", ["liverpool"]], ["Arsenal", ["arsenal"]], ["Chelsea", ["chelsea", "çelsi"]], ["Tottenham", ["tottenham"]],
  ["Newcastle", ["newcastle"]], ["Aston Villa", ["aston villa"]], ["Real Madrid", ["real madrid"]],
  ["Barcelona", ["barcelona", "barselona"]], ["Atletico", ["atletico", "atletiko"]], ["Sevilla", ["sevilla"]],
  ["Villarreal", ["villarreal"]], ["Valencia", ["valencia"]], ["Bayern", ["bayern", "bavariya"]], ["Dortmund", ["dortmund"]],
  ["Leverkusen", ["leverkusen"]], ["Leipzig", ["leipzig"]], ["Frankfurt", ["frankfurt"]], ["Juventus", ["juventus", "yuventus"]],
  ["Milan", ["milan"]], ["İnter", ["inter"]], ["Napoli", ["napoli"]], ["Roma", ["roma"]], ["Lazio", ["lazio"]],
  ["Atalanta", ["atalanta"]], ["PSG", ["psg", "paris saint"]], ["Marseille", ["marseille", "marsel"]], ["Lyon", ["lyon"]],
  ["Monaco", ["monaco"]], ["Lille", ["lille"]], ["Ajax", ["ajax"]], ["Porto", ["porto"]], ["Benfica", ["benfica"]],
  ["Sporting", ["sporting"]], ["Celtic", ["celtic"]],
];
const CITIES = [["Bakı",40.4093,49.8671],["Sumqayıt",40.5897,49.6686],["Gəncə",40.6828,46.3606],["Mingəçevir",40.77,47.0286],["Şirvan",39.937,48.929],["Naxçıvan",39.2089,45.4122],["Lənkəran",38.7529,48.85],["Şəki",41.1919,47.1706],["Quba",41.3611,48.5133],["Xaçmaz",41.459,48.802],["Şamaxı",40.631,48.641],["İsmayıllı",40.785,48.15],["Qəbələ",40.98,47.86],["Oğuz",41.071,47.465],["Zaqatala",41.63,46.64],["Balakən",41.726,46.404],["Qax",41.418,46.92],["Şuşa",39.758,46.75],["Ağdam",39.993,46.93],["Füzuli",39.604,47.15],["Cəbrayıl",39.399,47.03],["Kəlbəcər",40.106,46.045],["Laçın",39.638,46.546],["Zəngilan",39.088,46.65],["Qubadlı",39.344,46.58],["Tovuz",40.992,45.628],["Göygöl",40.585,46.306],["Yevlax",40.617,47.15],["Bərdə",40.375,47.126],["Ağsu",40.57,48.4],["Kürdəmir",40.335,48.16],["Ucar",40.52,47.65],["Göyçay",40.65,47.74],["Ağdaş",40.65,47.48],["Zərdab",40.22,47.71],["İmişli",39.87,48.06],["Saatlı",39.93,48.37],["Sabirabad",40.01,48.48],["Salyan",39.596,49],["Neftçala",39.376,49.247],["Hacıqabul",40.04,48.94],["Biləsuvar",39.46,48.55],["Masallı",39.034,48.665],["Astara",38.501,48.875],["Lerik",38.775,48.415],["Yardımlı",38.908,48.24]];
const DAYS = ["bazar", "bazar ertəsi", "çərşənbə axşamı", "çərşənbə", "cümə axşamı", "cümə", "şənbə"];
const MONTHS = ["yanvar", "fevral", "mart", "aprel", "may", "iyun", "iyul", "avqust", "sentyabr", "oktyabr", "noyabr", "dekabr"];
const HOUR = 3600e3, DAY = 24 * HOUR;
const POLL_MS = 60e3;     // xəbər lentini yoxlama intervalı
// GitHub Pages JSON-u ~600 san cache edir; hər dəqiqə yeni sorğu açarı təzə faylı gətirir
const freshUrl = (path) => `${path}?t=${Math.floor(Date.now() / 60000)}`;
const PAGE = 48;          // bölmə səhifəsində bir dəfəyə göstərilən xəbər

// Məxfi rejimdə və yaddaş dolanda seçimlər heç olmasa açıq vərəqdə işləsin.
const sessionPrefs = new Map();
const storage = {
  getItem(key) {
    if (sessionPrefs.has(key)) return sessionPrefs.get(key);
    try { return localStorage.getItem(key); } catch { return null; }
  },
  setItem(key, value) {
    sessionPrefs.set(key, String(value));
    try { localStorage.setItem(key, value); } catch {}
  },
  removeItem(key) {
    sessionPrefs.set(key, null);
    try { localStorage.removeItem(key); } catch {}
  },
};

/* ---------------------------------------------------------------- köməkçilər */
const $ = (s, r = document) => r.querySelector(s);
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
function tidy(s) {
  return decode(s).replace(/\u00a0/g, " ").replace(/\s+/g, " ").replace(/(?:\s*[-–—|])+\s*$/u, "").trim();
}
const txt = s => esc(tidy(s));
const catLabel = slug => CATS.find(c => c.slug === slug)?.label ?? slug;
function ago(iso) {
  const t = new Date(iso).getTime(); if (Number.isNaN(t)) return "";
  const m = Math.floor(Math.max(0, Date.now() - t) / 6e4);
  if (m < 1) return "indicə"; if (m < 60) return `${m} dəqiqə əvvəl`;
  const h = Math.floor(m / 60); if (h < 24) return `${h} saat əvvəl`;
  const d = Math.floor(h / 24); return d < 30 ? `${d} gün əvvəl` : fullDate(iso);
}
function fullDate(iso) { const d = new Date(iso); return Number.isNaN(d.getTime()) ? "" : `${d.getDate()} ${MONTHS[d.getMonth()]} ${d.getFullYear()}`; }
function today() { const a = new Date(), r = `${DAYS[a.getDay()]}, ${a.getDate()} ${MONTHS[a.getMonth()]} ${a.getFullYear()}`; return r.charAt(0).toLocaleUpperCase("az") + r.slice(1); }
const isFresh = a => { const age = Date.now() - new Date(a.publishedAt).getTime(); return age >= 0 && age < HOUR; };
const OUT = `target="_blank" rel="noopener noreferrer"`;
function langOf(a) { if (a.lang) return a.lang; const s = a.title + " " + a.summary; return /[а-яА-Я]/.test(s) ? "ru" : /[əƏ]/.test(s) ? "az" : /[ığİ]/.test(s) ? "tr" : "az"; }
const flText = s => {
  s = lc(s);
  return s.includes("mehriban") || s.includes("məhriban") || s.includes("мехрибан")
    || s.includes("birinci xanım") || s.includes("birinci xanim") || s.includes("first lady")
    || s.includes("first vice-president") || s.includes("first vice president")
    || s.includes("birinci vitse-prezident") || s.includes("первой леди") || s.includes("первая леди");
};
// Nişan başlığa görədir (rəsmi səhifənin ortaq tədbirləri ayrıca «Birinci xanım» nişanı almır).
const isFirstLady = a => !!a && flText(a.title);
// Birinci xanım: rəsmi səhifəsi və ya başlıq. Prezident qrupu bundan kənarda qalanlardır.
const isFlItem = a => !!a && (a.source === "Mehriban Əliyeva" || flText(a.title));
// Əsas blok: əvvəl Prezident (ən yeni), sonra Birinci xanım (ən yeni). Hər iki qrup görünsün.
function prezHome(list) {
  const now = Date.now();
  const age = a => now - new Date(a.publishedAt).getTime();
  const prez = list.filter(a => a.category === "prezident");
  const president = byDate(prez.filter(a => !isFlItem(a) && age(a) < 21 * DAY));
  const lady = byDate(prez.filter(a => isFlItem(a) && age(a) < 60 * DAY));
  const MAX = 12;
  const head = 4;
  const ladyKeep = lady.length ? Math.min(lady.length, 2) : 0;
  const presHead = Math.min(president.length, head - ladyKeep);
  const ladyHead = Math.min(lady.length, head - presHead);
  const first = [...president.slice(0, presHead), ...lady.slice(0, ladyHead)];
  const rest = [...president.slice(presHead), ...lady.slice(ladyHead)];
  return [...first, ...rest].slice(0, MAX);
}
const byDate = list => [...list].sort((x, y) => new Date(y.publishedAt).getTime() - new Date(x.publishedAt).getTime());
const lc = s => (s || "").toLocaleLowerCase("az");
const GROUP_MS = 36 * HOUR;
const GROUP_STOP = new Set("ve ile the and for from or bir bu da de ki veya icin olan və ilə də o üçün ya news xəbər xeber".split(/\s+/));
function normTitle(s) {
  return (s || "").toLowerCase().replace(/i̇/g, "i")
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
  if (!!a.imageUrl !== !!b.imageUrl) return a.imageUrl ? a : b;
  if ((a.summary || "").length !== (b.summary || "").length) return (a.summary || "").length > (b.summary || "").length ? a : b;
  return (a.publishedAt || "") >= (b.publishedAt || "") ? a : b;
}
// updater.py qruplamayıbsa, eyni qayda ilə brauzerdə birləşdir (news.json yığcam qalır, alts gələndə ona etibar edir)
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
    const alts = members.filter(m => m.a !== primary).map(m => ({ source: m.a.source, sourceUrl: m.a.sourceUrl, publishedAt: m.a.publishedAt }));
    if (alts.length) primary.alts = alts.sort((x, y) => (y.publishedAt || "").localeCompare(x.publishedAt || ""));
    out.push(primary);
  }
  return out.sort((x, y) => (y.publishedAt || "").localeCompare(x.publishedAt || ""));
}
// Eyni başlıq (eyni mənbə adı da olsa) 36 saat içində bir kart olsun.
function collapseExact(list) {
  const groups = [];
  for (const a of list || []) {
    const key = normTitle(decode(a.title));
    const dt = new Date(a.publishedAt).getTime();
    let g = null;
    if (key.length >= 12 && !Number.isNaN(dt)) g = groups.find(x => x.key === key && Math.abs(x.dt - dt) <= GROUP_MS);
    if (!g) groups.push({ key, dt: Number.isNaN(dt) ? 0 : dt, items: [a] });
    else g.items.push(a);
  }
  const out = [];
  for (const g of groups) {
    let primary = g.items[0];
    for (const a of g.items.slice(1)) primary = preferPrimary(primary, a);
    const alts = [];
    const urls = new Set([primary.sourceUrl]);
    const push = (src, url, publishedAt) => {
      if (!url || urls.has(url)) return;
      urls.add(url);
      alts.push({ source: src, sourceUrl: url, publishedAt });
    };
    for (const a of g.items) {
      if (a !== primary) push(a.source, a.sourceUrl, a.publishedAt);
      for (const alt of a.alts || []) push(alt.source, alt.sourceUrl, alt.publishedAt);
    }
    if (alts.length) primary.alts = alts.sort((x, y) => (y.publishedAt || "").localeCompare(x.publishedAt || ""));
    out.push(primary);
  }
  return out.sort((x, y) => (y.publishedAt || "").localeCompare(x.publishedAt || ""));
}
const altBadge = a => a.alts?.length ? `<span class="bd gold">+${a.alts.length} mənbə</span>` : "";
function altPop(a) {
  if (!a.alts?.length) return "";
  const rows = a.alts.map(r => `<a href="${esc(r.sourceUrl)}" ${OUT}>${esc(r.source)}</a>`).join("");
  return `<details class="altpop"><summary class="bd gold">+${a.alts.length} mənbə</summary><div>${rows}</div></details>`;
}
const STAR = `<svg viewBox="0 0 32 32" width="18" height="18" aria-hidden="true"><g fill="currentColor"><rect x="9.5" y="9.5" width="13" height="13" rx="2"/><rect x="9.5" y="9.5" width="13" height="13" rx="2" transform="rotate(45 16 16)"/></g></svg>`;

function imgUrl(a) {
  const u = a?.imageUrl || "";
  if (!u || /\/(?:resize\/?)?$/.test(u)) return "";
  return u;
}
function img(a, cls = "", eager = false) {
  const ph = `<svg class="ph" viewBox="0 0 32 32" aria-hidden="true"><g fill="currentColor"><rect x="9.5" y="9.5" width="13" height="13" rx="2"/><rect x="9.5" y="9.5" width="13" height="13" rx="2" transform="rotate(45 16 16)"/></g></svg>`;
  const url = imgUrl(a);
  const src = url ? `<img src="${esc(url)}" alt="" ${eager ? `fetchpriority="high"` : `loading="lazy"`} decoding="async" referrerpolicy="no-referrer" onerror="imgFail(this)">` : "";
  return `<div class="img ${cls}">${ph}${src}</div>`;
}
function badges(a, withCat = true, alt = "span") {
  const more = !a.alts?.length ? "" : alt === "pop" ? altPop(a) : altBadge(a);
  return `<div class="badges">${withCat ? `<span class="bd" data-cat="${esc(a.category)}"><i class="cdot"></i>${esc(catLabel(a.category))}</span>` : ""}${more}${a.video ? `<span class="bd red">▶ Video</span>` : ""}${a.lang ? `<span class="bd out">${esc(LANG_BADGE[a.lang] ?? a.lang.toUpperCase())}</span>` : ""}${isFresh(a) ? `<span class="bd red">Son dəqiqə</span>` : ""}</div>`;
}
function shownSource(a) {
  try {
    const host = new URL(a.sourceUrl || "").hostname.replace(/^www\./, "");
    if (host === "sesqazeti.az") return "Sesqazeti.az";
  } catch {}
  return a.source || "";
}
const meta = a => `<div class="meta"><span class="src">${esc(shownSource(a))}${a.author ? `<span class="muted"> · ${txt(a.author)}</span>` : ""}</span><time datetime="${esc(a.publishedAt)}">${ago(a.publishedAt)}</time></div>`;
const starBtn = a => `<span class="star${isSaved(a.id) ? " on" : ""}" data-act="star" data-save="${esc(a.id)}" role="button" tabindex="0" aria-pressed="${isSaved(a.id) ? "true" : "false"}" aria-label="${isSaved(a.id) ? "Seçimdən çıxar" : "Seçilmişlərə saxla"}">${isSaved(a.id) ? "★" : "☆"}</span>`;
const card = a => `<article class="card${imgUrl(a) ? "" : " noimg"}" data-cat="${esc(a.category)}">${starBtn(a)}${img(a)}<div class="b">${badges(a, true, "pop")}<a class="card-hit" href="${esc(a.sourceUrl || "#")}" ${OUT}><h3>${txt(a.title)}</h3>${meta(a)}</a></div></article>`;

// Şəkil yüklənməsə (hotlink qadağası və s.) kart şəkilsiz rejimə keçir
window.imgFail = el => { const c = el.closest(".card"); if (c) c.classList.add("noimg"); el.remove(); };

/* ---------------------------------------------------------------- vəziyyət */
const S = { data: null, error: null, offline: false, lastSync: null, lang: null, club: null, q: "", shown: PAGE, etag: null, markets: null, social: null, status: null, og: null, video: null, football: null, pray: null, prayOpen: false, warn: [], fxOpen: false, fxFrom: "USD", fxTo: "AZN", fxAmt: 100, wx: null, wxAll: null, wxSel: null, wxOpen: false, ads: null, tixOn: false, tixArea: "merkez" };
const HIJRI_AZ = ["", "Məhərrəm", "Səfər", "Rəbiüləvvəl", "Rəbiülaxır", "Cümadəl-ula", "Cümadəl-axır", "Rəcəb", "Şaban", "Ramazan", "Şəvval", "Zilqədə", "Zilhiccə"];
const PRAY_ORDER = [["Fajr", "Sübh"], ["Sunrise", "Günəş"], ["Dhuhr", "Zöhr"], ["Asr", "Əsr"], ["Maghrib", "Məğrib"], ["Isha", "İşa"]];
const PRAY_SVG = {
  Fajr: `<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M4 18h16M12 8.2v2.1M8.3 11l1.4 1.4M15.7 11l-1.4 1.4" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round"/><path d="M8.4 18a3.6 3.6 0 0 1 7.2 0" fill="none" stroke="currentColor" stroke-width="1.7"/></svg>`,
  Sunrise: `<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M4 18.5h16M12 5.2v2.5M8 8l1.6 1.6M16 8l-1.6 1.6" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round"/><circle cx="12" cy="14.6" r="3.15" fill="none" stroke="currentColor" stroke-width="1.7"/></svg>`,
  Dhuhr: `<svg viewBox="0 0 24 24" aria-hidden="true"><circle cx="12" cy="12" r="3.2" fill="none" stroke="currentColor" stroke-width="1.7"/><path d="M12 3.6v2.2M12 18.2v2.2M3.6 12h2.2M18.2 12h2.2M6.1 6.1l1.6 1.6M16.3 16.3l1.6 1.6M17.9 6.1l-1.6 1.6M7.7 16.3l-1.6 1.6" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round"/></svg>`,
  Asr: `<svg viewBox="0 0 24 24" aria-hidden="true"><circle cx="14" cy="14.2" r="3.15" fill="none" stroke="currentColor" stroke-width="1.7"/><path d="M14 6.2v2.2M9 9.2l1.5 1.5M19 10l-1.4 1.3M6.4 14.4H8.6" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round"/></svg>`,
  Maghrib: `<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M3.5 18.2h17M12 6.6v2.4M8.5 9.2l1.5 1.5M15.5 9.2 14 10.7" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round"/><path d="M7.2 18.2a4.8 4.8 0 0 1 9.6 0" fill="none" stroke="currentColor" stroke-width="1.7"/></svg>`,
  Isha: `<svg viewBox="0 0 24 24" aria-hidden="true"><path fill="currentColor" d="M14.8 3.6a7.1 7.1 0 1 0 5.6 11.2A6.2 6.2 0 0 1 14.8 3.6z"/></svg>`,
};
// WARN_RE dar saxlanır. Tıxac səhifəsi aşağıdakı ROAD_RULES ilə süzülür.
const WARN_RE = /tıxac|yol(?:un|lar(?:ın)?)?\s+bağlan|yol bağlı|avtomobil yol|nəqliyyatın hərəkət|(?:ağır |yol )qəza|hava xəbərdar|güclü külək|güclü yağış|şaxta|çovğun|dolu yağ|yağış xəbərdar|(?:^|[^\p{L}])sel(?:[^\p{L}]|$)/iu;
const TRAFFIC_AREAS = [
  { id: "merkez", label: "Bakı mərkəz", lat: 40.4093, lon: 49.8671, zoom: 12 },
  { id: "sumqayit", label: "Sumqayıt yolu", lat: 40.482, lon: 49.835, zoom: 13 },
  { id: "hava", label: "Hava limanı yolu", lat: 40.45, lon: 50.0, zoom: 13 },
  { id: "abseron", label: "Abşeron", lat: 40.45, lon: 49.95, zoom: 11 },
];
const ROAD_RULES = [
  { icon: "💥", kind: "qeza", re: /qəza(?!lı)/iu },
  { icon: "🚧", kind: "bagli", re: /(?:yol|küçə|prospekt|körpü|tunel|şose)\w{0,6}\s*bağlan|bağlan\w{0,8}\s+(?:yol|küçə|prospekt)|yol bağlı|hərəkət\w{0,4}\s+məhdudlaş|(?:yol|küçə|prospekt|körpü|tunel|şose)\w{0,8}.{0,40}təmir|təmir.{0,32}(?:yol|küçə|prospekt|körpü|tunel|şose)/iu },
  { icon: "🚦", kind: "tixac", re: /tıxac/iu },
  { icon: "🚇", kind: "metro", re: /metro|avtobus/iu },
  { icon: "🌧", kind: "hava", re: /hava xəbərdar|güclü külək|güclü yağış|şaxta|çovğun|dolu yağ|yağış xəbərdar|(?:^|[^\p{L}])sel(?:[^\p{L}]|$)/iu },
];
const ROAD_FALLBACK = /(?:^|[^\p{L}])(?:BNA|DYP)(?:[^\p{L}]|$)|yol polisi|nəqliyyatın hərəkət|avtomobil yol/iu;
function roadKind(title) {
  const t = decode(title || "");
  for (const r of ROAD_RULES) if (r.re.test(t)) return r;
  if (ROAD_FALLBACK.test(t)) return { icon: "🚦", kind: "yol" };
  return null;
}
function roadItems(list) {
  return (list || []).filter(a => (a.lang ?? "az") === "az").flatMap(a => {
    const k = roadKind(a.title);
    return k ? [{ ...a, icon: k.icon, kind: k.kind }] : [];
  }).sort((a, b) => new Date(b.publishedAt) - new Date(a.publishedAt));
}
function tixArea() { return TRAFFIC_AREAS.find(a => a.id === S.tixArea) || TRAFFIC_AREAS[0]; }
function wazeSrc(a) { return `https://embed.waze.com/iframe?zoom=${a.zoom}&lat=${a.lat}&lon=${a.lon}`; }
function wazeLive(a) { return `https://www.waze.com/live-map?ll=${a.lat},${a.lon}&zoom=${a.zoom}`; }
function bakuClock(date = new Date()) {
  const fmt = new Intl.DateTimeFormat("en-US", { timeZone: "Asia/Baku", hourCycle: "h23", weekday: "short", hour: "numeric" });
  const parts = Object.fromEntries(fmt.formatToParts(date).map(p => [p.type, p.value]));
  return { wd: parts.weekday, hour: Number(parts.hour) };
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
function roadHot(list) { return bakuRush() || roadItems(list).some(roadFresh); }
function syncTixDot() {
  const hot = roadHot(S.data?.articles || []);
  document.querySelectorAll(".tix-btn").forEach(el => {
    el.classList.toggle("hot", hot);
    el.setAttribute("aria-label", hot ? "Tıxac — diqqət" : "Tıxac");
  });
}
const SAVE_KEY = "8ulduz-saved";
function savedList() { try { const v = JSON.parse(storage.getItem(SAVE_KEY) || "[]"); return Array.isArray(v) ? v : []; } catch { return []; } }
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
  const fresh = (articles || []).filter(isFresh);
  let seen = null;
  try { seen = JSON.parse(storage.getItem(SEEN_KEY) || "null"); } catch {}
  if (!Array.isArray(seen)) {
    storage.setItem(SEEN_KEY, JSON.stringify(fresh.map(a => a.id)));
    return;
  }
  const known = new Set(seen);
  const novel = fresh.filter(a => a.id && !known.has(a.id)).slice(0, 3);
  for (const a of novel) {
    try {
      const n = new Notification("Son dəqiqə", { body: decode(a.title), icon: "./assets/icon-192.png", tag: "break-" + a.id });
      n.onclick = () => { window.focus(); if (a.sourceUrl) window.open(a.sourceUrl, "_blank", "noopener,noreferrer"); };
    } catch {}
  }
  storage.setItem(SEEN_KEY, JSON.stringify(fresh.map(a => a.id)));
}
async function armNotify() {
  if (!("Notification" in window)) return;
  let perm = Notification.permission;
  if (perm === "default") { try { perm = await Notification.requestPermission(); } catch { perm = "denied"; } }
  if (perm !== "granted") { storage.removeItem(NOTIFY_KEY); renderTicker(); return; }
  storage.setItem(NOTIFY_KEY, "1");
  storage.setItem(SEEN_KEY, JSON.stringify((S.data?.articles || []).filter(isFresh).map(a => a.id)));
  try {
    const reg = await navigator.serviceWorker.ready;
    if (reg.periodicSync) await reg.periodicSync.register("breaking", { minInterval: 5 * 60 * 1000 });
  } catch {}
  renderTicker();
}
function adSlots() { return (S.ads?.slots || []).filter(s => s && s.image && s.link); }
function adHtml() {
  const slots = adSlots();
  if (!slots.length) return `<section class="ad" aria-label="Reklam yeri">Reklam yeri</section>`;
  const s = slots[Math.floor(Date.now() / 30000) % slots.length];
  return `<section class="ad ad-live" aria-label="Reklam"><a href="${esc(s.link)}" target="_blank" rel="sponsored noopener noreferrer"><img src="${esc(s.image)}" alt="${esc(s.alt || "Reklam")}" loading="lazy" decoding="async"></a></section>`;
}
const byId = new Map();

/* ---------------------------------------------------------------- məlumat */
async function loadNews() {
  if (S.newsLoading) return;
  S.newsLoading = true;
  try {
    const r = await fetch(freshUrl("data/news.json"), { cache: "no-store" });
    if (!r.ok) throw new Error(`HTTP ${r.status}`);
    const tag = r.headers.get("etag") || r.headers.get("last-modified");
    S.offline = r.headers.get("X-8ulduz-data") === "cache";
    if (tag && tag === S.etag && S.data) {
      if (!S.offline) S.lastSync = new Date();
      S.error = null; renderTopbar(); return;
    }
    const d = await r.json();
    if (!Array.isArray(d.articles)) throw new Error("Xəbər məlumatının quruluşu yanlışdır");
    S.etag = tag;
    if (!S.offline) S.lastSync = new Date();
    S.error = null;
    if (S.data && S.data.updatedAt === d.updatedAt && S.og) { renderTopbar(); return; }
    await loadOg();
    for (const a of d.articles || []) if (!a.imageUrl && S.og[a.sourceUrl]) a.imageUrl = S.og[a.sourceUrl];
    d.articles = collapseExact(clusterArticles(d.articles));
    S.data = d; byId.clear(); for (const a of d.articles) byId.set(a.id, a);
    checkBreaking(d.articles);
    render();
  } catch (e) { S.error = String(e); S.offline = !navigator.onLine; if (!S.data) render(); else renderTopbar(); }
  finally { S.newsLoading = false; }
}

async function loadOg() {
  if (S.og) return;
  try {
    const r = await fetch(freshUrl("data/og.json"), { cache: "no-store" });
    const d = r.ok ? await r.json() : {};
    S.og = d && typeof d === "object" && !Array.isArray(d) ? d : {};
  } catch { S.og = {}; }
}
async function loadMarkets() {
  // Əsas mənbə: updater.py-nin yaratdığı data/markets.json (AMB, Yahoo Finance, gold-api və s.)
  try {
    const r = await fetch(freshUrl("data/markets.json"), { cache: "no-store" });
    if (r.ok) { const d = await r.json(); if (d.items?.length) { S.markets = d.items; renderMarkets(); return; } }
  } catch {}
  // Ehtiyat: brauzerdən birbaşa (açarsız, CORS açıq API-lər)
  const items = [];
  try {
    const g = await (await fetch("https://open.er-api.com/v6/latest/USD")).json(), azn = g.rates.AZN;
    items.push({ label: "Dollar", value: azn, dec: 4, unit: "AZN" }, { label: "Avro", value: azn / g.rates.EUR, dec: 4, unit: "AZN" },
      { label: "100 Rubl", value: azn / g.rates.RUB * 100, dec: 4, unit: "AZN" }, { label: "100 Lirə", value: azn / g.rates.TRY * 100, dec: 4, unit: "AZN" });
  } catch {}
  for (const [sym, label, dec] of [["XAU", "Qızıl", 1], ["XAG", "Gümüş", 2]]) {
    try { const x = await (await fetch(`https://api.gold-api.com/price/${sym}`)).json(); x?.price && items.push({ label, value: x.price, dec, unit: "USD" }); } catch {}
  }
  if (items.length) { S.markets = items; renderMarkets(); }
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
async function loadWeather() { try { S.wx = (await weather([CITIES[0]]))[0]; renderTopbar(); } catch {} }
async function loadAllWeather() {
  if (S.wxAll) return; renderTopbar();
  try { S.wxAll = (await weather(CITIES)).sort((a, b) => a.city.localeCompare(b.city, "az")); } catch { S.wxAll = []; }
  renderTopbar();
}

/* ---------------------------------------------------------------- marşrut */
function route() {
  let h = location.hash.replace(/^#/, "") || "/";
  try { h = decodeURIComponent(h); } catch {} // natamam %-kod səhifəni dayandırmasın
  if (h === "/menbeler" || h.startsWith("/menbeler?")) return { name: "sources" };
  if (h === "/videolent" || h.startsWith("/videolent?")) return { name: "videos" };
  if (h === "/secilmis" || h.startsWith("/secilmis?")) return { name: "saved" };
  if (h === "/bolmeler" || h.startsWith("/bolmeler?")) return { name: "sections" };
  const m = h.match(/^\/bolme\/([^/?]+)/); if (m) return { name: "section", slug: m[1] };
  if (h === "/tixac" || h.startsWith("/tixac?")) return { name: "traffic" };
  const q = h.match(/^\/axtar(?:\?q=(.*))?$/); if (q) return { name: "search", q: q[1] || "" };
  return { name: "home" };
}

/* ---------------------------------------------------------------- render */
function shell() {
  $("#app").innerHTML = `
  <a class="skip" href="#view">Məzmuna keç</a>
  <div class="topbar"><div class="wrap" id="topbar"></div></div>
  <header class="site" id="sitehead"><div class="wrap hrow">
    <a class="logo" href="#/"><i>${STAR}</i><b>8<span>ULDUZ</span></b></a>
    <nav class="main" id="nav" aria-label="Bölmələr"></nav>
    <a class="tix-stick tix-btn tix-band" href="#/tixac" title="Tıxac və yollar" aria-label="Tıxac">Tıxac</a>
    <label class="search"><span class="sr" hidden>Axtar</span>
      <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><circle cx="11" cy="11" r="7"/><path d="m20 20-3.5-3.5"/></svg>
      <input id="q" type="search" placeholder="Xəbər axtar…" autocomplete="off" aria-label="Xəbər axtar"></label>
  </div><div class="langstick" id="langstick"></div></header>
  <div id="ticker"></div>
  <div class="markets" id="markets" hidden><div class="wrap mk-wrap"><div class="mk-grid" id="mk"></div><div id="fx-slot"></div></div></div>
  <div class="filters"><div class="wrap" id="langs"></div></div>
  <main><div class="wrap" id="view" tabindex="-1"></div></main>
  <div class="wrap"><section class="cta" id="cta"><span class="ic">📬</span><div><h2>8ulduz kanalına qoşulun</h2><p>Ən vacib xəbərlər dərhal Telegram kanalımızda — vaxt itirmədən xəbərdar olun.</p></div><a class="btn" href="https://t.me/" target="_blank" rel="noopener noreferrer">Kanala keç →</a></section></div>
  <footer id="footer"></footer>
  <button class="totop" id="totop" aria-label="Yuxarı qayıt">↑</button>
  <nav class="tabbar" aria-label="Sürətli keçid">
    <a href="#/" data-tab="home"><b>⌂</b><span>Əsas</span></a>
    <a href="#/tixac" data-tab="traffic" class="tix-band"><span>Tıxac</span></a>
    <a href="#/bolmeler" data-tab="sections"><b>▦</b><span>Bölmələr</span></a>
    <button type="button" data-act="find"><b>⌕</b><span>Axtar</span></button>
    <a href="#/secilmis" data-tab="saved"><b>☆</b><span>Seçilmişlər</span></a>
  </nav>`;
  const q = $("#q");
  q.addEventListener("input", () => {
    S.q = q.value.trim(); S.shown = PAGE;
    const want = S.q ? `#/axtar?q=${encodeURIComponent(S.q)}` : "#/";
    if (location.hash !== want) history.replaceState(null, "", want);
    renderNav();
    renderView();
  });
  document.addEventListener("click", onClick);
  window.addEventListener("hashchange", () => { S.shown = PAGE; S.club = null; syncQuery(); render(); window.scrollTo(0, 0); });
  window.addEventListener("scroll", () => { $("#totop").classList.toggle("show", scrollY > 600); syncLangStick(); }, { passive: true });
  $("#totop").onclick = () => scrollTo({ top: 0, behavior: "smooth" });
  syncQuery();
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
  else if (r.name === "saved") { name = "Seçilmişlər"; desc = "Bu cihazda saxlanan xəbərlər."; }
  else if (r.name === "sources") { name = "Mənbə vəziyyəti"; desc = "RSS lentlərinin son yoxlanması."; }
  else if (r.name === "sections") { name = "Mənim bölmələrim"; desc = "Baş səhifə bölmələrinin sırası."; }
  else if (r.name === "videos") { name = "Video xəbərlər"; desc = "Azərbaycan kanallarının video lentləri."; }
  document.title = `${name} — 8ulduz`;
  if (md && desc) md.setAttribute("content", desc);
}

function renderTopbar() {
  const w = S.wx, upd = S.status?.checkedAt || S.data?.updatedAt;
  const stale = upd && Date.now() - new Date(upd).getTime() > 15 * 60e3;
  const syncBad = S.error || S.offline || S.status?.ok === false || stale;
  const syncText = S.offline ? "Oflayn — saxlanmış xəbərlər" : S.error ? "Xəbərlər yenilənmədi" : S.status?.ok === false ? "Mənbələr yoxlanmadı" : stale ? "Xəbər lenti köhnəlib" : S.status?.degraded ? "Bəzi mənbələr açılmır" : "";
  let pop = "";
  if (S.wxOpen) {
    const sel = S.wxSel && (S.wxAll || []).find(x => x.city === S.wxSel);
    pop = `<div class="wx-pop" role="dialog" aria-label="Bölgələr üzrə hava">` + (sel
      ? `<button class="wx-back" data-act="wx-back">← Bölgələrə qayıt</button>
         <div class="wx-now"><span class="wx-emo">${sel.icon}</span><div><b>${esc(sel.city)}</b><div class="muted">${esc(sel.label)}</div></div><b class="wx-temp">${sel.temp}°</b></div>
         <div class="wx-det">${[["Hiss olunur", `${sel.feels}°`], ["Rütubət", `%${sel.humidity}`], ["Külək", `${sel.wind} km/s`], ["Təzyiq", `${sel.pressure} hPa`], ["Yağıntı", `${sel.precip} mm`]].map(([k, v]) => `<div><small>${k}</small><b>${v}</b></div>`).join("")}</div>`
      : `<div class="wx-head"><span>Bölgələr üzrə hava</span><button data-act="wx-close" aria-label="Bağla">✕</button></div>` +
        (!S.wxAll ? `<div class="empty" style="padding:24px 0">Yüklənir…</div>` :
          `<div class="wx-grid">${S.wxAll.map(c => `<button class="wx-city" data-city="${esc(c.city)}"><span>${c.icon} ${esc(c.city)}</span><b>${c.temp}°</b></button>`).join("")}</div>`)) + `</div>`;
  }
  const fs = document.documentElement.dataset.fs || "0";
  const light = document.documentElement.dataset.theme === "light";
  $("#topbar").innerHTML = `    <span>${today()}</span>
    ${prayBit()}
    <div class="wx ${S.wxOpen ? "open" : ""}"><button class="wx-btn" data-act="wx" title="Azərbaycanın bölgələri üzrə hava"><span>${w ? w.icon : "🌡️"}</span><span>Bakı</span><b>${w ? `${w.temp}°` : "—"}</b><span style="opacity:.6">▾</span></button>${pop}</div>
    <a class="tix-pill tix-btn tix-band" href="#/tixac" title="Tıxac və yollar" aria-label="Tıxac"><span class="tix-lab">Tıxac</span></a>
    <span class="sp sync">${S.lastSync ? `Son əlaqə: ${S.lastSync.toLocaleTimeString("az-AZ")}` : ""}</span>
    ${syncText ? `<span class="sync-state${syncBad ? " bad" : ""}" role="status">${syncText}</span>` : ""}
    ${upd ? `<span class="yenilendi"><span class="dot${syncBad ? "" : " live"}" style="background:${syncBad ? "var(--red)" : "#34d399"}"></span>Yeniləndi: ${ago(upd)}</span>` : ""}
    <span class="prefs"><button data-act="theme" title="${light ? "Qaranlıq mövzu" : "İşıqlı mövzu"}" aria-label="Mövzu">${light ? "☾" : "☀"}</button><button data-act="fs-down" title="Şrifti kiçilt" aria-label="Şrifti kiçilt" ${fs === "0" ? "disabled" : ""}>A−</button><button data-act="fs-up" title="Şrifti böyüt" aria-label="Şrifti böyüt" ${fs === "2" ? "disabled" : ""}>A+</button></span>`;
  syncTixDot();
}

function renderNav() {
  const r = route(), cur = r.name === "section" ? r.slug : r.name === "home" ? "/" : "";
  $("#nav").innerHTML = `<a href="#/" class="${cur === "/" ? "on" : ""}">Baş səhifə</a>` +
    CATS.map(c => `<a href="#/bolme/${c.slug}" class="${cur === c.slug ? "on" : ""}">${esc(c.label)}</a>`).join("") +
    `<a href="#/tixac" class="nav-tix tix-band${r.name === "traffic" ? " on" : ""}">Tıxac</a>`;
  fitNav();
}
function fitNav() {
  const nav = $("#nav");
  if (!nav) return;
  nav.querySelectorAll(".nav-more").forEach(el => el.remove());
  const links = [...nav.querySelectorAll(":scope > a")];
  links.forEach(a => { a.hidden = false; });
  const desktop = matchMedia("(min-width: 721px)").matches;
  if (!desktop) return;
  const fits = () => nav.scrollWidth <= nav.clientWidth + 1;
  if (fits()) return;
  const tix = links.find(a => a.classList.contains("nav-tix"));
  const rest = links.filter(a => a !== tix && a.getAttribute("href") !== "#/");
  const more = document.createElement("details");
  more.className = "nav-more";
  more.innerHTML = `<summary>Daha çox</summary><div class="nav-more-pop"></div>`;
  const pop = more.querySelector(".nav-more-pop");
  if (tix) nav.insertBefore(more, tix); else nav.appendChild(more);
  for (let i = rest.length - 1; i >= 0 && !fits(); i--) {
    rest[i].hidden = true;
    const clone = rest[i].cloneNode(true);
    clone.hidden = false;
    pop.prepend(clone);
  }
  if (!pop.children.length) { more.remove(); return; }
  more.classList.toggle("has-on", [...pop.children].some(a => a.classList.contains("on")));
}

function renderTicker() {
  const latest = byDate((S.data?.articles ?? []).filter(a => (a.lang ?? "az") === "az"));
  const breaking = latest.filter(isFresh);
  const list = (breaking.length ? breaking : latest).slice(0, 12);
  if (!list.length) { $("#ticker").innerHTML = ""; return; }
  const items = [...list, ...list].map(a => `<a href="${esc(a.sourceUrl)}" ${OUT}>${txt(a.title)}</a>`).join("");
  const bell = !("Notification" in window) ? "" : `<button type="button" class="bell${notifyOn() ? " on" : ""}" data-act="notify" title="Son dəqiqə bildirişi. Səhifə açıq olanda yoxlanır.">${notifyOn() ? "Açıq" : "Bildiriş"}</button>`;
  $("#ticker").innerHTML = `<div class="ticker"><div class="lbl">${breaking.length ? "⚡ Son dəqiqə" : "Son xəbərlər"}${bell}</div><div class="run"><div class="track">${items}</div></div></div>`;
}

function prayIcon(key) {
  return `<span class="pi">${PRAY_SVG[key] || ""}</span>`;
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
  return "Bakı";
}
function prayCityOptions(current) {
  return [...CITIES].sort((a, b) => a[0].localeCompare(b[0], "az")).map(([name]) => `<option value="${esc(name)}"${name === current ? " selected" : ""}>${esc(name)}</option>`).join("");
}
function prayBit() {
  const p = S.pray;
  const city = p?.city || savedPrayCity();
  if (!p) return `<button class="pray" data-act="pray" type="button">Namaz · ${esc(city)}</button>`;
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
  const pop = S.prayOpen ? `<div class="pray-pop" role="dialog" aria-label="Namaz vaxtları"><div class="pray-h"><b>Namaz</b><span>${esc(hijri)} ${esc(String(h.year || ""))}</span></div><label class="pray-pick"><span>Şəhər</span><select class="pray-city" aria-label="Namaz şəhəri">${prayCityOptions(city)}</select></label>${rows}</div>` : "";
  return `<div class="pray-wrap${S.prayOpen ? " open" : ""}"><button class="pray" data-act="pray" type="button" aria-expanded="${S.prayOpen ? "true" : "false"}">${prayIcon(next.key)}<span class="pcity">Namaz · ${esc(city)}</span><b>${esc(next.lab)}</b><b class="pt">${esc(next.time)}</b><span class="phij">${esc(hijri)}</span><span class="caret" aria-hidden="true">▾</span></button>${pop}</div>`;
}
function nextPrayer(times) {
  if (!times) return { key: "", lab: "Namaz", time: "", mins: null };
  const now = new Date();
  const mins = now.getHours() * 60 + now.getMinutes();
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
  $("#markets").hidden = false;
  $("#mk").innerHTML = m.map(i => {
    const has = i.changePct != null && i.change != null;
    const cls = !has ? "flat" : i.changePct > 0 ? "up" : i.changePct < 0 ? "down" : "flat";
    const chg = has ? `<span>${i.changePct > 0 ? "↑" : i.changePct < 0 ? "↓" : "•"} %${Math.abs(i.changePct).toFixed(2)}</span><span>${i.change > 0 ? "+" : ""}${fmt(i.change, i.dec)}</span>`
      : `<span>${i.unit === "AZN" ? "məzənnə" : "qiymət"}</span><span>${i.unit === "AZN" ? "AZN" : "$"}</span>`;
    const title = [i.src && `Mənbə: ${i.src}`, i.asOf && `Tarix: ${i.asOf}`, i.stale && "son məlum qiymət"].filter(Boolean).join(" · ");
    return `<button type="button" class="mk" data-fx="${esc(i.id)}" title="${esc(title)}"><div class="n">${esc(i.label)}</div><div class="v">${fmt(i.value, i.dec)}<small>${i.unit === "AZN" ? "₼" : "$"}</small></div><div class="c ${cls}">${chg}</div></button>`;
  }).join("");
  const slot = $("#fx-slot"); if (slot) slot.innerHTML = fxPop();
  const from = $("#fx-from"), to = $("#fx-to"), amt = $("#fx-amt");
  if (from && to && amt) {
    from.value = S.fxFrom; to.value = S.fxTo;
    const sync = () => {
      S.fxFrom = from.value; S.fxTo = to.value; S.fxAmt = Number(amt.value) || 0;
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
  const dec = S.fxTo === "AZN" || S.fxTo === "BTC" ? 2 : 4;
  return `<div class="fx-pop" role="dialog"><div class="fx-h"><b>Çevirici</b><button type="button" data-act="fx-close" aria-label="Bağla">✕</button></div>
    <label>Məbləğ<input id="fx-amt" type="number" min="0" step="any" value="${esc(S.fxAmt)}"></label>
    <div class="fx-row"><select id="fx-from">${opts}</select><span>→</span><select id="fx-to">${opts}</select></div>
    <b class="fx-out">${out == null ? "—" : fmt(out, dec)}</b></div>`;
}

function langButtons(compact) {
  const btn = (code, label, short) => {
    const on = code ? S.lang === code : S.lang === null;
    return `<button type="button" class="pill${on ? " on" : ""}" data-lang="${code}" aria-label="${esc(label)}"${compact ? ` title="${esc(label)}"` : ""}>${esc(compact ? short : label)}</button>`;
  };
  return btn("", "Hamısı", "Hamısı") + LANGS.map(l => btn(l.code, l.label, LANG_BADGE[l.code] || l.code.toUpperCase())).join("");
}
function renderLangs() {
  const row = $("#langs");
  if (row) row.innerHTML = langButtons(false);
  const stick = $("#langstick");
  if (stick) stick.innerHTML = `<div class="wrap">${langButtons(true)}</div>`;
  syncLangStick();
}
function syncLangStick() {
  const head = document.querySelector("header.site");
  const filters = document.querySelector(".filters");
  if (!head || !filters) return;
  head.classList.toggle("stuck", filters.getBoundingClientRect().bottom <= head.getBoundingClientRect().bottom + 1);
}

function filtered(list) { return S.lang ? list.filter(a => langOf(a) === S.lang) : list; }

function orderedSocialPosts(max = 8) {
  const all = S.social?.posts || [];
  const bucket = p => p.who === "prezident" ? 0 : p.who === "birinci-xanim" ? 1 : 2;
  const groups = [[], [], []];
  for (const p of all) groups[bucket(p)].push(p);
  const [prez, lady, rest] = groups.map(g => byDate(g));
  const ladyKeep = lady.length ? Math.min(lady.length, max <= 4 ? 1 : 3) : 0;
  const prezTake = Math.min(prez.length, max - ladyKeep);
  const ladyTake = Math.min(lady.length, max - prezTake);
  return [...prez.slice(0, prezTake), ...lady.slice(0, ladyTake), ...rest.slice(0, max - prezTake - ladyTake)];
}
const NET_ICON = {
  x: `<svg viewBox="0 0 24 24" width="13" height="13" aria-hidden="true"><path fill="currentColor" d="M14.6 3h3.1l-6.8 7.8L19 21h-2.7l-5.3-6.9L6.3 21H3.1l7.3-8.4L3.4 3h2.8l4.8 6.3L14.6 3Zm-1.1 16.2h1.5L6.6 4.7H5L13.5 19.2Z"/></svg>`,
  ig: `<svg viewBox="0 0 24 24" width="13" height="13" aria-hidden="true"><rect x="3.5" y="3.5" width="17" height="17" rx="5" fill="none" stroke="currentColor" stroke-width="2"/><circle cx="12" cy="12" r="3.5" fill="none" stroke="currentColor" stroke-width="2"/><circle cx="17.2" cy="6.8" r="1.1" fill="currentColor"/></svg>`,
  fb: `<svg viewBox="0 0 24 24" width="13" height="13" aria-hidden="true"><path fill="currentColor" d="M14 8.5h3V5.5h-3c-2.5 0-4 1.6-4 4.1V12H8v3h2v7h3v-7h2.4l.6-3H13v-2.2c0-.7.3-1.3 1-1.3Z"/></svg>`,
  yt: `<svg viewBox="0 0 24 24" width="14" height="14" aria-hidden="true"><path fill="currentColor" d="M22.5 12.2s0-3-.4-4.3c-.2-.9-.9-1.6-1.8-1.8C18.8 5.7 12 5.7 12 5.7s-6.8 0-8.3.4c-.9.2-1.6.9-1.8 1.8C1.5 9.2 1.5 12.2 1.5 12.2s0 3 .4 4.3c.2.9.9 1.6 1.8 1.8 1.5.4 8.3.4 8.3.4s6.8 0 8.3-.4c.9-.2 1.6-.9 1.8-1.8.4-1.3.4-4.3.4-4.3ZM9.8 15.4V9l6 3.2-6 3.2Z"/></svg>`,
};
const netIcon = name => name === "Instagram" ? NET_ICON.ig : name === "Facebook" ? NET_ICON.fb : name === "YouTube" ? NET_ICON.yt : NET_ICON.x;
function profileRows() {
  const whoOrder = { "İlham Əliyev": 0, "Mehriban Əliyeva": 1 };
  return [...PROFILES].sort((a, b) => (whoOrder[a.who] ?? 9) - (whoOrder[b.who] ?? 9))
    .map(g => `<span class="soc-g"><b>${esc(g.who)}</b>${g.links.map(([n, u]) => `<a href="${u}" target="_blank" rel="noopener noreferrer" title="${esc(n)}" aria-label="${esc(g.who)}, ${esc(n)}">${netIcon(n)}${n === "X (AZ)" ? "<i>AZ</i>" : ""}</a>`).join("")}</span>`).join("");
}
function socialForSide() {
  const head = orderedSocialPosts(3);
  const seen = new Set(head.map(p => p.url || p.text));
  const more = orderedSocialPosts(40).filter(p => !seen.has(p.url || p.text));
  return [...head, ...more].slice(0, 10);
}
function socialBlock(side = false) {
  const posts = side ? socialForSide() : orderedSocialPosts(8);
  const cards = posts.map(p => `<a class="soc-p" href="${esc(p.url)}" target="_blank" rel="noopener noreferrer"><span class="soc-ic">${netIcon(p.network)}</span><span class="t">${txt(p.text)}</span><time>${ago(p.publishedAt)}</time></a>`).join("");
  const list = side ? `<div class="soc-list" data-marquee data-visible="4">` : `<div class="soc-list">`;
  return `<aside class="soc"><div class="soc-h"><b>Sosial şəbəkələr</b></div><div class="soc-links">${profileRows()}</div>${cards ? `${list}${cards}</div>` : `<p class="soc-empty muted">Yazılar hazırda açılmır — hesablara yuxarıdakı keçidlərdən baxın.</p>`}</aside>`;
}
function prezBlock(list) {
  const cards = list.map(a => `<a class="pcard" data-cat="${esc(a.category)}" href="${esc(a.sourceUrl)}" ${OUT}><span class="t">${isFirstLady(a) ? `<em class="tag">Birinci xanım</em>` : ""}${altBadge(a)}${txt(a.title)}</span><span class="meta"><span class="src">${esc(shownSource(a))}</span><time>${ago(a.publishedAt)}</time></span></a>`).join("");
  return `<section class="prez"><div class="prez-h"><h2>${STAR}<a href="#/bolme/prezident">Zuğulba Xronikası</a></h2>
    <span class="cnt muted">${list.length} xəbər</span>
    <span class="links">${PREZ_LINKS.map(l => `<a href="${l.url}" target="_blank" rel="noopener noreferrer">${l.name}</a>`).join("")}</span>
    <a class="btn" href="#/bolme/prezident">Hamısı →</a></div>
    <div class="prez-body">${list.length ? `<div class="prez-grid" data-marquee data-visible="4" data-visible-narrow="3">${cards}</div>` : ""}
    ${socialBlock(true)}</div></section>`;
}

function heroBlock(list) {
  if (!list.length) return "";
  const main = list.find(a => a.imageUrl && (a.lang ?? "az") === "az") ?? list.find(a => a.imageUrl) ?? list[0];
  const side = list.filter(a => a !== main).slice(0, 8);
  return `<section class="hero">
    <a class="hero-main" data-cat="${esc(main.category)}" href="${esc(main.sourceUrl)}" ${OUT}>${img(main, "", true)}<div class="body">
      <div class="badges"><span class="bd gold" data-cat="${esc(main.category)}"><i class="cdot"></i>${esc(catLabel(main.category))}</span>${altBadge(main)}${isFresh(main) ? `<span class="bd red">Son dəqiqə</span>` : ""}</div>
      <h1>${txt(main.title)}</h1>
      <div class="meta"><span class="src">${esc(main.source)}</span><time>${ago(main.publishedAt)}</time></div></div></a>
    <div class="hero-slot"><div class="hero-side" data-marquee data-visible="4">${side.map(a => `<a class="row-card" data-cat="${esc(a.category)}" href="${esc(a.sourceUrl)}" ${OUT}>${img(a)}<div class="x"><span class="tag" data-cat="${esc(a.category)}"><i class="cdot"></i>${esc(catLabel(a.category))}</span><span class="t">${txt(a.title)}</span><span class="meta"><span class="src">${esc(a.source)}</span><time>${ago(a.publishedAt)}</time></span></div></a>`).join("")}</div></div>
  </section>`;
}

function alertStrip() {
  const hits = roadItems(S.data?.articles || []).slice(0, 3);
  const wx = (S.warn || []).join(" · ");
  const rush = bakuRush() ? `<a class="rush" href="#/tixac">Pik saat — xəritəyə baxın</a>` : "";
  return `<section class="alerts"><b>Yol və hava</b>${rush}<a class="tix-go tix-band" href="#/tixac">Tıxac xəritəsi</a>${wx ? `<span class="wxn">${esc(wx)}</span>` : ""}${hits.map(a => `<a href="${esc(a.sourceUrl || "#")}" ${OUT}>${a.icon} ${txt(a.title)}</a>`).join("")}</section>`;
}
function ytBlock() {
  const items = S.video?.items || [];
  if (!items.length) return "";
  const cards = items.slice(0, 8).map(v => `<button type="button" class="yt" data-yt="${esc(v.videoId)}"><span class="thumb">${v.imageUrl ? `<img src="${esc(v.imageUrl)}" alt="" loading="lazy">` : ""}<i>▶</i></span><span class="cap"><b>${esc(v.channel)}</b><span>${txt(v.title)}</span></span></button>`).join("");
  return `<section><div class="sec-h"><h2>Video xəbərlər</h2><span class="cnt">${items.length}</span><a class="more" href="#/videolent">Hamısı →</a></div><div class="ytrow">${cards}</div></section>`;
}
function photoStrip(list) {
  const cut = Date.now() - 30 * HOUR;
  const pics = byDate(list.filter(a => a.imageUrl && new Date(a.publishedAt).getTime() > cut)).slice(0, 14);
  if (pics.length < 4) return "";
  return `<section><div class="sec-h"><h2>Foto qalereya</h2><span class="cnt">günün şəkilləri</span></div><div class="phrow">${pics.map(a => `<a href="${esc(a.sourceUrl)}" ${OUT}>${img(a)}<span>${txt(a.title)}</span></a>`).join("")}</div></section>`;
}
function footballBlock(list) {
  const fb = S.football;
  const news = byDate(list.filter(a => {
    const title = lc(decode(a.title));
    if (/(?:basketbol|voleybol|həndbol|tennis|cüdo|güləş|boks|futzal)/u.test(title)) return false;
    return a.category === "idman" && /futbol|premyer|liqa|qarabağ|neftçi|qarabag|sabah fk|mill[iı]/iu.test(title);
  })).slice(0, 4);
  const ev = fb?.events || [];
  if (!news.length && !ev.length) return "";
  const games = ev.slice(0, 3).map(e => `<li><b>${esc(e.home)}</b><span>${esc(e.hs ?? "–")} : ${esc(e.as ?? "–")}</span><b>${esc(e.away)}</b><time>${esc(e.date || "")}</time></li>`).join("");
  return `<section class="foot"><div class="sec-h"><h2>Futbol</h2><a class="more" href="${esc(fb?.link || "https://pfl.az/")}" target="_blank" rel="noopener noreferrer">pfl.az ↗</a></div>
    ${games ? `<ul class="games">${games}</ul>` : ""}
    ${fb?.note ? `<p class="muted foot-note">${esc(fb.note)}</p>` : ""}
    ${news.length ? `<div class="foot-news">${news.map(a => `<a href="${esc(a.sourceUrl)}" ${OUT}>${txt(a.title)}</a>`).join("")}</div>` : ""}</section>`;
}
function videosView() {
  const items = S.video?.items || [];
  const head = `<div class="page-h"><div><h1>Video xəbərlər</h1><p>Azərbaycan kanallarının YouTube lentləri. Video düyməyə basanda açılır.</p></div><span class="cnt">${items.length}</span></div>`;
  if (!items.length) return `${head}<p class="empty">Video lent hazırda açılmır. Bir az sonra yenidən baxın.</p>`;
  return `${head}<div class="ytgrid">${items.map(v => `<button type="button" class="yt" data-yt="${esc(v.videoId)}"><span class="thumb">${v.imageUrl ? `<img src="${esc(v.imageUrl)}" alt="" loading="lazy" decoding="async">` : ""}<i>▶</i></span><span class="cap"><b>${esc(v.channel)}</b><span>${txt(v.title)}</span></span></button>`).join("")}</div>`;
}
function videoBlock(list) {
  if (!list.length) return "";
  return `<section><div class="sec-h"><h2>Sayt videoları</h2><span class="cnt">${list.length} keçid</span><a class="more" href="#/bolme/video">Hamısı →</a></div>
    <div class="vrow">${list.slice(0, 15).map(a => `<a class="card vcard" href="${esc(a.sourceUrl)}" target="_blank" rel="noopener noreferrer">${img(a)}<div class="b"><h3>${txt(a.title)}</h3><div class="meta"><span class="src">${esc(a.source)}</span><time>${ago(a.publishedAt)} · mənbədə açır</time></div></div></a>`).join("")}</div></section>`;
}

// Ən yeni 8 xəbərdən şəkillilərə üstünlük ver (sıra yenə də tarixə görə qalır)
function pick4(list) {
  const top = list.slice(0, 8), withImg = top.filter(a => a.imageUrl);
  const chosen = new Set((withImg.length >= 4 ? withImg : [...withImg, ...top.filter(a => !a.imageUrl)]).slice(0, 4));
  return top.filter(a => chosen.has(a));
}
function catSection(c, list) {
  if (!list.length) return "";
  return `<section><div class="sec-h"><h2>${esc(c.label)}</h2><span class="cnt">${list.length}</span><a class="more" href="#/bolme/${c.slug}">Hamısı →</a></div>
    <div class="grid">${pick4(list).map(card).join("")}</div></section>`;
}

function skeleton() {
  return `<section class="prez"><div class="skel" style="height:180px"></div></section>
    <section class="hero"><div class="skel" style="height:340px"></div><div class="hero-side">${"<div class='skel' style='height:78px'></div>".repeat(4)}</div></section>
    <section><div class="grid">${"<div class='skel' style='height:220px'></div>".repeat(4)}</div></section>`;
}
function dayFive(list) {
  const cut = Date.now() - 18 * HOUR;
  return list.filter(a => new Date(a.publishedAt).getTime() >= cut)
    .map(a => ({ a, n: 1 + (a.alts?.length || 0) }))
    .sort((x, y) => y.n - x.n || (y.a.publishedAt || "").localeCompare(x.a.publishedAt || ""))
    .slice(0, 5).map(x => x.a);
}
function dayFiveBlock(list) {
  const items = dayFive(list);
  if (items.length < 2) return "";
  return `<section class="day5"><div class="sec-h"><h2>Günün 5 əsas xəbəri</h2><span class="cnt">son 18 saat</span></div>
    <ol>${items.map((a, i) => `<li><a href="${esc(a.sourceUrl)}" ${OUT}><b>${i + 1}</b><span>${txt(a.title)}</span><em>${1 + (a.alts?.length || 0)} mənbə</em></a></li>`).join("")}</ol></section>`;
}

function homeView() {
  const all = S.data.articles, m = filtered(all);
  const prez = prezHome(m);
  const vids = byDate(m.filter(a => a.video));
  const used = new Set();
  const hero = byDate(m).slice(0, 9); hero.forEach(a => used.add(a.id));
  const secs = homeCats().map(c => catSection(c, byDate(m.filter(a => a.category === c.slug && !used.has(a.id))))).join("");
  return prezBlock(prez) + adHtml() + heroBlock(byDate(m)) + dayFiveBlock(m) + alertStrip() + ytBlock() + photoStrip(m) + footballBlock(m) + `<section class="topread" hidden aria-hidden="true"></section>` + videoBlock(vids) + secs;
}

function listPage(title, desc, list, extra = "") {
  const shown = list.slice(0, S.shown);
  return `<div class="page-h"><div><h1>${esc(title)}</h1><p>${esc(desc)}</p></div><span class="cnt">${list.length} xəbər</span></div>${extra}` +
    (list.length ? `<div class="grid">${shown.map(card).join("")}</div>${list.length > shown.length ? `<button class="loadmore" data-act="more">Daha çox (${list.length - shown.length})</button>` : ""}`
      : `<p class="empty">${S.q ? "Axtarışınıza uyğun xəbər tapılmadı. Başqa sözlərlə yoxlayın və ya dil süzgəcini dəyişin." : "Bu bölmədə hələ xəbər yoxdur — növbəti yenilənmədə əlavə olunacaq."}</p>`);
}

function sectionView(slug) {
  const c = CATS.find(x => x.slug === slug);
  if (!c) return `<div class="empty"><h1 style="color:var(--fg)">Bölmə tapılmadı</h1><p>Axtardığınız bölmə mövcud deyil.</p><a href="#/" style="color:var(--primary);font-weight:700">← Baş səhifəyə qayıt</a></div>`;
  const d = S.data.articles;
  let list = slug === "video" ? d.filter(a => a.video) : slug === "sondeqiqe" ? d.filter(isFresh) : d.filter(a => a.category === slug);
  list = byDate(list);
  if (slug === "prezident") list = byDate(list);
  let extra = "";
  if (slug === "idman") {
    if (S.club) { const keys = CLUBS.find(k => k[0] === S.club)?.[1] ?? []; list = list.filter(a => { const s = lc(a.title + " " + a.summary); return keys.some(k => s.includes(k)); }); }
    extra = `<div class="chips"><button class="pill ${S.club === null ? "on" : ""}" data-club="">Bütün idman</button>${CLUBS.map(([n]) => `<button class="pill ${S.club === n ? "on" : ""}" data-club="${esc(n)}">${esc(n)}</button>`).join("")}</div>`;
  }
  if (slug === "prezident") extra = socialBlock();
  return listPage(c.label, c.description, filtered(list), extra);
}

function searchView() {
  const words = lc(S.q).split(/\s+/).filter(Boolean);
  const list = byDate(filtered(S.data.articles.filter(a => { const s = lc(decode(a.title + " " + a.summary + " " + a.source)); return words.every(w => s.includes(w)); })));
  return listPage(`Axtarış: “${S.q}”`, "Başlıq, xülasə və mənbə adına görə", list);
}

function trafficView() {
  const area = tixArea();
  const items = roadItems(S.data?.articles || []).slice(0, 40);
  const jumps = TRAFFIC_AREAS.map(a => `<button type="button" class="pill${a.id === area.id ? " on" : ""}" data-act="tix-area" data-area="${a.id}" aria-pressed="${a.id === area.id ? "true" : "false"}">${esc(a.label)}</button>`).join("");
  const rush = bakuRush() ? `<a class="rush" href="#/tixac">Pik saat — xəritəyə baxın</a>` : "";
  const map = S.tixOn
    ? `<iframe title="Waze canlı xəritə" src="${esc(wazeSrc(area))}" loading="lazy" allowfullscreen referrerpolicy="no-referrer-when-downgrade"></iframe>`
    : `<div class="tix-open"><p>Xəritə yalnız açanda yüklənir.</p><button type="button" class="btn" data-act="tix-open">Xəritəni aç</button></div>`;
  const rows = items.length
    ? `<ul class="tix-list">${items.map(a => `<li><a href="${esc(a.sourceUrl || "#")}" ${OUT}><span class="ic" aria-hidden="true">${a.icon}</span><span class="tt">${txt(a.title)}</span><span class="meta">${esc(shownSource(a))} · ${ago(a.publishedAt)}</span></a></li>`).join("")}</ul>`
    : `<p class="empty">Hazırda yol xəbəri görünmür. Xəritə canlıdır.</p>`;
  return `<div class="page-h"><div><h1>Tıxac və yollar</h1><p>Bakı və Abşeronun canlı yol vəziyyəti.</p></div><span class="cnt">${items.length} xəbər</span></div>
    <p class="tix-note">Xəritə Waze-dən açılır, açar tələb etmir. Yol xəbərləri saytdakı mövcud lentlərdən süzülür.</p>
    ${rush}
    <div class="tix-jumps">${jumps}</div>
    <div class="tix-map" id="tix-map">${map}<div class="tix-bar"><a href="${esc(wazeLive(area))}" ${OUT}>Xəritəni tam ekranda aç</a></div></div>
    ${rows}`;
}

function renderView() {
  syncQuery();
  pageMeta();
  const v = $("#view");
  if (S.error && !S.data) { v.innerHTML = `<div class="err" role="alert">Xəbər lenti yüklənə bilmədi. İnternet bağlantınızı yoxlayın. <button class="btn" data-act="retry">Yenidən yoxla</button></div>`; return; }
  if (!S.data) { v.innerHTML = skeleton(); return; }
  const r = route();
  const err = S.error ? `<div class="err" role="status">Son yenilənmə alınmadı. Saxlanmış xəbərlər göstərilir. <button class="btn" data-act="retry">Yenidən yoxla</button></div>` : "";
  const body = r.name === "sources" ? sourcesView() : r.name === "saved" ? savedView() : r.name === "sections" ? sectionsView() : r.name === "videos" ? videosView() : r.name === "traffic" ? trafficView() : S.q ? searchView() : r.name === "section" ? sectionView(r.slug) : homeView();
  v.innerHTML = err + body;
  $("#cta").hidden = r.name !== "home" || !!S.q;
  const tab = r.name === "saved" ? "saved" : r.name === "traffic" ? "traffic" : r.name === "sections" || r.name === "section" ? "sections" : r.name === "home" && !S.q ? "home" : "";
  document.querySelectorAll(".tabbar [data-tab]").forEach(el => el.classList.toggle("on", el.dataset.tab === tab));
  setupMarquees();
}

function sourceLevel(s) {
  const t = new Date(s.okAt || 0).getTime();
  const age = Number.isNaN(t) ? Infinity : Date.now() - t;
  if (!s.error && s.count > 0 && age < 6 * HOUR) return "ok";
  if (s.okAt && age < 36 * HOUR) return "warn";
  return "bad";
}
function sourcesView() {
  const rows = S.sources?.sources;
  if (!rows) return `<div class="page-h"><div><h1>Mənbə vəziyyəti</h1><p>Lentlərin son yoxlanması</p></div></div><p class="empty">Yüklənir…</p>`;
  const label = { ok: "İşləyir", warn: "Zəif", bad: "Xəta" };
  const body = rows.map(s => {
    const lv = sourceLevel(s);
    return `<li class="src-row ${lv}"><span class="src-dot" aria-hidden="true"></span><div><b>${esc(s.name)}</b><div class="muted">${esc(s.url || "")}</div>${s.error ? `<div class="src-err">${esc(s.error)}</div>` : ""}</div><div class="src-meta"><span>${label[lv]}</span><span>${s.count ?? 0} xəbər</span><time>${s.okAt ? ago(s.okAt) : "uğur yoxdur"}</time></div></li>`;
  }).join("");
  return `<div class="page-h"><div><h1>Mənbə vəziyyəti</h1><p>Yaşıl — son saatlarda xəbər gəlib. Sarı — boş və ya köhnəlmiş uğur. Qırmızı — xəta.</p></div><span class="cnt">${rows.length}</span></div><ul class="src-list">${body}</ul>`;
}

function renderFooter() {
  const srcs = [...new Set((S.data?.articles ?? []).map(shownSource))].sort((a, b) => a.localeCompare(b, "az"));
  $("#footer").innerHTML = `<div class="wrap fgrid">
    <div><div class="logo"><i>${STAR}</i><b>8<span>ULDUZ</span></b></div><p style="margin:0">Azərbaycan və dünyadan son xəbərlər — hər 5 dəqiqədən bir avtomatik yenilənən müstəqil xəbər lenti. Başlıq mənbənin öz səhifəsinə açılır.</p></div>
    <div><h4>Bölmələr</h4><div class="fcats">${CATS.map(c => `<a href="#/bolme/${c.slug}">${esc(c.label)}</a>`).join("")}</div></div>
    <div><h4>İzlənilən mənbələr</h4><div class="srcs">${srcs.map(s => `<span>${esc(s)}</span>`).join("")}</div></div>
  </div><div class="copy">© ${new Date().getFullYear()} 8ulduz. Bütün xəbər mətnlərinin hüququ müvafiq mənbələrə aiddir. <a href="#/menbeler">Mənbə vəziyyəti</a></div>`;
}

function savedView() {
  const items = savedList();
  return `<div class="page-h"><div><h1>Seçilmişlər</h1><p>Ulduzla saxladığınız xəbərlər bu cihazda qalır.</p></div><span class="cnt">${items.length}</span></div>` +
    (items.length ? `<div class="grid">${items.map(card).join("")}</div>` : `<p class="empty">Hələ seçilmiş xəbər yoxdur. Kartdakı ulduza basın.</p>`);
}
function sectionsView() {
  const { order, off } = sectionPref();
  const hide = new Set(off);
  const rows = order.map((slug, i) => {
    const c = CATS.find(x => x.slug === slug);
    if (!c) return "";
    const on = !hide.has(slug);
    return `<li data-cat="${esc(slug)}"><button type="button" data-act="sec-up" data-slug="${esc(slug)}" ${i === 0 ? "disabled" : ""} aria-label="Yuxarı">↑</button><button type="button" data-act="sec-down" data-slug="${esc(slug)}" ${i === order.length - 1 ? "disabled" : ""} aria-label="Aşağı">↓</button><button type="button" class="chk${on ? " on" : ""}" data-act="sec-toggle" data-slug="${esc(slug)}" aria-pressed="${on ? "true" : "false"}">${on ? "✓" : ""}</button><a href="#/bolme/${esc(slug)}"><i class="cdot"></i>${esc(c.label)}</a><span>${esc(c.description)}</span></li>`;
  }).join("");
  return `<div class="page-h"><div><h1>Mənim bölmələrim</h1><p>İşarəni götürün və ya sıranı dəyişin. Baş səhifə bunu yadda saxlayır.</p></div></div><ul class="mine">${rows}</ul>`;
}

function onClick(e) {
  const t = e.target.closest("[data-id],[data-act],[data-lang],[data-club],[data-city],[data-fx],[data-yt]");
  if (!e.target.closest(".altpop")) document.querySelectorAll("details.altpop[open]").forEach(d => { d.open = false; });
  if (!e.target.closest(".nav-more")) document.querySelectorAll(".nav-more[open]").forEach(d => { d.open = false; });
  if (!t) {
    let dirty = false;
    if (S.wxOpen && !e.target.closest(".wx")) { S.wxOpen = false; dirty = true; }
    if (S.prayOpen && !e.target.closest(".pray-wrap")) { S.prayOpen = false; dirty = true; }
    if (S.fxOpen && !e.target.closest(".fx-pop") && !e.target.closest("[data-fx]")) { S.fxOpen = false; dirty = true; }
    if (dirty) { renderTopbar(); renderMarkets(); }
    return;
  }
  if (t.dataset.act === "star") {
    e.preventDefault();
    e.stopPropagation();
    const id = t.dataset.save;
    const a = byId.get(id) || savedList().find(x => x.id === id);
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
  if (t.dataset.yt) {
    const box = t.querySelector(".thumb");
    if (box && !box.querySelector("iframe")) box.innerHTML = `<iframe src="https://www.youtube-nocookie.com/embed/${encodeURIComponent(t.dataset.yt)}?autoplay=1" allow="autoplay; encrypted-media; picture-in-picture" allowfullscreen title="Video"></iframe>`;
    return;
  }
  if (t.dataset.fx && !e.target.closest(".fx-pop")) { S.fxFrom = t.dataset.fx; S.fxTo = "AZN"; S.fxOpen = true; renderMarkets(); return; }
  if (t.dataset.lang !== undefined) { S.lang = t.dataset.lang || null; S.shown = PAGE; renderLangs(); renderView(); return; }
  if (t.dataset.club !== undefined) { S.club = t.dataset.club || null; S.shown = PAGE; renderView(); return; }
  if (t.dataset.city) { S.wxSel = t.dataset.city; renderTopbar(); return; }
  const act = t.dataset.act;
  if (act === "wx") { S.wxOpen = !S.wxOpen; S.wxSel = null; renderTopbar(); if (S.wxOpen) loadAllWeather(); }
  else if (act === "wx-close") { S.wxOpen = false; renderTopbar(); }
  else if (act === "wx-back") { S.wxSel = null; renderTopbar(); }
  else if (act === "more") { S.shown += PAGE; renderView(); }
  else if (act === "find") { const q = $("#q"); q?.focus(); q?.scrollIntoView({ block: "center" }); }
  else if (act === "tix-open") { S.tixOn = true; renderView(); }
  else if (act === "tix-area") {
    const id = t.dataset.area || "merkez";
    if (id === S.tixArea && S.tixOn) return;
    S.tixArea = id;
    renderView();
  }
  else if (act === "pray") { S.prayOpen = !S.prayOpen; renderTopbar(); }
  else if (act === "fx-close") { S.fxOpen = false; renderMarkets(); }
  else if (act === "theme" || act === "fs-down" || act === "fs-up") setPref(act);
  else if (act === "notify") armNotify();
  else if (act === "retry") { loadNews(); loadStatus(); }
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
function applyPrefs() {
  const theme = storage.getItem(THEME_KEY) === "light" ? "light" : "dark";
  document.documentElement.dataset.theme = theme;
  let fs = storage.getItem(FS_KEY);
  if (fs !== "0" && fs !== "1" && fs !== "2") fs = "0";
  document.documentElement.dataset.fs = fs;
  const meta = document.querySelector('meta[name="theme-color"]');
  if (meta) meta.content = theme === "light" ? "#f3f6fb" : "#0a1120";
}
function setPref(act) {
  if (act === "theme") {
    const next = document.documentElement.dataset.theme === "light" ? "dark" : "light";
    storage.setItem(THEME_KEY, next);
  } else {
    const n = Math.max(0, Math.min(2, Number(document.documentElement.dataset.fs || "0") + (act === "fs-up" ? 1 : -1)));
    storage.setItem(FS_KEY, String(n));
  }
  applyPrefs();
  renderTopbar();
  setupMarquees();
  fitNav();
}
function enableAnalytics() {
  const code = String(window.SITE_CONFIG?.goatcounter || "").trim();
  if (!code) return;
  const s = document.createElement("script");
  s.async = true;
  s.src = "https://gc.zgo.at/count.js";
  s.dataset.goatcounter = `https://${code}.goatcounter.com/count`;
  document.head.appendChild(s);
}

/* Sakit olanda bir sətir/kart yuxarı keçir (~4s). Kursor, fokus və gizli vərəqədə dayanır. */
const STEP_MS = 4000;
const LEAVE_MS = 2000;
const WHEEL_MS = 3000;
const TOUCH_MS = 5000;
function reducedMotion() { return matchMedia("(prefers-reduced-motion: reduce)").matches; }
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
  if (reducedMotion() || !el.classList.contains("vmarquee")) return;
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
  if (Math.abs(dist) < 1 || reducedMotion()) {
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
function nudgeStep(el, dir) {
  const pos = rowStops(el);
  const y = el.scrollTop;
  const target = dir > 0 ? (pos.find(p => p > y + 4) ?? pos[0]) : ([...pos].reverse().find(p => p < y - 4) ?? pos[0]);
  el._holdUntil = Date.now() + LEAVE_MS;
  animateTo(el, target);
}
function stopStep(el, snap) {
  cancelMotion(el);
  if (!snap) return;
  const { best, bestD } = nearestStop(el);
  if (bestD > 1) el.scrollTop = best;
}
function setupMarquees() {
  document.querySelectorAll("[data-marquee]").forEach(el => {
    cancelMotion(el);
    el._mouse = false;
    el._key = false;
    el.style.height = "";
    el.classList.remove("vmarquee");
    for (const item of el.children) item.style.height = "";
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
    const wrap = ensureWrap(el);
    let nav = wrap.querySelector(".step-nav");
    if (!nav) {
      nav = document.createElement("div");
      nav.className = "step-nav";
      nav.innerHTML = `<button type="button" data-step="-1" aria-label="Əvvəlki sətir">⌃</button><button type="button" data-step="1" aria-label="Növbəti sətir">⌄</button>`;
      wrap.appendChild(nav);
    }
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
document.addEventListener("pointerdown", (e) => {
  if (e.pointerType !== "touch") return;
  const el = marqueeOf(e.target);
  if (!el) return;
  stopStep(el, false);
  el._holdUntil = Date.now() + TOUCH_MS;
  scheduleStep(el, TOUCH_MS);
}, true);
document.addEventListener("wheel", (e) => {
  const el = marqueeOf(e.target);
  if (!el) return;
  stopStep(el, false);
  el._holdUntil = Date.now() + WHEEL_MS;
  scheduleStep(el, WHEEL_MS);
}, { passive: true, capture: true });
document.addEventListener("click", (e) => {
  const btn = e.target.closest?.("[data-step]");
  if (!btn) return;
  const el = marqueeOf(btn);
  if (!el) return;
  e.preventDefault();
  e.stopPropagation();
  nudgeStep(el, Number(btn.dataset.step));
}, true);
document.addEventListener("visibilitychange", () => {
  document.querySelectorAll("[data-marquee].vmarquee").forEach(el => {
    cancelMotion(el);
    if (!document.hidden) scheduleStep(el, LEAVE_MS);
  });
});
let marqueeResizeT = 0;
addEventListener("resize", () => {
  clearTimeout(marqueeResizeT);
  marqueeResizeT = setTimeout(() => { setupMarquees(); syncLangStick(); fitNav(); }, 150);
});

function render() { renderTopbar(); renderNav(); renderTicker(); renderLangs(); renderView(); renderFooter(); syncTixDot(); }

/* ---------------------------------------------------------------- start */
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
    if (r.ok) { S.video = await r.json(); if (route().name === "home" || route().name === "videos") renderView(); }
  } catch {}
}
async function loadFootball() {
  try {
    const r = await fetch(freshUrl("data/football.json"), { cache: "no-store" });
    if (r.ok) { S.football = await r.json(); if (route().name === "home") renderView(); }
  } catch {}
}
async function loadPrayer(city) {
  const name = CITIES.some(c => c[0] === city) ? city : savedPrayCity();
  const c = CITIES.find(x => x[0] === name) || CITIES[0];
  const token = (S.prayToken = (S.prayToken || 0) + 1);
  try {
    const u = `https://api.aladhan.com/v1/timings?latitude=${c[1]}&longitude=${c[2]}&method=13`;
    const d = await (await fetch(u)).json();
    if (token !== S.prayToken || !d?.data?.timings) return;
    S.pray = { city: c[0], timings: d.data.timings, hijri: d.data.date?.hijri };
    renderTopbar();
  } catch {}
}
async function loadWarnings() {
  const c = CITIES[0];
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
    if (route().name === "home") renderView();
  } catch {}
}
async function loadSocial() {
  try {
    const r = await fetch(freshUrl("data/social.json"), { cache: "no-store" });
    if (r.ok) { S.social = await r.json(); render(); }
  } catch {}
}
async function loadSources() {
  try {
    const r = await fetch(freshUrl("data/sources.json"), { cache: "no-store" });
    if (r.ok) S.sources = await r.json();
  } catch {}
  if (route().name === "sources") renderView();
}
async function loadStatus() {
  try {
    const r = await fetch(freshUrl("data/status.json"), { cache: "no-store" });
    if (r.ok) S.status = await r.json();
  } catch {}
  renderTopbar();
}
applyPrefs();
enableAnalytics();
if ("serviceWorker" in navigator) {
  navigator.serviceWorker.register("./sw.js").then((reg) => {
    if (!navigator.serviceWorker.controller) return;
    reg.addEventListener("updatefound", () => {
      const nw = reg.installing;
      if (!nw) return;
      nw.addEventListener("statechange", () => {
        if (nw.state === "activated") location.reload();
      });
    });
  }).catch(() => {});
}
document.addEventListener("toggle", (e) => {
  const d = e.target;
  if (!d.classList?.contains("altpop") || !d.open) return;
  document.querySelectorAll("details.altpop[open]").forEach(x => { if (x !== d) x.open = false; });
}, true);
shell(); render();
loadNews(); loadMarkets(); loadSocial(); loadStatus(); loadSources(); loadWeather(); loadVideo(); loadFootball(); loadPrayer(savedPrayCity()); loadWarnings(); loadAds();
setInterval(loadNews, POLL_MS);
setInterval(loadStatus, POLL_MS);
setInterval(loadSocial, 5 * 60e3);
setInterval(loadMarkets, 5 * 60e3);
setInterval(() => { loadSources(); loadVideo(); loadFootball(); }, 5 * 60e3);
setInterval(() => { if (adSlots().length > 1 && route().name === "home") { const el = document.querySelector("main .ad"); if (el) el.outerHTML = adHtml(); } }, 30e3);
document.addEventListener("change", (e) => {
  const sel = e.target.closest?.("select.pray-city");
  if (!sel) return;
  const city = sel.value;
  if (!CITIES.some(c => c[0] === city)) return;
  try { storage.setItem(PRAY_CITY_KEY, city); } catch {}
  S.prayOpen = true;
  loadPrayer(city);
});
document.addEventListener("keydown", (e) => {
  if (e.key !== "Enter" && e.key !== " ") return;
  const star = e.target.closest?.("[data-act=star]");
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
