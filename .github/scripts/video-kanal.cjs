// Kanal videoları: xəbər saytlarının öz Telegram kanalları və Instagram hesablarındakı videolar, bizim şərhimizlə (sahib, 2026-11-27).
// Sahib: «A B ni də.. B tək oxuaz la məhdud qalmasın» — B: xəbəri yazan saytın öz Telegram kanalındakı video (Oxu.az xəbərində
// t.me/oxuaze/201842 pəncərəsi, birbaşa mp4); bütün saytlar üçün. Həmin gün: «qutab bölməsi ilə razı deyiləm. Baku VS də sosil
// şəbəkələrdən götürüb öz komentini verib. Biz bunu da etməliyik» — Baku.ws-in Reels-i («Sevgi ilə hazırlanan qutab»: Bakı restoranının
// viral videosu, müəllif @foto_by_gunew göstərilib) və Beşiktaş azarkeşlərinin Batumidəki əsl görüntüsü bizdə yox idi.
//
// Bir modul, iki adapter (seçim, şərh, kredit, yoxlama ortaqdır):
//   telegram   https://t.me/s/<kanal> — kanalın ictimai önizləməsi (açarsız, Bot API yoxdur); postun videosu birbaşa faylla (telesco.pe).
//   instagram  Graph API Business Discovery (bizim açarla başqa biznes hesabının son 12 mediası; media_url — yalnız hesab yükləməyə
//              icazə verəndə və lisenziyalı musiqi olmayanda; yoxdursa Reels ötürülür). Açar: FB_PAGE_TOKEN, IG_USER_ID (və ya səhifənin
//              instagram_business_account-u). Dəqiq sorğu və 2026-11-27 sınağı: docs/sosial-video.md «Kanal videoları».
// Mənbələr: .github/video-kanal.json — yalnız assets/content-policy.js azSources-dakı saytların yoxlanmış kanalları (sayt → kanal və
// kanal → sayt). Siyahıda olmayan sayt faylda olsa da götürülmür (menbeler); işləyərkən kanalın başlığı saytın adını yazmırsa da (bizimdir).
// Axın (sosial-video.cjs kanalSec): vaxtı çatan platforma → kanalların son videoları (TELEGRAM_MAX_SAAT 12, INSTAGRAM_MAX_SAAT 48 saat) →
// süzgəc (aşağıda) → sıra: baxış sürəti (baxış ÷ saat) × güclü istiqamət (video-dil.cjs istiqamet) → Gemini yalnız paylaşımın mətnindən
// başlıq və 3–6 cümləlik diktor mətni yazır (rəqəm mənbədə olmalıdır, VS.checkText + VS.serhAzdir, saytın qaydası) → yalnız seçilənin
// faylı yüklənir (video-menbe.cjs indir: ölçü və imza) → «Kanal: kadrları yoxla» addımı (kadrYoxla): başqa saytın böyük başlıq bloku və
// ya yazı örtüyü, qan varsa video paylaşılmır.
// Qırmızı xətt 2: mənbə siyahıdakı saytdır — paylaşım saytın qaydasından (policyViolation, ünvan saytın öz ünvanı ilə) keçir; müxalifət
// kanalı, hesabı, müəllifi və paylaşımda müxalifət saytı mənbə kimi göstərilibsə götürülmür (muxalifet, muxalifetMetn). Paylaşımda adı
// çəkilən müəllif (@foto_by_gunew) mənbə deyil, görüntünün sahibidir: kreditdə yazılır, müxalifət yoxlamasından keçir.
// Xəbər səhifəsindəki Telegram pəncərəsi (video-menbe.cjs) də buradakı oxuyucunu və müxalifət yoxlamasını işlədir (tgEmbed).
"use strict";
const fs = require("fs"), path = require("path"), crypto = require("crypto");
const S = require("./social.cjs");
const VS = require("./video-ssenari.cjs");
const M = require("./video-menbe.cjs");
const { dil, istiqamet, cixarilir } = require("./video-dil.cjs");

