"""Səma xəbərləri (oz_sema.py): Ay fazaları, gündönümü və bərabərlik, Bakıda gün batımı, meteor axınları, tutulmalar.

Sahibin «Bəli, başla» qərarı (2026-11-10), 1-ci mərhələ: süni intellektsiz şablon xəbər. Sayta hələ qoşulmayıb.
- Hesablama yerlidir: istehsalda sorğu yoxdur.
  - Ay fazaları: Meeus, «Astronomical Algorithms», 49-cu fəsil.
  - Gündönümü və bərabərlik: Meeus, 27-ci fəsil; 2026–2030 üçün dəqiq anlar JPL Horizons-dan (SEASONS_JPL).
  - Günəşin doğma və batma vaxtı: NOAA tənlikləri, Bakı (40,4093 şm. e., 49,8671 şq. u.).
  - Ayın işıqlı hissəsi: Meeus, 48-ci fəsil.
- Meteor axınları («böyük dördlük») və tutulmalar 2026–2027 üçün statik cədvəldir: IMO təqvimi, NASA cədvəlləri.
  Bakıdan görünmə yalnız hesablanıbsa yazılır: Günəş tutulması üçün JPL Horizons efemeridləri ilə.
- tests/test_oz_sema.py hesablamanı USNO və JPL cədvəlləri ilə yoxlayır (tests/fixtures/oz_sema/).
"""
import datetime
import math
import pathlib
import sys

import oz_xeber as ox

BAKU = ox.BAKU
UTC = datetime.timezone.utc
LAT, LON = 40.4093, 49.8671   # Bakı
TZ_MIN = 240                  # Bakı vaxtı UTC+4, yay vaxtı yoxdur
DELTA_T = 69.2                # TT − UT1, saniyə (2026–2027; IERS: 69,1–69,3)
UNIX_JD = 2440587.5
J2000 = 2451545.0
TOPIC = "kosmos"
DAY_CAP = 2                   # plan: kosmos gündə ən çox 2 xəbər
CREDIT = "Astronomik hesablama"
USNO_PHASES = "https://aa.usno.navy.mil/data/MoonPhases"
USNO_SEASONS = "https://aa.usno.navy.mil/data/Earth_Seasons"
USNO_SUN = "https://aa.usno.navy.mil/data/RS_OneDay"
# Dərc vaxtları (Bakı). Ay fazası 08:15-də (brif); eyni gündə ikinci kosmos xəbəri onun ardınca gəlməsin deyə fəsil 09:30-da,
# gün batımı isə günortadan sonra, batmadan əvvəl.
SLOT = {"ay": "08:15", "fesil": "09:30", "batim": "16:30", "meteor-onizleme": "12:15", "meteor": "18:15",
        "tutulma": "08:30", "tutulma-gece": "18:30", "tutulma-onizleme": "12:30"}


def _sin(x):
    return math.sin(math.radians(x))


def _cos(x):
    return math.cos(math.radians(x))


def jd_of(dt):
    """Aware datetime -> Yulian günü (UT)."""
    return dt.timestamp() / 86400.0 + UNIX_JD


def dt_of(jd):
    """Yulian günü (UT) -> UTC datetime."""
    return datetime.datetime.fromtimestamp((jd - UNIX_JD) * 86400.0, tz=UTC)


def to_minute(dt):
    """Ən yaxın dəqiqəyə: 30 saniyə və çoxu yuxarı."""
    return (dt + datetime.timedelta(seconds=30)).replace(second=0, microsecond=0)


def baku_minute(dt):
    return to_minute(dt).astimezone(BAKU)


def _at(day, hm):
    """Bakı tarixi və «HH:MM» -> aware datetime."""
    h, m = hm.split(":")
    return datetime.datetime(day.year, day.month, day.day, int(h), int(m), tzinfo=BAKU)


# --- Ay fazaları: Meeus 49 -------------------------------------------------------------------------------------

# Düzəliş əmsalları: (əmsal, E-nin dərəcəsi). Arqumentlər _args_nf (yeni Ay, bədir) və _args_q (rüblər) sırasındadır.
_NEW = ((-0.40720, 0), (0.17241, 1), (0.01608, 0), (0.01039, 0), (0.00739, 1), (-0.00514, 1), (0.00208, 2), (-0.00111, 0),
        (-0.00057, 0), (0.00056, 1), (-0.00042, 0), (0.00042, 1), (0.00038, 1), (-0.00024, 1), (-0.00017, 0), (-0.00007, 0),
        (0.00004, 0), (0.00004, 0), (0.00003, 0), (0.00003, 0), (-0.00003, 0), (0.00003, 0), (-0.00002, 0), (-0.00002, 0),
        (0.00002, 0))
_FULL = ((-0.40614, 0), (0.17302, 1), (0.01614, 0), (0.01043, 0), (0.00734, 1), (-0.00515, 1), (0.00209, 2), (-0.00111, 0),
         (-0.00057, 0), (0.00056, 1), (-0.00042, 0), (0.00042, 1), (0.00038, 1), (-0.00024, 1), (-0.00017, 0), (-0.00007, 0),
         (0.00004, 0), (0.00004, 0), (0.00003, 0), (0.00003, 0), (-0.00003, 0), (0.00003, 0), (-0.00002, 0), (-0.00002, 0),
         (0.00002, 0))
_QUARTER = ((-0.62801, 0), (0.17172, 1), (-0.01183, 1), (0.00862, 0), (0.00804, 0), (0.00454, 1), (0.00204, 2), (-0.00180, 0),
            (-0.00070, 0), (-0.00040, 0), (-0.00034, 1), (0.00032, 1), (0.00032, 1), (-0.00028, 2), (0.00027, 1), (-0.00017, 0),
            (-0.00005, 0), (0.00004, 0), (-0.00004, 0), (0.00004, 0), (0.00003, 0), (0.00003, 0), (0.00002, 0), (0.00002, 0),
            (-0.00002, 0))
# Planet arqumentləri A1..A14: (başlanğıc, k əmsalı, amplituda, milyonda bir gün). A1-də əlavə −0,009173·T² var.
_PLANET = ((299.77, 0.107408, 325), (251.88, 0.016321, 165), (251.83, 26.651886, 164), (349.42, 36.412478, 126),
           (84.66, 18.206239, 110), (141.74, 53.303771, 62), (207.14, 2.453732, 60), (154.84, 7.306860, 56),
           (34.52, 27.261239, 47), (207.19, 0.121824, 42), (291.34, 1.844379, 40), (161.72, 24.198154, 37),
           (239.56, 25.513099, 35), (331.55, 3.592518, 23))


