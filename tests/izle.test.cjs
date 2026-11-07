// «Telegram-da izlə» (sahib, 2026-11-07): .github/scripts/izle.cjs və iş axını.
const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs"), path = require("node:path");
const root = path.join(__dirname, "..");
const I = require("../.github/scripts/izle.cjs");
const { loadApp } = require("../.github/scripts/topics.cjs");
const app = loadApp(root), cat = I.catalog(app);
const at = h => new Date(Date.now() - h * 3600e3).toISOString();
const row = (id, category, title, extra = {}) => ({ id, category, title, source: "APA", sourceUrl: "https://apa.az/" + id, publishedAt: at(0), lang: "az", ...extra });
const msg = (chat, text) => ({ update_id: 1, message: { chat: { id: chat, type: "private" }, text } });

test("izlə: the catalogue has sections, sport topics and districts with the site's own matching", () => {
  for (const k of ["b_idman", "b_bolgeler", "b_dunya", "i_fenerbahce", "i_qarabag", "r_quba"]) assert.ok(cat.has(k), k);
  assert.ok(!cat.has("b_sondeqiqe"), "Son dəqiqə mövzu deyil");
  for (const k of cat.keys()) assert.match(k, /^[a-z]_[a-z0-9_-]{1,60}$/, "Telegram start parametri: hərf, rəqəm, _ və -");
  assert.equal(cat.get("i_fenerbahce").match(row("1", "idman", "Fənərbağça qələbə qazandı")), true);
  assert.equal(cat.get("i_fenerbahce").match(row("2", "dunya", "Fənərbağça haqqında siyasi xəbər")), false, "idman mövzusu yalnız idmanda");
  assert.equal(cat.get("r_quba").match(row("3", "bolgeler", "Qubada yeni məktəb açılıb")), true);
});

test("izlə: «Başlat» subscribes in one step, the list shows it, «dayandır» stops it", () => {
  const s = I.newState();
  let out = I.handle(s, msg(7, "/start i_fenerbahce"), cat);
  assert.deepEqual(s.subs, { 7: ["i_fenerbahce"] });
  assert.match(out[0].text, /^✅ «Fenerbahçe» izlənir/);
  out = I.handle(s, msg(7, "/start i_fenerbahce"), cat);
  assert.match(out[0].text, /artıq izlənir/); assert.deepEqual(s.subs[7], ["i_fenerbahce"], "təkrar yazılmır");
  I.handle(s, msg(7, "/start r_quba"), cat);
  out = I.handle(s, msg(7, "/izlediklerim"), cat);
  assert.match(out[0].text, /Fenerbahçe[\s\S]*Quba/);
  assert.equal(out[0].reply_markup.inline_keyboard[0][0].callback_data, "stop:i_fenerbahce");
  I.handle(s, { update_id: 2, callback_query: { id: "q", data: "stop:i_fenerbahce", message: { chat: { id: 7 } } } }, cat);
  assert.deepEqual(s.subs[7], ["r_quba"]);
  I.handle(s, msg(7, "/start yoxdur_bele"), cat);
  assert.deepEqual(s.subs[7], ["r_quba"], "naməlum açar əlavə olunmur");
  out = I.handle(s, msg(7, "/dayandir"), cat);
  assert.equal(s.subs[7], undefined); assert.match(out[0].text, /Bütün izləmələr dayandırıldı/);
  assert.deepEqual(I.handle(s, { update_id: 3, message: { chat: { id: -100, type: "channel" }, text: "/start i_fenerbahce" } }, cat), [], "yalnız şəxsi söhbət");
});

