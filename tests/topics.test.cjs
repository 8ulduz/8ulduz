// .github/scripts/topics.cjs: rayon və idman mövzu səhifələri (sahib, 2026-11-06: Google «Quba xəbərləri» axtarışında tapsın).
const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("fs"), os = require("os"), path = require("path"), vm = require("vm");
const root = path.join(__dirname, "..");
const T = require("../.github/scripts/topics.cjs");

const NOW = Date.parse("2026-11-06T18:00:00Z");
const iso = h => new Date(NOW - h * 3600e3).toISOString();
const art = (id, title, category, h, source = "APA") => ({ id, title, summary: "", category, source, sourceUrl: `https://apa.az/${id}`, publishedAt: iso(h), lang: "az" });

function site(articles) {
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), "movzu-"));
  fs.mkdirSync(path.join(dir, "assets")); fs.mkdirSync(path.join(dir, "data")); fs.mkdirSync(path.join(dir, "xeber"));
  for (const f of ["app.js", "content-policy.js"]) fs.copyFileSync(path.join(root, "assets", f), path.join(dir, "assets", f));
  fs.writeFileSync(path.join(dir, "data/news.json"), JSON.stringify({ articles }));
  fs.writeFileSync(path.join(dir, "xeber/index.json"), JSON.stringify({ q1: [0, 5, "bolgeler"] }));
  return dir;
}
const read = (dir, f) => fs.readFileSync(path.join(dir, f), "utf8");
const items = html => (html.match(/<li>/g) || []).length;

test("topics: every region and sport topic gets a real page; enough news → indexed and in sitemap, too few → noindex", () => {
  const dir = site([art("q1", "Qubada qar yağıb", "bolgeler", 1), art("q2", "Quba rayonunda yeni məktəb açıldı", "gundem", 2), art("q3", "Qubanın dağ kəndlərinə qaz verildi", "cemiyyet", 3),
    art("z1", "Zaqatalada fındıq yığımı başa çatdı", "bolgeler", 4), art("f1", "“Qarabağ” “Neftçi”ni məğlub etdi", "idman", 1), art("f2", "Qubada futbol məktəbi açıldı", "idman", 2)]);
  const r = T.run(dir, { now: NOW });
  assert.ok(r.topics > 100, "bütün bölgə, rayon, idman bölməsi və komanda");
  const quba = read(dir, "rayon/quba/index.html");
  assert.equal(items(quba), 3, "Quba xəbərləri; idman xəbəri rayon səhifəsinə düşmür");
  assert.ok(quba.includes("<title>Quba xəbərləri — son xəbərlər — 8ulduz</title>") && quba.includes("<h1>Quba xəbərləri</h1>"));
  assert.ok(quba.includes('<link rel="canonical" href="https://8ulduz.az/rayon/quba/" />') && !quba.includes("noindex"));
  assert.ok(quba.includes('href="https://8ulduz.az/xeber/q1/"'), "öz səhifəsi olan xəbər ora aparır");
  assert.ok(quba.includes('href="https://8ulduz.az/#/bolme/bolgeler?m=Quba"'), "saytda həmin rayon açılır");
  assert.ok(quba.includes('href="https://8ulduz.az/rayon/qusar/"') && quba.includes('href="https://8ulduz.az/rayon/quba-xacmaz/"'), "qonşu rayonlar və bölgə");
  assert.ok(!/<script(?![^>]*type="application\/(?:ld\+)?json")/.test(quba), "səhifə skriptsizdir (sürət)");
  assert.ok(read(dir, "rayon/zaqatala/index.html").includes('content="noindex, follow"'), "1 xəbərli səhifə indekslənmir");
  const futbol = read(dir, "idman/qarabag/index.html");
  assert.equal(items(futbol), 1); assert.ok(futbol.includes("Qarabağ futbol klubu xəbərləri"));
  const map = read(dir, "sitemap-movzu.xml");
  assert.ok(map.includes("<loc>https://8ulduz.az/rayon/quba/</loc>") && map.includes("<loc>https://8ulduz.az/rayon/quba-xacmaz/</loc>"));
  assert.ok(!map.includes("rayon/zaqatala/") && !map.includes("idman/qarabag/"), "az xəbərli səhifə sitemap-də yoxdur");
  assert.equal(T.slugify("Şəki-Zaqatala"), "seki-zaqatala"); assert.equal(T.slugify("İsmayıllı"), "ismayilli"); assert.equal(T.slugify("Boks və UFC"), "boks-ve-ufc");
});