const FAYL = path.join(__dirname, "..", "video-kanal.json");
const QAYDA = path.join(__dirname, "..", "..", "assets", "content-policy.js");
const UA = "Mozilla/5.0 (compatible; 8ulduz-bot; +https://8ulduz.az/)";
const AD = { telegram: "Telegram", instagram: "Instagram" };
const ACAR = { telegram: "tv", instagram: "iv" };
const REFERER = { telegram: "https://t.me/", instagram: "https://www.instagram.com/" };
// TG_SAY: bir dövrədə oxunan Telegram kanalı (önizləmə ~100 KB, açarsız). Instagram: faylı yoxlanmış hesablar (fayl: true) hər dəfə,
// yoxlanmayanlardan IG_SINAQ — sorğu həddi saatda 200-dür, bir dövrədə ən çox 4 sorğu (+1 hesab nömrəsi).
const TG_SAY = 8, IG_SINAQ = 1, CEHD = 3, METN_MIN = VS.SERH_MIN.simvol, METN_MAX = 1500, MIN_S = 4, MAX_S = 900, KLIP_BOYU = 30, KADR_SAY = 4;
const HED = { min: VS.SERH_MIN.simvol, max: 650, sentMin: VS.SERH_MIN.cumle, sentMax: 6 };
const BASLIQ_MIN = 25, BASLIQ_MAX = 110;
const clean = S.clean;
const num = (v, d) => (Number.isFinite(Number(v)) && String(v ?? "").trim() !== "" ? Number(v) : d);
const idOf = s => crypto.createHash("sha1").update(String(s)).digest("hex").slice(0, 16);
const ENT = { quot: '"', amp: "&", apos: "'", lt: "<", gt: ">", nbsp: " ", laquo: "«", raquo: "»", ndash: "–", mdash: "—", hellip: "…", rsquo: "’", lsquo: "‘", rdquo: "”", ldquo: "“" };
const unent = s => String(s ?? "").replace(/&(#x[0-9a-f]+|#\d+|[a-z]+);/gi, (m, e) => {
  if (e[0] === "#") { const c = /^#x/i.test(e) ? parseInt(e.slice(2), 16) : parseInt(e.slice(1), 10); return c > 0 && c < 0x110000 ? String.fromCodePoint(c) : " "; }
  return ENT[e.toLowerCase()] ?? m;
});

// --- Saytın qaydası (assets/content-policy.js: təmiz JSON) və müxalifət ------------------------------------------------------------
let QC = null;
function qayda(file = QAYDA) {
  if (!QC || QC.file !== file) { const s = fs.readFileSync(file, "utf8"); QC = { file, p: JSON.parse(s.slice(s.indexOf("{"), s.lastIndexOf("}") + 1)) }; }
  return QC.p;
}
const AZ = { ə: "e", ı: "i", ö: "o", ü: "u", ş: "s", ç: "c", ğ: "g" };
// Ad müqayisəsi üçün: kiçik hərf, azərbaycan hərfləri latına, işarəsiz («Meydan TV», «@meydantv», «meydan_tv» → «meydantv»).
const norm = s => String(s ?? "").toLocaleLowerCase("az").replace(/[əıöüşçğ]/g, ch => AZ[ch]).normalize("NFKD").replace(/[̀-ͯ]/g, "").replace(/[^a-z0-9а-яё]+/g, "");
const cfg = (file = FAYL) => JSON.parse(fs.readFileSync(file, "utf8"));
// Müxalifət kökləri: profilin siyahısı + bağlı saytların (blockedHosts) adı («meydan.tv» → «meydan»).
function kokler(file = FAYL, Q = qayda()) {
  const host = (Q.blockedHosts || []).map(h => norm(String(h).split(".")[0])).map(k => (k.endsWith("media") && k.length > 8 ? k.slice(0, -5) : k));
  return [...new Set([...(cfg(file).muxalifet || []).map(norm), ...host].filter(k => k.length >= 4))];
}
// Kanal, hesab və müəllif adı (kimlik): kök adın içindədirsə — müxalifət. Tapılan kök və ya "".
function muxalifet(names, { file = FAYL, Q = qayda() } = {}) {
  const k = kokler(file, Q);
  for (const n of (Array.isArray(names) ? names : [names]).map(norm).filter(Boolean)) { const hit = k.find(x => n.includes(x)); if (hit) return hit; }
  return "";
}
// Paylaşımın mətni: müxalifət saytı mənbə kimi (adı, ünvanı, @hesabı, t.me keçidi). Adi sözlər sayılmır — «Azadlıq meydanı» Bakının
// meydanıdır, «Turan-Tovuz» futbol klubudur; ona görə mətndə kök yox, tam ad və ünvan axtarılır, kök yalnız @hesab və keçiddə.
function muxalifetMetn(text, { file = FAYL, Q = qayda() } = {}) {
  const t = String(text ?? "").toLocaleLowerCase("az");
  const ad = [...(cfg(file).muxalifet_adlar || []), ...(Q.blockedHosts || [])].map(x => String(x).toLocaleLowerCase("az")).find(x => x && t.includes(x));
  if (ad) return ad;
  const hesab = [...t.matchAll(/(?:@|t\.me\/|instagram\.com\/)([a-z0-9_.]{3,40})/g)].map(m => m[1]);
  return hesab.length ? muxalifet(hesab, { file, Q }) : "";
}
const policyRx = src => { try { return src ? new RegExp(src, "i") : null; } catch { return null; } };
const testRx = (rx, s) => !!rx && (rx.test(s) || rx.test(String(s).toLocaleLowerCase("az")));

// --- Mənbə siyahısı --------------------------------------------------------------------------------------------------------------
// telegram: { ad (azSources açarı), kanal, yoxlama }, instagram: { ad, hesab, fayl (true | null | false), yoxlama }, aktiv? (false — söndürülüb).
function kecerli(m, nov) {
  if (!m || typeof m !== "object") return "obyekt deyil";
  if (!clean(m.ad)) return "ad";
  if (nov === "telegram" && !/^[A-Za-z][A-Za-z0-9_]{3,31}$/.test(String(m.kanal || ""))) return "kanal";
  if (nov === "instagram" && !/^[A-Za-z0-9._]{1,30}$/.test(String(m.hesab || ""))) return "hesab";
  if (!clean(m.yoxlama)) return "yoxlama (sayt → kanal, kanal → sayt)";
  return "";
}
// Yalnız siyahıdakı sayt (azSources), bağlı olmayan, müxalifət adı daşımayan kanal. sayt: saytın öz ünvanı (qaydanın yoxlaması üçün).
function menbeler(file = FAYL, Q = qayda()) {
  const j = cfg(file), out = { telegram: [], instagram: [], atilan: [] };
  for (const nov of ["telegram", "instagram"]) {
    for (const m of Array.isArray(j[nov]) ? j[nov] : []) {
      const d = Q.azSources?.[m?.ad]?.[0], why = kecerli(m, nov) || (!d ? "sayt siyahıda (azSources) yoxdur" : "")
        || ((Q.blockedHosts || []).some(h => d === h || d.endsWith(`.${h}`)) ? "bağlı sayt" : "") || (muxalifet([m.kanal || m.hesab, m.ad], { file, Q }) ? "müxalifət adı" : "");
      if (why) { out.atilan.push(`${nov} ${m?.kanal || m?.hesab || "?"}: ${why}`); continue; }
      if (m.aktiv === false) continue;
      out[nov].push({ ...m, nov, domen: d, sayt: `https://${d}/` });
    }
  }
  return out;
}

// --- Telegram: ictimai səhifənin oxunması --------------------------------------------------------------------------------------------
const TG_FAYL = /^https:\/\/(?:[a-z0-9-]+\.)*(?:telesco\.pe|cdn-telegram\.org|telegram-cdn\.org)\/file\/[^\s"'<>]+$/i;
const sayi = s => { const m = String(s || "").trim().match(/^([\d.,]+)\s*([KM])?$/i); if (!m) return 0; const n = Number(m[1].replace(",", ".")); return Math.round(n * (m[2] ? (/k/i.test(m[2]) ? 1e3 : 1e6) : 1)); };
const muddet = s => { const p = String(s || "").trim().split(":").map(Number); return p.length >= 2 && p.every(Number.isFinite) ? p.reduce((a, x) => a * 60 + x, 0) : 0; };
const tgMetn = raw => unent(String(raw || "").replace(/<br\s*\/?>/gi, "\n").replace(/<[^>]+>/g, "")).replace(/[ \t ]+/g, " ").replace(/ *\n */g, "\n").trim();
// Postlar (t.me/s/<kanal> və ya ?embed=1 səhifəsi): [{ post, kanal, id, ad, fwd, video, dur, text, links, at, baxis, link }].
// Albomda birinci video götürülür. «Media is too big» postunda fayl yoxdur (video: "").
function tgPostlar(html) {
  const out = [];
  for (const b of String(html || "").split(/(?=<div class="tgme_widget_message\b[^"]*"[^>]*\bdata-post=")/).slice(1)) {
    const post = (b.match(/^<div[^>]*\bdata-post="([A-Za-z][A-Za-z0-9_]{3,31}\/\d{1,10})"/) || [])[1];
    if (!post) continue;
    const [kanal, id] = post.split("/");
    const f = b.match(/class="tgme_widget_message_forwarded_from[^"]*"[^>]*>([\s\S]*?)<\/div>/);
    const fwd = f ? { ad: tgMetn(f[1]).replace(/^Forwarded from\s*/i, "").trim(), kanal: (f[1].match(/href="https:\/\/t\.me\/([A-Za-z0-9_]{4,32})/) || [])[1] || "" } : null;
    const video = [...b.matchAll(/<video\b[^>]*\bsrc="([^"]+)"/g)].map(m => unent(m[1])).find(u => TG_FAYL.test(u)) || "";
    const raw = (b.match(/class="tgme_widget_message_text[^"]*"[^>]*>([\s\S]*?)<\/div>/) || [])[1] || "";
    out.push({ post, kanal, id, ad: tgMetn((b.match(/class="tgme_widget_message_owner_name"[^>]*>([\s\S]*?)<\/a>/) || [])[1]), fwd, video,
      dur: muddet((b.match(/class="message_video_duration[^"]*"[^>]*>([^<]*)</) || [])[1]), text: tgMetn(raw),
      links: [...raw.matchAll(/href="([^"]+)"/g)].map(m => unent(m[1])), at: Date.parse((b.match(/<time\b[^>]*\bdatetime="([^"]+)"/) || [])[1] || "") || 0,
      baxis: sayi((b.match(/class="tgme_widget_message_views"[^>]*>([^<]*)</) || [])[1]), link: `https://t.me/${post}` });
  }
  return out;
}
// Kanalın başlığı, istifadəçi adı, təsviri və postları.
function tgKanal(html) {
  const s = String(html || "");
  return { ad: tgMetn((s.match(/class="tgme_channel_info_header_title"[^>]*>([\s\S]*?)<\/div>/) || [])[1]),
    kanal: tgMetn((s.match(/class="tgme_channel_info_header_username"[^>]*>([\s\S]*?)<\/div>/) || [])[1]).replace(/^@/, ""),
    tesvir: tgMetn((s.match(/class="tgme_channel_info_description"[^>]*>([\s\S]*?)<\/div>/) || [])[1]), postlar: tgPostlar(s) };
}
// Kanal hələ də o saytındır: istifadəçi adı eynidir, başlıq və ya təsvir saytın adını və ya ünvanını yazır (kanal satılsa, adı dəyişsə — yox).
function bizimdir(info, m) {
  if (!info?.kanal || norm(info.kanal) !== norm(m.kanal)) return false;
  const t = norm(`${info.ad} ${info.tesvir}`), label = norm(String(m.domen || "").split(".")[0]), key = norm(m.ad);
  return (label.length >= 3 && t.includes(label)) || (key.length >= 3 && t.includes(key));
}

async function oxu(url, f, referer = "") {
  const r = await f(url, { headers: { "user-agent": UA, ...(referer ? { referer } : {}) }, signal: AbortSignal.timeout(20000) }).catch(() => null);
  return r?.ok && r.text ? String(await r.text().catch(() => "")).slice(0, 3e6) : "";
}

// --- Instagram: Business Discovery ----------------------------------------------------------------------------------------------
// Açar sorğunun ünvanındadır (Graph API-nin sənədləşmiş yolu, meta-yoxla.cjs ilə eyni): ünvan heç vaxt jurnala yazılmır, xəta mətnindən
// açar silinir (gizle). İş axınında açar GitHub sirridir — jurnalda maskalanır.
const IG_SAHE = "id,caption,media_product_type,media_type,media_url,permalink,timestamp,like_count,comments_count,view_count";
const graph = env => `https://graph.facebook.com/${env.FB_GRAPH_VERSION || "v27.0"}/`;
const gizle = (s, env = process.env) => [env.FB_PAGE_TOKEN].filter(k => k && k.length > 8).reduce((m, k) => m.split(k).join("***"), String(s ?? ""));
async function gjson(url, f) {
  const r = await f(url, { signal: AbortSignal.timeout(20000) }).catch(() => null);
  return r?.json ? r.json().catch(() => ({})) : {};
}
// Bizim Instagram hesabının nömrəsi: IG_USER_ID, yoxsa Facebook səhifəsinin instagram_business_account-u.
async function igHesab(env, f) {
  if (/^\d{5,25}$/.test(String(env.IG_USER_ID || ""))) return env.IG_USER_ID;
  if (!env.FB_PAGE_ID) return "";
  const j = await gjson(`${graph(env)}${encodeURIComponent(env.FB_PAGE_ID)}?${new URLSearchParams({ fields: "instagram_business_account", access_token: env.FB_PAGE_TOKEN })}`, f);
  return String(j?.instagram_business_account?.id || "");
}
// Hesabın son 12 mediası: { media } və ya { error, limit } (limit: sorğu həddi — bu dövrədə Instagram-a bir də sorğu yoxdur).
async function igMedia(hesab, { ig, env, fetch: f }) {
  const fields = `business_discovery.username(${hesab}){username,followers_count,media.limit(12){${IG_SAHE}}}`;
  const j = await gjson(`${graph(env)}${encodeURIComponent(ig)}?${new URLSearchParams({ fields, access_token: env.FB_PAGE_TOKEN })}`, f);
  if (j?.error || !j?.business_discovery) {
    const code = Number(j?.error?.code);
    return { error: gizle(`${j?.error?.message || "cavab yoxdur"}${code ? ` (#${code})` : ""}`, env).slice(0, 200), limit: [4, 17, 32, 613].includes(code) };
  }
  return { media: Array.isArray(j.business_discovery.media?.data) ? j.business_discovery.media.data : [] };
}

// --- Paylaşımın mətni, müəllifi, krediti ----------------------------------------------------------------------------------------
// Diktor mətni üçün: keçid, emoji, heşteq və kanalın öz çağırış sətirləri («Son xəbərlər», «Bizimlə əlaqə», «Ətraflı: …») atılır.
const CAGIRIS = /^(ətraflı|daha ətraflı|son xəbərlər|bizimlə əlaqə|abunə ol|kanala qoşul|kanalımıza|bizi izləyin|izləyin|xəbərləri bizdən|подписаться|подписывайтесь|наш канал)(?![\p{L}\p{N}])/iu;
function metnTemiz(s) {
  return String(s ?? "").replace(/https?:\/\/\S+|www\.\S+/gi, " ").replace(/#[\p{L}\p{N}_]+/gu, " ")
    .replace(/[\p{Extended_Pictographic}\u{1F1E6}-\u{1F1FF}️‍⃣▪️♦️•►▶️➡️⬇️👉]/gu, " ")
    .split(/\n+/).map(x => x.replace(/\s+/g, " ").trim()).filter(x => x && !CAGIRIS.test(x) && (x.match(/\p{L}/gu) || []).length >= 3)
    .filter(x => !/^@?[\p{L}\p{N}_.]+(?:\s*\|\s*@?[\p{L}\p{N}_.]+)*$/u.test(x) || x.split(" ").length > 3).join("\n").slice(0, METN_MAX);
}
// Paylaşımda adı çəkilən müəllif: kredit sözündən sonrakı (və ya öz sətrindəki) @hesab — kanalın, bizim və bot hesabı deyil — və ya
// «Görüntü:/Çəkiliş:/Video: Ad». Mətnin içində adı çəkilən adam («futbolçu @x qol vurdu») müəllif sayılmır; «Müəllif: Ad» də yox —
// Kulis.az-da şeirin müəllifidir (2026-11-27: «Müəllif: Osman Sarıvəlli», görüntünün sahibi deyil).
const KREDIT_SOZ = /(?:(?<!\p{L})(?:müəllif|görüntü|video|çəkiliş|kadr|mənbə|credit|via|by)|📹|🎥|📸|🎬|©)[\s:\-–—]*$/iu;
function muellifOf(text, own = []) {
  const s = String(text ?? ""), mine = new Set([...own, "8ulduz", "8ulduz.az"].map(norm));
  for (const m of s.matchAll(/(?:^|[^\p{L}\p{N}_@.])@([A-Za-z0-9_](?:[A-Za-z0-9_.]{0,28}[A-Za-z0-9_])?)/gu)) {
    const i = m.index + m[0].indexOf("@"), setir = s.slice(s.lastIndexOf("\n", i) + 1, (s.indexOf("\n", i) + 1 || s.length + 1) - 1);
    const kredit = KREDIT_SOZ.test(s.slice(Math.max(0, i - 30), i)) || setir.replace(/[\p{Extended_Pictographic}\uFE0F\s|]/gu, "") === `@${m[1]}`;
    if (kredit && !mine.has(norm(m[1])) && !/bot$/i.test(m[1])) return `@${m[1]}`;
  }
  const a = s.match(/(?:^|\n)\s*(?:görüntü|çəkiliş|video|kadr)\s*:\s*([^\n@#]{2,40}?)\s*(?:\n|$)/iu);
  return a && !/https?:/i.test(a[1]) ? clean(a[1]).replace(/[.,;:]+$/, "") : "";
}
// «Oxu.az (Telegram)», «Baku.ws (Instagram), @foto_by_gunew»: videoda və post mətnində «Görüntü: …».
const kredit = (ad, platforma, muellif = "") => `${clean(ad)} (${AD[platforma] || platforma})${muellif ? `, ${muellif}` : ""}`;
const basliq0 = metn => S.cut(String(metn || "").split("\n")[0], 160);

// --- Tezlik ---------------------------------------------------------------------------------------------------------------------
// Hər platformanın öz həddi və arası (state.tv, state.iv: video → vaxt); ümumi fasiləyə və gündəlik 30-a (VIDEO_GUNDE) sayılır.
function options(env = process.env) {
  return {
    telegram: { on: env.TELEGRAM_VIDEO !== "0", perDay: num(env.TELEGRAM_GUNDE, 6), gapMin: num(env.TELEGRAM_ARA_MIN, 90), maxAgeH: num(env.TELEGRAM_MAX_SAAT, 12) },
    instagram: { on: env.INSTAGRAM_VIDEO !== "0", perDay: num(env.INSTAGRAM_GUNDE, 6), gapMin: num(env.INSTAGRAM_ARA_MIN, 120), maxAgeH: num(env.INSTAGRAM_MAX_SAAT, 48) },
  };
}
const SOND = { telegram: "TELEGRAM_VIDEO=0", instagram: "INSTAGRAM_VIDEO=0" };
function dueBir(state, now, o, p) {
  if (!o[p].on) return `${AD[p]} videosu söndürülüb (${SOND[p]})`;
  const sec = now / 1000, times = Object.values(state?.[ACAR[p]] || {});
  const day = times.filter(t => sec - t < 86400).length;
  if (day >= o[p].perDay) return `24 saatda ${day} ${AD[p]} videosu (hədd ${o[p].perDay})`;
  const ago = Math.floor((sec - Math.max(0, ...times)) / 60);
  if (ago < o[p].gapMin) return `son ${AD[p]} videosu ${ago} dəq əvvəl (ara ${o[p].gapMin} dəq)`;
  return "";
}
// Vaxtı çatan platformalar, ən çoxdan videosu olmayan əvvəl. zorla (VIDEO_TUR=kanal): söndürülməyən hər biri.
function sira(state, now, o = options(), zorla = false) {
  const last = p => Math.max(0, ...Object.values(state?.[ACAR[p]] || {}));
  return ["telegram", "instagram"].filter(p => (zorla ? o[p].on : !dueBir(state, now, o, p))).sort((a, b) => last(a) - last(b));
}
const due = (state, now, o = options(), zorla = false) => (sira(state, now, o, zorla).length ? "" : ["telegram", "instagram"].map(p => dueBir(state, now, o, p) || `${AD[p]} söndürülüb`).join("; "));

// --- Namizədlər -----------------------------------------------------------------------------------------------------------------
// Növbə: ən çoxdan oxunmayan kanal əvvəl (state.km: «tg:<kanal>», «ig:<hesab>» → vaxt).
function novbe(list, state, pre) {
  const last = m => (state?.km || {})[`${pre}:${m.kanal || m.hesab}`] || 0;
  return list.map((m, i) => ({ m, i })).sort((a, b) => last(a.m) - last(b.m) || a.i - b.i).map(x => x.m);
}
// Namizəd: { id, platforma, m, link, video, at, baxis, dur, esli, metn, muellif } → "" (uyğundur) və ya səbəb. bos: səbəb jurnala yazılmır,
// siyahıya (skip) düşmür (köhnə, videosuz, işlənmiş).
function suz(c, { now, o, state, policy, D = dil() }) {
  if (!c.video) return { bos: "video yoxdur" };
  if (state?.[ACAR[c.platforma]]?.[c.id] || state?.v?.[c.id] || state?.skip?.[c.id]) return { bos: "işlənib" };
  if (!c.at || now - c.at > o.maxAgeH * 3600e3 || c.at - now > 600e3) return { bos: "köhnədir" };
  if (c.fwd) return { yox: `başqa kanaldan yönləndirilib (${c.fwd.ad || c.fwd.kanal || "?"})` };
  if (c.dur && (c.dur < MIN_S || c.dur > MAX_S)) return { yox: `video ${c.dur} s` };
  if (c.metn.length < METN_MIN) return { yox: `mətn qısadır (${c.metn.length} simvol, ən az ${METN_MIN})` };
  // Videonun dili profildədir (xəbər videosunda lent.dil kimi): başqa dildə yazan kanalın postu (Haqqin.az rusca) götürülmür.
  if (!D.re.herf.test(c.metn)) return { yox: "mətn videonun dilində deyil" };
  const title = basliq0(c.metn), kenar = D.x?.kenar ? new RegExp(D.x.kenar, "iu") : null;
  if (VS.protokol({ title })) return { yox: "protokol (görüş, qəbul, təbrik)" };
  if (kenar?.test(c.metn)) return { yox: "qan və ya meyit sözü" };
  if (M.yayim({ title: c.metn }, D)) return { yox: "film, serial, klip kadrı ola bilər" };
  if (cixarilir(c.metn, D)) return { yox: "heyvan, təbiət, kosmos (insan hadisəsi yoxdur)" };
  const mx = muxalifetMetn(c.esli) || (c.muellif ? muxalifet(c.muellif) : "");
  if (mx) return { yox: `müxalifət mənbəsi (${mx})` };
  if (policy({ id: c.id, title, summary: c.metn, source: c.m.ad, sourceUrl: c.m.sayt, category: "", lang: D.lent.dil })) return { yox: "saytın qaydasından keçmir" };
  const topic = S.topicOf({ title, summary: c.metn }, c.at / 1000);
  if ((state?.topics || []).some(t => S.sameTopic(t, topic))) return { yox: "eyni mövzuda video var" };
  return {};
}
// Sıra: baxış sürəti × tamaşaçı marağı — rəsmi tədbir (zəif mövzu, lent.ceki.zeif) zəif əmsalla, yoxsa güclü istiqamətin əmsalı
// (sosial-video.cjs cekisi kimi; «Video mövzuları»).
function bal(c, now, D = dil()) {
  const k = D.re.zeif?.test(basliq0(c.metn)) ? Number(D.lent.ceki?.zeif_emsal) || 1 : istiqamet(c.metn, D)?.emsal || 1;
  return (c.baxis / Math.max(1, (now - c.at) / 3600e3)) * k;
}

function tgNamized(p, m) {
  const own = [m.kanal, p.kanal];
  return { id: idOf(`tg:${p.post.toLowerCase()}`), platforma: "telegram", m, link: p.link, video: p.video, at: p.at, baxis: p.baxis, dur: p.dur, fwd: p.fwd,
    esli: p.text, metn: metnTemiz(p.text), muellif: muellifOf(p.text, own) };
}
function igNamized(x, m) {
  const text = String(x?.caption || "");
  return { id: idOf(`ig:${x?.id}`), platforma: "instagram", m, link: /^https:\/\/(www\.)?instagram\.com\//.test(x?.permalink || "") ? x.permalink : `https://www.instagram.com/${m.hesab}/`,
    video: /^https:\/\//.test(x?.media_url || "") ? x.media_url : "", at: Date.parse(x?.timestamp || "") || 0, baxis: Number(x?.view_count ?? x?.like_count ?? 0) || 0, dur: 0,
    fwd: null, esli: text, metn: metnTemiz(text), muellif: muellifOf(text, [m.hesab]) };
}

async function namizedler(p, { list, state, now, o, env, fetch: f, policy, log, deps = {} }) {
  const read = deps.oxu || oxu, out = [], sec = Math.floor(now / 1000), say = { yox: 0 };
  const al = c => {
    const r = suz(c, { now, o: o[p], state, policy });
    if (r.bos) return;
    if (r.yox) { (state.skip ||= {})[c.id] = sec; say.yox++; if (!/qısadır|video \d|dilində deyil/.test(r.yox)) log(`kanal videosu: ötürülür (${r.yox}) — ${c.link}`); return; }
    out.push({ ...c, bal: bal(c, now) });
  };
  if (p === "telegram") {
    for (const m of novbe(list.telegram, state, "tg").slice(0, TG_SAY)) {
      const html = await read(`https://t.me/s/${m.kanal}`, f);
      (state.km ||= {})[`tg:${m.kanal}`] = sec;
      if (!html) { log(`kanal videosu: t.me/s/${m.kanal} oxunmadı`); continue; }
      const info = tgKanal(html);
      if (!bizimdir(info, m)) { log(`kanal videosu: t.me/${m.kanal} — başlıq və təsvir ${m.domen} saytını yazmır («${info.ad || "?"}»), götürülmür`); continue; }
      for (const x of info.postlar) al(tgNamized(x, m));
    }
  } else {
    if (!env.FB_PAGE_TOKEN) { log("kanal videosu: Instagram — FB_PAGE_TOKEN yoxdur, ötürülür"); return out; }
    const ig = await (deps.igHesab || igHesab)(env, f);
    if (!ig) { log("kanal videosu: Instagram — bizim hesabın nömrəsi (IG_USER_ID) tapılmadı, ötürülür"); return out; }
    const sabit = list.instagram.filter(m => m.fayl === true), qalan = novbe(list.instagram.filter(m => m.fayl !== true), state, "ig").slice(0, IG_SINAQ);
    for (const m of [...sabit, ...qalan]) {
      const r = await igMedia(m.hesab, { ig, env, fetch: f });
      (state.km ||= {})[`ig:${m.hesab}`] = sec;
      if (r.error) { log(`kanal videosu: Instagram @${m.hesab} oxunmadı — ${r.error}`); if (r.limit) break; continue; }
      const reels = r.media.filter(x => x?.media_product_type === "REELS" || x?.media_type === "VIDEO");
      log(`kanal videosu: Instagram @${m.hesab} — ${reels.length} video, ${reels.filter(x => x.media_url).length}-i faylla`);
      for (const x of reels) al(igNamized(x, m));
    }
  }
  if (say.yox) log(`kanal videosu: ${AD[p]} — ${say.yox} video süzgəcdən keçmədi`);
  return out.sort((a, b) => b.bal - a.bal || b.at - a.at);
}

// --- Şərh: Gemini yalnız paylaşımın mətnindən -----------------------------------------------------------------------------------
const PROMPT = `Sən 8ulduz.az xəbər saytının video redaktorusan. Qısa şaquli video (Reels, Shorts) {menbe} xəbər saytının {platforma}
paylaşımındakı videodandır. Aşağıda paylaşımın öz mətni var (mənbənin dilində). Video üçün başlıq və diktor mətni yaz.

Qaydalar:
- {dil} yaz. {yad}nida və sual işarəsi, keçid, emoji, heşteq, @hesab olmasın. {nisbi} yazma.
- 3–5 cümlə, 200–600 simvol. Birinci cümlə hadisənin özüdür (nə, harada). Yalnız paylaşımın mətnindəki faktlar: heç nə əlavə etmə,
  təxmin etmə, şərh vermə. Tamaşaçı mövzunu bilmir: mətn nə baş verdiyini, harada və niyə xəbər olduğunu aydın deməlidir.
- Rəqəmi mənbədəki kimi yaz; mənbədə olmayan rəqəm yazma. Adları inisialsız yaz.
- basliq: 30–100 simvol, hadisəni deyən sadə cümlə; sonda nöqtə olmasın, «video» sözü olmasın.
- etiket: 3 mövzu etiketi ({etiket_dili}, «#»-siz, boşluqsuz).
- "uygun": false — paylaşım reklam, müsabiqə, abunə çağırışı, rəsmi görüş, qəbul, təbrik, başsağlığı, siyasi bəyanatdırsa; mətndə üç
  cümləyə yetən aydın fakt yoxdursa; videoda ölüm anı, qan, meyit, ağır yaralı və ya işgəncə varsa (müharibə xəbəri özü qadağan deyil); mətn yalnız oyunun hesabıdırsa.

Yalnız JSON qaytar: {"uygun": true, "basliq": "...", "text": "...", "etiket": ["...", "...", "..."]}

Paylaşım ({menbe}, {platforma}): {metn}`;
function promptOf(c, D = dil()) {
  const s = D.ssenari, yad = s.yad_herf_adi ? `${s.yad_herf_adi[0].toLocaleUpperCase(D.locale)}${s.yad_herf_adi.slice(1)}, ` : "";
  return PROMPT.replace(/\{menbe\}/g, () => clean(c.m.ad)).replace(/\{platforma\}/g, AD[c.platforma]).replace(/\{dil\}/g, s.dil).replace("{yad}", yad)
    .replace("{nisbi}", s.nisbi_gun_misal).replace("{etiket_dili}", s.etiket_dili).replace("{metn}", () => c.metn);
}
// → { title, text, etiket } | { yox: səbəb } (bu videodan şərh olmur — bir də sınanmır) | { gec: səbəb } (indi olmur: açar, Gemini).
async function metnYaz(c, { env = process.env, fetch: f = globalThis.fetch, policy, log = console.log, D = dil() } = {}) {
  if (!env.GEMINI_API_KEY) return { gec: "GEMINI_API_KEY yoxdur" };
  const raw = await VS.gemini(promptOf(c, D), env.GEMINI_API_KEY, f, log, env);
  if (raw == null) return { gec: "Gemini cavab vermir" };
  let j = null;
  try { j = JSON.parse(String(raw).replace(/^```(?:json)?\s*|\s*```$/g, "")); } catch {}
  if (!j || typeof j !== "object") return { yox: "cavab JSON deyil" };
  if (j.uygun === false) return { yox: "Gemini: paylaşımdan şərh olmur (reklam, protokol, fakt azdır)" };
  const title = VS.dilLatin(clean(j.basliq)).replace(/[.!?…]+$/, ""), text = VS.dilLatin(clean(j.text));
  const a = { id: c.id, kind: "kanal", title, summary: text, source: c.m.ad, sourceUrl: c.m.sayt, category: "", lang: D.lent.dil };
  const kenar = D.x?.kenar ? new RegExp(D.x.kenar, "iu") : null;
  const why = !text ? "mətn boşdur" : title.length < BASLIQ_MIN || title.length > BASLIQ_MAX ? `başlıq ${title.length} simvol` : D.re.yadHerf?.test(title) ? "başlıqda yad hərf"
    : /@|#|https?:/.test(`${title} ${text}`) ? "@hesab, heşteq və ya keçid" : policy(a) ? "saytın qaydasından keçmir" : muxalifetMetn(`${title} ${text}`) ? "müxalifət mənbəsi"
    : kenar?.test(text) ? "qan və ya meyit sözü" : cixarilir(`${title}. ${text}`, D) ? "heyvan, təbiət və ya kosmos mövzusu"
    : VS.checkText(text, `${c.metn}\n${c.esli}`, a, policy, HED) || VS.serhAzdir(text);
  if (why) return { yox: `mətn yoxlamadan keçmədi: ${why}` };
  const etiket = VS.hashtags(j.etiket);
  return { title, text, ...(etiket.length && !policy({ ...a, summary: etiket.join(" ") }) ? { etiket } : {}) };
}

// Saytdakı xəbər: eyni saytın son 24 saatdakı xəbəri, başlığı paylaşımın birinci sətri ilə eynidir (və ya onun başlanğıcıdır) — keçid
// ona; yoxdursa sosial-video.cjs saytın ana səhifəsini verir.
function xeberTap(articles, c, now = Date.now()) {
  const ilk = norm(String(c.esli || "").split("\n").find(x => (x.match(/\p{L}/gu) || []).length >= 3) || "");
  if (ilk.length < 20) return null;
  return (articles || []).find(a => /^[0-9a-f]{16}$/.test(String(a?.id || "")) && now - (Date.parse(a.publishedAt || "") || 0) < 86400e3
    && [a.source, ...(a.alts || []).map(x => x?.source)].includes(c.m.ad) && (t => t.length >= 20 && (ilk.startsWith(t) || t.startsWith(ilk)))(norm(a.title))) || null;
}

// Seçim + şərh + fayl → xeber.json-un girişi (sosial-video.cjs kanalSec yazır) və ya null. Gemini olmayanda heç nə «yanmır» (növbəti dövrə).
async function hazirla({ now = Date.now(), state, env = process.env, fetch: f = globalThis.fetch, policy, dir, log = console.log, articles = [], zorla = false, file = FAYL, deps = {} }) {
  if (typeof policy !== "function") throw new Error("kanal videosu: saytın qaydası (policyViolation) verilməyib");
  const o = options(env), plat = sira(state, now, o, zorla);
  if (!plat.length) return null;
  const list = menbeler(file);
  for (const x of list.atilan) log(`kanal videosu: siyahıdan atıldı — ${x}`);
  const t = Math.floor(now / 1000);
  for (const p of plat) {
    const pool = await namizedler(p, { list, state, now, o, env, fetch: f, policy, log, deps });
    if (!pool.length) { log(`kanal videosu: ${AD[p]} — təzə, faylı açıq, mətni yetən video yoxdur`); continue; }
    fs.mkdirSync(dir, { recursive: true });
    for (const c of pool.slice(0, CEHD)) {
      const s = await (deps.metnYaz || metnYaz)(c, { env, fetch: f, policy, log });
      if (s.gec) { log(`kanal videosu: indi yazılmır (${s.gec}) — növbəti dövrədə`); return null; }
      if (s.yox) { (state.skip ||= {})[c.id] = t; log(`kanal videosu: ötürülür (${s.yox}) — ${c.link}`); continue; }
      const err = await (deps.indir || M.indir)(c.video, path.join(dir, M.FAYL), f, REFERER[p]).catch(e => String(e?.message || e).slice(0, 120));
      if (err) { (state.skip ||= {})[c.id] = t; log(`kanal videosu: fayl alınmadı (${err}) — ${c.link}`); continue; }
      const ist = istiqamet(`${s.title} ${s.text}`), xb = xeberTap(articles, c, now);
      log(`kanal videosu: ${c.m.ad} (${AD[p]}) — ${c.baxis} baxış${ist ? `, istiqamət ${ist.ad}` : ""} → ${s.title}`);
      return { id: c.id, tur: "kanal", kind: "kanal", platforma: p, title: s.title, summary: "", text: s.text, category: "", source: c.m.ad, sourceUrl: c.link,
        sayt: c.m.sayt, publishedAt: new Date(c.at).toISOString(), alts: [], esli: { metn: c.metn.slice(0, 600), hesab: c.m.kanal || c.m.hesab }, ssenari: "gemini",
        baxis: c.baxis, ...(ist ? { istiqamet: ist.ad } : {}), ...(s.etiket ? { hashtags: s.etiket } : {}), ...(c.muellif ? { muellif: c.muellif } : {}),
        ...(xb ? { link: S.shareUrl(xb), xeber: xb.id } : {}), klip_boyu: KLIP_BOYU,
        menbeVideo: { file: M.FAYL, url: c.video, sehife: c.link, kredit: kredit(c.m.ad, p, c.muellif) } };
    }
  }
  return null;
}

// --- Xəbər səhifəsindəki Telegram pəncərəsi (video-menbe.cjs) ---------------------------------------------------------------------
// Postun ictimai pəncərəsi (?embed=1&mode=tme) → birbaşa fayl. Kanal istənilən ola bilər (Bakupost başqa kanalın postunu yerləşdirmişdi),
// müxalifət kanalı, yönləndirilən müxalifət postu, mətnində müxalifət saytı mənbə kimi olan post götürülmür. Siyahıdakı saytın kanalı
// deyilsə, mətnində rəhbərlik (leaderTerms) olan post da götürülmür. Kredit: siyahıdakı kanal — saytın adı, yoxsa kanalın başlığı.
async function tgEmbed(post, { fetch: f = globalThis.fetch, log = console.log, dir, sehife = "", file = FAYL, deps = {} } = {}) {
  const [kanal, id] = String(post || "").split("/");
  if (!/^[A-Za-z][A-Za-z0-9_]{3,31}$/.test(kanal || "") || !/^\d{1,10}$/.test(id || "")) return null;
  const html = await (deps.oxu || oxu)(`https://t.me/${kanal}/${id}?embed=1&mode=tme`, f, sehife);
  const p = tgPostlar(html).find(x => x.post.toLowerCase() === `${kanal}/${id}`.toLowerCase());
  if (!p) { log(`mənbə videosu: Telegram ${kanal}/${id} — post oxunmadı`); return null; }
  if (!p.video) { log(`mənbə videosu: Telegram ${p.post} — postda götürülə bilən video yoxdur (və ya fayl çox böyükdür)`); return null; }
  const Q = qayda(), mx = muxalifet([p.kanal, p.ad, p.fwd?.kanal, p.fwd?.ad].filter(Boolean)) || muxalifetMetn(p.text);
  if (mx) { log(`mənbə videosu: Telegram ${p.post} — müxalifət kanalı və ya mənbəsi (${mx}), götürülmür`); return null; }
  const asil = p.fwd?.kanal || p.kanal, bizim = menbeler(file, Q).telegram.find(m => norm(m.kanal) === norm(asil));
  if (!bizim && testRx(policyRx(Q.leaderTerms), p.text)) { log(`mənbə videosu: Telegram ${p.post} — siyahıda olmayan kanal, mətndə rəhbərlik — götürülmür`); return null; }
  const err = await (deps.indir || M.indir)(p.video, path.join(dir, M.FAYL), f, REFERER.telegram).catch(e => String(e?.message || e).slice(0, 120));
  if (err) { log(`mənbə videosu: Telegram ${p.post} — ${err}`); return null; }
  const bytes = fs.statSync(path.join(dir, M.FAYL)).size, ad = bizim ? bizim.ad : (p.fwd ? p.fwd.ad || `@${p.fwd.kanal}` : p.ad || `@${p.kanal}`);
  log(`mənbə videosu: Telegram ${p.post} (${ad}) — ${(bytes / 1e6).toFixed(1)} MB`);
  return { file: M.FAYL, url: p.video, sehife: p.link, kredit: kredit(ad, "telegram", muellifOf(p.text, [p.kanal, asil])), telegram: p.post, bytes };
}

// --- Kadr yoxlaması («Kanal: kadrları yoxla», ffmpeg-dən sonra) -----------------------------------------------------------------------
// Xəbər saytının videosunda onun öz dizaynı ola bilər (Baku.ws Reels-lərində başlıq bloku). Su nişanı silinmir (docs/sosial-video.md);
// başqa saytın böyük başlıq bloku və ya yazı örtüyü olan video bizim başlıq və altyazımızla toqquşur — götürülmür. Küncdəki kiçik loqo olar.
// Kadrları Gemini görür (video-arxiv.cjs kadrlar, X videosunun yoxlaması kimi). X-dən fərqli olaraq yoxlamaq mümkün olmasa video getmir:
// başqa saytın başlıq bloku yoxlanmadan bizim səhifəyə düşməsin.
const KADR_PROMPT = `Sən 8ulduz.az xəbər saytının video redaktorusan. Videonu {menbe} saytının {platforma} paylaşımından götürürük; üstünə
öz başlığımızı, altyazımızı və səsimizi qoyuruq. Aşağıda videonun {n} kadrı var (əvvəlindən sonuna). Yoxla:
- "yazi": true — kadrda başqa saytın və ya hesabın böyük başlıq bloku, xəbər başlığı, ekranın böyük hissəsini tutan yazı zolağı və ya
  mətn örtüyü var. Küncdəki kiçik loqo, kiçik su nişanı və ya kiçik hesab adı sayılmır — onda false.
- "qan": true — yalnız kadrda ölüm anı, qan, meyit və ya ağır yaralı açıq görünürsə.
- "sebeb": true olanda bir qısa cümlə, {dil}.

Yalnız JSON qaytar: {"yazi": false, "qan": false, "sebeb": ""}

Mətnimiz: {metn}`;
const kadrPromptOf = (x, n, D = dil()) => KADR_PROMPT.replace("{menbe}", () => clean(x.source)).replace("{platforma}", AD[x.platforma] || "Telegram")
  .replace("{n}", String(n)).replace(/\{dil\}/g, D.ssenari.dil).replace("{metn}", () => clean(x.text));
function kadrlar(file) {
  const VA = require("./video-arxiv.cjs"), p = VA.probe(file);
  return VA.kadrlar(file, p.dur, p.w, p.h).jpg;
}
// xeber.json-un kanal girişi → { dayan: səbəb } (video paylaşılmır) və ya { ok: true }.
async function kadrYoxla(x, { dir, env = process.env, fetch: f = globalThis.fetch, log = console.log, D = dil(), deps = {} } = {}) {
  const az = VS.serhAzdir(x?.text);
  if (az) return { dayan: az };
  if (!env.GEMINI_API_KEY) return { dayan: "kadrlar yoxlanmadı (GEMINI_API_KEY yoxdur)" };
  let jpg = [];
  try { jpg = ((deps.kadrlar || kadrlar)(path.join(dir, M.FAYL)) || []).slice(0, KADR_SAY); }
  catch (e) { return { dayan: `kadrlar alınmadı: ${String(e?.message || e).slice(0, 120)}` }; }
  if (!jpg.length) return { dayan: "kadr yoxdur" };
  const parts = [{ text: kadrPromptOf(x, jpg.length, D) }];
  jpg.forEach((b, i) => parts.push({ text: `Kadr ${i + 1}:` }, { inline_data: { mime_type: "image/jpeg", data: Buffer.from(b).toString("base64") } }));
  const raw = await VS.gemini(parts, env.GEMINI_API_KEY, f, log, env);
  if (raw == null) return { dayan: "Gemini cavab vermir — kadrlar yoxlanmadı" };
  let j = null;
  try { j = JSON.parse(String(raw).replace(/^```(?:json)?\s*|\s*```$/g, "")); } catch {}
  if (!j || typeof j !== "object") return { dayan: "kadr yoxlamasının cavabı JSON deyil" };
  if (j.qan === true) return { dayan: "kadrda ölüm anı, qan və ya meyit görünür" };
  if (j.yazi === true) return { dayan: `başqa saytın başlıq bloku və ya yazı örtüyü var${clean(j.sebeb) ? ` (${clean(j.sebeb).slice(0, 160)})` : ""}` };
  return { ok: true };
}

module.exports = { FAYL, AD, ACAR, TG_SAY, IG_SINAQ, CEHD, METN_MIN, HED, qayda, norm, kokler, muxalifet, muxalifetMetn, kecerli, menbeler, TG_FAYL, sayi, muddet,
  tgMetn, tgPostlar, tgKanal, bizimdir, igHesab, igMedia, gizle, metnTemiz, muellifOf, kredit, options, dueBir, sira, due, novbe, suz, bal, tgNamized, igNamized,
  namizedler, PROMPT, promptOf, metnYaz, xeberTap, hazirla, tgEmbed, KADR_PROMPT, kadrPromptOf, kadrYoxla };
