// 8ulduz — nadir səhifələr: «Mənbə vəziyyəti», «Haqqımızda», «Mənim bölmələrim». app.js (pageView) bunları yalnız həmin ünvan açılanda
// yükləyir: baş səhifənin kodu kiçik qalır (ölçü limiti, docs/qirmizi-xetler.md §3). Köməkçilər app.js-dən d ilə gəlir.
export function sourcesView(d) {
  const { S, esc, sourceName, shownSource, removedSource, sourceLevel, ago, trackedSources, sectionPref, CATS, ASSISTANT_ON, DRIVER_ON, config } = d;
  const rows = (S.sources?.sources || [...new Set((S.data?.articles || []).map(shownSource))].map(name => ({name}))).filter(s => !removedSource(s));
  if (!rows) return `<div class="page-h"><div><h1>Mənbə vəziyyəti</h1><p>Lentlərin son yoxlanması</p></div></div><p class="empty">Yüklənir…</p>`;
  const label = { ok: "İşləyir", warn: "Zəif", bad: "Xəta" };
  const body = rows.map(s => {
    const lv = s.count === undefined ? "unknown" : sourceLevel(s);
    return `<li class="src-row ${lv}"><span class="src-dot" aria-hidden="true"></span><div><b>${sourceName(s.name)}</b><div class="muted">${esc(s.url || "")}</div>${s.error ? `<div class="src-err">${esc(s.error)}</div>` : ""}</div><div class="src-meta"><span>${label[lv] || "Yoxlama məlumatı yoxdur"}</span><span>${s.count === undefined ? "—" : s.count + " xəbər"}</span><time>${s.okAt ? ago(s.okAt) : "uğur yoxdur"}</time></div></li>`;
  }).join("");
  return `<div class="page-h"><div><h1>Mənbə vəziyyəti</h1><p>Yaşıl — son saatlarda xəbər gəlib. Sarı — boş və ya köhnəlmiş uğur. Qırmızı — xəta.</p></div><span class="cnt">${rows.length}</span></div><label class="source-search">Mənbə axtar <input type="search" data-source-search placeholder="Mənbənin adı…"></label><ul class="src-list">${body}</ul>`;
}

