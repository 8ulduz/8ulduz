// .github/scripts/tiktok.cjs: öz video xəbərlərimiz TikTok-da (sahib, 2026-11-22). Şəbəkə yoxdur: TikTok testdə saxtadır.
// TIKTOK_TEST_DIR verilibsə (tiktok.yml «sinaq-video» işi) ffmpeg ilə hazırlanmış əsl video da eyni yoldan keçir.
const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("fs"), path = require("path"), os = require("os");
const T = require("../.github/scripts/tiktok.cjs");

const NOW = Date.parse("2026-11-22T12:00:00Z");
const KEYS = { TIKTOK_CLIENT_KEY: "awkey123456", TIKTOK_CLIENT_SECRET: "client-secret-XYZ-987", TIKTOK_POLL_MS: "0" };
const SEED = "rft.seed-refresh-token-000";
const mp4 = (n = 4000, mark = true, salt = "") => {
  const head = Buffer.from([0, 0, 0, 0x18, ...Buffer.from("ftypisom"), 0, 0, 2, 0, ...Buffer.from("isomiso2")]);
  const tag = mark ? Buffer.from("\0\0\0\x21data\0\0\0\x01\0\0\0\x008ulduz.az") : Buffer.alloc(0);
  const pad = Buffer.alloc(Math.max(0, n - head.length - tag.length), 7);
  pad.write(salt, 0);   // hər testin videosu öz baytlarıdır (eyni fayl = eyni video, ikinci dəfə getmir)
  return Buffer.concat([head, tag, pad]);
};
const tmp = () => fs.mkdtempSync(path.join(os.tmpdir(), "tiktok-"));
function video(dir, name, meta = {}, buf = mp4(4000, true, name)) {
  fs.writeFileSync(path.join(dir, `${name}.mp4`), buf);
  fs.writeFileSync(path.join(dir, `${name}.json`), JSON.stringify({ id: name, own: true, title: `Bakıda yeni metro stansiyası ${name}`, summary: "Stansiya sabah açılır.",
    createdAt: new Date(NOW - 30 * 60e3).toISOString(), ...meta }));
}

// Saxta TikTok: hər sorğu yazılır; cavablar ssenaridən.
function tiktok(o = {}) {
  const calls = [];
  let n = 0;
  const json = (j, status = 200) => ({ ok: status < 300, status, json: async () => j, text: async () => JSON.stringify(j) });
  const fetch = async (url, init = {}) => {
    const body = init.body;
    calls.push({ url, method: init.method, headers: init.headers || {}, body: typeof body === "string" ? body : body ? Buffer.from(body) : undefined });
    if (url.endsWith("/oauth/token/")) {
      const p = new URLSearchParams(body);
      if (o.token) return o.token(p);
      n++;
      return json({ access_token: `act.access-${n}-${"a".repeat(20)}`, expires_in: 86400, open_id: "open-1", refresh_token: `rft.rotated-${n}-${"r".repeat(20)}`, refresh_expires_in: 31536000, scope: o.scope || "user.info.basic,video.publish", token_type: "Bearer" });
    }
    if (url.endsWith("/creator_info/query/")) return o.creator ? o.creator() : json({ data: { creator_username: "8ulduz.az", creator_nickname: "8ulduz", privacy_level_options: ["FOLLOWER_OF_CREATOR", "MUTUAL_FOLLOW_FRIENDS", "SELF_ONLY"], comment_disabled: false, duet_disabled: true, stitch_disabled: false, max_video_post_duration_sec: 600 }, error: { code: "ok" } });
    if (url.endsWith("/video/init/")) return o.init ? o.init(JSON.parse(body)) : json({ data: { publish_id: "v_pub_file~1", upload_url: "https://open-upload.tiktokapis.com/video/?upload_id=1&upload_token=t" }, error: { code: "ok" } });
    if (url.startsWith("https://open-upload.tiktokapis.com/")) return o.put ? o.put(init) : { ok: true, status: 201 };
    if (url.endsWith("/status/fetch/")) return o.status ? o.status(JSON.parse(body)) : json({ data: { status: "PUBLISH_COMPLETE" }, error: { code: "ok" } });
    throw new Error(`gözlənilməyən sorğu ${url}`);
  };
  return { fetch, calls, json };
}
const go = (dir, tk, o = {}) => {
  const logs = [];
  return T.run({ videos: T.readVideos(dir), env: { ...KEYS, ...o.env }, now: o.now ?? NOW, fetch: tk.fetch, state: o.state || {}, log: s => logs.push(s), policy: o.policy, reels: o.reels })
    .then(res => ({ res, logs }));
};
const noSecrets = (text, extra = []) => {
  for (const s of [KEYS.TIKTOK_CLIENT_SECRET, KEYS.TIKTOK_CLIENT_KEY, SEED, ...extra]) assert.ok(!text.includes(s), `jurnalda/state-də açar var: ${s.slice(0, 8)}…`);
  assert.ok(!/act\.access-|rft\.rotated-/.test(text), "jurnalda/state-də token var");
};

