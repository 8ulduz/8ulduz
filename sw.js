/* 8ulduz — GitHub Pages alt yolu /8ulduz/ (və lokal eyni quruluş).
   Canlı fayllar (status, latest, markets): əvvəl live budağı (dəqiqəlik), sonra sayt, sonra ehtiyat kanal.
   Qalan data/*.json: əvvəl sayt, alınmasa ehtiyat kanal (GitHub raw). Keş yalnız hamısı alınmayanda (oflayn).
   HTML/JS/CSS: saxlanmış nüsxə dərhal, təzəsi arxada (cachedShell). Şəkillər: əvvəl keş. */
const VERSION = "v102"; // v102: mövzu mətni sürətli (Transfer/Futbol ilk açılış ~35% tez); // v101: köhnə keçid arxivdən gəlir, lent arada yüklənsə də; // v100: paylaşma keçidində xəbərin saatı (?h=), köhnə keçid arxiv budağından açılır; // v99: köhnə paylaşma keçidi 30 günlük xəbər səhifəsinə, səhifə xəbərin sətrini özündə gətirir; // v98: xəbərin sonunda və izlə pəncərəsində Telegram mövzu düyməsi; // v97: axtarışda «Telegram-da izlə» (istənilən mövzu); // v96: klub səhifəsində «Telegram-da izlə»; // v95: «Telegram-da izlə» düyməsi (@sekkizulduz_xeber_bot); // v67: #/bolme/bolgeler?m=Quba keçidi mövzunu açır (rayon/idman səhifələri); v66: GA4 yüngül göndərici (assets/ga.js, sayt açılandan sonra); v65: ilk açılış telefonun rejimi ilə (seçim yoxdursa); v64: 3 rəng (göy, qızılı, qırmızı), açıq rejim ağımtıl, telefonda valyutada faiz yerinə ox; v63: telefonda məzənnə zolağının əvvəlki dörd kartlı formatı qaytarıldı (rənglər qalır); v62: telefonda bir sətir bölmə (Son dəqiqə, Gündəm, İdman, Zuğulba) və ☰ — bütün bölmələr aşağıdan siyahı ilə; v61: telefonda məzənnə zolağında 3 kart (qiymət tam) və › düyməsi, qızıl/gümüş/neft öz rəngində; v60: telefonda bölmələr 3 sətirdə, altında «Günün 10 əsas xəbəri — Telegram-da»; v56: Facebook düyməsi botun yazdığı «8ulduz» səhifəsinə; v55: sürət (telefonda siyahı 6 kartla, bölmə/liqa keçidi lenti gözləmir, loqolar proksidən); v54: compact follow controls, brighter faster glow, sports menu colors; v53: Telegram düymələri 8ULDUZ kanalına (t.me/sekkizulduz_az); v52: anchored follow popover, Instagram and yellow-blue opacity glow; v51: owner article removal panel and configured mobile follow links; v50: v49 (altlıqda saytın hesabları) sahibin istəyi ilə geri alındı; v48: liqa səhifəsi faylı gələn kimi çəkilir; v47: liqa səhifəsi paralel yüklənir (idman modulu əvvəlcədən); v46: namaz işarələri sprite-da, gec dolan Zuğulba/slayder; v45: telefonda «Paylaş» sistem pəncərəsi; v44: rəsmi hesablar Chrome Custom Tab kimi; v43: telefonda yenə «Paylaş» düyməsi, rəsmi hesablar Chrome vərəqində; v42: məlumat cavabı keş yazısını gözləmir; v41: /x/ID paylaşma səhifəsi (og etiketləri, dərhal #/xeber/ID-yə keçir) işçidən yan keçir; v40: kod faylının keş açarı sorğusuz (app.js?c=… nüsxəsi köhnə kodu saxlayırdı); v39: bildiriş kliki saytın xəbər səhifəsinə aparır; v38: başlıq sırası, dil seçimi zolaqda, paylaşma ikonları, hərəkət düyməsi
const STATIC = "8ulduz-static-" + VERSION;
const DATA = "8ulduz-data-" + VERSION;
const SCOPE_URL = new URL("./", self.location);

function inScope(url) {
  return url.origin === self.location.origin && url.pathname.startsWith(SCOPE_URL.pathname);
}
function isData(url) {
  const rel = url.pathname.slice(SCOPE_URL.pathname.length);
  return rel.startsWith("data/") && rel.endsWith(".json");
}

