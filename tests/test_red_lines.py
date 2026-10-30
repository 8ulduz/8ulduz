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
        self.assertIn("guard_outputs\n  push_live", self.pipeline)
        self.assertIn("check_outputs.py", self.pipeline)

    def test_each_minute_has_its_own_address_because_raw_caches_branch_paths(self):
        sw = (ROOT / "sw.js").read_text(encoding="utf-8")
        self.assertIn("live/m/", sw)
        self.assertIn("LIVE_GRACE_S = 55", sw)
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


if __name__ == "__main__":
    unittest.main()
