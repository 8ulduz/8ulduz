// Video sisteminin dil profili (sahib, 2026-11-26: yol xəritəsinin 2-ci addımı — «video sistemini dildən asılı olmayan et»).
// 1) Hər profil az.json ilə eyni açarlardadır (yeni dil = yeni fayl, kod dəyişmir).
// 2) Sınaq dili (tests/fixtures/video-dil/xx.json, hər mətni «XX»): videoda, səsə gedən mətndə, ssenaridə və paylaşım mətnlərində
//    azərbaycanca şablon mətni qalmır — dilə bağlı hər şey profildən gəlir.
// 3) Profil seçilməyəndə (VIDEO_DIL boş) hər şey az profili ilədir; az profilinin mətnləri əvvəlki kimidir (digər testlər yoxlayır).
// 4) Profili işlədən skript qismən yüklənən (sparse-checkout) hər iş axınında profillər də yüklənir — yoxsa xəta yalnız main-də çıxardı.
"use strict";
const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("fs"), path = require("path");

const root = path.resolve(__dirname, "..");
const read = f => fs.readFileSync(path.join(root, f), "utf8");
const XX_DIR = path.join(__dirname, "fixtures", "video-dil");
const DL = require("../.github/scripts/video-dil.cjs");
const V = require("../.github/scripts/video-xeber.cjs");
const SV = require("../.github/scripts/sosial-video.cjs");
const S = require("../.github/scripts/social.cjs");
const VS = require("../.github/scripts/video-ssenari.cjs");
const VM = require("../.github/scripts/video-maraqli.cjs");
const Y = require("../.github/scripts/youtube.cjs");
const T = require("../.github/scripts/tiktok.cjs");

// Azərbaycanca şablon mətnləri (məzmun deyil): sınaq dilinin çıxışında heç biri olmamalıdır.
const AZ_SABLON = ["Abunə", "ABUNƏ", "Ətraflı", "Mənbə", "Görüntü", "BİLİRDİNİZMİ", "Bilirdinizmi", "səhifəmizi", "keçid profildədir", "#xəbərlər",
  "#Azərbaycan", "#maraqlı", "#bilirdinizmi", "Azərbaycan ədəbi dilində", "Azərbaycan dilində", "kiril hərfi", "«bu gün»", "noyabr", "Daha çox",
  "Məlumat: Vikipediya", "XƏBƏR", "Səkkiz Ulduz", "son xəbərlər", "@8ulduz.az", "@8ULDUZ?", "Maraqlı", "Heyvanlar aləmi"];

function withDil(kod, fn) {
  const keep = { d: process.env.VIDEO_DIL, q: process.env.VIDEO_DIL_QOVLUQ };
  process.env.VIDEO_DIL = kod;
  if (kod === "xx") process.env.VIDEO_DIL_QOVLUQ = XX_DIR;
  try { return fn(); } finally {
    if (keep.d === undefined) delete process.env.VIDEO_DIL; else process.env.VIDEO_DIL = keep.d;
    if (keep.q === undefined) delete process.env.VIDEO_DIL_QOVLUQ; else process.env.VIDEO_DIL_QOVLUQ = keep.q;
  }
}
const keys = (o, pre = "") => Object.entries(o).flatMap(([k, v]) => {
  const p = pre ? `${pre}.${k}` : k;
  // Siyahı və sərbəst lüğət (bölmə → ad, qrup → ad) dəyərdir: içindəki açarlar dildən-dilə fərqlənə bilər.
  return v && typeof v === "object" && !Array.isArray(v) && !/^(video\.bolmeler|lent\.ceki\.bolme|maraqli\.qruplar|youtube\.(nov_etiketleri|bolme_etiketleri))$/.test(p) ? keys(v, p) : [p];
});

