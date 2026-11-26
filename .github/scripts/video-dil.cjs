// Video sisteminin dil profili (sahib, 2026-11-26: yol xəritəsinin 2-ci addımı — «video sistemini dildən asılı olmayan et: dil,
// mənbələr və səs ayar kimi verilsin»). Videoda, səsdə, ssenaridə və paylaşım mətnlərində dilə bağlı hər şey bir fayldadır:
// .github/video-dil/<kod>.json. Yeni dil = yeni fayl (az.json ilə eyni açarlar; tests/video-dil.test.cjs yoxlayır), kod dəyişmir.
//
//   dil()        işin dili: VIDEO_DIL (boş — az). Video modulları (video-xeber, video-ssenari, video-maraqli, sosial-video) bunu işlədir.
//   dil("ru")    adla; yükləyicilər (youtube.cjs, tiktok.cjs) videonun dilini video.json-un «lang» sahəsindən götürür.
//   dilVarmi(k)  belə profil var? (yoxdursa yükləyici az profili ilə işləyir — başqa iş axınlarının videoları, icmal və s.)
//   fmt(şablon, { ad: dəyər })  «{ad}» yerinə dəyər; tanınmayan «{…}» olduğu kimi qalır.
// Profil sabitdir: oxunandan sonra dəyişmir (Object.freeze). Nizami ifadələr (herf, yad_herf, nisbi_gun, protokol, bagliyicilar) bir dəfə qurulur: D.re.
// Python tərəfi (video_ses.py, video_dinle.py) eyni faylları oxuyur. Qovluq: VIDEO_DIL_QOVLUQ (testlər üçün), yoxsa .github/video-dil.
"use strict";
const fs = require("fs"), path = require("path");

const QOVLUQ = path.join(__dirname, "..", "video-dil");
const KOD = /^[a-z]{2,3}$/;
const cache = new Map();
const qovluq = () => process.env.VIDEO_DIL_QOVLUQ || QOVLUQ;
const freeze = o => { if (o && typeof o === "object") { Object.values(o).forEach(freeze); Object.freeze(o); } return o; };

function oxu(kod, dir) {
  const d = JSON.parse(fs.readFileSync(path.join(dir, `${kod}.json`), "utf8"));
  if (d.kod !== kod) throw new Error(`video-dil: ${kod}.json-da kod «${d.kod}»-dur`);
  const re = {
    herf: new RegExp(d.herf, "u"),
    yadHerf: d.ssenari.yad_herf ? new RegExp(d.ssenari.yad_herf, "u") : null,
    nisbiGun: new RegExp(d.ssenari.nisbi_gun, "iu"),
    protokol: new RegExp(d.ssenari.protokol, "iu"),
    bagliyici: new RegExp(`^(${d.video.bagliyicilar.join("|")})$`, "u"),
    // Video seçimində zəif mövzu (lent.ceki.zeif, sosial-video.cjs cekisi): başlıqda olanda xəbərin çəkisi azalır.
    zeif: d.lent?.ceki?.zeif ? new RegExp(d.lent.ceki.zeif, "iu") : null,
    // Yayım kadrı (oyunun qolları, icmal, film, klip): mənbə videosu götürülmür (lent.yayim, video-menbe.cjs).
    yayim: d.lent?.yayim ? new RegExp(d.lent.yayim, "iu") : null,
  };
  return freeze({ ...d, re });
}

function dil(kod = process.env.VIDEO_DIL || "az") {
  kod = String(kod || "az").trim().toLowerCase();
  if (!KOD.test(kod)) throw new Error(`video-dil: yanlış dil kodu «${kod}»`);
  const dir = qovluq(), key = `${dir}\n${kod}`;
  if (!cache.has(key)) cache.set(key, oxu(kod, dir));
  return cache.get(key);
}
const dilVarmi = kod => KOD.test(String(kod || "")) && fs.existsSync(path.join(qovluq(), `${kod}.json`));
// Videonun öz dili (video.json «lang»); profili yoxdursa az.
const videonunDili = m => dil(dilVarmi(m?.lang) ? m.lang : "az");
const fmt = (s, v = {}) => String(s).replace(/\{(\w+)\}/g, (m, k) => (Object.prototype.hasOwnProperty.call(v, k) ? String(v[k]) : m));
const kodlar = () => { try { return fs.readdirSync(qovluq()).filter(f => /^[a-z]{2,3}\.json$/.test(f)).map(f => f.slice(0, -5)).sort(); } catch { return []; } };

module.exports = { dil, dilVarmi, videonunDili, fmt, kodlar, QOVLUQ };
