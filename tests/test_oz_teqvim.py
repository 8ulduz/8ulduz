"""Təqvim xəbərləri (oz_teqvim.py, faza 1): cədvəllər, iş günləri, bayram istirahəti, geri sayım, həftənin icmalı.
Şəbəkə yoxdur. Real məlumat: tests/fixtures/oz_teqvim/data/futbol/ — main-in 2026-11-10 tarixli fayllarından kəsiklər."""
import contextlib
import datetime
import io
import json
import pathlib
import re
import tempfile
import unittest
from unittest.mock import patch

import oz_teqvim as t
import oz_xeber as ox

ROOT = pathlib.Path(__file__).resolve().parent.parent
FIX = ROOT / "tests" / "fixtures" / "oz_teqvim"
BAKU = t.BAKU
D = datetime.date


def at(y, m, d, hh=8, mm=30):
    return datetime.datetime(y, m, d, hh, mm, tzinfo=BAKU)


def days(start, end):
    d = start
    while d <= end:
        yield d
        d += t.DAY


def write(root, name, doc):
    path = pathlib.Path(root) / "data" / "futbol"
    path.mkdir(parents=True, exist_ok=True)
    (path / f"{name}.json").write_text(json.dumps(doc, ensure_ascii=False), encoding="utf-8")


class FormatTest(unittest.TestCase):
    def test_suffixes_and_dates(self):
        self.assertEqual([t._cop(x) for x in ("Elm Günü", "peşə bayramı", "Ümumdünya Tütünsüz Gün", "Həftəsi", "11 noyabr",
                                               "1 iyun", "10 aprel")],
                         ["Elm Günüdür", "peşə bayramıdır", "Ümumdünya Tütünsüz Gündür", "Həftəsidir", "11 noyabrdır",
                          "1 iyundur", "10 apreldir"])
        self.assertEqual([t._join([]), t._join(["A"]), t._join(["A", "B"]), t._join(["A", "B", "C"])], ["", "A", "A və B", "A, B və C"])
        self.assertEqual(t._range(D(2026, 11, 9), D(2026, 11, 15)), "9–15 noyabr")
        self.assertEqual(t._range(D(2026, 11, 30), D(2026, 12, 6)), "30 noyabr – 6 dekabr")
        self.assertEqual(t._range(D(2026, 12, 31), D(2027, 1, 3)), "31 dekabr 2026 – 3 yanvar 2027")
        self.assertEqual(t._days_text([D(2026, 11, 10), D(2026, 11, 9)]), "9 və 10 noyabr")
        self.assertEqual(t._days_text([D(2026, 11, 11), D(2026, 11, 12), D(2026, 11, 13)]), "11, 12 və 13 noyabr")
        self.assertEqual(t._days_text([D(2026, 3, d) for d in range(23, 28)]), "23–27 mart")
        self.assertEqual(t._days_text([D(2026, 12, 31), D(2027, 1, 1)]), "31 dekabr və 1 yanvar")
        self.assertEqual([t._loc("20–22 noyabr"), t._loc("10 aprel")], ["20–22 noyabrda", "10 apreldə"])
        self.assertEqual([t._tur("12"), t._tur("Qrup 2"), t._tur("1/8 final")], ["12-ci tur", "2-ci qrup", "1/8 final"])


