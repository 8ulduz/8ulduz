// Öz videolarımızın veb nüsxəsi (sahib, 2026-11-25: «ən vacib qırmızı cizgi-gözqırpımı sürətidir», «video xəbərlərdə bəzi videolar
// (əsasən azərbaycan) 1-2 saniyəyə açılır»). Ana səhifənin «Video xəbərlər» zolağı (assets/vlent.js) öz videolarımızı YouTube
// oynadıcısı ilə oynadırdı: basışdan ilk kadra 1,7–2,4 s, telefonda qara ekran, fırlanan dairə, ⏸ və «Shorts» yazısı. X videoları
// (adi <video>) 0,2–0,5 s-ə başlayır. Bu skript YouTube-a yüklənmiş videonun kiçik nüsxəsini Cloudflare R2-yə yazır; zolaq onu X
// videosu kimi adi <video> ilə oynadır. Telekanalların YouTube videoları YouTube oynadıcısında qalır.
//
// sosial-video.yml işə salır:
//   node .github/scripts/veb-video.cjs hazirla <video.mp4> <veb.mp4>   «video» işi: ffmpeg ilə 720×1280, ≤ MAX_BYTES, moov əvvəldə
//   node .github/scripts/veb-video.cjs yukle <veb.mp4> <YouTube nömrəsi> «veb-video» işi: R2-yə <nömrə>.mp4 və index.json
//
// Saxlama yeri (2026-11-25, curl ilə yoxlanıb): R2 + öz domen BASE. Range (206), Content-Type video/mp4 (yükləyəndə verilir),
// yönləndirmə yoxdur, Cloudflare-in Bakı kənarından (GYD) verilir, pulsuz plan (10 GB, çıxış trafiki pulsuz), main-in tarixçəsinə
// heç nə yazılmır, yalnız GitHub Actions yazır. Rədd olunanlar: raw.githubusercontent.com (application/octet-stream + nosniff —
// iPhone Safari-də risk), GitHub Pages (fayl main-ə düşür, tarixçə şişir), GitHub Release (302 → bfcache sönür), jsDelivr (budaq
// 12 saat keşlənir, üçüncü tərəf). Qurulum (sahib): docs/veb-video.md.
//
// Sayt ünvanı yalnız yoxlamadan keçəndən sonra görür: fayl yüklənir, açıq ünvan Range ilə soruşulur (206, video/mp4, 3xx yox), sonra
// index.json-a yazılır. updater.py (update_video, yavaş dövrə) index.json-u oxuyur və öz kanalımızın videosuna data/video.json-da
// «mp4» sahəsini verir. Açar yoxdursa iş sakitcə ötürür: zolaq YouTube oynadıcısı ilə qalır.
// Qırmızı xətt 2: yeni xəbər yolu deyil — faylda yalnız video var (o artıq qaydadan keçib, youtube.cjs policyReason), index.json-da
// yalnız YouTube nömrələri; lentə düşən sətir data/video.json-da onsuz da olan öz videomuzdur.
"use strict";
const fs = require("fs"), path = require("path"), crypto = require("crypto");

const BASE = "https://video.8ulduz.az/";   // assets/vlent.js OWN_BASE və updater.py VEB_VIDEO_URL ilə eyni (tests/veb-video.test.cjs)
const BUCKET = "8ulduz-video";
const ID = /^[\w-]{6,20}$/;
const W = 720, H = 1280;                  // kartın eni ≤ 240 CSS px (3× ekranda 720 nöqtə); tam ekranda da yazılar oxunaqlıdır
const MAX_BYTES = 2.8e6, HARD_BYTES = 3.5e6, AUDIO_BPS = 64000;
const KEEP_DAYS = 30, KEEP_MAX = 300;     // zolaq kanalın son 10 videosunu göstərir; 30 gün × 8 video ≈ 0,7 GB (pulsuz hədd 10 GB)