test("tiktok: no secrets (or TIKTOK=0) means nothing is sent and the job stays green", async () => {
  const dir = tmp(); video(dir, "a1");
  for (const env of [{}, { TIKTOK_CLIENT_KEY: "only-key-1" }, { ...KEYS, TIKTOK: "0" }]) {
    const tk = tiktok(), logs = [];
    const res = await T.run({ videos: T.readVideos(dir), env, now: NOW, fetch: tk.fetch, state: {}, log: s => logs.push(s) });
    assert.equal(tk.calls.length, 0);
    assert.deepEqual(res.failed, []);
    assert.match(logs.join("\n"), /açar yoxdur|söndürülüb/);
  }
});

test("tiktok: keys but no connected account yet → quiet skip with a pointer to docs/tiktok.md", async () => {
  const dir = tmp(); video(dir, "a2");
  const tk = tiktok();
  const { res, logs } = await go(dir, tk);
  assert.equal(tk.calls.length, 0);
  assert.deepEqual(res.failed, []);
  assert.match(logs.join("\n"), /hələ qoşulmayıb — docs\/tiktok\.md «Qoşulma»/);
});

test("tiktok: Direct Post — refresh, creator info, FILE_UPLOAD, status; unaudited private account falls back to SELF_ONLY", async () => {
  const dir = tmp(); video(dir, "b1", { hashtags: ["Metro", "#Bakı"], source: "APA", sourceUrl: "https://apa.az/x/1" });
  let polls = 0;
  const tk = tiktok({ status: () => tk.json({ data: { status: ++polls < 2 ? "PROCESSING_UPLOAD" : "PUBLISH_COMPLETE" }, error: { code: "ok" } }) });
  const state = {};
  const { res, logs } = await go(dir, tk, { state, env: { TIKTOK_REFRESH_TOKEN: SEED } });
  assert.deepEqual(res.posted, [["direct", "b1", "PUBLISH_COMPLETE"]]);
  const tok = new URLSearchParams(tk.calls[0].body);
  assert.equal(tok.get("grant_type"), "refresh_token");
  assert.equal(tok.get("refresh_token"), SEED, "ilk dəfə sirrdəki refresh token");
  const init = JSON.parse(tk.calls.find(c => c.url.endsWith("/video/init/")).body);
  assert.equal(init.post_info.privacy_level, "SELF_ONLY", "PUBLIC_TO_EVERYONE hesabın seçimlərində yoxdur (audit/gizli hesab)");
  assert.equal(init.post_info.disable_duet, true, "hesabın öz ayarı saxlanır");
  assert.equal(init.post_info.brand_content_toggle, false);
  assert.equal(init.post_info.is_aigc, false);
  assert.match(init.post_info.title, /^Bakıda yeni metro stansiyası b1\n\nStansiya sabah açılır\.\n\nƏtraflı: 8ulduz\.az \(keçid profildədir\)\n\n#Metro #Bakı #8ulduz #xəbərlər #Azərbaycan$/);
  const size = fs.statSync(path.join(dir, "b1.mp4")).size;
  assert.deepEqual(init.source_info, { source: "FILE_UPLOAD", video_size: size, chunk_size: size, total_chunk_count: 1 });
  const put = tk.calls.find(c => c.method === "PUT");
  assert.equal(put.headers["content-range"], `bytes 0-${size - 1}/${size}`);
  assert.equal(put.headers["content-type"], "video/mp4");
  assert.ok(put.body.equals(fs.readFileSync(path.join(dir, "b1.mp4"))), "fayl bayt-bayt göndərilir");
  assert.equal(tk.calls.find(c => c.url.endsWith("/video/init/")).headers.authorization, "Bearer act.access-1-" + "a".repeat(20));
  assert.equal(polls, 2, "status emal bitənə qədər soruşulur");
  assert.match(logs.join("\n"), /paylaşıldı — .*SELF_ONLY/);
  noSecrets(logs.join("\n") + JSON.stringify(state));
  assert.ok(state.auth && T.unseal(state.auth, KEYS.TIKTOK_CLIENT_SECRET).refresh === "rft.rotated-1-" + "r".repeat(20), "yeni refresh token şifrəli saxlanır");
  assert.equal(T.unseal(state.auth, "başqa açar"), null);

  // Eyni video ikinci dəfə getmir; access token hələ təzədir — TikTok-a heç bir sorğu yoxdur.
  const tk2 = tiktok();
  const r2 = await go(dir, tk2, { state, now: NOW + 2 * 3600e3, env: { TIKTOK_REFRESH_TOKEN: SEED } });
  assert.equal(tk2.calls.length, 0);
  assert.deepEqual(r2.res.posted, []);
  // Eyni fayl başqa adla (modul videonu yenidən yazıb) da getmir.
  const dir3 = tmp(); fs.copyFileSync(path.join(dir, "b1.mp4"), path.join(dir3, "b1-yeni.mp4"));
  fs.writeFileSync(path.join(dir3, "b1-yeni.json"), JSON.stringify({ id: "b1-yeni", own: true, title: "Başqa başlıq", createdAt: new Date(NOW).toISOString() }));
  const r3 = await go(dir3, tiktok(), { state, now: NOW + 2 * 3600e3, env: { TIKTOK_REFRESH_TOKEN: SEED } });
  assert.deepEqual(r3.res.posted, []);
  assert.match(r3.logs.join(" "), /artıq paylaşılıb/);
});

test("tiktok: the rotated refresh token is used next time (not the stale secret); a new secret restarts the chain", async () => {
  const state = {}, dir = tmp();
  video(dir, "c1");
  await go(dir, tiktok(), { state, env: { TIKTOK_REFRESH_TOKEN: SEED } });
  const dir2 = tmp(); video(dir2, "c2", { createdAt: new Date(NOW + 2 * 86400e3).toISOString() });
  const tk = tiktok();
  await go(dir2, tk, { state, now: NOW + 2 * 86400e3, env: { TIKTOK_REFRESH_TOKEN: SEED } });
  assert.equal(new URLSearchParams(tk.calls[0].body).get("refresh_token"), "rft.rotated-1-" + "r".repeat(20), "access köhnəlib: zəncirdəki token");
  const dir3 = tmp(); video(dir3, "c3", { createdAt: new Date(NOW + 4 * 86400e3).toISOString() });
  const tk3 = tiktok();
  await go(dir3, tk3, { state, now: NOW + 4 * 86400e3, env: { TIKTOK_REFRESH_TOKEN: "rft.owner-reconnected-111" } });
  assert.equal(new URLSearchParams(tk3.calls[0].body).get("refresh_token"), "rft.owner-reconnected-111", "sahib sirri yeniləyib: köhnə zəncir yox");
});

test("tiktok: token errors — a revoked token asks to reconnect (red); a TikTok outage keeps the chain", async () => {
  const dir = tmp(); video(dir, "d1");
  const bad = tiktok({ token: () => bad.json({ error: "invalid_grant", error_description: "Refresh token is invalid or expired." }, 400) });
  const state = {};
  const { res, logs } = await go(dir, bad, { state, env: { TIKTOK_REFRESH_TOKEN: SEED } });
  assert.deepEqual(res.failed, [["token", "invalid_grant"]]);
  assert.match(logs.join("\n"), /yenidən qoşulmalıdır/);
  noSecrets(logs.join("\n"));

  const ok = {};
  await go(dir, tiktok(), { state: ok, env: { TIKTOK_REFRESH_TOKEN: SEED } });
  const sealed = ok.auth;
  const dir2 = tmp(); video(dir2, "d2", { createdAt: new Date(NOW + 2 * 86400e3).toISOString() });
  const down = tiktok({ token: () => down.json({ error: "server_error" }, 503) });
  const r2 = await go(dir2, down, { state: ok, now: NOW + 2 * 86400e3, env: { TIKTOK_REFRESH_TOKEN: SEED } });
  assert.equal(ok.auth, sealed, "müvəqqəti xəta: zəncir silinmir");
  assert.match(r2.logs.join("\n"), /müvəqqəti xəta/);
});

// Video modulunun çıxışı (video-xeber.cjs, FB/IG video sessiyası): <çıxış>.json = { duration, width, height, bytes, cover_s, voice }
// + xəbərin sahələri və own: true (müqavilə, docs/tiktok.md §7).
test("tiktok: the video module's output — its text is the caption, cover_s the cover, too-long videos are not sent", async () => {
  const dir = tmp();
  const row = { id: "0123456789abcdef", title: "Bakıda yeni metro stansiyası açılır", summary: "Qısa.", category: "gundem", lang: "az", source: "APA", sourceUrl: "https://apa.az/1",
    publishedAt: new Date(NOW - 20 * 60e3).toISOString(), text: "Stansiya sabah sərnişin qəbul edəcək. Açılışda nazir iştirak edəcək." };
  video(dir, "v1", { ...row, own: true, duration: 42.5, width: 1080, height: 1920, bytes: 4000, cover_s: 2.4, voice: true });
  const tk = tiktok();
  const { res } = await go(dir, tk, { env: { TIKTOK_REFRESH_TOKEN: SEED } });
  assert.deepEqual(res.posted.map(x => x[1]), ["0123456789abcdef"], "videonun adı xəbərin nömrəsidir");
  const init = JSON.parse(tk.calls.find(c => c.url.endsWith("/video/init/")).body);
  assert.match(init.post_info.title, /^Bakıda yeni metro stansiyası açılır\n\nStansiya sabah sərnişin qəbul edəcək\. Açılışda nazir iştirak edəcək\.\n\nƏtraflı: 8ulduz\.az/);
  assert.equal(init.post_info.video_cover_timestamp_ms, 2400);

  const long = tmp(); video(long, "v2", { ...row, id: "v2", title: "Uzun video", own: true, duration: 700 });
  const tk2 = tiktok(), state = {};
  const r2 = await go(long, tk2, { state, env: { TIKTOK_REFRESH_TOKEN: SEED } });
  assert.ok(!tk2.calls.some(c => c.url.endsWith("/video/init/")), "hesabın həddi 600 s");
  assert.match(r2.logs.join("\n"), /video 700 s, hesabın həddi 600 s/);
  assert.equal(state.posted.v2.s, "FAILED:duration", "hər dövrədə yenə cəhd edilmir");

  // Modulun xəbər sahələri və own olmayan çıxışı (yalnız texniki sahələr) getmir.
  const bare = tmp(); video(bare, "v3", { id: undefined, title: undefined, own: undefined, duration: 30, bytes: 4000, cover_s: 2 });
  const r3 = await go(bare, tiktok(), { env: { TIKTOK_REFRESH_TOKEN: SEED } });
  assert.deepEqual(r3.res.skipped.map(x => x[1]), ["id/başlıq yoxdur"]);
});

test("tiktok: a network error after the token refresh does not crash the run; the new token is kept", async () => {
  const dir = tmp(); video(dir, "n1");
  const state = {};
  const base = tiktok();
  const fetch = (url, init) => (url.endsWith("/creator_info/query/") ? Promise.reject(Object.assign(new Error("fetch failed"), { cause: { code: "ECONNRESET" } })) : base.fetch(url, init));
  const logs = [];
  const res = await T.run({ videos: T.readVideos(dir), env: { ...KEYS, TIKTOK_REFRESH_TOKEN: SEED }, now: NOW, fetch, state, log: s => logs.push(s) });
  assert.deepEqual(res.failed, [["n1", "network"]]);
  assert.equal(T.unseal(state.auth, KEYS.TIKTOK_CLIENT_SECRET).refresh, "rft.rotated-1-" + "r".repeat(20));
  assert.match(logs.join("\n"), /alınmadı \(network: ECONNRESET\)/);
});

test("tiktok: the command line runs with the site's real policy file and without keys stays quiet (exit 0)", () => {
  const dir = tmp(); video(dir, "cli1");
  const r = require("child_process").spawnSync(process.execPath, [".github/scripts/tiktok.cjs", "post", dir], { cwd: path.join(__dirname, ".."), encoding: "utf8",
    env: { PATH: process.env.PATH, SYSTEMROOT: process.env.SYSTEMROOT || "", TIKTOK_STATE: path.join(dir, "state.json") } });
  assert.equal(r.status, 0, r.stderr);
  assert.match(r.stdout, /açar yoxdur/);
  assert.ok(fs.existsSync(path.join(dir, "state.json")), "state müvəqqəti qovluğa yazılır, repoya yox");
});

test("tiktok: only our own videos —no own flag, no 8ulduz.az mark, X/reels videos and foreign video links never go", async () => {
  const dir = tmp();
  video(dir, "e1", { own: false });
  video(dir, "e2", {}, mp4(4000, false));
  video(dir, "e3", { video: "https://video.twimg.com/amplify_video/1/vid/a.mp4" });
  video(dir, "2124472979207958907");
  video(dir, "e5", { sourceUrl: "https://x.com/F1/status/1", source: "F1" });
  video(dir, "e6", { clips: ["https://www.youtube.com/watch?v=1"] });
  fs.writeFileSync(path.join(dir, "e7.mp4"), "not a video"); fs.writeFileSync(path.join(dir, "e7.json"), JSON.stringify({ id: "e7", own: true, title: "Mətn", createdAt: new Date(NOW).toISOString() }));
  const tk = tiktok();
  const { res, logs } = await go(dir, tk, { env: { TIKTOK_REFRESH_TOKEN: SEED }, reels: new Set(["2124472979207958907"]) });
  assert.equal(tk.calls.length, 0, "namizəd yoxdur: TikTok-a sorğu da yoxdur");
  const why = Object.fromEntries(res.skipped);
  assert.match(why.e1, /own: true/);
  assert.match(why.e2, /8ulduz\.az» nişanı/);
  assert.match(why.e3, /başqa saytın videosu/);
  assert.match(why["2124472979207958907"], /data\/reels\.json/);
  assert.match(why.e5, /sosial şəbəkədəndir/);
  assert.match(why.e6, /başqa saytın videosu/);
  assert.match(why.e7, /mp4 deyil/);
  assert.match(logs.join("\n"), /yeni video yoxdur/);
});

test("tiktok: red line 2 — the video's stories pass the site's source rule", async () => {
  const dir = tmp();
  video(dir, "f1", { source: "Qadağan", sourceUrl: "https://example.org/1" });
  video(dir, "f2", { items: [{ title: "Yaxşı", source: "APA", sourceUrl: "https://apa.az/1" }, { title: "Xarici mənbədə Azərbaycan", source: "BBC", sourceUrl: "https://bbc.com/1" }] });
  const tk = tiktok();
  const policy = a => a.source === "Qadağan" || (a.source === "BBC" && /Azərbaycan/.test(a.title));
  const { res } = await go(dir, tk, { env: { TIKTOK_REFRESH_TOKEN: SEED }, policy });
  assert.equal(tk.calls.length, 0);
  assert.deepEqual(res.skipped.map(x => x[1]), ["mənbə qaydası (Qadağan)", "mənbə qaydası (BBC)"]);
  assert.equal(T.policyReason({ title: "Sınaq" }, () => true), "", "xəbəri olmayan öz video (sınaq) qaydaya düşmür");
});

test("tiktok: pacing — one video per run, gap, daily cap, stale videos, TikTok's own limits pause posting", async () => {
  const dir = tmp();
  video(dir, "g1", { createdAt: new Date(NOW - 50 * 60e3).toISOString() });
  video(dir, "g2", { createdAt: new Date(NOW - 10 * 60e3).toISOString() });
  video(dir, "g3", { createdAt: new Date(NOW - 13 * 3600e3).toISOString() });
  const state = {}, tk = tiktok();
  const { res, logs } = await go(dir, tk, { state, env: { TIKTOK_REFRESH_TOKEN: SEED } });
  assert.deepEqual(res.posted.map(x => x[1]), ["g2"], "ən təzəsi, dövrədə biri");
  assert.match(logs.join("\n"), /12 saatdan köhnədir/);
  const r2 = await go(dir, tiktok(), { state, now: NOW + 20 * 60e3, env: { TIKTOK_REFRESH_TOKEN: SEED } });
  assert.match(r2.logs.join("\n"), /növbəti 40 dəq sonra/);
  const r3 = await go(dir, tiktok(), { state, now: NOW + 61 * 60e3, env: { TIKTOK_REFRESH_TOKEN: SEED, TIKTOK_MAX_DAY: "1" } });
  assert.match(r3.logs.join("\n"), /24 saatda 1 video getdi \(hədd 1\)/);
  assert.equal(T.options({ TIKTOK_MAX_DAY: "50" }).maxDay, 15, "TikTok-un ~15/gün həddindən çox olmaz");
  assert.equal(T.options({ TIKTOK_MODE: "inbox", TIKTOK_MAX_DAY: "9" }).maxDay, 5, "qaralama: 24 saatda 5");

  const dirS = tmp(); video(dirS, "g4");
  const spam = tiktok({ init: () => spam.json({ data: {}, error: { code: "spam_risk_too_many_posts", message: "daily cap" } }, 403) });
  const sS = {};
  const rs = await go(dirS, spam, { state: sS, env: { TIKTOK_REFRESH_TOKEN: SEED } });
  assert.deepEqual(rs.res.failed, [["g4", "spam_risk_too_many_posts"]]);
  assert.equal(sS.pause, NOW / 1000 + 6 * 3600);
  const after = await go(dirS, tiktok(), { state: sS, now: NOW + 3600e3, env: { TIKTOK_REFRESH_TOKEN: SEED } });
  assert.match(after.logs.join("\n"), /fasilə, 300 dəq qalıb/);

  const una = tiktok({ init: () => una.json({ data: {}, error: { code: "unaudited_client_can_only_post_to_private_accounts", message: "" } }, 403) });
  const ru = await go(dirS, una, { state: {}, env: { TIKTOK_REFRESH_TOKEN: SEED } });
  assert.match(ru.logs.join("\n"), /auditdən keçməyib — TikTok yalnız GİZLİ hesaba/);
});

test("tiktok: big files go in 5–64 MB chunks (last ≤128 MB), small ones in one piece", () => {
  for (const size of [1, 4.9e6, 64e6, 64e6 + 1, 150e6, 999e6, 4e9]) {
    const p = T.chunks(size);
    assert.equal(p.parts.length, p.total_chunk_count);
    assert.equal(p.parts[0][0], 0);
    assert.equal(p.parts.at(-1)[1], size, "son bayt");
    for (let i = 1; i < p.parts.length; i++) assert.equal(p.parts[i][0], p.parts[i - 1][1], "ardıcıl");
    if (size <= 64e6) assert.deepEqual([p.total_chunk_count, p.chunk_size], [1, size]);
    else {
      assert.equal(p.total_chunk_count, Math.floor(size / p.chunk_size));
      assert.ok(p.chunk_size >= 5e6 && p.chunk_size <= 64e6);
      assert.ok(p.parts.at(-1)[1] - p.parts.at(-1)[0] <= 128e6 && p.total_chunk_count <= 1000);
    }
  }
});

test("tiktok: upload failure can be retried once; processing posts are checked on the next run", async () => {
  const dir = tmp(); video(dir, "h1");
  const state = {};
  const fail = tiktok({ put: () => ({ ok: false, status: 500 }) });
  const r1 = await go(dir, fail, { state, env: { TIKTOK_REFRESH_TOKEN: SEED } });
  assert.deepEqual(r1.res.failed, [["h1", "upload"]]);
  assert.equal(state.posted.h1.s, "upload_failed");
  const slow = tiktok({ status: () => slow.json({ data: { status: "PROCESSING_UPLOAD" }, error: { code: "ok" } }) });
  const r2 = await go(dir, slow, { state, now: NOW + 61 * 60e3, env: { TIKTOK_REFRESH_TOKEN: SEED, TIKTOK_POLLS: "2" } });
  assert.equal(slow.calls.filter(c => c.url.endsWith("/video/init/")).length, 1, "ikinci (son) cəhd");
  assert.equal(state.posted.h1.s, "PROCESSING_UPLOAD");
  assert.equal(state.posted.h1.a, 2);
  assert.match(r2.logs.join("\n"), /hələ emal olunur/);
  // int64 nömrə: JSON.parse 7400000000000000001-i 7400000000000000000 edir — xam cavabdan oxunmalıdır.
  const raw = '{"data":{"status":"PUBLISH_COMPLETE","publicaly_available_post_id":[7400000000000000001]},"error":{"code":"ok"}}';
  const done = tiktok({ status: () => ({ ok: true, status: 200, json: async () => JSON.parse(raw), text: async () => raw }) });
  const r3 = await go(tmp(), done, { state, now: NOW + 70 * 60e3, env: { TIKTOK_REFRESH_TOKEN: SEED } });
  assert.equal(done.calls.filter(c => c.url.endsWith("/status/fetch/")).length, 1, "gözləyən paylaşım yoxlanır");
  assert.equal(state.posted.h1.s, "PUBLISH_COMPLETE");
  assert.match(r3.logs.join("\n"), /ictimai: https:\/\/www\.tiktok\.com\/@8ulduz\.az\/video\/7400000000000000001/);
  const r4 = await go(dir, tiktok(), { state, now: NOW + 3 * 3600e3, env: { TIKTOK_REFRESH_TOKEN: SEED } });
  assert.deepEqual(r4.res.posted, [], "üçüncü dəfə getmir");
});

test("tiktok: inbox (draft) mode uses video.upload, sends no caption, tells the owner to finish in the app", async () => {
  const dir = tmp(); video(dir, "i1");
  const tk = tiktok({ scope: "user.info.basic,video.upload", status: () => tk.json({ data: { status: "SEND_TO_USER_INBOX" }, error: { code: "ok" } }) });
  const { res, logs } = await go(dir, tk, { env: { TIKTOK_REFRESH_TOKEN: SEED, TIKTOK_MODE: "inbox" } });
  const init = tk.calls.find(c => c.url.endsWith("/video/init/"));
  assert.equal(init.url, "https://open.tiktokapis.com/v2/post/publish/inbox/video/init/");
  assert.deepEqual(Object.keys(JSON.parse(init.body)), ["source_info"]);
  assert.ok(!tk.calls.some(c => c.url.endsWith("/creator_info/query/")));
  assert.deepEqual(res.posted, [["inbox", "i1", "SEND_TO_USER_INBOX"]]);
  assert.match(logs.join("\n"), /TikTok tətbiqində bildirişə toxunub dərc edin/);
  assert.match(T.authUrl({ TIKTOK_CLIENT_KEY: "k", TIKTOK_MODE: "inbox" }), /scope=user\.info\.basic%2Cvideo\.upload/);
});

test("tiktok: connecting — the code from the redirect address becomes an encrypted token chain; nothing secret is logged", async () => {
  assert.equal(T.codeFrom("https://8ulduz.az/haqqinda/?code=C0de%2Aabc_DEF%21&scopes=user.info.basic%2Cvideo.publish&state=8ulduz"), "C0de*abc_DEF!");
  assert.equal(T.codeFrom("  C0de*abc_DEF!  "), "C0de*abc_DEF!");
  assert.equal(T.codeFrom("salam"), "");
  const url = new URL(T.authUrl({ TIKTOK_CLIENT_KEY: "awkey" }));
  assert.deepEqual([url.origin + url.pathname, url.searchParams.get("redirect_uri"), url.searchParams.get("scope"), url.searchParams.get("response_type")],
    ["https://www.tiktok.com/v2/auth/authorize/", "https://8ulduz.az/haqqinda/", "user.info.basic,video.publish", "code"]);
  const tk = tiktok(), state = {}, logs = [], masked = [];
  await T.connect({ code: "https://8ulduz.az/haqqinda/?code=C0de%2Aabc_DEF%21&state=8ulduz", env: KEYS, now: NOW, fetch: tk.fetch, state, log: s => logs.push(s), mask: t => masked.push(t) });
  const p = new URLSearchParams(tk.calls[0].body);
  assert.deepEqual([p.get("grant_type"), p.get("code"), p.get("redirect_uri"), p.get("client_key")], ["authorization_code", "C0de*abc_DEF!", "https://8ulduz.az/haqqinda/", KEYS.TIKTOK_CLIENT_KEY]);
  assert.match(logs.join("\n"), /qoşuldu — 8ulduz \(@8ulduz\.az\).*token 365 gün işləyir/);
  noSecrets(logs.join("\n") + JSON.stringify(state), ["C0de*abc_DEF!"]);
  assert.ok(masked.includes("C0de*abc_DEF!") && masked.some(t => t.startsWith("rft.rotated-")), "Actions jurnalında da gizlədilir");
  assert.equal(T.unseal(state.auth, KEYS.TIKTOK_CLIENT_SECRET).scope, "user.info.basic,video.publish");
  const bad = tiktok({ token: () => bad.json({ error: "invalid_grant", error_description: "Authorization code is expired." }, 400) });
  await assert.rejects(T.connect({ code: "C0de*abc_DEF!", env: KEYS, now: NOW, fetch: bad.fetch, state: {}, log: () => {} }), /bir dəfəlikdir.*haqqinda/);
  await assert.rejects(T.connect({ code: "", env: KEYS, now: NOW, fetch: bad.fetch, state: {}, log: () => {} }), /kod tapılmadı/);
});

test("tiktok: caption fits TikTok (≤2200), ends with the site and hashtags", () => {
  const c = T.caption({ title: "Ş".repeat(500), summary: "Uzun ".repeat(800), hashtags: ["a b", "#c", "", "#"] });
  assert.ok(c.length <= 2200);
  assert.match(T.caption({ title: "Başlıq", summary: "Başlıq" }), /^Başlıq\n\nƏtraflı: 8ulduz\.az \(keçid profildədir\)\n\n#8ulduz #xəbərlər #Azərbaycan$/);
});

test("tiktok: workflow — own job, no write access, the code never sits in env, state cache survives re-runs", () => {
  const wf = fs.readFileSync(path.join(__dirname, "../.github/workflows/tiktok.yml"), "utf8");
  assert.ok(!/contents: write/.test(wf) && !/git push/.test(wf), "main-ə və budaqlara yazmır");
  assert.ok(!/inputs\.kod\s*}}/.test(wf.split("\n").filter(l => /^\s+[A-Z_]+:/.test(l)).join("\n")), "kod env-ə qoyulmur");
  assert.match(wf, /group: tiktok\n\s+cancel-in-progress: false/);
  assert.match(wf, /key: tiktok-state-\$\{\{ github\.run_id \}\}-\$\{\{ github\.run_attempt \}\}/);
  assert.match(wf, /workflow_call:/);
  const pr = wf.slice(wf.indexOf("  sinaq-video:"), wf.indexOf("  post:"));
  assert.ok(!/secrets\./.test(pr), "PR yoxlamasına açar verilmir");
  assert.match(wf, /if: github\.event_name != 'pull_request' && github\.ref == 'refs\/heads\/main'/);
});