class TableTest(unittest.TestCase):
    """2026-cı il ƏƏSMN-in istehsalat təqvimi ilə eynidir (Nazirlər Kabinetinin 362 nömrəli qərarı)."""

    def test_2026_matches_the_official_production_calendar(self):
        year = list(days(D(2026, 1, 1), D(2026, 12, 31)))
        self.assertEqual(sum(1 for d in year if not t.qeyri_is_gunu(d)), 241, "beşgünlük həftədə 241 iş günü")
        holidays = [(d, e["name"]) for d in year for e in t._entries(d)
                    if e["kind"] == "dovlet" and e["off"] and e["name"] != "Ümumxalq Hüzn Günü"]
        self.assertEqual(len(holidays), 19, "iş günü hesab edilməyən 19 bayram günü")
        self.assertEqual(len(holidays) - len({d for d, _ in holidays}), 3, "onlardan 3-ü üst-üstə düşür")
        self.assertEqual(sorted(t.KOCURME), [D(2026, 3, 9), D(2026, 3, 25), D(2026, 3, 26), D(2026, 3, 27), D(2026, 3, 30),
                                             D(2026, 5, 11), D(2026, 5, 29), D(2026, 11, 10)])
        self.assertEqual([t.qeyri_is_gunu(D(2026, 11, d)) for d in range(8, 16)], [True, True, True, False, False, False, True, True],
                         "10 noyabr da istirahətdir (Google-un təqvimi bunu səhv verir)")
        self.assertTrue(t.qeyri_is_gunu(at(2026, 11, 10, 9, 0)), "datetime da qəbul olunur")
        self.assertFalse(t.qeyri_is_gunu(D(2026, 3, 31)))
        self.assertTrue(t.qeyri_is_gunu(D(2026, 1, 20)), "Ümumxalq Hüzn Günü iş günü deyil")
        self.assertFalse(t.qeyri_is_gunu(D(2026, 11, 12)), "Konstitusiya Günü iş günüdür")

    def test_unknown_year_is_not_guessed(self):
        self.assertIsNone(t.qeyri_is_gunu(D(2027, 1, 4)))
        self.assertIsNone(t.qeyri_is_gunu(D(2025, 12, 31)))
        self.assertNotIn("Novruz bayramı", t.gun_adlari(D(2027, 3, 21)), "2027-ci ilin Novruz günləri hələ elan olunmayıb")
        self.assertIn("Beynəlxalq Novruz Günü", t.gun_adlari(D(2027, 3, 21)))
        self.assertEqual(t.gun_adlari(D(2026, 3, 21))[:2], ["Novruz bayramı", "Ramazan bayramı"])

    def test_movable_days_follow_their_rule(self):
        self.assertEqual([t._nth_weekday(2026, 11, 3, 3), t._nth_weekday(2027, 11, 3, 3)], [D(2026, 11, 19), D(2027, 11, 18)])
        self.assertEqual([t._nth_weekday(2026, 11, 3, 6), t._nth_weekday(2027, 11, 3, 6)], [D(2026, 11, 15), D(2027, 11, 21)])
        self.assertEqual([t._nth_weekday(2026, 10, 1, 0), t._nth_weekday(2026, 7, 1, 5)], [D(2026, 10, 5), D(2026, 7, 4)])
        self.assertIn("Ümumdünya Fəlsəfə Günü", t.gun_adlari(D(2026, 11, 19)))
        self.assertNotIn("Ümumdünya Fəlsəfə Günü", t.gun_adlari(D(2026, 11, 21)), "UN səhifəsinin köhnə tarixi deyil")
        self.assertIn("Yol-Nəqliyyat Hadisələri Qurbanlarını Anma Ümumdünya Günü", t.gun_adlari(D(2026, 11, 15)))

    def test_names_of_the_day(self):
        self.assertEqual(t.gun_adlari(D(2026, 11, 10)), ["Sülh və İnkişaf Naminə Ümumdünya Elm Günü"])
        self.assertEqual(t.gun_adlari(D(2026, 11, 9)), ["Dövlət Bayrağı Günü", "Beynəlxalq Elm və Sülh Həftəsi"])
        self.assertEqual(t.gun_adlari(D(2026, 11, 13)), [], "həftənin ortası ayrıca ad deyil")
        self.assertEqual(t.gun_adlari(D(2026, 11, 6)), ["Azərbaycan Televiziyası və Radiosu Günü", "Bakı metropoliteni işçilərinin peşə bayramı",
                                                        "Müharibə və Silahlı Münaqişələrdə Ətraf Mühitin İstismarının Qarşısının Alınması Beynəlxalq Günü"])
        self.assertEqual(t.gun_adlari(D(2026, 9, 29))[0], "Turizm İşçiləri Günü", "2022-ci ildən 27 sentyabr deyil, 29 sentyabr")

    def test_tables_are_clean(self):
        names = [n for _, _, n, _, _ in t.DOVLET] + [n for _, _, n, _ in t.PESE] + [n for _, _, n, _ in t.BMT]
        names += [n for *_, n, _ in t.BMT_HEFTE]
        for name in names:
            self.assertNotRegex(ox._low(name), r"prezident|əliyev|birinci xanım|vitse", name)
        self.assertFalse(any(d == 8 and m == 3 for m, d, *_ in t.BMT), "8 Mart dövlət bayramıdır, BMT-də təkrarlanmır")
        for year in (2026, 2027, 2028):
            for d in days(D(year, 1, 1), D(year, 12, 31)):
                item, why = t.gun_item(d)
                if item:
                    self.assertLessEqual(len(item["title"]), t.TITLE_MAX, item["title"])
                    self.assertFalse(item["title"].endswith("."), item["title"])
                    self.assertTrue(item["lead"].endswith("."), item["lead"])
                    if not item["worth"]:
                        self.assertTrue(item["why"])
                else:
                    self.assertTrue(why)


