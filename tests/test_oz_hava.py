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
        self.routes, self.calls, self.agents = list(routes), [], {}

    def __call__(self, url, timeout=None, headers=None, **kw):
        self.calls.append(url)
        self.agents[url] = (headers or {}).get("User-Agent")
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

    def test_every_block_of_the_maximum_is_named(self):
        two = oh.meteo_item(self.day, self.now, self.mhx, self.with_kp(utc(2026, 11, 12, 18), 3.0))[0]
        self.assertIn("ən yüksək göstərici (3) saat 04:00–07:00 və 22:00–01:00 arasına düşür.", two["body"][0])
        blocks = [(t, 2.0 if t.hour < 12 else 1.0) for t, v in self.swpc[1]]
        many = oh.meteo_item(self.day, self.now, self.mhx, (self.swpc[0], blocks))[0]
        self.assertTrue(many["body"][0].endswith("Kp indeksi 1–2 arasında olacaq."), many["body"][0])
        flat = oh.meteo_item(self.day, self.now, self.mhx, (self.swpc[0], [(t, 2.0) for t, v in self.swpc[1]]))[0]
        self.assertTrue(flat["body"][0].endswith("Kp indeksi 2 olacaq."), flat["body"][0])
        three = [(t, 5.33 if t.hour in (3, 9, 15) else 1.0) for t, v in self.swpc[1]]
        storm = oh.meteo_item(self.day, self.now, self.mhx, (self.swpc[0], three))[0]
        self.assertIn("5,33 olacaq (saat 07:00–10:00, 13:00–16:00 və 19:00–22:00 arası); bu, NOAA", storm["body"][0])

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
        self.assertEqual(set(net.agents.values()), {None})          # qalan mənbələrə updater-in öz User-Agent-i
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


FC, MARINE, FC_PAST, MARINE_PAST, SST = (fx(n) for n in ("fc.json", "marine.json", "fc-past.json", "marine-past.json",
                                                         "sst.json"))
WEATHER = [("/v1/forecast", FC), ("/v1/marine", MARINE)]
WEATHER_PAST = [("/v1/forecast", FC_PAST), ("/v1/marine", MARINE_PAST)]
ALL = SPACE + WEATHER_PAST + [("erddap", SST)]


def go(test, now, routes, done=None):
    net = Net(routes)
    out = oh.items(ROOT, now, fetch=net, done=done)
    for item in out:
        check(test, item)
    return out, net


def calm(day, over=None):
    """8 şəhərin sakit günü (parse_om şəklində); over: şəhər adı -> dəyişən sahələr."""
    out = []
    for name, _, _, _ in oh.CITIES:
        row = {"temperature_2m_max": 15.0, "temperature_2m_min": 8.0, "wind_gusts_10m_max": 6.0, "snowfall_sum": 0.0}
        row.update((over or {}).get(name, {}))
        out.append({day: row})
    return out


def waves(day, over=None):
    return [{day: {"wave_height_max": (over or {}).get(name, 0.8)}} for name, _, _, _ in oh.SEA]


