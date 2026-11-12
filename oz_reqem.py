"""8ulduz-un öz xəbərləri, mərhələ 3: rəqəmlər (sahib, 2026-11-12: «5 qat genişləndir çeşidliliyi»).
Hava keyfiyyəti, internetin sürəti, istismar olunan boşluqlar və App Store siyahısı. Şablon xəbərlər, süni intellektsiz:
hər rəqəm, ad və tarix mənbənin həmin gün oxunan cavabındandır, vaxt Bakı vaxtıdır.

Dəqiqlik (qırmızı xətt 4): hər mənbənin cavabı özü-özünü təsdiqləməlidir (saylar, sıra, tarix, səhifənin öz göstərdiyi
rəqəmlər); uyğun gəlməyən, natamam və ya köhnə cavabdan xəbər yazılmır (worth=False, səbəbi «why»-da).

1. «Bakıda havanın keyfiyyəti» (hava-keyfiyyeti; hər gün 08:30–10:30 yoxlanır, 08:50). Open-Meteo-nun hava keyfiyyəti
   modeli, Bakı. Yalnız diqqətəlayiq gündə xəbər olur: PM2.5 və ya PM10-un orta gündəlik qatılığı ÜST-nin gündəlik
   tövsiyə həddini (15 və 45 mkq/m³) keçən ilk gün (dünən keçməyibsə) və ya Avropa hava keyfiyyəti indeksinin (EAQI)
   günün ən yüksək qiyməti «pis» (60-dan yuxarı) və daha ağır kateqoriyaya keçəndə. 2026-08-12 – 2026-11-12 dövründə
   (93 gün) bu qayda ilə 20 gün xəbər olardı; hədd isə 39 gündə (42%) keçilib, ona görə hər keçilən gün yazılmır.
   Model məlumatıdır, stansiya ölçməsi və rəsmi xəbərdarlıq deyil: mətn bunu deyir. Sorğu: gündə 1.
2. «İnternetin sürəti» (internet-sureti; ayın 10–28-i, 10:00–12:00, 10:30). Ookla-nın Speedtest Global Index səhifəsi:
   mobil və sabit internetin median sürəti və yeri, əvvəlki buraxılışla müqayisə. Yalnız səhifədəki son buraxılış ötən
   təqvim ayı olanda (yeni buraxılış); qalan günlər «hələ yoxdur». Modulun yaddaşı yoxdur: buraxılış yalnız çıxdığı
   ayın pəncərəsində (28 gündən qısa) xəbərdir, dərc hissəsi dərc olunmuş açarı 30 gün saxlayır. Sorğu: həmin günlərdə 1.
3. «İstismar olunan boşluqlar» (kev-hefte; şənbə 10:30–12:30, 11:00). CISA-nın KEV kataloqu: ötən həftə (şənbə–cümə)
   əlavə olunan boşluqlar, istehsalçıları ilə. Əlavə yoxdursa xəbər yoxdur. Sorğu: şənbə 1.
4. «App Store siyahısı» (app-store; cümə 17:00–19:00, 17:30). Apple-ın açıq lenti: Azərbaycan mağazasında pulsuz
   tətbiqlərin ilk onluğu, adlar mağazadakı kimi. Sorğu: cümə 1.

Modula daxil edilməyənlər (2026-11-12, səbəbi ilə):
- FIDE-nin aylıq reytinqi: ratings.fide.com GitHub-dan açılmır (iki sınaqda 15 saniyəlik vaxt aşımı).
- StatCounter-in aylıq payları: eyni ay üçün səhifənin cədvəli ilə qrafikin CSV-si fərqli rəqəm verir (oktyabr 2026,
  Chrome: 78,37% və 78,29%; Android: 82,5% və 82,39%). Hansının dəqiq olduğu bilinmir: dərc olunmur.
- «Bu həftə nə gözlənilir» (bazar axşamı): oz_teqvim-in bazar ertəsi 08:30 xəbəri ilə eyni məzmundur.
- APNIC IPv6 (Azərbaycanda 0,40%, dəyişmir), GitHub Innovation Graph (rüblük), ncert.az statistikası (rəqəmlərin hansı
  aya aid olduğu səhifədən sübut olunmur).

Sorğular yalnız fetch ilə (15 saniyə), hər növ öz pəncərəsində və gündə bir dəfə: açar qabaqcadan bilinir və done-da
olan növə sorğu getmir. Sorğudan sonra nəticə nə olursa olsun açar qayıdır (xəbər yoxdursa worth=False): şəbəkə xətası
«<növ>-xeta-<gün>», «hələ yoxdur» «<növ>-sorgu-<gün>» açarı ilə, növbəti gün yenə yoxlanır. Gündə ən çox 3 sorğu
(adi gün 1, ayın 10–28-i 2, həmin günlərin şənbə və cüməsi 3); bağlantı qırılanda ünvan ən çox 3 dəfə yoxlanır
(oz_gundelik._Net), vaxt aşımı və HTTP xətası təkrarlanmır.
Sınaq: python oz_reqem.py --sinaq --root DIR [--now 2026-11-12T09:00+04:00]
"""
import datetime
import email.utils
import html
import json
import pathlib
import re
import sys
import urllib.parse

import oz_gundelik as og
import oz_hava as oh
import oz_xeber as ox