def _args_nf(mp, m, f, om):
    return (mp, m, 2 * mp, 2 * f, mp - m, mp + m, 2 * m, mp - 2 * f, mp + 2 * f, 2 * mp + m, 3 * mp, m + 2 * f, m - 2 * f,
            2 * mp - m, om, mp + 2 * m, 2 * mp - 2 * f, 3 * m, mp + m - 2 * f, 2 * mp + 2 * f, mp + m + 2 * f, mp - m + 2 * f,
            mp - m - 2 * f, 3 * mp + m, 4 * mp)


def _args_q(mp, m, f, om):
    return (mp, m, mp + m, 2 * mp, 2 * f, mp - m, 2 * m, mp - 2 * f, mp + 2 * f, 3 * mp, 2 * mp - m, m + 2 * f, m - 2 * f,
            mp + 2 * m, 2 * mp + m, om, mp - m - 2 * f, 2 * mp + 2 * f, mp + m + 2 * f, mp - 2 * m, mp + m - 2 * f, 3 * m,
            2 * mp - 2 * f, mp - m + 2 * f, 3 * mp + m)


def phase_jde(n, q):
    """n-ci lunasiyanın fazası, JDE (TT). q: 0 yeni Ay, 1 birinci rüb, 2 bədir, 3 son rüb."""
    k = n + q / 4.0
    t = k / 1236.85
    jde = 2451550.09766 + 29.530588861 * k + 0.00015437 * t ** 2 - 0.000000150 * t ** 3 + 0.00000000073 * t ** 4
    e = 1 - 0.002516 * t - 0.0000074 * t ** 2
    m = 2.5534 + 29.10535670 * k - 0.0000014 * t ** 2 - 0.00000011 * t ** 3
    mp = 201.5643 + 385.81693528 * k + 0.0107582 * t ** 2 + 0.00001238 * t ** 3 - 0.000000058 * t ** 4
    f = 160.7108 + 390.67050284 * k - 0.0016118 * t ** 2 - 0.00000227 * t ** 3 + 0.000000011 * t ** 4
    om = 124.7746 - 1.56375588 * k + 0.0020672 * t ** 2 + 0.00000215 * t ** 3
    if q in (0, 2):
        args, coef = _args_nf(mp, m, f, om), (_NEW if q == 0 else _FULL)
    else:
        args, coef = _args_q(mp, m, f, om), _QUARTER
    c = sum(a * e ** p * _sin(x) for (a, p), x in zip(coef, args))
    if q in (1, 3):
        w = (0.00306 - 0.00038 * e * _cos(m) + 0.00026 * _cos(mp) - 0.00002 * _cos(mp - m) + 0.00002 * _cos(mp + m)
             + 0.00002 * _cos(2 * f))
        c += w if q == 1 else -w
    for i, (a0, a1, amp) in enumerate(_PLANET):
        c += amp * 1e-6 * _sin(a0 + a1 * k - (0.009173 * t ** 2 if i == 0 else 0.0))
    return jde + c


def phases(start, end):
    """[start, end) aralığındakı fazalar: [(q, UTC datetime)], vaxta görə."""
    out = []
    n = int(math.floor((jd_of(start) - 2451550.09766) / 29.530588861)) - 1
    while True:
        for q in range(4):
            when = dt_of(phase_jde(n, q) - DELTA_T / 86400.0)
            if when >= end:
                return out
            if when >= start:
                out.append((q, when))
        n += 1


def baku_phases(day, days):
    """Bakı tarixi ilə day-dən başlayan days gündəki fazalar: [(q, Bakı vaxtı, dəqiqəyə yuvarlaq)]."""
    a = _at(day, "00:00") - datetime.timedelta(hours=1)
    b = a + datetime.timedelta(days=days, hours=2)
    last = day + datetime.timedelta(days=days)
    return [(q, t) for q, t in ((q, baku_minute(w)) for q, w in phases(a, b)) if day <= t.date() < last]


def moon_illum(when):
    """Ayın işıqlı hissəsi, 0..1 (Meeus 48, sadələşdirilmiş). JPL Horizons ilə fərq 0,3 faiz bəndindən azdır."""
    t = (jd_of(when) + DELTA_T / 86400.0 - J2000) / 36525.0
    d = 297.8501921 + 445267.1114034 * t - 0.0018819 * t ** 2 + t ** 3 / 545868 - t ** 4 / 113065000
    m = 357.5291092 + 35999.0502909 * t - 0.0001536 * t ** 2 + t ** 3 / 24490000
    mp = 134.9633964 + 477198.8675055 * t + 0.0087414 * t ** 2 + t ** 3 / 69699 - t ** 4 / 14712000
    i = (180 - d - 6.289 * _sin(mp) + 2.100 * _sin(m) - 1.274 * _sin(2 * d - mp) - 0.658 * _sin(2 * d)
         - 0.214 * _sin(2 * mp) - 0.110 * _sin(d))
    return (1 + _cos(i)) / 2


# --- Gündönümü və bərabərlik: Meeus 27 ---------------------------------------------------------------------------

_SEASON0 = ((2451623.80984, 365242.37404, 0.05169, -0.00411, -0.00057),
            (2451716.56767, 365241.62603, 0.00325, 0.00888, -0.00030),
            (2451810.21715, 365242.01767, -0.11575, 0.00337, 0.00078),
            (2451900.05952, 365242.74049, -0.06223, -0.00823, 0.00032))
_SEASON_S = ((485, 324.96, 1934.136), (203, 337.23, 32964.467), (199, 342.08, 20.186), (182, 27.85, 445267.112),
             (156, 73.14, 45036.886), (136, 171.52, 22518.443), (77, 222.54, 65928.934), (74, 296.72, 3034.906),
             (70, 243.58, 9037.513), (58, 119.81, 33718.147), (52, 297.17, 150.678), (50, 21.02, 2281.226),
             (45, 247.54, 29929.562), (44, 325.15, 31555.956), (29, 60.93, 4443.417), (18, 155.12, 67555.328),
             (17, 288.79, 4562.452), (16, 198.04, 62894.029), (14, 199.76, 31436.921), (12, 95.39, 14577.848),
             (12, 287.11, 31931.756), (12, 320.81, 34777.259), (9, 227.73, 1222.114), (8, 15.45, 16859.074))
