/* 8ulduz — GitHub Pages alt yolu /8ulduz/ (və lokal eyni quruluş).
   Canlı fayllar (status, latest, markets): əvvəl live budağı (dəqiqəlik), sonra sayt, sonra ehtiyat kanal.
   Qalan data/*.json: əvvəl sayt, alınmasa ehtiyat kanal (GitHub raw). Keş yalnız hamısı alınmayanda (oflayn).
   HTML/JS/CSS: saxlanmış nüsxə dərhal, təzəsi arxada (cachedShell). Şəkillər: əvvəl keş. */
const VERSION = "v168"; // hər versiyanın qeydi: docs/sw-versiyalar.md (bu faylı oxucunun brauzeri endirir, tarixçə burada saxlanmır)
const STATIC = "8ulduz-static-" + VERSION;
// Məlumat keşinin adı versiyasızdır (2026-11-09): əvvəl hər yayımda (gündə 20–40 dəfə) silinirdi və yayımdan sonrakı ilk açılış
// keşsiz başlayırdı — app.js loadCached boş qalır, lent şəbəkəni gözləyirdi (telefonda +0,6–0,9 s). Açarlar sorğusuz yoldur
// (networkFirstData `bare`), sayı məhduddur, böyümür. Kod keşi (STATIC) əvvəlki kimi versiya ilə.
const DATA = "8ulduz-data";
const SCOPE_URL = new URL("./", self.location);

// İdarə paneli (/idare/, editorial-store.js) işçidən keçmir, həmişə şəbəkədən (sahib, 2026-11-11): saxlanmış köhnə nüsxə
// düzəlişdən sonra da «Illegal invocation» göstərirdi — açar «?v=» sorğusuna baxmır.
function inScope(url) {
  return url.origin === self.location.origin && url.pathname.startsWith(SCOPE_URL.pathname)
    && !url.pathname.startsWith(SCOPE_URL.pathname + "idare/") && !url.pathname.endsWith("/editorial-store.js");
}
function isData(url) {
  const rel = url.pathname.slice(SCOPE_URL.pathname.length);
  return rel.startsWith("data/") && rel.endsWith(".json");
}

self.addEventListener("install", (event) => {
  event.waitUntil((async () => {
    const cache = await caches.open(STATIC);
    // Yalnız ilk açılışın faylları (sahib, v107): ./ və kod faylları brauzerin HTTP keşindən gəlir (indicə yüklənib), şəbəkəyə yalnız
    // manifest və iki kiçik şəkil çıxır. index.html (./ ilə eyni səhifə), 512-lik və maskable ikonlar, og-default (~155 KB) işçidən heç vaxt
    // oxunmurdu, amma hər versiyada yenidən yoxlanırdı (2026-11-09).
    await cache.addAll(["./", "./assets/app.css", "./assets/app.min.js", "./assets/config.js", "./assets/content-policy.js", "./manifest.webmanifest",
      "./assets/logo-80.png", "./assets/icon-192.png"]);
    await self.skipWaiting();
  })());
});

// Keçid (v142, bir dəfə): köhnə versiyalı məlumat keşinin («8ulduz-data-vNNN») məzmunu silinməzdən əvvəl yeni ada köçürülür ki,
// bu yayımdan sonrakı açılış da keşsiz qalmasın. Yeni adda olan açar üstələnmir. Xəta aktivləşməni dayandırmır.
async function migrateData(keys) {
  try {
    const cur = await caches.open(DATA);
    for (const k of keys.filter((k) => /^8ulduz-data-/.test(k))) {
      const old = await caches.open(k);
      for (const req of await old.keys()) {
        if (await cur.match(req)) continue;
        const r = await old.match(req);
        if (r) await cur.put(req, r);
      }
    }
  } catch {}
}

