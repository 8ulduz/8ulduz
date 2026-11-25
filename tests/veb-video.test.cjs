// Öz videolarımızın veb nüsxəsi (.github/scripts/veb-video.cjs; sahib, 2026-11-25: «ən vacib qırmızı cizgi-gözqırpımı sürətidir»,
// «video xəbərlərdə bəzi videolar (əsasən azərbaycan) 1-2 saniyəyə açılır»). ffmpeg və R2 burada yoxdur: arqumentlər, imza və
// yükləmə ardıcıllığı saxta R2 ilə yoxlanır; əsl veb nüsxəni PR-da sosial-video.yml «Veb nüsxə» addımı qurur.
const { test } = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const os = require("node:os");
const path = require("node:path");
const crypto = require("node:crypto");
const root = path.join(__dirname, "..");
const read = f => fs.readFileSync(path.join(root, f), "utf8");
const V = require("../.github/scripts/veb-video.cjs");

const NOW = Date.parse("2026-11-25T12:00:00Z");
const ENV = { R2_ENDPOINT: "https://0123456789abcdef.r2.cloudflarestorage.com", R2_ACCESS_KEY_ID: "key-id-123", R2_SECRET_ACCESS_KEY: "secret-456" };
// Ən kiçik «MP4»: ftyp, moov, mdat (faststart).
const mp4 = (moovFirst = true) => {
  const box = (t, n) => { const b = Buffer.alloc(n); b.writeUInt32BE(n); b.write(t, 4, "latin1"); return b; };
  const parts = [box("ftyp", 24), box("moov", 64), box("mdat", 4096)];
  return Buffer.concat(moovFirst ? parts : [parts[0], parts[2], parts[1]]);
};
const tmpFile = buf => { const d = fs.mkdtempSync(path.join(os.tmpdir(), "veb-")); const f = path.join(d, "veb.mp4"); fs.writeFileSync(f, buf); return f; };

// Saxta R2 (S3 API) + açıq domen: hər sorğu yazılır, imza yoxlanır.
function r2({ index = null, publicRes = { status: 206, type: "video/mp4" }, failPut = "" } = {}) {
  const store = new Map(index ? [["index.json", JSON.stringify(index)]] : []), calls = [];
  const fetch = async (url, opt = {}) => {
    const u = new URL(url), method = opt.method || "GET", h = opt.headers || {};
    calls.push({ method, url, headers: h, redirect: opt.redirect });
    const res = (status, body = "", type = "") => ({ status, ok: status >= 200 && status < 300, headers: { get: k => ({ "content-type": type, location: status >= 300 && status < 400 ? "https://x/" : null })[k.toLowerCase()] ?? null }, text: async () => body });
    if (u.host === "video.8ulduz.az") return res(publicRes.status, "", publicRes.type);
    assert.equal(u.host, "0123456789abcdef.r2.cloudflarestorage.com");
    assert.match(h.authorization, /^AWS4-HMAC-SHA256 Credential=key-id-123\/20261125\/auto\/s3\/aws4_request, SignedHeaders=[a-z0-9;-]+, Signature=[0-9a-f]{64}$/);
    assert.equal(h["x-amz-content-sha256"], crypto.createHash("sha256").update(opt.body || "").digest("hex"), "gövdənin həşi imzadadır");
    const [, bucket, key] = u.pathname.split("/");
    assert.equal(bucket, "8ulduz-video");
    if (method === "PUT") { if (failPut === key) return res(403, "<Error><Code>AccessDenied</Code></Error>"); store.set(key, opt.body); return res(200); }
    if (method === "GET") return store.has(key) ? res(200, String(store.get(key))) : res(404, "<Error><Code>NoSuchKey</Code></Error>");
    if (method === "DELETE") { store.delete(key); return res(204); }
    return res(400);
  };
  return { fetch, store, calls };
}

test("veb-video: SigV4 matches AWS's published examples (GET with Range, PUT with body)", () => {
  const key = "AKIAIOSFODNN7EXAMPLE", secret = "wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY", now = Date.parse("2013-05-24T00:00:00Z");
  const get = V.sign({ method: "GET", url: "https://examplebucket.s3.amazonaws.com/test.txt", headers: { Range: "bytes=0-9" },
    hash: "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855", key, secret, region: "us-east-1", now });
  assert.ok(get.authorization.endsWith("SignedHeaders=host;range;x-amz-content-sha256;x-amz-date, Signature=f0e8bdb87c964420e857bd35b5d6ed310bd44f0170aba48dd91039c6036bdb41"), get.authorization);
  const put = V.sign({ method: "PUT", url: "https://examplebucket.s3.amazonaws.com/test%24file.text",
    headers: { Date: "Fri, 24 May 2013 00:00:00 GMT", "x-amz-storage-class": "REDUCED_REDUNDANCY" },
    hash: crypto.createHash("sha256").update("Welcome to Amazon S3.").digest("hex"), key, secret, region: "us-east-1", now });
  assert.ok(put.authorization.endsWith("Signature=98ad721746da40c64f1a55b78f14c238d841ea1380cd77a1b5971af0ece108bd"), put.authorization);
  assert.ok(!("host" in get), "host başlığını fetch özü qoyur");
});

