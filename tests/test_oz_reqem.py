"""Rəqəmlər (oz_reqem.py, mərhələ 3): hava keyfiyyəti, şahmat reytinqi, Speedtest, StatCounter, CISA KEV, App Store.
Şəbəkə yoxdur: tests/fixtures/oz_reqem/ — mənbələrin 2026-11-12 tarixli real cavablarından kəsiklər (Open-Meteo-nun 92 günlük
cavabından iki dövr; KEV kataloqunun 17 oktyabrdan sonrakı qeydləri, «count» ona uyğunlaşdırılıb; FIDE cədvəllərindən
doğum ili və «Exp.» sütunları çıxarılıb)."""
import contextlib
import datetime
import io
import json
import pathlib
import unittest
import urllib.error
from unittest.mock import patch

import oz_gundelik as og
import oz_reqem as r
import oz_xeber as ox

ROOT = pathlib.Path(__file__).resolve().parent.parent
FIX = ROOT / "tests" / "fixtures" / "oz_reqem"
D = datetime.date
KEYS = {"kind", "key", "title", "lead", "body", "credit", "link", "topic", "slot", "worth"}
LEADER = "Prezident İlham Əliyev"
OKT = D(2026, 10, 1)
_PAUSE = og.PAUSE


def setUpModule():
    og.PAUSE = 0  # testdə eyni sayta sorğular arasında gözləmə yoxdur


def tearDownModule():
    og.PAUSE = _PAUSE


def at(y, m, d, hh, mm=0):
    return datetime.datetime(y, m, d, hh, mm, tzinfo=r.BAKU)


def raw(name):
    return (FIX / name).read_bytes()


def text(name):
    return raw(name).decode("utf-8")


def doc(name):
    return json.loads(text(name))


def dump(obj):
    return json.dumps(obj, ensure_ascii=False).encode("utf-8")


def pages(aq="aq-noyabr.json"):
    """Bütün mənbələrin real cavabları, istehsalın soruşduğu ünvanlarla (StatCounter: oktyabr, yəni noyabrda soruşulan)."""
    table = {r.AQ_API.format(1): raw(aq), r.AQ_API.format(r.AQ_PAST): raw(aq), r.FIDE_OPEN: raw("fide-open.html"),
             r.FIDE_WOMEN: raw("fide-women.html"), r.SPEED_URL: raw("speedtest.html"), r.KEV_URL: raw("kev.json"),
             r.APP_URL: raw("apps.json")}
    for spec, name in zip(r.SC, ("sc-brauzer.csv", "sc-mobil-sistem.csv", "sc-telefon.csv")):
        table[r.sc_url(spec, OKT)] = raw(name)
    return table


class Fake:
    """Saxta fetch: ünvan -> bayt; siyahıda olmayan ünvan 404 verir (təkrar yoxlanmır), Exception dəyəri özü qalxır.
    Çağırışlar calls-dadır."""

    def __init__(self, table):
        self.table, self.calls = dict(table), []

    def __call__(self, url, timeout=None, headers=None):
        self.calls.append(url)
        value = self.table.get(url)
        if value is None:
            raise urllib.error.HTTPError(url, 404, "saxta şəbəkə: ünvan yoxdur", None, None)
        if isinstance(value, Exception):
            raise value
        return value


def kinds(found):
    return [i["kind"] for i in found]


def one(found, kind):
    hits = [i for i in found if i["kind"] == kind]
    assert len(hits) == 1, (kind, [i["key"] for i in found])
    return hits[0]


def aq_doc(days):
    """Süni cavab: {gün: (pm2_5, pm10, indeks)}, günün 24 saatı eyni qiymətlə; indeksi ozon alt-indeksi verir."""
    hourly = {"time": [], "pm2_5": [], "pm10": [], "european_aqi": [], "european_aqi_pm2_5": [], "european_aqi_pm10": [],
              "european_aqi_nitrogen_dioxide": [], "european_aqi_ozone": [], "european_aqi_sulphur_dioxide": []}
    for day, (pm25, pm10, aqi) in sorted(days.items()):
        for h in range(24):
            hourly["time"].append(f"{day.isoformat()}T{h:02d}:00")
            hourly["pm2_5"].append(pm25)
            hourly["pm10"].append(pm10)
            hourly["european_aqi"].append(aqi)
            hourly["european_aqi_ozone"].append(aqi)
            for f in ("european_aqi_pm2_5", "european_aqi_pm10", "european_aqi_nitrogen_dioxide", "european_aqi_sulphur_dioxide"):
                hourly[f].append(1)
    return {"latitude": 40.4, "longitude": 49.9, "utc_offset_seconds": 14400, "timezone": "Asia/Baku",
            "hourly_units": {"pm10": "μg/m³", "pm2_5": "μg/m³"}, "hourly": hourly}


def aq_two(today, yesterday, day=D(2026, 11, 12)):
    return r.aq_item(r.aq_parse(dump(aq_doc({day: today, day - r.DAY: yesterday}))), day)


class FormatTest(unittest.TestCase):
    def test_month_and_number_texts(self):
        self.assertEqual([r.month_loc(m) for m in (2, 4, 5, 6, 10, 12)],
                         ["fevralda", "apreldə", "mayda", "iyunda", "oktyabrda", "dekabrda"])
        self.assertEqual(r.month_in(D(2026, 10, 1)), "2026-cı ilin oktyabrında")
        self.assertEqual(r.month_in(D(2027, 4, 1)), "2027-ci ilin aprelində")
        self.assertEqual(r.month_in(D(2026, 6, 1)), "2026-cı ilin iyununda")
        self.assertEqual([r.pct(v) for v in (78.29, 4.5, 2.0, 0.03)], ["78,29%", "4,5%", "2%", "0,03%"])
        self.assertEqual(r.mbit(92.8), "92,80 Mbit/s")
        self.assertEqual(r._prev_month(D(2026, 1, 15)), D(2025, 12, 1))
        self.assertEqual(r._prev_month(D(2026, 11, 2)), OKT)
        self.assertEqual(r._fit("a" * 111, "b" * 110), "b" * 110)
        self.assertEqual(r._fit("a" * 111, "b" * 112), "b" * 112, "heç biri sığmırsa sonuncu qalır, qoruyucu onu dərc etmir")

    def test_parts_are_distinct_and_topics_are_known(self):
        names = [p[0] for p in r.PARTS]
        self.assertEqual(len(names), len(set(names)))
        self.assertEqual(len(names), 8)
        self.assertEqual({p[4] for p in r.PARTS}, {"təbiət", "idman", "texnologiya"})
        for _, _, credit, link, _, slot in r.PARTS:
            self.assertTrue(credit and link.startswith("https://"))
            self.assertRegex(slot, r"^\d\d:\d\d$")


