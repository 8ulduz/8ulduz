// Oxucuya gedən kod (assets/app.min.js) mənbədən (assets/app.js) qurulur: şərhlər və boşluqlar atılır, daxili adlar qısalır.
// Sahib 2026-11-08: ölçü həddi yayılan fayla aiddir, mənbədəki izahlar oxucunun telefonuna getmir.
//
//   npm ci --prefix .github/kicilt --ignore-scripts   (bir dəfə; terser versiyası package-lock.json-da sabitdir)
//   node .github/kicilt/kicilt.cjs                    (assets/app.js hər dəyişəndə; test köhnə nüsxəni tutur)
//
// Yuxarı səviyyəli adlar (homeView, shell, S…) qısalmır: test kiçildilmiş kodda eyni funksiyaları çağırıb mənbə ilə müqayisə
// edir, brauzerdə xəta adı oxunaqlı qalır (gzip ölçüsü eynidir, 2026-11-08 ölçüsü). «applyPrefs();» sətri sərhəd kimi
// saxlanır: ondan əvvəlki hissə yalnız tərifdir (test və prerender onu ayrıca işlədir), sonrakı hissə açılışdır.
const fs = require("fs"), path = require("path");

const ROOT = path.join(__dirname, "..", "..");
const SRC = "assets/app.js", OUT = "assets/app.min.js";
const MARK = "\napplyPrefs();\n";
// module: true OLMAZ: terser onda toplevel-i məcburi açır və hissədə çağırılmayan yuxarı funksiyaları atır (fayl 49 KB qalırdı).
// app.js-də statik import/export yoxdur, skript kimi oxunur; qısaldılan adlar sərt rejimin ayrılmış sözlərindən də qaçır.
const OPTIONS = {
  ecma: 2020, module: false, toplevel: false,
  compress: { toplevel: false }, mangle: { toplevel: false },
  format: { comments: false },
};
const PREAMBLE = "/* 8ulduz: kiçildilmiş kod. Mənbə assets/app.js, qurmaq: node .github/kicilt/kicilt.cjs (əl ilə dəyişməyin) */";

function terser() {
  try { return require("terser"); } catch {
    throw new Error("terser yoxdur: əvvəlcə «npm ci --prefix .github/kicilt --ignore-scripts» işlədin");
  }
}

async function build(source) {
  const { minify } = terser();
  const s = source.replace(/\r\n/g, "\n");
  const i = s.indexOf(MARK);
  if (i < 0 || s.indexOf(MARK, i + 1) >= 0) throw new Error(`${SRC}: «applyPrefs();» sətri tam bir dəfə olmalıdır`);
  const part = async code => (await minify(code, OPTIONS)).code;
  return `${PREAMBLE}\n${await part(s.slice(0, i))}${MARK}${await part(s.slice(i + MARK.length))}\n`;
}

module.exports = { build, SRC, OUT };

if (require.main === module) {
  const root = process.argv[2] || ROOT;
  build(fs.readFileSync(path.join(root, SRC), "utf8")).then(code => {
    fs.writeFileSync(path.join(root, OUT), code);
    console.log(`${OUT}: ${Buffer.byteLength(code)} bayt (mənbə ${Buffer.byteLength(fs.readFileSync(path.join(root, SRC), "utf8").replace(/\r\n/g, "\n"))})`);
  }).catch(e => { console.error(e.message); process.exit(1); });
}
