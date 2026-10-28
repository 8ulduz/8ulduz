// First version: deterministic commands over published feeds. No API keys in the browser.
export const fold = s => String(s || '').toLocaleLowerCase('az').normalize('NFD').replace(/[\u0300-\u036f]/g, '').replace(/[əıöüğşç]/g, c => ({ə:'e',ı:'i',ö:'o',ü:'u',ğ:'g',ş:'s',ç:'c'}[c])).replace(/[^\p{L}\p{N}\s]/gu, ' ').replace(/\s+/g, ' ').trim();
const escape = s => String(s ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const safeLink = u => /^(https?:\/\/|#\/)/i.test(String(u || '')) ? String(u) : '#/';
const newest = list => [...list].sort((a,b)=>new Date(b.publishedAt)-new Date(a.publishedAt));
const within = (stamp,hours) => {const age=Date.now()-new Date(stamp).getTime();return Number.isFinite(age)&&age>=-300000&&age<hours*3600000;};
const dateLabel = stamp => {const d=new Date(stamp);return Number.isNaN(d.getTime())?'tarix verilməyib':d.toLocaleString('az-AZ',{timeZone:'Asia/Baku',day:'numeric',month:'long',hour:'2-digit',minute:'2-digit'});};
const teamAliases = name => {
  const n=fold(name); const aliases={fenerbahce:['fenerbaxca','fenerbahce'],qarabag:['qarabag','qarabagh'],galatasaray:['qalatasaray','galatasaray'],besiktas:['besiktas','besiktash'],neftci:['neftci','neftchi']};
  return [...new Set([n,...Object.entries(aliases).filter(([key])=>n.includes(key)).flatMap(([,v])=>v)])];
};
export function parseCommand(text, snapshot = {}, context = {}) {
  const q=fold(text);
  if (/^(dayandir|sus|stop|sesi kes|oxumagi dayandir)$/.test(q)) return {type:'stop'};
  if (/^(davam et|davam|oxumaga davam et)$/.test(q)) return {type:'resume'};
  if (/^(novbeti|novbetini oxu|novbeti xeber|novbeti xeberi oxu)$/.test(q)) return {type:'next'};
  if (/^(bu xeberi ac|menbeni ac|xeberi ac)$/.test(q)) return {type:'open'};
  if (/basqa menbe|diger menbe/.test(q)) return {type:'alternatives'};
  const city=(snapshot.cities||[]).find(c=>q.split(' ').some(w=>w.startsWith(fold(c[0]))));
  const day=q.includes('sabah')?1:0;
  const unsupportedDate=/dunen|birisigun|gele[cn] hefte|gelen ay|[0-9]{1,2} (yanvar|fevral|mart|aprel|may|iyun|iyul|avqust|sentyabr|oktyabr|noyabr|dekabr)/.test(q);
  const rawPlace=(q.match(/^(.+?)\s+(?:hava|namaz)/)?.[1]||'').replace(/\b(?:sabah|bu gun|bugun|indi|mene)\b/g,'').trim();
  const selectedCity=city?.[0]||rawPlace||context.city||'Bakı';
  if (/namaz|subh|zohr|esr|megrib|isa vaxt/.test(q)) return {type:'prayer',city:selectedCity,day,unsupportedDate};
  if (/\bhava|temperatur|yagis|kulek/.test(q)) return {type:'weather',city:selectedCity,day,unsupportedDate};
  if (/tixac|yol veziyyet|yollar nece/.test(q)) return {type:'traffic'};
  const wantsStats=/son oyun|son matc|nece bit|netice|nece xali|nece xal|necenci|turnir|cedvel|hesab/.test(q);
  const teams=(snapshot.leagues||[]).flatMap(l=>(l.table||[]).map(t=>({team:t,league:l})));
  const found=teams.filter(x=>teamAliases(x.team.team).some(a=>a.length>2&&q.includes(a))).sort((a,b)=>b.team.team.length-a.team.team.length)[0];
  if(wantsStats) return {type:'sport',name:found?.team.team||(/^(nece|necenci|son oyun|son matc|hesab|netice)/.test(q)?context.team:null)||null,query:q};
  const category=(snapshot.categories||[]).find(c=>q.includes(fold(c.label))||q.includes(fold(c.slug)));
  const sources=[...new Set((snapshot.articles||[]).flatMap(a=>[a.source,...(a.alts||[]).map(x=>x.source)]).filter(Boolean))];
  const source=sources.sort((a,b)=>b.length-a.length).find(s=>{const n=fold(s).replace(/\baz\b/g,'').trim();return n.length>2&&q.includes(n);});
  let topic=q;
  for(const label of [category?.label,category?.slug,source].filter(Boolean))topic=topic.replace(new RegExp('\\b'+fold(label)+'(?:in|nin|un|nun|dan|den)?\\b','g'),' ');
  topic=topic.replace(/\b(?:haqqinda|barede|uzre|oxu|de|goster|xeberleri|xeberlerini|xeberler|xeber|basliqlari|basliqlarini|son|yeni|en|mene|zehmet|olmasa|bugun|butun)\b/g,' ').replace(/\s+/g,' ').trim();
  if(category||source||/xeber|oxu|haqqinda/.test(q))return {type:'news',category:category?.slug,source,topic};
  return {type:'help'};
}
export async function answerCommand(text,snapshot,context={},providers={}) {
  const intent=parseCommand(text,snapshot,context);
  const reply=(text,items=[],extra={})=>({text,items,...extra});
  if(['stop','resume','next','open','alternatives'].includes(intent.type))return {control:intent.type};
  if(intent.type==='news') {
    let list=newest((snapshot.articles||[]).filter(a=>!a.lang||a.lang==='az'));
    if(intent.category)list=list.filter(a=>a.category===intent.category);
    if(intent.source)list=list.filter(a=>[a.source,...(a.alts||[]).map(x=>x.source)].some(s=>fold(s)===fold(intent.source))).map(a=>{const alt=(a.alts||[]).find(x=>fold(x.source)===fold(intent.source));return fold(a.source)===fold(intent.source)?a:{...a,...alt,title:a.title,alts:[{source:a.source,sourceUrl:a.sourceUrl,publishedAt:a.publishedAt},...(a.alts||[]).filter(x=>x!==alt)]};});
    const words=intent.topic.split(' ').filter(w=>w.length>1);
    if(words.length)list=list.filter(a=>words.every(w=>fold(a.title).includes(w)));
    const selected=list.slice(0,5);
    const stamp=snapshot.newsAt;
    const note=stamp?` Lent: ${dateLabel(stamp)}.${within(stamp,1)?'':' Məlumat köhnəlmiş ola bilər.'}`:'';
    return selected.length?reply(`${intent.source?intent.source+' — ':''}${selected.length} xəbər başlığı.${note}`,selected,{readNews:true}):reply('Bu sorğu üzrə cari lentdə xəbər tapılmadı. Başqa ad, mənbə və ya bölmə ilə sınayın.');
  }
  if(intent.type==='traffic') {
    const list=(snapshot.road||[]).filter(a=>within(a.publishedAt,2)).slice(0,5);
    return reply('Küçələr üzrə canlı tıxac ölçülərinə çıxışım yoxdur. '+(list.length?'Son 2 saatda dərc edilmiş yol xəbərləri:':'Son 2 saatda uyğun yol xəbəri tapılmadı. Bu, yollarda tıxac olmadığı demək deyil.'),list,{links:[{title:'Canlı tıxac xəritəsi',url:'#/tixac'}],readNews:!!list.length});
  }
  if(intent.type==='sport') {
    if(!intent.name)return reply('Hansı komandanı nəzərdə tutursunuz? Məsələn: Fənərbaxçanın neçə xalı var?');
    context.team=intent.name;
    const matches=(snapshot.leagues||[]).filter(l=>(l.table||[]).some(t=>t.team===intent.name));
    const league=matches[0],row=league?.table.find(t=>t.team===intent.name);
    if(!row)return reply(`${intent.name} üçün cari cədvəl məlumatı tapılmadı.`);
    const stamp=league.updatedAt||snapshot.sportsAt;
    const ageNote=stamp?` Məlumat: ${dateLabel(stamp)}.${within(stamp,24)?'':' Köhnəlmiş ola bilər.'}`:' Yenilənmə vaxtı göstərilməyib; cari vəziyyət təsdiqlənmir.';
    const standing=row.pts!=null?`${row.team}: ${league.league}, ${row.pos}-ci yer, ${row.pts} xal.`:`${row.team}: ${row.pos}-ci yer, ${row.w} qələbə, ${row.l} məğlubiyyət.`;
    const wantsLast=/son oyun|son matc|nece bit|hesab|netice/.test(intent.query);
    if(!wantsLast)return reply(standing+ageNote,[],{links:[{title:league.source||'Turnir cədvəli',url:league.link||'https://www.espn.com/'}]});
    const games=(league.results||[]).filter(g=>g.played&&[g.home,g.away].some(n=>teamAliases(n).some(a=>teamAliases(row.team).includes(a)))&&new Date(g.date).getTime()<=Date.now()).sort((a,b)=>new Date(b.date)-new Date(a.date));
    const game=games[0];
    return reply((game?`Məlumatdakı son tamamlanmış oyun: ${game.home} ${game.hs} — ${game.as} ${game.away}. Tarix: ${dateLabel(game.date)}. `:'Bu komandanın son oyununun təsdiqlənmiş hesabı hazırkı məlumatda yoxdur. ')+standing+ageNote,[],{links:[{title:league.source||'İdman mənbəyi',url:league.link||'https://www.espn.com/'}]});
  }
  if(intent.type==='weather'||intent.type==='prayer') {
    if(intent.unsupportedDate)return reply('İlk versiyada bu gün və sabah üçün məlumat verə bilirəm.');
    context.city=intent.city;
    const city=(snapshot.cities||[]).find(c=>c[0]===intent.city);
    if(!city)return reply('Bu şəhər dəstəklənmir. Bakı, Gəncə və ya Azərbaycanın başqa şəhərini deyin.');
    const provider=providers[intent.type];
    if(!provider)return reply('Məlumat xidməti hazırda əlçatan deyil.');
    try {return await provider(city,intent.day);}catch {return reply('Məlumatı indi əldə etmək mümkün olmadı. Bir az sonra yenidən sınayın.');}
  }
  return reply('Bölmə, mənbə və şəxs üzrə xəbər başlıqlarını, hava və namaz vaxtlarını soruşa bilərsiniz. Məsələn: “Təhsil xəbərlərini oxu”, “AZƏRTAC xəbərlərini oxu”, “Arda Gülər haqqında xəbərləri oxu”, “Gəncədə hava necədir?”, “Fənərbaxçanın neçə xalı var?”');
}
async function getJSON(url) {const r=await fetch(url,{signal:AbortSignal.timeout(12000)});if(!r.ok)throw Error('HTTP '+r.status);return r.json();}
function bakuDate(day=0){const parts=new Intl.DateTimeFormat('en-CA',{timeZone:'Asia/Baku',year:'numeric',month:'2-digit',day:'2-digit'}).formatToParts(new Date());const p=Object.fromEntries(parts.map(x=>[x.type,x.value]));const d=new Date(`${p.year}-${p.month}-${p.day}T12:00:00+04:00`);d.setUTCDate(d.getUTCDate()+day);return d.toISOString().slice(0,10);}
export function createProviders(wxCode) {
  return {
    async weather(city,day) {
      const d=await getJSON(`https://api.open-meteo.com/v1/forecast?latitude=${city[1]}&longitude=${city[2]}&current=temperature_2m,weather_code,wind_speed_10m&daily=temperature_2m_max,temperature_2m_min,weather_code,precipitation_probability_max&timezone=Asia%2FBaku&forecast_days=2`);
      let text;
      if(day){const x=d.daily;if(!Number.isFinite(x?.temperature_2m_max?.[1]))throw Error('missing');text=`${city[0]}, sabah ${x.time[1]}: ${wxCode(x.weather_code[1])[0]}, ${Math.round(x.temperature_2m_min[1])}–${Math.round(x.temperature_2m_max[1])} dərəcə. Yağıntı ehtimalı ${x.precipitation_probability_max[1]} faiz.`;}
      else{const x=d.current;if(!Number.isFinite(x?.temperature_2m))throw Error('missing');text=`${city[0]}: ${wxCode(x.weather_code)[0]}, ${Math.round(x.temperature_2m)} dərəcə. Külək ${Math.round(x.wind_speed_10m)} kilometr/saat. Məlumat: ${x.time.replace('T',' ')}, Bakı vaxtı.`;}
      return {text,items:[],links:[{title:'Open-Meteo',url:'https://open-meteo.com/'}]};
    },
    async prayer(city,day) {
      const date=bakuDate(day),[y,m,d]=date.split('-');
      const data=await getJSON(`https://api.aladhan.com/v1/timings/${d}-${m}-${y}?latitude=${city[1]}&longitude=${city[2]}&method=13&timezonestring=Asia%2FBaku`);
      const times=data.data?.timings;if(!times?.Fajr)throw Error('missing');
      const labels=[['Fajr','Sübh'],['Sunrise','Günəş'],['Dhuhr','Zöhr'],['Asr','Əsr'],['Maghrib','Məğrib'],['Isha','İşa']];
      return {text:`${city[0]}, ${date}, ${day?'sabahın':'bu günün'} namaz vaxtları: `+labels.map(([key,label])=>`${label} ${times[key]?.split(' ')[0]||'verilməyib'}`).join('. ')+'. Hesablama: AlAdhan, 13-cü metod, Bakı saat qurşağı. Yerli təqvimlə fərqlənə bilər.',items:[],links:[{title:'AlAdhan — vaxtların mənbəyi',url:'https://aladhan.com/'}]};
    }
  };
}
export function selectReadingVoice(voices, selected = 'auto') {
  if (selected === 'off') return null;
  return (selected !== 'auto' && voices.find(v => v.voiceURI === selected)) ||
    voices.find(v => /^az(?:-|$)/i.test(v.lang)) || null;
}

// A single spoken request is submitted only after recognition has released the microphone.
export function createVoiceSession({Recognition, onStart = () => {}, onTranscript = () => {}, onComplete = () => {}, onError = () => {}, onEnd = () => {}}) {
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
    rec.lang = 'az-AZ'; rec.continuous = false; rec.interimResults = true;
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

export function mountAssistant({getSnapshot,wxCode}) {
  if(document.querySelector('#voice-assistant'))return;
  const root=document.createElement('div');root.id='voice-assistant';
  root.innerHTML=`<button class="assistant-launch" type="button" aria-expanded="false" aria-controls="assistant-panel">🎙 Köməkçi</button><section id="assistant-panel" class="assistant-panel" role="dialog" aria-label="8ULDUZ səsli köməkçisi" hidden><div class="assistant-head"><b>8ULDUZ köməkçi · pulsuz</b><button type="button" data-assistant="close" aria-label="Köməkçini bağla">✕</button></div><p class="assistant-intro">Danışın və ya yazın. Cavab pulsuz göstərilir; cihazda Azərbaycan səsi varsa oxunur.</p><form class="assistant-form"><label for="assistant-query">Nə bilmək istəyirsiniz?</label><div><input id="assistant-query" maxlength="240" autocomplete="off" placeholder="Təhsil xəbərlərini oxu"><button type="submit">Göndər</button></div></form><div class="assistant-examples"><button type="button" data-example="Son xəbərləri oxu">Son xəbərlər</button><button type="button" data-example="AZƏRTAC xəbərlərini oxu">AZƏRTAC</button><button type="button" data-example="Bakıda hava necədir?">Hava</button><button type="button" data-example="Namaz vaxtlarını de">Namaz</button><button type="button" data-example="Tıxac barədə de">Tıxac</button><button type="button" data-example="Fənərbaxçanın neçə xalı var?">İdman</button></div><div class="assistant-tools"><button type="button" data-assistant="mic">🎤 Danış</button><button type="button" data-assistant="stop">Dayandır</button><button type="button" data-assistant="resume">Davam et</button><button type="button" data-assistant="next">Növbəti</button></div><label class="assistant-voice">Oxuma səsi <select aria-label="Oxuma səsi"><option value="auto">Azərbaycan dili — cihazda varsa</option><option value="off">Səssiz — yalnız mətn</option></select></label><p class="assistant-status" role="status"></p><div class="assistant-answer" aria-live="polite"></div><p class="assistant-privacy">Mikrofon yalnız “Köməkçi” və ya “Danış” düyməsinə toxunanda açılır. Səs tanıma brauzerin xidmətinə göndərilə bilər. Söhbət saytda saxlanmır.</p></section>`;
  document.body.append(root);
  const panel=root.querySelector('.assistant-panel'),input=root.querySelector('input'),output=root.querySelector('.assistant-answer'),status=root.querySelector('.assistant-status'),voiceSelect=root.querySelector('select'),launcher=root.querySelector('.assistant-launch');
  const context = {};
  let result = null, index = 0, request = 0, utterance = null, readToken = 0;
  const synth = window.speechSynthesis;
  const providers = createProviders(wxCode);
  const micButton = root.querySelector('[data-assistant="mic"]');
  const voices = () => synth?.getVoices() || [];
  function populateVoices() {
    const previous = voiceSelect.value;
    voiceSelect.innerHTML = '<option value="auto">Azərbaycan dili — cihazda varsa</option><option value="off">Səssiz — yalnız mətn</option>' + voices().map(v => `<option value="${escape(v.voiceURI)}">${escape(v.name)} (${escape(v.lang)})</option>`).join('');
    voiceSelect.value = [...voiceSelect.options].some(o => o.value === previous) ? previous : 'auto';
  }
  populateVoices(); synth?.addEventListener?.('voiceschanged', populateVoices);
  function stop() { readToken++; synth?.cancel(); utterance = null; }
  function unlockAudio() {
    if (!synth || voiceSelect.value === 'off') return;
    try { synth.resume?.(); const warmup = new SpeechSynthesisUtterance(' '); warmup.volume = 0; synth.speak(warmup); } catch {}
  }
  async function speak(sentences, newsStart = -1, base = 0) {
    stop(); const token = readToken;
    if (!synth || voiceSelect.value === 'off') { status.textContent = 'Cavab ekranda göstərilir.'; return; }
    if (!voices().length) await new Promise(resolve => {
      const done = () => { clearTimeout(timeout); synth.removeEventListener?.('voiceschanged', done); resolve(); };
      const timeout = setTimeout(done, 1200); synth.addEventListener?.('voiceschanged', done, {once:true});
    });
    if (token !== readToken) return;
    const voice = selectReadingVoice(voices(), voiceSelect.value);
    if (!voice) { status.textContent = 'Bu cihazda Azərbaycan dili səsi yoxdur. Cavab aşağıda mətnlə göstərilir. İstəsəniz, səs siyahısından başqa dili özünüz seçə bilərsiniz.'; return; }
    const language = voice.lang;
    const voiceNote = /^az(?:-|$)/i.test(language) ? '' : /^tr(?:-|$)/i.test(language) ? ' Azərbaycan səsi yoxdur; türkcə səs istifadə olunur.' : ' Cihazın standart səsi istifadə olunur.';
    let n = 0;
    const next = () => {
      if (token !== readToken || n >= sentences.length) { if (token === readToken) status.textContent = 'Oxuma tamamlandı.' + voiceNote; return; }
      const position = n++;
      if (newsStart >= 0 && position >= newsStart) { index = base + position - newsStart; output.querySelectorAll('li').forEach((li,i) => li.classList.toggle('current', i === index)); }
      utterance = new SpeechSynthesisUtterance(sentences[position]);
      utterance.lang = language; if (voice) utterance.voice = voice; utterance.rate = .95;
      utterance.onend = next;
      utterance.onerror = event => { if (token === readToken && event.error !== 'canceled' && event.error !== 'interrupted') status.textContent = 'Brauzer səsləndirməni başlada bilmədi. Cavab ekrandadır; “Davam et” ilə yenidən sınayın.'; };
      try { synth.resume?.(); synth.speak(utterance); } catch { status.textContent = 'Bu brauzerdə səsləndirmə mümkün olmadı. Cavab ekrandadır.'; }
    };
    status.textContent = 'Oxuyuram…' + voiceNote; next();
  }
  function display(answer) {
    result = answer; index = 0;
    output.innerHTML = `<p>${escape(answer.text)}</p>${answer.items?.length ? '<ol>' + answer.items.map(a => `<li><a href="${escape(safeLink(a.sourceUrl))}" target="_blank" rel="noopener noreferrer">${escape(a.title)}</a><small>${escape(a.source)} · ${escape(dateLabel(a.publishedAt))}</small></li>`).join('') + '</ol>' : ''}${(answer.links || []).map(l => `<a class="assistant-source" href="${escape(safeLink(l.url))}" ${String(l.url).startsWith('#/') ? '' : 'target="_blank" rel="noopener noreferrer"'}>${escape(l.title)} ↗</a>`).join('')}`;
  }
  const session = createVoiceSession({
    Recognition: window.SpeechRecognition || window.webkitSpeechRecognition,
    onStart() { micButton.textContent = '■ Dinləməni bitir'; launcher.classList.add('listening'); launcher.setAttribute('aria-pressed','true'); micButton.setAttribute('aria-pressed','true'); status.textContent = 'Dinləyirəm… Bitirəndə cavab avtomatik hazırlanacaq.'; },
    onTranscript(text) { input.value = text; status.textContent = 'Eşitdim: ' + text; },
    onComplete(text) { run(text); },
    onEnd() { micButton.textContent = '🎤 Danış'; launcher.classList.remove('listening'); launcher.setAttribute('aria-pressed','false'); micButton.setAttribute('aria-pressed','false'); },
    onError(error) {
      const messages = {
        unsupported: 'Bu brauzerdə səs tanıma yoxdur. Saytı Chrome və ya Safari-də açın, yaxud əmri yazın.',
        'not-allowed': 'Mikrofon icazəsi verilmədi. Brauzerin sayt icazələrində mikrofonu aktiv edin və yenidən toxunun.',
        'service-not-allowed': 'Brauzerin səs tanıma xidməti əlçatan deyil. Saytı adi Chrome və ya Safari pəncərəsində açın.',
        'language-not-supported': 'Brauzer Azərbaycan dilində səs tanımanı dəstəkləmir. Bu cihazda əmri yazmaq mümkündür.',
        'audio-capture': 'Mikrofon açılmadı. Onu istifadə edən başqa tətbiqi bağlayıb yenidən sınayın.',
        'no-speech': 'Səs eşidilmədi. Mikrofona toxunub yenidən danışın.',
        network: 'Səs tanıma xidməti ilə bağlantı alınmadı. İnterneti yoxlayın və yenidən toxunun.',
      };
      status.textContent = messages[error] || 'Səs tanınmadı. Mikrofona toxunub yenidən sınayın.';
    },
  });
  function control(action) {
    if (action === 'stop') { stop(); session.cancel(); status.textContent = 'Dayandırıldı.'; return; }
    if (action === 'resume') { unlockAudio(); if (result) speak([result.text, ...(result.items || []).slice(index).map(a => a.title)], 1, index); else status.textContent = 'Əvvəl xəbər və ya məlumat soruşun.'; return; }
    if (!result?.items?.length) { status.textContent = 'Əvvəl xəbər başlıqlarını soruşun.'; return; }
    if (action === 'next') { if (index + 1 >= result.items.length) { status.textContent = 'Siyahı tamamlandı.'; return; } index++; speak([result.items[index].title], 0, index); return; }
    const item = result.items[index];
    if (action === 'open') { stop(); status.textContent = 'Mənbəni açmaq üçün aşağıdakı keçidə toxunun.'; output.innerHTML = `<a class="assistant-source" href="${escape(safeLink(item.sourceUrl))}" target="_blank" rel="noopener noreferrer">${escape(item.title)} ↗</a>`; return; }
    if (action === 'alternatives') display({text:'Bu xəbərin mənbələri:', items:[item, ...(item.alts || []).map(a => ({...a, title:item.title}))]});
  }
  async function run(text) {
    const id = ++request; session.cancel(); stop(); input.value = text; status.textContent = 'Məlumatı yoxlayıram…';
    try { const answer = await answerCommand(text, getSnapshot(), context, providers); if (id !== request) return; if (answer.control) { control(answer.control); return; } display(answer); speak([answer.text, ...(answer.readNews ? answer.items || [] : []).map((a,i) => `${i+1}. ${a.title}`)], answer.readNews ? 1 : -1); }
    catch { if (id === request) status.textContent = 'Sorğunu yerinə yetirmək olmadı. Yenidən sınayın.'; }
  }
  function close() { panel.hidden = true; launcher.setAttribute('aria-expanded','false'); request++; stop(); session.cancel(); launcher.focus(); }
  function startListening() {
    panel.hidden = false; launcher.setAttribute('aria-expanded','true');
    if (session.active) { session.stop(); return; }
    request++; stop();
    // A deliberate microphone tap opts back into spoken replies, even after text-only mode.
    if (voiceSelect.value === 'off') voiceSelect.value = 'auto';
    unlockAudio();
    status.textContent = 'Mikrofon açılır…'; session.start();
  }
  launcher.onclick = startListening;
  root.querySelector('form').onsubmit = event => { event.preventDefault(); unlockAudio(); if (input.value.trim()) run(input.value.trim()); };
  root.addEventListener('click', event => {
    const example = event.target.closest('[data-example]');
    if (example) { unlockAudio(); run(example.dataset.example); return; }
    const button = event.target.closest('[data-assistant]'); if (!button) return;
    if (button.dataset.assistant === 'close') close();
    else if (button.dataset.assistant === 'mic') startListening();
    else { unlockAudio(); control(button.dataset.assistant); }
  });
  root.addEventListener('keydown', event => { if (event.key === 'Escape' && !panel.hidden) close(); });
  voiceSelect.onchange = () => { stop(); status.textContent = 'Səs seçimi dəyişdirildi.'; };
  document.addEventListener('visibilitychange', () => { if (document.hidden) { request++; stop(); session.cancel(); } });
  return {run, close};
}
