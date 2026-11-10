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
    if (init.method === "HEAD") return { status: url.includes("/c200000000000000") ? 404 : 200 };
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
  assert.ok(body.text.startsWith("<b>Bakı &amp; Sumqayıt: külək</b>") && body.text.includes("https://www.8ulduz.az/c100000000000000?h="), "c2-nin səhifəsi hələ yoxdur: növbəti");
  assert.match(body.link_preview_options.url, /^https:\/\/www\.8ulduz\.az\/c100000000000000\?h=\d{8}$/, "h: xəbərin saatı (arxiv.cjs)");
  assert.ok(state.telegram["c100000000000000"]);
  await S.run({ articles, env, now: NOW + 5 * 60e3, fetch, state, log: s => logs.push(s) });
  assert.equal(sent.length, 1, "5 dəqiqə sonra (növbəti sayt yayımı) post yoxdur: fasilə 18 dəqiqədir");
  assert.ok(logs.some(s => s.includes("telegram: son post 5 dəq əvvəl, növbəti 13 dəq sonra")));
  await S.run({ articles, env, now: NOW + 20 * 60e3, fetch, state, log: s => logs.push(s) });
  assert.equal(sent[1][1].text.includes("/c300000000000000"), true, "fasilədən sonra növbəti xəbər, təkrar yox");
  assert.ok(!logs.join("\n").includes("123:SECRET"));
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
  assert.ok(!logs.join("\n").includes("123:SECRET") && logs.join("\n").includes("***"));
});

test("social: X post is signed with OAuth 1.0a and fits 280 characters", () => {
  const { base, header } = S.oauthHeader("POST", "https://api.x.com/2/tweets", { key: "ck", secret: "cs", token: "at", tokenSecret: "as" }, "nonce", 1700000000);
  assert.equal(base, "POST&https%3A%2F%2Fapi.x.com%2F2%2Ftweets&oauth_consumer_key%3Dck%26oauth_nonce%3Dnonce%26oauth_signature_method%3DHMAC-SHA1%26oauth_timestamp%3D1700000000%26oauth_token%3Dat%26oauth_version%3D1.0");
  const sig = require("crypto").createHmac("sha1", "cs&as").update(base).digest("base64");
  assert.ok(header.startsWith("OAuth oauth_consumer_key=\"ck\"") && header.includes(`oauth_signature="${encodeURIComponent(sig)}"`));
  const x = S.networks({ X_API_KEY: "k", X_API_SECRET: "s", X_ACCESS_TOKEN: "t", X_ACCESS_SECRET: "a" })[0];
  const [, init] = x.request(art("e1", { title: "Uzun ".repeat(100) }));
  const text = JSON.parse(init.body).text;
  assert.ok(text.length - "https://www.8ulduz.az/e100000000000000".length + 23 <= 280);
  assert.ok(init.headers.authorization.startsWith("OAuth "));
});

