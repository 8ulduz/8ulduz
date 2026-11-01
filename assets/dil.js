// Saytın öz yazılarının tərcüməsi. Yalnız Azərbaycan dilindən başqa dil seçiləndə yüklənir: Azərbaycan dilində giriş bu faylı görmür (3-cü qırmızı xətt).
// Xəbər mətni tərcümə olunmur. Yazı lüğətdə tam uyğun gəlməlidir, ona görə xəbər başlığına toxunmur.
const MON = ["yanvar", "fevral", "mart", "aprel", "may", "iyun", "iyul", "avqust", "sentyabr", "oktyabr", "noyabr", "dekabr"];
const DAYS = { "bazar ertəsi": 0, "çərşənbə axşamı": 1, "çərşənbə": 2, "cümə axşamı": 3, "cümə": 4, "şənbə": 5, "bazar": 6 };
const monthOf = s => MON.indexOf(s.toLowerCase());
const shortOf = s => MON.findIndex(m => m.slice(0, 3) === s);
const ATTRS = ["title", "aria-label", "placeholder"];
const SKIP = new Set(["SCRIPT", "STYLE", "NOSCRIPT", "TEXTAREA"]);

export function makeTr(lang) {
  const { w, t, mon, monN, mon3, days } = lang;
  const out = new Set(Object.values(w));
  const seen = new Map();
  const put = (tpl, ...parts) => parts.reduce((s, p, i) => s.replace(`$${i + 1}`, p), tpl);
  const RULES = [
    [/^(\d+) dəqiqə əvvəl$/, m => put(t.min, m[1])],
    [/^(\d+) saat əvvəl$/, m => put(t.hour, m[1])],
    [/^(\d+) gün əvvəl$/, m => put(t.day, m[1])],
    [/^(\d+) mənbə$/, m => put(t.src, m[1])],
    [/^(\d+) xəbər$/, m => put(t.count, m[1])],
    [/^(\d+) yeni xəbər$/, m => put(t.fresh, m[1])],
    [/^(\d{1,2}) ([\p{L}-]+)$/u, m => w[m[2]] ? m[1] + " " + w[m[2]] : null],
    [/^Daha çox \((\d+)\)$/, m => put(t.more, m[1])],
    [/^Bütün mənbələr \((\d+)\)$/, m => put(t.allSrc, m[1])],
    [/^Səhifə (\d+)$/, m => put(t.page, m[1])],
    [/^(.+) haqqında son 5 gündə xəbər tapılmadı$/, m => put(t.noTeamNews, m[1])],
    [/^Hazırda (\d+) mənbə izlənilir\. Hər lentin vəziyyətini$/, m => put(t.tracked, m[1])],
    [/^(.+): (\d+) oyun, (\d+) Q · (\d+) H · (\d+) M, qol (.+)$/, m => put(t.form, tr(m[1]), m[2], m[3], m[4], m[5], m[6])],
    [/^(\d{4}) 8ulduz\. Bütün xəbər mətnlərinin hüququ müvafiq mənbələrə aiddir$/, m => put(t.copy, m[1])],
    [/^(\d+)-[cç][iıuü] tur$/, m => put(t.round, m[1])],
    [/^(\d+)-[cç][iıuü] yer$/, m => put(t.place, m[1])],
    [/^(\d+)-[cç][iıuü] mərhələ$/, m => put(t.stage, m[1])],
    [/^yoxlanıb (.+)$/, m => put(t.checked, tr(m[1]))],
    [/^(.+) oyunları hələ əlavə olunmayıb$/, m => put(t.noGames, tr(m[1]))],
    [/^(\d{1,2}) (\p{L}+) oyunlarına qədər$/u, m => monthOf(m[2]) < 0 ? null : put(t.until, `${m[1]} ${mon[monthOf(m[2])]}`)],
    [/^(\p{L}+(?: \p{L}+)?), (\d{1,2}) (\p{L}+) (\d{4})$/u, m => { const d = DAYS[m[1].toLowerCase()], i = monthOf(m[3]); return d === undefined || i < 0 ? null : `${days[d]}, ${m[2]} ${mon[i]} ${m[4]}`; }],
    [/^(\d{1,2}) (\p{L}+)( \d{4})?$/u, m => monthOf(m[2]) < 0 ? null : `${m[1]} ${mon[monthOf(m[2])]}${m[3] || ""}`],
    [/^(\d{1,2}) (\p{L}{3})(, \d{1,2}:\d{2})?$/u, m => shortOf(m[2]) < 0 ? null : `${m[1]} ${mon3[shortOf(m[2])]}${m[3] || ""}`],
    [/^(\p{L}+) (\d{4})$/u, m => monthOf(m[1]) < 0 ? null : `${monN[monthOf(m[1])]} ${m[2]}`],
  ];
  const core = s => {
    if (w[s] !== undefined) return w[s];
    for (const [rx, fn] of RULES) {
      const m = s.match(rx);
      const r = m && fn(m);
      if (r) return r;
    }
    // Birləşmiş yazı: «Namaz · Bakı», «Yeniləndi: indicə», «Bakı, Sumqayıt».
    for (const sep of [" — ", " · ", ": ", ", "]) {
      if (!s.includes(sep)) continue;
      const parts = s.split(sep), done = parts.map(tr);
      if (done.some((p, i) => p !== parts[i])) return done.join(sep);
    }
    return null;
  };
  function tr(text) {
    if (seen.has(text)) return seen.get(text);
    let res = text;
    if (!out.has(text)) {
      const m = text.match(/^([^\p{L}\p{N}«]*)(.*?)([^\p{L}\p{N})]*)$/su);
      const got = w[text] !== undefined ? w[text] : m && m[2] ? core(m[2]) : null;
      if (got !== null && got !== undefined) res = w[text] !== undefined ? got : m[1] + got + m[3];
    }
    if (seen.size < 5000) seen.set(text, res);
    return res;
  }
  return tr;
}

