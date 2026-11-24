// Video lenti (sahib, 2026-11-24): «Son xəbərlərdən sonra şəkildəki formatda daimi oynayan video xəbərlər olsun. oraya x dan yeni
// olan hadisə və xəbər videoları da salmaq olar öz videolarımızı da, saytların videolarını da». Nümunə: üfüqi sürüşən şaquli kartlar,
// altında başlıq. Ekrana ən çox girən kart səssiz öz-özünə oynayır, bitəndə (ən çoxu PLAY_MAX) lent növbəti karta keçir, sonuncudan
// sonra birinciyə qayıdır. Videoya basanda səs açılır/bağlanır, başlığa basanda tam oynadıcı açılır: X videosu Videolentdə (lent.js),
// YouTube videosu video səhifəsində.
//
// Tənbəl modul: app.js bölmə ekrana yaxınlaşanda yükləyir (setupVlent), ilk açılışa fayl, sorğu, iş gətirmir. Eyni anda bir video
// yüklənir və oynayır (internet paketi, batareya); kənarda qalan kartın oynadıcısı silinir. Qənaət rejimində (Save-Data) və
// «hərəkəti azalt» seçiləndə (saytın düyməsi və ya cihaz) avtomatik oynamır, kart basılanda oynayır.
//
// Mənbələr (növbə ilə qarışıq, hər biri ən yenisi əvvəl):
//  - öz videolarımız: YouTube «8ULDUZ» kanalı (data/video.json, updater.YT_NEWS);
//  - X-in hadisə və xəbər videoları (lent.js: data/reels.json «xeber», hadisə sinfi) və X videolu öz xəbərlərimiz;
//  - Azərbaycan telekanallarının YouTube videoları (data/video.json).
// X videonu mənbə ünvanı göndərən sorğuya vermir (403): video referrer göndərməyən srcdoc çərçivəsində qurulur (lent.js kimi).
import { list, load } from "./lent.js?v=1";