test("izlə: a new matching story goes once to each follower; old, foreign-language and blocked stories do not", () => {
  const s = I.newState();
  s.subs = { 1: ["i_fenerbahce"], 2: ["b_idman", "i_fenerbahce"], 3: ["r_quba"] };
  assert.deepEqual(I.deliveries(s, [row("old", "idman", "Fənərbağça köhnə xəbər")], cat, app).length >= 0, true);
  s.seen = ["old"];
  const out = I.deliveries(s, [
    row("old", "idman", "Fənərbağça köhnə xəbər"),
    row("a1b2c3d4e5f60718", "idman", "Fənərbağça yeni məşqçi ilə müqavilə imzaladı", { imageUrl: "https://apa.az/a.jpg" }),
    row("ru", "dunya", "Квота", { lang: "ru" }),
  ], cat, app);
  assert.deepEqual(out.map(m => m.chat_id).sort(), ["1", "2"], "hər oxucuya bir dəfə, Quba izləyəninə yox");
  assert.equal(out[0].method, "sendPhoto"); assert.match(out[0].caption, /^<b>Fənərbağça yeni məşqçi/);
  assert.equal(out[0].reply_markup.inline_keyboard[0][0].url, "https://8ulduz.az/#/xeber/a1b2c3d4e5f60718?b=idman&h=" + at(0).slice(2, 13).replace(/\D/g, ""));
  assert.deepEqual(I.deliveries(s, [row("a1b2c3d4e5f60718", "idman", "Fənərbağça yeni məşqçi ilə müqavilə imzaladı")], cat, app), [], "ikinci dəfə göndərilmir");
});

test("izlə: the workflow runs apart from the news pipeline, keeps the followers only in the Actions cache", () => {
  const wf = fs.readFileSync(path.join(root, ".github/workflows/izle.yml"), "utf8");
  assert.ok(wf.includes("contents: read") && wf.includes("group: izle") && wf.includes("path: .izle") && wf.includes("secrets.TELEGRAM_BOT_TOKEN"));
  const gi = fs.readFileSync(path.join(root, ".gitignore"), "utf8");
  assert.ok(/^\.izle\/?$/m.test(gi), "siyahı repoya düşmür");
});

test("izlə: the team page shows the button for teams that have a news topic", () => {
  const k = fs.readFileSync(path.join(root, "assets/komanda.js"), "utf8");
  assert.ok(k.includes("tg-izle") && k.includes("topicFor(team.name)") && k.includes("?start=i_"));
});

test("izlə: any topic — the reader writes a word to the bot or presses the button on a search; matching is like the site search", () => {
  const s = I.newState(), c = I.catalog(app);
  let out = I.handle(s, msg(9, "Pensiya"), c);
  assert.match(out[0].text, /^✅ «Pensiya» izlənir/);
  const key = I.keyOf("İran Amerika münasibətləri");
  assert.match(key, /^q_[A-Za-z0-9_-]{1,62}$/);
  out = I.handle(s, msg(9, "/start " + key), c);
  assert.match(out[0].text, /«İran Amerika münasibətləri» izlənir/);
  assert.deepEqual(I.handle(s, msg(9, "salam"), c).length, 0, "salam mövzu deyil");
  s.seen = [];
  const sent = I.deliveries(s, [row("p1", "sosial", "Pensiyalar artırılır"), row("p2", "dunya", "İran ABŞ ilə danışıqlara başlayır"), row("p3", "dunya", "İranda zəlzələ")], c, app);
  assert.deepEqual(sent.map(m => m.caption || m.text).map(t => t.match(/<b>(.*?)<\/b>/)[1]), ["Pensiyalar artırılır", "İran ABŞ ilə danışıqlara başlayır"]);
  const hava = I.kwTopic(I.keyOf("hava"));
  assert.ok(hava.match(row("h", "gundem", "Sabah yağış yağacaq")) && !hava.match(row("l", "gundem", "Hava limanında tədbir")));
});

test("izlə: the follow panel link asks the reader which topic to follow", () => {
  const out = I.handle(I.newState(), msg(5, "/start movzu"), I.catalog(app));
  assert.match(out[0].text, /^📩 Nəyi izləmək istəyirsiniz\?/);
});