class AirTest(unittest.TestCase):
    def test_parse_and_day_numbers(self):
        days = r.aq_parse(raw("aq-avqust.json"))
        self.assertEqual(sorted(days), [D(2026, 8, 29) + r.DAY * i for i in range(8)])
        self.assertEqual(r.aq_day(days[D(2026, 8, 31)]), {"pm2_5": 28.2, "pm10": 121.6, "peak": 83, "hour": 12, "cat": 4,
                                                          "main": "PM10 hissəcikləri", "ok": True})
        self.assertEqual(r.aq_day(days[D(2026, 8, 30)])["peak"], 35)
        self.assertEqual([r.aq_cat(v) for v in (0, 20, 20.5, 40, 60, 61, 80, 100, 101, 400)], [0, 0, 1, 1, 2, 3, 3, 4, 5, 5])

    def test_first_day_over_the_guideline_and_a_worse_category(self):
        days = r.aq_parse(raw("aq-avqust.json"))
        item = r.aq_item(days, D(2026, 8, 31))
        self.assertTrue(KEYS <= set(item))
        self.assertTrue(item["worth"])
        self.assertEqual((item["kind"], item["key"], item["topic"], item["slot"]),
                         ("hava-keyfiyyeti", "hava-keyfiyyeti-2026-08-31", "təbiət", "08:50"))
        self.assertEqual(item["title"], "Bakıda hava keyfiyyəti indeksi bu gün 83 olacaq, bu, «çox pis» kateqoriyasıdır: model proqnozu")
        self.assertIn("Open-Meteo-nun model proqnozuna görə, bu gün, avqustun 31-də Bakıda PM2.5 hissəciklərinin orta gündəlik "
                      "qatılığı 28,2 mkq/m³, PM10 hissəciklərinin orta gündəlik qatılığı 121,6 mkq/m³ olacaq.", item["lead"])
        self.assertIn("PM2.5 üçün 15, PM10 üçün 45 mkq/m³ təşkil edir.", item["lead"])
        self.assertEqual(item["body"][0], "Avropa hava keyfiyyəti indeksinin (EAQI) gün ərzində ən yüksək qiyməti 83 olacaq (saat 12:00): "
                                          "altı pilləli şkalada bu, «çox pis» kateqoriyasıdır. Həmin saatda indeksi PM10 hissəcikləri "
                                          "müəyyən edir.")
        self.assertEqual(item["body"][1], "Dünən, avqustun 30-da PM2.5 hissəciklərinin orta gündəlik qatılığı 5,1 mkq/m³, PM10 "
                                          "hissəciklərinin qatılığı 9,3 mkq/m³, indeksin ən yüksək qiyməti 35 («qənaətbəxş») olub.")
        self.assertIn("rəsmi xəbərdarlıq deyil", item["body"][2])
        self.assertIn("model", item["credit"])
        nxt = r.aq_item(days, D(2026, 9, 1))
        self.assertTrue(nxt["worth"], "kateqoriya «çox pis»dən «son dərəcə pis»ə keçib")
        self.assertEqual(nxt["title"], "Bakıda havanın keyfiyyəti bu gün «son dərəcə pis» kateqoriyasına keçəcək: model proqnozu")
        self.assertIn("ən yüksək qiyməti 125 olacaq (saat 23:00)", nxt["body"][0])

    def test_no_item_when_nothing_changed(self):
        days = r.aq_parse(raw("aq-avqust.json"))
        for day, why in ((D(2026, 9, 2), "diqqətəlayiq dəyişiklik yoxdur"), (D(2026, 9, 3), "diqqətəlayiq dəyişiklik yoxdur"),
                         (D(2026, 9, 4), "diqqətəlayiq dəyişiklik yoxdur"), (D(2026, 8, 29), "tam deyil")):
            item = r.aq_item(days, day)
            self.assertFalse(item["worth"], day)
            self.assertIn(why, item["why"])
            self.assertEqual(item["key"], f"hava-keyfiyyeti-{day.isoformat()}")
        self.assertIn("PM2.5 39,4 mkq/m³ (dünən 26,8 mkq/m³)", r.aq_item(days, D(2026, 9, 2))["why"])
        calm = r.aq_item(r.aq_parse(raw("aq-noyabr.json")), D(2026, 11, 12))
        self.assertFalse(calm["worth"])
        self.assertIn("indeks 34 «qənaətbəxş» (dünən 34 «qənaətbəxş»)", calm["why"])

    def test_guideline_start_without_a_bad_category(self):
        item = r.aq_item(r.aq_parse(raw("aq-avqust.json")), D(2026, 9, 5))
        self.assertTrue(item["worth"])
        self.assertEqual(item["title"], "Bakıda PM2.5 və PM10 hissəciklərinin qatılığı bu gün ÜST-nin tövsiyə həddini keçəcək: model proqnozu")
        self.assertIn("«orta» kateqoriyasıdır", item["body"][0])
        nov = r.aq_item(r.aq_parse(raw("aq-noyabr.json")), D(2026, 11, 3))
        self.assertTrue(nov["worth"], "hədd dünən də keçilib, amma kateqoriya «orta»dan «pis»ə keçib")
        self.assertEqual(nov["title"], "Bakıda hava keyfiyyəti indeksi bu gün 69 olacaq, bu, «pis» kateqoriyasıdır: model proqnozu")
        self.assertIn("Həmin saatda indeksi ozon müəyyən edir.", nov["body"][0])
        self.assertIn("26 mkq/m³", nov["lead"])

    def test_thresholds(self):
        self.assertFalse(aq_two((15.0, 45.0, 30), (10, 20, 30))["worth"], "hədd keçilməyib: 15,0 və 45,0")
        only25 = aq_two((15.1, 20, 30), (10, 20, 30))
        self.assertTrue(only25["worth"])
        self.assertIn("Bakının havasında PM2.5 hissəcikləri bu gün", only25["title"] + " | " + aq_two((15.1, 20, 30), (10, 20, 30), D(2026, 11, 13))["title"])
        self.assertNotIn("PM10 hissəcik", only25["title"])
        self.assertIn("PM10 hissəcik", aq_two((10, 45.1, 30), (10, 20, 30))["title"])
        self.assertFalse(aq_two((20, 50, 30), (15.1, 20, 30))["worth"], "hədd dünən də keçilmişdi: ilk gün deyil")
        self.assertTrue(aq_two((10, 20, 61), (10, 20, 60))["worth"], "«orta»dan «pis»ə")
        self.assertFalse(aq_two((10, 20, 79), (10, 20, 61))["worth"], "kateqoriya eynidir")
        self.assertFalse(aq_two((10, 20, 59), (10, 20, 10))["worth"], "«yaxşı»dan «orta»ya keçid xəbər deyil")
        self.assertFalse(aq_two((10, 20, 61), (10, 20, 85))["worth"], "yaxşılaşma xəbər deyil")
        for day in (D(2026, 11, 12), D(2026, 11, 13)):
            for today in ((15.1, 20, 30), (16, 46, 101), (10, 20, 81)):
                item = aq_two(today, (10, 20, 30), day)
                self.assertTrue(item["worth"])
                self.assertLessEqual(len(item["title"]), r.TITLE_MAX)

    def test_gates(self):
        base = doc("aq-noyabr.json")
        day = D(2026, 11, 3)

        def changed(fn):
            d = json.loads(json.dumps(base))
            fn(d)
            return dump(d)

        for fn, why in ((lambda d: d.update(timezone="GMT"), "Bakı vaxtı"), (lambda d: d.update(latitude=41.7), "Bakı üçün"),
                        (lambda d: d["hourly_units"].update(pm2_5="mg/m³"), "ölçü vahidi"),
                        (lambda d: d["hourly"]["pm10"].pop(), "natamamdır"), (lambda d: d["hourly"].pop("european_aqi_ozone"), "natamamdır"),
                        (lambda d: d["hourly"]["time"].__setitem__(0, "2026-11-01 00:00"), "vaxt oxunmadı"),
                        (lambda d: d.pop("hourly"), "gözlənilən şəkildə deyil")):
            with self.assertRaises(r.Bad) as ctx:
                r.aq_parse(changed(fn))
            self.assertIn(why, str(ctx.exception))
        with self.assertRaises(ValueError):
            r.aq_parse(b"<html>xeta</html>")
        i = base["hourly"]["time"].index("2026-11-03T07:00")
        hole = r.aq_parse(changed(lambda d: d["hourly"]["pm2_5"].__setitem__(i, None)))
        self.assertNotIn(day, hole, "boş saatı olan gün götürülmür")
        self.assertFalse(r.aq_item(hole, day)["worth"])
        self.assertFalse(r.aq_item(hole, day + r.DAY)["worth"], "dünəni natamam olan gün də yazılmır")
        neg = r.aq_parse(changed(lambda d: d["hourly"]["pm10"].__setitem__(i, -3)))
        self.assertNotIn(day, neg)
        short = r.aq_parse(changed(lambda d: [v.pop() for v in d["hourly"].values()]))
        self.assertNotIn(D(2026, 11, 12), short, "23 saatlıq gün tam deyil")
        peak = base["hourly"]["time"].index("2026-11-03T15:00")
        odd = r.aq_item(r.aq_parse(changed(lambda d: d["hourly"]["european_aqi"].__setitem__(peak, 90))), day)
        self.assertFalse(odd["worth"])
        self.assertIn("üst-üstə düşmür", odd["why"])

    def test_window_done_and_failure(self):
        fake = Fake(pages())
        self.assertEqual(r.items(ROOT, at(2026, 11, 3, 8, 29), fake), [])
        self.assertEqual(r.items(ROOT, at(2026, 11, 3, 10, 30), fake), [])
        self.assertEqual(fake.calls, [])
        found = r.items(ROOT, at(2026, 11, 3, 8, 40), fake)
        self.assertEqual(fake.calls, [r.AQ_API.format(1)])
        self.assertEqual(kinds(found), ["hava-keyfiyyeti"])
        self.assertTrue(found[0]["worth"])
        self.assertEqual(found[0]["key"], "hava-keyfiyyeti-2026-11-03")
        calm = r.items(ROOT, at(2026, 11, 12, 8, 40), Fake(pages()))
        self.assertEqual([(i["key"], i["worth"]) for i in calm], [("hava-keyfiyyeti-2026-11-12", False)])
        for done in ({"hava-keyfiyyeti-2026-11-03"}, {"hava-keyfiyyeti-xeta-2026-11-03"}):
            fake = Fake(pages())
            self.assertEqual(r.items(ROOT, at(2026, 11, 3, 8, 40), fake, done), [])
            self.assertEqual(fake.calls, [])
        for table in ({}, {r.AQ_API.format(1): b"{}"}, {r.AQ_API.format(1): TimeoutError("vaxt bitdi")}):
            fake = Fake(table)
            bad = r.items(ROOT, at(2026, 11, 3, 8, 40), fake)
            self.assertEqual([(i["key"], i["worth"]) for i in bad], [("hava-keyfiyyeti-xeta-2026-11-03", False)])
            self.assertTrue(bad[0]["why"])
            self.assertEqual(len(fake.calls), 1)


