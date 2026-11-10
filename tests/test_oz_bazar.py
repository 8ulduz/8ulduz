"""Öz xəbər: bazar şablonları (oz_bazar.py). Şəbəkə yoxdur: cbar.az və GitHub saxtadır.
Real hal tests/fixtures/oz_bazar-dadır:
- AMB-nin 30 oktyabr, 5 və 6 noyabr 2026 bülletenləri (cbar.az, yalnız boş sətirlər silinib);
- main-dəki data/markets.json-un üç nüsxəsi: e627320de (31.10 06:45Z), a420b2862 (06.11 05:31Z), 1e493a2b5 (07.11 06:54Z)."""
import contextlib
import datetime
import io
import json
import pathlib
import re
import tempfile
import unittest
from unittest.mock import patch

import oz_bazar as ob
import oz_xeber as ox

ROOT = pathlib.Path(__file__).resolve().parent.parent
FIX = pathlib.Path(__file__).resolve().parent / "fixtures" / "oz_bazar"
BAKU = ox.BAKU
D = datetime.date
SHA31 = "e627320de5ce15a710009425323d334c710345df"
SHA06 = "a420b2862a9ba2044258c0eb37ff4c8d167bfc6a"
SHA07 = "1e493a2b5dad882535a134089de7a066bb3ef082"
FRI = datetime.datetime(2026, 11, 6, 9, 40, tzinfo=BAKU)
SAT = datetime.datetime(2026, 11, 7, 11, 0, tzinfo=BAKU)
TUE = datetime.datetime(2026, 11, 10, 10, 0, tzinfo=BAKU)  # 10 noyabr: AMB yeni bülleten verməyib
BULLETINS = {D(2026, 10, 30): "amb-2026-10-30.xml", D(2026, 11, 5): "amb-2026-11-05.xml", D(2026, 11, 6): "amb-2026-11-06.xml"}
SNAPS = {SHA31: "markets-2026-10-31T0645Z.json", SHA06: "markets-2026-11-06T0531Z.json", SHA07: "markets-2026-11-07T0654Z.json"}


def fx(name):
    return (FIX / name).read_bytes()


def mj(name):
    return json.loads(fx(name).decode("utf-8"))


