"""Gündəlik həyat xəbərləri (oz_gundelik.py, mərhələ 2): DİM təqvimi, səyyar ASAN, «ASAN müraciət», polisin gündəlik icmalı.
Şəbəkə yoxdur: tests/fixtures/oz_gundelik/ — mənbələrin 2026-11-10 və 2026-11-11 tarixli real cavablarından kəsiklər."""
import contextlib
import datetime
import io
import pathlib
import unittest
import urllib.error
from unittest.mock import patch

import oz_gundelik as g
import oz_xeber as ox

ROOT = pathlib.Path(__file__).resolve().parent.parent
FIX = ROOT / "tests" / "fixtures" / "oz_gundelik"
D = datetime.date
KEYS = {"kind", "key", "title", "lead", "body", "credit", "link", "topic", "slot", "worth"}
LEADER = "Prezident İlham Əliyev"
_PAUSE = g.PAUSE


def setUpModule():
    g.PAUSE = 0  # testdə saytlar arasında gözləmə yoxdur


def tearDownModule():
    g.PAUSE = _PAUSE


def at(y, m, d, hh, mm=0):
    return datetime.datetime(y, m, d, hh, mm, tzinfo=g.BAKU)


def raw(name):
    return (FIX / name).read_bytes()


def text(name):
    return raw(name).decode("utf-8")


def pages(tg="tg-polis-2026-11-11.html", asan="asan-mobile-2026-11-11.html"):
    return {
        g.DIM_URL: raw("dim-teqvim-p1.html"),
        g.DIM_URL + "?page=2": raw("dim-teqvim-p2.html"),
        g.DIM_URL + "?page=3": raw("dim-teqvim-p5.html"),
        g.ASAN_URL: raw(asan),
        g.MUR_CSV: raw("muraciet.csv"),
        g.MUR_PAGE: raw("vxsida-detail6.html"),
        g.TG_URL: raw(tg),
        g.TG_URL + "?before=6940": raw("tg-polis-b6940.html"),
        g.TG_URL + "?before=6920": raw("tg-polis-b6920.html"),
        g.TG_URL + "?before=6900": raw("tg-polis-b6900.html"),
    }


class Fake:
    """Saxta fetch: ünvan -> bayt; siyahıda olmayan ünvan və Exception dəyəri xəta verir. Çağırışlar calls-dadır."""

    def __init__(self, table):
        self.table, self.calls, self.timeouts = table, [], []

    def __call__(self, url, timeout=None, headers=None):
        self.calls.append(url)
        self.timeouts.append(timeout)
        value = self.table.get(url)
        if value is None:
            raise OSError("ünvan yoxdur")
        if isinstance(value, Exception):
            raise value
        return value


def dim_all():
    return g.dim_events(text("dim-teqvim-p1.html")) + g.dim_events(text("dim-teqvim-p2.html"))


def event(name, kind, start, end=None, cat=""):
    return {"name": name, "link": "", "status": "", "kind": kind, "cat": cat, "start": start, "end": end}


def tg_post(pid, name="tg-polis-2026-11-11.html"):
    return next(p for p in g.tg_posts(text(name)) if p["id"] == pid)


SUMMARY = ("📊 Noyabrın 10-da polis tərəfindən:\n\n- 34 cinayətin açılması təmin olunub (29-u cari, 5-i əvvəlki dövrlərdən).\n\n"
           "- 35 axtarışda olan şəxs saxlanılıb (19-u borclu şəxs).\n\n- 37 cinayət törətməkdə şübhəli bilinən şəxs saxlanılıb.\n\n"
           "- 7 narkotik, 2 qanunsuz silah-sursat faktı aşkarlanıb.")


class FormatTest(unittest.TestCase):
    def test_number_suffixes(self):
        self.assertEqual([g.num_loc(n) for n in (4, 30, 19, 10, 12, 6, 20, 100)],
                         ["4-də", "30-da", "19-da", "10-da", "12-də", "6-da", "20-də", "100-də"])
        self.assertEqual([g.num_abl(n) for n in (12, 6, 1, 13)], ["12-dən", "6-dan", "1-dən", "13-dən"])
        self.assertEqual([g.num_poss(n) for n in (67, 6, 53, 30, 11, 90, 100, 29, 5, 102)],
                         ["67-si", "6-sı", "53-ü", "30-u", "11-i", "90-ı", "100-ü", "29-u", "5-i", "102-si"])

    def test_dates(self):
        self.assertEqual(g.date_loc(D(2026, 11, 12)), "noyabrın 12-də")
        self.assertEqual(g.date_loc(D(2026, 4, 3)), "aprelin 3-də")
        self.assertEqual(g.date_loc(D(2026, 6, 10)), "iyunun 10-da")
        self.assertEqual(g.date_abl(D(2026, 12, 1)), "dekabrın 1-dən")
        self.assertEqual(g._span(D(2026, 11, 12), D(2026, 11, 26)), "12–26 noyabr")
        self.assertEqual(g._span(D(2026, 11, 30), D(2026, 12, 6)), "30 noyabr – 6 dekabr")
        self.assertEqual(g._span(D(2026, 12, 31), D(2027, 1, 4)), "31 dekabr 2026 – 4 yanvar 2027")
        self.assertEqual(g._span(D(2026, 11, 12), D(2026, 11, 12)), "12 noyabr")

    def test_days_loc(self):
        self.assertEqual(g.days_loc([D(2026, 11, 4)]), "noyabrın 4-də")
        self.assertEqual(g.days_loc([D(2026, 10, 31), D(2026, 11, 1)]), "oktyabrın 31-də və noyabrın 1-də")
        self.assertEqual(g.days_loc([D(2026, 11, 7), D(2026, 11, 8)]), "noyabrın 7-də və 8-də")
        self.assertEqual(g.days_loc([D(2026, 11, d) for d in range(6, 11)]), "noyabrın 6-dan 10-dək")
        self.assertEqual(g.days_loc([D(2026, 10, 30), D(2026, 10, 31), D(2026, 11, 1)]), "oktyabrın 30-dan noyabrın 1-dək")
        self.assertEqual(g.days_loc([D(2026, 11, 7), D(2026, 11, 8), D(2026, 11, 10)]), "noyabrın 7-də, 8-də və 10-da")

    def test_names(self):
        self.assertEqual([g._dat(n) for n in ("Bakı", "Gəncə", "Abşeron", "Sumqayıt", "Şəki")],
                         ["Bakıya", "Gəncəyə", "Abşerona", "Sumqayıta", "Şəkiyə"])
        self.assertEqual(g._cap("iyunun 3-də"), "İyunun 3-də")
        self.assertEqual(g._cap("noyabrın 3-də"), "Noyabrın 3-də")
        self.assertEqual(sorted(["Quba", "Qəbələ", "Tovuz", "Şirvan", "Goranboy", "Qusar"], key=g._az_key),
                         ["Goranboy", "Qəbələ", "Quba", "Qusar", "Şirvan", "Tovuz"])

    def test_place_typo_fix_only_for_one_extra_letter(self):
        self.assertEqual(g._fix_place("Netftçala rayonu, Mərkəz küçəsi 2", "Neftçala"), "Neftçala rayonu, Mərkəz küçəsi 2")
        self.assertEqual(g._fix_place("Ağdam rayonu", "Ağdaş"), "Ağdam rayonu")       # başqa rayon ola bilər
        self.assertEqual(g._fix_place("Şəki rayonu", "Şəmkir"), "Şəki rayonu")
        self.assertEqual(g._fix_place("Binəqədi rayonu, Biləcəri qəsəbəsi", "Bakı"), "Binəqədi rayonu, Biləcəri qəsəbəsi")
        self.assertEqual(g._fix_place("Xaçmaz rayonu", "Xaçmaz (Xudat ş)"), "Xaçmaz rayonu")