BAKU = ox.BAKU
UTC = datetime.timezone.utc
DAY = datetime.timedelta(days=1)
TITLE_MAX = 110
Bad = oh.Bad


# --- Ümumi ------------------------------------------------------------------------------------------------------------------

def _prev_month(d):
    """Əvvəlki ayın ilk günü."""
    return (d.replace(day=1) - DAY).replace(day=1)


def _fit(*titles):
    """İlk sığan başlıq (TITLE_MAX); heç biri sığmırsa sonuncu (qoruyucu onu dərc etmir)."""
    for t in titles:
        if len(t) <= TITLE_MAX:
            return t
    return titles[-1]


def _no(kind, key, title, why, credit, link, topic, slot):
    """Dərc olunmayan qeyd: açar pəncərəni bağlayır, səbəb «why»-dadır."""
    return og._item(kind, key, title, og._cap(why) + ".", [], credit, link, topic, slot, worth=False, why=why)


def _closed(done, kind, day, *keys):
    """Bu gün bu növə sorğu getməməlidir: əsas açar, günün xəta açarı və ya «hələ yoxdur» açarı done-dadır."""
    iso = day.isoformat()
    return any(k in done for k in (*keys, f"{kind}-xeta-{iso}", f"{kind}-sorgu-{iso}"))


# --- 1. Bakıda havanın keyfiyyəti -------------------------------------------------------------------------------------------

AQ_LAT, AQ_LON = 40.4093, 49.8671
AQ_API = ("https://air-quality-api.open-meteo.com/v1/air-quality?latitude=40.4093&longitude=49.8671"
          "&hourly=pm10,pm2_5,european_aqi,european_aqi_pm2_5,european_aqi_pm10,european_aqi_nitrogen_dioxide,"
          "european_aqi_ozone,european_aqi_sulphur_dioxide&timezone=Asia%2FBaku&past_days={}&forecast_days=1")
AQ_PAGE = "https://open-meteo.com/en/docs/air-quality-api"
AQ_CREDIT = "Open-Meteo (model proqnozu)"
AQ_WIN = ("08:30", "10:30")
AQ_SLOT = "08:50"
AQ_PM = {"pm2_5": "PM2.5", "pm10": "PM10"}
WHO = {"pm2_5": 15.0, "pm10": 45.0}      # ÜST-nin 2021-ci il tövsiyəsi: 24 saatlıq orta, mkq/m³
AQ_SUB = (("european_aqi_pm2_5", "PM2.5 hissəcikləri"), ("european_aqi_pm10", "PM10 hissəcikləri"),
          ("european_aqi_nitrogen_dioxide", "azot dioksid"), ("european_aqi_ozone", "ozon"),
          ("european_aqi_sulphur_dioxide", "kükürd dioksid"))
# Open-Meteo-nun sənədi: 0–20 yaxşı, 20–40 qənaətbəxş, 40–60 orta, 60–80 pis, 80–100 çox pis, 100-dən yuxarı son dərəcə pis.
AQ_CATS = ((20, "yaxşı"), (40, "qənaətbəxş"), (60, "orta"), (80, "pis"), (100, "çox pis"), (None, "son dərəcə pis"))
AQ_BAD = 3                               # «pis» və daha ağır kateqoriya
AQ_MAX = 5000.0
AQ_UNITS = ("μg/m³", "µg/m³")


def aq_parse(raw):
    """Open-Meteo-nun cavabı -> {gün: {sahə: 24 saatlıq qiymət}}. Yalnız 24 saatı tam və boşluqsuz olan günlər."""
    doc = oh._json(raw)
    if not isinstance(doc, dict) or not isinstance(doc.get("hourly"), dict):
        raise Bad("Open-Meteo-nun cavabı gözlənilən şəkildə deyil")
    if doc.get("timezone") != "Asia/Baku" or doc.get("utc_offset_seconds") != 14400:
        raise Bad("Open-Meteo-nun cavabı Bakı vaxtı ilə deyil")
    lat, lon = oh._flt(doc.get("latitude")), oh._flt(doc.get("longitude"))
    if lat is None or lon is None or abs(lat - AQ_LAT) > 0.5 or abs(lon - AQ_LON) > 0.5:
        raise Bad("Open-Meteo-nun cavabı Bakı üçün deyil")
    units = doc.get("hourly_units") if isinstance(doc.get("hourly_units"), dict) else {}
    if any(units.get(f) not in AQ_UNITS for f in AQ_PM):
        raise Bad("Open-Meteo-nun cavabında ölçü vahidi mkq/m³ deyil")
    hourly = doc["hourly"]
    times = hourly.get("time")
    names = tuple(AQ_PM) + ("european_aqi",) + tuple(f for f, _ in AQ_SUB)
    if not isinstance(times, list) or any(not isinstance(hourly.get(f), list) or len(hourly[f]) != len(times) for f in names):
        raise Bad("Open-Meteo-nun cavabında saatlıq sıralar natamamdır")
    slots = {}
    for i, t in enumerate(times):
        m = re.fullmatch(r"(\d{4}-\d\d-\d\d)T(\d\d):00", str(t))
        if not m:
            raise Bad("Open-Meteo-nun cavabında vaxt oxunmadı")
        slots.setdefault(m.group(1), {})[int(m.group(2))] = i
    out = {}
    for iso, hours in slots.items():
        if sorted(hours) != list(range(24)):
            continue
        row = {f: [oh._flt(hourly[f][hours[h]]) for h in range(24)] for f in names}
        if all(v is not None and 0 <= v <= AQ_MAX for vals in row.values() for v in vals):
            out[datetime.date.fromisoformat(iso)] = row
    return out


