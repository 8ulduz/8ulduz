// Video lenti (assets/vlent.js; sahib, 2026-11-24: «Son xəbərlərdən sonra … daimi oynayan video xəbərlər … x dan yeni olan hadisə və
// xəbər videoları … öz videolarımızı da, saytların videolarını da»).
const { test } = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const { pathToFileURL } = require('node:url');
const root = path.join(__dirname, '..');
const read = f => fs.readFileSync(path.join(root, f), 'utf8');
// lent.js başlığı HTML-dən təmizləyir (textarea): sınaqda sadə əvəzi.
globalThis.document ??= { createElement: () => ({ value: "", set innerHTML(v) { this.value = String(v).replace(/<[^>]*>/g, ""); } }) };
const mod = () => import(pathToFileURL(path.join(root, 'assets/vlent.js')).href);

const now = Date.now(), ago = h => new Date(now - h * 3600e3).toISOString();
const x = (id, h, extra = {}) => ({ id, a: 'acc', n: 'Hesab', m: 'xeber', q: 'h', v: 1000, w: 720, h: 1280, t: ago(h), c: `X videosu ${id}`,
  u: `https://video.twimg.com/amplify_video/${id}/vid/avc1/720x1280/a.mp4?tag=1`, i: `https://pbs.twimg.com/amplify_video_thumb/${id}/img/a.jpg`, ...extra });
const yt = (videoId, channel, h, shorts = true) => ({ videoId, channel, title: `${channel} ${videoId}`, publishedAt: ago(h),
  url: shorts ? `https://www.youtube.com/shorts/${videoId}` : `https://www.youtube.com/watch?v=${videoId}`, imageUrl: `https://i.ytimg.com/vi/${videoId}/hqdefault.jpg` });

// Sahib, 2026-11-25: «videolar köhnədir yenisi gəlməlidir önə daima». Əvvəl üç mənbə növbə ilə gəlirdi (öz, X, TV): canlı zolağın
// 1, 4, 7…-ci kartları 23–30 saatlıq öz videolarımız idi (YouTube yükləməsi kanalın həddində dayanmışdı), qalanları 0,5–2 saatlıq.
test('lent: ən yeni video həmişə birinci, hansı mənbədən olursa olsun (öz videolarımız, X xəbər videoları, telekanallar)', async () => {
  const { pick, OWN } = await mod();
  const S = { video: { items: [yt('tvOld000001', 'ARB 24', 5, false), yt('own0000001', OWN, 3), yt('tvNew000001', 'İctimai TV', 1), yt('own0000002', OWN, 1)] }, data: { articles: [] } };
  const reels = [x('1000000001', 4), x('1000000002', 2), x('1000000003', 1, { m: 'idman' }), x('1000000004', 1, { q: 'u' })];
  const got = pick(S, reels).map(v => v.id || v.k);
  assert.deepEqual(got, ['own0000002', 'tvNew000001', '1000000002', 'own0000001', '1000000001', 'tvOld000001']);
  // Canlı hal: öz videolarımız bir gün köhnədir, X və TV videoları təzədir — köhnə video təzələrin qabağına keçmir.
  const live = pick({ video: { items: [yt('ownDay0001', OWN, 24), yt('ownDay0002', OWN, 25), yt('tvNow00001', 'Real TV', 0.5), yt('tvNow00002', 'Report.az', 0.6)] }, data: { articles: [] } },
    [x('2000000001', 1.1), x('2000000002', 1.2)]).map(v => v.id || v.k);
  assert.deepEqual(live, ['tvNow00001', 'tvNow00002', '2000000001', '2000000002', 'ownDay0001', 'ownDay0002']);
  const times = pick(S, reels).map(v => Date.parse(v.t));
  assert.ok(times.every((t, i) => !i || times[i - 1] >= t), 'vaxt sırası pozulmur');
  const first = pick(S, reels)[0];
  assert.equal(first.src, '8ulduz.az', 'öz videomuzun nişanı sayt adıdır');
  assert.ok(first.tall, 'öz videolarımız şaquli Shorts-dur');
  assert.equal(pick(S, reels).find(v => v.id === 'tvOld000001').tall, false, 'üfüqi TV videosu kartın ortasında, kəsilmir');
});

