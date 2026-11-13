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
  assert.ok(k.includes("tg-izle") && k.includes("topicFor(team.name)") && k.includes('?start=${S.lang && S.lang !== "az" ? S.lang + "-" : ""}i_'), "komanda düyməsi saytın dilini də ötürür");
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

test("izlə: English, Russian and Turkish readers get the top 10 of the day in their own language at 09:00/19:00 Baku, once (owner 2026-11-08: «günün 10 əsas xəbəri … həmin dillər üzrə işləmir»)", () => {
  const s = I.newState();
  let out = I.handle(s, msg(9, "/start g_en"), cat);
  assert.deepEqual(s.subs[9], ["g_en"]); assert.match(out[0].text, /^✅ Done!.*in English/s);
  out = I.handle(s, msg(9, "/start g_en"), cat);
  assert.match(out[0].text, /already subscribed/); assert.deepEqual(s.subs[9], ["g_en"], "təkrar yazılmır");
  assert.match(I.handle(s, msg(10, "/start g_ru"), cat)[0].text, /^✅ Готово!/);
  assert.match(I.handle(s, msg(11, "/start g_tr"), cat)[0].text, /^✅ Tamam!/);
  const ed = I.dueEdition(Date.parse("2026-11-08T15:05:00Z"));
  assert.deepEqual([ed.slug, ed.end - ed.start], ["2026-11-08-axsam", 12 * 3600e3], "19:05 Bakı: axşam buraxılışı, son 12 saat");
  assert.equal(I.dueEdition(Date.parse("2026-11-08T20:30:00Z")).slug, "2026-11-08-axsam", "gecə 00:30: gecikmiş buraxılış hələ gedir");
  assert.equal(I.dueEdition(Date.parse("2026-11-08T12:00:00Z")), null, "16:00 Bakı: buraxılış yoxdur");
  assert.equal(I.dueEdition(Date.parse("2026-11-08T05:10:00Z")).slug, "2026-11-08-seher");
  const t = h => new Date(ed.end - h * 3600e3).toISOString();
  const titles = ["Earthquake shakes northern Japan coast", "Central bank raises interest rates again", "Football club signs young striker", "Wildfire forces evacuations in California",
    "Parliament approves new budget plan", "Scientists discover distant planet", "Oil prices climb after supply cuts", "Airline orders hundred new aircraft",
    "Election results announced in Brazil", "Storm causes flooding across Europe", "Tech company unveils folding phone", "Marathon record broken in Berlin"];
  const en = titles.map((title, i) => ({ id: (i + 1).toString(16).padStart(16, "0"), category: "dunya", lang: "en", title, summary: "", source: "Trend", sourceUrl: "https://trend.az/world/" + i, publishedAt: t(1 + i * 0.5), alts: i === 7 ? [{}, {}, {}] : [] }));
  en.push({ ...en[0], id: "dddddddddddddddd", title: "Earthquake shakes northern Japan coast, tsunami warning issued", alts: [{}, {}] });   // eyni hadisə, çox mənbə
  en.push({ ...en[1], id: "aaaaaaaaaaaaaaab", title: "Bakıda yeni park açılıb", lang: "az" }, { ...en[2], id: "bbbbbbbbbbbbbbbb", title: "Too old story", publishedAt: t(13) });
  const sent = I.digestMessages(s, "en", ed, en, app);
  assert.deepEqual(sent.map(m => m.chat_id), ["9"], "yalnız ingilis dilinə yazılmış oxucu");
  const text = sent[0].text, lines = text.split("\n").filter(l => /^\d+\. /.test(l));
  assert.equal(lines.length, 10);
  assert.match(lines[0], /Airline orders/, "ən çox mənbəli birinci"); assert.match(lines[1], /tsunami warning/);
  assert.ok(!text.includes("coast</a>") && !text.includes("Bakıda") && !text.includes("Too old"), "eyni hadisə, başqa dil və köhnə xəbər yoxdur");
  assert.match(text, /^<b>📰 8ULDUZ · Top 10 stories of the day<\/b>\nEvening edition · November 8\n/);
  assert.match(lines[0], /href="https:\/\/8ulduz\.az\/#\/xeber\/0{15}8\?b=dunya&amp;h=\d+"/, "keçid saytdadır, & qaçırılıb");
  assert.equal(sent[0].reply_markup.inline_keyboard[1][0].callback_data, "stop:g_en");
  assert.deepEqual(I.digestMessages(s, "en", ed, en, app), [], "eyni buraxılış iki dəfə getmir");
  assert.deepEqual(I.digestMessages(s, "ru", ed, en.slice(0, 4).map(a => ({ ...a, lang: "ru" })), app), [], "5-dən az xəbər: getmir");
  assert.equal(s.dg.ru, ed.slug, "azdırsa da bu buraxılış üçün bir daha axtarılmır");
  assert.deepEqual(I.deliveries(s, [row("cccccccccccccccc", "idman", "Futbol xəbəri")], cat, app), [], "buraxılış açarı tək xəbər göndərmir");
  const ru = ["Президент Ильхам Алиев встретился с президентом Турции", "Президент Ильхам Алиев: Нас никто не разделит", "Пожар на складе в Сумгайыте потушен",
    "Цены на нефть выросли после сокращения добычи", "Сборная победила в отборочном матче", "Учёные открыли новую далёкую планету", "Шторм обрушился на побережье Европы"]
    .map((title, i) => ({ id: (i + 80).toString(16).padStart(16, "0"), category: "dunya", lang: "ru", title, summary: "", source: "Day.Az", sourceUrl: "https://news.day.az/world/" + i, publishedAt: t(1 + i * 0.3), alts: i < 2 ? [{}, {}] : [] }));
  const s3 = I.newState(); I.handle(s3, msg(14, "/start g_ru"), cat);
  const ruText = I.digestMessages(s3, "ru", ed, ru, app)[0].text;
  assert.ok(ruText.includes("встретился") && !ruText.includes("Нас никто"), "rəhbərin sitatı ayrıca xəbər sayılmır (sahib 2026-11-06: «1 hadisədən yalnız 1 xəbər»)");
  assert.match(ruText, /Вечерний выпуск · 8 ноября/);
  const s2 = I.newState(); I.handle(s2, msg(13, "/start g_en"), cat);
  assert.deepEqual(I.digestMessages(s2, "en", ed, en.map(a => ({ ...a, source: "Reuters", sourceUrl: "https://example.com/x" })), app), [], "qeydiyyatda olmayan mənbə (qırmızı xətt 2) buraxılışa düşmür");
  out = I.handle(s, msg(9, "/stop"), cat);
  assert.match(out[0].text, /^🔕 Unsubscribed/); assert.equal(s.subs[9], undefined);
  out = I.handle(s, { update_id: 5, callback_query: { id: "q", data: "stop:g_tr", message: { chat: { id: 11 } } } }, cat);
  assert.equal(out[0].text, "🔕 Abonelik bitti"); assert.equal(s.subs[11], undefined);
  I.handle(s, msg(12, "/start i_fenerbahce"), cat); I.handle(s, msg(12, "/start g_ru"), cat);
  assert.match(I.handle(s, msg(12, "/stop"), cat)[0].text, /^🔕 Bütün izləmələr dayandırıldı/, "Azərbaycan mövzusu da varsa cavab Azərbaycan dilində");
});

