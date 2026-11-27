// Kod izləri: assets/kod.json (2026-11-27, sahib: «saytın çox sürətli işləyişini hərtərəfli təmin etmək»).
//
// GitHub Pages hər yayımda (botlar gündə 100+ dəfə yazır) BÜTÜN faylların ETag-ını dəyişir, baytlar eyni qalsa da. sw.js arxa yoxlaması
// kod faylını hər açılışda «no-cache» ilə soruşurdu: yayımdan sonra 304 əvəzinə tam 200 gəlirdi (app.min.js 62 KB, app.css 23 KB … gzip).
// İndi işçi əvvəl bu kiçik faylı soruşur (~1 KB) və saxlanmış nüsxəsinin izi buradakı ilə eyni olan faylı yenidən endirmir.
//
// kicilt.cjs hər işə düşəndə faylı yenidən yazır; tests/kod-izi.test.cjs köhnə qalanda düşür. Bir sətir — bir fayl (birləşmə rahatdır).
"use strict";
const fs = require("fs"), path = require("path"), crypto = require("crypto");

const KOD = "assets/kod.json";
// Siyahıdan kənar: content-policy.js-i idarə paneli (assets/editorial-store.js, «xəbəri çıxar») birbaşa main-ə yazır, kod.json onunla
// yenilənmir — o əvvəlki kimi hər açılışda yoxlanır. editorial-store.js və idare/ işçidən heç keçmir (sw.js inScope).
const KENAR = new Set(["assets/content-policy.js", "assets/editorial-store.js"]);
const DIRS = ["assets", "ig"];

// İşçinin (sw.js cachedShell) verdiyi, əllə yazılan kod: assets/ və ig/ içində .js/.css, bir də manifest.webmanifest.
function files(root) {
  const out = ["manifest.webmanifest"];
  for (const d of DIRS) for (const f of fs.readdirSync(path.join(root, d))) if (/\.(?:js|css)$/.test(f)) out.push(d + "/" + f);
  return out.filter(f => !KENAR.has(f) && fs.existsSync(path.join(root, f))).sort();
}
// İz: mətnin (BOM-suz, CRLF → LF) UTF-8 baytlarının SHA-256-sı, ilk 12 bayt base64url ilə (16 simvol). sw.js izOf ilə eyni.
const iz = text => crypto.createHash("sha256").update(Buffer.from(String(text).replace(/^﻿/, "").replace(/\r\n/g, "\n"), "utf8"))
  .digest().subarray(0, 12).toString("base64url");
function build(root) {
  const rows = files(root).map(f => JSON.stringify(f) + ":" + JSON.stringify(iz(fs.readFileSync(path.join(root, f), "utf8"))));
  return "{\n" + rows.join(",\n") + "\n}\n";
}

module.exports = { KOD, KENAR, files, iz, build };
