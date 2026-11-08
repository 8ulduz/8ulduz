// Bayram təbriki (sahib, 2026-11-07: «8 noyabr Zəfər Günü 00:00-dan sonra saytı açanda təbrik banneri açılsın»).
const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs"), path = require("node:path");
const root = path.join(__dirname, "..");

test("bayram: the greeting loads only on 8 and 9 November in Baku time, after the first screen, as a separate small module", () => {
  const js = fs.readFileSync(path.join(root, "assets/app.js"), "utf8");
  assert.ok(js.includes('const d = new Date(Date.now() + 144e5).toISOString().slice(5, 10); if (/^11-0[89]$/.test(d)'), "Bakı vaxtı (UTC+4) ilə 8 və 9 noyabr");
  assert.ok(js.includes('import(`${ASSET}bayram.js`).then(m => m.show(d === "11-08" ? d : "11-09"))'), "adi gündə modul yüklənmir");
  const day = ms => new Date(ms + 144e5).toISOString().slice(5, 10);
  assert.equal(day(Date.UTC(2026, 10, 7, 20, 0, 0)), "11-08", "7 noyabr 20:00 UTC = 8 noyabr 00:00 Bakı");
  assert.equal(day(Date.UTC(2026, 10, 7, 19, 59, 59)), "11-07");
  assert.equal(day(Date.UTC(2026, 10, 8, 20, 0, 0)), "11-09", "9 noyabr 00:00 Bakı: Bayraq Günü başlayır");
  assert.equal(day(Date.UTC(2026, 10, 9, 20, 0, 0)), "11-10", "10 noyabr 00:00 Bakıda bitir");
});

test("bayram: the module shows the owner's banner image from assets, no outside address, and stays small (speed, red line 3)", () => {
  const b = fs.readFileSync(path.join(root, "assets/bayram.js"), "utf8");
  assert.ok(b.includes('"11-08"') && b.includes("8ULDUZ.AZ Azərbaycanın ZƏFƏR GÜNÜnü təbrik edir") && b.includes("Bağla"));
  assert.ok(b.includes('"11-09"') && b.includes("Dövlət Bayrağı Günü münasibətilə təbrik edir") && b.includes("bayram-bayraq.webp"), "9 noyabr Bayraq Günü");
  assert.ok(!/https?:\/\//.test(b.replace(/^\/\/.*$/gm, "")), "xarici ünvan yoxdur");
  assert.ok(b.length < 6000, "kiçik modul");
  for (const f of ["bayram-zefer.webp", "bayram-bayraq.webp"]) assert.ok(fs.statSync(path.join(root, "assets", f)).size < 120e3, f + " 120 KB-dan kiçik: yalnız bayram günü, ilk ekrandan sonra yüklənir");
});

test("bayram: the module loads (a syntax error would silently show nothing) and opens once per session", async () => {
  const m = await import(require("node:url").pathToFileURL(path.join(root, "assets/bayram.js")).href);
  const made = [], store = new Map();
  const el = () => ({ attrs: {}, setAttribute(k, v) { this.attrs[k] = v; }, addEventListener() {}, append() {}, remove() {}, querySelector: () => ({ focus() {} }) });
  const doc = { querySelector: () => null, getElementById: () => null, createElement: t => { const e = el(); made.push([t, e]); return e; }, head: { append() {} }, body: { append() {} }, addEventListener() {}, removeEventListener() {} };
  const st = { getItem: k => store.get(k) || null, setItem: (k, v) => store.set(k, v) };
  const box = m.show("11-08", doc, st);
  assert.ok(box && box.innerHTML.includes("bayram-zefer.webp") && box.innerHTML.includes('class="bayram-x"') && box.attrs.role === "dialog");
  assert.equal(box.attrs["aria-label"], "8ULDUZ.AZ Azərbaycanın ZƏFƏR GÜNÜnü təbrik edir!");
  assert.equal(m.show("11-08", doc, st), null, "sessiyada ikinci dəfə açılmır");
  assert.equal(m.show("01-01", doc, st), null, "başqa gün yoxdur");
  const flag = m.show("11-09", doc, st);
  assert.ok(flag && flag.innerHTML.includes("bayram-bayraq.webp") && flag.attrs["aria-label"].includes("Dövlət Bayrağı Günü"), "9 noyabr öz banneri ilə");
  assert.equal(m.show("11-09", doc, st), null, "o da sessiyada bir dəfə");
});
