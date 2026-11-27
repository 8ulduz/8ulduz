// Saytın xəbərləri öz profillərimizdə (sahib, 2026-11-05: «bizim xəbərlərimiz profillərimizdə paylaşılsın»).
// .github/workflows/social.yml hər 20 dəqiqədən bir işə salır: node .github/scripts/social.cjs data/news.json
//
// Nə paylaşılır: son SOCIAL_MAX_AGE_H saatda (3) ən azı SOCIAL_MIN_SOURCES (4) mənbənin yazdığı azərbaycanca xəbər, ya da Prezident
// bölməsinin xəbəri; ən çox mənbəli birinci. Hər şəbəkəyə bir dövrədə SOCIAL_PER_RUN (1) post: saatda ən çox 3, spam olmasın.
// Keçid paylaşma səhifəsidir (https://www.8ulduz.az/<id>?h=<yymmddhh>, Cloudflare Worker .github/x-worker): og etiketləri önizləmədə
// başlıq və şəkli göstərir, oxucu saytda açılır. Worker naməlum xəbərə 302 verir: HEAD 200 = xəbər yayımdadır.
// Lent artıq redaksiya süzgəcindən keçib (qırmızı xətt 2: content_policy, müxalifət və dövlət qaydası), burada yalnız seçim var.
// Qırmızı xətt 1 və 3-ə toxunmur: xəbər axınından ayrı iş axınıdır, saytın koduna və yüklənməsinə heç nə əlavə etmir.
//
// Şəbəkə yalnız açarı GitHub sirrində olanda işləyir (yoxdursa ötürülür):
//   Telegram  TELEGRAM_BOT_TOKEN (bot kanala admin kimi əlavə olunur). Kanal TELEGRAM_CHAT-da (@ad və ya -100… nömrə) verilməyibsə,
//             botun admin edildiyi kanal botun öz yeniləmələrindən tapılır və yadda qalır (gizli kanalın açıq adı olmur).
//             t.me/sekkizulduz kanal deyil, şəxsi hesabdır: bot ora yaza bilmir.
//   Facebook  FB_PAGE_ID (8ulduz səhifəsi 1470250006171917, social.yml-də), FB_PAGE_TOKEN (Meta tətbiqi «8ulduz paylasma» 1000332509080909,
//             uzadılmış istifadəçi açarından alınmış müddətsiz səhifə açarı; yalnız SƏHİFƏ, şəxsi profilə API ilə yazmaq olmur)
//   X         X_API_KEY, X_API_SECRET, X_ACCESS_TOKEN, X_ACCESS_SECRET (developer.x.com, «Read and write» icazəsi)
//   LinkedIn  LINKEDIN_TOKEN (w_member_social), LINKEDIN_AUTHOR (urn:li:person:… və ya urn:li:organization:…)
//   Instagram Facebook açarları ilə; səhifəyə bağlı Instagram peşəkar hesabı və açarda instagram_content_publish icazəsi olanda işləyir
//             (söndürmək: Variables INSTAGRAM=0). Yalnız şəkilli xəbər, 120 dəqiqədən bir (IG_MIN_GAP_MIN), 24 saatda ≤100 (rəsmi hədd).
// Açarlar heç vaxt jurnala yazılmır. Paylaşılan nömrələr .social/posted.json-dadır (actions/cache), 3 gün saxlanır.
"use strict";
const fs = require("fs"), path = require("path"), crypto = require("crypto");

const SHARE = "https://www.8ulduz.az/";
const X_KEYS = ["X_API_KEY", "X_API_SECRET", "X_ACCESS_TOKEN", "X_ACCESS_SECRET"];
const KEEP_S = 3 * 86400;
const num = (v, d) => (Number.isFinite(Number(v)) && String(v ?? "").trim() !== "" ? Number(v) : d);

function options(env = process.env) {
  return {
    minSources: num(env.SOCIAL_MIN_SOURCES, 4),
    maxAgeH: num(env.SOCIAL_MAX_AGE_H, 3),
    perRun: num(env.SOCIAL_PER_RUN, 1),
    // Şəbəkəyə iki post arasında ən az bu qədər dəqiqə: iş həm cron, həm hər sayt yayımından sonra (~10 dəq) başlayır.
    minGapMin: num(env.SOCIAL_MIN_GAP_MIN, 18),
  };
}

const sources = a => 1 + (Array.isArray(a.alts) ? a.alts.length : 0);
// icmalın öz ünvanı var (icmal/<tarix>-seher/). h: xəbərin saatı — keçid günlər sonra arxiv budağından açılır (arxiv.cjs).
const shareUrl = a => a.url || `${SHARE}${a.id}${hourOf(a.publishedAt) ? `?h=${hourOf(a.publishedAt)}` : ""}`;
function hourOf(iso) { const m = String(iso || "").match(/^20(\d\d)-(\d\d)-(\d\d)T(\d\d)/); return m ? m.slice(1).join("") : ""; }
// Günün icmalı (updater.write_digest, 09:00 və 19:00 Bakı): siyahı icmal/index.json-dadır. 4 saatdan köhnə buraxılış göndərilmir.
const DIGEST_MAX_AGE_H = 4;
// Sahib, 2026-11-24: «icmalda olan xəbərə basanda saytdakı xəbərə keçid olsun». Buraxılışın ids-i items ilə eyni sıradadır
// (updater.write_digest): hər xəbərə öz paylaşma keçidi (u, shareUrl). h lentdəki saatdandır; lentdə yoxdursa h-siz — Worker
// saytın #/xeber/<id> səhifəsinə aparır, sayt xəbəri arxivdən tapır.
function digests(index, now, articles = []) {
  const at = new Map((Array.isArray(articles) ? articles : []).map(a => [String(a?.id), a?.publishedAt]));
  const link = id => (/^[0-9a-f]{16}$/.test(id) ? { u: shareUrl({ id, publishedAt: at.get(id) }) } : {});
  return (Array.isArray(index) ? index : []).filter(e => e && /^\d{4}-\d{2}-\d{2}-(seher|axsam)$/.test(e.slug || "") && Array.isArray(e.items) && e.items.length
    && now - e.at * 1000 < DIGEST_MAX_AGE_H * 3600e3 && now - e.at * 1000 > -60e3)
    .map(e => ({ id: `icmal-${e.slug}`, title: e.title, url: e.url, items: e.items.map((x, i) => ({ ...x, ...link(String(e.ids?.[i] || "")) })), digest: true }));
}
// Telegram: başlığın özü keçiddir (HTML). Facebook mətndə sözü keçid etmir, yalnız ünvanı: keçid başlığın altında, xəbərlər arasında boş sətir.
const digestList = a => a.items.map((x, i) => `${i + 1}. ${cut(x.t, 140)}${x.u ? `\n${x.u}` : ""}`).join(a.items.some(x => x.u) ? "\n\n" : "\n");
const digestHtml = a => a.items.map((x, i) => { const t = html(noLinks(cut(x.t, 140))); return `${i + 1}. ${x.u ? `<a href="${html(x.u)}">${t}</a>` : t}`; }).join("\n");
// Eyni başlıq başqa mənbədən yeni nömrə ilə gəlir: şəbəkəyə ikinci dəfə getməsin (5–6 noyabr Telegram-da təkrar).
const titleKey = a => "t:" + crypto.createHash("sha1").update(clean(a.title).toLocaleLowerCase("az").replace(/[^\p{L}\p{N}]+/gu, "")).digest("hex").slice(0, 16);
const clean = s => String(s ?? "").replace(/<[^>]+>/g, " ").replace(/\s+/g, " ").trim();

