// Kadrın mövzusu (sahib, 2026-11-27: «nərgizin ölümü videosunda çilingər işləri göstərilir. belə olmaz axı.»).
// İş 46036515482 (YouTube FvteQ4nJnuw): ölüm xəbərinə Gemini «metal crowbar tool» ifadəsi yazdı, Pixabay qazma (39) və qaynaq (12543)
// klipi verdi, söz uyğunluğu «metal» + «tool» ilə keçdi, redaktor ikisini seçdi, video bütünlüklə bu iki klipdən quruldu; mətndə
// «meyiti» də keçdi. Aşağıdakı etiketlər və mətn həmin işin jurnalındandır. Şəbəkə saxtadır. Sənəd: docs/sosial-video.md «Kadrın mövzusu».
"use strict";
const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("fs"), path = require("path"), os = require("os");
const VS = require("../.github/scripts/video-ssenari.cjs");
const VQ = require("../.github/scripts/video-qayda.cjs");
const SV = require("../.github/scripts/sosial-video.cjs");
const root = path.join(__dirname, "..");
const quiet = () => {};

// İş 46036515482-nin jurnalından (Xəbər seç addımı, 16:53:36).
const TEQ_39 = "drill, tool, metal, drilling, hole, work, craft, wimble, flint-borer, working, handicraft, craftsman";
const TEQ_12543 = "sparkles, industry, worker, industrial, metal, steel, equipment, production, technology, factory, manufacture, welding, sparks, "
  + "machine, iron, manufacturing, light, machinery, work, tool, fire, engineering, bright, shiny, energy, plant, modern, heavy, mechanical, plasma, "
  + "working, burn, arc, electric, automobile";
const BASLIQ = "Nərgizi öldürəndən sonra balta ilə doğrayıblar - Ata və ananın qorxunc cinayəti";
// Həmin videonun diktor mətni (Videonu yoxla addımı).
const METN = "Gəncə Ağır Cinayətlər Məhkəməsində dörd il əvvəl itkin düşən qızın qətli ilə bağlı məhkəmə prosesi yekunlaşıb. Ağdamın Yeni "
  + "İmamqulubəyli qəsəbəsində baş verən hadisə zamanı valideynlər qızlarını qətlə yetiriblər. Şikar Nəcəfov və arvadı Ramilə Nəcəfova qızlarının "
  + "həyat tərzini bəhanə edərək onu yatdığı yerdə öldürmək qərarına gəliblər. Ata qızının nəfəs yollarını sıxıb, ögey ana isə onun tərpənməməsi "
  + "üçün ayaqlarından tutub və dəmir linglə zərbələr endirilib. Cinayətdən sonra valideynlər dəhrə və balta ilə meyiti hissələrə bölüblər. "
  + "Məhkəmənin hökmü ilə Şikar Nəcəfov 18 il, Ramilə Nəcəfova isə 14 il 6 ay müddətinə azadlıqdan məhrum edilib.";
// Qan qadağasından keçən mətn: kadr qaydasını ayrıca yoxlamaq üçün (ölüm anı və cəsəd təsvir edilmir).
const TEMIZ = "Gəncə Ağır Cinayətlər Məhkəməsində dörd il əvvəl itkin düşən qızın qətli ilə bağlı məhkəmə prosesi yekunlaşıb. Hadisə Ağdamın "
  + "Yeni İmamqulubəyli qəsəbəsində baş verib. İstintaqa görə, qızın atası və ögey anası onu qətlə yetiriblər. Qız 2020-ci ildə itkin düşüb, "
  + "cinayət 4 il sonra üzə çıxıb. Məhkəmənin hökmü ilə ata 18 il, ögey ana isə 14 il 6 ay müddətinə azadlıqdan məhrum edilib.";
const NERGIZ = { title: BASLIQ, text: TEMIZ, yer: ["Ganja", "Azerbaijan"] };
const MEKTEB = { title: "Bakıda 12 yeni məktəb açılıb", text: "Bakıda 12 yeni məktəb binası istifadəyə verilib. Məktəblərdə 3600 şagird təhsil alacaq.", yer: ["Baku", "Azerbaijan"] };

const hit = (id, tags) => ({ id, duration: 15, user: `u${id}`, tags, pageURL: `https://pixabay.com/videos/x-${id}/`,
  videos: { medium: { url: `https://cdn.pixabay.com/${id}.mp4`, width: 1920, height: 1080, size: 5e6 } } });
