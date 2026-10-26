/* 8ulduz — GitHub Pages alt yolu /8ulduz/ (və lokal eyni quruluş).
   data/*.json: yalnız şəbəkə. Keş yalnız şəbəkə alınmayanda (oflayn).
   Statik fayllar: əvvəl keş. */
const VERSION = "v9";
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
    await cache.addAll(["./", "./index.html", "./assets/app.css", "./assets/app.js", "./assets/config.js", "./manifest.webmanifest",
      "./assets/icon-192.png", "./assets/icon-512.png", "./assets/icon-maskable-192.png", "./assets/icon-maskable-512.png", "./assets/og-default.png"]);
    await self.skipWaiting();
  })());
});

self.addEventListener("activate", (event) => {
  event.waitUntil((async () => {
    const keys = await caches.keys();
    await Promise.all(keys.filter((k) => k !== STATIC && k !== DATA).map((k) => caches.delete(k)));
    await self.clients.claim();
  })());
});

async function networkFirstData(req) {
  const cache = await caches.open(DATA);
  const bare = new URL(req.url);
  bare.search = "";
  try {
    const fresh = await fetch(new Request(req, { cache: "no-store" }));
    if (fresh && fresh.ok) {
      const headers = new Headers(fresh.headers);
      headers.set("X-8ulduz-data", "network");
      const marked = new Response(fresh.clone().body, { status: fresh.status, statusText: fresh.statusText, headers });
      await cache.put(bare.toString(), marked.clone());
      return marked;
    }
    return fresh;
  } catch {
    const hit = await cache.match(bare.toString());
    if (hit) {
      const headers = new Headers(hit.headers);
      headers.set("X-8ulduz-data", "cache");
      return new Response(hit.body, { status: hit.status, statusText: hit.statusText, headers });
    }
    return new Response('{"articles":[],"offline":true}', {
      status: 200,
      headers: { "Content-Type": "application/json; charset=utf-8" },
    });
  }
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

self.addEventListener("fetch", (event) => {
  const url = new URL(event.request.url);
  if (event.request.method !== "GET" || !inScope(url)) return;
  if (isData(url)) {
    event.respondWith(networkFirstData(event.request));
    return;
  }
  event.respondWith(cacheFirst(event.request));
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
  const res = await fetch(new URL("data/news.json", SCOPE_URL), { cache: "no-store" });
  if (!res.ok) return;
  const data = await res.json();
  const now = Date.now();
  const fresh = (data.articles || []).filter((a) => {
    const t = new Date(a.publishedAt).getTime();
    return t && now - t < 3600000;
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
