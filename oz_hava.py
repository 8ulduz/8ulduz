"""Hava və təbiət xəbərləri (oz_hava.py), mərhələ 2: meteohəssaslar üçün gün, maqnit qasırğası, normadan fərq, təhlükəli
hava həddi, Xəzərin suyu. Sahibin qərarı (2026-11-10): «Mərhələ 2-ni qur», yəni açarsız açıq mənbələrdən şablon xəbər,
süni intellektsiz. Sayta qoşulmayıb: updater.py və pipeline bu modulu çağırmır (NotOnTheSiteTest).

1. «Meteohəssaslar üçün gün» (hər gün, 08:30): MHX-nin «Tibbi-meteoroloji proqnoz» səhifəsindəki cümlə (olduğu kimi,
   dırnaqda) və NOAA SWPC-nin 3 günlük proqnozundan günün Kp indeksi (3 saatlıq UTC dövrləri Bakı vaxtına çevrilir).
   MHX-nin cümləsi bu günə deyilsə yalnız NOAA hissəsi yazılır, o da yalnız Kp 4 və yuxarıdırsa («qasırğa yoxdur» xəbər
   deyil). Qasırğa günü bu xəbərdə qasırğa bir cümlədir; MHX cümləsi yoxdursa xəbər yazılmır (qasırğanın öz xəbəri var).
2. «Maqnit qasırğası» (hadisə): NOAA-nın Kp cədvəlində (müşahidə və proqnoz) Kp 5-ə (G1) çatanda. «Qasırğa günü» D
   Bakı vaxtı ilə D−1 22:00-dan D 22:00-dək başlayan 3 saatlıq dövrlərdir (gecə sonrakı günə aiddir): hər dövr yalnız
   bir günə düşür, bir günə bir xəbər. Dünənki qasırğanın davamı (aradakı fasilə 9 saatdan az, səviyyə artmayıb) ayrıca
   xəbər deyil. alerts.json yalnız xəbər yazılanda açılır: «K indeksi N» bildirişinin vaxtı bir cümlədir.
3. «Normadan fərq» (hadisə): sabah Bakıda maksimum temperatur 1991–2020 normasından 5 °C və daha çox fərqlənəndə, isti
   və ya soyuq dövrün yalnız ilk günü. Norma aşağıdakı cədvəldir (NORM_MAX, NORM_MIN).
4. «Təhlükəli hava həddi» (hadisə, gündə ən çox bir xəbər): Open-Meteo-nun 8 şəhər üçün model proqnozunda sabah küləyin
   ani sürəti 20 m/san, şaxta −10 °C (Bakıda −5 °C), isti 38 °C, qar 10 sm (aran şəhərlərində 5 sm) və ya Xəzərdə dalğa
   3 m həddini keçəndə. Model məlumatı rəsmi xəbərdarlıq deyil: mətn «model proqnozuna görə» deyir.
5. «Xəzərin suyu» (may–sentyabr hər gün, digər aylarda şənbə): NOAA OISST (ERDDAP), Abşeron yaxınlığındakı xanalar, bir
   həftə əvvəllə müqayisə. Mövsümdən kənar 0,5 dərəcədən az dəyişiklik xəbər deyil.

Sorğular yalnız fetch ilə və yalnız öz pəncərəsində gedir (Bakı vaxtı): 08:30–10:30 MHX + SWPC mətni + Kp cədvəli,
11:00–13:00 OISST, 16:00–18:00 Open-Meteo proqnozu + dəniz proqnozu, 20:00–22:00 Kp cədvəli (bu gün qasırğa xəbəri
çıxmayıbsa). Hər sorğudan sonra, nəticəsi nə olursa olsun, pəncərənin açarı qayıdır (xəbər yoxdursa worth=False və «why»
ilə): istehsal qayıdan hər açarı done-a yazır və həmin pəncərədə ikinci sorğu getmir. Gündə ən çox 8 sorğu:
MHX 1, SWPC mətni 1, Kp cədvəli 2, alerts 1, Open-Meteo 1, dəniz 1, OISST 1.
"""
import datetime
import html
import json
import math
import pathlib
import re
import sys
import time
import urllib.parse

import oz_xeber as ox