# Meeus-un xətası ±35 saniyəyədir: dəqiqə sərhədində göstərilən vaxtı dəyişə bilər (2027-09-23: 10:01, əslində 10:02).
# Ona görə 2026–2030 anları JPL Horizons-dan götürülüb: Günəşin görünən ekliptik uzunluğu 0°, 90°, 180°, 270°, UT.
SEASONS_JPL = {
    2026: ("2026-03-20T14:45:59", "2026-06-21T08:24:32", "2026-09-23T00:05:14", "2026-12-21T20:50:15"),
    2027: ("2027-03-20T20:24:43", "2027-06-21T14:10:51", "2027-09-23T06:01:44", "2027-12-22T02:42:11"),
    2028: ("2028-03-20T02:17:09", "2028-06-20T20:02:01", "2028-09-22T11:45:19", "2028-12-21T08:19:41"),
    2029: ("2029-03-20T08:02:00", "2029-06-21T01:48:19", "2029-09-22T17:38:31", "2029-12-21T14:14:07"),
    2030: ("2030-03-20T13:52:07", "2030-06-21T07:31:20", "2030-09-22T23:26:54", "2030-12-21T20:09:39"),
}
SEASON_NAME = ("yaz bərabərliyi", "yay gündönümü", "payız bərabərliyi", "qış gündönümü")
SEASON_SLUG = ("yaz-beraberliyi", "yay-gundonumu", "payiz-beraberliyi", "qis-gundonumu")


def season_jde(year, i):
    """i: 0 yaz bərabərliyi, 1 yay gündönümü, 2 payız bərabərliyi, 3 qış gündönümü. JDE (TT)."""
    y = (year - 2000) / 1000.0
    c = _SEASON0[i]
    jde0 = c[0] + c[1] * y + c[2] * y ** 2 + c[3] * y ** 3 + c[4] * y ** 4
    t = (jde0 - J2000) / 36525.0
    w = 35999.373 * t - 2.47
    dl = 1 + 0.0334 * _cos(w) + 0.0007 * _cos(2 * w)
    s = sum(a * _cos(b + cc * t) for a, b, cc in _SEASON_S)
    return jde0 + 0.00001 * s / dl


def season(year, i):
    """Fəslin anı, UTC: JPL cədvəlində varsa ondan, yoxsa Meeus."""
    row = SEASONS_JPL.get(year)
    if row:
        return datetime.datetime.fromisoformat(row[i]).replace(tzinfo=UTC)
    return dt_of(season_jde(year, i) - DELTA_T / 86400.0)


# --- Günəş: NOAA ---------------------------------------------------------------------------------------------------

def sun_pos(jd):
    """Günəşin meyli (dərəcə) və zaman tənliyi (dəqiqə)."""
    t = (jd - J2000) / 36525.0
    l0 = (280.46646 + t * (36000.76983 + t * 0.0003032)) % 360.0
    m = 357.52911 + t * (35999.05029 - 0.0001537 * t)
    e = 0.016708634 - t * (0.000042037 + 0.0000001267 * t)
    c = (_sin(m) * (1.914602 - t * (0.004817 + 0.000014 * t)) + _sin(2 * m) * (0.019993 - 0.000101 * t)
         + _sin(3 * m) * 0.000289)
    om = 125.04 - 1934.136 * t
    lam = l0 + c - 0.00569 - 0.00478 * _sin(om)
    eps = 23 + (26 + (21.448 - t * (46.815 + t * (0.00059 - t * 0.001813))) / 60) / 60 + 0.00256 * _cos(om)
    dec = math.degrees(math.asin(_sin(eps) * _sin(lam)))
    y = math.tan(math.radians(eps / 2)) ** 2
    eqt = 4 * math.degrees(y * _sin(2 * l0) - 2 * e * _sin(m) + 4 * e * y * _sin(m) * _cos(2 * l0)
                           - 0.5 * y * y * _sin(4 * l0) - 1.25 * e * e * _sin(2 * m))
    return dec, eqt


def sun_event(day, rise, lat=LAT, lon=LON):
    """Günəşin doğma (rise=True) və ya batma anı, Bakı vaxtı (saniyəli). Günəş doğmursa və ya batmırsa None."""
    midnight = _at(day, "00:00")
    jd0 = jd_of(midnight)
    t = 720.0  # yerli gecəyarısından dəqiqə; ilk təxmin günorta, sonra hadisənin öz anında iki dəfə dəqiqləşir
    for _ in range(3):
        dec, eqt = sun_pos(jd0 + t / 1440.0)
        cos_h = _cos(90.833) / (_cos(lat) * _cos(dec)) - math.tan(math.radians(lat)) * math.tan(math.radians(dec))
        if cos_h < -1 or cos_h > 1:
            return None
        h = math.degrees(math.acos(cos_h))
        noon = 720 - 4 * lon - eqt + TZ_MIN
        t = noon - 4 * h if rise else noon + 4 * h
    return midnight + datetime.timedelta(minutes=t)


def sun_alt(when, lat=LAT, lon=LON):
    """Günəşin hündürlüyü (dərəcə, refraksiyasız)."""
    jd = jd_of(when)
    dec, eqt = sun_pos(jd)
    tst = (((jd - 0.5) % 1.0) * 1440.0 + eqt + 4 * lon) % 1440.0
    cz = _sin(lat) * _sin(dec) + _cos(lat) * _cos(dec) * _cos(tst / 4.0 - 180.0)
    return 90.0 - math.degrees(math.acos(max(-1.0, min(1.0, cz))))


def day_info(day):
    """Bakıda doğma və batma (dəqiqəyə yuvarlaq), gündüzün uzunluğu: göstərilən iki vaxtın fərqi, mətnlə uyğun olsun."""
    rise, sset = sun_event(day, True), sun_event(day, False)
    if rise is None or sset is None:
        return None
    r, s = to_minute(rise), to_minute(sset)
    return {"rise": r, "set": s, "length": s - r}


# --- Azərbaycan yazısı -------------------------------------------------------------------------------------------

def _cap1(s):
    return s[:1].upper() + s[1:]


def dur_text(td):
    """«9 saat 17 dəqiqə», «12 saat»."""
    h, m = divmod(int(round(td.total_seconds() / 60.0)), 60)
    return f"{h} saat {m} dəqiqə" if m else f"{h} saat"


def _hm_loc(t):
    """«17:17-də» («saat» sözü olmadan)."""
    return ox.time_loc(t)[len("saat "):]


