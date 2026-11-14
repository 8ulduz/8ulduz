#!/usr/bin/env node
// Avtomatik tıxac ölçüsü (sahib, 2026-11-14: «avtomatik tıxac xəbərləri hazırlayıb verən sistem qur», sonra «Bəli, Mapbox»).
// Mənbə: Mapbox Directions API, «driving-traffic» profili (Azərbaycan Mapbox-un tıxac örtüyündədir). Sahib 2026-11-14 hesaba kart
// bağladı («hazır»): ayda 100 000 sorğu pulsuzdur, artığı pullu (≈ 2 $ / 1 000). Mapbox-da xərc həddi yoxdur — qoruma DAILY_CAP-dır.
// TomTom yoxlanıb (2026-11-14): açar işləyir, amma Bakıda (və Tbilisidə) yol məlumatı yoxdur — «Point too far from nearest
// existing segment»; İstanbulda var. Waze-in xəritəsindən məlumat çəkmək onun şərtlərinə ziddir: qurulmur.
//
// Bir dövrə = 35 sorğu: Bakının 12 rayonunu (Abşeronla) əhatə edən 35 marşrut (hər biri 3 nöqtə). Mapbox marşrutu hissələrə bölüb hər hissənin tıxac dərəcəsini verir
// (low/moderate/heavy/severe); hissələr addımların (küçələrin) adı ilə toplanır, beləcə marşrut boyu tıxac olan hər küçə adı ilə
// çıxır. Səhər (Bakı 14:00-dək) marşrut şəhərə doğru, sonra şəhərdən çıxışa doğrudur.
// Büdcə: pik saatlarda (07–10, 17–20) hər 6 dəq = 60 dövrə, qalan vaxt (10–17, 20–22) hər 30 dəq = 18 dövrə;
// 78 × 35 = 2 730/gün, 31 günlük ayda ≈ 84 600 < 100 000. Dövrə yalnız bütöv gedir: gündə 3 000 sorğunu keçəcəksə heç başlamır
// (DAILY_CAP, vəziyyət faylında sayılır) — ən pis halda ayda 93 000.
// Açar yalnız MAPBOX_TOKEN mühit dəyişənindədir; heç vaxt çap olunmur, xətada yalnız HTTP kodu və açarsız səbəb yazılır.
// Nəticə: tixac.json (marşrutlar, tıxaclı küçələr, son 12 saatın avtomatik xəbərləri) → «tixac» budağı → saytın Tıxac səhifəsi.
// İstifadə: node tixac.cjs <çıxış qovluğu> [əvvəlki tixac.json] [tarix.json] [hafta.json]   |   node tixac.cjs --yoxla
"use strict";
const fs = require("node:fs"), path = require("node:path");

