"""Öz xəbər, mərhələ 2: hava və təbiət şablonları (oz_hava.py). Şəbəkə yoxdur: bütün sorğular saxtadır.
Real hal tests/fixtures/oz_hava-dadır (2026-11-11 axşamı və 12 noyabr gecəsi götürülmüş cavablar, yalnız lazım olan hissə):
- mhx216.html: MHX-nin «Tibbi-meteoroloji proqnoz» səhifəsinin əsas hissəsi (12 noyabrın cümləsi);
- swpc3day.txt: NOAA SWPC-nin 11 noyabr 12:30 UTC proqnozu; kp.json: Kp cədvəli (4–14 noyabr, 7–8 noyabr G1 qasırğası);
- alerts.json: 30 oktyabr – 11 noyabr K indeksi bildirişləri (və iki başqa bildiriş);
- fc.json, marine.json: Open-Meteo-nun 11–13 noyabr proqnozu (8 şəhər, 5 dəniz nöqtəsi); fc-past.json, marine-past.json:
  29 oktyabr – 13 noyabr (8–9 noyabr küləyi və Şuşa qarı); sst.json: OISST, 2–10 noyabr, Abşeron yaxınlığındakı 6 xana."""
import datetime
import json
import pathlib
import re
import unittest
import urllib.error
from unittest.mock import patch

import oz_xeber as ox
import oz_hava as oh

ROOT = pathlib.Path(__file__).resolve().parent.parent
FIX = pathlib.Path(__file__).resolve().parent / "fixtures" / "oz_hava"
BAKU = ox.BAKU
UTC = datetime.timezone.utc
D = datetime.date
HOUR = datetime.timedelta(hours=1)
NEED = {"kind", "key", "title", "lead", "body", "credit", "link", "topic", "slot", "worth"}


def fx(name):
    return (FIX / name).read_bytes()


def at(y, m, d, hh, mm=0):
    return datetime.datetime(y, m, d, hh, mm, tzinfo=BAKU)


def utc(y, m, d, hh, mm=0):
    return datetime.datetime(y, m, d, hh, mm, tzinfo=UTC)


def http(code):
    return urllib.error.HTTPError("https://saxta", code, "saxta", {}, None)


class Net:
    """Saxta fetch: ünvanın bir hissəsinə görə cavab; çağırışları yadda saxlayır."""

    def __init__(self, routes):
        self.routes, self.calls = list(routes), []

    def __call__(self, url, timeout=None, headers=None, **kw):
        self.calls.append(url)
        if timeout is None or timeout > 15:
            raise AssertionError("timeout 15 saniyədən çox olmamalıdır")
        for part, reply in self.routes:
            if part in url:
                if isinstance(reply, Exception):
                    raise reply
                return reply
        raise urllib.error.URLError("saxta: bu ünvan üçün cavab yoxdur")

    def n(self, part):
        return sum(1 for u in self.calls if part in u)


MHX, SWPC, KP, ALERTS = fx("mhx216.html"), fx("swpc3day.txt"), fx("kp.json"), fx("alerts.json")
SPACE = [("pg=216", MHX), ("3-day-forecast", SWPC), ("k-index-forecast", KP), ("alerts.json", ALERTS)]
SENTENCE = ("Noyabrın 12-də Abşeron yarımadasında meteoroloji amillərin mülayim tərəddüdü gözlənilir ki, bu da "
            "meteohəssas insanlar üçün əsasən əlverişlidir.")


def check(test, item):
    """Müqavilə: açarlar, başlığın uzunluğu, slot, worth=False olanda why."""
    test.assertTrue(NEED <= set(item), sorted(NEED - set(item)))
    test.assertLessEqual(len(item["title"]), 110, item["title"])
    test.assertFalse(item["title"].endswith("."))
    test.assertRegex(item["slot"], r"^\d\d:\d\d$")
    test.assertIsInstance(item["body"], list)
    if not item["worth"]:
        test.assertTrue(item.get("why"))
    blob = " ".join([item["title"], item["lead"], *item["body"]]) if item["worth"] else ""
    test.assertNotIn("xəbərdarlıq", blob.lower())


def kp_rows(*specs):
    """(Bakı vaxtı ilə başlanğıc, Kp, status) -> parse_kp-nin verdiyi sətirlər."""
    return sorted((t.astimezone(UTC), kp, st) for t, kp, st in specs)