export const OWN = "8ULDUZ";
const MAX = 24, PLAY_MAX = 60e3, YT = "https://www.youtube-nocookie.com/embed/";
const ID = /^[\w-]{6,20}$/, MP4 = /^https:\/\/video\.twimg\.com\/[\w/.-]+\.mp4(\?[\w=&.-]*)?$/;
const esc = s => String(s ?? "").replace(/[&<>"']/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[c]);
const img = u => /^https:\/\/i\d?\.ytimg\.com\//.test(u || "") ? u : /^https:\/\//.test(u || "") ? `https://wsrv.nl/?url=${encodeURIComponent(u)}&w=360&we&output=webp&q=70` : "";
const time = v => Date.parse(v.t) || 0;

const CSS = `.vl-row{display:flex;gap:12px;overflow-x:auto;scroll-snap-type:x mandatory;overscroll-behavior-x:contain;scrollbar-width:none;padding-bottom:4px}
.vl-row::-webkit-scrollbar{display:none}
.vl-c{flex:none;width:min(58vw,240px);scroll-snap-align:start}
.vl-v{position:relative;display:block;width:100%;aspect-ratio:9/16;border:0;padding:0;border-radius:12px;overflow:hidden;background:#000;cursor:pointer}
.vl-v>img,.vl-v>iframe{position:absolute;inset:0;width:100%;height:100%;border:0;object-fit:cover}
.vl-v>.vl-b{filter:blur(14px) brightness(.6);transform:scale(1.2)}
.vl-v>.vl-w{inset:50% 0 auto;height:auto;aspect-ratio:16/9;transform:translateY(-50%)}
.vl-v>iframe{pointer-events:none;background:transparent}
.vl-v>i{position:absolute;z-index:2;font-style:normal;color:#fff;text-shadow:0 1px 3px #000}
.vl-s{left:8px;top:8px;max-width:calc(100% - 52px);padding:2px 7px;border-radius:6px;background:#000a;font-size:12px;font-weight:700;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.vl-m{right:8px;top:6px;font-size:18px}
.vl-p{left:50%;top:50%;transform:translate(-50%,-50%);font-size:44px;opacity:.9}
.vl-c.on .vl-p{display:none}
.vl-c:not(.on) .vl-m{display:none}
.vl-bar{position:absolute;z-index:2;left:0;bottom:0;height:3px;width:0;background:#e11d48}
.vl-t{display:-webkit-box;-webkit-line-clamp:3;-webkit-box-orient:vertical;overflow:hidden;margin-top:8px;color:var(--fg);font-weight:700;font-size:var(--fs-meta);line-height:var(--lh-meta)}
.vl-t:hover{text-decoration:underline}`;

// Kartlar: üç mənbə növbə ilə (öz, X, TV), hər biri ən yenisi əvvəl; eyni video bir dəfə.
export function pick(S, reels) {
  const yt = (S?.video?.items || []).filter(v => ID.test(v?.videoId || "")).map(v => ({
    kind: "yt", id: v.videoId, t: v.publishedAt, title: v.title, src: v.channel === OWN ? "8ulduz.az" : v.channel, own: v.channel === OWN,
    tall: v.channel === OWN || /\/shorts\//.test(v.url || ""), i: v.imageUrl }));
  const x = list(S, reels).filter(v => MP4.test(v.u) && v.m === "xeber" && v.q !== "u").map(v => ({
    kind: "x", u: v.u, k: v.k, t: v.t, title: v.title || v.c, src: v.n, tall: v.h > v.w * 1.2, i: v.i }));
  const lanes = [yt.filter(v => v.own), x, yt.filter(v => !v.own)].map(l => l.filter(v => v.title).sort((a, b) => time(b) - time(a)));
  const out = [], seen = new Set();
  for (let r = 0; out.length < MAX && lanes.some(l => l.length > r); r++)
    for (const l of lanes) { const v = l[r]; if (v && !seen.has(v.id || v.u) && seen.add(v.id || v.u) && out.length < MAX) out.push(v); }
  return out;
}

const card = (v, n) => `<div class="vl-c" data-n="${n}"><button type="button" class="vl-v" aria-label="Videonun səsini aç və ya bağla">${v.i && img(v.i) ? `<img class="${v.tall ? "" : "vl-b"}" src="${esc(img(v.i))}" alt="" loading="lazy" decoding="async" referrerpolicy="no-referrer">${v.tall ? "" : `<img class="vl-w" src="${esc(img(v.i))}" alt="" loading="lazy" decoding="async" referrerpolicy="no-referrer">`}` : ""}<i class="vl-s">${esc(v.src)}</i><i class="vl-m">🔇</i><i class="vl-p">▶</i><span class="vl-bar"></span></button><a class="vl-t" href="${v.kind === "yt" ? `#/videolent?v=${encodeURIComponent(v.id)}` : "#/videolent"}" data-vl="${n}">${esc(v.title)}</a></div>`;

export async function mount(sec, S, still = () => false) {
  if (sec._vl) return;
  sec._vl = {};
  if (!document.getElementById("vl-css")) { const st = document.createElement("style"); st.id = "vl-css"; st.textContent = CSS; document.head.append(st); }
  const items = pick(S, await load().catch(() => []));
  if (!items.length) { sec.remove(); return; }
  const row = document.createElement("div");
  row.className = "vl-row";
  row.innerHTML = items.map(card).join("");
  sec.append(row);
  sec.style.minHeight = "";
  const cards = [...row.children], seen = new Map();
  const auto = () => !navigator.connection?.saveData && !still();
  let cur = -1, sound = false, timer = 0, user = false, hold = 0;

  const bar = p => { const b = cards[cur]?.querySelector(".vl-bar"); if (b) b.style.width = `${Math.min(100, p * 100)}%`; };
  const stop = () => {
    clearTimeout(timer);
    removeEventListener("message", onMsg);
    if (cur >= 0) { const c = cards[cur]; c.classList.remove("on"); c.querySelector("iframe")?.remove(); bar(0); }
    cur = -1;
  };
  const next = () => {
    if (cur < 0) return;
    const n = (cur + 1) % cards.length;
    stop();
    row.scrollTo({ left: cards[n].offsetLeft - row.offsetLeft, behavior: "smooth" });   // görünən kartı IntersectionObserver oynadır
    setTimeout(() => cur < 0 && play(n), 700);
  };
  // YouTube oynadıcısı vəziyyətini postMessage ilə bildirir (iframe API skripti yüklənmir): 0 — bitdi.
  function onMsg(e) {
    const f = cards[cur]?.querySelector("iframe");
    if (!f || e.source !== f.contentWindow) return;
    let d; try { d = typeof e.data === "string" ? JSON.parse(e.data) : e.data; } catch { return; }
    const i = d?.info;
    if (d?.event === "onStateChange" ? i === 0 : i?.playerState === 0) next();
    else if (i?.duration > 0 && i.currentTime >= 0) bar(i.currentTime / i.duration);
  }
  function play(n) {
    if (n === cur || document.hidden || !sec.isConnected) return;
    stop();
    cur = n;
    const v = items[n], c = cards[n], btn = c.querySelector(".vl-v"), f = document.createElement("iframe");
    c.classList.add("on");
    c.querySelector(".vl-m").textContent = sound ? "🔊" : "🔇";
    f.allow = "autoplay; encrypted-media; picture-in-picture";
    f.title = v.title;
    if (!v.tall) f.className = "vl-w";
    if (v.kind === "yt") {
      f.src = `${YT}${encodeURIComponent(v.id)}?autoplay=1&mute=${sound ? 0 : 1}&playsinline=1&controls=0&rel=0&modestbranding=1&enablejsapi=1&origin=${encodeURIComponent(location.origin)}`;
      addEventListener("message", onMsg);
      f.addEventListener("load", () => f.contentWindow?.postMessage(JSON.stringify({ event: "listening", id: "vl", channel: "widget" }), "*"), { once: true });
    } else {
      f.srcdoc = `<!doctype html><meta charset="utf-8"><meta name="referrer" content="no-referrer"><style>html,body{margin:0;height:100%;overflow:hidden;background:transparent}video{width:100%;height:100%;object-fit:${v.tall ? "cover" : "contain"}}</style><video playsinline muted autoplay src="${esc(v.u)}"></video>`;
      f.addEventListener("load", () => {
        const el = f.contentDocument?.querySelector("video");
        if (!el) return;
        el.muted = !sound;
        el.addEventListener("ended", next);
        el.addEventListener("timeupdate", () => el.duration > 0 && bar(el.currentTime / el.duration));
        el.play().catch(() => { el.muted = true; sound = false; c.querySelector(".vl-m").textContent = "🔇"; el.play().catch(() => {}); });
      }, { once: true });
    }
    btn.append(f);
    timer = setTimeout(next, PLAY_MAX);
  }
  const setSound = on => {
    sound = on;
    const c = cards[cur], f = c?.querySelector("iframe");
    if (!f) return;
    c.querySelector(".vl-m").textContent = on ? "🔊" : "🔇";
    if (items[cur].kind === "yt") f.contentWindow?.postMessage(JSON.stringify({ event: "command", func: on ? "unMute" : "mute", args: [] }), "*");
    else { const el = f.contentDocument?.querySelector("video"); if (el) { el.muted = !on; el.play().catch(() => {}); } }
  };

  // Görünən (ən azı 60%) ən soldakı kart oynayır; heç biri görünmürsə dayanır. Əl ilə sürüşdürəndə 1,2 s gözləyir.
  const pickVisible = () => {
    if (!auto() && !user) return;
    if (cur >= 0 && (seen.get(cur) || 0) >= 0.6) return;   // oynayan kart görünürsə dəyişmir (kompüterdə 4 kart birdən görünür)
    const best = [...seen].filter(([, r]) => r >= 0.6).sort((a, b) => a[0] - b[0])[0]?.[0] ?? -1;   // ən soldakı
    if (best < 0) stop(); else play(best);
  };
  const io = new IntersectionObserver(es => {
    es.forEach(e => seen.set(Number(e.target.dataset.n), e.isIntersecting ? e.intersectionRatio : 0));
    clearTimeout(hold); hold = setTimeout(pickVisible, 250);
  }, { threshold: [0, 0.6, 0.9] });
  cards.forEach(c => io.observe(c));
  row.addEventListener("scroll", () => { clearTimeout(hold); hold = setTimeout(pickVisible, 1200); }, { passive: true });
  document.addEventListener("visibilitychange", () => document.hidden ? stop() : pickVisible());

  row.addEventListener("click", e => {
    const t = e.target.closest("[data-vl]"), b = e.target.closest(".vl-v");
    if (t) {
      const v = items[Number(t.dataset.vl)];
      if (v.kind === "x") { e.preventDefault(); stop(); import("./lent.js?v=1").then(m => m.open(S, v.k)).catch(() => {}); }
      return;
    }
    if (!b) return;
    const n = Number(b.parentElement.dataset.n);
    user = true;
    if (n !== cur) { sound = true; play(n); } else setSound(!sound);
  });
  addEventListener("popstate", () => setTimeout(pickVisible, 300));   // Videolent bağlananda lent davam edir
}
