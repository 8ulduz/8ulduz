#!/usr/bin/env node
// Avtomatik tıxac ölçüsü (sahib, 2026-11-14: «avtomatik tıxac xəbərləri hazırlayıb verən sistem qur»).
// Mənbə: TomTom Traffic API (pulsuz plan, kartsız: həddi keçəndə sorğu sadəcə rədd olunur, pul tutulmur).
//   Flow Segment Data: ayda 20 000 pulsuz sorğu. 8 nöqtə × hər 15 dəq × 07:00–22:00 (64 dövrə) ≈ 512/gün ≈ 15 900/ay.
//   Incident Details: ayda 2 500 pulsuz sorğu. Yarım saatda bir (dəqiqə < 15 olan dövrə) ≈ 32/gün ≈ 1 000/ay.
// Açar yalnız TOMTOM_KEY mühit dəyişənindədir; heç vaxt çap olunmur, xətada yalnız HTTP kodu yazılır.
// Nəticə: tixac.json (yolların indiki vəziyyəti + son 12 saatın avtomatik xəbərləri). İş onu «tixac» budağına yazır,
// sayt Tıxac səhifəsində raw.githubusercontent.com-dan oxuyur (xəbər lentinə və main-ə heç nə yazılmır).
// İstifadə: node tixac.cjs <çıxış qovluğu> [əvvəlki tixac.json]   |   node tixac.cjs --yoxla  (nöqtələrin hansı yola düşdüyü)
"use strict";
const fs = require("node:fs"), path = require("node:path");

// Ölçü nöqtələri: yolun ortasında bir nöqtə. TomTom ən yaxın yol hissəsini götürür (frc: 0 magistral … 2 əsas küçə).
const ROADS = [
  { id: "heyder-eliyev", name: "Heydər Əliyev prospekti", where: "Koroğlu — Gənclik", lat: 40.4166, lon: 49.9198 },
  { id: "ziya-bunyadov", name: "Ziya Bünyadov prospekti", where: "Gənclik — 8-ci km", lat: 40.4237, lon: 49.8846 },
  { id: "sumqayit-yolu", name: "Bakı–Sumqayıt yolu", where: "Masazır dairəsi", lat: 40.4870, lon: 49.7676 },
  { id: "tbilisi", name: "Tbilisi prospekti", where: "20 Yanvar — Elmlər", lat: 40.3929, lon: 49.8131 },
  { id: "babek", name: "Babək prospekti", where: "Xətai — Gənclik", lat: 40.3955, lon: 49.8885 },
  { id: "neftciler", name: "Neftçilər prospekti", where: "Dənizkənarı bulvar", lat: 40.3668, lon: 49.8432 },
  { id: "hava-limani", name: "Hava limanı yolu", where: "Zığ dairəsi — aeroport", lat: 40.4290, lon: 50.0050 },
  { id: "mətbuat", name: "Mətbuat prospekti", where: "Elmlər — Bayıl", lat: 40.3802, lon: 49.8117 },
];
const BBOX = "49.70,40.30,50.15,40.62"; // Bakı və Abşeron (hadisələr)
const KEEP_MS = 12 * 3600e3;
const LEVELS = [ // cari sürət / sərbəst sürət
  { id: "sixtixac", max: 0.4, text: "sıx tıxac" },
  { id: "tixac", max: 0.6, text: "tıxac" },
  { id: "leng", max: 0.8, text: "hərəkət ləngdir" },
  { id: "serbest", max: Infinity, text: "hərəkət sərbəstdir" },
];
const ICON = { 1: "Qəza", 6: "Tıxac", 7: "Zolaq bağlıdır", 8: "Yol bağlıdır", 9: "Təmir işləri", 11: "Su basıb", 14: "Nasaz maşın" };

const bakuClock = t => new Date(t + 4 * 3600e3).toISOString().slice(11, 16);
const levelOf = r => LEVELS.find(l => r < l.max);
const bad = id => id === "tixac" || id === "sixtixac";

