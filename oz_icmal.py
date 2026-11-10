"""8ulduz-un öz xəbərləri, faza 1: icmal xəbərləri (sahib, 2026-11-10: «Bəli, başla»). Sayta hələ qoşulmayıb.

1. «Günün bələdçisi» (hər gün 08:00): səhər xülasəsi və günün oyunları bir xəbərdə. Ad saytın 09:00-dakı «Səhər icmalı»
   səhifəsi ilə qarışmasın deyə belədir. Siyahı:
   - Bakı və beş şəhərin (Gəncə, Sumqayıt, Lənkəran, Şəki, Naxçıvan) bu günkü proqnozu, Open-Meteo, bir sorğu: ən aşağı və
     ən yüksək temperatur, yağıntı ehtimalı, külək. Havanın təsviri Open-Meteo-nun hava kodundan sabit cədvəllə gəlir (SKY).
   - AMB-nin son bülleteni öz tarixi ilə (XML-in ValCurs Date-i; markets.json-un asOf-u sorğunun günüdür). Saat 08:00-da bu,
     adətən əvvəlki iş gününün bülletenidir: yeni bülleten iş günləri ~09:00–09:20-də çıxır.
   - Bu günün oyunları Bakı vaxtı ilə, 08:00-dan gecə 04:00-dək (Avropada saat 21:00 oyunu Bakıda 00:00-dır): Azərbaycan
     millisi, avrokubokda Azərbaycan klubu, Premyer Liqa, Kubok, I və II Liqa, saytın izlədiyi xarici klublar; ən çox 5 sətir.
     Saatı bəlli olmayan oyun yazılmır: təxirə salınan, saatı 00:00 olan, pfl.az-da stadionsuz (turun cədvəli açıqlanmayıb,
     tarix şərtidir), turun bütün oynanmamış oyunları eyni saata yazılıbsa və xarici liqa turunun 7+ oyunu bir saatdadırsa
     (yer tutucu cədvəl). UEFA kuboklarının liqa mərhələsində bu qayda yoxdur: son tur qaydaya görə eyni saatda oynanır.
   - Günün qeyd olunan günləri (oz_teqvim.gun_adlari) və həftə içində iş günü olmaması (oz_teqvim.qeyri_is_gunu).
   Məlumatı olmayan hissə yazılmır. Hava da, oyun da yoxdursa xəbər dərc olunmur.
2. «Həftənin rəqəmləri» (bazar 12:00): son 7 günün (keçən bazardan şənbəyədək) bazardan kənar rəqəmləri. Brent, qızıl,
   bitkoin və AMB məzənnələrinin həftəlik dəyişməsi burada yoxdur: o, şənbə günü «Həftənin bazarları»ndadır (oz_bazar,
   həftənin son bülleteni 7 gün əvvəlki ilə), bazar günü təkrar yazılmır.
   - 3,0 və daha güclü zəlzələlər: seismology.az siyahısı (oz_xeber.seys_list). Zəlzələ yoxdursa sətir yazılmır.
   - Bakıda 7 günün ən yüksək və ən aşağı temperaturu: Open-Meteo (model məlumatı).
   - Premyer Liqada 7 gündə vurulan qollar: data/futbol/premyer-liqa.json.
   Ən azı iki hissə olmalıdır.

Sorğular yalnız fetch ilə gedir: adi gün 2 (Open-Meteo, AMB), bazar günü 3 (həm də seismology.az; Open-Meteo-nun bir sorğusu
iki xəbərə çatır). items() günün xəbərlərini bir çağırışda qurur və eyni ünvana ikinci sorğu göndərmir. Canlıda gündə bir dəfə,
08:00-da çağırılmalıdır (bazar günü 12:00-ın xəbəri də o vaxt qurulur), sonrakı çağırışlara qurulmuş açarlar done ilə verilir.
Sınaq: python oz_icmal.py --sinaq --root DIR [--now 2026-11-10T09:00+04:00]
"""
import datetime
import json
import pathlib
import re
import sys

import oz_teqvim as tq
import oz_xeber as ox

BAKU = ox.BAKU
DAY = datetime.timedelta(days=1)
TITLE_MAX = 110
WEEKDAYS = ("bazar ertəsi", "çərşənbə axşamı", "çərşənbə", "cümə axşamı", "cümə", "şənbə", "bazar")

# --- Hava: Open-Meteo (open-meteo.com), açarsız model proqnozu; Milli Hidrometeorologiya Xidmətinin proqnozu deyil -----------

CITIES = (("Bakı", 40.4093, 49.8671), ("Gəncə", 40.6828, 46.3606), ("Sumqayıt", 40.5897, 49.6686),
          ("Lənkəran", 38.7529, 48.8475), ("Şəki", 41.1919, 47.1706), ("Naxçıvan", 39.2089, 45.4122))
OM_URL = ("https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}"
          "&daily=weather_code,temperature_2m_max,temperature_2m_min,precipitation_probability_max,wind_speed_10m_max"
          "&timezone=Asia%2FBaku&wind_speed_unit=ms&start_date={start}&end_date={end}")
OM_CREDIT, OM_LINK = "Open-Meteo", "https://open-meteo.com/"
# WMO hava kodları (Open-Meteo-nun sənədi) -> sabit ifadə. Cədvəldə olmayan kod üçün təsvir yazılmır, yalnız rəqəmlər.
SKY = {
    0: "açıq hava", 1: "əsasən açıq hava", 2: "dəyişkən buludlu hava", 3: "buludlu hava",
    45: "duman", 48: "duman və qırov",
    51: "zəif çiskin", 53: "çiskin", 55: "sıx çiskin", 56: "donan çiskin", 57: "donan çiskin",
    61: "zəif yağış", 63: "yağış", 65: "güclü yağış", 66: "donan yağış", 67: "donan yağış",
    71: "zəif qar", 73: "qar", 75: "güclü qar", 77: "qar dənələri",
    80: "arabir zəif yağış", 81: "arabir yağış", 82: "arabir güclü yağış", 85: "arabir qar", 86: "arabir güclü qar",
    95: "ildırımlı yağış", 96: "dolu ilə ildırımlı yağış", 99: "dolu ilə ildırımlı yağış",
}
SKY_NEWS = 45  # bu koddan başlayaraq (duman, çiskin, yağış, qar, ildırım) başlıqda «... gözlənilir» yazılır

# --- AMB ----------------------------------------------------------------------------------------------------------------
AMB_CREDIT, AMB_LINK = "Azərbaycan Mərkəzi Bankı", "https://www.cbar.az/"
AMB_FRESH = 10  # bundan köhnə bülleten «son məzənnə» kimi yazılmır

