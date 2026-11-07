// Bayram təbriki (sahib, 2026-11-07: «8 noyabr Zəfər Günü münasibətilə 00:00-dan sonra saytı açanda təbrik banneri açılsın»).
// app.js bu modulu yalnız bayram günü (Bakı vaxtı) yükləyir; adi gündə heç bir bayt gəlmir. Təbrik sahibin seçdiyi banner şəklidir
// (assets/bayram-zefer.webp, 800×800, ~67 KB): yalnız bu gün, ilk ekrandan sonra yüklənir. Sağ yuxarıda ✕; kənara toxunmaq və Esc də
// bağlayır. Brauzer sessiyasında bir dəfə açılır.
const DAYS = {
  "11-08": {
    // Mətn sahibindir (2026-11-07). Şəkildəki yazı: «Azərbaycan xalqının ZƏFƏR günü mübarək olsun!»
    title: "8ULDUZ.AZ Azərbaycanın ZƏFƏR GÜNÜnü təbrik edir!",
    img: "bayram-zefer.webp",
    alt: "8 Noyabr, Zəfər Günü. Azərbaycan xalqının Zəfər günü mübarək olsun! Qarabağ Azərbaycandır! 8ulduz.az",
  },
};

const CSS = `
.bayram{position:fixed;inset:0;z-index:2000;display:grid;place-items:center;padding:16px;background:#000c;animation:bayram-in .25s ease-out}
.bayram-card{position:relative;width:min(480px,100%,90dvh);aspect-ratio:1;border-radius:16px;overflow:hidden;background:#0b0a09;box-shadow:0 18px 40px #000a}
.bayram-card img{display:block;width:100%;height:100%;object-fit:cover}
.bayram-x{position:absolute;top:10px;right:10px;width:40px;height:40px;padding:0;border:0;border-radius:50%;background:#000a;color:#fff;font:700 22px/40px system-ui,sans-serif;cursor:pointer;backdrop-filter:blur(4px)}
.bayram-x:hover{background:#000d}
.bayram-x:focus-visible{outline:2px solid #fff;outline-offset:2px}
@keyframes bayram-in{from{opacity:0}to{opacity:1}}
@media (prefers-reduced-motion:reduce){.bayram{animation:none}}
`;

const esc = s => String(s).replace(/[&<>"]/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" })[c]);

export function show(key, doc = document, store = globalThis.sessionStorage) {
  const day = DAYS[key];
  if (!day || doc.querySelector(".bayram")) return null;
  const seen = "8ulduz-bayram-" + key;
  try { if (store?.getItem(seen) && !/[?&]bayram\b/.test(globalThis.location?.search || "")) return null; store?.setItem(seen, "1"); } catch {}
  if (!doc.getElementById("bayram-style")) { const st = doc.createElement("style"); st.id = "bayram-style"; st.textContent = CSS; doc.head.append(st); }
  const src = new URL(day.img, import.meta.url).href; // şəkil modulun öz qovluğundadır (assets/)
  const box = doc.createElement("div");
  box.className = "bayram";
  box.setAttribute("role", "dialog"); box.setAttribute("aria-modal", "true"); box.setAttribute("aria-label", day.title);
  box.innerHTML = `<div class="bayram-card"><img src="${esc(src)}" width="800" height="800" alt="${esc(day.alt)}" decoding="async">`
    + `<button type="button" class="bayram-x" aria-label="Bağla" title="Bağla">✕</button></div>`;
  const close = () => { box.remove(); doc.removeEventListener("keydown", onKey); };
  const onKey = e => { if (e.key === "Escape") close(); };
  box.addEventListener("click", e => { if (e.target === box || e.target.closest?.("button")) close(); });
  doc.addEventListener("keydown", onKey);
  doc.body.append(box);
  try { box.querySelector("button").focus({ preventScroll: true }); } catch {}
  return box;
}
