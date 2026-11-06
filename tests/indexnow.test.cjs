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
  const live = async (url, init) => init.method === "HEAD" ? { status: 200 } : (posts.push(JSON.parse(init.body)), { status: 200 });
  await I.run({ index, state, key: "k".repeat(32), now: NOW + 60e3, fetch: live, log: () => {} });
  assert.deepEqual(posts[1].urlList, [`https://8ulduz.az/xeber/${"d".repeat(16)}/`], "yayımlanandan sonra yalnız o; bildirilənlər təkrar getmir");
});

test("indexnow: the key file in the site root holds its own name", () => {
  const key = I.keyOf(path.join(__dirname, ".."));
  assert.match(key, /^[0-9a-f]{32}$/);
  assert.equal(fs.readFileSync(path.join(__dirname, "..", `${key}.txt`), "utf8").trim(), key);
});
