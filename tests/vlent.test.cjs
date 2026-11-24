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

test('lent: öz videolarımız, X xəbər videoları və telekanallar növbə ilə, hər biri ən yenisi əvvəl', async () => {
  const { pick, OWN } = await mod();
  const S = { video: { items: [yt('tvOld000001', 'ARB 24', 5, false), yt('own0000001', OWN, 3), yt('tvNew000001', 'İctimai TV', 1), yt('own0000002', OWN, 1)] }, data: { articles: [] } };
  const reels = [x('1000000001', 4), x('1000000002', 2), x('1000000003', 1, { m: 'idman' }), x('1000000004', 1, { q: 'u' })];
  const got = pick(S, reels).map(v => v.id || v.k);
  assert.deepEqual(got, ['own0000002', '1000000002', 'tvNew000001', 'own0000001', '1000000001', 'tvOld000001']);
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
    ['https://wsrv.nl/?url=' + encodeURIComponent('https://i.ytimg.com/vi/abcdefghijk/oar2.jpg') + '&w=360&we&output=webp&q=70', 'https://i.ytimg.com/vi/abcdefghijk/hqdefault.jpg'],
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
  assert.ok(v.includes('@media(min-width:300px){video{object-fit:contain}}') && card < 300,
    'X videosu kartda kartı doldurur, tam ekranda bütöv görünür (həddi kartın enindən böyükdür)');
  assert.ok(v.includes('if (fs >= 0) { fsEnd = true;') && open.includes('clearTimeout(timer);'), 'tam ekranda növbəti karta özü keçmir');
});

test('lent (tam ekran): hər cihazda işləyir, geri/✕/Escape bağlayır, lent yerində qalır, CLS yoxdur', () => {
  const v = read('assets/vlent.js');
  const open = /function openFs\(n\) \{[\s\S]*?\n  \}\n/.exec(v)?.[0] || '';
  const close = /function closeFs\(\) \{[\s\S]*?\n  \}\n/.exec(v)?.[0] || '';
  assert.ok(open.includes('history.pushState({ vlfs: 1 }, "");') && v.includes('addEventListener("popstate", () => { if (fs >= 0) closeFs(); });'), 'telefonun geri düyməsi tam ekranı bağlayır, səhifədən çıxmır');
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