// Eyni hadisə başqa başlıqla (sahib, 2026-11-10: Facebook-da 3 dəfə «Prezident Türkiyəyə səfərə gedib / gəlib / xanımı ilə getdi»;
// sayt onları birləşdirməmişdi, xülasələri eyni idi). Şəbəkədə son TOPIC_H saatda paylaşılmış xəbərlə eyni mövzudursa getmir:
// xülasənin əvvəli eynidir, və ya (NEAR_H saat içində) başlıq+xülasə sözlərinin çoxu üst-üstə düşür, və ya iki Prezident xəbəri PREZ_H saat
// içində eyni ada/ölkəyə aiddir (Türkiyə, Ankara…). Söz kökü = ilk 5 hərf; ümumi sözlər və hər Prezident xəbərində olan adlar sayılmır.
const TOPIC_H = 24, NEAR_H = 4, PREZ_H = 3;
// Şəbəkə spam qorunması ilə məhdudlaşdıranda (Instagram 2207051, 2026-11-13) neçə saat ona yazılmır.
const PAUSE_H = 6;
const STOP = new Set(("ilə üçün olan olub olaraq edib etdi edən edəcək edir gedib getdi gəlib gəldi bildirib deyib haqqında barədə xəbər " +
  "sonra daha yeni bütün bəzi onun bunu belə həmin artıq hələ qədər kimi görə üzrə dair bağlı keçirilib keçirildi video foto " +
  "videoçarx olunub olundu verib verdi alıb aldı").split(" "));
const GENERIC = new Set(["prezi", "ilham", "əliye", "mehri", "azərb", "respu", "birin"]);
const stems = s => [...new Set((clean(s).toLocaleLowerCase("az").match(/\p{L}{4,}/gu) || []).filter(w => !STOP.has(w))
  .map(w => w.slice(0, 5)).filter(w => !GENERIC.has(w)))];
// Ad və soyad: başlıqda yanaşı iki böyük hərfli söz (hər biri 3+ hərf), kökləri ilə: «Fira Cəlilovanın» → «fira cəlil». Hər xəbərdə olan
// adlar (GENERIC: İlham Əliyev, Prezident…) sayılmır.
const cutler = s => [...new Set([...clean(s).matchAll(/(?<![\p{L}])(\p{Lu}\p{Ll}{2,})\s+(?=(\p{Lu}\p{Ll}{2,}))/gu)]
  .map(m => [m[1], m[2]].map(w => w.toLocaleLowerCase("az").slice(0, 5)))
  .filter(p => !p.some(w => GENERIC.has(w))).map(p => p.join(" ")))];
function topicOf(a, at) {
  const sum = clean(a.summary).toLocaleLowerCase("az").replace(/[^\p{L}\p{N}]+/gu, "");
  return { at, prez: a.category === "prezident", key: sum.length >= 60 ? sum.slice(0, 80) : "",
    words: stems(`${a.title} ${clean(a.summary).slice(0, 300)}`), head: stems(a.title), names: stems((clean(a.title).match(/\p{Lu}\p{L}+/gu) || []).join(" ")),
    cut: cutler(a.title) };
}
function sameTopic(x, y) {
  if (x.key && x.key === y.key) return true;
  if (Math.abs(x.at - y.at) >= NEAR_H * 3600) return false; // eyni hadisənin təkrarları saatlar içində gəlir; səhər Ərdoğanın səfəri ≠ axşam Əliyevin səfəri
  // Eyni adamın adı və soyadı iki başlıqda (2026-11-27: 05:20 «Fira Cəlilovanın bağ evində oğurluq» videosundan sonra 07:47-də kanal yolu
  // «Novxanıda aparıcı Fira Cəlilovanın bağ evinə basqın edilib»-i seçdi — ortaq kök 2 idi, söz qaydası tutmurdu). Köhnə siyahıda cut yoxdur.
  if ((x.cut || []).some(p => (y.cut || []).includes(p))) return true;
  const shared = x.words.filter(w => y.words.includes(w)).length;
  // Xülasədəki ümumi cümlə (məs. «COP31 … sessiyası») tək başına bəs deyil: başlıqda da ortaq söz olmalıdır.
  if (shared >= 4 && shared / Math.min(x.words.length, y.words.length) >= 0.6 && x.head.some(w => y.head.includes(w))) return true;
  return x.prez && y.prez && Math.abs(x.at - y.at) < PREZ_H * 3600 && x.names.some(w => y.names.includes(w));
}

// Paylaşmağa layiq xəbərlər, ən vacibi birinci (mənbə sayı, sonra yenilik). opt.lang: lentin dili (video dil profili, sosial-video.cjs); yoxdursa az.
// opt.weight(a): sıranın əmsalı (yalnız video: sosial-video.cjs cekisi — tamaşaçı marağı); mənbə həddi əmsalsız sayla yoxlanır.
function candidates(articles, now, opt) {
  const out = [], lang = opt.lang || "az";
  for (const a of articles || []) {
    if (!/^[0-9a-f]{16}$/.test(String(a?.id || "")) || a.lang !== lang || !clean(a.title)) continue;
    const at = Date.parse(a.publishedAt || "");
    if (!Number.isFinite(at) || now - at > opt.maxAgeH * 3600e3 || at - now > 10 * 60e3) continue;
    const base = a.category === "prezident" ? Math.max(sources(a), opt.minSources) : sources(a);
    if (base < opt.minSources) continue;
    out.push({ a, score: base * (opt.weight ? opt.weight(a) : 1), at });
  }
  return out.sort((x, y) => y.score - x.score || y.at - x.at).map(x => x.a);
}