class SwpcTextTest(unittest.TestCase):
    def test_fixture(self):
        issued, blocks = oh.parse_swpc_text(SWPC)
        self.assertEqual(issued, utc(2026, 11, 11, 12, 30))
        self.assertEqual(len(blocks), 24)
        self.assertEqual(blocks[0], (utc(2026, 11, 11, 0), 1.67))
        self.assertEqual(blocks[-1], (utc(2026, 11, 13, 21), 1.33))
        self.assertEqual(dict(blocks)[utc(2026, 11, 12, 0)], 3.0)

    def test_g_mark_and_year_end(self):
        text = SWPC.decode("utf-8")
        marked = text.replace("3.00         1.67", "4.67 (G1)    1.67")
        self.assertNotEqual(marked, text)
        self.assertEqual(dict(oh.parse_swpc_text(marked)[1])[utc(2026, 11, 12, 0)], 4.67)
        late = text.replace(":Issued: 2026 Nov 11 1230 UTC", ":Issued: 2026 Dec 30 1230 UTC")
        late = late.replace("             Nov 11       Nov 12       Nov 13", "             Dec 30       Dec 31       Jan 01")
        issued, blocks = oh.parse_swpc_text(late.encode("utf-8"))
        self.assertEqual(issued, utc(2026, 12, 30, 12, 30))
        self.assertEqual(blocks[-1][0], utc(2027, 1, 1, 21))

    def test_garbage(self):
        text = SWPC.decode("utf-8")
        for bad in (b"", b"<html>503</html>", text.replace("06-09UT", "06+09UT"), text.replace(":Issued:", ":Sent:"),
                    text.replace("NOAA Kp index breakdown", "Kp")):
            with self.assertRaises(oh.Bad):
                oh.parse_swpc_text(bad)

    def test_kp_day_is_baku_time(self):
        day = oh.kp_day(oh.parse_swpc_text(SWPC)[1], D(2026, 11, 12))
        self.assertEqual(len(day), 8)
        self.assertEqual(day[0], (at(2026, 11, 12, 1), 2.33))     # 11 noyabr 21-00 UT
        self.assertEqual(day[1], (at(2026, 11, 12, 4), 3.0))      # 12 noyabr 00-03 UT
        self.assertEqual(day[-1], (at(2026, 11, 12, 22), 1.0))    # 12 noyabr 18-21 UT

    def test_g_level(self):
        for kp, g in ((None, 0), (0, 0), (4.33, 0), (4.67, 1), (5, 1), (5.33, 1), (5.67, 2), (6.33, 2), (7, 3), (8, 4),
                      (8.67, 5), (9, 5)):
            self.assertEqual(oh.g_level(kp), g, kp)


class MhxTest(unittest.TestCase):
    def test_fixture(self):
        day, text = oh.parse_mhx(MHX, at(2026, 11, 12, 8, 40))
        self.assertEqual(day, D(2026, 11, 12))
        self.assertEqual(text, SENTENCE)

    def test_year_end_and_capital_i(self):
        page = "<div>Yanvarın 1-də Abşeron yarımadasında hava meteohəssas insanlar üçün əlverişlidir.</div>"
        self.assertEqual(oh.parse_mhx(page.encode("utf-8"), at(2026, 12, 31, 20))[0], D(2027, 1, 1))
        page = "<div>İyunun  5-də&nbsp;Abşeron yarımadasında hava meteohəssas insanlar üçün əlverişlidir.</div>"
        day, text = oh.parse_mhx(page.encode("utf-8"), at(2027, 6, 5, 9))
        self.assertEqual(day, D(2027, 6, 5))
        self.assertTrue(text.startswith("İyunun 5-də Abşeron"))

    def test_garbage(self):
        for bad in ("", "<html><body>503</body></html>", "<div>Sabah hava meteohəssas insanlar üçün əlverişlidir, "
                    "tərəddüd gözlənilmir.</div>", "<div>Noyabrın 12-də meteohəssas</div>",
                    "<div>Noyabrın 12-də hava meteohəssas insanlar üçün <b>əlverişlidir</b> və sakitdir.</div>",
                    "<div>Martın 12-də Abşeron yarımadasında hava meteohəssas insanlar üçün əlverişlidir.</div>"):
            with self.assertRaises(oh.Bad, msg=bad):
                oh.parse_mhx(bad.encode("utf-8"), at(2026, 11, 12, 8, 40))


