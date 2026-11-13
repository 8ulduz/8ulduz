"""8ulduz-un öz xəbərləri, mərhələ 2: maliyyə şablonları, süni intellektsiz (sahib, 2026-11-10: «Mərhələ 2-ni qur»).

1. «Dünya birjaları»: çərşənbə axşamı–şənbə 09:00-da (pəncərə 09:00–09:40), ABŞ seansı bağlanandan sonra.
   - Yahoo Finance spark (saytın updater-i markets.json üçün eyni ünvanı işlədir: range=1d&interval=1d), alınmasa
     query2: S&P 500, Nasdaq Composite, Dow Jones, BIST 100, DAX, FTSE 100, Nikkei 225. Əmtəə yoxdur (təbii qazın
     əvvəlki bağlanışı eyni sorğuda 20 dəqiqədə işarəsini dəyişirdi, 2026-11-09).
   - IMOEX: Moskva Birjasının ISS tarixçəsi (gündəlik CLOSE), GitHub-dan alınmasa IMOEX yazılmır.
   - Dəyişmə Yahoo-nun fulldayChange-idir: chartPreviousClose BIST 100 üçün seans gedəndə köhnə qalır (2026-11-10 09:19Z:
     cümənin 11 482,6 bağlanışı, bazar ertəsinin 11 712,67 yox); fulldayChange regularMarketChangePercent ilə uyğun
     gəlmirsə indeks yazılmır.
   - Xəbər əvvəlki iş gününün (çərşənbə axşamı -> bazar ertəsi, şənbə -> cümə) seanslarıdır. Seansı davam edən birja
     (09:00-da Tokio) ayrıca sətirdə, Bakı vaxtı ilə saatı yazılaraq verilir; bağlı olan (bayram) birja yazılmır.
   - Sorğu: 2 (Yahoo + Moskva Birjası), Yahoo alınmasa 3.
2. «Kriptovalyuta bazarı»: hər gün 10:00-da (pəncərə 10:00–10:40).
   - CoinGecko-nun açarsız simple/price sorğusu (1 sorğu): bitkoin, efir, XRP, BNB, Solana, Dogecoin, Toncoin, dollar və
     manatla, son 24 saatın dəyişməsi ilə. 429 olsa 2 saniyədən sonra bir dəfə təkrar.
   - İş günləri (bazar ertəsi–cümə) yalnız bitkoin və ya efir son 24 saatda 2% və daha çox dəyişibsə dərc olunur,
     şənbə və bazar hər gün.
   - Faza 1-in metal xəbərində (oz_bazar) bitkoin sətri artıq yoxdur: kripto bu xəbərdədir.
3. «Banklarda dollar və avro»: iş günləri 10:30-da (pəncərə 10:30–11:10).
   - Bankların öz saytlarındakı nağd alış-satış məzənnəsi; yalnız səhifəsi bu günün tarixini göstərən bank sayılır.
     Ən azı 2 bank lazımdır. Dollar və avro üçün aralıq, aralığın uclarındakı banklar adı ilə.
   - Bank siyahısı (BANKS) və çıxarılanlar (UNDATED) aşağıda, səbəbi ilə. Sorğu: gündə 4 (ABB-nin səhifəsi ağırdır:
     RSC sorğusu ~480 KB; Unibank 167 KB, Xalq Bank 92 KB, AccessBank 48 KB). Səhifə dar oxunur: yalnız lazım olan hissə.
4. «BFB-də dövlət qiymətli kağızları hərracı»: Maliyyə Nazirliyinin istiqrazları çərşənbə axşamı, Mərkəzi Bankın notları
   çərşənbə və cümə axşamı (iş günləri). Sifarişlər 11:00–11:30 toplanır, nəticənin bfb.az-da çıxma saatı bilinmir:
   iki yoxlama, 13:30–13:40 və 18:30–19:10. Ana səhifənin yerləşdirmələr cədvəli (1 sorğu) bu günün AMB/MN sətirlərini
   verir, hər sətrin öz səhifəsi (gündə 1–2 sorğu) yerləşdirilən həcmi, müddəti və orta çəkili gəlirliliyi. Eyni günün
   hərracları bir xəbərdir. Cədvəldəki «Həcm» təklif olunan həcmdir, yerləşdirilən həcm yalnız hərracın səhifəsindədir.

Sorğular və `done` (canlı, gündə ən çox 15):
- items(root, now, fetch, done) yalnız xəbərin pəncərəsində sorğu göndərir. `done`: bu gün artıq işlənmiş açarlar. Açar
  `done`-dadırsa heç bir sorğu getmir.
- Hər xəbər pəncərəsində bir dəfə sorğu göndərir: sorğudan sonra dərc olunmayan nəticə də (worth False, «why» ilə: az
  dəyişmə, köhnə tarix, şəbəkə xətası) öz açarı ilə qayıdır. Canlı hər qayıdan açarı `done`-a yazmalıdır (yalnız dərc
  olunanları yox): o gün həmin xəbər üçün başqa sorğu getməsin. Ehtiyat yol sorğunun öz içindədir: Yahoo üçün query2,
  CoinGecko üçün 429-dan sonra bir təkrar, BFB üçün ikinci yoxlama (birinci yoxlamada nəticə yoxdursa, bfb.az
  alınmırsa və ya hərrac səhifəsi oxunmursa heç nə qayıtmır, axşam yenə yoxlanır).
- Gündəlik say, ən pis halda: birja 3, kripto 2, banklar 4, BFB 6 (1 + 2 səhifə, iki yoxlama) = 15; adi gündə 8–11.

Sayta qoşulmayıb: updater.py və pipeline bu faylı çağırmır.
Nümunələr: python oz_maliyye.py --sinaq --root DIR [--now 2026-11-10T09:00+04:00]
"""
import datetime
import html
import json
import pathlib
import re
import sys
import time
import urllib.error
import urllib.parse

import oz_teqvim
import oz_xeber as ox

BAKU = ox.BAKU
UTC = datetime.timezone.utc
DAY = datetime.timedelta(days=1)
WINDOW = datetime.timedelta(minutes=40)
TIMEOUT = 15
PAUSE = 1.0          # sınaqda eyni hosta sorğular arasında
_sleep = time.sleep  # testlər əvəz edir
TOPIC = "iqtisadiyyat"
COUNT = {2: "İki", 3: "Üç", 4: "Dörd", 5: "Beş", 6: "Altı", 7: "Yeddi"}


# --- Köməkçilər ---------------------------------------------------------------------------------------

def _baku(now):
    return now.astimezone(BAKU) if now.tzinfo else now.replace(tzinfo=BAKU)


def _num(x):
    """Sonlu ədəd (float) və ya None: mətn, bool, NaN və sonsuzluq rədd edilir."""
    if isinstance(x, bool) or not isinstance(x, (int, float)):
        return None
    x = float(x)
    if x != x or x in (float("inf"), float("-inf")):
        return None
    return x


def _numtext(s):
    """«1.6940», «99,506.0306», «40,000,000» -> float (vergül minlik ayırıcıdır); alınmırsa None."""
    s = (s or "").strip().replace(",", "")
    if not re.fullmatch(r"\d+(?:\.\d+)?", s):
        return None
    return float(s)


def _text(raw):
    if isinstance(raw, (bytes, bytearray)):
        return bytes(raw).decode("utf-8", "replace")
    return raw if isinstance(raw, str) else ""


def _json(raw):
    """JSON cavabı və ya None (zibil, HTML, kəsilmiş cavab)."""
    try:
        return json.loads(_text(raw))
    except ValueError:
        return None


def _clean(s):
    return " ".join(html.unescape(re.sub(r"<[^>]+>", " ", s or "")).split())


def _dmy(s):
    """«06.11.2026» -> date və ya None."""
    m = re.search(r"(\d\d)\.(\d\d)\.(\d{4})", s or "")
    if not m:
        return None
    try:
        return datetime.date(int(m.group(3)), int(m.group(2)), int(m.group(1)))
    except ValueError:
        return None


def _month_date(day, month, year):
    """(«6», «Noyabr», «2026») -> date və ya None."""
    name = ox._low(month or "")
    if name not in ox.MONTHS:
        return None
    try:
        return datetime.date(int(year), ox.MONTHS.index(name) + 1, int(day))
    except ValueError:
        return None


def _date_text(d):
    return f"{ox.day_text(d)} {d.year}"


def _year_loc(d):
    """«4 noyabr 2026-cı ildə»."""
    return f"{ox.day_text(d)} {ox.ordinal(d.year)} ildə"


def _pct(v):
    return ox.az_num(v, 2) + "%"


def _join(words):
    words = list(words)
    return ", ".join(words[:-1]) + " və " + words[-1] if len(words) > 1 else "".join(words)


def _err(e):
    code = getattr(e, "code", None)
    return f"{type(e).__name__} {code}" if isinstance(e, urllib.error.HTTPError) and code else type(e).__name__


def _in_window(now, slot, length=WINDOW):
    start = datetime.datetime.combine(now.date(), slot, BAKU)
    return start <= now < start + length