self.addEventListener("install", (event) => {
  event.waitUntil((async () => {
    const cache = await caches.open(STATIC);
    await cache.addAll(["./", "./index.html", "./assets/app.css", "./assets/app.js", "./assets/assistant.js", "./assets/reader.js", "./assets/source-stats.js", "./assets/config.js", "./assets/content-policy.js", "./manifest.webmanifest",
      "./assets/logo-80.png", "./assets/icon-192.png", "./assets/icon-512.png", "./assets/icon-maskable-192.png", "./assets/icon-maskable-512.png", "./assets/og-default.png"]);
    await self.skipWaiting();
  })());
});

self.addEventListener("activate", (event) => {
  event.waitUntil((async () => {
    const keys = await caches.keys();
    await Promise.all(keys.filter((k) => /^8ulduz-(static|data)-/.test(k) && k !== STATIC && k !== DATA).map((k) => caches.delete(k)));
    await self.clients.claim();
  })());
});

// Bot hər 10 dəqiqədən bir main-ə yazır. Ziyarətçinin şəbəkəsinin DNS-i domeni tapmayanda, bağlantı kəsiləndə və ya
// Pages yayımı ilişəndə sayt açılan telefonda lent donmasın: eyni fayl birbaşa repodan gəlir (CORS açıqdır).
const MIRROR = "https://raw.githubusercontent.com/8ulduz/8ulduz/main/";
// QIRMIZI XƏTT 1: pipeline.sh hər dəqiqənin faylını ayrı yola yazır (m/<dəqiqə>/status.json), çünki budaq adı ilə
// verilən fayl 5 dəqiqə keşdə qalır. Yaranmamış yola sorğu 404-ü 55 saniyə keşə salır: dəqiqə yalnız yazılandan sonra istənir.
const LIVE = "https://raw.githubusercontent.com/8ulduz/8ulduz/live/m/";
const LIVE_FILES = /data\/(?:status|latest(?:\.[a-z]{2})?|markets)\.json$/; // latest.az.json və s. yalnız live budağındadır (main-də yoxdur)
const LIVE_WAIT_MS = 2500;
const LIVE_GRACE_S = 45;
const LIVE_PAUSE_MS = 5 * 60e3; // 429/403 olsa bu qədər sayt kanalı işlənir
let liveSkipUntil = 0;
const ORIGIN_WAIT_MS = 4000; // başlıq gəlməsə ehtiyat kanala keç; gövdə axarkən kəsilmir
const MIRROR_WAIT_MS = 6000;
const STALE_MS = 15 * 60e3; // Pages bu qədər yayımlamayıbsa ilişib sayılır
const LIVE_DATA = /data\/(?:status|latest(?:\.[a-z]{2})?|news(?:\.[a-z]{2})?)\.json$/; // yalnız hər dövrə dəyişən fayllar müqayisə olunur (news.<dil>.json da main-dədir)

async function attempt(input, init, waitMs) {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), waitMs);
  try {
    const r = await fetch(input, { ...init, signal: controller.signal });
    if (!r.ok || /html/i.test(r.headers.get("content-type") || "")) throw Error("bad response " + r.status);
    return r;
  } finally { clearTimeout(timer); }
}

function marked(response, source) {
  const headers = new Headers(response.headers);
  headers.set("X-8ulduz-data", source);
  if (source === "mirror" || source === "live") headers.set("Content-Type", "application/json; charset=utf-8");
  return new Response(response.body, { status: response.status, statusText: response.statusText, headers });
}

function pagesStuck(response, url) {
  if (!LIVE_DATA.test(url.pathname)) return false;
  const modified = Date.parse(response.headers.get("last-modified") || "");
  return modified > 0 && Date.now() - modified > STALE_MS;
}

// Təzə məlumat: əvvəl sayt, sonra ehtiyat kanal. Heç biri alınmasa null.
async function liveData(url) {
  if (!LIVE_FILES.test(url.pathname) || Date.now() < liveSkipUntil) return null;
  const file = url.pathname.split("/").pop();
  const slot = Math.floor((Date.now() / 1000 - LIVE_GRACE_S) / 60);
  for (const minute of [slot, slot - 1, slot - 2]) {
    try {
      return marked(await attempt(LIVE + minute + "/" + file, { cache: "no-store", mode: "cors", credentials: "omit" }, LIVE_WAIT_MS), "live");
    } catch (e) {
      if (/ (?:403|429)$/.test(e.message)) liveSkipUntil = Date.now() + LIVE_PAUSE_MS;
      if (!/ 404$/.test(e.message)) return null; // şəbəkə xətası: digər dəqiqələri gözləmədən sayta keç
    }
  }
  liveSkipUntil = Date.now() + 60e3; // axın yazmır: dəqiqəlik bir daha yoxla, indi sayt kanalı
  return null;
}

