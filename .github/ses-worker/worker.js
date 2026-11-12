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
  const cache = caches.default, key = new Request(`https://dinle.cache/t2/${encodeURIComponent(src.href)}`);
  const hit = await cache.match(key);
  if (hit) return new Response(hit.body, { headers: { "Content-Type": "application/json; charset=utf-8", ...cors } });
  const text = await sourceText(src), body = JSON.stringify({ text });
  const headers = { "Content-Type": "application/json; charset=utf-8", "Cache-Control": "public, max-age=86400" };
  if (text) ctx.waitUntil(cache.put(key, new Response(body, { headers })));
  return new Response(body, { headers: { ...headers, ...cors } });
}

async function audio(req, env, ctx, src, q, cors) {
  const cache = caches.default, key = new Request(`https://dinle.cache/a2/${encodeURIComponent(src.href)}`, { headers: req.headers.get("Range") ? { Range: req.headers.get("Range") } : {} });
  const hit = await cache.match(key);
  if (hit) return withHeaders(hit, cors);
  // Səs axınla verilir və eyni vaxtda keşə yazılır (yalnız tam alınıbsa: okP).
  const keep = (res, okP = true) => { const [a, b] = res.body.tee(); ctx.waitUntil(Promise.all([new Response(b).arrayBuffer(), okP]).then(([buf, ok]) => ok && buf.byteLength > 3000 && cache.put(new Request(key.url), new Response(buf, { headers: AUDIO_HEADERS }))).catch(() => {})); return new Response(a, { headers: { ...AUDIO_HEADERS, ...cors } }); };
  const id = q.get("id") || "";
  if (/^[0-9a-f]{16}$/.test(id)) {
    // Dəqiqə nişanı və 404-ün keşlənməməsi: səs hazır olan kimi verilir (əvvəlki «hələ yoxdur» cavabı 5 dəqiqə yadda qalmır).
    const r = await fetch(`${READY}${id}.mp3?m=${Math.floor(Date.now() / 6e4)}`, { cf: { cacheTtlByStatus: { "200-299": 300, "400-599": -1 } } }).catch(() => null);
    if (r?.ok) return keep(r);
  }
  if (!env.AZURE_KEY) return new Response("hazır deyil", { status: 503, headers: cors });
  // Basılan anda (sahib: «anında»): başlıq + mənbə dərhal səslənir (ilk səs ~0,5 s); mənbədən tam mətn paralel gəlir
  // və başlıq oxunarkən arxasınca səslənir — bir axın, arada fasilə yoxdur.
  const t = clean(q.get("t") || "").slice(0, 300), s = clean(q.get("s") || "").slice(0, 80), head = script(t, s, "");
  const tailP = sourceText(src).then(b => { const full = script(t, s, b); return full.startsWith(head) ? full.slice(head.length).trim() : full; });
  if (!head) {
    const full = await tailP;
    if (!full) return new Response("mətn yoxdur", { status: 422, headers: cors });
    const r = await tts(env, full);
    return r?.ok ? keep(r) : new Response("azure " + (r?.status || "yox"), { status: 503, headers: cors });
  }
  const r1 = await tts(env, head);
  if (!r1?.ok) return new Response("azure " + (r1?.status || "yox"), { status: 503, headers: cors });   // limit dolubsa və s.
  const r2P = tailP.then(tail => tail ? tts(env, tail) : null);
  const { readable, writable } = new TransformStream();
  const okP = (async () => {
    await r1.body.pipeTo(writable, { preventClose: true });
    const r2 = await r2P;
    if (r2?.ok) await r2.body.pipeTo(writable, { preventClose: true });
    await writable.close();
    return !r2 || r2.ok;   // mətnin qalanı alınmayıbsa yalnız başlıq oxunur və keşə yazılmır
  })().catch(async () => { try { await writable.abort(); } catch {} return false; });
  return keep(new Response(readable), okP);
}

const tts = (env, text) => fetch(`https://${env.AZURE_REGION || "westeurope"}.tts.speech.microsoft.com/cognitiveservices/v1`, {
  method: "POST",
  headers: { "Ocp-Apim-Subscription-Key": env.AZURE_KEY, "Content-Type": "application/ssml+xml", "X-Microsoft-OutputFormat": "audio-24khz-48kbitrate-mono-mp3", "User-Agent": "8ulduz-dinle" },
  body: `<speak version="1.0" xmlns="http://www.w3.org/2001/10/synthesis" xml:lang="az-AZ"><voice name="${VOICE}">${xml(text)}</voice></speak>`,
}).catch(() => null);

