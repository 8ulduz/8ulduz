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
  assert.ok(js.includes('<button type="button" class="share" data-act="dinle" data-id="${esc(a.id)}">${S.dinOn === a.id ? "■ Bitir" : "Dinlə"}</button><button type="button" class="share" data-act="share"'), "hər kartda «Paylaş»ın yanında «Dinlə»; oxunanda «■ Bitir» (sahib, 2026-11-07/08)");
  assert.ok(js.includes('onState: s => { S.dinOn = s.playing && s.id;'), "ayrıca pəncərə yoxdur: vəziyyət düymənin özündədir");
  assert.ok(!/\.dinle\{position:fixed/.test(fs.readFileSync(path.join(root, "assets/dinle.js"), "utf8")), "səs pəncərəsi yoxdur");
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
const flush = async (n = 10) => { for (let k = 0; k < n; k++) await new Promise(r => setImmediate(r)); };
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

test("dinlə: pressing «Dinlə» again on the story that is playing stops it (sahib, 2026-11-07)", async () => {
  const js = fs.readFileSync(path.join(root, "assets/app.js"), "utf8");
  assert.ok(js.includes(".then(p => p.playing && p.id === a?.id ? p.stop() : p.play(a))"), "ikinci basış dayandırır");
  const { createPlayer } = await load();
  const env = fakeEnv(true), p = createPlayer({ list: () => list, ...env });
  await p.play(list[0]);
  assert.equal(p.id, list[0].id); assert.equal(p.playing, true);
  p.stop();
  assert.equal(p.playing, false); assert.equal(p.id, undefined);
});

test("dinlə: pressing «Dinlə» on a slider card stops the slider (sahib, 2026-11-07)", () => {
  const js = fs.readFileSync(path.join(root, "assets/app.js"), "utf8");
  assert.ok(js.includes(`t.closest(".hero-strip")?.querySelector('.hero-pause[aria-pressed="false"]')?.click();`));
});

test("dinlə: the player reports its state to the button (playing at once, stopped after «Bitir»), no window of its own", async () => {
  const { createPlayer } = await load();
  const env = fakeEnv(true), states = [], p = createPlayer({ list: () => list, ...env, onState: s => states.push({ ...s }) });
  const started = p.play(list[0]);
  assert.deepEqual(states[0], { id: list[0].id, playing: true, msg: undefined }, "düymə dərhal «■ Bitir» olur");
  await started;
  p.stop();
  assert.equal(states.at(-1).playing, false);
  assert.equal(env.doc.body.children.length, 0, "səhifəyə pəncərə əlavə olunmur");
});

test("dinlə: while the voice is being prepared the button keeps «Səs hazırlanır…» (owner: it went back to «Dinlə»); a computer with an Azerbaijani voice reads at once", async t => {
  const { createPlayer } = await load();
  const js = fs.readFileSync(path.join(root, "assets/app.js"), "utf8");
  assert.ok(js.includes("if (s.msg && !s.playing) setTimeout("), "yalnız bitmiş vəziyyətin yazısı 3 saniyədən sonra «Dinlə» olur");
  t.mock.timers.enable({ apis: ["setTimeout"] });
  const story = { ...list[0], title: "Klub prezidenti", source: "Sportinfo", sourceUrl: "https://www.sportinfo.az/1.html" };
  const env = fakeEnv(false), states = [];
  const p = createPlayer({ list: () => list, ...env, server: "https://dinle.example/ses", onState: s => states.push({ ...s }) });
  await p.play(story);
  env.els[0].onerror(); await flush();
  assert.deepEqual([states.at(-1).msg, states.at(-1).playing], ["Səs hazırlanır…", true]);
  t.mock.timers.tick(1e4); await flush();
  assert.equal(env.played.filter(s => s.startsWith("https://dinle.example/")).length, 2, "10 saniyə sonra yenidən soruşur");
  assert.deepEqual([states.at(-1).msg, states.at(-1).playing], ["Səs hazırlanır…", true], "yenidən soruşanda da yazı qalır");
  assert.equal(env.spoken.length, 0, "türk səsi ilə tələsik oxumur, Babəki gözləyir");
  p.stop();
  const env2 = fakeEnv(false);
  env2.synth.getVoices = () => [{ name: "Microsoft Babek Online (Natural) - Azerbaijani (Azerbaijan)", lang: "az-AZ", localService: false }];
  const p2 = createPlayer({ list: () => list, ...env2, server: "https://dinle.example/ses" });
  await p2.play(story);
  env2.els[0].onerror(); await flush(30);
  assert.equal(p2.mode, "tts", "kompüterdə (Edge) Babək cihazda var: gözləmədən oxuyur");
  assert.ok(env2.spoken[0].text.startsWith("Klub prezidenti"));
  p2.stop();
});

test("dinlə: without a prepared voice the full text comes from the text server and the device voice reads it at once", async () => {
  const { createPlayer } = await load();
  const env = fakeEnv(false), long = "Napoli klubunun prezidenti baş məşqçi ilə görüşüb və komandanın vəziyyətini müzakirə edib. ".repeat(4);
  const base = env.fetchFn, asked = [];
  env.fetchFn = async (url, o) => url.startsWith("https://dinle.example/") ? (asked.push(url), { ok: true, json: async () => ({ text: long }) }) : base(url, o);
  const p = createPlayer({ list: () => list, ...env, worker: "https://dinle.example/" });
  await p.play({ ...list[0], title: "Klub prezidenti", source: "Sportinfo", sourceUrl: "https://www.sportinfo.az/1.html" });
  assert.deepEqual(asked, ["https://dinle.example/?u=" + encodeURIComponent("https://www.sportinfo.az/1.html")]);
  assert.equal(p.mode, "tts");
  for (let k = 0; k < 50 && env.spoken.at(-1)?.onend; k++) { const u = env.spoken.at(-1), n = env.spoken.length; u.onend(); if (env.spoken.length === n) break; }  // hər hissə bitir, növbəti başlayır
  const said = env.spoken.map(u => u.text).join(" ");
  assert.ok(said.startsWith("Klub prezidenti."), said.slice(0, 80));
  assert.ok(said.includes("Napoli"), "tam mətn oxunur, yalnız başlıq yox");
  p.stop();
});

test("dinlə: with the «dinle» server the story streams at once (prepared voice or Azure Babək); not ready → «Səs hazırlanır…» and a retry", async () => {
  const { createPlayer } = await load();
  const env = fakeEnv(true), states = [], story = { ...list[0], title: "Klub prezidenti", source: "Sportinfo", sourceUrl: "https://www.sportinfo.az/1.html" };
  const p = createPlayer({ list: () => list, ...env, server: "https://dinle.example/ses", onState: s => states.push({ ...s }) });
  await p.play(story);
  const src = "https://dinle.example/ses?u=" + encodeURIComponent(story.sourceUrl) + "&id=" + story.id + "&t=" + encodeURIComponent("Klub prezidenti") + "&s=Sportinfo";
  assert.ok(env.played.includes(src), env.played.join(" | "));
  assert.equal(env.fetched.length, 0, "əlavə sorğu yoxdur: səs dərhal serverdən");
  assert.equal(p.mode, "file");
  env.els[0].onerror(); await flush();   // server: hələ hazır deyil (503)
  assert.equal(states.at(-1).msg, "Səs hazırlanır…");
  assert.equal(p.playing, true, "gözləyir, ikinci basış bitirir");
  p.stop();
});
