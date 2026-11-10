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
//             (söndürmək: Variables INSTAGRAM=0). Yalnız şəkilli xəbər, 45 dəqiqədən bir.
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
function digests(index, now) {
  return (Array.isArray(index) ? index : []).filter(e => e && /^\d{4}-\d{2}-\d{2}-(seher|axsam)$/.test(e.slug || "") && Array.isArray(e.items) && e.items.length
    && now - e.at * 1000 < DIGEST_MAX_AGE_H * 3600e3 && now - e.at * 1000 > -60e3)
    .map(e => ({ id: `icmal-${e.slug}`, title: e.title, url: e.url, items: e.items, digest: true }));
}
const digestList = a => a.items.map((x, i) => `${i + 1}. ${cut(x.t, 140)}`).join("\n");
// Eyni başlıq başqa mənbədən yeni nömrə ilə gəlir: şəbəkəyə ikinci dəfə getməsin (5–6 noyabr Telegram-da təkrar).
const titleKey = a => "t:" + crypto.createHash("sha1").update(clean(a.title).toLocaleLowerCase("az").replace(/[^\p{L}\p{N}]+/gu, "")).digest("hex").slice(0, 16);
const clean = s => String(s ?? "").replace(/<[^>]+>/g, " ").replace(/\s+/g, " ").trim();

// Eyni hadisə başqa başlıqla (sahib, 2026-11-10: Facebook-da 3 dəfə «Prezident Türkiyəyə səfərə gedib / gəlib / xanımı ilə getdi»;
// sayt onları birləşdirməmişdi, xülasələri eyni idi). Şəbəkədə son TOPIC_H saatda paylaşılmış xəbərlə eyni mövzudursa getmir:
// xülasənin əvvəli eynidir, və ya (NEAR_H saat içində) başlıq+xülasə sözlərinin çoxu üst-üstə düşür, və ya iki Prezident xəbəri PREZ_H saat
// içində eyni ada/ölkəyə aiddir (Türkiyə, Ankara…). Söz kökü = ilk 5 hərf; ümumi sözlər və hər Prezident xəbərində olan adlar sayılmır.
const TOPIC_H = 24, NEAR_H = 4, PREZ_H = 3;
const STOP = new Set(("ilə üçün olan olub olaraq edib etdi edən edəcək edir gedib getdi gəlib gəldi bildirib deyib haqqında barədə xəbər " +
  "sonra daha yeni bütün bəzi onun bunu belə həmin artıq hələ qədər kimi görə üzrə dair bağlı keçirilib keçirildi video foto " +
  "videoçarx olunub olundu verib verdi alıb aldı").split(" "));
const GENERIC = new Set(["prezi", "ilham", "əliye", "mehri", "azərb", "respu", "birin"]);
const stems = s => [...new Set((clean(s).toLocaleLowerCase("az").match(/\p{L}{4,}/gu) || []).filter(w => !STOP.has(w))
  .map(w => w.slice(0, 5)).filter(w => !GENERIC.has(w)))];
function topicOf(a, at) {
  const sum = clean(a.summary).toLocaleLowerCase("az").replace(/[^\p{L}\p{N}]+/gu, "");
  return { at, prez: a.category === "prezident", key: sum.length >= 60 ? sum.slice(0, 80) : "",
    words: stems(`${a.title} ${clean(a.summary).slice(0, 300)}`), head: stems(a.title), names: stems((clean(a.title).match(/\p{Lu}\p{L}+/gu) || []).join(" ")) };
}
function sameTopic(x, y) {
  if (x.key && x.key === y.key) return true;
  if (Math.abs(x.at - y.at) >= NEAR_H * 3600) return false; // eyni hadisənin təkrarları saatlar içində gəlir; səhər Ərdoğanın səfəri ≠ axşam Əliyevin səfəri
  const shared = x.words.filter(w => y.words.includes(w)).length;
  // Xülasədəki ümumi cümlə (məs. «COP31 … sessiyası») tək başına bəs deyil: başlıqda da ortaq söz olmalıdır.
  if (shared >= 4 && shared / Math.min(x.words.length, y.words.length) >= 0.6 && x.head.some(w => y.head.includes(w))) return true;
  return x.prez && y.prez && Math.abs(x.at - y.at) < PREZ_H * 3600 && x.names.some(w => y.names.includes(w));
}

// Paylaşmağa layiq xəbərlər, ən vacibi birinci (mənbə sayı, sonra yenilik).
function candidates(articles, now, opt) {
  const out = [];
  for (const a of articles || []) {
    if (!/^[0-9a-f]{16}$/.test(String(a?.id || "")) || a.lang !== "az" || !clean(a.title)) continue;
    const at = Date.parse(a.publishedAt || "");
    if (!Number.isFinite(at) || now - at > opt.maxAgeH * 3600e3 || at - now > 10 * 60e3) continue;
    const score = a.category === "prezident" ? Math.max(sources(a), opt.minSources) : sources(a);
    if (score < opt.minSources) continue;
    out.push({ a, score, at });
  }
  return out.sort((x, y) => y.score - x.score || y.at - x.at).map(x => x.a);
}