class FideTest(unittest.TestCase):
    def setUp(self):
        self.month, self.rows = r.fide_parse(text("fide-open.html"), "Players")
        self.month_w, self.women = r.fide_parse(text("fide-women.html"), "Women")

    def test_parse(self):
        self.assertEqual((self.month, self.month_w), (D(2026, 11, 1), D(2026, 11, 1)))
        self.assertEqual(len(self.rows), 100)
        self.assertEqual(self.rows[0], {"rank": 1, "id": "1503014", "name": "Carlsen, Magnus", "fed": "NOR", "rating": 2823})
        self.assertEqual([(x["rank"], x["rating"]) for x in self.rows if x["fed"] == "AZE"],
                         [(27, 2709), (36, 2692), (38, 2689), (54, 2662), (90, 2632)])
        self.assertEqual(text("fide-women.html").count("rank_span"), 101, "100-cü yerlə eyni reytinqli 101-ci sətir də səhifədədir")
        self.assertEqual(len(self.women), 100, "yalnız ilk 100 yer")
        self.assertEqual([(x["rank"], x["rating"]) for x in self.women if x["fed"] == "AZE"], [(59, 2389), (63, 2384), (82, 2363), (99, 2341)])
        self.assertEqual(r.fide_name({"id": "1", "name": "Abasov, Nijat"}), "Nijat Abasov")
        self.assertEqual(r.fide_name({"id": "1", "name": "Tək Ad"}), "Tək Ad")
        self.assertEqual(r.fide_name(self.rows[26]), "Şəhriyar Məmmədyarov")

    def test_item(self):
        item = r.fide_item(self.month, self.rows, self.women)
        self.assertTrue(KEYS <= set(item))
        self.assertTrue(item["worth"] and item["list"])
        self.assertEqual((item["kind"], item["key"], item["topic"], item["slot"]), ("sahmat-reytinq", "sahmat-reytinq-2026-11", "idman", "11:30"))
        self.assertEqual(item["title"], "FIDE noyabr reytinqini açıqlayıb: Şəhriyar Məmmədyarov 27-ci, Aydın Süleymanlı 36-cı yerdədir")
        self.assertEqual(item["lead"], "Beynəlxalq Şahmat Federasiyasının (FIDE) 2026-cı ilin noyabr reytinq siyahısına görə, klassik şahmat "
                                       "üzrə dünyanın ən yüksək reytinqli 100 şahmatçısı arasında Azərbaycanı 5 nəfər təmsil edir. Onların "
                                       "arasında ən yüksək yerdə Şəhriyar Məmmədyarov qərarlaşıb: 2709 reytinq xalı ilə 27-ci yer. Qadınların "
                                       "ilk yüzlüyündə Azərbaycanı 4 şahmatçı təmsil edir.")
        self.assertEqual(item["body"], ["27-ci yer: Şəhriyar Məmmədyarov — 2709", "36-cı yer: Aydın Süleymanlı — 2692",
                                        "38-ci yer: Teymur Rəcəbov — 2689", "54-cü yer: Məhəmməd Muradlı — 2662",
                                        "90-cı yer: Rauf Məmmədov — 2632", "Qadınlar, 59-cu yer: Ülviyyə Fətəliyeva — 2389",
                                        "Qadınlar, 63-cü yer: Gövhər Beydullayeva — 2384", "Qadınlar, 82-ci yer: Xanım Balacayeva — 2363",
                                        "Qadınlar, 99-cu yer: Günay Məmmədzadə — 2341"])
        self.assertEqual(r.fide_item(D(2026, 12, 1), self.rows, self.women)["title"],
                         "FIDE-nin dekabr reytinqi: dünyanın ilk yüzlüyündə 5 Azərbaycan şahmatçısı var")
        self.assertEqual(r.fide_item(D(2027, 1, 1), self.rows, self.women)["title"],
                         "Şəhriyar Məmmədyarov FIDE-nin yanvar reytinqində 27-ci yerdədir, ilk yüzlükdə 5 Azərbaycan şahmatçısı var")

    def test_one_player_and_none(self):
        solo = [dict(x, fed="XXX") if x["fed"] == "AZE" and x["rank"] != 27 else x for x in self.rows]
        item = r.fide_item(self.month, solo, [dict(x, fed="XXX") for x in self.women])
        self.assertTrue(item["worth"])
        self.assertEqual(item["title"], "FIDE noyabr reytinqini açıqlayıb: Şəhriyar Məmmədyarov 27-ci yerdədir")
        self.assertIn("Azərbaycanı bir nəfər, Şəhriyar Məmmədyarov təmsil edir: 2709 reytinq xalı ilə 27-ci yer.", item["lead"])
        self.assertNotIn("Qadınların", item["lead"])
        self.assertEqual(item["body"], ["27-ci yer: Şəhriyar Məmmədyarov — 2709"])
        none = r.fide_item(self.month, [dict(x, fed="XXX") for x in self.rows], self.women)
        self.assertFalse(none["worth"])
        self.assertEqual(none["key"], "sahmat-reytinq-2026-11")

    def test_gates(self):
        page = text("fide-open.html")
        with self.assertRaises(r.Bad):
            r.fide_parse(page, "Women")
        with self.assertRaises(r.Bad):
            r.fide_parse(page.replace("Top 100 Players November 2026", "Top Players"), "Players")
        cut = page.replace('<td><span class="rank_span">50</span></td>', "<td></td>")
        with self.assertRaises(r.Bad) as ctx:
            r.fide_parse(cut, "Players")
        self.assertIn("100 ardıcıl yer", str(ctx.exception))
        with self.assertRaises(r.Bad):
            r.fide_parse(page.split('<span class="rank_span">61</span>')[0], "Players")
        with self.assertRaises(r.Bad) as ctx:
            r.fide_parse(page.replace("<td class=rating_column>2709</td>", "<td class=rating_column>2809</td>"), "Players")
        self.assertIn("sıralanmayıb", str(ctx.exception))
        with self.assertRaises(r.Bad) as ctx:
            r.fide_parse(page.replace("<td class=rating_column>2709</td>", "<td class=rating_column>27o9</td>"), "Players")
        self.assertIn("sətir oxunmadı", str(ctx.exception))
        tail = text("fide-women.html").replace("<td class=rating_column>2340</td>\n</tr></table>", "<td class=rating_column>2339</td>\n</tr></table>")
        self.assertNotEqual(tail, text("fide-women.html"))
        with self.assertRaises(r.Bad):
            r.fide_parse(tail, "Women")

    def test_window_done_and_stale_list(self):
        fake = Fake(pages())
        found = r.items(ROOT, at(2026, 11, 2, 11, 10), fake)
        self.assertEqual(fake.calls, [r.FIDE_OPEN, r.FIDE_WOMEN])
        self.assertEqual([(i["key"], i["worth"]) for i in found], [("sahmat-reytinq-2026-11", True)])
        for now in (at(2026, 11, 2, 10, 59), at(2026, 11, 2, 13, 0), at(2026, 11, 6, 11, 10), at(2026, 11, 30, 11, 10)):
            fake = Fake({r.FIDE_OPEN: raw("fide-open.html"), r.FIDE_WOMEN: raw("fide-women.html")})
            self.assertEqual([i for i in r.items(ROOT, now, fake) if i["kind"] == "sahmat-reytinq"], [])
            self.assertNotIn(r.FIDE_OPEN, fake.calls)
        for done in ({"sahmat-reytinq-2026-11"}, {"sahmat-reytinq-sorgu-2026-11-02"}, {"sahmat-reytinq-xeta-2026-11-02"}):
            fake = Fake(pages())
            self.assertEqual(r.items(ROOT, at(2026, 11, 2, 11, 10), fake, done), [])
            self.assertEqual(fake.calls, [])
        # Dekabrın 1-də səhifədə hələ noyabr siyahısıdır: xəbər yoxdur, qadınlar siyahısı soruşulmur, sabah yenə yoxlanır.
        fake = Fake(pages())
        early = r.items(ROOT, at(2026, 12, 1, 11, 10), fake)
        self.assertEqual(fake.calls, [r.FIDE_OPEN])
        self.assertEqual([(i["key"], i["worth"]) for i in early], [("sahmat-reytinq-sorgu-2026-12-01", False)])
        self.assertIn("hələ noyabr 2026 siyahısıdır", early[0]["why"])
        table = pages()
        table[r.FIDE_WOMEN] = raw("fide-open.html")
        broken = r.items(ROOT, at(2026, 11, 2, 11, 10), Fake(table))
        self.assertEqual([(i["key"], i["worth"]) for i in broken], [("sahmat-reytinq-xeta-2026-11-02", False)])
        del table[r.FIDE_WOMEN]
        self.assertEqual([i["key"] for i in r.items(ROOT, at(2026, 11, 2, 11, 10), Fake(table))], ["sahmat-reytinq-xeta-2026-11-02"])


