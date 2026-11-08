// Paylaşma keçidi serveri (.github/x-worker/worker.js, Cloudflare Workers): x.8ulduz.az/<id> hər dəqiqə og etiketli səhifə verir (sahib, 2026-11-08:
// «Facebook-da paylaşanda başlıq çıxmır, xəbərə qayıtmır; tam düzəlt, WhatsApp kimi»).
const test = require("node:test");
const assert = require("node:assert/strict");
const path = require("node:path"), { pathToFileURL } = require("node:url");
const load = () => import(pathToFileURL(path.join(__dirname, "..", ".github/x-worker/worker.js")).href);

const ID = "0123456789abcdef", NOW = Date.UTC(2026, 10, 8, 12, 34, 50); // 2026-11-08T12:34:50Z
const SLOT = Math.floor((NOW / 1000 - 45) / 60);
const row = {
  id: ID, title: "Başlıq </script><b>", summary: "Xülasə", source: "APA", sourceUrl: "https://apa.az/1", imageUrl: "https://apa.az/i.jpg?a=1&b=(2)",
  category: "siyaset", publishedAt: "2026-11-07T13:05:00+04:00", lang: "az", alts: [{ source: "Report", sourceUrl: "https://report.az/1" }, { source: "Keçidsiz" }],
};
const feed = (articles, extra = {}) => JSON.stringify({ updatedAt: "2026-11-08T12:34:00+00:00", count: articles.length, articles, ...extra });
const html = (status, body) => new Response(body, { status, headers: { "Content-Type": "text/html; charset=utf-8" } });
const json = (status, body) => new Response(body, { status, headers: { "Content-Type": status === 200 ? "application/json" : "text/plain" } });

// fetch əvəzi: ünvan → cavab; soruşulan ünvanlar `seen`-də. Siyahıda olmayan ünvan 404.
function world(routes) {
  const seen = [];
  globalThis.fetch = async (url, opts = {}) => {
    seen.push(String(url));
    assert.ok(opts.signal instanceof AbortSignal, "hər sorğunun vaxtı var");
    const r = routes[String(url)];
    if (r instanceof Error) throw r;
    if (typeof r === "function") return r();
    return r || json(404, "404: Not Found");
  };
  return seen;
}
function memoryCache() {
  const store = new Map(), puts = [];
  globalThis.caches = { default: { match: async req => { const r = store.get(req.url); return r && r.clone(); }, put: async (req, res) => { puts.push(req.url); store.set(req.url, res); } } };
  return { store, puts };
}
const call = async (w, u, ctx = { waitUntil() {} }) => w.default.fetch(new Request(u), {}, ctx);
test.beforeEach(() => { delete globalThis.caches; });

test("x-worker 1: the page updater wrote on the site is served as it is, og:url points at this server, and it is cached for 10 minutes", async () => {
  const w = await load();
  const page = `<!doctype html>\n<html lang="az"><head><meta property="og:title" content="Neft bahalaşdı" /><meta property="og:url" content="https://8ulduz.az/x/${ID}" /></head></html>\n`;
  const seen = world({ [`https://8ulduz.az/x/${ID}`]: html(200, page) });
  const { puts } = memoryCache();
  const waited = [];
  const r = await call(w, `https://x.8ulduz.az/${ID}?h=26110813`, { waitUntil: p => waited.push(p) });
  assert.equal(r.status, 200);
  assert.equal(r.headers.get("Content-Type"), "text/html; charset=utf-8");
  assert.equal(r.headers.get("Cache-Control"), "public, max-age=600");
  assert.equal(r.headers.get("X-Robots-Tag"), "noindex");
  assert.equal(await r.text(), page.replace(`https://8ulduz.az/x/${ID}`, `https://x.8ulduz.az/${ID}`), "yalnız og:url dəyişir");
  assert.deepEqual(seen, [`https://8ulduz.az/x/${ID}`], "səhifə varsa lent soruşulmur");
  await Promise.all(waited);
  assert.deepEqual(puts, [`https://x.8ulduz.az/${ID}`], "keş açarı h-sız: eyni xəbər bir dəfə saxlanır");
  seen.length = 0;
  const again = await call(w, `https://x.8ulduz.az/${ID}`);
  assert.equal(await again.text(), page.replace(`https://8ulduz.az/x/${ID}`, `https://x.8ulduz.az/${ID}`));
  assert.deepEqual(seen, [], "ikinci sorğu keşdən, şəbəkəyə çıxmır");
  assert.equal(again.headers.get("Cache-Control"), "public, max-age=600");
});