test("topics: a page keeps its own history for 30 days (the archive is 1-2 days) and is rewritten at most hourly", () => {
  const dir = site([art("q1", "Qubada qar yağıb", "bolgeler", 1), art("q2", "Quba rayonunda yeni məktəb açıldı", "gundem", 2), art("q3", "Qubanın dağ kəndlərinə qaz verildi", "cemiyyet", 3)]);
  T.run(dir, { now: NOW });
  fs.writeFileSync(path.join(dir, "data/news.json"), JSON.stringify({ articles: [art("q4", "Qubada &quot;Alma&quot; festivalı", "bolgeler", 0)] }));
  T.run(dir, { now: NOW + 20 * 60e3 });
  assert.equal(items(read(dir, "rayon/quba/index.html")), 3, "bir saat keçməyib: yazılmır");
  T.run(dir, { now: NOW + 2 * 3600e3 });
  let quba = read(dir, "rayon/quba/index.html");
  assert.equal(items(quba), 4, "köhnə xəbərlər lentdən çıxsa da səhifədə qalır");
  assert.ok(quba.includes("Qubada &quot;Alma&quot; festivalı") && !quba.includes("&amp;quot;"), "işarələr bir dəfə qaçırılır");
  fs.writeFileSync(path.join(dir, "data/news.json"), JSON.stringify({ articles: [] }));
  T.run(dir, { now: NOW + 31 * 86400e3 });
  quba = read(dir, "rayon/quba/index.html");
  assert.equal(items(quba), 0, "30 gündən köhnə xəbər çıxır"); assert.ok(quba.includes("noindex"));
});

test("topics: the site opens the topic from the link; pipeline publishes the pages; robots lists the sitemap", () => {
  const ctx = vm.createContext({ console, Map, Set, URL, Date, AbortController, setTimeout, clearTimeout, addEventListener() {},
    localStorage: { getItem() { return null; }, setItem() {}, removeItem() {} }, location: { hash: "#/bolme/bolgeler?m=Quba" }, navigator: { onLine: true },
    window: { addEventListener() {} }, document: { documentElement: { dataset: {} }, addEventListener() {}, querySelector() { return null; }, createElement() { return {}; } }, matchMedia: () => ({ matches: false }) });
  vm.runInContext(fs.readFileSync(path.join(root, "assets/app.js"), "utf8").split(/\r?\napplyPrefs\(\);\r?\n/)[0], ctx);
  const r = vm.runInContext("route()", ctx);
  assert.equal(r.slug, "bolgeler"); assert.equal(r.m, "Quba");
  ctx.location.hash = "#/bolme/idman?m=Boks%20v%C9%99%20UFC";
  assert.equal(vm.runInContext("route().m", ctx), "Boks və UFC");
  const src = fs.readFileSync(path.join(root, "assets/app.js"), "utf8");
  assert.ok(src.includes("if (um && sportTopic(um) && S.clubUrl !== location.hash) { S.club = um;"), "keçid mövzunu seçir");
  const sh = fs.readFileSync(path.join(root, ".github/scripts/pipeline.sh"), "utf8").replace(/\r\n/g, "\n");
  assert.ok(sh.includes('node "$REPO_DIR/.github/scripts/topics.cjs" "$REPO_DIR"') && sh.includes("    prerender_home\n    topic_pages\n") && sh.includes("for name in rayon idman sitemap-movzu.xml"));
  assert.ok(fs.readFileSync(path.join(root, "updater.py"), "utf8").includes(String.raw`"Sitemap: " + SITE + "sitemap-movzu.xml\n"`));
});

test("topics: «$» in a headline is plain text, not a String.replace pattern", () => {
  const titles = ["Qubada “Go home pu$$y” plakatı", "Quba üçün 50 milyon $'lık layihə", "Qubada $& və $` işarəli elan", "Quba: __ITEMS__ sözü olan başlıq"];
  const dir = site(titles.map((t, i) => art("q" + (i + 1), t, "bolgeler", i + 1)));
  T.run(dir, { now: NOW });
  const html = read(dir, "rayon/quba/index.html");
  const esc = s => s.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/"/g, "&quot;");
  for (const t of titles) assert.ok(html.includes(esc(t)) || html.includes(t), "başlıq olduğu kimi: " + t);
  assert.equal(html.split("</script>").length - 1, read(root, ".github/scripts/topics.cjs").match(/const PAGE = [\s\S]*?;\n/)[0].split("</script>").length - 1, "şablonun qalanı səhifəyə ikinci dəfə yapışmır");
  const data = JSON.parse(html.match(/<script type="application\/json" id="movzu">([\s\S]*?)<\/script>/)[1]);
  assert.deepEqual(data.items.map(i => i.t).sort(), [...titles].sort(), "saxlanan siyahı oxunur (səhifə hər yayımda yenidən yazılmır)");
  assert.equal(items(html), titles.length);
  assert.deepEqual([...new Set(html.match(/__[A-Z0-9_]+?__/g))], ["__ITEMS__"], "doldurulmamış yer qalmır; başlıqdakı «__ITEMS__» mətn kimi qalır");
});
