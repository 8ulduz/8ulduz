// assets/ga.js: GA4 yüngül göndərici (sahib, 2026-11-06: əsas statistika GA4, sürət qorunsun).
const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("fs"), path = require("path"), vm = require("vm");
const root = path.join(__dirname, "..");

function load({ stored = null, ref = "", host = "8ulduz.az" } = {}) {
  const sent = [], store = new Map(stored ? [["8ulduz-ga", JSON.stringify(stored)]] : []), timers = [];
  const ctx = { URLSearchParams, JSON, Math, String, Date, console,
    location: { origin: "https://" + host, hostname: host, search: "?utm_source=telegram" },
    document: { referrer: ref, visibilityState: "visible" },
    navigator: { language: "az-AZ", sendBeacon: u => (sent.push(u), true) },
    screen: { width: 390, height: 844 },
    localStorage: { getItem: k => store.get(k) ?? null, setItem: (k, v) => store.set(k, v) },
    setTimeout: (f, ms) => timers.push([f, ms]), fetch: async () => {} };
  const src = fs.readFileSync(path.join(root, "assets/ga.js"), "utf8").replace(/^export /gm, "") + "\n;({ hit, pageUrl, news })";
  return { api: vm.runInNewContext(src, ctx), sent, store, timers };
}
const params = u => Object.fromEntries(new URL(u).searchParams);

test("ga4: first visit sends page_view with new-user and session-start flags; route becomes a path", () => {
  const { api, sent, store, timers } = load({ ref: "https://t.me/sekkizulduz_az" });
  api.hit("G-NHSDLY61CD", "/#/bolme/gundem", "Gündəm — 8ulduz", Date.parse("2026-11-06T16:00:00Z"));
  assert.equal(sent.length, 1);
  assert.ok(sent[0].startsWith("https://www.google-analytics.com/g/collect?"));
  const p = params(sent[0]);
  assert.equal(p.tid, "G-NHSDLY61CD"); assert.equal(p.en, "page_view"); assert.equal(p.v, "2");
  assert.equal(p.dl, "https://8ulduz.az/bolme/gundem?utm_source=telegram", 'hash marşrutu hesabatda səhifə yolu kimi');
  assert.equal(p._fv, "1"); assert.equal(p._ss, "1"); assert.equal(p.sct, "1"); assert.equal(p.dr, "https://t.me/sekkizulduz_az");
  assert.match(p.cid, /^\d+\.\d+$/);
  const saved = JSON.parse(store.get("8ulduz-ga"));
  assert.equal(saved.cid, p.cid);
  assert.equal(timers.length, 1, '10 saniyədən sonra fəal sessiya hadisəsi');
  timers[0][0]();
  const e = params(sent[1]);
  assert.equal(e.en, "user_engagement"); assert.equal(e.seg, "1"); assert.equal(e._fv, undefined);
});

test("ga4: returning reader keeps the id; a new session after 30 minutes, none before", () => {
  const t = Date.parse("2026-11-06T16:00:00Z");
  const { api, sent } = load({ stored: { cid: "123.456", sid: t / 1000 - 600, sct: 4, last: t - 5 * 60e3 } });
  api.hit("G-NHSDLY61CD", "/", "8ulduz", t);
  let p = params(sent[0]);
  assert.equal(p.cid, "123.456"); assert.equal(p._fv, undefined); assert.equal(p._ss, undefined, 'eyni sessiya'); assert.equal(p.sct, "4");
  assert.equal(p.dl, "https://8ulduz.az/?utm_source=telegram");
  api.hit("G-NHSDLY61CD", "/#/axtar?q=gizli", "Axtarış", t + 31 * 60e3);
  p = params(sent[1]);
  assert.equal(p._ss, "1"); assert.equal(p.sct, "5"); assert.equal(p.dr, undefined, 'mənbə yalnız ilk baxışda');
  assert.equal(p.dl, "https://8ulduz.az/axtar?utm_source=telegram", 'axtarılan söz Google-a getmir');
});