test("x-worker 1b: a 404.html answered with status 200, or a page without og tags, does not count as the share page", async () => {
  const w = await load();
  world({ [`https://8ulduz.az/x/${ID}`]: html(200, "<!doctype html><html><head><title>Səhifə tapılmadı — 8ulduz</title></head></html>") });
  const r = await call(w, `https://x.8ulduz.az/${ID}?h=26110813`);
  assert.equal(r.status, 302);
  assert.equal(r.headers.get("Location"), `https://8ulduz.az/#/xeber/${ID}?h=26110813`);
});

test("x-worker 2: a story that is only in the minute channel gets the same page updater.share_page writes (og tags, image proxy, row hand-off, jump)", async () => {
  const w = await load();
  const seen = world({ [`${"https://raw.githubusercontent.com/8ulduz/8ulduz/live/m/"}${SLOT - 1}/latest.json`]: json(200, feed([{ id: "ffffffffffffffff", title: "Başqa" }, row])) });
  const realNow = Date.now; Date.now = () => NOW;
  let r;
  try { r = await call(w, `https://x.8ulduz.az/${ID}?h=26110712`); } finally { Date.now = realNow; }
  assert.equal(r.status, 200);
  const page = await r.text();
  const live = seen.filter(u => u.includes("/live/m/")).map(u => +u.match(/\/m\/(\d+)\//)[1]);
  assert.deepEqual(live, [SLOT, SLOT - 1, SLOT - 2, SLOT - 3], "sw.js ilə eyni dəqiqələr: (indi − 45 s)/60 və əvvəlki 3 (yaranmamış dəqiqə soruşulmur: raw 404-ü 55 s keşləyir)");
  assert.ok(!seen.some(u => u.includes("/data/")), "dəqiqəlik kanalda tapılanda saytın lent faylları soruşulmur");
  assert.ok(page.startsWith('<!doctype html>\n<html lang="az">'));
  assert.ok(page.includes('<meta property="og:title" content="Başlıq &lt;/script&gt;&lt;b&gt;" />'), "başlıq kodlanır");
  assert.ok(page.includes('<meta property="og:description" content="Xülasə" />'));
  assert.ok(page.includes(`<meta property="og:url" content="https://x.8ulduz.az/${ID}" />`), "kanonik ünvan bu serverdir: Facebook yenidən soruşsa yenə bura gəlir");
  assert.ok(page.includes('<meta property="og:image" content="https://wsrv.nl/?url=https%3A%2F%2Fapa.az%2Fi.jpg%3Fa%3D1%26b%3D%282%29&amp;w=1200&amp;h=630&amp;fit=cover&amp;a=attention&amp;output=jpg&amp;q=78&amp;default=https%3A%2F%2F8ulduz.az%2Fassets%2Fog-default.png" />'), "şəkil proksidən 1200×630, Python quote() kimi kodlanır");
  assert.ok(page.includes('<meta property="og:locale" content="az_AZ" />') && page.includes('<meta name="twitter:card" content="summary_large_image" />'));
  const m = page.match(/<script>try\{sessionStorage\.setItem\("x:0123456789abcdef",(".*?")\)\}catch\(e\)\{\}location\.replace\(("[^"]+")\)<\/script>\n/);
  assert.ok(m, "sətir sessionStorage-a, dərhal sayta (updater.share_jump)");
  assert.ok(!page.includes("</script><b>"), "başlıq skripti qıra bilmir");
  const handed = JSON.parse(JSON.parse(m[1].replace(/<\\\//g, "</")));
  assert.deepEqual(handed, { id: ID, title: "Başlıq </script><b>", summary: "Xülasə", source: "APA", sourceUrl: "https://apa.az/1", imageUrl: "https://apa.az/i.jpg?a=1&b=(2)", category: "siyaset", publishedAt: "2026-11-07T13:05:00+04:00", lang: "az", alts: [{ source: "Report", sourceUrl: "https://report.az/1" }] }, "SHARE_ROW_FIELDS, keçidsiz alt düşür");
  assert.equal(JSON.parse(m[2]), `https://8ulduz.az/#/xeber/${ID}?b=siyaset&h=26110713`, "saat xəbərin öz vaxtından (arxiv budağı), keçiddəki h yox");
  assert.ok(page.includes(`<meta http-equiv="refresh" content="0;url=https://8ulduz.az/#/xeber/${ID}?b=siyaset&amp;h=26110713" />`), "skriptsiz brauzer də keçir");
  assert.ok(page.includes(`<link rel="canonical" href="https://8ulduz.az/#/xeber/${ID}?b=siyaset&amp;h=26110713" />`) && page.includes('<meta name="robots" content="noindex" />'));
  assert.ok(page.endsWith(`<a href="https://8ulduz.az/">8ulduz</a></p></body></html>\n`));
});

test("x-worker 2b: when the minute channel has nothing, the site's feed files are searched (latest, first, news); a removed story is not served", async () => {
  const w = await load();
  const seen = world({ "https://8ulduz.az/data/first.json": json(200, feed([row], { og: {}, sharePages: true })) });
  const r = await call(w, `https://x.8ulduz.az/${ID}`);
  assert.equal(r.status, 200);
  assert.ok((await r.text()).includes('og:title" content="Başlıq'));
  assert.deepEqual(seen.filter(u => u.includes("/data/")).sort(), ["https://8ulduz.az/data/first.json", "https://8ulduz.az/data/latest.json", "https://8ulduz.az/data/news.json"]);
  world({ "https://8ulduz.az/data/latest.json": json(200, feed([], { removed: { "apa.az#1": { id: ID, ids: [ID], title: "Başlıq" } } })), "https://8ulduz.az/data/news.json": json(200, feed([row])) });
  const gone = await call(w, `https://x.8ulduz.az/${ID}?h=26110713`);
  assert.equal(gone.status, 302, "redaksiyanın çıxardığı xəbər verilmir (QIRMIZI XƏTT 2: lentdə olmayan sətir uydurulmur), sayt özü qərar verir");
  assert.equal(gone.headers.get("Location"), `https://8ulduz.az/#/xeber/${ID}?h=26110713`);
});

test("x-worker 2c: the page text is identical to updater.share_page for the same row (summary cut at 200, no image → site image, fallback description)", async () => {
  const { pageHtml, xml, hourOf, appUrl } = await load();
  const long = "Söz ".repeat(60).trim();
  const page = pageHtml({ id: ID, title: "  Çox   boşluq\n", summary: `<b>${long}</b>`, source: "Report", sourceUrl: "https://report.az/2", publishedAt: "2026-11-08T05:01:46+00:00", lang: "ru", category: "iqtisadiyyat" });
  const desc = page.match(/og:description" content="([^"]*)"/)[1];
  assert.ok(desc.endsWith("…") && desc.length <= 200 && !desc.includes("<b>"), desc);
  assert.ok(page.includes('<title>Çox boşluq — 8ulduz</title>') && page.includes('<html lang="ru">') && page.includes('content="ru_RU"'));
  assert.ok(page.includes('<meta property="og:image" content="https://8ulduz.az/assets/og-default.png" />'), "şəkilsiz xəbər saytın şəkli ilə");
  assert.ok(page.includes(`"${appUrl(ID, "iqtisadiyyat", "26110805")}"`.replace(/&/g, "&amp;")));
  const bare = pageHtml({ id: ID, title: "T", source: "APA", publishedAt: "2026-11-08T05:01:46+00:00" });
  assert.ok(bare.includes('og:description" content="APA · 2026-11-08"'), "xülasəsiz: mənbə · tarix");
  assert.ok(bare.includes(`location.replace("https://8ulduz.az/#/xeber/${ID}?b=&h=26110805")`), "bölməsiz sətir Python kimi ?b=&h=");
  assert.equal(pageHtml({ id: ID, title: "T" }, "26110101").match(/location\.replace\("([^"]+)"\)/)[1], `https://8ulduz.az/#/xeber/${ID}?b=&h=26110101`, "vaxtsız sətirdə keçidin h-si");
  assert.equal(xml("A &amp;amp; B <i>&quot;"), "A &amp; B &lt;i&gt;&quot;", "updater._xml: əvvəl açılır, sonra kodlanır");
  assert.equal(hourOf({ publishedAt: "2026-11-07T13:05:00+04:00" }), "26110713");
  assert.equal(hourOf({}), "");
});

test("x-worker 3: a link never dies — not in any feed, feed errors, server exceptions and odd paths all end on the site", async () => {
  const w = await load();
  world({});
  let r = await call(w, `https://x.8ulduz.az/${ID}?h=26110812`);
  assert.equal(r.status, 302);
  assert.equal(r.headers.get("Location"), `https://8ulduz.az/#/xeber/${ID}?h=26110812`, "sayt arxivdən açır");
  r = await call(w, `https://x.8ulduz.az/${ID}`);
  assert.equal(r.headers.get("Location"), `https://8ulduz.az/#/xeber/${ID}`, "saatsız keçid");
  r = await call(w, `https://x.8ulduz.az/${ID}?h=<script>`);
  assert.equal(r.headers.get("Location"), `https://8ulduz.az/#/xeber/${ID}`, "h yalnız rəqəm");
  globalThis.fetch = async () => { throw new TypeError("network down"); };
  r = await call(w, `https://x.8ulduz.az/${ID}?h=26110812`);
  assert.equal([r.status, r.headers.get("Location")].join(" "), `302 https://8ulduz.az/#/xeber/${ID}?h=26110812`, "şəbəkə xətası da 302");
  globalThis.fetch = async () => json(200, "{not json");
  r = await call(w, `https://x.8ulduz.az/${ID}`);
  assert.equal(r.status, 302, "zədəli lent də 302");
  globalThis.caches = { default: { match: async () => { throw new Error("cache down"); }, put: async () => {} } };
  r = await call(w, `https://x.8ulduz.az/${ID}`);
  assert.equal(r.status, 302, "keş xətası da 302");
  delete globalThis.caches;
  for (const bad of ["https://x.8ulduz.az/", "https://x.8ulduz.az/abc", "https://x.8ulduz.az/0123456789ABCDEF", "https://x.8ulduz.az/x/0123456789abcdef"]) {
    r = await call(w, bad);
    assert.equal([r.status, r.headers.get("Location")].join(" "), "302 https://8ulduz.az/", bad);
  }
  r = await call(w, "https://x.8ulduz.az/saglam");
  assert.equal([r.status, await r.text()].join(" "), "200 ok");
});

test("x-worker: the minute channel is asked with the same path scheme pipeline.sh writes (live branch, m/<minute>/latest.json)", async () => {
  const { findRow } = await load();
  const seen = world({});
  assert.equal(await findRow(ID, NOW), null);
  assert.ok(seen.includes(`https://raw.githubusercontent.com/8ulduz/8ulduz/live/m/${SLOT}/latest.json`), seen.join("\n"));
  assert.equal(seen.length, 4 + 3, "4 dəqiqə + 3 lent faylı, hamısı bir dəfə");
});
