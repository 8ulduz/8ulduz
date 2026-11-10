// 8ULDUZ paylaşma keçidi — Cloudflare Workers (pulsuz plan), ünvan: https://www.8ulduz.az/<id>?h=<yymmddhh> (köhnə x.8ulduz.az keçidləri də bura gəlir)
// Sahib, 2026-11-08: «Facebook-da paylaşanda başlıq çıxmır, xəbərə qayıtmır; tam düzəlt, WhatsApp kimi».
// Niyə: Facebook, WhatsApp, Telegram, X önizləməni keçidin og: etiketlərindən oxuyur. Saytın /x/<id> səhifəsini updater.py yazır,
// amma main-ə 10 dəqiqədən bir düşür: son dəqiqələrin xəbəri paylaşılanda səhifə hələ yoxdur, önizləmə boş qalırdı. Bu server
// hər keçidi həmin dəqiqə cavablandırır:
//   1) https://8ulduz.az/x/<id> varsa (updater.write_share_pages) — olduğu kimi, og:url bu ünvana;
//   2) yoxdursa xəbərin sətri lentdən tapılır: dəqiqəlik kanal (live budağı, m/<dəqiqə>/latest.json, cari və əvvəlki 3 dəqiqə),
//      sonra saytın data/latest.json, data/first.json, data/news.json — tapılanda updater.share_page ilə eyni səhifə
//      (og:title, og:description, og:image wsrv.nl proksisindən 1200×630, sessionStorage-a sətir, skriptlə dərhal saytın #/xeber/<id>?b=&h= ünvanına;
//      meta refresh yoxdur, canonical səhifənin özüdür: Facebook robotu refresh-i izləyib baş səhifənin kartını götürürdü — 2026-11-08);
//   3) heç yerdə yoxdursa (və ya server xəta versə) 302 → https://8ulduz.az/#/xeber/<id>?h=…: sayt xəbəri arxivdən açır. Keçid heç vaxt ölmür.
//   0) SÜRƏT (2026-11-09): og səhifəsi yalnız önizləmə robotlarına lazımdır. Keçidə basan oxucunun brauzeri (Sec-Fetch-Dest: document,
//      Sec-Fetch-Mode: navigate göndərir, robot deyil) dərhal 302 ilə sayta gedir: nə saytın /x/ səhifəsi, nə lent soruşulur (soyuq
//      cavab 0,6 s idi), HTML və skript də yoxdur. Robot (Facebook, WhatsApp, Telegram, X …) Sec-Fetch başlıqları göndərmir və ya
//      adında robot sözü var: ona əvvəlki kimi og səhifəsi. Köhnə Safari (iOS < 16.4) Sec-Fetch göndərmir: ona da og səhifəsi, skript keçirir.
// Tapılan səhifə Cloudflare keşində 10 dəqiqə qalır (bot bir keçidi bir neçə dəfə soruşur).
// QIRMIZI XƏTT 2: yalnız lentdə olan sətirlər verilir (onlar content_policy.enforce-dan keçib); lentdə olmayan xəbər uydurulmur.
// QIRMIZI XƏTT 1: dəqiqəlik kanal sw.js ilə eyni qayda ilə oxunur (45 s güzəşt, yaranmamış dəqiqə soruşulmur: raw 404-ü 55 s keşləyir).
// ŞƏKİL (2026-11-10, sahib: «Facebook avto paylaşımlarda xəbərin şəkli olmur»): Sharing Debugger — wsrv.nl Facebook robotuna 403 verir,
//   kart şəkilsiz qalır. Verilən səhifədə og:image bu serverin ünvanıdır: /i/<id>.jpg. Worker şəkli özü gətirir (əvvəl wsrv.nl-dən
//   1200×630 JPEG, alınmasa mənbənin öz şəkli), 1 gün keşdə saxlayır; şəkil yoxdursa 302 → saytın og-default.png. Səhifə mətni
//   updater.share_page ilə eyni qalır (pageHtml), yalnız verilərkən og:image dəyişir (ownImage).
// Yükləmə: bu qovluqda «npx wrangler deploy» və ya Cloudflare panelində kodu yapışdırmaq; addımlar docs/x-worker.md-də.