test("video-dil: every language profile has exactly the keys of az.json (a new language is a new file, no code change)", () => {
  const az = JSON.parse(read(".github/video-dil/az.json")), want = keys(az).sort();
  const files = [...DL.kodlar().map(k => path.join(DL.QOVLUQ, `${k}.json`)), path.join(XX_DIR, "xx.json")];
  assert.ok(DL.kodlar().includes("az"), "az profili var");
  for (const f of files) {
    const p = JSON.parse(fs.readFileSync(f, "utf8")), kod = path.basename(f, ".json");
    assert.deepEqual(keys(p).sort(), want, `${kod}.json-un açarları az.json ilə eyni olmalıdır`);
    assert.equal(p.kod, kod, `${kod}.json: kod fayl adı ilə eynidir`);
    for (const [k, v] of Object.entries(p.abune)) assert.ok(v.ved && v.say, `${kod}: abune.${k}`);
    assert.equal(p.video.aylar.length, 12, `${kod}: 12 ay`);
  }
  // Nizami ifadələr qurulur, dil kodu yoxlanır, profil dəyişmir.
  const xx = withDil("xx", () => DL.dil());
  assert.equal(xx.kod, "xx");
  assert.ok(xx.re.herf.test("aẋb") && xx.re.bagliyici.test("xxand") && xx.re.protokol.test("they xxmet") && xx.re.yadHerf === null);
  // Video seçiminin tamaşaçı çəkisi də profildəndir (lent.ceki): azərbaycanca bölmə əmsalı və zəif mövzu sözləri sınaq dilinə keçmir.
  assert.equal(withDil("xx", () => SV.cekisi({ title: "XX xxsummit", category: "idman" })), 1, "2 × 0,5");
  assert.equal(withDil("xx", () => SV.cekisi({ title: "Bakıda sammit", category: "medeniyyet" })), 1, "az sözləri və əmsalları xx-də yoxdur");
  assert.equal(SV.cekisi({ title: "Bakıda sammit", category: "medeniyyet" }), 1.4 * 0.6);
  assert.throws(() => DL.dil("../az"), /yanlış dil kodu/);
  assert.throws(() => { "use strict"; DL.dil("az").abune.xeber.ved = "x"; });
  assert.equal(DL.fmt("{a} və {b} {yox}", { a: 1, b: "iki" }), "1 və iki {yox}");
});

test("video-dil: no VIDEO_DIL — everything is the Azerbaijani profile (today's videos do not change)", () => {
  const prev = process.env.VIDEO_DIL;
  delete process.env.VIDEO_DIL;
  try {
    assert.equal(DL.dil().kod, "az");
    assert.deepEqual(V.ABUNE, DL.dil("az").abune);
    assert.equal(V.SUB_TEXT, "ABUNƏ OL");
    assert.equal(VS.PROMPT, VS.promptOf(DL.dil("az")));
    assert.match(VS.PROMPT, /- Azərbaycan ədəbi dilində, 5–7 aydın cümlə/);
    assert.match(VS.PROMPT, /Keçid, emoji, nida və sual işarəsi, kiril hərfi yoxdur\. «bu gün», «dünən», «sabah» yoxdur\./);
    // Profili olmayan dilin videosu (başqa iş axınları) yükləyicidə az profili ilə gedir.
    assert.equal(DL.videonunDili({ lang: "tr" }).kod, "az");
    assert.equal(DL.videonunDili({}).kod, "az");
  } finally { if (prev !== undefined) process.env.VIDEO_DIL = prev; }
});

