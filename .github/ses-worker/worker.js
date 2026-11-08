// 8ULDUZ «Dinlə» mətn serveri — Cloudflare Workers (pulsuz plan, kart istəmir). Sahib, 2026-11-08: «anında düşən xəbəri
// mənbədən oxusun», «pullu heç nə olmasın», «müəllif hüququ mənlikdir».
// «Dinlə» basılan anda xəbərin hazır səs faylı hələ yoxdursa sayt bu serverdən xəbərin TAM mətnini alır və cihazın öz səsi ilə
// dərhal oxuyur. Brauzer mənbə saytını özü oxuya bilmir (CORS), ona görə mətni bu kiçik server götürür. Səs burada yaradılmır.
// Quraşdırma: Cloudflare → Workers & Pages → Create → «Hello World» → Edit code → bu faylın hamısını yapışdır → Deploy.
// Ünvan (https://<ad>.<hesab>.workers.dev) assets/config.js-də sesWorker-ə yazılır. Gizli açar yoxdur.
// Sorğu: GET /?u=<mənbə ünvanı> → {"text": "..."}. Yalnız 8ulduz.az-dan gələn sorğu qəbul olunur; nəticə 1 gün keşdə qalır.

const SITE = /^https:\/\/(?:www\.)?8ulduz\.az(?:\/|$)/;
const UA = "Mozilla/5.0 (Linux; Android 14) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0 Mobile Safari/537.36 8ulduz-dinle";
const MAX_CHARS = 6000;

export default {
  async fetch(req, env, ctx) {
    const cors = { "Access-Control-Allow-Origin": "https://8ulduz.az", "Vary": "Origin" };
    if (req.method === "OPTIONS") return new Response(null, { headers: { ...cors, "Access-Control-Allow-Methods": "GET" } });
    if (!SITE.test(req.headers.get("Origin") || req.headers.get("Referer") || "")) return new Response("forbidden", { status: 403 });
    let src;
    try { src = new URL(new URL(req.url).searchParams.get("u") || ""); } catch { return new Response("bad url", { status: 400 }); }
    if (src.protocol !== "https:" || /^[\d.]+$|^\[|(^|\.)(localhost|internal|local)$/.test(src.hostname)) return new Response("bad url", { status: 400 });
    const cache = caches.default, key = new Request(`https://dinle.cache/${encodeURIComponent(src.href)}`);
    const hit = await cache.match(key);
    if (hit) return new Response(hit.body, { headers: { "Content-Type": "application/json; charset=utf-8", ...cors } });
    let text = "";
    try {
      const r = await fetch(src.href, { headers: { "User-Agent": UA, "Accept": "text/html" }, redirect: "follow" });
      if (r.ok && /html/.test(r.headers.get("content-type") || "")) text = extract((await r.text()).slice(0, 1_500_000));
    } catch {}
    const body = JSON.stringify({ text: cut(text) });
    const headers = { "Content-Type": "application/json; charset=utf-8", "Cache-Control": "public, max-age=86400" };
    if (text) ctx.waitUntil(cache.put(key, new Response(body, { headers })));
    return new Response(body, { headers: { ...headers, ...cors } });
  },
};

const ENT = { amp: "&", lt: "<", gt: ">", quot: '"', apos: "'", nbsp: " ", laquo: "«", raquo: "»", ndash: "–", mdash: "—", hellip: "…", rsquo: "’", lsquo: "‘", rdquo: "”", ldquo: "“" };
export function clean(s) {
  return String(s).replace(/<[^>]+>/g, " ").replace(/&(#x?[0-9a-f]+|[a-z]+);/gi, (m, e) => e[0] === "#" ? String.fromCodePoint(parseInt(e.slice(1).replace(/^x/i, ""), /^#x/i.test(e) ? 16 : 10)) : ENT[e.toLowerCase()] ?? m).replace(/\s+/g, " ").trim();
}
// reader_content.py ilə eyni qayda: əvvəl JSON-LD articleBody, sonra məqalənin abzasları; ödənişli xəbər oxunmur.
export function extract(html) {
  for (const m of html.matchAll(/<script[^>]+application\/ld\+json[^>]*>([\s\S]*?)<\/script>/gi)) {
    let data; try { data = JSON.parse(m[1]); } catch { continue; }
    const stack = [data];
    while (stack.length) {
      const n = stack.pop();
      if (Array.isArray(n)) { stack.push(...n); continue; }
      if (!n || typeof n !== "object") continue;
      if (n.isAccessibleForFree === false || n.isAccessibleForFree === "false") return "";
      if (typeof n.articleBody === "string") { const t = clean(n.articleBody); if (t.length >= 200) return t; }
      for (const v of Object.values(n)) if (v && typeof v === "object") stack.push(v);
    }
  }
  const scope = (html.match(/<article[\s\S]*?<\/article>/i) || [html])[0].replace(/<(script|style|nav|header|footer|aside|form)\b[\s\S]*?<\/\1>/gi, " ");
  const paras = [...scope.matchAll(/<p\b[^>]*>([\s\S]*?)<\/p>/gi)].map(m => clean(m[1])).filter(t => t.length > 40 && !/©|bütün hüquqlar|reklam/i.test(t));
  const text = [...new Set(paras)].join(" ");
  return text.length >= 200 ? text : "";
}
export function cut(text, max = MAX_CHARS) {
  return text.length > max ? text.slice(0, max).replace(/[^.!?…]*$/, "") : text;
}
