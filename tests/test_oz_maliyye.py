"""Öz xəbər, mərhələ 2: maliyyə şablonları (oz_maliyye.py). Şəbəkə yoxdur: bütün sorğular saxtadır.
Real hal tests/fixtures/oz_maliyye-dədir (2026-11-09/10-da götürülmüş cavablar, yalnız lazım olan hissəsi):
- Yahoo spark: 9 noyabr 22:01Z (ABŞ seansı bağlanıb) və 10 noyabr 09:34Z (Avropa və İstanbul seansı gedir);
- Moskva Birjasının ISS tarixçəsi (IMOEX, 2–9 noyabr; 4 noyabr bayramdır);
- CoinGecko: 9 noyabr 18:12Z (efir −4,69%) və 10 noyabr 09:34Z (sakit gün);
- ABB (RSC cavabı və HTML), Unibank, Xalq Bank, AccessBank: hamısında məzənnə 6 noyabr 2026 tarixlidir;
- bfb.az ana səhifəsinin cədvəli və 3, 4, 5 noyabr hərraclarının səhifələri."""
import datetime
import json
import pathlib
import unittest
import urllib.error
from unittest.mock import patch

import oz_maliyye as om
import oz_xeber as ox

ROOT = pathlib.Path(__file__).resolve().parent.parent
FIX = pathlib.Path(__file__).resolve().parent / "fixtures" / "oz_maliyye"
BAKU = ox.BAKU
D = datetime.date


def fx(name):
    return (FIX / name).read_bytes()


def at(y, m, d, hh, mm=0):
    return datetime.datetime(y, m, d, hh, mm, tzinfo=BAKU)


def down():
    return urllib.error.URLError("saxta xəta")


def http(code):
    return urllib.error.HTTPError("https://saxta", code, "saxta", {}, None)


class Net:
    """Saxta şəbəkə. routes: ünvan (və ya «başlanğıc*») -> bayt, xəta və ya siyahı (hər sorğuya növbəti cavab, sonuncu
    təkrarlanır). Siyahıda olmayan ünvan URLError verir. calls: (ünvan, timeout, başlıqlar)."""

    def __init__(self, routes=None):
        self.routes = dict(routes or {})
        self.calls = []

    def __call__(self, url, timeout=None, headers=None):
        self.calls.append((url, timeout, headers))
        body = self.routes.get(url)
        if body is None:
            for prefix, value in self.routes.items():
                if prefix.endswith("*") and url.startswith(prefix[:-1]):
                    body = value
                    break
        if isinstance(body, list):
            body = body.pop(0) if len(body) > 1 else body[0]
        if body is None:
            raise down()
        if isinstance(body, Exception):
            raise body
        return body

    def urls(self):
        return [c[0] for c in self.calls]


SPARK1, SPARK2 = "spark-2026-11-09T2201Z.json", "spark-2026-11-10T0934Z.json"
CG_QUIET, CG_MOVED = "coingecko-2026-11-10T0934Z.json", "coingecko-2026-11-09T1812Z.json"
MOEX = "https://iss.moex.com/*"
Q1, Q2 = om.spark_url(), om.spark_url(om.YAHOO[1])
BANK_URL = {b[0]: b[1] for b in om.BANKS}
BANK_FIX = {"ABB": "abb-2026-11-10.rsc.txt", "Unibank": "unibank-2026-11-10.html", "Xalq Bank": "xalq-2026-11-10.html",
            "AccessBank": "access-2026-11-10.html"}
HOME = fx("bfb-home-2026-11-10.html")
LINK = {r["isin"]: r["link"] for r in om.parse_bfb_home(HOME)}
N28, N168, N84, N252, MN1080 = "AZ2736024707", "AZ2738024705", "AZ2739024704", "AZ2737024706", "AZ0201240105"
BFB_FIX = {N28: "bfb-amb-28-2026-11-04.html", N168: "bfb-amb-168-2026-11-04.html", N84: "bfb-amb-84-2026-11-05.html",
           N252: "bfb-amb-252-2026-11-05.html", MN1080: "bfb-mn-1080-2026-11-03.html"}
MON, TUE, WED, THU, FRI, SAT, SUN = (D(2026, 11, d) for d in (2, 3, 4, 5, 6, 7, 8))  # 2–8 noyabr 2026


def routes(**over):
    """Hər şeyin işlədiyi şəbəkə. over: ünvan -> başqa cavab."""
    r = {Q1: fx(SPARK1), MOEX: fx("moex-imoex-2026-11-10.json"), om.CG_URL: fx(CG_QUIET), om.BFB_HOME: HOME}
    r.update({BANK_URL[n]: fx(f) for n, f in BANK_FIX.items()})
    r.update({LINK[i]: fx(f) for i, f in BFB_FIX.items()})
    r.update(over)
    return r


def spark(name, edit):
    """Real spark cavabı, edit(simvol -> meta) ilə dəyişdirilmiş."""
    doc = json.loads(fx(name))
    edit({r["symbol"]: r["response"][0]["meta"] for r in doc["spark"]["result"]})
    return json.dumps(doc).encode()


def cg(name, when, edit=None):
    """Real CoinGecko cavabı, yenilənmə anı `when`-ə çəkilmiş."""
    doc = json.loads(fx(name))
    for row in doc.values():
        row["last_updated_at"] = int(when.timestamp())
    if edit:
        edit(doc)
    return json.dumps(doc).encode()


def day_at(day, hh, mm=0):
    return datetime.datetime.combine(day, datetime.time(hh, mm), BAKU)


BIRJA_NOW = at(2026, 11, 10, 9, 0)  # çərşənbə axşamı: bazar ertəsinin (9 noyabr) seansları
BIRJA_TITLE = "ABŞ birjalarında yüksəliş: S&P 500 indeksi 2,35% yüksəlib"
BIRJA_LEAD = ("9 noyabrda ABŞ birjalarında S&P 500 indeksi 2,35% yüksələrək 7 549,94 bənddə, Nasdaq Composite 2,74% "
              "yüksələrək 25 253,14 bənddə və Dow Jones 2,15% yüksələrək 52 389,75 bənddə bağlanıb.")
BIRJA_BODY = [
    "BIST 100 (İstanbul): 2,00% yüksələrək 11 712,67 bənddə bağlanıb",
    "IMOEX (Moskva): 0,27% enərək 2 470,07 bənddə bağlanıb",
    "DAX (Frankfurt): 1,73% yüksələrək 26 267,19 bənddə bağlanıb",
    "FTSE 100 (London): 1,02% yüksələrək 10 782,87 bənddə bağlanıb",
    "Nikkei 225 (Tokio): 2,33% yüksələrək 58 775,50 bənddə bağlanıb",
]


def imoex(target=D(2026, 11, 9)):
    return om.imoex_quote(om.parse_moex(fx("moex-imoex-2026-11-10.json")), target)