function cut(s, n) {
  s = clean(s);
  return s.length <= n ? s : s.slice(0, n - 1).replace(/\s+\S*$/, "") + "…";
}
const html = s => s.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");

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
      const text = a.digest ? `<b>${html(a.title)}</b>\nGünün ən çox yazılan ${a.items.length} xəbəri:\n\n${html(digestList(a))}\n\n${url}`
        : `<b>${html(cut(a.title, 250))}</b>${sum && sum !== clean(a.title) ? `\n\n${html(sum)}` : ""}\n\n${url}`;
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
    list.push({ name: "instagram", token: env.FB_PAGE_TOKEN, ig: env.IG_USER_ID || "", gapMin: num(env.IG_MIN_GAP_MIN, 45), // gündə ≤32 (API həddi 50)
      wants: a => !a.digest && /^https:\/\/\S+$/.test(String(a.imageUrl || "")),
      async prepare(f, state, log) {
        const r = await f(`${root}${encodeURIComponent(env.FB_PAGE_ID)}?fields=instagram_business_account,access_token&access_token=${encodeURIComponent(env.FB_PAGE_TOKEN)}`, { signal: AbortSignal.timeout(15000) }).then(x => x.json()).catch(() => ({}));
        if (r?.access_token) this.token = r.access_token;
        this.ig ||= r?.instagram_business_account?.id || "";
        if (!this.ig) { log(`instagram: səhifəyə bağlı Instagram peşəkar hesabı yoxdur və ya açarda instagram_basic icazəsi yoxdur${r?.error?.message ? ` (${r.error.message})` : ""} — ötürülür`); return false; }
        return true;
      },
      caption(a) {
        const sum = cut(a.summary, 600);
        return `${cut(a.title, 300)}${sum && sum !== clean(a.title) ? `\n\n${sum}` : ""}\n\nƏtraflı: 8ulduz.az (keçid profildədir)\n\n#8ulduz #xəbərlər #Azərbaycan`;
      },
      // Konteyner → (hazır olanda) dərc. Cavab fetch Response kimidir: run eyni yoxlamanı edir.
      async post(a, f) {
        const call = (p, body) => f(`${root}${p}`, { method: "POST", headers: { "content-type": "application/x-www-form-urlencoded" },
          body: new URLSearchParams({ ...body, access_token: this.token }).toString(), signal: AbortSignal.timeout(30000) });
        const c = await call(`${this.ig}/media`, { image_url: a.imageUrl, caption: this.caption(a) });
        if (!c.ok) return c;
        const { id } = await c.json();
        for (let i = 0; ; i++) {
          const p = await call(`${this.ig}/media_publish`, { creation_id: id });
          if (p.ok || i >= 4) return p;
          const t = await p.text().catch(() => "");
          if (!/9007|not ready|not available/i.test(t)) return { ok: false, status: p.status, text: async () => t };
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
async function run({ articles, digestIndex = [], env = process.env, now = Date.now(), fetch: f = globalThis.fetch, state = {}, log = console.log }) {
  const opt = options(env), nets = networks(env), eds = digests(digestIndex, now), list = [...eds, ...candidates(articles, now, opt)];
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
      try {
        let r;
        if (net.post) r = await net.post(a, f);
        else { const [url, init] = net.request(a); r = await f(url, { ...init, signal: AbortSignal.timeout(20000) }); }
        if (r?.skip) { n--; log(`${net.name}: ötürülür (${r.skip}), növbəti dövrədə yenə yoxlanır — ${clean(a.title)}`); continue; }
        if (!r.ok) throw new Error(`HTTP ${r.status} ${String(await r.text().catch(() => "")).slice(0, 300)}`);
        done[a.id] = last[net.name] = Math.floor(now / 1000);
        if (!a.digest) { done[titleKey(a)] = done[a.id]; recent.push(topic); }
        result.posted.push([net.name, a.id]);
        log(`${net.name}: paylaşıldı — ${clean(a.title)}`);
      } catch (e) {
        const msg = hide(e);
        if (net.name === "telegram" && /chat not found|kicked|not a member|not enough rights|need administrator/i.test(msg)) delete state._telegram; // növbəti dövrə kanalı yenidən axtarır
        if (net.skipFailed) done[a.id] = Math.floor(now / 1000); // eyni xəbər hər dövrədə təkrar yoxlanmasın
        result.failed.push([net.name, a.id]);
        log(`${net.name}: alınmadı — ${msg}`);
        break; // şəbəkə imtina edirsə bu dövrədə ona daha yazmırıq
      }
    }
  }
  return result;
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
  const res = await run({ articles, digestIndex, now, state });
  fs.mkdirSync(path.dirname(stateFile), { recursive: true });
  fs.writeFileSync(stateFile, JSON.stringify(state));
  // Hamısı alınmayıbsa iş qırmızı olsun (sahib görsün); qismən uğur yaşıl.
  if (res.failed.length && !res.posted.length) process.exitCode = 1;
}

module.exports = { digests, candidates, networks, oauthHeader, readState, run, options, cut, topicOf, sameTopic };
if (require.main === module) main().catch(e => { console.error(String(e?.message || e)); process.exitCode = 1; });
