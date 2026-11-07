#!/usr/bin/env node
// «Dinlə» üçün təbii Azərbaycan səsi hər telefonda (sahib, 2026-11-07: «səslə bağlı önəmli olan istifadə edən üçün çox rahat olsun»).
// Telefonların çoxunda Azərbaycan səsi yoxdur (türk səsi ilə oxuyur). Ona görə əsas xəbərlərin səsi Microsoft Azure-un Babək (az-AZ)
// səsi ilə əvvəlcədən hazırlanır və ayrıca «ses» budağına mp3 kimi yazılır (ses/<id>.mp3). Sayt mp3-ü yalnız «Dinlə» basılanda
// raw.githubusercontent.com-dan götürür (dinle.js); yoxdursa cihazın öz səsi işləyir. main-ə və sayta heç nə yazılmır, budaq
// tarixçəsizdir (valideynsiz commit), SES_KEEP_DAYS-dan köhnə fayllar silinir — repo və sayt ağırlaşmır.
// AZURE_SPEECH_KEY sirri yoxdursa iş heç nə etmədən bitir. Pulsuz Azure limiti (ayda 500 000 simvol) aşılmasın deyə gündəlik və
// aylıq simvol həddi budaqdakı usage.json-da sayılır. Mətn saytda göstərilən başlıq + xülasədir (dinle.js textOf), mənbənin tam mətni
// deyil; xəbərlər saytın öz lentindən gəlir və app.js policyViolation-dan keçir (qırmızı xətt 2).
"use strict";
const path = require("node:path"), { execFileSync } = require("node:child_process"), { pathToFileURL } = require("node:url");

const SITE = "https://8ulduz.az/", BRANCH = "ses", VOICE = "az-AZ-BabekNeural";
const SES_KEEP_DAYS = 3, PER_RUN = 12, DAY_CHARS = 15000, MONTH_CHARS = 450000, MAX_AGE_H = 30;

const sources = a => 1 + (a.alts || []).length;
// Hansı xəbərlər səslənsin: Azərbaycan dilində, son 30 saatın, çox mənbəli olanlar önə (oxucunun ən çox açdığı), sonra yenilər.
function pick(articles, have, now, ok = () => true) {
  return articles
    .filter(a => /^[0-9a-f]{16}$/.test(String(a?.id || "")) && (a.lang || "az") === "az" && a.title && !have.has(a.id) && ok(a))
    .filter(a => { const t = Date.parse(a.publishedAt); return t && now - t < MAX_AGE_H * 3600e3 && t <= now + 600e3; })
    .sort((x, y) => sources(y) - sources(x) || String(y.publishedAt).localeCompare(String(x.publishedAt)));
}

const xml = s => String(s).replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;");
const ssml = text => `<speak version="1.0" xmlns="http://www.w3.org/2001/10/synthesis" xml:lang="az-AZ"><voice name="${VOICE}">${xml(text)}</voice></speak>`;

// Simvol hesabı: { "2026-11": n, "2026-11-07": n } — yalnız cari ay və gün saxlanır.
function budget(usage, now) {
  const d = new Date(now).toISOString(), month = d.slice(0, 7), day = d.slice(0, 10);
  return { month, day, left: Math.max(0, Math.min(MONTH_CHARS - (usage[month] || 0), DAY_CHARS - (usage[day] || 0))) };
}

const gitB = (dir, args, input) => execFileSync("git", ["-C", dir, ...args], { input, maxBuffer: 64 << 20 });
const git = (dir, args, input) => gitB(dir, args, input).toString("utf8").trim();

async function tts(text, key, region) {
  const r = await fetch(`https://${region}.tts.speech.microsoft.com/cognitiveservices/v1`, {
    method: "POST", signal: AbortSignal.timeout(30000),
    headers: { "Ocp-Apim-Subscription-Key": key, "Content-Type": "application/ssml+xml", "X-Microsoft-OutputFormat": "audio-24khz-48kbitrate-mono-mp3", "User-Agent": "8ulduz-ses" },
    body: ssml(text),
  });
  if (!r.ok) throw new Error(`Azure ${r.status}`);
  const buf = Buffer.from(await r.arrayBuffer());
  if (buf.length < 2000) throw new Error("Azure: boş səs");
  return buf;
}