// [en, enlik] cütləri (Mapbox sırası). Ad oxucu üçündür; küçə adları Mapbox-dan gəlir.
const ROUTES = [
  { id: "simal", rayon: "Binəqədi", name: "Bakı–Sumqayıt yolu — 20 Yanvar — Tbilisi prospekti", pts: [[49.7050, 40.5360], [49.8090, 40.4040], [49.8140, 40.3760]] },
  { id: "qerb", rayon: "Nərimanov", name: "Binəqədi — Moskva prospekti — Ziya Bünyadov prospekti", pts: [[49.8150, 40.4500], [49.8460, 40.4150], [49.8700, 40.4240]] },
  { id: "aeroport", rayon: "Nizami", name: "Aeroport yolu — Heydər Əliyev prospekti — Gənclik", pts: [[50.0300, 40.4400], [49.9180, 40.4180], [49.8513, 40.4006]] },
  { id: "cenub", rayon: "Xətai", name: "Zığ şossesi — Babək prospekti — Neftçilər prospekti", pts: [[49.9600, 40.3700], [49.8900, 40.3940], [49.8400, 40.3660]] },
  { id: "sebail", rayon: "Səbail", name: "Fəvvarələr — Azneft — Neftçilər prospekti", pts: [[49.8375, 40.3720], [49.8480, 40.3620], [49.8680, 40.3770]] },
  { id: "bayil", rayon: "Səbail", name: "Badamdar — Bayıl", pts: [[49.8000, 40.3400], [49.8300, 40.3450], [49.8470, 40.3600]] },
  { id: "qaradag", rayon: "Qaradağ", name: "Lökbatan — Şıx — Bayıl", pts: [[49.7250, 40.3300], [49.7900, 40.3150], [49.8250, 40.3300]] },
  { id: "yasamal", rayon: "Yasamal", name: "Yasamal — İnşaatçılar — Hüsü Hacıyev", pts: [[49.7900, 40.3900], [49.8150, 40.3800], [49.8350, 40.3780]] },
  { id: "cavid", rayon: "Yasamal", name: "Hüseyn Cavid prospekti — Elmlər Akademiyası — 28 May", pts: [[49.7950, 40.3700], [49.8150, 40.3770], [49.8400, 40.3790]] },
  { id: "serifzade", rayon: "Yasamal", name: "Badamdar — Şərifzadə — Yasamal", pts: [[49.8100, 40.3500], [49.8150, 40.3700], [49.8000, 40.3850]] },
  { id: "merkez", rayon: "Nəsimi", name: "Mərkəz — 28 May — Xətai", pts: [[49.8300, 40.3800], [49.8490, 40.3790], [49.8650, 40.3800]] },
  { id: "fuzuli", rayon: "Nəsimi", name: "Füzuli — Səməd Vurğun — Xətai", pts: [[49.8400, 40.3850], [49.8600, 40.3830], [49.8750, 40.3780]] },
  { id: "azadliq", rayon: "Nəsimi", name: "Azadlıq prospekti", pts: [[49.8400, 40.3850], [49.8430, 40.4100], [49.8430, 40.4300]] },
  { id: "dernegul", rayon: "Binəqədi", name: "20 Yanvar — Nəsimi — Dərnəgül", pts: [[49.8100, 40.4040], [49.8300, 40.4220], [49.8600, 40.4250]] },
  { id: "ataturk", rayon: "Nərimanov", name: "Təbriz — Atatürk prospekti — Nərimanov", pts: [[49.8550, 40.3900], [49.8700, 40.4040], [49.8850, 40.4150]] },
  { id: "kor", rayon: "Nərimanov", name: "Ziya Bünyadov — Koroğlu dairəsi", pts: [[49.8700, 40.4240], [49.9000, 40.4250], [49.9180, 40.4180]] },
  { id: "nobel", rayon: "Xətai", name: "Nobel prospekti — Əhmədli", pts: [[49.8700, 40.3700], [49.9000, 40.3720], [49.9400, 40.3750]] },
  { id: "agseher", rayon: "Xətai", name: "Ağ şəhər — Xətai", pts: [[49.8650, 40.3650], [49.8850, 40.3600], [49.9100, 40.3680]] },
  { id: "xocali", rayon: "Xətai", name: "Xocalı prospekti — Həzi Aslanov", pts: [[49.8700, 40.3830], [49.8950, 40.3880], [49.9250, 40.3950]] },
  { id: "qarayev", rayon: "Nizami", name: "Koroğlu — Qara Qarayev — Əhmədli", pts: [[49.9000, 40.4200], [49.9300, 40.4050], [49.9550, 40.3900]] },
  { id: "bineqedi", rayon: "Binəqədi", name: "Binəqədi qəsəbəsi — Moskva prospekti", pts: [[49.8300, 40.4650], [49.8400, 40.4400], [49.8450, 40.4250]] },
  { id: "xirdalan", rayon: "Abşeron", name: "Xırdalan — Biləcəri — 20 Yanvar", pts: [[49.7550, 40.4480], [49.7900, 40.4250], [49.8100, 40.4050]] },
  { id: "masazir", rayon: "Abşeron", name: "Novxanı — Masazır — Xırdalan", pts: [[49.7500, 40.4900], [49.7600, 40.4600], [49.7550, 40.4480]] },
  { id: "sumqayit", rayon: "Abşeron", name: "Sumqayıt — Corat — Bakı yolu", pts: [[49.6500, 40.5850], [49.6900, 40.5550], [49.7200, 40.5200]] },
  { id: "novxani", rayon: "Abşeron", name: "Novxanı — Binəqədi yolu", pts: [[49.7900, 40.5300], [49.8200, 40.4900], [49.8300, 40.4600]] },
  { id: "bakixanov", rayon: "Sabunçu", name: "Bakıxanov — Koroğlu dairəsi", pts: [[49.9700, 40.4250], [49.9400, 40.4250], [49.9200, 40.4180]] },
  { id: "mastaga", rayon: "Sabunçu", name: "Maştağa — Zabrat — Bakı", pts: [[49.9900, 40.5300], [49.9550, 40.4800], [49.9250, 40.4300]] },
  { id: "bilgeh", rayon: "Sabunçu", name: "Bilgəh — Nardaran — Maştağa", pts: [[50.0400, 40.5700], [49.9900, 40.5600], [49.9600, 40.5150]] },
  { id: "merdekan", rayon: "Xəzər", name: "Mərdəkan — Qala — Aeroport yolu", pts: [[50.1400, 40.4900], [50.0800, 40.4700], [50.0300, 40.4400]] },
  { id: "buzovna", rayon: "Xəzər", name: "Buzovna — Maştağa", pts: [[50.1100, 40.5200], [50.0500, 40.5300], [49.9900, 40.5300]] },
  { id: "turkan", rayon: "Xəzər", name: "Türkan — Zirə — Aeroport", pts: [[50.2100, 40.3650], [50.1300, 40.4000], [50.0500, 40.4400]] },
  { id: "qaracuxur", rayon: "Suraxanı", name: "Qaraçuxur — Əhmədli", pts: [[49.9900, 40.4000], [49.9700, 40.3900], [49.9500, 40.3850]] },
  { id: "hovsan", rayon: "Suraxanı", name: "Hövsan — Zığ", pts: [[50.0700, 40.3700], [50.0100, 40.3650], [49.9600, 40.3700]] },
  { id: "suraxani", rayon: "Suraxanı", name: "Suraxanı — Bülbülə — Əmircan", pts: [[50.0100, 40.4300], [49.9800, 40.4100], [49.9500, 40.4050]] },
  { id: "neftciler", rayon: "Nizami", name: "Keşlə — Neftçilər metrosu — Qara Qarayev", pts: [[49.8900, 40.4000], [49.9100, 40.4000], [49.9430, 40.4105]] },
];
const DAILY_CAP = 3000;
const PARALLEL = 5;          // eyni anda sorğu (Mapbox həddi dəqiqədə 300)
// Səkkiz əsas yol (sahib 2026-11-14: «pik saat bülletenləri səkkiz əsas yol üzrə»): adlar Mapbox-un küçə adlarıdır, marşrutlar
// bunların hamısından keçir (2026-11-14 yoxlaması). Bülletendə hər biri, sərbəst olsa da, yazılır.
const WATCH = ["Moskva prospekti", "Heydər Əliyev prospekti", "Ziya Bünyadov prospekti", "Tbilisi prospekti", "Babək prospekti",
  "Neftçilər prospekti", "Binəqədi şosesi", "Koroğlu Rəhimov küçəsi"];
