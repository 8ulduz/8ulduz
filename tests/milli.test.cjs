// Milli komandalar (sahib, 2026-11-07): .github/scripts/milli.cjs, komanda.js «milli-komandalar», menyu (app.js navLeagues).
const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("fs"), os = require("os"), path = require("path"), vm = require("vm");
const root = path.join(__dirname, "..");
const M = require("../.github/scripts/milli.cjs");

const flag = c => `<span class="flagicon"><img alt="" src="//thumb.wikimedia.org/wikipedia/commons/thumb/x/xx/Flag_of_${c}.svg/40px-Flag_of_${c}.svg.png?utm_source=x" /></span>`;
const team = c => `<a href="/wiki/${c}_national_football_team" title="${c} national football team">${c}</a>`;
const row = (pos, c, p, w, d, l, gf, ga, pts, note = "") => `<tr><td style="background-color:#BBF3BB;">${pos}</td><th scope="row">${flag(c)}&#160;${team(c)}</th><td>${p}</td><td>${w}</td><td>${d}</td><td>${l}</td><td>${gf}</td><td>${ga}</td><td>${gf - ga >= 0 ? "+" : ""}${gf - ga}</td><td>${pts}</td>${note}</tr>`;
const box = (day, time, home, score, away) => `<div itemscope="" class="footballbox"><div class="fleft"><time><div class="fdate">${day ? `x<span class="bday dtstart published updated itvstart">${day}</span>` : "TBA"}</div>${time ? `<div class="ftime">${time}</div>` : ""}</time></div><table class="fevent"><tbody><tr><th class="fhome">${team(home)}</th><th class="fscore">${score}</th><th class="faway">${team(away)}</th></tr></tbody></table><div class="fright"><div itemprop="location"><span itemprop="name"><a>Baku Olympic Stadium</a></span>, <span itemprop="address">Baku</span></div></div></div>`;
const HEAD = `<table class="wikitable"><tbody><tr><th><abbr title="Position">Pos</abbr></th><th>Team<style>.x{}</style></th><th>Pld</th><th>W</th><th>D</th><th>L</th><th>GF</th><th>GA</th><th>GD</th><th>Pts</th><th>Qualification</th></tr>`;
const PAGE = `<h2 id="Groups">Groups</h2><h3 id="Group_2">Group 2</h3>${HEAD}
  ${row(1, "Azerbaijan", 3, 1, 2, 0, 3, 2, 5, `<td rowspan="1">Promotion to League C</td>`)}${row(2, "Lithuania", 3, 1, 1, 1, 2, 2, 4, "<td></td>")}${row(3, "Liechtenstein", 2, 0, 1, 1, 1, 2, 1, `<td rowspan="1">Relegation play-offs</td>`)}</tbody></table>
  <p>Times are CET/CEST</p>${box("2026-10-04", "18:00", "Azerbaijan", "1–0", "Lithuania")}${box("2026-11-13", "20:45 <a>CET</a>", "Liechtenstein", "v", "Azerbaijan")}${box("", "", "Lithuania", "Match 6", "Liechtenstein")}
  <h2 id="Goalscorers">Goalscorers</h2>`;

test("milli: the Wikipedia group page becomes a team-page document (table, notes, flags, games in UTC, Azerbaijani names)", () => {
  const doc = M.parsePage(PAGE, M.SPECS[3]);
  assert.equal(doc.id, "ml-d"); assert.equal(doc.name, "Millətlər Liqası D"); assert.equal(doc.nat, true);
  const [g] = doc.groups;
  assert.equal(g.name, "Qrup 2");
  assert.deepEqual(g.rows.map(r => [r.team, r.pos, r.pts, r.gd, r.note || ""]), [["azerbaycan", 1, 5, 1, "Yuxarı liqaya keçid"], ["litva", 2, 4, 0, ""], ["lixtensteyn", 3, 1, -1, "Aşağı liqa üçün pley-off"]]);
  assert.deepEqual(doc.teams.azerbaycan, { name: "Azərbaycan", logo: "https://thumb.wikimedia.org/wikipedia/commons/thumb/x/xx/Flag_of_Azerbaijan.svg/120px-Flag_of_Azerbaijan.svg.png" }, "bayraq 120 px, sorğu parametrsiz");
  const [played, next, tba] = doc.games;
  assert.deepEqual(played, { date: "2026-10-04T16:00:00+00:00", home: "azerbaycan", away: "litva", played: true, round: "Qrup 2", hs: 1, as: 0, stadium: "Baku Olympic Stadium" }, "18:00 CEST = 16:00 UTC");
  assert.equal(next.date, "2026-11-13T19:45:00+00:00", "20:45 CET (qış vaxtı) = 19:45 UTC"); assert.equal(next.played, false);
  assert.equal(tba.date, "", "vaxtı elan olunmayan oyun da var (səhifədə «Vaxtı elan olunmayıb»)");
  assert.throws(() => M.parsePage("<p>səhifə dəyişib</p>", M.SPECS[0]), /qrup/);
  assert.throws(() => M.parsePage(PAGE.replace("<td>3</td><td>1</td><td>2</td>", "<td>3</td><td>9</td><td>2</td>"), M.SPECS[3]), /ziddiyyət/, "səhv redaktə yazılmır");
});

