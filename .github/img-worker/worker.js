// 8ULDUZ şəkil keşi — Cloudflare Workers + R2, ünvan: https://img.8ulduz.az/?url=<mənbə>&w=<en>&we&output=webp&q=70
// Sahib, 2026-11-27: «Bəli, qur» (təklif: saytın kiçildilmiş şəkilləri öz domenimizdən, öz keşimizdən gəlsin).
// Niyə: şəkillər wsrv.nl-dən gəlir. Onun keşində olan şəkil Bakıdan (Cloudflare GYD) 44–70 ms, olmayan 230–3 400 ms-dir
// (docs/qirmizi-xetler.md §3, 2026-11-27 qeydi). Gündə ~1 100 təzə şəkil (~13 MB) var: hər birinin ilk oxucusu soyuq cavabı gözləyirdi.
// Bu server hər şəkli bir dəfə wsrv.nl-dən alır və saxlayır. Ardıcıllıq:
//   1) caches.default — oxucunun Cloudflare düyünündəki keş (~20–40 ms);
//   2) R2 (SEKIL bağlaması, 8ulduz-sekil bucket-i) — bütün düyünlər üçün bir nüsxə (~60–150 ms); 30 gündən sonra silinir (lifecycle qaydası);
//   3) heç birində yoxdursa wsrv.nl, eyni sorğu ilə və vaxt həddi ilə (WSRV_MS). 200 və şəkil gələndə dərhal verilir, R2-yə və keşə
//      ctx.waitUntil-də yazılır. Xəta, gecikmə və ya şəkil olmayan cavab heç yerə yazılmır.
// Sorğu saytın wsrv.nl sorğusunun eynisidir (app.js sized, lent.js, vlent.js): sayt yalnız hostu dəyişir. Parametrlərin sırası açarı
// dəyişmir (canonical): eyni şəkil bir dəfə saxlanır, wsrv.nl-ə isə həmişə saytın öz sırası ilə gedir — onun keşindəki nüsxə də işə yarayır.
// Sui-istifadəyə qarşı: yalnız saytın işlətdiyi parametrlər və enlər (WIDTHS), yalnız output=webp və q=70, url yalnız http(s);
// cavab yalnız raster şəkil (svg yox: öz domenimizdən skriptli fayl verilmir) və MAX_BYTES-dan kiçik. Qalan hər şey 400.
// wsrv.nl xəta versə və ya gecikə, şəkil yox, xəta statusu gedir (no-store): saytın imgFail-i növbəti ünvana keçir — eyni wsrv.nl
// ünvanı, sonra orijinal. Limit dolanda (Cloudflare 1027) və ya server dayananda da oxucu şəkli eyni yolla alır.
// Sirr, açar yoxdur: yalnız R2 bağlaması. Yükləmə: bu qovluqda «npx wrangler deploy» və ya Cloudflare panelində kodu yapışdırmaq
// (docs/img-worker.md). Testlər: tests/img-worker.test.cjs.

export const HOST = "img.8ulduz.az";
const WSRV = "https://wsrv.nl/";
// Saytın işlətdiyi enlər (2026-11-27): slayd 640 / 480, «Son xəbərlər» və video kartı 360, Zuğulba 168, xəbər səhifəsi 960,
// Videolent posteri 720 (lent.js), komanda loqoları və bayraqlar 96 / 112 / 48 / 40 / 36 (futbol.js, komanda.js: sized(…, ölçü × 2)).
export const WIDTHS = new Set([36, 40, 48, 96, 112, 168, 360, 480, 640, 720, 960]);
const PARAMS = ["url", "w", "we", "output", "q"];
const URL_MAX = 2048;
export const MAX_BYTES = 2e6;                      // 960 px webp q=70 adətən 30–150 KB-dır
export const WSRV_MS = 6000;                       // wsrv.nl-in soyuq cavabı 2026-11-27-də ən çox 3,4 s idi
const TYPES = /^image\/(?:webp|jpeg|png|gif|avif)$/;
export const KEEP = "public, max-age=31536000, immutable"; // məzmunu ünvan müəyyən edir: dəyişmir
const UA = "Mozilla/5.0 (compatible; 8ulduz-img/1.0; +https://8ulduz.az/)";

export default {
  async fetch(req, env, ctx) {
    const url = new URL(req.url);
    if (url.pathname === "/saglam") return text(200, "ok");
    if (url.pathname !== "/") return text(404, "yoxdur");
    if (req.method !== "GET" && req.method !== "HEAD") return text(405, "yalnız GET", { Allow: "GET, HEAD" });
    const c = canonical(url.searchParams);
    if (c.error) return text(400, c.error);
    const res = await image(c, env, ctx);
    return req.method === "HEAD" ? new Response(null, res) : res;
  },
};