// Pixabay + Gemini saxtası: db[ifadə] → kliplər; redaktorun cavabı answer(); soruşulan ifadələr asked-də.
function fake(db, answer = () => null) {
  const asked = [], downloads = [];
  const f = async (u, o = {}) => {
    if (u.startsWith("https://pixabay.com/api/videos/")) { const q = new URL(u).searchParams.get("q"); asked.push(q); return { ok: true, json: async () => ({ hits: db[q] || [] }) }; }
    if (/models\?pageSize/.test(u)) return { ok: true, json: async () => ({ models: [] }) };
    if (/generateContent/.test(u)) {
      const a = answer(JSON.parse(o.body).contents[0].parts[0].text);
      return a == null ? { ok: false, status: 400, json: async () => ({}) } : { ok: true, status: 200, json: async () => ({ candidates: [{ content: { parts: [{ text: JSON.stringify(a) }] } }] }) };
    }
    downloads.push(u);
    return { ok: true, arrayBuffer: async () => new Uint8Array(15000).buffer };
  };
  return { f, asked, downloads };
}
const ENV = { PIXABAY_API_KEY: "k", GEMINI_API_KEY: "g", VIDEO_GEMINI_WAIT_MS: "0" };

test("kadr: the Nərgiz case — a death story, both stock clips (drilling 39, welding 12543) and the «metal crowbar tool» query are refused", () => {
  assert.ok(VS.facie({ title: BASLIQ, text: METN, category: "cemiyyet" }), "bölmə «Cəmiyyət» olsa da, ölüm və cinayət xəbəridir");
  assert.ok(VS.facie({ title: "Yol qəzasında 2 nəfər həlak olub" }) && VS.facie({ title: "x", category: "hadise" }));
  assert.ok(!VS.facie({ title: MEKTEB.title, text: MEKTEB.text, category: "cemiyyet" }));
  assert.ok(!VS.facie({ title: "Ölkə üzrə yeni qaydalar qüvvəyə minib" }), "«ölkə» ölüm sözü deyil");
  const M = { metn: `${BASLIQ}. ${TEMIZ}`, facie: true };
  assert.match(VS.yadMovzu(TEQ_39, M), /faciə xəbərində silah və ya alət \(.*drill.*\)/);
  assert.match(VS.yadMovzu(TEQ_12543, M), /faciə xəbərində silah və ya alət \(tool\)/);
  assert.match(VS.yadMovzu("metal crowbar tool", M), /faciə xəbərində silah və ya alət \(crowbar, tool\)/, "ifadə banka göndərilmir");
  // Faciə olmasa da: qazma və qaynaq xəbərdə yoxdursa yaddır (hər xəbər üçün qayda).
  const adi = { metn: `${BASLIQ}. ${TEMIZ}`, facie: false };
  assert.match(VS.yadMovzu(TEQ_39, adi), /xəbərdə olmayan mövzu: iş və sənət \(craft, craftsman, handicraft\)/);
  assert.match(VS.yadMovzu(TEQ_12543, adi), /xəbərdə olmayan mövzu: iş və sənət/);
  // Söz uyğunluğu: «tool» cins sözüdür, əsas söz «crowbar»-dır — qazma klipi lom deyil.
  assert.equal(VS.relevance("metal crowbar tool", TEQ_39), 0);
  assert.equal(VS.relevance("metal crowbar tool", TEQ_12543), 0);
  assert.ok(VS.relevance("metal crowbar", "crowbar, metal, iron") > 0);
  // Uyğun səhnələr keçir.
  for (const t of ["police, car, lights, night, emergency", "court, courthouse, justice, building", "village, road, night, rural"]) assert.equal(VS.yadMovzu(t, M), "", t);
});

test("kadr: an activity clip needs the activity in the story — welding fits a factory story, a beach fits tourism, never a death story", () => {
  const zavod = { metn: "Gəncədə yeni alüminium zavodu istifadəyə verilib. Zavodda 300 nəfər işləyəcək.", facie: false };
  assert.equal(VS.yadMovzu(TEQ_12543, zavod), "", "zavod xəbərində qaynaq və fabrik kadrı olar");
  assert.match(VS.yadMovzu(TEQ_12543, { metn: `${MEKTEB.title}. ${MEKTEB.text}` }), /iş və sənət/);
  const cimerlik = "beach, sea, summer, tropical, vacation";
  assert.equal(VS.yadMovzu(cimerlik, { metn: "Turizm mövsümündə çimərliklərə gələnlərin sayı artıb." }), "");
  assert.match(VS.yadMovzu(cimerlik, { metn: "Çimərlikdə bir nəfər boğulub.", facie: true }), /şən və ya istirahət əhvalı/, "faciədə adı çəkilsə də");
  assert.match(VS.yadMovzu("kitchen, chef, cooking, food", { metn: `${MEKTEB.title}. ${MEKTEB.text}` }), /mətbəx və yemək/);
  assert.equal(VS.yadMovzu("kitchen, chef, cooking, food", { metn: "Bakıda yeni restoranlar açılıb." }), "");
  assert.match(VS.yadMovzu("woman, portrait, sad", { metn: TEMIZ, facie: true }), /yaxın planda insan/);
  assert.match(VS.yadMovzu("coffin, funeral, church", { metn: TEMIZ, facie: true }), /qan, meyit, ölüm və ya qorxu/);
  // Mətn yoxdursa (hava videosu — səhnələr koddandır) fəaliyyət yoxlanmır.
  assert.equal(VS.yadMovzu(TEQ_12543, {}), "");
});