test("social: Facebook page and LinkedIn requests carry the share link", () => {
  const [fb, li] = S.networks({ FB_PAGE_ID: "42", FB_PAGE_TOKEN: "p", LINKEDIN_TOKEN: "l", LINKEDIN_AUTHOR: "urn:li:person:abc" });
  const a = art("f1");
  const [fu, fi] = fb.request(a);
  assert.equal(fu, "https://graph.facebook.com/v27.0/42/feed");
  assert.equal(new URLSearchParams(fi.body).get("link"), `https://www.8ulduz.az/f100000000000000?h=${a.publishedAt.slice(2, 13).replace(/\D/g, "")}`);
  assert.equal(new URLSearchParams(fi.body).get("access_token"), "p");
  const [lu, lii] = li.request(a);
  const body = JSON.parse(lii.body);
  assert.equal(lu, "https://api.linkedin.com/rest/posts");
  assert.equal(body.author, "urn:li:person:abc");
  assert.equal(body.content.article.source, `https://www.8ulduz.az/f100000000000000?h=${a.publishedAt.slice(2, 13).replace(/\D/g, "")}`);
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
  assert.ok(wf.includes("workflow_dispatch:") && wf.includes("cron:"), "pipeline dispatch edir, cron ehtiyat");
  assert.ok(wf.includes("contents: read") && !wf.includes("contents: write"), "repoya yazmır");
  for (const s of ["TELEGRAM_BOT_TOKEN", "FB_PAGE_TOKEN", "X_ACCESS_SECRET", "LINKEDIN_TOKEN"]) assert.ok(wf.includes(`\${{ secrets.${s} }}`), s);
  const pipe = fs.readFileSync(path.join(__dirname, "../.github/scripts/pipeline.sh"), "utf8");
  // Qırmızı xətt 1: yalnız main yayımı uğurlu olanda, arxa planda və vaxt limiti ilə; sürətli dövrəyə toxunmur.
  assert.equal(pipe.split("social.yml").length - 1, 1, "bir yerdən başladılır");
  const pub = pipe.slice(pipe.indexOf("publish_main() {"), pipe.indexOf("\nslow_loop() {"));
  assert.ok(pub.includes('( sleep 90; gh_t workflow run social.yml --ref "$BRANCH" >/dev/null 2>&1 ) &'), "main yayımından sonra, arxa planda, gh_t (15 s limit)");
});

test("social: the site's Telegram buttons lead to the channel the bot posts to, not to a personal account", () => {
  const cfg = fs.readFileSync(path.join(__dirname, "../assets/config.js"), "utf8");
  assert.ok(cfg.includes('telegram: "https://t.me/sekkizulduz_az"'), "«Kanala keç» və «İzlə → Telegram» 8ULDUZ kanalına aparır");
  assert.ok(!/telegram: "https:\/\/t\.me\/(sekkizulduz|vuqarm6666)"/.test(cfg), "@sekkizulduz və @vuqarm6666 şəxsi hesabdır, kanal deyil");
});

test("social: a Facebook user token in the secret is turned into the page token before posting, and neither is logged", async () => {
  const env = { FB_PAGE_ID: "1470250006171917", FB_PAGE_TOKEN: "EAAuserTOKEN123456" };
  const posts = [], logs = [];
  const fetch = async (url, init = {}) => {
    if (url.includes("?fields=access_token")) return { json: async () => ({ access_token: "EAApageTOKEN654321", id: "1470250006171917" }) };
    if (init.method === "HEAD") return { status: 200 };
    posts.push([url, new URLSearchParams(init.body)]);
    return { ok: false, status: 400, text: async () => "bad EAApageTOKEN654321 EAAuserTOKEN123456" };
  };
  await S.run({ articles: [art("fa", { imageUrl: "https://apa.az/i.jpg" })], env, now: NOW, fetch, state: {}, log: s => logs.push(s) });
  const feed = posts.find(p => p[0].endsWith("/feed"));
  assert.equal(feed[0], "https://graph.facebook.com/v27.0/1470250006171917/feed");
  assert.equal(feed[1].get("access_token"), "EAApageTOKEN654321", "səhifə açarı ilə yazılır");
  const all = logs.join("\n");
  assert.ok(all.includes("istifadəçi açarından səhifə açarı alındı"));
  assert.ok(!all.includes("EAApageTOKEN654321") && !all.includes("EAAuserTOKEN123456") && all.includes("***"), "açarlar jurnalda görünmür");
});