class GunItemTest(unittest.TestCase):
    def test_un_day(self):
        item, _ = t.gun_item(D(2026, 11, 10))
        self.assertEqual(item["title"], "Bu gün Sülh və İnkişaf Naminə Ümumdünya Elm Günüdür")
        self.assertEqual(item["lead"], "BMT-nin beynəlxalq günlər siyahısına görə, 10 noyabr Sülh və İnkişaf Naminə Ümumdünya Elm Günüdür "
                                       "(UNESCO, 31 C/Resolution 20).")
        self.assertEqual(item["body"], ["9–15 noyabr BMT-nin siyahısında Beynəlxalq Elm və Sülh Həftəsidir."])
        self.assertEqual((item["key"], item["slot"], item["topic"], item["worth"]), ("gun-2026-11-10", "07:45", "təqvim", True))
        self.assertEqual((item["credit"], item["link"]), ("Birləşmiş Millətlər Təşkilatı", t.BMT_URL))

    def test_professional_day_with_e_qanun_link(self):
        item, _ = t.gun_item(D(2026, 11, 22))
        self.assertEqual(item["title"], "Bu gün Azərbaycanda ədliyyə işçilərinin peşə bayramıdır")
        self.assertEqual(item["lead"], "22 noyabr Azərbaycanda ədliyyə işçilərinin peşə bayramı kimi qeyd olunur.")
        self.assertEqual((item["credit"], item["link"]), ("e-qanun.az", "https://e-qanun.az/framework/387"))
        item, _ = t.gun_item(D(2026, 11, 6))
        self.assertEqual(item["title"], "Bu gün Azərbaycan Televiziyası və Radiosu Günüdür")
        self.assertEqual(item["lead"], "6 noyabr Azərbaycan Televiziyası və Radiosu Günü kimi qeyd olunur. "
                                       "Bu gün həm də Bakı metropoliteni işçilərinin peşə bayramıdır.")
        self.assertTrue(item["body"][0].startswith("BMT-nin beynəlxalq günlər siyahısına görə, bu gün həm də Müharibə"))

    def test_state_holiday_only_is_not_published_but_other_days_are(self):
        item, why = t.gun_item(D(2026, 11, 12))
        self.assertEqual(item["title"], "Bu gün Konstitusiya Günüdür")
        self.assertFalse(item["worth"])
        self.assertIn("«Bu gün tarixdə»", why)
        item, _ = t.gun_item(D(2026, 11, 9))
        self.assertTrue(item["worth"], "BMT həftəsi də başlayır")
        self.assertEqual(item["title"], "Bu gün Beynəlxalq Elm və Sülh Həftəsi başlayır")
        self.assertTrue(item["lead"].endswith("Azərbaycanda bu gün Dövlət Bayrağı Günüdür."))
        item, _ = t.gun_item(D(2026, 9, 20))
        self.assertEqual(item["title"], "Bu gün Azərbaycanda Neftçilər Günüdür")
        self.assertIn("Bu gün həm də Dövlət Suverenliyi Günüdür.", item["lead"])

    def test_mourning_day_and_empty_day(self):
        item, why = t.gun_item(D(2026, 9, 27))
        self.assertFalse(item["worth"], "Anım Günü: turizm günü dərc olunmur")
        self.assertIn("anım günü", why)
        self.assertIsNone(t.gun_item(D(2026, 11, 13))[0])
        self.assertIsNone(t.gun_item(D(2026, 11, 11))[0])

    def test_novruz_only_in_announced_year(self):
        item26, item27 = t.gun_item(D(2026, 3, 21))[0], t.gun_item(D(2027, 3, 21))[0]
        lead26, lead27 = item26["lead"], item27["lead"]
        self.assertEqual(item26["title"], "Bu gün Ümumdünya Poeziya Günüdür", "BMT-nin Novruz günü bayramın təkrarıdır")
        self.assertNotIn("Beynəlxalq Novruz Günü", " ".join([lead26, *item26["body"]]))
        self.assertEqual(item27["title"], "Bu gün Beynəlxalq Novruz Günüdür", "2027-ci ilin bayram günləri hələ elan olunmayıb")
        self.assertIn("Azərbaycanda bu gün Novruz bayramı və Ramazan bayramıdır.", lead26)
        self.assertNotIn("bayramı", lead27)