test("kadr: goruntu never sends the weapon query and drops off-topic clips even when the editor picks them; a death story with only off-topic clips gets none", async () => {
  const db = {
    "metal crowbar tool": [hit(39, TEQ_39), hit(12543, TEQ_12543)],
    "welding sparks": [hit(12543, TEQ_12543)],
    "court building": [hit(1, "court, courthouse, justice, building")],
    // 5 və 4 söz uyğunluğundan keçir (polis, kənd yolu), amma etiketində silah və yaxın planda insan var.
    "police car lights night": [hit(2, "police, car, lights, night, emergency"), hit(5, "police, car, lights, night, pistol, weapon"), hit(39, TEQ_39)],
    "night village road": [hit(3, "village, road, night, rural"), hit(4, "village, road, night, woman, portrait")],
  };
  let prompt = "";
  const { f, asked, downloads } = fake(db, p => { if (/montaj redaktorusan/.test(p)) { prompt = p; return { klip: [1, 2, 3, 4, 5, 6] }; } return null; });
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), "kadr-movzu-"));
  const logs = [];
  const opt = { env: ENV, fetch: f, log: s => logs.push(s), say: 8, category: "cemiyyet", xeber: NERGIZ, yer: NERGIZ.yer };
  const got = await VS.goruntu(["metal crowbar tool", "welding sparks", "court building", "police car lights night", "night village road"], dir, opt);
  assert.deepEqual(got.map(g => g.id).sort(), [1, 2, 3], "yalnız məhkəmə, polis, kənd yolu");
  assert.ok(!asked.includes("metal crowbar tool") && !asked.includes("welding sparks"), "silah və yad fəaliyyət ifadəsi banka getmir");
  assert.ok(!downloads.some(u => /\/(39|12543|4|5)\.mp4$/.test(u)));
  assert.ok(logs.some(s => /ifadə ötürüldü — «metal crowbar tool»: faciə xəbərində silah və ya alət \(crowbar, tool\)/.test(s)));
  assert.ok(logs.some(s => /«police car lights night» Pixabay 5: faciə xəbərində silah və ya alət \(weapon, pistol\)/.test(s)), "uyğun ifadəyə gələn silah kadrı da atılır");
  assert.ok(logs.some(s => /Pixabay 4: faciə xəbərində yaxın planda insan/.test(s)));
  assert.match(prompt, /"xeberin_movzusu"/);
  // Uyğun klip yoxdursa yad klip qoyulmur.
  const only = fake({ "metal tool": [hit(39, TEQ_39)], "industrial work": [hit(12543, TEQ_12543)], "police car lights night": [hit(39, TEQ_39)] },
    p => (/montaj redaktorusan/.test(p) ? { klip: [1, 2] } : null));
  assert.deepEqual(await VS.goruntu(["metal tool", "industrial work"], dir, { ...opt, fetch: only.f, log: quiet }), []);
  assert.deepEqual(only.downloads, []);
  fs.rmSync(dir, { recursive: true, force: true });
});