test("social: the same headline under a new story number is not posted to a network twice", async () => {
  const sent = [];
  const fetch = async (url, init) => {
    if (init.method === "HEAD") return { status: 200 };
    sent.push(JSON.parse(init.body).text);
    return { ok: true, status: 200, text: async () => "" };
  };
  const env = { TELEGRAM_BOT_TOKEN: "123:SECRET", TELEGRAM_CHAT: "-1002" }, state = {};
  const title = "Bu şəxslər 3600 manat maaş alacaq";
  await S.run({ articles: [art("d1", { title })], env, now: NOW, fetch, state, log: () => {} });
  await S.run({ articles: [art("d2", { title: ` ${title.toUpperCase()}! ` }), art("d3")], env, now: NOW + 20 * 60e3, fetch, state, log: () => {} });
  assert.equal(sent.length, 2);
  assert.ok(sent[1].includes("/d300000000000000"), "5–6 noyabr Telegram-da eyni başlıq iki dəfə getmişdi");
});

test("social: the site's Facebook button leads to the page the bot posts to, not to the 'Səkkiz Ulduz' profile", () => {
  const cfg = fs.readFileSync(path.join(__dirname, "..", "assets", "config.js"), "utf8");
  assert.ok(cfg.includes('facebook: "https://www.facebook.com/profile.php?id=61596264031461"'), "«8ulduz» səhifəsi (Graph səhifə nömrəsi 1470250006171917)");
  assert.ok(!cfg.includes("61596034210996"), "«Səkkiz Ulduz» ayrı profildir, xəbərlər ora getmir");
});

test("social: Google Search Console verification files stay in the site root (Google News publisher page depends on them)", () => {
  for (const f of ["google46236e63755f93fb.html", "google5f791d9cb20ec3f6.html"])
    assert.equal(fs.readFileSync(path.join(__dirname, "..", f), "utf8").trim(), `google-site-verification: ${f}`, `${f} silinsə, Google təsdiqi itir`);
});

test("social: Yandex Webmaster verification file stays in the site root", () => {
  assert.ok(fs.readFileSync(path.join(__dirname, "..", "yandex_08701d77d2078d9e.html"), "utf8").includes("Verification: 08701d77d2078d9e"), "silinsə, Yandex təsdiqi itir");
});

test("social: the daily digest goes out at its hour even inside the 18-minute gap, as a numbered list with its own link, once", async () => {
  const sent = [];
  const fetch = async (url, init) => {
    if (init.method === "HEAD") return { status: 200 };
    sent.push(JSON.parse(init.body).text);
    return { ok: true, status: 200, text: async () => "" };
  };
  const env = { TELEGRAM_BOT_TOKEN: "123:SECRET", TELEGRAM_CHAT: "-1002" };
  const at = NOW / 1000 - 300;
  const ed = { slug: "2026-11-05-seher", title: "Səhər icmalı · 5 noyabr 2026", url: "https://8ulduz.az/icmal/2026-11-05-seher/", at,
    items: [{ t: "Birinci xəbər", n: 12 }, { t: "İkinci & son xəbər", n: 9 }] };
  const state = { _last: { telegram: NOW / 1000 - 5 * 60 } };
  await S.run({ articles: [art("e1")], digestIndex: [ed], env, now: NOW, fetch, state, log: () => {} });
  assert.equal(sent.length, 1, "5 dəqiqə əvvəl post olsa da icmal gedir, adi xəbər isə gözləyir");
  assert.ok(sent[0].startsWith("<b>Səhər icmalı · 5 noyabr 2026</b>"));
  assert.ok(sent[0].includes("1. Birinci xəbər\n2. İkinci &amp; son xəbər"));
  assert.ok(sent[0].endsWith("https://8ulduz.az/icmal/2026-11-05-seher/"));
  await S.run({ articles: [], digestIndex: [ed], env, now: NOW + 20 * 60e3, fetch, state, log: () => {} });
  assert.equal(sent.length, 1, "icmal ikinci dəfə getmir");
  assert.deepEqual(S.digests([{ ...ed, at: NOW / 1000 - 5 * 3600 }], NOW), [], "4 saatdan köhnə buraxılış göndərilmir");
});