class SpeedTest(unittest.TestCase):
    def test_parse_and_item(self):
        data = r.speed_parse(text("speedtest.html"))
        self.assertEqual(data["month"], D(2026, 9, 1))
        self.assertEqual(data["mobileMedian"], {"cur": {"down": 98.92, "up": 23.8, "rank": 47, "month": "2026-09"},
                                                "prev": {"down": 98.62, "up": 23.55, "rank": 47, "month": "2026-08"}})
        self.assertEqual(data["fixedMedian"], {"cur": {"down": 92.94, "up": 93.8, "rank": 81, "month": "2026-09"},
                                               "prev": {"down": 92.8, "up": 93.75, "rank": 78, "month": "2026-08"}})
        item = r.speed_item(data)
        self.assertTrue(KEYS <= set(item))
        self.assertTrue(item["worth"])
        self.assertEqual((item["kind"], item["key"], item["topic"], item["slot"]),
                         ("internet-sureti", "internet-sureti-2026-09", "texnologiya", "10:30"))
        self.assertEqual(item["title"], "Azərbaycan mobil internetin sürətinə görə dünyada 47-ci, sabit internetdə 81-ci yerdədir: Speedtest")
        self.assertEqual(item["lead"], "Ookla şirkətinin «Speedtest Global Index» reytinqinin 2026-cı il sentyabr buraxılışına görə, Azərbaycan "
                                       "mobil internetin median yükləmə sürətinə görə dünyada 47-ci, sabit genişzolaqlı internetin sürətinə "
                                       "görə 81-ci yerdədir. Əvvəlki buraxılışda bu yerlər müvafiq olaraq 47-ci və 78-ci idi.")
        self.assertEqual(item["body"], ["Mobil internet: median yükləmə sürəti 98,92 Mbit/s (əvvəlki buraxılışda 98,62 Mbit/s), median "
                                        "göndərmə sürəti 23,80 Mbit/s.",
                                        "Sabit genişzolaqlı internet: median yükləmə sürəti 92,94 Mbit/s (əvvəlki buraxılışda 92,80 Mbit/s), "
                                        "median göndərmə sürəti 93,80 Mbit/s."])
        self.assertEqual(r.speed_item(dict(data, month=D(2026, 10, 1)))["title"],
                         "Speedtest: Azərbaycanda mobil internetin median sürəti 98,92 Mbit/s, sabit internetin sürəti 92,94 Mbit/s")
        self.assertEqual(r.speed_item(dict(data, month=D(2026, 11, 1)))["title"],
                         "Speedtest reytinqinin noyabr buraxılışı: Azərbaycan mobil internetdə 47-ci, sabit internetdə 81-ci yerdədir")

    def test_gates(self):
        page = text("speedtest.html")
        for old, new, why in (
                ('"previous_rank":47,"current_rank":47', '"previous_rank":47,"current_rank":46', "üst-üstə düşmür"),
                ('"previous_rank":78,"current_rank":81', '"previous_rank":77,"current_rank":81', "üst-üstə düşmür"),
                ('"current_rank":81,"download_mbps":"92.94"', '"current_rank":81,"download_mbps":"92.95"', "üst-üstə düşmür"),
                ('"currentMonth":1788220800000', '"currentMonth":1785542400000', "cari buraxılışın tarixi"),
                ("Azerbaijan&#x27;s Mobile", "Armenia&#x27;s Mobile", "Azərbaycanın səhifəsi deyil"),
                ("var data = ", "var veri = ", "«data» tapılmadı"),
                ("var display_data = {", "var display_data = [", "«display_data» oxunmadı"),
                ("var display_data = {", "var display_data = 5; var x = {", "obyekt deyil"),
                ('"month":"2026-09","prevMonth":"2026-08"}]\n', '"month":"2026-09","prevMonth":"2026-07"}]\n', "ardıcıl deyil")):
            self.assertIn(old, page, old)
            with self.assertRaises(r.Bad) as ctx:
                r.speed_parse(page.replace(old, new))
            self.assertIn(why, str(ctx.exception), old)
        with self.assertRaises(r.Bad):
            r.speed_parse("<html><title>Speedtest Global Index Azerbaijan</title></html>")

    def test_only_a_new_release_is_news(self):
        fake = Fake({r.SPEED_URL: raw("speedtest.html")})
        new = [i for i in r.items(ROOT, at(2026, 10, 12, 10, 40), fake) if i["kind"] == "internet-sureti"]
        self.assertEqual([(i["key"], i["worth"]) for i in new], [("internet-sureti-2026-09", True)])
        self.assertEqual(fake.calls, [r.SPEED_URL])
        fake = Fake({r.SPEED_URL: raw("speedtest.html")})
        old = r.items(ROOT, at(2026, 11, 12, 10, 40), fake)
        self.assertEqual([(i["key"], i["worth"]) for i in old], [("internet-sureti-sorgu-2026-11-12", False)])
        self.assertIn("yeni buraxılış hələ yoxdur: səhifədəki son buraxılış sentyabr 2026", old[0]["why"])
        for now in (at(2026, 10, 9, 10, 40), at(2026, 10, 29, 10, 40), at(2026, 10, 12, 9, 59), at(2026, 10, 12, 12, 0)):
            fake = Fake({r.SPEED_URL: raw("speedtest.html")})
            self.assertEqual([i for i in r.items(ROOT, now, fake) if i["kind"] == "internet-sureti"], [])
            self.assertNotIn(r.SPEED_URL, fake.calls)
        for done in ({"internet-sureti-2026-09"}, {"internet-sureti-sorgu-2026-10-12"}, {"internet-sureti-xeta-2026-10-12"}):
            fake = Fake({r.SPEED_URL: raw("speedtest.html")})
            self.assertEqual(r.items(ROOT, at(2026, 10, 12, 10, 40), fake, done), [])
            self.assertEqual(fake.calls, [])
        bad = r.items(ROOT, at(2026, 10, 12, 10, 40), Fake({r.SPEED_URL: b"<html><title>Just a moment...</title></html>"}))
        self.assertEqual([(i["key"], i["worth"]) for i in bad], [("internet-sureti-xeta-2026-10-12", False)])
        self.assertIn("Azərbaycanın səhifəsi deyil", bad[0]["why"])


