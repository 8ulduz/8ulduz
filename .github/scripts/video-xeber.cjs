// Video xəbər (sahib, 2026-11-22: «Facebook-da video xəbərlər verilsin… İnstagramda videolar verilsin. Videolarda başda 8ulduz.az
// yazılsın»). Bir xəbərdən şaquli qısa video (Reels): saytın rəngləri, yuxarıda başdan sona loqo + «8ulduz.az», böyük başlıq,
// izah cümlə-cümlə altyazı kimi, istəyə görə Azərbaycan səsi (SARA, «Dinlə» serverinin modeli), sonda «Ətraflı: 8ulduz.az».
// Videoda yalnız bizim hazırladığımız və istifadə hüququmuz olan şey var: xəbərin başlığı və izahı (mətn), brend dizaynı, səs və
// (sahib, 2026-11-22: «videogörüntü olsun o xəbərə uyğun») Pixabay/Pexels video bankının pulsuz lisenziyalı klipləri (video-ssenari.cjs).
// Xəbər saytlarının və X-in video/fotosu, musiqi yoxdur (Meta Rights Manager, Content ID riski; docs/sosial-video.md).
//
// İşlədilmə:  node .github/scripts/video-xeber.cjs <giriş.json> <çıxış.mp4>
//   giriş  — data/news.json sətri (id, title, summary, category, source, alts, publishedAt) + istəyə bağlı:
//            text  ekranda və səsdə gedən izah (social.cjs describe(): yalnız tam cümlələr); yoxdursa summary-nin tam cümlələri
//            bolme bölmənin adı (yoxdursa saytın CATS siyahısından)
//            klipler  fon klipləri (çıxış qovluğuna görə yol; video-ssenari.cjs goruntu()). Varsa fon görüntüdür, yoxdursa tünd göy
//                     fon; şaquli klip ekranı doldurur, üfüqi tam enində ortada (arxada bulanıq nüsxəsi)
//            goruntuMenbe  videoda «Görüntü: …» (Pixabay və ya Pexels)
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
"use strict";
const fs = require("fs"), path = require("path"), os = require("os"), { spawnSync } = require("child_process");

const ROOT = path.resolve(__dirname, "../..");
const W = 1080, H = 1920, FPS = 30;
const X0 = 72, TEXT_W = W - 2 * X0;            // sağda Reels düymələri, aşağıda Reels izahı: mətn bu sahədə qalır
const MIN_S = 8, MAX_S = 59;                   // Facebook Reels API 3–90 s; qısa video daha çox sona qədər baxılır
const BODY_MAX = 750;                          // izahın ekranda/səsdə ən çox simvolu (≈ 5–7 cümlə, 35–45 s; sahib 2026-11-22: «4-7 cümlədə olsun. uzun da olsun»)
const LEAD_S = 0.35, GAP_S = 0.25, OUTRO_S = 2.8;
// Rənglər saytdandır: tünd göy fon (og-default.png, app.css --bg), loqonun narıncısı.
const COLOR = { bg: "0B1426", bar: "060D1A", orange: "F5A30A", white: "FFFFFF", gray: "AFC0D8", box: "1A3563", blue: "1E4D8C", blue2: "2563EB" };
// Yerləşmə (piksel, 1080×1920). Lentdə Reels ortadan 4:5-ə kəsilir (y 285…1635), tam ekranda yuxarıda ~170 px, aşağıda ~420 px,
// sağda ~130 px şəbəkənin öz düymələridir: brend və bütün yazılar y 300…1480 arasındadır — loqo lentdə də, tam ekranda da görünür.
const L = { barY: 300, barH: 120, logoH: 80, chipY: 466, headY: 556, headMaxH: 470, capMinY: 860, capMaxY: 1110, srcY: 1404, outroY: 900 };
// Görüntülü video: başlıq yuxarıda yarımşəffaf tünd zolaqda (görüntü ortada açıq qalır), altyazılar aşağıda, mənbə və «Görüntü: Pixabay» altda.
const LF = { headY: 540, headMaxH: 290, sizes: [76, 70, 64, 58, 52], capY: 1150, srcY: 1420 };
const FONT = "Roboto";