async function main(root, dir, env = process.env) {
  const key = env.AZURE_SPEECH_KEY, region = env.AZURE_SPEECH_REGION || "westeurope";
  if (!key) { console.log("ses: AZURE_SPEECH_KEY yoxdur — səs hazırlanmır (sayt cihazın səsi ilə oxuyur)"); return; }
  const { loadApp } = require("./topics.cjs");
  const app = loadApp(root), now = Date.now();
  const { textOf } = await import(pathToFileURL(path.join(root, "assets/dinle.js")).href);
  let articles = [];
  try { const r = await fetch(`${SITE}data/news.json?t=${now}`, { signal: AbortSignal.timeout(30000) }); if (r.ok) articles = (await r.json()).articles || []; } catch {}
  if (articles.length < 50) { console.log(`ses: lent alınmadı (${articles.length})`); return; }
  // Budaqdakı fayllar: <id>.mp3 (blob-un özü endirilmir), usage.json.
  const have = new Map(); let usage = {};
  try {
    for (const line of git(dir, ["ls-tree", "HEAD"]).split("\n").filter(Boolean)) {
      const m = line.match(/^100644 blob ([0-9a-f]{40})\t(.+)$/);
      if (m && /^[0-9a-f]{16}\.mp3$/.test(m[2])) have.set(m[2].slice(0, 16), m[1]);
      if (m && m[2] === "usage.json") usage = JSON.parse(git(dir, ["cat-file", "blob", m[1]]));
    }
  } catch {}
  const live = new Set(articles.map(a => a.id));
  let dropped = 0;  // lentdən çıxmış və SES_KEEP_DAYS-dan köhnə xəbərin səsi silinir
  const born = id => Number(usage.t?.[id] || 0);
  for (const id of [...have.keys()]) if (!live.has(id) && now - born(id) > SES_KEEP_DAYS * 864e5) { have.delete(id); dropped++; }
  const b = budget(usage, now);
  let left = b.left, made = 0;
  const t = { ...(usage.t || {}) };
  for (const a of pick(articles, have, now, x => !app.policyViolation(x))) {
    if (made >= PER_RUN) break;
    const text = textOf(a);
    if (text.length > left) break;
    try { have.set(a.id, git(dir, ["hash-object", "-w", "--stdin"], await tts(text, key, region))); }
    catch (e) { console.log("ses:", a.id, e.message); if (/40[13]|429/.test(e.message)) break; continue; }
    left -= text.length; made++; t[a.id] = now;
  }
  if (!made && !dropped) { console.log("ses: yeni səs yoxdur"); return; }
  const used = b.left - left;
  for (const id of Object.keys(t)) if (!have.has(id)) delete t[id];
  usage = { [b.month]: (usage[b.month] || 0) + used, [b.day]: (usage[b.day] || 0) + used, t };
  const u = git(dir, ["hash-object", "-w", "--stdin"], JSON.stringify(usage));
  const rows = [...have].sort().map(([id, sha]) => `100644 blob ${sha}\t${id}.mp3`).concat(`100644 blob ${u}\tusage.json`);
  const tree = git(dir, ["mktree"], rows.join("\n") + "\n");
  const commit = git(dir, ["-c", "user.name=8ulduz-bot", "-c", "user.email=bot@8ulduz.az", "commit-tree", tree, "-m", "Xəbər səsləri"]);
  git(dir, ["push", "-q", "--force", "origin", `${commit}:refs/heads/${BRANCH}`]);
  console.log(`ses: ${made} yeni səs, ${dropped} köhnə silindi, budaqda ${have.size}; bu ay ${usage[b.month]} simvol`);
}

module.exports = { pick, ssml, budget, main, SES_KEEP_DAYS, MONTH_CHARS, DAY_CHARS };
if (require.main === module) main(path.resolve(process.argv[2] || "."), path.resolve(process.argv[3] || ".ses")).catch(e => { console.error("ses:", e?.message || e); process.exitCode = 1; });