class StatCounterTest(unittest.TestCase):
    def item(self, n, name):
        names, months = r.sc_parse(raw(name))
        return r.sc_item(r.SC[n], names, months, OKT)

    def test_url_and_parse(self):
        self.assertEqual(r.sc_url(r.SC[1], OKT),
                         "https://gs.statcounter.com/chart.php?device=Mobile&device_hidden=mobile&statType_hidden=os_combined&region_hidden=AZ"
                         "&granularity=monthly&statType=Operating%20System&region=Azerbaijan&fromInt=202609&toInt=202610"
                         "&fromMonthYear=2026-09&toMonthYear=2026-10&csv=1")
        self.assertIn("fromInt=202512&toInt=202601&fromMonthYear=2025-12&toMonthYear=2026-01", r.sc_url(r.SC[0], D(2026, 1, 1)))
        names, months = r.sc_parse(raw("sc-brauzer.csv"))
        self.assertEqual(names[:3], ["Chrome", "Safari", "Firefox"])
        self.assertEqual(sorted(months), [D(2026, 9, 1), OKT])
        self.assertEqual(months[OKT][:3], [78.29, 9.78, 4.51])

    def test_browsers(self):
        item = self.item(0, "sc-brauzer.csv")
        self.assertTrue(KEYS <= set(item))
        self.assertTrue(item["worth"] and item["list"])
        self.assertEqual((item["kind"], item["key"], item["topic"], item["slot"]), ("brauzer-payi", "brauzer-payi-2026-10", "texnologiya", "12:30"))
        self.assertEqual(item["title"], "Azərbaycanda brauzerlərin payı: oktyabrda Chrome 78,29%, Safari 9,78%, Firefox 4,51%")
        self.assertEqual(item["lead"], "StatCounter-in veb-səhifə baxışlarına əsaslanan statistikasına görə, 2026-cı ilin oktyabrında Azərbaycanda "
                                       "bütün cihazlardan veb-səhifə baxışlarında brauzerlərin payı belə olub: Chrome 78,29%, Safari 9,78%, "
                                       "Firefox 4,51%. Bir ay əvvəllə müqayisədə ən böyük dəyişiklik Safari üzrədir: pay 8,49%-dən 9,78%-ə "
                                       "yüksəlib.")
        self.assertEqual(item["body"], ["Chrome: 78,29% (sentyabrda 78,33%)", "Safari: 9,78% (sentyabrda 8,49%)",
                                        "Firefox: 4,51% (sentyabrda 5,47%)", "Samsung Internet: 3,62% (sentyabrda 3,92%)",
                                        "Edge: 1,92% (sentyabrda 2,09%)", "Opera: 1,13% (sentyabrda 1,07%)", "Qalanları birlikdə: 0,75%"])
        self.assertEqual(item["link"], "https://gs.statcounter.com/browser-market-share/all/azerbaijan")

    def test_mobile_systems_and_vendors(self):
        os_item = self.item(1, "sc-mobil-sistem.csv")
        self.assertTrue(os_item["worth"])
        self.assertEqual(os_item["key"], "mobil-sistem-payi-2026-10")
        self.assertEqual(os_item["title"], "Azərbaycanda mobil əməliyyat sistemlərinin payı: oktyabrda Android 82,39%, iOS 17,58%")
        self.assertIn("ən böyük dəyişiklik Android üzrədir: pay 84,31%-dən 82,39%-ə enib.", os_item["lead"])
        self.assertEqual(os_item["body"], ["Android: 82,39% (sentyabrda 84,31%)", "iOS: 17,58% (sentyabrda 15,67%)", "Qalanları birlikdə: 0,03%"])
        tel = self.item(2, "sc-telefon.csv")
        self.assertTrue(tel["worth"])
        self.assertEqual(tel["key"], "telefon-payi-2026-10")
        self.assertEqual(tel["title"], "Azərbaycanda telefon istehsalçılarının payı: oktyabrda Samsung 38,06%, Xiaomi 27,58%, Apple 17,58%")
        self.assertIn("mobil telefonlardan veb-səhifə baxışlarında cihaz istehsalçılarının payı belə olub: Samsung 38,06%, Xiaomi 27,58%, "
                      "Apple 17,58%.", tel["lead"])
        self.assertIn("ən böyük dəyişiklik Samsung üzrədir: pay 40,96%-dən 38,06%-ə enib.", tel["lead"])
        self.assertEqual(tel["body"], ["Samsung: 38,06% (sentyabrda 40,96%)", "Xiaomi: 27,58% (sentyabrda 28,71%)",
                                       "Apple: 17,58% (sentyabrda 15,67%)", "Honor: 2,96% (sentyabrda 2,51%)", "Huawei: 2% (sentyabrda 2,2%)",
                                       "İstehsalçısı müəyyən edilməyən cihazlar: 9,21% (sentyabrda 7,48%)", "Qalanları birlikdə: 2,6%"])

    def test_other_title_form_and_no_change(self):
        names, months = r.sc_parse(b'"Date","A","B","C","Other"\n2026-10,50,30,15,5\n2026-11,55,27,13,5\n')
        item = r.sc_item(r.SC[0], names, months, D(2026, 11, 1))
        self.assertTrue(item["worth"])
        self.assertEqual(item["title"], "A noyabrda Azərbaycanda veb-trafikin 55%-ni toplayıb, ikinci yerdə B, üçüncü yerdə C")
        self.assertIn("ən böyük dəyişiklik A üzrədir: pay 50%-dən 55%-ə yüksəlib.", item["lead"])
        self.assertEqual(item["body"], ["A: 55% (oktyabrda 50%)", "B: 27% (oktyabrda 30%)", "C: 13% (oktyabrda 15%)", "Qalanları birlikdə: 5%"])
        names, months = r.sc_parse(b'"Date","A","B","C","Other"\n2026-10,50,30,15,5\n2026-11,50.2,29.9,14.9,5\n')
        same = r.sc_item(r.SC[0], names, months, D(2026, 11, 1))
        self.assertFalse(same["worth"], "dəyişiklik yoxdursa, yazmırıq")
        self.assertIn("nəzərəçarpan dəyişiklik yoxdur: ən böyük fərq 0,2 faiz bəndi (A)", same["why"])
        self.assertEqual(same["key"], "brauzer-payi-2026-11")
        gone = r.sc_item(r.SC[0], names, months, D(2026, 12, 1))
        self.assertFalse(gone["worth"])
        self.assertIn("cədvəldə ötən ay", gone["why"])
        names, months = r.sc_parse(b'"Date","A","Unknown","Other"\n2026-10,90,9.8,0.2\n2026-11,99.3,0.4,0.3\n')
        self.assertFalse(r.sc_item(r.SC[2], names, months, D(2026, 11, 1))["worth"], "adı olan iki pay yoxdur")

    def test_gates(self):
        for raw_csv, why in ((b'"Date","A","B"\n2026-10,50,30\n', "cəmi 100% deyil"), (b'"Date","A","B"\n2026-10,50,x\n', "pay oxunmadı"),
                             (b'"Date","A","B"\n2026/10,50,50\n', "sətir oxunmadı"), (b'"Date","A","B"\n2026-10,50,25,25\n', "sətir oxunmadı"),
                             (b'"Ay","A","B"\n2026-10,50,50\n', "gözlənilən şəkildə deyil"), (b'"Date","A","A"\n2026-10,50,50\n', "sütun adları"),
                             (b"", "gözlənilən şəkildə deyil"), (b"<html>Error</html>", "gözlənilən şəkildə deyil"),
                             (b'"Date","A","B"\n2026-10,150,-50\n', "pay oxunmadı")):
            with self.assertRaises(r.Bad) as ctx:
                r.sc_parse(raw_csv)
            self.assertIn(why, str(ctx.exception), raw_csv)
        names, months = r.sc_parse(b'\xef\xbb\xbf"Date","A","B"\r\n2026-10,50.3,49.4\r\n\r\n')
        self.assertEqual((names, months), (["A", "B"], {OKT: [50.3, 49.4]}))

    def test_days_window_and_done(self):
        fake = Fake(pages())
        found = r.items(ROOT, at(2026, 11, 6, 12, 10), fake)
        self.assertEqual(fake.calls, [r.sc_url(spec, OKT) for spec in r.SC])
        self.assertEqual([(i["key"], i["worth"]) for i in found],
                         [("brauzer-payi-2026-10", True), ("mobil-sistem-payi-2026-10", True), ("telefon-payi-2026-10", True)])
        sc = {r.sc_url(spec, OKT): raw(name) for spec, name in zip(r.SC, ("sc-brauzer.csv", "sc-mobil-sistem.csv", "sc-telefon.csv"))}
        for day, want in ((1, []), (2, ["brauzer-payi"]), (3, ["brauzer-payi", "mobil-sistem-payi"]),
                          (4, ["brauzer-payi", "mobil-sistem-payi", "telefon-payi"]), (8, ["brauzer-payi", "mobil-sistem-payi", "telefon-payi"]),
                          (9, [])):
            fake = Fake(sc)
            got = [i["kind"] for i in r.items(ROOT, at(2026, 11, day, 12, 10), fake) if i["kind"].endswith("-payi")]
            self.assertEqual(got, want, day)
        for now in (at(2026, 11, 6, 11, 59), at(2026, 11, 6, 14, 0)):
            fake = Fake(sc)
            self.assertEqual([i for i in r.items(ROOT, now, fake) if i["kind"].endswith("-payi")], [])
            self.assertEqual([u for u in fake.calls if u in sc], [])
        fake = Fake(pages())
        rest = r.items(ROOT, at(2026, 11, 6, 12, 10), fake, {"brauzer-payi-2026-10", "telefon-payi-xeta-2026-11-06"})
        self.assertEqual(fake.calls, [r.sc_url(r.SC[1], OKT)])
        self.assertEqual(kinds(rest), ["mobil-sistem-payi"])
        table = pages()
        table[r.sc_url(r.SC[0], OKT)] = b"<html>429</html>"
        del table[r.sc_url(r.SC[2], OKT)]
        mixed = r.items(ROOT, at(2026, 11, 6, 12, 10), Fake(table))
        self.assertEqual([(i["key"], i["worth"]) for i in mixed],
                         [("brauzer-payi-xeta-2026-11-06", False), ("mobil-sistem-payi-2026-10", True), ("telefon-payi-xeta-2026-11-06", False)])


