"""8ulduz-un öz xəbərləri, faza 1: bazar şablonları, süni intellektsiz (sahib, 2026-11-10: «Bəli, başla»).

1. AMB bank metalları: iş günləri saat 09:40-da, AMB bülleteni çıxandan sonra (09:06–09:20).
   - Mərkəzi Bankın gündəlik bülletenindəki «Bank metalları» bölməsi: qızıl, gümüş, platin və palladium, manatla,
     «1 t.u.» (troya unsiyası) üçün, əvvəlki bülletenlə müqayisədə.
   - Dünya qiyməti data/markets.json-dan: qızıl və gümüş (gold-api.com), bitkoin (Yahoo Finance), dəyişməsi ilə.
     Qızıl və gümüşün markets.json-dakı dəyişməsi yazılmır (spot qiymət fyuçersin bağlanışı ilə müqayisə olunub):
     dəyişmə öz bağlanış nüsxəmizə görə hesablanır, nüsxə yoxdursa yalnız qiymət yazılır.
   - Bu gün yeni bülleten yoxdursa (bayram, həftə sonu) xəbər yoxdur.
   - Sorğu: gündə 2 (bu günün və əvvəlki bülleten). Ünvanlar oz_xeber.amb_latest-inkilərdir: canlıda AMB məzənnə
     xəbəri ilə eyni sorğulardır. Valyuta siyahısı burada yazılmır, o, AMB məzənnə xəbərindədir (oz_xeber.amb_item).
2. Həftənin bazarları: şənbə saat 11:00-da.
   - Brent, WTI, qızıl, gümüş və bitkoinin həftəlik dəyişməsi: indiki markets.json 7 gün əvvəlki ilə.
   - AMB-nin rəsmi məzənnələri, qonşu ölkələrin valyutaları da: həftənin son bülleteni 7 gün əvvəlki ilə.
   - Sorğu: həftədə 2 (AMB). 7 gün əvvəlki markets.json-u canlıda öz kiçik gündəlik bağlanış faylımız verəcək;
     sınaq onu GitHub-dan alır (2 sorğu, github_history).

Sayta qoşulmayıb: updater.py və pipeline bu faylı çağırmır.
Nümunələr: python oz_bazar.py --sinaq --root DIR [--now 2026-11-10T09:00+04:00]
"""
import datetime
import json
import pathlib
import re
import sys
import xml.etree.ElementTree as ET

import oz_xeber as ox

BAKU = ox.BAKU
DAY = datetime.timedelta(days=1)
AMB_CREDIT = "Azərbaycan Mərkəzi Bankı"
AMB_LINK = "https://www.cbar.az/currency/rates"
METALS = ("XAU", "XAG", "XPT", "XPD")  # qızıl, gümüş, platin, palladium
# Bülleten 09:06–09:20 arası çıxır (markets.json tarixçəsi, 2026-11-02...06).
DAILY_SLOT = datetime.time(9, 40)
# Şənbə: birjalar cümə gecəsi bağlanıb. Yahoo-nun yekun qiyməti səhər gəlir: 31 oktyabrda Brent 08:05-də 112,33,
# 10:45-də 113,43 idi.
WEEKLY_SLOT = datetime.time(11, 0)
# ABŞ seansının bağlanışı: qışda 22:00 UTC (17:00 New York), yayda 21:00 UTC; 21:00–22:00 fasilədir. 22:00 UTC-dən əvvəlki
# son nüsxə hər iki halda bağlanış qiymətidir (qışda ən çox ~10 dəqiqə əvvəl).
CLOSE_UTC = datetime.time(22, 0)
FRESH = datetime.timedelta(hours=3)     # markets.json sətri bundan köhnədirsə yazılmır
SNAP_AGE = datetime.timedelta(hours=6)  # GitHub nüsxəsi istənən andan bundan köhnədirsə götürülmür
WEEK_CODES = ("USD", "EUR", "RUB", "TRY", "GEL", "IRR", "KZT", "UZS", "KGS", "TMT", "UAH", "BYN", "CNY")
# id: (adlıq hal, yiyəlik hal + vahid, qrup). Qrup başlıqda təkrarı saxlayır: Brent və WTI birlikdə hərəkət edir.
WORLD = {
    "BRENT": ("Brent nefti", "Brent neftinin bareli", "neft"),
    "WTI": ("WTI nefti", "WTI neftinin bareli", "neft"),
    "XAU": ("qızıl", "qızılın unsiyası", "metal"),
    "XAG": ("gümüş", "gümüşün unsiyası", "metal"),
    "BTC": ("bitkoin", "bitkoin", "kripto"),
}
WEEK_IDS = ("BRENT", "WTI", "XAU", "XAG", "BTC")
_LABEL = {"BRENT": "neft", "WTI": "neft", "XAU": "qızıl", "XAG": "gümüş", "BTC": "bitkoin"}
DEC = {"BRENT": 2, "WTI": 2, "XAU": 1, "XAG": 2, "BTC": 0}
SRC_LINKS = {"Yahoo Finance": "https://finance.yahoo.com/", "gold-api.com": "https://gold-api.com/",
             "CNBC": "https://www.cnbc.com/", "CoinGecko": "https://www.coingecko.com/", AMB_CREDIT: AMB_LINK}