# --- Futbol: saytın data/futbol faylları ---------------------------------------------------------------------------------
# Azərbaycan klubu = Premyer Liqanın komandası; milli komanda = «azerbaycan». (fayl, ad, yerlik hal)
AZ_LEAGUES = (("premyer-liqa", "Premyer Liqa", "Premyer Liqada"), ("kubok", "Azərbaycan Kuboku", "Azərbaycan Kubokunda"),
              ("i-liqa", "I Liqa", "I Liqada"), ("ii-liqa", "II Liqa", "II Liqada"))
EURO_CUPS = ("cl", "al", "kl")  # UEFA-nın üç kuboku; avroliqa.json basketboldur
COMPS = {
    "cl": "Çempionlar Liqası", "al": "Avropa Liqası", "kl": "Konfrans Liqası",
    "turkiye": "Türkiyə Super Liqası", "ispaniya": "İspaniya La Liqası", "ingiltere": "İngiltərə Premyer Liqası",
    "italiya": "İtaliya A Seriyası", "almaniya": "Almaniya Bundesliqası", "fransa": "Fransa çempionatı",
    "turkiye-kuboku": "Türkiyə Kuboku", "ispaniya-kuboku": "İspaniya Kral Kuboku", "ingiltere-kuboku": "İngiltərə Kuboku",
    "liqa-kuboku": "İngiltərə Liqa Kuboku", "italiya-kuboku": "İtaliya Kuboku", "almaniya-kuboku": "Almaniya Kuboku",
    "fransa-kuboku": "Fransa Kuboku",
}
LEAGUES = ("turkiye", "ispaniya", "ingiltere", "italiya", "almaniya", "fransa")
FOREIGN = LEAGUES + ("turkiye-kuboku", "ispaniya-kuboku", "ingiltere-kuboku", "liqa-kuboku", "italiya-kuboku", "almaniya-kuboku",
                     "fransa-kuboku") + EURO_CUPS
# Saytın izlədiyi xarici klublar (assets/app.js SPORT_TEAMS, «Türkiyə» və «Avropa» qrupları; oz_futbol_dunya.BIG ilə eyni).
# Rəqəm növbədir: sətir çox olanda əvvəl Türkiyə klubları, sonra «Real Madrid» və «Barcelona».
BIG = {
    "galatasaray": 0, "fenerbahce": 0, "besiktas": 0, "trabzonspor": 0,
    "real-madrid": 1, "barcelona": 1,
    "manchester-city": 2, "manchester-united": 2, "liverpool": 2, "arsenal": 2, "chelsea": 2, "bayern-munich": 2,
    "inter-milan": 2, "ac-milan": 2, "milan": 2, "juventus": 2, "paris-saint-germain": 2,
}
GAMES_MAX = 5
FOREIGN_LINE_MAX = 3          # xarici yarışın sətrində ən çox 3 oyun (növbə ilə seçilir, saat sırası ilə yazılır)
FROM_HOUR, NIGHT_HOUR = 8, 4  # günün oyunları: 08:00-dan sabahkı 04:00-dək (Bakı vaxtı)
PLACEHOLDER_MIN = 3           # turun ən azı bu qədər oynanmamış oyunu eyni saatdadırsa, saat yer tutucudur
# Xarici liqa turunda bir saatda bu qədər oynanmamış oyun da yer tutucudur, tur qismən elan olunsa belə (Fransanın 25-ci turu:
# 8 oyun 2027-03-20 16:00Z-də, yalnız «Marseille» – «Lyon» elan olunub). Real cədvəldə ən çoxu 6-dır (Bundesliqa 2025/26, 28-ci tur).
PLACEHOLDER_SHARE = 7
PFL_CREDIT, PFL_LINK = "Peşəkar Futbol Liqası", "https://pfl.az/"

# --- Zəlzələ ------------------------------------------------------------------------------------------------------------
SEYS_WEEK_MIN = 3.0  # seismology.az siyahısı 3,0 və daha güclü təkanları verir
SEYS_PAGE = 20       # siyahının bir səhifəsində 20 təkan var
SEYS_HEAD = 4.0      # bundan güclü təkan həftənin başlığına çıxır


# --- Ümumi köməkçilər ---------------------------------------------------------------------------------------------------

def _now(now):
    if now is None:
        return datetime.datetime.now(BAKU)
    if now.tzinfo is None:
        return now.replace(tzinfo=BAKU)
    return now.astimezone(BAKU)