const SITE = "https://8ulduz.az/";
const HOST = "https://www.8ulduz.az/"; // 2026-11-09, sahib: «x.» saytın adı ilə qarışmasın. Köhnə x.8ulduz.az keçidləri eyni Worker-ə gəlir (ikinci custom domain); kartlarda, og:url-də və keş açarında www.
const LIVE = "https://raw.githubusercontent.com/8ulduz/8ulduz/live/m/";
const LIVE_GRACE_S = 45, LIVE_MINUTES = 4;            // sw.js: slot = (indi − 45 s) / 60; cari və əvvəlki 3 dəqiqə
const FEEDS = ["data/latest.json", "data/first.json", "data/news.json"];
const PAGE_MS = 4000, FEED_MS = 6000;                 // bot ~10 s gözləyir; gec gələn cavab 302 ilə əvəz olunur
const CACHE_S = 600;
const ID = /^\/([0-9a-f]{16})\/?$/;
const IMG = /^\/i\/([0-9a-f]{16})\.jpg$/;
const IMG_CACHE_S = 86400, IMG_MS = 8000, IMG_MAX = 8e6; // Facebook şəkli 8 MB-dək qəbul edir
const LOCALE = { az: "az_AZ", ru: "ru_RU", en: "en_US", tr: "tr_TR" };
const ROW_FIELDS = ["id", "title", "summary", "source", "sourceUrl", "imageUrl", "category", "publishedAt", "lang", "video", "author"]; // updater.SHARE_ROW_FIELDS
const UA = "Mozilla/5.0 (compatible; 8ulduz-x/1.0; +https://8ulduz.az/)";
// Önizləmə robotları və skriptlər: adında bu sözlərdən biri olan heç vaxt yönləndirilmir (og səhifəsi alır).
const BOT = /bot|crawl|spider|slurp|fetch|preview|scrap|externalhit|facebook|meta-external|whatsapp|telegram(?!.*android)|twitterbot|linkedinbot|slack|discord|skype|viber|pinterestbot|pinterest\/0|embedly|iframely|vkshare|odkl|mastodon|bluesky|quora|outbrain|googlebot|google-|googleother|adsbot|mediapartners|feedfetcher|bingbot|bingpreview|msnbot|yandexbot|yandex\.com|duckduckbot|baiduspider|applebot|ia_archiver|archive\.org|curl|wget|python|java\/|okhttp|go-http|node-fetch|axios|libwww|lynx/i;
// Oxucunun brauzeri: səhifə naviqasiyası başlıqları var (Chrome 76+, Firefox 90+, Safari 16.4+, Android WebView, Facebook/Instagram daxili brauzeri) və adı robot deyil.
export const isReader = req => { const h = req.headers; return h.get("sec-fetch-dest") === "document" && h.get("sec-fetch-mode") === "navigate" && !BOT.test(h.get("user-agent") || ""); };

export default {
  async fetch(req, env, ctx) {
    const url = new URL(req.url);
    if (url.pathname === "/saglam") return new Response("ok", { headers: { "Cache-Control": "no-store" } });
    const im = url.pathname.match(IMG);
    if (im) return cardImage(im[1], ctx).catch(() => Response.redirect(`${SITE}assets/og-default.png`, 302));
    const m = url.pathname.match(ID);
    if (!m) return Response.redirect(SITE, url.hostname === "www.8ulduz.az" && url.pathname === "/" ? 301 : 302); // www kökü sayta daimi yönlənir (əvvəl Pages belə edirdi); qalan yad yollar müvəqqəti
    const id = m[1], h = (url.searchParams.get("h") || "").replace(/\D/g, "").slice(0, 8);
    if (isReader(req)) return Response.redirect(`${SITE}#/xeber/${id}${h ? "?h=" + h : ""}`, 302); // oxucu dərhal sayta (b= bölməsi lentdən tapılır, sayt onsuz da açır)
    try {
      const page = await sharePage(id, h, ctx);
      if (page) return page;
    } catch {}
    return Response.redirect(`${SITE}#/xeber/${id}${h ? "?h=" + h : ""}`, 302); // sayt arxivdən açır (app.js loadShared / scanArchives)
  },
};