test("kadr: the editor names what each clip shows; a clip it calls off-topic is dropped even if picked; a death story without the editor gets no clips", async () => {
  const db = { "school building": [hit(11, "school, building, education"), hit(12, "school, building, classroom")] };
  const { f } = fake(db, p => (/montaj redaktorusan/.test(p) ? { movzu: [{ klip: 1, gosterir: "məktəb binası", xeberin_movzusu: true },
    { klip: 2, gosterir: "qazma dəzgahı", xeberin_movzusu: false }], klip: [1, 2] } : null));
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), "kadr-red-"));
  const logs = [];
  const got = await VS.goruntu(["school building"], dir, { env: ENV, fetch: f, log: s => logs.push(s), say: 8, category: "cemiyyet", xeber: MEKTEB, yer: MEKTEB.yer });
  assert.deepEqual(got.map(g => g.id), [11]);
  assert.ok(logs.some(s => /Pixabay 12: redaktor mövzuya yad gördü \(qazma dəzgahı\)/.test(s)));
  // Redaktor cavab vermir: adi xəbərdə ifadə sırası qalır, faciə xəbərində klip qoyulmur.
  const nores = fake({ "school building": db["school building"], "court building": [hit(21, "court, courthouse, justice"), hit(22, "court, building, law")] });
  assert.deepEqual((await VS.goruntu(["school building"], dir, { env: ENV, fetch: nores.f, log: quiet, say: 8, category: "cemiyyet", xeber: MEKTEB })).map(g => g.id), [11, 12]);
  const flogs = [];
  assert.deepEqual(await VS.goruntu(["court building"], dir, { env: ENV, fetch: nores.f, log: s => flogs.push(s), say: 8, category: "cemiyyet", xeber: NERGIZ }), []);
  assert.ok(flogs.some(s => /faciə xəbəri — montaj redaktoru kadrlara baxmadı, klip qoyulmur/.test(s)));
  // Faciə xəbərinin ehtiyat səhnələri hadisə bölməsinindir (insansız), «Cəmiyyət»in «people walking» yox.
  assert.deepEqual(VS.ehtiyat({ category: "cemiyyet", facie: true }), VS.EHTIYAT.hadise);
  fs.rmSync(dir, { recursive: true, force: true });
});

test("kadr: the death story with only off-topic stock footage is skipped for the next story (sosial-video seçim)", async () => {
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), "kadr-sec-"));
  const NOW = Date.parse("2026-11-27T16:50:00Z");
  const SOURCE_N = `${TEMIZ} Hadisə 2020-ci ildə baş verib.`;
  const SOURCE_M = "Bakıda 12 yeni məktəb binası istifadəyə verilib. Layihəyə 45,5 milyon manat ayrılıb. Məktəblərdə 3600 şagird təhsil alacaq. "
    + "Binalarda idman zalı, kitabxana və laboratoriyalar var. Tikinti işləri 2025-ci ildə başlayıb və plana uyğun bitib.";
  const GOOD_M = "Bakıda 12 yeni məktəb binası istifadəyə verilib. Layihəyə 45,5 milyon manat vəsait ayrılıb. Yeni məktəblərdə 3600 şagird "
    + "təhsil alacaq. Hər binada idman zalı, kitabxana və laboratoriyalar yaradılıb. Tikinti işlərinə 2025-ci ildə başlanılıb və işlər plana uyğun "
    + "başa çatdırılıb. Məktəblərin həyətləri də abadlaşdırılıb və yaşıllıq zolaqları salınıb. Məktəblər yeni tədris ilindən fəaliyyət göstərəcək.";
  const art = (c, title, summary, min, category) => ({ id: c.repeat(16), title, summary, category, lang: "az", source: "APA", sourceUrl: `https://apa.az/${c}`,
    publishedAt: new Date(NOW - min * 60e3).toISOString(), alts: [{ source: "Report" }, { source: "Oxu.az" }, { source: "Trend" }] });
  const nergiz = art("a", BASLIQ, SOURCE_N, 5, "cemiyyet"), mekteb = art("b", "Bakıda 12 yeni məktəb binası istifadəyə verilib", SOURCE_M, 10, "cemiyyet");
  const page = s => `<html><body>${s.split(". ").map(x => `<p>${x}. Hadisə haqqında ətraflı məlumat verilir.</p>`).join("")}</body></html>`;
  let story = "";
  const f = async (u, o = {}) => {
    if (u === "https://apa.az/a") return { ok: true, text: async () => page(SOURCE_N) };
    if (u === "https://apa.az/b") return { ok: true, text: async () => page(SOURCE_M) };
    if (/models\?pageSize/.test(u)) return { ok: true, json: async () => ({ models: [] }) };
    if (/generateContent/.test(u)) {
      const pr = JSON.parse(o.body).contents[0].parts[0].text, red = /montaj redaktorusan/.test(pr);
      if (!red) story = /Başlıq: Nərgizi/.test(pr) ? "a" : "b";
      const out = red ? { klip: [1, 2, 3] }
        : story === "a" ? { uygun: true, text: TEMIZ, axtar: ["metal crowbar tool", "metal tool work", "industrial work"], yer: ["Ganja", "Azerbaijan"] }
          : { uygun: true, text: GOOD_M, axtar: ["school building"], yer: ["Baku", "Azerbaijan"] };
      return { ok: true, status: 200, json: async () => ({ candidates: [{ content: { parts: [{ text: JSON.stringify(out) }] } }] }) };
    }
    if (u.startsWith("https://pixabay.com/api/videos/")) {
      // Nərgiz xəbərinə bank yalnız qazma və qaynaq verir (ehtiyat səhnələrə də); məktəbə məktəb.
      return { ok: true, json: async () => ({ hits: story === "a" ? [hit(39, TEQ_39), hit(12543, TEQ_12543)] : [hit(2, "school, building, classroom"), hit(3, "school, building, education")] }) };
    }
    return { ok: true, arrayBuffer: async () => new Uint8Array(15000).buffer };
  };
  const logs = [], state = SV.readState(path.join(dir, "yox.json"), NOW);
  const x = await SV.sec({ articles: [nergiz, mekteb], env: { VIDEO_ACAR: "1", VIDEO_PAYLAS: "0", GEMINI_API_KEY: "g", PIXABAY_API_KEY: "p", VIDEO_GEMINI_WAIT_MS: "0" },
    now: NOW, state, fetch: f, cats: [{ slug: "cemiyyet", label: "Cəmiyyət" }], dir, log: s => logs.push(s) });
  assert.ok(logs.some(s => /ötürülür \(uyğun görüntü 0 klip, ən az 2\) — Nərgizi öldürəndən/.test(s)), logs.join("\n"));
  assert.ok(state.skip[nergiz.id], "Nərgiz xəbəri yad kadrla video olmur");
  assert.equal(x.id, mekteb.id, "növbəti xəbər");
  assert.ok(!JSON.stringify(x.goruntu || []).match(/\b(39|12543)\b/));
  fs.rmSync(dir, { recursive: true, force: true });
});

