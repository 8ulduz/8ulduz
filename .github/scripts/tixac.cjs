#!/usr/bin/env node
// Avtomatik tıxac ölçüsü (sahib, 2026-11-14: «avtomatik tıxac xəbərləri hazırlayıb verən sistem qur», sonra «Bəli, Mapbox»).
// Mənbə: Mapbox Directions API, «driving-traffic» profili (Azərbaycan Mapbox-un tıxac örtüyündədir). Kartsız hesab:
// ayda 10 000 sorğu pulsuz, həddi keçəndə sorğu sadəcə rədd olunur, pul tutulmur.
// TomTom yoxlanıb (2026-11-14): açar işləyir, amma Bakıda (və Tbilisidə) yol məlumatı yoxdur — «Point too far from nearest
// existing segment»; İstanbulda var. Waze-in xəritəsindən məlumat çəkmək onun şərtlərinə ziddir: qurulmur.
//
// Bir dövrə = 3 sorğu: 3 uzun marşrut (hər biri 3 nöqtə). Mapbox marşrutu hissələrə bölüb hər hissənin tıxac dərəcəsini verir
// (low/moderate/heavy/severe); hissələr addımların (küçələrin) adı ilə toplanır, beləcə marşrut boyu tıxac olan hər küçə adı ilə
// çıxır. Səhər (Bakı 14:00-dək) marşrut şəhərə doğru, sonra şəhərdən çıxışa doğrudur.
// Büdcə (4 marşrut, 8 əsas yol): pik saatlarda (07–10, 17–20) hər 6 dəq = 60 dövrə, qalan vaxt (10–17, 20–22) hər 30 dəq = 18 dövrə;
// 78 × 4 = 312/gün,
// 31 günlük ayda ≈ 9 700 < 10 000. Gündə 330 sorğudan çox getmir (DAILY_CAP, vəziyyət faylında sayılır).
// Açar yalnız MAPBOX_TOKEN mühit dəyişənindədir; heç vaxt çap olunmur, xətada yalnız HTTP kodu və açarsız səbəb yazılır.
// Nəticə: tixac.json (marşrutlar, tıxaclı küçələr, son 12 saatın avtomatik xəbərləri) → «tixac» budağı → saytın Tıxac səhifəsi.
// İstifadə: node tixac.cjs <çıxış qovluğu> [əvvəlki tixac.json]   |   node tixac.cjs --yoxla
"use strict";
const fs = require("node:fs"), path = require("node:path");

// [en, enlik] cütləri (Mapbox sırası). Ad oxucu üçündür; küçə adları Mapbox-dan gəlir.
const ROUTES = [
  { id: "simal", name: "Bakı–Sumqayıt yolu — 20 Yanvar — Tbilisi prospekti", pts: [[49.7050, 40.5360], [49.8090, 40.4040], [49.8140, 40.3760]] },
  { id: "qerb", name: "Binəqədi — Moskva prospekti — Ziya Bünyadov prospekti", pts: [[49.8150, 40.4500], [49.8460, 40.4150], [49.8700, 40.4240]] },
  { id: "aeroport", name: "Aeroport yolu — Heydər Əliyev prospekti — Gənclik", pts: [[50.0300, 40.4400], [49.9180, 40.4180], [49.8513, 40.4006]] },
  { id: "cenub", name: "Zığ şossesi — Babək prospekti — Neftçilər prospekti", pts: [[49.9600, 40.3700], [49.8900, 40.3940], [49.8400, 40.3660]] },
];
const DAILY_CAP = 330;
// Səkkiz əsas yol (sahib 2026-11-14: «pik saat bülletenləri səkkiz əsas yol üzrə»): adlar Mapbox-un küçə adlarıdır, marşrutlar
// bunların hamısından keçir (2026-11-14 yoxlaması). Bülletendə hər biri, sərbəst olsa da, yazılır.
const WATCH = ["Moskva prospekti", "Heydər Əliyev prospekti", "Ziya Bünyadov prospekti", "Tbilisi prospekti", "Babək prospekti",
  "Neftçilər prospekti", "Binəqədi şosesi", "Koroğlu Rəhimov küçəsi"];