def _until(d, year=None):
    """«15 oktyabradək», «30 aprelədək»; başqa ildirsə «2027-ci il 2 fevraladək»."""
    text = f"{d.day} {ox.MONTHS[d.month - 1]}{'ədək' if d.month == 4 else 'adək'}"
    return f"{ox.ordinal(d.year)} il {text}" if year is not None and d.year != year else text


def _range_text(a, b):
    """«4–20 dekabr», «28 dekabr – 12 yanvar»."""
    if a.month == b.month:
        return f"{a.day}–{b.day} {ox.MONTHS[a.month - 1]}"
    return f"{ox.day_text(a)} – {ox.day_text(b)}"


def _pct(x):
    return f"{ox.az_num(round(x * 100), 0)}%"


# --- 1. Ay fazası ------------------------------------------------------------------------------------------------

PHASE_LABEL = ("Yeni Ay", "Birinci rüb", "Bədirlənmə", "Son rüb")
PHASE_SLUG = ("yeni-ay", "birinci-rub", "bedir", "son-rub")
_PRED = (("yeni Ay olacaq", "yeni Ay olub"), ("birinci rübə çatacaq", "birinci rübə çatıb"),
         ("bədirlənəcək", "bədirlənib"), ("son rübə çatacaq", "son rübə çatıb"))


def _phase_text(q, when, future):
    """«Ay 17 noyabrda ... birinci rübə çatacaq»; yeni Ay üçün «9 noyabrda ... yeni Ay olacaq»."""
    pred = _PRED[q][0 if future else 1]
    return f"{when} {pred}" if q == 0 else f"Ay {when} {pred}"


def moon_item(q, t, after, ref, nth=0):
    """t: fazanın Bakı vaxtı; after: [(q, t)] sonrakı fazalar; ref: dərc anı (keçmiş və ya gələcək zaman üçün);
    nth: bədir üçün ilin neçənci bədirlənməsidir."""
    future = t > ref
    title = _cap1(_phase_text(q, f"bu gün {ox.time_loc(t)}", future))
    lead = "Hesablamalara görə, " + _phase_text(q, f"{ox.day_loc(t)} Bakı vaxtı ilə {ox.time_loc(t)}", future) + "."
    if q == 2 and nth:
        lead += f" Bu, {ox.ordinal(t.year)} ilin {ox.ordinal(nth)} bədirlənməsidir."
    body = [f"{PHASE_LABEL[q2]}: {ox.day_text(t2)}, saat {t2:%H:%M}" for q2, t2 in after[:3]]
    return {"kind": "ay-faza", "key": f"sema-ay-{t:%Y-%m-%d}-{PHASE_SLUG[q]}", "title": title, "lead": lead,
            "body": body, "list": True, "credit": CREDIT, "link": USNO_PHASES, "topic": TOPIC, "slot": SLOT["ay"],
            "worth": True}


def moon_items(day, now):
    out = []
    for q, t in baku_phases(day, 1):
        after = [x for x in baku_phases(day, 40) if x[1] > t][:3]
        nth = 0
        if q == 2:
            jan1 = datetime.date(t.year, 1, 1)
            nth = sum(1 for q2, t2 in baku_phases(jan1, (day - jan1).days + 1) if q2 == 2)
        item = moon_item(q, t, after, max(now, _at(day, SLOT["ay"])), nth)
        ecl = eclipse_at_phase(q, t)
        if ecl:
            item["worth"], item["why"] = False, f"{ecl['name']} xəbərində var: bir hadisə, bir xəbər"
        out.append(item)
    return out


# --- 2. Gündönümü, bərabərlik və gün batımı ---------------------------------------------------------------------

def season_item(i, t, info, later, later_info, ref):
    future = t > ref
    verb = "olacaq" if future else "olub"
    name = SEASON_NAME[i]
    body = [f"Bakıda bu gün Günəş {ox.time_loc(info['rise'])} doğur, {_hm_loc(info['set'])} batır; "
            f"gündüz {dur_text(info['length'])} çəkir."]
    if later_info:
        body.append(f"Bir həftə sonra, {ox.day_loc(later)} gündüz {dur_text(later_info['length'])} çəkəcək.")
    return {"kind": "fesil", "key": f"sema-fesil-{t.year}-{SEASON_SLUG[i]}",
            "title": f"Bu gün {ox.time_loc(t)} {name} {verb}: Bakıda gündüz {dur_text(info['length'])} çəkir",
            "lead": f"Hesablamalara görə, {name} {ox.day_loc(t)} Bakı vaxtı ilə {ox.time_loc(t)} {verb}.",
            "body": body, "credit": CREDIT, "link": USNO_SEASONS, "topic": TOPIC, "slot": SLOT["fesil"], "worth": True}


def season_items(day, now):
    out = []
    for i in range(4):
        t = baku_minute(season(day.year, i))
        if t.date() != day:
            continue
        info = day_info(day)
        if not info:
            continue
        later = day + datetime.timedelta(days=7)
        out.append(season_item(i, t, info, later, day_info(later), max(now, _at(day, SLOT["fesil"]))))
    return out


SUNSET_HOURS = (18, 20)  # 19:00 bərabərliklərin həftəsinə düşür: o həftə fəsil xəbəri artıq var


def _mins(t):
    return t.hour * 60 + t.minute


def _regime_end(day, lim, up):
    """Günəş limitdən sonra (up) və ya əvvəl batmağa davam edən son gün."""
    last = day
    for n in range(1, 400):
        d = day + datetime.timedelta(days=n)
        info = day_info(d)
        if not info or not (_mins(info["set"]) > lim if up else _mins(info["set"]) < lim):
            return last
        last = d
    return last


def sunset_item(day, h, up, info, prev, last, ref):
    """ref: dərc anı. Rejimin sonu öz cümləsidir: «Bu, ... davam edəcək» doğma vaxtından sonra ona aid oxunurdu."""
    lim = datetime.time(h, 0)
    side = "sonra" if up else "əvvəl"
    verb = "batacaq" if info["set"] > ref else "batıb"  # dərc gecikib, Günəş artıq batıbsa
    body = [f"Günəş {_until(last, day.year)} hər gün {ox.time_loc(lim)}n {side} batacaq.",
            f"Bu gün Günəş {ox.time_loc(info['rise'])} doğur, gündüz {dur_text(info['length'])} çəkir."]
    return {"kind": "gun-batimi", "key": f"sema-batim-{day:%Y-%m-%d}-{h}",
            "title": f"Bakıda Günəş bu gündən etibarən {ox.time_loc(lim)}n {side} batacaq",
            "lead": (f"Hesablamalara görə, Bakıda Günəş bu gün {ox.time_loc(info['set'])} {verb}; "
                     f"dünən {_hm_loc(prev['set'])} batmışdı."),
            "body": body, "credit": CREDIT, "link": USNO_SUN, "topic": TOPIC, "slot": SLOT["batim"], "worth": True}


