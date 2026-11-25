// Video xəbərlər Facebook səhifəsində və Instagram-da (Reels) — sahib, 2026-11-22: «Facebook-da video xəbərlər verilsin…
// İnstagramda videolar verilsin. Videolarda başda 8ulduz.az yazılsın.» Araşdırma və seçimlər: docs/sosial-video.md.
// .github/workflows/sosial-video.yml 30 dəqiqədən bir işə salır:
//   node sosial-video.cjs sec <news.json> <qovluq>        vaxtıdırsa xəbər seçir: <qovluq>/xeber.json, GITHUB_OUTPUT «hazir=1»
//   node sosial-video.cjs numune <xəbər.json> <qovluq>    PR yoxlaması: verilən nümunə xəbər (paylaşılmır)
//   (arada video-xeber.cjs <qovluq>/xeber.json <qovluq>/video.mp4 videonu hazırlayır)
//   node sosial-video.cjs paylas <qovluq>                 videonu Facebook Reels və Instagram Reels-ə yükləyir
//
// Seçim social.cjs-dəkidir (son 3 saatda 4+ mənbəli azərbaycanca xəbər və ya Prezident bölməsi; eyni xəbər/başlıq/mövzu iki dəfə
// getmir) + izah (mənbə səhifəsinin tam cümlələri, describe()). İzahı tapılmayan xəbər video olmur. Tezlik: VIDEO_MIN_GAP_MIN
// (120, 10 dəqiqə dözümlə — due()) dəqiqədən bir, yalnız Bakı vaxtı ilə VIDEO_SAAT (8-23) saatlarında, 24 saatda ən çox VIDEO_GUNDE (8).
// Fayl ictimai ünvana qoyulmur: hər iki şəbəkəyə birbaşa yüklənir (rupload.facebook.com, «resumable upload»). Repoya video yazılmır.
//
// Açarlar (social.yml ilə eyni sirlər): FB_PAGE_ID, FB_PAGE_TOKEN. Açar yoxdursa iş sakitcə ötürülür. Açar jurnala düşmür.
//   Facebook  Səhifə Reels (POST /{page}/video_reels): pages_show_list, pages_read_engagement, pages_manage_posts; 24 saatda 30 Reels.
//             Postun mətnində saytdakı xəbərin keçidi; ilk şərhdə də (pages_manage_engagement varsa, yoxdursa ötürülür).
//   Instagram media_type=REELS, upload_type=resumable: instagram_basic, instagram_content_publish (+ Facebook Login for Business).
//             Keçid basılmır: mətnin sonunda «Ətraflı: 8ulduz.az», keçid profildədir. 24 saatda 100 post (şəkilli postlarla birlikdə).
// Qırmızı xətt 2: lent və izah saytın policyViolation qaydasından keçir; qayda faylı oxunmasa heç nə seçilmir.
// Qırmızı xətt 1 və 3: ayrıca iş axınıdır, main-ə və sayta heç nə yazmır.
// Gündəlik hava videosu (video-hava.cjs; sahib, 2026-11-23): ayrıca qayda ilə — Bakı vaxtı HAVA_VAXT-dan (20:45) sonrakı ilk pəncərədə,
// gündə bir dəfə (state.hava). Xəbər videosunun fasiləsinə (VIDEO_MIN_GAP_MIN) və gündəlik həddinə sayılmır (_last, v), mövzu siyahısına düşmür;
// həmin 30 dəqiqəlik pəncərədə xəbər videosu növbəti pəncərəyə qalır (bir pəncərədə bir iş, pipeline.sh video_loop).
// Maraqlı videolar (video-maraqli.cjs; sahib, 2026-11-24: «əsas odur onlar kimi sən də tap o cür maraqlı videolar»): Vikipediyanın faktları,
// Pixabay/Pexels görüntüsü, SARA səsi — xəbər videosu ilə növbələşir: son maraqlı videodan MARAQLI_ARA_MIN (60) dəqiqə keçibsə və gündə
// MARAQLI_GUNDE (10) dolmayıbsa, pəncərədə əvvəl maraqlı video; uyğun xəbər olmayan pəncərədə də (gündəlik həddə qədər). Ümumi fasiləyə
// və gündəlik həddə (VIDEO_MIN_GAP_MIN, VIDEO_GUNDE — Facebook-un 24 saatda 30 Reels həddi) sayılır, xəbər mövzularının siyahısına düşmür.
// Dil profili (2026-11-26, video-dil.cjs; VIDEO_DIL, boş — az): lentin dili və mənbə həddi (lent), izahın hərfləri (herf), paylaşım
// mətnləri (paylasim) və hava videosu (hava: yalnız profildə true olan dildə — hava mətnləri azərbaycancadır) profildəndir.
"use strict";
const fs = require("fs"), path = require("path");
const S = require("./social.cjs");
const { dil, fmt } = require("./video-dil.cjs");
const VS = require("./video-ssenari.cjs");
const VH = require("./video-hava.cjs");
const VA = require("./video-arxiv.cjs");
const VM = require("./video-maraqli.cjs");
const VX = require("./video-xeber.cjs");

const num = (v, d) => (Number.isFinite(Number(v)) && String(v ?? "").trim() !== "" ? Number(v) : d);
const KEEP_S = 3 * 86400;
const UA = "Mozilla/5.0 (compatible; 8ulduz-bot; +https://8ulduz.az/)";