def _window_text(slot, length=WINDOW):
    start = datetime.datetime.combine(datetime.date(2026, 1, 1), slot)
    return f"{slot:%H:%M}–{start + length:%H:%M}"


def is_working_day(d):
    """Beşgünlük iş həftəsinin iş günü (oz_teqvim). Rəsmi təqvimi olmayan ildə həftə içi iş günü sayılır: bayramda
    banklar məzənnəni yeniləmir, tarix yoxlaması xəbəri onsuz da saxlayır."""
    off = oz_teqvim.qeyri_is_gunu(d)
    if off is None:
        return d.weekday() < 5
    return not off


def prev_weekday(d):
    """Əvvəlki həftə içi gün: çərşənbə axşamı -> bazar ertəsi, şənbə -> cümə, bazar ertəsi -> cümə."""
    d -= DAY
    while d.weekday() >= 5:
        d -= DAY
    return d


def _get(fetch, url, headers=None, timeout=TIMEOUT):
    return fetch(url, timeout=timeout, headers=headers)


def _guard(item):
    """Rəhbərliyin adı keçən xəbər avtomatik çıxmır (oz_xeber.needs_owner)."""
    if ox.needs_owner("\n".join([item["title"], item["lead"]] + list(item["body"]))):
        return None, "rəhbərliyin adı keçir: sahibin təsdiqi lazımdır"
    return item, item.get("why", "")


def _skip(kind, key, slot, title, why, credit, link):
    """Sorğudan sonra dərc olunmayan nəticə: açar `done`-a düşsün, o gün yenə sorğu getməsin."""
    return {"kind": kind, "key": key, "title": title, "lead": _cap(why) + ".", "body": [], "credit": credit, "link": link,
            "topic": TOPIC, "slot": f"{slot:%H:%M}", "worth": False, "why": why}


def _cap(s):
    return s[:1].upper() + s[1:]


# --- 1. Dünya birjaları ---------------------------------------------------------------------------------

BIRJA_SLOT = datetime.time(9, 0)
BIRJA_DAYS = (1, 2, 3, 4, 5)  # çərşənbə axşamı–şənbə: bazar ertəsi–cümənin seansları
BIRJA_MIN = 3                  # bundan az indeksin bağlanışı varsa xəbər yoxdur
YAHOO = ("https://query1.finance.yahoo.com", "https://query2.finance.yahoo.com")
SPARK = "/v7/finance/spark?symbols={}&range=1d&interval=1d"
# (simvol, ad, şəhər); IMOEX Yahoo-da yoxdur, Moskva Birjasından gəlir
INDICES = (
    ("^GSPC", "S&P 500", "Nyu-York"),
    ("^IXIC", "Nasdaq Composite", "Nyu-York"),
    ("^DJI", "Dow Jones", "Nyu-York"),
    ("XU100.IS", "BIST 100", "İstanbul"),
    ("IMOEX", "IMOEX", "Moskva"),
    ("^GDAXI", "DAX", "Frankfurt"),
    ("^FTSE", "FTSE 100", "London"),
    ("^N225", "Nikkei 225", "Tokio"),
)
US = ("^GSPC", "^IXIC", "^DJI")
MOEX_URL = ("https://iss.moex.com/iss/history/engines/stock/markets/index/securities/IMOEX.json"
            "?iss.meta=off&iss.only=history&history.columns=TRADEDATE,CLOSE&from={}")
MOEX_TIMEOUT = 10
BIRJA_LINK = "https://finance.yahoo.com/markets/world-indices/"


def spark_url(host=YAHOO[0]):
    return host + SPARK.format(urllib.parse.quote(",".join(s for s, _, _ in INDICES if s != "IMOEX"), safe=","))


def _spark_quote(r, now_ts):
    """Spark nəticəsinin bir simvolu -> {sym, value, change, pct, day, live, at} və ya None."""
    if not isinstance(r, dict) or not isinstance(r.get("symbol"), str):
        return None
    resp = r.get("response")
    meta = resp[0].get("meta") if isinstance(resp, list) and resp and isinstance(resp[0], dict) else None
    if not isinstance(meta, dict):
        return None
    price, change = _num(meta.get("regularMarketPrice")), _num(meta.get("fulldayChange"))
    cpc, rmcp = _num(meta.get("chartPreviousClose")), _num(meta.get("regularMarketChangePercent"))
    rmt, off = _num(meta.get("regularMarketTime")), _num(meta.get("gmtoffset"))
    if not price or price <= 0 or rmt is None or off is None:
        return None
    if change is None and cpc:
        change = price - cpc
    if change is None or price - change <= 0:
        return None
    pct = change / (price - change) * 100
    if abs(pct) >= 25 or (rmcp is not None and abs(rmcp - pct) > 0.05):
        return None  # zibil və ya bir-birinə uyğun gəlməyən sahələr
    period = meta.get("currentTradingPeriod")
    reg = period.get("regular") if isinstance(period, dict) else None
    start = _num(reg.get("start")) if isinstance(reg, dict) else None
    end = _num(reg.get("end")) if isinstance(reg, dict) else None
    live = start is not None and end is not None and start <= rmt < end and now_ts < end
    try:
        day = datetime.datetime.fromtimestamp(rmt + off, UTC).date()
        at = datetime.datetime.fromtimestamp(rmt, UTC).astimezone(BAKU)
    except (OverflowError, OSError, ValueError):
        return None
    return {"sym": r["symbol"], "value": price, "change": change, "pct": round(pct, 2), "day": day, "live": live, "at": at}


def parse_spark(raw, now):
    """Yahoo spark cavabı -> {simvol: qiymət}. now: sorğu anı (seans davam edirmi)."""
    doc = _json(raw)
    spark = doc.get("spark") if isinstance(doc, dict) else None
    result = spark.get("result") if isinstance(spark, dict) else None
    out = {}
    for r in result if isinstance(result, list) else []:
        q = _spark_quote(r, now.timestamp())
        if q:
            out[q["sym"]] = q
    return out


def spark_fetch(fetch, now):
    """(qiymətlər, host) və ya ({}, xətalar): əvvəl query1, alınmasa query2."""
    errors = []
    for host in YAHOO:
        name = urllib.parse.urlsplit(host).netloc
        try:
            quotes = parse_spark(_get(fetch, spark_url(host)), now)
        except Exception as e:
            errors.append(f"{name}: {_err(e)}")
            continue
        if quotes:
            return quotes, name
        errors.append(f"{name}: cavabda indeks yoxdur")
    return {}, "; ".join(errors)


def parse_moex(raw):
    """Moskva Birjasının ISS tarixçəsi -> [(gün, bağlanış)], köhnədən yeniyə."""
    doc = _json(raw)
    hist = doc.get("history") if isinstance(doc, dict) else None
    cols = hist.get("columns") if isinstance(hist, dict) else None
    rows = hist.get("data") if isinstance(hist, dict) else None
    if not isinstance(cols, list) or not isinstance(rows, list) or "TRADEDATE" not in cols or "CLOSE" not in cols:
        return []
    i, j = cols.index("TRADEDATE"), cols.index("CLOSE")
    out = {}
    for row in rows:
        if not isinstance(row, list) or len(row) <= max(i, j):
            continue
        try:
            day = datetime.date.fromisoformat(str(row[i]))
        except ValueError:
            continue
        close = _num(row[j])
        if close and close > 0:
            out[day] = close
    return sorted(out.items())


def imoex_quote(rows, target):
    """IMOEX-in `target` günü bağlanışı və əvvəlki bağlanışa görə dəyişməsi, ya da None."""
    days = [d for d, _ in rows]
    if target not in days or days.index(target) == 0:
        return None
    k = days.index(target)
    (day, close), (pday, pclose) = rows[k], rows[k - 1]
    if (day - pday).days > 10:
        return None
    pct = (close - pclose) / pclose * 100
    if abs(pct) >= 25:
        return None
    return {"sym": "IMOEX", "value": close, "change": close - pclose, "pct": round(pct, 2), "day": day, "live": False,
            "at": None}


def moex_fetch(fetch, target):
    """(IMOEX və ya None, qeyd)."""
    try:
        rows = parse_moex(_get(fetch, MOEX_URL.format((target - 14 * DAY).isoformat()), timeout=MOEX_TIMEOUT))
    except Exception as e:
        return None, f"Moskva Birjası alınmadı ({_err(e)})"
    q = imoex_quote(rows, target)
    return q, "" if q else f"Moskva Birjasının tarixçəsində {_date_text(target)} bağlanışı yoxdur"


def _pts(v):
    return ox.az_num(v, 2)


def _rise(pct):
    return "yüksəlib" if pct > 0 else "enib"


def _closed(r):
    """«2,35% yüksələrək 7 549,94 bənddə»."""
    if not r["pct"]:
        return f"dəyişmədən {_pts(r['value'])} bənddə"
    return f"{_pct(r['pct'])} {'yüksələrək' if r['pct'] > 0 else 'enərək'} {_pts(r['value'])} bənddə"


