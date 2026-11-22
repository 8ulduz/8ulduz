// TikTok: öz hazırladığımız video xəbərlər 8ulduz-un TikTok hesabında (sahib, 2026-11-22: «Tik-tok səhifəmizdə videolar verilsin.
// Videolarda başda 8ulduz.az yazılsın.»). Qurulum, TikTok-un qaydaları və audit: docs/tiktok.md.
//
// .github/workflows/tiktok.yml işə salır:
//   node .github/scripts/tiktok.cjs post <qovluq>    qovluqdakı <ad>.mp4 + <ad>.json cütlərindən birini paylaşır (Content Posting API)
//   node .github/scripts/tiktok.cjs qosul            TikTok-un icazədən sonra qaytardığı kodu tokenə çevirir (iş axınının «kod» girişi)
//   node .github/scripts/tiktok.cjs sinaq <qovluq>   ffmpeg ilə 9:16 sınaq videosu (yuxarıda «8ulduz.az»), modul hazır olana qədər
//
// Video faylını bu skript hazırlamır: onu video modulu (ayrı sessiya, «Facebook və Instagram-da video xəbərlər») qurur, yuxarıya
// «8ulduz.az» yazısını o yandırır. Hər video üçün <ad>.json (müqavilə, docs/tiktok.md «Video modulu ilə qoşulma»):
//   { "id": "…", "own": true, "title": "…", "summary": "…", "createdAt": "ISO", "hashtags": ["…"],
//     "source": "…", "sourceUrl": "…", "category": "…", "lang": "az", "items": [{ title, source, sourceUrl, category }], "aigc": false }
// video-xeber.cjs-in öz sahələri də oxunur: text (izah, mətndə xülasənin yerinə), cover_s (üz qabığı), duration (hesabın həddi ilə).
//
// Yalnız öz videolarımız (sahib, 2026-11-22; müəllif hüququ): JSON-da own: true, faylın metadatasında «8ulduz.az» nişanı
// (ffmpeg -metadata comment=8ulduz.az), başqa saytın video ünvanı yoxdur, data/reels.json-dakı X videosu deyil. X-dəki F1, NBA,
// Fox News kimi videolar TikTok-a heç vaxt getmir.
// Qırmızı xətt 2: videonun xəbəri (source/sourceUrl, items) saytın öz qaydasından (app.js policyViolation) keçir.
// Qırmızı xətt 1 və 3-ə toxunmur: xəbər axınından ayrı iş axınıdır, saytın koduna və yüklənməsinə heç nə əlavə etmir.
//
// Açarlar (GitHub Secrets): TIKTOK_CLIENT_KEY, TIKTOK_CLIENT_SECRET; istəyə bağlı TIKTOK_REFRESH_TOKEN. Açar yoxdursa sakitcə ötürülür.
// Token: TikTok sənədində access 24 saat / refresh 365 gün (başqa səhifədə 2 saat / 180 gün) — kod cavabdakı expires_in və
// refresh_expires_in-i işlədir. Yeniləmə cavabı göndərilənin YERİNƏ yeni refresh token qaytarır: köhnəsinə güvənmək olmaz. Ona görə
// token zənciri .tiktok/state.json-da (actions/cache) AES-256-GCM ilə şifrəli saxlanır: açar TIKTOK_CLIENT_SECRET-dən alınır, fork
// PR-ları sirri görmədiyi üçün oxuya bilmir. Keş itsə sirrdəki TIKTOK_REFRESH_TOKEN-ə, o da köhnəlibsə «yenidən qoşulun».
// Açar və token heç vaxt jurnala yazılmır (hide; Actions-da ::add-mask::).
"use strict";
const fs = require("fs"), path = require("path"), crypto = require("crypto");

const API = "https://open.tiktokapis.com/v2/";
const AUTH_URL = "https://www.tiktok.com/v2/auth/authorize/";
// Qeydiyyatdakı Redirect URI ilə hərfbəhərf eyni olmalıdır. Skriptsiz statik səhifə: kod ünvan sətrində qalır, statistikaya getmir.
const REDIRECT = "https://8ulduz.az/haqqinda/";
const SCOPES = { direct: "user.info.basic,video.publish", inbox: "user.info.basic,video.upload" };
// Media transfer guide: 5–64 MB hissə (sonuncu ≤128 MB), 64 MB-a qədər fayl bir hissədə; hissə sayı = floor(ölçü / hissə).
const MB = 1e6, SINGLE_MAX = 64 * MB, CHUNK = 10 * MB, MAX_SIZE = 4e9;
const TITLE_MAX = 2200;            // post_info.title: 2200 UTF-16 simvol
const KEEP_S = 30 * 86400;         // paylaşılanların siyahısı 30 gün
const PAUSE_H = 6;                 // TikTok spam həddi (spam_risk_too_many_posts): bu qədər saat yazılmır
const MARK = Buffer.from("8ulduz.az");
// Başqasının videosu: bu ünvanlardan gələn fayl və ya keçid TikTok-a getmir.
const FOREIGN_VIDEO = /(^|\.)(twimg\.com|twitter\.com|x\.com|youtube\.com|youtu\.be|tiktok\.com|tiktokcdn\.com|instagram\.com|cdninstagram\.com|facebook\.com|fbcdn\.net|fb\.watch|vk\.com|ok\.ru|rutube\.ru|dailymotion\.com|vimeo\.com)$/i;
const RETRY = new Set(["upload_failed", "internal", "video_pull_failed"]);
const PENDING = new Set(["init", "uploaded", "PROCESSING_UPLOAD", "PROCESSING_DOWNLOAD"]);
const TRANSIENT = /^(http_5\d\d|http_429|server_error|temporarily_unavailable|rate_limit_exceeded|internal_error)$/;