def aq_cat(v):
    """EAQI qiyməti -> kateqoriyanın sırası (0 «yaxşı» … 5 «son dərəcə pis»)."""
    for i, (top, _) in enumerate(AQ_CATS):
        if top is None or v <= top:
            return i
    return len(AQ_CATS) - 1


def aq_day(row):
    """Günün göstəriciləri: PM-lərin orta gündəlik qatılığı (onda birə), indeksin ən yüksək qiyməti, saatı, kateqoriyası.
    ok: ümumi indeks həmin saatda alt-indekslərin ən böyüyünə bərabərdir (Open-Meteo-nun tərifi)."""
    peak = max(row["european_aqi"])
    hour = row["european_aqi"].index(peak)
    subs = [(row[f][hour], name) for f, name in AQ_SUB]
    top = max(v for v, _ in subs)
    main = [name for v, name in subs if v == top]
    return {"pm2_5": oh._r1(sum(row["pm2_5"]) / 24), "pm10": oh._r1(sum(row["pm10"]) / 24), "peak": int(round(peak)),
            "hour": hour, "cat": aq_cat(peak), "main": main[0] if len(main) == 1 else "", "ok": abs(top - peak) < 0.5}


def _ug(v):
    return f"{oh.num(v, 1)} mkq/m³"


def aq_item(days, day):
    """Günün xəbəri: yalnız həddin keçildiyi ilk gün və ya indeks «pis» və daha ağır kateqoriyaya keçəndə."""
    key = f"hava-keyfiyyeti-{day.isoformat()}"
    tail = (AQ_CREDIT, AQ_PAGE, "təbiət", AQ_SLOT)
    title0 = f"Bakıda havanın keyfiyyəti: {ox.day_text(day)}"
    if day not in days or day - DAY not in days:
        return _no("hava-keyfiyyeti", key, title0, "bu günün və ya dünənin 24 saatlıq model məlumatı tam deyil", *tail)
    t, y = aq_day(days[day]), aq_day(days[day - DAY])
    if not (t["ok"] and y["ok"]):
        return _no("hava-keyfiyyeti", key, title0, "ümumi indeks alt-indekslərin ən böyüyü ilə üst-üstə düşmür", *tail)
    cat, cat_y = AQ_CATS[t["cat"]][1], AQ_CATS[y["cat"]][1]
    over = [p for p in AQ_PM if t[p] > WHO[p]]
    start = bool(over) and not any(y[p] > WHO[p] for p in AQ_PM)
    worse = t["cat"] >= AQ_BAD and t["cat"] > y["cat"]
    if not (start or worse):
        return _no("hava-keyfiyyeti", key, title0,
                   f"diqqətəlayiq dəyişiklik yoxdur: PM2.5 {_ug(t['pm2_5'])} (dünən {_ug(y['pm2_5'])}), PM10 {_ug(t['pm10'])} "
                   f"(dünən {_ug(y['pm10'])}), indeks {t['peak']} «{cat}» (dünən {y['peak']} «{cat_y}»)", *tail)
    form = day.toordinal() % 2
    if worse:
        title = (f"Bakıda havanın keyfiyyəti bu gün «{cat}» kateqoriyasına keçəcək: model proqnozu",
                 f"Bakıda hava keyfiyyəti indeksi bu gün {t['peak']} olacaq, bu, «{cat}» kateqoriyasıdır: model proqnozu")[form]
    else:
        names = og._join([AQ_PM[p] for p in over])
        title = (f"Bakıda {names} hissəciklərinin qatılığı bu gün ÜST-nin tövsiyə həddini keçəcək: model proqnozu",
                 f"Bakının havasında {names} hissəcikləri bu gün ÜST-nin gündəlik həddindən çox olacaq: model proqnozu")[form]
    lead = (f"Open-Meteo-nun model proqnozuna görə, bu gün, {og.date_loc(day)} Bakıda PM2.5 hissəciklərinin orta gündəlik "
            f"qatılığı {_ug(t['pm2_5'])}, PM10 hissəciklərinin orta gündəlik qatılığı {_ug(t['pm10'])} olacaq. Ümumdünya Səhiyyə "
            f"Təşkilatının (ÜST) gündəlik tövsiyə həddi PM2.5 üçün {oh.num(WHO['pm2_5'], 1)}, PM10 üçün "
            f"{oh.num(WHO['pm10'], 1)} mkq/m³ təşkil edir.")
    first = (f"Avropa hava keyfiyyəti indeksinin (EAQI) gün ərzində ən yüksək qiyməti {t['peak']} olacaq (saat {t['hour']:02d}:00): "
             f"altı pilləli şkalada bu, «{cat}» kateqoriyasıdır.")
    if t["main"]:
        first += f" Həmin saatda indeksi {t['main']} müəyyən edir."
    body = [first,
            f"Dünən, {og.date_loc(day - DAY)} PM2.5 hissəciklərinin orta gündəlik qatılığı {_ug(y['pm2_5'])}, PM10 hissəciklərinin "
            f"qatılığı {_ug(y['pm10'])}, indeksin ən yüksək qiyməti {y['peak']} («{cat_y}») olub.",
            "Rəqəmlər atmosfer modelinin hesablamasıdır: ölçmə stansiyasının göstəricisi və rəsmi xəbərdarlıq deyil."]
    return og._item("hava-keyfiyyeti", key, title, lead, body, *tail)


