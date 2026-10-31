"""Saytın iki qırmızı xətti (docs/qirmizi-xetler.md). Bu testlər düşürsə, kodu yox, dəyişikliyi yoxlayın."""
import json
import pathlib
import re
import sys
import tempfile
import time
import unittest
from unittest.mock import patch

import content_policy
import updater

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / ".github" / "scripts"))
from check_outputs import enforce_policy  # noqa: E402


def article(source, url, title="Başlıq", category="dunya", **extra):
    return {"id": url, "source": source, "sourceUrl": url, "title": title, "summary": "", "category": category,
            "lang": "az", "publishedAt": "2026-10-30T06:00:00+00:00", **extra}


class SourceListTest(unittest.TestCase):
    def test_every_feed_is_on_the_allowlist_and_none_was_dropped(self):
        names = {f[0] for f in updater.AZ_FEEDS} | {f[0] for f in updater.WORLD_FEEDS}
        self.assertEqual(names - set(content_policy.AZ_SOURCES) - set(content_policy.WORLD_SOURCES), set())
        self.assertEqual(len(updater.FEEDS), len(updater.AZ_FEEDS) + len(updater.WORLD_FEEDS))

    def test_world_feeds_are_registered_as_foreign(self):
        self.assertEqual({f[0] for f in updater.WORLD_FEEDS} - set(content_policy.WORLD_SOURCES), set())
        self.assertEqual({f[0] for f in updater.AZ_FEEDS} & set(content_policy.WORLD_SOURCES), set())

    def test_no_feed_points_at_a_blocked_site(self):
        for feed in updater.FEEDS:
            self.assertFalse(content_policy.is_blocked(feed[1]), feed[0])
        for domains in [*content_policy.AZ_SOURCES.values(), *content_policy.WORLD_SOURCES.values()]:
            for domain in domains:
                self.assertFalse(content_policy.is_blocked("https://" + domain + "/"), domain)

    def test_an_unlisted_feed_cannot_join(self):
        self.assertFalse(content_policy.source_registered("Yeni Sayt"))
        self.assertFalse(content_policy.source_allowed("Yeni Sayt", "https://yenisayt.az/1"))