export function translateTree(root, tr) {
  const doc = root.ownerDocument || root;
  if (root.nodeType === 3) return textNode(root, tr);
  if (root.nodeType === 1 && SKIP.has(root.tagName)) return;
  const walker = doc.createTreeWalker(root, 4);
  for (let n = walker.nextNode(); n; n = walker.nextNode()) if (!SKIP.has(n.parentNode?.tagName)) textNode(n, tr);
  if (root.nodeType === 1) attrs(root, tr);
  root.querySelectorAll?.("[title],[aria-label],[placeholder]").forEach(el => attrs(el, tr));
  root.querySelectorAll?.("template").forEach(el => translateTree(el.content, tr));
}
function textNode(n, tr) {
  const v = n.nodeValue, m = v.match(/^(\s*)([\s\S]*?)(\s*)$/);
  if (!m[2]) return;
  const r = tr(m[2].replace(/\s+/g, " "));
  if (r !== m[2] && r !== m[2].replace(/\s+/g, " ")) n.nodeValue = m[1] + r + m[3];
}
function attrs(el, tr) {
  for (const a of ATTRS) {
    const v = el.getAttribute(a);
    if (v) { const r = tr(v); if (r !== v) el.setAttribute(a, r); }
  }
}
// Bu dildə xəbəri olmayan bölmənin keçidi gizlənir. İdman bütün dillərdədir.
export function emptySections(articles, code) {
  const all = new Set(), mine = new Set();
  for (const a of articles || []) {
    all.add(a.category);
    if ((a.lang ?? "az") === code) mine.add(a.category);
  }
  all.delete("idman");
  return [...all].filter(c => !mine.has(c));
}

export async function startDil(S, code) {
  const { default: lang } = await import(`./dil-${code}.js`);
  const tr = makeTr(lang);
  let from, empty = [];
  const hide = () => {
    if (from !== S.data?.articles) { from = S.data?.articles; empty = emptySections(from, code); }
    document.querySelectorAll('a[href^="#/bolme/"]').forEach(a => { a.style.display = empty.includes(a.getAttribute("href").slice(8).split(/[/?]/)[0]) ? "none" : ""; });
  };
  document.documentElement.lang = code;
  S.tr = root => translateTree(root, tr);
  const ask = window.confirm.bind(window);
  window.confirm = text => ask(tr(String(text)));
  translateTree(document.documentElement, tr);
  hide();
  new MutationObserver(list => {
    for (const m of list) {
      if (m.type === "attributes") attrs(m.target, tr);
      else if (m.type === "characterData") textNode(m.target, tr);
      else m.addedNodes.forEach(n => translateTree(n, tr));
    }
    hide();
  }).observe(document.documentElement, { subtree: true, childList: true, characterData: true, attributes: true, attributeFilter: ATTRS });
}