class HelperTest(unittest.TestCase):
    def test_days(self):
        self.assertEqual(om.prev_weekday(D(2026, 11, 10)), D(2026, 11, 9))
        self.assertEqual(om.prev_weekday(D(2026, 11, 14)), D(2026, 11, 13))
        self.assertEqual(om.prev_weekday(D(2026, 11, 9)), D(2026, 11, 6))
        self.assertFalse(om.is_working_day(D(2026, 11, 10)), "9 noyabrın köçürülmüş istirahət günü")
        self.assertFalse(om.is_working_day(SAT))
        self.assertTrue(om.is_working_day(D(2026, 11, 11)))
        self.assertTrue(om.is_working_day(D(2027, 11, 10)), "təqvimi olmayan ildə həftə içi iş günü sayılır")
        self.assertFalse(om.is_working_day(D(2027, 11, 9)), "Dövlət Bayrağı Günü")

    def test_numbers(self):
        self.assertEqual(om._numtext("99,506.0306"), 99506.0306)
        self.assertEqual(om._numtext("40,000,000 "), 40000000.0)
        self.assertIsNone(om._numtext("Elan ediləcək"))
        self.assertIsNone(om._num(True))
        self.assertIsNone(om._num(float("nan")))
        self.assertIsNone(om._num("1.7"))
        self.assertEqual(om._dmy("Yeniləndi 06.11.2026"), D(2026, 11, 6))
        self.assertIsNone(om._dmy("31.02.2026"))

    def test_leadership_is_never_published(self):
        item = {"title": "Sınaq", "lead": "Prezident İlham Əliyev sərəncam imzalayıb.", "body": [], "worth": True}
        self.assertEqual(om._guard(item), (None, "rəhbərliyin adı keçir: sahibin təsdiqi lazımdır"))
        item = {"title": "Sınaq", "lead": "S&P 500 indeksi yüksəlib.", "body": ["Mehriban Əliyeva"], "worth": True}
        self.assertIsNone(om._guard(item)[0])
        ok = {"title": "Sınaq", "lead": "S&P 500 indeksi yüksəlib.", "body": ["DAX enib"], "worth": True}
        self.assertEqual(om._guard(ok), (ok, ""))


class BirjaTest(unittest.TestCase):
    def test_real_close(self):
        quotes = om.parse_spark(fx(SPARK1), BIRJA_NOW)
        self.assertEqual(sorted(quotes), sorted(s for s, _, _ in om.INDICES if s != "IMOEX"))
        sp = quotes["^GSPC"]
        self.assertEqual((sp["value"], sp["pct"], sp["day"], sp["live"]), (7549.94, 2.35, D(2026, 11, 9), False))
        item, why = om.birja_item(quotes, imoex(), BIRJA_NOW)
        self.assertEqual((item["title"], item["lead"], item["body"]), (BIRJA_TITLE, BIRJA_LEAD, BIRJA_BODY))
        self.assertEqual((item["key"], item["slot"], item["topic"], item["worth"], why),
                         ("birja-2026-11-09", "09:00", "iqtisadiyyat", True, ""))
        self.assertEqual((item["credit"], item["link"]), ("Yahoo Finance və Moskva Birjası", om.BIRJA_LINK))
        self.assertLessEqual(len(item["title"]), 110)

    def test_running_and_later_sessions_are_labelled(self):
        now = at(2026, 11, 10, 13, 34)  # Avropa və İstanbul seansı gedir, Tokio 10 noyabrı bağlayıb
        item, _ = om.birja_item(om.parse_spark(fx(SPARK2), now), None, now)
        self.assertEqual(item["lead"], BIRJA_LEAD)
        self.assertEqual(item["body"], [
            "Nikkei 225 (Tokio): 10 noyabrda 2,87% yüksələrək 60 459,58 bənddə bağlanıb",
            "BIST 100 (İstanbul): seans davam edir, Bakı vaxtı ilə saat 13:19-da indeks 11 758,18 bənd olub, bu, əvvəlki "
            "bağlanışdan 0,39% yüksəkdir",
            "DAX (Frankfurt): seans davam edir, Bakı vaxtı ilə saat 13:19-da indeks 26 520,68 bənd olub, bu, əvvəlki "
            "bağlanışdan 0,97% yüksəkdir",
            "FTSE 100 (London): seans davam edir, Bakı vaxtı ilə saat 13:19-da indeks 10 812,40 bənd olub, bu, əvvəlki "
            "bağlanışdan 0,27% yüksəkdir",
        ])
        self.assertEqual(item["credit"], "Yahoo Finance")

    def test_garbage_and_inconsistent_quotes_are_dropped(self):
        self.assertEqual(om.parse_spark(b"<html>", BIRJA_NOW), {})
        self.assertEqual(om.parse_spark(b'{"spark":{"result":[{"symbol":"^GSPC","response":[{"meta":{}}]}]}}', BIRJA_NOW), {})
        self.assertEqual(om.parse_spark(b'{"spark":null}', BIRJA_NOW), {})

        def edit(meta):
            meta["^GSPC"]["regularMarketChangePercent"] = 9.9   # fulldayChange ilə uyğun gəlmir
            meta["^DJI"]["regularMarketPrice"] = 0
            meta["^IXIC"]["regularMarketTime"] = "dünən"
            meta["^FTSE"]["fulldayChange"] = 9000.0             # +500%: zibil
        quotes = om.parse_spark(spark(SPARK1, edit), BIRJA_NOW)
        self.assertEqual(sorted(quotes), ["XU100.IS", "^GDAXI", "^N225"])
        item, why = om.birja_item(quotes, imoex(), BIRJA_NOW)
        self.assertTrue(item["worth"])
        self.assertEqual(item["lead"], "9 noyabrda BIST 100 (İstanbul) indeksi 2,00% yüksələrək 11 712,67 bənddə bağlanıb.")
        self.assertEqual(item["title"], "İstanbul birjasında BIST 100 indeksi 2,00% yüksəlib")
        self.assertEqual(item["body"], BIRJA_BODY[1:3] + BIRJA_BODY[4:])

    def test_too_few_closes_is_not_news(self):
        quotes = om.parse_spark(fx(SPARK1), BIRJA_NOW)
        two = {k: quotes[k] for k in ("^GSPC", "^DJI")}
        item, why = om.birja_item(two, None, BIRJA_NOW)
        self.assertEqual((item["worth"], item["key"]), (False, "birja-2026-11-09"))
        self.assertEqual(why, "9 noyabr 2026 üçün 2 indeksin bağlanışı var, ən azı 3 lazımdır")
        self.assertEqual(item["why"], why)
        item, why = om.birja_item({}, None, BIRJA_NOW)
        self.assertFalse(item["worth"])

    def test_a_closed_exchange_is_left_out(self):
        quotes = om.parse_spark(fx(SPARK1), BIRJA_NOW)
        for sym in om.US:
            quotes[sym] = dict(quotes[sym], day=D(2026, 11, 6))  # bayram: son bağlanış cümənindir
        item, _ = om.birja_item(quotes, imoex(), BIRJA_NOW)
        self.assertEqual(item["closed"], ["S&P 500", "Nasdaq Composite", "Dow Jones"])
        self.assertNotIn("S&P", item["lead"] + " ".join(item["body"]))
        self.assertEqual(item["body"], BIRJA_BODY[1:])

    def test_imoex(self):
        rows = om.parse_moex(fx("moex-imoex-2026-11-10.json"))
        self.assertEqual(rows[-1], (D(2026, 11, 9), 2470.07))
        q = om.imoex_quote(rows, D(2026, 11, 9))
        self.assertEqual((q["value"], q["pct"], q["day"]), (2470.07, -0.27, D(2026, 11, 9)))
        self.assertIsNone(om.imoex_quote(rows, D(2026, 11, 4)), "bayram: o günün bağlanışı yoxdur")
        self.assertIsNone(om.imoex_quote(rows, D(2026, 11, 2)), "əvvəlki bağlanış yoxdur")
        self.assertIsNone(om.imoex_quote([(D(2026, 10, 20), 2400.0), (D(2026, 11, 9), 2470.07)], D(2026, 11, 9)), "köhnə")
        self.assertIsNone(om.imoex_quote([(D(2026, 11, 6), 1000.0), (D(2026, 11, 9), 2470.07)], D(2026, 11, 9)), "zibil")
        self.assertEqual(om.parse_moex(b"<html>"), [])
        self.assertEqual(om.parse_moex(b'{"history":{"columns":["TRADEDATE"],"data":[["2026-11-09"]]}}'), [])
        self.assertEqual(om.parse_moex(b'{"history":{"columns":["TRADEDATE","CLOSE"],"data":[["x",1],["2026-11-09",null],[1]]}}'), [])

    def test_window_days_and_done(self):
        for now in (at(2026, 11, 9, 9, 0), at(2026, 11, 8, 9, 0), at(2026, 11, 10, 8, 59), at(2026, 11, 10, 9, 40),
                    at(2026, 11, 10, 15, 0)):
            net = Net(routes())
            item, why = om.birja(now, net, set())
            self.assertIsNone(item, now)
            self.assertTrue(why)
            self.assertEqual(net.calls, [], now)
        net = Net(routes())
        self.assertEqual(om.birja(BIRJA_NOW, net, {"birja-2026-11-09"}), (None, "bu xəbər bu gün artıq işlənib"))
        self.assertEqual(net.calls, [])
        item, _ = om.birja(at(2026, 11, 10, 9, 39), net, set())
        self.assertEqual((item["title"], item["body"]), (BIRJA_TITLE, BIRJA_BODY))
        self.assertEqual(len(net.calls), 2)
        self.assertEqual(net.calls[0], (Q1, 15, None))
        self.assertIn("range=1d&interval=1d", Q1)
        self.assertTrue(net.calls[1][0].startswith("https://iss.moex.com/iss/history/"))
        self.assertIn("from=2026-10-26", net.calls[1][0])
        self.assertLessEqual(net.calls[1][1], 15)
        net = Net(routes())
        item, _ = om.birja(at(2026, 11, 14, 9, 0), net, set())  # şənbə: cümənin seansları (məlumat köhnədir)
        self.assertEqual((item["key"], item["worth"]), ("birja-2026-11-13", False))

    def test_fallback_and_failures(self):
        net = Net(routes(**{Q1: down(), Q2: fx(SPARK1)}))
        item, _ = om.birja(BIRJA_NOW, net, set())
        self.assertEqual((item["title"], item["body"]), (BIRJA_TITLE, BIRJA_BODY))
        self.assertEqual(net.urls()[:2], [Q1, Q2])
        self.assertEqual(len(net.calls), 3)
        net = Net(routes(**{Q1: b"<html>captcha</html>", Q2: fx(SPARK1), MOEX: down()}))
        item, _ = om.birja(BIRJA_NOW, net, set())
        self.assertEqual(item["body"], BIRJA_BODY[:1] + BIRJA_BODY[2:], "Moskva Birjası alınmasa IMOEX yazılmır")
        self.assertEqual(item["credit"], "Yahoo Finance")
        net = Net(routes(**{Q1: http(429), Q2: down()}))
        item, why = om.birja(BIRJA_NOW, net, set())
        self.assertEqual(why, "Yahoo Finance alınmadı: query1.finance.yahoo.com: HTTPError 429; query2.finance.yahoo.com: URLError")
        self.assertEqual((item["worth"], item["why"], item["key"]), (False, why, "birja-2026-11-09"))
        self.assertEqual(net.urls(), [Q1, Q2], "Yahoo alınmasa Moskva Birjasına sorğu getmir")


