// Xəbərin mənbə saytındakı öz videosu — videomuzun görüntüsü kimi (sahib, 2026-11-26: «Bir çox xəbər saytı hesabı eyni görüntünü
// verir, məsələn Ceyhun Bayramovun “Sabah”ın oyunundakı videosu… biz də verək. Qaydalarımızda bunu əngəlləyən nəsə varsa sil.
// Mən hüquqi tərəfini də öyrənmişəm, problem yoxdur»). Əvvəlki qayda (docs/sosial-video.md «Müəllif hüququ»): yalnız video bankı
// və sahibin görüntüsü. Əsas: baku.ws_official təhlili — ən çox baxılan 12 Reels-in hamısında hadisənin öz görüntüsü var.
//
// Nə götürülür: xəbəri yazan saytın (əsas mənbə, sonra digər mənbələr) səhifəsindəki video faylı (mp4, mov, m4v, webm) — səhifənin
// özündə və ya onun pleyer çərçivəsində (player.bizim.media, bax.tv/embed, newstube.az/embed). Görüntünün mənbəyi videoda və post
// mətnində yazılır: «Görüntü: Bizim.Media». Səs götürülmür (diktor mətni bizimdir), su nişanı silinmir.
// Nə götürülmür:
//   - YouTube, Instagram, TikTok, Telegram pəncərəsi: orada fayl yoxdur, platformanın qorumasını aşmaq olmaz — bank klipi ilə davam;
//   - X videoları (video.twimg.com) və saytın öz səhifələri (8ULDUZ): X videoları yalnız yerləşdirilir (docs/youtube.md);
//   - reklam və saytın hər səhifəsində olan fayl (banner; baş səhifədə də varsa atılır);
//   - film, serial, musiqi klipi və treyler kadrı (profil lent.yayim) — YouTube Content ID və Meta Rights Manager avtomatik tanıyır.
//     Açmaq: Variables MENBE_YAYIM=1. Liqaların oyun kadrı (qol, icmal) 2026-11-26-dan götürülür (sahib: «3 et»).
// Fayl seçim addımında yüklənir (ffmpeg hələ yoxdur): ölçü həddi və faylın imzası (ftyp/EBML) yoxlanır; müddət və ölçü montajda
// (video-xeber.cjs render) yoxlanır — keçməsə bank klipləri ilə davam edir. Hamısını söndürmək: Variables MENBE_VIDEO=0.
"use strict";
const fs = require("fs"), path = require("path");
const { dil } = require("./video-dil.cjs");

const UA = "Mozilla/5.0 (compatible; 8ulduz-bot; +https://8ulduz.az/)";
const FAYL = "klip-menbe.mp4";   // «klip-*.mp4» montajdan sonra silinir (sosial-video.yml); konteyneri ffmpeg məzmundan tanıyır
const MAX_BYTES = 150e6, MIN_BYTES = 150e3, SEHIFE_MAX = 4, CERCIVE_MAX = 2, HTML_MAX = 3e6;
// Fayl ünvanı: uzantı, sonra istəyə bağlı «/» (newstube: …_720p.mp4/) və sorğu.
const FAYL_RE = /(?:https?:)?\/\/[^"'\s<>\\]+\.(?:mp4|mov|m4v|webm)(?:\/(?=["'\s<>\\?]))?(?:\?[^"'\s<>\\]*)?/gi;
// Heç vaxt: platformalar (fayl bizə verilmir və ya X qaydası), reklam şəbəkələri, saytın bəzəyi.
const YAD = /(twimg\.com|(^|[/.])x\.com|twitter\.com|youtube|youtu\.be|googlevideo|instagram|cdninstagram|fbcdn|facebook|tiktok|telegram|(^|[/.])t\.me|vk\.com|ok\.ru|adriver|adviad|doubleclick|googlesyndication|adform|yandex)/i;
const REKLAM = /(banner|reklam|\/ads?[/_-]|[/_.-]ads?\.|promo|informer|manifest|sponsor|popup)/i;
const PLEYER = /(embed|player|pleyer)/i;

const abs = (u, base) => { try { return new URL(String(u).replace(/&amp;/g, "&"), base).href; } catch { return ""; } };
const yaxsi = u => /^https:\/\//.test(u) && !YAD.test(u) && !REKLAM.test(u);
// Keyfiyyət: ünvanda «720p» kimi nişan varsa böyüyü (1080-dək) əvvəl.
const keyfiyyet = u => { const m = String(u).match(/(\d{3,4})p\b/i), n = m ? Number(m[1]) : 0; return n > 1080 ? 0 : n; };

