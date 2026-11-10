"""Xarici futbol və basketbol üzrə öz xəbərlər (oz_futbol_dunya.py): şəkilçilər, turun bitməsi, cədvəl, kuboklar,
avrokubok, böyük klub, NBA, Avroliqa, günlük plan və sınaq. Şəbəkə yoxdur: məlumat sintetikdir və ya
tests/fixtures/oz_futbol_dunya-dakı real fayllardan (main, 2026-11-10) kəsilib."""
import contextlib
import copy
import datetime
import io
import json
import pathlib
import tempfile
import unittest
from unittest.mock import patch

import oz_futbol_dunya as fd

ROOT = pathlib.Path(__file__).resolve().parent.parent
FIX = ROOT / "tests" / "fixtures" / "oz_futbol_dunya"
BAKU = fd.BAKU
UTC = datetime.timezone.utc


def baku(y, mo, d, h=0, mi=0):
    return datetime.datetime(y, mo, d, h, mi, tzinfo=BAKU)


def iso(y, mo, d, h=15, mi=0):
    return datetime.datetime(y, mo, d, h, mi, tzinfo=UTC).isoformat()


def game(date, home, away, hs=None, as_=None, rnd="1", **extra):
    g = {"date": date, "home": home, "away": away, "played": hs is not None, "round": rnd}
    if hs is not None:
        g["hs"], g["as"] = hs, as_
    g.update(extra)
    return g


def official(games, names, deduct=None):
    """Rəsmi cədvəl, testdə ayrıca hesablanır (modulun kodundan asılı deyil)."""
    st = {t: {"team": t, "p": 0, "w": 0, "d": 0, "l": 0, "gf": 0, "ga": 0} for t in names}
    for g in games:
        if not g["played"]:
            continue
        for me, a, b in ((g["home"], g["hs"], g["as"]), (g["away"], g["as"], g["hs"])):
            r = st[me]
            r["p"] += 1
            r["gf"] += a
            r["ga"] += b
            r["w" if a > b else "d" if a == b else "l"] += 1
    rows = list(st.values())
    for r in rows:
        r["pts"] = 3 * r["w"] + r["d"] - (deduct or {}).get(r["team"], 0)
    rows.sort(key=lambda r: (-r["pts"], r["ga"] - r["gf"], -r["gf"]))
    for n, r in enumerate(rows, 1):
        r["pos"] = n
    return rows


def doc(games, names, rows=None, **extra):
    d = {"id": "x", "name": "x", "source": "TheSportsDB", "source_url": "https://www.thesportsdb.com/",
         "url": "https://en.wikipedia.org/wiki/X", "key": "2026", "season": "2026/27", "asof": "2026-11-08",
         "teams": {s: {"name": n} for s, n in names.items()},
         "groups": [{"name": "", "rows": official(games, names) if rows is None else rows}], "games": games}
    d.update(extra)
    return d


@contextlib.contextmanager
def site(files):
    with tempfile.TemporaryDirectory() as tmp:
        base = pathlib.Path(tmp) / "data" / "futbol"
        base.mkdir(parents=True)
        for key, d in files.items():
            (base / f"{key}.json").write_text(json.dumps(d, ensure_ascii=False), encoding="utf-8")
        yield pathlib.Path(tmp)


ENG = {"arsenal": "Arsenal", "chelsea": "Chelsea", "hull-city": "Hull City", "liverpool": "Liverpool"}
R1 = [game(iso(2026, 10, 31), "arsenal", "hull-city", 2, 0, "1"), game(iso(2026, 11, 1, 16, 30), "chelsea", "liverpool", 1, 1, "1")]


def eng(r2, r3=()):
    return fd.prep(doc(R1 + list(r2) + list(r3), ENG))


