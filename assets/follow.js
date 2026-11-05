// Loaded only on click. Trusted styles travel with the module: one small request opens the panel.
const platforms = [
  ['telegram', 'Telegram', 'tg', ['t.me', 'telegram.me']],
  ['whatsapp', 'WhatsApp', 'wa', ['whatsapp.com']],
  ['facebook', 'Facebook', 'fb', ['facebook.com', 'fb.com']],
  ['instagram', 'Instagram', 'ig', ['instagram.com']],
  ['googleNews', 'Google News', '', ['news.google.com']],
  ['linkedin', 'LinkedIn', 'in', ['linkedin.com']],
  ['youtube', 'YouTube', 'yt', ['youtube.com']],
  ['x', 'X', 'x', ['x.com', 'twitter.com']],
];

export function followLinks(config = {}) {
  const links = {telegram: config.telegram, ...config.follow};
  return platforms.flatMap(([id, label, icon, hosts]) => {
    try {
      const url = new URL(String(links[id] || '').trim());
      const host = url.hostname.replace(/^www\./, '');
      if (url.protocol !== 'https:' || url.username || url.password || url.port || !hosts.includes(host) || url.pathname === '/') return [];
      if (id === 'whatsapp' && !/^\/channel\/[^/]+\/?$/.test(url.pathname)) return [];
      if (id === 'googleNews' && !/^\/publications\/[^/]+/.test(url.pathname)) return [];
      if (id === 'linkedin' && !/^\/(?:company|in)\/[^/]+\/?$/.test(url.pathname)) return [];
      return [{id, label, icon, href: url.href}];
    } catch { return []; }
  });
}

const styles = `
.follow-dialog{position:fixed;inset:auto 0 0;box-sizing:border-box;width:min(100%,480px);max-height:85dvh;margin:0 auto;padding:10px 16px max(20px,env(safe-area-inset-bottom));border:1px solid var(--border);border-radius:22px 22px 0 0;background:var(--card);color:var(--fg);font:inherit;overflow:auto;overscroll-behavior:contain}
.follow-dialog::backdrop{background:#0009}
.follow-dialog .follow-handle{width:36px;height:4px;margin:0 auto 6px;border-radius:4px;background:var(--border)}
.follow-dialog header{display:flex;align-items:center;justify-content:space-between;gap:8px}
.follow-dialog h2{margin:0;font-size:var(--fs-title);line-height:var(--lh-title)}
.follow-dialog .follow-close{width:44px;height:44px;flex:none;border-radius:50%;font-size:22px;color:var(--muted)}
.follow-dialog p{margin:0 0 16px;color:var(--muted);font-size:var(--fs-meta);line-height:var(--lh-meta)}
.follow-grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:10px}
.follow-grid a{display:flex;align-items:center;gap:10px;min-height:56px;padding:10px 12px;border:1px solid var(--border);border-radius:12px;background:var(--card2);font-size:var(--fs-body);line-height:var(--lh-body);font-weight:var(--fw-semibold);overflow-wrap:anywhere}
.follow-grid a:only-child{grid-column:1/-1}
.follow-grid a:hover{border-color:var(--primary)}
.follow-grid svg,.follow-grid .follow-google{width:20px;height:20px;flex:none;fill:currentColor}
.follow-grid .follow-google{display:grid;place-items:center;font-weight:var(--fw-bold)}
.follow-dialog :focus-visible{outline:2px solid var(--primary);outline-offset:3px}
html.follow-open{overflow:hidden}
@media(min-width:721px){.follow-dialog{inset:0;margin:auto;height:fit-content;border-radius:18px}}
`;

// Back dismisses the panel without leaving the current article or changing its hash.
export function wireFollowDialog(dialog, opener, win = window) {
  let hasEntry = false, closing = false;
  const savedOverflow = win.document.documentElement.classList.contains('follow-open');
  const cleanup = () => {
    win.removeEventListener('popstate', popped);
    if (!savedOverflow) win.document.documentElement.classList.remove('follow-open');
    if (opener?.isConnected) opener.focus({preventScroll: true});
    dialog.remove();
  };
  const popped = () => {
    if (dialog.open) dialog.close();
  };
  const close = () => {
    if (closing) return;
    closing = true;
    if (hasEntry && win.history.state?.['8ulduz-follow']) win.history.back();
    else dialog.close();
  };
  dialog.addEventListener('cancel', event => { event.preventDefault(); close(); });
  dialog.addEventListener('close', cleanup, {once: true});
  dialog.querySelector('.follow-close').addEventListener('click', close);
  dialog.addEventListener('click', event => {
    if (event.target !== dialog) return;
    const r = dialog.getBoundingClientRect();
    if (event.clientX < r.left || event.clientX > r.right || event.clientY < r.top || event.clientY > r.bottom) close();
  });
  try {
    dialog.showModal();
    win.document.documentElement.classList.add('follow-open');
    try { win.history.pushState({...win.history.state, '8ulduz-follow': true}, '', win.location.href); hasEntry = true; } catch {}
    win.addEventListener('popstate', popped);
  } catch (error) { cleanup(); throw error; }
  return close;
}

export function openFollow(opener, track = () => {}, chromeLink = () => '') {
  if (document.querySelector('.follow-dialog[open]')) return;
  if (!document.getElementById('follow-style')) {
    const style = document.createElement('style'); style.id = 'follow-style'; style.textContent = styles; document.head.append(style);
  }
  const dialog = document.createElement('dialog');
  dialog.className = 'follow-dialog';
  dialog.setAttribute('aria-labelledby', 'follow-title');
  dialog.innerHTML = '<div class="follow-handle" aria-hidden="true"></div><header><h2 id="follow-title">8ULDUZ-u izlə</h2><button type="button" class="follow-close" aria-label="Bağla" autofocus>×</button></header><p>Sizə rahat olan platformanı seçin.</p><div class="follow-grid"></div>';
  const grid = dialog.querySelector('.follow-grid');
  for (const item of followLinks(globalThis.SITE_CONFIG)) {
    const link = document.createElement('a');
    link.href = item.href; link.target = '_blank'; link.rel = 'noopener noreferrer';
    if (item.icon) {
      const svg = document.createElementNS('http://www.w3.org/2000/svg', 'svg');
      svg.setAttribute('aria-hidden', 'true');
      const use = document.createElementNS('http://www.w3.org/2000/svg', 'use');
      use.setAttribute('href', new URL('sosial.svg#' + item.icon, import.meta.url).href);
      svg.append(use); link.append(svg);
    } else {
      const mark = document.createElement('span'); mark.className = 'follow-google'; mark.textContent = 'G'; mark.setAttribute('aria-hidden', 'true'); link.append(mark);
    }
    link.append(document.createTextNode(item.label));
    link.addEventListener('click', event => {
      track('follow-' + item.id);
      const app = chromeLink(item.href);
      if (app) { event.preventDefault(); location.href = app; }
    });
    grid.append(link);
  }
  if (!grid.children.length) { grid.remove(); dialog.querySelector('p').textContent = 'İzləmə kanalları hazırda əlçatan deyil. Daha sonra yenidən yoxlayın.'; }
  document.body.append(dialog);
  wireFollowDialog(dialog, opener);
}