KRIPTO_BODY = [
    "XRP: 1,091 dollar (1,850 manat), son 24 saatda 5,65% ucuzlaşıb",
    "BNB: 686,24 dollar (1 166,61 manat), son 24 saatda 1,35% ucuzlaşıb",
    "Solana: 86,72 dollar (147,42 manat), son 24 saatda 2,77% ucuzlaşıb",
    "Dogecoin: 0,0699 dollar (0,1189 manat), son 24 saatda 1,65% ucuzlaşıb",
    "Toncoin: 1,035 dollar (1,760 manat), son 24 saatda 1,19% ucuzlaşıb",
]
QUIET_WHY = "iş günüdür, bitkoin (0,22%) və efir (0,25%) son 24 saatda 2%-dən az dəyişib"
SAT10 = at(2026, 11, 14, 10, 5)
WED10 = at(2026, 11, 11, 10, 5)


class KriptoTest(unittest.TestCase):
    def test_real_moved_day(self):
        now = at(2026, 11, 9, 22, 20)  # bazar ertəsi
        coins = om.parse_coingecko(fx(CG_MOVED))
        self.assertEqual(sorted(coins), sorted(c for c, _ in om.COINS))
        self.assertEqual((coins["bitcoin"]["usd"], coins["bitcoin"]["azn"], coins["bitcoin"]["pct"]), (74713.0, 127012.0, -1.39))
        self.assertEqual(coins["bitcoin"]["at"], datetime.datetime(2026, 11, 9, 18, 12, 45, tzinfo=datetime.timezone.utc))
        item, why = om.kripto_item(coins, now)
        self.assertEqual(item["title"], "Efir sutka ərzində 4,69% ucuzlaşıb, bitkoin 74 713 dollara enib")
        self.assertEqual(item["lead"], "CoinGecko saytının məlumatına görə, 9 noyabrda Bakı vaxtı ilə saat 22:12-də 1 bitkoin "
                                       "74 713 dollar (127 012 manat) olub, son 24 saatda qiyməti 1,39% azalıb. 1 efir 2 125,31 "
                                       "dollar (3 613,03 manat) olub, 4,69% ucuzlaşıb.")
        self.assertEqual(item["body"], KRIPTO_BODY)
        self.assertEqual((item["key"], item["slot"], item["worth"], item["credit"], why),
                         ("kripto-2026-11-09", "10:00", True, "CoinGecko", ""))

    def test_quiet_weekday_is_not_published_but_weekend_is(self):
        coins = om.parse_coingecko(fx(CG_QUIET))
        item, why = om.kripto_item(coins, at(2026, 11, 10, 13, 40))
        self.assertEqual((item["worth"], item["why"], why), (False, QUIET_WHY, QUIET_WHY))
        self.assertEqual(item["title"], "Bitkoin 74 353 dollara qalxıb: sutka ərzində 0,22% bahalaşıb")
        self.assertEqual(item["body"][0], "XRP: 1,087 dollar (1,850 manat), son 24 saatda 0,44% ucuzlaşıb")
        self.assertEqual(item["body"][4], "Toncoin: 1,091 dollar (1,850 manat), son 24 saatda 7,39% bahalaşıb")
        for now in (SAT10, at(2026, 11, 15, 10, 5)):  # şənbə, bazar
            coins = om.parse_coingecko(cg(CG_QUIET, now))
            item, why = om.kripto_item(coins, now)
            self.assertEqual((item["worth"], why), (True, ""), now)
            self.assertNotIn("why", item)

    def test_threshold_is_two_percent_for_bitcoin_or_ether(self):
        for b, e, worth in ((2.0, 0.1, True), (-2.0, 0.1, True), (0.1, -2.0, True), (1.99, -1.99, False), (0.0, 0.0, False)):
            def edit(doc, b=b, e=e):
                doc["bitcoin"]["usd_24h_change"], doc["ethereum"]["usd_24h_change"] = b, e
                doc["solana"]["usd_24h_change"] = 15.0  # başqa koinin dəyişməsi həddə təsir etmir
            item, _ = om.kripto_item(om.parse_coingecko(cg(CG_QUIET, WED10, edit)), WED10)
            self.assertEqual(item["worth"], worth, (b, e))
        both = lambda doc: (doc["bitcoin"].update(usd_24h_change=3.0), doc["ethereum"].update(usd_24h_change=5.5))
        item, _ = om.kripto_item(om.parse_coingecko(cg(CG_QUIET, WED10, both)), WED10)
        self.assertEqual(item["title"], "Bitkoin 3,00%, efir 5,50% bahalaşıb: 1 bitkoin 74 353 dollar")
        flat = lambda doc: (doc["bitcoin"].update(usd_24h_change=0.0), doc["ethereum"].update(usd_24h_change=0.0))
        item, _ = om.kripto_item(om.parse_coingecko(cg(CG_QUIET, SAT10, flat)), SAT10)
        self.assertEqual(item["title"], "Bitkoinin qiyməti sutka ərzində dəyişməyib: 1 bitkoin 74 353 dollar")
        self.assertIn("son 24 saatda qiyməti dəyişməyib. 1 efir 2 101,44 dollar (3 572,45 manat) olub, qiyməti dəyişməyib.",
                      item["lead"])

    def test_missing_stale_and_garbage(self):
        self.assertEqual(om.parse_coingecko(b"<html>"), {})
        self.assertEqual(om.parse_coingecko(b"[]"), {})
        self.assertEqual(om.kripto_item({}, SAT10), (None, "CoinGecko cavabında bitkoin və ya efirin qiyməti yoxdur"))

        def edit(doc):
            del doc["ethereum"]
            doc["ripple"]["azn"] = 3.0                # manat/dollar nisbəti 1,70 deyil
            doc["solana"]["usd"] = "85"
            doc["dogecoin"]["usd_24h_change"] = None
            doc["binancecoin"]["usd_24h_change"] = 250.0
        coins = om.parse_coingecko(cg(CG_QUIET, SAT10, edit))
        self.assertEqual(sorted(coins), ["bitcoin", "the-open-network"])
        self.assertIsNone(om.kripto_item(coins, SAT10)[0])
        item, why = om.kripto_item(om.parse_coingecko(fx(CG_QUIET)), SAT10)  # 4 gün əvvəlki qiymət
        self.assertEqual((item, why), (None, "CoinGecko-da bitkoinin qiyməti köhnədir (10 noyabr 2026 13:34)"))
        old = lambda doc: doc["solana"].update(last_updated_at=int((SAT10 - datetime.timedelta(hours=5)).timestamp()))
        item, _ = om.kripto_item(om.parse_coingecko(cg(CG_QUIET, SAT10, old)), SAT10)
        self.assertEqual([line.split(":")[0] for line in item["body"]], ["XRP", "BNB", "Dogecoin", "Toncoin"])

    def test_window_done_retry_and_failures(self):
        fresh = cg(CG_QUIET, SAT10)
        for now in (at(2026, 11, 14, 9, 59), at(2026, 11, 14, 10, 40), at(2026, 11, 14, 22, 0)):
            net = Net({om.CG_URL: fresh})
            self.assertIsNone(om.kripto(now, net, set())[0])
            self.assertEqual(net.calls, [], now)
        net = Net({om.CG_URL: fresh})
        self.assertEqual(om.kripto(SAT10, net, {"kripto-2026-11-14"}), (None, "bu xəbər bu gün artıq işlənib"))
        self.assertEqual(net.calls, [])
        item, _ = om.kripto(SAT10, net, set())
        self.assertEqual((item["key"], item["worth"]), ("kripto-2026-11-14", True))
        self.assertEqual(net.calls, [(om.CG_URL, 15, None)])
        self.assertIn("ids=bitcoin,ethereum,", om.CG_URL)
        self.assertIn("vs_currencies=usd,azn", om.CG_URL)
        slept = []
        with patch.object(om, "_sleep", slept.append):
            net = Net({om.CG_URL: [http(429), fresh]})
            item, _ = om.kripto(SAT10, net, set())
            self.assertEqual((item["worth"], len(net.calls), slept), (True, 2, [2]))
            net = Net({om.CG_URL: http(429)})
            item, why = om.kripto(SAT10, net, set())
            self.assertEqual((item["worth"], why, len(net.calls)), (False, "CoinGecko alınmadı: HTTPError 429", 2))
            net = Net({om.CG_URL: http(500)})
            item, why = om.kripto(SAT10, net, set())
            self.assertEqual((item["key"], item["worth"], item["why"], len(net.calls)),
                             ("kripto-2026-11-14", False, "CoinGecko alınmadı: HTTPError 500", 1))
        net = Net({om.CG_URL: fx(CG_QUIET)})  # köhnə cavab: xəbər yoxdur, açar qayıdır (o gün yenə sorğu getmir)
        item, why = om.kripto(SAT10, net, set())
        self.assertEqual((item["worth"], item["body"]), (False, []))
        self.assertTrue(why.startswith("CoinGecko-da bitkoinin qiyməti köhnədir"))
        net = Net({om.CG_URL: cg(CG_QUIET, WED10)})
        item, why = om.kripto(WED10, net, set())
        self.assertEqual((item["worth"], why), (False, QUIET_WHY))


