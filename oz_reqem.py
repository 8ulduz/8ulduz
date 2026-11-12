"""8ulduz-un öz xəbərləri, mərhələ 3: rəqəmlər (sahib, 2026-11-12: «5 qat genişləndir çeşidliliyi»).
Hava keyfiyyəti, şahmat reytinqi, texnologiya rəqəmləri və həftəlik siyahılar. Şablon xəbərlər, süni intellektsiz: hər
rəqəm, ad və tarix mənbənin həmin gün oxunan cavabındandır, vaxt Bakı vaxtıdır.

Dəqiqlik (qırmızı xətt 4): hər mənbənin cavabı özü-özünü təsdiqləməlidir (cəmlər, saylar, sıra, tarix); uyğun gəlməyən,
natamam və ya köhnə cavabdan xəbər yazılmır (worth=False, səbəbi «why»-da).

1. «Bakıda havanın keyfiyyəti» (hava-keyfiyyeti; hər gün 08:30–10:30 yoxlanır, 08:50). Open-Meteo-nun hava keyfiyyəti
   modeli, Bakı. Yalnız diqqətəlayiq gündə xəbər olur: PM2.5 və ya PM10-un orta gündəlik qatılığı ÜST-nin gündəlik
   tövsiyə həddini (15 və 45 mkq/m³) keçən ilk gün (dünən keçməyibsə) və ya Avropa hava keyfiyyəti indeksinin (EAQI)
   günün ən yüksək qiyməti «pis» (60-dan yuxarı) və daha ağır kateqoriyaya keçəndə. Model məlumatıdır, stansiya ölçməsi
   və rəsmi xəbərdarlıq deyil: mətn bunu deyir. Sorğu: gündə 1.
2. «Şahmat reytinqi» (sahmat-reytinq; ayın 1–5-i, 11:00–13:00, 11:30). FIDE-nin aylıq siyahısı: dünyanın ilk yüzlüyündə
   (açıq siyahı və qadınlar) Azərbaycanı təmsil edənlər. Siyahının başlığındakı ay cari ay olmalıdır. FIDE-nin səhifəsi
   əvvəlki ayın siyahısını vermir: kimin irəlilədiyi yazılmır. Sorğu: həmin günlərdə 2.
3. «İnternetin sürəti» (internet-sureti; ayın 10–28-i, 10:00–12:00, 10:30). Ookla-nın Speedtest Global Index səhifəsi:
   mobil və sabit internetin median sürəti və yeri, əvvəlki buraxılışla müqayisə. Yalnız səhifədəki son buraxılış ötən
   təqvim ayı olanda (yeni buraxılış); qalan günlər «hələ yoxdur». Sorğu: həmin günlərdə 1.
4. StatCounter-in aylıq payları (ayın 2-si brauzerlər, 3-ü mobil əməliyyat sistemləri, 4-ü telefon istehsalçıları;
   alınmasa 8-dək; 12:00–14:00, 12:30): ötən ayın ilk üçlüyü və bir ay əvvəllə ən böyük fərq. Ən böyük fərq 0,5 faiz
   bəndindən azdırsa xəbər yazılmır («dəyişiklik yoxdursa, yazmırıq»). Sorğu: həmin günlərdə 1–3.
5. «İstismar olunan boşluqlar» (kev-hefte; şənbə 10:30–12:30, 11:00). CISA-nın KEV kataloqu: ötən həftə (şənbə–cümə)
   əlavə olunan boşluqlar, istehsalçıları ilə. Əlavə yoxdursa xəbər yoxdur. Sorğu: şənbə 1.
6. «App Store siyahısı» (app-store; cümə 17:00–19:00, 17:30). Apple-ın açıq lenti: Azərbaycan mağazasında pulsuz
   tətbiqlərin ilk onluğu, adlar mağazadakı kimi. Sorğu: cümə 1.

Sorğular yalnız fetch ilə (15 saniyə), hər növ öz pəncərəsində və gündə bir dəfə: açar qabaqcadan bilinir və done-da
olan növə sorğu getmir. Sorğudan sonra nəticə nə olursa olsun açar qayıdır (xəbər yoxdursa worth=False): şəbəkə xətası
«<növ>-xeta-<gün>», «hələ yoxdur» «<növ>-sorgu-<gün>» açarı ilə, növbəti gün yenə yoxlanır. Gündə ən çox 8 sorğu
(adi gün 1, şənbə və cümə 2, ayın ilk günləri 4–6).
Sınaq: python oz_reqem.py --sinaq --root DIR [--now 2026-11-12T09:00+04:00]
"""
import csv
import datetime
import email.utils
import functools
import html
import io
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


