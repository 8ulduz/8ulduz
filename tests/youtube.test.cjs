// .github/scripts/youtube.cjs: öz video xəbərlərimiz YouTube Shorts-da (2026-11-22). Şəbəkə yoxdur: Google və YouTube testdə saxtadır.
// YOUTUBE_TEST_DIR verilibsə (youtube.yml «sinaq-video» işi) ffmpeg ilə hazırlanmış əsl video da eyni yoldan keçir.
const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("fs"), path = require("path"), os = require("os");
const Y = require("../.github/scripts/youtube.cjs");
const { loadApp } = require("../.github/scripts/topics.cjs");

const root = path.join(__dirname, "..");
const NOW = Date.parse("2026-11-22T12:00:00Z");
const KEYS = { YOUTUBE_CLIENT_ID: "123-abc.apps.googleusercontent.com", YOUTUBE_CLIENT_SECRET: "GOCSPX-client-secret-XYZ", YOUTUBE_REFRESH_TOKEN: "1//refresh-token-000-abc", YOUTUBE_RETRY_MS: "0" };
const ACCESS = "ya29.access-token-" + "a".repeat(24);
const TOKEN_URL = "https://oauth2.googleapis.com/token", API = "https://www.googleapis.com/youtube/v3/", UPLOAD = "https://www.googleapis.com/upload/youtube/v3/videos";
const SESSION = "https://www.googleapis.com/upload/youtube/v3/videos?uploadType=resumable&upload_id=SESSION-xyz-123";
const SCOPES = "https://www.googleapis.com/auth/youtube.upload https://www.googleapis.com/auth/youtube.readonly";

// Kiçik, amma düzgün qurulmuş MP4: ftyp + moov (mvhd, video izi tkhd + hdlr «vide», səs izi) + udta nişanı + mdat.
const box = (type, ...parts) => {
  const body = Buffer.concat(parts.map(p => (Buffer.isBuffer(p) ? p : Buffer.from(p, "latin1"))));
  const h = Buffer.alloc(8); h.writeUInt32BE(8 + body.length); h.write(type, 4, "latin1");
  return Buffer.concat([h, body]);
};
function mvhd(dur, ts = 1000) { const b = Buffer.alloc(100); b.writeUInt32BE(ts, 12); b.writeUInt32BE(Math.round(dur * ts), 16); return box("mvhd", b); }
function tkhd(w, h, turned = false) {
  const b = Buffer.alloc(84), m = 40;
  if (turned) { b.writeInt32BE(0, m); b.writeInt32BE(0x10000, m + 4); b.writeInt32BE(-0x10000, m + 12); b.writeInt32BE(0, m + 16); }
  else { b.writeInt32BE(0x10000, m); b.writeInt32BE(0x10000, m + 16); }
  b.writeInt32BE(0x40000000, m + 32);
  b.writeUInt32BE(w * 65536, 76); b.writeUInt32BE(h * 65536, 80);
  return box("tkhd", b);
}
const hdlr = kind => { const b = Buffer.alloc(25); b.write(kind, 8, "latin1"); return box("hdlr", b); };
function mp4({ w = 1080, h = 1920, dur = 30, mark = true, salt = "", turned = false, n = 3000 } = {}) {
  const ftyp = box("ftyp", "isom", Buffer.from([0, 0, 2, 0]), "isomiso2avc1mp41");
  const moov = box("moov", mvhd(dur), box("trak", tkhd(0, 0), box("mdia", hdlr("soun"))), box("trak", tkhd(w, h, turned), box("mdia", hdlr("vide"))),
    mark ? box("udta", box("meta", Buffer.alloc(4), box("ilst", box("\xa9cmt", box("data", Buffer.from([0, 0, 0, 1, 0, 0, 0, 0]), "8ulduz.az"))))) : Buffer.alloc(0));
  const pad = Buffer.alloc(n, 7); pad.write(salt, 0);   // hər testin videosu öz baytlarıdır
  return Buffer.concat([ftyp, moov, box("mdat", pad)]);
}
const tmp = () => fs.mkdtempSync(path.join(os.tmpdir(), "youtube-"));
const NEWS = "1448923757abcdef";
function video(dir, name, meta = {}, buf = mp4({ salt: name })) {
  fs.writeFileSync(path.join(dir, `${name}.mp4`), buf);
  fs.writeFileSync(path.join(dir, `${name}.json`), JSON.stringify({ id: name, own: true, title: `Bakıda yeni metro stansiyası açılır ${name}`, summary: "Stansiya sabah sərnişin qəbul edəcək.",
    createdAt: new Date(NOW - 30 * 60e3).toISOString(), source: "APA", sourceUrl: `https://apa.az/xeber/${name}`, category: "gundem", lang: "az", ...meta }));
  return path.join(dir, `${name}.mp4`);
}

