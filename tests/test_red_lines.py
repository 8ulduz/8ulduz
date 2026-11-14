"""Saytın iki qırmızı xətti (docs/qirmizi-xetler.md). Bu testlər düşürsə, kodu yox, dəyişikliyi yoxlayın."""
import datetime
import email.utils
import json
import os
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
                      "Ceyhun Bayramovdan diqqətçəkən jest: Özbəkistanın birinci xanımına kömək etdi",
                      # 2026-11-04: Baku.ws-in bu xəbəri Zuğulbaya düşmüşdü — ölkə adı defislə («ABŞ-nin») tanınmırdı
                      "ABŞ-nin birinci xanımı Oleşkidə atəşkəslə bağlı diplomatik görüş təşkil edəcək",
                      "Fransanın birinci xanımı Brijit Makron sərgi açıb",
                      "Türkiyənin birinci xanımı Əminə Ərdoğan Bakıya gəlib",
                      "Birinci xanım Melaniya Tramp uşaqlarla görüşüb",
                      "Birinci xanımı qarşılayan nazir istefa verdi"]:
            self.assertNotEqual(self.label(title), "Prezident", title)
        self.assertNotEqual(self.label("Первая леди Франции посетила выставку", "ru"), "Prezident")
        self.assertNotEqual(self.label("Azerbaijan's first vice president", "en", True), "Prezident")

    def test_azerbaijani_leadership_stays_in(self):
        for title in ["Prezident İlham Əliyev fərman imzalayıb", "Birinci vitse-prezident Mehriban Əliyeva tədbirdə iştirak edib",
                      "Birinci xanım Bakıda sərgi ilə tanış olub",
                      "Azərbaycanın birinci xanımı sərgi ilə tanış olub",
                      "Birinci xanım Mehriban Əliyeva Türkiyə Prezidentinin xanımı ilə görüşüb",
                      "Birinci xanım Mehriban Əliyeva Fransaya səfər edib"]:
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
            for name in ("news.json", "latest.json", "first.json", "latest.az.json", "news.en.json"):
                (root / "data" / name).write_text(json.dumps({"articles": rows, "count": 3}), encoding="utf-8")
            enforce_policy(root)
            for name in ("news.json", "latest.json", "first.json", "latest.az.json", "news.en.json"):
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
                 "LATEST_FILE": root / "data" / "latest.json", "LINK_HEALTH_FILE": root / ".cache" / "link_health.json", "FIRST_FILE": root / "data" / "first.json", "CACHE_DIR": root / ".cache", "FEED_CACHE": root / ".cache" / "feeds.json",
                 "SLOW_FEED_CACHE": root / ".cache" / "slow.json", "OFFICIAL_CACHE": root / ".cache" / "official.json",
                 "UNDATED_FILE": root / ".cache" / "undated.json", "RECENT_FILE": root / ".cache" / "recent.json", "GNEWS_CACHE": root / ".cache" / "gnews.json",
                 "GROUPS_FILE": root / ".cache" / "groups.json", "RELABEL_MARK": root / ".cache" / "relabeled",
                 # main() hər dövrədə Google News sitemap-ı da yazır: yamaqsız test repodakı əsl sitemap-news.xml-i boşaldırdı
                 "NEWS_SITEMAP_FILE": root / "sitemap-news.xml"}
        self.patches = [patch.object(updater, key, value) for key, value in names.items()]
        for item in self.patches:
            item.start()
        self.root = root

    def tearDown(self):
        for item in self.patches:
            item.stop()
        self.tmp.cleanup()

    def item(self, link, title):
        # Tarix nisbi: sabit «30 Oct 2026» 5 gündən köhnə olanda lentdən kəsilirdi və ikinci dövrə testləri sakitcə başqa yolla keçirdi
        pub = email.utils.format_datetime(datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(hours=2))
        return {"title": title, "link": link, "description": "", "pubDate": pub, "author": "", "image": None}

    def cycle(self, fetcher, official=None, feeds=None):
        feeds = feeds or [("APA", "https://apa.az/rss", "az", None), ("BBC News", "https://feeds.bbci.co.uk/x", "en", None), ("Report", "https://report.az/rss", "az", None)]
        with patch.object(updater, "FEEDS", feeds), patch.object(updater, "fetch_feed_fast", fetcher), \
                patch.object(updater, "official_items", official or (lambda: ([], []))), patch.object(updater, "FAST_BUDGET_S", 0.3):
            return updater.run_fast()

    def news(self, name="news.json"):
        return json.loads((self.root / "data" / name).read_text(encoding="utf-8"))["articles"]

    def test_image_added_to_the_feed_later_reaches_the_story(self):
        link = "https://apa.az/haqqinda-1"
        def feed(image):
            def fetcher(feed, old=None):
                rows = [dict(self.item(link, "Avropada güclü fırtına başladı"), image=image)] if feed[0] == "APA" else []
                return {"items": rows, "url": feed[1], "at": time.time(), "err": None}
            return fetcher
        self.cycle(feed(None))
        self.assertFalse(next(a for a in self.news() if a["sourceUrl"] == link).get("imageUrl"))
        self.cycle(feed("https://apa.az/sekil.jpg"))
        self.assertEqual(next(a for a in self.news() if a["sourceUrl"] == link)["imageUrl"], "https://apa.az/sekil.jpg")

    def test_president_page_is_read_even_when_every_feed_worker_is_busy(self):
        # Sahib, 2026-11-10: «niyə prezident.az-dan əvvəldən çəkmirik?» — rəsmi səhifə lentlərin növbəsinin sonunda qalırdı.
        link = "https://president.az/az/articles/view/74616"
        def slow(feed, old=None):
            time.sleep(1)
            return {"items": [], "url": feed[1], "at": time.time(), "err": None}
        official = lambda: ([("Prezident.az", "az", "Prezident", "Prezident", self.item(link, "İlham Əliyev Türkiyəyə səfərə getdi"))], [])
        with patch.object(updater, "FAST_WORKERS", 1):
            self.cycle(slow, official=official)
        self.assertTrue(any(a["sourceUrl"] == link for a in self.news()), "president.az xəbəri lentlər gecikəndə də həmin dövrədə gəlir")

    def test_a_retitled_story_keeps_one_record(self):
        """Eyni mənbənin eyni nömrəli xəbəri yeni başlıq və slug ilə gələndə ikinci qeyd yaranmır: başlıq yenilənir, keçid və nömrə qalır."""
        def feed_with(link, title):
            def fetcher(feed, old=None):
                rows = [self.item(link, title)] if feed[0] == ("Report" if "report.az" in link else "APA") else []
                return {"items": rows, "url": feed[1], "at": time.time(), "err": None}
            return fetcher
        self.cycle(feed_with("https://apa.az/europe/tbiliside-yangin-baslayib-1011019", "Tbilisidə telekanal binasında yanğın başlayıb"))
        first = [a for a in self.news() if "apa.az" in a["sourceUrl"]]
        self.assertEqual(len(first), 1)
        self.cycle(feed_with("https://apa.az/europe/tbiliside-yangin-sondurulub-yenilenib-1011019", "Tbilisidə telekanal binasında yanğın söndürülüb - YENİLƏNİB"))
        rows = [a for a in self.news() if "apa.az" in a["sourceUrl"]]
        self.assertEqual(len(rows), 1, "eyni nömrəli xəbər iki dəfə düşməməlidir")
        self.assertEqual(rows[0]["sourceUrl"], "https://apa.az/europe/tbiliside-yangin-baslayib-1011019")
        self.assertEqual(rows[0]["id"], first[0]["id"], "paylaşılan keçid dəyişmir")
        self.assertIn("söndürülüb", rows[0]["title"])
        # başqa sayt eyni nömrə ilə ayrı xəbərdir
        self.cycle(feed_with("https://report.az/az/hadise/basliq-1011019", "Bakıda yol qəzası olub"))
        self.assertEqual(len([a for a in self.news() if a["sourceUrl"].endswith("1011019")]), 2)

    def feed_of(self, source, rows):
        def fetcher(feed, old=None):
            return {"items": rows if feed[0] == source else [], "url": feed[1], "at": time.time(), "err": None}
        return fetcher

    def test_a_retitled_alt_source_does_not_overwrite_another_outlets_card(self):
        """Açar qeydin əlavə mənbəsinə aiddirsə yeni başlıq o mənbəyə yazılır: əsas mənbənin (başqa saytın) başlığı dəyişmir."""
        when = datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds")
        alt = {"source": "Report", "sourceUrl": "https://report.az/az/hadise/kohne-basliq-528168", "title": "Bakıda yeni məktəb açıldı", "publishedAt": when, "lang": "az"}
        row = {"id": "a" * 16, "source": "APA", "sourceUrl": "https://apa.az/sosial/bakida-mekteb-1234567", "title": "Bakıda yeni məktəb binası istifadəyə verildi",
               "summary": "APA-nın xülasəsi", "category": "tehsil", "lang": "az", "publishedAt": when, "alts": [alt]}
        updater.OUT_FILE.write_text(json.dumps({"articles": [row]}), encoding="utf-8")
        self.cycle(self.feed_of("Report", [dict(self.item("https://report.az/az/hadise/yeni-basliq-528168", "Nazir yeni məktəbdəki çatışmazlıqları tənqid etdi"), description="Report-un xülasəsi")]))
        got = [a for a in self.news() if a["sourceUrl"] == row["sourceUrl"]]
        self.assertEqual(len(got), 1)
        self.assertEqual((got[0]["title"], got[0]["summary"]), (row["title"], row["summary"]), "APA kartı Report-un başlığını almamalıdır")
        self.assertEqual([x["title"] for x in got[0].get("alts") or []], ["Nazir yeni məktəbdəki çatışmazlıqları tənqid etdi"])
        self.assertFalse([a for a in self.news() if "report.az" in a["sourceUrl"]], "eyni nömrəli xəbər ayrıca qeyd kimi qayıtmır")

    def test_a_retitle_passes_the_same_filters_as_a_new_story(self):
        """QIRMIZI XƏTT 2: məlum xəbər süzgəcdən keçməyən başlıqla yenilənəndə həmin dövrədə lentdən çıxır (əvvəl bir dövrə qalırdı)."""
        self.cycle(self.feed_of("APA", [self.item("https://apa.az/siyaset/iclas-kecirilib-528169", "Milli Məclisdə iclas keçirilib"), self.item("https://apa.az/hava-528100", "Bakıda hava şəraiti dəyişəcək")]))
        self.assertEqual(len(self.news()), 2)
        self.cycle(self.feed_of("APA", [self.item("https://apa.az/siyaset/qalmaqal-528169", "Milli Məclisdə korrupsiya qalmaqalı"), self.item("https://apa.az/hava-528100", "Bakıda hava şəraiti dəyişəcək")]))
        self.assertTrue(updater.is_negative_about_leadership("Milli Məclisdə korrupsiya qalmaqalı", ""))
        for name in ("news.json", "latest.json", "first.json"):
            self.assertEqual([a["sourceUrl"] for a in self.news(name)], ["https://apa.az/hava-528100"], name)

    def test_two_stories_with_the_same_date_code_keep_their_own_titles(self):
        """Slugun sonundakı gün kodu (Al Jazeera «…-111126») xəbər nömrəsi deyil: eyni günün iki xəbəri bir-birinin başlığını almır."""
        code = datetime.datetime.now(updater.BAKU).strftime("%d%m%y")
        feeds = [("Al Jazeera", "https://www.aljazeera.com/xml/rss/all.xml", "en", None)]
        guard = self.item(f"https://www.aljazeera.com/video/newsfeed/2026/11/12/guard-collapses-{code}", "French guard collapses as Macron rushes to help")
        mother = self.item(f"https://www.aljazeera.com/video/newsfeed/2026/11/12/mother-reunites-{code}", "Mother reunites with sons taken 40 years ago")
        self.assertIsNone(updater.story_key(guard["link"]))
        self.cycle(self.feed_of("Al Jazeera", [guard]), feeds=feeds)
        self.cycle(self.feed_of("Al Jazeera", [mother, guard]), feeds=feeds)
        self.cycle(self.feed_of("Al Jazeera", [mother, guard]), feeds=feeds)
        self.assertEqual({a["sourceUrl"]: a["title"] for a in self.news()}, {guard["link"]: guard["title"], mother["link"]: mother["title"]})

    def test_an_unreadable_date_is_an_undated_item_not_a_new_story_every_minute(self):
        """Oxunmayan pubDate «indi» damğası almır: tarix yavaş prosesdən (dates.json) gəlir və sonra dəyişmir."""
        link = "https://apa.az/tarixi-oxunmayan-1"
        row = dict(self.item(link, "Tarixi oxunmayan lentin xəbəri"), pubDate="13/11/2026 saat 10:00")
        self.assertIsNone(updater._pub_dt(row["pubDate"]))
        self.cycle(self.feed_of("APA", [row]))
        self.assertFalse(self.news() if (self.root / "data" / "news.json").exists() else [], "tarix tapılana qədər lentə düşmür")
        stamp = updater._norm_iso(datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(hours=3))
        updater.DATES_FILE.write_text(json.dumps({link: stamp}), encoding="utf-8")
        self.cycle(self.feed_of("APA", [row]))
        self.cycle(self.feed_of("APA", [row]))
        self.assertEqual([(a["sourceUrl"], a["publishedAt"]) for a in self.news()], [(link, stamp)])

    def first_screen_feed(self, feed, old=None):
        rows = [self.item("https://apa.az/ilk-1", "Avropada güclü fırtına başladı")] if feed[0] == "APA" else []
        return {"items": rows, "url": feed[1], "at": time.time(), "err": None}

    def test_every_cycle_writes_the_first_screen_with_the_news(self):
        self.cycle(self.first_screen_feed)
        self.assertEqual([a["sourceUrl"] for a in self.news("first.json")], ["https://apa.az/ilk-1"])

    def test_a_failing_first_screen_does_not_stop_the_news(self):
        with patch.object(updater, "first_screen_rows", side_effect=ValueError("sınaq")):
            self.cycle(self.first_screen_feed)
        self.assertEqual([a["sourceUrl"] for a in self.news()], ["https://apa.az/ilk-1"])
        self.assertFalse((self.root / "data" / "first.json").exists())

    def link_feed(self, feed, old=None):
        rows = [self.item("https://apa.az/olu-1", "Avropada güclü fırtına başladı"), self.item("https://apa.az/saglam-2", "Asiyada böyük zəlzələ qeydə alındı")] if feed[0] == "APA" else []
        return {"items": rows, "url": feed[1], "at": time.time(), "err": None}

    def test_a_dead_link_leaves_the_news_and_comes_back_when_fixed(self):
        (self.root / ".cache").mkdir(exist_ok=True)
        health = self.root / ".cache" / "link_health.json"
        self.cycle(self.link_feed)
        self.assertEqual(len(self.news()), 2)
        health.write_text(json.dumps({"https://apa.az/olu-1": {"dead": True, "at": time.time(), "since": time.time()}}), encoding="utf-8")
        self.cycle(self.link_feed)
        self.assertEqual([a["sourceUrl"] for a in self.news()], ["https://apa.az/saglam-2"])
        self.assertEqual(json.loads((self.root / "data" / "latest.json").read_text(encoding="utf-8"))["dead"], ["https://apa.az/olu-1"])
        health.write_text("{}", encoding="utf-8")
        self.cycle(self.link_feed)
        self.assertEqual(len(self.news()), 2)

    def test_the_news_cycle_never_checks_links_itself(self):
        with patch.object(updater, "link_status", side_effect=AssertionError("xəbər dövrəsi linkə sorğu göndərməməlidir")):
            self.cycle(self.link_feed)
        self.assertEqual(len(self.news()), 2)

    def test_a_broken_link_file_or_failure_does_not_stop_the_news(self):
        (self.root / ".cache").mkdir(exist_ok=True)
        (self.root / ".cache" / "link_health.json").write_text("{pozuq", encoding="utf-8")
        self.cycle(self.link_feed)
        self.assertEqual(len(self.news()), 2)
        with patch.object(updater, "drop_dead_links", side_effect=ValueError("sınaq")):
            self.cycle(self.link_feed)
        self.assertEqual(len(self.news()), 2)

    def test_too_many_dead_links_are_not_believed(self):
        (self.root / ".cache").mkdir(exist_ok=True)
        many = {f"https://apa.az/{i}": {"dead": True, "at": 1, "since": 1} for i in range(updater.LINK_DEAD_MAX + 1)}
        (self.root / ".cache" / "link_health.json").write_text(json.dumps(many), encoding="utf-8")
        self.assertEqual(updater.dead_links(100), set())
        self.assertEqual(len(updater.dead_links(1000)), updater.LINK_DEAD_MAX + 1)

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

    def test_each_language_has_its_own_minute_file_and_the_shared_file_keeps_all(self):
        def fetcher(feed, old=None):
            items = {"APA": [self.item("https://apa.az/1", "Bakıda yeni park istifadəyə verildi")],
                     "BBC News": [self.item("https://www.bbc.co.uk/2", "Storm hits the northern coast of Europe")],
                     "Report": []}[feed[0]]
            return {"items": items, "url": feed[1], "at": time.time(), "err": None}
        with patch.dict(os.environ):
            os.environ.pop("LATEST_LANG_FILES", None)
            self.assertEqual(self.cycle(fetcher), 0)
        urls = lambda name: [a["sourceUrl"] for a in self.news(name)]
        self.assertEqual(urls("latest.az.json"), ["https://apa.az/1"])
        self.assertEqual(urls("latest.en.json"), ["https://www.bbc.co.uk/2"])
        self.assertEqual(urls("latest.ru.json"), [])
        self.assertEqual(set(urls("latest.json")), {"https://apa.az/1", "https://www.bbc.co.uk/2"})
        self.assertEqual(json.loads((self.root / "data" / "latest.az.json").read_text(encoding="utf-8"))["count"], 1)
        status = json.loads((self.root / "data" / "status.json").read_text(encoding="utf-8"))
        self.assertNotIn("langs", status, "köhnə pipeline.sh dil fayllarını live-ə yazmır: sayt onları istəməsin")
        with patch.dict(os.environ, {"LATEST_LANG_FILES": "1"}):
            self.assertEqual(self.cycle(fetcher), 0)
        status = json.loads((self.root / "data" / "status.json").read_text(encoding="utf-8"))
        self.assertEqual(status["langs"], ["az", "en", "ru", "tr"])

    def test_full_feed_is_split_by_language_only_with_the_new_pipeline(self):
        """QIRMIZI XƏTT 3: azərbaycanca oxucu news.json-dan öz sətirlərini (+ xarici idman: idman bölməsi bütün dillərdədir) çəkir,
        ingilis/rus/türk oxucu news.<dil>.json-dan yalnız öz dilini; bayraqsız (köhnə pipeline) hər şey əvvəlki kimi bir fayldadır."""
        feeds = [("APA", "https://apa.az/rss", "az", None), ("BBC News", "https://feeds.bbci.co.uk/x", "en", None),
                 ("Match TV", "https://matchtv.ru/news/rss", "ru", "İdman"), ("Report", "https://report.az/rss", "az", None)]
        fresh = lambda link, title: {**self.item(link, title), "pubDate": time.strftime("%a, %d %b %Y %H:%M:%S GMT", time.gmtime())}
        # Hər dövrədə yalnız APA-dan yeni xəbər gəlir (dəyişiklik olmayanda main() faylı yazmır); BBC və Match TV yalnız birinci dövrədədir,
        # sonra əvvəlki lentdən (bölünmüş fayllardan) daşınmalıdır (qırmızı xətt 1).
        def fetcher(feed, old=None, step=1):
            apa = {1: fresh("https://apa.az/1", "Bakıda yeni park istifadəyə verildi"), 2: fresh("https://apa.az/2", "Metroda yeni qatarlar işə düşdü"),
                   3: fresh("https://apa.az/3", "Hava limanında yeni terminal açıldı")}[step]
            items = {"APA": [apa], "Report": [],
                     "BBC News": [fresh("https://www.bbc.co.uk/2", "Storm hits the northern coast of Europe")] if step == 1 else [],
                     "Match TV": [fresh("https://matchtv.ru/5", "Карабах вышел в плей-офф")] if step == 1 else []}[feed[0]]
            return {"items": items, "url": feed[1], "at": time.time(), "err": None}
        urls = lambda name="news.json": [a["sourceUrl"] for a in self.news(name)]
        with patch.dict(os.environ):
            os.environ.pop("NEWS_LANG_FILES", None)
            self.assertEqual(self.cycle(fetcher, feeds=feeds), 0)
            self.assertEqual(set(urls()), {"https://apa.az/1", "https://www.bbc.co.uk/2", "https://matchtv.ru/5"}, "bayraqsız hər şey bir faylda")
            self.assertFalse((self.root / "data" / "news.en.json").exists())
            self.assertNotIn("newsLangs", json.loads((self.root / "data" / "status.json").read_text(encoding="utf-8")))
            os.environ["NEWS_LANG_FILES"] = "1"
            self.assertEqual(self.cycle(lambda feed, old=None: fetcher(feed, step=2), feeds=feeds), 0)
        self.assertEqual(set(urls()), {"https://apa.az/1", "https://apa.az/2", "https://matchtv.ru/5"}, "azərbaycanca + xarici idman; ingilis sətri burada deyil")
        self.assertEqual(urls("news.en.json"), ["https://www.bbc.co.uk/2"], "BBC bu dövrədə gəlməsə də əvvəlki lentdən daşınır")
        self.assertEqual(urls("news.ru.json"), ["https://matchtv.ru/5"])
        self.assertEqual(urls("news.tr.json"), [])
        data = json.loads((self.root / "data" / "news.json").read_text(encoding="utf-8"))
        self.assertEqual((data["langs"], data["count"]), (["en", "ru", "tr"], 3))
        self.assertEqual(json.loads((self.root / "data" / "status.json").read_text(encoding="utf-8"))["newsLangs"], ["en", "ru", "tr"])
        self.assertEqual(sorted(a["sourceUrl"] for a in updater.read_feed()),
                         ["https://apa.az/1", "https://apa.az/2", "https://matchtv.ru/5", "https://www.bbc.co.uk/2"], "birləşmiş lentdə hər keçid bir dəfə")
        # Üçüncü dövrə əvvəlki lenti bölünmüş fayllardan oxuyur: dil faylındakı xəbər itmir
        with patch.dict(os.environ, {"NEWS_LANG_FILES": "1"}):
            self.assertEqual(self.cycle(lambda feed, old=None: fetcher(feed, step=3), feeds=feeds), 0)
        self.assertEqual(urls("news.en.json"), ["https://www.bbc.co.uk/2"], "ingilis sətri dil faylından daşınır")
        self.assertEqual(set(urls()), {"https://apa.az/1", "https://apa.az/2", "https://apa.az/3", "https://matchtv.ru/5"})

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

    def test_language_minute_files_go_only_to_the_live_branch(self):
        self.assertIn("for name in status latest latest.az latest.en latest.ru latest.tr markets", self.pipeline)
        self.assertIn('rm -f "$REPO_DIR"/data/latest.??.json', self.pipeline)
        self.assertIn("export LATEST_LANG_FILES=1", self.pipeline)
        self.assertEqual(updater.FEED_LANGS, ("az", "en", "ru", "tr"))

    def test_full_feed_language_files_stay_on_main_behind_the_flag(self):
        self.assertIn("export NEWS_LANG_FILES=1", self.pipeline)
        self.assertNotIn("news.??.json", self.pipeline)  # dil faylları main-dədir: publish_main yalnız latest.??.json-u silir
        self.assertEqual(updater.NEWS_LANGS, ("en", "ru", "tr"))
        self.assertIn(r"news(?:\.[a-z]{2})?", (ROOT / "sw.js").read_text(encoding="utf-8"))

    def test_share_pages_go_to_main_behind_the_flag(self):
        # Sahibin qeydi (2026-11-04): paylaşılan keçiddə xəbər görünsün — og etiketli x/<id>.html səhifələri main-ə yalnız bayraqla gedir
        self.assertIn("export SHARE_PAGES=1", self.pipeline)
        self.assertIn('if [ -d "$WORK/x" ]; then rm -rf "$REPO_DIR/x"; cp -a "$WORK/x" "$REPO_DIR/x"; fi', self.pipeline)
        self.assertIn('if [ -d "$REPO_DIR/x" ]; then git -C "$REPO_DIR" add x', self.pipeline)
        self.assertIn('[ -d "$REPO_DIR/x" ] && cp -a "$REPO_DIR/x" "$WORK/x"', self.pipeline)
        self.assertIn("write_share_pages(articles)", (ROOT / "updater.py").read_text(encoding="utf-8"))

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

    def test_phone_and_money_transfers_are_not_sport(self):
        # 2026-11-14, sahib: «idmana telefon xəbəri düşür» — «ses transferi» futbol transferi sayılırdı.
        t = "WhatsApp ve Telegram sesli aramalarını kaydetme özelliği geliyor"
        d = ("Samsung, kat hücresel şebeke aramalarında sunduğu dâhili ses kaydı yeteneğini, üçüncü taraf mesajlaşma ve VoIP "
             "(IP üzerinden ses transferi) uygulamalarına genişletmeye hazırlanıyor.")
        self.assertEqual(updater.categorize(t, d, "tr"), "Texnologiya")
        self.assertEqual(updater.categorize(t, d, "tr", world=True), "Texnologiya")
        self.assertNotEqual(self.label("Bankdan pul transferi zamanı komissiya artırılır"), "İdman")
        self.assertNotEqual(updater.categorize("Havalimanı transferi ücretleri arttı", "", "tr"), "İdman")
        # Futbol transferi əvvəlki kimi idmandır
        self.assertEqual(updater.categorize("Galatasaray'ın yeni transferi İstanbul'a geldi", "", "tr"), "İdman")
        self.assertEqual(self.label("Neftçi qış transfer pəncərəsində iki futbolçu alacaq"), "İdman")
        self.assertEqual(self.label("Futbolçunun transferi baş tutmadı"), "İdman")

    def test_ascii_azerbaijani_title_is_not_english(self):
        self.assertEqual(updater.detect_lang("Tehrandan Avropaya", "", "az"), "az")
        self.assertEqual(updater.detect_lang("Zaqatalada qaz olmayacaq", "", "az"), "az")
        self.assertEqual(updater.detect_lang("Azerbaijan, Turkiye discuss solar energy deal", "", "az"), "en")
        # Türk hərfli ad ingilis xəbərini AZ lentə salmır
        self.assertEqual(updater.detect_lang("Erdoğan thanks Azerbaijan for sharing COP29 experience at Antalya climate summit", "Turkish President Recep Tayyip Erdoğan has expressed appreciation to Azerbaijan", "az"), "en")
        self.assertEqual(updater.detect_lang("Yeni Parti leader Özgür Özel makes phone call to President Ilham Aliyev", "Chairman of Türkiye's Yeni Parti Özgür Özel has called President of Azerbaijan Ilham Aliyev.", "az"), "en")
        self.assertEqual(updater.detect_lang("Azerbaijan advances green energy corridor talks with Bulgaria", "exports to Türkiye and Europe", "az"), "en")
        self.assertEqual(updater.detect_lang("Özgür Özel Bakıya gedir", "", "az"), "az")
        self.assertEqual(updater.detect_lang("Türkiye ilk yeri tutdu", "Yarış başa çatdı", "az"), "az")
        self.assertEqual(updater.detect_lang("Sincere dialogue between President Ilham Aliyev and Recep Tayyip Erdoğan", "", "az"), "en")
        self.assertEqual(updater.detect_lang("Fulya Öztürk Aygün Kazımovanın mahnısını paylaşdı", "", "az"), "az")

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

    def test_stored_groups_do_not_bring_broken_reyting_links_back(self):
        rows = [{"sourceUrl": "https://a.az/1"}]
        stored = {"https://a.az/1": [{"sourceUrl": "https://reyting.az/haber/x.html", "source": "Reyting.az"}]}
        with tempfile.TemporaryDirectory() as tmp, patch.object(updater, "GROUPS_FILE", pathlib.Path(tmp) / "qrup.json"):
            updater.GROUPS_FILE.write_text(updater.json.dumps(stored), encoding="utf-8")
            out = updater.apply_groups(rows)
        self.assertEqual(out[0]["alts"][0]["sourceUrl"], "https://reyting.az/xeber/x")

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
        self.patches = [patch.object(updater, "OUT_FILE", root / "news.json"), patch.object(updater, "ARCHIVE_DIR", root / "arxiv"), patch.object(updater, "SHARE_DIR", root / "paylas"), patch.object(updater, "ARCHIVE_OG_FILE", root / "aog.json"), patch.object(updater, "CACHE_DIR", root), patch.object(updater, "_fetch_og", return_value="")]
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

    def shared(self, url):
        sid = updater.hashlib.sha1(url.encode()).hexdigest()[:16]
        part = updater._read_json(updater.SHARE_DIR / f"{updater.share_part(sid)}.json", {}).get("articles") or []
        return next((r for r in part if r["id"] == sid), None)

    def test_share_index_moves_rows_from_the_old_32_part_files_into_256_parts(self):
        # 2026-11-09: 32 fayl (id >> 3) → 256 fayl (id-nin ilk iki hex rəqəmi). Köhnə fayldakı, lentdən çıxmış xəbər itmir: öz yeni hissəsinə düşür.
        now, url = updater.time.time(), "https://apa.az/1"
        sid = updater.hashlib.sha1(url.encode()).hexdigest()[:16]
        self.assertEqual((updater.SHARE_PARTS, updater.share_part(sid)), (256, int(sid[:2], 16)))
        updater.SHARE_DIR.mkdir(parents=True, exist_ok=True)
        old = {**self.row(url, 3, id=sid), "at": int(now - 7200)}
        (updater.SHARE_DIR / f"{int(sid[:2], 16) >> 3}.json").write_text(updater.json.dumps({"at": now - 7200, "articles": [old]}), encoding="utf-8")
        updater.update_share_index([], now)
        part = updater._read_json(updater.SHARE_DIR / f"{updater.share_part(sid)}.json", {})
        self.assertEqual(part.get("parts"), 256)
        self.assertEqual([r["sourceUrl"] for r in part["articles"]], [url])
        self.assertEqual(len(list(updater.SHARE_DIR.glob("*.json"))), 256)

    def test_shared_link_opens_for_a_day_after_the_story_leaves_the_feed(self):
        now, url, alt = updater.time.time(), "https://apa.az/1", "https://report.az/1"
        sid = lambda u: updater.hashlib.sha1(u.encode()).hexdigest()[:16]
        self.write(self.row(url, 1, id=sid(url), alts=[{"source": "Report", "sourceUrl": alt}]), self.row("https://azadliq.org/1", 1, id=sid("https://azadliq.org/1")))
        updater.update_archive(now=now)
        self.assertIsNone(self.shared("https://azadliq.org/1"))
        self.write(self.row("https://apa.az/2", 0, id=sid("https://apa.az/2")))
        for hours in (1.1, 24.5):
            updater.update_archive(now=now + hours * 3600)
            self.assertEqual(self.shared(url)["sourceUrl"], url)
            self.assertEqual(self.shared(alt)["of"], sid(url))  # qrupa düşən mənbənin keçidi əsas xəbərə yönəlir
        updater.update_archive(now=now + 26 * 3600)
        self.assertIsNone(self.shared(url))
        self.assertEqual(self.shared("https://apa.az/2")["sourceUrl"], "https://apa.az/2")

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

    def backlog_feed(self, *items):
        cache = updater.ARCHIVE_DIR.parent / "feeds.json"
        cache.write_text(updater.json.dumps({"DOST Agentliyi": {"items": list(items), "at": 5}}), encoding="utf-8")
        return patch.object(updater, "FEED_CACHE", cache), patch.object(updater, "SLOW_FEED_CACHE", updater.ARCHIVE_DIR.parent / "yoxdur.json")

    def feed_item(self, url, hours, title="DOST mərkəzində müraciətlər qəbul olunur"):
        at = updater.datetime.datetime.now(updater.datetime.timezone.utc) - updater.datetime.timedelta(hours=hours)
        return {"title": title, "link": url, "description": "", "pubDate": at.isoformat(), "image": None, "author": ""}

    def test_official_news_older_than_the_feed_reaches_its_section(self):
        self.write(self.row("https://apa.az/1", 1))
        first, second = self.backlog_feed(self.feed_item("https://dost.gov.az/news/1", 30), self.feed_item("https://dost.gov.az/news/2", 7 * 24))
        with first, second:
            updater.update_archive()
        self.assertEqual([a["sourceUrl"] for a in self.rows("sosial")], ["https://dost.gov.az/news/1"])
        self.assertEqual(self.rows("sosial")[0]["category"], "sosial")

    def test_backlog_stories_get_their_page_image_once(self):
        self.write(self.row("https://apa.az/1", 1))
        first, second = self.backlog_feed(self.feed_item("https://dost.gov.az/news/4", 3))
        with first, second, patch.object(updater, "_fetch_og", return_value="https://dost.gov.az/a.jpg") as look:
            updater.update_archive()
            self.assertEqual(self.rows("sosial")[0]["imageUrl"], "https://dost.gov.az/a.jpg")
            self.assertEqual(look.call_count, 1)
            updater.update_archive(now=updater.time.time() + 3700)
            self.assertEqual(look.call_count, 1, "bir dəfə tapılan yenidən sorğulanmır")
            self.assertEqual(self.rows("sosial")[0]["imageUrl"], "https://dost.gov.az/a.jpg")

    def test_wrongly_taken_featured_image_is_removed_from_the_archive(self):
        self.write(self.row("https://lent.az/xeber/1", 2, source="Lent.az", imageUrl="https://lent.az/storage/news/2026/october/31/middle/a.webp"))
        updater.update_archive()
        self.assertNotIn("imageUrl", self.rows()[0])

    def test_backlog_keeps_the_negative_leadership_filter(self):
        self.write(self.row("https://apa.az/1", 1))
        with patch.object(updater, "is_negative_about_leadership", return_value=True):
            first, second = self.backlog_feed(self.feed_item("https://dost.gov.az/news/3", 2))
            with first, second:
                updater.update_archive()
        self.assertEqual(self.rows("sosial"), [])

    def test_a_new_section_gets_its_archive_without_waiting_an_hour(self):
        now = updater.time.time()
        self.write(self.row("https://apa.az/1", 2))
        updater.update_archive(now=now)
        (updater.ARCHIVE_DIR / "sosial.json").unlink()
        self.write(self.row("https://apa.az/2", 1))
        updater.update_archive(now=now + 600)
        self.assertTrue((updater.ARCHIVE_DIR / "sosial.json").exists())
        self.assertEqual(len(self.rows()), 2)

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