def aq_now(now, net, done):
    day = now.date()
    if not oh._in(now, AQ_WIN) or _closed(done, "hava-keyfiyyeti", day, f"hava-keyfiyyeti-{day.isoformat()}"):
        return []
    return [aq_item(aq_parse(net(AQ_API.format(1))), day)]


# --- 2. İnternetin sürəti: Speedtest Global Index ---------------------------------------------------------------------------

SPEED_URL = "https://www.speedtest.net/global-index/azerbaijan"
SPEED_CREDIT = "Ookla, Speedtest Global Index"
SPEED_DAYS = (10, 28)
SPEED_WIN = ("10:00", "12:00")
SPEED_SLOT = "10:30"
SPEED_KINDS = ("mobileMedian", "fixedMedian")


def _js_var(page, name):
    """Səhifənin skriptindəki «var ad = {...}» obyektinin JSON-u."""
    m = re.search(r"\bvar\s+" + re.escape(name) + r"\s*=\s*", page)
    if not m:
        raise Bad(f"Speedtest səhifəsində «{name}» tapılmadı")
    try:
        obj, _ = json.JSONDecoder().raw_decode(page, m.end())
    except ValueError:
        raise Bad(f"Speedtest səhifəsində «{name}» oxunmadı")
    if not isinstance(obj, dict):
        raise Bad(f"Speedtest səhifəsində «{name}» obyekt deyil")
    return obj


def speed_parse(page):
    """Səhifə -> {month, mobileMedian: {cur, prev}, fixedMedian: {cur, prev}}; cur və prev: {down, up, rank, month}.
    Sıranın son iki ayı ardıcıl olmalı, səhifənin özünün göstərdiyi rəqəmlər (display_data) sıra ilə üst-üstə düşməlidir."""
    title = re.search(r"<title>([^<]*)</title>", page)
    name = html.unescape(title.group(1)) if title else ""
    if "Azerbaijan" not in name or "Speedtest Global Index" not in name:
        raise Bad("Speedtest səhifəsi Azərbaycanın səhifəsi deyil")
    data, shown = _js_var(page, "data"), _js_var(page, "display_data")
    out = {}
    for kind in SPEED_KINDS:
        series, disp = data.get(kind), shown.get(kind)
        if not isinstance(series, list) or not isinstance(disp, dict):
            raise Bad("Speedtest səhifəsində median sırası yoxdur")
        rows = sorted((r for r in series if isinstance(r, dict)), key=lambda r: str(r.get("month")))
        if len(rows) < 2:
            raise Bad("Speedtest səhifəsində iki ay yoxdur")
        vals = {}
        for tag, r in (("cur", rows[-1]), ("prev", rows[-2])):
            down, up, rank = oh._flt(r.get("download_mbps")), oh._flt(r.get("upload_mbps")), r.get("rank")
            if (down is None or up is None or isinstance(rank, bool) or not isinstance(rank, int)
                    or not (0 < down < 10000 and 0 < up < 10000 and 1 <= rank <= 300)):
                raise Bad("Speedtest səhifəsində sürət və ya yer oxunmadı")
            vals[tag] = {"down": down, "up": up, "rank": rank, "month": str(r.get("month"))}
        if str(rows[-1].get("prevMonth")) != vals["prev"]["month"]:
            raise Bad("Speedtest səhifəsində son iki buraxılış ardıcıl deyil")
        if (disp.get("hide_rank") or disp.get("current_rank") != vals["cur"]["rank"]
                or disp.get("previous_rank") != vals["prev"]["rank"] or oh._flt(disp.get("download_mbps")) != vals["cur"]["down"]):
            raise Bad("Speedtest səhifəsinin göstərdiyi rəqəmlər sıra ilə üst-üstə düşmür")
        out[kind] = vals
    m = re.fullmatch(r"(\d{4})-(\d\d)", out[SPEED_KINDS[0]]["cur"]["month"])
    if not m or out[SPEED_KINDS[1]]["cur"]["month"] != m.group(0):
        raise Bad("Speedtest səhifəsində mobil və sabit internetin buraxılış ayı fərqlidir")
    month = datetime.date(int(m.group(1)), int(m.group(2)), 1)
    stamp = data.get("currentMonth")
    if isinstance(stamp, bool) or not isinstance(stamp, (int, float)) or \
            datetime.datetime.fromtimestamp(stamp / 1000, UTC).date() != month:
        raise Bad("Speedtest səhifəsində cari buraxılışın tarixi sıra ilə üst-üstə düşmür")
    out["month"] = month
    return out


def mbit(v):
    return f"{ox.az_num(v, 2)} Mbit/s"


