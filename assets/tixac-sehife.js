// Tıxac-İndi səhifəsi (#/tixac): tənbəl modul — yalnız səhifə açılanda yüklənir, ilk açılışa gəlmir
// (sahib 2026-11-19: «kodu tam incələyib artıqları təmizləyib yer açmaq lazımdır … saytın hazırki işləyişinə qəti mənfi təsir etmədən»).
// Kod app.js-dən olduğu kimi köçürülüb; əsas koddakı köməkçilər app.js-in tixHelpers() funksiyası ilə verilir.
export function view(h) {
  const { S, tixArea, geoArea, localRoadItems, roadItems, TRAFFIC_AREAS, esc, txt, safeHref, OUT, sourceName, shownSource, ago, bakuRush, TOUCH_UI, yandexSrc, wazeSrc, wazeApp, wazeLive, HOUR, loadTixac } = h;
  function trafficView() {
    const area = tixArea(), konum = geoArea();
    const items = localRoadItems(S.data?.articles || []).slice(0, 40);
    const jump = a => `<button type="button" class="pill${a.id === area.id ? " on" : ""}" data-act="tix-area" data-area="${a.id}" aria-pressed="${a.id === area.id ? "true" : "false"}">${esc(a.label)}</button>`;
    const jumps = (konum ? jump(konum) : `<button type="button" class="pill" data-act="geo"${S.geoBusy ? " disabled" : ""}>${S.geoBusy ? "Konum axtarılır…" : "📍 Konumum"}</button>`) + TRAFFIC_AREAS.map(jump).join("") + (S.geoErr && !konum ? `<span class="geo-err">${esc(S.geoErr)}</span>` : "");
    const rush = bakuRush() ? `<a class="rush" href="#/tixac">Pik saat — xəritəyə baxın</a>` : "";
    // Sahib 2026-11-14: «Waze-in mobil tətbiq xəritəsi açılsın bizdə». Telefonda da Waze-in öz xəritəsi (embed.waze.com: axtarış, tıxac
    // rəngləri, «yerim» düyməsi), səhifə açılan kimi və ekran boyu. 2026-11-04-də telefonda Waze xəritə əvəzinə «tətbiqi yüklə» göstərirdi və
    // Yandex-ə keçilmişdi; 2026-11-14-də telefon brauzerində (375 px, Android) xəritə açılır. Ehtiyat: oxucu bir toxunuşla Yandex-ə keçə bilər.
    // Xəritə yalnız bu səhifədə yüklənir (sürət: başqa səhifələrdə yoxdur).
    const map = TOUCH_UI && S.tixYandex
      ? `<iframe title="Canlı tıxac xəritəsi (Yandex)" src="${esc(yandexSrc(area))}" loading="lazy" allowfullscreen referrerpolicy="no-referrer-when-downgrade"></iframe>`
      : `<iframe title="Waze canlı xəritə" src="${esc(wazeSrc(area))}" allow="geolocation" allowfullscreen referrerpolicy="no-referrer-when-downgrade"></iframe>`;
    const rows = items.length
      ? `<ul class="tix-list">${items.map(a => `<li><a href="${safeHref(a.sourceUrl || "#")}" ${OUT}><span class="ic" aria-hidden="true">${a.icon}</span><span class="tt">${txt(a.title)}</span><span class="meta">${sourceName(shownSource(a))} · ${ago(a.publishedAt)}</span></a></li>`).join("")}</ul>`
      : `<p class="empty">Son 2 saatda Bakı və Abşeron üzrə uyğun yol xəbəri tapılmadı. Bu, yollarda tıxac olmadığı demək deyil. Cari vəziyyəti xəritədə yoxlayın.</p>`;
    return `<div class="page-h"><div><h1>Tıxac-İndi</h1><p class="sec-desc">Bakı və Abşeronun canlı yol vəziyyəti.</p></div><span class="cnt">${items.length} xəbər</span></div>
      ${rush}
      <div class="tix-jumps">${jumps}</div>
      <div class="tix-map" id="tix-map">${map}<div class="tix-bar">${TOUCH_UI ? `<button type="button" class="tix-alt" data-act="tix-yandex">${S.tixYandex ? "Waze xəritəsinə qayıt" : "Xəritə görünmür? Yandex xəritəsi"}</button><a href="${esc(wazeApp(area))}" ${OUT}>Waze tətbiqində aç</a>` : `<a href="${esc(wazeLive(area))}" ${OUT}>Xəritəni tam ekranda aç</a>`}</div></div>
      ${tixMeasure()}
      ${officialRoad()}
      <p class="tix-note">${TOUCH_UI && S.tixYandex ? "Xəritə Yandex Xəritələrdəndir." : "Xəritə Waze-dəndir."} Aşağıda son 2 saatın Bakı və Abşeron üzrə yol xəbərləri.</p>
      ${rows}`;
  }
  // Rəsmi elanlar (sahib 2026-11-14: «rəsmi kanallardan yol bağlanması və təmir elanları»): son 12 saatın yol xəbərlərindən NİİM, BNA,
  // DYP/Yol polisi və nazirliklərin elanları — mənbə qaydasından keçmiş lentdən, ayrıca sorğu yoxdur.
  const OFFICIAL_ROAD = /NİİM|İntellektual İdarəetmə|Nəqliyyat Agentliyi|\bBNA\b|\bDYP\b|yol polisi|Daxili İşlər Nazirliyi|Avtomobil Yolları/iu;
  function officialRoad() {
    const rows = roadItems(S.data?.articles || []).filter(a => Date.now() - new Date(a.publishedAt) < 12 * HOUR && OFFICIAL_ROAD.test(`${a.title} ${a.summary || ""}`)).slice(0, 6);
    if (!rows.length) return "";
    return `<section class="tix-olcu" aria-label="Rəsmi elanlar"><h2>Rəsmi elanlar</h2><ul>${rows.map(a => `<li><a href="${safeHref(a.sourceUrl || "#")}" ${OUT}>${txt(a.title)}</a> <span class="muted">${sourceName(shownSource(a))} · ${ago(a.publishedAt)}</span></li>`).join("")}</ul></section>`;
  }

  const TIX_LVL = { sixtixac: "🔴", tixac: "🟠", leng: "🟡", bagli: "⛔" };
  function tixMeasure() {
    loadTixac();
    const d = S.tix, at = d && Date.parse(d.updatedAt);
    if (!d || !(Date.now() - at < 3 * 3600e3)) return ""; // 3 saatdan köhnə ölçü göstərilmir (gecə ölçü yoxdur)
    const clock = t => new Date(t + 144e5).toISOString().slice(11, 16);
    const order = { sixtixac: 0, bagli: 1, tixac: 2, leng: 3 };
    const now = [...(d.streets || [])].sort((a, b) => (order[a.level] ?? 9) - (order[b.level] ?? 9)).slice(0, 12);
    const list = now.length
      ? `<ul class="tix-now">${now.map(s => `<li><span aria-hidden="true">${TIX_LVL[s.level] || "•"}</span><b>${esc(s.name)}</b> <span class="muted">(${esc(s.dir)})</span> — ${esc(s.text)}${s.jamKm && s.jamKm !== "0,0" && s.level !== "leng" ? `, ${esc(s.jamKm)} km` : ""}</li>`).join("")}</ul>`
      : `<p class="tix-ok">Ölçülən marşrutlarda ciddi tıxac yoxdur.</p>`;
    // Səkkiz əsas yol: hər biri, sərbəst olsa da (sahib 2026-11-14: «səkkiz əsas yol üzrə»)
    const W_TEXT = { sixtixac: "sıx tıxac", tixac: "tıxac", leng: "ləng", serbest: "sərbəst", "?": "ölçülməyib" };
    const eight = Array.isArray(d.watch) && d.watch.length ? `<h3>Səkkiz əsas yol</h3><ul class="tix-now">${d.watch.map(([n, l, k]) => `<li><span aria-hidden="true">${TIX_LVL[l] || (l === "serbest" ? "🟢" : "⚪")}</span><b>${esc(n)}</b> — ${esc(W_TEXT[l] || l)}${(l === "tixac" || l === "sixtixac") && k !== "0,0" ? `, ${esc(k)} km` : ""}</li>`).join("")}</ul>` : "";
    // Rayon balı 0–10 (35 marşrut, 2026-11-14) və bütün şəhər üzrə xülasə
    const zl = Array.isArray(d.rayons) ? d.rayons : [], zc = b => b >= 7 ? "🔴" : b >= 4 ? "🟠" : b >= 2 ? "🟡" : "🟢";
    const ray = zl.length ? `<h3>Rayonlar üzrə tıxac balı</h3><ul class="tix-now">${zl.map(([n, b, k]) => `<li><span aria-hidden="true">${zc(b)}</span><b>${esc(n)}</b> — ${b | 0}/10${k !== "0,0" ? `, ${esc(k)} km tıxac` : ""}</li>`).join("")}</ul>` : "";
    const ev = (d.events || []).slice(0, 10);
    const feed = ev.length ? `<h3>Son dəyişikliklər</h3><ul class="tix-ev">${ev.map(e => `<li class="${esc(e.kind || "")}"><time>${clock(e.t)}</time> ${esc(e.text)}</li>`).join("")}</ul>` : "";
    return `<section class="tix-olcu" aria-label="Yolların vəziyyəti"><h2>Yolların vəziyyəti <span class="muted">· ${clock(at)} ölçüsü</span></h2>${list}${ray}${eight}${feed}<p class="tix-src">Mənbə: Mapbox tıxac məlumatı, 8ulduz.az hesablaması. Pik saatlarda 6, qalan vaxt 30 dəqiqədən bir yenilənir.</p></section>`;
  }


  return trafficView();
}