def _live_line(r):
    head = f"{r['name']} ({r['city']}): seans davam edir, Bakı vaxtı ilə {ox.time_loc(r['at'])} indeks {_pts(r['value'])} bənd olub"
    if not r["pct"]:
        return head + ", əvvəlki bağlanış səviyyəsindədir"
    return head + f", bu, əvvəlki bağlanışdan {_pct(r['pct'])} {'yüksəkdir' if r['pct'] > 0 else 'aşağıdır'}"


def _birja_title(res):
    by = {r["sym"]: r for r in res}
    sp, bist = by.get("^GSPC"), by.get("XU100.IS")
    if bist and abs(bist["pct"]) >= 2 and (not sp or abs(bist["pct"]) > abs(sp["pct"])):
        return f"İstanbul birjasında BIST 100 indeksi {_pct(bist['pct'])} {_rise(bist['pct'])}"
    if sp and abs(sp["pct"]) >= 1:
        return f"ABŞ birjalarında {'yüksəliş' if sp['pct'] > 0 else 'düşüş'}: S&P 500 indeksi {_pct(sp['pct'])} {_rise(sp['pct'])}"
    moved = [r for r in res if r["pct"]]
    first = sp or (moved[0] if moved else res[0])
    if len(moved) >= 4 and len({r["pct"] > 0 for r in moved}) == 1:
        top = max(moved, key=lambda r: abs(r["pct"]))
        return f"Dünya birjalarında {'yüksəliş' if top['pct'] > 0 else 'düşüş'}: {top['name']} {_pct(top['pct'])} {_rise(top['pct'])}"
    other = [r for r in moved if r is not first and (r["pct"] > 0) != (first["pct"] > 0)]
    if first["pct"] and other:
        b = max(other, key=lambda r: abs(r["pct"]))
        return (f"Dünya birjaları: {first['name']} {_pct(first['pct'])} {_rise(first['pct'])}, "
                f"{b['name']} {_pct(b['pct'])} {_rise(b['pct'])}")
    if first["pct"]:
        return f"Dünya birjaları: {first['name']} indeksi {_pct(first['pct'])} {_rise(first['pct'])}"
    return f"Dünya birjaları: {first['name']} indeksi dəyişməyib"


def birja_item(quotes, imoex, now):
    """Təmiz funksiya. quotes: parse_spark; imoex: imoex_quote və ya None. Qaytarır (xəbər, səbəb)."""
    target = prev_weekday(now.date())
    key = f"birja-{target.isoformat()}"
    rows = dict(quotes or {})
    if imoex:
        rows["IMOEX"] = imoex
    res, later, live, closed = [], [], [], []
    for sym, name, city in INDICES:
        q = rows.get(sym)
        if not q:
            continue
        r = dict(q, name=name, city=city)
        if r["live"]:
            live.append(r)
        elif r["day"] == target:
            res.append(r)
        elif r["day"] > target:
            later.append(r)
        else:
            closed.append(name)  # o gün birja bağlı idi (bayram): köhnə bağlanış xəbər deyil
    if len(res) < BIRJA_MIN:
        why = f"{_date_text(target)} üçün {len(res)} indeksin bağlanışı var, ən azı {BIRJA_MIN} lazımdır"
        return _skip("birja", key, BIRJA_SLOT, "Dünya birjaları: bağlanış məlumatı azdır", why,
                     "Yahoo Finance", BIRJA_LINK), why
    us = [r for r in res if r["sym"] in US]
    rest = [r for r in res if r["sym"] not in US]
    if us:
        parts = [f"{r['name']}{' indeksi' if k == 0 else ''} {_closed(r)}" for k, r in enumerate(us)]
        lead = f"{ox.day_loc(target)} ABŞ birjalarında {_join(parts)} bağlanıb."
    else:
        r = rest.pop(0)
        lead = f"{ox.day_loc(target)} {r['name']} ({r['city']}) indeksi {_closed(r)} bağlanıb."
    body = [f"{r['name']} ({r['city']}): {_closed(r)} bağlanıb" for r in rest]
    body += [f"{r['name']} ({r['city']}): {ox.day_loc(r['day'])} {_closed(r)} bağlanıb" for r in later]
    body += [_live_line(r) for r in live]
    srcs = ["Yahoo Finance"] + (["Moskva Birjası"] if any(r["sym"] == "IMOEX" for r in res + later) else [])
    item = {"kind": "birja", "key": key, "topic": TOPIC, "slot": f"{BIRJA_SLOT:%H:%M}", "list": True,
            "title": _birja_title(res), "lead": lead, "body": body, "credit": _join(srcs), "link": BIRJA_LINK,
            "worth": True}
    if closed:
        item["closed"] = closed
    return _guard(item)


def birja(now, fetch, done=()):
    """Bu günün birja xəbəri: çərşənbə axşamı–şənbə, 09:00–09:40. Qaytarır (xəbər və ya None, səbəb)."""
    target = prev_weekday(now.date())
    key = f"birja-{target.isoformat()}"
    if key in done:
        return None, "bu xəbər bu gün artıq işlənib"
    if now.weekday() not in BIRJA_DAYS:
        return None, "dünya birjaları xəbəri çərşənbə axşamı–şənbə çıxır"
    if not _in_window(now, BIRJA_SLOT):
        return None, f"xəbərin vaxtı {_window_text(BIRJA_SLOT)} arasıdır"
    quotes, src = spark_fetch(fetch, now)
    if not quotes:
        why = f"Yahoo Finance alınmadı: {src}"
        return _skip("birja", key, BIRJA_SLOT, "Dünya birjaları: məlumat alınmadı", why, "Yahoo Finance", BIRJA_LINK), why
    imoex, _ = moex_fetch(fetch, target)
    return birja_item(quotes, imoex, now)


# --- 2. Kriptovalyuta bazarı -------------------------------------------------------------------------------

KRIPTO_SLOT = datetime.time(10, 0)
KRIPTO_MOVE = 2.0                          # iş günü bundan az dəyişmə xəbər deyil
KRIPTO_FRESH = datetime.timedelta(hours=2)
COINS = (("bitcoin", "bitkoin"), ("ethereum", "efir"), ("ripple", "XRP"), ("binancecoin", "BNB"), ("solana", "Solana"),
         ("dogecoin", "Dogecoin"), ("the-open-network", "Toncoin"))
CG_URL = ("https://api.coingecko.com/api/v3/simple/price?ids=" + ",".join(c for c, _ in COINS) +
          "&vs_currencies=usd,azn&include_24hr_change=true&include_last_updated_at=true")
CG_CREDIT, CG_LINK = "CoinGecko", "https://www.coingecko.com/"


def parse_coingecko(raw):
    """CoinGecko simple/price -> {id: {usd, azn, pct, at}}; zibil və natamam sətirlər düşür."""
    doc = _json(raw)
    out = {}
    if not isinstance(doc, dict):
        return out
    for cid, _ in COINS:
        row = doc.get(cid)
        if not isinstance(row, dict):
            continue
        usd, azn = _num(row.get("usd")), _num(row.get("azn"))
        pct, at = _num(row.get("usd_24h_change")), _num(row.get("last_updated_at"))
        if not usd or not azn or usd <= 0 or pct is None or at is None or abs(pct) >= 90:
            continue
        if not 1.6 <= azn / usd <= 1.8:  # manat dollara bağlıdır (1,70): başqa nisbət xətalı cavabdır
            continue
        try:
            when = datetime.datetime.fromtimestamp(at, UTC).astimezone(BAKU)
        except (OverflowError, OSError, ValueError):
            continue
        out[cid] = {"usd": usd, "azn": azn, "pct": round(pct, 2), "at": when}
    return out


def _price(v):
    """Qiymət böyüklüyünə görə: 74 713; 2 125,31; 86,72; 1,091; 0,0699."""
    dec = 0 if v >= 10000 else 2 if v >= 10 else 3 if v >= 1 else 4 if v >= 0.01 else 6
    return ox.az_num(v, dec)


def _cheap(pct):
    return "bahalaşıb" if pct > 0 else "ucuzlaşıb"


def _coin_line(name, c):
    head = f"{name}: {_price(c['usd'])} dollar ({_price(c['azn'])} manat)"
    if not c["pct"]:
        return head + ", son 24 saatda dəyişməyib"
    return head + f", son 24 saatda {_pct(c['pct'])} {_cheap(c['pct'])}"


def _kripto_title(btc, eth):
    b, e, usd = btc["pct"], eth["pct"], _price(btc["usd"])
    if abs(b) >= KRIPTO_MOVE and abs(e) >= KRIPTO_MOVE and (b > 0) == (e > 0):
        return f"Bitkoin {_pct(b)}, efir {_pct(e)} {_cheap(b)}: 1 bitkoin {usd} dollar"
    if abs(e) >= KRIPTO_MOVE and abs(e) > abs(b):
        tail = f"bitkoin {usd} dollara {'qalxıb' if b > 0 else 'enib'}" if b else f"bitkoin {usd} dollar"
        return f"Efir sutka ərzində {_pct(e)} {_cheap(e)}, {tail}"
    if b:
        return f"Bitkoin {usd} dollara {'qalxıb' if b > 0 else 'enib'}: sutka ərzində {_pct(b)} {_cheap(b)}"
    return f"Bitkoinin qiyməti sutka ərzində dəyişməyib: 1 bitkoin {usd} dollar"