const clean = s => String(s ?? "").replace(/<[^>]+>/g, " ").replace(/\s+/g, " ").replace(/ ([.,!?;:…])/g, "$1").trim();
const MONTHS = ["yanvar", "fevral", "mart", "aprel", "may", "iyun", "iyul", "avqust", "sentyabr", "oktyabr", "noyabr", "dekabr"];

// Mətnin təxmini eni (piksel). ASS-də şrift ölçüsü sətir hündürlüyüdür: Roboto Black və Medium-da ölçülmüş en ≈ 0,71 × ölçü ×
// cədvəl (2026-11-22, CI kadrı: «nəticəsində 5 kəndin» 96-lıq başlıqda 676 px). En ~4% artıq sayılır: sətri özümüz bölürük (\N),
// libass sətri əlavə bölməsin — bölsə, başlıq altyazının üstünə düşər.
function charEm(ch) {
  if (ch === " ") return 0.26;
  if (/[iljıIİ|!.,:;'’]/.test(ch)) return 0.29;
  if (/[ftr()[\]"«»“”\-–/]/.test(ch)) return 0.38;
  if (/[mwMWƏ—%@]/.test(ch)) return 0.9;
  if (/\d/.test(ch)) return 0.58;
  if (ch !== ch.toLocaleLowerCase("az")) return 0.7;
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
function fitHeadline(title, sizes = [96, 88, 80, 72, 66, 60], maxH = L.headMaxH) {
  for (const size of sizes) {
    const lines = wrap(title, size, "black", TEXT_W);
    if (lines.length * size <= maxH) return { size, lines };
  }
  const size = sizes[sizes.length - 1], max = Math.floor(maxH / size), lines = wrap(title, size, "black", TEXT_W);
  const kept = lines.slice(0, max);
  kept[max - 1] = kept[max - 1].replace(/[\s,.;:–-]*$/, "") + "…";
  return { size, lines: kept };
}

// İzah cümlələrə bölünür; sığmayan cümlə bərabərə yaxın hissələrə — imkan olsa vergüldən, sonra bağlayıcıdan əvvəl, ən son
// istənilən sözdən («Ərçivan | qəsəbəsindən» kimi ad birləşməsi az parçalansın). Hər altyazı ən çox CAP_LINES sətir.
const CAP_SIZE = 62, CAP_LINES = 3, CAP_PAD = 16, CAP_W = TEXT_W - 2 * CAP_PAD;
const SENT_SPLIT = /(?<!(?:^|[\s(])\p{Lu}\.)(?<=[.!?…]["»”)]?)\s+(?=["«“(]?[\p{Lu}\d])/u;   // «İ. Əliyev» inisialı cümlə sonu deyil
const CONJ = /^(və|amma|lakin|ancaq|çünki|həmçinin|habelə|eləcə|bununla|həm|yaxud|ya|ki)$/u;
const capLines = s => wrap(s, CAP_SIZE, "medium", CAP_W).length;
function splitSentence(words, k) {
  if (k <= 1 || words.length < 2) return [words.join(" ")];
  const total = words.join(" ").length, target = total / k;
  let best = null, pos = 0;
  for (let i = 1; i < words.length; i++) {
    pos += words[i - 1].length + 1;
    const head = words.slice(0, i).join(" ");
    if (capLines(head) > CAP_LINES) break;
    const cost = Math.abs(pos - target) + (/[,;:]$/.test(words[i - 1]) ? 0 : CONJ.test(words[i].toLocaleLowerCase("az")) ? 12 : 30);
    if (!best || cost < best.cost) best = { i, cost };
  }
  const i = best ? best.i : 1;
  return [words.slice(0, i).join(" "), ...splitSentence(words.slice(i), Math.max(1, k - 1))];
}
function captionChunks(body) {
  return clean(body).split(SENT_SPLIT).filter(Boolean).flatMap(sentence => {
    const n = capLines(sentence);
    if (n <= CAP_LINES) return [sentence];
    const words = sentence.split(" ");
    let parts = splitSentence(words, Math.ceil(n / CAP_LINES));
    // Hissə yenə sığmırsa (çox uzun söz və s.) — bir də bölünür.
    parts = parts.flatMap(p => (capLines(p) <= CAP_LINES ? [p] : splitSentence(p.split(" "), Math.ceil(capLines(p) / CAP_LINES))));
    return parts;
  });
}

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
  const names = sourceNames(a);
  if (!names.length) return "";
  if (names.length <= 2) return `Mənbə: ${names.join(", ")}`;
  return `Mənbə: ${names.slice(0, 2).join(", ")} və daha ${names.length - 2} sayt`;
}
// Bakı vaxtı (UTC+4, yay vaxtı yoxdur).
function bakuTime(iso) {
  const t = Date.parse(iso || "");
  if (!Number.isFinite(t)) return "";
  const d = new Date(t + 4 * 3600e3);
  return `${d.getUTCDate()} ${MONTHS[d.getUTCMonth()]}, ${String(d.getUTCHours()).padStart(2, "0")}:${String(d.getUTCMinutes()).padStart(2, "0")}`;
}

// Videonun mətn planı: ekranda nə yazılır, səsə nə gedir.
const OUTRO_SAY = "Ətraflı məlumat səkkiz ulduz nöqtə az saytında.";
function prepare(a, opt = {}) {
  const title = clean(a.title);
  if (!title) throw new Error("başlıq yoxdur");
  const footage = Boolean(opt.footage);
  const head = footage ? fitHeadline(title, LF.sizes, LF.headMaxH) : fitHeadline(title);
  const chunks = captionChunks(bodyText(a));
  const label = clean(a.bolme || opt.cats?.find(c => c.slug === a.category)?.label || "Xəbər").toLocaleUpperCase("az");
  const source = [sourceLine(a), footage ? `Görüntü: ${clean(a.goruntuMenbe) || "Pexels"}` : ""].filter(Boolean).join(" · ");
  return { id: a.id, title, head, chunks, label, when: bakuTime(a.publishedAt), source, footage,
    say: [title, ...chunks, OUTRO_SAY] };
}

// Zaman planı. voice: video_ses.py nəticəsi { parts: [[başlanğıc, son], …] } (hissələr prepare().say sırası ilə) və ya null.
// Səssiz: oxuma sürəti (~13 simvol/s), hər altyazı ən azı 2,4 s.
function timeline(p, voice = null) {
  const n = p.say.length;
  let spans;
  const used = Boolean(voice && Array.isArray(voice.parts) && voice.parts.length === n);
  if (used) {
    spans = voice.parts.map(([s, e]) => [LEAD_S + s, LEAD_S + e]);
  } else {
    spans = [];
    let t = LEAD_S;
    for (let i = 0; i < n; i++) {
      const len = clean(p.say[i]).length;
      const d = i === 0 ? Math.max(3.2, len / 14) : i === n - 1 ? OUTRO_S : Math.max(2.4, len / 13);
      spans.push([t, t + d]);
      t += d + GAP_S;
    }
  }
  // Çox uzun olsa sondakı altyazılar düşür (başlıq və sonluq qalır).
  let chunks = p.chunks.slice(), parts = spans.slice(1, 1 + chunks.length);
  const outroLen = spans[n - 1][1] - spans[n - 1][0];
  const fullEnd = (last) => last + GAP_S + Math.max(OUTRO_S, outroLen + 0.5);
  while (chunks.length && fullEnd(parts[parts.length - 1][1]) > MAX_S) { chunks.pop(); parts.pop(); }
  const keepUntil = parts.length ? parts[parts.length - 1][1] : spans[0][1], mainEnd = keepUntil + GAP_S;
  const outro = [mainEnd, mainEnd + Math.max(OUTRO_S, outroLen + 0.5)];
  const duration = Math.round(Math.max(MIN_S, Math.min(MAX_S, outro[1] + 0.3)) * 100) / 100;
  // Səs ekranla eyni: altyazı düşübsə onun səsi kəsilir, sonluq səsi sonluğun başlanğıcına sürüşür (hamısı video vaxtı ilə).
  return { duration, head: spans[0], chunks: chunks.map((text, i) => ({ text, at: parts[i] })), outro,
    voiceCut: used ? { keepUntil, outroFrom: spans[n - 1][0], outroAt: outro[0] } : null };
}

// ASS (libass) — bütün yazılar və formalar. Rəng: &HBBGGRR&, şəffaflıq: &HAA& (00 tam görünür, FF görünmür).
const assColor = hex => `&H${hex.slice(4, 6)}${hex.slice(2, 4)}${hex.slice(0, 2)}&`;
const assTime = s => { const cs = Math.max(0, Math.round(s * 100)); return `${Math.floor(cs / 360000)}:${String(Math.floor(cs / 6000) % 60).padStart(2, "0")}:${String(Math.floor(cs / 100) % 60).padStart(2, "0")}.${String(cs % 100).padStart(2, "0")}`; };
// Mətndə ASS idarə simvolları ({ } \) olmasın: «{» etiket açır, «\» əmr başlayır.
const assText = s => clean(s).replace(/\\/g, "/").replace(/\{/g, "(").replace(/\}/g, ")");
const circle = r => { const k = Math.round(r * 0.5523), d = 2 * r; return `m ${r} 0 b ${r + k} 0 ${d} ${r - k} ${d} ${r} b ${d} ${r + k} ${r + k} ${d} ${r} ${d} b ${r - k} ${d} 0 ${r + k} 0 ${r} b 0 ${r - k} ${r - k} 0 ${r} 0`; };
const rect = (w, h) => `m 0 0 l ${w} 0 ${w} ${h} 0 ${h}`;

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
    st("Cap", CAP_SIZE, COLOR.white, false, { font: " Medium", border: 3, outline: CAP_PAD, outlineColor: COLOR.box }),
    st("Small", 36, COLOR.gray, false),
    st("Outro", 60, COLOR.gray, false, { font: " Medium", align: 5 }),
    st("OutroBig", 132, COLOR.orange, true, { font: " Black", align: 5 }),
  ];
  const ev = [];
  const dlg = (layer, from, to, style, text) => ev.push(`Dialogue: ${layer},${assTime(from)},${assTime(to)},${style},,0,0,0,,${text}`);
  const headY = p.footage ? LF.headY : L.headY;
  if (p.footage) {
    // Görüntülü: bölmə və başlığın arxasında yarımşəffaf tünd zolaq (görüntü ortada açıq qalır), sonluqda bütün ekran tündləşir.
    const top = L.barY + L.barH, bandH = bandBottom(p) - top;
    dlg(0, 0, out + 0.3, "Shape", `{\\an7\\pos(0,${top})\\p1\\bord0\\shad0\\1c${assColor(COLOR.bar)}\\1a&H50&\\fad(0,300)}${rect(W, bandH)}`);
    dlg(0, out, D, "Shape", `{\\an7\\pos(0,0)\\p1\\bord0\\shad0\\1c${assColor(COLOR.bg)}\\1a&H28&\\fad(300,0)}${rect(W, H)}`);
  } else {
    // Fon: tünd göy üstündə yavaş hərəkət edən iki yumşaq işıq (videonun canlı görünməsi üçün; şəkil deyil, forma).
    dlg(0, 0, D, "Shape", `{\\an5\\move(180,640,280,760)\\p1\\bord0\\shad0\\1c${assColor(COLOR.blue)}\\1a&HA8&\\blur90}${circle(520)}`);
    dlg(0, 0, D, "Shape", `{\\an5\\move(960,1560,880,1460)\\p1\\bord0\\shad0\\1c${assColor(COLOR.blue2)}\\1a&HDC&\\blur90}${circle(440)}`);
  }
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
  // Görüntünün üstündə yazı kölgə və kənar xətlə oxunur.
  const onVideo = p.footage ? "\\bord3\\3c&H000000&\\shad2\\4a&H40&" : "";
  dlg(3, 0, out + 0.3, "Head", `{\\an7\\move(${X0},${headY + 24},${X0},${headY},0,300)\\fad(120,300)${onVideo}}${p.head.lines.map(assText).join("\\N")}`);
  if (p.source) dlg(3, 0, out + 0.3, "Small", `{\\an7\\pos(${X0},${p.footage ? LF.srcY : L.srcY})${fade}${p.footage ? `\\1c${assColor(COLOR.white)}${onVideo}` : ""}}${assText(p.source)}`);
  // Altyazılar: tünd fonda başlığın altında (başlığın hündürlüyünə görə), görüntülü videoda aşağıda; səslə eyni anda.
  const capY = p.footage ? LF.capY : Math.min(L.capMaxY, Math.max(L.capMinY, L.headY + p.head.lines.length * p.head.size + 64));
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
  // Sonluq.
  dlg(3, out, D, "Outro", `{\\pos(540,${L.outroY - 140})\\fad(300,0)}Ətraflı:`);
  dlg(3, out, D, "OutroBig", `{\\pos(540,${L.outroY})\\fad(300,0)\\t(0,400,\\fscx104\\fscy104)\\t(400,800,\\fscx100\\fscy100)}8ulduz{\\1c${assColor(COLOR.white)}}.az`);
  dlg(3, out, D, "Outro", `{\\pos(540,${L.outroY + 150})\\fad(300,0)\\fs48}Xəbərin davamı və bütün mənbələr saytda`);
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
// Kadr planı (sahib, 2026-11-23: «tam professional kimi işlə»): kəsim danışığın sərhədindədir — başlıq oxunanda bir kadr, sonra hər
// altyazı hissəsi bir kadr, sonluq sonuncunun davamı. Xəbər montajında kadr 3–6 s-dir; əvvəl 45 s-lik videoda 5 kadr (~9 s) idi.
// SHOT_MIN-dən qısa hissə qonşusuna birləşir, SHOT_MAX-dan uzunu bərabər bölünür. Kliplər sıra ilə gedir (Gemini-nin ifadələri
// diktor mətninin cümlə sırasındadır): çatmasa təkrarlanır, təkrarda klipin işlənməmiş yerindən (ss) — eyni kadr iki dəfə görünməsin.
// Klip: fayl yolu və ya { file, w, h, dur }. Ölçü məlumdursa və klip şaquli deyilsə (en/hündürlük > KLIP_SAQULI) — «sığdırma»: klip
// tam enində ortada, arxada onun bulanıq nüsxəsi. Üfüqi 1920×1080 klipi 9:16-ya kəsmək həm mövzunu atır (sarayın yerinə göy
// qalır), həm də 1,8 dəfə böyüdüb bulanıqlaşdırır (2026-11-22 nümunə videosu).
const SHOT_MIN = 2.6, SHOT_MAX = 6.5, KLIP_SAQULI = 0.8, KLIP_Y = 740;
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
// Başlıq zolağının alt kənarı (görüntülü video). Üfüqi klip ondan aşağı başlayır: 3 sətirlik başlıqda zolaq KLIP_Y-dən aşağı düşür,
// klipin üstü zolağın altında qalırdı (2026-11-23 nümunəsi).
const bandBottom = p => LF.headY + p.head.lines.length * p.head.size + 40;
function clipFilter(c, i, clipY = KLIP_Y) {
  const head = `[${i}:v]fps=${FPS},trim=duration=${c.d.toFixed(2)},setpts=PTS-STARTPTS`;
  if (!fitsWide(c)) return `${head},scale=${W}:${H}:force_original_aspect_ratio=increase:flags=bicubic,crop=${W}:${H},setsar=1[c${i}]`;
  const fh = Math.round(W * c.h / c.w / 2) * 2, y = Math.max(0, Math.min(clipY, H - fh));
  // Bulanıq fon kiçik ölçüdə hazırlanır (ucuzdur), sonra böyüdülür və tündləşdirilir.
  return `${head},split=2[b${i}][f${i}];[b${i}]scale=${W / 4}:${H / 4}:force_original_aspect_ratio=increase,crop=${W / 4}:${H / 4},boxblur=12:2,`
    + `scale=${W}:${H},eq=brightness=-0.14:saturation=0.8[g${i}];[f${i}]scale=${W}:${fh}:flags=bicubic[h${i}];[g${i}][h${i}]overlay=0:${y},setsar=1[c${i}]`;
}

function ffmpegArgs({ tl, assFile, logo, voiceFile, out, clips = [], clipY = KLIP_Y }) {
  const D = tl.duration.toFixed(2);
  const plan = shotPlan(clips, tl);
  const args = ["-hide_banner", "-loglevel", "error", "-y"];
  let bg;
  if (plan.length) {
    // Şaquli klip 9:16-ya doldurulur, üfüqi tam enində sığdırılır (clipFilter); 30 kadr/s, bir az tündləşdirilir (yazı oxunsun).
    plan.forEach(c => args.push("-stream_loop", "-1", ...(c.ss > 0 ? ["-ss", c.ss.toFixed(2)] : []), "-t", c.d.toFixed(2), "-i", c.file));
    bg = plan.map((c, i) => clipFilter(c, i, clipY)).join(";")
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
    const c = tl.voiceCut, ms = s => Math.round(s * 1000);
    // Əsas hissə + (altyazı düşübsə, sürüşdürülmüş) sonluq səsi; LEAD_S qədər gecikmə.
    audio = c && c.outroAt + 0.01 < c.outroFrom
      ? `[${ai}:a]asplit=2[m][o];[m]atrim=0:${(c.keepUntil - LEAD_S).toFixed(3)},asetpts=PTS-STARTPTS[m1];[o]atrim=${(c.outroFrom - LEAD_S).toFixed(3)},asetpts=PTS-STARTPTS,adelay=${ms(c.outroAt - c.keepUntil)}:all=1[o1];[m1][o1]concat=n=2:v=0:a=1,adelay=${ms(LEAD_S)}:all=1,`
      : `[${ai}:a]adelay=${ms(LEAD_S)}:all=1,`;
    audio += `apad,atrim=0:${D},aresample=48000,aformat=sample_fmts=fltp:channel_layouts=stereo,loudnorm=I=-16:TP=-1.5:LRA=11,aresample=48000[a]`;
  } else {
    args.push("-f", "lavfi", "-t", D, "-i", "anullsrc=channel_layout=stereo:sample_rate=48000");
    audio = `[${ai}:a]aformat=sample_fmts=fltp:channel_layouts=stereo[a]`;
  }
  const video = `${bg},ass=${assFile}[t];[${li}:v]scale=-1:${L.logoH}:flags=lanczos,format=rgba[lg];[t][lg]overlay=${logoX()}:${logoY()}:format=rgb,format=yuv420p[v]`;
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

// Səs: video_ses.py (SARA). Alınmasa null — video səssiz hazırlanır.
function voice(p, dir, log) {
  const parts = path.join(dir, "ses-hisseler.json"), wav = path.join(dir, "ses.wav"), times = path.join(dir, "ses.json");
  fs.writeFileSync(parts, JSON.stringify({ parts: p.say }));
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

// <çıxış>.json-dakı xəbər sahələri (TikTok yükləyicisi, PR 8ulduz/8ulduz#293, bunları oxuyur: text — mətn, own — öz videomuzdur).
// own yalnız bu modulun hazırladığı videoda olur: içində xəbərin mətni və saytın dizaynı var, başqasının görüntüsü yoxdur.
function storyFields(a) {
  const text = clean(a.text || "") || clean(a.summary || "");
  return { id: a.id, own: true, title: clean(a.title), summary: clean(a.summary || ""), text, source: a.source || "", sourceUrl: a.sourceUrl || "",
    category: a.category || "", lang: a.lang || "az", publishedAt: a.publishedAt || "",
    ...(Array.isArray(a.hashtags) && a.hashtags.length ? { hashtags: a.hashtags.slice(0, 3) } : {}) };   // YouTube/TikTok yükləyicisi oxuyur
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
    policy ||= x => app.policyViolation(x);
    cats ||= app.CATS;
  }
  if (policy(a)) throw new Error(`xəbər saytın qaydasından keçmir: ${clean(a.title)}`);
  if (a.text && policy({ ...a, summary: a.text })) throw new Error("izah saytın qaydasından keçmir");
  out = path.resolve(out);
  // Fon klipləri (video-ssenari.cjs goruntu()): çıxış qovluğuna görə yol; olmayan fayl atılır.
  // Ölçü ffprobe ilə oxunur (üfüqi klip sığdırılır, clipFilter); oxunmasa klip doldurulur.
  const clips = (Array.isArray(a.klipler) ? a.klipler : []).map(f => path.resolve(opt.base || path.dirname(out), String(f))).filter(f => fs.existsSync(f))
    .map(file => { try { const m = probe(file); return { file, w: m.width || 0, h: m.height || 0, dur: m.duration || 0 }; } catch { return { file }; } });
  const menbe = clean(a.goruntuMenbe) || "Pexels";
  const p = prepare(a, { cats, footage: clips.length > 0 });
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), "video-xeber-"));
  try {
    const wantVoice = opt.voice ?? (a.ses !== false && process.env.VIDEO_SES !== "0");
    const v = wantVoice ? voice(p, dir, log) : null;
    const tl = timeline(p, v);
    fs.writeFileSync(path.join(dir, "video.ass"), ass(p, tl));
    fs.mkdirSync(path.dirname(out), { recursive: true });
    run("ffmpeg", ffmpegArgs({ tl, assFile: "video.ass", logo: path.join(ROOT, LOGO.file), voiceFile: v?.file, out, clips, clipY: Math.max(KLIP_Y, bandBottom(p)) }), { cwd: dir, timeout: 900000 });
    const cover_s = 1.5;
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
    const meta = { ...storyFields(a), ...probe(out), cover_s, kadrlar, voice: Boolean(v), parts: 2 + tl.chunks.length, title: p.title,
      ...(clips.length ? (shots => ({ goruntu: menbe, klip: new Set(shots.map(s => s.file)).size, kadr: shots.length, sigdirilan: shots.filter(fitsWide).length }))(shotPlan(clips, tl)) : {}) };
    fs.writeFileSync(out.replace(/\.mp4$/i, "") + ".json", JSON.stringify(meta, null, 1));
    if (opt.keepAss) fs.copyFileSync(path.join(dir, "video.ass"), out.replace(/\.mp4$/i, "") + ".ass");
    log(`video: ${meta.width}×${meta.height}, ${meta.duration.toFixed(1)} s, ${(meta.bytes / 1e6).toFixed(1)} MB, ${tl.chunks.length} altyazı, ${v ? "səsli" : "səssiz"}, ${clips.length ? `${meta.kadr} kadr, ${meta.klip} klip (${menbe}; ${meta.sigdirilan} kadr üfüqi, sığdırıldı)` : "görüntüsüz"} — ${p.title}`);
    return meta;
  } finally {
    fs.rmSync(dir, { recursive: true, force: true });
  }
}

module.exports = { render, prepare, timeline, ass, ffmpegArgs, shotPlan, shotBounds, wordTimes, clipFilter, bandBottom, KLIP_Y, LF, captionChunks, bodyText, fitHeadline, wrap, textWidth, sourceLine, bakuTime, probe, storyFields,
  W, H, FPS, MIN_S, MAX_S, L, COLOR,
  // Hava videosu (video-hava.cjs) eyni brendi, səsi, altyazını və kodlaşdırmanı işlədir: qayda iki yerdə yazılmır.
  clean, voice, run, assColor, assTime, assText, rect, circle, logoX, logoY, logoW, LOGO, X0, TEXT_W, FONT, CAP_SIZE, CAP_PAD, CAP_W, OUTRO_SAY };

if (require.main === module) {
  const [src, out] = process.argv.slice(2);
  if (!src || !out) { console.error("İşlədilmə: node .github/scripts/video-xeber.cjs <giriş.json> <çıxış.mp4>"); process.exit(2); }
  render(JSON.parse(fs.readFileSync(src, "utf8")), out, { keepAss: process.env.VIDEO_ASS === "1" })
    .catch(e => { console.error(`video: alınmadı — ${String(e?.message || e)}`); process.exitCode = 1; });
}