class MeteoItemTest(unittest.TestCase):
    def setUp(self):
        self.day, self.now = D(2026, 11, 12), at(2026, 11, 12, 8, 40)
        self.mhx = (self.day, SENTENCE)
        self.swpc = oh.parse_swpc_text(SWPC)
        self.swpc13 = (utc(2026, 11, 13, 0, 30), self.swpc[1])     # eyni cədvəl, 13 noyabrın buraxılışı kimi

    def with_kp(self, start, kp, issued=None):
        return issued or self.swpc[0], [(t, kp if t == start else v) for t, v in self.swpc[1]]

    def test_full(self):
        item, why = oh.meteo_item(self.day, self.now, self.mhx, self.swpc)
        check(self, item)
        self.assertEqual(item["title"], "MHX: 12 noyabr Abşeronda meteohəssas insanlar üçün əsasən əlverişlidir")
        self.assertEqual(item["lead"], "Milli Hidrometeorologiya Xidmətinin (MHX) tibbi-meteoroloji proqnozunda deyilir: "
                         "«" + SENTENCE[:-1] + "».")
        self.assertEqual(len(item["body"]), 2)
        self.assertIn("12 noyabrda (Bakı vaxtı ilə, 3 saatlıq dövrlər üzrə) Kp indeksi 1–3 arasında olacaq; ən yüksək "
                      "göstərici (3) saat 04:00–07:00 arasına düşür.", item["body"][0])
        self.assertIn("aşağıdır", item["body"][1])
        self.assertEqual((item["key"], item["slot"], item["worth"]), ("meteohessas-2026-11-12", "08:30", True))
        self.assertIn("NOAA", item["credit"])
        self.assertEqual(item["link"], oh.MHX_URL)

    def test_storm_day_is_one_line(self):
        item, why = oh.meteo_item(self.day, self.now, self.mhx, self.with_kp(utc(2026, 11, 12, 15), 5.33))
        check(self, item)
        self.assertEqual(len(item["body"]), 1)
        self.assertIn("ən yüksək göstəricisi 5,33 olacaq (saat 19:00–22:00 arası)", item["body"][0])
        self.assertIn("G1 (zəif)", item["body"][0])

    def test_unknown_phrase_gets_generic_title(self):
        text = "Noyabrın 12-də şimal küləyinin güclənməsi bəzi meteohəssas insanlarda narahatlıq yarada bilər."
        item, why = oh.meteo_item(self.day, self.now, (self.day, text), self.swpc)
        self.assertEqual(item["title"], "Meteohəssaslar üçün 12 noyabr: MHX-nin tibbi-meteoroloji proqnozu")
        self.assertIn(text[:-1], item["lead"])

    def test_stale_mhx_quiet_noaa_is_not_news(self):
        day, now = D(2026, 11, 13), at(2026, 11, 13, 8, 40)       # səhifədə hələ 12 noyabrın cümləsidir
        item, why = oh.meteo_item(day, now, self.mhx, self.swpc13)
        self.assertIsNone(item)
        self.assertIn("MHX-nin səhifəsi bu günə deyil (12 noyabr)", why)
        self.assertIn("xəbər deyil", why)

    def test_stale_mhx_active_noaa(self):
        day, now = D(2026, 11, 13), at(2026, 11, 13, 8, 40)
        item, why = oh.meteo_item(day, now, self.mhx, self.with_kp(utc(2026, 11, 13, 6), 4.33, self.swpc13[0]))
        check(self, item)
        self.assertTrue(item["title"].startswith("NOAA proqnozu: 13 noyabrda Kp indeksi ən çox 4,33 olacaq"), item["title"])
        self.assertEqual((item["credit"], item["link"]), (oh.SWPC_CREDIT, oh.SWPC_PAGE))
        self.assertIn("saat 10:00–13:00", item["lead"])
        item, why = oh.meteo_item(day, now, None, self.with_kp(utc(2026, 11, 13, 6), 5.33, self.swpc13[0]), ["MHX alınmadı: URLError"])
        self.assertIsNone(item)
        self.assertIn("ayrıca xəbərdir", why)
        self.assertIn("MHX alınmadı", why)

    def test_stale_noaa(self):
        now = at(2026, 11, 13, 8, 40)                              # proqnoz 11 noyabr 16:30-da (Bakı) çıxıb: 40 saat
        item, why = oh.meteo_item(D(2026, 11, 13), now, (D(2026, 11, 13), SENTENCE.replace("12", "13")), self.swpc)
        check(self, item)
        self.assertEqual(item["body"], [])
        self.assertEqual(item["credit"], oh.MHX_CREDIT)
        self.assertEqual(oh.meteo_item(D(2026, 11, 13), now, None, self.swpc)[0], None)
        self.assertEqual(oh.meteo_item(self.day, self.now)[0], None)

    def test_leadership_is_never_published(self):
        text = "Noyabrın 12-də Prezident İlham Əliyev Abşeronda meteohəssas insanlar üçün tədbirdə iştirak edəcək."
        item, why = oh.meteo_item(self.day, self.now, (self.day, text), self.swpc)
        self.assertFalse(oh._guard(item)["worth"])
        self.assertTrue(oh._guard(oh.meteo_item(self.day, self.now, self.mhx, self.swpc)[0])["worth"])