test("veb-video: the web copy is 720×1280 H.264 with moov first, sized by duration to stay under 2.8 MB", () => {
  const a = V.ffmpegArgs("in.mp4", "out.mp4", 20);
  const at = k => a[a.indexOf(k) + 1];
  assert.equal(at("-vf"), "scale=720:1280:flags=lanczos,format=yuv420p");
  assert.equal(at("-c:v"), "libx264");
  assert.equal(at("-movflags"), "+faststart", "brauzer ilk kadrı faylın başından göstərir");
  assert.equal(at("-metadata"), "comment=8ulduz.az");
  assert.equal(at("-map"), "0:v:0");
  for (const d of [8, 20, 40, 59, 60]) {
    const kbps = V.bitrate(d);
    assert.ok(((kbps + 64 + 8) * 1000 / 8) * d <= V.MAX_BYTES * 1.001 || kbps === 1200, `${d} s → ${kbps} kb/s`);
  }
  assert.equal(V.bitrate(20), 1048);
  assert.equal(V.bitrate(59), 307);
  assert.equal(V.bitrate(8), 1200, "yuxarı həddi");
  assert.equal(V.bitrate(undefined), V.bitrate(60), "müddət bilinməsə 60 s sayılır");
  assert.ok(V.faststart(mp4(true)) && !V.faststart(mp4(false)));
});

test("veb-video: upload → public check (206, video/mp4, no redirect) → index.json; old files beyond 30 days are deleted", async () => {
  const old = { v: "OLDVIDEO001", t: "2026-10-01T00:00:00Z", b: 1 }, keep = { v: "KEEPVIDEO01", t: "2026-11-20T00:00:00Z", b: 1 };
  const fake = r2({ index: { items: [keep, old, { v: "../bad", t: "2026-11-24T00:00:00Z" }] } }), logs = [];
  const res = await V.yukle({ file: tmpFile(mp4()), id: "NEWVIDEO001", env: ENV, fetch: fake.fetch, now: NOW, log: s => logs.push(s) });
  assert.equal(res.url, "https://video.8ulduz.az/NEWVIDEO001.mp4", logs.join("\n"));
  const order = fake.calls.map(c => `${c.method} ${new URL(c.url).host === "video.8ulduz.az" ? "açıq " : ""}${new URL(c.url).pathname.split("/").pop()}`);
  assert.deepEqual(order, ["PUT NEWVIDEO001.mp4", "GET açıq NEWVIDEO001.mp4", "GET index.json", "PUT index.json", "DELETE OLDVIDEO001.mp4"]);
  const put = fake.calls[0];
  assert.equal(put.headers["content-type"], "video/mp4", "oxucuya video/mp4 gedir (iPhone Safari)");
  assert.equal(put.headers["cache-control"], "public, max-age=31536000, immutable", "fayl adı dəyişmir: Cloudflare və brauzer saxlayır");
  const pub = fake.calls[1];
  assert.equal(pub.headers.range, "bytes=0-1023");
  assert.equal(pub.redirect, "manual", "yönləndirmə izlənmir, sayılır");
  const idx = JSON.parse(fake.store.get("index.json"));
  assert.deepEqual(idx.items.map(x => x.v), ["NEWVIDEO001", "KEEPVIDEO01"], "yeni əvvəldə, 30 gündən köhnə və yanlış nömrə çıxır");
  assert.equal(fake.calls[3].headers["cache-control"], "public, max-age=60");
  assert.equal(fake.calls[3].headers["content-type"], "application/json");
});

test("veb-video: the site never gets an address that fails — redirect, wrong type, 404, bad id, no keys, unreadable index", async () => {
  const run = async (opt, extra = {}) => { const fake = r2(opt), logs = []; const res = await V.yukle({ file: tmpFile(mp4()), id: "NEWVIDEO001", env: ENV, fetch: fake.fetch, now: NOW, log: s => logs.push(s), ...extra }); return { res, fake, logs }; };
  for (const publicRes of [{ status: 302, type: "" }, { status: 200, type: "video/mp4" }, { status: 206, type: "application/octet-stream" }, { status: 404, type: "text/html" }]) {
    const { res, fake } = await run({ publicRes });
    assert.ok(res.failed, JSON.stringify(publicRes));
    assert.ok(!fake.store.has("index.json"), `${publicRes.status} ${publicRes.type}: siyahıya yazılmır`);
  }
  const noKeys = await run({}, { env: {} });
  assert.equal(noKeys.res.skipped, "acar");
  assert.equal(noKeys.fake.calls.length, 0, "açar yoxdursa heç nə soruşulmur");
  assert.match(noKeys.logs[0], /ötürülür, zolaq YouTube oynadıcısı ilə qalır/);
  assert.equal((await run({}, { id: "../../x" })).res.skipped, "id");
  assert.equal((await run({}, { file: tmpFile(mp4(false)) })).res.skipped, "olcu", "moov sonda: oxucu bütün faylı gözləyərdi");
  assert.equal((await run({}, { file: path.join(os.tmpdir(), "yoxdur-veb.mp4") })).res.skipped, "fayl");
  const denied = await run({ failPut: "NEWVIDEO001.mp4" });
  assert.match(denied.res.failed, /put 403 AccessDenied/);
  // index.json oxunmadı (404 yox, başqa xəta): köhnə siyahı yarımçıq siyahı ilə əvəzlənmir.
  const fake = r2({ index: { items: [] } }), f = async (u, o = {}) => (o.method || "GET") === "GET" && u.endsWith("/index.json") ? { status: 500, ok: false, headers: { get: () => null }, text: async () => "" } : fake.fetch(u, o);
  const res = await V.yukle({ file: tmpFile(mp4()), id: "NEWVIDEO001", env: ENV, fetch: f, now: NOW, log: () => {} });
  assert.ok(res.failed && JSON.parse(fake.store.get("index.json")).items.length === 0);
  assert.throws(() => V.config({ ...ENV, R2_ENDPOINT: "https://evil.example.com" }), /R2_ENDPOINT/);
  assert.equal(V.config({ ...ENV, R2_ENDPOINT: ENV.R2_ENDPOINT + "/8ulduz-video" }).endpoint, ENV.R2_ENDPOINT, "bucket yolu ilə yazılsa da işləyir");
});

