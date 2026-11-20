// Futbol bloku (ana səhifənin «İdman nəticələri və cədvəllər» paneli, liqa səhifəsi): tənbəl modul — yalnız panel açılanda və ya
// liqa səhifəsində yüklənir (sahib 2026-11-19: «kodu … təmizləyib yer açmaq»). Kod app.js-dən olduğu kimi köçürülüb;
// əsas koddakı köməkçilər app.js-in fbHelpers() funksiyası ilə verilir.

// «Bu gün» (sahib 2026-11-20: canlı hesab, «pulsuz həll»): data/canli.json — yeniləyici football-data.org-un pulsuz planından yazır
// (13 turnir, vəziyyət və hesab), alınmayanda OpenLigaDB; Türkiyə, Rusiya, Azərbaycan API-Football-dan dəqiqə ilə. Fayl əvvəl dəqiqəlik canlı kanaldan, alınmasa saytdan; panel açıq və canlı oyun
// varsa dəqiqədə bir yenidən oxunur. Açar yoxdursa fayl yoxdur, blok çıxmır.
const LIVE_URL = "https://raw.githubusercontent.com/8ulduz/8ulduz/live/m/";
let live = null, liveAt = 0, liveBusy = false;
async function liveGet(url, opt) {
  try { const r = await fetch(url, opt); if (r.ok) { const d = await r.json(); if (Array.isArray(d?.matches)) return d; } } catch {}
  return null;
}
async function liveLoad(rerender) {
  if (liveBusy) return;
  liveBusy = true; liveAt = Date.now();
  const slot = Math.floor((Date.now() / 1000 - 45) / 60);
  let d = null;
  for (const m of [slot, slot - 1]) if (!d) d = await liveGet(`${LIVE_URL}${m}/canli.json`, { cache: "no-store", mode: "cors", credentials: "omit" });
  d ||= await liveGet(`${new URL("../data/canli.json", import.meta.url).href}?t=${Math.floor(Date.now() / 6e4)}`);
  liveBusy = false;
  if (d && JSON.stringify(d.matches) !== JSON.stringify(live?.matches)) { live = d; rerender?.(false); }
}
const SV = (inner, title) => `<svg viewBox="0 0 30 20" width="18" height="12" aria-hidden="true" style="flex:none;border-radius:2px;box-shadow:0 0 0 1px #0003;vertical-align:-1px">${inner}</svg>`;
const H3 = (a, b, c) => SV(`<rect width="30" height="20" fill="${b}"/><rect width="30" height="6.67" fill="${a}"/><rect y="13.33" width="30" height="6.67" fill="${c}"/>`);
const V3 = (a, b, c) => SV(`<rect width="30" height="20" fill="${b}"/><rect width="10" height="20" fill="${a}"/><rect x="20" width="10" height="20" fill="${c}"/>`);
const FL = {
  az: H3("#00b5e2", "#ef3340", "#509e2f"),
  eng: SV('<rect width="30" height="20" fill="#fff"/><path d="M15 0v20M0 10h30" stroke="#ce1124" stroke-width="4"/>'),
  sco: SV('<rect width="30" height="20" fill="#0065bd"/><path d="M0 0l30 20M30 0L0 20" stroke="#fff" stroke-width="3"/>'),
  esp: SV('<rect width="30" height="20" fill="#aa151b"/><rect y="5" width="30" height="10" fill="#f1bf00"/>'),
  ita: V3("#009246", "#fff", "#ce2b37"), fra: V3("#0055a4", "#fff", "#ef4135"), bel: V3("#000", "#fdda24", "#ef3340"),
  ger: H3("#000", "#dd0000", "#ffce00"), ned: H3("#ae1c28", "#fff", "#21468b"), rus: H3("#fff", "#0039a6", "#d52b1e"),
  tur: SV('<rect width="30" height="20" fill="#e30a17"/><circle cx="11.5" cy="10" r="5" fill="#fff"/><circle cx="12.8" cy="10" r="4" fill="#e30a17"/><circle cx="18.5" cy="10" r="1.6" fill="#fff"/>'),
  por: SV('<rect width="30" height="20" fill="#da291c"/><rect width="12" height="20" fill="#046a38"/><circle cx="12" cy="10" r="3.5" fill="#ffe900"/>'),
  ksa: SV('<rect width="30" height="20" fill="#006c35"/><rect x="7" y="12" width="16" height="1.6" fill="#fff"/>'),
  bra: SV('<rect width="30" height="20" fill="#009c3b"/><path d="M15 3l11 7-11 7-11-7z" fill="#ffdf00"/><circle cx="15" cy="10" r="3.6" fill="#002776"/>'),
  usa: SV('<rect width="30" height="20" fill="#fff"/><path d="M0 1.5h30M0 4.6h30M0 7.7h30M0 10.8h30M0 13.9h30M0 17h30" stroke="#b22234" stroke-width="1.55"/><rect width="13" height="10.8" fill="#3c3b6e"/>'),
  eu: SV('<rect width="30" height="20" fill="#003399"/><circle cx="15" cy="10" r="5" fill="none" stroke="#ffcc00" stroke-width="1.4" stroke-dasharray="1.2 1.4"/>'),
};
// id -> [bayraq, ölkə, liqa]; Azərbaycan liqaları (football.json) dünya siyahısında deyil
const LIQA = {
  "eng.1": ["eng", "İngiltərə", "Premyer Liqa"], "eng.2": ["eng", "İngiltərə", "Çempionşip"], "esp.1": ["esp", "İspaniya", "La Liga"],
  "ita.1": ["ita", "İtaliya", "Seriya A"], "ger.1": ["ger", "Almaniya", "Bundesliqa"], "fra.1": ["fra", "Fransa", "Liqa 1"],
  "tur.1": ["tur", "Türkiyə", "Süper Liq"], "por.1": ["por", "Portuqaliya", "Primeyra Liqa"], "ned.1": ["ned", "Hollandiya", "Eredivizie"],
  "bel.1": ["bel", "Belçika", "Pro Liqa"], "sco.1": ["sco", "Şotlandiya", "Premyership"], "rus.1": ["rus", "Rusiya", "Premyer Liqa"],
  "ksa.1": ["ksa", "Səudiyyə Ərəbistanı", "Pro Liqa"], "bra.1": ["bra", "Braziliya", "Seriya A"], "usa.1": ["usa", "ABŞ", "MLS"],
  "uefa.champions": ["", "UEFA", "Çempionlar Liqası"], "uefa.europa": ["", "UEFA", "Avropa Liqası"], "uefa.conference": ["", "UEFA", "Konfrans Liqası"],
  nba: ["usa", "ABŞ", "NBA"], euroleague: ["eu", "Avropa", "Avroliqa"],
};
// Menyunun liqa düyməsi (app.js navLeagues; sahib 2026-11-19: «ölkənin adı qalın, liqa adı nazik, ölkə bayrağı»): bayraq, qalın ölkə,
// nazik liqa. id sports.json-dakı liqa id-sidir; tanınmayan liqa adı ilə qalır.
export function navLabel(id, label, esc) {
  const [fl, country, name] = LIQA[id] || ["", "", label];
  return `${FL[fl] || ""}${country ? `<b>${esc(country)}</b>` : ""}<span${country ? ' style="font-weight:400"' : ""}>${esc(name)}</span>`;
}
export const flag = k => FL[k] || "";

