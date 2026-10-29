import {selectReadingVoice} from './assistant.js';

export function readingChunks(text, limit=220) {
  const sentences=String(text || '').trim().match(/[^.!?]+[.!?]*\s*/gu) || [];
  const chunks=[];
  for(const sentence of sentences) {
    const words=sentence.trim().split(/\s+/); let part='';
    for(const word of words) {
      if(part && part.length+word.length+1>limit){chunks.push(part);part='';}
      part+=(part?' ':'')+word;
    }
    if(part)chunks.push(part);
  }
  return chunks;
}

export function mountReader({getArticles,driverEnabled=()=>false,setDriver=()=>{}}) {
  const root=document.createElement('section');
  root.className='driver-reader'; root.hidden=true;
  root.setAttribute('aria-label','Azərbaycan dilində xəbər dinlə');
  root.innerHTML='<header><b>Xəbəri dinlə</b><button data-reader="close" aria-label="Dinləməni bağla">✕</button></header><h2></h2><a class="reader-source" target="_blank" rel="noopener noreferrer">Mənbədə tam xəbəri aç ↗</a><p role="status"></p><div class="reader-controls"><button data-reader="play">▶ Oxu</button><button data-reader="pause">Ⅱ Fasilə</button><button data-reader="stop">■ Dayandır</button><button data-reader="next">Növbəti xəbər →</button></div><p class="reader-note">Oxuma bu səhifədə davam edir. İdarəetməni yola çıxmazdan əvvəl qurun.</p>';
  document.body.append(root);
  const status=root.querySelector('[role=status]'), play=root.querySelector('[data-reader=play]');
  let article=null, text='', chunks=[], index=0, generation=0, utterance=null;
  let textsPromise=null;
  const synth=window.speechSynthesis;
  function cancel(){generation++; synth?.cancel();utterance=null;}
  function setStatus(message){status.textContent=message;}
  function voice(){return selectReadingVoice(synth?.getVoices?.() || []);}
  function read() {
    if(!text){setStatus('Tam məqalə mətni hələ əldə edilməyib. Mənbə keçidindən xəbəri aça bilərsiniz.');return;}
    if(!synth || !voice()){setStatus('Bu cihaz/brauzer Azərbaycan dilində səs təqdim etmir. Azərbaycan səsi olan cihaz və ya ayrıca Azərbaycan TTS xidməti tələb olunur.');return;}
    if(synth.paused){synth.resume();setStatus('Oxuma davam edir.');return;}
    cancel(); chunks=readingChunks(article.title+'. '+text);index=0;
    const id=generation;
    function next() {
      if(id!==generation)return;
      if(index>=chunks.length){setStatus('Xəbər tamamlandı.');return;}
      utterance=new SpeechSynthesisUtterance(chunks[index]);
      utterance.voice=voice();utterance.lang='az-AZ';utterance.rate=.95;
      setStatus(`Oxunur · ${index+1}/${chunks.length}`);
      utterance.onend=()=>{index++;next();};
      utterance.onerror=event=>{if(id===generation && !['canceled','interrupted'].includes(event.error))setStatus('Səsli oxuma alınmadı. Oxu düyməsi ilə yenidən sınayın.');};
      synth.speak(utterance);
    }
    next();
  }
  async function select(item) {
    cancel(); const id=generation; article=item;text='';root.hidden=false;play.disabled=true;
    root.querySelector('h2').textContent=item.title;
    const source=root.querySelector('.reader-source');source.href=item.sourceUrl;source.textContent=`${item.source} — tam xəbəri mənbədə aç ↗`;
    setStatus('Mənbədən alınmış məqalə mətni yoxlanır…');
    if(item.lang && item.lang!=='az'){setStatus('Səsli oxuma yalnız Azərbaycan dilində xəbərlər üçündür.');return;}
    try {
      if(!textsPromise)textsPromise=fetch('./data/reader.json',{cache:'no-store',signal:AbortSignal.timeout(12000)}).then(r=>{if(!r.ok)throw Error();return r.json();}).catch(error=>{textsPromise=null;throw error;});
      const data=await textsPromise;if(id!==generation)return;
      const cached=data.articles?.[item.sourceUrl];
      if(cached?.text && cached.lang==='az')text=cached.text;
      play.disabled=!text;
      if(text){read();}else setStatus('Tam məqalə mətni hələ əldə edilməyib. Başlıq tam məqalə kimi oxunmur; xəbəri mənbədə aça bilərsiniz.');
    } catch {if(id===generation){play.disabled=true;setStatus('Məqalə mətni hazırda yüklənmir. Xəbəri mənbədə aça bilərsiniz.');}}
  }
  document.addEventListener('click',event=>{
    if(event.target.closest?.('[data-driver-mode]')) {
      const on=!driverEnabled();setDriver(on);
      if(!on){cancel();root.hidden=true;}
      return;
    }
    const button=event.target.closest?.('[data-listen]');if(!button)return;
    const item=getArticles().find(a=>String(a.id)===button.dataset.listen);
    if(item)select(item);
  });
  document.addEventListener('click',event=>{
    if(!driverEnabled() || event.defaultPrevented || event.button!==0 || event.ctrlKey || event.metaKey || event.shiftKey || event.altKey)return;
    const link=event.target.closest?.('a[href]');
    if(!link || link.classList.contains('reader-source'))return;
    const item=getArticles().find(a=>a.sourceUrl===link.href && (a.lang || 'az')==='az');
    if(!item)return;
    event.preventDefault();event.sourceNavigation=true;
    // A real user click opens the publisher; this tab owns the audio controls.
    window.open(item.sourceUrl,'_blank','noopener,noreferrer');
    select(item);
  });
  root.addEventListener('click',event=>{
    const action=event.target.closest('[data-reader]')?.dataset.reader;
    if(action==='close'){cancel();root.hidden=true;}
    if(action==='stop'){cancel();index=0;setStatus('Dayandırıldı.');}
    if(action==='pause'){synth?.pause();setStatus('Fasilə verildi. Oxu düyməsi ilə davam edin.');}
    if(action==='play')read();
    if(action==='next'){
      const all=getArticles().filter(a=>(a.lang || 'az')==='az');
      const at=all.findIndex(a=>a.id===article?.id);
      if(at>=0 && at+1<all.length)select(all[at+1]);else setStatus('Növbəti Azərbaycan dilində xəbər yoxdur.');
    }
  });
  window.addEventListener('pagehide',cancel);
  return {select};
}