class SuffixTest(unittest.TestCase):
    def test_pronunciation_endings(self):
        self.assertEqual(fd.acc("Hull City"), "«Hull City»ni")
        self.assertEqual(fd.acc("Bayern"), "«Bayern»i")
        self.assertEqual(fd.acc("Barcelona"), "«Barcelona»nı")
        self.assertEqual(fd.acc("Liverpool"), "«Liverpool»u")
        # Azərbaycan mətbuatında «Mançester Yunayted»: incə sait (data/news.json: “Mançester Yunayted”ə)
        self.assertEqual(fd.acc("Manchester United"), "«Manchester United»i")
        self.assertEqual(fd.dative("Manchester United"), "«Manchester United»ə")
        self.assertEqual(fd.dative("Arsenal"), "«Arsenal»a")
        self.assertEqual(fd.dative("Barcelona"), "«Barcelona»ya")
        self.assertEqual(fd.ablative("Barcelona"), "«Barcelona»dan")
        self.assertEqual(fd.gen("Hull City"), "«Hull City»nin")
        self.assertEqual(fd.gen("Arsenal"), "«Arsenal»ın")
        self.assertEqual(fd.dative("Chelsea"), "«Chelsea»yə")
        self.assertEqual(fd.ablative("Chelsea"), "«Chelsea»dən")
        self.assertEqual(fd.acc("Marseille"), "«Marseille»i")
        self.assertEqual(fd.dative("Fenerbahçe"), "«Fenerbahçe»yə")
        self.assertEqual(fd.acc("Schalke 04"), "«Schalke 04»ü")
        self.assertEqual(fd.dative("Nottingham Forest"), "«Nottingham Forest»ə")
        self.assertEqual(fd.acc("Crystal Palace"), "«Crystal Palace»i")
        self.assertEqual(fd.ablative("Brighton & Hove Albion"), "«Brighton & Hove Albion»dan")

    def test_written_letter_fallback(self):
        self.assertNotIn("Hannover 96", fd.PRON)
        self.assertEqual(fd.acc("Hannover 96"), "«Hannover 96»nı")       # «doxsan altı»
        self.assertEqual(fd.acc("Rot-Weiss Essen"), "«Rot-Weiss Essen»i")
        self.assertEqual(fd.dative("Atlético Ottawa"), "«Atlético Ottawa»ya")
        self.assertEqual(fd.acc("Grimsby"), "«Grimsby»ni")                 # İngilis sonluğu -y oxunuşda «i»
        self.assertEqual(fd.acc("Kəpəz"), "«Kəpəz»i")

    def test_number_endings(self):
        cases = {27: "27-yə", 25: "25-ə", 26: "26-ya", 30: "30-a", 40: "40-a", 20: "20-yə", 6: "6-ya", 100: "100-ə", 9: "9-a"}
        for n, want in cases.items():
            self.assertEqual(fd.num_dat(n), want)

    def test_map_covers_fixture_and_site_teams(self):
        names = set()
        for f in FIX.glob("data/futbol/*.json"):
            names |= {t["name"] for t in json.loads(f.read_text(encoding="utf-8"))["teams"].values()}
        self.assertEqual(sorted(n for n in names if n not in fd.PRON), [])
        live = ROOT / "site" / "data" / "futbol"          # CI-da main-in məlumatı burada olur
        if not live.is_dir():
            self.skipTest("site/ yoxdur (yalnız CI-da)")
        missing = []
        for key in (*fd.TOP, "cl", "al", "kl"):
            path = live / f"{key}.json"
            if path.exists():
                missing += [f"{key}: {t.get('name')}" for t in json.loads(path.read_text(encoding="utf-8"))["teams"].values()
                            if t.get("name") not in fd.PRON]
        self.assertEqual(missing, [])


class TimeTest(unittest.TestCase):
    def test_slots(self):
        self.assertEqual(fd._slot_after(datetime.datetime(2026, 11, 8, 19, 15, tzinfo=UTC)), baku(2026, 11, 8, 23, 15))
        self.assertEqual(fd._slot_after(datetime.datetime(2026, 11, 8, 19, 40, tzinfo=UTC)), baku(2026, 11, 9, 8, 30))
        self.assertEqual(fd._slot_after(datetime.datetime(2026, 11, 8, 22, 0, tzinfo=UTC)), baku(2026, 11, 9, 8, 30))
        self.assertEqual(fd._slot_after(baku(2026, 11, 8, 10, 7)), baku(2026, 11, 8, 10, 15))
        self.assertEqual(fd._morning(datetime.datetime(2026, 11, 4, 20, 0, tzinfo=UTC)), baku(2026, 11, 5, 8, 0))
        self.assertEqual(fd._morning(datetime.datetime(2026, 11, 3, 17, 45, tzinfo=UTC)), baku(2026, 11, 4, 8, 0))
        self.assertEqual(fd._days_loc([datetime.datetime(2026, 11, 6, 20, 0, tzinfo=UTC),
                                       datetime.datetime(2026, 11, 8, 16, 30, tzinfo=UTC)]), "7–8 noyabrda")
        self.assertEqual(fd._days_loc([datetime.datetime(2026, 10, 31, 15, 0, tzinfo=UTC),
                                       datetime.datetime(2026, 11, 2, 15, 0, tzinfo=UTC)]), "31 oktyabr – 2 noyabrda")