function options(env = process.env) {
  const [from, to] = String(env.VIDEO_SAAT || "8-23").split("-").map(Number);
  return {
    // Mənbə həddinin ilkin dəyəri profildədir (lent.min_menbe; az: 4) — dəyişən (Variables) onu yenə üstələyir.
    minSources: num(env.VIDEO_MIN_SOURCES, num(env.SOCIAL_MIN_SOURCES, dil().lent.min_menbe)),
    maxAgeH: num(env.VIDEO_MAX_AGE_H, 3),
    // Sahib, 2026-11-24: «öz video sayımızı 10 dəfə artırmaq lazımdır». 10 qat (80) Facebook-un API həddini (24 saatda 30 Reels) keçir;
    // hər platforma öz həddinə qədər: 30 dəqiqədən bir (hər yoxlama pəncərəsi), gündə 30 (əvvəl 120 dəqiqə, 8).
    gapMin: num(env.VIDEO_MIN_GAP_MIN, 30),
    perDay: num(env.VIDEO_GUNDE, 30),
    from: Number.isInteger(from) ? from : 8, to: Number.isInteger(to) ? to : 23,
  };
}

function readState(file, now) {
  let s = {};
  try { s = JSON.parse(fs.readFileSync(file, "utf8")) || {}; } catch {}
  const sec = now / 1000, keep = o => Object.fromEntries(Object.entries(o && typeof o === "object" ? o : {}).filter(([, t]) => sec - t < KEEP_S));
  return { v: keep(s.v), skip: keep(s.skip), t: keep(s.t), facebook: keep(s.facebook), instagram: keep(s.instagram), klip: keep(s.klip), hava: keep(s.hava), m: keep(s.m),
    topics: (Array.isArray(s.topics) ? s.topics : []).filter(x => x && sec - (x.posted || 0) < S.TOPIC_H * 3600), _last: s._last || 0 };
}
const writeState = (file, state) => { fs.mkdirSync(path.dirname(file), { recursive: true }); fs.writeFileSync(file, JSON.stringify(state)); };

// Fasilə 30 dəqiqəlik pəncərələrdə yoxlanır (:17, :47), işin başlama vaxtı isə bir-iki dəqiqə oynayır: 120 dəqiqə (2026-11-24-dək) dörd pəncərə idi.
// Dözüm olmasa dördüncü pəncərə «119 dəq əvvəl, növbəti 1 dəq sonra» ilə ötürülür və ara 2,5 saat olur (2026-11-23, 23:47 videosu
// ümumiyyətlə getmədi). Dözüm fasilənin dörddə birindən çox deyil: VIDEO_MIN_GAP_MIN=30 qoyulsa ara 23 dəqiqədən az olmur.
const GAP_TOL_MIN = 10;
const gapTol = gapMin => Math.min(GAP_TOL_MIN, Math.floor(gapMin / 4));

// Vaxtıdırmı? Boş sətir — bəli; yoxsa səbəb.
function due(state, now, opt) {
  const sec = Math.floor(now / 1000), h = new Date(now + 4 * 3600e3).getUTCHours();   // Bakı vaxtı (UTC+4)
  if (h < opt.from || h > opt.to) return `Bakı vaxtı ${h}:00 — video ${opt.from}:00–${opt.to}:59 arası gedir`;
  const ago = Math.round((sec - (state._last || 0)) / 60), gap = opt.gapMin - gapTol(opt.gapMin);
  if (ago < gap) return `son video ${ago} dəq əvvəl, növbəti ${gap - ago} dəq sonra`;
  const day = Object.values(state.v || {}).filter(t => sec - t < 86400).length;
  if (day >= opt.perDay) return `24 saatda ${day} video (hədd ${opt.perDay})`;
  return "";
}

// --- Hava videosu: vaxt qaydası ---------------------------------------------------------------------------------------------
// Bakı vaxtı (UTC+4, yay vaxtı yoxdur): gün («2026-11-24») və gecə yarısından dəqiqə.
const bakuClock = now => { const d = new Date(now + 4 * 3600e3); return { day: d.toISOString().slice(0, 10), min: d.getUTCHours() * 60 + d.getUTCMinutes(), h: d.getUTCHours() }; };
const hhmm = m => `${String(Math.floor(m / 60)).padStart(2, "0")}:${String(m % 60).padStart(2, "0")}`;
// HAVA_VAXT (20:45): sabahkı proqnoz axşam — ICON modelinin günorta buraxılışı (12 UTC) Open-Meteo-da ~20:25-də olur, adamlar sabahı
// axşam planlayır; MHX-in proqnozu günortadır, rəqiblərin videosu ~17:30 (docs/sosial-video.md «Hava videosu»). Pəncərə xəbər videosunun
// saatlarının sonuna qədərdir (VIDEO_SAAT, 23:59): bir dövrə alınmasa növbəti 30 dəqiqədə yenidən.
function havaOptions(env = process.env) {
  const [h, m] = String(env.HAVA_VAXT || "20:45").split(":").map(Number);
  const ok = Number.isInteger(h) && h >= 0 && h < 24 && Number.isInteger(m) && m >= 0 && m < 60;
  return { on: env.HAVA_VIDEO !== "0", from: ok ? h * 60 + m : 20 * 60 + 45, to: options(env).to };
}
function havaDue(state, now, ho) {
  if (!ho.on) return "hava videosu söndürülüb (HAVA_VIDEO=0)";
  const c = bakuClock(now);
  if (c.min < ho.from || c.h > ho.to) return `hava videosu Bakı vaxtı ${hhmm(ho.from)}–${ho.to}:59 arası`;
  if (state.hava?.[c.day]) return "bu günün hava videosu hazırlanıb";
  return "";
}
// Maraqlı video: söndürmə (MARAQLI_VIDEO=0), gündəlik hədd və öz fasiləsi. state.m: mövzu → vaxt (3 gün saxlanır: mövzu təkrarlanmır).
function maraqliOptions(env = process.env) {
  return { on: env.MARAQLI_VIDEO !== "0", perDay: num(env.MARAQLI_GUNDE, 10), gapMin: num(env.MARAQLI_ARA_MIN, 60) };
}
const maraqliSay = (state, now) => Object.values(state.m || {}).filter(t => now / 1000 - t < 86400).length;
// "" — vaxtıdır; yoxsa səbəb. fill: uyğun xəbər yoxdur — öz fasiləsi gözlənmir, yalnız gündəlik hədd.
function maraqliDue(state, now, mo, fill = false) {
  if (!mo.on) return "maraqlı video söndürülüb (MARAQLI_VIDEO=0)";
  const day = maraqliSay(state, now);
  if (day >= mo.perDay) return `24 saatda ${day} maraqlı video (hədd ${mo.perDay})`;
  const last = Math.max(0, ...Object.values(state.m || {})), ago = Math.floor((now / 1000 - last) / 60);
  if (!fill && ago < mo.gapMin) return `son maraqlı video ${ago} dəq əvvəl (ara ${mo.gapMin} dəq)`;
  return "";
}
// Mövzu + fakt + görüntü → <qovluq>/xeber.json (tur: "maraqli"). Alınmasa null (xəbər videosu gedir).
async function maraqliSec({ now, state, env, fetch: f, policy, dir, log, post, hazirla = VM.hazirla }) {
  let x = null;
  try {
    x = await hazirla({ now, env, fetch: f, policy, dir, log, istifade: new Set(Object.keys(state.m || {})), klip: new Set(Object.keys(state.klip || {})) });
  } catch (e) { log(`::warning::maraqlı video alınmadı — ${String(e?.message || e).slice(0, 300)}`); return null; }
  if (!x) return null;
  const { klip, ...rest } = x;
  const out = { ...rest, klipler: klip.map(k => k.file), goruntu: klip.map(goruntuSetir), goruntuMenbe: VS.kredit(klip) };
  fs.writeFileSync(path.join(dir, "xeber.json"), JSON.stringify(out, null, 1));
  if (post) {
    const t = Math.floor(now / 1000);
    state.v[out.id] = t; state._last = t; (state.m ||= {})[out.movzu] = t;
    for (const k of klip) (state.klip ||= {})[`${k.p}:${k.id}`] = t;
  }
  log(`maraqlı video: seçildi — ${out.title} (${out.sourceUrl})`);
  output("hazir", "1");
  output("tur", "maraqli");
  return out;
}