class DimTest(unittest.TestCase):
    def test_events_from_real_page(self):
        ev = g.dim_events(text("dim-teqvim-p1.html"))
        self.assertEqual(len(ev), 12)
        first = ev[0]
        self.assertEqual(first["name"], "Qiymətləndirmə fəaliyyəti ilə məşğul olmaq üçün ixtisas imtahanlarında iştirak üçün qeydiyyat")
        self.assertEqual((first["start"], first["end"], first["kind"], first["cat"], first["status"]),
                         (D(2026, 10, 6), D(2026, 11, 8), "Qeydiyyat", "Qiymətləndirmə fəaliyyəti", "Keçirilir"))
        self.assertTrue(first["link"].startswith("https://dim.gov.az/az/teqvim/"))
        taxi = ev[6]   # kateqoriya xanası boşdur
        self.assertEqual((taxi["kind"], taxi["cat"], taxi["end"]), ("Qeydiyyat", "", D(2026, 11, 19)))
        sat = ev[7]    # imtahanın bitmə tarixi yoxdur
        self.assertEqual((sat["kind"], sat["start"], sat["end"]), ("İmtahan", D(2026, 11, 7), None))

    def test_garbage_page_has_no_events(self):
        self.assertEqual(g.dim_events("<html><body>Xəta 500</body></html>"), [])
        self.assertEqual(g.dim_events(""), [])

    def test_week_digest(self):
        item = g.dim_week_item(dim_all(), D(2026, 11, 9))
        self.assertEqual(item["key"], "dim-hefte-2026-11-09")
        self.assertEqual(item["title"], "DİM-in bu həftəki təqvimi: 2 qeydiyyatın son günü, 1 imtahan və 1 yeni qeydiyyat")
        self.assertEqual(item["lead"], "Dövlət İmtahan Mərkəzinin (DİM) təqviminə görə, 9–15 noyabr tarixlərində 2 qeydiyyat başa "
                                       "çatır, 1 imtahan keçirilir və 1 qeydiyyat başlayır.")
        self.assertEqual(item["body"], [
            "10 noyabr, çərşənbə axşamı — qeydiyyatın son günü: Aqrar sığorta fəaliyyəti üzrə müstəqil ekspert sertifikatı almaq "
            "istəyən namizədlər üçün test imtahanına qeydiyyat",
            "12 noyabr, cümə axşamı — qeydiyyatın son günü: Peşəkar mühasib sertifikatı imtahanına qeydiyyat (I mərhələ)",
            "12 noyabr, cümə axşamı — qeydiyyat başlayır: İnzibati vəzifələr üzrə müsabiqənin test imtahanına (A və B növü) "
            "qeydiyyat (son gün: 2 dekabr)",
            "14 noyabr, şənbə — imtahan: TKT (kağız-əsaslı)"])
        self.assertTrue(item["worth"] and item["list"])
        self.assertEqual((item["slot"], item["topic"], item["credit"], item["link"]),
                         ("09:00", "təqvim", "Dövlət İmtahan Mərkəzi", g.DIM_URL))

    def test_week_digest_cap(self):
        full = g.dim_week_item(dim_all(), D(2026, 11, 16))
        self.assertEqual(full["title"], "DİM-in bu həftəki təqvimi: 3 qeydiyyatın son günü və 7 imtahan")
        self.assertEqual(len(full["body"]), 10)
        self.assertIn("20 noyabr, cümə — imtahan: GRE (saat 09:00)", full["body"])
        with patch.object(g, "DIM_LINES", 5):
            cut = g.dim_week_item(dim_all(), D(2026, 11, 16))
        self.assertEqual(len(cut["body"]), 6)
        self.assertEqual(cut["body"][-1], "Təqvimdə bu həftə daha 5 tədbir var.")

    def test_week_without_events_or_incomplete(self):
        empty = g.dim_week_item(dim_all(), D(2026, 12, 14))
        self.assertFalse(empty["worth"])
        self.assertIn("yoxdur", empty["why"])
        part = g.dim_week_item(dim_all(), D(2026, 11, 9), complete=False)
        self.assertFalse(part["worth"])
        self.assertIn("çatılmadı", part["why"])

    def test_deadline_day_single(self):
        item = g.dim_day_item(dim_all(), D(2026, 11, 12))
        self.assertEqual(item["key"], "dim-gun-2026-11-12")
        self.assertEqual(item["title"], "Peşəkar mühasib sertifikatı imtahanına qeydiyyat (I mərhələ) noyabrın 12-də başa çatır")
        self.assertEqual(item["lead"], "Dövlət İmtahan Mərkəzinin (DİM) təqviminə görə, «Peşəkar mühasib sertifikatı imtahanına "
                                       "qeydiyyat (I mərhələ)» bu gün, noyabrın 12-də başa çatır. Qeydiyyat oktyabrın 22-də "
                                       "başlayıb. İmtahan noyabrın 22-də keçiriləcək.")
        self.assertEqual(item["body"], [])
        self.assertTrue(item["worth"])
        self.assertTrue(item["link"].startswith("https://dim.gov.az/az/teqvim/pesekar-muhasib"))

    def test_deadline_title_falls_back_to_category_then_generic(self):
        item = g.dim_day_item(dim_all(), D(2026, 11, 10))
        self.assertEqual(item["title"], "Aqrar sığorta üzrə qeydiyyat noyabrın 10-da başa çatır")
        self.assertIn("İmtahan noyabrın 18-də keçiriləcək.", item["lead"])
        long = event("Çox uzun adlı " + "sınaq " * 20 + "imtahanına qeydiyyat", "Qeydiyyat", D(2026, 11, 1), D(2026, 11, 10))
        item = g.dim_day_item([long], D(2026, 11, 10))
        self.assertEqual(item["title"], "DİM-in təqvimi: bir qeydiyyat noyabrın 10-da başa çatır")
        self.assertLessEqual(len(item["title"]), g.TITLE_MAX)

    def test_deadline_day_several(self):
        item = g.dim_day_item(dim_all(), D(2026, 11, 19))
        self.assertEqual(item["title"], "DİM-in təqvimi: noyabrın 19-da 3 qeydiyyat başa çatır")
        self.assertEqual(item["lead"], "Dövlət İmtahan Mərkəzinin (DİM) təqviminə görə, bu gün, noyabrın 19-da 3 qeydiyyatın son günüdür.")
        self.assertEqual(len(item["body"]), 3)
        self.assertEqual(item["body"][0], "Dövlət qulluğuna qəbul imtahanına qeydiyyat (BB vəzifə qrupu üzrə): 29 oktyabr – 19 noyabr")
        self.assertTrue(item["list"])

    def test_no_deadline_or_incomplete_is_not_news(self):
        none = g.dim_day_item(dim_all(), D(2026, 11, 13))
        self.assertEqual((none["key"], none["worth"], none["why"]), ("dim-gun-2026-11-13", False, "bu gün qeydiyyatın son günü yoxdur"))
        part = g.dim_day_item(dim_all(), D(2026, 11, 12), complete=False)
        self.assertEqual((part["key"], part["worth"]), ("dim-gun-2026-11-12-natamam", False))

    def test_exam_is_matched_only_by_name(self):
        reg = event("Sınaq imtahanına qeydiyyat", "Qeydiyyat", D(2026, 11, 1), D(2026, 11, 12))
        other = event("Başqa imtahan", "İmtahan", D(2026, 11, 20))
        early = event("Sınaq imtahanı", "İmtahan", D(2026, 11, 5))
        mine = event("Sınaq imtahanı", "İmtahan", D(2026, 11, 25))
        self.assertIsNone(g._exam_of(reg, [reg, other, early]))
        self.assertIs(g._exam_of(reg, [reg, other, early, mine]), mine)

    def test_leadership_event_is_left_out(self):
        bad = event(f"{LEADER}in adına təqaüd müsabiqəsinə qeydiyyat", "Qeydiyyat", D(2026, 11, 1), D(2026, 11, 12))
        day = g.dim_day_item([bad], D(2026, 11, 12))
        self.assertFalse(day["worth"])
        week = g.dim_week_item(dim_all() + [bad], D(2026, 11, 9))
        self.assertEqual(week["skipped"], [bad["name"]])
        self.assertNotIn("Əliyev", "\n".join([week["title"], week["lead"]] + week["body"]))
        self.assertEqual(len(week["body"]), 4)

    def test_paging_stops_when_the_needed_day_is_reached(self):
        fake = Fake(pages())
        events, complete = g.dim_get(g._Net(fake), D(2026, 11, 12))
        self.assertEqual((len(events), complete, fake.calls), (12, True, [g.DIM_URL]))
        fake = Fake(pages())
        events, complete = g.dim_get(g._Net(fake), D(2026, 11, 22))
        self.assertEqual((len(events), complete, len(fake.calls)), (24, True, 2))

    def test_paging_gives_up_after_three_pages(self):
        fake = Fake(pages())
        events, complete = g.dim_get(g._Net(fake), D(2027, 7, 1))
        self.assertEqual((complete, len(fake.calls)), (False, g.DIM_PAGES))
        table = pages()
        table[g.DIM_URL + "?page=2"] = b"<html>bos</html>"
        events, complete = g.dim_get(g._Net(Fake(table)), D(2026, 11, 22))
        self.assertEqual((len(events), complete), (12, False))
        table[g.DIM_URL] = b"<html>bos</html>"
        with self.assertRaises(ValueError):
            g.dim_get(g._Net(Fake(table)), D(2026, 11, 12))