class StormTest(unittest.TestCase):
    def setUp(self):
        self.rows = oh.parse_kp(KP)
        self.alerts = oh.parse_alerts(ALERTS)

    def test_parse(self):
        self.assertEqual(len(self.rows), 81)
        self.assertEqual(self.rows[0], (utc(2026, 11, 4, 0), 2.33, "observed"))
        self.assertEqual(self.rows[-1][2], "predicted")
        self.assertIn((utc(2026, 11, 7, 19, 45), 5), self.alerts)
        self.assertIn((utc(2026, 10, 31, 19, 14), 6), self.alerts)
        old = [["time_tag", "kp", "observed", "noaa_scale"]] + [
            ["2026-11-07 %02d:00:00" % h, "5.33" if h == 18 else "2.00", "observed", None] for h in range(0, 24, 3)]
        rows = oh.parse_kp(json.dumps(old).encode("utf-8"))
        self.assertEqual(len(rows), 8)
        self.assertEqual(rows[6], (utc(2026, 11, 7, 18), 5.33, "observed"))

    def test_garbage(self):
        for bad in (b"[]", b"{}", b'[{"time_tag": "x", "kp": 5}]', b'[{"time_tag": "2026-11-07T18:00:00", "kp": 55}]'):
            with self.assertRaises(oh.Bad):
                oh.parse_kp(bad)
        with self.assertRaises(ValueError):
            oh.parse_kp(b"<html>")
        self.assertEqual(oh.parse_alerts(b'[{"message": "ALERT: Geomagnetic K-index of 5"}, 5, {"x": 1}]'), [])

    def test_real_storm_of_8_november(self):
        item, why = oh.storm_item(D(2026, 11, 8), self.rows, at(2026, 11, 8, 8, 40), self.alerts)
        check(self, item)
        self.assertEqual(item["title"], "Zəif maqnit qasırğası qeydə alınıb: Kp indeksi 5,33 (G1)")
        self.assertIn("Kp indeksi Bakı vaxtı ilə 7 noyabr saat 22:00–01:00 arası 5,33 (G1), 8 noyabr saat 04:00–07:00 "
                      "arası 5 (G1) olub; bu, NOAA şkalasında G1 (zəif) səviyyəli maqnit qasırğasıdır.", item["lead"])
        self.assertIn("NOAA-nın «K indeksi 5» bildirişinə görə, bu həddə Bakı vaxtı ilə 7 noyabr saat 23:45-də çatılıb.",
                      item["body"])
        self.assertEqual((item["key"], item["topic"], item["worth"]), ("maqnit-qasirgasi-2026-11-08", "kosmos", True))
        plain = oh.storm_item(D(2026, 11, 8), self.rows, at(2026, 11, 8, 8, 40))[0]
        self.assertEqual(len(plain["body"]), len(item["body"]) - 1)

    def test_other_days_have_no_storm(self):
        for d in (7, 9, 10, 11, 12, 13):
            item, why = oh.storm_item(D(2026, 11, d), self.rows, at(2026, 11, d, 8, 40), self.alerts)
            self.assertIsNone(item, d)
            self.assertIn("çatmır", why)

    def test_forecast_only_and_mixed(self):
        day = D(2026, 11, 12)
        rows = kp_rows((at(2026, 11, 12, 4), 3.0, "observed"), (at(2026, 11, 12, 19), 6.33, "predicted"))
        item, why = oh.storm_item(day, rows, at(2026, 11, 12, 8, 40))
        check(self, item)
        self.assertEqual(item["title"], "Orta səviyyəli maqnit qasırğası gözlənilir: Kp indeksi 6,33 (G2), NOAA proqnozu")
        self.assertIn("proqnozuna görə, Kp indeksi Bakı vaxtı ilə 12 noyabr saat 19:00–22:00 arası 6,33 (G2) olacaq",
                      item["lead"])
        rows = kp_rows((at(2026, 11, 12, 4), 5.0, "observed"), (at(2026, 11, 12, 7), 4.67, "estimated"),
                       (at(2026, 11, 12, 10), 7.0, "predicted"), (at(2026, 11, 12, 13), 5.0, "predicted"))
        item, why = oh.storm_item(day, rows, at(2026, 11, 12, 8, 40))
        self.assertEqual(item["title"], "Zəif maqnit qasırğası qeydə alınıb: Kp indeksi 5 (G1)")
        self.assertIn("07:00–10:00 arası 4,67 (G1) olub", item["lead"])
        self.assertIn("Proqnoza görə, Kp indeksi 12 noyabr saat 10:00–13:00 arası 7 (G3), 12 noyabr saat 13:00–16:00 "
                      "arası 5 (G1) olacaq.", item["body"])
        self.assertIn("Kp indeksi cəmi 4 üçsaatlıq dövrdə G1 və yuxarı səviyyədədir.", item["body"])

    def test_night_belongs_to_next_day_and_continuation(self):
        night = (at(2026, 11, 11, 22), 5.0, "observed")
        self.assertIsNone(oh.storm_item(D(2026, 11, 11), kp_rows(night), at(2026, 11, 11, 20, 10))[0])
        self.assertIsNotNone(oh.storm_item(D(2026, 11, 12), kp_rows(night), at(2026, 11, 12, 8, 40))[0])
        yesterday = (at(2026, 11, 11, 16), 5.33, "observed")
        item, why = oh.storm_item(D(2026, 11, 12), kp_rows(yesterday, night), at(2026, 11, 12, 8, 40))
        self.assertIsNone(item)
        self.assertIn("davamıdır", why)
        self.assertIsNotNone(oh.storm_item(D(2026, 11, 11), kp_rows(yesterday, night), at(2026, 11, 11, 20, 10))[0])
        stronger = (at(2026, 11, 11, 22), 6.0, "observed")
        self.assertIsNotNone(oh.storm_item(D(2026, 11, 12), kp_rows(yesterday, stronger), at(2026, 11, 12, 8, 40))[0])
        later = (at(2026, 11, 12, 4), 5.0, "observed")             # 12 saat fasilə: yeni hadisə
        self.assertIsNotNone(oh.storm_item(D(2026, 11, 12), kp_rows(yesterday, later), at(2026, 11, 12, 8, 40))[0])


