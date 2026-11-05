const { test } = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const root = path.join(__dirname, '..');

test('optional assets cannot block shell installation; a used module remains available offline', async () => {
  const origin = 'https://example.com/';
  const events = {}, store = new Map(), requests = [];
  let online = true, optionalAvailable = false;
  const key = input => new URL(input.url || String(input), origin).href;
  const fetchFile = async input => {
    const url = key(input), file = new URL(url).pathname.slice(1) || 'index.html';
    requests.push(file);
    if (!online) throw Error('offline');
    if (!optionalAvailable && /assistant|reader|icon-512|maskable|og-default/.test(file)) return new Response('', {status: 404});
    return new Response(fs.readFileSync(path.join(root, file)), {headers: {'content-type': 'text/javascript'}});
  };
  const cache = {
    match: async req => store.get(key(req))?.clone(),
    put: async (req, response) => { store.set(key(req), response.clone()); },
    addAll: async urls => {
      for (const url of urls) {
        const response = await fetchFile(url);
        if (!response.ok) throw Error('precache failed: ' + url);
        await cache.put(url, response);
      }
    },
  };
  const context = vm.createContext({URL, Request, Response, Headers, console, AbortController, Date, setTimeout, clearTimeout,
    fetch: fetchFile, caches: {open: async () => cache},
    self: {location: new URL('sw.js', origin), addEventListener: (name, fn) => { events[name] = fn; },
      skipWaiting: async () => {}, clients: {matchAll: async () => []}},
  });
  vm.runInContext(fs.readFileSync(path.join(root, 'sw.js'), 'utf8'), context);
  let installed;
  events.install({waitUntil: promise => { installed = promise; }});
  await installed;
  assert.ok(store.has(origin + 'index.html'));
  assert.ok(store.has(origin + 'assets/app.js'));
  assert.ok(store.has(origin + 'assets/voice-search.js'));
  assert.ok(!requests.includes('assets/assistant.js'));

  const get = async file => {
    let response;
    const background = [];
    events.fetch({request: new Request(origin + file), respondWith: promise => { response = promise; }, waitUntil: promise => background.push(promise)});
    const result = await response;
    await Promise.all(background);
    return result;
  };
  optionalAvailable = true;
  const first = await get('assets/assistant.js');
  assert.equal(first.status, 200);
  const body = await first.text();
  assert.ok(store.has(origin + 'assets/assistant.js'));
  online = false;
  assert.equal(await (await get('assets/assistant.js')).text(), body);
  assert.match(await (await get('index.html')).text(), /8ulduz — Son xəbərlər/);
});