// Səhifədəki video faylları (mütləq ünvan, təkrarsız, keyfiyyətlisi əvvəl) və baxılmalı pleyer çərçivələri.
function linkler(html, base) {
  const s = String(html || "").slice(0, HTML_MAX).replace(/\\\//g, "/");
  const fayl = [...new Set((s.match(FAYL_RE) || []).map(u => abs(u, base)).filter(yaxsi))];
  const order = new Map(fayl.map((u, i) => [u, i]));
  fayl.sort((a, b) => keyfiyyet(b) - keyfiyyet(a) || order.get(a) - order.get(b));
  const cercive = [...new Set([...s.matchAll(/<iframe\b[^>]*?\bsrc\s*=\s*["']([^"']+)["']/gi)].map(m => abs(m[1], base))
    .filter(u => yaxsi(u) && PLEYER.test(u)))].slice(0, CERCIVE_MAX);
  return { fayl, cercive };
}

// Faylın imzası: MP4/MOV (4-cü baytdan «ftyp») və ya WebM/Matroska (EBML). HTML və xəta səhifəsi video kimi saxlanmasın.
const videodur = buf => buf.length >= 12 && (buf.subarray(4, 8).toString("latin1") === "ftyp" || buf.readUInt32BE(0) === 0x1A45DFA3);

async function oxu(url, f, referer = "") {
  const r = await f(url, { headers: { "user-agent": UA, ...(referer ? { referer } : {}) }, signal: AbortSignal.timeout(15000) }).catch(() => null);
  return r?.ok && r.text ? String(await r.text().catch(() => "")).slice(0, HTML_MAX) : "";
}
async function indir(url, file, f, referer) {
  const r = await f(url, { headers: { "user-agent": UA, referer }, signal: AbortSignal.timeout(180000) }).catch(() => null);
  if (!r?.ok) return `HTTP ${r?.status || "?"}`;
  const n = Number(r.headers?.get?.("content-length") || 0);
  if (n > MAX_BYTES) return `fayl böyükdür (${Math.round(n / 1e6)} MB)`;
  const buf = Buffer.from(await r.arrayBuffer());
  if (buf.length > MAX_BYTES) return `fayl böyükdür (${Math.round(buf.length / 1e6)} MB)`;
  if (buf.length < MIN_BYTES) return `fayl kiçikdir (${Math.round(buf.length / 1e3)} KB)`;
  if (!videodur(buf)) return "video faylı deyil";
  fs.writeFileSync(file, buf);
  return "";
}

// Yayım kadrı (film, serial, klip, treyler): başlıqdan tanınır (profil lent.yayim).
const yayim = (a, D = dil()) => Boolean(D.re.yayim && D.re.yayim.test(String(a?.title || "")));

// Xəbərin mənbə videosu: { file, url, sehife, kredit, bytes } və ya null. page: əsas mənbənin artıq oxunmuş səhifəsi.
async function menbeVideo(a, page, { env = process.env, fetch: f = globalThis.fetch, log = console.log, dir, D = dil() } = {}) {
  if (env.MENBE_VIDEO === "0" || !a?.sourceUrl) return null;
  if (env.MENBE_YAYIM !== "1" && yayim(a, D)) { log(`mənbə videosu: yayım kadrı ola bilər (film, serial, klip) — götürülmür: ${a.title}`); return null; }
  const alts = (Array.isArray(a.alts) ? a.alts : []).filter(x => x?.sourceUrl && x.source);
  const videolu = x => /video/i.test(String(x.title || ""));
  const sehifeler = [{ source: a.source, url: a.sourceUrl, html: page || "" }, ...alts.filter(videolu), ...alts.filter(x => !videolu(x))]
    .map(x => ({ source: x.source, url: x.url || x.sourceUrl, html: x.html || "" }))
    .filter((x, i, all) => x.source !== "8ULDUZ" && /^https:\/\//.test(x.url) && all.findIndex(y => y.url === x.url) === i).slice(0, SEHIFE_MAX);
  for (const s of sehifeler) {
    const html = s.html || await oxu(s.url, f);
    if (!html) continue;
    const l = linkler(html, s.url);
    // Saytın hər səhifəsində olan fayl (bəzək, reklam) xəbərin videosu deyil: baş səhifədə də varsa atılır. Səhifənin özündə
    // xəbərin faylı yoxdursa (və ya yalnız bəzəkdirsə) pleyer çərçivəsinə baxılır.
    let bas = null;
    const temiz = async list => {
      if (!list.length) return list;
      bas ??= (await oxu(new URL("/", s.url).href, f)).replace(/\\\//g, "/");
      return list.filter(u => !bas.includes(u) && !bas.includes(new URL(u).pathname));
    };
    let fayl = await temiz(l.fayl);
    for (const c of l.cercive) { if (fayl.length) break; fayl = await temiz(linkler(await oxu(c, f, s.url), c).fayl); }
    if (!fayl.length) continue;
    for (const url of fayl.slice(0, 2)) {
      const err = await indir(url, path.join(dir, FAYL), f, s.url).catch(e => String(e?.message || e).slice(0, 120));
      if (err) { log(`mənbə videosu: ${s.source} — ${err} (${url})`); continue; }
      const bytes = fs.statSync(path.join(dir, FAYL)).size;
      log(`mənbə videosu: ${s.source} — ${(bytes / 1e6).toFixed(1)} MB (${url})`);
      return { file: FAYL, url, sehife: s.url, kredit: s.source, bytes };
    }
  }
  log("mənbə videosu: mənbə səhifələrində götürülə bilən video faylı yoxdur (YouTube/Instagram pəncərəsi və ya video yoxdur)");
  return null;
}

module.exports = { menbeVideo, linkler, videodur, yayim, indir, FAYL, MAX_BYTES, MIN_BYTES, YAD, REKLAM };