self.addEventListener("activate", (event) => {
  event.waitUntil((async () => {
    const keys = await caches.keys();
    await migrateData(keys);
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
      const shell = await cache.match("./"); // ilkin keşdə yalnız ./ var (index.html eyni səhifədir)
      if (shell) return shell;
    }
    return new Response("Oflayn", { status: 503, headers: { "Content-Type": "text/plain; charset=utf-8" } });
  }
}

// HTML/JS/CSS: saxlanmış nüsxə dərhal verilir (təkrar açılış şəbəkəni gözləmir), təzəsi arxada yüklənib növbəti açılış
// üçün saxlanır. Kod dəyişəndə VERSION artır və install hamısını təzədən yığır. Artmasa da: arxa yoxlama app.js/app.css-də
// fərq görəndə açıq səhifələrə «shell-updated» göndərir (app.js onWorkerMessage: ekranda hələ lent yoxdursa dərhal, yoxsa gözdən itəndə yenilənir — 2026-11-09-a qədər kompüterdə çəkilmiş səhifə 3-cü saniyədə yenidən açılırdı).
// index.html hər yayımda dəyişə bilər, ona görə o müqayisə olunmur. Nüsxə yoxdursa (ilk açılış, başqa yol) şəbəkə gözlənilir.
// Yalnız bu ünvanın öz nüsxəsi: başqa yolda index.html açılsa ./assets/ yolları sınır. O hal şəbəkə alınmayanda cacheFirst-dədir.
const CODE_FILE = /\.(?:js|css)$/;
// Çoxdan gəlməyən oxucu (sahib, 2026-11-13: Facebook-un daxili brauzeri saytın 3 gün əvvəlki nüsxəsini göstərdi): saxlanmış nüsxə
// SHELL_MAX_AGE_MS-dən köhnədirsə əvvəl təzəsi gözlənilir, SHELL_WAIT_MS-də gəlməsə saxlanmış verilir. Hər gün gələn oxucunun
// nüsxəsi hər açılışda arxada təzələnir, ona görə ona toxunmur: təkrar açılış əvvəlki kimi şəbəkəni gözləmir.
const SHELL_MAX_AGE_MS = 36 * 3600e3, SHELL_WAIT_MS = 2500;
function tooOld(res) {
  const at = Date.parse(res.headers.get("date") || "");
  return at > 0 && Date.now() - at > SHELL_MAX_AGE_MS;
}
async function cachedShell(req, event) {
  const cache = await caches.open(STATIC);
  // Açar həmişə yalnız yoldur (naviqasiya da, kod faylı da): ?utm_source=… və ya app.js?c=… kimi sorğu öz nüsxəsini
  // yaradırdı, ignoreSearch isə həmişə ən köhnəsini qaytarırdı; arxa yoxlama yalnız sorğusuz açarı təzələdiyindən o oxucu
  // köhnə kodda qalırdı (v39-da app.js belə ilişdi). Şəbəkəyə də sorğusuz yol gedir: CDN-də bir nüsxə.
  const key = req.url.split(/[?#]/)[0];
  let saved = await cache.match(key, { ignoreSearch: false });
  if (saved?.redirected) saved = undefined; // yönləndirilmiş cavabı brauzer naviqasiyada rədd edir (ERR_FAILED)
  // Müqayisə üçün mətn saxlanmış cavab səhifəyə verilməzdən ƏVVƏL götürülür: gövdə oxunandan sonra clone() xəta atır
  // və keş heç vaxt yenilənmirdi (v33-də belə idi: köhnə app.js telefonda qalırdı).
  const savedText = saved && CODE_FILE.test(new URL(req.url).pathname) ? saved.clone().text().catch(() => null) : null;
  const old = !!saved && tooOld(saved);
  let tell = !old; // səhifəyə saxlanmış nüsxə verilirsə təzə kod barədə xəbər gedir; təzəsi verilibsə ehtiyac yoxdur
  const net = fetch(new Request(key, { cache: "no-cache" }));
  const network = net.then(async (fresh) => {
    if (fresh.redirected) return req.mode === "navigate" ? Response.redirect(fresh.url, 302) : fresh;
    if (!fresh.ok) return fresh;
    const copy = fresh.clone(), text = savedText ? fresh.clone().text() : null; // surətlər gövdə səhifəyə verilməzdən əvvəl
    const changed = !!text && (await savedText) !== (await text);
    await cache.put(key, copy).catch(() => {});
    if (changed && tell) for (const client of await self.clients.matchAll({ type: "window" })) client.postMessage({ type: "shell-updated" });
    return fresh;
  });
  if (!saved) return network.catch(() => cacheFirst(req));
  event?.waitUntil?.(network.catch(() => {}));
  network.catch(() => {});
  if (old) {
    const fresh = await Promise.race([net.catch(() => null), new Promise((r) => setTimeout(() => { tell = true; r(null); }, SHELL_WAIT_MS))]);
    if (fresh?.ok && !fresh.redirected) return fresh;
    tell = true;
  }
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
  const id = d.id === "on" ? "" : d.id; // «on»: nümunə bildiriş (app.js armNotify), xəbər deyil
  const url = id ? storyUrl(id, d.cat) : SCOPE_URL.href; // köhnə bildirişin data.url-i mənbə ola bilər: ona baxılmır
  event.waitUntil(self.clients.matchAll({ type: "window", includeUncontrolled: true }).then(async (list) => {
    const open = list.find((w) => w.url.startsWith(SCOPE_URL.href));
    if (open && id) { try { await open.focus(); open.postMessage({ type: "open-story", id }); return; } catch {} } // açıq səhifə yenidən yüklənmir
    return self.clients.openWindow(url);
  }));
});