test("izlə: a reader from the English, Russian or Turkish site follows a topic in their own language — replies, topic names and stories (owner 2026-11-08: «'Telegram-da izlə' düymələri başqa dillərdə də»)", () => {
  const trs = Object.fromEntries(["en", "ru", "tr"].map(c => [c, I.loadTr(root, c)]));
  const s = I.newState();
  let out = I.handle(s, msg(21, "/start en-b_dunya"), cat, trs);
  assert.deepEqual([s.subs[21], s.lang[21]], [["b_dunya"], "en"]);
  assert.equal(out[0].text, "✅ Now following «World». New stories will come here as soon as they appear.\n\nList and stop: /list");
  I.handle(s, msg(21, "/start en-i_fenerbahce"), cat, trs);
  assert.match(I.handle(s, msg(21, "/start en-b_dunya"), cat, trs)[0].text, /^✅ You already follow «World»/);
  out = I.handle(s, msg(21, "/list"), cat, trs);
  assert.equal(out[0].text, "You follow:\n• World\n• Fenerbahce"); assert.equal(out[0].reply_markup.inline_keyboard[0][0].text, "🔕 World — stop");
  assert.match(I.handle(s, msg(22, "/start ru-r_quba"), cat, trs)[0].text, /^✅ Вы следите за темой «Губа»/);
  out = I.handle(s, { update_id: 7, callback_query: { id: "q", data: "stop:r_quba", message: { chat: { id: 22 } } } }, cat, trs);
  assert.equal(out[0].text, "🔕 «Губа»: подписка отменена"); assert.equal(s.subs[22], undefined);
  out = I.handle(s, msg(23, "/start tr-movzu"), cat, trs);
  assert.match(out[0].text, /^📩 Neyi takip etmek istersiniz\?/); assert.equal(s.lang[23], "tr");
  assert.match(I.handle(s, msg(23, "Erdoğan"), cat, trs)[0].text, /^✅ «Erdoğan» takip ediliyor/, "bota yazılan söz də o dildə");
  // Göndəriş: ingilis oxucuya ingilis xəbəri, idman isə istənilən dildə; Azərbaycan oxucusu üçün əvvəlki kimi.
  s.subs[24] = ["b_dunya"]; s.lang[24] = "az"; s.seen = [];
  const sent = I.deliveries(s, [
    row("e100000000000001", "dunya", "Fire in the city", { lang: "en", source: "Trend", sourceUrl: "https://trend.az/world/1" }),
    row("a100000000000001", "dunya", "Şəhərdə yanğın"),
    row("f100000000000001", "idman", "Fenerbahçe yeni transfer etdi", { lang: "tr", source: "Ajansspor", sourceUrl: "https://www.ajansspor.com/haber/1" }),
  ], cat, app, trs);
  const got = id => sent.filter(m => m.chat_id === id).map(m => (m.caption || m.text).match(/^<b>([^<]+)/)[1]).sort();
  assert.deepEqual(got("21"), ["Fenerbahçe yeni transfer etdi", "Fire in the city"], "ingilis oxucu: ingilis xəbəri və idman");
  assert.deepEqual(got("24"), ["Şəhərdə yanğın"], "Azərbaycan oxucusu: əvvəlki kimi");
  const en = sent.find(m => m.chat_id === "21" && /Fire/.test(m.text || m.caption));
  assert.match(en.text || en.caption, /Trend · World$/); assert.deepEqual(en.reply_markup.inline_keyboard.map(r => r[0].text), ["📖 Read on 8ULDUZ", "🔕 World — stop"]);
  assert.match(I.handle(s, msg(21, "/stop"), cat, trs)[0].text, /^🔕 All follows stopped/);
  out = I.handle(s, msg(25, "/start b_dunya"), cat, trs);
  assert.equal(s.lang[25], "az"); assert.match(out[0].text, /^✅ «Dünya» izlənir/, "şəkilçisiz köhnə keçid: Azərbaycan dili");
  assert.equal(I.chatLang(s, "99"), "az", "naməlum oxucu: Azərbaycan dili");
});