export function aboutView(d) {
  const { S, esc, sourceName, shownSource, removedSource, sourceLevel, ago, trackedSources, sectionPref, CATS, ASSISTANT_ON, DRIVER_ON, config } = d;
  const srcs = trackedSources();
  const contact = String(config.contact || "").trim();
  const gc = String(config.goatcounter || "").trim();
  return `<div class="page-h"><div><h1>Haqqımızda</h1><p>Biz kimik və sayt necə işləyir</p></div></div>
  <div class="about">
    <section><h2>Sayt nədir</h2><p>8ulduz gün ərzində onlarla saytı bir-bir açmamaq üçün qurduğumuz səhifədir. Azərbaycanın və dünyanın xəbər saytlarında nə çıxırsa, başlığı, qısa xülasəsi və şəkli ilə burada görürsünüz. Biz xəbər yazmırıq: başlığa toxunanda xəbər öz saytında açılır, tam mətni də orada oxuyursunuz. Lent hər dəqiqə təzələnir.</p></section>
    <section><h2>Mənbələr</h2><p>İndi ${srcs.length} sayt izləyirik. Hansının necə işlədiyini <a href="#/menbeler">Mənbə vəziyyəti</a> səhifəsində görə bilərsiniz.</p><div class="srcs">${srcs.map(s => `<span>${sourceName(s)}</span>`).join("")}</div></section>
    <section><h2>Necə seçirik</h2><ul>
      <li>Eyni hadisəni bir neçə sayt yazanda onları bir kartda birləşdiririk, «N mənbə» düyməsi hamısını göstərir.</li>
      <li>Baş səhifədəki böyük kart ən son xəbəri yox, son saatlarda ən çox saytın yazdığı xəbəri göstərir.</li>
      <li>Bölməni proqram özü seçir, ona görə arada səhv düşə bilər. Görsəniz, bizə yazın.</li>
      <li>Əvvəlcədən Azərbaycan dilində xəbərlər görünür. Rus, ingilis və türk dilində xəbərlər üçün yuxarıdan dili dəyişin.</li>
      <li>Ölkəmiz və dövlət rəhbərliyi barədə xəbərləri yalnız Azərbaycan saytlarından götürürük (idmanda xarici saytların klub və idmançı xəbərləri də var). Dövlət rəhbərliyini hədəf alan qərəzli materiallara yer vermirik.</li>
      <li>Məzənnə Mərkəzi Bankdandır (alınmayanda bazar məzənnəsi, yanında nişan olur), neft və bitcoin Yahoo Finance-dən, qızıl və gümüş gold-api.com-dan. Bunlar məlumat üçündür, maliyyə məsləhəti deyil.</li>
    </ul></section>
    <section><h2>Məxfilik</h2><p>Tam mətn (sayt və Android tətbiqi üçün): <a href="./mexfilik/">Məxfilik siyasəti</a>.</p><ul><li>Paylaşma düyməsi yalnız seçdiyiniz tətbiqi açır. Sayt yalnız kliklərin ümumi sayını görür, kimin nəyi paylaşdığını yox.</li><li>Səslə axtarış mikrofonu yalnız axtarış qutusundakı mikrofon düyməsinə basanda açır. Səsi brauzerinizin öz nitq tanıma xidməti (Chrome-da Google, Safari-də Apple) işləyir; səs bu sayta gəlmir və saxlanmır.</li>${ASSISTANT_ON ? `<li>Səsli köməkçi mikrofonu yalnız “Köməkçi” və ya “Danış” düyməsinə toxunanda açır. Səsin tanınması brauzerin xarici xidmətində işlənə bilər. Köməkçinin yazılı söhbəti yalnız açıq səhifənin yaddaşında qalır və sayt tərəfindən saxlanmır. Hava və namaz sorğuları müvafiq xidmətlərə seçilmiş şəhərin koordinatlarını göndərir.</li>` : ""}
      <li>Sayt kuki qoymur və hesab tələb etmir. Seçilmişlər, bölmə sırası, dil, tema və şəhər seçimi yalnız sizin cihazınızda (brauzerin yaddaşında) saxlanır.</li>
      <li>«Bildiriş» düyməsi brauzerdən icazə istəyir; bildiriş yalnız səhifə açıq olanda, cihazın özündə yaranır, heç bir serverə göndərilmir.</li>
      <li>Hava (Open-Meteo), namaz vaxtı (aladhan.com), tıxac xəritəsi (Waze; telefonda istəyə görə Yandex Xəritələr) və video (YouTube) brauzerinizdən birbaşa həmin xidmətlərə sorğu göndərir; onların öz məxfilik qaydaları tətbiq olunur. Xəritə və video yalnız düyməyə basanda yüklənir.</li><li>Konum yalnız «Konumum» düyməsinə basanda brauzerdən soruşulur və cihazınızda qalır: hava və namaz üçün ən yaxın şəhərin koordinatı, tıxac xəritəsi üçün təxminən 1 km-ə yuvarlaqlanmış nöqtə işlədilir; sayta heç nə göndərilmir.</li>
      <li>Mənbə adının yanındakı rəqəmlər bu gün / bu həftə / bu ay / bu il üzrə bütün ziyarətçilərin həmin mənbəyə keçidləridir; fərdi ziyarətçi sayı deyil. Sayım funksiyanın işə düşməsindən başlayır, 4 saata qədər gecikə bilər. Rəqəm əvəzinə tire məlumatın əlçatan olmadığını göstərir.</li>
      ${DRIVER_ON ? `<li>Sürücü rejimi sizin seçiminizlə aktivləşir. Mənbə ayrıca vərəqdə açılır; açıq məqalədən alınmış mətn bu saytda göstərilmədən cihazın Azərbaycan səsi ilə oxunur. Səs, mətn və ya fon oxuması əlçatan olmaya bilər. Ayrı mənbənin vərəqi bu sayt tərəfindən idarə olunmur.</li>` : ""}
      <li>${gc ? "Ziyarət statistikası GoatCounter ilə, kukisiz və şəxsi məlumat toplamadan aparılır." : "Ziyarət statistikası hazırda toplanmır."}</li>
    </ul></section>
    <section><h2>Əlaqə</h2><p>${contact ? `Bizə yazın: <a href="mailto:${esc(contact)}">${esc(contact)}</a>. ` : ""}Səhv, təklif və ya yeni sayt əlavə etmək istəsəniz, <a href="https://github.com/8ulduz/8ulduz/issues" target="_blank" rel="noopener noreferrer">GitHub-da</a> da yaza bilərsiniz. Xəbərlərin hüququ onları dərc edən saytlara məxsusdur. Hansısa sayt xəbərlərinin burada görünməsini istəmirsə, yazsın, siyahıdan çıxararıq.</p></section>
  </div>`;
}

export function sectionsView(d) {
  const { S, esc, sourceName, shownSource, removedSource, sourceLevel, ago, trackedSources, sectionPref, CATS, ASSISTANT_ON, DRIVER_ON, config } = d;
  const { order, off } = sectionPref();
  const hide = new Set(off);
  const rows = order.map((slug, i) => {
    const c = CATS.find(x => x.slug === slug);
    if (!c) return "";
    const on = !hide.has(slug);
    return `<li data-cat="${esc(slug)}"><button type="button" data-act="sec-up" data-slug="${esc(slug)}" ${i === 0 ? "disabled" : ""} aria-label="Yuxarı">↑</button><button type="button" data-act="sec-down" data-slug="${esc(slug)}" ${i === order.length - 1 ? "disabled" : ""} aria-label="Aşağı">↓</button><button type="button" class="chk${on ? " on" : ""}" data-act="sec-toggle" data-slug="${esc(slug)}" aria-pressed="${on ? "true" : "false"}">${on ? "✓" : ""}</button><a href="/bolme/${esc(slug)}/"><i class="cdot"></i>${esc(c.label)}</a><span>${esc(c.description)}</span></li>`;
  }).join("");
  return `<div class="page-h"><div><h1>Mənim bölmələrim</h1><p>İşarəni götürün və ya sıranı dəyişin. Baş səhifə bunu yadda saxlayır.</p></div></div><ul class="mine">${rows}</ul>`;
}
