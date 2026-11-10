// «Dinlə» (sahib, 2026-11-07: «dinlə funksiyasını mükəmməl şəkildə işə sal»; «istifadə edən üçün çox rahat olsun»).
// Kartdakı «Dinlə» bu modulu yalnız basılanda yükləyir (adi açılışa bayt əlavə olunmur — qırmızı xətt 1).
// Basılan xəbər oxunur və bitəndə dayanır (sahib, 2026-11-08: «o bitəndə dayanmır … sonra digərinə keçir. bunu düzəlt»);
// növbəti xəbərə yalnız kilid ekranındakı «Növbəti» düyməsi ilə keçilir.
// Səs sırası: 1) xəbərin TAM mətni hazır təbii Azərbaycan səsi ilə (Edge Babək; .github/scripts/ses.py 8ulduz/ses reposuna
// yazır) — hər telefonda eyni, ekran kilidlənəndə də çalır; «Növbəti» əvvəl hazır səsli xəbərlərə keçir; 2) cihazın Azərbaycan səsi (Edge: «Microsoft … Online (Natural)»); 3) türk səsi — ə/x/q
// türkcə yaxın səsə çevrilir ki, düzgün tələffüz olunsun; heç biri yoxdursa düymədə qısa izah.

export const AUDIO = "https://raw.githubusercontent.com/8ulduz/ses/main/";

