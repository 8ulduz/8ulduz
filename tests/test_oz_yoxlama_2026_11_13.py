"""2026-11-13 kod yoxlamasında öz xəbər modullarında (oz_*.py) tapılan xətalar: hər test düzəlişdən əvvəl düşürdü.
Şəbəkə yoxdur: saxta sorğu funksiyaları, sabit saat və ya repodakı nümunə faylların surəti."""
import datetime
import json
import pathlib
import tempfile
import unittest

import oz_futbol_az as fa
import oz_futbol_dunya as fd
import oz_hava as oh
import oz_icmal as oi
import oz_maliyye as om
import oz_medeniyyet as omd
import oz_xeber as ox

ROOT = pathlib.Path(__file__).resolve().parent.parent
UTC = datetime.timezone.utc


class LeadershipHoldTest(unittest.TestCase):
    """Sahibin qaydası: Prezident və birinci vitse-prezident adı, vəzifəsi keçən xəbər özü-özünə dərc olunmur."""

    def test_common_ways_of_naming_the_leadership_are_held(self):
        for text in ("Azərbaycan Respublikası Prezidentinin sərəncamı ilə 9 noyabr Dövlət Bayrağı Günü elan edilib",
                     "Prezident İ. Əliyev Türkiyəyə rəsmi səfər edib", "M. Əliyeva Fransada sərginin açılışında iştirak edib",
                     "Dövlətimizin başçısı xalqa müraciət edib", "Ölkə Prezidentinin sərəncamı ilə təltif olunub",
                     "Prezident Əliyev Rusiya Prezidenti ilə görüşüb", "İlham Heydər oğlu Əliyev 1961-ci ildə anadan olub",
                     "Mehriban xanım Əliyeva sərgidə iştirak edib", "Birinci vitse-prezident Türkiyəyə səfər edib",
                     "Dövlət başçısı Türkiyəyə səfər edib", "İLHAM  ƏLİYEV çıxış edib", "PREZİDENTİN FƏRMANI ilə",
                     "Prezident İlham Əliyev çıxış edib", "Birinci xanım Mehriban Əliyeva"):
            self.assertTrue(ox.needs_owner(text), text)

    def test_other_presidents_and_ordinary_news_are_not_held(self):
        for text in ("FIFA prezidenti Bakıya gəlib", "«Qarabağ» klubunun prezidenti açıqlama verib", "Bakıda yağış yağacaq",
                     "ABŞ prezidenti Kennedi 1963-cü ildə öldürülüb", "Mərkəzi Bank məzənnəni açıqladı", "Həkim Əliyeva məsləhət verib"):
            self.assertFalse(ox.needs_owner(text), text)


class FactGateTest(unittest.TestCase):
    RELEASE = ("Saatlı RİH-dən bildirilib ki, noyabrın 5-də tədbirdə 120 nəfər iştirak edib. Ailələrə 5 min manat yardım ayrılıb. "
               "Heç kim kənarda qalmayıb, problem olmayıb.")

    def test_month_scale_word_and_single_quotes_are_checked(self):
        self.assertEqual(ox.fact_gate("Tədbir noyabrın 5-də keçirilib.", self.RELEASE), [])
        self.assertEqual(ox.fact_gate("Ailələrə 5 min manat yardım ayrılıb.", self.RELEASE), [])
        self.assertIn("may", ox.fact_gate("Tədbir mayın 5-də keçirilib.", self.RELEASE), "«may» «olmayıb» sözünün içində tapılmamalıdır")
        self.assertIn("5 milyon", ox.fact_gate("Ailələrə 5 milyon manat yardım ayrılıb.", self.RELEASE))
        self.assertIn("120 min", ox.fact_gate("Tədbirdə 120 min nəfər iştirak edib.", self.RELEASE))
        self.assertTrue(any("verəcəyik" in m for m in ox.fact_gate("Tədbirdə deyilib: ‘Biz hər kəsə 5 min manat verəcəyik’", self.RELEASE)), "‘…’ sitatı da yoxlanır")


