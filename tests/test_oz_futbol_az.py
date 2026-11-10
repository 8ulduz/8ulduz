"""Öz futbol xəbərləri (oz_futbol_az.py): Premyer Liqanın turu, tura baxış və bombardirlər, I/II Liqa, kubok, milli, avrokubok.
Şəbəkə yoxdur: pfl.az saxta cavabla əvəz olunur. Real məlumat: tests/fixtures/oz_futbol_az — main-in 2026-11-10 tarixli
data/futbol faylları (logolar və uzaq turlar çıxarılıb) və pfl.az-ın həmin günkü /seasons, /bombarders/list cavabları."""
import datetime
import io
import json
import pathlib
import re
import tempfile
import unittest
from contextlib import redirect_stdout
from unittest.mock import patch

import oz_futbol_az as fa

ROOT = pathlib.Path(__file__).resolve().parent.parent
FIX = pathlib.Path(__file__).resolve().parent / "fixtures" / "oz_futbol_az"
PFL = "https://pfl.az/api/v1"


def at(s):
    return datetime.datetime.fromisoformat(s)


def by_key(rows):
    return {r["key"]: r for r in rows}


class FakeFetch:
    """pfl.az-ın saxtası: ünvanın sonu -> cavab. Tanımadığı ünvana şəbəkə xətası verir."""
    def __init__(self, pages):
        self.pages, self.urls = pages, []

    def __call__(self, url, timeout=None, headers=None):
        self.urls.append(url)
        for end, body in self.pages.items():
            if url.endswith(end):
                return body if isinstance(body, bytes) else json.dumps(body).encode("utf-8")
        raise OSError("şəbəkə yoxdur: " + url)


def real_pfl():
    return FakeFetch({"/seasons?project_id=1": (FIX / "pfl" / "seasons.json").read_bytes(),
                      "/bombarders/list?league_id=52": (FIX / "pfl" / "bombarders-list.json").read_bytes()})


# --- Süni liqa: kənar hallar üçün ------------------------------------------------------------------------------

TEAMS = {"neftci": "Neftçi", "sabah": "Sabah", "qarabag": "Qarabağ", "zire": "Zirə"}


def game(rnd, date, home, away, score=None, stadium="Palms Sports Arena"):
    g = {"home": home, "away": away, "date": date, "played": score is not None, "stadium": stadium, "round": str(rnd)}
    if score is not None:
        g["hs"], g["as"] = score
    return g


def rows_for(games, teams=TEAMS):
    """Rəsmi cədvəl kimi: oyun sayı və xal oyunlardan."""
    t = {k: {"team": k, "p": 0, "pts": 0} for k in teams}
    for g in games:
        if g["played"]:
            for k, a, b in ((g["home"], g["hs"], g["as"]), (g["away"], g["as"], g["hs"])):
                t[k]["p"] += 1
                t[k]["pts"] += 3 if a > b else 1 if a == b else 0
    rows = sorted(t.values(), key=lambda r: -r["pts"])
    for i, r in enumerate(rows, 1):
        r["pos"] = i
    return rows


def league(games, rows=None, lid="premyer-liqa", name="Misli Premyer Liqası", short="Premyer Liqa", teams=TEAMS):
    return {"id": lid, "name": name, "short": short, "source": "pfl.az", "key": "2026", "season": "2026-27",
            "teams": {k: {"name": v} for k, v in teams.items()},
            "groups": [{"name": "", "rows": rows_for(games, teams) if rows is None else rows}], "games": games}


def site(tmp, docs):
    """docs: {"premyer-liqa": {...}} -> tmp/data/futbol/premyer-liqa.json."""
    root = pathlib.Path(tmp)
    (root / "data" / "futbol").mkdir(parents=True, exist_ok=True)
    for name, doc in docs.items():
        text = doc if isinstance(doc, str) else json.dumps(doc, ensure_ascii=False)
        (root / "data" / "futbol" / f"{name}.json").write_text(text, encoding="utf-8")
    return root


R1 = [game(1, "2026-11-01T15:00+04:00", "neftci", "sabah", (2, 0)), game(1, "2026-11-01T18:00+04:00", "qarabag", "zire", (1, 1))]
R2 = [game(2, "2026-11-08T15:00+04:00", "sabah", "qarabag", (1, 0)), game(2, "2026-11-08T18:00+04:00", "zire", "neftci", (0, 3))]


class WritingTest(unittest.TestCase):
    def test_case_endings_follow_pronunciation(self):
        self.assertEqual([fa.sx(n, c) for n, c in (
            ("Araz-Naxçıvan", "dat"), ("Şamaxı", "ins"), ("Zirə", "acc"), ("Sabah", "abl"), ("Neftçi", "gen"), ("Kəpəz", "dat"),
            ("Qaradağ L.", "acc"), ("Viking", "dat"), ("Barcelona", "ins"), ("Manchester City", "acc"), ("Slavia Prague", "acc"),
            ("Rheinpark Stadion", "loc"), ("İmişli", "dat"), ("MOİK", "acc"))],
            ["«Araz-Naxçıvan»a", "«Şamaxı»yla", "«Zirə»ni", "«Sabah»dan", "«Neftçi»nin", "«Kəpəz»ə", "«Qaradağ L.»ı", "«Viking»ə",
             "«Barcelona»yla", "«Manchester City»ni", "«Slavia Prague»ı", "«Rheinpark Stadion»da", "«İmişli»yə", "«MOİK»i"])
        self.assertEqual([fa.sx("Lixtenşteyn", "dat", False), fa.sx("Litva", "acc", False), fa.sx("Premyer Liqa", "loc", False),
                          fa.sx("Misli Premyer Liqası", "gen", False), fa.sx("Azərbaycan Kuboku", "acc", False)],
                         ["Lixtenşteynə", "Litvanı", "Premyer Liqada", "Misli Premyer Liqasının", "Azərbaycan Kubokunu"])
        # Mənsubiyyət şəkilçili ad: Liqasında, Gəncləri»nə; xarici ad yox: «Manchester City»yə.
        self.assertEqual([fa.sx("Çempionlar Liqası", "loc", False), fa.sx("Avropa Liqası", "dat", False),
                          fa.sx("Ağstafa Gəncləri", "dat"), fa.sx("Ağstafa Gəncləri", "abl"), fa.sx("Ağstafa Gəncləri", "ins"),
                          fa.sx("Manchester City", "dat"), fa.sx("Neftçi", "loc")],
                         ["Çempionlar Liqasında", "Avropa Liqasına", "«Ağstafa Gəncləri»nə", "«Ağstafa Gəncləri»ndən",
                          "«Ağstafa Gəncləri»ylə", "«Manchester City»yə", "«Neftçi»də"])

    def test_venues_are_written_in_full(self):
        self.assertEqual([fa.venue(v) for v in ("Tovuz şəhər st.", "M.H. Sumqayıt ş. st.", "Bank Respublika A.",
                                                 "T.B. - Respublika st.", "Azersun Arena", "H.Ə. adına İmişli ş. st.")],
                         ["Tovuz şəhər stadionu", "Mehdi Hüseynzadə adına Sumqayıt şəhər stadionu", "Bank Respublika Arena",
                          "Tofiq Bəhramov adına Respublika stadionu", "Azersun Arena", "İmişli şəhər stadionu"])
        self.assertEqual([fa._venue_loc("Yevlax şəhər stadionu"), fa._venue_loc("Azersun Arena"), fa._venue_loc("Palms Sports FM")],
                         ["Yevlax şəhər stadionunda", "Azersun Arenada", ""])

    def test_publish_time_after_a_game(self):
        self.assertEqual(fa._ready_after(at("2026-11-08T17:30+04:00")), at("2026-11-08T19:45+04:00"))
        self.assertEqual(fa._ready_after(at("2026-11-08T21:45+04:00")), at("2026-11-09T00:00+04:00"))
        self.assertEqual(fa._ready_after(at("2026-11-08T23:00+04:00")), at("2026-11-09T09:00+04:00"))
        self.assertEqual(fa._ready_after(at("2026-11-05T00:00+04:00"), 8), at("2026-11-05T08:00+04:00"))
        self.assertEqual([fa._span(at("2026-11-06T18:00+04:00"), at("2026-11-08T17:30+04:00")),
                          fa._span(at("2026-10-30T18:30+04:00"), at("2026-11-02T19:00+04:00"))], ["6–8 noyabr", "30 oktyabr – 2 noyabr"])


