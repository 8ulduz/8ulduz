"""Formula 1, cüdo və UEFA əmsalları üzrə öz xəbərlər (oz_idman2.py): şəkilçilər, təqvimlər, F1 (ön baxış,
kvalifikasiya, yarış), cüdo medalları, UEFA cədvəli, pəncərələr, done, sorğu həddi, sınaq və CLI.
Şəbəkə yoxdur: saxta fetch tests/fixtures/oz_idman2-dəki real cavabları (Jolpica, IJF, UEFA; 2026-11-10) qaytarır."""
import contextlib
import copy
import datetime
import io
import json
import pathlib
import unittest
import urllib.parse
from unittest.mock import patch

import oz_idman2 as m

ROOT = pathlib.Path(__file__).resolve().parent.parent
FIX = ROOT / "tests" / "fixtures" / "oz_idman2"
SITE = FIX / "site"
BAKU = m.BAKU
UTC = datetime.timezone.utc
REQUIRED = ("kind", "key", "title", "lead", "body", "credit", "link", "topic", "slot", "worth")


def baku(y, mo, d, h=0, mi=0):
    return datetime.datetime(y, mo, d, h, mi, tzinfo=BAKU)


def utc(y, mo, d, h=0, mi=0):
    return datetime.datetime(y, mo, d, h, mi, tzinfo=UTC)


def load(name):
    return json.loads((FIX / name).read_text(encoding="utf-8"))


def raw(doc):
    return json.dumps(doc).encode("ascii")


def fixture_name(url):
    """Sorğunun ünvanı -> fixture faylının adı."""
    if url.startswith(m.F1_API + "/"):
        tail = url[len(m.F1_API) + 1:].split("?")[0]
        if tail.startswith("circuits/baku"):
            return "f1-circuits-baku-races.json"
        return "f1-" + tail.replace("/", "-")
    if url.startswith(m.IJF_API):
        q = urllib.parse.parse_qs(urllib.parse.urlsplit(url).query)
        if q["params[action]"] == ["competition.results"]:
            return "ijf-{}-results.json".format(q["params[id_competition]"][0])
        return "ijf-list-{}.json".format(q["params[year]"][0])
    if url.startswith("https://comp.uefa.com/"):
        return "uefa-{}.json".format(url.rsplit("=", 1)[1])
    raise AssertionError("gözlənilməyən sorğu: " + url)


class Fake:
    """Saxta fetch: fixture qaytarır və sorğuları sayır. replace: {fayl adı: bytes və ya Exception};
    fail: hər sorğu xəta verir; fail_first: hər ünvanın ilk sorğusu xəta verir; garbage: hər cavab zibildir."""

    def __init__(self, replace=None, fail=False, fail_first=False, garbage=False):
        self.urls = []
        self.replace = dict(replace or {})
        self.fail, self.fail_first, self.garbage = fail, fail_first, garbage

    def __call__(self, url, timeout=15, headers=None):
        assert timeout <= 15, timeout
        first = url not in self.urls
        self.urls.append(url)
        name = fixture_name(url)
        if self.fail or (self.fail_first and first):
            raise OSError("timed out")
        if self.garbage:
            return b"<html>503 Service Unavailable</html>"
        if name in self.replace:
            v = self.replace[name]
            if isinstance(v, Exception):
                raise v
            return v
        path = FIX / name
        if not path.exists():
            raise OSError("404 " + name)
        return path.read_bytes()

    def host(self, part):
        return [u for u in self.urls if part in u]


def run_day(day, fake, step=10, root=SITE):
    """Canlı dövrə: gün boyu hər `step` dəqiqədə items(); qaytarılan hər açar done-a yazılır."""
    done, got = set(), []
    t = datetime.datetime.combine(day, datetime.time(0, 0), BAKU)
    end = t + datetime.timedelta(days=1)
    while t < end:
        new = m.items(root, t, fetch=fake, done=done)
        got += new
        done |= {i["key"] for i in new}
        t += datetime.timedelta(minutes=step)
    return got


def race20(table=True):
    f, why = m.race_facts(load("f1-2026-20-results.json"), 2026, 20)
    assert f, why
    teams = {r["id"]: r["team"] for r in f["rows"]}
    tab = m.standings(load("f1-2026-20-driverStandings.json"), 2026, 20, teams) if table else None
    return f, tab


def week_of(y, mo, d):
    return next(w for w in m.euro_weeks(SITE) if w["check"].date() == datetime.date(y, mo, d))


def judo_ev(cid):
    return next(e for e in m.CUDO_CAL if e["id"] == cid)


class GrammarTest(unittest.TestCase):
    def test_driver_suffixes_follow_pronunciation(self):
        self.assertEqual(m.f1_gen("Norris"), "«Norris»in")
        self.assertEqual(m.f1_dat("Verstappen"), "«Verstappen»ə")
        self.assertEqual(m.f1_dat("Leclerc"), "«Leclerc»ə")          # Leklerk: samitlə bitir
        self.assertEqual(m.f1_gen("Antonelli"), "«Antonelli»nin")
        self.assertEqual(m.f1_dat("Antonelli"), "«Antonelli»yə")
        self.assertEqual(m.f1_dat("Hamilton"), "«Hamilton»a")
        self.assertEqual(m.f1_abl("Hamilton"), "«Hamilton»dan")
        self.assertEqual(m.f1_abl("Russell"), "«Russell»dən")        # Rassel
        self.assertEqual(m.f1_gen("Lawson"), "«Lawson»un")
        self.assertEqual(m.f1_abl("Verstappen"), "«Verstappen»dən")

    def test_unknown_driver_falls_back_to_spelling(self):
        self.assertEqual(m.f1_gen("Rossi"), "«Rossi»nin")
        self.assertEqual(m.f1_abl("Smith"), "«Smith»dən")
        self.assertEqual(m.f1_dat("Kowal"), "«Kowal»a")

    def test_every_driver_in_the_saved_results_has_a_pronunciation(self):
        for name in ("f1-2026-20-results.json", "f1-2026-15-results.json"):
            for x in load(name)["MRData"]["RaceTable"]["Races"][0]["Results"]:
                self.assertIn(x["Driver"]["familyName"], m.F1_PRON)

    def test_grand_prix_forms(self):
        self.assertEqual(m._gp_forms("Brazilian Grand Prix"),
                         ("Braziliya Qran-prisi", "Braziliya Qran-prisinin", "Braziliya Qran-prisində"))
        self.assertEqual(m._gp_forms("Bahrain Grand Prix in Malaysia")[1], "Bəhreyn Qran-prisinin (Malayziyada)")
        self.assertEqual(m._gp_forms("Bahrain Grand Prix in Malaysia")[2], "Bəhreyn Qran-prisində (Malayziyada)")
        self.assertEqual(m._gp_forms("Foo Grand Prix"), ("«Foo Grand Prix»", "«Foo Grand Prix»nin", "«Foo Grand Prix»də"))

    def test_small_formats(self):
        d = datetime.date
        self.assertEqual(m._range_loc(d(2026, 10, 29), d(2026, 10, 31)), "29–31 oktyabrda")
        self.assertEqual(m._range_loc(d(2026, 2, 27), d(2026, 3, 1)), "27 fevral – 1 martda")
        self.assertEqual(m._range_loc(d(2026, 2, 7), d(2026, 2, 7)), "7 fevralda")
        self.assertEqual(m._abl_az("Ukrayna"), "Ukraynadan")
        self.assertEqual(m._abl_az("İsrail"), "İsraildən")
        self.assertEqual(m._abl_az("Farer adaları"), "Farer adalarından")
        self.assertEqual(m._pts("390"), "390")
        self.assertEqual(m._pts(12.5), "12,5")
        self.assertEqual(m._and(["a"]), "a")
        self.assertEqual(m._and(["a", "b", "c"]), "a, b və c")
        self.assertEqual(m._and([]), "")
        self.assertEqual(m._team("RB F1 Team"), "RB")

    def test_gap_to_the_winner(self):
        win = {"laps": 71}
        self.assertEqual(m._behind({"time": "+14.602", "laps": 71}, win), "14,602 saniyə")
        self.assertEqual(m._behind({"time": "+1:15.402", "laps": 71}, win), "1 dəqiqə 15,402 saniyə")
        self.assertEqual(m._behind({"time": "+4.427", "laps": 70}, win), "1 dövrə")     # dövrə geridə: vaxt başqa şeydir
        self.assertEqual(m._behind({"time": "", "laps": 71}, win), "")