// Plan + görüntü → <qovluq>/xeber.json (tur: "hava"). Məlumat və rəqəm yoxlaması video-hava.cjs-dədir; keçməsə video yoxdur.
async function havaHazirla({ raw, app, now, state, env = process.env, fetch: f = globalThis.fetch, policy = () => false, dir, log = console.log, post = true, footage = true, arxiv = [] }) {
  const list = VH.cities(app), today = bakuClock(now).day, day = bakuClock(now + 86400e3).day;
  const { rows, why } = VH.parse(raw, list, day);
  if (why.length) log(`hava videosu: ötürülən şəhər — ${why.join("; ")}`);
  const p = VH.plan(rows, day, { label: c => app.wxCode(c)[0], now });
  const bad = VH.yoxla(p, rows);
  if (bad) throw new Error(`rəqəm yoxlaması — ${bad}`);
  if (policy(VH.policyRow(p))) throw new Error("mətn saytın qaydasından keçmir");
  fs.mkdirSync(dir, { recursive: true });
  // Görüntü: hava şəraitinə uyğun səhnə, əvvəl Bakının özü (video-hava.cjs sahneler). Yer icazəsi: Azərbaycan və Bakı — yad yerin
  // etiketli klipi atılır, kadrı montaj redaktoru yoxlayır. KLIP_MIN-dən az uyğun klip varsa görüntüsüz (brend fonu): hava videosu
  // gündəlikdir, rəqəmlər əsasdır — xəbər videosundakı kimi ötürülmür.
  // Arxiv (video-arxiv.cjs, seçim video-hava.cjs arxivSecim): əvvəl Bakının yeri yoxlanmış, sabahkı havada çəkilmiş klipi — başlıq kadrı.
  const ax = VH.arxivSecim(p);
  let klip = footage && (VS.MENBELER.some(m => env[m.env]) || arxiv.some(e => e.menbe === "Sahib")) ? await VS.goruntu(VH.sahneler(p), dir, { env, fetch: f, log, say: 6, category: "hava",
    istifade: new Set(Object.keys(state.klip || {})), yer: ["Azerbaijan"], xeber: { title: p.headline, text: p.text, yer: ax.yer }, arxiv, hava: ax.hava }) : [];
  if (klip.length && klip.length < KLIP_MIN) {
    for (const k of klip) fs.rmSync(path.join(dir, k.file), { force: true });
    log(`hava videosu: uyğun görüntü ${klip.length} klip (ən az ${KLIP_MIN}) — brend fonu ilə`);
    klip = [];
  }
  const x = { ...p, ...(klip.length ? { klipler: klip.map(k => k.file), goruntu: klip.map(goruntuSetir), goruntuMenbe: VS.kredit(klip) } : {}) };
  fs.writeFileSync(path.join(dir, "xeber.json"), JSON.stringify(x, null, 1));
  if (post) {
    const t = Math.floor(now / 1000);
    (state.hava ||= {})[today] = t;   // seçim günü sayır: video alınmasa da eyni gün hər 30 dəqiqədə təkrar hazırlanmır
    for (const k of klip) (state.klip ||= {})[`${k.p}:${k.id}`] = t;
  }
  log(`hava videosu: hazırlanır — ${p.title} (${p.link})`);
  output("hazir", "1");
  output("tur", "hava");
  return x;
}
async function havaSec({ app, now, state, env, fetch: f, policy, dir, log, post, arxiv }) {
  try {
    const raw = await VH.fetchData(VH.cities(app), { fetch: f, env, wait: num(env.HAVA_WAIT_MS, 5000) });
    return await havaHazirla({ raw, app, now, state, env, fetch: f, policy, dir, log, post, arxiv });
  } catch (e) {
    log(`::warning::hava videosu alınmadı — ${String(e?.message || e).slice(0, 300)}; növbəti pəncərədə yenidən`);
    return null;
  }
}