def month_loc(month):
    """«oktyabrda», «apreldə», «iyunda»."""
    name = ox.MONTHS[month - 1]
    return name + ("da" if og._back(name) else "də")


def month_in(d):
    """«2026-cı ilin oktyabrında»."""
    name = ox.MONTHS[d.month - 1]
    return f"{ox.ordinal(d.year)} ilin {name}{ox._four(name, ('ında', 'ində', 'unda', 'ündə'))}"


def pct(v):
    """«78,29%», «4,5%», «2%»."""
    return oh.num(v, 2) + "%"


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


# --- 2. Şahmat: FIDE-nin aylıq siyahısı -------------------------------------------------------------------------------------

FIDE_OPEN = "https://ratings.fide.com/a_top.php?list=open"
FIDE_WOMEN = "https://ratings.fide.com/a_top.php?list=women"
FIDE_PAGE = "https://ratings.fide.com/top_lists.phtml"
FIDE_CREDIT = "Beynəlxalq Şahmat Federasiyası (FIDE)"
FIDE_DAYS = (1, 5)
FIDE_WIN = ("11:00", "13:00")
FIDE_SLOT = "11:30"
FIDE_FED = "AZE"
_EN_MONTHS = ("January", "February", "March", "April", "May", "June", "July", "August", "September", "October",
              "November", "December")
_FIDE_HEAD = re.compile(r"Top 100 (Players|Women) ([A-Z][a-z]+) (\d{4})")
_FIDE_ROW = re.compile(r'rank_span"?>\s*(\d+)\s*</span>.*?href="?/profile/(\d+)"?>([^<]+)</a>.*?flag-wrapper"?>[^<]*(?:<img[^>]*>)?'
                       r'\s*([A-Z]{3})\s*</td>.*?rating_column"?>\s*(\d{4})\s*</td>', re.S)
# FIDE nömrəsi -> adın Azərbaycan yazılışı. Yalnız 2026-11-12-də siyahıda görünən və yazılışı şübhəsiz olanlar;
# cədvəldə olmayan şahmatçının adı mənbədəki kimi (latın) yazılır.
AZ_CHESS = {
    "13401319": "Şəhriyar Məmmədyarov", "13413937": "Aydın Süleymanlı", "13400924": "Teymur Rəcəbov",
    "13409301": "Məhəmməd Muradlı", "13401653": "Rauf Məmmədov", "13403052": "Ülviyyə Fətəliyeva",
    "13413015": "Gövhər Beydullayeva", "13406396": "Xanım Balacayeva", "13403729": "Günay Məmmədzadə",
}


