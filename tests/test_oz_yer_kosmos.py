"""Öz xəbər, mərhələ 2: yer və kosmos şablonları (oz_yer_kosmos.py). Şəbəkə yoxdur: bütün sorğular saxtadır.
Real hal tests/fixtures/oz_yer_kosmos-dadır (2026-11-10-da götürülmüş cavablar, yalnız lazım olan hissəsi):
- USGS: 9 noyabr İmamoğlu (Türkiyə) zəlzələsi (1 günlük sorğu) və 10 oktyabr – 10 noyabr, M4+ (67 zəlzələ);
- AFAD: 2–10 noyabr, M4+ (Kozan/Adana zəlzələsi, dənizdəki iki təkan);
- seismology.az siyahısı; JPL CAD: 1–12 noyabr Aydan yaxın 9 keçid və 2–23 noyabr 0,05 AB-dən yaxın 72 keçid;
- Launch Library 2: 10 noyabrda qarşıdakı 10 buraxılış, son pilotlu buraxılışlar, son Starship uçuşları."""
import datetime
import json
import pathlib
import unittest
import urllib.error
from unittest.mock import patch

import oz_xeber as ox
import oz_yer_kosmos as om

ROOT = pathlib.Path(__file__).resolve().parent.parent
FIX = pathlib.Path(__file__).resolve().parent / "fixtures" / "oz_yer_kosmos"
BAKU = ox.BAKU
UTC = datetime.timezone.utc
D = datetime.date
MIN = datetime.timedelta(minutes=1)
NEED = {"kind", "key", "title", "lead", "body", "credit", "link", "topic", "slot", "worth"}


def fx(name):
    return (FIX / name).read_bytes()


def at(y, m, d, hh, mm=0):
    return datetime.datetime(y, m, d, hh, mm, tzinfo=BAKU)


def utc(y, m, d, hh, mm=0, ss=0):
    return datetime.datetime(y, m, d, hh, mm, ss, tzinfo=UTC)


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


def feat(qid, when, mag, place, lat, lon, depth=10, status="reviewed", typ="earthquake", ids=None):
    return {"type": "Feature", "id": qid, "geometry": {"type": "Point", "coordinates": [lon, lat, depth]},
            "properties": {"mag": mag, "place": place, "time": int(when.timestamp() * 1000), "status": status, "type": typ,
                           "ids": ids or f",{qid},", "url": f"https://earthquake.usgs.gov/earthquakes/eventpage/{qid}"}}


def usgs(feats, gen=None):
    meta = {} if gen is None else {"generated": int(gen.timestamp() * 1000)}
    return json.dumps({"type": "FeatureCollection", "metadata": meta, "features": feats}).encode("utf-8")


def quakes(*feats):
    return om.parse_usgs(usgs(list(feats)))["quakes"]


REAL = json.loads(fx("usgs-1d-2026-11-10.json").decode("utf-8"))["features"]   # İmamoğlu, 9 noyabr 12:28:18 UTC
AFAD = "afad-2026-11-02_11-10.json"
NOW = at(2026, 11, 9, 17, 50)   # tik: 17 mod 6 = 5, dəqiqə 50–59
IRAN = ("30 km S of Shiraz, Iran", 29.3, 52.5)
TURKEY = ("17 km NW of İmamoğlu, Turkey", 37.39, 35.54)
TAJIK = ("76 km W of Murghob, Tajikistan", 38.05, 73.11)
EMPTY = ("earthquake.usgs.gov", usgs([]))


def worth(items_):
    return [i for i in items_ if i["worth"]]


def by_key(items_, key):
    return next(i for i in items_ if i["key"] == key)


class HelpersTest(unittest.TestCase):
    def test_tick(self):
        for hh, mm, want in ((0, 5, True), (1, 10, True), (1, 5, False), (13, 10, True), (10, 40, True), (12, 0, True),
                             (17, 50, True), (17, 49, False), (18, 0, True)):
            self.assertEqual(om.tick(at(2026, 11, 12, hh, mm)), want, (hh, mm))

    def test_numbers_and_suffixes(self):
        self.assertEqual([om.num(15.35), om.num(10.0), om.num(8.76, 1)], ["15,35", "10", "8,8"])
        self.assertEqual([om.poss(x) for x in ("0,48", "0,14", "0,50", "0,06", "0,97", "3")],
                         ["0,48-i", "0,14-ü", "0,50-si", "0,06-sı", "0,97-si", "3-ü"])

    def test_fold_keeps_only_azerbaijani_marks(self):
        self.assertEqual([om.fold(x) for x in ("Kāzerūn", "Kŭlob", "İmamoğlu", "Türkmenbaşy", "Gölbaşı Çay")],
                         ["Kazerun", "Kulob", "İmamoğlu", "Türkmenbaşy", "Gölbaşı Çay"])

    def test_genitive_by_sound(self):
        self.assertEqual([om.gen(x) for x in ("Kozan", "İmamoğlu", "Kyzyl-Eshme", "Murghob", "Təbriz")],
                         ["Kozanın", "İmamoğlunun", "Kyzyl-Eshmenin", "Murghobun", "Təbrizin"])

    def test_distance_to_baku(self):
        self.assertEqual(om.baku_km(37.39, 35.5394), 1280)
        self.assertEqual(om.baku_km(37.5505, 35.626), 1270)
        self.assertAlmostEqual(om.km_between((37.5505, 35.626), (37.39, 35.5394)), 19.4, places=1)

    def test_place_translation(self):
        w = lambda s: om.where(om.place(s))
        self.assertEqual(w("17 km NW of İmamoğlu, Turkey"), ("Türkiyədə", "Türkiyədə, İmamoğlunun 17 km şimal-qərbində"))
        self.assertEqual(w("93 km ESE of Kyzyl-Eshme, Kyrgyzstan")[1], "Qırğızıstanda, Kyzyl-Eshmenin 93 km şərq-cənub-şərqində")
        self.assertEqual(w("21 km W of Kāzerūn, Iran")[1], "İranda, Kazerunun 21 km qərbində")
        self.assertEqual(w("10 km S of Tabriz, Iran")[1], "İranda, Təbrizin 10 km cənubunda")
        self.assertEqual(w("Turkey-Iran border region")[0], "Türkiyə-İran sərhəd bölgəsində")
        self.assertEqual(w("eastern Turkey")[0], "Türkiyənin şərqində")
        self.assertEqual(w("northwestern Iran")[0], "İranın şimal-qərbində")
        self.assertEqual(w("Caspian Sea"), ("Xəzər dənizində", "Xəzər dənizində"))
        self.assertIsNone(om.place("bilinməyən yer"))
        self.assertIsNone(om.where(None))
        self.assertIsNone(w("101 km SSE of Palekastro, Greece"))

    def test_region_filter(self):
        o = lambda s, lat=38.0, lon=45.0: om.outside(om.place(s), lat, lon)
        self.assertEqual(o("17 km NW of İmamoğlu, Turkey"), "")
        self.assertEqual(o("101 km SSE of Palekastro, Greece"), "region xaricində (Yunanıstan)")
        self.assertTrue(o("5 km S of Ganja, Azerbaijan").startswith("Azərbaycan"))
        self.assertTrue(o("Azerbaijan-Iran border region").startswith("Azərbaycan"))
        self.assertEqual(o("12 km S of Makhachkala, Russia", 42.87, 47.5), "")
        self.assertEqual(o("40 km E of Aktash, Russia", 49.5, 87.0), "Rusiyada, Şimali Qafqazdan kənarda")
        self.assertEqual(o(""), "yer adı tanınmadı")

    def test_azerbaijan_polygon(self):
        self.assertEqual(om.az_km(40.68, 46.36), 0.0)    # Gəncə
        self.assertEqual(om.az_km(39.35, 45.45), 0.0)    # Naxçıvan
        self.assertTrue(0 < om.az_km(41.95, 46.25) < 100)   # Laqodexi tərəfi, Gürcüstan
        self.assertTrue(0 < om.az_km(38.3, 48.3) < 100)     # Ərdəbil
        self.assertTrue(om.az_km(37.39, 35.54) > 100)       # İmamoğlu
        self.assertTrue(om.az_km(35.7, 51.4) > 100)         # Tehran


