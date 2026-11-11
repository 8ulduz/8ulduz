// Google Analytics 4, yüngül göndərici (sahib, 2026-11-06: əsas statistika GA4 olsun, sürət qorunsun).
// Google-un gtag.js-i (153 KB sıxılmış, 444 KB kod) yüklənmir: baxış birbaşa GA4-ün /g/collect ünvanına gedir.
// Yalnız ümumi say: təsadüfi cihaz nömrəsi (cid), sessiya nömrəsi, səhifə, başlıq, dil, ekran ölçüsü. Ad, e-poçt, konum yoxdur.
// Fayl app.js-dən ayrıdır və yalnız sayt açılandan sonra (enableAnalytics) yüklənir: ilk ekrana təsiri yoxdur.
const KEY = "8ulduz-ga", SESSION_MS = 30 * 60e3, ENGAGED_MS = 10e3;
const GA = "https://www.google-analytics.com/g/collect?";
let seq = 0, engaged = false;

function send(q) {
  const u = GA + q;
  try { if (navigator.sendBeacon?.(u)) return; } catch {}
  fetch(u, { method: "POST", mode: "no-cors", keepalive: true, credentials: "omit" }).catch(() => {});
}

function state(now) {
  let s = null;
  try { s = JSON.parse(localStorage.getItem(KEY) || "null"); } catch {}
  const first = !s?.cid;
  if (first) s = { cid: `${Math.floor(Math.random() * 2147483647)}.${Math.floor(now / 1000)}`, sct: 0 };
  const start = !s.sid || now - (s.last || 0) > SESSION_MS;
  if (start) { s.sid = Math.floor(now / 1000); s.sct = (s.sct || 0) + 1; }
  s.last = now;
  try { localStorage.setItem(KEY, JSON.stringify(s)); } catch {}
  return { s, first, start };
}

// Hash marşrutu (#/bolme/gundem) GA4 hesabatında ayrıca səhifə kimi görünsün: /bolme/gundem
export function pageUrl(path, loc = location) {
  const [base, hash = ""] = String(path || "/").split("#");
  const route = hash.replace(/^\/?/, "/").split("?")[0];
  return loc.origin + (route !== "/" ? route : base || "/") + loc.search;
}

// Xəbər keçidi (sahib 2026-11-11): «news_outbound_click» — news_domain (www-siz), news_url, news_title. «out» kimi ikinci dəfə getmir.
export function news(a) {
  const art = a?.closest?.("article");
  if (!a?.matches || a.matches(".soc-p") || !(art || a.closest(".phrow,.track,.alerts,.foot-news"))) return null;
  const t = (a.querySelector("h1,h2,h3,h4,.t") || art?.querySelector("h1,h2,h3,h4") || a).textContent.trim();
  return t ? [a.hostname.toLowerCase().replace(/^www\./, ""), a.href, t] : null;
}

// ev: hadisə (sahib 2026-11-07: keçidləri ölçmək) — "out-apa.az" (mənbəyə keçid), "share-wa" (paylaşma), "install-…".
// GA4-də hadisənin adı birinci hissədir (out, share, install), qalanı «type» parametridir.
export function hit(id, path, title, now = Date.now(), ev = "", a) {
  if (!/^G-[A-Z0-9]+$/.test(String(id || "")) || !/^(www\.)?8ulduz\.az$/.test(location.hostname)) return null; // yerli sınaq statistikaya düşmür
  const { s, first, start } = state(now);
  const [name, ...type] = String(ev).split("-"), n = name === "out" && news(a);
  const q = new URLSearchParams({ v: "2", tid: id, cid: s.cid, sid: String(s.sid), sct: String(s.sct), _p: String(Math.floor(Math.random() * 1e9)),
    _s: String(++seq), en: n ? "news_outbound_click" : ev ? name.replace(/\W/g, "_").slice(0, 40) || "event" : "page_view", dl: pageUrl(path), dt: String(title || "8ulduz").slice(0, 300),
    ul: String(navigator.language || "").toLowerCase(), sr: `${screen.width || 0}x${screen.height || 0}` });
  if (n) ["domain", "url", "title"].forEach((k, i) => q.set("ep.news_" + k, n[i].slice(0, 100))); // GA4 həddi: 100 işarə
  else if (ev) q.set("ep.type", type.join("-").slice(0, 100));
  if (ev) { q.set("seg", "1"); send(q); return q; }
  const ref = document.referrer;
  if (seq === 1 && ref && !ref.startsWith(location.origin)) q.set("dr", ref);
  if (first) q.set("_fv", "1");
  if (start) { q.set("_ss", "1"); q.set("_nsi", "1"); }
  if (engaged) q.set("seg", "1");
  send(q);
  // 10 saniyə açıq qalan səhifə: «fəal sessiya» (GA4-də bounce/engagement düzgün çıxsın)
  if (!engaged) setTimeout(() => {
    if (engaged || document.visibilityState !== "visible") return;
    engaged = true;
    const e = new URLSearchParams(q); e.set("en", "user_engagement"); e.set("seg", "1"); e.set("_et", String(ENGAGED_MS)); e.set("_s", String(++seq));
    e.delete("_fv"); e.delete("_ss"); e.delete("_nsi"); e.delete("dr");
    send(e);
  }, ENGAGED_MS);
  return q;
}
