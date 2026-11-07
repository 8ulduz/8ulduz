// Xəbər səsləri (.github/scripts/ses.cjs): hansı xəbərin səslənəcəyi, pulsuz limit, sirr yoxdursa heç nə etməmək.
const test = require("node:test");
const assert = require("node:assert/strict");
const ses = require("../.github/scripts/ses.cjs");

test("ses: Azerbaijani stories of the last 30 hours, most sources first; already voiced and foreign ones skipped", () => {
  const now = Date.parse("2026-11-07T12:00:00Z"), at = h => new Date(now - h * 3600e3).toISOString();
  const rows = [
    { id: "a".repeat(16), title: "Bir", lang: "az", publishedAt: at(1) },
    { id: "b".repeat(16), title: "İki", lang: "az", publishedAt: at(2), alts: [{}, {}] },
    { id: "c".repeat(16), title: "Üç", lang: "ru", publishedAt: at(1) },
    { id: "d".repeat(16), title: "Köhnə", lang: "az", publishedAt: at(40) },
    { id: "e".repeat(16), title: "Var", lang: "az", publishedAt: at(1) },
    { id: "f".repeat(16), title: "Qadağan", lang: "az", publishedAt: at(1) },
  ];
  const ids = ses.pick(rows, new Set(["e".repeat(16)]), now, a => a.title !== "Qadağan").map(a => a.title);
  assert.deepEqual(ids, ["İki", "Bir"]);
});

test("ses: the free Azure allowance is never exceeded (day and month ceilings)", () => {
  const now = Date.parse("2026-11-07T12:00:00Z");
  assert.ok(ses.MONTH_CHARS <= 500000 && ses.DAY_CHARS * 31 <= 500000, "pulsuz limit ayda 500 000 simvoldur");
  assert.equal(ses.budget({}, now).left, ses.DAY_CHARS);
  assert.equal(ses.budget({ "2026-11-07": ses.DAY_CHARS }, now).left, 0);
  assert.equal(ses.budget({ "2026-11": ses.MONTH_CHARS - 10 }, now).left, 10);
});

test("ses: text is XML-escaped for the speech request", () => {
  assert.ok(ses.ssml('A & B <c> "d"').includes("A &amp; B &lt;c&gt; &quot;d&quot;"));
  assert.ok(ses.ssml("x").includes('voice name="az-AZ-BabekNeural"'));
});

test("ses: without the Azure key nothing is fetched or written", async () => {
  const old = global.fetch; let calls = 0; global.fetch = async () => { calls++; return { ok: false }; };
  try { await ses.main(".", ".nope", {}); } finally { global.fetch = old; }
  assert.equal(calls, 0);
});