class UsgsAfadParseTest(unittest.TestCase):
    def test_real_month(self):
        doc = om.parse_usgs(fx("usgs-2026-10-10_11-11-m4.json"))
        self.assertEqual(len(doc["quakes"]), 67)
        q = doc["quakes"][0]
        self.assertEqual((q["id"], q["mag"], q["place"], q["status"]), ("us7000tx3n", 4.7, "17 km NW of İmamoğlu, Turkey", "reviewed"))
        self.assertEqual(q["utc"].replace(microsecond=0), utc(2026, 11, 9, 12, 28, 18))
        self.assertEqual(doc["generated"], utc(2026, 11, 10, 9, 39, 9))

    def test_garbage(self):
        for raw in (b"", b"<html>503</html>", b"\xff\xfe\x00", b"[]", b'{"features": 5}'):
            with self.assertRaises(ValueError):
                om.parse_usgs(raw)
        bad = [{"id": "x"}, {"id": "us0000zz", "properties": {"mag": "?", "time": 1}, "geometry": {"coordinates": [1, 2]}},
               {"id": "bad id!", "properties": {"mag": 5, "time": 1794227298182}, "geometry": {"coordinates": [35, 37, 1]}},
               None, feat("us0000ok", utc(2026, 11, 9, 11), 5.0, *TURKEY)]
        self.assertEqual([q["id"] for q in om.parse_usgs(usgs(bad))["quakes"]], ["us0000ok"])

    def test_afad_rows_and_match(self):
        rows = om.parse_afad(fx(AFAD))
        self.assertEqual(len(rows), 5)
        self.assertEqual((rows[0]["province"], rows[0]["district"], rows[0]["neighborhood"], rows[0]["mag"]), ("Adana", "Kozan", "Akdam", 4.6))
        self.assertEqual(rows[0]["utc"], utc(2026, 11, 9, 12, 28, 19))
        self.assertEqual([om._afad_place(r) for r in rows], [True, False, True, True, False])   # dənizdəki iki təkan: yox
        q = quakes(*REAL)[0]
        self.assertEqual(om.afad_match(q, rows)["id"], "598668")
        self.assertIsNone(om.afad_match(dict(q, utc=q["utc"] + 3 * MIN), rows))
        self.assertIsNone(om.afad_match(dict(q, lat=q["lat"] + 1.0), rows))
        with self.assertRaises(ValueError):
            om.parse_afad(b'{"error": "x"}')
        self.assertEqual(om.parse_afad(b'[{"date": "?"}, {"eventID": "1"}]'), [])