def speed_item(data):
    """Buraxılışın xəbəri: mobil və sabit internetin median sürəti və yeri, əvvəlki buraxılışla."""
    month, mob, fix = data["month"], data["mobileMedian"], data["fixedMedian"]
    mname = ox.MONTHS[month.month - 1]
    r_m, r_f = ox.ordinal(mob["cur"]["rank"]), ox.ordinal(fix["cur"]["rank"])
    title = _fit((f"Azərbaycan mobil internetin sürətinə görə dünyada {r_m}, sabit internetdə {r_f} yerdədir: Speedtest",
                  f"Speedtest: Azərbaycanda mobil internetin median sürəti {mbit(mob['cur']['down'])}, sabit internetin sürəti "
                  f"{mbit(fix['cur']['down'])}",
                  f"Speedtest reytinqinin {mname} buraxılışı: Azərbaycan mobil internetdə {r_m}, sabit internetdə {r_f} yerdədir")
                 [month.month % 3],
                 f"Speedtest reytinqinin {mname} buraxılışı: Azərbaycan mobil internetdə {r_m}, sabit internetdə {r_f} yerdədir")
    lead = (f"Ookla şirkətinin «Speedtest Global Index» reytinqinin {ox.ordinal(month.year)} il {mname} buraxılışına görə, Azərbaycan "
            f"mobil internetin median yükləmə sürətinə görə dünyada {r_m}, sabit genişzolaqlı internetin sürətinə görə {r_f} "
            f"yerdədir. Əvvəlki buraxılışda bu yerlər müvafiq olaraq {ox.ordinal(mob['prev']['rank'])} və "
            f"{ox.ordinal(fix['prev']['rank'])} idi.")
    body = [f"{label}: median yükləmə sürəti {mbit(v['cur']['down'])} (əvvəlki buraxılışda {mbit(v['prev']['down'])}), median "
            f"göndərmə sürəti {mbit(v['cur']['up'])}."
            for label, v in (("Mobil internet", mob), ("Sabit genişzolaqlı internet", fix))]
    return og._item("internet-sureti", f"internet-sureti-{month:%Y-%m}", title, lead, body, SPEED_CREDIT, SPEED_URL,
                    "texnologiya", SPEED_SLOT)


def speed_now(now, net, done):
    day = now.date()
    month = _prev_month(day)
    key = f"internet-sureti-{month:%Y-%m}"
    if not SPEED_DAYS[0] <= day.day <= SPEED_DAYS[1] or not oh._in(now, SPEED_WIN) or _closed(done, "internet-sureti", day, key):
        return []
    data = speed_parse(og._text(net(SPEED_URL)))
    if data["month"] != month:
        got = data["month"]
        return [_no("internet-sureti", f"internet-sureti-sorgu-{day.isoformat()}", f"Speedtest: {ox.MONTHS[month.month - 1]} buraxılışı",
                    f"yeni buraxılış hələ yoxdur: səhifədəki son buraxılış {ox.MONTHS[got.month - 1]} {got.year}", SPEED_CREDIT,
                    SPEED_URL, "texnologiya", SPEED_SLOT)]
    return [speed_item(data)]


# --- 3. İstismar olunan boşluqlar: CISA KEV ---------------------------------------------------------------------------------

KEV_URL = "https://www.cisa.gov/sites/default/files/feeds/known_exploited_vulnerabilities.json"
KEV_PAGE = "https://www.cisa.gov/known-exploited-vulnerabilities-catalog"
KEV_CREDIT = "CISA (ABŞ)"
KEV_WIN = ("10:30", "12:30")
KEV_SLOT = "11:00"
KEV_LINES = 15
_CVE = re.compile(r"CVE-\d{4}-\d{4,}")


def kev_parse(raw):
    """KEV kataloqu -> {rows: [{cve, vendor, product, added, ransom}], released (UTC), version}.
    «count» sahəsi qeydlərin sayına bərabər olmalıdır: yarımçıq fayldan xəbər yazılmır."""
    doc = oh._json(raw)
    rows = doc.get("vulnerabilities") if isinstance(doc, dict) else None
    if not isinstance(rows, list) or not rows:
        raise Bad("CISA kataloqu gözlənilən şəkildə deyil")
    if isinstance(doc.get("count"), bool) or doc.get("count") != len(rows):
        raise Bad("CISA kataloqunda qeydlərin sayı «count» sahəsi ilə üst-üstə düşmür")
    m = re.match(r"(\d{4})-(\d\d)-(\d\d)T(\d\d):(\d\d)", str(doc.get("dateReleased") or ""))
    if not m:
        raise Bad("CISA kataloqunun tarixi oxunmadı")
    released = datetime.datetime(*(int(x) for x in m.groups()), tzinfo=UTC)
    out = []
    for r in rows:
        if not isinstance(r, dict):
            raise Bad("CISA kataloqunda qeyd oxunmadı")
        try:
            added = datetime.date.fromisoformat(str(r.get("dateAdded")))
        except ValueError:
            raise Bad("CISA kataloqunda əlavə tarixi oxunmayan qeyd var")
        cve, vendor, product = (" ".join(str(r.get(k) or "").split()) for k in ("cveID", "vendorProject", "product"))
        out.append({"cve": cve, "vendor": vendor, "product": product, "added": added,
                    "ransom": str(r.get("knownRansomwareCampaignUse") or "") == "Known"})
    return {"rows": out, "released": released, "version": str(doc.get("catalogVersion") or "")}