class WorkDaysTest(unittest.TestCase):
    def test_short_week(self):
        item, _ = t.is_item(D(2026, 11, 9))
        self.assertEqual(item["title"], "Bu həftə 3 gün işləyirik: 9 və 10 noyabr iş günü deyil")
        self.assertEqual(item["lead"], "Əmək və Əhalinin Sosial Müdafiəsi Nazirliyinin təsdiq etdiyi 2026-cı ilin istehsalat təqviminə görə, "
                                       "bu həftə beşgünlük iş həftəsində 11, 12 və 13 noyabr iş günləridir.")
        self.assertEqual(item["body"], ["9 noyabr Dövlət Bayrağı Günüdür.",
                                        "10 noyabr istirahət günüdür: 8 noyabr – Zəfər Günü bazar gününə düşüb, 9 noyabr isə Dövlət Bayrağı Günüdür."])
        self.assertEqual((item["key"], item["slot"], item["worth"], item["link"]),
                         ("is-gunleri-2026-11-09", "08:00", True, t.TEQVIM[2026]))
        item, _ = t.is_item(D(2026, 5, 25))
        self.assertEqual(item["title"], "Bu həftə 2 gün işləyirik: 27, 28 və 29 may iş günü deyil")
        item, _ = t.is_item(D(2026, 3, 23))
        self.assertEqual(item["title"], "Bu həftə iş günü yoxdur: 23–27 mart istirahət günləridir")
        self.assertTrue(item["lead"].endswith("Növbəti iş günü 31 martdır."))

    def test_normal_week_other_days_and_unknown_year(self):
        item, why = t.is_item(D(2026, 11, 16))
        self.assertFalse(item["worth"])
        self.assertIn("adi beşgünlük", why)
        self.assertEqual(t.is_item(D(2026, 11, 10)), (None, "bazar ertəsi deyil"))
        item, why = t.is_item(D(2026, 12, 28))
        self.assertIsNone(item, "1 yanvar 2027 bilinmir: təxmin edilmir")
        self.assertIn("2027-ci il üçün rəsmi istehsalat təqvimi hələ yoxdur", why)

    def test_day_before_a_holiday_break(self):
        item, _ = t.istirahet_item(D(2026, 11, 6))
        self.assertEqual(item["title"], "7–10 noyabr 4 gün istirahətdir, işə 11 noyabrda çıxılacaq")
        self.assertTrue(item["lead"].endswith("beşgünlük iş həftəsində 7–10 noyabr istirahət günləridir. Növbəti iş günü 11 noyabrdır."))
        self.assertEqual(item["body"][:2], ["8 noyabr Zəfər Günüdür.", "9 noyabr Dövlət Bayrağı Günüdür."])
        self.assertEqual(item["key"], "istirahet-2026-11-07")
        item, _ = t.istirahet_item(D(2026, 3, 19))
        self.assertEqual(item["title"], "20–30 mart 11 gün istirahətdir, işə 31 martda çıxılacaq")
        self.assertIn("20 və 21 mart Novruz bayramı və Ramazan bayramıdır.", item["body"])
        self.assertIsNone(t.istirahet_item(D(2026, 1, 19))[0], "20 yanvar tək gündür: bayram istirahəti deyil")
        self.assertIsNone(t.istirahet_item(D(2026, 11, 5))[0])
        self.assertEqual(t.istirahet_item(D(2026, 11, 7))[1], "bu gün iş günü deyil")
        item, why = t.istirahet_item(D(2026, 12, 30))
        self.assertIsNone(item)
        self.assertIn("2027-ci il", why)