test("veb-video: one address everywhere — the job writes it, updater.py copies it, vlent.js accepts only it", () => {
  assert.equal(V.BASE, "https://video.8ulduz.az/");
  assert.ok(read("updater.py").includes('VEB_VIDEO_URL = "https://video.8ulduz.az/"'));
  assert.ok(read("assets/vlent.js").includes('const OWN_BASE = "https://video.8ulduz.az/";'));
  const reg = JSON.parse(read("tests/fixtures/ucuncu-terefler.json"))["video.8ulduz.az"];
  assert.ok(reg && reg.vaxt === "sonra" && reg.yonlendirir === false && reg.numune === "https://video.8ulduz.az/index.json", "üçüncü tərəf siyahısında, gecə yoxlaması index.json-u soruşur");
});

test("veb-video: workflow — the web copy is made in the video job, uploaded only after YouTube, only on main, only R2 secrets", () => {
  const wf = read(".github/workflows/sosial-video.yml");
  const step = wf.slice(wf.indexOf("- name: Veb nüsxə"), wf.indexOf("- name: Paylaş"));
  assert.match(step, /if: steps\.sec\.outputs\.hazir == '1' && steps\.yoxla\.outcome == 'success'\n\s+continue-on-error: true\n/, "alınmasa paylaşma dayanmır");
  assert.ok(step.includes("node .github/scripts/veb-video.cjs hazirla video-out/video.mp4 video-out/veb.mp4"));
  assert.ok(wf.indexOf("- name: Veb nüsxə") < wf.indexOf("- name: Video (artefakt, 3 gün)"), "veb.mp4 artefaktdadır");
  const job = wf.slice(wf.indexOf("\n  veb-video:"));
  assert.match(job, /needs: \[video, youtube\]\n/);
  assert.match(job, /if: \$\{\{ !cancelled\(\) && github\.ref == 'refs\/heads\/main' && needs\.youtube\.outputs\.video_id != '' \}\}/);
  assert.deepEqual([...job.matchAll(/\$\{\{ secrets\.(\w+) \}\}/g)].map(m => m[1]), ["R2_ENDPOINT", "R2_ACCESS_KEY_ID", "R2_SECRET_ACCESS_KEY"], "yalnız R2 sirləri");
  assert.ok(job.includes('node .github/scripts/veb-video.cjs yukle video-out/veb.mp4 "$VIDEO_ID"'));
  assert.ok(/group: veb-video\n\s+cancel-in-progress: false/.test(job), "index.json-u iki iş eyni anda yazmır");
  const yt = read(".github/workflows/youtube.yml");
  assert.ok(yt.includes("value: ${{ jobs.post.outputs.video_id }}") && yt.includes("video_id: ${{ steps.yukle.outputs.video_id }}") && /- name: Yüklə\n\s+id: yukle\n/.test(yt));
  const Y = require("../.github/scripts/youtube.cjs");
  assert.equal(Y.videoIdOf({ posted: [["9fa597ae98cb32a9", "vid12345678"]] }), "vid12345678");
  assert.equal(Y.videoIdOf({ posted: [["x", "?"]] }), "", "yanlış nömrə çıxışa yazılmır");
  assert.equal(Y.videoIdOf({ posted: [] }), "");
  // TikTok/YouTube yükləyicisi veb.mp4-ü götürmür (cütü .json yoxdur).
  const d = fs.mkdtempSync(path.join(os.tmpdir(), "veb-art-"));
  fs.writeFileSync(path.join(d, "video.mp4"), mp4()); fs.writeFileSync(path.join(d, "video.json"), "{}"); fs.writeFileSync(path.join(d, "veb.mp4"), mp4());
  assert.deepEqual(Y.readVideos(d).map(v => path.basename(v.file)), ["video.mp4"]);
});