async function freshData(req) {
  const url = new URL(req.url);
  const live = await liveData(url);
  if (live) return live;
  let origin = null;
  try { origin = await attempt(new Request(req, { cache: "no-store" }), {}, ORIGIN_WAIT_MS); } catch {}
  if (origin && !pagesStuck(origin, url)) return marked(origin, "network");
  try {
    const rel = url.pathname.slice(SCOPE_URL.pathname.length) + url.search;
    return marked(await attempt(MIRROR + rel, { cache: "no-store", mode: "cors", credentials: "omit" }, MIRROR_WAIT_MS), "mirror");
  } catch {}
  return origin ? marked(origin, "network") : null;
}

async function networkFirstData(req, event) {
  const cache = await caches.open(DATA);
  const bare = new URL(req.url);
  bare.search = "";
  const fresh = await freshData(req);
  if (fresh) {
    // Keşə yazı arxada: səhifə cavabı başlıq gələn kimi alır (əvvəl 770 KB-lıq lentin yazılması da gözlənilirdi).
    const put = cache.put(bare.toString(), fresh.clone()).catch(() => {});
    event?.waitUntil?.(put);
    return fresh;
  }
  const hit = await cache.match(bare.toString());
  if (hit) return marked(hit, "cache");
  return new Response('{"offline":true}', {
    status: 503,
    headers: { "Content-Type": "application/json; charset=utf-8" },
  });
}

async function cacheFirst(req) {
  const cache = await caches.open(STATIC);
  const hit = await cache.match(req, { ignoreSearch: true });
  if (hit) return hit;
  try {
    const fresh = await fetch(req);
    if (fresh && fresh.ok && req.method === "GET") await cache.put(req, fresh.clone());
    return fresh;
  } catch {
    if (req.mode === "navigate") {
      const shell = (await cache.match("./index.html")) || (await cache.match("./"));
      if (shell) return shell;
    }
    return new Response("Oflayn", { status: 503, headers: { "Content-Type": "text/plain; charset=utf-8" } });
  }
}

