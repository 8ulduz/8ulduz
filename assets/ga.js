// GA4 yüngül göndərici (sahib 2026-11-06: əsas statistika GA4, sürət qorunsun): gtag.js yüklənmir, baxış birbaşa /g/collect-ə gedir.
// Yalnız ümumi say (təsadüfi cid, sessiya, səhifə, başlıq, dil, ekran); ad, e-poçt, konum yoxdur. Açılışdan sonra yüklənir.
const KEY = "8ulduz-ga", SESSION_MS = 30 * 60e3, ENGAGED_MS = 10e3;
const GA = "https://www.google-analytics.com/g/collect?";
let seq = 0, engaged = false;

function send(q) {
  const u = GA + q;
  try { if (navigator.sendBeacon?.(u)) return; } catch {}
  fetch(u, { method: "POST", mode: "no-cors", keepalive: true, credentials: "omit" }).catch(() => {});
}

let mem = null; // yaddaş bağlıdırsa hər baxış yeni oxucu sayılmasın
function state(now) {
  let s = null;
  try { s = JSON.parse(localStorage.getItem(KEY) || "null"); } catch {}
  s ||= mem;
  const first = !s?.cid;
  if (first) s = { cid: `${Math.floor(Math.random() * 2147483647)}.${Math.floor(now / 1000)}`, sct: 0 };
  const start = !s.sid || now - (s.last || 0) > SESSION_MS;
  if (start) { s.sid = Math.floor(now / 1000); s.sct = (s.sct || 0) + 1; }
  s.last = now; mem = s;
  try { localStorage.setItem(KEY, JSON.stringify(s)); } catch {}
  return { s, first, start };
}

// #/bolme/gundem hesabatda /bolme/gundem səhifəsidir
export function pageUrl(path, loc = location) {
  const [base, hash = ""] = String(path || "/").split("#");
  const route = hash.replace(/^\/?/, "/").split("?")[0];
  return loc.origin + (route !== "/" ? route : base || "/") + loc.search;
}

// Xəbər keçidi (sahib 2026-11-11): «news_outbound_click» (news_domain, news_url, news_title), «out» ikinci dəfə getmir.
export function news(a) {
  const art = a?.closest?.("article");
  if (!a?.matches || a.matches(".soc-p") || !(art || a.closest(".phrow,.track,.alerts,.foot-news"))) return null;
  const el = a.querySelector("h1,h2,h3,h4,.t") || art?.querySelector("h1,h2,h3,h4") || a, tag = el.querySelector?.(".tag")?.textContent || ""; // etiket başlıq deyil
  const t = el.textContent.replace(tag, "").trim();
  return t ? [a.hostname.toLowerCase().replace(/^www\./, ""), a.href, t] : null;
}

// ev (sahib 2026-11-07): "out-apa.az", "share-wa", "install-…": ad birinci hissədir, qalanı «type».
// Robot, gecə sürət yoxlaması (2026-11-17: ~96% idi), yerli sınaq sayılmır.
const BOT = /bot\b|crawl|spider|facebookexternalhit|meta-external|HeadlessChrome|Lighthouse/i;
export const robot = (n = navigator) => !!n.webdriver || BOT.test(n.userAgent || "");
export function hit(id, path, title, now = Date.now(), ev = "", a) {
  if (!/^G-[A-Z0-9]+$/.test(String(id || "")) || !/^(www\.)?8ulduz\.az$/.test(location.hostname) || robot()) return null;
  if (!ev && document.visibilityState === "hidden") { // gizli səhifə: görünəndə
    const go = () => document.visibilityState === "visible" && (document.removeEventListener("visibilitychange", go), hit(id, path, title));
    document.addEventListener?.("visibilitychange", go);
    return null;
  }
  const { s, first, start } = state(now);
  const [name, ...type] = String(ev).split("-"), n = name === "out" && news(a);
  const q = new URLSearchParams({ v: "2", tid: id, cid: s.cid, sid: String(s.sid), sct: String(s.sct), _p: String(Math.floor(Math.random() * 1e9)),
    _s: String(++seq), en: n ? "news_outbound_click" : ev ? name.replace(/\W/g, "_").slice(0, 40) || "event" : "page_view", dl: pageUrl(path), dt: String(title || "8ulduz").slice(0, 300),
    ul: String(navigator.language || "").toLowerCase(), sr: `${screen.width || 0}x${screen.height || 0}` });
  if (n) ["domain", "url", "title"].forEach((k, i) => q.set("ep.news_" + k, n[i].slice(0, 100)));
  else if (ev) q.set("ep.type", type.join("-").slice(0, 100));
  if (ev) { q.set("seg", "1"); send(q); return q; }
  const ref = document.referrer;
  if (seq === 1 && ref && !ref.startsWith(location.origin)) q.set("dr", ref);
  if (first) q.set("_fv", "1");
  if (start) { q.set("_ss", "1"); q.set("_nsi", "1"); }
  if (engaged) q.set("seg", "1");
  send(q);
  // 10 saniyə açıq qalan səhifə: «fəal sessiya»
  if (!engaged) setTimeout(() => {
    if (engaged || document.visibilityState !== "visible") return;
    engaged = true;
    const e = new URLSearchParams(q); e.set("en", "user_engagement"); e.set("seg", "1"); e.set("_et", String(ENGAGED_MS)); e.set("_s", String(++seq));
    e.delete("_fv"); e.delete("_ss"); e.delete("_nsi"); e.delete("dr");
    send(e);
  }, ENGAGED_MS);
  return q;
}
