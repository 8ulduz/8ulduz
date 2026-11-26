// Liqanın oyunları və canlı hesab (sahib 2026-11-26: «İstənilən liqanı seçəndə cədvəlin altında və bölmədə oyunlar və canlı skorlar
// olsun. Bu bütün turnirlərdə bu cür olsun»). Tənbəl modul: liqa səhifəsi (komanda.js) və futbol bloku (futbol.js: /bolme/cedvel/,
// ana səhifənin idman paneli) yükləyir, ilk açılışa düşmür. Qayda hər turnirdə eynidir, liqaya xüsusi xəritə yoxdur:
// - oyunlar liqanın öz faylındandır (data/futbol/<liqa>.json, main, 10 dəqiqədən bir);
// - liqa istidirsə (oyunun başlaması [indi − 30 dəq, indi + 4 saat], saatsız oyunda o gecə; updater.league_hot ilə eyni) dəqiqəlik
//   canlı kanaldan liqa-<liqa>.json gəlir: təzə cədvəl və yaxın günlərin oyunları canlı hesabla (updater.write_live_leagues);
// - blok səhifədə və vərəq görünən ikən liqa isti qaldıqca fayl dəqiqədə bir yenidən oxunur, dəyişəndə səhifə yenidən çəkilir.
// Yerləşdirmə oxuması yoxdur (tests/cpu-guard): blokun səhifədə olduğunu yalnız querySelector yoxlayır.
const LIVE = "https://raw.githubusercontent.com/8ulduz/8ulduz/live/m/";
const MIN = 60e3, HOUR = 60 * MIN, BAKU = 4 * HOUR;
const MON = ["yan", "fev", "mar", "apr", "may", "iyn", "iyl", "avq", "sen", "okt", "noy", "dek"];
const MONTH = ["yanvar", "fevral", "mart", "aprel", "may", "iyun", "iyul", "avqust", "sentyabr", "oktyabr", "noyabr", "dekabr"];
const esc = s => String(s ?? "").replace(/[&<>"']/g, c => `&#${c.charCodeAt(0)};`);
const at = g => Date.parse(g?.date || "");
const byKick = (a, b) => at(a) - at(b);
const bk = t => new Date(t + BAKU); // Bakı vaxtı (yay vaxtı yoxdur): UTC alıcıları ilə oxunur
const dayKey = t => bk(t).toISOString().slice(0, 10);
const hm = t => bk(t).toISOString().slice(11, 16);
const dm = t => `${bk(t).getUTCDate()} ${MON[bk(t).getUTCMonth()]}`;
export const isLive = g => !g.played && (g.live?.s === "live" || g.live?.s === "ht");
const isDone = g => !!g.played || g.live?.s === "ft";

// Oyunun «isti» pəncərəsi: updater._live_window ilə eyni.
export function windowOf(g) {
  const t = at(g);
  if (!Number.isFinite(t) || g.state === "off") return null;
  return g.day ? [t + 8 * HOUR, t + 20 * HOUR] : [t - 30 * MIN, t + 4 * HOUR];
}
export const hot = (doc, now = Date.now()) => (doc?.games || []).some(g => { const w = windowOf(g); return !!w && w[0] <= now && now <= w[1]; });

// Canlı nüsxə liqanın faylına: cədvəl ondan, [from, to] aralığının oyunları ondan, qalan oyunlar fayldan.
const MERGED = new WeakMap();
export function merge(doc, patch) {
  if (!doc || !patch || patch.id !== doc.id || !Array.isArray(patch.games)) return doc;
  const hit = MERGED.get(doc);
  if (hit?.patch === patch) return hit.out;
  const from = Date.parse(patch.from), to = Date.parse(patch.to);
  const keep = (doc.games || []).filter(g => { const t = at(g); return !(t >= from && t <= to); });
  const out = { ...doc, groups: patch.groups?.length || !doc.groups?.length ? patch.groups || [] : doc.groups, games: [...keep, ...patch.games].sort(byKick), liveAt: patch.at };
  MERGED.set(doc, { patch, out });
  return out;
}

async function get(url) {
  try { const r = await fetch(url, { cache: "no-store", mode: "cors", credentials: "omit" }); if (r.ok) return await r.json(); } catch {}
  return null;
}
const COPY = new Map();
const visible = () => globalThis.document?.visibilityState !== "hidden";
function pull(id, rerender) {
  let c = COPY.get(id);
  if (!c) COPY.set(id, c = { t: 0, patch: null, busy: false });
  if (c.busy || Date.now() - c.t < 55e3 || !visible()) return;
  c.busy = true; c.t = Date.now();
  const slot = Math.floor((Date.now() / 1000 - 45) / 60); // pipeline dəqiqənin faylını ~5–35-ci saniyədə yazır
  (async () => {
    let d = null;
    for (const m of [slot, slot - 1]) if (!d) d = await get(`${LIVE}${m}/liqa-${id}.json`);
    c.busy = false;
    if (d?.id === id && Array.isArray(d.games) && d.at !== c.patch?.at) { c.patch = d; rerender?.(false); }
  })();
}
// Blok səhifədədirsə dəqiqədə bir; səhifədən çıxanda dayanır.
let timer = null, watch = null;
function keep(id, rerender) {
  watch = { id, rerender };
  if (timer || !globalThis.document?.querySelector) return;
  const run = () => {
    timer = null;
    if (!watch || !globalThis.document?.querySelector(`[data-oy="${watch.id}"]`)) return;
    pull(watch.id, watch.rerender);
    timer = setTimeout(run, MIN);
    timer?.unref?.(); // Node (testlər): proses taymeri gözləməsin
  };
  timer = setTimeout(run, MIN);
  timer?.unref?.();
}
// Liqanın faylı (isti ikən canlı nüsxə ilə). İsti deyilsə fayl olduğu kimi.
export function use(doc, rerender) {
  if (!doc?.id || !hot(doc)) return doc;
  pull(doc.id, rerender);
  keep(doc.id, rerender);
  return merge(doc, COPY.get(doc.id)?.patch);
}
// Futbol bloku üçün liqanın faylı (komanda.js öz faylını özü gətirir), 10 dəqiqə yaddaşda. Fayl və ya canlı nüsxə gələndə blok
// yerində yenilənir (draw): bütöv səhifə çəkilişi oxucu səhifə ilə işləyərkən təxirə düşür (requestRender), blok isə gözləməsin.
const FILES = new Map();
export function league(id) {
  if (!/^[a-z0-9-]+$/.test(id || "")) return null;
  let f = FILES.get(id);
  if (!f || (!f.busy && Date.now() - f.t > 10 * MIN)) {
    FILES.set(id, f = { t: Date.now(), doc: f?.doc || null, busy: true });
    const mine = f;
    get(new URL(`../data/futbol/${id}.json`, import.meta.url).href).then(d => {
      mine.busy = false;
      if (d && Array.isArray(d.games)) { mine.doc = d; draw(id); } else mine.t = Date.now() - 10 * MIN + 30e3;
    });
  }
  return f.doc ? use(f.doc, () => draw(id)) : null;
}
function draw(id) {
  const el = globalThis.document?.querySelector(`[data-oy="${id}"]`), doc = FILES.get(id)?.doc;
  if (el && doc) el.outerHTML = block(use(doc, () => draw(id))) || `<div data-oy="${id}"></div>`;
}

const CSS = ".oy{margin:16px 0}.oy .sec-h{display:flex;align-items:baseline;gap:10px}.oy-on{color:#e11d48;font-weight:800;font-size:13px}.oy h3{margin:12px 0 2px;font-size:13px;font-weight:700;color:var(--muted)}.oy ul{list-style:none;margin:0;padding:0;max-width:640px}.oy li{display:grid;grid-template-columns:74px minmax(0,1fr) auto minmax(0,1fr);gap:8px;align-items:center;padding:7px 0;border-bottom:1px solid var(--border);font-size:14px}.oy li>a,.oy li>span{color:inherit;text-decoration:none;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}.oy li>.h{text-align:right}.oy li>b{min-width:46px;text-align:center;font-variant-numeric:tabular-nums}.oy small{color:var(--muted);font-size:12px;line-height:1.25}.oy li.on small,.oy li.on>b{color:#e11d48;font-weight:800}.oy-src{color:var(--muted);font-size:12px;margin:6px 0 0}@media(min-width:768px){.oy li{grid-template-columns:104px minmax(0,1fr) auto minmax(0,1fr)}}";
function css() {
  const d = globalThis.document;
  if (!d?.head || d.getElementById("oy-css")) return;
  const s = d.createElement("style");
  s.id = "oy-css"; s.textContent = CSS;
  d.head.append(s);
}
// Bütöv günlər: ən çox `days` oyun günü, `max` oyuna çatanda dayanır (gün yarımçıq kəsilmir).
function wholeDays(list, days, max) {
  const out = [];
  let seen = 0, last = "";
  for (const g of list) {
    const k = dayKey(at(g));
    if (k !== last) { if (seen >= days || out.length >= max) break; seen++; last = k; }
    out.push(g);
  }
  return out;
}
function when(g, kind, now) {
  const t = at(g), l = g.live || {};
  if (isLive(g)) return l.s === "ht" ? "Fasilə" : `● ${l.min ? `${esc(l.min)}'` : "Canlı"}`;
  if (g.state === "off") return "Təxirə salınıb";
  const pen = g.pen ? ` · pen ${esc(g.pen)}` : "";
  if (kind === "past") return dm(t) + pen;
  if (isDone(g)) return "Bitdi" + pen;
  if (kind === "next") return g.day ? dm(t) : `${dm(t)}, ${hm(t)}`;
  if (l.s === "pp") return "Təxirə salınıb";
  return g.day ? "Gecə" : t <= now ? "Gözlənilir" : hm(t); // saatsız oyun (NBA) Bakıda gecə oynanır
}
// HTML: canlılar, bu gün, növbəti oyun günləri, son nəticələr. Oyun yoxdursa boş sətir.
export function block(doc, { now = Date.now() } = {}) {
  const games = (doc?.games || []).filter(g => Number.isFinite(at(g)) && g.home && g.away);
  if (!doc?.id || !games.length) return "";
  css();
  const today = dayKey(now), teams = doc.teams || {};
  const live = games.filter(isLive).sort(byKick), rest = games.filter(g => !isLive(g));
  const todays = rest.filter(g => dayKey(at(g)) === today).sort(byKick);
  const next = wholeDays(rest.filter(g => dayKey(at(g)) > today && !isDone(g) && g.state !== "off").sort(byKick), 3, 12);
  const past = wholeDays(rest.filter(g => dayKey(at(g)) < today && isDone(g)).sort((a, b) => at(b) - at(a)), 2, 10);
  const name = slug => { const t = teams[slug] || {}; return esc(t.short || t.name || slug); };
  const team = (slug, cls) => `<a${cls} href="#/komanda/${esc(doc.id)}/${encodeURIComponent(slug)}">${name(slug)}</a>`;
  const score = g => g.played && g.hs != null ? `${esc(g.hs)} : ${esc(g.as)}` : g.live?.hs != null && g.live.s !== "pp" ? `${esc(g.live.hs)} : ${esc(g.live.as)}` : "–";
  const row = kind => g => `<li${isLive(g) ? ' class="on"' : ""}><small>${when(g, kind, now)}</small>${team(g.home, ' class="h"')}<b>${score(g)}</b>${team(g.away, "")}</li>`;
  const part = (title, list, kind) => list.length ? `<h3>${title}</h3><ul>${list.map(row(kind)).join("")}</ul>` : "";
  const [, m, d] = today.split("-").map(Number);
  const body = part("Canlı", live, "live") + part(`Bu gün, ${d} ${MONTH[m - 1]}`, todays, "today") + part("Növbəti oyunlar", next, "next") + part("Son nəticələr", past, "past");
  if (!body) return "";
  const src = doc.liveAt && games.some(g => g.live) ? `<p class="oy-src">Canlı hesab: TheSportsDB, football-data.org · yoxlanıb ${hm(Date.parse(doc.liveAt))}</p>` : "";
  return `<section class="tm-sec oy" data-oy="${esc(doc.id)}"><div class="sec-h"><h2>Oyunlar</h2>${live.length ? `<span class="oy-on">● ${live.length} canlı</span>` : ""}</div>${body}${src}</section>`;
}