test("ga4: bad id sends nothing; the site loads the sender only after it is shown and keeps gtag.js out", () => {
  const { api, sent } = load();
  assert.equal(api.hit("", "/", "x"), null); assert.equal(api.hit("UA-1", "/", "x"), null); assert.equal(sent.length, 0);
  const local = load({ host: "localhost" });
  assert.equal(local.api.hit("G-NHSDLY61CD", "/", "x"), null, "yerli sınaq GA4-ə getmir"); assert.equal(local.sent.length, 0);
  const app = fs.readFileSync(path.join(root, "assets/app.js"), "utf8"), cfg = fs.readFileSync(path.join(root, "assets/config.js"), "utf8");
  assert.ok(cfg.includes('ga4: "G-NHSDLY61CD"'));
  assert.ok(app.includes('import("./ga.js?v=4")') && app.includes("gaOn = 1; gaFlush();"), 'ga.js yalnız enableAnalytics-dən sonra (afterNews)');
  for (const f of ["assets/app.js", "index.html", "assets/config.js"]) assert.ok(!/googletagmanager|gtag\/js/.test(fs.readFileSync(path.join(root, f), "utf8")), f + ': Google-un ağır skripti yoxdur');
  assert.ok(fs.statSync(path.join(root, "assets/ga.js")).size < 4500, 'göndərici kiçik qalır');
  assert.ok(fs.readFileSync(path.join(root, "mexfilik/index.html"), "utf8").includes("Google Analytics 4"), 'məxfilik səhifəsində yazılıb');
});

test("ga4: clicks to sources, shares and installs are counted as events (owner 2026-11-07: measure click-throughs)", () => {
  const { api, sent, timers } = load({ stored: { cid: "1.2", sid: 1793990000, sct: 3, last: Date.parse("2026-11-07T08:00:00Z") } });
  api.hit("G-NHSDLY61CD", "/#/bolme/gundem", "Gündəm — 8ulduz", Date.parse("2026-11-07T08:01:00Z"), "out-apa.az");
  api.hit("G-NHSDLY61CD", "/", "8ulduz", Date.parse("2026-11-07T08:02:00Z"), "share-wa");
  let p = params(sent[0]);
  assert.equal(p.en, "out"); assert.equal(p["ep.type"], "apa.az"); assert.equal(p.dl, "https://8ulduz.az/bolme/gundem?utm_source=telegram");
  assert.equal(p._fv, undefined); assert.equal(p.dr, undefined); assert.equal(p.cid, "1.2");
  p = params(sent[1]);
  assert.equal(p.en, "share"); assert.equal(p["ep.type"], "wa");
  assert.equal(timers.length, 0, "hadisə fəal sessiya taymerini başlatmır");
  const app = fs.readFileSync(path.join(root, "assets/app.js"), "utf8");
  assert.ok(app.includes("gaQ.push([visitPath(), document.title, void 0, path, a]); gaFlush();"), "trackEvent GA4-ə də gedir");
  assert.ok(app.includes('trackEvent("out-" + a.host, a)'), "mənbəyə (başqa sayta) keçid sayılır");
});

// Sahib 2026-11-11: xəbər keçidi ayrıca hadisədir, domen/keçid/başlıq ilə; hər klik bir hadisə.
const link = (href, { inner = null, art, list = false, cls = "" } = {}) => { const u = new URL(href); return { href, hostname: u.hostname, matches: s => !!cls && s.includes(cls), textContent: "  Şəkil başlığı ",
  querySelector: () => inner && { textContent: inner, querySelector: () => /^Birinci/.test(inner) ? { textContent: "Birinci xanım" } : null }, closest: s => s === "article" ? (art === undefined ? null : { querySelector: () => art ? { textContent: art } : null }) : list ? {} : null }; };

