// Meta açarının sağlamlığı və paylaşımların görünməsi (2026-11-23). İş axını: .github/workflows/meta-yoxla.yml
// (əl ilə, həftədə bir, PR-da). Yalnız oxuyur (GET), heç nə paylaşmır. Açar jurnala düşmür. Qurulum: docs/sosial-video.md
// «Meta açarı: yoxlama və yeniləmə».
//
//   1. Açar (debug_token): etibarlıdır, növü, tətbiq, müddətlər (expires_at, data_access_expires_at), icazələr.
//      Paylaşım üçün: pages_show_list, pages_read_engagement, pages_manage_posts, instagram_basic, instagram_content_publish.
//      Keçidli ilk şərh üçün: pages_manage_engagement və pages_read_user_content. 2026-11-23-də Meta videoya şərhi
//      «(#200) The permission(s) pages_read_user_content,pages_manage_engagement are not available» ilə qaytardı.
//   2. Səhifədə rol (/me/accounts tasks): paylaşım üçün CREATE_CONTENT, şərh üçün MODERATE (Meta-nın şərh sənədi).
//   3. Görünmə: son Facebook Reels və Instagram videolarının baxışı. Meta: «Any data generated while an app is in Development
//      mode, such as test posts, can only be seen by role users» (developers.facebook.com/docs/development/build-and-test/app-modes).
//      Facebook-da köhnə videoların hamısını ən çox ROLE_MAX nəfər görübsə, tətbiq Development rejimində ola bilər.
"use strict";

const REQUIRED = {
  pages_show_list: "səhifə siyahısı",
  pages_read_engagement: "səhifə açarı",
  pages_manage_posts: "Facebook paylaşımı",
  instagram_basic: "Instagram hesabı",
  instagram_content_publish: "Instagram paylaşımı",
};
const COMMENT = { pages_manage_engagement: "keçidli ilk şərh", pages_read_user_content: "videoya şərh" };
const STATS = { read_insights: "Facebook baxış statistikası", instagram_manage_insights: "Instagram baxış statistikası" };
const DAY = 86400e3;
const num = (v, d) => (Number.isFinite(Number(v)) && String(v ?? "").trim() !== "" ? Number(v) : d);

// Açar və ondan alınan səhifə açarı heç bir mətnə düşməsin.
const masker = keys => s => keys.filter(k => k && k.length > 8).reduce((m, k) => m.split(k).join("***"), String(s ?? ""));

function insightValue(res, name) {
  const m = (res?.data || []).find(x => x?.name === name);
  const v = m?.values?.[0]?.value ?? m?.total_value?.value;
  return Number.isFinite(Number(v)) ? Number(v) : null;
}