class ForecastTest(unittest.TestCase):
    T = D(2026, 11, 13)

    def setUp(self):
        self.past = oh.parse_om(FC_PAST, 8, oh.FC_FIELDS)
        self.sea_past = oh.parse_om(MARINE_PAST, 5, oh.SEA_FIELDS)

    def test_parse_and_urls(self):
        cities = oh.parse_om(FC, 8, oh.FC_FIELDS)
        self.assertEqual(cities[0][D(2026, 11, 12)], {"temperature_2m_max": 13.6, "temperature_2m_min": 8.1,
                                                      "wind_gusts_10m_max": 13.4, "snowfall_sum": 0.0})
        self.assertEqual(cities[7][D(2026, 11, 11)]["temperature_2m_min"], -3.5)
        self.assertEqual(oh.parse_om(MARINE, 5, oh.SEA_FIELDS)[4][D(2026, 11, 11)], {"wave_height_max": 1.46})
        self.assertIn("latitude=40.4093,40.6828,40.5897,38.7529,41.1919,41.3611,39.2089,39.758&longitude=49.8671,46.3606,"
                      "49.6686,48.85,47.1706,48.5133,45.4122,46.75&daily=temperature_2m_max,temperature_2m_min,"
                      "wind_gusts_10m_max,snowfall_sum&timezone=Asia%2FBaku&wind_speed_unit=ms", oh.fc_url())
        self.assertNotIn("past_days", oh.fc_url())
        self.assertTrue(oh.fc_url(14).endswith("&forecast_days=3&past_days=14"))
        self.assertIn("latitude=40.30,40.62,38.75,41.80,40.22&longitude=50.00,49.75,49.00,48.75,50.85&daily=wave_height_max",
                      oh.marine_url())
        self.assertTrue(oh.sst_url(D(2026, 11, 14)).endswith(
            ".json?sst%5B(2026-11-04T12:00:00Z):1:(last)%5D%5B(0.0)%5D%5B(40.375):1:(40.625)%5D%5B(49.625):1:(50.125)%5D"))

    def test_garbage(self):
        kmh, nodays, odd = json.loads(FC), json.loads(FC), json.loads(FC)
        kmh[0]["daily_units"]["wind_gusts_10m_max"] = "km/h"
        nodays[3]["daily"]["time"] = []
        for bad in (b"{}", b'{"error": true, "reason": "x"}', b"[]", json.dumps(kmh).encode("utf-8"),
                    json.dumps(json.loads(FC)[:7]).encode("utf-8"), json.dumps(nodays).encode("utf-8")):
            with self.assertRaises(oh.Bad):
                oh.parse_om(bad, 8, oh.FC_FIELDS)
        with self.assertRaises(ValueError):
            oh.parse_om(b"<html>", 8, oh.FC_FIELDS)
        odd[0]["daily"]["wind_gusts_10m_max"] = [None, "x", 999]
        odd[0]["daily"]["snowfall_sum"] = [0]
        row = oh.parse_om(json.dumps(odd).encode("utf-8"), 8, oh.FC_FIELDS)[0]
        self.assertEqual([row[D(2026, 11, d)]["wind_gusts_10m_max"] for d in (11, 12, 13)], [None, None, None])
        self.assertEqual((row[D(2026, 11, 11)]["snowfall_sum"], row[D(2026, 11, 13)]["snowfall_sum"]), (0.0, None))

    def test_normals_table(self):
        self.assertEqual((len(oh.NORM_MAX), len(oh.NORM_MIN)), (366, 366))
        self.assertTrue(all(-10 < n < x < 45 for x, n in zip(oh.NORM_MAX, oh.NORM_MIN)))
        self.assertEqual(oh.norm_of(D(2026, 11, 10)), (14.7, 9.8))
        self.assertEqual(oh.norm_of(D(2026, 1, 1)), (oh.NORM_MAX[0], oh.NORM_MIN[0]))
        self.assertEqual(oh.norm_of(D(2028, 2, 29)), (oh.NORM_MAX[59], oh.NORM_MIN[59]))
        self.assertEqual(oh.norm_of(D(2026, 12, 31)), (oh.NORM_MAX[365], oh.NORM_MIN[365]))
        self.assertGreater(oh.norm_of(D(2026, 7, 15))[0], oh.norm_of(D(2026, 1, 15))[0] + 15)

    def test_real_wind_and_snow_of_9_november(self):
        item, why = oh.hazard_item(D(2026, 11, 9), self.past, self.sea_past)
        check(self, item)
        self.assertEqual(item["title"], "Model proqnozu: sabah Bakıda küləyin ani sürəti 23,6 m/san ola bilər")
        self.assertEqual(item["lead"], "Open-Meteo-nun model proqnozuna görə, sabah, 9 noyabrda küləyin ani sürəti Bakıda "
                         "23,6 m/san, Sumqayıtda 23,1 m/san olacaq.")
        self.assertEqual(item["body"], ["Model proqnozuna görə, Şuşada 11,1 sm qar yağacaq.", oh.HZ_NOTE])
        self.assertEqual((item["key"], item["slot"], item["topic"]), ("hava-hedd-2026-11-09", "16:10", "təbiət"))
        item, why = oh.hazard_item(D(2026, 11, 8), self.past, self.sea_past)
        self.assertEqual(item["title"], "Model proqnozu: sabah Sumqayıtda küləyin ani sürəti 24,6 m/san ola bilər")
        self.assertIn("Sumqayıtda 24,6 m/san, Bakıda 23,3 m/san olacaq", item["lead"])
        self.assertEqual(item["body"], [oh.HZ_NOTE])           # Şuşada 8,47 sm qar və 2,62 m dalğa həddən aşağıdır
        for d in (7, 10, 11, 12, 13):
            item, why = oh.hazard_item(D(2026, 11, d), self.past, self.sea_past, notes=["dəniz proqnozu yoxdur"])
            self.assertIsNone(item, d)
            self.assertEqual(why, "sabah üçün heç bir hədd keçilmir; dəniz proqnozu yoxdur")

    def test_thresholds(self):
        T = self.T
        cases = (("Gəncə", "wind_gusts_10m_max", 19.9, 20.0, "gust"), ("Bakı", "temperature_2m_min", -4.9, -5.0, "frost"),
                 ("Gəncə", "temperature_2m_min", -9.9, -10.0, "frost"), ("Lənkəran", "temperature_2m_max", 37.9, 38.0, "heat"),
                 ("Bakı", "snowfall_sum", 4.9, 5.0, "snow"), ("Şuşa", "snowfall_sum", 9.9, 10.0, "snow"))
        for city, field, below, hit, kind in cases:
            self.assertEqual(oh.hazards(T, calm(T, {city: {field: below}})), {}, (city, field))
            self.assertEqual(list(oh.hazards(T, calm(T, {city: {field: hit}}))), [kind], (city, field))
        self.assertEqual(oh.hazards(T, calm(T), waves(T, {"Nabran": 2.99})), {})
        self.assertEqual(oh.hazards(T, calm(T), waves(T, {"Nabran": 3.0})), {"wave": [("Nabran sahilində", 3.0)]})
        missing = calm(T, {"Bakı": {"wind_gusts_10m_max": None, "temperature_2m_min": None, "snowfall_sum": None}})
        self.assertEqual(oh.hazards(T, missing, None), {})
        self.assertEqual(oh.hazards(D(2026, 11, 20), calm(T, {"Bakı": {"wind_gusts_10m_max": 30.0}})), {})

    def test_all_thresholds_merge_into_one_item(self):
        T = self.T
        cities = calm(T, {"Sumqayıt": {"wind_gusts_10m_max": 26.04},
                          "Bakı": {"wind_gusts_10m_max": 21.0, "snowfall_sum": 6.0},
                          "Şuşa": {"temperature_2m_min": -12.34, "snowfall_sum": 14.0},
                          "Quba": {"temperature_2m_min": -10.0}, "Naxçıvan": {"temperature_2m_max": 38.5}})
        item, why = oh.hazard_item(T, cities, waves(T, {"Neft Daşları": 3.24, "Nabran": 3.0}))
        check(self, item)
        self.assertEqual(item["title"], "Model proqnozu: sabah Sumqayıtda küləyin ani sürəti 26 m/san ola bilər")
        self.assertIn("13 noyabrda küləyin ani sürəti Sumqayıtda 26 m/san, Bakıda 21 m/san olacaq.", item["lead"])
        self.assertEqual(item["body"], [
            "Model proqnozuna görə, Şuşada 14 sm, Bakıda 6 sm qar yağacaq.",
            "Model proqnozuna görə, minimum temperatur Şuşada −12,3 °C, Qubada −10 °C olacaq.",
            "Model proqnozuna görə, maksimum temperatur Naxçıvanda 38,5 °C olacaq.",
            "Model proqnozuna görə, Xəzərdə dalğanın maksimum hündürlüyü Neft Daşları yaxınlığında 3,2 m, Nabran sahilində "
            "3 m olacaq.", oh.HZ_NOTE])
        self.assertIn("rəsmi hava proqnozu deyil", oh.HZ_NOTE)
        self.assertIn("minimum temperatur −10 °C (Bakıda −5 °C), maksimum temperatur 38 °C, qar 10 sm", oh.HZ_NOTE)

    def test_titles_by_kind(self):
        T = self.T
        for over, sea, title in (
                ({"Şuşa": {"temperature_2m_min": -12.34}}, None, "Şuşada minimum temperatur −12,3 °C ola bilər"),
                ({"Şuşa": {"snowfall_sum": 11.13}}, None, "Şuşada 11,1 sm qar yağa bilər"),
                ({"Gəncə": {"temperature_2m_max": 40.0}}, None, "Gəncədə maksimum temperatur 40 °C ola bilər"),
                ({}, {"Neft Daşları": 3.24}, "Neft Daşları yaxınlığında dalğanın hündürlüyü 3,2 m ola bilər")):
            item, why = oh.hazard_item(T, calm(T, over), waves(T, sea))
            check(self, item)
            self.assertEqual(item["title"], "Model proqnozu: sabah " + title)
        self.assertIn("sabah, 13 noyabrda Xəzərdə dalğanın maksimum hündürlüyü Neft Daşları yaxınlığında 3,2 m olacaq.",
                      item["lead"])

    def test_real_cold_day_of_9_november(self):
        baku = self.past[0]
        self.assertEqual([oh.anomaly(D(2026, 11, d), baku) for d in (8, 9, 10)], [-1.6, -5.6, -4.5])
        item, why = oh.norm_item(D(2026, 11, 9), baku)
        check(self, item)
        self.assertEqual(item["title"], "Model proqnozu: sabah Bakıda gündüz hava normadan 5,6 dərəcə soyuq olacaq")
        self.assertEqual(item["lead"], "Open-Meteo-nun model proqnozuna görə, sabah, 9 noyabrda Bakıda maksimum temperatur "
                         "9,2 °C olacaq. Bu, 1991–2020-ci illərin həmin günə düşən orta maksimumundan (14,8 °C) 5,6 dərəcə "
                         "aşağıdır.")
        self.assertTrue(item["body"][0].startswith("Minimum temperatur "), item["body"][0])
        self.assertEqual(item["body"][-1], oh.NORM_NOTE)
        self.assertEqual((item["key"], item["slot"]), ("norma-ferq-2026-11-09", "16:20"))
        item, why = oh.norm_item(D(2026, 11, 10), baku)
        self.assertIsNone(item)
        self.assertEqual(why, "Bakıda fərq 4,5 dərəcədir (hədd 5)")

    def test_spell_is_reported_once(self):
        T, Y = self.T, self.T - datetime.timedelta(days=1)
        (nx, nn), ny = oh.norm_of(T), oh.norm_of(Y)[0]

        def baku(y, t, tmin=None):
            return {Y: {"temperature_2m_max": y, "temperature_2m_min": 5.0},
                    T: {"temperature_2m_max": t, "temperature_2m_min": tmin}}

        item, why = oh.norm_item(T, baku(ny + 6, nx + 7))
        self.assertIsNone(item)
        self.assertIn("davamıdır", why)
        item, why = oh.norm_item(T, baku(ny - 6, nx + 7))          # dünən soyuq idi, sabah isti: yeni hadisə
        check(self, item)
        self.assertIn("normadan 7 dərəcə isti olacaq", item["title"])
        self.assertIn("7 dərəcə yüksəkdir", item["lead"])
        self.assertEqual(item["body"], [oh.NORM_NOTE])
        self.assertIsNotNone(oh.norm_item(T, baku(ny + 4.9, nx + 5))[0])
        self.assertIsNone(oh.norm_item(T, baku(ny, nx + 4.9))[0])
        self.assertIsNone(oh.norm_item(T, baku(ny, None))[0])
        self.assertIsNone(oh.norm_item(T, {})[0])
        item, why = oh.norm_item(T, baku(None, nx - 5, nn))
        self.assertIn("normadan 5 dərəcə soyuq olacaq", item["title"])
        self.assertIn("orta minimumuna", item["body"][0])
        item, why = oh.norm_item(T, baku(None, nx - 5, nn - 3))
        self.assertIn("3 dərəcə aşağıdır", item["body"][0])

    def test_baku_heat_folds_the_normal_into_the_hazard_item(self):
        T = D(2027, 7, 15)
        cities = calm(T, {"Bakı": {"temperature_2m_max": 40.0, "temperature_2m_min": 25.0}})
        hz, nm = oh.forecast_items(T, cities, None, at(2027, 7, 14, 16, 10))
        check(self, hz)
        check(self, nm)
        self.assertEqual((hz["worth"], nm["worth"]), (True, False))
        self.assertIn("təhlükəli hava həddi xəbərində yazılır", nm["why"])
        self.assertTrue(hz["body"][0].startswith("Bakıda maksimum temperatur (40 °C) 1991–2020-ci illərin"), hz["body"][0])
        self.assertEqual(hz["body"][-1], oh.HZ_NOTE)
        hz, nm = oh.forecast_items(T, calm(T, {"Bakı": {"temperature_2m_max": 37.0}}), None, at(2027, 7, 14, 16, 10))
        self.assertEqual((hz["worth"], nm["worth"]), (False, True))   # hədd keçilməyib: normadan fərq öz xəbəridir