test("qan qadağası: the news video text and headline go through x.kenar too — the Nərgiz narration («meyiti hissələrə bölüblər») is refused", () => {
  const a = { title: BASLIQ, category: "cemiyyet" };
  assert.match(VS.checkText(METN, METN, a), /qan qadağası: «meyit/);
  assert.equal(VS.checkText(TEMIZ, `${TEMIZ} 2020`, a), "");
  assert.match(VS.checkText(TEMIZ, `${TEMIZ} 2020`, { title: "Çayda kişi MEYİTİ tapılıb" }), /qan qadağası/, "başlıq da, böyük hərflə də");
  assert.match(VQ.GOSTERIS, /Qan qadağası\. «Qanlı», «qan içində», «meyit», «cəsəd» yazma/);
  assert.match(VQ.GOSTERIS, /Ölüm anını \(necə boğulduğu, vurulduğu, hansı alətlə\)/);
  assert.ok(VS.PROMPT.includes(VQ.GOSTERIS));
});

test("kadr: the prompts carry the rule; the profile has the words; the doc records the case", () => {
  assert.match(VS.PROMPT, /Xəbərdə olmayan iş, sənət və fəaliyyəti \(qazma, qaynaq, dülgərlik, fabrik, mətbəx, idman zalı\)/);
  assert.match(VS.PROMPT, /silahı, aləti \(bıçaq, balta,\nlom, çəkic, mişar, tapança\), qanı, meyiti, tabutu/);
  assert.doesNotMatch(VS.PROMPT, /şəhər, təbiət, texnika\)/, "ölüm xəbərinə «texnika» səhnəsi təklif olunmur");
  assert.match(VS.REDAKTOR, /"xeberin_movzusu"/);
  assert.match(VS.REDAKTOR, /cinayətin alətini göstərmə/);
  const az = JSON.parse(fs.readFileSync(path.join(root, ".github/video-dil/az.json"), "utf8"));
  assert.deepEqual(Object.keys(az.kadr.movzu).sort(), Object.keys(VS.MOVZU_TEQ).sort(), "hər fəaliyyətin profildə sözü var");
  assert.ok(/çilingər/.test(az.kadr.movzu.is) && /qətl/.test(az.kadr.facie));
  for (const w of ["crowbar", "axe", "knife", "blood", "corpse", "coffin", "portrait", "beach"]) {
    assert.ok(Object.values(VS.FACIE_TEQ).some(s => s.has(VS.words(w)[0])), w);
  }
  const doc = fs.readFileSync(path.join(root, "docs/sosial-video.md"), "utf8");
  const sec = doc.slice(doc.indexOf("## Kadrın mövzusu"), doc.indexOf("## Media qaydası"));
  for (const w of ["«nərgizin ölümü videosunda çilingər işləri göstərilir. belə olmaz axı.»", "46036515482", "metal crowbar tool", "yadMovzu", "kadr.facie", "KLIP_MIN"]) {
    assert.ok(sec.includes(w), w);
  }
});