class QuakePlanTest(unittest.TestCase):
    def test_real_quake_with_afad(self):
        rows = om.parse_afad(fx(AFAD))
        plan = om.quake_plan(quakes(*REAL), NOW, set(), afad=lambda q: om.afad_match(q, rows))
        self.assertEqual(len(plan), 1)
        it = plan[0]
        self.assertTrue(NEED <= set(it))
        self.assertEqual((it["key"], it["worth"], it["topic"], it["slot"]), ("zelzele-region-us7000tx3n", True, "təbiət", "17:50"))
        self.assertEqual(it["title"], "Türkiyənin Adana ilində 4,6 maqnitudalı zəlzələ olub")
        self.assertEqual(it["lead"], "Türkiyənin Fəlakət və Fövqəladə Hallar İdarəsinin (AFAD) məlumatına görə, 9 noyabrda Bakı vaxtı "
                         "ilə saat 16:28-də Adana ilinin Kozan rayonunda (Akdam məhəlləsi) 4,6 maqnitudalı zəlzələ baş verib. "
                         "Zəlzələnin ocağı 15,35 km dərinlikdə olub.")
        self.assertEqual(it["body"], ["ABŞ Geoloji Xidməti (USGS) zəlzələnin maqnitudasını 4,7 kimi qiymətləndirib.",
                                      "Episentr Bakıdan 1 270 km aralıdadır."])
        self.assertEqual((it["credit"], it["link"]), (om.AFAD_CREDIT, "https://deprem.afad.gov.tr/event-detail/598668"))

    def test_real_quake_usgs_text(self):
        it = om.quake_plan(quakes(*REAL), NOW)[0]
        self.assertEqual(it["title"], "Türkiyədə 4,7 maqnitudalı zəlzələ olub")
        self.assertEqual(it["lead"], "ABŞ Geoloji Xidmətinin (USGS) məlumatına görə, 9 noyabrda Bakı vaxtı ilə saat 16:28-də Türkiyədə, "
                         "İmamoğlunun 17 km şimal-qərbində 4,7 maqnitudalı zəlzələ baş verib. Zəlzələnin ocağı 10 km dərinlikdə olub.")
        self.assertEqual(it["body"], ["Episentr Bakıdan 1 280 km aralıdadır."])
        self.assertEqual((it["credit"], it["link"]), (om.USGS_CREDIT, "https://earthquake.usgs.gov/earthquakes/eventpage/us7000tx3n"))
        self.assertLessEqual(len(it["title"]), 110)

    def test_afad_down_or_sea_falls_back_to_usgs(self):
        def boom(q):
            raise urllib.error.URLError("x")
        it = om.quake_plan(quakes(*REAL), NOW, afad=boom)[0]
        self.assertTrue(it["worth"])
        self.assertEqual(it["title"], "Türkiyədə 4,7 maqnitudalı zəlzələ olub")
        self.assertIn("AFAD alınmadı", it["note"])
        sea = om.parse_afad(fx(AFAD))[4]
        it = om.quake_plan(quakes(*REAL), NOW, afad=lambda q: sea)[0]
        self.assertEqual(it["credit"], om.USGS_CREDIT)

    def test_title_verb_by_second(self):
        it = om.quake_plan(quakes(feat("us0000q1", utc(2026, 11, 9, 11, 0, 1), 5.6, *IRAN)), NOW)[0]
        self.assertEqual(it["title"], "İranda 5,6 maqnitudalı zəlzələ qeydə alınıb")
        self.assertIn("İranda, Şirazın 30 km cənubunda 5,6 maqnitudalı zəlzələ baş verib.", it["lead"])

    def test_threshold_type_region_azerbaijan(self):
        t = utc(2026, 11, 9, 11)
        self.assertEqual(om.quake_plan(quakes(feat("us0000a1", t, 4.4, *TURKEY)), NOW), [])
        self.assertEqual(len(worth(om.quake_plan(quakes(feat("us0000a2", t, 4.5, *TURKEY)), NOW))), 1)
        for f in (feat("us0000b1", t, 5.5, *TURKEY, typ="explosion"),
                  feat("us0000b2", t, 5.5, "101 km SSE of Palekastro, Greece", 34.3, 26.5),
                  feat("us0000b3", t, 5.5, "41 km S of Farkhār, Afghanistan", 36.2, 69.9),
                  feat("us0000b4", t, 5.5, "5 km S of Ganja, Azerbaijan", 40.63, 46.36),
                  feat("us0000b5", t, 5.5, "10 km N of Parsabad, Iran", 40.68, 46.36),      # nöqtə Azərbaycanın içindədir
                  feat("us0000b6", t, 5.5, "40 km E of Aktash, Russia", 49.5, 87.0),
                  feat("us0000b7", t, 5.5, "naməlum yer", 38.0, 44.0)):
            self.assertEqual(om.quake_plan(quakes(f), NOW), [], f["id"])
        it = om.quake_plan(quakes(feat("us0000b8", t, 5.5, "12 km S of Makhachkala, Russia", 42.87, 47.5)), NOW)[0]
        self.assertIn("Rusiyada, Mahaçqalanın 12 km cənubunda", it["lead"])
        self.assertEqual(it["body"], ["Episentr Bakıdan 340 km aralıdadır."])

    def test_only_today_fresh_and_reviewed(self):
        yesterday = feat("us0000c1", utc(2026, 11, 8, 19, 30), 5.5, *TURKEY)       # 8 noyabr 23:30 Bakı
        future = feat("us0000c2", utc(2026, 11, 9, 15), 5.5, *IRAN)
        self.assertEqual(om.quake_plan(quakes(yesterday, future), NOW), [])
        old = om.quake_plan(quakes(feat("us0000c3", utc(2026, 11, 9, 6), 5.5, *TURKEY)), NOW)[0]    # 7 saat 50 dəqiqə əvvəl
        self.assertEqual((old["key"], old["worth"], old["pending"]), ("zelzele-yox-us0000c3", False, False))
        self.assertTrue(old["why"].startswith("gecikmiş xəbər"))
        auto = om.quake_plan(quakes(feat("us0000c4", utc(2026, 11, 9, 13), 5.5, *TURKEY, status="automatic")), NOW)[0]
        self.assertEqual((auto["key"], auto["worth"], auto["pending"]), ("zelzele-yox-us0000c4", False, True))
        self.assertIn("yoxlamayıb", auto["why"])

    def three(self):
        return quakes(feat("us0000q1", utc(2026, 11, 9, 11, 0), 5.6, *IRAN), feat("us0000q2", utc(2026, 11, 9, 11, 20), 5.0, *TURKEY),
                      feat("us0000q3", utc(2026, 11, 9, 11, 40), 4.8, *TAJIK))

    def test_cap_two_a_day_strongest_first_rest_in_one_line(self):
        plan = om.quake_plan(self.three(), NOW)
        self.assertEqual([(i["key"], i["worth"]) for i in plan],
                         [("zelzele-region-us0000q1", True), ("zelzele-region-us0000q2", True), ("zelzele-yox-us0000q3", False)])
        self.assertEqual(plan[0]["body"][-1], "Bu gün regionda 4,5 və daha güclü daha 1 zəlzələ qeydə alınıb: "
                         "Tacikistanda 4,8 maqnitudalı (saat 15:40-da).")
        self.assertEqual(len(plan[1]["body"]), 1)
        self.assertEqual((plan[2]["why"], plan[2]["pending"]), ("gündə 2 zəlzələ xəbəri həddi", False))

    def test_cap_counts_only_published_keys_in_done(self):
        one = om.quake_plan(self.three(), NOW, {"zelzele-region-us0000zz"})
        self.assertEqual([i["key"] for i in worth(one)], ["zelzele-region-us0000q1"])
        none = om.quake_plan(self.three(), NOW, {"zelzele-region-us0000zz", "zelzele-region-us0000yy"})
        self.assertEqual(worth(none), [])
        noise = {"zelzele-yox-us0000zz", "zelzele-yox-us0000yy", "zelzele-sorgu-2026-11-09T16", "asteroid-gun-2026-11-09"}
        self.assertEqual(len(worth(om.quake_plan(self.three(), NOW, noise))), 2)

    def test_done_dedupe_by_any_id(self):
        self.assertEqual(om.quake_plan(quakes(*REAL), NOW, {"zelzele-region-us7000tx3n"}), [])
        self.assertEqual(om.quake_plan(quakes(*REAL), NOW, {"zelzele-yox-us7000tx3n"}), [])
        moved = feat("tr000123", utc(2026, 11, 9, 12, 28, 18), 4.7, *TURKEY, ids=",us7000tx3n,tr000123,")
        self.assertEqual(om.quake_plan(quakes(moved), NOW, {"zelzele-region-us7000tx3n"}), [])
        self.assertEqual(len(worth(om.quake_plan(quakes(moved), NOW, {"zelzele-region-us7000abcd"}))), 1)

    def test_aftershock_is_one_event(self):
        main = feat("us0000m1", utc(2026, 11, 9, 10, 0), 5.2, "91 km ESE of Kyzyl-Eshme, Kyrgyzstan", 39.3619, 73.3023)
        after = feat("us0000m2", utc(2026, 11, 9, 11, 16), 4.5, "99 km ESE of Kyzyl-Eshme, Kyrgyzstan", 39.294, 73.3725)
        plan = om.quake_plan(quakes(after, main), NOW)
        self.assertEqual([(i["key"], i["worth"]) for i in plan], [("zelzele-region-us0000m1", True), ("zelzele-yox-us0000m2", False)])
        self.assertEqual(plan[0]["body"][0], "Episentr Bakıdan 2 000 km aralıdadır.")
        self.assertIn("daha 1 zəlzələ qeydə alınıb: Qırğızıstanda 4,5 maqnitudalı (saat 15:16-da).", plan[0]["body"][1])
        self.assertIn("ardınca gəlib", plan[1]["why"])
        self.assertFalse(plan[1]["pending"])
        # əsas zəlzələ artıq dərc olunub: təkan nə xəbərdir, nə də başqa xəbərin sətri
        later = om.quake_plan(quakes(after, main), NOW, {"zelzele-region-us0000m1"})
        self.assertEqual([(i["key"], i["worth"]) for i in later], [("zelzele-yox-us0000m2", False)])

    def test_seismology_az_check_near_the_border(self):
        seen = []

        def hit(q):
            seen.append(q["id"])
            return {"area": "Lerik", "ml": 4.6}
        near = feat("us0000s1", utc(2026, 11, 9, 11), 4.9, "5 km N of Ardabil, Iran", 38.3, 48.3)
        plan = om.quake_plan(quakes(near, *REAL), NOW, seys=hit)
        self.assertEqual(seen, ["us0000s1"])      # İmamoğlu sərhəddən uzaqdır: seismology.az yoxlanmır
        skip = by_key(plan, "zelzele-yox-us0000s1")
        self.assertEqual(skip["why"], "seismology.az siyahısında var (Lerik, ML 4,6): onun xəbəri dərc olunur")
        self.assertEqual([i["key"] for i in worth(plan)], ["zelzele-region-us7000tx3n"])
        self.assertEqual(len(by_key(plan, "zelzele-region-us7000tx3n")["body"]), 1)   # seismology.az-dakı zəlzələ sadalanmır
        it = om.quake_plan(quakes(near), NOW, seys=lambda q: None)[0]
        self.assertTrue(it["worth"])
        self.assertIn("İranda, Ərdəbilin 5 km şimalında", it["lead"])

        def boom(q):
            raise urllib.error.URLError("x")
        it = om.quake_plan(quakes(near), NOW, seys=boom)[0]
        self.assertTrue(it["worth"])
        self.assertIn("seismology.az yoxlanmadı", it["note"])

    def test_seismology_az_real_list(self):
        net = Net([("seismology.az", fx("seys-2026-11-10.html"))])
        q = feat("us0000s2", utc(2026, 10, 1, 10, 51, 50), 4.6, "8 km N of Lagodekhi, Georgia", 41.95, 46.25)
        plan = om.quake_plan(quakes(q), at(2026, 10, 1, 15, 30), seys=om._seys_lookup(om._Get(net)))
        self.assertEqual(plan[0]["why"], "seismology.az siyahısında var (Zaqatala, ML 4,1): onun xəbəri dərc olunur")
        self.assertEqual(net.n("seismology.az"), 1)


