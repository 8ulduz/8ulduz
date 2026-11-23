// TikTok tətbiq yoxlaması (App review) üçün demo video: ekran yazısı (docs/tiktok.md «Demo video»). TikTok-un tələbi: tam axın,
// Website URL ilə eyni domen, interfeys və istifadəçinin hərəkətləri, hər məhsul və icazə. Bu yazı agentin göstərə bildiyi hissədir:
// saytın əsl səhifələri (ünvan sətri görünür), TikTok üçün ingiliscə bölmələr, bizim hazırladığımız nümunə video və TikTok işinin
// ictimai jurnalı. Sahibin öz hissəsi (TikTok-da «Authorize», telefonda qaralamanı dərc etmək) ikinci videodur, onu sahib çəkir.
//
// İşlədilmə (tiktok-demo.yml): xvfb-run -a -s "-screen 0 1280x860x24" node .github/scripts/tiktok-demo.cjs <çıxış qovluğu>
//   DEMO_BASE     sayt (standart https://8ulduz.az/; PR-da budağın yerli nüsxəsi)
//   DEMO_PREVIEW  1: yazının küncündə «PREVIEW — not for submission» (PR önizləməsi TikTok-a göndərilmir)
//   DEMO_VIDEO    göstəriləcək nümunə mp4 (video modulunun son videosu)
//   DEMO_RUN_URL  TikTok işinin ictimai səhifəsi (github.com/…/actions/runs/…)
// Chrome başlıqlı (headed) rejimdə Xvfb ekranında açılır, ffmpeg x11grab bütün ekranı yazır: ünvan sətri də videoda görünür. Aşağıdakı
// 100 piksellik zolaqda ingiliscə izah gedir. Əlavə paket yoxdur (Node 22+: WebSocket). Sirr yoxdur: iş heç bir açar almır.
"use strict";
const fs = require("fs"), os = require("os"), path = require("path"), http = require("http"), { spawn, spawnSync } = require("child_process");

const W = 1280, H = 860, BAND = 100, WIN_H = H - BAND, FPS = 25;
const sleep = ms => new Promise(ok => setTimeout(ok, ms));

// Altyazı mətni: ən çox 3 sətir, ~95 simvol.
function wrap(text, n = 95) {
  const out = [];
  let line = "";
  for (const w of String(text).split(/\s+/)) {
    if ((line + " " + w).trim().length > n) { out.push(line); line = w; } else line = (line + " " + w).trim();
  }
  if (line) out.push(line);
  return out.slice(0, 3).join("\n");
}

// Səhnələr: { at, caption } — yazı başlayandan saniyə. Çəkilişdən sonra ffmpeg drawtext ilə zolağa yazılır.
function captionFilter(caps, dir, total, { font, preview }) {
  const parts = [`drawbox=x=0:y=${WIN_H}:w=${W}:h=${BAND}:color=0x0b1f3a:t=fill`];
  // Hər sətir ayrıca drawtext: ffmpeg 7-də çoxsətirli mətndə sətir sonu boş qutu (tofu) kimi çıxır.
  caps.forEach((c, i) => {
    const end = i + 1 < caps.length ? caps[i + 1].at : total;
    wrap(c.caption).split("\n").forEach((line, j) => {
      const file = path.join(dir, `cap${i}_${j}.txt`);
      fs.writeFileSync(file, line);
      parts.push(`drawtext=fontfile='${font}':textfile='${file}':expansion=none:fontcolor=white:fontsize=21:x=22:y=${WIN_H + 12 + j * 28}:enable='between(t,${c.at.toFixed(2)},${end.toFixed(2)})'`);
    });
  });
  const tag = path.join(dir, "tag.txt");
  fs.writeFileSync(tag, preview ? "PREVIEW — not for submission" : "8ulduz.az · TikTok app review demo");
  parts.push(`drawtext=fontfile='${font}':textfile='${tag}':expansion=none:fontcolor=${preview ? "0xffd166" : "0xaabbd2"}:fontsize=15:x=w-text_w-16:y=h-24`);
  return parts.join(",");
}