class AsanTest(unittest.TestCase):
    def test_stops_from_real_page(self):
        stops = g.asan_stops(text("asan-mobile.html"))
        self.assertEqual(len(stops), 18)
        self.assertEqual(len({s["bus"] for s in stops}), 9)   # İmişli avtobusunun məntəqəsi yoxdur
        baki = stops[0]
        self.assertEqual((baki["bus"], baki["place"], baki["short"], baki["start"], baki["end"], baki["days"]),
                         ("Bakı Səyyar ASAN xidmət avtobusu", "Binəqədi rayonu, Biləcəri qəsəbəsi", "Bakı",
                          D(2026, 11, 12), D(2026, 11, 26), 15))
        self.assertEqual(baki["link"], "https://asan.gov.az/mobile-service/baki-seyyar-asan-avtobusu")
        self.assertTrue(stops[1]["place"].startswith("Neftçala rayonu, "))   # mənbədə «Netftçala»

    def test_one_bus_tomorrow(self):
        item = g.asan_item(g.asan_stops(text("asan-mobile-2026-11-11.html")), D(2026, 11, 12))
        self.assertEqual(item["key"], "seyyar-asan-2026-11-13")
        self.assertEqual(item["title"], "Səyyar ASAN xidmət avtobusu noyabrın 13-dən Ağdam rayonunda olacaq")
        self.assertEqual(item["lead"], "«ASAN xidmət»in cədvəlinə görə, Bərdə Səyyar ASAN xidmət avtobusu 13–26 noyabr tarixlərində "
                                       "(14 gün) Ağdam rayonunda xidmət göstərəcək.")
        self.assertEqual((item["link"], item["slot"], item["worth"], item["body"]),
                         ("https://asan.gov.az/mobile-service/berde-seyyar-asan-avtobusu", "10:00", True, []))

    def test_settlement_and_address(self):
        item = g.asan_item(g.asan_stops(text("asan-mobile.html")), D(2026, 11, 11))
        self.assertEqual(item["title"], "Səyyar ASAN xidmət avtobusu noyabrın 12-dən Biləcəri qəsəbəsində olacaq")
        self.assertEqual(item["lead"], "«ASAN xidmət»in cədvəlinə görə, Bakı Səyyar ASAN xidmət avtobusu 12–26 noyabr tarixlərində "
                                       "(15 gün) Binəqədi rayonunun Biləcəri qəsəbəsində xidmət göstərəcək.")
        item = g.asan_item(g.asan_stops(text("asan-mobile-2026-11-11.html")), D(2026, 11, 11))
        self.assertEqual(item["title"], "Səyyar ASAN xidmət avtobusu noyabrın 12-dən Binəqədi rayonunda olacaq")
        self.assertIn("Binəqədi rayonunda (Biləcəri qəsəbəsi, Asəf Zeynallı 35, Biləcəri Bələdiyyəsinin qarşısı) xidmət göstərəcək.",
                      item["lead"])

    def test_many_buses_in_one_item(self):
        item = g.asan_item(g.asan_stops(text("asan-mobile-2026-11-11.html")), D(2026, 11, 30))
        self.assertEqual(item["key"], "seyyar-asan-2026-12-01")
        self.assertEqual(item["title"], "Səyyar ASAN xidmət avtobusları dekabrın 1-dən 8 məntəqədə xidmət göstərəcək")
        self.assertEqual(item["lead"], "«ASAN xidmət»in cədvəlinə görə, dekabrın 1-dən 8 Səyyar ASAN xidmət avtobusu aşağıdakı "
                                       "məntəqələrdə xidmət göstərəcək.")
        self.assertEqual(len(item["body"]), 8)
        self.assertEqual(item["body"][0], "Bərdə avtobusu: Tərtər rayonu, 1–18 dekabr (18 gün)")
        self.assertEqual(item["body"][2], "Qəbələ avtobusu: Ağsu rayonu, 1–18 dekabr (18 gün)")
        self.assertTrue(item["list"] and item["worth"])
        self.assertEqual(item["link"], g.ASAN_URL)

    def test_two_buses(self):
        stops = [s for s in g.asan_stops(text("asan-mobile-2026-11-11.html"))
                 if s["start"] == D(2026, 12, 1) and s["bus"].split()[0] in ("Sabirabad", "Gəncə")]
        item = g.asan_item(stops, D(2026, 11, 30))
        self.assertEqual(item["title"], "Səyyar ASAN xidmət avtobusları dekabrın 1-dən Şəmkir və Şirvanda olacaq")
        self.assertEqual(item["lead"], "«ASAN xidmət»in cədvəlinə görə, Gəncə Səyyar ASAN xidmət avtobusu 1–18 dekabr tarixlərində "
                                       "(18 gün) Şəmkir rayonunda xidmət göstərəcək. Sabirabad Səyyar ASAN xidmət avtobusu isə "
                                       "1–18 dekabr tarixlərində (18 gün) Şirvan rayonunda xidmət göstərəcək.")
        self.assertEqual(item["body"], [])

    def test_nothing_starts_tomorrow(self):
        item = g.asan_item(g.asan_stops(text("asan-mobile-2026-11-11.html")), D(2026, 11, 13))
        self.assertEqual((item["key"], item["worth"]), ("seyyar-asan-2026-11-14", False))
        self.assertIn("yoxdur", item["why"])

    def test_bad_rows(self):
        page = ('<article><h3><a href="https://asan.gov.az/mobile-service/x">Sınaq Səyyar ASAN xidmət avtobusu</a></h3>'
                '<a href="javascript:;" data-place="Quba rayonu" data-date="01.12.2026 - 18.12.2026, 17-gün"><span>Quba</span></a>'
                '<a href="javascript:;" data-place="Qusar rayonu" data-date="18.12.2026 - 01.12.2026, 18-gün"><span>Qusar</span></a>'
                '<a href="javascript:;" data-place="" data-date="01.12.2026 - 18.12.2026"><span>Boş</span></a>'
                '<a href="javascript:;" data-place="Şabran rayonu" data-date="tezliklə"><span>Şabran</span></a></article>')
        stops = g.asan_stops(page)
        self.assertEqual([(s["place"], s["days"]) for s in stops], [("Quba rayonu", None)])   # gün sayı tarixlərə uyğun deyil
        self.assertNotIn("gün)", g.asan_item(stops, D(2026, 11, 30))["lead"])
        self.assertEqual(g.asan_stops("<html><body>Xəta</body></html>"), [])


