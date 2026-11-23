#!/usr/bin/env node
// Saranın oxunuş lüğəti (sahib, 2026-11-23: «tam normal insan kimi oxunsun», «lüğət yolu»).
//
// SARA hər sözü Azərbaycan hərflərinin səsi ilə oxuyur. Azərbaycan yazısı fonetikdir, ona görə səhv yalnız üç yerdən gəlir:
// qısaltmalar (ABŞ, FHN), orijinal yazılışda qalan xarici adlar (Google, Washington, «Celta Vigo») və simvollar. Simvol və
// rəqəmi az_text.py qaydaları həll edir. Qısaltma və xarici adlar isə yüzlərlədir, ona görə əl ilə deyil, lüğətlə həll olunur:
//   1. adaylar: xəbər arxivində böyük hərflə başlayan və heç vaxt kiçik hərflə yazılmayan hər söz və hər qısaltma;
//   2. Gemini paketlərlə soruşulur: «Azərbaycan diktoru bunu necə oxuyar?» (dəyişmirsə boş);
//   3. hər cavabı qaydalar yoxlayır (yoxla()): yalnız Azərbaycan hərfləri, ağlabatan uzunluq; Azərbaycan yazılışlı ad
//      (Xankəndi, Sumqayıt) ən çox 2 hərf dəyişə bilər — Gemini adı «düzəltməsin»;
//   4. lüğət: .github/ses-server/ses-lugat.json (repoda, baxılıb) + həftəlik əlavələr tarixçəsiz «ses-lugat» budağında
//      (lugat.json; main-ə yazılmır). az_text.py ikisini birləşdirir, repodakı üstündür.
//
// İşlədilmə (.github/workflows/ses-lugat.yml):
//   node ses-lugat.cjs qur <çıxış.json>                  — bütün arxivdən baza lüğəti (sonra PR ilə repoya)
//   node ses-lugat.cjs yenile <baza.json> <budaq/lugat.json> — yalnız yeni sözlər, budaq faylı yenilənir
// GEMINI_API_KEY lazımdır. Xəbər yazmır, paylaşmır.
"use strict";
const fs = require("fs");
const path = require("path");

const ROOT = path.resolve(__dirname, "..", "..");
const AZ = "abcçdeəfgğhxıijkqlmnoöprsştuüvyz";
const ALLOWED = new RegExp(`^[${AZ} -]+$`);
const LETTER_NAMES = { a: "a", b: "be", c: "ce", ç: "çe", d: "de", e: "e", ə: "ə", f: "fe", g: "ge", ğ: "ğe", h: "he", x: "xe", ı: "ı",
  i: "i", j: "je", k: "ka", q: "qe", l: "el", m: "em", n: "en", o: "o", ö: "ö", p: "pe", r: "er", s: "es", ş: "şe", t: "te", u: "u",
  ü: "ü", v: "ve", y: "ye", z: "ze" };
const BATCH = 120;
const lowerAz = s => String(s).replace(/I/g, "ı").replace(/İ/g, "i").toLowerCase();
const ROMAN = /^(?=[IVXL]{2,})L?X{0,3}(IX|IV|V?I{0,3})$/;
// İngilis/Avropa yazılışının əlamətləri (Azərbaycan sözündə olmur): w, sh, ch, th, ph, ck, gh, oo, ee, ou, ea, ae, -tion, Mc.
const FOREIGN_SIGN = /w|sh|ch|th|ph|ck|gh|oo|ee|ou|ea|ae|tion$|^mc/i;

// Mətnlər: canlı lent (data/news.json), bölmə arxivi (data/arxiv/*.json), öz xəbərlər (data/oz/*.json). Yalnız azərbaycanca.
function texts(root = ROOT) {
  const out = [];
  const take = a => { if (a && (a.lang || "az") === "az") out.push([a.title, a.summary, a.text].filter(Boolean).join(" ")); };
  const read = f => { try { return JSON.parse(fs.readFileSync(f, "utf8")); } catch { return null; } };
  const news = read(path.join(root, "data/news.json"));
  (news?.articles || []).forEach(take);
  for (const dir of ["data/arxiv", "data/oz"]) {
    const d = path.join(root, dir);
    if (!fs.existsSync(d)) continue;
    for (const f of fs.readdirSync(d).filter(f => f.endsWith(".json"))) {
      const x = read(path.join(d, f));
      (Array.isArray(x) ? x : x?.articles || x?.items || []).forEach(take);
    }
  }
  return [...new Set(out.map(s => s.replace(/\s+/g, " ").trim()).filter(Boolean))];
}

