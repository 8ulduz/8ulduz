#!/usr/bin/env node
// Rayon və idman mövzu səhifələri (sahib, 2026-11-06): Google «Quba xəbərləri», «Qarabağ futbol xəbərləri» kimi axtarışlarda
// bizi tapsın. Saytda rayon/idman seçimi yalnız düymə ilə idi (ünvan dəyişmirdi), axtarış sistemi onu görmürdü.
// pipeline.sh publish_main hər main yazılışında işlədir: node .github/scripts/topics.cjs <repo>
//   rayon/<slug>/index.html  — Bölgələrin hər bölgəsi və rayonu (app.js REGION_TABS)
//   idman/<slug>/index.html  — İdmanın hər alt bölməsi və komandası (app.js SPORT_TABS)
//   sitemap-movzu.xml        — yalnız ən azı MIN_INDEX xəbəri olan səhifələr (boş səhifə Google-da saytın dəyərini salır)
// Xəbər seçimi app.js-in öz clubMatches()-i ilədir: səhifədəki siyahı saytdakı düymə ilə eynidir, qayda iki yerdə yazılmır.
// Arxiv 1-2 günlükdür; hər səhifə öz siyahısını saxlayır (KEEP_DAYS gün, KEEP xəbər), səhifənin içindəki JSON-dan oxunur.
// Səhifələr skriptsizdir (yüngül, sürət qırmızı xətti); bir səhifə ən çox REWRITE_MS-dən bir yazılır (repo tarixçəsi şişməsin).
"use strict";
const fs = require("node:fs"), path = require("node:path"), vm = require("node:vm");

const SITE = "https://8ulduz.az/";
// «Telegram-da izlə» botu (izle.cjs): adı assets/config.js tgBot-dadır; boşdursa düymə yoxdur.
const botOf = root => { try { return (fs.readFileSync(path.join(root, "assets/config.js"), "utf8").match(/tgBot:\s*"([A-Za-z0-9_]{5,32})"/) || [])[1] || ""; } catch { return ""; } };
const KEEP_DAYS = 30, KEEP = 30, MIN_INDEX = 3, REWRITE_MS = 60 * 60e3;
const KINDS = { rayon: { tabs: "REGION_TABS", section: "bolgeler", label: "Bölgələr" }, idman: { tabs: "SPORT_TABS", section: "idman", label: "İdman" } };

