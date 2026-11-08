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
  const src = fs.readFileSync(path.join(root, "assets/ga.js"), "utf8").replace(/^export /gm, "") + "\n;({ hit, pageUrl, isBot })";
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
  assert.ok(app.includes('import("./ga.js?v=3")') && app.includes("gaOn = 1; gaFlush();"), 'ga.js yalnız enableAnalytics-dən sonra (afterNews)');
  for (const f of ["assets/app.js", "index.html", "assets/config.js"]) assert.ok(!/googletagmanager|gtag\/js/.test(fs.readFileSync(path.join(root, f), "utf8")), f + ': Google-un ağır skripti yoxdur');
  assert.ok(fs.statSync(path.join(root, "assets/ga.js")).size < 4000, 'göndərici kiçik qalır');
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
  assert.ok(app.includes("gaQ.push([visitPath(), document.title, void 0, path]); gaFlush();"), "trackEvent GA4-ə də gedir");
  assert.ok(app.includes('trackEvent("out-" + a.host)'), "mənbəyə (başqa sayta) keçid sayılır");
});

test("ga4: automated visits (webdriver, headless, crawlers, no screen) are not counted; real phones are", () => {
  const { api, sent } = load();
  const chrome = "Mozilla/5.0 (Linux; Android 14; SM-A546B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0 Mobile Safari/537.36";
  const scr = { width: 390, height: 844 };
  assert.equal(api.isBot({ userAgent: chrome }, scr), false);
  assert.equal(api.isBot({ userAgent: "Mozilla/5.0 (Linux; Android 13; CUBOT X30) Chrome/130.0 Mobile" }, scr), false, "Cubot telefonu");
  assert.equal(api.isBot({ userAgent: "Mozilla/5.0 (iPhone; CPU iPhone OS 18_0 like Mac OS X) Safari/604.1" }, scr), false);
  for (const ua of ["Mozilla/5.0 (X11; Linux x86_64) HeadlessChrome/130.0 Safari/537.36", "Mozilla/5.0 (compatible; Googlebot/2.1)",
    "Mozilla/5.0 (compatible; bingbot/2.0)", "Chrome-Lighthouse", "facebookexternalhit/1.1", "python-requests/2.32", "curl/8.4"])
    assert.equal(api.isBot({ userAgent: ua }, scr), true, ua);
  assert.equal(api.isBot({ userAgent: chrome, webdriver: true }, scr), true, "idarə olunan brauzer");
  assert.equal(api.isBot({ userAgent: chrome }, { width: 0, height: 0 }), true, "ekransız");
  api.hit("G-NHSDLY61CD", "/", "8ulduz");
  assert.equal(sent.length, 1, "adi oxucu sayılır");
});
