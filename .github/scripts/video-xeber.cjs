// Video xəbər (sahib, 2026-11-22: «Facebook-da video xəbərlər verilsin… İnstagramda videolar verilsin. Videolarda başda 8ulduz.az
// yazılsın»). Bir xəbərdən şaquli qısa video (Reels): saytın rəngləri, yuxarıda başdan sona loqo + «8ulduz.az», böyük başlıq,
// izah cümlə-cümlə altyazı kimi, istəyə görə Azərbaycan səsi (SARA, «Dinlə» serverinin modeli), sonda «Ətraflı: 8ulduz.az».
// Videoda: xəbərin başlığı və izahı (mətn), brend dizaynı, səs və görüntü. Görüntü (sahib, 2026-11-22: «videogörüntü olsun o xəbərə
// uyğun»; 2026-11-26: «bir çox xəbər saytı hesabı eyni görüntünü verir… biz də verək»): xəbərin mənbə saytındakı öz videosu
// (video-menbe.cjs; mənbə videoda yazılır), yoxdursa Pixabay/Pexels video bankının klipləri (video-ssenari.cjs).
// X-in videoları, xəbərin fotosu və musiqi yoxdur (docs/sosial-video.md «Görüntünün mənbəyi»).
//
// İşlədilmə:  node .github/scripts/video-xeber.cjs <giriş.json> <çıxış.mp4>
//   giriş  — data/news.json sətri (id, title, summary, category, source, alts, publishedAt) + istəyə bağlı:
//            text  ekranda və səsdə gedən izah (social.cjs describe(): yalnız tam cümlələr); yoxdursa summary-nin tam cümlələri
//            bolme bölmənin adı (yoxdursa saytın CATS siyahısından)
//            klipler  fon klipləri (çıxış qovluğuna görə yol; video-ssenari.cjs goruntu()). Varsa fon görüntüdür, yoxdursa tünd göy
//                     fon; şaquli klip ekranı doldurur, üfüqi tam enində ortada (arxada bulanıq nüsxəsi)
//            goruntuMenbe  videoda «Görüntü: …» (Pixabay və ya Pexels)
//            menbeVideo  { file, kredit } — mənbə saytının öz videosu (video-menbe.cjs): oxunursa fon odur, «Görüntü: <kredit>»
//            ses   false → səssiz (boş səs izi)
//   çıxış  — <çıxış>.mp4: MP4 (moov əvvəldə), H.264 High 4.1, yuv420p, 1080×1920 (9:16), 30 kadr/s, GOP 2 s, CRF 21 (≤8 Mbit/s),
//            AAC-LC 48 kHz stereo 128 kbit/s; MIN_S…MAX_S saniyə. Facebook Reels (3–90 s), Instagram Reels və TikTok qəbul edir.
//            <çıxış>.json: xəbərin sahələri (id, own: true, title, summary, text, source, sourceUrl, category, lang, publishedAt) +
//            { duration, width, height, bytes, …, cover_s, kadrlar, voice, parts }; mp4-də nişan comment=8ulduz.az (TikTok yükləyicisi)
//            <çıxış>.jpg: örtük kadrı (başlıq tam görünən an, cover_s)
//   require: const { render } = require("./video-xeber.cjs"); await render(sətir, "video.mp4")
// Lazımdır: ffmpeg (libass ilə; Ubuntu paketi belədir), Roboto şrifti (fonts-roboto-unhinted; yoxdursa sistem şrifti).
// Səs üçün: python3 + torch + transformers (.github/scripts/video_ses.py). Səs alınmasa video səssiz hazırlanır, iş dayanmır.
//
// Qırmızı xətt 2: giriş saytın öz qaydasından (app.js policyViolation) keçir — başlıq da, izah da; pozan xəbər üçün video olmur.
// Qırmızı xətt 1 və 3-ə toxunmur: GitHub Actions-da ayrıca iş axınıdır (sosial-video.yml), sayta və xəbər axınına heç nə yazmır.
// Dil profili (sahib, 2026-11-26, yol xəritəsinin 2-ci addımı): ekrandakı və səsdəki bütün yazılar (abunə çağırışı, nişanlar, mənbə,
// aylar, bağlayıcılar) .github/video-dil/<VIDEO_DIL>.json-dandır (video-dil.cjs); boş — az. Burada dilə bağlı mətn yoxdur.
"use strict";
const fs = require("fs"), path = require("path"), os = require("os"), { spawnSync } = require("child_process");
const { dil, fmt } = require("./video-dil.cjs");

const ROOT = path.resolve(__dirname, "../..");
const W = 1080, H = 1920, FPS = 30;
const X0 = 72, TEXT_W = W - 2 * X0;            // sağda Reels düymələri, aşağıda Reels izahı: mətn bu sahədə qalır
const MIN_S = 8, MAX_S = 59;                   // Facebook Reels API 3–90 s; qısa video daha çox sona qədər baxılır
const BODY_MAX = 750;                          // izahın ekranda/səsdə ən çox simvolu (≈ 5–7 cümlə, 35–45 s; sahib 2026-11-22: «4-7 cümlədə olsun. uzun da olsun»)
const LEAD_S = 0.35, GAP_S = 0.25, OUTRO_S = 2.8;
// Başlıq oxunmur (sahib, 2026-11-24: «Başlıqları oxumasın»; 2026-11-25: «8ulduz videolarında başlıq oxunmamalı idi»): başlıq ekranda
// başdan sonluğa qədər yazılıb qalır, səs birinci cümlə ilə başlayır. Başlıq üçün ayrıca səssiz an yoxdur: səs LEAD_S-də başlayır
// (2026-11-25, YouTube Studio: baxanların 60,6%-i videonu ilk saniyələrdə ötürür, orta baxış ~7 s — ilk saniyə sükutla getməsin).
// Abunə çağırışı (sahib, 2026-11-25: «baxış var, lakin baxanlar hesaba abunə olmurlar»): sonluqda vəd, şəbəkənin öz abunə düyməsini
// göstərən ipucu və səs (subOutro; 2026-11-26-dan videoda basılmayan düymə şəkli yoxdur). Hər video növünün öz vədi var: abunə olan nə alacağını bilsin.
// Səs iki cümlədir (sahib, 2026-11-25: «Abunə ol deyib pauza vermir. belə oxuyanda nə dediyini tam başa düşmək olmur»): «Abunə olun.»
// ayrıca cümlə kimi bitir, sonra cümlə fasiləsi, sonra vəd. Vergüllə yazılanda səs fasiləsiz oxuyurdu.
// Vədlər profildədir (abune: { xeber, maraqli, hava } → { ved, say }); ABUNE — az profilininki (testlər və yükləyicilər müqayisə edir).
const ABUNE = dil("az").abune;
const abune = tur => { const a = dil().abune; return a[tur] || a.xeber; };
// Rənglər saytdandır: tünd göy fon (og-default.png, app.css --bg), loqonun narıncısı.
const COLOR = { bg: "0B1426", bar: "060D1A", orange: "F5A30A", white: "FFFFFF", gray: "AFC0D8", box: "1A3563", blue: "1E4D8C", blue2: "2563EB" };
// Yerləşmə (piksel, 1080×1920). Lentdə Reels ortadan 4:5-ə kəsilir (y 285…1635), tam ekranda yuxarıda ~170 px, aşağıda ~420 px,
// sağda ~130 px şəbəkənin öz düymələridir: brend və bütün yazılar y 300…1480 arasındadır — loqo lentdə də, tam ekranda da görünür.
const L = { barY: 300, barH: 120, logoH: 80, chipY: 466, headY: 556, headMaxH: 470, capMinY: 860, capMaxY: 1110, srcY: 1404, outroY: 900 };
const FONT = "Roboto";

const clean = s => String(s ?? "").replace(/<[^>]+>/g, " ").replace(/\s+/g, " ").replace(/ ([.,!?;:…])/g, "$1").trim();