def kev_item(cat, sat, now):
    """Şənbənin xəbəri: ötən həftə (şənbə–cümə) kataloqa əlavə olunan boşluqlar."""
    first, last = sat - 7 * DAY, sat - DAY
    key = f"kev-hefte-{first.isoformat()}"
    tail = (KEV_CREDIT, KEV_PAGE, "texnologiya", KEV_SLOT)
    span = og._span(first, last)
    title0 = f"İstismar olunan boşluqlar kataloqu: {span}"
    if cat["released"] > now + DAY or cat["released"].date() < max(r["added"] for r in cat["rows"]):
        return _no("kev-hefte", key, title0, "kataloqun tarixi qeydlərin tarixi ilə uyğun gəlmir", *tail)
    week = [r for r in cat["rows"] if first <= r["added"] <= last]
    if not week:
        return _no("kev-hefte", key, title0, "ötən həftə kataloqa boşluq əlavə olunmayıb", *tail)
    if any(not _CVE.fullmatch(r["cve"]) or not r["vendor"] or not r["product"] for r in week) \
            or len({r["cve"] for r in week}) != len(week):
        return _no("kev-hefte", key, title0, "həftənin qeydlərində nömrəsi, istehsalçısı və ya məhsulu oxunmayan var", *tail)
    by = {}
    for r in week:
        by.setdefault(r["vendor"], []).append(r)
    vendors = sorted(by, key=lambda v: (-len(by[v]), v.lower()))
    n, names = len(week), ", ".join(vendors[:3])
    forms = ((f"İstismar olunan boşluqlar kataloquna bir həftədə {n} qeyd əlavə olunub: {names}",
              f"İstismar olunan boşluqlar kataloquna bir həftədə {n} qeyd əlavə olunub"),
             (f"CISA bir həftədə {n} boşluğu istismar olunanlar kataloquna əlavə edib: {names}",
              f"CISA bir həftədə {n} boşluğu istismar olunanlar kataloquna əlavə edib"),
             (f"Həftənin kibertəhlükəsizlik icmalı: istismar olunan {n} yeni boşluq, siyahıda {names}",
              f"Həftənin kibertəhlükəsizlik icmalı: istismar olunan {n} yeni boşluq"))
    title = _fit(*forms[first.isocalendar()[1] % 3])
    lead = (f"ABŞ-nin Kibertəhlükəsizlik və İnfrastruktur Təhlükəsizliyi Agentliyinin (CISA) məlumatına görə, {span} tarixlərində "
            f"«İstismar olunduğu məlum olan boşluqlar» (KEV) kataloquna {n} boşluq əlavə olunub.")
    if n > 1:
        lead += (" Hamısı bir istehsalçının məhsullarına aiddir." if len(vendors) == 1 else
                 f" Onlar {len(vendors)} istehsalçının məhsullarına aiddir.")
    lead += f" Kataloqda hazırda {og._n(len(cat['rows']))} qeyd var."
    order = sorted(week, key=lambda r: (vendors.index(r["vendor"]), r["added"], r["cve"]))
    body = [f"{r['vendor']}: {r['product']} — {r['cve']} ({ox.day_text(r['added'])})" for r in order[:KEV_LINES]]
    if n > KEV_LINES:
        body.append(f"Daha {n - KEV_LINES} boşluq kataloqun səhifəsindədir.")
    ransom = sum(1 for r in week if r["ransom"])
    if ransom:
        body.append(f"Fidyə proqramı kampaniyalarında istifadəsi məlum olan boşluqların sayı: {ransom}.")
    return og._item("kev-hefte", key, title, lead, body, *tail, lst=True)


def kev_now(now, net, done):
    day = now.date()
    key = f"kev-hefte-{(day - 7 * DAY).isoformat()}"
    if day.weekday() != 5 or not oh._in(now, KEV_WIN) or _closed(done, "kev-hefte", day, key):
        return []
    return [kev_item(kev_parse(net(KEV_URL)), day, now)]


# --- 4. App Store: Azərbaycan mağazasında pulsuz tətbiqlər --------------------------------------------------------------------

APP_URL = "https://rss.marketingtools.apple.com/api/v2/az/apps/top-free/25/apps.json"
APP_PAGE = "https://apps.apple.com/az/iphone/charts/36"   # oxucu üçün: eyni siyahı App Store-un öz səhifəsində
APP_CREDIT = "Apple, App Store"
APP_WIN = ("17:00", "19:00")
APP_SLOT = "17:30"
APP_TOP = 10
APP_FRESH = datetime.timedelta(days=2)


