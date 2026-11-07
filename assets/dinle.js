// «Dinlə» (sahib, 2026-11-07: «dinlə funksiyasını mükəmməl şəkildə işə sal»; Edge-dəki təbii Azərbaycan səsi bəyənilib).
// Xəbər səhifəsindəki «🔊 Dinlə» bu modulu yalnız basılanda yükləyir (adi açılışa bayt əlavə olunmur — qırmızı xətt 1).
// Oxunan: başlıq + saytdakı xülasə (saytda onsuz da göstərilən mətn; mənbənin tam mətni yayılmır). «Növbəti» lentdəki
// növbəti Azərbaycan dilində xəbərə keçir — radio kimi. Səs: cihazın Azərbaycan səsi (Edge: «Microsoft … Online (Natural)»
// təbii səs), yoxdursa türk səsi (başa düşülən, yaxın dil); heç biri yoxdursa açıq izah. Kilid ekranı düymələri Media Session ilə.

export function textOf(a, decode = s => s) {
  const clean = s => decode(String(s || "")).replace(/<[^>]+>/g, " ").replace(/\s+/g, " ").trim();
  const title = clean(a?.title).replace(/[.!?…]*$/, "");
  const summary = clean(a?.summary);
  return summary && !summary.startsWith(title) ? `${title}. ${summary}` : title + ".";
}

// Uzun mətn hissələrə bölünür: bəzi brauzerlər (Chrome) 15 saniyədən uzun ifadəni yarıda kəsir.
export function chunks(text, limit = 200) {
  const out = [];
  for (const sentence of String(text || "").match(/[^.!?…]+[.!?…]*\s*/gu) || []) {
    let part = "";
    for (const word of sentence.trim().split(/\s+/)) {
      if (part && part.length + word.length + 1 > limit) { out.push(part); part = ""; }
      part += (part ? " " : "") + word;
    }
    if (part) out.push(part);
  }
  return out;
}

// Səs seçimi: Azərbaycan (təbii/onlayn səs önə), sonra türk; ad sırası sabitdir ki, hər dəfə eyni səs çıxsın.
export function pickVoice(voices) {
  const score = v => (/natural|online|neural/i.test(v.name) ? 2 : 0) + (v.localService ? 0 : 1);
  const best = re => voices.filter(v => re.test(v.lang || "")).sort((x, y) => score(y) - score(x) || String(x.name).localeCompare(String(y.name)))[0];
  const az = best(/^az(?:[-_]|$)/i);
  if (az) return { voice: az, lang: "az-AZ", az: true };
  const tr = best(/^tr(?:[-_]|$)/i);
  return tr ? { voice: tr, lang: "tr-TR", az: false } : null;
}

const CSS = `
.dinle{position:fixed;left:8px;right:8px;bottom:calc(64px + env(safe-area-inset-bottom));z-index:1100;max-width:560px;margin:0 auto;padding:10px 12px;border:1px solid var(--primary,#fbbf24);border-radius:12px;background:#0f1b33;color:#f8fafc;box-shadow:0 10px 28px #0007;font-size:.9rem}
.dinle-t{display:-webkit-box;-webkit-line-clamp:2;-webkit-box-orient:vertical;overflow:hidden;margin:0 0 6px;font-weight:700;line-height:1.3}
.dinle-s{margin:0 0 8px;color:#94a3b8;font-size:.75rem}
.dinle-b{display:flex;gap:6px;flex-wrap:wrap}
.dinle-b button{min-height:36px;padding:6px 12px;border:1px solid #334155;border-radius:18px;background:#1e293b;color:inherit;font:inherit;font-weight:700;cursor:pointer}
.dinle-b button[data-d=pp]{background:var(--primary,#fbbf24);border-color:transparent;color:#111}
@media(min-width:901px){.dinle{bottom:16px}}
`;

