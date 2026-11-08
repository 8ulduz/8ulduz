#!/usr/bin/env node
// Daimi xəbər arxivi (sahib, 2026-11-07: «100 000 əlavə faylda da yayım və sayt ağırlaşmasın»).
// Paylaşılan keçid günlər sonra da açılsın deyə hər xəbərin sətri saxlanır, amma main-ə (GitHub Pages) heç bir fayl əlavə olunmur:
// sətirlər ayrıca «arxiv» budağındadır, saata görə bir fayl (saat/YYMMDDHH.json — xəbərin publishedAt sətrindəki saat, sayt da
// keçidə ?h= ilə eyni saatı yazır). Gündə 24 fayl; budaq tarixçəsizdir (hər yazı valideynsiz bir commit), repo şişmir.
// Sayt faylı raw.githubusercontent.com-dan yalnız köhnə keçid açılanda oxuyur (app.js arxRow). Bu iş xəbər pipeline-ından ayrıdır
// (.github/workflows/arxiv.yml): düşsə də lent dayanmır. Mənbə saytın öz yayımlanmış lentləridir (onsuz da content_policy-dən keçib);
// burada da app.js policyViolation yoxlanır, sayt da göstərəndə yoxlayır.
"use strict";
const fs = require("node:fs"), path = require("node:path"), { execFileSync } = require("node:child_process");

const SITE = "https://8ulduz.az/";
const FEEDS = ["news.json", "news.en.json", "news.ru.json", "news.tr.json"];
const KEEP_DAYS = 400, BRANCH = "arxiv";
const FIELDS = ["id", "title", "summary", "source", "sourceUrl", "imageUrl", "category", "publishedAt", "lang", "video", "author"];

// Saytdakı app.js ilə eyni: "2026-11-07T13:05:00+04:00" -> "26110713" (sətrin öz yazılışı, saat qurşağı çevrilmir).
const hourOf = iso => { const m = String(iso || "").match(/^20(\d\d)-(\d\d)-(\d\d)T(\d\d)/); return m ? m.slice(1).join("") : ""; };

function compact(a) {
  const row = {};
  for (const k of FIELDS) if (a[k]) row[k] = k === "summary" ? String(a[k]).slice(0, 600) : a[k];
  const alts = (a.alts || []).filter(x => x?.sourceUrl).slice(0, 20).map(x => { const r = {}; for (const k of ["id", "title", "source", "sourceUrl"]) if (x[k]) r[k] = x[k]; return r; });
  if (alts.length) row.alts = alts;
  return row;
}

// Yeni sətirləri saat qovluqlarına paylayır. buckets: { saat: {id: sətir} } — dəyişən saatların siyahısını qaytarır.
function merge(buckets, articles, ok = () => true) {
  const changed = new Set();
  for (const a of articles) {
    if (!/^[0-9a-f]{16}$/.test(String(a?.id || "")) || !a.title || !a.sourceUrl || !ok(a)) continue;
    const h = hourOf(a.publishedAt);
    if (!h) continue;
    const b = (buckets[h] ||= {}), row = compact(a), old = b[a.id];
    if (old && JSON.stringify(old) === JSON.stringify(row)) continue;
    b[a.id] = row; changed.add(h);
  }
  return [...changed].sort();
}

const tooOld = (h, now) => { const t = Date.UTC(2000 + +h.slice(0, 2), +h.slice(2, 4) - 1, +h.slice(4, 6), +h.slice(6, 8)); return !(t > now - KEEP_DAYS * 86400e3); };

// Budaqdakı saat faylları: saat -> blob. ls-tree yolu «saat/26110713.json» verir; ad yalnız saatdır (əks halda hamısı «köhnə» sayılıb silinirdi).
function readHours(dir) {
  const out = new Map();
  let list = "";
  try { list = git(dir, ["ls-tree", "HEAD", "saat/"]); } catch { return out; }
  for (const line of list.split("\n").filter(Boolean)) { const [meta, name] = line.split("\t"), sha = meta.split(" ")[2], h = (name.match(/(\d{8})\.json$/) || [])[1]; if (h && sha) out.set(h, sha); }
  return out;
}
// Boşluq (iş düşəndə lentdən çıxmış saatlar): saytın bölmə arxivlərindən (data/arxiv/<bölmə>.json) yalnız budaqda hələ olmayan
// saatların sətirləri. Mövcud saat faylı endirilmir; lentdəki sətir üstündür (eyni id iki dəfə yazılmır).
const gapRows = (rows, have, buckets) => rows.filter(a => { const h = hourOf(a?.publishedAt); return h && !have.has(h) && !buckets[h]?.[a.id]; });