class WeatherRoundTest(unittest.TestCase):
    """16:00–18:00 pəncərəsi: Open-Meteo proqnozu və dəniz proqnozu, sabah üçün."""

    def test_forecast_round(self):
        out, net = go(self, at(2026, 11, 11, 16, 10), WEATHER)
        self.assertEqual([(i["key"], i["worth"]) for i in out],
                         [("hava-hedd-2026-11-12", False), ("norma-ferq-2026-11-12", False)])
        self.assertEqual((len(net.calls), net.n("/v1/forecast"), net.n("/v1/marine")), (2, 1, 1))
        self.assertEqual(out[1]["why"], "Bakıda fərq 0,7 dərəcədir (hədd 5)")
        again, net = go(self, at(2026, 11, 11, 17, 0), WEATHER, {i["key"] for i in out})
        self.assertEqual((again, net.calls), ([], []))
        for hh, mm in ((15, 59), (18, 0)):
            out, net = go(self, at(2026, 11, 11, hh, mm), WEATHER)
            self.assertEqual((out, net.calls), ([], []))

    def test_forecast_round_with_real_hits(self):
        out, net = go(self, at(2026, 11, 8, 16, 10), WEATHER_PAST)
        self.assertEqual([(i["key"], i["worth"]) for i in out],
                         [("hava-hedd-2026-11-09", True), ("norma-ferq-2026-11-09", True)])
        self.assertEqual(len(net.calls), 2)

    def test_forecast_failures(self):
        now = at(2026, 11, 11, 16, 10)
        keys = [("hava-hedd-2026-11-12", False), ("norma-ferq-2026-11-12", False)]
        out, net = go(self, now, [("/v1/forecast", FC), ("/v1/marine", http(502))])
        self.assertEqual([(i["key"], i["worth"]) for i in out], keys)
        self.assertIn("dəniz proqnozu alınmadı", out[0]["why"])
        for reply in (http(500), b"<html>", b'{"error": true}'):
            out, net = go(self, now, [("/v1/forecast", reply), ("/v1/marine", MARINE)])
            self.assertEqual([(i["key"], i["worth"]) for i in out], keys)
            self.assertEqual(len(net.calls), 1)                     # proqnoz alınmayıbsa dəniz sorğusu getmir
        out, net = go(self, at(2026, 11, 14, 16, 10), WEATHER)      # cavabda 15 noyabr yoxdur
        self.assertEqual([i["worth"] for i in out], [False, False])
        self.assertIn("sabahkı gün yoxdur", out[0]["why"])


