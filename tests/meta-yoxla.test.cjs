// .github/scripts/meta-yoxla.cjs: Meta açarı və paylaşımların görünməsi. Şəbəkə yoxdur: Graph API testdə saxtadır.
const test = require("node:test");
const assert = require("node:assert/strict");
const M = require("../.github/scripts/meta-yoxla.cjs");

const NOW = Date.parse("2026-11-23T12:00:00Z");
const USER = "EAAuser-token-" + "u".repeat(40), PAGE = "EAApage-token-" + "p".repeat(40);
const ALL = [...Object.keys(M.REQUIRED), ...Object.keys(M.COMMENT), ...Object.keys(M.STATS), "business_management"];
const ago = h => new Date(NOW - h * 3600e3).toISOString().replace(/\.\d+Z$/, "+0000");

// Saxta Graph API: yol → cavab. Hər sorğu yadda qalır (açar hansı sorğuya getdi).
function graph({ scopes = ALL, valid = true, type = "USER", expires = 0, dataAccess = NOW / 1000 + 80 * 86400, tasks = ["ADVERTISE", "ANALYZE", "CREATE_CONTENT", "MESSAGING", "MODERATE", "MANAGE"],
  fb = [[30, 120, 95], [20, 60, 40], [1, 2, 1]], ig = [[30, 400, 300], [20, 200, 150]], insightsError = false } = {}) {
  const calls = [];
  const f = async url => {
    const u = new URL(url), p = u.pathname.replace(/^\/v[\d.]+\//, ""), q = Object.fromEntries(u.searchParams);
    calls.push({ p, q });
    const ok = body => ({ ok: true, status: 200, json: async () => body });
    if (p === "debug_token") return ok(valid ? { data: { is_valid: true, type, app_id: "1000332509080909", application: "8ulduz paylasma", expires_at: expires, data_access_expires_at: dataAccess, scopes } }
      : { data: { is_valid: false, error: { message: "Session has expired" } } });
    if (p === "me/accounts") return ok({ data: [{ id: "1470250006171917", name: "8ulduz", tasks }] });
    if (p === "1470250006171917") return ok({ id: "1470250006171917", name: "8ulduz", followers_count: 812, access_token: PAGE, instagram_business_account: { id: "1784" } });
    if (p === "1470250006171917/video_reels") return ok({ data: fb.map(([h], i) => ({ id: `v${i}`, created_time: ago(h), description: `Başlıq ${i}\n\nmətn`, permalink_url: `/reel/v${i}` })) });
    const v = p.match(/^v(\d+)\/video_insights$/);
    if (v) return ok(insightsError ? { error: { message: "(#10) read_insights lazımdır" } }
      : { data: [{ name: "blue_reels_play_count", values: [{ value: fb[v[1]][1] }] }, { name: "post_impressions_unique", values: [{ value: fb[v[1]][2] }] }] });
    const s = p.match(/^v(\d+)$/);
    if (s) return ok({ likes: { summary: { total_count: 3 } }, comments: { summary: { total_count: 0 } } });
    if (p === "1784/media") return ok({ data: ig.map(([h], i) => ({ id: `m${i}`, caption: `IG ${i}`, media_product_type: "REELS", permalink: `https://instagram.com/reel/m${i}`, timestamp: ago(h), like_count: 5, comments_count: 1 })) });
    const m = p.match(/^m(\d+)\/insights$/);
    if (m) return ok({ data: [{ name: "views", values: [{ value: ig[m[1]][1] }] }, { name: "reach", values: [{ value: ig[m[1]][2] }] }] });
    return ok({ error: { message: `naməlum: ${p}` } });
  };
  return { f, calls };
}
const env = { FB_PAGE_TOKEN: USER, FB_PAGE_ID: "1470250006171917" };

test("a healthy key: no problem, stats per video, and neither key ever appears in the report", async () => {
  const g = graph();
  const out = await M.check({ env, f: g.f, now: NOW });
  assert.deepEqual(out.fail, []);
  assert.deepEqual(out.warn, []);
  assert.equal(out.fb.length, 3);
  assert.equal(out.fb[0].plays, 120);
  assert.equal(out.ig[0].reach, 300);
  const text = M.report(out);
  assert.ok(!text.includes(USER) && !text.includes(PAGE), "açar hesabata düşməsin");
  assert.match(text, /Problem yoxdur/);
  assert.match(text, /\| 120 \| 95 \|/);
  // Səhifənin videoları səhifə açarı ilə oxunur, açarın özü yalnız debug_token və səhifə üçün.
  for (const c of g.calls.filter(c => /video_reels|insights|^v\d|media/.test(c.p))) assert.equal(c.q.access_token, PAGE, c.p);
});

test("the comment permissions that Meta asked for on 2026-11-23 are reported as a warning, not a failure", async () => {
  const g = graph({ scopes: ALL.filter(s => !M.COMMENT[s]) });
  const out = await M.check({ env, f: g.f, now: NOW });
  assert.deepEqual(out.fail, []);
  assert.equal(out.warn.length, 1);
  assert.match(out.warn[0], /pages_manage_engagement/);
  assert.match(out.warn[0], /pages_read_user_content/);
});

test("a missing posting permission, an expired key or a key without page rights fails the job", async () => {
  let out = await M.check({ env, f: graph({ scopes: ALL.filter(s => s !== "pages_manage_posts") }).f, now: NOW });
  assert.match(out.fail.join(" "), /pages_manage_posts/);
  out = await M.check({ env, f: graph({ valid: false }).f, now: NOW });
  assert.match(out.fail.join(" "), /etibarsız.*Session has expired/);
  out = await M.check({ env, f: graph({ dataAccess: NOW / 1000 - 60 }).f, now: NOW });
  assert.match(out.fail.join(" "), /məlumat girişi/);
  out = await M.check({ env, f: graph({ tasks: ["ANALYZE"] }).f, now: NOW });
  assert.match(out.fail.join(" "), /CREATE_CONTENT/);
  assert.match(out.warn.join(" "), /MODERATE/);
  out = await M.check({ env: { FB_PAGE_ID: "1" }, f: graph().f, now: NOW });
  assert.match(out.fail.join(" "), /FB_PAGE_TOKEN/);
});

test("expiry within two weeks is a warning", async () => {
  const out = await M.check({ env, f: graph({ dataAccess: NOW / 1000 + 5 * 86400 }).f, now: NOW });
  assert.deepEqual(out.fail, []);
  assert.match(out.warn.join(" "), /məlumat girişi 2026-11-28/);
});

test("Facebook reels nobody but the app's own people saw (while Instagram has viewers) point to Development mode", async () => {
  const out = await M.check({ env, f: graph({ fb: [[30, 1, 1], [20, 0, 0], [10, 2, 1], [1, 0, 0]] }).f, now: NOW });
  assert.equal(out.fail.length, 1);
  assert.match(out.fail[0], /Development rejimi/);
  assert.match(out.fail[0], /son 3 videonu ən çox 2 nəfər/);
  assert.match(out.fail[0], /Instagram-da eyni videoları 400/);
});

test("fresh videos do not count, and without statistics there is no guess", async () => {
  let out = await M.check({ env, f: graph({ fb: [[2, 0, 0], [1, 0, 0]] }).f, now: NOW });
  assert.deepEqual(out.fail, []);
  out = await M.check({ env, f: graph({ fb: [[30, 0, 0], [20, 0, 0]], insightsError: true }).f, now: NOW });
  assert.deepEqual(out.fail, []);
  assert.match(out.info.join(" "), /baxış statistikası alınmadı/);
  assert.match(M.report(out), /Statistika xətası: \(#10\)/);
});

test("a page token (not a user token) is checked without the user-only page list", async () => {
  const g = graph({ type: "PAGE" });
  const out = await M.check({ env: { ...env, FB_PAGE_TOKEN: PAGE }, f: g.f, now: NOW });
  assert.deepEqual(out.fail, []);
  assert.ok(!g.calls.some(c => c.p === "me/accounts"));
});
