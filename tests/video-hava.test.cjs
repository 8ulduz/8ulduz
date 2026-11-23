// Gündəlik hava videosu (sahib, 2026-11-23): .github/scripts/video-hava.cjs. Məlumatdan mətnə, rəqəm dəqiqliyi, hədlər, kreditlər,
// ekran planı və yükləyicilərin müqaviləsi. ffmpeg burada işləmir: real video PR-da sosial-video.yml-də hazırlanır (hava nümunəsi).
const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("fs"), path = require("path");
const VH = require("../.github/scripts/video-hava.cjs");
const V = require("../.github/scripts/video-xeber.cjs");
const { loadApp } = require("../.github/scripts/topics.cjs");
const root = path.join(__dirname, "..");
const read = f => fs.readFileSync(path.join(root, f), "utf8").replace(/\r\n/g, "\n");
const app = loadApp(root), label = c => app.wxCode(c)[0];
const FX = JSON.parse(read("tests/fixtures/video-hava.json"));   // Open-Meteo-nun həqiqi cavabı, 23–25 noyabr
const LIST = VH.cities(app);
const copy = x => JSON.parse(JSON.stringify(x));
const rowsOf = (raw, day = "2026-11-25") => VH.parse(raw, LIST, day).rows;
const row = o => ({ name: "Bakı", code: 3, tmax: 10, tmin: 5, precip: 0, prob: 0, snow: 0, wind: 6, gust: 9, dir: 300, ...o });

test("hava: cities and coordinates come from the site itself (app.js CITIES) — one Open-Meteo request, m/s, Baku time zone", () => {
  assert.deepEqual(LIST.map(c => c.name), VH.SEHERLER);
  const site = new Map(app.CITIES.map(c => [String(c[0]), [Number(c[1]), Number(c[2])]]));
  for (const c of LIST) assert.deepEqual([c.lat, c.lon], site.get(c.name), `${c.name}: koordinat app.js-dəndir`);
  // updater.py-nin hava səhifələri də eyni nöqtələrdir (Bakı = bolme/hava/baki/).
  assert.ok(read("updater.py").includes('("Bakı", 40.4093, 49.8671)'));
  assert.throws(() => VH.cities(app, ["Bakı", "Atlantida"]), /Atlantida.*CITIES/);
  const u = VH.url(LIST);
  assert.ok(u.startsWith("https://api.open-meteo.com/v1/forecast?latitude=40.4093,40.5897,"), u);
  assert.match(u, /&wind_speed_unit=ms&timezone=Asia%2FBaku&forecast_days=3$/);
  for (const k of Object.keys(VH.DAILY)) assert.ok(u.includes(k), k);
  // Ödənişli plan (kommersiya istifadəsi): açar yalnız ünvanda, ayrıca host.
  assert.match(VH.url(LIST, "K3Y"), /^https:\/\/customer-api\.open-meteo\.com\/v1\/forecast\?.*&apikey=K3Y$/);
  assert.equal(VH.LINK, "https://8ulduz.az/bolme/hava/", "keçid birbaşa sayta (www paylaşma serveri bu yolu ana səhifəyə yönləndirir)");
});

test("hava: the response is checked — units, time zone, coordinates, day, limits; a bad city drops out, bad Baku means no video", () => {
  const { rows, why } = VH.parse(FX.response, LIST, "2026-11-25");
  assert.equal(rows.length, 9); assert.deepEqual(why, []);
  assert.deepEqual(rows[0], { name: "Bakı", code: 80, tmax: 13.9, tmin: 7.2, precip: 7, prob: 84, snow: 0, wind: 12.68, gust: 22.4, dir: 348 }, "xam ədədlər olduğu kimi");
  const bad = (i, f) => { const r = copy(FX.response); f(r[i]); return VH.parse(r, LIST, "2026-11-25"); };
  let p = bad(2, o => { o.daily_units.wind_speed_10m_max = "km/h"; });
  assert.equal(p.rows.length, 8); assert.match(p.why[0], /Gəncə: vahid: wind_speed_10m_max km\/h/);
  assert.match(bad(3, o => { o.latitude = 45; }).why[0], /Mingəçevir: koordinat/);
  assert.match(bad(4, o => { o.daily.temperature_2m_max[2] = 99; }).why[0], /Şəki: temperature_2m_max = 99/);
  assert.match(bad(5, o => { o.daily.temperature_2m_min[2] = 30; }).why[0], /Quba: maksimum minimumdan aşağıdır/);
  assert.match(bad(6, o => { o.timezone = "GMT"; }).why[0], /Lənkəran: saat qurşağı/);
  assert.match(bad(7, o => { o.daily.weather_code[2] = null; }).why[0], /weather_code yoxdur/);
  assert.equal(bad(8, o => { o.daily.precipitation_probability_max[2] = null; }).rows[8].prob, null, "ehtimal olmaya bilər");
  assert.throws(() => bad(0, o => { o.daily_units.temperature_2m_max = "°F"; }), /Bakı məlumatı yoxlamadan keçmədi/);
  assert.throws(() => VH.parse(FX.response, LIST, "2026-11-29"), /Bakı məlumatı/, "gün yoxdursa video yoxdur");
  assert.throws(() => VH.parse(FX.response.slice(1), LIST, "2026-11-25"), /9 nöqtə gözlənilirdi/);
});