class ArticleRuleTest(unittest.TestCase):
    def test_link_must_lead_to_the_named_source(self):
        self.assertTrue(content_policy.source_allowed("Day.Az", "https://avia.day.az/1"))
        self.assertTrue(content_policy.source_allowed("Report", "https://www.report.az/1"))
        self.assertFalse(content_policy.source_allowed("Report", "https://report.az.example.com/1"))
        self.assertFalse(content_policy.source_allowed("APA", "https://www.meydan.tv/1"))
        self.assertTrue(content_policy.is_blocked("https://www.azadliq.org/a/1"))
        self.assertFalse(content_policy.is_blocked("https://azadliq.org.example.com/a/1"))

    def test_foreign_sources_do_not_report_on_azerbaijan(self):
        for title in ["Azerbaijan signs a deal", "Azerbaycan açıklaması", "Azərbaycan prezidenti", "Алиев принял делегацию",
                      "Баку ответил Еревану", "Bakü'de zirve", "Talks on the Zangezur corridor", "SOCAR buys a stake",
                      "Pashinyan and Aliyev met", "Karabakh talks resume", "Şuşa'da tören"]:
            self.assertTrue(content_policy.foreign_about_azerbaijan("BBC News", "dunya", title), title)
        for title in ["Bakırköy'de kaza", "Bakan açıklama yaptı", "Storm hits Europe", "Azerice kurs açıldı"]:
            self.assertFalse(content_policy.foreign_about_azerbaijan("BBC News", "dunya", title), title)

    def test_rule_reads_the_summary_too(self):
        self.assertTrue(content_policy.foreign_about_azerbaijan("TASS", "dunya", "Переговоры", "Встреча прошла в Баку"))

    def test_sport_exception_stops_at_leadership(self):
        self.assertFalse(content_policy.foreign_about_azerbaijan("Match TV", "idman", "Карабах вышел в плей-офф"))
        self.assertTrue(content_policy.foreign_about_azerbaijan("Match TV", "idman", "Алиев поздравил футболистов"))

    def test_sport_exception_belongs_to_sport_sites_not_to_the_section(self):
        for source, title in [("BBC News", "Azerbaijan to transfer four detainees"), ("TASS", "В Краснодаре задержали гражданина Азербайджана"),
                              ("Interfax", "В Баку заявили о борьбе с незаконной миграцией"), ("Habertürk", "Karabağ maçı öncesi açıklama")]:
            self.assertTrue(content_policy.foreign_about_azerbaijan(source, "idman", title), title)
        for source in content_policy.SPORT_SOURCES:
            self.assertFalse(content_policy.foreign_about_azerbaijan(source, "idman", "Карабах вышел в плей-офф"), source)
            self.assertIn(source, content_policy.WORLD_SOURCES)

    def test_wider_spellings_are_caught(self):
        for title in ["Karabagh talks", "Nakhichevan visit", "Sumgayit factory", "Ganja was hit", "Azeris protest", "в Гяндже прошли", "Гянджи", "в Шуше открыли",
                      "Бакинский суд", "Ильхам заявил", "Mehriban visited", "Хикмет Гаджиев заявил", "Лачин", "Khojaly", "Hocalı anıldı", "Арцах", "Zakir Hasanov",
                      "ALİYEV açıklama yaptı", "BAKÜ'de toplantı"]:
            self.assertTrue(content_policy.foreign_about_azerbaijan("BBC News", "dunya", title), title)
        for title in ["Bakırköy'de kaza", "Bakan açıklama yaptı", "Azerice kurs açıldı", "Гаджиев забил гол", "Шушукаться не надо", "Organization meets"]:
            self.assertFalse(content_policy.foreign_about_azerbaijan("BBC News", "dunya", title), title)

    def test_only_web_links_pass(self):
        self.assertFalse(content_policy.source_allowed("AZƏRTAC", "javascript://azertag.az/%0aalert(1)"))
        self.assertFalse(content_policy.source_allowed("AZƏRTAC", "data://azertag.az/x"))
        self.assertTrue(content_policy.source_allowed("AZƏRTAC", "https://azertag.az/x"))

    def test_foreign_alternative_is_checked_by_its_own_title(self):
        row = article("APA", "https://apa.az/1", "Avropada güclü fırtına başladı", alts=[
            {"source": "TASS", "sourceUrl": "https://tass.ru/1", "title": "Буря в Европе и заявление Баку"},
            {"source": "Interfax", "sourceUrl": "https://interfax.ru/1", "title": "Буря в Европе"},
        ])
        clean, _ = content_policy.enforce([row])
        self.assertEqual([alt["source"] for alt in clean[0]["alts"]], ["Interfax"])

    def test_every_video_channel_is_on_the_list(self):
        self.assertEqual({name for name, _ in updater.YT_NEWS} - content_policy.VIDEO_CHANNELS, set())

    def test_azerbaijani_sources_are_not_touched_by_the_foreign_rule(self):
        self.assertFalse(content_policy.foreign_about_azerbaijan("APA", "siyaset", "Azərbaycan Prezidenti qəbul edib"))

    def test_gate_removes_violators_and_their_alternatives(self):
        keep = article("APA", "https://apa.az/1", "Azərbaycan Prezidenti qəbul edib", alts=[
            {"source": "Report", "sourceUrl": "https://report.az/1"},
            {"source": "TASS", "sourceUrl": "https://tass.ru/1"},
            {"source": "Azadlıq", "sourceUrl": "https://azadliq.org/1"},
        ])
        rows = [keep, article("BBC News", "https://bbc.co.uk/1", "Azerbaijan news"), article("Yeni Sayt", "https://yenisayt.az/1")]
        clean, dropped = content_policy.enforce(rows)
        self.assertEqual([a["sourceUrl"] for a in clean], ["https://apa.az/1"])
        self.assertEqual([alt["source"] for alt in clean[0]["alts"]], ["Report"])
        self.assertEqual(sum(dropped.values()), 2)

    def test_browser_and_server_read_the_same_rule_file(self):
        self.assertIn('window.CONTENT_POLICY', (ROOT / "assets" / "content-policy.js").read_text(encoding="utf-8"))
        self.assertIn('content-policy.js', (ROOT / "index.html").read_text(encoding="utf-8"))
        self.assertIn('content-policy.js', (ROOT / "sw.js").read_text(encoding="utf-8"))


class ChronicleTest(unittest.TestCase):
    """Zuğulba xronikası: başqa ölkənin prezidenti və ya birinci xanımı ora düşmür, adına söz yazılmır."""

    def label(self, title, lang="az", world=False):
        return updater.categorize(title, "", lang, None, world)

    def test_foreign_leaders_stay_out(self):
        for title in ["Bolsonaru özünü \"prezident\" elan etdi", "Keçmiş prezident dar ağacına gedir",
                      "Ceyhun Bayramovdan diqqətçəkən jest: Özbəkistanın birinci xanımına kömək etdi"]:
            self.assertNotEqual(self.label(title), "Prezident", title)
        self.assertNotEqual(self.label("Первая леди Франции посетила выставку", "ru"), "Prezident")
        self.assertNotEqual(self.label("Azerbaijan's first vice president", "en", True), "Prezident")

    def test_azerbaijani_leadership_stays_in(self):
        for title in ["Prezident İlham Əliyev fərman imzalayıb", "Birinci vitse-prezident Mehriban Əliyeva tədbirdə iştirak edib",
                      "Birinci xanım Bakıda sərgi ilə tanış olub"]:
            self.assertEqual(self.label(title), "Prezident", title)

    def test_social_post_is_not_attributed_to_the_wrong_person(self):
        self.assertIsNone(updater.social_author("ABŞ prezidenti Tramp Truth Social-da paylaşım edib"))
        self.assertIsNone(updater.social_author("Azercell prezidenti sosial şəbəkədə paylaşıb"))
        self.assertIsNone(updater.social_author("Özbəkistanın birinci xanımı paylaşım edib"))
        self.assertEqual(updater.social_author("Prezident İlham Əliyev paylaşım edib")[0], "prezident")
        self.assertEqual(updater.social_author("Birinci vitse-prezident Mehriban Əliyeva paylaşım edib")[0], "birinci-xanim")


