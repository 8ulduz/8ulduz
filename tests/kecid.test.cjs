// Keçidlər (sahib, 2026-11-09: «keçidlər gözqırpımında»): ana səhifənin DOM-u kənara çıxanda saxlanır, bölmə hovuzu yaddaşda qalır,
// axtarış mətni id ilə saxlanır, tarix sırası sadə sətir müqayisəsi ilə, keçidə toxunan anda lazım olan fayl istənir.
// Ölçülər və səbəblər docs/qirmizi-xetler.md §3-də (2026-11-09, keçidlər).
const { test } = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs"), vm = require("node:vm"), path = require("node:path");
const root = path.join(__dirname, "..");
const read = f => fs.readFileSync(path.join(root, f), "utf8").replace(/\r\n/g, "\n");
const APP = read("assets/app.js");
const ISO = /^\d{4}-\d\d-\d\dT\d\d:\d\d:\d\d\+00:00$/;

// Testlərin saxta brauzeri: DOM yoxdur, yalnız HTML və vəziyyət. timers: setTimeout çağırışları (idle-in ehtiyat yolu) buraya yazılır.
function app({ phone = false, timers = [] } = {}) {
  const ctx = vm.createContext({
    console, URL, AbortController, TextEncoder, btoa,
    setTimeout: (f, ms) => timers.push([f, ms]), clearTimeout() {}, setInterval: () => 0, clearInterval() {},
    addEventListener() {}, localStorage: { getItem() { return null; }, setItem() {}, removeItem() {} },
    location: { hash: "#/" }, navigator: { onLine: true }, window: { addEventListener() {} }, history: { replaceState() {} },
    document: { documentElement: { dataset: {} }, hidden: false, addEventListener() {}, querySelector() { return null; }, querySelectorAll() { return []; },
      createElement() { return { _v: "", set innerHTML(v) { this._v = String(v); }, get innerHTML() { return this._v; }, get value() { return this._v; }, get content() { return { html: this._v, children: [] }; }, children: [] }; },
      createDocumentFragment() { return { nodes: [], append(...n) { this.nodes.push(...n); } }; } },
    matchMedia: q => ({ matches: phone && String(q).includes("hover:none") }), requestAnimationFrame: () => 0,
  });
  vm.runInContext(APP.split("\napplyPrefs();\n")[0], ctx);
  vm.runInContext("render = () => {}; renderTopbar = () => {}; checkBreaking = () => {}; primeHeroImage = () => {}; requestRender = () => {}; loadArchive = async () => {};", ctx);
  return ctx;
}
const run = (ctx, code) => vm.runInContext(code, ctx);

test("keçid: every publishedAt in the shipped data has one UTC format, so the plain string order of newest() equals the old localeCompare order", () => {
  const files = ["data/news.json", "data/latest.json", "data/first.json", ...fs.readdirSync(path.join(root, "data/arxiv")).filter(f => f.endsWith(".json")).map(f => "data/arxiv/" + f)];
  let n = 0;
  for (const f of files) for (const a of JSON.parse(read(f)).articles || []) for (const v of [a.publishedAt, ...(a.alts || []).map(x => x.publishedAt)]) {
    n++;
    assert.match(String(v), ISO, `${f}: «${v}» — updater.py (_norm_iso) bütün tarixləri UTC, saniyə dəqiqliyi ilə yazır; başqa format sətir sırasını pozar`);
  }
  assert.ok(n > 1000, "məlumat faylları oxundu");
  assert.ok(read("updater.py").includes('return dt.astimezone(datetime.timezone.utc).isoformat(timespec="seconds")'), "updater.py _norm_iso formatı saxlayır");
  const newest = run(app(), "newest");
  const rows = ["2026-11-09T12:00:00+00:00", "2026-11-09T12:00:01+00:00", "", undefined, "2025-01-01T00:00:00+00:00", "2026-11-09T11:59:59+00:00", "2026-11-09T12:00:00+00:00"].map((publishedAt, i) => ({ i, publishedAt }));
  const old = (x, y) => (y.publishedAt || "").localeCompare(x.publishedAt || "");
  assert.deepEqual([...rows].sort(newest).map(a => a.i), [...rows].sort(old).map(a => a.i), "eyni sıra (boş tarix sonda, bərabərlər yerində)");
  assert.ok(!/publishedAt \|\| ""\)\.localeCompare/.test(APP), "publishedAt sırasında localeCompare qalmayıb (4 100 sətirdə 2,7 → 0,9 ms)");
});