def _read(path):
    """JSON obyekt və ya None (fayl yoxdur, pozuqdur, obyekt deyil)."""
    try:
        doc = json.loads(pathlib.Path(path).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    return doc if isinstance(doc, dict) else None


def _err(e):
    return f"{type(e).__name__}: {e}"[:120]


def _join(names):
    """«A», «A və B», «A, B və C»."""
    names = [n for n in names if n]
    if len(names) <= 1:
        return "".join(names)
    return ", ".join(names[:-1]) + " və " + names[-1]


def _span(a, b):
    """«1–7 noyabr», «26 oktyabr – 1 noyabr»."""
    if (a.year, a.month) == (b.year, b.month):
        return f"{a.day}–{b.day} {ox.MONTHS[a.month - 1]}"
    return f"{ox.day_text(a)} – {ox.day_text(b)}"


def _days_text(days):
    """«2 noyabr», «2 və 4 noyabr», «31 oktyabr və 2 noyabr»."""
    days = sorted(days)
    if all((d.year, d.month) == (days[0].year, days[0].month) for d in days):
        return f"{_join([str(d.day) for d in days])} {ox.MONTHS[days[0].month - 1]}"
    return _join([ox.day_text(d) for d in days])


def _n1(v, keep=False):
    """Bir onluq rəqəm, işarəsi ilə: 9.8 -> «9,8», 10.0 -> «10», -1.2 -> «-1,2», -0.04 -> «0».
    keep=True: «,0» saxlanır (aralıqda iki tərəf eyni yazılsın: «6,0–9,8»)."""
    r = round(float(v), 1)
    if r == 0:
        return "0,0" if keep else "0"
    s = ox.az_num(r, 1)
    if s.endswith(",0") and not keep:
        s = s[:-2]
    return ("-" if r < 0 else "") + s


def _rng(lo, hi):
    """Temperatur aralığı: «6–10», «2,3–9,1»; bir tərəf tam ədəddirsə ikisi də bir onluqla: «6,0–9,8» (yoxsa «6–9,8» kimi
    qarışıq görünür). Mənfi ədədlə «-1,2 ilə 8,3» (tire mənfi işarəsi ilə qarışmasın)."""
    a, b = _n1(lo), _n1(hi)
    if a == b:
        return a
    if ("," in a) != ("," in b):
        a, b = _n1(lo, keep=True), _n1(hi, keep=True)
    return f"{a} ilə {b}" if a.startswith("-") else f"{a}–{b}"


def _deg(lo, hi):
    """Siyahı sətri və başlıq üçün: «6,0–9,8 dərəcə», «3 dərəcə»; «ilə» aralığı «arasında» ilə bitir: «-1,2 ilə 8,3 dərəcə
    arasında»."""
    rng = _rng(lo, hi)
    return f"{rng} dərəcə arasında" if " ilə " in rng else f"{rng} dərəcə"


def _num(v):
    return float(v) if isinstance(v, (int, float)) and not isinstance(v, bool) else None


def _text(raw):
    return raw.decode("utf-8", "replace") if isinstance(raw, bytes) else str(raw or "")


class _Get:
    """fetch-in üstündə: bir çağırışda hər ünvana ən çox bir sorğu (xəta da yadda qalır). count göndərilən sorğuları sayır."""

    def __init__(self, fetch):
        self.fetch = fetch
        self.cache = {}
        self.count = 0

    def __call__(self, url):
        if self.fetch is None:
            raise LookupError("sorğu funksiyası verilməyib")
        if url not in self.cache:
            self.count += 1
            try:
                self.cache[url] = (self.fetch(url, timeout=20), None)
            except Exception as e:  # şəbəkə xətası yalnız həmin hissəni saxlayır
                self.cache[url] = (None, e)
        data, err = self.cache[url]
        if err is not None:
            raise err
        return data


def _leader(text):
    try:
        return bool(ox.needs_owner(text))
    except Exception:
        return bool(re.search(r"prezident|birinci xanım|vitse-prezident|əliyev", ox._low(text)))


def _guard(item):
    """Rəhbərliyin adı keçən xəbər dərc olunmur (sahibin qaydası)."""
    if item.get("worth") and _leader("\n".join([item["title"], item["lead"], *item["body"]])):
        return dict(item, worth=False, why="rəhbərliyin adı keçir: dərc olunmur")
    return item


# --- Hava ---------------------------------------------------------------------------------------------------------------

def om_url(day, past=0):
    """Altı şəhər bir sorğuda; past > 0 olanda keçən günlər də (bazar günü həftənin rəqəmləri üçün eyni sorğu)."""
    return OM_URL.format(lat=",".join(str(c[1]) for c in CITIES), lon=",".join(str(c[2]) for c in CITIES),
                         start=(day - DAY * past).isoformat(), end=day.isoformat())


def _cell(daily, key, i):
    col = daily.get(key)
    return _num(col[i]) if isinstance(col, list) and i < len(col) else None


def parse_om(raw):
    """Open-Meteo cavabı -> {şəhər: {gün: {code, tmax, tmin, rain, wind}}}. Bir neçə yerin cavabı siyahıdır, sıra sorğudakı
    kimidir. Koordinatı sorğudakından 0,3 dərəcədən çox fərqlənən yer (sıra qarışıbsa) götürülmür."""
    try:
        doc = json.loads(_text(raw))
    except ValueError:
        return {}
    docs = doc if isinstance(doc, list) else [doc]
    out = {}
    for (name, lat, lon), loc in zip(CITIES, docs):
        if not isinstance(loc, dict):
            continue
        got_lat, got_lon = _num(loc.get("latitude")), _num(loc.get("longitude"))
        if got_lat is None or got_lon is None or abs(got_lat - lat) > 0.3 or abs(got_lon - lon) > 0.3:
            continue
        daily = loc.get("daily") if isinstance(loc.get("daily"), dict) else {}
        times = daily.get("time") if isinstance(daily.get("time"), list) else []
        days = {}
        for i, t in enumerate(times):
            try:
                d = datetime.date.fromisoformat(str(t))
            except ValueError:
                continue
            code = _cell(daily, "weather_code", i)
            days[d] = {"code": int(code) if code is not None else None, "tmax": _cell(daily, "temperature_2m_max", i),
                       "tmin": _cell(daily, "temperature_2m_min", i), "rain": _cell(daily, "precipitation_probability_max", i),
                       "wind": _cell(daily, "wind_speed_10m_max", i)}
        out[name] = days
    return out


def _temp_ok(w):
    lo, hi = w.get("tmin"), w.get("tmax")
    return lo is not None and hi is not None and -60 < lo <= hi < 60


def _weather(om, day):
    """Bu günün proqnozu: [(şəhər, dəyərlər)], Bakı birinci. Bakının proqnozu yoxdursa None."""
    rows = [(name, (om.get(name) or {}).get(day)) for name, _, _ in CITIES]
    rows = [(name, w) for name, w in rows if w and _temp_ok(w)]
    return rows if rows and rows[0][0] == "Bakı" else None


def _city_line(name, w):
    bits = [SKY[w["code"]]] if w.get("code") in SKY else []
    bits.append(f"temperatur {_deg(w['tmin'], w['tmax'])}")
    if w.get("rain") is not None and 0 <= w["rain"] <= 100:
        bits.append(f"yağıntı ehtimalı {int(round(w['rain']))}%")
    if w.get("wind") is not None and round(w["wind"], 1) > 0:
        bits.append(f"külək saniyədə {_n1(w['wind'])} metrə qədər")
    return f"{name}: {', '.join(bits)}"


def _temp_span(w):
    a, b = _n1(w["tmin"]), _n1(w["tmax"])
    return f"temperatur {a} dərəcə olacaq" if a == b else f"temperatur {_rng(w['tmin'], w['tmax'])} dərəcə arasında olacaq"


def _weather_lead(w):
    sky = SKY.get(w.get("code"))
    where = f"bu gün Bakıda {sky} gözlənilir, " if sky else "bu gün Bakıda "
    return f"Open-Meteo-nun proqnozuna görə, {where}{_temp_span(w)}."


def _weather_frag(w):
    sky, deg = SKY.get(w.get("code")), _deg(w["tmin"], w["tmax"])
    if sky and w["code"] >= SKY_NEWS:
        return f"Bakıda {sky} gözlənilir, {deg}"
    if sky:
        return f"Bakıda {sky}, {deg}"
    return f"Bakıda {deg}"


# --- AMB ----------------------------------------------------------------------------------------------------------------

def _amb(get, day):
    """day günü qüvvədə olan son bülleten: (bülletenin öz günü, {"USD": .., "EUR": ..}). Bayram, həftə sonu və hələ
    açıqlanmayan gün üçün AMB son bülleteni qaytarır: gün XML-in öz Date-indən götürülür. 1 sorğu."""
    b_day, rates = ox.parse_amb(get(ox.AMB_URL.format(day)))
    vals = {c: rates[c][1] for c in ("USD", "EUR") if c in rates and rates[c][1] > 0}
    if not b_day or not vals:
        raise ValueError("bülletendə tarix və ya dollar, avro yoxdur")
    if b_day > day:
        raise ValueError(f"bülletenin günü ({b_day.isoformat()}) sorğu günündən sonradır")
    return b_day, vals


def _amb_line(b_day, vals):
    names = (("USD", "1 ABŞ dolları"), ("EUR", "1 avro"))
    rates = [f"{name} {ox.az_num(vals[c], 4)} manat" for c, name in names if c in vals]
    word = "məzənnələri" if len(rates) > 1 else "məzənnəsi"
    return f"AMB-nin son rəsmi {word} ({ox.day_text(b_day)} üçün): {', '.join(rates)}"


# --- Günün oyunları -----------------------------------------------------------------------------------------------------

def _dt(value):
    try:
        dt = datetime.datetime.fromisoformat(str(value))
    except (TypeError, ValueError):
        return None
    return (dt if dt.tzinfo else dt.replace(tzinfo=BAKU)).astimezone(BAKU)


def _when(value):
    """Başlama vaxtı (Bakı). Saatsız tarix və saatı 00:00 olan oyun (yer tutucu) üçün None."""
    s = str(value or "")
    if not re.match(r"\d{4}-\d\d-\d\dT\d\d:\d\d", s) or "T00:00" in s:
        return None
    return _dt(s)


def _tur(value):
    value = str(value or "").strip()
    if value.isdigit():
        return f"{ox.ordinal(int(value))} tur"
    m = re.fullmatch(r"Qrup\s*(\d+)", value)
    return f"{ox.ordinal(int(m.group(1)))} qrup" if m else value


def _football(path):
    doc = _read(path)
    return doc if doc and str(doc.get("sport") or "football") == "football" else None


def _source(doc):
    src = str(doc.get("source") or "")
    if src == "pfl.az":
        return PFL_CREDIT, PFL_LINK
    if src.startswith("OpenLigaDB"):
        return "OpenLigaDB", str(doc.get("source_url") or doc.get("url") or "https://www.openligadb.de/")
    if src.startswith("Vikipediya"):
        return "Vikipediya", str(doc.get("url") or "https://az.wikipedia.org/")
    return src, str(doc.get("source_url") or doc.get("url") or "")


def _team(teams, tid):
    info = teams.get(tid) if isinstance(teams, dict) else None
    name = info.get("name") if isinstance(info, dict) else None
    return str(name or tid)


def _fakes(games, kind):
    """Yer tutucu saatlar: {(tur, vaxt)}. Turun bütün oynanmamış oyunları (ən azı 3) bir saata yazılıbsa (TheSportsDB-də La
    Liqanın 13-cü turunun 10 oyunu 16:00Z), xarici liqada (kind="liqa") həm də turun 7+ oyunu bir saatdadırsa. UEFA kuboklarının
    (kind="uefa") liqa mərhələsində (tur rəqəmdir) qayda yoxdur: cədvəl bütöv açıqlanır, son tur qaydaya görə eyni saatda
    oynanır (ÇL-in 8-ci turunun 18 oyunu 2027-01-27 20:00Z)."""
    by = {}
    for g in games:
        if not g.get("played") and g.get("state") != "off":
            by.setdefault(str(g.get("round") or ""), []).append(str(g.get("date") or ""))
    fake = set()
    for rnd, dates in by.items():
        if kind == "uefa" and rnd.isdigit():
            continue
        if len(dates) >= PLACEHOLDER_MIN and len(set(dates)) == 1:
            fake.add((rnd, dates[0]))
        elif kind == "liqa":
            fake.update((rnd, d) for d in set(dates) if dates.count(d) >= PLACEHOLDER_SHARE)
    return fake


def _kind(fid):
    return "uefa" if fid in EURO_CUPS else "liqa" if fid in LEAGUES else "kubok"


def _rows(doc, kind):
    """Faylın saatı bəlli oyunları: [(oyun, Bakı vaxtı)]. kind: "pfl" (Azərbaycan liqaları), "uefa", "liqa", "kubok" (xarici
    liqa və kuboklar), "milli". Düşənlər: təxirə salınan (state=off), saatsız, pfl.az-da stadionsuz (turun cədvəli
    açıqlanmayıb, tarix turun şərti tarixidir) və başqa mənbələrdə yer tutucu saat (_fakes)."""
    games = [g for g in doc.get("games") if isinstance(g, dict)] if isinstance(doc.get("games"), list) else []
    pfl = kind == "pfl"
    fake = set() if pfl else _fakes(games, kind)
    out = []
    for g in games:
        if g.get("state") == "off" or (pfl and not g.get("stadium")):
            continue
        if not g.get("played") and (str(g.get("round") or ""), str(g.get("date") or "")) in fake:
            continue
        dt = _when(g.get("date"))
        if dt:
            out.append((g, dt))
    return out


def _game(doc, g, dt):
    teams = doc.get("teams") if isinstance(doc.get("teams"), dict) else {}
    hid, aid = str(g.get("home") or ""), str(g.get("away") or "")
    return {"hid": hid, "aid": aid, "home": _team(teams, hid), "away": _team(teams, aid), "dt": dt}


def _milli_files(root):
    """Azərbaycan millisinin yarışları: ml-*.json və milli-menyu.json-da Azərbaycanın olduğu yarışlar."""
    data = pathlib.Path(root) / "data"
    ids = [p.stem for p in sorted((data / "futbol").glob("ml-*.json"))]
    menu = _read(data / "milli-menyu.json") or {}
    comps = menu.get("comps") if isinstance(menu.get("comps"), list) else []
    for c in comps:
        cid = str(c.get("id") or "") if isinstance(c, dict) else ""
        if re.fullmatch(r"[a-z0-9-]+", cid) and "Azərbaycan" in (c.get("teams") or []):
            ids.append(cid)
    return list(dict.fromkeys(ids))


def _rank(x):
    """Xarici oyunun növbəsi: BIG-dəki ən kiçik rəqəm (Türkiyə klubları 0)."""
    return min(BIG.get(x["hid"], 9), BIG.get(x["aid"], 9))


def _hm(dt, day):
    return f"{dt:%H:%M}" if dt.date() == day else f"gecə {dt:%H:%M}"


def _line_text(gr, day):
    quote = gr["kind"] != "milli"
    pairs = []
    for x in gr["games"]:
        home, away = (f"«{x['home']}»", f"«{x['away']}»") if quote else (x["home"], x["away"])
        pairs.append(f"{home} – {away} ({_hm(x['dt'], day)})")
    head = gr["comp"] + (f", {gr['rnd']}" if gr.get("rnd") else "")
    return f"{head}: {', '.join(pairs)}"


def day_games(root, day):
    """Günün oyun sətirləri (ən çox GAMES_MAX), vaciblik sırası ilə: milli, avrokubokda Azərbaycan klubu, Premyer Liqa,
    Kubok, I Liqa, II Liqa, xarici klublar. Hər sətir: kind, comp, rnd, games, source, text (və liqada loc)."""
    fut = pathlib.Path(root) / "data" / "futbol"
    start = datetime.datetime.combine(day, datetime.time(FROM_HOUR), tzinfo=BAKU)
    end = datetime.datetime.combine(day + DAY, datetime.time(NIGHT_HOUR), tzinfo=BAKU)
    pl = _read(fut / "premyer-liqa.json") or {}
    clubs = set(pl["teams"]) if isinstance(pl.get("teams"), dict) else set()
    groups, used = [], set()

    def todays(doc, kind):
        return [(g, dt) for g, dt in _rows(doc, kind) if start <= dt < end]

    for fid in _milli_files(root):
        doc = _football(fut / f"{fid}.json")
        if not doc or not doc.get("nat"):
            continue
        for g, dt in todays(doc, "milli"):
            x = _game(doc, g, dt)
            if "azerbaycan" in (x["hid"], x["aid"]):
                groups.append({"kind": "milli", "order": (0, 0, dt), "comp": str(doc.get("name") or doc.get("short") or ""),
                               "rnd": _tur(g.get("round")), "games": [x], "source": _source(doc)})
    for fid in EURO_CUPS:
        doc = _football(fut / f"{fid}.json")
        if not doc or not clubs:
            continue
        for g, dt in todays(doc, "uefa"):
            x = _game(doc, g, dt)
            if x["hid"] in clubs or x["aid"] in clubs:
                used.add((fid, x["hid"], x["aid"]))
                groups.append({"kind": "avro", "order": (1, 0, dt), "comp": COMPS[fid], "rnd": _tur(g.get("round")),
                               "games": [x], "source": _source(doc), "az": x["hid"] if x["hid"] in clubs else x["aid"]})
    for i, (fid, name, loc) in enumerate(AZ_LEAGUES):
        doc = _football(fut / f"{fid}.json")
        if not doc:
            continue
        by = {}
        for g, dt in todays(doc, "pfl"):
            by.setdefault(str(g.get("round") or ""), []).append(_game(doc, g, dt))
        for rnd, games in by.items():
            games.sort(key=lambda x: (x["dt"], x["home"]))
            groups.append({"kind": "liqa", "order": (2 + i, 0, games[0]["dt"]), "fid": fid, "comp": name, "loc": loc,
                           "rnd": _tur(rnd), "games": games, "source": _source(doc)})
    for fid in FOREIGN:
        doc = _football(fut / f"{fid}.json")
        if not doc:
            continue
        games = []
        for g, dt in todays(doc, _kind(fid)):
            x = _game(doc, g, dt)
            if (x["hid"] in BIG or x["aid"] in BIG) and (fid, x["hid"], x["aid"]) not in used:
                games.append(x)
        if games:
            games.sort(key=lambda x: (_rank(x), x["dt"], x["home"]))
            games = sorted(games[:FOREIGN_LINE_MAX], key=lambda x: (x["dt"], x["home"]))
            groups.append({"kind": "xarici", "order": (6, min(_rank(x) for x in games), games[0]["dt"]),
                           "comp": COMPS[fid], "rnd": "", "games": games, "source": _source(doc)})
    groups.sort(key=lambda gr: gr["order"])
    groups = groups[:GAMES_MAX]
    for gr in groups:
        gr["text"] = _line_text(gr, day)
    return groups


def _big_names(groups):
    names = []
    for gr in groups:
        if gr["kind"] == "xarici":
            for x in gr["games"]:
                for tid, name in ((x["hid"], x["home"]), (x["aid"], x["away"])):
                    if tid in BIG and f"«{name}»" not in names:
                        names.append(f"«{name}»")
    return names


def _at(dt, day):
    """(«bu gün» / «bu gecə», «saat 21:45-də»)."""
    return ("bu gün" if dt.date() == day else "bu gecə"), ox.time_loc(dt)


def _games_lead(groups, day):
    out = []
    for gr in groups:
        if gr["kind"] not in ("milli", "avro"):
            continue
        x = gr["games"][0]
        when, hour = _at(x["dt"], day)
        if gr["kind"] == "milli":
            home = x["hid"] == "azerbaycan"
            opp = x["away"] if home else x["home"]
            frame = f"{gr['comp']} çərçivəsində " if gr["comp"] else ""
            out.append(f"Azərbaycan millisi {when} {frame}{'doğma meydanda' if home else 'səfərdə'} "
                       f"{opp} ilə oynayacaq (Bakı vaxtı ilə {hour}).")
        else:
            home = x["hid"] == gr["az"]
            club, opp = (x["home"], x["away"]) if home else (x["away"], x["home"])
            out.append(f"«{club}» {when} {ox.place_loc(gr['comp'])} {'doğma meydanda' if home else 'səfərdə'} "
                       f"«{opp}» ilə qarşılaşacaq (Bakı vaxtı ilə {hour}).")
    counts = {}
    for gr in groups:
        if gr["kind"] == "liqa":
            counts[gr["loc"]] = counts.get(gr["loc"], 0) + len(gr["games"])
    if counts:
        out.append(f"Bu gün {_join([f'{loc} {n}' for loc, n in counts.items()])} oyun keçiriləcək.")
    names = _big_names(groups)
    if names:
        out.append(f"Xarici klublardan {_join(names[:4])} meydana çıxacaq.")
    return out


def _games_frag(groups):
    if not groups:
        return ""
    first = groups[0]
    if first["kind"] == "milli":
        x = first["games"][0]
        return f"Azərbaycan millisi {x['away'] if x['hid'] == 'azerbaycan' else x['home']} ilə oynayacaq"
    if first["kind"] == "avro":
        x = first["games"][0]
        club, opp = (x["home"], x["away"]) if x["hid"] == first["az"] else (x["away"], x["home"])
        return f"«{club}» {ox.place_loc(first['comp'])} «{opp}» ilə oynayacaq"
    leagues = [gr for gr in groups if gr["kind"] == "liqa"]
    if leagues:
        locs = list(dict.fromkeys(gr["loc"] for gr in leagues))
        n = sum(len(gr["games"]) for gr in leagues)
        return f"{locs[0]} {n} oyun" if len(locs) == 1 else f"Azərbaycan futbolunda {n} oyun"
    names = _big_names(groups)
    return f"{_join(names[:2])} meydana çıxacaq" if names else ""


# --- Təqvim -------------------------------------------------------------------------------------------------------------

def _observance(day):
    """«Bu gün Dövlət Bayrağı Günüdür. Beynəlxalq Elm və Sülh Həftəsi başlayır. 9 noyabr iş günü deyil.» Həftə adı
    gun_adlari-da yalnız başladığı gün olur. Həftə sonunun «iş günü deyil»-i yazılmır."""
    names = [n for n in tq.gun_adlari(day) if n]
    days = [n for n in names if not n.endswith("Həftəsi")]
    weeks = [n for n in names if n.endswith("Həftəsi")]
    out = []
    if days:
        out.append(f"Bu gün {_join(days)}{ox._four(days[-1], ('dır', 'dir', 'dur', 'dür'))}.")
    if weeks:
        out.append(f"{'' if days else 'Bu gün '}{_join(weeks)} başlayır.")
    if day.weekday() < 5 and tq.qeyri_is_gunu(day) is True:
        out.append(f"{ox.day_text(day)} iş günü deyil.")
    return " ".join(out)


# --- 1. «Günün bələdçisi» -----------------------------------------------------------------------------------------------

def _beledci_title(day, baku, groups):
    head = f"Günün bələdçisi, {ox.day_text(day)}"
    weather = _weather_frag(baku) if baku else ""
    game = _games_frag(groups)
    frags = [game, weather] if groups and groups[0]["kind"] in ("milli", "avro") else [weather, game]
    frags = [f for f in frags if f]
    while frags:
        title = f"{head}: {'; '.join(frags)}"
        if len(title) <= TITLE_MAX:
            return title
        frags.pop()
    return head


def beledci_item(root, day, get):
    """«Günün bələdçisi» (08:00). get: _Get (sorğular). Qaytarır (xəbər, səbəb)."""
    missing = {}
    weather = None
    try:
        weather = _weather(parse_om(get(om_url(day, 7 if day.weekday() == 6 else 0))), day)
        if not weather:
            missing["hava"] = "Open-Meteo-nun cavabında bu gün üçün Bakının proqnozu yoxdur"
    except Exception as e:
        missing["hava"] = f"Open-Meteo alınmadı: {_err(e)}"
    amb = None
    try:
        amb = _amb(get, day)
        if (day - amb[0]).days > AMB_FRESH:
            missing["AMB"] = f"son bülleten köhnədir ({ox.day_text(amb[0])})"
            amb = None
    except Exception as e:
        missing["AMB"] = f"AMB bülleteni alınmadı: {_err(e)}"
    groups = day_games(root, day)
    if not groups:
        missing["oyunlar"] = "bu gün izlənən futbol oyunu yoxdur"
    obs = _observance(day)

    body = [_city_line(name, w) for name, w in weather or []]
    if amb:
        body.append(_amb_line(*amb))
    body += [gr["text"] for gr in groups]
    if obs:
        body.append(obs)
    baku = weather[0][1] if weather else None
    lead = ([_weather_lead(baku)] if baku else []) + _games_lead(groups, day)
    if not lead:
        lead = [obs or (_amb_line(*amb) + "." if amb else "Bu gün üçün məlumat yoxdur.")]
    credits = ([(OM_CREDIT, OM_LINK)] if weather else []) + ([(AMB_CREDIT, AMB_LINK)] if amb else [])
    credits += [gr["source"] for gr in groups if gr["source"][0]]
    credits = list(dict.fromkeys(credits))
    item = {"kind": "beledci", "key": f"beledci-{day.isoformat()}", "title": _beledci_title(day, baku, groups),
            "lead": " ".join(lead), "body": body, "list": True,
            "credit": ", ".join(dict.fromkeys(c for c, _ in credits)) or OM_CREDIT,
            "link": next((link for _, link in credits if link), OM_LINK),
            "topic": "icmal", "slot": "08:00", "worth": bool(weather or groups), "missing": missing}
    if not item["worth"]:
        item["why"] = "nə hava proqnozu, nə də bu günün oyunları var: qalan hissələr (AMB, təqvim) başqa xəbərlərdədir"
    return item, item.get("why", "")


# --- 2. «Həftənin rəqəmləri» --------------------------------------------------------------------------------------------

def _quakes(page, start, end):
    """Həftənin 3,0 və daha güclü təkanları. Qaytarır (fakt, səbəb)."""
    rows = ox.seys_list(page)
    if not rows:
        return None, "seismology.az siyahısı oxunmadı"
    local = [(q, q["utc"].astimezone(BAKU)) for q in rows]
    if len(rows) >= SEYS_PAGE and min(t.date() for _, t in local) >= start:
        return None, "seismology.az siyahısının birinci səhifəsi bütünlüklə bu həftədəndir: say tam olmaya bilər"
    week = sorted(((q, t) for q, t in local if q["ml"] >= SEYS_WEEK_MIN and start <= t.date() <= end), key=lambda r: r[1])
    if not week:
        return None, "bu həftə 3,0 və daha güclü zəlzələ qeydə alınmayıb"
    top = max(q["ml"] for q, _ in week)
    strongest = [(q, t) for q, t in week if q["ml"] == top]
    q, t = strongest[0]
    ml = ox.az_num(q["ml"], 1)
    if len(week) == 1:
        body = (f"{ox.SEYS_CREDIT}nin məlumatına görə, {ox.day_loc(t)} Bakı vaxtı ilə {ox.time_loc(t)} {ox.place_loc(q['area'])} "
                f"{ml} maqnitudalı zəlzələ qeydə alınıb. Zəlzələnin ocağı {q['depth']} km dərinlikdə olub.")
        lead = f"{ox.place_loc(q['area'])} {ml} maqnitudalı zəlzələ qeydə alınıb"
    else:
        rows_text = "; ".join(f"{ox.day_loc(tt)} {ox.time_loc(tt)} {ox.place_loc(qq['area'])} ({ox.az_num(qq['ml'], 1)})"
                              for qq, tt in week)
        body = (f"{ox.SEYS_CREDIT}nin məlumatına görə, son 7 gündə 3,0 və daha güclü {len(week)} zəlzələ qeydə alınıb: "
                f"{rows_text}.")
        if len(strongest) == 1:
            body += f" Ən güclüsü {ox.place_loc(q['area'])} qeydə alınan {ml} maqnitudalı zəlzələ olub."
        lead = f"3,0 və daha güclü {len(week)} zəlzələ qeydə alınıb"
    if top >= SEYS_HEAD:
        frag, prio = f"{ox.place_loc(q['area'])} {ml} maqnitudalı zəlzələ", 1
    elif len(week) == 1:
        frag, prio = f"{ox.place_loc(q['area'])} {ml} maqnitudalı zəlzələ", 6
    else:
        frag, prio = f"3,0 və daha güclü {len(week)} zəlzələ", 6
    return {"part": "zəlzələ", "prio": prio, "frag": frag, "lead": lead, "body": body,
            "credit": (ox.SEYS_CREDIT, ox.SEYS_LIST)}, ""


def _temps(om, start):
    """Bakıda 7 günün ən yüksək və ən aşağı temperaturu. 7 günün hamısı yoxdursa None."""
    baku = om.get("Bakı") or {}
    rows = [(start + DAY * i, baku.get(start + DAY * i)) for i in range(7)]
    if not all(w and _temp_ok(w) for _, w in rows):
        return None
    hi = max(w["tmax"] for _, w in rows)
    lo = min(w["tmin"] for _, w in rows)
    hi_days = [d for d, w in rows if w["tmax"] == hi]
    lo_days = [d for d, w in rows if w["tmin"] == lo]
    body = (f"Open-Meteo-nun model məlumatına görə, Bakıda son 7 günün ən yüksək temperaturu {_n1(hi)} dərəcə "
            f"({_days_text(hi_days)}), ən aşağı temperaturu {_n1(lo)} dərəcə ({_days_text(lo_days)}) olub.")
    return {"part": "temperatur", "prio": 4, "frag": f"Bakıda ən yüksək temperatur {_n1(hi)} dərəcə",
            "lead": f"Bakıda temperatur Open-Meteo-nun model məlumatına görə {_rng(lo, hi)} dərəcə arasında olub",
            "body": body, "credit": (OM_CREDIT, OM_LINK)}


def _goals(x):
    return x["hs"] + x["as"]


def _pl_week(root, start, end):
    """Premyer Liqada 7 gündə oynanan oyunlar və qollar. Qaytarır (fakt, səbəb)."""
    doc = _read(pathlib.Path(root) / "data" / "futbol" / "premyer-liqa.json")
    if not doc:
        return None, "premyer-liqa.json oxunmadı"
    teams = doc.get("teams") if isinstance(doc.get("teams"), dict) else {}
    rows = [g for g in doc.get("games") if isinstance(g, dict)] if isinstance(doc.get("games"), list) else []
    played = []
    for g in rows:
        dt = _dt(g.get("date"))
        hs, as_ = g.get("hs"), g.get("as")
        if not dt or not g.get("played") or not start <= dt.date() <= end:
            continue
        if not isinstance(hs, int) or not isinstance(as_, int) or isinstance(hs, bool) or isinstance(as_, bool):
            continue
        played.append({"dt": dt, "rnd": str(g.get("round") or ""), "hs": hs, "as": as_,
                       "home": _team(teams, str(g.get("home") or "")), "away": _team(teams, str(g.get("away") or ""))})
    if not played:
        return None, "Premyer Liqada bu həftə oyun olmayıb"
    played.sort(key=lambda x: x["dt"])
    n, goals = len(played), sum(_goals(x) for x in played)
    # Turlar sıra ilə: təxirə salınmış oyun köhnə turdandır («2-ci, 15-ci və 16-cı turlar»).
    rounds = sorted(set(x["rnd"] for x in played), key=lambda r: (not r.isdigit(), int(r) if r.isdigit() else 0, r))
    if len(rounds) == 1 and rounds[0].isdigit():
        tur = f"{ox.ordinal(int(rounds[0]))} tur"
        whole = sum(1 for g in rows if str(g.get("round") or "") == rounds[0]) == n
        if whole:
            text = f"Premyer Liqanın {tur}u başa çatıb: {n} oyunda " + (f"{goals} qol vurulub." if goals else "qol vurulmayıb.")
        else:
            text = f"Premyer Liqanın {tur}unun {n} oyununda " + (f"{goals} qol vurulub." if goals else "qol vurulmayıb.")
    else:
        text = f"Premyer Liqada {n} oyunda " + (f"{goals} qol vurulub" if goals else "qol vurulmayıb")
        if all(r.isdigit() for r in rounds):
            text += f" ({_join([ox.ordinal(int(r)) for r in rounds])} turlar)"
        text += "."
    # «Ən çox», «ən böyük» yalnız hesablananda və tək olanda (bərabərlikdə yazılmır).
    most = max(_goals(x) for x in played)
    top = [x for x in played if _goals(x) == most]
    named = top[0] if len(top) == 1 and most >= 5 else None
    if named:
        text += f" Ən çox qol «{named['home']}» – «{named['away']}» oyununda vurulub: {named['hs']}:{named['as']}."
    margin = max(abs(x["hs"] - x["as"]) for x in played)
    wide = [x for x in played if abs(x["hs"] - x["as"]) == margin]
    if len(wide) == 1 and margin >= 3 and wide[0] is not named:
        x = wide[0]
        text += f" Ən böyük hesab: «{x['home']}» – «{x['away']}» {x['hs']}:{x['as']}."
    return {"part": "futbol", "prio": 3 if goals else 9, "frag": f"Premyer Liqada {goals} qol" if goals else "",
            "lead": f"Premyer Liqada {n} oyunda " + (f"{goals} qol vurulub" if goals else "qol vurulmayıb"),
            "body": text, "credit": (PFL_CREDIT, PFL_LINK)}, ""


def reqemler_item(root, day, get):
    """«Həftənin rəqəmləri» (bazar 12:00): day-7 ... day-1. get: _Get. Qaytarır (xəbər və ya None, səbəb)."""
    if day.weekday() != 6:
        return None, "bazar günü deyil"
    start, end = day - DAY * 7, day - DAY
    span = _span(start, end)
    facts, missing = [], {}
    try:
        fact, why = _quakes(_text(get(ox.SEYS_LIST)), start, end)
        if fact:
            facts.append(fact)
        else:
            missing["zəlzələ"] = why
    except Exception as e:
        missing["zəlzələ"] = f"seismology.az alınmadı: {_err(e)}"
    try:
        fact = _temps(parse_om(get(om_url(day, 7))), start)
        if fact:
            facts.append(fact)
        else:
            missing["temperatur"] = "Open-Meteo-nun cavabında Bakının 7 günü tam deyil"
    except Exception as e:
        missing["temperatur"] = f"Open-Meteo alınmadı: {_err(e)}"
    fact, why = _pl_week(root, start, end)
    if fact:
        facts.append(fact)
    else:
        missing["futbol"] = why

    ranked = sorted(facts, key=lambda x: x["prio"])
    head = f"Həftənin rəqəmləri, {span}"
    frags = [x["frag"] for x in ranked if x["frag"]][:2]
    while frags and len(head + ": " + ", ".join(frags)) > TITLE_MAX:
        frags.pop()
    title = head + ": " + ", ".join(frags) if frags else head
    clauses = ", ".join(x["lead"] for x in ranked[:2])
    lead = f"Son 7 gündə ({span}) {clauses}." if facts else f"Son 7 günün ({span}) rəqəmləri alınmadı."
    credits = list(dict.fromkeys(x["credit"] for x in facts))
    item = {"kind": "reqemler", "key": f"reqemler-{day.isoformat()}", "title": title, "lead": lead,
            "body": [x["body"] for x in facts], "list": True,
            "credit": ", ".join(c for c, _ in credits) or OM_CREDIT, "link": credits[0][1] if credits else OM_LINK,
            "topic": "icmal", "slot": "12:00", "worth": len(facts) >= 2, "missing": missing}
    if not item["worth"]:
        item["why"] = f"həftənin rəqəmlərindən yalnız {len(facts)} hissə alındı (ən azı 2 lazımdır)"
    return item, item.get("why", "")


# --- İstehsal və sınaq --------------------------------------------------------------------------------------------------

def items(root, now, fetch=None, done=()):
    """now-un Bakı günü üçün xəbərlər, hər biri «slot» saatı ilə: hər gün «Günün bələdçisi», bazar günü «Həftənin rəqəmləri»
    də. worth=False olanlar da qaytarılır (səbəbi «why»-dadır). done: artıq qurulmuş (dərc gözləyən və ya dərc olunmuş)
    açarlar: onlar qurulmur, sorğu getmir. Sorğu yalnız fetch ilə: adi gün 2, bazar günü 3."""
    now = _now(now)
    day = now.date()
    get = _Get(fetch)
    done = set(done or ())
    out = []
    if f"beledci-{day.isoformat()}" not in done:
        out.append(beledci_item(root, day, get)[0])
    if day.weekday() == 6 and f"reqemler-{day.isoformat()}" not in done:
        item, _ = reqemler_item(root, day, get)
        if item:
            out.append(item)
    return [_guard(item) for item in out]


def _verdict(item):
    return "✅ Dərc olunardı" if item.get("worth") else f"⏭ Dərc olunmazdı: {item.get('why') or 'səbəb yazılmayıb'}"


def _label(d, today):
    rel = {0: "bu gün", -1: "dünən", 1: "sabah"}.get((d - today).days, "")
    return f"{ox.day_text(d)} {d.year}, {WEEKDAYS[d.weekday()]}" + (f" ({rel})" if rel else "")


def _show(label, item, why):
    if not item:
        return [f"**{label}:** ⏭ Dərc olunmazdı: {why}", ""]
    item = _guard(item)
    md = [f"**{label}, saat {item['slot']}:**", ""] + ox.render(item)
    if item.get("missing"):
        md += ["> Yazılmayan hissələr: " + "; ".join(f"{k} — {v}" for k, v in item["missing"].items()), ""]
    return md + [_verdict(item), ""]


def sinaq(root, now=None, fetch=None):
    """Nümunələr (Markdown): bugünkü «Günün bələdçisi» və ən son bazar gününün «Həftənin rəqəmləri», real sorğularla.
    Heç nə yazmır. fetch verilməyibsə updater-in fetch-i işlənir."""
    root = pathlib.Path(root)
    now = _now(now)
    today = now.date()
    note = ""
    if fetch is None:
        try:
            fetch = ox._u().fetch
        except Exception as e:
            note = f"> updater yüklənmədi ({_err(e)}): sorğusuz hissələr göstərilir."
    get = _Get(fetch)
    md = ["# İcmal xəbərləri (oz_icmal.py): sınaq", "",
          f"{now:%d.%m.%Y %H:%M} (Bakı vaxtı). Sayta heç nə yazılmır. İstehsalda gündə 2 sorğu gedir, bazar günü 3.", ""]
    if note:
        md += [note, ""]
    md += ["## 1. «Günün bələdçisi» (hər gün 08:00)", ""]
    item, why = beledci_item(root, today, get)
    md += _show(_label(today, today), item, why)
    md += ["### Növbəti 7 günün oyun hissəsi", "",
           "Bugünkü fayllarla; hava və AMB həmin günün səhəri alınacaq. Oyunu olmayan gün göstərilmir.", ""]
    shown = 0
    for i in range(1, 8):
        d = today + DAY * i
        groups = day_games(root, d)
        if groups:
            shown += 1
            md += [f"**{_label(d, today)}:**", ""] + [f"- {gr['text']}" for gr in groups] + [""]
    if not shown:
        md += ["- Növbəti 7 gündə izlənən oyun yoxdur.", ""]
    md += ["## 2. «Həftənin rəqəmləri» (bazar 12:00)", ""]
    sunday = today - DAY * ((today.weekday() + 1) % 7)
    item, why = reqemler_item(root, sunday, get)
    label = _label(sunday, today) + ("" if sunday == today else " — ən son real hal")
    md += _show(label, item, why)
    if item and "zəlzələ" in item.get("missing", {}):
        md += _quake_example(get, sunday, today)
    md += [f"Bu sınaqda {get.count} sorğu göndərilib.", ""]
    return md


def _quake_example(get, sunday, today, weeks=12):
    """Bu həftə zəlzələ yoxdursa, zəlzələ olan ən son həftənin sətri (eyni siyahıdan, yeni sorğu getmir)."""
    md = ["### Zəlzələ hissəsi: zəlzələ olan ən son həftə", ""]
    try:
        page = _text(get(ox.SEYS_LIST))
    except Exception as e:
        return md + [f"> seismology.az alınmadı: {_err(e)}", ""]
    for k in range(1, weeks + 1):
        day = sunday - DAY * 7 * k
        fact, _ = _quakes(page, day - DAY * 7, day - DAY)
        if fact:
            return md + [f"{_span(day - DAY * 7, day - DAY)}, {_label(day, today)} xəbərinə düşərdi:", "", f"- {fact['body']}", ""]
    return md + [f"- Son {weeks} həftədə 3,0 və daha güclü zəlzələ olmayıb.", ""]


def _arg(argv, name):
    return argv[argv.index(name) + 1] if name in argv and argv.index(name) + 1 < len(argv) else None


def main(argv):
    if "--sinaq" not in argv:
        print(__doc__)
        return 0
    root = pathlib.Path(_arg(argv, "--root") or pathlib.Path(__file__).parent)
    when = _arg(argv, "--now")
    now = datetime.datetime.fromisoformat(when) if when else None
    sys.stdout.write("\n".join(sinaq(root, now)) + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
