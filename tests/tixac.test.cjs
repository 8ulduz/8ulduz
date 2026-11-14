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

test("tixac: a run makes three requests, keeps the token out of logs, respects the daily cap and keeps 12 hours of news", async () => {
  const urls = [], logs = [], token = "pk.SIRRITOKEN123";
  const jam = route([["Ziya Bünyadov prospekti", ["heavy", "heavy", "heavy", "low"]]], [{ id: "i1", type: "accident", affected_road_names: ["Ziya Bünyadov prospekti"], impact: "major" }]);
  const fetchFn = async url => { urls.push(url); return { ok: true, json: async () => jam }; };
  const now = Date.parse("2026-11-16T05:00:00Z"); // Bakı 09:00, şəhərə doğru
  const d = await T.run({ token, prev: { events: [{ t: now - 13 * 3600e3, text: "köhnə" }, { t: now - 3600e3, text: "təzə" }] }, now, fetchFn, log: s => logs.push(s) });
  assert.equal(urls.length, 3); assert.ok(urls.every(u => u.includes("/driving-traffic/") && u.includes("annotations=congestion,distance")));
  assert.ok(!logs.join("\n").includes(token), "açar jurnala düşmür");
  assert.equal(d.used, 3); assert.equal(d.routes[0].dir, "şəhərə doğru"); assert.equal(d.routes[0].typ, 10); assert.equal(d.routes[0].min, 15);
  assert.deepEqual(d.streets.map(s => s.level), ["sixtixac"], "eyni küçə üç marşrutda: bir sətir");
  assert.ok(d.events.some(e => e.text.startsWith("Qəza: Ziya Bünyadov")) && d.events.some(e => e.text.startsWith("Ziya Bünyadov prospekti (şəhərə doğru): sıx tıxac")) && d.events.some(e => e.text === "təzə") && !d.events.some(e => e.text === "köhnə"), "12 saatdan köhnə xəbər çıxır");
  // ikinci dövrə: dəyişiklik yoxdur → yeni xəbər yoxdur, eyni hadisə təkrarlanmır
  const again = await T.run({ token, prev: d, now: now + 300e3, fetchFn, log: () => {} });
  assert.equal(again.events.length, d.events.length); assert.equal(again.used, 6);
  // gündəlik hədd
  urls.length = 0;
  const capped = await T.run({ token, prev: { ...d, used: T.DAILY_CAP }, now: now + 600e3, fetchFn, log: () => {} });
  assert.equal(urls.length, 0, "hədd dolanda sorğu getmir"); assert.equal(capped.routes.length, 0);
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
  assert.ok(y.includes("- cron: '*/5 3-5,13-15 * * *'") && y.includes("- cron: '*/20 6-12,16-17 * * *'"));
  const perDay = (3 * 12 * 2) + (7 * 3 + 2 * 3); // pik: 6 saat × 12; qalan: 9 saat × 3
  assert.equal(perDay, 99); assert.ok(perDay * T.ROUTES.length * 31 < 10000, "31 günlük ayda 10 000-dən az"); assert.ok(T.DAILY_CAP * 31 > perDay * 3 * 31 && T.DAILY_CAP * 30 < 10000 + 100);
});

test("tixac: the Tıxac page shows the measurement only when it is fresh, with escaped street names", () => {
  const src = fs.readFileSync(path.join(root, "assets/app.js"), "utf8");
  assert.ok(src.includes('const TIX_URL = "https://raw.githubusercontent.com/8ulduz/8ulduz/tixac/tixac.json";'));
  assert.ok(src.includes("if (!d || !(Date.now() - at < 3 * 3600e3)) return \"\";"), "köhnə ölçü göstərilmir");
  assert.ok(src.includes("<b>${esc(s.name)}</b>") && src.includes("${esc(e.text)}"), "küçə adı və xəbər mətn kimi");
  assert.ok(src.includes("Avtomatik ölçü: Mapbox tıxac məlumatı"), "mənbə göstərilir");
});