test("video-dil: test language — the video, the spoken text, the script prompt and every post text come from the profile", () => {
  const a = { id: "0123456789abcdef", title: "Lorem ẋ ipsum dolor", text: "Lorem ẋ ipsum dolor sit amet. Consectetur ẋ adipiscing elit xxand more words here. Sed do eiusmod ẋ tempor.",
    source: "Alpha", alts: [{ source: "Beta" }, { source: "Gamma" }], category: "cemiyyet", bolme: "Cəmiyyət", publishedAt: "2026-11-25T17:03:00Z" };
  const out = withDil("xx", () => {
    const res = {};
    for (const [name, x] of [["xeber", a], ["maraqli", { ...a, tur: "maraqli" }]]) for (const footage of [false, true]) {
      const p = V.prepare({ ...x, goruntuMenbe: "Pixabay" }, { cats: [{ slug: "cemiyyet", label: "Cəmiyyət" }], footage });
      res[`${name}.${footage}`] = { p, ass: V.ass(p, V.timeline(p, null)) };
    }
    res.story = V.storyFields(a);
    const x = { ...a, link: "https://www.8ulduz.az/0123456789abcdef?h=26112517", hashtags: ["lorem"], goruntu: [{}], goruntuMenbe: "Pixabay" };
    res.posts = [undefined, "maraqli"].flatMap(tur => [SV.fbText({ ...x, tur, sourceUrl: "https://en.wikipedia.org/wiki/Cheetah" }), SV.igText({ ...x, tur, sourceUrl: "https://en.wikipedia.org/wiki/Cheetah" })]);
    const m = { ...res.story, hashtags: ["lorem"] };
    res.yt = [Y.descriptionOf(m), Y.tagsOf(m).join(","), Y.descriptionOf({ ...m, kind: "maraqli", id: "maraqli-x-2026-11-25", url: "https://8ulduz.az/" })];
    res.tt = [T.caption(m), T.caption({ ...m, kind: "maraqli" })];
    res.prompts = [VS.promptOf(), VM.promptOf()];
    const sent = "Lorem ẋ ipsum dolor sit amet consectetur adipiscing elit sed do eiusmod tempor incididunt.", six = w => Array(6).fill(w).join(" ");
    res.check = [VS.checkText(six(sent), "", {}), VS.checkText(six(sent.replace("ẋ", "x")), "", {}), VS.checkText(six(sent.replace("Lorem", "Lorem xxtoday")), "", {})];
    res.tags = VS.hashtags(["#Lorem", "xxnews", "привет"]);
    res.protokol = [VS.protokol({ title: "They xxmet today" }), VS.protokol({ title: "Prezident qəbul edib" })];
    res.title = VM.checkTitle("Привет мир это длинный заголовок ẋ", "", () => false);
    res.cand = S.candidates([{ ...a, lang: "xx", alts: [] }, { ...a, id: "0123456789abcdee", lang: "az", alts: [] }], Date.parse(a.publishedAt), { minSources: 1, maxAgeH: 3, lang: DL.dil().lent.dil }).map(x => x.id);
    res.describe = S.describe({ ...a, summary: "Lorem ẋ ipsum dolor sit amet, consectetur adipiscing elit." }, "", () => false, DL.dil().re.herf);
    return res;
  });
  // Gemini-yə göstəriş redaksiyanın dilindədir (azərbaycanca, qəsdən): orada yalnız mətnin dili, yad əlifba və nisbi gün sözləri profildəndir.
  const { prompts, ...shown } = out, all = JSON.stringify(shown);
  for (const s of AZ_SABLON) assert.ok(!all.includes(s), `sınaq dilinin çıxışında azərbaycanca şablon qalıb: «${s}»`);
  for (const s of ["Azərbaycan ədəbi dilində", "Azərbaycan dilində", "kiril hərfi", "«bu gün»"]) assert.ok(!prompts.join("\n").includes(s), `göstərişdə «${s}» qalıb`);
  const ass = out["xeber.true"].ass, p = out["xeber.true"].p;
  assert.ok(ass.includes("XX-SUBSCRIBE") && ass.includes("XX-news-promise") && ass.includes("XX-More:"), "sonluq: düymə, vəd, sayt sətri");
  assert.equal(p.label, "XX-SOCIETY", "bölmənin adı profildən (saytın azərbaycanca adı yox)");
  assert.ok(p.when.includes("xx-nov") && /XX-Source: Alpha, Beta \+1 XX-sites · XX-Footage: Pixabay/.test(p.source));
  assert.deepEqual(p.say.slice(-1), ["XX subscribe. XX news promise."], "səsə gedən çağırış profildən");
  assert.equal(out["maraqli.true"].p.label, "XX-DIDYOUKNOW");
  assert.equal(out.story.lang, "xx", "video.json lang — videonun dili (yükləyicilər profili buradan tapır)");
  assert.ok(out.posts.every(t => t.includes("XX-")) && out.posts[0].includes("XX-More: https://www.8ulduz.az/") && out.posts[0].includes("#xxnews"));
  assert.ok(out.yt[0].includes("XX-news-promise — XX-subscribe: https://www.youtube.com/@8ULDUZ-XX") && out.yt[0].includes("XX-tagline") && out.yt[1].includes("xx society"));
  assert.ok(out.tt[0].includes("XX-More: 8ulduz.az (XX-link-in-profile)") && out.tt[1].includes("XX-facts-promise"));
  assert.ok(out.prompts.every(s => s.includes("XX-language") && s.includes("«xxtoday»")) && !out.prompts[0].includes("kiril"));
  assert.deepEqual(out.check, ["", "XX-not-in-language", "nisbi gün sözü"], "mətnin yoxlaması: profilin hərfi və nisbi gün sözləri; kiril yasağı yoxdur");
  assert.deepEqual(out.tags, ["Lorem", "привет"], "ümumi etiket profildən, kiril əlifbası bu dildə yad deyil");
  assert.deepEqual(out.protokol, [true, false]);
  assert.equal(out.title, "", "yad əlifba yoxdursa başlıq kirilə görə düşmür");
  assert.deepEqual(out.cand, ["0123456789abcdef"], "lentdən yalnız profilin dilindəki xəbərlər");
  assert.ok(out.describe.includes("ẋ"), "izah profilin hərfləri ilə tanınır");
});

