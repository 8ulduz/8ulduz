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
  { name: "president.az", url: "https://www.president.az" },
  { name: "firstlady.az", url: "https://www.firstlady.az" },
  { name: "X — @presidentaz", url: "https://x.com/presidentaz" },
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
const POLL_MS = 60e3;     // xəbər lentini yoxlama intervalı (ETag ilə — dəyişməyibsə 304)
const PAGE = 48;          // bölmə səhifəsində bir dəfəyə göstərilən xəbər

/* ---------------------------------------------------------------- köməkçilər */
const $ = (s, r = document) => r.querySelector(s);
const ESC = { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" };
const _dec = document.createElement("textarea");
function decode(s) { if (!s || s.indexOf("&") < 0) return s || ""; _dec.innerHTML = s; return _dec.value; }
function esc(s) { return String(s ?? "").replace(/[&<>"']/g, c => ESC[c]); }
const txt = s => esc(decode(s));
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
const isFresh = a => { const t = new Date(a.publishedAt).getTime(); return !Number.isNaN(t) && Date.now() - t < HOUR; };
const DATELINE = /^\s*[\p{Lu}][\p{L}\s-]{1,30}[.,]\s*\d{1,2}\s+\p{L}+[.,]?\s*(?:\d{4}[.,]?\s*)?(?:AZƏRTAC|AZERTAC|APA|Report|Trend)?[.,:—-]*\s*/u;
const clean = s => decode(s || "").replace(DATELINE, "").trim();
function langOf(a) { if (a.lang) return a.lang; const s = a.title + " " + a.summary; return /[а-яА-Я]/.test(s) ? "ru" : /[əƏ]/.test(s) ? "az" : /[ığİ]/.test(s) ? "tr" : "az"; }
const isFirstLady = a => { const s = (a.title + " " + a.summary).toLowerCase(); return s.includes("mehriban") || s.includes("birinci xanım") || s.includes("birinci xanim"); };
const prezSort = list => [...list].sort((x, y) => Number(isFirstLady(x)) - Number(isFirstLady(y)));
const byDate = list => [...list].sort((x, y) => y.publishedAt.localeCompare(x.publishedAt));
const lc = s => (s || "").toLocaleLowerCase("az");
const STAR = `<svg viewBox="0 0 32 32" width="18" height="18" aria-hidden="true"><g fill="currentColor"><rect x="9.5" y="9.5" width="13" height="13" rx="2"/><rect x="9.5" y="9.5" width="13" height="13" rx="2" transform="rotate(45 16 16)"/></g></svg>`;

function img(a, cls = "") {
  const ph = `<svg class="ph" viewBox="0 0 32 32" aria-hidden="true"><g fill="currentColor"><rect x="9.5" y="9.5" width="13" height="13" rx="2"/><rect x="9.5" y="9.5" width="13" height="13" rx="2" transform="rotate(45 16 16)"/></g></svg>`;
  const src = a.imageUrl ? `<img src="${esc(a.imageUrl)}" alt="" loading="lazy" decoding="async" referrerpolicy="no-referrer" onerror="imgFail(this)">` : "";
  return `<div class="img ${cls}">${ph}${src}</div>`;
}
function badges(a, withCat = true) {
  return `<div class="badges">${withCat ? `<span class="bd">${esc(catLabel(a.category))}</span>` : ""}${a.video ? `<span class="bd red">▶ Video</span>` : ""}${a.lang ? `<span class="bd out">${esc(LANG_BADGE[a.lang] ?? a.lang.toUpperCase())}</span>` : ""}${isFresh(a) ? `<span class="bd red">Son dəqiqə</span>` : ""}</div>`;
}
const meta = a => `<div class="meta"><span class="src">${esc(a.source)}${a.author ? `<span class="muted"> · ${txt(a.author)}</span>` : ""}</span><time datetime="${esc(a.publishedAt)}">${ago(a.publishedAt)}</time></div>`;
const card = a => `<button class="card${a.imageUrl ? "" : " noimg"}" data-id="${esc(a.id)}">${img(a)}<div class="b">${badges(a)}<h3>${txt(a.title)}</h3><p>${esc(clean(a.summary))}</p>${meta(a)}</div></button>`;

// Şəkil yüklənməsə (hotlink qadağası və s.) kart şəkilsiz rejimə keçir
window.imgFail = el => { const c = el.closest(".card"); if (c) c.classList.add("noimg"); el.remove(); };

/* ---------------------------------------------------------------- vəziyyət */
const S = { data: null, error: null, lastSync: null, lang: null, club: null, q: "", shown: PAGE, etag: null, markets: null, wx: null, wxAll: null, wxSel: null, wxOpen: false };
const byId = new Map();

/* ---------------------------------------------------------------- məlumat */
async function loadNews() {
  try {
    const r = await fetch("data/news.json", { cache: "no-cache" });
    if (!r.ok) throw new Error(`HTTP ${r.status}`);
    const tag = r.headers.get("etag") || r.headers.get("last-modified");
    S.lastSync = new Date(); S.error = null;
    if (tag && tag === S.etag && S.data) { renderTopbar(); return; }
    S.etag = tag;
    const d = await r.json();
    if (S.data && S.data.updatedAt === d.updatedAt) { renderTopbar(); return; }
    S.data = d; byId.clear(); for (const a of d.articles) byId.set(a.id, a);
    render();
  } catch (e) { S.error = String(e); if (!S.data) render(); else renderTopbar(); }
}

async function loadMarkets() {
  // Əsas mənbə: updater.py-nin yaratdığı data/markets.json (AMB, Yahoo Finance, gold-api və s.)
  try {
    const r = await fetch("data/markets.json", { cache: "no-cache" });
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
  const h = decodeURIComponent(location.hash.replace(/^#/, "")) || "/";
  const m = h.match(/^\/bolme\/([^/?]+)/); if (m) return { name: "section", slug: m[1] };
  const q = h.match(/^\/axtar(?:\?q=(.*))?$/); if (q) return { name: "search", q: q[1] || "" };
  return { name: "home" };
}

/* ---------------------------------------------------------------- render */
function shell() {
  $("#app").innerHTML = `
  <div class="topbar"><div class="wrap" id="topbar"></div></div>
  <header class="site"><div class="wrap hrow">
    <a class="logo" href="#/"><i>${STAR}</i><b>8<span>ULDUZ</span></b></a>
    <nav class="main" id="nav" aria-label="Bölmələr"></nav>
    <label class="search"><span class="sr" hidden>Axtar</span>
      <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><circle cx="11" cy="11" r="7"/><path d="m20 20-3.5-3.5"/></svg>
      <input id="q" type="search" placeholder="Xəbər axtar…" autocomplete="off" aria-label="Xəbər axtar"></label>
  </div></header>
  <div id="ticker"></div>
  <div class="markets" id="markets" hidden><div class="wrap"><div class="mk-grid" id="mk"></div></div></div>
  <div class="filters"><div class="wrap" id="langs"></div></div>
  <main><div class="wrap" id="view"></div></main>
  <div class="wrap"><section class="cta" id="cta"><span class="ic">📬</span><div><h2>8ulduz kanalına qoşulun</h2><p>Ən vacib xəbərlər dərhal Telegram kanalımızda — vaxt itirmədən xəbərdar olun.</p></div><a class="btn" href="https://t.me/" target="_blank" rel="noopener noreferrer">Kanala keç →</a></section></div>
  <footer id="footer"></footer>
  <dialog class="modal" id="modal"></dialog>
  <button class="totop" id="totop" aria-label="Yuxarı qayıt">↑</button>`;
  const q = $("#q");
  q.addEventListener("input", () => {
    S.q = q.value.trim(); S.shown = PAGE;
    const want = S.q ? `#/axtar?q=${encodeURIComponent(S.q)}` : "#/";
    if (location.hash !== want) history.replaceState(null, "", want);
    renderView();
  });
  document.addEventListener("click", onClick);
  window.addEventListener("hashchange", () => { S.shown = PAGE; S.club = null; const r = route(); if (r.name === "search") { S.q = r.q; q.value = r.q; } render(); window.scrollTo(0, 0); });
  window.addEventListener("scroll", () => $("#totop").classList.toggle("show", scrollY > 600), { passive: true });
  $("#totop").onclick = () => scrollTo({ top: 0, behavior: "smooth" });
  $("#modal").addEventListener("click", e => { if (e.target.id === "modal") e.target.close(); });
  const r = route(); if (r.name === "search") { S.q = r.q; q.value = r.q; }
}

function renderTopbar() {
  const w = S.wx, upd = S.data?.updatedAt;
  let pop = "";
  if (S.wxOpen) {
    const sel = S.wxSel && (S.wxAll || []).find(x => x.city === S.wxSel);
    pop = `<div class="wx-pop" role="dialog" aria-label="Bölgələr üzrə hava">` + (sel
      ? `<button class="muted" data-act="wx-back" style="font-size:12px;font-weight:700;color:var(--primary)">← Bölgələrə qayıt</button>
         <div style="display:flex;align-items:center;gap:10px;margin-top:8px"><span style="font-size:34px">${sel.icon}</span><div><b style="font-size:17px">${esc(sel.city)}</b><div class="muted">${sel.label}</div></div><b style="margin-left:auto;font-size:28px">${sel.temp}°</b></div>
         <div class="wx-det">${[["Hiss olunur", `${sel.feels}°`], ["Rütubət", `%${sel.humidity}`], ["Külək", `${sel.wind} km/s`], ["Təzyiq", `${sel.pressure} hPa`], ["Yağıntı", `${sel.precip} mm`]].map(([k, v]) => `<div><small>${k}</small><b>${v}</b></div>`).join("")}</div>`
      : `<div class="wx-head"><span>Bölgələr üzrə hava</span><button data-act="wx-close" aria-label="Bağla">✕</button></div>` +
        (!S.wxAll ? `<div class="empty" style="padding:24px 0">Yüklənir…</div>` :
          `<div class="wx-grid">${S.wxAll.map(c => `<button class="wx-city" data-city="${esc(c.city)}"><span>${c.icon} ${esc(c.city)}</span><b>${c.temp}°</b></button>`).join("")}</div>`)) + `</div>`;
  }
  $("#topbar").innerHTML = `<span>${today()}</span>
    <div class="wx ${S.wxOpen ? "open" : ""}"><button class="wx-btn" data-act="wx" title="Azərbaycanın bölgələri üzrə hava"><span>${w ? w.icon : "🌡️"}</span><span>Bakı</span><b>${w ? `${w.temp}°` : "—"}</b><span style="opacity:.6">▾</span></button>${pop}</div>
    <span class="sp sync">${S.lastSync ? `<span class="dot"></span>Son yenilənmə: ${S.lastSync.toLocaleTimeString("az-AZ")}` : ""}</span>
    ${upd ? `<span><span class="dot live" style="background:#34d399"></span>Yeniləndi: ${ago(upd)}</span>` : ""}`;
}

function renderNav() {
  const r = route(), cur = r.name === "section" ? r.slug : r.name === "home" ? "/" : "";
  $("#nav").innerHTML = `<a href="#/" class="${cur === "/" ? "on" : ""}">Baş səhifə</a>` +
    CATS.map(c => `<a href="#/bolme/${c.slug}" class="${cur === c.slug ? "on" : ""}">${esc(c.label)}</a>`).join("");
  $("#nav .on")?.scrollIntoView({ block: "nearest", inline: "nearest" });
}

function renderTicker() {
  const list = byDate((S.data?.articles ?? []).filter(a => (a.lang ?? "az") === "az")).slice(0, 12);
  if (!list.length) { $("#ticker").innerHTML = ""; return; }
  const items = [...list, ...list].map(a => `<button data-id="${esc(a.id)}">${txt(a.title)}</button>`).join("");
  $("#ticker").innerHTML = `<div class="ticker"><div class="lbl">⚡ Son dəqiqə</div><div class="run"><div class="track">${items}</div></div></div>`;
}

function fmt(v, dec) { return Number(v).toLocaleString("en-US", { minimumFractionDigits: Math.min(dec, 2), maximumFractionDigits: dec }); }
function renderMarkets() {
  const m = S.markets; if (!m?.length) return;
  $("#markets").hidden = false;
  $("#mk").innerHTML = m.map(i => {
    const has = i.changePct != null && i.change != null;
    const cls = !has ? "flat" : i.changePct > 0 ? "up" : i.changePct < 0 ? "down" : "flat";
    const chg = has ? `<span>${i.changePct > 0 ? "↑" : i.changePct < 0 ? "↓" : "•"} %${Math.abs(i.changePct).toFixed(2)}</span><span>${i.change > 0 ? "+" : ""}${fmt(i.change, i.dec)}</span>`
      : `<span>${i.unit === "AZN" ? "məzənnə" : "qiymət"}</span><span>${i.unit === "AZN" ? "AZN" : "$"}</span>`;
    const title = [i.src && `Mənbə: ${i.src}`, i.asOf && `Tarix: ${i.asOf}`, i.stale && "son məlum qiymət"].filter(Boolean).join(" · ");
    return `<div class="mk" title="${esc(title)}"><div class="n">${esc(i.label)}</div><div class="v">${fmt(i.value, i.dec)}<small>${i.unit === "AZN" ? "₼" : "$"}</small></div><div class="c ${cls}">${chg}</div></div>`;
  }).join("");
}

function renderLangs() {
  $("#langs").innerHTML = `<button class="pill ${S.lang === null ? "on" : ""}" data-lang="">Hamısı</button>` +
    LANGS.map(l => `<button class="pill ${S.lang === l.code ? "on" : ""}" data-lang="${l.code}">${l.label}</button>`).join("");
}

function filtered(list) { return S.lang ? list.filter(a => langOf(a) === S.lang) : list; }

function prezBlock(list) {
  if (!list.length) return "";
  return `<section class="prez"><div class="prez-h"><h2>${STAR}<a href="#/bolme/prezident">Zuğulba Xronikası</a></h2>
    <span class="cnt muted" style="font-size:12px;font-weight:600">${list.length} xəbər</span>
    <span class="links">${PREZ_LINKS.map(l => `<a href="${l.url}" target="_blank" rel="noopener noreferrer">${l.name}</a>`).join("")}</span>
    <a class="btn" href="#/bolme/prezident">Hamısı →</a></div>
    <div class="prez-grid">${prezSort(list).slice(0, 8).map(a => `<button class="pcard" data-id="${esc(a.id)}">${isFirstLady(a) ? `<span class="tag">Birinci xanım</span>` : ""}<span class="t">${txt(a.title)}</span><span class="meta"><span class="src">${esc(a.source)}</span><time>${ago(a.publishedAt)}</time></span></button>`).join("")}</div></section>`;
}

function heroBlock(list) {
  if (!list.length) return "";
  const main = list.find(a => a.imageUrl && (a.lang ?? "az") === "az") ?? list.find(a => a.imageUrl) ?? list[0];
  const side = list.filter(a => a !== main).slice(0, 4);
  return `<section class="hero">
    <button class="hero-main" data-id="${esc(main.id)}">${img(main)}<div class="body">
      <div class="badges"><span class="bd gold">${esc(catLabel(main.category))}</span>${isFresh(main) ? `<span class="bd red">Son dəqiqə</span>` : ""}</div>
      <h1>${txt(main.title)}</h1><p>${esc(clean(main.summary))}</p>
      <div class="meta"><span class="src">${esc(main.source)}</span><time>${ago(main.publishedAt)}</time></div></div></button>
    <div class="hero-side">${side.map(a => `<button class="row-card" data-id="${esc(a.id)}">${img(a)}<div class="x"><span class="tag">${esc(catLabel(a.category))}</span><span class="t">${txt(a.title)}</span><span class="meta"><span class="src">${esc(a.source)}</span><time>${ago(a.publishedAt)}</time></span></div></button>`).join("")}</div>
  </section>`;
}

function videoBlock(list) {
  if (!list.length) return "";
  return `<section><div class="sec-h"><h2>Video xəbərlər</h2><span class="cnt">${list.length} video keçid</span><a class="more" href="#/bolme/video">Hamısı →</a></div>
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
  return `<section class="hero"><div class="skel" style="height:340px"></div><div class="hero-side">${"<div class='skel' style='height:78px'></div>".repeat(4)}</div></section>
    <section><div class="grid">${"<div class='skel' style='height:250px'></div>".repeat(4)}</div></section>`;
}

function homeView() {
  const all = S.data.articles, m = filtered(all);
  const prez = m.filter(a => a.category === "prezident" && Date.now() - new Date(a.publishedAt).getTime() < DAY).slice(0, 20);
  const vids = byDate(m.filter(a => a.video));
  const used = new Set();
  const hero = byDate(m).slice(0, 5); hero.forEach(a => used.add(a.id));
  const secs = CATS.filter(c => !["video", "prezident", "sondeqiqe"].includes(c.slug))
    .map(c => catSection(c, byDate(m.filter(a => a.category === c.slug && !used.has(a.id))))).join("");
  return prezBlock(prez) + `<section class="ad" aria-label="Reklam yeri">Reklam yeri</section>` + heroBlock(byDate(m)) + videoBlock(vids) + secs;
}

function listPage(title, desc, list, extra = "") {
  const shown = list.slice(0, S.shown);
  return `<div class="page-h"><div><h1>${esc(title)}</h1><p>${esc(desc)}</p></div><span class="cnt">${list.length} xəbər</span></div>${extra}` +
    (list.length ? `<div class="grid">${shown.map(card).join("")}</div>${list.length > shown.length ? `<button class="loadmore" data-act="more">Daha çox (${list.length - shown.length})</button>` : ""}`
      : `<p class="empty">Bu bölmədə hələ xəbər yoxdur — növbəti yenilənmədə əlavə olunacaq.</p>`);
}

function sectionView(slug) {
  const c = CATS.find(x => x.slug === slug);
  if (!c) return `<div class="empty"><h1 style="color:var(--fg)">Bölmə tapılmadı</h1><p>Axtardığınız bölmə mövcud deyil.</p><a href="#/" style="color:var(--primary);font-weight:700">← Baş səhifəyə qayıt</a></div>`;
  const d = S.data.articles;
  let list = slug === "video" ? d.filter(a => a.video) : slug === "sondeqiqe" ? d.filter(isFresh) : d.filter(a => a.category === slug);
  list = byDate(list);
  if (slug === "prezident") list = prezSort(list);
  let extra = "";
  if (slug === "idman") {
    if (S.club) { const keys = CLUBS.find(k => k[0] === S.club)?.[1] ?? []; list = list.filter(a => { const s = lc(a.title + " " + a.summary); return keys.some(k => s.includes(k)); }); }
    extra = `<div class="chips"><button class="pill ${S.club === null ? "on" : ""}" data-club="">Bütün idman</button>${CLUBS.map(([n]) => `<button class="pill ${S.club === n ? "on" : ""}" data-club="${esc(n)}">${esc(n)}</button>`).join("")}</div>`;
  }
  if (slug === "prezident") extra = `<div class="chips">${PREZ_LINKS.map(l => `<a class="pill" href="${l.url}" target="_blank" rel="noopener noreferrer">${l.name} ↗</a>`).join("")}</div>`;
  return listPage(c.label, c.description, filtered(list), extra);
}

function searchView() {
  const words = lc(S.q).split(/\s+/).filter(Boolean);
  const list = byDate(filtered(S.data.articles.filter(a => { const s = lc(decode(a.title + " " + a.summary + " " + a.source)); return words.every(w => s.includes(w)); })));
  return listPage(`Axtarış: “${S.q}”`, "Başlıq, xülasə və mənbə adına görə", list);
}

function renderView() {
  const v = $("#view");
  if (S.error && !S.data) { v.innerHTML = `<div class="err">Xəbər lenti yüklənə bilmədi: ${esc(S.error)}</div>`; return; }
  if (!S.data) { v.innerHTML = skeleton(); return; }
  const r = route();
  const err = S.error ? `<div class="err">Xəbər lenti yüklənə bilmədi: ${esc(S.error)}</div>` : "";
  v.innerHTML = err + (S.q ? searchView() : r.name === "section" ? sectionView(r.slug) : homeView());
  $("#cta").hidden = r.name !== "home" || !!S.q;
}

function renderFooter() {
  const srcs = [...new Set((S.data?.articles ?? []).map(a => a.source))].sort((a, b) => a.localeCompare(b, "az"));
  $("#footer").innerHTML = `<div class="wrap fgrid">
    <div><div class="logo"><i>${STAR}</i><b>8<span>ULDUZ</span></b></div><p style="margin:0">Azərbaycan və dünyadan son xəbərlər — hər 5 dəqiqədən bir avtomatik yenilənən müstəqil xəbər lenti. Xəbərlər qısa xülasə və mənbə keçidi ilə təqdim olunur.</p></div>
    <div><h4>Bölmələr</h4><div class="fcats">${CATS.map(c => `<a href="#/bolme/${c.slug}">${esc(c.label)}</a>`).join("")}</div></div>
    <div><h4>İzlənilən mənbələr</h4><div class="srcs">${srcs.map(s => `<span>${esc(s)}</span>`).join("")}</div></div>
  </div><div class="copy">© ${new Date().getFullYear()} 8ulduz. Bütün xəbər mətnlərinin hüququ müvafiq mənbələrə aiddir.</div>`;
}

function openModal(a) {
  const d = $("#modal");
  d.innerHTML = `<button class="x" data-act="close" aria-label="Bağla">✕</button>${a.imageUrl ? img(a) : ""}<div class="b">
    <div class="badges"><span class="bd gold">${esc(catLabel(a.category))}</span>${isFresh(a) ? `<span class="bd red">Son dəqiqə</span>` : ""}${a.video ? `<span class="bd red">▶ Video</span>` : ""}</div>
    <h2>${txt(a.title)}</h2>
    <div class="m"><b>${esc(a.source)}</b>${a.author ? `<span>•</span><span>${txt(a.author)}</span>` : ""}<span>•</span><span>${ago(a.publishedAt)}</span><span>•</span><span>${fullDate(a.publishedAt)}</span></div>
    <p>${esc(clean(a.summary))}</p>
    <div class="note">Bu xəbər avtomatik toplanmış qısa xülasədir. Mətnin tam versiyası mənbə saytına aiddir.</div>
    <div class="acts"><a class="btn" href="${esc(a.sourceUrl)}" target="_blank" rel="noopener noreferrer">Mənbədə oxu ↗</a>
    ${navigator.share ? `<button class="btn ghost" data-act="share">Paylaş</button>` : `<button class="btn ghost" data-act="copy">Linki kopyala</button>`}</div></div>`;
  d._a = a;
  if (!d.open) d.showModal();
}

function onClick(e) {
  const t = e.target.closest("[data-id],[data-act],[data-lang],[data-club],[data-city]");
  if (!t) { if (S.wxOpen && !e.target.closest(".wx")) { S.wxOpen = false; renderTopbar(); } return; }
  if (t.dataset.id && t.tagName !== "A") { const a = byId.get(t.dataset.id); if (a) openModal(a); return; }
  if (t.dataset.lang !== undefined) { S.lang = t.dataset.lang || null; S.shown = PAGE; renderLangs(); renderView(); return; }
  if (t.dataset.club !== undefined) { S.club = t.dataset.club || null; S.shown = PAGE; renderView(); return; }
  if (t.dataset.city) { S.wxSel = t.dataset.city; renderTopbar(); return; }
  const act = t.dataset.act;
  if (act === "wx") { S.wxOpen = !S.wxOpen; S.wxSel = null; renderTopbar(); if (S.wxOpen) loadAllWeather(); }
  else if (act === "wx-close") { S.wxOpen = false; renderTopbar(); }
  else if (act === "wx-back") { S.wxSel = null; renderTopbar(); }
  else if (act === "more") { S.shown += PAGE; renderView(); }
  else if (act === "close") $("#modal").close();
  else if (act === "share") { const a = $("#modal")._a; navigator.share({ title: decode(a.title), url: a.sourceUrl }).catch(() => {}); }
  else if (act === "copy") { const a = $("#modal")._a; navigator.clipboard?.writeText(a.sourceUrl); t.textContent = "Kopyalandı ✓"; }
}

function render() { renderTopbar(); renderNav(); renderTicker(); renderLangs(); renderView(); renderFooter(); }

/* ---------------------------------------------------------------- start */
shell(); render();
loadNews(); loadMarkets(); loadWeather();
setInterval(loadNews, POLL_MS);
setInterval(loadMarkets, 5 * 60e3);
setInterval(loadWeather, 30 * 60e3);
setInterval(() => { if (S.data) renderTopbar(); }, 30e3);
