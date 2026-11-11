"""Formula 1, cüdo və UEFA əmsalları üzrə öz xəbərlər (oz_idman2.py). Şəbəkə yoxdur: saxta fetch
tests/fixtures/oz_idman2-dəki real cavabları (Jolpica, IJF, UEFA; 2026-11-10) qaytarır."""
import datetime
import json
import pathlib
import unittest
import urllib.parse

import oz_idman2 as m

ROOT = pathlib.Path(__file__).resolve().parent.parent
FIX = ROOT / "tests" / "fixtures" / "oz_idman2"
SITE = FIX / "site"
BAKU = m.BAKU


def baku(y, mo, d, h=0, mi=0):
    return datetime.datetime(y, mo, d, h, mi, tzinfo=BAKU)


def load(name):
    return json.loads((FIX / name).read_text(encoding="utf-8"))


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
    """Saxta fetch: fixture qaytarır, sorğuları sayır. replace: {fayl adı: bytes və ya Exception}."""

    def __init__(self, replace=None):
        self.urls = []
        self.replace = dict(replace or {})

    def __call__(self, url, timeout=15, headers=None):
        assert timeout <= 15
        self.urls.append(url)
        name = fixture_name(url)
        if name in self.replace:
            v = self.replace[name]
            if isinstance(v, Exception):
                raise v
            return v
        path = FIX / name
        if not path.exists():
            raise OSError("404 " + name)
        return path.read_bytes()


class SmokeTest(unittest.TestCase):
    def test_calendar_matches_saved_api(self):
        races = load("f1-2026.json")["MRData"]["RaceTable"]["Races"]
        self.assertEqual(len(races), len(m.F1_CAL[2026]))
        for r, c in zip(races, m.F1_CAL[2026]):
            self.assertEqual((int(r["round"]), r["raceName"]), (c["round"], c["name"]))
            self.assertEqual(m._ergast_dt(r["date"], r["time"]), c["race"])

    def test_race_item_from_fixture(self):
        f, why = m.race_facts(load("f1-2026-20-results.json"), 2026, 20)
        self.assertTrue(f, why)
        teams = {r["id"]: r["team"] for r in f["rows"]}
        table = m.standings(load("f1-2026-20-driverStandings.json"), 2026, 20, teams)
        item, why = m.race_item(f, table, baku(2026, 11, 9, 9, 30))
        self.assertTrue(item, why)
        self.assertEqual(item["title"], "Lando Norris Braziliya Qran-prisində birinci yerdən start götürüb qalib gəlib")

    def test_items_in_window(self):
        fake = Fake()
        out = m.items(SITE, baku(2026, 11, 9, 9, 35), fetch=fake)
        self.assertEqual([i["key"] for i in out], ["f1-2026-r20-yaris"])
        self.assertEqual(len(fake.urls), 2)

    def test_sinaq_runs(self):
        md = m.sinaq(SITE, baku(2026, 11, 12, 9, 0), fetch=Fake())
        text = "\n".join(md)
        self.assertIn("Dərc olunardı", text)
        self.assertNotIn("xəta:", text)


if __name__ == "__main__":
    unittest.main()