const num = (v, d) => (Number.isFinite(Number(v)) && String(v ?? "").trim() !== "" ? Number(v) : d);
const clean = s => String(s ?? "").replace(/<[^>]+>/g, " ").replace(/\s+/g, " ").trim();
const cut = (s, n) => { s = clean(s); return s.length <= n ? s : s.slice(0, n - 1).replace(/\s+\S*$/, "") + "…"; };
const sleep = ms => new Promise(ok => setTimeout(ok, ms));
const hostOf = u => { try { return new URL(String(u)).hostname; } catch { return ""; } };
const sha = b => crypto.createHash("sha256").update(b).digest("hex").slice(0, 16);
const titleKey = t => "t:" + sha(clean(t).toLocaleLowerCase("az").replace(/[^\p{L}\p{N}]+/gu, ""));

function options(env = process.env) {
  const mode = env.TIKTOK_MODE === "inbox" ? "inbox" : "direct";
  return {
    mode,
    // Audit keçənə qədər TikTok yalnız SELF_ONLY qəbul edir: hesabın seçimlərində (creator_info) yoxdursa SELF_ONLY seçilir.
    privacy: env.TIKTOK_PRIVACY || "PUBLIC_TO_EVERYONE",
    // TikTok: hesaba gündə ~15 API postu (bütün tətbiqlər birlikdə); qaralama (inbox) 24 saatda ən çox 5.
    maxDay: Math.min(num(env.TIKTOK_MAX_DAY, mode === "inbox" ? 5 : 10), mode === "inbox" ? 5 : 15),
    minGapMin: num(env.TIKTOK_MIN_GAP_MIN, 60),
    maxAgeH: num(env.TIKTOK_MAX_AGE_H, 12),
    brandOrganic: env.TIKTOK_BRAND_ORGANIC === "1",
    redirect: env.TIKTOK_REDIRECT_URI || REDIRECT,
    pollMs: num(env.TIKTOK_POLL_MS, 6000),   // status: 30 sorğu/dəq
    polls: num(env.TIKTOK_POLLS, 20),
  };
}