class SpaceRoundTest(unittest.TestCase):
    """Səhər və axşam pəncərəsi: MHX, SWPC mətni, Kp cədvəli, alerts."""

    def run_items(self, now, routes=SPACE, done=None):
        net = Net(routes)
        out = oh.items(ROOT, now, fetch=net, done=done)
        for item in out:
            check(self, item)
        return out, net

    def test_morning_round(self):
        out, net = self.run_items(at(2026, 11, 12, 8, 40))
        self.assertEqual([(i["key"], i["worth"]) for i in out],
                         [("meteohessas-2026-11-12", True), ("maqnit-sorgu-2026-11-12-seher", False)])
        self.assertEqual((len(net.calls), net.n("alerts")), (3, 0))
        again, net2 = self.run_items(at(2026, 11, 12, 8, 40))
        self.assertEqual(out, again)                                # eyni məlumat, eyni an: eyni nəticə
        naive, net3 = self.run_items(datetime.datetime(2026, 11, 12, 8, 40))
        self.assertEqual(out, naive)

    def test_done_stops_requests(self):
        keys = {"meteohessas-2026-11-12", "maqnit-sorgu-2026-11-12-seher"}
        out, net = self.run_items(at(2026, 11, 12, 9, 10), done=keys)
        self.assertEqual((out, net.calls), ([], []))
        out, net = self.run_items(at(2026, 11, 12, 9, 10), done={"meteohessas-2026-11-12"})
        self.assertEqual([i["key"] for i in out], ["maqnit-sorgu-2026-11-12-seher"])
        self.assertEqual((len(net.calls), net.n("k-index-forecast")), (1, 1))
        out, net = self.run_items(at(2026, 11, 12, 9, 10), done={"maqnit-qasirgasi-2026-11-12"})
        self.assertEqual([i["key"] for i in out], ["meteohessas-2026-11-12"])
        self.assertEqual(net.n("k-index-forecast"), 0)

    def test_outside_windows_nothing_is_requested(self):
        for hh, mm in ((0, 5), (8, 29), (10, 30), (14, 0), (19, 59), (22, 0), (23, 50)):
            out, net = self.run_items(at(2026, 11, 12, hh, mm))
            self.assertEqual((out, net.calls), ([], []), (hh, mm))

    def test_evening_round(self):
        out, net = self.run_items(at(2026, 11, 12, 20, 10))
        self.assertEqual([(i["key"], i["worth"]) for i in out], [("maqnit-sorgu-2026-11-12-axsam", False)])
        self.assertEqual(len(net.calls), 1)
        for done in ({"maqnit-sorgu-2026-11-12-axsam"}, {"maqnit-qasirgasi-2026-11-12"}):
            out, net = self.run_items(at(2026, 11, 12, 21, 0), done=done)
            self.assertEqual((out, net.calls), ([], []))
        out, net = self.run_items(at(2026, 11, 12, 21, 0), done={"maqnit-sorgu-2026-11-12-seher"})
        self.assertEqual(len(out), 1)                               # səhərin açarı axşamı bağlamır

    def test_storm_morning_opens_alerts_once(self):
        out, net = self.run_items(at(2026, 11, 8, 8, 40))
        self.assertEqual([(i["key"], i["worth"]) for i in out],
                         [("meteohessas-2026-11-08", False), ("maqnit-qasirgasi-2026-11-08", True)])
        self.assertEqual((len(net.calls), net.n("alerts")), (4, 1))
        self.assertIn("23:45", " ".join(out[1]["body"]))
        self.assertEqual(out[1]["slot"], "08:40")
        routes = SPACE[:3] + [("alerts.json", http(500))]
        out, net = self.run_items(at(2026, 11, 8, 20, 30), routes)   # bildirişlər alınmasa xəbər onlarsız çıxır
        self.assertEqual([(i["key"], i["worth"], i["slot"]) for i in out], [("maqnit-qasirgasi-2026-11-08", True, "20:10")])
        self.assertNotIn("bildirişinə", " ".join(out[0]["body"]))

    def test_failures_return_the_window_keys(self):
        garbage = [(part, b"<html>503</html>") for part, _ in SPACE]
        for routes in ([], garbage, [(part, http(503)) for part, _ in SPACE]):
            out, net = self.run_items(at(2026, 11, 12, 8, 40), routes)
            self.assertEqual([(i["key"], i["worth"]) for i in out],
                             [("meteohessas-2026-11-12", False), ("maqnit-sorgu-2026-11-12-seher", False)])
            self.assertEqual(len(net.calls), 3)
        out, net = self.run_items(at(2026, 11, 20, 8, 40))           # cədvəl 14 noyabrda bitir
        self.assertIn("köhnədir", out[1]["why"])
        self.assertEqual(oh.items(ROOT, "sabah", fetch=Net([])), [])


class SinaqTest(unittest.TestCase):
    def test_sample_run(self):
        net = Net(SPACE)
        with patch.object(oh.time, "sleep") as sleep:
            md = "\n".join(oh.sinaq(ROOT, at(2026, 11, 12, 2, 30), fetch=net))
        for part in ("## 1.", "## 2.", "MHX: 12 noyabr Abşeronda", "Son real hal: 8 noyabr 2026", "✅ Dərc olunardı",
                     "⏭ Dərc olunmazdı", "sorğu göndərilib"):
            self.assertIn(part, md)
        self.assertNotIn("Sınaq xətası", md)
        self.assertLessEqual(len(net.calls), 20)
        self.assertEqual(len(net.calls), len(set(net.calls)))

    def test_sample_run_survives_dead_network(self):
        with patch.object(oh.time, "sleep"):
            md = "\n".join(oh.sinaq(ROOT, at(2026, 11, 12, 2, 30), fetch=Net([])))
        self.assertIn("# Hava və təbiət", md)
        self.assertTrue(re.search(r"Sınaq xətası|Dərc olunmazdı", md))


if __name__ == "__main__":
    unittest.main()