test("hava: rounding is the site's (updater.py round — half to even), units as on the weather pages", () => {
  assert.deepEqual([14.5, 15.5, -2.5, -0.4, 13.9, 7.2, 22.4, 0.5].map(VH.rnd), [14, 16, -2, 0, 14, 7, 22, 0]);
  assert.ok(!Object.is(VH.rnd(-0.2), -0), "−0 yazılmır");
  assert.deepEqual([17, -3, 0].map(VH.deg), ["+17°", "−3°", "0°"]);
  assert.deepEqual([3.4, 0.6, 7, 12.6, 0].map(VH.mmText), ["3,4", "0,6", "7", "13", "0"]);
  assert.deepEqual(VH.nums(row({ tmax: 13.9, tmin: 7.2, wind: 12.68, gust: 22.4, precip: 7, snow: 2.87, prob: 84 })),
    { tmax: 14, tmin: 7, wind: 13, gust: 22, precip: "7", snow: 3, prob: 84 });
});

test("hava: the text is the data in a fixed template — Baku, wind (xəzri), amount, the warning, both pages of the regions", () => {
  const p = VH.plan(rowsOf(FX.response), "2026-11-25", { label, now: Date.parse(FX.now) });
  assert.equal(p.id, "hava-2026-11-25");
  assert.equal(p.title, "Hava proqnozu, 25 noyabr: Bakıda güclü külək, +7°…+14°", "tarixli başlıq (YouTube/TikTok təkrarı başlıqla tanıyır)");
  assert.equal(p.headline, "Sabah Bakıda güclü külək", "Bakıda xəbərdarlıq varsa başlıq odur");
  assert.deepEqual(p.parts.map(x => [x.sahne, x.text]), [
    ["giris", "Sabah, 25 noyabr, çərşənbə, hava belə olacaq."],
    ["baki", "Bakıda arabir yağış yağacaq."],
    ["baki", "Gecə 7, gündüz 14 dərəcə isti olacaq."],
    ["baki", "Şimal küləyi (xəzri) əsəcək, sürəti saniyədə 13 metrə, ani küləklərdə 22 metrə çatacaq."],
    ["baki", "Yağıntının miqdarı 7 millimetr olacaq."],
    ["diqqet", "Diqqət: ani küləklərin sürəti Bakıda saniyədə 22, Sumqayıtda 22 metrə çatacaq."],
    ["bolge0", "Gündüz Sumqayıtda 14, Gəncədə 11, Mingəçevirdə 12, Şəkidə 15 dərəcə isti olacaq."],
    ["bolge0", "Hamısında yağış yağacaq."],
    ["bolge1", "Qubada 10, Lənkəranda 15, Naxçıvanda 14, Şuşada 13 dərəcə isti gözlənilir."],
    ["bolge1", "Lənkəranda və Şuşada yağış yağacaq."],
    ["bolge1", "Qubada qar yağacaq."],
  ]);
  assert.deepEqual(p.xeberdarliq, [{ k: "kulek", seher: ["Bakı", "Sumqayıt"], line: "Ani külək: Bakı 22, Sumqayıt 22 m/san" }]);
  assert.deepEqual(p.bolgeler.map(pg => pg.map(c => c.name)), [["Sumqayıt", "Gəncə", "Mingəçevir", "Şəki"], ["Quba", "Lənkəran", "Naxçıvan", "Şuşa"]]);
  assert.equal(p.baki.label, "Yağışlı", "kodun adı saytdakı kimi (app.js wxCode)");
  assert.equal(p.link, VH.LINK);
  assert.equal(VH.yoxla(p, rowsOf(FX.response)), "");
  // Sakit gün (24 noyabr): «yağıntı gözlənilmir», cənub-qərb küləyi (gilavar deyil: yalnız cənub), xəbərdarlıq yoxdur.
  const q = VH.plan(rowsOf(FX.response, "2026-11-24"), "2026-11-24", { label });
  assert.equal(q.parts[1].text, "Bakıda hava buludlu olacaq, yağıntı gözlənilmir.");
  assert.equal(q.parts.find(x => /küləyi/.test(x.text)).text, "Cənub-qərb küləyi əsəcək, sürəti saniyədə 10 metrə, ani küləklərdə 18 metrə çatacaq.");
  assert.ok(!q.parts.some(x => x.sahne === "diqqet") && q.headline === "Sabah Bakıda buludlu hava");
  for (const c of q.parts) assert.ok(V.wrap(c.text, V.CAP_SIZE, "medium", V.CAP_W).length <= 3, `altyazı ≤ 3 sətir: ${c.text}`);
});

