// Global outbound-click counts. No credentials or personal identifiers in this module.
export const eventPath = name => 'source-click-' + String(name || '').trim();
export function periodStarts(now = new Date()) {
  const p = Object.fromEntries(new Intl.DateTimeFormat('en-CA', {timeZone:'Asia/Baku',year:'numeric',month:'2-digit',day:'2-digit'}).formatToParts(now).map(x => [x.type,x.value]));
  const day = `${p.year}-${p.month}-${p.day}`;
  const week = new Date(day + 'T00:00:00Z');
  week.setUTCDate(week.getUTCDate() - (week.getUTCDay() + 6) % 7);
  return [day, week.toISOString().slice(0,10), `${p.year}-${p.month}-01`, `${p.year}-01-01`];
}
// GoatCounter 404 = bu yolda hələ keçid yoxdur (0). İl 0-dırsa gün/həftə/ay da 0-dır: 4 sorğu əvəzinə 1.
export async function fetchCounts(code, name, fetcher = fetch, now = new Date()) {
  if (!/^[a-z0-9-]+$/i.test(code || '')) throw Error('not configured');
  const one = async start => {
    const url = `https://${code}.goatcounter.com/counter/${encodeURIComponent(eventPath(name))}.json?start=${start}`;
    const r = await fetcher(url, {signal:AbortSignal.timeout(8000)});
    if(r.status===403)throw Error('public-counter-disabled');
    if(r.status===404)return 0;
    if (!r.ok) return null;
    const data = await r.json();
    const count = String(data.count ?? '').replace(/[\s,\.\u00a0]/g, '');
    return /^\d+$/.test(count) ? Number(count) : null;
  };
  const [day, week, month, year] = periodStarts(now);
  const yearCount = await one(year);
  if (yearCount === 0) return [0, 0, 0, 0];
  return [...await Promise.all([day, week, month].map(one)), yearCount];
}
// Heç bir keçid yoxdursa və ya məlumat alınmayıbsa sayğac göstərilmir (kartlarda «—/—/—/—» səs-küyü idi).
export const shownCount = counts => (counts || []).some(n => Number.isSafeInteger(n) && n > 0) ? countText(counts) : '';
export const countText = counts => (counts || [null,null,null,null]).map(n => Number.isSafeInteger(n) && n >= 0 ? n : '—').join('/');

export function mountSourceStats({code, getArticles}) {
  if (!/^[a-z0-9-]+$/i.test(code || '')) return;
  const cache = new Map(), seen = new WeakSet(), pending = new Map();
  const tooltip = 'Bütün ziyarətçilər üzrə mənbəyə keçid: bu gün / bu həftə (bazar ertəsindən) / bu ay / bu il · Bakı vaxtı. Statistika 4 saata qədər gecikə bilər. — məlumat əlçatan deyil.';
  function paint(name, values) {
    document.querySelectorAll('[data-source-count]').forEach(el => {
      if (el.dataset.sourceCount !== name) return;
      el.textContent = shownCount(values); el.title = tooltip;
      el.setAttribute('aria-label', `${name}: ${countText(values)}, gün / həftə / ay / il`);
    });
  }
  // At most two source requests (eight period queries) in flight.
  const queue = []; let active = 0, disabled=false;
  function pump() {
    while(active < 2 && queue.length) {
      const name = queue.shift(); active++;
      fetchCounts(code,name).catch(error => {
        if(error.message==='public-counter-disabled'){disabled=true;queue.length=0;pending.clear();}
        return [null,null,null,null];
      }).then(values => {
        cache.set(name,values); paint(name,values);
      }).finally(() => {pending.delete(name); active--; pump();});
    }
  }
  function load(name) {
    if(disabled)return;
    if(cache.has(name)){paint(name,cache.get(name));return;}
    if(pending.has(name))return;
    pending.set(name,true); queue.push(name); pump();
  }
  const observer = typeof IntersectionObserver === 'function' ? new IntersectionObserver(entries => entries.forEach(e => {
    if(e.isIntersecting){observer.unobserve(e.target);load(e.target.dataset.sourceCount);}
  })) : null;
  function scan() {
    document.querySelectorAll('[data-source-count]').forEach(el => {
      if(seen.has(el))return; seen.add(el); el.title=tooltip;
      if(cache.has(el.dataset.sourceCount))paint(el.dataset.sourceCount,cache.get(el.dataset.sourceCount));
      else if(observer)observer.observe(el); else load(el.dataset.sourceCount);
    });
  }
  new MutationObserver(scan).observe(document.querySelector('#app'), {childList:true,subtree:true});
  scan();
  function track(event) {
    if((event.defaultPrevented && !event.sourceNavigation) || (event.type==='auxclick' && event.button!==1))return;
    if(!/^(www\.)?8ulduz\.az$|^8ulduz\.github\.io$/i.test(location.hostname))return;
    const link=event.target.closest?.('a[href]'); if(!link)return;
    const items=(getArticles() || []).flatMap(a => [a,...(a.alts || [])]);
    const article=items.find(a => a.sourceUrl===link.href);
    if(!article?.source || typeof window.goatcounter?.count!=='function')return;
    window.goatcounter.count({path:eventPath(article.source),title:article.source,event:true,no_session:true,referrer:''});
  }
  document.addEventListener('click',track);
  document.addEventListener('auxclick',track);
}
