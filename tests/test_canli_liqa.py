"""Liqa seçiləndə oyunlar və canlı hesab (sahib 2026-11-26: «çempionlar liqası oyunları bitdi. 1 dəq keçdi. cədvəl dəyişmədi …
İstənilən liqanı seçəndə cədvəlin altında və bölmədə oyunlar və canlı skorlar olsun. Bu bütün turnirlərdə bu cür olsun»).

Real məlumat (tests/fixtures/canli_liqa/, 2026-11-25 axşamı): main-dəki data/futbol/cl.json (21:41, 20:00 oyunları hələ oynanmayıb),
cempionsip.json və avroliqa.json-dan kəsiklər; TheSportsDB livescore cavabları (22:12 UTC, futbol və Avroliqa); data/canli.json-un
21:39 (7 ÇL oyunu gedir) və 22:03 (bitib) nüsxələri. liqa-cl-2140.json və liqa-cl-2212.json sayt testlərinin (tests/oyunlar.test.cjs)
işlətdiyi canlı nüsxələrdir: burada eyni girişdən təzədən qurulur və tutuşdurulur."""
import contextlib
import datetime
import io
import json
import pathlib
import tempfile
import unittest
import urllib.error
from unittest.mock import patch

import updater

FIX = pathlib.Path(__file__).parent / "fixtures" / "canli_liqa"
UTC = datetime.timezone.utc


def load(name):
    return json.loads((FIX / name).read_text(encoding="utf-8"))


def at(h, m):
    return datetime.datetime(2026, 11, 25, h, m, tzinfo=UTC)


def rows_2212():
    return updater.tsdb_live_rows(load("livescore-soccer.json")) + updater.tsdb_live_rows(load("livescore-basketball.json")) + \
        updater.canli_live_rows(load("canli-2203.json"))


def live_of(doc, rows, now):
    out = updater.live_league_doc(doc, rows, now)
    return {(g["home"], g["away"]): g.get("live") for g in out["games"]}


class NamesTest(unittest.TestCase):
    def test_the_same_club_under_another_sources_name(self):
        for a, b in [("Atleti", "Atlético Madrid"), ("Shaktar", "Shakhtar Donetsk"), ("PSG", "Paris Saint-Germain"), ("Inter", "Inter Milan"),
                     ("Stuttgart", "VfB Stuttgart"), ("Neftchi Baku", "Neftçi"), ("Sumgayit", "Sumqayıt"), ("Bodo/Glimt", "Bodø/Glimt"),
                     ("Baskonia", "Kosner Baskonia"), ("Club Brugge", "Club Brugge")]:
            self.assertEqual(updater._live_side(a, b), 2, (a, b))

    def test_a_shared_word_is_only_a_maybe_and_other_clubs_are_not_matched(self):
        self.assertEqual(updater._live_side("Man United", "Manchester United"), 1)
        self.assertEqual(updater._live_side("Real Madrid", "Real Betis"), 1, "ortaq «Real» klubu eyniləşdirmir")
        self.assertEqual(updater._live_side("Kapaz", "Kəpəz"), 1)
        self.assertEqual(updater._live_side("Chelsea", "Rubin Kazan"), 0)

    def test_arsenal_tula_does_not_take_the_score_of_arsenals_game(self):
        doc = {"sport": "football", "teams": {"arsenal": {"name": "Arsenal"}, "chelsea": {"name": "Chelsea"}}}
        g = {"date": "2026-11-28T17:30:00+00:00", "home": "arsenal", "away": "chelsea", "played": False}
        row = {"sport": "football", "t": datetime.datetime(2026, 11, 28, 17, 30, tzinfo=UTC), "s": "live", "h": "Arsenal Tula", "a": "Rubin Kazan", "hs": 1, "as": 0}
        self.assertIsNone(updater.match_live(g, doc, [row]), "bir komandanın adı uyğun gəlir, rəqib yox — başqa oyundur")