BAKU = ox.BAKU
UTC = datetime.timezone.utc
DAY = datetime.timedelta(days=1)
HOUR = datetime.timedelta(hours=1)
TIMEOUT = 15
PAUSE = 1.0                 # sınaqda eyni hosta sorğular arasında, saniyə
TITLE_MAX = 110
TOPIC = "təbiət"            # CONVENTIONS-in siyahısında hava mövzusu yoxdur; oz_yer_kosmos da «təbiət» yazır
WIN_MORNING = ("08:30", "10:30")
WIN_SEA = ("11:00", "13:00")
WIN_FORECAST = ("16:00", "18:00")
WIN_EVENING = ("20:00", "22:00")

# --- Ümumi ---------------------------------------------------------------------------------------------------------------


class Bad(ValueError):
    """Mənbənin cavabı gözlənilən şəkildə deyil; mətni «why»-da yazılır."""


def _baku(now=None):
    """Aware Bakı vaxtı; ofsetsiz vaxt Bakı vaxtı sayılır."""
    if now is None:
        now = datetime.datetime.now(BAKU)
    return now.replace(tzinfo=BAKU) if now.tzinfo is None else now.astimezone(BAKU)


def _at(day, hm):
    h, m = hm.split(":")
    return datetime.datetime(day.year, day.month, day.day, int(h), int(m), tzinfo=BAKU)


def _in(now, win):
    return _at(now.date(), win[0]) <= now < _at(now.date(), win[1])


def _err(e):
    code = getattr(e, "code", None)
    return f"{type(e).__name__} {code}" if isinstance(code, int) else type(e).__name__


def _why(e, src):
    return str(e) if isinstance(e, Bad) else f"{src} alınmadı: {_err(e)}"


def _flt(x):
    if isinstance(x, bool):
        return None
    try:
        v = float(x)
    except (TypeError, ValueError):
        return None
    return v if math.isfinite(v) else None


def _r1(x):
    """Onda birə yuvarlaq (yarım yuxarı)."""
    return math.floor(x * 10 + 0.5) / 10


def num(v, dec=1):
    """Ədəd artıq sıfırsız: 15.35 (dec=2) -> «15,35», 3.0 -> «3», 16.5 -> «16,5». Mütləq qiymətdir."""
    text = ox.az_num(v, dec)
    return text.rstrip("0").rstrip(",") if "," in text else text


def temp(v):
    """«−4,3 °C», «9,8 °C»: az_num mütləq qiymət verir, işarəni özümüz yazırıq."""
    v = _r1(v)
    return f"{'−' if v < 0 else ''}{num(v, 1)} °C"


def _text(raw):
    return raw.decode("utf-8", "replace") if isinstance(raw, (bytes, bytearray)) else str(raw)


def _json(raw):
    return json.loads(_text(raw))


def _leader(text):
    try:
        return bool(ox.needs_owner(text))
    except Exception:
        return bool(re.search(r"prezident|birinci xanım|vitse-prezident|əliyev", ox._low(text)))


def _guard(item):
    """Rəhbərliyin adı keçən xəbər dərc olunmur (sahibin qaydası; MHX-nin cümləsi mənbədən olduğu kimi gəlir)."""
    if item.get("worth") and _leader("\n".join([item["title"], item["lead"], *item["body"]])):
        return dict(item, worth=False, why="rəhbərliyin adı keçir: dərc olunmur")
    return item


def _fail(kind, key, title, why, credit, link, topic, now):
    """Dərc olunmayan qeyd (mənbə alınmadı və ya xəbər yoxdur): səbəb «why»-dadır, açar pəncərəni bağlayır."""
    return {"kind": kind, "key": key, "title": title, "lead": why, "body": [], "credit": credit, "link": link,
            "topic": topic, "slot": f"{now:%H:%M}", "worth": False, "why": why}


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