// HTML/JS/CSS: saxlanmış nüsxə dərhal verilir (təkrar açılış şəbəkəni gözləmir), təzəsi arxada yüklənib növbəti açılış
// üçün saxlanır. Kod dəyişəndə VERSION artır və install hamısını təzədən yığır. Artmasa da: arxa yoxlama app.js/app.css-də
// fərq görəndə açıq səhifələrə «shell-updated» göndərir (app.js: oxucu hələ toxunmayıbsa dərhal, yoxsa gözdən itəndə yenilənir).
// index.html hər yayımda dəyişə bilər, ona görə o müqayisə olunmur. Nüsxə yoxdursa (ilk açılış, başqa yol) şəbəkə gözlənilir.
// Yalnız bu ünvanın öz nüsxəsi: başqa yolda index.html açılsa ./assets/ yolları sınır. O hal şəbəkə alınmayanda cacheFirst-dədir.
const CODE_FILE = /\.(?:js|css)$/;
async function cachedShell(req, event) {
  const cache = await caches.open(STATIC);
  // Açar həmişə yalnız yoldur (naviqasiya da, kod faylı da): ?utm_source=… və ya app.js?c=… kimi sorğu öz nüsxəsini
  // yaradırdı, ignoreSearch isə həmişə ən köhnəsini qaytarırdı; arxa yoxlama yalnız sorğusuz açarı təzələdiyindən o oxucu
  // köhnə kodda qalırdı (v39-da app.js belə ilişdi). Şəbəkəyə də sorğusuz yol gedir: CDN-də bir nüsxə.
  const key = req.url.split(/[?#]/)[0];
  const saved = await cache.match(key, { ignoreSearch: false });
  // Müqayisə üçün mətn saxlanmış cavab səhifəyə verilməzdən ƏVVƏL götürülür: gövdə oxunandan sonra clone() xəta atır
  // və keş heç vaxt yenilənmirdi (v33-də belə idi: köhnə app.js telefonda qalırdı).
  const savedText = saved && CODE_FILE.test(new URL(req.url).pathname) ? saved.clone().text().catch(() => null) : null;
  const network = fetch(new Request(key, { cache: "no-cache" })).then(async (fresh) => {
    if (!fresh.ok) return fresh;
    const copy = fresh.clone();
    const changed = !!savedText && (await savedText) !== (await fresh.clone().text());
    await cache.put(key, copy).catch(() => {});
    if (changed) for (const client of await self.clients.matchAll({ type: "window" })) client.postMessage({ type: "shell-updated" });
    return fresh;
  });
  if (!saved) return network.catch(() => cacheFirst(req));
  event?.waitUntil?.(network.catch(() => {}));
  network.catch(() => {});
  return saved;
}

self.addEventListener("fetch", (event) => {
  const url = new URL(event.request.url);
  // Sayğac sorğusu (sendBeacon) və skript özü getsin: keşlənsə və ya kəsilsə ziyarət yazılmır.
  if (url.hostname === "gc.zgo.at" || url.hostname.endsWith(".goatcounter.com")) return;
  if (event.request.method !== "GET" || !inScope(url)) return;
  if (isData(url)) {
    event.respondWith(networkFirstData(event.request, event));
    return;
  }
  if (/\/x\/[0-9a-f]{16}$/.test(url.pathname)) return; // paylaşma səhifəsi (updater.py write_share_pages): keşə düşməsin, köhnəsi 404.html-dən yönlənir
  const shell = event.request.mode === "navigate" || /\.(?:html|js|css|webmanifest)$/.test(url.pathname);
  event.respondWith(shell ? cachedShell(event.request, event) : cacheFirst(event.request));
});

const SEEN_URL = new URL("./notify-seen.json", SCOPE_URL).toString();
function decodeBasic(s) {
  return String(s || "").replace(/&amp;/g, "&").replace(/&quot;/g, '"').replace(/&#39;|&apos;/g, "'").replace(/&lt;/g, "<").replace(/&gt;/g, ">");
}
async function readSeen() {
  const cache = await caches.open(DATA);
  const hit = await cache.match(SEEN_URL);
  if (!hit) return null;
  try {
    const v = await hit.json();
    return Array.isArray(v) ? v : [];
  } catch { return []; }
}
async function writeSeen(ids) {
  const cache = await caches.open(DATA);
  await cache.put(SEEN_URL, new Response(JSON.stringify(ids), { headers: { "Content-Type": "application/json" } }));
}
const LANG_URL = new URL("./notify-lang.json", SCOPE_URL).toString();
async function readLang() { // "" = bütün dillər; hələ bildirilməyibsə saytın standart dili
  const hit = await (await caches.open(DATA)).match(LANG_URL);
  if (!hit) return "az";
  try { const v = await hit.json(); return typeof v === "string" ? v : "az"; } catch { return "az"; }
}
self.addEventListener("message", (event) => {
  if (event.data?.type !== "notify-lang") return;
  event.waitUntil(caches.open(DATA).then((c) => c.put(LANG_URL, new Response(JSON.stringify(String(event.data.lang || "")), { headers: { "Content-Type": "application/json" } }))));
});
async function syncBreaking() {
  const res = await freshData(new Request(new URL("data/latest.json", SCOPE_URL)));
  if (!res) return;
  const data = await res.json();
  const now = Date.now();
  const fresh = (data.articles || []).filter((a) => {
    const t = new Date(a.publishedAt).getTime();
    return t && now - t >= 0 && now - t < 3600000;
  });
  const seen = await readSeen();
  if (!seen) {
    await writeSeen(fresh.map((a) => a.id));
    return;
  }
  const known = new Set(seen);
  const lang = await readLang();
  const novel = fresh.filter((a) => a.id && !known.has(a.id) && (!lang || a.lang === lang)).slice(0, 2);
  for (const a of novel) {
    await self.registration.showNotification("Son dəqiqə", {
      body: decodeBasic(a.title),
      icon: new URL("assets/icon-192.png", SCOPE_URL).toString(),
      tag: "break-" + a.id,
      data: { id: a.id, cat: a.category || "", url: storyUrl(a.id, a.category) },
    });
  }
  await writeSeen(fresh.map((a) => a.id));
}
self.addEventListener("periodicsync", (event) => {
  if (event.tag === "breaking") event.waitUntil(syncBreaking());
});
// Saytın öz xəbər səhifəsi: oxucu bildirişə basanda mənbəyə yox, 8ulduz-a gəlir (sahibin qeydi, 2026-11-04)
function storyUrl(id, cat) { return new URL("#/xeber/" + encodeURIComponent(id) + (cat ? "?b=" + encodeURIComponent(cat) : ""), SCOPE_URL).href; }
self.addEventListener("notificationclick", (event) => {
  event.notification.close();
  const d = event.notification.data || {};
  const url = d.id ? storyUrl(d.id, d.cat) : SCOPE_URL.href; // köhnə bildirişin data.url-i mənbə ola bilər: ona baxılmır
  event.waitUntil(self.clients.matchAll({ type: "window", includeUncontrolled: true }).then(async (list) => {
    const open = list.find((w) => w.url.startsWith(SCOPE_URL.href));
    if (open && d.id) { try { await open.focus(); open.postMessage({ type: "open-story", id: d.id }); return; } catch {} } // açıq səhifə yenidən yüklənmir
    return self.clients.openWindow(url);
  }));
});
