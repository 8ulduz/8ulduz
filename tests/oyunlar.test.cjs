// Liqanın oyunları və canlı hesab (assets/oyunlar.js; sahib 2026-11-26: «İstənilən liqanı seçəndə cədvəlin altında və bölmədə oyunlar
// və canlı skorlar olsun. Bu bütün turnirlərdə bu cür olsun»). Fikstur: 2026-11-25 ÇL axşamının real məlumatı (tests/fixtures/canli_liqa):
// main-dəki cl.json (21:41, 20:00 oyunları hələ oynanmayıb) və updater.live_league_doc-un o fayldan qurduğu canlı nüsxələr
// (21:40 — 7 oyun gedir, data/canli.json; 22:12 — 7 oyun bitib, TheSportsDB livescore). tests/test_canli_liqa.py eyni nüsxəni
// Python-da qurub bu fayllarla tutuşdurur: iki tərəfin müqaviləsi bir yerdədir.
const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const { pathToFileURL } = require("node:url");

const root = path.join(__dirname, "..");
const read = f => fs.readFileSync(path.join(root, f), "utf8");
const fix = f => JSON.parse(read("tests/fixtures/canli_liqa/" + f));
const mod = () => import(pathToFileURL(path.join(root, "assets/oyunlar.js")).href);
const T = s => Date.parse(s);

test("oyunlar: «isti» liqa qaydası updater.py ilə eynidir (30 dəq əvvəl — 4 saat sonra; saatsız oyun o gecə)", async () => {
  const { windowOf, hot } = await mod();
  const py = read("updater.py");
  assert.match(py, /LIVE_HOT_BEFORE = datetime\.timedelta\(minutes=30\)/);
  assert.match(py, /LIVE_HOT_AFTER = datetime\.timedelta\(hours=4\)/);
  assert.match(py, /LIVE_DAY_FROM, LIVE_DAY_TO = datetime\.timedelta\(hours=8\), datetime\.timedelta\(hours=20\)/);
  const g = { date: "2026-11-25T20:00:00+00:00" };
  assert.deepEqual(windowOf(g), [T("2026-11-25T19:30:00Z"), T("2026-11-26T00:00:00Z")]);
  assert.deepEqual(windowOf({ date: "2026-11-25T12:00:00+00:00", day: true }), [T("2026-11-25T20:00:00Z"), T("2026-11-26T08:00:00Z")]);
  assert.equal(windowOf({ ...g, state: "off" }), null, "təxirə salınan oyun liqanı isitmir");
  const doc = { games: [g] };
  assert.ok(!hot(doc, T("2026-11-25T19:29:00Z")) && hot(doc, T("2026-11-25T19:31:00Z")) && hot(doc, T("2026-11-25T23:59:00Z")) && !hot(doc, T("2026-11-26T00:01:00Z")));
});

test("oyunlar: canlı nüsxə cədvəli və öz aralığının oyunlarını əvəz edir, qalan oyunlar liqanın faylındandır", async () => {
  const { merge } = await mod();
  const cl = fix("cl.json"), patch = fix("liqa-cl-2212.json");
  const out = merge(cl, patch);
  assert.equal(merge(cl, patch), out, "eyni giriş — eyni obyekt (komanda.js-in oyun yaddaşı hər çəkilişdə sıfırlanmasın)");
  assert.equal(out.groups, patch.groups);
  assert.equal(out.games.length, cl.games.length, "aralıqdakı oyun təkrarlanmır");
  const psg = out.games.find(g => g.home === "paris-saint-germain" && g.round === "5");
  assert.deepEqual(psg.live, { s: "ft", hs: 2, as: 2 });
  assert.ok(out.games.some(g => g.round === "6") && out.games.some(g => g.round === "4"), "aralıqdan kənar turlar fayldan qalır");
  assert.equal(merge(cl, { ...patch, id: "al" }), cl, "başqa liqanın nüsxəsi qəbul olunmur");
  assert.equal(merge(cl, null), cl);
});

test("oyunlar: 21:40 — gedən 7 oyun «Canlı»da hesabla, bu günün bitən oyunları, növbəti tur və son nəticələr", async () => {
  const { merge, block } = await mod();
  const html = block(merge(fix("cl.json"), fix("liqa-cl-2140.json")), { now: T("2026-11-25T21:40:00Z") });
  assert.ok(html.startsWith('<section class="tm-sec oy" data-oy="cl">'));
  assert.ok(html.includes("● 7 canlı"));
  // Bakı UTC+4-dür: 20:00 UTC oyunları Bakıda 26 noyabr 00:00-dadır, 21:40 UTC isə 01:40 — «bu gün» 26 noyabrdır.
  const live = html.slice(html.indexOf("<h3>Canlı</h3>"), html.indexOf("<h3>Növbəti"));
  assert.ok(!html.includes("<h3>Bu gün"), "bu günün (26 noyabr) 7 oyununun hamısı gedir — «Canlı»dadır");
  assert.equal(live.split('<li class="on">').length - 1, 7);
  assert.ok(live.includes(">PSG</a><b>2 : 1</b><a"), "PSG — Roma 2:1 (gedir)");
  assert.ok(html.includes("<h3>Növbəti oyunlar</h3>") && html.includes("9 dek"), "növbəti tur (9–10 dekabr) liqanın faylından");
  const past = html.slice(html.indexOf("<h3>Son nəticələr</h3>"));
  assert.ok(past.includes("<small>25 noy</small>") && past.includes(">Sabah</a><b>1 : 4</b><a"), "dünən (Bakı vaxtı 21:45): Sabah — Barselona 1:4");
  assert.ok(past.includes("<small>24 noy</small>"), "son iki oyun günü");
  assert.ok(html.includes('href="#/komanda/cl/sabah"'), "komanda adı onun səhifəsinə aparır");
  assert.ok(html.includes("Canlı hesab: TheSportsDB, football-data.org · yoxlanıb 01:40"), "mənbə və yoxlama vaxtı (Bakı)");
});

