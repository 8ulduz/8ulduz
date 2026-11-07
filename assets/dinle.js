// «Dinlə» (sahib, 2026-11-07: «dinlə funksiyasını mükəmməl şəkildə işə sal»; «istifadə edən üçün çox rahat olsun»).
// Xəbər səhifəsindəki «🔊 Dinlə» bu modulu yalnız basılanda yükləyir (adi açılışa bayt əlavə olunmur — qırmızı xətt 1).
// Oxunan: başlıq + saytdakı xülasə (saytda onsuz da göstərilən mətn; mənbənin tam mətni yayılmır). «Növbəti» lentdəki
// növbəti Azərbaycan dilində xəbərə keçir, xəbər bitəndə özü keçir — radio kimi.
// Səs sırası: 1) xəbərin TAM mətni hazır təbii Azərbaycan səsi ilə (Edge Babək; .github/scripts/ses.py 8ulduz/ses reposuna
// yazır) — hər telefonda eyni, ekran kilidlənəndə də çalır; «Növbəti» əvvəl hazır səsli xəbərlərə keçir; 2) cihazın Azərbaycan səsi (Edge: «Microsoft … Online (Natural)»); 3) türk səsi — ə/x/q
// türkcə yaxın səsə çevrilir ki, düzgün tələffüz olunsun; heç biri yoxdursa açıq izah. Sürət seçimi yadda qalır.

export const AUDIO = "https://raw.githubusercontent.com/8ulduz/ses/main/";

export function textOf(a, decode = s => s) {
  const clean = s => decode(String(s || "")).replace(/<[^>]+>/g, " ").replace(/\s+/g, " ").trim();
  const title = clean(a?.title).replace(/[.!?…]*$/, "");
  const summary = clean(a?.summary);
  return summary && !summary.startsWith(title) ? `${title}. ${summary}` : title + ".";
}

