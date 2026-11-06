// Milli komandaların yarışları (sahib, 2026-11-07: «Milli komandalar, altında ölkələrin milli komandaları; seçəndə iştirak etdikləri
// çempionatlar və oradakı vəziyyətləri — klublar kimi»). Mənbə: ingiliscə Vikipediyanın yarış səhifəsi (CC BY-SA), klub liqaları kimi.
// Hər yarış üçün data/futbol/<id>.json yazır (komanda səhifəsinin formatı: teams, groups, games); siyahıya (index.json) updater.py
// national_rows() əlavə edir. Pipeline-ın yavaş dövrəsində işləyir (pipeline.sh slow_loop), xəbər axınına toxunmur.
// Sorğu azdır: yarış başına 6 saatda bir, oyun günü 30 dəqiqədə bir, bir dövrədə ən çox MAX_FETCH. Alınmasa əvvəlki fayl qalır.
"use strict";
const fs = require("fs"), path = require("path");

const UA = "8ulduz.az/1.0 (https://8ulduz.az) standings";
const API = "https://en.wikipedia.org/w/api.php?format=json&formatversion=2&action=parse&prop=text&redirects=1&page=";
const EVERY_MS = 6 * 3600e3, LIVE_MS = 30 * 60e3, MAX_FETCH = 2;
// id, ad, səhifə, saat qurşağı (səhifədə yazılan vaxtın qurşağı), mövsüm
const SPECS = [
  { id: "ml-a", name: "Millətlər Liqası A", page: "2026–27 UEFA Nations League A", zone: "Europe/Paris", key: "2026", season: "2026/27" },
  { id: "ml-b", name: "Millətlər Liqası B", page: "2026–27 UEFA Nations League B", zone: "Europe/Paris", key: "2026", season: "2026/27" },
  { id: "ml-c", name: "Millətlər Liqası C", page: "2026–27 UEFA Nations League C", zone: "Europe/Paris", key: "2026", season: "2026/27" },
  { id: "ml-d", name: "Millətlər Liqası D", page: "2026–27 UEFA Nations League D", zone: "Europe/Paris", key: "2026", season: "2026/27" },
  { id: "asiya-kuboku", name: "Asiya Kuboku", page: "2027 AFC Asian Cup", zone: "Asia/Riyadh", key: "2027", season: "2027" },
];
// Adlar app.js-dəki «Milli komandalar» siyahısı ilə eynidir: ünvan (teamSlug) addan çıxır.
const AZ = {
  Albania: "Albaniya", Andorra: "Andorra", Armenia: "Ermənistan", Austria: "Avstriya", Azerbaijan: "Azərbaycan", Bahrain: "Bəhreyn", Belarus: "Belarus",
  Belgium: "Belçika", "Bosnia and Herzegovina": "Bosniya və Herseqovina", Bulgaria: "Bolqarıstan", China: "Çin", Croatia: "Xorvatiya", Cyprus: "Kipr",
  "Czech Republic": "Çexiya", Czechia: "Çexiya", Denmark: "Danimarka", England: "İngiltərə", Estonia: "Estoniya", "Faroe Islands": "Farer adaları", Finland: "Finlandiya",
  France: "Fransa", Georgia: "Gürcüstan", Germany: "Almaniya", Gibraltar: "Cəbəllütariq", Greece: "Yunanıstan", Hungary: "Macarıstan", Iceland: "İslandiya",
  Indonesia: "İndoneziya", Iran: "İran", Iraq: "İraq", Israel: "İsrail", Italy: "İtaliya", Japan: "Yaponiya", Jordan: "İordaniya", Kazakhstan: "Qazaxıstan",
  Kosovo: "Kosovo", Kuwait: "Küveyt", Kyrgyzstan: "Qırğızıstan", Latvia: "Latviya", Liechtenstein: "Lixtenşteyn", Lithuania: "Litva", Luxembourg: "Lüksemburq",
  Malta: "Malta", Moldova: "Moldova", Montenegro: "Monteneqro", Netherlands: "Hollandiya", "North Korea": "Şimali Koreya", "North Macedonia": "Şimali Makedoniya",
  "Northern Ireland": "Şimali İrlandiya", Norway: "Norveç", Oman: "Oman", Palestine: "Fələstin", Poland: "Polşa", Portugal: "Portuqaliya", Qatar: "Qətər",
  "Republic of Ireland": "İrlandiya", Romania: "Rumıniya", "San Marino": "San-Marino", "Saudi Arabia": "Səudiyyə Ərəbistanı", Scotland: "Şotlandiya",
  Serbia: "Serbiya", Singapore: "Sinqapur", Slovakia: "Slovakiya", Slovenia: "Sloveniya", "South Korea": "Cənubi Koreya", Spain: "İspaniya", Sweden: "İsveç",
  Switzerland: "İsveçrə", Syria: "Suriya", Tajikistan: "Tacikistan", Thailand: "Tailand", Turkey: "Türkiyə", "Türkiye": "Türkiyə", Ukraine: "Ukrayna",
  "United Arab Emirates": "BƏƏ", Uzbekistan: "Özbəkistan", Vietnam: "Vyetnam", Wales: "Uels", Yemen: "Yəmən", "Kingdom of Saudi Arabia": "Səudiyyə Ərəbistanı",
  Australia: "Avstraliya", India: "Hindistan", Lebanon: "Livan", Malaysia: "Malayziya", Philippines: "Filippin", Turkmenistan: "Türkmənistan", "Hong Kong": "Honkonq",
};
const NOTE = [[/quarter-final/i, "1/4 finala çıxır"], [/promotion play-?off/i, "Yuxarı liqa üçün pley-off"], [/relegation play-?off/i, "Aşağı liqa üçün pley-off"],
  [/promot/i, "Yuxarı liqaya keçid"], [/relegat/i, "Aşağı liqaya düşmə"], [/possible knockout/i, "Sıralamaya görə pley-off şansı"], [/knockout|round of 16/i, "Pley-offa çıxır"]];