class HotTest(unittest.TestCase):
    def test_a_league_is_hot_from_30_minutes_before_to_4_hours_after_a_kickoff(self):
        doc = {"games": [{"date": "2026-11-25T20:00:00+00:00", "played": False}]}
        self.assertFalse(updater.league_hot(doc, at(19, 29)))
        self.assertTrue(updater.league_hot(doc, at(19, 31)))
        self.assertTrue(updater.league_hot(doc, at(23, 59)))
        self.assertFalse(updater.league_hot(doc, datetime.datetime(2026, 11, 26, 0, 1, tzinfo=UTC)))
        self.assertFalse(updater.league_hot({"games": [{"date": "2026-11-25T20:00:00+00:00", "state": "off"}]}, at(20, 30)), "təxirə salınan oyun")

    def test_a_game_without_a_time_is_hot_that_night(self):
        doc = {"games": [{"date": "2026-11-25T12:00:00+00:00", "day": True, "played": False}]}
        self.assertFalse(updater.league_hot(doc, at(19, 0)))
        self.assertTrue(updater.league_hot(doc, datetime.datetime(2026, 11, 26, 3, 0, tzinfo=UTC)))


class RealEveningTest(unittest.TestCase):
    """2026-11-25: ÇL-in 20:00 oyunları ~21:53-də bitdi, sayt cədvəli 22:30-a qədər köhnə idi."""

    def test_2140_seven_games_are_live_with_their_score(self):
        live = live_of(load("cl.json"), updater.canli_live_rows(load("canli-2139.json")), at(21, 40))
        running = {k: v for k, v in live.items() if v}
        self.assertEqual(len(running), 7)
        self.assertEqual(running[("paris-saint-germain", "roma")], {"s": "live", "hs": 2, "as": 1})
        self.assertEqual(running[("sporting-cp", "manchester-united")], {"s": "live", "hs": 1, "as": 2})
        self.assertIsNone(live[("sabah", "barcelona")], "mənbənin öz nəticəsi olan oyuna toxunulmur")

    def test_2212_every_champions_league_game_has_its_final_score(self):
        live = live_of(load("cl.json"), rows_2212(), at(22, 12))
        self.assertEqual(sum(1 for v in live.values() if v and v["s"] == "ft"), 7)
        self.assertEqual(live[("atletico-madrid", "viking")], {"s": "ft", "hs": 2, "as": 0})
        self.assertEqual(live[("club-brugge", "liverpool")], {"s": "ft", "hs": 0, "as": 3})
        self.assertEqual(live[("sporting-cp", "manchester-united")], {"s": "ft", "hs": 2, "as": 2},
                         "mənbələr razılaşmır (football-data.org 2:3): eyni oyunun TheSportsDB sətri adla tam uyğundur, o götürülür")

    def test_2212_the_rule_is_the_same_for_the_championship_and_for_basketball(self):
        ch = live_of(load("cempionsip.json"), rows_2212(), at(22, 12))
        self.assertEqual(ch[("bolton-wanderers", "west-bromwich-albion")], {"s": "ft", "hs": 1, "as": 3})
        self.assertEqual(ch[("stoke-city", "millwall")], {"s": "ft", "hs": 2, "as": 1})
        av = live_of(load("avroliqa.json"), rows_2212(), at(22, 12))
        self.assertEqual(av[("kosner-baskonia", "anadolu-efes")], {"s": "ft", "hs": 86, "as": 81})
        self.assertEqual(av[("real-madrid", "zalgiris")], {"s": "ft", "hs": 108, "as": 93})
        football_only = [r for r in rows_2212() if r["sport"] == "football"]
        self.assertFalse(any(live_of(load("avroliqa.json"), football_only, at(22, 12)).values()), "futbol sətri basketbol oyununa düşmür (Real Madrid)")

    def test_the_site_fixtures_are_what_the_updater_writes(self):
        for name, now, rows in (("liqa-cl-2140.json", at(21, 40), updater.canli_live_rows(load("canli-2139.json"))),
                                ("liqa-cl-2212.json", at(22, 12), updater.tsdb_live_rows(load("livescore-soccer.json")) + updater.canli_live_rows(load("canli-2203.json")))):
            self.assertEqual(updater.live_league_doc(load("cl.json"), rows, now), load(name), name)


class FlowTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        root = pathlib.Path(self.tmp.name)
        self.team, self.canli = root / "data" / "futbol", root / "canli"
        self.team.mkdir(parents=True)
        (root / "data" / "canli.json").write_text((FIX / "canli-2203.json").read_text(encoding="utf-8"), encoding="utf-8")
        for name in ("cl", "cempionsip", "avroliqa"):
            (self.team / f"{name}.json").write_text((FIX / f"{name}.json").read_text(encoding="utf-8"), encoding="utf-8")
        self.leagues = [{"id": "cl"}, {"id": "cempionsip"}, {"id": "avroliqa"}, {"id": "../x"}]
        self.patches = [patch.object(updater, "TEAM_DIR", self.team), patch.object(updater, "LIVE_LEAGUE_DIR", self.canli),
                        patch.object(updater, "LIVE_FILE", root / "data" / "canli.json")]
        for p in self.patches:
            p.start()

    def tearDown(self):
        for p in self.patches:
            p.stop()
        self.tmp.cleanup()

    def answer(self, asked):
        def fetch(url, timeout=None, headers=None, data=None):
            asked.append(url)
            return (FIX / ("livescore-basketball.json" if "Basketball" in url else "livescore-soccer.json")).read_bytes()
        return fetch

    def test_one_request_per_sport_only_while_a_league_is_hot_and_finished_rounds_are_due(self):
        asked, stamps = [], {}
        with patch.object(updater, "fetch", self.answer(asked)), contextlib.redirect_stdout(io.StringIO()):
            rows, pending = updater.live_league_rows(self.leagues, stamps, at(22, 12), sleep=lambda s: None)
            self.assertEqual(sorted(u.split("s=")[1] for u in asked), ["Basketball", "Soccer"])
            self.assertTrue(any(r["h"] == "Lille" for r in rows), "data/canli.json sətirləri də")
            self.assertEqual(pending, {"cl": {"5"}, "cempionsip": {"17"}, "avroliqa": {"14"}}, "mənbəsi hələ bitirməyən turlar")
            asked.clear()
            self.assertEqual(updater.live_league_rows(self.leagues, stamps, datetime.datetime(2026, 11, 27, 12, 0, tzinfo=UTC)), ([], {}))
            self.assertEqual(asked, [], "oyun yoxdursa şəbəkə sorğusu yoxdur")

    def test_429_pauses_thesportsdb_for_everybody(self):
        asked, stamps = [], {}
        def busy(url, timeout=None, headers=None, data=None):
            asked.append(url)
            raise urllib.error.HTTPError(url, 429, "Too Many Requests", {}, None)
        with patch.object(updater, "fetch", busy), contextlib.redirect_stdout(io.StringIO()):
            rows, _ = updater.live_league_rows(self.leagues, stamps, at(22, 12), sleep=lambda s: None)
        self.assertEqual(len(asked), 1, "ikinci idman növü soruşulmur")
        self.assertEqual(stamps["until"], "2026-11-25T22:27:00+00:00", "tur sorğuları da (tsdb_refresh) 15 dəqiqə gözləyir")
        self.assertTrue(rows, "data/canli.json sətirləri qalır")

    def test_hot_leagues_get_a_live_copy_and_a_cooled_league_loses_it(self):
        with patch.object(updater, "fetch", self.answer([])), contextlib.redirect_stdout(io.StringIO()):
            rows, _ = updater.live_league_rows(self.leagues, {}, at(22, 12), sleep=lambda s: None)
        self.assertEqual(updater.write_live_leagues(self.leagues, rows, at(22, 12)), ["avroliqa.json", "cempionsip.json", "cl.json"])
        cl = json.loads((self.canli / "cl.json").read_text(encoding="utf-8"))
        self.assertEqual(cl["groups"], load("cl.json")["groups"])
        self.assertEqual(sum(1 for g in cl["games"] if (g.get("live") or {}).get("s") == "ft"), 7)
        (self.canli / "kohne.json").write_text("{}", encoding="utf-8")
        self.assertEqual(updater.write_live_leagues(self.leagues, rows, datetime.datetime(2026, 11, 27, 6, 0, tzinfo=UTC)), [])
        self.assertEqual(list(self.canli.glob("*.json")), [], "soyuyan liqanın nüsxəsi silinir")

    def test_nothing_is_written_when_no_league_is_hot(self):
        empty = pathlib.Path(self.tmp.name) / "bos"
        with patch.object(updater, "LIVE_LEAGUE_DIR", empty):
            self.assertEqual(updater.write_live_leagues(self.leagues, [], datetime.datetime(2026, 12, 25, tzinfo=UTC)), [])
        self.assertFalse(empty.exists(), "qovluq yaranmır (testlər repoda iz qoymur)")