class SlotTest(unittest.TestCase):
    def test_slot_rounds_up_and_moves_night_to_morning(self):
        self.assertEqual(m._slot(utc(2026, 9, 26, 15, 0)), baku(2026, 9, 26, 19, 0))
        self.assertEqual(m._slot(utc(2026, 9, 26, 16, 10)), baku(2026, 9, 26, 20, 30))
        self.assertEqual(m._slot(utc(2026, 11, 8, 21, 0)), baku(2026, 11, 9, 9, 30))      # 01:00 -> 09:30
        self.assertEqual(m._slot(utc(2026, 11, 8, 18, 41)), baku(2026, 11, 9, 10, 0))     # 22:41 -> ertəsi 10:00

    def test_tries_stay_on_the_same_day(self):
        self.assertEqual(m._tries(baku(2026, 11, 9, 9, 30), 2), [baku(2026, 11, 9, 9, 30), baku(2026, 11, 9, 11, 30)])
        self.assertEqual(m._tries(baku(2026, 11, 9, 21, 30), 2), [baku(2026, 11, 9, 21, 30), baku(2026, 11, 9, 23, 30)])
        self.assertEqual(m._tries(baku(2026, 11, 9, 22, 0), 2), [baku(2026, 11, 9, 22, 0)])
        self.assertEqual(m._tries(baku(2026, 11, 9, 11, 0), 1), [baku(2026, 11, 9, 11, 0)])

    def test_window_is_forty_minutes(self):
        tries = [baku(2026, 11, 9, 9, 30), baku(2026, 11, 9, 11, 30)]
        self.assertIsNone(m._try_no(baku(2026, 11, 9, 9, 29), tries))
        self.assertEqual(m._try_no(baku(2026, 11, 9, 9, 30), tries), 0)
        self.assertEqual(m._try_no(baku(2026, 11, 9, 10, 9), tries), 0)
        self.assertIsNone(m._try_no(baku(2026, 11, 9, 10, 10), tries))
        self.assertEqual(m._try_no(baku(2026, 11, 9, 12, 0), tries), 1)

    def test_f1_slots(self):
        evs = {e["key"]: e for e in m.f1_events(2026)}
        self.assertEqual(len(evs), 23 * 3)
        # Bakı: şənbə yarışı, ön baxış cümə axşamı, kvalifikasiya cümə
        self.assertEqual(evs["f1-2026-r15-onbaxis"]["tries"][0], baku(2026, 9, 24, 11, 0))
        self.assertEqual(evs["f1-2026-r15-siralama"]["tries"][0], baku(2026, 9, 25, 19, 0))
        self.assertEqual(evs["f1-2026-r15-yaris"]["tries"], [baku(2026, 9, 26, 19, 0), baku(2026, 9, 26, 21, 0)])
        # Avropa yarışı: kvalifikasiya şənbə axşamı, yarış bazar axşamı
        self.assertEqual(evs["f1-2026-r13-siralama"]["tries"][0], baku(2026, 9, 5, 21, 0))
        self.assertEqual(evs["f1-2026-r13-yaris"]["tries"], [baku(2026, 9, 6, 21, 0), baku(2026, 9, 6, 23, 0)])
        # Amerika yarışı Bakıda gecəyə düşür: səhər 09:30
        self.assertEqual(evs["f1-2026-r20-yaris"]["tries"], [baku(2026, 11, 9, 9, 30), baku(2026, 11, 9, 11, 30)])
        self.assertEqual(evs["f1-2026-r21-onbaxis"]["tries"][0], baku(2026, 11, 19, 11, 0))
        for e in evs.values():
            self.assertEqual(len({t.date() for t in e["tries"]}), 1)
            if e["kind"] == "f1-onbaxis":
                self.assertEqual(e["tries"][0].weekday(), 3)
        self.assertEqual(m.f1_events(2027), [])           # təqvim yoxdur: xəbər də, sorğu da yoxdur

    def test_judo_slots(self):
        j = {e["key"]: e for e in m.judo_events()}
        self.assertEqual(j["cudo-ijf-3157"]["tries"], [baku(2026, 10, 31, 21, 0)])       # Əbu-Dabi: yerli 21:00
        self.assertEqual(j["cudo-ijf-3159"]["tries"], [baku(2026, 11, 16, 9, 30)])       # Zaqreb: gecə -> səhər
        self.assertEqual(j["cudo-ijf-3160"]["tries"], [baku(2026, 12, 6, 16, 0)])        # Tokio: 21:00 JST
        self.assertEqual(j["cudo-ijf-3205"]["tries"], [baku(2026, 8, 17, 9, 30)])        # Lima
        self.assertEqual(m.judo_events([]), [])           # boş il bütün təqvimi qaytarmır

    def test_uefa_checks(self):
        checks = m.uefa_checks(SITE, 2026)
        days = [w["check"] for w in checks]
        self.assertIn(baku(2026, 11, 6, 11, 0), days)
        self.assertIn(baku(2026, 10, 16, 11, 0), days)
        self.assertEqual(days, sorted(set(days)))
        summer = [w for w in checks if w["last"] is None]
        self.assertEqual(len(summer), 9)                  # iyul–avqust 2026-nın cümələri
        for w in summer:
            self.assertIn(w["check"].month, (7, 8))
            self.assertEqual(w["check"].weekday(), 4)
            self.assertIsNone(w["az"])
        for w in checks:
            if w["last"] is not None:
                self.assertGreaterEqual(w["check"], w["last"] + m.UEFA_LAG)
                self.assertLess(w["check"] - w["last"], datetime.timedelta(days=2))
        self.assertEqual(week_of(2026, 11, 6)["az"], {"w": 0, "d": 0, "l": 1})           # Vikinq 4:1 Sabah
        self.assertEqual(week_of(2026, 10, 16)["az"], {"w": 1, "d": 0, "l": 0})          # Sabah 2:0 Slaviya
        self.assertIsNone(week_of(2026, 11, 27)["az"])                                   # oyun hələ oynanmayıb
        self.assertEqual(m._uefa_year(datetime.date(2026, 11, 6)), 2027)
        self.assertEqual(m._uefa_year(datetime.date(2027, 3, 12)), 2027)
        self.assertEqual(m._uefa_year(datetime.date(2027, 7, 9)), 2028)

    def test_uefa_without_site_files_keeps_only_summer_fridays(self):
        checks = m.uefa_checks(ROOT / "tests" / "fixtures" / "yoxdur", 2026)
        self.assertEqual(len(checks), 9)
        self.assertTrue(all(w["last"] is None for w in checks))

    def test_event_keys_are_unique_and_june_is_empty(self):
        for year in (2026, 2027):
            evs = m.events(SITE, year)
            keys = [e["key"] for e in evs]
            self.assertEqual(len(keys), len(set(keys)))
            self.assertFalse([e["key"] for e in evs if e["kind"] == "uefa-emsal" and e["tries"][0].month == 6])
            for e in evs:
                self.assertIn(e["kind"], m.LABEL)
                self.assertTrue(e["credit"] and e["link"].startswith("https://"))


class CalendarTest(unittest.TestCase):
    def test_f1_calendar_equals_the_saved_api_schedule(self):
        races = load("f1-2026.json")["MRData"]["RaceTable"]["Races"]
        self.assertEqual(len(races), len(m.F1_CAL[2026]))
        for r, c in zip(races, m.F1_CAL[2026]):
            self.assertEqual((int(r["round"]), r["raceName"]), (c["round"], c["name"]))
            self.assertEqual(m._ergast_dt(r["date"], r["time"]), c["race"])
            self.assertEqual(m._ergast_dt(r["Qualifying"]["date"], r["Qualifying"]["time"]), c["quali"])
            self.assertTrue(m.gp_az(r["raceName"]), r["raceName"])
            self.assertIn(r["Circuit"]["Location"]["locality"], m.CITY_AZ)

    def test_calendar_check_against_saved_lists(self):
        fake = Fake()
        lines = m.calendar_check(fake, 2026)
        text = "\n".join(lines)
        self.assertEqual(text.count("eynidir"), 3, text)   # F1 2026, IJF 2026, IJF 2027
        self.assertNotIn("⚠", text)
        self.assertIn("F1 2027: modulda təqvim yoxdur", text)
        self.assertEqual(len(fake.urls), 3)

    def test_calendar_check_reports_a_difference_and_a_dead_source(self):
        doc = load("f1-2026.json")
        doc["MRData"]["RaceTable"]["Races"][20]["date"] = "2026-11-29"
        text = "\n".join(m.calendar_check(Fake(replace={"f1-2026.json": raw(doc)}), 2026))
        self.assertIn("⚠ fərq var: 21-ci mərhələ", text)
        text = "\n".join(m.calendar_check(Fake(fail=True), 2026))
        self.assertIn("Jolpica alınmadı", text)
        self.assertEqual(text.count("siyahı alınmadı"), 2)

    def test_judo_calendar_has_names_for_everything(self):
        self.assertEqual(len(m.CUDO_CAL), 31)
        for ev in m.CUDO_CAL:
            self.assertIn(ev["city"], m.JUDO_CITY)
            self.assertIn(ev["rank"], m.JUDO_RANK)
            self.assertLessEqual(ev["from"], ev["to"])


