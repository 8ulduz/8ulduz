// Videolent: şaquli, tam ekran, barmaqla sürüşdürülən video lenti (sahib, 2026-11-19: «tiktok stilini düzəlt.
// videoların bəzilərinə yazı tərcümə ehtiyac olmaya bilər… gündə 40»). Tənbəl modul: yalnız «Videolent» basılanda
// yüklənir, ilk açılışa heç nə gətirmir.
//
// Videolar: data/reels.json (X-in yazısız videoları, yeniləyici oz_x.reels + content_policy.enforce ilə yazır) və lentdəki
// X videolu öz xəbərlərimiz (a.xv). X videonu mənbə ünvanı göndərən sorğuya vermir (403): lent referrer göndərməyən
// srcdoc çərçivəsinin içində qurulur, video elementlərini bu modul (ana səhifənin kodu) yaradır — çərçivədə skript yoxdur.
// Eyni anda bir video yüklənir və oynayır; poster yalnız yaxındakı slaydlara qoyulur (internet paketi və batareya).

const FILE = new URL("../data/reels.json", import.meta.url).href;
// Hər videonun üstündə «8ulduz.az» yazısı (sahib 2026-11-20: «bütün videoların üstündə başda 8ulduz yazısı … basanda sayt açılsın»;
// 2026-11-22: «videolarda başda 8ulduz.az yazılsın»): basanda lent bağlanır və oxucu sayta qayıdır — ✕ ilə eyni. Şəkil deyil, yazı:
// əlavə sorğu yoxdur, ünvan oxunur.
const MP4 = /^https:\/\/video\.twimg\.com\/[\w/.-]+\.mp4(\?[\w=&.-]*)?$/;
const esc = s => String(s ?? "").replace(/[&<>"']/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[c]);
const plain = s => { const t = document.createElement("textarea"); t.innerHTML = String(s ?? ""); return t.value; };
const px = (u, w) => /^https:\/\/pbs\.twimg\.com\//.test(u || "") ? `https://wsrv.nl/?url=${encodeURIComponent(u)}&w=${w}&we&output=webp&q=70` : "";
const SOUND_KEY = "8u-reels-sound";
// İzlənmiş videolar (sahib 2026-11-19: «videolar davamlı təzələnməlidir»): lent hər açılışda əvvəl görülməyənləri göstərir,
// izlənmişlər sona keçir. Telefonda saxlanır, heç yerə göndərilmir. 2000 (sahib 2026-11-20: «heç təkrar olmayan»): lentdəki
// bütün videolardan (oz_x.REELS_MAX 1000 + öz xəbərlərimiz) çox — görülən video yaddaşdan düşüb yenidən «təzə» olmur.
const SEEN_KEY = "8u-reels-seen", SEEN_MAX = 2000;
// İlk açılışda böyük ox (sahib 2026-11-20: «videoların jestlə dəyişdiyini göstərən (ilk dəfə yalnız) böyük ox»): bir dəfə göstərilir.
const HINT_KEY = "8u-reels-hint";
// Videonun açarı (sahib 2026-11-23: «3 dəfə açmışam hər dəfə öncə baxdığım video çıxıb»): X-in media nömrəsi, ünvan yox. Eyni video
// başqa paylaşımda, başqa ölçüdə (480x852 / 720x1280), başqa ?tag= ilə və ya öz video xəbərimizdə gələndə də bir açardır — izlənmiş
// video başqa ünvanla «təzə» kimi qayıtmır. Köhnə yaddaşdakı ünvanlar da oxunanda açara çevrilir.
export const vkey = u => { const m = /\/(?:ext_tw_video|amplify_video|tweet_video)\/(\d{6,25})\//.exec(u || ""); return m ? m[1] : String(u || "").split("?")[0]; };
const K = v => v.key || vkey(v.u);
// Yaddaş yazılmayanda (gizli rejim, dolu yaddaş, sosial şəbəkənin daxili brauzeri) siyahı bu səhifənin yaddaşında qalır: lenti bir
// səhifədə yenidən açanda da izlənmiş video birinci gəlmir.
let mem = null;
export const seenOrder = () => {
  if (mem) return mem;
  try { return [...new Set(JSON.parse(localStorage.getItem(SEEN_KEY) || "[]").map(vkey).reverse())].reverse(); } catch { return []; }
};
export const markSeen = u => {
  const k = vkey(u), a = seenOrder().filter(x => x !== k);
  a.push(k);
  const keep = a.slice(-SEEN_MAX);
  try { localStorage.setItem(SEEN_KEY, JSON.stringify(keep)); mem = null; } catch { mem = keep; }
};

const CSS = `html,body{margin:0;height:100%;background:#000;color:#fff;font:15px/1.35 system-ui,-apple-system,Segoe UI,Roboto,sans-serif;-webkit-tap-highlight-color:transparent}
.feed{height:100%;overflow-y:auto;scroll-snap-type:y mandatory;overscroll-behavior:contain;scrollbar-width:none}
.feed::-webkit-scrollbar{display:none}
section{position:relative;height:100%;scroll-snap-align:start;scroll-snap-stop:always;overflow:hidden}
video{position:absolute;inset:0;z-index:0;width:100%;height:100%;object-fit:contain;background:#000}
.cap{position:absolute;z-index:1;left:0;right:64px;bottom:0;padding:40px 14px calc(18px + env(safe-area-inset-bottom));background:linear-gradient(transparent,#000b);pointer-events:none}
.cap b{display:block;font-size:14px;text-shadow:0 1px 2px #000}
.cap span{display:block;margin-top:4px;font-weight:700;font-size:16px;text-shadow:0 1px 2px #000}
.cap a{pointer-events:auto;display:inline-block;margin-top:8px;padding:6px 12px;border:1px solid #fff9;border-radius:99px;color:#fff;text-decoration:none;font-size:13px;background:#0005}
.p::after{content:"▶";position:absolute;left:50%;top:50%;transform:translate(-50%,-50%);font-size:46px;color:#fffd;pointer-events:none;text-shadow:0 2px 12px #000}
.bar{position:absolute;z-index:1;left:0;bottom:0;height:3px;background:#e11d48;width:0;pointer-events:none}
button{position:fixed;right:12px;z-index:2;width:44px;height:44px;border-radius:50%;border:0;background:#0009;color:#fff;font-size:20px;line-height:44px;padding:0;cursor:pointer}
.x{top:calc(12px + env(safe-area-inset-top))}
.lg{left:12px;right:auto;top:calc(12px + env(safe-area-inset-top));width:auto;height:auto;padding:7px 12px;border-radius:12px;background:#0007;font-size:18px;font-weight:800;line-height:1.2;letter-spacing:.2px;text-shadow:0 1px 2px #000}
.lg i{font-style:normal;color:#e11d48}
.snd{bottom:calc(96px + env(safe-area-inset-bottom))}
.sh{position:absolute;bottom:calc(150px + env(safe-area-inset-bottom));width:auto;padding:0 14px;border-radius:22px;font-size:14px;font-weight:700}
.wait{position:fixed;inset:0;margin:auto;width:36px;height:36px;border:3px solid #fff3;border-top-color:#fff;border-radius:50%;animation:spin .8s linear infinite}
@keyframes spin{to{transform:rotate(360deg)}}
.end{display:grid;place-items:center;text-align:center;padding:24px;color:#ccc}
.new{position:fixed;z-index:2;left:50%;top:calc(16px + env(safe-area-inset-top));transform:translateX(-50%);padding:6px 14px;border-radius:99px;background:#e11d48;color:#fff;font-weight:700;font-size:14px;pointer-events:none}
.new[hidden]{display:none}
.hint{position:fixed;z-index:3;inset:0;display:grid;place-content:center;justify-items:center;gap:14px;background:#0008;font-size:19px;font-weight:800;text-align:center;text-shadow:0 2px 8px #000;transition:opacity .4s}
.hint i{line-height:0;filter:drop-shadow(0 2px 8px #000);animation:up 1.2s ease-in-out infinite}
.hint.off{opacity:0;pointer-events:none}
@keyframes up{0%,100%{transform:translateY(24px);opacity:.5}50%{transform:translateY(-24px);opacity:1}}`;

let live = null;

// Lentin sırası: əvvəl heç görülməyənlər (mix), sonra izlənmişlər — ən çoxdan baxılan birinci (sahib 2026-11-20: «heç təkrar olmayan»;
// 2026-11-23: hər açılışda əvvəl baxılan video birinci çıxırdı). order: izlənmiş açarlar, ən köhnəsi əvvəl.
export function list(S, reels, order = seenOrder()) {
  const own = (S?.data?.articles || []).filter(a => a.xv && MP4.test(a.xv.u)).map(a => ({
    u: a.xv.u, i: a.imageUrl, w: a.xv.w, h: a.xv.h, n: "8ulduz.az", m: "xeber", t: a.publishedAt, title: plain(a.title), link: a.sourceUrl, k: a.id, v: OWN_V }));
  const x = reels.filter(r => MP4.test(r.u)).map(r => ({ u: r.u, i: r.i, w: r.w, h: r.h, n: r.n, m: r.m || "idman", t: r.t, link: `https://x.com/${r.a}/status/${r.id}`, k: String(r.id || ""), p: r.p === 1,
    v: Number.isInteger(r.v) ? r.v : -1, q: r.q === "u" ? "u" : "h", c: typeof r.c === "string" ? r.c.slice(0, 140) : "" }));
  const keys = new Set(), all = [];
  for (const v of [...own, ...x]) { v.key = vkey(v.u); if (!keys.has(v.key) && keys.add(v.key)) all.push(v); }   // eyni video bir dəfə; öz xəbərimiz X nüsxəsindən üstündür
  const at = new Map(order.map((k, i) => [k, i]));
  return [...mix(all.filter(v => !at.has(v.key))), ...all.filter(v => at.has(v.key)).sort((a, b) => at.get(a.key) - at.get(b.key))];
}

// TikTok kimi qarışıq axın (sahib 2026-11-19: «video axını tiktok kimi olsun», «əksəriyyəti futboldur … proporsional olsun
// müxtəlif mövzular»): ən çox baxılan əvvəl (rank), amma eyni mövzu son SPREAD videoda varsa növbəti mövzu gəlir — futbol lenti
// doldurmur; eyni hesabdan iki video ardıcıl gəlmir.
// İki sinif (sahib 2026-11-22: «videoların 60%-i … hadisələr …, Təmir-tadilatdakı videolar bənzəri videolar (çox fərqli mövzularda)»):
// hadisə və yeniliklər («h») ilə usta işi («u») 3:2 növbə ilə — h h u h u; bir sinif qurtaranda o biri davam edir.
// Lent xəbər anı ilə açılır (sahib 2026-11-23: «hadisə və xəbər xarakterli videolarla bağlı da vəziyyət düzgün deyil»): hadisə
// sinfində «xeber» mövzusunun ən çox baxılanı birincidir.
const PATTERN = [0, 0, 1, 0, 1];   // 1 — usta işi
// Ən çox baxılan və təzə əvvəl (sahib 2026-11-23: «20-80 yaş arası ən çox baxılan videolar olsun. boş boş videolardır indi
// əksəriyyəti»): reels «v» — X-in baxış sayı; hər 12 saat yaş baxışın bir onluq dərəcəsinə bərabərdir (12 saatlıq 1 milyon ≈ təzə
// 100 min). Birinci dərəcəli mənbə (sahib 2026-11-20, reels «p») yarım dərəcə önədir — əvvəl yaşına baxmadan önə keçirdi. Sayı
// bilinməyən video ən sonda; öz video xəbərimizin sayı yoxdur, orta populyar video kimi sayılır (OWN_V). Əvvəl mövzular ciddi növbə
// ilə gəlirdi və hər mövzunun başı — 6 min baxışlı da olsa — lentin əvvəlinə düşürdü.
const AGE_PER_DECADE = 12 * 3600e3, P_BONUS = 0.5, OWN_V = 1e5, LEAD = "xeber", SPREAD = 3;
const rank = v => Math.log10(Math.max(v.v ?? 0, 0) + 1) - (Date.now() - (Date.parse(v.t) || 0)) / AGE_PER_DECADE + (v.p ? P_BONUS : 0);
function lane(list) {
  const rest = list.map(v => [rank(v), v]).sort((a, b) => b[0] - a[0]).map(([, v]) => v), out = [];
  const lead = rest.findIndex(v => v.m === LEAD);
  if (lead > 0) rest.unshift(rest.splice(lead, 1)[0]);
  while (rest.length) {   // son SPREAD videoda olmayan mövzu; yoxdursa son SPREAD−1, … ; heç biri yoxdursa ən çox baxılan
    let i = -1;
    for (let k = SPREAD; k > 0 && i < 0; k--) { const recent = out.slice(-k).map(v => v.m || "idman"); i = rest.findIndex(v => !recent.includes(v.m || "idman")); }
    out.push(rest.splice(i < 0 ? 0 : i, 1)[0]);
  }
  return out;
}
export function mix(list) {
  const h = lane(list.filter(v => v.q !== "u")), u = lane(list.filter(v => v.q === "u")), rr = [];
  for (let i = 0; h.length || u.length; i++) {
    const want = PATTERN[i % PATTERN.length] ? u : h;
    rr.push((want.length ? want : want === u ? h : u).shift());
  }
  const out = [];
  while (rr.length) {
    const last = out[out.length - 1]?.n, i = rr.findIndex(v => v.n !== last);
    out.push(rr.splice(i < 0 ? 0 : i, 1)[0]);
  }
  return out;
}

// Bitməyən lent (sahib 2026-11-20: «bitməyən lent … ən yüksək səviyyədə»): görülməyənlər qurtaranda lent dayanmır — əvvəl
// görülmüşlər, ən çoxdan görülən birinci, ən son baxılan REPLAY_GAP video istisna, mövzu növbəsi ilə yenidən gəlir.
export function replay(pool, order, gap = REPLAY_GAP) {
  gap = Math.min(gap, Math.floor(pool.length / 2));   // az video olanda da lent dövr edir
  const recent = new Set(gap ? order.slice(-gap) : []), at = new Map(order.map((k, i) => [k, i]));
  const old = pool.filter(v => !recent.has(K(v))).sort((a, b) => (at.get(K(a)) ?? -1) - (at.get(K(b)) ?? -1));
  return mix(old.slice(0, REPLAY_BATCH));
}
const REPLAY_GAP = 15, REPLAY_BATCH = 30;

// Lent açıq ikən yeni videolar (sahib 2026-11-19: «tiktok kimi videolar daima təzələnsin»; 2026-11-20: «tiktokdan geri qalmasın»):
// dəqiqədə bir, yalnız vərəq görünəndə. Fayl əvvəl dəqiqəlik canlı kanaldan (live budağı: yazıcıdan ~5 dəq), alınmasa saytdan.
const FRESH_MS = 60e3;
const LIVE = "https://raw.githubusercontent.com/8ulduz/8ulduz/live/m/";
async function items(url, opt) {
  try {
    const r = await fetch(url, opt);
    if (r.ok) { const d = (await r.json()).items; if (Array.isArray(d)) return d; }
  } catch {}
  return null;
}
export async function load() {
  const slot = Math.floor((Date.now() / 1000 - 45) / 60);
  for (const m of [slot, slot - 1]) {
    const d = await items(`${LIVE}${m}/reels.json`, { cache: "no-store", mode: "cors", credentials: "omit" });
    if (d) return d;
  }
  return (await items(`${FILE}?t=${Math.floor(Date.now() / 6e4)}`)) || [];
}

// Paylaşım keçidi (sahib 2026-11-20: «videolentdəki paylaşım x-a aparır. bizim sayta olsun, istəyən keçər mənbəyə»): saytın öz ünvanı,
// açan adam lentə həmin videodan başlayır; mənbəyə keçid videonun altındakı düymədədir.
export const shareLink = v => `https://8ulduz.az/#/videolent?r=${encodeURIComponent(v.k || "")}`;
// Paylaşılan video bu telefonda artıq izlənibsə birinci yox, ikinci gəlir (sahib 2026-11-23: izlənmiş video birinci çıxmasın) —
// lent təzə videodan açılır, paylaşılan bir sürüşdürmə uzaqdadır.
export function first(items, k, order = seenOrder()) {
  const i = k ? items.findIndex(v => v.k === k) : -1;
  if (i < 0) return items;
  const rest = [...items.slice(0, i), ...items.slice(i + 1)];
  return order.includes(K(items[i])) && rest.length ? [rest[0], items[i], ...rest.slice(1)] : [items[i], ...rest];
}
export async function open(S, k = "") {
  if (live) return;
  live = {};
  const f = document.createElement("iframe");
  f.title = "Videolent";
  f.allow = "autoplay; fullscreen";
  f.style.cssText = "position:fixed;inset:0;width:100%;height:100%;border:0;z-index:2147483000;background:#000";
  f.srcdoc = `<!doctype html><meta charset="utf-8"><meta name="referrer" content="no-referrer"><style>${CSS}</style><body><div class="wait"></div></body>`;
  const close = () => {
    if (!live) return;
    removeEventListener("popstate", onPop);
    clearInterval(live.fresh);
    live.io?.disconnect();
    f.remove();
    document.documentElement.style.overflow = live.overflow || "";
    live = null;
  };
  const onPop = () => close();
  live.overflow = document.documentElement.style.overflow;
  document.documentElement.style.overflow = "hidden";
  history.pushState({ reels: 1 }, "");
  addEventListener("popstate", onPop);
  // Lent dərhal (sahib 2026-11-22: «paylaşımlardan videoları açanda sıçrayış olmadan ani keçid»): qara çərçivə videoların siyahısını
  // gözləmədən açılır, siyahı gələndə dolur — arada ana səhifə görünüb itmir.
  const ready = new Promise(res => f.addEventListener("load", res, { once: true }));
  document.body.append(f);
  const items = first(list(S, await load()), k);
  await ready;
  build(f, items, () => history.back(), async () => list(S, await load()));
}

const slide = v => `<section><video playsinline loop preload="none" data-src="${esc(v.u)}" data-poster="${esc(px(v.i, 720))}"></video><div class="bar"></div><div class="cap"><b>${esc(v.n)}</b>${v.title || v.c ? `<span>${esc(v.title || v.c)}</span>` : ""}<a href="${esc(v.link)}" target="${v.title ? "_top" : "_blank"}" rel="noopener">${v.title ? "Xəbəri oxu" : "X-də bax ↗"}</a></div><button class="sh" type="button" aria-label="Paylaş" data-link="${esc(shareLink(v))}" data-title="${esc(v.title || v.c || v.n)}">Paylaş</button></section>`;

function build(f, items, back, more) {
  const doc = f.contentDocument, win = f.contentWindow;
  if (!doc || !live) return;
  let sound = false;
  try { sound = sessionStorage.getItem(SOUND_KEY) === "1"; } catch {}
  doc.body.innerHTML = `<div class="feed">${items.map(slide).join("")}<section class="end"><p>${items.length ? "Videolar yüklənir…" : "Hələ video yoxdur. Bir az sonra yenidən baxın."}</p></section></div><button class="lg" type="button" aria-label="8ulduz.az — sayta qayıt">8ulduz<i>.az</i></button><button class="x" type="button" aria-label="Bağla">✕</button><button class="snd" type="button" aria-label="Səs">${sound ? "🔊" : "🔇"}</button><div class="new" hidden></div>`;
  const feed = doc.querySelector(".feed"), slides = [...feed.querySelectorAll("section:not(.end)")], sndBtn = doc.querySelector(".snd");
  const pos = s => slides.indexOf(s);
  const vid = s => s.querySelector("video");
  const near = i => {
    for (const s of slides.slice(Math.max(0, i - 1), i + 3)) { const v = vid(s); if (!v.poster && v.dataset.poster) v.poster = v.dataset.poster; }
    // növbəti video əvvəlcədən yüklənir: sürüşdürəndə dərhal başlayır (TikTok kimi); yalnız biri — internet paketi qorunur
    const n = slides[i + 1] && vid(slides[i + 1]);
    if (n && !n.src) { n.preload = "auto"; n.src = n.dataset.src; }
  };
  const play = s => {
    markSeen(vid(s).dataset.src);
    const v = vid(s);
    if (!v.src) v.src = v.dataset.src;
    v.muted = !sound;
    v.play().then(() => s.classList.remove("p")).catch(() => { if (!v.muted) { v.muted = true; sound = false; sndBtn.textContent = "🔇"; v.play().catch(() => s.classList.add("p")); } else s.classList.add("p"); });
  };
  const stop = s => {
    const v = vid(s);
    if (!v.src) return;
    v.pause();
    // uzaqdakı slaydın videosu yaddaşdan çıxır: yüzlərlə video açıq qalmasın
    if (Math.abs(pos(s) - live.at) > 2) { v.removeAttribute("src"); v.load(); }
  };
  live.at = 0;
  live.io = new win.IntersectionObserver(es => {
    for (const e of es) {
      const s = e.target;
      if (e.isIntersecting && e.intersectionRatio >= 0.6) { live.at = pos(s); near(live.at); play(s); if (live.at >= slides.length - 3) refill(); }
      else stop(s);
    }
  }, { root: feed, threshold: [0, 0.6] });
  const wire = s => {
    live.io.observe(s);
    const v = vid(s), bar = s.querySelector(".bar");
    v.addEventListener("timeupdate", () => { if (v.duration) bar.style.width = `${(v.currentTime / v.duration) * 100}%`; });
  };
  slides.forEach(wire);
  near(0);
  // Yeni videolar izlənən videonun ardınca girir: barmaqla bir sürüşdürmə — təzə video. Görülənlər təkrar gəlmir.
  const have = new Set(items.map(K)), pool = new Map(items.map(v => [K(v), v])), note = doc.querySelector(".new");
  const put = (list, at) => {   // at: bu slayddan sonra; yoxdursa lentin sonuna
    const tpl = doc.createElement("template");
    tpl.innerHTML = list.map(slide).join("");
    const fresh = [...tpl.content.children];
    if (at) at.after(...fresh); else feed.querySelector(".end").before(...fresh);
    slides.splice(at ? pos(at) + 1 : slides.length, 0, ...fresh);
    fresh.forEach(wire);
    near(live.at);
  };
  const fetchNew = async () => {
    const all = await more(), watched = new Set(seenOrder());
    for (const v of all) if (!pool.has(K(v))) pool.set(K(v), v);
    const add = all.filter(v => !have.has(K(v)) && !watched.has(K(v)));
    for (const v of add) have.add(K(v));
    return add;
  };
  const freshTick = async () => {
    if (document.visibilityState !== "visible" || !live) return;
    const add = await fetchNew();
    if (!add.length || !live) return;
    put(add, slides[live.at] || null);
    note.textContent = `+${add.length} yeni video ↓`;
    note.hidden = false;
    setTimeout(() => { note.hidden = true; }, 4000);
  };
  let filling = false;
  const refill = async () => {   // lentin sonuna 3 video qalıb: əvvəl təzələr, yoxdursa çoxdan görülənlər — lent bitmir
    if (filling || !live) return;
    filling = true;
    try {
      const add = await fetchNew();
      if (!live) return;
      const next = add.length ? add : replay([...pool.values()], seenOrder());
      if (next.length) put(next, null);
    } finally { filling = false; }
  };
  live.fresh = setInterval(freshTick, FRESH_MS);
  feed.addEventListener("click", e => {
    if (e.target.closest("a")) return;
    const sh = e.target.closest(".sh");
    if (sh) {
      const url = sh.dataset.link;
      if (navigator.share) navigator.share({ url, title: sh.dataset.title }).catch(() => {});
      else navigator.clipboard?.writeText(url).then(() => { sh.textContent = "Kopyalandı ✓"; setTimeout(() => { sh.textContent = "Paylaş"; }, 1500); }).catch(() => {});
      return;
    }
    const s = e.target.closest("section:not(.end)");
    if (!s) return;
    const v = vid(s);
    if (v.paused) { v.muted = !sound; v.play().then(() => s.classList.remove("p")).catch(() => {}); } else { v.pause(); s.classList.add("p"); }
  });
  sndBtn.addEventListener("click", () => {
    sound = !sound;
    try { sessionStorage.setItem(SOUND_KEY, sound ? "1" : "0"); } catch {}
    sndBtn.textContent = sound ? "🔊" : "🔇";
    const s = slides[live.at];
    if (s) { const v = vid(s); v.muted = !sound; if (v.paused) play(s); }
  });
  doc.querySelector(".x").addEventListener("click", back);
  doc.querySelector(".lg").addEventListener("click", back);
  doc.addEventListener("keydown", e => {
    if (e.key === "Escape") back();
    else if (e.key === "ArrowDown" || e.key === "ArrowUp") { e.preventDefault(); feed.scrollBy({ top: (e.key === "ArrowDown" ? 1 : -1) * feed.clientHeight, behavior: "smooth" }); }
  });
  let hinted = true;
  try { hinted = !!localStorage.getItem(HINT_KEY); } catch {}
  if (!hinted && slides.length > 1) {
    try { localStorage.setItem(HINT_KEY, "1"); } catch {}
    const hint = doc.createElement("div");
    hint.className = "hint";
    hint.innerHTML = '<i><svg width="66" height="88" viewBox="0 0 24 32" aria-hidden="true"><path d="M12 1 1 13h7v18h8V13h7z" fill="#fff"/></svg></i><p>Növbəti video üçün<br>yuxarı sürüşdürün</p>';
    const off = () => { hint.classList.add("off"); setTimeout(() => hint.remove(), 500); };
    hint.addEventListener("pointerdown", off, { once: true });
    feed.addEventListener("scroll", off, { once: true, passive: true });
    setTimeout(off, 4500);
    doc.body.append(hint);
  }
  f.focus();
  win.focus();
}
