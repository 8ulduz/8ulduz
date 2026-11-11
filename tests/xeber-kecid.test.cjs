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
  assert.ok(app.includes('href="${hasPage(a) ? `/xeber/${a.id}/` : detailUrl(a)}"'), "N mənbə nişanı yalnız səhifəsi olan xəbərdə həqiqi keçiddir (3+ mənbə və ya Zuğulba), qalanı tətbiqin içində");
  assert.ok(app.includes('safeHref(a.sourceUrl)'), "başlıq yenə mənbəni açır");
  assert.ok(app.includes('location.hash = "#/" + m[1]'), "klik tətbiqin içində qalır");
});

// Sahib, 2026-11-11: Cursor-un ilk variantında «N mənbə» nişanı 2 mənbəli kartda da /xeber/<id>/ idi (səhifə yalnız 3+ mənbə və
// Zuğulba üçün yaranır), menyudakı /bolme/sondeqiqe/ və /bolme/video/ səhifələri isə yox idi — Google 404 görərdi.
test("every real /bolme/ link has a page the updater writes; the «N mənbə» badge is a real link only where a story page exists", () => {
  const py = read("updater.py"), app = read("assets/app.js"), html = read("index.html");
  const block = name => { const i = py.indexOf(`\n${name} = [`); assert.ok(i > 0, name); return py.slice(i, py.indexOf("\n]", i)); };
  const pages = new Set([...(block("SECTIONS") + block("SERVICE_PAGES")).matchAll(/^\s+\("([a-z]+)",/gm)].map(m => m[1]));
  for (const m of py.slice(py.indexOf("\nSECTION_ALIASES = {")).split("}")[0].matchAll(/"([a-z]+)":/g)) pages.add(m[1]);
  const cats = [...app.slice(app.indexOf("const CATS = ["), app.indexOf("];", app.indexOf("const CATS = ["))).matchAll(/slug: "([a-z]+)"/g)].map(m => m[1]);
  assert.ok(cats.length >= 12, "CATS oxundu");
  const linked = new Set([...cats, ...[...(html + app).matchAll(/href="\/bolme\/([a-z]+)\/"/g)].map(m => m[1])]);
  assert.deepEqual([...linked].filter(s => !pages.has(s)), [], "bu bölmə keçidlərinin səhifəsi yoxdur (updater SECTIONS / SERVICE_PAGES)");

  const src = app.match(/^const hasPage = .*;\nconst altBadge = .*;$/m)[0];
  const altBadge = new Function("langOf", "detailUrl", `${src}
return altBadge`)(a => a.lang || "az", a => "#/xeber/" + a.id);
  const at = min => new Date(Date.now() - min * 60e3).toISOString();
  const alt = (n, min = 60) => Array.from({ length: n }, (_, i) => ({ source: "S" + i, publishedAt: at(min) }));
  const row = (o = {}) => ({ id: "a".repeat(16), category: "gundem", lang: "az", publishedAt: at(60), ...o });
  assert.ok(altBadge(row({ alts: alt(2), n: 2 })).includes(`href="/xeber/${"a".repeat(16)}/"`), "3 mənbə: səhifə var, həqiqi keçid");
  assert.ok(altBadge(row({ alts: alt(1), n: 1 })).includes('href="#/xeber/'), "2 mənbə: səhifə yoxdur, tətbiqin içində");
  assert.ok(altBadge(row({ alts: alt(3), n: 1 })).includes('href="#/xeber/'), "brauzerdə birləşmiş kart: serverdə 2 mənbə idi, səhifə yoxdur");
  assert.ok(altBadge(row({ alts: alt(1), n: 1, category: "prezident" })).includes('href="/xeber/'), "Zuğulba: həmişə səhifə var");
  assert.ok(altBadge(row({ alts: alt(4), n: 4, lang: "ru" })).includes('href="#/xeber/'), "başqa dil: səhifə yoxdur");
  assert.ok(altBadge(row({ alts: alt(2, 5), n: 2 })).includes('href="#/xeber/'), "3-cü mənbə 5 dəqiqə əvvəl gəlib: səhifə hələ yazılmayıb (10 dəqiqəlik dövrə)");
  assert.ok(altBadge(row({ alts: [...alt(2), ...alt(3, 2)], n: 5 })).includes('href="/xeber/'), "3 mənbə 1 saatdır var, yeniləri indi gəlir: səhifə var");
  assert.ok(altBadge(row({ alts: alt(1), n: 1, category: "prezident", publishedAt: at(3) })).includes('href="#/xeber/'), "təzə Zuğulba xəbəri: səhifə hələ yoxdur");
  assert.ok(altBadge(row({ alts: alt(16), n: 16, publishedAt: at(8) })).includes('href="#/xeber/'), "köhnə hadisənin kartına 8 dəqiqə əvvəl yeni əsas xəbər gəlib (nömrə dəyişib): səhifəsi hələ yoxdur (canlıda 2026-11-11 07:45-də belə 3 keçid 404 idi)");
  assert.equal(altBadge(row()), "", "tək mənbə: nişan yoxdur");
  assert.ok(app.includes("primary = {...primary}; primary.n = primary.alts?.length;"), "n — serverdəki mənbə sayı (brauzer birləşdirməsindən əvvəl)");
});