class RaceTest(unittest.TestCase):
    def test_race_item_from_the_saved_result(self):
        f, table = race20()
        item, why = m.race_item(f, table, baku(2026, 11, 9, 9, 30))
        self.assertTrue(item, why)
        self.assertEqual(item["title"], "Lando Norris Braziliya Qran-prisində birinci yerdən start götürüb qalib gəlib")
        self.assertEqual(item["lead"], (
            "Formula 1 mövsümünün 20-ci mərhələsi — Braziliya Qran-prisi 8 noyabrda San-Pauluda keçirilib. "
            "McLaren pilotu Lando Norris birinci yerdən start götürüb 71 dövrəni 1:35:23,504 vaxtla başa vuraraq qalib gəlib. "
            "21-ci yerdən start götürən Max Verstappen (Red Bull) qalibdən 14,602 saniyə geri qalaraq ikinci, "
            "Isack Hadjar (Red Bull) qalibdən 24,485 saniyə geri qalaraq üçüncü olub."))
        body = "\n".join(item["body"])
        self.assertIn("İlk onluqdakı digər pilotlar: 4. George Russell (Mercedes), 5. Andrea Kimi Antonelli (Mercedes), "
                      "6. Oscar Piastri (McLaren), 7. Liam Lawson (RB), 8. Charles Leclerc (Ferrari), "
                      "9. Lewis Hamilton (Ferrari), 10. Nico Hülkenberg (Audi).", body)
        self.assertIn("Ən sürətli dövrəni Andrea Kimi Antonelli (Mercedes) 1:12,689 vaxtla keçib.", body)
        self.assertIn("Yarışı başa vurmayıb: Lance Stroll (Aston Martin). Start götürməyib: Valtteri Bottas (Cadillac).", body)
        self.assertIn("Çempionatda ilk beşlik: 1. Andrea Kimi Antonelli (Mercedes) – 390 xal, 2. Max Verstappen (Red Bull) – "
                      "279 xal, 3. George Russell (Mercedes) – 262 xal, 4. Lewis Hamilton (Ferrari) – 261 xal, "
                      "5. Charles Leclerc (Ferrari) – 249 xal.", body)
        self.assertIn("Lider Andrea Kimi Antonelli ikinci yerdəki «Verstappen»dən 111 xal öndədir.", body)
        self.assertIn("Bu, «Norris»in mövsümdəki 3-cü qələbəsidir.", body)
        self.assertEqual((item["kind"], item["key"], item["slot"], item["topic"], item["worth"], item["list"]),
                         ("f1-yaris", "f1-2026-r20-yaris", "09:30", "idman", True, True))
        self.assertEqual(item["link"], "https://api.jolpi.ca/ergast/f1/2026/20/results.json")
        self.assertLessEqual(len(item["title"]), 110)

    def test_baku_race_is_named(self):
        f, why = m.race_facts(load("f1-2026-15-results.json"), 2026, 15)
        self.assertTrue(f, why)
        self.assertTrue(f["baku"])
        table = m.standings(load("f1-2026-15-driverStandings.json"), 2026, 15, {r["id"]: r["team"] for r in f["rows"]})
        item, why = m.race_item(f, table, baku(2026, 9, 26, 19, 0))
        self.assertEqual(item["title"], "George Russell Bakıda keçirilən Azərbaycan Qran-prisinin qalibi olub")
        self.assertIn("Azərbaycan Qran-prisi 26 sentyabrda Bakı Şəhər Halqasında keçirilib.", item["lead"])
        self.assertIn("51 dövrəni 1:38:02,143 vaxtla", item["lead"])
        self.assertIn("Max Verstappen (Red Bull) qalibdən 0,196 saniyə geri qalaraq ikinci", item["lead"])
        body = "\n".join(item["body"])
        # 16-cı yerdə təsnif olunan (Retired, 49 dövrə) pilot «başa vurmayıb» siyahısında deyil
        self.assertIn("Yarışı başa vurmayıb: Franco Colapinto (Alpine), Pierre Gasly (Alpine), Lando Norris (McLaren), "
                      "Alexander Albon (Williams), Fernando Alonso (Aston Martin), Lance Stroll (Aston Martin).", body)
        self.assertNotIn("Bottas", body)
        self.assertIn("Lider Andrea Kimi Antonelli ikinci yerdəki «Russell»dən 66 xal öndədir.", body)
        self.assertIn("Bu, «Russell»in mövsümdəki 3-cü qələbəsidir.", body)

    def test_first_win_and_plain_titles(self):
        f, table = race20()
        for row in table:
            if row["name"] == "Lando Norris":
                row["wins"] = 1
        item, _ = m.race_item(f, table, baku(2026, 11, 9, 9, 30))
        self.assertEqual(item["title"], "Lando Norris Braziliya Qran-prisində mövsümdə ilk dəfə qalib gəlib")
        self.assertIn("Bu, «Norris»in mövsümdəki ilk qələbəsidir.", item["body"])
        f["rows"][0]["grid"] = 4
        item, _ = m.race_item(f, None, baku(2026, 11, 9, 9, 30))
        self.assertEqual(item["title"], "Lando Norris Braziliya Qran-prisinin qalibi olub")
        self.assertIn("Lando Norris 4-cü yerdən start götürüb 71 dövrəni", item["lead"])
        self.assertFalse([b for b in item["body"] if "Çempionatda" in b or "qələbəsidir" in b])   # cədvəlsiz də xəbərdir

    def test_missing_incomplete_and_garbage_results(self):
        self.assertEqual(m.race_facts(load("f1-2026-21-results.json"), 2026, 21),
                         (None, "yarışın nəticəsi API-də hələ yoxdur"))
        for doc in (None, {}, [], "x", {"MRData": {}}, {"MRData": {"RaceTable": {"Races": ["x", 5]}}}):
            self.assertIsNone(m.race_facts(doc, 2026, 20)[0])
        full = load("f1-2026-20-results.json")
        self.assertIsNone(m.race_facts(full, 2026, 19)[0])                    # başqa mərhələnin (köhnə) cavabı
        self.assertIsNone(m.race_facts(full, 2025, 20)[0])
        doc = copy.deepcopy(full)
        doc["MRData"]["RaceTable"]["Races"][0]["Results"] = doc["MRData"]["RaceTable"]["Races"][0]["Results"][:6]
        self.assertEqual(m.race_facts(doc, 2026, 20), (None, "yarışın nəticəsi natamamdır (6 pilot)"))
        doc = copy.deepcopy(full)
        del doc["MRData"]["RaceTable"]["Races"][0]["Results"][0]              # qalib yoxdur
        self.assertIsNone(m.race_facts(doc, 2026, 20)[0])
        doc = copy.deepcopy(full)
        del doc["MRData"]["RaceTable"]["Races"][0]["Results"][0]["Time"]
        self.assertIn("qalibin vaxtı", m.race_facts(doc, 2026, 20)[1])
        doc = copy.deepcopy(full)
        doc["MRData"]["RaceTable"]["Races"][0]["Results"][0]["laps"] = ""
        self.assertIsNone(m.race_facts(doc, 2026, 20)[0])
        doc = copy.deepcopy(full)
        del doc["MRData"]["RaceTable"]["Races"][0]["time"]
        self.assertEqual(m.race_facts(doc, 2026, 20), (None, "yarışın tarixi yoxdur"))

    def test_standings_need_the_same_round(self):
        doc = load("f1-2026-20-driverStandings.json")
        self.assertGreaterEqual(len(m.standings(doc, 2026, 20)), 20)
        self.assertIsNone(m.standings(doc, 2026, 21))                         # köhnə cədvəl yeni yarışa yazılmır
        self.assertIsNone(m.standings(load("f1-2026-19-driverStandings.json"), 2026, 20))
        for bad in (None, {}, [], {"MRData": {"StandingsTable": {"StandingsLists": []}}}):
            self.assertIsNone(m.standings(bad, 2026, 20))
        short = copy.deepcopy(doc)
        lst = short["MRData"]["StandingsTable"]["StandingsLists"][0]
        lst["DriverStandings"] = lst["DriverStandings"][:3]
        self.assertIsNone(m.standings(short, 2026, 20))
        # iki komandada çıxış edən pilotun komandası yarışın nəticəsindən götürülür, yoxdursa yazılmır
        rows = {r["family"]: r for r in m.standings(doc, 2026, 20)}
        self.assertEqual(rows["Lawson"]["team"], "")
        self.assertEqual(rows["Antonelli"]["team"], "Mercedes")
        f, table = race20()
        self.assertEqual({r["family"]: r for r in table}["Lawson"]["team"], "RB")

    def test_make_race_guards_time(self):
        make = m.f1_make_race(2026, 20)
        item, why = make(Fake(), baku(2026, 11, 8, 20, 0))                    # yarışdan əvvəl
        self.assertEqual((item, why), (None, "yarış hələ keçirilməyib (cavab köhnə və ya səhvdir)"))
        item, why = make(Fake(), baku(2026, 11, 14, 9, 30))                   # 5 gün sonra: köhnə
        self.assertEqual((item, why), (None, "yarışın nəticəsi köhnədir (təqvim dəyişib)"))
        item, why = make(Fake(fail=True), baku(2026, 11, 9, 9, 30))
        self.assertEqual((item, why), (None, "Jolpica alınmadı: OSError"))
        item, why = make(Fake(garbage=True), baku(2026, 11, 9, 9, 30))
        self.assertIsNone(item)
        fake = Fake(replace={"f1-2026-20-driverStandings.json": OSError("x")})
        item, why = make(fake, baku(2026, 11, 9, 9, 30))                      # cədvəl gecikir: nəticə yenə xəbərdir
        self.assertTrue(item["worth"])
        self.assertNotIn("Çempionatda", "\n".join(item["body"]))
        self.assertEqual(len(fake.urls), 2)