test("social: Instagram posts a picture story to the Instagram account linked to the Facebook page, quietly skips until it is linked", async () => {
  const env = { FB_PAGE_ID: "1470250006171917", FB_PAGE_TOKEN: "EAAuserTOKEN123456" };
  assert.deepEqual(S.networks(env).map(n => n.name), ["facebook", "instagram"]);
  assert.deepEqual(S.networks({ ...env, INSTAGRAM: "0" }).map(n => n.name), ["facebook"], "söndürmək olur");
  const pic = art("e1", { imageUrl: "https://apa.az/i.jpg", title: "Bakıda yeni park açıldı", summary: "Park 5 hektardır." });
  const noPic = art("e2", { alts: Array(9).fill({}) }); // ən çox mənbəli, amma şəkilsiz: Instagram-a getmir
  const calls = [], logs = [];
  let linked = false, ready = 1;
  const fetch = async (url, init = {}) => {
    if (init.method === "HEAD") return { status: 200 };
    calls.push([url, init.body ? Object.fromEntries(new URLSearchParams(init.body)) : null]);
    if (url.includes("fields=instagram_business_account")) return { json: async () => linked ? { access_token: "PAGEtok12345", instagram_business_account: { id: "1784" } } : { access_token: "PAGEtok12345" } };
    if (url.endsWith("/feed")) return { ok: true, status: 200, text: async () => "" };
    if (url.endsWith("/1784/media")) return { ok: true, status: 200, json: async () => ({ id: "C9" }), text: async () => "" };
    if (url.endsWith("/1784/media_publish")) return ready-- > 0 ? { ok: false, status: 400, text: async () => '{"error":{"code":9007,"message":"Media ID is not available"}}' } : { ok: true, status: 200, text: async () => "" };
    throw new Error("gözlənilməz " + url);
  };
  const state = {};
  let res = await S.run({ articles: [noPic, pic], env, now: NOW, fetch, state, log: s => logs.push(s) });
  assert.deepEqual(res.posted.map(x => x[0]), ["facebook"], "hesab bağlı deyil: Instagram sakitcə ötürülür");
  assert.deepEqual(res.failed, []);
  assert.ok(logs.some(s => s.startsWith("instagram: səhifəyə bağlı Instagram peşəkar hesabı yoxdur")));
  linked = true; calls.length = 0;
  const net = S.networks(env).find(n => n.name === "instagram");
  assert.equal(net.gapMin, 45, "gündə ən çox 32 post (Instagram API həddi 50)");
  res = await S.run({ articles: [noPic, pic], env: { ...env, IG_WAIT_MS: "0" }, now: NOW + 60 * 60e3, fetch, state: { ...state, _last: {} }, log: () => {} });
  const media = calls.find(c => c[0].endsWith("/1784/media"));
  assert.ok(media, "şəkilli xəbər göndərildi");
  assert.equal(media[1].image_url, "https://apa.az/i.jpg");
  assert.equal(media[1].access_token, "PAGEtok12345", "istifadəçi açarından alınmış səhifə açarı");
  assert.ok(media[1].caption.startsWith("Bakıda yeni park açıldı\n\nPark 5 hektardır.") && media[1].caption.includes("8ulduz.az"));
  assert.ok(!calls.some(c => c[1]?.image_url === undefined && c[0].endsWith("/media")), "şəkilsiz xəbər Instagram-a getmir");
  assert.equal(calls.filter(c => c[0].endsWith("/media_publish")).length, 2, "hazır deyilsə (9007) gözləyib yenidən dərc edir");
  assert.ok(res.posted.some(x => x[0] === "instagram" && x[1] === pic.id));
});

