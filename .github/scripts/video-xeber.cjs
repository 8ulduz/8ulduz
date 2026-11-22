// Video xəbər (sahib, 2026-11-22: «Facebook-da video xəbərlər verilsin… İnstagramda videolar verilsin. Videolarda başda 8ulduz.az
// yazılsın»). Bir xəbərdən şaquli qısa video (Reels): saytın rəngləri, yuxarıda başdan sona loqo + «8ulduz.az», böyük başlıq,
// izah cümlə-cümlə altyazı kimi, istəyə görə Azərbaycan səsi (SARA, «Dinlə» serverinin modeli), sonda «Ətraflı: 8ulduz.az».
// Videoda yalnız bizim hazırladığımız şey var: xəbərin başlığı və izahı (mətn), brend dizaynı, səs. Üçüncü tərəfin videosu,
// fotosu, musiqisi yoxdur (Meta Rights Manager riski; docs/sosial-video.md).
//
// İşlədilmə:  node .github/scripts/video-xeber.cjs <giriş.json> <çıxış.mp4>
//   giriş  — data/news.json sətri (id, title, summary, category, source, alts, publishedAt) + istəyə bağlı:
//            text  ekranda və səsdə gedən izah (social.cjs describe(): yalnız tam cümlələr); yoxdursa summary-nin tam cümlələri
//            bolme bölmənin adı (yoxdursa saytın CATS siyahısından)
//            ses   false → səssiz (boş səs izi)
//   çıxış  — <çıxış>.mp4: MP4 (moov əvvəldə), H.264 High 4.1, yuv420p, 1080×1920 (9:16), 30 kadr/s, GOP 2 s, CRF 21 (≤8 Mbit/s),
//            AAC-LC 48 kHz stereo 128 kbit/s; MIN_S…MAX_S saniyə. Facebook Reels (3–90 s), Instagram Reels və TikTok qəbul edir.
//            <çıxış>.json: { duration, width, height, bytes, cover_s, voice, parts }
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
const BODY_MAX = 360;                          // izahın ekranda/səsdə ən çox simvolu (≈ 3 cümlə, 20–25 s)
const LEAD_S = 0.35, GAP_S = 0.25, OUTRO_S = 2.8;
// Rənglər saytdandır: tünd göy fon (og-default.png, app.css --bg), loqonun narıncısı.
const COLOR = { bg: "0B1426", bar: "060D1A", orange: "F5A30A", white: "FFFFFF", gray: "AFC0D8", box: "14284A", blue: "1E4D8C" };
// Yerləşmə (piksel, 1080×1920). Lentdə Reels ortadan 4:5-ə kəsilir (y 285…1635), tam ekranda yuxarıda ~170 px, aşağıda ~420 px,
// sağda ~130 px şəbəkənin öz düymələridir: brend və bütün yazılar y 300…1480 arasındadır — loqo lentdə də, tam ekranda da görünür.
const L = { barY: 300, barH: 120, logoH: 80, chipY: 466, headY: 556, headMaxH: 470, capMinY: 860, capMaxY: 1110, srcY: 1404, outroY: 900 };
const FONT = "Roboto";

const clean = s => String(s ?? "").replace(/<[^>]+>/g, " ").replace(/\s+/g, " ").trim();
const MONTHS = ["yanvar", "fevral", "mart", "aprel", "may", "iyun", "iyul", "avqust", "sentyabr", "oktyabr", "noyabr", "dekabr"];