test("hava: frost is said as «şaxta» (the voice cannot read a minus), probability below 50% says «yağa bilər», calm wind, gilavar", () => {
  assert.equal(VH.geceGunduz(-5, -1), "Gecə 5, gündüz 1 dərəcə şaxta olacaq");
  assert.equal(VH.geceGunduz(-3, 4), "Gecə 3 dərəcə şaxta, gündüz 4 dərəcə isti olacaq");
  assert.equal(VH.geceGunduz(0, 6), "Gecə 0 dərəcə, gündüz 6 dərəcə isti olacaq");
  assert.equal(VH.siyahi([["Gəncədə", 4], ["Şəkidə", 2], ["Şuşada", -2], ["Qubada", 0]]), "Gəncədə 4, Şəkidə 2 dərəcə isti, Şuşada 2 dərəcə şaxta, Qubada 0 dərəcə");
  const p = VH.plan([row({ code: 61, prob: 40, precip: 0.4, tmin: -4.6, tmax: -0.6, wind: 2, gust: 3 }), ...["Sumqayıt", "Gəncə"].map(name => row({ name }))], "2027-01-12", { label });
  assert.equal(p.parts[1].text, "Bakıda yağış yağa bilər.");
  assert.equal(p.parts[2].text, "Gecə 5, gündüz 1 dərəcə şaxta olacaq.", "−4,6 → 5 (yarımda cüt), −0,6 → 1");
  assert.deepEqual(p.parts.slice(3, 5).map(x => x.text), ["Külək zəif olacaq.", "Yağıntının miqdarı 0,4 millimetr olacaq."], "hər cümlə ayrıca altyazıdır");
  assert.equal(p.title, "Hava proqnozu, 12 yanvar: Bakıda yağış, −5°…−1°");
  assert.ok(!p.text.includes("−") && !/-\d/.test(p.text), "səsə mənfi işarə getmir");
  assert.equal(VH.kulekCumle(VH.nums(row({ wind: 9, gust: 10, dir: 180 })), row({ dir: 180 }), true), "Cənub küləyi (gilavar) əsəcək, sürəti saniyədə 9 metrə çatacaq.");
  assert.equal(VH.kulekCumle(VH.nums(row({ wind: 9, dir: 180 })), row({ dir: 180 }), false), "Cənub küləyi əsəcək, sürəti saniyədə 9 metrə, ani küləklərdə 9 metrə çatacaq.".replace(", ani küləklərdə 9 metrə", ""));
  assert.deepEqual(["Bakı", "Gəncə", "Sumqayıt", "Mingəçevir", "Şuşa", "Lənkəran"].map(VH.loc), ["Bakıda", "Gəncədə", "Sumqayıtda", "Mingəçevirdə", "Şuşada", "Lənkəranda"]);
});

