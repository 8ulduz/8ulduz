"""Yer və kosmos xəbərləri (oz_yer_kosmos.py), mərhələ 2: regionda zəlzələ, asteroidlərin Yerə yaxınlaşması, kosmik
buraxılışlar. Sahibin qərarı (2026-11-10): «Mərhələ 2-ni qur», yəni açarsız açıq API-lərdən şablon xəbər, süni intellektsiz.
Sayta qoşulmayıb: updater.py və pipeline bu modulu çağırmır (NotOnTheSiteTest).

1. «Regionda zəlzələ»: USGS-in FDSN sorğusu (son 24 saat, Türkiyə ilə Mərkəzi Asiya arasındakı qutu), Türkiyə üçün AFAD.
   - Bölgə: Türkiyə, İran, Gürcüstan, Ermənistan, Rusiyanın Şimali Qafqazı, Qazaxıstan, Qırğızıstan, Tacikistan,
     Türkmənistan, Özbəkistan, Xəzər və Qara dəniz. Maqnituda 4,5 və daha çox, USGS-in yoxladığı («reviewed») zəlzələ.
   - Azərbaycan ərazisindəki zəlzələ yazılmır (yer adında «Azerbaijan» və ya sərhəd çoxbucaqlısının içi): onu seismology.az
     xəbəri (oz_xeber.seys_item) verir. Sərhədə 100 km-dən yaxın zəlzələ seismology.az siyahısında ±2 dəqiqə ilə varsa, o da.
   - Türkiyədə il, rayon və məhəllə AFAD-dandır: eyni zəlzələ ±2 dəqiqə və 50 km ilə tapılır.
   - Yalnız Bakı vaxtı ilə bu günün zəlzələsi (done yalnız bu günün açarlarıdır) və 6 saatdan təzə olanı.
   - Gündə ən çox 2 xəbər. Çox olsa ən güclüsü yazılır, qalanları onun bir cümləsində sadalanır. Eyni bölgədə (100 km,
     24 saat) eyni və ya daha güclü zəlzələnin ardınca gələn təkan ayrıca xəbər deyil: bir hadisə, bir xəbər.
2. «Asteroid Yerin yaxınlığından keçir» (NASA JPL, CAD API): bazar ertəsi növbəti 7 günün 0,05 AB-dən yaxın keçidləri;
   digər günlər Aydan yaxın (1 Ay məsafəsindən az) keçid olanda bir xəbər: ən böyüyü, qalanları bir cümlədə.
   Ölçünü JPL vermirsə parlaqlıqdan (H) hesablanır: D = 1329 km / √albedo · 10^(−H/5), albedo 0,25–0,05.
3. «Həftənin kosmik buraxılışları» (The Space Devs, Launch Library 2): bazar ertəsi həftənin icmalı; digər günlər yalnız
   pilotlu buraxılış və ya Starship üçün, LL2 statusu «Go» və vaxtı dəqiqəyədək məlumdursa. D gününün xəbəri D 13:00 ilə
   D+1 13:00 arasındakı buraxılışlardır: gecə və səhər tezdən uçuş bir gün əvvəl yazılır.

Sorğular yalnız fetch ilə və yalnız «tik»də gedir: saat h-da dəqiqə 10·(h mod 6) … 10·(h mod 6)+9 (00:00, 01:10, 02:20…).
İstehsal items()-i 10–30 dəqiqədən bir çağırır: 10 dəqiqəlik dövrədə hər tikə bir çağırış düşür, 30 dəqiqəlikdə ardıcıl 3
tikdən birinə. Hər sorğudan sonra, nəticəsi nə olursa olsun, pəncərənin açarı qayıdır (xəbər yoxdursa worth=False və «why»
ilə): istehsal qayıdan hər açarı done-a yazır və həmin pəncərədə ikinci sorğu getmir. Gündə ən çox: USGS 24 (saatda bir,
açar «zelzele-sorgu-<gün>T<saat>»), LL2 1 (10:00–13:00), JPL 1 (13:00–16:00), AFAD 2 və seismology.az 2 (yalnız dərc
olunacaq zəlzələ üçün), cəmi 30. İstehsal worth=False açarlarını done-a yazmasa belə tik LL2 və JPL-i 3 sorğu ilə saxlayır.

Zəlzələnin açarları: dərc olunan «zelzele-region-<USGS id>», qəti dərc olunmayan (təkan, gecikmiş, gündəlik hədd,
seismology.az-da var) «zelzele-yox-<id>». USGS-in hələ yoxlamadığı zəlzələ items()-də qayıtmır: növbəti tikdə yenə baxılır.
"""
import datetime
import json
import math
import pathlib
import re
import sys
import time
import unicodedata
import urllib.parse

import oz_xeber as ox

BAKU = ox.BAKU
UTC = datetime.timezone.utc
DAY = datetime.timedelta(days=1)
HOUR = datetime.timedelta(hours=1)
MINUTE = datetime.timedelta(minutes=1)
TIMEOUT = 15
PAUSE = 1.0                 # sınaqda eyni hosta sorğular arasında, saniyə
TITLE_MAX = 110
BAKU_LL = (40.4093, 49.8671)
EARTH_KM = 6371.0088
DEG_KM = EARTH_KM * math.pi / 180

# --- Ümumi: vaxt, ədəd, şəkilçi ----------------------------------------------------------------------------------------


def _baku(now=None):
    """Aware Bakı vaxtı; ofsetsiz vaxt Bakı vaxtı sayılır."""
    if now is None:
        now = datetime.datetime.now(BAKU)
    return now.replace(tzinfo=BAKU) if now.tzinfo is None else now.astimezone(BAKU)


def _at(day, hm):
    h, m = hm.split(":")
    return datetime.datetime(day.year, day.month, day.day, int(h), int(m), tzinfo=BAKU)


def tick(now):
    """Sorğu anı: saat h-da dəqiqə 10·(h mod 6) … 10·(h mod 6)+9."""
    now = _baku(now)
    return now.minute // 10 == now.hour % 6


def _err(e):
    code = getattr(e, "code", None)
    return f"{type(e).__name__} {code}" if isinstance(code, int) else type(e).__name__


def _half_up(x):
    return int(math.floor(x + 0.5))


def _flt(x):
    try:
        v = float(x)
    except (TypeError, ValueError):
        return None
    return v if math.isfinite(v) else None


def num(v, dec=2):
    """Ədəd artıq sıfırsız: 15.35 -> «15,35», 10.0 -> «10», 8.76 (dec=1) -> «8,8»."""
    text = ox.az_num(v, dec)
    return text.rstrip("0").rstrip(",") if "," in text else text


def _hm(t):
    return f"{t.astimezone(BAKU):%H:%M}"


def _minute(t):
    """Ən yaxın dəqiqəyə."""
    return (t + datetime.timedelta(seconds=30)).replace(second=0, microsecond=0)


def _span(a, b):
    """«9–15 noyabrda», «28 dekabr – 3 yanvarda»."""
    if a == b:
        return ox.day_loc(a)
    if a.month == b.month:
        return f"{a.day}–{ox.day_loc(b)}"
    return f"{ox.day_text(a)} – {ox.day_loc(b)}"


_UNITS = ("sıfır", "bir", "iki", "üç", "dörd", "beş", "altı", "yeddi", "səkkiz", "doqquz")
_TENS = ("", "on", "iyirmi", "otuz", "qırx", "əlli", "altmış", "yetmiş", "səksən", "doxsan")


