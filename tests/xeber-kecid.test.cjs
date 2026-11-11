// Googlebot ana səhifənin statik HTML-ində /xeber/ və /bolme/ keçidlərini görməlidir.
"use strict";
const { test } = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");

const root = path.join(__dirname, "..");
const read = f => fs.readFileSync(path.join(root, f), "utf8");

test("homepage static HTML links /xeber/ and /bolme/ before JavaScript", () => {
  const html = read("index.html");
  const stories = html.match(/href="\/xeber\/[0-9a-f]{16}\/"/g) || [];
  assert.ok(stories.length >= 1, "index.html-də /xeber/<id>/ keçidi yoxdur");
  assert.equal(html.includes('href="#/xeber/'), false);
  assert.ok(html.includes('href="/bolme/gundem/"'), "bölmə menyusu /bolme/ ünvanıdır");
  assert.equal(html.includes('href="#/bolme/'), false);
  const app = read("assets/app.js");
  assert.ok(app.includes('href="/xeber/${a.id}/"'), "N mənbə nişanı xəbər səhifəsinə aparır");
  assert.ok(app.includes('safeHref(a.sourceUrl)'), "başlıq yenə mənbəni açır");
  assert.ok(app.includes('location.hash = "#/" + m[1] + "/" + m[2]'), "klik tətbiqin içində qalır");
});