function fontPath() {
  const fc = spawnSync("fc-match", ["-f", "%{file}", "DejaVu Sans"], { encoding: "utf8" });
  return (fc.status === 0 && String(fc.stdout || "").trim()) || "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf";
}

function chromePath() {
  if (process.env.CHROME) return process.env.CHROME;
  for (const p of ["/usr/bin/google-chrome", "/usr/bin/google-chrome-stable", "/usr/bin/chromium", "/usr/bin/chromium-browser"]) if (fs.existsSync(p)) return p;
  throw new Error("Chrome tapılmadı (CHROME=...)");
}

// Nümunə videonu yerli serverdən verir (Range ilə: Chrome video oynadanda hissə-hissə soruşur).
function videoServer(file) {
  const size = fs.statSync(file).size;
  const srv = http.createServer((req, res) => {
    const m = /bytes=(\d+)-(\d*)/.exec(req.headers.range || "");
    const a = m ? Number(m[1]) : 0, b = m && m[2] ? Number(m[2]) : size - 1;
    res.writeHead(m ? 206 : 200, { "content-type": "video/mp4", "accept-ranges": "bytes", "content-length": b - a + 1, ...(m ? { "content-range": `bytes ${a}-${b}/${size}` } : {}) });
    fs.createReadStream(file, { start: a, end: b }).pipe(res);
  });
  return new Promise(ok => srv.listen(0, "127.0.0.1", () => ok({ url: `http://127.0.0.1:${srv.address().port}/video.mp4`, close: () => srv.close() })));
}

async function launchChrome() {
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), "demo-chrome-"));
  // Səhifəni örtən pəncərələr olmasın: tərcümə təklifi (az dili qəbul edilən dillərdədir), «Sign in to Chrome», parol.
  fs.mkdirSync(path.join(dir, "Default"), { recursive: true });
  fs.writeFileSync(path.join(dir, "Default", "Preferences"), JSON.stringify({ translate: { enabled: false }, intl: { accept_languages: "en-US,en,az" },
    signin: { allowed: false }, credentials_enable_service: false, browser: { has_seen_welcome_page: true } }));
  const proc = spawn(chromePath(), [`--window-size=${W},${WIN_H}`, "--window-position=0,0", "--remote-debugging-port=0", `--user-data-dir=${dir}`,
    "--no-first-run", "--no-default-browser-check", "--disable-extensions", "--test-type", "--no-sandbox", "--disable-dev-shm-usage", "--disable-sync",
    "--disable-features=Translate,TranslateUI,MediaRouter,OptimizationGuideModelDownloading,PrivacySandboxSettings4,ChromeSigninIntercept,SigninPromo,DesktopPWAsAppHomePage", "--disable-search-engine-choice-screen",
    "--password-store=basic", "--autoplay-policy=no-user-gesture-required", "--force-device-scale-factor=1", "--lang=en-US", "--mute-audio", "about:blank"], { stdio: "ignore" });
  const portFile = path.join(dir, "DevToolsActivePort");
  for (let i = 0; i < 300 && !fs.existsSync(portFile) && proc.exitCode === null; i++) await sleep(100);
  if (!fs.existsSync(portFile)) { try { proc.kill("SIGKILL"); } catch {} throw new Error("Chrome açılmadı (DevToolsActivePort yoxdur)"); }
  const [port, wsPath] = fs.readFileSync(portFile, "utf8").split("\n");
  return { proc, ws: `ws://127.0.0.1:${port}${wsPath.trim()}` };
}

function cdp(url) {
  const ws = new WebSocket(url);
  let id = 0; const wait = new Map(), handlers = [];
  ws.onmessage = ev => {
    const m = JSON.parse(ev.data);
    if (m.id && wait.has(m.id)) { const { ok, no } = wait.get(m.id); wait.delete(m.id); m.error ? no(new Error(m.error.message)) : ok(m.result); }
    else handlers.forEach(h => h(m));
  };
  const send = (method, params = {}, sessionId) => new Promise((ok, no) => { const i = ++id; wait.set(i, { ok, no }); ws.send(JSON.stringify({ id: i, method, params, sessionId })); });
  return new Promise(ok => { ws.onopen = () => ok({ send, on: h => handlers.push(h), close: () => ws.close() }); });
}