class GamesCountdownTest(unittest.TestCase):
    def test_milestones_only(self):
        ist, la = t.OYUNLAR
        item, _ = t.oyun_item(ist, D(2027, 3, 8))
        self.assertEqual(item["title"], "IV Avropa Oyunlarının açılışına 100 gün qalıb")
        self.assertEqual(item["lead"], "IV Avropa Oyunları 16–27 iyun 2027-ci il tarixlərində Türkiyənin İstanbul şəhərində keçiriləcək. "
                                       "Açılışa 100 gün qalıb.")
        self.assertEqual((item["key"], item["topic"], item["credit"]), ("oyun-istanbul-2027-100", "idman", "Avropa Olimpiya Komitələri"))
        self.assertEqual(t.oyun_item(ist, D(2027, 6, 15))[0]["title"], "IV Avropa Oyunları sabah İstanbulda başlayır")
        item, _ = t.oyun_item(ist, D(2027, 6, 16))
        self.assertEqual(item["title"], "IV Avropa Oyunları bu gün İstanbulda başlayır")
        self.assertIn("keçirilir.", item["lead"])
        self.assertEqual(t.oyun_item(ist, D(2026, 11, 10)), (None, "mərhələ günü deyil: açılışa 218 gün qalıb"))
        self.assertIsNone(t.oyun_item(ist, D(2027, 6, 17))[0])
        item, _ = t.oyun_item(la, D(2028, 4, 5))
        self.assertEqual(item["title"], "XXXIV Yay Olimpiya Oyunlarının açılışına 100 gün qalıb")
        self.assertIn("ABŞ-ın Los-Anceles şəhərində", item["lead"])
        self.assertEqual(t.oyun_item(la, D(2028, 7, 13))[0]["title"], "XXXIV Yay Olimpiya Oyunları sabah Los-Ancelesdə başlayır")
        self.assertEqual(t._next_milestone(ist, D(2026, 11, 11)), D(2027, 3, 8))
        published = [d for d in days(D(2026, 11, 10), D(2028, 8, 1)) for g in t.OYUNLAR if t.oyun_item(g, d)[0]]
        self.assertEqual(len(published), 12, "hər oyun üçün 6 gün")