test("video-dil: weather video only where the profile says so (its texts are Azerbaijani grammar)", () => {
  assert.equal(DL.dil("az").hava, true);
  assert.equal(withDil("xx", () => DL.dil().hava), false);
  const src = read(".github/scripts/sosial-video.cjs");
  assert.match(src, /app\?\.CITIES && dil\(\)\.hava\) \{/, "sec(): hava budağı profilin hava: true-su ilə");
});

// Qismən yüklənən iş axınları: video-dil.cjs-i (dolayısı ilə) işlədən skript siyahıdadırsa, video-dil.cjs və profil qovluğu da siyahıdadır.
test("video-dil: every sparse checkout that ships a profile-reading script also ships video-dil.cjs and the profiles", () => {
  const dir = path.join(root, ".github/scripts"), cache = new Map();
  const needs = f => {
    if (cache.has(f)) return cache.get(f);
    cache.set(f, false);
    let src = "";
    try { src = fs.readFileSync(path.join(dir, f), "utf8"); } catch { return false; }
    const deps = [...src.matchAll(/require\("\.\/([\w.-]+\.cjs)"\)/g)].map(m => m[1]);
    const r = f === "video-dil.cjs" || /video_ses\.py|video_dinle\.py/.test(f) || deps.some(needs);
    cache.set(f, r);
    return r;
  };
  ["video_ses.py", "video_dinle.py"].forEach(f => cache.set(f, true));
  let checked = 0;
  for (const wf of fs.readdirSync(path.join(root, ".github/workflows")).filter(f => f.endsWith(".yml"))) {
    const yml = read(`.github/workflows/${wf}`);
    for (const m of yml.matchAll(/sparse-checkout: \|\n([\s\S]*?)\n\s*sparse-checkout-cone-mode/g)) {
      const list = m[1].split("\n").map(s => s.trim()).filter(Boolean);
      const scripts = list.filter(x => /^\.github\/scripts\/[\w.-]+\.(cjs|py)$/.test(x)).map(x => path.basename(x));
      if (!scripts.some(needs)) continue;
      checked++;
      assert.ok(list.includes(".github/scripts/video-dil.cjs"), `${wf}: sparse-checkout-da .github/scripts/video-dil.cjs yoxdur`);
      assert.ok(list.includes(".github/video-dil/"), `${wf}: sparse-checkout-da .github/video-dil/ yoxdur`);
    }
  }
  assert.ok(checked >= 5, `profili işlədən qismən yükləmələr: sosial-video, youtube, tiktok, ses-lugat, video-arxiv (${checked})`);
  // PR yoxlaması profil dəyişəndə də işləyir (nümunə videolar, yükləyicilərin testləri).
  for (const wf of ["sosial-video.yml", "youtube.yml", "tiktok.yml"]) {
    const yml = read(`.github/workflows/${wf}`);
    assert.ok(yml.includes("      - .github/scripts/video-dil.cjs\n") && yml.includes("      - .github/video-dil/**\n"), `${wf}: pull_request paths`);
  }
});
