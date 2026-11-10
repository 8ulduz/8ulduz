// Google indeks: ana səhifənin statik HTML-i (JS-dən əvvəl) /xeber/ keçidləri daşıyır.
"use strict";
const { test } = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");

const root = path.join(__dirname, "..");
const read = f => fs.readFileSync(path.join(root, f), "utf8");

test("homepage static HTML links /xeber/ pages before JavaScript", () => {
  const html = read("index.html");
  const hrefs = html.match(/href="\/xeber\/[0-9a-f]{16}\/"/g) || [];
  assert.ok(hrefs.length >= 1, "index.html-də /xeber/<id>/ keçidi yoxdur");
  assert.equal(html.includes('href="#/xeber/'), false, "xəbər nişanı hash ünvanı qalmamalıdır");
  assert.ok(html.includes('href="/bolme/gundem/"'), "bölmə menyusu həqiqi /bolme/ ünvanıdır");
  assert.ok(html.includes('Telegram-a qoşul') && html.includes('href="https://t.me/sekkizulduz_az"'), "Telegram düyməsi");
  assert.equal(read("assets/config.js").includes("https://t.me/KANAL"), false, "KANAL yer tutucusu silinməlidir");
  const app = read("assets/app.js");
  assert.ok(app.includes('href="${storyHref(a)}"') && app.includes("`/xeber/${a.id}/`"), "N mənbə nişanı /xeber/ ünvanıdır");
  assert.ok(app.includes('location.hash = "#/" + m[1] + "/" + m[2]'), "klik tətbiqin içindəki ünvana keçir");
});