REPO_COMMITS = "https://api.github.com/repos/8ulduz/8ulduz/commits?path=data/markets.json&until={}&per_page=1"
REPO_RAW = "https://raw.githubusercontent.com/8ulduz/8ulduz/{}/data/markets.json"


# --- Köməkçilər ---------------------------------------------------------------------------------------

def _baku(now):
    return now.astimezone(BAKU) if now.tzinfo else now.replace(tzinfo=BAKU)


def _when(iso):
    """ISO vaxt -> Bakı vaxtı (aware) və ya None."""
    try:
        t = datetime.datetime.fromisoformat(str(iso).replace("Z", "+00:00"))
    except (TypeError, ValueError):
        return None
    return t.astimezone(BAKU) if t.tzinfo else t.replace(tzinfo=BAKU)


def _isnum(x):
    return isinstance(x, (int, float)) and not isinstance(x, bool)


def _cap(s):
    return s[:1].upper() + s[1:]


def _join(words):
    """«a, b və c»."""
    words = list(words)
    return ", ".join(words[:-1]) + " və " + words[-1] if len(words) > 1 else "".join(words)


def _date_text(d):
    return f"{ox.day_text(d)} {d.year}"


def _pct(new, old):
    return round((new - old) / old * 100, 2) if old else 0.0


def _verb(diff):
    return "bahalaşıb" if diff > 0 else "ucuzlaşıb"


def _manat(v):
    return f"{ox.az_num(v, 4)} manat"


def _dollar(v, dec):
    return f"{ox.az_num(v, dec)} dollar"


def _moves(parts):
    """[(ad, fərq, mətn)] -> «qızıl 74,8 dollar (1,82%), gümüş 0,97 dollar (1,86%) ucuzlaşıb»: fel eynidirsə bir dəfə."""
    verbs = [_verb(d) if d else "dəyişməyib" for _, d, _ in parts]
    if len(set(verbs)) == 1 and verbs[0] != "dəyişməyib":
        return ", ".join(f"{name} {text}" for name, _, text in parts) + " " + verbs[0]
    return ", ".join(f"{name} dəyişməyib" if verb == "dəyişməyib" else f"{name} {text} {verb}"
                     for (name, _, text), verb in zip(parts, verbs))


def _guard(item):
    """Rəhbərliyin adı keçən xəbər avtomatik çıxmır (oz_xeber.needs_owner). Bazar məlumatında olmamalıdır, yenə yoxlanır."""
    if ox.needs_owner("\n".join([item["title"], item["lead"], *item["body"]])):
        return None, "rəhbərliyin adı keçir: sahibin təsdiqi lazımdır"
    return item, item.get("why", "")


# --- AMB bülleteni -----------------------------------------------------------------------------------

def parse_bulletin(xml_bytes):
    """AMB bülleteni -> (qüvvədə olduğu gün, {kod: {"type", "nominal", "name", "value"}}).
    type bölmənin adıdır («Bank metalları», «Xarici valyutalar»). Gün bülletenin öz Date-indəndir: həftə sonu və
    bayram günü sorğusu son bülleteni qaytarır."""
    root = ET.fromstring(xml_bytes)
    try:
        day = datetime.datetime.strptime((root.get("Date") or "").strip(), "%d.%m.%Y").date()
    except ValueError:
        day = None
    rows = {}
    for group in root.iter("ValType"):
        kind = " ".join((group.get("Type") or "").split())
        for v in group.iter("Valute"):
            try:
                value = float(v.findtext("Value"))
            except (TypeError, ValueError):
                continue
            if value > 0 and v.get("Code"):
                rows[v.get("Code")] = {"type": kind, "nominal": " ".join((v.findtext("Nominal") or "").split()),
                                       "name": " ".join((v.findtext("Name") or "").split()), "value": value}
    return day, rows


def bulletin(fetch, day):
    """`day` günü qüvvədə olan bülleten (o gün bülleten yoxdursa, ondan əvvəlki son bülleten). 1 sorğu."""
    return parse_bulletin(fetch(ox.AMB_URL.format(day), timeout=15))


def previous(fetch, day):
    """`day`-dan əvvəlki son bülleten, oz_xeber.amb_latest kimi gün-gün geri (adətən 1 sorğu)."""
    for back in range(1, 8):
        pday, rows = bulletin(fetch, day - back * DAY)
        if pday and pday < day:
            return pday, rows
    return None, {}


def latest_pair(fetch, today):
    """Son bülleten və ondan əvvəlki. Ünvanlar oz_xeber.amb_latest-inkilərdir (əvvəl sabahın tarixi, sonra geri)."""
    cur = bulletin(fetch, today + DAY)
    return cur, (previous(fetch, cur[0]) if cur[0] else (None, {}))


def week_bulletins(fetch, today):
    """Həftənin son bülleteni (`today` günü qüvvədə olan) və ondan 7 gün əvvəlki (o gün bülleten yoxdursa, ondan əvvəlki
    son bülleten). 2 sorğu."""
    cur = bulletin(fetch, today)
    return cur, (bulletin(fetch, cur[0] - 7 * DAY) if cur[0] else (None, {}))