# --- NOAA SWPC: Kp indeksi, G şkalası ------------------------------------------------------------------------------------
SWPC_TEXT = "https://services.swpc.noaa.gov/text/3-day-forecast.txt"
SWPC_KP = "https://services.swpc.noaa.gov/products/noaa-planetary-k-index-forecast.json"
SWPC_ALERTS = "https://services.swpc.noaa.gov/products/alerts.json"
SWPC_PAGE = "https://www.swpc.noaa.gov/products/3-day-forecast"
SWPC_KP_PAGE = "https://www.swpc.noaa.gov/products/planetary-k-index"
SWPC_CREDIT = "NOAA Kosmik Hava Proqnozu Mərkəzi (SWPC)"
SWPC_GEN = "ABŞ Milli Okean və Atmosfer Administrasiyasının (NOAA) Kosmik Hava Proqnozu Mərkəzinin"
SWPC_FRESH = datetime.timedelta(hours=30)   # 3 günlük proqnoz gündə iki dəfə çıxır (00:30 və 12:30 UTC)
G_NAME = {1: "zəif", 2: "orta", 3: "güclü", 4: "çox güclü", 5: "ifrat güclü"}
G_TITLE = {1: "Zəif", 2: "Orta səviyyəli", 3: "Güclü", 4: "Çox güclü", 5: "İfrat güclü"}
_MON_EN = {"Jan": 1, "Feb": 2, "Mar": 3, "Apr": 4, "May": 5, "Jun": 6, "Jul": 7, "Aug": 8, "Sep": 9, "Oct": 10,
           "Nov": 11, "Dec": 12}
_ISSUED = re.compile(r"^:Issued:\s*(\d{4}) ([A-Z][a-z]{2}) (\d{1,2}) (\d{2})(\d{2}) UTC", re.M)
_KP_HEAD = re.compile(r"^[ \t]+([A-Z][a-z]{2}) (\d{1,2})[ \t]+([A-Z][a-z]{2}) (\d{1,2})[ \t]+([A-Z][a-z]{2}) (\d{1,2})[ \t]*$",
                      re.M)
_KP_ROW = re.compile(r"^(\d{2})-(\d{2})UT[ \t]+(.+)$", re.M)
_KP_VAL = re.compile(r"(\d+(?:\.\d+)?)(?:[ \t]*\(G\d\))?")


def g_level(kp):
    """NOAA-nın G şkalası: Kp 5 -> G1 … Kp 9 -> G5; 5-dən aşağı 0. NOAA 4,67-ni (5−) də G1 yazır."""
    if kp is None or kp < 4.5:
        return 0
    return max(0, min(5, int(math.floor(kp + 0.5)) - 4))


def parse_swpc_text(raw):
    """3-day-forecast.txt -> (buraxılış anı UTC, [(dövrün başlanğıcı UTC, Kp)]) vaxt sırası ilə, 24 dövr."""
    text = _text(raw).replace("\r", "")
    m = _ISSUED.search(text)
    i = text.find("NOAA Kp index breakdown")
    if not m or i < 0 or m.group(2) not in _MON_EN:
        raise Bad("NOAA-nın 3 günlük proqnozu tanınmadı")
    issued = datetime.datetime(int(m.group(1)), _MON_EN[m.group(2)], int(m.group(3)), int(m.group(4)),
                               int(m.group(5)), tzinfo=UTC)
    part = text[i:]
    j = part.find("Rationale")
    part = part[:j] if j > 0 else part
    h = _KP_HEAD.search(part)
    if not h:
        raise Bad("NOAA-nın 3 günlük proqnozunda Kp cədvəli tanınmadı")
    days = []
    for k in (0, 1, 2):
        mon = _MON_EN.get(h.group(1 + 2 * k))
        if not mon:
            raise Bad("NOAA-nın 3 günlük proqnozunda ay tanınmadı")
        d = datetime.date(issued.year, mon, int(h.group(2 + 2 * k)))
        if d < issued.date() - 60 * DAY:      # dekabrın sonunda yanvar sütunu
            d = datetime.date(issued.year + 1, mon, d.day)
        days.append(d)
    blocks = []
    for r in _KP_ROW.finditer(part):
        vals = _KP_VAL.findall(r.group(3))
        if len(vals) != 3:
            raise Bad("NOAA-nın 3 günlük proqnozunda Kp sətri tanınmadı")
        for d, v in zip(days, vals):
            blocks.append((datetime.datetime(d.year, d.month, d.day, int(r.group(1)), tzinfo=UTC), float(v)))
    if len(blocks) != 24 or any(not 0 <= v <= 9 for _, v in blocks):
        raise Bad("NOAA-nın 3 günlük proqnozunda Kp cədvəli natamamdır")
    return issued, sorted(blocks)