class FinalDueTest(unittest.TestCase):
    NOW = at(22, 12)

    def test_a_round_the_live_source_calls_finished_is_asked_after_3_minutes_not_30(self):
        waiting = [{"date": "2026-11-25T19:45:00+00:00", "played": False, "round": "17"}]
        stamp = (self.NOW - datetime.timedelta(minutes=4)).isoformat()
        self.assertFalse(updater._tsdb_round_due(waiting, stamp, self.NOW), "adi qayda: 30 dəqiqə")
        self.assertTrue(updater._tsdb_round_due(waiting, stamp, self.NOW, final=True))
        self.assertFalse(updater._tsdb_round_due(waiting, (self.NOW - datetime.timedelta(minutes=2)).isoformat(), self.NOW, final=True))
        doc = {"id": "cempionsip", "key": "2026", "groups": [{"rows": [{"p": 16}]}], "games": [dict(waiting[0], round="17"), {"date": "2026-12-20T15:00:00+00:00", "played": False, "round": "22"}]}
        stamps = {"cempionsip": {"season": "2026", "rounds": {str(r): stamp for r in range(1, 47)}}}
        plan = updater._tsdb_plan([doc], stamps, self.NOW, {"cempionsip": {"17"}})
        self.assertEqual(plan[0][3:], ("cempionsip", 17), "«bitdi» deyilən tur növbənin başındadır")

    def test_pfl_and_cups_wait_only_three_minutes_after_a_finished_game(self):
        last = (self.NOW - datetime.timedelta(minutes=4)).isoformat()
        self.assertTrue(updater._final_due({"premyer-liqa": {"12"}}, "premyer-liqa", last, self.NOW))
        self.assertFalse(updater._final_due({"premyer-liqa": {"12"}}, "premyer-liqa", (self.NOW - datetime.timedelta(minutes=1)).isoformat(), self.NOW))
        self.assertFalse(updater._final_due({}, "premyer-liqa", last, self.NOW))


class RedLineTest(unittest.TestCase):
    def test_live_league_work_stays_in_the_slow_cycle_and_off_main(self):
        import inspect
        self.assertNotIn("live_league", inspect.getsource(updater.run_fast), "qırmızı xətt 1: 60 saniyəlik dövrədə şəbəkə yoxdur")
        src = inspect.getsource(updater.update_team_pages)
        self.assertIn("live_league_rows(", src)
        self.assertIn("write_live_leagues(", src)
        self.assertEqual(updater.LIVE_LEAGUE_DIR, updater.ROOT / "canli", "data/-dan kənar: main-ə getmir, yalnız live budağına")
        self.assertTrue(updater.TSDB_LIVE.startswith("https://www.thesportsdb.com/api/v1/json/123/"), "açarsız, pulsuz")


if __name__ == "__main__":
    unittest.main()