class RoundTest(unittest.TestCase):
    """Turun bitməsi: natamam tur, təxirə salınmış oyun, şərti başlama vaxtı, bərabər xal, məlumat yoxdur."""
    NOW = baku(2026, 11, 9, 12, 0)

    def test_complete_round(self):
        lg = eng([game(iso(2026, 11, 7), "hull-city", "chelsea", 1, 3, "2"),
                  game(iso(2026, 11, 8, 16, 30), "liverpool", "arsenal", 0, 1, "2")])
        item, why = fd.round_item("ingiltere", lg, "2", self.NOW)
        self.assertEqual(why, "")
        self.assertEqual(item["title"], "İngiltərə Premyer Liqasında 2-ci tur: lider «Arsenal» «Liverpool»u 1:0 hesabı ilə məğlub edib")
        self.assertIn("İngiltərə Premyer Liqasının 2-ci turu 7–8 noyabrda keçirilib.", item["lead"])
        self.assertIn("Lider «Arsenal» səfərdə «Liverpool»u 1:0 hesabı ilə məğlub edib və xallarının sayını 6-ya çatdırıb.", item["lead"])
        self.assertIn("«Arsenal» ikinci yerdəki «Chelsea»dən 2 xal öndədir.", item["lead"])
        self.assertIn("Turun 2 oyununda 5 qol vurulub.", item["lead"])
        self.assertIn("«Hull City» – «Chelsea» 1:3", item["body"])
        self.assertEqual((item["key"], item["slot"], item["date"], item["topic"], item["worth"]),
                         ("liqa-ingiltere-2026-t2", "23:15", "2026-11-08", "idman", True))
        self.assertTrue(item["list"])
        self.assertEqual((item["credit"], item["link"]), ("TheSportsDB", "https://www.thesportsdb.com/"))

    def test_incomplete_round_is_not_news(self):
        lg = eng([game(iso(2026, 11, 7), "hull-city", "chelsea", 1, 3, "2"),
                  game(iso(2026, 11, 8, 16, 30), "liverpool", "arsenal", rnd="2")])
        item, why = fd.round_item("ingiltere", lg, "2", self.NOW)
        self.assertIsNone(item)
        self.assertIn("tur başa çatmayıb", why)
        self.assertIn("«Liverpool» – «Arsenal»", why)

    def test_played_flag_from_the_future_counts_as_unplayed(self):
        lg = eng([game(iso(2026, 11, 7), "hull-city", "chelsea", 1, 3, "2"),
                  game(iso(2026, 11, 8, 16, 30), "liverpool", "arsenal", 0, 1, "2")])
        item, why = fd.round_item("ingiltere", lg, "2", baku(2026, 11, 8, 12, 0))
        self.assertIsNone(item)
        self.assertIn("başa çatmayıb", why)

    def test_postponed_game_is_named_and_round_completes(self):
        lg = eng([game(iso(2026, 11, 7), "hull-city", "chelsea", 1, 3, "2"),
                  game(iso(2026, 11, 20, 16, 30), "liverpool", "arsenal", rnd="2")])
        item, why = fd.round_item("ingiltere", lg, "2", self.NOW)
        self.assertEqual(why, "")
        self.assertIn("«Liverpool» – «Arsenal» oyunu hələ keçirilməyib.", item["body"])
        self.assertIn("Turda keçirilən 1 oyunda 4 qol vurulub.", item["lead"])
        self.assertEqual(item["title"], "İngiltərə Premyer Liqasında 2-ci tur: «Chelsea» liderliyə yüksəlib")
        self.assertIn("Əvvəlki lider «Arsenal» bu turda oynamayıb və 3 xalla 2-ci yerə düşüb.", item["lead"])
        self.assertEqual((item["slot"], item["date"]), ("21:45", "2026-11-07"))

    def test_placeholder_kickoffs_keep_the_round_open(self):
        r2 = [game(iso(2026, 11, 7), "hull-city", "chelsea", 1, 3, "2"), game(iso(2026, 11, 8, 16, 30), "liverpool", "arsenal", 0, 1, "2")]
        r3 = [game(iso(2026, 11, 22, 16, 0), "arsenal", "chelsea", rnd="3"), game(iso(2026, 11, 22, 16, 0), "hull-city", "liverpool", rnd="3")]
        lg = eng(r2, r3)
        for now in (baku(2026, 11, 22, 23, 0), baku(2026, 11, 30, 12, 0)):
            item, why = fd.round_item("ingiltere", lg, "3", now)
            self.assertIsNone(item)
            self.assertIn("tur başa çatmayıb", why)
        with site({"ingiltere": doc(R1 + r2 + r3, ENG)}) as root:
            keys = [i["key"] for i in fd.items(root, baku(2026, 11, 23, 9, 0))]
        self.assertNotIn("liqa-ingiltere-2026-t3", keys)

    def test_tie_at_the_top(self):
        lg = eng([game(iso(2026, 11, 7), "hull-city", "chelsea", 0, 2, "2"),
                  game(iso(2026, 11, 8, 16, 30), "arsenal", "liverpool", 1, 1, "2")])
        item, _ = fd.round_item("ingiltere", lg, "2", self.NOW)
        self.assertEqual(item["title"], "İngiltərə Premyer Liqasında 2-ci tur: «Arsenal» və «Chelsea» 4 xalla cədvəlin başındadır")
        self.assertIn("Hər iki komandanın 4 xalı var və onlar cədvəlin başındadır.", item["lead"])
        self.assertNotIn("fərq", item["title"])
        self.assertNotIn("öndədir", item["lead"])

    def test_missing_data_gives_no_item(self):
        with site({}) as root:
            self.assertEqual(fd.items(root, self.NOW), [])
            self.assertIn("> data/futbol faylları tapılmadı: xəbər yoxdur.", fd.sinaq(root, self.NOW))
        with site({"ingiltere": {"teams": {}, "groups": []}}) as root:   # games yoxdur: fayl sayılmır
            self.assertEqual(fd.load(root), {})
        lg = fd.prep(doc([], ENG))
        self.assertEqual(fd.round_item("ingiltere", lg, "5", self.NOW), (None, "turun oyunları və ya tarixləri yoxdur"))
        lg = fd.prep(doc([game("", "arsenal", "chelsea", 1, 0, "1")], ENG))
        self.assertIsNone(fd.round_item("ingiltere", lg, "1", self.NOW)[0])

    def test_official_table_resorted_and_deduction_kept(self):
        tr = {"kasimpasa": "Kasımpaşa", "besiktas": "Beşiktaş", "galatasaray": "Galatasaray", "goztepe": "Göztepe"}
        games = [game(iso(2026, 10, 31), "besiktas", "goztepe", 2, 0, "1"), game(iso(2026, 10, 31), "kasimpasa", "galatasaray", 1, 1, "1"),
                 game(iso(2026, 11, 7), "besiktas", "galatasaray", 1, 0, "2"), game(iso(2026, 11, 7), "kasimpasa", "goztepe", 0, 0, "2")]
        rows = official(games, tr)
        bad = sorted(rows, key=lambda r: r["team"] != "kasimpasa")           # Kasımpaşa (2 xal) Beşiktaşdan (6) yuxarıda
        for n, r in enumerate(bad, 1):
            r["pos"] = n
        lg = fd.prep(doc(games, tr, rows=bad))
        table, official_order = fd.table(lg, self.NOW, self.NOW)
        self.assertTrue(official_order)
        self.assertEqual([r["team"] for r in table[:2]], ["besiktas", "kasimpasa"])
        lg = fd.prep(doc(games, tr, rows=official(games, tr, deduct={"besiktas": 5})))   # xal çıxılıb: 6 - 5 = 1
        table, official_order = fd.table(lg, self.NOW, self.NOW)
        self.assertTrue(official_order)
        self.assertEqual(table[0]["team"], "kasimpasa")
        self.assertEqual(fd._row(table, "besiktas")["pts"], 1)

    def test_html_entities_are_decoded(self):
        lg = fd.prep(doc(R1, {**ENG, "arsenal": "Brighton &amp; Hove Albion"}))
        self.assertEqual(lg["names"]["arsenal"], "Brighton & Hove Albion")


