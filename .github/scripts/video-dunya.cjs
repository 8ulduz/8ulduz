// Dünya videoları Azərbaycan dilində (sahib, 2026-11-26: «dünya saytlarından lazım olan tipli videoları götürüb tərcümə ilə azərbaycan
// dilində verilsin», «müəyyən etdiyin istiqamətlərə ən uyğun və keyfiyyətli dünya mənbələrinin tapılmasını, qoşulmasını, istifadəni
// təmin et. Say kifayətdən artıq olsun»). İstiqamətlər baku.ws_official təhlilindəndir (docs/sosial-video.md «Rəqib təhlili»): insan
// hekayəsi, hadisənin öz görüntüsü, məşhurlar və mədəniyyət, heyvanlar və təbiət, elm və kosmos, idman anı.
//
// Mənbələr: .github/video-dunya.json — hər biri yoxlanmış siyahı ünvanı (RSS, MRSS, Atom, video sayt xəritəsi, HTML siyahı, JSON)
// və birbaşa video faylı verən sayt. Yeni mənbə = fayla bir sətir, kod dəyişmir.
// Axın (sosial-video.cjs dunyaSec): növbə ilə bir neçə mənbənin təzə videoları oxunur → faylı tapılanlar namizəddir → Gemini bir
// sorğuda istiqamətə ən uyğununu seçir, Azərbaycan dilində başlıq və diktor mətni yazır (yalnız mənbədəki faktlar; rəqəm yoxlanır,
// saytın qaydası — qırmızı xətt 2 — həm mənbə mətninə, həm tərcüməyə tətbiq olunur) → fayl yüklənir (video-menbe.cjs) → montaj.
// Videoda mənbə yazılır («Mənbə: …», «Görüntü: …»), səs və altyazı bizimdir. YouTube/Instagram pəncərəsi, yayım kadrı götürülmür.
// Qayda (policy) məcburidir: sosial-video.cjs onu saytın qaydasından verir (app.policyViolation, assets/content-policy.js). Qaydasız
// çağırış xətadır — xarici mənbənin mətni yoxlanmadan videoya düşə bilməz.
"use strict";
const fs = require("fs"), path = require("path"), crypto = require("crypto");
const S = require("./social.cjs");
const VS = require("./video-ssenari.cjs");
const M = require("./video-menbe.cjs");
const { dil } = require("./video-dil.cjs");

const FAYL = path.join(__dirname, "..", "video-dunya.json");
const UA = "Mozilla/5.0 (compatible; 8ulduz-bot; +https://8ulduz.az/)";
const NOVLER = ["rss", "mrss", "atom", "sitemap", "html", "json"];
const MENBE_SAY = 6, MENBE_NAMIZED = 4, NAMIZED_MAX = 10, SEHIFE_SAY = 12, MAX_AGE_H = 96, SOURCE_MAX = 3500;
const clean = S.clean;
const num = (v, d) => (Number.isFinite(Number(v)) && String(v ?? "").trim() !== "" ? Number(v) : d);

// --- Mənbə siyahısı --------------------------------------------------------------------------------------------------------------
// { ad, dil, lent, nov, sec? (HTML siyahıda və sayt xəritəsində video səhifəsinin ünvan nümunəsi), json? (JSON-un sahələri),
//   istiqamet: [1..6], sertler (istifadə şərti, saytın özündə yazıldığı kimi), aktiv? (false — söndürülüb) }.
function kecerli(m) {
  if (!m || typeof m !== "object") return "obyekt deyil";
  if (!clean(m.ad) || m.ad.length > 40) return "ad";
  if (!/^[a-z]{2,3}$/.test(String(m.dil || ""))) return "dil";
  if (!/^https:\/\/[^\s]+$/.test(String(m.lent || ""))) return "lent https olmalıdır";
  if (!NOVLER.includes(m.nov)) return "növ";
  if (m.sec != null) { try { new RegExp(m.sec); } catch { return "sec nümunəsi"; } }
  if (m.nov === "html" && !m.sec) return "HTML siyahıda sec lazımdır";
  if (m.nov === "json" && !(m.json && clean(m.json.siyahi) && clean(m.json.kecid))) return "JSON sahələri (siyahi, kecid)";
  if (!Array.isArray(m.istiqamet) || !m.istiqamet.length || m.istiqamet.some(n => !(n >= 1 && n <= 6))) return "istiqamət";
  if (!clean(m.sertler)) return "şərtlər";
  return "";
}
function menbeler(file = FAYL) {
  const j = JSON.parse(fs.readFileSync(file, "utf8"));
  return (Array.isArray(j.menbeler) ? j.menbeler : []).filter(m => !kecerli(m) && m.aktiv !== false);
}