test("tiktok: hooked to the video module — main only, real posting runs only, checked video only, TikTok secrets only", () => {
  const wf = fs.readFileSync(path.join(__dirname, "../.github/workflows/sosial-video.yml"), "utf8");
  const job = wf.slice(wf.indexOf("\n  tiktok:"));
  assert.ok(job.length > 20, "sosial-video.yml-də tiktok işi var");
  assert.match(job, /needs: video\n/);
  assert.match(job, /if: \$\{\{ !cancelled\(\) && github\.ref == 'refs\/heads\/main' && needs\.video\.outputs\.paylas == '1' && needs\.video\.outputs\.yoxlandi == '1' \}\}/);
  assert.match(job, /uses: \.\/\.github\/workflows\/tiktok\.yml\n\s+with:\n\s+artifact: video-xeber\n/);
  assert.ok(!/secrets: inherit|FB_PAGE_TOKEN/.test(job), "Facebook açarı TikTok işinə getmir");
  assert.deepEqual([...job.matchAll(/(TIKTOK_\w+): \$\{\{ secrets\.(TIKTOK_\w+) \}\}/g)].map(m => m[1] === m[2] && m[1]), ["TIKTOK_CLIENT_KEY", "TIKTOK_CLIENT_SECRET", "TIKTOK_REFRESH_TOKEN"]);
  // paylas: PR və paylas=false önizləməsində 0; yoxlandi: «Videonu yoxla» addımı keçəndə 1.
  assert.match(wf, /paylas: \$\{\{ steps\.sec\.outputs\.hazir == '1' && github\.event_name != 'pull_request' && \(github\.event_name != 'workflow_dispatch' \|\| inputs\.paylas\) && '1' \|\| '0' \}\}/);
  assert.match(wf, /yoxlandi: \$\{\{ steps\.yoxla\.outcome == 'success' && '1' \|\| '0' \}\}/);
  assert.match(wf, /- name: Videonu yoxla\n\s+id: yoxla\n/);
  // Seçim TikTok açarı ilə də işləyir (YouTube açarı ilə də: youtube.yml); FB/IG addımı açarı əvvəlki kimi alır.
  assert.match(wf, /VIDEO_ACAR: \$\{\{ \(secrets\.FB_PAGE_TOKEN != '' \|\| \(secrets\.TIKTOK_CLIENT_KEY != '' && secrets\.TIKTOK_CLIENT_SECRET != ''\) \|\| \(secrets\.YOUTUBE_CLIENT_ID != '' && secrets\.YOUTUBE_CLIENT_SECRET != '' && secrets\.YOUTUBE_REFRESH_TOKEN != ''\)\) && '1' \|\| '0' \}\}/);
  const tk = fs.readFileSync(path.join(__dirname, "../.github/workflows/tiktok.yml"), "utf8");
  const call = tk.slice(tk.indexOf("workflow_call:"), tk.indexOf("workflow_dispatch:"));
  for (const s of ["TIKTOK_CLIENT_KEY", "TIKTOK_CLIENT_SECRET", "TIKTOK_REFRESH_TOKEN"]) assert.match(call, new RegExp(`${s}:\\n\\s+required: false`), `${s} workflow_call-da elan olunub`);
  // Facebook açarı olmayanda FB/IG addımı heç nə göndərmir (şəbəkə siyahısı boşdur), iş qırmızı olmur.
  assert.deepEqual(require("../.github/scripts/sosial-video.cjs").networks({ FB_PAGE_ID: "1" }), []);
});