export function createPlayer({ list, decode = s => s, doc = document, synth = globalThis.speechSynthesis, Utterance = globalThis.SpeechSynthesisUtterance, nav = globalThis.navigator }) {
  let box = null, cur = null, parts = [], i = 0, gen = 0, choice = null, playing = false;
  const voices = () => new Promise(res => {
    const now = synth?.getVoices?.() || [];
    if (now.length) return res(now);
    let done = false; const end = () => { if (!done) { done = true; res(synth?.getVoices?.() || []); } };
    synth?.addEventListener?.("voiceschanged", end, { once: true }); setTimeout(end, 1500);
  });
  const ui = () => {
    if (box) return box;
    if (!doc.getElementById("dinle-style")) { const st = doc.createElement("style"); st.id = "dinle-style"; st.textContent = CSS; doc.head.append(st); }
    box = doc.createElement("section");
    box.className = "dinle"; box.setAttribute("aria-label", "Xəbəri dinlə");
    box.innerHTML = '<p class="dinle-t"></p><p class="dinle-s" role="status"></p><div class="dinle-b"><button type="button" data-d="pp">❚❚ Fasilə</button><button type="button" data-d="next">Növbəti ⏭</button><button type="button" data-d="stop">✕ Bağla</button></div>';
    box.addEventListener("click", e => { const d = e.target.closest?.("[data-d]")?.dataset.d; if (d === "pp") toggle(); if (d === "next") next(); if (d === "stop") stop(); });
    doc.body.append(box);
    return box;
  };
  const status = s => { ui().querySelector(".dinle-s").textContent = s; };
  const ppLabel = () => { ui().querySelector("[data-d=pp]").textContent = playing ? "❚❚ Fasilə" : "▶ Davam"; };
  function speak(id) {
    if (id !== gen) return;
    if (i >= parts.length) { next(true); return; }
    const u = new Utterance(parts[i]);
    u.voice = choice.voice; u.lang = choice.lang; u.rate = choice.az ? 1 : .95;
    u.onend = () => { if (id === gen) { i++; speak(id); } };
    u.onerror = e => { if (id === gen && !/cancel|interrupt/.test(e?.error || "")) { playing = false; ppLabel(); status("Səsli oxuma dayandı. «▶ Davam» ilə yenidən başladın."); } };
    synth.speak(u);
  }
  async function play(a) {
    if (!synth || !Utterance) { ui(); status("Bu brauzer səsli oxumanı dəstəkləmir. Edge və ya Chrome-da açın."); return; }
    gen++; synth.cancel(); cur = a; parts = chunks(textOf(a, decode)); i = 0;
    ui().querySelector(".dinle-t").textContent = decode(a.title || "");
    choice = pickVoice(await voices());
    if (!choice) { playing = false; ppLabel(); status("Bu cihazda Azərbaycan və ya türk səsi yoxdur. Edge brauzerində təbii Azərbaycan səsi var."); return; }
    playing = true; ppLabel();
    const vn = String(choice.voice.name).replace(/^(Microsoft|Google)\s+/, "").replace(/\s+(Online|-).*$/, "");
    status(choice.az ? `Oxunur · səs: ${vn}` : `Azərbaycan səsi yoxdur, türk səsi ilə oxunur (${vn}). Təbii Azərbaycan səsi Edge brauzerindədir.`);
    try { if (nav?.mediaSession) { nav.mediaSession.metadata = new globalThis.MediaMetadata({ title: decode(a.title || ""), artist: "8ULDUZ" }); nav.mediaSession.setActionHandler("nexttrack", () => next()); nav.mediaSession.setActionHandler("pause", toggle); nav.mediaSession.setActionHandler("play", toggle); } } catch {}
    speak(gen);
  }
  function toggle() {
    if (!cur) return;
    if (playing) { synth.pause(); playing = false; } else if (synth.paused) { synth.resume(); playing = true; } else { play(cur); return; }
    ppLabel();
  }
  function next(auto) {
    const all = list().filter(a => (a.lang || "az") === "az");
    const at = all.findIndex(a => a.id === cur?.id), b = all[at + 1];
    if (b) play(b); else { playing = false; ppLabel(); status(auto ? "Xəbərlər bitdi." : "Növbəti xəbər yoxdur."); }
  }
  function stop() { gen++; synth?.cancel(); playing = false; cur = null; box?.remove(); box = null; }
  globalThis.addEventListener?.("pagehide", stop);
  return { play, stop, toggle, next, get playing() { return playing; } };
}
