// Oxucuya gedən kod (assets/app.min.js) mənbədən (assets/app.js) qurulur: şərhlər və boşluqlar atılır, daxili adlar qısalır.
// Sahib 2026-11-08: ölçü həddi yayılan fayla aiddir, mənbədəki izahlar oxucunun telefonuna getmir.
//
//   npm ci --prefix .github/kicilt --ignore-scripts   (bir dəfə; terser versiyası package-lock.json-da sabitdir)
//   node .github/kicilt/kicilt.cjs                    (assets/app.js hər dəyişəndə; test köhnə nüsxəni tutur)
//
// Yuxarı səviyyəli adlar da (homeView, shell, S…) qısalır (sahib, 2026-11-13: «hədd artırılmır, gələcək əlavələr üçün ciddi yer açılsın,
// saytın işləyişinə toxunulmasın»): fayl 169 982 → ~157 000 bayt, gzip ~3,3 KB az. Oxucu üçün heç nə dəyişmir: fayl hər yerdə modul kimi
// yüklənir (type="module"), yuxarı adlar modulun içində qalır, başqa skript onları görmür; kodda eval/new Function yoxdur.
//   • Fayl iki hissədə kiçilir («applyPrefs();» sərhədi qalır: ondan əvvəl yalnız tərif — test onu ayrıca işlədir —, sonra açılış);
//     iki hissə eyni ad cədvəlini (nameCache) bölüşür. applyPrefs adı sərhəd sətrində olduğu üçün qısalmır.
//   • Brauzerin öz adları (document, fetch, scrollTo…) heç bir funksiyaya verilmir: bütün faylın sərbəst adları əvvəlcədən tapılır və
//     ayrılır — əks halda bir hissədə qısaldılan ad o biri hissədəki brauzer çağırışını örtə bilərdi.
//   • Test (browser-logic: «the minified code … renders every page the same») kiçildilmiş kodda eyni funksiyaları ad cədvəli ilə
//     çağırıb hər səhifənin HTML-ini mənbə ilə hərfbəhərf tutuşdurur. Xətanın izindəki qısa adı açmaq: node .github/kicilt/kicilt.cjs --adlar
const fs = require("fs"), path = require("path");

const ROOT = path.join(__dirname, "..", "..");
const SRC = "assets/app.js", OUT = "assets/app.min.js";
const MARK = "\napplyPrefs();\n";
// module: true OLMAZ: terser onda toplevel-i məcburi açır və hissədə çağırılmayan yuxarı funksiyaları atır (fayl 49 KB qalırdı).
// app.js-də statik import/export yoxdur, skript kimi oxunur; qısaldılan adlar sərt rejimin ayrılmış sözlərindən də qaçır.
// compress.toplevel sönülüdür: heç bir yuxarı funksiya atılmır və ya birləşdirilmir, yalnız adı qısalır.
const options = (reserved, names) => ({
  ecma: 2020, module: false, toplevel: false,
  compress: { toplevel: false }, mangle: { toplevel: true, reserved }, nameCache: names,
  format: { comments: false },
});
const PREAMBLE = "/* 8ulduz: kiçildilmiş kod. Mənbə assets/app.js, qurmaq: node .github/kicilt/kicilt.cjs (əl ilə dəyişməyin) */";

function terser() {
  try { return require("terser"); } catch {
    throw new Error("terser yoxdur: əvvəlcə «npm ci --prefix .github/kicilt --ignore-scripts» işlədin");
  }
}

// Bütün faylın sərbəst (elan olunmamış) adları: brauzerin verdikləri. Onlar qısa ad kimi işlədilmir.
function freeNames(source) {
  const { ast } = terser().minify_sync(source, { parse: {}, compress: false, mangle: false, format: { ast: true, code: false } });
  ast.figure_out_scope({});
  return [...ast.globals.keys()];
}
// { code, names }: names — mənbədəki yuxarı ad → fayldakı qısa ad (test və xəta izi üçün; fayla yazılmır).
function buildSync(source) {
  const { minify_sync } = terser();
  const s = source.replace(/\r\n/g, "\n");
  const i = s.indexOf(MARK);
  if (i < 0 || s.indexOf(MARK, i + 1) >= 0) throw new Error(`${SRC}: «applyPrefs();» sətri tam bir dəfə olmalıdır`);
  const cache = {}, reserved = ["applyPrefs", ...freeNames(s)];
  const part = code => { const r = minify_sync(code, options(reserved, cache)); if (r.error) throw r.error; return r.code; };
  const code = `${PREAMBLE}\n${part(s.slice(0, i))}${MARK}${part(s.slice(i + MARK.length))}\n`;
  const names = Object.fromEntries(Object.entries(cache.vars?.props || {}).map(([k, v]) => [k.slice(1), v]));
  const taken = new Set(reserved);
  for (const [k, v] of Object.entries(names)) if (taken.has(v)) throw new Error(`«${k}» brauzer adı ilə toqquşan «${v}» adına qısaldı`);
  return { code, names };
}
async function build(source) { return buildSync(source).code; }

module.exports = { build, buildSync, SRC, OUT };

if (require.main === module) {
  const args = process.argv.slice(2), root = args.find(a => !a.startsWith("--")) || ROOT;
  try {
    const source = fs.readFileSync(path.join(root, SRC), "utf8"), { code, names } = buildSync(source);
    if (args.includes("--adlar")) { console.log(JSON.stringify(Object.fromEntries(Object.entries(names).map(([k, v]) => [v, k])), null, 1)); process.exit(0); } // qısa ad → mənbədəki ad
    fs.writeFileSync(path.join(root, OUT), code);
    console.log(`${OUT}: ${Buffer.byteLength(code)} bayt (mənbə ${Buffer.byteLength(source.replace(/\r\n/g, "\n"))})`);
  } catch (e) { console.error(e.message); process.exit(1); }
}
