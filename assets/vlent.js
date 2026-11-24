// Video lenti (sahib, 2026-11-24): «Son xəbərlərdən sonra şəkildəki formatda daimi oynayan video xəbərlər olsun. oraya x dan yeni
// olan hadisə və xəbər videoları da salmaq olar öz videolarımızı da, saytların videolarını da». Nümunə: üfüqi sürüşən şaquli kartlar,
// altında başlıq. Görünən ən soldakı kart səssiz öz-özünə oynayır, bitəndə (ən çoxu PLAY_MAX) lent növbəti karta keçir, sonuncudan
// sonra birinciyə qayıdır. Başlığa basanda tam oynadıcı açılır: X videosu Videolentdə (lent.js), YouTube videosu video səhifəsində.
//
// Sahib, 2026-11-24: «son xəbərlərin altındakı videoxəbərlərə basanda tam ekran olsun» (bütün növlər: öz, TV, X). Videoya basanda
// həmin kart səslə tam pəncərəyə açılır. Oynadıcı yerindən tərpənmir (iframe köçürülsə yenidən yüklənər), ona görə video olduğu yerdən
// davam edir. Kartın lentdəki yerini eyni ölçülü boş yer tutur: arxadakı səhifə tərpənmir, CLS yoxdur. Səhifənin sürüşməsi
// hadisələrlə dayandırılır, overflow dəyişmir (o da səhifəni tərpədərdi). Brauzer verirsə (Android, kompüter, iPad) əlavə olaraq
// əsl tam ekran açılır. iPhone Safari div üçün bunu vermir, orada tam pəncərə qalır. Bağlamaq: ✕, geri düyməsi, Escape.
// Bağlananda lent olduğu yerdədir, video səssiz davam edir. Tam ekranda növbəti karta keçilmir: video bitəndə ▶ görünür,
// basanda yenidən oynayır. Basmaq dayandırır və davam etdirir.
//
// Sahib, 2026-11-24 (ikinci baxış): «videolar ləngimə ilə oynayır», «videoların hamısı tam kart ölçüsündə ola bilərmi? Bizim videolar
// da daxil». Ona görə:
//  - növbəti kartın oynadıcısı oynayan video ilə yanaşı qabaqcadan hazırlanır (X: video yüklənir, YouTube: oynadıcı açılır, dayanmış),
//    keçiddə yalnız «oynat» əmri gedir; proqramla sürüşdürəndə görünüş yoxlaması 1 s gözləyir (əvvəlki kart geri seçilmir);
//  - hər video kartı tam doldurur: üfüqi video ortadan kəsilir (X: object-fit:cover; YouTube: 16:9 çərçivə kartın hündürlüyündə,
//    eni 316%, ortada), şəkil də. Öz Shorts-larımızın şəkli şaquli oar2.jpg-dir (hqdefault.jpg şaquli videoda yanlarda qara zolaqlıdır),
//    üfüqi videoların şəkli hq720.jpg (zolaqsız), yoxdursa mqdefault.jpg. Şəkillər wsrv.nl ilə 360 px-ə kiçilir.
//
// Tənbəl modul: app.js bölmə ekrana yaxınlaşanda yükləyir (setupVlent), ilk açılışa fayl, sorğu, iş gətirmir. Eyni anda bir video
// oynayır, ən çoxu iki oynadıcı (oynayan və növbəti) var; qalanları silinir. Qənaət rejimində (Save-Data) və «hərəkəti azalt»
// seçiləndə (saytın düyməsi və ya cihaz) avtomatik oynamır və qabaqcadan yükləmir, kart basılanda oynayır.
//
// Mənbələr (növbə ilə qarışıq, hər biri ən yenisi əvvəl):
//  - öz videolarımız: YouTube «8ULDUZ» kanalı (data/video.json, updater.YT_NEWS);
//  - X-in hadisə və xəbər videoları (lent.js: data/reels.json «xeber», hadisə sinfi) və X videolu öz xəbərlərimiz;
//  - Azərbaycan telekanallarının YouTube videoları (data/video.json).
// Sahib, 2026-11-24 (üçüncü baxış): «üstündə yazılar olsa da video tam kart boyu olmalıdır» — telefonda (şaquli ekran) X videosu tam
// ekranda da ekranı doldurur (cover), kompüterdə (üfüqi ekran) bütöv qalır. YouTube oynadıcısı tam ekranda bütöv qalır (düymələri kəsilməsin).
// X videonu mənbə ünvanı göndərən sorğuya vermir (403): video referrer göndərməyən srcdoc çərçivəsində qurulur (lent.js kimi).
// Ad-fəzası importu (2026-11-24, canlıda görüldü): sw.js kod faylının saxlanmış nüsxəsini dərhal verir (açar sorğusuz yoldur), təzəsi
// arxada gəlir. Yayımdan sonrakı ilk açılışda köhnə lent.js-ə adlı import ({ list, load }) bu modulu bütövlükdə sındırırdı — lent boş
// qalırdı. Ad yoxdursa işçi təzəsini artıq yükləyir: bir az sonra eyni fayl yeni ünvanla (yeni modul) soruşulur.
import * as lentNs from "./lent.js?v=1";
let L = lentNs;
const freshLent = async () => {
  for (const ms of [800, 2500]) {
    await new Promise(r => setTimeout(r, ms));
    const m = await import(`./lent.js?v=1&n=${Date.now()}`).catch(() => null);
    if (m?.list && m.load) return m;
  }
  return null;
};