class MuracietTest(unittest.TestCase):
    def rows(self):
        return g.mur_rows(raw("muraciet.csv"))

    def test_rows_from_real_csv(self):
        rows = self.rows()
        self.assertEqual(len(rows), 180)
        self.assertEqual(max(r[0] for r in rows), D(2026, 11, 6))
        self.assertIn((D(2022, 5, 14), "Abşeron", 1), rows)   # «Abşeron » — boşluq silinir

    def test_utf8_and_bad_rows(self):
        data = "problem_count,date,region\n3,2026-11-02,Bakı\nx,2026-11-02,Bakı\n2,dünən,Bakı\n4,2026-11-03\n"
        self.assertEqual(g.mur_rows(data.encode("utf-8")), [(D(2026, 11, 2), "Bakı", 3)])

    def test_garbage_is_an_error(self):
        for bad in (b"", b"<!DOCTYPE html><html><title>Google Drive - Virus scan warning</title></html>",
                    "say,tarix\n1,2".encode("utf-8"), "problem_count,date,region\n".encode("utf-8")):
            with self.assertRaises(ValueError):
                g.mur_rows(bad)

    def test_weekly_item(self):
        item = g.mur_item(self.rows(), D(2026, 11, 9))
        self.assertEqual(item["key"], "asan-muraciet-2026-11-02")
        self.assertEqual(item["title"], "Ötən həftə «ASAN müraciət» vasitəsilə 108 problem göndərilib, 67-si Bakıya aiddir")
        self.assertEqual(item["lead"], "VXSİDA-nın Publik Data Portalındakı məlumata görə, 2–6 noyabr tarixlərində «ASAN müraciət» "
                                       "informasiya sistemi vasitəsilə 108 problem göndərilib. Ən çox problem Bakı (67), Gəncə (10), "
                                       "Abşeron (8) və Sumqayıt (8) üzrə qeydə alınıb. Bir həftə əvvəl (26–30 oktyabr) bu say 144 olub.")
        self.assertEqual(item["body"], ["Problemlər 13 regiona aiddir: Bakı – 67, Gəncə – 10, Abşeron – 8, Sumqayıt – 8, Şəki – 4, "
                                        "Yevlax – 3, Şamaxı – 2, Goranboy – 1, Qəbələ – 1, Quba – 1, Qusar – 1, Şirvan – 1, Tovuz – 1."])
        self.assertEqual((item["worth"], item["slot"], item["topic"], item["link"]), (True, "11:00", "icmal", g.MUR_PAGE))

    def test_stale_data_is_not_news(self):
        item = g.mur_item(self.rows(), D(2026, 11, 16))   # 11–13 noyabrın məlumatı yoxdur
        self.assertEqual((item["key"], item["worth"]), ("asan-muraciet-2026-11-09", False))
        self.assertIn("yenilənməyib", item["why"])

    def test_previous_week_only_with_same_number_of_work_days(self):
        rows = self.rows() + [(D(2026, 11, 11), "Bakı", 5), (D(2026, 11, 12), "Bakı", 4), (D(2026, 11, 13), "Gəncə", 9)]
        item = g.mur_item(rows, D(2026, 11, 16))   # 9 və 10 noyabr iş günü deyil: 3 iş günü 5 iş günü ilə müqayisə olunmur
        self.assertTrue(item["worth"])
        self.assertEqual(item["title"], "Ötən həftə «ASAN müraciət» vasitəsilə 18 problem göndərilib")   # iki region bərabərdir
        self.assertIn("11–13 noyabr tarixlərində", item["lead"])
        self.assertNotIn("Bir həftə əvvəl", item["lead"])

    def test_one_region_zero_and_cap(self):
        one = g.mur_item([(D(2026, 11, 2), "Bakı", 3), (D(2026, 11, 6), "Bakı", 4)], D(2026, 11, 9))
        self.assertEqual(one["title"], "Ötən həftə «ASAN müraciət» vasitəsilə 7 problem göndərilib, hamısı Bakıya aiddir")
        self.assertNotIn("Ən çox", one["lead"])
        self.assertEqual(one["body"], ["Problemlər 1 regiona aiddir: Bakı – 7."])
        zero = g.mur_item([(D(2026, 11, 6), "Bakı", 0)], D(2026, 11, 9))
        self.assertEqual((zero["worth"], zero["why"]), (False, "ötən həftə problem göndərilməyib"))
        many = g.mur_item([(D(2026, 11, 6), f"Rayon{n:02d}", 21 - n) for n in range(1, 21)], D(2026, 11, 9))
        self.assertIn("Problemlər 20 regiona aiddir: Rayon01 – 20, ", many["body"][0])
        self.assertTrue(many["body"][0].endswith("Rayon15 – 6, digər 5 region – 15."))

    def test_link_from_portal_page(self):
        self.assertEqual(g.mur_link(text("vxsida-detail6.html")), g.MUR_CSV)
        self.assertEqual(g.mur_link("<a href='http://x' id='ASAN_Appeal__Number_of_problems_by_region__csv'>"), "")
        self.assertEqual(g.mur_link("<html></html>"), "")

    def test_get_falls_back_to_the_portal_link(self):
        fake = Fake(pages())
        self.assertEqual(len(g.mur_get(g._Net(fake), D(2026, 11, 6))), 180)
        self.assertEqual(fake.calls, [g.MUR_CSV])
        new = "https://drive.google.com/uc?export=download&id=YENI"
        page = f'<a href="{new.replace("&", "&amp;")}" id="{g.MUR_ANCHOR}">CSV</a>'.encode("utf-8")
        fake = Fake({g.MUR_CSV: b"<html>Not found</html>", g.MUR_PAGE: page, new: raw("muraciet.csv")})
        self.assertEqual(len(g.mur_get(g._Net(fake), D(2026, 11, 6))), 180)
        self.assertEqual(fake.calls, [g.MUR_CSV, g.MUR_PAGE, new])
        fake = Fake({g.MUR_CSV: OSError("403"), g.MUR_PAGE: raw("vxsida-detail6.html")})   # səhifədəki ünvan eynidir
        with self.assertRaises(OSError):
            g.mur_get(g._Net(fake), D(2026, 11, 6))
        self.assertEqual(fake.calls, [g.MUR_CSV, g.MUR_PAGE])
        fake = Fake(pages())   # köhnə məlumat: ünvan yoxlanır, oxunan sətirlər qaytarılır
        self.assertEqual(len(g.mur_get(g._Net(fake), D(2026, 11, 13))), 180)
        self.assertEqual(fake.calls, [g.MUR_CSV, g.MUR_PAGE])


