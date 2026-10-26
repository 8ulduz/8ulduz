/* 8ulduz — GitHub Pages alt yolu /8ulduz/ (və lokal eyni quruluş).
   data/*.json: yalnız şəbəkə. Keş yalnız şəbəkə alınmayanda (oflayn).
   Statik fayllar: əvvəl keş. */
const VERSION = "v3";
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
      "./assets/icon-192.png", "./assets/icon-512.png", "./assets/icon-maskable-192.png", "./assets/icon-maskable-512.png"]);
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