def kp_day(blocks, day):
    """Bakı vaxtı ilə həmin gün başlayan 3 saatlıq dövrlər: [(başlanğıc, Bakı vaxtı; Kp)]."""
    out = [(s.astimezone(BAKU), kp) for s, kp in blocks]
    return [(t, kp) for t, kp in out if t.date() == day]


def _blk(t):
    return f"{t:%H:%M}–{t + 3 * HOUR:%H:%M}"


def kp_text(day, kp):
    """NOAA-nın 3 günlük proqnozundan günün Kp cümlələri (qasırğa günü bir cümlə)."""
    vals = [v for _, v in kp]
    top, low = max(vals), min(vals)
    first = [t for t, v in kp if v == top][0]
    span = "Bakı vaxtı ilə" if len(kp) >= 8 else f"Bakı vaxtı ilə {kp[0][0]:%H:%M}–{kp[-1][0] + 3 * HOUR:%H:%M}"
    head = f"{SWPC_GEN} 3 günlük proqnozuna görə, {ox.day_loc(day)} ({span}, 3 saatlıq dövrlər üzrə) "
    g = g_level(top)
    if g:
        return [head + f"Kp indeksinin ən yüksək göstəricisi {num(top, 2)} olacaq (saat {_blk(first)} arası); bu, NOAA "
                f"şkalasında G{g} ({G_NAME[g]}) maqnit qasırğası səviyyəsidir."]
    if low == top:
        rng = f"Kp indeksi {num(top, 2)} olacaq"
    else:
        rng = (f"Kp indeksi {num(low, 2)}–{num(top, 2)} arasında olacaq; ən yüksək göstərici ({num(top, 2)}) saat "
               f"{_blk(first)} arasına düşür")
    return [head + rng + ".", "Bu, NOAA şkalasında maqnit qasırğası həddindən (G1, Kp 5) aşağıdır."]


# --- 1. Meteohəssaslar üçün gün ------------------------------------------------------------------------------------------
MHX_URL = "https://meteo.az/index.php?ln=az&pg=216"
MHX_CREDIT = "Milli Hidrometeorologiya Xidməti"
METEO_SLOT = "08:30"
KP_ACTIVE = 4.0             # MHX cümləsi olmayanda yalnız bundan yuxarı Kp xəbərdir
KP_MIN_BLOCKS = 4
_MHX_DIV = re.compile(r"<div[^>]*>([^<]*meteohəssas[^<]*)</div>", re.I)
_MHX_DATE = re.compile(r"^(\w+)\s+(\d{1,2})\s*-")
_MHX_TAIL = re.compile(r"meteohəssas insanlar üçün ([^.,;:!?«»]{3,40})\.?$")
_MON_GEN = ("yanvarın", "fevralın", "martın", "aprelin", "mayın", "iyunun", "iyulun", "avqustun", "sentyabrın",
            "oktyabrın", "noyabrın", "dekabrın")


def parse_mhx(raw, now):
    """MHX-nin «Tibbi-meteoroloji proqnoz» səhifəsi -> (cümlənin günü, cümlə)."""
    m = _MHX_DIV.search(_text(raw))
    if not m:
        raise Bad("MHX səhifəsində proqnoz cümləsi tapılmadı")
    text = re.sub(r"\s+", " ", html.unescape(m.group(1))).strip()
    if not 30 <= len(text) <= 600:
        raise Bad("MHX-nin cümləsi gözlənilən uzunluqda deyil")
    d = _MHX_DATE.match(text)
    word = ox._low(d.group(1)) if d else ""
    if word not in _MON_GEN:
        raise Bad("MHX-nin cümləsində tarix tanınmadı")
    for year in (now.year, now.year + 1, now.year - 1):
        try:
            day = datetime.date(year, _MON_GEN.index(word) + 1, int(d.group(2)))
        except ValueError:
            continue
        if abs((day - now.date()).days) <= 40:
            return day, text
    raise Bad("MHX-nin cümləsində tarix tanınmadı")