class KevTest(unittest.TestCase):
    def setUp(self):
        self.cat = r.kev_parse(raw("kev.json"))

    def test_parse(self):
        self.assertEqual(len(self.cat["rows"]), 31)
        self.assertEqual(self.cat["released"], datetime.datetime(2026, 11, 10, 19, 3, tzinfo=datetime.timezone.utc))
        self.assertEqual(self.cat["version"], "2026.11.10")
        self.assertIn({"cve": "CVE-2026-123158", "vendor": "OpenBSD", "product": "OpenSSH", "added": D(2026, 11, 9), "ransom": False},
                      self.cat["rows"])

    def test_week_item(self):
        item = r.kev_item(self.cat, D(2026, 11, 14), at(2026, 11, 14, 11))
        self.assertTrue(KEYS <= set(item))
        self.assertTrue(item["worth"] and item["list"])
        self.assertEqual((item["kind"], item["key"], item["topic"], item["slot"]), ("kev-hefte", "kev-hefte-2026-11-07", "texnologiya", "11:00"))
        self.assertEqual(item["title"], "İstismar olunan boşluqlar kataloquna bir həftədə 10 qeyd əlavə olunub: Barracuda Networks, Cisco, Google")
        self.assertEqual(item["lead"], "ABŞ-nin Kibertəhlükəsizlik və İnfrastruktur Təhlükəsizliyi Agentliyinin (CISA) məlumatına görə, "
                                       "7–13 noyabr tarixlərində «İstismar olunduğu məlum olan boşluqlar» (KEV) kataloquna 10 boşluq əlavə "
                                       "olunub. Onlar 9 istehsalçının məhsullarına aiddir. Kataloqda hazırda 31 qeyd var.")
        self.assertEqual(item["body"], [
            "Barracuda Networks: Multiple Products — CVE-2026-111560 (10 noyabr)",
            "Barracuda Networks: Barracuda Email Security Gateway (ESG) — CVE-2026-116606 (10 noyabr)",
            "Cisco: BroadWorks — CVE-2026-20320 (10 noyabr)", "Google: Chromium — CVE-2026-125350 (10 noyabr)",
            "GPUStack: GPUStack — CVE-2026-102895 (9 noyabr)", "IBM: Aspera Faspex — CVE-2026-123218 (9 noyabr)",
            "Microsoft: Office — CVE-2026-124194 (10 noyabr)", "OpenBSD: OpenSSH — CVE-2026-123158 (9 noyabr)",
            "Openwave Messaging Limited: Webtop Media Transcoder — CVE-2026-111793 (10 noyabr)",
            "SignalWire: FreeSwitch — CVE-2026-116779 (9 noyabr)"])

    def test_other_weeks_and_title_forms(self):
        now = at(2026, 11, 14, 11)
        w1 = r.kev_item(self.cat, D(2026, 11, 7), now)
        self.assertEqual((w1["key"], w1["worth"]), ("kev-hefte-2026-10-31", True))
        self.assertEqual(w1["title"], "Həftənin kibertəhlükəsizlik icmalı: istismar olunan 3 yeni boşluq, siyahıda Apple, SonicWall, WordPress")
        self.assertIn("31 oktyabr – 6 noyabr tarixlərində", w1["lead"])
        self.assertIn("kataloquna 3 boşluq əlavə olunub. Onlar 3 istehsalçının məhsullarına aiddir.", w1["lead"])
        self.assertEqual(w1["body"], ["Apple: Multiple Products — CVE-2024-27834 (4 noyabr)", "SonicWall: SonicOS SSLVPN — CVE-2026-19868 (6 noyabr)",
                                      "WordPress: WordPress Core — CVE-2026-119977 (3 noyabr)"])
        w2 = r.kev_item(self.cat, D(2026, 10, 31), now)
        self.assertEqual(w2["title"], "CISA bir həftədə 10 boşluğu istismar olunanlar kataloquna əlavə edib: Ivanti, PHP Group, Adobe")
        self.assertIn("24–30 oktyabr tarixlərində", w2["lead"])
        self.assertIn("Onlar 8 istehsalçının məhsullarına aiddir.", w2["lead"])
        none = r.kev_item(self.cat, D(2026, 11, 21), at(2026, 11, 21, 11))
        self.assertEqual((none["key"], none["worth"]), ("kev-hefte-2026-11-14", False))
        self.assertIn("əlavə olunmayıb", none["why"])

    def crafted(self, rows, released="2026-11-13T20:00:00Z"):
        return r.kev_parse(dump({"catalogVersion": "x", "dateReleased": released, "count": len(rows), "vulnerabilities": rows}))

    def row(self, n, day="2026-11-10", vendor="Acme", product="Router", ransom="Unknown"):
        return {"cveID": f"CVE-2026-{10000 + n}", "vendorProject": vendor, "product": product, "dateAdded": day,
                "knownRansomwareCampaignUse": ransom}

    def test_single_vendor_ransomware_and_long_week(self):
        now = at(2026, 11, 14, 11)
        one_row = r.kev_item(self.crafted([self.row(1)]), D(2026, 11, 14), now)
        self.assertTrue(one_row["worth"])
        self.assertIn("kataloquna 1 boşluq əlavə olunub. Kataloqda hazırda 1 qeyd var.", one_row["lead"])
        same = r.kev_item(self.crafted([self.row(1), self.row(2, ransom="Known")]), D(2026, 11, 14), now)
        self.assertIn("kataloquna 2 boşluq əlavə olunub. Hamısı bir istehsalçının məhsullarına aiddir.", same["lead"])
        self.assertEqual(same["body"][-1], "Fidyə proqramı kampaniyalarında istifadəsi məlum olan boşluqların sayı: 1.")
        many = r.kev_item(self.crafted([self.row(i, vendor=f"V{i:02d}") for i in range(17)]), D(2026, 11, 14), now)
        self.assertEqual(len(many["body"]), r.KEV_LINES + 1)
        self.assertEqual(many["body"][-1], "Daha 2 boşluq kataloqun səhifəsindədir.")
        self.assertLessEqual(len(many["title"]), r.TITLE_MAX)
        long_names = r.kev_item(self.crafted([self.row(i, vendor="Çox Uzun Adlı İstehsalçı Şirkəti " + "x" * 30 + str(i)) for i in range(3)]),
                                D(2026, 11, 14), now)
        self.assertEqual(long_names["title"], "İstismar olunan boşluqlar kataloquna bir həftədə 3 qeyd əlavə olunub")

    def test_gates(self):
        base = doc("kev.json")
        for fn, why in ((lambda d: d.update(count=30), "«count» sahəsi"), (lambda d: d.update(count=True), "«count» sahəsi"),
                        (lambda d: d.update(dateReleased="dünən"), "tarixi oxunmadı"), (lambda d: d.update(vulnerabilities=[]), "gözlənilən şəkildə"),
                        (lambda d: d["vulnerabilities"][5].update(dateAdded="10.11.2026"), "əlavə tarixi"),
                        (lambda d: d["vulnerabilities"].__setitem__(3, "x"), "qeyd oxunmadı")):
            d = json.loads(json.dumps(base))
            fn(d)
            with self.assertRaises(r.Bad) as ctx:
                r.kev_parse(dump(d))
            self.assertIn(why, str(ctx.exception))
        now = at(2026, 11, 14, 11)
        for rows, why in (([self.row(1, vendor="")], "oxunmayan var"), ([self.row(1, product=" ")], "oxunmayan var"),
                          ([self.row(1), self.row(1)], "oxunmayan var"), ([dict(self.row(1), cveID="CVE-26-1")], "oxunmayan var")):
            item = r.kev_item(self.crafted(rows), D(2026, 11, 14), now)
            self.assertFalse(item["worth"])
            self.assertIn(why, item["why"])
        stale = r.kev_item(self.crafted([self.row(1)], released="2026-11-09T10:00:00Z"), D(2026, 11, 14), now)
        self.assertFalse(stale["worth"], "kataloqun tarixi son qeyddən əvvəldir")
        self.assertIn("uyğun gəlmir", stale["why"])
        future = r.kev_item(self.cat, D(2026, 11, 7), at(2026, 11, 7, 11))
        self.assertFalse(future["worth"], "kataloqun tarixi indidən sonradır")

    def test_saturday_window_and_done(self):
        fake = Fake(pages())
        found = r.items(ROOT, at(2026, 11, 14, 12, 10), fake)
        self.assertEqual(fake.calls, [r.KEV_URL])
        self.assertEqual([(i["key"], i["worth"]) for i in found], [("kev-hefte-2026-11-07", True)])
        for now in (at(2026, 11, 13, 12, 10), at(2026, 11, 15, 12, 10), at(2026, 11, 14, 10, 29), at(2026, 11, 14, 12, 30)):
            fake = Fake(pages())
            self.assertEqual([i for i in r.items(ROOT, now, fake) if i["kind"] == "kev-hefte"], [])
            self.assertNotIn(r.KEV_URL, fake.calls)
        for done in ({"kev-hefte-2026-11-07"}, {"kev-hefte-xeta-2026-11-14"}):
            fake = Fake(pages())
            self.assertEqual(r.items(ROOT, at(2026, 11, 14, 12, 10), fake, done), [])
            self.assertEqual(fake.calls, [])
        bad = r.items(ROOT, at(2026, 11, 14, 12, 10), Fake({r.KEV_URL: b'{"count": 2, "vulnerabilities": [{}]}'}))
        self.assertEqual([(i["key"], i["worth"]) for i in bad], [("kev-hefte-xeta-2026-11-14", False)])
        self.assertIn("«count» sahəsi", bad[0]["why"])