class PolisTest(unittest.TestCase):
    def test_posts_from_real_page(self):
        posts = g.tg_posts(text("tg-polis-2026-11-11.html"))
        self.assertEqual([p["id"] for p in posts], [6957, 6959, 6961, 6962, 6963, 6965])
        post = posts[-1]
        self.assertEqual(post["when"], datetime.datetime(2026, 11, 11, 11, 28, 41, tzinfo=g.BAKU))
        self.assertEqual(post["url"], "https://t.me/polisazerbaycan/6965")
        self.assertEqual(g.tg_before(text("tg-polis-2026-11-11.html")), 6940)
        self.assertEqual(g.tg_posts("<html></html>"), [])

    def test_summary_item(self):
        post = tg_post(6965)
        p, why = g.polis_parse(post["text"], post["when"].date())
        self.assertEqual(why, "")
        self.assertEqual((p["days"], p["crimes"], p["split"], p["wanted"], p["debt"], p["suspects"], p["missing"]),
                         ([D(2026, 11, 10)], 34, (29, 5), 35, 19, 37, 3))
        self.assertEqual(p["rest"], ["7 narkotik, 2 qanunsuz silah-sursat faktı aşkarlanıb.",
                                     "Dələduzluğa görə axtarışda olan 3 nəfər saxlanılıb."])
        item = g.polis_item(post, p)
        self.assertEqual(item["key"], "polis-icmal-2026-11-10")
        self.assertEqual(item["title"], "Noyabrın 10-da polis 34 cinayətin açılmasını təmin edib")
        self.assertEqual(item["lead"], "Daxili İşlər Nazirliyinin məlumatına görə, noyabrın 10-da polis 34 cinayətin açılmasını təmin "
                                       "edib (29-u cari, 5-i əvvəlki dövrlərdən). Axtarışda olan 35 nəfər (19-u borclu şəxs) və cinayət "
                                       "törətməkdə şübhəli bilinən 37 nəfər saxlanılıb, itkin kimi axtarılan 3 nəfər tapılıb.")
        self.assertEqual(item["body"], p["rest"])
        self.assertEqual((item["link"], item["credit"], item["slot"], item["topic"], item["worth"]),
                         ("https://t.me/polisazerbaycan/6965", "Daxili İşlər Nazirliyi", "12:00", "icmal", True))
        self.assertTrue(item["list"])

    def test_two_day_summary(self):
        post = tg_post(6905, "tg-polis-b6920.html")
        p, _ = g.polis_parse(post["text"], post["when"].date())
        self.assertEqual((p["days"], p["crimes"], p["split"], p["wanted"], p["debt"], p["suspects"], p["missing"]),
                         ([D(2026, 10, 31), D(2026, 11, 1)], 75, (66, 9), 83, 51, 63, 8))
        self.assertEqual(len(p["rest"]), 4)
        self.assertEqual(p["rest"][2], "Ümumi çəkisi 5,7 kq narkotik vasitə aşkarlanaraq götürülüb.")
        item = g.polis_item(post, p)
        self.assertEqual(item["key"], "polis-icmal-2026-11-01")
        self.assertEqual(item["title"], "Oktyabrın 31-də və noyabrın 1-də polis 75 cinayətin açılmasını təmin edib")
        self.assertIn("(66-sı cari, 9-u əvvəlki dövrlərdən)", item["lead"])
        self.assertIn("83 nəfər (51-i borclu şəxs)", item["lead"])

    def test_lone_dash_and_missing_split(self):
        post = tg_post(6891, "tg-polis-b6900.html")
        p, _ = g.polis_parse(post["text"], post["when"].date())
        self.assertEqual((p["crimes"], p["split"], p["wanted"], p["debt"], p["suspects"], p["missing"]), (53, (48, 5), 119, 94, 41, 6))
        self.assertIn("40,5 kq narkotik vasitə və 1 800 ədəd güclü təsiredici xassəyə malik həb qanunsuz dövriyyədən çıxarılıb.", p["rest"])
        post = tg_post(6896, "tg-polis-b6900.html")
        p, _ = g.polis_parse(post["text"], post["when"].date())
        self.assertEqual((p["crimes"], p["split"]), (39, None))
        self.assertIn("polis 39 cinayətin açılmasını təmin edib. Axtarışda olan 97 nəfər (74-ü borclu şəxs)", g.polis_item(post, p)["lead"])

    def test_other_posts_are_not_summaries(self):
        for pid, name in ((6895, "tg-polis-b6900.html"), (6907, "tg-polis-b6920.html"), (6963, "tg-polis-2026-11-11.html")):
            post = tg_post(pid, name)
            self.assertEqual(g.polis_parse(post["text"], post["when"].date()), (None, "icmal deyil"))
        for name in ("tg-polis-2026-11-10.html", "tg-polis-b6940.html"):
            found = [p["id"] for p in g.tg_posts(text(name)) if g.polis_parse(p["text"], p["when"].date())[0]]
            self.assertEqual(found, [6920] if "6940" in name else [])

    def test_broken_summaries(self):
        day = D(2026, 11, 11)
        p, why = g.polis_parse("📊 Noyabrın 10-da polis tərəfindən:\n\n- 34 cinayətin açılması təmin olunub.\n\n- 7 narkotik faktı aşkarlanıb.", day)
        self.assertIsNone(p)
        self.assertIn("üç əsas rəqəm", why)
        self.assertEqual(g.polis_parse(SUMMARY.replace("Noyabrın 10-da", "Dünən"), day), (None, "icmalın tarixi oxunmadı"))
        self.assertEqual(g.polis_parse(SUMMARY.replace("Noyabrın 10-da", "Noyabrın 31-də"), day), (None, "icmalın tarixi oxunmadı"))
        p, _ = g.polis_parse(SUMMARY.replace("29-u cari", "20-si cari").replace("19-u borclu", "190-ı borclu"), day)
        self.assertEqual((p["crimes"], p["split"], p["debt"], p["missing"]), (34, None, None, None))   # cəm düz gəlmir: yazılmır
        item = g.polis_item({"id": 1, "url": g.TG_URL, "when": at(2026, 11, 11, 11), "text": SUMMARY}, p)
        self.assertEqual(item["lead"], "Daxili İşlər Nazirliyinin məlumatına görə, noyabrın 10-da polis 34 cinayətin açılmasını təmin "
                                       "edib. Axtarışda olan 35 nəfər və cinayət törətməkdə şübhəli bilinən 37 nəfər saxlanılıb.")

    def test_foreign_lines_are_not_copied(self):
        p, _ = g.polis_parse(SUMMARY + "\n\n#PolisAzərbaycan #DİN2026\nƏtraflı: 102 xidməti", D(2026, 11, 11))
        self.assertEqual(p["rest"], ["7 narkotik, 2 qanunsuz silah-sursat faktı aşkarlanıb."])

    def test_phrase_days(self):
        posted = D(2026, 11, 11)
        five = [D(2026, 11, d) for d in range(6, 11)]
        self.assertEqual(g.phrase_days("Noyabrın 6-dan 10-dək", posted), five)
        self.assertEqual(g.phrase_days("Noyabrın 6–10-da", posted), five)
        self.assertEqual(g.phrase_days("Noyabrın 7-də, 8-də və 10-da", posted), [D(2026, 11, 7), D(2026, 11, 8), D(2026, 11, 10)])
        self.assertEqual(g.phrase_days("Dekabrın 31-də və yanvarın 1-də", D(2027, 1, 2)), [D(2026, 12, 31), D(2027, 1, 1)])
        self.assertEqual(g.phrase_days("İyunun 3-də", D(2026, 6, 4)), [D(2026, 6, 3)])
        for bad in ("Ötən gün", "10-da", "Noyabrın", "Noyabrın 10-dan", "Noyabrın 10-dək", "Fevralın 30-da"):
            self.assertIsNone(g.phrase_days(bad, posted), bad)

    def test_only_todays_fresh_summary_is_used(self):
        posts = g.tg_posts(text("tg-polis-2026-11-11.html"))
        post, p, why = g.polis_find(posts, D(2026, 11, 11))
        self.assertEqual((post["id"], why), (6965, ""))
        post, p, why = g.polis_find(posts, D(2026, 11, 12))   # dünənki yazı bu günün icmalı deyil
        self.assertIsNone(post)
        self.assertIn("hələ dərc olunmayıb", why)
        old = {"id": 7000, "url": g.TG_URL, "when": at(2026, 11, 11, 11), "text": SUMMARY.replace("Noyabrın 10-da", "Noyabrın 2-də")}
        post, p, why = g.polis_find([old], D(2026, 11, 11))
        self.assertIsNone(post)
        self.assertIn("köhnədir", why)

    def test_expected_days(self):
        self.assertEqual([g.polis_day(D(2026, 11, d)) for d in (7, 8, 9, 10, 11, 14)], [True, False, False, False, True, True])
        self.assertFalse(g.polis_day(D(2027, 1, 2)))   # şənbəyə düşən bayram

    def test_leadership_is_not_published(self):
        post = {"id": 1, "url": g.TG_URL, "when": at(2026, 11, 11, 11), "text": SUMMARY + f"\n\n- {LEADER} 3 əməkdaşı təltif edib."}
        p, _ = g.polis_parse(post["text"], D(2026, 11, 11))
        item = g.polis_item(post, p)
        self.assertFalse(item["worth"])
        self.assertIn("rəhbərliyin adı", item["why"])