def fide_parse(page, kind):
    """FIDE-nin «Top 100» cədvəli -> (siyahının ayı, [{rank, id, name, fed, rating}]). kind: «Players» və ya «Women».
    1-dən başlayan ardıcıl yerlər (ən azı 100) və artmayan reytinq tələb olunur: yarımçıq cədvəldən xəbər yazılmır."""
    head = _FIDE_HEAD.search(page)
    if not head or head.group(1) != kind or head.group(2) not in _EN_MONTHS:
        raise Bad("FIDE səhifəsinin başlığı gözlənilən kimi deyil")
    month = datetime.date(int(head.group(3)), _EN_MONTHS.index(head.group(2)) + 1, 1)
    rows = []
    for part in page.split("<tr>")[1:]:
        if "rank_span" not in part:
            continue
        m = _FIDE_ROW.search(part)
        if not m:
            raise Bad("FIDE siyahısında sətir oxunmadı")
        rows.append({"rank": int(m.group(1)), "id": m.group(2), "name": " ".join(html.unescape(m.group(3)).split()),
                     "fed": m.group(4), "rating": int(m.group(5))})
    # 100-cü yerlə eyni reytinqi olanlar da cədvəldədir (2026-11: qadınlarda 101 sətir): yalnız ilk 100 yer götürülür.
    if not 100 <= len(rows) <= 130 or [r["rank"] for r in rows] != list(range(1, len(rows) + 1)):
        raise Bad("FIDE siyahısında 100 ardıcıl yer yoxdur")
    if any(a["rating"] < b["rating"] for a, b in zip(rows, rows[1:])) or not all(1800 <= r["rating"] <= 2999 for r in rows) \
            or any(r["rating"] != rows[99]["rating"] for r in rows[100:]):
        raise Bad("FIDE siyahısı reytinqə görə sıralanmayıb")
    return month, rows[:100]


def fide_name(row):
    """Azərbaycan yazılışı (cədvəldə varsa), yoxsa mənbədəki ad: «Mamedov, Rauf» -> «Rauf Mamedov»."""
    if row["id"] in AZ_CHESS:
        return AZ_CHESS[row["id"]]
    last, sep, first = row["name"].partition(",")
    return f"{first.strip()} {last.strip()}".strip() if sep else row["name"]


def fide_item(month, rows, women):
    """Ayın xəbəri: ilk yüzlükdə Azərbaycanı təmsil edənlər, yer və reytinqləri ilə."""
    key = f"sahmat-reytinq-{month:%Y-%m}"
    tail = (FIDE_CREDIT, FIDE_PAGE, "idman", FIDE_SLOT)
    mname = ox.MONTHS[month.month - 1]
    az = [r for r in rows if r["fed"] == FIDE_FED]
    azw = [r for r in women if r["fed"] == FIDE_FED]
    if not az:
        return _no("sahmat-reytinq", key, f"FIDE-nin {mname} reytinqi", "açıq siyahının ilk yüzlüyündə Azərbaycan şahmatçısı yoxdur",
                   *tail)
    n, best = len(az), az[0]
    place = lambda r: f"{ox.ordinal(r['rank'])} yer"
    pair = (f"{fide_name(best)} {ox.ordinal(best['rank'])}, {fide_name(az[1])} {place(az[1])}dədir" if n > 1 else
            f"{fide_name(best)} {place(best)}dədir")
    title = _fit((f"FIDE-nin {mname} reytinqi: dünyanın ilk yüzlüyündə {n} Azərbaycan şahmatçısı var",
                  f"{fide_name(best)} FIDE-nin {mname} reytinqində {place(best)}dədir, ilk yüzlükdə {n} Azərbaycan şahmatçısı var",
                  f"FIDE {mname} reytinqini açıqlayıb: {pair}")[month.month % 3],
                 f"FIDE-nin {mname} reytinqi: dünyanın ilk yüzlüyündə {n} Azərbaycan şahmatçısı var")
    lead = (f"Beynəlxalq Şahmat Federasiyasının (FIDE) {ox.ordinal(month.year)} ilin {mname} reytinq siyahısına görə, klassik şahmat "
            f"üzrə dünyanın ən yüksək reytinqli 100 şahmatçısı arasında Azərbaycanı ")
    if n > 1:
        lead += (f"{n} nəfər təmsil edir. Onların arasında ən yüksək yerdə {fide_name(best)} qərarlaşıb: {best['rating']} reytinq "
                 f"xalı ilə {place(best)}.")
    else:
        lead += f"bir nəfər, {fide_name(best)} təmsil edir: {best['rating']} reytinq xalı ilə {place(best)}."
    if azw:
        lead += f" Qadınların ilk yüzlüyündə Azərbaycanı {len(azw)} şahmatçı təmsil edir."
    body = [f"{place(r)}: {fide_name(r)} — {r['rating']}" for r in az]
    body += [f"Qadınlar, {place(r)}: {fide_name(r)} — {r['rating']}" for r in azw]
    return og._item("sahmat-reytinq", key, title, lead, body, *tail, lst=True)