// Türk səsi «ə», «x», «q» hərflərini tanımır (hərf adı deyir və ya buraxır): ən yaxın türk səsinə çevrilir.
export function forTurkish(text) {
  return String(text).replace(/[əƏxXqQ]/g, c => ({ ə: "e", Ə: "E", x: "h", X: "H", q: "g", Q: "G" })[c]);
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

const SILENT = "data:audio/wav;base64,UklGRiQAAABXQVZFZm10IBAAAAABAAEARKwAAIhYAQACABAAZGF0YQAAAAA=";
export const RATES = [1, 1.25, 1.5, 0.85];

const CSS = `
.dinle{position:fixed;left:8px;right:8px;bottom:calc(64px + env(safe-area-inset-bottom));z-index:1100;max-width:560px;margin:0 auto;padding:10px 12px;border:1px solid var(--primary,#fbbf24);border-radius:12px;background:#0f1b33;color:#f8fafc;box-shadow:0 10px 28px #0007;font-size:.9rem}
.dinle-t{display:-webkit-box;-webkit-line-clamp:2;-webkit-box-orient:vertical;overflow:hidden;margin:0 0 6px;font-weight:700;line-height:1.3}
.dinle-s{margin:0 0 8px;color:#94a3b8;font-size:.75rem}
.dinle-b{display:flex;gap:6px;flex-wrap:wrap}
.dinle-b button{min-height:40px;padding:6px 14px;border:1px solid #334155;border-radius:20px;background:#1e293b;color:inherit;font:inherit;font-weight:700;cursor:pointer}
.dinle-b button[data-d=pp]{background:var(--primary,#fbbf24);border-color:transparent;color:#111}
@media(min-width:901px){.dinle{bottom:16px}}
`;

export function createPlayer({ list, decode = s => s, doc = document, synth = globalThis.speechSynthesis, Utterance = globalThis.SpeechSynthesisUtterance,
  nav = globalThis.navigator, fetchFn = globalThis.fetch, AudioCtor = globalThis.Audio, store = globalThis.localStorage }) {
  let box = null, cur = null, parts = [], i = 0, gen = 0, choice = null, playing = false, mode = "", aud = null;
  let rate = Number(store?.getItem?.("dinle-rate")) || 1;
  const files = new Map();  // id -> Promise<blob url | "">
  const voices = () => new Promise(res => {
    const now = synth?.getVoices?.() || [];
    if (now.length) return res(now);
    let done = false; const end = () => { if (!done) { done = true; res(synth?.getVoices?.() || []); } };
    synth?.addEventListener?.("voiceschanged", end, { once: true }); setTimeout(end, 1500);
  });
  // Hazır səs faylı (yoxdursa ""): bir sorğu, 6 saniyə; növbəti xəbərinki əvvəlcədən götürülür ki, ara olmasın.
  // Hazır səslərin siyahısı (index.json): bir sorğu, 10 dəqiqədə bir təzələnir; siyahıda olmayan xəbər üçün sorğu getmir.
  let voiced = null, voicedAt = 0;
  const loadVoiced = async () => {
    if (voiced && Date.now() - voicedAt < 6e5) return voiced;
    try { const r = await fetchFn(`${AUDIO}index.json?t=${Math.floor(Date.now() / 6e5)}`, { signal: AbortSignal.timeout(5000) }); if (r.ok) { voiced = new Set((await r.json()).ids || []); voicedAt = Date.now(); } } catch {}
    return voiced || new Set();
  };
  const audioFor = id => {
    if (!files.has(id)) files.set(id, (async () => {
      if (!fetchFn || !AudioCtor || !/^[0-9a-f]{16}$/.test(String(id || "")) || !(await loadVoiced()).has(id)) return "";
      try {
        const r = await fetchFn(`${AUDIO}${id}.mp3`, { signal: AbortSignal.timeout(6000) });
        if (!r.ok) return "";
        return URL.createObjectURL(new Blob([await r.arrayBuffer()], { type: "audio/mpeg" }));
      } catch { return ""; }
    })());
    return files.get(id);
  };
  const azList = () => list().filter(a => (a.lang || "az") === "az");
  // Növbəti: əvvəl hazır tam səsi olan xəbər (maşında dinləyən ardıcıl təbii səs eşitsin), sonra qalanlar.
  const after = a => { const all = azList(), at = all.findIndex(x => x.id === a?.id), rest = all.slice(at + 1); return rest.find(x => voiced?.has(x.id)) || rest[0]; };
  const ui = () => {
    if (box) return box;
    if (!doc.getElementById("dinle-style")) { const st = doc.createElement("style"); st.id = "dinle-style"; st.textContent = CSS; doc.head.append(st); }
    box = doc.createElement("section");
    box.className = "dinle"; box.setAttribute("aria-label", "Xəbəri dinlə");
    box.innerHTML = '<p class="dinle-t"></p><p class="dinle-s" role="status"></p><div class="dinle-b"><button type="button" data-d="pp">❚❚ Fasilə</button><button type="button" data-d="next">Növbəti ⏭</button><button type="button" data-d="rate" aria-label="Oxuma sürəti"></button><button type="button" data-d="stop">✕ Bağla</button></div>';
    box.addEventListener("click", e => { const d = e.target.closest?.("[data-d]")?.dataset.d; if (d === "pp") toggle(); if (d === "next") next(); if (d === "rate") setRate(); if (d === "stop") stop(); });
    doc.body.append(box);
    rateLabel();
    return box;
  };
  const status = s => { ui().querySelector(".dinle-s").textContent = s; };
  const ppLabel = () => { ui().querySelector("[data-d=pp]").textContent = playing ? "❚❚ Fasilə" : "▶ Davam"; };
  function rateLabel() { const b = box?.querySelector("[data-d=rate]"); if (b) b.textContent = `${String(rate).replace(".", ",")}×`; }
  function setRate() {
    rate = RATES[(RATES.indexOf(rate) + 1) % RATES.length];
    try { store?.setItem?.("dinle-rate", String(rate)); } catch {}
    rateLabel();
    if (mode === "file") aud.playbackRate = rate;
    else if (mode === "tts" && playing) { const id = ++gen; synth.cancel(); speak(id); }  // cari hissə yeni sürətlə təkrarlanır
  }
  function speak(id) {
    if (id !== gen) return;
    if (i >= parts.length) { next(true); return; }
    const u = new Utterance(choice.az ? parts[i] : forTurkish(parts[i]));
    u.voice = choice.voice; u.lang = choice.lang; u.rate = rate * (choice.az ? 1 : .95);
    u.onend = () => { if (id === gen) { i++; speak(id); } };
    u.onerror = e => { if (id === gen && !/cancel|interrupt/.test(e?.error || "")) { playing = false; ppLabel(); status("Səsli oxuma dayandı. «▶ Davam» ilə yenidən başladın."); } };
    synth.speak(u);
  }
  function media(a) {
    try {
      if (!nav?.mediaSession) return;
      nav.mediaSession.metadata = new globalThis.MediaMetadata({ title: decode(a.title || ""), artist: "8ULDUZ" });
      nav.mediaSession.setActionHandler("nexttrack", () => next());
      nav.mediaSession.setActionHandler("pause", toggle); nav.mediaSession.setActionHandler("play", toggle);
    } catch {}
  }
  function halt() { gen++; synth?.cancel?.(); if (aud) { aud.onended = aud.onerror = null; aud.pause(); } mode = mode === "file" ? "" : mode; }
  // Telefon (xüsusən iPhone) səsi yalnız toxunuşla başladır: element toxunuş anında açılır və bütün xəbərlər üçün o işlədilir.
  const unlock = () => { if (aud || !AudioCtor) return; try { aud = new AudioCtor(); aud.src = SILENT; aud.play()?.catch?.(() => {}); } catch { aud = null; } };
  async function play(a) {
    unlock(); halt(); const id = gen; cur = a; mode = ""; parts = []; i = 0;
    ui().querySelector(".dinle-t").textContent = decode(a.title || "");
    status("Hazırlanır…");
    const url = await audioFor(a.id);
    if (id !== gen) return;
    if (url) {
      mode = "file"; aud.src = url; aud.playbackRate = rate;
      aud.onended = () => { if (id === gen) next(true); };
      aud.onerror = () => { if (id === gen) { files.set(a.id, Promise.resolve("")); play(a); } };  // fayl xarabdırsa cihazın səsi
      playing = true; ppLabel(); media(a);
      status("Oxunur · tam xəbər, təbii Azərbaycan səsi");
      try { await aud.play(); } catch { playing = false; ppLabel(); status("Başlatmaq üçün «▶ Davam» basın."); }
    } else {
      if (!synth || !Utterance) { playing = false; ppLabel(); status("Bu xəbərin hazır səsi yoxdur, bu brauzer də səsli oxumanı dəstəkləmir."); return; }
      choice = pickVoice(await voices());
      if (id !== gen) return;
      if (!choice) { playing = false; ppLabel(); status("Bu xəbərin hazır səsi yoxdur, cihazda da Azərbaycan və ya türk səsi tapılmadı."); return; }
      mode = "tts"; parts = chunks(textOf(a, decode)); playing = true; ppLabel(); media(a);
      const vn = String(choice.voice.name).replace(/^(Microsoft|Google)\s+/, "").replace(/\s+(Online|-).*$/, "");
      status(choice.az ? `Oxunur · səs: ${vn}` : `Oxunur · türk səsi (${vn}) — bu xəbərin hazır səsi hələ yoxdur`);
      speak(id);
    }
    const n = after(a); if (n) audioFor(n.id);  // növbəti xəbərin səsi arxada hazırlanır
  }
  function toggle() {
    if (!cur) return;
    if (mode === "file") { if (playing) aud.pause(); else aud.play().catch(() => {}); playing = !playing; }
    else if (playing) { synth.pause(); playing = false; }
    else if (synth?.paused) { synth.resume(); playing = true; }
    else { play(cur); return; }
    ppLabel();
  }
  function next(auto) {
    const b = after(cur);
    if (b) play(b); else { halt(); playing = false; ppLabel(); status(auto ? "Xəbərlər bitdi." : "Növbəti xəbər yoxdur."); }
  }
  function stop() {
    halt(); aud = null; playing = false; cur = null; box?.remove(); box = null;
    for (const p of files.values()) p.then(u => u && URL.revokeObjectURL(u));
    files.clear();
  }
  globalThis.addEventListener?.("pagehide", stop);
  return { play, stop, toggle, next, get playing() { return playing; }, get mode() { return mode; } };
}