export function textOf(a, decode = s => s) {
  const clean = s => decode(String(s || "")).replace(/<[^>]+>/g, " ").replace(/\s+/g, " ").trim();
  // «- Video», «(FOTO)» kimi nişanlar oxunmur (sahib, 2026-11-10; ses.py spoken_title ilə eyni).
  const title = clean(a?.title).replace(/\s*[(\[]\s*(?:foto|v[iİı]deo)(?:lar)?(?:\s*[,+/]\s*(?:foto|v[iİı]deo)(?:lar)?)*\s*[)\]]/gi, "").replace(/\s*(?:[-–—|:+]\s*)?(?:foto|v[iİı]deo)(?:lar)?(?:\s*[/+]\s*(?:foto|v[iİı]deo))?\s*$/i, "").replace(/^\s*(?:foto|v[iİı]deo)\s*[:|–—-]\s*/i, "").replace(/[.!?…]*$/, "");
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
// Xəbər başqa dildədirsə (sahib, 2026-11-08: «dinlə düyməsi dillər üzrə dəyişmir») o dilin səsi: ingilis xəbəri ingilis səsi ilə.
const LOCALE = { en: "en-US", ru: "ru-RU", tr: "tr-TR" };
export const langOf = a => a?.lang || "az";
export function pickVoice(voices, want = "az") {
  const score = v => (/natural|online|neural/i.test(v.name) ? 2 : 0) + (v.localService ? 0 : 1);
  const best = re => voices.filter(v => re.test(v.lang || "")).sort((x, y) => score(y) - score(x) || String(x.name).localeCompare(String(y.name)))[0];
  if (want !== "az" && /^[a-z]{2,3}$/.test(want)) { const own = best(new RegExp(`^${want}(?:[-_]|$)`, "i")); return own ? { voice: own, lang: own.lang || LOCALE[want] || want, az: false, own: true } : null; }
  const az = best(/^az(?:[-_]|$)/i);
  if (az) return { voice: az, lang: "az-AZ", az: true };
  const tr = best(/^tr(?:[-_]|$)/i);
  return tr ? { voice: tr, lang: "tr-TR", az: false } : null;
}

const WAIT = "Səs hazırlanır…";
const SAYS = { az: " xəbər verir. ", en: " reports. ", ru: " сообщает. ", tr: " bildiriyor. " };
const SILENT = "data:audio/wav;base64,UklGRiQAAABXQVZFZm10IBAAAAABAAEARKwAAIhYAQACABAAZGF0YQAAAAA=";

// Ayrıca pəncərə yoxdur (sahib, 2026-11-08: «əlavə pəncərəyə nə ehtiyac var? təkrar basanda dayansın»): vəziyyət kartın öz
// düyməsindədir — onState({ id, playing, msg }) ilə sayt «Dinlə» ↔ «■ Dayan» yazır. Xəbər bitəndə növbətiyə özü keçir;
// kilid ekranında fasilə/növbəti (Media Session).
export function createPlayer({ list, decode = s => s, onState = () => {}, synth = globalThis.speechSynthesis, Utterance = globalThis.SpeechSynthesisUtterance,
  nav = globalThis.navigator, fetchFn = globalThis.fetch, AudioCtor = globalThis.Audio, worker = globalThis.SITE_CONFIG?.sesWorker, server = globalThis.SITE_CONFIG?.sesServer }) {
  let cur = null, parts = [], i = 0, gen = 0, choice = null, playing = false, mode = "", aud = null;
  const files = new Map();  // id -> Promise<blob url | "">
  const emit = msg => onState({ id: cur?.id, playing, msg });
  const voices = () => new Promise(res => {
    const now = synth?.getVoices?.() || [];
    if (now.length) return res(now);
    let done = false; const end = () => { if (!done) { done = true; res(synth?.getVoices?.() || []); } };
    synth?.addEventListener?.("voiceschanged", end, { once: true }); setTimeout(end, 1500);
  });
  // Hazır səslərin siyahısı (index.json): bir sorğu, dəqiqədə bir təzələnir (yeni xəbərin səsi 1–2 dəqiqəyə hazır olur); siyahıda olmayan xəbər üçün sorğu getmir.
  let voiced = null, voicedAt = 0;
  const loadVoiced = async () => {
    if (voiced && Date.now() - voicedAt < 6e4) return voiced;
    try { const r = await fetchFn(`${AUDIO}index.json?t=${Math.floor(Date.now() / 6e4)}`, { signal: AbortSignal.timeout(8000) }); if (r.ok) { voiced = new Set((await r.json()).ids || []); voicedAt = Date.now(); } } catch {}
    return voiced || new Set();
  };
  // Hazır səs faylı (yoxdursa ""): bir sorğu, zəif internetdə də 20 saniyə gözlənir; növbəti xəbərinki əvvəlcədən götürülür.
  const audioFor = id => {
    if (!files.has(id)) files.set(id, (async () => {
      if (!fetchFn || !AudioCtor || !/^[0-9a-f]{16}$/.test(String(id || "")) || !(await loadVoiced()).has(id)) return "";
      try {
        const r = await fetchFn(`${AUDIO}${id}.mp3`, { signal: AbortSignal.timeout(20000) });
        if (!r.ok) return "";
        return URL.createObjectURL(new Blob([await r.arrayBuffer()], { type: "audio/mpeg" }));
      } catch { return ""; }
    })());
    return files.get(id);
  };
  // Hazır səs yoxdursa xəbərin TAM mətni mətn serverindən (.github/ses-worker/worker.js) — basılan anda, cihazın səsi ilə.
  // Server yoxdursa və ya cavab vermirsə saytdakı başlıq + xülasə oxunur.
  const fullText = async a => {
    if (worker && String(a?.sourceUrl).startsWith("https://")) try {
      const r = await fetchFn(`${worker}?u=${encodeURIComponent(a.sourceUrl)}`, { signal: AbortSignal.timeout(7000) });
      const t = r.ok ? String((await r.json()).text || "") : "";
      if (t.length > 200) { const title = textOf({ title: a.title }, decode).replace(/[.]$/, ""); return `${title}. ${a.source ? a.source + (SAYS[langOf(a)] || ". ") : ""}${t.startsWith(title) ? t.slice(title.length) : t}`; }
    } catch {}
    return textOf(a, decode);
  };
  const sameLang = a => list().filter(x => langOf(x) === langOf(a));
  // Növbəti: əvvəl hazır tam səsi olan xəbər (maşında dinləyən ardıcıl təbii səs eşitsin), sonra qalanlar.
  const after = a => { const all = sameLang(a), at = all.findIndex(x => x.id === a?.id), rest = all.slice(at + 1); return rest.find(x => voiced?.has(x.id)) || rest[0]; };
  function speak(id) {
    if (id !== gen) return;
    if (i >= parts.length) { stop(); return; }   // xəbər bitdi: dayanır
    const own = choice.az || choice.own;   // türk hərfinə çevirmə yalnız Azərbaycan mətni türk səsi ilə oxunanda
    const u = new Utterance(own ? parts[i] : forTurkish(parts[i]));
    u.voice = choice.voice; u.lang = choice.lang; u.rate = own ? 1 : .95;
    u.onend = () => { if (id === gen) { i++; speak(id); } };
    u.onerror = e => { if (id === gen && !/cancel|interrupt/.test(e?.error || "")) { playing = false; emit("Səsli oxuma dayandı"); } };
    synth.speak(u);
  }
  function media(a) {
    try {
      if (!nav?.mediaSession) return;
      nav.mediaSession.metadata = new globalThis.MediaMetadata({ title: decode(a.title || ""), artist: "8ULDUZ" });
      nav.mediaSession.setActionHandler("nexttrack", () => next());
      nav.mediaSession.setActionHandler("pause", toggle); nav.mediaSession.setActionHandler("play", toggle);
      nav.mediaSession.setActionHandler("stop", stop);
    } catch {}
  }
  function halt() { gen++; synth?.cancel?.(); if (aud) { aud.onended = aud.onerror = null; aud.pause(); } mode = mode === "file" ? "" : mode; }
  // Telefon (xüsusən iPhone) səsi yalnız toxunuşla başladır: element toxunuş anında açılır və bütün xəbərlər üçün o işlədilir.
  const unlock = () => { if (aud || !AudioCtor) return; try { aud = new AudioCtor(); aud.src = SILENT; aud.play()?.catch?.(() => {}); } catch { aud = null; } };
  async function play(a, tries = 0) {
    unlock(); halt(); const id = gen; cur = a; mode = ""; parts = []; i = 0;
    playing = true; emit(tries > 0 ? WAIT : undefined);  // düymə dərhal «■ Bitir» olur; gözləmədə «Səs hazırlanır…» qalır
    // «dinle» serveri (Cloudflare, .github/ses-worker): hazır tam səs və ya Azure-un rəsmi Babək səsi, basılan anda.
    // Səs hələ hazır deyilsə (server 503): cihazda Azərbaycan səsi varsa (kompüterdə Edge: Babək) gözləmədən o oxuyur;
    // yoxdursa düymə «Səs hazırlanır…» yazısını saxlayır (sahib, 2026-11-08: «səs hazırlanır yazır qayıdır dinləyə»),
    // 10 saniyədən bir yenidən soruşur (4 dəqiqəyədək), sonra cihazın səsi. Ünvan toxunuş anında verilir (iPhone).
    // Babək serveri və hazır səslər yalnız Azərbaycan dilindədir: başqa dildə xəbəri cihazın o dildəki səsi oxuyur.
    const az = langOf(a) === "az";
    if (az && server && tries >= 0 && String(a?.sourceUrl).startsWith("https://")) {
      const e = encodeURIComponent, src = `${server}?u=${e(a.sourceUrl)}&id=${e(a.id || "")}&t=${e(decode(a.title || ""))}&s=${e(a.source || "")}`;
      mode = "file"; aud.src = src; media(a);
      const mine = () => id === gen && aud.currentSrc === src;
      aud.onended = () => { if (mine()) stop(); };   // xəbər bitdi: dayanır, növbətiyə keçmir
      aud.onerror = () => {
        if (!mine()) return;
        voices().then(vs => {
          if (id !== gen) return;
          if (pickVoice(vs)?.az || tries >= 24) play(a, -1);
          else { emit(WAIT); setTimeout(() => { if (id === gen) play(a, tries + 1); }, 1e4); }
        });
      };
      aud.play()?.catch?.(() => { if (id === gen && aud.currentSrc === src && !aud.error) { playing = false; emit("Başlatmaq üçün yenidən basın"); } });
      return;
    }
    const url = az ? await audioFor(a.id) : "";
    if (id !== gen) return;
    if (url) {
      mode = "file"; aud.src = url;
      // Yalnız bu faylın hadisəsi sayılır: toxunuşdakı səssiz klipin gecikən «bitdi» siqnalı xəbəri bitmiş saymasın.
      const mine = () => id === gen && aud.currentSrc === url;
      aud.onended = () => { if (mine()) stop(); };
      aud.onerror = () => { if (mine()) { files.set(a.id, Promise.resolve("")); play(a); } };  // fayl xarabdırsa cihazın səsi
      media(a);
      try { await aud.play(); } catch { if (id === gen) { playing = false; emit("Başlatmaq üçün yenidən basın"); } }
    } else {
      if (!synth || !Utterance) { playing = false; emit("Bu brauzerdə səsli oxuma yoxdur"); return; }
      const [vs, text] = await Promise.all([voices(), fullText(a)]);
      choice = pickVoice(vs, langOf(a));
      if (id !== gen) return;
      if (!choice) { playing = false; emit(az ? "Cihazda Azərbaycan və ya türk səsi yoxdur" : "Cihazda bu dilin səsi yoxdur"); return; }
      mode = "tts"; parts = chunks(text); media(a);
      speak(id);
    }
  }
  function toggle() {
    if (!cur) return;
    if (mode === "file") { if (playing) aud.pause(); else aud.play().catch(() => {}); playing = !playing; }
    else if (playing) { synth.pause(); playing = false; }
    else if (synth?.paused) { synth.resume(); playing = true; }
    else { play(cur); return; }
    emit();
  }
  function next() {
    const b = after(cur);
    if (b) play(b); else stop();
  }
  function stop() {
    halt(); aud?.pause?.(); playing = false; emit(); cur = null;
    for (const p of files.values()) p.then(u => u && URL.revokeObjectURL(u));
    files.clear();
  }
  globalThis.addEventListener?.("pagehide", stop);
  return { play, stop, toggle, next, get playing() { return playing; }, get mode() { return mode; }, get id() { return cur?.id; } };
}
