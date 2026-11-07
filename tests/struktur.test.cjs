// Struktur qoruyucuları (sahib, 2026-11-07: «strukturu elə qur ki, nə əlavə etsək, dəyişsək belə sayt ağırlaşmasın; bütün qırmızı
// cizgilərimiz ETİBARLI qorunsun»). Bu testlər konkret xüsusiyyəti yox, gələcək dəyişikliyin növünü tutur: yeni fayl ilk açılışa
// düşərsə, tənbəl modul şişərsə, sayta sərhədsiz qovluq əlavə olunarsa, xəbər yazan yeni skript mənbə qaydasını keçməzsə — test
// qırmızı olur və səbəbi deyir. Qaydanı yumşaltmaq yalnız sahibin açıq göstərişi ilə (docs/qirmizi-xetler.md, «Struktur»).
const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs"), path = require("node:path"), zlib = require("node:zlib");
const root = path.join(__dirname, "..");
const read = f => fs.readFileSync(path.join(root, f), "utf8").replace(/\r\n/g, "\n");
const gz = f => zlib.gzipSync(Buffer.from(read(f)), { level: 9 }).length;

test("struktur 1: the first visit loads exactly these files — a new feature must be a lazy module, not another startup file", () => {
  const html = read("index.html");
  const scripts = [...html.matchAll(/<script\b[^>]*\bsrc="([^"]+)"/g)].map(m => m[1]).sort();
  assert.deepEqual(scripts, ["./assets/app.js", "./assets/config.js", "./assets/content-policy.js"],
    "ilk açılışa yeni skript əlavə olunub — onu app.js-dən import() ilə yalnız lazım olanda yükləyin (bax: bayram.js, dinle.js)");
  const styles = [...html.matchAll(/<link\b[^>]*rel="stylesheet"[^>]*href="([^"]+)"/g)].map(m => m[1]);
  assert.deepEqual(styles, ["./assets/app.css"], "ilk açılışa yeni CSS faylı — stili tənbəl modulun özü yazsın");
  const preload = [...html.matchAll(/<link\b[^>]*rel="(?:modulepreload|preload)"[^>]*href="([^"]+)"/g)].map(m => m[1]);
  assert.ok(preload.every(h => h === "./assets/app.js" || /^https:\/\/wsrv\.nl\//.test(h)), "əvvəlcədən yükləmə yalnız app.js və ilk şəkil: " + preload.join(", "));
  const shellImgs = [...html.replace(/<main[\s\S]*?<\/main>/, "").matchAll(/<img\b[^>]*src="([^"]+)"/g)].map(m => m[1]);
  assert.deepEqual(shellImgs, ["./assets/logo-80.png"], "qabıqda (hazır ilk ekrandan kənarda) yalnız loqo şəkli olur");
});

test("struktur 2: startup bytes have one total ceiling (gzip), so many small additions cannot add up unnoticed", () => {
  const files = ["index.html", "assets/app.js", "assets/app.css", "assets/config.js", "assets/content-policy.js"];
  const sizes = Object.fromEntries(files.map(f => [f, gz(f)])), total = Object.values(sizes).reduce((a, b) => a + b, 0);
  assert.ok(sizes["index.html"] < 16e3, `index.html ${sizes["index.html"]} B gzip — hazır ilk ekran 16 KB-dan böyük olmamalıdır (prerender.cjs)`);
  assert.ok(total < 115e3, `ilk açılış kodu ${total} B gzip > 115 000: ${JSON.stringify(sizes)}`);
});

test("struktur 3: app.js has no static imports; every lazily loaded module exists and stays small", () => {
  const js = read("assets/app.js");
  assert.ok(!/^\s*import\s+[\w{*]/m.test(js), "app.js-də statik import ilk açılışı ağırlaşdırır — import() işlədin");
  const lazy = new Set([...js.matchAll(/import\(\s*[`'"](?:\$\{ASSET\}|\.\/)([\w-]+\.js)[`'"]\s*\)/g)].map(m => m[1]));
  assert.ok(lazy.size >= 5, "tənbəl modullar tapılmadı: " + [...lazy]);
  for (const f of lazy) {
    const p = path.join(root, "assets", f);
    assert.ok(fs.existsSync(p), "import() olmayan fayla: " + f);
    const n = read("assets/" + f).length;
    assert.ok(n < 40e3, `${f} ${n} B — tənbəl modul 40 KB-dan kiçik qalsın, böyüyürsə hissələrə bölün`);
  }
  const pre = (read("sw.js").match(/cache\.addAll\(\[([^\]]*)\]/) || [])[1] || "";
  assert.ok(pre.includes("./assets/app.js"), "sw ilkin keş siyahısı tapılmadı");
  for (const f of lazy) assert.ok(!pre.includes(f), `${f} service worker-in ilkin keşinə düşməsin (ilk ziyarətdə arxada endirilir)`);
});

test("struktur 4: pictures shipped with the site stay small", () => {
  for (const f of fs.readdirSync(path.join(root, "assets")).filter(f => /\.(png|jpe?g|webp|gif|svg|avif)$/i.test(f))) {
    const n = fs.statSync(path.join(root, "assets", f)).size;
    assert.ok(n < 110e3, `assets/${f} ${n} B — 110 KB-dan böyük şəkil olmaz (kiçildin və ya wsrv.nl ilə verin)`);
  }
});

test("struktur 5: the site (GitHub Pages) only gets folders with a known bound — per-story files go to the arxiv branch", () => {
  const sh = read(".github/scripts/pipeline.sh").replace(/\s#\s[^\n]*/g, "");
  const added = new Set();
  for (const line of sh.split("\n").filter(l => /git -C "\$REPO_DIR" add /.test(l))) {
    for (const m of line.matchAll(/add ([^2>;|]+?)(?: 2>|;|$)/g)) m[1].trim().split(/\s+/).filter(x => !x.startsWith("\"$")).forEach(x => added.add(x));
  }
  for (const m of sh.matchAll(/for name in ([a-z .-]+); do \[ -e "\$REPO_DIR\/\$name" \] && git -C "\$REPO_DIR" add/g)) m[1].trim().split(/\s+/).forEach(x => added.add(x));
  // Hər qovluğun həddi (sayı nə qədər xəbər olsa da böyümür) — yenisini əlavə edəndə həddini də burada yazın.
  const BOUND = {
    data: "sabit adlı fayllar; arxiv bölmə başına 200 xəbər", "sitemap.xml": "bir fayl", "feed.xml": "bir fayl", "robots.txt": "bir fayl", "index.html": "bir fayl",
    bolme: "bölmə səhifələri + sosial yazı səhifələri (30 gün, ≤ 400)", x: "paylaşma səhifələri, 25 saat (prune_share_pages)", xeber: "3+ mənbəli xəbərlər, 30 gün",
    icmal: "gündə 2 icmal", rayon: "rayon siyahısı qədər", idman: "idman mövzuları qədər", "sitemap-movzu.xml": "bir fayl",
  };
  assert.deepEqual([...added].sort(), Object.keys(BOUND).sort(), "sayta yeni qovluq yazılır — həddi yoxdursa arxiv budağına (arxiv.cjs) yazın");
  const up = read("updater.py");
  assert.ok(/SHARE_KEEP_S, SHARE_PARTS = 25 \* 3600/.test(up) && /STORY_KEEP_S = 30 \* 86400/.test(up) && /SOCIAL_ARCHIVE_DAYS, SOCIAL_ARCHIVE_MAX = 30, 400/.test(up), "qovluqların silinmə müddəti dəyişib");
});

test("struktur 6: every Node script that sends or publishes stories applies the site's source rule (red line 2)", () => {
  const writers = ["topics.cjs", "izle.cjs", "arxiv.cjs", "social.cjs", "prerender.cjs"];
  for (const f of writers) assert.ok(/policyViolation|content-policy/.test(read(".github/scripts/" + f)), `${f} mənbə qaydasını (policyViolation) işlətmir`);
  const known = new Set([...writers, "indexnow.cjs", "milli.cjs", "serve.cjs", "speed.cjs"]);
  const all = fs.readdirSync(path.join(root, ".github/scripts")).filter(f => f.endsWith(".cjs"));
  assert.deepEqual(all.filter(f => !known.has(f)), [], "yeni Node skripti: xəbər yazırsa policyViolation işlətsin və bu siyahıya əlavə olunsun");
});

test("struktur 7: the live-site speed check also runs in the busy part of the day (data grows, code does not change)", () => {
  const wf = read(".github/workflows/speed.yml");
  const cron = (wf.match(/cron: "([^"]+)"/) || [])[1] || "";
  const hours = cron.split(" ")[1].split(",").map(Number);
  assert.ok(hours.length >= 4 && hours.some(h => h >= 8 && h <= 14), "sürət ölçüsü gün ərzində (lent ən böyük olanda) da işləsin: " + cron);
});