const KEEP_MS = 12 * 3600e3;
const MIN_M = 600;            // bundan qısa küçə hissəsi xəbər vermir (kəsişmə, döngə)
const INCIDENT = { accident: "Qəza", road_closure: "Yol bağlıdır", construction: "Təmir işləri", disabled_vehicle: "Nasaz maşın", lane_restriction: "Zolaq bağlıdır", road_hazard: "Yolda təhlükə", planned_event: "Tədbir səbəbilə məhdudiyyət" };

const meters = ([x1, y1], [x2, y2]) => { // iki nöqtə arası düz məsafə (m)
  const r = Math.PI / 180, a = Math.sin((y2 - y1) * r / 2) ** 2 + Math.cos(y1 * r) * Math.cos(y2 * r) * Math.sin((x2 - x1) * r / 2) ** 2;
  return 12742e3 * Math.asin(Math.sqrt(a));
};
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
  // Nöqtə dənizə və ya yolsuz yerə düşəndə Mapbox çox uzaq yol tapır (2026-11-14 sınağı: Bayıl → bərə → İran, 1 830 km).
  // Düz xətdən 3 dəfədən çox uzun marşrut ölçülmür.
  const line = route.pts.slice(1).reduce((a, p, i) => a + meters(route.pts[i], p), 0);
  if (d.routes[0].distance > line * 3 + 5000) throw new Error(`marşrut yolunu azıb: ${km(d.routes[0].distance)} km`);
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

