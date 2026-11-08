#!/usr/bin/env node
// «Telegram-da izlə» (sahib, 2026-11-07: «Fənərbağça haqqında xəbərlər oxucunun Telegram-ına gəlsin»).
// Saytda bölmə, komanda və rayon səhifəsindəki düymə t.me/<bot>?start=<açar> açır; oxucu «Başlat» basır və bot o mövzunun
// yeni xəbərlərini ona göndərir. Açar: b_<bölmə> (CATS), i_<idman mövzusu>, r_<rayon> — topics.cjs-in mövzuları, seçim app.js
// clubMatches() ilə (saytdakı düymə və mövzu səhifəsi ilə eyni). Xəbərlər saytın öz faylından (data/latest.json, news.json) oxunur.
// İş axını .github/workflows/izle.yml: xəbər pipeline-ından ayrıdır (lent düşməsin), repoya yazmır. Abunəçi siyahısı (chat id) yalnız
// GitHub Actions keşindədir (.izle/state.json), repoda və saytda görünmür. Telegram qaydası: bot yalnız «Başlat» basmış adama yazır.
"use strict";
const fs = require("node:fs"), path = require("node:path");
const { loadApp, topics } = require("./topics.cjs");

const SITE = "https://8ulduz.az/";
const MAX_TOPICS = 30, SEEN_KEEP = 6000, FEED_EVERY_MS = 60e3, FULL_EVERY_MS = 10 * 60e3, SAVE_EVERY_MS = 5 * 60e3;
const NO_SECTION = new Set(["sondeqiqe"]);
const NAMED = { amp: "&", lt: "<", gt: ">", quot: "\"", apos: "'", nbsp: " ", laquo: "«", raquo: "»", ndash: "–", mdash: "—", hellip: "…" };
const unent = s => String(s ?? "").replace(/&(#\d+|[a-z]+);/gi, (m, e) => e[0] === "#" ? String.fromCodePoint(+e.slice(1) || 32) : NAMED[e.toLowerCase()] ?? m);
const html = s => unent(s).replace(/<[^>]+>/g, "").replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").trim();

// Sərbəst mövzu (sahib 2026-11-07: «təhsil, Gəncə, hava, Rusiya–Ukrayna, İran–Amerika, İlham Əliyev, pensiya»):
// oxucu saytda axtarır və ya bota sadəcə söz yazır. Açar q_<sözün UTF-8 base64url-i> (Telegram start: yalnız A-Za-z0-9_-, 64 simvol).
// Seçim saytın axtarışı kimi: ə→e, ı→i və s.; hər əsas söz (kökü) başlıqda və ya xülasədə olmalıdır; «haqqında», «müharibəsi»,
// «münasibətləri» kimi ümumi sözlər tələb olunmur. Bir neçə yaxın ad bir sözü əvəz edir (ABŞ = Amerika, hava = proqnoz/yağış...).
const FOLD = { "ə": "e", "ı": "i", "ö": "o", "ü": "u", "ğ": "g", "ş": "s", "ç": "c" };
const fold = s => String(s || "").toLocaleLowerCase("az").replace(/[əıöüğşç]/g, ch => FOLD[ch]).normalize("NFKD").replace(/[\u0300-\u036f]/g, "");
const GENERIC = /^(salam|sagol|tesekkur|hello|hi$|ok$|haqq|bared|xeber|ve$|ile$|uzre|munasib|muharib|elaqe|veziyyet|son$|yeni)/;
const SAME = [
  ["ameri", "abs", "vasinqton", "trump", "tramp"], ["rusiy", "rf", "moskva", "kreml", "putin"], ["ukray", "kiyev", "zelenski"],
  ["iran", "tehran"], ["israil", "netanyahu"], ["turkiy", "ankara", "erdogan"], ["pensiy", "teqaud"],
  ["hava proqnoz", "hava serait", "havanin", "yagis", "yagint", "qar yag", "sulu qar", "kulek", "kuley", "saxta", "sinoptik", "meteoroloj", "temperatur", "dumanl", "bulud"],
];
const stem = w => w.length > 5 ? w.slice(0, Math.max(5, w.length - 3)) : w;
function kwTopic(key) {
  if (!/^q_[A-Za-z0-9_-]{2,62}$/.test(key)) return null;
  let label;
  try { label = Buffer.from(key.slice(2).replace(/-/g, "+").replace(/_/g, "/"), "base64").toString("utf8").replace(/\s+/g, " ").trim(); } catch { return null; }
  if (!label || label.length > 45 || /[\u0000-\u001f<>\ufffd]/.test(label)) return null;
  return kwFromText(label);
}
function kwFromText(label) {
  const words = fold(label).split(/[^\p{L}\p{N}]+/u).filter(w => w.length >= 2 || /\d/.test(w));
  const use = words.filter(w => !GENERIC.test(w)).slice(0, 4);
  if (!use.length) return null;
  const alts = use.map(w => { const s = stem(w), g = SAME.find(x => x.some(y => !y.includes(" ") && (s.startsWith(y) || s.length > 2 && y.startsWith(s)))); return g || [s]; });
  return { label, kw: true, match: a => { const t = " " + fold(`${a.title} ${a.summary || ""}`).replace(/[^\p{L}\p{N}]+/gu, " ") + " "; return alts.every(g => g.some(y => t.includes(" " + y))); } };
}
const keyOf = text => "q_" + Buffer.from(text, "utf8").toString("base64").replace(/\+/g, "-").replace(/\//g, "_").replace(/=+$/, "");
// Kataloqda yoxdursa sərbəst mövzu kimi yaradılır (bir dəfə).
function topicOf(cat, key) {
  if (!cat.has(key)) { const t = kwTopic(key); if (!t) return null; cat.set(key, t); }
  return cat.get(key);
}

// Mövzu kataloqu: açar -> { label, match(a) }.
function catalog(app) {
  const map = new Map();
  for (const c of app.CATS || []) if (!NO_SECTION.has(c.slug)) map.set(`b_${c.slug}`, { label: c.label, match: a => c.slug === "video" ? !!a.video : a.category === c.slug });
  for (const t of topics(app)) {
    const key = `${t.kind === "rayon" ? "r" : "i"}_${t.slug}`.replace(/[^a-z0-9_-]/g, "").slice(0, 60);
    if (map.has(key)) continue;
    map.set(key, { label: t.label, match: t.kind === "rayon" ? a => a.category !== "idman" && app.clubMatches(a, t.name) : a => a.category === "idman" && app.clubMatches(a, t.name) });
  }
  for (const [code, L] of Object.entries(DIGEST_LANGS)) map.set(`g_${code}`, { label: L.label, match: () => false });  // tək xəbər yox, gündə iki buraxılış
  return map;
}

// Oxucuya hansı xəbərlər gedir: idmanda hər dil (sahibin dil qaydası), qalanında yalnız Azərbaycan dili.
const wanted = (a, app) => a?.id && a.title && a.sourceUrl && !app.policyViolation(a) && (a.category === "idman" || (a.lang || "az") === "az");
// h: xəbərin saatı — lentdən çıxandan sonra sətir arxiv budağından açılır (arxiv.cjs).
const storyUrl = a => /^[0-9a-f]{16}$/.test(a.id) ? `${SITE}#/xeber/${a.id}?b=${encodeURIComponent(a.category || "")}&h=${require("./arxiv.cjs").hourOf(a.publishedAt)}` : a.sourceUrl;

// Günün 10 əsas xəbəri başqa dillərdə (sahib, 2026-11-08: «günün 10 əsas xəbəri teleqramda digər dillərə dəyişmir və yəqin ki
// həmin dillər üzrə işləmir»). Azərbaycan dilində icmal kanala gedir (updater.write_digest + social.cjs). İngilis/rus/türk oxucu
// saytdakı düymə ilə bota yazılır (start=g_<dil>) və 09:00/19:00 (Bakı) öz dilində günün 10 xəbərini alır. Seçim icmalın
// qaydasıdır (updater.digest_pick): ən çox mənbənin yazdığı, bərabərdə təzəsi; eyni başlıq və eyni hadisə bir dəfə; 5-dən azsa getmir.
const DIGEST_LANGS = {
  en: { label: "Top 10 stories of the day (English)", head: "Top 10 stories of the day", seher: "Morning edition", axsam: "Evening edition", more: "All news", stop: "🔕 Unsubscribe", stopped: "🔕 Unsubscribed",
    on: "✅ Done! Every day at 09:00 and 19:00 (Baku time) the top 10 stories of the day will come here in English.\n\nTo unsubscribe: /stop",
    had: "✅ You are already subscribed: the top 10 stories of the day, every day at 09:00 and 19:00 (Baku time).\n\nTo unsubscribe: /stop",
    off: "🔕 Unsubscribed. To subscribe again, tap «Top 10 stories of the day — on Telegram» on 8ulduz.az." },
  ru: { label: "10 главных новостей дня (русский)", head: "10 главных новостей дня", seher: "Утренний выпуск", axsam: "Вечерний выпуск", more: "Все новости", stop: "🔕 Отписаться", stopped: "🔕 Подписка отменена",
    on: "✅ Готово! Каждый день в 09:00 и 19:00 (по Баку) сюда будут приходить 10 главных новостей дня на русском.\n\nОтписаться: /stop",
    had: "✅ Вы уже подписаны: 10 главных новостей дня, каждый день в 09:00 и 19:00 (по Баку).\n\nОтписаться: /stop",
    off: "🔕 Подписка отменена. Чтобы подписаться снова, нажмите «10 главных новостей дня — в Telegram» на 8ulduz.az." },
  tr: { label: "Günün en önemli 10 haberi (Türkçe)", head: "Günün en önemli 10 haberi", seher: "Sabah baskısı", axsam: "Akşam baskısı", more: "Tüm haberler", stop: "🔕 Aboneliği bitir", stopped: "🔕 Abonelik bitti",
    on: "✅ Tamam! Her gün 09:00 ve 19:00'da (Bakü saati) günün en önemli 10 haberi Türkçe olarak buraya gelecek.\n\nAboneliği bitirmek için: /stop",
    had: "✅ Zaten abonesiniz: günün en önemli 10 haberi, her gün 09:00 ve 19:00'da (Bakü saati).\n\nAboneliği bitirmek için: /stop",
    off: "🔕 Abonelik bitti. Yeniden abone olmak için 8ulduz.az'da «Günün en önemli 10 haberi — Telegram'da» düğmesine basın." },
};
const DIGEST_EDITIONS = [["seher", 9, 24], ["axsam", 19, 12]], DIGEST_LATE_H = 6, DIGEST_MIN = 5, DIGEST_SIZE = 10, DIGEST_SAME_EVENT = 0.3, BAKU_MS = 4 * 3600e3;
const digestLang = key => /^g_([a-z]{2})$/.exec(key || "")?.[1];
// Vaxtı çatmış (ən gec 6 saat keçmiş) buraxılış: { slug, key, start, end } (ms) və ya null.
function dueEdition(now) {
  let best = null;
  for (const back of [0, 1]) {
    const day = new Date(now + BAKU_MS - back * 86400e3);
    for (const [key, hour, hours] of DIGEST_EDITIONS) {
      const end = Date.UTC(day.getUTCFullYear(), day.getUTCMonth(), day.getUTCDate(), hour) - BAKU_MS;
      if (now >= end && now - end < DIGEST_LATE_H * 3600e3 && (!best || end > best.end))
        best = { slug: `${new Date(end + BAKU_MS).toISOString().slice(0, 10)}-${key}`, key, start: end - hours * 3600e3, end };
    }
  }
  return best;
}
// Eyni hadisə: başlıq + xülasənin əvvəli üzrə 5 hərflik köklər, nadir söz ağır (updater._event_tokens ilə eyni üsul).
// Rəhbərin sözlərindən sitat («Президент Ильхам Алиев: …») hadisənin parçasıdır: rəhbər xəbəri seçiləndən sonra sitat başlıqları
// buraxılmır (updater._leader_quote, sahib 2026-11-06 «1 hadisədən yalnız 1 xəbər»).
const LEADER = { en: "president|head of state|ilham aliyev", ru: "президент|глава государства|ильхам алиев", tr: "cumhurbaşkanı|devlet başkanı|ilham aliyev" };
const leaderOf = code => LEADER[code] && { any: new RegExp(LEADER[code], "u"), quote: new RegExp(`^\\s*(?:${LEADER[code]})[^:]{0,25}:`, "u") };
const eventTokens = (a, code) => new Set((`${a.title || ""} ${String(a.summary || "").slice(0, 220)}`.toLocaleLowerCase(code).match(/\p{L}{4,}/gu) || []).map(w => w.slice(0, 5)));
function pickTop(articles, code, start, end, app) {
  const rows = (articles || []).filter(a => { const t = Date.parse(a?.publishedAt); return a?.id && String(a.title || "").trim() && (a.lang || "az") === code && t >= start && t < end && !app.policyViolation(a); });
  rows.sort((x, y) => (y.alts || []).length - (x.alts || []).length || String(y.publishedAt).localeCompare(String(x.publishedAt)));
  const toks = rows.map(a => eventTokens(a, code)), df = new Map();
  for (const t of toks) for (const w of t) df.set(w, (df.get(w) || 0) + 1);
  const idf = w => Math.log((rows.length + 1) / ((df.get(w) || 0) + 1));
  const norm = toks.map(t => Math.sqrt([...t].reduce((s, w) => s + idf(w) ** 2, 0)));
  const same = (i, j) => norm[i] && norm[j] && [...toks[i]].filter(w => toks[j].has(w)).reduce((s, w) => s + idf(w) ** 2, 0) / (norm[i] * norm[j]) >= DIGEST_SAME_EVENT;
  const out = [], picked = [], titles = new Set(), L = leaderOf(code), low = s => String(s || "").toLocaleLowerCase(code);
  const quote = a => L && (L.quote.test(low(a.title)) || /^\s*["“«„]/.test(low(a.title)) && L.any.test(low(String(a.summary || "").slice(0, 300))));
  let leader = false;
  for (let i = 0; i < rows.length && out.length < DIGEST_SIZE; i++) {
    const k = low(rows[i].title).replace(/[^\p{L}\p{N}]+/gu, "");
    if (titles.has(k) || (leader && quote(rows[i])) || picked.some(j => same(i, j))) continue;
    titles.add(k); picked.push(i); out.push(rows[i]);
    leader ||= !!L && L.any.test(low(`${rows[i].title} ${String(rows[i].summary || "").slice(0, 220)}`));
  }
  return out;
}
const attr = s => String(s).replace(/&/g, "&amp;").replace(/"/g, "&quot;");
// Bu dilə yazılmış oxuculara buraxılış (bir dəfə: state.dg[dil] = buraxılışın adı).
function digestMessages(state, code, ed, articles, app) {
  const L = DIGEST_LANGS[code], key = `g_${code}`, chats = Object.keys(state.subs).filter(id => state.subs[id].includes(key));
  if (!L || !ed || !chats.length || state.dg[code] === ed.slug) return [];
  state.dg[code] = ed.slug;
  const items = pickTop(articles, code, ed.start, ed.end, app);
  if (items.length < DIGEST_MIN) return [];
  const date = new Intl.DateTimeFormat(code, { day: "numeric", month: "long", timeZone: "Asia/Baku" }).format(new Date(ed.end));
  const text = `<b>📰 8ULDUZ · ${L.head}</b>\n${L[ed.key]} · ${date}\n\n` +
    items.map((a, i) => `${i + 1}. <a href="${attr(storyUrl(a))}">${html(a.title).slice(0, 180)}</a>${a.source ? ` — ${html(a.source)}` : ""}`).join("\n");
  const reply_markup = { inline_keyboard: [[{ text: `📖 ${L.more} · 8ULDUZ`, url: SITE }], [{ text: L.stop, callback_data: `stop:${key}` }]] };
  return chats.map(chat_id => ({ method: "sendMessage", chat_id, text, parse_mode: "HTML", reply_markup, link_preview_options: { is_disabled: true } }));
}

function newState(s) {
  s = s && typeof s === "object" ? s : {};
  return { offset: Number(s.offset) || 0, subs: s.subs && typeof s.subs === "object" ? s.subs : {}, seen: Array.isArray(s.seen) ? s.seen : null, dg: s.dg && typeof s.dg === "object" ? s.dg : {} };
}

// Telegram yeniləməsi -> cavablar (testlənir; şəbəkə yoxdur). state.subs: { chatId: [açar, ...] }.
function handle(state, u, cat) {
  const out = [], msg = u.message, cb = u.callback_query;
  const list = id => state.subs[id] || [];
  const listText = id => list(id).length ? `Siz izləyirsiniz:\n${list(id).map(k => `• ${cat.get(k)?.label || k}`).join("\n")}` : "Hələ heç nə izləmirsiniz. Mövzunu buraya yazın (məsələn: pensiya) və ya saytda «📩 Telegram-da izlə» düyməsinə basın: " + SITE;
  const stopKb = id => ({ inline_keyboard: list(id).map(k => [{ text: `🔕 ${cat.get(k)?.label || k} — dayandır`, callback_data: `stop:${k}` }]) });
  if (msg?.chat?.type === "private" && typeof msg.text === "string") {
    const id = String(msg.chat.id), text = msg.text.trim(), [cmd, arg = ""] = text.split(/\s+/, 2);
    let key = cmd === "/start" && arg && topicOf(cat, arg) ? arg : "";
    if (!key && !text.startsWith("/") && Buffer.byteLength(text) < 46 && kwFromText(text)) topicOf(cat, key = keyOf(text.replace(/\s+/g, " ")));
    const G = cmd === "/start" && DIGEST_LANGS[digestLang(arg)];
    if (G) {
      const had = list(id).includes(arg);
      if (!had) state.subs[id] = [...list(id), arg];
      out.push({ method: "sendMessage", chat_id: id, text: had ? G.had : G.on });
    } else if (key && cat.has(key)) {
      const arg = key;
      const had = list(id).includes(arg);
      if (!had && list(id).length >= MAX_TOPICS) out.push({ method: "sendMessage", chat_id: id, text: `Ən çox ${MAX_TOPICS} mövzu izləmək olar. Birini dayandırın: /izlediklerim` });
      else {
        if (!had) state.subs[id] = [...list(id), arg];
        out.push({ method: "sendMessage", chat_id: id, text: `✅ «${cat.get(arg).label}» ${had ? "artıq izlənir" : "izlənir"}. Yeni xəbər çıxan kimi buraya göndərəcəyəm.\n\nSiyahı və dayandırmaq: /izlediklerim` });
      }
    } else if (cmd === "/start" || cmd === "/help" || cmd === "/komek") {
      out.push({ method: "sendMessage", chat_id: id, text: arg === "movzu" ? "📩 Nəyi izləmək istəyirsiniz? Mövzunu bir-iki sözlə buraya yazın, məsələn: pensiya, Gəncə, hava, İran Amerika, İlham Əliyev.\n\nYeni xəbər çıxan kimi buraya göndərəcəyəm." : `Salam! Bu, 8ULDUZ xəbər botudur.\n\nİzləmək istədiyiniz mövzunu buraya yazın, məsələn: pensiya, Gəncə, hava, İran Amerika, İlham Əliyev. Və ya saytda (${SITE}) bölmə, komanda, rayon səhifəsində və axtarışda «📩 Telegram-da izlə» düyməsinə basın — yeni xəbərlər buraya gələcək.\n\n${listText(id)}`, ...(list(id).length ? { reply_markup: stopKb(id) } : {}) });
    } else if (/^\/(izlediklerim|izlədiklərim|list)$/i.test(cmd)) {
      out.push({ method: "sendMessage", chat_id: id, text: listText(id), ...(list(id).length ? { reply_markup: stopKb(id) } : {}) });
    } else if (/^\/(dayandir|dayandır|stop)$/i.test(cmd)) {
      const only = list(id).length && list(id).every(k => digestLang(k)) && DIGEST_LANGS[digestLang(list(id)[0])];  // yalnız başqa dildə buraxılış: cavab o dildə
      delete state.subs[id];
      out.push({ method: "sendMessage", chat_id: id, text: only ? only.off : "🔕 Bütün izləmələr dayandırıldı. Yenidən başlamaq üçün mövzunu buraya yazın və ya saytda «📩 Telegram-da izlə» düyməsinə basın." });
    }
  } else if (cb?.data?.startsWith("stop:") && cb.message?.chat?.id) {
    const id = String(cb.message.chat.id), key = cb.data.slice(5);
    state.subs[id] = list(id).filter(k => k !== key);
    if (!state.subs[id].length) delete state.subs[id];
    out.push({ method: "answerCallbackQuery", callback_query_id: cb.id, text: DIGEST_LANGS[digestLang(key)]?.stopped || `🔕 «${cat.get(key)?.label || key}» dayandırıldı` });
  }
  return out;
}

// Yeni xəbərlər -> göndərişlər. Hər oxucuya bir xəbər bir dəfə (bir neçə mövzusuna uyğun gəlsə də).
function deliveries(state, articles, cat, app) {
  const seen = new Set(state.seen || []), fresh = [];
  for (const a of articles) if (a?.id && !seen.has(a.id)) { seen.add(a.id); fresh.push(a); }
  state.seen = [...seen].slice(-SEEN_KEEP);
  const used = new Set(Object.values(state.subs).flat()), out = [];
  for (const a of fresh.filter(a => wanted(a, app)).sort((x, y) => String(x.publishedAt).localeCompare(String(y.publishedAt)))) {
    const keys = [...used].filter(k => { try { return topicOf(cat, k)?.match(a); } catch { return false; } });
    if (!keys.length) continue;
    for (const [chat, list] of Object.entries(state.subs)) {
      const key = list.find(k => keys.includes(k));
      if (!key) continue;
      const url = storyUrl(a), label = cat.get(key).label;
      const caption = `<b>${html(a.title).slice(0, 300)}</b>\n${html(a.source || "")} · ${html(label)}`;
      const reply_markup = { inline_keyboard: [[{ text: "📖 8ULDUZ-da oxu", url }], [{ text: `🔕 ${label} — dayandır`, callback_data: `stop:${key}` }]] };
      out.push(/^https:\/\//.test(a.imageUrl || "") ? { method: "sendPhoto", chat_id: chat, photo: a.imageUrl, caption, parse_mode: "HTML", reply_markup, _text: caption }
        : { method: "sendMessage", chat_id: chat, text: caption, parse_mode: "HTML", reply_markup, link_preview_options: { is_disabled: true } });
    }
  }
  return out;
}

async function call(token, m, fetchFn = fetch) {
  const { method, _text, ...body } = m;
  const r = await fetchFn(`https://api.telegram.org/bot${token}/${method}`, { method: "POST", headers: { "content-type": "application/json" }, body: JSON.stringify(body), signal: AbortSignal.timeout(method === "getUpdates" ? 40000 : 15000) });
  const d = await r.json().catch(() => ({}));
  if (!d.ok && method === "sendPhoto") return call(token, { method: "sendMessage", chat_id: body.chat_id, text: _text, parse_mode: "HTML", reply_markup: body.reply_markup, link_preview_options: { is_disabled: true } }, fetchFn);
  return d;
}

async function feed(full) {
  const get = async f => { try { const r = await fetch(`${SITE}data/${f}?t=${Date.now()}`, { signal: AbortSignal.timeout(20000) }); return r.ok ? (await r.json()).articles || [] : []; } catch { return []; } };
  const [latest, news] = await Promise.all([get("latest.json"), full ? get("news.json") : []]);
  return [...latest, ...news];
}

// Dilin tam lenti (data/news.<dil>.json): yalnız buraxılış vaxtı və o dilə yazılmış oxucu varsa.
async function feedLang(code) {
  try { const r = await fetch(`${SITE}data/news.${code}.json?t=${Date.now()}`, { signal: AbortSignal.timeout(20000) }); return r.ok ? (await r.json()).articles || [] : null; } catch { return null; }
}

function save(file, state) {
  fs.mkdirSync(path.dirname(file), { recursive: true });
  fs.writeFileSync(file + ".tmp", JSON.stringify(state));
  fs.renameSync(file + ".tmp", file);
}

async function main(root) {
  const token = process.env.TELEGRAM_BOT_TOKEN, file = process.env.IZLE_STATE || path.join(root, ".izle/state.json");
  const until = Date.now() + Number(process.env.IZLE_RUN_MS || 50 * 60e3);
  if (!token) { console.log("izlə: TELEGRAM_BOT_TOKEN yoxdur"); return; }
  let state;
  try { state = newState(JSON.parse(fs.readFileSync(file, "utf8"))); } catch { state = newState(); }
  const app = loadApp(root), cat = catalog(app);
  const me = await call(token, { method: "getMe" });
  console.log(`izlə: bot @${me?.result?.username || "?"}, ${cat.size} mövzu, ${Object.keys(state.subs).length} oxucu`);
  const hook = await call(token, { method: "getWebhookInfo" });
  if (hook?.result?.url) { console.log("izlə: botda webhook var, getUpdates işləməz — dayanıram"); return; }
  if (!state.seen) { state.seen = []; deliveries(state, await feed(true), cat, app); } // ilk dəfə: köhnə xəbərlər göndərilmir
  let lastFeed = 0, lastFull = Date.now(), lastSave = Date.now(), lastDigest = 0, sent = 0;
  while (Date.now() < until) {
    const up = await call(token, { method: "getUpdates", offset: state.offset, timeout: 25, allowed_updates: ["message", "callback_query"] }).catch(() => ({}));
    if (!up?.ok) await new Promise(r => setTimeout(r, 5000)); // şəbəkə və ya başqa getUpdates: dövr boş fırlanmasın
    for (const u of up?.result || []) {
      state.offset = u.update_id + 1;
      for (const m of handle(state, u, cat)) await call(token, m).catch(() => {});
    }
    if (Date.now() - lastFeed >= FEED_EVERY_MS) {
      const full = Date.now() - lastFull >= FULL_EVERY_MS;
      lastFeed = Date.now(); if (full) lastFull = lastFeed;
      for (const m of deliveries(state, await feed(full), cat, app)) {
        const d = await call(token, m).catch(() => ({}));
        if (d?.error_code === 403) delete state.subs[m.chat_id]; // oxucu botu bağlayıb
        else if (d?.ok) sent++;
        await new Promise(r => setTimeout(r, 60));
      }
    }
    if (Date.now() - lastDigest >= FEED_EVERY_MS) {
      lastDigest = Date.now();
      const ed = dueEdition(lastDigest), langs = new Set(Object.values(state.subs).flat().map(digestLang).filter(c => DIGEST_LANGS[c]));
      for (const code of ed ? [...langs].filter(c => state.dg[c] !== ed.slug) : []) {
        const articles = await feedLang(code);
        if (!articles) continue;   // lent alınmadı: növbəti dəqiqə yenidən
        for (const m of digestMessages(state, code, ed, articles, app)) {
          const d = await call(token, m).catch(() => ({}));
          if (d?.error_code === 403) delete state.subs[m.chat_id];
          else if (d?.ok) sent++;
          await new Promise(r => setTimeout(r, 60));
        }
        save(file, state); lastSave = Date.now();   // buraxılış iki dəfə getməsin (iş yarıda kəsilsə də)
      }
    }
    if (Date.now() - lastSave >= SAVE_EVERY_MS) { save(file, state); lastSave = Date.now(); }
  }
  save(file, state);
  console.log(`izlə: ${sent} xəbər göndərildi, ${Object.keys(state.subs).length} oxucu`);
}

module.exports = { catalog, handle, deliveries, newState, storyUrl, keyOf, kwTopic, MAX_TOPICS, dueEdition, pickTop, digestMessages, DIGEST_LANGS };
if (require.main === module) main(path.resolve(process.argv[2] || ".")).catch(e => { console.error("izlə:", e?.message || e); process.exitCode = 1; });