def sunset_items(day, now):
    info, prev = day_info(day), day_info(day - datetime.timedelta(days=1))
    if not info or not prev:
        return []
    a, b = _mins(prev["set"]), _mins(info["set"])
    ref = max(now, _at(day, SLOT["batim"]))
    out = []
    for h in SUNSET_HOURS:
        lim = h * 60
        if a <= lim < b or a >= lim > b:
            up = b > lim
            out.append(sunset_item(day, h, up, info, prev, _regime_end(day, lim, up), ref))
    return out


# --- 3. Meteor axınları ------------------------------------------------------------------------------------------

IMO = "Beynəlxalq Meteor Təşkilatı (IMO)"
IMO_PDF = "https://www.imo.net/files/meteor-shower/cal{}.pdf"
SHOWER_NAME = {"QUA": "Kvadrantid", "ETA": "Eta-Akvarid", "PER": "Perseid", "GEM": "Geminid"}
# «Böyük dördlük» (plan: «Meteor showers: only the big four»): IMO-nun 5-ci cədvəlində ZHR-i ən yüksək dörd gecə axını.
# (kod, IMO təqviminin ili, aktivlik başlanğıcı, sonu, maksimum UTC, maksimumun sonu (aralıqdırsa), ZHR, IMO «80+» yazıbmı,
#  müşahidə gecəsi: Bakı vaxtı ilə maksimuma ən yaxın səhər 03:00-ın əvvəlki axşamı). Mənbə: IMO cal2026.pdf, cal2027.pdf.
METEORS = (
    ("QUA", 2026, "2025-12-28", "2026-01-12", "2026-01-03T21:00", None, 80, False, "2026-01-03"),
    ("ETA", 2026, "2026-04-19", "2026-05-28", "2026-05-06", None, 50, False, "2026-05-05"),
    ("PER", 2026, "2026-07-17", "2026-08-24", "2026-08-13T02:00", "2026-08-13T04:00", 100, False, "2026-08-12"),
    ("GEM", 2026, "2026-12-04", "2026-12-20", "2026-12-14T14:00", None, 150, False, "2026-12-14"),
    ("QUA", 2027, "2026-12-28", "2027-01-12", "2027-01-04T03:25", None, 80, True, "2027-01-03"),
    ("ETA", 2027, "2027-04-19", "2027-05-28", "2027-05-06T09:00", None, 50, False, "2027-05-05"),
    ("PER", 2027, "2027-07-17", "2027-08-24", "2027-08-13T08:00", "2027-08-13T10:00", 110, True, "2027-08-12"),
    ("GEM", 2027, "2027-12-04", "2027-12-20", "2027-12-14T20:00", None, 150, False, "2027-12-14"),
)
TABLE_YEARS = (2026, 2027)


def _utc(s):
    return datetime.datetime.fromisoformat(s).replace(tzinfo=UTC)


def meteor(row):
    code, year, a, b, m1, m2, zhr, plus, night = row
    timed = "T" in m1
    return {"code": code, "year": year, "from": datetime.date.fromisoformat(a), "to": datetime.date.fromisoformat(b),
            "max": _utc(m1).astimezone(BAKU) if timed else None, "max_end": _utc(m2).astimezone(BAKU) if m2 else None,
            "max_day": _utc(m1).astimezone(BAKU).date() if timed else datetime.date.fromisoformat(m1),
            "zhr": zhr, "plus": plus, "night": datetime.date.fromisoformat(night),
            "name": f"{SHOWER_NAME[code]} meteor axını"}


def _max_text(m, rel=None):
    """«14 dekabrda Bakı vaxtı ilə saat 18:00 radələrində»; rel verilibsə tarix əvəzinə «bu gün», «sabah»."""
    when = rel or ox.day_loc(m["max_day"])
    if not m["max"]:
        return when
    zone = "" if rel else " Bakı vaxtı ilə"
    if m["max_end"]:
        return f"{when}{zone} saat {m['max']:%H:%M}–{m['max_end']:%H:%M} arasında"
    return f"{when}{zone} saat {m['max']:%H:%M} radələrində"


def _rel_day(d, pub):
    if d == pub:
        return "bu gün"
    return "sabah" if d == pub + datetime.timedelta(days=1) else ox.day_loc(d)


def meteor_slot(m):
    """Zirvə xəbəri axşam 18:15-də; maksimum həmin axşam daha tezdirsə, ondan 45 dəqiqə əvvəl (rübə yuvarlaq)."""
    if m["max"] and m["max"].date() == m["night"]:
        s = m["max"] - datetime.timedelta(minutes=45)
        hm = f"{s.hour:02d}:{s.minute - s.minute % 15:02d}"
        return max(SLOT["ay"], min(SLOT["meteor"], hm))
    return SLOT["meteor"]


def meteor_item(m, preview, ref):
    """preview: zirvədən 2 gün əvvəlki xəbər; əks halda zirvə gecəsinin xəbəri. ref: dərc anı."""
    probe = m["max"] or _at(m["max_day"], "03:00")
    future = probe > ref
    verb = "zirvəyə çatacaq" if future else "zirvəyə çatıb"
    olacaq = "olacaq" if future else "olub"
    pub = ref.date()
    if preview:
        title = f"{m['name']} {ox.day_loc(m['max_day'])} {verb}"
    else:
        rel = _rel_day(m["max_day"], pub)
        if rel == "sabah" and m["max"] and m["max"].hour < 6:
            rel = "bu gecə"
        title = f"{m['name']} {_max_text(m, rel)} {verb}"
    lead = (f"Beynəlxalq Meteor Təşkilatının (IMO) təqviminə görə, {_range_text(m['from'], m['to'])} tarixlərində aktiv olan {m['name']} "
            f"{_max_text(m)} {verb}.")
    body = [f"IMO-nun proqnozuna görə, zirvədə ZHR göstəricisi (ideal şəraitdə saatda görünə biləcək meteor sayı): "
            f"{m['zhr']}{' (daha çox ola bilər)' if m['plus'] else ''}."]
    lit = moon_illum(probe if not m["max_end"] else probe + (m["max_end"] - m["max"]) / 2)
    moon = f"Ayın işıqlı hissəsi 1%-dən az {olacaq}" if lit < 0.005 else f"Ayın {_pct(lit)}-i işıqlı {olacaq}"
    body.append(f"Hesablamaya görə, zirvə {'vaxtı' if m['max'] else 'günü'} {moon}.")
    if m["max"]:
        ends = [m["max"]] + ([m["max_end"]] if m["max_end"] else [])
        alts = [sun_alt(x) for x in ends]
        if all(a < -6 for a in alts):  # vətəndaş alatoranlığından sonra; 18:00 və ya 07:25 «gecə» deyil, amma qaranlıqdır
            body.append(f"Zirvə vaxtı Bakıda hava qaranlıq {olacaq}.")
        elif all(a > 0 for a in alts):
            body.append(f"Zirvə vaxtı Bakıda gündüz {olacaq}.")
    part = "onizleme" if preview else "zirve"
    return {"kind": "meteor", "key": f"sema-meteor-{m['code'].lower()}-{m['year']}-{part}", "title": title, "lead": lead,
            "body": body, "credit": IMO, "link": IMO_PDF.format(m["year"]), "topic": TOPIC,
            "slot": SLOT["meteor-onizleme"] if preview else meteor_slot(m), "worth": True}


