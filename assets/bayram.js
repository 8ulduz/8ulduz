// Bayram təbriki (sahib, 2026-11-07: «8 noyabr Zəfər Günü münasibətilə 00:00-dan sonra saytı açanda təbrik banneri açılsın»).
// app.js bu modulu yalnız bayram günü (Bakı vaxtı) yükləyir; adi gündə heç bir bayt gəlmir. Şəkil faylı yoxdur: bayraq rəngləri
// və aypara-ulduz CSS/SVG ilə. Brauzer sessiyasında bir dəfə açılır; «Bağla», kənara toxunmaq və Esc bağlayır.
const DAYS = {
  "11-08": {
    // Mətn sahibindir (2026-11-07): «8 ulduz.az Azərbaycanın ZƏFƏR GÜNÜnü təbrik edir».
    top: "8 Noyabr",
    title: "8ULDUZ.AZ Azərbaycanın ZƏFƏR GÜNÜnü təbrik edir!",
    text: "",
  },
};

const STAR = '<svg viewBox="0 0 100 100" width="44" height="44" aria-hidden="true"><circle cx="44" cy="50" r="30" fill="#fff"/><circle cx="52" cy="50" r="24" fill="#ef3340"/>'
  + '<polygon fill="#fff" points="75,50 69.6,52.2 70,58 66.3,53.6 60.7,55 63.8,50 60.7,45 66.3,46.4 70,42 69.6,47.8"/></svg>';

const CSS = `
.bayram{position:fixed;inset:0;z-index:2000;display:grid;place-items:center;padding:16px;background:#000b;animation:bayram-in .25s ease-out}
.bayram-card{position:relative;box-sizing:border-box;width:min(420px,100%);max-height:90dvh;overflow:auto;border-radius:14px;background:#0f1b33;color:#f8fafc;box-shadow:0 18px 40px #0008;text-align:center}
.bayram-flag{display:grid;grid-template-rows:1fr 1fr 1fr;height:96px}
.bayram-flag i{display:block}.bayram-flag i:nth-child(1){background:#00b5e2}.bayram-flag i:nth-child(2){background:#ef3340}.bayram-flag i:nth-child(3){background:#509e2f}
.bayram-flag svg{position:absolute;left:50%;top:26px;transform:translateX(-50%)}
.bayram-body{padding:16px 18px 18px}
.bayram-top{margin:0;color:var(--primary,#fbbf24);font-weight:700;letter-spacing:.06em;text-transform:uppercase;font-size:.8rem}
.bayram h2{margin:6px 0 16px;font-size:1.45rem;line-height:1.3}
.bayram p{margin:0 0 14px;line-height:1.5;font-size:.95rem}
.bayram-sign{margin:0 0 14px!important;font-weight:700;color:#94a3b8}
.bayram button{min-width:120px;min-height:40px;padding:8px 18px;border:0;border-radius:20px;background:var(--primary,#fbbf24);color:#111;font:inherit;font-weight:700;cursor:pointer}
.bayram button:focus-visible{outline:2px solid var(--fg,#fff);outline-offset:3px}
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
  const box = doc.createElement("div");
  box.className = "bayram";
  box.setAttribute("role", "dialog"); box.setAttribute("aria-modal", "true"); box.setAttribute("aria-labelledby", "bayram-t");
  box.innerHTML = `<div class="bayram-card"><div class="bayram-flag"><i></i><i></i><i></i>${STAR}</div><div class="bayram-body">`
    + `<p class="bayram-top">${esc(day.top)}</p><h2 id="bayram-t">${esc(day.title)}</h2>${day.text ? `<p>${esc(day.text)}</p>` : ""}`
    + `<button type="button">Bağla</button></div></div>`;
  const close = () => { box.remove(); doc.removeEventListener("keydown", onKey); };
  const onKey = e => { if (e.key === "Escape") close(); };
  box.addEventListener("click", e => { if (e.target === box || e.target.closest?.("button")) close(); });
  doc.addEventListener("keydown", onKey);
  doc.body.append(box);
  try { box.querySelector("button").focus({ preventScroll: true }); } catch {}
  return box;
}