class ItemsTest(unittest.TestCase):
    def run_at(self, now, table=None, done=None):
        fake = Fake(pages() if table is None else table)
        return g.items(ROOT, now, fake, done), fake

    def test_no_request_outside_the_windows(self):
        for hh, mm in ((0, 0), (8, 59), (9, 30), (10, 30), (11, 0), (11, 44), (12, 15), (18, 0)):
            out, fake = self.run_at(at(2026, 11, 12, hh, mm))   # cümə axşamı
            self.assertEqual((out, fake.calls), ([], []), (hh, mm))

    def test_each_source_in_its_window(self):
        out, fake = self.run_at(at(2026, 11, 12, 9, 5))
        self.assertEqual([(i["key"], i["worth"]) for i in out], [("dim-gun-2026-11-12", True)])
        self.assertEqual((fake.calls, fake.timeouts), ([g.DIM_URL], [15]))
        out, fake = self.run_at(at(2026, 11, 12, 10, 0))
        self.assertEqual([(i["key"], i["worth"]) for i in out], [("seyyar-asan-2026-11-13", True)])
        self.assertEqual(fake.calls, [g.ASAN_URL])
        out, fake = self.run_at(at(2026, 11, 11, 11, 50))
        self.assertEqual([(i["key"], i["worth"]) for i in out], [("polis-icmal-2026-11-10", True)])
        self.assertEqual(fake.calls, [g.TG_URL])

    def test_monday(self):
        out, fake = self.run_at(at(2026, 11, 16, 9, 0))
        self.assertEqual([(i["key"], i["worth"]) for i in out], [("dim-hefte-2026-11-16", True)])
        self.assertEqual(fake.calls, [g.DIM_URL, g.DIM_URL + "?page=2"])
        out, fake = self.run_at(at(2026, 11, 9, 11, 0))
        self.assertEqual([(i["key"], i["worth"]) for i in out], [("asan-muraciet-2026-11-02", True)])
        self.assertEqual(fake.calls, [g.MUR_CSV])
        out, fake = self.run_at(at(2026, 11, 16, 11, 0))   # məlumat köhnədir
        self.assertEqual([(i["key"], i["worth"]) for i in out], [("asan-muraciet-2026-11-09", False)])
        self.assertEqual(fake.calls, [g.MUR_CSV, g.MUR_PAGE])
        out, fake = self.run_at(at(2026, 11, 17, 11, 0))   # çərşənbə axşamı: müraciət xəbəri yoxdur
        self.assertEqual((out, fake.calls), ([], []))

    def test_police_summary_not_out_yet_and_days_off(self):
        out, fake = self.run_at(at(2026, 11, 11, 11, 50), pages(tg="tg-polis-2026-11-10.html"))
        self.assertEqual([(i["key"], i["worth"]) for i in out], [("polis-icmal-gozlenilir-2026-11-11", False)])
        self.assertIn("hələ dərc olunmayıb", out[0]["why"])
        for day in (8, 9, 10, 15):   # bazar, bayram, köçürülən istirahət günü, bazar
            out, fake = self.run_at(at(2026, 11, day, 11, 50))
            self.assertEqual((out, fake.calls), ([], []), day)

    def test_done_keys_cost_no_request(self):
        for now, key in ((at(2026, 11, 12, 9, 5), "dim-gun-2026-11-12"), (at(2026, 11, 16, 9, 5), "dim-hefte-2026-11-16"),
                         (at(2026, 11, 12, 10, 5), "seyyar-asan-2026-11-13"), (at(2026, 11, 9, 11, 5), "asan-muraciet-2026-11-02"),
                         (at(2026, 11, 11, 11, 50), "polis-icmal-2026-11-10")):
            out, fake = self.run_at(now, done={key})
            self.assertEqual((out, fake.calls), ([], []), key)
            out, fake = self.run_at(now, done={"basqa-acar"})
            self.assertEqual([i["key"] for i in out], [key])

    def test_network_failure_and_garbage_never_raise(self):
        times = (at(2026, 11, 12, 9, 5), at(2026, 11, 16, 9, 5), at(2026, 11, 12, 10, 5), at(2026, 11, 9, 11, 5), at(2026, 11, 11, 11, 50))
        junk = {url: b"<html><body>503</body></html>" for url in pages()}
        boom = {url: RuntimeError("partladı") for url in pages()}
        for now in times:
            for table in ({}, junk, boom):
                out, fake = self.run_at(now, table)
                self.assertEqual(len(out), 1)
                self.assertFalse(out[0]["worth"])
                self.assertTrue(out[0]["why"])
                self.assertIn("-xeta-", out[0]["key"])
                self.assertGreaterEqual(len(fake.calls), 1)

    def test_dropped_connection_is_retried_once(self):
        class Flaky(Fake):
            def __init__(self, table, errors):
                super().__init__(table)
                self.errors = list(errors)

            def __call__(self, url, timeout=None, headers=None):
                if self.errors:
                    self.calls.append(url)
                    raise self.errors.pop(0)
                return super().__call__(url, timeout, headers)

        now = at(2026, 11, 12, 9, 5)
        fake = Flaky(pages(), [ConnectionResetError(104, "Connection reset by peer")])
        out = g.items(ROOT, now, fake)
        self.assertEqual([(i["key"], i["worth"]) for i in out], [("dim-gun-2026-11-12", True)])
        self.assertEqual(fake.calls, [g.DIM_URL, g.DIM_URL])
        fake = Flaky(pages(), [urllib.error.URLError(ConnectionResetError(104, "Connection reset by peer"))] * 3)
        out = g.items(ROOT, now, fake)
        self.assertEqual((out[0]["key"], out[0]["worth"], len(fake.calls)), ("dim-xeta-2026-11-12", False, 2))
        for err in (TimeoutError("vaxt bitdi"), urllib.error.URLError(TimeoutError("vaxt bitdi")),
                    urllib.error.HTTPError(g.DIM_URL, 403, "Forbidden", None, None)):
            fake = Flaky(pages(), [err])   # vaxt aşımı və HTTP xətası təkrar yoxlanmır
            out = g.items(ROOT, now, fake)
            self.assertEqual((out[0]["worth"], len(fake.calls)), (False, 1), repr(err))

    def test_item_shape_determinism_and_naive_time(self):
        seen = []
        for now in (at(2026, 11, 12, 9, 5), at(2026, 11, 16, 9, 5), at(2026, 11, 12, 10, 5), at(2026, 11, 9, 11, 5),
                    at(2026, 11, 16, 11, 5), at(2026, 11, 11, 11, 50), at(2026, 11, 13, 9, 5), at(2026, 11, 13, 10, 5)):
            out, _ = self.run_at(now)
            again, _ = self.run_at(now)
            self.assertEqual(out, again)
            naive, _ = self.run_at(now.replace(tzinfo=None))
            self.assertEqual(out, naive)
            seen += out
        self.assertEqual(len(seen), 8)
        for item in seen:
            self.assertLessEqual(KEYS, set(item), item["key"])
            self.assertIsInstance(item["body"], list)
            self.assertRegex(item["slot"], r"^\d\d:\d\d$")
            self.assertIn(item["topic"], ("təqvim", "icmal"))
            self.assertTrue(item["link"].startswith("https://"))
            if item["worth"]:
                self.assertLessEqual(len(item["title"]), g.TITLE_MAX)
                self.assertFalse(item["title"].endswith("."))
                self.assertFalse(ox.needs_owner("\n".join([item["title"], item["lead"]] + item["body"])))
                self.assertTrue(ox.render(item))
            else:
                self.assertTrue(item["why"])

    def test_guard_blocks_leadership_and_long_titles(self):
        ok = g._item("x", "k", "Başlıq", "Giriş.", ["Bənd."], "Mənbə", "https://x", "icmal", "12:00")
        self.assertIs(g._guard(ok), ok)
        bad = g._guard(dict(ok, body=[f"{LEADER} iştirak edib."]))
        self.assertEqual((bad["worth"], bad["why"]), (False, "rəhbərliyin adı keçir: avtomatik dərc olunmur"))
        long = g._guard(dict(ok, title="a" * (g.TITLE_MAX + 1)))
        self.assertFalse(long["worth"])

    def day_requests(self, day, step, record_all):
        """Bir günün bütün dövrələri: sorğuların sayı. record_all — canlı qaytarılan bütün açarları done-a yazır."""
        fake, done = Fake(pages()), set()
        now = datetime.datetime.combine(day, datetime.time(0, 0), tzinfo=g.BAKU)
        while now.date() == day:
            for item in g.items(ROOT, now, fake, done):
                if record_all or item["worth"]:
                    done.add(item["key"])
            now += datetime.timedelta(minutes=step)
        return len(fake.calls)

    def test_daily_request_budget(self):
        for day in (D(2026, 11, 9), D(2026, 11, 11), D(2026, 11, 12), D(2026, 11, 14), D(2026, 11, 15), D(2026, 11, 16)):
            self.assertLessEqual(self.day_requests(day, 30, False), 8, day)   # 30 dəqiqədən bir: pəncərə başına bir tur
            self.assertLessEqual(self.day_requests(day, 10, True), 8, day)    # 10 dəqiqədən bir, bütün açarlar done-da
        self.assertEqual(self.day_requests(D(2026, 11, 12), 30, False), 3)    # adi gün: DİM, ASAN, polis
        self.assertEqual(self.day_requests(D(2026, 11, 16), 30, False), 6)    # bazar ertəsi: DİM 2, ASAN, müraciət 2, polis