def kripto_item(coins, now):
    """Təmiz funksiya. coins: parse_coingecko. Qaytarır (xəbər və ya None, səbəb)."""
    key = f"kripto-{now.date().isoformat()}"
    btc, eth = coins.get("bitcoin"), coins.get("ethereum")
    if not btc or not eth:
        return None, "CoinGecko cavabında bitkoin və ya efirin qiyməti yoxdur"
    t = btc["at"]
    if not now - KRIPTO_FRESH <= t <= now + datetime.timedelta(minutes=15):
        return None, f"CoinGecko-da bitkoinin qiyməti köhnədir ({_date_text(t)} {t:%H:%M})"
    # Efir də başlığa və «dəyərli» qərarına düşür: onun da vaxtı yoxlanır (əvvəl 3 günlük qiymət təzə kimi yazıla bilirdi)
    if not now - KRIPTO_FRESH <= eth["at"] <= now + datetime.timedelta(minutes=15):
        return None, f"CoinGecko-da efirin qiyməti köhnədir ({_date_text(eth['at'])} {eth['at']:%H:%M})"
    b_move = f"qiyməti {_pct(btc['pct'])} {'artıb' if btc['pct'] > 0 else 'azalıb'}" if btc["pct"] else "qiyməti dəyişməyib"
    e_move = f"{_pct(eth['pct'])} {_cheap(eth['pct'])}" if eth["pct"] else "qiyməti dəyişməyib"
    lead = (f"CoinGecko saytının məlumatına görə, {ox.day_loc(t)} Bakı vaxtı ilə {ox.time_loc(t)} 1 bitkoin "
            f"{_price(btc['usd'])} dollar ({_price(btc['azn'])} manat) olub, son 24 saatda {b_move}. "
            f"1 efir {_price(eth['usd'])} dollar ({_price(eth['azn'])} manat) olub, {e_move}.")
    body = [_coin_line(name, coins[cid]) for cid, name in COINS[2:] if cid in coins and now - KRIPTO_FRESH <= coins[cid]["at"] <= now + datetime.timedelta(minutes=15)]
    weekend = now.weekday() >= 5
    moved = abs(btc["pct"]) >= KRIPTO_MOVE or abs(eth["pct"]) >= KRIPTO_MOVE
    item = {"kind": "kripto", "key": key, "topic": TOPIC, "slot": f"{KRIPTO_SLOT:%H:%M}", "list": True,
            "title": _kripto_title(btc, eth), "lead": lead, "body": body, "credit": CG_CREDIT, "link": CG_LINK,
            "worth": weekend or moved}
    if not item["worth"]:
        item["why"] = (f"iş günüdür, bitkoin ({_pct(btc['pct'])}) və efir ({_pct(eth['pct'])}) son 24 saatda "
                       f"{ox.az_num(KRIPTO_MOVE, 0)}%-dən az dəyişib")
    return _guard(item)


def coingecko_fetch(fetch):
    """CoinGecko: 429 olsa 2 saniyədən sonra bir dəfə təkrar."""
    try:
        return _get(fetch, CG_URL)
    except urllib.error.HTTPError as e:
        if e.code != 429:
            raise
    _sleep(2)
    return _get(fetch, CG_URL)


def kripto(now, fetch, done=()):
    """Bu günün kripto xəbəri: hər gün 10:00–10:40. Qaytarır (xəbər və ya None, səbəb)."""
    key = f"kripto-{now.date().isoformat()}"
    if key in done:
        return None, "bu xəbər bu gün artıq işlənib"
    if not _in_window(now, KRIPTO_SLOT):
        return None, f"xəbərin vaxtı {_window_text(KRIPTO_SLOT)} arasıdır"
    try:
        item, why = kripto_item(parse_coingecko(coingecko_fetch(fetch)), now)
    except Exception as e:
        item, why = None, f"CoinGecko alınmadı: {_err(e)}"
    if not item:  # pəncərədə bir sorğu: açar qayıdır, o gün yenə sorğu getmir
        item = _skip("kripto", key, KRIPTO_SLOT, "Kriptovalyuta bazarı: məlumat alınmadı", why, CG_CREDIT, CG_LINK)
    return item, why


# --- 3. Banklarda dollar və avro --------------------------------------------------------------------------

BANK_SLOT = datetime.time(10, 30)
BANK_MIN = 2
RANGE = {"USD": (1.6, 1.8), "EUR": (1.5, 2.5)}  # bundan kənar məzənnə zibildir


def _pair(buy, sell, code):
    buy, sell = _num(buy), _num(sell)
    lo, hi = RANGE[code]
    if buy is None or sell is None or not lo <= buy < sell <= hi:
        return None
    return (buy, sell)


def parse_abb(raw):
    """ABB: Next.js-in react-query məlumatı (RSC cavabı və ya HTML-in içindəki qaçırılmış mətn): valyutanın CASH sətri,
    rateDate onun öz tarixidir. Səhifə ~0,5–0,9 MB-dır: yalnız USD və EUR seqmentləri oxunur."""
    s = _text(raw)
    if '\\"currency\\"' in s:
        s = s.replace('\\"', '"')
    out, day = {}, None
    for code in ("USD", "EUR"):
        i = s.find('{"currency":"' + code + '","rates":[')
        j = s.find("]}", i) if i >= 0 else -1
        if j < 0:
            continue
        try:
            doc = json.loads(s[i:j + 2])
        except ValueError:
            continue
        for r in doc.get("rates") or []:
            if not isinstance(r, dict) or r.get("type") != "CASH" or not isinstance(r.get("details"), dict):
                continue
            det = r["details"]
            buy = (det.get("buyRate") or {}).get("current") if isinstance(det.get("buyRate"), dict) else None
            sell = (det.get("saleRate") or {}).get("current") if isinstance(det.get("saleRate"), dict) else None
            try:
                rdate = datetime.date.fromisoformat(str(det.get("rateDate")))
            except ValueError:
                rdate = None
            if code == "USD":
                day = rdate
            if rdate and rdate == day:
                out[code] = _pair(buy, sell, code)
            break
    return {"date": day, "USD": out.get("USD"), "EUR": out.get("EUR")}


def parse_unibank(raw):
    """Unibank: «Nağd» sekmesinin cədvəli və «Yeniləndi 06.11.2026»."""
    page = _text(raw)
    tab = re.search(r'data-id="(exchange\d+)"[^>]*title="Nağd"', page)
    box = re.search(r"data-id='" + (tab.group(1) if tab else "exchange0") + r"'>(.*?)</table>", page, re.S)
    if not box:
        return None
    day = re.search(r"Yeniləndi\s*(\d\d\.\d\d\.\d{4})", box.group(1))
    rows = {}
    for code, buy, sell in re.findall(r"<tr>\s*<td>\s*([A-Z]{3})\s*</td>\s*<td>\s*([\d.]+).*?</td>\s*<td>\s*([\d.]+)",
                                      box.group(1), re.S):
        rows.setdefault(code, (_numtext(buy), _numtext(sell)))
    usd, eur = rows.get("USD") or (None, None), rows.get("EUR") or (None, None)
    return {"date": _dmy(day.group(1)) if day else None, "USD": _pair(usd[0], usd[1], "USD"), "EUR": _pair(eur[0], eur[1], "EUR")}


def _js_atom(tok):
    if tok in ("null", "void 0", "undefined", ""):
        return None
    if tok in ("true", "false"):
        return tok == "true"
    if re.fullmatch(r"-?\d+(?:\.\d+)?(?:[eE][-+]?\d+)?", tok):
        return float(tok)
    return None


def _js_list(src):
    """JavaScript arqument siyahısı (Nuxt-un sıxılmış payload-unun sonu) -> qiymətlər; eval yoxdur."""
    out, i, n = [], 0, len(src)
    while i < n:
        while i < n and src[i] in " \t\r\n":
            i += 1
        if i >= n:
            break
        if src[i] == '"':
            j = i + 1
            while j < n and src[j] != '"':
                j += 2 if src[j] == "\\" else 1
            try:
                out.append(json.loads(src[i:j + 1]))
            except ValueError:
                out.append(None)
            i = j + 1
        else:
            j, depth = i, 0
            while j < n and not (src[j] == "," and depth == 0):
                if src[j] in "[{(":
                    depth += 1
                elif src[j] in "]})":
                    depth -= 1
                j += 1
            out.append(_js_atom(src[i:j].strip()))
            i = j
        while i < n and src[i] in " \t\r\n":
            i += 1
        if i < n and src[i] == ",":
            i += 1
    return out