async function check({ env = process.env, f = fetch, now = Date.now() } = {}) {
  const T = env.FB_PAGE_TOKEN || "", P = String(env.FB_PAGE_ID || "");
  const out = { fail: [], warn: [], info: [], token: null, page: null, fb: [], ig: [], keys: [T] };
  if (!T) { out.fail.push("`FB_PAGE_TOKEN` sirri yoxdur"); return out; }
  if (!P) { out.fail.push("`FB_PAGE_ID` yoxdur"); return out; }
  const ver = env.FB_GRAPH_VERSION || "v27.0", root = `https://graph.facebook.com/${ver}/`;
  const n = Math.max(1, Math.min(25, num(env.META_YOXLA_N, 10)));
  const oldMs = num(env.META_YOXLA_OLD_H, 6) * 3600e3, roleMax = num(env.META_ROLE_MAX, 2);
  const get = async (p, q = {}, tok = T) => {
    const u = new URL(root + p);
    for (const [k, v] of Object.entries(q)) u.searchParams.set(k, v);
    u.searchParams.set("access_token", tok);
    try { const r = await f(u.toString(), { signal: AbortSignal.timeout(15000) }); return await r.json().catch(() => ({})); }
    catch (e) { return { error: { message: String(e?.message || e) } }; }
  };
  const err = r => (r?.error ? String(r.error.message || JSON.stringify(r.error)).slice(0, 200) : "");

  // 1. Açar
  const dbg = await get("debug_token", { input_token: T });
  const d = dbg?.data || {};
  const scopes = new Set(d.scopes || []);
  out.token = { valid: d.is_valid === true, type: d.type || "?", app: d.application || "", appId: d.app_id || "",
    expires: num(d.expires_at, 0), dataAccess: num(d.data_access_expires_at, 0), scopes: [...scopes].sort() };
  if (!out.token.valid) {
    out.fail.push(`açar etibarsızdır: ${err(dbg) || err(d) || "debug_token cavab vermədi"}`);
    return out;
  }
  const soon = t => t > 0 && t * 1000 - now < 14 * DAY;
  if (out.token.expires > 0 && out.token.expires * 1000 <= now) out.fail.push("açarın müddəti bitib");
  else if (soon(out.token.expires)) out.warn.push(`açarın müddəti ${new Date(out.token.expires * 1000).toISOString().slice(0, 10)} tarixində bitir`);
  if (out.token.dataAccess > 0 && out.token.dataAccess * 1000 <= now) out.fail.push("açarın məlumat girişi (data access) bitib: açarı yeniləyin");
  else if (soon(out.token.dataAccess)) out.warn.push(`açarın məlumat girişi ${new Date(out.token.dataAccess * 1000).toISOString().slice(0, 10)} tarixində bitir: açarı yeniləyin`);
  const miss = list => Object.keys(list).filter(s => !scopes.has(s));
  const mReq = miss(REQUIRED), mCom = miss(COMMENT), mSt = miss(STATS);
  if (mReq.length) out.fail.push(`paylaşım icazəsi yoxdur: ${mReq.map(s => `\`${s}\` (${REQUIRED[s]})`).join(", ")}`);
  if (mCom.length) out.warn.push(`keçidli şərh üçün icazə yoxdur: ${mCom.map(s => `\`${s}\``).join(", ")} — keçid yalnız post mətnindədir`);
  if (mSt.length) out.info.push(`statistika icazəsi yoxdur: ${mSt.map(s => `\`${s}\` (${STATS[s]})`).join(", ")}`);

  // 2. Səhifə: rol, səhifə açarı, Instagram hesabı
  let tasks = null;
  if (out.token.type === "USER") {
    const acc = await get("me/accounts", { fields: "id,name,tasks", limit: "100" });
    const mine = (acc?.data || []).find(x => String(x.id) === P);
    if (mine) tasks = mine.tasks || [];
    else out.warn.push(`açarın sahibi səhifəni (${P}) idarə edənlər siyahısında görünmür${err(acc) ? `: ${err(acc)}` : ""}`);
  }
  const pg = await get(encodeURIComponent(P), { fields: "id,name,link,followers_count,fan_count,access_token,instagram_business_account" });
  if (pg?.error) { out.fail.push(`səhifə oxunmadı: ${err(pg)}`); return out; }
  const PT = pg.access_token || T;
  out.keys.push(PT);
  out.page = { id: pg.id || P, name: pg.name || "", link: pg.link || "", followers: pg.followers_count ?? pg.fan_count ?? null, tasks };
  if (tasks) {
    if (!tasks.includes("CREATE_CONTENT")) out.fail.push("səhifədə paylaşım hüququ (CREATE_CONTENT) yoxdur");
    if (!tasks.includes("MODERATE")) out.warn.push("səhifədə şərh hüququ (MODERATE) yoxdur");
  }

  // 3. Facebook Reels: baxış (video_insights), bəyənmə və şərh sayı
  const reels = await get(`${encodeURIComponent(P)}/video_reels`, { fields: "id,created_time,description,permalink_url", limit: String(n) }, PT);
  if (reels?.error) out.warn.push(`Facebook Reels siyahısı oxunmadı: ${err(reels)}`);
  for (const r of (reels?.data || []).slice(0, n)) {
    const ins = await get(`${encodeURIComponent(r.id)}/video_insights`, { metric: "blue_reels_play_count,post_impressions_unique" }, PT);
    const soc = await get(encodeURIComponent(r.id), { fields: "likes.summary(true).limit(0),comments.summary(true).limit(0)" }, PT);
    out.fb.push({ id: r.id, time: r.created_time || "", title: String(r.description || "").split("\n")[0].slice(0, 80), link: r.permalink_url || "",
      plays: insightValue(ins, "blue_reels_play_count"), reach: insightValue(ins, "post_impressions_unique"),
      likes: soc?.likes?.summary?.total_count ?? null, comments: soc?.comments?.summary?.total_count ?? null, error: err(ins) });
  }

  // 4. Instagram: son videolar, baxış və əhatə (insights), bəyənmə
  const ig = pg?.instagram_business_account?.id || env.IG_USER_ID || "";
  if (ig) {
    const media = await get(`${encodeURIComponent(ig)}/media`, { fields: "id,caption,media_product_type,permalink,timestamp,like_count,comments_count", limit: String(n * 2) }, PT);
    if (media?.error) out.warn.push(`Instagram siyahısı oxunmadı: ${err(media)}`);
    for (const m of (media?.data || []).filter(x => x.media_product_type === "REELS").slice(0, n)) {
      let ins = await get(`${encodeURIComponent(m.id)}/insights`, { metric: "views,reach" }, PT);
      if (ins?.error) ins = await get(`${encodeURIComponent(m.id)}/insights`, { metric: "reach" }, PT);
      out.ig.push({ id: m.id, time: m.timestamp || "", title: String(m.caption || "").split("\n")[0].slice(0, 80), link: m.permalink || "",
        plays: insightValue(ins, "views"), reach: insightValue(ins, "reach"), likes: m.like_count ?? null, comments: m.comments_count ?? null, error: err(ins) });
    }
  }

  // 5. Görünmə: köhnə (oldMs-dən əvvəlki) videolarda ən böyük göstərici. Bəyənmə/şərh rol sahibinin özündən də ola bilər.
  const peak = list => {
    const old = list.filter(x => x.time && now - Date.parse(x.time) >= oldMs);
    const vals = old.flatMap(x => [x.plays, x.reach]).filter(v => v != null);
    return { old: old.length, measured: vals.length > 0, max: vals.length ? Math.max(...vals) : null };
  };
  const fbP = peak(out.fb), igP = peak(out.ig);
  out.visibility = { fb: fbP, ig: igP };
  if (fbP.old >= 2 && fbP.measured && fbP.max <= roleMax) {
    const ref = igP.measured && igP.max > roleMax ? ` (Instagram-da eyni videoları ${igP.max} nəfərə qədər görüb)` : "";
    out.fail.push(`Facebook-da son ${fbP.old} videonu ən çox ${fbP.max} nəfər görüb${ref}: Meta tətbiqi Development rejimindədirsə, paylaşımları yalnız tətbiqin rol sahibləri görür. Tətbiqi Live rejiminə keçirin (docs/sosial-video.md)`);
  } else if (fbP.old >= 2 && !fbP.measured) {
    out.info.push("Facebook baxış statistikası alınmadı: görünməni ölçmək olmadı");
  }
  return out;
}

const fmtN = v => (v == null ? "—" : String(v));
const day = t => (t ? String(t).replace("T", " ").slice(0, 16) : "—");

function report(out) {
  const L = [];
  L.push("## Meta açarı və görünmə", "");
  L.push(out.fail.length ? `**Problem: ${out.fail.length}**` : "**Problem yoxdur**", "");
  for (const s of out.fail) L.push(`- ❌ ${s}`);
  for (const s of out.warn) L.push(`- ⚠️ ${s}`);
  for (const s of out.info) L.push(`- ℹ️ ${s}`);
  if (out.token) {
    const t = out.token;
    L.push("", "### Açar", "", "| | |", "|---|---|",
      `| Növ | ${t.type} |`, `| Tətbiq | ${t.app || "—"} (${t.appId || "—"}) |`,
      `| Müddət | ${t.expires ? new Date(t.expires * 1000).toISOString().slice(0, 10) : "müddətsiz"} |`,
      `| Məlumat girişi | ${t.dataAccess ? new Date(t.dataAccess * 1000).toISOString().slice(0, 10) : "—"} |`,
      `| İcazələr | ${t.scopes.map(s => `\`${s}\``).join(", ") || "—"} |`);
  }
  if (out.page) {
    const p = out.page;
    L.push("", "### Səhifə", "", `${p.name || p.id}${p.followers != null ? `, ${p.followers} izləyici` : ""}${p.tasks ? `; hüquqlar: ${p.tasks.join(", ") || "—"}` : ""}`);
  }
  const table = (name, list) => {
    if (!list.length) return;
    L.push("", `### ${name}`, "", "| Vaxt (UTC) | Video | Baxış | Əhatə | Bəyənmə | Şərh |", "|---|---|---|---|---|---|");
    for (const x of list) {
      const title = (x.title || x.id).replace(/\|/g, "/");
      L.push(`| ${day(x.time)} | ${x.link ? `[${title}](${x.link})` : title} | ${fmtN(x.plays)} | ${fmtN(x.reach)} | ${fmtN(x.likes)} | ${fmtN(x.comments)} |`);
    }
    const e = list.find(x => x.error)?.error;
    if (e) L.push("", `Statistika xətası: ${e}`);
  };
  table("Facebook Reels", out.fb);
  table("Instagram Reels", out.ig);
  return masker(out.keys)(L.join("\n")) + "\n";
}

async function main() {
  const fs = require("fs");
  const out = await check();
  const text = report(out);
  const mask = masker(out.keys);
  // Səhifə açarı sirr deyil, GitHub onu özü gizlətmir: jurnalda görünməsin.
  if (process.env.GITHUB_ACTIONS) for (const k of out.keys.slice(1)) if (k && k.length > 8) console.log(`::add-mask::${k}`);
  for (const s of out.fail) console.log(mask(`::error::meta: ${s.replace(/`/g, "")}`));
  for (const s of out.warn) console.log(mask(`::warning::meta: ${s.replace(/`/g, "")}`));
  for (const s of out.info) console.log(mask(`meta: ${s.replace(/`/g, "")}`));
  console.log(text);
  if (process.env.GITHUB_STEP_SUMMARY) fs.appendFileSync(process.env.GITHUB_STEP_SUMMARY, text);
  if (out.fail.length) process.exitCode = 1;
}

module.exports = { check, report, masker, insightValue, REQUIRED, COMMENT, STATS };
if (require.main === module) main().catch(e => { console.error(`meta: ${String(e?.message || e).slice(0, 300)}`); process.exitCode = 1; });