class PublishGateTest(unittest.TestCase):
    def test_old_or_foreign_data_is_stripped_before_publishing(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = pathlib.Path(tmp)
            (root / "data").mkdir()
            rows = [article("APA", "https://apa.az/1"), article("TASS", "https://tass.ru/1", "Алиев принял"), article("X", "https://meydan.tv/1")]
            for name in ("news.json", "latest.json"):
                (root / "data" / name).write_text(json.dumps({"articles": rows, "count": 3}), encoding="utf-8")
            enforce_policy(root)
            for name in ("news.json", "latest.json"):
                data = json.loads((root / "data" / name).read_text(encoding="utf-8"))
                self.assertEqual([a["sourceUrl"] for a in data["articles"]], ["https://apa.az/1"])
                self.assertEqual(data["count"], 1)


class FastCycleTest(unittest.TestCase):
    """Sürətli dövrə: ilişən lent gözlənilmir, qapı işləyir, status hər dövrə yazılır."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        root = pathlib.Path(self.tmp.name)
        (root / "data").mkdir()
        names = {"OUT_DIR": root / "data", "OUT_FILE": root / "data" / "news.json", "STATUS_FILE": root / "data" / "status.json",
                 "SOURCES_FILE": root / "data" / "sources.json", "OG_FILE": root / "data" / "og.json", "DATES_FILE": root / "data" / "dates.json",
                 "LATEST_FILE": root / "data" / "latest.json", "CACHE_DIR": root / ".cache", "FEED_CACHE": root / ".cache" / "feeds.json",
                 "SLOW_FEED_CACHE": root / ".cache" / "slow.json", "OFFICIAL_CACHE": root / ".cache" / "official.json",
                 "UNDATED_FILE": root / ".cache" / "undated.json", "RECENT_FILE": root / ".cache" / "recent.json", "GNEWS_CACHE": root / ".cache" / "gnews.json",
                 "GROUPS_FILE": root / ".cache" / "groups.json", "RELABEL_MARK": root / ".cache" / "relabeled"}
        self.patches = [patch.object(updater, key, value) for key, value in names.items()]
        for item in self.patches:
            item.start()
        self.root = root

    def tearDown(self):
        for item in self.patches:
            item.stop()
        self.tmp.cleanup()

    def item(self, link, title):
        return {"title": title, "link": link, "description": "", "pubDate": "Fri, 30 Oct 2026 06:00:00 GMT", "author": "", "image": None}

    def cycle(self, fetcher, official=None):
        feeds = [("APA", "https://apa.az/rss", "az", None), ("BBC News", "https://feeds.bbci.co.uk/x", "en", None), ("Report", "https://report.az/rss", "az", None)]
        with patch.object(updater, "FEEDS", feeds), patch.object(updater, "fetch_feed_fast", fetcher), \
                patch.object(updater, "official_items", official or (lambda: ([], []))), patch.object(updater, "FAST_BUDGET_S", 0.3):
            return updater.run_fast()

    def news(self, name="news.json"):
        return json.loads((self.root / "data" / name).read_text(encoding="utf-8"))["articles"]

    def test_a_hanging_feed_does_not_hold_the_cycle(self):
        def fetcher(feed, old=None):
            if feed[0] == "Report":
                time.sleep(3)
            return {"items": [self.item(f"https://{'apa.az' if feed[0] == 'APA' else 'bbc.co.uk'}/haqqinda-1", "Avropada güclü fırtına başladı")],
                    "url": feed[1], "at": time.time(), "err": None}
        began = time.time()
        code = self.cycle(fetcher)
        self.assertLess(time.time() - began, 2.5)
        self.assertEqual(code, 0)
        self.assertTrue(self.news())
        self.assertIn("cycleSeconds", json.loads((self.root / "data" / "status.json").read_text(encoding="utf-8"))["stats"])

    def test_foreign_azerbaijan_story_and_foreign_link_never_reach_any_file(self):
        def fetcher(feed, old=None):
            items = {"APA": [self.item("https://apa.az/1", "Bakıda yeni park istifadəyə verildi"), self.item("https://meydan.tv/1", "Başqa saytdan gələn xəbər başlığı")],
                     "BBC News": [self.item("https://www.bbc.co.uk/1", "Azerbaijan signs a new agreement"), self.item("https://www.bbc.co.uk/2", "Storm hits the northern coast of Europe")],
                     "Report": []}[feed[0]]
            return {"items": items, "url": feed[1], "at": time.time(), "err": None}
        self.assertEqual(self.cycle(fetcher), 0)
        for name in ("news.json", "latest.json"):
            urls = {a["sourceUrl"] for a in self.news(name)}
            self.assertEqual(urls, {"https://apa.az/1", "https://www.bbc.co.uk/2"}, name)

    def test_a_failed_cycle_keeps_the_feed_and_still_reports_status(self):
        updater.OUT_FILE.write_text(json.dumps({"articles": [article("APA", "https://apa.az/1", "Köhnə xəbər başlığı burada")]}), encoding="utf-8")
        self.assertEqual(self.cycle(lambda feed, old=None: {"items": [], "url": feed[1], "at": 0, "err": "HTTP 500"}), 1)
        self.assertEqual(len(self.news()), 1)
        status = json.loads((self.root / "data" / "status.json").read_text(encoding="utf-8"))
        self.assertFalse(status["ok"])
        self.assertTrue(status["attemptedAt"])

    def test_slow_groups_reach_the_feed_and_merged_links_do_not_return(self):
        url = "https://apa.az/haqqinda-1"
        twin = "https://report.az/haqqinda-1"
        rows = [article("APA", url, "Avropada güclü fırtına başladı", publishedAt="2026-10-30T06:00:00+00:00"),
                article("Report", twin, "Avropada güclü fırtına başladı", publishedAt="2026-10-30T05:59:00+00:00")]
        updater.OUT_FILE.write_text(json.dumps({"articles": rows}), encoding="utf-8")
        updater.compute_groups()
        def fetcher(feed, old=None):
            return {"items": [self.item(url, rows[0]["title"]), self.item(twin, rows[1]["title"])] if feed[0] == "APA" else [],
                    "url": feed[1], "at": time.time(), "err": None}
        self.cycle(fetcher)
        shown = self.news()
        self.assertEqual(len(shown), 1)
        self.assertEqual(len(shown[0]["alts"]), 1)
        self.cycle(fetcher)
        self.assertEqual(len(self.news()), 1)

    def test_fast_cycle_does_not_backfill_with_older_items(self):
        floor = updater.datetime.datetime(2026, 10, 30, 6, 0, tzinfo=updater.datetime.timezone.utc)
        self.assertTrue(updater._older_than("Fri, 30 Oct 2026 05:00:00 GMT", floor))
        self.assertFalse(updater._older_than("Fri, 30 Oct 2026 07:00:00 GMT", floor))
        self.assertFalse(updater._older_than("tarix deyil", floor))

    def test_unchanged_feed_answers_304_without_parsing(self):
        with patch("urllib.request.urlopen", side_effect=updater.urllib.error.HTTPError("u", 304, "x", {}, None)):
            result = updater.fetch_feed_fast(("APA", "https://apa.az/rss", "az", None),
                                             {"items": [{"link": "https://apa.az/1"}], "url": "https://apa.az/rss", "at": 1, "etag": "e"})
        self.assertEqual(result["items"], [{"link": "https://apa.az/1"}])
        self.assertGreater(result["at"], 1)


class PipelineContractTest(unittest.TestCase):
    pipeline = (ROOT / ".github" / "scripts" / "pipeline.sh").read_text(encoding="utf-8")
    workflow = (ROOT / ".github" / "workflows" / "update.yml").read_text(encoding="utf-8")
    watchdog = (ROOT / ".github" / "workflows" / "watchdog.yml").read_text(encoding="utf-8")

    def setting(self, name):
        return int(re.search(rf'^{name}="\$\{{{name}:-(\d+)\}}"', self.pipeline, re.M).group(1))

    def test_cycle_is_at_most_one_minute(self):
        self.assertLessEqual(self.setting("CYCLE"), 60)
        self.assertLess(self.setting("FAST_LIMIT"), 60)
        self.assertLess(updater.FAST_BUDGET_S, self.setting("FAST_LIMIT"))

    def test_slow_work_cannot_block_news(self):
        self.assertIn("slow_loop &", self.pipeline)
        self.assertIn("publish_main &", self.pipeline)

    def test_jobs_overlap_at_handoff(self):
        self.assertNotIn("concurrency:", self.workflow)
        self.assertIn("newer_run_started", self.pipeline)
        self.assertGreater(70 * 60, self.setting("MAX_RUN"))

    def test_every_publish_passes_the_gate(self):
        self.assertIn("guard_outputs\n  promote_code\n  if push_live", self.pipeline)
        self.assertIn("check_outputs.py", self.pipeline)

    def test_broken_checker_cannot_overwrite_last_known_good(self):
        run_py = self.pipeline.split("run_py() {")[1].split("\n}\n")[0]
        self.assertNotIn("copy_code", run_py)
        self.assertIn('"${CUR_RAN:-0}" = 1 ] && [ "${CUR_CHECKED:-0}" = 1', self.pipeline)

    def test_hung_cycle_ends_the_job_but_a_github_outage_does_not(self):
        self.assertIn("self_watch $$", self.pipeline)
        loop = self.pipeline.split("while :; do\n  began=$SECONDS\n  touch")[1]
        self.assertLess(loop.index('touch "$STATE/heartbeat"\n  guard_outputs'), loop.index("push_live"))
        self.assertIn('"$push_fails" -ge "$PUSH_FAILS_MAX"', self.pipeline)
        self.assertNotIn('"$GH" ', self.pipeline.split("# --------------------------------------------------------------------- başlanğıc")[1])

    def test_watchdog_leaves_a_fresh_job_alone(self):
        self.assertIn("fromdateiso8601) < ($(date +%s) - 360)", self.watchdog)

    def test_each_minute_has_its_own_address_because_raw_caches_branch_paths(self):
        sw = (ROOT / "sw.js").read_text(encoding="utf-8")
        self.assertIn("live/m/", sw)
        self.assertIn("LIVE_GRACE_S = 45", sw)
        self.assertIn("65 - $(date +%s) % 60", self.pipeline)
        self.assertIn('m="$(printf', self.pipeline)
        self.assertIn('"$SLOTS/$slot"', self.pipeline)

    def test_live_branch_keeps_no_history(self):
        self.assertIn("commit-tree", self.pipeline)
        self.assertIn("--force", self.pipeline)
        self.assertLessEqual(3600 / self.setting("MAIN_EVERY"), 10)  # GitHub Pages: saatda 10 yığım

    def test_watchdog_restarts_a_stuck_job_and_reports(self):
        self.assertIn("workflow_run", self.watchdog)
        self.assertIn("gh run cancel", self.watchdog)
        self.assertIn("gh issue create", self.watchdog)


class FastCycleReliefTest(unittest.TestCase):
    feed = ("Femida.az", "https://femida.az/rss.xml", "az", None)

    def test_a_dead_feed_stops_holding_the_cycle_after_three_failures(self):
        calls = []
        def dead(feed):
            calls.append(feed[0])
            return feed[0], [], "TimeoutError", feed[1]
        with patch.object(updater, "_fetch_conditional", side_effect=TimeoutError()), patch.object(updater, "fetch_feed", dead):
            entry = None
            for _ in range(5):
                entry = updater.fetch_feed_fast(self.feed, entry)
        self.assertEqual(len(calls), 3)
        self.assertTrue(entry["late"])
        self.assertEqual(entry["err"], "TimeoutError")

    def test_a_paused_feed_is_tried_again(self):
        old = {"items": [{"link": "https://femida.az/1"}], "pausedAt": updater.time.time() - updater.FEED_RETRY_S - 1, "fails": 3}
        with patch.object(updater, "_fetch_conditional", return_value=[{"link": "https://femida.az/2"}]):
            entry = updater.fetch_feed_fast(self.feed, old)
        self.assertEqual(entry["items"], [{"link": "https://femida.az/2"}])
        self.assertFalse(entry.get("pausedAt"))

    def test_our_own_network_failure_pauses_nothing(self):
        feeds = [(f"S{i}", f"https://s{i}.az/rss", "az", None) for i in range(10)]
        def fails(feed, old=None):
            return {"items": [], "err": "DNS", "pausedAt": updater.time.time(), "fails": 3}
        with tempfile.TemporaryDirectory() as tmp, patch.object(updater, "FEEDS", feeds), patch.object(updater, "fetch_feed_fast", fails), \
                patch.object(updater, "official_items", lambda: ([], [])), patch.object(updater, "CACHE_DIR", pathlib.Path(tmp)), \
                patch.object(updater, "FEED_CACHE", pathlib.Path(tmp) / "f.json"), patch.object(updater, "SLOW_FEED_CACHE", pathlib.Path(tmp) / "s.json"), \
                patch.object(updater, "OFFICIAL_CACHE", pathlib.Path(tmp) / "o.json"), patch.object(updater, "GNEWS_CACHE", pathlib.Path(tmp) / "g.json"):
            updater.collect_fast()
            saved = updater._read_json(pathlib.Path(tmp) / "f.json", {})
        self.assertTrue(all(not entry["pausedAt"] for entry in saved.values()))

    def test_one_late_answer_does_not_pause_a_healthy_feed(self):
        def slow(feed, old=None):
            time.sleep(1)
            return {"items": [], "err": None}
        with tempfile.TemporaryDirectory() as tmp, patch.object(updater, "FEEDS", [self.feed]), patch.object(updater, "fetch_feed_fast", slow), \
                patch.object(updater, "official_items", lambda: ([], [])), patch.object(updater, "FAST_BUDGET_S", 0.1), patch.object(updater, "CACHE_DIR", pathlib.Path(tmp)), \
                patch.object(updater, "FEED_CACHE", pathlib.Path(tmp) / "f.json"), patch.object(updater, "SLOW_FEED_CACHE", pathlib.Path(tmp) / "s.json"), \
                patch.object(updater, "OFFICIAL_CACHE", pathlib.Path(tmp) / "o.json"), patch.object(updater, "GNEWS_CACHE", pathlib.Path(tmp) / "g.json"):
            updater.collect_fast()
            saved = updater._read_json(pathlib.Path(tmp) / "f.json", {})
        self.assertEqual(saved[self.feed[0]]["fails"], 1)
        self.assertFalse(saved[self.feed[0]]["pausedAt"])
        self.assertIn(self.feed[0], updater.LATE_FEEDS)

    def test_many_slowly_accumulating_pauses_are_cleared_too(self):
        now = time.time()
        feeds = [(f"S{i}", f"https://s{i}.az/rss", "az", None) for i in range(10)]
        with tempfile.TemporaryDirectory() as tmp, patch.object(updater, "FEEDS", feeds), \
                patch.object(updater, "official_items", lambda: ([], [])), patch.object(updater, "CACHE_DIR", pathlib.Path(tmp)), \
                patch.object(updater, "FEED_CACHE", pathlib.Path(tmp) / "f.json"), patch.object(updater, "SLOW_FEED_CACHE", pathlib.Path(tmp) / "s.json"), \
                patch.object(updater, "OFFICIAL_CACHE", pathlib.Path(tmp) / "o.json"), patch.object(updater, "GNEWS_CACHE", pathlib.Path(tmp) / "g.json"), \
                patch.object(updater, "fetch_feed", lambda feed: (feed[0], [], "x", feed[1])), patch.object(updater, "_fetch_conditional", side_effect=TimeoutError()):
            # Hərəsi fərqli vaxtda dayandırılıb: son bir dəqiqədə yox, son 5 dəqiqədə.
            (pathlib.Path(tmp) / "f.json").write_text(json.dumps({f[0]: {"items": [], "err": "x", "pausedAt": now - 120, "fails": 3} for f in feeds}), encoding="utf-8")
            updater.collect_fast()
            saved = updater._read_json(pathlib.Path(tmp) / "f.json", {})
        self.assertTrue(all(not entry["pausedAt"] for entry in saved.values()))

    def test_answering_late_is_not_counted_as_success(self):
        self.assertIn("cavab gecikir", (ROOT / "updater.py").read_text(encoding="utf-8"))

    def test_official_pages_do_not_wait_for_each_other(self):
        started = []
        def page(url, tries=1, timeout=12):
            started.append(url)
            if "azertag" in url:
                raise TimeoutError("asıldı")
            return ""
        with patch.object(updater, "fetch_text", page):
            items, errors = updater.official_items()
        self.assertEqual(len(started), 3)
        self.assertEqual(len(errors), 1)
        self.assertIn("AZƏRTAC", errors[0])


class BulkDatedFeedTest(unittest.TestCase):
    def test_old_articles_with_a_rewritten_date_are_detected(self):
        items = [{"pubDate": f"Sat, 31 Oct 2026 04:{i % 16:02d}:00 +0400", "link": f"https://marja.az/{i}"} for i in range(100)]
        self.assertTrue(updater.bulk_dated(items))

    def test_a_feed_with_a_stable_date_in_its_links_is_not_touched(self):
        # Azərbaycan qəzeti: lent sorğu vaxtını yazır, əsl tarix keçiddədir (fixed_source_date).
        items = [{"pubDate": f"Sat, 31 Oct 2026 07:{i % 9:02d}:00 +0000", "link": f"https://azerbaijan-news.az/az/posts/detail/x-{1793300000 + i * 900}/{i}"} for i in range(50)]
        self.assertFalse(updater.bulk_dated(items))

    def test_a_busy_real_feed_is_not_touched(self):
        items = [{"pubDate": f"Sat, 31 Oct 2026 {i // 30:02d}:{i * 2 % 60:02d}:00 +0400"} for i in range(120)]
        self.assertFalse(updater.bulk_dated(items))
        self.assertFalse(updater.bulk_dated([{"pubDate": "Sat, 31 Oct 2026 04:00:00 +0400"}] * 20))


class QualityTest(unittest.TestCase):
    def label(self, title, desc=""):
        return updater.categorize(title, desc)

    def test_short_stems_do_not_match_inside_other_words(self):
        self.assertNotEqual(self.label("Avropa kəşfiyyatı həyəcan təbili çalır"), "Texnologiya")
        self.assertNotEqual(self.label("Roman Abramoviç Bakıya gəldi"), "Mədəniyyət")
        self.assertEqual(self.label("Noyabrda 5 bürcü sevgi və pulda yeniliklər gözləyir"), "Həyat")
        self.assertNotEqual(self.label("Kiyevin doqquz rayonunda su təchizatı pozulub"), "Bölgələr")
        self.assertEqual(self.label("Tovuzda avtomobil kanala aşdı"), "Bölgələr")

    def test_ascii_azerbaijani_title_is_not_english(self):
        self.assertEqual(updater.detect_lang("Tehrandan Avropaya", "", "az"), "az")
        self.assertEqual(updater.detect_lang("Zaqatalada qaz olmayacaq", "", "az"), "az")
        self.assertEqual(updater.detect_lang("Azerbaijan, Turkiye discuss solar energy deal", "", "az"), "en")

    def test_same_site_stories_do_not_merge_by_event_similarity(self):
        at = "2026-10-31T01:00:00+00:00"
        row = lambda url, title, src: {"id": url, "sourceUrl": url, "title": title, "source": src, "publishedAt": at, "summary": "", "category": "gundem", "lang": "az"}
        out = updater.group_duplicates([row("https://a.az/1", "Bakıda avtobus qəzaya uğrayıb, sürücü həbs olunub", "A"),
                                        row("https://a.az/2", "Bakıda avtobus sürücüsü qəza törədib və saxlanılıb", "A")])
        self.assertEqual(len(out), 2)

    def test_a_card_counts_each_site_once(self):
        at = "2026-10-31T01:00:00+00:00"
        row = lambda url, src: {"id": url, "sourceUrl": url, "title": "Sabah Şahbuzda işıq olmayacaq bütün gün", "source": src, "publishedAt": at, "summary": "", "category": "gundem", "lang": "az"}
        out = updater.group_duplicates([row("https://a.az/1", "A"), row("https://a.az/2", "A"), row("https://b.az/1", "B")])
        self.assertEqual(len(out), 1)
        self.assertEqual(len({alt["source"] for alt in out[0]["alts"]}), len(out[0]["alts"]))
        self.assertNotIn(out[0]["source"], {alt["source"] for alt in out[0]["alts"]})

    def test_a_wrong_merge_leaves_the_card_when_groups_change(self):
        rows = [{"sourceUrl": "https://a.az/1", "alts": [{"sourceUrl": "https://b.az/9", "source": "B"}]}, {"sourceUrl": "https://c.az/2"}]
        with tempfile.TemporaryDirectory() as tmp, patch.object(updater, "GROUPS_FILE", pathlib.Path(tmp) / "g.json"):
            updater.GROUPS_FILE.write_text('{"https://c.az/2":[{"sourceUrl":"https://d.az/3","source":"D"}]}', encoding="utf-8")
            out = updater.apply_groups(rows)
        self.assertNotIn("alts", out[0])
        self.assertEqual(out[1]["alts"][0]["source"], "D")

    def test_first_minute_of_a_job_keeps_existing_merges(self):
        rows = [{"sourceUrl": "https://a.az/1", "alts": [{"sourceUrl": "https://b.az/9", "source": "B"}]}]
        with tempfile.TemporaryDirectory() as tmp, patch.object(updater, "GROUPS_FILE", pathlib.Path(tmp) / "yoxdur.json"):
            self.assertEqual(updater.apply_groups(rows), rows)

    def test_foreign_sources_have_a_smaller_share(self):
        self.assertLess(updater.MAX_PER_WORLD_SOURCE, updater.MAX_PER_SOURCE)
        self.assertLess(updater.MAX_WORLD + updater.MAX_WORLD_SPORT, updater.FAST_MAX_ITEMS * 0.4)

    def test_a_politics_site_does_not_put_weather_or_football_into_politics(self):
        cat = lambda title, desc="": updater.categorize(title, desc, "az", "Siyasət?")
        self.assertEqual(cat("Noyabrın ilk günü hava necə olacaq? - PROQNOZ"), "Cəmiyyət")
        self.assertEqual(cat("Bu dəfə futbolçular yox, baş məşqçilər dalaşdı + VİDEO"), "İdman")
        self.assertEqual(cat("Ermənistan parlamentindəki qarşıdurmaya görə Rubinyan məsul tutulur"), "Siyasət")
        self.assertEqual(cat("Açıq məktub: kimə sual verək"), "Siyasət")
        self.assertEqual(updater.categorize("Nəcəfli haqqında bir söz", "", "az", "Siyasət"), "Siyasət")

    def test_a_mixed_feed_sends_only_sport_to_the_sports_section(self):
        self.assertEqual(updater.categorize("Oktyabrın son günü yağış yağacaq - HAVA PROQNOZU", "", "az", "İdman?"), "Cəmiyyət")
        self.assertNotEqual(updater.categorize("Sevgilisi ilə barışdı", "", "az", "İdman?"), "İdman")
        self.assertEqual(updater.categorize("Bakıda futbol turniri başladı", "", "az", "İdman?"), "İdman")
        self.assertEqual(updater.categorize("Heç bir idman sözü yoxdur burada", "", "az", "İdman"), "İdman")

    def test_every_new_sport_feed_is_registered_and_marked_as_sport(self):
        for name in ("Qol.az", "Fanat.az"):
            self.assertTrue(content_policy.source_registered(name))
            self.assertIn(name, [f[0] for f in updater.FEEDS])
        world = {f[0]: f for f in updater.FEEDS if f[0] in updater.WORLD_SOURCES}
        for name in content_policy.SPORT_SOURCES:
            self.assertIn(name, world, name)
            self.assertEqual(world[name][3], "İdman", name)

    def test_a_foreign_sports_site_still_cannot_write_about_the_leadership(self):
        row = article("Motorsport F1", "https://www.motorsport.com/1", title="Baku GP: President Aliyev watched the race", category="idman")
        self.assertTrue(content_policy.violation(row))
        race = article("Motorsport F1", "https://www.motorsport.com/2", title="Verstappen wins in Baku", category="idman")
        self.assertFalse(content_policy.violation(race))
        moved = article("Motorsport F1", "https://www.motorsport.com/3", title="Baku talks start", category="siyaset")
        self.assertTrue(content_policy.violation(moved))


class ArchiveTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        root = pathlib.Path(self.tmp.name)
        self.patches = [patch.object(updater, "OUT_FILE", root / "news.json"), patch.object(updater, "ARCHIVE_DIR", root / "arxiv")]
        for p in self.patches:
            p.start()

    def tearDown(self):
        for p in self.patches:
            p.stop()
        self.tmp.cleanup()

    def write(self, *articles):
        updater.OUT_FILE.write_text(updater.json.dumps({"articles": list(articles)}), encoding="utf-8")

    def row(self, url, hours, **extra):
        at = updater.datetime.datetime.now(updater.datetime.timezone.utc) - updater.datetime.timedelta(hours=hours)
        return {"id": url, "title": "Məktəblərdə yeni dərs ili", "summary": "", "source": "APA", "sourceUrl": url, "publishedAt": at.isoformat(), "category": "tehsil", "lang": "az", **extra}

    def rows(self, slug="tehsil"):
        return updater._read_json(updater.ARCHIVE_DIR / f"{slug}.json", {}).get("articles") or []

    def test_items_stay_after_they_leave_the_feed(self):
        self.write(self.row("https://apa.az/1", 2))
        updater.update_archive(now=updater.time.time())
        self.write(self.row("https://apa.az/2", 1))
        updater.update_archive(now=updater.time.time() + 3700)
        self.assertEqual([a["sourceUrl"] for a in self.rows()], ["https://apa.az/2", "https://apa.az/1"])

    def test_written_at_most_once_an_hour(self):
        now = updater.time.time()
        self.write(self.row("https://apa.az/1", 2))
        updater.update_archive(now=now)
        self.write(self.row("https://apa.az/2", 1))
        updater.update_archive(now=now + 600)
        self.assertEqual(len(self.rows()), 1)

    def test_old_and_forbidden_items_are_removed(self):
        self.write(self.row("https://apa.az/1", 6 * 24), self.row("https://azadliq.org/1", 1), self.row("https://apa.az/3", 1))
        updater.update_archive()
        self.assertEqual([a["sourceUrl"] for a in self.rows()], ["https://apa.az/3"])

    def test_archive_repairs_broken_reyting_links(self):
        updater.ARCHIVE_DIR.mkdir(parents=True)
        (updater.ARCHIVE_DIR / "gundem.json").write_text(updater.json.dumps({"at": 1, "articles": [self.row("https://reyting.az/haber/kohne-1.html", 3, source="Reyting.az")]}), encoding="utf-8")
        self.write(self.row("https://apa.az/yeni", 1))
        updater.update_archive()
        self.assertEqual([a["sourceUrl"] for a in self.rows("gundem")], ["https://reyting.az/xeber/kohne-1"])

    def test_merged_sections_carry_their_old_archive_over(self):
        updater.ARCHIVE_DIR.mkdir(parents=True)
        (updater.ARCHIVE_DIR / "texnologiya.json").write_text(updater.json.dumps({"at": 1, "articles": [self.row("https://apa.az/kohne", 3, category="texnologiya")]}), encoding="utf-8")
        self.write(self.row("https://apa.az/yeni", 1), self.row("https://apa.az/kohne-lent", 2, category="texnologiya"))
        updater.update_archive()
        self.assertEqual(sorted(a["sourceUrl"] for a in self.rows()), ["https://apa.az/kohne", "https://apa.az/kohne-lent", "https://apa.az/yeni"])
        self.assertEqual({a["category"] for a in self.rows()}, {"tehsil"})
        self.assertEqual(self.rows("texnologiya"), [])

    def test_merged_sections_have_one_page_each_and_old_addresses_redirect(self):
        slugs = [s[0] for s in updater.SECTIONS]
        self.assertNotIn("sehiyye", slugs)
        self.assertNotIn("texnologiya", slugs)
        with tempfile.TemporaryDirectory() as tmp, patch.object(updater, "SECTIONS_DIR", pathlib.Path(tmp)):
            updater.write_sections([])
            old = (pathlib.Path(tmp) / "sehiyye" / "index.html").read_text(encoding="utf-8")
        self.assertIn("url=../heyat/", old)

    def test_the_presidential_chronicle_has_no_archive(self):
        self.write(self.row("https://apa.az/1", 1))
        updater.update_archive()
        self.assertFalse((updater.ARCHIVE_DIR / "prezident.json").exists())


class ReaderRetiredTest(unittest.TestCase):
    def test_full_texts_are_no_longer_published(self):
        self.assertFalse(updater.READER_ENABLED)
        with tempfile.TemporaryDirectory() as tmp, patch.object(updater, "OUT_DIR", pathlib.Path(tmp)):
            file = pathlib.Path(tmp) / "reader.json"
            file.write_text("{}", encoding="utf-8")
            updater.retire_reader()
            self.assertFalse(file.exists())


class DateFloorTest(unittest.TestCase):
    def test_spaces_in_feed_dates_are_collapsed(self):
        floor = updater.datetime.datetime(2026, 10, 30, 6, 0, tzinfo=updater.datetime.timezone.utc)
        self.assertTrue(updater._older_than("Fri,  30   Oct 2026 05:00:00 GMT", floor))


if __name__ == "__main__":
    unittest.main()
