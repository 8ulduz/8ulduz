// YouTube Shorts: 8ulduz-un öz hazırladığı video xəbərlər YouTube kanalında (2026-11-22). Məqsəd: videolar Google axtarışının video
// nəticələrinə düşsün. Saytın Videolenti Google-da indekslənmir: #/videolent?r= ünvanı ayrıca səhifə sayılmır, başqasının X videosundan
// qurulan səhifələr də spam qaydasına düşür. Qurulum, açarlar və qaydalar: docs/youtube.md.
//
// .github/workflows/youtube.yml işə salır:
//   node .github/scripts/youtube.cjs post <qovluq>    qovluqdakı <ad>.mp4 + <ad>.json cütlərindən birini yükləyir (Data API v3 videos.insert)
//   node .github/scripts/youtube.cjs yoxla           açarları yoxlayır: token alınır, kanalın adı jurnala yazılır (heç nə yüklənmir)
//   node .github/scripts/youtube.cjs sinaq <qovluq>   ffmpeg ilə 9:16 sınaq videosu (yuxarıda «8ulduz.az»): qurulumu yoxlamaq üçün
//
// Video faylını bu skript hazırlamır: onu video modulu (.github/scripts/video-xeber.cjs, sosial-video.yml) qurur, yuxarıya
// «8ulduz.az» yazısını o yandırır. Müqavilə TikTok yükləyicisi ilə eynidir (docs/youtube.md «Video modulu ilə qoşulma»):
//   <ad>.mp4  — şaquli (hündürlük ≥ en), ≤ YOUTUBE_MAX_S (60) saniyə, metadatasında «8ulduz.az» nişanı (ffmpeg -metadata comment=8ulduz.az)
//   <ad>.json — { "id", "own": true, "title", "summary"?, "kind"? (xeber | icmal | hava | valyuta | bazar | maraqli), "url"?, "publishedAt"?,
//                 "createdAt"?, "hashtags"?, "source"?, "sourceUrl"?, "category"?, "lang"?, "items"?: [{ title, source, sourceUrl }], "aigc"?, "text"? }
// Qoşulma: sosial-video.yml «youtube» işi «video-xeber» artefaktını verir (video.mp4 + video.json, video-xeber.cjs, ≤ 59 s).
//
// Yalnız öz videolarımız (müəllif hüququ): own: true, faylda «8ulduz.az» nişanı, başqa saytın video ünvanı yoxdur, data/reels.json-dakı
// X videosu deyil. X-dəki F1, NBA, Fox News, klub videoları YouTube-a heç vaxt getmir: 1 dəqiqədən uzun Shorts-a müəllif hüququ
// iddiası gələrsə video bütün dünyada bloklanır, kanal da risk altına düşür. Ona görə video 60 saniyədən uzun olmur.
// Qırmızı xətt 2: videonun xəbəri (source/sourceUrl, items) saytın öz qaydasından (app.js policyViolation) keçir.
// Qırmızı xətt 1 və 3-ə toxunmur: xəbər axınından ayrı iş axınıdır, saytın koduna və yüklənməsinə heç nə əlavə etmir.
//
// Açarlar (GitHub Secrets): YOUTUBE_CLIENT_ID, YOUTUBE_CLIENT_SECRET, YOUTUBE_REFRESH_TOKEN. Biri yoxdursa iş sakitcə ötürülür.
// Google-un refresh tokeni dəyişmir (TikTok-dakı kimi zəncir yoxdur): hər dövrə ondan qısa ömürlü access token alır.
// Kvota (2026-06-01-dən): videos.insert-in öz qutusu var, gündə 100 yükləmə, Sakit okean vaxtı ilə gecə yarısı yenilənir.
// Paylaşılanlar .youtube/state.json-dadır (actions/cache, 30 gün; içində açar yoxdur). Token youtube.readonly icazəsi də verirsə, yükləmədən
// əvvəl kanalın son 50 videosu da yoxlanır: keş itsə də eyni video iki dəfə getmir. Açar və token heç vaxt jurnala yazılmır.
"use strict";
const fs = require("fs"), path = require("path"), crypto = require("crypto");