def meteor_items(day, now):
    out = []
    for row in METEORS:
        m = meteor(row)
        if day == m["night"] - datetime.timedelta(days=2):
            out.append(meteor_item(m, True, max(now, _at(day, SLOT["meteor-onizleme"]))))
        elif day == m["night"]:
            out.append(meteor_item(m, False, max(now, _at(day, meteor_slot(m)))))
    return out


# --- 4. Tutulmalar -----------------------------------------------------------------------------------------------

NASA = "NASA"
NASA_SE = "https://eclipse.gsfc.nasa.gov/SEdecade/SEdecade2021.html"
NASA_LE = "https://eclipse.gsfc.nasa.gov/LEdecade/LEdecade2021.html"
JPL_NOTE = "Bakı üçün vaxtlar NASA JPL-in Horizons efemeridləri ilə hesablanıb."
JPL_SEEN = "Bakıdan görünmə NASA JPL-in Horizons efemeridləri ilə yoxlanıb."
# Günəş: (tarix, ən böyük faza TD, növ, maqnituda, NASA-nın görünmə bölgəsi (cədvəldəki kimi), qismən görünmə yeri,
#  mərkəzi zolaq, Bakı). Bakı: «zona» (Bakı görünmə zonasından kənardadır), «gecə» (tutulma Bakıda Günəş batandan sonradır)
#  və ya JPL Horizons-un topomərkəzi efemeridləri ilə hesablanmış kontaktlar (UTC), maksimal faza, örtülmə payı.
SOLAR = (
    ("2026-02-17", "12:13:05", "Annular", 0.963, "s Argentina & Chile, s Africa, Antarctica [Annular: Antarctica]",
     "Argentina və Çilinin cənubunda, Afrikanın cənubunda və Antarktidada",
     "Həlqəvi tutulma Antarktidada müşahidə olunacaq.", "zona"),
    ("2026-08-12", "17:47:05", "Total", 1.039, "n N. America, w Africa, Europe [Total: Arctic, Greenland, Iceland, Spain]",
     "Şimali Amerikanın şimalında, Afrikanın qərbində və Avropada",
     "Tam tutulma zolağı Arktika, Qrenlandiya, İslandiya və İspaniyadan keçəcək.", "gecə"),
    ("2027-02-06", "16:00:47", "Annular", 0.928, "S. America, Antarctica, w & s Africa [Annular: Chile, Argentina, Atlantic]",
     "Cənubi Amerikada, Antarktidada, Afrikanın qərbində və cənubunda",
     "Həlqəvi tutulma zolağı Çili, Argentina və Atlantik okeanından keçəcək.", "gecə"),
    ("2027-08-02", "10:07:49", "Total", 1.079,
     "Africa, Europe, Mid East, w & s Asia [Total:Morocco, Spain, Algeria, Libya, Egypt, Saudi Arabia, Yemen, Somalia]",
     "Afrikada, Avropada, Yaxın Şərqdə, Asiyanın qərbində və cənubunda",
     "Tam tutulma zolağı Mərakeş, İspaniya, Əlcəzair, Liviya, Misir, Səudiyyə Ərəbistanı, Yəmən və Somalidən keçəcək.",
     {"start": "2027-08-02T09:13:03", "max": "2027-08-02T10:11:10", "end": "2027-08-02T11:06:38", "mag": 0.379,
      "obsc": 0.269}),
)
# Ay: (tarix, ən böyük faza TD, növ, kölgə maqnitudası, NASA-nın görünmə bölgəsi, görünmə yeri,
#  ən böyük faza anında Ayın Bakıda hündürlüyü: JPL Horizons, dərəcə).
LUNAR = (
    ("2026-03-03", "11:34:52", "Total", 1.151, "e Asia, Australia, Pacific, Americas",
     "Asiyanın şərqində, Avstraliyada, Sakit okeanda və Amerikada", -31.0),
    ("2026-08-28", "04:14:04", "Partial", 0.930, "e Pacific, Americas, Europe, Africa",
     "Sakit okeanın şərqində, Amerikada, Avropada və Afrikada", -24.3),
    ("2027-02-20", "23:14:06", "Penumbral", -0.057, "Americas, Europe, Africa, Asia",
     "Amerikada, Avropada, Afrikada və Asiyada", 45.6),
    ("2027-07-18", "16:04:09", "Penumbral", -1.068, "e Africa, Asia, Australia, Pacific",
     "Afrikanın şərqində, Asiyada, Avstraliyada və Sakit okeanda", -2.1),
    ("2027-08-17", "07:14:59", "Penumbral", -0.525, "Pacific, Americas", "Sakit okeanda və Amerikada", -56.4),
)
ECLIPSE_NAME = {("gunes", "Total"): "tam Günəş tutulması", ("gunes", "Annular"): "həlqəvi Günəş tutulması",
                ("gunes", "Partial"): "qismən Günəş tutulması", ("gunes", "Hybrid"): "hibrid Günəş tutulması",
                ("ay", "Total"): "tam Ay tutulması", ("ay", "Partial"): "qismən Ay tutulması",
                ("ay", "Penumbral"): "yarımkölgəli Ay tutulması"}
SHALLOW = -0.5  # kölgə maqnitudası bundan kiçik yarımkölgəli tutulmada Ay yarımkölgəyə azca girir: xəbər yazılmır