test("hava: warnings use oz_hava.py's thresholds (gust, frost, heat, snow) and the site's heavy rain; raw value decides, rounded value is shown", () => {
  const oz = read("oz_hava.py");
  const m = oz.match(/^GUST, FROST, FROST_BAKU, HEAT, SNOW, SNOW_LOW, WAVE = ([^\n]+)$/m)[1].split(",").map(Number);
  assert.deepEqual([VH.GUST, VH.FROST, VH.FROST_BAKU, VH.HEAT, VH.SNOW, VH.SNOW_LOW], m.slice(0, 6), "hədlər oz_hava.py ilə eynidir");
  assert.deepEqual(VH.MOUNTAIN, JSON.parse(oz.match(/^MOUNTAIN = \(([^)]+)\)/m)[1].replace(/^/, "[").replace(/$/, "]")), "dağ şəhərləri (qar həddi 10 sm)");
  assert.match(read("assets/app.js"), /if \(rain >= 20\) bits\.push/, "leysan həddi saytın hava zolağındakıdır");
  const rows = [row({ tmin: -5.2, gust: 19.6 }), row({ name: "Gəncə", tmax: 38.4 }), row({ name: "Quba", snow: 9.5, code: 73 }), row({ name: "Sumqayıt", snow: 5.2, code: 73 }),
    row({ name: "Lənkəran", precip: 24.6, code: 63, prob: 90 }), row({ name: "Şuşa", tmin: -12.4, code: 95, prob: 70 }), row({ name: "Naxçıvan", tmin: -9.9 })];
  const w = VH.xeberdarliq(rows);
  assert.deepEqual(w.map(x => x.k), ["leysan", "qar", "saxta"], "ən çox 3 növ, sıra ilə; ani külək 19,6 < 20 — yoxdur");
  assert.deepEqual(w.map(x => x.line), ["Güclü yağış: Lənkəran 25 mm", "Qar: Sumqayıt 5 sm", "Şaxta: Şuşa −12°, Bakı −5°"]);
  assert.ok(!w[1].seher.includes("Quba"), "Quba dağ şəhəridir: 9,5 sm < 10");
  assert.ok(!w[2].seher.includes("Naxçıvan"), "−9,9 > −10");
  const p = VH.plan(rows, "2027-01-12", { label });
  assert.equal(p.parts.filter(x => x.sahne === "diqqet").map(x => x.text).join(" "), "Diqqət: Lənkəranda 25 millimetr yağıntı gözlənilir. Sumqayıtda 5 santimetr qar yağacaq. Gecə Şuşada 12, Bakıda 5 dərəcə şaxta olacaq.");
  assert.equal(p.headline, "Sabah Bakıda şaxta");
  assert.equal(VH.yoxla(p, rows), "");
  const heat = VH.xeberdarliq([row({ name: "Gəncə", tmax: 39 }), row({ name: "Bakı", code: 96, prob: 80 })]);
  assert.deepEqual(heat.map(x => x.line), ["İstilik: Gəncə +39°", "İldırım: Bakı"]);
});

test("hava: the number check catches a number that is not in the data or belongs to another city", () => {
  const rows = rowsOf(FX.response), p = VH.plan(rows, "2026-11-25", { label });
  assert.equal(VH.yoxla(p, rows), "");
  const t = copy(p);
  t.parts[2].text = "Gecə 7, gündüz 19 dərəcə isti olacaq.";
  assert.match(VH.yoxla(t), /məlumatda olmayan rəqəm: 19/);
  const s = copy(p);
  s.parts[6].text = "Gündüz Sumqayıtda 14, Gəncədə 15, Mingəçevirdə 12, Şəkidə 11 dərəcə isti olacaq.";
  assert.match(VH.yoxla(s), /Gəncə: mətndə 15, məlumatda yoxdur/, "şəhərlərin rəqəmi dəyişdirilsə tutulur");
  const c = copy(p);
  c.bolgeler[0][1].tmax = 12;
  assert.match(VH.yoxla(c, rows), /Gəncə: tmax 12 ≠ məlumat 11/, "kart məlumatın yuvarlağıdır");
  const r = copy(rows); r[0].tmax = 15.6;
  assert.match(VH.yoxla(p, r), /Bakı: tmax 14 ≠ məlumat 16/);
  assert.match(VH.yoxla({ ...p, title: "Bakıda hava" }), /başlıq/);
});

// ASS: Dialogue sətirləri → { start, end, style, tags, text }.
const T = s => { const [h, m, x] = s.split(":"); return Number(h) * 3600 + Number(m) * 60 + Number(x); };
function events(a) {
  return a.split("\n").filter(l => l.startsWith("Dialogue:")).map(l => {
    const f = l.slice(10).split(",");
    const text = f.slice(9).join(",");
    return { start: T(f[1]), end: T(f[2]), style: f[3], raw: text, text: text.replace(/\{[^}]*\}/g, "") };
  });
}