const AUDIO_HEADERS = { "Content-Type": "audio/mpeg", "Cache-Control": "public, max-age=86400", "Accept-Ranges": "bytes" };
const withHeaders = (res, cors) => { const h = new Headers(res.headers); for (const [k, v] of Object.entries(cors)) h.set(k, v); return new Response(res.body, { status: res.status, headers: h }); };
const xml = s => s.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
export function script(title, source, body) {
  const t = title.replace(/[.!?…\s]+$/, "");
  let rest = body;
  if (t && rest.startsWith(t)) rest = rest.slice(t.length).replace(/^[\s.]+/, "");
  return [t && `${t}.`, source && `${source} xəbər verir.`, rest].filter(Boolean).join(" ").trim();
}

// Adlı HTML işarələri: bəzi saytlar «g&uuml;n» yazır (lent, teleqraf, apasport) — səs «ampersand» oxumasın. Böyük-kiçik hərf fərqlidir.
const ENT = { amp: "&", lt: "<", gt: ">", quot: '"', apos: "'", nbsp: " ", shy: "", laquo: "«", raquo: "»", ndash: "–", mdash: "—", hellip: "…", rsquo: "’", lsquo: "‘", rdquo: "”", ldquo: "“", bdquo: "„", sbquo: "‚", bull: "•", middot: "·", deg: "°", times: "×", euro: "€", copy: "©", reg: "®", trade: "™",
  uuml: "ü", Uuml: "Ü", ouml: "ö", Ouml: "Ö", ccedil: "ç", Ccedil: "Ç", auml: "ä", Auml: "Ä", euml: "ë", iuml: "ï", acirc: "â", Acirc: "Â", icirc: "î", Icirc: "Î", ucirc: "û", ecirc: "ê", ocirc: "ô",
  eacute: "é", Eacute: "É", aacute: "á", iacute: "í", oacute: "ó", uacute: "ú", agrave: "à", egrave: "è", scaron: "š", Scaron: "Š", ntilde: "ñ" };