class WeekAheadTest(unittest.TestCase):
    """Real kəsiklər: Premyer Liqa 11–13-cü turlar, I Liqa 7–9, Kubok, Millətlər Liqası D, «Sabah» Çempionlar Liqasında."""

    def test_week_with_the_national_team(self):
        item, _ = t.hefte_item(FIX, at(2026, 11, 9))
        self.assertEqual(item["title"], "Bu həftə nə gözlənilir: Lixtenşteyn – Azərbaycan oyunu və Konstitusiya Günü")
        self.assertEqual(item["lead"], "Azərbaycan millisi 13 noyabr saat 23:45-də səfərdə Lixtenşteyn ilə oynayacaq (Millətlər Liqası D, 2-ci qrup). "
                                       "Premyer Liqada bu həftə oyun yoxdur: 12-ci tur 20 noyabrda «İmişli» – «Zirə» oyunu ilə başlayacaq. "
                                       "9 noyabr Dövlət Bayrağı Günü, 12 noyabr isə Konstitusiya Günüdür. 9 və 10 noyabr iş günü deyil.")
        self.assertIn("13 noyabr (cümə): Millətlər Liqası D, 2-ci qrup — Lixtenşteyn – Azərbaycan, 23:45, Rheinpark Stadion", item["body"])
        self.assertIn("10 noyabr (çərşənbə axşamı): istirahət günü (iş günü deyil); Sülh və İnkişaf Naminə Ümumdünya Elm Günü", item["body"])
        self.assertEqual((item["key"], item["slot"], item["topic"], item["list"], item["worth"]), ("hefte-2026-11-09", "08:30", "icmal", True, True))

    def test_full_round_and_lower_league(self):
        item, _ = t.hefte_item(FIX, at(2026, 11, 16))
        self.assertEqual(item["title"], "Bu həftə nə gözlənilir: Premyer Liqanın 12-ci turu və Milli Dirçəliş Günü")
        self.assertTrue(item["lead"].startswith("Premyer Liqanın 12-ci turu 20–22 noyabrda keçiriləcək. 17 noyabr Milli Dirçəliş Günüdür."))
        self.assertIn("20 noyabr (cümə): Premyer Liqa, 12-ci tur — «İmişli» – «Zirə», 14:30; «Sumqayıt» – «Sabah», 19:00", item["body"])
        self.assertIn("19 noyabr (cümə axşamı): I Liqa, 8-ci tur — «MOİK» – «Səbail», 14:00; «Xankəndi» – «Karvan-Yevlax», 14:00; "
                      "«Mingəçevir» – «Baku Sportinq», 14:30", item["body"])
        self.assertEqual(item["credit"].split(", ")[0], "Peşəkar Futbol Liqası")

    def test_placeholder_schedule_is_not_written_as_a_date(self):
        item, _ = t.hefte_item(FIX, at(2026, 11, 23))
        self.assertEqual(item["title"], "Bu həftə nə gözlənilir: «Sabah» – «Barcelona» oyunu və Premyer Liqanın 13-cü turu")
        self.assertEqual(item["lead"], "«Sabah» 25 noyabr saat 21:45-də Çempionlar Liqası oyununda doğma meydanda «Barcelona» ilə qarşılaşacaq. "
                                       "Premyer Liqanın 13-cü turunun oyun cədvəli hələ açıqlanmayıb.")
        self.assertNotIn("27 noyabrda", item["lead"], "pfl.az-ın 00:00 tarixi turun şərti tarixidir")
        self.assertTrue(any(b.startswith("Premyer Liqa, 13-cü tur — «") and b.endswith(
            "oyun cədvəli hələ açıqlanmayıb (pfl.az-da turun tarixi 27 noyabr)") for b in item["body"]), item["body"])
        item, _ = t.hefte_item(FIX, at(2026, 11, 30))
        self.assertIn("Azərbaycan Kubokunun 1/8 final oyunlarının cədvəli hələ açıqlanmayıb.", item["lead"])
        self.assertFalse(any("12:00" in b for b in item["body"]), "stadionsuz 12:00 da yer tutucudur")

    def test_rescheduled_games_and_postponed_game(self):
        item, _ = t.hefte_item(FIX, at(2026, 12, 14))
        self.assertIn("Premyer Liqanın 2-ci turunun 2 oyunu bu həftə keçiriləcək.", item["lead"])
        self.assertTrue(item["title"].startswith("Bu həftə nə gözlənilir: Premyer Liqa oyunları"), item["title"])
        with tempfile.TemporaryDirectory() as tmp:
            teams = {"neftci": {"name": "Neftçi"}, "sabah": {"name": "Sabah"}, "zire": {"name": "Zirə"}, "kepez": {"name": "Kəpəz"}}
            write(tmp, "premyer-liqa", {"source": "pfl.az", "teams": teams, "games": [
                {"home": "neftci", "away": "sabah", "date": "2026-11-16T14:00+04:00", "played": False, "stadium": "A", "round": "12"},
                {"home": "zire", "away": "kepez", "date": "2026-11-18T19:00+04:00", "played": False, "stadium": "B", "round": "12"}]})
            item, _ = t.hefte_item(tmp, at(2026, 11, 16, 15, 0))
            self.assertIn("Premyer Liqanın 12-ci turunun 1 oyunu bu həftə keçiriləcək.", item["lead"],
                          "bu günün keçmiş, oynanmamış oyunu yazılmır")
            self.assertFalse(any("«Neftçi»" in b for b in item["body"]))

    def test_missing_data_and_empty_week(self):
        with tempfile.TemporaryDirectory() as tmp:
            item, _ = t.hefte_item(tmp, at(2026, 11, 9))
            self.assertEqual(item["title"], "Bu həftə nə gözlənilir: Konstitusiya Günü və Dövlət Bayrağı Günü")
            self.assertTrue(item["worth"])
            item, why = t.hefte_item(tmp, at(2026, 12, 21))
            self.assertFalse(item["worth"])
            self.assertIn("futbol oyunu və bayram yoxdur", why)
            write(tmp, "premyer-liqa", {"games": "pozuq"})
            (pathlib.Path(tmp) / "data" / "futbol" / "ml-d.json").write_text("{pozuq", encoding="utf-8")
            self.assertTrue(t.hefte_item(tmp, at(2026, 11, 9))[0]["worth"], "pozuq fayl xəbəri sındırmır")
        self.assertEqual(t.hefte_item(FIX, at(2026, 11, 10)), (None, "bazar ertəsi deyil"))