def _last_word(n):
    """Ədədin oxunuşunun son sözü: 48 -> «səkkiz», 50 -> «əlli», 100 -> «yüz»."""
    n = abs(int(n))
    if n == 0:
        return "sıfır"
    if n % 10:
        return _UNITS[n % 10]
    if n % 100:
        return _TENS[n % 100 // 10]
    return "yüz" if n % 1000 else "min"


def poss(text):
    """Ədədin mənsubiyyət şəkilçisi oxunuşa görə: «0,48-i», «0,14-ü», «0,50-si», «0,06-sı», «3-ü»."""
    digits = text.split(",")[-1].replace(" ", "").replace(" ", "")
    word = _last_word(int(digits)) if digits.isdigit() else "a"
    forms = ("sı", "si", "su", "sü") if ox._vowel_end(word) else ("ı", "i", "u", "ü")
    return f"{text}-{ox._four(word, forms)}"


# Azərbaycan əlifbasında olan işarələr qalır (ç, ş, ğ, ö, ü, İ), qalanları düşür: «Kāzerūn» -> «Kazerun», «Kŭlob» -> «Kulob».
_KEEP = {("c", "̧"), ("s", "̧"), ("g", "̆"), ("o", "̈"), ("u", "̈"), ("i", "̇")}


def fold(name):
    out = []
    for ch in unicodedata.normalize("NFD", name or ""):
        if unicodedata.combining(ch):
            if out and (out[-1].lower(), ch) in _KEEP:
                out.append(ch)
            continue
        out.append(ch)
    return unicodedata.normalize("NFC", "".join(out))


def _sound(name):
    """Adın oxunuşunun sonu (şəkilçi üçün): son söz, samitdən sonrakı son «y» sait sayılır (İngilis «-y» i, türk dillərində ı)."""
    words = fold(name).split()
    w = ox._low(words[-1]) if words else ""
    if len(w) > 1 and w[-1] == "y" and w[-2] not in ox._VOWELS:
        w = w[:-1] + ("ı" if ox._last_vowel(w[:-1]) in "aıou" else "i")
    return w


def gen(name):
    """Yiyəlik hal oxunuşa görə: «Kozanın», «İmamoğlunun», «Kyzyl-Eshmenin», «Murghobun»."""
    s = _sound(name)
    return f"{name}{'n' if ox._vowel_end(s) else ''}{ox._four(s, ('ın', 'in', 'un', 'ün'))}"


def km_between(a, b):
    """Böyük dairə məsafəsi, km; a, b: (en, uzunluq)."""
    la1, lo1, la2, lo2 = map(math.radians, (a[0], a[1], b[0], b[1]))
    h = math.sin((la2 - la1) / 2) ** 2 + math.cos(la1) * math.cos(la2) * math.sin((lo2 - lo1) / 2) ** 2
    return 2 * EARTH_KM * math.asin(min(1.0, math.sqrt(h)))


def baku_km(lat, lon):
    """Bakıya böyük dairə məsafəsi, 10 km-ə yuvarlaq."""
    return _half_up(km_between((lat, lon), BAKU_LL) / 10.0) * 10


# --- Şəbəkə ------------------------------------------------------------------------------------------------------------


class _Get:
    """fetch-in üstündə: bir çağırışda hər ünvana ən çox bir sorğu (xəta da yadda qalır), eyni hosta sorğular arasında
    pause saniyə fasilə. count göndərilən sorğuların sayıdır, hosts hər hosta neçə sorğu getdiyi."""

    def __init__(self, fetch=None, pause=0.0):
        self.fetch, self.pause = fetch, pause
        self.cache, self.last, self.hosts, self.count = {}, {}, {}, 0

    def __call__(self, url, accept="application/json"):
        if url not in self.cache:
            host = urllib.parse.urlsplit(url).netloc
            if self.pause and host in self.last:
                wait = self.pause - (time.monotonic() - self.last[host])
                if wait > 0:
                    time.sleep(wait)
            self.count += 1
            self.hosts[host] = self.hosts.get(host, 0) + 1
            try:
                if self.fetch is None:
                    self.fetch = ox._u().fetch
                self.cache[url] = (self.fetch(url, timeout=TIMEOUT, headers={"Accept": accept}), None)
            except Exception as e:  # şəbəkə xətası yalnız həmin mənbəni saxlayır
                self.cache[url] = (None, e)
            self.last[host] = time.monotonic()
        data, err = self.cache[url]
        if err is not None:
            raise err
        return data


def _json(raw):
    return json.loads(raw.decode("utf-8") if isinstance(raw, (bytes, bytearray)) else raw)


def _leader(text):
    try:
        return bool(ox.needs_owner(text))
    except Exception:
        return bool(re.search(r"prezident|birinci xanım|vitse-prezident|əliyev", ox._low(text)))


def _guard(item):
    """Rəhbərliyin adı keçən xəbər dərc olunmur (sahibin qaydası; mətnin hamısı mənbədən gəlir)."""
    if item.get("worth") and _leader("\n".join([item["title"], item["lead"], *item["body"]])):
        return dict(item, worth=False, why="rəhbərliyin adı keçir: dərc olunmur")
    return item


def _fail(kind, key, title, why, credit, link, topic, now):
    """Mənbə alınmayanda dərc olunmayan qeyd: səbəb «why»-dadır."""
    return {"kind": kind, "key": key, "title": title, "lead": why, "body": [], "credit": credit, "link": link,
            "topic": topic, "slot": f"{now:%H:%M}", "worth": False, "why": why}


# --- 1. Regionda zəlzələ -----------------------------------------------------------------------------------------------

USGS_API = "https://earthquake.usgs.gov/fdsnws/event/1/query"
USGS_MAP = "https://earthquake.usgs.gov/earthquakes/map/"
USGS_CREDIT = "ABŞ Geoloji Xidməti (USGS)"
USGS_GEN = "ABŞ Geoloji Xidmətinin (USGS)"
AFAD_API = "https://servisnet.afad.gov.tr/apigateway/deprem/apiv2/event/filter"
AFAD_EVENT = "https://deprem.afad.gov.tr/event-detail/{}"
AFAD_CREDIT = "Türkiyənin Fəlakət və Fövqəladə Hallar İdarəsi (AFAD)"
AFAD_GEN = "Türkiyənin Fəlakət və Fövqəladə Hallar İdarəsinin (AFAD)"
BOX = (("minlatitude", 24), ("maxlatitude", 50), ("minlongitude", 25), ("maxlongitude", 88))
MIN_MAG = 4.5
QUAKE_CAP = 2
QUAKE_KEY = "zelzele-region-"   # dərc olunan zəlzələ: gündəlik hədd yalnız bu açarları sayır
QUAKE_SKIP = "zelzele-yox-"     # qəti dərc olunmayan zəlzələ
QUAKE_TICK = "zelzele-sorgu-"   # saatın USGS sorğusu göndərilib
TOPIC_QUAKE = "təbiət"      # CONVENTIONS-in siyahısında təbiət yoxdur; planın «nature 3/3» həddi
CLUSTER_KM = 100.0
CLUSTER_H = 24
MATCH_S = 120               # USGS ↔ AFAD ↔ seismology.az: ±2 dəqiqə
MATCH_KM = 50.0
NEAR_AZ_KM = 100.0
FRESH = datetime.timedelta(hours=6)
STALE = datetime.timedelta(hours=2)
REST_MAX = 5

COUNTRY = {  # USGS-in yazdığı ad -> (adlıq, yerlik, yiyəlik)
    "Turkey": ("Türkiyə", "Türkiyədə", "Türkiyənin"),
    "Türkiye": ("Türkiyə", "Türkiyədə", "Türkiyənin"),
    "Iran": ("İran", "İranda", "İranın"),
    "Georgia": ("Gürcüstan", "Gürcüstanda", "Gürcüstanın"),
    "Armenia": ("Ermənistan", "Ermənistanda", "Ermənistanın"),
    "Russia": ("Rusiya", "Rusiyada", "Rusiyanın"),
    "Kazakhstan": ("Qazaxıstan", "Qazaxıstanda", "Qazaxıstanın"),
    "Kyrgyzstan": ("Qırğızıstan", "Qırğızıstanda", "Qırğızıstanın"),
    "Tajikistan": ("Tacikistan", "Tacikistanda", "Tacikistanın"),
    "Turkmenistan": ("Türkmənistan", "Türkmənistanda", "Türkmənistanın"),
    "Uzbekistan": ("Özbəkistan", "Özbəkistanda", "Özbəkistanın"),
    "Caspian Sea": ("Xəzər dənizi", "Xəzər dənizində", "Xəzər dənizinin"),
    "Black Sea": ("Qara dəniz", "Qara dənizdə", "Qara dənizin"),
}
NEIGHBOUR = {"Azerbaijan": "Azərbaycan", "Iraq": "İraq", "Syria": "Suriya", "Afghanistan": "Əfqanıstan",
             "Pakistan": "Pakistan", "Xinjiang": "Sincan", "China": "Çin", "Greece": "Yunanıstan", "India": "Hindistan",
             "Bulgaria": "Bolqarıstan", "Romania": "Rumıniya", "Ukraine": "Ukrayna", "Nepal": "Nepal",
             "Mongolia": "Monqolustan", "Cyprus": "Kipr", "Saudi Arabia": "Səudiyyə Ərəbistanı", "Oman": "Oman",
             "United Arab Emirates": "BƏƏ", "Egypt": "Misir", "Lebanon": "Livan", "Israel": "İsrail", "Jordan": "İordaniya"}
# Azərbaycan dilində yazılışı dəqiq bilinən şəhərlər; qalanları mənbədəki kimi (Azərbaycan əlifbasında olmayan işarəsiz).
CITY_AZ = {
    "Iran": {"Tehran": "Tehran", "Tabriz": "Təbriz", "Ardabil": "Ərdəbil", "Mashhad": "Məşhəd", "Isfahan": "İsfahan",
             "Shiraz": "Şiraz", "Urmia": "Urmiya", "Orumiyeh": "Urmiya", "Zanjan": "Zəncan", "Qazvin": "Qəzvin",
             "Hamadan": "Həmədan", "Rasht": "Rəşt", "Ahar": "Əhər", "Khoy": "Xoy", "Marand": "Mərənd",
             "Maragheh": "Marağa", "Sarab": "Sərab", "Meshgin Shahr": "Meşkinşəhr", "Astara": "Astara",
             "Kermanshah": "Kirmanşah", "Kerman": "Kirman", "Qom": "Qum", "Yazd": "Yəzd"},
    "Armenia": {"Yerevan": "İrəvan", "Gyumri": "Gümrü", "Kapan": "Qafan", "Goris": "Gorus", "Meghri": "Mehri",
                "Sisian": "Sisyan", "Dilijan": "Dilican", "Ijevan": "İcevan"},
    "Russia": {"Makhachkala": "Mahaçqala", "Derbent": "Dərbənd", "Khasavyurt": "Xasavyurt", "Grozny": "Qroznı",
               "Vladikavkaz": "Vladiqafqaz", "Nalchik": "Nalçik", "Sochi": "Soçi"},
    "Turkey": {"Istanbul": "İstanbul", "Izmir": "İzmir", "Erzurum": "Ərzurum", "Kars": "Qars", "Ardahan": "Ərdahan",
               "Iğdır": "İğdır", "Igdir": "İğdır"},
    "Kyrgyzstan": {"Bishkek": "Bişkek", "Osh": "Oş", "Jalal-Abad": "Cəlalabad"},
    "Uzbekistan": {"Tashkent": "Daşkənd", "Samarkand": "Səmərqənd", "Bukhara": "Buxara", "Namangan": "Namanqan",
                   "Andijan": "Əndican", "Fergana": "Fərqanə"},
    "Tajikistan": {"Dushanbe": "Düşənbə", "Khujand": "Xocənd"},
    "Kazakhstan": {"Almaty": "Almatı", "Shymkent": "Çimkənd"},
    "Turkmenistan": {"Ashgabat": "Aşqabad", "Turkmenbashi": "Türkmənbaşı", "Türkmenbaşy": "Türkmənbaşı"},
}
CITY_AZ["Türkiye"] = CITY_AZ["Turkey"]
DIR = {"N": "şimal", "S": "cənub", "E": "şərq", "W": "qərb"}
SIDE = {"northern": "şimal", "southern": "cənub", "eastern": "şərq", "western": "qərb", "central": "mərkəz",
        "northwestern": "şimal-qərb", "northeastern": "şimal-şərq", "southwestern": "cənub-qərb",
        "southeastern": "cənub-şərq"}
_DIR_LOC = {"şimal": "şimalında", "cənub": "cənubunda", "şərq": "şərqində", "qərb": "qərbində", "mərkəz": "mərkəzində"}
NORTH_CAUCASUS = (41.0, 44.9, 39.5, 48.7)   # en və uzunluq hüdudları: Krasnodarın cənubundan Dağıstana

# Azərbaycanın sərhədi (sadələşdirilmiş, ±10–15 km): materik və Naxçıvan, (en, uzunluq), saat əqrəbi istiqamətində.
AZ_MAIN = ((41.90, 48.56), (41.78, 48.38), (41.63, 48.10), (41.50, 47.90), (41.22, 47.86), (41.30, 47.55),
           (41.42, 47.20), (41.55, 46.95), (41.70, 46.75), (41.86, 46.55), (41.80, 46.30), (41.62, 46.22),
           (41.45, 46.38), (41.25, 46.55), (41.10, 46.68), (41.05, 46.45), (41.18, 46.10), (41.32, 45.75),
           (41.45, 45.40), (41.33, 45.10), (41.28, 45.02), (41.15, 45.15), (41.05, 45.30), (40.97, 45.55),
           (40.82, 45.62), (40.62, 45.72), (40.42, 45.68), (40.25, 45.98), (40.05, 45.95), (39.80, 46.10),
           (39.60, 46.40), (39.40, 46.46), (39.20, 46.50), (38.87, 46.53), (39.00, 46.75), (39.12, 46.93),
           (39.30, 47.15), (39.42, 47.33), (39.55, 47.60), (39.68, 47.90), (39.50, 48.25), (39.40, 48.32),
           (39.15, 48.15), (38.90, 48.05), (38.65, 48.15), (38.45, 48.60), (38.43, 48.88), (38.75, 48.87),
           (39.20, 48.95), (39.37, 49.30), (39.75, 49.40), (40.05, 49.45), (40.33, 49.82), (40.36, 50.20),
           (40.42, 50.37), (40.50, 50.15), (40.57, 49.90), (40.60, 49.65), (40.85, 49.45), (41.10, 49.25),
           (41.45, 48.95), (41.70, 48.75))
AZ_NAX = ((39.73, 44.77), (39.78, 44.90), (39.68, 45.12), (39.62, 45.35), (39.55, 45.60), (39.45, 45.80),
          (39.30, 45.92), (39.15, 46.05), (38.98, 46.12), (38.86, 46.12), (38.90, 45.90), (38.93, 45.65),
          (39.10, 45.40), (39.25, 45.10), (39.45, 44.88), (39.62, 44.78))


def _inside(lat, lon, poly):
    """Nöqtə çoxbucaqlının içindədir (şüa üsulu, en və uzunluq müstəvisində)."""
    inside = False
    for i in range(len(poly)):
        y1, x1 = poly[i]
        y2, x2 = poly[(i + 1) % len(poly)]
        if (y1 > lat) != (y2 > lat) and lon < x1 + (lat - y1) * (x2 - x1) / (y2 - y1):
            inside = not inside
    return inside


def _seg_km(p, a, b):
    """Nöqtədən parçaya məsafə, km (yerli düz proyeksiyada)."""
    k = math.cos(math.radians(p[0])) * DEG_KM
    ax, ay = (a[1] - p[1]) * k, (a[0] - p[0]) * DEG_KM
    bx, by = (b[1] - p[1]) * k, (b[0] - p[0]) * DEG_KM
    dx, dy = bx - ax, by - ay
    t = 0.0 if dx == 0 and dy == 0 else max(0.0, min(1.0, -(ax * dx + ay * dy) / (dx * dx + dy * dy)))
    return math.hypot(ax + t * dx, ay + t * dy)


def az_km(lat, lon):
    """Azərbaycan sərhədinə məsafə, km; ərazinin içində 0."""
    best = float("inf")
    for poly in (AZ_MAIN, AZ_NAX):
        if _inside(lat, lon, poly):
            return 0.0
        for i in range(len(poly)):
            best = min(best, _seg_km((lat, lon), poly[i], poly[(i + 1) % len(poly)]))
    return best


def usgs_url(start, end, minmag=MIN_MAG):
    """USGS FDSN sorğusu: qutu, maqnituda həddi, [start, end] (UTC)."""
    q = [("format", "geojson"), ("starttime", f"{start.astimezone(UTC):%Y-%m-%dT%H:%M:%S}"),
         ("endtime", f"{end.astimezone(UTC):%Y-%m-%dT%H:%M:%S}"), ("minmagnitude", minmag)] + list(BOX) + [("orderby", "time")]
    return USGS_API + "?" + urllib.parse.urlencode(q, safe=":")


def _ms(v):
    x = _flt(v)
    if x is None:
        return None
    try:
        return datetime.datetime.fromtimestamp(x / 1000.0, tz=UTC)
    except (OverflowError, OSError, ValueError):
        return None


def _quake(f):
    """GeoJSON xüsusiyyəti -> zəlzələ və ya None (natamam və ya pozuq sətir)."""
    try:
        p, c = f["properties"], f["geometry"]["coordinates"]
        lon, lat = float(c[0]), float(c[1])
    except (KeyError, TypeError, ValueError, IndexError):
        return None
    mag, t = _flt(p.get("mag")), _ms(p.get("time"))
    if mag is None or t is None or not (-90 <= lat <= 90 and -180 <= lon <= 180):
        return None
    qid = str(f.get("id") or p.get("code") or "")
    if not re.fullmatch(r"[A-Za-z0-9_-]{4,40}", qid):
        return None
    ids = {x for x in str(p.get("ids") or "").split(",") if x} | {qid}
    return {"id": qid, "ids": ids, "mag": round(mag, 1), "type": str(p.get("type") or ""),
            "place": " ".join(str(p.get("place") or "").split()), "utc": t, "lat": lat, "lon": lon,
            "depth": _flt(c[2]) if len(c) > 2 else None, "status": str(p.get("status") or ""),
            "url": str(p.get("url") or f"https://earthquake.usgs.gov/earthquakes/eventpage/{qid}")}


def parse_usgs(raw):
    """USGS cavabı -> {"generated": UTC vaxtı və ya None, "quakes": [...]}. Pozuq cavab ValueError-dur."""
    try:
        doc = _json(raw)
    except (UnicodeDecodeError, ValueError, TypeError) as e:
        raise ValueError("USGS cavabı JSON deyil") from e
    if not isinstance(doc, dict) or not isinstance(doc.get("features"), list):
        raise ValueError("USGS cavabında zəlzələ siyahısı yoxdur")
    meta = doc.get("metadata") if isinstance(doc.get("metadata"), dict) else {}
    quakes = [q for q in (_quake(f) for f in doc["features"]) if q]
    return {"generated": _ms(meta.get("generated")), "quakes": quakes}


_P_DIST = re.compile(r"^(\d+(?:\.\d+)?) km ([NSEW]{1,3}) of (.+), ([^,]+)$")
_P_SIDE = re.compile(r"^(" + "|".join(SIDE) + r") (.+)$", re.I)
_P_BORDER = re.compile(r"^(.+) border region$", re.I)
_P_NAMED = re.compile(r"^(.+), ([^,]+)$")


def place(text):
    """USGS-in yer adı -> {"kind", "countries", "country", ...} və ya None (tanınmayan format)."""
    text = " ".join((text or "").split())
    m = _P_DIST.match(text)
    if m:
        return {"kind": "city", "countries": [m.group(4)], "country": m.group(4), "km": m.group(1), "dir": m.group(2),
                "city": m.group(3)}
    m = _P_BORDER.match(text)
    if m:
        parts = [p.strip() for p in m.group(1).split("-")]
        return {"kind": "border", "countries": parts, "country": next((p for p in parts if p in COUNTRY), "")}
    m = _P_SIDE.match(text)
    if m:
        return {"kind": "side", "countries": [m.group(2)], "country": m.group(2), "side": m.group(1).lower()}
    if text in COUNTRY or text in NEIGHBOUR:
        return {"kind": "country", "countries": [text], "country": text}
    m = _P_NAMED.match(text)
    if m:  # «Crete, Greece»: yalnız ölkə yazılır
        return {"kind": "country", "countries": [m.group(2)], "country": m.group(2)}
    return None


def city_name(city, country):
    """Şəhər adı: dəqiq Azərbaycan yazılışı, yoxsa mənbədəki kimi (Azərbaycan əlifbasında olmayan işarəsiz)."""
    plain = fold(city)
    return CITY_AZ.get(country, {}).get(plain, plain)


def _dir_loc(parts):
    """[«şimal», «qərb»] -> «şimal-qərbində»."""
    return "-".join(parts[:-1] + [_DIR_LOC[parts[-1]]])


def where(pl):
    """(başlıqda yer, girişdə yer) Azərbaycan dilində və ya None."""
    if not pl:
        return None
    if pl["kind"] == "border":
        parts = [COUNTRY[p][0] if p in COUNTRY else NEIGHBOUR.get(p) for p in pl["countries"]]
        if not all(parts):
            return None
        text = "-".join(parts) + " sərhəd bölgəsində"
        return text, text
    if pl["country"] not in COUNTRY:
        return None
    _, loc, gen_ = COUNTRY[pl["country"]]
    if pl["kind"] == "side":
        text = f"{gen_} {_dir_loc(SIDE[pl['side']].split('-'))}"
        return text, text
    if pl["kind"] == "city":
        city = city_name(pl["city"], pl["country"])
        detail = f"{gen(city)} {num(float(pl['km']), 1)} km {_dir_loc([DIR[c] for c in pl['dir']])}"
        return loc, f"{loc}, {detail}"
    return loc, loc


def outside(pl, lat, lon):
    """Bölgədən kənardırsa səbəb, bölgədədirsə boş sətir."""
    if pl is None:
        return "yer adı tanınmadı"
    names = pl["countries"]
    if "Azerbaijan" in names:
        return "Azərbaycan: bu zəlzələni seismology.az xəbəri verir"
    if not any(n in COUNTRY for n in names):
        return "region xaricində (" + ", ".join(NEIGHBOUR.get(n, n) for n in names) + ")"
    lat0, lat1, lon0, lon1 = NORTH_CAUCASUS
    if pl["country"] == "Russia" and not (lat0 <= lat <= lat1 and lon0 <= lon <= lon1):
        return "Rusiyada, Şimali Qafqazdan kənarda"
    return ""


def _static_why(q):
    """Zəlzələ heç vaxt xəbər olmayacaqsa səbəb (növ, güc, bölgə, Azərbaycan ərazisi)."""
    if q["type"] != "earthquake":
        return f"zəlzələ deyil ({q['type'] or 'növü yoxdur'})"
    if q["mag"] < MIN_MAG:
        return f"{ox.az_num(MIN_MAG, 1)}-dən zəifdir"
    why = outside(q["pl"], q["lat"], q["lon"])
    if why:
        return why
    if az_km(q["lat"], q["lon"]) == 0:
        return "Azərbaycan ərazisində: bu zəlzələni seismology.az xəbəri verir"
    if where(q["pl"]) is None:
        return "yer adı Azərbaycan dilinə çevrilmədi"
    return ""


def _secondary(q, pool):
    """q-dan əvvəlki 24 saatda 100 km-dən yaxında eyni və ya daha güclü zəlzələ (ən erkəni), yoxsa None."""
    best = None
    for p in pool:
        if p is q or p["mag"] < q["mag"]:
            continue
        lag = (q["utc"] - p["utc"]).total_seconds()
        if lag < 0 or lag > CLUSTER_H * 3600 or (lag == 0 and p["id"] >= q["id"]):
            continue
        if km_between((p["lat"], p["lon"]), (q["lat"], q["lon"])) <= CLUSTER_KM and (best is None or p["utc"] < best["utc"]):
            best = p
    return best


def _root(q):
    for _ in range(20):
        if not q.get("prim"):
            return q
        q = q["prim"]
    return q


def _done(q, done):
    return any(QUAKE_KEY + i in done or QUAKE_SKIP + i in done for i in q["ids"])


def parse_afad(raw):
    """AFAD cavabı -> [{id, utc, lat, lon, mag, depth, country, province, district, neighborhood, location}]."""
    doc = _json(raw)
    if not isinstance(doc, list):
        raise ValueError("AFAD cavabı siyahı deyil")
    out = []
    for r in doc:
        try:
            t = datetime.datetime.fromisoformat(str(r["date"]))
            lat, lon, mag = float(r["latitude"]), float(r["longitude"]), float(r["magnitude"])
        except (KeyError, TypeError, ValueError):
            continue
        t = t.replace(tzinfo=UTC) if t.tzinfo is None else t.astimezone(UTC)  # AFAD-ın «date»-i UTC-dir
        clean = {k: " ".join(str(r.get(k) or "").split()) for k in ("country", "province", "district", "neighborhood", "location")}
        out.append(dict(clean, id=str(r.get("eventID") or ""), utc=t, lat=lat, lon=lon, mag=mag, depth=_flt(r.get("depth"))))
    return out


def afad_url(start, end, base=AFAD_API):
    q = [("start", f"{start.astimezone(UTC):%Y-%m-%dT%H:%M:%S}"), ("end", f"{end.astimezone(UTC):%Y-%m-%dT%H:%M:%S}"),
         ("minmag", 4), ("orderby", "timedesc")]
    return base + "?" + urllib.parse.urlencode(q, safe=":")


def afad_match(q, rows):
    """AFAD-da eyni zəlzələ: vaxt ±2 dəqiqə, məsafə 50 km-ə qədər; bir neçəsi varsa vaxtca ən yaxını."""
    best = None
    for a in rows:
        lag = abs((a["utc"] - q["utc"]).total_seconds())
        if lag <= MATCH_S and km_between((a["lat"], a["lon"]), (q["lat"], q["lon"])) <= MATCH_KM:
            if best is None or lag < best[0]:
                best = (lag, a)
    return best[1] if best else None


def _afad_place(a):
    """AFAD-ın il və rayonu yalnız quru ərazidəki zəlzələ üçün: dənizdəkində (ölkə boş, «Akdeniz - [253 km]») yox."""
    return bool(a and a["country"] == "Türkiye" and a["province"] and "[" not in a["location"])


def rest_line(rest):
    rows = sorted(rest, key=lambda q: q["utc"])
    parts = [f"{where(q['pl'])[0]} {ox.az_num(q['mag'], 1)} maqnitudalı ({ox.time_loc(q['utc'].astimezone(BAKU))})"
             for q in rows[:REST_MAX]]
    text = parts[0] if len(parts) == 1 else ", ".join(parts[:-1]) + " və " + parts[-1]
    more = f"; daha {len(rows) - REST_MAX} təkan burada sadalanmır" if len(rows) > REST_MAX else ""
    return f"Bu gün regionda {ox.az_num(MIN_MAG, 1)} və daha güclü daha {len(rows)} zəlzələ qeydə alınıb: {text}{more}."


def quake_item(q, now, rest=(), a=None):
    """Zəlzələ xəbəri. a: AFAD-da eyni zəlzələ (Türkiyə); quru ərazidədirsə il, rayon, məhəllə, güc və dərinlik ondandır."""
    title_loc, where_text = where(q["pl"])
    mag = ox.az_num(q["mag"], 1)
    verb = "qeydə alınıb" if int(q["utc"].timestamp()) % 2 else "olub"   # başlıq iki cür, zəlzələnin saniyəsinə görə
    if _afad_place(a):
        t, amag = a["utc"].astimezone(BAKU), ox.az_num(a["mag"], 1)
        prov, dist, hood = a["province"], a["district"], a["neighborhood"]
        spot = f"{prov} ilinin {dist} rayonunda" if dist and dist != prov else f"{prov} ilində"
        if hood:
            spot += f" ({hood} məhəlləsi)"
        title = f"Türkiyənin {prov} ilində {amag} maqnitudalı zəlzələ {verb}"
        lead = f"{AFAD_GEN} məlumatına görə, {ox.day_loc(t)} Bakı vaxtı ilə {ox.time_loc(t)} {spot} {amag} maqnitudalı zəlzələ baş verib."
        if a["depth"] is not None and a["depth"] >= 0:
            lead += f" Zəlzələnin ocağı {num(a['depth'], 2)} km dərinlikdə olub."
        body = [f"ABŞ Geoloji Xidməti (USGS) zəlzələnin maqnitudasını {mag} kimi qiymətləndirib."] if amag != mag else []
        lat, lon, credit, link = a["lat"], a["lon"], AFAD_CREDIT, AFAD_EVENT.format(a["id"])
    else:
        t = q["utc"].astimezone(BAKU)
        title = f"{title_loc} {mag} maqnitudalı zəlzələ {verb}"
        lead = f"{USGS_GEN} məlumatına görə, {ox.day_loc(t)} Bakı vaxtı ilə {ox.time_loc(t)} {where_text} {mag} maqnitudalı zəlzələ baş verib."
        if q["depth"] is not None and q["depth"] >= 0:
            lead += f" Zəlzələnin ocağı {num(q['depth'], 1)} km dərinlikdə olub."
        body, lat, lon, credit, link = [], q["lat"], q["lon"], USGS_CREDIT, q["url"]
    body.append(f"Episentr Bakıdan {ox.az_num(baku_km(lat, lon), 0)} km aralıdadır.")
    if rest:
        body.append(rest_line(rest))
    return {"kind": "zelzele-region", "key": QUAKE_KEY + q["id"], "title": title, "lead": lead, "body": body,
            "credit": credit, "link": link, "topic": TOPIC_QUAKE, "slot": f"{now:%H:%M}", "worth": True,
            "mag": q["mag"], "utc": q["utc"].isoformat()}


def quake_plan(quakes, now, done=(), afad=None, seys=None):
    """Bir sorğunun zəlzələlərindən xəbərlər: dərc olunacaqlar (worth) və bu günün dərc olunmayanları («why» ilə).
    afad(q), seys(q): AFAD-da və seismology.az siyahısında eyni zəlzələ və ya None; xəta ata bilər."""
    now = _baku(now)
    done = set(done or ())
    pool = []
    for q in quakes:
        q = dict(q, pl=place(q["place"]))
        q["why"] = _static_why(q)
        if not q["why"]:
            pool.append(q)
    for q in pool:
        q["prim"] = _secondary(q, pool)
    cands = [q for q in pool if q["utc"].astimezone(BAKU).date() == now.date() and q["utc"] <= now and not _done(q, done)]
    slots = max(0, QUAKE_CAP - sum(1 for k in done if k.startswith(QUAKE_KEY)))
    ready = []
    for q in sorted(cands, key=lambda x: (-x["mag"], x["utc"], x["id"])):
        root = _root(q)
        if root is not q:
            q["why"] = (f"eyni bölgədəki {ox.az_num(root['mag'], 1)} maqnitudalı zəlzələnin ({_hm(root['utc'])}) "
                        f"ardınca gəlib: bir hadisə, bir xəbər")
        elif now - q["utc"] > FRESH:
            q["why"] = f"gecikmiş xəbər: zəlzələdən {int((now - q['utc']).total_seconds() // 3600)} saat keçib"
        elif q["status"] != "reviewed":
            q["why"] = f"USGS hələ yoxlamayıb («{q['status'] or 'status yoxdur'}»): növbəti sorğuda"
            q["pending"] = True
        else:
            ready.append(q)
    chosen = []
    for q in ready:
        if len(chosen) >= slots:
            q["why"] = f"gündə {QUAKE_CAP} zəlzələ xəbəri həddi"
            continue
        if seys is not None and az_km(q["lat"], q["lon"]) <= NEAR_AZ_KM:
            try:
                hit = seys(q)
            except Exception as e:  # yoxlanmadısa xəbər yazılır: buraxılmış xəbər təkrardan pisdir
                hit, q["note"] = None, f"seismology.az yoxlanmadı ({_err(e)})"
            if hit:
                q["why"] = f"seismology.az siyahısında var ({hit['area']}, ML {ox.az_num(hit['ml'], 1)}): onun xəbəri dərc olunur"
                continue
        chosen.append(q)
    picked = {id(q) for q in chosen}
    rest = [q for q in cands if id(q) not in picked and q["status"] == "reviewed" and not q["why"].startswith("seismology")
            and not _done(_root(q), done)]
    out = []
    for n, q in enumerate(chosen):
        a = None
        if afad is not None and q["pl"]["country"] in ("Turkey", "Türkiye"):
            try:
                a = afad(q)
            except Exception as e:  # AFAD alınmadısa USGS-in mətni
                q["note"] = f"AFAD alınmadı ({_err(e)})"
        item = quake_item(q, now, rest if n == 0 else (), a)
        if q.get("note"):
            item["note"] = q["note"]
        out.append(item)
    for q in sorted(cands, key=lambda x: x["utc"]):
        if id(q) not in picked:
            out.append(dict(quake_item(q, now), key=QUAKE_SKIP + q["id"], worth=False, why=q["why"] or "səbəb yazılmayıb",
                            pending=bool(q.get("pending"))))
    return out


def _afad_lookup(get, start, end):
    """AFAD-a bir sorğu (yalnız ilk dəfə lazım olanda); alınmadısa xəta atır və USGS-in mətni yazılır."""
    box = {}

    def look(q):
        if "rows" not in box:
            box["rows"], box["err"] = None, None
            try:
                box["rows"] = parse_afad(get(afad_url(start, end)))
            except Exception as e:
                box["err"] = e
        if box["rows"] is None:
            raise box["err"] or LookupError("AFAD")
        return afad_match(q, box["rows"])
    return look


def _seys_lookup(get):
    box = {}

    def look(q):
        if "rows" not in box:
            try:
                box["rows"] = ox.seys_list(get(ox.SEYS_LIST, accept="text/html").decode("utf-8", "replace"))
            except Exception as e:
                box["rows"], box["err"] = None, e
        if box["rows"] is None:
            raise box["err"]
        return next((s for s in box["rows"] if abs((s["utc"] - q["utc"]).total_seconds()) <= MATCH_S), None)
    return look


def _quake_mark(now, why):
    """Saatın sorğu qeydi (dərc olunmur): açarı done-a düşəndən sonra həmin saatda USGS-ə ikinci sorğu getmir."""
    return _fail("zelzele-sorgu", f"{QUAKE_TICK}{now:%Y-%m-%dT%H}", "Regionda zəlzələ: saatın sorğusu", why,
                 USGS_CREDIT, USGS_MAP, TOPIC_QUAKE, now)


def quakes_now(now, get, done):
    """İstehsalın bir tiki: USGS-in son 24 saatı. Saatda bir sorğu; hələ yoxlanmamış zəlzələ qayıtmır (növbəti tikdə)."""
    if f"{QUAKE_TICK}{now:%Y-%m-%dT%H}" in done:
        return []
    try:
        doc = parse_usgs(get(usgs_url(now - DAY, now)))
    except Exception as e:
        return [_quake_mark(now, f"USGS alınmadı: {_err(e)}" if not isinstance(e, ValueError) else str(e))]
    gen_at = doc["generated"]
    if gen_at is not None and now - gen_at > STALE:
        t = gen_at.astimezone(BAKU)
        return [_quake_mark(now, f"USGS cavabı köhnədir: {ox.day_text(t)} {t:%H:%M} tarixlidir")]
    plan = quake_plan(doc["quakes"], now, done, afad=_afad_lookup(get, now - DAY, now + 5 * MINUTE), seys=_seys_lookup(get))
    out = [i for i in plan if not i.get("pending")]
    new = sum(1 for i in out if i["worth"])
    return out + [_quake_mark(now, f"bu saatın sorğusu göndərilib: {new} yeni xəbər")]


# --- 2. Asteroidlər ----------------------------------------------------------------------------------------------------

CAD_API = "https://ssd-api.jpl.nasa.gov/cad.api"
CAD_PAGE = "https://cneos.jpl.nasa.gov/ca/"
SBDB_PAGE = "https://ssd.jpl.nasa.gov/tools/sbdb_lookup.html#/?sstr={}"
JPL_CREDIT = "NASA-nın Reaktiv Hərəkət Laboratoriyası (JPL)"
JPL_GEN = "NASA-nın Reaktiv Hərəkət Laboratoriyasının (JPL)"
AU_KM = 149597870.7
LD_KM = 384400.0
DIGEST_AU = 0.05
TT_UTC = 69.184             # TDB ilə UTC fərqi, saniyə (TT − UTC; TDB − TT 2 ms-dən azdır)
AST_WINDOW = ("13:00", "16:00")
AST_SLOT = "13:10"
DIGEST_MAX = 12
TIMED = datetime.timedelta(minutes=30)   # keçid vaxtının xətası bundan azdırsa saat da yazılır


def cad_url(d1, d2, dist):
    q = [("date-min", d1.isoformat()), ("date-max", d2.isoformat()), ("dist-max", dist), ("diameter", "true"),
         ("fullname", "true")]
    return CAD_API + "?" + urllib.parse.urlencode(q)


def _tsig(s):
    """JPL-in keçid vaxtı xətası: «< 00:01» -> 0, «01:40» -> 1 saat 40 dəq, «2_00:46» -> 2 gün 46 dəq; tanınmırsa None."""
    s = str(s or "").strip()
    if s.startswith("<"):
        return datetime.timedelta(0)
    m = re.fullmatch(r"(?:(\d+)_)?(\d+):(\d\d)", s)
    if not m:
        return None
    return datetime.timedelta(days=int(m.group(1) or 0), hours=int(m.group(2)), minutes=int(m.group(3)))


def _ast_name(full, des):
    full = " ".join(str(full or "").split())
    m = re.fullmatch(r"\((.+)\)", full)
    return m.group(1) if m else (full or des)


def _cad_row(r, ix):
    def cell(name):
        i = ix.get(name)
        return r[i] if i is not None and isinstance(r, list) and i < len(r) else None
    jd, dist, v = _flt(cell("jd")), _flt(cell("dist")), _flt(cell("v_rel"))
    des = " ".join(str(cell("des") or "").split())
    if jd is None or dist is None or v is None or dist <= 0 or not des:
        return None
    try:
        utc = datetime.datetime.fromtimestamp((jd - 2440587.5) * 86400.0 - TT_UTC, tz=UTC)
    except (OverflowError, OSError, ValueError):
        return None
    km = dist * AU_KM
    return {"des": des, "name": _ast_name(cell("fullname"), des), "utc": utc, "au": dist, "km": km, "ld": km / LD_KM,
            "v": v, "h": _flt(cell("h")), "diam": _flt(cell("diameter")), "sigma": _tsig(cell("t_sigma_f"))}


def parse_cad(raw):
    """JPL CAD cavabı -> [keçid]. Boş cavab (count 0) boş siyahıdır, pozuq cavab ValueError."""
    try:
        doc = _json(raw)
    except (UnicodeDecodeError, ValueError, TypeError) as e:
        raise ValueError("JPL cavabı JSON deyil") from e
    if not isinstance(doc, dict) or "signature" not in doc:
        raise ValueError("JPL cavabı tanınmadı")
    try:
        count = int(doc.get("count") or 0)
    except (TypeError, ValueError):
        raise ValueError("JPL cavabında say oxunmadı") from None
    if count == 0:
        return []
    fields, data = doc.get("fields"), doc.get("data")
    if not isinstance(fields, list) or not isinstance(data, list):
        raise ValueError("JPL cavabında sahələr yoxdur")
    ix = {f: i for i, f in enumerate(fields)}
    for need in ("des", "jd", "dist", "v_rel"):
        if need not in ix:
            raise ValueError(f"JPL cavabında «{need}» sahəsi yoxdur")
    return [x for x in (_cad_row(r, ix) for r in data) if x]


def _metres(x):
    return max(1, _half_up(x)) if x < 100 else _half_up(x / 10.0) * 10


def size_text(row):
    """«diametri təxminən 18–40 metr»: JPL diametr verməyibsə parlaqlıqdan (albedo 0,25–0,05)."""
    if row["diam"]:
        d = row["diam"] * 1000
        return f"diametri {num(row['diam'], 1)} km" if d >= 1000 else f"diametri {_metres(d)} metr"
    if row["h"] is None:
        return ""
    lo = 1329000.0 / math.sqrt(0.25) * 10 ** (-row["h"] / 5)
    hi = 1329000.0 / math.sqrt(0.05) * 10 ** (-row["h"] / 5)
    if hi >= 1000:
        a, b = num(lo / 1000, 1), num(hi / 1000, 1)
        return f"diametri təxminən {a}–{b} km" if a != b else f"diametri təxminən {a} km"
    a, b = _metres(lo), _metres(hi)
    return f"diametri təxminən {a}–{b} metr" if a != b else f"diametri təxminən {a} metr"


def km_text(km):
    return f"{ox.az_num(km / 1e6, 2)} milyon km" if km >= 1e6 else f"{ox.az_num(_half_up(km), 0)} km"


def _ast_when(r, loc=True):
    """Keçid vaxtı Bakı vaxtı ilə: xətası 30 dəqiqədən azdırsa saatı da, 1 gündən çoxdursa «təxminən»."""
    t = _minute(r["utc"]).astimezone(BAKU)
    sig = r["sigma"]
    if sig is not None and sig < TIMED:
        return f"{ox.day_loc(t)} Bakı vaxtı ilə {ox.time_loc(t)}" if loc else f"{ox.day_text(t)}, {t:%H:%M}"
    day = ox.day_loc(t) if loc else ox.day_text(t)
    if sig is None or sig >= DAY:
        return f"təxminən {day}"
    return day


def asteroid_event_item(rows, day, now):
    """Bu gün (Bakı vaxtı) Aydan yaxın keçid: ən böyüyü (H ən kiçik), qalanları bir cümlədə. Yoxdursa (None, səbəb)."""
    now = _baku(now)
    sub = [r for r in rows if r["ld"] < 1 and _minute(r["utc"]).astimezone(BAKU).date() == day]
    if not sub:
        return None, "bu gün Aydan yaxın keçən asteroid yoxdur"
    main = min(sub, key=lambda r: (r["h"] if r["h"] is not None else 99.0, r["ld"]))
    others = sorted((r for r in sub if r is not main), key=lambda r: r["utc"])
    verb = "keçəcək" if main["utc"] > now else "keçib"
    k = 1 / main["ld"]
    closer = f"Aydan {_half_up(k)} dəfə yaxın" if k >= 1.5 else "Aydan yaxın"
    title = f"{main['name']} asteroidi bu gün Yerin yanından {closer} məsafədən {verb}"
    lead = (f"{JPL_GEN} məlumatına görə, {main['name']} asteroidi {_ast_when(main)} Yerdən {km_text(main['km'])}, yəni "
            f"Yer–Ay məsafəsinin {poss(ox.az_num(main['ld'], 2))} qədər məsafədən saniyədə {num(main['v'], 1)} km sürətlə {verb}.")
    body = []
    size = size_text(main)
    if size:
        body.append(f"Parlaqlığına görə asteroidin {size} qiymətləndirilir." if not main["diam"]
                    else f"JPL-in məlumatına görə, asteroidin {size}-dir.")
    if others:
        names = ", ".join(f"{r['name']} ({km_text(r['km'])})" for r in others)
        body.append(f"Bu gün Yerin yanından Aydan yaxın məsafədən daha {len(others)} asteroid keçir: {names}.")
    body.append("Məsafə Yerin mərkəzindən ölçülür; Yer–Ay məsafəsi orta hesabla 384 400 km-dir.")
    item = {"kind": "asteroid", "key": f"asteroid-gun-{day.isoformat()}", "title": title, "lead": lead, "body": body,
            "credit": JPL_CREDIT, "link": SBDB_PAGE.format(urllib.parse.quote(main["des"])), "topic": "kosmos",
            "slot": AST_SLOT, "worth": True}
    return item, ""


def asteroid_digest_item(rows, now):
    """Bazar ertəsi: növbəti 7 gündə 0,05 AB-dən yaxın keçidlər. Yoxdursa (None, səbəb)."""
    now = _baku(now)
    week = sorted((r for r in rows if now <= r["utc"] < now + 7 * DAY and r["au"] <= DIGEST_AU), key=lambda r: r["utc"])
    if not week:
        return None, "növbəti 7 gündə Yerə 0,05 AB-dən yaxın keçən asteroid yoxdur"
    n, far = len(week), ox.az_num(DIGEST_AU * AU_KM / 1e6, 1)
    first, last = (_minute(week[0]["utc"]).astimezone(BAKU).date(), _minute(week[-1]["utc"]).astimezone(BAKU).date())
    near = min(week, key=lambda r: r["ld"])
    title = f"Növbəti 7 gündə {n} asteroid Yerə {far} milyon km-dən yaxın məsafədən keçəcək"
    lead = (f"{JPL_GEN} məlumatına görə, {_span(first, last)} {n} asteroid Yerə 0,05 astronomik vahiddən ({far} milyon km) "
            f"yaxın məsafədən keçəcək. Ən yaxını {near['name']} asteroididir: o, {_ast_when(near)} Yerdən "
            f"{km_text(near['km'])} ({ox.az_num(near['ld'], 2)} Ay məsafəsi) uzaqlıqdan keçəcək.")
    sized = [r for r in week if r["h"] is not None]
    big = min(sized, key=lambda r: r["h"]) if sized else None
    if big is not None and big is not near and size_text(big):
        lead += f" Ən böyüyü {big['name']} asteroididir: {size_text(big)}."
    shown = week if n <= DIGEST_MAX else sorted(sorted(week, key=lambda r: r["ld"])[:DIGEST_MAX], key=lambda r: r["utc"])
    body = []
    for r in shown:
        size = size_text(r)
        body.append(f"{_ast_when(r, loc=False)} — {r['name']}: {km_text(r['km'])} ({ox.az_num(r['ld'], 2)} Ay məsafəsi)"
                    + (f", {size}" if size else ""))
    if n > len(shown):
        body.append(f"Daha {n - len(shown)} asteroid bundan uzaq məsafədən keçəcək.")
    body.append("Ay məsafəsi Yerlə Ay arasındakı orta məsafədir (384 400 km); məsafə Yerin mərkəzindən ölçülür, "
                "ölçülər parlaqlığa görə təxminidir.")
    item = {"kind": "asteroid-hefte", "key": f"asteroid-hefte-{now.date().isoformat()}", "title": title, "lead": lead,
            "body": body, "list": True, "credit": JPL_CREDIT, "link": CAD_PAGE, "topic": "kosmos", "slot": AST_SLOT,
            "worth": True}
    return item, ""


def asteroids_now(now, get, done):
    """İstehsalın bir tiki: 13:00–16:00 pəncərəsində, günün xəbəri hələ çıxmayıbsa bir JPL sorğusu."""
    day = now.date()
    if not (_at(day, AST_WINDOW[0]) <= now < _at(day, AST_WINDOW[1])):
        return []
    monday = day.weekday() == 0
    day_key = f"asteroid-gun-{day.isoformat()}"
    key = f"asteroid-hefte-{day.isoformat()}" if monday else day_key
    if key in done:
        return []
    url = cad_url(day - DAY, day + 8 * DAY, str(DIGEST_AU)) if monday else cad_url(day - DAY, day + DAY, "1LD")
    try:
        rows = parse_cad(get(url))
    except Exception as e:
        why = str(e) if isinstance(e, ValueError) else f"JPL alınmadı: {_err(e)}"
        return [_fail("asteroid", key, "Asteroidlər: məlumat alınmadı", why, JPL_CREDIT, CAD_PAGE, "kosmos", now)]
    out = []
    if monday:   # icmalın sorğusu bu günün Aydan yaxın keçidlərini də verir: əlavə sorğu yoxdur
        item, why = asteroid_digest_item(rows, now)
        out.append(item or _fail("asteroid-hefte", key, "Asteroidlər: bu həftə xəbər yoxdur", why, JPL_CREDIT, CAD_PAGE,
                                 "kosmos", now))
    item, why = asteroid_event_item(rows, day, now)
    if item and day_key not in done:
        out.append(item)
    elif not monday:   # sorğu getdi, xəbər yoxdur: açar qayıdır ki, bu pəncərədə bir də sorğu getməsin
        out.append(_fail("asteroid", day_key, "Asteroidlər: bu gün xəbər yoxdur", why, JPL_CREDIT, CAD_PAGE, "kosmos", now))
    return out


# --- 3. Kosmik buraxılışlar --------------------------------------------------------------------------------------------

LL2_API = "https://ll.thespacedevs.com/2.3.0/launches/"
LL2_UP = LL2_API + "upcoming/"
LL2_CREDIT = "The Space Devs (Launch Library 2)"
LL2_GEN = "The Space Devs-in Launch Library 2"
SLN_PAGE = "https://spacelaunchnow.app/launch/{}/"
SLN_UP = "https://spacelaunchnow.app/launch/upcoming/"
LAUNCH_WINDOW = ("10:00", "13:00")
LAUNCH_SLOT = "10:40"
TILE = "13:00"              # D gününün xəbəri D 13:00 – D+1 13:00 arasındakı buraxılışlar
PLANNED = ("Go", "TBC", "TBD")
FLOWN = ("Success", "Failure", "Partial Failure", "In Flight")
WEEK_PREC = ("SEC", "MIN", "HR", "DAY")
EXACT = ("SEC", "MIN")
CREWED = ("Human Exploration", "Tourism")
CC_AZ = {"USA": "ABŞ", "CHN": "Çin", "RUS": "Rusiya", "KAZ": "Qazaxıstan", "NZL": "Yeni Zelandiya",
         "GUF": "Fransa Qvianası", "FRA": "Fransa", "IND": "Hindistan", "JPN": "Yaponiya", "KOR": "Cənubi Koreya",
         "PRK": "Şimali Koreya", "IRN": "İran", "ISR": "İsrail", "AUS": "Avstraliya", "GBR": "Böyük Britaniya",
         "NOR": "Norveç", "SWE": "İsveç", "BRA": "Braziliya", "DEU": "Almaniya", "ESP": "İspaniya", "ITA": "İtaliya",
         "CAN": "Kanada", "MHL": "Marşall Adaları", "UKR": "Ukrayna", "TUR": "Türkiyə", "PRT": "Portuqaliya"}
STATUS_NOTE = {"TBC": "tarix dəqiqləşdirilir", "TBD": "tarix hələ müəyyən deyil"}


def ll2_url(gte, lte, base=LL2_UP, limit=40):
    z = "%Y-%m-%dT%H:%M:%SZ"
    q = [("mode", "normal"), ("limit", limit), ("net__gte", gte.astimezone(UTC).strftime(z)),
         ("net__lte", lte.astimezone(UTC).strftime(z))]
    return base + "?" + urllib.parse.urlencode(q, safe=":")


def _iso(s):
    try:
        t = datetime.datetime.fromisoformat(str(s).replace("Z", "+00:00"))
    except (TypeError, ValueError):
        return None
    return t.replace(tzinfo=UTC) if t.tzinfo is None else t


def _launch(r):
    if not isinstance(r, dict):
        return None
    net = _iso(r.get("net"))
    name = " ".join(str(r.get("name") or "").split())
    if net is None or not name:
        return None
    rocket, _, payload = name.partition(" | ")

    def sub(obj, *keys):
        for k in keys:
            obj = obj.get(k) if isinstance(obj, dict) else None
        return obj or ""
    pad = r.get("pad") if isinstance(r.get("pad"), dict) else {}
    return {"id": str(r.get("id") or ""), "slug": str(r.get("slug") or ""), "name": name, "rocket": rocket,
            "rocket_full": sub(r, "rocket", "configuration", "full_name"), "mission": sub(r, "mission", "name") or payload,
            "mtype": sub(r, "mission", "type"), "status": sub(r, "status", "abbrev"), "net": net,
            "prec": sub(r, "net_precision", "abbrev"), "win_start": _iso(r.get("window_start")),
            "win_end": _iso(r.get("window_end")), "lsp": sub(r, "launch_service_provider", "name"),
            "site": sub(pad, "location", "name").split(",")[0].strip(), "cc": sub(pad, "country", "alpha_3_code")}


def parse_ll2(raw):
    try:
        doc = _json(raw)
    except (UnicodeDecodeError, ValueError, TypeError) as e:
        raise ValueError("LL2 cavabı JSON deyil") from e
    rows = doc.get("results") if isinstance(doc, dict) else None
    if not isinstance(rows, list):
        raise ValueError("LL2 cavabında buraxılış siyahısı yoxdur")
    return [x for x in (_launch(r) for r in rows) if x]


def crewed(launch):
    return launch["mtype"] in CREWED


def starship(launch):
    return launch["rocket"].startswith("Starship")


def mission_text(m):
    """«Unknown Payload» -> «naməlum yük»; «SatNet LEO Group TBD?» -> «SatNet LEO Group»; «(Starship Flight 15)» -> «(Starship-in 15-ci uçuşu)»."""
    m = re.sub(r"\s*\bTBD\??$", "", m).strip()
    if m in ("Unknown Payload", "Unknown", ""):
        return "naməlum yük"
    return re.sub(r"\(Starship Flight (\d+)\)", lambda x: f"(Starship-in {ox.ordinal(x.group(1))} uçuşu)", m)


def _flight(launch):
    m = re.search(r"\bFlight (\d+)\b", launch["name"])
    return int(m.group(1)) if m else None


def _who(launch):
    """«Starship-in 15-ci uçuşu», «pilotlu Shenzhou 24 missiyası»."""
    if starship(launch):
        n = _flight(launch)
        return f"Starship-in {ox.ordinal(n)} uçuşu" if n else "Starship raketinin buraxılışı"
    return f"pilotlu {mission_text(launch['mission'])} missiyası"


def _when_launch(launch, loc=True):
    t = launch["net"].astimezone(BAKU)
    if launch["prec"] in EXACT:
        return f"{ox.day_loc(t)} Bakı vaxtı ilə {ox.time_loc(t)}" if loc else f"{ox.day_text(t)}, {t:%H:%M}"
    if launch["prec"] == "HR":
        return f"{ox.day_loc(t)} Bakı vaxtı ilə təxminən {ox.time_loc(t)}" if loc else f"{ox.day_text(t)}, təxminən {t:%H:%M}"
    return ox.day_loc(t) if loc else ox.day_text(t)


def launch_digest_item(launches, now, end):
    """Bazar ertəsi: [now, end) arasında planlaşdırılan buraxılışlar. Yoxdursa (None, səbəb)."""
    rows = sorted((x for x in launches if now < x["net"] < end and x["status"] in PLANNED and x["prec"] in WEEK_PREC),
                  key=lambda x: (x["net"], x["name"]))
    if not rows:
        return None, "bu həftə planlaşdırılan kosmik buraxılış yoxdur"
    n = len(rows)
    first, last = rows[0]["net"].astimezone(BAKU).date(), (end - MINUTE).astimezone(BAKU).date()
    marks = [x for x in rows if starship(x) or crewed(x)]
    title = f"Bu həftə dünyada {n} kosmik buraxılış planlaşdırılır"
    names = [("Starship" if starship(x) else f"pilotlu {mission_text(x['mission'])}") for x in marks]
    if names:
        extra = f", aralarında {' və '.join(dict.fromkeys(names))} var"
        if len(title + extra) <= TITLE_MAX:
            title += extra
    lead = f"{LL2_GEN} məlumatına görə, {_span(min(first, last), last)} dünyada {n} raket buraxılışı planlaşdırılır."
    for x in marks:
        note = STATUS_NOTE.get(x["status"])
        lead += f" Onların arasında {_when_launch(x)} {_who(x)} var" + (f" ({note})." if note else ".")
    body = []
    for x in rows:
        where_ = CC_AZ.get(x["cc"], "")
        note = STATUS_NOTE.get(x["status"])
        body.append(f"{_when_launch(x, loc=False)} — " + (f"{where_}: " if where_ else "") + f"{x['rocket']}, "
                    f"{mission_text(x['mission'])}" + (f" ({note})" if note else ""))
    item = {"kind": "buraxilis-hefte", "key": f"buraxilis-hefte-{now.date().isoformat()}", "title": title, "lead": lead,
            "body": body, "list": True, "credit": LL2_CREDIT, "link": SLN_UP, "topic": "kosmos", "slot": LAUNCH_SLOT,
            "worth": True}
    return item, ""


def launch_day_item(x, day, now, others=()):
    """Pilotlu buraxılış və ya Starship: D 13:00 – D+1 13:00 arasında. Dərc yalnız «Go» və dəqiq vaxtla."""
    t = x["net"].astimezone(BAKU)
    rel = "bu gün" if t.date() == day else ("bu gecə" if t.hour < 6 else "sabah")
    where_ = CC_AZ.get(x["cc"], "")
    site = f"{x['site']} ({where_})" if x["site"] and where_ else (x["site"] or where_)
    if starship(x):
        n = _flight(x)
        head = f"Starship-in {ox.ordinal(n)} uçuşu" if n else "Starship raketinin buraxılışı"
        title = f"{head} {rel} {ox.time_loc(t)} planlaşdırılır"
        lead = (f"{LL2_GEN} məlumatına görə, Starship raketinin " + (f"{ox.ordinal(n)} uçuşu " if n else "buraxılışı ")
                + f"{_when_launch(x)}" + (f" {site} buraxılış meydançasından" if site else "") + " planlaşdırılır.")
    else:
        mission = mission_text(x["mission"])
        title = f"Pilotlu {mission} missiyasının buraxılışı {rel} {ox.time_loc(t)} planlaşdırılır"
        lead = (f"{LL2_GEN} məlumatına görə, pilotlu {mission} missiyası {_when_launch(x)} {x['rocket']} raketi ilə"
                + (f" {site} buraxılış meydançasından" if site else "") + " buraxılacaq.")
    body = [f"Raket: {x['rocket_full'] or x['rocket']}", f"Missiya: {mission_text(x['mission'])}"]
    ws, we = x["win_start"], x["win_end"]
    if ws and we and we > ws:
        body.append(f"Buraxılış pəncərəsi Bakı vaxtı ilə {_hm(ws)}–{_hm(we)} arasıdır")
    for o in others:
        body.append(f"Həmin gün {_when_launch(o)} {_who(o)} da planlaşdırılır")
    item = {"kind": "buraxilis", "key": f"buraxilis-gun-{day.isoformat()}", "title": title, "lead": lead, "body": body,
            "list": True, "credit": LL2_CREDIT, "link": SLN_PAGE.format(x["slug"]) if x["slug"] else SLN_UP,
            "topic": "kosmos", "slot": LAUNCH_SLOT, "worth": True}
    if x["status"] != "Go":
        item.update(worth=False, why=f"buraxılış təsdiqlənməyib (LL2 statusu {x['status'] or 'yoxdur'})")
    elif x["prec"] not in EXACT:
        item.update(worth=False, why="buraxılış vaxtı dəqiqəyədək məlum deyil")
    elif x["net"] <= now:
        item.update(worth=False, why="buraxılış vaxtı keçib")
    return item


def launch_day_items(launches, day, now):
    """D gününün pilotlu və Starship buraxılışları (D 13:00 – D+1 13:00): dərc olunan bir xəbər, qalanları «why» ilə."""
    lo, hi = _at(day, TILE), _at(day + DAY, TILE)
    cands = sorted((x for x in launches if lo <= x["net"] < hi and (crewed(x) or starship(x))), key=lambda x: x["net"])
    items_ = [launch_day_item(x, day, now) for x in cands]
    ok = [x for x, i in zip(cands, items_) if i["worth"]]
    out = []
    if ok:
        out.append(launch_day_item(ok[0], day, now, ok[1:]))
    for x, i in zip(cands, items_):
        if not i["worth"]:
            out.append(dict(i, key=f"{i['key']}-{x['slug'][:48] or x['id'][:8]}"))
    return out


def _launch_fail(now, key, why):
    return _fail("buraxilis", key, "Kosmik buraxılışlar: məlumat alınmadı", why, LL2_CREDIT, SLN_UP, "kosmos", now)


def launches_now(now, get, done):
    """İstehsalın bir tiki: 10:00–13:00 pəncərəsində, günün xəbəri hələ çıxmayıbsa bir LL2 sorğusu."""
    day = now.date()
    if not (_at(day, LAUNCH_WINDOW[0]) <= now < _at(day, LAUNCH_WINDOW[1])):
        return []
    monday = day.weekday() == 0
    key = f"buraxilis-hefte-{day.isoformat()}" if monday else f"buraxilis-gun-{day.isoformat()}"
    if key in done:
        return []
    start, end = (now, _at(day + 7 * DAY, "00:00")) if monday else (_at(day, TILE), _at(day + DAY, TILE))
    try:
        launches = parse_ll2(get(ll2_url(start, end)))
    except Exception as e:
        return [_launch_fail(now, key, str(e) if isinstance(e, ValueError) else f"LL2 alınmadı: {_err(e)}")]
    out = []
    if monday:   # icmalın sorğusu bu günün pilotlu və Starship buraxılışlarını da verir: əlavə sorğu yoxdur
        item, why = launch_digest_item(launches, now, end)
        out.append(item or _fail("buraxilis-hefte", key, "Kosmik buraxılışlar: bu həftə xəbər yoxdur", why, LL2_CREDIT,
                                 SLN_UP, "kosmos", now))
    day_key = f"buraxilis-gun-{day.isoformat()}"
    if day_key not in done:
        found = launch_day_items(launches, day, now)
        out += found
        if not monday and not any(i["key"] == day_key for i in found):   # sorğu getdi, xəbər yoxdur: açar qayıdır
            out.append(_fail("buraxilis", day_key, "Kosmik buraxılışlar: bu gün xəbər yoxdur",
                             "13:00-dan sabah 13:00-dək təsdiqlənmiş pilotlu buraxılış və ya Starship yoxdur", LL2_CREDIT,
                             SLN_UP, "kosmos", now))
    return out


# --- Canlı ---------------------------------------------------------------------------------------------------------------


def items(root, now, fetch=None, done=None):
    """now anında (Bakı vaxtı) dərc olunacaq yer və kosmos xəbərləri. Sorğu yalnız tikdə və fetch ilə; done: bu gün dərc
    olunmuş açarlar (onların sorğusu getmir). worth=False olanlar «why» ilə qayıdır. Heç vaxt xəta atmır."""
    try:
        now = _baku(now)
        done = set(done or ())
    except Exception:
        return []
    if not tick(now):
        return []
    get = _Get(fetch)
    out = []
    for part in (quakes_now, launches_now, asteroids_now):
        try:
            out += part(now, get, done)
        except Exception as e:  # bir hissənin xətası digərlərini saxlamır
            out.append(_fail("xeta", f"yer-kosmos-xeta-{part.__name__}-{now:%Y-%m-%dT%H}", "Modul xətası",
                             f"{part.__name__}: {_err(e)}", USGS_CREDIT, USGS_MAP, "kosmos", now))
    return [_guard(i) for i in out]


# --- Sınaq ---------------------------------------------------------------------------------------------------------------


def _verdict(item):
    return "✅ Dərc olunardı" if item.get("worth") else f"⏭ Dərc olunmazdı: {item.get('why') or 'səbəb yazılmayıb'}"


def _show(label, item):
    item = _guard(item)
    md = [f"**{label}**", ""] + ox.render(item)
    if item.get("note"):
        md += [f"> {item['note']}", ""]
    return md + [_verdict(item), ""]


def _label_day(d):
    return f"{ox.day_text(d)} {d.year}"


def replay_day(day, quakes, afad=None, seys=None, delay=30):
    """O günün istehsal tikləri (dəqiqə 10·(h mod 6)+5), USGS zəlzələni delay dəqiqə sonra verir fərziyyəsi ilə:
    [(tik vaxtı, xəbər)]: dərc olunanlar və hər zəlzələnin ilk dəfə dərc olunmayan qərarı."""
    done, seen, out = set(), set(), []
    for h in range(24):
        t = _at(day, f"{h:02d}:{10 * (h % 6) + 5:02d}")
        vis = [q for q in quakes if q["utc"] + delay * MINUTE <= t and q["utc"] >= t - DAY]
        for item in quake_plan(vis, t, done, afad, seys):
            if item["key"] in seen:
                continue
            seen.add(item["key"])
            out.append((t, item))
            if not item.get("pending"):   # istehsal kimi: qayıdan hər qəti açar done-a düşür
                done.add(item["key"])
    return out


def _sinaq_quakes(now, get):
    md = []
    try:
        doc = parse_usgs(get(usgs_url(now - DAY, now)))
        todays = quake_plan(doc["quakes"], now, set(), _afad_lookup(get, now - DAY, now + 5 * MINUTE), _seys_lookup(get))
        md += [f"**Bu gün, {_label_day(now.date())}, {now:%H:%M}: istehsalın sorğusu (son 24 saat), "
               f"{len(doc['quakes'])} zəlzələ.**", ""]
        for item in todays:
            md += _show(f"{ox.day_text(now)} {now:%H:%M}", item)
        if not todays:
            md += ["⏭ Dərc olunmazdı: bu gün (Bakı vaxtı) regionda 4,5 və daha güclü zəlzələ olmayıb.", ""]
        for q in doc["quakes"]:
            t = q["utc"].astimezone(BAKU)
            if t.date() != now.date():
                md += [f"- Dünənki zəlzələ yazılmır: {t:%d.%m %H:%M}, {ox.az_num(q['mag'], 1)}, «{q['place']}»."]
        md += [""]
    except Exception as e:
        md += [f"> USGS alınmadı: {_err(e)} {e}"[:300], ""]
    start = now - 14 * DAY
    try:
        doc = parse_usgs(get(usgs_url(start, now)))
    except Exception as e:
        return md + [f"> USGS (14 gün) alınmadı: {_err(e)}", ""]
    quakes = doc["quakes"]
    why = {}
    for q in quakes:
        w = _static_why(dict(q, pl=place(q["place"])))
        why.setdefault(w or "regionda", []).append(q)
    md += [f"**Son 14 gün:** qutuda {ox.az_num(MIN_MAG, 1)} və daha güclü {len(quakes)} zəlzələ; regionda "
           f"{len(why.get('regionda', []))}. Süzgəcdən keçməyənlər: "
           + "; ".join(f"{k} — {len(v)}" for k, v in sorted(why.items()) if k != "regionda") + ".", ""]
    try:
        afad_rows = parse_afad(get(afad_url(start, now)))
    except Exception as e:
        afad_rows, md = None, md + [f"> AFAD alınmadı: {_err(e)}", ""]

    def afad(q):
        if afad_rows is None:
            raise LookupError("AFAD alınmadı")
        return afad_match(q, afad_rows)
    days = sorted({q["utc"].astimezone(BAKU).date() for q in why.get("regionda", [])}, reverse=True)
    for day in days[:3]:
        for t, item in replay_day(day, quakes, afad, _seys_lookup(get)):
            md += _show(f"Son real hal: {_label_day(day)}, istehsal tiki {t:%H:%M}", item)
    if not days:
        md += ["> Son 14 gündə regionda 4,5 və daha güclü zəlzələ olmayıb.", ""]
    return md


def _monday_on_or_before(day):
    return day - DAY * day.weekday()


def _sinaq_launches(now, get):
    md = []
    monday = _monday_on_or_before(now.date())
    if now < _at(monday, LAUNCH_SLOT):
        monday -= 7 * DAY
    at = _at(monday, LAUNCH_SLOT)
    url = ll2_url(_at(monday, LAUNCH_WINDOW[0]), _at(monday + 14 * DAY, "00:00"), base=LL2_API, limit=80)
    try:
        launches = parse_ll2(get(url))
    except Exception as e:
        return [f"> LL2 alınmadı: {_err(e)}", ""]
    replay = [dict(x, status="Go") if x["status"] in FLOWN else x for x in launches]
    item, why = launch_digest_item(replay, at, _at(monday + 7 * DAY, "00:00"))
    label = (f"Son real hal: {_label_day(monday)} (bazar ertəsi) icmalı, {LAUNCH_SLOT}; bugünkü məlumatla, o vaxtdan uçmuş "
             f"buraxılışlar da planlaşdırılan kimi")
    md += _show(label, item) if item else [f"**{label}:** ⏭ Dərc olunmazdı: {why}", ""]
    today = now.date()
    if today.weekday() != 0:
        t = max(now, _at(today, LAUNCH_SLOT))
        found = launch_day_items(launches, today, t)
        for it in found:
            md += _show(f"Bu gün, {_label_day(today)}: pilotlu buraxılış və ya Starship (13:00-dan sabah 13:00-dək)", it)
        if not found:
            md += [f"**Bu gün, {_label_day(today)}:** ⏭ Dərc olunmazdı: 13:00-dan sabah 13:00-dək pilotlu buraxılış və ya "
                   f"Starship yoxdur.", ""]
    nxt = sorted((x for x in launches if x["net"] > now and (crewed(x) or starship(x)) and x["status"] in PLANNED),
                 key=lambda x: x["net"])
    for x in nxt[:2]:
        day = (x["net"].astimezone(BAKU) - (_at(today, TILE) - _at(today, "00:00"))).date()
        it = launch_day_items([x], day, _at(day, LAUNCH_SLOT))[0]
        md += _show(f"Növbəti hal: {x['name']}, xəbər {_label_day(day)} {LAUNCH_SLOT}-da (bugünkü statusla)", it)
    nmon = monday + 7 * DAY
    if nmon > today:
        item, why = launch_digest_item(launches, _at(nmon, LAUNCH_SLOT), _at(nmon + 7 * DAY, "00:00"))
        label = f"Növbəti bazar ertəsi, {_label_day(nmon)}: bugünkü siyahı ilə"
        md += _show(label, item) if item else [f"**{label}:** ⏭ Dərc olunmazdı: {why}", ""]
    try:
        prev = parse_ll2(get(LL2_API + "previous/?" + urllib.parse.urlencode([("mode", "normal"), ("limit", 1),
                                                                            ("is_crewed", "true")])))
    except Exception as e:
        return md + [f"> LL2 (son pilotlu buraxılış) alınmadı: {_err(e)}", ""]
    for x in prev[:1]:
        x = dict(x, status="Go")
        day = (x["net"].astimezone(BAKU) - (_at(today, TILE) - _at(today, "00:00"))).date()
        it = launch_day_items([x], day, _at(day, LAUNCH_SLOT))[0]
        md += _show(f"Son real pilotlu buraxılış: {x['name']}, xəbər {_label_day(day)} {LAUNCH_SLOT}-da", it)
    return md


def _sinaq_asteroids(now, get):
    today = now.date()
    monday = _monday_on_or_before(today)
    if now < _at(monday, AST_SLOT):
        monday -= 7 * DAY
    try:
        rows = parse_cad(get(cad_url(today - 14 * DAY, monday + 15 * DAY, str(DIGEST_AU))))
    except Exception as e:
        return [f"> JPL alınmadı: {_err(e)}", ""]
    md = []
    item, why = asteroid_digest_item(rows, _at(monday, AST_SLOT))
    label = f"Son real hal: {_label_day(monday)} (bazar ertəsi) icmalı, {AST_SLOT}; bugünkü siyahı ilə (sonra tapılanlar da var)"
    md += _show(label, item) if item else [f"**{label}:** ⏭ Dərc olunmazdı: {why}", ""]
    if today.weekday() != 0:
        item, why = asteroid_event_item(rows, today, max(now, _at(today, AST_SLOT)))
        label = f"Bu gün, {_label_day(today)}: Aydan yaxın keçid"
        md += _show(label, item) if item else [f"**{label}:** ⏭ Dərc olunmazdı: {why}", ""]
    for back in range(1, 15):
        day = today - back * DAY
        if day.weekday() == 0:
            continue
        item, _ = asteroid_event_item(rows, day, _at(day, AST_SLOT))
        if item:
            md += _show(f"Aydan yaxın keçidin son real halı: {_label_day(day)}, {AST_SLOT}", item)
            break
    nmon = monday + 7 * DAY
    item, why = asteroid_digest_item(rows, _at(nmon, AST_SLOT))
    label = f"Növbəti bazar ertəsi, {_label_day(nmon)}: bugünkü siyahı ilə"
    md += _show(label, item) if item else [f"**{label}:** ⏭ Dərc olunmazdı: {why}", ""]
    return md


def sinaq(root, now=None, fetch=None):
    """Nümunələr (Markdown): bu günün qərarı və hər xəbər növünün son real halı, real sorğularla (~8 sorğu).
    Sayta və repoya heç nə yazmır. fetch verilməyibsə updater-in fetch-i işlənir."""
    now = _baku(now)
    get = _Get(fetch, pause=PAUSE)
    md = ["# Yer və kosmos xəbərləri (oz_yer_kosmos.py): sınaq", "",
          f"{now:%d.%m.%Y %H:%M} (Bakı vaxtı). Sayta heç nə yazılmır. İstehsalda sorğu yalnız tikdə gedir (saat h-da "
          f"dəqiqə 10·(h mod 6)): USGS gündə ən çox 24, LL2 və JPL gündə 1; AFAD və seismology.az yalnız dərc olunacaq "
          f"zəlzələ üçün (gündə ən çox 2). Cəmi gündə ən çox 30 sorğu.", ""]
    for head, part in (("## 1. Regionda zəlzələ (USGS; Türkiyə üçün AFAD)", _sinaq_quakes),
                       ("## 2. Kosmik buraxılışlar (The Space Devs, Launch Library 2)", _sinaq_launches),
                       ("## 3. Asteroidlər (NASA JPL, CAD API)", _sinaq_asteroids)):
        md += [head, ""]
        try:
            md += part(now, get)
        except Exception as e:
            md += [f"> Sınaq xətası: {_err(e)}: {e}"[:300], ""]
    md += ["## Sorğular", "", f"Bu sınaqda {get.count} sorğu göndərilib: "
           + ", ".join(f"{h} {n}" for h, n in sorted(get.hosts.items())) + ".", ""]
    return md


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