def meteo_item(day, now, mhx=None, swpc=None, notes=()):
    """«Meteohəssaslar üçün gün». mhx: (gün, cümlə) və ya None; swpc: parse_swpc_text-in nəticəsi və ya None.
    -> (xəbər | None, səbəb)."""
    why = list(notes)
    sentence = None
    if mhx:
        if mhx[0] == day:
            sentence = mhx[1]
        else:
            why.append(f"MHX-nin səhifəsi bu günə deyil ({ox.day_text(mhx[0])})")
    kp = []
    if swpc:
        age = now - swpc[0]
        kp = kp_day(swpc[1], day) if -HOUR <= age <= SWPC_FRESH else []
        if len(kp) < KP_MIN_BLOCKS:
            kp = []
            why.append("NOAA-nın 3 günlük proqnozu köhnədir və ya bu günü əhatə etmir")
    top = max((v for _, v in kp), default=0.0)
    base = {"kind": "meteohessas", "key": f"meteohessas-{day.isoformat()}", "topic": TOPIC, "slot": METEO_SLOT,
            "worth": True}
    if sentence:
        tail = _MHX_TAIL.search(sentence)
        if tail:
            where = "Abşeronda " if "Abşeron" in sentence else ""
            title = f"MHX: {ox.day_text(day)} {where}meteohəssas insanlar üçün {tail.group(1).strip()}"
        else:
            title = f"Meteohəssaslar üçün {ox.day_text(day)}: MHX-nin tibbi-meteoroloji proqnozu"
        lead = f"{MHX_CREDIT}nin (MHX) tibbi-meteoroloji proqnozunda deyilir: «{sentence.rstrip('. ')}»."
        credit = MHX_CREDIT + ("; " + SWPC_CREDIT if kp else "")
        return dict(base, title=title[:TITLE_MAX], lead=lead, body=kp_text(day, kp) if kp else [], credit=credit,
                    link=MHX_URL), ""
    if not kp:
        return None, "; ".join(why) or "məlumat yoxdur"
    if g_level(top):
        return None, "; ".join(why + ["maqnit qasırğası ayrıca xəbərdir"])
    if top < KP_ACTIVE:
        return None, "; ".join(why + [f"NOAA-da qasırğa gözlənilmir (Kp ən çox {num(top, 2)}): xəbər deyil"])
    text = kp_text(day, kp)
    title = f"NOAA proqnozu: {ox.day_loc(day)} Kp indeksi ən çox {num(top, 2)} olacaq, maqnit qasırğası həddinə çatmır"
    return dict(base, title=title[:TITLE_MAX], lead=text[0], body=text[1:], credit=SWPC_CREDIT, link=SWPC_PAGE), ""


def meteo_now(now, get, done):
    """Səhər pəncərəsi: MHX səhifəsi və SWPC mətni, hərəsi bir sorğu."""
    day = now.date()
    key = f"meteohessas-{day.isoformat()}"
    if not _in(now, WIN_MORNING) or key in done:
        return []
    notes, mhx, swpc = [], None, None
    try:
        mhx = parse_mhx(get(MHX_URL, "text/html"), now)
    except Exception as e:
        notes.append(_why(e, "MHX"))
    try:
        swpc = parse_swpc_text(get(SWPC_TEXT, "text/plain"))
    except Exception as e:
        notes.append(_why(e, "NOAA"))
    item, why = meteo_item(day, now, mhx, swpc, notes)
    return [item or _fail("meteohessas", key, "Meteohəssaslar üçün gün: xəbər yoxdur", why, MHX_CREDIT, MHX_URL,
                          TOPIC, now)]


# --- 2. Maqnit qasırğası -------------------------------------------------------------------------------------------------
STORM_KEY = "maqnit-qasirgasi-"     # dərc olunan xəbər
STORM_TICK = "maqnit-sorgu-"        # pəncərənin sorğusu göndərilib, xəbər yoxdur
STORM_GAP = 9 * HOUR                # dünənki son qasırğa dövrü ilə bu günün ilk dövrü arasında: davam sayılır
STORM_LIST = 3
_ALT_K = re.compile(r"ALERT: Geomagnetic K-index of (\d)")
_ALT_T = re.compile(r"Threshold Reached: (\d{4}) ([A-Z][a-z]{2}) (\d{1,2}) (\d{2})(\d{2}) UTC")


