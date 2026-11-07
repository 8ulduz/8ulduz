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

test("dinlə: every card has «Dinlə» next to «Paylaş»; the module loads only when pressed (speed red line)", () => {
  const js = fs.readFileSync(path.join(root, "assets/app.js"), "utf8");
  assert.ok(js.includes('<button type="button" class="share" data-act="dinle" data-id="${esc(a.id)}">Dinlə</button><button type="button" class="share" data-act="share"'), "hər kartda «Paylaş»ın yanında «Dinlə» (sahib, 2026-11-07)");
  assert.ok(js.includes('(S.dinle ||= import(`${ASSET}dinle.js`)'), "modul yalnız basılanda");
  assert.ok(!/<script[^>]+dinle\.js|modulepreload[^>]+dinle/.test(fs.readFileSync(path.join(root, "index.html"), "utf8")), "ilk açılışda yüklənmir");
});

test("dinlə: the Turkish fallback voice gets ə/x/q as the nearest Turkish sounds", async () => {
  const { forTurkish } = await load();
  assert.equal(forTurkish("Əliyev xalqa qəzet"), "Eliyev halga gezet");
});

// Saxta brauzer: hazır mp3 varsa o çalır (hər telefonda eyni təbii səs), yoxdursa cihazın səsi; növbəti xəbərinki əvvəlcədən götürülür.
function fakeEnv(hasFile) {
  const el = () => ({ tag: "", children: [], dataset: {}, style: {}, textContent: "", setAttribute() {}, append(c) { this.children.push(c); }, remove() {}, addEventListener() {},
    querySelector(sel) { return (this._q ||= {})[sel] ||= el(); }, set innerHTML(v) {}, get innerHTML() { return ""; } });
  const doc = { head: el(), body: el(), getElementById: () => null, createElement: el };
  const fetched = [], played = [], spoken = [], els = [];
  const fetchFn = async url => {
    fetched.push(url.split("?")[0]);
    if (url.includes("index.json")) return { ok: true, json: async () => ({ ids: hasFile ? ["aaaaaaaaaaaaaaaa", "cccccccccccccccc"] : [] }) };
    return { ok: true, arrayBuffer: async () => new ArrayBuffer(8) };
  };
  class AudioCtor { constructor() { this.src = ""; els.push(this); } get currentSrc() { return this.src; } play() { played.push(this.src); return Promise.resolve(); } pause() {} }
  const synth = { getVoices: () => [{ name: "Google Türkçe", lang: "tr-TR", localService: true }], speak: u => spoken.push(u), cancel() {}, pause() {}, resume() {} };
  class Utterance { constructor(t) { this.text = t; } }
  return { doc, fetchFn, AudioCtor, synth, Utterance, fetched, played, spoken, els, nav: {}, store: { getItem: () => null, setItem() {} } };
}
const list = [{ id: "aaaaaaaaaaaaaaaa", title: "Xəbər bir", lang: "az" }, { id: "bbbbbbbbbbbbbbbb", title: "Xəbər iki", lang: "az" }, { id: "cccccccccccccccc", title: "Xəbər üç", lang: "az" }];

test("dinlə: the full-story natural-voice file plays first; «next» goes to the next story that has one, fetched ahead", async () => {
  const { createPlayer, AUDIO } = await load();
  const env = fakeEnv(true), p = createPlayer({ list: () => list, ...env });
  await p.play(list[0]);
  assert.equal(p.mode, "file");
  assert.ok(env.played.some(s => s.startsWith("blob:")), "hazır səs faylı çalınır");
  assert.equal(env.spoken.length, 0, "cihaz səsi işə düşmür");
  assert.deepEqual(env.fetched, [AUDIO + "index.json", AUDIO + "aaaaaaaaaaaaaaaa.mp3", AUDIO + "cccccccccccccccc.mp3"], "səssiz «iki» atlanır");
  assert.equal(AUDIO, "https://raw.githubusercontent.com/8ulduz/ses/main/", "səslər sayt reposunda yox, ayrıca reposdadır");
  assert.ok(env.played[0].startsWith("data:audio/wav"), "toxunuş anında element açılır (iPhone)");
  const el = env.els[0], playing = el.src, n = env.played.length;
  el.src = "data:audio/wav;x"; el.onended(); el.src = playing; await new Promise(r => setTimeout(r, 10));  // gecikən səssiz klip hadisəsi xəbəri bitirmir
  assert.equal(env.played.length, n, "növbəti xəbərə keçilmədi");
  el.onended(); await new Promise(r => setTimeout(r, 10));
  assert.ok(env.played.length > n, "faylın özü bitəndə növbəti xəbər başlayır");
  p.stop();
});

test("dinlə: without a prepared file the device voice reads, Turkish voice with converted letters", async () => {
  const { createPlayer } = await load();
  const env = fakeEnv(false), p = createPlayer({ list: () => list, ...env });
  await p.play(list[0]);
  assert.equal(p.mode, "tts");
  assert.ok(!env.fetched.some(u => u.endsWith(".mp3")), "siyahıda olmayan xəbər üçün mp3 istənmir");
  assert.equal(env.spoken[0].text, "Hebər bir.".replace("ə", "e"));
  assert.equal(env.spoken[0].lang, "tr-TR");
  p.stop();
});
