// Maraqlı videolar (video-maraqli.cjs; sahib, 2026-11-24: «əsas odur onlar kimi sən də tap o cür maraqlı videolar»).
// Sosial hesablara yalnız istifadə hüququmuz olan görüntü gedir: Pixabay/Pexels klipi + Vikipediyanın faktı + SARA səsi.
const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const os = require("node:os");
const path = require("node:path");
const root = path.join(__dirname, "..");
const VM = require("../.github/scripts/video-maraqli.cjs");
const SV = require("../.github/scripts/sosial-video.cjs");
const VX = require("../.github/scripts/video-xeber.cjs");
// Saytın öz qaydası (policyViolation), sadələşdirilmiş nüsxə yox: 2026-11-24 PR-da sadə süzgəclə test keçdi, CI-da isə montaj
// «saytın qaydasından keçmir» deyə dayandı — Vikipediya icazəli mənbələr siyahısında deyildi.
const APP = require("../.github/scripts/topics.cjs").loadApp(root);
const policy = a => APP.policyViolation(a);
const tmp = () => fs.mkdtempSync(path.join(os.tmpdir(), "maraqli-"));

const SOURCE = "The cheetah (Acinonyx jubatus) is a large cat and the fastest land animal. It has a tawny to creamy white or pale buff fur "
  + "that is marked with evenly spaced, solid black spots. The cheetah is capable of running at 93 to 104 km/h (58 to 65 mph); it has evolved "
  + "specialized adaptations for speed, including a light build, long thin legs and a long tail. Its head is small and rounded, with a short "
  + "snout and black tear-like facial streaks. The cheetah is mostly active during the day. It lives in a variety of habitats in Africa and Iran. "
  + "Cheetahs typically reach 67 to 94 cm at the shoulder, and the head-and-body length is between 1.1 and 1.5 m.";
const GOOD = {
  title: "Gepard saatda 104 kilometrə qədər sürətlə qaça bilir",
  text: "Gepard quruda yaşayan heyvanların ən sürətlisidir. Onun yüngül bədəni, uzun nazik ayaqları və uzun quyruğu sürət üçün yaranıb. "
    + "Qaçarkən saatda 93 kilometrdən 104 kilometrədək sürət yığa bilir. Üzündə gözlərindən ağzına doğru uzanan qara zolaqlar var. "
    + "Gepard əsasən gündüz fəaldır və ovuna gizlicə yaxınlaşır. Bu pişikkimilər Afrikada və İranda müxtəlif yerlərdə yaşayır.",
  etiket: ["gepard", "heyvanlar", "maraqlıfaktlar"],
};
// Vikipediya və Gemini (video-ssenari.cjs gemini: əvvəl model siyahısı, sonra generateContent).
function fakeFetch({ answer = GOOD, extract = SOURCE, wiki = [] } = {}) {
  return async (url) => {
    const u = String(url);
    if (u.includes("wikipedia.org/w/api.php")) {
      wiki.push(decodeURIComponent(u.split("titles=")[1]));
      return { ok: true, json: async () => ({ query: { pages: [extract ? { title: "x", extract: `${extract}\n\n== See also ==\nOther cats 1999 2000` } : { missing: true }] } }) };
    }
    if (u.includes("?pageSize")) return { ok: true, json: async () => ({ models: [{ name: "models/gemini-3.6-flash", supportedGenerationMethods: ["generateContent"] }] }) };
    if (u.includes(":generateContent")) return { ok: true, status: 200, json: async () => ({ candidates: [{ content: { parts: [{ text: JSON.stringify(answer) }] } }] }) };
    throw new Error(`gözlənilməz sorğu: ${u}`);
  };
}
const ENV = { GEMINI_API_KEY: "k", PIXABAY_API_KEY: "p", VIDEO_GEMINI_WAIT_MS: "0" };
const fakeGoruntu = (n = 3, calls = []) => async (axtar, dir, o) => {
  calls.push({ axtar, o });
  return Array.from({ length: n }, (_, i) => { fs.writeFileSync(path.join(dir, `klip-${i + 1}.mp4`), "x"); return { file: `klip-${i + 1}.mp4`, p: "Pixabay", id: 100 + i, user: "müəllif", q: axtar[0] }; });
};