function cut(s, n) {
  s = clean(s);
  return s.length <= n ? s : s.slice(0, n - 1).replace(/\s+\S*$/, "") + "…";
}
// Sahib, 2026-11-18: «başlığın altında mütləq xəbərin açıqlaması olsun — anlaşılan şərh», «izah uzun olsa yaxşıdır». Lentin xülasəsi
// qısadır (mənbədə ~220 simvolda kəsilir, çox xəbərdə boşdur), ona görə mənbə səhifəsi də oxunur. Namizədlər: xəbərin ilk abzasları,
// naşirin öz paylaşım təsviri (og:description, description), lentin xülasəsi; hamısından yalnız tam cümlələr (≤1200 simvol), ən uzunu
// seçilir. Saytın ümumi təsviri («operativ xəbərləri fasiləsiz çatdırır») götürülmür: təsvir ya başlıqla ortaq söz daşımalı, ya da
// səhifənin öz abzaslarında olmalıdır; abzaslar başlıqla ortaq sözü olan ilk abzasdan başlayır (menyu, reklam, oxşar xəbər düşür). Hər
// izah saytın qaydasından (app.js policyViolation) keçir. Heç biri yoxdursa xəbər Instagram-a getmir — izahsız post olmur.
const DESC_MAX = 1200;
const ENT = { quot: '"', amp: "&", apos: "'", lt: "<", gt: ">", nbsp: " ", laquo: "«", raquo: "»", ndash: "–", mdash: "—", hellip: "…",
  rsquo: "’", lsquo: "‘", rdquo: "”", ldquo: "“", uuml: "ü", Uuml: "Ü", ouml: "ö", Ouml: "Ö", ccedil: "ç", Ccedil: "Ç" };