def _nuxt_vars(page, head):
    """window.__NUXT__=(function(a,b,...){...}(arqumentlər)): {ad: qiymət}. Uyğun gəlməsə {}."""
    end = page.find("</script>", head.end())
    script = page[head.end():end if end > 0 else len(page)]
    k = script.rfind("}(")
    if k < 0:
        return {}
    src = re.sub(r"\)\s*\)\s*;?\s*$", "", script[k + 2:])
    params = [p.strip() for p in head.group(1).split(",")]
    values = _js_list(src)
    return dict(zip(params, values)) if len(values) == len(params) else {}


def parse_xalq(raw):
    """Xalq Bank: Nuxt payload-undakı «exchange-rates» bloku (date: «6 Noyabr 2026», textarea.USD.cash_buy ...). Təkrarlanan
    qiymətləri Nuxt dəyişənə çıxarır (cash_sell:d): onlar funksiyanın arqumentlərindən oxunur."""
    page = _text(raw)
    head = re.search(r"window\.__NUXT__=\(function\(([^)]*)\)\{", page)
    i = page.find('type:"exchange-rates"')
    if i < 0:
        return None
    names = _nuxt_vars(page, head) if head else {}

    def value(tok):
        tok = (tok or "").strip()
        if tok.startswith('"'):
            try:
                return json.loads(tok)
            except ValueError:
                return None
        atom = _js_atom(tok)
        return atom if atom is not None or not re.fullmatch(r"[A-Za-z_$][\w$]*", tok) else names.get(tok)

    block = page[i:i + 3000]
    m = re.search(r'date:("(?:[^"\\]|\\.)*"|[A-Za-z_$][\w$]*)', block)
    when = value(m.group(1)) if m else None
    d = re.fullmatch(r"\s*(\d{1,2})\s+(\S+)\s+(\d{4})\s*", when) if isinstance(when, str) else None
    out = {"date": _month_date(*d.groups()) if d else None}
    for code in ("USD", "EUR"):
        box = re.search(code + r":\{([^{}]*)\}", block)
        fields = dict(re.findall(r"(\w+):([^,{}]+)", box.group(1))) if box else {}
        out[code] = _pair(value(fields.get("cash_buy")), value(fields.get("cash_sell")), code)
    return out


def parse_access(raw):
    """AccessBank: data-id="cash" cədvəli («1 USD») və ondan sonrakı «Yenilənib: <span>06.11.2026</span>»."""
    page = _text(raw)
    box = re.search(r'<table[^>]*data-id="cash"[^>]*>(.*?)</table>', page, re.S)
    if not box:
        return None
    day = re.search(r"Yenilənib:\s*(?:<[^>]+>\s*)*(\d\d\.\d\d\.\d{4})", page[box.end():box.end() + 4000])
    rows = {}
    for code, buy, sell in re.findall(r"<td>\s*1\s+([A-Z]{3})\s*</td>\s*<td[^>]*>\s*([\d.]+)\s*</td>\s*<td[^>]*>\s*([\d.]+)\s*</td>",
                                      box.group(1), re.S):
        rows.setdefault(code, (_numtext(buy), _numtext(sell)))
    usd, eur = rows.get("USD") or (None, None), rows.get("EUR") or (None, None)
    return {"date": _dmy(day.group(1)) if day else None, "USD": _pair(usd[0], usd[1], "USD"), "EUR": _pair(eur[0], eur[1], "EUR")}


# (ad, ünvan, başlıqlar, oxuyan). Yalnız səhifəsi məzənnənin öz tarixini göstərən banklar.
# ABB-yə RSC sorğusu: eyni məlumat HTML-siz gəlir (478 KB, HTML səhifə 745 KB, ana səhifə 859 KB; 2026-11-10).
BANKS = (
    ("ABB", "https://abb-bank.az/ferdi/valyuta-mezenneleri", {"RSC": "1"}, parse_abb),
    ("Unibank", "https://unibank.az/az", None, parse_unibank),
    ("Xalq Bank", "https://www.xalqbank.az/az", None, parse_xalq),
    ("AccessBank", "https://www.accessbank.az/az/", None, parse_access),
)
# Kontekstdəki yeddi bankdan çıxarılanlar (2026-11-10 yoxlanıb): məzənnənin qoyulduğu günü göstərmirlər.
UNDATED = (
    ("Yelo Bank", "https://www.yelo.az/az/exchange-rates/", "saytda məzənnənin tarixi yoxdur"),
    ("Expressbank", "https://www.expressbank.az/az",
     "tarix hər açılışda bu günündür (keş damğası, 30 dəqiqədən bir yenilənir), məzənnənin qoyulduğu günü göstərmir"),
    ("Bank Respublika", "https://www.bankrespublika.az/get_rates", "cavabda tarix yoxdur"),
)


def bank_fetch(fetch, banks=BANKS):
    """[(ad, ünvan, məlumat və ya None, xəta, bayt)]: hər bank bir sorğu, biri alınmasa qalanları davam edir."""
    out = []
    for name, url, headers, parse in banks:
        try:
            raw = _get(fetch, url, headers)
        except Exception as e:
            out.append((name, url, None, f"sayt açılmadı ({_err(e)})", 0))
            continue
        try:
            data = parse(raw)
        except Exception as e:
            data = None
        out.append((name, url, data, "" if data else "məzənnə oxunmadı", len(raw or b"")))
    return out


def _span(lo, hi):
    return ox.az_num(lo, 4) if lo == hi else f"{ox.az_num(lo, 4)}–{ox.az_num(hi, 4)}"


def _ends(rows, k):
    """rows: [(bank, (alış, satış))], k: 0 alış, 1 satış -> (ən aşağı, onun bankları, ən yuxarı, onun bankları)."""
    vals = [round(p[k], 4) for _, p in rows]
    lo, hi = min(vals), max(vals)
    return (lo, [n for n, p in rows if round(p[k], 4) == lo], hi, [n for n, p in rows if round(p[k], 4) == hi])


def _named(names, value):
    """«ABB (1,6970 manat)»."""
    return f"{_join(names)} ({ox.az_num(value, 4)} manat)"


def _ends_text(rows, what):
    """Aralığın uclarındakı banklar adı ilə: «Dolları ən baha ABB (1,6970 manat), ən ucuz Xalq Bank (1,6900 manat) alır;
    ən ucuz Unibank (1,7005 manat), ən baha AccessBank (1,7025 manat) satır.»"""
    b_lo, b_lo_n, b_hi, b_hi_n = _ends(rows, 0)
    s_lo, s_lo_n, s_hi, s_hi_n = _ends(rows, 1)
    if b_hi == b_lo and s_hi == s_lo:
        return f"{what} bankların hamısı {ox.az_num(b_lo, 4)} manata alır, {ox.az_num(s_lo, 4)} manata satır."
    buy = (f"ən baha {_named(b_hi_n, b_hi)}, ən ucuz {_named(b_lo_n, b_lo)} alır" if b_hi > b_lo
           else f"bankların hamısı {ox.az_num(b_lo, 4)} manata alır")
    sell = (f"ən ucuz {_named(s_lo_n, s_lo)}, ən baha {_named(s_hi_n, s_hi)} satır" if s_hi > s_lo
            else f"bankların hamısı {ox.az_num(s_lo, 4)} manata satır")
    return f"{what} {buy}; {sell}."


def bank_item(results, day):
    """Təmiz funksiya. results: bank_fetch; day: məzənnənin olmalı olduğu gün. Qaytarır (xəbər, səbəb)."""
    key = f"bank-mezenne-{day.isoformat()}"
    fresh, notes = [], []
    for name, url, data, err, _ in results:
        when = data.get("date") if data else None
        if not data:
            notes.append(f"{name}: {err or 'məzənnə oxunmadı'}")
        elif when != day:
            notes.append(f"{name}: məzənnə {_date_text(when)} tarixlidir" if when else f"{name}: məzənnənin tarixi oxunmadı")
        elif not data.get("USD"):
            notes.append(f"{name}: dolların nağd məzənnəsi oxunmadı")
        else:
            fresh.append((name, url, data))
    if len(fresh) < BANK_MIN:
        why = (f"{_date_text(day)} tarixli nağd məzənnə {len(fresh)} bankda var, ən azı {BANK_MIN} lazımdır"
               + (" (" + "; ".join(notes) + ")" if notes else ""))
        return _skip("bank-mezenne", key, BANK_SLOT, "Banklarda nağd məzənnə: bu günün məlumatı azdır", why,
                     _join(b[0] for b in BANKS), BANKS[0][1]), why
    usd = [(n, d["USD"]) for n, _, d in fresh]
    eur = [(n, d["EUR"]) for n, _, d in fresh if d.get("EUR")]
    b_lo, _, b_hi, _ = _ends(usd, 0)
    s_lo, s_lo_names, s_hi, _ = _ends(usd, 1)
    names = [n for n, _, _ in fresh]
    lead = (f"{COUNT.get(len(names), len(names))} bankın ({_join(names)}) saytlarında {ox.day_text(day)} üçün göstərilən "
            f"nağd məzənnələrə görə ABŞ dolları {_span(b_lo, b_hi)} manata alınır, {_span(s_lo, s_hi)} manata satılır. ")
    lead += _ends_text(usd, "Dolları")
    if len(eur) >= BANK_MIN:
        eb_lo, _, eb_hi, _ = _ends(eur, 0)
        es_lo, _, es_hi, _ = _ends(eur, 1)
        lead += f" Avro {_span(eb_lo, eb_hi)} manata alınır, {_span(es_lo, es_hi)} manata satılır. " + _ends_text(eur, "Avronu")
    body = []
    for name, _, d in fresh:
        line = f"{name}: dolları {ox.az_num(d['USD'][0], 4)} manata alır, {ox.az_num(d['USD'][1], 4)} manata satır"
        if d.get("EUR"):
            line += f"; avronu {ox.az_num(d['EUR'][0], 4)} manata alır, {ox.az_num(d['EUR'][1], 4)} manata satır"
        body.append(line)
    sell = _span(s_lo, s_hi)
    titles = [f"Banklarda dollar {sell} manata satılır",
              f"Banklarda nağd dollar {_span(b_lo, b_hi)} manata alınır, {sell} manata satılır"]
    if s_hi > s_lo:
        titles.append(f"Dolları ən ucuz {_join(s_lo_names)} satır: {ox.az_num(s_lo, 4)} manat")
    titles = [t for t in titles if len(t) <= 110] or titles[:1]
    item = {"kind": "bank-mezenne", "key": key, "topic": TOPIC, "slot": f"{BANK_SLOT:%H:%M}", "list": True,
            "title": titles[day.toordinal() % len(titles)], "lead": lead, "body": body, "credit": _join(names),
            "link": fresh[0][1], "worth": True}
    if notes:
        item["left_out"] = notes
    return _guard(item)