export const OWN = "8ULDUZ";
const MAX = 24, PLAY_MAX = 60e3, YT = "https://www.youtube-nocookie.com/embed/";
const ID = /^[\w-]{6,20}$/, MP4 = /^https:\/\/video\.twimg\.com\/[\w/.-]+\.mp4(\?[\w=&.-]*)?$/;
const esc = s => String(s ?? "").replace(/[&<>"']/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[c]);
const wsrv = u => `https://wsrv.nl/?url=${encodeURIComponent(u)}&w=360&we&output=webp&q=70`;
const time = v => Date.parse(v.t) || 0;
// Kartın şəkli və alınmasa ehtiyatı (YouTube: video nömrəsindən).
export const poster = v => v.kind !== "yt" ? [/^https:\/\//.test(v.i || "") ? wsrv(v.i) : "", ""]
  : [wsrv(`https://i.ytimg.com/vi/${v.id}/${v.tall ? "oar2" : "hq720"}.jpg`), `https://i.ytimg.com/vi/${v.id}/${v.tall ? "hqdefault" : "mqdefault"}.jpg`];

const CSS = `.vl-row{display:flex;gap:12px;overflow-x:auto;scroll-snap-type:x mandatory;overscroll-behavior-x:contain;scrollbar-width:none;padding-bottom:4px}
.vl-row::-webkit-scrollbar{display:none}
.vl-c{flex:none;width:min(58vw,240px);scroll-snap-align:start}
.vl-v{position:relative;display:block;width:100%;aspect-ratio:9/16;border:0;padding:0;border-radius:12px;overflow:hidden;background:#000;cursor:pointer}
.vl-v>img,.vl-v>iframe{position:absolute;inset:0;width:100%;height:100%;border:0;object-fit:cover}
.vl-v>iframe{pointer-events:none;background:transparent;opacity:0}
.vl-v>iframe.w{left:50%;width:316.05%;transform:translateX(-50%)}
.vl-c.on .vl-v>iframe.go{opacity:1}
.vl-v>i{position:absolute;z-index:2;font-style:normal;color:#fff;text-shadow:0 1px 3px #000}
.vl-s{left:8px;top:8px;max-width:calc(100% - 52px);padding:2px 7px;border-radius:6px;background:#000a;font-size:12px;font-weight:700;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.vl-m{right:8px;top:6px;font-size:18px}
.vl-p{left:50%;top:50%;transform:translate(-50%,-50%);font-size:44px;opacity:.9}
.vl-c.on .vl-p{display:none}
.vl-c:not(.on) .vl-m{display:none}
.vl-bar{position:absolute;z-index:2;left:0;bottom:0;height:3px;width:0;background:#e11d48}
.vl-t{display:-webkit-box;-webkit-line-clamp:3;-webkit-box-orient:vertical;overflow:hidden;margin-top:8px;color:var(--fg);font-weight:700;font-size:var(--fs-meta);line-height:var(--lh-meta)}
.vl-t:hover{text-decoration:underline}
.vl-hold{flex:none;width:min(58vw,240px)}
.vl-c.fs{position:fixed;inset:0;z-index:2147483000;width:auto;margin:0;background:#000;touch-action:none}
.vl-c.fs .vl-v{position:absolute;inset:0;height:100%;aspect-ratio:auto;border-radius:0}
@media(orientation:landscape){.vl-c.fs .vl-v>img{object-fit:contain}}
.vl-c.fs .vl-v:has(>iframe.w)>img{object-fit:contain}
.vl-c.fs .vl-v>iframe.w{left:0;width:100%;transform:none}
.vl-c.fs .vl-m{display:none}
.vl-c.fs .vl-s{left:12px;top:calc(14px + env(safe-area-inset-top));font-size:14px}
.vl-c.fs.ps .vl-p{display:block;font-size:64px}
.vl-c.fs .vl-bar{z-index:4;height:4px}
.vl-c.fs .vl-t{position:absolute;z-index:3;left:0;right:0;bottom:0;margin:0;padding:48px 16px calc(18px + env(safe-area-inset-bottom));background:linear-gradient(#0000,#000c);color:#fff;font-size:16px;line-height:1.4;pointer-events:none;text-decoration:none}
.vl-fx{position:absolute;z-index:5;right:12px;width:44px;height:44px;border:0;border-radius:50%;padding:0;background:#0009;color:#fff;font-size:20px;line-height:44px;cursor:pointer}
.vl-fx.x{top:calc(12px + env(safe-area-inset-top))}
.vl-fx.snd{top:calc(64px + env(safe-area-inset-top))}`;
const LABEL = "Videonu tam ekranda aç", LABEL_FS = "Videonu dayandır və ya davam etdir";
const SCROLL_KEYS = ["ArrowUp", "ArrowDown", "PageUp", "PageDown", "Home", "End", " "];

// Kartlar: üç mənbə növbə ilə (öz, X, TV), hər biri ən yenisi əvvəl; eyni video bir dəfə.
export function pick(S, reels) {
  const yt = (S?.video?.items || []).filter(v => ID.test(v?.videoId || "")).map(v => ({
    kind: "yt", id: v.videoId, t: v.publishedAt, title: v.title, src: v.channel === OWN ? "8ulduz.az" : v.channel, own: v.channel === OWN,
    tall: v.channel === OWN || /\/shorts\//.test(v.url || "") }));
  const x = L.list(S, reels).filter(v => MP4.test(v.u) && v.m === "xeber" && v.q !== "u").map(v => ({
    kind: "x", u: v.u, k: v.k, t: v.t, title: v.title || v.c, src: v.n, i: v.i }));
  const lanes = [yt.filter(v => v.own), x, yt.filter(v => !v.own)].map(l => l.filter(v => v.title).sort((a, b) => time(b) - time(a)));
  const out = [], seen = new Set();
  for (let r = 0; out.length < MAX && lanes.some(l => l.length > r); r++)
    for (const l of lanes) { const v = l[r]; if (v && !seen.has(v.id || v.u) && seen.add(v.id || v.u) && out.length < MAX) out.push(v); }
  return out;
}

const card = (v, n) => {
  const [src, alt] = poster(v);
  return `<div class="vl-c" data-n="${n}"><button type="button" class="vl-v" aria-label="${LABEL}">${src ? `<img src="${esc(src)}"${alt ? ` data-alt="${esc(alt)}"` : ""} alt="" loading="lazy" decoding="async" referrerpolicy="no-referrer">` : ""}<i class="vl-s">${esc(v.src)}</i><i class="vl-m">🔇</i><i class="vl-p">▶</i><span class="vl-bar"></span></button><a class="vl-t" href="${v.kind === "yt" ? `#/videolent?v=${encodeURIComponent(v.id)}` : "#/videolent"}" data-vl="${n}">${esc(v.title)}</a></div>`;
};

export async function mount(sec, S, still = () => false) {
  if (sec._vl) return;
  sec._vl = {};
  if (!document.getElementById("vl-css")) { const st = document.createElement("style"); st.id = "vl-css"; st.textContent = CSS; document.head.append(st); }
  if (!L.list || !L.load) { const m = await freshLent(); if (!m) { sec.remove(); return; } L = m; }
  const items = pick(S, await L.load().catch(() => []));
  if (!items.length) { sec.remove(); return; }
  const row = document.createElement("div");
  row.className = "vl-row";
  row.innerHTML = items.map(card).join("");
  row.querySelectorAll("img[data-alt]").forEach(im => im.addEventListener("error", () => { if (im.dataset.alt) { im.src = im.dataset.alt; im.dataset.alt = ""; } }));
  sec.append(row);
  sec.style.minHeight = "";
  const cards = [...row.children], seen = new Map(), players = new Map();
  const auto = () => !navigator.connection?.saveData && !still();
  let cur = -1, sound = false, timer = 0, user = false, hold = 0, lock = 0;
  // Tam ekran: açıq kartın nömrəsi (-1 — bağlı), dayandırılıb/bitib, lentdəki yerini tutan boş yer, əsl tam ekran açılıbmı.
  let fs = -1, fsWait = false, fsEnd = false, spot = null, native = false;

  const icon = () => { const c = cards[cur]; if (!c) return; c.querySelector(".vl-m").textContent = sound ? "🔊" : "🔇"; const b = c.querySelector(".vl-fx.snd"); if (b) b.textContent = sound ? "🔊" : "🔇"; };
  const bar =(n, p) => { const b = cards[n]?.querySelector(".vl-bar"); if (b) b.style.width = `${Math.min(100, p * 100)}%`; };
  const ytCmd = (f, func) => f.contentWindow?.postMessage(JSON.stringify({ event: "command", func, args: [] }), "*");
  const videoOf = f => f.contentDocument?.querySelector("video");
  // Oynadıcını qurur (hələ oynatmır). X: video yüklənir; YouTube: oynadıcı açılır və vəziyyətini bildirməyə başlayır.
  function make(n) {
    if (players.has(n)) return players.get(n);
    const v = items[n], f = document.createElement("iframe");
    f.allow = "autoplay; encrypted-media; picture-in-picture";
    f.title = v.title;
    f.loading = "eager";
    f._ready = false;
    const ready = () => { f._ready = true; if (f._want) start(n); };
    if (v.kind === "yt") {
      if (!v.tall) f.className = "w";
      f.src = `${YT}${encodeURIComponent(v.id)}?autoplay=0&mute=1&playsinline=1&controls=0&rel=0&modestbranding=1&enablejsapi=1&origin=${encodeURIComponent(location.origin)}`;
      // Oynadıcı hazır olanda ilk mesajını göndərir (onReady/initialDelivery): «hazır» o vaxtdır, iframe-in «load»u erkəndir.
      const listen = () => f.isConnected && !f._ready && f.contentWindow?.postMessage(JSON.stringify({ event: "listening", id: "vl" + n, channel: "widget" }), "*");
      f._onMsg = ready;
      f.addEventListener("load", () => { listen(); setTimeout(listen, 500); setTimeout(listen, 1500); setTimeout(listen, 3000); }, { once: true });
    } else {
      // Kartda (eni ≤ 240 px) video kartı doldurur, tam ekranda (çərçivə enlidir) bütöv görünür: çərçivənin öz ölçüsünə görə.
      f.srcdoc = `<!doctype html><meta charset="utf-8"><meta name="referrer" content="no-referrer"><style>html,body{margin:0;height:100%;overflow:hidden;background:#000}video{width:100%;height:100%;object-fit:cover}@media(orientation:landscape){video{object-fit:contain}}</style><video playsinline muted preload="auto" src="${esc(v.u)}"></video>`;
      f.addEventListener("load", () => {
        const el = videoOf(f);
        if (el) {
          el.addEventListener("ended", () => n === cur && next());
          el.addEventListener("timeupdate", () => n === cur && el.duration > 0 && bar(n, el.currentTime / el.duration));
          el.addEventListener("playing", () => f.classList.add("go"));
        }
        ready();
      }, { once: true });
    }
    cards[n].querySelector(".vl-v").append(f);
    players.set(n, f);
    return f;
  }
  // Hazır oynadıcıya «oynat» (hazır deyilsə yüklənəndə).
  function start(n) {
    const f = players.get(n);
    if (!f || n !== cur) return;
    if (!f._ready) { f._want = true; return; }
    f._want = false;
    if (items[n].kind === "yt") { ytCmd(f, sound ? "unMute" : "mute"); ytCmd(f, "playVideo"); setTimeout(() => f.classList.add("go"), 250); }
    else {
      const el = videoOf(f);
      if (!el) return;
      el.muted = !sound;
      el.play().catch(() => { el.muted = true; sound = false; icon(); el.play().catch(() => {}); });
    }
  }
  const halt = n => { const f = players.get(n); if (f) { if (items[n].kind === "yt") ytCmd(f, "pauseVideo"); else videoOf(f)?.pause(); } };
  // Yalnız oynayan və növbəti kartın oynadıcısı qalır.
  const trim = keep => players.forEach((f, n) => { if (!keep.includes(n)) { f.remove(); players.delete(n); bar(n, 0); } });
  const nextOf = n => (n + 1) % cards.length;
  function stop() {
    clearTimeout(timer);
    if (cur >= 0) { cards[cur].classList.remove("on"); halt(cur); }
    cur = -1;
    trim([]);
  }
  function play(n) {
    if (document.hidden || !sec.isConnected) return;
    if (n === cur) return;
    if (cur >= 0) { cards[cur].classList.remove("on"); halt(cur); }
    clearTimeout(timer);
    cur = n;
    cards[n].classList.add("on");
    icon();
    make(n);
    start(n);
    const nx = nextOf(n);
    trim([n, nx]);
    if (auto() && nx !== n) make(nx);   // növbəti qabaqcadan
    timer = setTimeout(next, PLAY_MAX);
  }
  function next() {
    if (cur < 0) return;
    if (fs >= 0) { fsEnd = true; cards[fs].classList.add("ps"); return; }   // tam ekranda növbətiyə keçmir: ▶
    const n = nextOf(cur);
    lock = Date.now() + 1000;   // proqramla sürüşmə: görünüş yoxlaması əvvəlki kartı geri seçməsin
    row.scrollTo({ left: cards[n].offsetLeft - row.offsetLeft, behavior: "smooth" });
    play(n);
  }
  // YouTube oynadıcısı vəziyyətini postMessage ilə bildirir (iframe API skripti yüklənmir): 0 — bitdi, 1 — oynayır.
  addEventListener("message", e => {
    let n = -1;
    players.forEach((p, k) => { if (e.source && e.source === p.contentWindow) n = k; });
    if (n < 0) return;
    const f = players.get(n);
    if (!f._ready) f._onMsg?.();
    if (n !== cur) return;
    let d; try { d = typeof e.data === "string" ? JSON.parse(e.data) : e.data; } catch { return; }
    const i = d?.info, st = d?.event === "onStateChange" ? i : i?.playerState;
    if (st === 0) next();
    else if (st === 1) f.classList.add("go");
    if (i?.duration > 0 && i.currentTime >= 0) bar(cur, i.currentTime / i.duration);
  });
  const setSound = on => {
    sound = on;
    const f = players.get(cur);
    if (!f) return;
    icon();
    if (items[cur].kind === "yt") ytCmd(f, on ? "unMute" : "mute");
    else { const el = videoOf(f); if (el) { el.muted = !on; if (!fsWait && !fsEnd) el.play().catch(() => {}); } }
  };

  // Tam ekran (yuxarıdakı şərh). Basma istifadəçinin hərəkətidir: səs və əsl tam ekran ancaq onun içində açılır.
  // Arxadakı səhifə sürüşmür: dinləyicilər yalnız tam ekran açıq ikən kartdadır (lentin öz sürüşməsini ləngitməsin), overflow
  // dəyişmir (kompüterdə zolağı götürüb səhifəni tərpədərdi).
  const noScroll = e => e.preventDefault();
  function openFs(n) {
    if (fs >= 0) return;
    const c = cards[n];
    user = true;
    if (n !== cur) { sound = true; play(n); } else setSound(true);   // oynayan kart: olduğu yerdən davam
    if (cur !== n) return;
    clearTimeout(timer);
    fs = n; fsWait = fsEnd = false;
    spot = document.createElement("div");
    spot.className = "vl-c vl-hold";
    spot.style.height = c.offsetHeight + "px";
    c.before(spot);
    c.classList.add("fs");
    c.addEventListener("wheel", noScroll, { passive: false });
    c.addEventListener("touchmove", noScroll, { passive: false });
    c.setAttribute("role", "dialog");
    c.setAttribute("aria-modal", "true");
    c.setAttribute("aria-label", items[n].title);
    c.querySelector(".vl-v").setAttribute("aria-label", LABEL_FS);
    c.insertAdjacentHTML("beforeend", `<button type="button" class="vl-fx x" aria-label="Bağla">✕</button><button type="button" class="vl-fx snd" aria-label="Səsi aç və ya bağla">${sound ? "🔊" : "🔇"}</button>`);
    history.pushState({ vlfs: 1 }, "");
    native = false;
    if (document.fullscreenEnabled && c.requestFullscreen) c.requestFullscreen().then(() => { native = fs === n; }).catch(() => {});
    c.querySelector(".vl-fx.x").focus({ preventScroll: true });
  }
  function closeFs() {
    if (fs < 0) return;
    const c = cards[fs], ended = fsEnd, waited = fsWait;
    setSound(false);   // lentdə səssiz davam edir (dayanmış video bu əmrlə oynamır)
    fs = -1; fsWait = fsEnd = false; native = false;
    c.removeEventListener("wheel", noScroll);
    c.removeEventListener("touchmove", noScroll);
    if (document.fullscreenElement) document.exitFullscreen().catch(() => {});
    // Yerinə qayıdan kart iki kadr görünmür: geri düyməsi «giriş» sayılmır, kartın qayıtması CLS-ə yazılardı.
    c.style.visibility = "hidden";
    c.classList.remove("fs", "ps");
    ["role", "aria-modal", "aria-label"].forEach(a => c.removeAttribute(a));
    c.querySelectorAll(".vl-fx").forEach(b => b.remove());
    spot?.remove(); spot = null;
    const b = c.querySelector(".vl-v");
    b.setAttribute("aria-label", LABEL);
    requestAnimationFrame(() => requestAnimationFrame(() => { c.style.visibility = ""; if (fs < 0) b.focus({ preventScroll: true }); }));
    if (!auto()) stop();
    else if (ended) next();
    else { if (waited) start(cur); timer = setTimeout(next, PLAY_MAX); }
  }
  const back = () => history.state?.vlfs ? history.back() : closeFs();
  function fsToggle() {
    if (fs < 0 || fs !== cur) return;
    if (fsWait || fsEnd) { fsWait = fsEnd = false; cards[fs].classList.remove("ps"); start(fs); }
    else { fsWait = true; cards[fs].classList.add("ps"); halt(fs); }
  }
  document.addEventListener("keydown", e => {
    if (fs < 0) return;
    if (e.key === "Escape") { e.preventDefault(); back(); }
    else if (SCROLL_KEYS.includes(e.key) && !(e.key === " " && e.target.closest?.("button"))) e.preventDefault();
  });
  document.addEventListener("fullscreenchange", () => { if (native && fs >= 0 && !document.fullscreenElement) back(); });

  // Görünən (ən azı 60%) ən soldakı kart oynayır; heç biri görünmürsə dayanır. Əl ilə sürüşdürəndə 0,6 s gözləyir.
  const pickVisible = () => {
    if (fs >= 0 || (!auto() && !user) || Date.now() < lock) return;
    if (cur >= 0 && (seen.get(cur) || 0) >= 0.6) return;   // oynayan kart görünürsə dəyişmir (kompüterdə 4 kart birdən görünür)
    const best = [...seen].filter(([, r]) => r >= 0.6).sort((a, b) => a[0] - b[0])[0]?.[0] ?? -1;   // ən soldakı
    if (best < 0) stop(); else play(best);
  };
  const io = new IntersectionObserver(es => {
    es.forEach(e => seen.set(Number(e.target.dataset.n), e.isIntersecting ? e.intersectionRatio : 0));
    clearTimeout(hold); hold = setTimeout(pickVisible, 120);
  }, { threshold: [0, 0.6, 0.9] });
  cards.forEach(c => io.observe(c));
  row.addEventListener("scroll", () => { clearTimeout(hold); hold = setTimeout(pickVisible, 600); }, { passive: true });
  document.addEventListener("visibilitychange", () => {
    if (fs >= 0) { if (document.hidden && !fsWait && !fsEnd) fsToggle(); return; }   // tam ekran: dayanır, ▶ ilə davam
    document.hidden ? stop() : pickVisible();
  });

  row.addEventListener("click", e => {
    const t = e.target.closest("[data-vl]"), b = e.target.closest(".vl-v"), fx = e.target.closest(".vl-fx");
    if (fs >= 0) {
      if (fx?.classList.contains("x")) back();
      else if (fx) setSound(!sound);
      else if (b || t) { e.preventDefault(); fsToggle(); }
      return;
    }
    if (t) {
      const v = items[Number(t.dataset.vl)];
      if (v.kind === "x") { e.preventDefault(); stop(); import("./lent.js?v=1").then(m => m.open(S, v.k)).catch(() => {}); }
      return;
    }
    if (!b) return;
    openFs(Number(b.parentElement.dataset.n));
  });
  addEventListener("popstate", () => { if (fs >= 0) closeFs(); });   // geri düyməsi tam ekranı bağlayır
  addEventListener("popstate", () => setTimeout(pickVisible, 300));   // Videolent bağlananda lent davam edir
}
