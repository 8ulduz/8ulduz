const REPO = '8ulduz/8ulduz';
const POLICY_PATH = 'assets/content-policy.js';
const API = 'https://api.github.com';

export function removalKey(value) {
  const u = new URL(value);
  // Yolu «/» olan, amma sorğusu olan ünvan da xəbərdir (azpolitika.info/?p=846712); yalnız saytın baş səhifəsi rədd edilir.
  if (u.protocol !== 'https:' || u.username || u.password || u.port || (u.pathname === '/' && !u.search)) throw new Error('Xəbərin tam HTTPS keçidini yazın.');
  const nums = [...u.pathname.matchAll(/(?:\/|[-_])(\d{5,})(?=\.html?|\/|$)/g)].map(m => m[1]).filter(n => !/^(?:19|20)\d{6}$/.test(n));
  return nums.length ? u.hostname.toLowerCase().replace(/^www\./, '') + '#' + nums.at(-1) : u.href.split('#')[0];
}

export function parsePolicy(text) {
  const start = text.indexOf('{'), end = text.lastIndexOf('}');
  if (start < 0 || end <= start) throw new Error('Saytın qayda faylı oxunmadı.');
  const data = JSON.parse(text.slice(start, end + 1));
  if (!data.azSources || !data.worldSources || !Array.isArray(data.blockedHosts)) throw new Error('Saytın qayda faylı tanınmadı.');
  return {data, prefix: text.slice(0, start), suffix: text.slice(end + 1)};
}

export async function makeRemoval(article, user, policy, at = new Date().toISOString()) {
  const rows = [article, ...(article.alts || [])], urls = [], keys = [], ids = new Set([article.id].filter(Boolean));
  const domains = Object.values({...policy.azSources, ...policy.worldSources}).flat();
  for (const row of rows) {
    if (!row.sourceUrl) continue;
    // Əlavə mənbənin keçidi açar verə bilməsə (http://) bütün çıxarılma dayanmırdı: o, yalnız id-si ilə çıxarılır
    // (editorial_sync.py http ünvanlı siyahını bütöv rədd edir, ona görə ünvanı yazılmır). Əsas xəbər üçün xəta qalır.
    let key = '', u;
    try { key = removalKey(row.sourceUrl); u = new URL(row.sourceUrl); } catch (e) { if (row === article) throw e; }
    if (key) {
      const host = u.hostname.toLowerCase().replace(/^www\./, '');
      if (!domains.some(d => host === d || host.endsWith('.' + d))) throw new Error('Bu keçid saytın xəbər mənbələrinə aid deyil.');
      urls.push(row.sourceUrl, u.href); keys.push(key);
    }
    for (const url of new Set([row.sourceUrl, u?.href || row.sourceUrl])) {
      const digest = await crypto.subtle.digest('SHA-1', new TextEncoder().encode(url));
      ids.add([...new Uint8Array(digest)].map(n => n.toString(16).padStart(2, '0')).join('').slice(0, 16));
    }
  }
  if (!urls.length) throw new Error('Xəbər keçidi yoxdur.');
  return {key: keys[0], ids: [...ids], urls: [...new Set(urls)], keys: [...new Set(keys)], title: String(article.title || article.sourceUrl).slice(0, 400), at, by: user};
}

export function mergeRemoval(text, record) {
  const parsed = parsePolicy(text), records = parsed.data.removedArticles ||= {};
  const old = records[record.key];
  const merged = old ? {...old, ids: [...new Set([old.id, ...(old.ids || []), ...record.ids].filter(Boolean))], urls: [...new Set([...(old.urls || []), ...record.urls])], keys: [...new Set([old.key, ...(old.keys || []), ...record.keys].filter(Boolean))]} : record;
  if (old && JSON.stringify(old) === JSON.stringify(merged)) return {text, changed: false};
  records[record.key] = merged;
  return {text: parsed.prefix + JSON.stringify(parsed.data, null, 2) + parsed.suffix, changed: true};
}

const decode = s => new TextDecoder().decode(Uint8Array.from(atob(s.replace(/\s/g, '')), c => c.charCodeAt(0)));
const encode = s => {
  const bytes = new TextEncoder().encode(s); let result = '';
  for (let i = 0; i < bytes.length; i += 8192) result += String.fromCharCode(...bytes.subarray(i, i + 8192));
  return btoa(result);
};

export class GithubEditor {
  #token = '';
  // Brauzerin fetch-i obyektin metodu kimi çağırılanda «Illegal invocation» atır (sahib, 2026-11-11: panel girişi): ox funksiyası ilə.
  constructor(fetcher = (...a) => fetch(...a)) { this.fetcher = fetcher; this.user = null; }
  logout() { this.#token = ''; this.user = null; }
  async request(path, options = {}) {
    if (!this.#token) throw new Error('Əvvəlcə giriş edin.');
    const response = await this.fetcher(API + path, {...options, cache: 'no-store', redirect: 'error', signal: AbortSignal.timeout(15000), headers: {'Accept': 'application/vnd.github+json', 'X-GitHub-Api-Version': '2022-11-28', 'Authorization': 'Bearer ' + this.#token, ...(options.body ? {'Content-Type': 'application/json'} : {})}});
    if (!response.ok) {
      const error = new Error(response.status === 401 ? 'Giriş açarı qəbul edilmədi.' : response.status === 403 ? 'Bu əməliyyat üçün yazma icazəsi yoxdur.' : response.status === 409 ? 'Qayda faylı dəyişib; yenidən yoxlanılır.' : 'GitHub sorğusu alınmadı (' + response.status + ').');
      error.status = response.status; throw error;
    }
    return response.json();
  }
  async login(token) {
    this.logout(); this.#token = token.trim();
    try {
      const [user, repo] = await Promise.all([this.request('/user'), this.request('/repos/' + REPO)]);
      if (!user.login || repo.permissions?.push !== true) throw new Error('Bu hesabın 8ulduz/8ulduz reposuna yazma icazəsi yoxdur.');
      this.user = user.login; return user.login;
    } catch (error) { this.logout(); throw error; }
  }
  async policy() {
    const file = await this.request('/repos/' + REPO + '/contents/' + POLICY_PATH + '?ref=main');
    if (file.encoding !== 'base64' || !file.sha) throw new Error('Qayda faylı oxunmadı.');
    return {sha: file.sha, text: decode(file.content)};
  }
  async remove(article) {
    if (!this.user) throw new Error('Əvvəlcə giriş edin.');
    for (let attempt = 0; attempt < 3; attempt++) {
      const file = await this.policy(), {data} = parsePolicy(file.text);
      const record = await makeRemoval(article, this.user, data), merged = mergeRemoval(file.text, record);
      if (!merged.changed) return {record, already: true};
      try {
        const result = await this.request('/repos/' + REPO + '/contents/' + POLICY_PATH, {method: 'PUT', body: JSON.stringify({branch: 'main', sha: file.sha, content: encode(merged.text), message: 'Redaksiya: xəbər çıxarıldı (' + record.key.slice(0, 100) + ')'})});
        return {record, commit: result.commit?.sha};
      } catch (error) { if (error.status !== 409 || attempt === 2) throw error; }
    }
  }
  async liveContains(record) {
    const file = await this.request('/repos/' + REPO + '/contents/data/latest.json?ref=live');
    const data = JSON.parse(decode(file.content));
    return Object.values(data.removed || {}).some(r => r.key === record.key || r.ids?.some(id => record.ids.includes(id)));
  }
}
