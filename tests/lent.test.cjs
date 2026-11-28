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
  assert.ok(+oz.match(/^REELS_MAX = (\d+)/m)[1] >= 1000, 'sahib 2026-11-22: «video sayı 1000 olsun»');
  const seen = fs.readFileSync(path.join(root, 'assets/lent.js'), 'utf8').match(/SEEN_MAX = (\d+)/);
  assert.ok(+seen[1] > +oz.match(/^REELS_MAX = (\d+)/m)[1], 'izlənmiş yaddaşı lentdən böyükdür: video təkrar «təzə» olmur');
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
  assert.ok(src.includes('if (live.at >= slides.length - 3) grow()') && src.includes('const grow = () => { if (queue.length) put(queue.splice(0, CHUNK), null); else refill(); };'),
    'sona 3 video qalanda doldurulur: əvvəl qurulmamış slaydlar, onlar bitəndə təzə videolar');
  assert.ok(!src.includes('Hamısını izlədiniz'), 'lent «bitdi» demir');
  assert.ok(+src.match(/SEEN_MAX = (\d+)/)[1] >= 2000, 'görülənlərin yaddaşı lentdən böyükdür: təkrar «təzə» kimi gəlmir');
});

test('Videolent: videos come from the minute live channel (writer → site ~5 min, not 25–30), the site file is the fallback', () => {
  const src = fs.readFileSync(file, 'utf8');
  assert.ok(src.includes('"https://raw.githubusercontent.com/8ulduz/8ulduz/live/m/"') && src.includes('/reels.json`'), 'canlı kanal');
  assert.ok(src.includes('credentials: "omit"'), 'kuki göndərilmir');
  const sh = fs.readFileSync(path.join(__dirname, '..', '.github/scripts/pipeline.sh'), 'utf8');
  assert.ok(sh.includes('markets social; do') && sh.includes('  for name in reels canli; do'), 'push_live reels.json-u da göndərir');
  const fn = name => sh.slice(sh.indexOf(`${name}() {`), sh.indexOf('\n}\n', sh.indexOf(`${name}() {`)));
  const pull = fn('pull_reel_src'), apply = fn('apply_queue');
  // Sahib 2026-11-27: növbə main-də yox, x-novbe budağındadır; main yalnız budaq hələ yoxdursa (404) və bu işdə görünməyibsə oxunur.
  assert.ok(sh.includes('NOVBE_BRANCH="${NOVBE_BRANCH:-x-novbe}"') && fn('novbe_file').includes('*_x.json)'), 'yalnız oz_x.json');
  assert.ok(pull.includes('contents/$src?ref=$ref') && pull.includes('ref="refs/heads/$NOVBE_BRANCH"') && pull.includes('json.load') && !pull.includes('git '), 'budaqdan, yoxlanır, git toqquşması yoxdur');
  assert.ok(/if \[ -e "\$STATE\/novbe-budaq" \] \|\| ! grep -q "\(HTTP 404\)" "\$err"; then rm -f "\$tmp" "\$err"; return 1; fi\n\s+ref="refs\/heads\/main"/.test(pull),
    'main-ə yalnız budaq yoxdursa keçir; şəbəkə xətasında və budaq görünəndən sonra yox');
  assert.ok(apply.includes('mv -f "$CUR/$src.yeni" "$CUR/$src"'), 'növbə kod qovluğuna atomik qoyulur: yavaş dövrə yarımçıq fayl oxumur');
  const loop = sh.slice(sh.indexOf('\nwhile :; do\n  began=$SECONDS'));
  assert.ok(loop.includes('if [ -e "$STATE/novbe.yeni" ]; then rm -f "$STATE/novbe.yeni"; apply_queue; fi'), 'əsas döngü yerli faylı qoyur, şəbəkə yox');
  assert.ok(loop.includes('if [ -e "$STATE/novbe-budaq" ]; then copy_code "$REPO_DIR" "$CUR" "$(novbe_file)"; else copy_code "$REPO_DIR" "$CUR"; fi'),
    'main yazısından sonra main-in donmuş oz_x.json-u budağın nüsxəsinin üstünə yazılmır');
  const start = sh.slice(sh.indexOf('# --------------------------------------------------------------------- başlanğıc'));
  assert.ok(start.indexOf('pull_reel_src || { sleep 5; pull_reel_src; }') > start.indexOf('copy_code "$REPO_DIR" "$CUR"')
    && start.indexOf('apply_queue') < start.indexOf('\nslow_loop &'), 'işin əvvəlində budağın nüsxəsi yavaş dövrədən əvvəl gəlir');
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

test('Videolent: «8ulduz.az» sits over every video and takes the reader back to the site, like ✕ (owner 2026-11-20, 2026-11-22)', () => {
  const src = fs.readFileSync(file, 'utf8');
  assert.ok(src.includes('<button class="lg" type="button" aria-label="8ulduz.az — sayta qayıt">8ulduz<i>.az</i></button>'), 'yazı: 8ulduz.az');
  assert.ok(!src.includes('logo-80.png'), 'şəkil yox, yazı: əlavə sorğu yoxdur');
  assert.ok(src.includes('doc.querySelector(".lg").addEventListener("click", back);'));
  assert.ok(/\.lg\{left:12px;right:auto;top:calc\(12px/.test(src), 'yuxarıda solda, hər videonun üstündə (sabit)');
});

test('Videolent: the share button says «Paylaş» like the site (owner 2026-11-22)', () => {
  const src = fs.readFileSync(file, 'utf8');
  assert.ok(src.includes('data-title="${esc(v.title || v.c || v.n)}">Paylaş</button></section>'), 'düymədə «Paylaş» yazısı');
  assert.ok(src.includes('sh.textContent = "Paylaş"'), 'kopyalanandan sonra yenə «Paylaş»');
});

test('Videolent: a shared video opens at once — the black frame does not wait for the video list or the news (owner 2026-11-22)', async () => {
  const src = fs.readFileSync(file, 'utf8').replace(/\r\n/g, '\n');
  const at = s => { const i = src.indexOf(s); assert.ok(i > 0, s); return i; };
  assert.ok(at('document.body.append(f);\n  const t = Date.now();') < at('items = list(S, await load(t, OPEN_MS));')
    && at('items = list(S, await load(t, OPEN_MS));') < at('build(f, first(items, k), () => history.back()'),
    'çərçivə siyahıdan əvvəl açılır, siyahı gələndə dolur');
  assert.ok(src.includes('<body><div class="wait"></div></body>'), 'arada fırlanan işarə');
  const app = fs.readFileSync(path.join(__dirname, '..', 'assets', 'app.js'), 'utf8');
  assert.ok(app.includes('if (!r.reel || S.reelAt === r.reel || !S.data && !/^\\d{17,}$/.test(r.reel)) return;'), 'X videosu xəbərləri gözləmir');
  const rx = /^\d{17,}$/;
  assert.ok(rx.test('2123875512364024026'), 'X açarı');
  assert.ok(!rx.test('d1361f50c15d6e00') && !rx.test('1234567890123456'), 'öz xəbərimizin 16 simvolluq açarı xəbərləri gözləyir');
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

test('Videolent: first-degree sources (reels «p») lead each topic, topics still alternate (owner 2026-11-20)', async () => {
  const { mix } = await import(pathToFileURL(file).href);
  const list = [
    { u: 's1', n: 'A', m: 'idman' }, { u: 's2', n: 'B', m: 'idman' }, { u: 'sp', n: 'nocontextfooty', m: 'idman', p: true },
    { u: 't1', n: 'C', m: 'tebiet' }, { u: 'tp', n: 'buitengebieden', m: 'tebiet', p: true },
  ];
  for (let i = 0; i < 10; i++) {
    const out = mix(list).map(v => v.u);
    assert.deepEqual(new Set(out.slice(0, 2)), new Set(['sp', 'tp']), 'hər mövzunun ilk videosu birinci dərəcəli mənbədəndir');
    assert.equal(out.length, 5);
  }
  const src = fs.readFileSync(file, 'utf8');
  assert.ok(src.includes('p: r.p === 1'), 'reels.json-dakı «p» lentə keçir');
});

test('Videolent: events and craft videos come 3:2 — 60% / 40% (owner 2026-11-22), the caption explains each video', async () => {
  const { mix } = await import(pathToFileURL(file).href);
  const list = [];
  for (let i = 0; i < 30; i++) list.push({ u: `h${i}`, n: `H${i % 6}`, m: ['idman', 'xeber', 'texnika'][i % 3], q: 'h' });
  for (let i = 0; i < 20; i++) list.push({ u: `u${i}`, n: `U${i % 5}`, m: ['yemek', 'elm'][i % 2], q: 'u' });
  for (let k = 0; k < 10; k++) {
    const out = mix(list);
    assert.equal(out.length, 50);
    const first10 = out.slice(0, 10).filter(v => v.q === 'u').length;
    assert.ok(first10 >= 3 && first10 <= 5, `ilk 10 videoda usta işi ${first10}: təxminən 4`);
    const all = out.filter(v => v.q === 'u').length;
    assert.equal(all, 20);
  }
  const onlyH = mix(list.filter(v => v.q === 'h'));
  assert.equal(onlyH.length, 30, 'bir sinif yoxdursa o biri tam gəlir');
  const src = fs.readFileSync(file, 'utf8');
  assert.ok(src.includes('const PATTERN = [0, 0, 1, 0, 1];'), 'h h u h u');
  assert.ok(src.includes('q: r.q === "u" ? "u" : "h"') && src.includes('${v.title || v.c ? `<span>${esc(v.title || v.c)}</span>` : ""}'), 'izah hesabın adının altında');
  assert.ok(src.includes('data-title="${esc(v.title || v.c || v.n)}"'), 'paylaşımda da izah');
});

// Sahib 2026-11-23: «videolent tapşırığım düzgün və tam icra olunmayıb. 3 dəfə açmışam hər dəfə öncə baxdığım video çıxıb.
// hadisə və xəbər xarakterli videolarla bağlı da vəziyyət düzgün deyil.»
const store = (fail = false) => {
  const m = new Map();
  const ls = { getItem: k => (fail ? null : m.get(k) ?? null), setItem: (k, v) => { if (fail) throw new Error('QuotaExceededError'); m.set(k, String(v)); }, removeItem: k => m.delete(k), m };
  Object.defineProperty(globalThis, 'localStorage', { value: ls, configurable: true, writable: true });
  return ls;
};
const HOUR = 3600e3, NOW = Date.parse('2026-11-23T15:00:00Z');
const mp4 = (id, size = '480x852', tag = 29) => `https://video.twimg.com/amplify_video/${id}/vid/avc1/${size}/a${id % 97n}.mp4?tag=${tag}`;
function feed() {   // reels.json kimi: 4 xəbər, 10 başqa hadisə (5 mövzu), 6 usta işi; hər biri başqa yaşda
  const rows = [], add = (i, m, q, a, hours, p) => rows.push({ id: String(2124800000000000000n + BigInt(i)), a, n: a, m, q, u: mp4(2124000000000000000n + BigInt(i)),
    i: '', w: 720, h: 1280, t: new Date(NOW - hours * HOUR).toISOString(), c: `İzah ${i}`, ...(p ? { p: 1 } : {}) });
  for (let i = 0; i < 4; i++) add(i, 'xeber', 'h', `X${i}`, 1 + i * 3);
  for (let i = 0; i < 10; i++) add(10 + i, ['idman', 'tebiet', 'elm', 'kino', 'texnika'][i % 5], 'h', `H${i}`, 2 + i);
  for (let i = 0; i < 6; i++) add(30 + i, ['yemek', 'texnika', 'elm'][i % 3], 'u', `U${i}`, 5 + i * 10);
  return rows;
}

test('Videolent: three opens in a row never start with a video already watched, even when it comes back under another address (owner 2026-11-23)', async () => {
  const { list, first, markSeen, seenOrder, vkey } = await import(pathToFileURL(file).href);
  store();
  const reels = feed(), firsts = [];
  for (let open = 0; open < 3; open++) {
    const items = first(list({}, reels), '');
    assert.ok(!seenOrder().includes(vkey(items[0].u)), `açılış ${open + 1}: birinci video əvvəl izlənməyib`);
    firsts.push(items[0].k);
    markSeen(items[0].u); markSeen(items[1].u);   // oxucu 1–2 videoya baxıb bağlayır
  }
  assert.equal(new Set(firsts).size, 3, 'hər açılış başqa videodan başlayır');
  // eyni video başqa ölçüdə, başqa ?tag= ilə və ya başqa paylaşımda: yenə izlənmiş sayılır
  const watched = reels.find(r => vkey(r.u) === seenOrder()[0]);
  const again = { ...watched, id: '2124899999999999999', u: watched.u.replace('480x852', '720x1280').replace('tag=29', 'tag=12') };
  const items = list({}, [...reels, again]);
  assert.equal(items.filter(v => v.key === vkey(again.u)).length, 1, 'eyni video lentdə bir dəfə');
  assert.ok(items.findIndex(v => v.key === vkey(again.u)) >= items.length - seenOrder().length, 'başqa ünvanla gələn izlənmiş video sona keçir');
  // köhnə yaddaş (2026-11-23-ə qədər ünvan saxlanırdı) da oxunur
  const ls = store();
  ls.setItem('8u-reels-seen', JSON.stringify(reels.slice(0, 5).map(r => r.u)));
  assert.ok(!reels.slice(0, 5).some(r => vkey(r.u) === list({}, reels)[0].key), 'köhnə yaddaşdakı ünvanlar da izlənmiş sayılır');
});

test('Videolent: when every video has been watched the longest-ago one comes back first, never the last one (owner 2026-11-20, 2026-11-23)', async () => {
  const { list, markSeen, vkey } = await import(pathToFileURL(file).href);
  store();
  const reels = feed();
  for (const r of reels) markSeen(r.u);   // hamısına baxılıb: ən çoxdan baxılan reels[0]
  markSeen(reels[0].u);                   // reels[0]-a ən son yenidən baxılıb
  const items = list({}, reels);
  assert.equal(items[0].key, vkey(reels[1].u), 'ən çoxdan baxılan birinci');
  assert.equal(items.at(-1).key, vkey(reels[0].u), 'ən son baxılan ən sonda');
});

// Sahib 2026-11-24: «vatsapda videolentdən paylaşılanda həmin videoya qayıtmır … tam birdəfəlik düzəlt. artıq neçənci dəfədir deyirəm».
// 2026-11-23-dən izlənmiş paylaşılan video ikinci gəlirdi: paylaşan öz keçidini açanda başqa video görürdü.
test('Videolent: a shared link ALWAYS opens that very video first, even if this phone has watched it (owner 2026-11-24)', async () => {
  const { list, first, markSeen } = await import(pathToFileURL(file).href);
  store();
  const reels = feed(), shared = reels[7];
  assert.equal(first(list({}, reels), shared.id)[0].k, shared.id, 'izlənməmiş paylaşılan video birinci');
  markSeen(shared.u);
  const items = first(list({}, reels), shared.id);
  assert.equal(items[0].k, shared.id, 'izlənmiş olsa da birinci');
  assert.equal(items.length, list({}, reels).length, 'heç nə itmir');
});

test('Videolent: the shared link shows no site flash — black screen, the module at once; returning after sharing lands on the same video (owner 2026-11-24)', () => {
  const crypto = require('node:crypto');
  const html = fs.readFileSync(path.join(__dirname, '..', 'index.html'), 'utf8').replace(/\r\n/g, '\n');
  const body = html.match(/<script>([\s\S]*?)<\/script>/)[1];
  assert.ok(html.match(/script-src[^;"]*/)[0].includes(`'sha256-${crypto.createHash('sha256').update(body).digest('base64')}'`), 'CSP hash');
  assert.ok(!/<style\b/.test(html), 'index.html-də daxili CSS yoxdur (açılış müqaviləsi)');
  assert.ok(body.includes('st.id = "reels-boot"; st.textContent = "html{background:#000}body{visibility:hidden}";'), 'yalnız lent keçidində: sayt görünmür, qara ekran');
  assert.ok(body.includes('lp.rel = "modulepreload"; lp.href = "./assets/lent.js?v=1";'), 'lent modulu dərhal');
  assert.ok(body.includes('setTimeout(function () { if (st.parentNode) st.parentNode.removeChild(st); }, 8000);'), 'lent alınmasa sayt 8 s sonra görünür');
  // Yalnız paylaşılan videonun keçidi: #/videolent özü «Video xəbərlər» səhifəsidir.
  const re = new RegExp(body.match(/location\.hash\.match\((\/\^#[^\n]*?\/)\)/)[1].slice(1, -1));
  assert.equal(('#/videolent?r=2125245555639042179'.match(re) || [])[1], '2125245555639042179');
  assert.equal('#/videolent'.match(re), null);
  assert.equal('#/'.match(re), null);
  // Lent açıq ikən səhifə yenidən yüklənibsə (telefon WhatsApp-a paylaşanda səhifəni boşaldıb, geri, yeniləmə) — həmin video.
  assert.ok(body.includes('sessionStorage.getItem("8u-reels-at")') && body.includes('document.wasDiscarded || nav === "reload" || nav === "back_forward"')
    && body.includes('history.replaceState(null, "", "#/videolent?r=" + ra.k)'), 'izlənən videoya qayıdış');
  assert.ok(body.indexOf('8u-reels-at') < body.indexOf('var home ='), 'qayıdış marşrutdan əvvəl: qara ekran da işləyir');
  const src = fs.readFileSync(file, 'utf8').replace(/\r\n/g, '\n');
  assert.ok(src.includes('markSeen(vid(s).dataset.src);\n    atSave(s.dataset.k);') && src.includes('const slide = v => `<section data-k="${esc(v.k || "")}"'), 'oynayan video yadda saxlanır');
  assert.ok(/const close = \(\) => \{[\s\S]*?atDrop\(\);\n    siteShow\(\);/.test(src), 'bağlananda unudulur, sayt görünür');
  assert.ok(src.includes('z-index:2147483000;background:#000;visibility:visible'), 'lent gizli saytın içində görünür');
  assert.ok(src.includes('document.addEventListener("visibilitychange", live.vis);') && src.includes('!s.classList.contains("p") && vid(s).paused) play(s);'), 'qayıdanda video davam edir');
  const app = fs.readFileSync(path.join(__dirname, '..', 'assets', 'app.js'), 'utf8');
  assert.ok(app.includes('import("./lent.js?v=1").then(m => m.open(S, r.reel)).catch(() => $("#reels-boot")?.remove());'), 'modul alınmasa sayt dərhal görünür');
  assert.ok(src.includes('const siteShow = () => document.getElementById("reels-boot")?.remove();'));
});

test('Videolent: if the phone does not keep storage (private mode, in-app browser), the same page still remembers what was watched', async () => {
  const { list, markSeen, seenOrder, vkey } = await import(pathToFileURL(file).href);
  store(true);
  const reels = feed(), a = list({}, reels)[0];
  markSeen(a.u);
  assert.deepEqual(seenOrder(), [vkey(a.u)], 'yaddaş yazılmasa da səhifədə qalır');
  assert.notEqual(list({}, reels)[0].key, a.key, 'yenidən açılışda başqa video');
  store();
  markSeen(reels[5].u);   // yaddaş yenə işləyir: səhifədəki siyahı ora yazılır
  assert.deepEqual(JSON.parse(localStorage.getItem('8u-reels-seen')), [vkey(a.u), vkey(reels[5].u)]);
});

test('Videolent: the feed opens with the freshest news moment, keeps 60/40 and freshness beats a first-degree source by more than 6 hours (owner 2026-11-22, 2026-11-23)', async () => {
  const { list, mix } = await import(pathToFileURL(file).href);
  store();
  for (let k = 0; k < 20; k++) {
    const items = list({}, feed());
    assert.equal(items[0].m, 'xeber', 'lent xəbər anı ilə açılır');
    assert.equal(items[0].n, 'X0', 'ən təzə xəbər');
    assert.deepEqual(items.slice(0, 5).map(v => v.q), ['h', 'h', 'u', 'h', 'u'], 'h h u h u: 60% / 40%');
    for (const m of ['idman', 'tebiet', 'elm', 'kino', 'texnika']) {
      const t = items.filter(v => v.m === m && v.q === 'h').map(v => Date.parse(v.t));
      assert.deepEqual(t, [...t].sort((a, b) => b - a), `${m}: ən təzəsi əvvəl`);
    }
  }
  const t = h => new Date(NOW - h * HOUR).toISOString();
  const lane = [{ u: 'old-p', n: 'P', m: 'maraqli', p: true, t: t(30) }, { u: 'fresh', n: 'A', m: 'maraqli', t: t(1) },
    { u: 'p2', n: 'Q', m: 'tebiet', p: true, t: t(4) }, { u: 'n3', n: 'B', m: 'tebiet', t: t(3) }];
  const out = mix(lane).map(v => v.u);
  assert.ok(out.indexOf('fresh') < out.indexOf('old-p'), '30 saatlıq birinci dərəcəli video 1 saatlıq videonun önünə keçmir');
  assert.ok(out.indexOf('p2') < out.indexOf('n3'), 'yaşı yaxındırsa birinci dərəcəli mənbə önədir');
  const src = fs.readFileSync(file, 'utf8');
  assert.ok(src.includes('const AGE_PER_DECADE = 12 * 3600e3, P_BONUS = 0.5, OWN_V = 1e5, LEAD = "xeber", SPREAD = 3;'));
  assert.ok(!src.includes('(b.p ? 1 : 0) - (a.p ? 1 : 0)'), 'birinci dərəcəli mənbə yaşına baxmadan önə keçmir');
});

test('Videolent: the most watched come first, empty low-view clips sink, unknown counts go last (owner 2026-11-23: «20-80 yaş arası ən çox baxılan videolar olsun»)', async () => {
  const { list, mix } = await import(pathToFileURL(file).href);
  store();
  const t = h => new Date(Date.now() - h * HOUR).toISOString();
  const lane = [{ u: 'az', n: 'A', m: 'idman', t: t(1), v: 3000 }, { u: 'cox', n: 'B', m: 'idman', t: t(5), v: 900000 },
    { u: 'kohne-cox', n: 'C', m: 'idman', t: t(40), v: 2000000 }, { u: 'bilinmir', n: 'D', m: 'idman', t: t(0.5) }];
  assert.deepEqual(mix(lane).map(v => v.u), ['cox', 'az', 'kohne-cox', 'bilinmir'],
    '5 saatlıq 900 min baxış 1 saatlıq 3 mindən önə; 40 saatlıq 2 milyon təzələrin arxasında; sayı bilinməyən sonda');
  const reels = feed().map((r, i) => ({ ...r, v: r.m === 'xeber' ? 1000 * (i + 1) : 50000 }));
  reels.find(r => r.n === 'X2').v = 5e6;
  assert.equal(list({}, reels)[0].n, 'X2', 'xəbərlərin ən çox baxılanı lenti açır');
  assert.equal(list({ data: { articles: [] } }, [{ ...reels[0], v: 'çox' }])[0].v, -1, 'rəqəm olmayan say bilinmir sayılır');
});

test('Videolent: a topic head with few views does not jump the queue — most watched first, a topic never three times in a row (owner 2026-11-19, 2026-11-23)', async () => {
  const { mix } = await import(pathToFileURL(file).href);
  const t = new Date().toISOString(), list = [];
  for (let i = 0; i < 12; i++) list.push({ u: 'f' + i, n: 'club' + i, m: 'idman', t, v: 900000 - i * 1000 });
  for (let i = 0; i < 4; i++) list.push({ u: 'x' + i, n: 'news' + i, m: 'xeber', t, v: 500000 });
  list.push({ u: 'bos', n: 'brand', m: 'yemek', t, v: 6000 }, { u: 'elm', n: 'sci', m: 'elm', t, v: 300000 });
  const out = mix(list).map(v => v.u);
  assert.equal(out[0], 'x0', 'xəbər anı birinci');
  assert.ok(out.indexOf('bos') > out.indexOf('elm'), '6 min baxışlı mövzu başı 300 minlikdən sonra gəlir');
  const ms = mix(list).map(v => v.m);
  assert.ok(!ms.some((m, i) => i && m === 'idman' && ms[i - 1] === 'idman' && ms.slice(i + 1).some(x => x !== 'idman')),
    'başqa mövzu qaldıqca futbol ardıcıl gəlmir');
  assert.deepEqual(ms.slice(0, 4), ['xeber', 'idman', 'elm', 'yemek'], 'ilk 4 videoda 4 mövzu');
});

test('Videolent: rus və ingilis oxucu izahı öz dilində görür (sahib 2026-11-24: «videoları tam şəkildə rus və ingilis dillərində də verməliyik»)', async () => {
  const { cap, list } = await import(pathToFileURL(file).href);
  const r = { c: 'Futbolçu qol vurur', ru: 'Футболист забивает гол', en: 'A player scores' };
  assert.equal(cap(r, 'ru'), 'Футболист забивает гол');
  assert.equal(cap(r, 'en'), 'A player scores');
  assert.equal(cap(r, 'az'), 'Futbolçu qol vurur');
  assert.equal(cap(r, 'tr'), 'Futbolçu qol vurur', 'türk oxucu azərbaycanca izahı anlayır');
  assert.equal(cap(r, null), 'Futbolçu qol vurur', '«Hamısı»');
  assert.equal(cap({ c: 'Futbolçu qol vurur' }, 'ru'), '', 'rus izahı yoxdursa izahsız: azərbaycanca izah rus oxucuya kömək etmir');
  const reel = { id: '2123096874748187031', a: 'LFC', n: 'Liverpul', u: 'https://video.twimg.com/amplify_video/2123096874748187031/vid/avc1/480x852/a.mp4', w: 480, h: 852, t: '2026-11-24T10:00:00+00:00', ...r };
  assert.equal(list({ lang: 'en', data: { articles: [] } }, [reel], [])[0].c, 'A player scores', 'lent oxucunun dilini götürür');
});

test('Videolent: a feed that opens with zero height (in-app browser, background tab) loads no video and marks nothing watched; it starts when it gets a size (live check 2026-11-25)', async () => {
  const { onScreen, flat } = await import(pathToFileURL(file).href);
  // Sıfır hündürlüklü lentdə brauzer hər slaydı «tam görünür» deyir: 850 slayd = 850 yüklənən video.
  const zero = { isIntersecting: true, intersectionRatio: 1, boundingClientRect: { height: 0 } };
  assert.equal(flat(zero), true);
  assert.equal(onScreen(zero), false, 'ölçüsüz slayd oynamır, «baxılmış» olmur, yaddaşa yazılmır');
  assert.equal(onScreen({ isIntersecting: true, intersectionRatio: 1, boundingClientRect: { height: 812 } }), true, 'ekrandakı slayd oynayır');
  assert.equal(onScreen({ isIntersecting: true, intersectionRatio: 0.3, boundingClientRect: { height: 812 } }), false, 'yarıdan az görünən oynamır');
  assert.equal(onScreen({ isIntersecting: false, intersectionRatio: 0, boundingClientRect: { height: 812 } }), false);
  const src = fs.readFileSync(file, 'utf8');
  assert.ok(src.includes('if (flat(e)) { live.flat = true; continue; }'), 'ölçüsüz slayd nə oynayır, nə dayanır');
  assert.ok(src.includes('if (onScreen(e)) { live.at = pos(s); near(live.at); play(s);'), 'yalnız ekrandakı slayd oynayır');
  assert.ok(src.includes('win.addEventListener("resize"') && src.includes('live.io.unobserve(s); live.io.observe(s);'), 'ölçü gələndə müşahidə təzədən başlayır: paylaşılan video oynayır');
});

test('Videolent opens in a blink: slides are built in parts, the list is kept in memory, the first video loads at once (owner 2026-11-25: «videolent bir neçə saniyəyə açılır … ən vacib qırmızı cizgi-gözqırpımı sürətidir»)', async () => {
  const src = fs.readFileSync(file, 'utf8').replace(/\r\n/g, '\n');
  // 1. Slaydlar hissə-hissə: 980 slaydın birdən qurulması canlı saytda ~1,5 s çəkirdi, ilk video yalnız bundan sonra yüklənirdi.
  const size = src.match(/const FIRST = (\d+), CHUNK = (\d+);/);
  assert.ok(+size[1] >= 4 && +size[1] <= 10, 'ilk açılışda bir neçə slayd (sona 3 qalanda növbəti hissə gəlir, ona görə ən azı 4)');
  assert.ok(+size[2] >= 6 && +size[2] <= 30, 'növbəti hissə kiçikdir: sürüşdürmə ilişmir');
  assert.ok(src.includes('const queue = items.slice(FIRST);') && src.includes('${items.slice(0, FIRST).map(slide).join("")}'), 'yalnız ilk FIRST slayd qurulur');
  assert.ok(!src.includes('${items.map(slide).join("")}'), 'bütün slaydlar birdən qurulmur');
  assert.ok(src.includes('const have = new Set(items.map(K))'), 'qurulmamış videolar da «var» sayılır: təzələnmə onları ikinci dəfə əlavə etmir');
  // 2. İlk video müşahidəçinin ilk xəbərini gözləmir.
  assert.ok(src.includes('if (v0) { v0.preload = "auto"; v0.src = v0.dataset.src; }'), 'ilk video siyahı gələn kimi yüklənir');
  // 3. Geridə qalan video yaddaşdan çıxır.
  assert.ok(src.includes('drop(slides[live.at - 3]); drop(slides[live.at + 3]);'), 'uzaqdakı videolar yüklü qalmır');
  // 4. Siyahı yaddaşda: iki ardıcıl çağırış bir sorğudur; MEMO_MS-dən sonra təzə sorğu; lentin açılışı OPEN_MS-ə qədər köhnəsini götürür.
  const memoMs = +src.match(/const MEMO_MS = (\d+)e3/)[1] * 1e3, freshMs = +src.match(/const FRESH_MS = (\d+)e3/)[1] * 1e3;
  assert.ok(memoMs < freshMs, 'açıq lentin dəqiqəlik yoxlaması həmişə təzə fayl alır');
  const calls = [], realFetch = globalThis.fetch;
  globalThis.fetch = async url => { calls.push(String(url)); return { ok: true, json: async () => ({ items: [{ id: String(calls.length) }] }) }; };
  try {
    const { load } = await import(pathToFileURL(file).href + '?memo=1');
    const t = 1e12, a = await load(t), b = await load(t + 1000);
    assert.equal(calls.length, 1, 'ikinci çağırış şəbəkəyə getmir');
    assert.equal(a, b, 'eyni siyahı');
    assert.ok(calls[0].startsWith('https://raw.githubusercontent.com/8ulduz/8ulduz/live/m/'), 'canlı kanal');
    await load(t + memoMs + 1);
    assert.equal(calls.length, 2, 'MEMO_MS keçəndən sonra təzə sorğu');
    const old = await load(t + memoMs + 1 + 10 * 60e3, 15 * 60e3);
    assert.equal(calls.length, 2, 'lentin açılışı 15 dəqiqəyə qədər köhnə siyahını götürür (təzəsi arxada soruşulur)');
    assert.equal(old[0].id, '2');
  } finally { globalThis.fetch = realFetch; }
  assert.ok(src.includes('if (late) freshTick();'), 'köhnə siyahı ilə açılan lent təzə videoları dərhal soruşur');
  assert.ok(src.includes('if (k && late && !items.some(v => v.k === k)) { late = false; items = list(S, await load()); }'), 'paylaşılan video köhnə siyahıda yoxdursa təzəsi gözlənir');
  // 5. Düyməyə toxunan an modul və siyahı soruşulur (klikdən ~100 ms əvvəl).
  const app = fs.readFileSync(path.join(__dirname, '..', 'assets', 'app.js'), 'utf8');
  assert.ok(app.includes(`['[data-act="reels"]', () => import("./lent.js?v=1").then(m => m.load()).catch(() => {})]`), 'niyyət: modul + siyahı');
});

// Sahib 2026-11-26: «həm sayt həmdə sos şəbəkələrdə "çox baxılan" videolar verilməsini təmin et». Saytda: Videolentin «Çox baxılan»
// görünüşü — son 48 saatın videoları X-in baxış sayı ilə, ən çox baxılan birinci; adi lent (mövzu növbəsi, 60/40, xəbər anı) dəyişmir.
test('Videolent «Çox baxılan»: the last 48 hours by X view count, most watched first — ties keep their order, unknown counts go last, the window is respected (owner 2026-11-26)', async () => {
  const { top, views } = await import(pathToFileURL(file).href);
  const t = h => new Date(NOW - h * HOUR).toISOString();
  const v = (u, hours, n, more = {}) => ({ u, key: u, n: 'A', m: 'idman', t: t(hours), ...(n === undefined ? {} : { v: n }), ...more });
  const items = [v('az', 1, 3000), v('orta', 5, 900000), v('cox', 30, 5500000), v('kohne', 49, 9000000), v('sayi-yox', 2), v('beraber1', 10, 900000),
    v('bilinmir', 3, -1), v('oz', 4, 100000, { title: 'Öz video xəbərimiz' }), v('kenar', 47.9, 40000), v('beraber2', 20, 900000), v('sifir', 6, 0)];
  const before = items.map(x => x.u);
  const out = top(items, NOW, []).map(x => x.u);
  assert.deepEqual(out, ['cox', 'orta', 'beraber1', 'beraber2', 'kenar', 'az', 'sifir', 'sayi-yox', 'bilinmir', 'oz'],
    'ən çox baxılan birinci; bərabər saylar verilən sırada; sayı olmayan, bilinməyən və öz video xəbərimiz (təxmini say) sonda');
  assert.ok(!out.includes('kohne'), '49 saatlıq video 9 milyon baxışla da pəncərədən kənardır');
  assert.equal(out.length, items.length - 1, 'pəncərədəki heç bir video itmir, heç biri iki dəfə gəlmir');
  assert.deepEqual(items.map(x => x.u), before, 'verilən siyahı dəyişmir (adi lentin sırası qalır)');
  // Pəncərənin sərhədi: düz 48 saat içəridədir, bir dəqiqə köhnəsi yox.
  assert.deepEqual(top([v('ic', 48, 5), v('col', 48 + 1 / 60, 9)], NOW, []).map(x => x.u), ['ic']);
  // Baxış sayı: yalnız X-in mənfi olmayan tam ədədi; öz video xəbərimizin sayı sıralama təxminidir.
  assert.equal(views({ v: 2110507 }), 2110507);
  assert.equal(views({ v: 0 }), 0);
  for (const bad of [{}, { v: -1 }, { v: 'çox' }, { v: 1.5 }, { v: 100000, title: 'Öz xəbər' }]) assert.equal(views(bad), -1, JSON.stringify(bad));
  // Pəncərədə video yoxdursa (yazıcı 2 gündən çox dayanıb) görünüş boş qalmır: bütün lent sayla düzülür.
  assert.deepEqual(top([v('a', 60, 5), v('b', 100, 9), v('c', 70)], NOW, []).map(x => x.u), ['b', 'a', 'c']);
  assert.deepEqual(top([], NOW, []), []);
});

test('Videolent «Çox baxılan»: a watched video never comes first here either; with the real feed shape nothing but the count decides (owner 2026-11-23, 2026-11-26)', async () => {
  const { top, list, markSeen, vkey } = await import(pathToFileURL(file).href);
  store();
  const realNow = Date.now;
  Date.now = () => NOW;   // list() və top() eyni «indi» ilə
  try {
    // feed(): 20 video, ən köhnəsi 55 saatlıq usta işi — pəncərədən kənar.
    const reels = feed().map((r, i) => ({ ...r, v: 10000 + ((i * 7919) % 20) * 50000 }));
    const all = list({}, reels);
    const out = top(all);
    assert.equal(out.length, 19, '48 saatdan köhnə video «Çox baxılan»da yoxdur');
    assert.deepEqual(out.map(x => x.v), [...out.map(x => x.v)].sort((a, b) => b - a), 'yalnız say: mövzu növbəsi və 60/40 burada yoxdur');
    assert.equal(out[0].v, Math.max(...reels.filter(r => NOW - Date.parse(r.t) <= 48 * HOUR).map(r => r.v)));
    assert.equal(all[0].m, 'xeber', 'adi lent əvvəlki kimi xəbər anı ilə açılır');
    // Oxucu ilk iki videoya baxır: növbəti açılışda onlar sonda, sıra yenə sayla.
    markSeen(out[0].u); markSeen(out[1].u);
    const again = top(list({}, reels));
    assert.deepEqual(again.slice(-2).map(x => x.key), [vkey(out[0].u), vkey(out[1].u)], 'izlənmişlər sonda, öz aralarında yenə sayla');
    assert.equal(again[0].key, out[2].key, 'birinci video: baxılmamışların ən çox baxılanı');
    assert.equal(again.length, 19);
  } finally { Date.now = realNow; }
});

test('Videolent: the card shows the X view count, short and never overstated — «2,1 mln baxış», «94 min baxış» (owner 2026-11-26)', async () => {
  const { baxis } = await import(pathToFileURL(file).href);
  const cases = [[1, '1 baxış'], [850, '850 baxış'], [999, '999 baxış'], [1000, '1 min baxış'], [1099, '1 min baxış'], [3400, '3,4 min baxış'], [9999, '9,9 min baxış'],
    [10000, '10 min baxış'], [94000, '94 min baxış'], [94999, '94 min baxış'], [469118, '469 min baxış'], [999999, '999 min baxış'], [1000000, '1 mln baxış'],
    [1949999, '1,9 mln baxış'], [2110507, '2,1 mln baxış'], [5559872, '5,5 mln baxış'], [9999999, '9,9 mln baxış'], [12345678, '12 mln baxış'], [250000000, '250 mln baxış']];
  for (const [n, want] of cases) assert.equal(baxis(n), want, String(n));
  for (const n of [0, -1, undefined, null, NaN, Infinity, 1.5, '94000']) assert.equal(baxis(n), '', `say deyil: ${n}`);
  const src = fs.readFileSync(file, 'utf8');
  assert.ok(src.includes('const count = v => { const t = baxis(views(v)); return t ? `<i> · ${t}</i>` : ""; };') && src.includes('<div class="cap"><b>${esc(v.n)}${count(v)}</b>'),
    'say hesabın adının yanında, hər iki görünüşdə; sayı bilinməyən videoda və öz video xəbərimizdə yazı yoxdur');
});

test('Videolent «Çox baxılan»: one button in the lazy module — the default feed is untouched, the switch waits for no network, the first load gets nothing new (speed red line)', () => {
  const root = path.join(__dirname, '..');
  const src = fs.readFileSync(file, 'utf8').replace(/\r\n/g, '\n');
  assert.ok(src.includes('<button class="top" type="button" aria-pressed="false">Çox baxılan</button>'), 'düymə lentin yuxarısında, basılmamış: lent adi sıra ilə açılır');
  assert.ok(src.includes('let hot = false, flip = 0, noteT = 0;') && src.includes('build(f, first(items, k), () => history.back(), async keep => list(S, await load(undefined, keep)), late);'),
    'açılışda adi lent (mövzu növbəsi, 60/40, xəbər anı — sahibin 2026-11-19…23 qərarları)');
  assert.ok(src.includes('const n = ++flip, all = await more(OPEN_MS);') && src.includes('show(all, hot ? top(all) : all);'), 'keçid yaddaşdakı siyahı ilə: şəbəkə gözlənilmir');
  assert.ok(src.includes('if (!live || n !== flip) return;'), 'ardıcıl iki basış: lent bir dəfə, son seçimlə düzülür');
  assert.ok(src.includes('for (const s of slides) { live.io.unobserve(s); drop(s); s.remove(); }') && src.includes('if (!s.isConnected) continue;'),
    'köhnə slaydların videosu boşalır və silinir: arxada video oynamır');
  assert.ok(src.includes('put(queue.splice(0, FIRST), null);\n    feed.scrollTop = 0;\n    warm();'), 'yeni sıra birinci videodan, yenə hissə-hissə (FIRST), ilk video dərhal yüklənir');
  assert.ok(src.includes('if (!add.length || !live || hot) return;'), '«Çox baxılan»da təzə video sıranın arasına girmir');
  // Pəncərə yazıcının sayları yenilədiyi müddətdir: X sayları yalnız son 2 günün videoları üçün təzələnir.
  assert.ok(src.includes('const TOP_MS = 48 * 3600e3;'), '48 saat');
  const xy = fs.readFileSync(path.join(root, '.github/scripts/x_yazici.py'), 'utf8').replace(/\r\n/g, '\n');
  const at = xy.indexOf('def refresh(reels, now'), refresh = xy.slice(at, xy.indexOf('\ndef ', at + 1));
  assert.ok(at > 0 && refresh.includes('floor = now - datetime.timedelta(days=2)'), 'x_yazici.refresh: saylar son 2 gün üçün yenilənir — «Çox baxılan» pəncərəsi bundan uzun olmasın');
  // İlk açılış: düymə, sıra və say yalnız tənbəl moduldadır.
  for (const f of ['assets/app.js', 'assets/app.min.js', 'assets/app.css', 'index.html', 'sw.js']) {
    assert.ok(!fs.readFileSync(path.join(root, f), 'utf8').includes('Çox baxılan'), `${f}: ilk açılışa bayt düşmür`);
  }
  const pre = (fs.readFileSync(path.join(root, 'sw.js'), 'utf8').match(/cache\.addAll\(\[([^\]]*)\]/) || [])[1] || '';
  assert.ok(pre.includes('./assets/app.min.js') && !pre.includes('lent.js'), 'lent.js service worker-in ilkin keşində yoxdur');
  const budce = JSON.parse(fs.readFileSync(path.join(root, 'tests/budce.json'), 'utf8'));
  assert.ok(Buffer.byteLength(src) < budce.kod['tenbel.js'], 'tənbəl modul büdcəsi (tests/budce.json)');
});

test('Videolent: the poster comes from the image cache (img.8ulduz.az); a <video> poster gives no error event, so it is checked first and falls back to the same wsrv.nl query (owner 2026-11-27, docs/img-worker.md)', async () => {
  const { setPoster } = await import(pathToFileURL(file).href);
  const IMG = 'https://img.8ulduz.az/?url=https%3A%2F%2Fpbs.twimg.com%2Fa.jpg&w=720&we&output=webp&q=70';
  for (const ok of [true, false]) {
    const v = { dataset: { poster: IMG }, poster: '' }, im = {};
    setPoster(v, undefined, im);
    assert.equal(v.dataset.poster, '', 'bir dəfə yoxlanır');
    assert.equal(im.src, IMG);
    assert.equal(im.referrerPolicy, 'no-referrer');
    assert.equal(v.poster, '', 'yoxlanana qədər boş');
    (ok ? im.onload : im.onerror)();
    assert.equal(v.poster, ok ? IMG : IMG.replace('https://img.8ulduz.az/', 'https://wsrv.nl/'), ok ? 'Worker' : 'Worker alınmasa wsrv.nl');
  }
  const src = fs.readFileSync(file, 'utf8');
  assert.ok(src.includes('`${IMG}?url=${encodeURIComponent(u)}&w=${w}&we&output=webp&q=70`') && src.includes('if (!v.poster && v.dataset.poster) setPoster(v);'), 'yaxın slaydların posteri setPoster ilə');
});