class RealPremyerLiqaTest(unittest.TestCase):
    """Real məlumat: 11-ci tur 6–8 noyabr, 12-ci tur 20–22 noyabr, 13-cü turun saatları 00:00."""

    def test_fixture_reads_without_errors(self):
        evs, errors = fa._events(FIX)
        self.assertEqual(errors, [])
        self.assertTrue({"pfl-tur", "pfl-tur-oncesi", "pfl-bombardir", "liqa-tur", "kubok-merhele", "kubok-cutler",
                         "milli-oncesi", "milli-netice", "avro-oncesi", "avro-netice"} <= {e["kind"] for e in evs})

    def test_round_summary_after_the_last_game(self):
        item = by_key(fa.items(FIX, at("2026-11-08T20:00+04:00")))["tur-premyer-liqa-2026-t11"]
        self.assertTrue(item["worth"], item.get("why"))
        self.assertEqual(item["title"], "Premyer Liqada 11-ci tur: «Neftçi» fərqi 3 xala çatdırıb, 6 oyunda 13 qol vurulub")
        self.assertEqual(item["lead"], "Misli Premyer Liqasının 11-ci turu 6–8 noyabrda keçirilib. Lider «Neftçi» «Kəpəz»i 1:0 hesabı "
                                       "ilə məğlub edib və 24 xal toplayıb. «Sabah» və «Turan Tovuz» 21 xal toplayıb. Liderin fərqi "
                                       "1 xaldan 3 xala çatıb. Turun 6 oyununda 13 qol vurulub.")
        self.assertEqual(item["body"], [
            "«Qarabağ» – «Turan Tovuz» – 0:1", "«Neftçi» – «Kəpəz» – 1:0", "«Şəfa» – «Araz-Naxçıvan» – 2:2",
            "«Zirə» – «Qəbələ» – 2:1", "«İmişli» – «Sumqayıt» – 0:0", "«Sabah» – «Şamaxı» – 2:2",
            "Cədvəldə «Turan Tovuz» 4-cü yerdən 3-cü yerə, «Zirə» 6-cı yerdən 5-ci yerə qalxıb; «Qarabağ» 3-cü yerdən 4-cü yerə, "
            "«Kəpəz» 5-ci yerdən 6-cı yerə düşüb.",
            "«Sabah», «Qarabağ», «Kəpəz» və «Sumqayıt» 10 oyun keçirib, digər komandalar isə 11 oyun.",
            "2-ci turun «Sabah» – «Sumqayıt» və «Qarabağ» – «Kəpəz» oyunları 17 dekabrda keçiriləcək."])
        self.assertEqual((item["slot"], item["topic"], item["credit"], item["kind"], item["list"]),
                         ("19:45", "idman", "Peşəkar Futbol Liqası", "pfl-tur", True))

    def test_round_summary_window(self):
        def keys(now):
            return {i["key"] for i in fa.items(FIX, at(now))}
        self.assertNotIn("tur-premyer-liqa-2026-t11", keys("2026-11-08T19:40+04:00"))  # son oyun 17:30-da başlayıb
        self.assertIn("tur-premyer-liqa-2026-t11", keys("2026-11-09T09:00+04:00"))
        self.assertNotIn("tur-premyer-liqa-2026-t11", keys("2026-11-10T08:00+04:00"))  # 36 saat keçib

    def test_preview_the_day_before_with_head_to_head(self):
        item = by_key(fa.items(FIX, at("2026-11-19T12:30+04:00")))["tur-oncesi-premyer-liqa-2026-t12"]
        self.assertTrue(item["worth"], item.get("why"))
        self.assertEqual(item["title"], "Premyer Liqada 12-ci tur 20 noyabrda başlayır: lider «Neftçi» sonuncu «Araz-Naxçıvan»a qonaq gedəcək")
        self.assertEqual(item["lead"], "Misli Premyer Liqasının 12-ci turu 20–22 noyabrda keçiriləcək. Tur 20 noyabrda saat 14:30-da "
                                       "Yevlax şəhər stadionunda «İmişli» – «Zirə» oyunu ilə başlayacaq. 24 xalla lider olan «Neftçi» "
                                       "22 noyabrda saat 14:30-da Şamaxı şəhər stadionunda «Araz-Naxçıvan»a qonaq olacaq. Komandalar "
                                       "Premyer Liqada 2024-25 mövsümündən bəri 8 dəfə qarşılaşıb: «Neftçi» 3, «Araz-Naxçıvan» 2 dəfə "
                                       "qalib gəlib, 3 oyun heç-heçə bitib.")
        self.assertEqual(len(item["body"]), 6)
        # Kubok oyunları sayılmır: «son qarşılaşma» Premyer Liqadakıdır (1/8 finaldan sonra «Sumqayıt» – «Qarabağ» kimi).
        self.assertEqual(item["body"][0], "20 noyabr, 14:30, Yevlax şəhər stadionu: «İmişli» (8-ci yer, 11 xal) – «Zirə» (5-ci yer, "
                                          "19 xal). Premyer Liqadakı son qarşılaşma: 22 avqust 2026, «Zirə» – «İmişli» – 3:1.")
        # Bu mövsümkü oyunları sonraya salınıb: son qarşılaşma keçən mövsümdəndir.
        self.assertEqual(item["body"][1], "20 noyabr, 19:00, Mehdi Hüseynzadə adına Sumqayıt şəhər stadionu: «Sumqayıt» (9-cu yer, "
                                          "10 xal) – «Sabah» (2-ci yer, 21 xal). Premyer Liqadakı son qarşılaşma: 19 mart 2026, "
                                          "«Sabah» – «Sumqayıt» – 3:1.")
        self.assertEqual(item["slot"], "12:00")
        self.assertNotIn("tur-oncesi-premyer-liqa-2026-t12", {i["key"] for i in fa.items(FIX, at("2026-11-20T14:30+04:00"))})

    def test_placeholder_kick_off_times_give_no_preview(self):
        item = by_key(fa.items(FIX, at("2026-11-26T12:30+04:00")))["tur-oncesi-premyer-liqa-2026-t13"]
        self.assertFalse(item["worth"])
        self.assertIn("00:00", item["why"])

    def test_scorers_come_from_pfl_sorted_by_goals(self):
        fetch = real_pfl()
        item = by_key(fa.items(FIX, at("2026-11-09T10:30+04:00"), fetch))["bombardir-premyer-liqa-2026-t11"]
        self.assertTrue(item["worth"], item.get("why"))
        self.assertEqual(item["title"], "Premyer Liqanın bombardirlər yarışında «Neftçi»nin futbolçusu Breno Almeyda 9 qolla öndədir")
        self.assertEqual(item["lead"], "Misli Premyer Liqasının 11-ci turundan sonra bombardirlər siyahısına «Neftçi»nin futbolçusu "
                                       "Breno Almeyda 9 qolla başçılıq edir. «Sabah»dan Coy-Lens Mikels 7, «Araz-Naxçıvan»dan "
                                       "Ağadadaş Salyanskiy 5 qol vurub.")
        self.assertEqual(item["body"], [
            "Breno Almeyda («Neftçi») – 9 qol", "Coy-Lens Mikels («Sabah») – 7 qol", "Ağadadaş Salyanskiy («Araz-Naxçıvan») – 5 qol",
            "Aleksey Kaşuk («Qarabağ») – 4 qol", "Davit Volkov («Zirə») – 4 qol", "Joarlem Santos («Turan Tovuz») – 4 qol",
            "Qustavo Klisman («Neftçi») – 4 qol", "Ronaldo Vaskez («Sumqayıt») – 4 qol"])
        self.assertEqual(fetch.urls, [PFL + "/seasons?project_id=1", PFL + "/bombarders/list?league_id=52"])
        self.assertEqual(item["slot"], "10:00")

    def test_scorers_need_the_fetch_and_a_quiet_league(self):
        item = by_key(fa.items(FIX, at("2026-11-09T10:30+04:00")))["bombardir-premyer-liqa-2026-t11"]
        self.assertFalse(item["worth"])
        self.assertIn("sorğu", item["why"])
        broken = by_key(fa.items(FIX, at("2026-11-09T10:30+04:00"), FakeFetch({})))["bombardir-premyer-liqa-2026-t11"]
        self.assertFalse(broken["worth"])
        self.assertIn("pfl.az alınmadı", broken["why"])

    def test_paged_scorer_list_falls_back_to_the_full_list(self):
        page = json.loads((FIX / "pfl" / "bombarders-list.json").read_text(encoding="utf-8"))
        page["data"]["last_page"], page["data"]["total"] = 2, 25
        full = {"data": page["data"]["data"] + [{"player": {"name": "Yeni", "surname": "Bombardir"}, "club": {"title": "Zirə"},
                                                  "value": "12"}]}
        fetch = FakeFetch({"/seasons?project_id=1": (FIX / "pfl" / "seasons.json").read_bytes(),
                           "/bombarders/list?league_id=52": page, "/bombarders?league_id=52": full})
        rows = fa.pfl_scorers(fetch, "2026-27")
        self.assertEqual([(r["name"], r["goals"]) for r in rows[:3]], [("Yeni Bombardir", 12), ("Breno Almeyda", 9), ("Coy-Lens Mikels", 7)])
        self.assertEqual(fetch.urls[-1], PFL + "/bombarders?league_id=52")
        self.assertEqual(len(fetch.urls), 3)
        with self.assertRaises(ValueError):  # başqa mövsümün liqası
            fa.pfl_scorers(fetch, "2027-28")

    def test_scorer_sort_is_numeric_with_a_stable_tie_rule(self):
        rows = [{"player": {"name": n, "surname": s}, "club": {"title": c}, "value": v} for n, s, c, v in (
            ("Ruslan", "Quliyev", "Şirvan", "12"), ("Elçin", "Qasımov", "Ağstafa Gəncləri", "17"), ("Çingiz", "Məmmədov", "Şirvan", "3"),
            ("Amil", "Yunanov", "Şirvan", "9"), ("Bəxtiyar", "Həsənov", "Difai", "3"), ("Boş", "Dəyər", "Difai", None))]
        got, more = fa.scorer_rows({"data": {"data": rows, "last_page": 1, "total": 6}})
        self.assertFalse(more)
        self.assertEqual([(r["name"], r["goals"]) for r in fa.sorted_scorers(got)],
                         [("Elçin Qasımov", 17), ("Ruslan Quliyev", 12), ("Amil Yunanov", 9), ("Bəxtiyar Həsənov", 3),
                          ("Çingiz Məmmədov", 3)])
        self.assertEqual(fa.scorer_rows({"data": rows[:2]})[0][0]["goals"], 12)  # /bombarders: səhifəsiz siyahı