def parse_kp(raw):
    """noaa-planetary-k-index-forecast.json -> [(dövrün başlanğıcı UTC, Kp, status)] vaxt sırası ilə.
    status: observed | estimated | predicted. Həm obyektlər, həm də köhnə «sətirlər massivi» şəkli oxunur."""
    data = _json(raw)
    rows = []
    for r in data if isinstance(data, list) else []:
        if isinstance(r, dict):
            tag, kp, st = r.get("time_tag"), r.get("kp"), r.get("observed")
        elif isinstance(r, (list, tuple)) and len(r) >= 3:
            tag, kp, st = r[0], r[1], r[2]
        else:
            continue
        v = _flt(kp)
        try:
            t = datetime.datetime.strptime(str(tag)[:19].replace(" ", "T"), "%Y-%m-%dT%H:%M:%S")
        except ValueError:
            continue    # başlıq sətri
        if v is not None and 0 <= v <= 9:
            rows.append((t.replace(tzinfo=UTC), v, str(st or "").lower()))
    if len(rows) < 8:
        raise Bad("NOAA-nın Kp cədvəli tanınmadı")
    return sorted(rows)


def parse_alerts(raw):
    """alerts.json-dakı «ALERT: Geomagnetic K-index of N» bildirişləri -> [(həddə çatılan an UTC, N)], vaxt sırası ilə."""
    out = []
    data = _json(raw)
    for a in data if isinstance(data, list) else []:
        msg = str(a.get("message") or "") if isinstance(a, dict) else ""
        k, t = _ALT_K.search(msg), _ALT_T.search(msg)
        if k and t and t.group(2) in _MON_EN:
            try:
                when = datetime.datetime(int(t.group(1)), _MON_EN[t.group(2)], int(t.group(3)), int(t.group(4)),
                                         int(t.group(5)), tzinfo=UTC)
            except ValueError:
                continue
            out.append((when, int(k.group(1))))
    return sorted(out)


def storm_day(rows, day):
    """«Qasırğa günü»: Bakı vaxtı ilə day−1 22:00-dan day 22:00-dək başlayan dövrlər."""
    a, b = _at(day - DAY, "22:00"), _at(day, "22:00")
    return [r for r in rows if a <= r[0] < b]


def _blk_text(r):
    t = r[0].astimezone(BAKU)
    return f"{ox.day_text(t.date())} saat {_blk(t)} arası {num(r[1], 2)} (G{g_level(r[1])})"


def _blk_list(rs):
    """Ən güclü üç dövr, vaxt sırası ilə."""
    pick = sorted(sorted(rs, key=lambda r: (-r[1], r[0]))[:STORM_LIST])
    return ", ".join(_blk_text(r) for r in pick)


def storm_item(day, rows, now, alerts=(), slot="08:40"):
    """Günün maqnit qasırğası xəbəri. rows: parse_kp, alerts: parse_alerts. -> (xəbər | None, səbəb)."""
    today = [r for r in storm_day(rows, day) if g_level(r[1])]
    if not today:
        return None, "bu günün dövrlərində Kp 5-ə (G1) çatmır"
    prev = [r for r in storm_day(rows, day - DAY) if g_level(r[1])]
    if prev and today[0][0] - prev[-1][0] <= STORM_GAP and \
            max(g_level(r[1]) for r in today) <= max(g_level(r[1]) for r in prev):
        return None, "dünənki qasırğanın davamıdır: bir hadisə, bir xəbər"
    seen = [r for r in today if r[2] != "predicted"]
    ahead = [r for r in today if r[2] == "predicted"]
    main = seen or ahead
    top = max(r[1] for r in main)
    g = g_level(top)
    scale = f"bu, NOAA şkalasında G{g} ({G_NAME[g]}) səviyyəli maqnit qasırğasıdır"
    body = []
    if seen:
        title = f"{G_TITLE[g]} maqnit qasırğası qeydə alınıb: Kp indeksi {num(top, 2)} (G{g})"
        lead = f"{SWPC_GEN} məlumatına görə, Kp indeksi Bakı vaxtı ilə {_blk_list(seen)} olub; {scale}."
        if ahead:
            body.append(f"Proqnoza görə, Kp indeksi {_blk_list(ahead)} olacaq.")
    else:
        title = f"{G_TITLE[g]} maqnit qasırğası gözlənilir: Kp indeksi {num(top, 2)} (G{g}), NOAA proqnozu"
        lead = f"{SWPC_GEN} proqnozuna görə, Kp indeksi Bakı vaxtı ilə {_blk_list(ahead)} olacaq; {scale}."
    if len(today) > STORM_LIST:
        body.append(f"Kp indeksi cəmi {len(today)} üçsaatlıq dövrdə G1 və yuxarı səviyyədədir.")
    a, b = _at(day - DAY, "22:00"), _at(day, "22:00") + 3 * HOUR
    hit = sorted((-k, t) for t, k in alerts if a <= t < b and k >= 5)
    if hit:
        t = hit[0][1].astimezone(BAKU)
        body.append(f"NOAA-nın «K indeksi {-hit[0][0]}» bildirişinə görə, bu həddə Bakı vaxtı ilə "
                    f"{ox.day_text(t.date())} {ox.time_loc(t)} çatılıb.")
    body.append("NOAA şkalasında maqnit qasırğası Kp 5-dən (G1) başlayır, ən yüksək pillə G5-dir (Kp 9).")
    return {"kind": "maqnit-qasirgasi", "key": STORM_KEY + day.isoformat(), "title": title[:TITLE_MAX], "lead": lead,
            "body": body, "credit": SWPC_CREDIT, "link": SWPC_KP_PAGE, "topic": "kosmos", "slot": slot,
            "worth": True}, ""