// updater.share_page raw_app: #/xeber/<id>?b=<bölmə>&h=<arxiv budağının saatı>
export const appUrl = (id, category = "", h = "") => `${SITE}#/xeber/${id}?b=${category || ""}${h ? "&h=" + h : ""}`;

// Tapılan səhifə (Response) və ya null. Ardıcıllıq: keş → saytın /x/ səhifəsi → dəqiqəlik kanal → saytın lent faylları.
async function sharePage(id, h, ctx) {
  const cache = globalThis.caches?.default, key = new Request(HOST + id);
  if (cache) { const hit = await cache.match(key); if (hit) return hit; }
  let html = await staticPage(id);
  if (!html) { const row = await findRow(id); if (row) html = pageHtml(row, h); }
  if (!html) return null;
  html = ownImage(html, id);
  const res = new Response(html, { headers: { "Content-Type": "text/html; charset=utf-8", "Cache-Control": `public, max-age=${CACHE_S}`, "X-Robots-Tag": "noindex" } });
  if (cache) { const put = cache.put(key, res.clone()); if (ctx?.waitUntil) ctx.waitUntil(put); else await put.catch(() => {}); }
  return res;
}

async function get(url, ms) {
  return fetch(url, { headers: { "User-Agent": UA, "Accept": "text/html,application/json" }, signal: AbortSignal.timeout(ms), cf: { cacheTtl: 0 } });
}

// 1) updater.write_share_pages-in yazdığı səhifə; og:url bu serverə (Facebook kanonik ünvanı yenidən soruşur: Pages-ə yox, bura).
async function staticPage(id) {
  try {
    const r = await get(`${SITE}x/${id}`, PAGE_MS);
    if (r.status !== 200 || !/text\/html/.test(r.headers.get("Content-Type") || "")) return "";
    const html = await r.text();
    return html.includes('property="og:title"') ? withoutRefresh(html.replaceAll(`${SITE}x/${id}`, `${HOST}${id}`), id) : "";
  } catch { return ""; }
}

// Facebook robotu <meta http-equiv="refresh">-i izləyir: 8ulduz.az/#/xeber/… → baş səhifə → «8ulduz — Son xəbərlər» kartı (2026-11-08, canlı jurnal).
// Köhnə statik səhifələrdə (25 saatadək) refresh hələ var: burada atılır, canonical bu serverin ünvanı olur (og:url ilə eyni).
export const withoutRefresh = (html, id) => html.replace(/<meta http-equiv="refresh"[^>]*\/>\n?/, "").replace(/<link rel="canonical" href="[^"]*" \/>/, `<link rel="canonical" href="${HOST}${id}" />`);

// 2) Xəbərin sətri lentdə. Dəqiqəlik kanal ən təzədir (sayt faylları 10 dəqiqəyədək köhnə ola bilər), ona görə birinci.
export async function findRow(id, now = Date.now()) {
  const slot = Math.floor((now / 1000 - LIVE_GRACE_S) / 60);
  const minutes = Array.from({ length: LIVE_MINUTES }, (_, i) => `${LIVE}${slot - i}/latest.json`);
  return (await rowIn(minutes, id)) || rowIn(FEEDS.map(f => SITE + f), id);
}