class RealLowerLeaguesAndCupTest(unittest.TestCase):
    def test_ii_liqa_round_summary(self):
        item = by_key(fa.items(FIX, at("2026-11-03T18:00+04:00")))["tur-ii-liqa-2026-t9"]
        self.assertTrue(item["worth"], item.get("why"))
        self.assertEqual(item["title"], "II Liqada 9-cu tur: «Ağstafa Gəncləri» «Şəki»ni 11:1 hesabı ilə məğlub edib")
        self.assertEqual(item["lead"], "II Liqanın 9-cu turu 1–3 noyabrda keçirilib. Lider «Qaradağ L.» səfərdə «Marafon»u 1:0 hesabı "
                                       "ilə məğlub edib və 24 xal toplayıb. «Şirvan» 22 xalla ikinci yerdədir. Liderin fərqi 1 xaldan "
                                       "2 xala çatıb. Turun 6 oyununda 25 qol vurulub.")
        self.assertEqual(item["body"][0], "«Ağstafa Gəncləri» – «Şəki» – 11:1")
        self.assertEqual((len(item["body"]), item["kind"]), (6, "liqa-tur"))

    def test_incomplete_round_gives_no_item(self):
        item = by_key(fa.items(FIX, at("2026-11-10T18:00+04:00")))["tur-ii-liqa-2026-t10"]
        self.assertFalse(item["worth"])
        self.assertEqual(item["why"], "tur bitməyib: «Difai» – «Zəngəzur», «Şirvan» – «Marafon» və «Şəki» – «Dinamo» oyunlarının "
                                      "nəticəsi yoxdur")

    def test_round_counted_by_the_table_but_missing_in_games(self):
        item = by_key(fa.items(FIX, at("2026-11-05T18:00+04:00")))["tur-i-liqa-2026-t7"]
        self.assertFalse(item["worth"])
        self.assertEqual(item["why"], "tur bitməyib: «Mingəçevir» – «Şahdağ Qusar» oyununun nəticəsi yoxdur (rəsmi cədvəl isə bu "
                                      "oyunu sayıb)")

    def test_points_tie_at_the_top(self):
        item = by_key(fa.items(FIX, at("2026-10-22T18:00+04:00")))["tur-i-liqa-2026-t6"]
        self.assertTrue(item["worth"], item.get("why"))
        self.assertEqual(item["title"], "I Liqada 6-cı tur: «Gəncəbasar» «Zaqatala»nı 7:0 hesabı ilə məğlub edib")
        self.assertEqual(item["lead"], "I Liqanın 6-cı turu 21–22 oktyabrda keçirilib. «Gəncəbasar» və «Şahdağ Qusar» 15 xalla "
                                       "cədvəlin başındadır. Turun 5 oyununda 20 qol vurulub.")

    def test_cup_stage_results(self):
        item = by_key(fa.items(FIX, at("2026-10-29T17:00+04:00")))["kubok-2026-ii-tesnifat-yekun"]
        self.assertTrue(item["worth"], item.get("why"))
        self.assertEqual(item["title"], "Azərbaycan Kubokunun II təsnifat mərhələsi: «Sumqayıt» səfərdə «Kür-Araz»ı 11:0 hesabı ilə "
                                        "məğlub edib")
        self.assertEqual(item["lead"], "Azərbaycan Kubokunun II təsnifat mərhələsi 27–29 oktyabrda keçirilib. Mərhələnin 12 oyununda "
                                       "71 qol vurulub.")
        self.assertIn("«Səbail» – «Zirə» – 2:2 (növbəti mərhələyə «Zirə» keçib)", item["body"])
        self.assertEqual(len(item["body"]), 12)

    def test_cup_pairs_without_the_placeholder_date(self):
        item = by_key(fa.items(FIX, at("2026-11-03T12:00+04:00")))["kubok-2026-1-8-final-cutler"]
        self.assertTrue(item["worth"], item.get("why"))
        self.assertEqual(item["title"], "Azərbaycan Kubokunun 1/8 final mərhələsi: «Turan Tovuz» «Kəpəz»i, «Sabah» «İmişli»ni qəbul edəcək")
        self.assertEqual(item["lead"], "Azərbaycan Kubokunun 1/8 final mərhələsinin cütləri bəllidir. Premyer Liqa komandaları 4 cütdə "
                                       "bir-biri ilə qarşılaşacaq: «Turan Tovuz» – «Kəpəz», «Sabah» – «İmişli», «Neftçi» – «Şəfa», "
                                       "«Sumqayıt» – «Qarabağ».")
        self.assertEqual(len(item["body"]), 8)
        self.assertNotIn("dekabr", item["lead"] + " ".join(item["body"]))  # 1 dekabr 12:00 hamısı üçün yer tutucudur
        self.assertNotIn("kubok-2026-1-8-final-cutler", {i["key"] for i in fa.items(FIX, at("2026-11-09T12:00+04:00"))})


class RealNationalAndEuropeTest(unittest.TestCase):
    def test_national_team_preview(self):
        # Açar oyunun tarixindən yox, mərhələ, rəqib və meydandan qurulur: tarixi dəyişən oyun ikinci xəbər vermir.
        item = by_key(fa.items(FIX, at("2026-11-12T12:30+04:00")))["milli-ml-d-2026-qrup-2-lixtensteyn-sefer-oncesi"]
        self.assertTrue(item["worth"], item.get("why"))
        self.assertEqual(item["title"], "Azərbaycan millisi Millətlər Liqasında 13 noyabrda Lixtenşteynə qonaq gedəcək")
        self.assertEqual(item["lead"], "Azərbaycan millisi UEFA Millətlər Liqasının D liqasında 2-ci qrupdakı növbəti oyununu 13 noyabrda "
                                       "«Rheinpark Stadion»da Lixtenşteyn millisinə qarşı keçirəcək. Görüş Bakı vaxtı ilə saat 23:45-də "
                                       "başlayacaq. Qrupda Azərbaycan 3 oyunda 5 xalla birinci, Litva 3 oyunda 4 xalla ikinci, "
                                       "Lixtenşteyn 2 oyunda 1 xalla üçüncü yerdədir. Bu, Azərbaycanın qrupdakı son oyunudur.")
        self.assertEqual((item["credit"], item["slot"]), ("Vikipediya", "12:00"))

    def test_national_team_result(self):
        item = by_key(fa.items(FIX, at("2026-10-04T20:00+04:00")))["milli-ml-d-2026-qrup-2-litva-ev-netice"]
        self.assertTrue(item["worth"], item.get("why"))
        self.assertEqual(item["title"], "Azərbaycan millisi Millətlər Liqasında Litvanı 1:0 hesabı ilə məğlub edib")
        self.assertEqual(item["lead"], "Azərbaycan millisi UEFA Millətlər Liqasının D liqasında 2-ci qrupdakı oyununda Neftçi Arenada Litva "
                                       "millisini 1:0 hesabı ilə məğlub edib. Bu nəticədən sonra Azərbaycan 3 oyunda 5 xal toplayıb və "
                                       "qrupda birinci yerdədir. Komanda növbəti oyununu 13 noyabrda Bakı vaxtı ilə saat 23:45-də "
                                       "Lixtenşteynə qarşı keçirəcək.")
        self.assertEqual(item["body"], ["1-ci yer: Azərbaycan – 3 oyun, 5 xal", "2-ci yer: Litva – 3 oyun, 4 xal",
                                        "3-cü yer: Lixtenşteyn – 2 oyun, 1 xal"])

    def test_sabah_result_in_europe(self):
        item = by_key(fa.items(FIX, at("2026-11-05T08:30+04:00")))["avro-cl-2026-sabah-4-viking-sefer-netice"]
        self.assertTrue(item["worth"], item.get("why"))
        self.assertEqual(item["title"], "«Sabah» Çempionlar Liqasında «Viking»ə 1:4 hesabı ilə uduzub")
        self.assertEqual(item["lead"], "Çempionlar Liqasının liqa mərhələsinin 4-cü turunda «Sabah» səfərdə «Viking»lə qarşılaşıb və 1:4 "
                                       "hesabı ilə məğlub olub. Azərbaycan təmsilçisi 4 oyunda 3 xal toplayıb (1 qələbə, 3 məğlubiyyət) "
                                       "və 36 komanda arasında 31-ci yerdədir. «Sabah» növbəti oyununu 25 noyabrda Bakı vaxtı ilə saat "
                                       "21:45-də doğma meydanda «Barcelona»ya qarşı keçirəcək.")
        self.assertEqual((item["slot"], item["credit"]), ("08:00", "OpenLigaDB"))  # oyun Bakı vaxtı ilə 00:00-da başlayıb

    def test_sabah_preview(self):
        item = by_key(fa.items(FIX, at("2026-11-24T12:30+04:00")))["avro-cl-2026-sabah-5-barcelona-ev-oncesi"]
        self.assertTrue(item["worth"], item.get("why"))
        self.assertEqual(item["title"], "«Sabah» Çempionlar Liqasında 25 noyabrda «Barcelona»nı qəbul edəcək")
        self.assertEqual(item["lead"], "Çempionlar Liqasının liqa mərhələsinin 5-ci turunda «Sabah» 25 noyabrda Bakı vaxtı ilə saat "
                                       "21:45-də doğma meydanda «Barcelona»yla qarşılaşacaq. «Sabah» 4 oyunda 3 xal toplayıb və 36 "
                                       "komanda arasında 31-ci yerdədir. «Barcelona» 4 oyunda 9 xalla 5-ci yerdədir.")