class RealEnglandTest(unittest.TestCase):
    """Real məlumat (main, 2026-11-08): Premyer Liqanın 10-cu turu."""
    def test_round_10(self):
        items = fd.items(FIX, baku(2026, 11, 8, 23, 30))
        item = next(i for i in items if i["key"] == "liqa-ingiltere-2026-t10")
        self.assertEqual(item["title"], "İngiltərə Premyer Liqasında 10-cu tur: «Arsenal» fərqi 5 xala çatdırıb")
        for part in ("İngiltərə Premyer Liqasının 10-cu turu 7–8 noyabrda keçirilib.",
                     "Lider «Arsenal» doğma meydanda «Hull City»ni 1:0 hesabı ilə məğlub edib və xallarının sayını 27-yə çatdırıb.",
                     "«Arsenal» ikinci yerdəki «Brighton & Hove Albion»dan 5 xal öndədir.",
                     "«Brentford»u 2:0 hesabı ilə məğlub edən «Brighton & Hove Albion» 22 xalla 2-ci yerə yüksəlib",
                     "«Nottingham Forest»ə 1:3 hesabı ilə uduzan «Manchester City» 21 xalla 3-cü yerə düşüb",
                     "«Crystal Palace»i 3:1 hesabı ilə məğlub edən «Liverpool» 18 xalla 4-cü yerə yüksəlib",
                     "Turun 10 oyununda 30 qol vurulub, ən məhsuldar görüşdə «Manchester United» ilə «Aston Villa» 4:4 hesabı ilə heç-heçə edib."):
            self.assertIn(part, item["lead"])
        self.assertIn("«Arsenal» – «Hull City» 1:0", item["body"])
        self.assertIn("Ev sahibləri 6, qonaqlar 2 oyunda qalib gəlib, 2 oyun heç-heçə bitib.", item["body"])
        self.assertIn("Cədvəlin başı: «Arsenal» — 27 xal, «Brighton & Hove Albion» — 22 xal, «Manchester City» — 21 xal, «Liverpool» — 18 xal.",
                      item["body"])
        self.assertEqual((item["slot"], item["date"]), ("23:15", "2026-11-08"))
        self.assertLessEqual(len(item["title"]), 110)
        text = json.dumps(item, ensure_ascii=False)
        self.assertNotIn("&amp;", text)
        self.assertEqual(fd.items(FIX, baku(2026, 11, 8, 23, 30)), items)          # deterministik

    def test_stale_round_is_not_published_later(self):
        self.assertNotIn("liqa-ingiltere-2026-t10", [i["key"] for i in fd.items(FIX, baku(2026, 11, 10, 18, 0))])

    def test_big_club_game_inside_a_same_day_summary_is_skipped(self):
        evs = {e["key"]: e for e in fd.events(fd.load(FIX))}
        self.assertNotIn("why", evs["klub-ingiltere-2026-arsenal-hull-city"])             # 7 noyabr, icmal 8 noyabrda
        self.assertEqual(evs["klub-ingiltere-2026-arsenal-hull-city"]["slot"].date(), datetime.date(2026, 11, 7))
        self.assertIn("why", evs["klub-ingiltere-2026-sunderland-chelsea"])               # 8 noyabr, icmal da 8 noyabrda
        item, _ = evs["klub-ingiltere-2026-arsenal-hull-city"]["make"](baku(2026, 11, 7, 21, 45))
        self.assertEqual(item["title"], "«Arsenal» İngiltərə Premyer Liqasında «Hull City»ni 1:0 hesabı ilə məğlub edib")
        self.assertTrue(item["lead"].startswith("İngiltərə Premyer Liqasının 10-cu turunda «Arsenal» 7 noyabrda doğma meydanda "
                                                "«Hull City»ni 1:0 hesabı ilə məğlub edib."))
        self.assertEqual(item["body"], ["Görüş «Emirates Stadium»da keçirilib."])