class SafeUrlTest(unittest.TestCase):
    def test_public_links_pass(self):
        for url in ("https://oxu24.com/a?b=1", "http://sayt.az/xəbər başlığı", " https://sayt.az/a\n", "https://8.8.8.8/a"):
            self.assertTrue(content_policy.safe_url(url), url)

    def test_internal_and_confusing_links_fail(self):
        for url in ("http://169.254.169.254/latest", "http://127.0.0.1/", "http://127.1/", "http://0x7f.1/", "http://2130706433/",
                    "http://[::1]/", "http://10.0.0.1/", "http://localhost:8080/", "http://printer.local/", "file:///etc/passwd",
                    "javascript://sayt.az/%0aalert(1)", "https://evil.com\\@report.az/", "https://report.az@evil.com/",
                    "https://report.az/a\tb", "", None):
            self.assertFalse(content_policy.safe_url(url), url)

    def test_policy_refuses_a_link_browsers_read_differently(self):
        name, domains = next(iter(content_policy.AZ_SOURCES.items()))
        self.assertTrue(content_policy.source_allowed(name, f"https://{domains[0]}/a"))
        self.assertFalse(content_policy.source_allowed(name, f"https://evil.com\\@{domains[0]}/a"))


if __name__ == "__main__":
    unittest.main()
