// Avtomatik tıxac ölçüsü (.github/scripts/tixac.cjs, sahib 2026-11-14: «Bəli, Mapbox»).
const test = require("node:test"), assert = require("node:assert/strict"), fs = require("node:fs"), path = require("node:path");
const T = require("../.github/scripts/tixac.cjs");
const root = path.join(__dirname, "..");

// Mapbox cavabı: hər addımın həndəsəsi n nöqtədir → n-1 hissə; ayaqdakı congestion/distance massivləri hissələrə uyğundur.
const step = (name, n, extra = {}) => ({ name, geometry: { coordinates: Array.from({ length: n }, (_, i) => [49.8 + i / 1000, 40.4]) }, duration: 60, duration_typical: 60, ...extra });
function route(parts, incidents = []) {
  const steps = [], cong = [], dist = [];
  for (const [name, list, extra] of parts) { steps.push(step(name, list.length + 1, extra)); for (const c of list) { cong.push(c); dist.push(300); } }
  return { code: "Ok", routes: [{ distance: dist.reduce((a, b) => a + b, 0), duration: 900, duration_typical: 600, legs: [{ steps, incidents, annotation: { congestion: cong, distance: dist } }] }] };
}

test("tixac: segments are summed per street and graded by the share of heavy and severe traffic", () => {
  const r = route([["Heydər Əliyev prospekti", ["heavy", "heavy", "severe", "low"]], ["Babək prospekti", ["low", "low", "moderate", "low"]], ["Dalan", ["severe"]]]).routes[0];
  const s = T.streets(r), by = Object.fromEntries(s.map(x => [x.name, x]));
  assert.equal(by["Heydər Əliyev prospekti"].m, 1200); assert.equal(by["Heydər Əliyev prospekti"].heavy + by["Heydər Əliyev prospekti"].severe, 900);
  assert.equal(T.levelOf(by["Heydər Əliyev prospekti"]).id, "sixtixac");
  assert.equal(T.levelOf(by["Babək prospekti"]).id, "serbest");
  assert.equal(T.levelOf(by["Dalan"]), null, "600 m-dən qısa küçə xəbər vermir");
  assert.equal(T.levelOf({ m: 2000, known: 400, heavy: 2000, severe: 0, moderate: 0 }), null, "məlumatı az olan küçə xəbər vermir");
});

test("tixac: news only when a street changes — jam starts, gets worse, clears; never on every cycle", () => {
  const row = (level, text) => ({ name: "Tbilisi prospekti", dir: "şəhərə doğru", level, text, jamKm: "1,8", extra: 4 });
  assert.match(T.eventFor(row("tixac", "tıxac"), undefined), /^Tbilisi prospekti \(şəhərə doğru\): tıxac, 1,8 km hissədə hərəkət çətindir, yol adi haldan təxminən 4 dəq çox çəkir\.$/);
  assert.match(T.eventFor(row("sixtixac", "sıx tıxac"), "tixac"), /sıx tıxac/);
  assert.equal(T.eventFor(row("tixac", "tıxac"), "tixac"), null, "dəyişməyibsə xəbər yoxdur");
  assert.equal(T.eventFor(row("tixac", "tıxac"), "sixtixac"), null, "sıxdan adi tıxaca düşmək ayrıca xəbər deyil");
  assert.match(T.eventFor(row("serbest", "hərəkət sərbəstdir"), "sixtixac"), /tıxac azalıb, hərəkət sərbəstdir/);
  assert.equal(T.eventFor(row("leng", "hərəkət ləngdir"), undefined), null);
});