def fide_now(now, net, done):
    day = now.date()
    month = day.replace(day=1)
    key = f"sahmat-reytinq-{month:%Y-%m}"
    if not FIDE_DAYS[0] <= day.day <= FIDE_DAYS[1] or not oh._in(now, FIDE_WIN) or _closed(done, "sahmat-reytinq", day, key):
        return []
    got, rows = fide_parse(og._text(net(FIDE_OPEN)), "Players")
    if got != month:
        return [_no("sahmat-reytinq", f"sahmat-reytinq-sorgu-{day.isoformat()}", f"FIDE-nin {ox.MONTHS[month.month - 1]} reytinqi",
                    f"FIDE-nin səhifəsində hələ {ox.MONTHS[got.month - 1]} {got.year} siyahısıdır", FIDE_CREDIT, FIDE_PAGE,
                    "idman", FIDE_SLOT)]
    got_w, women = fide_parse(og._text(net(FIDE_WOMEN)), "Women")
    if got_w != month:
        raise Bad("FIDE-nin qadınlar siyahısı başqa ayındır")
    return [fide_item(month, rows, women)]


# --- 3. İnternetin sürəti: Speedtest Global Index ---------------------------------------------------------------------------

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


# --- 4. StatCounter: brauzerlər, mobil əməliyyat sistemləri, telefon istehsalçıları ---------------------------------------------

SC_BASE = "https://gs.statcounter.com/chart.php?"
SC_CREDIT = "StatCounter Global Stats"
SC_WIN = ("12:00", "14:00")
SC_SLOT = "12:30"
SC_LAST_DAY = 8                 # ayın bu günündən sonra ötən ayın payları xəbər deyil
SC_SUM = 0.6                    # sətrin cəmi 100-dən ən çox bu qədər fərqlənə bilər (yuvarlaqlaşdırma)
SC_MIN = 0.5                    # bundan kiçik pay siyahıda yazılmır
SC_DELTA = 0.5                  # ən böyük aylıq fərq bundan kiçikdirsə xəbər yoxdur (faiz bəndi)
SC_OTHER = ("Other", "Unknown")
SC = (
    {"kind": "brauzer-payi", "day": 2, "whose": "brauzerlərin", "traffic": "veb-trafikin",
     "scope": "bütün cihazlardan veb-səhifə baxışlarında brauzerlərin payı", "unknown": "Naməlum brauzer",
     "page": "https://gs.statcounter.com/browser-market-share/all/azerbaijan",
     "query": "device=Desktop%20%26%20Mobile%20%26%20Tablet%20%26%20Console&device_hidden=desktop%2Bmobile%2Btablet%2Bconsole"
              "&multi-device=true&statType_hidden=browser&region_hidden=AZ&granularity=monthly&statType=Browser&region=Azerbaijan"},
    {"kind": "mobil-sistem-payi", "day": 3, "whose": "mobil əməliyyat sistemlərinin", "traffic": "mobil veb-trafikin",
     "scope": "mobil telefonlardan veb-səhifə baxışlarında əməliyyat sistemlərinin payı", "unknown": "Naməlum sistem",
     "page": "https://gs.statcounter.com/os-market-share/mobile/azerbaijan",
     "query": "device=Mobile&device_hidden=mobile&statType_hidden=os_combined&region_hidden=AZ&granularity=monthly"
              "&statType=Operating%20System&region=Azerbaijan"},
    {"kind": "telefon-payi", "day": 4, "whose": "telefon istehsalçılarının", "traffic": "mobil veb-trafikin",
     "scope": "mobil telefonlardan veb-səhifə baxışlarında cihaz istehsalçılarının payı",
     "unknown": "İstehsalçısı müəyyən edilməyən cihazlar",
     "page": "https://gs.statcounter.com/vendor-market-share/mobile/azerbaijan",
     "query": "device=Mobile&device_hidden=mobile&statType_hidden=vendor&region_hidden=AZ&granularity=monthly"
              "&statType=Device%20Vendor&region=Azerbaijan"},
)


