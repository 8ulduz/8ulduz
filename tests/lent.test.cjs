// Videolent (assets/lent.js): TikTok kimi qarışıq axın və canlı təzələnmə (sahib, 2026-11-19).
const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const { pathToFileURL } = require('node:url');
const file = path.join(__dirname, '..', 'assets', 'lent.js');

test('Videolent: the same account never plays twice in a row while others remain, nothing is lost', async () => {
  const { mix } = await import(pathToFileURL(file).href);
  const list = [];
  for (let i = 0; i < 30; i++) list.push({ u: `u${i}`, n: i < 20 ? 'NBA' : `A${i % 3}` });
  for (let k = 0; k < 20; k++) {
    const out = mix(list);
    assert.equal(out.length, list.length);
    assert.deepEqual(new Set(out.map(v => v.u)), new Set(list.map(v => v.u)));
    const firstRun = out.findIndex((v, i) => i && v.n === out[i - 1].n);
    const othersLeft = firstRun > 0 && out.slice(firstRun).some(v => v.n !== out[firstRun].n);
    assert.ok(!othersLeft, 'ardıcıl eyni hesab yalnız başqa hesab qalmayanda');
  }
});

test('Videolent: new videos arrive while the feed is open, the next video is preloaded, every slide can be shared', () => {
  const src = fs.readFileSync(file, 'utf8');
  assert.match(src, /const FRESH_MS = 60e3/, 'dəqiqədə bir yeni video yoxlanır');
  assert.ok(src.includes('document.visibilityState !== "visible"'), 'vərəq gizlidirsə sorğu yoxdur');
  assert.ok(src.includes('clearInterval(live.fresh)'), 'bağlananda yoxlama dayanır');
  assert.ok(src.includes('n.preload = "auto"; n.src = n.dataset.src'), 'yalnız növbəti video əvvəlcədən yüklənir');
  assert.ok(src.includes('class="sh"') && src.includes('navigator.share'), 'Paylaş düyməsi');
});

test('Videolent: topics take turns, football cannot fill the feed (owner 2026-11-19: «proporsional olsun müxtəlif mövzular»)', async () => {
  const { mix } = await import(pathToFileURL(file).href);
  const list = [];
  for (let i = 0; i < 40; i++) list.push({ u: `f${i}`, n: `club${i % 8}`, m: 'idman' });
  for (const m of ['tebiet', 'elm', 'kino', 'oyun']) for (let i = 0; i < 5; i++) list.push({ u: `${m}${i}`, n: `${m}${i % 2}`, m });
  const out = mix(list);
  const first10 = out.slice(0, 10).filter(v => v.m === 'idman').length;
  assert.ok(first10 <= 3, `ilk 10 videoda idman ${first10}: mövzular növbə ilə`);
  assert.equal(out.length, list.length);
});

test('Videolent: the news job starts the video writer every 20 minutes (GitHub cron skipped it for 11 hours, 2026-11-19/20), never twice at once, many videos per run', () => {
  const root = path.join(__dirname, '..');
  const sh = fs.readFileSync(path.join(root, '.github/scripts/pipeline.sh'), 'utf8');
  const at = sh.indexOf('xyazici_loop() {'), loop = sh.slice(at, sh.indexOf('\n}\n', at));
  assert.ok(at > 0 && loop.includes('/ 1200 ))'), '20 dəqiqəlik pəncərə');
  assert.ok(loop.includes('gh_t workflow run x-yazici.yml --ref main') && loop.includes('select(.status != "completed")'), 'yalnız dispatch, gedən iş varsa yox');
  assert.ok(!/GEMINI|fxtwitter|curl |python/.test(loop), 'açar və X sorğusu bu döngüdə yoxdur');
  assert.ok(sh.includes('xyazici_loop &\nXYAZICI_PID=$!') && sh.includes('kill "$XYAZICI_PID"'));
  const xy = fs.readFileSync(path.join(root, '.github/scripts/x_yazici.py'), 'utf8');
  const oz = fs.readFileSync(path.join(root, 'oz_x.py'), 'utf8');
  assert.ok(+xy.match(/^REELS_PER_RUN = (\d+)/m)[1] >= 12, 'bir işdə ən azı 12 video (sahib: «çox sayda»)');
  assert.ok(+oz.match(/^REELS_MAX = (\d+)/m)[1] >= 72 * 12 / 2 * 1.5, 'lent ən azı 1,5 günlük axını tutur');
});

test('Videolent: the feed never ends — when unseen videos run out, the longest-ago seen come back, never the last ones (owner 2026-11-20)', async () => {
  const { replay } = await import(pathToFileURL(file).href);
  const pool = Array.from({ length: 40 }, (_, i) => ({ u: `v${i}`, n: `a${i % 7}`, m: ['idman', 'elm', 'kino'][i % 3] }));
  const order = pool.map(v => v.u);   // v0 ən çoxdan, v39 ən son görülüb
  const out = replay(pool, order);
  assert.ok(out.length >= 20, 'lentin sonuna yeni dəstə gəlir');
  assert.ok(!out.some(v => order.slice(-15).includes(v.u)), 'son baxılan 15 video dərhal təkrar gəlmir');
  assert.ok(out.some(v => v.u === 'v0'), 'ən çoxdan görülən qayıdır');
  assert.ok(replay(pool.slice(0, 6), order.slice(0, 6)).length >= 3, 'az video olanda da lent dövr edir');
  const src = fs.readFileSync(file, 'utf8');
  assert.ok(src.includes('if (live.at >= slides.length - 3) refill()'), 'sona 3 video qalanda doldurulur');
  assert.ok(!src.includes('Hamısını izlədiniz'), 'lent «bitdi» demir');
  assert.ok(+src.match(/SEEN_MAX = (\d+)/)[1] >= 2000, 'görülənlərin yaddaşı lentdən böyükdür: təkrar «təzə» kimi gəlmir');
});