BANK_DAY = D(2026, 11, 6)
BANK_NOW = at(2026, 11, 6, 10, 30)
BANK_LEAD = ("Dörd bankın (ABB, Unibank, Xalq Bank və AccessBank) saytlarında 6 noyabr üçün göstərilən nağd məzənnələrə görə "
             "ABŞ dolları 1,6900–1,6970 manata alınır, 1,7005–1,7025 manata satılır. Dolları ən baha ABB (1,6970 manat), ən "
             "ucuz Xalq Bank (1,6900 manat) alır; ən ucuz Unibank və Xalq Bank (1,7005 manat), ən baha AccessBank (1,7025 "
             "manat) satır. Avro 1,8561–1,8770 manata alınır, 1,9174–1,9230 manata satılır. Avronu ən baha Unibank (1,8770 "
             "manat), ən ucuz AccessBank (1,8561 manat) alır; ən ucuz Unibank (1,9174 manat), ən baha Xalq Bank (1,9230 "
             "manat) satır.")
BANK_BODY = [
    "ABB: dolları 1,6970 manata alır, 1,7020 manata satır; avronu 1,8656 manata alır, 1,9208 manata satır",
    "Unibank: dolları 1,6940 manata alır, 1,7005 manata satır; avronu 1,8770 manata alır, 1,9174 manata satır",
    "Xalq Bank: dolları 1,6900 manata alır, 1,7005 manata satır; avronu 1,8760 manata alır, 1,9230 manata satır",
    "AccessBank: dolları 1,6920 manata alır, 1,7025 manata satır; avronu 1,8561 manata alır, 1,9227 manata satır",
]
BANK_TITLES = ["Banklarda dollar 1,7005–1,7025 manata satılır",
               "Banklarda nağd dollar 1,6900–1,6970 manata alınır, 1,7005–1,7025 manata satılır",
               "Dolları ən ucuz Unibank və Xalq Bank satır: 1,7005 manat"]