// Adaylar: [{ t: söz, n: say, k: kontekst }]. Qısaltma (2–8 böyük hərf) və heç vaxt kiçik hərflə yazılmayan böyük hərfli söz.
// Rum rəqəmi (qayda həll edir) və «known» (artıq yoxlanmış) çıxarılır.
function candidates(list, known = new Set()) {
  const all = list.join("\n");
  const lower = new Set(all.match(/(?<![\p{L}])[\p{Ll}]+(?![\p{L}])/gu) || []);
  const found = new Map();
  const add = (t, i) => {
    if (known.has(t) || ROMAN.test(t)) return;
    const e = found.get(t);
    if (e) { e.n++; return; }
    found.set(t, { t, n: 1, k: all.slice(Math.max(0, i - 70), i + t.length + 70).replace(/\s+/g, " ").trim() });
  };
  for (const m of all.matchAll(/(?<![\p{L}\d])(\p{Lu}{2,8})(?=\d|[^\p{L}]|$)/gu)) {
    const t = m[1];
    if (t.length > 3 && lower.has(lowerAz(t))) continue;          // «OLDU», «VİDEO» — söz, qayda oxuyur
    add(t, m.index);
  }
  for (const m of all.matchAll(/(?<![\p{L}\d])(\p{Lu}[\p{L}]*\p{Ll}[\p{L}]*)(?![\p{L}])/gu)) {
    const t = m[1];
    if (lower.has(lowerAz(t))) continue;                           // cümlə başında böyük yazılmış adi söz
    add(t, m.index);
  }
  return [...found.values()].sort((a, b) => b.n - a.n || a.t.localeCompare(b.t));
}

function distance(a, b) {
  const d = Array.from({ length: a.length + 1 }, (_, i) => [i, ...Array(b.length).fill(0)]);
  for (let j = 1; j <= b.length; j++) d[0][j] = j;
  for (let i = 1; i <= a.length; i++)
    for (let j = 1; j <= b.length; j++) d[i][j] = Math.min(d[i - 1][j] + 1, d[i][j - 1] + 1, d[i - 1][j - 1] + (a[i - 1] !== b[j - 1]));
  return d[a.length][b.length];
}

// Azərbaycan yazılışlı söz: bütün hərflər əlifbadandır, xarici əlamət yoxdur, qısaltma deyil.
const azLooking = t => [...lowerAz(t)].every(c => AZ.includes(c)) && !FOREIGN_SIGN.test(t) && !/^\p{Lu}{2,}$/u.test(t);

// Gemini cavabının yoxlanması. Qaytarır: oxunuş (lüğətə), "" (dəyişmir) və ya null (rədd).
function yoxla(token, said) {
  if (typeof said !== "string") return null;
  const s = lowerAz(said).replace(/\s+/g, " ").replace(/\s*-\s*/g, "-").trim();
  if (!s) return "";
  if (!ALLOWED.test(s) || s.length > token.length * 6 + 12) return null;
  if (s.replace(/[- ]/g, "") === lowerAz(token)) return "";        // NATO → nato: qayda onsuz da belə oxuyur
  if (azLooking(token) && distance(s.replace(/[- ]/g, ""), lowerAz(token)) > 2) return null;
  // Hərf-hərf oxunuş (a-be-şe) yalnız hərf adlarından ibarət olmalıdır və sırası sözə uyğun gəlməlidir.
  if (/^\p{Lu}{2,8}$/u.test(token) && /-/.test(s) && !/ /.test(s)) {
    const parts = s.split("-");
    const spelled = parts.every(p => Object.values(LETTER_NAMES).includes(p) || /^[a-zəıöüçşğ]+$/.test(p));
    if (!spelled) return null;
  }
  return s;
}

const PROMPT = `Sən Azərbaycan televiziyasının xəbər diktorusan. Aşağıdakı sözlər xəbər mətnlərindən götürülüb (kontekst verilib).
Hər söz üçün onu efirdə necə oxuyacağını yaz: yalnız kiçik Azərbaycan hərfləri (${AZ}), boşluq və tire.

Qaydalar:
- Hərf-hərf oxunan qısaltma: Azərbaycan hərf adları, tire ilə. Hərf adları: a, be, ce, çe, de, e, ə, fe, ge, ğe, he, xe, ı, i, je, ka, qe, el, em, en, o, ö, pe, er, es, şe, te, u, ü, ve, ye, ze. Nümunə: ABŞ → a-be-şe, FHN → fe-he-en, BMT → be-em-te.
- Söz kimi oxunan qısaltma söz kimi: NATO → "", UEFA → "", SOCAR → sokar. Beynəlxalq ingilis qısaltmasını azərbaycanlıların dediyi kimi yaz (CNN → si-en-en, BBC → bi-bi-si).
- Orijinal (ingilis, fransız, alman, ispan…) yazılışda qalan ad: azərbaycanlı diktorun tələffüzü ilə. Nümunə: Washington → vaşinqton, Google → qugl, Bloomberg → blumberq, Celta → selta, Sacramento → sakramento.
- Söz Azərbaycan hərflərinin səsi ilə onsuz da düzgün oxunursa (Xankəndi, Sumqayıt, Makron, Tramp), boş sətir "" qaytar. Azərbaycan adlarını dəyişmə.
- Sözə şəkilçi qoşulubsa (Vaşinqtonun), şəkilçini də oxunuşa daxil et.
- Mənasını dəyişmə, tərcümə etmə, açılışını yazma (ABŞ → "amerika birləşmiş ştatları" YOX, a-be-şe).

Cavab: yalnız JSON obyekt {"söz": "oxunuş və ya boş"}, hər verilən söz üçün bir açar.

Sözlər:
`;