const KEEP_MS = 12 * 3600e3;
const MIN_M = 600;            // bundan qısa küçə hissəsi xəbər vermir (kəsişmə, döngə)
const INCIDENT = { accident: "Qəza", road_closure: "Yol bağlıdır", construction: "Təmir işləri", disabled_vehicle: "Nasaz maşın", lane_restriction: "Zolaq bağlıdır", road_hazard: "Yolda təhlükə", planned_event: "Tədbir səbəbilə məhdudiyyət" };

const bakuClock = t => new Date(t + 4 * 3600e3).toISOString().slice(11, 16);
const bakuHour = t => new Date(t + 4 * 3600e3).getUTCHours();
const km = m => (m / 1000).toFixed(1).replace(".", ",");
const bad = id => id === "tixac" || id === "sixtixac";
const RANK = { serbest: 0, leng: 1, tixac: 2, sixtixac: 3 };

async function getJson(url, token, fetchFn = fetch) {
  const r = await fetchFn(url + (url.includes("?") ? "&" : "?") + "access_token=" + encodeURIComponent(token), { headers: { "User-Agent": "8ulduz-tixac" }, signal: AbortSignal.timeout?.(15000) });
  if (!r.ok) {
    let why = ""; try { why = (await r.text()).split(token).join("***").replace(/\s+/g, " ").slice(0, 160); } catch {}
    throw new Error("HTTP " + r.status + (why ? " " + why : ""));
  }
  return r.json();
}

function directed(route, now) { // səhər şəhərə doğru, günorta və axşam şəhərdən çıxış
  const out = bakuHour(now) >= 14;
  return { ...route, pts: out ? [...route.pts].reverse() : route.pts, dir: out ? "şəhərdən çıxış" : "şəhərə doğru" };
}

async function directions(route, token, fetchFn) {
  const coords = route.pts.map(p => p.join(",")).join(";");
  const d = await getJson(`https://api.mapbox.com/directions/v5/mapbox/driving-traffic/${coords}?annotations=congestion,distance&overview=full&geometries=geojson&steps=true&language=en`, token, fetchFn);
  if (d.code !== "Ok" || !d.routes?.length) throw new Error("marşrut yoxdur: " + (d.code || "?"));
  return d.routes[0];
}

// Marşrutun hissələrini küçə adlarına görə toplayır: məsafə, ağır/çox ağır tıxac məsafəsi, vaxt və adi vaxt.
function streets(route) {
  const by = new Map();
  for (const leg of route.legs || []) {
    const cong = leg.annotation?.congestion || [], dist = leg.annotation?.distance || [];
    let i = 0;
    for (const s of leg.steps || []) {
      const n = Math.max(0, (s.geometry?.coordinates?.length || 1) - 1), name = (s.name || s.ref || "").trim();
      const row = name && (by.get(name) || by.set(name, { name, m: 0, heavy: 0, severe: 0, moderate: 0, known: 0, dur: 0, typ: 0 }).get(name));
      for (let k = 0; k < n && i < cong.length; k++, i++) {
        if (!row) continue;
        const m = dist[i] || 0, c = cong[i];
        row.m += m;
        if (c !== "unknown") row.known += m;
        if (c === "heavy") row.heavy += m; else if (c === "severe") row.severe += m; else if (c === "moderate") row.moderate += m;
      }
      if (row) { row.dur += s.duration || 0; row.typ += s.duration_typical ?? s.duration ?? 0; }
    }
  }
  return [...by.values()];
}

function levelOf(st) {
  if (st.m < MIN_M || st.known < st.m * 0.5) return null; // qısa və ya məlumatı azdır
  // Pay və uzunluq birlikdə: 16 km-lik yolda 3 km ağır tıxac payla 18%-dir, amma sürücü üçün tıxacdır (2026-11-14, Moskva prospekti).
  const jam = st.heavy + st.severe, heavy = jam / st.m, severe = st.severe / st.m, slow = (jam + st.moderate) / st.m;
  if (severe >= 0.3 || heavy >= 0.5 || st.severe >= 1000 || jam >= 4000) return { id: "sixtixac", text: "sıx tıxac" };
  if (heavy >= 0.25 && jam >= 400 || jam >= 1500) return { id: "tixac", text: "tıxac" };
  if (slow >= 0.4 || jam + st.moderate >= 2500) return { id: "leng", text: "hərəkət ləngdir" };
  return { id: "serbest", text: "hərəkət sərbəstdir" };
}

