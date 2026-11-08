// 8ULDUZ «Dinlə» serveri — Cloudflare Workers (pulsuz plan). Sahib, 2026-11-08: «anında», «səs babək olsun», «pullu heç nə olmasın».
// GET /ses?u=<mənbə>&id=<xəbər id>&t=<başlıq>&s=<mənbə adı> → audio/mpeg, basılan anda, Babək (az-AZ) səsi ilə:
//   1) Cloudflare keşi (bu xəbəri əvvəl dinləyən olubsa) → dərhal;
//   2) hazır tam səs (8ulduz/ses reposu, xəbər çıxandan 1–2 dəqiqə sonra hazır olur) → dərhal;
//   3) hələ hazır deyilsə: mənbədən TAM mətn + Microsoft Azure-un RƏSMİ Babək səsi (AZURE_KEY sirri, pulsuz F0 planı ayda
//      500 000 simvol; limit dolsa Azure dayanır, pul çıxmır) → axınla, oxuma ~1 saniyəyə başlayır.
//   Heç biri alınmasa 503: sayt hazır səsi gözləyir.
// GET /?u=<mənbə> → {"text": "..."} (cihaz səsi üçün tam mətn).
// Yalnız 8ulduz.az səhifəsindən gələn sorğu qəbul olunur. Sirlər Cloudflare-də: AZURE_KEY (gizli), AZURE_REGION (məs. westeurope).
// Yükləmə: .github/ses-worker qovluğunda «npx wrangler deploy».

const SITE = /^https:\/\/(?:www\.)?8ulduz\.az(?:\/|$)/;
const UA = "Mozilla/5.0 (Linux; Android 14) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0 Mobile Safari/537.36 8ulduz-dinle";
const MAX_CHARS = 6000, VOICE = "az-AZ-BabekNeural", READY = "https://raw.githubusercontent.com/8ulduz/ses/main/";

export default {
  async fetch(req, env, ctx) {
    const url = new URL(req.url), cors = { "Access-Control-Allow-Origin": "https://8ulduz.az", "Vary": "Origin" };
    if (req.method === "OPTIONS") return new Response(null, { headers: { ...cors, "Access-Control-Allow-Methods": "GET" } });
    if (url.pathname === "/saglam") return new Response(env.AZURE_KEY ? "ok azure" : "ok", { headers: cors });
    if (!SITE.test(req.headers.get("Origin") || req.headers.get("Referer") || "")) return new Response("forbidden", { status: 403 });
    let src;
    try { src = new URL(url.searchParams.get("u") || ""); } catch { return new Response("bad url", { status: 400 }); }
    if (src.protocol !== "https:" || /^[\d.]+$|^\[|(^|\.)(localhost|internal|local)$/.test(src.hostname)) return new Response("bad url", { status: 400 });
    return url.pathname === "/ses" ? audio(req, env, ctx, src, url.searchParams, cors) : textJson(ctx, src, cors);
  },
};

async function sourceText(src) {
  try {
    const r = await fetch(src.href, { headers: { "User-Agent": UA, "Accept": "text/html" }, redirect: "follow" });
    if (r.ok && /html/.test(r.headers.get("content-type") || "")) return cut(extract((await r.text()).slice(0, 1_500_000)));
  } catch {}
  return "";
}

async function textJson(ctx, src, cors) {
  const cache = caches.default, key = new Request(`https://dinle.cache/t/${encodeURIComponent(src.href)}`);
  const hit = await cache.match(key);
  if (hit) return new Response(hit.body, { headers: { "Content-Type": "application/json; charset=utf-8", ...cors } });
  const text = await sourceText(src), body = JSON.stringify({ text });
  const headers = { "Content-Type": "application/json; charset=utf-8", "Cache-Control": "public, max-age=86400" };
  if (text) ctx.waitUntil(cache.put(key, new Response(body, { headers })));
  return new Response(body, { headers: { ...headers, ...cors } });
}

async function audio(req, env, ctx, src, q, cors) {
  const cache = caches.default, key = new Request(`https://dinle.cache/a/${encodeURIComponent(src.href)}`, { headers: req.headers.get("Range") ? { Range: req.headers.get("Range") } : {} });
  const hit = await cache.match(key);
  if (hit) return withHeaders(hit, cors);
  const keep = (res) => { const [a, b] = res.body.tee(); ctx.waitUntil(new Response(b).arrayBuffer().then(buf => buf.byteLength > 3000 && cache.put(new Request(key.url), new Response(buf, { headers: AUDIO_HEADERS }))).catch(() => {})); return new Response(a, { headers: { ...AUDIO_HEADERS, ...cors } }); };
  const id = q.get("id") || "";
  if (/^[0-9a-f]{16}$/.test(id)) {
    const r = await fetch(READY + id + ".mp3", { cf: { cacheTtl: 300 } }).catch(() => null);
    if (r?.ok) return keep(r);
  }
  if (!env.AZURE_KEY) return new Response("hazır deyil", { status: 503, headers: cors });
  const text = script(clean(q.get("t") || "").slice(0, 300), clean(q.get("s") || "").slice(0, 80), await sourceText(src));
  if (!text) return new Response("mətn yoxdur", { status: 422, headers: cors });
  const r = await fetch(`https://${env.AZURE_REGION || "westeurope"}.tts.speech.microsoft.com/cognitiveservices/v1`, {
    method: "POST",
    headers: { "Ocp-Apim-Subscription-Key": env.AZURE_KEY, "Content-Type": "application/ssml+xml", "X-Microsoft-OutputFormat": "audio-24khz-48kbitrate-mono-mp3", "User-Agent": "8ulduz-dinle" },
    body: `<speak version="1.0" xmlns="http://www.w3.org/2001/10/synthesis" xml:lang="az-AZ"><voice name="${VOICE}">${xml(text)}</voice></speak>`,
  }).catch(() => null);
  if (!r?.ok) return new Response("azure " + (r?.status || "yox"), { status: 503, headers: cors });   // limit dolubsa və s.
  return keep(r);
}

const AUDIO_HEADERS = { "Content-Type": "audio/mpeg", "Cache-Control": "public, max-age=86400", "Accept-Ranges": "bytes" };
const withHeaders = (res, cors) => { const h = new Headers(res.headers); for (const [k, v] of Object.entries(cors)) h.set(k, v); return new Response(res.body, { status: res.status, headers: h }); };
const xml = s => s.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
export function script(title, source, body) {
  const t = title.replace(/[.!?…\s]+$/, "");
  let rest = body;
  if (t && rest.startsWith(t)) rest = rest.slice(t.length).replace(/^[\s.]+/, "");
  return [t && `${t}.`, source && `${source} xəbər verir.`, rest].filter(Boolean).join(" ").trim();
}

const ENT = { amp: "&", lt: "<", gt: ">", quot: '"', apos: "'", nbsp: " ", laquo: "«", raquo: "»", ndash: "–", mdash: "—", hellip: "…", rsquo: "’", lsquo: "‘", rdquo: "”", ldquo: "“" };
export function clean(s) {
  return String(s).replace(/<[^>]+>/g, " ").replace(/&(#x?[0-9a-f]+|[a-z]+);/gi, (m, e) => e[0] === "#" ? String.fromCodePoint(parseInt(e.slice(1).replace(/^x/i, ""), /^#x/i.test(e) ? 16 : 10)) : ENT[e.toLowerCase()] ?? m).replace(/\s+/g, " ").replace(/([.!?…])(?=[A-ZÇƏĞİÖŞÜ])/g, "$1 ").trim();  // «gündür.Bu» → «gündür. Bu»
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
