import {GithubEditor, removalKey, parsePolicy} from '../assets/editorial-store.js?v=2';

if (top !== self) { document.documentElement.hidden = true; throw new Error('Panel çərçivədə açılmır.'); }

const $ = s => document.querySelector(s), editor = new GithubEditor();
let articles = [], selected = null, busy = false, generation = 0;
const removed = new Set();
const status = (text, error = false) => { $('#status').textContent = text; $('#status').className = error ? 'error' : 'success'; };
const el = (tag, text) => { const n = document.createElement(tag); n.textContent = text; return n; };
const matches = a => removed.has(a.id) || removed.has(a.sourceUrl) || removed.has(removalKey(a.sourceUrl));
function choose(article) {
  if (busy || !editor.user) return;
  selected = article; $('#chosen-title').textContent = article.title || article.sourceUrl;
  $('#chosen-url').textContent = article.sourceUrl; $('#chosen-url').href = article.sourceUrl;
  $('#confirm').showModal();
}
function render() {
  const query = $('#search').value.trim().toLocaleLowerCase('az');
  const list = articles.filter(a => !matches(a) && (!query || `${a.title} ${a.source} ${a.sourceUrl}`.toLocaleLowerCase('az').includes(query)));
  $('#count').textContent = list.length + ' xəbər' + (list.length > 100 ? ' · ilk 100 göstərilir' : '');
  $('#results').replaceChildren(...list.slice(0, 100).map(a => {
    const row = el('article', ''); row.className = 'result';
    const copy = el('div', ''); copy.append(el('h3', a.title), el('p', a.source || new URL(a.sourceUrl).hostname));
    const link = el('a', 'Mənbədə aç ↗'); link.href = a.sourceUrl; link.target = '_blank'; link.rel = 'noopener noreferrer'; copy.append(link);
    const button = el('button', 'Sil'); button.type = 'button'; button.disabled = busy; button.addEventListener('click', () => choose(a)); row.append(copy, button); return row;
  }));
}
async function json(url) { const r = await fetch(url, {cache: 'no-store'}); if (!r.ok) throw new Error('Xəbər siyahısı yüklənmədi.'); return r.json(); }
async function loadArticles() {
  const files = ['news.json', 'news.en.json', 'news.ru.json', 'news.tr.json'];
  const results = await Promise.allSettled(files.map(f => json('../data/' + f + '?t=' + Date.now())));
  if (results[0].status === 'rejected') throw results[0].reason;
  const seen = new Map();
  for (const result of results) if (result.status === 'fulfilled') for (const a of result.value.articles || []) {
    try { removalKey(a.sourceUrl); if (!seen.has(a.sourceUrl)) seen.set(a.sourceUrl, a); } catch {}
  }
  articles = [...seen.values()].sort((a, b) => String(b.publishedAt).localeCompare(String(a.publishedAt))); render();
}
$('#login-form').addEventListener('submit', async event => {
  event.preventDefault(); const input = $('#token'), token = input.value; input.value = ''; const button = event.submitter; button.disabled = true;
  status('Giriş yoxlanılır…');
  try {
    const user = await editor.login(token); $('#account').textContent = '@' + user;
    $('#login-panel').hidden = true; $('#editor').hidden = false;
    const policy = parsePolicy((await editor.policy()).text).data;
    for (const r of Object.values(policy.removedArticles || {})) for (const key of [r.id, r.key, ...(r.ids || []), ...(r.urls || []), ...(r.keys || [])]) if (key) removed.add(key);
    await loadArticles(); status('Xəbəri axtarın və ya keçidini daxil edin.');
  } catch (error) { editor.logout(); $('#editor').hidden = true; $('#login-panel').hidden = false; status(error.message, true); }
  finally { button.disabled = false; }
});
function logout() { generation++; editor.logout(); selected = null; articles = []; removed.clear(); $('#results').replaceChildren(); $('#editor').hidden = true; $('#login-panel').hidden = false; if ($('#confirm').open) $('#confirm').close(); status('Giriş bağlandı.'); }
$('#logout').addEventListener('click', logout);
window.addEventListener('pagehide', () => { generation++; editor.logout(); });
window.addEventListener('pageshow', event => { if (event.persisted) logout(); });
$('#search').addEventListener('input', render);
$('#cancel').addEventListener('click', () => $('#confirm').close());
$('#url-form').addEventListener('submit', async event => {
  event.preventDefault(); if (busy) return;
  try {
    const u = new URL($('#source-url').value), isOwn = ['8ulduz.az', 'www.8ulduz.az', '8ulduz.github.io'].includes(u.hostname);
    let a;
    if (isOwn) {
      const id = u.hash.match(/^#\/xeber\/([0-9a-f]{16})$/)?.[1] || u.pathname.match(/\/x\/([0-9a-f]{16})(?:\.html)?\/?$/)?.[1];
      if (!id) throw new Error('8ULDUZ-da xəbərin öz keçidini daxil edin.');
      a = articles.find(a => a.id === id);
      if (!a) { const d = await json('../data/paylas/' + (parseInt(id.slice(0, 2), 16) >> 3) + '.json?t=' + Date.now()); a = d.articles?.find(a => a.id === id); if (a?.of) a = articles.find(row => row.id === a.of); }
      if (!a?.sourceUrl) throw new Error('Bu xəbər tapılmadı. Mənbədəki keçidi daxil edin.');
    } else { const key = removalKey(u.href); a = articles.find(a => removalKey(a.sourceUrl) === key) || {sourceUrl: u.href, title: u.href}; }
    if (matches(a)) throw new Error('Bu xəbər artıq çıxarılma siyahısındadır.');
    choose(a);
  } catch (error) { status(error.message, true); }
});
$('#remove').addEventListener('click', async () => {
  if (!selected || busy) return;
  busy = true; $('#remove').disabled = true; $('#cancel').disabled = true; $('#logout').disabled = true;
  const current = ++generation; status('Silinmə qeydə alınır…');
  try {
    const {record, already} = await editor.remove(selected);
    if (current !== generation) return;
    for (const key of [...record.ids, ...record.urls, ...record.keys]) removed.add(key);
    $('#confirm').close(); selected = null; render();
    status(already ? 'Xəbər artıq çıxarılma siyahısındadır.' : 'Silinmə saxlanıldı. Ümumi saytda növbəti canlı yenilənməsinə ötürülür…');
    void waitForLive(record, current);
  } catch (error) { status('Silinmə saxlanılmadı. ' + error.message, true); }
  finally { busy = false; $('#remove').disabled = false; $('#cancel').disabled = false; $('#logout').disabled = false; render(); }
});
$('#confirm').addEventListener('cancel', event => { if (busy) event.preventDefault(); });
async function waitForLive(record, current) {
  for (let i = 0; i < 12 && generation === current; i++) {
    await new Promise(resolve => setTimeout(resolve, 10000));
    if (generation !== current || !editor.user) return;
    try { if (await editor.liveContains(record)) { status('Silinmə canlı axına çatdı. Açıq səhifələr növbəti yoxlamada tətbiq edəcək.'); return; } } catch {}
  }
  if (generation === current) status('Silinmə saxlanılıb, amma canlı axında hələ təsdiqlənməyib. Xəbər yeniləyicisinin işlədiyini yoxlayın.', true);
}