const TOKEN_URL = "https://oauth2.googleapis.com/token";
const API = "https://www.googleapis.com/youtube/v3/";
const UPLOAD = "https://www.googleapis.com/upload/youtube/v3/videos";
const HOME = "https://8ulduz.az/";
const KEYS = ["YOUTUBE_CLIENT_ID", "YOUTUBE_CLIENT_SECRET", "YOUTUBE_REFRESH_TOKEN"];
// YouTube resursunun hədləri (developers.google.com/youtube/v3/docs/videos): başlıq 100 simvol, təsvir 5000 bayt, teqlər cəmi 500
// simvol (vergüllər sayılır, boşluqlu teq dırnaqlı sayılır); başlıqda və təsvirdə < və > olmaz.
const TITLE_MAX = 100, DESC_MAX = 5000, TAGS_MAX = 500, TAG_MAX = 30;
const KEEP_S = 30 * 86400;
const MARK = Buffer.from("8ulduz.az");
// Adın bütün yazılışları (sahib, 2026-11-24: «8ulduz» axtaranda kanal çıxır, «8 ulduz» axtaranda çıxmır; «səkkiz ulduz, səkkizulduz,
// xəbər yazanda da çıxsın»). YouTube «8 ulduz»-u iki söz kimi oxuyur, bitişik «8ULDUZ» adına uyğun gəlmir: təsvirdə və teqlərdə
// rəqəmlə, sözlə, bitişik və ayrı yazılış var (profil: youtube.tagline, youtube.etiketler). Tək «8», «səkkiz», «xəbər» kimi ümumi
// sözlərdə yer baxış sayından asılıdır.
// Dil profili (2026-11-26, video-dil.cjs): təsvirin, teqlərin, abunə sətrinin və kanalın dili videonun dilidir — video.json «lang»
// (profili yoxdursa az: başqa iş axınlarının videoları). Mətnlər .github/video-dil/<dil>.json «youtube» və «abune» bölmələrindədir.
// Abunə çağırışı (sahib, 2026-11-25: «baxanlar abunə olsunlar»): vəd videodakı ilə eynidir (eyni profil). Keçid kanalı abunə
// pəncərəsi ilə açır (Shorts təsvirində keçid basılmır; adi baxış səhifəsində basılır). VED, CHANNEL — az profilininki.
const { dil, videonunDili, fmt } = require("./video-dil.cjs");
const VED = Object.fromEntries(Object.entries(dil("az").abune).map(([k, v]) => [k, v.ved]));
const CHANNEL = dil("az").youtube.kanal;
// Başqasının videosu: bu ünvanlardan gələn fayl və ya keçid YouTube-a getmir.
const FOREIGN_VIDEO = /(^|\.)(twimg\.com|twitter\.com|x\.com|youtube\.com|youtu\.be|tiktok\.com|tiktokcdn\.com|instagram\.com|cdninstagram\.com|facebook\.com|fbcdn\.net|fb\.watch|vk\.com|ok\.ru|rutube\.ru|dailymotion\.com|vimeo\.com)$/i;
const SITE_URL = /^https:\/\/(www\.)?8ulduz\.az(\/[^\s<>"]*)?$/;
const KINDS = new Set(["xeber", "icmal", "hava", "valyuta", "bazar", "sinaq", "maraqli"]);
const RETRY_HTTP = new Set([500, 502, 503, 504]);
const READ_SCOPE = /(^|\s)https:\/\/www\.googleapis\.com\/auth\/youtube(\.readonly|\.force-ssl)?(\s|$)/;
const UPLOAD_SCOPE = /(^|\s)https:\/\/www\.googleapis\.com\/auth\/(youtube|youtube\.upload|youtube\.force-ssl|youtubepartner)(\s|$)/;


const num = (v, d) => (Number.isFinite(Number(v)) && String(v ?? "").trim() !== "" ? Number(v) : d);
const clean = s => String(s ?? "").replace(/<[^>]+>/g, " ").replace(/\s+/g, " ").trim();
const cut = (s, n) => { s = clean(s); return s.length <= n ? s : s.slice(0, n - 1).replace(/\s+\S*$/, "") + "…"; };
const noAngle = s => String(s ?? "").replace(/</g, "‹").replace(/>/g, "›");
const sleep = ms => new Promise(ok => setTimeout(ok, ms));
const hostOf = u => { try { return new URL(String(u)).hostname; } catch { return ""; } };
const sha = b => crypto.createHash("sha256").update(b).digest("hex").slice(0, 16);
const titleKey = t => "t:" + sha(clean(t).toLocaleLowerCase("az").replace(/[^\p{L}\p{N}]+/gu, ""));
function hourOf(iso) { const m = String(iso || "").match(/^20(\d\d)-(\d\d)-(\d\d)T(\d\d)/); return m ? m.slice(1).join("") : ""; }
function cutBytes(s, n) {
  s = String(s);
  if (Buffer.byteLength(s) <= n) return s;
  let lo = 0, hi = s.length;
  while (lo < hi) { const mid = (lo + hi + 1) >> 1; if (Buffer.byteLength(s.slice(0, mid)) <= n - 3) lo = mid; else hi = mid - 1; }
  return s.slice(0, lo).replace(/\s+\S*$/, "") + "…";
}

function options(env = process.env) {
  const privacy = ["public", "unlisted", "private"].includes(env.YOUTUBE_PRIVACY) ? env.YOUTUBE_PRIVACY : "public";
  return {
    privacy,
    // Yükləmə kvotası gündə 100-dür. Standart 30 (sahib, 2026-11-24: video sayı 10 qat; əvvəl 8 — kanal yeni idi), video dövrəsi ilə
    // eyni sayda; ara 20 dəqiqə (video 30 dəqiqədən bir gəlir, iş bir neçə dəqiqə gec başlaya bilər). Kanalın öz həddi dolanda
    // yükləyici 24 saat fasilə verir (aşağıda uploadLimitExceeded).
    maxDay: Math.max(0, Math.min(num(env.YOUTUBE_MAX_DAY, 30), 50)),
    minGapMin: num(env.YOUTUBE_MIN_GAP_MIN, 20),
    maxAgeH: num(env.YOUTUBE_MAX_AGE_H, 12),
    // Shorts 3 dəqiqəyə qədər ola bilər, amma 1 dəqiqədən uzun Shorts müəllif hüququ iddiasında bütün dünyada bloklanır: 60-dan çox olmur.
    maxS: Math.max(1, Math.min(num(env.YOUTUBE_MAX_S, 60), 60)),
    category: /^\d{1,3}$/.test(env.YOUTUBE_CATEGORY || "") ? env.YOUTUBE_CATEGORY : "25",   // 25 = News & Politics
    notify: env.YOUTUBE_NOTIFY !== "0",
    retryMs: num(env.YOUTUBE_RETRY_MS, 3000),
  };
}

// MP4 qutuları: müddət (moov/mvhd) və video izinin ölçüsü (trak/tkhd, mdia/hdlr = vide). ffprobe lazım deyil.
function boxes(buf, start, end, cb) {
  let i = start;
  while (i + 8 <= end) {
    let size = buf.readUInt32BE(i), hdr = 8;
    const type = buf.toString("latin1", i + 4, i + 8);
    if (size === 1) { if (i + 16 > end) return; size = Number(buf.readBigUInt64BE(i + 8)); hdr = 16; }
    else if (size === 0) size = end - i;
    if (size < hdr || i + size > end) return;
    cb(type, i + hdr, i + size);
    i += size;
  }
}
function mp4Info(buf) {
  const out = { duration: 0, width: 0, height: 0 };
  if (!Buffer.isBuffer(buf) || buf.length < 16) return out;
  try {
    boxes(buf, 0, buf.length, (t, a, b) => {
      if (t !== "moov") return;
      boxes(buf, a, b, (t2, a2, b2) => {
        if (t2 === "mvhd" && b2 - a2 >= 32) {
          const v1 = buf[a2] === 1, ts = buf.readUInt32BE(a2 + (v1 ? 20 : 12)), d = v1 ? Number(buf.readBigUInt64BE(a2 + 24)) : buf.readUInt32BE(a2 + 16);
          if (ts) out.duration = Math.round(d / ts * 1000) / 1000;
        }
        if (t2 !== "trak") return;
        let w = 0, h = 0, turned = false, vide = false;
        boxes(buf, a2, b2, (t3, a3, b3) => {
          if (t3 === "tkhd" && b3 - a3 >= 84) {
            const v1 = buf[a3] === 1, m = a3 + (v1 ? 52 : 40), at = a3 + (v1 ? 88 : 76);
            if (at + 8 <= b3) { w = buf.readUInt32BE(at) / 65536; h = buf.readUInt32BE(at + 4) / 65536; }
            turned = buf.readInt32BE(m) === 0 && buf.readInt32BE(m + 4) !== 0;   // 90° fırladılıb: en və hündürlük yer dəyişir
          }
          if (t3 === "mdia") boxes(buf, a3, b3, (t4, a4) => { if (t4 === "hdlr" && buf.toString("latin1", a4 + 8, a4 + 12) === "vide") vide = true; });
        });
        if (vide && w && h && !out.width) { out.width = Math.round(turned ? h : w); out.height = Math.round(turned ? w : h); }
      });
    });
  } catch {}
  return out;
}

// Shorts şərti: şaquli və ya kvadrat, ən çox maxS saniyə. Boş sətir = olar.
function shortsReason(info, opt) {
  if (!info.width || !info.height) return "videonun ölçüsü oxunmadı (mp4 deyil və ya moov yoxdur)";
  if (info.width > info.height) return `şaquli deyil (${info.width}×${info.height}) — Shorts 9:16 və ya kvadrat olur`;
  if (!(info.duration > 0)) return "videonun müddəti oxunmadı";
  if (info.duration > opt.maxS) return `${info.duration.toFixed(1)} s — ${opt.maxS} saniyədən uzundur (1 dəqiqədən uzun Shorts müəllif hüququ iddiasında bloklanır)`;
  return "";
}

// Yalnız öz videolarımız: boş sətir = olar, mətn = niyə olmaz.
function foreignReason(meta, buf, reels = new Set()) {
  if (meta?.own !== true) return "own: true yoxdur — yalnız öz hazırladığımız videolar gedir";
  const urls = [meta.video, meta.videoUrl, meta.src, ...(Array.isArray(meta.clips) ? meta.clips : [])].filter(Boolean).map(String);
  if (urls.some(u => FOREIGN_VIDEO.test(hostOf(u)) || !/^https:\/\/(www\.)?8ulduz\.az\//.test(u))) return "başqa saytın videosudur";
  if ([meta.sourceUrl, ...(Array.isArray(meta.items) ? meta.items : []).map(x => x?.sourceUrl)].some(u => FOREIGN_VIDEO.test(hostOf(u)))) return "xəbər video/sosial şəbəkədəndir";
  if (reels.has(String(meta.id)) || urls.some(u => reels.has(u))) return "X videosudur (data/reels.json)";
  if (!Buffer.isBuffer(buf) || buf.length < 12 || buf.subarray(4, 8).toString("latin1") !== "ftyp") return "mp4 deyil";
  const head = buf.subarray(0, 2e6), tail = buf.subarray(Math.max(0, buf.length - 2e6));
  if (!head.includes(MARK) && !tail.includes(MARK)) return "faylda «8ulduz.az» nişanı yoxdur (ffmpeg -metadata comment=8ulduz.az)";
  return "";
}
// Qırmızı xətt 2: videonun aid olduğu hər xəbər saytın qaydasından keçir. Xəbəri olmayan öz video (hava, valyuta, sınaq) qaydaya düşmür.
function policyReason(meta, policy) {
  const stories = [...(meta.source || meta.sourceUrl ? [meta] : []), ...(Array.isArray(meta.items) ? meta.items : [])];
  for (const s of stories) {
    const a = { title: s?.title ?? meta.title, summary: s?.summary ?? (s === meta ? meta.summary : ""), source: s?.source, sourceUrl: s?.sourceUrl,
      category: s?.category ?? meta.category, lang: s?.lang ?? meta.lang };
    if (policy(a)) return `mənbə qaydası (${clean(a.source) || hostOf(a.sourceUrl) || "?"})`;
  }
  return "";
}

const kindOf = m => (KINDS.has(m?.kind) ? m.kind : m?.sinaq ? "sinaq" : /^icmal-/.test(String(m?.id || "")) ? "icmal" : "xeber");
// Təsvirdəki keçid: saytın səhifəsi. Xəbər → paylaşma səhifəsi (https://www.8ulduz.az/<nömrə>?h=<saat>, social.cjs ilə eyni),
// icmal → icmal səhifəsi, qalanı → video modulunun verdiyi url və ya ana səhifə. Başqa saytın keçidi təsvirə düşmür.
function linkOf(m) {
  for (const u of [m.url, m.link]) if (SITE_URL.test(String(u || ""))) return String(u);
  const id = clean(m.id), ic = /^icmal-(\d{4}-\d\d-\d\d-(?:seher|axsam))$/.exec(id);
  if (ic) return `${HOME}icmal/${ic[1]}/`;
  if (kindOf(m) === "xeber" && /^[0-9a-f]{16}$/.test(id)) { const h = hourOf(m.publishedAt); return `https://www.8ulduz.az/${id}${h ? `?h=${h}` : ""}`; }
  return HOME;
}
const titleOf = m => cut(noAngle(clean(m.title)), TITLE_MAX);
function hashtagsOf(m) {
  const own = (Array.isArray(m.hashtags) ? m.hashtags : []).map(t => "#" + String(t).replace(/^#+/, "").replace(/[^\p{L}\p{N}_]/gu, "")).filter(t => t.length > 1).slice(0, 3);
  return [...new Set([...own, ...videonunDili(m).youtube.hashtaglar])].join(" ");
}
const abuneLine = m => { const D = videonunDili(m); return fmt(D.youtube.abune, { ved: (D.abune[kindOf(m)] || D.abune.xeber).ved, kanal: D.youtube.kanal }); };
function descriptionOf(m, link = linkOf(m)) {
  // Xülasə; yoxdursa videodakı izahın (text) əvvəli.
  const D = videonunDili(m), Yt = D.youtube;
  const k = kindOf(m), title = clean(m.title), pick = [m.summary, m.text].map(clean).find(x => x && x !== title) || "";
  const sum = pick ? cut(pick, pick === clean(m.summary) ? 1500 : 600) : "";
  const items = (Array.isArray(m.items) ? m.items : []).filter(x => clean(x?.title)).slice(0, 10);
  const list = k === "icmal" && items.length ? items.map((x, i) => `${i + 1}. ${cut(x.title, 140)}`).join("\n") : "";
  const src = k === "icmal" ? [] : [...new Set([m.source, ...items.map(x => x.source)].map(clean).filter(Boolean))].slice(0, 5);
  const tail = [fmt(Yt.etrafli, { link }), abuneLine(m), src.length ? fmt(Yt.menbe, { adlar: src.join(", ") }) : "", Yt.tagline, hashtagsOf(m)].filter(Boolean).join("\n\n");
  const body = [sum, list].filter(Boolean).join("\n\n");
  const room = DESC_MAX - Buffer.byteLength(noAngle(tail)) - 2;
  return noAngle([body ? cutBytes(body, room) : "", tail].filter(Boolean).join("\n\n"));
}
// Teqlər: YouTube-un sayma qaydası ilə cəmi ≤ 500 (vergül 1, boşluqlu teq +2 dırnaq).
function tagsOf(m) {
  const Yt = videonunDili(m).youtube;
  const raw = [...Yt.etiketler, ...(Yt.nov_etiketleri[kindOf(m)] || []), Yt.bolme_etiketleri[m.category],
    ...(Array.isArray(m.hashtags) ? m.hashtags : []).map(t => String(t).replace(/^#+/, "").replace(/_/g, " "))];
  const out = [], seen = new Set();
  let total = 0;
  for (let t of raw) {
    t = clean(String(t ?? "").replace(/[<>,"]/g, " ")).slice(0, TAG_MAX).trim();
    const key = t.toLocaleLowerCase("az");
    if (!t || seen.has(key)) continue;
    const cost = t.length + (/\s/.test(t) ? 2 : 0) + (out.length ? 1 : 0);
    if (total + cost > TAGS_MAX) continue;
    seen.add(key); out.push(t); total += cost;
  }
  return out;
}
function resourceOf(m, opt) {
  return {
    snippet: { title: titleOf(m), description: descriptionOf(m), tags: tagsOf(m), categoryId: opt.category, defaultLanguage: /^[a-z]{2}$/.test(m.lang || "") ? m.lang : videonunDili(m).kod },
    // Səs SARA modelidir, amma real adamı və ya hadisəni təqlid etmir: «realistic altered or synthetic» sayılmır, aigc: true verilərsə bildirilir.
    status: { privacyStatus: m.sinaq ? "private" : opt.privacy, selfDeclaredMadeForKids: false, embeddable: true, license: "youtube", publicStatsViewable: true,
      containsSyntheticMedia: m.aigc === true },
  };
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
// Kanalda tapılan təkrar (d: 1) yükləmə deyil, gündəlik həddə sayılmır. Gündəlik hava videosu da sayılmır (sahib, 2026-11-23: o,
// xəbər videosunun 8-lik həddinə düşmür): yoxsa 8 xəbər + hava 9 edir və axşamın son xəbəri YouTube-a getmir (2026-11-23, 21:48).
// Növ (k) yükləmə qeydindədir; köhnə qeydlərdə yoxdur, onlarda hava videosu adından tanınır («hava-<gün>»).
const isHava = (k, v) => (v.k ? v.k === "hava" : /^hava-/.test(k));
const uploadsSince = (state, sec) => Object.entries(state.posted || {}).filter(([k, v]) => !/^[th]:/.test(k) && v.v && !v.d && !isHava(k, v) && sec - v.t < 86400).length;

// Kvota Sakit okean vaxtı ilə gecə yarısı yenilənir (Bakı vaxtı ilə 11:00–12:00): fasilə ondan 1 dəqiqə sonrayadək.
function quotaReset(now) {
  const p = new Intl.DateTimeFormat("en-US", { timeZone: "America/Los_Angeles", hourCycle: "h23", hour: "2-digit", minute: "2-digit", second: "2-digit" }).formatToParts(new Date(now));
  const g = t => Number(p.find(x => x.type === t)?.value || 0);
  return now - (g("hour") * 3600 + g("minute") * 60 + g("second")) * 1000 + 86400e3 + 60e3;
}

const reasonOf = (j, status) => j?.error?.errors?.[0]?.reason || j?.error?.details?.find?.(d => d?.reason)?.reason || j?.error?.status || `http_${status}`;
async function token(f, env) {
  const r = await f(TOKEN_URL, { method: "POST", headers: { "content-type": "application/x-www-form-urlencoded" },
    body: new URLSearchParams({ client_id: env.YOUTUBE_CLIENT_ID, client_secret: env.YOUTUBE_CLIENT_SECRET, refresh_token: env.YOUTUBE_REFRESH_TOKEN, grant_type: "refresh_token" }).toString(),
    signal: AbortSignal.timeout(20000) }).catch(e => ({ err: e }));
  if (r.err) throw Object.assign(new Error(`token alınmadı: şəbəkə xətası (${clean(r.err?.cause?.code || r.err?.message).slice(0, 60)}) — növbəti dövrədə yenə yoxlanır`), { code: "network" });
  const j = await r.json().catch(() => ({}));
  if (j?.access_token) return { access: String(j.access_token), scope: String(j.scope || "") };
  const code = String(j?.error || `http_${r.status}`);
  const why = code === "invalid_grant" ? "refresh token etibarsızdır: layihə «Testing» rejimindədirsə token 7 gündə köhnəlir, icazə götürülübsə və ya token 6 ay işlənməyibsə də. Yenisini alın: docs/youtube.md «Token köhnələndə»"
    : /^(invalid_client|unauthorized_client)$/.test(code) ? "YOUTUBE_CLIENT_ID və ya YOUTUBE_CLIENT_SECRET yanlışdır, ya da token başqa klientlə alınıb (docs/youtube.md)"
    : "Google cavab vermədi — növbəti dövrədə yenə yoxlanır";
  throw Object.assign(new Error(`token alınmadı (${code}): ${why}`), { code });
}
async function get(f, access, p, q) {
  const r = await f(`${API}${p}?${new URLSearchParams(q)}`, { headers: { authorization: `Bearer ${access}` }, signal: AbortSignal.timeout(20000) }).catch(e => ({ err: e }));
  if (r.err) return { ok: false, reason: "network", data: {} };
  const j = await r.json().catch(() => ({}));
  return { ok: r.status === 200, reason: r.status === 200 ? "ok" : reasonOf(j, r.status), message: clean(j?.error?.message).slice(0, 200), data: j || {} };
}
// Kanal və son 50 yükləmə (2 vahid ümumi kvotadan, yükləmə kvotasına dəymir).
async function channel(f, access, items = true) {
  const c = await get(f, access, "channels", { part: "snippet,contentDetails,statistics", mine: "true" });
  if (!c.ok) return { error: c.reason };
  const ch = c.data.items?.[0];
  if (!ch) return { error: "youtubeSignupRequired" };
  const out = { id: ch.id, title: clean(ch.snippet?.title), videos: num(ch.statistics?.videoCount, 0), uploads: ch.contentDetails?.relatedPlaylists?.uploads, items: [] };
  if (!items || !out.uploads) return out;
  const p = await get(f, access, "playlistItems", { part: "snippet", playlistId: out.uploads, maxResults: "50" });
  if (!p.ok) return { ...out, error: p.reason };
  out.items = (p.data.items || []).map(x => ({ id: x.snippet?.resourceId?.videoId || "", title: String(x.snippet?.title || ""), description: String(x.snippet?.description || "") }));
  return out;
}

// Resumable upload (developers.google.com/youtube/v3/guides/using_resumable_upload_protocol): sessiya → fayl → kəsilsə qalan hissə.
async function startUpload(f, access, resource, size, opt) {
  const q = new URLSearchParams({ uploadType: "resumable", part: "snippet,status", notifySubscribers: opt.notify ? "true" : "false" });
  for (let i = 0; i < 2; i++) {
    if (i) await sleep(opt.retryMs);
    const r = await f(`${UPLOAD}?${q}`, { method: "POST", headers: { authorization: `Bearer ${access}`, "content-type": "application/json; charset=UTF-8",
      "x-upload-content-length": String(size), "x-upload-content-type": "video/mp4" }, body: JSON.stringify(resource), signal: AbortSignal.timeout(30000) }).catch(e => ({ err: e }));
    if (r.err) { if (i) return { reason: "network", message: clean(r.err?.cause?.code || r.err?.message).slice(0, 80) }; continue; }
    const session = r.status === 200 ? r.headers?.get?.("location") : "";
    if (session) return { session };
    const j = await r.json().catch(() => ({}));
    if (RETRY_HTTP.has(r.status) && !i) continue;
    return { reason: r.status === 200 ? "sessiya_yoxdur" : reasonOf(j, r.status), message: clean(j?.error?.message).slice(0, 200), status: r.status };
  }
  return { reason: "network" };
}
async function sendFile(f, session, buf, opt) {
  const size = buf.length;
  let from = 0, last = "";
  for (let i = 0; i < 4; i++) {
    if (i) await sleep(opt.retryMs * 2 ** (i - 1));
    const headers = { "content-type": "video/mp4" };
    if (from) headers["content-range"] = `bytes ${from}-${size - 1}/${size}`;
    const r = await f(session, { method: "PUT", headers, body: buf.subarray(from), redirect: "manual", signal: AbortSignal.timeout(300000) }).catch(e => ({ err: e }));
    if (!r.err && (r.status === 200 || r.status === 201)) return { ok: true, video: await r.json().catch(() => ({})) };
    if (!r.err && r.status !== 308 && !RETRY_HTTP.has(r.status)) {
      const j = await r.json().catch(() => ({}));
      return { ok: false, reason: r.status === 404 ? "sessiya_köhnəlib" : reasonOf(j, r.status), message: clean(j?.error?.message).slice(0, 200) };
    }
    last = r.err ? `şəbəkə: ${clean(r.err?.cause?.code || r.err?.message).slice(0, 60)}` : `HTTP ${r.status}`;
    // Nə qədəri çatıb? Boş PUT + «bytes */ölçü»: 308 + Range → qalanı göndərilir; 200/201 → artıq tamamdır.
    const s = await f(session, { method: "PUT", headers: { "content-range": `bytes */${size}` }, body: "", redirect: "manual", signal: AbortSignal.timeout(30000) }).catch(e => ({ err: e }));
    if (s.err) continue;
    if (s.status === 200 || s.status === 201) return { ok: true, video: await s.json().catch(() => ({})) };
    if (s.status === 308) { const m = /bytes=0-(\d+)/.exec(s.headers?.get?.("range") || ""); from = m ? Math.min(Number(m[1]) + 1, size) : 0; continue; }
    if (s.status === 404) return { ok: false, reason: "sessiya_köhnəlib", message: "" };
  }
  return { ok: false, reason: "upload", message: last };
}

// Bir dövrə: ən təzə (icmal və sınaq öndə), hələ getməmiş bir video.
async function run({ videos = [], env = process.env, now = Date.now(), fetch: f = globalThis.fetch, state = {}, log = console.log, policy = () => false, reels = new Set(), mask = () => {} }) {
  const opt = options(env), sec = Math.floor(now / 1000), res = { posted: [], failed: [], skipped: [] };
  const secrets = new Set(KEYS.map(k => env[k]).filter(x => x && x.length > 6));
  const hide = s => [...secrets].reduce((m, k) => m.split(k).join("***"), String(s?.message || s));
  const ctx = { log: s => log(hide(s)), mask: t => { if (t && t.length > 6) { secrets.add(t); mask(t); } } };
  if (env.YOUTUBE === "0") { ctx.log("youtube: söndürülüb (Variables YOUTUBE=0)"); return res; }
  const missing = KEYS.filter(k => !env[k]);
  if (missing.length) { ctx.log(`youtube: açar yoxdur (${missing.join(", ")}) — ötürülür. Qurulum: docs/youtube.md`); return res; }
  prune(state, now);
  const posted = state.posted;

  // Namizədlər (şəbəkəsiz yoxlama).
  const list = [];
  for (const v of videos) {
    const m = v.meta, id = clean(m.id).slice(0, 80), name = cut(m.title || id, 120);
    if (!id || !clean(m.title)) { res.skipped.push([id, "id/başlıq yoxdur"]); continue; }
    if (posted[id]) continue;   // eyni video iki dəfə getmir
    const at = Date.parse(m.createdAt || m.publishedAt || "") || now;
    if (!m.sinaq && now - at > opt.maxAgeH * 3600e3) { res.skipped.push([id, "köhnədir"]); ctx.log(`youtube: ötürülür (${opt.maxAgeH} saatdan köhnədir) — ${name}`); continue; }
    let buf;
    try { buf = fs.readFileSync(v.file); } catch { res.skipped.push([id, "fayl oxunmadı"]); continue; }
    const why = foreignReason(m, buf, reels) || policyReason(m, policy) || shortsReason(mp4Info(buf), opt);
    if (why) { res.skipped.push([id, why]); ctx.log(`youtube: ötürülür (${why}) — ${name}`); continue; }
    const h = "h:" + sha(buf), t = titleKey(m.title);
    if (posted[h] || (!m.sinaq && posted[t])) { ctx.log(`youtube: bu video (və ya bu başlıq) artıq yüklənib — ${name}`); continue; }
    list.push({ id, m, buf, at, h, t, name, prio: m.sinaq ? 2 : kindOf(m) === "icmal" ? 1 : 0 });
  }
  if (!list.length) { ctx.log(`youtube: yüklənəcək yeni video yoxdur${videos.length ? ` (${videos.length} fayl baxıldı)` : ""}`); return res; }
  list.sort((x, y) => y.prio - x.prio || y.at - x.at);
  const v = list[0];
  if ((state.pause || 0) > sec) { ctx.log(`youtube: fasilə (${state.why || "YouTube həddi"}), ${Math.ceil((state.pause - sec) / 60)} dəq qalıb`); return res; }
  const day = uploadsSince(state, sec), lastAgo = Math.round((sec - (state.last || 0)) / 60);
  if (day >= opt.maxDay) { ctx.log(`youtube: 24 saatda ${day} video yükləndi (hədd ${opt.maxDay}) — növbəti sonra`); return res; }
  if (!v.prio && lastAgo < opt.minGapMin) { ctx.log(`youtube: son video ${lastAgo} dəq əvvəl, növbəti ${opt.minGapMin - lastAgo} dəq sonra`); return res; }

  let tok;
  try { tok = await token(f, env); ctx.mask(tok.access); }
  catch (e) { ctx.log(`youtube: ${e.message}`); res.failed.push(["token", e.code || "?"]); return res; }
  if (tok.scope && !UPLOAD_SCOPE.test(tok.scope)) { ctx.log("youtube: tokendə youtube.upload icazəsi yoxdur — tokeni yenidən alın (docs/youtube.md «Token»)"); res.failed.push([v.id, "scope"]); return res; }
  const remember = (vid, dup = false) => { posted[v.id] = { t: sec, v: vid || "?", n: v.name, k: kindOf(v.m), ...(dup ? { d: 1 } : {}) }; posted[v.h] = { t: sec }; if (!v.m.sinaq) posted[v.t] = { t: sec }; };

  // Keş itsə də təkrar olmasın: kanalın son 50 videosunda eyni başlıq və ya eyni keçid varsa yüklənmir.
  if (READ_SCOPE.test(tok.scope)) {
    const ch = await channel(f, tok.access);
    if (ch.error === "youtubeSignupRequired") { ctx.log("youtube: bu Google hesabının YouTube kanalı yoxdur — əvvəl kanal yaradın (docs/youtube.md «Kanal»)"); res.failed.push([v.id, ch.error]); return res; }
    if (ch.error) ctx.log(`youtube: kanalın son videoları oxunmadı (${ch.error}) — yalnız öz siyahımızla yoxlanır`);
    // Keçid yalnız xəbər və icmalda hər videoya xasdır; hava/valyuta/bazar videosunun keçidi hər gün eyni səhifədir (bolme/hava/) —
    // onlarda tarixli başlıq yoxlanır, yoxsa ikinci günün hava videosu dünənkinin təkrarı sayılardı.
    const link = linkOf(v.m), key = v.t, ownLink = link !== HOME && ["xeber", "icmal"].includes(kindOf(v.m));
    const dup = v.m.sinaq ? null : ch.items.find(x => titleKey(x.title) === key || (ownLink && x.description.includes(link)));
    if (dup) { remember(dup.id, true); ctx.log(`youtube: kanalda artıq var (https://www.youtube.com/shorts/${dup.id}) — ${v.name}`); return res; }
  }

  const resource = resourceOf(v.m, opt);
  const stop = r => {
    const why = `${r.reason}${r.message ? `: ${r.message}` : ""}`;
    if (r.reason === "quotaExceeded") { state.pause = Math.floor(quotaReset(now) / 1000); state.why = "gündəlik yükləmə kvotası"; ctx.log("youtube: gündəlik yükləmə kvotası (100) dolub — Sakit okean vaxtı ilə gecə yarısı (Bakı ~11–12:00) yenilənir"); }
    else if (r.reason === "uploadLimitExceeded") { state.pause = sec + 24 * 3600; state.why = "kanalın yükləmə həddi"; ctx.log("youtube: kanalın yükləmə həddi dolub (YouTube-un öz həddi) — 24 saat fasilə"); }
    else if (r.reason === "youtubeSignupRequired") { state.pause = sec + 6 * 3600; state.why = "kanal yoxdur"; ctx.log("youtube: bu Google hesabının YouTube kanalı yoxdur — docs/youtube.md «Kanal». 6 saat fasilə"); }
    else if (/^(insufficientPermissions|ACCESS_TOKEN_SCOPE_INSUFFICIENT)$/.test(r.reason)) ctx.log("youtube: tokendə youtube.upload icazəsi yoxdur — tokeni yenidən alın (docs/youtube.md «Token»)");
    else if (/^(accessNotConfigured|SERVICE_DISABLED)$/.test(r.reason)) ctx.log("youtube: Google Cloud layihəsində «YouTube Data API v3» yandırılmayıb (docs/youtube.md «Google Cloud»)");
    ctx.log(`youtube: alınmadı (${why}) — ${v.name}`);
    res.failed.push([v.id, r.reason]);
  };
  const init = await startUpload(f, tok.access, resource, v.buf.length, opt);
  if (!init.session) { stop(init); return res; }
  ctx.mask(init.session);   // sessiya ünvanı yükləmə açarıdır
  const sent = await sendFile(f, init.session, v.buf, opt);
  if (!sent.ok) { ctx.log(`youtube: fayl yüklənmədi (${sent.reason}${sent.message ? `: ${sent.message}` : ""}) — ${v.name}`); res.failed.push([v.id, sent.reason]); return res; }
  const vid = clean(sent.video?.id), priv = sent.video?.status?.privacyStatus || resource.status.privacyStatus;
  remember(vid);
  state.last = sec;
  ctx.log(`youtube: yükləndi — https://www.youtube.com/shorts/${vid || "?"} (${priv}) — ${v.name}`);
  if (priv !== resource.status.privacyStatus) ctx.log(`youtube: DİQQƏT — ${resource.status.privacyStatus} istənmişdi, YouTube ${priv} qoydu (kanalın standart ayarı və ya yoxlama). YouTube Studio-da baxın`);
  if (sent.video?.status?.uploadStatus === "rejected") ctx.log(`youtube: DİQQƏT — YouTube videonu rədd etdi (${sent.video.status.rejectionReason || "?"})`);
  res.posted.push([v.id, vid]);
  return res;
}

// «yoxla»: açarlar işləyirmi, hansı kanala yazılır (yükləmə kvotasına dəymir).
async function check({ env = process.env, fetch: f = globalThis.fetch, log = console.log, mask = () => {} }) {
  const secrets = new Set(KEYS.map(k => env[k]).filter(x => x && x.length > 6));
  const hide = s => [...secrets].reduce((m, k) => m.split(k).join("***"), String(s?.message || s));
  const missing = KEYS.filter(k => !env[k]);
  if (missing.length) throw new Error(`açar yoxdur: ${missing.join(", ")} — docs/youtube.md «Açarları GitHub-a yazın»`);
  let tok;
  try { tok = await token(f, env); } catch (e) { throw new Error(hide(e)); }
  secrets.add(tok.access); mask(tok.access);
  const scopes = tok.scope.split(/\s+/).filter(Boolean).map(s => s.replace("https://www.googleapis.com/auth/", "")).join(", ");
  log(hide(`youtube: token alındı; icazələr: ${scopes || "?"}`));
  if (tok.scope && !UPLOAD_SCOPE.test(tok.scope)) throw new Error("tokendə youtube.upload icazəsi yoxdur — tokeni yenidən alın (docs/youtube.md «Token»)");
  if (!READ_SCOPE.test(tok.scope)) { log("youtube: kanal adını görmək və təkrarı kanalda yoxlamaq üçün youtube.readonly icazəsi də verin (istəyə bağlı)"); return {}; }
  const ch = await channel(f, tok.access, false);
  if (ch.error === "youtubeSignupRequired") throw new Error("bu Google hesabının YouTube kanalı yoxdur — docs/youtube.md «Kanal»");
  if (ch.error) throw new Error(`kanal oxunmadı (${ch.error})`);
  log(hide(`youtube: kanal — ${ch.title} (https://www.youtube.com/channel/${ch.id}), ${ch.videos} video. Videolar bu kanala yüklənəcək`));
  return ch;
}

// Sınaq videosu (video modulu qoşulana qədər): 1080×1920, 30 kadr/s, H.264 + AAC, 6 s, yuxarıda «8ulduz.az». Xəbər deyil.
function makeTestVideo(dir, now = Date.now(), spawn = require("child_process").spawnSync) {
  fs.mkdirSync(dir, { recursive: true });
  const fc = spawn("fc-match", ["-f", "%{file}", "DejaVu Sans:bold"], { encoding: "utf8" });
  const font = (fc.status === 0 && String(fc.stdout || "").trim()) || "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf";
  const name = `sinaq-${Math.floor(now / 1000)}`, file = path.join(dir, `${name}.mp4`), txt = path.join(dir, `${name}.txt`);
  const when = new Date(now + 4 * 3600e3).toISOString().slice(0, 16).replace("T", " ");
  fs.writeFileSync(txt, `YouTube sınağı\n${when} (Bakı)`);
  const q = p => `'${String(p).replace(/\\/g, "/").replace(/'/g, "")}'`;
  const vf = [`drawtext=fontfile=${q(font)}:text='8ulduz.az':fontcolor=white:fontsize=110:x=(w-text_w)/2:y=170`,
    `drawtext=fontfile=${q(font)}:textfile=${q(txt)}:fontcolor=white:fontsize=64:line_spacing=28:x=(w-text_w)/2:y=(h-text_h)/2`].join(",");
  const r = spawn("ffmpeg", ["-hide_banner", "-loglevel", "error", "-y",
    "-f", "lavfi", "-i", "color=c=0x0b1f3a:s=1080x1920:r=30:d=6", "-f", "lavfi", "-i", "anullsrc=r=48000:cl=stereo",
    "-vf", vf, "-t", "6", "-shortest", "-c:v", "libx264", "-pix_fmt", "yuv420p", "-r", "30", "-c:a", "aac", "-b:a", "128k",
    "-movflags", "+faststart", "-metadata", "comment=8ulduz.az", "-metadata", "title=8ulduz.az sınaq", file], { encoding: "utf8" });
  try { fs.unlinkSync(txt); } catch {}
  if (r.status !== 0) throw new Error(`ffmpeg alınmadı: ${String(r.stderr || r.error?.message || "").slice(0, 300)}`);
  fs.writeFileSync(path.join(dir, `${name}.json`), JSON.stringify({ id: name, own: true, sinaq: true, kind: "sinaq", title: "8ulduz.az — sınaq videosu",
    summary: "Yükləyicinin sınağı: bu video gizlidir (private), yalnız kanal sahibi görür. YouTube Studio-dan silə bilərsiniz.", createdAt: new Date(now).toISOString(), hashtags: [] }));
  return file;
}

// Bu dövrədə yüklənən videonun YouTube nömrəsi (yoxdursa ""): yalnız düzgün nömrə iş axınının çıxışına yazılır.
const videoIdOf = res => (res?.posted || []).map(p => String(p[1] || "")).find(v => /^[\w-]{6,20}$/.test(v)) || "";

function readState(file) {
  try { const s = JSON.parse(fs.readFileSync(file, "utf8")); return s && typeof s === "object" ? s : {}; } catch { return {}; }
}

async function main() {
  const [cmd, arg] = process.argv.slice(2);
  const stateFile = process.env.YOUTUBE_STATE || ".youtube/state.json";
  const now = Date.now(), lines = [];
  const log = s => { lines.push(s); console.log(s); };
  // Actions jurnalı alınmış tokeni də gizlətsin (sirlər onsuz da gizlədilir).
  const mask = t => { if (process.env.GITHUB_ACTIONS === "true") process.stdout.write(`::add-mask::${t}\n`); };
  const summary = () => { if (process.env.GITHUB_STEP_SUMMARY && lines.length) fs.appendFileSync(process.env.GITHUB_STEP_SUMMARY, `### YouTube\n\n${lines.map(l => `- ${l.replace(/^youtube: /, "")}`).join("\n")}\n`); };
  if (cmd === "sinaq") { log(`youtube: sınaq videosu — ${makeTestVideo(arg || "youtube-in", now)}`); return; }
  if (cmd === "yoxla") {
    try { await check({ log, mask }); } catch (e) { log(`youtube: yoxlama alınmadı — ${e.message}`); process.exitCode = 1; }
    summary();
    return;
  }
  if (cmd !== "post") { console.error("istifadə: youtube.cjs post <qovluq> | yoxla | sinaq <qovluq>"); process.exitCode = 2; return; }
  // Qırmızı xətt 2: qayda faylı oxunmasa heç nə yüklənmir (xəta ilə dayanır).
  const { loadApp } = require("./topics.cjs");
  const app = loadApp(path.resolve("."));
  let reels = new Set();
  try { const r = JSON.parse(fs.readFileSync("data/reels.json", "utf8")); reels = new Set((r.items || []).flatMap(x => [String(x.id), String(x.u || "")]).filter(Boolean)); } catch {}
  const state = readState(stateFile);
  let res;
  try { res = await run({ videos: readVideos(arg || "youtube-in"), now, state, log, mask, reels, policy: a => app.policyViolation(a) }); }
  finally { fs.mkdirSync(path.dirname(stateFile), { recursive: true }); fs.writeFileSync(stateFile, JSON.stringify(state)); summary(); }
  // Yüklənən videonun nömrəsi: sosial-video.yml «veb-video» işi saytın veb nüsxəsini bu adla yazır (veb-video.cjs).
  const vid = videoIdOf(res);
  if (vid && process.env.GITHUB_OUTPUT) fs.appendFileSync(process.env.GITHUB_OUTPUT, `video_id=${vid}\n`);
  // Heç nə alınmayıbsa iş qırmızı olsun (sahib görsün); ötürmə və fasilə yaşıl.
  if (res.failed.length && !res.posted.length) process.exitCode = 1;
}

module.exports = { VED, CHANNEL, options, mp4Info, shortsReason, foreignReason, policyReason, kindOf, linkOf, titleOf, descriptionOf, tagsOf, resourceOf, readVideos,
  quotaReset, token, channel, startUpload, sendFile, run, check, makeTestVideo, videoIdOf, TITLE_MAX, DESC_MAX, TAGS_MAX };
if (require.main === module) main().catch(e => { console.error(String(e?.message || e).slice(0, 300)); process.exitCode = 1; });