class ItemsQuakeTest(unittest.TestCase):
    def routes(self, feats=REAL, gen=None):
        return [("earthquake.usgs.gov", usgs(feats, gen)), ("servisnet.afad.gov.tr", fx(AFAD))]

    def test_no_request_off_tick(self):
        net = Net(self.routes())
        self.assertEqual(om.items(ROOT, at(2026, 11, 9, 17, 25), fetch=net), [])
        self.assertEqual(net.calls, [])

    def test_tick_publishes_marks_the_hour_and_stops(self):
        net = Net(self.routes())
        out = om.items(ROOT, NOW, fetch=net)
        self.assertEqual([(i["key"], i["worth"]) for i in out], [("zelzele-region-us7000tx3n", True), ("zelzele-sorgu-2026-11-09T17", False)])
        for i in out:
            self.assertTrue(NEED <= set(i), i["key"])
            self.assertTrue(i["worth"] or i["why"], i["key"])
        self.assertEqual(out[0]["title"], "Türkiyənin Adana ilində 4,6 maqnitudalı zəlzələ olub")
        self.assertEqual((net.n("earthquake.usgs.gov"), net.n("afad.gov.tr"), net.n("seismology.az"), len(net.calls)), (1, 1, 0, 2))
        url = net.calls[0]
        for part in ("fdsnws/event/1/query?format=geojson", "starttime=2026-11-08T13:50:00", "endtime=2026-11-09T13:50:00",
                     "minmagnitude=4.5", "minlatitude=24", "maxlatitude=50", "minlongitude=25", "maxlongitude=88"):
            self.assertIn(part, url)
        self.assertIn("minmag=4", net.calls[1])
        self.assertEqual(out, om.items(ROOT, NOW, fetch=Net(self.routes())))       # eyni məlumat, eyni an: eyni nəticə
        done = {i["key"] for i in out}
        again = Net(self.routes())
        self.assertEqual(om.items(ROOT, NOW + 5 * MIN, fetch=again, done=done), [])   # həmin saat: sorğu getmir
        self.assertEqual(again.calls, [])
        nxt = Net(self.routes())
        out = om.items(ROOT, at(2026, 11, 9, 18, 0), fetch=nxt, done=done)             # növbəti saat: USGS bir dəfə, AFAD yox
        self.assertEqual([(i["key"], i["worth"]) for i in out], [("zelzele-sorgu-2026-11-09T18", False)])
        self.assertEqual((nxt.n("earthquake.usgs.gov"), len(nxt.calls)), (1, 1))

    def test_unreviewed_waits_for_the_next_tick(self):
        t = utc(2026, 11, 9, 13, 20)
        net = Net(self.routes([feat("us0000p1", t, 5.1, *IRAN, status="automatic")]))
        out = om.items(ROOT, NOW, fetch=net)
        self.assertEqual([i["key"] for i in out], ["zelzele-sorgu-2026-11-09T17"])
        done = {i["key"] for i in out}
        net = Net(self.routes([feat("us0000p1", t, 5.1, *IRAN)]))
        out = om.items(ROOT, at(2026, 11, 9, 18, 5), fetch=net, done=done)
        self.assertEqual([(i["key"], i["worth"]) for i in out], [("zelzele-region-us0000p1", True), ("zelzele-sorgu-2026-11-09T18", False)])
        self.assertEqual(net.n("afad.gov.tr"), 0)      # İran: AFAD-a sorğu getmir

    def test_usgs_down_garbage_stale(self):
        for reply, text in ((urllib.error.URLError("x"), "USGS alınmadı: URLError"), (http(503), "USGS alınmadı: HTTPError 503"),
                            (b"<html>", "USGS cavabı JSON deyil"), (b'{"x": 1}', "USGS cavabında zəlzələ siyahısı yoxdur"),
                            (usgs(REAL, NOW - 3 * 60 * MIN), "USGS cavabı köhnədir: 9 noyabr 14:50 tarixlidir"),
                            (RuntimeError("x"), "USGS alınmadı: RuntimeError")):
            net = Net([("earthquake.usgs.gov", reply)])
            out = om.items(ROOT, NOW, fetch=net)
            self.assertEqual([(i["key"], i["worth"], i["why"]) for i in out], [("zelzele-sorgu-2026-11-09T17", False, text)])
            self.assertEqual(len(net.calls), 1)

    def test_fresh_generated_stamp_is_fine_and_naive_now_is_baku(self):
        net = Net(self.routes(REAL, NOW - 5 * MIN))
        out = om.items(ROOT, NOW.replace(tzinfo=None), fetch=net)
        self.assertEqual([i["key"] for i in worth(out)], ["zelzele-region-us7000tx3n"])

    def test_leadership_guard(self):
        with patch.object(ox, "needs_owner", return_value=True):
            out = om.items(ROOT, NOW, fetch=Net(self.routes()))
        q = by_key(out, "zelzele-region-us7000tx3n")
        self.assertEqual((q["worth"], q["why"]), (False, "rəhbərliyin adı keçir: dərc olunmur"))
        clean = om.quake_plan(quakes(*REAL), NOW)[0]
        self.assertTrue(om._guard(clean)["worth"])
        named = dict(clean, body=clean["body"] + ["Prezident İlham Əliyev məhəlləsi"])
        self.assertFalse(om._guard(named)["worth"])