test("ga4: a news link is one news_outbound_click with domain, full link and headline; other links stay «out»", () => {
  const t = Date.parse("2026-11-11T12:00:00Z"), { api, sent } = load({ stored: { cid: "1.2", sid: t / 1000 - 60, sct: 1, last: t - 1e3 } });
  const go = (ev, a) => api.hit("G-NHSDLY61CD", "/", "8ulduz", t, ev, a);
  go("out-www.apa.az", link("https://www.APA.az/siyasi/xeber-123?x=1", { inner: " Prezident səfərə gedib ", art: "" })); // kart: başlıq keçidin içindədir
  go("out-report.az", link("https://report.az/a/1", { art: "Xəbər səhifəsinin başlığı" })); // xəbər səhifəsi: «mənbədə oxu» düyməsi
  go("out-trend.az", link("https://trend.az/p/9", { list: true })); // günün şəkilləri, qaçan sətir: başlıq keçidin öz mətnidir
  go("out-t.me", link("https://t.me/sekkizulduz_az")); // xəbər deyil
  go("out-www.facebook.com", link("https://www.facebook.com/p/1", { inner: "Post", art: "", cls: ".soc-p" })); // sosial post xəbər deyil
  go("share-wa", link("https://www.apa.az/x", { inner: "Başlıq", art: "" })); // paylaşma keçid deyil
  assert.equal(sent.length, 6, "hər klik bir hadisə");
  const p = sent.map(params);
  assert.deepEqual(p.map(x => x.en), ["news_outbound_click", "news_outbound_click", "news_outbound_click", "out", "out", "share"]);
  assert.equal(p[0]["ep.news_domain"], "apa.az", "www-siz, kiçik hərflə: bir sayt bir sətir");
  assert.equal(p[0]["ep.news_url"], "https://www.APA.az/siyasi/xeber-123?x=1"); assert.equal(p[0]["ep.news_title"], "Prezident səfərə gedib");
  assert.equal(p[0]["ep.type"], undefined, "xəbər keçidi «out» kimi ikinci dəfə sayılmır");
  assert.equal(p[1]["ep.news_title"], "Xəbər səhifəsinin başlığı"); assert.equal(p[2]["ep.news_title"], "Şəkil başlığı"); assert.equal(p[2]["ep.news_domain"], "trend.az");
  assert.equal(p[3]["ep.type"], "t.me"); assert.equal(p[3]["ep.news_domain"], undefined); assert.equal(p[4]["ep.type"], "www.facebook.com");
  const long = params(go("out-a.az", link("https://a.az/" + "x".repeat(300), { inner: "b".repeat(300), art: "" })).toString().replace(/^/, "https://x/?"));
  assert.equal(long["ep.news_url"].length, 100); assert.equal(long["ep.news_title"].length, 100, "GA4 həddi: 100 işarə");
  assert.equal(api.news(link("https://president.az/az/articles/view/1", { inner: "Birinci xanımPrezident Sammitdə iştirak edib", art: "" }))[2], "Prezident Sammitdə iştirak edib", "kart etiketi başlığa yapışmır");
  assert.equal(api.news(null), null); assert.equal(api.news({}), null);
  const app = fs.readFileSync(path.join(root, "assets/app.js"), "utf8");
  assert.ok(app.includes('for (const t of ["click", "auxclick"]) addEventListener(t, e =>') && app.includes("e.button < 2) trackEvent("), "orta düymə sayılır, sağ düymə yox");
  for (const c of ["card-hit", "pcard-hit", "source-entry"]) assert.match(app, new RegExp(`<article[^]*?class="${c}"`), c + " <article> içindədir: xəbər keçidi kimi tanınır");
  for (const c of ["phrow", "track", "alerts", "foot-news"]) assert.ok(app.includes(`class="${c}`), c + ": xəbər keçidi olan siyahı");
});

test("ga4: with storage blocked the reader stays one user and one session for the page's lifetime", () => {
  const { api, sent } = load();
  const blocked = { getItem() { throw new Error("blocked"); }, setItem() { throw new Error("blocked"); } };
  const src = fs.readFileSync(path.join(root, "assets/ga.js"), "utf8").replace(/^export /gm, "") + "\n;({ hit })";
  const out = [], t0 = Date.parse("2026-11-06T16:00:00Z");
  const g = vm.runInNewContext(src, { URLSearchParams, JSON, Math, String, Date, console, location: { origin: "https://8ulduz.az", hostname: "8ulduz.az", search: "" },
    document: { referrer: "", visibilityState: "visible" }, navigator: { language: "az-AZ", sendBeacon: u => (out.push(u), true) }, screen: { width: 390, height: 844 },
    localStorage: blocked, setTimeout() {}, fetch: async () => {} });
  g.hit("G-NHSDLY61CD", "/", "8ulduz", t0); g.hit("G-NHSDLY61CD", "/#/bolme/gundem", "Gündəm", t0 + 20e3); g.hit("G-NHSDLY61CD", "/#/bolme/idman", "İdman", t0 + 40e3);
  const p = out.map(params);
  assert.equal(new Set(p.map(x => x.cid)).size, 1, "eyni oxucu");
  assert.deepEqual(p.map(x => [x._fv, x._ss]), [["1", "1"], [undefined, undefined], [undefined, undefined]], "yalnız ilk baxış yeni istifadəçi və yeni sessiyadır");
  assert.ok(api && sent.length === 0);
});
