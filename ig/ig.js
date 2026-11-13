// 8ulduz.az/ig/ (sahib, 2026-11-13): Instagram profilindəki keçid bura aparır. Instagram-da paylaşılan son xəbərlər eyni sıra ilə və
// eyni şəkillə; şəklə toxunanda xəbər açılır. Siyahını «Profillərdə paylaş» işi (.github/scripts/social.cjs igGrid) «ig» budağına yazır.
// Səhifə saytın tətbiqini yükləmir, saytın sürətinə təsir etmir.
"use strict";
(function () {
  var SRC = "https://raw.githubusercontent.com/8ulduz/8ulduz/ig/ig.json";
  var grid = document.getElementById("grid");
  var safe = function (u) { return /^https:\/\//.test(String(u || "")) ? String(u) : ""; };
  function show(items) {
    grid.textContent = "";
    items.forEach(function (x) {
      var url = safe(x.url), img = safe(x.img);
      if (!url || !x.title) return;
      var a = document.createElement("a"), s = document.createElement("span");
      a.href = url; s.textContent = x.title;
      if (img) {
        var i = document.createElement("img");
        i.src = img; i.alt = x.title; i.loading = "lazy"; i.decoding = "async"; i.referrerPolicy = "no-referrer";
        i.onerror = function () { i.remove(); a.className = "noimg"; };
        a.appendChild(i);
      } else a.className = "noimg";
      a.appendChild(s);
      grid.appendChild(a);
    });
    if (!grid.children.length) fail();
  }
  function fail() { grid.innerHTML = '<p class="msg">Siyahı hələ hazır deyil. <a href="../">Bütün xəbərlər</a></p>'; }
  fetch(SRC + "?t=" + Math.floor(Date.now() / 6e4), { cache: "no-store" })
    .then(function (r) { if (!r.ok) throw 0; return r.json(); })
    .then(function (d) { show(Array.isArray(d && d.items) ? d.items : []); })
    .catch(fail);
})();