class LateGuideTest(unittest.TestCase):
    def test_a_guide_first_built_in_the_evening_is_not_published_and_asks_nothing(self):
        asked = []
        def fetch(url, timeout=None, headers=None):
            asked.append(url)
            raise OSError("şəbəkə")
        late = oi.items(ROOT, datetime.datetime(2026, 11, 20, 22, 30, tzinfo=oi.BAKU), fetch)
        guide = next(i for i in late if i["kind"] == "beledci")
        self.assertEqual((guide["key"], guide["worth"]), ("beledci-2026-11-20", False))
        self.assertIn("gecdir", guide["why"])
        self.assertEqual(asked, [], "gecikmiş bələdçi üçün sorğu getmir")
        oi.items(ROOT, datetime.datetime(2026, 11, 20, 9, 0, tzinfo=oi.BAKU), fetch)
        self.assertTrue(asked, "səhər əvvəlki kimi qurulur")


class StormTest(unittest.TestCase):
    def table(self, now, storm):
        rows, t = [], datetime.datetime(2026, 11, 13, 0, tzinfo=UTC)
        while t < datetime.datetime(2026, 11, 23, 0, tzinfo=UTC):
            past, cur = t + datetime.timedelta(hours=3) <= now, t <= now < t + datetime.timedelta(hours=3)
            rows.append({"time_tag": t.strftime("%Y-%m-%dT%H:%M:%S"), "kp": storm.get(t, 2.0) if past else 2.0,
                         "observed": "observed" if past else "estimated" if cur else "predicted", "noaa_scale": None})
            t += datetime.timedelta(hours=3)
        return json.dumps(rows).encode()

    def run_days(self, storm, moments):
        done, seen = set(), []
        for when in moments:
            now = datetime.datetime.fromisoformat(when).replace(tzinfo=oh.BAKU)
            def fetch(url, timeout=None, headers=None, now=now):
                if url == oh.SWPC_KP:
                    return self.table(now, storm)
                raise OSError("x")
            for item in oh.items(None, now, fetch, done):
                if item["kind"] == "maqnit-qasirgasi":
                    done.add(item["key"])
                    seen.append((when, item["key"], item["worth"]))
        return seen

    def test_a_storm_that_starts_after_the_evening_check_is_reported_next_morning(self):
        # 19 noyabr 19:00–22:00 və 22:00–01:00 (Bakı): axşam sorğusunda (20:10) birinci dövr hələ bitməyib
        storm = {datetime.datetime(2026, 11, 19, 15, tzinfo=UTC): 5.0, datetime.datetime(2026, 11, 19, 18, tzinfo=UTC): 4.67}
        seen = self.run_days(storm, ("2026-11-19T08:40", "2026-11-19T20:10", "2026-11-20T08:40", "2026-11-20T20:10", "2026-11-21T08:40"))
        self.assertEqual([k for _, k, worth in seen if worth], ["maqnit-qasirgasi-2026-11-20"], "dünən yazılmamış qasırğa «davam» sayılmır")

    def test_a_reported_storm_is_still_one_story_over_three_days(self):
        storm = {datetime.datetime(2026, 11, 18, 21, tzinfo=UTC) + datetime.timedelta(hours=3 * n): 6.0 for n in range(18)}  # 19-u 01:00-dan 21-i səhərədək
        seen = self.run_days(storm, ("2026-11-19T08:40", "2026-11-20T08:40", "2026-11-20T20:10", "2026-11-21T08:40", "2026-11-21T20:10"))
        self.assertEqual([k for _, k, worth in seen if worth], ["maqnit-qasirgasi-2026-11-19"], "bir hadisə, bir xəbər")

    def test_kp_nine_minus_is_g4(self):
        self.assertEqual([oh.g_level(k) for k in (8.33, 8.67, 9.0)], [4, 4, 5])
        self.assertAlmostEqual(oh.NORM_MIN[59], 4.0, msg="29 fevral norması qonşu günlərlə uyğundur (əvvəl 3,4 idi)")


