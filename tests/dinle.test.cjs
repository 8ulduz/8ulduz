// «Dinlə» (sahib, 2026-11-07: «dinlə funksiyasını mükəmməl şəkildə işə sal»; Edge-dəki təbii Azərbaycan səsi bəyənilib).
const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs"), path = require("node:path"), { pathToFileURL } = require("node:url");
const root = path.join(__dirname, "..");
const load = () => import(pathToFileURL(path.join(root, "assets/dinle.js")).href);

test("dinlə: reads the title and the site's own summary, never the publisher's full text", async () => {
  const { textOf } = await load();
  assert.equal(textOf({ title: "Bakıda yağış", summary: "<p>Sabah  güclü yağış gözlənilir.</p>" }), "Bakıda yağış. Sabah güclü yağış gözlənilir.");
  assert.equal(textOf({ title: "Başlıq!", summary: "" }), "Başlıq.");
  assert.equal(textOf({ title: "Eyni", summary: "Eyni mətn davam edir" }), "Eyni.", "xülasə başlığı təkrarlayırsa yalnız başlıq");
  const js = fs.readFileSync(path.join(root, "assets/dinle.js"), "utf8");
  assert.ok(!/reader\.json|fetch\(/.test(js), "mənbənin tam mətni yüklənmir");
});

test("dinlə: long text is split for browsers that cut long utterances", async () => {
  const { chunks } = await load();
  const parts = chunks("Bir. " + "söz ".repeat(120) + "son.", 200);
  assert.ok(parts.length > 2 && parts.every(p => p.length <= 200));
  assert.equal(parts[0], "Bir.");
});

test("dinlə: the natural Azerbaijani voice (Edge) comes first, then any Azerbaijani, then Turkish; none → a clear message", async () => {
  const { pickVoice } = await load();
  const v = (name, lang, localService = true) => ({ name, lang, localService });
  const voices = [v("Microsoft Ahmet Online (Natural) - Turkish", "tr-TR", false), v("Some az", "az-AZ"), v("Microsoft Banu Online (Natural) - Azerbaijani (Azerbaijan)", "az-AZ", false), v("English", "en-US")];
  assert.equal(pickVoice(voices).voice.name, "Microsoft Banu Online (Natural) - Azerbaijani (Azerbaijan)");
  assert.equal(pickVoice(voices).lang, "az-AZ");
  const tr = pickVoice([v("English", "en-US"), v("Google Türkçe", "tr-TR")]);
  assert.equal(tr.voice.name, "Google Türkçe"); assert.equal(tr.az, false);
  assert.equal(pickVoice([v("English", "en-US")]), null);
});

test("dinlə: the site loads the module only when «🔊 Dinlə» is pressed (speed red line)", () => {
  const js = fs.readFileSync(path.join(root, "assets/app.js"), "utf8");
  assert.ok(js.includes(`globalThis.speechSynthesis ? '<button type="button" class="pill tg-izle" data-act="dinle">🔊 Dinlə</button>' : ""`), "düymə yalnız səsli oxuma olan brauzerdə");
  assert.ok(js.includes('(S.dinle ||= import(`${ASSET}dinle.js`)'), "modul yalnız basılanda");
  assert.ok(!/<script[^>]+dinle\.js|modulepreload[^>]+dinle/.test(fs.readFileSync(path.join(root, "index.html"), "utf8")), "ilk açılışda yüklənmir");
});