const ZONE_ABBR = { CET: "Europe/Paris", CEST: "Europe/Paris", WET: "Europe/Lisbon", WEST: "Europe/Lisbon", BST: "Europe/London", GMT: "Etc/UTC", UTC: "Etc/UTC",
  EET: "Europe/Athens", EEST: "Europe/Athens", TRT: "Europe/Istanbul", MSK: "Europe/Moscow", AZT: "Asia/Baku", AST: "Asia/Riyadh" };

// Mətnə tərcümə edilməmiş komanda adı olduğu kimi qalır (ingiliscə): sayt pozulmur, sonra lüğətə əlavə olunur.
const azName = en => AZ[en] || en;
// app.js teamSlug ilə eyni: kiçik hərf, diakritik işarələr atılır, ə→e, ı→i, söz arası «-».
function slugOf(s) {
  return String(s || "").toLocaleLowerCase("az").normalize("NFD").replace(/[̀-ͯ]/g, "").replace(/ə/g, "e").replace(/ı/g, "i")
    .replace(/[^\p{L}\p{N}]+/gu, "-").replace(/^-+|-+$/g, "");
}
const text = raw => String(raw || "").replace(/<style[\s\S]*?<\/style>|<sup[\s\S]*?<\/sup>/g, "").replace(/<[^>]+>/g, "")
  .replace(/&#160;|&nbsp;/g, " ").replace(/&#91;|&#93;/g, "").replace(/&amp;/g, "&").replace(/&#39;/g, "'").replace(/[−–]/g, "-").replace(/\s+/g, " ").trim();
const int = raw => { const t = text(raw); if (!/^[+-]?\d+$/.test(t)) throw new Error("rəqəm deyil: " + t.slice(0, 20)); return Number(t); };
const teamOf = raw => (raw.match(/title="([^"]+?) (?:national (?:football|soccer) team|men's national football team)"[^>]*>([^<]+)<\/a>/) || [])[2] || "";
// Bayraq: Vikipediyanın 120 px nüsxəsi (klub loqoları kimi; 40 px başlıqda bulanıq görünürdü).
const flagOf = raw => { const m = raw.match(/src="(\/\/[^"]*?Flag_of[^"?]*)/); return m ? "https:" + m[1].replace(/\/\d+px-/, "/120px-") : ""; };

// Saat qurşağındakı vaxt -> ISO (UTC). Intl ilə: kitabxana yoxdur.
function zoned(day, hm, zone) {
  const [y, mo, d] = day.split("-").map(Number), [h, mi] = hm.split(":").map(Number);
  const guess = Date.UTC(y, mo - 1, d, h, mi);
  const parts = Object.fromEntries(new Intl.DateTimeFormat("en-US", { timeZone: zone, hourCycle: "h23", year: "numeric", month: "2-digit", day: "2-digit", hour: "2-digit", minute: "2-digit" })
    .formatToParts(new Date(guess)).map(p => [p.type, p.value]));
  const local = Date.UTC(+parts.year, +parts.month - 1, +parts.day, +parts.hour, +parts.minute);
  return new Date(guess - (local - guess)).toISOString().replace(".000Z", "+00:00");
}

// Bir qrupun cədvəli: «Team» sütunu olan ilk wikitable.
function standings(chunk) {
  for (const table of chunk.match(/<table class="wikitable[\s\S]*?<\/table>/g) || []) {
    const trs = table.match(/<tr[\s\S]*?<\/tr>/g) || [];
    const head = (trs[0] || "").match(/<t[hd]\b[^>]*>[\s\S]*?(?=<t[hd]\b|<\/tr>)/g)?.map(text) || [];
    const col = name => head.findIndex(h => h === name || h.startsWith(name));
    if (col("Team") < 0 || col("Pts") < 0) continue;
    const rows = [];
    let note = "", left = 0;
    for (const tr of trs.slice(1)) {
      const cells = tr.match(/<t[hd]\b[^>]*>[\s\S]*?(?=<t[hd]\b|<\/tr>)/g) || [];
      if (cells.length < col("Pts") + 1) continue;
      const en = teamOf(cells[col("Team")]);
      if (!en) throw new Error("komanda adı tapılmadı");
      const row = { team: slugOf(azName(en)), en, flag: flagOf(cells[col("Team")]), pos: int(cells[0]), p: int(cells[col("Pld")]), w: int(cells[col("W")]), d: int(cells[col("D")]),
        l: int(cells[col("L")]), gf: int(cells[col("GF")]), ga: int(cells[col("GA")]), pts: int(cells[col("Pts")]) };
      row.gd = row.gf - row.ga;
      if (row.w + row.d + row.l !== row.p || row.pts > 3 * row.w + row.d) throw new Error("cədvəl ziddiyyətlidir: " + en);
      const color = cells[0].match(/background-color:(#[0-9a-fA-F]{6})/);
      if (color) row.color = color[1];
      if (left <= 0 && cells.length > col("Pts") + 1) {
        const last = cells[col("Pts") + 1];
        left = Number((last.match(/rowspan="(\d+)"/) || [])[1] || 1);
        note = (NOTE.find(([rx]) => rx.test(text(last))) || [])[1] || "";
      }
      if (note) row.note = note;
      left--;
      rows.push(row);
    }
    if (rows.length >= 3) return rows;
  }
  return null;
}

// Oyun qutuları (Module:Football box): tarix, saat, tərəflər, hesab.
function boxes(chunk, zone, round) {
  const games = [];
  for (const box of chunk.split(/(?=<div[^>]*class="footballbox")/).slice(1)) {
    const home = teamOf((box.match(/<th class="fhome"[\s\S]*?<\/th>/) || [""])[0]), away = teamOf((box.match(/<th class="faway"[\s\S]*?<\/th>/) || [""])[0]);
    const day = (box.match(/itvstart">(\d{4}-\d{2}-\d{2})</) || [])[1];
    if (!home || !away) continue;
    const ft = (box.match(/<div class="ftime">([\s\S]*?)<\/div>/) || [])[1] || "";
    const hm = (text(ft).match(/^(\d{1,2}:\d{2})/) || [])[1];
    const abbr = (text(ft).match(/^\d{1,2}:\d{2}\s+([A-Z]{2,5})\b/) || [])[1];
    const tz = ZONE_ABBR[abbr] || zone;
    // Tarixi elan olunmayan oyun (TBA) da yazılır: səhifədə «Vaxtı elan olunmayıb».
    const game = { date: !day ? "" : hm && tz ? zoned(day, hm, tz) : `${day}T12:00:00+00:00`, home: slugOf(azName(home)), away: slugOf(azName(away)), played: false, round };
    if (day && !hm) game.day = true;
    const score = text((box.match(/<th class="fscore">([\s\S]*?)<\/th>/) || [])[1]);
    const got = score.match(/^(\d+)\s*-\s*(\d+)/);
    if (got) Object.assign(game, { played: true, hs: +got[1], as: +got[2] });
    else if (/postpon|cancel|abandon/i.test(score)) game.state = "off";
    const venue = text((box.match(/itemprop="location"[\s\S]*?<span itemprop="name(?: address)?">([\s\S]*?)<\/span>/) || [])[1]).split(",")[0];
    if (venue) game.stadium = venue.slice(0, 60);
    games.push(game);
  }
  return games;
}

// Səhifə -> komanda səhifəsinin sənədi. Yalnız qrup mərhələsi: qrupların bölmələri «Group_1» / «Group_A».
function parsePage(html, spec) {
  const heads = [...html.matchAll(/<h3[^>]*id="Group_([A-Z0-9]{1,2})"/g)];
  if (!heads.length) throw new Error("qrup tapılmadı");
  const teams = {}, groups = [], games = [];
  heads.forEach((h, i) => {
    const chunk = html.slice(h.index, heads[i + 1] ? heads[i + 1].index : html.indexOf("<h2", h.index + 10) > 0 ? html.indexOf("<h2", h.index + 10) : html.length);
    const name = `Qrup ${h[1]}`, rows = standings(chunk);
    if (!rows) throw new Error(name + ": cədvəl yoxdur");
    for (const r of rows) {
      teams[r.team] = { name: azName(r.en), logo: r.flag };
      delete r.en; delete r.flag;
    }
    groups.push({ name, rows });
    for (const g of boxes(chunk, spec.zone, name)) if (teams[g.home] && teams[g.away]) games.push(g);
  });
  const asof = (html.match(/Updated to match\(es\) played on (\d{1,2}) (\w+) (\d{4})/) || []);
  const MONTHS = ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"];
  return { id: spec.id, name: spec.name, short: spec.name, source: "Vikipediya", url: "https://en.wikipedia.org/wiki/" + encodeURIComponent(spec.page.replace(/ /g, "_")),
    sport: "football", nat: true, asof: asof[1] && MONTHS.includes(asof[2]) ? `${asof[3]}-${String(MONTHS.indexOf(asof[2]) + 1).padStart(2, "0")}-${asof[1].padStart(2, "0")}` : "",
    key: spec.key, season: spec.season, teams, groups, games: games.sort((x, y) => (x.date || "9999").localeCompare(y.date || "9999")) };
}

// Nə vaxt yenidən soruşulsun: oyun gedən və ya nəticəsi gözlənilən gün tez, qalan vaxt 6 saatda bir.
function due(doc, at, now) {
  if (!at) return true;
  const since = now - Date.parse(at);
  if (!doc) return since >= LIVE_MS; // alınmayan yarış hər dövrə soruşulmasın
  if (since >= EVERY_MS) return true;
  const busy = (doc.games || []).some(g => !g.played && g.state !== "off" && Date.parse(g.date) <= now && now - Date.parse(g.date) < 30 * 3600e3);
  return busy && since >= LIVE_MS;
}

async function run(root, { now = Date.now(), fetchText = defaultFetch, log = console.log } = {}) {
  const dir = path.join(root, "data", "futbol");
  fs.mkdirSync(dir, { recursive: true });
  const stateFile = path.join(dir, "milli-yoxlama.json");
  let state = {};
  try { state = JSON.parse(fs.readFileSync(stateFile, "utf8")) || {}; } catch {}
  let asked = 0;
  for (const spec of [...SPECS].sort((a, b) => String(state[a.id] || "").localeCompare(String(state[b.id] || "")))) {
    const file = path.join(dir, `${spec.id}.json`);
    let old = null;
    try { old = JSON.parse(fs.readFileSync(file, "utf8")); } catch {}
    if (asked >= MAX_FETCH || !due(old, state[spec.id], now)) continue;
    asked++;
    state[spec.id] = new Date(now).toISOString();
    try {
      const doc = parsePage(await fetchText(API + encodeURIComponent(spec.page)), spec);
      // Eyni mövsümdə komandaların yarısı dəyişibsə kimsə səhifəni pozub: əvvəlki qalır.
      if (old?.season === doc.season && Object.keys(old.teams || {}).filter(t => !doc.teams[t]).length > Object.keys(doc.teams).length / 2) throw new Error("komandalar dəyişib");
      const textDoc = JSON.stringify(doc);
      if (JSON.stringify(old) !== textDoc) fs.writeFileSync(file, textDoc);
      log(`milli: ${spec.name} — ${doc.groups.length} qrup, ${doc.games.length} oyun`);
    } catch (e) {
      log(`milli: ${spec.name} alınmadı — ${String(e?.message || e).slice(0, 80)}`);
    }
  }
  fs.writeFileSync(stateFile, JSON.stringify(state));
}

async function defaultFetch(url) {
  const r = await fetch(url, { headers: { "user-agent": UA, accept: "application/json" }, signal: AbortSignal.timeout(20000) });
  if (!r.ok) throw new Error("HTTP " + r.status);
  const j = await r.json();
  if (!j?.parse?.text) throw new Error(j?.error?.code || "boş cavab");
  return j.parse.text;
}

module.exports = { SPECS, AZ, slugOf, zoned, standings, boxes, parsePage, due, run };
if (require.main === module) run(process.argv[2] || ".").catch(e => { console.error(String(e?.message || e)); process.exitCode = 1; });