class QualiTest(unittest.TestCase):
    def test_quali_item_from_the_saved_result(self):
        f, why = m.quali_facts(load("f1-2026-20-qualifying.json"), 2026, 20)
        self.assertTrue(f, why)
        item, why = m.quali_item(f, baku(2026, 11, 8, 9, 30))
        self.assertEqual(item["title"], "Lando Norris Braziliya Qran-prisinin kvalifikasiyasında birinci olub")
        self.assertEqual(item["lead"], (
            "Formula 1 mövsümünün 20-ci mərhələsi olan Braziliya Qran-prisinin kvalifikasiyasında McLaren pilotu "
            "Lando Norris 1:27,470 vaxtla birinci olub. George Russell (Mercedes) «Norris»dən 0,204 saniyə geri qalaraq "
            "ikinci, Andrea Kimi Antonelli (Mercedes) «Norris»dən 0,625 saniyə geri qalaraq üçüncü yeri tutub."))
        self.assertEqual(item["body"][-1], "Yarış 8 noyabrda Bakı vaxtı ilə saat 21:00-də başlayacaq.")
        self.assertIn("4. Charles Leclerc (Ferrari)", item["body"][0])
        self.assertEqual((item["key"], item["kind"], item["worth"]), ("f1-2026-r20-siralama", "f1-siralama", True))

    def test_baku_quali(self):
        f, _ = m.quali_facts(load("f1-2026-15-qualifying.json"), 2026, 15)
        item, _ = m.quali_item(f, baku(2026, 9, 25, 19, 0))
        self.assertEqual(item["title"], "George Russell Bakıda Azərbaycan Qran-prisinin kvalifikasiyasında birinci olub")
        self.assertIn("George Russell 1:42,526 vaxtla birinci olub. Charles Leclerc (Ferrari) «Russell»dən 0,837 saniyə", item["lead"])
        self.assertIn("Oscar Piastri (McLaren) «Russell»dən 0,838 saniyə geri qalaraq üçüncü yeri tutub.", item["lead"])
        self.assertEqual(item["body"][-1], "Yarış 26 sentyabrda Bakı vaxtı ilə saat 15:00-də başlayacaq.")

    def test_missing_and_incomplete_quali(self):
        self.assertEqual(m.quali_facts(load("f1-2026-21-qualifying.json"), 2026, 21),
                         (None, "kvalifikasiyanın nəticəsi API-də hələ yoxdur"))
        for doc in (None, {}, [], {"MRData": {"RaceTable": {"Races": [None]}}}):
            self.assertIsNone(m.quali_facts(doc, 2026, 20)[0])
        full = load("f1-2026-20-qualifying.json")
        doc = copy.deepcopy(full)
        rows = doc["MRData"]["RaceTable"]["Races"][0]["QualifyingResults"]
        for k in ("Q1", "Q2", "Q3"):
            rows[0].pop(k, None)                                              # birincinin vaxtı yoxdur
        self.assertIsNone(m.quali_facts(doc, 2026, 20)[0])
        doc = copy.deepcopy(full)
        doc["MRData"]["RaceTable"]["Races"][0]["QualifyingResults"] = rows[:4]
        self.assertIn("natamamdır (4 pilot)", m.quali_facts(doc, 2026, 20)[1])
        doc = copy.deepcopy(full)
        del doc["MRData"]["RaceTable"]["Races"][0]["QualifyingResults"][1]["Q3"]   # ikincinin Q3 vaxtı yoxdur: fərq yazılmır
        f, _ = m.quali_facts(doc, 2026, 20)
        item, _ = m.quali_item(f, baku(2026, 11, 8, 9, 30))
        self.assertIn("George Russell (Mercedes) ikinci, Andrea Kimi Antonelli (Mercedes) «Norris»dən 0,625", item["lead"])

    def test_make_quali_guards_time(self):
        make = m.f1_make_quali(2026, 20)
        self.assertTrue(make(Fake(), baku(2026, 11, 8, 9, 30))[0])
        self.assertEqual(make(Fake(), baku(2026, 11, 20, 9, 30)),
                         (None, "kvalifikasiyanın nəticəsi bu həftə sonuna aid deyil (təqvim dəyişib)"))
        self.assertEqual(make(Fake(fail=True), baku(2026, 11, 8, 9, 30)), (None, "Jolpica alınmadı: OSError"))
        self.assertIsNone(make(Fake(garbage=True), baku(2026, 11, 8, 9, 30))[0])