def app_parse(raw):
    """Apple-ın lenti -> {updated (Bakı vaxtı), apps: [{name, artist, id}]}; ölkə «az», siyahı «Top Free Apps» olmalıdır."""
    doc = oh._json(raw)
    feed = doc.get("feed") if isinstance(doc, dict) else None
    if not isinstance(feed, dict) or not isinstance(feed.get("results"), list):
        raise Bad("Apple-ın siyahısı gözlənilən şəkildə deyil")
    if feed.get("country") != "az" or feed.get("title") != "Top Free Apps":
        raise Bad("Apple-ın siyahısı Azərbaycan üzrə pulsuz tətbiqlər siyahısı deyil")
    try:
        updated = email.utils.parsedate_to_datetime(str(feed.get("updated")))
    except (TypeError, ValueError):
        raise Bad("Apple-ın siyahısının tarixi oxunmadı")
    if updated.tzinfo is None:
        raise Bad("Apple-ın siyahısının tarixi vaxt qurşağısızdır")
    apps = []
    for r in feed["results"]:
        r = r if isinstance(r, dict) else {}
        name, artist, ident = (" ".join(str(r.get(k) or "").split()) for k in ("name", "artistName", "id"))
        if not (name and artist and ident):
            raise Bad("Apple-ın siyahısında adı və ya tərtibatçısı boş olan tətbiq var")
        apps.append({"name": name, "artist": artist, "id": ident})
    if len(apps) < APP_TOP or len({a["id"] for a in apps}) != len(apps):
        raise Bad("Apple-ın siyahısı natamamdır və ya təkrarlanan tətbiq var")
    return {"updated": updated.astimezone(BAKU), "apps": apps}


def app_item(data, day, now):
    """Cümənin xəbəri: siyahının ilk onluğu, adlar və tərtibatçılar mağazadakı kimi."""
    key = f"app-store-{day.isoformat()}"
    tail = (APP_CREDIT, APP_PAGE, "texnologiya", APP_SLOT)
    title0 = f"App Store-un Azərbaycan üzrə pulsuz tətbiqlər siyahısı: {ox.day_text(day)}"
    age = now - data["updated"]
    if age > APP_FRESH or age < -datetime.timedelta(hours=1):
        return _no("app-store", key, title0, f"siyahının tarixi köhnədir: {ox.day_text(data['updated'])}", *tail)
    apps = data["apps"][:APP_TOP]
    a, b, c = (x["name"] for x in apps[:3])
    title = _fit((f"App Store-un Azərbaycan üzrə pulsuz tətbiqlər siyahısında ilk üçlük: «{a}», «{b}» və «{c}»",
                  f"«{a}» App Store-un Azərbaycan üzrə pulsuz tətbiqlər siyahısında birinci yerdədir",
                  f"App Store-da bu həftə: Azərbaycan üzrə pulsuz tətbiqlər siyahısına «{a}» başçılıq edir")
                 [day.isocalendar()[1] % 3],
                 f"«{a}» App Store-un Azərbaycan üzrə pulsuz tətbiqlər siyahısında birinci yerdədir", title0)
    lead = (f"Apple-ın {ox.day_text(data['updated'])} tarixli açıq məlumatına görə, App Store-un Azərbaycan mağazasında pulsuz "
            f"tətbiqlərin siyahısına («Top Free Apps») «{a}» başçılıq edir. İkinci yerdə «{b}», üçüncü yerdə «{c}» qərarlaşıb.")
    body = [f"{i}. «{x['name']}» — {x['artist']}" for i, x in enumerate(apps, 1)]
    return og._item("app-store", key, title, lead, body, *tail, lst=True)


def app_now(now, net, done):
    day = now.date()
    if day.weekday() != 4 or not oh._in(now, APP_WIN) or _closed(done, "app-store", day, f"app-store-{day.isoformat()}"):
        return []
    return [app_item(app_parse(net(APP_URL)), day, now)]


# --- İstehsal ---------------------------------------------------------------------------------------------------------------

# (növ, qurucu, mənbənin adı, oxucu üçün keçid, mövzu, slot, sorğunun getdiyi ünvan)
PARTS = (
    ("hava-keyfiyyeti", aq_now, AQ_CREDIT, AQ_PAGE, "təbiət", AQ_SLOT, AQ_API),
    ("internet-sureti", speed_now, SPEED_CREDIT, SPEED_URL, "texnologiya", SPEED_SLOT, SPEED_URL),
    ("kev-hefte", kev_now, KEV_CREDIT, KEV_PAGE, "texnologiya", KEV_SLOT, KEV_URL),
    ("app-store", app_now, APP_CREDIT, APP_PAGE, "texnologiya", APP_SLOT, APP_URL),
)


def _failed(kind, credit, link, topic, slot, url, day, err):
    """Mənbə alınmadı və ya cavabı özünü təsdiqləmədi: günün xəta açarı ilə, bu gün bir də sorğu getmir."""
    host = urllib.parse.urlsplit(url).hostname or url
    why = str(err) if isinstance(err, Bad) else f"{host} alınmadı və ya oxunmadı: {oh._err(err)}"
    return og._item(kind, f"{kind}-xeta-{day.isoformat()}", f"{credit}: məlumat alınmadı", og._cap(why) + ".", [], credit, link,
                    topic, slot, worth=False, why=why)


def _run(now, net, done):
    out = []
    for kind, build, credit, link, topic, slot, url in PARTS:
        try:
            out += build(now, net, done)
        except Exception as e:  # bir mənbənin xətası digərlərini saxlamır
            out.append(_failed(kind, credit, link, topic, slot, url, now.date(), e))
    return out


def items(root, now, fetch=None, done=None):
    """now anında (Bakı vaxtı) pəncərəsi açıq olan növlərin xəbərləri. worth=False olanların səbəbi why-dadır.
    done: dərc olunmuş və ya qurulmuş açarlar; onların mənbəyinə sorğu getmir. Heç vaxt xəta qaldırmır."""
    try:
        now = og._now(now)
        done = set(done or ())
        net = og._Net(fetch if fetch is not None else og._default_fetch())
        return [og._guard(i) for i in _run(now, net, done) if i.get("key") not in done]
    except Exception:
        return []