class SeaTest(unittest.TestCase):
    def setUp(self):
        self.data = oh.parse_sst(SST)

    def synth(self, last, now_vals, old_vals=None):
        cells = [(40.375, 50.125), (40.625, 49.625)]
        data = {last: dict(zip(cells, now_vals))}
        if old_vals:
            data[last - datetime.timedelta(days=7)] = dict(zip(cells, old_vals))
        return data

    def test_parse(self):
        self.assertEqual(sorted(self.data), [D(2026, 11, d) for d in range(2, 11)])
        self.assertEqual(self.data[D(2026, 11, 10)], {(40.375, 50.125): 16.93, (40.625, 49.625): 16.26,
                                                      (40.625, 49.875): 16.39, (40.625, 50.125): 16.58})
        head = b'{"table": {"columnNames": ["time", "latitude", "longitude", "sst"], "rows": '
        for bad in (b"{}", b"[]", b'{"table": {"columnNames": ["time"], "rows": []}}', head + b"[]}}",
                    head + b'[["x", 1, 2, 3]]}}', head + b"[[1]]}}"):
            with self.assertRaises(oh.Bad):
                oh.parse_sst(bad)

    def test_real_week(self):
        item, why = oh.sea_item(self.data, at(2026, 11, 14, 11, 10))
        check(self, item)
        self.assertEqual(item["title"],
                         "Abşeron yaxınlığında Xəzərin səth temperaturu 16,3–16,9 °C: bir həftədə 1,3 dərəcə soyuyub")
        self.assertIn("10 noyabrda Abşeron yarımadası yaxınlığında Xəzər dənizində suyun səth temperaturu 16,3–16,9 °C "
                      "olub (4 nöqtə üzrə orta 16,5 °C).", item["lead"])
        self.assertIn("Bir həftə əvvəl, 3 noyabrda eyni nöqtələrdə", item["body"][0])
        self.assertIn("(orta 17,8 °C) idi: orta göstərici 1,3 dərəcə azalıb.", item["body"][0])
        self.assertEqual(item["body"][-1], oh.SST_NOTE)
        self.assertEqual((item["key"], item["slot"]), ("xezer-su-2026-11-14", "11:10"))
        item, why = oh.sea_item(self.data, at(2026, 11, 15, 11, 10))
        self.assertIsNone(item)
        self.assertIn("köhnədir (son gün 10 noyabr)", why)

    def test_season_and_threshold(self):
        sat = at(2026, 11, 14, 11, 10)
        item, why = oh.sea_item(self.synth(D(2026, 11, 12), (16.0, 16.4), (15.8, 16.0)), sat)
        self.assertIsNone(item)                                     # +0,3: mövsümdən kənar xəbər deyil
        self.assertIn("0,3 dərəcədir", why)
        item, why = oh.sea_item(self.synth(D(2026, 11, 12), (16.0, 16.4), (15.0, 15.4)), sat)
        self.assertIn("16–16,4 °C: bir həftədə 1 dərəcə isinib", item["title"])
        self.assertIsNone(oh.sea_item(self.synth(D(2026, 11, 12), (16.0, 16.4)), sat)[0])
        self.assertIsNone(oh.sea_item({D(2026, 11, 12): {(40.375, 50.125): 16.0}}, sat)[0])
        july = at(2027, 7, 6, 11, 10)                               # mövsümdə hər gün, dəyişiklik az olsa da
        item, why = oh.sea_item(self.synth(D(2027, 7, 4), (24.0, 24.4), (23.8, 24.0)), july)
        check(self, item)
        self.assertEqual(item["title"],
                         "Abşeron yaxınlığında Xəzərin səth temperaturu 24–24,4 °C: bir həftədə 0,3 dərəcə isinib")
        item, why = oh.sea_item(self.synth(D(2027, 7, 4), (24.0, 24.0), (24.0, 24.0)), july)
        self.assertEqual(item["title"], "Abşeron yaxınlığında Xəzərin səth temperaturu 24 °C")
        self.assertIn("dəyişməyib", item["body"][0])
        item, why = oh.sea_item(self.synth(D(2027, 7, 4), (24.0, 24.4)), july)
        self.assertEqual(item["body"], [oh.SST_NOTE])
        self.assertIn("(2 nöqtə üzrə orta 24,2 °C)", item["lead"])

    def test_rounds(self):
        routes = [("erddap", SST)]
        out, net = go(self, at(2026, 11, 14, 11, 10), routes)       # şənbə
        self.assertEqual([(i["key"], i["worth"]) for i in out], [("xezer-su-2026-11-14", True)])
        self.assertEqual(net.calls, [oh.sst_url(D(2026, 11, 14))])
        self.assertEqual(net.agents[net.calls[0]], "8ulduz-bot/1.0 (+https://8ulduz.az)")   # ERDDAP: öz User-Agent-imiz
        out, net = go(self, at(2026, 11, 14, 12, 0), routes, {"xezer-su-2026-11-14"})
        self.assertEqual((out, net.calls), ([], []))
        for now in (at(2026, 11, 12, 11, 10), at(2026, 11, 14, 10, 59), at(2026, 11, 14, 13, 0)):
            out, net = go(self, now, routes)                        # cümə axşamı; pəncərədən kənar
            self.assertEqual((out, net.calls), ([], []), now)
        out, net = go(self, at(2027, 7, 6, 11, 10), routes)         # mövsümdə çərşənbə axşamı da; cavab köhnədir
        self.assertEqual([(i["key"], i["worth"]) for i in out], [("xezer-su-2027-07-06", False)])
        self.assertEqual(len(net.calls), 1)
        for reply in (http(404), b"<html>", b"{}"):
            out, net = go(self, at(2026, 11, 14, 11, 10), [("erddap", reply)])
            self.assertEqual([(i["key"], i["worth"]) for i in out], [("xezer-su-2026-11-14", False)])
            self.assertEqual(len(net.calls), 1)