test("izlə: a language's full feed read for the first time, or after nobody followed in it, does not flood readers with old stories", () => {
  const s = I.newState(), en = (id, title) => row(id, "dunya", title, { lang: "en", source: "Trend", sourceUrl: "https://trend.az/world/" + id });
  s.subs = { 31: ["b_dunya"], 32: ["g_ru"] }; s.lang = { 31: "en" }; s.seen = [];
  assert.deepEqual(I.topicLangs(s), ["en"], "yalnız buraxılışa yazılan oxucu dil lentini yükləmir");
  assert.deepEqual(I.mergeLangFeeds(s, ["en"], { en: [en("e200000000000001", "Old story")] }), [], "ilk dəfə: göndərilmir");
  assert.ok(s.seen.includes("e200000000000001")); assert.deepEqual(s.primed, ["en"]);
  const merged = I.mergeLangFeeds(s, ["en"], { en: [en("e200000000000001", "Old story"), en("e200000000000002", "New story")] });
  assert.deepEqual(I.deliveries(s, merged, cat, app).map(m => m.chat_id + ":" + /New story/.test(m.text || m.caption)), ["31:true"]);
  I.mergeLangFeeds(s, [], {});
  assert.deepEqual(s.primed, [], "ingilis dilində izləyən qalmadı");
  assert.deepEqual(I.mergeLangFeeds(s, ["en"], { en: [en("e200000000000003", "Gap story")] }), [], "fasilədən sonra yenə «görülmüş» sayılır");
  assert.deepEqual(I.mergeLangFeeds(s, ["en"], { en: null }), [], "lent alınmadısa: heç nə");
  assert.deepEqual(s.primed, ["en"], "alınmasa da əvvəl hazırlanmış dil qalır");
});

test("izlə: a long written topic still gets its stories — the stop button fits Telegram's 64-byte callback_data", () => {
  const topic = "Naxçıvan Muxtar Respublikasının büdcəsi", s = I.newState(), c = I.catalog(app);
  assert.ok(Buffer.byteLength(topic) > 42 && Buffer.byteLength(topic) < 46, "qəbul olunan ən uzun mövzulardan biri");
  let out = I.handle(s, msg(9, topic), c);
  assert.match(out[0].text, /^✅ /);
  const key = s.subs["9"]?.[0];
  assert.ok(key && Buffer.byteLength("stop:" + key) > 64, "açar «stop:» ilə 64 baytdan uzundur");
  out = I.handle(s, msg(9, "/list"), c);
  const data = out.flatMap(o => o.reply_markup?.inline_keyboard || []).flat().map(b => b.callback_data).filter(Boolean);
  assert.ok(data.length === 1 && Buffer.byteLength(data[0]) <= 64 && data[0].startsWith("stop#"), "düymənin məlumatı 64 bayta sığır");
  const sent = I.deliveries(s, [row("n1", "siyaset", "Naxçıvan Muxtar Respublikasının büdcəsi təsdiqləndi")], c, app);
  assert.ok(sent.length >= 1, "xəbər oxucuya gedir");
  for (const o of sent) for (const b of (o.reply_markup?.inline_keyboard || []).flat()) if (b.callback_data) assert.ok(Buffer.byteLength(b.callback_data) <= 64);
  I.handle(s, { update_id: 3, callback_query: { id: "q", data: data[0], message: { chat: { id: 9 } } } }, c);
  assert.equal(s.subs["9"], undefined, "uzun mövzu düymə ilə dayandırılır");
  I.handle(s, msg(9, "Pensiya"), c);
  assert.ok(I.handle(s, msg(9, "/list"), c).flatMap(o => o.reply_markup?.inline_keyboard || []).flat().some(b => /^stop:q_/.test(b.callback_data || "")), "qısa açar əvvəlki kimi göndərilir");
});
