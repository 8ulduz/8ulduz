// «Instagram hekayəsi» (sahib, 2026-11-17: Instagram-da xəbəri paylaşanda yalnız mesaj siyahısı çıxırdı). Səbəb: sayt telefonun
// paylaşım pəncərəsinə yalnız başlıq və keçid verirdi, Instagram isə lentə/hekayəyə ancaq şəkil qəbul edir. Bu modul xəbərdən
// 1080×1920 hekayə şəkli çəkir (xəbərin şəkli + başlıq + «8ulduz.az») və onu fayl kimi paylaşır: Instagram «Hekayə», «Lent»
// seçimlərini göstərir. Instagram şəkillə gələn keçidi basılan etmir — keçid paylaşmadan əvvəl kopyalanır (stikerə yapışdırılır).
// Yalnız telefonda paylaşım menyusu açılanda yüklənir (adi açılışa bayt yoxdur). Şəkil wsrv.nl-dən (CORS açıq) gəlir.

const W = 1080, H = 1920, PAD = 80;

const wsrv = u => `https://wsrv.nl/?url=${encodeURIComponent(u)}&w=${W}&h=1080&fit=cover&a=attention&output=jpg&q=80`;

async function picture(url) {
  if (!/^https:\/\//.test(String(url || ""))) return null;
  try {
    const r = await fetch(wsrv(url), { signal: AbortSignal.timeout(6000) });
    if (!r.ok || !/^image\//.test(r.headers.get("content-type") || "")) return null;
    return await createImageBitmap(await r.blob());
  } catch { return null; }
}

// Sözləri sətirlərə bölür; maxLines-dan artıq olsa son sətir «…» ilə bitir.
export function lines(measure, text, width, maxLines) {
  const out = [];
  let cur = "";
  for (const w of String(text || "").split(/\s+/).filter(Boolean)) {
    const next = cur ? `${cur} ${w}` : w;
    if (cur && measure(next) > width) { out.push(cur); cur = w; } else cur = next;
  }
  if (cur) out.push(cur);
  if (out.length <= maxLines) return out;
  const cut = out.slice(0, maxLines);
  let last = cut[maxLines - 1];
  while (last && measure(`${last}…`) > width) last = last.replace(/\s*\S+$/, "");
  cut[maxLines - 1] = `${last}…`;
  return cut;
}

// {title, imageUrl, source} → JPEG fayl (Promise). Şəkil alınmasa yalnız mətnli kart.
export async function storyFile({ title, imageUrl, source }) {
  const img = await picture(imageUrl);
  const c = document.createElement("canvas");
  c.width = W; c.height = H;
  const g = c.getContext("2d");
  g.fillStyle = "#0b1220"; g.fillRect(0, 0, W, H);
  let y = 220;
  if (img) {
    const s = Math.max(W / img.width, 1080 / img.height), w = img.width * s, h = img.height * s;
    g.save(); g.beginPath(); g.rect(0, y, W, 1080); g.clip();
    g.drawImage(img, (W - w) / 2, y + (1080 - h) / 2, w, h); g.restore();
    const fade = g.createLinearGradient(0, y + 760, 0, y + 1080);
    fade.addColorStop(0, "rgba(11,18,32,0)"); fade.addColorStop(1, "#0b1220");
    g.fillStyle = fade; g.fillRect(0, y + 760, W, 320);
    y += 1080 + 40;
  } else y = 520;
  const font = "system-ui, -apple-system, 'Segoe UI', Roboto, Arial, sans-serif";
  g.fillStyle = "#f5c542"; g.font = `800 64px ${font}`; g.textBaseline = "alphabetic";
  g.fillText("★ 8ulduz", PAD, 140);
  g.fillStyle = "#ffffff"; g.font = `800 62px ${font}`;
  const rows = lines(t => g.measureText(t).width, title, W - 2 * PAD, img ? 6 : 10);
  for (const r of rows) { y += 74; g.fillText(r, PAD, y); }
  if (source) { g.fillStyle = "#9fb0c8"; g.font = `500 40px ${font}`; g.fillText(String(source).slice(0, 40), PAD, y + 80); }
  g.fillStyle = "#f5c542"; g.font = `800 52px ${font}`;
  g.fillText("Ətraflı: 8ulduz.az", PAD, H - 110);
  const blob = await new Promise(res => c.toBlob(res, "image/jpeg", 0.88));
  if (!blob) throw new Error("şəkil çəkilmədi");
  return new File([blob], "8ulduz-hekaye.jpg", { type: "image/jpeg" });
}