test('lent: X-dən yalnız hadisə və xəbər videoları; X videolu öz xəbərimiz də düşür; ən çoxu 24 kart', async () => {
  const { pick } = await mod();
  const own = { id: 'abcdef0123456789', title: 'Öz xəbərimiz', publishedAt: ago(0.5), sourceUrl: 'https://apa.az/x', imageUrl: 'https://apa.az/a.jpg',
    xv: { u: 'https://video.twimg.com/ext_tw_video/2000000001/pu/vid/720x1280/b.mp4', w: 720, h: 1280 } };
  const reels = Array.from({ length: 40 }, (_, i) => x(String(3000000000 + i), 1 + i / 10));
  const got = pick({ video: { items: [] }, data: { articles: [own] } }, [...reels, x('9', 1, { m: 'kino' })]);
  assert.equal(got.length, 24);
  assert.equal(got[0].title, 'Öz xəbərimiz');
  assert.ok(got.every(v => v.kind === 'x' && !/kino/.test(v.title)));
});

test('lent (sahib 2026-11-24, ikinci baxış): hər video kartı tam doldurur, şəkil də; növbəti video qabaqcadan hazırlanır', async () => {
  const { poster } = await mod();
  assert.deepEqual(poster({ kind: 'yt', id: 'abcdefghijk', tall: true }),
    ['https://img.8ulduz.az/?url=' + encodeURIComponent('https://i.ytimg.com/vi/abcdefghijk/oar2.jpg') + '&w=360&we&output=webp&q=70', 'https://i.ytimg.com/vi/abcdefghijk/hqdefault.jpg'],
    'Shorts: şaquli şəkil (hqdefault yanlarda qara zolaqlıdır)');
  assert.match(poster({ kind: 'yt', id: 'abcdefghijk', tall: false })[0], /hq720\.jpg/, 'üfüqi: zolaqsız şəkil');
  assert.equal(poster({ kind: 'yt', id: 'abcdefghijk', tall: false })[1], 'https://i.ytimg.com/vi/abcdefghijk/mqdefault.jpg');
  const v = read('assets/vlent.js');
  assert.ok(v.includes('.vl-v>iframe.w{left:50%;width:316.05%;transform:translateX(-50%)}'), '16:9 YouTube kartın hündürlüyündə, ortadan kəsilir');
  assert.ok(v.includes('video{width:100%;height:100%;object-fit:cover}') && !v.includes('object-fit:${'), 'X videosu həmişə kartı doldurur');
  assert.ok(v.includes('preload="auto"') && v.includes('if (auto() && nx !== n) make(nx);'), 'növbəti kartın oynadıcısı qabaqcadan');
  assert.ok(v.includes('trim([n, nx]);'), 'ən çoxu iki oynadıcı');
  assert.ok(read('assets/app.css').includes('nav.main>a.ph,nav.main .nav-inst{border:1px solid var(--border)}'), 'telefon cərgəsi: AZ düyməsinin kənarı kimi (sahib: ağ xətt pis göründü)');
});

test('lent: tənbəl modul, «Son xəbərlər»dən dərhal sonra, sabit sətirli qutu (dəqiqəlik çəkiliş oynayan videonu kəsmir)', () => {
  const app = read('assets/app.js');
  assert.ok(app.includes('latestBlock(remaining) + (uiLang(S.lang) ? "" : VLENT)'), 'lent «Son xəbərlər»dən sonradır');
  assert.ok(/const VLENT = `<section id="vlent" style="min-height:[^"]+">[^$]*<\/section>`;/.test(app), 'qutunun sətri sabitdir (dəyişən yoxdur) və hündürlüyü qabaqcadan verilib');
  assert.ok(app.includes('import("./vlent.js").then(m => m.mount(el, S, motionOff))'), 'modul yalnız bölmə yaxınlaşanda yüklənir');
  assert.ok(app.includes('rootMargin: "900px 0px"'));
  const sw = read('sw.js');
  assert.ok(!sw.includes('vlent.js'), 'service worker ilkin keşinə düşmür');
  const v = read('assets/vlent.js');
  assert.ok(v.includes('<meta name="referrer" content="no-referrer">'), 'X videosu referrer göndərməyən çərçivədə (X 403 verir)');
  assert.ok(v.includes('https://www.youtube-nocookie.com/embed/') && v.includes('?autoplay=0&mute=1&'), 'YouTube çərəzsiz, səssiz başlayır (oynadıcı qabaqcadan açılır, «oynat» əmri ilə başlayır)');
  assert.ok(v.includes('saveData') && v.includes('still()'), 'qənaət və «hərəkəti azalt» rejimində özü oynamır');
});

