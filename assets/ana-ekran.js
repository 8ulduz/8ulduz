// «Ana ekrana əlavə et» ipucu: brauzer quraşdırma təklifi verməyəndə (sahib, 2026-11-10: düymə telefonda həmişə görünsün).
// Yalnız düyməyə basanda yüklənir (app.min.js 170 000 bayt büdcəsi). Daxili brauzer (Facebook, Instagram, Android WebView)
// ana ekrana əlavə etmir: əvvəl Safari / Chrome-da açılır. chrome — Android-də Chrome-da açan intent:// ünvanı (app.js appLink kimi).
const esc = s => String(s).replace(/[&<>"']/g, c => `&#${c.charCodeAt(0)};`);
const here = globalThis.location;
const chromeOf = (ua, l = here) => l && /Android/.test(ua) ? `intent://${l.host}${l.pathname}${l.search}#Intent;scheme=https;package=com.android.chrome;S.browser_fallback_url=${encodeURIComponent(l.href)};end` : "";
export function hint(ua, ios, chrome = chromeOf(ua)) {
  const A = "<b>Ana ekrana əlavə et</b>", inApp = /FBAN|FBAV|Instagram|Line\/|; wv\)/.test(ua);
  if (ios) return `<p>${inApp ? "Yuxarıdakı <b>⋯</b> → <b>Safari-də aç</b>, sonra " : ""}<b>Paylaş</b> ⬆ → ${A}.</p>`;
  const how = /SamsungBrowser/.test(ua) ? "Aşağıdakı <b>≡</b> menyusu → <b>Səhifəni əlavə et</b> → <b>Ana ekran</b>"
    : /Firefox/.test(ua) ? `Brauzerin <b>⋮</b> menyusu → <b>Quraşdır</b> (və ya ${A})`
    : `Brauzerin <b>⋮</b> menyusu → ${A} (və ya <b>Tətbiqi quraşdır</b>)`;
  if (!inApp) return `<p>${how}.</p>`;
  return `<p>Bu pəncərə tətbiqin daxili brauzeridir, ana ekrana buradan əlavə olunmur.</p>${chrome ? `<p><a class="btn" href="${esc(chrome)}">Chrome-da aç</a></p>` : ""}<p>Chrome-da <b>⋮</b> → ${A}.</p>`;
}