async function main() {
  const out = path.resolve(process.argv[2] || "tiktok-demo");
  fs.mkdirSync(out, { recursive: true });
  const base = (process.env.DEMO_BASE || "https://8ulduz.az/").replace(/\/?$/, "/");
  const preview = process.env.DEMO_PREVIEW === "1", runUrl = process.env.DEMO_RUN_URL || "", sample = process.env.DEMO_VIDEO || "";
  if (!process.env.DISPLAY) throw new Error("DISPLAY yoxdur: xvfb-run ilə işə salın");

  const vsrv = sample && fs.existsSync(sample) ? await videoServer(sample) : null;
  const chrome = await launchChrome();
  const c = await cdp(chrome.ws);
  const { targetInfos } = await c.send("Target.getTargets");
  const page = targetInfos.find(t => t.type === "page");
  const { sessionId } = await c.send("Target.attachToTarget", { targetId: page.targetId, flatten: true });
  const s = (m, p) => c.send(m, p, sessionId);
  await s("Page.enable");
  let loaded = null;
  c.on(m => { if (m.sessionId === sessionId && m.method === "Page.loadEventFired" && loaded) { loaded(); loaded = null; } });
  const go = async (url, settle = 1500) => {
    const done = new Promise(ok => { loaded = ok; });
    await s("Page.navigate", { url });
    await Promise.race([done, sleep(15000)]);
    await sleep(settle);
  };
  const js = async expr => (await s("Runtime.evaluate", { expression: expr, awaitPromise: true, returnByValue: true })).result?.value;
  const scroll = async (expr, ms) => { await js(expr); await sleep(ms); };

  // Yazı: bütün Xvfb ekranı (Chrome pəncərəsi yuxarıda 1280×760, aşağıda boş zolaq).
  const raw = path.join(out, "raw.mp4");
  const rec = spawn("ffmpeg", ["-hide_banner", "-loglevel", "error", "-y", "-f", "x11grab", "-draw_mouse", "0", "-video_size", `${W}x${H}`, "-framerate", String(FPS),
    "-i", `${process.env.DISPLAY}+0,0`, "-c:v", "libx264", "-preset", "ultrafast", "-crf", "18", "-pix_fmt", "yuv420p", raw], { stdio: ["pipe", "inherit", "inherit"] });
  const t0 = Date.now() + 400;
  const caps = [];
  const cap = caption => { caps.push({ at: Math.max(0, (Date.now() - t0) / 1000), caption }); console.log(`[${caps.at(-1).at.toFixed(1)} s] ${caption}`); };
  await sleep(800);

  const steps = 5 + (vsrv ? 1 : 0) + (runUrl ? 1 : 0);
  let n = 0;
  const step = text => cap(`${++n}/${steps}  ${text}`);

  cap("8ulduz.az — TikTok app review demo 1: Login Kit (user.info.basic) and Content Posting API, Upload to inbox (video.upload).");
  await go(base, 3500);
  step(`${new URL(base).host === "8ulduz.az" ? "8ulduz.az" : "The 8ulduz website"} is an Azerbaijani news website. It is the Website URL registered for our TikTok app.`);
  await sleep(5000);
  await scroll("(document.querySelector('.copy') || document.body.lastElementChild).scrollIntoView({ behavior: 'smooth', block: 'end' })", 2500);
  cap("Privacy Policy and Terms of Service links are in the footer of every page, without opening a menu.");
  await sleep(4500);

  // Altyazı keçiddən əvvəl dəyişir: yeni səhifə ilə izah eyni anda görünür.
  step("About page, also the Login Kit Redirect URI: what our TikTok app does. It sends 8ulduz's own news videos to the 8ulduz TikTok account.");
  await go(`${base}haqqinda/#tiktok`);
  await sleep(7000);

  step("Terms of Service (English summary): only videos produced by 8ulduz, only to 8ulduz's own accounts; TikTok's own terms apply on TikTok.");
  await go(`${base}sertler/#en`);
  await sleep(6500);

  step("Privacy Policy, TikTok section: the TikTok data we receive (open ID, display name, tokens, posting options, upload status), storage and revocation.");
  await go(`${base}mexfilik/#tiktok`);
  await sleep(5500);
  await scroll("window.scrollBy({ top: 260, behavior: 'smooth' })", 4000);

  if (vsrv) {
    step("The content: a vertical news video made by 8ulduz itself (our text, text-to-speech voice-over, licensed stock footage, 8ulduz.az branding).");
    await go(vsrv.url, 800);
    await js("(() => { const v = document.querySelector('video'); if (v) { v.muted = true; v.play().catch(() => {}); } return !!v; })()");
    const dur = Number(await js("(document.querySelector('video') || {}).duration || 0")) || 12;
    await sleep(Math.min(16, Math.max(8, dur)) * 1000);
  }

  if (runUrl) {
    // Girişsiz baxışda GitHub jurnalı göstərmir, işlərin siyahısı və vəziyyəti görünür.
    step("Our server pipeline on GitHub Actions: the video job renders the video, then the 'tiktok / post' job uploads it with the Content Posting API (FILE_UPLOAD) and checks its status. Keys stay in encrypted secrets.");
    await go(runUrl, 4000);
    await sleep(6000);
    await scroll("(() => { const h = [...document.querySelectorAll('h2, h3')].find(e => /TikTok/.test(e.textContent)); if (h) h.scrollIntoView({ behavior: 'smooth', block: 'start' }); else window.scrollBy({ top: 420, behavior: 'smooth' }); return !!h; })()", 6000);
  }

  step("In the TikTok app the account owner taps the inbox notification, edits the caption, chooses who can view the video and posts it (demo video 2).");
  await sleep(7000);

  rec.stdin.write("q");
  await new Promise(ok => rec.on("close", ok));
  const total = (Date.now() - t0) / 1000;
  try { c.close(); chrome.proc.kill("SIGTERM"); } catch {}
  vsrv?.close();

  const final = path.join(out, "tiktok-demo.mp4");
  const r = spawnSync("ffmpeg", ["-hide_banner", "-loglevel", "error", "-y", "-i", raw, "-vf", captionFilter(caps, out, total, { font: fontPath(), preview }),
    "-c:v", "libx264", "-preset", "medium", "-crf", "27", "-pix_fmt", "yuv420p", "-r", String(FPS), "-movflags", "+faststart", "-an", final], { encoding: "utf8" });
  if (r.status !== 0) throw new Error(`ffmpeg (altyazı) alınmadı: ${String(r.stderr || r.error?.message).slice(0, 400)}`);
  fs.unlinkSync(raw);
  for (const f of fs.readdirSync(out)) if (/^cap\d+_\d+\.txt$|^tag\.txt$/.test(f)) fs.unlinkSync(path.join(out, f));
  const size = fs.statSync(final).size;
  fs.writeFileSync(path.join(out, "ssenari.txt"), [`Sayt: ${base}${preview ? " (PREVIEW)" : ""}`, `Uzunluq: ${total.toFixed(1)} s, ölçü: ${(size / 1e6).toFixed(1)} MB`, "",
    ...caps.map(x => `${x.at.toFixed(1).padStart(5)} s  ${x.caption}`)].join("\n") + "\n");
  console.log(`demo: ${final} — ${total.toFixed(1)} s, ${(size / 1e6).toFixed(1)} MB`);
  if (size > 50e6) throw new Error("TikTok demo videosu 50 MB-dan böyük ola bilməz");
}

module.exports = { wrap, captionFilter };
if (require.main === module) main().catch(e => { console.error(String(e?.stack || e).slice(0, 600)); process.exit(1); });