test("hava: the screen — brand from first to last frame, every text inside y 300…1480, word-by-word captions equal the voice, credits", () => {
  const rows = rowsOf(FX.response), p = { ...VH.plan(rows, "2026-11-25", { label }), goruntuMenbe: "Pixabay" };
  const pr = VH.prepare(p), tl = V.timeline(pr, null);
  assert.ok(tl.duration >= 20 && tl.duration <= V.MAX_S, String(tl.duration));
  assert.equal(pr.say.at(-1), V.OUTRO_SAY, "sonda sayt adı səslənir");
  const ev = events(VH.ass(p, tl, { footage: true }));
  const brand = ev.find(e => e.style === "Brand" && e.text === ".az");
  assert.ok(brand && brand.start === 0 && Math.abs(brand.end - tl.duration) < 0.02, "«8ulduz.az» başdan sona");
  // Altyazılar: hər hissə bir dəfə, sözləri səsin mətni ilə eynidir (sözbəsöz), hər söz öz vaxtında narıncı.
  const caps = ev.filter(e => e.style === "Cap");
  assert.deepEqual(caps.map(e => e.text.replace(/\\N/g, " ")), pr.say.slice(0, -1));
  assert.ok(caps.every(e => (e.raw.match(/\\t\(/g) || []).length === 2 * e.text.replace(/\\N/g, " ").split(" ").length));
  // Yazılar y 300…1480 arasında (lentdə 4:5 kəsik və Reels düymələri); fon və sonluq istisna.
  for (const e of ev.filter(e => !["Shape", "Outro", "OutroBig"].includes(e.style))) {
    const m = e.raw.match(/\\(?:pos|move)\((\d+(?:\.\d+)?),(\d+(?:\.\d+)?)/);
    assert.ok(m && Number(m[2]) >= 300 && Number(m[2]) <= 1480, `${e.style} «${e.text}» y=${m?.[2]}`);
  }
  for (const e of ev.filter(e => e.style === "Shape" && e.start < tl.outro[0] && !/\\pos\(0,0\)|\\an5/.test(e.raw))) {
    const m = e.raw.match(/\\(?:pos|move)\(([\d.]+),([\d.]+)/);
    assert.ok(Number(m[2]) >= 300 && Number(m[2]) <= 1480, `forma y=${m[2]}`);
  }
  const all = ev.map(e => e.text).join("\n");
  assert.ok(all.includes("Hava: Open-Meteo, model proqnozu · Görüntü: Pixabay"), "kredit videoda");
  assert.ok(all.includes("Hava: Open-Meteo.com (CC BY 4.0) · Görüntü: Pixabay"), "sonluqda lisenziya");
  assert.ok(all.includes("Bütün şəhərlər: 8ulduz.az/bolme/hava"));
  for (const c of [p.baki, ...p.bolgeler.flat()]) assert.ok(all.includes(VH.deg(c.tmax)) && all.includes(c.name), `${c.name} kartı`);
  assert.ok(all.includes("Ani külək: Bakı 22, Sumqayıt 22 m/san") && all.includes("Model proqnozu, rəsmi xəbərdarlıq deyil"));
  // Səhnələr: Bakı, xəbərdarlıq, iki bölgə səhifəsi; bitişikdir, sonluqda bitir.
  const sc = VH.scenes(p, tl);
  assert.deepEqual(sc.map(s => s.key), ["baki", "diqqet", "bolge0", "bolge1"]);
  assert.ok(sc.every((s, i) => i === 0 ? s.from === 0 : s.from === sc[i - 1].to) && sc.at(-1).to === tl.outro[0]);
  // Görüntüsüz: brend fonu (hərəkətli işıq), «Görüntü:» yazılmır.
  assert.ok(!events(VH.ass(p, tl, { footage: false })).some(e => /Görüntü/.test(e.text)));
  // Mətndə ASS idarə simvolu işləmir.
  const bad = { ...p, headline: "Sabah {\\fs200} Bakıda" };
  assert.ok(!events(VH.ass(bad, tl)).some(e => /\\fs200/.test(e.text)));
});

test("hava: icons are vector shapes inside their own box (no emoji: libass has no colour emoji); the wind arrow points downwind", () => {
  for (const k of ["acik", "esasen", "qismen", "bulud", "duman", "ciskin", "yagis", "leysan", "dondurucu", "qar", "ildirim", "deyisken"]) {
    const list = VH.icon(k, 100, 800, 200);
    assert.ok(list.length >= 1, k);
    for (const { sh } of list) {
      const xy = sh.d.replace(/[mlb]/g, " ").trim().split(/\s+/).map(Number);
      assert.ok(xy.every(v => Number.isFinite(v) && v >= -0.01), `${k}: yol öz qutusundan (0,0) başlayır`);
      assert.ok(sh.x >= 90 && sh.x <= 310 && sh.y >= 790 && sh.y <= 1010, `${k}: qutunun içində (${sh.x}, ${sh.y})`);
    }
  }
  // Şimal küləyi (0) cənuba əsir: ox aşağı (ucu mərkəzdən aşağıda).
  const [{ sh }] = VH.arrow(0, 500, 500, 40), xy = sh.d.replace(/[ml]/g, " ").trim().split(/\s+/).map(Number);
  const ys = xy.filter((_, i) => i % 2).map(y => y + sh.y);
  assert.ok(Math.max(...ys) > 515 && Math.min(...ys) > 475, "ox aşağı göstərir");
  assert.equal(VH.kind(0), "acik"); assert.equal(VH.kind(45), "duman"); assert.equal(VH.kind(82), "leysan"); assert.equal(VH.kind(86), "arabirqar"); assert.equal(VH.kind(99), "dolu");
});

test("hava: footage fits the weather — Baku's own view first, nature scenes next, no foreign city streets; wind adds the sea", () => {
  const rows = rowsOf(FX.response), p = VH.plan(rows, "2026-11-25", { label });
  const q = VH.sahneler(p);
  assert.equal(q[0], "baku rain", "əvvəl Bakının həqiqi görüntüsü həmin havada");
  assert.ok(q.includes("caspian sea waves"), "güclü külək — Xəzərin dalğası");
  const sunny = VH.sahneler(VH.plan([row({ code: 0 }), row({ name: "Sumqayıt" })], "2026-07-01", { label }));
  assert.deepEqual(sunny.slice(0, 2), ["baku azerbaijan", "baku skyline"]);
  for (const k of Object.keys(VH.DAILY).length ? ["acik", "bulud", "duman", "yagis", "qar", "ildirim"] : []) {
    const list = VH.sahneler({ baki: { kind: k }, xeberdarliq: [] });
    assert.ok(list.length >= 4 && list.every(s => !/street|city|traffic|people|crowd/.test(s) || /^baku/.test(s)), `${k}: ${list}`);
  }
});

test("hava: video.json follows the TikTok/YouTube contract — own, kind «hava», the site's page, dated id and title, credits in the text", () => {
  const p = { ...VH.plan(rowsOf(FX.response), "2026-11-25", { label, now: Date.parse(FX.now) }), goruntuMenbe: "Pixabay" };
  const m = VH.storyFields(p);
  assert.deepEqual(Object.keys(m).sort(), ["category", "createdAt", "hashtags", "id", "kind", "lang", "own", "publishedAt", "summary", "text", "title", "url"].sort());
  assert.equal(m.own, true); assert.equal(m.kind, "hava"); assert.equal(m.url, "https://8ulduz.az/bolme/hava/"); assert.equal(m.id, "hava-2026-11-25");
  assert.match(m.text, /Hava məlumatı: Open-Meteo\.com, model proqnozu \(CC BY 4\.0\); rəsmi xəbərdarlıq deyil\. Görüntü: Pixabay\.$/);
  assert.equal(m.createdAt, "2026-11-24T16:47:00.000Z");
  const Y = require("../.github/scripts/youtube.cjs"), TT = require("../.github/scripts/tiktok.cjs");
  assert.equal(Y.kindOf(m), "hava");
  assert.equal(Y.linkOf(m), "https://8ulduz.az/bolme/hava/", "YouTube təsvirində hava səhifəsi");
  assert.ok(Y.descriptionOf(m).includes("CC BY 4.0") && Y.tagsOf(m).includes("hava proqnozu"));
  assert.ok(TT.caption(m).startsWith(p.title) && TT.caption(m).includes("Open-Meteo.com") && TT.caption(m).includes("#havaproqnozu"));
  const policy = a => app.policyViolation(a);
  assert.equal(Y.policyReason(m, policy), ""); assert.equal(TT.policyReason(m, policy), "");
  assert.equal(app.policyViolation(VH.policyRow(p)), false, "öz mətnimiz saytın qaydasından keçir (8ULDUZ)");
});