// --- Siyahının oxunması ----------------------------------------------------------------------------------------------------------
const unent = s => String(s ?? "").replace(/<!\[CDATA\[([\s\S]*?)\]\]>/g, "$1").replace(/&#(\d+);/g, (_, n) => String.fromCodePoint(Number(n)))
  .replace(/&#x([0-9a-f]+);/gi, (_, n) => String.fromCodePoint(parseInt(n, 16))).replace(/&lt;/g, "<").replace(/&gt;/g, ">").replace(/&quot;/g, '"').replace(/&apos;|&#39;/g, "'").replace(/&nbsp;/g, " ").replace(/&amp;/g, "&");
const metn = s => clean(unent(unent(s)).replace(/<[^>]+>/g, " "));
const teq = (b, ...names) => { for (const n of names) { const m = b.match(new RegExp(`<${n}\\b[^>]*>([\\s\\S]*?)</${n}>`, "i")); if (m && metn(m[1])) return metn(m[1]); } return ""; };
const atr = (b, name, a) => { const m = b.match(new RegExp(`<${name}\\b[^>]*?\\b${a}\\s*=\\s*["']([^"']+)["']`, "i")); return m ? unent(m[1]) : ""; };
const vaxt = s => { const t = Date.parse(String(s || "")); return Number.isFinite(t) ? t : 0; };
const idOf = link => crypto.createHash("sha1").update(String(link)).digest("hex").slice(0, 16);
const yol = (o, p) => String(p || "").split(".").filter(Boolean).reduce((x, k) => (x == null ? x : x[k]), o);

// Siyahıdan videolar: [{ id, title, desc, link, at, fayl? }] — təzəsi əvvəl. Faylı siyahıda olmayanınkı səhifədən tapılır (namizedler).
function oxuSiyahi(m, body, now = Date.now()) {
  const out = [], s = String(body || "");
  const add = x => { if (/^https:\/\//.test(x.link || "") && (!x.at || now - x.at < MAX_AGE_H * 3600e3)) out.push({ ...x, id: idOf(x.link) }); };
  const faylOf = b => M.linkler(b, m.lent).fayl[0] || "";
  if (m.nov === "json") {
    let j = null; try { j = JSON.parse(s); } catch {}
    for (const it of (Array.isArray(yol(j, m.json.siyahi)) ? yol(j, m.json.siyahi) : []).slice(0, 40)) {
      const link = clean(yol(it, m.json.kecid));
      add({ title: metn(yol(it, m.json.basliq)), desc: metn(yol(it, m.json.tesvir)), link, at: vaxt(yol(it, m.json.tarix)), fayl: clean(yol(it, m.json.fayl)) || "" });
    }
  } else if (m.nov === "html") {
    const re = new RegExp(m.sec), seen = new Set();
    for (const h of s.matchAll(/<a\b[^>]*?\bhref\s*=\s*["']([^"']+)["']/gi)) {
      let link = ""; try { link = new URL(unent(h[1]).split("#")[0], m.lent).href; } catch {}
      if (!link || seen.has(link) || !re.test(link)) continue;
      seen.add(link); add({ title: "", desc: "", link, at: 0 });
      if (seen.size >= 25) break;
    }
  } else if (m.nov === "sitemap") {
    const re = m.sec ? new RegExp(m.sec) : null;
    for (const b of s.split(/<url\b[^>]*>/i).slice(1)) {
      const link = teq(b, "loc");
      if (re && !re.test(link)) continue;
      add({ title: teq(b, "video:title", "news:title"), desc: teq(b, "video:description"), link, at: vaxt(teq(b, "video:publication_date", "news:publication_date", "lastmod")), fayl: faylOf(teq(b, "video:content_loc")) });
    }
  } else {
    const re = m.sec ? new RegExp(m.sec) : null;
    for (const b of s.split(/<(?:item|entry)\b[^>]*>/i).slice(1)) {
      const link = teq(b, "link") || atr(b, "link", "href") || teq(b, "guid", "id");
      if (re && !re.test(link)) continue;
      add({ title: teq(b, "title", "media:title"), desc: teq(b, "description", "summary", "media:description", "content:encoded", "content").slice(0, 1200), link,
        at: vaxt(teq(b, "pubDate", "published", "updated", "dc:date")), fayl: faylOf(b) });
    }
  }
  const seen = new Set();
  return out.filter(x => !seen.has(x.id) && seen.add(x.id)).sort((a, b) => b.at - a.at);
}

async function oxu(url, f, referer = "") {
  const r = await f(url, { headers: { "user-agent": UA, accept: "*/*", ...(referer ? { referer } : {}) }, signal: AbortSignal.timeout(20000) }).catch(() => null);
  return r?.ok && r.text ? String(await r.text().catch(() => "")).slice(0, 3e6) : "";
}
const sehifeMeta = (html, name) => metn((String(html).match(new RegExp(`<meta[^>]+(?:property|name)=["']${name}["'][^>]*content=["']([^"']*)["']`, "i"))
  || String(html).match(new RegExp(`<meta[^>]+content=["']([^"']*)["'][^>]*(?:property|name)=["']${name}["']`, "i")) || [])[1] || "");

// Mənbələrin növbəsi: ən çoxdan işlənməyən əvvəl (state.dm: ad → vaxt), eyni vaxtda siyahının sırası. Bir dövrədə MENBE_SAY mənbə.
function novbe(list, state) {
  const last = n => (state?.dm || {})[n] || 0;
  return list.map((m, i) => ({ m, i })).sort((a, b) => last(a.m.ad) - last(b.m.ad) || a.i - b.i).map(x => x.m);
}

// Namizədlər: faylı məlum, hələ işlənməmiş, saytın qaydasından keçən videolar (mətn mənbənin dilindədir).
async function namizedler({ list, state, now, fetch: f, policy, log, deps = {} }) {
  const read = deps.oxu || oxu, out = [];
  let sehife = 0;
  for (const m of novbe(list, state).slice(0, MENBE_SAY)) {
    if (out.length >= NAMIZED_MAX) break;
    const body = await read(m.lent, f);
    (state.dm ||= {})[m.ad] = Math.floor(now / 1000);
    if (!body) { log(`dünya videosu: ${m.ad} — siyahı oxunmadı`); continue; }
    let n = 0;
    for (const it of oxuSiyahi(m, body, now)) {
      if (n >= MENBE_NAMIZED || out.length >= NAMIZED_MAX) break;
      if (state.dv?.[it.id] || state.v?.[it.id] || state.skip?.[it.id]) continue;
      let { title, desc, fayl } = it, body2 = "";
      // Siyahıda çatmayan (fayl, başlıq, mətn) videonun səhifəsindən götürülür; səhifə oxunmasa siyahıdakı ilə davam edilir.
      const html = (!fayl || !title || desc.length < 200) && sehife < SEHIFE_SAY ? (sehife++, await read(it.link, f, m.lent)) : "";
      if (html) {
        title ||= sehifeMeta(html, "og:title") || metn((html.match(/<title[^>]*>([\s\S]*?)<\/title>/i) || [])[1]);
        if (desc.length < 200) desc = [desc, sehifeMeta(html, "og:description") || sehifeMeta(html, "description")].filter(Boolean).join(" ");
        body2 = S.pageParagraphs(html, /\p{L}/u).join(" ").slice(0, SOURCE_MAX);
        if (!fayl) {
          const l = M.linkler(html, it.link);
          fayl = l.fayl[0] || "";
          for (const c of l.cercive) { if (fayl) break; fayl = M.linkler(await read(c, f, it.link), c).fayl[0] || ""; }
        }
      }
      const a = { id: it.id, title: clean(title), summary: clean(desc).slice(0, 600), category: "dunya", lang: m.dil, source: m.ad, sourceUrl: it.link };
      if (!fayl || !a.title) { (state.skip ||= {})[it.id] = Math.floor(now / 1000); continue; }
      // Qırmızı xətt 2: xarici mənbədən Azərbaycan və rəhbərliyi haqqında, müxalifət mövzusunda video olmur — mənbənin öz mətni yoxlanır.
      if (policy(a) || policy({ ...a, summary: `${desc} ${body2}` })) { (state.skip ||= {})[it.id] = Math.floor(now / 1000); log(`dünya videosu: saytın qaydasından keçmir — ${m.ad}: ${a.title}`); continue; }
      if (M.yayim({ title: `${title} ${desc}` })) { (state.skip ||= {})[it.id] = Math.floor(now / 1000); continue; }
      out.push({ a, m, fayl, at: it.at, source: clean(`${title}. ${desc} ${body2}`).slice(0, SOURCE_MAX) });
      n++;
    }
  }
  return out;
}

// --- Seçim və tərcümə: bir Gemini sorğusu ----------------------------------------------------------------------------------------
const PROMPT = `Sən 8ulduz.az xəbər saytının video redaktorusan. Aşağıda dünya saytlarının {n} videosu var (başlıq və mətn mənbənin dilindədir).
Qısa şaquli video (Reels, Shorts) üçün ən uyğun BİR videonu seç və onun üçün {dil} başlıq və diktor mətni yaz.

Seçim. Tamaşaçının ən çox baxdığı istiqamətlər, vaciblik sırası ilə:
1) insan hekayəsi (qeyri-adi insan, yaxşılıq, ailə, sevindirən və ya təsirləndirən hadisə);
2) hadisənin öz görüntüsü (xilasetmə, qəza, yanğın, sel, qasırğa, təbii fəlakət, şahidin çəkdiyi görüntü);
3) məşhurlar, mədəniyyət, əyləncə;
4) heyvanlar, təbiət;
5) elm, kosmos, texnologiya;
6) idman anı (oyunun yayım kadrı yox: azarkeş, rekord, idmançının hərəkəti).
Uyğun DEYİL: sammit, görüş, bəyanat, mətbuat konfransı, siyasi çıxış, müharibənin gedişi, tok-şou, Azərbaycan və onun rəhbərliyi, Ermənistan–Azərbaycan mövzusu.
Heç biri uyğun deyilsə {"sec": 0} qaytar.

Mətn qaydaları:
- {dil} yaz. {yad}nida və sual işarəsi, keçid, emoji olmasın. {nisbi} yazma.
- 4–6 cümlə, 380–650 simvol. Birinci cümlə hadisənin özüdür (nə, harada). Yalnız seçdiyin videonun mətnindəki faktlar: heç nə əlavə etmə, şərh vermə.
- Rəqəmi mənbədəki kimi yaz: mənbədə rəqəmlə yazılıbsa rəqəmlə, sözlə yazılıbsa sözlə. Mənbədə olmayan rəqəm yazma.
- Xarici adları Azərbaycan dilində oxunduğu kimi yaz, inisial yazma.
- basliq: 40–90 simvol, hadisəni deyən sadə cümlə; sonda nöqtə olmasın, «video» sözü olmasın.
- etiket: 3 mövzu etiketi ({etiket_dili}, «#»-siz, boşluqsuz).

Yalnız JSON qaytar: {"sec": <videonun nömrəsi və ya 0>, "istiqamet": <1–6>, "basliq": "...", "text": "...", "etiket": ["...", "...", "..."]}

Videolar:
{videolar}`;
function promptOf(list, D = dil()) {
  const s = D.ssenari;
  const yad = s.yad_herf_adi ? `${s.yad_herf_adi[0].toLocaleUpperCase(D.locale)}${s.yad_herf_adi.slice(1)}, ` : "";
  return PROMPT.replace("{n}", String(list.length)).replace(/\{dil\}/g, s.dil).replace("{yad}", yad)
    .replace("{nisbi}", s.nisbi_gun_misal).replace("{etiket_dili}", s.etiket_dili)
    .replace("{videolar}", list.map((c, i) => `[${i + 1}] Mənbə: ${c.a.source} (${c.m.dil})\n${c.source}`).join("\n\n"));
}
const BASLIQ_MIN = 25, BASLIQ_MAX = 110;

// Seçilmiş video: { c (namizəd), title, text, etiket, istiqamet } | { yox: səbəb } | null (Gemini cavab vermir).
async function sec(list, { env = process.env, fetch: f = globalThis.fetch, policy = () => false, log = console.log } = {}) {
  if (!env.GEMINI_API_KEY) { log("dünya videosu: GEMINI_API_KEY yoxdur"); return null; }
  const raw = await VS.gemini(promptOf(list), env.GEMINI_API_KEY, f, log, env);
  if (raw == null) return null;
  let j = null;
  try { j = JSON.parse(String(raw).replace(/^```(?:json)?\s*|\s*```$/g, "")); } catch {}
  const i = Number(j?.sec), c = Number.isInteger(i) && i >= 1 ? list[i - 1] : null;
  if (!c) return { yox: i === 0 ? "istiqamətə uyğun video yoxdur" : "cavab JSON deyil" };
  const title = VS.dilLatin(clean(j.basliq)).replace(/[.!?…]+$/, ""), text = VS.dilLatin(clean(j.text));
  const az = { ...c.a, title, summary: text, lang: dil().lent.dil };
  const why = title.length < BASLIQ_MIN || title.length > BASLIQ_MAX ? `başlıq ${title.length} simvol` : dil().re.yadHerf?.test(title) ? "başlıqda yad hərf"
    : policy(az) ? "tərcümə saytın qaydasından keçmir" : VS.checkText(text, c.source, az, policy);
  if (why) return { yox: why, c };
  const etiket = VS.hashtags(j.etiket);
  return { c, title, text, istiqamet: Number(j.istiqamet) || 0, ...(etiket.length && !policy({ ...az, summary: etiket.join(" ") }) ? { etiket } : {}) };
}

// --- Tezlik ---------------------------------------------------------------------------------------------------------------------
// DUNYA_VIDEO=0 — söndürülüb; gündə ən çox DUNYA_GUNDE (8), arası DUNYA_ARA_MIN (90 dəq). state.dv: video → vaxt (state.dm: mənbə → son oxunma).
function options(env = process.env) {
  return { on: env.DUNYA_VIDEO !== "0", perDay: num(env.DUNYA_GUNDE, 8), gapMin: num(env.DUNYA_ARA_MIN, 90) };
}
function due(state, now, o) {
  if (!o.on) return "dünya videosu söndürülüb (DUNYA_VIDEO=0)";
  const sec = now / 1000, times = Object.values(state.dv || {});
  const day = times.filter(t => sec - t < 86400).length;
  if (day >= o.perDay) return `24 saatda ${day} dünya videosu (hədd ${o.perDay})`;
  const ago = Math.floor((sec - Math.max(0, ...times)) / 60);
  if (ago < o.gapMin) return `son dünya videosu ${ago} dəq əvvəl (ara ${o.gapMin} dəq)`;
  return "";
}

// Seçim + tərcümə + fayl → xeber.json-un girişi (sosial-video.cjs dunyaSec yazır) və ya null.
async function hazirla({ now = Date.now(), state, env = process.env, fetch: f = globalThis.fetch, policy, dir, log = console.log, file = FAYL, deps = {} }) {
  if (typeof policy !== "function") throw new Error("dünya videosu: saytın qaydası (policyViolation) verilməyib");
  const list = menbeler(file);
  if (!list.length) { log("dünya videosu: mənbə siyahısı boşdur"); return null; }
  const pool = await namizedler({ list, state, now, fetch: f, policy, log, deps });
  if (!pool.length) { log("dünya videosu: təzə, faylı açıq video tapılmadı"); return null; }
  const s = await (deps.sec || sec)(pool, { env, fetch: f, policy, log });
  const t = Math.floor(now / 1000);
  if (!s) { log("dünya videosu: Gemini cavab vermir — növbəti dövrədə"); return null; }
  if (s.yox) { if (s.c) (state.skip ||= {})[s.c.a.id] = t; log(`dünya videosu: ${s.yox}${s.c ? ` — ${s.c.a.source}: ${s.c.a.title}` : ""}`); return null; }
  const { c } = s;
  fs.mkdirSync(dir, { recursive: true });
  const err = await (deps.indir || M.indir)(c.fayl, path.join(dir, M.FAYL), f, c.a.sourceUrl).catch(e => String(e?.message || e).slice(0, 120));
  if (err) { (state.skip ||= {})[c.a.id] = t; log(`dünya videosu: fayl alınmadı (${err}) — ${c.a.source}: ${c.fayl}`); return null; }
  log(`dünya videosu: ${c.a.source} (${c.m.dil}) → ${s.title}`);
  return { id: c.a.id, tur: "dunya", kind: "dunya", title: s.title, summary: "", text: s.text, category: "dunya", source: c.a.source, sourceUrl: c.a.sourceUrl,
    publishedAt: new Date(c.at || now).toISOString(), alts: [], esli: { title: c.a.title, dil: c.m.dil }, istiqamet: s.istiqamet, ssenari: "gemini",
    ...(s.etiket ? { hashtags: s.etiket } : {}), menbeVideo: { file: M.FAYL, url: c.fayl, sehife: c.a.sourceUrl, kredit: c.a.source } };
}

module.exports = { FAYL, NOVLER, kecerli, menbeler, oxuSiyahi, novbe, namizedler, promptOf, sec, options, due, hazirla, idOf, MENBE_SAY, NAMIZED_MAX, MAX_AGE_H };