test("keçid: byDate caches each row's timestamp and still orders like a fresh Date parse, also after a row's date changes", () => {
  const byDate = run(app(), "byDate");
  const rows = [["a", "2026-11-09T12:00:00+00:00"], ["b", "2026-11-09T12:00:00.500Z"], ["c", "2026-11-08T23:00:00+04:00"], ["d", "yanlış"], ["e", "2026-11-09T12:00:01+00:00"], ["f", undefined]].map(([id, publishedAt]) => ({ id, publishedAt }));
  const naive = list => [...list].sort((x, y) => new Date(y.publishedAt).getTime() - new Date(x.publishedAt).getTime());
  assert.deepEqual(Array.from(byDate(rows), a => a.id), naive(rows).map(a => a.id));
  assert.deepEqual(Array.from(byDate(rows), a => a.id), naive(rows).map(a => a.id), "ikinci çağırış (yaddaşdan) eyni");
  rows[0].publishedAt = "2030-01-01T00:00:00+00:00";
  assert.equal(byDate(rows)[0].id, "a", "tarixi dəyişən sətir yeni yerinə düşür (yaddaş sahəni yoxlayır)");
});

test("keçid: search text is cached by story id across re-merged clones and rebuilt when the title, summary or source count changes", () => {
  const ctx = app(), searchText = run(ctx, "searchText");
  const a = { id: "x1", title: "Bakıda yeni yol", summary: "Xülasə", source: "APA", sourceUrl: "https://apa.az/1", alts: [{ source: "Report" }] };
  const s1 = searchText(a);
  assert.equal(searchText({ ...a }), s1, "klon eyni yaddaşı alır (collapseExact hər qurmada sətri klonlayır, obyekt açarı boşa düşürdü)");
  assert.equal(s1.t, "bakida yeni yol");
  assert.ok(s1.rest.includes("report") && s1.rest.includes("xulase"));
  assert.notEqual(searchText({ ...a, title: "Bakıda köhnə yol" }), s1, "başlıq dəyişdi");
  assert.notEqual(searchText({ ...a, summary: "Başqa" }), s1, "xülasə dəyişdi");
  assert.notEqual(searchText({ ...a, alts: [] }), s1, "mənbə sayı dəyişdi");
  assert.equal(run(ctx, "SEARCH_TEXT instanceof Map"), true);
  assert.ok(APP.includes("if (SEARCH_TEXT.size >= 2e4) SEARCH_TEXT.clear();"), "yaddaş sərhədsiz böyümür");
});

test("keçid: a section pool is rebuilt only when its own rows, its archive or the withdrawals change — a minute refresh with the same content reuses it", () => {
  const ctx = app();
  const at = new Date().toISOString().replace(/\.\d+Z$/, "+00:00");
  const row = (id, category) => ({ id, title: "Xəbər " + id, summary: "", category, source: "APA", sourceUrl: "https://apa.az/" + id, publishedAt: at, lang: "az" });
  ctx.rows = [row("g1", "gundem"), row("s1", "siyaset"), row("i1", "idman")];
  run(ctx, 'S.data = { articles: rows }; S.archive = { gundem: { at: Date.now(), rows: [{ ...rows[0], id: "g1a" }, { id: "g0", title: "Köhnə gündəm xəbəri", category: "gundem", source: "Report", sourceUrl: "https://report.az/g0", publishedAt: "2026-11-01T10:00:00+00:00", lang: "az" }] } };');
  const pool = s => run(ctx, `catPool(${JSON.stringify(s)}, S.data.articles.filter(a => a.category === ${JSON.stringify(s)}))`);
  const p1 = pool("gundem");
  assert.deepEqual(Array.from(p1, a => a.id), ["g1", "g0"], "lent + arxiv birləşir, eyni keçid bir dəfə, ən yenisi üstdə");
  run(ctx, "S.data = { articles: S.data.articles.map(a => ({ ...a })) }"); // dəqiqəlik lent: yeni obyektlər, eyni məzmun
  assert.equal(pool("gundem"), p1, "məzmun eynidirsə hovuz yenidən qurulmur (collapseExact 1×-də 10–14 ms idi)");
  run(ctx, "globalThis.__json = 0; const J = JSON.stringify; JSON.stringify = (...a) => (__json++, J(...a));");
  assert.equal(pool("gundem"), p1);
  assert.equal(run(ctx, "__json"), 0, "eyni S.data: məzmun müqayisəsi də edilmir («Daha çox», alt düymə)");
  run(ctx, "S.data = { articles: [...S.data.articles, { ...S.data.articles[1], id: 's2', sourceUrl: 'https://apa.az/s2' }] }");
  assert.equal(pool("gundem"), p1, "başqa bölmənin yeni xəbəri gündəmin hovuzuna toxunmur");
  run(ctx, "S.data = { articles: [...S.data.articles, { ...S.data.articles[0], id: 'g2', sourceUrl: 'https://apa.az/g2' }] }");
  const p2 = pool("gundem");
  assert.notEqual(p2, p1);
  assert.ok(p2.some(a => a.id === "g2"), "bölmənin yeni xəbəri hovuza düşür");
  run(ctx, "S.data = { articles: S.data.articles.map(a => a.id === 'g1' ? { ...a, title: 'Başlıq düzəldi' } : a) }");
  const p3 = pool("gundem");
  assert.ok(p3 !== p2 && p3.some(a => a.title === "Başlıq düzəldi"), "başlıq düzəlişi görünür");
  run(ctx, "S.archive.gundem.rows = [...S.archive.gundem.rows]");
  const p4 = pool("gundem");
  assert.notEqual(p4, p3, "arxiv gələndə yenidən");
  run(ctx, "removedIds.add('yox')");
  assert.notEqual(pool("gundem"), p4, "silinmə siyahısı dəyişəndə yenidən");
  assert.notEqual(pool("sondeqiqe"), pool("sondeqiqe"), "«son dəqiqə» saatla dəyişir: yaddaşda saxlanmır");
  assert.ok(APP.includes("list = catPool(slug, list);") && !APP.includes("list = byDate(withArchive(slug, list));"), "sectionView hovuzu buradan alır");
});

