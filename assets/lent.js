// Videolent: şaquli, tam ekran, barmaqla sürüşdürülən video lenti (sahib, 2026-11-19: «tiktok stilini düzəlt.
// videoların bəzilərinə yazı tərcümə ehtiyac olmaya bilər… gündə 40»). Tənbəl modul: yalnız «Videolent» basılanda
// yüklənir, ilk açılışa heç nə gətirmir.
//
// Videolar: data/reels.json (X-in yazısız videoları, yeniləyici oz_x.reels + content_policy.enforce ilə yazır) və lentdəki
// X videolu öz xəbərlərimiz (a.xv). X videonu mənbə ünvanı göndərən sorğuya vermir (403): lent referrer göndərməyən
// srcdoc çərçivəsinin içində qurulur, video elementlərini bu modul (ana səhifənin kodu) yaradır — çərçivədə skript yoxdur.
// Eyni anda bir video yüklənir və oynayır; poster yalnız yaxındakı slaydlara qoyulur (internet paketi və batareya).

const FILE = new URL("../data/reels.json", import.meta.url).href;
const MP4 = /^https:\/\/video\.twimg\.com\/[\w/.-]+\.mp4(\?[\w=&.-]*)?$/;
const esc = s => String(s ?? "").replace(/[&<>"']/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[c]);
const plain = s => { const t = document.createElement("textarea"); t.innerHTML = String(s ?? ""); return t.value; };
const px = (u, w) => /^https:\/\/pbs\.twimg\.com\//.test(u || "") ? `https://wsrv.nl/?url=${encodeURIComponent(u)}&w=${w}&we&output=webp&q=70` : "";
const SOUND_KEY = "8u-reels-sound";
// İzlənmiş videolar (sahib 2026-11-19: «videolar davamlı təzələnməlidir»): lent hər açılışda əvvəl görülməyənləri göstərir,
// izlənmişlər sona keçir. Telefonda saxlanır (ən çox 400 ünvan), heç yerə göndərilmir.
const SEEN_KEY = "8u-reels-seen", SEEN_MAX = 400;
const seenSet = () => { try { return new Set(JSON.parse(localStorage.getItem(SEEN_KEY) || "[]")); } catch { return new Set(); } };
const markSeen = u => { try { const a = [...seenSet()].filter(x => x !== u); a.push(u); localStorage.setItem(SEEN_KEY, JSON.stringify(a.slice(-SEEN_MAX))); } catch {} };

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
.snd{bottom:calc(96px + env(safe-area-inset-bottom))}
.end{display:grid;place-items:center;text-align:center;padding:24px;color:#ccc}`;

let live = null;

function list(S, reels) {
  const own = (S?.data?.articles || []).filter(a => a.xv && MP4.test(a.xv.u)).map(a => ({
    u: a.xv.u, i: a.imageUrl, w: a.xv.w, h: a.xv.h, n: "8ulduz.az", t: a.publishedAt, title: plain(a.title), link: a.sourceUrl }));
  const x = reels.filter(r => MP4.test(r.u)).map(r => ({ u: r.u, i: r.i, w: r.w, h: r.h, n: r.n, t: r.t, link: `https://x.com/${r.a}/status/${r.id}` }));
  const seen = new Set(), watched = seenSet();
  const all = [...own, ...x].sort((a, b) => String(b.t).localeCompare(String(a.t))).filter(v => !seen.has(v.u) && seen.add(v.u));
  return [...all.filter(v => !watched.has(v.u)), ...all.filter(v => watched.has(v.u))];   // əvvəl görülməyənlər, ən təzəsi önə
}

export async function open(S) {
  if (live) return;
  live = {};
  let reels = [];
  try {
    const r = await fetch(`${FILE}?t=${Math.floor(Date.now() / 6e4)}`);
    if (r.ok) reels = (await r.json()).items || [];
  } catch {}
  const items = list(S, Array.isArray(reels) ? reels : []);
  const f = document.createElement("iframe");
  f.title = "Videolent";
  f.allow = "autoplay; fullscreen";
  f.style.cssText = "position:fixed;inset:0;width:100%;height:100%;border:0;z-index:2147483000;background:#000";
  f.srcdoc = `<!doctype html><meta charset="utf-8"><meta name="referrer" content="no-referrer"><style>${CSS}</style><body></body>`;
  const close = () => {
    if (!live) return;
    removeEventListener("popstate", onPop);
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
  f.addEventListener("load", () => build(f, items, () => history.back()), { once: true });
  document.body.append(f);
}

function build(f, items, back) {
  const doc = f.contentDocument, win = f.contentWindow;
  if (!doc || !live) return;
  let sound = false;
  try { sound = sessionStorage.getItem(SOUND_KEY) === "1"; } catch {}
  doc.body.innerHTML = `<div class="feed">${items.map((v, i) => `<section data-i="${i}"><video playsinline loop preload="none" data-src="${esc(v.u)}" data-poster="${esc(px(v.i, 720))}"></video><div class="bar"></div><div class="cap"><b>${esc(v.n)}</b>${v.title ? `<span>${esc(v.title)}</span>` : ""}<a href="${esc(v.link)}" target="${v.title ? "_top" : "_blank"}" rel="noopener">${v.title ? "Xəbəri oxu" : "X-də bax ↗"}</a></div></section>`).join("")}<section class="end"><p>${items.length ? "Hamısını izlədiniz. Yeni videolar gün ərzində əlavə olunur." : "Hələ video yoxdur. Bir az sonra yenidən baxın."}</p></section></div><button class="x" type="button" aria-label="Bağla">✕</button><button class="snd" type="button" aria-label="Səs">${sound ? "🔊" : "🔇"}</button>`;
  const feed = doc.querySelector(".feed"), slides = [...doc.querySelectorAll("section[data-i]")], sndBtn = doc.querySelector(".snd");
  const vid = s => s.querySelector("video");
  const near = i => { for (const s of slides.slice(Math.max(0, i - 1), i + 3)) { const v = vid(s); if (!v.poster && v.dataset.poster) v.poster = v.dataset.poster; } };
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
    if (Math.abs(+s.dataset.i - live.at) > 2) { v.removeAttribute("src"); v.load(); }
  };
  live.at = 0;
  live.io = new win.IntersectionObserver(es => {
    for (const e of es) {
      const s = e.target;
      if (e.isIntersecting && e.intersectionRatio >= 0.6) { live.at = +s.dataset.i; near(live.at); play(s); }
      else stop(s);
    }
  }, { root: feed, threshold: [0, 0.6] });
  slides.forEach(s => live.io.observe(s));
  near(0);
  for (const s of slides) {
    const v = vid(s), bar = s.querySelector(".bar");
    v.addEventListener("timeupdate", () => { if (v.duration) bar.style.width = `${(v.currentTime / v.duration) * 100}%`; });
  }
  feed.addEventListener("click", e => {
    if (e.target.closest("a")) return;
    const s = e.target.closest("section[data-i]");
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
  doc.addEventListener("keydown", e => {
    if (e.key === "Escape") back();
    else if (e.key === "ArrowDown" || e.key === "ArrowUp") { e.preventDefault(); feed.scrollBy({ top: (e.key === "ArrowDown" ? 1 : -1) * feed.clientHeight, behavior: "smooth" }); }
  });
  f.focus();
  win.focus();
}
