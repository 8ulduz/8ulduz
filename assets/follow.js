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
.follow-dialog{position:fixed;inset:0 auto auto 8px;z-index:1200;box-sizing:border-box;width:min(260px,calc(100vw - 16px));max-height:85dvh;margin:0;padding:8px;border:1px solid var(--border);border-radius:10px;background:var(--nav-row);color:var(--fg);box-shadow:0 14px 28px #0006;font:inherit;overflow:auto;overscroll-behavior:contain}
.follow-dialog header{display:flex;align-items:center;justify-content:space-between;gap:8px}
.follow-dialog h2{margin:0;font-size:.9rem;line-height:1.3}
.follow-dialog .follow-close{width:32px;height:32px;flex:none;border-radius:50%;font-size:22px;color:var(--muted)}
.follow-dialog p{margin:0 0 8px;color:var(--muted);font-size:.72rem;line-height:1.4}
.follow-grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:6px}
.follow-grid a{display:flex;align-items:center;gap:6px;min-height:38px;padding:6px 8px;border:1px solid var(--border);border-radius:6px;background:var(--card);font-size:.82rem;line-height:1.3;font-weight:var(--fw-semibold);overflow-wrap:anywhere}
.follow-grid a:last-child:nth-child(odd){grid-column:1/-1}
.follow-grid a:hover{border-color:var(--primary)}
.follow-grid svg,.follow-grid .follow-google{width:18px;height:18px;flex:none;fill:currentColor}
.follow-grid .follow-google{display:grid;place-items:center;font-weight:var(--fw-bold)}
.follow-tg{display:block;margin-top:6px;padding:8px;border:1px solid var(--primary);border-radius:6px;background:var(--card);font-size:.82rem;font-weight:var(--fw-semibold);text-align:center}
.follow-dialog :focus-visible{outline:2px solid var(--primary);outline-offset:3px}
`;

export function followPosition(anchor, size, viewport) {
  const edge = 8, gap = 6, width = Math.min(260, viewport.width - 2 * edge);
  const below = Math.max(0, viewport.height - edge - anchor.bottom - gap), above = Math.max(0, anchor.top - gap - edge);
  if (Math.max(below, above) < Math.min(size.height, 160)) return {width, maxHeight: viewport.height - 2 * edge, left: Math.max(edge, Math.min(anchor.right - width, viewport.width - width - edge)), top: edge};
  const down = below >= Math.min(size.height, 240) || below >= above;
  const maxHeight = Math.max(1, Math.min(viewport.height - 2 * edge, down ? below : above)), height = Math.min(size.height, maxHeight);
  return {width, maxHeight, left: Math.max(edge, Math.min(anchor.right - width, viewport.width - width - edge)), top: Math.max(edge, Math.min(down ? anchor.bottom + gap : anchor.top - gap - height, viewport.height - edge - height))};
}

// Back dismisses the panel without leaving the current article or changing its hash.
export function wireFollowDialog(dialog, opener, win = window) {
  let hasEntry = false, closing = false, waitingPop = false, restoreFocus = true, navigateAfter;
  const navigate = () => { const hash = navigateAfter; navigateAfter = null; if (hash) win.location.hash = hash; };
  const cleanup = () => {
    if (!waitingPop) { win.removeEventListener('popstate', popped); navigate(); }
    win.removeEventListener('click', outside, true);
    win.removeEventListener('keydown', escaped);
    win.removeEventListener('resize', close);
    win.removeEventListener('scroll', scrolled, true);
    opener?.setAttribute?.('aria-expanded', 'false');
    if (restoreFocus && opener?.isConnected) opener.focus({preventScroll: true});
    dialog.remove();
  };
  const popped = () => {
    waitingPop = false;
    if (dialog.open) dialog.close();
    else { win.removeEventListener('popstate', popped); navigate(); }
  };
  const close = () => {
    if (closing) return;
    closing = true;
    if (hasEntry && win.history.state?.['8ulduz-follow']) { waitingPop = true; win.history.back(); }
    if (dialog.open) dialog.close();
  };
  const outside = event => {
    if (event.target === opener || opener?.contains?.(event.target) || event.target === dialog || dialog.contains?.(event.target)) return;
    restoreFocus = false;
    const link = event.target?.closest?.('a[href^="#"]');
    if (link && !event.ctrlKey && !event.metaKey && !event.shiftKey && !link.target) { event.preventDefault(); navigateAfter = link.getAttribute('href'); }
    close();
  };
  const escaped = event => { if (event.key === 'Escape') { event.preventDefault(); close(); } };
  const scrolled = event => { if (event.target === win || event.target === win.document || event.target === win.document?.documentElement) { restoreFocus = false; close(); } };
  dialog.addEventListener('cancel', event => { event.preventDefault(); close(); });
  dialog.addEventListener('close', cleanup, {once: true});
  dialog.querySelector('.follow-close').addEventListener('click', close);
  try {
    const viewport = {width: win.document.documentElement.clientWidth || win.innerWidth, height: win.innerHeight};
    if (dialog.style) dialog.style.width = Math.min(260, viewport.width - 16) + 'px';
    dialog.show();
    if (opener?.getBoundingClientRect && dialog.style) {
      const button = opener.getBoundingClientRect(), head = opener.closest?.('#sitehead')?.getBoundingClientRect();
      const anchor = head ? {top: head.top, bottom: head.bottom, right: button.right} : button;
      const pos = followPosition(anchor, dialog.getBoundingClientRect(), viewport);
      for (const [key, value] of Object.entries(pos)) dialog.style[key] = value + 'px';
    }
    opener?.setAttribute?.('aria-expanded', 'true');
    try { win.history.pushState({...win.history.state, '8ulduz-follow': true}, '', win.location.href); hasEntry = true; } catch {}
    win.addEventListener('popstate', popped);
    win.addEventListener('click', outside, true);
    win.addEventListener('keydown', escaped);
    win.addEventListener('resize', close);
    win.addEventListener('scroll', scrolled, {capture: true, passive: true});
  } catch (error) { cleanup(); throw error; }
  return close;
}

let activeClose;
export function openFollow(opener, track = () => {}, chromeLink = () => '') {
  if (document.querySelector('.follow-dialog[open]')) { activeClose?.(); return; }
  if (!document.getElementById('follow-style')) {
    const style = document.createElement('style'); style.id = 'follow-style'; style.textContent = styles; document.head.append(style);
  }
  const dialog = document.createElement('dialog');
  dialog.className = 'follow-dialog';
  dialog.setAttribute('aria-labelledby', 'follow-title');
  dialog.innerHTML = '<header><h2 id="follow-title">8ULDUZ-u izlə</h2><button type="button" class="follow-close" aria-label="Bağla" autofocus>×</button></header><p>Sizə rahat olan platformanı seçin.</p><div class="follow-grid"></div>';
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
      activeClose?.();
      const app = chromeLink(item.href);
      if (app) { event.preventDefault(); location.href = app; }
    });
    grid.append(link);
  }
  // «Telegram-da izlə» botu (izle.cjs): oxucu istədiyi mövzunu bota yazır (pensiya, Gəncə, hava...).
  const bot = globalThis.SITE_CONFIG?.tgBot;
  if (bot && grid.children.length) {
    const tg = document.createElement('a');
    tg.className = 'follow-tg'; tg.href = `https://t.me/${bot}?start=movzu`; tg.target = '_blank'; tg.rel = 'noopener noreferrer';
    tg.textContent = '📩 İstədiyiniz mövzunu Telegram-da izləyin';
    tg.addEventListener('click', () => { track('follow-tgbot'); activeClose?.(); });
    grid.after(tg);
  }
  if (!grid.children.length) { grid.remove(); dialog.querySelector('p').textContent = 'İzləmə kanalları hazırda əlçatan deyil. Daha sonra yenidən yoxlayın.'; }
  document.body.append(dialog);
  activeClose = wireFollowDialog(dialog, opener);
}