class AppTest(unittest.TestCase):
    def setUp(self):
        self.data = r.app_parse(raw("apps.json"))

    def test_parse_and_item(self):
        self.assertEqual(self.data["updated"], at(2026, 11, 12, 20, 19).replace(second=4))
        self.assertEqual(len(self.data["apps"]), 25)
        self.assertEqual(self.data["apps"][0], {"name": "mygov", "artist": "Innovation and Digital Development Agency", "id": "1533956540"})
        item = r.app_item(self.data, D(2026, 11, 13), at(2026, 11, 13, 17, 30))
        self.assertTrue(KEYS <= set(item))
        self.assertTrue(item["worth"] and item["list"])
        self.assertEqual((item["kind"], item["key"], item["topic"], item["slot"]), ("app-store", "app-store-2026-11-13", "texnologiya", "17:30"))
        self.assertEqual(item["title"], "«mygov» App Store-un Azərbaycan üzrə pulsuz tətbiqlər siyahısında birinci yerdədir")
        self.assertEqual(item["lead"], "Apple-ın 12 noyabr tarixli açıq məlumatına görə, App Store-un Azərbaycan mağazasında pulsuz "
                                       "tətbiqlərin siyahısına («Top Free Apps») «mygov» başçılıq edir. İkinci yerdə «SİMA - Rəqəmsal İmza», "
                                       "üçüncü yerdə «Leobank - Mobile Bank və Kart» qərarlaşıb.")
        self.assertEqual(len(item["body"]), 10)
        self.assertEqual(item["body"][0], "1. «mygov» — Innovation and Digital Development Agency")
        self.assertEqual(item["body"][3], "4. «ChatGPT» — OpenAI OpCo, LLC")
        self.assertEqual(item["body"][9], "10. «PASHA Insurance» — Pasha Insurance Company PJSC")

    def test_title_forms_and_freshness(self):
        short = {"updated": self.data["updated"], "apps": [dict(a, name=f"Tətbiq {i}") for i, a in enumerate(self.data["apps"], 1)]}
        self.assertEqual(r.app_item(short, D(2026, 11, 13), at(2026, 11, 13, 17, 30))["title"],
                         "«Tətbiq 1» App Store-un Azərbaycan üzrə pulsuz tətbiqlər siyahısında birinci yerdədir")
        late = dict(short, updated=at(2026, 11, 19, 20, 0))
        self.assertEqual(r.app_item(late, D(2026, 11, 20), at(2026, 11, 20, 17, 30))["title"],
                         "App Store-da bu həftə: Azərbaycan üzrə pulsuz tətbiqlər siyahısına «Tətbiq 1» başçılıq edir")
        later = dict(short, updated=at(2026, 11, 26, 20, 0))
        self.assertEqual(r.app_item(later, D(2026, 11, 27), at(2026, 11, 27, 17, 30))["title"],
                         "App Store-un Azərbaycan üzrə pulsuz tətbiqlər siyahısında ilk üçlük: «Tətbiq 1», «Tətbiq 2» və «Tətbiq 3»")
        self.assertEqual(r.app_item(dict(self.data, updated=at(2026, 11, 26, 20, 0)), D(2026, 11, 27), at(2026, 11, 27, 17, 30))["title"],
                         "«mygov» App Store-un Azərbaycan üzrə pulsuz tətbiqlər siyahısında birinci yerdədir", "uzun adlarla üçlük başlığa sığmır")
        old = r.app_item(self.data, D(2026, 11, 20), at(2026, 11, 20, 17, 30))
        self.assertFalse(old["worth"])
        self.assertIn("köhnədir: 12 noyabr", old["why"])
        self.assertFalse(r.app_item(self.data, D(2026, 11, 12), at(2026, 11, 12, 17, 30))["worth"], "siyahının tarixi indidən sonradır")

    def test_gates(self):
        base = doc("apps.json")
        for fn, why in ((lambda f: f.update(country="us"), "Azərbaycan üzrə"), (lambda f: f.update(title="Top Paid Apps"), "Azərbaycan üzrə"),
                        (lambda f: f.update(updated="dünən"), "tarixi oxunmadı"), (lambda f: f.update(results=f["results"][:9]), "natamamdır"),
                        (lambda f: f["results"].__setitem__(1, dict(f["results"][0])), "təkrarlanan"),
                        (lambda f: f["results"][4].update(name="  "), "boş olan"), (lambda f: f["results"][4].pop("artistName"), "boş olan"),
                        (lambda f: f.update(results="yox"), "gözlənilən şəkildə")):
            d = json.loads(json.dumps(base))
            fn(d["feed"])
            with self.assertRaises(r.Bad) as ctx:
                r.app_parse(dump(d))
            self.assertIn(why, str(ctx.exception))
        with self.assertRaises(r.Bad):
            r.app_parse(b"[]")

    def test_friday_window_done_and_leadership(self):
        fake = Fake(pages())
        found = r.items(ROOT, at(2026, 11, 13, 17, 10), fake)
        self.assertEqual(fake.calls, [r.APP_URL])
        self.assertEqual([(i["key"], i["worth"]) for i in found], [("app-store-2026-11-13", True)])
        for now in (at(2026, 11, 12, 17, 10), at(2026, 11, 14, 17, 10), at(2026, 11, 13, 16, 59), at(2026, 11, 13, 19, 0)):
            fake = Fake(pages())
            self.assertEqual([i for i in r.items(ROOT, now, fake) if i["kind"] == "app-store"], [])
            self.assertNotIn(r.APP_URL, fake.calls)
        for done in ({"app-store-2026-11-13"}, {"app-store-xeta-2026-11-13"}):
            fake = Fake(pages())
            self.assertEqual(r.items(ROOT, at(2026, 11, 13, 17, 10), fake, done), [])
            self.assertEqual(fake.calls, [])
        d = doc("apps.json")
        d["feed"]["results"][6]["name"] = LEADER
        held = r.items(ROOT, at(2026, 11, 13, 17, 10), Fake({r.APP_URL: dump(d)}))
        self.assertEqual([(i["key"], i["worth"]) for i in held], [("app-store-2026-11-13", False)])
        self.assertIn("rəhbərliyin adı keçir", held[0]["why"])


