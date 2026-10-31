/* 8ulduz — GitHub Pages alt yolu /8ulduz/ (və lokal eyni quruluş).
   Canlı fayllar (status, latest, markets): əvvəl live budağı (dəqiqəlik), sonra sayt, sonra ehtiyat kanal.
   Qalan data/*.json: əvvəl sayt, alınmasa ehtiyat kanal (GitHub raw). Keş yalnız hamısı alınmayanda (oflayn).
   HTML/JS/CSS: əvvəl şəbəkə, oflayn olanda keş. Şəkillər: əvvəl keş. */
const VERSION = "v24"; // shell timeout
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
const LIVE_FILES = /data\/(?:status|latest|markets)\.json$/;
const LIVE_WAIT_MS = 2500;
const LIVE_GRACE_S = 45;
const LIVE_PAUSE_MS = 5 * 60e3; // 429/403 olsa bu qədər sayt kanalı işlənir
let liveSkipUntil = 0;
const ORIGIN_WAIT_MS = 4000; // başlıq gəlməsə ehtiyat kanala keç; gövdə axarkən kəsilmir
const MIRROR_WAIT_MS = 6000;
const STALE_MS = 15 * 60e3; // Pages bu qədər yayımlamayıbsa ilişib sayılır
const LIVE_DATA = /data\/(?:status|latest|news)\.json$/; // yalnız hər dövrə dəyişən fayllar müqayisə olunur

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

async function networkFirstData(req) {
  const cache = await caches.open(DATA);
  const bare = new URL(req.url);
  bare.search = "";
  const fresh = await freshData(req);
  if (fresh) {
    try { await cache.put(bare.toString(), fresh.clone()); } catch {}
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

const SHELL_WAIT_MS = 4000; // zəif şəbəkədə ağ ekran qalmasın: keşdəki nüsxə göstərilir, təzəsi arxada yazılır
async function networkFirstShell(req) {
  const cache = await caches.open(STATIC);
  const network = fetch(new Request(req, { cache: "no-cache" })).then(async (fresh) => {
    if (fresh.ok) {
      try { await cache.put(req, fresh.clone()); } catch {}
    }
    return fresh;
  });
  const saved = (await cache.match(req, { ignoreSearch: true })) || (req.mode === "navigate" ? await cache.match("./index.html") : null);
  if (!saved) return network.catch(() => cacheFirst(req));
  network.catch(() => {});
  let timer;
  const late = new Promise((resolve) => { timer = setTimeout(() => resolve(saved), SHELL_WAIT_MS); });
  try {
    return await Promise.race([network, late]);
  } catch {
    return saved;
  } finally { clearTimeout(timer); }
}

self.addEventListener("fetch", (event) => {
  const url = new URL(event.request.url);
  if (event.request.method !== "GET" || !inScope(url)) return;
  if (isData(url)) {
    event.respondWith(networkFirstData(event.request));
    return;
  }
  const shell = event.request.mode === "navigate" || /\.(?:html|js|css|webmanifest)$/.test(url.pathname);
  event.respondWith(shell ? networkFirstShell(event.request) : cacheFirst(event.request));
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
  const novel = fresh.filter((a) => a.id && !known.has(a.id)).slice(0, 2);
  for (const a of novel) {
    await self.registration.showNotification("Son dəqiqə", {
      body: decodeBasic(a.title),
      icon: new URL("assets/icon-192.png", SCOPE_URL).toString(),
      tag: "break-" + a.id,
      data: { id: a.id, url: a.sourceUrl || "" },
    });
  }
  await writeSeen(fresh.map((a) => a.id));
}
self.addEventListener("periodicsync", (event) => {
  if (event.tag === "breaking") event.waitUntil(syncBreaking());
});
self.addEventListener("notificationclick", (event) => {
  event.notification.close();
  const url = (event.notification.data && event.notification.data.url) || SCOPE_URL.href;
  event.waitUntil(self.clients.openWindow(url));
});