# --- Sınaq ------------------------------------------------------------------------------------------------------------------

AQ_PAST = 92


def _case(label, item):
    item = og._guard(item)
    return [f"_{label}; açar `{item['key']}`, saat {item['slot']}_", ""] + ox.render(item) + [og._verdict(item), ""]


def _aq_sinaq(now, net):
    today = now.date()
    md = ["## 1. Bakıda havanın keyfiyyəti (hər gün 08:50, yalnız diqqətəlayiq gündə)", ""]
    days = aq_parse(net(AQ_API.format(AQ_PAST)))
    md += [f"_Open-Meteo-dan {len(days)} tam gün oxundu._", ""]
    md += _case(f"{og._label(today, today)}: bugünkü cavabla", aq_item(days, today))
    shown = 0
    for d in sorted(days, reverse=True):
        if d >= today:
            continue
        item = aq_item(days, d)
        if item["worth"]:
            md += _case(f"{og._label(d, today)}: son real hal (o günün səhərində «bu gün» deyə yazılardı)", item)
            shown += 1
            if shown >= 3:
                break
    if not shown:
        md += [f"> Son {AQ_PAST} gündə diqqətəlayiq gün tapılmadı.", ""]
    return md


def _speed_sinaq(now, net):
    today = now.date()
    md = ["## 2. İnternetin sürəti: Speedtest Global Index (ayın 10–28-i, 10:30, yalnız yeni buraxılış)", ""]
    data = speed_parse(og._text(net(SPEED_URL)))
    item = speed_item(data)
    if data["month"] != _prev_month(today):
        item = dict(item, worth=False, why=f"yeni buraxılış hələ yoxdur: bu, {ox.MONTHS[data['month'].month - 1]} "
                                           f"{data['month'].year} buraxılışıdır (çıxdığı ay dərc olunardı)")
    return md + _case(f"{ox.MONTHS[data['month'].month - 1]} {data['month'].year} buraxılışı: son real hal", item)


def _kev_sinaq(now, net):
    today = now.date()
    md = ["## 3. İstismar olunan boşluqlar: CISA KEV (şənbə 11:00)", ""]
    cat = kev_parse(net(KEV_URL))
    md += [f"_Kataloqda {len(cat['rows'])} qeyd, versiya {cat['version']}._", ""]
    sat = today - DAY * ((today.weekday() - 5) % 7)
    for i, tag in enumerate(("ən son şənbə", "ondan əvvəlki şənbə", "üç həftə əvvəlki şənbə")):
        d = sat - 7 * DAY * i
        md += _case(f"{og._label(d, today)}: {tag}, bugünkü kataloqla", kev_item(cat, d, now))
    return md


def _app_sinaq(now, net):
    today = now.date()
    md = ["## 4. App Store: Azərbaycan mağazasında pulsuz tətbiqlər (cümə 17:30)", ""]
    return md + _case(f"{og._label(today, today)}: bugünkü siyahı (canlıda yalnız cümə günü)", app_item(app_parse(net(APP_URL)), today, now))


def sinaq(root, now=None, fetch=None):
    """Nümunələr (Markdown): bu an dərc olunacaqlar və hər növün ən son real halları. Sayta heç nə yazmır.
    Sorğular: Open-Meteo 1, Speedtest 1, CISA 1, Apple 1."""
    try:
        now = og._now(now)
        net = og._Net(fetch if fetch is not None else og._default_fetch())
        md = [f"## Rəqəmlər: öz xəbərlər ({now:%d.%m.%Y %H:%M}, Bakı vaxtı)", "",
              "Şablon xəbərlər, süni intellektsiz: hər rəqəm, ad və tarix mənbənin özündəndir. Sayta heç nə yazılmır.", ""]
        live = items(root, now, net)
        md += ["**Bu an dərc olunacaqlar:**", ""]
        md += [f"- `{i['key']}` ({i['slot']}): {i['title']} — " + ("✅" if i["worth"] else f"⏭ {i.get('why')}")
               for i in live] or ["- yoxdur (heç bir növün pəncərəsi açıq deyil)"]
        md += [""]
        for part in (_aq_sinaq, _speed_sinaq, _kev_sinaq, _app_sinaq):
            try:
                md += part(now, net)
            except Exception as e:
                md += [f"> {part.__name__}: {e if isinstance(e, Bad) else oh._err(e)}"[:300], ""]
        md += ["## Mənbələrə çıxış (bu sınaqda)", ""]
        md += [f"- {url} — {result}" for url, result in net.log] or ["- sorğu getməyib"]
        return md + [""]
    except Exception as e:
        return [f"> Sınaq xətası: {type(e).__name__}: {e}"[:300], ""]


def _arg(argv, name):
    return argv[argv.index(name) + 1] if name in argv and argv.index(name) + 1 < len(argv) else None


def main(argv):
    if "--sinaq" not in argv:
        print(__doc__)
        return 0
    root = pathlib.Path(_arg(argv, "--root") or pathlib.Path(__file__).resolve().parent)
    when = _arg(argv, "--now")
    now = datetime.datetime.fromisoformat(when) if when else None
    sys.stdout.write("\n".join(sinaq(root, now)) + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