class PreviewTest(unittest.TestCase):
    def test_preview_from_the_saved_schedule(self):
        table = m.standings(load("f1-2026-20-driverStandings.json"), 2026, 20)
        item, why = m.preview_item(load("f1-2026-21.json"), table, baku(2026, 11, 19, 11, 0), 2026, 21, None, 23)
        self.assertTrue(item, why)
        self.assertEqual(item["title"], "Formula 1: Las-Veqas Qran-prisi bu həftə sonu keçiriləcək")
        self.assertEqual(item["lead"], (
            "Formula 1 mövsümünün 21-ci mərhələsi — Las-Veqas Qran-prisi 22 noyabrda Las-Veqasda "
            "(Las Vegas Strip Street Circuit) keçiriləcək. Yarış Bakı vaxtı ilə saat 08:00-də başlayacaq."))
        self.assertEqual(item["body"], [
            "Kvalifikasiya 21 noyabrda Bakı vaxtı ilə saat 08:00-də başlayacaq.",
            "Çempionatda Andrea Kimi Antonelli (Mercedes) 390 xalla liderdir, Max Verstappen (Red Bull) 279, "
            "George Russell (Mercedes) 262 xal toplayıb.",
            "Lider ikinci yerdəki «Verstappen»dən 111 xal öndədir."])
        self.assertEqual((item["key"], item["slot"]), ("f1-2026-r21-onbaxis", "11:00"))

    def test_city_in_the_title_when_it_is_not_in_the_name(self):
        item, _ = m.preview_item(load("f1-2026-20.json"), None, baku(2026, 11, 5, 11, 0), 2026, 20, None, 23)
        self.assertEqual(item["title"], "Formula 1: Braziliya Qran-prisi bu həftə sonu San-Pauluda keçiriləcək")
        self.assertEqual(len(item["body"]), 1)                                # cədvəlsiz: yalnız kvalifikasiya sətri

    def test_baku_preview_counts_the_races_on_the_circuit(self):
        races = load("f1-circuits-baku-races.json")["MRData"]["RaceTable"]["Races"]
        n = len([r for r in races if (int(r["season"]), int(r["round"])) <= (2026, 15)])
        self.assertEqual(m._baku_count(load("f1-circuits-baku-races.json"), 2026, 15), n)
        self.assertIsNone(m._baku_count(load("f1-circuits-baku-races.json"), 2027, 3))   # siyahıda yoxdursa say yazılmır
        self.assertIsNone(m._baku_count({}, 2026, 15))
        table = m.standings(load("f1-2026-14-driverStandings.json"), 2026, 14)
        item, why = m.preview_item(load("f1-2026-15.json"), table, baku(2026, 9, 24, 11, 0), 2026, 15, n, 23)
        self.assertEqual(item["title"], "Formula 1: Azərbaycan Qran-prisi bu həftə sonu Bakıda keçiriləcək")
        self.assertIn("Azərbaycan Qran-prisi 26 sentyabrda Bakı Şəhər Halqasında keçiriləcək. "
                      "Yarış Bakı vaxtı ilə saat 15:00-də başlayacaq.", item["lead"])
        self.assertIn("Kvalifikasiya 25 sentyabrda Bakı vaxtı ilə saat 16:00-da başlayacaq.", item["body"])
        self.assertIn(f"Bu, Bakı Şəhər Halqasında keçirilən {n}-cu Formula 1 yarışı olacaq.", item["body"])
        self.assertEqual(n, 10)
        self.assertIn("Çempionatda Andrea Kimi Antonelli (Mercedes) 292 xalla liderdir, George Russell (Mercedes) 211, "
                      "Lewis Hamilton (Ferrari) 191 xal toplayıb.", item["body"])

    def test_sprint_and_last_round(self):
        year = load("f1-2026.json")
        item, why = m.preview_item(year, None, baku(2026, 10, 8, 11, 0), 2026, 17, None, 23)
        self.assertTrue(item, why)
        self.assertIn("Bu həftə sonu sprint yarışı da keçiriləcək: 10 oktyabrda, Bakı vaxtı ilə saat 13:00-də.", item["body"])
        item, why = m.preview_item(year, None, baku(2026, 12, 3, 11, 0), 2026, 23, None, 23)
        self.assertEqual(item["title"], "Formula 1 mövsümünün son mərhələsi — Əbu-Dabi Qran-prisi bu həftə sonu keçiriləcək")
        for e in m.F1_CAL[2026]:                                              # bütün mərhələlərin başlığı sığır
            thursday = e["race"].astimezone(BAKU) - datetime.timedelta(days=3)
            item, why = m.preview_item(year, None, thursday, 2026, e["round"], None, 23)
            self.assertTrue(item, (e["round"], why))
            self.assertLessEqual(len(item["title"]), 110)

    def test_preview_guards(self):
        doc = load("f1-2026-21.json")
        self.assertEqual(m.preview_item(doc, None, baku(2026, 11, 23, 11, 0), 2026, 21), (None, "yarış artıq keçib"))
        self.assertEqual(m.preview_item(doc, None, baku(2026, 11, 12, 11, 0), 2026, 21),
                         (None, "təqvim dəyişib: yarış bu həftə sonu deyil"))
        self.assertEqual(m.preview_item(doc, None, baku(2026, 11, 19, 11, 0), 2026, 22),
                         (None, "mərhələnin təqvimi API-də yoxdur"))
        bad = copy.deepcopy(doc)
        del bad["MRData"]["RaceTable"]["Races"][0]["time"]
        self.assertEqual(m.preview_item(bad, None, baku(2026, 11, 19, 11, 0), 2026, 21), (None, "yarışın vaxtı yoxdur"))
        for junk in (None, {}, [], "x"):
            self.assertIsNone(m.preview_item(junk, None, baku(2026, 11, 19, 11, 0), 2026, 21)[0])

    def test_make_preview_requests(self):
        make = m.f1_make_preview(2026, 21, 23)
        fake = Fake()
        self.assertTrue(make(fake, baku(2026, 11, 19, 11, 0))[0])
        self.assertEqual(len(fake.urls), 2)
        fake = Fake()
        self.assertTrue(m.f1_make_preview(2026, 15, 23)(fake, baku(2026, 9, 24, 11, 0))[0])
        self.assertEqual(len(fake.urls), 3)                                   # Bakı: + pistin tarixçəsi
        moved = load("f1-2026-21.json")
        moved["MRData"]["RaceTable"]["Races"][0]["date"] = "2026-12-13"
        fake = Fake(replace={"f1-2026-21.json": raw(moved)})
        self.assertIsNone(make(fake, baku(2026, 11, 19, 11, 0))[0])
        self.assertEqual(len(fake.urls), 1)                                   # təqvim yaramır: əlavə sorğu getmir
        fake = Fake(replace={"f1-2026-20-driverStandings.json": OSError("x")})
        item, _ = make(fake, baku(2026, 11, 19, 11, 0))
        self.assertEqual(len(item["body"]), 1)                                # cədvəl alınmadı: ön baxış yenə var