class BudgetTest(unittest.TestCase):
    """İstehsalın bir günü: items() 10 dəqiqədən bir çağırılır, qayıdan hər açar done-a yazılır. Gündə ən çox 8 sorğu."""

    def day(self, y, m, d, routes):
        net, done, seen = Net(routes), set(), []
        t = at(y, m, d, 0, 5)
        while t.date() == D(y, m, d):
            for item in oh.items(ROOT, t, fetch=net, done=done):
                check(self, item)
                self.assertNotIn(item["key"], done)
                done.add(item["key"])
                seen.append(item)
            t += datetime.timedelta(minutes=10)
        self.assertLessEqual(len(net.calls), 8)
        return net, seen

    def test_quiet_saturday(self):
        net, seen = self.day(2026, 11, 14, ALL)
        self.assertEqual(len(net.calls), 7)                         # MHX, SWPC mətni, Kp ×2, OISST, proqnoz, dəniz
        self.assertEqual(net.n("k-index-forecast"), 2)
        self.assertEqual(sorted(i["key"] for i in seen), sorted([
            "meteohessas-2026-11-14", "maqnit-sorgu-2026-11-14-seher", "xezer-su-2026-11-14", "hava-hedd-2026-11-15",
            "norma-ferq-2026-11-15", "maqnit-sorgu-2026-11-14-axsam"]))

    def test_storm_day(self):
        net, seen = self.day(2026, 11, 8, ALL)                      # bazar: OISST yoxdur; axşam Kp sorğusu getmir
        self.assertEqual(len(net.calls), 6)
        self.assertEqual((net.n("k-index-forecast"), net.n("alerts")), (1, 1))
        self.assertEqual(sorted(i["key"] for i in seen if i["worth"]),
                         ["hava-hedd-2026-11-09", "maqnit-qasirgasi-2026-11-08", "norma-ferq-2026-11-09"])

    def test_dead_network_day(self):
        net, seen = self.day(2026, 11, 14, [])
        self.assertEqual(len(net.calls), 6)                         # hər pəncərədə bir cəhd, təkrar yoxdur
        self.assertFalse(any(i["worth"] for i in seen))