class AsteroidTest(unittest.TestCase):
    def test_parse(self):
        rows = om.parse_cad(fx("cad-1ld-2026-11-01_11-12.json"))
        self.assertEqual(len(rows), 9)
        self.assertEqual((rows[0]["des"], rows[0]["name"], rows[0]["h"], rows[0]["diam"]), ("2026 VE3", "2026 VE3", 28.473, None))
        self.assertTrue(all(r["ld"] < 1 for r in rows))
        big = om.parse_cad(fx("cad-2026-11-02_11-23.json"))
        self.assertEqual(len(big), 72)
        self.assertEqual(big[2]["name"], "524522 Zoozve (2002 VE68)")
        self.assertEqual(om.parse_cad(b'{"signature": {"version": "1.5"}, "count": 0}'), [])
        for raw in (b"", b"<html>", b"[]", b'{"count": 1}', b'{"signature": {}, "count": 2, "fields": ["des"], "data": [["x"]]}',
                    b'{"signature": {}, "count": "x"}'):
            with self.assertRaises(ValueError):
                om.parse_cad(raw)
        short = b'{"signature": {}, "count": 2, "fields": ["des", "jd", "dist", "v_rel"], "data": [["A"], ["B", "x", "0.01", "5"]]}'
        self.assertEqual(om.parse_cad(short), [])

    def test_small_helpers(self):
        td = datetime.timedelta
        self.assertEqual([om._tsig(x) for x in ("< 00:01", "01:40", "2_00:46", "x", None)],
                         [td(0), td(hours=1, minutes=40), td(days=2, minutes=46), None, None])
        self.assertEqual(om.size_text({"diam": 0.5, "h": 20.0}), "diametri 500 metr")
        self.assertEqual(om.size_text({"diam": 1.2, "h": 17.0}), "diametri 1,2 km")
        self.assertEqual(om.size_text({"diam": None, "h": 25.847}), "diametri təxminən 18–40 metr")
        self.assertEqual(om.size_text({"diam": None, "h": 17.0}), "diametri təxminən 1,1–2,4 km")
        self.assertEqual(om.size_text({"diam": None, "h": None}), "")
        self.assertEqual([om.km_text(40842.3), om.km_text(6018000.0)], ["40 842 km", "6,02 milyon km"])

    def test_event_item_real_4_november(self):
        rows = om.parse_cad(fx("cad-1ld-2026-11-01_11-12.json"))
        it, why = om.asteroid_event_item(rows, D(2026, 11, 4), at(2026, 11, 4, 13, 10))
        self.assertEqual(why, "")
        self.assertTrue(NEED <= set(it))
        self.assertEqual((it["key"], it["worth"], it["topic"], it["credit"]), ("asteroid-gun-2026-11-04", True, "kosmos", om.JPL_CREDIT))
        self.assertEqual(it["title"], "2026 VO5 asteroidi bu gün Yerin yanından Aydan 2 dəfə yaxın məsafədən keçəcək")
        self.assertEqual(it["lead"], "NASA-nın Reaktiv Hərəkət Laboratoriyasının (JPL) məlumatına görə, 2026 VO5 asteroidi 4 noyabrda "
                         "Bakı vaxtı ilə saat 21:10-da Yerdən 186 373 km, yəni Yer–Ay məsafəsinin 0,48-i qədər məsafədən saniyədə "
                         "8,8 km sürətlə keçəcək.")
        self.assertEqual(it["body"][0], "Parlaqlığına görə asteroidin diametri təxminən 18–40 metr qiymətləndirilir.")
        self.assertEqual(it["body"][1], "Bu gün Yerin yanından Aydan yaxın məsafədən daha 2 asteroid keçir: 2026 VW7 (40 842 km), "
                         "2026 VO4 (189 578 km).")
        self.assertIn("sstr=2026%20VO5", it["link"])
        self.assertLessEqual(len(it["title"]), 110)

    def test_event_item_none_and_past(self):
        rows = om.parse_cad(fx("cad-1ld-2026-11-01_11-12.json"))
        it, why = om.asteroid_event_item(rows, D(2026, 11, 3), at(2026, 11, 3, 13, 10))
        self.assertEqual((it, why), (None, "bu gün Aydan yaxın keçən asteroid yoxdur"))
        it, _ = om.asteroid_event_item(rows, D(2026, 11, 2), at(2026, 11, 2, 13, 10))
        self.assertEqual(it["title"], "2026 VU asteroidi bu gün Yerin yanından Aydan yaxın məsafədən keçib")
        self.assertIn("2 noyabrda Bakı vaxtı ilə saat 08:09-da Yerdən 372 331 km, yəni Yer–Ay məsafəsinin 0,97-si qədər məsafədən "
                      "saniyədə 12,6 km sürətlə keçib.", it["lead"])

    def test_digest_real_9_november(self):
        rows = om.parse_cad(fx("cad-2026-11-02_11-23.json"))
        it, why = om.asteroid_digest_item(rows, at(2026, 11, 9, 13, 10))
        self.assertEqual((it["key"], it["worth"], it["list"]), ("asteroid-hefte-2026-11-09", True, True))
        self.assertEqual(it["title"], "Növbəti 7 gündə 17 asteroid Yerə 7,5 milyon km-dən yaxın məsafədən keçəcək")
        self.assertTrue(it["lead"].startswith(
            "NASA-nın Reaktiv Hərəkət Laboratoriyasının (JPL) məlumatına görə, 10–14 noyabrda 17 asteroid Yerə "
            "0,05 astronomik vahiddən (7,5 milyon km) yaxın məsafədən keçəcək. Ən yaxını 2026 VT3 asteroididir: o, "
            "10 noyabrda Yerdən 1,66 milyon km (4,32 Ay məsafəsi) uzaqlıqdan keçəcək. Ən böyüyü 2026 VV5 asteroididir: "
            "diametri təxminən 39–8"), it["lead"])
        self.assertRegex(it["lead"], r"diametri təxminən 39–8[78] metr\.$")
        self.assertEqual(len(it["body"]), 14)      # ən yaxın 12 keçid, qalanların sayı, izah
        self.assertEqual(it["body"][0], "10 noyabr, 01:12 — 2026 VQ4: 3,82 milyon km (9,93 Ay məsafəsi), diametri təxminən 10–23 metr")
        self.assertEqual(it["body"][1], "təxminən 10 noyabr — 2015 VH65: 3,73 milyon km (9,69 Ay məsafəsi), diametri təxminən 8–17 metr")
        self.assertEqual(it["body"][12], "Daha 5 asteroid bundan uzaq məsafədən keçəcək.")
        none, why = om.asteroid_digest_item(rows, at(2026, 12, 7, 13, 10))
        self.assertEqual((none, why), (None, "növbəti 7 gündə Yerə 0,05 AB-dən yaxın keçən asteroid yoxdur"))

    def run_at(self, now, fixture, done=None):
        net = Net([EMPTY, ("ssd-api.jpl.nasa.gov", fixture)])
        out = om.items(ROOT, now, fetch=net, done=done)
        return net, [i for i in out if i["kind"].startswith("asteroid")]

    def test_window_tick_done_and_one_request(self):
        small = fx("cad-1ld-2026-11-01_11-12.json")
        net, out = self.run_at(at(2026, 11, 10, 13, 10), small)        # çərşənbə axşamı, Aydan yaxın keçid yoxdur
        self.assertEqual([(i["key"], i["worth"], i["why"]) for i in out],
                         [("asteroid-gun-2026-11-10", False, "bu gün Aydan yaxın keçən asteroid yoxdur")])
        self.assertEqual(net.n("ssd-api.jpl.nasa.gov"), 1)
        url = next(u for u in net.calls if "jpl" in u)
        self.assertIn("cad.api?date-min=2026-11-09&date-max=2026-11-11&dist-max=1LD", url)
        net, out = self.run_at(at(2026, 11, 10, 14, 20), small, {"asteroid-gun-2026-11-10"})
        self.assertEqual((net.n("jpl"), out), (0, []))
        for hh, mm in ((12, 0), (16, 40), (13, 30)):      # pəncərədən əvvəl, sonra, tik deyil
            net, out = self.run_at(at(2026, 11, 10, hh, mm), small)
            self.assertEqual((net.n("jpl"), out), (0, []), (hh, mm))
        net, out = self.run_at(at(2026, 11, 4, 13, 10), small)
        self.assertEqual([(i["key"], i["worth"]) for i in out], [("asteroid-gun-2026-11-04", True)])

    def test_monday_digest_and_event_from_one_request(self):
        big = fx("cad-2026-11-02_11-23.json")
        net, out = self.run_at(at(2026, 11, 9, 13, 10), big)
        self.assertEqual([(i["key"], i["worth"]) for i in out], [("asteroid-hefte-2026-11-09", True)])
        self.assertEqual(net.n("jpl"), 1)
        self.assertIn("cad.api?date-min=2026-11-08&date-max=2026-11-17&dist-max=0.05", next(u for u in net.calls if "jpl" in u))
        net, out = self.run_at(at(2026, 11, 2, 13, 10), big)             # 2 noyabr: 2026 VU Aydan yaxın keçib
        self.assertEqual([(i["key"], i["worth"]) for i in out], [("asteroid-hefte-2026-11-02", True), ("asteroid-gun-2026-11-02", True)])
        self.assertEqual(net.n("jpl"), 1)
        net, out = self.run_at(at(2026, 11, 9, 14, 20), big, {"asteroid-hefte-2026-11-09"})
        self.assertEqual((net.n("jpl"), out), (0, []))
        net, out = self.run_at(at(2026, 11, 9, 13, 10), b'{"signature": {"version": "1.5"}, "count": 0}')
        self.assertEqual([(i["key"], i["worth"]) for i in out], [("asteroid-hefte-2026-11-09", False)])

    def test_jpl_down_or_garbage_returns_the_key(self):
        for reply, text in ((http(503), "JPL alınmadı: HTTPError 503"), (b"<html>", "JPL cavabı JSON deyil"),
                            (b'{"message": "x"}', "JPL cavabı tanınmadı")):
            net, out = self.run_at(at(2026, 11, 10, 13, 10), reply)
            self.assertEqual([(i["key"], i["worth"], i["why"]) for i in out], [("asteroid-gun-2026-11-10", False, text)])
            self.assertEqual(net.n("jpl"), 1)