// Saat ağacı və kök ağac. Budaq --filter=blob:none ilə klonlanır: köhnə saatların faylı yerli nüsxədə yoxdur, onlar serverdədir.
// --missing olmadan mktree belə faylı «unavailable» sayıb dayanırdı (2026-11-07 17:00-dan 18 iş düşdü: lentdən çıxmış 26032507.json).
function writeTree(dir, have, other) {
  const saat = git(dir, ["mktree", "--missing"], [...have].sort().map(([h, sha]) => `100644 blob ${sha}\t${h}.json`).join("\n") + "\n");
  return git(dir, ["mktree", "--missing"], [...other, `040000 tree ${saat}\tsaat`].join("\n") + "\n");
}
const git = (dir, args, input) => execFileSync("git", ["-C", dir, ...args], { input, encoding: "utf8", maxBuffer: 64 << 20 }).trim();

async function main(root, dir) {
  const { loadApp } = require("./topics.cjs");
  const app = loadApp(root), now = Date.now();
  const get = async f => { try { const r = await fetch(`${SITE}data/${f}?t=${now}`, { signal: AbortSignal.timeout(30000) }); return r.ok ? (await r.json()).articles || [] : []; } catch { return []; } };
  const articles = (await Promise.all(FEEDS.map(get))).flat();
  if (articles.length < 50) { console.log(`arxiv: lent alınmadı (${articles.length}), dayanıram`); return; }
  const sections = (await Promise.all([...new Set(articles.map(a => a.category).filter(c => /^[a-z]+$/.test(String(c))))].map(c => get(`arxiv/${c}.json`)))).flat();
  // Mövcud budaq (dir: --filter=blob:none ilə klonlanıb; yalnız lazım olan saatların faylı endirilir).
  const have = new Map(), other = [];
  // saat/ xaricindəki qovluqlar (idx/: köhnə saatsız keçidlərin göstəricisi, bir dəfə yazılıb) olduğu kimi qalır.
  try { for (const line of git(dir, ["ls-tree", "HEAD"]).split("\n").filter(Boolean)) if (!/\tsaat$/.test(line)) other.push(line); } catch {}
  for (const [h, sha] of readHours(dir)) have.set(h, sha);
  const buckets = {}, touched = new Set(articles.map(a => hourOf(a.publishedAt)).filter(Boolean));
  for (const h of touched) if (have.has(h)) { try { buckets[h] = Object.fromEntries((JSON.parse(git(dir, ["cat-file", "blob", have.get(h)])).articles || []).map(r => [r.id, r])); } catch {} }
  const ok = a => !app.policyViolation(a);
  const changed = [...new Set([...merge(buckets, articles, ok), ...merge(buckets, gapRows(sections, have, buckets), ok)])].sort();
  for (const h of changed) {
    const body = JSON.stringify({ h, articles: Object.values(buckets[h]).sort((x, y) => String(x.publishedAt).localeCompare(String(y.publishedAt))) });
    have.set(h, git(dir, ["hash-object", "-w", "--stdin"], body));
  }
  let dropped = 0;
  for (const h of [...have.keys()]) if (tooOld(h, now)) { have.delete(h); dropped++; }
  if (!changed.length && !dropped) { console.log("arxiv: dəyişiklik yoxdur"); return; }
  const tree = writeTree(dir, have, other);
  const commit = git(dir, ["-c", "user.name=8ulduz-bot", "-c", "user.email=bot@8ulduz.az", "commit-tree", tree, "-m", "Xəbər arxivi"]);
  git(dir, ["push", "-q", "--force", "origin", `${commit}:refs/heads/${BRANCH}`]);
  console.log(`arxiv: ${articles.length} sətir, ${changed.length} saat yeniləndi, ${have.size} saat budaqda, ${dropped} köhnə silindi`);
}

module.exports = { hourOf, compact, merge, tooOld, readHours, gapRows, writeTree, main, KEEP_DAYS };
if (require.main === module) main(path.resolve(process.argv[2] || "."), path.resolve(process.argv[3] || ".arxiv")).catch(e => { console.error("arxiv:", e?.message || e); process.exitCode = 1; });