def banks(now, fetch, done=()):
    """Bu günün bank məzənnəsi xəbəri: iş günü, 10:30–11:10. Qaytarır (xəbər və ya None, səbəb)."""
    if f"bank-mezenne-{now.date().isoformat()}" in done:
        return None, "bu xəbər bu gün artıq işlənib"
    if not is_working_day(now.date()):
        return None, f"{_date_text(now.date())} iş günü deyil: banklar məzənnəni yeniləmir"
    if not _in_window(now, BANK_SLOT):
        return None, f"xəbərin vaxtı {_window_text(BANK_SLOT)} arasıdır"
    return bank_item(bank_fetch(fetch), now.date())


# --- 4. BFB-də dövlət qiymətli kağızları hərracı ------------------------------------------------------------

BFB_HOME = "https://www.bfb.az/"
BFB_DAYS = (1, 2, 3)  # çərşənbə axşamı (Maliyyə Nazirliyi), çərşənbə və cümə axşamı (Mərkəzi Bank)
BFB_SLOTS = ((datetime.time(13, 30), datetime.timedelta(minutes=10)), (datetime.time(18, 30), WINDOW))
BFB_CREDIT = "Bakı Fond Birjası"
ISSUERS = ("ARMB", "MN")
_BFB_LINK = re.compile(r'href="(https://www\.bfb\.az/xeber/[a-z0-9-]+)"')
_ISIN = re.compile(r"[A-Z]{2}[A-Z0-9]{10}")
_PRICE_YIELD = re.compile(r"([\d,]+(?:\.\d+)?)\s*\(\s*(\d+(?:\.\d+)?)\s*%\s*\)")


def parse_bfb_home(raw):
    """bfb.az ana səhifəsinin yerləşdirmələr cədvəli (Emitentin adı | Alət | İSİN | Həcm | Gəlirlilik | Tədavül müddəti |
    Yerləşdirmə Tarixi) -> [{issuer, isin, offered, day, link}]. «Kupon %» olan cədvəl gələcək yerləşdirmələrdir, oxunmur."""
    page = _text(raw)
    for part in page.split("<table")[1:]:
        table = part.split("</table>")[0]
        head = _clean(" ".join(re.findall(r"<th[^>]*>(.*?)</th>", table, re.S)))
        if "Emitentin adı" not in head or "Gəlirlilik" not in head or "Yerləşdirmə" not in head:
            continue
        out = []
        for tr in re.findall(r"<tr[^>]*>(.*?)</tr>", table, re.S):
            cells = re.findall(r"<td[^>]*>(.*?)</td>", tr, re.S)
            if len(cells) < 7:
                continue
            link = _BFB_LINK.search(cells[0])
            day = _dmy(_clean(cells[6]))
            if link and day:
                out.append({"issuer": _clean(cells[0]), "isin": _clean(cells[2]), "offered": _numtext(_clean(cells[3]).replace("AZN", "")),
                            "term": _clean(cells[5]), "day": day, "link": link.group(1)})
        return out
    return []


def state_rows(rows, day):
    """Günün AMB (ARMB) və Maliyyə Nazirliyi (MN) yerləşdirmələri, İSİN-ə görə təkrarsız."""
    out, seen = [], set()
    for r in rows:
        if r["issuer"] in ISSUERS and r["day"] == day and r["isin"] not in seen:
            seen.add(r["isin"])
            out.append(r)
    return out


def _field(fields, *prefixes):
    for k, v in fields.items():
        if any(k.startswith(p) for p in prefixes):
            return v
    return ""


def parse_bfb_detail(raw):
    """Hərracın səhifəsi (text_editor-dakı açar/qiymət cədvəli) -> məlumat və ya None."""
    page = _text(raw)
    i = page.find('class="text_editor"')
    if i < 0:
        return None
    j = page.find("</figure>", i)
    box = page[i:j if j > 0 else len(page)]
    fields = {}
    for tr in re.findall(r"<tr[^>]*>(.*?)</tr>", box, re.S):
        cells = [_clean(c) for c in re.findall(r"<td[^>]*>(.*?)</td>", tr, re.S)]
        if len(cells) >= 2 and cells[0]:
            fields[" ".join(ox._low(cells[0]).replace("–", " ").split())] = cells[1]
    intro = re.search(r"(\d{1,2})\s+(\w+)\s+(\d{4})-c[ıi] il tarixində", _clean(box))
    term = re.match(r"(\d+)\s*gün", _field(fields, "notun müddəti", "istiqrazların tədavül müddəti", "tədavül müddəti"))
    cut = _PRICE_YIELD.search(_field(fields, "kəsmə qiyməti"))
    wavg = _PRICE_YIELD.search(_field(fields, "ortaçəkili qiymət", "orta çəkili qiymət"))
    coupon = re.match(r"(\d+(?:\.\d+)?)\s*%", _field(fields, "faiz dərəcəsi"))
    count = lambda *p: int(_field(fields, *p)) if _field(fields, *p).isdigit() else None
    out = {
        "day": _month_date(*intro.groups()) if intro else None,
        "isin": _field(fields, "dövlət qeydiyyat nömrəsi"),
        "term": int(term.group(1)) if term else None,
        "offered": _numtext(_field(fields, "emissiya həcmi", "buraxılış həcmi").replace("manat", "")),
        "placed": _numtext(_field(fields, "reallaşdırılmış həcm").replace("manat", "")),
        "bids": _numtext(_field(fields, "sifarişlərin ümumi həcmi").replace("manat", "")),
        "investors": count("investor sayı"),
        "orders": count("sifariş sayı", "sifarişlərin sayı"),
        "cut": (_numtext(cut.group(1)), float(cut.group(2))) if cut else None,
        "wavg": (_numtext(wavg.group(1)), float(wavg.group(2))) if wavg else None,
        "coupon": float(coupon.group(1)) if coupon else None,
        "maturity": _dmy(_field(fields, "notun ödəniş tarixi", "ödəniş tarixi", "ödəmə tarixi")),
        "underwriter": _field(fields, "anderrayter"),
    }
    if not _ISIN.fullmatch(out["isin"]) or not out["term"] or out["placed"] is None or not out["wavg"] or not out["wavg"][0]:
        return None
    return out


def bfb_details(fetch, rows):
    """Hər yerləşdirmənin səhifəsi (1 sorğu). Cədvəldəki İSİN və gün səhifədəkinə uyğun gəlməlidir.
    Qaytarır ([(sətir, məlumat)], qeydlər)."""
    out, notes = [], []
    for r in rows:
        try:
            d = parse_bfb_detail(_get(fetch, r["link"]))
        except Exception as e:
            notes.append(f"{r['isin']}: səhifə açılmadı ({_err(e)})")
            continue
        if not d:
            notes.append(f"{r['isin']}: səhifədə hərracın nəticəsi oxunmadı")
        elif d["isin"] != r["isin"] or (d["day"] and d["day"] != r["day"]):
            notes.append(f"{r['isin']}: səhifə başqa hərracındır ({d['isin']})")
        else:
            out.append((r, d))
    return out, notes


def _az0(v):
    return ox.az_num(v, 0)


def _mln(v):
    """Başlıq üçün məbləğ: «12,5 milyon», «300 milyon»; 50 min manatdan az məbləğ tam rəqəmlə («30 000») — əvvəl «0 milyon
    manatlıq» çıxırdı."""
    s = ox.az_num(v / 1e6, 1)
    if s in ("0,0", "0"):
        return _az0(v)
    return (s[:-2] if s.endswith(",0") else s) + " milyon"