async function getJson(url, key, fetchFn = fetch) {
  const r = await fetchFn(url + (url.includes("?") ? "&" : "?") + "key=" + encodeURIComponent(key), { headers: { "User-Agent": "8ulduz-tixac" }, signal: AbortSignal.timeout?.(15000) });
  if (!r.ok) throw new Error("HTTP " + r.status); // ünvan (açarla) heç vaxt xətaya düşmür
  return r.json();
}

async function flow(road, key, fetchFn) {
  const d = (await getJson(`https://api.tomtom.com/traffic/services/4/flowSegmentData/absolute/10/json?point=${road.lat},${road.lon}&unit=KMPH`, key, fetchFn)).flowSegmentData || {};
  const c = d.coordinates?.coordinate || [];
  return { frc: d.frc, speed: d.currentSpeed, free: d.freeFlowSpeed, conf: d.confidence, closed: !!d.roadClosure, first: c[0], last: c[c.length - 1] };
}

async function incidents(key, fetchFn) {
  const fields = "{incidents{type,geometry{type,coordinates},properties{id,iconCategory,magnitudeOfDelay,startTime,from,to,length,delay,roadNumbers}}}";
  const d = await getJson(`https://api.tomtom.com/traffic/services/5/incidentDetails?bbox=${BBOX}&fields=${encodeURIComponent(fields)}&language=en-GB&categoryFilter=1,6,7,8,9,11,14&timeValidityFilter=present`, key, fetchFn);
  return (d.incidents || []).map(i => i.properties || {}).filter(p => ICON[p.iconCategory]);
}

// Yolun vəziyyəti və əvvəlkinə görə xəbər (yalnız dəyişəndə; etibarlılığı aşağı ölçü xəbər vermir).
function roadState(road, f, prev, now) {
  if (!f || !(f.free > 0) || !(f.speed >= 0)) return null;
  const ratio = Math.round(f.speed / f.free * 100) / 100, lvl = f.closed ? { id: "bagli", text: "yol bağlıdır" } : levelOf(ratio);
  const row = { id: road.id, name: road.name, where: road.where, level: lvl.id, text: lvl.text, speed: Math.round(f.speed), free: Math.round(f.free), ratio, conf: f.conf, at: now };
  let event = null;
  const was = prev?.level, sure = (f.conf ?? 1) >= 0.7;
  if (sure && lvl.id !== was) {
    if (lvl.id === "bagli") event = `${road.name} (${road.where}): yol bağlıdır.`;
    else if (bad(lvl.id) && !bad(was) || lvl.id === "sixtixac" && was === "tixac") event = `${road.name} (${road.where}): ${lvl.text}. Maşınlar saatda ${row.speed} km sürətlə gedir (adi halda ${row.free} km).`;
    else if ((bad(was) || was === "bagli") && !bad(lvl.id)) event = `${road.name} (${road.where}): tıxac azalıb, ${lvl.id === "serbest" ? "hərəkət sərbəstdir" : "hərəkət hələ ləngdir"} (saatda ${row.speed} km).`;
  }
  return { row, event: event && { t: now, kind: bad(lvl.id) || lvl.id === "bagli" ? "pis" : "yaxsi", road: road.id, text: event } };
}

function incidentEvents(list, prevIds, now) {
  const out = [];
  for (const p of list) {
    if (!p.id || prevIds.has(p.id)) continue;
    if (p.iconCategory === 6 && (p.magnitudeOfDelay || 0) < 3) continue; // adi tıxac yollardan gəlir; yalnız «böyük» tıxac hadisəsi
    const where = [p.from, p.to].filter(Boolean).join(" — "), km = p.length ? ` (${(p.length / 1000).toFixed(1).replace(".", ",")} km)` : "", late = p.delay >= 120 ? `, gecikmə təxminən ${Math.round(p.delay / 60)} dəq` : "";
    out.push({ t: now, kind: "hadise", id: p.id, text: `${ICON[p.iconCategory]}: ${where || "Bakı"}${km}${late}.` });
  }
  return out;
}