class RealEuropeTest(unittest.TestCase):
    """Real məlumat: Çempionlar Liqasının 4-cü turu (3–4 noyabr), Liqa Kubokunun 4-cü mərhələsi, Avroliqanın 10-cu turu."""
    def setUp(self):
        self.data = fd.load(FIX)

    def test_champions_league_matchday_4(self):
        item, why = fd.night_item("cl", self.data["cl"], "4", baku(2026, 11, 5, 8, 0))
        self.assertEqual(why, "")
        self.assertEqual(item["title"], "Çempionlar Liqasında 4-cü tur: «Fenerbahçe» «Liverpool»u 3:2 hesabı ilə məğlub edib")
        for part in ("Çempionlar Liqasının liqa mərhələsinin 4-cü turu başa çatıb.",
                     "«Paris Saint-Germain» və «Real Madrid» 12 xalla cədvəlin başındadır: hər iki komanda 4 oyunun hamısında qalib gəlib.",
                     "Türkiyə klublarından «Galatasaray» doğma meydanda «VfB Stuttgart»ı 2:0 hesabı ilə məğlub edib və 6 xalla 18-ci yerdədir.",
                     "«Fenerbahçe» doğma meydanda «Liverpool»u 3:2 hesabı ilə məğlub edib və 5 xalla 19-cu yerdədir.",
                     "Turun ən böyük hesablı qələbəsini «Como» qazanıb: komanda səfərdə «Lens»ı 9:1 hesabı ilə məğlub edib.",
                     "Turun 18 oyununda 70 qol vurulub."):
            self.assertIn(part, item["lead"])
        text = "\n".join([item["title"], item["lead"], *item["body"]])
        self.assertNotIn("Sabah", text)                       # «Sabah»ı başqa modul yazır
        self.assertEqual(len(item["body"]), 18)               # 17 nəticə (Sabahın oyunu yoxdur) + cədvəl
        self.assertEqual((item["key"], item["slot"], item["date"]), ("avrokubok-cl-2026-t4", "08:00", "2026-11-05"))
        self.assertEqual(item["credit"], "OpenLigaDB (ODbL 1.0)")

    def test_tuesday_big_club_game_gets_its_own_item_wednesday_one_does_not(self):
        evs = {e["key"]: e for e in fd.events(self.data)}
        gala = evs["klub-cl-2026-galatasaray-vfb-stuttgart"]
        self.assertNotIn("why", gala)
        self.assertEqual(gala["slot"], baku(2026, 11, 4, 8, 30))
        self.assertIn("why", evs["klub-cl-2026-fenerbahce-liverpool"])
        item, _ = gala["make"](gala["slot"])
        self.assertEqual(item["title"], "«Galatasaray» Çempionlar Liqasında «VfB Stuttgart»ı 2:0 hesabı ilə məğlub edib")
        self.assertTrue(item["lead"].startswith("Çempionlar Liqasının liqa mərhələsinin 4-cü turunda «Galatasaray» 3 noyabrda "
                                                "doğma meydanda «VfB Stuttgart»ı 2:0 hesabı ilə məğlub edib."))
        keep, cut = fd.day_plan(fd.events(self.data), datetime.date(2026, 11, 4))
        clubs = sorted(e["key"] for e in keep if e["kind"] == "klub-oyunu")
        # 6 oyundan 3-ü: əvvəl Türkiyə klubu, sonra «Barcelona», sonra fayldakı ilk oyun
        self.assertEqual(clubs, ["klub-cl-2026-barcelona-aston-villa", "klub-cl-2026-feyenoord-inter-milan",
                                 "klub-cl-2026-galatasaray-vfb-stuttgart"])
        self.assertEqual(len([e for e in cut if e["kind"] == "klub-oyunu"]), 3)

    def test_league_cup_round_4(self):
        item, why = fd.cup_item("liqa-kuboku", self.data["liqa-kuboku"], "4-cü mərhələ", baku(2026, 10, 30, 8, 30))
        self.assertEqual(why, "")
        self.assertEqual(item["title"], "İngiltərə Liqa Kubokunun 4-cü mərhələsi: «Arsenal» penaltilər seriyasında «Fleetwood Town»a uduzub")
        for part in ("İngiltərə Liqa Kubokunun 4-cü mərhələsinin oyunları 27–29 oktyabrda keçirilib.",
                     "«Arsenal» səfərdə «Fleetwood Town» ilə 1:1 hesabı ilə heç-heçə edib, penaltilər seriyasında isə 3:5 hesabı ilə "
                     "uduzub və mübarizədən kənarlaşıb.",
                     "«Liverpool» doğma meydanda «Chelsea» ilə 1:1 hesabı ilə heç-heçə edib, penaltilər seriyasında isə 6:5 hesabı ilə "
                     "qalib gəlib və 1/4 finala yüksəlib.",
                     "«Manchester City» doğma meydanda «Brighton & Hove Albion» ilə 2:2 hesabı ilə heç-heçə edib, penaltilər seriyasında "
                     "isə 4:3 hesabı ilə qalib gəlib və 1/4 finala yüksəlib."):
            self.assertIn(part, item["lead"])
        self.assertIn("«Fleetwood Town» – «Arsenal» 1:1 (penaltilər seriyası 5:3)", item["body"])
        self.assertTrue(item["body"][-1].startswith("1/4 finalın cütləri: «Manchester City» – «Bradford City», "))
        self.assertEqual((item["key"], item["slot"], item["date"]), ("kubok-liqa-kuboku-2026-4-cu-merhele", "08:30", "2026-10-30"))
        self.assertEqual(item["credit"], "Vikipediya")

    def test_cup_stage_rules(self):
        cup = {"a": "Accrington Stanley", "b": "Barnet", "c": "Crewe Alexandra", "d": "Doncaster Rovers", "arsenal": "Arsenal"}
        games = [game(iso(2026, 11, 8), "a", "b", 2, 1, "1-ci mərhələ"), game(iso(2026, 11, 8), "c", "d", 0, 3, "1-ci mərhələ")]
        lg = fd.prep(doc(games, cup, rows=[]))
        self.assertEqual(fd.cup_item("ingiltere-kuboku", lg, "1-ci mərhələ", baku(2026, 11, 9, 9, 0)), (None, "böyük klub oynamayıb"))
        games = [game(iso(2026, 11, 8), "a", "arsenal", 0, 3, "1-ci mərhələ"), game(iso(2026, 11, 12), "c", "d", rnd="1-ci mərhələ")]
        lg = fd.prep(doc(games, cup, rows=[]))
        item, why = fd.cup_item("ingiltere-kuboku", lg, "1-ci mərhələ", baku(2026, 11, 9, 9, 0))
        self.assertIsNone(item)
        self.assertIn("mərhələ başa çatmayıb", why)
        lg = fd.prep(doc([game("", "a", "arsenal", rnd="1/8 final")], cup, rows=[]))
        self.assertIsNone(fd.cup_item("ingiltere-kuboku", lg, "1/8 final", baku(2026, 11, 9, 9, 0))[0])

    def test_euroleague_round_10(self):
        lg = self.data["avroliqa"]
        item, why = fd.euro_item(lg, "10", baku(2026, 11, 7, 8, 30))
        self.assertEqual(why, "")
        self.assertEqual(item["title"], "Avroliqada 10-cu tur: «Fenerbahçe Tarfin» «Kosner Baskonia»nı 84:65 hesabı ilə məğlub edib")
        self.assertIn("Basketbol üzrə Avroliqanın 10-cu turunda lider «Panathinaikos AKTOR» səfərdə «Real Madrid»i 115:112 hesabı ilə "
                      "məğlub edib və 8 qələbə, 2 məğlubiyyətlə birinci yerdədir.", item["lead"])
        self.assertIn("«Beşiktaş» doğma meydanda «Žalgiris»ə 69:83 hesabı ilə uduzub", item["lead"])
        self.assertNotIn("oyunda", item["lead"])           # faylda turun bütün oyunları yoxdur: say yazılmır
        stale = copy.deepcopy(lg["doc"])
        stale["groups"][0]["rows"][5]["l"] -= 1
        self.assertEqual(fd.euro_item(fd.prep(stale), "10", baku(2026, 11, 7, 8, 30))[1], "cədvəl bu turu hələ saymayıb (məlumat təzə deyil)")
        old = copy.deepcopy(lg["doc"])
        old["asof"] = "2026-11-05"
        self.assertEqual(fd.euro_item(fd.prep(old), "10", baku(2026, 11, 7, 8, 30))[1], "məlumat təzə deyil")