class SinaqTest(unittest.TestCase):
    def test_sample_run_with_saved_pages(self):
        fake = Fake(pages())
        md = g.sinaq(ROOT, at(2026, 11, 12, 10, 5), fake)
        self.assertTrue(all(isinstance(line, str) for line in md))
        doc = "\n".join(md)
        for part in ("## 1. DİM təqvimi", "## 2. Səyyar ASAN xidmət", "## 3. «ASAN müraciət»", "## 4. Polisin gündəlik icmalı",
                     "### Peşəkar mühasib sertifikatı imtahanına qeydiyyat (I mərhələ) noyabrın 12-də başa çatır",
                     "### Səyyar ASAN xidmət avtobusu noyabrın 13-dən Ağdam rayonunda olacaq",
                     "### Ötən həftə «ASAN müraciət» vasitəsilə 108 problem göndərilib, 67-si Bakıya aiddir",
                     "### Noyabrın 10-da polis 34 cinayətin açılmasını təmin edib",
                     "### Noyabrın 4-də polis 64 cinayətin açılmasını təmin edib",
                     "✅ Dərc olunardı", "⏭ Dərc olunmazdı:", "## Mənbələrə çıxış"):
            self.assertIn(part, doc)
        self.assertLessEqual(len(fake.calls), 10)
        self.assertEqual(len(fake.calls), len(set(fake.calls)))   # hər ünvana bir sorğu

    def test_sample_run_survives_dead_network(self):
        for table in ({}, {url: b"\xff\xfe\x00zibil" for url in pages()}):
            md = g.sinaq(ROOT, at(2026, 11, 12, 10, 5), Fake(table))
            self.assertIn("## Mənbələrə çıxış (bu sınaqda)", md)
            self.assertNotIn("✅ Dərc olunardı", "\n".join(md))

    def test_cli(self):
        out = io.StringIO()
        with patch.object(g, "_default_fetch", lambda: Fake(pages())), contextlib.redirect_stdout(out):
            code = g.main(["--sinaq", "--root", str(ROOT), "--now", "2026-11-12T10:05+04:00"])
        self.assertEqual(code, 0)
        self.assertIn("## Gündəlik həyat: öz xəbərlər (12.11.2026 10:05, Bakı vaxtı)", out.getvalue())
        self.assertIn("`seyyar-asan-2026-11-13` (10:00): Səyyar ASAN xidmət avtobusu noyabrın 13-dən Ağdam rayonunda olacaq — ✅",
                      out.getvalue())


if __name__ == "__main__":
    unittest.main()