def bank_results(*data):
    """bank_fetch nəticəsi kimi: (ad, tarix, dollar, avro)."""
    return [(n, "https://bank/" + n, {"date": day, "USD": usd, "EUR": eur}, "", 1000) for n, day, usd, eur in data]


class BankTest(unittest.TestCase):
    def test_real_pages(self):
        want = {"ABB": ((1.697, 1.702), (1.8656, 1.9208)), "Unibank": ((1.694, 1.7005), (1.877, 1.9174)),
                "Xalq Bank": ((1.69, 1.7005), (1.876, 1.923)), "AccessBank": ((1.692, 1.7025), (1.8561, 1.9227))}
        for name, _, _, parse in om.BANKS:
            data = parse(fx(BANK_FIX[name]))
            self.assertEqual((data["date"], data["USD"], data["EUR"]), (BANK_DAY,) + want[name], name)
        html = om.parse_abb(fx("abb-2026-11-10.html.txt"))  # HTML səhifənin içindəki qaçırılmış nüsxə
        self.assertEqual((html["date"], html["USD"], html["EUR"]), (BANK_DAY,) + want["ABB"])

    def test_real_item(self):
        net = Net(routes())
        item, why = om.banks(BANK_NOW, net, set())
        self.assertEqual((item["lead"], item["body"]), (BANK_LEAD, BANK_BODY))
        self.assertEqual(item["title"], BANK_TITLES[BANK_DAY.toordinal() % 3])
        self.assertEqual((item["key"], item["slot"], item["worth"], item["topic"], why),
                         ("bank-mezenne-2026-11-06", "10:30", True, "iqtisadiyyat", ""))
        self.assertEqual((item["credit"], item["link"]), ("ABB, Unibank, Xalq Bank və AccessBank", BANK_URL["ABB"]))
        self.assertEqual(net.urls(), [b[1] for b in om.BANKS], "hər banka bir sorğu")
        self.assertEqual(net.calls[0][2], {"RSC": "1"})
        self.assertTrue(all(t <= 15 for _, t, _ in net.calls))
        seen = {om.bank_item(om.bank_fetch(Net(routes())), BANK_DAY + datetime.timedelta(days=k))[0]["title"] for k in (0,)}
        self.assertTrue(seen <= set(BANK_TITLES))
        for title in BANK_TITLES:
            self.assertLessEqual(len(title), 110)

    def test_only_banks_showing_the_day_count(self):
        results = om.bank_fetch(Net(routes()))
        item, why = om.bank_item(results, D(2026, 11, 11))  # səhifələr hələ 6 noyabrı göstərir
        self.assertEqual((item["worth"], item["key"], item["body"]), (False, "bank-mezenne-2026-11-11", []))
        self.assertTrue(why.startswith("11 noyabr 2026 tarixli nağd məzənnə 0 bankda var, ən azı 2 lazımdır (ABB: məzənnə "
                                       "6 noyabr 2026 tarixlidir; Unibank: məzənnə 6 noyabr 2026 tarixlidir;"), why)
        mixed = bank_results(("A Bank", BANK_DAY, (1.69, 1.70), None), ("B Bank", D(2026, 11, 5), (1.60, 1.79), (1.8, 1.9)),
                             ("C Bank", BANK_DAY, (1.695, 1.70), (1.87, 1.92)), ("D Bank", None, (1.61, 1.78), None),
                             ("E Bank", BANK_DAY, None, (1.87, 1.92)))
        item, _ = om.bank_item(mixed, BANK_DAY)
        self.assertEqual(item["lead"], "İki bankın (A Bank və C Bank) saytlarında 6 noyabr üçün göstərilən nağd məzənnələrə görə "
                                       "ABŞ dolları 1,6900–1,6950 manata alınır, 1,7000 manata satılır. Dolları ən baha C Bank "
                                       "(1,6950 manat), ən ucuz A Bank (1,6900 manat) alır; bankların hamısı 1,7000 manata satır.")
        self.assertEqual(item["body"], ["A Bank: dolları 1,6900 manata alır, 1,7000 manata satır",
                                        "C Bank: dolları 1,6950 manata alır, 1,7000 manata satır; avronu 1,8700 manata alır, "
                                        "1,9200 manata satır"])
        self.assertEqual(item["left_out"], ["B Bank: məzənnə 5 noyabr 2026 tarixlidir", "D Bank: məzənnənin tarixi oxunmadı",
                                            "E Bank: dolların nağd məzənnəsi oxunmadı"])
        same = bank_results(("A Bank", BANK_DAY, (1.69, 1.70), (1.87, 1.92)), ("C Bank", BANK_DAY, (1.69, 1.70), (1.87, 1.93)))
        item, _ = om.bank_item(same, BANK_DAY)
        self.assertIn("ABŞ dolları 1,6900 manata alınır, 1,7000 manata satılır. Dolları bankların hamısı 1,6900 manata alır, "
                      "1,7000 manata satır. Avro 1,8700 manata alınır, 1,9200–1,9300 manata satılır. Avronu bankların hamısı "
                      "1,8700 manata alır; ən ucuz A Bank (1,9200 manat), ən baha C Bank (1,9300 manat) satır.", item["lead"])
        one = bank_results(("A Bank", BANK_DAY, (1.69, 1.70), None))
        self.assertFalse(om.bank_item(one, BANK_DAY)[0]["worth"])

    def test_broken_sites_and_garbage(self):
        net = Net(routes(**{BANK_URL["ABB"]: down(), BANK_URL["Unibank"]: b"<html>texniki işlər</html>"}))
        item, _ = om.banks(BANK_NOW, net, set())
        self.assertTrue(item["lead"].startswith("İki bankın (Xalq Bank və AccessBank) saytlarında 6 noyabr üçün"), item["lead"])
        self.assertEqual(item["left_out"], ["ABB: sayt açılmadı (URLError)", "Unibank: məzənnə oxunmadı"])
        self.assertEqual(item["credit"], "Xalq Bank və AccessBank")
        self.assertEqual(len(net.calls), 4)
        net = Net()  # heç bir sayt açılmır
        item, why = om.banks(BANK_NOW, net, set())
        self.assertEqual((item["worth"], item["key"], len(net.calls)), (False, "bank-mezenne-2026-11-06", 4))
        for name, _, _, parse in om.BANKS:
            data = parse(b"<html><table><tr><td>USD</td></tr></table></html>")
            self.assertFalse(data and (data.get("date") or data.get("USD") or data.get("EUR")), name)
        self.assertIsNone(om._pair(1.2, 1.7, "USD"), "aralıqdan kənar")
        self.assertIsNone(om._pair(1.70, 1.69, "USD"), "alış satışdan bahadır")
        self.assertIsNone(om._pair("1.69", 1.70, "USD"))
        self.assertEqual(om._pair(1.69, 1.70, "USD"), (1.69, 1.70))

    def test_working_days_window_and_done(self):
        for now in (at(2026, 11, 7, 10, 30), at(2026, 11, 10, 10, 30), at(2026, 11, 6, 10, 29), at(2026, 11, 6, 11, 10)):
            net = Net(routes())
            self.assertIsNone(om.banks(now, net, set())[0], now)
            self.assertEqual(net.calls, [], now)
        net = Net(routes())
        self.assertEqual(om.banks(BANK_NOW, net, {"bank-mezenne-2026-11-06"}), (None, "bu xəbər bu gün artıq işlənib"))
        self.assertEqual(net.calls, [])
        item, why = om.banks(at(2026, 11, 11, 10, 45), net, set())  # iş günü, saytlar köhnə tarixlidir
        self.assertEqual((item["worth"], item["key"], len(net.calls)), (False, "bank-mezenne-2026-11-11", 4))