class JudoTest(unittest.TestCase):
    def cats(self, cid):
        cats, why = m.judo_cats(load(f"ijf-{cid}-results.json"))
        self.assertTrue(cats, why)
        return cats

    def test_abu_dhabi_grand_slam(self):
        item, why = m.judo_item(judo_ev("3157"), self.cats("3157"), baku(2026, 10, 31, 21, 0))
        self.assertTrue(item, why)
        self.assertEqual(item["title"], "Əbu-Dabi Böyük Dəbilqə turniri: Azərbaycan yığması medal sıralamasında birinci olub")
        self.assertEqual(item["lead"], (
            "29–31 oktyabrda Əbu-Dabidə keçirilən Böyük Dəbilqə turnirində Azərbaycan cüdoçuları 5 medal qazanıb: "
            "2 qızıl, 1 gümüş və 2 bürünc. Balabəy Ağayev (-60 kq) və Könül Əliyeva (-48 kq) qalib gəlib, "
            "Uşanqi Kokauri (+100 kq) ikinci, Rəşad Yelkiyev (-66 kq) və Hidayət Heydərov (-73 kq) üçüncü olub."))
        self.assertEqual(item["body"], [
            "Ruslan Paşayev (-66 kq) və Madina Kaisinova (+78 kq) beşinci, Gültac Məmmədəliyeva (-52 kq) yeddinci yeri tutub.",
            "Azərbaycan yığması medal sıralamasında birinci olub."])
        self.assertEqual((item["key"], item["link"], item["credit"]),
                         ("cudo-ijf-3157", "https://www.ijf.org/competition/3157/results", "Beynəlxalq Cüdo Federasiyası (IJF)"))

    def test_world_championships(self):
        item, why = m.judo_item(judo_ev("3151"), self.cats("3151"), baku(2026, 10, 10, 21, 0))
        self.assertTrue(item, why)
        self.assertEqual(item["title"], "Cüdo üzrə dünya çempionatı (Bakı): Azərbaycan cüdoçuları 1 qızıl, 2 gümüş və 4 bürünc medal qazanıb")
        self.assertLessEqual(len(item["title"]), 110)
        self.assertEqual(item["lead"], (
            "4–10 oktyabrda Bakıda keçirilən dünya çempionatında Azərbaycan cüdoçuları 7 medal qazanıb: 1 qızıl, 2 gümüş və "
            "4 bürünc. Əhməd Yusifov (-60 kq) qalib gəlib, Zelim Tçkayev (-81 kq) və Uşanqi Kokauri (+100 kq) ikinci, "
            "Rəşid Məmmədəliyev (-73 kq), Ömər Rəcəbli (-81 kq), Murad Fətiyev (-90 kq) və Kənan Nəsibov (+100 kq) üçüncü olub."))
        self.assertEqual(item["body"], [
            "Camal Qamzatxanov (+100 kq) beşinci, Gültac Məmmədəliyeva (-52 kq) yeddinci yeri tutub.",
            "Azərbaycan yığması fərdi yarışların medal sıralamasında üçüncü olub."])

    def test_no_medal_is_not_news(self):
        self.assertEqual(m.judo_item(judo_ev("3205"), self.cats("3205"), baku(2026, 8, 17, 9, 30)),
                         (None, "Azərbaycan cüdoçuları medal qazanmayıb"))
        cats = self.cats("3157")                                              # yalnız 5 və 7-ci yerlər: xəbər deyil
        for c in cats:
            c["persons"] = [p for p in c["persons"] if p["country_short"] != "AZE" or p["place"] in ("5", "7")]
        self.assertIsNone(m.judo_item(judo_ev("3157"), cats, baku(2026, 10, 31, 21, 0))[0])

    def test_single_medal_and_tied_table(self):
        cats = self.cats("3157")
        for c in cats:
            c["persons"] = [p for p in c["persons"] if p["country_short"] != "AZE" or p["id_person"] == "13028"]
        item, _ = m.judo_item(judo_ev("3157"), cats, baku(2026, 10, 31, 21, 0))
        self.assertEqual(item["title"], "Əbu-Dabi Böyük Dəbilqə turniri: Hidayət Heydərov (-73 kq) bürünc medal qazanıb")
        self.assertIn("Azərbaycan cüdoçuları 1 medal qazanıb: 1 bürünc. Hidayət Heydərov (-73 kq) üçüncü olub.", item["lead"])
        # medal sayı başqa ölkə ilə tam eynidirsə yer yazılmır
        self.assertIsNone(m.medal_rank({"AZE": [1, 0, 0], "FRA": [1, 0, 0], "JPN": [3, 0, 0]}))
        self.assertEqual(m.medal_rank({"AZE": [1, 1, 0], "FRA": [1, 0, 0], "JPN": [3, 0, 0]}), 2)
        self.assertIsNone(m.medal_rank({"FRA": [1, 0, 0]}))
        self.assertEqual(m.medal_table(self.cats("3157"))["AZE"], [2, 1, 2])
        self.assertEqual(m.medal_table(self.cats("3157"))["CRO"], [2, 0, 1])

    def test_missing_incomplete_and_garbage_results(self):
        empty = json.loads('{"totals":{"total":0},"by_categories":[]}')        # nəticəsi hələ olmayan turnirin real cavabı
        self.assertEqual(m.judo_cats(empty), (None, "IJF nəticələri hələ yoxdur"))
        for junk in (None, [], "x", {}, {"by_categories": "x"}):
            self.assertIsNone(m.judo_cats(junk)[0])
        doc = load("ijf-3157-results.json")
        part = copy.deepcopy(doc)
        del part["by_categories"]["2"]                                        # qadınların çəkiləri hələ yoxdur
        self.assertEqual(m.judo_cats(part), (None, "IJF nəticələri natamamdır (7 çəki)"))
        part = copy.deepcopy(doc)
        first = sorted(part["by_categories"]["1"], key=int)[0]
        part["by_categories"]["1"][first]["persons"] = [p for p in part["by_categories"]["1"][first]["persons"] if p["place"] != "1"]
        self.assertEqual(m.judo_cats(part), (None, "-60 kq çəkisində medallar hələ bəlli deyil"))

    def test_names(self):
        self.assertEqual(m.judoka_name({"id_person": "51220", "family_name": "ALIYEVA", "given_name": "Konul"}), "Könül Əliyeva")
        self.assertEqual(m.judoka_name({"id_person": "1", "family_name": "MIRZAYEV", "given_name": "Babarahim"}), "Babarəhim Mirzəyev")
        self.assertEqual(m.judoka_name({"id_person": "2", "family_name": "SMITH", "given_name": "John"}), "John Smith")
        self.assertEqual(m.judoka_name({}), "")
        seen = {}
        for cid in ("3151", "3157", "3205"):
            for c in self.cats(cid):
                for p in c["persons"]:
                    if p["country_short"] == "AZE":
                        seen[p["id_person"]] = m.judoka_name(p)
        self.assertTrue(seen)
        self.assertTrue(set(seen) <= set(m.AZ_JUDOKA))                        # saxlanmış turnirlərdəki hamı lüğətdədir

    def test_leadership_name_blocks_the_item(self):
        with patch.dict(m.AZ_JUDOKA, {"20144": "İlham Əliyev"}):
            self.assertEqual(m.judo_item(judo_ev("3157"), self.cats("3157"), baku(2026, 10, 31, 21, 0)),
                             (None, "mətndə rəhbərliyin adı keçir"))
        item = m._item("cudo", "k", "Prezident İlham Əliyev cüdoçuları qəbul edib", "Giriş.", [], "x", "https://x", baku(2026, 1, 1))
        self.assertEqual(m._finish(item), (None, "mətndə rəhbərliyin adı keçir"))
        long = m._item("cudo", "k", "a" * 111, "Giriş.", [], "x", "https://x", baku(2026, 1, 1))
        self.assertEqual(m._finish(long), (None, "başlıq çox uzundur"))

    def test_make_judo(self):
        make = m.judo_make(judo_ev("3157"))
        fake = Fake()
        self.assertTrue(make(fake, baku(2026, 10, 31, 21, 0))[0]["worth"])
        self.assertEqual(len(fake.urls), 1)
        self.assertIn("params%5Baction%5D=competition.results", fake.urls[0])   # [ ] kodlanır (curl «bad range» xətası)
        self.assertIn("params%5Bid_competition%5D=3157", fake.urls[0])
        self.assertEqual(make(Fake(fail=True), baku(2026, 10, 31, 21, 0)), (None, "IJF alınmadı: OSError"))
        self.assertIsNone(make(Fake(garbage=True), baku(2026, 10, 31, 21, 0))[0])


class UefaTest(unittest.TestCase):
    def facts(self, change=None):
        doc = load("uefa-2027.json")
        if change:
            change(doc)
        f, why = m.uefa_facts(doc)
        self.assertTrue(f, why)
        return f

    def test_facts_from_the_saved_table(self):
        f = self.facts()
        self.assertEqual((f["me"]["pos"], f["me"]["pts"], f["me"]["trend"]), (24, 24.187, "STABLE"))
        self.assertEqual((f["up"]["code"], f["up"]["pts"]), ("UKR", 24.837))
        self.assertEqual((f["down"]["code"], f["down"]["pts"]), ("ISR", 24.125))
        self.assertEqual(f["updated"], utc(2026, 11, 5, 21, 57).replace(second=47))
        for mem in load("uefa-2027.json")["data"]["members"]:
            self.assertIn(mem["member"]["countryCode"], m.UEFA_AZ)

    def test_unchanged_table_is_not_news(self):
        item, why = m.uefa_item(self.facts(), week_of(2026, 11, 6), baku(2026, 11, 6, 11, 0), 2027)
        self.assertFalse(item["worth"])
        self.assertEqual(item["why"], "Azərbaycanın yeri dəyişməyib və klublar bu həftə xal qazanmayıb")
        self.assertEqual(item["key"], "uefa-emsal-2026-11-06")
        self.assertEqual(item["title"], "UEFA reytinqi: Azərbaycan 24,187 xalla 24-cü yerdədir")
        self.assertEqual(item["lead"], "UEFA-nın 6 noyabr tarixli ölkə əmsalları cədvəlində Azərbaycan 24,187 xalla 24-cü yeri tutur.")
        self.assertEqual(item["body"], [
            "Azərbaycan klubları 2026/27 mövsümündə 5,625 xal toplayıb (mövsüm cədvəlində 15-ci yer).",
            "4 klubdan biri avrokuboklarda mübarizəni davam etdirir.",
            "Bir pillə yuxarıda Ukrayna (24,837 xal) və bir pillə aşağıda İsrail (24,125 xal) qərarlaşıb.",
            "Azərbaycan Ukraynadan 0,650 xal geri qalır, İsraildən 0,062 xal öndədir."])
        summer = {"check": baku(2026, 8, 7, 11, 0), "last": None, "az": None}
        item, why = m.uefa_item(self.facts(), summer, baku(2026, 8, 7, 11, 0), 2027)
        self.assertFalse(item["worth"])
        self.assertIn("klubların həftəlik nəticəsi saytda yoxdur", item["why"])

    def test_points_won_this_week_are_news(self):
        item, why = m.uefa_item(self.facts(), week_of(2026, 10, 16), baku(2026, 10, 16, 11, 0), 2027)
        self.assertTrue(item["worth"])
        self.assertNotIn("why", item)
        self.assertTrue(item["lead"].endswith("Azərbaycan klubları bu həftə avrokuboklarda 1 qələbə qazanıb."))
        week = {"check": baku(2026, 10, 16, 11, 0), "last": utc(2026, 10, 15, 19), "az": {"w": 1, "d": 2, "l": 1}}
        item, _ = m.uefa_item(self.facts(), week, baku(2026, 10, 16, 11, 0), 2027)
        self.assertIn("1 qələbə qazanıb və 2 dəfə heç-heçə edib.", item["lead"])
        week["az"] = {"w": 0, "d": 0, "l": 3}                                  # yalnız məğlubiyyət: xal yoxdur
        self.assertFalse(m.uefa_item(self.facts(), week, baku(2026, 10, 16, 11, 0), 2027)[0]["worth"])

    def test_rank_change_is_news(self):
        def aze(trend, pos=None):
            def change(doc):
                for mem in doc["data"]["members"]:
                    if mem["member"]["countryCode"] == "AZE":
                        mem["overallRanking"]["trend"] = trend
                        if pos:
                            mem["overallRanking"]["position"] = pos
                    elif pos and mem["overallRanking"]["position"] == pos:
                        mem["overallRanking"]["position"] = 24
            return change
        week = week_of(2026, 11, 6)
        item, _ = m.uefa_item(self.facts(aze("UP", 23)), week, baku(2026, 11, 6, 11, 0), 2027)
        self.assertTrue(item["worth"])
        self.assertEqual(item["title"], "UEFA reytinqi: Azərbaycan 23-cü pilləyə yüksəlib")
        self.assertIn("Azərbaycan 24,187 xalla 23-cü yerə yüksəlib.", item["lead"])
        self.assertIn("bir pillə aşağıda Ukrayna (24,837 xal) qərarlaşıb.", "\n".join(item["body"]))   # saxta cədvəl: yalnız sıra
        item, _ = m.uefa_item(self.facts(aze("DOWN", 25)), week, baku(2026, 11, 6, 11, 0), 2027)
        self.assertTrue(item["worth"])
        self.assertEqual(item["title"], "UEFA reytinqi: Azərbaycan 25-ci pilləyə düşüb")

    def test_garbage_and_missing_table(self):
        for junk in (None, [], "x", {}, {"data": None}, {"data": {"members": []}}, {"data": {"members": "x"}}):
            self.assertIsNone(m.uefa_facts(junk)[0])
        doc = load("uefa-2027.json")
        no_az = copy.deepcopy(doc)
        no_az["data"]["members"] = [x for x in no_az["data"]["members"] if x["member"]["countryCode"] != "AZE"]
        self.assertEqual(m.uefa_facts(no_az), (None, "Azərbaycan cədvəlin bu səhifəsində yoxdur"))
        no_date = copy.deepcopy(doc)
        del no_date["data"]["lastUpdateDate"]
        self.assertEqual(m.uefa_facts(no_date), (None, "cədvəlin yenilənmə tarixi yoxdur"))

    def test_make_uefa_needs_a_fresh_table(self):
        week = week_of(2026, 11, 6)
        fake = Fake()
        item, why = m.uefa_make(week, 2027)(fake, baku(2026, 11, 6, 11, 0))
        self.assertEqual((item["key"], item["worth"]), ("uefa-emsal-2026-11-06", False))
        self.assertEqual(len(fake.urls), 1)
        self.assertIn("seasonYear=2027", fake.urls[0])
        old = load("uefa-2027.json")
        old["data"]["lastUpdateDate"] = "2026-11-04T21:57:47+0000"            # cümə axşamı oyunlarından əvvəlki cədvəl
        self.assertEqual(m.uefa_make(week, 2027)(Fake(replace={"uefa-2027.json": raw(old)}), baku(2026, 11, 6, 11, 0)),
                         (None, "UEFA cədvəli bu həftənin oyunlarından sonra hələ yenilənməyib"))
        self.assertEqual(m.uefa_make(week, 2027)(Fake(), baku(2026, 11, 5, 11, 0)), (None, "cədvəlin tarixi gələcəkdədir"))
        summer = {"check": baku(2026, 11, 20, 11, 0), "last": None, "az": None}
        self.assertEqual(m.uefa_make(summer, 2027)(Fake(), baku(2026, 11, 20, 11, 0)),
                         (None, "UEFA cədvəli son 3 gündə yenilənməyib"))
        self.assertEqual(m.uefa_make(week, 2027)(Fake(fail=True), baku(2026, 11, 6, 11, 0)), (None, "UEFA alınmadı: OSError"))
        self.assertIsNone(m.uefa_make(week, 2027)(Fake(garbage=True), baku(2026, 11, 6, 11, 0))[0])