test("oyunlar: 22:12 — oyunlar bitəndə «Canlı» yoxdur, hesab «Bitdi» ilə; cədvəl canlı nüsxədən gəlir", async () => {
  const { merge, block } = await mod();
  const doc = merge(fix("cl.json"), fix("liqa-cl-2212.json"));
  const html = block(doc, { now: T("2026-11-25T22:12:00Z") });
  assert.ok(!html.includes("<h3>Canlı</h3>") && !html.includes("canlı</span>"));
  const today = html.slice(html.indexOf("<h3>Bu gün, 26 noyabr</h3>"), html.indexOf("<h3>Növbəti"));
  assert.equal(today.split("<li>").length - 1, 7, "Bakı günü 26 noyabrın 7 oyunu (00:00)");
  assert.equal(today.split("Bitdi").length - 1, 7);
  assert.ok(today.includes(">Sporting</a><b>2 : 2</b><a"), "Sportinq — MU: TheSportsDB 2:2 (football-data.org 2:3 deyirdi)");
});

test("oyunlar: qayda bütün turnirlərdə eynidir — saytdakı hər liqanın faylı eyni blokla çəkilir", async () => {
  const { block } = await mod();
  const index = JSON.parse(read("data/futbol/index.json"));
  let shown = 0;
  for (const l of index.leagues) {
    const file = path.join(root, "data/futbol", l.id + ".json");
    if (!fs.existsSync(file)) continue;
    const doc = JSON.parse(fs.readFileSync(file, "utf8"));
    const html = block(doc, { now: T("2026-11-25T21:40:00Z") });
    if ((doc.games || []).some(g => g.date && g.home && g.away)) {
      assert.ok(html.includes(`data-oy="${l.id}"`), `${l.id}: oyunları var, blok çıxmalıdır`);
      shown++;
    } else assert.equal(html, "", `${l.id}: oyun yoxdur — blok yoxdur`);
    assert.ok(!/<script|javascript:/i.test(html), l.id);
  }
  assert.ok(shown >= 40, `blok ${shown} turnirdə`);
});

test("oyunlar: isti liqa dəqiqəlik canlı kanaldan oxunur, soyuq liqaya sorğu getmir", async () => {
  const { use, hot } = await mod();
  const asked = [], real = globalThis.fetch;
  const kick = new Date(Date.now() - 20 * 60e3).toISOString();
  const doc = { id: "sinaq-liqa", groups: [{ name: "", rows: [{ team: "a", pos: 1 }] }], teams: { a: { name: "A" }, b: { name: "B" } }, games: [{ date: kick, home: "a", away: "b", played: false }] };
  const patch = { id: "sinaq-liqa", at: "x", from: new Date(Date.now() - 864e5).toISOString(), to: new Date(Date.now() + 864e5).toISOString(),
    groups: [{ name: "", rows: [{ team: "b", pos: 1 }] }], games: [{ ...doc.games[0], live: { s: "live", hs: 0, as: 1, min: 20 } }] };
  globalThis.fetch = async url => { asked.push(String(url)); return { ok: true, json: async () => patch }; };
  try {
    let renders = 0;
    assert.ok(hot(doc));
    assert.equal(use(doc, () => renders++), doc, "nüsxə gələnə qədər fayl olduğu kimi");
    await new Promise(r => setTimeout(r, 10));
    assert.match(asked[0], /^https:\/\/raw\.githubusercontent\.com\/8ulduz\/8ulduz\/live\/m\/\d+\/liqa-sinaq-liqa\.json$/);
    assert.equal(renders, 1, "nüsxə gələndə səhifə bir dəfə yenidən çəkilir");
    const out = use(doc, () => renders++);
    assert.deepEqual(out.games[0].live, { s: "live", hs: 0, as: 1, min: 20 });
    assert.equal(out.groups[0].rows[0].team, "b", "cədvəl canlı nüsxədən");
    assert.equal(asked.length, 1, "dəqiqə dolmamış təkrar sorğu yoxdur");
    const cold = { id: "soyuq", games: [{ date: "2026-01-01T18:00:00+00:00", home: "a", away: "b", played: true, hs: 1, as: 0 }] };
    assert.equal(use(cold, () => {}), cold);
    assert.equal(asked.length, 1, "oyunu getməyən liqaya canlı kanal soruşulmur");
  } finally { globalThis.fetch = real; }
});