test('lent: öz YouTube kanalımız video siyahısına yığılır və qayda siyahısındadır', () => {
  const up = read('updater.py');
  assert.ok(up.includes('("8ULDUZ", "https://www.youtube.com/feeds/videos.xml?channel_id=UCU8rSsJEFf78Y0rCya2fmhg")'));
  assert.ok(read('assets/content-policy.js').includes('"Real TV", "8ULDUZ"]'));
  assert.ok(up.includes('got = yt_items(url, VIDEO_PER)') && /VIDEO_PER = 10/.test(up), 'kanal başına 10 video: xəbərə aid TV videosu tapılsın');
});

// Sahib, 2026-11-24: «son xəbərlərin altındakı videoxəbərlərə basanda tam ekran olsun» (öz, TV və X videoları).
test('lent (sahib 2026-11-24, tam ekran): videoya basanda kart səslə tam ekrana açılır, video olduğu yerdən davam edir', () => {
  const v = read('assets/vlent.js');
  const open = /function openFs\(n\) \{[\s\S]*?\n  \}\n/.exec(v)?.[0] || '';
  const close = /function closeFs\(\) \{[\s\S]*?\n  \}\n/.exec(v)?.[0] || '';
  assert.ok(open && close, 'openFs/closeFs var');
  assert.ok(v.includes('openFs(Number(b.parentElement.dataset.n));'), 'videoya basmaq tam ekranı açır (əvvəl yalnız səsi açıb-bağlayırdı)');
  assert.ok(v.includes('aria-label="${LABEL}"') && v.includes('const LABEL = "Videonu tam ekranda aç"'));
  assert.ok(open.includes('c.classList.add("fs")') && !/iframe|make\(|\.append\(/.test(open),
    'oynadıcı yerindən tərpənmir (iframe köçürülsə yenidən yüklənər, video başdan başlayardı)');
  assert.ok(open.includes('if (n !== cur) { sound = true; play(n); } else setSound(true);'), 'səslə; oynayan kart olduğu yerdən davam edir');
  assert.ok(v.includes('.vl-c.fs{position:fixed;inset:0;z-index:2147483000;'), 'bütün pəncərəni tutur, saytın başlığı və menyusu üstə çıxmır');
  assert.ok(v.includes('.vl-c.fs .vl-v>iframe.w{left:0;width:100%;transform:none}'), 'üfüqi YouTube videosu tam ekranda kəsilmir, bütöv görünür');
  const card = Number(/\.vl-c\{flex:none;width:min\(58vw,(\d+)px\)/.exec(v)?.[1]);
  // Sahib, 2026-11-24 (üçüncü baxış): «üstündə yazılar olsa da video tam kart boyu olmalıdır».
  assert.ok(v.includes('video{width:100%;height:100%;object-fit:cover}@media(orientation:landscape){video{object-fit:contain}}') && card < 300,
    'X videosu kartda və telefonun tam ekranında ekranı doldurur, yalnız üfüqi ekranda (kompüter) bütöv görünür');
  assert.ok(v.includes('@media(orientation:landscape){.vl-c.fs .vl-v>img{object-fit:contain}}') && v.includes('.vl-c.fs .vl-v:has(>iframe.w)>img{object-fit:contain}'),
    'şəkil də videonun ölçüsündədir; üfüqi YouTube videosunun şəkli oynadıcı kimi bütöv');
  assert.ok(v.includes('if (fs >= 0) { fsEnd = true;') && open.includes('clearTimeout(timer);'), 'tam ekranda növbəti karta özü keçmir');
});

test('lent (tam ekran): hər cihazda işləyir, geri/✕/Escape bağlayır, lent yerində qalır, CLS yoxdur', () => {
  const v = read('assets/vlent.js');
  const open = /function openFs\(n\) \{[\s\S]*?\n  \}\n/.exec(v)?.[0] || '';
  const close = /function closeFs\(\) \{[\s\S]*?\n  \}\n/.exec(v)?.[0] || '';
  assert.ok(open.includes('history.pushState({ vlfs: 1 }, "");') && v.includes('addEventListener("popstate", () => { if (fs >= 0) closeFs(); }, on);'), 'telefonun geri düyməsi tam ekranı bağlayır, səhifədən çıxmır');
  assert.ok(v.includes('if (e.key === "Escape") { e.preventDefault(); back(); }') && v.includes('if (fx?.classList.contains("x")) back();'));
  assert.ok(open.includes('if (document.fullscreenEnabled && c.requestFullscreen)'), 'əsl tam ekran yalnız brauzer verirsə (iPhone Safari div üçün vermir: tam pəncərə qalır)');
  assert.ok(v.includes('if (native && fs >= 0 && !document.fullscreenElement) back();'), 'brauzerin tam ekranından çıxmaq (Esc, Android geri) bizimkini də bağlayır');
  assert.ok(open.includes('spot.style.height = c.offsetHeight + "px";') && open.includes('c.before(spot);'), 'kartın lentdəki yerini eyni ölçülü boş yer tutur: arxadakı kartlar tərpənmir');
  assert.ok(close.includes('c.style.visibility = "hidden";'), 'geri düyməsi «giriş» sayılmır: yerinə qayıdan kart iki kadr gizli (CLS-ə yazılmır)');
  assert.ok(!v.includes('style.overflow'), 'səhifənin overflow-u dəyişmir (kompüterdə zolaq gedib səhifə tərpənərdi)');
  assert.ok(open.includes('c.addEventListener("touchmove", noScroll, { passive: false });') && close.includes('c.removeEventListener("touchmove", noScroll);')
    && !/row\.addEventListener\("(touchmove|wheel)"/.test(v), 'sürüşmə yalnız tam ekran açıq ikən dayandırılır: lentin öz sürüşməsi ləngimir');
  assert.ok(close.includes('setSound(false);'), 'bağlananda video lentdə səssiz davam edir');
});

test('Video lenti: the next YouTube video is primed — it plays at once when chosen (owner 2026-11-25: «bəzi videolar (əsasən azərbaycan) 1-2 saniyəyə açılır … gözqırpımı»)', () => {
  const v = read('assets/vlent.js');
  // Ölçü (canlı sayt): basışdan ilk kadra hazır oynadıcıda 1,7 s, oynadıcı yoxdursa 2,4 s — axın yalnız «oynat»dan sonra gəlirdi.
  assert.ok(v.includes('const ready = () => { f._ready = true; if (f._want) start(n); else prime(n); };'), 'hazır, amma seçilməmiş oynadıcı hazırlanır');
  assert.ok(v.includes('if (f && n !== cur && items[n].kind === "yt" && !f._prime) { f._prime = 1; ytCmd(f, "mute"); ytCmd(f, "playVideo"); }'),
    'hazırlıq səssizdir, yalnız YouTube və yalnız oynamayan kart üçün, bir dəfə');
  assert.ok(v.includes('if (st === 1 && f._prime === 1) { f._prime = 2; ytCmd(f, "pauseVideo"); }'), 'ilk kadrda dayanır: seçilməmiş video oynamır');
  assert.ok(!v.includes('"seekTo"'), 'əvvələ qaytarılmır: seekTo axını yenidən yükləyir (ölçü: +0,5 s)');
  // Sahib 2026-11-25 (telefon ekranının videosu): kartda YouTube-un qara yükləmə ekranı, fırlanan dairə və «Shorts» yazısı görünməməlidir.
  assert.ok(!/setTimeout\(\(\) => f\.classList\.add\("go"\)/.test(v), 'YouTube oynadıcısı vaxtla açılmır (video başlamadan yükləmə ekranı görünürdü)');
  assert.ok(v.includes('else if (st === 1) f.classList.add("go");') && v.includes('.vl-c.on .vl-v>iframe.go{opacity:1}') && v.includes('.vl-v>iframe{pointer-events:none;background:transparent;opacity:0}'),
    'oynadıcı yalnız «oynayır» xəbəri gələndə görünür, o vaxta qədər kartın şəkli qalır');
  assert.ok(v.includes('if (auto() && nx !== n) make(nx);'), 'qənaət rejimində oynadıcı qabaqcadan qurulmur, deməli hazırlanmır');
  // Kompüter: siçan kartın üstünə gələndə onun oynadıcısı qurulur (4–5 kart görünür, basılan kart növbəti olmaya bilər).
  const over = /row\.addEventListener\("pointerover", e => \{[\s\S]*?\}, \{ passive: true \}\);/.exec(v)?.[0] || '';
  assert.ok(over.includes('if (e.pointerType !== "mouse" || fs >= 0 || !auto()) return;'), 'yalnız siçan: barmaqla sürüşdürmə oynadıcı qurmur');
  assert.ok(over.includes('players.size < 4'), 'eyni anda ən çoxu 4 oynadıcı');
});

// Sahib, 2026-11-25: «video xəbər kompda kursor üzərinə aparılanda oynamalı idi. belə deyil!!!», «yalnız kursor üstünə aparılanda
// başlasın oynamağa avtomatik yox, kursoru çəkəndə dayansın». Əvvəl kursor yalnız oynadıcını qurur, video isə özü növbə ilə oynayırdı.
test('Video lenti on a computer: a card plays only while the cursor is on it and stops when the cursor leaves; phones keep autoplay', () => {
  const v = read('assets/vlent.js');
  const m = /export async function mount\(sec, S, still = \(\) => false, given = null\) \{[\s\S]*?\n\}\n?/.exec(v)?.[0] || '';
  assert.ok(m.includes('const hover = matchMedia("(hover:hover) and (pointer:fine)").matches;'), 'kompüter: siçan əsas göstəricidir; telefon və planşet (hover:none) əvvəlki kimi');
  const over = /row\.addEventListener\("pointerover", e => \{[\s\S]*?\}, \{ passive: true \}\);/.exec(m)?.[0] || '';
  assert.ok(over.includes('if (n >= 0 && hover) play(n);'), 'kursor kartın üstünə gələn kimi oynayır (gözləmə yoxdur)');
  const out = /row\.addEventListener\("pointerout", e => \{[\s\S]*?\}, \{ passive: true \}\);/.exec(m)?.[0] || '';
  assert.ok(out.includes('cards[cur].contains(e.relatedTarget)') && out.includes('rest();'), 'kursor kartdan çıxanda dayanır; kartın içində (şəkil, başlıq) gəzəndə yox');
  const rest = /function rest\(\) \{[\s\S]*?\n  \}\n/.exec(m)?.[0] || '';
  assert.ok(rest.includes('halt(cur);') && rest.includes('cards[cur].classList.remove("on");') && !rest.includes('trim('), 'dayanır, kartda şəkil görünür, oynadıcı silinmir: qayıdanda olduğu yerdən dərhal');
  const pv = /const pickVisible = \(\) => \{[\s\S]*?\n  \};\n/.exec(m)?.[0] || '';
  assert.ok(pv.startsWith('const pickVisible = () => {\n    if (hover) {') && !/if \(hover\) \{[^}]*play\(/.test(pv), 'kompüterdə görünən kart özü oynamır');
  const play = /function play\(n\) \{[\s\S]*?\n  \}\n/.exec(m)?.[0] || '';
  assert.ok(play.indexOf('if (hover) {') >= 0 && play.indexOf('if (hover) {') < play.indexOf('make(nx)') && play.indexOf('if (hover) {') < play.indexOf('setTimeout(next, PLAY_MAX)'),
    'kompüterdə növbəti kart qabaqcadan qurulmur və vaxtla növbəti karta keçmir');
  const next = /function next\(\) \{[\s\S]*?\n  \}\n/.exec(m)?.[0] || '';
  assert.ok(next.includes('if (hover) { again(cur); return; }') && next.indexOf('if (hover)') < next.indexOf('row.scrollTo'), 'bitən video yenidən başlayır, zolaq kursorun altında sürüşmür');
  assert.ok(m.includes('else if (hover && !c.matches(":hover")) rest();'), 'tam ekran bağlananda kursor kartda deyilsə dayanır');
  assert.ok(m.includes('if (hover && row.matches(":hover") && !force) return false;'), 'kursor zolaqdadırsa yeni siyahı kartları altında dəyişmir');
  // Telefon: əvvəlki kimi görünən kart özü oynayır və növbəti qabaqcadan hazırlanır.
  assert.ok(pv.includes('const best = ') && play.includes('if (auto() && nx !== n) make(nx);') && play.includes('timer = setTimeout(next, PLAY_MAX);'));
});

// Sahib, 2026-11-25: «ən vacib qırmızı cizgi-gözqırpımı sürətidir», «video xəbərlərdə bəzi videolar (əsasən azərbaycan) 1-2 saniyəyə açılır».
// Ölçü (kompüter brauzeri): YouTube kartı basışdan ilk kadra 2,4 s (oynadıcı yoxdursa), 1,7 s (hazırdırsa); X videosu (adi <video>) 0,2–0,5 s.
test('lent (sahib 2026-11-25): öz videomuzun veb nüsxəsi X videosu kimi adi <video> ilə oynayır; telekanallar YouTube-da qalır', async () => {
  const { pick, poster, OWN, ownMp4 } = await mod();
  const web = id => `https://video.8ulduz.az/${id}.mp4`;
  const S = { video: { items: [
    { ...yt('ownWeb0001', OWN, 1), mp4: web('ownWeb0001') },
    yt('ownTube001', OWN, 2),
    { ...yt('tvWeb00001', 'ARB 24', 1), mp4: web('tvWeb00001') },
    { ...yt('ownBad0001', OWN, 3), mp4: 'https://evil.example/ownBad0001.mp4' },
    { ...yt('ownOther01', OWN, 4), mp4: web('ownWeb0001') },
  ] }, data: { articles: [] } };
  const got = Object.fromEntries(pick(S, []).map(v => [v.id, v]));
  assert.equal(got.ownWeb0001.kind, 'mp4');
  assert.equal(got.ownWeb0001.u, web('ownWeb0001'));
  assert.ok(got.ownWeb0001.own && got.ownWeb0001.tall && got.ownWeb0001.src === '8ulduz.az');
  assert.equal(got.ownTube001.kind, 'yt', 'veb nüsxəsi yoxdursa YouTube-dan oynayır');
  assert.equal(got.tvWeb00001.kind, 'yt', 'telekanalın videosu YouTube oynadıcısında qalır');
  assert.equal(got.ownBad0001.kind, 'yt', 'yalnız öz domenimiz (video.8ulduz.az)');
  assert.equal(got.ownOther01.kind, 'yt', 'fayl adı videonun öz nömrəsidir: başqa videonun faylı oynamır');
  assert.ok(ownMp4({ videoId: 'abcdefghijk', mp4: web('abcdefghijk') }) && !ownMp4({ videoId: 'abc/../x', mp4: web('abc/../x') }) && !ownMp4({ videoId: 'abcdefghijk', mp4: web('abcdefghijk') + '?x=1' }));
  assert.deepEqual(poster(got.ownWeb0001), poster({ kind: 'yt', id: 'ownWeb0001', tall: true }), 'şəkli YouTube-dakı şaquli şəkildir');
  const v = read('assets/vlent.js');
  // Növ «mp4» X videosunun yolundan keçir: srcdoc-da adi <video preload="auto">, «yt» olmayan start/halt/səs.
  assert.ok(v.includes('if (v.kind === "yt") {') && v.includes('<video playsinline muted preload="auto" src="${esc(v.u)}"></video>'), 'oynadıcı X videosununku kimidir');
  assert.ok(v.includes('if (items[n].kind === "yt") { ytCmd(f, sound ? "unMute" : "mute"); ytCmd(f, "playVideo");') && v.includes('items[n].kind === "yt" && !f._prime'), 'YouTube əmrləri və hazırlıq yalnız YouTube kartına');
  assert.ok(v.includes('href="${v.kind === "x" ? "#/videolent" : `#/videolent?v=${encodeURIComponent(v.id)}`}"'), 'başlığın keçidi video səhifəsidir (YouTube kartı kimi)');
  assert.ok(v.includes('if (v.kind === "x") { e.preventDefault(); stop(); import("./lent.js?v=1")'), 'Videolent yalnız X videosu üçün');
  // Yalnız növbəti kart qabaqcadan yüklənir və qənaət rejimində heç biri (auto()).
  assert.ok(v.includes('if (auto() && nx !== n) make(nx);') && v.includes('trim([n, nx]);'));
});

test('Video lenti refreshes while the page stays open, without cutting the video being watched (owner 2026-11-25: «saytdakı video xəbərlər niyə yenilənmir?»)', () => {
  const v = read('assets/vlent.js');
  const m = /export async function mount\(sec, S, still = \(\) => false, given = null\) \{[\s\S]*?\n\}\n?/.exec(v)?.[0] || '';
  assert.ok(m, 'mount yenidən qurmaq üçün hazır siyahı qəbul edir');
  // Əvvəl kartlar səhifə açılanda bir dəfə qurulurdu: açıq qalan səhifədə zolaq saatlarla köhnə qalırdı.
  const fresh = +v.match(/const FRESH = (\d+) \* 60e3, EARLY = (\d+)e3;/)[1];
  assert.ok(fresh >= 2 && fresh <= 10, 'siyahı bir neçə dəqiqədən bir yoxlanır (426 KB-lıq fayl: tez-tez deyil)');
  assert.ok(m.includes('const tick = setInterval(() => { due = true; fresh(); swap(); }, FRESH);'), 'dövri yoxlama');
  assert.ok(m.includes('if (!due || checking || document.hidden || !sec.isConnected || !visible() || ac.signal.aborted) return;'),
    'yalnız vərəq və zolaq görünəndə yoxlanır: gizli vərəq şəbəkəni yormur');
  assert.ok(m.includes('if (list.length && key(list) !== key(items)) { pending = list; swap(); }'), 'siyahı dəyişməyibsə zolağa toxunulmur');
  // Oynayan və görünən video kəsilmir.
  assert.ok(m.includes('const quiet = document.hidden || !sec.isConnected || cur < 0 || !visible() || early;') && m.includes('if (!quiet && !force) return false;'),
    'yenidən qurma yalnız sakit anda: vərəq gizli, zolaq görünmür, heç nə oynamır və ya zolaq təzə göstərilib');
  assert.ok(m.includes('if (!pending || fs >= 0 || ac.signal.aborted) return false;'), 'tam ekran açıqdırsa heç vaxt');
  assert.ok(m.includes('if (n < cur && swap(true)) return;'), 'lent sonuncu özü oynayan kartdan əvvələ qayıdanda yeni siyahıdan başlayır (YouTube kartları atlanır)');
  // Video siyahısı gec gəlibsə TV videoları sonra düşür.
  assert.ok(m.includes('if (S?.video || ++waits > 30)'), 'S.video gələn kimi yoxlanır');
  // Yenidən qurulanda köhnə dinləyicilər qalmır.
  assert.ok(m.includes('stop(); io.disconnect(); clearTimeout(hold); clearInterval(tick); clearInterval(wait); ac.abort();') && m.includes('mount(sec, S, still, list);'), 'köhnə zolaq tam söndürülür');
  // Pəncərəyə və sənədə bağlı hər dinləyicinin tam çağırışı (mötərizə balansı ilə) «, on)» ilə bitir. row./c./f. — elementin özünün.
  const calls = ev => {
    const out = [], head = 'addEventListener(' + ev;
    for (let i = m.indexOf(head); i >= 0; i = m.indexOf(head, i + 1)) {
      const before = m.slice(Math.max(0, i - 9), i);
      if (/[\w.]$/.test(before) && !before.endsWith('document.')) continue;
      let depth = 0, j = i + 'addEventListener'.length, quote = '';
      for (; j < m.length; j++) {
        const ch = m[j];
        if (quote) { if (ch === '\\') j++; else if (ch === quote) quote = ''; continue; }
        if (ch === '"' || ch === "'" || ch === '`') quote = ch;
        else if (ch === '(') depth++;
        else if (ch === ')' && --depth === 0) break;
      }
      out.push(m.slice(i, j + 1));
    }
    return out;
  };
  for (const ev of ['"message"', '"keydown"', '"fullscreenchange"', '"visibilitychange"', '"popstate"']) {
    const all = calls(ev);
    assert.ok(all.length && all.every(x => x.endsWith(', on)')), `${ev} dinləyicisi yenidən qurulanda silinir`);
  }
  assert.ok(m.includes('const old = sec.querySelector(".vl-row");') && m.includes('if (old) old.replaceWith(row); else sec.append(row);'), 'yeni sətir köhnənin yerinə: səhifə atlamır');
});

// Sahib, 2026-11-26 («…videolarda açıldıqdan sonra dayan işarəsinin bir neçə saniyə görünməsi…», seçim: «A: avtomatik oynamasın»).
// YouTube oynadıcısı hər başlayanda ~3,5 s öz ⏸ işarəsini, kanal adını və «Shorts» yazısını göstərir; parametrlə söndürülmür, üstünü
// örtmək YouTube-un qaydasına ziddir. Ona görə telefonda YouTube kartı (telekanallar) özü oynamır, basanda tam ekranda açılır.
test('Video lenti (owner 2026-11-26, A): YouTube cards never start by themselves on a phone — the strip plays own and X videos and skips them; a tap still opens them full screen', () => {
  const v = read('assets/vlent.js');
  const m = /export async function mount\(sec, S, still = \(\) => false, given = null\) \{[\s\S]*?\n\}\n?/.exec(v)?.[0] || '';
  const okSrc = /\n  const ok = n => items\[n\]\.kind !== "yt";\n/.exec(m)?.[0], nextSrc = /\n  const nextOf = n => \{[^\n]*\n/.exec(m)?.[0];
  assert.ok(okSrc && nextSrc, 'qayda bir yerdədir');
  const run = kinds => new Function('items', 'cards', `${okSrc}${nextSrc}; return { ok, nextOf };`)(kinds.map(kind => ({ kind })), kinds);
  const a = run(['yt', 'x', 'yt', 'yt', 'mp4', 'yt']);
  assert.deepEqual([0, 1, 2, 3, 4, 5].map(a.nextOf), [1, 4, 4, 4, 1, 1], 'növbəti özü oynayan kart: YouTube kartları atlanır, sonuncudan əvvələ qayıdır');
  assert.equal(run(['yt', 'yt', 'yt']).nextOf(1), 1, 'özü oynayan kart yoxdursa yerində qalır');
  assert.equal(run(['x']).nextOf(0), 0);
  const pv = /const pickVisible = \(\) => \{[\s\S]*?\n  \};\n/.exec(m)?.[0] || '';
  assert.ok(pv.includes('.filter(([n, r]) => r >= 0.6 && ok(n))'), 'görünən YouTube kartı seçilmir');
  const next = /function next\(\) \{[\s\S]*?\n  \}\n/.exec(m)?.[0] || '';
  assert.ok(next.includes('if (n === cur) { if (ok(cur)) again(cur); else stop(); return; }'), 'başqa özü oynayan kart yoxdursa: öz video yenidən, basılmış YouTube dayanır');
  assert.ok(m.includes('const first = [0, 1].find(k => k < items.length && ok(k));') && m.includes('if (!hover && auto() && !given && first != null) make(first);'), 'zolaq yaxınlaşanda YouTube oynadıcısı qabaqcadan qurulmur');
  // Basış dəyişmir: kart səslə tam ekranda açılır (YouTube kartı da), kompüterdə kursorla oynatma qalır.
  assert.ok(m.includes('openFs(Number(b.parentElement.dataset.n));') && m.includes('if (n !== cur) { sound = true; play(n); } else setSound(true);'), 'basanda oynayır');
  assert.ok(m.includes('if (n >= 0 && hover) play(n);'), 'kompüter: kursor (sahib, 2026-11-25)');
  // ▶ işarəsi oynamayan kartda görünür.
  assert.ok(v.includes('.vl-c.on .vl-p{display:none}'));
});