// Sorğunun yeganə forması: { src, w, query } və ya { error }. Sıra, «we» ↔ «we=» açarı dəyişmir; artıq, çatışmayan və ya təkrar parametr 400.
export function canonical(params) {
  const keys = [...params.keys()];
  if (keys.length !== PARAMS.length || !PARAMS.every(k => params.getAll(k).length === 1)) return { error: "parametrlər: url, w, we, output=webp, q=70" };
  if (params.get("we") !== "" || params.get("output") !== "webp" || params.get("q") !== "70") return { error: "yalnız we, output=webp, q=70" };
  const w = params.get("w"), src = params.get("url");
  if (!/^[1-9]\d{1,3}$/.test(w) || !WIDTHS.has(+w)) return { error: "en: " + [...WIDTHS].join(", ") };
  if (src.length > URL_MAX || !/^https?:\/\//i.test(src) || /[\0-\x1f]/.test(src)) return { error: "url yalnız http(s)" };
  let u;
  try { u = new URL(src); } catch { return { error: "url yalnız http(s)" }; }
  if (!/^https?:$/.test(u.protocol) || !u.hostname || u.username || u.password) return { error: "url yalnız http(s)" };
  if (u.hostname === HOST || u.hostname === "wsrv.nl") return { error: "url proksinin özüdür" }; // dövrə yox
  return { src, w: +w, query: `url=${encodeURIComponent(src)}&w=${w}&we&output=webp&q=70` };
}

// R2 açarı: sorğunun SHA-256-sı (ünvan 2 KB ola bilər, açar qısa və sabit qalır). v1: format dəyişsə yeni ön şəkilçi.
export async function r2Key(query) {
  const d = new Uint8Array(await crypto.subtle.digest("SHA-256", new TextEncoder().encode(query)));
  return "v1/" + Array.from(d, b => b.toString(16).padStart(2, "0")).join("");
}

export async function image({ query }, env, ctx) {
  const cache = globalThis.caches?.default, key = new Request(`https://${HOST}/?${query}`), bucket = env?.SEKIL;
  const later = p => (ctx?.waitUntil ? ctx.waitUntil(p) : p);
  // 1) Bu düyünün keşi.
  try { const hit = cache && await cache.match(key); if (hit) return mark(hit, "edge"); } catch {}
  const name = await r2Key(query);
  // 2) R2: başqa düyündə və ya isitmədə (sekil-isit.cjs) gətirilmiş nüsxə.
  try {
    const obj = bucket && await bucket.get(name);
    if (obj) {
      const type = obj.httpMetadata?.contentType || "image/webp";
      const res = ok(await obj.arrayBuffer(), TYPES.test(type) ? type : "image/webp", "r2");
      if (cache) later(cache.put(key, res.clone()).catch(() => {}));
      return res;
    }
  } catch {}
  // 3) wsrv.nl, saytın öz sırası ilə.
  let r, body;
  try {
    r = await fetch(`${WSRV}?${query}`, { headers: { "User-Agent": UA, "Accept": "image/webp,image/*" }, signal: AbortSignal.timeout(WSRV_MS) });
  } catch (e) { return text(timedOut(e) ? 504 : 502, "wsrv.nl cavab vermədi"); }
  const type = (r.headers.get("Content-Type") || "").split(";")[0].trim().toLowerCase();
  if (r.status !== 200 || !TYPES.test(type) || +(r.headers.get("Content-Length") || 0) > MAX_BYTES) {
    try { await r.body?.cancel(); } catch {}
    return text(r.status >= 400 && r.status < 500 ? r.status : 502, `wsrv.nl: ${r.status} ${type || "-"}`);
  }
  try { body = await r.arrayBuffer(); } catch (e) { return text(timedOut(e) ? 504 : 502, "wsrv.nl cavabı yarımçıq"); }
  if (!body.byteLength || body.byteLength > MAX_BYTES) return text(502, "şəklin ölçüsü: " + body.byteLength);
  const res = ok(body, type, "wsrv");
  later(Promise.all([
    bucket && bucket.put(name, body, { httpMetadata: { contentType: type, cacheControl: KEEP } }).catch(() => {}),
    cache && cache.put(key, res.clone()).catch(() => {}),
  ]));
  return res;
}

const timedOut = e => e?.name === "TimeoutError" || e?.name === "AbortError";
const BASE = { "Access-Control-Allow-Origin": "*", "Timing-Allow-Origin": "*", "X-Content-Type-Options": "nosniff" };
// X-Sekil: şəkil haradan gəldi (edge / r2 / wsrv) — yoxlama üçün (docs/img-worker.md).
function ok(body, type, from) {
  return new Response(body, { status: 200, headers: { ...BASE, "Content-Type": type, "Cache-Control": KEEP, "X-Sekil": from } });
}
function mark(hit, from) {
  const res = new Response(hit.body, hit);
  res.headers.set("X-Sekil", from);
  return res;
}
function text(status, msg, extra = {}) {
  return new Response(msg, { status, headers: { ...BASE, "Content-Type": "text/plain; charset=utf-8", "Cache-Control": "no-store", ...extra } });
}