test("tixac: a run makes one request per route (35 routes, all districts), keeps the token out of logs, respects the daily cap and keeps 12 hours of news", async () => {
  const urls = [], logs = [], token = "pk.SIRRITOKEN123";
  const jam = route([["Ziya Bünyadov prospekti", ["heavy", "heavy", "heavy", "low"]]], [{ id: "i1", type: "accident", affected_road_names: ["Ziya Bünyadov prospekti"], impact: "major" }]);
  const fetchFn = async url => { urls.push(url); return { ok: true, json: async () => jam }; };
  const now = Date.parse("2026-11-16T05:00:00Z"); // Bakı 09:00, şəhərə doğru
  const d = await T.run({ token, prev: { events: [{ t: now - 13 * 3600e3, text: "köhnə" }, { t: now - 3600e3, text: "təzə" }] }, now, fetchFn, log: s => logs.push(s) });
  assert.equal(urls.length, T.ROUTES.length); assert.equal(T.ROUTES.length, 35); assert.ok(urls.every(u => u.includes("/driving-traffic/") && u.includes("annotations=congestion,distance")));
  assert.ok(!logs.join("\n").includes(token), "açar jurnala düşmür");
  assert.equal(d.used, 35); assert.ok(!("jam" in d.routes[0]), "ara ölçü sayları fayla düşmür"); assert.equal(d.routes[0].rayon, "Binəqədi"); assert.equal(d.routes[0].dir, "şəhərə doğru"); assert.equal(d.routes[0].typ, 10); assert.equal(d.routes[0].min, 15);
  assert.deepEqual(d.streets.map(s => s.level), ["sixtixac"], "eyni küçə 35 marşrutda: bir sətir");
  assert.equal(d.counted, 1); assert.equal(d.jammed, 1);
  assert.equal(d.rayons.length, 11, "bir marşrutlu Qaradağ (1,2 km məlumat) bal almır"); assert.ok(d.rayons.every(z => z[1] === 10));
  assert.deepEqual(Array.from(d.watch[2]), ["Ziya Bünyadov prospekti", "sixtixac", "0,9"], "səkkiz yoldan biri"); assert.equal(d.watch.length, 8); assert.equal(d.watch[0][1], "?", "ölçülməyən yol «?»");
  const h = T.history([{ t: now - 31 * 3600e3 }, { t: now - 3600e3, r: [] }], d, now);
  assert.equal(h.length, 2, "30 saatdan köhnə nüsxə düşür"); assert.deepEqual(h[1].w, d.watch); assert.deepEqual(h[1].i, ["Qəza: Ziya Bünyadov prospekti. Təsiri böyükdür."]); assert.deepEqual(h[1].r[0], ["simal", 15, 10]);
  assert.ok(d.events.some(e => e.text.startsWith("Qəza: Ziya Bünyadov")) && d.events.some(e => e.text.startsWith("Ziya Bünyadov prospekti (şəhərə doğru): sıx tıxac")) && d.events.some(e => e.text === "təzə") && !d.events.some(e => e.text === "köhnə"), "12 saatdan köhnə xəbər çıxır");
  // ikinci dövrə: dəyişiklik yoxdur → yeni xəbər yoxdur, eyni hadisə təkrarlanmır
  const again = await T.run({ token, prev: d, now: now + 300e3, fetchFn, log: () => {} });
  assert.equal(again.events.length, d.events.length); assert.equal(again.used, 70);
  // gündəlik hədd
  urls.length = 0;
  const capped = await T.run({ token, prev: { ...d, used: T.DAILY_CAP - T.ROUTES.length + 1 }, now: now + 600e3, fetchFn, log: () => {} });
  assert.equal(urls.length, 0, "dövrə həddi keçəcəksə heç bir sorğu getmir (yarımçıq ölçü yoxdur)"); assert.equal(capped.capped, true);
  const nextDay = await T.run({ token, prev: { ...d, used: T.DAILY_CAP }, now: now + 86400e3, fetchFn, log: () => {} });
  assert.equal(nextDay.used, 35, "yeni gündə say sıfırdan başlayır"); urls.length = 0;
  // axşam: şəhərdən çıxış (marşrut tərsinə)
  urls.length = 0;
  const eve = await T.run({ token, prev: {}, now: Date.parse("2026-11-16T14:00:00Z"), fetchFn, log: () => {} });
  assert.equal(eve.routes[0].dir, "şəhərdən çıxış"); assert.ok(urls[0].includes(T.ROUTES[0].pts[2].join(",") + ";"), "axşam marşrut mərkəzdən başlayır");
  // xəta: açar xətada görünmür, əvvəlki tıxac bir saat qalır (yalançı «açıldı» xəbəri yoxdur)
  const failing = async url => ({ ok: false, status: 401, text: async () => `{"message":"Not Authorized - Invalid Token","url":"${url}"}` });
  const errLogs = [];
  const err = await T.run({ token, prev: d, now: now + 900e3, fetchFn: failing, log: s => errLogs.push(s) });
  assert.ok(!errLogs.join("\n").includes(token) && errLogs.join("\n").includes("HTTP 401"));
  assert.deepEqual(err.streets.map(s => s.level), ["sixtixac"]); assert.equal(err.events.length, d.events.length);
});