AMB_TITLE = "Mərkəzi Bank 70 milyon manatlıq notlar yerləşdirib: 28 günlük 6,38%, 168 günlük 6,57% orta gəlirliliklə"
AMB_LEAD = ("4 noyabr 2026-cı ildə Bakı Fond Birjasında Azərbaycan Mərkəzi Bankının (AMB) 28 və 168 günlük notlarının "
            "yerləşdirilməsi üzrə hərraclar keçirilib. Hərraca çıxarılan 70 000 000 manatlıq notların hamısı yerləşdirilib.")
AMB_BODY = [
    "28 günlük notlar (AZ2736024707): 40 000 000 manat yerləşdirilib; 6 investorun sifarişlərinin ümumi həcmi 83 200 000 "
    "manat olub; orta çəkili gəlirlilik 6,38%, kəsmə gəlirliliyi 6,43%; ödəniş tarixi 2 dekabr 2026",
    "168 günlük notlar (AZ2738024705): 30 000 000 manat yerləşdirilib; 5 investorun sifarişlərinin ümumi həcmi 41 200 000 "
    "manat olub; orta çəkili gəlirlilik 6,57%, kəsmə gəlirliliyi 6,59%; ödəniş tarixi 21 aprel 2027",
]
ONE_TITLE = "Mərkəzi Bank 40 milyon manatlıq 28 günlük notları 6,38% orta gəlirliliklə yerləşdirib"
BFB_NOON, BFB_EVE = day_at(WED, 13, 30), day_at(WED, 18, 30)


def auctions(day):
    rows = om.state_rows(om.parse_bfb_home(HOME), day)
    return [(r, om.parse_bfb_detail(fx(BFB_FIX[r["isin"]]))) for r in rows]


