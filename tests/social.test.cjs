// .github/scripts/social.cjs: saytın xəbərləri öz profillərimizdə (sahib, 2026-11-05).
const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("fs"), path = require("path"), os = require("os");
const S = require("../.github/scripts/social.cjs");

const NOW = Date.parse("2026-11-05T15:00:00Z");
const ago = m => new Date(NOW - m * 60e3).toISOString();
const art = (id, o = {}) => ({ id: id.padEnd(16, "0"), title: `Xəbər ${id}`, summary: "Qısa xülasə", category: "gundem", lang: "az", publishedAt: ago(10), alts: [{}, {}, {}], ...o });
const opt = S.options({});

test("social: only Azerbaijani stories covered by 4+ sources (or the President section) within 3 hours, biggest first", () => {
  const list = S.candidates([
    art("a1", { alts: [{}, {}] }),                          // 3 mənbə: düşür
    art("a2"),                                              // 4 mənbə
    art("a3", { alts: Array(8).fill({}) }),                 // 9 mənbə: birinci
    art("a4", { lang: "tr", alts: Array(8).fill({}) }),     // xarici dil: düşür
    art("a5", { publishedAt: ago(200) }),                   // 3 saatdan köhnə: düşür
    art("a6", { category: "prezident", alts: [] }),         // Prezident bölməsi: həmişə
    art("a7", { id: "not-a-share-id" }),                    // paylaşma səhifəsi yoxdur: düşür
    art("a8", { title: "  " }),
  ], NOW, opt).map(a => a.id.slice(0, 2));
  assert.deepEqual(list, ["a3", "a2", "a6"], "bərabər balda daha yeni birinci, sonra lent sırası");
  assert.deepEqual(opt, { minSources: 4, maxAgeH: 3, perRun: 1, minGapMin: 18 }, "saatda ən çox 3 post (postlar arası 18 dəqiqə)");
});

test("social: a network is used only when its secret exists; no secrets means nothing is sent", async () => {
  assert.deepEqual(S.networks({}).map(n => n.name), []);
  assert.deepEqual(S.networks({ TELEGRAM_BOT_TOKEN: "t", FB_PAGE_ID: "1", X_API_KEY: "k", LINKEDIN_TOKEN: "l" }).map(n => n.name), ["telegram"], "yarımçıq açar dəsti işləmir");
  let calls = 0;
  const res = await S.run({ articles: [art("b1")], env: {}, now: NOW, fetch: () => { calls++; }, log: () => {} });
  assert.equal(calls, 0);
  assert.deepEqual(res, { posted: [], failed: [] });
});

test("social: Telegram post links to the site share page, one per run, never twice, token never logged", async () => {
  const env = { TELEGRAM_BOT_TOKEN: "123:SECRET" };
  const sent = [], logs = [];
  const fetch = async (url, init) => {
    if (url.includes("/getUpdates")) return { json: async () => ({ ok: true, result: [
      { my_chat_member: { chat: { id: -1001, type: "channel", title: "Köhnə" }, new_chat_member: { status: "administrator" } } },
      { my_chat_member: { chat: { id: -1001, type: "channel", title: "Köhnə" }, new_chat_member: { status: "left" } } },
      { my_chat_member: { chat: { id: 5, type: "private", title: "" }, new_chat_member: { status: "member" } } },
      { my_chat_member: { chat: { id: -1002, type: "channel", title: "8ULDUZ" }, new_chat_member: { status: "administrator" } } }] }) };
    if (init.method === "HEAD") return { status: url.endsWith("x/c200000000000000") ? 404 : 200 };
    sent.push([url, JSON.parse(init.body)]);
    return { ok: true, status: 200, text: async () => "" };
  };
  const state = {};
  const articles = [art("c1", { title: "Bakı & Sumqayıt: külək", alts: Array(6).fill({}) }), art("c2", { alts: Array(9).fill({}) }), art("c3")];
  await S.run({ articles, env, now: NOW, fetch, state, log: s => logs.push(s) });
  assert.equal(sent.length, 1, "bir dövrədə bir post");
  const [url, body] = sent[0];
  assert.equal(url, "https://api.telegram.org/bot123:SECRET/sendMessage");
  assert.equal(body.chat_id, -1002, "botun admin olduğu kanal yeniləmələrdən tapılır (çıxarıldığı və şəxsi söhbət sayılmır)");
  assert.deepEqual(state._telegram, { chat: -1002, title: "8ULDUZ" }, "tapılan kanal yadda qalır");
  assert.ok(logs.some(s => s.includes("kanal tapıldı — 8ULDUZ (-1002)")));
  assert.ok(body.text.startsWith("<b>Bakı &amp; Sumqayıt: külək</b>") && body.text.endsWith("https://8ulduz.az/x/c100000000000000"), "c2-nin səhifəsi hələ yoxdur: növbəti");
  assert.equal(body.link_preview_options.url, "https://8ulduz.az/x/c100000000000000");
  assert.ok(state.telegram["c100000000000000"]);
  await S.run({ articles, env, now: NOW + 5 * 60e3, fetch, state, log: s => logs.push(s) });
  assert.equal(sent.length, 1, "5 dəqiqə sonra (növbəti sayt yayımı) post yoxdur: fasilə 18 dəqiqədir");
  assert.ok(logs.some(s => s.includes("telegram: son post 5 dəq əvvəl, növbəti 13 dəq sonra")));
  await S.run({ articles, env, now: NOW + 20 * 60e3, fetch, state, log: s => logs.push(s) });
  assert.equal(sent[1][1].text.includes("x/c300000000000000"), true, "fasilədən sonra növbəti xəbər, təkrar yox");
  assert.ok(!logs.join("\n").includes("SECRET"));
});

