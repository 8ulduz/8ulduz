// A single spoken request is submitted only after recognition has released the microphone.
export function createVoiceSession({Recognition, lang = 'az-AZ', onStart = () => {}, onTranscript = () => {}, onComplete = () => {}, onError = () => {}, onEnd = () => {}}) {
  let epoch = 0, current = null, active = false, timer = null;
  function cancel() {
    epoch++; clearTimeout(timer);
    const old = current; current = null; active = false;
    try { old?.abort(); } catch {}
    onEnd();
  }
  function stop() { try { current?.stop(); } catch { cancel(); onError('audio-capture'); } }
  function start() {
    if (active) { stop(); return; }
    if (!Recognition) { onError('unsupported'); return; }
    cancel(); const token = epoch;
    let transcript = '', failed = false, finished = false;
    let rec; try { rec = new Recognition(); } catch { onError('audio-capture'); return; }
    current = rec; active = true;
    rec.lang = lang; rec.continuous = false; rec.interimResults = true;
    rec.onstart = () => { if (token === epoch) onStart(); };
    rec.onresult = event => {
      if (token !== epoch || finished || failed) return;
      const segments = Array.from(event.results || []);
      transcript = segments.map(r => r[0]?.transcript || '').join(' ').trim();
      onTranscript(transcript);
      if (segments.length && segments.every(r => r.isFinal !== false)) stop();
    };
    rec.onspeechend = () => { if (token === epoch && !finished) stop(); };
    rec.onerror = event => { if (token !== epoch || finished) return; failed = true; onError(event.error); cancel(); };
    rec.onend = () => {
      if (token !== epoch || finished) return;
      finished = true; clearTimeout(timer); current = null; active = false; onEnd();
      if (!failed && transcript) onComplete(transcript);
      else if (!failed) onError('no-speech');
    };
    try { rec.start(); if (!finished && token === epoch) timer = setTimeout(() => { if (token === epoch && !finished) stop(); }, 15000); }
    catch { active = false; current = null; onEnd(); onError('audio-capture'); }
  }
  return {start, stop, cancel, get active() { return active; }};
}

const VOICE_SEARCH_ERRORS = {'not-allowed': 'Mikrofona icazə yoxdur', 'service-not-allowed': 'Səslə axtarış bağlıdır', 'no-speech': 'Səs eşidilmədi', 'audio-capture': 'Mikrofon tapılmadı', 'network': 'Səs xidmətinə çatmır'};
// Axtarış qutusunun mikrofonu: deyilən söz qutuya yazılır və adi axtarış kimi işləyir.
export function mountVoiceSearch({button, input, Recognition, onDone = () => {}}) {
  if (!Recognition || !button || !input) return null;
  const hint = input.placeholder;
  let before = '', timer = null;
  const make = lang => createVoiceSession({Recognition, lang,
    onStart() { clearTimeout(timer); before = input.value; input.value = ''; input.placeholder = 'Dinləyirəm…'; button.classList.add('on'); button.setAttribute('aria-pressed', 'true'); },
    onTranscript(text) { input.value = text; },
    onComplete(text) {
      input.value = text.replace(/[.!?…]+$/u, '').trim(); input.placeholder = hint;
      input.dispatchEvent(new Event('input', {bubbles: true}));
      onDone();
    },
    onError(code) {
      // Azərbaycan dilini tanımayan cihazda (məsələn, iPhone) komanda adları türkcə də düzgün çıxır.
      if (code === 'language-not-supported' && lang !== 'tr-TR') { session = make('tr-TR'); session.start(); return; }
      input.value = ''; input.placeholder = VOICE_SEARCH_ERRORS[code] || 'Səs tanınmadı';
      clearTimeout(timer); timer = setTimeout(() => { input.placeholder = hint; if (!input.value) input.value = before; }, 4000);
    },
    onEnd() { button.classList.remove('on'); button.setAttribute('aria-pressed', 'false'); },
  });
  let session = make('az-AZ');
  button.hidden = false;
  button.parentElement?.classList.add('has-mic');
  button.addEventListener('click', event => { event.preventDefault(); session.start(); });
  return {get session() { return session; }};
}