class BfbTest(unittest.TestCase):
    def test_real_table(self):
        rows = om.parse_bfb_home(HOME)
        self.assertEqual(len(rows), 15)
        self.assertEqual(max(r["day"] for r in rows), D(2026, 11, 6), "gələcək yerləşdirmələr («Kupon %» cədvəli) oxunmur")
        self.assertEqual([(r["issuer"], r["isin"], r["offered"]) for r in om.state_rows(rows, WED)],
                         [("ARMB", N168, 30000000.0), ("ARMB", N28, 40000000.0)])
        self.assertEqual([r["isin"] for r in om.state_rows(rows, TUE)], [MN1080])
        self.assertEqual(om.state_rows(rows, FRI), [], "özəl şirkətin istiqrazı dövlət qiymətli kağızı deyil")
        self.assertEqual([r["isin"] for r in om.state_rows(rows + rows, THU)], [N84, N252], "İSİN-ə görə təkrarsız")
        self.assertEqual(om.parse_bfb_home(b"<html><table><tr><td>x</td></tr></table></html>"), [])
        self.assertEqual(om.parse_bfb_home(b""), [])

    def test_real_auction_pages(self):
        d = om.parse_bfb_detail(fx(BFB_FIX[N28]))
        self.assertEqual((d["day"], d["isin"], d["term"], d["offered"], d["placed"], d["bids"], d["investors"], d["orders"]),
                         (WED, N28, 28, 40000000.0, 40000000.0, 83200000.0, 6, 6))
        self.assertEqual((d["wavg"], d["cut"], d["maturity"], d["coupon"]),
                         ((99506.0306, 6.38), (99502.3776, 6.43), D(2026, 12, 2), None))
        d = om.parse_bfb_detail(fx(BFB_FIX[MN1080]))
        self.assertEqual((d["day"], d["isin"], d["term"], d["offered"], d["placed"], d["bids"], d["investors"], d["orders"]),
                         (TUE, MN1080, 1080, 200000000.0, 34428100.0, 67157300.0, 8, 12))
        self.assertEqual((d["wavg"], d["cut"], d["maturity"], d["coupon"]),
                         ((99.3366, 7.25), (99.3366, 7.25), D(2029, 11, 3), 7.0))
        self.assertIsNone(om.parse_bfb_detail(b"<html>404</html>"))
        self.assertIsNone(om.parse_bfb_detail(b'<div class="text_editor"><table><tr><td>Emitent</td><td>X</td></tr></table></figure>'))
        broken = fx(BFB_FIX[N28]).replace(b"AZ2736024707", b"Prezident")
        self.assertIsNone(om.parse_bfb_detail(broken), "İSİN yerində başqa mətn")

    def test_real_items(self):
        item, why = om.bfb_item(WED, auctions(WED))
        self.assertEqual((item["title"], item["lead"], item["body"]), (AMB_TITLE, AMB_LEAD, AMB_BODY))
        self.assertEqual((item["key"], item["worth"], item["credit"], item["link"], item["topic"], why),
                         ("bfb-herrac-2026-11-04", True, "Bakı Fond Birjası", LINK[N168], "iqtisadiyyat", ""))
        self.assertLessEqual(len(item["title"]), 110)
        item, _ = om.bfb_item(THU, auctions(THU))
        self.assertEqual(item["title"], "Mərkəzi Bank 60 milyon manatlıq notlar yerləşdirib: 84 günlük 6,52%, 252 günlük 6,67% "
                                        "orta gəlirliliklə")
        item, _ = om.bfb_item(TUE, auctions(TUE))
        self.assertEqual(item["title"], "Maliyyə Nazirliyi 1080 günlük istiqrazların 34,4 milyon manatlığını 7,25% orta "
                                        "gəlirliliklə yerləşdirib")
        self.assertEqual(item["lead"], "3 noyabr 2026-cı ildə Bakı Fond Birjasında Maliyyə Nazirliyinin 1080 günlük dövlət "
                                       "istiqrazlarının yerləşdirilməsi üzrə hərrac keçirilib. 200 000 000 manatlıq buraxılışdan "
                                       "34 428 100 manatlıq istiqraz yerləşdirilib, orta çəkili gəlirlilik 7,25% olub.")
        self.assertEqual(item["body"], ["1080 günlük istiqrazlar (AZ0201240105): buraxılış həcmi 200 000 000 manat, yerləşdirilib "
                                        "34 428 100 manat; 8 investorun sifarişlərinin ümumi həcmi 67 157 300 manat olub; orta "
                                        "çəkili gəlirlilik 7,25%, kəsmə gəlirliliyi 7,25%; illik faiz dərəcəsi 7%; ödəmə tarixi "
                                        "3 noyabr 2029"])
        self.assertLessEqual(len(item["title"]), 110)
        self.assertEqual(om.bfb_item(WED, [])[0], None)

    def test_partly_placed_and_empty_auctions(self):
        (r1, d1), (r2, d2) = auctions(WED)
        part = dict(d1, placed=12500000.0)
        item, _ = om.bfb_item(WED, [(r1, part), (r2, d2)])
        self.assertEqual(item["title"], "Mərkəzi Bank 52,5 milyon manatlıq notlar yerləşdirib: 28 günlük 6,38%, 168 günlük 6,57% "
                                        "orta gəlirliliklə")
        self.assertIn("Hərraca çıxarılan 70 000 000 manatlıq notlardan 52 500 000 manatlığı yerləşdirilib.", item["lead"])
        item, _ = om.bfb_item(WED, [(r2, d2)])
        self.assertEqual(item["title"], ONE_TITLE)
        self.assertIn("28 günlük notlarının yerləşdirilməsi üzrə hərrac keçirilib.", item["lead"])

    def test_flow_windows_and_done(self):
        net = Net(routes())
        item, _ = om.bfb(BFB_NOON, net, set())
        self.assertEqual((item["title"], item["lead"], item["body"], item["slot"]), (AMB_TITLE, AMB_LEAD, AMB_BODY, "13:30"))
        self.assertEqual(net.urls(), [om.BFB_HOME, LINK[N168], LINK[N28]])
        self.assertEqual(om.bfb(BFB_EVE, Net(routes()), set())[0]["slot"], "18:30")
        for now in (day_at(MON, 13, 30), day_at(FRI, 18, 30), day_at(WED, 13, 29), day_at(WED, 13, 40), day_at(WED, 18, 29),
                    day_at(WED, 19, 10), at(2026, 11, 10, 13, 30)):  # 10 noyabr: çərşənbə axşamı, amma iş günü deyil
            net = Net(routes())
            self.assertIsNone(om.bfb(now, net, set())[0], now)
            self.assertEqual(net.calls, [], now)
        net = Net(routes())
        self.assertEqual(om.bfb(BFB_NOON, net, {"bfb-herrac-2026-11-04"}), (None, "bu xəbər bu gün artıq işlənib"))
        self.assertEqual(net.calls, [])

    def test_no_result_yet_is_checked_again_in_the_evening(self):
        net = Net(routes())
        item, why = om.bfb(at(2026, 11, 12, 13, 30), net, set())  # cədvəldə 12 noyabr sətri yoxdur
        self.assertEqual((item, why), (None, "bfb.az-da 12 noyabr 2026 tarixli dövlət qiymətli kağızı yerləşdirməsi yoxdur "
                                             "(axşam yenə yoxlanacaq)"))
        self.assertEqual(net.urls(), [om.BFB_HOME])
        item, why = om.bfb(at(2026, 11, 12, 18, 30), net, set())
        self.assertEqual((item["worth"], item["key"], item["why"]),
                         (False, "bfb-herrac-2026-11-12", "bfb.az-da 12 noyabr 2026 tarixli dövlət qiymətli kağızı yerləşdirməsi yoxdur"))
        self.assertEqual(len(net.calls), 2)

    def test_failures(self):
        net = Net(routes(**{om.BFB_HOME: down()}))
        self.assertEqual(om.bfb(BFB_NOON, net, set()), (None, "bfb.az alınmadı: URLError (axşam yenə yoxlanacaq)"))
        item, why = om.bfb(BFB_EVE, net, set())
        self.assertEqual((item["worth"], item["key"], why), (False, "bfb-herrac-2026-11-04", "bfb.az alınmadı: URLError"))
        self.assertEqual(len(net.calls), 2)
        net = Net(routes(**{LINK[N168]: down()}))
        item, why = om.bfb(BFB_NOON, net, set())
        self.assertEqual((item, why), (None, "hərracın səhifəsi oxunmadı: AZ2738024705: səhifə açılmadı (URLError) (axşam yenə "
                                             "yoxlanacaq)"))
        item, _ = om.bfb(BFB_EVE, net, set())
        self.assertEqual((item["title"], item["body"], item["worth"]), (ONE_TITLE, AMB_BODY[:1], True))
        net = Net(routes(**{LINK[N168]: fx(BFB_FIX[N252]), LINK[N28]: b"<html>404</html>"}))  # başqa hərracın səhifəsi
        item, why = om.bfb(BFB_EVE, net, set())
        self.assertEqual((item["worth"], item["body"]), (False, []))
        self.assertEqual(why, "hərracın səhifəsi oxunmadı: AZ2738024705: səhifə başqa hərracındır (AZ2737024706); "
                              "AZ2736024707: səhifədə hərracın nəticəsi oxunmadı")
        net = Net(routes(**{om.BFB_HOME: b"<html>texniki işlər</html>"}))
        self.assertFalse(om.bfb(BFB_EVE, net, set())[0]["worth"])