def storm_now(now, get, done):
    """Səhər və axşam pəncərəsi: Kp cədvəli (1 sorğu); xəbər yazılırsa alerts.json (1 sorğu)."""
    day = now.date()
    if STORM_KEY + day.isoformat() in done:
        return []
    if _in(now, WIN_MORNING):
        mark, slot = f"{STORM_TICK}{day.isoformat()}-seher", "08:40"
    elif _in(now, WIN_EVENING):
        mark, slot = f"{STORM_TICK}{day.isoformat()}-axsam", "20:10"
    else:
        return []
    if mark in done:
        return []
    try:
        rows = parse_kp(get(SWPC_KP))
        if rows[-1][0] < now:
            raise Bad("NOAA-nın Kp cədvəli köhnədir")
        item, why = storm_item(day, rows, now, (), slot)
    except Exception as e:
        item, why = None, _why(e, "NOAA")
    if item is None:
        return [_fail("maqnit-qasirgasi", mark, "Maqnit qasırğası: xəbər yoxdur", why, SWPC_CREDIT, SWPC_KP_PAGE,
                      "kosmos", now)]
    try:
        item = storm_item(day, rows, now, parse_alerts(get(SWPC_ALERTS)), slot)[0]
    except Exception:
        pass    # bildirişlər alınmasa xəbər onlarsız çıxır
    return [item]


#@NEXT@
# --- İstehsal ------------------------------------------------------------------------------------------------------------
PARTS = (meteo_now, storm_now)


def items(root, now, fetch=None, done=None):
    """now anında (Bakı vaxtı) dərc olunacaq hava və təbiət xəbərləri. Sorğu yalnız öz pəncərəsində və fetch ilə gedir;
    done: bu gün qayıtmış açarlar (onların sorğusu getmir). worth=False olanlar «why» ilə qayıdır. Heç vaxt xəta atmır."""
    try:
        now = _baku(now)
        done = set(done or ())
    except Exception:
        return []
    get = _Get(fetch)
    out = []
    for part in PARTS:
        try:
            out += part(now, get, done)
        except Exception as e:  # bir hissənin xətası digərlərini saxlamır
            out.append(_fail("xeta", f"hava-xeta-{part.__name__}-{now:%Y-%m-%dT%H}", "Modul xətası",
                             f"{part.__name__}: {_err(e)}", SWPC_CREDIT, SWPC_PAGE, TOPIC, now))
    return [_guard(i) for i in out]


# --- Sınaq ---------------------------------------------------------------------------------------------------------------


def _verdict(item):
    return "✅ Dərc olunardı" if item.get("worth") else f"⏭ Dərc olunmazdı: {item.get('why') or 'səbəb yazılmayıb'}"


def _show(label, item):
    item = _guard(item)
    return [f"**{label}**", ""] + ox.render(item) + [_verdict(item), ""]