// Marşrutun bütün hissələri üzrə: ağır+çox ağır, orta və tıxac dərəcəsi məlum olan məsafə (rayon balı üçün).
function loadOf(route) {
  const o = { jam: 0, mod: 0, known: 0 };
  for (const leg of route.legs || []) {
    const cong = leg.annotation?.congestion || [], dist = leg.annotation?.distance || [];
    cong.forEach((c, i) => {
      const m = dist[i] || 0;
      if (c === "unknown") return;
      o.known += m;
      if (c === "heavy" || c === "severe") o.jam += m; else if (c === "moderate") o.mod += m;
    });
  }
  return o;
}

// Rayon balı 0–10: rayonun marşrutlarında ağır tıxaclı yolun payı (orta tıxac yarım sayılır); 40% və çoxu = 10.
// Sıra: ən tıxaclı rayon əvvəl. Məlumatı 2 km-dən az olan rayon yazılmır.
function rayonScores(routes) {
  const by = new Map();
  for (const r of routes) {
    if (!r.rayon) continue;
    const z = by.get(r.rayon) || by.set(r.rayon, { jam: 0, mod: 0, known: 0 }).get(r.rayon);
    z.jam += r.jam || 0; z.mod += r.mod || 0; z.known += r.known || 0;
  }
  return [...by].filter(([, z]) => z.known >= 2000)
    .map(([name, z]) => [name, Math.min(10, Math.round((z.jam + z.mod / 2) / z.known * 25)), km(z.jam)])
    .sort((a, b) => b[1] - a[1] || a[0].localeCompare(b[0], "az"));
}