def run_day(day, net, minutes=10):
    """Canlı dövrə: `minutes` dəqiqədən bir items(), hər qayıdan açar `done`-a yazılır. Qaytarır bütün xəbərləri."""
    done, out = set(), []
    for k in range(0, 24 * 60, minutes):
        got = om.items(ROOT, day_at(day, k // 60, k % 60), net, done)
        out += got
        done |= {i["key"] for i in got}
    return out


class ItemsTest(unittest.TestCase):
    def test_a_normal_day(self):
        net = Net(routes(**{om.CG_URL: cg(CG_MOVED, day_at(WED, 10, 0)), Q1: spark(SPARK1, lambda meta: [
            m.update(regularMarketTime=m["regularMarketTime"] - 6 * 86400) for m in meta.values()])}))
        with patch.object(om, "_sleep", lambda s: None):
            got = run_day(WED, net)
        self.assertEqual([(i["key"], i["worth"]) for i in got],
                         [("birja-2026-11-03", True), ("kripto-2026-11-04", True), ("bank-mezenne-2026-11-04", False),
                          ("bfb-herrac-2026-11-04", True)])
        self.assertEqual(len(net.calls), 2 + 1 + 4 + 3)
        for item in got:
            for key in ("kind", "key", "title", "lead", "body", "credit", "link", "topic", "slot", "worth"):
                self.assertIn(key, item, item["key"])
            self.assertEqual(item["topic"], "iqtisadiyyat")
            self.assertTrue(item["worth"] or item["why"], item["key"])
            self.assertFalse(item["title"].endswith("."), item["title"])
            self.assertTrue(ox.render(item))
        self.assertEqual(got[0]["lead"], BIRJA_LEAD.replace("9 noyabrda", "3 noyabrda"))

    def test_request_budget_on_the_worst_day(self):
        """Gündə ən çox 15 sorğu: Yahoo-nun birinci ünvanı işləmir, CoinGecko 429 verir, BFB-nin bir səhifəsi açılmır."""
        net = Net(routes(**{Q1: down(), Q2: fx(SPARK1), om.CG_URL: [http(429), fx(CG_QUIET)], LINK[N168]: down()}))
        with patch.object(om, "_sleep", lambda s: None):
            got = run_day(WED, net)
        self.assertEqual(len(net.calls), 15)
        self.assertEqual(sorted(i["key"] for i in got),
                         ["bank-mezenne-2026-11-04", "bfb-herrac-2026-11-04", "birja-2026-11-03", "kripto-2026-11-04"])
        self.assertEqual([i["title"] for i in got if i["worth"]], [ONE_TITLE])
        net = Net()  # heç nə işləmir: xəta atılmır, hər xəbər bir dəfə yoxlanır
        with patch.object(om, "_sleep", lambda s: None):
            got = run_day(WED, net)
        self.assertEqual([(i["key"], i["worth"]) for i in got],
                         [("birja-2026-11-03", False), ("kripto-2026-11-04", False), ("bank-mezenne-2026-11-04", False),
                          ("bfb-herrac-2026-11-04", False)])
        self.assertEqual(len(net.calls), 2 + 1 + 4 + 2)

    def test_quiet_times_send_nothing(self):
        for day in (SUN, MON, WED):
            for hh, mm in ((0, 0), (8, 59), (9, 40), (11, 10), (13, 40), (19, 10), (23, 59)):
                if (day, hh) == (MON, 9):
                    continue
                net = Net(routes())
                self.assertEqual(om.items(ROOT, day_at(day, hh, mm), net), [], (day, hh, mm))
                self.assertEqual(net.calls, [], (day, hh, mm))
        utc = datetime.datetime(2026, 11, 14, 6, 5, tzinfo=datetime.timezone.utc)  # 10:05 Bakı, şənbə
        got = om.items(ROOT, utc, Net({om.CG_URL: cg(CG_QUIET, SAT10)}))
        self.assertEqual([(i["key"], i["worth"]) for i in got], [("kripto-2026-11-14", True)])

    def test_items_never_raises(self):
        def boom(url, timeout=None, headers=None):
            raise RuntimeError("partladı")
        for hh, mm in ((9, 0), (10, 0), (10, 30), (13, 30), (18, 30)):
            got = om.items(ROOT, day_at(WED, hh, mm), boom, None)
            self.assertTrue(all(not i["worth"] and i["why"] for i in got), (hh, mm))
        junk = Net({"https://*": b"\xff\xfe<<<"})
        with patch.object(om, "_sleep", lambda s: None):
            self.assertTrue(all(not i["worth"] for i in run_day(WED, junk)))

    def test_sinaq(self):
        net = Net(routes())
        with patch.object(om, "_sleep", lambda s: None):
            md = "\n".join(om.sinaq(ROOT, at(2026, 11, 11, 12, 0), net))
        self.assertNotIn("Sınaq xətası", md)
        for title, _ in om.PARTS:
            self.assertIn("## " + title, md)
        self.assertIn("### " + BANK_TITLES[BANK_DAY.toordinal() % 3], md)
        self.assertIn("**Son real hal: 6 noyabr 2026**", md)
        self.assertIn("- " + BANK_BODY[0], md)
        self.assertIn("**Son real hal: 5 noyabr 2026**", md)
        self.assertIn("### Mərkəzi Bank 60 milyon manatlıq notlar yerləşdirib", md)
        self.assertIn("**Son real hal: 3 noyabr 2026**", md)
        self.assertIn("### Maliyyə Nazirliyi 1080 günlük istiqrazların 34,4 milyon manatlığını", md)
        self.assertIn("✅ Dərc olunardı", md)
        self.assertIn("⏭ Dərc olunmazdı", md)
        self.assertIn("- Yelo Bank: sayt açılmadı (URLError); onsuz da siyahıya salınmır: saytda məzənnənin tarixi yoxdur", md)
        self.assertLessEqual(len(net.calls), 20)
        self.assertEqual(len(net.calls), len(set(net.urls())), "sınaqda eyni ünvana iki sorğu getmir")
        self.assertIn(f"Sınaqda {len(net.calls)} sorğu getdi", md)
        with patch.object(om, "_sleep", lambda s: None):
            md = "\n".join(om.sinaq(ROOT, at(2026, 11, 11, 12, 0), Net()))
        self.assertNotIn("Sınaq xətası", md)
        self.assertIn("Yahoo Finance alınmadı", md)
        self.assertIn("CoinGecko alınmadı", md)
        self.assertIn("bfb.az alınmadı", md)

    def test_sinaq_shows_todays_items_in_their_windows(self):
        net = Net(routes(**{om.CG_URL: cg(CG_MOVED, at(2026, 11, 4, 10, 0))}))
        with patch.object(om, "_sleep", lambda s: None):
            md = "\n".join(om.sinaq(ROOT, at(2026, 11, 4, 10, 5), net))
        self.assertIn("**Bu gün (4 noyabr 2026, 10:05):**", md)
        self.assertIn("### Efir sutka ərzində 4,69% ucuzlaşıb, bitkoin 74 713 dollara enib", md)
        with patch.object(om, "_sleep", lambda s: None):
            md = "\n".join(om.sinaq(ROOT, BFB_NOON, Net(routes())))
        self.assertIn("### " + AMB_TITLE, md)


if __name__ == "__main__":
    unittest.main()