// Lentdəki başlıqlarda HTML işarələri qala bilir (&quot;): əvvəl açılır, sonra bir dəfə qaçırılır.
const NAMED = { amp: "&", lt: "<", gt: ">", quot: "\"", apos: "'", nbsp: " ", ndash: "–", mdash: "—", laquo: "«", raquo: "»", hellip: "…", ldquo: "“", rdquo: "”", lsquo: "‘", rsquo: "’" };
const unent = s => String(s ?? "").replace(/&(#x[0-9a-f]+|#\d+|[a-z]+);/gi, (m, e) => e[0] === "#" ? (n => n > 0 && n < 0x110000 ? String.fromCodePoint(n) : m)(e[1] === "x" || e[1] === "X" ? parseInt(e.slice(2), 16) : parseInt(e.slice(1), 10)) : NAMED[e.toLowerCase()] ?? m);
const esc = s => String(s ?? "").replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;");
function slugify(s) {
  return String(s).toLocaleLowerCase("az").replace(/ə/g, "e").replace(/ı/g, "i").replace(/ö/g, "o").replace(/ü/g, "u").replace(/ş/g, "s")
    .replace(/ç/g, "c").replace(/ğ/g, "g").normalize("NFKD").replace(/[̀-ͯ]/g, "").replace(/[^a-z0-9]+/g, "-").replace(/^-|-$/g, "");
}

// app.js brauzer mühitində (prerender.cjs ilə eyni üsul): yalnız mövzu siyahıları və seçim funksiyası lazımdır.
function loadApp(root) {
  const context = vm.createContext({
    console: { ...console, log() {}, warn() {}, info() {} }, Map, Set, URL, Date, AbortController, setTimeout, clearTimeout, performance,
    addEventListener() {}, localStorage: { getItem() { return null; }, setItem() {}, removeItem() {} },
    location: { hash: "#/", href: SITE }, navigator: { onLine: true }, history: { replaceState() {} },
    document: { documentElement: { dataset: {}, style: {} }, addEventListener() {}, querySelector() { return null; }, querySelectorAll() { return []; },
      createElement() { return { _v: "", set innerHTML(v) { this._v = String(v); }, get innerHTML() { return this._v; }, get value() { return this._v; }, content: {}, children: [] }; } },
    matchMedia: () => ({ matches: false }), requestAnimationFrame: () => 0, SITE_CONFIG: {},
  });
  context.window = context;
  vm.runInContext(fs.readFileSync(path.join(root, "assets/content-policy.js"), "utf8"), context);
  vm.runInContext(fs.readFileSync(path.join(root, "assets/app.js"), "utf8").split(/\r?\napplyPrefs\(\);\r?\n/)[0], context);
  return vm.runInContext("({ clubMatches, policyViolation, REGION_TABS, SPORT_TABS, CATS })", context);
}

// Hər mövzu: bölgə/alt bölmə və onun içindəki rayonlar/komandalar. parent: üst mövzu (keçidlər üçün).
function topics(app) {
  const out = [];
  for (const [kind, k] of Object.entries(KINDS)) {
    for (const t of app[k.tabs]) {
      const top = { kind, name: t.name, label: t.label || t.name, slug: slugify(t.name), parent: null };
      out.push(top);
      for (const g of t.groups || []) for (const i of g.items) out.push({ kind, name: i.name, label: i.name, slug: slugify(i.name), parent: top, group: g.group || "" });
    }
  }
  const seen = new Set();
  return out.filter(t => t.slug && !seen.has(t.kind + "/" + t.slug) && seen.add(t.kind + "/" + t.slug));
}

function readRows(root) {
  const rows = new Map();
  const add = list => { for (const a of list || []) if (a?.sourceUrl && a.title && !rows.has(a.sourceUrl)) rows.set(a.sourceUrl, a); };
  const read = f => { try { return JSON.parse(fs.readFileSync(path.join(root, f), "utf8")).articles; } catch { return []; } };
  add(read("data/news.json"));
  let arx = [];
  try { arx = fs.readdirSync(path.join(root, "data/arxiv")).filter(f => f.endsWith(".json")); } catch {}
  for (const f of arx) add(read("data/arxiv/" + f));
  return [...rows.values()];
}

function heading(t) {
  if (t.kind === "rayon") return { h1: `${t.label} xəbərləri`, title: `${t.label} xəbərləri — son xəbərlər`, desc: `${t.label}: rayon və şəhərdən son xəbərlər, hadisələr, açılışlar. Azərbaycan saytlarından bir yerdə — 8ulduz.` };
  const what = t.parent && t.parent.name === "Futbol" ? `${t.label} futbol klubu` : t.parent ? `${t.label} (${t.parent.label})` : t.label;
  return { h1: `${what} xəbərləri`, title: `${what} xəbərləri — son idman xəbərləri`, desc: `${what}: son xəbərlər, nəticələr və transferlər bir yerdə — 8ulduz.` };
}

const PAGE = `<!doctype html>
<html lang="az">
<head>
<meta charset="UTF-8" />
<meta name="viewport" content="width=device-width, initial-scale=1.0" />
<title>__TITLE__ — 8ulduz</title>
<meta name="description" content="__DESC__" />
__ROBOTS__<link rel="canonical" href="__URL__" />
<meta name="theme-color" content="#15233b" />
<meta property="og:type" content="website" /><meta property="og:site_name" content="8ulduz" /><meta property="og:title" content="__TITLE__" />
<meta property="og:description" content="__DESC__" /><meta property="og:url" content="__URL__" /><meta property="og:image" content="${SITE}assets/og-default.png" />
<meta property="og:locale" content="az_AZ" />
<link rel="icon" href="${SITE}assets/icon-192.png" sizes="192x192" />
<script type="application/ld+json">__LD__</script>
<style>body{margin:0;font:17px/1.5 system-ui,-apple-system,"Segoe UI",Roboto,sans-serif;background:#15233b;color:#d5deeb}main{max-width:760px;margin:0 auto;padding:16px}a{color:#d6bd80}h1{font-size:1.5em;margin:.4em 0 .2em;color:#fff}ul{padding-left:1.2em}li{margin:0 0 1em}li>a{font-weight:600;text-decoration:none}small{display:block;color:#aabbd2}.go{display:inline-block;margin:.6em 0 1em;padding:8px 14px;border-radius:999px;background:#d6bd80;color:#15233b;font-weight:700;text-decoration:none}.rel a{display:inline-block;margin:0 10px 6px 0}@media(prefers-color-scheme:light){body{background:#f6f4ee;color:#172b4d}h1{color:#172b4d}a{color:#19385f}small{color:#465773}.go{background:#19385f;color:#fff}}</style>
<script type="application/json" id="movzu">__DATA__</script>
</head>
<body><main>
<p><a href="${SITE}">8ULDUZ</a> › <a href="${SITE}bolme/__SECTION__/">__SECTION_LABEL__</a>__CRUMB__</p>
<h1>__H1__</h1>
<p>__INTRO__</p>
<a class="go" href="__APP__">Son xəbərləri saytda aç</a>__TG__
__ITEMS__
__REL__
<p><a href="${SITE}icmal/">Günün icmalı</a> · <a href="https://t.me/sekkizulduz_az">Telegram kanalımız</a> · <a href="${SITE}">8ULDUZ — bütün xəbərlər</a></p>
</main></body>
</html>
`;

const AZ_MONTHS = ["yanvar", "fevral", "mart", "aprel", "may", "iyun", "iyul", "avqust", "sentyabr", "oktyabr", "noyabr", "dekabr"];
function bakuDate(iso) {
  const d = new Date(Date.parse(iso) + 4 * 3600e3);
  return isNaN(d) ? "" : `${d.getUTCDate()} ${AZ_MONTHS[d.getUTCMonth()]}, ${String(d.getUTCHours()).padStart(2, "0")}:${String(d.getUTCMinutes()).padStart(2, "0")}`;
}

function oldItems(file) {
  try {
    const m = fs.readFileSync(file, "utf8").match(/<script type="application\/json" id="movzu">([\s\S]*?)<\/script>/);
    const d = JSON.parse(m[1].replace(/\\u003c/g, "<"));
    return { items: Array.isArray(d.items) ? d.items : [], at: Number(d.at) || 0 };
  } catch { return { items: [], at: 0 }; }
}

function page(t, items, all, stories, now, bot = "") {
  const { h1, title, desc } = heading(t);
  const url = `${SITE}${t.kind}/${t.slug}/`, k = KINDS[t.kind];
  const app = `${SITE}#/bolme/${k.section}?m=${encodeURIComponent(t.name)}`;
  const href = i => stories[i.i] ? `${SITE}xeber/${i.i}/` : i.i ? `${SITE}#/xeber/${encodeURIComponent(i.i)}?b=${encodeURIComponent(i.c || k.section)}` : i.u;
  const list = items.length
    ? `<ul>${items.map(i => `<li><a href="${esc(href(i))}">${esc(i.t)}</a><small>${esc(i.s)}${i.d ? " · " + esc(bakuDate(i.d)) : ""}</small></li>`).join("")}</ul>`
    : `<p>Son ${KEEP_DAYS} gündə bu mövzuda xəbər yoxdur. Yeni xəbər çıxan kimi burada görünəcək.</p>`;
  const kin = all.filter(x => x.kind === t.kind && x !== t && (t.parent ? x.parent === t.parent || x === t.parent : x.parent === t));
  const rel = kin.length ? `<p class="rel"><b>${t.parent ? "Digər" : "Daxilində"}:</b> ${kin.map(x => `<a href="${SITE}${x.kind}/${x.slug}/">${esc(x.label)}</a>`).join(" ")}</p>` : "";
  const crumb = t.parent ? ` › <a href="${SITE}${t.kind}/${t.parent.slug}/">${esc(t.parent.label)}</a>` : "";
  const intro = items.length ? `Son ${KEEP_DAYS} gündə ${esc(t.label)} haqqında ${items.length} xəbər. Siyahı avtomatik yenilənir.` : esc(desc);
  const ld = { "@context": "https://schema.org", "@type": "CollectionPage", name: h1, url, inLanguage: "az",
    breadcrumb: { "@type": "BreadcrumbList", itemListElement: [{ "@type": "ListItem", position: 1, name: "8ULDUZ", item: SITE }, { "@type": "ListItem", position: 2, name: k.label, item: `${SITE}bolme/${k.section}/` },
      ...(t.parent ? [{ "@type": "ListItem", position: 3, name: t.parent.label, item: `${SITE}${t.kind}/${t.parent.slug}/` }] : []), { "@type": "ListItem", position: t.parent ? 4 : 3, name: t.label, item: url }] } };
  const json = o => JSON.stringify(o).replace(/</g, "\\u003c");
  // Bir keçid, funksiya ilə: String.replace(sətir, sətir) başlıqdakı «$$», «$'», «$&» işarələrini nümunə kimi oxuyur — «pu$$y»
  // «pu$y» olurdu, «50 milyon $'lık» isə şablonun qalanını JSON blokuna yapışdırıb səhifəni sındırırdı (2026-11-12).
  const fill = { TITLE: esc(title), DESC: esc(desc), URL: url, ROBOTS: items.length >= MIN_INDEX ? "" : '<meta name="robots" content="noindex, follow" />\n',
    LD: json(ld), DATA: json({ name: t.name, at: now, items }), SECTION: k.section, SECTION_LABEL: k.label,
    CRUMB: crumb, H1: esc(h1), INTRO: intro, APP: esc(app), TG: bot ? ` <a class="go" href="https://t.me/${bot}?start=${t.kind === "rayon" ? "r" : "i"}_${t.slug}" rel="noopener">📩 Telegram-da izlə</a>` : "", ITEMS: list, REL: rel };
  return PAGE.replace(/__([A-Z0-9]+(?:_[A-Z0-9]+)*)__/g, (all, name) => Object.hasOwn(fill, name) ? fill[name] : all);
}

function run(root, { now = Date.now(), app = loadApp(root) } = {}) {
  const rows = readRows(root).filter(a => !app.policyViolation(a));
  let stories = {};
  try { stories = JSON.parse(fs.readFileSync(path.join(root, "xeber/index.json"), "utf8")) || {}; } catch {}
  const all = topics(app), cutoff = now - KEEP_DAYS * 86400e3, map = [], bot = botOf(root);
  let written = 0;
  for (const t of all) {
    const pool = t.kind === "rayon" ? rows.filter(a => a.category !== "idman") : rows.filter(a => a.category === "idman");
    const fresh = pool.filter(a => app.clubMatches(a, t.name)).map(a => ({ i: a.id || "", t: unent(a.title).replace(/<[^>]+>/g, "").trim(), u: a.sourceUrl, s: unent(a.source || ""), d: a.publishedAt || "", c: a.category || "" }));
    const file = path.join(root, t.kind, t.slug, "index.html"), old = oldItems(file);
    const byUrl = new Map();
    for (const i of [...fresh, ...old.items]) if (i?.u && i.t && !byUrl.has(i.u) && (Date.parse(i.d) || now) >= cutoff) byUrl.set(i.u, i);
    const items = [...byUrl.values()].sort((a, b) => String(b.d).localeCompare(String(a.d))).slice(0, KEEP);
    const same = JSON.stringify(items) === JSON.stringify(old.items);
    const exists = fs.existsSync(file);
    if (!exists || (!same && now - old.at >= REWRITE_MS)) {
      fs.mkdirSync(path.dirname(file), { recursive: true });
      fs.writeFileSync(file, page(t, items, all, stories, now, bot));
      written++;
    }
    const kept = exists && (same || now - old.at < REWRITE_MS) ? old.items : items;
    if (kept.length >= MIN_INDEX) map.push({ loc: `${SITE}${t.kind}/${t.slug}/`, last: String(kept[0]?.d || "").slice(0, 10) });
  }
  const xml = `<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n` +
    map.map(u => `<url><loc>${u.loc}</loc>${u.last ? `<lastmod>${u.last}</lastmod>` : ""}<changefreq>hourly</changefreq></url>`).join("\n") + `\n</urlset>\n`;
  fs.writeFileSync(path.join(root, "sitemap-movzu.xml"), xml);
  return { topics: all.length, written, indexed: map.length };
}

module.exports = { run, slugify, topics, loadApp, KEEP_DAYS, MIN_INDEX };
if (require.main === module) {
  const r = run(path.resolve(process.argv[2] || "."));
  console.log(`mövzu səhifələri: ${r.topics} mövzu, ${r.written} yazıldı, ${r.indexed} sitemap-də`);
}
