// «N mənbə» kartında keçid ən sürətli mənbəyə (sahib, 2026-11-10: «saytdan mənbə ağır açılır»). Sürət — telefon şəraitində ilk görüntü
// (FCP, ms), .github/scripts/menbe-suret.cjs gündə iki dəfə ölçür və «suret» budağına yazır. Fərq ≥ 1 s olanda kartın keçidi və mənbə
// adı ən sürətli mənbəyə keçir; kartın nömrəsi, başlığı, şəkli, paylaşma keçidi və «Dinlə» eyni qalır, əvvəlki əsas mənbə «N mənbə»
// siyahısına düşür. Rəsmi mənbə (president.az, mehriban-aliyeva.az) həmişə əsasdır. Ölçülməyən mənbəyə toxunulmur.
// Ayrıca fayldır: app.js-in ölçüsü artmır, lent gələndən sonra yüklənir; alınmasa kartlar olduğu kimi qalır.
const URL_ = "https://raw.githubusercontent.com/8ulduz/8ulduz/suret/menbe-suret.json";
const OFFICIAL = new Set(["Prezident.az", "Mehriban Əliyeva"]), GAIN_MS = 1000;
const host = u => (/^https?:\/\/([^/?#:]+)/i.exec(u || "")?.[1] || "").toLowerCase().replace(/^www\./, "");

export function swifter(ms) {
  const f = r => ms?.[host(r.sourceUrl)];
  return a => {
    if (!a?.alts?.length || OFFICIAL.has(a.source) || !f(a)) return a;
    let b = null;
    for (const r of a.alts) if ((r.lang || "az") === (a.lang || "az") && f(r) && (!b || f(r) < f(b))) b = r;
    if (!b || f(a) - f(b) < GAIN_MS) return a;
    const old = { source: a.source, sourceUrl: a.sourceUrl, publishedAt: a.publishedAt, title: a.title, lang: a.lang };
    return { ...a, source: b.source, sourceUrl: b.sourceUrl, author: "", alts: [old, ...a.alts.filter(r => r !== b)] };
  };
}

export async function load() {
  const r = await fetch(URL_);
  const d = r.ok ? await r.json() : null;
  return d?.ms && typeof d.ms === "object" ? swifter(d.ms) : null;
}