const sha256 = b => crypto.createHash("sha256").update(b).digest("hex");
const hmac = (k, s) => crypto.createHmac("sha256", k).update(s).digest();
const enc = s => encodeURIComponent(s).replace(/[!'()*]/g, c => "%" + c.charCodeAt(0).toString(16).toUpperCase());

// Video bitreyti müddətə görə: fayl MAX_BYTES-dan böyük olmasın (59 s → ~310 kb/s, 20 s → 1 Mb/s; yuxarı həddi 1,2 Mb/s).
function bitrate(duration) {
  const d = Number(duration) > 0 ? Number(duration) : 60;
  return Math.max(250, Math.min(1200, Math.floor((MAX_BYTES * 8 / d - AUDIO_BPS - 8000) / 1000)));
}
function ffmpegArgs(input, output, duration) {
  const v = bitrate(duration);
  return ["-hide_banner", "-loglevel", "error", "-y", "-i", input, "-map", "0:v:0", "-map", "0:a:0?",
    "-vf", `scale=${W}:${H}:flags=lanczos,format=yuv420p`, "-c:v", "libx264", "-preset", "slow", "-profile:v", "high", "-level:v", "3.1",
    "-crf", "27", "-maxrate", `${v}k`, "-bufsize", `${2 * v}k`, "-g", "60", "-r", "30",
    "-c:a", "aac", "-b:a", "64k", "-ac", "2", "-ar", "48000", "-movflags", "+faststart", "-metadata", "comment=8ulduz.az", output];
}
// moov qutusu mdat-dan əvvəldirmi (brauzer ilk kadrı faylın başından göstərir, sonu gözləmir).
function faststart(buf) {
  for (let i = 0; i + 8 <= buf.length;) {
    const size = buf.readUInt32BE(i), type = buf.toString("latin1", i + 4, i + 8);
    if (type === "moov") return true;
    if (type === "mdat") return false;
    const n = size === 1 && i + 16 <= buf.length ? Number(buf.readBigUInt64BE(i + 8)) : size;
    if (n < 8) return false;
    i += n;
  }
  return false;
}
function hazirla(input, output, { spawn = require("child_process").spawnSync, log = console.log } = {}) {
  let duration = 0;
  try { duration = JSON.parse(fs.readFileSync(path.join(path.dirname(input), "video.json"), "utf8")).duration; } catch {}
  const r = spawn("ffmpeg", ffmpegArgs(input, output, duration), { encoding: "utf8" });
  if (r.status !== 0) throw new Error(`ffmpeg alınmadı: ${String(r.stderr || r.error?.message || "").slice(0, 300)}`);
  const buf = fs.readFileSync(output);
  if (buf.length > HARD_BYTES || !faststart(buf)) { fs.rmSync(output, { force: true }); throw new Error(`veb nüsxə uyğun deyil (${buf.length} bayt, moov əvvəldə: ${faststart(buf)})`); }
  log(`veb-video: ${W}×${H}, ${(buf.length / 1e6).toFixed(2)} MB, ${bitrate(duration)} kb/s (${Number(duration || 0).toFixed(1)} s)`);
  return { bytes: buf.length, duration };
}

// AWS Signature V4 (R2-nin S3 API-si; bölgə «auto»). Asılılıqsız: iş axınında npm quraşdırılmır.
function sign({ method, url, headers = {}, hash, key, secret, region = "auto", service = "s3", now = Date.now() }) {
  const u = new URL(url), amz = new Date(now).toISOString().replace(/[-:]|\.\d{3}/g, ""), day = amz.slice(0, 8);
  const h = { ...Object.fromEntries(Object.entries(headers).map(([k, v]) => [k.toLowerCase(), String(v).trim().replace(/\s+/g, " ")])),
    host: u.host, "x-amz-content-sha256": hash, "x-amz-date": amz };
  const names = Object.keys(h).sort(), signed = names.join(";");
  const query = [...u.searchParams].map(([k, v]) => `${enc(k)}=${enc(v)}`).sort().join("&");
  const canon = [method, u.pathname, query, names.map(n => `${n}:${h[n]}\n`).join(""), signed, hash].join("\n");
  const scope = `${day}/${region}/${service}/aws4_request`;
  const sts = ["AWS4-HMAC-SHA256", amz, scope, sha256(canon)].join("\n");
  const k = hmac(hmac(hmac(hmac("AWS4" + secret, day), region), service), "aws4_request");
  delete h.host;   // fetch özü qoyur
  return { ...h, authorization: `AWS4-HMAC-SHA256 Credential=${key}/${scope}, SignedHeaders=${signed}, Signature=${hmac(k, sts).toString("hex")}` };
}

// Açarlar (GitHub Secrets): R2_ENDPOINT (https://<hesab>.r2.cloudflarestorage.com), R2_ACCESS_KEY_ID, R2_SECRET_ACCESS_KEY.
// Bucket adı Variables R2_BUCKET (yoxdursa BUCKET). Biri yoxdursa null: iş ötürülür.
function config(env = process.env) {
  const key = env.R2_ACCESS_KEY_ID, secret = env.R2_SECRET_ACCESS_KEY;
  let endpoint = env.R2_ENDPOINT || (env.R2_ACCOUNT_ID ? `https://${env.R2_ACCOUNT_ID}.r2.cloudflarestorage.com` : "");
  if (!key || !secret || !endpoint) return null;
  try { endpoint = new URL(endpoint).origin; } catch { endpoint = ""; }
  if (!/^https:\/\/[\w.-]+\.r2\.cloudflarestorage\.com$/.test(endpoint)) throw new Error("R2_ENDPOINT https://<hesab>.r2.cloudflarestorage.com olmalıdır (docs/veb-video.md)");
  const bucket = env.R2_BUCKET || BUCKET;
  if (!/^[a-z0-9][a-z0-9-]{1,61}[a-z0-9]$/.test(bucket)) throw new Error("R2_BUCKET adı yanlışdır");
  return { key, secret, endpoint, bucket };
}
async function s3(cfg, method, name, { body, type, cache, f = globalThis.fetch, now = Date.now() } = {}) {
  const url = `${cfg.endpoint}/${enc(cfg.bucket)}/${name.split("/").map(enc).join("/")}`;
  const headers = sign({ method, url, headers: { ...(type ? { "content-type": type } : {}), ...(cache ? { "cache-control": cache } : {}) },
    hash: sha256(body || ""), key: cfg.key, secret: cfg.secret, now });
  const r = await f(url, { method, headers, body, redirect: "manual" });
  const text = method === "GET" || !r.ok ? await r.text() : "";
  const code = (/<Code>([^<]+)<\/Code>/.exec(text) || [])[1] || "";
  return { status: r.status, ok: r.ok, text, code };
}
// Oxucunun görəcəyi ünvan: Range ilə 206, video/mp4, yönləndirmə yoxdur (3xx bfcache-i söndürür, AGENTS.md sürət siyahısı 2).
async function publicCheck(url, f = globalThis.fetch) {
  let r;
  try { r = await f(url, { headers: { range: "bytes=0-1023" }, redirect: "manual" }); } catch (e) { return `açıq ünvan soruşulmadı (${e.message})`; }
  const type = String(r.headers.get("content-type") || "");
  if (r.status >= 300 && r.status < 400) return `açıq ünvan yönləndirir (${r.status} → ${r.headers.get("location")})`;
  if (r.status !== 206) return `açıq ünvan ${r.status} verdi (Range üçün 206 gözlənilir; öz domen R2-yə qoşulubmu?)`;
  if (!/^video\/mp4\b/i.test(type)) return `açıq ünvanın növü ${type || "yoxdur"} (video/mp4 gözlənilir)`;
  return "";
}

async function yukle({ file, id, env = process.env, fetch: f = globalThis.fetch, now = Date.now(), log = console.log }) {
  const cfg = config(env);
  if (!cfg) { log("veb-video: R2 açarı yoxdur (R2_ENDPOINT, R2_ACCESS_KEY_ID, R2_SECRET_ACCESS_KEY) — ötürülür, zolaq YouTube oynadıcısı ilə qalır. Qurulum: docs/veb-video.md"); return { skipped: "acar" }; }
  if (!ID.test(String(id || ""))) { log(`veb-video: YouTube nömrəsi yanlışdır (${String(id).slice(0, 40)}) — ötürülür`); return { skipped: "id" }; }
  let buf;
  try { buf = fs.readFileSync(file); } catch { log("veb-video: veb nüsxə yoxdur («Veb nüsxə» addımı alınmayıb) — ötürülür"); return { skipped: "fayl" }; }
  if (buf.length > HARD_BYTES || !faststart(buf)) { log(`veb-video: veb nüsxə uyğun deyil (${buf.length} bayt) — ötürülür`); return { skipped: "olcu" }; }
  const name = `${id}.mp4`, url = BASE + name;
  const put = await s3(cfg, "PUT", name, { body: buf, type: "video/mp4", cache: "public, max-age=31536000, immutable", f, now });
  if (!put.ok) { log(`veb-video: R2-yə yazılmadı (${put.status} ${put.code})`); return { failed: `put ${put.status} ${put.code}` }; }
  const why = await publicCheck(url, f);
  if (why) { log(`veb-video: ${why} — siyahıya yazılmadı, zolaq YouTube oynadıcısı ilə qalır`); return { failed: why }; }
  // Siyahı S3 API ilə oxunur (keşsiz). 404 — ilk dəfə; başqa xəta: yazılmır (köhnə siyahı yarımçıq siyahı ilə əvəzlənməsin).
  const got = await s3(cfg, "GET", "index.json", { f, now });
  let old = [];
  if (got.status === 200) { try { old = JSON.parse(got.text).items || []; } catch { log("veb-video: index.json oxunmadı — yenidən qurulur"); } }
  else if (got.status !== 404) { log(`veb-video: index.json oxunmadı (${got.status} ${got.code}) — siyahı yazılmadı`); return { failed: `index ${got.status}` }; }
  const t = new Date(now).toISOString().slice(0, 19) + "Z";
  const all = [{ v: id, t, b: buf.length }, ...old.filter(x => x && ID.test(String(x.v || "")) && x.v !== id)];
  const fresh = x => now - (Date.parse(x.t) || 0) < KEEP_DAYS * 86400e3;
  const keep = all.filter(fresh).slice(0, KEEP_MAX), drop = all.filter(x => !keep.includes(x));
  const idx = await s3(cfg, "PUT", "index.json", { body: JSON.stringify({ updatedAt: t, items: keep }), type: "application/json", cache: "public, max-age=60", f, now });
  if (!idx.ok) { log(`veb-video: index.json yazılmadı (${idx.status} ${idx.code})`); return { failed: `index put ${idx.status}` }; }
  for (const x of drop) { const d = await s3(cfg, "DELETE", `${x.v}.mp4`, { f, now }); if (!d.ok && d.status !== 404) log(`veb-video: köhnə fayl silinmədi (${x.v}, ${d.status})`); }
  log(`veb-video: yazıldı — ${url} (${(buf.length / 1e6).toFixed(2)} MB); siyahıda ${keep.length} video${drop.length ? `, ${drop.length} köhnə silindi` : ""}`);
  return { url, items: keep.length, removed: drop.length };
}

async function main() {
  const [cmd, a, b] = process.argv.slice(2), lines = [];
  const log = s => { lines.push(s); console.log(s); };
  const summary = () => { if (process.env.GITHUB_STEP_SUMMARY && lines.length) fs.appendFileSync(process.env.GITHUB_STEP_SUMMARY, `### Veb video\n\n${lines.map(l => `- ${l.replace(/^veb-video: /, "")}`).join("\n")}\n`); };
  try {
    if (cmd === "hazirla" && a && b) hazirla(a, b, { log });
    else if (cmd === "yukle" && a) { const r = await yukle({ file: a, id: b, log }); if (r.failed) process.exitCode = 1; }
    else { console.error("istifadə: veb-video.cjs hazirla <video.mp4> <veb.mp4> | yukle <veb.mp4> <YouTube nömrəsi>"); process.exitCode = 2; }
  } catch (e) { log(`veb-video: ${e.message}`); process.exitCode = 1; }
  summary();
}

module.exports = { BASE, BUCKET, ID, W, H, MAX_BYTES, KEEP_DAYS, KEEP_MAX, bitrate, ffmpegArgs, faststart, hazirla, sign, config, s3, publicCheck, yukle };
if (require.main === module) main();