test("keçid: on a phone late() keeps the deferred cards in LATE_HTML and leaves only a keyed empty template in the page; lateContent rebuilds them", () => {
  const ctx = app({ phone: true });
  const html = run(ctx, 'late(["<b>1</b>", "<b>2</b>", "<b>3</b>"], 1)');
  const key = (html.match(/<template data-late="([^"]+)"><\/template>$/) || [])[1];
  assert.ok(key, html);
  assert.equal(html, `<b>1</b><template data-late="${key}"></template>`, "səhifə sətrində yalnız açar");
  assert.equal(run(ctx, `LATE_HTML.get(${JSON.stringify(key)})`), "<b>2</b><b>3</b>");
  assert.equal(run(ctx, 'late(["<b>1</b>", "<b>2</b>", "<b>3</b>"], 1)'), html, "eyni məzmun eyni açar: S.viewPage müqayisəsi dəyişmir");
  ctx.t = { dataset: { late: key } };
  assert.equal(run(ctx, "lateContent(t).html"), "<b>2</b><b>3</b>", "doldurma yaddaşdan");
  assert.equal(run(ctx, 'late(["a", "b"], 5)'), "ab", "sayı azdırsa şablon yoxdur");
  assert.equal(run(app(), 'late(["<b>1</b>", "<b>2</b>"], 1)'), "<b>1</b><b>2</b>", "kompüterdə hamısı birdən");
  assert.ok(APP.includes("recent(LATE_HTML, k, h, 40);"), "yaddaş həddi");
  assert.ok(APP.includes('next.content.querySelectorAll?.("template[data-late]").forEach(t => { const c = lateContent(t); if (c) t.replaceWith(c); });'), "dolmuş səhifənin yenidən çəkilişi şablonu yaddaşdan açır");
});