const ent = s => s.replace(/&(#x?[0-9a-f]+|[a-z]+);/gi, (m, e) => e[0] === "#" ? String.fromCodePoint(parseInt(e.slice(1).replace(/^x/i, ""), /^#x/i.test(e) ? 16 : 10)) : ENT[e] ?? ENT[e.toLowerCase()] ?? m);
export function clean(s) {
  return ent(ent(String(s).replace(/<[^>]+>/g, " "))).replace(/\s+/g, " ").replace(/([.!?…])(?=[A-ZÇƏĞİÖŞÜ])/g, "$1 ").trim();  // «gündür.Bu» → «gündür. Bu»
}
// Xəbərin altındakı lazımsız hissələr (sahib, 2026-11-08: «xəbərin altındakı lazımsız şeyləri də oxuyur»); reader_content.py-də eynisi.
// JUNK: paylaşım/abunə çağırışları, hüquq qeydləri, ödənişli xəbər yazısı, səhv/xəta səhifəsi; belə cümlə/abzas oxunmur.
// STOP: «Oxşar xəbərlər» kimi başlıqdan sonra heç nə oxunmur. Azərbaycan hərfi olmayan abzas (ingiliscə xəta səhifəsi) oxunmur.
// Abzas rejimində durğu işarəsi olmayan qısa sətir (oxşar xəbərin başlığı) oxunmur.
const JUNK = /sosial şəbəkələrdə paylaş|xəbər (xoşunuza gəldi|maraqlı gəlib)|kanalımız(da|a)? (izləy|abunə)|abunə olun|ctrl\s*\+\s*enter|mətndə (səhv|xəta)|qeydiyyatdan keçin|ödənişli (xəbər|video|foto)|bizi (facebook|[iİ]nstagram|telegram|whatsapp|youtube|tiktok)|xəbəri paylaş|©|bütün (müəllif )?hüquqlar|hüquqları qorunur|[iİ]stinad (mütləqdir|edilməlidir|vacibdir|zəruridir)|(materiallar(ın|dan)|məlumatdan) [iİ]stifadə|cloudflare ray id|[iİ]zləyin @|^(müəllif|foto|video|mənbə|reklam)\s*:/i;
const STOP = /^((oxşar|digər|əlaqəli|son) xəbərlər|mövzu(ya aid| ilə bağlı)|ən çox oxunan|xəbər lenti|bölmənin digər)( xəbərləri)?\s*:?$/i;
const AZ = /[əğışçöüƏĞŞÇÖÜİ]/;
export function tidy(parts, paragraphs = false) {
  const out = [];
  for (let p of parts) {
    p = p.replace(/\{\{[^}]*\}\}/g, " ").replace(/\((unikal|eksklüziv)\)/gi, " ").replace(/\s+/g, " ").trim();
    if (!p) continue;
    if (STOP.test(p)) break;
    if (JUNK.test(p) || !AZ.test(p)) continue;
    if (paragraphs && p.length < 220 && !/[.!?…]["”»’]?\s/.test(p) && !/[.!?:;"”»)’']$/.test(p.replace(/(\.\.\.|…)$/, ""))) continue;
    out.push(p);
  }
  return out;
}
const sentences = text => tidy(text.split(/(?<=[.!?…])\s+(?=[A-ZÇƏĞİÖŞÜ"“«])/)).join(" ");
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
      if (typeof n.articleBody === "string") { const t = sentences(clean(n.articleBody)); if (t.length >= 200) return t; }
      for (const v of Object.values(n)) if (v && typeof v === "object") stack.push(v);
    }
  }
  // Sahib, 2026-11-12 («dinləməni tam düzəlt hər bir saytda»): reader_content.py-nin eyni iki addımı — əvvəl məqalə blokunun
  // abzasları (ArticleParagraphs), tapılmasa səhifədə ən çox nəsr olan blok (DenseBlocks). Hazır səs və anında səs eyni mətni oxuyur.
  const tokens = tokenize(html);
  const rows = tidy([...new Set(scopedRows(tokens))], true).filter(t => t.length >= 30);
  let text = sentences(rows.join(" "));
  if (rows.length >= 2 && text.length >= 200 && text.length <= 24000) return text;
  text = denseText(tokens, html);
  return text.length >= 100 && text.length <= 24000 ? text : "";
}

// HTML → [növ, teq, atributlar | mətn]: "o" açılış, "c" bağlanış, "t" mətn. script/style məzmunu atılır.
const ATTR = /\b(class|id|itemprop)\s*=\s*(?:"([^"]*)"|'([^']*)'|([^\s"'>]+))/gi;
export function tokenize(html) {
  const out = [], re = /<!--[\s\S]*?-->|<(script|style)\b[^>]*>[\s\S]*?<\/\1\s*>|<(\/?)([a-zA-Z][a-zA-Z0-9:-]*)((?:[^>"']|"[^"]*"|'[^']*')*)>|([^<]+|<)/g;
  for (const m of html.matchAll(re)) {
    if (m[5] !== undefined) { out.push(["t", "", m[5]]); continue; }
    if (!m[3]) continue;
    const tag = m[3].toLowerCase();
    if (m[2]) { out.push(["c", tag, null]); continue; }
    const a = {};
    for (const x of m[4].matchAll(ATTR)) a[x[1].toLowerCase()] ??= x[2] ?? x[3] ?? x[4] ?? "";
    out.push(["o", tag, a]);
    if (/\/\s*$/.test(m[4])) out.push(["c", tag, null]);
  }
  return out;
}

const VOID_P = new Set("br img hr meta link input source wbr".split(" "));
const BLOCK_TAGS = new Set("nav aside footer header h1 script style form".split(" "));
const SCOPE = /(?:article|news|entry|post|detail)[-_ ](?:body|content|text|desc)|fullstory|full-post-article|\btext-one\b|\bzoomtext\b|\bnews-detail\b/i;
function scopedRows(tokens) {
  const stack = [], rows = [];
  let para = null;
  for (const [kind, tag, a] of tokens) {
    if (kind === "t") { if (para && stack.length && !stack.at(-1)[2]) para.push(a); continue; }
    if (kind === "o") {
      const marker = (a.class || "") + " " + (a.id || ""), parent = stack.at(-1) || ["", false, false];
      const scoped = parent[1] || tag === "article" || a.itemprop === "articleBody" || a.id === "font_size" || SCOPE.test(marker);
      const blocked = parent[2] || BLOCK_TAGS.has(tag) || /related|recommend|advert|comment|social|paywall/i.test(marker);
      if (!VOID_P.has(tag)) stack.push([tag, scoped, blocked]);
      if (tag === "p" && scoped && !blocked && !/title|info|caption|date|share|foot|copyright|author|subscribe|banner/i.test(a.class || "")) para = [];
      continue;
    }
    if (tag === "p" && para) { const t = clean(para.join(" ")); if (t) rows.push(t); para = null; }
    for (let i = stack.length - 1; i >= 0; i--) if (stack[i][0] === tag) { stack.length = i; break; }
  }
  return rows;
}

const VOID = new Set("br img hr meta link input source wbr area base col embed track param".split(" "));
const INLINE = new Set("a b strong em i u span font small sup sub mark abbr time label s del ins cite q code big strike nobr".split(" "));
const SKIP = new Set("nav aside footer header script style form noscript button select textarea iframe svg figcaption h1 h2 h3 h4 h5 h6 title head".split(" "));
const SKIP_CLASS = /related|recommend|advert|comment|social|paywall|share|breadcrumb|sidebar|cookie|popup|modal|(?:^|[\s_-])(?:tags?|teq|menu|footer|banner|widget|date|time|tarix|author|views?|counter)(?:$|[\s_-])/i;
const PROSE = /[.!?…]["”»’)]?(\s|$)/;
const STAMP = /^\s*(\d{1,2}[:.]\d{2}(?!\d)|\d{1,2}[.\/-]\d{1,2}[.\/-]\d{2,4}(?!\d)|\d{1,2}\s+(yanvar|fevral|mart|aprel|may|iyun|iyul|avqust|sentyabr|oktyabr|noyabr|dekabr)\s+(\d{4}\s+)?\d{1,2}:\d{2}(?!\d))/i;
const META = /^\s*(teqlər|etiketlər|açar sözlər|mənbə|müəllif|foto|oxunub|baxış(lar)?( sayı)?|tarix|bölmə|şriftin ölçüsü)\s*:/i;
function denseText(tokens, html) {
  const root = { buf: [], own: [], seq: [] }, found = [];
  let stack = [["", false, root]];
  const flush = n => { const t = clean(n.buf.join(" ")); n.buf = []; if (t) { n.own.push(t); n.seq.push(t); } };
  const close = n => {
    flush(n);
    let prose = 0;
    for (const p of n.seq) if (p.length >= 60 && AZ.test(p) && PROSE.test(p) && !STAMP.test(p)) prose += p.length;
    if (prose >= 100) found.push([prose, n.seq]);
  };
  const end = gone => { for (let i = gone.length - 1; i >= 0; i--) if (!INLINE.has(gone[i][0])) { close(gone[i][2]); gone[i][2].up.seq.push(...gone[i][2].own); } };
  for (const [kind, tag, a] of tokens) {
    if (kind === "t") { if (!stack.at(-1)[1]) stack.at(-1)[2].buf.push(a); continue; }
    if (kind === "o") {
      if (VOID.has(tag)) { if (tag === "br") flush(stack.at(-1)[2]); continue; }
      let [, blocked, node] = stack.at(-1);
      blocked = blocked || SKIP.has(tag) || SKIP_CLASS.test((a.class || "") + " " + (a.id || ""));
      if (!INLINE.has(tag)) { flush(node); node = { buf: [], own: [], seq: [], up: node }; }
      stack.push([tag, blocked, node]);
      continue;
    }
    for (let i = stack.length - 1; i > 0; i--) if (stack[i][0] === tag) { const gone = stack.slice(i); stack = stack.slice(0, i); end(gone); break; }
  }
  end(stack.slice(1));
  close(root);
  const m = html.match(/<meta\b[^>]*?(?:property|name)=["'](?:og:)?description["'][^>]*?content=["']([^"']{40,})/i) || html.match(/<meta\b[^>]*?content=["']([^"']{40,})["'][^>]*?(?:property|name)=["'](?:og:)?description["']/i);
  const squash = s => s.replace(/[^\p{L}\p{N}_]+/gu, "").toLowerCase(), head = html.match(/<title\b[^>]*>([\s\S]*?)<\/title>/i);
  let key = m ? squash(clean(m[1])).slice(0, 40) : "";
  if (key && head && squash(clean(head[1])).startsWith(key)) key = "";   // təsvir başlığın özüdürsə mətni göstərmir
  let best = [], top = 0;
  for (const [prose, seq] of found) {
    const hit = !!key && squash(seq.join(" ")).includes(key);
    if (prose < 200 && !hit) continue;   // qısa xəbər yalnız səhifənin öz təsviri ilə üst-üstə düşəndə
    const score = prose + (hit ? 1e6 : 0);   // təsviri olan blok həmişə öndədir
    if (score > top) { best = seq; top = score; }
  }
  return sentences(tidy([...new Set(best)].filter(p => !(META.test(p) && p.length < 200) && !STAMP.test(p)), true).filter(t => t.length >= 30).join(" "));
}
export function cut(text, max = MAX_CHARS) {
  return text.length > max ? text.slice(0, max).replace(/[^.!?…]*$/, "") : text;
}