// Sahibin brauzerdə açacağı icazə ünvanı (docs/tiktok.md «Qoşulma»). client_key gizli deyil: TikTok onu ünvanda özü göstərir.
function authUrl(env = process.env, mode = options(env).mode) {
  const q = new URLSearchParams({ client_key: env.TIKTOK_CLIENT_KEY || "<CLIENT_KEY>", scope: SCOPES[mode], response_type: "code",
    redirect_uri: options(env).redirect, state: "8ulduz" });
  return `${AUTH_URL}?${q}`;
}
// TikTok-un qaytardığı ünvan (…?code=…&scopes=…&state=…) və ya kodun özü.
function codeFrom(s) {
  s = String(s ?? "").trim();
  const m = s.match(/[?&]code=([^&#\s]+)/);
  const c = m ? m[1] : (/^[\w*!.~%-]{8,}$/.test(s) ? s : "");
  try { return decodeURIComponent(c); } catch { return c; }
}

// Hissələr: [başlanğıc, son) bayt aralıqları.
function chunks(size) {
  if (size <= SINGLE_MAX) return { chunk_size: size, total_chunk_count: 1, parts: [[0, size]] };
  const n = Math.floor(size / CHUNK), parts = [];
  for (let i = 0; i < n; i++) parts.push([i * CHUNK, i === n - 1 ? size : (i + 1) * CHUNK]);
  return { chunk_size: CHUNK, total_chunk_count: n, parts };
}

// Şifrəli token zənciri (actions/cache ictimai repoda PR işlərinə də açıqdır: açıq saxlanmır).
const keyOf = secret => Buffer.from(crypto.hkdfSync("sha256", String(secret), "8ulduz-tiktok", "state-v1", 32));
function seal(obj, secret) {
  const iv = crypto.randomBytes(12), c = crypto.createCipheriv("aes-256-gcm", keyOf(secret), iv);
  const body = Buffer.concat([c.update(JSON.stringify(obj), "utf8"), c.final()]);
  return Buffer.concat([iv, c.getAuthTag(), body]).toString("base64");
}
function unseal(s, secret) {
  try {
    const b = Buffer.from(String(s), "base64"), d = crypto.createDecipheriv("aes-256-gcm", keyOf(secret), b.subarray(0, 12));
    d.setAuthTag(b.subarray(12, 28));
    return JSON.parse(Buffer.concat([d.update(b.subarray(28)), d.final()]).toString("utf8"));
  } catch { return null; }
}
const seedOf = t => (t ? sha(`seed:${t}`) : "");

function authFrom(j, now, prev = {}) {
  const sec = Math.floor(now / 1000);
  return { access: j.access_token, accessUntil: sec + num(j.expires_in, 7200),
    refresh: j.refresh_token || prev.refresh, refreshUntil: j.refresh_expires_in ? sec + num(j.refresh_expires_in, 0) : prev.refreshUntil || sec + 180 * 86400,
    openId: j.open_id || prev.openId || "", scope: j.scope || prev.scope || "", seed: prev.seed || "" };
}
async function tokenCall(f, env, params) {
  const r = await f(`${API}oauth/token/`, { method: "POST", headers: { "content-type": "application/x-www-form-urlencoded", "cache-control": "no-cache" },
    body: new URLSearchParams({ client_key: env.TIKTOK_CLIENT_KEY, client_secret: env.TIKTOK_CLIENT_SECRET, ...params }).toString(), signal: AbortSignal.timeout(20000) });
  const j = await r.json().catch(() => ({}));
  if (!j?.access_token) throw Object.assign(new Error(`token alınmadı: ${j?.error || `HTTP ${r.status}`}${j?.error_description ? ` — ${j.error_description}` : ""}`), { code: j?.error || `http_${r.status}` });
  return j;
}

// Keşdəki zəncir → (vaxtı çatıbsa) yeniləmə → sirrdəki TIKTOK_REFRESH_TOKEN. null: hələ qoşulmayıb.
async function access(f, env, state, now, ctx, force = false) {
  const secret = env.TIKTOK_CLIENT_SECRET, seed = env.TIKTOK_REFRESH_TOKEN || "", sec = Math.floor(now / 1000);
  let auth = state.auth ? unseal(state.auth, secret) : null;
  if (state.auth && !auth) ctx.log("tiktok: keşdəki token oxunmadı (TIKTOK_CLIENT_SECRET dəyişib?) — sirrdəki tokenlə yoxlanır");
  // Sahib sirrə yeni refresh token yazıbsa (yenidən qoşulub), köhnə zəncir yox, o işlənir.
  if (auth && seed && auth.seed !== seedOf(seed)) { ctx.log("tiktok: TIKTOK_REFRESH_TOKEN sirri yenilənib — ondan istifadə olunur"); auth = null; }
  if (auth?.access && !force && auth.accessUntil - sec > 600) { ctx.mask(auth.access); return auth; }
  const tries = [auth?.refresh, seed].filter((x, i, a) => x && a.indexOf(x) === i);
  if (!tries.length) return null;
  let err, transient = false;
  for (const rt of tries) {
    ctx.mask(rt);
    try {
      const j = await tokenCall(f, env, { grant_type: "refresh_token", refresh_token: rt });
      const next = authFrom(j, now, { ...(rt === auth?.refresh ? auth : {}), refresh: rt, seed: seedOf(seed) || (rt === auth?.refresh ? auth.seed : "") });
      ctx.mask(next.access); ctx.mask(next.refresh);
      state.auth = seal(next, secret);
      return next;
    } catch (e) { err = e; transient ||= !e.code || TRANSIENT.test(e.code); }
  }
  // Şəbəkə və ya TikTok-un müvəqqəti xətası: zəncir silinmir, növbəti dövrə yenə yoxlayır.
  if (transient) throw Object.assign(new Error(`${err.message} — müvəqqəti xəta, növbəti dövrədə yenə yoxlanır`), { code: err.code || "network" });
  delete state.auth;
  throw Object.assign(new Error(`${err.message}. TikTok yenidən qoşulmalıdır: docs/tiktok.md «Qoşulma»`), { code: err.code, auth: true });
}

async function api(f, token, p, body) {
  const init = { method: "POST", headers: { authorization: `Bearer ${token}`, "content-type": "application/json; charset=UTF-8" }, signal: AbortSignal.timeout(30000) };
  if (body !== undefined) init.body = JSON.stringify(body);
  // Şəbəkə xətası atılmır, kod kimi qayıdır: yenilənmiş token (state.auth) hər halda saxlanmalıdır.
  const r = await f(`${API}${p}`, init).catch(e => ({ ok: false, status: 0, text: async () => "", err: e }));
  if (r.err) return { status: 0, code: "network", message: clean(r.err?.cause?.code || r.err?.message).slice(0, 80), data: {}, raw: "" };
  const raw = await r.text().catch(() => "");
  let j = {};
  try { j = JSON.parse(raw) || {}; } catch {}
  const code = j?.error?.code || (r.ok ? "ok" : `http_${r.status}`);
  return { status: r.status, code, message: clean(j?.error?.message).slice(0, 200), data: j?.data || {}, raw };
}

// Videonun mətni (post_info.title). TikTok-da keçid basılmır: sayt profilin «bio» hissəsindədir.
function caption(meta) {
  const own = (Array.isArray(meta.hashtags) ? meta.hashtags : []).map(t => "#" + String(t).replace(/^#+/, "").replace(/[^\p{L}\p{N}_]/gu, "")).filter(t => t.length > 1);
  const tags = [...new Set([...own, "#8ulduz", "#xəbərlər", "#Azərbaycan"])].slice(0, 8).join(" ");
  // video-xeber.cjs-in «text» sahəsi ekranda və səsdə gedən izahdır: varsa o, yoxsa xəbərin xülasəsi.
  const desc = clean(meta.text) || clean(meta.summary);
  const title = cut(meta.title, 300), sum = desc && desc !== clean(meta.title) ? cut(desc, 1200) : "";
  return `${title}${sum ? `\n\n${sum}` : ""}\n\nƏtraflı: 8ulduz.az (keçid profildədir)\n\n${tags}`.slice(0, TITLE_MAX);
}

// Yalnız öz videolarımız: boş sətir = olar, mətn = niyə olmaz.
function foreignReason(meta, buf, reels = new Set()) {
  if (meta?.own !== true) return "own: true yoxdur — yalnız öz hazırladığımız videolar gedir";
  const urls = [meta.video, meta.videoUrl, meta.src, ...(Array.isArray(meta.clips) ? meta.clips : [])].filter(Boolean).map(String);
  if (urls.some(u => FOREIGN_VIDEO.test(hostOf(u)) || !/^https:\/\/(www\.)?8ulduz\.az\//.test(u))) return "başqa saytın videosudur";
  if ([meta.sourceUrl, ...(meta.items || []).map(x => x?.sourceUrl)].some(u => FOREIGN_VIDEO.test(hostOf(u)))) return "xəbər video/sosial şəbəkədəndir";
  if (reels.has(String(meta.id)) || urls.some(u => reels.has(u))) return "X videosudur (data/reels.json)";
  if (buf.length < 12 || buf.subarray(4, 8).toString("latin1") !== "ftyp") return "mp4 deyil";
  const head = buf.subarray(0, 2 * MB), tail = buf.subarray(Math.max(0, buf.length - 2 * MB));
  if (!head.includes(MARK) && !tail.includes(MARK)) return "faylda «8ulduz.az» nişanı yoxdur (ffmpeg -metadata comment=8ulduz.az)";
  return "";
}
// Qırmızı xətt 2: videonun aid olduğu hər xəbər saytın qaydasından keçir. Xəbəri olmayan (öz) video, məs. sınaq, qaydaya düşmür.
function policyReason(meta, policy) {
  const stories = [...(meta.source || meta.sourceUrl ? [meta] : []), ...(Array.isArray(meta.items) ? meta.items : [])];
  for (const s of stories) {
    const a = { title: s.title ?? meta.title, summary: s.summary ?? (s === meta ? [meta.summary, meta.text].filter(Boolean).join(" ") : ""), source: s.source, sourceUrl: s.sourceUrl, category: s.category ?? meta.category, lang: s.lang ?? meta.lang };
    if (policy(a)) return `mənbə qaydası (${clean(a.source) || hostOf(a.sourceUrl) || "?"})`;
  }
  return "";
}

function readVideos(dir) {
  let names = [];
  try { names = fs.readdirSync(dir, { recursive: true }).map(String); } catch { return []; }
  return names.filter(n => n.endsWith(".json")).map(n => {
    const file = path.join(dir, n.slice(0, -5) + ".mp4");
    let meta = null;
    try { meta = JSON.parse(fs.readFileSync(path.join(dir, n), "utf8")); } catch {}
    return meta && typeof meta === "object" && fs.existsSync(file) ? { meta, file } : null;
  }).filter(Boolean);
}

function prune(state, now) {
  const sec = Math.floor(now / 1000);
  state.posted = Object.fromEntries(Object.entries(state.posted || {}).filter(([, v]) => v && sec - (v.t || 0) < KEEP_S));
}
const live = (state, sec) => Object.entries(state.posted || {}).filter(([k, v]) => !/^[th]:/.test(k) && sec - v.t < 86400 && !String(v.s).startsWith("FAILED") && v.s !== "upload_failed");

// Status sorğusu: son vəziyyəti state-ə yazır, jurnala bir sətir.
async function checkStatus(f, token, key, entry, opt, ctx, wait) {
  let st = "", d = {}, raw = "";
  for (let i = 0; i < (wait ? opt.polls : 1); i++) {
    if (i) await sleep(opt.pollMs);
    const r = await api(f, token, "post/publish/status/fetch/", { publish_id: entry.p });
    if (r.code !== "ok") { ctx.log(`tiktok: status alınmadı (${r.code}${r.message ? `: ${r.message}` : ""}) — ${entry.n}`); return entry.s; }
    d = r.data; st = d.status || ""; raw = r.raw;
    if (st && !PENDING.has(st)) break;
  }
  const reason = d.fail_reason || "";
  entry.s = st === "FAILED" ? `FAILED:${reason || "?"}` : st || entry.s;
  // Post nömrəsi int64-dür (19 rəqəm): JSON.parse onu yuvarlaqlaşdırır, ona görə xam cavabdan oxunur. Sahə adı TikTok-da belədir (sic).
  const id = (String(raw).match(/"publicaly_available_post_id"\s*:\s*\[\s*"?(\d+)/) || [])[1];
  if (id) entry.id = id;
  if (st === "PUBLISH_COMPLETE") ctx.log(`tiktok: paylaşıldı — ${entry.n}${entry.id ? ` (ictimai: https://www.tiktok.com/@${ctx.user || "8ulduz.az"}/video/${entry.id})` : entry.v === "SELF_ONLY" ? " (yalnız hesab sahibinə görünür: SELF_ONLY)" : entry.v === "inbox" ? " (tətbiqdə dərc olundu)" : " (moderasiyadan sonra ictimai olacaq)"}`);
  else if (st === "SEND_TO_USER_INBOX") ctx.log(`tiktok: qaralama göndərildi — TikTok tətbiqində bildirişə toxunub dərc edin: ${entry.n}`);
  else if (st === "FAILED") ctx.log(`tiktok: TikTok qəbul etmədi (${reason}) — ${entry.n}`);
  else ctx.log(`tiktok: hələ emal olunur (${st || "?"}), növbəti dövrədə yoxlanır — ${entry.n}`);
  return entry.s;
}

// Bir dövrə: əvvəl gözləyənlərin statusu, sonra ən təzə, hələ getməmiş bir video.
async function run({ videos = [], env = process.env, now = Date.now(), fetch: f = globalThis.fetch, state = {}, log = console.log, policy = () => false, reels = new Set(), mask = () => {} }) {
  const opt = options(env), sec = Math.floor(now / 1000), res = { posted: [], failed: [], skipped: [] };
  const secrets = new Set([env.TIKTOK_CLIENT_SECRET, env.TIKTOK_CLIENT_KEY, env.TIKTOK_REFRESH_TOKEN].filter(x => x && x.length > 6));
  const hide = s => [...secrets].reduce((m, k) => m.split(k).join("***"), String(s?.message || s));
  const ctx = { log: s => log(hide(s)), mask: t => { if (t && t.length > 6) { secrets.add(t); mask(t); } } };
  if (env.TIKTOK === "0") { ctx.log("tiktok: söndürülüb (Variables TIKTOK=0)"); return res; }
  if (!env.TIKTOK_CLIENT_KEY || !env.TIKTOK_CLIENT_SECRET) { ctx.log("tiktok: açar yoxdur (TIKTOK_CLIENT_KEY, TIKTOK_CLIENT_SECRET) — ötürülür. Qurulum: docs/tiktok.md"); return res; }
  prune(state, now);
  const posted = state.posted;

  // Namizədlər (şəbəkəsiz yoxlama).
  const list = [];
  for (const v of videos) {
    const m = v.meta, id = clean(m.id).slice(0, 80), name = cut(m.title || id, 120);
    if (!id || !clean(m.title)) { res.skipped.push([id, "id/başlıq yoxdur"]); continue; }
    const at = Date.parse(m.createdAt || m.publishedAt || "") || now;
    const prev = posted[id];
    if (prev && !(RETRY.has(String(prev.s).replace(/^FAILED:/, "")) && (prev.a || 1) < 2)) continue;   // eyni video iki dəfə getmir
    if (!m.sinaq && (now - at > opt.maxAgeH * 3600e3)) { res.skipped.push([id, "köhnədir"]); ctx.log(`tiktok: ötürülür (${opt.maxAgeH} saatdan köhnədir) — ${name}`); continue; }
    let buf;
    try { buf = fs.readFileSync(v.file); } catch { res.skipped.push([id, "fayl oxunmadı"]); continue; }
    const why = foreignReason(m, buf, reels) || policyReason(m, policy) || (buf.length > MAX_SIZE ? "4 GB-dan böyükdür" : "");
    if (why) { res.skipped.push([id, why]); ctx.log(`tiktok: ötürülür (${why}) — ${name}`); continue; }
    const h = "h:" + sha(buf), t = titleKey(m.title);
    if (!prev && (posted[h] || (!m.sinaq && posted[t]))) { ctx.log(`tiktok: bu video (və ya bu başlıq) artıq paylaşılıb — ${name}`); continue; }
    list.push({ id, m, buf, at, h, t, name });
  }
  list.sort((x, y) => (y.m.sinaq ? 1 : 0) - (x.m.sinaq ? 1 : 0) || y.at - x.at);
  const waiting = Object.entries(posted).filter(([k, v]) => !/^[th]:/.test(k) && PENDING.has(v.s) && v.p && sec - v.t < 86400).slice(0, 3);
  if (!list.length && !waiting.length) { ctx.log(`tiktok: paylaşılacaq yeni video yoxdur${videos.length ? ` (${videos.length} fayl baxıldı)` : ""}`); return res; }

  let auth;
  try { auth = await access(f, env, state, now, ctx); }
  catch (e) { ctx.log(`tiktok: ${e.message}`); res.failed.push(["token", e.code || "?"]); return res; }
  if (!auth) { ctx.log(`tiktok: hesab hələ qoşulmayıb — docs/tiktok.md «Qoşulma» (iş axını «TikTok-da paylaş», «kod» girişi). Ötürülür.`); return res; }
  if (auth.refreshUntil - sec < 14 * 86400) ctx.log(`tiktok: DİQQƏT — token ${Math.max(0, Math.floor((auth.refreshUntil - sec) / 86400))} gün sonra bitir, yenidən qoşulun (docs/tiktok.md «Qoşulma»)`);

  for (const [key, entry] of waiting) await checkStatus(f, auth.access, key, entry, opt, ctx, false);

  if (!list.length) return res;
  const pause = state.pause || 0;
  // Əl ilə sınaq (sinaq) fasiləni gözləmir: hesabı gizli edəndən sonra dərhal yoxlamaq olur; adi videolar gözləyir.
  if (pause > sec && !list[0].m.sinaq) { ctx.log(`tiktok: TikTok həddinə görə fasilə, ${Math.ceil((pause - sec) / 60)} dəq qalıb`); return res; }
  const day = live(state, sec), lastAgo = Math.round((sec - (state.last || 0)) / 60), v = list[0];
  if (day.length >= opt.maxDay) { ctx.log(`tiktok: 24 saatda ${day.length} video getdi (hədd ${opt.maxDay}) — növbəti sonra`); return res; }
  if (!v.m.sinaq && lastAgo < opt.minGapMin) { ctx.log(`tiktok: son video ${lastAgo} dəq əvvəl, növbəti ${opt.minGapMin - lastAgo} dəq sonra`); return res; }
  if (opt.mode === "direct" && !String(auth.scope).includes("video.publish")) { ctx.log("tiktok: tokendə video.publish icazəsi yoxdur — yenidən qoşulun (docs/tiktok.md)"); res.failed.push([v.id, "scope"]); return res; }
  if (opt.mode === "inbox" && !String(auth.scope).includes("video.upload")) { ctx.log("tiktok: tokendə video.upload icazəsi yoxdur — yenidən qoşulun (docs/tiktok.md)"); res.failed.push([v.id, "scope"]); return res; }

  // TikTok-un cavab kodları (Direct Post / Upload reference).
  const stop = r => {
    const why = `${r.code}${r.message ? `: ${r.message}` : ""}`;
    if (r.code === "spam_risk_too_many_posts") { state.pause = sec + PAUSE_H * 3600; ctx.log(`tiktok: hesabın gündəlik API həddi dolub — ${PAUSE_H} saat fasilə`); }
    else if (r.code === "reached_active_user_cap") { state.pause = sec + 24 * 3600; ctx.log("tiktok: tətbiqin gündəlik istifadəçi həddi dolub — 24 saat fasilə"); }
    else if (r.code === "unaudited_client_can_only_post_to_private_accounts") { state.pause = sec + 12 * 3600; ctx.log("tiktok: tətbiq hələ auditdən keçməyib — TikTok yalnız GİZLİ hesaba və yalnız SELF_ONLY qəbul edir. Hesabı gizli edin və ya auditi gözləyin (docs/tiktok.md). 12 saat fasilə"); }
    else if (r.code === "spam_risk_user_banned_from_posting") { state.pause = sec + 24 * 3600; ctx.log("tiktok: TikTok bu hesaba API ilə paylaşmağı bağlayıb — 24 saat fasilə, hesabı tətbiqdə yoxlayın"); }
    ctx.log(`tiktok: alınmadı (${why}) — ${v.name}`);
    res.failed.push([v.id, r.code]);
  };

  let creator = {}, privacy = "";
  if (opt.mode === "direct") {
    let ci = await api(f, auth.access, "post/publish/creator_info/query/");
    if (ci.code === "access_token_invalid") {
      try { auth = await access(f, env, state, now, ctx, true); } catch (e) { ctx.log(`tiktok: ${e.message}`); res.failed.push(["token", e.code || "?"]); return res; }
      ci = await api(f, auth.access, "post/publish/creator_info/query/");
    }
    if (ci.code !== "ok") { stop(ci); return res; }
    creator = ci.data;
    ctx.user = clean(creator.creator_username);
    const opts = Array.isArray(creator.privacy_level_options) ? creator.privacy_level_options : [];
    const want = v.m.sinaq ? "SELF_ONLY" : opt.privacy;
    privacy = opts.includes(want) ? want : opts.includes("SELF_ONLY") ? "SELF_ONLY" : opts[0] || "SELF_ONLY";
    if (privacy !== want) ctx.log(`tiktok: ${want} bu hesabda seçilə bilmir (${opts.join(", ") || "siyahı boş"}) — ${privacy} ilə göndərilir`);
    const max = num(creator.max_video_post_duration_sec, 0);
    if (max) ctx.log(`tiktok: hesab — ${clean(creator.creator_nickname)} (@${ctx.user}), video ən çox ${max} s, görünmə: ${privacy}`);
    const dur = num(v.m.duration, 0);
    if (max && dur > max) {
      posted[v.id] = { t: sec, s: "FAILED:duration", n: v.name, a: 2 };
      ctx.log(`tiktok: ötürülür (video ${Math.round(dur)} s, hesabın həddi ${max} s) — ${v.name}`);
      res.skipped.push([v.id, "uzundur"]);
      return res;
    }
  }

  const plan = chunks(v.buf.length);
  const source_info = { source: "FILE_UPLOAD", video_size: v.buf.length, chunk_size: plan.chunk_size, total_chunk_count: plan.total_chunk_count };
  const body = opt.mode === "inbox" ? { source_info } : {
    post_info: { title: caption(v.m), privacy_level: privacy, disable_comment: !!creator.comment_disabled, disable_duet: !!creator.duet_disabled,
      disable_stitch: !!creator.stitch_disabled, video_cover_timestamp_ms: Math.max(0, Math.floor(num(v.m.coverMs, num(v.m.cover_s, 1) * 1000))),
      brand_content_toggle: false, brand_organic_toggle: opt.brandOrganic, is_aigc: v.m.aigc === true },
    source_info };
  const init = await api(f, auth.access, opt.mode === "inbox" ? "post/publish/inbox/video/init/" : "post/publish/video/init/", body);
  if (init.code !== "ok" || !init.data.publish_id || !init.data.upload_url) { stop(init.code === "ok" ? { ...init, code: "cavab_natamam" } : init); return res; }
  const entry = posted[v.id] = { t: sec, s: "init", p: String(init.data.publish_id), n: v.name, v: privacy || "inbox", a: (posted[v.id]?.a || 0) + 1 };
  posted[v.h] = posted[v.t] = { t: sec };
  state.last = sec;
  try {
    for (const [a, b] of plan.parts) {
      const r = await f(init.data.upload_url, { method: "PUT", headers: { "content-type": "video/mp4", "content-range": `bytes ${a}-${b - 1}/${v.buf.length}` },
        body: v.buf.subarray(a, b), signal: AbortSignal.timeout(180000) });
      if (![200, 201, 206].includes(r.status)) throw new Error(`HTTP ${r.status}`);
    }
  } catch (e) {
    entry.s = "upload_failed";
    // Fayl TikTok-a tam çatmadı: post yaranmayıb, eyni video növbəti dəfə (bir dəfə) yenə göndərilə bilər.
    delete posted[v.h]; delete posted[v.t];
    ctx.log(`tiktok: fayl yüklənmədi (${hide(e)}) — ${v.name}`);
    res.failed.push([v.id, "upload"]);
    return res;
  }
  entry.s = "uploaded";
  const st = await checkStatus(f, auth.access, v.id, entry, opt, ctx, true);
  if (String(st).startsWith("FAILED")) {
    const reason = String(st).slice(7);
    if (/^spam_risk_too_many_posts$/.test(reason)) state.pause = sec + PAUSE_H * 3600;
    if (RETRY.has(reason) && entry.a < 2) { delete posted[v.h]; delete posted[v.t]; }
    res.failed.push([v.id, reason]);
  } else res.posted.push([opt.mode, v.id, st]);
  return res;
}

// «qosul»: TikTok icazə səhifəsindən sonra açılan ünvandakı kod → token zənciri (şifrəli keşə). Kod bir dəfəlikdir və bir neçə
// dəqiqə işləyir; client_secret olmadan onunla heç nə etmək olmur.
async function connect({ code, env = process.env, now = Date.now(), fetch: f = globalThis.fetch, state = {}, log = console.log, mask = () => {} }) {
  const opt = options(env), c = codeFrom(code);
  const secrets = new Set([env.TIKTOK_CLIENT_SECRET, env.TIKTOK_CLIENT_KEY, env.TIKTOK_REFRESH_TOKEN, c].filter(x => x && x.length > 6));
  const hide = s => [...secrets].reduce((m, k) => m.split(k).join("***"), String(s?.message || s));
  const add = t => { if (t && t.length > 6) { secrets.add(t); mask(t); } };
  add(c);
  if (!env.TIKTOK_CLIENT_KEY || !env.TIKTOK_CLIENT_SECRET) throw new Error("açar yoxdur: əvvəl TIKTOK_CLIENT_KEY və TIKTOK_CLIENT_SECRET sirlərini yazın (docs/tiktok.md)");
  if (!c) throw new Error("kod tapılmadı: TikTok-un açdığı ünvanı (…/haqqinda/?code=…) tam yapışdırın");
  let j;
  try { j = await tokenCall(f, env, { grant_type: "authorization_code", code: c, redirect_uri: opt.redirect }); }
  catch (e) { throw new Error(`${hide(e)} (kod bir dəfəlikdir və tez köhnəlir: icazə ünvanını yenidən açıb təzə kod alın; Redirect URI ${opt.redirect} olmalıdır)`); }
  add(j.access_token); add(j.refresh_token);
  const auth = authFrom(j, now, { seed: seedOf(env.TIKTOK_REFRESH_TOKEN || "") });
  state.auth = seal(auth, env.TIKTOK_CLIENT_SECRET);
  let who = "";
  if (String(auth.scope).includes("video.publish")) {
    const ci = await api(f, auth.access, "post/publish/creator_info/query/").catch(() => ({ data: {} }));
    if (ci.data?.creator_username) who = `${clean(ci.data.creator_nickname)} (@${clean(ci.data.creator_username)}), görünmə seçimləri: ${(ci.data.privacy_level_options || []).join(", ")}`;
  }
  const days = Math.floor((auth.refreshUntil - Math.floor(now / 1000)) / 86400);
  log(hide(`tiktok: qoşuldu${who ? ` — ${who}` : ""}; icazələr: ${auth.scope || "?"}; token ${days} gün işləyir (yeniləmə avtomatikdir)`));
  if (!/video\.(publish|upload)/.test(auth.scope)) log("tiktok: DİQQƏT — video icazəsi verilməyib (video.publish və ya video.upload): tətbiqdə scope əlavə edib yenidən qoşulun");
  return auth;
}

// Sınaq videosu (video modulu main-ə düşənə qədər): 1080×1920, 30 kadr/s, H.264 + AAC, 6 s, yuxarıda «8ulduz.az».
function makeTestVideo(dir, now = Date.now(), spawn = require("child_process").spawnSync) {
  fs.mkdirSync(dir, { recursive: true });
  const fc = spawn("fc-match", ["-f", "%{file}", "DejaVu Sans:bold"], { encoding: "utf8" });
  const font = (fc.status === 0 && String(fc.stdout || "").trim()) || "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf";
  const name = `sinaq-${Math.floor(now / 1000)}`, file = path.join(dir, `${name}.mp4`), txt = path.join(dir, `${name}.txt`);
  const when = new Date(now + 4 * 3600e3).toISOString().slice(0, 16).replace("T", " ");
  fs.writeFileSync(txt, `Sınaq videosu\n${when} (Bakı)`);
  const q = p => `'${String(p).replace(/\\/g, "/").replace(/'/g, "")}'`;
  const vf = [`drawtext=fontfile=${q(font)}:text='8ulduz.az':fontcolor=white:fontsize=110:x=(w-text_w)/2:y=170`,
    `drawtext=fontfile=${q(font)}:textfile=${q(txt)}:fontcolor=white:fontsize=64:line_spacing=28:x=(w-text_w)/2:y=(h-text_h)/2`].join(",");
  const r = spawn("ffmpeg", ["-hide_banner", "-loglevel", "error", "-y",
    "-f", "lavfi", "-i", "color=c=0x0b1f3a:s=1080x1920:r=30:d=6", "-f", "lavfi", "-i", "anullsrc=r=44100:cl=stereo",
    "-vf", vf, "-t", "6", "-shortest", "-c:v", "libx264", "-pix_fmt", "yuv420p", "-r", "30", "-c:a", "aac", "-b:a", "128k",
    "-movflags", "+faststart", "-metadata", "comment=8ulduz.az", "-metadata", "title=8ulduz.az sınaq", file], { encoding: "utf8" });
  try { fs.unlinkSync(txt); } catch {}
  if (r.status !== 0) throw new Error(`ffmpeg alınmadı: ${String(r.stderr || r.error?.message || "").slice(0, 300)}`);
  fs.writeFileSync(path.join(dir, `${name}.json`), JSON.stringify({ id: name, own: true, sinaq: true, title: "8ulduz.az — sınaq videosu",
    summary: "Yükləyicinin sınağı: bu video yalnız hesab sahibinə görünür.", createdAt: new Date(now).toISOString(), hashtags: [] }));
  return file;
}

function readState(file) {
  try { const s = JSON.parse(fs.readFileSync(file, "utf8")); return s && typeof s === "object" ? s : {}; } catch { return {}; }
}

async function main() {
  const [cmd, arg] = process.argv.slice(2);
  const stateFile = process.env.TIKTOK_STATE || ".tiktok/state.json";
  const now = Date.now(), lines = [];
  const log = s => { lines.push(s); console.log(s); };
  // Actions jurnalı alınmış tokenləri də gizlətsin (sirlər onsuz da gizlədilir).
  const mask = t => { if (process.env.GITHUB_ACTIONS === "true") process.stdout.write(`::add-mask::${t}\n`); };
  const save = state => { fs.mkdirSync(path.dirname(stateFile), { recursive: true }); fs.writeFileSync(stateFile, JSON.stringify(state)); };
  const summary = () => { if (process.env.GITHUB_STEP_SUMMARY && lines.length) fs.appendFileSync(process.env.GITHUB_STEP_SUMMARY, `### TikTok\n\n${lines.map(l => `- ${l.replace(/^tiktok: /, "")}`).join("\n")}\n`); };
  if (cmd === "sinaq") { log(`tiktok: sınaq videosu — ${makeTestVideo(arg || "tiktok-in", now)}`); return; }
  if (cmd === "link") { console.log(authUrl()); return; }
  const state = readState(stateFile);
  if (cmd === "qosul") {
    let code = arg || process.env.TIKTOK_CODE || "";
    // İş axınının «kod» girişi env-ə qoyulmur (addımın env siyahısı jurnalda görünür): hadisə faylından oxunur.
    if (!code && process.env.GITHUB_EVENT_PATH) try { code = JSON.parse(fs.readFileSync(process.env.GITHUB_EVENT_PATH, "utf8"))?.inputs?.kod || ""; } catch {}
    try { await connect({ code, now, state, log, mask }); save(state); }
    catch (e) { log(`tiktok: qoşulma alınmadı — ${e.message}`); process.exitCode = 1; }
    summary();
    return;
  }
  if (cmd !== "post") { console.error("istifadə: tiktok.cjs post <qovluq> | qosul [kod] | sinaq <qovluq> | link"); process.exitCode = 2; return; }
  // Qırmızı xətt 2: qayda faylı oxunmasa heç nə paylaşılmır (xəta ilə dayanır).
  const { loadApp } = require("./topics.cjs");
  const app = loadApp(path.resolve("."));
  let reels = new Set();
  try { const r = JSON.parse(fs.readFileSync("data/reels.json", "utf8")); reels = new Set((r.items || []).flatMap(x => [String(x.id), String(x.u || "")]).filter(Boolean)); } catch {}
  let res;
  // Gözlənilməz xətada da state (yenilənmiş token zənciri) saxlanır: köhnə refresh token artıq işləməyə bilər.
  try { res = await run({ videos: readVideos(arg || "tiktok-in"), now, state, log, mask, reels, policy: a => app.policyViolation(a) }); }
  finally { save(state); summary(); }
  // Heç nə alınmayıbsa iş qırmızı olsun (sahib görsün); ötürmə və fasilə yaşıl.
  if (res.failed.length && !res.posted.length) process.exitCode = 1;
}

module.exports = { options, authUrl, codeFrom, chunks, seal, unseal, access, caption, foreignReason, policyReason, readVideos, run, connect, makeTestVideo, SCOPES, REDIRECT };
if (require.main === module) main().catch(e => { console.error(String(e?.message || e).slice(0, 300)); process.exitCode = 1; });