test("social: a picture Instagram refuses is skipped so the next run tries another story", async () => {
  const env = { FB_PAGE_ID: "1", FB_PAGE_TOKEN: "EAAuserTOKEN123456", INSTAGRAM: "1" };
  const pic = art("f1", { imageUrl: "https://site.az/a.webp" });
  const fetch = async (url, init = {}) => {
    if (init.method === "HEAD") return { status: 200 };
    if (url.includes("fields=instagram_business_account")) return { json: async () => ({ instagram_business_account: { id: "17" } }) };
    if (url.endsWith("/feed")) return { ok: true, status: 200, text: async () => "" };
    return { ok: false, status: 400, text: async () => '{"error":{"code":36003,"message":"Only photo or video can be accepted as media type"}}' };
  };
  const state = {};
  const res = await S.run({ articles: [pic], env, now: NOW, fetch, state, log: () => {} });
  assert.deepEqual(res.failed, [["instagram", pic.id]]);
  assert.ok(state.instagram[pic.id], "təkrar yoxlanmır");
});

test("social: missing X secrets are named in the log (2026-11-10: X got no posts, nothing said why), never their values", async () => {
  const logs = [];
  await S.run({ articles: [art("g1")], env: { X_API_KEY: "k", X_API_SECRET: "secretvalue" }, now: NOW, fetch: async () => ({ status: 200, ok: true }), log: m => logs.push(m) });
  assert.ok(logs.some(m => m.startsWith("x: sirr yoxdur — X_ACCESS_TOKEN, X_ACCESS_SECRET")), logs.join("\n"));
  assert.ok(!logs.join("\n").includes("secretvalue"));
  const full = [];
  await S.run({ articles: [], env: { X_API_KEY: "k", X_API_SECRET: "s", X_ACCESS_TOKEN: "t", X_ACCESS_SECRET: "a" }, now: NOW, fetch: async () => ({ status: 200, ok: true }), log: m => full.push(m) });
  assert.ok(!full.some(m => m.includes("sirr yoxdur")));
});

test("social: share links use the share Worker host www.8ulduz.az/<id>?h=, not the old 8ulduz.az/x/ pages", () => {
  const x = S.networks({ X_API_KEY: "k", X_API_SECRET: "s", X_ACCESS_TOKEN: "t", X_ACCESS_SECRET: "a" })[0];
  const text = JSON.parse(x.request(art("h1"))[1].body).text;
  assert.match(text, /\nhttps:\/\/www\.8ulduz\.az\/h100000000000000\?h=\d{8}$/);
  assert.ok(!fs.readFileSync(path.join(__dirname, "../.github/scripts/social.cjs"), "utf8").includes("8ulduz.az/x/"));
});

test("social: Facebook gets only stories with a picture, scrapes the link first and waits so the card shows the image (owner, 2026-11-10)", async () => {
  const env = { FB_PAGE_ID: "42", FB_PAGE_TOKEN: "PAGEtok12345", INSTAGRAM: "0", FB_SCRAPE_WAIT_MS: "0" };
  const noPic = art("a71", { alts: Array(9).fill({}) }), pic = art("a72", { imageUrl: "https://apa.az/i.jpg" });
  const calls = [];
  let card = [{ url: "https://wsrv.nl/?url=https%3A%2F%2Fapa.az%2Fi.jpg&w=1200" }];
  const fetch = async (url, init = {}) => {
    if (init.method === "HEAD") return { status: 200 };
    if (url.includes("?fields=access_token")) return { json: async () => ({}) };
    const body = Object.fromEntries(new URLSearchParams(init.body || ""));
    calls.push([url, body]);
    if (body.scrape === "true") return { ok: true, json: async () => ({ id: body.id, image: card }) };
    if (url.endsWith("/feed")) return { ok: true, status: 200, text: async () => "" };
    throw new Error("gözlənilməz " + url);
  };
  const logs = [];
  let res = await S.run({ articles: [noPic, pic], env, now: NOW, fetch, state: {}, log: s => logs.push(s) });
  assert.deepEqual(res.posted, [["facebook", pic.id]], "şəkilsiz xəbər Facebook-a getmir: ");
  const i = calls.findIndex(c => c[1].scrape === "true"), j = calls.findIndex(c => c[0].endsWith("/feed"));
  assert.ok(i >= 0 && j > i, "əvvəl keçid oxudulur, sonra post");
  assert.equal(calls[i][1].id, calls[j][1].link, "eyni keçid");
  card = [];
  calls.length = 0;
  res = await S.run({ articles: [art("a73", { imageUrl: "https://apa.az/j.jpg" })], env, now: NOW + 3600e3, fetch, state: {}, log: s => logs.push(s) });
  assert.deepEqual(res.posted.map(x => x[0]), ["facebook"], "Facebook şəkli görməsə də post gedir (wsrv.nl Facebook-a 403 verir, ötürsək heç nə getməzdi)");
});