class FakeNet:
    """cbar.az və GitHub-un saxtası; hər sorğu qeyd olunur.
    AMB, cbar.az kimi: istənən gün qüvvədə olan bülleten, yəni o gün və ya ondan əvvəlki son bülleten.
    GitHub: commits API `until`-a qədərki son nüsxənin sha-sını verir, raw isə nüsxənin özünü."""
    def __init__(self, bulletins=None, snaps=None):
        self.bulletins = {d: fx(n) for d, n in (BULLETINS if bulletins is None else bulletins).items()}
        self.snaps = {s: fx(n) for s, n in (SNAPS if snaps is None else snaps).items()}
        self.calls, self.headers = [], []

    def __call__(self, url, timeout=None, headers=None, data=None):
        self.calls.append(url)
        self.headers.append(headers or {})
        m = re.search(r"/currencies/(\d\d)\.(\d\d)\.(\d{4})\.xml$", url)
        if m:
            day = D(int(m.group(3)), int(m.group(2)), int(m.group(1)))
            have = [d for d in self.bulletins if d <= day]
            if not have:
                raise OSError("bülleten yoxdur")
            return self.bulletins[max(have)]
        m = re.search(r"/commits\?path=data/markets\.json&until=(\d{4}-\d\d-\d\dT\d\d:\d\d:\d\dZ)&per_page=1$", url)
        if m:
            until = datetime.datetime.strptime(m.group(1), "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=datetime.timezone.utc)
            dated = sorted((datetime.datetime.fromisoformat(json.loads(raw)["updatedAt"]), sha) for sha, raw in self.snaps.items())
            older = [sha for t, sha in dated if t <= until]
            return json.dumps([{"sha": older[-1]}] if older else []).encode("utf-8")
        m = re.search(r"^https://raw\.githubusercontent\.com/8ulduz/8ulduz/([0-9a-f]{40})/data/markets\.json$", url)
        if m and m.group(1) in self.snaps:
            return self.snaps[m.group(1)]
        raise OSError("saxta şəbəkədə yoxdur: " + url)


def make_root(test, markets_name=None, markets=None):
    tmp = tempfile.TemporaryDirectory()
    test.addCleanup(tmp.cleanup)
    data = pathlib.Path(tmp.name) / "data"
    data.mkdir()
    if markets_name or markets is not None:
        doc = markets if markets is not None else mj(markets_name)
        (data / "markets.json").write_text(json.dumps(doc, ensure_ascii=False), encoding="utf-8")
    return pathlib.Path(tmp.name)


def metal_bulletin(day, xau, xag, xpt, xpd):
    names = {"XAU": "Qızıl", "XAG": "Gümüş", "XPT": "Platin", "XPD": "Palladium"}
    values = dict(zip(ob.METALS, (xau, xag, xpt, xpd)))
    return day, {c: {"type": "Bank metalları", "nominal": "1 t.u.", "name": names[c], "value": values[c]} for c in ob.METALS}


DAILY_TITLE = "AMB: qızıl 2,24% ucuzlaşıb, unsiyası 6 877,4350 manat"
DAILY_LEAD = ("Azərbaycan Mərkəzi Bankının (AMB) 6 noyabr bülleteninə görə qızılın 1 troya unsiyasının (t.u.) rəsmi qiyməti "
              "6 877,4350 manatdır. Bu, 5 noyabr bülletenindəkindən 157,2755 manat (2,24%) azdır.")
DAILY_BODY = [
    "1 t.u. gümüş: 87,6642 manat (2,4923 manat, 2,76% ucuzlaşıb)",
    "1 t.u. platin: 2 580,1750 manat (16,7450 manat, 0,64% ucuzlaşıb)",
    "1 t.u. palladium: 1 741,1145 manat (9,8345 manat, 0,56% ucuzlaşıb)",
    "Dünya bazarında Bakı vaxtı ilə saat 09:31-də qızılın unsiyası 4 038,7 dollar, gümüşün unsiyası 51,40 dollar olub "
    "(gold-api.com). Əvvəlki bağlanışla müqayisədə qızıl 74,8 dollar (1,82%), gümüş 0,97 dollar (1,86%) ucuzlaşıb.",
    "Bitkoinin qiyməti 75 314 dollar olub, əvvəlki bağlanışla müqayisədə 669 dollar (0,88%) ucuzlaşıb (Yahoo Finance).",
]
WEEK_TITLE = "Həftənin bazarları: Brent nefti 13,32% ucuzlaşıb, gümüş 5,72% bahalaşıb"
WEEK_LEAD = ("Son bir həftədə (31 oktyabr – 7 noyabr) dünya bazarında Brent neftinin bareli 113,43 dollardan 98,32 dollara "
             "düşüb (15,11 dollar, 13,32%). Gümüşün unsiyası 49,25 dollardan 52,07 dollara qalxıb (2,82 dollar, 5,72%).")
WEEK_BODY = [
    "WTI neftinin bareli 104,12 dollardan 90,83 dollara düşüb (13,29 dollar, 12,76%).",
    "Qızılın unsiyası 3 876,4 dollardan 4 072,1 dollara qalxıb (195,7 dollar, 5,05%).",
    "Bitkoin 77 200 dollardan 75 934 dollara düşüb (1 266 dollar, 1,64%).",
    "Mərkəzi Bankın rəsmi məzənnələri, 6 noyabr bülleteni 30 oktyabr bülleteni ilə müqayisədə:",
    "1 avro: 1,9037 manat (0,0018 manat, 0,09% bahalaşıb)",
    "100 Rusiya rublu: 2,0840 manat (0,0083 manat, 0,40% ucuzlaşıb)",
    "1 Türk lirəsi: 0,0339 manat (0,0001 manat, 0,29% ucuzlaşıb)",
    "1 Gürcü larisi: 0,6561 manat (0,0010 manat, 0,15% bahalaşıb)",
    "100 Qazaxıstan tengəsi: 0,3768 manat (0,0015 manat, 0,40% bahalaşıb)",
    "100 Özbək somu: 0,0142 manat (0,0001 manat, 0,71% bahalaşıb)",
    "1 Belarus rublu: 0,5771 manat (0,0241 manat, 4,36% bahalaşıb)",
    "1 Çin yuanı: 0,2549 manat (0,0004 manat, 0,16% ucuzlaşıb)",
    "Dəyişməyib: 1 ABŞ dolları (1,7000 manat), 1 Qırğız somu (0,0194 manat), 1 Türkmənistan manatı (0,4857 manat), "
    "1 Ukrayna qrivnası (0,0375 manat)",
]


class Rules:
    def assert_rules(self, item):
        """Sahibin qaydaları: başlıq ≤110 simvol, sonda nöqtə yoxdur; ədəd vergüllə, işarəsiz (artım/azalma sözlə)."""
        text = "\n".join([item["title"], item["lead"], *item["body"]])
        self.assertLessEqual(len(item["title"]), 110, item["title"])
        self.assertFalse(item["title"].endswith("."), item["title"])
        self.assertIsNone(re.search(r"\d\.\d", text), text)
        self.assertIsNone(re.search(r"[-−+]\d", text), text)
        for key in ("kind", "key", "title", "lead", "body", "credit", "link", "topic", "slot", "worth"):
            self.assertIn(key, item)
        self.assertEqual(item["topic"], "iqtisadiyyat")
        if not item["worth"]:
            self.assertTrue(item.get("why"))


class ParseTest(unittest.TestCase):
    def test_real_bulletin_has_a_bank_metals_section(self):
        day, rows = ob.parse_bulletin(fx("amb-2026-11-06.xml"))
        self.assertEqual(day, D(2026, 11, 6))
        self.assertEqual(rows["XAU"], {"type": "Bank metalları", "nominal": "1 t.u.", "name": "Qızıl", "value": 6877.435})
        self.assertEqual([rows[c]["name"] for c in ob.METALS], ["Qızıl", "Gümüş", "Platin", "Palladium"])
        self.assertEqual({rows[c]["type"] for c in ob.METALS}, {"Bank metalları"})
        self.assertEqual((rows["USD"]["type"], rows["RUB"]["name"], rows["RUB"]["nominal"]), ("Xarici valyutalar", "100 Rusiya rublu", "100"))
        self.assertNotIn("IRR", rows)
        self.assertEqual(len(rows), 42)  # 4 metal, 37 valyuta və SDR
        self.assertEqual(ox.parse_amb(fx("amb-2026-11-06.xml"))[1]["XAU"], ("Qızıl", 6877.435))  # AMB məzənnə xəbərinin oxuduğu

    def test_broken_values_and_date(self):
        xml = ('<ValCurs Date="x"><ValType Type="Bank metalları"><Valute Code="XAU"><Nominal>1 t.u.</Nominal>'
               '<Name>Qızıl</Name><Value>abc</Value></Valute><Valute Code="XAG"><Name>Gümüş</Name></Valute></ValType></ValCurs>')
        self.assertEqual(ob.parse_bulletin(xml.encode("utf-8")), (None, {}))


class DailyTest(unittest.TestCase, Rules):
    def test_real_case_6_november(self):
        root = make_root(self, "markets-2026-11-06T0531Z.json")
        net = FakeNet()
        item, why = ob.daily(root, FRI, net)
        self.assertEqual(why, "")
        self.assertEqual(item["title"], DAILY_TITLE)
        self.assertEqual(item["lead"], DAILY_LEAD)
        self.assertEqual(item["body"], DAILY_BODY)
        self.assertEqual({k: item[k] for k in ("kind", "key", "slot", "credit", "link", "worth", "list")},
                         {"kind": "amb-metal", "key": "amb-metal-2026-11-06", "slot": "09:40", "credit": "Azərbaycan Mərkəzi Bankı",
                          "link": "https://www.cbar.az/currency/rates", "worth": True, "list": True})
        self.assertNotIn("why", item)
        self.assert_rules(item)
        text = " ".join(item["body"])
        for name in ("Avro", "avro", "rublu", "lirəsi", "larisi"):
            self.assertNotIn(name, text, "valyuta siyahısı AMB məzənnə xəbərindədir")
        # 2 sorğu, oz_xeber.amb_latest-in ünvanları ilə eyni: canlıda bir sorğu iki xəbərə gedir
        self.assertEqual(len(net.calls), 2)
        twin = FakeNet()
        ox.amb_latest(twin, FRI.date())
        self.assertEqual(net.calls, twin.calls)
        self.assertEqual(ob.items(root, FRI, FakeNet()), [item])
        self.assertEqual(ox.render(item)[0], "### " + DAILY_TITLE)

    def test_weekend_early_hours_and_days_without_a_new_bulletin(self):
        root = make_root(self, "markets-2026-11-06T0531Z.json")
        net = FakeNet()
        self.assertEqual(ob.daily(root, datetime.datetime(2026, 11, 7, 10, 0, tzinfo=BAKU), net),
                         (None, "həftə sonu AMB bülleten vermir"))
        self.assertEqual(ob.daily(root, datetime.datetime(2026, 11, 6, 9, 10, tzinfo=BAKU), net),
                         (None, "xəbərin vaxtı hələ çatmayıb (09:40)"))
        self.assertEqual(net.calls, [], "həftə sonu və 09:40-dan əvvəl sorğu yoxdur")
        self.assertEqual(ob.daily(root, TUE, net),
                         (None, "bu gün (10 noyabr 2026) AMB-nin yeni bülleteni yoxdur, son bülleten 6 noyabr 2026"))
        self.assertEqual(net.calls, ["https://www.cbar.az/currencies/11.11.2026.xml"], "bülleten köhnədirsə əvvəlkinə sorğu getmir")
        self.assertEqual(ob.items(root, TUE, net), [])
        self.assertEqual(ob.daily(root, FRI), (None, "sorğu funksiyası verilməyib"))
        self.assertEqual(ob.daily(root, FRI, lambda url, **kw: b"<html>"), (None, "AMB bülleteni alınmadı: ParseError"))
        self.assertEqual(ob.daily(root, FRI, FakeNet(bulletins={})), (None, "AMB bülleteni alınmadı: OSError"))
        utc = datetime.datetime(2026, 11, 6, 5, 40, tzinfo=datetime.timezone.utc)  # 09:40 Bakı
        self.assertEqual(ob.daily(root, utc, FakeNet())[0]["title"], DAILY_TITLE)

    def test_stale_old_or_missing_world_prices_are_left_out(self):
        markets = mj("markets-2026-11-06T0531Z.json")
        for row in markets["items"]:
            if row["id"] == "XAU":
                row["stale"] = True
        item, _ = ob.daily(make_root(self, markets=markets), FRI, FakeNet())
        self.assertEqual(item["body"][3], "Dünya bazarında Bakı vaxtı ilə saat 09:31-də gümüşün unsiyası 51,40 dollar olub "
                                          "(gold-api.com). Əvvəlki bağlanışla müqayisədə gümüş 0,97 dollar (1,86%) ucuzlaşıb.")
        self.assertEqual(len(item["body"]), 5)
        late = datetime.datetime(2026, 11, 6, 13, 40, tzinfo=BAKU)  # markets.json 4 saat köhnədir
        item, _ = ob.daily(make_root(self, "markets-2026-11-06T0531Z.json"), late, FakeNet())
        self.assertEqual(item["body"], DAILY_BODY[:3])
        item, _ = ob.daily(make_root(self), FRI, FakeNet())  # markets.json yoxdur
        self.assertEqual((item["title"], item["body"], item["worth"]), (DAILY_TITLE, DAILY_BODY[:3], True))
        markets = mj("markets-2026-11-06T0531Z.json")
        for row in markets["items"]:
            row["change"] = row["changePct"] = None
        item, _ = ob.daily(make_root(self, markets=markets), FRI, FakeNet())
        self.assertEqual(item["body"][3:], [
            "Dünya bazarında Bakı vaxtı ilə saat 09:31-də qızılın unsiyası 4 038,7 dollar, gümüşün unsiyası 51,40 dollar olub (gold-api.com).",
            "Bitkoinin qiyməti 75 314 dollar olub (Yahoo Finance)."])

    def test_title_patterns_and_empty_news(self):
        cur = metal_bulletin(D(2026, 11, 6), 6877.435, 87.6642, 2580.175, 1741.1145)
        cases = [
            ((6912.0, 88.0, 2590.0, 1750.0), "AMB-də dörd bank metalının hamısı ucuzlaşıb: qızılın unsiyası 6 877,4350 manat"),
            ((6850.0, 88.0, 2570.0, 1750.0), "AMB: qızılın unsiyası 27,4350 manat bahalaşaraq 6 877,4350 manat olub"),
            ((6877.435, 88.6642, 2580.175, 1740.1145), "AMB: qızılın qiyməti dəyişməyib, gümüşün unsiyası 1,0000 manat ucuzlaşıb"),
            ((6700.0, 85.0, 2500.0, 1700.0), "AMB: qızıl 2,65% bahalaşıb, unsiyası 6 877,4350 manat"),
        ]
        for prev_values, title in cases:
            item, why = ob.metals_item(cur, metal_bulletin(D(2026, 11, 5), *prev_values), {}, FRI)
            self.assertEqual(item["title"], title)
            self.assertTrue(item["worth"])
            self.assert_rules(item)
        item, _ = ob.metals_item(cur, metal_bulletin(D(2026, 11, 5), 6877.435, 88.6642, 2580.175, 1740.1145), {}, FRI)
        self.assertTrue(item["lead"].endswith("Bu, 5 noyabr bülletenindəki qiymətlə eynidir."))
        self.assertEqual(item["body"], ["1 t.u. gümüş: 87,6642 manat (1,0000 manat, 1,13% ucuzlaşıb)", "1 t.u. platin: 2 580,1750 manat (dəyişməyib)",
                                        "1 t.u. palladium: 1 741,1145 manat (1,0000 manat, 0,06% bahalaşıb)"])
        item, why = ob.metals_item(cur, (D(2026, 11, 5), cur[1]), {}, FRI)
        self.assertEqual((item["worth"], item["why"], why), (False, "AMB-də bank metallarının qiyməti dəyişməyib",
                                                             "AMB-də bank metallarının qiyməti dəyişməyib"))
        self.assertEqual(item["title"], "AMB-də bank metallarının qiyməti dəyişməyib: qızılın unsiyası 6 877,4350 manat")
        self.assert_rules(item)

    def test_missing_metals_previous_bulletin_or_date(self):
        cur = ob.parse_bulletin(fx("amb-2026-11-06.xml"))
        prev = ob.parse_bulletin(fx("amb-2026-11-05.xml"))
        no_metals = (cur[0], {k: v for k, v in cur[1].items() if k not in ob.METALS})
        self.assertEqual(ob.metals_item(no_metals, prev, {}, FRI), (None, "bülletendə qızılın qiyməti yoxdur"))
        self.assertEqual(ob.metals_item(cur, (None, {}), {}, FRI), (None, "əvvəlki bülleten alınmadı: dəyişmə yazıla bilmir"))
        self.assertEqual(ob.metals_item(cur, cur, {}, FRI), (None, "əvvəlki bülleten alınmadı: dəyişmə yazıla bilmir"))
        self.assertEqual(ob.metals_item((None, cur[1]), prev, {}, FRI), (None, "AMB bülleteninin tarixi oxunmadı"))

    def test_leadership_mention_blocks_the_item(self):
        root = make_root(self, "markets-2026-11-06T0531Z.json")
        with patch.object(ox, "needs_owner", return_value=True):
            self.assertEqual(ob.daily(root, FRI, FakeNet()), (None, "rəhbərliyin adı keçir: sahibin təsdiqi lazımdır"))


class WeeklyTest(unittest.TestCase, Rules):
    def real(self):
        return (mj("markets-2026-11-07T0654Z.json"), {D(2026, 10, 31): mj("markets-2026-10-31T0645Z.json")},
                ob.parse_bulletin(fx("amb-2026-11-06.xml")), ob.parse_bulletin(fx("amb-2026-10-30.xml")))

    def test_week_ago_is_a_pure_tolerant_lookup(self):
        m = {"items": []}
        self.assertEqual(ob.week_ago({D(2026, 10, 31): m}, SAT), (D(2026, 10, 31), m))
        self.assertEqual(ob.week_ago({"2026-10-30": m}, SAT), (D(2026, 10, 30), m))
        self.assertEqual(ob.week_ago({datetime.datetime(2026, 10, 31, 6, 45, tzinfo=datetime.timezone.utc): m}, SAT), (D(2026, 10, 31), m))
        self.assertEqual(ob.week_ago({D(2026, 10, 29): m, "x": m, D(2026, 10, 31): "yox"}, SAT), (None, None))
        self.assertEqual(ob.week_ago({D(2026, 11, 1): {"b": 1}, D(2026, 10, 31): m, D(2026, 10, 30): {"a": 1}}, SAT)[1], m)
        self.assertEqual(ob.week_ago({D(2026, 11, 1): {"b": 1}, D(2026, 10, 30): {"a": 1}}, SAT)[1], {"a": 1})
        self.assertEqual(ob.week_ago(None, SAT), (None, None))

    def test_real_week_31_october_to_7_november(self):
        item, why = ob.weekly_item(*self.real(), SAT)
        self.assertEqual(why, "")
        self.assertEqual(item["title"], WEEK_TITLE)
        self.assertEqual(item["lead"], WEEK_LEAD)
        self.assertEqual(item["body"], WEEK_BODY)
        self.assertEqual({k: item[k] for k in ("kind", "key", "slot", "credit", "link", "worth", "list")},
                         {"kind": "bazar-hefte", "key": "bazar-hefte-2026-11-07", "slot": "11:00",
                          "credit": "Yahoo Finance, gold-api.com və Azərbaycan Mərkəzi Bankı", "link": "https://finance.yahoo.com/",
                          "worth": True, "list": True})
        self.assert_rules(item)

    def test_stale_rows_and_missing_parts(self):
        markets, history, cur, prev = self.real()
        for row in history[D(2026, 10, 31)]["items"]:
            if row["id"] == "BRENT":
                row["stale"] = True  # 7 gün əvvəl köhnə idi
        for row in markets["items"]:
            if row["id"] == "XAU":
                row["stale"] = True  # indi köhnədir
        item, _ = ob.weekly_item(markets, history, (None, {}), (None, {}), SAT)
        text = "\n".join([item["title"], item["lead"], *item["body"]])
        self.assertNotIn("Brent", text)
        self.assertNotIn("Qızıl", text)
        self.assertNotIn("Mərkəzi Bank", text)
        self.assertEqual(item["title"], "Həftənin bazarları: WTI nefti 12,76% ucuzlaşıb, gümüş 5,72% bahalaşıb")
        self.assertEqual(item["body"], ["Bitkoin 77 200 dollardan 75 934 dollara düşüb (1 266 dollar, 1,64%)."])
        self.assertEqual(item["credit"], "Yahoo Finance və gold-api.com")
        markets, history, cur, prev = self.real()
        item, _ = ob.weekly_item(markets, {}, cur, prev, SAT)  # 7 gün əvvəlki bazar məlumatı yoxdur: yalnız AMB
        self.assertEqual(item["title"], "Həftənin bazarları: AMB-də 1 Belarus rublu 4,36% bahalaşıb")
        self.assertEqual(item["lead"], "Azərbaycan Mərkəzi Bankının (AMB) 6 noyabr bülletenində, 30 oktyabr bülleteni ilə müqayisədə, "
                                       "1 Belarus rublu 0,0241 manat (4,36%), 100 Özbək somu 0,0001 manat (0,71%) bahalaşıb.")
        self.assertEqual(item["body"], WEEK_BODY[3:])
        self.assertEqual((item["credit"], item["link"]), ("Azərbaycan Mərkəzi Bankı", "https://www.cbar.az/currency/rates"))
        self.assert_rules(item)
        self.assertEqual(ob.weekly_item(markets, {}, (D(2026, 10, 30), cur[1]), (D(2026, 10, 23), prev[1]), SAT),
                         (None, "7 gün əvvəlki bazar məlumatı yoxdur; bu həftə AMB bülleten verməyib, son bülleten 30 oktyabr 2026"))
        self.assertEqual(ob.weekly_item({}, history, (None, {}), (None, {}), SAT),
                         (None, "bazar qiymətləri köhnədir və ya yoxdur; AMB bülleteni yoxdur"))
        self.assertEqual(ob.weekly_item(markets, {}, cur, (None, {}), SAT),
                         (None, "7 gün əvvəlki bazar məlumatı yoxdur; 7 gün əvvəlki AMB bülleteni yoxdur"))

    def test_title_when_everything_moved_the_same_way_and_when_nothing_moved(self):
        markets, history, cur, prev = self.real()
        old = markets
        new = json.loads(json.dumps(markets))
        for row in new["items"]:
            if row["id"] in ob.WEEK_IDS:
                row["value"] = round(row["value"] * 0.9, 4)
        item, _ = ob.weekly_item(new, {D(2026, 10, 31): old}, (None, {}), (None, {}), SAT)
        self.assertEqual(item["title"], "Həftənin bazarları: neft, qızıl, gümüş və bitkoin ucuzlaşıb, Brent nefti 10,00% düşüb")
        self.assert_rules(item)
        item, why = ob.weekly_item(old, {D(2026, 10, 31): old}, cur, (D(2026, 10, 30), cur[1]), SAT)
        self.assertEqual((item["worth"], why), (False, "həftə ərzində qiymətlər dəyişməyib"))
        self.assertEqual(item["title"], "Həftənin bazarları: qiymətlər dəyişməyib")
        self.assert_rules(item)

    def test_schedule_requests_and_items(self):
        root = make_root(self, "markets-2026-11-07T0654Z.json")
        net = FakeNet()
        self.assertEqual(ob.weekly(root, datetime.datetime(2026, 11, 6, 12, 0, tzinfo=BAKU), net),
                         (None, "həftəlik xəbər yalnız şənbə günü çıxır"))
        self.assertEqual(ob.weekly(root, datetime.datetime(2026, 11, 7, 10, 30, tzinfo=BAKU), net),
                         (None, "xəbərin vaxtı hələ çatmayıb (11:00)"))
        self.assertEqual(net.calls, [])
        history = {D(2026, 10, 31): mj("markets-2026-10-31T0645Z.json")}
        item, why = ob.weekly(root, SAT, net, history)
        self.assertEqual((item["title"], item["lead"], item["body"], why), (WEEK_TITLE, WEEK_LEAD, WEEK_BODY, ""))
        self.assertEqual(net.calls, ["https://www.cbar.az/currencies/07.11.2026.xml", "https://www.cbar.az/currencies/30.10.2026.xml"])
        self.assertEqual(ob.items(root, SAT, net, history), [item])
        only = ob.items(root, SAT, net)  # tarixçəsiz: bazar hissəsi yazılmır, GitHub-a sorğu getmir
        self.assertEqual([i["title"] for i in only], ["Həftənin bazarları: AMB-də 1 Belarus rublu 4,36% bahalaşıb"])
        self.assertFalse(any("github" in u for u in net.calls))
        self.assertEqual(ob.weekly(root, SAT, FakeNet(bulletins={})),
                         (None, "7 gün əvvəlki bazar məlumatı yoxdur; AMB bülleteni yoxdur; AMB bülleteni alınmadı: OSError"))


class GithubTest(unittest.TestCase):
    def test_week_old_markets_json_costs_two_requests(self):
        net = FakeNet()
        history = ob.github_history(net, SAT)
        self.assertEqual(list(history), [D(2026, 10, 31)])
        self.assertEqual(history[D(2026, 10, 31)]["updatedAt"], "2026-10-31T06:45:33+00:00")
        self.assertEqual(net.calls, [
            "https://api.github.com/repos/8ulduz/8ulduz/commits?path=data/markets.json&until=2026-10-31T07:00:00Z&per_page=1",
            "https://raw.githubusercontent.com/8ulduz/8ulduz/" + SHA31 + "/data/markets.json"])
        self.assertEqual(net.headers[0], {"Accept": "application/vnd.github+json"})

    def test_far_or_missing_snapshot_is_not_used(self):
        self.assertIsNone(ob.github_markets(FakeNet(), datetime.datetime(2026, 11, 1, 11, 0, tzinfo=BAKU)))  # nüsxə 1 gün köhnədir
        self.assertIsNone(ob.github_markets(FakeNet(snaps={}), SAT))
        self.assertEqual(ob.github_history(FakeNet(snaps={}), SAT), {})
        self.assertIsNone(ob.github_markets(lambda url, **kw: b'[{"sha": "abc"}]', SAT))


class SinaqTest(unittest.TestCase):
    def test_holiday_tuesday_shows_today_and_the_last_real_cases(self):
        root = make_root(self, "markets-2026-11-07T0654Z.json")
        net = FakeNet()
        md = "\n".join(ob.sinaq(root, TUE, net))
        self.assertIn("**Bu gün (10 noyabr 2026, 10:00):** ⏭ Dərc olunmazdı: bu gün (10 noyabr 2026) AMB-nin yeni bülleteni "
                      "yoxdur, son bülleten 6 noyabr 2026", md)
        self.assertIn("**Son real hal: 6 noyabr 2026 bülleteni**, xəbər həmin gün saat 09:40-da çıxardı; dünya qiyməti: "
                      "markets.json-un 6 noyabr 09:31 nüsxəsi (GitHub).", md)
        self.assertIn("### " + DAILY_TITLE, md)
        for line in DAILY_BODY:
            self.assertIn("- " + line, md)
        self.assertIn("**Bu gün (10 noyabr 2026, 10:00):** ⏭ Dərc olunmazdı: həftəlik xəbər yalnız şənbə günü çıxır", md)
        self.assertIn("**Son real hal: 7 noyabr 2026, şənbə**, xəbər saat 11:00-də çıxardı. İndi: markets.json-un 7 noyabr 10:54 "
                      "nüsxəsi (GitHub); 7 gün əvvəl: markets.json-un 31 oktyabr 10:45 nüsxəsi (GitHub); AMB-nin 6 noyabr 2026 və "
                      "30 oktyabr 2026 bülletenləri.", md)
        self.assertIn("### " + WEEK_TITLE, md)
        for line in WEEK_BODY:
            self.assertIn("- " + line, md)
        self.assertEqual(md.count("✅ Dərc olunardı"), 2)
        self.assertEqual([sum(host in u for u in net.calls) for host in ("cbar.az", "api.github.com", "raw.githubusercontent.com")],
                         [4, 3, 3])

    def test_saturday_after_eleven_shows_todays_weekly_item(self):
        root = make_root(self, "markets-2026-11-07T0654Z.json")
        md = "\n".join(ob.sinaq(root, SAT, FakeNet()))
        self.assertIn("**Bu gün (7 noyabr 2026, 11:00):** ⏭ Dərc olunmazdı: həftə sonu AMB bülleten vermir", md)
        self.assertIn("### " + DAILY_TITLE, md)
        self.assertIn("**Bu gün (7 noyabr 2026):** 7 gün əvvəl: markets.json-un 31 oktyabr 10:45 nüsxəsi (GitHub).", md)
        self.assertIn("### " + WEEK_TITLE, md)
        self.assertEqual(md.count("✅ Dərc olunardı"), 2)

    def test_network_failure_is_reported_not_raised(self):
        md = "\n".join(ob.sinaq(make_root(self), TUE, FakeNet(bulletins={}, snaps={})))
        self.assertIn("⏭ Dərc olunmazdı: AMB bülleteni alınmadı: OSError", md)
        self.assertIn("> AMB bülleteni alınmadı: OSError", md)
        self.assertIn("⏭ Dərc olunmazdı: 7 gün əvvəlki bazar məlumatı yoxdur; AMB bülleteni yoxdur", md)
        self.assertNotIn("✅", md)

    def test_cli_prints_the_markdown(self):
        root = make_root(self, "markets-2026-11-07T0654Z.json")
        out = io.StringIO()
        with patch.object(ob, "_default_fetch", return_value=FakeNet()), contextlib.redirect_stdout(out):
            code = ob.main(["--sinaq", "--root", str(root), "--now", "2026-11-10T10:00+04:00"])
        self.assertEqual(code, 0)
        self.assertIn("Bakı vaxtı ilə 10.11.2026 10:00. Sayta heç nə yazılmır.", out.getvalue())
        self.assertIn("### " + DAILY_TITLE, out.getvalue())
        self.assertIn("### " + WEEK_TITLE, out.getvalue())


class NotOnTheSiteTest(unittest.TestCase):
    """Sayta qoşulmayıb: updater.py və pipeline bu faylı çağırmır (sahib: «hələ sayta tətbiq etmə»)."""
    def test_site_does_not_use_it(self):
        self.assertNotIn("oz_bazar", (ROOT / "updater.py").read_text(encoding="utf-8"))
        self.assertNotIn("oz_bazar", (ROOT / ".github" / "scripts" / "pipeline.sh").read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