// Mətnin təxmini eni (piksel). ASS-də şrift ölçüsü sətir hündürlüyüdür: Roboto Black və Medium-da ölçülmüş en ≈ 0,71 × ölçü ×
// cədvəl (2026-11-22, CI kadrı: «nəticəsində 5 kəndin» 96-lıq başlıqda 676 px). En ~4% artıq sayılır: sətri özümüz bölürük (\N),
// libass sətri əlavə bölməsin — bölsə, başlıq altyazının üstünə düşər.
function charEm(ch) {
  if (ch === " ") return 0.26;
  if (/[iljıIİ|!.,:;'’]/.test(ch)) return 0.29;
  if (/[ftr()[\]"«»“”\-–/]/.test(ch)) return 0.38;
  if (/[mwMWƏ—%@]/.test(ch)) return 0.9;
  if (/\d/.test(ch)) return 0.58;
  if (ch !== ch.toLocaleLowerCase(dil().locale)) return 0.7;
  return 0.58;
}
const WEIGHT = { black: 1, bold: 1, medium: 1, regular: 0.97 };
const EM_OF_SIZE = 0.74;
function textWidth(s, size, weight = "regular") {
  let w = 0;
  for (const ch of String(s)) w += charEm(ch);
  return w * size * EM_OF_SIZE * WEIGHT[weight];
}
// Sözlər üzrə acgöz bölmə. Sığmayan tək söz öz sətrində qalır.
function wrap(text, size, weight, maxW) {
  const lines = [];
  let cur = "";
  for (const word of clean(text).split(" ").filter(Boolean)) {
    const next = cur ? `${cur} ${word}` : word;
    if (cur && textWidth(next, size, weight) > maxW) { lines.push(cur); cur = word; } else cur = next;
  }
  if (cur) lines.push(cur);
  return lines;
}

// Başlıq: sahəyə sığan ən böyük ölçü. Çox uzun başlıq (nadir) son sətirdə «…» ilə kəsilir.
function fitHeadline(title, sizes = [96, 88, 80, 72, 66, 60], maxH = L.headMaxH, w = TEXT_W) {
  for (const size of sizes) {
    const lines = wrap(title, size, "black", w);
    if (lines.length * size <= maxH) return { size, lines };
  }
  const size = sizes[sizes.length - 1], max = Math.floor(maxH / size), lines = wrap(title, size, "black", w);
  const kept = lines.slice(0, max);
  kept[max - 1] = kept[max - 1].replace(/[\s,.;:–-]*$/, "") + "…";
  return { size, lines: kept };
}

// İzah cümlələrə bölünür; sığmayan cümlə bərabərə yaxın hissələrə — imkan olsa vergüldən, sonra bağlayıcıdan əvvəl, ən son
// istənilən sözdən («Ərçivan | qəsəbəsindən» kimi ad birləşməsi az parçalansın). Hər altyazı ən çox CAP_LINES sətir.
const CAP_SIZE = 62, CAP_LINES = 3, CAP_PAD = 16, CAP_W = TEXT_W - 2 * CAP_PAD;
// Altyazının ölçüsü: tünd fonda qutuda 3 sətir (CAP), görüntülü videonun aşağı blokunda qutusuz 2 sətir (CAPF; eni FOOT_W).
const CAP = { size: CAP_SIZE, lines: CAP_LINES, w: CAP_W }, CAPF = { size: 46, lines: 2, w: W - X0 - 100 };
const SENT_SPLIT = /(?<!(?:^|[\s(])\p{Lu}\.)(?<=[.!?…]["»”)]?)\s+(?=["«“(]?[\p{Lu}\d])/u;   // «İ. Əliyev» inisialı cümlə sonu deyil
// Bağlayıcılar (və, amma, …) profildədir: video.bagliyicilar → D.re.bagliyici.
const capLines = (s, c = CAP) => wrap(s, c.size, "medium", c.w).length;
function splitSentence(words, k, c = CAP) {
  if (k <= 1 || words.length < 2) return [words.join(" ")];
  const total = words.join(" ").length, target = total / k, D = dil(), CONJ = D.re.bagliyici;
  let best = null, pos = 0;
  for (let i = 1; i < words.length; i++) {
    pos += words[i - 1].length + 1;
    const head = words.slice(0, i).join(" ");
    if (capLines(head, c) > c.lines) break;
    const cost = Math.abs(pos - target) + (/[,;:]$/.test(words[i - 1]) ? 0 : CONJ.test(words[i].toLocaleLowerCase(D.locale)) ? 12 : 30);
    if (!best || cost < best.cost) best = { i, cost };
  }
  const i = best ? best.i : 1;
  return [words.slice(0, i).join(" "), ...splitSentence(words.slice(i), Math.max(1, k - 1), c)];
}
// Cümlə-cümlə: [[altyazı, …], …] — sığmayan cümlə bir neçə altyazıdır (səs onları bir nəfəsdə oxuyur, prepare().davam).
function captionSentences(body, c = CAP) {
  return clean(body).split(SENT_SPLIT).filter(Boolean).map(sentence => {
    const n = capLines(sentence, c);
    if (n <= c.lines) return [sentence];
    const words = sentence.split(" ");
    let parts = splitSentence(words, Math.ceil(n / c.lines), c);
    // Hissə yenə sığmırsa (çox uzun söz və s.) — bir də bölünür.
    parts = parts.flatMap(p => (capLines(p, c) <= c.lines ? [p] : splitSentence(p.split(" "), Math.ceil(capLines(p, c) / c.lines), c)));
    return parts;
  });
}
const captionChunks = (body, c = CAP) => captionSentences(body, c).flat();

// Sözlərin səsdəki vaxtı [söz, başlanğıc, son]: səs modeli hissənin [s, e] vaxtını verir, hissənin içində söz vaxtı tələffüzün
// uzunluğu ilə bölünür — hərf sayı; rəqəm sözlə oxunur («2026» → «iki min iyirmi altı», hər rəqəm ~4 hərf); «ABŞ» kimi qısaltma
// hərf-hərf oxunur (ikiqat); vergüldən və nöqtədən sonrakı fasilə həmin sözün payıdır (söz fasilədə seçili qalır).
function wordTimes(text, s, e) {
  const words = clean(text).split(" ").filter(Boolean);
  const wt = words.map(w => {
    const letters = (w.match(/\p{L}/gu) || []).length, digits = (w.match(/\d/g) || []).length;
    const caps = /^\p{Lu}{2,}/u.test(w.replace(/[^\p{L}]/gu, "")) ? letters : 0;
    return 1 + letters + caps + digits * 4 + (/[,;:–]$/.test(w) ? 3 : /[.!?…]["»”)]?$/.test(w) ? 4 : 0);
  });
  const total = wt.reduce((a, b) => a + b, 0) || 1;
  let acc = 0;
  return words.map((w, i) => { const a = s + (e - s) * acc / total; acc += wt[i]; return [w, a, s + (e - s) * acc / total]; });
}

// İzah: yalnız tam cümlələr, BODY_MAX simvola qədər (ən azı bir cümlə). Mənbənin kəsdiyi xülasə («…») sona qədər getmir.
function bodyText(a) {
  const src = clean(a.text || "") || clean(a.summary || "");
  if (!src) return "";
  const full = /(…|\.\.\.)$/.test(src) ? src.replace(/\s*(…|\.\.\.)$/, "") : src;
  const sentences = full.split(SENT_SPLIT).filter(Boolean);
  const complete = /(…|\.\.\.)$/.test(src) ? sentences.filter(s => /[.!?]["»”)]?$/.test(s)) : sentences;
  let out = "";
  for (const s of complete) {
    if (out && (out + " " + s).length > BODY_MAX) break;
    out = out ? `${out} ${s}` : s;
  }
  if (out.length > BODY_MAX * 1.5) return "";            // tək cümlə çox uzundur: video başlıq + qısa izah olmalıdır
  return clean(out) === clean(a.title) ? "" : out;
}

const sourceNames = a => [...new Set([a.source, ...(Array.isArray(a.alts) ? a.alts.map(x => x?.source) : [])].map(clean).filter(Boolean))];
function sourceLine(a) {
  const names = sourceNames(a), v = dil().video;
  if (!names.length) return "";
  if (names.length <= 2) return fmt(v.menbe, { adlar: names.join(", ") });
  return fmt(v.menbe_cox, { adlar: names.slice(0, 2).join(", "), n: names.length - 2 });
}
// Bakı vaxtı (UTC+4, yay vaxtı yoxdur).
function bakuTime(iso) {
  const t = Date.parse(iso || "");
  if (!Number.isFinite(t)) return "";
  const d = new Date(t + 4 * 3600e3);
  return `${d.getUTCDate()} ${dil().video.aylar[d.getUTCMonth()]}, ${String(d.getUTCHours()).padStart(2, "0")}:${String(d.getUTCMinutes()).padStart(2, "0")}`;
}

// Videonun mətn planı: ekranda nə yazılır, səsə nə gedir.
function prepare(a, opt = {}) {
  const title = clean(a.title);
  if (!title) throw new Error("başlıq yoxdur");
  const footage = Boolean(opt.footage), tur = a.tur === "maraqli" ? "maraqli" : "xeber";
  const head = footage ? fitHeadline(title, LF.sizes, LF.headMaxH, FOOT_W) : fitHeadline(title);
  const sentences = captionSentences(bodyText(a)), chunks = sentences.flat();
  // Maraqlı videonun nişanı rubrikanın adıdır («Bilirdinizmi?»): başlıq faktın özüdür, nişan onu suala çevirir.
  // Bölmənin adı: profildə video.bolmeler doludursa ondan (saytın bölmə adları azərbaycancadır), boşdursa (az) saytın öz adı.
  const D = dil(), own = Object.keys(D.video.bolmeler).length ? D.video.bolmeler[a.category] : a.bolme || opt.cats?.find(c => c.slug === a.category)?.label;
  const label = tur === "maraqli" ? D.video.maraqli : clean(own || D.video.xeber).toLocaleUpperCase(D.locale);
  const source = [sourceLine(a), footage ? fmt(D.video.goruntu, { menbe: clean(a.goruntuMenbe) || "Pexels" }) : ""].filter(Boolean).join(" · ");
  // davam[i]: say[i] əvvəlki hissənin cümləsinin davamıdır — video_ses.py onları bir mətn kimi səsləndirir (sahib, 2026-11-25:
  // «sətirdən sətrə keçəndə mənasız pauza verir»). Cümləni altyazı özü bölür, ona görə burada dəqiq bilinir; mətndən təxmin
  // («Xudat | Məmmədovun», «azalaraq | 3 565,2 dollar» böyük hərflə, rəqəmlə başlayır) dörddə birini buraxırdı.
  // say: səsə gedən hissələr — altyazılar və sonluq (abunə çağırışı); başlıq yoxdur (quietHead).
  return { id: a.id, title, head, chunks, label, when: bakuTime(a.publishedAt), source, footage, quietHead: true, tur,
    say: [...chunks, abune(tur).say], davam: [...sentences.flatMap(s => s.map((_, j) => j > 0)), false] };
}

// Zaman planı. voice: video_ses.py nəticəsi { parts: [[başlanğıc, son], …] } (hissələr prepare().say sırası ilə) və ya null.
// Səssiz: oxuma sürəti (~13 simvol/s), hər altyazı ən azı 2,4 s.
// p.quietHead (xəbər və maraqlı video): say-da başlıq yoxdur — head yalnız səsdən əvvəlki andır ([0, lead]), say[0] birinci altyazıdır.
// Yoxdursa (hava videosu) say[0] ekrandakı başlığın altında oxunan giriş cümləsidir və head onun vaxtıdır.
function timeline(p, voice = null) {
  const quiet = Boolean(p.quietHead), n = p.say.length, lead = LEAD_S, h = quiet ? 0 : 1;
  let spans;
  const used = Boolean(voice && Array.isArray(voice.parts) && voice.parts.length === n);
  if (used) {
    spans = voice.parts.map(([s, e]) => [lead + s, lead + e]);
  } else {
    spans = [];
    let t = lead;
    for (let i = 0; i < n; i++) {
      const len = clean(p.say[i]).length;
      const d = i < h ? Math.max(3.2, len / 14) : i === n - 1 ? OUTRO_S : Math.max(2.4, len / 13);
      spans.push([t, t + d]);
      t += d + GAP_S;
    }
  }
  const head = quiet ? [0, lead] : spans[0];
  // Çox uzun olsa sondakı altyazılar düşür (başlıq və sonluq qalır).
  let chunks = p.chunks.slice(), parts = spans.slice(h, h + chunks.length);
  const outroLen = spans[n - 1][1] - spans[n - 1][0];
  const fullEnd = (last) => last + GAP_S + Math.max(OUTRO_S, outroLen + 0.5);
  while (chunks.length && fullEnd(parts[parts.length - 1][1]) > MAX_S) { chunks.pop(); parts.pop(); }
  // Görüntü aparan video (X klipi; p.min_s — klipin uzunluğu, render): mətn qısadırsa əsas hissə klip boyu uzanır, sonluq sonda qalır.
  const outroD = Math.max(OUTRO_S, outroLen + 0.5), want = Math.min(MAX_S, Number(p.min_s) || 0) - outroD - 0.3;
  const keepUntil = parts.length ? parts[parts.length - 1][1] : head[1], mainEnd = Math.max(keepUntil + GAP_S, want);
  const outro = [mainEnd, mainEnd + outroD];
  const duration = Math.round(Math.max(MIN_S, Math.min(MAX_S, outro[1] + 0.3)) * 100) / 100;
  // Səs ekranla eyni: altyazı düşübsə onun səsi kəsilir, sonluq səsi sonluğun başlanğıcına sürüşür (hamısı video vaxtı ilə).
  // lead: səs faylının videoda başladığı an (ffmpegArgs adelay).
  return { duration, head, lead, chunks: chunks.map((text, i) => ({ text, at: parts[i] })), outro,
    voiceCut: used ? { keepUntil, outroFrom: spans[n - 1][0], outroAt: outro[0] } : null };
}

// ASS (libass) — bütün yazılar və formalar. Rəng: &HBBGGRR&, şəffaflıq: &HAA& (00 tam görünür, FF görünmür).
const assColor = hex => `&H${hex.slice(4, 6)}${hex.slice(2, 4)}${hex.slice(0, 2)}&`;
const assTime = s => { const cs = Math.max(0, Math.round(s * 100)); return `${Math.floor(cs / 360000)}:${String(Math.floor(cs / 6000) % 60).padStart(2, "0")}:${String(Math.floor(cs / 100) % 60).padStart(2, "0")}.${String(cs % 100).padStart(2, "0")}`; };
// Mətndə ASS idarə simvolları ({ } \) olmasın: «{» etiket açır, «\» əmr başlayır.
const assText = s => clean(s).replace(/\\/g, "/").replace(/\{/g, "(").replace(/\}/g, ")");
const circle = r => { const k = Math.round(r * 0.5523), d = 2 * r; return `m ${r} 0 b ${r + k} 0 ${d} ${r - k} ${d} ${r} b ${d} ${r + k} ${r + k} ${d} ${r} ${d} b ${r - k} ${d} 0 ${r + k} 0 ${r} b 0 ${r - k} ${r - k} 0 ${r} 0`; };
const rect = (w, h) => `m 0 0 l ${w} 0 ${w} ${h} 0 ${h}`;

// Abunə çağırışı — xəbər, maraqlı və hava videosunda eyni (video-hava.cjs də bunları işlədir). Videodakı yazı basılmır: abunə düyməsi
// şəbəkənin özünündür (Instagram, Facebook və YouTube-da adımızın yanında, TikTok-da şəklimizin üstündə «+»). Sahib 2026-11-26: «abunə ol
// yazısını elə et üstünə basanda hansı sos şəbəkədədirsə orada abunə olsun» — videonun içində bu mümkün deyil, ona görə videoda
// düymə şəkli yoxdur (əvvəl zolaqda nişan və sonluqda «ABUNƏ OL» düyməsi idi, basılmırdı): sonluqda vəd və həmin düyməni göstərən
// ipucu (profil video.abune_ipucu). Basılan keçid paylaşım mətnindədir: Instagram və TikTok «@8ulduz.az», YouTube abunə pəncərəsi.
const SUB_TEXT = dil("az").video.abune_ipucu;
const subText = () => dil().video.abune_ipucu;
// Sonluq: üstdə növün vədi (ağ), ortada ipucu (narıncı, ən çox 2 sətir), altda sayt sətri (alt — hazır ASS mətni).
function subOutro(dlg, out, D, y, tur, alt) {
  dlg(3, out, D, "Outro", `{\\pos(540,${y - 170})\\fad(300,0)\\1c${assColor(COLOR.white)}}${assText(abune(tur).ved)}`);
  dlg(3, out, D, "Outro", `{\\pos(540,${y})\\fad(300,0)\\fs50\\1c${assColor(COLOR.orange)}}${wrap(subText(), 50, "medium", TEXT_W).map(assText).join("\\N")}`);
  dlg(3, out, D, "Outro", `{\\pos(540,${y + 170})\\fad(300,0)\\fs48}${alt}`);
}

// Görüntülü video — aşağı blok (sahib, 2026-11-26: «videolarda yazı və logo Baku WS bənzəri olsun eynisi yox. hazırda videonun üstünü
// örtür»; həmin gün Baku WS-in üç Reels şəkli ilə: «çox sadə edibsən … rənglər, loqo bizə məxsus olsun, lakin format eyni bu
// şəkildəkilər kimi olsun, azca fərqlilik qat»). Görüntü bütün kadrı tutur və yuxarısı açıqdır (brend zolağı yoxdur). Aşağıda görüntü
// tünd göyə keçir, keçidin üstündə blok: loqo və bölmə nişanı, başlıq (dırnaqdakı ifadə və rəqəm narıncı), sözbəsöz altyazı; solda
// yuxarıdan enib dairəvi küncdən sağa dönən narıncı xətt, altında tarix və mənbə. Baku WS-dən fərqi: rəng (onlarda qara və qızılı),
// xəttin üfüqi hissəsi videonun gediş xəttidir (dolur), loqonun yanında bölmə nişanı, sözbəsöz altyazı və səs.
// Blok aşağıdan qurulur (blok()): xəttin üfüqi hissəsi y LF.lineY-də, mənbə sətri onun altında — hamısı y 1480-ə qədər (tam ekranda
// aşağıda Reels yazısı, lentin 4:5 kəsiyi y 1635-ə qədərdir); sağda Reels düymələrinə görə mətn x ≤ W − X0.
const LF = { lineY: 1424, lineX: 60, textX: 100, thick: 6, corner: 40, logoH: 56, logoGap: 24, headGap: 20, capGap: 20, srcGap: 18,
  sizes: [68, 64, 60, 56, 52], headMaxH: 3 * 64, fade: 170, fadeStep: 42, fadeLayers: 16 };
const FOOT_W = W - X0 - LF.textX;     // blokda mətnin eni (908)
const LH = 1.17;                       // Roboto: sətrin hündürlüyü ≈ 1,17 × ölçü (libass)
// Blokun yerləri (başlığın sətir sayına görə): altyazıya həmişə 2 sətirlik yer var — başlıq və loqo videonun ortasında yerindən oynamır.
function blok(p) {
  const capH = Math.round(CAPF.lines * CAPF.size * LH);
  const capTop = LF.lineY - LF.capGap - capH;
  const headBottom = capTop - LF.headGap;
  const headTop = headBottom - Math.round(p.head.lines.length * p.head.size * LH);
  const logoY = headTop - LF.logoGap - LF.logoH;
  return { capTop, headTop, headBottom, logoY, lineTop: logoY - 8, fadeTop: logoY - LF.fade };
}
// Dairəvi küncü olan «L» xətt (ASS forması, qalınlıq t, künc radiusu r): (x, y1)-dən aşağı (x, y2)-yə, oradan sağa (x2, y2)-yə.
function kuncXett(x, y1, y2, x2, t = LF.thick, r = LF.corner) {
  const k = 0.5523, q = r - t, f = v => Math.round(v * 10) / 10;
  return `m ${x} ${y1} l ${x} ${y2 - r} b ${x} ${f(y2 - r + k * r)} ${f(x + r - k * r)} ${y2} ${x + r} ${y2} l ${x2} ${y2} ${x2} ${y2 - t} ${x + r} ${y2 - t} `
    + `b ${f(x + r - k * q)} ${y2 - t} ${x + t} ${f(y2 - r + k * q)} ${x + t} ${y2 - r} l ${x + t} ${y1}`;
}
// Başlığın vurğusu: dırnaq içindəki ifadə («…», "…", “…”) və rəqəm (yanındakı sözlə: «600 hektar», «5 kəndin») narıncı, qalanı ağ.
function vurgu(lines, on = assColor(COLOR.orange), off = assColor(COLOR.white)) {
  const text = lines.join(" "), lit = new Array(text.length).fill(false), PAIR = { "«": "»", "“": "”", "„": "“", "\"": "\"" };
  for (let i = 0, close = null; i < text.length; i++) {
    if (close) { lit[i] = true; if (text[i] === close) close = null; continue; }
    if (PAIR[text[i]] && text.indexOf(PAIR[text[i]], i + 1) > i) { close = PAIR[text[i]]; lit[i] = true; }
  }
  for (const m of text.matchAll(/(?<![\p{L}\p{N}])\d[\d.,]*(?:\s*%|\s+\p{L}+)?/gu)) for (let i = m.index; i < m.index + m[0].length; i++) lit[i] = true;
  const esc = ch => (ch === "\\" ? "/" : ch === "{" ? "(" : ch === "}" ? ")" : ch);
  let k = 0;
  return lines.map(line => {
    let out = "", cur = false;
    for (const ch of line) { const v = lit[k++]; if (v !== cur) { out += `{\\1c${v ? on : off}}`; cur = v; } out += esc(ch); }
    k++;   // sətirlər arasındakı boşluq
    return out;
  });
}
// Görüntülü videonun yazıları (ass): keçid, xətt, blok, altyazı, sonluq.
function assFootage(p, tl, dlg) {
  const D = tl.duration, out = tl.outro[0], b = blok(p), white = assColor(COLOR.white), lit = assColor(COLOR.orange);
  const ms = x => Math.max(0, Math.round(x * 1000)), fade = `\\fad(250,300)`, x = LF.textX;
  // Keçid: tünd göyün bir-birinin üstünə düşən yumşaq qatları (hər biri ~14%) — görüntü aşağıya doğru tündləşir, blok oxunur.
  for (let i = 0; i < LF.fadeLayers; i++) {
    const y = b.fadeTop + i * LF.fadeStep;
    if (y >= H) break;
    dlg(0, 0, D, "Shape", `{\\an7\\pos(0,${y})\\p1\\bord0\\shad0\\blur24\\1c${assColor(COLOR.bg)}\\1a&HDB&}${rect(W, H - y + 40)}`);
  }
  // Sonluq: bütün ekran tündləşir (vəd, ipucu, sayt).
  dlg(1, out, D, "Shape", `{\\an7\\pos(0,0)\\p1\\bord0\\shad0\\1c${assColor(COLOR.bg)}\\1a&H18&\\fad(300,0)}${rect(W, H)}`);
  // Künc xətti: zəif iz başdan sona, üstündə dolan (gediş) — şaquli hissə və künc başdan doludur, üfüqi hissə video boyu sağa dolur.
  const L2 = kuncXett(LF.lineX, b.lineTop, LF.lineY, W - X0), full = LF.lineX + LF.corner + LF.thick;
  dlg(2, 0, out + 0.3, "Shape", `{\\an7\\pos(0,0)\\p1\\bord0\\shad0\\1c${lit}\\1a&HA0&${fade}}${L2}`);
  dlg(2, 0, out + 0.3, "Shape", `{\\an7\\pos(0,0)\\p1\\bord0\\shad0\\1c${lit}\\clip(0,0,${full},${H})\\t(0,${ms(out)},\\clip(0,0,${W - X0},${H}))${fade}}${L2}`);
  // Loqo şəkli ffmpeg-də (logoAt) b.logoY-dədir; yanında «.az», sonra bölmə nişanı.
  const lw = Math.round(LOGO.w * LF.logoH / LOGO.h), az = 50;
  dlg(3, 0, out + 0.3, "Brand", `{\\an1\\pos(${x + lw - 3},${b.logoY + LF.logoH + 3})\\fs${az}${fade}}.az`);
  dlg(3, 0, out + 0.3, "Chip", `{\\an4\\pos(${Math.round(x + lw + textWidth(".az", az, "black") + 30)},${b.logoY + LF.logoH / 2})\\fs34\\bord10${fade}}${assText(p.label)}`);
  // Başlıq: blokun içində, vurğulu; kölgə ilə (açıq görüntüdə də oxunsun).
  dlg(3, 0, out + 0.3, "Head", `{\\an7\\move(${x},${b.headTop + 20},${x},${b.headTop},0,300)\\fad(120,300)\\shad2\\4c${assColor(COLOR.bar)}\\4a&H60&}${vurgu(p.head.lines).join("\\N")}`);
  // Tarix və mənbə: xəttin altında, kiçik.
  const alt = [p.when, p.source].filter(Boolean).map(assText).join(" · ");
  if (alt) dlg(3, 0, out + 0.3, "Small", `{\\an7\\pos(${x},${LF.lineY + LF.srcGap})\\fs30${fade}}${alt}`);
  // Altyazılar: başlığın altında, qutusuz; deyilən söz narıncı yanır (sözbəsöz).
  tl.chunks.forEach((c, i) => {
    const until = i + 1 < tl.chunks.length ? tl.chunks[i + 1].at[0] : out;
    const times = wordTimes(c.text, c.at[0], c.at[1]);
    let k = 0;
    const lines = wrap(c.text, CAPF.size, "medium", CAPF.w).map(line => line.split(" ").filter(Boolean).map(w => {
      const [, a, e] = times[k++] || [w, c.at[0], c.at[1]], t1 = ms(a - c.at[0]), t2 = ms(e - c.at[0]);
      return `{\\1c${white}\\t(${t1},${t1 + 60},\\1c${lit})\\t(${t2},${t2 + 60},\\1c${white})}${assText(w)}`;
    }).join(" "));
    dlg(4, c.at[0], until, "Cap", `{\\an7\\pos(${x},${b.capTop})\\fad(180,120)\\shad1\\4c${assColor(COLOR.bar)}\\4a&H60&}${lines.join("\\N")}`);
  });
  subOutro(dlg, out, D, L.outroY, p.tur, `${assText(dil().video.etrafli)} {\\1c${lit}}8ulduz{\\1c${white}}.az`);
}

// Görüntüsüz video (klip tapılmayanda): tünd göy fon, yuxarıda brend zolağı və gediş xətti, bölmə, başlıq, qutuda altyazı, mənbə.
function assTund(p, tl, dlg) {
  const D = tl.duration, out = tl.outro[0];
  // Fon: tünd göy üstündə yavaş hərəkət edən iki yumşaq işıq (videonun canlı görünməsi üçün; şəkil deyil, forma).
  dlg(0, 0, D, "Shape", `{\\an5\\move(180,640,280,760)\\p1\\bord0\\shad0\\1c${assColor(COLOR.blue)}\\1a&HA8&\\blur90}${circle(520)}`);
  dlg(0, 0, D, "Shape", `{\\an5\\move(960,1560,880,1460)\\p1\\bord0\\shad0\\1c${assColor(COLOR.blue2)}\\1a&HDC&\\blur90}${circle(440)}`);
  // Yuxarı zolaq: başdan sona. Loqo şəkli ffmpeg-də bu zolağın üstünə qoyulur, yanında «.az» — birlikdə «8ULDUZ.az».
  dlg(1, 0, D, "Shape", `{\\an7\\pos(0,${L.barY})\\p1\\bord0\\shad0\\1c${assColor(COLOR.bar)}}${rect(W, L.barH)}`);
  dlg(2, 0, D, "Brand", `{\\an1\\pos(${logoX() + logoW() - 4},${logoY() + L.logoH + 4})\\fs72}.az`);
  // Gediş xətti: videonun nə qədəri qalıb (xəbər Reels-lərində adət).
  const py = L.barY + L.barH;
  dlg(2, 0, D, "Shape", `{\\an7\\pos(0,${py})\\p1\\bord0\\shad0\\1c${assColor(COLOR.orange)}\\clip(0,${py},1,${py + 8})\\t(0,${Math.round(D * 1000)},\\clip(0,${py},${W},${py + 8}))}${rect(W, 8)}`);
  // Bölmə, vaxt, başlıq, mənbə: sonluğa qədər.
  const fade = `\\fad(250,300)`;
  dlg(3, 0, out + 0.3, "Chip", `{\\an4\\pos(${X0 + 12},${L.chipY + 30})${fade}}${assText(p.label)}`);
  if (p.when) dlg(3, 0, out + 0.3, "When", `{\\an4\\pos(${Math.round(X0 + textWidth(p.label, 40, "black") + 64)},${L.chipY + 30})${fade}}${assText(p.when)}`);
  dlg(3, 0, out + 0.3, "Head", `{\\an7\\move(${X0},${L.headY + 24},${X0},${L.headY},0,300)\\fad(120,300)}${p.head.lines.map(assText).join("\\N")}`);
  if (p.source) dlg(3, 0, out + 0.3, "Small", `{\\an7\\pos(${X0},${L.srcY})${fade}}${assText(p.source)}`);
  // Altyazılar: başlığın altında (başlığın hündürlüyünə görə), səslə eyni anda.
  const capY = Math.min(L.capMaxY, Math.max(L.capMinY, L.headY + p.head.lines.length * p.head.size + 64));
  // Hər altyazı növbətisi başlayanda (sonuncu — sonluq başlayanda) çəkilir: səsli videoda hissələr bitişikdir, üst-üstə düşməsinlər.
  // Deyilən söz narıncı yanır, deyilmiş söz yenə ağ olur (Reels/Shorts altyazısı; sahib 2026-11-23: «tam professional»):
  // hər sözün öz \t keçidi var, vaxt sətrin başlanğıcından ms ilə (wordTimes). Qutunun ölçüsü dəyişmir: yalnız rəng.
  const white = assColor(COLOR.white), lit = assColor(COLOR.orange), ms = x => Math.max(0, Math.round(x * 1000));
  tl.chunks.forEach((c, i) => {
    const until = i + 1 < tl.chunks.length ? tl.chunks[i + 1].at[0] : out;
    const times = wordTimes(c.text, c.at[0], c.at[1]);
    let k = 0;
    const lines = wrap(c.text, CAP_SIZE, "medium", CAP_W).map(line => line.split(" ").filter(Boolean).map(w => {
      const [, a, b] = times[k++] || [w, c.at[0], c.at[1]], t1 = ms(a - c.at[0]), t2 = ms(b - c.at[0]);
      return `{\\1c${white}\\t(${t1},${t1 + 60},\\1c${lit})\\t(${t2},${t2 + 60},\\1c${white})}${assText(w)}`;
    }).join(" "));
    dlg(4, c.at[0], until, "Cap", `{\\an7\\pos(${X0 + CAP_PAD},${capY + CAP_PAD})\\fad(180,120)}${lines.join("\\N")}`);
  });
  // Sonluq: vəd, abunə ipucu, altında sayt.
  subOutro(dlg, out, D, L.outroY, p.tur, `${assText(dil().video.etrafli)} {\\1c${lit}}8ulduz{\\1c${white}}.az`);
}

function ass(p, tl) {
  const D = tl.duration, end = assTime(D), out = tl.outro[0];
  const sc = hex => `&H00${assColor(hex).slice(2, 8)}`;   // üslubda rəng: &HAABBGGRR
  const st = (name, size, color, bold, extra = {}) => {
    const o = { outline: 0, outlineColor: "000000", border: 1, align: 7, ...extra };
    return `Style: ${name},${FONT}${extra.font || ""},${size},${sc(color)},${sc(color)},${sc(o.outlineColor)},${sc("000000")},${bold ? -1 : 0},0,0,0,100,100,0,0,${o.border},${o.outline},0,${o.align},${X0},${X0},0,1`;
  };
  const styles = [
    st("Shape", 10, COLOR.white, false),
    st("Brand", 96, COLOR.white, true, { font: " Black" }),
    st("Chip", 40, COLOR.bg, true, { font: " Black", border: 3, outline: 12, outlineColor: COLOR.orange }),
    st("When", 40, COLOR.gray, false),
    st("Head", p.head.size, COLOR.white, true, { font: " Black" }),
    // Altyazı: tünd fonda qutuda, görüntülü videonun blokunda qutusuz (CAPF).
    p.footage ? st("Cap", CAPF.size, COLOR.white, false, { font: " Medium" })
      : st("Cap", CAP_SIZE, COLOR.white, false, { font: " Medium", border: 3, outline: CAP_PAD, outlineColor: COLOR.box }),
    st("Small", 36, COLOR.gray, false),
    st("Outro", 60, COLOR.gray, false, { font: " Medium", align: 5 }),
  ];
  const ev = [];
  const dlg = (layer, from, to, style, text) => ev.push(`Dialogue: ${layer},${assTime(from)},${assTime(to)},${style},,0,0,0,,${text}`);
  if (p.footage) assFootage(p, tl, dlg); else assTund(p, tl, dlg);
  return ["[Script Info]", "ScriptType: v4.00+", `PlayResX: ${W}`, `PlayResY: ${H}`, "WrapStyle: 0", "ScaledBorderAndShadow: yes", "YCbCr Matrix: TV.709", "",
    "[V4+ Styles]",
    "Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding",
    ...styles, "", "[Events]", "Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text", ...ev, ""].join("\n");
}
// Loqo (assets/logo.png, 933×212: «8» nişanı + «ULDUZ»), zolağın solunda.
const LOGO = { file: "assets/logo.png", w: 933, h: 212 };
const logoX = () => X0;
const logoY = () => L.barY + Math.round((L.barH - L.logoH) / 2);
const logoW = () => Math.round(LOGO.w * L.logoH / LOGO.h);

// ffmpeg arqumentləri. Yazılar RGB-də çəkilir (narıncı-göy kənarları yuv420-də yayılmasın), sonda yuv420p.
// Kadr planı (sahib, 2026-11-23: «tam professional kimi işlə»): kəsim danışığın sərhədindədir — başlıq (səssiz) və birinci altyazı bir kadr, sonra hər
// altyazı hissəsi bir kadr, sonluq sonuncunun davamı. Xəbər montajında kadr 3–6 s-dir; əvvəl 45 s-lik videoda 5 kadr (~9 s) idi.
// SHOT_MIN-dən qısa hissə qonşusuna birləşir, SHOT_MAX-dan uzunu bərabər bölünür. Kliplər sıra ilə gedir (Gemini-nin ifadələri
// diktor mətninin cümlə sırasındadır): çatmasa təkrarlanır, təkrarda klipin işlənməmiş yerindən (ss) — eyni kadr iki dəfə görünməsin.
// Klip: fayl yolu və ya { file, w, h, dur }. Hər klip kadrı tam doldurur (sahib, 2026-11-24: «bu videoların hündürlüyünü tam ölçüdə
// etsək daha baxımlı olar. üstündə yazılar olsa da video tam kart boyu olmalıdır»). Əvvəl (2026-11-22) üfüqi klip tam enində ortada,
// arxada bulanıq nüsxəsi ilə idi, çünki ortadan kəsəndə mövzu düşürdü (sarayın yerinə göy) və 1080p klip 1,8 dəfə böyüyüb bulanıqlaşırdı.
// İndi ikisi də başqa yolla həll olunur: kəsim ortadan yox, kadrın hərəkət və detal olan yerindəndir (focusX, hər kadr üçün ayrıca —
// «auto-reframe»), üfüqi klipin isə ən böyük nüsxəsi (4K) yüklənir (video-ssenari.cjs). Ölçü bilinməsə və ya ffmpeg ölçə bilməsə — ortadan.
const SHOT_MIN = 2.6, SHOT_MAX = 6.5, KLIP_SAQULI = 0.8;
const r2 = x => Math.round(x * 100) / 100;
function shotBounds(tl) {
  const D = tl.duration, b = [0];
  for (const c of tl.chunks || []) if (c.at[0] > b[b.length - 1] + 0.01 && c.at[0] < D - 0.01) b.push(c.at[0]);
  b.push(D);
  let seg = b.slice(1).map((e, i) => [b[i], e]);
  // Qısa hissə: əvvəlkinə (birincidirsə növbətiyə) birləşir.
  for (let i = 0; i < seg.length && seg.length > 1;) {
    if (seg[i][1] - seg[i][0] >= SHOT_MIN) { i++; continue; }
    if (i > 0) { seg[i - 1][1] = seg[i][1]; seg.splice(i, 1); } else { seg[1][0] = seg[0][0]; seg.splice(0, 1); }
  }
  // Uzun hissə: bərabər bölünür (altyazısız fasilə, sonluq).
  seg = seg.flatMap(([s, e]) => { const n = Math.ceil((e - s) / SHOT_MAX - 1e-9); return Array.from({ length: n }, (_, k) => [s + (e - s) * k / n, s + (e - s) * (k + 1) / n]); });
  return seg;
}
function shotPlan(clips, tl) {
  const list = clips.map(c => (typeof c === "string" ? { file: c } : c));
  if (!list.length) return [];
  const seg = shotBounds(tl), used = list.map(() => 0);
  let t = 0;
  return seg.map(([s, e], k) => {
    const d = k === seg.length - 1 ? r2(tl.duration - t) : r2(e - s);
    t = r2(t + d);
    const i = k % list.length, c = list[i];
    // Təkrarda klipin işlənməmiş yerindən; uzunluğu bilinmirsə və ya qalan yer çatmırsa — əvvəldən (-stream_loop dövrə vurur).
    const ss = c.dur > 0 && used[i] + d <= c.dur - 0.2 ? r2(used[i]) : 0;
    used[i] = ss + d;
    return { ...c, d, ss };
  });
}
const fitsWide = c => c.w > 0 && c.h > 0 && c.w / c.h > KLIP_SAQULI;

// Ağıllı kəsim (auto-reframe): klipin kiçik boz nüsxəsində (fw×fh, ardıcıl kadrlar) hər sütunun «enerjisi» — iki kadr arasındakı fərq
// (hərəkət) və qonşu nöqtələrin fərqi (detal: bina, adam, yazı; boş göy və divar azdır). 9:16 pəncərə (eni frac) enerjinin ən çox olduğu
// yerə qoyulur; ortaya yüngül üstünlük var (enerji bərabərdirsə kadr ortadan, kəsim kənara sıçramır). Nəticə: pəncərənin ortası, 0…1.
function focusX(buf, fw, fh, frac) {
  const n = Math.floor(buf.length / (fw * fh)), ww = Math.max(1, Math.min(fw, Math.round(fw * frac)));
  if (!(n > 0) || ww >= fw) return 0.5;
  const col = new Float64Array(fw);
  for (let k = 0; k < n; k++) {
    const o = k * fw * fh, p = o - fw * fh;
    for (let y = 0; y < fh; y++) for (let x = 1; x < fw; x++) {
      const i = o + y * fw + x;
      col[x] += 0.5 * Math.abs(buf[i] - buf[i - 1]) + (k ? Math.abs(buf[i] - buf[p + y * fw + x]) : 0);
    }
  }
  let sum = 0, best = -1, at = (fw - ww) >> 1;
  for (let x = 0; x < ww; x++) sum += col[x];
  const total = col.reduce((a, b) => a + b, 0);
  if (!(total > 0)) return 0.5;
  for (let s = 0; s + ww <= fw; s++) {
    if (s) sum += col[s + ww - 1] - col[s - 1];
    const mid = (s + ww / 2) / fw, score = sum * (1 - 0.3 * Math.abs(mid - 0.5));
    if (score > best + 1e-9) { best = score; at = s; }
  }
  return Math.round(((at + ww / 2) / fw) * 1000) / 1000;
}
// Kadrın hissəsini (ss, d) ffmpeg ilə kiçik boz kadrlara çevirib focusX. Alınmasa ortası.
function focusOf(c, opt = {}) {
  if (!fitsWide(c)) return 0.5;
  const fw = 160, fh = Math.max(2, Math.round(fw * c.h / c.w / 2) * 2), frac = (c.h * W / H) / c.w;
  try {
    const r = spawnSync("ffmpeg", ["-v", "error", ...(c.ss > 0 ? ["-ss", c.ss.toFixed(2)] : []), "-t", String(Math.min(c.d || 4, 6)), "-i", c.file,
      "-vf", `fps=4,scale=${fw}:${fh},format=gray`, "-f", "rawvideo", "pipe:1"], { maxBuffer: 32 << 20, timeout: opt.timeout || 60000, cwd: opt.cwd });
    return r.status === 0 && r.stdout?.length ? focusX(r.stdout, fw, fh, frac) : 0.5;
  } catch { return 0.5; }
}

function clipFilter(c, i) {
  const head = `[${i}:v]fps=${FPS},trim=duration=${c.d.toFixed(2)},setpts=PTS-STARTPTS`;
  if (!fitsWide(c)) return `${head},scale=${W}:${H}:force_original_aspect_ratio=increase:flags=bicubic,crop=${W}:${H},setsar=1[c${i}]`;
  // Üfüqi (və kvadrat) klip: hündürlüyü kadrın hündürlüyünə, 9:16 pəncərə ağıllı kəsimin yerində (cx).
  const sw = Math.round(H * c.w / c.h / 2) * 2, cx = c.cx >= 0 && c.cx <= 1 ? c.cx : 0.5;
  const x = Math.max(0, Math.min(sw - W, Math.round(cx * sw - W / 2)));
  return `${head},scale=${sw}:${H}:flags=bicubic,crop=${W}:${H}:${x}:0,setsar=1[c${i}]`;
}

// p (görüntülü video): loqo şəkli aşağı blokdadır (blok().logoY, LF.logoH); p yoxdursa yuxarı zolaqdadır.
function ffmpegArgs({ tl, assFile, logo, voiceFile, out, clips = [], focus = null, p = null }) {
  const D = tl.duration.toFixed(2);
  const plan = shotPlan(clips, tl).map(c => (focus && fitsWide(c) ? { ...c, cx: focus(c) } : c));
  const args = ["-hide_banner", "-loglevel", "error", "-y"];
  let bg;
  if (plan.length) {
    // Hər klip kadrı doldurur (clipFilter; üfüqi klip ağıllı kəsimlə); 30 kadr/s, bir az tündləşdirilir (yazı oxunsun).
    plan.forEach(c => args.push("-stream_loop", "-1", ...(c.ss > 0 ? ["-ss", c.ss.toFixed(2)] : []), "-t", c.d.toFixed(2), "-i", c.file));
    bg = plan.map((c, i) => clipFilter(c, i)).join(";")
      + `;${plan.map((_, i) => `[c${i}]`).join("")}concat=n=${plan.length}:v=1:a=0,eq=brightness=-0.04:saturation=0.95,trim=duration=${D},format=rgb24`;
  } else {
    args.push("-f", "lavfi", "-i", `color=c=0x${COLOR.bg}:s=${W}x${H}:r=${FPS}:d=${D}`);
    bg = "[0:v]format=rgb24";
  }
  const li = plan.length || 1, ai = li + 1;
  args.push("-i", logo);
  let audio;
  if (voiceFile) {
    args.push("-i", voiceFile);
    const c = tl.voiceCut, ms = s => Math.round(s * 1000), lead = tl.lead ?? LEAD_S;
    // Əsas hissə + (altyazı düşübsə, sürüşdürülmüş) sonluq səsi; lead qədər gecikmə (LEAD_S).
    audio = c && c.outroAt + 0.01 < c.outroFrom
      ? `[${ai}:a]asplit=2[m][o];[m]atrim=0:${(c.keepUntil - lead).toFixed(3)},asetpts=PTS-STARTPTS[m1];[o]atrim=${(c.outroFrom - lead).toFixed(3)},asetpts=PTS-STARTPTS,adelay=${ms(c.outroAt - c.keepUntil)}:all=1[o1];[m1][o1]concat=n=2:v=0:a=1,adelay=${ms(lead)}:all=1,`
      : `[${ai}:a]adelay=${ms(lead)}:all=1,`;
    audio += `apad,atrim=0:${D},aresample=48000,aformat=sample_fmts=fltp:channel_layouts=stereo,loudnorm=I=-16:TP=-1.5:LRA=11,aresample=48000[a]`;
  } else {
    args.push("-f", "lavfi", "-t", D, "-i", "anullsrc=channel_layout=stereo:sample_rate=48000");
    audio = `[${ai}:a]aformat=sample_fmts=fltp:channel_layouts=stereo[a]`;
  }
  const lg = p?.footage && plan.length ? { x: LF.textX, y: blok(p).logoY, h: LF.logoH } : { x: logoX(), y: logoY(), h: L.logoH };
  // Görüntülü videoda loqo blokla birlikdə sonluğa qədərdir (sonluqda «Ətraflı: 8ulduz.az» qalır, loqo onun yerinə düşməsin).
  const until = lg.y !== logoY() ? `:enable='lt(t,${(tl.outro[0] + 0.3).toFixed(2)})'` : "";
  const video = `${bg},ass=${assFile}[t];[${li}:v]scale=-1:${lg.h}:flags=lanczos,format=rgba[lg];[t][lg]overlay=${lg.x}:${lg.y}:format=rgb${until},format=yuv420p[v]`;
  args.push("-filter_complex", `${video};${audio}`, "-map", "[v]", "-map", "[a]", "-t", D,
    "-c:v", "libx264", "-preset", "medium", "-profile:v", "high", "-level:v", "4.1", "-crf", "21", "-maxrate", "8M", "-bufsize", "16M",
    "-r", String(FPS), "-g", String(2 * FPS), "-keyint_min", String(2 * FPS), "-sc_threshold", "0", "-pix_fmt", "yuv420p",
    "-colorspace", "bt709", "-color_primaries", "bt709", "-color_trc", "bt709", "-color_range", "tv",
    "-c:a", "aac", "-b:a", "128k", "-ar", "48000", "-ac", "2", "-movflags", "+faststart",
    // Öz videomuzun nişanı: TikTok yükləyicisi (tiktok.cjs) yalnız bu nişanlı faylı göndərir — X/reels videoları getməsin.
    "-metadata", "comment=8ulduz.az", out);
  return args;
}

function run(cmd, args, opt = {}) {
  const r = spawnSync(cmd, args, { encoding: "utf8", maxBuffer: 64 << 20, timeout: opt.timeout || 300000, cwd: opt.cwd, env: opt.env || process.env });
  if (r.error) throw new Error(`${cmd}: ${r.error.message}`);
  if (r.status !== 0) throw new Error(`${cmd} ${r.status}: ${String(r.stderr || r.stdout).trim().slice(-800)}`);
  return r.stdout;
}

// Səs: video_ses.py (profilin Edge səsi — az: Babək; alınmasa profilin ehtiyatı — az: SARA). Alınmasa null — video səssiz hazırlanır.
function voice(p, dir, log) {
  const parts = path.join(dir, "ses-hisseler.json"), wav = path.join(dir, "ses.wav"), times = path.join(dir, "ses.json");
  // max_s: səs bundan uzun olsa video_ses.py (Babək) bir az tez oxuyur — sondakı altyazılar düşməsin (timeline: səsdən sonra
  // GAP_S + sonluğun artığı + 0,3 s).
  // dil: video_ses.py səsi (Edge səsi, temp, mətnin hazırlanması, ehtiyat) eyni profildən götürür.
  fs.writeFileSync(parts, JSON.stringify({ parts: p.say, max_s: MAX_S - LEAD_S - 1, dil: dil().kod, ...(Array.isArray(p.davam) && p.davam.length === p.say.length ? { davam: p.davam } : {}) }));
  try {
    run(process.env.VIDEO_PYTHON || "python3", [path.join(__dirname, "video_ses.py"), parts, wav, times], { timeout: 600000 });
    const v = JSON.parse(fs.readFileSync(times, "utf8"));
    if (!Array.isArray(v.parts) || v.parts.length !== p.say.length) throw new Error("səs hissələri uyğun deyil");
    return { file: wav, ...v };
  } catch (e) {
    log(`video: səs alınmadı, səssiz hazırlanır — ${String(e.message || e).slice(0, 300)}`);
    return null;
  }
}

// Jurnal üçün səsin adı: vaxtlar.json «motor» — profilin Edge səsi (az: babek → «Babək») və ya ehtiyat SARA.
const sesAdi = m => (m === "sara" ? "SARA" : m === dil().ses.motor ? dil().ses.ad : String(m || "?"));

// <çıxış>.json-dakı xəbər sahələri (TikTok yükləyicisi, PR 8ulduz/8ulduz#293, bunları oxuyur: text — mətn, own — öz videomuzdur).
// own yalnız bu modulun hazırladığı videoda olur: montaj, mətn, səs və dizayn bizimdir; görüntü bank klipi, sahibin görüntüsü və ya
// (2026-11-26-dan, sahibin qərarı) mənbə saytının öz videosudur — mənbə videoda və mətndə göstərilir.
function storyFields(a) {
  const text = clean(a.text || "") || clean(a.summary || "");
  return { id: a.id, own: true, title: clean(a.title), summary: clean(a.summary || ""), text, source: a.source || "", sourceUrl: a.sourceUrl || "",
    // lang: videonun dili (profil) — yükləyicilər (youtube.cjs, tiktok.cjs) mətni bu dilin profilindən yazır.
    category: a.category || "", lang: dil().kod, publishedAt: a.publishedAt || "",
    // Maraqlı video (video-maraqli.cjs): növ və saytın keçidi YouTube/TikTok yükləyicisinə (xəbər deyil, paylaşma səhifəsi yoxdur).
    ...(a.kind === "maraqli" ? { kind: "maraqli", url: a.url || "https://8ulduz.az/" } : {}),
    // Dünya videosu (video-dunya.cjs): saytda ayrıca xəbər səhifəsi yoxdur — keçid «Dünya» bölməsinədir.
    ...(a.kind === "dunya" ? { kind: "dunya", url: a.url || "https://8ulduz.az/bolme/dunya/" } : {}),
    // X videosu («Çox baxılan», video-dunya.cjs xHazirla): keçid saytın Videolentinədir.
    ...(a.kind === "x" ? { kind: "x", url: a.url || "https://8ulduz.az/#/videolent" } : {}),
    ...(Array.isArray(a.hashtags) && a.hashtags.length ? { hashtags: a.hashtags.slice(0, 3) } : {}) };   // YouTube/TikTok yükləyicisi oxuyur
}

// Mənbənin öz videosu (video-menbe.cjs, sahib 2026-11-26): fayl oxunursa, videodursa və kifayət qədər uzun və iridirsə fon odur.
// Telefon çəkilişinin fırlanma nişanı nəzərə alınır (ffmpeg kadrı özü çevirir: ölçü də çevrilmiş olmalıdır).
const MENBE_MIN_S = 4, MENBE_MIN_PX = 240;
function menbeKlip(file) {
  try {
    const j = JSON.parse(run("ffprobe", ["-v", "error", "-show_entries", "format=duration:stream=codec_type,width,height:stream_tags=rotate:stream_side_data=rotation", "-of", "json", file]));
    const v = (j.streams || []).find(x => x.codec_type === "video");
    if (!v) return null;
    const rot = Math.abs(Number(v.side_data_list?.find(d => d.rotation != null)?.rotation ?? v.tags?.rotate ?? 0)) % 180 === 90;
    const w = rot ? v.height : v.width, h = rot ? v.width : v.height, dur = Number(j.format?.duration) || 0;
    return w >= MENBE_MIN_PX && h >= MENBE_MIN_PX && dur >= MENBE_MIN_S ? { file, w, h, dur } : null;
  } catch { return null; }
}

function probe(file) {
  const j = JSON.parse(run("ffprobe", ["-v", "error", "-show_entries", "format=duration,size:stream=codec_type,codec_name,width,height,pix_fmt,r_frame_rate,sample_rate,channels", "-of", "json", file]));
  const v = j.streams.find(s => s.codec_type === "video") || {}, a = j.streams.find(s => s.codec_type === "audio") || {};
  return { duration: Number(j.format.duration), bytes: Number(j.format.size), width: v.width, height: v.height, vcodec: v.codec_name, pix: v.pix_fmt, fps: v.r_frame_rate, acodec: a.codec_name, rate: Number(a.sample_rate), channels: a.channels };
}

// Bir xəbər → mp4 (+ .json, .jpg). opt: { voice: false, log, policy, cats }.
async function render(a, out, opt = {}) {
  const log = opt.log || console.log;
  let policy = opt.policy, cats = opt.cats;
  if (!policy || !cats) {
    const app = require("./topics.cjs").loadApp(ROOT);    // qayda faylı oxunmasa xəta: video olmur
    // Dünya və X videoları (kind): mənbə lentin siyahısında deyil — xarici mənbə qaydası (topics.cjs xariciPozur).
    policy ||= x => (x?.kind === "dunya" || x?.kind === "x" ? app.xariciPozur(x) : app.policyViolation(x));
    cats ||= app.CATS;
  }
  if (policy(a)) throw new Error(`xəbər saytın qaydasından keçmir: ${clean(a.title)}`);
  if (a.text && policy({ ...a, summary: a.text })) throw new Error("izah saytın qaydasından keçmir");
  out = path.resolve(out);
  // Fon klipləri (video-ssenari.cjs goruntu()): çıxış qovluğuna görə yol; olmayan fayl atılır.
  // Ölçü ffprobe ilə oxunur (üfüqi klip ağıllı kəsimlə doldurur, clipFilter); oxunmasa klip ortadan doldurulur.
  const base = opt.base || path.dirname(out);
  let clips = (Array.isArray(a.klipler) ? a.klipler : []).map(f => path.resolve(base, String(f))).filter(f => fs.existsSync(f))
    .map(file => { try { const m = probe(file); return { file, w: m.width || 0, h: m.height || 0, dur: m.duration || 0 }; } catch { return { file }; } });
  let menbe = clean(a.goruntuMenbe) || "Pexels";
  // Mənbənin öz videosu varsa və oxunursa görüntü odur (bank klipləri yalnız ehtiyatdır); videoda «Görüntü: <mənbə>» yazılır.
  const mvFile = a.menbeVideo?.file ? path.resolve(base, String(a.menbeVideo.file)) : "";
  const mv = mvFile && fs.existsSync(mvFile) ? (opt.menbeKlip || menbeKlip)(mvFile) : null;
  if (mv) { clips = [mv]; menbe = clean(a.menbeVideo.kredit) || clean(a.source) || menbe; a = { ...a, goruntuMenbe: menbe }; }
  else if (mvFile) log(`video: mənbənin videosu oxunmadı və ya qısadır — ${clips.length ? "bank klipləri ilə" : "görüntüsüz"}`);
  const p = prepare(a, { cats, footage: clips.length > 0 });
  // klip_boyu (X videosu): video ən azı klipin uzunluğu qədər (həddə qədər) davam edir — baxılan şey görüntünün özüdür.
  if (mv && Number(a.klip_boyu) > 0) p.min_s = Math.min(mv.dur, Number(a.klip_boyu));
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), "video-xeber-"));
  try {
    const wantVoice = opt.voice ?? (a.ses !== false && process.env.VIDEO_SES !== "0");
    const v = wantVoice ? voice(p, dir, log) : null;
    const tl = timeline(p, v);
    fs.writeFileSync(path.join(dir, "video.ass"), ass(p, tl));
    fs.mkdirSync(path.dirname(out), { recursive: true });
    run("ffmpeg", ffmpegArgs({ tl, assFile: "video.ass", logo: path.join(ROOT, LOGO.file), voiceFile: v?.file, out, clips, p, focus: c => focusOf(c, { cwd: dir }) }), { cwd: dir, timeout: 900000 });
    // Örtük: başlıq yerinə oturub (hərəkəti 0,3 s), birinci altyazı hələ yoxdur — səs və altyazı tl.head[1]-də (LEAD_S) başlayır.
    const cover_s = Math.round(Math.min(1.5, Math.max(0.3, tl.head[1] - 0.05)) * 100) / 100;
    const jpg = out.replace(/\.mp4$/i, "") + ".jpg";
    run("ffmpeg", ["-hide_banner", "-loglevel", "error", "-y", "-ss", String(cover_s), "-i", out, "-frames:v", "1", "-q:v", "3", jpg]);
    // kadrlar: önizləmə üçün anlar — başlıq, ilk iki altyazının ortası, sonluq (sosial-video.yml şəkil düzəldir).
    const mid = ([s, e]) => Math.round((s + e) * 50) / 100;
    // Görüntülü videoda hər kadrın (montaj) ortası — montajı və sözbəsöz altyazını bir baxışda yoxlamaq üçün (ən çox 7).
    let t0 = 0;
    const shotMids = shotPlan(clips, tl).map(c => { const m = mid([t0, t0 + c.d]); t0 += c.d; return m; });
    const kadrlar = clips.length
      ? [cover_s, ...shotMids.slice(1, 8).filter(x => x < tl.outro[0]), mid([tl.outro[0], tl.duration])]
      : [cover_s, ...tl.chunks.slice(0, 2).map(c => mid(c.at)), mid([tl.outro[0], tl.duration])];
    const meta = { ...storyFields(a), ...probe(out), cover_s, kadrlar, voice: Boolean(v), ...(v?.motor ? { ses: v.motor } : {}), ...(v ? { oxunan: p.say } : {}), ...(v?.nefes ? { nefes: v.nefes } : {}), parts: 2 + tl.chunks.length, title: p.title,
      ...(mv ? { menbeVideo: true } : {}),
      ...(clips.length ? (shots => ({ goruntu: menbe, klip: new Set(shots.map(s => s.file)).size, kadr: shots.length, kesilen: shots.filter(fitsWide).length }))(shotPlan(clips, tl)) : {}) };
    fs.writeFileSync(out.replace(/\.mp4$/i, "") + ".json", JSON.stringify(meta, null, 1));
    if (opt.keepAss) fs.copyFileSync(path.join(dir, "video.ass"), out.replace(/\.mp4$/i, "") + ".ass");
    log(`video: ${meta.width}×${meta.height}, ${meta.duration.toFixed(1)} s, ${(meta.bytes / 1e6).toFixed(1)} MB, ${tl.chunks.length} altyazı, ${v ? `səsli (${sesAdi(v.motor)})` : "səssiz"}, ${clips.length ? `${meta.kadr} kadr, ${meta.klip} klip (${menbe}; ${meta.kesilen} kadr üfüqi, ağıllı kəsildi)` : "görüntüsüz"} — ${p.title}`);
    return meta;
  } finally {
    fs.rmSync(dir, { recursive: true, force: true });
  }
}

module.exports = { menbeKlip, render, prepare, timeline, ass, ffmpegArgs, shotPlan, shotBounds, wordTimes, clipFilter, focusX, focusOf, blok, vurgu, kuncXett, LF, CAPF, FOOT_W, captionChunks, captionSentences, bodyText, fitHeadline, wrap, textWidth, sourceLine, bakuTime, probe, storyFields,
  W, H, FPS, MIN_S, MAX_S, L, COLOR,
  // Hava videosu (video-hava.cjs) eyni brendi, səsi, altyazını və kodlaşdırmanı işlədir: qayda iki yerdə yazılmır.
  clean, voice, sesAdi, run, assColor, assTime, assText, rect, circle, logoX, logoY, logoW, LOGO, X0, TEXT_W, FONT, CAP_SIZE, CAP_PAD, CAP_W,
  // Abunə çağırışı: üç video növündə eyni sonluq (vəd, ipucu), hər növün öz vədi.
  ABUNE, abune, SUB_TEXT, subOutro };

if (require.main === module) {
  const [src, out] = process.argv.slice(2);
  if (!src || !out) { console.error("İşlədilmə: node .github/scripts/video-xeber.cjs <giriş.json> <çıxış.mp4>"); process.exit(2); }
  render(JSON.parse(fs.readFileSync(src, "utf8")), out, { keepAss: process.env.VIDEO_ASS === "1" })
    .catch(e => { console.error(`video: alınmadı — ${String(e?.message || e)}`); process.exitCode = 1; });
}
