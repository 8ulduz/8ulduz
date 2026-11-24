const { test } = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');

// Alt pəncərələrin rəngi saytın əksidir (2026-11-24). Pəncərədə fon dəyişəni dəyişəndə
// yazı dəyişəni köhnə qalanda yazı oxunmurdu: seçili «AZ» və ☰-də «İdman» tünd göy üstündə tünd göy.
// Burada pəncərədə işlənən hər fon/yazı cütü hər iki temada WCAG AA (4,5) həddindən yuxarı olmalıdır.
const css = fs.readFileSync(path.join(__dirname, '..', 'assets', 'app.css'), 'utf8');
const SEL = '.nav-pop,.nav-more-pop,.wx-pop,.pray-pop,.fx-pop,.ldd-pop,.altpop div,.sharepop,.follow-dialog';
const body = re => { const m = css.match(re); assert.ok(m, `CSS-də tapılmadı: ${re}`); return m[1]; };
const esc = s => s.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
const vars = text => Object.fromEntries(text.split(';').map(d => d.split(':')).filter(p => p[0].trim().startsWith('--')).map(([k, ...v]) => [k.trim(), v.join(':').trim()]));

const pop = { dark: body(/:root\{--pop:(#[0-9a-f]{6})\}/), light: body(/:root\[data-theme=light\]\{--pop:(#[0-9a-f]{6})\}/) };
const base = vars(body(new RegExp(`(?:^|[}\\n])${esc(SEL)}\\{([^}]*)\\}`)));
const light = { ...base, ...vars(body(new RegExp(`:root\\[data-theme=light\\] :is\\(${esc(SEL)}\\)\\{([^}]*)\\}`))) };

function color(v, theme) {
  const set = theme === 'light' ? light : base;
  for (let i = 0; i < 5; i++) {
    const m = v.match(/^var\((--[\w-]+)\)$/);
    if (!m) break;
    v = m[1] === '--pop' ? pop[theme] : set[m[1]];
    assert.ok(v, `${m[1]} pəncərədə təyin olunmayıb (${theme})`);
  }
  assert.match(v, /^#[0-9a-f]{3}(?:[0-9a-f]{3})?$/i, `bərk rəng deyil: ${v}`);
  const h = v.length === 4 ? v.slice(1).split('').map(c => c + c).join('') : v.slice(1);
  return [0, 2, 4].map(i => parseInt(h.slice(i, i + 2), 16));
}
const lum = c => c.map(x => { x /= 255; return x <= 0.03928 ? x / 12.92 : ((x + 0.055) / 1.055) ** 2.4; }).reduce((s, x, i) => s + x * [0.2126, 0.7152, 0.0722][i], 0);
const ratio = (a, b) => { const [x, y] = [lum(a), lum(b)].sort((p, q) => q - p); return (x + 0.05) / (y + 0.05); };

// [fon, yazı]: app.css-də pəncərə içində birlikdə işlənən cütlər.
const PAIRS = [
  ['--card', '--fg'], ['--card', '--muted'], ['--card', '--primary'],
  ['--card2', '--fg'], ['--card2', '--primary'],
  ['--primary', '--primary-fg'], // .ldm.on (dil), nav.main a.on (☰), .btn
  ['--nav-row2', '--fg'], ['--nav-row3', '--fg'],
  ['--nav-chip', '--fg'], ['--nav-chip2', '--fg'], ['--nav-chip3', '--fg'],
  ['--nav-chip', '--primary'], ['--nav-chip2', '--primary'], ['--nav-chip3', '--primary'], // .pill.all
  ['--nav-on', '#fff'], ['--nav-on2', '#fff'], ['--nav-on3', '#fff'], // .pop-col .pill.on
  ['--sky-fill', '--sky-on'], ['--sky-fill', '--sky-dim'],
  ['--pray-fill', '--pray-on'], ['--pray-next', '--pray-on'],
];

for (const theme of ['dark', 'light']) {
  test(`alt pəncərələrdə yazı oxunur: ${theme} tema`, () => {
    const bad = [];
    for (const [bg, fg] of PAIRS) {
      const r = ratio(color(bg.startsWith('--') ? `var(${bg})` : bg, theme), color(fg.startsWith('--') ? `var(${fg})` : fg, theme));
      if (r < 4.5) bad.push(`${bg} üstündə ${fg}: ${r.toFixed(2)}`);
    }
    assert.deepEqual(bad, []);
  });
}

test('dil pəncərəsində izah yazısı solğunlaşdırılmır', () => {
  // opacity:.75 ilə --muted krem fonda 3,3 kontrast verirdi.
  assert.doesNotMatch(css, /\.ldd-pop \.lang-note\{[^}]*opacity/);
});