def sc_url(spec, month):
    """İki tam ayın (month və ondan əvvəlki) CSV-si. Cari ay istənmir: StatCounter onu yarımçıq verir."""
    a = _prev_month(month)
    return (f"{SC_BASE}{spec['query']}&fromInt={a:%Y%m}&toInt={month:%Y%m}&fromMonthYear={a:%Y-%m}"
            f"&toMonthYear={month:%Y-%m}&csv=1")


def sc_parse(raw):
    """CSV -> (adlar, {ayın ilk günü: paylar}). Hər sətrin payları 0–100 aralığında, cəmi 100% olmalıdır."""
    table = [row for row in csv.reader(io.StringIO(og._text(raw).lstrip("﻿"))) if row]
    if not table or table[0][0].strip() != "Date" or len(table[0]) < 3:
        raise Bad("StatCounter-in cədvəli gözlənilən şəkildə deyil")
    names = [" ".join(n.split()) for n in table[0][1:]]
    if any(not n for n in names) or len(set(names)) != len(names):
        raise Bad("StatCounter-in cədvəlində sütun adları oxunmadı")
    months = {}
    for row in table[1:]:
        m = re.fullmatch(r"(\d{4})-(\d\d)", row[0].strip())
        if not m or len(row) != len(names) + 1:
            raise Bad("StatCounter-in cədvəlində sətir oxunmadı")
        vals = [oh._flt(v) for v in row[1:]]
        if any(v is None or v < 0 or v > 100 for v in vals):
            raise Bad("StatCounter-in cədvəlində pay oxunmadı")
        if abs(sum(vals) - 100) > SC_SUM:
            raise Bad("StatCounter-in cədvəlində payların cəmi 100% deyil")
        months[datetime.date(int(m.group(1)), int(m.group(2)), 1)] = vals
    return names, months


def sc_item(spec, names, months, month):
    """Ötən ayın payları: ilk üçlük və bir ay əvvəllə ən böyük fərq."""
    prev = _prev_month(month)
    kind = spec["kind"]
    key = f"{kind}-{month:%Y-%m}"
    tail = (SC_CREDIT, spec["page"], "texnologiya", SC_SLOT)
    when, when_prev = month_loc(month.month), month_loc(prev.month)
    title0 = f"Azərbaycanda {spec['whose']} payı: {ox.MONTHS[month.month - 1]}"
    if month not in months or prev not in months:
        return _no(kind, key, title0, "cədvəldə ötən ay və ya ondan əvvəlki ay yoxdur", *tail)
    rows = list(zip(names, months[month], months[prev]))
    named = sorted((r for r in rows if r[0] not in SC_OTHER), key=lambda r: (-r[1], r[0]))
    top = [r for r in named if r[1] >= SC_MIN][:3]
    if len(top) < 2:
        return _no(kind, key, title0, "cədvəldə payı 0,5%-dən böyük iki ad yoxdur", *tail)
    change = max(named, key=lambda r: (abs(round(r[1] - r[2], 2)), r[1]))
    delta = round(change[1] - change[2], 2)
    if abs(delta) < SC_DELTA:
        return _no(kind, key, title0, f"ay ərzində nəzərəçarpan dəyişiklik yoxdur: ən böyük fərq {oh.num(abs(delta), 2)} faiz bəndi "
                                      f"({change[0]})", *tail)
    shares = ", ".join(f"{n} {pct(c)}" for n, c, _ in top)
    second = f"ikinci yerdə {top[1][0]}" + (f", üçüncü yerdə {top[2][0]}" if len(top) > 2 else "")
    title = _fit((f"Azərbaycanda {spec['whose']} payı: {when} {shares}",
                  f"{top[0][0]} {when} Azərbaycanda {spec['traffic']} {pct(top[0][1])}-ni toplayıb, {second}")[month.month % 2],
                 f"Azərbaycanda {spec['whose']} payı: {when} {shares}", title0)
    lead = (f"StatCounter-in veb-səhifə baxışlarına əsaslanan statistikasına görə, {month_in(month)} Azərbaycanda {spec['scope']} "
            f"belə olub: {shares}. Bir ay əvvəllə müqayisədə ən böyük dəyişiklik {change[0]} üzrədir: pay {pct(change[2])}-dən "
            f"{pct(change[1])}-ə {'yüksəlib' if delta > 0 else 'enib'}.")
    listed = [r for r in named if r[1] >= SC_MIN]
    body = [f"{n}: {pct(c)} ({when_prev} {pct(p)})" for n, c, p in listed]
    body += [f"{spec['unknown']}: {pct(c)} ({when_prev} {pct(p)})" for n, c, p in rows if n == "Unknown" and c >= SC_MIN]
    rest = round(sum(c for n, c, _ in rows if c < SC_MIN or n == "Other"), 2)
    if rest > 0:
        body.append(f"Qalanları birlikdə: {pct(rest)}")
    return og._item(kind, key, title, lead, body, *tail, lst=True)