class ItemsAndSinaqTest(unittest.TestCase):
    def test_items_of_a_day(self):
        monday = t.items(FIX, at(2026, 11, 9, 8, 0))
        self.assertEqual([i["kind"] for i in monday], ["gun", "is-gunleri", "hefte"])
        self.assertEqual(monday, t.items(FIX, at(2026, 11, 9, 8, 0)), "eyni məlumat və vaxt: eyni nəticə")
        self.assertEqual([i["key"] for i in t.items(FIX, at(2026, 11, 10, 9, 0))], ["gun-2026-11-10"])
        friday = t.items(FIX, at(2026, 11, 6, 9, 0))
        self.assertEqual([i["kind"] for i in friday], ["gun", "istirahet"])
        required = {"kind", "key", "title", "lead", "body", "credit", "link", "topic", "slot", "worth"}
        for item in monday + friday:
            self.assertTrue(required <= set(item), item.keys())
            self.assertRegex(item["slot"], r"^\d\d:\d\d$")
            self.assertIn(item["topic"], ("idman", "iqtisadiyyat", "təqvim", "kosmos", "icmal"))
            self.assertLessEqual(len(item["title"]), t.TITLE_MAX)
            self.assertNotRegex(item["title"] + item["lead"], r"[А-Яа-яЁё]")
        self.assertIn("oyun-istanbul-2027-100", [i["key"] for i in t.items(FIX, at(2027, 3, 8, 9, 0)) if i["worth"]])

    def test_leadership_is_never_published(self):
        with patch.object(ox, "needs_owner", return_value=True):
            rows = t.items(FIX, at(2026, 11, 9, 8, 0))
        self.assertTrue(rows and all(not i["worth"] and "rəhbərliyin" in i["why"] for i in rows))

    def test_sinaq_and_cli(self):
        now = at(2026, 11, 10, 9, 0)
        md = "\n".join(t.sinaq(FIX, now))
        for text in ("## 1. «Bu gün nə günüdür»", "### Bu gün Sülh və İnkişaf Naminə Ümumdünya Elm Günüdür",
                     "### Bu həftə 3 gün işləyirik: 9 və 10 noyabr iş günü deyil", "— ən son real hal",
                     "### 7–10 noyabr 4 gün istirahətdir, işə 11 noyabrda çıxılacaq",
                     "⏭ Dərc olunmazdı: 2027-ci il üçün rəsmi istehsalat təqvimi hələ yoxdur",
                     "### IV Avropa Oyunlarının açılışına 100 gün qalıb", "### Bu həftə nə gözlənilir: Lixtenşteyn – Azərbaycan oyunu",
                     "✅ Dərc olunardı", "⏭ Dərc olunmazdı: yalnız dövlət bayramıdır"):
            self.assertIn(text, md)
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            self.assertEqual(t.main(["--sinaq", "--root", str(FIX), "--now", "2026-11-10T09:00+04:00"]), 0)
        self.assertEqual(out.getvalue().strip(), md.strip())
        self.assertFalse(re.search(r"https?://(?!www\.un\.org|e-qanun\.az|sosial\.gov\.az|sporteurope\.org|la28\.org|pfl\.az|en\.wikipedia\.org|www\.openligadb\.de)",
                                   md), "yalnız mənbə keçidləri")


class NotOnTheSiteTest(unittest.TestCase):
    def test_site_pipeline_does_not_use_it(self):
        self.assertNotIn("oz_teqvim", (ROOT / "updater.py").read_text(encoding="utf-8"))
        self.assertNotIn("oz_teqvim", (ROOT / ".github" / "scripts" / "pipeline.sh").read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