test("social: Telegram without a channel posts nothing and says so; an explicit TELEGRAM_CHAT is used as is", async () => {
  const logs = [], sent = [];
  const fetch = async (url, init = {}) => {
    if (url.includes("/getUpdates")) return { json: async () => ({ ok: true, result: [] }) };
    if (url.includes("/getMe")) return { json: async () => ({ ok: true, result: { username: "ulduz_bot" } }) };
    if (init.method === "HEAD") return { status: 200 };
    sent.push(JSON.parse(init.body));
    return { ok: true, status: 200, text: async () => "" };
  };
  const res = await S.run({ articles: [art("ab")], env: { TELEGRAM_BOT_TOKEN: "1:S" }, now: NOW, fetch, state: {}, log: s => logs.push(s) });
  assert.deepEqual(res, { posted: [], failed: [] });
  assert.ok(logs.some(s => s.includes("bot @ulduz_bot heç bir kanalda admin deyil")), "sahib hansı botu əlavə edəcəyini görür");
  await S.run({ articles: [art("ab")], env: { TELEGRAM_BOT_TOKEN: "1:S", TELEGRAM_CHAT: "@kanal" }, now: NOW, fetch, state: {}, log: () => {} });
  assert.equal(sent[0].chat_id, "@kanal");
});

test("social: a failing network is reported without its token and the story stays unposted", async () => {
  const env = { TELEGRAM_BOT_TOKEN: "123:SECRET", TELEGRAM_CHAT: "-1002" };
  const logs = [], state = { _telegram: { chat: -1002, title: "8ULDUZ" } };
  const fetch = async (url, init) => {
    if (init.method === "HEAD") return { status: 200 };
    throw new Error(`request to ${url} failed`);
  };
  const res = await S.run({ articles: [art("d1")], env, now: NOW, fetch, state, log: s => logs.push(s) });
  assert.deepEqual(res.failed, [["telegram", "d100000000000000"]]);
  assert.deepEqual(state.telegram, {});
  assert.ok(state._telegram, 'adi şəbəkə xətasında kanal unudulmur');
  assert.ok(!logs.join("\n").includes("SECRET") && logs.join("\n").includes("***"));
});