async function pool(items, n, fn) {
  const out = new Array(items.length);
  let next = 0;
  await Promise.all(Array.from({ length: Math.min(n, items.length) }, async () => {
    while (next < items.length) { const i = next++; out[i] = await fn(items[i], i); }
  }));
  return out;
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
  // Dövrə bütöv gedir ya heç getmir: yarımçıq ölçü rayon balını və «açıldı» xəbərlərini korlayardı.
  if (used + ROUTES.length > DAILY_CAP) { log(`  ! gündəlik hədd: bu gün ${used} sorğu, dövrə buraxıldı`); return { capped: true, day, used }; }
  const old = new Map((prev.streets || []).map(r => [r.id, r])), seen = new Set(prev.incIds || []);
  const rows = [], events = [], routes = [], errors = [];
  used += ROUTES.length;
  const got = await pool(ROUTES, PARALLEL, async base => {
    const route = directed(base, now);
    try { return { route, r: await directions(route, token, fetchFn) }; } catch (e) { return { route, err: e.message }; }
  });
  for (const { route, r, err } of got) { // marşrut sırası ilə: nəticə paralel gəlsə də eyni çıxır
    if (err) { errors.push(route.id + ": " + err); continue; }
    routes.push({ id: route.id, name: route.name, rayon: route.rayon, dir: route.dir, min: Math.round(r.duration / 60), typ: Math.round((r.duration_typical ?? r.duration) / 60), km: km(r.distance), ...loadOf(r) });
    for (const st of streets(r)) { // eyni küçə iki marşrutda: pis vəziyyət qalır
      const row = streetRow(st, route.dir, now), i = row ? rows.findIndex(x => x.id === row.id) : -1;
      if (!row || i >= 0 && RANK[rows[i].level] >= RANK[row.level]) continue;
      if (i >= 0) rows.splice(i, 1);
      rows.push(row);
    }
    events.push(...incidentEvents(r, seen, now));
  }
  for (const row of rows) {
    const text = eventFor(row, old.get(row.id)?.level);
    if (text) events.push({ t: now, kind: bad(row.level) ? "pis" : "yaxsi", road: row.id, text });
  }
  // tıxac olan küçə bu dəfə heç ölçülmədisə (marşrut dəyişdi), «açıldı» deyilmir: sadəcə siyahıdan çıxır
  // ölçülməyən marşrutun küçələri əvvəlki vəziyyətində qalır (bir xəta «tıxac açıldı» xəbəri yaratmasın)
  if (errors.length) for (const [id, r] of old) if (!rows.some(x => x.id === id) && now - r.at < 3600e3) rows.push(r);
  const all = [...events.reverse(), ...(prev.events || [])].filter(e => now - e.t < KEEP_MS).slice(0, 80);
  for (const e of events) log(`  + ${bakuClock(e.t)} ${e.text}`);
  if (errors.length) log("  ! " + errors.join("; "));
  const measured = rows.filter(r => r.at === now);
  return { updatedAt: new Date(now).toISOString(), source: "Mapbox", day, used,
    routes: routes.map(({ jam, mod, known, ...r }) => r), rayons: rayonScores(routes),
    counted: new Set(measured.map(r => r.name)).size, jammed: new Set(measured.filter(r => bad(r.level)).map(r => r.name)).size,
    streets: rows.filter(r => r.level !== "serbest").sort((a, b) => RANK[b.level] - RANK[a.level] || parseFloat(b.jamKm.replace(",", ".")) - parseFloat(a.jamKm.replace(",", "."))),
    watch: watchOf(rows), events: all, incIds: [...seen].slice(-300), errors: errors.length };
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
  const names = new Set(), got = await pool(ROUTES, PARALLEL, async base => {
    const route = directed(base, Date.now());
    try { return { route, r: await directions(route, token) }; } catch (e) { return { route, err: e.message }; }
  });
  for (const { route, r, err } of got) {
    if (err) { console.log(`${route.id}: ${err}`); continue; }
    const list = streets(r).filter(s => s.m >= MIN_M), l = loadOf(r);
    list.forEach(s => names.add(s.name));
    console.log(`${route.id} [${route.rayon}] ${km(r.distance)} km, ${Math.round(r.duration / 60)} dəq (adi ${Math.round((r.duration_typical ?? r.duration) / 60)}), məlum ${Math.round(l.known / r.distance * 100)}%, ağır ${km(l.jam)} km: ${list.map(s => `${s.name} ${km(s.m)}${levelOf(s) ? "" : "?"}`).join("; ")}`);
  }
  console.log(`fərqli küçə (≥ ${MIN_M} m): ${names.size}; səkkiz yoldan tapılmayan: ${WATCH.filter(w => !names.has(w)).join(", ") || "yoxdur"}`);
  console.log("rayon balı: " + rayonScores(got.filter(g => g.r).map(g => ({ rayon: g.route.rayon, ...loadOf(g.r) }))).map(z => z.join(" ")).join(" | "));
}

// Günün tarixçəsi (tarix.json): hər ölçünün qısa nüsxəsi, 30 saat. oz_tixac.py səhər/axşam pik saatı xəbərini bundan yazır
// (marşrutun ən uzun vaxtı, tıxacın neçə dəqiqə sürdüyü, dünənlə müqayisə). Sayt bu faylı oxumur.
const HIST_MS = 30 * 3600e3;
function snapshot(d, now) {
  return { t: now, r: d.routes.map(r => [r.id, r.min, r.typ]), z: d.rayons || [], n: [d.counted || 0, d.jammed || 0], s: d.streets.map(s => [s.name, s.dir, s.level, s.jamKm]), w: d.watch || [],
    i: d.events.filter(e => e.t === now && e.kind === "hadise").map(e => e.text) };
}
function history(prev, d, now) {
  return [...(Array.isArray(prev) ? prev : []).filter(x => x && now - x.t < HIST_MS), ...(d.routes.length ? [snapshot(d, now)] : [])];
}