def sc_now(spec, now, net, done):
    day = now.date()
    month = _prev_month(day)
    key = f"{spec['kind']}-{month:%Y-%m}"
    if not spec["day"] <= day.day <= SC_LAST_DAY or not oh._in(now, SC_WIN) or _closed(done, spec["kind"], day, key):
        return []
    names, months = sc_parse(net(sc_url(spec, month)))
    return [sc_item(spec, names, months, month)]


# --- 5. İstismar olunan boşluqlar: CISA KEV ---------------------------------------------------------------------------------

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


# --- 6. App Store: Azərbaycan mağazasında pulsuz tətbiqlər --------------------------------------------------------------------

APP_URL = "https://rss.marketingtools.apple.com/api/v2/az/apps/top-free/25/apps.json"
APP_PAGE = "https://rss.marketingtools.apple.com/"
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

PARTS = (
    ("hava-keyfiyyeti", aq_now, AQ_CREDIT, AQ_PAGE, "təbiət", AQ_SLOT),
    ("sahmat-reytinq", fide_now, FIDE_CREDIT, FIDE_PAGE, "idman", FIDE_SLOT),
    ("internet-sureti", speed_now, SPEED_CREDIT, SPEED_URL, "texnologiya", SPEED_SLOT),
) + tuple((spec["kind"], functools.partial(sc_now, spec), SC_CREDIT, spec["page"], "texnologiya", SC_SLOT) for spec in SC) + (
    ("kev-hefte", kev_now, KEV_CREDIT, KEV_PAGE, "texnologiya", KEV_SLOT),
    ("app-store", app_now, APP_CREDIT, APP_PAGE, "texnologiya", APP_SLOT),
)


def _failed(kind, credit, link, topic, slot, day, err):
    """Mənbə alınmadı və ya cavabı özünü təsdiqləmədi: günün xəta açarı ilə, bu gün bir də sorğu getmir."""
    host = urllib.parse.urlsplit(link).hostname or link
    why = str(err) if isinstance(err, Bad) else f"{host} alınmadı və ya oxunmadı: {oh._err(err)}"
    return og._item(kind, f"{kind}-xeta-{day.isoformat()}", f"{credit}: məlumat alınmadı", og._cap(why) + ".", [], credit, link,
                    topic, slot, worth=False, why=why)