def _placed(e, start):
    """Xəbərin günü və slotu. start: Bakıda görünən tutulmanın yerli başlanğıcı, yoxsa ən böyük faza. Günortadan əvvəldirsə
    (gecəyarısından sonrakı Ay tutulması, səhər Günəş tutulması), xəbər əvvəlki axşam: səhər 08:30-da hadisə keçmiş ola bilər."""
    evening = start.hour < 12
    e.update(start=start, day=start.date() - datetime.timedelta(days=1) if evening else start.date(),
             slot=SLOT["tutulma-gece"] if evening else SLOT["tutulma"])
    return e


def eclipses():
    """Cədvəldəki tutulmalar: hər biri xəbərin günü, vaxtı və Bakıdan görünüb-görünməməsi ilə."""
    out = []
    for date, td, typ, mag, region_en, region, central, baku in SOLAR:
        g = baku_minute(_utc(f"{date}T{td}") - datetime.timedelta(seconds=DELTA_T))
        local = None
        if isinstance(baku, dict):
            local = {k: (baku_minute(_utc(baku[k])) if k in ("start", "max", "end") else baku[k]) for k in baku}
        out.append(_placed({"body": "gunes", "type": typ, "mag": mag, "greatest": g, "region_en": region_en, "region": region,
                            "central": central, "local": local, "hidden": None if local else baku, "visible": bool(local),
                            "name": ECLIPSE_NAME[("gunes", typ)], "link": NASA_SE, "shallow": False},
                           local["start"] if local else g))
    for date, td, typ, mag, region_en, region, alt in LUNAR:
        g = baku_minute(_utc(f"{date}T{td}") - datetime.timedelta(seconds=DELTA_T))
        out.append(_placed({"body": "ay", "type": typ, "mag": mag, "greatest": g, "region_en": region_en, "region": region,
                            "alt": alt, "visible": alt > 0, "name": ECLIPSE_NAME[("ay", typ)], "link": NASA_LE,
                            "shallow": typ == "Penumbral" and mag < SHALLOW}, g))
    return sorted(out, key=lambda e: e["greatest"])


def eclipse_at_phase(q, t):
    """Yeni Ay Günəş tutulması, bədir Ay tutulması ilə eyni hadisədir: cədvəldə 1 gün içində varsa onu qaytarır."""
    want = {0: "gunes", 2: "ay"}.get(q)
    for e in eclipses():
        if e["body"] == want and not e["shallow"] and abs((e["greatest"] - t).total_seconds()) < 86400:
            return e
    return None


def _when_word(e, pub):
    g = e["greatest"]
    if g.date() == pub:
        return "bu gün"
    if g.date() == pub + datetime.timedelta(days=1):
        return "bu gecə" if g.hour < 6 else "sabah"
    return ox.day_loc(g)


def eclipse_item(e, preview, ref):
    pub = ref.date()
    g = e["greatest"]
    when = ox.day_loc(g) if preview else _when_word(e, pub)
    if e["body"] == "gunes":
        if e["visible"]:
            seen = "Bakıdan qismən görünəcək"
        else:
            seen = "Bakıdan görünməyəcək"
    else:
        seen = "Bakıdan görünəcək" if e["visible"] else "ən böyük fazası Bakıdan görünməyəcək"
    title = f"{_cap1(when)} {e['name']} olacaq: {seen}"
    where = "Yer kürəsində " if e["body"] == "gunes" else ""  # Günəş tutulmasının Bakıdakı ən böyük fazası abzasdadır
    lead = (f"NASA-nın məlumatına görə, {ox.day_loc(g)} {e['name']} baş verəcək; tutulmanın {where}ən böyük fazası "
            f"Bakı vaxtı ilə {ox.time_loc(g)} olacaq.")
    body = []
    if e["body"] == "gunes":
        loc = e["local"]
        if loc:
            body.append(f"Bakıda tutulma {ox.time_loc(loc['start'])} başlayacaq, {_hm_loc(loc['max'])} ən böyük fazaya "
                        f"çatacaq və {_hm_loc(loc['end'])} bitəcək.")
            body.append(f"Bakıda tutulmanın maksimal fazası {ox.az_num(loc['mag'], 2)} olacaq: Günəş diskinin "
                        f"{_pct(loc['obsc'])}-i örtüləcək.")
        elif e["hidden"] == "zona":
            body.append("Bakı tutulmanın görünmə zonasından kənardadır.")
        else:
            body.append("Tutulma Bakıda Günəş batandan sonra baş verəcək, ona görə buradan görünməyəcək.")
        body.append(e["central"])
        body.append(f"Qismən tutulma {e['region']} görünəcək.")
        body.append(JPL_NOTE if loc else JPL_SEEN)
    else:
        if e["visible"]:
            body.append(f"Ən böyük faza anında Ay Bakıda üfüqdən təxminən {ox.az_num(e['alt'], 0)}° yüksəklikdə olacaq.")
        else:
            body.append("Ən böyük faza anında Ay Bakıda üfüqdən aşağıda olacaq.")
        if e["type"] == "Total":
            body.append("Ay tamamilə Yerin tam kölgəsinə girəcək.")
        elif e["type"] == "Partial":
            body.append(f"Ən böyük fazada Ay diametrinin {_pct(e['mag'])}-i Yerin tam kölgəsinə girəcək.")
        else:
            body.append("Ay yalnız Yerin yarımkölgəsindən keçəcək.")
        body.append(f"Tutulma {e['region']} görünəcək.")
        body.append("Ayın Bakıdakı hündürlüyü NASA JPL-in Horizons efemeridləri ilə hesablanıb.")
    part = "onizleme" if preview else "gun"
    item = {"kind": "tutulma", "key": f"sema-tutulma-{g:%Y-%m-%d}-{e['body']}-{part}", "title": title, "lead": lead,
            "body": body, "credit": NASA, "link": e["link"], "topic": TOPIC,
            "slot": SLOT["tutulma-onizleme"] if preview else e["slot"], "worth": True}
    # Dərc olunmur: dayaz tutulma, yarımkölgəli tutulmanın önizləməsi və gecikmiş dərc. Mətn gələcək zamandadır, dərc anı
    # e["start"]-ı (Bakıda görünən tutulmanın yerli başlanğıcı, yoxsa ən böyük faza) keçibsə, «olacaq» yanlış olardı.
    if e["shallow"]:
        sign = "-" if e["mag"] < 0 else ""
        item["worth"], item["why"] = False, f"dayaz yarımkölgəli tutulma (kölgə maqnitudası {sign}{ox.az_num(e['mag'], 3)})"
    elif preview and e["type"] == "Penumbral":
        item["worth"], item["why"] = False, "yarımkölgəli tutulma: yalnız tutulma gecəsinin xəbəri"
    elif ref >= e["start"]:
        item["worth"], item["why"] = False, "gecikmiş xəbər: tutulma artıq başlayıb"
    return item