function streetRow(st, dir, now) {
  const lvl = levelOf(st);
  if (!lvl) return null;
  const extra = Math.round((st.dur - st.typ) / 60);
  return { id: `${st.name}|${dir}`, name: st.name, dir, level: lvl.id, text: lvl.text, km: km(st.m), jamKm: km(st.heavy + st.severe), extra: extra > 0 ? extra : 0, at: now };
}

function eventFor(row, was) {
  if (!row || row.level === was) return null;
  const where = `${row.name} (${row.dir})`;
  if (bad(row.level) && (!bad(was) || row.level === "sixtixac" && was === "tixac"))
    return `${where}: ${row.text}, ${row.jamKm} km hissədə hərəkət çətindir${row.extra >= 2 ? `, yol adi haldan təxminən ${row.extra} dəq çox çəkir` : ""}.`;
  if (bad(was) && !bad(row.level)) return `${where}: tıxac azalıb, ${row.level === "serbest" ? "hərəkət sərbəstdir" : "hərəkət hələ ləngdir"}.`;
  return null;
}

function incidentEvents(route, seen, now) {
  const out = [];
  for (const leg of route.legs || []) for (const inc of leg.incidents || []) {
    const kind = INCIDENT[inc.type];
    if (!kind || !inc.id || seen.has(inc.id)) continue;
    seen.add(inc.id);
    const street = (inc.affected_road_names || [])[0] || "", impact = inc.impact === "critical" || inc.impact === "major" ? " Təsiri böyükdür." : "";
    out.push({ t: now, kind: "hadise", id: inc.id, text: `${kind}${street ? `: ${street}` : ""}.${impact}` });
  }
  return out;
}

async function run({ token, prev = {}, now = Date.now(), fetchFn = fetch, log = console.log }) {
  const day = new Date(now + 4 * 3600e3).toISOString().slice(0, 10);
  let used = prev.day === day ? prev.used || 0 : 0;
  const old = new Map((prev.streets || []).map(r => [r.id, r])), seen = new Set(prev.incIds || []);
  const rows = [], events = [], routes = [], errors = [];
  for (const base of ROUTES) {
    if (used >= DAILY_CAP) { errors.push("gündəlik hədd"); break; }
    const route = directed(base, now);
    try {
      used++;
      const r = await directions(route, token, fetchFn);
      routes.push({ id: route.id, name: route.name, dir: route.dir, min: Math.round(r.duration / 60), typ: Math.round((r.duration_typical ?? r.duration) / 60), km: km(r.distance) });
      for (const st of streets(r)) { // eyni küçə iki marşrutda: pis vəziyyət qalır
        const row = streetRow(st, route.dir, now), i = row ? rows.findIndex(x => x.id === row.id) : -1;
        if (!row || i >= 0 && RANK[rows[i].level] >= RANK[row.level]) continue;
        if (i >= 0) rows.splice(i, 1);
        rows.push(row);
      }
      events.push(...incidentEvents(r, seen, now));
    } catch (e) { errors.push(route.id + ": " + e.message); }
  }
  for (const row of rows) {
    const text = eventFor(row, old.get(row.id)?.level);
    if (text) events.push({ t: now, kind: bad(row.level) ? "pis" : "yaxsi", road: row.id, text });
  }
  // tıxac olan küçə bu dəfə heç ölçülmədisə (marşrut dəyişdi), «açıldı» deyilmir: sadəcə siyahıdan çıxır
  // ölçülməyən marşrutun küçələri əvvəlki vəziyyətində qalır (bir xəta «tıxac açıldı» xəbəri yaratmasın)
  for (const [id, r] of old) if (!rows.some(x => x.id === id) && errors.some(e => !e.startsWith("gündəlik")) && now - r.at < 3600e3) rows.push(r);
  const all = [...events.reverse(), ...(prev.events || [])].filter(e => now - e.t < KEEP_MS).slice(0, 80);
  for (const e of events) log(`  + ${bakuClock(e.t)} ${e.text}`);
  if (errors.length) log("  ! " + errors.join("; "));
  return { updatedAt: new Date(now).toISOString(), source: "Mapbox", day, used, routes, streets: rows.filter(r => r.level !== "serbest"), watch: watchOf(rows), events: all, incIds: [...seen].slice(-200), errors: errors.length };
}