async function rowIn(urls, id) {
  const found = await Promise.all(urls.map(async u => {
    try {
      const r = await get(u, FEED_MS);
      if (r.status !== 200) return null;
      const d = await r.json();
      if (removed(d, id)) return { gone: true };
      return (d.articles || []).find(a => a && a.id === id) || null;
    } catch { return null; }
  }));
  const row = found.find(Boolean);
  return row && !row.gone ? row : null;
}

// Redaksiyanın çıxardığı xəbər (latest.json «removed»): səhifə verilmir, 302 ilə sayt özü qərar verir.
const removed = (d, id) => Object.values(d.removed || {}).some(r => r && (r.id === id || (r.ids || []).includes(id)));

// og:image wsrv.nl-dirsə bu serverin /i/<id>.jpg ünvanı olur (Facebook wsrv.nl-dən ala bilmir). Saytın şəkli (og-default) dəyişmir.
export const ownImage = (html, id) => html.replace(/(<meta property="og:image" content=")https:\/\/wsrv\.nl\/[^"]*(" \/>)/, `$1${HOST}i/${id}.jpg$2`);

// Şəklin mənbəsi: lentdəki sətir, yoxdursa saytın /x/ səhifəsindəki wsrv ünvanının url= parametri.
async function imageSource(id) {
  const row = await findRow(id).catch(() => null);
  if (row) return /^https?:\/\//.test(String(row.imageUrl || "")) ? String(row.imageUrl) : "";
  const page = await staticPage(id);
  const m = page.match(/og:image" content="https:\/\/wsrv\.nl\/\?url=([^&"]+)/);
  return m ? decodeURIComponent(m[1]) : "";
}

const isImage = r => r && r.status === 200 && /^image\//.test(r.headers.get("Content-Type") || "") && +(r.headers.get("Content-Length") || 0) <= IMG_MAX;

// /i/<id>.jpg: kart şəkli. Əvvəl wsrv.nl (kiçik JPEG, WhatsApp 600 KB-dan böyüyü göstərmir), alınmasa mənbənin öz şəkli.
export async function cardImage(id, ctx) {
  const cache = globalThis.caches?.default, key = new Request(`${HOST}i/${id}.jpg`);
  if (cache) { const hit = await cache.match(key); if (hit) return hit; }
  const src = await imageSource(id);
  if (!src) return Response.redirect(`${SITE}assets/og-default.png`, 302);
  const ask = (u, extra = {}) => fetch(u, { headers: { "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0 Safari/537.36", "Accept": "image/avif,image/webp,image/jpeg,image/*", ...extra }, signal: AbortSignal.timeout(IMG_MS) }).catch(() => null);
  let r = await ask(`https://wsrv.nl/?url=${quote(src)}&w=1200&h=630&fit=cover&a=attention&output=jpg&q=78`);
  if (!isImage(r)) r = await ask(src, { "Referer": new URL(src).origin + "/" });
  if (!isImage(r)) return Response.redirect(`${SITE}assets/og-default.png`, 302);
  const res = new Response(r.body, { headers: { "Content-Type": r.headers.get("Content-Type"), "Cache-Control": `public, max-age=${IMG_CACHE_S}` } });
  if (cache) { const put = cache.put(key, res.clone()); if (ctx?.waitUntil) ctx.waitUntil(put); else await put.catch(() => {}); }
  return res;
}

// updater._xml: əvvəl açılır (ikiqat kodlanmış & qalmasın), sonra kodlanır.
export function xml(s) {
  let cur = String(s ?? "");
  for (let i = 0; i < 3; i++) { const nxt = unescapeHtml(cur); if (nxt === cur) break; cur = nxt; }
  return cur.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;").replace(/'/g, "&#x27;");
}
const ENT = { amp: "&", lt: "<", gt: ">", quot: '"', apos: "'", nbsp: " ", laquo: "«", raquo: "»", ndash: "–", mdash: "—", hellip: "…", rsquo: "’", lsquo: "‘", rdquo: "”", ldquo: "“" };
const unescapeHtml = s => s.replace(/&(#x([0-9a-f]+)|#(\d+)|([a-z]+));/gi, (m, _, hex, dec, name) => hex ? String.fromCodePoint(parseInt(hex, 16)) : dec ? String.fromCodePoint(+dec) : ENT[name.toLowerCase()] ?? m);
// updater._js: skriptin içində </script> və <!-- qırmır.
const js = v => JSON.stringify(v).replace(/<\//g, "<\\/").replace(/<!--/g, "<\\!--");

export const hourOf = a => (String(a.publishedAt || "").match(/^20(\d\d)-(\d\d)-(\d\d)T(\d\d)/) || []).slice(1).join("");

// updater.share_page + share_jump ilə eyni səhifə (tests/x-worker.test.cjs saytdakı x/<id>.html ilə tutuşdurur).
export function pageHtml(a, h = "") {
  const id = a.id, title = xml(String(a.title || "").replace(/\s+/g, " ").trim());
  let desc = String(a.summary || "").replace(/<[^>]+>|\s+/g, " ").trim();
  if (desc.length > 200) desc = desc.slice(0, 197).replace(/\s\S*$/, "") + "…";
  desc = xml(desc || `${a.source || "8ulduz"} · ${String(a.publishedAt || "").slice(0, 10)}`);
  const fallback = `${SITE}assets/og-default.png`, img = String(a.imageUrl || "");
  // Önizləmə şəkli proksidən 1200×630 JPEG (~100 KB): WhatsApp 600 KB-dan böyüyü göstərmir; silinmiş şəkil yerinə saytın şəkli.
  const image = xml(img.startsWith("https://") ? `https://wsrv.nl/?url=${quote(img)}&w=1200&h=630&fit=cover&a=attention&output=jpg&q=78&default=${quote(fallback)}` : fallback);
  const app = appUrl(id, a.category, hourOf(a) || h), lang = a.lang || "az";
  return `<!doctype html>
<html lang="${xml(lang)}"><head><meta charset="UTF-8" /><meta name="viewport" content="width=device-width, initial-scale=1.0" />
<title>${title} — 8ulduz</title><meta name="robots" content="noindex" /><link rel="canonical" href="${HOST}${id}" />
<meta property="og:type" content="article" /><meta property="og:site_name" content="8ulduz" /><meta property="og:title" content="${title}" />
<meta property="og:description" content="${desc}" /><meta property="og:url" content="${HOST}${id}" /><meta property="og:image" content="${image}" />
<meta property="og:locale" content="${LOCALE[lang] || "az_AZ"}" /><meta name="twitter:card" content="summary_large_image" />
${jump(a, app)}</head><body><p><a href="${xml(app)}">${title}</a> — <a href="${SITE}">8ulduz</a></p></body></html>
`;
}

// Python urllib.parse.quote(s, safe=""): yalnız A–Z a–z 0–9 _ . - ~ qalır.
const quote = s => encodeURIComponent(s).replace(/[!'()*]/g, c => "%" + c.charCodeAt(0).toString(16).toUpperCase());

// Facebook/WhatsApp-dan gələn oxucu: sətir sessionStorage-a, sayt xəbəri heç nəyi gözləmədən göstərir (app.js açılış, "x:"+id).
function jump(a, app) {
  const row = {};
  for (const k of ROW_FIELDS) if (a[k]) row[k] = k === "summary" ? String(a[k]).slice(0, 600) : a[k];
  const alts = (a.alts || []).slice(0, 20).filter(x => x && x.sourceUrl).map(x => Object.fromEntries(["id", "title", "source", "sourceUrl"].filter(k => x[k]).map(k => [k, x[k]])));
  if (alts.length) row.alts = alts;
  return `<script>try{sessionStorage.setItem(${js("x:" + a.id)},${js(JSON.stringify(row))})}catch(e){}location.replace(${js(app)})</script>\n`;
}