test("social: the same event under different headlines is posted once per network (owner, 2026-11-10: Facebook got the President's Türkiyə visit 3 times)", async () => {
  const sum = "Azərbaycan Respublikasının Prezidenti İlham Əliyev Türkiyə Respublikasının Prezidenti Rəcəb Tayyib Ərdoğanın dəvəti ilə BMT-nin İqlim Dəyişmələri üzrə Çərçivə Konvensiyasının Tərəflər Konfransının 31-ci sessiyasının…";
  const p = (id, title, m, summary = sum) => art(id, { title, summary, category: "prezident", alts: [], publishedAt: ago(m), imageUrl: "https://apa.az/i.jpg" });
  const visit = [p("b1", "Prezident İlham Əliyev Türkiyəyə səfərə gedib", 70), p("b2", "İlham Əliyev Türkiyəyə səfərə gəlib", 60),
    p("b3", "Prezident xanımı ilə Türkiyəyə getdi", 50), p("b4", "İlham Əliyev Türkiyədə belə qarşılandı", 40, "")];
  const other = p("b5", "Prezident Polşa Prezidentinə başsağlığı verib", 30, "Azərbaycan Prezidenti İlham Əliyev Polşa Prezidenti Karol Navrotskiyə başsağlığı məktubu göndərib.");
  const sent = [];
  const f = async (url, init = {}) => { if (init.method === "HEAD") return { status: 200 }; if (/sendMessage/.test(url)) sent.push(JSON.parse(init.body).text); return { ok: true, status: 200, json: async () => ({ ok: true }) }; };
  const state = { _last: { telegram: 0 } }, logs = [];
  for (let i = 0; i < 5; i++) await S.run({ articles: [...visit, other], env: { TELEGRAM_BOT_TOKEN: "t", TELEGRAM_CHAT: "@k" }, now: NOW + i * 20 * 60e3, fetch: f, state, log: s => logs.push(s) });
  assert.equal(sent.filter(t => /Türkiy/.test(t)).length, 1, "səfər bir dəfə");
  assert.equal(sent.filter(t => /Polşa/.test(t)).length, 1, "başqa Prezident xəbəri gedir");
  assert.ok(logs.some(s => /eyni mövzu artıq paylaşılıb/.test(s)));
  const T = (a, h = 0) => S.topicOf(a, NOW / 1000 + h * 3600);
  assert.ok(!S.sameTopic(T(visit[0]), T(p("c1", "Türkiyə Prezidenti Ərdoğan Azərbaycana rəsmi səfərə gəlib", 0, "Türkiyə Respublikasının Prezidenti Rəcəb Tayyib Ərdoğan Azərbaycana rəsmi səfərə gəlib."), -6)), "səhər Ərdoğanın səfəri ≠ axşam Əliyevin səfəri");
  assert.ok(!S.sameTopic(T(visit[0]), T(art("c2", { title: "COP31 çərçivəsində ÜST ilə dəyirmi masa keçirilib", summary: "Ümumdünya Səhiyyə Təşkilatı ilə birgə dəyirmi masa. " + sum }))), "xülasədəki ortaq COP31 cümləsi tək başına bəs deyil");
});