test("keçid: the home DOM is kept when leaving and put back on return; a changed feed refreshes it in idle time, a changed language or 10 minutes discard it", () => {
  const timers = [], ctx = app({ timers });
  const node = () => ({ matches: () => false, querySelector: () => null, querySelectorAll: () => [], closest: () => null });
  const kids = [node(), node()];
  ctx.v = { childNodes: kids, firstChild: kids[0], children: kids, got: null, replaceChildren(f) { this.got = f; }, querySelector: () => null, querySelectorAll: () => [] };
  run(ctx, 'S.data = { articles: [] }; S.partial = false; S.viewPage = "<p>ev</p>"; S.lang = "az";');
  assert.deepEqual(Array.from(run(ctx, "[keyDiff([1, 2, 3, 4], [1, 2, 3, 4]), keyDiff([9, 2, 3, 4], [1, 2, 3, 4]), keyDiff([1, 2, 3, 9], [1, 2, 3, 4]), keyDiff([9, 2, 3, 9], [1, 2, 3, 4])]")), [0, 1, 2, 2], "ilk üç sahə (lent, arxiv, dəqiqə) yumşaq, qalanı sərt");
  assert.equal(run(ctx, "homeKey().length"), 20);
  run(ctx, 'globalThis.__k = homeKey(); S.error = "şəbəkə"');
  assert.equal(run(ctx, "keyDiff(homeKey(), __k)"), 2, "xəta zolağı yaranıb: saxlanan DOM-da yoxdur, yenidən qurulur");
  run(ctx, "S.error = null");
  run(ctx, "keepHome(v)");
  assert.equal(run(ctx, "S.viewPage"), null, "yeni səhifə boş qutuya çəkilir");
  assert.equal(run(ctx, "S.homeKeep.frag.nodes.length"), 2, "üst düyünlər parçaya köçdü");
  assert.equal(run(ctx, "S.homeKeep.page"), "<p>ev</p>");
  const frag = run(ctx, "S.homeKeep.frag");
  assert.equal(run(ctx, "restoreHome(v)"), true, "eyni açar: geri qoyulur");
  assert.equal(ctx.v.got, frag);
  assert.equal(run(ctx, "S.viewPage"), "<p>ev</p>", "səhifə sətri qayıdır: növbəti eyni çəkiliş DOM-a toxunmur");
  assert.equal(run(ctx, "S.homeKeep"), null);
  assert.equal(run(ctx, "S.lateDone"), run(ctx, "lateKey()"), "dolmuş siyahı dolmuş sayılır");
  assert.equal(timers.length, 0, "açar eynidirsə boş anda çəkiliş yoxdur");
  run(ctx, "keepHome(v); S.data = { articles: [] };");
  assert.equal(run(ctx, "restoreHome(v)"), true, "lent dəyişib: köhnə DOM dərhal, təzəsi boş anda");
  assert.deepEqual(timers.map(t => [t[0].name, t[1]]), [["renderView", 500]]);
  ctx.v.got = null;
  run(ctx, 'keepHome(v); S.lang = "ru";');
  assert.equal(run(ctx, "restoreHome(v)"), false, "dil dəyişib: saxlanan atılır");
  assert.equal(ctx.v.got, null);
  assert.equal(run(ctx, "S.homeKeep"), null);
  run(ctx, 'S.viewPage = "<p>ev</p>"; keepHome(v); S.homeKeep.at -= NEWS_FULL_MS + 1;');
  assert.equal(run(ctx, "restoreHome(v)"), false, "10 dəqiqədən köhnə saxlanmış atılır");
  run(ctx, 'S.viewPage = "<p>ev</p>"; S.partial = true; keepHome(v);');
  assert.equal(run(ctx, "S.homeKeep"), null, "ilk ekran (natamam lent) saxlanmır");
  assert.ok(APP.includes("if (S.viewHome && !home) keepHome(v);") && APP.includes("if (!home || !restoreHome(v)) {") && APP.includes("S.viewHome = home && !S.partial;"), "renderView-da yer");
});

test("keçid: touching a link preloads what that page will need (archive, sports file, rare-page module, team module); startup is untouched", () => {
  const ctx = app();
  run(ctx, 'globalThis.calls = []; loadArchive = s => calls.push("arxiv:" + s); wantSports = () => calls.push("idman"); preTeam = () => calls.push("komanda"); loadPages = () => calls.push("sehife"); S.data = { articles: [] }; S.partial = false;');
  for (const h of ["#/bolme/sehiyye", "#/bolme/gundem?m=Quba", "#/bolme/cedvel", "#/bolme/valyuta", "#/haqqinda", "#/bolmeler", "#/menbeler?x=1", "#/komanda/premyer-liqa/qarabag", "#/xeber/abc", "#/", "#/secilmis", null]) run(ctx, `preload(${JSON.stringify(h)})`);
  assert.deepEqual(Array.from(run(ctx, "calls")), ["arxiv:heyat", "arxiv:gundem", "idman", "sehife", "sehife", "sehife", "komanda"], "«bolmeler» «bolme» ilə qarışmır");
  run(ctx, "calls.length = 0; S.partial = true; preload('#/bolme/gundem')");
  assert.deepEqual(Array.from(run(ctx, "calls")), [], "ilk ekran hələ dolmayıbsa arxiv istənmir (tam lentlə yarışmasın)");
  assert.ok(APP.includes(`document.addEventListener("pointerdown", e => { const a = e.target.closest?.("a[href]"); if (!a) return; let h = a.getAttribute("href") || ""; const m = h.match(/^\\/bolme\\/([^/?#]+)/); if (m) h = "#/bolme/" + m[1]; if (h[0] === "#") preload(h); }, { passive: true, capture: true });`), "telefonda barmaq toxunan anda");
  assert.ok(APP.includes('preT = setTimeout(() => preload(item.getAttribute("href")), 120);'), "kompüterdə kursor menyuda dayananda");
  assert.ok(APP.includes('if (["sources", "about", "sections"].includes(route().name)) renderView();'), "modul gələndə yalnız həmin səhifədəsə çəkilir");
});
