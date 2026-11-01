// Komanda səhifəsi (#/komanda/<liga>/<ad>). Kod, üslub və məlumat yalnız bu səhifə açılanda yüklənir: baş səhifənin sürətinə toxunmur.
// Məlumat: data/futbol/ (updater.py, update_team_pages): pfl.az, Vikipediya, OpenLigaDB. Heyət tabı və zona zolaqları yalnız faylda məlumat olanda görünür.
const DIR = "data/futbol/";
const FILE_TTL = 10 * 60e3;
const FAIL_WAIT = 30e3;
const TABS = [["", "Baxış"], ["oyunlar", "Oyunlar"], ["cedvel", "Cədvəl"], ["heyet", "Heyət"], ["xeberler", "Xəbərlər"]];
const NOTE_AZ = {
  "Champions League": "Çempionlar Liqası", "Champions League qualifying": "Çempionlar Liqasının seçmə mərhələsi",
  "Europa League": "Avropa Liqası", "Europa League qualifying": "Avropa Liqasının seçmə mərhələsi",
  "Conference League": "Konfrans Liqası", "Conference League qualifying": "Konfrans Liqasının seçmə mərhələsi",
  "Relegation": "Aşağı liqaya düşmə", "Relegated": "Aşağı liqaya düşmə", "Relegation playoff": "Aşağı liqa üçün pley-off",
  "Qualifies for round of 16": "1/8 finala çıxış", "Knockout phase playoffs - seeded": "Pley-off (səbətli)", "Knockout phase playoffs - unseeded": "Pley-off (səbətsiz)", "Eliminated": "Mübarizədən çıxır",
};
const POS_AZ = [["gk", "Qapıçılar"], ["df", "Müdafiəçilər"], ["mf", "Yarımmüdafiəçilər"], ["fw", "Hücumçular"], ["", "Digər"]];
// Xəbər süzgəci: «Sabah» və «Qəbələ» həm də başqa mənadadır, ona görə yalnız idman bölməsi və başqa idman növlərinin xəbəri olmadan.
const OTHER_SPORT = /basketbol|voleybol|həndbol|tennis|cüdo|güləş|boks|futzal|şahmat|шахмат|gimnast|basketball|баскетбол|волейбол/iu;
// Avroliqa klubu futbol klubu ilə adaşdır (Real Madrid, Barselona): basketbol sözü olmayan xəbər düşmür.
const BASKET = /basketbol|basketball|баскетбол|avroliqa|euroleague|евролиг/iu;
const TOPIC_ALIAS = { "Internazionale": "İnter", "Paris Saint-Germain": "PSG" };
const SUFFIX = "(?:in|nin|un|nun|ün|nün|ın|nın|a|e|i|u|ya|ye|ni|nu|na|ne|la|le|dan|den|ndan|nden|da|de|nda|nde|nı|nü|s|а|у|е|я|ю|ы|и|ь|ом|ем)?";