test("milli: asks Wikipedia rarely (6 h, 30 min on match days, 2 per cycle) and keeps the old file when it fails", async () => {
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), "milli-"));
  const asked = [];
  const now = Date.parse("2026-11-13T21:00:00Z");
  await M.run(dir, { now, log: () => {}, fetchText: async url => { asked.push(decodeURIComponent(url)); if (url.includes("League_D") || url.includes("League%20D")) return PAGE; throw new Error("HTTP 503"); } });
  assert.equal(asked.length, 2, "bir dövrədə ən çox 2 sorğu");
  await M.run(dir, { now: now + 60e3, log: () => {}, fetchText: async url => { asked.push(decodeURIComponent(url)); return url.includes("League%20D") ? PAGE : Promise.reject(new Error("503")); } });
  await M.run(dir, { now: now + 120e3, log: () => {}, fetchText: async url => { asked.push(decodeURIComponent(url)); return url.includes("League%20D") ? PAGE : Promise.reject(new Error("503")); } });
  assert.equal(asked.length, 5, "hər yarış bir dəfə; alınmayan yarış dərhal yenidən soruşulmur");
  await M.run(dir, { now: now + 31 * 60e3, log: () => {}, fetchText: async url => { asked.push(url); throw new Error("503"); } });
  assert.equal(asked.length, 7, "30 dəqiqədən sonra yenidən (dövrədə 2)");
  const file = path.join(dir, "data/futbol/ml-d.json");
  assert.equal(JSON.parse(fs.readFileSync(file, "utf8")).groups[0].rows[0].team, "azerbaycan");
  assert.ok(!fs.existsSync(path.join(dir, "data/futbol/ml-a.json")), "alınmayan yarışın faylı yazılmır");
  const doc = JSON.parse(fs.readFileSync(file, "utf8"));
  assert.equal(M.due(doc, new Date(now).toISOString(), now + 20 * 60e3), false, "oyun günü də 30 dəqiqədən tez yox");
  assert.equal(M.due(doc, new Date(now).toISOString(), now + 31 * 60e3), true, "nəticəsi gözlənilən oyun var: 30 dəqiqədən sonra");
  assert.equal(M.due({ games: [] }, new Date(now).toISOString(), now + 5 * 3600e3), false, "sakit gün: 6 saatdan tez yox");
  assert.equal(M.due({ games: [] }, new Date(now).toISOString(), now + 6 * 3600e3), true);
});

test("milli: the menu lists the national teams under the leagues and each opens its page; names match the data and news filter", () => {
  const app = fs.readFileSync(path.join(root, "assets/app.js"), "utf8");
  const list = app.match(/nat = "([^"]+)"\.split\(","\)/)[1].split(",");
  const k = fs.readFileSync(path.join(root, "assets/komanda.js"), "utf8").replace(/^export /gm, "");
  const ctx = vm.createContext({});
  vm.runInContext(k.split("// Komandanın oyunları")[0] + ";this.out={MILLI,NAT,natRx};", ctx);
  const { MILLI, NAT, natRx } = ctx.out;
  assert.equal(MILLI, "milli-komandalar");
  assert.deepEqual(Object.values(NAT).map(x => x[0]), list, "menyudakı ölkələr komanda səhifəsinin siyahısı ilə eynidir");
  assert.deepEqual(Object.keys(NAT), list.map(M.slugOf), "ünvan addan çıxır (app.js teamSlug, milli.cjs slugOf)");
  for (const name of list.filter(n => n !== "Azərbaycan" && !["Rusiya", "Braziliya", "ABŞ"].includes(n))) assert.ok(Object.values(M.AZ).includes(name), name + ": Vikipediyadakı adı tərcümə olunur");
  const hit = (name, s) => natRx(name).test(s.toLocaleLowerCase("az"));
  assert.ok(hit("İspaniya", "İspaniya millisinin heyəti açıqlandı") && hit("İspaniya", "Сборная Испании обыграла Хорватию") && hit("İspaniya", "İspanya Milli Takımı"));
  assert.ok(!hit("Türkiyə", "Türkiyə Milli Məclisinin sədri") && !hit("İspaniya", "İspaniya çempionatında Barselona qalib gəlib"), "klub və siyasət xəbəri milli komandaya düşmür");
  assert.ok(hit("Hollandiya", "Niderland yığması") && hit("ABŞ", "ABŞ millisi") && hit("Səudiyyə Ərəbistanı", "Səudiyyə millisi"));
  assert.ok(k.includes("if (r.liga === MILLI) {") && k.includes("${esc(doc.name)}: xəbərlər</h2>"), "milli komanda səhifəsi və liqa səhifəsinin altında xəbərlər");
});

test("milli: the pipeline runs the script in the slow cycle and updater lists the competitions", () => {
  const sh = fs.readFileSync(path.join(root, ".github/scripts/pipeline.sh"), "utf8").replace(/\r\n/g, "\n");
  assert.ok(sh.includes('timeout -k 5 60 node "$REPO_DIR/.github/scripts/milli.cjs" "$WORK"') && sh.includes('run_py --slow "$SLOW_LIMIT" || echo "yavaş dövrə xəta verdi"\n    milli_step\n'));
  const py = fs.readFileSync(path.join(root, "updater.py"), "utf8").split(String.fromCharCode(13)).join("");
  assert.ok(py.includes('NATIONAL_DOCS = ("ml-a", "ml-b", "ml-c", "ml-d", "asiya-kuboku")') && py.includes("    leagues += national_rows()\n"));
  assert.deepEqual(M.SPECS.map(s => s.id), ["ml-a", "ml-b", "ml-c", "ml-d", "asiya-kuboku"]);
});