async function run({ key, prev = {}, now = Date.now(), fetchFn = fetch, withIncidents = true, log = console.log }) {
  const old = new Map((prev.roads || []).map(r => [r.id, r]));
  const roads = [], events = [], errors = [];
  for (const road of ROADS) {
    try { const s = roadState(road, await flow(road, key, fetchFn), old.get(road.id), now); if (s) { roads.push(s.row); if (s.event) events.push(s.event); } }
    catch (e) { errors.push(road.id + ": " + e.message); const o = old.get(road.id); if (o) roads.push(o); }
  }
  let incIds = prev.incIds || [];
  if (withIncidents) {
    try { const list = await incidents(key, fetchFn); events.push(...incidentEvents(list, new Set(incIds), now)); incIds = list.map(p => p.id).filter(Boolean); }
    catch (e) { errors.push("hadisələr: " + e.message); }
  }
  const all = [...events.reverse(), ...(prev.events || [])].filter(e => now - e.t < KEEP_MS).slice(0, 60);
  for (const e of events) log(`  + ${bakuClock(e.t)} ${e.text}`);
  if (errors.length) log("  ! " + errors.join("; "));
  return { updatedAt: new Date(now).toISOString(), source: "TomTom", roads, events: all, incIds, errors: errors.length };
}

async function probe(key) {
  // Açarın özü yox, yalnız forması (401 gələndə yapışdırılan mətnin açar olub-olmadığını bilmək üçün).
  console.log(`açar: ${key.length} simvol, ${/^[A-Za-z0-9]+$/.test(key) ? "yalnız hərf və rəqəm" : "boşluq və ya başqa işarə var"}, ${/\s/.test(key) ? "boşluqlu" : "boşluqsuz"}`);
  for (const road of ROADS) {
    try { const f = await flow(road, key); console.log(`${road.id}: frc=${f.frc} sürət=${f.speed}/${f.free} etibar=${f.conf} bağlı=${f.closed} hissə ${f.first?.latitude?.toFixed(4)},${f.first?.longitude?.toFixed(4)} → ${f.last?.latitude?.toFixed(4)},${f.last?.longitude?.toFixed(4)}`); }
    catch (e) { console.log(`${road.id}: ${e.message}`); }
  }
  try { const l = await incidents(key); console.log(`hadisələr: ${l.length}`); for (const p of l.slice(0, 8)) console.log(`  ${ICON[p.iconCategory]} | ${p.from || ""} — ${p.to || ""} | ${p.length || 0} m | gecikmə ${p.delay || 0} s`); }
  catch (e) { console.log("hadisələr: " + e.message); }
}

module.exports = { ROADS, LEVELS, levelOf, roadState, incidentEvents, run, bakuClock };

if (require.main === module) {
  const key = process.env.TOMTOM_KEY;
  if (!key) { console.error("TOMTOM_KEY yoxdur"); process.exit(1); }
  const [a, b] = process.argv.slice(2);
  if (a === "--yoxla") probe(key).catch(e => { console.error(e.message); process.exit(1); });
  else {
    let prev = {}; try { prev = JSON.parse(fs.readFileSync(b, "utf8")); } catch {}
    const now = Date.now(), minute = new Date(now).getUTCMinutes();
    run({ key, prev, now, withIncidents: minute < 15 || !prev.updatedAt }).then(d => {
      if (!d.roads.length) { console.error("heç bir yol ölçülmədi"); process.exit(1); }
      fs.mkdirSync(a, { recursive: true });
      fs.writeFileSync(path.join(a, "tixac.json"), JSON.stringify(d));
      console.log(`tixac.json: ${d.roads.length} yol, ${d.events.length} xəbər, ${d.errors} xəta`);
    }).catch(e => { console.error(e.message); process.exit(1); });
  }
}