class RealNbaTest(unittest.TestCase):
    def setUp(self):
        self.lg = fd.load(FIX)["nba"]

    def test_us_day_8_november(self):
        item, why = fd.nba_item(self.lg, datetime.date(2026, 11, 8), baku(2026, 11, 9, 18, 0))
        self.assertEqual(why, "")
        self.assertEqual(item["title"], "NBA-da «Los Angeles Lakers» ardıcıl 5-ci qələbəsini qazanıb")
        for part in ("NBA-da ABŞ vaxtı ilə 8 noyabrda 7 oyun keçirilib.",
                     "«Philadelphia 76ers» səfərdə «Chicago Bulls»u 127:121 hesabı ilə məğlub edib və 9 qələbə, 2 məğlubiyyətlə "
                     "Şərq konfransının lideridir.",
                     "«Los Angeles Lakers» səfərdə «Detroit Pistons»u 121:116 hesabı ilə məğlub edib və 9 qələbə, 2 məğlubiyyətlə "
                     "Qərb konfransının lideridir.",
                     "Bu, «Los Angeles Lakers»in ardıcıl 5-ci qələbəsidir.",
                     "Günün ən böyük fərqli qələbəsini «Dallas Mavericks» qazanıb: komanda doğma meydanda «Brooklyn Nets»i 130:93 "
                     "hesabı ilə üstələyib."):
            self.assertIn(part, item["lead"])
        self.assertEqual(len(item["body"]), 8)
        self.assertEqual((item["key"], item["slot"], item["date"], item["credit"]), ("nba-2026-11-08", "09:00", "2026-11-09", "Vikipediya"))

    def test_unfinished_day_and_odd_scores_wait(self):
        item, why = fd.nba_item(self.lg, datetime.date(2026, 11, 9), baku(2026, 11, 10, 9, 0))
        self.assertIsNone(item)
        self.assertIn("hamısı bitməyib", why)
        d = copy.deepcopy(self.lg["doc"])
        g = next(x for x in d["games"] if x["date"].startswith("2026-11-08"))
        g["as"] = g["hs"]
        item, why = fd.nba_item(fd.prep(d), datetime.date(2026, 11, 8), baku(2026, 11, 9, 18, 0))
        self.assertIsNone(item)
        self.assertIn("şübhəli hesab", why)
        self.assertEqual(fd.nba_item(self.lg, datetime.date(2026, 11, 3), baku(2026, 11, 4, 9, 0)), (None, "həmin gün oyun yoxdur"))


NED = {"psv-eindhoven": "PSV Eindhoven", "feyenoord": "Feyenoord", "utrecht": "Utrecht", "ajax": "Ajax", "twente": "Twente",
       "heerenveen": "Heerenveen"}