class TitlesAndPricesTest(unittest.TestCase):
    def test_afisha_title_without_short_names_falls_back_to_the_count(self):
        day = datetime.date(2026, 11, 17)
        def ev(i, name, venue, hh):
            return {"id": i, "name": name, "when": datetime.datetime(2026, 11, 17, hh, 0, tzinfo=omd.BAKU), "venue": venue,
                    "cat": "concerts", "state": 1, "kind": "concerts"}
        events = [ev(1, "Üzeyir Hacıbəyli adına Azərbaycan Dövlət Simfonik Orkestrinin konserti", "Azərbaycan Dövlət Akademik Filarmoniyası", 19),
                  ev(2, "Qara Qarayev adına Azərbaycan Dövlət Kamera Orkestrinin konserti", "Kamera və orqan musiqisi zalı", 19),
                  ev(3, "Fikrət Əmirov adına Azərbaycan Dövlət Mahnı və Rəqs Ansamblının konserti", "Beynəlxalq Muğam Mərkəzi", 20)]
        item, _ = omd.afisa_item(day, events)
        self.assertEqual(item["title"], "Bu gün Bakı səhnələrində 3 tədbir")
        weekend, _ = omd.hefte_item(datetime.date(2026, 11, 21), [dict(e, when=e["when"].replace(day=21)) for e in events], [])
        self.assertEqual(weekend["title"], "Həftəsonu Bakı səhnələrində 3 tədbir")

    def test_a_stale_ether_price_is_not_published_as_fresh(self):
        now = datetime.datetime(2026, 11, 14, 10, 5, tzinfo=om.BAKU)
        fresh, old = int((now - datetime.timedelta(minutes=3)).timestamp()), int((now - datetime.timedelta(days=3)).timestamp())
        doc = {"bitcoin": {"usd": 74353, "azn": 126401, "usd_24h_change": 0.22, "last_updated_at": fresh},
               "ethereum": {"usd": 2101.44, "azn": 3572.45, "usd_24h_change": -4.69, "last_updated_at": old}}
        item = om.kripto(now, lambda url, timeout=None, headers=None: json.dumps(doc).encode(), set())[0]
        self.assertFalse(item["worth"])
        self.assertIn("efirin qiyməti köhnədir", item["why"])
        doc["ethereum"]["last_updated_at"] = fresh
        self.assertTrue(om.kripto(now, lambda url, timeout=None, headers=None: json.dumps(doc).encode(), set())[0]["worth"])

    def test_a_small_placement_is_not_zero_million(self):
        self.assertEqual(om._mn_title({"term": 364, "placed": 30000.0, "offered": 20000000.0, "wavg": (99.1, 7.25)}),
                         "Maliyyə Nazirliyi 364 günlük istiqrazların 30 000 manatlığını 7,25% orta gəlirliliklə yerləşdirib")
        self.assertEqual(om._mn_title({"term": 364, "placed": 12500000.0, "offered": 20000000.0, "wavg": (99.1, 7.25)}),
                         "Maliyyə Nazirliyi 364 günlük istiqrazların 12,5 milyon manatlığını 7,25% orta gəlirliliklə yerləşdirib")
        self.assertEqual(om._amb_title([{"term": 28, "placed": 300000000.0, "wavg": (99.1, 7.25)}]),
                         "Mərkəzi Bank 300 milyon manatlıq 28 günlük notları 7,25% orta gəlirliliklə yerləşdirib")


def league(games, rows):
    teams = sorted({t for g in games for t in (g["home"], g["away"])})
    return {"key": "2026", "teams": {t: {"name": t.title()} for t in teams}, "games": games, "groups": [{"name": "", "rows": rows}]}


def game(day, home, away, hs=None, as_=None, rnd="4", state=None):
    g = {"date": f"2026-11-{day:02d}T17:00:00+00:00", "home": home, "away": away, "round": rnd, "played": hs is not None}
    if hs is not None:
        g.update(hs=hs, **{"as": as_})
    if state:
        g["state"] = state
    return g