class ItemsTest(unittest.TestCase):
    def check_contract(self, items):
        for i in items:
            for k in REQUIRED:
                self.assertIn(k, i, i.get("key"))
            self.assertIsInstance(i["body"], list)
            self.assertRegex(i["slot"], r"^\d\d:\d\d$")
            self.assertEqual(i["topic"], "idman")
            self.assertTrue(i["link"].startswith("https://"))
            if not i["worth"]:
                self.assertTrue(i["why"], i["key"])

    def test_window_done_and_determinism(self):
        fake = Fake()
        self.assertEqual(m.items(SITE, baku(2026, 11, 9, 9, 29), fetch=fake), [])
        self.assertEqual(m.items(SITE, baku(2026, 11, 9, 10, 10), fetch=fake), [])       # pəncərə bağlanıb
        self.assertEqual(m.items(SITE, baku(2026, 11, 9, 9, 40), fetch=fake, done={"f1-2026-r20-yaris"}), [])
        self.assertEqual(fake.urls, [])
        out = m.items(SITE, baku(2026, 11, 9, 9, 30), fetch=fake)
        self.assertEqual([(i["key"], i["worth"], i["slot"], i["date"]) for i in out],
                         [("f1-2026-r20-yaris", True, "09:30", "2026-11-09")])
        self.assertEqual(len(fake.urls), 2)
        self.assertEqual(m.items(SITE, baku(2026, 11, 9, 10, 9), fetch=Fake()), out)     # pəncərənin hər anında eyni xəbər
        self.assertEqual(m.items(SITE, datetime.datetime(2026, 11, 9, 9, 45), fetch=Fake()), out)   # tz-siz vaxt Bakıdır
        self.assertEqual(m.items(SITE, utc(2026, 11, 9, 5, 45), fetch=Fake()), out)
        self.check_contract(out)

    def test_failed_first_try_leaves_the_second_open(self):
        bad = Fake(replace={"f1-2026-20-results.json": OSError("timed out")})
        out = m.items(SITE, baku(2026, 11, 9, 9, 35), fetch=bad)
        self.assertEqual([(i["key"], i["worth"]) for i in out], [("f1-2026-r20-yaris-cehd1", False)])
        self.assertEqual(out[0]["why"], "Jolpica alınmadı: OSError; növbəti cəhd saat 11:30-da")
        self.assertEqual(len(bad.urls), 1)
        self.check_contract(out)
        done = {out[0]["key"]}
        self.assertEqual(m.items(SITE, baku(2026, 11, 9, 9, 45), fetch=bad, done=done), [])   # pəncərədə bir sorğu
        self.assertEqual(len(bad.urls), 1)
        ok = Fake()
        out = m.items(SITE, baku(2026, 11, 9, 11, 30), fetch=ok, done=done)
        self.assertEqual([(i["key"], i["worth"], i["slot"]) for i in out], [("f1-2026-r20-yaris", True, "11:30")])
        out = m.items(SITE, baku(2026, 11, 9, 11, 40), fetch=bad, done=done)             # ikinci cəhd də alınmır
        self.assertEqual([(i["key"], i["worth"], i["why"]) for i in out],
                         [("f1-2026-r20-yaris", False, "Jolpica alınmadı: OSError")])
        self.check_contract(out)

    def test_a_day_in_production_race(self):
        fake = Fake()
        got = run_day(datetime.date(2026, 11, 9), fake)
        self.assertEqual([(i["key"], i["worth"]) for i in got], [("f1-2026-r20-yaris", True)])
        self.assertEqual(len(fake.urls), 2)
        fake = Fake(fail=True)
        got = run_day(datetime.date(2026, 11, 9), fake)
        self.assertEqual([(i["key"], i["worth"]) for i in got],
                         [("f1-2026-r20-yaris-cehd1", False), ("f1-2026-r20-yaris", False)])
        self.assertEqual(len(fake.urls), 2)                                   # hər pəncərədə bir sorğu, təkrar yoxdur
        fake = Fake(fail_first=True)
        got = run_day(datetime.date(2026, 11, 9), fake)
        self.assertEqual([(i["key"], i["worth"]) for i in got],
                         [("f1-2026-r20-yaris-cehd1", False), ("f1-2026-r20-yaris", True)])
        self.assertEqual(len(fake.urls), 3)
        fake = Fake(garbage=True)
        got = run_day(datetime.date(2026, 11, 9), fake, step=30)
        self.assertEqual([i["worth"] for i in got], [False, False])
        self.assertEqual(len(fake.urls), 2)
        self.check_contract(got)

    def test_a_day_in_production_baku_preview(self):
        fake = Fake()
        got = run_day(datetime.date(2026, 9, 24), fake)
        good = [i for i in got if i["worth"]]
        self.assertEqual([i["key"] for i in good], ["f1-2026-r15-onbaxis"])
        self.assertEqual(good[0]["title"], "Formula 1: Azərbaycan Qran-prisi bu həftə sonu Bakıda keçiriləcək")
        self.assertIn("Bu, Bakı Şəhər Halqasında keçirilən 10-cu Formula 1 yarışı olacaq.", good[0]["body"])
        self.assertEqual(len(fake.host("api.jolpi.ca")), 3)
        fake = Fake(fail_first=True)
        got = run_day(datetime.date(2026, 9, 24), fake)
        self.assertEqual(len(fake.host("api.jolpi.ca")), 4)                   # ən ağır hal: 1 + 3
        self.assertLessEqual(len(fake.urls), 6)
        self.assertIn(("f1-2026-r15-onbaxis", True), [(i["key"], i["worth"]) for i in got])
        self.check_contract(got)

    def test_a_day_in_production_judo_and_uefa(self):
        fake = Fake()
        got = run_day(datetime.date(2026, 10, 31), fake)
        self.assertEqual([(i["key"], i["worth"], i["slot"]) for i in got], [("cudo-ijf-3157", True, "21:00")])
        self.assertEqual(len(fake.urls), 1)
        fake = Fake()
        got = run_day(datetime.date(2026, 11, 6), fake)                       # avrokubok həftəsindən sonra: dəyişməyib
        self.assertEqual([(i["key"], i["worth"]) for i in got], [("uefa-emsal-2026-11-06", False)])
        self.assertEqual(len(fake.urls), 1)
        self.check_contract(got)
        empty = b'{"totals":{"total":0},"by_categories":[]}'
        fake = Fake(replace={"ijf-3159-results.json": empty})
        got = run_day(datetime.date(2026, 11, 16), fake)                      # Zaqreb: nəticə hələ yoxdur
        self.assertEqual([(i["key"], i["worth"], i["why"]) for i in got],
                         [("cudo-ijf-3159", False, "IJF nəticələri hələ yoxdur")])
        self.assertEqual(len(fake.urls), 1)
        fake = Fake()
        got = run_day(datetime.date(2026, 8, 17), fake)                       # Lima: medal yoxdur
        self.assertIn(("cudo-ijf-3205", False, "Azərbaycan cüdoçuları medal qazanmayıb"),
                      [(i["key"], i["worth"], i["why"]) for i in got])
        fake = Fake()
        got = run_day(datetime.date(2026, 10, 10), fake)                      # dünya çempionatının son günü + kvalifikasiya
        self.assertIn(("cudo-ijf-3151", True), [(i["key"], i["worth"]) for i in got])
        self.assertLessEqual(len(fake.urls), 6)
        self.assertEqual(len({i["key"] for i in got}), len(got))              # bir hadisə — bir açar
        self.check_contract(got)

    def test_no_requests_outside_the_plan(self):
        for day in (datetime.date(2026, 11, 12), datetime.date(2026, 12, 28), datetime.date(2027, 1, 5),
                    datetime.date(2026, 6, 30), datetime.date(2028, 5, 14)):
            fake = Fake()
            self.assertEqual(run_day(day, fake, step=30), [], day)
            self.assertEqual(fake.urls, [], day)

    def test_every_planned_day_fits_the_budget(self):
        full = {"f1-onbaxis": 2, "f1-siralama": 1, "f1-yaris": 2, "cudo": 1, "uefa-emsal": 1}
        for year in (2026, 2027):
            days = {}
            for e in m.events(SITE, year):
                worst = full[e["kind"]] + (1 if e["key"] == "f1-2026-r15-onbaxis" else 0) + (len(e["tries"]) - 1)
                days[e["tries"][0].date()] = days.get(e["tries"][0].date(), 0) + worst
                self.assertLessEqual(len(e["tries"]), 2)
            self.assertTrue(days)
            self.assertLessEqual(max(days.values()), 6, sorted(days.items(), key=lambda kv: -kv[1])[:3])

    def test_cap_marks_the_extra_items(self):
        def ev(n, kind):
            def make(fetch, at):
                return m._item(kind, f"k{n}", f"Başlıq {n}", "Giriş.", [], "x", "https://x", at), ""
            return {"kind": kind, "key": f"k{n}", "tries": [baku(2026, 11, 9, 9, 30)], "label": "x", "make": make,
                    "credit": "x", "link": "https://x"}
        evs = [ev(1, "f1-onbaxis"), ev(2, "uefa-emsal"), ev(3, "f1-yaris"), ev(4, "cudo"), ev(5, "f1-siralama"), ev(6, "cudo")]
        with patch.object(m, "day_events", return_value=evs):
            out = m.items(SITE, baku(2026, 11, 9, 9, 30), fetch=Fake())
        self.assertEqual([i["key"] for i in out if i["worth"]], ["k3", "k4", "k5", "k6"])   # yarış, sonra cüdo/kvalifikasiya
        extra = [i for i in out if not i["worth"]]
        self.assertEqual([i["key"] for i in extra], ["k2", "k1"])
        self.assertIn("ən çox 4 xəbər", extra[0]["why"])
        self.assertEqual(len(out), 6)                                         # hamısının açarı qayıdır: təkrar sorğu yoxdur

    def test_never_raises(self):
        def boom(fetch, at):
            raise RuntimeError("x")
        e = {"kind": "cudo", "key": "k", "tries": [baku(2026, 11, 9, 9, 30)], "label": "x", "make": boom,
             "credit": "x", "link": "https://x"}
        with patch.object(m, "day_events", return_value=[e]):
            out = m.items(SITE, baku(2026, 11, 9, 9, 30), fetch=Fake())
        self.assertEqual([(i["key"], i["worth"], i["why"]) for i in out], [("k", False, "xəta: RuntimeError")])
        self.assertEqual(m.items(SITE, "2026-11-09", fetch=Fake()), [])
        self.assertEqual(m.items(ROOT / "yoxdur", baku(2026, 11, 9, 9, 30), fetch=Fake(fail=True))[0]["worth"], False)
        with patch.object(m, "day_events", side_effect=RuntimeError("x")):
            self.assertEqual(m.items(SITE, baku(2026, 11, 9, 9, 30), fetch=Fake()), [])