test("maraqlı: Vikipediya icazəli dünya mənbəyidir (sahib 2026-11-24: «qaydanı dəyiş»), qırmızı xətt 2 ona da tətbiq olunur", () => {
  const src = fs.readFileSync(path.join(root, "assets/content-policy.js"), "utf8"), P = JSON.parse(src.slice(src.indexOf("{"), src.lastIndexOf("}") + 1));
  assert.deepEqual(P.worldSources.Vikipediya, ["wikipedia.org"]);
  const a = { title: "Gepard quruda ən sürətli heyvandır", summary: "Afrikada yaşayır", source: "Vikipediya", sourceUrl: "https://en.wikipedia.org/wiki/Cheetah", category: "maraqli", lang: "az" };
  assert.equal(policy(a), false);
  assert.equal(policy({ ...a, summary: "Bakıda da görünüb" }), true, "xarici mənbə: Azərbaycan mövzusu düşür");
  assert.equal(policy({ ...a, sourceUrl: "https://evil.example/wiki/Cheetah" }), true, "keçid Vikipediyaya aparmalıdır");
  // Öz video qapısı siyahıdan asılı deyil (sahib: «1-i də et»).
  assert.equal(VM.qayda({ title: "Gepard", summary: "Afrikada yaşayır" }, () => false), false);
  assert.equal(VM.qayda({ title: "Gepard", summary: "Azərbaycanda yaşayıb" }, () => false), true);
  assert.equal(VM.qayda({ title: "Gepard", summary: "İlham Əliyev" }, () => false), true);
  assert.ok(fs.readFileSync(path.join(root, "docs/qirmizi-xetler.md"), "utf8").includes("2026-11-24, sahib («qaydanı dəyiş»): `worldSources`-a **Vikipediya**"));
});

test("maraqlı: mövzular — çoxdur, təkrarsızdır, Azərbaycan və Ermənistan mövzusu yoxdur, axtarış ifadəsi mövzunun adı ilə bitir", () => {
  assert.ok(VM.MOVZULAR.length >= 60, `${VM.MOVZULAR.length} mövzu`);
  assert.equal(new Set(VM.MOVZULAR.map(m => m.id)).size, VM.MOVZULAR.length);
  for (const m of VM.MOVZULAR) {
    assert.ok(/^[a-z0-9-]+$/.test(m.id) && m.az && m.wiki && VM.QRUP[m.qrup], m.id);
    assert.ok(m.axtar.length && m.axtar.every(q => /^[a-z ]+$/.test(q)), `${m.id}: axtarış latınca`);
    assert.ok(!VM.qayda({ title: `${m.az} ${m.wiki}`, summary: m.axtar.join(" ") }, policy) && !/armen|erməni/i.test(`${m.az} ${m.wiki}`), m.id);
  }
  for (const q of ["heyvan", "tebiet", "kosmos"]) assert.ok(VM.MOVZULAR.filter(m => m.qrup === q).length >= 8, q);
});

test("maraqlı: növbə hər gün başqa mövzudan başlayır, son günlərin mövzusu təkrarlanmır", () => {
  const d1 = Date.parse("2026-11-24T08:00:00Z"), d2 = d1 + 86400e3;
  assert.notEqual(VM.novbe(d1)[0].id, VM.novbe(d2)[0].id);
  assert.deepEqual(VM.novbe(d1).map(m => m.id), VM.novbe(d1 + 3600e3).map(m => m.id), "gün ərzində eyni sıra");
  const used = new Set(VM.novbe(d1).slice(0, 3).map(m => m.id));
  assert.ok(!VM.novbe(d1, used).some(m => used.has(m.id)));
  assert.equal(VM.novbe(d1).length, VM.MOVZULAR.length);
});

test("maraqlı: Vikipediyanın mətni — istinadlar və «See also» atılır, məqalə yoxdursa boş", async () => {
  const t = await VM.fakt("Cheetah", fakeFetch());
  assert.ok(t.startsWith("The cheetah") && !t.includes("See also") && !t.includes("1999"));
  assert.equal(await VM.fakt("Yox", fakeFetch({ extract: "" })), "");
  assert.equal(await VM.fakt("X", async () => { throw new Error("şəbəkə"); }), "");
  assert.ok(VM.apiUrl("Giant panda").includes("titles=Giant%20panda") && VM.wikiUrl("Giant panda") === "https://en.wikipedia.org/wiki/Giant_panda");
});