test("oyunlar: sürət — tənbəl moduldur, ilk açılışa düşmür, yerləşdirmə oxumur, büdcəyə sığır", () => {
  const src = read("assets/oyunlar.js"), app = read("assets/app.js"), sw = read("sw.js"), budce = JSON.parse(read("tests/budce.json"));
  assert.ok(Buffer.byteLength(src) < budce.kod["tenbel.js"], "tənbəl modul büdcəsi");
  assert.ok(!app.includes("oyunlar.js") && !read("index.html").includes("oyunlar") && !sw.includes("oyunlar"), "app.js, index.html, service worker onu bilmir");
  for (const f of ["assets/komanda.js", "assets/futbol.js"]) assert.equal(read(f).split('import("./oyunlar.js")').length - 1, 1, f + " modulu bir yerdən yükləyir");
  assert.ok(!/getBoundingClientRect|offset(?:Top|Left|Width|Height)|client(?:Width|Height)|inner(?:Width|Height)|scroll[XY]|getComputedStyle/.test(src), "çəkilişdə yerləşdirmə oxuması yoxdur");
  assert.ok(!/setInterval/.test(src), "dövri iş yalnız blok səhifədə olanda (setTimeout + querySelector)");
});

test("oyunlar: futbol blokunda liqaya xüsusi xəritə yoxdur — seçilən hər liqa eyni yolla", () => {
  const fb = read("assets/futbol.js");
  assert.ok(!fb.includes("LIVE_OF") && !fb.includes("leagueLive"), "12 liqalıq canli.json xəritəsi çıxıb");
  assert.ok(fb.includes('const id = teamSlug(l.short || "Premyer Liqa"), O = oyun(id), doc = O?.league(id);'));
  assert.equal(fb.split("${games(fb)}").length - 1, 2, "dünya liqası və Azərbaycan liqası: ikisində də cədvəlin altında");
});

test("pipeline: main yayımı dayaz fetch edir (PR birləşəndən sonra 45 dəqiqəlik dayanma), canlı liqa nüsxələri live budağına gedir", () => {
  const sh = read(".github/scripts/pipeline.sh");
  const pub = sh.slice(sh.indexOf("publish_main() {"), sh.indexOf("\nmilli_step() {"));
  assert.ok(pub.includes('timeout 90 git -C "$REPO_DIR" fetch -q --depth=1 origin "$BRANCH"'), "fetch-depth 1 klonda adi fetch birləşmədən sonra bütün tarixçəni çəkir");
  assert.ok(!/fetch -q origin "\$BRANCH"/.test(pub));
  assert.ok(pub.includes('echo "::warning::main-ə yazılmadı'), "alınmayan yayım logda görünür (əvvəl səssiz idi)");
  const live = sh.slice(sh.indexOf("push_live() {"), sh.indexOf("\n}\n", sh.indexOf("push_live() {")));
  assert.ok(live.includes('for name in "$WORK"/canli/*.json; do') && live.includes('cp "$name" "$dir/liqa-$(basename "$name")"'));
  assert.ok(!/git -C "\$REPO_DIR" add[^\n]*canli/.test(sh), "canlı liqa nüsxələri main-ə yazılmır");
  assert.match(read("updater.py"), /^LIVE_LEAGUE_DIR = ROOT \/ "canli"$/m, "data/-dan kənar: publish_main onu main-ə köçürmür");
});

test("oyunlar: futbol blokunda fayl gələndə yalnız blok yerində dəyişir — oxucu səhifə ilə işləyərkən də gözləmir", async () => {
  const { league } = await mod();
  const real = { fetch: globalThis.fetch, document: globalThis.document }, asked = [];
  const el = { outerHTML: '<div data-oy="cl"></div>' };
  globalThis.document = { querySelector: sel => sel === '[data-oy="cl"]' ? el : null, getElementById: () => null, head: null, visibilityState: "visible" };
  globalThis.fetch = async url => { asked.push(String(url)); return { ok: true, json: async () => fix("cl.json") }; };
  try {
    assert.equal(league("cl"), null, "fayl hələ yoxdur: futbol.js yer tutucu qoyur");
    await new Promise(r => setTimeout(r, 10));
    const files = () => asked.filter(u => u.includes("/data/futbol/"));
    assert.match(files()[0], /\/data\/futbol\/cl\.json$/);
    assert.ok(el.outerHTML.startsWith('<section class="tm-sec oy" data-oy="cl">'), "blok yer tutucunun yerinə qoyuldu");
    assert.ok(league("cl").games.length, "növbəti çəkilişdə fayl yaddaşdandır");
    assert.equal(files().length, 1, "fayl bir dəfə (isti saatda canlı nüsxə də soruşula bilər)");
    assert.equal(league("../x"), null);
  } finally { globalThis.fetch = real.fetch; if (real.document === undefined) delete globalThis.document; else globalThis.document = real.document; }
});