def _run(now, net, done):
    out = []
    for kind, build, credit, link, topic, slot in PARTS:
        try:
            out += build(now, net, done)
        except Exception as e:  # bir mənbənin xətası digərlərini saxlamır
            out.append(_failed(kind, credit, link, topic, slot, now.date(), e))
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


def _fide_sinaq(now, net):
    today = now.date()
    md = ["## 2. Şahmat: FIDE-nin aylıq siyahısı (ayın 1–5-i, 11:30)", ""]
    month, rows = fide_parse(og._text(net(FIDE_OPEN)), "Players")
    month_w, women = fide_parse(og._text(net(FIDE_WOMEN)), "Women")
    if month_w != month:
        return md + ["> Açıq siyahı ilə qadınlar siyahısının ayı fərqlidir: dərc olunmazdı.", ""]
    item = fide_item(month, rows, women)
    if item["worth"] and month != today.replace(day=1):
        item = dict(item, worth=False, why="siyahı cari ayın siyahısı deyil")
    return md + _case(f"{ox.MONTHS[month.month - 1]} {month.year} siyahısı: son real hal", item)


def _speed_sinaq(now, net):
    today = now.date()
    md = ["## 3. İnternetin sürəti: Speedtest Global Index (ayın 10–28-i, 10:30, yalnız yeni buraxılış)", ""]
    data = speed_parse(og._text(net(SPEED_URL)))
    item = speed_item(data)
    if data["month"] != _prev_month(today):
        item = dict(item, worth=False, why=f"yeni buraxılış hələ yoxdur: bu, {ox.MONTHS[data['month'].month - 1]} "
                                           f"{data['month'].year} buraxılışıdır (çıxdığı ay dərc olunardı)")
    return md + _case(f"{ox.MONTHS[data['month'].month - 1]} {data['month'].year} buraxılışı: son real hal", item)


def _sc_sinaq(now, net):
    month = _prev_month(now.date())
    md = ["## 4. StatCounter: aylıq paylar (ayın 2-si, 3-ü və 4-ü, 12:30)", ""]
    for spec in SC:
        try:
            names, months = sc_parse(net(sc_url(spec, month)))
        except Exception as e:
            md += [f"> {spec['kind']}: {e if isinstance(e, Bad) else oh._err(e)}", ""]
            continue
        md += _case(f"{ox.MONTHS[month.month - 1]} {month.year}, {spec['whose']} payı: son real hal", sc_item(spec, names, months, month))
    return md


def _kev_sinaq(now, net):
    today = now.date()
    md = ["## 5. İstismar olunan boşluqlar: CISA KEV (şənbə 11:00)", ""]
    cat = kev_parse(net(KEV_URL))
    md += [f"_Kataloqda {len(cat['rows'])} qeyd, versiya {cat['version']}._", ""]
    sat = today - DAY * ((today.weekday() - 5) % 7)
    for i, tag in enumerate(("ən son şənbə", "ondan əvvəlki şənbə", "üç həftə əvvəlki şənbə")):
        d = sat - 7 * DAY * i
        md += _case(f"{og._label(d, today)}: {tag}, bugünkü kataloqla", kev_item(cat, d, now))
    return md


def _app_sinaq(now, net):
    today = now.date()
    md = ["## 6. App Store: Azərbaycan mağazasında pulsuz tətbiqlər (cümə 17:30)", ""]
    return md + _case(f"{og._label(today, today)}: bugünkü siyahı (canlıda yalnız cümə günü)", app_item(app_parse(net(APP_URL)), today, now))


def sinaq(root, now=None, fetch=None):
    """Nümunələr (Markdown): bu an dərc olunacaqlar və hər növün ən son real halları. Sayta heç nə yazmır.
    Sorğular: Open-Meteo 1, FIDE 2, Speedtest 1, StatCounter 3, CISA 1, Apple 1."""
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
        for part in (_aq_sinaq, _fide_sinaq, _speed_sinaq, _sc_sinaq, _kev_sinaq, _app_sinaq):
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