BEL = {"club-brugge": "Club Brugge", "anderlecht": "Anderlecht", "gent": "Gent", "genk": "Genk"}
POR = {"porto": "Porto", "benfica": "Benfica", "braga": "Braga", "sporting-cp": "Sporting CP"}


def other_files():
    ned = [game(iso(2026, 10, 31), "feyenoord", "utrecht", 1, 0, "1"), game(iso(2026, 10, 31), "psv-eindhoven", "ajax", 0, 0, "1"),
           game(iso(2026, 11, 1), "twente", "heerenveen", 0, 0, "1"),
           game(iso(2026, 11, 7), "psv-eindhoven", "twente", 2, 0, "2"), game(iso(2026, 11, 8), "utrecht", "feyenoord", 1, 0, "2"),
           game(iso(2026, 11, 8, 16, 30), "ajax", "heerenveen", 0, 0, "2")]
    bel = [game(iso(2026, 10, 31), "club-brugge", "anderlecht", 1, 0, "1"), game(iso(2026, 11, 1), "gent", "genk", 0, 0, "1"),
           game(iso(2026, 11, 7), "genk", "club-brugge", 1, 2, "2"), game(iso(2026, 11, 8), "anderlecht", "gent", 1, 0, "2")]
    por = [game(iso(2026, 10, 31), "porto", "braga", 1, 0, "1"), game(iso(2026, 11, 1), "benfica", "sporting-cp", 2, 2, "1"),
           game(iso(2026, 11, 7), "braga", "sporting-cp", 0, 1, "2"), game(iso(2026, 11, 8, 16, 30), "porto", "benfica", rnd="2")]
    return {"hollandiya": doc(ned, NED), "belcika": doc(bel, BEL), "portuqaliya": doc(por, POR)}


class OtherLeaguesTest(unittest.TestCase):
    def test_one_combined_item_a_day(self):
        with site(other_files()) as root:
            evs = {e["key"]: e for e in fd.events(fd.load(root))}
            self.assertEqual(sorted(k for k in evs if k.startswith("liqa-diger")), ["liqa-diger-2026-11-02", "liqa-diger-2026-11-09"])
            ev = evs["liqa-diger-2026-11-09"]
            self.assertEqual(ev["slot"], baku(2026, 11, 9, 10, 30))
            item, why = ev["make"](ev["slot"])
            items = fd.items(root, baku(2026, 11, 9, 11, 0))
        self.assertEqual(item["title"], "Avropa çempionatlarında həftə sonu: «PSV Eindhoven» Hollandiyada liderliyə yüksəlib")
        self.assertTrue(item["lead"].startswith("2 çempionatda turlar başa çatıb: Hollandiya (2-ci tur) və Belçika (2-ci tur). "
                                                "Hollandiyada «PSV Eindhoven» doğma meydanda «Twente»ni 2:0 hesabı ilə məğlub edib "
                                                "və 4 xalla liderliyə yüksəlib, əvvəlki lider «Feyenoord» 3 xalla 2-ci yerdədir."))
        self.assertEqual(item["body"][1], "Belçika (Pro Liqa), 2-ci tur: lider «Club Brugge» səfərdə «Genk»i 2:1 hesabı ilə məğlub "
                                          "edib və 6 xalla birinci yerdədir, ikinci yerdəki «Anderlecht»dən 3 xal öndədir. 2 oyunda 4 qol vurulub.")
        self.assertEqual(len(item["body"]), 2)
        self.assertIn("Portuqaliya, 2-ci tur: tur başa çatmayıb: «Porto» – «Benfica» oyununun nəticəsi yoxdur", item["skipped"])
        self.assertEqual([i["key"] for i in items if i["kind"] == "liqa-diger"], ["liqa-diger-2026-11-09"])


ESP = {"barcelona": "Barcelona", "real-madrid": "Real Madrid"}


def leader_files():
    esp = [game(iso(2026, 10, 10 + 7 * n), "barcelona", "real-madrid", 2, 1, str(n + 1)) for n in range(4)]
    esp.append(game(iso(2026, 11, 7), "barcelona", "real-madrid", 3, 0, "5"))
    esp.append(game(iso(2026, 11, 22), "real-madrid", "barcelona", rnd="6"))      # fasilədən sonrakı oyun (hələ oynanmayıb)
    return {"ingiltere": doc(R1 + [game(iso(2026, 11, 7), "hull-city", "chelsea", 1, 3, "2"),
                                   game(iso(2026, 11, 8, 16, 30), "liverpool", "arsenal", 0, 1, "2")], ENG),
            "ispaniya": doc(esp, ESP)}


class LeadersTest(unittest.TestCase):
    def test_monday_leaders_and_break_week(self):
        with patch.object(fd, "LEADERS_MIN", 2), site(leader_files()) as root:
            data = fd.load(root)
            item, why = fd.leaders_item(data, datetime.date(2026, 11, 9), baku(2026, 11, 9, 9, 0))
            self.assertEqual(why, "")
            self.assertEqual(item["title"], "Avropa çempionatlarında liderlər: «Barcelona» 5 oyunda 5 qələbə qazanıb")
            self.assertEqual(item["lead"], "Cədvəllərin hazırkı vəziyyətinə görə İngiltərədə «Arsenal» (6 xal), İspaniyada isə "
                                           "«Barcelona» (15) cədvəlin başındadır. «Barcelona» hələ məğlub olmayıb.")
            self.assertIn("İngiltərə: «Arsenal» — 6 xal, ikinci yerdəki «Chelsea»dən 2 xal öndədir.", item["body"])
            self.assertIn("Ardıcıl qələbə seriyaları: «Barcelona» — 5 oyun.", item["body"])
            self.assertEqual((item["key"], item["slot"]), ("liqa-liderler-2026-11-09", "09:00"))
            item, why = fd.leaders_item(data, datetime.date(2026, 11, 16), baku(2026, 11, 16, 9, 0))
            self.assertIsNone(item)
            self.assertIn("beynəlxalq fasilə", why)
            evs = {e["key"]: e for e in fd.events(data)}
            self.assertIn("why", evs["liqa-liderler-2026-11-16"])
            self.assertNotIn("why", evs["liqa-liderler-2026-11-09"])


