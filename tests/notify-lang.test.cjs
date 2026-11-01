// «Son dəqiqə» bildirişi seçilmiş dildə gəlir: açıq səhifədə də, fon yoxlamasında da.
const { test } = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const path = require('node:path');
const root = path.join(__dirname, '..');
const now = () => new Date().toISOString();
const row = (id, lang) => ({ id, lang, title: 'Xəbər ' + id, summary: '', publishedAt: now() });

function page() {
  const memory = new Map();
  const ctx = vm.createContext({
    console, Map, Set, URL, Date, AbortController, setTimeout, clearTimeout, addEventListener() {},
    localStorage: { getItem: k => memory.has(k) ? memory.get(k) : null, setItem: (k, v) => memory.set(k, String(v)), removeItem: k => memory.delete(k) },
    location: { hash: '#/' }, navigator: { onLine: true },
    window: { addEventListener() {} },
    document: { documentElement: { dataset: {} }, addEventListener() {}, querySelector() { return null; }, createElement() { return {}; } },
    matchMedia: () => ({ matches: false }),
  });
  vm.runInContext(fs.readFileSync(path.join(root, 'assets/app.js'), 'utf8').split(/\r?\napplyPrefs\(\);\r?\n/)[0], ctx);
  vm.runInContext('globalThis.shown = []; notifyOn = () => true; showBreaking = a => shown.push(a.id); globalThis.setLangForTest = v => { S.lang = v; };', ctx);
  return ctx;
}

test('açıq səhifə: yalnız seçilmiş dildəki yeni xəbər bildirilir', () => {
  const ctx = page();
  ctx.setLangForTest('az');
  ctx.checkBreaking([]);
  ctx.checkBreaking([row('az1', 'az'), row('ru1', 'ru')]);
  assert.deepEqual(Array.from(ctx.shown), ['az1']);
});

test('dil dəyişəndə artıq görülmüş xəbər təzə kimi gəlmir', () => {
  const ctx = page();
  ctx.setLangForTest('az');
  ctx.checkBreaking([]);
  const list = [row('az1', 'az'), row('ru1', 'ru')];
  ctx.checkBreaking(list);
  ctx.setLangForTest('ru');
  ctx.checkBreaking(list);
  assert.deepEqual(Array.from(ctx.shown), ['az1']);
});

test('«Hamısı» seçiləndə bütün dillər bildirilir', () => {
  const ctx = page();
  ctx.setLangForTest(null);
  ctx.checkBreaking([]);
  ctx.checkBreaking([row('az1', 'az'), row('ru1', 'ru')]);
  assert.deepEqual(Array.from(ctx.shown).sort(), ['az1', 'ru1']);
});

function worker(lang, seen) {
  const store = new Map();
  const cache = {
    match: async u => { const v = store.get(String(u)); return v ? v.clone() : undefined; },
    put: async (u, r) => { store.set(String(u), r.clone()); },
    addAll: async () => {},
  };
  const handlers = {};
  const shown = [];
  const ctx = vm.createContext({
    console, Map, Set, URL, Date, Request, Response, Headers, setTimeout, clearTimeout, AbortController, AbortSignal, Promise, JSON,
    fetch: async () => { throw Error('offline'); },
    caches: { open: async () => cache, keys: async () => [] },
    self: {
      location: new URL('https://8ulduz.az/sw.js'),
      addEventListener: (t, f) => { handlers[t] = f; },
      registration: { showNotification: async (_t, o) => { shown.push(o.data.id); } },
      clients: {},
    },
  });
  vm.runInContext(fs.readFileSync(path.join(root, 'sw.js'), 'utf8'), ctx);
  return { ctx, handlers, shown, cache, lang, seen };
}

async function runSync(w, articles) {
  w.ctx.__data = JSON.stringify({ articles });
  vm.runInContext('freshData = async () => new Response(__data);', w.ctx);
  await w.cache.put(vm.runInContext('SEEN_URL', w.ctx), new Response('[]'));
  await vm.runInContext('syncBreaking()', w.ctx);
}

test('fon yoxlaması: dil bildirilməyibsə Azərbaycan dilində xəbər seçilir', async () => {
  const w = worker();
  await runSync(w, [row('az1', 'az'), row('ru1', 'ru')]);
  assert.deepEqual(w.shown, ['az1']);
});

test('fon yoxlaması: səhifənin bildirdiyi dilə əməl olunur', async () => {
  const w = worker();
  let done;
  w.handlers.message({ data: { type: 'notify-lang', lang: 'ru' }, waitUntil: p => { done = p; } });
  await done;
  await runSync(w, [row('az1', 'az'), row('ru1', 'ru')]);
  assert.deepEqual(w.shown, ['ru1']);
});