class WorldFootballTest(unittest.TestCase):
    def test_a_games_file_that_misses_earlier_rounds_gives_no_table_facts(self):
        # kl.json kimi: fayl 4-cü turdan başlayır, rəsmi cədvəl isə artıq 3 oyun sayır
        games = [game(26, "a", "b", 2, 0), game(26, "c", "d", 1, 1)]
        rows = [{"team": t, "pos": n + 1, "p": 3, "w": 3 - n % 2, "d": 0, "l": n % 2, "gf": 5, "ga": 2, "pts": 9 - 3 * (n % 2)} for n, t in enumerate("abcd")]
        lg = fd.prep(league(games, rows))
        now = datetime.datetime(2026, 11, 27, 8, 5, tzinfo=fd.BAKU)
        self.assertTrue(lg["partial"])
        self.assertEqual(fd.table(lg, now, now), ([], False), "oyunlardan yığılan «1 oyun, 3 xal» cədvəli yazılmır")
        self.assertEqual(fd.round_facts(lg, "4", now), (None, fd.PARTIAL_WHY))
        # tam fayl: rəsmi cədvəl oyunlarla üst-üstə düşür
        full = fd.prep(league(games, [{"team": "a", "pos": 1, "p": 1, "w": 1, "d": 0, "l": 0, "gf": 2, "ga": 0, "pts": 3},
                                      {"team": "c", "pos": 2, "p": 1, "w": 0, "d": 1, "l": 0, "gf": 1, "ga": 1, "pts": 1},
                                      {"team": "d", "pos": 3, "p": 1, "w": 0, "d": 1, "l": 0, "gf": 1, "ga": 1, "pts": 1},
                                      {"team": "b", "pos": 4, "p": 1, "w": 0, "d": 0, "l": 1, "gf": 0, "ga": 2, "pts": 0}]))
        self.assertFalse(full["partial"])
        self.assertEqual([r["team"] for r in fd.table(full, now, now)[0]][0], "a")

    def test_the_real_conference_league_file_is_recognised_as_partial(self):
        path = ROOT / "data" / "futbol" / "kl.json"
        if not path.exists():
            self.skipTest("kl.json yoxdur")
        doc = json.loads(path.read_text(encoding="utf-8"))
        played = sum(1 for g in doc.get("games") or [] if g.get("played"))
        counted = sum(int(r.get("p") or 0) for grp in doc.get("groups") or [] for r in grp.get("rows") or [])
        if counted <= 2 * played:
            self.skipTest("fayl artıq tamdır")
        self.assertTrue(fd.prep(doc)["partial"])

    def test_a_postponed_game_flagged_off_does_not_hold_the_round_for_ever(self):
        games = [game(7, "a", "b", 1, 0, "11"), game(8, "c", "d", 2, 2, "11"), game(8, "e", "f", rnd="11", state="off")]
        rows = [{"team": t, "pos": n + 1, "p": 0 if t in "ef" else 1, "w": 0, "d": 0, "l": 0, "gf": 0, "ga": 0, "pts": 0} for n, t in enumerate("abcdef")]
        lg = fd.prep(league(games, rows))
        core, late, early = fd._core(lg["rounds"]["11"])
        self.assertEqual(([g["home"] for g in core], [g["home"] for g in late]), (["a", "c"], ["e"]))
        facts, why = fd.round_facts(lg, "11", datetime.datetime(2026, 11, 9, 9, 0, tzinfo=fd.BAKU))
        self.assertEqual(why, "")
        self.assertEqual([g["home"] for g in facts["skipped"]], ["e"], "təxirə salınmış oyunun adı çəkilir, tur isə bitmiş sayılır")
        # tarixi də silinmiş «off» oyunu sıralamanı sındırmır
        games[2]["date"] = ""
        self.assertEqual(fd.round_facts(fd.prep(league(games, rows)), "11", datetime.datetime(2026, 11, 9, 9, 0, tzinfo=fd.BAKU))[1], "")


class AzFootballTest(unittest.TestCase):
    def site(self, name, doc):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        root = pathlib.Path(tmp.name)
        (root / "data" / "futbol").mkdir(parents=True)
        (root / "data" / "futbol" / f"{name}.json").write_text(json.dumps(doc, ensure_ascii=False), encoding="utf-8")
        return root

    def test_second_leg_alone_does_not_send_a_club_through(self):
        doc = json.loads((ROOT / "tests" / "fixtures" / "oz_futbol_az" / "kubok-2025.json").read_text(encoding="utf-8"))
        doc["games"] = [g for g in doc["games"] if g["round"] not in ("1/2 ilk", "1/2 cavab", "Final")]
        first = next(g for g in doc["games"] if g["round"] == "1/4 ilk" and g["home"] == "samaxi")
        first.update(played=False)
        first.pop("hs"), first.pop("as")
        second = next(g for g in doc["games"] if g["round"] == "1/4 cavab" and g["away"] == "samaxi")
        second.update(hs=1, **{"as": 0})
        K = fa._league(self.site("kubok", doc), "kubok")
        event = next(e for e in fa._cup_events(K, {}, ()) if e["key"].endswith("1-4-cavab-yekun"))
        item = fa._build(event, None)
        self.assertNotIn("Qarabağ", item["title"], "ilk oyunun nəticəsi yoxdursa «yüksəlib» yazılmır")


if __name__ == "__main__":
    unittest.main()