class PlanTest(unittest.TestCase):
    def fake(self, kind, key, hour, rank=None):
        e = {"kind": kind, "key": key, "slot": baku(2026, 11, 9, hour), "prio": fd.PRIO[kind], "make": lambda now: (None, "")}
        if rank is not None:
            e["rank"] = rank
        return e

    def test_daily_caps(self):
        evs = [self.fake("liqa-tur", f"t{n}", 8) for n in range(6)]
        evs += [self.fake("nba", "nba", 9), self.fake("liqa-diger", "diger", 10), self.fake("kubok", "kubok", 11),
                self.fake("liqa-liderler", "liderler", 9)]
        evs += [self.fake("klub-oyunu", f"k{n}", 20, rank=r) for n, r in enumerate([(2, 1), (0, 2), (1, 3), (2, 0), (0, 5)])]
        evs.append(dict(self.fake("klub-oyunu", "covered", 21, rank=(0, 0)), why="icmalda"))
        keep, cut = fd.day_plan(evs, datetime.date(2026, 11, 9))
        self.assertEqual(len(keep), fd.DAILY_CAP)
        self.assertEqual([e["key"] for e in keep][:7], [f"t{n}" for n in range(6)] + ["nba"])
        clubs = [e["key"] for e in keep + cut if e["kind"] == "klub-oyunu"]
        self.assertNotIn("covered", clubs)
        self.assertEqual(sorted(e["key"] for e in keep + cut if e["kind"] == "klub-oyunu" and e not in cut[-2:]), ["k1", "k2", "k4"])
        self.assertEqual(sorted(e["key"] for e in cut[-2:]), ["k0", "k3"])
        self.assertEqual(fd.day_plan(evs, datetime.date(2026, 11, 10)), ([], []))


class SinaqTest(unittest.TestCase):
    NOW = baku(2026, 11, 10, 7, 0)

    def test_samples(self):
        md = "\n".join(fd.sinaq(FIX, self.NOW))
        self.assertIn("## Xarici futbol və basketbol (oz_futbol_dunya.py)", md)
        self.assertIn("### İngiltərə Premyer Liqasında 10-cu tur: «Arsenal» fərqi 5 xala çatdırıb", md)
        self.assertIn("### Çempionlar Liqasında 4-cü tur: «Fenerbahçe» «Liverpool»u 3:2 hesabı ilə məğlub edib", md)
        self.assertIn("### NBA-da «Los Angeles Lakers» ardıcıl 5-ci qələbəsini qazanıb", md)
        self.assertIn("### Avroliqada 10-cu tur: «Fenerbahçe Tarfin» «Kosner Baskonia»nı 84:65 hesabı ilə məğlub edib", md)
        self.assertGreaterEqual(md.count("✅ Dərc olunardı"), 5)
        self.assertIn("⏭ Dərc olunmazdı: oyun həmin gün dərc olunan tur icmalındadır", md)
        self.assertNotIn("&amp;", md)
        for line in md.splitlines():
            if line.startswith(("✅", "⏭")):
                self.assertTrue(line == "✅ Dərc olunardı" or line.startswith("⏭ Dərc olunmazdı: "), line)

    def test_cli_and_no_network(self):
        out = io.StringIO()
        with patch("sys.stdout", out):
            self.assertEqual(fd.main(["--sinaq", "--root", str(FIX), "--now", "2026-11-10T07:00+04:00"]), 0)
        self.assertIn("Xarici futbol", out.getvalue())

        def boom(*a, **k):
            raise AssertionError("şəbəkə sorğusu olmamalıdır")
        self.assertIsInstance(fd.items(FIX, self.NOW, fetch=boom), list)
        self.assertIsInstance(fd.sinaq(FIX, self.NOW, fetch=boom), list)


class SafetyTest(unittest.TestCase):
    def test_leadership_is_never_published(self):
        self.assertFalse(fd.leader_free("Prezident İlham Əliyev oyunu izləyib"))
        self.assertTrue(fd.leader_free("«Arsenal» «Hull City»ni 1:0 hesabı ilə məğlub edib"))
        self.assertEqual(fd._finish({"title": "Prezident İlham Əliyev stadionda", "lead": "", "body": []}),
                         (None, "mətndə rəhbərliyin adı keçir"))

    def test_not_on_the_site(self):
        """Sahib 2026-11-10: faza 1 sınaq budağındadır. Sayt bu modulu çağırmır."""
        self.assertNotIn("oz_futbol_dunya", (ROOT / "updater.py").read_text(encoding="utf-8"))
        self.assertNotIn("oz_futbol_dunya", (ROOT / ".github" / "scripts" / "pipeline.sh").read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