class SinaqTest(unittest.TestCase):
    def test_sample_run(self):
        net = Net(ALL)
        with patch.object(oh.time, "sleep"):
            md = "\n".join(oh.sinaq(ROOT, at(2026, 11, 12, 2, 30), fetch=net))
        for part in ("## 1.", "## 2.", "## 3.", "## 4.", "MHX: 12 noyabr Abşeronda", "Son real hal: 8 noyabr 2026",
                     "Son real hal (hədd): 9 noyabr 2026", "Son real hal (normadan fərq): 9 noyabr 2026",
                     "Sabah, 13 noyabr 2026", "bu gün sorğu getməzdi", "16,3–16,9 °C", "✅ Dərc olunardı",
                     "⏭ Dərc olunmazdı", "Bu sınaqda 7 sorğu göndərilib"):
            self.assertIn(part, md)
        self.assertNotIn("Sınaq xətası", md)
        self.assertEqual(len(net.calls), 7)
        self.assertEqual(len(net.calls), len(set(net.calls)))

    def test_sample_run_survives_dead_network(self):
        with patch.object(oh.time, "sleep"):
            md = "\n".join(oh.sinaq(ROOT, at(2026, 11, 12, 2, 30), fetch=Net([])))
        self.assertIn("# Hava və təbiət", md)
        self.assertIn("Yoxlama (yalnız son gün): URLError.", md)
        self.assertTrue(re.search(r"Sınaq xətası|Dərc olunmazdı", md))


if __name__ == "__main__":
    unittest.main()