test("social: X post is signed with OAuth 1.0a and fits 280 characters", () => {
  const { base, header } = S.oauthHeader("POST", "https://api.x.com/2/tweets", { key: "ck", secret: "cs", token: "at", tokenSecret: "as" }, "nonce", 1700000000);
  assert.equal(base, "POST&https%3A%2F%2Fapi.x.com%2F2%2Ftweets&oauth_consumer_key%3Dck%26oauth_nonce%3Dnonce%26oauth_signature_method%3DHMAC-SHA1%26oauth_timestamp%3D1700000000%26oauth_token%3Dat%26oauth_version%3D1.0");
  const sig = require("crypto").createHmac("sha1", "cs&as").update(base).digest("base64");
  assert.ok(header.startsWith("OAuth oauth_consumer_key=\"ck\"") && header.includes(`oauth_signature="${encodeURIComponent(sig)}"`));
  const x = S.networks({ X_API_KEY: "k", X_API_SECRET: "s", X_ACCESS_TOKEN: "t", X_ACCESS_SECRET: "a" })[0];
  const [, init] = x.request(art("e1", { title: "Uzun ".repeat(100) }));
  const text = JSON.parse(init.body).text;
  assert.ok(text.length - "https://8ulduz.az/x/e100000000000000".length + 23 <= 280);
  assert.ok(init.headers.authorization.startsWith("OAuth "));
});

test("social: Facebook page and LinkedIn requests carry the share link", () => {
  const [fb, li] = S.networks({ FB_PAGE_ID: "42", FB_PAGE_TOKEN: "p", LINKEDIN_TOKEN: "l", LINKEDIN_AUTHOR: "urn:li:person:abc" });
  const a = art("f1");
  const [fu, fi] = fb.request(a);
  assert.equal(fu, "https://graph.facebook.com/v21.0/42/feed");
  assert.equal(new URLSearchParams(fi.body).get("link"), "https://8ulduz.az/x/f100000000000000");
  const [lu, lii] = li.request(a);
  const body = JSON.parse(lii.body);
  assert.equal(lu, "https://api.linkedin.com/rest/posts");
  assert.equal(body.author, "urn:li:person:abc");
  assert.equal(body.content.article.source, "https://8ulduz.az/x/f100000000000000");
});

test("social: state keeps posted ids for 3 days and survives a broken file", () => {
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), "social-"));
  const f = path.join(dir, "posted.json");
  fs.writeFileSync(f, JSON.stringify({ telegram: { a: NOW / 1000 - 3600, b: NOW / 1000 - 4 * 86400 }, _telegram: { chat: -1002, title: "8ULDUZ" } }));
  assert.deepEqual(Object.keys(S.readState(f, NOW).telegram), ["a"]);
  assert.deepEqual(S.readState(f, NOW)._telegram, { chat: -1002, title: "8ULDUZ" }, "tapılmış kanal köhnəlmir");
  fs.writeFileSync(f, "{bad");
  assert.deepEqual(S.readState(f, NOW), {});
});

test("social: the workflow is separate from the news pipeline, reads only the feed and passes secrets by name", () => {
  const wf = fs.readFileSync(path.join(__dirname, "../.github/workflows/social.yml"), "utf8");
  assert.ok(wf.includes("node .github/scripts/social.cjs data/news.json"));
  assert.ok(wf.includes('workflows: ["pages build and deployment"]') && wf.includes("cron:"), "hər sayt yayımından sonra, cron ehtiyat");
  assert.ok(wf.includes("contents: read") && !wf.includes("contents: write"), "repoya yazmır");
  for (const s of ["TELEGRAM_BOT_TOKEN", "FB_PAGE_TOKEN", "X_ACCESS_SECRET", "LINKEDIN_TOKEN"]) assert.ok(wf.includes(`\${{ secrets.${s} }}`), s);
  const pipe = fs.readFileSync(path.join(__dirname, "../.github/scripts/pipeline.sh"), "utf8");
  assert.ok(!pipe.includes("social"), "xəbər axınına (qırmızı xətt 1) toxunmur");
});

test("social: the site's Telegram buttons lead to the channel the bot posts to, not to a personal account", () => {
  const cfg = fs.readFileSync(path.join(__dirname, "../assets/config.js"), "utf8");
  assert.ok(cfg.includes('telegram: "https://t.me/sekkizulduz_az"'), "«Kanala keç» və «İzlə → Telegram» 8ULDUZ kanalına aparır");
  assert.ok(!/telegram: "https:\/\/t\.me\/(sekkizulduz|vuqarm6666)"/.test(cfg), "@sekkizulduz və @vuqarm6666 şəxsi hesabdır, kanal deyil");
});