test("maraqlı: Gemini-nin mətni yoxlanır — rəqəm mənbədə, başlıqda sual yox, saytın qaydası", async () => {
  const m = VM.MOVZULAR.find(x => x.id === "gepard"), logs = [];
  const ok = await VM.ssenari(m, SOURCE, { env: ENV, fetch: fakeFetch(), policy, log: s => logs.push(s) });
  assert.equal(ok.uygun, true);
  assert.equal(ok.title, GOOD.title);
  assert.deepEqual(ok.etiket, ["gepard", "heyvanlar", "maraqlıfaktlar"]);
  const uydurma = await VM.ssenari(m, SOURCE, { env: ENV, fetch: fakeFetch({ answer: { ...GOOD, text: GOOD.text.replace("104", "130") } }), policy, log: () => {} });
  assert.equal(uydurma.uygun, false);
  assert.match(uydurma.sebeb, /mənbədə olmayan rəqəm: 130/);
  const sual = await VM.ssenari(m, SOURCE, { env: ENV, fetch: fakeFetch({ answer: { ...GOOD, title: "Gepard nə qədər sürətlə qaçır?" } }), policy, log: () => {} });
  assert.match(sual.sebeb, /sual/);
  const baslig = await VM.ssenari(m, SOURCE, { env: ENV, fetch: fakeFetch({ answer: { ...GOOD, title: "Gepard 300 kilometr sürətlə qaçır" } }), policy, log: () => {} });
  assert.match(baslig.sebeb, /başlıqda mənbədə olmayan rəqəm: 300/);
  const az = await VM.ssenari(m, SOURCE, { env: ENV, fetch: fakeFetch({ answer: { ...GOOD, text: `${GOOD.text} Gepardlar Azərbaycanda da yaşayıb.` } }), policy, log: () => {} });
  assert.equal(az.uygun, false, "qırmızı xətt 2");
  assert.equal((await VM.ssenari(m, "qısa", { env: ENV, fetch: fakeFetch(), policy, log: () => {} })).uygun, false, "mənbə qısadır");
  assert.equal(await VM.ssenari(m, SOURCE, { env: {}, fetch: fakeFetch(), policy, log: () => {} }), null, "açar yoxdur");
});

test("maraqlı: hazırlama — fakt, mətn və görüntü; klip azdırsa növbəti mövzu; görüntü açarı yoxdursa video yoxdur", async () => {
  const now = Date.parse("2026-11-24T08:00:00Z"), dir = tmp(), wiki = [], calls = [];
  let n = 0;
  const goruntu = async (axtar, d, o) => (n++ === 0 ? [] : fakeGoruntu(3, calls)(axtar, d, o));
  const x = await VM.hazirla({ now, env: ENV, fetch: fakeFetch({ wiki }), policy, dir, log: () => {}, goruntu });
  const [first, second] = VM.novbe(now);
  assert.deepEqual(wiki, [first.wiki, second.wiki], "birinci mövzunun klipi yox idi — ikinci");
  assert.equal(x.movzu, second.id);
  assert.equal(x.id, `maraqli-${second.id}-2026-11-24`);
  assert.deepEqual([x.tur, x.kind, x.category, x.bolme, x.source, x.url, x.link], ["maraqli", "maraqli", "maraqli", "Maraqlı", "Vikipediya", VM.LINK, VM.LINK]);
  assert.equal(x.sourceUrl, VM.wikiUrl(second.wiki));
  assert.equal(x.klip.length, 3);
  assert.deepEqual(calls[0].axtar, second.axtar, "klip mövzunun öz adı ilə axtarılır");
  assert.deepEqual([calls[0].o.category, calls[0].o.yer, calls[0].o.say], ["maraqli", [], 6]);
  assert.equal(await VM.hazirla({ now, env: { GEMINI_API_KEY: "k" }, fetch: fakeFetch(), policy, dir, log: () => {}, goruntu }), null);
  // Hazır xeber.json montajın qapısından (video-xeber.cjs render: policy(a) və policy({ ...a, summary: text })) keçir.
  assert.equal(policy(x), false);
  assert.equal(policy({ ...x, summary: x.text }), false);
  // Ümumi səhnə yoxdur: gepard videosunda şəhər görünməsin.
  assert.deepEqual(require("../.github/scripts/video-ssenari.cjs").EHTIYAT.maraqli, []);
});

