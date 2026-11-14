// Namaz və hava səhifələri (updater.py write_subpages): şəhər siyahısı və hava adları saytdakı vidcetlə eyni qalmalıdır,
// yoxsa /bolme/namaz/<şəhər>/ səhifəsi ilə başlıqdakı göstərici fərqli vaxt göstərər.
const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("fs"), path = require("path");
const root = path.join(__dirname, "..");
const app = fs.readFileSync(path.join(root, "assets/app.js"), "utf8");
const py = fs.readFileSync(path.join(root, "updater.py"), "utf8");

test("xidmət səhifələri: updater.py CITIES = app.js CITIES", () => {
  const js = JSON.parse(app.match(/^const CITIES = (\[\[.*\]\]);$/m)[1]);
  const block = py.slice(py.indexOf("\nCITIES = ["), py.indexOf("\nNAMAZ_FILE = "));
  const rows = [...block.matchAll(/\("([^"]+)", ([\d.]+), ([\d.]+)\)/g)].map(m => [m[1], Number(m[2]), Number(m[3])]);
  assert.deepEqual(rows, js);
});

test("xidmət səhifələri: namaz üsulu və vaxt adları vidcetlə eynidir", () => {
  assert.match(app, /api\.aladhan\.com\/v1\/timings\/\$\{day\}\?latitude=\$\{c\[1\]\}&longitude=\$\{c\[2\]\}&method=13/);
  assert.match(py, /api\.aladhan\.com\/v1\/calendar\/\{year\}\/\{mon\}\?latitude=\{lat\}&longitude=\{lon\}&method=13/);
  const js = JSON.parse(app.match(/^const PRAY_ORDER = (\[\[.*\]\]);$/m)[1]);
  const pyRows = [...py.match(/^PRAY_LABELS = \((.*)\)$/m)[1].matchAll(/\("(\w+)", "([^"]+)"\)/g)].map(m => [m[1], m[2]]);
  assert.deepEqual(pyRows, js);
});

test("xidmət səhifələri: hava adları wxCode ilə eynidir", () => {
  const names = [...app.slice(app.indexOf("function wxCode(c)"), app.indexOf("async function weather(")).matchAll(/\["([^"]+)", "/g)].map(m => m[1]);
  const block = py.slice(py.indexOf("def wx_label(code):"), py.indexOf("def _deg(v):"));
  for (const n of names) assert.ok(block.includes(`"${n}"`), n);
});

test("xidmət səhifələri: tətbiqdəki keçidlər updater.city_slug ilə eyni ünvana aparır", () => {
  const citySlug = new Function(app.match(/^function citySlug\(n\) \{.*\}$/m)[0] + "; return citySlug;")();
  const cities = JSON.parse(app.match(/^const CITIES = (\[\[.*\]\]);$/m)[1]).map(c => c[0]);
  const slugs = cities.map(citySlug);
  assert.equal(new Set(slugs).size, cities.length);
  for (const s of slugs) assert.match(s, /^[a-z]+$/);
  // tests/test_xidmet_sehifeleri.py test_slugs_and_locative eyni nümunələri yoxlayır
  assert.deepEqual(["Bakı", "İsmayıllı", "Şəki", "Göyçay", "Ağdaş", "Ucar"].map(citySlug), ["baki", "ismayilli", "seki", "goycay", "agdas", "ucar"]);
  for (const part of ["popMore(`namaz/${citySlug(city)}/`", "popMore(`hava/${citySlug(sel.city)}/`", 'popMore("hava/"', '<a href="/bolme/namaz/">', '<a href="/bolme/mezenne/dollar/">']) assert.ok(app.includes(part), part);
});

test("xidmət səhifələri: alt səhifə keçidi bölmə sayılmır (arxiv əvvəlcədən istənmir)", () => {
  const hashOf = new Function("return " + app.match(/^const hashOf = (.*?); \/\//m)[1])();
  const a = href => ({ getAttribute: () => href });
  assert.equal(hashOf(a("/bolme/idman/")), "#/bolme/idman");
  assert.equal(hashOf(a("/bolme/valyuta/")), "#/bolme/valyuta");
  for (const href of ["/bolme/namaz/", "/bolme/namaz/baki/", "/bolme/hava/gence/", "/bolme/mezenne/dollar/"]) assert.equal(hashOf(a(href)), href);
});

test("xidmət səhifələri: klik tutucusu alt səhifəni tətbiqin bölməsinə çevirmir («Bölmə tapılmadı» çıxırdı)", () => {
  const end = app.indexOf('/.exec(a.getAttribute("href"))'), start = app.lastIndexOf("const m = /", end);
  assert.ok(start > 0 && end > start);
  const rx = new RegExp(app.slice(start + "const m = /".length, end));
  assert.equal(rx.exec("/bolme/idman/")[1], "bolme/idman");
  assert.equal(rx.exec("/xeber/0123456789abcdef/")[1], "xeber/0123456789abcdef");
  for (const href of ["/bolme/namaz/", "/bolme/namaz/baki/", "/bolme/hava/", "/bolme/hava/ismayilli/", "/bolme/mezenne/dollar/"]) assert.equal(rx.exec(href), null, href);
});
