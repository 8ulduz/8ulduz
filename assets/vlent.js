// Video lenti (sahib, 2026-11-24): «Son xəbərlərdən sonra şəkildəki formatda daimi oynayan video xəbərlər olsun. oraya x dan yeni
// olan hadisə və xəbər videoları da salmaq olar öz videolarımızı da, saytların videolarını da». Nümunə: üfüqi sürüşən şaquli kartlar,
// altında başlıq. Görünən ən soldakı kart səssiz öz-özünə oynayır, bitəndə (ən çoxu PLAY_MAX) lent növbəti karta keçir, sonuncudan
// sonra birinciyə qayıdır. Başlığa basanda tam oynadıcı açılır: X videosu Videolentdə (lent.js), YouTube videosu video səhifəsində.
// YouTube kartı (telekanallar) telefonda özü oynamır, lent onun üstündən keçir; basanda tam ekranda açılır (sahib, 2026-11-26, «A»; nextOf).
// Kompüterdə (siçan) belə deyil — sahib, 2026-11-25: «video xəbər kompda kursor üzərinə aparılanda oynamalı idi … yalnız kursor üstünə
// aparılanda başlasın oynamağa avtomatik yox, kursoru çəkəndə dayansın»: zolaq özü oynamır, kursorun altındakı kart oynayır (hover).
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
//    üfüqi videoların şəkli hq720.jpg (zolaqsız), yoxdursa mqdefault.jpg. Şəkillər şəkil keşindən (img.8ulduz.az) 360 px-ə kiçilir;
//    alınmasa app.js (viaWsrv) eyni sorğunu wsrv.nl-dən, o da alınmasa buradakı data-alt orijinalı verir.
//
// Tənbəl modul: app.js bölmə ekrana yaxınlaşanda yükləyir (setupVlent), ilk açılışa fayl, sorğu, iş gətirmir. Eyni anda bir video
// oynayır, ən çoxu iki oynadıcı (oynayan və növbəti) var; qalanları silinir. Qənaət rejimində (Save-Data) və «hərəkəti azalt»
// seçiləndə (saytın düyməsi və ya cihaz) avtomatik oynamır və qabaqcadan yükləmir, kart basılanda oynayır.
//
// Mənbələr (qarışıq, ən yenisi əvvəl — pick):
//  - öz videolarımız: YouTube «8ULDUZ» kanalı (data/video.json, updater.YT_NEWS). Veb nüsxəsi olan video («mp4» sahəsi, ownMp4)
//    YouTube oynadıcısı ilə yox, X videosu kimi adi <video> ilə oynayır (sahib, 2026-11-25: «video xəbərlərdə bəzi videolar (əsasən
//    azərbaycan) 1-2 saniyəyə açılır … gözqırpımı»). YouTube kartı basışdan ilk kadra 1,7–2,4 s gedirdi, telefonda qara ekran, fırlanan
//    dairə, ⏸ və «Shorts» yazısı görünürdü. Nüsxəni sosial-video.yml «veb-video» işi Cloudflare R2-yə yazır (.github/scripts/veb-video.cjs),
//    updater.py ünvanı video.json-a köçürür (ownMp4). Nüsxə yoxdursa (köhnə video, R2 qurulmayıb) video YouTube-dan oynayır. Şəkli və başlığın
//    keçidi (video səhifəsi) YouTube-dakı kimidir;
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
// Öz videomuzun veb nüsxəsi: yalnız öz domenimiz və videonun öz YouTube nömrəsi ilə adlanan fayl (veb-video.cjs BASE).
const OWN_BASE = "https://video.8ulduz.az/";
export const ownMp4 = v => ID.test(v?.videoId || "") && v.mp4 === `${OWN_BASE}${v.videoId}.mp4`;
const esc = s => String(s ?? "").replace(/[&<>"']/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[c]);
const px = u => `https://img.8ulduz.az/?url=${encodeURIComponent(u)}&w=360&we&output=webp&q=70`;
const time = v => Date.parse(v.t) || 0;
// Kartın şəkli və alınmasa ehtiyatı (YouTube və öz videomuzun veb nüsxəsi: video nömrəsindən).
export const poster = v => v.kind === "x" ? [/^https:\/\//.test(v.i || "") ? px(v.i) : "", ""]
  : [px(`https://i.ytimg.com/vi/${v.id}/${v.tall ? "oar2" : "hq720"}.jpg`), `https://i.ytimg.com/vi/${v.id}/${v.tall ? "hqdefault" : "mqdefault"}.jpg`];

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

// Kartlar: ən yeni video həmişə birinci (sahib 2026-11-25: «videolar köhnədir yenisi gəlməlidir önə daima»), hansı mənbədən olursa
// olsun; eyni vaxtda öz, X, TV. Əvvəl üç mənbə növbə ilə gəlirdi və hər üçüncü kart öz videomuz idi: YouTube yükləməsi dayananda
// (kanalın həddi) zolağın 1, 4, 7…-ci kartları 23–30 saatlıq idi, qalanları 0,5–2 saatlıq (canlı, 2026-11-25). Eyni video bir dəfə.
// Öz videomuzun veb nüsxəsi varsa növü «mp4»: oynadıcısı X videosununku kimidir (make, start, halt — «yt» olmayan yol), şəkli və
// keçidi YouTube-dakı kimi.
export function pick(S, reels) {
  const yt = (S?.video?.items || []).filter(v => ID.test(v?.videoId || "")).map(v => {
    const own = v.channel === OWN, mp4 = own && ownMp4(v);
    return { kind: mp4 ? "mp4" : "yt", ...(mp4 ? { u: v.mp4 } : {}), id: v.videoId, t: v.publishedAt, title: v.title, src: own ? "8ulduz.az" : v.channel, own,
      tall: own || /\/shorts\//.test(v.url || "") };
  });
  const x = L.list(S, reels).filter(v => MP4.test(v.u) && v.m === "xeber" && v.q !== "u").map(v => ({
    kind: "x", u: v.u, k: v.k, t: v.t, title: v.title || v.c, src: v.n, i: v.i }));
  const all = [...yt.filter(v => v.own), ...x, ...yt.filter(v => !v.own)].filter(v => v.title).sort((a, b) => time(b) - time(a));
  const out = [], seen = new Set();
  for (const v of all) if (out.length < MAX && !seen.has(v.id || v.u) && seen.add(v.id || v.u)) out.push(v);
  return out;
}

const card = (v, n) => {
  const [src, alt] = poster(v);
  return `<div class="vl-c" data-n="${n}"><button type="button" class="vl-v" aria-label="${LABEL}">${src ? `<img src="${esc(src)}"${alt ? ` data-alt="${esc(alt)}"` : ""} alt="" loading="lazy" decoding="async" referrerpolicy="no-referrer">` : ""}<i class="vl-s">${esc(v.src)}</i><i class="vl-m">🔇</i><i class="vl-p">▶</i><span class="vl-bar"></span></button><a class="vl-t" href="${v.kind === "x" ? "#/videolent" : `#/videolent?v=${encodeURIComponent(v.id)}`}" data-vl="${n}">${esc(v.title)}</a></div>`;
};

// Zolaq yenilənir (sahib 2026-11-25: «saytdakı video xəbərlər niyə yenilənmir?»). Əvvəl kartlar səhifə açılanda bir dəfə qurulurdu:
// telefonda sayt saatlarla açıq qalır (və ana səhifə geri qayıdanda yaddaşdan qoyulur), zolaq isə köhnə videoları göstərirdi; video
// siyahısı (data/video.json) xəbərlərdən gec gələndə TV videoları heç düşmürdü. İndi FRESH-dən bir (vərəq və zolaq görünəndə) siyahı
// yoxlanır; dəyişibsə zolaq yenidən qurulur — oynayan və görünən videonu kəsmədən (swap).
const FRESH = 5 * 60e3, EARLY = 15e3;
export async function mount(sec, S, still = () => false, given = null) {
  if (sec._vl && !given) return;
  sec._vl = {};
  if (!document.getElementById("vl-css")) { const st = document.createElement("style"); st.id = "vl-css"; st.textContent = CSS; document.head.append(st); }
  if (!L.list || !L.load) { const m = await freshLent(); if (!m) { sec.remove(); return; } L = m; }
  const items = given || pick(S, await L.load().catch(() => []));
  if (!items.length) { sec.remove(); return; }
  const row = document.createElement("div");
  row.className = "vl-row";
  row.innerHTML = items.map(card).join("");
  row.querySelectorAll("img[data-alt]").forEach(im => im.addEventListener("error", () => { if (im.dataset.alt) { im.src = im.dataset.alt; im.dataset.alt = ""; } }));
  const old = sec.querySelector(".vl-row");
  if (old) old.replaceWith(row); else sec.append(row);
  sec.style.minHeight = "";
  const cards = [...row.children], seen = new Map(), players = new Map();
  const auto = () => !navigator.connection?.saveData && !still();
  // Kompüter (sahib 2026-11-25, yuxarıda): zolaq özü oynamır və növbəti karta keçmir, qabaqcadan oynadıcı qurmur. Kursor kartın
  // üstünə gələn kimi o video səssiz oynayır, çəkiləndə dayanır (oynadıcı qalır: qayıdanda olduğu yerdən dərhal davam edir), bitəndə
  // yenidən başlayır. Telefon və planşetdə (kursor yoxdur) əvvəlki kimi görünən kart özü oynayır.
  const hover = matchMedia("(hover:hover) and (pointer:fine)").matches;
  let cur = -1, sound = false, timer = 0, user = false, hold = 0, lock = 0;
  // Tam ekran: açıq kartın nömrəsi (-1 — bağlı), dayandırılıb/bitib, lentdəki yerini tutan boş yer, əsl tam ekran açılıbmı.
  let fs = -1, fsWait = false, fsEnd = false, spot = null, native = false;
  // Səhifəyə bağlı dinləyicilər yenidən qurulanda bu siqnalla silinir.
  const ac = new AbortController(), on = { signal: ac.signal };

  const icon = () => { const c = cards[cur]; if (!c) return; c.querySelector(".vl-m").textContent = sound ? "🔊" : "🔇"; const b = c.querySelector(".vl-fx.snd"); if (b) b.textContent = sound ? "🔊" : "🔇"; };
  const bar =(n, p) => { const b = cards[n]?.querySelector(".vl-bar"); if (b) b.style.width = `${Math.min(100, p * 100)}%`; };
  const ytCmd = (f, func) => f.contentWindow?.postMessage(JSON.stringify({ event: "command", func, args: [] }), "*");
  // Növbəti YouTube videosu qabaqcadan hazırlanır (sahib 2026-11-25: «video xəbərlərdə bəzi videolar (əsasən azərbaycan) 1-2 saniyəyə
  // açılır … gözqırpımı»). Ölçü (canlı sayt): oynadıcı hazır olsa da video axını yalnız «oynat»dan sonra gəlirdi — basışdan ilk kadra
  // 1,7 s (oynadıcı da yoxdursa 2,4 s). Hazır, amma seçilməmiş oynadıcı səssiz başladılır və ilk kadrda dayandırılır
  // (mesaj dinləyicisi): seçiləndə video yaddaşdan dərhal oynayır. Əvvələ qaytarılmır: seekTo axını yenidən yükləyir (ölçü: +0,5 s). X videosu onsuz da qabaqcadan yüklənir (preload="auto").
  // Qənaət rejimində (auto() yox) oynadıcı qabaqcadan qurulmur, deməli hazırlanmır da.
  const prime = n => { const f = players.get(n); if (f && n !== cur && items[n].kind === "yt" && !f._prime) { f._prime = 1; ytCmd(f, "mute"); ytCmd(f, "playVideo"); } };
  const videoOf = f => f.contentDocument?.querySelector("video");
  // Oynadıcını qurur (hələ oynatmır). X və öz veb nüsxəmiz (mp4): video yüklənir; YouTube: oynadıcı açılır və vəziyyətini bildirməyə başlayır.
  function make(n) {
    if (players.has(n)) return players.get(n);
    const v = items[n], f = document.createElement("iframe");
    f.allow = "autoplay; encrypted-media; picture-in-picture";
    f.title = v.title;
    f.loading = "eager";
    f._ready = false;
    const ready = () => { f._ready = true; if (f._want) start(n); else prime(n); };
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
    f._prime = 3;   // seçildi: hazırlıq dayandırması daha lazım deyil
    // YouTube oynadıcısı yalnız «oynayır» (vəziyyət 1) xəbəri gələndə görünür, o vaxta qədər kartda şəkil qalır (sahib 2026-11-25, telefon
    // ekranının videosu: ARB 24, Real TV, 8ulduz kartlarında qara ekran, fırlanan dairə və «Shorts» yazısı). Əvvəl oynadıcı 100–250 ms-dən
    // sonra açılırdı. Ölçü (telefon görünüşü): video 380–520 ms-də başlayır, arada YouTube-un yükləmə ekranı görünürdü; telefon
    // internetində bu ara saniyələrlə olur.
    if (items[n].kind === "yt") { ytCmd(f, sound ? "unMute" : "mute"); ytCmd(f, "playVideo"); }
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
  // YouTube kartı (telekanallar) telefonda özü oynamır, yalnız şəkli və ▶ görünür; basanda tam ekranda səslə açılır (sahib, 2026-11-26:
  // «A: avtomatik oynamasın»). YouTube oynadıcısı hər başlayanda ~3,5 s öz ⏸ işarəsini, kanal adını və «Shorts» yazısını göstərir,
  // parametrlə söndürülmür, üstünü örtmək YouTube-un qaydasına ziddir. Lent öz videolarımızı (veb nüsxəsi) və X videolarını oynadır,
  // YouTube kartlarının üstündən keçir. Kompüterdə kursorla oynatma (sahib, 2026-11-25) dəyişmir.
  const ok = n => items[n].kind !== "yt";
  const nextOf = n => { for (let k = 1; k <= cards.length; k++) { const m = (n + k) % cards.length; if (ok(m)) return m; } return n; };   // növbəti özü oynayan kart (yoxdursa n)
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
    if (hover) { trim([n, ...[...players.keys()].filter(k => k !== n).slice(-3)]); return; }   // kompüter: son kursor kartları hazır qalır
    trim([n, nx]);
    if (auto() && nx !== n) make(nx);   // növbəti qabaqcadan
    timer = setTimeout(next, PLAY_MAX);
  }
  // Kompüter: kursor çəkildi — video dayanır, kartda yenə şəkli görünür; oynadıcı silinmir.
  function rest() {
    if (cur < 0) return;
    cards[cur].classList.remove("on");
    halt(cur);
    cur = -1;
  }
  // Kompüter: kursorun altındakı video bitəndə yenidən başlayır (YouTube: bitmiş videoya «oynat» əvvəldən başladır).
  const again = n => {
    const f = players.get(n);
    if (!f) return;
    if (items[n].kind === "yt") ytCmd(f, "playVideo");
    else { const el = videoOf(f); if (el) { el.currentTime = 0; el.play().catch(() => {}); } }
  };
  function next() {
    if (cur < 0) return;
    if (fs >= 0) { fsEnd = true; cards[fs].classList.add("ps"); return; }   // tam ekranda növbətiyə keçmir: ▶
    if (hover) { again(cur); return; }   // kompüter: zolaq tərpənmir
    const n = nextOf(cur);
    if (n === cur) { if (ok(cur)) again(cur); else stop(); return; }   // özü oynayan başqa kart yoxdur
    if (n < cur && swap(true)) return;   // dövr başa çatdı: yeni siyahı varsa zolaq ondan başlayır
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
    let d; try { d = typeof e.data === "string" ? JSON.parse(e.data) : e.data; } catch { return; }
    const i = d?.info, st = d?.event === "onStateChange" ? i : i?.playerState;
    if (n !== cur) {   // hazırlanan oynadıcı: ilk kadr gəldi — dayanır
      if (st === 1 && f._prime === 1) { f._prime = 2; ytCmd(f, "pauseVideo"); }
      return;
    }
    if (st === 0) next();
    else if (st === 1) f.classList.add("go");
    if (i?.duration > 0 && i.currentTime >= 0) bar(cur, i.currentTime / i.duration);
  }, on);
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
    else if (hover && !c.matches(":hover")) rest();   // kompüter: kursor kartda deyil — dayanır
    else if (ended) next();
    else { if (waited) start(cur); if (!hover) timer = setTimeout(next, PLAY_MAX); }
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
  }, on);
  document.addEventListener("fullscreenchange", () => { if (native && fs >= 0 && !document.fullscreenElement) back(); }, on);

  // Görünən (ən azı 60%) ən soldakı kart oynayır; heç biri görünmürsə dayanır. Əl ilə sürüşdürəndə 0,6 s gözləyir.
  const visible = () => [...seen.values()].some(r => r > 0.1);
  const pickVisible = () => {
    if (hover) { if (fs < 0 && cur >= 0 && (seen.get(cur) || 0) < 0.1) rest(); return; }   // kompüter: yalnız kursor oynadır
    if (fs >= 0 || (!auto() && !user) || Date.now() < lock) return;
    if (cur >= 0 && (seen.get(cur) || 0) >= 0.6) return;   // oynayan kart görünürsə dəyişmir (kompüterdə 4 kart birdən görünür)
    const best = [...seen].filter(([n, r]) => r >= 0.6 && ok(n)).sort((a, b) => a[0] - b[0])[0]?.[0] ?? -1;   // ən soldakı özü oynayan
    if (best < 0) stop(); else play(best);
  };
  const io = new IntersectionObserver(es => {
    const was = visible();
    es.forEach(e => seen.set(Number(e.target.dataset.n), e.isIntersecting ? e.intersectionRatio : 0));
    if (!was && visible()) shownAt = Date.now();   // zolaq yenicə göründü (səhifə sürüşdü, ana səhifəyə qayıdış)
    if (swap()) return;
    fresh();
    clearTimeout(hold); hold = setTimeout(pickVisible, 120);
  }, { threshold: [0, 0.6, 0.9] });
  cards.forEach(c => io.observe(c));
  // Birinci kartın oynadıcısı zolaq ekrana yaxınlaşanda qurulur (modul ~900 px qabaqdan yüklənir), görünəndə yox: video ekrana çatanda
  // hazırdır (sahib, 2026-11-26: «videoların gec oynaması … gözqırpımı»). Ölçü: YouTube kartı görünəndən oynamağa 3,9 s gedirdi.
  // İlk iki kartdan (telefonda görünənlər) özü oynayan birincisi; YouTube kartı özü oynamır.
  const first = [0, 1].find(k => k < items.length && ok(k));
  if (!hover && auto() && !given && first != null) make(first);
  row.addEventListener("scroll", () => { clearTimeout(hold); hold = setTimeout(pickVisible, 600); }, { passive: true });
  document.addEventListener("visibilitychange", () => {
    if (fs >= 0) { if (document.hidden && !fsWait && !fsEnd) fsToggle(); return; }   // tam ekran: dayanır, ▶ ilə davam
    if (document.hidden) stop();
    else if (due) fresh().then(() => { if (!ac.signal.aborted && cur < 0) pickVisible(); });   // əvvəl yenilənmə, sonra oynatma
    else pickVisible();
  }, on);

  // Kompüter: kursor kartın üstünə gələn kimi o video oynayır, kartdan çıxanda dayanır (hover). Əsas göstəricisi barmaq olan cihazda
  // (planşetə siçan qoşulanda) kursor yalnız kartın oynadıcısını qabaqcadan qurur, basış adətən bundan sonradır.
  row.addEventListener("pointerover", e => {
    if (e.pointerType !== "mouse" || fs >= 0 || !auto()) return;
    const n = Number(e.target.closest(".vl-c")?.dataset.n ?? -1);
    if (n >= 0 && hover) play(n);
    else if (n >= 0 && n !== cur && !players.has(n) && players.size < 4) make(n);
  }, { passive: true });
  row.addEventListener("pointerout", e => {
    if (!hover || e.pointerType !== "mouse" || fs >= 0 || cur < 0 || cards[cur].contains(e.relatedTarget)) return;
    rest();
  }, { passive: true });
  row.addEventListener("pointerleave", () => { if (hover) setTimeout(swap, 50); }, { passive: true });   // gözləyən yeni siyahı kursor zolaqdan çıxanda

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
  addEventListener("popstate", () => { if (fs >= 0) closeFs(); }, on);   // geri düyməsi tam ekranı bağlayır
  addEventListener("popstate", () => setTimeout(pickVisible, 300), on);   // Videolent bağlananda lent davam edir

  // Yenilənmə (yuxarıdakı FRESH şərhi). Yeni siyahı gözləyir (pending), zolaq bunlardan birində yenidən qurulur:
  // vərəq gizlidir, ana səhifə ekranda deyil, zolaq görünmür, heç nə oynamır, zolaq təzə qurulub və oxucu hələ toxunmayıb (EARLY),
  // ya da lent sonuncu kartdan birinciyə qayıdır (next). Tam ekran açıqdırsa və ya oxucu zolaqda irəlidədirsə gözləyir.
  const builtAt = Date.now(), key = l => l.map(v => v.id || v.u).join(" ");
  let pending = null, due = false, checking = false, waits = 0, shownAt = builtAt, touched = 0;
  row.addEventListener("pointerdown", () => { touched = Date.now(); }, { passive: true });
  function swap(force = false) {
    if (!pending || fs >= 0 || ac.signal.aborted) return false;
    const since = Math.max(builtAt, shownAt), early = Date.now() - since < EARLY && touched < since;   // təzə göstərilib, toxunulmayıb
    const quiet = document.hidden || !sec.isConnected || cur < 0 || !visible() || early;
    if (!quiet && !force) return false;
    if (hover && row.matches(":hover") && !force) return false;   // kompüter: kursor zolaqdadırsa kartlar altında dəyişmir
    const list = pending;
    pending = null;
    stop(); io.disconnect(); clearTimeout(hold); clearInterval(tick); clearInterval(wait); ac.abort();
    mount(sec, S, still, list);
    return true;
  }
  async function fresh() {
    if (!due || checking || document.hidden || !sec.isConnected || !visible() || ac.signal.aborted) return;
    due = false; checking = true;
    try {
      const list = pick(S, await L.load().catch(() => []));
      if (list.length && key(list) !== key(items)) { pending = list; swap(); }
    } finally { checking = false; }
  }
  const tick = setInterval(() => { due = true; fresh(); swap(); }, FRESH);
  // Video siyahısı (S.video) zolaqdan gec gəlibsə: gələn kimi yoxlanır (ən çoxu 30 s gözlənir).
  const wait = setInterval(() => { if (S?.video || ++waits > 30) { clearInterval(wait); if (S?.video) { due = true; fresh(); } } }, 1000);
  sec._vl.fresh = () => { due = true; fresh(); };
}
