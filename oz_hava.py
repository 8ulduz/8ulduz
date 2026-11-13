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
    pause saniyə fasilə. count göndərilən sorğuların sayıdır, hosts hər hosta neçə sorğu getdiyi. agent verilərsə
    User-Agent odur (ERDDAP üçün), yoxsa updater-in öz User-Agent-i."""

    def __init__(self, fetch=None, pause=0.0):
        self.fetch, self.pause = fetch, pause
        self.cache, self.last, self.hosts, self.count = {}, {}, {}, 0

    def __call__(self, url, accept="application/json", agent=None):
        key = (url, agent)
        if key not in self.cache:
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
                headers = {"Accept": accept}
                if agent:
                    headers["User-Agent"] = agent
                self.cache[key] = (self.fetch(url, timeout=TIMEOUT, headers=headers), None)
            except Exception as e:  # şəbəkə xətası yalnız həmin mənbəni saxlayır
                self.cache[key] = (None, e)
            self.last[host] = time.monotonic()
        data, err = self.cache[key]
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
    """NOAA-nın G şkalası: Kp 5 -> G1 … Kp 9 -> G5; 5-dən aşağı 0. NOAA 4,67-ni (5−) də G1 yazır.
    G4 «Kp 8, 9− daxil», G5 yalnız Kp 9-dur: 8,67 (9−) G4-dür (NOAA özü «8.67 (G4)» yazır), əvvəl «İfrat güclü (G5)» çıxırdı."""
    if kp is None or kp < 4.5:
        return 0
    return 5 if kp >= 8.85 else min(4, int(math.floor(kp + 0.5)) - 4)


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
    tops = [_blk(t) for t, v in kp if v == top]
    when = "" if len(tops) > 3 else tops[0] if len(tops) == 1 else ", ".join(tops[:-1]) + " və " + tops[-1]
    span = "Bakı vaxtı ilə" if len(kp) >= 8 else f"Bakı vaxtı ilə {kp[0][0]:%H:%M}–{kp[-1][0] + 3 * HOUR:%H:%M}"
    head = f"{SWPC_GEN} 3 günlük proqnozuna görə, {ox.day_loc(day)} ({span}, 3 saatlıq dövrlər üzrə) "
    g = g_level(top)
    if g:
        at = f" (saat {when} arası)" if when else ""
        return [head + f"Kp indeksinin ən yüksək göstəricisi {num(top, 2)} olacaq{at}; bu, NOAA şkalasında G{g} "
                f"({G_NAME[g]}) maqnit qasırğası səviyyəsidir."]
    if low == top:
        rng = f"Kp indeksi {num(top, 2)} olacaq"
    else:
        rng = f"Kp indeksi {num(low, 2)}–{num(top, 2)} arasında olacaq"
        if when:
            rng += f"; ən yüksək göstərici ({num(top, 2)}) saat {when} arasına düşür"
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


STORM_CONT = "dünənki qasırğanın davamıdır: bir hadisə, bir xəbər"

def storm_item(day, rows, now, alerts=(), slot="08:40", told=True):
    """Günün maqnit qasırğası xəbəri. rows: parse_kp, alerts: parse_alerts. -> (xəbər | None, səbəb).
    told: dünənki qasırğa haqqında xəbər çıxıb (və ya o özü davam sayılıb). Çıxmayıbsa bu günkü «davam» deyil, ilk xəbərdir:
    axşam sorğusundan sonra başlayan qasırğa əvvəl heç vaxt yazılmırdı (dünən hələ bitməmişdi, bu gün «davam» idi)."""
    today = [r for r in storm_day(rows, day) if g_level(r[1])]
    if not today:
        return None, "bu günün dövrlərində Kp 5-ə (G1) çatmır"
    prev = [r for r in storm_day(rows, day - DAY) if g_level(r[1])]
    if told and prev and today[0][0] - prev[-1][0] <= STORM_GAP and \
            max(g_level(r[1]) for r in today) <= max(g_level(r[1]) for r in prev):
        return None, STORM_CONT
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
    chain = lambda d: f"{STORM_TICK}{d.isoformat()}-davam"
    told = STORM_KEY + (day - DAY).isoformat() in done or chain(day - DAY) in done
    try:
        rows = parse_kp(get(SWPC_KP))
        if rows[-1][0] < now:
            raise Bad("NOAA-nın Kp cədvəli köhnədir")
        item, why = storm_item(day, rows, now, (), slot, told)
    except Exception as e:
        item, why = None, _why(e, "NOAA")
    if item is None:
        fails = [_fail("maqnit-qasirgasi", mark, "Maqnit qasırğası: xəbər yoxdur", why, SWPC_CREDIT, SWPC_KP_PAGE, "kosmos", now)]
        if why == STORM_CONT and chain(day) not in done:  # üç günlük qasırğa: sabah da «davam» sayılsın
            fails.append(_fail("maqnit-qasirgasi", chain(day), "Maqnit qasırğası: davam edir", why, SWPC_CREDIT, SWPC_KP_PAGE, "kosmos", now))
        return fails
    try:
        item = storm_item(day, rows, now, parse_alerts(get(SWPC_ALERTS)), slot, told)[0]
    except Exception:
        pass    # bildirişlər alınmasa xəbər onlarsız çıxır
    return [item]


# --- 3–4. Open-Meteo: normadan fərq, təhlükəli hava həddi ----------------------------------------------------------------
OM_API = "https://api.open-meteo.com/v1/forecast"
OM_MARINE = "https://marine-api.open-meteo.com/v1/marine"
OM_PAGE = "https://open-meteo.com/"
OM_CREDIT = "Open-Meteo (model proqnozu)"
FC_FIELDS = ("temperature_2m_max", "temperature_2m_min", "wind_gusts_10m_max", "snowfall_sum")
SEA_FIELDS = ("wave_height_max",)
LIMITS = {"temperature_2m_max": (-60, 60), "temperature_2m_min": (-60, 60), "wind_gusts_10m_max": (0, 100),
          "snowfall_sum": (0, 500), "wave_height_max": (0, 20)}
CITIES = (("Bakı", "Bakıda", "40.4093", "49.8671"), ("Gəncə", "Gəncədə", "40.6828", "46.3606"),
          ("Sumqayıt", "Sumqayıtda", "40.5897", "49.6686"), ("Lənkəran", "Lənkəranda", "38.7529", "48.85"),
          ("Şəki", "Şəkidə", "41.1919", "47.1706"), ("Quba", "Qubada", "41.3611", "48.5133"),
          ("Naxçıvan", "Naxçıvanda", "39.2089", "45.4122"), ("Şuşa", "Şuşada", "39.758", "46.75"))
SEA = (("Bakı buxtası", "Bakı buxtasında", "40.30", "50.00"), ("Sumqayıt", "Sumqayıt sahilində", "40.62", "49.75"),
       ("Lənkəran", "Lənkəran sahilində", "38.75", "49.00"), ("Nabran", "Nabran sahilində", "41.80", "48.75"),
       ("Neft Daşları", "Neft Daşları yaxınlığında", "40.22", "50.85"))
MOUNTAIN = ("Şəki", "Quba", "Naxçıvan", "Şuşa")     # qar həddi 10 sm; qalan şəhərlərdə 5 sm
GUST, FROST, FROST_BAKU, HEAT, SNOW, SNOW_LOW, WAVE = 20.0, -10.0, -5.0, 38.0, 10.0, 5.0, 3.0
ANOM = 5.0                  # Bakıda maksimum temperaturun normadan fərqi, °C
HZ_KEY = "hava-hedd-"
NORM_KEY = "norma-ferq-"
HZ_SLOT = "16:10"
NORM_SLOT = "16:20"
SINAQ_PAST = 14

# Bakı (40,4093° şm. e., 49,8671° ş. u.) üçün gündəlik norma, °C: ilin günü üzrə (29 fevral daxil, 366 gün).
# Bir dəfə hesablanıb (2026-11-12): Open-Meteo arxivi (archive-api, models=era5), 1991–2020-ci illərin gündəlik maksimum və
# minimumu, ±7 gün üzrə orta; üstünə proqnoz modeli ilə ERA5 arasındakı orta fərq gəlinib (historical-forecast-api,
# 2022–2025, ±15 gün üzrə orta: maksimumda qışda +0,1…+0,9, yayda +2,9…+3,3; minimumda −1,9…+0,2). Bu düzəliş olmasa
# proqnoz modelinin şəhər xanası ERA5-in dəniz təsirli xanasından yayda həmişə «isti» görünərdi.
NORM_MAX = (
    8.5, 8.5, 8.4, 8.3, 8.2, 8.1, 8.0, 7.9, 7.8, 7.8, 7.7, 7.7, 7.6, 7.5, 7.5, 7.5,
    7.4, 7.4, 7.3, 7.3, 7.2, 7.2, 7.2, 7.2, 7.2, 7.2, 7.2, 7.3, 7.3, 7.3, 7.4, 7.4,
    7.4, 7.4, 7.4, 7.4, 7.4, 7.4, 7.4, 7.4, 7.4, 7.5, 7.5, 7.5, 7.5, 7.6, 7.6, 7.7,
    7.9, 8.0, 8.1, 8.2, 8.4, 8.5, 8.6, 8.7, 8.7, 8.9, 9.1, 9.2, 9.2, 9.4, 9.6, 9.6,
    9.8, 9.9, 9.9, 9.9, 10.0, 10.1, 10.1, 10.3, 10.4, 10.5, 10.5, 10.6, 10.8, 10.8, 11.0, 11.2,
    11.3, 11.5, 11.7, 11.8, 12.0, 12.1, 12.1, 12.2, 12.4, 12.6, 12.7, 12.9, 13.0, 13.1, 13.2, 13.4,
    13.6, 13.9, 14.3, 14.6, 14.6, 15.0, 15.3, 15.4, 15.5, 15.7, 15.7, 15.8, 16.0, 16.2, 16.3, 16.5,
    16.6, 16.6, 16.8, 16.9, 17.1, 17.3, 17.5, 17.7, 17.9, 18.1, 18.4, 18.6, 18.8, 19.1, 19.4, 19.6,
    19.8, 20.0, 20.3, 20.5, 20.7, 21.0, 21.2, 21.5, 21.7, 21.9, 22.2, 22.5, 22.7, 22.9, 23.1, 23.4,
    23.7, 24.0, 24.2, 24.4, 24.5, 24.7, 25.0, 25.2, 25.4, 25.7, 25.9, 26.1, 26.1, 26.2, 26.4, 26.7,
    26.8, 26.9, 27.0, 27.2, 27.3, 27.6, 27.8, 28.0, 28.1, 28.1, 28.3, 28.4, 28.6, 28.7, 28.7, 28.8,
    28.9, 29.0, 29.2, 29.3, 29.5, 29.5, 29.6, 29.6, 29.8, 29.8, 29.9, 30.0, 30.1, 30.1, 30.3, 30.4,
    30.5, 30.6, 30.5, 30.6, 30.6, 30.7, 30.7, 30.8, 30.8, 31.0, 31.2, 31.3, 31.3, 31.4, 31.5, 31.5,
    31.5, 31.5, 31.6, 31.5, 31.5, 31.4, 31.4, 31.4, 31.3, 31.3, 31.3, 31.2, 31.1, 31.0, 31.0, 31.0,
    31.0, 31.1, 31.1, 31.0, 31.0, 30.9, 30.8, 30.7, 30.6, 30.5, 30.4, 30.3, 30.1, 30.0, 29.8, 29.7,
    29.5, 29.3, 29.2, 29.1, 28.9, 28.7, 28.5, 28.3, 28.0, 27.7, 27.5, 27.3, 27.1, 26.9, 26.7, 26.5,
    26.3, 26.1, 25.9, 25.7, 25.5, 25.4, 25.1, 24.9, 24.7, 24.4, 24.2, 24.0, 23.8, 23.6, 23.4, 23.2,
    23.0, 22.8, 22.6, 22.5, 22.3, 22.2, 22.1, 22.0, 21.9, 21.7, 21.6, 21.3, 21.1, 21.0, 20.8, 20.6,
    20.4, 20.2, 20.0, 19.9, 19.6, 19.3, 19.0, 18.8, 18.6, 18.4, 18.1, 17.8, 17.6, 17.4, 17.2, 17.0,
    16.8, 16.6, 16.3, 16.1, 15.9, 15.7, 15.5, 15.2, 15.0, 14.8, 14.7, 14.5, 14.3, 14.1, 13.9, 13.7,
    13.4, 13.2, 12.9, 12.7, 12.6, 12.4, 12.3, 12.1, 11.9, 11.6, 11.4, 11.2, 11.1, 10.9, 10.7, 10.7,
    10.6, 10.4, 10.3, 10.1, 10.0, 9.9, 9.8, 9.6, 9.5, 9.4, 9.3, 9.2, 9.1, 9.1, 9.0, 9.0,
    9.0, 9.0, 9.0, 9.0, 9.0, 9.0, 9.0, 9.0, 8.9, 8.8, 8.8, 8.8, 8.7, 8.6,
)
NORM_MIN = (
    3.9, 3.9, 3.8, 3.7, 3.7, 3.6, 3.4, 3.4, 3.4, 3.3, 3.2, 3.1, 3.0, 3.0, 3.0, 2.9,
    2.9, 2.9, 2.8, 2.8, 2.7, 2.7, 2.7, 2.6, 2.5, 2.5, 2.4, 2.4, 2.4, 2.4, 2.4, 2.4,
    2.4, 2.4, 2.4, 2.3, 2.4, 2.5, 2.5, 2.6, 2.6, 2.7, 2.7, 2.7, 2.7, 2.7, 2.8, 2.9,
    2.9, 3.0, 3.1, 3.2, 3.3, 3.4, 3.4, 3.6, 3.7, 3.9, 4.0, 4.0, 4.1, 4.2, 4.2, 4.3,
    4.3, 4.4, 4.5, 4.6, 4.6, 4.6, 4.6, 4.7, 4.7, 4.8, 4.9, 5.0, 5.1, 5.2, 5.3, 5.4,
    5.6, 5.7, 5.8, 5.9, 6.0, 6.2, 6.3, 6.4, 6.5, 6.6, 6.7, 6.8, 7.0, 7.2, 7.3, 7.4,
    7.6, 7.8, 8.1, 8.2, 8.4, 8.6, 8.8, 9.0, 9.2, 9.3, 9.4, 9.5, 9.7, 9.9, 10.0, 10.1,
    10.2, 10.3, 10.4, 10.6, 10.7, 10.9, 11.1, 11.3, 11.6, 11.8, 12.0, 12.2, 12.4, 12.6, 12.9, 13.0,
    13.2, 13.4, 13.7, 13.9, 14.1, 14.3, 14.5, 14.7, 15.0, 15.2, 15.4, 15.7, 15.9, 16.1, 16.3, 16.6,
    16.8, 17.0, 17.2, 17.3, 17.5, 17.6, 17.7, 17.9, 18.1, 18.3, 18.5, 18.7, 18.9, 19.0, 19.2, 19.4,
    19.7, 19.8, 19.9, 20.1, 20.3, 20.5, 20.7, 20.8, 20.9, 21.0, 21.1, 21.2, 21.4, 21.5, 21.5, 21.5,
    21.6, 21.7, 21.9, 22.0, 22.1, 22.3, 22.3, 22.4, 22.4, 22.5, 22.6, 22.6, 22.7, 22.8, 23.0, 23.1,
    23.3, 23.3, 23.4, 23.5, 23.6, 23.7, 23.7, 23.8, 23.8, 23.9, 24.1, 24.2, 24.3, 24.3, 24.4, 24.4,
    24.4, 24.4, 24.5, 24.5, 24.5, 24.5, 24.4, 24.4, 24.4, 24.3, 24.3, 24.3, 24.3, 24.3, 24.2, 24.2,
    24.2, 24.2, 24.2, 24.1, 24.0, 24.0, 23.9, 23.8, 23.7, 23.7, 23.6, 23.5, 23.4, 23.2, 23.2, 23.1,
    23.0, 22.9, 22.8, 22.6, 22.4, 22.3, 22.2, 22.0, 21.8, 21.6, 21.4, 21.2, 21.1, 20.9, 20.7, 20.5,
    20.3, 20.1, 19.9, 19.7, 19.5, 19.5, 19.3, 19.1, 18.9, 18.7, 18.5, 18.3, 18.2, 18.0, 17.8, 17.6,
    17.4, 17.2, 17.0, 16.9, 16.8, 16.7, 16.6, 16.5, 16.3, 16.1, 16.0, 15.8, 15.6, 15.4, 15.2, 15.0,
    14.8, 14.7, 14.6, 14.4, 14.2, 13.9, 13.8, 13.7, 13.5, 13.2, 13.0, 12.7, 12.5, 12.4, 12.2, 12.0,
    11.8, 11.6, 11.4, 11.1, 11.0, 10.7, 10.5, 10.2, 10.1, 9.9, 9.8, 9.7, 9.6, 9.4, 9.2, 9.1,
    8.9, 8.7, 8.4, 8.3, 8.1, 7.9, 7.7, 7.5, 7.4, 7.2, 7.1, 6.9, 6.8, 6.6, 6.5, 6.3,
    6.2, 6.1, 6.0, 5.9, 5.7, 5.6, 5.5, 5.3, 5.2, 5.1, 4.9, 4.8, 4.7, 4.5, 4.4, 4.4,
    4.3, 4.2, 4.1, 4.1, 4.1, 4.2, 4.1, 4.2, 4.1, 4.0, 4.0, 3.9, 3.9, 3.9,
)


def _points(table):
    return "latitude=" + ",".join(p[2] for p in table) + "&longitude=" + ",".join(p[3] for p in table)


def fc_url(past=0):
    """8 şəhərin gündəlik proqnozu: bu gün, sabah, birisi gün (bir sorğu)."""
    return (f"{OM_API}?{_points(CITIES)}&daily={','.join(FC_FIELDS)}&timezone=Asia%2FBaku&wind_speed_unit=ms"
            f"&forecast_days=3" + (f"&past_days={past}" if past else ""))


def marine_url(past=0):
    return (f"{OM_MARINE}?{_points(SEA)}&daily={','.join(SEA_FIELDS)}&timezone=Asia%2FBaku&forecast_days=3"
            + (f"&past_days={past}" if past else ""))


def _cell(col, i, field):
    v = _flt(col[i]) if isinstance(col, list) and i < len(col) else None
    lo, hi = LIMITS[field]
    return v if v is not None and lo <= v <= hi else None


def parse_om(raw, n, fields):
    """Open-Meteo-nun n nöqtəlik gündəlik cavabı -> [{gün: {sahə: ədəd | None}}], nöqtələrin sırası ilə."""
    data = _json(raw)
    if isinstance(data, dict):
        data = [data]
    if not isinstance(data, list) or len(data) != n:
        raise Bad("Open-Meteo cavabı tanınmadı")
    out = []
    for o in data:
        daily = o.get("daily") if isinstance(o, dict) else None
        times = daily.get("time") if isinstance(daily, dict) else None
        if not isinstance(times, list) or not times:
            raise Bad("Open-Meteo cavabında günlər yoxdur")
        units = o.get("daily_units")
        if "wind_gusts_10m_max" in fields and (not isinstance(units, dict) or units.get("wind_gusts_10m_max") != "m/s"):
            raise Bad("Open-Meteo küləyin sürətini m/san ilə verməyib")
        days = {}
        for i, t in enumerate(times):
            try:
                d = datetime.date.fromisoformat(str(t)[:10])
            except ValueError:
                raise Bad("Open-Meteo cavabında tarix tanınmadı")
            days[d] = {f: _cell(daily.get(f), i, f) for f in fields}
        out.append(days)
    return out


def hazards(day, cities, sea=None):
    """Günün hədd keçən göstəriciləri: {növ: [(yerlik, dəyər)]}; hər siyahı ən kəskindən başlayır, boş növ yoxdur.
    Növlərin sırası xəbərdəki sıradır: külək, qar, şaxta, isti, dalğa."""
    hit = {"gust": [], "snow": [], "frost": [], "heat": [], "wave": []}
    for (name, loc, _, _), days in zip(CITIES, cities):
        row = days.get(day) or {}
        g, s = row.get("wind_gusts_10m_max"), row.get("snowfall_sum")
        tn, tx = row.get("temperature_2m_min"), row.get("temperature_2m_max")
        if g is not None and g >= GUST:
            hit["gust"].append((loc, g))
        if s is not None and s >= (SNOW if name in MOUNTAIN else SNOW_LOW):
            hit["snow"].append((loc, s))
        if tn is not None and tn <= (FROST_BAKU if name == "Bakı" else FROST):
            hit["frost"].append((loc, tn))
        if tx is not None and tx >= HEAT:
            hit["heat"].append((loc, tx))
    for (name, loc, _, _), days in zip(SEA, sea or ()):
        w = (days.get(day) or {}).get("wave_height_max")
        if w is not None and w >= WAVE:
            hit["wave"].append((loc, w))
    for kind, rows in hit.items():
        rows.sort(key=lambda r: r[1], reverse=(kind != "frost"))
    return {kind: rows for kind, rows in hit.items() if rows}


_HZ_UNIT = {"gust": "m/san", "snow": "sm", "wave": "m"}
_HZ_TEXT = {"gust": "küləyin ani sürəti {} olacaq", "snow": "{} qar yağacaq", "frost": "minimum temperatur {} olacaq",
            "heat": "maksimum temperatur {} olacaq", "wave": "Xəzərdə dalğanın maksimum hündürlüyü {} olacaq"}
_HZ_TITLE = {"gust": "{} küləyin ani sürəti {} ola bilər", "snow": "{} {} qar yağa bilər",
             "frost": "{} minimum temperatur {} ola bilər", "heat": "{} maksimum temperatur {} ola bilər",
             "wave": "{} dalğanın hündürlüyü {} ola bilər"}


def _hz_val(kind, v):
    return temp(v) if kind in ("frost", "heat") else f"{num(_r1(v), 1)} {_HZ_UNIT[kind]}"


def _hz_line(kind, rows):
    return _HZ_TEXT[kind].format(", ".join(f"{loc} {_hz_val(kind, v)}" for loc, v in rows))


HZ_NOTE = (f"Bu, rəsmi hava proqnozu deyil, Open-Meteo modelinin hesablamasıdır. Xəbər bu hədlər keçiləndə yazılır: "
           f"küləyin ani sürəti {num(GUST, 1)} m/san, minimum temperatur {temp(FROST)} (Bakıda {temp(FROST_BAKU)}), "
           f"maksimum temperatur {temp(HEAT)}, qar {num(SNOW, 1)} sm (Bakı, Gəncə, Sumqayıt və Lənkəranda "
           f"{num(SNOW_LOW, 1)} sm), Xəzərdə dalğa {num(WAVE, 1)} m.")
NORM_NOTE = ("Norma Open-Meteo arxivindəki ERA5 reanalizinin 1991–2020-ci illər üzrə gündəlik orta göstəricisidir: ±7 gün "
             "üzrə hamarlanıb və proqnoz modeli ilə reanaliz arasındakı orta fərqə (2022–2025-ci illər) görə "
             "düzəldilib. Bu, Milli Hidrometeorologiya Xidmətinin stansiya norması deyil.")


def hazard_item(day, cities, sea=None, extra=(), notes=()):
    """«Təhlükəli hava həddi»: day (sabah) üçün keçilən bütün hədlər bir xəbərdə. -> (xəbər | None, səbəb)."""
    hit = hazards(day, cities, sea)
    if not hit:
        return None, "; ".join(["sabah üçün heç bir hədd keçilmir"] + list(notes))
    kinds = list(hit)
    loc, v = hit[kinds[0]][0]
    title = "Model proqnozu: sabah " + _HZ_TITLE[kinds[0]].format(loc, _hz_val(kinds[0], v))
    lead = f"Open-Meteo-nun model proqnozuna görə, sabah, {ox.day_loc(day)} {_hz_line(kinds[0], hit[kinds[0]])}."
    body = [f"Model proqnozuna görə, {_hz_line(kind, hit[kind])}." for kind in kinds[1:]]
    return {"kind": "hava-hedd", "key": HZ_KEY + day.isoformat(), "title": title[:TITLE_MAX], "lead": lead,
            "body": body + list(extra) + [HZ_NOTE], "credit": OM_CREDIT, "link": OM_PAGE, "topic": TOPIC,
            "slot": HZ_SLOT, "worth": True}, ""


def norm_of(day):
    """Günün norması: (orta maksimum, orta minimum), °C."""
    i = datetime.date(2000, day.month, day.day).timetuple().tm_yday - 1
    return NORM_MAX[i], NORM_MIN[i]


def anomaly(day, baku):
    """Bakıda günün maksimum temperaturunun normadan fərqi (onda birə); proqnoz yoxdursa None."""
    tx = (baku.get(day) or {}).get("temperature_2m_max")
    return None if tx is None else _r1(_r1(tx) - norm_of(day)[0])


def _norm_cmp(d, nx):
    return (f"1991–2020-ci illərin həmin günə düşən orta maksimumundan ({temp(nx)}) {num(d, 1)} dərəcə "
            f"{'yüksəkdir' if d > 0 else 'aşağıdır'}")


def norm_item(day, baku):
    """«Normadan fərq»: day (sabah) Bakıda maksimum temperatur normadan ANOM və daha çox fərqlidirsə, dövrün ilk günü.
    baku: parse_om-un Bakı üçün verdiyi günlər. -> (xəbər | None, səbəb)."""
    d = anomaly(day, baku)
    if d is None:
        return None, "Bakı üçün sabahın proqnozu yoxdur"
    if abs(d) < ANOM:
        return None, f"Bakıda fərq {num(d, 1)} dərəcədir (hədd {num(ANOM, 1)})"
    p = anomaly(day - DAY, baku)
    if p is not None and abs(p) >= ANOM and (p > 0) == (d > 0):
        return None, "isti və ya soyuq dövrün davamıdır: bir hadisə, bir xəbər"
    tx, tn = baku[day]["temperature_2m_max"], baku[day].get("temperature_2m_min")
    nx, nn = norm_of(day)
    title = f"Model proqnozu: sabah Bakıda gündüz hava normadan {num(d, 1)} dərəcə {'isti' if d > 0 else 'soyuq'} olacaq"
    lead = (f"Open-Meteo-nun model proqnozuna görə, sabah, {ox.day_loc(day)} Bakıda maksimum temperatur {temp(tx)} "
            f"olacaq. Bu, {_norm_cmp(d, nx)}.")
    body = []
    if tn is not None:
        dn = _r1(_r1(tn) - nn)
        if dn == 0:
            tail = f"1991–2020-ci illərin orta minimumuna ({temp(nn)}) bərabərdir"
        else:
            tail = (f"1991–2020-ci illərin orta minimumundan ({temp(nn)}) {num(dn, 1)} dərəcə "
                    f"{'yüksəkdir' if dn > 0 else 'aşağıdır'}")
        body.append(f"Minimum temperatur {temp(tn)} gözlənilir: bu, {tail}.")
    return {"kind": "norma-ferq", "key": NORM_KEY + day.isoformat(), "title": title[:TITLE_MAX], "lead": lead,
            "body": body + [NORM_NOTE], "credit": OM_CREDIT, "link": OM_PAGE, "topic": TOPIC, "slot": NORM_SLOT,
            "worth": True}, ""


def _fc_fail(day, why, now):
    return [_fail("hava-hedd", HZ_KEY + day.isoformat(), "Təhlükəli hava həddi: xəbər yoxdur", why, OM_CREDIT, OM_PAGE,
                  TOPIC, now),
            _fail("norma-ferq", NORM_KEY + day.isoformat(), "Normadan fərq: xəbər yoxdur", why, OM_CREDIT, OM_PAGE,
                  TOPIC, now)]


def forecast_items(day, cities, sea, now, notes=()):
    """Proqnoz pəncərəsinin iki qeydi (day sabahdır): təhlükəli hava həddi və normadan fərq. Bakıda şaxta və ya isti
    həddi keçilibsə normadan fərq ayrıca xəbər deyil, hədd xəbərində bir cümlədir (bir hadisə, bir xəbər)."""
    if day not in cities[0]:
        return _fc_fail(day, "Open-Meteo proqnozunda sabahkı gün yoxdur", now)
    fails = _fc_fail(day, "", now)
    nitem, nwhy = norm_item(day, cities[0])
    hit = hazards(day, cities, sea)
    extra = []
    if nitem and any(loc == CITIES[0][1] for kind in ("frost", "heat") for loc, _ in hit.get(kind, ())):
        tx = cities[0][day]["temperature_2m_max"]
        extra = [f"Bakıda maksimum temperatur ({temp(tx)}) {_norm_cmp(anomaly(day, cities[0]), norm_of(day)[0])}."]
        nitem, nwhy = None, "təhlükəli hava həddi xəbərində yazılır: bir hadisə, bir xəbər"
    hitem, hwhy = hazard_item(day, cities, sea, extra, notes)
    return [hitem or dict(fails[0], lead=hwhy, why=hwhy), nitem or dict(fails[1], lead=nwhy, why=nwhy)]


def forecast_now(now, get, done):
    """16:00–18:00 pəncərəsi: Open-Meteo proqnozu (1 sorğu) və dəniz proqnozu (1 sorğu), sabah üçün."""
    day = now.date() + DAY
    keys = (HZ_KEY + day.isoformat(), NORM_KEY + day.isoformat())
    if not _in(now, WIN_FORECAST) or all(k in done for k in keys):
        return []
    try:
        cities = parse_om(get(fc_url()), len(CITIES), FC_FIELDS)
    except Exception as e:
        return [i for i in _fc_fail(day, _why(e, "Open-Meteo"), now) if i["key"] not in done]
    notes, sea = [], None
    try:
        sea = parse_om(get(marine_url()), len(SEA), SEA_FIELDS)
    except Exception as e:
        notes.append(_why(e, "Open-Meteo dəniz proqnozu"))
    return [i for i in forecast_items(day, cities, sea, now, notes) if i["key"] not in done]


# --- 5. Xəzərin suyu -----------------------------------------------------------------------------------------------------
SST_BASE = "https://coastwatch.pfeg.noaa.gov/erddap/griddap/ncdcOisst21NrtAgg_LonPM180"
SST_PAGE = SST_BASE + ".html"
SST_CREDIT = "NOAA OISST (peyk məlumatı)"
SST_AGENT = "8ulduz-bot/1.0 (+https://8ulduz.az)"   # ERDDAP GitHub-dan brauzer kimi görünən User-Agent-ə 403 verib
SST_LAST = SST_BASE + ".json?sst%5B(last)%5D%5B(0.0)%5D%5B(40.375):(40.625)%5D%5B(49.625):(50.125)%5D"   # yoxlama üçün
SST_KEY = "xezer-su-"
SST_SLOT = "11:10"
SST_BACK = 10               # sorğu son 10 günü istəyir: son gün və ondan 7 gün əvvəl
SST_STALE = 4               # son gün bundan köhnədirsə xəbər yoxdur (OISST adətən 1–2 gün geridədir)
SST_MIN = 0.5               # mövsümdən kənar bir həftədə bundan az dəyişiklik xəbər deyil
SEASON = (5, 9)             # çimərlik mövsümü: may–sentyabr, hər gün; digər aylarda şənbə
SST_NOTE = ("Bu, peyk və ölçmə məlumatlarından hesablanan açıq dəniz səthinin gündəlik orta temperaturudur (0,25 "
            "dərəcəlik şəbəkə); sahildə, çimərlik zolağında suyun temperaturu fərqlənə bilər.")


def sst_url(day):
    """Abşeron yaxınlığındakı 6 xana (ikisi sahildədir və həmişə boşdur), son SST_BACK gün."""
    start = (day - SST_BACK * DAY).isoformat()
    q = f"sst[({start}T12:00:00Z):1:(last)][(0.0)][(40.375):1:(40.625)][(49.625):1:(50.125)]"
    return SST_BASE + ".json?" + q.replace("[", "%5B").replace("]", "%5D")


def parse_sst(raw):
    """ERDDAP cədvəli -> {gün: {(en, uzunluq): °C}}; boş xanalar yazılmır."""
    data = _json(raw)
    table = data.get("table") if isinstance(data, dict) else None
    names = table.get("columnNames") if isinstance(table, dict) else None
    if not isinstance(names, list) or any(n not in names for n in ("time", "latitude", "longitude", "sst")):
        raise Bad("OISST cavabı tanınmadı")
    it, la, lo, iv = (names.index(n) for n in ("time", "latitude", "longitude", "sst"))
    out = {}
    for r in table.get("rows") or []:
        try:
            d = datetime.date.fromisoformat(str(r[it])[:10])
            cell, v = (r[la], r[lo]), _flt(r[iv])
        except (ValueError, IndexError, TypeError):
            raise Bad("OISST cavabında sətir tanınmadı")
        out.setdefault(d, {})
        if v is not None and -2 <= v <= 40:
            out[d][cell] = v
    if not out:
        raise Bad("OISST cavabı boşdur")
    return out


def _rng(vals):
    lo, hi = num(vals[0], 1), num(vals[-1], 1)
    return lo if lo == hi else f"{lo}–{hi}"


def sea_item(data, now):
    """«Xəzərin suyu»: son günün temperaturu və 7 gün əvvəllə müqayisə (eyni xanalar). -> (xəbər | None, səbəb)."""
    day = now.date()
    full = sorted(d for d, cells in data.items() if len(cells) >= 2)
    if not full:
        return None, "OISST-də Abşeron xanaları boşdur"
    last = full[-1]
    if last > day or (day - last).days > SST_STALE:
        return None, f"OISST məlumatı köhnədir (son gün {ox.day_text(last)})"
    cur, old = data[last], data.get(last - 7 * DAY) or {}
    cells = sorted(c for c in cur if c in old)
    week = len(cells) >= 2
    if not week:
        cells = sorted(cur)
    vals = sorted(_r1(cur[c]) for c in cells)
    mean = _r1(sum(cur[c] for c in cells) / len(cells))
    delta, was, mean0 = None, [], 0.0
    if week:
        was = sorted(_r1(old[c]) for c in cells)
        mean0 = _r1(sum(old[c] for c in cells) / len(cells))
        delta = _r1(mean - mean0)
    if not SEASON[0] <= day.month <= SEASON[1]:
        if delta is None:
            return None, "bir həftə əvvəlin məlumatı yoxdur: müqayisə mümkün deyil"
        if abs(delta) < SST_MIN:
            return None, f"bir həftədə dəyişiklik {num(delta, 1)} dərəcədir (hədd {num(SST_MIN, 1)}): xəbər deyil"
    title = f"Abşeron yaxınlığında Xəzərin səth temperaturu {_rng(vals)} °C"
    if delta:
        title += f": bir həftədə {num(delta, 1)} dərəcə {'isinib' if delta > 0 else 'soyuyub'}"
    lead = (f"ABŞ Milli Okean və Atmosfer Administrasiyasının (NOAA) OISST peyk məlumatına görə, {ox.day_loc(last)} "
            f"Abşeron yarımadası yaxınlığında Xəzər dənizində suyun səth temperaturu {_rng(vals)} °C olub "
            f"({len(cells)} nöqtə üzrə orta {num(mean, 1)} °C).")
    body = []
    if delta is not None:
        change = "dəyişməyib" if delta == 0 else f"{num(delta, 1)} dərəcə {'artıb' if delta > 0 else 'azalıb'}"
        body.append(f"Bir həftə əvvəl, {ox.day_loc(last - 7 * DAY)} eyni nöqtələrdə {_rng(was)} °C (orta "
                    f"{num(mean0, 1)} °C) idi: orta göstərici {change}.")
    return {"kind": "xezer-su", "key": SST_KEY + day.isoformat(), "title": title[:TITLE_MAX], "lead": lead,
            "body": body + [SST_NOTE], "credit": SST_CREDIT, "link": SST_PAGE, "topic": TOPIC, "slot": SST_SLOT,
            "worth": True}, ""


def sea_runs(day):
    """Sorğu günü: may–sentyabr hər gün, digər aylarda şənbə."""
    return SEASON[0] <= day.month <= SEASON[1] or day.weekday() == 5


def sea_now(now, get, done):
    """11:00–13:00 pəncərəsi: OISST (1 sorğu)."""
    day = now.date()
    key = SST_KEY + day.isoformat()
    if not _in(now, WIN_SEA) or not sea_runs(day) or key in done:
        return []
    try:
        item, why = sea_item(parse_sst(get(sst_url(day), agent=SST_AGENT)), now)
    except Exception as e:
        item, why = None, _why(e, "OISST")
    return [item or _fail("xezer-su", key, "Xəzərin suyu: xəbər yoxdur", why, SST_CREDIT, SST_PAGE, TOPIC, now)]


# --- İstehsal ------------------------------------------------------------------------------------------------------------
PARTS = (meteo_now, storm_now, sea_now, forecast_now)


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


def _sinaq_forecast(now, get):
    day = now.date() + DAY
    cities = parse_om(get(fc_url(SINAQ_PAST)), len(CITIES), FC_FIELDS)
    notes, sea = [], None
    try:
        sea = parse_om(get(marine_url(SINAQ_PAST)), len(SEA), SEA_FIELDS)
    except Exception as e:
        notes.append(_why(e, "Open-Meteo dəniz proqnozu"))
    md = []
    for item in forecast_items(day, cities, sea, now, notes):
        md += _show(f"Sabah, {_label_day(day)} (istehsalda 16:00–18:00)", item)
    past = sorted((d for d in cities[0] if d <= now.date()), reverse=True)
    tail = "(bir gün əvvəl yazılardı; modelin həmin gün üçün son hesablaması ilə)"
    for name, build in (("hədd", lambda d: hazard_item(d, cities, sea)),
                        ("normadan fərq", lambda d: norm_item(d, cities[0]))):
        for d in past:
            item = build(d)[0]
            if item:
                md += _show(f"Son real hal ({name}): {_label_day(d)} {tail}", item)
                break
        else:
            md += [f"> Son {len(past)} gündə xəbər olmayıb ({name}).", ""]
    return md


def _sinaq_sea(now, get):
    day = now.date()
    md = []
    try:
        item, why = sea_item(parse_sst(get(sst_url(day), agent=SST_AGENT)), now)
    except Exception as e:
        item, why = None, _why(e, "OISST")
        for name, url, agent in (("updater-in User-Agent-i ilə", sst_url(day), None),
                                 ("yalnız son gün", SST_LAST, SST_AGENT), ("yalnız son gün, updater-in User-Agent-i ilə",
                                                                         SST_LAST, None)):
            try:
                md += [f"> Yoxlama ({name}): alındı, {len(get(url, agent=agent))} bayt.", ""]
            except Exception as e2:
                md += [f"> Yoxlama ({name}): {_err(e2)}.", ""]
    label = (f"Bu günün məlumatı ilə, {_label_day(day)} (istehsalda 11:00–13:00: may–sentyabr hər gün, digər aylarda "
             f"şənbə{'' if sea_runs(day) else '; bu gün sorğu getməzdi'})")
    return _show(label, item or _fail("xezer-su", SST_KEY + day.isoformat(), "Xəzərin suyu: xəbər yoxdur", why,
                                      SST_CREDIT, SST_PAGE, TOPIC, now)) + md


SINAQ = (("## 1. Meteohəssaslar üçün gün (MHX, NOAA SWPC)", _sinaq_meteo),
         ("## 2. Maqnit qasırğası (NOAA SWPC)", _sinaq_storm),
         ("## 3. Təhlükəli hava həddi və normadan fərq (Open-Meteo)", _sinaq_forecast),
         ("## 4. Xəzərin suyu (NOAA OISST)", _sinaq_sea))


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
