// Videolent: şaquli, tam ekran, barmaqla sürüşdürülən video lenti (sahib, 2026-11-19: «tiktok stilini düzəlt.
// videoların bəzilərinə yazı tərcümə ehtiyac olmaya bilər… gündə 40»). Tənbəl modul: yalnız «Videolent» basılanda
// yüklənir, ilk açılışa heç nə gətirmir.
//
// Videolar: data/reels.json (X-in yazısız videoları, yeniləyici oz_x.reels + content_policy.enforce ilə yazır) və lentdəki
// X videolu öz xəbərlərimiz (a.xv). X videonu mənbə ünvanı göndərən sorğuya vermir (403): lent referrer göndərməyən
// srcdoc çərçivəsinin içində qurulur, video elementlərini bu modul (ana səhifənin kodu) yaradır — çərçivədə skript yoxdur.
// Eyni anda bir video yüklənir və oynayır; poster yalnız yaxındakı slaydlara qoyulur (internet paketi və batareya).

const FILE = new URL("../data/reels.json", import.meta.url).href;
// Hər videonun üstündə saytın loqosu (sahib 2026-11-20: «bütün videoların üstündə başda 8ulduz yazısı … basanda sayt açılsın»): basanda
// lent bağlanır və oxucu sayta qayıdır — ✕ ilə eyni.
const LOGO = new URL("./logo-80.png", import.meta.url).href;
const MP4 = /^https:\/\/video\.twimg\.com\/[\w/.-]+\.mp4(\?[\w=&.-]*)?$/;
const esc = s => String(s ?? "").replace(/[&<>"']/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[c]);
const plain = s => { const t = document.createElement("textarea"); t.innerHTML = String(s ?? ""); return t.value; };
const px = (u, w) => /^https:\/\/pbs\.twimg\.com\//.test(u || "") ? `https://wsrv.nl/?url=${encodeURIComponent(u)}&w=${w}&we&output=webp&q=70` : "";
const SOUND_KEY = "8u-reels-sound";
// İzlənmiş videolar (sahib 2026-11-19: «videolar davamlı təzələnməlidir»): lent hər açılışda əvvəl görülməyənləri göstərir,
// izlənmişlər sona keçir. Telefonda saxlanır, heç yerə göndərilmir. 2000 (sahib 2026-11-20: «heç təkrar olmayan»): lentdəki
// bütün videolardan (oz_x.REELS_MAX 800 + öz xəbərlərimiz) çox — görülən video yaddaşdan düşüb yenidən «təzə» olmur.
const SEEN_KEY = "8u-reels-seen", SEEN_MAX = 2000;
// İlk açılışda böyük ox (sahib 2026-11-20: «videoların jestlə dəyişdiyini göstərən (ilk dəfə yalnız) böyük ox»): bir dəfə göstərilir.
const HINT_KEY = "8u-reels-hint";
const seenOrder = () => { try { return JSON.parse(localStorage.getItem(SEEN_KEY) || "[]"); } catch { return []; } };
const seenSet = () => new Set(seenOrder());
const markSeen = u => { try { const a = seenOrder().filter(x => x !== u); a.push(u); localStorage.setItem(SEEN_KEY, JSON.stringify(a.slice(-SEEN_MAX))); } catch {} };

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
.lg{left:12px;right:auto;top:calc(12px + env(safe-area-inset-top));width:auto;height:auto;padding:7px 10px;border-radius:12px;background:#0007;line-height:0}
.lg img{height:24px;width:auto;filter:drop-shadow(0 1px 2px #000)}
.snd{bottom:calc(96px + env(safe-area-inset-bottom))}
.sh{position:absolute;bottom:calc(150px + env(safe-area-inset-bottom));font-size:22px}
.end{display:grid;place-items:center;text-align:center;padding:24px;color:#ccc}
.new{position:fixed;z-index:2;left:50%;top:calc(16px + env(safe-area-inset-top));transform:translateX(-50%);padding:6px 14px;border-radius:99px;background:#e11d48;color:#fff;font-weight:700;font-size:14px;pointer-events:none}
.new[hidden]{display:none}
.hint{position:fixed;z-index:3;inset:0;display:grid;place-content:center;justify-items:center;gap:14px;background:#0008;font-size:19px;font-weight:800;text-align:center;text-shadow:0 2px 8px #000;transition:opacity .4s}
.hint i{line-height:0;filter:drop-shadow(0 2px 8px #000);animation:up 1.2s ease-in-out infinite}
.hint.off{opacity:0;pointer-events:none}
@keyframes up{0%,100%{transform:translateY(24px);opacity:.5}50%{transform:translateY(-24px);opacity:1}}`;

let live = null;

function list(S, reels) {
  const own = (S?.data?.articles || []).filter(a => a.xv && MP4.test(a.xv.u)).map(a => ({
    u: a.xv.u, i: a.imageUrl, w: a.xv.w, h: a.xv.h, n: "8ulduz.az", m: "xeber", t: a.publishedAt, title: plain(a.title), link: a.sourceUrl, k: a.id }));
  const x = reels.filter(r => MP4.test(r.u)).map(r => ({ u: r.u, i: r.i, w: r.w, h: r.h, n: r.n, m: r.m || "idman", t: r.t, link: `https://x.com/${r.a}/status/${r.id}`, k: String(r.id || "") }));
  const seen = new Set(), watched = seenSet();
  const all = [...own, ...x].sort((a, b) => String(b.t).localeCompare(String(a.t))).filter(v => !seen.has(v.u) && seen.add(v.u));
  return [...mix(all.filter(v => !watched.has(v.u))), ...mix(all.filter(v => watched.has(v.u)))];   // əvvəl görülməyənlər
}

// TikTok kimi qarışıq axın (sahib 2026-11-19: «video axını tiktok kimi olsun», «əksəriyyəti futboldur … proporsional olsun
// müxtəlif mövzular»): mövzular növbə ilə gəlir (idman, təbiət, elm, kino …; hər açılışda başqa sıra), hər mövzunun içində ən
// təzəsi önə; eyni hesabdan iki video ardıcıl gəlmir.
export function mix(list) {
  const groups = new Map();
  for (const v of list) { const k = v.m || "idman"; if (!groups.has(k)) groups.set(k, []); groups.get(k).push(v); }
  const order = [...groups.values()].sort(() => Math.random() - 0.5), rr = [];
  while (order.some(g => g.length)) for (const g of order) if (g.length) rr.push(g.shift());
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
  const recent = new Set(gap ? order.slice(-gap) : []), at = new Map(order.map((u, i) => [u, i]));
  const old = pool.filter(v => !recent.has(v.u)).sort((a, b) => (at.get(a.u) ?? -1) - (at.get(b.u) ?? -1));
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
async function load() {
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
export function first(items, k) {
  const i = k ? items.findIndex(v => v.k === k) : -1;
  return i > 0 ? [items[i], ...items.slice(0, i), ...items.slice(i + 1)] : items;
}
export async function open(S, k = "") {
  if (live) return;
  live = {};
  const items = first(list(S, await load()), k);
  const f = document.createElement("iframe");
  f.title = "Videolent";
  f.allow = "autoplay; fullscreen";
  f.style.cssText = "position:fixed;inset:0;width:100%;height:100%;border:0;z-index:2147483000;background:#000";
  f.srcdoc = `<!doctype html><meta charset="utf-8"><meta name="referrer" content="no-referrer"><style>${CSS}</style><body></body>`;
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
  f.addEventListener("load", () => build(f, items, () => history.back(), async () => list(S, await load())), { once: true });
  document.body.append(f);
}

const slide = v => `<section><video playsinline loop preload="none" data-src="${esc(v.u)}" data-poster="${esc(px(v.i, 720))}"></video><div class="bar"></div><div class="cap"><b>${esc(v.n)}</b>${v.title ? `<span>${esc(v.title)}</span>` : ""}<a href="${esc(v.link)}" target="${v.title ? "_top" : "_blank"}" rel="noopener">${v.title ? "Xəbəri oxu" : "X-də bax ↗"}</a></div><button class="sh" type="button" aria-label="Paylaş" data-link="${esc(shareLink(v))}" data-title="${esc(v.title || v.n)}">↗</button></section>`;

function build(f, items, back, more) {
  const doc = f.contentDocument, win = f.contentWindow;
  if (!doc || !live) return;
  let sound = false;
  try { sound = sessionStorage.getItem(SOUND_KEY) === "1"; } catch {}
  doc.body.innerHTML = `<div class="feed">${items.map(slide).join("")}<section class="end"><p>${items.length ? "Videolar yüklənir…" : "Hələ video yoxdur. Bir az sonra yenidən baxın."}</p></section></div><button class="lg" type="button" aria-label="8ulduz.az — sayta qayıt"><img src="${LOGO}" alt="8ULDUZ" width="106" height="24"></button><button class="x" type="button" aria-label="Bağla">✕</button><button class="snd" type="button" aria-label="Səs">${sound ? "🔊" : "🔇"}</button><div class="new" hidden></div>`;
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
  const have = new Set(items.map(v => v.u)), pool = new Map(items.map(v => [v.u, v])), note = doc.querySelector(".new");
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
    const all = await more();
    for (const v of all) if (!pool.has(v.u)) pool.set(v.u, v);
    const add = all.filter(v => !have.has(v.u) && !seenSet().has(v.u));
    for (const v of add) have.add(v.u);
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
      else navigator.clipboard?.writeText(url).then(() => { sh.textContent = "✓"; setTimeout(() => { sh.textContent = "↗"; }, 1500); }).catch(() => {});
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
