// «Gözqırpımı» hər hissədə (sahib, 2026-11-24: «sürət qırmızı cizgimizdir. "gözqırpımında" ölçüsü saytın istisnasız hər bir hissəsində
// olsun! bunu ən peşəkar və innovativ üsullarla təmin et»). Toxunuşları ucuzladan üsullar və onları ölçən alət yerində qalsın.
const { test } = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const root = path.join(__dirname, '..');
const read = f => fs.readFileSync(path.join(root, f), 'utf8');
const B = JSON.parse(read('tests/budce.json'));

test('gözqırpımı: ekrandan kənar bloklar və kartlar çəkilmir, açıq pəncərəli kart kəsilmir', () => {
  const css = read('assets/app.css');
  assert.ok(css.includes('#view>section,#view>.lazy-sec,#view>details,#footer,.grid>.card,.latest-grid>.card{content-visibility:auto;contain-intrinsic-block-size:auto 360px}'),
    'content-visibility: hər toxunuşda üslub və yerləşdirmə yalnız görünən hissəyə (tema, geri, «daha çox», kart → xəbər)');
  assert.ok(css.includes('#view>:has(details[open]),.card:has(details[open]){content-visibility:visible}'), '«N mənbə» pəncərəsi kartın sərhədində kəsilməsin');
  assert.ok(!/\.ytrow>\.card\{content-visibility/.test(css), 'üfüqi zolaqda (eni kartdan) content-visibility yoxdur: sürüşəndə kart eni sıçrayardı');
});

test('gözqırpımı: axtarış hərfi dərhal boyanır, nəticə kadrdan sonra və yalnız sonuncu hərf üçün', () => {
  const app = read('assets/app.js');
  assert.ok(/const tok = \+\+qTok;\s*afterFrame\(\(\) => \{ if \(tok !== qTok\) return; renderNav\(\); renderView\(\); \}\);/.test(app));
});

test('gözqırpımı: «daha çox» yalnız yeni kartları əlavə edir, tema yalnız düyməni yeniləyir', () => {
  const app = read('assets/app.js');
  assert.ok(app.includes('if (act === "latest-more") { const was = S.latestCount || 8; S.latestCount = was + 8; if (!moreLatest(was)) renderView(); }'));
  assert.ok(/function moreLatest\(was\) \{[\s\S]*?grid\.append\(t\.content\);[\s\S]*?sec\._src = fresh\.outerHTML;[\s\S]*?idle\(renderView, 300, 2000\);/.test(app), 'bölmənin sətri növbəti çəkilişlə eynidir, aşağı bölmələr boş anda');
  const pref = app.slice(app.indexOf('function setPref(act)'), app.indexOf('} else {', app.indexOf('function setPref(act)')));
  assert.ok(pref.includes('applyPrefs();') && pref.includes('return;') && !pref.includes('setupMarquees') && !pref.includes('fitNav'), 'rəng yerləşdirməni dəyişmir');
});

test('gözqırpımı: xəbər açılanda lent yenidən təhlil olunmur, məzənnə formatlayıcısı bir dəfə qurulur', () => {
  const app = read('assets/app.js');
  assert.ok(/function relatedOf\(a\) \{\s*const all = S\.data\?\.articles \|\| \[\], df = titleDf\(\)/.test(app));
  assert.ok(app.includes('const df = titleDf(); // sözün neçə başlıqda olduğu'), 'tvOf eyni statistikanı işlədir');
  assert.ok(app.includes('NUM_FMT.set(dec, f = new Intl.NumberFormat("en-US"') && !/toLocaleString\("en-US", \{ minimumFractionDigits/.test(app));
  const f = new Intl.NumberFormat('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 4 });
  assert.equal(f.format(1.7), (1.7).toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 4 }), 'çıxış eynidir');
});

test('gözqırpımı: tənbəl modul barmaq toxunan an soruşulur, ilk açılışa sorğu əlavə olunmur', () => {
  const app = read('assets/app.js');
  assert.ok(app.includes('document.addEventListener("pointerdown", intent, { capture: true, passive: true });'));
  for (const m of ['import("./lent.js?v=1")', 'import("./follow.js?v=8")', 'dinle.js`)', 'tixLoad']) assert.ok(app.slice(app.indexOf('const INTENT = ['), app.indexOf('function intent(e)')).includes(m), m);
});

test('gözqırpımı: ölçü aləti giriş qapılarını və toxunuşları ölçür, büdcələr bir yerdə', () => {
  const s = read('.github/scripts/speed.cjs');
  for (const n of ['Google: xəbər səhifəsi', 'Google: bölmə səhifəsi', 'paylaşma keçidi (www → sayt)', 'hava səhifəsi', 'namaz səhifəsi', 'məzənnə səhifəsi', 'icmal səhifəsi', 'rayon səhifəsi', 'komanda səhifəsi', 'haqqında səhifəsi'])
    assert.ok(s.includes(`"${n}"`), `giriş: ${n}`);
  for (const n of ['☰ menyu', 'hava pəncərəsi', 'namaz pəncərəsi', 'məzənnə pəncərəsi', 'dil seçimi', 'tema', 'izlə pəncərəsi', 'İdman (bölmə cərgəsi)', '«daha çox» xəbər', 'ulduz (seçilmişlərə)', 'kart → xəbər', 'paylaş pəncərəsi', 'geri: xəbər → ana səhifə', 'Videolent (alt panel)', 'Tıxac (alt panel)', 'idman alt düyməsi', 'axtarışa yazmaq (hər hərf)'])
    assert.ok(s.includes(`"${n}"`), `toxunuş: ${n}`);
  assert.ok(s.includes('Input.dispatchTouchEvent') && s.includes('type: "event", durationThreshold: 16'), 'həqiqi toxunuş və Event Timing (el.click() INP yazmır)');
  assert.ok(/await giris\(\);\s*await klik\(\);/.test(s), 'tam dövrədə (PR, main, gecə) hər ikisi işləyir');
  for (const k of ['inp', 'klik.gorunme', 'klik.sebeke', 'giris.sehife', 'yeni.sert2']) assert.ok(k in B.speed, k);
  assert.ok(!/SPEED_PROF|SPEED_BLOCK|SPEED_DIAG/.test(s), 'müvəqqəti diaqnostika qalmayıb');
});