// Komandanın bu yarışdakı oyunları: yarış başına bir dəfə hesablanır (cədvəldə hər sətir soruşur).
const BY_TEAM = new WeakMap();
export function gamesOf(doc, slug) {
  let map = BY_TEAM.get(doc);
  if (!map) {
    map = new Map();
    for (const g of doc?.games || []) for (const side of [g.home, g.away]) { if (!map.has(side)) map.set(side, []); map.get(side).push(g); }
    BY_TEAM.set(doc, map);
  }
  return map.get(slug) || [];
}
export function resultOf(g, slug) {
  if (!g.played || g.hs == null || g.as == null) return "";
  const mine = g.home === slug ? g.hs : g.as, other = g.home === slug ? g.as : g.hs;
  return mine > other ? "w" : mine < other ? "l" : "d";
}
export function formOf(games, slug, n = 5) {
  return games.filter(g => g.played).sort(byKick).slice(-n).map(g => resultOf(g, slug));
}
const byKick = (x, y) => (x.date || "9999").localeCompare(y.date || "9999");
// Oynanmış və qarşıdakı oyunlar. Vaxtı keçib nəticəsi gəlməyən oyun «qarşıdakı» sayılmır, təxirə salınan da.
export function splitGames(games, now = Date.now()) {
  const sorted = [...games].sort(byKick);
  const played = sorted.filter(g => g.played);
  const next = sorted.filter(g => !g.played && g.state !== "off" && (!g.date || new Date(g.date).getTime() > now));
  return { played, next };
}
export function rowOf(doc, slug) {
  for (const g of doc?.groups || []) { const row = g.rows.find(r => r.team === slug); if (row) return { row, group: g }; }
  return null;
}
// «Türkiyə Süper Liqası, 1-ci yer»
export function standingLine(doc, slug, ordinal) {
  const hit = rowOf(doc, slug);
  return hit ? `${doc.name}, ${ordinal(hit.row.pos)} yer` : doc.name;
}
// Cədvəlin zona izahı: ESPN-in verdiyi qeydlər, cədvəldəki sırası ilə.
export function zonesOf(rows) {
  const seen = new Map();
  for (const r of rows) if (r.note && r.color && !seen.has(r.note)) seen.set(r.note, r.color);
  return [...seen].map(([note, color]) => ({ note: NOTE_AZ[note] || note, color }));
}
// Komandanın digər yarışları (Kubok, Çempionlar Liqası). Əvəzedicilər ayrı komandadır, oyunları qarışmır.
export function otherLeagues(index, league, slug) {
  if (league.reserve) return [];
  return (index.leagues || []).filter(l => l.id !== league.id && !l.reserve && (l.sport || "football") === (league.sport || "football") && l.teams?.includes(slug));
}
// Ad birbaşa regex-ə düşür, mövzusu olmayan komanda üçün: böyük hərf saxlanır, ingiliscə «nice» Nitsa sayılmasın.
export function nameRx(names) {
  const safe = [...new Set(names.filter(n => n && n.length >= 3))].map(n => n.replace(/[.*+?^${}()|[\]\\]/g, "\\$&")).join("|");
  return safe ? new RegExp(`(?<![\\p{L}\\p{N}])(?:${safe})${SUFFIX}(?![\\p{L}\\p{N}])`, "u") : null;
}