def _trim(v):
    s = ox.az_num(v, 2)
    return s.rstrip("0").rstrip(",")


def _amb_line(d):
    parts = [f"{_az0(d['placed'])} manat yerləşdirilib"]
    if d["bids"] is not None and d["investors"]:
        parts.append(f"{d['investors']} investorun sifarişlərinin ümumi həcmi {_az0(d['bids'])} manat olub")
    rates = f"orta çəkili gəlirlilik {_pct(d['wavg'][1])}"
    if d["cut"]:
        rates += f", kəsmə gəlirliliyi {_pct(d['cut'][1])}"
    parts.append(rates)
    if d["maturity"]:
        parts.append(f"ödəniş tarixi {_date_text(d['maturity'])}")
    return f"{d['term']} günlük notlar ({d['isin']}): " + "; ".join(parts)


def _mn_line(d):
    parts = []
    if d["offered"]:
        parts.append(f"buraxılış həcmi {_az0(d['offered'])} manat, yerləşdirilib {_az0(d['placed'])} manat")
    else:
        parts.append(f"{_az0(d['placed'])} manat yerləşdirilib")
    if d["bids"] is not None and d["investors"]:
        parts.append(f"{d['investors']} investorun sifarişlərinin ümumi həcmi {_az0(d['bids'])} manat olub")
    rates = f"orta çəkili gəlirlilik {_pct(d['wavg'][1])}"
    if d["cut"]:
        rates += f", kəsmə gəlirliliyi {_pct(d['cut'][1])}"
    parts.append(rates)
    if d["coupon"] is not None:
        parts.append(f"illik faiz dərəcəsi {_trim(d['coupon'])}%")
    if d["maturity"]:
        parts.append(f"ödəmə tarixi {_date_text(d['maturity'])}")
    return f"{d['term']} günlük istiqrazlar ({d['isin']}): " + "; ".join(parts)


def _amb_title(amb):
    placed = sum(d["placed"] for d in amb)
    if not placed:
        return f"Mərkəzi Bankın {_join(str(d['term']) for d in amb)} günlük notlarının hərracında notlar yerləşdirilməyib"
    if len(amb) == 1:
        d = amb[0]
        return (f"Mərkəzi Bank {_mln(d['placed'])} manatlıq {d['term']} günlük notları {_pct(d['wavg'][1])} "
                f"orta gəlirliliklə yerləşdirib")
    title = (f"Mərkəzi Bank {_mln(placed)} manatlıq notlar yerləşdirib: "
             + ", ".join(f"{d['term']} günlük {_pct(d['wavg'][1])}" for d in amb) + " orta gəlirliliklə")
    return title if len(title) <= 110 else f"Mərkəzi Bank {_mln(placed)} manatlıq notlar yerləşdirib"


def _mn_title(d):
    if not d["placed"]:
        return f"Maliyyə Nazirliyinin {d['term']} günlük istiqrazlarının hərracında istiqraz yerləşdirilməyib"
    if d["offered"] and d["placed"] < d["offered"]:
        return (f"Maliyyə Nazirliyi {d['term']} günlük istiqrazların {_mln(d['placed'])} manatlığını "
                f"{_pct(d['wavg'][1])} orta gəlirliliklə yerləşdirib")
    return (f"Maliyyə Nazirliyi {_mln(d['placed'])} manatlıq {d['term']} günlük istiqrazları {_pct(d['wavg'][1])} "
            f"orta gəlirliliklə yerləşdirib")


def _amb_lead(day, amb):
    terms = _join(str(d["term"]) for d in amb)
    lead = (f"{_year_loc(day)} Bakı Fond Birjasında Azərbaycan Mərkəzi Bankının (AMB) {terms} günlük notlarının "
            f"yerləşdirilməsi üzrə {'hərraclar' if len(amb) > 1 else 'hərrac'} keçirilib.")
    offered = [d["offered"] for d in amb]
    placed = sum(d["placed"] for d in amb)
    if all(offered):
        total = sum(offered)
        if placed == total:
            lead += f" Hərraca çıxarılan {_az0(total)} manatlıq notların hamısı yerləşdirilib."
        else:
            lead += f" Hərraca çıxarılan {_az0(total)} manatlıq notlardan {_az0(placed)} manatlığı yerləşdirilib."
    return lead


def _mn_lead(day, d):
    lead = (f"{_year_loc(day)} Bakı Fond Birjasında Maliyyə Nazirliyinin {d['term']} günlük dövlət istiqrazlarının "
            f"yerləşdirilməsi üzrə hərrac keçirilib.")
    if d["offered"]:
        lead += f" {_az0(d['offered'])} manatlıq buraxılışdan {_az0(d['placed'])} manatlıq istiqraz yerləşdirilib"
    else:
        lead += f" {_az0(d['placed'])} manatlıq istiqraz yerləşdirilib"
    return lead + f", orta çəkili gəlirlilik {_pct(d['wavg'][1])} olub."


def bfb_item(day, auctions, slot=BFB_SLOTS[-1][0]):
    """Təmiz funksiya. auctions: bfb_details-in [(sətir, məlumat)]-ı; bir günün hamısı bir xəbərdir.
    Qaytarır (xəbər və ya None, səbəb)."""
    amb = sorted((d for r, d in auctions if r["issuer"] == "ARMB"), key=lambda d: d["term"])
    mn = sorted((d for r, d in auctions if r["issuer"] == "MN"), key=lambda d: d["term"])
    if not amb and not mn:
        return None, f"{_date_text(day)} BFB-də dövlət qiymətli kağızlarının hərrac nəticəsi oxunmadı"
    lead, body = [], []
    for d in mn:
        lead.append(_mn_lead(day, d))
        body.append(_mn_line(d))
    if amb:
        lead.append(_amb_lead(day, amb))
        body += [_amb_line(d) for d in amb]
    item = {"kind": "bfb-herrac", "key": f"bfb-herrac-{day.isoformat()}", "topic": TOPIC, "slot": f"{slot:%H:%M}",
            "list": True, "title": _mn_title(mn[0]) if mn else _amb_title(amb), "lead": " ".join(lead), "body": body,
            "credit": BFB_CREDIT, "link": auctions[0][0]["link"], "worth": True}
    return _guard(item)


def bfb(now, fetch, done=()):
    """Bu günün BFB xəbəri: çərşənbə axşamı–cümə axşamı iş günləri, 13:30–13:40 və 18:30–19:10.
    Qaytarır (xəbər və ya None, səbəb)."""
    key = f"bfb-herrac-{now.date().isoformat()}"
    if key in done:
        return None, "bu xəbər bu gün artıq işlənib"
    if now.weekday() not in BFB_DAYS or not is_working_day(now.date()):
        return None, "dövlət qiymətli kağızlarının hərracı çərşənbə axşamı–cümə axşamı iş günləri keçirilir"
    slot = next((s for s, length in BFB_SLOTS if _in_window(now, s, length)), None)
    if not slot:
        return None, "xəbərin vaxtı " + " və ".join(_window_text(s, length) for s, length in BFB_SLOTS) + " arasıdır"
    last = slot == BFB_SLOTS[-1][0]
    try:
        rows = state_rows(parse_bfb_home(_get(fetch, BFB_HOME)), now.date())
    except Exception as e:
        why = f"bfb.az alınmadı: {_err(e)}"
        if not last:
            return None, why + " (axşam yenə yoxlanacaq)"
        return _skip("bfb-herrac", key, slot, "BFB: məlumat alınmadı", why, BFB_CREDIT, BFB_HOME), why
    if not rows:
        why = f"bfb.az-da {_date_text(now.date())} tarixli dövlət qiymətli kağızı yerləşdirməsi yoxdur"
        if not last:
            return None, why + " (axşam yenə yoxlanacaq)"
        return _skip("bfb-herrac", key, slot, "BFB-də bu gün dövlət qiymətli kağızlarının hərrac nəticəsi yoxdur", why,
                     BFB_CREDIT, BFB_HOME), why
    auctions, notes = bfb_details(fetch, rows)
    if notes and not last:
        return None, "hərracın səhifəsi oxunmadı: " + "; ".join(notes) + " (axşam yenə yoxlanacaq)"
    if not auctions:
        why = "hərracın səhifəsi oxunmadı: " + "; ".join(notes)
        return _skip("bfb-herrac", key, slot, "BFB-də hərracın nəticəsi oxunmadı", why, BFB_CREDIT, BFB_HOME), why
    return bfb_item(now.date(), auctions, slot)


# --- Canlı və sınaq ------------------------------------------------------------------------------------------

def _default_fetch():
    return ox._u().fetch


def _lazy(fetch):
    """Standart sorğu funksiyası yalnız sorğu lazım olanda yüklənir (updater)."""
    box = {}

    def get(url, timeout=TIMEOUT, headers=None):
        if "f" not in box:
            box["f"] = fetch or _default_fetch()
        return box["f"](url, timeout=timeout, headers=headers)
    return get


BUILDERS = (birja, kripto, banks, bfb)