class ItemsTest(unittest.TestCase):
    def test_never_raises_and_closed_windows_send_nothing(self):
        fake = Fake(pages())
        for now in (at(2026, 11, 12, 3, 0), at(2026, 11, 12, 15, 0), at(2026, 11, 12, 23, 59)):
            self.assertEqual(r.items(ROOT, now, fake), [])
        self.assertEqual(fake.calls, [])

        def boom(url, timeout=None, headers=None):
            raise RuntimeError("partladı")

        for now in (at(2026, 11, 2, 12, 10), at(2026, 11, 14, 11, 0), at(2026, 11, 13, 17, 10), at(2026, 11, 12, 8, 40)):
            found = r.items(ROOT, now, boom)
            self.assertTrue(found)
            self.assertTrue(all(not i["worth"] and i["why"] and "-xeta-" in i["key"] and KEYS <= set(i) for i in found))
        with patch.object(og, "_default_fetch", return_value=None):
            lost = r.items(ROOT, at(2026, 11, 12, 8, 40))
        self.assertEqual([(i["key"], i["worth"]) for i in lost], [("hava-keyfiyyeti-xeta-2026-11-12", False)])
        self.assertEqual(r.items(ROOT, "saat deyil", fake), [])
        naive = r.items(ROOT, datetime.datetime(2026, 11, 3, 8, 40), Fake(pages()))
        self.assertEqual(kinds(naive), ["hava-keyfiyyeti"], "ofsetsiz vaxt Bakı vaxtıdır")
        utc = r.items(ROOT, datetime.datetime(2026, 11, 3, 4, 40, tzinfo=datetime.timezone.utc), Fake(pages()))
        self.assertEqual(kinds(utc), ["hava-keyfiyyeti"])

    def test_dropped_connection_is_retried_a_few_times_then_the_day_is_closed(self):
        """Bağlantı qırılanda (oz_gundelik._Net) ünvan ən çox TRIES dəfə yoxlanır; vaxt aşımı və HTTP xətası təkrarlanmır."""
        fake = Fake({r.AQ_API.format(1): urllib.error.URLError("Connection reset by peer")})
        lost = r.items(ROOT, at(2026, 11, 12, 8, 40), fake)
        self.assertEqual(len(fake.calls), og.TRIES)
        self.assertEqual([(i["key"], i["worth"]) for i in lost], [("hava-keyfiyyeti-xeta-2026-11-12", False)])
        self.assertIn("URLError", lost[0]["why"])
        fake = Fake({r.AQ_API.format(1): urllib.error.URLError("Connection reset by peer")})
        self.assertEqual(r.items(ROOT, at(2026, 11, 12, 8, 50), fake, {i["key"] for i in lost}), [])
        self.assertEqual(fake.calls, [])

    def test_one_request_round_a_day_when_every_key_goes_to_done(self):
        """Canlıda dərc hissəsi qayıdan hər açarı done-a yazır («hamisi»): hər növ gündə bir sorğu turu, uğursuz gündə də."""
        for day, table, most in ((D(2026, 11, 2), pages(), 4), (D(2026, 11, 6), pages(), 5), (D(2026, 11, 13), pages(), 3),
                                 (D(2026, 11, 14), pages(), 3), (D(2026, 11, 12), pages(), 2), (D(2026, 11, 3), {}, 4),
                                 (D(2026, 11, 14), {}, 3)):
            fake, done, seen = Fake(table), set(), []
            now = datetime.datetime(day.year, day.month, day.day, 0, 5, tzinfo=r.BAKU)
            while now.date() == day:
                for item in r.items(ROOT, now, fake, done):
                    self.assertNotIn(item["key"], done)
                    done.add(item["key"])
                    seen.append(item)
                now += datetime.timedelta(minutes=10)
            self.assertEqual(len(fake.calls), len(set(fake.calls)), (day, "hər ünvan gündə bir dəfə"))
            self.assertEqual(len(fake.calls), most, (day, fake.calls))
            for item in seen:
                self.assertTrue(KEYS <= set(item))
                if item["worth"]:
                    self.assertLessEqual(len(item["title"]), r.TITLE_MAX, item["title"])
                    self.assertNotRegex(item["title"] + item["lead"], r"[А-Яа-яЁё]")
                else:
                    self.assertTrue(item["why"])

    def test_real_day_gives_the_expected_items(self):
        fake, done, out = Fake(pages()), set(), []
        now = at(2026, 11, 6, 0, 5)
        while now.date() == D(2026, 11, 6):
            for item in r.items(ROOT, now, fake, done):
                done.add(item["key"])
                out.append((item["key"], item["worth"]))
            now += datetime.timedelta(minutes=30)
        self.assertEqual(out, [("hava-keyfiyyeti-2026-11-06", False), ("brauzer-payi-2026-10", True), ("mobil-sistem-payi-2026-10", True),
                               ("telefon-payi-2026-10", True), ("app-store-2026-11-06", False)])


class SinaqTest(unittest.TestCase):
    def test_sample_page(self):
        fake = Fake(pages())
        md = "\n".join(r.sinaq(ROOT, at(2026, 11, 12, 20, 0), fake))
        for head in ("## Rəqəmlər: öz xəbərlər (12.11.2026 20:00, Bakı vaxtı)", "## 1. Bakıda havanın keyfiyyəti", "## 2. Şahmat: FIDE",
                     "## 3. İnternetin sürəti", "## 4. StatCounter", "## 5. İstismar olunan boşluqlar", "## 6. App Store",
                     "## Mənbələrə çıxış (bu sınaqda)"):
            self.assertIn(head, md)
        self.assertIn("yoxdur (heç bir növün pəncərəsi açıq deyil)", md)
        self.assertIn("### Bakıda hava keyfiyyəti indeksi bu gün 69 olacaq, bu, «pis» kateqoriyasıdır: model proqnozu", md)
        self.assertIn("### FIDE noyabr reytinqini açıqlayıb: Şəhriyar Məmmədyarov 27-ci, Aydın Süleymanlı 36-cı yerdədir", md)
        self.assertIn("yeni buraxılış hələ yoxdur: bu, sentyabr 2026 buraxılışıdır", md)
        self.assertIn("### Azərbaycanda brauzerlərin payı: oktyabrda Chrome 78,29%, Safari 9,78%, Firefox 4,51%", md)
        self.assertIn("### Həftənin kibertəhlükəsizlik icmalı: istismar olunan 3 yeni boşluq, siyahıda Apple, SonicWall, WordPress", md)
        self.assertIn("«mygov»", md)
        self.assertIn("✅ Dərc olunardı", md)
        self.assertIn("⏭ Dərc olunmazdı", md)
        self.assertEqual(len(fake.calls), 9)
        self.assertEqual(len(set(fake.calls)), 9)

    def test_sample_page_survives_a_dead_network(self):
        md = "\n".join(r.sinaq(ROOT, at(2026, 11, 14, 11, 0), Fake({})))
        self.assertIn("## Mənbələrə çıxış (bu sınaqda)", md)
        self.assertIn("HTTPError 404", md)
        self.assertNotIn("Traceback", md)
        self.assertNotIn("Sınaq xətası", md)

    def test_cli(self):
        out = io.StringIO()
        with patch.object(og, "_default_fetch", return_value=Fake(pages())), contextlib.redirect_stdout(out):
            self.assertEqual(r.main(["--sinaq", "--root", str(ROOT), "--now", "2026-11-12T20:00+04:00"]), 0)
        self.assertIn("## Rəqəmlər: öz xəbərlər (12.11.2026 20:00, Bakı vaxtı)", out.getvalue())
        self.assertIn("## 6. App Store", out.getvalue())
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            self.assertEqual(r.main([]), 0)
        self.assertIn("Sınaq: python oz_reqem.py --sinaq", out.getvalue())


if __name__ == "__main__":
    unittest.main()