export function view(h, list) {
  const { S, MONTHS, esc, sized, decode, lc, byDate, teamHref, safeHref, clubAz, ordTur, shortDT, OUT, txt, fbLeagues } = h;
  const asofLabel = d => { const [, m, day] = String(d).split("-").map(Number); return m && day ? `${day} ${MONTHS[m - 1]} oyunlarına qədər` : ""; };
  const GROUP_AZ = { "Eastern Conference": "Şərq", "Western Conference": "Qərb", "League Phase": "Liqa mərhələsi" };
  const FB_HEAD = '<table class="fb-table"><thead><tr><th>#</th><th>Komanda</th><th>O</th><th>Q</th><th>H</th><th>M</th><th>Qol</th><th>F</th><th>Xal</th></tr></thead><tbody>'; // futbol cədvəlinin başlığı (iki yerdə)
  function worldTable(l, g) {
    const rows = g.rows || [];
    if (l.sport === "basketball") return `<table class="fb-table"><thead><tr><th>#</th><th>Komanda</th><th>Q</th><th>M</th><th>%</th><th>Geridə</th></tr></thead><tbody>${rows.map(t => `<tr><td>${esc(t.pos)}</td><td class="nm">${t.logo ? `<img src="${esc(sized(t.logo, 96, 1))}" alt="" loading="lazy" referrerpolicy="no-referrer" data-fail="rm">` : ""}${esc(t.team)}</td><td>${esc(t.w)}</td><td>${esc(t.l)}</td><td>${(t.pct * 100).toFixed(1)}</td><td>${esc(String(t.gb ?? "-"))}</td></tr>`).join("")}</tbody></table>`;
    return `${FB_HEAD}${rows.map(t => `<tr>${t.color ? `<td style="box-shadow:inset 3px 0 0 ${esc(t.color)}" title="${esc(t.note || "")}">` : "<td>"}${esc(t.pos)}</td><td class="nm">${t.logo ? `<img src="${esc(sized(t.logo, 96, 1))}" alt="" loading="lazy" referrerpolicy="no-referrer" data-fail="rm">` : ""}${esc(t.team)}</td><td>${esc(t.p)}</td><td>${esc(t.w)}</td><td>${esc(t.d)}</td><td>${esc(t.l)}</td><td>${esc(t.gf)}:${esc(t.ga)}</td><td>${t.gd > 0 ? "+" : ""}${esc(t.gd)}</td><td><b>${esc(t.pts)}</b></td></tr>`).join("")}</tbody></table>`;
  }
  function footballBlock(list) {
    const all = fbLeagues();
    const fb = all[Math.min(S.fbLeague || 0, Math.max(0, all.length - 1))];
    const news = byDate(list.filter(a => {
      const title = lc(decode(a.title));
      if (/(?:basketbol|voleybol|həndbol|tennis|cüdo|güləş|boks|futzal)/u.test(title)) return false;
      return a.category === "idman" && /futbol|premyer|liqa|qarabağ|neftçi|qarabag|sabah fk|mill[iı]/iu.test(title);
    })).slice(0, 4);
    // Liqa məlumatı yoxdursa blok yoxdur.
    if (!fb) return "";
    const tab = (S.fbTab === "table" && !fb.table?.length) ? "results" : (S.fbTab || "results");
    const picker = all.length > 1 ? `<div class="fb-leagues" role="tablist" aria-label="Liqalar">${all.map((l, i) => `${i > 0 && (l.world !== all[i - 1].world || l.sport !== all[i - 1].sport) ? `<i class="sep" aria-hidden="true"></i>` : ""}<button type="button" class="pill${l === fb ? " on" : ""}${l.sport === "basketball" ? " bb" : ""}" data-fbleague="${i}" role="tab" aria-selected="${l === fb}">${leagueLabel(l)}</button>`).join("")}</div>` : "";
    if (fb.world) {
      const groups = fb.groups || [];
      const gi = Math.min(Number(S.fbTab) || 0, groups.length - 1);
      const gtabs = groups.length > 1 ? `<div class="fb-groups">${groups.map((g, i) => `<button type="button" class="pill${i === gi ? " on" : ""}" data-fbtab="${i}">${esc(GROUP_AZ[g.name] || g.name)}</button>`).join("")}</div>` : "";
      const wteams = (groups[gi]?.rows || []).slice(0, 12).map(t => `<a href="${teamHref(fb, t.full || t.team)}" class="fb-team" title="${esc(t.full || t.team)}"><b class="pos">${esc(t.pos)}</b>${t.logo ? `<img src="${esc(sized(t.logo, 96, 1))}" alt="" loading="lazy" decoding="async" referrerpolicy="no-referrer" data-fail="rm">` : ""}<span class="nm">${esc(t.team)}</span><span class="pts"><b>${fb.sport === "basketball" ? `${esc(t.w)}-${esc(t.l)}` : t.pts}</b> ${fb.sport === "basketball" ? "" : "xal"}</span></a>`).join("");
      return `<section class="foot"><div class="sec-h"><h2>${fb.sport === "basketball" ? "Basketbol" : "Futbol"}</h2><span class="cnt">${esc(fb.league)}${fb.season ? ` · ${esc(fb.season)}` : ""}${fb.asof ? ` · ${esc(asofLabel(fb.asof))}` : ""}${fb.stale ? " · köhnə məlumat" : ""}</span><a class="more" href="${safeHref(fb.link)}" target="_blank" rel="noopener noreferrer">Vikipediya ↗</a></div>
        ${picker}
        <div class="strip"><div class="fb-teams">${wteams}</div></div>
        ${gtabs}
        <div class="fb-pane">${groups[gi] ? worldTable(fb, groups[gi]) : ""}</div></section>`;
    }
    const teams = fb.table.map(t => `<a href="${teamHref(fb, t.team)}" class="fb-team" title="${esc(t.team)}: ${esc(t.p)} oyun, ${esc(t.w)} Q · ${esc(t.d)} H · ${esc(t.l)} M, qol ${esc(t.gf)}:${esc(t.ga)}"><b class="pos">${esc(t.pos)}</b>${t.logo ? `<img src="${esc(sized(t.logo, 96, 1))}" alt="" loading="lazy" decoding="async" referrerpolicy="no-referrer" data-fail="rm">` : ""}<span class="nm">${esc(clubAz(t.team))}</span><span class="pts"><b>${esc(t.pts)}</b> xal</span></a>`).join("");
    const tabs = [["results", "Nəticələr", fb.roundPlayed], ["fixtures", "Təqvim", fb.roundNext], ["table", "Turnir cədvəli", ""], ["scorers", "Bombardirlər", ""]]
      .filter(([k]) => k !== "table" || fb.table?.length)
      .map(([k, l, r]) => `<button type="button" class="fb-tab${tab === k ? " on" : ""}" data-fbtab="${k}"><span>${l}${r ? `<small>${esc(/^\d+$/.test(String(r)) ? ordTur(r) + " tur" : String(r))}</small>` : ""}</span><i>→</i></button>`).join("");
    const game = g => `<li><b>${esc(clubAz(g.home))}</b><span>${g.played ? `${esc(g.hs ?? "–")} : ${esc(g.as ?? "–")}` : "–"}</span><b>${esc(clubAz(g.away))}</b><time datetime="${esc(g.date || "")}" title="${esc(g.stadium || "")}">${esc(shortDT(g.date))}</time></li>`;
    let pane = "";
    if (tab === "results") pane = fb.results?.length ? `<ul class="games">${fb.results.map(game).join("")}</ul>` : `<p class="muted foot-note">Nəticə hələ yoxdur.</p>`;
    else if (tab === "fixtures") pane = fb.fixtures?.length ? `<ul class="games">${fb.fixtures.map(game).join("")}</ul>` : `<p class="muted foot-note">Növbəti tur hələ elan olunmayıb.</p>`;
    else if (tab === "table") pane = `${FB_HEAD}${fb.table.map(t => `<tr><td>${esc(t.pos)}</td><td class="nm"><a href="${teamHref(fb, t.team)}">${esc(clubAz(t.team))}</a></td><td>${esc(t.p)}</td><td>${esc(t.w)}</td><td>${esc(t.d)}</td><td>${esc(t.l)}</td><td>${esc(t.gf)}:${esc(t.ga)}</td><td>${t.gd > 0 ? "+" : ""}${esc(t.gd)}</td><td><b>${esc(t.pts)}</b></td></tr>`).join("")}</tbody></table>`;
    else if (tab === "scorers") pane = fb.scorers?.length ? `<ol class="fb-scorers">${fb.scorers.map(s => `<li><b>${esc(s.name)}</b> <span class="muted">${esc(clubAz(s.club))}</span><em>${esc(s.goals)} qol</em></li>`).join("")}</ol>` : `<p class="muted foot-note">Bombardir siyahısı alınmadı.</p>`;
    return `<section class="foot"><div class="sec-h"><h2>Futbol</h2><span class="cnt">${esc(fb.league || "")}${fb.season ? ` · ${esc(fb.season)}` : ""}${fb.stale ? " · köhnə məlumat" : ""}</span><a class="more" href="${safeHref(fb.link || "https://pfl.az/")}" target="_blank" rel="noopener noreferrer">pfl.az ↗</a></div>
      ${picker}
      <div class="fb-top${teams ? "" : " noteams"}">${teams ? `<div class="strip"><div class="fb-teams">${teams}</div></div>` : ""}<nav class="fb-links" aria-label="Futbol bölmələri">${tabs}</nav></div>
      <div class="fb-pane">${pane}</div>
      ${news.length ? `<div class="foot-news">${news.map(a => `<a href="${safeHref(a.sourceUrl)}" ${OUT}>${txt(a.title)}</a>`).join("")}</div>` : ""}</section>`;
  }
  // 9-cu, 10-cu, 1-ci, 3-cü, 6-cı tur: sıra sayı şəkilçisi


  // Liqa düyməsi (sahib 2026-11-19: «liqaların adları səliqəli yazılsın: ölkənin adı qalın, liqa adı nazik, ölkə bayrağı olsun»).
  // Bayraq SVG-dir (Windows-da bayraq emojisi hərf kimi görünür); app.css-də yer olmadığı üçün stil burada.
  const leagueLabel = l => {
    const [fl, country, name] = l.world ? (LIQA[l.id] || ["", "", l.league || l.short || ""]) : ["az", "Azərbaycan", l.short || l.league || ""];
    return `<span style="display:inline-flex;align-items:center;gap:5px;white-space:nowrap">${FL[fl] || ""}${country ? `<b style="font-weight:800">${esc(country)}</b>` : ""}<span style="font-weight:400">${esc(name)}</span></span>`;
  };
  // Bu günün oyunları: canlılar əvvəl, sonra başlayacaqlar, sonra bitənlər (sıranı yeniləyici qoyur)
  const LIVE_FL = { PL: "eng", ELC: "eng", PD: "esp", SA: "ita", BL1: "ger", FL1: "fra", DED: "ned", PPL: "por", BSA: "bra", TSL: "tur", RPL: "rus", AZE: "az" };
  const LIVE_COMP = { PL: "Premyer Liqa", ELC: "Çempionşip", PD: "La Liqa", SA: "Seriya A", BL1: "Bundesliqa", FL1: "Liqa 1", DED: "Eredivizie",
    PPL: "Primeyra Liqa", CL: "Çempionlar Liqası", BSA: "Braziliya", CLI: "Libertadores", WC: "Dünya çempionatı", EC: "Avropa çempionatı", TSL: "Süper Liq", RPL: "Rusiya", AZE: "Premyer Liqa" };
  function liveBlock() {
    const on = (live?.matches || []).some(m => m.s === "live" || m.s === "ht");
    if (globalThis.document?.visibilityState === "visible" && Date.now() - liveAt > (on ? 60e3 : 5 * 60e3)) liveLoad(h.requestRender);
    const rows = (live?.matches || []).slice(0, 14);
    if (!rows.length) return "";
    const tm = d => { const x = new Date(d); return Number.isNaN(+x) ? "" : x.toLocaleTimeString("az-AZ", { hour: "2-digit", minute: "2-digit", timeZone: "Asia/Baku" }); };
    const st = m => m.s === "live" ? `<b style="color:#e11d48">● ${m.min ? esc(m.min) + "'" : "Canlı"}</b>` : m.s === "ht" ? '<b style="color:#e11d48">Fasilə</b>' : m.s === "ft" ? "Bitdi" : m.s === "pp" ? "Təxirə salınıb" : esc(tm(m.t));
    const sc = m => m.hs == null ? "–" : `${esc(m.hs)} : ${esc(m.as)}`;
    const li = m => `<li style="display:grid;grid-template-columns:92px 1fr auto 1fr;gap:8px;align-items:center;padding:6px 0;border-bottom:1px solid var(--border)"><small style="display:flex;flex-direction:column;line-height:1.2"><span style="display:inline-flex;gap:4px;align-items:center">${FL[LIVE_FL[m.c]] || ""}<span style="white-space:nowrap;overflow:hidden;text-overflow:ellipsis">${esc(LIVE_COMP[m.c] || m.c)}</span></span>${st(m)}</small><b style="text-align:right">${esc(m.h)}</b><span style="font-weight:800;min-width:44px;text-align:center">${sc(m)}</span><b>${esc(m.a)}</b></li>`;
    return `<section class="foot"><div class="sec-h"><h2>Bu gün</h2><span class="cnt">${on ? "canlı hesab" : "oyunlar və nəticələr"}</span><a class="more" href="https://www.football-data.org/" target="_blank" rel="noopener noreferrer" title="football-data.org, OpenLigaDB, API-Football">Mənbə ↗</a></div><ul style="list-style:none;margin:0;padding:0;font-size:14px">${rows.map(li).join("")}</ul></section>`;
  }
  return liveBlock() + footballBlock(list);
}