def eclipse_items(day, now):
    out = []
    for e in eclipses():
        if day == e["day"]:
            out.append(eclipse_item(e, False, max(now, _at(day, e["slot"]))))
        elif day == e["day"] - datetime.timedelta(days=2) and e["visible"] and not e["shallow"]:
            out.append(eclipse_item(e, True, max(now, _at(day, SLOT["tutulma-onizleme"]))))
    return out


def table_items(day):
    """Meteor və tutulma cədvəli bu ili əhatə etmirsə: dərc olunmayan bir qeyd, səbəbi ilə."""
    if day.year <= TABLE_YEARS[-1]:
        return []
    year = ox.ordinal(day.year)
    return [{"kind": "sema-cedvel", "key": f"sema-cedvel-{day.year}", "title": f"{year} il üçün meteor və tutulma cədvəli yoxdur",
             "lead": "Meteor axınlarının (IMO) və tutulmaların (NASA) cədvəli 2026–2027-ci illər üçündür.", "body": [],
             "credit": CREDIT, "link": IMO_PDF.format(day.year), "topic": TOPIC, "slot": SLOT["ay"], "worth": False,
             "why": f"cədvəldə {year} il yoxdur: IMO və NASA cədvəllərini əlavə etmək lazımdır"}]


# --- Gün ---------------------------------------------------------------------------------------------------------

_PRIO = {"tutulma": 0, "fesil": 1, "meteor": 2, "ay-faza": 3, "gun-batimi": 4}


def day_items(day, now=None):
    """Bakı tarixi day üçün bütün səma xəbərləri. now: dərc anı (keçmiş və ya gələcək zaman üçün)."""
    now = now or _at(day, "00:00")
    out = (eclipse_items(day, now) + season_items(day, now) + meteor_items(day, now) + moon_items(day, now)
           + sunset_items(day, now) + table_items(day))
    worth = sorted((i for i in out if i["worth"]), key=lambda i: (_PRIO.get(i["kind"], 9), i["slot"]))
    for i in worth[DAY_CAP:]:
        i["worth"], i["why"] = False, f"gündə {DAY_CAP} kosmos xəbəri həddi"
    return sorted(out, key=lambda i: (i["slot"], _PRIO.get(i["kind"], 9)))


def items(root, now, fetch=None):
    """İstehsalın now anında (Bakı vaxtı) dərc edəcəyi xəbərlər: həmin günün səma xəbərləri. Sorğu yoxdur."""
    now = now.replace(tzinfo=BAKU) if now.tzinfo is None else now.astimezone(BAKU)
    return day_items(now.date(), now)


# --- Sınaq ------------------------------------------------------------------------------------------------------

def _verdict(item):
    return "✅ Dərc olunardı" if item["worth"] else f"⏭ Dərc olunmazdı: {item['why']}"


def _case(label, day, kinds):
    """O günün (dərc anı slotdur) seçilmiş növlü xəbərləri, etiketlə."""
    md = []
    for item in day_items(day):
        if item["kind"] in kinds:
            md += [f"> {label}: {ox.day_text(day)} {day.year}, dərc vaxtı {item['slot']}", ""]
            md += ox.render(item) + [_verdict(item), ""]
    return md


def _scan(today, kinds, step, limit=400):
    """today-dən geriyə (step=-1) və ya irəli (step=1) həmin növ xəbəri olan ilk gün."""
    for n in range(1, limit):
        d = today + datetime.timedelta(days=n * step)
        if any(i["kind"] in kinds for i in day_items(d)):
            return d
    return None


def sinaq(root, now=None, fetch=None):
    """Nümunələr (Markdown): bugünkü xəbərlər və hər növün sonuncu və növbəti real halı. Sorğu yoxdur."""
    now = now or datetime.datetime.now(BAKU)
    now = now.replace(tzinfo=BAKU) if now.tzinfo is None else now.astimezone(BAKU)
    today = now.date()
    md = ["## Səma xəbərləri: sınaq", "",
          f"{now:%d.%m.%Y %H:%M} (Bakı vaxtı). Hesablama yerlidir, sorğu yoxdur; sayta heç nə yazılmır.", "",
          f"### Bu gün, {ox.day_text(today)}", ""]
    todays = items(root, now)
    for item in todays:
        md += ox.render(item) + [_verdict(item), ""]
    if not todays:
        md += [f"> {ox.day_text(today)} üçün səma xəbəri yoxdur.", ""]
    groups = (("Ay fazaları", ("ay-faza",)), ("Gündönümü və bərabərlik", ("fesil",)), ("Bakıda gün batımı", ("gun-batimi",)),
              ("Meteor axınları", ("meteor",)), ("Tutulmalar", ("tutulma",)))
    for head, kinds in groups:
        md += [f"## {head}", ""]
        last, nxt = _scan(today, kinds, -1, 800), _scan(today, kinds, 1, 800)
        if last:
            md += _case("Sonuncu real hal", last, kinds)
        if nxt:
            md += _case("Növbəti hal", nxt, kinds)
        if nxt and kinds == ("meteor",):  # önizləmədən sonra zirvə gecəsi
            after = _scan(nxt, kinds, 1, 10)
            if after:
                md += _case("Növbəti hal", after, kinds)
        if kinds == ("tutulma",):
            for e in eclipses():
                if e["day"] > today and e["day"] != nxt and e["visible"] and not e["shallow"]:
                    md += _case("Bakıdan görünən tutulma", e["day"] - datetime.timedelta(days=2), kinds)
                    md += _case("Bakıdan görünən tutulma", e["day"], kinds)
            hidden = [e for e in eclipses() if e["day"] > today and e["shallow"]]
            if hidden:
                md += _case("Dərc olunmayan hal", hidden[0]["day"], kinds)
    return md


def _arg(argv, name):
    return argv[argv.index(name) + 1] if name in argv and argv.index(name) + 1 < len(argv) else None


def main(argv):
    if "--sinaq" not in argv:
        print(__doc__)
        return 0
    root = pathlib.Path(_arg(argv, "--root") or pathlib.Path(__file__).parent)
    now = _arg(argv, "--now")
    now = datetime.datetime.fromisoformat(now) if now else None
    sys.stdout.write("\n".join(sinaq(root, now)) + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