test("tixac: the workflow only writes the «tixac» branch, the token is only in the measuring steps, the budget fits the free plan", () => {
  const y = fs.readFileSync(path.join(root, ".github/workflows/tixac.yml"), "utf8");
  assert.equal((y.match(/secrets\.MAPBOX_TOKEN/g) || []).length, 2);
  assert.ok(/git push -q --force "\$URL" HEAD:refs\/heads\/tixac\n/.test(y) && !/refs\/heads\/main\b(?!')/.test(y.replace("github.ref == 'refs/heads/main'", "")));
  assert.ok(y.includes("- cron: '*/6 3-5,13-15 * * *'") && y.includes("- cron: '0,30 6-12,16-17 * * *'"));
  const perDay = (3 * 10 * 2) + (7 * 2 + 2 * 2); // pik: 6 saat × 10; qalan: 9 saat × 2
  assert.equal(perDay, 78); assert.ok(perDay * T.ROUTES.length * 31 < 90000, "31 günlük ayda 90 000-dən az (pulsuz hədd 100 000)");
  assert.ok(T.DAILY_CAP >= perDay * T.ROUTES.length && T.DAILY_CAP * 31 <= 93000, "gündəlik hədd ayı 100 000-dən aşağı saxlayır");
  assert.ok(y.includes("[ -f out/tixac.json ] || {") && y.includes("git add tixac.json tarix.json hafta.json"), "hədd günü heç nə yazılmır");
});

test("tixac: the Tıxac page shows the measurement only when it is fresh, with escaped street names", () => {
  const src = fs.readFileSync(path.join(root, "assets/app.js"), "utf8");
  assert.ok(src.includes('const TIX_URL = "https://raw.githubusercontent.com/8ulduz/8ulduz/tixac/tixac.json";'));
  assert.ok(src.includes("if (!d || !(Date.now() - at < 3 * 3600e3)) return \"\";"), "köhnə ölçü göstərilmir");
  assert.ok(src.includes("<b>${esc(s.name)}</b>") && src.includes("${esc(e.text)}"), "küçə adı və xəbər mətn kimi");
  assert.ok(src.includes("Mənbə: Mapbox tıxac məlumatı"), "mənbə göstərilir");
  const tix = src.slice(src.indexOf("function trafficView"), src.indexOf("function officialRoad"));
  assert.ok(tix.length > 500 && !/vtomatik/.test(tix) && !/vtomatik/.test(src.slice(src.indexOf("const TIX_URL"), src.indexOf("const TIX_URL") + 4000)), "sahib 2026-11-14: «avtomatik» sözü yoxdur");
  assert.ok(src.includes("<h1>Tıxac-İndi</h1>") && src.includes("name = \"Tıxac-İndi\""), "başlıq «Tıxac-İndi»");
  assert.ok(src.includes("<h3>Rayonlar üzrə tıxac balı</h3>") && src.includes("<b>${esc(n)}</b> — ${b | 0}/10"), "rayon balı: ad mətn kimi, bal rəqəm kimi");
  assert.ok(src.includes("Bakıda tıxaclı küçə: ${d.jammed | 0}") && src.includes("ölçülən ${d.counted | 0} küçədən"), "şəhər xülasəsi rəqəm kimi");
});

test("tixac: routes cover every district, a lost route is rejected, district scores and the weekly tally", async () => {
  assert.deepEqual([...new Set(T.ROUTES.map(r => r.rayon))].sort(), ["Abşeron", "Binəqədi", "Nərimanov", "Nəsimi", "Nizami", "Qaradağ", "Sabunçu", "Suraxanı", "Səbail", "Xətai", "Xəzər", "Yasamal"].sort());
  assert.equal(new Set(T.ROUTES.map(r => r.id)).size, 35);
  // 2026-11-14 sınağı: dənizə düşən nöqtə bərə ilə İrana gedən 1 830 km-lik marşrut verdi
  const far = route([["Bakı - Türkmənbaşı Bərəsi", ["unknown"]]]); far.routes[0].distance = 1829700;
  const d = await T.run({ token: "pk.x", prev: {}, now: Date.parse("2026-11-16T05:00:00Z"), fetchFn: async () => ({ ok: true, json: async () => far }), log: () => {} });
  assert.equal(d.routes.length, 0); assert.equal(d.errors, 35);
  assert.deepEqual(T.rayonScores([{ rayon: "Nəsimi", jam: 1000, mod: 0, known: 2500 }, { rayon: "Yasamal", jam: 0, mod: 1000, known: 5000 }, { rayon: "Qaradağ", jam: 1000, mod: 0, known: 1500 }]),
    [["Nəsimi", 10, "1,0"], ["Yasamal", 3, "0,0"]], "40% ağır = 10; orta yarım sayılır; 2 km-dən az məlumat bal almır");
  const snap = { day: "2026-11-16", updatedAt: "2026-11-16T04:00:00Z", rayons: [["Nəsimi", 6, "1,0"]],
    streets: [{ name: "Təbriz küçəsi", level: "tixac", jamKm: "1,2" }, { name: "Təbriz küçəsi", level: "sixtixac", jamKm: "2,5" }, { name: "Füzuli küçəsi", level: "leng", jamKm: "0,0" }] };
  let w = T.week({ days: { "2026-11-16": { n: 1, s: {}, z: {} } } }, snap); // köhnə formatlı gün (m, k yoxdur)
  w = T.week(w, { ...snap, updatedAt: "2026-11-16T08:00:00Z" });
  assert.deepEqual(w.days["2026-11-16"], { n: 3, s: { "Təbriz küçəsi": 2 }, m: { "Təbriz küçəsi": 36 }, k: { "Təbriz küçəsi": 2.5 }, z: { "Nəsimi": 12 } },
    "Bakı 08:00 pik (6 dəq), 12:00 adi (30 dəq); iki istiqamət bir dəfə; ən uzun tıxac km");
  for (let i = 1; i <= 9; i++) w = T.week(w, { ...snap, day: `2026-11-${16 + i}` });
  assert.equal(Object.keys(w.days).length, 8, "8 gün saxlanır"); assert.ok(!w.days["2026-11-16"]);
});