// Səkkiz yolun vəziyyəti: hər yol üçün ən pis istiqamət; bu dövrədə ölçülməyibsə «?».
function watchOf(rows) {
  return WATCH.map(name => {
    const mine = rows.filter(r => r.name === name).sort((a, b) => RANK[b.level] - RANK[a.level])[0];
    return mine ? [name, mine.level, mine.jamKm] : [name, "?", "0,0"];
  });
}

async function probe(token) {
  console.log(`açar: ${token.length} simvol, ${token.startsWith("pk.") ? "«pk.» ilə başlayır" : "«pk.» ilə başlamır"}`);
  for (const base of ROUTES) {
    const route = directed(base, Date.now());
    try {
      const r = await directions(route, token);
      const list = streets(r).filter(s => s.m >= MIN_M);
      const known = list.reduce((a, s) => a + s.known, 0), all = list.reduce((a, s) => a + s.m, 0);
      console.log(`${route.id} (${route.dir}): ${km(r.distance)} km, ${Math.round(r.duration / 60)} dəq (adi ${Math.round((r.duration_typical ?? r.duration) / 60)} dəq), tıxac məlumatı olan hissə ${all ? Math.round(known / all * 100) : 0}%, hadisə ${(r.legs || []).reduce((a, l) => a + (l.incidents || []).length, 0)}`);
      for (const s of list) console.log(`   ${s.name}: ${km(s.m)} km | ağır ${km(s.heavy)} | çox ağır ${km(s.severe)} | orta ${km(s.moderate)} | məlum ${Math.round(s.known / s.m * 100)}% → ${levelOf(s)?.text || "-"}`);
    } catch (e) { console.log(`${route.id}: ${e.message}`); }
  }
}

// Günün tarixçəsi (tarix.json): hər ölçünün qısa nüsxəsi, 30 saat. oz_tixac.py səhər/axşam pik saatı xəbərini bundan yazır
// (marşrutun ən uzun vaxtı, tıxacın neçə dəqiqə sürdüyü, dünənlə müqayisə). Sayt bu faylı oxumur.
const HIST_MS = 30 * 3600e3;
function snapshot(d, now) {
  return { t: now, r: d.routes.map(r => [r.id, r.min, r.typ]), s: d.streets.map(s => [s.name, s.dir, s.level, s.jamKm]), w: d.watch || [],
    i: d.events.filter(e => e.t === now && e.kind === "hadise").map(e => e.text) };
}
function history(prev, d, now) {
  return [...(Array.isArray(prev) ? prev : []).filter(x => x && now - x.t < HIST_MS), ...(d.routes.length ? [snapshot(d, now)] : [])];
}

module.exports = { WATCH, watchOf, HIST_MS, snapshot, history, ROUTES, DAILY_CAP, directed, streets, levelOf, streetRow, eventFor, incidentEvents, run, bakuClock };

if (require.main === module) {
  const token = process.env.MAPBOX_TOKEN;
  if (!token) { console.error("MAPBOX_TOKEN yoxdur"); process.exit(1); }
  const [a, b, c] = process.argv.slice(2);
  if (a === "--yoxla") probe(token).catch(e => { console.error(e.message); process.exit(1); });
  else {
    let prev = {}; try { prev = JSON.parse(fs.readFileSync(b, "utf8")); } catch {}
    let prevHist = []; try { prevHist = JSON.parse(fs.readFileSync(c, 'utf8')).snaps; } catch {}
    const now = Date.now();
    run({ token, prev, now }).then(d => {
      if (!d.routes.length) { console.error("heç bir marşrut ölçülmədi"); process.exit(1); }
      fs.mkdirSync(a, { recursive: true });
      fs.writeFileSync(path.join(a, "tixac.json"), JSON.stringify(d));
      fs.writeFileSync(path.join(a, "tarix.json"), JSON.stringify({ updatedAt: d.updatedAt, snaps: history(prevHist, d, now) }));
      console.log(`tixac.json: ${d.routes.length} marşrut, ${d.streets.length} tıxaclı küçə, ${d.events.length} xəbər, bu gün ${d.used} sorğu`);
    }).catch(e => { console.error(e.message); process.exit(1); });
  }
}