test('Videolent: videos come from the minute live channel (writer → site ~5 min, not 25–30), the site file is the fallback', () => {
  const src = fs.readFileSync(file, 'utf8');
  assert.ok(src.includes('"https://raw.githubusercontent.com/8ulduz/8ulduz/live/m/"') && src.includes('/reels.json`'), 'canlı kanal');
  assert.ok(src.includes('credentials: "omit"'), 'kuki göndərilmir');
  const sh = fs.readFileSync(path.join(__dirname, '..', '.github/scripts/pipeline.sh'), 'utf8');
  assert.ok(sh.includes('markets social; do') && sh.includes('  for name in reels canli; do'), 'push_live reels.json-u da göndərir');
  const pull = sh.slice(sh.indexOf('pull_reel_src() {'), sh.indexOf('\n}\n', sh.indexOf('pull_reel_src() {')));
  assert.ok(pull.includes('contents/$src?ref=main') && pull.includes('*_x.json)') && pull.includes('json.load') && !pull.includes('git '), 'yalnız oz_x.json, yoxlanır, git toqquşması yoxdur');
  assert.ok(sh.includes('[ -f "$STATE/reel-src.new" ] && mv -f "$STATE/reel-src.new" "$CUR/$(cat "$STATE/reel-src.name")"'), 'əsas döngü yerli faylı qoyur, şəbəkə yox');
});

test('Videolent: a big swipe-up arrow shows on the first open only (owner 2026-11-20)', () => {
  const src = fs.readFileSync(file, 'utf8');
  assert.ok(src.includes('const HINT_KEY = "8u-reels-hint"'));
  assert.ok(/hinted = !!localStorage\.getItem\(HINT_KEY\)/.test(src) && src.includes('localStorage.setItem(HINT_KEY, "1")'), 'bir dəfə göstərilir, telefonda yadda qalır');
  assert.ok(src.includes('feed.addEventListener("scroll", off, { once: true, passive: true })') && src.includes('setTimeout(off, 4500)'), 'sürüşdürəndə və ya 4,5 s sonra çəkilir');
});

test('Videolent: share opens our site at the same video, the source stays one tap away (owner 2026-11-20)', async () => {
  const { shareLink, first } = await import(pathToFileURL(file).href);
  assert.equal(shareLink({ k: '2123793500739404215', link: 'https://x.com/a/status/2123793500739404215' }), 'https://8ulduz.az/#/videolent?r=2123793500739404215');
  const items = [{ k: 'a' }, { k: 'b' }, { k: 'c' }];
  assert.deepEqual(first(items, 'c').map(v => v.k), ['c', 'a', 'b'], 'paylaşılan video birinci');
  assert.deepEqual(first(items, 'yox').map(v => v.k), ['a', 'b', 'c'], 'video artıq yoxdursa lent adi qaydada');
  const src = fs.readFileSync(file, 'utf8');
  assert.ok(src.includes('data-link="${esc(shareLink(v))}"') && !src.includes('data-link="${esc(v.link)}"'), 'paylaş düyməsi X-ə yox, sayta aparır');
  assert.ok(src.includes('"X-də bax ↗"'), 'mənbəyə keçid qalır');
  const app = fs.readFileSync(path.join(__dirname, '..', 'assets', 'app.js'), 'utf8');
  assert.ok(app.includes('import("./lent.js?v=1").then(m => m.open(S, r.reel))'), '#/videolent?r= lenti həmin videodan açır');
});

test('Videolent: the 8ulduz logo sits over every video and takes the reader back to the site, like ✕ (owner 2026-11-20)', () => {
  const src = fs.readFileSync(file, 'utf8');
  assert.ok(src.includes('<button class="lg" type="button" aria-label="8ulduz.az — sayta qayıt"><img src="${LOGO}"'));
  assert.ok(src.includes('doc.querySelector(".lg").addEventListener("click", back);'));
  assert.ok(/\.lg\{left:12px;right:auto;top:calc\(12px/.test(src), 'yuxarıda solda, hər videonun üstündə (sabit)');
});

test('Videolent: #/videolent?r=<id> is read from the address (the shared link really opens that video)', () => {
  const app = fs.readFileSync(path.join(__dirname, '..', 'assets', 'app.js'), 'utf8');
  const m = app.match(/name: "videos", reel: \(h\.match\((\/.*?\/)\) \|\| \[\]\)\[1\]/);
  assert.ok(m, 'videolent marşrutu r= oxuyur');
  const rx = eval(m[1]);
  assert.equal(('/videolent?r=2123748200729210898'.match(rx) || [])[1], '2123748200729210898');
  assert.equal(('/videolent?x=1&r=ab_c-9'.match(rx) || [])[1], 'ab_c-9');
  assert.equal('/videolent'.match(rx), null);
});