const unent = s => String(s).replace(/&(#x[0-9a-f]+|#\d+|[a-z]+);/gi, (m, e) => {
  if (e[0] === "#") { const c = /^#x/i.test(e) ? parseInt(e.slice(2), 16) : parseInt(e.slice(1), 10); return c > 0 && c < 0x110000 ? String.fromCodePoint(c) : " "; }
  return ENT[e] ?? ENT[e.toLowerCase()] ?? m;
});
const AZ_LETTER = /[əğışçöüƏĞŞÇÖÜİ]/;
function pageDescriptions(page) {
  const out = [];
  for (const m of String(page).slice(0, 400000).matchAll(/<meta\b[^>]*>/gi)) {
    const tag = m[0], key = (tag.match(/\b(?:property|name)\s*=\s*["']?([^"'\s>]+)/i) || [])[1] || "";
    if (!/^(og:description|description|twitter:description)$/i.test(key)) continue;
    const c = (tag.match(/\bcontent\s*=\s*"([^"]*)"/i) || tag.match(/\bcontent\s*=\s*'([^']*)'/i) || [])[1];
    const d = c && clean(unent(unent(c)));
    if (d && !out.includes(d)) out.push(d);
  }
  return out;
}
// letter: mətnin dilini tanıdan hərflər (video dil profili «herf», sosial-video.cjs); yoxdursa azərbaycanca hərflər.
function pageParagraphs(page, letter = AZ_LETTER) {
  const body = String(page).slice(0, 600000).replace(/<(script|style|noscript)\b[\s\S]*?<\/\1>/gi, " ");
  return [...body.matchAll(/<p\b[^>]*>([\s\S]*?)<\/p>/gi)].map(m => clean(unent(unent(m[1].replace(/<[^>]+>/g, " ")))))
    .filter(t => t.length >= 40 && letter.test(t) && !/©|abunə ol|paylaş|bütün hüquqlar|istinad (mütləq|edilməlidir)/i.test(t));
}
function describe(a, page, policy = () => false, letter = AZ_LETTER) {
  const site = stems(a.source), head = stems(a.title).filter(w => !site.includes(w)), title = clean(a.title);   // «Sportinfo TV» ≠ saytın təsviri
  const near = d => !head.length || stems(d).some(w => head.includes(w));
  const ok = d => d && d !== title && letter.test(d) && !policy({ ...a, summary: d });
  const found = [];
  const own = sentences(a.summary, DESC_MAX);
  if (ok(own) && near(own)) found.push(own);
  if (page) {
    const paras = pageParagraphs(page, letter), text = paras.join(" ");
    for (const d of pageDescriptions(page)) {
      const t = sentences(d, DESC_MAX, true);
      if (ok(t) && (near(t) || text.includes(t.slice(0, 60)))) found.push(t);
    }
    const lead = paras.slice(0, 6).findIndex(near);
    if (lead >= 0) {
      const t = sentences(paras.slice(lead, lead + 8).join(" "), DESC_MAX, true);
      if (ok(t)) found.push(t);
    }
  }
  return found.reduce((x, y) => (y.length > x.length ? y : x), "");
}
const html = s => s.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
// Telegram mətndəki sayt adını («Modern.az xəbər verir ki…») özü keçidə çevirir və o, bizim keçiddən yuxarıda durur: oxucu mənbəyə
// gedirdi. Nöqtədən sonra boşluq olmayanda («edilib.Metbuat.az») keçid olmayan ünvana (edilib.metbuat.az) aparırdı (2026-11-14).
// Əvvəl cümlə sonuna boşluq, sonra sayt adının son nöqtəsindən sonra görünməz boşluq (U+200B): ad oxunur, keçid yaranmır.
const SITE_TLD = "az|com|ru|org|net|info|tv|ws|media|news|io|me|biz|tr|ge|eu|uk";
// Böyük-kiçik hərf burada fərqlidir (cümlə sonu: kiçik hərf, nöqtə, böyük hərf), ona görə sonluğun «Media», «AZ» yazılışları ayrıca sayılır.
const TLD_ANY_CASE = SITE_TLD.split("|").flatMap(t => [t, t[0].toUpperCase() + t.slice(1), t.toUpperCase()]).join("|");
const NAME_AFTER_DOT = new RegExp(`(\\p{Ll})\\.(?=\\p{Lu}[\\p{L}\\d-]*\\.(?:${TLD_ANY_CASE})(?![\\p{L}\\d]))`, "gu");
const SITE_NAME = new RegExp(`(?<![\\p{L}\\d@/.-])((?:[\\p{L}\\d-]+\\.)+)(${SITE_TLD})(?![\\p{L}\\d])`, "giu");
const noLinks = s => String(s).replace(NAME_AFTER_DOT, "$1. ").replace(SITE_NAME, "$1\u200B$2");
// Sahib, 2026-11-18: Instagram izahında cümlə yarımçıq qalmasın. Lentin xülasəsi mənbədə ~220 simvolda kəsilir («…bildirilib.İmtahan…»):
// kəsilibsə (sonda «…») yalnız tam cümlələr saxlanılır — sonu . ! ? (dırnaq/mötərizə ola bilər), ardınca boşluq, son və ya böyük hərf.
// Nöqtədən əvvəl tək böyük hərf (A.Əliyev), rəqəm arası (3.5) və sayt adı (Bizim.Media) cümlə sonu deyil. Tam cümlə yoxdursa (və ya
// çox qısadırsa) xülasə yazılmır, başlıq kifayətdir.
const SENT_END = new RegExp(`(?<!(?:^|[\\s.(])\\p{Lu})[.!?]["»”')]*(?=\\s|$|(?!(?:${TLD_ANY_CASE})(?![\\p{L}\\d]))\\p{Lu})`, "gu");
const SENT_GAP = new RegExp(`(?<=\\p{Ll}[.!?]["»”')]*)(?=(?!(?:${TLD_ANY_CASE})(?![\\p{L}\\d]))\\p{Lu})`, "gu");   // «edib.Sonra» → «edib. Sonra», «Milli.Az» olduğu kimi
function sentences(s, n, cutAlways = false) {
  s = clean(s);
  if (!cutAlways && !/(…|\.\.\.)$/.test(s) && s.length <= n) return s;   // mənbə kəsməyib: xülasə tamdır
  s = s.replace(/\s*(…|\.\.\.)$/, "");
  let end = 0;
  for (const m of s.matchAll(SENT_END)) { const e = m.index + m[0].length; if (e > n) break; end = e; }
  const out = s.slice(0, end).replace(SENT_GAP, " ").trim();
  return out.length >= 30 ? out : "";
}

// RFC 5849 (OAuth 1.0a), X API v2 üçün. JSON gövdəsi imzaya daxil deyil.
const pct = s => encodeURIComponent(s).replace(/[!'()*]/g, c => "%" + c.charCodeAt(0).toString(16).toUpperCase());
function oauthHeader(method, url, k, nonce = crypto.randomBytes(16).toString("hex"), ts = Math.floor(Date.now() / 1000)) {
  const p = { oauth_consumer_key: k.key, oauth_nonce: nonce, oauth_signature_method: "HMAC-SHA1", oauth_timestamp: String(ts), oauth_token: k.token, oauth_version: "1.0" };
  const params = Object.keys(p).sort().map(x => `${pct(x)}=${pct(p[x])}`).join("&");
  const base = `${method.toUpperCase()}&${pct(url)}&${pct(params)}`;
  p.oauth_signature = crypto.createHmac("sha1", `${pct(k.secret)}&${pct(k.tokenSecret)}`).update(base).digest("base64");
  return { base, header: "OAuth " + Object.keys(p).sort().map(x => `${pct(x)}="${pct(p[x])}"`).join(", ") };
}

// Hər şəbəkə: açar varsa { name, request(a) } — request fetch-ə veriləcək [url, init] qaytarır.
function networks(env = process.env) {
  const list = [];
  if (env.TELEGRAM_BOT_TOKEN) list.push({ name: "telegram", chat: env.TELEGRAM_CHAT || "",
    // Kanal verilməyibsə: bot kanala admin ediləndə Telegram bunu botun yeniləmələrinə yazır (24 saat saxlanır); tapılan kanal state-də qalır.
    async prepare(f, state, log) {
      if (this.chat) return true;
      if (state._telegram?.chat) { this.chat = state._telegram.chat; return true; }
      const r = await f(`https://api.telegram.org/bot${env.TELEGRAM_BOT_TOKEN}/getUpdates?allowed_updates=${encodeURIComponent('["my_chat_member","channel_post"]')}`, { signal: AbortSignal.timeout(15000) });
      const d = await r.json();
      if (!d.ok) throw new Error(`getUpdates: ${d.description || r.status}`);
      const chats = new Map();
      for (const u of d.result || []) {
        const m = u.my_chat_member, p = u.channel_post;
        if (m?.chat?.id && m.chat.type !== "private") {
          if (["administrator", "creator"].includes(m.new_chat_member?.status)) chats.set(m.chat.id, m.chat.title || ""); else chats.delete(m.chat.id);
        }
        if (p?.chat?.id) chats.set(p.chat.id, p.chat.title || "");
      }
      if (!chats.size) {
        // Hansı bot olduğunu deyirik (açıq ad, açar deyil): sahib kanala məhz bu botu əlavə etməlidir.
        const me = await f(`https://api.telegram.org/bot${env.TELEGRAM_BOT_TOKEN}/getMe`, { signal: AbortSignal.timeout(15000) }).then(x => x.json()).catch(() => ({}));
        log(`telegram: bot${me?.result?.username ? ` @${me.result.username}` : ""} heç bir kanalda admin deyil (və ya 24 saatdan əvvəl əlavə edilib): botu kanala yenidən admin edin və ya TELEGRAM_CHAT yazın`);
        return false;
      }
      const [id, title] = [...chats].pop();
      log(`telegram: kanal tapıldı — ${title} (${id})${chats.size > 1 ? `; digərləri: ${[...chats].slice(0, -1).map(([i, t]) => `${t} (${i})`).join(", ")}` : ""}`);
      this.chat = id;
      state._telegram = { chat: id, title };
      return true;
    },
    request(a) {
      const url = shareUrl(a), sum = cut(a.summary, 300);
      const text = a.digest ? `<b>${html(a.title)}</b>\nGünün ən çox yazılan ${a.items.length} xəbəri:\n\n${digestHtml(a)}\n\n${url}`
        : `<b>${html(noLinks(cut(a.title, 250)))}</b>${sum && sum !== clean(a.title) ? `\n\n${html(noLinks(sum))}` : ""}\n\n${url}`;
      return [`https://api.telegram.org/bot${env.TELEGRAM_BOT_TOKEN}/sendMessage`, { method: "POST", headers: { "content-type": "application/json" },
        body: JSON.stringify({ chat_id: this.chat, text, parse_mode: "HTML", link_preview_options: { url, prefer_large_media: true } }) }];
    } });
  if (env.FB_PAGE_ID && env.FB_PAGE_TOKEN) {
    const graphRoot = `https://graph.facebook.com/${env.FB_GRAPH_VERSION || "v27.0"}/`, graph = `${graphRoot}${encodeURIComponent(env.FB_PAGE_ID)}`;
    list.push({ name: "facebook", token: env.FB_PAGE_TOKEN,
      // Sirrə istifadəçi açarı da yazıla bilər (2026-11-05 belə oldu: #200 «requires ... with page token»): ondan səhifə açarı alınır.
      // Səhifə açarı ilə bu sorğu access_token qaytarmır, onda açar olduğu kimi qalır.
      async prepare(f, state, log) {
        const r = await f(`${graph}?fields=access_token&access_token=${encodeURIComponent(env.FB_PAGE_TOKEN)}`, { signal: AbortSignal.timeout(15000) }).then(x => x.json()).catch(() => ({}));
        if (r?.access_token && r.access_token !== env.FB_PAGE_TOKEN) { this.token = r.access_token; log("facebook: istifadəçi açarından səhifə açarı alındı (sirrə səhifə açarını yazmaq daha yaxşıdır)"); }
        return true;
      },
      // Sahib, 2026-11-10: «Facebook avto paylaşımlarda xəbərin şəkli olmur». Facebook keçidi ilk dəfə görəndə og:image-i arxada
      // emal edir: dərhal yaradılan postun kartı şəkilsiz qalır və elə qalır. Ona görə: yalnız şəkilli xəbər; əvvəl keçid oxudulur
      // (scrape=true), Facebook şəkli görməyibsə xəbər bu dövrədə ötürülür; görübsə emal üçün qısa gözləmə, sonra post.
      wants: a => a.digest || /^https:\/\/\S+$/.test(String(a.imageUrl || "")),
      async scrape(link, f) {
        const r = await f(graphRoot, { method: "POST", headers: { "content-type": "application/x-www-form-urlencoded" },
          body: new URLSearchParams({ id: link, scrape: "true", access_token: this.token }).toString(), signal: AbortSignal.timeout(20000) });
        return r?.json ? await r.json().catch(() => null) : null;
      },
      async post(a, f) {
        if (!a.digest) {
          const og = await this.scrape(shareUrl(a), f).catch(() => null);
          // Ötürmə yoxdur (2026-11-10, Sharing Debugger): wsrv.nl Facebook robotuna 403 verir — kart şəklini proksidən heç vaxt ala
          // bilmir; ötürsək Facebook-a heç nə getməzdi. Post həmişə gedir; şəkil paylaşma səhifəsinin öz ünvanından gələndə düzələcək.
          if (og && !og.error) await new Promise(ok => setTimeout(ok, num(env.FB_SCRAPE_WAIT_MS, 8000)));
        }
        const [url, init] = this.request(a);
        return f(url, { ...init, signal: AbortSignal.timeout(20000) });
      },
      request(a) { return [`${graph}/feed`, { method: "POST", headers: { "content-type": "application/x-www-form-urlencoded" },
        body: new URLSearchParams({ message: a.digest ? `${a.title}\nGünün ən çox yazılan ${a.items.length} xəbəri:\n\n${digestList(a)}` : cut(a.title, 500), link: shareUrl(a), access_token: this.token }).toString() }]; } });
  }
  if (X_KEYS.every(k => env[k])) list.push({ name: "x", request: a => {
    const url = "https://api.x.com/2/tweets";
    const { header } = oauthHeader("POST", url, { key: env.X_API_KEY, secret: env.X_API_SECRET, token: env.X_ACCESS_TOKEN, tokenSecret: env.X_ACCESS_SECRET });
    // Keçid X-də 23 simvol sayılır: başlıq 250-yə qədər, cəmi 280-dən az.
    return [url, { method: "POST", headers: { authorization: header, "content-type": "application/json" }, body: JSON.stringify({ text: `${cut(a.title, 250)}\n${shareUrl(a)}` }) }];
  } });
  if (env.LINKEDIN_TOKEN && env.LINKEDIN_AUTHOR) list.push({ name: "linkedin", request: a => ["https://api.linkedin.com/rest/posts", {
    method: "POST",
    headers: { authorization: `Bearer ${env.LINKEDIN_TOKEN}`, "content-type": "application/json", "linkedin-version": env.LINKEDIN_VERSION || "202510", "x-restli-protocol-version": "2.0.0" },
    body: JSON.stringify({ author: env.LINKEDIN_AUTHOR, commentary: cut(a.title, 700), visibility: "PUBLIC",
      distribution: { feedDistribution: "MAIN_FEED", targetEntities: [], thirdPartyDistributionChannels: [] },
      content: { article: { source: shareUrl(a), title: cut(a.title, 200) } }, lifecycleState: "PUBLISHED", isReshareDisabledByAuthor: false }) }] });
  // Instagram (sahib 2026-11-06): Facebook səhifəsinə bağlı Instagram peşəkar hesabına şəkilli post. Ayrı açar yoxdur: səhifə açarı
  // instagram_basic + instagram_content_publish icazəsi ilə alınmalıdır. Hesab bağlı deyilsə və ya icazə yoxdursa sakitcə ötürülür.
  // Instagram yalnız şəkilli post qəbul edir (JPEG, ictimai URL), keçid postda basılmır: mətnin sonunda «8ulduz.az» yazılır.
  if (env.FB_PAGE_ID && env.FB_PAGE_TOKEN && env.INSTAGRAM !== "0") {
    const root = `https://graph.facebook.com/${env.FB_GRAPH_VERSION || "v27.0"}/`;
    list.push({ name: "instagram", root, token: env.FB_PAGE_TOKEN, ig: env.IG_USER_ID || "", // Rəsmi hədd 24 saatda 100 API postudur
      // (content_publishing_limit): dərcdən əvvəl hesabın öz sayğacı soruşulur, dolubsa post getmir (skip: «24 saatlıq hədd dolub»).
      // Ara 120 dəqiqə (2026-11-26; əvvəl Facebook kimi 18 dəq, gündə ~50). Ölçü (docs/sosial-video.md «Rəqib təhlili»): 20–25 noyabrda
      // 243 şəkilli post 0 bəyənmə aldı (8 izləyici), 45 Reels — 37. Şəkilli post yalnız izləyicinin lentinə düşür, Reels isə
      // izləməyənlərə də göstərilir; nəticəsiz sıx avtomatik post spam siqnalıdır (2207051, 2026-11-13). Dəyişən: Variables IG_MIN_GAP_MIN.
      gapMin: num(env.IG_MIN_GAP_MIN, 120),
      wants: a => !a.digest && /^https:\/\/\S+$/.test(String(a.imageUrl || "")),
      async prepare(f, state, log) {
        const r = await f(`${root}${encodeURIComponent(env.FB_PAGE_ID)}?fields=instagram_business_account,access_token&access_token=${encodeURIComponent(env.FB_PAGE_TOKEN)}`, { signal: AbortSignal.timeout(15000) }).then(x => x.json()).catch(() => ({}));
        if (r?.access_token) this.token = r.access_token;
        this.ig ||= r?.instagram_business_account?.id || "";
        if (!this.ig) { log(`instagram: səhifəyə bağlı Instagram peşəkar hesabı yoxdur və ya açarda instagram_basic icazəsi yoxdur${r?.error?.message ? ` (${r.error.message})` : ""} — ötürülür`); return false; }
        return true;
      },
      caption(a, desc = describe(a, "")) {
        return `${cut(a.title, 300)}${desc ? `\n\n${desc}` : ""}\n\nƏtraflı: 8ulduz.az (keçid profildədir)\n\n#8ulduz #xəbərlər #Azərbaycan`;
      },
      // Konteyner → (hazır olanda) dərc. Cavab fetch Response kimidir: run eyni yoxlamanı edir.
      async post(a, f, policy) {
        // Rəsmi hədd (Instagram Graph API, content_publishing_limit): son 24 saatda API ilə dərc olunmuş postların sayı. Dolubsa bu
        // dövrədə Instagram-a heç nə getmir; cavab yoxdursa (sorğu alınmadı) post adi qaydada gedir — ara onsuz da gündə ≤12 saxlayır.
        // Sayğac dövrədə bir dəfə soruşulur (namizəd ötürüləndə növbəti üçün yenə sorğu yoxdur).
        const lim = (this.limit ??= await f(`${root}${encodeURIComponent(this.ig)}/content_publishing_limit?fields=quota_usage,config&access_token=${encodeURIComponent(this.token)}`, { signal: AbortSignal.timeout(15000) })
          .then(x => x.json()).catch(() => ({})))?.data?.[0];
        const used = Number(lim?.quota_usage), total = Number(lim?.config?.quota_total) || 100;
        if (lim?.quota_usage != null && Number.isFinite(used) && used >= total) return { skip: `24 saatlıq hədd dolub: ${used}/${total}` };
        const page = /^https?:\/\//.test(String(a.sourceUrl || "")) ? await f(a.sourceUrl, { headers: { "user-agent": "Mozilla/5.0 (compatible; 8ulduz-bot; +https://8ulduz.az/)" }, signal: AbortSignal.timeout(10000) })
          .then(r => (r?.ok && r.text ? r.text() : ""), () => "").catch(() => "") : "";
        const desc = describe(a, page, policy);
        if (!desc) return { skip: "izah tapılmadı", drop: true };
        const call = (p, body) => f(`${root}${p}`, { method: "POST", headers: { "content-type": "application/x-www-form-urlencoded" },
          body: new URLSearchParams({ ...body, access_token: this.token }).toString(), signal: AbortSignal.timeout(30000) });
        const t0 = Date.now();
        const c = await call(`${this.ig}/media`, { image_url: a.imageUrl, caption: this.caption(a, desc) });
        if (!c.ok) return c;
        const { id } = await c.json();
        for (let i = 0; ; i++) {
          const p = await call(`${this.ig}/media_publish`, { creation_id: id });
          if (p.ok) return p;
          const t = await p.text().catch(() => "");
          // 2026-11-13: dərc cavabı xəta («Application request limit reached», 2207051) olsa da post Instagram-da çıxırdı. Fasilə və
          // mövzu yadda qalmırdı: hər dövrə yenə göndərirdi — 6,5 saatda 36 post, eyni hadisə 5 dəfə. Belə cavab «bəlkə dərc olunub» sayılır.
          const busy = /9007|not ready|not available/i.test(t);
          if (!busy) {
            // 2026-11-17: 13 noyabrdan bəri HƏR dərc bu xəta ilə qayıdırdı, post isə çıxırdı (ig.json: 6 saatdan bir post). Xəta cavabı
            // fasilə qoyduğu üçün Instagram-a gündə 4 post gedirdi, Facebook-a ~53. Konteynerin öz statusu soruşulur: PUBLISHED isə
            // post çıxıb — adi uğur, fasilə yoxdur.
            // 2026-11-17 (2): ilk gün status «PUBLISHED» deyildi (dərc hələ bitməmişdi və ya sorğu cavabsız qaldı), post isə çıxmışdı.
            // Ona görə bir neçə dəfə yoxlanır və status bilinmirsə hesabın son postuna baxılır (eyni işdə /ig/ siyahısı bu sorğunu
            // problemsiz oxuyur): cəhddən sonra çıxmış və başlığı bu xəbərinki olan post — dərc olunub.
            // 2026-11-20 ölçüsü: 18 noyabr düzəlişindən sonra da Instagram-a gündə düz 4 post gedirdi (13:44, 19:46, 01:49, 08:00 UTC; Facebook-a
            // 49–52). Hər 6 saatlıq fasilənin ilk dərci post çıxarırdı (Instagram-ın öz vaxtı xəta jurnalından 3–9 s əvvəl), cavab isə 2207051
            // və konteyner statusu ERROR idi: status ERROR görəndə hesabın son postuna baxmadan «çıxmayıb» deyib 6 saat fasilə qoyurdu.
            // Status yalançı ola bilər: ERROR/EXPIRED-də də hesabın son postu yoxlanır; post yoxdursa — həqiqətən çıxmayıb (fasilə).
            const q = `access_token=${encodeURIComponent(this.token)}`, get = u => f(u, { signal: AbortSignal.timeout(15000) }).then(x => x.json()).catch(() => ({}));
            const head = s => clean(String(s || "").split("\n")[0]).replace(/…$/, "").slice(0, 60);
            let known = false; const seen = [];
            for (let k = 0; k < 3; k++) {
              if (k) await new Promise(res => setTimeout(res, num(env.IG_WAIT_MS, 3000)));
              const sr = await get(`${root}${encodeURIComponent(id)}?fields=status_code&${q}`), st = sr?.status_code || "";
              seen.push(st || sr?.error?.code || "?");
              if (st === "PUBLISHED") return { ok: true, status: 200, text: async () => "" };
              const m = (await get(`${root}${encodeURIComponent(this.ig)}/media?fields=timestamp,caption&limit=1&${q}`))?.data?.[0];
              if (m && Date.parse(m.timestamp) >= t0 - 60e3 && head(m.caption) === head(cut(a.title, 300))) return { ok: true, status: 200, text: async () => "" };
              if (st === "ERROR" || st === "EXPIRED") { known = true; break; }
            }
            // Status əvvəldə: jurnal xətanı 300 simvolda kəsir, status ondan sonra görünmürdü.
            return { ok: false, status: p.status, text: async () => `(status: ${seen.join(",")}) ${t}`, maybePosted: !known };
          }
          if (i >= 4) return { ok: false, status: p.status, text: async () => t, maybePosted: false };
          await new Promise(res => setTimeout(res, num(env.IG_WAIT_MS, 3000)));
        }
      },
      // Şəkli Instagram qəbul etmədi (format, ölçü, sayt bağlayır): bu xəbər ötürülür, növbəti dövrə başqasını götürür.
      skipFailed: true });
  }
  return list;
}

function readState(file, now) {
  let s = {};
  try { s = JSON.parse(fs.readFileSync(file, "utf8")) || {}; } catch {}
  const out = {};
  for (const [net, ids] of Object.entries(s)) {
    if (!ids || typeof ids !== "object") continue;
    if (net.startsWith("_")) { out[net] = ids; continue; } // şəbəkənin parametrləri (məs. tapılmış Telegram kanalı)
    out[net] = Object.fromEntries(Object.entries(ids).filter(([, t]) => now / 1000 - t < KEEP_S));
  }
  return out;
}

// Bir dövrə: hər şəbəkəyə ən vacib, hələ paylaşılmamış xəbər(lər). Paylaşma səhifəsi saytda yoxdursa (main hələ yayımlanmayıb) növbəti.
async function run({ articles, digestIndex = [], env = process.env, now = Date.now(), fetch: f = globalThis.fetch, state = {}, log = console.log, policy = () => false }) {
  const opt = options(env), nets = networks(env), eds = digests(digestIndex, now, articles), list = [...eds, ...candidates(articles, now, opt)];
  const result = { posted: [], failed: [] };
  // X açarları natamamdırsa şəbəkə sakitcə düşürdü (2026-11-10: «X-də xəbər yoxdur»): hansı sirrin çatmadığını jurnala yaz.
  const xMissing = X_KEYS.filter(k => !env[k]);
  if (xMissing.length) log(`x: sirr yoxdur — ${xMissing.join(", ")} (developer.x.com, «Read and write»; repo Settings → Secrets) — ötürülür`);
  if (!nets.length) {
    log(`Açar yoxdur, heç nə göndərilmir. Növbəti seçim: ${list[0] ? `${sources(list[0])} mənbə — ${clean(list[0].title)}` : "yoxdur"}`);
    return result;
  }
  const live = new Map();
  const pageLive = async a => {
    if (!live.has(a.id)) live.set(a.id, f(shareUrl(a), { method: "HEAD", redirect: "manual", signal: AbortSignal.timeout(15000) }).then(r => r.status === 200, () => false));
    return live.get(a.id);
  };
  // Açar URL-də və ya cavabda ola bilər: bütün açarlar (və alınmış səhifə açarı) jurnalda *** olur.
  const hide = s => [env.TELEGRAM_BOT_TOKEN, env.FB_PAGE_TOKEN, ...nets.map(n => n.token)].filter(x => x && x.length > 8)
    .reduce((m, k) => m.split(k).join("***"), String(s?.message || s));
  for (const net of nets) {
    if (net.prepare && !(await net.prepare(f, state, log).catch(e => { log(`${net.name}: hazırlıq alınmadı — ${hide(e)}`); return false; }))) continue;
    if (net.name === "instagram") result.ig = net;   // /ig/ səhifəsinin siyahısı üçün (main → igMedia)
    const until = state._pause?.[net.name] || 0;
    if (until > now / 1000) { log(`${net.name}: məhdudiyyətə görə fasilə, ${Math.ceil((until - now / 1000) / 60)} dəq qalıb`); continue; }
    const done = state[net.name] ||= {};
    const last = state._last ||= {};
    // Bir dəfəlik (iş axınında «fb_yenile»): www keçidi ilə artıq paylaşılmış xəbərlər Facebook-a yenidən oxudulur — kartı şəkilsiz
    // qalmış postlar şəkil alır. Köhnə /x/ səhifə keçidli postlar (2026-11-10 13:01 UTC-dən əvvəl) belə düzəlmir: o səhifələr yoxdur.
    if (net.scrape && env.FB_RESCRAPE === "1") {
      const since = Date.parse("2026-11-10T13:01:00Z") / 1000;
      const again = (articles || []).filter(a => done[a.id] >= since);
      let ok = 0;
      for (const a of again) { const og = await net.scrape(shareUrl(a), f).catch(() => null); if ((og?.image || []).length) ok++; }
      log(`${net.name}: ${again.length} paylaşılmış keçid yenidən oxudildi, ${ok}-də şəkil var`);
    }
    const ago = Math.round((now / 1000 - (last[net.name] || 0)) / 60);
    // İcmal saatında getməlidir: fasiləni gözləmir (xəbər postları gözləyir).
    const gap = net.gapMin ?? opt.minGapMin, mine = (early => (early ? eds : list).filter(a => !net.wants || net.wants(a)));
    const early = ago < gap;
    if (early && !mine(true).some(a => !done[a.id])) { log(`${net.name}: son post ${ago} dəq əvvəl, növbəti ${gap - ago} dəq sonra`); continue; }
    let n = 0;
    // Bu şəbəkədə son TOPIC_H saatda paylaşılmış xəbərlərin mövzuları (lentdə olanlar; vaxt — paylaşıldığı an).
    const sec = Math.floor(now / 1000), byId = new Map((articles || []).map(a => [a.id, a]));
    const recent = Object.entries(done).filter(([id, t]) => byId.has(id) && sec - t < TOPIC_H * 3600).map(([id]) => topicOf(byId.get(id), Date.parse(byId.get(id).publishedAt) / 1000 || sec));
    for (const a of mine(early)) {
      if (n >= opt.perRun) break;
      if (done[a.id] || (!a.digest && done[titleKey(a)])) continue;
      const topic = !a.digest && topicOf(a, Date.parse(a.publishedAt) / 1000 || sec);
      if (topic && recent.some(t => sameTopic(t, topic))) { done[a.id] = sec; log(`${net.name}: eyni mövzu artıq paylaşılıb, ötürülür — ${clean(a.title)}`); continue; }
      if (!(await pageLive(a))) continue;
      n++;
      let maybe = false;
      try {
        let r;
        if (net.post) r = await net.post(a, f, policy);
        else { const [url, init] = net.request(a); r = await f(url, { ...init, signal: AbortSignal.timeout(20000) }); }
        if (r?.skip) {
          n--;
          if (r.drop) { done[a.id] = sec; log(`${net.name}: ötürülür (${r.skip}) — ${clean(a.title)}`); continue; }   // hər dövrədə yenə oxunmasın
          log(`${net.name}: ötürülür (${r.skip}), növbəti dövrədə yenə yoxlanır — ${clean(a.title)}`); continue;
        }
        if (!r.ok && r.maybePosted) {
          maybe = true;   // xəta cavabı, amma post çıxmış ola bilər: fasilə, mövzu və /ig/ siyahısı yenə yazılır
          done[a.id] = last[net.name] = sec;
          if (!a.digest) { done[titleKey(a)] = sec; recent.push(topic); }
          if (net.name === "instagram") igRemember(state, a, sec);
        }
        if (!r.ok) throw new Error(`HTTP ${r.status} ${String(await r.text().catch(() => "")).slice(0, 300)}`);
        done[a.id] = last[net.name] = Math.floor(now / 1000);
        if (!a.digest) { done[titleKey(a)] = done[a.id]; recent.push(topic); }
        result.posted.push([net.name, a.id]);
        if (net.name === "instagram") igRemember(state, a, done[a.id]);
        log(`${net.name}: paylaşıldı — ${clean(a.title)}`);
      } catch (e) {
        const msg = hide(e);
        if (net.name === "telegram" && /chat not found|kicked|not a member|not enough rights|need administrator/i.test(msg)) delete state._telegram; // növbəti dövrə kanalı yenidən axtarır
        if (net.skipFailed) done[a.id] = Math.floor(now / 1000); // eyni xəbər hər dövrədə təkrar yoxlanmasın
        // Şəbəkə spam qorunması ilə məhdudlaşdırıb («request limit», Instagram 2207051): PAUSE_H saat bu şəbəkəyə yazılmır.
        // 2026-11-18: dərc cavabı bu xəta olub post çıxanda (maybePosted) fasilə yoxdur — 17 noyabr düzəlişindən sonra da status və son post
        // sorğuları postu tapmırdı, hər post 6 saat fasilə qoyurdu (Instagram-a gündə 4 post). Ara və mövzu yuxarıda yazılıb, spam yoxdur.
        // Fasilə yalnız post çıxmadığı bilinəndə: konteyner yaranmadı (ilk sorğu imtina etdi) və ya status ERROR/EXPIRED.
        if (!maybe && /request limit|2207051|limit how often|ограничиваем/i.test(msg)) { (state._pause ||= {})[net.name] = sec + PAUSE_H * 3600; log(`${net.name}: məhdudiyyət — ${PAUSE_H} saat fasilə`); }
        result.failed.push([net.name, a.id]);
        log(`${net.name}: alınmadı — ${msg}`);
        break; // şəbəkə imtina edirsə bu dövrədə ona daha yazmırıq
      }
    }
  }
  return result;
}

// 8ulduz.az/ig/ (sahib, 2026-11-13): Instagram postunda keçid basılmır, profildəki keçid bu səhifəyə aparır. Səhifədə Instagram-dakı
// postlar eyni sıra ilə və eyni şəkillə durur; oxucu postda gördüyü şəklə toxunub xəbəri açır. Sıra və tərkib Instagram-ın özündən
// (API: son 36 post); hər postun xəbəri paylaşanda yadda saxlanan siyahıdan (state._ig), olmasa başlığı lentdəki xəbərlə tutuşdurulur.
// Xəbər tapılmasa keçid saytın axtarışına (başlıqla) gedir. Şəkil: xəbərin öz şəkli (paylaşma Worker-i /i/<id>.jpg — Instagram-a
// göndərilən şəklin eynisi); xəbər tapılmasa Instagram-ın şəkli. Fayl ayrıca işdə «ig» budağına yazılır (social.yml), sayta toxunmur.
const IG_KEEP = 60, IG_SHOW = 36;
const igKey = s => clean(s).replace(/…$/, "").toLocaleLowerCase("az").replace(/[^\p{L}\p{N}]+/gu, "").slice(0, 60);
function igRemember(state, a, t) {
  const list = (state._ig ||= []).filter(x => x.id !== a.id);
  list.unshift({ id: a.id, title: clean(a.title), url: shareUrl(a), img: `${SHARE}i/${a.id}.jpg`, t });
  state._ig = list.slice(0, IG_KEEP);
}
// Tutuşdurma sırası (sonrakı üstündür): arxivdəki xəbərin alternativ başlıqları, arxiv, lentin alternativ başlıqları, lent,
// paylaşanda yadda saxlanan. Alternativ başlıq lazımdır: xəbərin əsas mənbəyi dəyişəndə başlığı da dəyişir (2026-11-13 ölçüsü:
// tapılmayan 22 postdan 11-i alternativ başlıqda və ya arxivdə idi). API cavab verməsə siyahı boşdur: budaqdakı köhnə siyahı qalır.
function igGrid(media, state = {}, articles = [], archive = []) {
  const known = new Map(), put = (t, a) => { if (a?.id && t) known.set(igKey(t), { id: a.id, title: clean(a.title), url: shareUrl(a), img: `${SHARE}i/${a.id}.jpg` }); };
  for (const list of [archive, articles]) {
    for (const a of list || []) for (const x of a?.alts || []) put(x.title, a);
    for (const a of list || []) put(a?.title, a);
  }
  for (const x of [...(state._ig || [])].reverse()) known.set(igKey(x.title), x);
  if (!Array.isArray(media) || !media.length) return [];
  return media.slice(0, IG_SHOW).map(m => {
    const title = clean(String(m.caption || "").split("\n")[0]).replace(/…$/, "");
    const hit = title && known.get(igKey(title));
    const t = Math.floor(Date.parse(m.timestamp) / 1000) || 0;
    if (hit) return { title: hit.title, url: hit.url, img: hit.img, t };
    // Video (Reels, sosial-video.cjs): media_url mp4 faylıdır, şəkil deyil — örtük kadrı (thumbnail_url) götürülür.
    const img = m.media_type === "VIDEO" ? m.thumbnail_url : m.media_url || m.thumbnail_url;
    return { title, url: title ? `https://8ulduz.az/#/axtar?q=${encodeURIComponent(title.slice(0, 120))}` : "https://8ulduz.az/", img: String(img || ""), t };
  }).filter(x => x.title);
}
async function igMedia(net, f) {
  if (!net?.ig || !net.root) return [];
  const u = `${net.root}${encodeURIComponent(net.ig)}/media?fields=caption,media_type,media_url,thumbnail_url,timestamp&limit=${IG_SHOW}&access_token=${encodeURIComponent(net.token)}`;
  const r = await f(u, { signal: AbortSignal.timeout(15000) }).then(x => x.json()).catch(() => ({}));
  return Array.isArray(r?.data) ? r.data : [];
}

async function main() {
  const feed = process.argv[2] || "data/news.json";
  const stateFile = process.env.SOCIAL_STATE || ".social/posted.json";
  const now = Date.now();
  // Qırmızı xətt 2, ikinci qapı (2026-11-07): lent artıq süzülüb, amma şəbəkəyə gedən hər xəbər saytın öz qaydasından da keçir.
  // Qayda faylı oxunmasa heç nə paylaşılmır (xəta ilə dayanır).
  const { loadApp } = require("./topics.cjs");
  const app = loadApp(path.resolve("."));
  const articles = (JSON.parse(fs.readFileSync(feed, "utf8")).articles || []).filter(a => !app.policyViolation(a));
  const state = readState(stateFile, now);
  let digestIndex = [];
  try { digestIndex = JSON.parse(fs.readFileSync("icmal/index.json", "utf8")); } catch {}
  const res = await run({ articles, digestIndex, now, state, policy: a => app.policyViolation(a) });
  // /ig/ səhifəsinin siyahısı (social.yml «ig» işi budağa yazır). Instagram qoşulu deyilsə və ya siyahı boşdursa fayl yazılmır.
  // Instagram-dan siyahı saatda bir dəfə və ya bu dövrədə post çıxanda soruşulur (Meta sorğu həddi; iş ~10 dəqiqədən bir işləyir).
  const lastAsk = state._igAsked || 0, posted = res.posted.some(x => x[0] === "instagram") || (state._last?.instagram || 0) > lastAsk;
  if (res.ig && (posted || now / 1000 - lastAsk >= 3600)) try {
    state._igAsked = Math.floor(now / 1000);
    let archive = [];
    try { archive = fs.readdirSync("data/arxiv").filter(f => f.endsWith(".json")).flatMap(f => JSON.parse(fs.readFileSync(path.join("data/arxiv", f), "utf8")).articles || []).filter(a => !app.policyViolation(a)); } catch {}
    const grid = igGrid(await igMedia(res.ig, globalThis.fetch), state, articles, archive);
    if (grid.length) { fs.mkdirSync("ig-out", { recursive: true }); fs.writeFileSync("ig-out/ig.json", JSON.stringify({ at: Math.floor(now / 1000), items: grid })); }
  } catch (e) { console.log(`ig: siyahı yazılmadı — ${String(e?.message || e).slice(0, 120)}`); }
  fs.mkdirSync(path.dirname(stateFile), { recursive: true });
  fs.writeFileSync(stateFile, JSON.stringify(state));
  // Hamısı alınmayıbsa iş qırmızı olsun (sahib görsün); qismən uğur yaşıl.
  if (res.failed.length && !res.posted.length) process.exitCode = 1;
}

module.exports = { digests, candidates, networks, oauthHeader, readState, run, options, cut, sentences, describe, pageDescriptions, pageParagraphs, topicOf, sameTopic, igGrid, igRemember, igMedia, noLinks,
  titleKey, shareUrl, clean, TOPIC_H };   // sosial-video.cjs eyni seçim və mövzu qaydasını işlədir
if (require.main === module) main().catch(e => { console.error(String(e?.message || e)); process.exitCode = 1; });