test("maraqlı: seçim — xəbər videosu ilə növbələşir, gündəlik həddi var, uyğun xəbər olmayanda pəncərəni doldurur", async () => {
  const now = Date.parse("2026-11-24T08:00:00Z"), env = { ...ENV, VIDEO_ACAR: "1" }, sec = now / 1000;
  const mo = SV.maraqliOptions({});
  assert.deepEqual(mo, { on: true, perDay: 10, gapMin: 60 });
  const st = SV.readState("/yoxdur", now);
  assert.equal(SV.maraqliDue(st, now, mo), "");
  st.m = { gepard: sec - 20 * 60 };
  assert.match(SV.maraqliDue(st, now, mo), /20 dəq əvvəl/);
  assert.equal(SV.maraqliDue(st, now, mo, true), "", "xəbər yoxdursa fasilə gözlənmir");
  st.m = Object.fromEntries(VM.MOVZULAR.slice(0, 10).map((m, i) => [m.id, sec - 3 * 3600 - i]));
  assert.match(SV.maraqliDue(st, now, mo, true), /hədd 10/);
  assert.match(SV.maraqliDue(st, now, SV.maraqliOptions({ MARAQLI_VIDEO: "0" })), /söndürülüb/);
  // Vaxtıdır: pəncərədə əvvəl maraqlı video.
  const dir = tmp(), state = SV.readState("/yoxdur", now);
  const x = await SV.sec({ articles: [], env, now, state, policy, dir, log: () => {}, maraqli: o => VM.hazirla({ ...o, goruntu: fakeGoruntu() }), fetch: fakeFetch() });
  assert.equal(x.tur, "maraqli");
  const file = JSON.parse(fs.readFileSync(path.join(dir, "xeber.json"), "utf8"));
  assert.deepEqual(file.klipler, ["klip-1.mp4", "klip-2.mp4", "klip-3.mp4"]);
  assert.equal(file.goruntuMenbe, "Pixabay");
  assert.ok(!("klip" in file));
  assert.equal(state.v[x.id], sec, "ümumi gündəlik həddə və fasiləyə sayılır");
  assert.equal(state.m[x.movzu], sec);
  assert.equal(state._last, sec);
  // Maraqlı videonun fasiləsi dolmayıb, xəbər yoxdur: pəncərə yenə maraqlı video ilə dolur (gündəlik həddə qədər).
  const later = now + 31 * 60e3, d2 = tmp();
  const y = await SV.sec({ articles: [], env, now: later, state, policy, dir: d2, log: () => {}, maraqli: o => VM.hazirla({ ...o, goruntu: fakeGoruntu() }), fetch: fakeFetch() });
  assert.equal(y?.tur, "maraqli");
  assert.notEqual(y.movzu, x.movzu, "mövzu təkrarlanmır");
  // Yalnız xəbər (VIDEO_TUR=xeber) — maraqlı video yoxdur.
  const z = await SV.sec({ articles: [], env: { ...env, VIDEO_TUR: "xeber" }, now: later + 31 * 60e3, state, policy, dir: tmp(), log: () => {}, maraqli: async () => { throw new Error("çağırılmamalı idi"); }, fetch: fakeFetch() });
  assert.equal(z, null);
});

test("maraqlı: paylaşma mətni — mənbə (Vikipediya keçidi), görüntü bankı, rubrikanın etiketləri; xəbər mövzularına düşmür", async () => {
  const x = { ...JSON.parse(fs.readFileSync(path.join(root, "tests/fixtures/video-maraqli.json"), "utf8")), goruntu: [{ p: "Pixabay", id: 1 }], goruntuMenbe: "Pixabay" };
  for (const t of [SV.fbText(x), SV.igText(x)]) {
    assert.ok(t.startsWith(x.title) && t.includes("Məlumat: Vikipediya — https://en.wikipedia.org/wiki/Cheetah") && t.includes("Görüntü: Pixabay"));
    assert.ok(t.includes("#maraqlı #bilirdinizmi #8ulduz") || t.includes("#maraqlı"), "rubrikanın etiketi");
    assert.ok(!t.includes("#xəbərlər"));
  }
  assert.ok(SV.fbText(x).includes("Daha çox: https://8ulduz.az/") && SV.igText(x).includes("keçid profildədir"));
  // video.json (video-xeber.cjs storyFields): YouTube/TikTok yükləyicisi növü və saytın keçidini görür.
  const sf = VX.storyFields(x);
  assert.deepEqual([sf.kind, sf.url, sf.source, sf.own], ["maraqli", "https://8ulduz.az/", "Vikipediya", true]);
  const YT = require("../.github/scripts/youtube.cjs");
  assert.equal(YT.kindOf(sf), "maraqli");
  assert.equal(YT.linkOf(sf), "https://8ulduz.az/");
  assert.equal(YT.policyReason(sf, policy), "", "mənbə qaydasından keçir");
  assert.ok(YT.policyReason({ ...sf, title: "Azərbaycanda gepard" }, policy), "qırmızı xətt 2 YouTube-da da");
});