// Saxta Google/YouTube: hər sorğu yazılır, cavablar ssenaridən (əsl Response obyektləri: başlıqlar fetch-dəki kimi oxunur).
function youtube(o = {}) {
  const calls = [];
  const res = (status, j, headers = {}) => new Response(j === undefined ? null : JSON.stringify(j), { status, headers: { "content-type": "application/json", ...headers } });
  const fetch = async (url, init = {}) => {
    url = String(url);
    const body = init.body;
    calls.push({ url, method: init.method || "GET", headers: init.headers || {}, body: typeof body === "string" ? body : body ? Buffer.from(body) : undefined });
    if (url === TOKEN_URL) return o.token ? o.token(new URLSearchParams(body)) : res(200, { access_token: ACCESS, expires_in: 3599, scope: o.scope ?? SCOPES, token_type: "Bearer" });
    if (url.startsWith(API + "channels?")) return o.channels ? o.channels() : res(200, { items: [{ id: "UC8ulduz", snippet: { title: "8ulduz.az" }, contentDetails: { relatedPlaylists: { uploads: "UU8ulduz" } }, statistics: { videoCount: "3" } }] });
    if (url.startsWith(API + "playlistItems?")) return o.items ? o.items() : res(200, { items: [] });
    if (url.startsWith(UPLOAD + "?") && init.method === "POST") return o.init ? o.init(JSON.parse(body), init) : res(200, {}, { location: SESSION });
    if (url === SESSION) {
      if (o.put) return o.put(init, calls);
      const meta = JSON.parse(calls.find(c => c.url.startsWith(UPLOAD + "?") && c.method === "POST").body);
      return res(201, { id: "vid123", status: { uploadStatus: "uploaded", privacyStatus: meta.status.privacyStatus } });
    }
    throw new Error(`gözlənilməyən sorğu ${url}`);
  };
  return { fetch, calls, res };
}
const go = (dir, yt, o = {}) => {
  const logs = [];
  return Y.run({ videos: Y.readVideos(dir), env: { ...KEYS, ...o.env }, now: o.now ?? NOW, fetch: yt.fetch, state: o.state || {}, log: s => logs.push(s), policy: o.policy, reels: o.reels })
    .then(res => ({ res, logs }));
};
const noSecrets = (text, extra = []) => {
  for (const s of [KEYS.YOUTUBE_CLIENT_SECRET, KEYS.YOUTUBE_REFRESH_TOKEN, KEYS.YOUTUBE_CLIENT_ID, ACCESS, SESSION, ...extra]) assert.ok(!text.includes(s), `jurnalda/state-də açar var: ${s.slice(0, 10)}…`);
};
const initBody = yt => JSON.parse(yt.calls.find(c => c.url.startsWith(UPLOAD + "?") && c.method === "POST").body);
// YouTube-un teq sayma qaydası: vergül 1, boşluqlu teq dırnaqlı sayılır.
const tagCost = tags => tags.reduce((n, t, i) => n + t.length + (/\s/.test(t) ? 2 : 0) + (i ? 1 : 0), 0);

test("youtube: no secrets (or YOUTUBE=0) means nothing is sent and the job stays green", async () => {
  const dir = tmp(); video(dir, "a1");
  for (const env of [{ YOUTUBE_CLIENT_ID: "", YOUTUBE_CLIENT_SECRET: "", YOUTUBE_REFRESH_TOKEN: "" }, { YOUTUBE_REFRESH_TOKEN: "" }, { YOUTUBE: "0" }]) {
    const yt = youtube();
    const { res, logs } = await go(dir, yt, { env });
    assert.equal(yt.calls.length, 0, "açarsız heç bir sorğu getmir");
    assert.deepEqual(res.failed, []);
    assert.match(logs.join("\n"), /açar yoxdur|söndürülüb/);
  }
});

