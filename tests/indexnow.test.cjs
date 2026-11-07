// .github/scripts/indexnow.cjs: yeni xəbər səhifələri Bing/Yandex-ə (2026-11-06).
const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("fs"), path = require("path");
const I = require("../.github/scripts/indexnow.cjs");

const NOW = Date.parse("2026-11-06T12:00:00Z"), T = NOW / 1000;

test("indexnow: only new, published story pages younger than 31 days are sent, once", async () => {
  const index = { ["a".repeat(16)]: [T - 60, 4, "gundem"], ["b".repeat(16)]: [T - 120, 5, "idman"], ["c".repeat(16)]: [T - 32 * 86400, 4, "gundem"], ["d".repeat(16)]: [T - 30, 4, "gundem"] };
  const posts = [];
  const fetch = async (url, init) => {
    if (init.method === "GET") return { status: 200, text: async () => "k".repeat(32) };
    if (init.method === "HEAD") return { status: url.includes("d".repeat(16)) ? 404 : 200 };
    posts.push(JSON.parse(init.body));
    return { status: 202 };
  };
  const state = {};
  const ids = await I.run({ index, state, key: "k".repeat(32), now: NOW, fetch, log: () => {} });
  assert.deepEqual(ids, ["a".repeat(16), "b".repeat(16)], "köhnə (32 gün) və hələ yayımlanmayan (404) səhifə yox");
  assert.equal(posts[0].host, "8ulduz.az");
  assert.equal(posts[0].keyLocation, `https://8ulduz.az/${"k".repeat(32)}.txt`);
  assert.deepEqual(posts[0].urlList, [`https://8ulduz.az/xeber/${"a".repeat(16)}/`, `https://8ulduz.az/xeber/${"b".repeat(16)}/`]);
  const live = async (url, init) => init.method === "GET" ? { status: 200, text: async () => "k".repeat(32) }
    : init.method === "HEAD" ? { status: 200 } : (posts.push(JSON.parse(init.body)), { status: 200 });
  await I.run({ index, state, key: "k".repeat(32), now: NOW + 60e3, fetch: live, log: () => {} });
  assert.deepEqual(posts[1].urlList, [`https://8ulduz.az/xeber/${"d".repeat(16)}/`], "yayımlanandan sonra yalnız o; bildirilənlər təkrar getmir");
});

test("indexnow: a missing or wrong deployed key postpones submission until publication", async () => {
  const id = "e".repeat(16), key = "k".repeat(32), index = { [id]: [T - 60, 4, "gundem"] };
  for (const proof of [{ status: 404 }, { status: 200, text: async () => "old key" }]) {
    const state = {}, requests = [];
    const unavailable = async (url, init) => { requests.push(init.method); return proof; };
    assert.deepEqual(await I.run({ index, state, key, now: NOW, fetch: unavailable, log: () => {} }), []);
    assert.deepEqual(requests, ["GET"], "neither news probes nor notifications run before the ownership proof is live");
    assert.deepEqual(state.sent, {}, "postponed pages remain eligible for the next run");
    const live = async (url, init) => init.method === "GET" ? { status: 200, text: async () => key }
      : { status: init.method === "HEAD" ? 200 : 202 };
    assert.deepEqual(await I.run({ index, state, key, now: NOW + 60e3, fetch: live, log: () => {} }), [id]);
  }
});

test("indexnow: a rejected notification preserves pending pages and reports the API error code only", async () => {
  const id = "f".repeat(16), key = "k".repeat(32), state = {};
  const fetch = async (url, init) => init.method === "GET" ? { status: 200, text: async () => key }
    : init.method === "HEAD" ? { status: 200 }
    : { status: 403, json: async () => ({ errorCode: "UserForbiddedToAccessSite", message: `private diagnostic ${key}` }) };
  await assert.rejects(I.run({ index: { [id]: [T - 60, 4, "gundem"] }, state, key, now: NOW, fetch, log: () => {} }),
    { message: "indexnow: HTTP 403 (UserForbiddedToAccessSite)" });
  assert.deepEqual(state.sent, {}, "a rejected URL is never recorded as successfully submitted");
});

test("indexnow: rotating a rejected proof retries recent pages once under the new key", async () => {
  const id = "1".repeat(16), key = "2".repeat(32), index = { [id]: [T - 60, 4, "gundem"] };
  for (const oldKey of [undefined, "3".repeat(32)]) {
    const state = { key: oldKey, sent: { [id]: T - 60 } };
    const fetch = async (url, init) => init.method === "GET" ? { status: 200, text: async () => key }
      : { status: init.method === "HEAD" ? 200 : 202 };
    assert.deepEqual(await I.run({ index, state, key, now: NOW, fetch, log: () => {} }), [id], "old or unversioned delivery state cannot suppress the new ownership proof's notifications");
    assert.equal(state.key, key);
    assert.deepEqual(await I.run({ index, state, key, now: NOW + 60e3, fetch: () => assert.fail("already sent under this key"), log: () => {} }), []);
  }
});

test("indexnow: the key file in the site root holds its own name", () => {
  const key = I.keyOf(path.join(__dirname, ".."));
  assert.match(key, /^[0-9a-f]{32}$/);
  assert.equal(fs.readFileSync(path.join(__dirname, "..", `${key}.txt`), "utf8").trim(), key);
});