class SinaqTest(unittest.TestCase):
    def test_sinaq_shows_the_last_real_cases(self):
        fake = Fake()
        with patch.object(m, "SEC_PAUSE", 0):
            md = m.sinaq(SITE, baku(2026, 11, 12, 9, 0), fetch=fake)
        text = "\n".join(md)
        for key in ("f1-2026-r20-onbaxis", "f1-2026-r20-siralama", "f1-2026-r20-yaris", "f1-2026-r15-yaris",
                    "cudo-ijf-3151", "cudo-ijf-3157", "uefa-emsal-2026-11-06"):
            self.assertEqual(text.count(f"`{key}`"), 1, key)
        self.assertEqual(text.count("`cudo-ijf-3159`"), 1)                    # plan sətri təkrarlanmır
        self.assertEqual(text.count("✅ Dərc olunardı"), 6)
        self.assertEqual(text.count("⏭ Dərc olunmazdı"), 1)
        self.assertIn("⏭ Dərc olunmazdı: Azərbaycanın yeri dəyişməyib və klublar bu həftə xal qazanmayıb", text)
        self.assertIn("### George Russell Bakıda keçirilən Azərbaycan Qran-prisinin qalibi olub", text)
        self.assertIn("Bu gün üçün planda xəbər yoxdur.", text)
        self.assertNotIn("xəta:", text)
        self.assertNotIn("⚠", text)
        self.assertLessEqual(len(fake.urls), 20)
        self.assertIn(f"Bu sınaq {len(fake.urls)} sorğu göndərdi", text)

    def test_sinaq_survives_dead_sources(self):
        for fake in (Fake(fail=True), Fake(garbage=True)):
            with patch.object(m, "SEC_PAUSE", 0):
                text = "\n".join(m.sinaq(SITE, baku(2026, 11, 12, 9, 0), fetch=fake))
            self.assertEqual(text.count("✅ Dərc olunardı"), 0)
            self.assertEqual(text.count("⏭ Dərc olunmazdı"), 7)
        with patch.object(m, "SEC_PAUSE", 0):
            text = "\n".join(m.sinaq(ROOT / "yoxdur", baku(2026, 9, 24, 11, 10), fetch=Fake()))
        self.assertIn("pəncərədədir", text)

    def test_cli(self):
        out = io.StringIO()
        with patch.object(m, "SEC_PAUSE", 0), patch.object(m, "_default_fetch", lambda: Fake()), contextlib.redirect_stdout(out):
            code = m.main(["--sinaq", "--root", str(SITE), "--now", "2026-11-12T09:00+04:00"])
        self.assertEqual(code, 0)
        self.assertIn("## İdman: Formula 1, cüdo və UEFA ölkə əmsalları (oz_idman2.py)", out.getvalue())
        self.assertIn("Sınaq vaxtı: 12.11.2026 09:00 (Bakı)", out.getvalue())
        err = io.StringIO()
        with contextlib.redirect_stderr(err):
            self.assertEqual(m.main(["--sinaq", "--now", "sabah"]), 2)
        self.assertIn("--now oxunmadı", err.getvalue())


if __name__ == "__main__":
    unittest.main()