test("youtube: an own vertical video goes up once as a public Short with the site link, and never twice", async () => {
  const dir = tmp();
  const file = video(dir, NEWS, { publishedAt: "2026-11-22T11:20:00Z", hashtags: ["metro", "Bakı"] });
  const yt = youtube(), state = {};
  const { res, logs } = await go(dir, yt, { state });
  assert.deepEqual(res.posted, [[NEWS, "vid123"]]);
  assert.deepEqual(yt.calls.map(c => c.url.split("?")[0]), [TOKEN_URL, API + "channels", API + "playlistItems", UPLOAD, SESSION.split("?")[0]]);
  const tok = new URLSearchParams(yt.calls[0].body);
  assert.equal(tok.get("grant_type"), "refresh_token");
  assert.equal(tok.get("refresh_token"), KEYS.YOUTUBE_REFRESH_TOKEN);
  const init = yt.calls[3], put = yt.calls[4], size = fs.statSync(file).size;
  assert.match(init.url, /uploadType=resumable/);
  assert.match(init.url, /part=snippet%2Cstatus/);
  assert.equal(init.headers.authorization, `Bearer ${ACCESS}`);
  assert.equal(init.headers["x-upload-content-length"], String(size));
  assert.equal(init.headers["x-upload-content-type"], "video/mp4");
  assert.equal(put.method, "PUT");
  assert.equal(put.body.length, size, "bütün fayl bir PUT-da gedir");
  const meta = initBody(yt);
  assert.equal(meta.status.privacyStatus, "public");
  assert.equal(meta.status.selfDeclaredMadeForKids, false);
  assert.equal(meta.status.containsSyntheticMedia, false);
  assert.equal(meta.snippet.categoryId, "25");
  assert.equal(meta.snippet.defaultLanguage, "az");
  assert.match(meta.snippet.title, /^Bakıda yeni metro stansiyası açılır/);
  assert.ok(meta.snippet.description.includes(`Ətraflı: https://www.8ulduz.az/${NEWS}?h=26112211`), meta.snippet.description);
  assert.match(meta.snippet.description, /Mənbə: APA/);
  assert.match(meta.snippet.description, /#metro #Bakı #8ulduz #xəbərlər #Shorts$/);
  assert.ok(meta.snippet.tags.includes("8ulduz") && meta.snippet.tags.includes("gündəm") && meta.snippet.tags.includes("metro"));
  assert.match(logs.join("\n"), /yükləndi — https:\/\/www\.youtube\.com\/shorts\/vid123 \(public\)/);
  assert.equal(state.posted[NEWS].v, "vid123");
  noSecrets(logs.join("\n") + JSON.stringify(state));

  // İkinci dövrə: eyni video (eyni nömrə, eyni fayl, eyni başlıq) heç bir sorğu olmadan ötürülür.
  const yt2 = youtube();
  const again = await go(dir, yt2, { state, now: NOW + 3 * 3600e3 });
  assert.equal(yt2.calls.length, 0);
  assert.deepEqual(again.res.posted, []);
  const dir2 = tmp(); video(dir2, "fedcba9876543210", { title: `Bakıda yeni metro stansiyası açılır ${NEWS}` });
  const yt3 = youtube();
  await go(dir2, yt3, { state, now: NOW + 3 * 3600e3 });
  assert.equal(yt3.calls.length, 0, "eyni başlıq başqa nömrə ilə də ikinci dəfə getmir");
});

test("youtube: only our own videos — X/reels, foreign links, unmarked files, horizontal or >60 s videos never go", async () => {
  const cases = [
    ["n1", { own: false }, undefined, /own: true yoxdur/],
    ["n2", { videoUrl: "https://video.twimg.com/ext_tw_video/1/pu/vid/720x1280/a.mp4" }, undefined, /başqa saytın videosudur/],
    ["n3", { clips: ["https://www.youtube.com/watch?v=abc"] }, undefined, /başqa saytın videosudur/],
    ["n4", { sourceUrl: "https://x.com/F1/status/1" }, undefined, /video\/sosial şəbəkədəndir/],
    ["reel-1", {}, undefined, /X videosudur/],
    ["n5", {}, mp4({ mark: false, salt: "n5" }), /«8ulduz\.az» nişanı yoxdur/],
    ["n6", {}, mp4({ w: 1920, h: 1080, salt: "n6" }), /şaquli deyil \(1920×1080\)/],
    ["n7", {}, mp4({ dur: 75, salt: "n7" }), /75\.0 s — 60 saniyədən uzundur/],
    ["n8", {}, mp4({ dur: 60.2, salt: "n8" }), /60 saniyədən uzundur/],
    ["n9", {}, Buffer.from("not a video at all, just text bytes"), /mp4 deyil/],
  ];
  for (const [name, meta, buf, why] of cases) {
    const dir = tmp(); video(dir, name, meta, buf);
    const yt = youtube();
    const { res, logs } = await go(dir, yt, { reels: new Set(["reel-1"]), env: { YOUTUBE_MAX_S: "180" } });
    assert.equal(yt.calls.length, 0, `${name}: heç bir sorğu getməməlidir`);
    assert.deepEqual(res.posted, []);
    assert.match(logs.join("\n"), why, name);
  }
  // 90° fırladılmış izi (en 1920, hündürlük 1080 + matris) əslində şaquli videodur.
  const dir = tmp(); video(dir, "n10", {}, mp4({ w: 1920, h: 1080, turned: true, salt: "n10" }));
  const { res } = await go(dir, youtube());
  assert.deepEqual(res.posted, [["n10", "vid123"]]);
});

test("youtube: red line 2 — the site's own source rule (policyViolation) is applied to the video's stories", async () => {
  const app = loadApp(root), policy = a => app.policyViolation(a);
  const bad = [
    { source: "BBC News", sourceUrl: "https://www.bbc.com/news/world-1", title: "Azerbaijan president visits Vietnam", lang: "en", category: "dunya" },
    { source: "Meydan TV", sourceUrl: "https://www.meydan.tv/az/article/1", title: "Bakıda yağış yağır" },
    { kind: "icmal", source: undefined, sourceUrl: undefined, items: [{ title: "Bakıda yağış", source: "APA", sourceUrl: "https://apa.az/1" }, { title: "Azerbaijan leader speaks", source: "BBC News", sourceUrl: "https://www.bbc.com/news/2" }] },
    { kind: "icmal", source: undefined, sourceUrl: undefined, items: [{ title: "Mənbəsiz xəbər" }] },
  ];
  for (const [i, meta] of bad.entries()) {
    const dir = tmp(); video(dir, `p${i}`, meta);
    const yt = youtube();
    const { res, logs } = await go(dir, yt, { policy });
    assert.equal(yt.calls.length, 0, `p${i}: qaydanı pozan video getmir`);
    assert.deepEqual(res.posted, []);
    assert.match(logs.join("\n"), /mənbə qaydası/);
  }
  const ok = [
    { source: "APA", sourceUrl: "https://apa.az/xeber/2", title: "Prezident İlham Əliyev Vyetnama səfər edib" },
    { source: "BBC News", sourceUrl: "https://www.bbc.com/news/world-3", title: "Storm hits Florida coast", lang: "en", category: "dunya" },
    { kind: "hava", source: undefined, sourceUrl: undefined, title: "Bakıda sabah hava: +12°, külək" },   // öz məlumatımız: xəbər yoxdur
  ];
  for (const [i, meta] of ok.entries()) {
    const dir = tmp(); video(dir, `q${i}`, meta);
    const { res } = await go(dir, youtube(), { policy });
    assert.equal(res.posted.length, 1, `q${i} getməlidir`);
  }
  assert.throws(() => Y.policyReason({ source: "APA", sourceUrl: "https://apa.az/1", title: "x" }, () => { throw new Error("qayda yoxdur"); }), /qayda yoxdur/,
    "qayda işləməsə susmur, iş dayanır");
});

test("youtube: if the cache is lost, the channel's own recent uploads stop a duplicate", async () => {
  const dir = tmp(); video(dir, NEWS, { publishedAt: "2026-11-22T11:20:00Z" });
  const yt = youtube({ items: () => new Response(JSON.stringify({ items: [{ snippet: { title: "Köhnə ad", description: `Ətraflı: https://www.8ulduz.az/${NEWS}?h=26112211`, resourceId: { videoId: "old42" } } }] }), { status: 200 }) });
  const state = {};
  const { res, logs } = await go(dir, yt, { state });
  assert.deepEqual(res.posted, []);
  assert.ok(!yt.calls.some(c => c.url.startsWith(UPLOAD)), "yükləmə başlamır");
  assert.match(logs.join("\n"), /kanalda artıq var \(https:\/\/www\.youtube\.com\/shorts\/old42\)/);
  assert.equal(state.posted[NEWS].v, "old42");
  assert.equal(state.posted[NEWS].d, 1, "kanalda tapılan təkrar gündəlik həddə sayılmır");
  // youtube.readonly icazəsi yoxdursa kanal oxunmur, yalnız öz siyahımız işləyir.
  const yt2 = youtube({ scope: "https://www.googleapis.com/auth/youtube.upload" });
  const r2 = await go(dir, yt2);
  assert.equal(r2.res.posted.length, 1);
  assert.ok(!yt2.calls.some(c => c.url.startsWith(API)), "readonly icazəsi olmadan kanala sorğu yoxdur");
});

test("youtube: an interrupted upload resumes from the byte YouTube already has", async () => {
  const dir = tmp(); const file = video(dir, "r1");
  const size = fs.statSync(file).size;
  let n = 0;
  const yt = youtube({
    put: (init, calls) => {
      n++;
      if (n === 1) return new Response(JSON.stringify({ error: { code: 503 } }), { status: 503 });
      if (n === 2) { assert.equal(init.headers["content-range"], `bytes */${size}`); return new Response(null, { status: 308, headers: { range: "bytes=0-99" } }); }
      assert.equal(init.headers["content-range"], `bytes 100-${size - 1}/${size}`);
      assert.equal(calls.at(-1).body.length, size - 100);
      return new Response(JSON.stringify({ id: "res77", status: { uploadStatus: "uploaded", privacyStatus: "public" } }), { status: 201 });
    },
  });
  const { res } = await go(dir, yt);
  assert.deepEqual(res.posted, [["r1", "res77"]]);
  assert.equal(n, 3);
  // Şəbəkə kəsilir, amma YouTube faylı tam alıb: yoxlama 201 qaytarır, video ikinci dəfə göndərilmir.
  const dir2 = tmp(); video(dir2, "r2");
  let m = 0;
  const yt2 = youtube({ put: () => { m++; if (m === 1) throw new TypeError("fetch failed"); return new Response(JSON.stringify({ id: "res88", status: { privacyStatus: "public" } }), { status: 201 }); } });
  const r2 = await go(dir2, yt2);
  assert.deepEqual(r2.res.posted, [["r2", "res88"]]);
  assert.equal(m, 2);
});

test("youtube: quota and channel limits pause the uploader instead of retrying every run", async () => {
  const dir = tmp(); video(dir, "k1");
  const quota = { error: { code: 403, message: "The request cannot be completed because you have exceeded your quota.", errors: [{ reason: "quotaExceeded", domain: "youtube.quota" }] } };
  const yt = youtube({ init: () => new Response(JSON.stringify(quota), { status: 403 }) }), state = {};
  const { res, logs } = await go(dir, yt, { state });
  assert.deepEqual(res.failed, [["k1", "quotaExceeded"]]);
  assert.equal(state.pause, Date.parse("2026-11-23T08:01:00Z") / 1000, "kvota Sakit okean vaxtı ilə gecə yarısı yenilənir (noyabrda UTC-8)");
  assert.match(logs.join("\n"), /kvotası \(100\) dolub/);
  const yt2 = youtube();
  const r2 = await go(dir, yt2, { state, now: NOW + 3600e3 });
  assert.equal(yt2.calls.length, 0, "fasilədə sorğu yoxdur");
  assert.match(r2.logs.join("\n"), /fasilə \(gündəlik yükləmə kvotası\)/);
  const dir3 = tmp(); video(dir3, "k3", { createdAt: "2026-11-23T08:20:00Z" });
  const r3 = await go(dir3, youtube(), { state, now: Date.parse("2026-11-23T08:30:00Z") });
  assert.equal(r3.res.posted.length, 1, "kvota yenilənəndən sonra yüklənir");

  const dir2 = tmp(); video(dir2, "k2");
  const lim = { error: { code: 400, errors: [{ reason: "uploadLimitExceeded" }] } }, st2 = {};
  await go(dir2, youtube({ init: () => new Response(JSON.stringify(lim), { status: 400 }) }), { state: st2 });
  assert.equal(st2.pause, NOW / 1000 + 24 * 3600);
  assert.equal(Y.quotaReset(Date.parse("2026-07-01T12:00:00Z")), Date.parse("2026-07-02T07:01:00Z"), "yayda Sakit okean vaxtı UTC-7");
});

test("youtube: a dead refresh token or a missing scope is reported clearly, without leaking secrets", async () => {
  const dir = tmp(); video(dir, "t1");
  const yt = youtube({ token: () => new Response(JSON.stringify({ error: "invalid_grant", error_description: `Token has been expired or revoked: ${KEYS.YOUTUBE_REFRESH_TOKEN}` }), { status: 400 }) });
  const { res, logs } = await go(dir, yt);
  assert.deepEqual(res.failed, [["token", "invalid_grant"]]);
  assert.match(logs.join("\n"), /Testing.*7 gün.*Token köhnələndə/);
  noSecrets(logs.join("\n"));
  const yt2 = youtube({ scope: "https://www.googleapis.com/auth/youtube.readonly" });
  const r2 = await go(dir, yt2);
  assert.deepEqual(r2.res.failed, [["t1", "scope"]]);
  assert.ok(!yt2.calls.some(c => c.url.startsWith(UPLOAD)));
  // YouTube-un xəta mətni açarı təkrarlasa da jurnala düşmür.
  const echo = { error: { code: 400, message: `bad request for ${KEYS.YOUTUBE_CLIENT_SECRET} with ${ACCESS}`, errors: [{ reason: "invalidTitle" }] } };
  const r3 = await go(dir, youtube({ init: () => new Response(JSON.stringify(echo), { status: 400 }) }));
  assert.deepEqual(r3.res.failed, [["t1", "invalidTitle"]]);
  noSecrets(r3.logs.join("\n"));
  const r4 = await go(dir, youtube({ init: () => new Response(JSON.stringify({ error: { code: 403, errors: [{ reason: "youtubeSignupRequired" }] } }), { status: 401 }) }));
  assert.match(r4.logs.join("\n"), /YouTube kanalı yoxdur/);
});

test("youtube: daily limit and spacing — but the digest and the test video skip the gap", async () => {
  const sec = NOW / 1000;
  const busy = () => ({ last: sec - 10 * 60, posted: Object.fromEntries(Array.from({ length: 3 }, (_, i) => [`old${i}`, { t: sec - 3600 * (i + 1), v: `v${i}` }])) });
  const dir = tmp(); video(dir, "g1");
  const r1 = await go(dir, youtube(), { state: busy() });
  assert.deepEqual(r1.res.posted, []);
  assert.match(r1.logs.join("\n"), /son video 10 dəq əvvəl, növbəti 20 dəq sonra/);
  const dir2 = tmp(); video(dir2, "icmal-2026-11-22-seher", { kind: "icmal", title: "Səhər icmalı · 22 noyabr 2026", source: undefined, sourceUrl: undefined,
    items: [{ title: "Birinci xəbər", source: "APA", sourceUrl: "https://apa.az/1" }, { title: "İkinci xəbər", source: "Report", sourceUrl: "https://report.az/2" }] });
  const yt2 = youtube();
  const r2 = await go(dir2, yt2, { state: busy() });
  assert.equal(r2.res.posted.length, 1, "icmal ara gözləmir");
  const d = initBody(yt2).snippet.description;
  assert.ok(d.startsWith("Stansiya sabah sərnişin qəbul edəcək.\n\n1. Birinci xəbər\n2. İkinci xəbər\n\nƏtraflı: https://8ulduz.az/icmal/2026-11-22-seher/"), d);
  assert.ok(!/Mənbə:/.test(d), "icmalda mənbə siyahısı yoxdur");
  assert.ok(initBody(yt2).snippet.tags.includes("günün icmalı"));
  const full = { posted: Object.fromEntries(Array.from({ length: 8 }, (_, i) => [`old${i}`, { t: sec - 600 * (i + 1), v: `v${i}` }])) };
  const r3 = await go(dir2, youtube(), { state: full });
  assert.match(r3.logs.join("\n"), /24 saatda 8 video yükləndi \(hədd 8\)/);
  const old = tmp(); video(old, "g2", { createdAt: new Date(NOW - 13 * 3600e3).toISOString() });
  const r4 = await go(old, youtube());
  assert.match(r4.logs.join("\n"), /12 saatdan köhnədir/);
});

test("youtube: the test video is uploaded private and is never matched by title", async () => {
  const dir = tmp(); video(dir, "sinaq-1", { sinaq: true, kind: "sinaq", title: "8ulduz.az — sınaq videosu", source: undefined, sourceUrl: undefined, createdAt: new Date(NOW - 48 * 3600e3).toISOString() });
  const yt = youtube({ items: () => new Response(JSON.stringify({ items: [{ snippet: { title: "8ulduz.az — sınaq videosu", description: "", resourceId: { videoId: "s0" } } }] }), { status: 200 }) });
  const { res } = await go(dir, yt, { state: { last: NOW / 1000 - 60 } });
  assert.deepEqual(res.posted, [["sinaq-1", "vid123"]]);
  assert.equal(initBody(yt).status.privacyStatus, "private");
  assert.ok(initBody(yt).snippet.description.includes("Ətraflı: https://8ulduz.az/"));
});

test("youtube: title, description and tags always fit YouTube's limits and carry no < >", () => {
  const long = "Ən uzun başlıq <b>qalın</b> və > işarəsi ilə ".repeat(10);
  const m = { id: NEWS, own: true, title: long, summary: "Çox uzun xülasə ə ş ç ğ ı ö ü. ".repeat(400), source: "APA", category: "dunya", publishedAt: "2026-11-22T09:05:00Z",
    hashtags: Array.from({ length: 60 }, (_, i) => `çox_uzun_heşteq_nömrə_${i}`) };
  const r = Y.resourceOf(m, Y.options({}));
  assert.ok(r.snippet.title.length <= Y.TITLE_MAX && r.snippet.title.length > 50, r.snippet.title);
  assert.ok(!/[<>]/.test(r.snippet.title + r.snippet.description + r.snippet.tags.join(",")));
  assert.ok(Buffer.byteLength(r.snippet.description) <= Y.DESC_MAX, `${Buffer.byteLength(r.snippet.description)} bayt`);
  assert.ok(r.snippet.description.includes(`Ətraflı: https://www.8ulduz.az/${NEWS}?h=26112209`), "uzun xülasədə də keçid qalır");
  assert.ok(r.snippet.description.endsWith("#Shorts"));
  assert.ok(tagCost(r.snippet.tags) <= Y.TAGS_MAX, `teqlər ${tagCost(r.snippet.tags)}`);
  assert.ok(r.snippet.tags.every(t => t.length <= 30));
  // İcmal: uzun xülasə + 10 uzun başlıq (azərbaycan hərfi 2 baytdır) 5000 baytı keçir — kəsilən mətn olur, keçid və heşteqlər qalır.
  const ic = Y.resourceOf({ id: "icmal-2026-11-22-axsam", own: true, title: "Axşam icmalı", summary: "şəçğıöü ".repeat(300),
    items: Array.from({ length: 10 }, (_, i) => ({ title: `${i} ` + "ğşçəıöü ".repeat(30) })) }, Y.options({})).snippet.description;
  assert.ok(Buffer.byteLength(ic) <= Y.DESC_MAX && Buffer.byteLength(ic) > 4500, `${Buffer.byteLength(ic)} bayt`);
  assert.ok(ic.includes("Ətraflı: https://8ulduz.az/icmal/2026-11-22-axsam/") && ic.endsWith("#Shorts"));
  assert.deepEqual(r.snippet.tags.slice(0, 5), ["8ulduz", "8ulduz.az", "xəbərlər", "son xəbərlər", "Azərbaycan xəbərləri"]);
  // Keçid yalnız saytın özünə: video modulunun verdiyi başqa sayt ünvanı işlədilmir.
  assert.equal(Y.linkOf({ id: "abc", kind: "hava", url: "https://evil.example/x" }), "https://8ulduz.az/");
  assert.equal(Y.linkOf({ id: "abc", kind: "valyuta", url: "https://8ulduz.az/bolme/iqtisadiyyat/" }), "https://8ulduz.az/bolme/iqtisadiyyat/");
  assert.equal(Y.linkOf({ id: NEWS }), `https://www.8ulduz.az/${NEWS}`);
  assert.equal(Y.options({ YOUTUBE_MAX_S: "180" }).maxS, 60, "60 saniyədən uzun Shorts olmur");
  assert.equal(Y.options({ YOUTUBE_MAX_DAY: "500" }).maxDay, 50, "gündəlik kvota 100-dür");
  assert.equal(Y.options({ YOUTUBE_PRIVACY: "hamıya" }).privacy, "public");
});

test("youtube: MP4 reader finds duration and the video track's size, ignoring the audio track", () => {
  assert.deepEqual(Y.mp4Info(mp4({ w: 1080, h: 1920, dur: 42.5 })), { duration: 42.5, width: 1080, height: 1920 });
  assert.deepEqual(Y.mp4Info(mp4({ w: 1920, h: 1080, dur: 10, turned: true })), { duration: 10, width: 1080, height: 1920 });
  assert.deepEqual(Y.mp4Info(Buffer.from("xxxxxxxxxxxxxxxxxxxxxxxx")), { duration: 0, width: 0, height: 0 });
  const broken = mp4(); broken.writeUInt32BE(0xffffff, 32);   // moov ölçüsü pozulub: xəta atmır, sadəcə oxunmur
  assert.equal(Y.mp4Info(broken).width, 0);
});

test("youtube: the check command names the channel and needs no upload quota", async () => {
  const yt = youtube(), logs = [];
  const ch = await Y.check({ env: KEYS, fetch: yt.fetch, log: s => logs.push(s) });
  assert.equal(ch.title, "8ulduz.az");
  assert.ok(!yt.calls.some(c => c.url.startsWith(UPLOAD)));
  assert.match(logs.join("\n"), /kanal — 8ulduz\.az \(https:\/\/www\.youtube\.com\/channel\/UC8ulduz\)/);
  noSecrets(logs.join("\n"));
  await assert.rejects(Y.check({ env: {}, fetch: yt.fetch, log: () => {} }), /açar yoxdur/);
  await assert.rejects(Y.check({ env: KEYS, fetch: youtube({ channels: () => new Response(JSON.stringify({ items: [] }), { status: 200 }) }).fetch, log: () => {} }), /kanalı yoxdur/);
});

test("youtube: the workflow only reads the repo, uploads only from main and never touches X videos", () => {
  const yml = fs.readFileSync(path.join(root, ".github/workflows/youtube.yml"), "utf8").replace(/\r\n/g, "\n");
  assert.match(yml, /permissions:\n  contents: read\n/);
  assert.ok(!/contents: write|git push/.test(yml));
  assert.match(yml, /post:\n    if: github\.event_name != 'pull_request' && github\.ref == 'refs\/heads\/main'/);
  for (const k of ["YOUTUBE_CLIENT_ID", "YOUTUBE_CLIENT_SECRET", "YOUTUBE_REFRESH_TOKEN"]) assert.ok(yml.includes(`${k}: \${{ secrets.${k} }}`), k);
  assert.ok(!/reels|oz_x|twimg/.test(yml.replace(/^\s*#.*$/gm, "").replace(/data\/reels\.json/g, "")), "iş axını X videolarını yükləmir");
  const js = fs.readFileSync(path.join(root, ".github/scripts/youtube.cjs"), "utf8");
  assert.ok(!/console\.log\([^)]*(SECRET|REFRESH)/.test(js), "açar jurnala yazılmır");
});

// youtube.yml «sinaq-video» işi: ffmpeg ilə hazırlanmış əsl 9:16 video oxunur və saxta YouTube-a tam göndərilir.
test("youtube: a real ffmpeg video passes the Shorts checks and is sent whole", { skip: !process.env.YOUTUBE_TEST_DIR && "YOUTUBE_TEST_DIR yoxdur (yalnız youtube.yml-də)" }, async () => {
  const dir = process.env.YOUTUBE_TEST_DIR, videos = Y.readVideos(dir);
  assert.equal(videos.length, 1);
  const buf = fs.readFileSync(videos[0].file), info = Y.mp4Info(buf);
  assert.equal(info.width, 1080);
  assert.equal(info.height, 1920);
  assert.ok(info.duration > 5.5 && info.duration < 6.5, `müddət ${info.duration}`);
  assert.equal(Y.foreignReason(videos[0].meta, buf), "");
  const yt = youtube(), logs = [];
  const res = await Y.run({ videos, env: KEYS, now: Date.now(), fetch: yt.fetch, state: {}, log: s => logs.push(s) });
  assert.equal(res.posted.length, 1, logs.join("\n"));
  assert.equal(yt.calls.find(c => c.url === SESSION).body.length, buf.length);
  assert.equal(initBody(yt).status.privacyStatus, "private");
});