async function ask(batch, { key, f = fetch, log = console.log, env = process.env, gemini } = {}) {
  const g = gemini || require("./video-ssenari.cjs").gemini;
  const list = batch.map(x => `${x.t}\t«${x.k}»`).join("\n");
  const raw = await g(PROMPT + list, key, f, log, { ...env, VIDEO_GEMINI_WAIT_MS: env.VIDEO_GEMINI_WAIT_MS ?? 15000 });
  if (raw == null) return null;
  try {
    const j = JSON.parse(String(raw).replace(/^```(?:json)?\s*|\s*```$/g, ""));
    return j && typeof j === "object" ? j : {};
  } catch { log(`lüğət: JSON oxunmadı (${String(raw).slice(0, 120)})`); return {}; }
}

// Adayları paketlərlə soruşur. Qaytarır: { sozler: {söz: oxunuş}, yoxlanib: [cavab alınan bütün sözlər], redd: [{t, said}] }.
async function build(cands, opt = {}) {
  const log = opt.log || console.log;
  const sozler = {}, yoxlanib = [], redd = [];
  for (let i = 0; i < cands.length; i += BATCH) {
    const batch = cands.slice(i, i + BATCH);
    const ans = await ask(batch, opt);
    if (ans == null) { log(`lüğət: Gemini cavab vermədi, ${i} sözdən sonra dayandı`); break; }
    for (const { t } of batch) {
      if (!(t in ans)) continue;                                    // cavabda yoxdur — növbəti dəfə yenə soruşulacaq
      const ok = yoxla(t, ans[t]);
      if (ok === null) { redd.push({ t, said: ans[t] }); continue; }
      yoxlanib.push(t);
      if (ok) sozler[t] = ok;
    }
    log(`lüğət: ${Math.min(i + BATCH, cands.length)}/${cands.length}, lüğətdə ${Object.keys(sozler).length}, rədd ${redd.length}`);
  }
  return { sozler, yoxlanib, redd };
}

const readJson = (f, d) => { try { return JSON.parse(fs.readFileSync(f, "utf8")); } catch { return d; } };
const sortObj = o => Object.fromEntries(Object.entries(o).sort(([a], [b]) => a.localeCompare(b)));

async function main(argv = process.argv.slice(2), env = process.env) {
  const key = env.GEMINI_API_KEY;
  if (!key) { console.log("::warning::GEMINI_API_KEY yoxdur — lüğət qurulmadı"); return 0; }
  const [mode, a, b] = argv;
  if (mode === "qur" && a) {
    const cands = candidates(texts());
    console.log(`lüğət: ${cands.length} aday`);
    const r = await build(cands, { key, env });
    fs.writeFileSync(a, JSON.stringify({ izah: "Saranın oxunuş lüğəti (ses-lugat.cjs qur): söz → oxunuş. Repodakı baxılmış nüsxədir.",
      sozler: sortObj(r.sozler), yoxlanib: r.yoxlanib.sort(), redd: r.redd }, null, 1) + "\n");
    return 0;
  }
  if (mode === "yenile" && a && b) {
    const base = readJson(a, { sozler: {}, yoxlanib: [] });
    const cur = readJson(b, { sozler: {}, yoxlanib: [] });
    const known = new Set([...Object.keys(base.sozler || {}), ...(base.yoxlanib || []), ...Object.keys(cur.sozler || {}), ...(cur.yoxlanib || [])]);
    const cands = candidates(texts(), known).slice(0, Number(env.SES_LUGAT_MAX || 600));
    console.log(`lüğət: ${cands.length} yeni aday`);
    if (!cands.length) return 0;
    const r = await build(cands, { key, env });
    const out = { izah: "Saranın oxunuş lüğətinə həftəlik əlavələr (ses-lugat.yml). az_text.py repodakı ses-lugat.json ilə birləşdirir.",
      at: new Date().toISOString(), sozler: sortObj({ ...(cur.sozler || {}), ...r.sozler }),
      yoxlanib: [...new Set([...(cur.yoxlanib || []), ...r.yoxlanib])].sort() };
    fs.writeFileSync(b, JSON.stringify(out, null, 1) + "\n");
    console.log(`lüğət: ${Object.keys(r.sozler).length} yeni söz, ${r.redd.length} rədd`);
    for (const x of r.redd.slice(0, 30)) console.log(`  rədd: ${x.t} → ${JSON.stringify(x.said)}`);
    return 0;
  }
  console.error("İşlədilmə: ses-lugat.cjs qur <çıxış.json> | yenile <baza.json> <budaq/lugat.json>");
  return 2;
}

if (require.main === module) main().then(c => { process.exitCode = c; }, e => { console.error(e); process.exitCode = 1; });

module.exports = { texts, candidates, yoxla, build, ask, azLooking, distance, PROMPT, main };
