// Media qaydası (sahib, 2026-11-27). Sahib mətbuatın ümumi qadağalarını istədi; ona «Media haqqında» Qanunun 14.1, 15.1 və 21-ci
// maddələri, Meta-nın qrafik məzmun qaydaları və beş təklif göstərildi. Cavab: «Hamısını əlavə et». Sənəd: docs/sosial-video.md
// «Media qaydası (sahib, 2026-11-27)».
//
//   1. Azyaşlı zərərçəkən və şübhəli (Qanun 15.1.5): mətndə azyaşlı, zərərçəkən və ya şübhəli hadisəsi və şəxsin adı birlikdədirsə
//      video olmur. Adsız xilas edilən uşaq olar.
//   2. Təqsirsizlik prezumpsiyası (14.1.14): məhkəmə hökmü olmadan «cinayətkar», «qatil», «oğru», «dələduz» … — video olmur.
//      Cinayətin adı («dələduzluq», «oğurluq», «qətl») olar.
//   3. Söyüş (14.1.6): səsdə və altyazıda yoxdur.
//   4. İntihar: üsulu, vasitəsi və yeri deyilmir. Sadəcə xəbər (üsulsuz) olar.
//   5. Çılpaqlıq və pornoqrafiya (14.1.13) və azyaşlının üzü — kadr yoxlamasındadır (KADR_SETIRLER, kadrHokmu), mətndə yox.
// Hər diktor mətni (xəbər, dünya, X, kanal videosu) VS.checkText-dən keçir, checkText bunu çağırır; videonun başlığı da yoxlanır
// (xəbər videosunun başlığı mənbədəndir: qaydanı pozan başlıqla video olmur). Gemini-yə göstəriş (GOSTERIS) hər mətn göstərişindədir.
// Sözlər dil profilindədir (.github/video-dil/<dil>.json «qayda»; sınaq dilində boşdur — qayda işləmir). Şəbəkə işi yoxdur.
"use strict";
const { dil } = require("./video-dil.cjs");

// Profilin nizami ifadələri bir dəfə qurulur. Ad qaydası böyük hərfə baxır: «i» bayrağı olmadan (/iu-da \p{Lu} kiçik hərfi də tutur).
const cache = new WeakMap();
function re(D) {
  if (!cache.has(D)) {
    const q = D.qayda || {}, mk = (s, fl = "iu") => (s ? new RegExp(s, fl) : null);
    cache.set(D, { azyasli: mk(q.azyasli), hadise: mk(q.hadise), ad: mk(q.ad, "u"), etiket: mk(q.etiket), hokm: mk(q.hokm), soyus: mk(q.soyus),
      intihar: mk(q.intihar), usul: mk(q.usul) });
  }
  return cache.get(D);
}
// JS-in /i bayrağı «İ»-ni «i» saymır: mətn həm özü, həm dilin kiçik hərfi ilə yoxlanır («QATİL» → «qatil»).
const tap = (rx, s, lc) => (rx ? ((s.match(rx) || lc.match(rx) || [])[0] || "") : "");

// Mətnin (başlıq + diktor mətni) yoxlanması: səbəb (azərbaycanca) və ya "" — keçdi.
function yoxla(metn, D = dil()) {
  const s = String(metn ?? "").replace(/\s+/g, " ").trim();
  if (!s) return "";
  const lc = s.toLocaleLowerCase(D.locale || "az"), R = re(D);
  const az = tap(R.azyasli, s, lc), hd = az && tap(R.hadise, s, lc), ad = hd && R.ad ? (s.match(R.ad) || [])[0] || "" : "";
  // Ad jurnala yazılmır (iş jurnalı açıqdır): azyaşlının adı orada da olmasın.
  if (az && hd && ad) return `azyaşlı zərərçəkən və ya şübhəlinin adı var («${az}», «${hd}…»; Media haqqında Qanun 15.1.5)`;
  const et = tap(R.etiket, s, lc);
  if (et && !tap(R.hokm, s, lc)) return `məhkəmə hökmü olmadan «${et}» deyilir (təqsirsizlik prezumpsiyası, 14.1.14): «şübhəli», «təqsirləndirilən» yazılmalıdır`;
  if (tap(R.soyus, s, lc)) return "söyüş var (Media haqqında Qanun 14.1.6)";
  const it = tap(R.intihar, s, lc), us = it && tap(R.usul, s, lc);
  if (it && us) return `intiharın üsulu, vasitəsi və ya yeri deyilir («${us}»)`;
  return "";
}

// Gemini-yə göstəriş (redaksiyanın dili ilə, digər göstəriş sətirləri kimi): xəbər, dünya, X və kanal videosunun mətn göstərişlərində.
const GOSTERIS = `- Media qaydası. Azyaşlı zərərçəkənin və ya şübhəlinin adını, soyadını, məktəbini, ünvanını yazma: «15 yaşlı yeniyetmə» kimi yaz.
  Məhkəmə hökmü olmadan heç kimi «cinayətkar», «qatil», «oğru», «dələduz», «terrorçu» adlandırma: «şübhəli», «təqsirləndirilən»,
  «saxlanılan» yaz. Söyüş, kobud söz və jarqon yazma, sitatda da. İntihar xəbərində üsulu, vasitəni və yeri yazma, yalnız baş verdiyini de.`;

// Kadr yoxlamasının ortaq sahələri (X, kanal və mənbə videosunun yoxlaması): qan, çılpaqlıq, azyaşlının üzü. Əmin olmayanda false.
const KADR_SETIRLER = `- "qan": true — yalnız kadrda ölüm anı, qan, meyit və ya ağır yaralı açıq görünürsə.
- "cilpaq": true — yalnız kadrda çılpaq bədən (cinsiyyət orqanı, açıq qadın döşü) və ya cinsi səhnə görünürsə.
- "usaq": true — yalnız 18 yaşından kiçik uşağın üzü aydın görünürsə və o, mətnə görə hadisənin zərərçəkəni (cinayət, zorakılıq,
  təcavüz, ağır xəsarət) və ya şübhəlisidir. Kütlədə, uzaqdan, bulanıq görünən, xilas edilən və ya sağ-salamat tapılan uşaq sayılmır.
- "qan", "cilpaq", "usaq": əmin deyilsənsə false yaz.`;
const KADR_JSON = `"qan": false, "cilpaq": false, "usaq": false`;
// Gemini-nin cavabı → səbəb və ya "" (keçdi).
function kadrHokmu(j) {
  if (j?.qan === true) return "kadrda ölüm anı, qan və ya meyit görünür";
  if (j?.cilpaq === true) return "kadrda çılpaqlıq və ya cinsi səhnə görünür (Media haqqında Qanun 14.1.13)";
  if (j?.usaq === true) return "kadrda azyaşlı zərərçəkənin və ya şübhəlinin üzü görünür (Media haqqında Qanun 15.1.5)";
  return "";
}

module.exports = { yoxla, GOSTERIS, KADR_SETIRLER, KADR_JSON, kadrHokmu };
