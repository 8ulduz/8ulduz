// Saranın oxunuş lüğəti (.github/scripts/ses-lugat.cjs): adaylar, Gemini cavabının yoxlanması, paketlərlə qurulma.
"use strict";
const test = require("node:test");
const assert = require("node:assert/strict");
const L = require("../.github/scripts/ses-lugat.cjs");

const TEXTS = [
  "ABŞ-nin dövlət katibi və FHN əməkdaşları Xankəndidə görüşüb. Bloomberg yazır ki, Google yeni məhsul təqdim edib.",
  "VİDEO: Bakıda qəza oldu. XII turda «Celta Vigo» uduzdu. Bu gün video yayıldı, bu səbəbdən Bakı küləkli olacaq.",
  "Din və dövlət münasibətləri, din xadimləri. ABŞ-da seçki. Sacramento Kings komandası.",
];

test("ses-lugat: adaylar — qısaltma və heç vaxt kiçik yazılmayan ad; adi söz, rum rəqəmi, böyük yazılmış söz yox", () => {
  const c = L.candidates(TEXTS).map(x => x.t);
  // Xüsusi adlar (Bakı, Xankəndidə) da namizəddir: Gemini «dəyişmir» deyir, yoxlanmış siyahıya düşür, növbəti dəfə soruşulmur.
  for (const t of ["ABŞ", "FHN", "Bloomberg", "Google", "Celta", "Vigo", "Sacramento", "Kings", "Xankəndidə", "Bakı"]) assert.ok(c.includes(t), t);
  for (const t of ["VİDEO", "XII", "Din", "Bu"]) assert.ok(!c.includes(t), t);
  const abs = L.candidates(TEXTS).find(x => x.t === "ABŞ");
  assert.equal(abs.n, 2);
  assert.match(abs.k, /ABŞ-nin dövlət katibi/);
  assert.deepEqual(L.candidates(TEXTS, new Set(["ABŞ", "Google"])).filter(x => ["ABŞ", "Google"].includes(x.t)), []);
});

test("ses-lugat: Gemini cavabı yoxlanır — yalnız Azərbaycan hərfləri, Azərbaycan adı dəyişdirilmir", () => {
  assert.equal(L.yoxla("ABŞ", "a-be-şe"), "a-be-şe");
  assert.equal(L.yoxla("FHN", " Fe - he - en "), "fe-he-en");
  assert.equal(L.yoxla("Washington", "vaşinqton"), "vaşinqton");
  assert.equal(L.yoxla("NATO", "nato"), "");               // qayda onsuz da belə oxuyur
  assert.equal(L.yoxla("Xankəndidə", ""), "");
  assert.equal(L.yoxla("Sacramento", "sakramento"), "sakramento");   // Azərbaycan yazılışlı, 1 hərf fərq
  assert.equal(L.yoxla("Xankəndi", "stepanakert"), null);  // Azərbaycan adı «düzəldilmir»
  assert.equal(L.yoxla("Google", "Gooqle!"), null);
  assert.equal(L.yoxla("BMT", "birləşmiş millətlər təşkilatı ".repeat(3)), null);
  assert.equal(L.yoxla("Google", 5), null);
});

test("ses-lugat: paketlərlə qurulur; cavabsız söz yoxlanmış sayılmır, rədd ayrıca", async () => {
  const cands = L.candidates(TEXTS);
  const answers = { ABŞ: "a-be-şe", FHN: "fe-he-en", Google: "qugl", Bloomberg: "blumberq", Xankəndidə: "", Celta: "selta", Kings: "kinqs", Vigo: "", Sacramento: "sakramento!" };
  const asked = [];
  const gemini = async (prompt) => { asked.push(prompt); return JSON.stringify(answers); };
  const r = await L.build(cands, { key: "x", gemini, log: () => {} });
  assert.equal(asked.length, 1);
  assert.match(asked[0], /a-be-şe/);
  assert.deepEqual(r.sozler, { ABŞ: "a-be-şe", FHN: "fe-he-en", Google: "qugl", Bloomberg: "blumberq", Celta: "selta", Kings: "kinqs" });
  assert.ok(r.yoxlanib.includes("Xankəndidə") && r.yoxlanib.includes("Vigo"));
  assert.ok(!r.yoxlanib.includes("Sacramento"));
  assert.deepEqual(r.redd.map(x => x.t), ["Sacramento"]);
  const none = await L.build(cands, { key: "x", gemini: async () => null, log: () => {} });
  assert.deepEqual(none, { sozler: {}, yoxlanib: [], redd: [] });
});

test("ses-lugat: repodakı lüğət az_text-in əlifbası ilə yazılıb", () => {
  const lex = require("../.github/ses-server/ses-lugat.json");
  for (const [k, v] of Object.entries(lex.sozler)) assert.match(v, /^[abcçdeəfgğhxıijkqlmnoöprsştuüvyz -]+$/, k);
});
