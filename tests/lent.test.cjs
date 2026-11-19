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
  assert.match(src, /const FRESH_MS = 120e3/, '2 dəqiqədən bir yeni video yoxlanır');
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