# --- markets.json --------------------------------------------------------------------------------------

def read_markets(root):
    try:
        doc = json.loads((pathlib.Path(root) / "data" / "markets.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    return doc if isinstance(doc, dict) else {}


def market_rows(markets):
    return {i.get("id"): i for i in (markets or {}).get("items") or [] if isinstance(i, dict)}


def usable(item, markets=None, now=None):
    """markets.json sətri yazıla bilərmi: dəyəri var və «stale» deyil. now verilibsə, sətrin vaxtı now-dan FRESH-dən
    köhnə olmamalıdır (və gələcəkdə olmamalıdır)."""
    if not item or item.get("stale") or not _isnum(item.get("value")) or item["value"] <= 0:
        return False
    if now is None:
        return True
    at = _when(item.get("at") or (markets or {}).get("updatedAt"))
    return bool(at) and now - FRESH <= at <= now + datetime.timedelta(minutes=15)


def _dec(item):
    d = item.get("dec")
    return int(d) if _isnum(d) and int(d) == d and 0 <= d <= 4 else DEC.get(item.get("id"), 2)


def _change(item):
    """markets.json sətrinin öz dəyişməsi (əvvəlki bağlanışa görə): (yuvarlaq fərq, «74,8 dollar (1,82%)») və ya None."""
    ch, pct = item.get("change"), item.get("changePct")
    if not (_isnum(ch) and _isnum(pct)):
        return None
    dec = _dec(item)
    diff = round(ch, dec)
    return diff, f"{_dollar(diff, dec)} ({ox.az_num(pct, 2)}%)"


def _own_change(item, old):
    """Öz bağlanış nüsxəmizə görə dəyişmə: eyni mənbədən (spot ilə spot) olmalıdır. Fərq ekrandakı yuvarlaq qiymətlərdən."""
    if not usable(old) or (old.get("src") or "") != (item.get("src") or ""):
        return None
    dec = _dec(item)
    diff = round(round(item["value"], dec) - round(old["value"], dec), dec)
    return diff, f"{_dollar(diff, dec)} ({ox.az_num(_pct(item['value'], old['value']), 2)}%)"


def prev_close(history, day, back=4):
    """Təmiz funksiya. history: {gün: markets}, günün bağlanışından sonra götürülmüş nüsxə (gün: birja seansının günü).
    `day`-dan əvvəlki son gün, ən çox `back` gün geri (bazar ertəsi üçün cümə): (gün, markets) və ya (None, None)."""
    best = None
    for key, markets in (history or {}).items():
        d = _iso_day(key)
        if d is None or not isinstance(markets, dict) or not day - back * DAY <= d < day:
            continue
        if best is None or d > best[0]:
            best = (d, markets)
    return best or (None, None)


def close_time(at):
    """`at`-dan əvvəlki son ABŞ seansının bağlanış anı (iş günü, CLOSE_UTC)."""
    t = datetime.datetime.combine(at.astimezone(datetime.timezone.utc).date(), CLOSE_UTC, datetime.timezone.utc)
    while t > at or t.weekday() >= 5:
        t -= DAY
    return t


# --- 1. AMB bank metalları (iş günləri) -----------------------------------------------------------------

def metal_rows(rows, prev_rows):
    """Bülletenin bank metalları (qızıl birinci), əvvəlki bülletenə görə dəyişmə ilə."""
    out = []
    for code in METALS:
        r = rows.get(code)
        if not r:
            continue
        p = prev_rows.get(code)
        out.append(dict(r, code=code, diff=round(r["value"] - p["value"], 4) if p else None,
                        pct=_pct(r["value"], p["value"]) if p else None))
    return out


def _gold_phrase(nominal):
    """AMB-nin vahidi ilə: «1 t.u.» = 1 troya unsiyası (AMB qısaltmanı açmır; AZƏRTAC «troya unsiyası» yazır)."""
    if nominal == "1 t.u.":
        return "qızılın 1 troya unsiyasının (t.u.) rəsmi qiyməti"
    return f"qızılın rəsmi qiyməti ({nominal})" if nominal else "qızılın rəsmi qiyməti"


def _metal_line(m):
    head = " ".join(x for x in (m["nominal"], ox._low(m["name"])) if x) + f": {_manat(m['value'])}"
    if m["diff"] is None:
        return head
    if not m["diff"]:
        return head + " (dəyişməyib)"
    return head + f" ({ox.az_num(m['diff'], 4)} manat, {ox.az_num(m['pct'], 2)}% {_verb(m['diff'])})"


def _metals_title(metals, gold):
    v, d, p = _manat(gold["value"]), gold["diff"], gold["pct"]
    moved = [m for m in metals if m["diff"]]
    if d and abs(p) >= 2:
        return f"AMB: qızıl {ox.az_num(p, 2)}% {_verb(d)}, unsiyası {v}"
    if len(moved) == 4 and len({m["diff"] > 0 for m in moved}) == 1:
        return f"AMB-də dörd bank metalının hamısı {_verb(d)}: qızılın unsiyası {v}"
    if d:
        return f"AMB: qızılın unsiyası {ox.az_num(d, 4)} manat {'bahalaşaraq' if d > 0 else 'ucuzlaşaraq'} {v} olub"
    if moved:
        m = max(moved, key=lambda x: abs(x["pct"]))
        return (f"AMB: qızılın qiyməti dəyişməyib, {ox._gen_plain(ox._low(m['name']))} unsiyası "
                f"{ox.az_num(m['diff'], 4)} manat {_verb(m['diff'])}")
    return f"AMB-də bank metallarının qiyməti dəyişməyib: qızılın unsiyası {v}"


def world_lines(markets, now, closes=None):
    """Dünya bazarı: qızıl və gümüş bir cümlədə, bitkoin ayrıca. «stale» və ya köhnə sətir yazılmır.
    Diqqət: updater-də qızıl və gümüşün dəyəri gold-api.com spot qiymətidir, «əvvəlki bağlanış» (change) isə Yahoo-nun
    GC=F/SI=F fyuçersinin previousClose-udur. 6 noyabr 09:31-də markets.json qızıl üçün −74,8 dollar (−1,82%) yazırdı,
    spot isə əvvəlki bağlanışda (5 noyabr 21:55 UTC) 4 088,8 idi: həqiqi dəyişmə −50,1 dollar (−1,23%). Ona görə gold-api
    sətrinin dəyişməsi öz bağlanış nüsxəmizdən hesablanır (closes: {gün: markets}, prev_close); nüsxə yoxdursa yazılmır.
    Yahoo-dan gələn sətirdə (bitkoin, gold-api alınmayanda qızıl) dəyər və bağlanış eyni mənbədəndir: o dəyişmə yazılır."""
    rows = market_rows(markets)
    old_rows = market_rows(prev_close(closes, now.date())[1])
    out = []
    metals = [rows[k] for k in ("XAU", "XAG") if usable(rows.get(k), markets, now)]
    if metals:
        at = _when(metals[0].get("at") or markets.get("updatedAt"))
        prices = ", ".join(f"{WORLD[i['id']][1]} {_dollar(i['value'], _dec(i))}" for i in metals)
        srcs = _join(dict.fromkeys(i["src"] for i in metals if i.get("src")))
        line = f"Dünya bazarında Bakı vaxtı ilə {ox.time_loc(at)} {prices} olub" + (f" ({srcs})." if srcs else ".")
        parts = []
        for i in metals:
            c = _own_change(i, old_rows.get(i["id"])) if i.get("src") == "gold-api.com" else _change(i)
            if c:
                parts.append((WORLD[i["id"]][0], c[0], c[1]))
        if parts:
            line += f" Əvvəlki bağlanışla müqayisədə {_moves(parts)}."
        out.append(line)
    btc = rows.get("BTC")
    if usable(btc, markets, now):
        line = f"Bitkoinin qiyməti {_dollar(btc['value'], _dec(btc))} olub"
        c = _change(btc)
        if c:
            since = "son 24 saatda" if btc.get("src") == "CoinGecko" else "əvvəlki bağlanışla müqayisədə"
            line += f", {since} " + (f"{c[1]} {_verb(c[0])}" if c[0] else "dəyişməyib")
        out.append(line + (f" ({btc['src']})." if btc.get("src") else "."))
    return out


def metals_item(cur, prev, markets, now, closes=None):
    """AMB bank metalları və dünya qiyməti. cur, prev: parse_bulletin() nəticəsi; markets: data/markets.json;
    closes: {gün: markets} bağlanış nüsxələri (world_lines). Xəbər yalnız bu günün (now) bülleteni üçündür.
    Qaytarır (xəbər və ya None, səbəb)."""
    day, rows = cur
    pday, prows = prev if prev and prev[0] and day and prev[0] < day else (None, {})
    if not day:
        return None, "AMB bülleteninin tarixi oxunmadı"
    if day != now.date():
        return None, f"bu gün ({_date_text(now.date())}) AMB-nin yeni bülleteni yoxdur, son bülleten {_date_text(day)}"
    metals = metal_rows(rows, prows)
    gold = next((m for m in metals if m["code"] == "XAU"), None)
    if not gold:
        return None, "bülletendə qızılın qiyməti yoxdur"
    if not pday or gold["diff"] is None:
        return None, "əvvəlki bülleten alınmadı: dəyişmə yazıla bilmir"
    v, d = _manat(gold["value"]), gold["diff"]
    lead = f"Azərbaycan Mərkəzi Bankının (AMB) {ox.day_text(day)} bülleteninə görə {_gold_phrase(gold['nominal'])} {v}dır. "
    if d:
        lead += (f"Bu, {ox.day_text(pday)} bülletenindəkindən {ox.az_num(d, 4)} manat ({ox.az_num(gold['pct'], 2)}%) "
                 f"{'çoxdur' if d > 0 else 'azdır'}.")
    else:
        lead += f"Bu, {ox.day_text(pday)} bülletenindəki qiymətlə eynidir."
    moved = any(m["diff"] for m in metals)
    item = {"kind": "amb-metal", "key": f"amb-metal-{day.isoformat()}", "topic": "iqtisadiyyat",
            "slot": f"{DAILY_SLOT:%H:%M}", "list": True, "title": _metals_title(metals, gold), "lead": lead,
            "body": [_metal_line(m) for m in metals if m["code"] != "XAU"] + world_lines(markets, now, closes),
            "credit": AMB_CREDIT, "link": AMB_LINK, "worth": moved}
    if not moved:
        item["why"] = "AMB-də bank metallarının qiyməti dəyişməyib"
    return _guard(item)


def daily(root, now, fetch=None, closes=None):
    """Bu günün metal xəbəri: iş günü, 09:40-dan sonra, AMB bu gün yeni bülleten veribsə. Həftə sonu və 09:40-dan əvvəl
    sorğu getmir; bayramda 1 sorğu. closes: {gün: markets}, canlıda öz gündəlik bağlanış faylımızdan.
    Qaytarır (xəbər və ya None, səbəb)."""
    now = _baku(now)
    if now.weekday() >= 5:
        return None, "həftə sonu AMB bülleten vermir"
    if now.time() < DAILY_SLOT:
        return None, f"xəbərin vaxtı hələ çatmayıb ({DAILY_SLOT:%H:%M})"
    if not fetch:
        return None, "sorğu funksiyası verilməyib"
    try:
        cur = bulletin(fetch, now.date() + DAY)
        if cur[0] != now.date():
            return metals_item(cur, None, {}, now)  # yeni bülleten yoxdur: səbəbi metals_item yazır
        prev = previous(fetch, cur[0])
    except Exception as e:
        return None, f"AMB bülleteni alınmadı: {type(e).__name__}"
    return metals_item(cur, prev, read_markets(root), now, closes)


# --- 2. Həftənin bazarları (şənbə) -----------------------------------------------------------------------

def _iso_day(key):
    if isinstance(key, datetime.datetime):
        return _baku(key).date()
    if isinstance(key, datetime.date):
        return key
    try:
        return datetime.date.fromisoformat(str(key)[:10])
    except ValueError:
        return None


def week_ago(history, now, tol=1):
    """Təmiz funksiya. history: {gün: markets} (gün date və ya «YYYY-MM-DD»). 7 gün əvvəlki gün, o yoxdursa ±tol gün
    içində ən yaxını. Qaytarır (gün, markets) və ya (None, None).
    Canlıda tarixçəni öz kiçik gündəlik bağlanış faylımız verəcək (gündə ~10 dəyər, main-in isti yolundan kənarda):
    CI-da checkout dayazdır, git tarixçəsi yoxdur. Sınaq onu GitHub-dan alır (github_history)."""
    target = now.date() - 7 * DAY
    best = None
    for key, markets in (history or {}).items():
        day = _iso_day(key)
        if day is None or not isinstance(markets, dict):
            continue
        gap = abs((day - target).days)
        if gap <= tol and (best is None or (gap, day) < (best[0], best[1])):
            best = (gap, day, markets)
    return (best[1], best[2]) if best else (None, None)


def week_moves(markets, old, now):
    """Brent, WTI, qızıl, gümüş, bitkoin: indiki markets.json ilə 7 gün əvvəlkinin fərqi. Təmiz funksiya.
    İndiki sətir təzə olmalıdır (usable, now), köhnə sətir «stale» olmamalıdır, ikisi də eyni mənbədən olmalıdır
    (gold-api spotu Yahoo fyuçersi ilə müqayisə olunmur); biri yoxdursa alət yazılmır.
    Fərq ekrandakı yuvarlaq qiymətlərdən hesablanır (oxucu çıxsa eyni rəqəmi alsın), faiz dəqiq qiymətlərdən."""
    now_rows, old_rows = market_rows(markets), market_rows(old)
    out = []
    for mid in WEEK_IDS:
        a, b = old_rows.get(mid), now_rows.get(mid)
        if not usable(b, markets, now) or not usable(a) or (a.get("src") or "") != (b.get("src") or ""):
            continue
        dec = _dec(b)
        out.append({"id": mid, "old": a["value"], "new": b["value"], "dec": dec, "src": b.get("src") or "",
                    "diff": round(round(b["value"], dec) - round(a["value"], dec), dec),
                    "pct": _pct(b["value"], a["value"])})
    return out


def week_currencies(cur, prev, now):
    """AMB: həftənin son bülleteni (bu həftənin iş günündən) 7 gün əvvəlki bülletenlə. Qaytarır (məlumat və ya None, səbəb)."""
    day, rows = cur if cur else (None, {})
    pday, prows = prev if prev else (None, {})
    monday = now.date() - now.weekday() * DAY
    if not day:
        return None, "AMB bülleteni yoxdur"
    if not monday <= day <= now.date():
        return None, f"bu həftə AMB bülleten verməyib, son bülleten {_date_text(day)}"
    if not pday or pday >= day:
        return None, "7 gün əvvəlki AMB bülleteni yoxdur"
    out = []
    for code in WEEK_CODES:
        a, b = prows.get(code), rows.get(code)
        if a and b:
            out.append({"code": code, "name": ox._amb_name(b["name"]), "value": b["value"],
                        "diff": round(b["value"] - a["value"], 4), "pct": _pct(b["value"], a["value"])})
    if not out:
        return None, "bülletenlərdə müqayisə ediləcək valyuta yoxdur"
    return {"day": day, "pday": pday, "rows": out}, ""


def _span(a, b):
    if a.year != b.year:
        return f"{_date_text(a)} – {_date_text(b)}"
    return f"{ox.day_text(a)} – {ox.day_text(b)}"


def _week_clause(m):
    """«Brent neftinin bareli 113,43 dollardan 98,32 dollara düşüb (15,11 dollar, 13,32%)»."""
    dec, name = m["dec"], WORLD[m["id"]][1]
    if not m["diff"]:
        return f"{name} dəyişməyib: {_dollar(m['new'], dec)}"
    text = (f"{name} {_dollar(m['old'], dec)}dan {_dollar(m['new'], dec)}a {'qalxıb' if m['diff'] > 0 else 'düşüb'} "
            f"({_dollar(m['diff'], dec)}")
    return text + (f", {ox.az_num(m['pct'], 2)}%)" if m["pct"] else ")")


def _pair(movers):
    """Başlıq və giriş üçün iki alət: ən çox dəyişən və başqa qrupdan ən çox dəyişən (Brent və WTI yan-yana düşməsin)."""
    if not movers:
        return []
    a = movers[0]
    b = next((m for m in movers[1:] if WORLD[m["id"]][2] != WORLD[a["id"]][2]), movers[1] if len(movers) > 1 else None)
    return [a, b] if b else [a]


def _top_currencies(amb):
    rows = [r for r in (amb or {}).get("rows") or [] if r["diff"] and r["pct"]]
    return sorted(rows, key=lambda r: -abs(r["pct"]))


def _week_title(moves, movers, pair, amb):
    if pair:
        a = pair[0]
        pa = f"{ox.az_num(a['pct'], 2)}%"
        if len(movers) >= 3 and len(movers) == len(moves) and len({m["pct"] > 0 for m in movers}) == 1:
            names = _join(dict.fromkeys(_LABEL[m["id"]] for m in moves))
            return (f"Həftənin bazarları: {names} {_verb(a['pct'])}, {WORLD[a['id']][0]} {pa} "
                    f"{'qalxıb' if a['pct'] > 0 else 'düşüb'}")
        if len(pair) == 1:
            return f"Həftənin bazarları: {WORLD[a['id']][0]} {pa} {_verb(a['pct'])}"
        b = pair[1]
        pb = f"{ox.az_num(b['pct'], 2)}%"
        if (a["pct"] > 0) == (b["pct"] > 0):
            return f"Həftənin bazarları: {WORLD[a['id']][0]} {pa}, {WORLD[b['id']][0]} {pb} {_verb(a['pct'])}"
        return f"Həftənin bazarları: {WORLD[a['id']][0]} {pa} {_verb(a['pct'])}, {WORLD[b['id']][0]} {pb} {_verb(b['pct'])}"
    top = _top_currencies(amb)
    if top:
        return f"Həftənin bazarları: AMB-də {top[0]['name']} {ox.az_num(top[0]['pct'], 2)}% {_verb(top[0]['diff'])}"
    return "Həftənin bazarları: qiymətlər dəyişməyib"


def _week_lead(old_day, now, moves, pair, amb):
    if pair:
        clauses = [_week_clause(m) for m in pair]
        return (f"Son bir həftədə ({_span(old_day, now.date())}) dünya bazarında {clauses[0]}."
                + "".join(f" {_cap(c)}." for c in clauses[1:]))
    if moves:
        return f"Son bir həftədə ({_span(old_day, now.date())}) dünya bazarında qiymətlər dəyişməyib."
    head = (f"Azərbaycan Mərkəzi Bankının (AMB) {ox.day_text(amb['day'])} bülletenində, "
            f"{ox.day_text(amb['pday'])} bülleteni ilə müqayisədə, ")
    top = _top_currencies(amb)[:2]
    if not top:
        return head + "rəsmi məzənnələr dəyişməyib."
    return head + _moves([(r["name"], r["diff"], f"{ox.az_num(r['diff'], 4)} manat ({ox.az_num(r['pct'], 2)}%)")
                          for r in top]) + "."


def _amb_lines(amb):
    changed = [r for r in amb["rows"] if r["diff"]]
    same = [r for r in amb["rows"] if not r["diff"]]
    lines = [f"Mərkəzi Bankın rəsmi məzənnələri, {ox.day_text(amb['day'])} bülleteni "
             f"{ox.day_text(amb['pday'])} bülleteni ilə müqayisədə:"]
    lines += [f"{r['name']}: {_manat(r['value'])} ({ox.az_num(r['diff'], 4)} manat, {ox.az_num(r['pct'], 2)}% "
              f"{_verb(r['diff'])})" for r in changed]
    if same:
        lines.append("Dəyişməyib: " + ", ".join(f"{r['name']} ({_manat(r['value'])})" for r in same))
    return lines


def weekly_item(markets, history, cur, prev, now):
    """Şənbə xəbəri, təmiz funksiya (sorğu yoxdur). markets: indiki markets.json; history: {gün: markets} (week_ago);
    cur, prev: həftənin son bülleteni və 7 gün əvvəlki bülleten (parse_bulletin). Qaytarır (xəbər və ya None, səbəb)."""
    old_day, old = week_ago(history, now)
    moves = week_moves(markets, old, now) if old else []
    amb, amb_why = week_currencies(cur, prev, now)
    if not moves and not amb:
        why = "7 gün əvvəlki bazar məlumatı yoxdur" if not old else "bazar qiymətləri köhnədir və ya yoxdur"
        return None, f"{why}; {amb_why}"
    movers = sorted((m for m in moves if m["diff"] and m["pct"]), key=lambda m: -abs(m["pct"]))
    pair = _pair(movers)
    body = [_cap(_week_clause(m)) + "." for m in moves if m not in pair]
    if amb:
        body += _amb_lines(amb)
    srcs = list(dict.fromkeys(m["src"] for m in moves if m["src"]))
    if amb:
        srcs.append(AMB_CREDIT)
    moved = bool(movers) or bool(amb and any(r["diff"] for r in amb["rows"]))
    item = {"kind": "bazar-hefte", "key": f"bazar-hefte-{now.date().isoformat()}", "topic": "iqtisadiyyat",
            "slot": f"{WEEKLY_SLOT:%H:%M}", "list": True, "title": _week_title(moves, movers, pair, amb),
            "lead": _week_lead(old_day, now, moves, pair, amb), "body": body,
            "credit": _join(srcs) or "markets.json", "link": SRC_LINKS.get(srcs[0], AMB_LINK) if srcs else AMB_LINK,
            "worth": moved}
    if not moved:
        item["why"] = "həftə ərzində qiymətlər dəyişməyib"
    return _guard(item)


def weekly(root, now, fetch=None, history=None):
    """Bu günün həftəlik xəbəri: şənbə, 11:00-dan sonra. history: {gün: markets}, canlıda öz gündəlik bağlanış
    faylımızdan (hələ yoxdur). Verilməsə bazar hissəsi yazılmır. Qaytarır (xəbər və ya None, səbəb)."""
    now = _baku(now)
    if now.weekday() != 5:
        return None, "həftəlik xəbər yalnız şənbə günü çıxır"
    if now.time() < WEEKLY_SLOT:
        return None, f"xəbərin vaxtı hələ çatmayıb ({WEEKLY_SLOT:%H:%M})"
    cur, prev, note = (None, {}), (None, {}), ""
    if fetch:
        try:
            cur, prev = week_bulletins(fetch, now.date())
        except Exception as e:
            note = f"; AMB bülleteni alınmadı: {type(e).__name__}"
    item, why = weekly_item(read_markets(root), history or {}, cur, prev, now)
    return item, (why if item else why + note)


# --- GitHub-dakı markets.json tarixçəsi (yalnız sınaq) ------------------------------------------------------

def github_markets(fetch, at):
    """main-dəki data/markets.json-un `at` anına qədərki son nüsxəsi: 2 sorğu (commits API, sonra raw), girişsiz.
    Nüsxə `at`-dan SNAP_AGE-dən köhnədirsə None."""
    until = at.astimezone(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    commits = json.loads(fetch(REPO_COMMITS.format(until), timeout=15,
                               headers={"Accept": "application/vnd.github+json"}).decode("utf-8"))
    sha = commits[0].get("sha") if isinstance(commits, list) and commits and isinstance(commits[0], dict) else ""
    if not re.fullmatch(r"[0-9a-f]{40}", sha or ""):
        return None
    markets = json.loads(fetch(REPO_RAW.format(sha), timeout=15).decode("utf-8"))
    t = _when(markets.get("updatedAt")) if isinstance(markets, dict) else None
    if not t or not at - SNAP_AGE <= t <= at + datetime.timedelta(minutes=15):
        return None
    return markets


def github_history(fetch, now):
    """{gün: markets}: markets.json-un `now`-dan 7 gün əvvəlki nüsxəsi (2 sorğu). Yalnız sınaq üçündür;
    canlıda bunun yerinə öz kiçik gündəlik bağlanış faylımız olacaq."""
    snap = github_markets(fetch, now - 7 * DAY)
    return {_when(snap["updatedAt"]).date(): snap} if snap else {}


# --- Canlı və sınaq ------------------------------------------------------------------------------------------

def items(root, now, fetch=None, history=None):
    """`now` anında (Bakı) canlının dərc edəcəyi bazar xəbərləri. worth False olan xəbər «why» ilə qayıdır, dərc olunmur.
    history: {gün: markets}, öz gündəlik bağlanış faylımızdan (hələ yoxdur): gündəlik xəbər ondan əvvəlki bağlanışı
    (prev_close), həftəlik xəbər 7 gün əvvəlkini (week_ago) götürür."""
    now = _baku(now)
    found = [daily(root, now, fetch, history)[0], weekly(root, now, fetch, history)[0]]
    return [i for i in found if i]


def _default_fetch():
    return ox._u().fetch


def _memo(fetch):
    """Sınaqda eyni ünvana ikinci sorğu getmir."""
    seen = {}

    def get(url, **kw):
        if url not in seen:
            seen[url] = fetch(url, **kw)
        return seen[url]
    return get


def _verdict(item):
    return "✅ Dərc olunardı" if item.get("worth") else f"⏭ Dərc olunmazdı: {item.get('why') or 'dəyəri azdır'}"


def _shown(item, why):
    return ox.render(item) + [_verdict(item), ""] if item else [f"⏭ Dərc olunmazdı: {why}", ""]


def _snapshot(fetch, at):
    """(markets.json-un `at` anına qədərki nüsxəsi və ya {}, izah)."""
    try:
        snap = github_markets(fetch, at)
    except Exception as e:
        return {}, f"markets.json-un nüsxəsi alınmadı ({type(e).__name__})"
    if not snap:
        return {}, "markets.json-un həmin vaxta yaxın nüsxəsi tapılmadı"
    t = _when(snap.get("updatedAt"))
    return snap, f"markets.json-un {ox.day_text(t)} {t:%H:%M} nüsxəsi (GitHub)"


def _history(fetch, at):
    snap, note = _snapshot(fetch, at - 7 * DAY)
    return ({_when(snap["updatedAt"]).date(): snap} if snap else {}), note


def _closes(fetch, at):
    """Öz bağlanış faylımızın əvəzi: markets.json-un `at`-dan əvvəlki son seans bağlanışındakı nüsxəsi (2 sorğu)."""
    t = close_time(at)
    snap, note = _snapshot(fetch, t)
    return ({t.date(): snap} if snap else {}), note


def _sinaq_daily(root, now, fetch):
    item, why = daily(root, now, fetch)
    if item:  # bu günün bülleteni var: bağlanış nüsxəsi ilə yenidən (bülletenlər _memo-dadır, təkrar sorğu yoxdur)
        closes, n_close = _closes(fetch, now)
        item, why = daily(root, now, fetch, closes)
        return [f"**Bu gün ({_date_text(now.date())}):** əvvəlki bağlanış: {n_close}.", ""] + _shown(item, why)
    md = [f"**Bu gün ({_date_text(now.date())}, {now:%H:%M}):** ⏭ Dərc olunmazdı: {why}", ""]
    try:
        cur, prev = latest_pair(fetch, now.date())
    except Exception as e:
        return md + [f"> AMB bülleteni alınmadı: {type(e).__name__}", ""]
    day = cur[0]
    if not day:
        return md + ["> AMB bülleteninin tarixi oxunmadı.", ""]
    if day == now.date():  # bu günün bülleteni var, xəbərin vaxtı hələ çatmayıb
        at, markets, note = now, read_markets(root), "dünya qiyməti indiki markets.json-dan"
    else:
        at = datetime.datetime.combine(day, DAILY_SLOT, BAKU)
        markets, note = _snapshot(fetch, at)
        note = "dünya qiyməti: " + note if markets else note + ": dünya qiyməti yazılmır"
    closes, n_close = _closes(fetch, at)
    item, why = metals_item(cur, prev, markets, at, closes)
    md += [f"**Son real hal: {_date_text(day)} bülleteni**, xəbər həmin gün {ox.time_loc(DAILY_SLOT)} çıxardı; {note}; "
           f"əvvəlki bağlanış: {n_close}.", ""]
    return md + _shown(item, why)


def _sinaq_weekly(root, now, fetch):
    if now.weekday() == 5 and now.time() >= WEEKLY_SLOT:
        history, note = _history(fetch, now)
        item, why = weekly(root, now, fetch, history)
        return [f"**Bu gün ({_date_text(now.date())}):** 7 gün əvvəl: {note}.", ""] + _shown(item, why)
    _, why = weekly(root, now, fetch)
    md = [f"**Bu gün ({_date_text(now.date())}, {now:%H:%M}):** ⏭ Dərc olunmazdı: {why}", ""]
    at = datetime.datetime.combine(now.date() - ((now.weekday() - 5) % 7) * DAY, WEEKLY_SLOT, BAKU)
    if at > now:
        at -= 7 * DAY
    markets, n_now = _snapshot(fetch, at)
    history, n_old = _history(fetch, at)
    try:
        cur, prev = week_bulletins(fetch, at.date())
        n_amb = (f"AMB-nin {_date_text(cur[0])} və {_date_text(prev[0])} bülletenləri" if cur[0] and prev[0]
                 else "AMB bülleteni oxunmadı")
    except Exception as e:
        cur, prev, n_amb = (None, {}), (None, {}), f"AMB bülleteni alınmadı ({type(e).__name__})"
    item, why = weekly_item(markets, history, cur, prev, at)
    md += [f"**Son real hal: {_date_text(at.date())}, şənbə**, xəbər {ox.time_loc(at)} çıxardı. İndi: {n_now}; "
           f"7 gün əvvəl: {n_old}; {n_amb}.", ""]
    return md + _shown(item, why)


def sinaq(root, now=None, fetch=None):
    """Nümunələr (Markdown): bu günün qərarı və son real hal (son bülleten, son şənbə). Sayta və repoya heç nə yazmır."""
    now = _baku(now or datetime.datetime.now(BAKU))
    fetch = _memo(fetch or _default_fetch())
    md = [f"Bakı vaxtı ilə {now:%d.%m.%Y %H:%M}. Sayta heç nə yazılmır.", ""]
    md += ["## AMB bank metalları və dünya qiyməti (iş günləri, 09:40)", ""] + _sinaq_daily(root, now, fetch)
    md += ["## Həftənin bazarları (şənbə, 11:00)", ""] + _sinaq_weekly(root, now, fetch)
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