def ll2(rows):
    return json.dumps({"count": len(rows), "results": rows}).encode("utf-8")


UP = "ll2-upcoming-2026-11-10.json"


class LaunchTest(unittest.TestCase):
    def up(self):
        return om.parse_ll2(fx(UP))

    def raw(self, name=UP):
        return json.loads(fx(name).decode("utf-8"))["results"]

    def test_parse(self):
        rows = self.up()
        self.assertEqual(len(rows), 10)
        star = rows[5]
        self.assertEqual((star["rocket"], star["status"], star["prec"], star["cc"], star["site"]),
                         ("Starship", "TBC", "MIN", "USA", "SpaceX Starbase"))
        self.assertEqual(star["net"], utc(2026, 11, 13, 22, 45))
        self.assertTrue(om.starship(star))
        self.assertFalse(om.crewed(star))
        self.assertEqual([om.crewed(x) for x in om.parse_ll2(fx("ll2-previous-crewed-2026-11-10.json"))], [True, True, True])
        for raw in (b"", b"<html>", b"[]", b'{"detail": "Request was throttled."}'):
            with self.assertRaises(ValueError):
                om.parse_ll2(raw)
        self.assertEqual(om.parse_ll2(b'{"results": [5, {"name": "A | B"}, {"name": "", "net": "2026-11-13T22:45:00Z"}]}'), [])
        self.assertEqual([om.mission_text(x) for x in ("Unknown Payload", "SatNet LEO Group TBD?", "Starlink Group 31-2 (Starship Flight 15)")],
                         ["naməlum yük", "SatNet LEO Group", "Starlink Group 31-2 (Starship-in 15-ci uçuşu)"])

    def test_digest_real_week(self):
        it, why = om.launch_digest_item(self.up(), at(2026, 11, 9, 10, 40), at(2026, 11, 16, 0, 0))
        self.assertTrue(NEED <= set(it))
        self.assertEqual((it["key"], it["worth"], it["list"], it["topic"]), ("buraxilis-hefte-2026-11-09", True, True, "kosmos"))
        self.assertEqual(it["title"], "Bu həftə dünyada 8 kosmik buraxılış planlaşdırılır, aralarında Starship var")
        self.assertEqual(it["lead"], "The Space Devs-in Launch Library 2 məlumatına görə, 11–15 noyabrda dünyada 8 raket buraxılışı "
                         "planlaşdırılır. Onların arasında 14 noyabrda Bakı vaxtı ilə saat 02:45-də Starship-in 15-ci uçuşu var "
                         "(tarix dəqiqləşdirilir).")
        self.assertEqual(len(it["body"]), 8)
        self.assertEqual(it["body"][0], "11 noyabr, 06:49 — ABŞ: Falcon 9 Block 5, USSF-627")
        self.assertEqual(it["body"][2], "11 noyabr, təxminən 15:40 — Çin: Long March 2D, naməlum yük")
        self.assertEqual(it["body"][5], "14 noyabr, 02:45 — ABŞ: Starship, Starlink Group 31-2 (Starship-in 15-ci uçuşu) (tarix dəqiqləşdirilir)")
        nxt, _ = om.launch_digest_item(self.up(), at(2026, 11, 16, 10, 40), at(2026, 11, 23, 0, 0))
        self.assertEqual(nxt["title"], "Bu həftə dünyada 2 kosmik buraxılış planlaşdırılır")
        self.assertEqual(nxt["body"][1], "20 noyabr, təxminən 15:00 — Çin: Long March 8A, SatNet LEO Group (tarix dəqiqləşdirilir)")
        none, why = om.launch_digest_item(self.up(), at(2026, 11, 23, 10, 40), at(2026, 11, 30, 0, 0))
        self.assertEqual((none, why), (None, "bu həftə planlaşdırılan kosmik buraxılış yoxdur"))

    def test_starship_day_item_needs_go(self):
        day, now = D(2026, 11, 13), at(2026, 11, 13, 10, 40)
        out = om.launch_day_items(self.up(), day, now)
        self.assertEqual(len(out), 1)
        self.assertEqual((out[0]["worth"], out[0]["why"]), (False, "buraxılış təsdiqlənməyib (LL2 statusu TBC)"))
        self.assertTrue(out[0]["key"].startswith("buraxilis-gun-2026-11-13-starship-starlink-group-31-2"))
        go = [dict(x, status="Go") if om.starship(x) else x for x in self.up()]
        it = om.launch_day_items(go, day, now)[0]
        self.assertEqual((it["key"], it["worth"]), ("buraxilis-gun-2026-11-13", True))
        self.assertEqual(it["title"], "Starship-in 15-ci uçuşu bu gecə saat 02:45-də planlaşdırılır")
        self.assertEqual(it["lead"], "The Space Devs-in Launch Library 2 məlumatına görə, Starship raketinin 15-ci uçuşu 14 noyabrda Bakı "
                         "vaxtı ilə saat 02:45-də SpaceX Starbase (ABŞ) buraxılış meydançasından planlaşdırılır.")
        self.assertEqual(it["body"], ["Raket: Starship V3", "Missiya: Starlink Group 31-2 (Starship-in 15-ci uçuşu)",
                                      "Buraxılış pəncərəsi Bakı vaxtı ilə 02:45–04:00 arasıdır"])
        self.assertEqual(it["link"], "https://spacelaunchnow.app/launch/starship-starlink-group-31-2-starship-flight-15/")
        self.assertEqual(om.launch_day_items(go, D(2026, 11, 12), at(2026, 11, 12, 10, 40)), [])     # 12 noyabr 13:00 – 13 noyabr 13:00
        self.assertEqual(om.launch_day_items(go, D(2026, 11, 14), at(2026, 11, 14, 10, 40)), [])

    def test_crewed_day_item_real_crew_13(self):
        crew = om.parse_ll2(fx("ll2-previous-crewed-2026-11-10.json"))[0]
        day, now = D(2026, 10, 1), at(2026, 10, 1, 10, 40)
        it = om.launch_day_items([dict(crew, status="Go")], day, now)[0]
        self.assertTrue(it["worth"])
        self.assertEqual(it["title"], "Pilotlu Crew-13 missiyasının buraxılışı bu gün saat 19:10-da planlaşdırılır")
        self.assertEqual(it["lead"], "The Space Devs-in Launch Library 2 məlumatına görə, pilotlu Crew-13 missiyası 1 oktyabrda Bakı "
                         "vaxtı ilə saat 19:10-da Falcon 9 Block 5 raketi ilə Cape Canaveral SFS (ABŞ) buraxılış meydançasından buraxılacaq.")
        self.assertEqual(it["body"], ["Raket: Falcon 9 Block 5", "Missiya: Crew-13"])
        for change, text in (({"status": "Success"}, "buraxılış təsdiqlənməyib (LL2 statusu Success)"),
                             ({"status": "Go", "prec": "HR"}, "buraxılış vaxtı dəqiqəyədək məlum deyil"),
                             ({"status": "Go", "net": utc(2026, 10, 1, 9, 30)}, "buraxılış vaxtı keçib")):
            bad = om.launch_day_items([dict(crew, **change)], day, at(2026, 10, 1, 14, 0))[0]
            self.assertEqual((bad["worth"], bad["why"]), (False, text))

    def run_at(self, now, reply, done=None):
        net = Net([EMPTY, ("ll.thespacedevs.com", reply)])
        out = om.items(ROOT, now, fetch=net, done=done)
        return net, [i for i in out if i["kind"].startswith("buraxilis")]

    def test_window_tick_done_and_one_request(self):
        net, out = self.run_at(at(2026, 11, 10, 10, 40), fx(UP))      # çərşənbə axşamı: pilotlu buraxılış və Starship yoxdur
        self.assertEqual([(i["key"], i["worth"]) for i in out], [("buraxilis-gun-2026-11-10", False)])
        self.assertTrue(out[0]["why"])
        self.assertEqual(net.n("thespacedevs"), 1)
        url = next(u for u in net.calls if "thespacedevs" in u)
        for part in ("/2.3.0/launches/upcoming/?mode=normal", "net__gte=2026-11-10T09:00:00Z", "net__lte=2026-11-11T09:00:00Z"):
            self.assertIn(part, url)
        net, out = self.run_at(at(2026, 11, 10, 11, 50), fx(UP), {"buraxilis-gun-2026-11-10"})
        self.assertEqual((net.n("thespacedevs"), out), (0, []))
        for hh, mm in ((9, 30), (13, 10), (10, 20)):       # pəncərədən əvvəl, sonra, tik deyil
            net, out = self.run_at(at(2026, 11, 10, hh, mm), fx(UP))
            self.assertEqual((net.n("thespacedevs"), out), (0, []), (hh, mm))

    def test_friday_starship_not_confirmed_is_final_for_the_day(self):
        net, out = self.run_at(at(2026, 11, 13, 10, 40), fx(UP))
        self.assertEqual([i["worth"] for i in out], [False, False])
        self.assertEqual(out[1]["key"], "buraxilis-gun-2026-11-13")
        rows = self.raw()
        rows[5]["status"] = {"id": 1, "name": "Go for Launch", "abbrev": "Go"}
        net, out = self.run_at(at(2026, 11, 13, 10, 40), ll2(rows))
        self.assertEqual([(i["key"], i["worth"]) for i in out], [("buraxilis-gun-2026-11-13", True)])

    def test_monday_digest_one_request(self):
        net, out = self.run_at(at(2026, 11, 9, 10, 40), fx(UP))
        self.assertEqual([(i["key"], i["worth"]) for i in out], [("buraxilis-hefte-2026-11-09", True)])
        self.assertEqual(net.n("thespacedevs"), 1)
        url = next(u for u in net.calls if "thespacedevs" in u)
        for part in ("net__gte=2026-11-09T06:40:00Z", "net__lte=2026-11-15T20:00:00Z"):
            self.assertIn(part, url)
        net, out = self.run_at(at(2026, 11, 9, 11, 50), fx(UP), {"buraxilis-hefte-2026-11-09"})
        self.assertEqual((net.n("thespacedevs"), out), (0, []))
        net, out = self.run_at(at(2026, 11, 9, 10, 40), ll2([]))
        self.assertEqual([(i["key"], i["worth"]) for i in out], [("buraxilis-hefte-2026-11-09", False)])

    def test_ll2_down_or_throttled_returns_the_key(self):
        for reply, text in ((http(429), "LL2 alınmadı: HTTPError 429"), (b'{"detail": "Request was throttled."}', "LL2 cavabında buraxılış siyahısı yoxdur"),
                            (b"<html>", "LL2 cavabı JSON deyil")):
            net, out = self.run_at(at(2026, 11, 10, 10, 40), reply)
            self.assertEqual([(i["key"], i["worth"], i["why"]) for i in out], [("buraxilis-gun-2026-11-10", False, text)])
            self.assertEqual(net.n("thespacedevs"), 1)

    def test_leadership_in_mission_name(self):
        rows = self.raw("ll2-previous-crewed-2026-11-10.json")[:1]
        rows[0].update(net="2026-11-10T15:10:06Z", window_start="2026-11-10T15:10:06Z", window_end="2026-11-10T15:10:06Z",
                       status={"id": 1, "name": "Go for Launch", "abbrev": "Go"})
        net, out = self.run_at(at(2026, 11, 10, 10, 40), ll2(rows))
        self.assertEqual([(i["key"], i["worth"]) for i in out], [("buraxilis-gun-2026-11-10", True)])
        rows[0]["mission"]["name"] = "Prezident İlham Əliyev"
        net, out = self.run_at(at(2026, 11, 10, 10, 40), ll2(rows))
        self.assertEqual([(i["key"], i["worth"], i["why"]) for i in out],
                         [("buraxilis-gun-2026-11-10", False, "rəhbərliyin adı keçir: dərc olunmur")])