export function mountTeam(d) {
  const { S, esc, card, byDate, sized, shortDT, ordinal, ago, decode, clubMatches, topics, withArchive, loadArchive, months, requestJSON, freshUrl, requestRender } = d;
  const files = new Map();
  function file(path) {
    let f = files.get(path);
    if (!f || Date.now() - f.at > FILE_TTL) {
      f = { at: Date.now(), doc: f?.doc || null, failed: false };
      files.set(path, f);
      const mine = f;
      requestJSON(freshUrl(path), {}, 12000).then(({ d: doc }) => { mine.doc = doc; })
        .catch(() => { mine.failed = true; mine.at = Date.now() - FILE_TTL + FAIL_WAIT; })
        .finally(() => requestRender(false));
    }
    return f;
  }
  const leaguePath = (league, key) => `${DIR}${league.id}${key === league.ready[0].key ? "" : `-${key}`}.json`;
  const href = (liga, slug, tab = "", key = "") => `#/komanda/${liga}/${encodeURIComponent(slug)}${tab ? `/${tab}` : ""}${key ? `?s=${key}` : ""}`;
  const logo = (url, size, name = "") => url ? `<img src="${esc(sized(url, size * 2))}" alt="" width="${size}" height="${size}" loading="lazy" decoding="async" referrerpolicy="no-referrer" onerror="this.style.visibility='hidden'">` : `<span class="tm-nologo" style="width:${size}px;height:${size}px;font-size:${Math.round(size * 0.46)}px" aria-hidden="true">${esc([...name][0] || "")}</span>`;
  const message = (title, text, back = "") => `<div class="empty"><h1 style="color:var(--fg)">${esc(title)}</h1><p>${esc(text)}</p>${back}</div>`;
  const home = `<a href="#/" style="color:var(--primary);font-weight:700">← Baş səhifəyə qayıt</a>`;
  const asof = d => { const [, m, day] = String(d).split("-").map(Number); return m && day ? `${day} ${months[m - 1]} oyunlarına qədər` : ""; };
  const leagueHref = (id, key) => `#/komanda/${id}${key ? `?s=${key}` : ""}`;
  // Kubokda cədvəl yoxdur: liqanın səhifəsi klubların siyahısıdır.
  const clubList = doc => `<ul class="tm-clubs">${Object.keys(doc.teams || {}).sort((a, b) => doc.teams[a].name.localeCompare(doc.teams[b].name, "az")).map(slug => `<li><a href="${href(doc.id, slug)}">${logo(doc.teams[slug].logo, 24, doc.teams[slug].name)}<span>${esc(doc.teams[slug].name)}</span></a></li>`).join("")}</ul>`;

  // --- oyun kartları
  function gameCard(g, doc, slug) {
    const side = (who, score) => { const t = doc.teams[who] || {}; return `<span class="tm-side${who === slug ? " me" : ""}">${logo(t.logo, 20, t.short || t.name)}<span class="nm">${esc(t.short || t.name || who)}</span>${g.played ? `<b>${esc(score)}</b>` : ""}</span>`; };
    const res = resultOf(g, slug), other = g.home === slug ? g.away : g.home;
    const state = g.played ? (g.pen ? `Pen. ${esc(g.pen)}` : "Bitib") : g.state === "live" ? "Oyun gedir" : g.state === "off" ? "Təxirə salınıb" : g.date && new Date(g.date).getTime() < Date.now() ? "Nəticə gözlənilir" : "";
    return `<a class="tm-game" href="${href(doc.id, other)}" title="${esc(g.stadium || "")}">
      <span class="tm-comp">${esc(doc.name)}${g.round ? ` · ${esc(/^\d+$/.test(g.round) ? `${ordinal(g.round)} tur` : g.round)}` : ""}</span>
      ${side(g.home, g.hs)}${side(g.away, g.as)}
      <span class="tm-when"><time datetime="${esc(g.date || "")}">${g.date ? esc(g.day ? shortDT(g.date).split(",")[0] : shortDT(g.date)) : "Vaxtı elan olunmayıb"}</time>${state ? `<em>${state}</em>` : ""}${res ? `<i class="tm-r ${res}">${res === "w" ? "Q" : res === "d" ? "H" : "M"}</i>` : ""}</span></a>`;
  }
  // Tam siyahı: aylara bölünür (Oyunlar tabı və vərəq eyni siyahıdır).
  function fullList(rows, slug) {
    if (!rows.length) return `<p class="muted tm-none">Oyun tapılmadı.</p>`;
    const byMonth = new Map();
    for (const { g, doc } of [...rows].sort((x, y) => byKick(x.g, y.g))) {
      const when = g.date ? new Date(g.date) : null;
      const key = when ? `${months[when.getMonth()]} ${when.getFullYear()}` : "Vaxtı elan olunmayıb";
      if (!byMonth.has(key)) byMonth.set(key, []);
      byMonth.get(key).push(gameCard(g, doc, slug));
    }
    return [...byMonth].map(([m, cards]) => `<h3 class="tm-month">${esc(m[0].toLocaleUpperCase("az") + m.slice(1))}</h3><div class="tm-games list">${cards.join("")}</div>`).join("");
  }

  // --- cədvəl: ilk iki sütun yerində qalır, qalanı yana sürüşür
  function basketTable(doc, rows, slug, key) {
    const body = rows.map(r => { const t = doc.teams[r.team] || {}; return `<tr${r.team === slug ? ` class="me" aria-current="true"` : ""}><td class="pos">${esc(r.pos)}</td><td class="club"><a href="${href(doc.id, r.team, "", key)}">${logo(t.logo, 18)}<span>${esc(t.short || t.name || r.team)}</span></a></td><td>${esc(r.p)}</td><td>${esc(r.w)}</td><td>${esc(r.l)}</td><td>${(r.pct * 100).toFixed(1)}</td><td class="pts">${esc(r.gb)}</td></tr>`; }).join("");
    return `<div class="tm-scroll" tabindex="0" role="region" aria-label="Turnir cədvəli"><table class="tm-table"><thead><tr><th class="pos">#</th><th class="club">Komanda</th><th title="Oyun">O</th><th title="Qələbə">Q</th><th title="Məğlubiyyət">M</th><th>%</th><th title="Liderdən geri">Geridə</th></tr></thead><tbody>${body}</tbody></table></div>`;
  }
  function tableHtml(doc, rows, slug, key) {
    if (doc.sport === "basketball") return basketTable(doc, rows, slug, key);
    const body = rows.map(r => {
      const t = doc.teams[r.team] || {};
      const bar = r.color && /^#[0-9a-f]{3,8}$/i.test(r.color) ? ` style="box-shadow:inset 3px 0 0 ${r.color}"` : "";
      const form = formOf(gamesOf(doc, r.team), r.team).map(x => `<i class="tm-r ${x}">${x === "w" ? "Q" : x === "d" ? "H" : "M"}</i>`).join("");
      return `<tr${r.team === slug ? ` class="me" aria-current="true"` : ""}><td class="pos"${bar}${r.note ? ` title="${esc(NOTE_AZ[r.note] || r.note)}"` : ""}>${esc(r.pos)}</td><td class="club"><a href="${href(doc.id, r.team, "", key)}">${logo(t.logo, 18, t.short || t.name)}<span>${esc(t.short || t.name || r.team)}</span></a></td><td>${esc(r.p)}</td><td>${esc(r.w)}</td><td>${esc(r.d)}</td><td>${esc(r.l)}</td><td>${esc(r.gf)}:${esc(r.ga)}</td><td>${r.gd > 0 ? "+" : ""}${esc(r.gd)}</td><td class="pts">${esc(r.pts)}</td>${doc.games?.length ? `<td class="form">${form}</td>` : ""}</tr>`;
    }).join("");
    return `<div class="tm-scroll" tabindex="0" role="region" aria-label="Turnir cədvəli"><table class="tm-table"><thead><tr><th class="pos">#</th><th class="club">Komanda</th><th title="Oyun">O</th><th title="Qələbə">Q</th><th title="Heç-heçə">H</th><th title="Məğlubiyyət">M</th><th>Qol</th><th title="Fərq">F</th><th>Xal</th>${doc.games?.length ? `<th class="form">Son 5</th>` : ""}</tr></thead><tbody>${body}</tbody></table></div>`;
  }
  function legend(rows) {
    const zones = zonesOf(rows);
    return zones.length ? `<ul class="tm-legend">${zones.map(z => `<li><i style="background:${/^#[0-9a-f]{3,8}$/i.test(z.color) ? z.color : "transparent"}"></i>${esc(z.note)}</li>`).join("")}</ul>` : "";
  }
  function picker(index, league, doc, slug, tab, key) {
    const leagues = [league, ...(slug ? otherLeagues(index, league, slug) : [])];
    const season = league.ready.length > 1 ? `<label>Mövsüm<select data-tm-go>${league.ready.map((s, i) => `<option value="${esc(slug ? href(league.id, slug, tab, i ? s.key : "") : `#/komanda/${league.id}${i ? `?s=${s.key}` : ""}`)}"${s.key === key ? " selected" : ""}>${esc(s.label)}</option>`).join("")}</select></label>` : "";
    const comp = leagues.length > 1 ? `<label>Yarış<select data-tm-go>${leagues.map(l => `<option value="${esc(href(l.id, slug, tab))}"${l.id === league.id ? " selected" : ""}>${esc(l.name)}</option>`).join("")}</select></label>` : "";
    return comp || season ? `<div class="tm-pick">${comp}${season}</div>` : "";
  }
  function tablesHtml(doc, slug, key) {
    if (!doc.groups?.length) return `<p class="muted tm-none">Bu yarışda turnir cədvəli yoxdur.</p>`;
    return doc.groups.map(g => `${doc.groups.length > 1 && g.name ? `<h3 class="tm-month">${esc(g.name)}</h3>` : ""}${tableHtml(doc, g.rows, slug, key)}${legend(g.rows)}`).join("");
  }
  // Baxışdakı qısa cədvəl: komanda və qonşuları.
  function miniTable(doc, slug) {
    const hit = rowOf(doc, slug);
    if (!hit) return "";
    const rows = hit.group.rows, at = rows.indexOf(hit.row), from = Math.max(0, Math.min(at - 2, rows.length - 5));
    return tableHtml(doc, rows.slice(from, from + 5), slug, "");
  }

  // --- xəbərlər: app.js-dəki klub mövzuları, mövzusu olmayan komanda üçün adın özü
  function topicFor(name) {
    const alias = TOPIC_ALIAS[name];
    if (alias) return alias;
    return topics.find(t => t.name === name || clubMatches({ title: name, source: "" }, t.name))?.name || null;
  }
  function newsOf(team, doc) {
    loadArchive("idman");
    const basket = doc?.sport === "basketball";
    const topic = basket ? null : topicFor(team.name);
    const rx = topic ? null : nameRx([team.name, team.short]);
    const pool = withArchive("idman", S.data?.articles || []);
    return byDate(pool.filter(a => {
      if (a.category !== "idman" || (basket ? doc.id === "avroliqa" && !BASKET.test(decode(a.title + " " + (a.summary || ""))) : OTHER_SPORT.test(decode(a.title || "")))) return false;
      return topic ? clubMatches(a, topic) : !!rx?.test(decode(`${a.title} ${a.summary || ""}`));
    }));
  }
  function newsBlock(team, slice, more, doc) {
    const list = newsOf(team, doc);
    if (!list.length) return `<p class="muted tm-none">${esc(team.name)} haqqında son 5 gündə xəbər tapılmadı.</p>`;
    const rows = slice ? list.slice(0, slice) : list.slice(0, S.shown || 48);
    return `<div class="grid">${rows.map(card).join("")}</div>${slice && list.length > slice ? more : !slice && list.length > rows.length ? `<button class="loadmore" data-act="more">Daha çox (${list.length - rows.length})</button>` : ""}`;
  }

  // --- heyət
  function squadBlock(league, slug, name) {
    const f = file(`${DIR}heyet-${league.id}.json`);
    const players = f.doc?.teams?.[slug]?.players;
    if (!players?.length) return `<p class="muted tm-none">${f.failed ? "Heyət yüklənmədi." : f.doc ? `${esc(name)} üçün heyət məlumatı yoxdur.` : "Yüklənir…"}</p>`;
    const wiki = f.doc.teams[slug].wiki;
    const credit = wiki ? `<p class="tm-src muted">Heyət: <a href="https://en.wikipedia.org/wiki/${encodeURIComponent(wiki.replace(/ /g, "_"))}" target="_blank" rel="noopener noreferrer">Vikipediya</a>, <a href="https://creativecommons.org/licenses/by-sa/4.0/" target="_blank" rel="noopener noreferrer">CC BY-SA 4.0</a></p>` : "";
    return POS_AZ.map(([key, label]) => {
      const rows = players.filter(p => (p.pos || "") === key);
      return rows.length ? `<section class="tm-sec tm-squad"><h3 class="tm-month">${label}</h3><ul>${rows.map(p => `<li><b>${esc(p.no || "")}</b>${p.flag ? `<img src="${esc(sized(p.flag, 40))}" alt="${esc(p.country || "")}" title="${esc(p.country || "")}" width="20" height="20" loading="lazy" decoding="async" referrerpolicy="no-referrer" onerror="this.remove()">` : ""}<span>${esc(p.name)}</span>${p.age ? `<em>${esc(p.age)} yaş</em>` : ""}</li>`).join("")}</ul></section>` : "";
    }).join("") + credit;
  }

  function view(r) {
    const index = file(`${DIR}index.json`);
    if (!index.doc) return index.failed ? message("Komanda məlumatı açılmadı", "İnternet bağlantınızı yoxlayın. Səhifə özü yenidən cəhd edəcək.", home) : `<div class="tm-wait"><div class="skel" style="height:96px"></div><div class="skel" style="height:220px"></div></div>`;
    const league = (index.doc.leagues || []).find(l => l.id === r.liga);
    if (!league) return message("Bu liqanın səhifəsi yoxdur", "Hazırda yalnız məlumatı alınan liqaların komanda səhifələri açılır.", home);
    const current = league.ready[0].key;
    const key = league.ready.some(s => s.key === r.season) ? r.season : current;
    const main = file(leaguePath(league, key));
    if (!main.doc) return main.failed ? message("Komanda məlumatı açılmadı", "İnternet bağlantınızı yoxlayın. Səhifə özü yenidən cəhd edəcək.", home) : `<div class="tm-wait"><div class="skel" style="height:96px"></div><div class="skel" style="height:220px"></div></div>`;
    const doc = main.doc, seasonKey = key === current ? "" : key;
    const checked = index.doc.checked?.[league.id];
    const when = doc.asof ? asof(doc.asof) : "";
    const link = (url, text) => url ? `<a href="${esc(url)}" target="_blank" rel="noopener noreferrer">${esc(text)}</a>` : esc(text);
    const named = x => link(x.source_url || x.url, x.source);
    // Səhifədə göstərilən bütün yarışların mənbəyi: lisenziya bunu tələb edir.
    const source = (list = [doc]) => `<p class="tm-src muted">Mənbə: ${[...[...new Map(list.map(x => [x.source, x])).values()].map(named), ...list.filter(x => x.source_url && x.url).slice(0, 1).map(x => link(x.url, "Vikipediya"))].join(", ")}${when ? ` · ${esc(when)}` : ""}${checked ? ` · yoxlanıb ${esc(ago(checked))}` : ""}</p>`;
    const slug = r.team;
    if (!slug || !doc.teams?.[slug]) {
      // Komandasız ünvan və ya bu mövsüm liqada olmayan komanda: liqanın cədvəli.
      document.title = `${doc.name} — 8ulduz`;
      return `<div class="page-h"><div><h1>${esc(doc.name)}</h1><p>${esc(doc.season)}${slug ? " · bu mövsüm komanda bu yarışda deyil" : ""}</p></div></div>${picker(index.doc, league, doc, slug && league.teams.includes(slug) ? slug : "", "cedvel", key)}<section class="tm-sec">${doc.groups?.length ? tablesHtml(doc, "", seasonKey) : clubList(doc)}</section>${source()}`;
    }
    const team = doc.teams[slug];
    document.title = `${team.name} — 8ulduz`;
    document.querySelector('meta[name="description"]')?.setAttribute("content", `${team.name}: oyunlar, turnir cədvəli və son xəbərlər.`);
    const hasSquad = !seasonKey && league.heyet?.includes(slug);
    const hasGames = doc.games?.length || (!seasonKey && otherLeagues(index.doc, league, slug).some(l => !l.source?.startsWith("Viki")));
    const tab = TABS.some(([k]) => k === r.tab) && (r.tab !== "heyet" || hasSquad) && (r.tab !== "cedvel" || doc.groups?.length) && (r.tab !== "oyunlar" || hasGames) ? r.tab : "";
    const head = `<header class="tm-head">${logo(team.logo, 56, team.name)}<div><p><a class="tm-league" href="${leagueHref(league.id, seasonKey)}">${esc(doc.name)}</a>${esc(standingLine(doc, slug, ordinal).slice(doc.name.length))}${seasonKey ? ` · ${esc(doc.season)}` : ""}</p><h1>${esc(team.name)}</h1></div></header>`;
    const tabs = `<nav class="tm-tabs" aria-label="Komanda bölmələri">${TABS.filter(([k]) => (k !== "heyet" || hasSquad) && (k !== "cedvel" || doc.groups?.length) && (k !== "oyunlar" || hasGames)).map(([k, label]) => `<a href="${href(league.id, slug, k, seasonKey)}"${k === tab ? ` class="on" aria-current="page"` : ""}>${label}</a>`).join("")}</nav>`;
    // Baxışda oyunlar bütün yarışlardan: cari mövsümdə komandanın digər yarışlarının faylları da gəlir. Oyunlar tabı yalnız seçilmiş yarışı göstərir.
    const needGames = hasGames && tab === "";
    const others = needGames && !seasonKey ? otherLeagues(index.doc, league, slug).map(l => ({ l, f: file(leaguePath(l, l.ready[0].key)) })) : [];
    const docs = [doc, ...others.map(o => o.f.doc).filter(Boolean)];
    const rows = docs.flatMap(x => gamesOf(x, slug).map(g => ({ g, doc: x })));
    S.teamSheet = needGames ? { title: `${team.name}: bütün oyunlar`, html: fullList(rows, slug) } : null;
    let body = "";
    if (tab === "") {
      const { played, next } = splitGames(rows.map(x => x.g));
      const cards = list => list.map(g => gameCard(g, rows.find(x => x.g === g).doc, slug)).join("");
      const form = formOf(gamesOf(doc, slug), slug);
      body = `${form.length ? `<section class="tm-sec tm-form"><h2>Son nəticələr</h2><div>${form.map(x => `<i class="tm-r ${x}">${x === "w" ? "Q" : x === "d" ? "H" : "M"}</i>`).join("")}</div></section>` : ""}
        ${!hasGames ? "" : `<section class="tm-sec"><div class="sec-h"><h2>${seasonKey ? "Oyunlar" : "Növbəti oyunlar"}</h2><button type="button" class="more" data-tm-sheet>Bütün oyunlar →</button></div>${seasonKey ? "" : next.length ? `<div class="tm-games">${cards(next.slice(0, 3))}</div>` : `<p class="muted tm-none">Növbəti oyun hələ elan olunmayıb.</p>`}</section>
        <section class="tm-sec"><div class="sec-h"><h2>Son oyunlar</h2></div>${played.length ? `<div class="tm-games">${cards(played.slice(-3).reverse())}</div>` : `<p class="muted tm-none">Bu mövsüm hələ oyun olmayıb.</p>`}</section>`}
        ${doc.groups?.length ? `<section class="tm-sec"><div class="sec-h"><h2>Turnir cədvəli</h2><a class="more" href="${href(league.id, slug, "cedvel", seasonKey)}">Bütün cədvəl →</a></div>${miniTable(doc, slug)}</section>` : ""}
        <section class="tm-sec"><div class="sec-h"><h2>Xəbərlər</h2></div>${newsBlock(team, 6, `<a class="loadmore tm-more" href="${href(league.id, slug, "xeberler", seasonKey)}">Bütün xəbərlər →</a>`, doc)}</section>`;
    } else if (tab === "oyunlar") {
      body = `${picker(index.doc, league, doc, slug, tab, key)}<section class="tm-sec">${rows.length ? fullList(rows, slug) : `<p class="muted tm-none">${esc(doc.name)} oyunları hələ əlavə olunmayıb.</p>`}</section>`;
    } else if (tab === "cedvel") {
      body = `${picker(index.doc, league, doc, slug, tab, key)}<section class="tm-sec">${tablesHtml(doc, slug, seasonKey)}</section>`;
    } else if (tab === "heyet") {
      body = `<section class="tm-sec">${squadBlock(league, slug, team.name)}</section>`;
    } else {
      body = `<section class="tm-sec"><div class="sec-h"><h2>Xəbərlər</h2></div>${newsBlock(team, 0, "", doc)}</section>`;
    }
    return `${head}${tabs}${body}${source(docs)}`;
  }

  // --- vərəq: telefonda aşağıdan açılır, geri düyməsi bağlayır
  function openSheet() {
    const sheet = S.teamSheet;
    if (!sheet) return;
    const dlg = document.createElement("dialog");
    dlg.className = "tm-sheet";
    dlg.innerHTML = `<div class="tm-sheet-h"><h2>${esc(sheet.title)}</h2><button type="button" data-tm-close aria-label="Bağla">×</button></div><div class="tm-sheet-b">${sheet.html}</div>`;
    document.body.append(dlg);
    history.pushState({ tmSheet: 1 }, "", location.href);
    const close = () => dlg.close();
    window.addEventListener("popstate", close);
    window.addEventListener("hashchange", close);
    dlg.addEventListener("click", e => { if (e.target === dlg || e.target.closest("[data-tm-close]")) close(); });
    dlg.addEventListener("close", () => {
      window.removeEventListener("popstate", close);
      window.removeEventListener("hashchange", close);
      dlg.remove();
      if (history.state?.tmSheet) history.back();
    });
    dlg.showModal();
  }
  document.addEventListener("click", e => { if (e.target.closest?.("[data-tm-sheet]")) openSheet(); });
  document.addEventListener("change", e => { if (e.target.matches?.("[data-tm-go]")) location.hash = e.target.value; });
  return { view, openSheet, topicFor, newsOf };
}