// Mətnin təxmini eni (piksel). ASS-də şrift ölçüsü sətir hündürlüyüdür (Roboto-da em ≈ ölçü/1.17…1.32); en burada qəsdən bir az
// böyük sayılır: sətri özümüz bölürük (\N), libass sətri əlavə bölməsin — bölsə, başlıq altyazının üstünə düşər.
function charEm(ch) {
  if (ch === " ") return 0.26;
  if (/[iljıIİ|!.,:;'’]/.test(ch)) return 0.29;
  if (/[ftr()[\]"«»“”\-–/]/.test(ch)) return 0.38;
  if (/[mwMWƏ—%@]/.test(ch)) return 0.9;
  if (/\d/.test(ch)) return 0.58;
  if (ch !== ch.toLocaleLowerCase("az")) return 0.7;
  return 0.58;
}
const WEIGHT = { black: 1.13, bold: 1.07, medium: 1.04, regular: 1 };
const EM_OF_SIZE = 1 / 1.17;
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
function fitHeadline(title) {
  for (const size of [96, 88, 80, 72, 66, 60]) {
    const lines = wrap(title, size, "black", TEXT_W);
    if (lines.length * size <= L.headMaxH) return { size, lines };
  }
  const size = 60, max = Math.floor(L.headMaxH / size), lines = wrap(title, size, "black", TEXT_W);
  const kept = lines.slice(0, max);
  kept[max - 1] = kept[max - 1].replace(/[\s,.;:–-]*$/, "") + "…";
  return { size, lines: kept };
}

// İzah cümlələrə bölünür; sığmayan cümlə bərabərə yaxın hissələrə — imkan olsa vergüldən, sonra bağlayıcıdan əvvəl, ən son
// istənilən sözdən («Ərçivan | qəsəbəsindən» kimi ad birləşməsi az parçalansın). Hər altyazı ən çox CAP_LINES sətir.
const CAP_SIZE = 62, CAP_LINES = 3, CAP_PAD = 16, CAP_W = TEXT_W - 2 * CAP_PAD;
const SENT_SPLIT = /(?<=[.!?…]["»”)]?)\s+(?=["«“(]?[\p{Lu}\d])/u;
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
  const head = fitHeadline(title);
  const chunks = captionChunks(bodyText(a));
  const label = clean(a.bolme || opt.cats?.find(c => c.slug === a.category)?.label || "Xəbər").toLocaleUpperCase("az");
  return { id: a.id, title, head, chunks, label, when: bakuTime(a.publishedAt), source: sourceLine(a),
    say: [title, ...chunks, OUTRO_SAY] };
}

// Zaman planı. voice: video_ses.py nəticəsi { parts: [[başlanğıc, son], …] } (hissələr prepare().say sırası ilə) və ya null.
// Səssiz: oxuma sürəti (~13 simvol/s), hər altyazı ən azı 2,4 s.
function timeline(p, voice = null) {
  const n = p.say.length;
  let spans;
  if (voice && Array.isArray(voice.parts) && voice.parts.length === n) {
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
  const mainEnd = (parts.length ? parts[parts.length - 1][1] : spans[0][1]) + GAP_S;
  const outro = [mainEnd, mainEnd + Math.max(OUTRO_S, outroLen + 0.5)];
  const duration = Math.round(Math.max(MIN_S, Math.min(MAX_S, outro[1] + 0.3)) * 100) / 100;
  // Səs hissələri ekranla eyni: outro səsi outro-nun başlanğıcına sürüşür (düşən altyazıların səsi kəsilir).
  return { duration, head: spans[0], chunks: chunks.map((text, i) => ({ text, at: parts[i] })), outro,
    voiceCut: voice ? { mainEnd, outroFrom: spans[n - 1][0], outroAt: outro[0] } : null };
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
  // Fon: tünd göy üstündə yavaş hərəkət edən iki yumşaq işıq (videonun canlı görünməsi üçün; şəkil deyil, forma).
  dlg(0, 0, D, "Shape", `{\\an5\\move(180,640,280,760)\\p1\\bord0\\shad0\\1c${assColor(COLOR.blue)}\\1a&HA8&\\blur90}${circle(520)}`);
  dlg(0, 0, D, "Shape", `{\\an5\\move(960,1560,880,1460)\\p1\\bord0\\shad0\\1c${assColor(COLOR.orange)}\\1a&HD8&\\blur90}${circle(440)}`);
  // Yuxarı zolaq: başdan sona. Loqo şəkli ffmpeg-də bu zolağın üstünə qoyulur, yanında «.az» — birlikdə «8ULDUZ.az».
  dlg(1, 0, D, "Shape", `{\\an7\\pos(0,${L.barY})\\p1\\bord0\\shad0\\1c${assColor(COLOR.bar)}}${rect(W, L.barH)}`);
  dlg(2, 0, D, "Brand", `{\\an1\\pos(${logoX() + logoW() + 4},${logoY() + L.logoH + 4})\\fs72}.az`);
  // Gediş xətti: videonun nə qədəri qalıb (xəbər Reels-lərində adət).
  const py = L.barY + L.barH;
  dlg(2, 0, D, "Shape", `{\\an7\\pos(0,${py})\\p1\\bord0\\shad0\\1c${assColor(COLOR.orange)}\\clip(0,${py},1,${py + 8})\\t(0,${Math.round(D * 1000)},\\clip(0,${py},${W},${py + 8}))}${rect(W, 8)}`);
  // Bölmə, vaxt, başlıq, mənbə: sonluğa qədər.
  const fade = `\\fad(250,300)`;
  dlg(3, 0, out + 0.3, "Chip", `{\\an4\\pos(${X0 + 12},${L.chipY + 30})${fade}}${assText(p.label)}`);
  if (p.when) dlg(3, 0, out + 0.3, "When", `{\\an4\\pos(${Math.round(X0 + textWidth(p.label, 40, "black") + 64)},${L.chipY + 30})${fade}}${assText(p.when)}`);
  dlg(3, 0, out + 0.3, "Head", `{\\an7\\move(${X0},${L.headY + 28},${X0},${L.headY},0,350)${fade}}${p.head.lines.map(assText).join("\\N")}`);
  if (p.source) dlg(3, 0, out + 0.3, "Small", `{\\an7\\pos(${X0},${L.srcY})${fade}}${assText(p.source)}`);
  // Altyazılar başlığın altında (başlığın hündürlüyünə görə), səslə eyni anda.
  const capY = Math.min(L.capMaxY, Math.max(L.capMinY, L.headY + p.head.lines.length * p.head.size + 64));
  for (const c of tl.chunks) {
    const lines = wrap(c.text, CAP_SIZE, "medium", CAP_W).map(assText);
    dlg(4, c.at[0], c.at[1] + GAP_S, "Cap", `{\\an7\\pos(${X0 + CAP_PAD},${capY + CAP_PAD})\\fad(180,120)}${lines.join("\\N")}`);
  }
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
function ffmpegArgs({ tl, assFile, logo, voiceFile, out }) {
  const D = tl.duration.toFixed(2);
  const args = ["-hide_banner", "-loglevel", "error", "-y",
    "-f", "lavfi", "-i", `color=c=0x${COLOR.bg}:s=${W}x${H}:r=${FPS}:d=${D}`,
    "-i", logo];
  let audio;
  if (voiceFile) {
    args.push("-i", voiceFile);
    const c = tl.voiceCut, ms = s => Math.round(s * 1000);
    // Əsas hissə + (altyazı düşübsə, sürüşdürülmüş) sonluq səsi; LEAD_S qədər gecikmə.
    audio = c && c.outroAt + 0.01 < c.outroFrom
      ? `[2:a]asplit=2[m][o];[m]atrim=0:${(c.mainEnd - LEAD_S).toFixed(3)},asetpts=PTS-STARTPTS[m1];[o]atrim=${(c.outroFrom - LEAD_S).toFixed(3)},asetpts=PTS-STARTPTS,adelay=${ms(c.outroAt - c.mainEnd)}:all=1[o1];[m1][o1]concat=n=2:v=0:a=1,adelay=${ms(LEAD_S)}:all=1,`
      : `[2:a]adelay=${ms(LEAD_S)}:all=1,`;
    audio += `apad,atrim=0:${D},aresample=48000,aformat=sample_fmts=fltp:channel_layouts=stereo,loudnorm=I=-16:TP=-1.5:LRA=11,aresample=48000[a]`;
  } else {
    args.push("-f", "lavfi", "-t", D, "-i", "anullsrc=channel_layout=stereo:sample_rate=48000");
    audio = "[2:a]aformat=sample_fmts=fltp:channel_layouts=stereo[a]";
  }
  const video = `[0:v]format=rgb24,ass=${assFile}[t];[1:v]scale=-1:${L.logoH}:flags=lanczos,format=rgba[lg];[t][lg]overlay=${logoX()}:${logoY()}:format=rgb,format=yuv420p[v]`;
  args.push("-filter_complex", `${video};${audio}`, "-map", "[v]", "-map", "[a]", "-t", D,
    "-c:v", "libx264", "-preset", "medium", "-profile:v", "high", "-level:v", "4.1", "-crf", "21", "-maxrate", "8M", "-bufsize", "16M",
    "-r", String(FPS), "-g", String(2 * FPS), "-keyint_min", String(2 * FPS), "-sc_threshold", "0", "-pix_fmt", "yuv420p",
    "-colorspace", "bt709", "-color_primaries", "bt709", "-color_trc", "bt709", "-color_range", "tv",
    "-c:a", "aac", "-b:a", "128k", "-ar", "48000", "-ac", "2", "-movflags", "+faststart", out);
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
  const p = prepare(a, { cats });
  out = path.resolve(out);
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), "video-xeber-"));
  try {
    const wantVoice = opt.voice ?? (a.ses !== false && process.env.VIDEO_SES !== "0");
    const v = wantVoice ? voice(p, dir, log) : null;
    const tl = timeline(p, v);
    fs.writeFileSync(path.join(dir, "video.ass"), ass(p, tl));
    fs.mkdirSync(path.dirname(out), { recursive: true });
    run("ffmpeg", ffmpegArgs({ tl, assFile: "video.ass", logo: path.join(ROOT, LOGO.file), voiceFile: v?.file, out }), { cwd: dir, timeout: 600000 });
    const cover_s = 1.5;
    const jpg = out.replace(/\.mp4$/i, "") + ".jpg";
    run("ffmpeg", ["-hide_banner", "-loglevel", "error", "-y", "-ss", String(cover_s), "-i", out, "-frames:v", "1", "-q:v", "3", jpg]);
    const meta = { ...probe(out), cover_s, voice: Boolean(v), parts: 2 + tl.chunks.length, title: p.title };
    fs.writeFileSync(out.replace(/\.mp4$/i, "") + ".json", JSON.stringify(meta, null, 1));
    if (opt.keepAss) fs.copyFileSync(path.join(dir, "video.ass"), out.replace(/\.mp4$/i, "") + ".ass");
    log(`video: ${meta.width}×${meta.height}, ${meta.duration.toFixed(1)} s, ${(meta.bytes / 1e6).toFixed(1)} MB, ${tl.chunks.length} altyazı, ${v ? "səsli" : "səssiz"} — ${p.title}`);
    return meta;
  } finally {
    fs.rmSync(dir, { recursive: true, force: true });
  }
}

module.exports = { render, prepare, timeline, ass, ffmpegArgs, captionChunks, bodyText, fitHeadline, wrap, textWidth, sourceLine, bakuTime, probe,
  W, H, FPS, MIN_S, MAX_S, L, COLOR };

if (require.main === module) {
  const [src, out] = process.argv.slice(2);
  if (!src || !out) { console.error("İşlədilmə: node .github/scripts/video-xeber.cjs <giriş.json> <çıxış.mp4>"); process.exit(2); }
  render(JSON.parse(fs.readFileSync(src, "utf8")), out, { keepAss: process.env.VIDEO_ASS === "1" })
    .catch(e => { console.error(`video: alınmadı — ${String(e?.message || e)}`); process.exitCode = 1; });
}