async function sourcePage(a, f) {
  if (!/^https?:\/\//.test(String(a.sourceUrl || ""))) return "";
  return f(a.sourceUrl, { headers: { "user-agent": UA }, signal: AbortSignal.timeout(10000) })
    .then(r => (r?.ok && r.text ? r.text() : ""), () => "").catch(() => "");
}

// Ən vacib, hələ video olmamış, izahı olan xəbər. Seçilməyənlər state.skip-ə düşür (hər dövrədə yenidən oxunmasın).
async function pick({ articles, state, now, opt, fetch: f, policy, log, only = "" }) {
  const sec = Math.floor(now / 1000);
  // Lentin dili profildədir (lent.dil): yalnız o dildəki xəbərlər namizəddir.
  const list = only ? (articles || []).filter(a => a.id === only) : S.candidates(articles, now, { ...opt, lang: dil().lent.dil });
  for (const a of list) {
    if (!only && (state.v[a.id] || state.skip[a.id] || state.t[S.titleKey(a)])) continue;
    const topic = S.topicOf(a, Date.parse(a.publishedAt) / 1000 || sec);
    if (!only && state.topics.some(t => S.sameTopic(t, topic))) { state.skip[a.id] = sec; log(`video: eyni mövzuda video var, ötürülür — ${S.clean(a.title)}`); continue; }
    if (!only && VS.protokol(a)) { state.skip[a.id] = sec; log(`video: protokol xəbəri (görüş, qəbul, təbrik) — kadrla göstərilmir, ötürülür — ${S.clean(a.title)}`); continue; }
    const page = await sourcePage(a, f);
    const text = S.describe(a, page, policy, dil().re.herf);
    if (!text) { state.skip[a.id] = sec; log(`video: izah tapılmadı, ötürülür — ${S.clean(a.title)}`); continue; }
    return { a, text, topic, page };
  }
  return null;
}

// xeber.json: video-xeber.cjs-in girişi + paylaşma üçün keçid.
function entry(a, text, cats = []) {
  return { id: a.id, title: S.clean(a.title), summary: a.summary || "", text, category: a.category, bolme: cats.find(c => c.slug === a.category)?.label || "",
    source: a.source, sourceUrl: a.sourceUrl, publishedAt: a.publishedAt, alts: (a.alts || []).map(x => ({ source: x?.source })), link: S.shareUrl(a) };
}

// xeber.json-da hər klip: mənbə, nömrə, müəllif (krediti), axtarış; arxivdən gələnin arxiv nömrəsi və yoxlanmış yeri (jurnal və önizləmə).
const goruntuSetir = k => ({ p: k.p, id: k.id, user: k.user, q: k.q, ...(k.kredit ? { kredit: k.kredit } : {}), ...(k.arxiv ? { arxiv: k.arxiv, yer: k.yer, level: k.level } : {}) });
// Paylaşım mətnlərinin dilə bağlı hissələri profildədir (paylasim): etiketlər, «Ətraflı», kreditlər, abunə sətirləri.
const P = () => dil().paylasim;
// Mövzu etiketləri (Gemini, video-ssenari.cjs hashtags) əvvəl, sonra ümumilər.
const tag = x => [...(x.hashtags || []).map(t => `#${t}`), ...P().etiketler].join(" ");
// Facebook: keçid basılır — postun mətnində saytdakı xəbər (paylaşma səhifəsi: önizləmə + saytda açılır).
// Pexels və Pixabay xahişi: görüntünün haradan olduğunu göstərin.
const credit = x => (x.goruntu?.length ? `\n\n${fmt(P().goruntu, { menbe: x.goruntuMenbe || "Pexels" })}` : "");
// Hava videosu: Open-Meteo-nun CC BY 4.0 atribusiyası (kredit və lisenziya), «model proqnozu, rəsmi xəbərdarlıq deyil» (saytın hava səhifəsi
// kimi), görüntü bankı. Etiketlər hava etiketləridir (#xəbərlər yox).
const havaKredit = x => `Hava məlumatı: Open-Meteo.com, model proqnozu (CC BY 4.0). Rəsmi proqnozu Milli Hidrometeorologiya Xidməti verir.${x.goruntu?.length ? `\nGörüntü: ${x.goruntuMenbe || "Pixabay"}` : ""}`;
const havaTag = x => [...new Set([...(x.hashtags || []).map(t => `#${t}`), "#8ulduz", "#Azərbaycan"])].join(" ");
// Maraqlı video: fakt mənbəyi (Vikipediya, məqalənin keçidi) və görüntü bankı; etiketlər rubrikanındır (#xəbərlər yox).
const maraqliKredit = x => `${fmt(P().maraqli_kredit, { url: x.sourceUrl })}${x.goruntu?.length ? `
${fmt(P().goruntu, { menbe: x.goruntuMenbe || "Pixabay" })}` : ""}`;
const maraqliTag = x => [...new Set([...(x.hashtags || []).map(t => `#${t}`), ...P().maraqli_etiketler])].join(" ");
// Abunə çağırışı (sahib, 2026-11-25: «baxanlar abunə olsunlar»): keçid sətrindən sonra — birinci sətir başlıq olaraq qalır (videonun
// altında o görünür). Vəd videodakı ilə eynidir (video-xeber.cjs ABUNE). Instagram-da @ad basılır; Facebook-da səhifə postun üstündədir.
const fbAbune = x => fmt(P().fb_abune, { ved: VX.abune(x.tur).ved });
const igAbune = x => fmt(P().ig_abune, { ved: VX.abune(x.tur).ved });
const etrafli = link => fmt(P().etrafli, { link }), dahaCox = link => fmt(P().daha_cox, { link });
const fbText = x => (x.tur === "maraqli"
  ? `${S.cut(x.title, 300)}

${S.cut(x.text, 1500)}

${dahaCox(x.link)}

${fbAbune(x)}

${maraqliKredit(x)}

${maraqliTag(x)}`
  : x.tur === "hava"
  ? `${S.cut(x.title, 300)}\n\n${S.cut(x.text, 1500)}\n\n${etrafli(x.link)}\n\n${fbAbune(x)}\n\n${havaKredit(x)}\n\n${havaTag(x)}`
  : `${S.cut(x.title, 300)}\n\n${S.cut(x.text, 900)}\n\n${etrafli(x.link)}\n\n${fbAbune(x)}${credit(x)}\n\n${tag(x)}`);
// Instagram: keçid basılmır (sosial-paylasma.md) — sayt adı və «keçid profildədir».
const igText = x => (x.tur === "maraqli"
  ? `${S.cut(x.title, 300)}

${S.cut(x.text, 1500)}

${dahaCox(P().profil_kecid)}

${igAbune(x)}

${maraqliKredit(x)}

${maraqliTag(x)} #video`
  : x.tur === "hava"
  ? `${S.cut(x.title, 300)}\n\n${S.cut(x.text, 1500)}\n\n${etrafli(P().profil_kecid)}\n\n${igAbune(x)}\n\n${havaKredit(x)}\n\n${havaTag(x)} #video`
  : `${S.cut(x.title, 300)}\n\n${S.cut(x.text, 1200)}\n\n${etrafli(P().profil_kecid)}\n\n${igAbune(x)}${credit(x)}\n\n${tag(x)} #video`);

const wait = ms => new Promise(ok => setTimeout(ok, ms));
const SECIM_MAX = 4, KLIP_MIN = 2;
const json = r => (r?.json ? r.json().catch(() => ({})) : {});

// Hər şəbəkə: { name, prepare(f, log), post(x, video, f, log) → { ok, id } | { skip } }. Açar yoxdursa siyahı boşdur.
function networks(env = process.env) {
  const list = [];
  if (!env.FB_PAGE_ID || !env.FB_PAGE_TOKEN) return list;
  const ver = env.FB_GRAPH_VERSION || "v27.0", root = `https://graph.facebook.com/${ver}/`, page = encodeURIComponent(env.FB_PAGE_ID);
  const form = (f, u, body, token, ms = 30000) => f(u, { method: "POST", headers: { "content-type": "application/x-www-form-urlencoded" },
    body: new URLSearchParams({ ...body, access_token: token }).toString(), signal: AbortSignal.timeout(ms) });
  // Fayl Meta-nın yükləmə serverinə birbaşa gedir (ictimai ünvan lazım deyil): bir hissədə, offset 0.
  const upload = (f, url, token, video) => f(url, { method: "POST", signal: AbortSignal.timeout(180000), body: video,
    headers: { authorization: `OAuth ${token}`, offset: "0", file_size: String(video.length), "content-type": "application/octet-stream" } });
  const pageToken = async (f, log, self) => {
    const r = await f(`${root}${page}?fields=access_token,instagram_business_account&access_token=${encodeURIComponent(env.FB_PAGE_TOKEN)}`, { signal: AbortSignal.timeout(15000) }).then(json).catch(() => ({}));
    if (r?.access_token && r.access_token !== env.FB_PAGE_TOKEN) { self.token = r.access_token; log(`${self.name}: istifadəçi açarından səhifə açarı alındı`); }
    return r || {};
  };
  if (env.VIDEO_FACEBOOK !== "0") list.push({ name: "facebook", token: env.FB_PAGE_TOKEN,
    async prepare(f, log) { await pageToken(f, log, this); return true; },
    async post(x, video, f, log) {
      const start = await form(f, `${root}${page}/video_reels`, { upload_phase: "start" }, this.token).then(json);
      if (!start?.video_id) return { ok: false, error: `başlanğıc: ${JSON.stringify(start?.error || start).slice(0, 300)}` };
      const id = start.video_id;
      const up = await upload(f, start.upload_url || `https://rupload.facebook.com/video-upload/${ver}/${id}`, this.token, video);
      const upj = await json(up);
      if (!up.ok || upj?.success === false) return { ok: false, error: `yükləmə: HTTP ${up.status} ${JSON.stringify(upj?.error || upj).slice(0, 300)}` };
      const fin = await form(f, `${root}${page}/video_reels`, { upload_phase: "finish", video_id: id, video_state: "PUBLISHED",
        title: S.cut(x.title, 100), description: fbText(x) }, this.token).then(json);
      if (!fin?.success) return { ok: false, error: `dərc: ${JSON.stringify(fin?.error || fin).slice(0, 300)}` };
      // Emal bitənə qədər gözlə (şərh yalnız dərc olunmuş videoya yazılır). Gözləmə bitsə də post dərc olunub sayılır.
      let st = "";
      for (let i = 0, n = Math.ceil(num(env.VIDEO_FB_WAIT_S, 180) * 1000 / num(env.VIDEO_POLL_MS, 10000)); i < n; i++) {
        const s = await f(`${root}${encodeURIComponent(id)}?fields=status&access_token=${encodeURIComponent(this.token)}`, { signal: AbortSignal.timeout(15000) }).then(json).catch(() => ({}));
        st = s?.status?.video_status || "";
        if (st === "ready" || s?.status?.publishing_phase?.status === "complete") break;
        if (/error|expired|failed/.test(st)) return { ok: false, error: `emal: ${JSON.stringify(s.status).slice(0, 300)}` };
        await wait(num(env.VIDEO_POLL_MS, 10000));
      }
      if (env.VIDEO_FB_SERH !== "0") {
        const c = await form(f, `${root}${encodeURIComponent(id)}/comments`, { message: etrafli(x.link) }, this.token, 20000).then(json).catch(() => ({}));
        if (!c?.id) log(`facebook: keçidli şərh yazılmadı (pages_manage_engagement icazəsi lazımdır) — ${JSON.stringify(c?.error?.message || c).slice(0, 160)}`);
      }
      return { ok: true, id, status: st };
    } });
  if (env.INSTAGRAM !== "0" && env.VIDEO_INSTAGRAM !== "0") list.push({ name: "instagram", token: env.FB_PAGE_TOKEN, ig: env.IG_USER_ID || "",
    async prepare(f, log) {
      const r = await pageToken(f, () => {}, this);
      this.ig ||= r?.instagram_business_account?.id || "";
      if (!this.ig) { log(`instagram: səhifəyə bağlı Instagram peşəkar hesabı və ya açarda instagram_basic yoxdur${r?.error?.message ? ` (${r.error.message})` : ""} — ötürülür`); return false; }
      return true;
    },
    async post(x, video, f, log) {
      const q = `access_token=${encodeURIComponent(this.token)}`, get = u => f(u, { signal: AbortSignal.timeout(15000) }).then(json).catch(() => ({}));
      const lim = (await get(`${root}${encodeURIComponent(this.ig)}/content_publishing_limit?fields=quota_usage,config&${q}`))?.data?.[0];
      if (lim?.quota_usage != null && Number(lim.quota_usage) >= (Number(lim?.config?.quota_total) || 100)) return { skip: `24 saatlıq hədd dolub: ${lim.quota_usage}` };
      // 2026-11-22: ilk görüntülü videoda (16,8 MB) rupload «ProcessingFailedError» verdi (retriable: false; Facebook eyni faylı qəbul etdi).
      // Eyni sorğunun təkrarı kömək etmir: bir dəfə yeni konteynerlə, VIDEO_IG_RETRY_MS sonra. Yüklənməmiş konteyner dərc olunmur.
      let init, up, upj;
      for (let t = 0; t < 2; t++) {
        if (t) { log(`instagram: yükləmə alınmadı (HTTP ${up.status} ${JSON.stringify(upj?.error || upj).slice(0, 200)}) — yeni konteynerlə təkrar`); await wait(num(env.VIDEO_IG_RETRY_MS, 60000)); }
        init = await form(f, `${root}${encodeURIComponent(this.ig)}/media`, { media_type: "REELS", upload_type: "resumable", caption: igText(x),
          thumb_offset: String(Math.round((x.cover_s || 1.5) * 1000)) }, this.token).then(json);
        if (!init?.id) return { ok: false, error: `konteyner: ${JSON.stringify(init?.error || init).slice(0, 300)}` };
        up = await upload(f, init.uri || `https://rupload.facebook.com/ig-api-upload/${ver}/${init.id}`, this.token, video);
        upj = await json(up);
        if (up.ok && upj?.success !== false) break;
      }
      if (!up.ok || upj?.success === false) return { ok: false, error: `yükləmə: HTTP ${up.status} ${JSON.stringify(upj?.error || upj).slice(0, 300)}` };
      // Meta tövsiyəsi: statusu dəqiqədə bir, 5 dəqiqədən çox olmayaraq; qısa video adətən 20–60 s-də hazır olur.
      let st = "";
      for (let i = 0, n = Math.ceil(num(env.VIDEO_IG_WAIT_S, 300) * 1000 / num(env.VIDEO_POLL_MS, 15000)); i < n && st !== "FINISHED"; i++) {
        await wait(num(env.VIDEO_POLL_MS, 15000));
        const s = await get(`${root}${encodeURIComponent(init.id)}?fields=status_code,status&${q}`);
        st = s?.status_code || "";
        if (st === "ERROR" || st === "EXPIRED") return { ok: false, error: `emal: ${st} ${String(s?.status || "").slice(0, 200)}` };
      }
      if (st !== "FINISHED") return { ok: false, error: `emal ${num(env.VIDEO_IG_WAIT_S, 300)} s-də bitmədi (${st || "?"})` };
      const pub = await form(f, `${root}${encodeURIComponent(this.ig)}/media_publish`, { creation_id: init.id }, this.token);
      const pj = await json(pub);
      if (pub.ok && pj?.id) return { ok: true, id: pj.id };
      // social.cjs (2026-11-13…20): dərc cavabı xəta olsa da post çıxa bilir — konteynerin statusu yoxlanır.
      await wait(num(env.VIDEO_POLL_MS, 15000) / 3);
      if ((await get(`${root}${encodeURIComponent(init.id)}?fields=status_code&${q}`))?.status_code === "PUBLISHED") return { ok: true, id: init.id };
      return { ok: false, error: `dərc: HTTP ${pub.status} ${JSON.stringify(pj?.error || pj).slice(0, 300)}` };
    } });
  return list;
}

function output(key, value) {
  if (process.env.GITHUB_OUTPUT) fs.appendFileSync(process.env.GITHUB_OUTPUT, `${key}=${value}\n`);
}

// sec: vaxtıdırsa xəbəri seçir. Paylaşma rejimində seçim dərhal «video» sayılır (_last): video alınmasa da eyni xəbər hər
// 30 dəqiqədə yenidən hazırlanmasın.
// arxiv: öz video arxivi (VA.kitabxana(): «video-arxiv» budağı, oxunmasa data/video-arxiv.json) — xəbərin yeri məlum olanda əvvəl oradan.
async function sec({ articles, env = process.env, now = Date.now(), state, fetch: f = globalThis.fetch, policy = () => false, cats = [], dir, log = console.log, app = null, arxiv = [], maraqli = VM.hazirla }) {
  const opt = options(env), post = env.VIDEO_PAYLAS !== "0";
  // İş axını seçimə açarın özünü vermir, yalnız VIDEO_ACAR=1/0 (açar var/yox).
  const hasKey = env.VIDEO_ACAR ? env.VIDEO_ACAR === "1" : networks(env).length > 0;
  if (post && !hasKey) { log("video: açar yoxdur (FB_PAGE_TOKEN) — heç nə hazırlanmır"); return null; }
  const only = String(env.VIDEO_XEBER || "").trim();
  // Hava videosu (VIDEO_TUR: avtomatik — vaxtıdırsa; hava — dərhal, önizləmə və əl ilə; xeber — yalnız xəbər). Alınmasa (Open-Meteo cavab
  // vermədi) bu pəncərədə xəbər videosu gedir, hava növbəti pəncərədə yenidən sınanır. Paylaşma rejimində gündə bir dəfə.
  const tur = String(env.VIDEO_TUR || "").trim();
  // Hava videosunun mətnləri (video-hava.cjs: şəhər adlarının şəkilçiləri, külək, xəbərdarlıq) azərbaycancadır: yalnız profildə hava: true.
  if (!only && tur !== "xeber" && app?.CITIES && dil().hava) {
    const why = tur === "hava" ? (post && state.hava?.[bakuClock(now).day] ? "bu günün hava videosu artıq paylaşılıb (önizləmə üçün «Paylaş»-ı söndürün)" : "")
      : havaDue(state, now, havaOptions(env));
    if (!why) {
      const x = await havaSec({ app, now, state, env, fetch: f, policy, dir, log, post, arxiv });
      if (x || tur === "hava") return x;
    } else {
      log(`video: ${why}`);
      if (tur === "hava") return null;
    }
  }
  if (!only && post) {   // yalnız hazırlama (önizləmə) fasilə gözləmir
    const why = due(state, now, opt);
    if (why) { log(`video: ${why}`); return null; }
  }
  // Maraqlı video: vaxtıdırsa əvvəl o (alınmasa xəbər); VIDEO_TUR=maraqli — dərhal (önizləmə və əl ilə).
  const mo = maraqliOptions(env), mArgs = { now, state, env, fetch: f, policy, dir, log, post, hazirla: maraqli };
  if (!only && tur !== "xeber") {
    const why = tur === "maraqli" ? (mo.on ? "" : "maraqlı video söndürülüb (MARAQLI_VIDEO=0)") : maraqliDue(state, now, mo);
    if (!why) { const x = await maraqliSec(mArgs); if (x || tur === "maraqli") return x; }
    else { log(`video: ${why}`); if (tur === "maraqli") return null; }
  }
  // Sahib, 2026-11-22: «Xəbər uzun olsun biraz və videogörüntü olsun o xəbərə uyğun». Gemini mənbənin mətnindən 4–7 cümləlik
  // diktor mətni yazır, Pixabay/Pexels-dən xəbərə uyğun klip gəlir (alınmasa tünd fon). video-ssenari.cjs.
  // Xəbər kadrla göstərilmirsə və ya mətn yoxlamadan keçmirsə («uygun: false»), növbəti xəbər (ən çox SECIM_MAX).
  // Yalnız əl ilə seçilən xəbərdə (VIDEO_XEBER) Gemini alınmasa mənbənin öz cümlələri gedir.
  // Keyfiyyət həddi: görüntü mənbəyi varsa, KLIP_MIN-dən az uyğun klip tapılan xəbər ötürülür (yanlış və ya boş görüntülü video yox).
  const footage = VS.MENBELER.some(m => env[m.env]) || arxiv.some(e => e.menbe === "Sahib");
  let got = null, sc = null, klip = [];
  for (let i = 0; i < SECIM_MAX; i++) {
    got = await pick({ articles, state, now, opt, fetch: f, policy, log, only });
    if (!got) break;
    const bolme = cats.find(c => c.slug === got.a.category)?.label || "";
    sc = await VS.ssenari({ ...got.a, bolme }, got.page, { env, fetch: f, policy, log, fallback: got.text });
    // Gemini işləmir (gündəlik limit və s.): mənbənin cümlələri və ümumi kadrla video olmur — növbəti dövrədə yenidən.
    if (!only && !sc) { log("video: Gemini mətni yoxdur — bu dövrədə video hazırlanmır, növbəti dövrədə yenidən"); return null; }
    if (only || sc.uygun !== false) {
      fs.mkdirSync(dir, { recursive: true });
      // Son 3 günün videolarında işlənmiş kliplər yenidən götürülmür (state.klip, «Pixabay:123»): eyni kadr hər gün görünməsin.
      klip = await VS.goruntu(sc?.axtar || [], dir, { env, fetch: f, log, category: got.a.category, istifade: new Set(Object.keys(state.klip || {})),
        yer: sc?.yer || [], xeber: sc?.text ? { title: got.a.title, text: sc.text, yer: sc.yer } : null, arxiv });
      if (only || !footage || klip.length >= KLIP_MIN) break;
      for (const k of klip) fs.rmSync(path.join(dir, k.file), { force: true });
      sc = { uygun: false, sebeb: `uyğun görüntü ${klip.length} klip, ən az ${KLIP_MIN}` };
      klip = [];
    }
    log(`video: ötürülür (${sc.sebeb || "uyğun deyil"}) — ${S.clean(got.a.title)}`);
    state.skip[got.a.id] = Math.floor(now / 1000);
    got = null;
  }
  if (!got) {
    log(only ? `video: ${only} lentdə yoxdur və ya izahı tapılmadı` : "video: uyğun xəbər yoxdur");
    // Uyğun xəbər yoxdur: pəncərə boş qalmasın — maraqlı video (öz fasiləsi gözlənmir, gündəlik həddə qədər).
    if (!only && tur !== "xeber" && !maraqliDue(state, now, mo, true)) return await maraqliSec(mArgs);
    return null;
  }
  const x = { ...entry(got.a, sc?.text || got.text, cats), ...(sc?.text ? { ssenari: "gemini" } : {}), ...(sc?.etiket?.length ? { hashtags: sc.etiket } : {}),
    ...(klip.length ? { klipler: klip.map(k => k.file), goruntu: klip.map(goruntuSetir), goruntuMenbe: VS.kredit(klip) } : {}) };
  fs.writeFileSync(path.join(dir, "xeber.json"), JSON.stringify(x, null, 1));
  if (post) {
    const t = Math.floor(now / 1000);
    state.v[x.id] = t; state._last = t;
    for (const k of klip) (state.klip ||= {})[`${k.p}:${k.id}`] = t;
  }
  log(`video: seçildi — ${x.title} (${x.link})`);
  output("hazir", "1");
  return x;
}

// paylas: hazır videonu hər şəbəkəyə yükləyir. Nəticə state-ə yazılır; hamısı alınmasa iş qırmızıdır.
async function paylas({ dir, env = process.env, now = Date.now(), state, fetch: f = globalThis.fetch, log = console.log }) {
  const x = JSON.parse(fs.readFileSync(path.join(dir, "xeber.json"), "utf8"));
  let meta = {};
  try { meta = JSON.parse(fs.readFileSync(path.join(dir, "video.json"), "utf8")); } catch {}
  const video = fs.readFileSync(path.join(dir, "video.mp4"));
  const nets = networks(env), t = Math.floor(now / 1000), res = { posted: [], failed: [] };
  const hide = s => [env.FB_PAGE_TOKEN, ...nets.map(n => n.token)].filter(k => k && k.length > 8).reduce((m, k) => m.split(k).join("***"), String(s?.message || s));
  for (const net of nets) {
    try {
      if (!(await net.prepare(f, log))) continue;
      const r = await net.post({ ...x, cover_s: meta.cover_s }, video, f, log);
      if (r?.skip) { log(`${net.name}: video ötürülür (${r.skip})`); continue; }
      if (!r?.ok) throw new Error(r?.error || "naməlum xəta");
      state[net.name][x.id] = t;
      res.posted.push(net.name);
      log(`${net.name}: video paylaşıldı — ${x.title}`);
    } catch (e) {
      res.failed.push(net.name);
      log(`${net.name}: video alınmadı — ${hide(e)}`);
    }
  }
  // Hava videosu ayrıca qaydadır: xəbər videosunun siyahısına (fasilə, gündəlik hədd, mövzu) düşmür.
  if (x.tur === "hava") { const d = bakuClock(now).day; (state.hava ||= {})[d] = state.hava[d] || t; return res; }
  // Maraqlı video: gündəlik həddə və fasiləyə sayılır (seçimdə yazılıb), xəbər mövzularının siyahısına düşmür.
  if (x.tur === "maraqli") { state.v[x.id] = state.v[x.id] || t; if (x.movzu) (state.m ||= {})[x.movzu] = state.m[x.movzu] || t; return res; }
  state.v[x.id] = state.v[x.id] || t;
  state.t[S.titleKey(x)] = t;
  state.topics.push({ ...S.topicOf(x, Date.parse(x.publishedAt) / 1000 || t), posted: t });
  return res;
}

async function main() {
  const [cmd, a1, a2] = process.argv.slice(2);
  const stateFile = process.env.VIDEO_STATE || ".sosial-video/state.json";
  const now = Date.now(), state = readState(stateFile, now);
  if (cmd === "numune") {
    const x = JSON.parse(fs.readFileSync(a1, "utf8"));
    fs.mkdirSync(a2, { recursive: true });
    fs.writeFileSync(path.join(a2, "xeber.json"), JSON.stringify({ ...x, text: x.text || x.summary, link: S.shareUrl(x) }, null, 1));
    output("hazir", "1");
    return;
  }
  if (cmd === "numune-hava") {
    // PR yoxlaması: Open-Meteo-nun saxlanmış cavabından (tests/fixtures/video-hava.json) hava videosu — şəbəkə və paylaşma yoxdur.
    const fx = JSON.parse(fs.readFileSync(a1, "utf8")), app = require("./topics.cjs").loadApp(path.resolve("."));
    await havaHazirla({ raw: fx.response, app, now: Date.parse(fx.now), state, env: {}, policy: a => app.policyViolation(a), dir: a2, post: false, footage: false });
    return;
  }
  if (cmd === "numune-maraqli") {
    // PR yoxlaması: saxlanmış maraqlı video (tests/fixtures/video-maraqli.json) — Vikipediya, Gemini və paylaşma yoxdur, kliplər süni.
    const x = JSON.parse(fs.readFileSync(a1, "utf8"));
    fs.mkdirSync(a2, { recursive: true });
    fs.writeFileSync(path.join(a2, "xeber.json"), JSON.stringify({ ...x, tur: "maraqli", kind: "maraqli" }, null, 1));
    output("hazir", "1");
    output("tur", "maraqli");
    return;
  }
  if (cmd === "sec") {
    // Qırmızı xətt 2, ikinci qapı: lent saytın öz qaydasından keçir; qayda faylı oxunmasa xəta ilə dayanır (heç nə seçilmir).
    const app = require("./topics.cjs").loadApp(path.resolve("."));
    const articles = (JSON.parse(fs.readFileSync(a1, "utf8")).articles || []).filter(a => !app.policyViolation(a));
    await sec({ articles, state, now, policy: a => app.policyViolation(a), cats: app.CATS, dir: a2, app, arxiv: VA.kitabxana(process.env, console.log) });
    writeState(stateFile, state);
    return;
  }
  if (cmd === "paylas") {
    const res = await paylas({ dir: a1, state, now });
    writeState(stateFile, state);
    if (res.failed.length && !res.posted.length) process.exitCode = 1;
    return;
  }
  console.error("İşlədilmə: sosial-video.cjs sec <news.json> <qovluq> | numune <xəbər.json> <qovluq> | numune-hava <open-meteo.json> <qovluq> | numune-maraqli <video.json> <qovluq> | paylas <qovluq>");
  process.exitCode = 2;
}

module.exports = { options, readState, due, pick, entry, networks, sec, paylas, fbText, igText, havaOptions, havaDue, havaHazirla, bakuClock,
  maraqliOptions, maraqliDue, maraqliSec, maraqliSay };
if (require.main === module) main().catch(e => { console.error(`video: ${String(e?.message || e)}`); process.exitCode = 1; });