class BudgetAndSinaqTest(unittest.TestCase):
    def all_routes(self):
        return [("earthquake.usgs.gov", fx("usgs-2026-10-10_11-11-m4.json")), ("servisnet.afad.gov.tr", fx(AFAD)),
                ("seismology.az", fx("seys-2026-11-10.html")), ("launches/previous/", fx("ll2-previous-crewed-2026-11-10.json")),
                ("ll.thespacedevs.com", fx(UP)), ("ssd-api.jpl.nasa.gov", fx("cad-2026-11-02_11-23.json"))]

    def test_a_day_of_ten_minute_cycles_stays_in_budget(self):
        net, done = Net([EMPTY, ("ll.thespacedevs.com", fx(UP)), ("ssd-api.jpl.nasa.gov", fx("cad-1ld-2026-11-01_11-12.json"))]), set()
        t = at(2026, 11, 10, 0, 3)
        for _ in range(144):
            done |= {i["key"] for i in om.items(ROOT, t, fetch=net, done=done)}
            t += 10 * MIN
        self.assertEqual((net.n("earthquake.usgs.gov"), net.n("thespacedevs"), net.n("jpl")), (24, 1, 1))
        self.assertLessEqual(len(net.calls), 30)

    def test_five_minute_cycles_do_not_double_the_requests(self):
        net, done = Net([EMPTY]), set()
        t = at(2026, 11, 10, 17, 0)
        for _ in range(24):
            done |= {i["key"] for i in om.items(ROOT, t, fetch=net, done=done)}
            t += 5 * MIN
        self.assertEqual(net.n("earthquake.usgs.gov"), 2)       # 17:50 və 18:00 tikləri

    def test_everything_down_never_raises(self):
        for hh, mm in ((10, 40), (13, 10), (17, 50)):
            out = om.items(ROOT, at(2026, 11, 10, hh, mm), fetch=Net([]))
            self.assertTrue(out)
            self.assertTrue(all(not i["worth"] and i["why"] for i in out))
        self.assertEqual(om.items(ROOT, "pozuq vaxt", fetch=Net([])), [])

    def test_sinaq_with_saved_responses(self):
        net = Net(self.all_routes())
        with patch.object(om, "PAUSE", 0.0):
            md = om.sinaq(ROOT, at(2026, 11, 10, 14, 0), fetch=net)
        text = "\n".join(md)
        self.assertLessEqual(len(net.calls), 20)
        for part in ("## 1. Regionda zəlzələ", "### Türkiyənin Adana ilində 4,6 maqnitudalı zəlzələ olub", "✅ Dərc olunardı",
                     "### Qırğızıstanda 5,2 maqnitudalı zəlzələ", "ardınca gəlib: bir hadisə, bir xəbər",
                     "### Bu həftə dünyada 8 kosmik buraxılış planlaşdırılır, aralarında Starship var",
                     "### Pilotlu Crew-13 missiyasının buraxılışı bu gün saat 19:10-da planlaşdırılır",
                     "### Növbəti 7 gündə 17 asteroid Yerə 7,5 milyon km-dən yaxın məsafədən keçəcək",
                     "### 2026 VR5 asteroidi bu gün Yerin yanından Aydan yaxın məsafədən keçəcək", "## Sorğular"):
            self.assertIn(part, text)
        self.assertNotIn("Sınaq xətası", text)

    def test_sinaq_everything_down(self):
        with patch.object(om, "PAUSE", 0.0):
            md = om.sinaq(ROOT, at(2026, 11, 10, 14, 0), fetch=Net([]))
        text = "\n".join(md)
        self.assertIn("alınmadı", text)
        self.assertNotIn("Sınaq xətası", text)


if __name__ == "__main__":
    unittest.main()
