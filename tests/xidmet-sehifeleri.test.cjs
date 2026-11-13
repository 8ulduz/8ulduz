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