def items(root, now, fetch=None, done=None):
    """`now` anında (Bakı) canlının işləyəcəyi maliyyə xəbərləri. worth False olan nəticə «why» ilə qayıdır, dərc
    olunmur, amma açarı `done`-a yazılmalıdır (o gün həmin xəbər üçün yenə sorğu getməsin). Heç vaxt xəta atmır."""
    now = _baku(now)
    done = set(done or ())
    get = _lazy(fetch)
    out = []
    for build in BUILDERS:
        try:
            item, _ = build(now, get, done)
        except Exception:
            item = None
        if item:
            out.append(item)
    return out


def _memo(fetch):
    """Sınaqda eyni ünvana ikinci sorğu getmir; neçə sorğu getdiyi hostlara görə sayılır."""
    seen, hosts = {}, {}

    def get(url, timeout=TIMEOUT, headers=None):
        key = (url, json.dumps(headers, sort_keys=True) if headers else "")
        if key not in seen:
            host = urllib.parse.urlsplit(url).netloc
            if host in hosts and PAUSE:
                _sleep(PAUSE)  # eyni hosta sorğular arasında 1 saniyə
            hosts[host] = hosts.get(host, 0) + 1
            try:
                seen[key] = (fetch(url, timeout=timeout, headers=headers), None)
            except Exception as e:
                seen[key] = (None, e)
        raw, err = seen[key]
        if err is not None:
            raise err
        return raw
    get.hosts = hosts
    return get


def _verdict(item):
    return "✅ Dərc olunardı" if item.get("worth") else f"⏭ Dərc olunmazdı: {item.get('why') or 'dəyəri azdır'}"


def _shown(item, why=""):
    if item and item.get("worth"):
        return ox.render(item) + [_verdict(item), ""]
    if item and item.get("body"):
        return ox.render(item) + [_verdict(item), ""]
    return [f"⏭ Dərc olunmazdı: {(item or {}).get('why') or why}", ""]


def _today(now, label, item, why):
    head = f"**Bu gün ({_date_text(now.date())}, {now:%H:%M}):**"
    if item:
        return [head, ""] + _shown(item, why)
    return [f"{head} ⏭ Dərc olunmazdı: {why}", ""]


def _sinaq_birja(now, fetch):
    item, why = birja(now, fetch, set())
    md = _today(now, "birja", item, why)
    if item:
        return md
    quotes, src = spark_fetch(fetch, now)
    if not quotes:
        return md + [f"> Yahoo Finance alınmadı: {src}", ""]
    target = prev_weekday(now.date())
    imoex, note = moex_fetch(fetch, target)
    md += [f"**Sınaq anındakı məlumatla** ({src}; IMOEX: {note or 'Moskva Birjası, ' + _date_text(imoex['day'])}). "
           f"Canlıda xəbər çərşənbə axşamı–şənbə {_window_text(BIRJA_SLOT)} arasında çıxır, {_date_text(target)} "
           f"seanslarını verir.", ""]
    item, why = birja_item(quotes, imoex, now)
    if item and item.get("closed"):
        md += [f"Bağlı olan birjalar (yazılmır): {', '.join(item['closed'])}.", ""]
    return md + _shown(item, why)


def _sinaq_kripto(now, fetch):
    item, why = kripto(now, fetch, set())
    md = _today(now, "kripto", item, why)
    if item:
        return md
    try:
        coins = parse_coingecko(coingecko_fetch(fetch))
    except Exception as e:
        return md + [f"> CoinGecko alınmadı: {_err(e)}", ""]
    if not coins:
        return md + ["> CoinGecko cavabı oxunmadı.", ""]
    at = coins["bitcoin"]["at"] if "bitcoin" in coins else now
    md += [f"**Sınaq anındakı məlumatla** (CoinGecko, {_date_text(at)} {at:%H:%M}). Canlıda xəbər hər gün "
           f"{_window_text(KRIPTO_SLOT)} arasında çıxır; iş günü yalnız bitkoin və ya efir 2% və daha çox dəyişibsə.", ""]
    item, why = kripto_item(coins, now)
    return md + _shown(item, why)


def _bank_status(results):
    md = ["**Bankların saytları** (bu sorğu GitHub-dan gedir):", ""]
    for name, url, data, err, size in results:
        if not size and err:
            md.append(f"- {name}: {err}")
            continue
        line = f"- {name}: sayt açıldı ({size // 1024} KB)"
        if not data:
            md.append(f"{line}, {err}")
            continue
        when = data.get("date")
        rates = []
        for code, label in (("USD", "dollar"), ("EUR", "avro")):
            if data.get(code):
                rates.append(f"{label} {ox.az_num(data[code][0], 4)} / {ox.az_num(data[code][1], 4)}")
        md.append(f"{line}, məzənnə {_date_text(when) if when else 'tarixsiz'}: " + (", ".join(rates) or "oxunmadı"))
    return md


def _sinaq_banks(now, fetch):
    item, why = banks(now, fetch, set())
    md = _today(now, "banklar", item, why)
    results = bank_fetch(fetch)
    md += _bank_status(results)
    for name, url, reason in UNDATED:
        try:
            size = len(_get(fetch, url) or b"")
            md.append(f"- {name}: sayt açıldı ({size // 1024} KB), siyahıya salınmır: {reason}")
        except Exception as e:
            md.append(f"- {name}: sayt açılmadı ({_err(e)}); onsuz da siyahıya salınmır: {reason}")
    md.append("")
    dates = sorted({d["date"] for _, _, d, _, _ in results if d and d.get("date") and d["date"] <= now.date()})
    if item and item.get("worth"):
        return md
    if not dates:
        return md + ["> Bankların heç birində tarixli məzənnə oxunmadı.", ""]
    day = dates[-1]
    md += [f"**Son real hal: {_date_text(day)}** (bankların saytındakı son məzənnələr), xəbər həmin gün "
           f"{ox.time_loc(BANK_SLOT)} çıxardı.", ""]
    item, why = bank_item(results, day)
    return md + _shown(item, why)


def _sinaq_bfb(now, fetch):
    item, why = bfb(now, fetch, set())
    md = _today(now, "bfb", item, why)
    try:
        rows = parse_bfb_home(_get(fetch, BFB_HOME))
    except Exception as e:
        return md + [f"> bfb.az alınmadı: {_err(e)}", ""]
    state = [r for r in rows if r["issuer"] in ISSUERS and r["day"] < now.date()]
    if not state:
        return md + ["> bfb.az-ın cədvəlində dövlət qiymətli kağızı yerləşdirməsi oxunmadı.", ""]
    days = [state[0]["day"]]
    mn = next((r["day"] for r in state if r["issuer"] == "MN"), None)
    if mn and mn not in days:
        days.append(mn)
    for day in days:
        auctions, notes = bfb_details(fetch, state_rows(state, day))
        md += [f"**Son real hal: {_date_text(day)}**, xəbər həmin gün {ox.time_loc(BFB_SLOTS[0][0])} və ya "
               f"{ox.time_loc(BFB_SLOTS[1][0])} çıxardı.", ""]
        if notes:
            md += ["> " + "; ".join(notes), ""]
        item, why = bfb_item(day, auctions) if auctions else (None, "hərracın səhifəsi oxunmadı")
        md += _shown(item, why)
    return md


PARTS = (
    ("Dünya birjaları (çərşənbə axşamı–şənbə, 09:00)", _sinaq_birja),
    ("Kriptovalyuta bazarı (hər gün, 10:00)", _sinaq_kripto),
    ("Banklarda dollar və avro (iş günləri, 10:30)", _sinaq_banks),
    ("BFB-də dövlət qiymətli kağızları hərracı (çərşənbə axşamı–cümə axşamı, 13:30 və 18:30)", _sinaq_bfb),
)


def sinaq(root, now=None, fetch=None):
    """Nümunələr (Markdown): hər xəbərin bu günkü qərarı və son real hal. Sayta və repoya heç nə yazmır. Xəta atmır."""
    now = _baku(now or datetime.datetime.now(BAKU))
    get = _memo(_lazy(fetch))
    md = [f"Bakı vaxtı ilə {now:%d.%m.%Y %H:%M}. Sayta heç nə yazılmır.", ""]
    for title, part in PARTS:
        md += [f"## {title}", ""]
        try:
            md += part(now, get)
        except Exception as e:
            md += [f"> Sınaq xətası: {type(e).__name__}: {e}"[:300], ""]
    total = sum(get.hosts.values())
    md += [f"Sınaqda {total} sorğu getdi: " + ", ".join(f"{h} {n}" for h, n in get.hosts.items()) + ".", ""]
    return md


def _now_arg(s):
    return _baku(datetime.datetime.fromisoformat(s)) if s else None


def main(argv):
    if "--sinaq" not in argv:
        print(__doc__)
        return 0
    root = pathlib.Path(ox._arg(argv, "--root") or pathlib.Path(__file__).resolve().parent)
    sys.stdout.write("\n".join(sinaq(root, _now_arg(ox._arg(argv, "--now")))) + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