// tiktok.yml «sinaq-video»: ffmpeg-in hazırladığı əsl 9:16 video eyni yoldan keçir (yerdə ffmpeg yoxdursa ötürülür).
test("tiktok: a real ffmpeg test video passes the own-video check and is uploaded byte for byte", { skip: !process.env.TIKTOK_TEST_DIR && "TIKTOK_TEST_DIR yoxdur (ffmpeg yalnız tiktok.yml-də)" }, async () => {
  const dir = process.env.TIKTOK_TEST_DIR, vids = T.readVideos(dir);
  assert.equal(vids.length, 1);
  const buf = fs.readFileSync(vids[0].file);
  assert.equal(T.foreignReason(vids[0].meta, buf), "", "own: true və faylda 8ulduz.az nişanı");
  assert.ok(buf.length > 20000 && buf.length < 64e6);
  const probe = require("child_process").spawnSync("ffprobe", ["-v", "error", "-select_streams", "v:0", "-show_entries", "stream=codec_name,width,height,r_frame_rate:format=duration", "-of", "json", vids[0].file], { encoding: "utf8" });
  if (probe.status === 0) {
    const j = JSON.parse(probe.stdout), s = j.streams[0];
    assert.deepEqual([s.codec_name, s.width, s.height, s.r_frame_rate], ["h264", 1080, 1920, "30/1"], "TikTok: H.264, 9:16, 23–60 kadr/s");
    assert.ok(Number(j.format.duration) >= 5 && Number(j.format.duration) <= 600);
  }
  const tk = tiktok(), state = {};
  const { res } = await go(dir, tk, { state, env: { TIKTOK_REFRESH_TOKEN: SEED } });
  assert.equal(res.posted.length, 1);
  const init = JSON.parse(tk.calls.find(c => c.url.endsWith("/video/init/")).body);
  assert.equal(init.post_info.privacy_level, "SELF_ONLY", "sınaq həmişə yalnız sahibə görünür");
  assert.ok(tk.calls.find(c => c.method === "PUT").body.equals(buf));
});