class EdgeCaseTest(unittest.TestCase):
    def items_at(self, docs, now, fetch=None):
        with tempfile.TemporaryDirectory() as tmp:
            return by_key(fa.items(site(tmp, docs), at(now), fetch))

    def test_round_with_an_unplayed_game_waits(self):
        games = R1 + R2 + [game(3, "2026-11-15T15:00+04:00", "neftci", "qarabag", (1, 0)),
                           game(3, "2026-11-15T18:00+04:00", "sabah", "zire")]
        item = self.items_at({"premyer-liqa": league(games)}, "2026-11-15T21:00+04:00")["tur-premyer-liqa-2026-t3"]
        self.assertFalse(item["worth"])
        self.assertEqual(item["why"], "tur bitməyib: «Sabah» – «Zirə» oyununun nəticəsi yoxdur")

    def test_postponed_game_does_not_hold_the_round(self):
        games = R1 + R2 + [game(3, "2026-11-15T15:00+04:00", "neftci", "qarabag", (1, 0)),
                           game(3, "2026-12-20T18:00+04:00", "sabah", "zire")]
        item = self.items_at({"premyer-liqa": league(games)}, "2026-11-15T18:00+04:00")["tur-premyer-liqa-2026-t3"]
        self.assertTrue(item["worth"], item.get("why"))
        self.assertEqual(item["title"], "Premyer Liqada 3-cü tur: «Neftçi» fərqi 6 xala çatdırıb, 1 oyunda 1 qol vurulub")
        self.assertIn("Turun «Sabah» – «Zirə» oyunu 20 dekabrda keçiriləcək.", item["body"])
        self.assertIn("«Sabah» və «Zirə» 2 oyun keçirib, digər komandalar isə 3 oyun.", item["body"])
        self.assertEqual(item["slot"], "17:15")

    def test_placeholder_times(self):
        games = R1 + R2 + [game(3, "2026-11-22T00:00+04:00", "neftci", "zire"), game(3, "2026-11-22T00:00+04:00", "sabah", "qarabag")]
        item = self.items_at({"premyer-liqa": league(games)}, "2026-11-21T12:30+04:00")["tur-oncesi-premyer-liqa-2026-t3"]
        self.assertFalse(item["worth"])
        self.assertIn("00:00", item["why"])
        games[-2]["date"] = games[-1]["date"] = "2026-11-22T16:00+04:00"
        item = self.items_at({"premyer-liqa": league(games)}, "2026-11-21T12:30+04:00")["tur-oncesi-premyer-liqa-2026-t3"]
        self.assertTrue(item["worth"], item.get("why"))
        self.assertTrue(item["title"].startswith("Premyer Liqada 3-cü tur 22 noyabrda başlayır: lider «Neftçi» "), item["title"])

    def test_table_ties_are_not_ranked_by_guess(self):
        games = [game(1, "2026-11-01T15:00+04:00", "neftci", "sabah", (1, 0)), game(1, "2026-11-01T18:00+04:00", "qarabag", "zire", (1, 0)),
                 game(2, "2026-11-08T15:00+04:00", "sabah", "zire", (2, 0)), game(2, "2026-11-08T18:00+04:00", "neftci", "qarabag", (0, 0))]
        got = self.items_at({"premyer-liqa": league(games)}, "2026-11-08T21:00+04:00")
        item = got["tur-premyer-liqa-2026-t2"]
        self.assertTrue(item["worth"], item.get("why"))
        self.assertEqual(item["title"], "Premyer Liqada 2-ci tur: «Qarabağ» və «Neftçi» 4 xalla öndədir, 2 oyunda 2 qol vurulub")
        self.assertIn("«Qarabağ» və «Neftçi» 4 xalla cədvəlin başındadır.", item["lead"])
        self.assertFalse(any(b.startswith("Cədvəldə") for b in item["body"]))  # yeri bölüşülənlərin «yer dəyişməsi» yazılmır

    def test_table_that_disagrees_with_the_games_gives_no_item(self):
        rows = rows_for(R1 + R2)
        rows[0]["pts"] += 2
        item = self.items_at({"premyer-liqa": league(R1 + R2, rows=rows)}, "2026-11-08T21:00+04:00")["tur-premyer-liqa-2026-t2"]
        self.assertFalse(item["worth"])
        self.assertTrue(item["why"].startswith("rəsmi cədvəl oyunların nəticələri ilə uyğun gəlmir"), item["why"])

    def test_missing_or_broken_data_gives_nothing(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.assertEqual(fa.items(pathlib.Path(tmp), at("2026-11-10T09:00+04:00")), [])
            md = "\n".join(fa.sinaq(pathlib.Path(tmp), at("2026-11-10T09:00+04:00"), FakeFetch({})))
            self.assertIn("> Məlumatda belə hal yoxdur.", md)
        broken = {"premyer-liqa": "{not json", "i-liqa": {"games": "x", "teams": [], "groups": "y"},
                  "kubok": {"games": [{"home": "a"}, {"home": "a", "away": "b", "date": "dünən"}]}}
        with tempfile.TemporaryDirectory() as tmp:
            root = site(tmp, broken)
            self.assertEqual(fa.items(root, at("2026-11-10T09:00+04:00")), [])
            self.assertEqual(fa._events(root)[1], [])

    def test_leadership_name_is_never_auto_published(self):
        teams = dict(TEAMS, zire="İlham Əliyev")
        item = self.items_at({"premyer-liqa": league(R1 + R2, teams=teams)}, "2026-11-08T21:00+04:00")["tur-premyer-liqa-2026-t2"]
        self.assertFalse(item["worth"])
        self.assertIn("rəhbərliyin adı", item["why"])

    def test_daily_cap_keeps_the_most_important(self):
        docs = {"premyer-liqa": league(R1 + R2),
                "i-liqa": league(R1 + R2, lid="i-liqa", name="I Liqa", short="I Liqa")}
        got = self.items_at(docs, "2026-11-08T21:00+04:00")
        self.assertTrue(got["tur-premyer-liqa-2026-t2"]["worth"])
        self.assertTrue(got["tur-i-liqa-2026-t2"]["worth"])
        with patch.object(fa, "DAY_CAP", 1):
            got = self.items_at(docs, "2026-11-08T21:00+04:00")
        self.assertTrue(got["tur-premyer-liqa-2026-t2"]["worth"])
        self.assertFalse(got["tur-i-liqa-2026-t2"]["worth"])
        self.assertIn("gündəlik hədd", got["tur-i-liqa-2026-t2"]["why"])


class CupNationalEuropeBranchesTest(unittest.TestCase):
    """Real məlumatda hələ olmayan hallar: iki oyunluq mərhələnin cəmi, final, millinin məğlubiyyəti və heç-heçəsi,
    avrokubokda qələbə və heç-heçə."""

    def items_at(self, docs, now, menu=None):
        with tempfile.TemporaryDirectory() as tmp:
            root = site(tmp, docs)
            if menu is not None:
                (root / "data" / "milli-menyu.json").write_text(json.dumps(menu, ensure_ascii=False), encoding="utf-8")
            return by_key(fa.items(root, at(now)))

    def cup(self):
        return {"id": "kubok", "name": "Azərbaycan Kuboku", "short": "Kubok", "source": "pfl.az", "key": "2026", "season": "2026-27",
                "teams": {k: {"name": v} for k, v in TEAMS.items()}, "groups": [],
                "games": [game("1/2 ilk", "2027-04-15T18:00+04:00", "sabah", "qarabag", (1, 0)),
                          game("1/2 ilk", "2027-04-15T20:00+04:00", "zire", "neftci", (2, 2)),
                          game("1/2 cavab", "2027-04-29T18:00+04:00", "qarabag", "sabah", (2, 1)),
                          game("1/2 cavab", "2027-04-29T20:00+04:00", "neftci", "zire", (0, 1)),
                          game("Final", "2027-05-13T20:00+04:00", "sabah", "zire", None, "Bakı Olimpiya Stadionu")]}

    def test_two_legged_stage_and_final_pairs(self):
        got = self.items_at({"kubok": self.cup()}, "2027-04-29T23:00+04:00")
        res = got["kubok-2026-1-2-cavab-yekun"]
        self.assertTrue(res["worth"], res.get("why"))
        # Cavab oyununun qalibi («Qarabağ») cəmdə kənarlaşıb: başlıq finala yüksələnlərdir.
        self.assertEqual(res["title"], "Azərbaycan Kubokunda «Sabah» və «Zirə» finala yüksəlib")
        self.assertEqual(res["lead"], "Azərbaycan Kubokunun yarımfinalının cavab oyunları 29 apreldə keçirilib. «Sabah» və «Zirə» finala "
                                      "yüksəlib. Mərhələnin 2 oyununda 4 qol vurulub.")
        self.assertEqual(res["body"], ["«Qarabağ» – «Sabah» – 2:1; iki oyunun cəmi 2:2 (növbəti mərhələyə «Sabah» keçib)",
                                       "«Neftçi» – «Zirə» – 0:1; iki oyunun cəmi 2:3 (növbəti mərhələyə «Zirə» keçib)"])
        pairs = got["kubok-2026-final-cutler"]
        self.assertEqual(pairs["title"], "Azərbaycan Kubokunun finalında «Sabah» və «Zirə» qarşılaşacaq")
        self.assertEqual(pairs["lead"], "Azərbaycan Kubokunun finalının iştirakçıları bəllidir: «Sabah» və «Zirə». Oyun 13 mayda "
                                        "saat 20:00-də keçiriləcək.")
        self.assertEqual(pairs["body"], ["«Sabah» – «Zirə» (13 may, 20:00, Bakı Olimpiya Stadionu)"])

    def test_cup_final_winner(self):
        doc = self.cup()
        doc["games"][-1].update(played=True, hs=2, **{"as": 1})
        item = self.items_at({"kubok": doc}, "2027-05-13T23:00+04:00")["kubok-2026-final-yekun"]
        self.assertEqual(item["title"], "Azərbaycan Kubokunun finalı: «Sabah» «Zirə»ni 2:1 hesabı ilə məğlub edib")
        self.assertEqual(item["lead"], "Azərbaycan Kubokunun finalı 13 mayda keçirilib. «Sabah» Azərbaycan Kubokunu qazanıb.")

    def test_national_team_loss_and_draws(self):
        teams = {"azerbaycan": "Azərbaycan", "litva": "Litva", "malta": "Malta", "andorra": "Andorra"}
        menu = {"comps": [{"id": "ml-d", "name": "Millətlər Liqası D", "teams": list(teams.values())}]}

        def nat(played):
            """Qrupun üç oyunu; ilk «played» oyunun nəticəsi var, qalanları hələ oynanmayıb."""
            games = [game("Qrup 2", "2026-09-24T16:00:00+00:00", "azerbaycan", "litva", (0, 1), ""),
                     game("Qrup 2", "2026-09-27T16:00:00+00:00", "malta", "azerbaycan", (2, 2), "National Stadium"),
                     game("Qrup 2", "2026-10-01T16:00:00+00:00", "azerbaycan", "andorra", (0, 0), "Neftchi Arena")]
            for g in games[played:]:
                g["played"] = False
                del g["hs"], g["as"]
            return {"ml-d": {"id": "ml-d", "name": "Millətlər Liqası D", "source": "Vikipediya", "url": "https://en.wikipedia.org/wiki/ML_D",
                             "key": "2026", "teams": {k: {"name": v} for k, v in teams.items()},
                             "groups": [{"name": "Qrup 2", "rows": []}], "games": games}}
        loss = self.items_at(nat(1), "2026-09-24T23:00+04:00", menu)["milli-ml-d-2026-qrup-2-litva-ev-netice"]
        self.assertEqual(loss["title"], "Azərbaycan millisi Millətlər Liqasında Litvaya 0:1 hesabı ilə uduzub")
        self.assertIn("2-ci qrupdakı oyununda Litva millisinə 0:1 hesabı ilə uduzub.", loss["lead"])
        # 0 xal: «0 xal toplayıb» yox; «Malta» və «Andorra» ilə xal bərabərdir: hesablanmış cədvəldə yer yazılmır.
        self.assertIn("Bu nəticədən sonra Azərbaycan 1 oyunda xal qazanmayıb. ", loss["lead"])
        self.assertIn("Komanda növbəti oyununu 27 sentyabrda Bakı vaxtı ilə saat 20:00-də Maltaya qarşı keçirəcək.", loss["lead"])
        draw = self.items_at(nat(2), "2026-09-27T23:00+04:00", menu)["milli-ml-d-2026-qrup-2-malta-sefer-netice"]
        self.assertEqual(draw["title"], "Azərbaycan millisi Millətlər Liqasında səfərdə Malta ilə 2:2 hesabı ilə heç-heçə edib")
        self.assertIn("2-ci qrupdakı oyununda «National Stadium»da Malta millisi ilə 2:2 hesabı ilə heç-heçə edib.", draw["lead"])
        last = self.items_at(nat(3), "2026-10-01T23:00+04:00", menu)["milli-ml-d-2026-qrup-2-andorra-ev-netice"]
        self.assertEqual(last["title"], "Azərbaycan millisi Millətlər Liqasında Andorra ilə qolsuz heç-heçə edib")
        self.assertIn("oyununda Neftçi Arenada Andorra millisi ilə qolsuz heç-heçə edib.", last["lead"])
        self.assertTrue(last["lead"].endswith("Bu, Azərbaycanın qrupdakı son oyunu idi."), last["lead"])

    def test_club_win_and_draw_in_europe(self):
        cl = {"id": "cl", "name": "Çempionlar Liqası", "source": "OpenLigaDB (www.openligadb.de)",
              "source_url": "https://www.openligadb.de/", "key": "2026",
              "teams": {"sabah": {"name": "Sabah"}, "arsenal": {"name": "Arsenal"}, "napoli": {"name": "Napoli"}},
              "groups": [{"name": "", "rows": [{"team": "napoli", "pos": 1, "p": 1, "pts": 1}, {"team": "sabah", "pos": 2, "p": 2, "pts": 4},
                                               {"team": "arsenal", "pos": 3, "p": 1, "pts": 0}]}],
              "games": [{"date": "2026-10-13T16:45:00+00:00", "home": "sabah", "away": "arsenal", "played": True, "round": "2", "hs": 3, "as": 0},
                        {"date": "2026-10-20T19:00:00+00:00", "home": "napoli", "away": "sabah", "played": True, "round": "3", "hs": 1, "as": 1}]}
        docs = {"premyer-liqa": league(R1 + R2), "cl": cl}
        win = self.items_at(docs, "2026-10-13T23:30+04:00")["avro-cl-2026-sabah-2-arsenal-ev-netice"]
        self.assertEqual(win["title"], "«Sabah» Çempionlar Liqasında «Arsenal»ı 3:0 hesabı ilə məğlub edib")
        self.assertIn("«Sabah» doğma meydanda «Arsenal»la qarşılaşıb və 3:0 hesabı ilə qalib gəlib. Azərbaycan təmsilçisi 1 oyunda "
                      "3 xal toplayıb (1 qələbə).", win["lead"])  # sonra oyun olub: cədvəldəki yer o günə aid deyil, yazılmır
        draw = self.items_at(docs, "2026-10-21T08:30+04:00")["avro-cl-2026-sabah-3-napoli-sefer-netice"]
        self.assertEqual(draw["title"], "«Sabah» Çempionlar Liqasında «Napoli»ylə 1:1 hesabı ilə heç-heçə edib")
        self.assertIn("(1 qələbə, 1 heç-heçə) və 3 komanda arasında 2-ci yerdədir.", draw["lead"])
        self.assertEqual(draw["slot"], "08:00")


def real_cup_2025(unplay=()):
    """Keçən mövsümün real kubok faylı (main-in data/futbol/kubok-2025.json, logolar çıxarılıb): iki oyunluq 1/4 final və
    yarımfinal, final. unplay: nəticəsi silinən mərhələlər (cütlər xəbəri üçün)."""
    doc = json.loads((FIX / "kubok-2025.json").read_text(encoding="utf-8"))
    for g in doc["games"]:
        if g["round"] in unplay:
            g["played"] = False
            g.pop("hs", None)
            g.pop("as", None)
    return doc


def scorer_fetch(rows):
    """pfl.az-ın saxtası: /seasons real cavabdır, /bombarders/list verilən sətirlərdir (ad, soyad, klub, qol)."""
    body = {"data": {"data": [{"player": {"name": n, "surname": s}, "club": {"title": c}, "value": str(v)} for n, s, c, v in rows],
                     "last_page": 1, "total": len(rows)}}
    return FakeFetch({"/seasons?project_id=1": (FIX / "pfl" / "seasons.json").read_bytes(), "/bombarders/list?league_id=52": body})


class ReviewTest(unittest.TestCase):
    """Müstəqil yoxlamada (2026-11-10) tapılan boşluqlar: hər biri əvvəl uğursuz test kimi yazılıb."""

    def items_at(self, docs, now, fetch=None, menu=None):
        with tempfile.TemporaryDirectory() as tmp:
            root = site(tmp, docs)
            if menu is not None:
                (root / "data" / "milli-menyu.json").write_text(json.dumps(menu, ensure_ascii=False), encoding="utf-8")
            return fa.items(root, at(now), fetch)

    def test_published_keys_are_not_rebuilt_and_pfl_is_not_asked_again(self):
        # Canlı items()-i hər futbol dövrəsində (10 dəqiqə) çağırır: dərc olunmuş açar ötürülməsə, bombardirlərin 24 saatlıq
        # pəncərəsində hər dövrə pfl.az-a 2 sorğu gedərdi.
        fetch = real_pfl()
        got = by_key(fa.items(FIX, at("2026-11-09T10:30+04:00"), fetch, done={"bombardir-premyer-liqa-2026-t11"}))
        self.assertNotIn("bombardir-premyer-liqa-2026-t11", got)
        self.assertIn("tur-premyer-liqa-2026-t11", got)
        self.assertEqual(fetch.urls, [])

    def test_preview_waits_when_the_official_table_disagrees_with_the_games(self):
        # I Liqanın 7-ci turundakı kimi: rəsmi cədvəl games[]-də nəticəsi olmayan oyunu sayıb. Hesablanmış xal və yer səhv olar.
        games = R1 + R2 + [game(3, "2026-11-22T16:00+04:00", "neftci", "zire"), game(3, "2026-11-22T19:00+04:00", "sabah", "qarabag")]
        rows = rows_for(R1 + R2)
        rows[0]["p"] += 1
        rows[0]["pts"] += 3
        item = by_key(self.items_at({"premyer-liqa": league(games, rows=rows)}, "2026-11-21T12:30+04:00"))["tur-oncesi-premyer-liqa-2026-t3"]
        self.assertFalse(item["worth"])
        self.assertIn("rəsmi cədvəl", item["why"])

    def test_national_standings_with_a_points_tie_give_no_place(self):
        # UEFA-da xal bərabərliyində əvvəlcə qarşılıqlı oyunlar həll edir. Qol fərqi ilə «Azərbaycan» üçüncü olardı,
        # qarşılıqlı oyunlarla («Azərbaycan» – «Litva» 1:0, «Andorra» – «Azərbaycan» 1:0) ikincidir: yer yazılmamalıdır.
        teams = {"azerbaycan": "Azərbaycan", "litva": "Litva", "malta": "Malta", "andorra": "Andorra"}
        menu = {"comps": [{"id": "ml-d", "name": "Millətlər Liqası D", "teams": list(teams.values())}]}
        games = [game("Qrup 2", "2026-09-24T16:00:00+00:00", "azerbaycan", "litva", (1, 0), "Neftchi Arena"),
                 game("Qrup 2", "2026-09-27T16:00:00+00:00", "litva", "malta", (5, 0), "LFF Stadium"),
                 game("Qrup 2", "2026-09-27T18:45:00+00:00", "andorra", "azerbaycan", (1, 0), "Estadi Nacional")]
        doc = {"id": "ml-d", "name": "Millətlər Liqası D", "source": "Vikipediya", "url": "https://en.wikipedia.org/wiki/ML_D",
               "key": "2026", "teams": {k: {"name": v} for k, v in teams.items()}, "groups": [{"name": "Qrup 2", "rows": []}],
               "games": games}
        item = next(i for i in self.items_at({"ml-d": doc}, "2026-09-28T08:30+04:00", menu=menu) if i["kind"] == "milli-netice")
        self.assertTrue(item["worth"], item.get("why"))
        self.assertIn("Bu nəticədən sonra Azərbaycan 2 oyunda 3 xal toplayıb.", item["lead"])
        self.assertNotIn("yerdədir", item["lead"])
        self.assertFalse(any(re.match(r"\d+-c\w yer:", b) for b in item["body"]), item["body"])

    def test_cup_return_legs_lead_with_who_went_through(self):
        # Real məlumat, 2025-26. 1/4 final: «Qəbələ» – «Sabah» 3:3, cəmi 3:3, keçən yarımfinalın cütlərindəndir.
        doc = real_cup_2025()
        qf = by_key(self.items_at({"kubok": doc}, "2026-03-05T21:00+04:00"))["kubok-2025-1-4-cavab-yekun"]
        self.assertTrue(qf["worth"], qf.get("why"))
        self.assertEqual(qf["title"], "Bizon Azərbaycan Kubokunda «Zirə», «Qarabağ», «Turan Tovuz» və «Sabah» yarımfinala yüksəlib")
        self.assertEqual(qf["lead"], "Bizon Azərbaycan Kubokunun 1/4 final mərhələsinin cavab oyunları 3–5 martda keçirilib. «Zirə», "
                                     "«Qarabağ», «Turan Tovuz» və «Sabah» yarımfinala yüksəlib. Mərhələnin 4 oyununda 14 qol vurulub.")
        self.assertEqual(qf["body"], [
            "«Zirə» – «Sumqayıt» – 2:0; iki oyunun cəmi 2:0 (növbəti mərhələyə «Zirə» keçib)",
            "«Qarabağ» – «Şamaxı» – 3:1; iki oyunun cəmi 4:3 (növbəti mərhələyə «Qarabağ» keçib)",
            "«Kəpəz» – «Turan Tovuz» – 0:2; iki oyunun cəmi 0:3 (növbəti mərhələyə «Turan Tovuz» keçib)",
            "«Qəbələ» – «Sabah» – 3:3; iki oyunun cəmi 3:3 (növbəti mərhələyə «Sabah» keçib)"])
        sf = by_key(self.items_at({"kubok": doc}, "2026-04-22T23:00+04:00"))["kubok-2025-1-2-cavab-yekun"]
        self.assertEqual(sf["title"], "Bizon Azərbaycan Kubokunda «Zirə» və «Sabah» finala yüksəlib")
        final = by_key(self.items_at({"kubok": doc}, "2026-05-13T23:00+04:00"))["kubok-2025-final-yekun"]
        self.assertEqual(final["title"], "Bizon Azərbaycan Kubokunun finalı: «Sabah» «Zirə»ni 2:1 hesabı ilə məğlub edib")
        self.assertEqual(final["lead"], "Bizon Azərbaycan Kubokunun finalı 13 mayda keçirilib. «Sabah» Bizon Azərbaycan Kubokunu qazanıb.")

    def test_two_legged_pairs_give_both_dates(self):
        doc = real_cup_2025(unplay=("1/4 ilk", "1/4 cavab", "1/2 ilk", "1/2 cavab", "Final"))
        item = by_key(self.items_at({"kubok": doc}, "2025-12-05T12:00+04:00"))["kubok-2025-1-4-ilk-cutler"]
        self.assertTrue(item["worth"], item.get("why"))
        self.assertTrue(item["lead"].endswith(" İlk oyunlar 4–5 fevralda, cavab oyunları 3–5 martda keçiriləcək."), item["lead"])
        self.assertEqual(item["body"][0], "«Sumqayıt» – «Zirə» (4 fevral, 17:00, Mehdi Hüseynzadə adına Sumqayıt şəhər stadionu)")

    def test_two_games_at_one_instant_are_a_placeholder(self):
        doc = {"id": "kubok", "name": "Azərbaycan Kuboku", "short": "Kubok", "source": "pfl.az", "key": "2026", "season": "2026-27",
               "teams": {k: {"name": v} for k, v in TEAMS.items()}, "groups": [],
               "games": [game("1/2 ilk", "2027-04-15T12:00+04:00", "sabah", "qarabag", None, ""),
                         game("1/2 ilk", "2027-04-15T12:00+04:00", "zire", "neftci", None, "")]}
        item = by_key(self.items_at({"kubok": doc}, "2027-04-10T12:00+04:00"))["kubok-2026-1-2-ilk-cutler"]
        self.assertTrue(item["worth"], item.get("why"))
        self.assertNotIn("aprel", item["lead"] + " ".join(item["body"]))

    def test_cup_final_level_after_the_game_is_not_published(self):
        # Penaltilər seriyası məlumatda yoxdur: kubokun qalibi bəlli deyil, «heç-heçə edib» xəbəri boşdur.
        doc = CupNationalEuropeBranchesTest.cup(self)
        doc["games"][-1].update(played=True, hs=1, **{"as": 1})
        item = by_key(self.items_at({"kubok": doc}, "2027-05-13T23:00+04:00"))["kubok-2026-final-yekun"]
        self.assertFalse(item["worth"])
        self.assertIn("qalib", item["why"])

    def test_scorer_ties_are_never_cut_and_never_ranked(self):
        many = [("Ad%d" % i, "Soyad", "Zirə", 2) for i in range(5)]
        item = by_key(fa.items(FIX, at("2026-11-09T10:30+04:00"), scorer_fetch(many)))["bombardir-premyer-liqa-2026-t11"]
        self.assertFalse(item["worth"])
        self.assertIn("bərabər", item["why"])
        rows = ([("Breno", "Almeyda", "Neftçi", 9)] + [("Ad%d" % i, "Yeddi", "Sabah", 7) for i in range(3)]
                + [("Ad%d" % i, "Üç", "Qarabağ", 3) for i in range(12)])
        item = by_key(fa.items(FIX, at("2026-11-09T10:30+04:00"), scorer_fetch(rows)))["bombardir-premyer-liqa-2026-t11"]
        self.assertTrue(item["worth"], item.get("why"))
        # 7 qolu olan üç futbolçudan ikisini seçib yazmaq olmaz; 3 qolu olan 12 nəfər siyahıya yarımçıq düşməməlidir.
        self.assertEqual(item["lead"], "Misli Premyer Liqasının 11-ci turundan sonra bombardirlər siyahısına «Neftçi»nin futbolçusu "
                                       "Breno Almeyda 9 qolla başçılıq edir.")
        self.assertEqual([b.split(" – ")[1] for b in item["body"]], ["9 qol", "7 qol", "7 qol", "7 qol"])

    def test_zero_goal_round(self):
        games = [game(1, "2026-11-01T15:00+04:00", "neftci", "sabah", (0, 0)), game(1, "2026-11-01T18:00+04:00", "qarabag", "zire", (0, 0))]
        item = by_key(self.items_at({"premyer-liqa": league(games)}, "2026-11-01T21:00+04:00"))["tur-premyer-liqa-2026-t1"]
        self.assertTrue(item["worth"], item.get("why"))
        self.assertEqual(item["title"], "Premyer Liqada 1-ci tur: 2 oyunda qol vurulmayıb")
        self.assertEqual(item["lead"], "Misli Premyer Liqasının 1-ci turu 1 noyabrda keçirilib. Turun 2 oyununda qol vurulmayıb.")

    def test_long_competition_names_keep_titles_short(self):
        teams = {"azerbaycan": "Azərbaycan", "bosniya": "Bosniya və Herseqovina", "norvec": "Norveç"}
        menu = {"comps": [{"id": "avro-2028-secme", "name": "Avropa Çempionatı 2028: seçmə", "teams": list(teams.values())}]}
        doc = {"id": "avro-2028-secme", "name": "Avropa Çempionatı 2028: seçmə", "source": "Vikipediya",
               "url": "https://en.wikipedia.org/wiki/UEFA_Euro_2028_qualifying", "key": "2028",
               "teams": {k: {"name": v} for k, v in teams.items()}, "groups": [{"name": "Qrup A", "rows": []}],
               "games": [game("Qrup A", "2027-03-25T19:45:00+00:00", "bosniya", "azerbaycan", (2, 2), "Grbavica"),
                         game("Qrup A", "2027-03-28T16:00:00+00:00", "azerbaycan", "norvec", None, "Neftchi Arena")]}
        got = self.items_at({"avro-2028-secme": doc}, "2027-03-26T08:30+04:00", menu=menu)
        res = next(i for i in got if i["kind"] == "milli-netice")
        self.assertEqual(res["title"], "Azərbaycan millisi səfərdə Bosniya və Herseqovina ilə 2:2 hesabı ilə heç-heçə edib")
        self.assertTrue(res["lead"].startswith("Azərbaycan millisi Avropa Çempionatının seçmə mərhələsində A qrupundakı oyununda "
                                               "«Grbavica»da Bosniya və Herseqovina millisi ilə 2:2 hesabı ilə heç-heçə edib."), res["lead"])

    def test_european_knockout_stage_names(self):
        cl = {"id": "cl", "name": "Çempionlar Liqası", "source": "OpenLigaDB (www.openligadb.de)", "source_url": "https://www.openligadb.de/",
              "key": "2026", "teams": {"sabah": {"name": "Sabah"}, "arsenal": {"name": "Arsenal"}}, "groups": [],
              "games": [{"date": "2027-02-17T17:45:00+00:00", "home": "sabah", "away": "arsenal", "played": True,
                         "round": "1/8 final, 1-ci oyun", "hs": 1, "as": 0}]}
        got = self.items_at({"premyer-liqa": league(R1 + R2), "cl": cl}, "2027-02-18T00:30+04:00")
        item = next(i for i in got if i["kind"] == "avro-netice")
        self.assertTrue(item["lead"].startswith("Çempionlar Liqasının 1/8 final mərhələsinin ilk oyununda «Sabah» doğma meydanda "
                                                "«Arsenal»la qarşılaşıb və 1:0 hesabı ilə qalib gəlib."), item["lead"])
        self.assertNotIn("xal", item["lead"])  # xal yalnız liqa mərhələsindədir: pley-off oyunu xal vermir

    def test_national_game_without_a_known_time_or_postponed_gets_no_preview(self):
        # milli.cjs vaxtı elan olunmayan oyunu «T12:00:00+00:00» və day=true, təxirə salınanı state="off" yazır:
        # saat 16:00 uydurulmamalı, təxirə salınan oyuna baxış yazılmamalıdır.
        doc = json.loads((FIX / "data" / "futbol" / "ml-d.json").read_text(encoding="utf-8"))
        menu = json.loads((FIX / "data" / "milli-menyu.json").read_text(encoding="utf-8"))
        nxt = next(g for g in doc["games"] if g["home"] == "lixtensteyn" and g["away"] == "azerbaycan")
        nxt.update(date="2026-11-13T12:00:00+00:00", day=True)
        got = self.items_at({"ml-d": doc}, "2026-11-12T12:30+04:00", menu=menu)
        self.assertEqual([i["key"] for i in got if i["kind"] == "milli-oncesi"], [])
        res = by_key(self.items_at({"ml-d": doc}, "2026-10-04T20:00+04:00", menu=menu))["milli-ml-d-2026-qrup-2-litva-ev-netice"]
        self.assertNotIn("növbəti oyununu", res["lead"])
        del nxt["day"]
        nxt.update(date="2026-11-13T19:45:00+00:00", state="off")
        got = self.items_at({"ml-d": doc}, "2026-11-12T12:30+04:00", menu=menu)
        self.assertEqual([i["key"] for i in got if i["kind"] == "milli-oncesi"], [])


class SecondReviewTest(unittest.TestCase):
    """İkinci müstəqil yoxlama (2026-11-10): hər biri əvvəl uğursuz test kimi yazılıb."""

    def items_at(self, docs, now, fetch=None):
        with tempfile.TemporaryDirectory() as tmp:
            return by_key(fa.items(site(tmp, docs), at(now), fetch))

    def test_points_ties_are_never_ranked_in_moves(self):
        # pfl.az bərabər xalda əvvəlcə qarşılıqlı oyunlara baxır: 2025-26 mövsümünün sonunda «Turan Tovuz» (59 xal, +17)
        # «Neftçi»dən (59 xal, +25) yuxarıdadır (premyer-liqa-2025.json). Xalı bərabər olanın yeri qol fərqi ilə təxmin edilmir.
        r1 = [game(1, "2026-11-01T15:00+04:00", "neftci", "sabah", (1, 0)), game(1, "2026-11-01T18:00+04:00", "qarabag", "zire", (0, 0))]
        r2 = [game(2, "2026-11-08T15:00+04:00", "sabah", "zire", (6, 0)), game(2, "2026-11-08T18:00+04:00", "neftci", "qarabag", (0, 1))]
        # Turdan əvvəl «Sabah» və «Neftçi» 3 xalla bərabərdir («Neftçi» qarşılıqlı oyunu udub): onların əvvəlki yeri bilinmir.
        r3 = [game(3, "2026-11-15T15:00+04:00", "neftci", "zire", (2, 0)), game(3, "2026-11-15T18:00+04:00", "sabah", "qarabag", (0, 0))]
        item = self.items_at({"premyer-liqa": league(r1 + r2 + r3)}, "2026-11-15T21:00+04:00")["tur-premyer-liqa-2026-t3"]
        self.assertTrue(item["worth"], item.get("why"))
        self.assertEqual([b for b in item["body"] if b.startswith("Cədvəldə")], ["Cədvəldə «Qarabağ» 1-ci yerdən 2-ci yerə düşüb."])
        # Turdan sonra yeni oyun oynanıb: rəsmi cədvəl artıq o tura aid deyil, turdan sonra xalı bərabər olanların yeri də yazılmır.
        r3 = [game(3, "2026-11-15T15:00+04:00", "neftci", "zire", (1, 0)), game(3, "2026-11-15T18:00+04:00", "sabah", "qarabag", (1, 0))]
        r4 = [game(4, "2026-11-16T12:00+04:00", "zire", "qarabag", (1, 1)), game(4, "2026-11-22T12:00+04:00", "neftci", "sabah")]
        item = self.items_at({"premyer-liqa": league(r1 + r2 + r3 + r4)}, "2026-11-16T15:00+04:00")["tur-premyer-liqa-2026-t3"]
        self.assertTrue(item["worth"], item.get("why"))
        self.assertEqual([b for b in item["body"] if b.startswith("Cədvəldə")], ["Cədvəldə «Qarabağ» 1-ci yerdən 3-cü yerə düşüb."])

    def test_cup_pairs_count_premier_league_teams_even_without_places(self):
        # Rəsmi cədvəl oyunlarla uyğun gəlmir və xallar bərabərdir: yerlər bilinmir, amma Premyer Liqa komandaları bəllidir.
        r1 = [game(1, "2026-11-01T15:00+04:00", "neftci", "sabah", (1, 0)), game(1, "2026-11-01T18:00+04:00", "qarabag", "zire", (1, 0))]
        rows = rows_for(r1)
        rows[0]["pts"] += 2
        teams = dict(TEAMS, karvan="Karvan-Yevlax", simal="Şimal")
        cup = {"id": "kubok", "name": "Azərbaycan Kuboku", "short": "Kubok", "source": "pfl.az", "key": "2026", "season": "2026-27",
               "teams": {k: {"name": v} for k, v in teams.items()}, "groups": [],
               "games": [game("1/8 final", "2026-12-02T15:00+04:00", "karvan", "simal"),
                         game("1/8 final", "2026-12-02T18:00+04:00", "neftci", "qarabag"),
                         game("1/8 final", "2026-12-03T15:00+04:00", "sabah", "zire")]}
        item = self.items_at({"premyer-liqa": league(r1, rows=rows), "kubok": cup}, "2026-11-26T12:00+04:00")["kubok-2026-1-8-final-cutler"]
        self.assertTrue(item["worth"], item.get("why"))
        self.assertEqual(item["title"], "Azərbaycan Kubokunun 1/8 final mərhələsi: «Neftçi» «Qarabağ»ı, «Sabah» «Zirə»ni qəbul edəcək")
        self.assertIn(" Premyer Liqa komandaları 2 cütdə bir-biri ilə qarşılaşacaq: «Neftçi» – «Qarabağ», «Sabah» – «Zirə».", item["lead"])

    def test_postponed_european_game_gets_no_preview(self):
        # TheSportsDB (al.json, kl.json) təxirə salınan oyunu state="off", saatı bəlli olmayanı 00:00 UTC yazır.
        al = {"id": "al", "name": "Avropa Liqası", "source": "TheSportsDB", "source_url": "https://www.thesportsdb.com/", "key": "2026",
              "teams": {"sabah": {"name": "Sabah"}, "roma": {"name": "Roma"}, "porto": {"name": "Porto"}}, "groups": [],
              "games": [{"date": "2026-11-26T17:45:00+00:00", "home": "sabah", "away": "roma", "played": False, "round": "5", "state": "off"},
                        {"date": "2026-12-10T00:00:00+00:00", "home": "porto", "away": "sabah", "played": False, "round": "6"}]}
        docs = {"premyer-liqa": league(R1 + R2), "al": al}
        for now in ("2026-11-25T12:30+04:00", "2026-12-09T12:30+04:00"):
            self.assertEqual([k for k, i in self.items_at(docs, now).items() if i["kind"] == "avro-oncesi"], [], now)

    def test_european_knockout_preview_has_no_league_phase_points(self):
        cl = {"id": "cl", "name": "Çempionlar Liqası", "source": "OpenLigaDB (www.openligadb.de)", "source_url": "https://www.openligadb.de/",
              "key": "2026", "teams": {"sabah": {"name": "Sabah"}, "arsenal": {"name": "Arsenal"}},
              "groups": [{"name": "", "rows": [{"team": "arsenal", "pos": 1, "p": 1, "pts": 0}, {"team": "sabah", "pos": 2, "p": 1, "pts": 3}]}],
              "games": [{"date": "2026-09-16T16:45:00+00:00", "home": "sabah", "away": "arsenal", "played": True, "round": "1", "hs": 1, "as": 0},
                        {"date": "2027-02-17T17:45:00+00:00", "home": "arsenal", "away": "sabah", "played": False, "round": "Pley-off"}]}
        item = next(i for i in self.items_at({"premyer-liqa": league(R1 + R2), "cl": cl}, "2027-02-16T12:30+04:00").values()
                    if i["kind"] == "avro-oncesi")
        self.assertTrue(item["worth"], item.get("why"))
        self.assertEqual(item["lead"], "Çempionlar Liqasının pley-off mərhələsində «Sabah» 17 fevralda Bakı vaxtı ilə saat 21:45-də "
                                       "səfərdə «Arsenal»la qarşılaşacaq.")

    def test_a_game_played_early_is_dated_in_the_summary(self):
        # Turun bir oyunu 8 gün əvvəl keçirilib (Avropa oyunlarına görə): «turu 8 noyabrda keçirilib» o oyunun tarixini demir.
        teams = dict(TEAMS, imisli="İmişli", kepez="Kəpəz")
        r1 = [game(1, "2026-10-25T15:00+04:00", "neftci", "sabah", (1, 0)), game(1, "2026-10-25T17:00+04:00", "qarabag", "zire", (1, 1)),
              game(1, "2026-10-25T19:00+04:00", "imisli", "kepez", (0, 2))]
        r2 = [game(2, "2026-10-31T18:00+04:00", "qarabag", "neftci", (2, 0)), game(2, "2026-11-08T15:00+04:00", "sabah", "imisli", (3, 0)),
              game(2, "2026-11-08T18:00+04:00", "kepez", "zire", (1, 1))]
        item = self.items_at({"premyer-liqa": league(r1 + r2, teams=teams)}, "2026-11-08T21:00+04:00")["tur-premyer-liqa-2026-t2"]
        self.assertTrue(item["worth"], item.get("why"))
        self.assertTrue(item["lead"].startswith("Misli Premyer Liqasının 2-ci turu 8 noyabrda keçirilib."), item["lead"])
        self.assertIn("Turun 3 oyununda 7 qol vurulub.", item["lead"])
        self.assertEqual(item["body"][-1], "Turun «Qarabağ» – «Neftçi» oyunu 31 oktyabrda keçirilib.")

    def test_play_off_game_is_not_a_league_game(self):
        # 2025-26: «Qəbələ» – «Mingəçevir» (I Liqanın komandası) keçid oyunu «p/o» turudur və «Mingəçevir» teams-dədir. Liqa
        # cədvəlinə düşməməlidir: ««Mingəçevir» 0 oyun keçirib» yazılmasın, sonuncu yer 4-cüdür, qarşılıqlı oyun sayılmır.
        teams = dict(TEAMS, mingecevir="Mingəçevir")
        r3 = [game(3, "2026-11-22T15:00+04:00", "zire", "neftci"), game(3, "2026-11-22T18:00+04:00", "sabah", "qarabag")]
        games = R1 + R2 + r3 + [game("p/o", "2026-12-20T18:00+04:00", "zire", "mingecevir")]
        docs = {"premyer-liqa": league(games, rows=rows_for(R1 + R2), teams=teams)}
        item = self.items_at(docs, "2026-11-08T21:00+04:00")["tur-premyer-liqa-2026-t2"]
        self.assertTrue(item["worth"], item.get("why"))
        self.assertFalse([b for b in item["body"] if "Mingəçevir" in b], item["body"])
        item = self.items_at(docs, "2026-11-21T12:30+04:00")["tur-oncesi-premyer-liqa-2026-t3"]
        self.assertTrue(item["worth"], item.get("why"))
        self.assertEqual(item["title"], "Premyer Liqada 3-cü tur 22 noyabrda başlayır: lider «Neftçi» sonuncu «Zirə»yə qonaq gedəcək")
        past = [("2025-26", fa._games({"games": [game("10", "2026-03-01T15:00+04:00", "neftci", "sabah", (1, 0)),
                                                  game("p/o", "2026-05-28T18:00+04:00", "sabah", "neftci", (2, 0))]}))]
        self.assertEqual(fa._h2h(past, "neftci", "sabah")["n"], 1)

    def test_teams_without_a_game_yet(self):
        # 2025-26: 1-ci turun «Sabah» – «Qarabağ» oyunu dekabra salınıb. «0 oyun keçirib» yox, «hələ oyun keçirməyib».
        games = [game(1, "2026-11-01T15:00+04:00", "neftci", "sabah", (2, 0)), game(1, "2026-12-20T18:00+04:00", "qarabag", "zire")]
        item = self.items_at({"premyer-liqa": league(games)}, "2026-11-01T18:00+04:00")["tur-premyer-liqa-2026-t1"]
        self.assertTrue(item["worth"], item.get("why"))
        self.assertIn("«Qarabağ» və «Zirə» hələ oyun keçirməyib, digər komandalar isə 1 oyun.", item["body"])
        self.assertNotIn(" 0 xal", item["lead"])  # «Qarabağ», «Zirə» və «Sabah» 0 xal toplayıb — yazılmır

    def test_foreign_club_endings_follow_pronunciation(self):
        # «Hull City»ni (Siti), «Chelsea»ni (Çelsi), «Crystal Palace»i (Pelis), «Sparta Prague»a (Praq), «Red Star Belgrade»i.
        self.assertEqual([fa.sx(n, c) for n, c in (
            ("Leicester City", "acc"), ("Hull City", "dat"), ("Chelsea", "acc"), ("Crystal Palace", "acc"), ("Sparta Prague", "dat"),
            ("TSG Hoffenheim", "ins"), ("Red Star Belgrade", "acc"), ("Union Saint-Gilloise", "acc"))],
            ["«Leicester City»ni", "«Hull City»yə", "«Chelsea»ni", "«Crystal Palace»i", "«Sparta Prague»a", "«TSG Hoffenheim»la",
             "«Red Star Belgrade»i", "«Union Saint-Gilloise»ı"])


SITE = ROOT / "site"  # CI main-in məlumatını bura çıxarır (oz-modul.yml); yerli işdə yoxdur və testlər ötürülür


def site_copy(tmp, swap=None, drop=()):
    """main-in data/futbol və milli-menyu.json surəti. swap: {"premyer-liqa": "premyer-liqa-2025"} keçən mövsümü «bu mövsüm»
    edir (bütöv real mövsüm: təxirə salınan oyunlar, keçid oyunu, cədvəldə xal düzəlişi)."""
    src, dst = SITE / "data", pathlib.Path(tmp) / "data"
    (dst / "futbol").mkdir(parents=True)
    for p in (src / "futbol").glob("*.json"):
        if p.stem not in drop:
            (dst / "futbol" / p.name).write_bytes(p.read_bytes())
    for name, other in (swap or {}).items():
        (dst / "futbol" / f"{name}.json").write_bytes((src / "futbol" / f"{other}.json").read_bytes())
    if (src / "milli-menyu.json").exists():
        (dst / "milli-menyu.json").write_bytes((src / "milli-menyu.json").read_bytes())
    return pathlib.Path(tmp)


SCORE = re.compile(r"«(.+?)» – «(.+?)» – (\d+):(\d+)")


@unittest.skipUnless((SITE / "data" / "futbol" / "premyer-liqa-2025.json").exists(), "main-in məlumatı yoxdur (yalnız CI-da)")
class MainDataSweepTest(unittest.TestCase):
    """main-in bütün real məlumatı ilə hər hadisənin xəbəri qurulur (pəncərəyə və həddə baxmadan): xəta, boş ad, uzun başlıq
    olmamalıdır; tur icmallarının nəticələri və qol sayı oyunlardan ayrıca yoxlanır."""

    def sweep(self, root, league_file):
        evs, errors = fa._events(root)
        self.assertEqual(errors, [])
        doc = json.loads((root / "data" / "futbol" / f"{league_file}.json").read_text(encoding="utf-8"))
        names = {k: (v or {}).get("name") or k for k, v in doc["teams"].items()}
        built = summaries = 0
        for e in evs:
            item = fa._build(e, None)
            built += 1
            why = item.get("why") or ""
            self.assertFalse(why.startswith("xəta"), (e["key"], why))
            if not item["worth"]:
                self.assertTrue(why, e["key"])
                continue
            text = "\n".join([item["title"], item["lead"]] + item["body"])
            self.assertLessEqual(len(item["title"]), fa.TITLE_MAX, item["title"])
            self.assertFalse(item["title"].endswith("."), item["title"])
            self.assertNotRegex(text, r"«»|None|\{|\}|«[a-z0-9-]+»| 0 oyun keçirib", e["key"])
            if e["kind"] != "pfl-tur":
                continue
            summaries += 1
            # Hər nəticə sətri həmin turun oynanmış oyunudur; girişdəki oyun və qol sayı sətirlərlə eynidir.
            rnd = e["key"].rsplit("-t", 1)[1]
            rg = [g for g in doc["games"] if str(g.get("round")) == rnd and g.get("played")]
            listed = []
            for m in (SCORE.fullmatch(b) for b in item["body"]):
                if m:
                    hit = [g for g in rg if (names.get(g["home"]), names.get(g["away"]), g["hs"], g["as"]) == (m[1], m[2], int(m[3]), int(m[4]))]
                    self.assertEqual(len(hit), 1, (e["key"], m[0]))
                    listed.append(hit[0])
            n = re.search(r"Turun (\d+) oyununda (?:(\d+) qol vurulub|qol vurulmayıb)\.", item["lead"])
            self.assertTrue(n, (e["key"], item["lead"]))
            self.assertEqual(int(n[1]), len(listed), e["key"])
            self.assertEqual(int(n[2] or 0), sum(g["hs"] + g["as"] for g in listed), e["key"])
            # Lider: icmaldakı son oyuna qədər yalnız liqa oyunlarından (rəqəmli turlar) hesablanan xal, tək lider.
            last = max(at(g["date"]) for g in listed)
            pts = {}
            for g in doc["games"]:
                if g.get("played") and str(g.get("round")).isdigit() and at(g["date"]) <= last:
                    for k, a, b in ((g["home"], g["hs"], g["as"]), (g["away"], g["as"], g["hs"])):
                        pts[names.get(k)] = pts.get(names.get(k), 0) + (3 if a > b else 1 if a == b else 0)
            lead = re.search(r"Lider «(.+?)» .*? və (\d+) xal toplayıb\.|«([^»]+)» (\d+) xalla liderdir\.", item["lead"])
            if lead:
                who, got = (lead[1], int(lead[2])) if lead[1] else (lead[3], int(lead[4]))
                self.assertEqual(pts[who], got, e["key"])
                self.assertLess(sorted(pts.values())[-2], got, (e["key"], "lider tək deyil"))
        self.assertGreater(built, 50)
        self.assertGreater(summaries, 5)

    def test_current_data(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.sweep(site_copy(tmp), "premyer-liqa")

    def test_last_season_as_the_current_one(self):
        # 2025-26 bütöv: 1-ci, 14-cü, 21-ci turun oyunları aylarla sonraya salınıb, «p/o» keçid oyunu, rəsmi cədvəldə xal düzəlişi.
        with tempfile.TemporaryDirectory() as tmp:
            root = site_copy(tmp, {"premyer-liqa": "premyer-liqa-2025", "kubok": "kubok-2025", "cl": "cl-2025"}, drop=("premyer-liqa-2025",))
            self.sweep(root, "premyer-liqa")

    def test_two_seasons_ago_as_the_current_one(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = site_copy(tmp, {"premyer-liqa": "premyer-liqa-2024"}, drop=("premyer-liqa-2024", "premyer-liqa-2025"))
            self.sweep(root, "premyer-liqa")


class ContractTest(unittest.TestCase):
    TIMES = ("2026-10-04T20:00+04:00", "2026-10-22T18:00+04:00", "2026-10-29T17:00+04:00", "2026-11-03T18:00+04:00",
             "2026-11-05T08:30+04:00", "2026-11-05T18:00+04:00", "2026-11-08T20:00+04:00", "2026-11-09T10:30+04:00",
             "2026-11-10T18:00+04:00", "2026-11-12T12:30+04:00", "2026-11-19T12:30+04:00", "2026-11-24T12:30+04:00",
             "2026-11-26T12:30+04:00")

    def test_every_item_follows_the_contract(self):
        seen = 0
        for now in self.TIMES:
            got = fa.items(FIX, at(now), real_pfl())
            self.assertEqual(got, fa.items(FIX, at(now), real_pfl()))  # eyni məlumat və an: eyni nəticə
            self.assertLessEqual(sum(1 for i in got if i["worth"]), fa.DAY_CAP * 2)
            for i in got:
                seen += 1
                for k in ("kind", "key", "title", "lead", "body", "credit", "link", "topic", "slot", "worth"):
                    self.assertIn(k, i)
                self.assertIsInstance(i["body"], list)
                self.assertEqual(i["topic"], "idman")
                self.assertRegex(i["slot"], r"^\d\d:\d\d$")
                self.assertTrue(i["link"].startswith("https://"), i["link"])
                if i["worth"]:
                    self.assertLessEqual(len(i["title"]), fa.TITLE_MAX, i["title"])
                    self.assertFalse(i["title"].endswith("."), i["title"])
                    self.assertNotRegex(i["title"] + i["lead"] + " ".join(i["body"]), r"«»|None|\{|\}")
                else:
                    self.assertTrue(i.get("why"), i["key"])
        self.assertGreater(seen, 15)

    def test_sinaq_shows_real_cases_without_network(self):
        fetch = real_pfl()
        md = "\n".join(fa.sinaq(FIX, at("2026-11-10T09:00+04:00"), fetch))
        for head in ("## Premyer Liqa: tur icmalı", "## Premyer Liqa: növbəti tura baxış", "## Premyer Liqa: bombardirlər",
                     "## I Liqa: tur icmalı", "## II Liqa: tur icmalı", "## Azərbaycan Kuboku: cütlər",
                     "## Azərbaycan millisi: oyundan bir gün əvvəl", "## Avrokubok: nəticə"):
            self.assertIn(head, md)
        self.assertIn("### Premyer Liqada 11-ci tur: «Neftçi» fərqi 3 xala çatdırıb, 6 oyunda 13 qol vurulub", md)
        self.assertIn("### Premyer Liqanın bombardirlər yarışında «Neftçi»nin futbolçusu Breno Almeyda 9 qolla öndədir", md)
        self.assertIn("✅ Dərc olunardı", md)
        self.assertIn("⏭ Dərc olunmazdı: tur bitməyib: «Mingəçevir» – «Şahdağ Qusar»", md)
        self.assertEqual(fetch.urls, [PFL + "/seasons?project_id=1", PFL + "/bombarders/list?league_id=52"])

    def test_cli_prints_the_sample(self):
        out = io.StringIO()
        with patch.object(fa, "_real_fetch", return_value=real_pfl()), redirect_stdout(out):
            self.assertEqual(fa.main(["--sinaq", "--root", str(FIX), "--now", "2026-11-10T09:00+04:00"]), 0)
        self.assertIn("## Azərbaycan futbolu: öz xəbərlər (10.11.2026 09:00, Bakı vaxtı)", out.getvalue())

    def test_not_wired_to_the_site(self):
        for path in (ROOT / "updater.py", ROOT / ".github" / "scripts" / "pipeline.sh"):
            self.assertNotIn("oz_futbol_az", path.read_text(encoding="utf-8"))
        self.assertFalse(re.search(r"data/football\.json", (ROOT / "oz_futbol_az.py").read_text(encoding="utf-8").split('"""', 2)[2]))


if __name__ == "__main__":
    unittest.main()
