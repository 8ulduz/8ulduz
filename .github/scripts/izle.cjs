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
  return map;
}

// Oxucuya hansı xəbərlər gedir: idmanda hər dil (sahibin dil qaydası), qalanında yalnız Azərbaycan dili.
const wanted = (a, app) => a?.id && a.title && a.sourceUrl && !app.policyViolation(a) && (a.category === "idman" || (a.lang || "az") === "az");
const storyUrl = a => /^[0-9a-f]{16}$/.test(a.id) ? `${SITE}#/xeber/${a.id}?b=${encodeURIComponent(a.category || "")}` : a.sourceUrl;

function newState(s) {
  s = s && typeof s === "object" ? s : {};
  return { offset: Number(s.offset) || 0, subs: s.subs && typeof s.subs === "object" ? s.subs : {}, seen: Array.isArray(s.seen) ? s.seen : null };
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
    if (key && cat.has(key)) {
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
      delete state.subs[id];
      out.push({ method: "sendMessage", chat_id: id, text: "🔕 Bütün izləmələr dayandırıldı. Yenidən başlamaq üçün mövzunu buraya yazın və ya saytda «📩 Telegram-da izlə» düyməsinə basın." });
    }
  } else if (cb?.data?.startsWith("stop:") && cb.message?.chat?.id) {
    const id = String(cb.message.chat.id), key = cb.data.slice(5);
    state.subs[id] = list(id).filter(k => k !== key);
    if (!state.subs[id].length) delete state.subs[id];
    out.push({ method: "answerCallbackQuery", callback_query_id: cb.id, text: `🔕 «${cat.get(key)?.label || key}» dayandırıldı` });
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
  let lastFeed = 0, lastFull = Date.now(), lastSave = Date.now(), sent = 0;
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
    if (Date.now() - lastSave >= SAVE_EVERY_MS) { save(file, state); lastSave = Date.now(); }
  }
  save(file, state);
  console.log(`izlə: ${sent} xəbər göndərildi, ${Object.keys(state.subs).length} oxucu`);
}

module.exports = { catalog, handle, deliveries, newState, storyUrl, keyOf, kwTopic, MAX_TOPICS };
if (require.main === module) main(path.resolve(process.argv[2] || ".")).catch(e => { console.error("izlə:", e?.message || e); process.exitCode = 1; });