def _label_day(d):
    return f"{ox.day_text(d)} {d.year}"


def _sinaq_meteo(now, get):
    day = now.date()
    notes, mhx, swpc = [], None, None
    try:
        mhx = parse_mhx(get(MHX_URL, "text/html"), now)
    except Exception as e:
        notes.append(_why(e, "MHX"))
    try:
        swpc = parse_swpc_text(get(SWPC_TEXT, "text/plain"))
    except Exception as e:
        notes.append(_why(e, "NOAA"))
    md = []
    days = [day] + ([mhx[0]] if mhx and mhx[0] > day else [])
    for d in days:
        item, why = meteo_item(d, now, mhx, swpc, notes)
        label = (f"Bu gün, {_label_day(d)} (istehsalda 08:30–10:30)" if d == day else
                 f"MHX-nin səhifəsindəki gün, {_label_day(d)} (istehsalda həmin günün səhəri yazılardı)")
        md += _show(label, item or _fail("meteohessas", f"meteohessas-{d.isoformat()}",
                                         "Meteohəssaslar üçün gün: xəbər yoxdur", why, MHX_CREDIT, MHX_URL, TOPIC, now))
    if swpc:
        md += [f"> NOAA-nın 3 günlük proqnozu {swpc[0].astimezone(BAKU):%d.%m.%Y %H:%M}-da (Bakı vaxtı) buraxılıb.", ""]
    return md


def _sinaq_storm(now, get):
    day = now.date()
    rows = parse_kp(get(SWPC_KP))
    alerts = None
    md = [f"> Kp cədvəli: {len(rows)} dövr, {rows[0][0].astimezone(BAKU):%d.%m %H:%M} – "
          f"{rows[-1][0].astimezone(BAKU):%d.%m %H:%M} (Bakı vaxtı).", ""]
    shown = 0
    for back in range(0, 9):
        d = day - back * DAY
        when = now if back == 0 else _at(d, "20:10")
        item, why = storm_item(d, rows, when)
        if item is not None:
            if alerts is None:
                try:
                    alerts = parse_alerts(get(SWPC_ALERTS))
                except Exception as e:
                    alerts = []
                    md += [f"> alerts.json alınmadı: {_err(e)}", ""]
            item = storm_item(d, rows, when, alerts)[0]
            label = (f"Bu gün, {_label_day(d)}" if back == 0 else
                     f"Son real hal: {_label_day(d)} (həmin gün yazılardı, bu gün yox)")
            md += _show(label, item)
            shown += 1
            if back:
                break
        elif back == 0:
            md += _show(f"Bu gün, {_label_day(d)}", _fail("maqnit-qasirgasi", f"{STORM_TICK}{d.isoformat()}-seher",
                                                         "Maqnit qasırğası: xəbər yoxdur", why, SWPC_CREDIT,
                                                         SWPC_KP_PAGE, "kosmos", now))
    if not shown:
        md += ["> Cədvəldəki günlərdə Kp 5-ə (G1) çatmayıb.", ""]
    return md


SINAQ = (("## 1. Meteohəssaslar üçün gün (MHX, NOAA SWPC)", _sinaq_meteo),
         ("## 2. Maqnit qasırğası (NOAA SWPC)", _sinaq_storm))


def sinaq(root, now=None, fetch=None):
    """Nümunələr (Markdown): bu günün qərarı və hər xəbər növünün son real halı, real sorğularla (7 sorğu).
    Sayta və repoya heç nə yazmır. fetch verilməyibsə updater-in fetch-i işlənir."""
    now = _baku(now)
    get = _Get(fetch, pause=PAUSE)
    md = ["# Hava və təbiət xəbərləri (oz_hava.py): sınaq", "",
          f"{now:%d.%m.%Y %H:%M} (Bakı vaxtı). Sayta heç nə yazılmır. İstehsalda sorğu yalnız öz pəncərəsində gedir: "
          f"08:30–10:30 MHX, SWPC mətni və Kp cədvəli; 11:00–13:00 OISST; 16:00–18:00 Open-Meteo proqnozu və dəniz "
          f"proqnozu; 20:00–22:00 Kp cədvəli. Gündə ən çox 8 sorğu.", ""]
    for head, part in SINAQ:
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
