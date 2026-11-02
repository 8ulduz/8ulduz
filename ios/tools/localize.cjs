// İnterfeys dilləri: saytın lüğətindən (assets/dil-*.js) və tətbiqə xas yazılardan (app-strings.json) .strings faylları yaradır.
// İşlətmək: node ios/tools/localize.cjs        faylları yazır
//           node ios/tools/localize.cjs --check lüğətdə olmayan yazıları göstərir
const fs = require("fs");
const path = require("path");

const ios = path.join(__dirname, "..");
const root = path.join(ios, "..");
const LANGS = ["en", "ru", "tr"];

function site(code) {
  const text = fs.readFileSync(path.join(root, "assets", `dil-${code}.js`), "utf8");
  const start = text.indexOf("export default ");
  return JSON.parse(text.slice(start + "export default ".length).trim().replace(/;$/, ""));
}

function swiftFiles(dir, out = []) {
  for (const entry of fs.readdirSync(dir, { withFileTypes: true })) {
    const full = path.join(dir, entry.name);
    if (entry.isDirectory()) swiftFiles(full, out);
    else if (entry.name.endsWith(".swift")) out.push(full);
  }
  return out;
}

// \(x.count) tam ədəddir, qalanı mətn: SwiftUI açarı %lld və %@ ilə qurur.
const INT_EXPR = /count|Count|\.pos$|^minutes$/;
function toKey(literal) {
  return literal
    .replace(/\\\(((?:[^()]|\([^()]*\))*)\)/g, (_, expr) => (INT_EXPR.test(expr) ? "%lld" : "%@"))
    .replace(/\\"/g, '"')
    .replace(/\\n/g, "\n");
}

function literals() {
  const found = new Set();
  const files = [
    ...swiftFiles(path.join(ios, "App")),
    path.join(ios, "Packages/UlduzCore/Sources/UlduzCore/Catalog.swift"),
    path.join(ios, "Packages/UlduzCore/Sources/UlduzCore/TeamData.swift"),
  ];
  for (const file of files) {
    for (const line of fs.readFileSync(file, "utf8").split(/\r?\n/)) {
      if (/^\s*\/\//.test(line) || /^\s*(?:static let|private static let) \w+ = \[/.test(line) && /https?:/.test(line)) continue;
      for (const m of line.matchAll(/"((?:[^"\\]|\\.)*)"/g)) {
        const value = m[1];
        if (!/\p{L}{2}/u.test(value)) continue;
        if (/^[a-z0-9_.-]+$/.test(value) && !/[əüöğıçş]/.test(value)) continue; // açar, simvol, fayl adı
        if (/https?:|mailto:|^\w+\.\w+\.|\.json|^8ulduz-|^[A-Z_]+$|[|\\]{2}|\(\?|\?\?|\\\(.*\? |^[\s,):]|^CFBundle|\w\|\w/.test(value)) continue;
        const before = line.slice(0, m.index);
        if (/(?:systemName|symbol|systemImage|bundleIdentifier|identifier):\s*$/.test(before)) continue;
        found.add(toKey(value));
      }
    }
  }
  const topics = fs.readFileSync(path.join(ios, "Packages/UlduzCore/Sources/UlduzCore/TopicData.swift"), "utf8");
  const tree = JSON.parse(topics.split(/\r?\n/).find(line => line.startsWith('{"SPORT_TEAMS"')));
  const walk = t => { found.add(t.name); if (t.label) found.add(t.label); (t.groups || []).forEach(g => { if (g.group) found.add(g.group); g.items.forEach(walk); }); };
  [...tree.SPORT_TABS, ...tree.REGION_TABS].forEach(walk);
  return found;
}

const ROUND_KEYS = { "%lld xəbər": "count", "Daha çox (%lld)": "more" };
function translate(key, lang, app) {
  if (app[key] !== undefined) return app[key];
  if (lang.w[key] !== undefined) return lang.w[key];
  if (ROUND_KEYS[key]) return lang.t[ROUND_KEYS[key]].replace("$1", "%lld");
  // Sonu nöqtəli və ya iki nöqtəli yazı: lüğətdə işarəsiz saxlanır.
  const edge = key.match(/^(.*?)([.:…]+)$/su);
  if (edge && lang.w[edge[1]] !== undefined) return lang.w[edge[1]] + edge[2];
  return null;
}

function escape(s) {
  return s.replace(/\\/g, "\\\\").replace(/"/g, '\\"').replace(/\n/g, "\\n");
}

function main() {
  const check = process.argv.includes("--check");
  const appFile = path.join(__dirname, "app-strings.json");
  const appAll = fs.existsSync(appFile) ? JSON.parse(fs.readFileSync(appFile, "utf8")) : {};
  const keys = [...literals()].sort();
  const missing = new Map();
  const tables = {};
  for (const code of LANGS) {
    const lang = site(code);
    const app = appAll[code] || {};
    tables[code] = { lang, rows: [] };
    // %, $ işarəli yazılar saytın öz şablonudur: format sətri kimi oxunmasın.
    const data = Object.keys(lang.w).filter(k => !/[%$]/.test(k + lang.w[k]));
    for (const key of [...new Set([...keys, ...Object.keys(app), ...data])].sort()) {
      const value = translate(key, lang, app);
      if (value === null) { if (keys.includes(key)) missing.set(key, (missing.get(key) || []).concat(code)); }
      else tables[code].rows.push([key, value]);
    }
  }
  if (check) {
    console.log(`${keys.length} yazı, ${missing.size} tərcüməsiz`);
    for (const [key, codes] of missing) console.log(JSON.stringify(key), codes.join(","));
    return;
  }
  const res = path.join(ios, "App", "Resources");
  const write = (code, rows) => {
    const dir = path.join(res, `${code}.lproj`);
    fs.mkdirSync(dir, { recursive: true });
    const body = rows.map(([k, v]) => `"${escape(k)}" = "${escape(v)}";`).join("\n");
    fs.writeFileSync(path.join(dir, "Localizable.strings"), `/* ios/tools/localize.cjs yaradır, əl ilə dəyişməyin. */\n${body}\n`);
  };
  for (const code of LANGS) write(code, tables[code].rows);
  // Telefon ingilis dilində olsa da «az» seçiləndə yazılar azərbaycanca qalsın: lookup bu fayla düşür.
  write("az", keys.map(k => [k, k]));

  const dates = {};
  for (const code of LANGS) {
    const { lang } = tables[code];
    dates[code] = { min: lang.t.min, hour: lang.t.hour, day: lang.t.day, round: lang.t.round, place: lang.t.place, until: lang.t.until, now: lang.w["indicə"] || "", mon: lang.mon, monN: lang.monN, mon3: lang.mon3, days: lang.days };
  }
  fs.writeFileSync(path.join(ios, "Packages/UlduzCore/Sources/UlduzCore/UiDates.swift"),
`// ios/tools/localize.cjs yaradır (assets/dil-*.js), əl ilə dəyişməyin.
enum UiDatesData {
    static let json = #"""
${JSON.stringify(dates)}
"""#
}
`);
  console.log(`yazıldı: ${keys.length} açar, ${missing.size} tərcüməsiz`);
}

main();
