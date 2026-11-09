// Büdcə qoruyucuları (sahib, 2026-11-09). Açılışın ən böyük baytları kod yox, updater.py-ın hər dəqiqə yazdığı məlumatdır və heç nə onu
// məhdudlaşdırmırdı: first.json 4 gündə 47 → 64 KB gzip böyüdü (hər +10 KB gzip telefonda ~13 ms ötürmə + ~4 ms JSON.parse, 4×);
// latest.json açıq hər vərəqdə hər dəqiqə yenidən gəlir. Burada hər məlumat faylının gzip tavanı, sətir sahələrinin siyahısı (yeni sahə =
// hər sətirə bayt), app.css/sw.js gzip və hazır ilk ekranın xam ölçüsü yoxlanır; bütün rəqəmlər tests/budce.json-dadır və
// docs/qirmizi-xetler.md §3 «Büdcə cədvəli» ilə eyni olmalıdır. Tavanlar: son 4 günün ən böyüyü + 20–25%.
// Qırmızı olsa faylı yox, qaydanı kiçildin (updater.py: first_screen_rows, LATEST_MAX, SHARE_FIELDS); hədd yalnız sahibin sətri ilə dəyişir.
const { test } = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs"), path = require("node:path"), zlib = require("node:zlib");
const root = path.join(__dirname, "..");
const read = f => fs.readFileSync(path.join(root, f), "utf8").replace(/\r\n/g, "\n");
const gz = f => zlib.gzipSync(Buffer.from(read(f)), { level: 9 }).length;
const B = require("./budce.json");
const file = key => key === "paylas.json.gz" ? null : "data/" + key.replace(/\.gz$/, "");

test("büdcə: data files served on every visit stay under their gzip ceilings (committed snapshot)", t => {
  const got = {};
  for (const [key, limit] of Object.entries(B.melumat)) {
    const files = key === "paylas.json.gz" ? fs.readdirSync(path.join(root, "data/paylas")).filter(f => f.endsWith(".json")).map(f => "data/paylas/" + f) : [file(key)];
    for (const f of files) {
      const n = gz(f); got[key] = Math.max(got[key] || 0, n);
      assert.ok(n < limit, `${f} ${n} B gzip ≥ ${limit}: updater.py-də sətir sayı və ya sahə artıb (first_screen_rows, LATEST_MAX, SHARE_FIELDS, og xəritəsi) — faylı yox, qaydanı kiçildin; hədd yalnız sahibin sətri ilə (docs §3 Büdcə cədvəli)`);
    }
  }
  t.diagnostic("məlumat gzip (ən böyük): " + JSON.stringify(got));
});

test("büdcə: feed rows carry only the known fields, no full text; share rows only the share fields", () => {
  const known = new Set(B.setir.saheler), share = new Set(B.setir["paylas.saheler"]);
  for (const f of ["data/first.json", "data/news.json", "data/latest.json"]) {
    for (const a of JSON.parse(read(f)).articles) {
      const extra = Object.keys(a).filter(k => !known.has(k));
      assert.deepEqual(extra, [], `${f}: sətirdə yeni sahə ${extra} — hər sahə hər sətirə baytdır (1 000 sətir × sahə); lazımdırsa tests/budce.json setir.saheler-ə sahibin qərarı ilə`);
      assert.ok(String(a.summary || "").length <= B.setir["xulase.max"], `${f} ${a.id}: xülasə ${String(a.summary).length} > ${B.setir["xulase.max"]} — tam mətn lentə düşməz`);
    }
  }
  for (const f of fs.readdirSync(path.join(root, "data/paylas")).filter(f => f.endsWith(".json"))) {
    for (const r of JSON.parse(read("data/paylas/" + f)).articles || []) {
      const extra = Object.keys(r).filter(k => !share.has(k));
      assert.deepEqual(extra, [], `paylas/${f}: paylaşma sətri yalnız SHARE_FIELDS (${extra})`);
    }
  }
});

test("büdcə: app.css and sw.js have gzip ceilings, the prerendered first screen a raw ceiling", t => {
  const got = { "app.css.gz": gz("assets/app.css"), "sw.js.gz": gz("sw.js") };
  for (const [k, limit] of Object.entries(B.gz)) assert.ok(got[k] < limit, `${k} ${got[k]} ≥ ${limit}`);
  const pre = read("index.html").match(/<div class="pre-skel" data-prerender="[^"]+">([\s\S]*?)<noscript>/);
  assert.ok(pre, "hazır ilk ekran index.html-dədir");
  got["pre-skel"] = Buffer.byteLength(pre[1]);
  assert.ok(got["pre-skel"] < B.xam["pre-skel"], `hazır ilk ekran ${got["pre-skel"]} B ≥ ${B.xam["pre-skel"]}: prerender.cjs daha çox kart saxlayır`);
  t.diagnostic("gzip/xam: " + JSON.stringify(got));
});

test("büdcə: the rule book lists every budget with the same number (owner decision, dated)", () => {
  const doc = read("docs/qirmizi-xetler.md");
  const table = doc.slice(doc.indexOf("### Büdcə cədvəli"));
  assert.ok(table.length > 100, "docs/qirmizi-xetler.md-də «### Büdcə cədvəli» yoxdur");
  const spaced = n => String(n).replace(/\B(?=(\d{3})+$)/g, " ");
  const esc = s => s.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
  const groups = { ...B.kod, ...B.gz, ...B.xam, ...B.melumat, "xulase.max": B.setir["xulase.max"] };
  for (const [k, v] of Object.entries(groups)) assert.ok(new RegExp("\\| `" + esc(k) + "` \\| " + spaced(v) + " \\|").test(table), `docs §3 Büdcə cədvəlində «${k}» = ${spaced(v)} sətri yoxdur: büdcə dəyişibsə cədvələ tarix və səbəblə yazın (yalnız sahibin qərarı)`);
  const rows = [...table.matchAll(/^\| `([^`]+)` \| /gm)].map(m => m[1]);
  for (const k of rows) assert.ok(k in groups, `cədvəldə artıq sətir: ${k} (tests/budce.json-da yoxdur)`);
});
