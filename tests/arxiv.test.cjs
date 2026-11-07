// Daimi xəbər arxivi (sahib, 2026-11-07: «100 000 əlavə faylda da yayım və sayt ağırlaşmasın»): .github/scripts/arxiv.cjs.
const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs"), path = require("node:path"), vm = require("node:vm");
const root = path.join(__dirname, "..");
const A = require("../.github/scripts/arxiv.cjs");

test("arxiv: the hour comes from the story's own time string — the site, the bots and the share page use the same rule", () => {
  assert.equal(A.hourOf("2026-11-07T13:05:00+04:00"), "26110713");
  assert.equal(A.hourOf("2026-11-07T23:59:59Z"), "26110723");
  assert.equal(A.hourOf(""), "");
  const js = fs.readFileSync(path.join(root, "assets/app.js"), "utf8");
  const src = js.match(/const hourOf = a => [^\n]+/)[0];
  const appHour = vm.runInNewContext(`${src}; hourOf`);
  for (const iso of ["2026-11-07T13:05:00+04:00", "2026-01-31T00:00:00.000Z", "x"]) assert.equal(appHour({ publishedAt: iso }), A.hourOf(iso), iso);
  assert.ok(fs.readFileSync(path.join(root, "updater.py"), "utf8").includes(`re.match(r"20(\\d\\d)-(\\d\\d)-(\\d\\d)T(\\d\\d)", str(a.get("publishedAt") or ""))`), "paylaşma səhifəsi də eyni saat");
});

test("arxiv: rows go to their hour once, unchanged rows do not rewrite a file, blocked and non-hex rows are left out", () => {
  const b = {}, row = (id, t, extra = {}) => ({ id, title: "Xəbər " + id, sourceUrl: "https://apa.az/" + id, source: "APA", publishedAt: t, category: "gundem", junk: "x", ...extra });
  const rows = [row("a".repeat(16), "2026-11-07T13:05:00Z"), row("b".repeat(16), "2026-11-07T14:01:00Z", { alts: [{ source: "Report", sourceUrl: "https://report.az/1", imageUrl: "i" }] }), row("1", "2026-11-07T13:00:00Z"), row("c".repeat(16), "2026-11-07T13:30:00Z", { bad: 1 })];
  assert.deepEqual(A.merge(b, rows, a => !a.bad), ["26110713", "26110714"]);
  assert.deepEqual(Object.keys(b["26110713"]), ["a".repeat(16)]);
  assert.equal(b["26110713"]["a".repeat(16)].junk, undefined, "yalnız lazım olan sahələr");
  assert.deepEqual(b["26110714"]["b".repeat(16)].alts, [{ source: "Report", sourceUrl: "https://report.az/1" }]);
  assert.deepEqual(A.merge(b, rows, a => !a.bad), [], "dəyişməyən saat yenidən yazılmır");
  assert.ok(A.tooOld("25010100", Date.UTC(2026, 10, 7)) && !A.tooOld("26110713", Date.UTC(2026, 10, 7)));
});

test("arxiv: nothing is added to main or the site; the job runs apart from the news pipeline and keeps no history", () => {
  const wf = fs.readFileSync(path.join(root, ".github/workflows/arxiv.yml"), "utf8"), sc = fs.readFileSync(path.join(root, ".github/scripts/arxiv.cjs"), "utf8");
  assert.ok(wf.includes("group: arxiv") && wf.includes("--branch arxiv") && wf.includes("--filter=blob:none"), "ayrıca budaq, yalnız lazım olan fayllar endirilir");
  assert.ok(sc.includes('"commit-tree", tree, "-m"') && !/commit-tree[^\n]*"-p"/.test(sc), "valideynsiz commit: tarixçə yoxdur");
  assert.ok(sc.includes("refs/heads/${BRANCH}") && sc.includes('BRANCH = "arxiv"') && !sc.includes("refs/heads/main"));
  assert.ok(!fs.readFileSync(path.join(root, ".github/scripts/pipeline.sh"), "utf8").includes("arxiv.cjs"), "60 saniyəlik axına toxunmur");
  const js = fs.readFileSync(path.join(root, "assets/app.js"), "utf8");
  assert.ok(js.includes("https://raw.githubusercontent.com/8ulduz/8ulduz/arxiv/") && js.includes("${R}saat/${h}.json") && js.includes("${R}idx/${id.slice(0, 2)}.json") && js.includes("await shareRow(id) || await arxRow(id)"), "sayt yalnız köhnə keçiddə oxuyur");
  assert.ok(/return r && !removedSource\(r\) && !policyViolation\(r\) \? r : null;\n\}\n\/\/ Paylaşılan keçid/.test(js.replace(/\r\n/g, "\n")), "arxivdən gələn sətir də qaydadan keçir");
});

test("arxiv: the hours already on the branch are read by hour name, so nothing recent is dropped as «old» (bug 2026-11-07)", () => {
  const os = require("node:os"), { execFileSync } = require("node:child_process");
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), "arxiv-")), g = (...a) => execFileSync("git", ["-C", dir, ...a], { encoding: "utf8" });
  g("init", "-q");
  fs.mkdirSync(path.join(dir, "saat")); fs.mkdirSync(path.join(dir, "idx"));
  fs.writeFileSync(path.join(dir, "saat", "26110713.json"), "{}"); fs.writeFileSync(path.join(dir, "saat", "26110603.json"), "{}"); fs.writeFileSync(path.join(dir, "idx", "ab.json"), "{}");
  g("add", "."); g("-c", "user.name=t", "-c", "user.email=t@t", "commit", "-qm", "t");
  const hours = A.readHours(dir);
  assert.deepEqual([...hours.keys()].sort(), ["26110603", "26110713"]);
  for (const h of hours.keys()) assert.equal(A.tooOld(h, Date.UTC(2026, 10, 7)), false, h);
  assert.equal(A.readHours(path.join(dir, "yoxdur")).size, 0, "budaq yoxdursa boş");
  fs.rmSync(dir, { recursive: true, force: true });
});