// Həftəlik yığım (hafta.json): hər gün üçün ölçü sayı (n), hər küçənin neçə ölçüdə (s) və təxminən neçə dəqiqə (m) tıxaclı
// olduğu (iki istiqamət bir dəfə), ən uzun tıxacı km ilə (k) və hər rayonun bal cəmi (z). Bir ölçü pik saatda (07–10, 17–20)
// 6, qalan vaxt 30 dəqiqəni təmsil edir (cron belədir). oz_tixac.py şənbə günü «Həftənin ən tıxaclı küçələri» xəbərini bundan
// yazır; 8 gün saxlanır.
const WEEK_DAYS = 8;
const stepMin = t => { const h = bakuHour(t); return h >= 7 && h < 10 || h >= 17 && h < 20 ? 6 : 30; };
function week(prev, d, now = Date.parse(d.updatedAt)) {
  const days = { ...(prev && typeof prev.days === "object" ? prev.days : {}) };
  const today = days[d.day] = { n: 0, s: {}, m: {}, k: {}, z: {}, ...(days[d.day] || {}) };
  for (const x of ["m", "k"]) today[x] = today[x] || {};
  today.n++;
  const step = stepMin(now), seen = new Set();
  for (const st of d.streets) {
    if (!bad(st.level)) continue;
    const kmv = parseFloat(String(st.jamKm).replace(",", ".")) || 0;
    today.k[st.name] = Math.max(today.k[st.name] || 0, kmv);
    if (seen.has(st.name)) continue;
    seen.add(st.name);
    today.s[st.name] = (today.s[st.name] || 0) + 1;
    today.m[st.name] = (today.m[st.name] || 0) + step;
  }
  for (const [name, score] of d.rayons || []) today.z[name] = (today.z[name] || 0) + score;
  const keep = Object.keys(days).sort().slice(-WEEK_DAYS);
  return { updatedAt: d.updatedAt, days: Object.fromEntries(keep.map(k => [k, days[k]])) };
}

module.exports = { week, rayonScores, loadOf, pool, WATCH, watchOf, HIST_MS, snapshot, history, ROUTES, DAILY_CAP, directed, streets, levelOf, streetRow, eventFor, incidentEvents, run, bakuClock };

if (require.main === module) {
  const token = process.env.MAPBOX_TOKEN;
  if (!token) { console.error("MAPBOX_TOKEN yoxdur"); process.exit(1); }
  const [a, b, c] = process.argv.slice(2);
  if (a === "--yoxla") probe(token).catch(e => { console.error(e.message); process.exit(1); });
  else {
    let prev = {}; try { prev = JSON.parse(fs.readFileSync(b, "utf8")); } catch {}
    let prevHist = []; try { prevHist = JSON.parse(fs.readFileSync(c, 'utf8')).snaps; } catch {}
    let prevWeek = {}; try { prevWeek = JSON.parse(fs.readFileSync(process.argv[5], "utf8")); } catch {}
    const now = Date.now();
    run({ token, prev, now }).then(d => {
      if (d.capped) return; // gündəlik hədd: heç nə yazılmır, iş uğurla bitir
      if (!d.routes.length) { console.error("heç bir marşrut ölçülmədi"); process.exit(1); }
      fs.mkdirSync(a, { recursive: true });
      fs.writeFileSync(path.join(a, "tixac.json"), JSON.stringify(d));
      fs.writeFileSync(path.join(a, "tarix.json"), JSON.stringify({ updatedAt: d.updatedAt, snaps: history(prevHist, d, now) }));
      fs.writeFileSync(path.join(a, "hafta.json"), JSON.stringify(week(prevWeek, d)));
      console.log(`tixac.json: ${d.routes.length} marşrut, ${d.streets.length} tıxaclı küçə, ${d.events.length} xəbər, bu gün ${d.used} sorğu`);
    }).catch(e => { console.error(e.message); process.exit(1); });
  }
}
