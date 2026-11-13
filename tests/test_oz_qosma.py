"""Öz xəbərlərin sayta qoşulması (sahib 2026-11-12: «Sayta qoşmağa başla», sonra «Bəli, yandır»).
Açar OZ_DERC=1 mühit dəyişənidir; onu yalnız pipeline.sh qoyur (tests/test_oz_xeber.py::WiredSwitchedOnTest). Buradakı testlər açarı özləri qoyub götürür.
Şəbəkə yoxdur: lentlər və dərc modulu saxtadır."""
import contextlib
import datetime
import email.utils
import io
import json
import os
import pathlib
import re
import subprocess
import sys
import tempfile
import time
import unittest
from types import SimpleNamespace
from unittest.mock import patch

import content_policy
import updater

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / ".github" / "scripts"))
from check_outputs import bad_outputs, enforce_policy  # noqa: E402

OWN = "8ULDUZ"
ON = {"OZ_DERC": "1", "NEWS_LANG_FILES": "1"}
FEED_FILES = ("news.json", "latest.json", "latest.az.json", "first.json")
SLOW_STEPS = ["compute_groups", "update_markets", "resolve_undated", "update_social", "update_video", "update_football", "update_sports",
              "retire_reader", "refresh_slow_feeds", "write_public", "update_archive", "update_team_pages"]


def iso(minutes_ago):
    return (datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(minutes=minutes_ago)).isoformat(timespec="seconds")


def own_row(n, minutes_ago, category="idman", title=None, **extra):
    """oz_derc.row-un verdiyi formada sətir (updater.make_article-in açarları)."""
    ident = f"{n:016x}"
    return {"id": ident, "title": title or f"Öz xəbər {n}", "summary": f"{n} nömrəli öz xəbərin girişi.", "category": category,
            "source": OWN, "sourceUrl": f"https://8ulduz.az/xeber/{ident}/", "publishedAt": iso(minutes_ago), "imageUrl": None,
            "lang": "az", "author": "", "video": False, **extra}


def plain_row(source, url, title, minutes_ago, **extra):
    return {"id": url, "title": title, "summary": "", "category": "gundem", "source": source, "sourceUrl": url,
            "publishedAt": iso(minutes_ago), "lang": "az", **extra}


@contextlib.contextmanager
def env(**values):
    """Təmiz mühit: açar və lent bayraqları yoxdur, yalnız verilənlər var."""
    with patch.dict(os.environ):
        for key in ("OZ_DERC", "NEWS_LANG_FILES", "LATEST_LANG_FILES", "SHARE_PAGES", "SOCIAL_LOOP"):
            os.environ.pop(key, None)
        os.environ.update(values)
        yield


@contextlib.contextmanager
def quiet():
    out = io.StringIO()
    with contextlib.redirect_stdout(out):
        yield out


class Sandbox(unittest.TestCase):
    """tests/test_red_lines.py::FastCycleTest kimi: updater müvəqqəti qovluğa yazır."""

    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        root = self.root = pathlib.Path(tmp.name)
        (root / "data").mkdir()
        data, cache = root / "data", root / ".cache"
        names = {"OUT_DIR": data, "OUT_FILE": data / "news.json", "STATUS_FILE": data / "status.json", "SOURCES_FILE": data / "sources.json",
                 "OG_FILE": data / "og.json", "DATES_FILE": data / "dates.json", "LATEST_FILE": data / "latest.json", "FIRST_FILE": data / "first.json",
                 "OWN_ROWS_FILE": cache / "oz-yayimda.json", "CACHE_DIR": cache, "LINK_HEALTH_FILE": cache / "link_health.json",
                 "FEED_CACHE": cache / "feeds.json", "SLOW_FEED_CACHE": cache / "slow.json", "OFFICIAL_CACHE": cache / "official.json",
                 "UNDATED_FILE": cache / "undated.json", "RECENT_FILE": cache / "recent.json", "GNEWS_CACHE": cache / "gnews.json",
                 "GROUPS_FILE": cache / "groups.json", "RELABEL_MARK": cache / "relabeled", "STORY_DIR": root / "xeber",
                 "NEWS_SITEMAP_FILE": root / "sitemap-news.xml", "SHARE_PAGES_DIR": root / "x"}
        for key, value in names.items():
            item = patch.object(updater, key, value)
            item.start()
            self.addCleanup(item.stop)

    def item(self, link, title, minutes_ago=120):
        pub = email.utils.format_datetime(datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(minutes=minutes_ago))
        return {"title": title, "link": link, "description": "", "pubDate": pub, "author": "", "image": None}

    def items(self):
        return {"APA": [self.item("https://apa.az/a-1", "Avropada güclü fırtına başladı", 30), self.item("https://apa.az/a-2", "Bakıda yeni məktəb açıldı", 90)],
                "BBC News": [self.item("https://www.bbc.com/news/x-1", "Storm hits northern Europe", 60)]}

    def cycle(self, items):
        feeds = [("APA", "https://apa.az/rss", "az", None), ("BBC News", "https://feeds.bbci.co.uk/x", "en", None), ("Report", "https://report.az/rss", "az", None)]

        def fetcher(feed, old=None):
            return {"items": [dict(i) for i in items.get(feed[0], [])], "url": feed[1], "at": time.time(), "err": None}

        with patch.object(updater, "FEEDS", feeds), patch.object(updater, "fetch_feed_fast", fetcher), \
                patch.object(updater, "official_items", lambda: ([], [])), patch.object(updater, "FAST_BUDGET_S", 0.3), quiet() as out:
            code = updater.run_fast()
        return code, out.getvalue()

    def doc(self, name):
        return json.loads((self.root / "data" / name).read_text(encoding="utf-8"))

    def own_in(self, name):
        return [a for a in self.doc(name)["articles"] if a.get("source") == OWN]

    def write_rows(self, rows):
        """Main-ə çatmış sətirlərin nüsxəsi (pipeline.sh own_rows_live): lent yalnız bunu oxuyur."""
        self.write_raw(json.dumps({"v": 1, "articles": rows}, ensure_ascii=False))

    def write_raw(self, text):
        updater.OWN_ROWS_FILE.parent.mkdir(parents=True, exist_ok=True)
        updater.OWN_ROWS_FILE.write_text(text, encoding="utf-8")

    def write_derc(self, text):
        """Dərc dövrəsinin öz faylı (data/oz/xeberler.json): main-ə çatana qədər lent onu oxumur."""
        path = self.root / "data" / "oz" / "xeberler.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")


class SwitchOffFeedTest(Sandbox):
    """Açar yoxdursa sətir faylı olsa da oxunmur: lent faylın olmadığı haldakı ilə eynidir."""

    def test_rows_file_is_not_even_opened(self):
        self.write_rows([own_row(1, 5)])
        for value in (None, "", "0", "true", " 1", "11"):
            with env(**({} if value is None else {"OZ_DERC": value})), patch.object(updater, "_read_json", side_effect=AssertionError("fayl oxunmamalıdır")):
                self.assertEqual(updater.read_own_rows(), [], repr(value))

    def test_feed_is_the_same_with_and_without_a_rows_file(self):
        with env():
            self.assertEqual(self.cycle(self.items())[0], 0)
            before = {name: self.doc(name)["articles"] for name in FEED_FILES}
            self.assertTrue(before["news.json"])
            self.write_rows([own_row(1, 5), own_row(2, 20)])
            saved = updater.OWN_ROWS_FILE.read_bytes()
            for value in (None, "0", "true"):
                with env(**({} if value is None else {"OZ_DERC": value})):
                    self.assertEqual(self.cycle({**self.items(), "Report": [self.item("https://report.az/r-9", "Gəncədə yeni park salındı", 10)]})[0], 0)
                for name in FEED_FILES:
                    self.assertEqual(self.own_in(name), [], f"{name} {value!r}")
            self.assertEqual(updater.OWN_ROWS_FILE.read_bytes(), saved, "sürətli dövrə sətir faylına yazmır")
            # Eyni lentlə təkrar dövrə: əvvəlki lentdəki sətirlər də olduğu kimi qalır (öz sətir süzgəci başqa mənbəyə toxunmur).
            kept = [a for a in self.doc("news.json")["articles"] if a["sourceUrl"] != "https://report.az/r-9"]
            self.assertEqual(kept, before["news.json"])

    def test_switching_off_takes_own_rows_out_of_the_next_feed(self):
        self.write_rows([own_row(1, 5)])
        with env(**ON):
            self.cycle(self.items())
            self.assertEqual(len(self.own_in("news.json")), 1)
        with env(NEWS_LANG_FILES="1"):
            self.cycle({**self.items(), "Report": [self.item("https://report.az/r-9", "Gəncədə yeni park salındı", 10)]})
            for name in FEED_FILES:
                self.assertEqual(self.own_in(name), [], name)


class SwitchOnFeedTest(Sandbox):
    """Mərhələ 3-dən sonrakı hal (açar var): öz sətirlər yazılan lentə dəyişmədən çatır və qapıdan keçir."""

    SAME = "«Qarabağ» «Neftçi»ni 2:0 hesabı ilə məğlub edib"

    def check_everywhere(self, rows):
        by_date = sorted(rows, key=lambda r: r["publishedAt"], reverse=True)
        news = self.doc("news.json")["articles"]
        self.assertEqual(self.own_in("news.json"), by_date, "sətir olduğu kimi: id, başlıq, bölmə, keçid, vaxt")
        self.assertEqual([a["publishedAt"] for a in news], sorted((a["publishedAt"] for a in news), reverse=True), "lent tarix sırasındadır")
        for name in ("latest.json", "latest.az.json", "first.json"):
            self.assertEqual(self.own_in(name), by_date, name)
        for name in ("news.en.json", "news.ru.json", "news.tr.json", "latest.en.json", "latest.ru.json", "latest.tr.json"):
            self.assertEqual(self.own_in(name), [], f"{name}: öz xəbər azərbaycancadır")
        for name in ("news.json", "latest.json", "first.json"):
            for a in self.doc(name)["articles"]:
                self.assertNotIn(OWN, [x.get("source") for x in a.get("alts") or []], "öz xəbər başqa kartın alt mənbəsi olmur")
                if a.get("source") == OWN:
                    self.assertNotIn("alts", a, "başqa mənbə öz xəbərə bağlanmır")
        self.assertEqual(content_policy.enforce(rows), (rows, {}), "öz sətirlər qapıdan keçir")

    def test_own_pages_are_in_the_news_sitemap_only_when_switched_on(self):
        """Sahib, 2026-11-13: «Bəli, əlavə et». Lentdəki öz xəbərin səhifəsi saytdadır, Google News xəritəsinə də yazılır."""
        rows = [own_row(1, 5), own_row(2, 20)]
        self.write_rows(rows)
        with env(**ON):
            self.assertEqual(self.cycle(self.items())[0], 0)
            xml = (self.root / "sitemap-news.xml").read_text(encoding="utf-8")
            for r in rows:
                self.assertEqual(xml.count(f"<loc>{r['sourceUrl']}</loc>"), 1, r["id"])
            self.assertIn("<news:title>Öz xəbər 1</news:title>", xml)
        with env():
            self.assertEqual(self.cycle(self.items())[0], 0)
            self.assertNotIn("/xeber/000000000000000", (self.root / "sitemap-news.xml").read_text(encoding="utf-8"), "açarsız öz səhifə yazılmır")

    def test_own_rows_reach_every_written_file_unchanged(self):
        # 1: lentdəki xəbərlə eyni başlıq, bölməsi başlığın «təbii» bölməsindən fərqli; 3: 30 saat əvvəlki sətir.
        rows = [own_row(1, 5, "tehsil", self.SAME), own_row(2, 45, "iqtisadiyyat"), own_row(3, 30 * 60, "cemiyyet")]
        self.write_rows(rows)
        items = {**self.items(), "Report": [self.item("https://report.az/r-1", self.SAME, 4)]}
        with env(**ON):
            code, _ = self.cycle(items)
            self.assertEqual(code, 0)
            self.check_everywhere(rows)
            self.assertEqual(self.doc("status.json")["stats"]["policyDropped"], {})
            # İkinci dövrə işin ilk dövrəsi kimi (köhnə sətirlər yenidən təsnif edilir), lentə yeni xəbər də gəlir.
            updater.RELABEL_MARK.unlink()
            items["APA"] = items["APA"] + [self.item("https://apa.az/a-3", "Gəncədə yeni park salındı", 1)]
            self.assertEqual(self.cycle(items)[0], 0)
            self.check_everywhere(rows)
            self.assertIn("https://apa.az/a-3", [a["sourceUrl"] for a in self.doc("news.json")["articles"]])
            # Dərc dövrəsi sətri fayldan çıxaranda (48 saat) lentdən də çıxır: sətir yalnız fayldan gəlir.
            self.write_rows(rows[:2])
            self.assertEqual(self.cycle(items)[0], 0)
            self.check_everywhere(rows[:2])

    def test_a_real_publisher_row_passes_the_reader_and_the_gate(self):
        import oz_derc
        when = datetime.datetime.now(oz_derc.BAKU) - datetime.timedelta(minutes=3)
        row = oz_derc.row({"key": "sinaq-qosma-1", "kind": "sinaq", "topic": "idman", "title": "Sınaq başlığı", "lead": "Sınaq xəbərinin girişi."}, when)
        self.assertEqual((row["source"], row["sourceUrl"]), (OWN, f"https://8ulduz.az/xeber/{row['id']}/"))
        self.assertIsNone(content_policy.violation(row))
        self.write_rows([row])
        with env(**ON):
            self.assertEqual(updater.read_own_rows(), [row])
            self.assertEqual(self.cycle(self.items())[0], 0)
            self.assertEqual(self.own_in("news.json"), [row])

    def test_without_the_source_on_the_allowlist_every_own_row_is_dropped(self):
        self.write_rows([own_row(1, 5), own_row(2, 45)])
        with env(**ON), patch.dict(content_policy.AZ_SOURCES):
            del content_policy.AZ_SOURCES[OWN]
            self.assertEqual(self.cycle(self.items())[0], 0)
            for name in FEED_FILES:
                self.assertEqual(self.own_in(name), [], name)
            self.assertEqual(self.doc("status.json")["stats"]["policyDropped"], {"icazəli siyahıda deyil": 2})
            self.assertEqual(len(self.doc("news.json")["articles"]), 2, "başqa xəbərlər yerindədir")
        self.assertIn(OWN, content_policy.AZ_SOURCES)

    def test_broken_or_foreign_rows_never_reach_the_feed(self):
        good = own_row(1, 5)
        with env(**ON):
            for text in ("{", "[]", "null", json.dumps({"articles": "x"}), json.dumps({"v": 1})):
                self.write_raw(text)
                self.assertEqual(updater.read_own_rows(), [], text)
            updater.OWN_ROWS_FILE.unlink()
            self.assertEqual(updater.read_own_rows(), [], "fayl yoxdur")
            self.write_rows([None, 5, {"source": OWN}, {**own_row(2, 5), "publishedAt": "dünən"}, {**own_row(3, 5), "id": 7},
                             own_row(4, 6 * 24 * 60), {**own_row(5, 5), "source": "APA", "sourceUrl": "https://apa.az/x-5"}, good, dict(good)])
            self.assertEqual(updater.read_own_rows(), [good], "yalnız forması düz, təzə, mənbəyi «8ULDUZ» olan sətir; təkrar bir dəfə")
            # Adı «8ULDUZ», keçidi başqa sayt: oxunur, amma qapı rədd edir.
            self.write_rows([{**own_row(6, 5), "sourceUrl": "https://evil.example/xeber/6/"}, good])
            self.assertEqual(self.cycle(self.items())[0], 0)
            self.assertEqual(self.own_in("news.json"), [good])
            self.assertEqual(self.doc("status.json")["stats"]["policyDropped"], {"icazəli siyahıda deyil": 1})
            # Zədəli fayl dövrəni dayandırmır.
            self.write_raw("{")
            self.assertEqual(self.cycle({**self.items(), "Report": [self.item("https://report.az/r-9", "Gəncədə yeni park salındı", 10)]})[0], 0)
            self.assertEqual(self.own_in("news.json"), [])
            self.assertEqual(len(self.doc("news.json")["articles"]), 3, "lent yazılıb: iki əvvəlki və bir yeni xəbər")

    def test_merge_puts_rows_by_date_and_returns_the_same_list_when_empty(self):
        feed = [plain_row("APA", "https://apa.az/1", "Bir", 10), plain_row("APA", "https://apa.az/2", "İki", 30)]
        self.assertIs(updater.merge_own_rows(feed, []), feed)
        newest, middle, oldest = own_row(1, 1), own_row(2, 20), own_row(3, 300)
        out = updater.merge_own_rows(feed, [oldest, newest, middle])
        self.assertEqual([a["sourceUrl"] for a in out], [newest["sourceUrl"], "https://apa.az/1", middle["sourceUrl"], "https://apa.az/2", oldest["sourceUrl"]])
        self.assertEqual(len(feed), 2, "verilən siyahı dəyişmir")
        self.assertEqual(updater.merge_own_rows([], [oldest, newest]), [newest, oldest])


class OwnRowsElsewhereTest(Sandbox):
    """Lentdən oxuyan yerlər: qruplaşma, link yoxlaması, xəbər səhifələri, dərcdən əvvəlki qapı."""

    def test_grouping_passes_own_rows_through(self):
        title = "Bakıda beynəlxalq forum işə başlayıb"
        rows = [plain_row("APA", "https://apa.az/f-1", title, 10), plain_row("Report", "https://report.az/f-1", title, 12), own_row(1, 11, "gundem", title)]
        alone = updater.group_duplicates([dict(r) for r in rows[:2]])
        self.assertEqual(len(alone), 1, "eyni başlıqlı iki mənbə bir kartdır")
        out = updater.group_duplicates([dict(r) for r in rows])
        self.assertEqual([a for a in out if a["source"] == OWN], [rows[2]], "öz sətir olduğu kimi, ayrıca")
        self.assertEqual([a for a in out if a["source"] != OWN], alone, "qalanların qruplaşması öz sətirsiz olduğu kimidir")

    def test_link_checker_never_asks_for_an_own_page(self):
        asked = []
        feed = [own_row(1, 5), plain_row("APA", "https://apa.az/a-1", "Bir", 5)]
        with patch.object(updater, "read_feed", lambda *a, **k: feed), patch.object(updater, "link_status", lambda url: asked.append(url) or "dead"), quiet():
            updater.check_links()
        self.assertEqual(asked, ["https://apa.az/a-1"])
        self.assertEqual(list(json.loads(updater.LINK_HEALTH_FILE.read_text(encoding="utf-8"))), ["https://apa.az/a-1"])

    def test_image_lookup_never_asks_for_an_own_page(self):
        asked = []
        feed = [own_row(1, 5), plain_row("APA", "https://apa.az/a-1", "Bir", 5)]
        with patch.object(updater, "_fetch_og", lambda url, logos=None: asked.append(url)), quiet():
            updater.fill_og_images(feed)
        self.assertEqual(asked, ["https://apa.az/a-1"], "öz səhifənin og:image-i saytın ümumi lövhəsidir: soruşulmur")
        self.assertIsNone(feed[0]["imageUrl"])

    def test_story_pages_leave_an_existing_own_page_untouched(self):
        def alts(sid):
            return [{"source": name, "sourceUrl": f"https://{host}/x/{sid}", "title": "Başlıq", "lang": "az"} for name, host in (("Report", "report.az"), ("Trend", "trend.az"))]
        own = {**own_row(1, 30), "alts": alts("oz")}
        other = {**plain_row("APA", "https://apa.az/news/1", "Zəfər Günü ilə bağlı hərbi yürüşlər olacaq", 20), "id": "f" * 16, "summary": "Xülasə.", "alts": alts("b")}
        self.assertTrue(updater.story_worthy(own), "3 mənbəli öz sətir ümumi qaydaya görə səhifəyə layiq olardı")
        page = self.root / "xeber" / own["id"] / "index.html"
        page.parent.mkdir(parents=True)
        page.write_text("ÖZ SƏHİFƏ", encoding="utf-8")
        with patch.object(updater, "story_image_widths", lambda rows, limit=80: {}), quiet():
            index = updater.write_story_pages([own, other])
            self.assertEqual(sorted(index), [other["id"]], "ümumi şablon yalnız başqa xəbərə səhifə yazır")
            self.assertIn("Zəfər Günü", (self.root / "xeber" / other["id"] / "index.html").read_text(encoding="utf-8"))
            self.assertEqual(page.read_text(encoding="utf-8"), "ÖZ SƏHİFƏ", "öz səhifənin üstünə yazılmır")
            again = updater.write_story_pages([own, other], now=time.time() + 31 * 86400)
        self.assertEqual(again, {}, "30 gündən sonra ümumi səhifə silinir")
        self.assertFalse((self.root / "xeber" / other["id"]).exists())
        self.assertEqual(page.read_text(encoding="utf-8"), "ÖZ SƏHİFƏ", "öz səhifə köhnə ümumi səhifələrlə birgə silinmir (onu dərc dövrəsi özü silir)")

    def test_publish_gate_passes_own_rows_and_still_rejects_the_rest(self):
        own = own_row(1, 5)
        apa = plain_row("APA", "https://apa.az/1", "Başlıq", 5)
        rows = [apa, own, {**own_row(2, 5), "sourceUrl": "https://evil.example/xeber/2/"}, {**own_row(3, 5), "sourceUrl": "https://meydan.tv/x"},
                plain_row("Yeni Sayt", "https://yenisayt.az/1", "Başlıq", 5), plain_row("TASS", "https://tass.ru/1", "Алиев принял", 5)]
        names = ("news.json", "latest.json", "first.json", "latest.az.json", "news.ru.json")
        for name in names:
            (self.root / "data" / name).write_text(json.dumps({"articles": rows, "count": len(rows)}, ensure_ascii=False), encoding="utf-8")
        self.write_derc(json.dumps({"v": 1, "articles": [own]}, ensure_ascii=False))
        (self.root / "data" / "oz" / "derc.json").write_text(json.dumps({"v": 1}), encoding="utf-8")
        self.assertEqual(bad_outputs(self.root), [])
        removed = enforce_policy(self.root)
        self.assertEqual(sorted(removed), sorted(names))
        for name in names:
            self.assertEqual(self.doc(name)["articles"], [apa, own], name)
            self.assertEqual(self.doc(name)["count"], 2)
        self.assertEqual(self.doc("oz/xeberler.json")["articles"], [own], "qapı sətir faylına toxunmur")
        self.assertEqual(enforce_policy(self.root), {}, "təmiz lentdə dəyişiklik yoxdur")
        self.write_derc("{")
        self.assertEqual(bad_outputs(self.root), ["data/oz/xeberler.json"], "zədəli sətir faylı da tutulur: pipeline son sağlam nüsxəni qaytarır")


class PublishedCopyTest(Sandbox):
    """Sətir lentə yalnız səhifəsi saytda olandan sonra düşür (2026-11-12): kart birbaşa xəbərin səhifəsinə aparır, səhifə isə
    sayta main yazılışı ilə çatır. Sürətli dövrə dərc dövrəsinin faylını yox, onun main-ə çatmış nüsxəsini oxuyur."""

    def test_a_row_that_is_not_on_main_yet_stays_out_of_the_feed(self):
        first, second = own_row(1, 30), own_row(2, 3)
        with env(**ON):
            self.write_derc(json.dumps({"v": 1, "articles": [second, first]}, ensure_ascii=False))
            self.assertEqual(self.cycle(self.items())[0], 0)
            for name in FEED_FILES:
                self.assertEqual(self.own_in(name), [], f"{name}: dərc dövrəsi yazıb, amma səhifələr hələ saytda deyil")
            self.write_rows([first])   # main-ə birinci çatıb
            self.assertEqual(self.cycle(self.items())[0], 0)
            for name in FEED_FILES:
                self.assertEqual(self.own_in(name), [first], name)
            self.write_rows([second, first])
            self.assertEqual(self.cycle(self.items())[0], 0)
            for name in FEED_FILES:
                self.assertEqual(self.own_in(name), [second, first], name)
            self.assertEqual(json.loads((self.root / "data" / "oz" / "xeberler.json").read_text(encoding="utf-8"))["articles"], [second, first],
                             "sürətli dövrə dərc dövrəsinin faylına toxunmur")


class PipelineCopyTest(unittest.TestCase):
    """pipeline.sh own_rows_live: main-ə yazılmış sətir faylının nüsxəsi. Başlanğıcda dərhal, main yazılışından sonra Pages yayımını gözləyib."""

    SH = (ROOT / ".github" / "scripts" / "pipeline.sh").read_text(encoding="utf-8")

    def test_reader_points_at_the_copy_not_at_the_publishers_file(self):
        import oz_derc
        self.assertEqual(updater.OWN_ROWS_FILE, updater.CACHE_DIR / "oz-yayimda.json")
        self.assertEqual(oz_derc.ROWS, ("data", "oz", "xeberler.json"))
        self.assertIn('src="$REPO_DIR/data/oz/xeberler.json" dst="$WORK/.cache/oz-yayimda.json"', self.SH)

    def test_copy_is_made_only_after_a_successful_push_and_at_start(self):
        body = self.SH[self.SH.index("\npublish_main() {"):]
        body = body[:body.index("\n}\n")]
        push = body.index('push -q origin "HEAD:$BRANCH"')
        self.assertEqual(body.count("own_rows_live"), 1)
        self.assertLess(push, body.index("own_rows_live 90"), "nüsxə yalnız main-ə yazılandan sonra")
        self.assertLess(body.index("own_rows_live 90"), body.index("return 0", push), "uğurlu yazılışın qolunda")
        self.assertLess(self.SH.index("\nown_rows_live 0"), self.SH.index("\nslow_loop &"), "başlanğıc nüsxəsi yavaş dövrədən əvvəl")

    def test_function_copies_at_once_or_after_the_wait(self):
        found = re.search(r"^own_rows_live\(\) \{\n.*?^\}\n", self.SH, re.M | re.S)
        self.assertTrue(found, "funksiya tapılmadı")
        script = found.group(0) + r'''
set -u
src="$REPO_DIR/data/oz/xeberler.json"; dst="$WORK/.cache/oz-yayimda.json"
own_rows_live 0; own_rows_live 90
[ ! -e "$WORK/.cache" ] || { echo "sətir faylı yoxdursa heç nə yaranmır"; exit 1; }
mkdir -p "$REPO_DIR/data/oz"; printf A > "$src"
own_rows_live 0
[ "$(cat "$dst")" = A ] || { echo "başlanğıcda nüsxə dərhal görünür"; exit 1; }
printf B > "$src"
own_rows_live 2
[ "$(cat "$dst")" = A ] || { echo "yayım gözlənilməmiş təzə nüsxə görünmür"; exit 1; }
printf C > "$src"
wait
[ "$(cat "$dst")" = B ] || { echo "gözləmədən sonra main-ə yazılmış nüsxə görünür (sonrakı dəyişiklik yox)"; exit 1; }
[ ! -e "$dst.yeni" ] || { echo "müvəqqəti fayl qalmır"; exit 1; }
'''
        with tempfile.TemporaryDirectory() as tmp:
            repo, work = pathlib.Path(tmp, "repo"), pathlib.Path(tmp, "work")
            repo.mkdir()
            work.mkdir()
            run = subprocess.run(["bash", "-c", script], env={**os.environ, "REPO_DIR": str(repo), "WORK": str(work)},
                                 capture_output=True, text=True, timeout=30)
        self.assertEqual((run.returncode, run.stdout.strip()), (0, ""), run.stderr)


class SlowStepTest(unittest.TestCase):
    """Yavaş addım (updater.update_own_news): açarsız heç nə, açarla bir dərc dövrəsi; xətası digər addımları saxlamır."""

    def slow_cycle(self):
        calls = []
        fakes = {n: (lambda n=n: calls.append(n)) for n in SLOW_STEPS}
        with patch.multiple(updater, read_feed=lambda *a, **k: [], fill_og_images=lambda *a, **k: None, drop_dead_images=lambda a: a, **fakes), quiet() as out:
            code = updater.slow_cycle()
        return code, calls, out.getvalue()

    def test_without_the_flag_nothing_is_imported_and_nothing_is_written(self):
        with tempfile.TemporaryDirectory() as tmp, patch.object(updater, "ROOT", pathlib.Path(tmp)), patch.dict(sys.modules), env():
            for name in [n for n in sys.modules if n.startswith("oz_")]:
                del sys.modules[name]
            sys.modules["oz_derc"] = None  # import cəhdi olsa ImportError verər
            for value in (None, "", "0", "true", "on", " 1", "11"):
                os.environ.pop("OZ_DERC", None)
                if value is not None:
                    os.environ["OZ_DERC"] = value
                self.assertIsNone(updater.update_own_news(), repr(value))
            del sys.modules["oz_derc"]
            os.environ.pop("OZ_DERC", None)
            with patch.object(updater, "update_own_news", wraps=updater.update_own_news) as step:
                code, calls, out = self.slow_cycle()
            step.assert_called_once_with()
            self.assertEqual(code, 0)
            self.assertEqual(calls[:3], ["compute_groups", "update_markets", "resolve_undated"], "addım məzənnədən sonradır, digərlərinin sırası dəyişməyib")
            self.assertEqual(calls[-1], "update_team_pages")
            self.assertNotIn("!", out, "xəta yoxdur")
            self.assertEqual([n for n in sys.modules if n.startswith("oz_")], [], "dərc modulu və xəbər modulları yüklənməyib")
            self.assertEqual(list(pathlib.Path(tmp).iterdir()), [], "heç bir fayl yazılmayıb")

    def test_with_the_flag_one_cycle_runs_on_the_root(self):
        calls = []
        result = {"enabled": True, "published": [{}], "queued": 3, "held": [], "blocked": [{}], "errors": []}
        fake = SimpleNamespace(cycle=lambda root: calls.append(root) or result)
        with tempfile.TemporaryDirectory() as tmp, patch.object(updater, "ROOT", pathlib.Path(tmp)), patch.dict(sys.modules, {"oz_derc": fake}), env(OZ_DERC="1"), quiet() as out:
            self.assertIs(updater.update_own_news(), result)
            self.assertEqual(calls, [pathlib.Path(tmp)])
        self.assertEqual(out.getvalue().strip(), "Öz xəbərlər: dərc 1, növbədə 3, saxlanılan 0, rədd 1, xəta 0")

    def test_the_real_module_is_importable_from_the_step(self):
        import oz_derc
        seen = []
        with tempfile.TemporaryDirectory() as tmp, patch.object(updater, "ROOT", pathlib.Path(tmp)), env(OZ_DERC="1"), quiet(), \
                patch.object(oz_derc, "cycle", lambda root: seen.append(root) or {"published": [], "queued": 0, "held": [], "blocked": [], "errors": []}):
            self.assertEqual(updater.update_own_news()["queued"], 0)
            self.assertEqual(seen, [pathlib.Path(tmp)])

    def test_a_failing_or_missing_publisher_does_not_stop_the_other_steps(self):
        def boom(root):
            raise RuntimeError("sınıq")
        for module in (SimpleNamespace(cycle=boom), None):  # None: kod qovluğunda fayl yoxdur (köhnə son işlək nüsxə)
            with patch.dict(sys.modules, {"oz_derc": module}), env(OZ_DERC="1"):
                code, calls, out = self.slow_cycle()
            self.assertEqual(code, 0)
            self.assertEqual(calls[-1], "update_team_pages", "sonrakı addımlar işləyir")
            self.assertIn("resolve_undated", calls)
            self.assertIn("! yavaş addım: update_own_news", out)


class PolicyTest(unittest.TestCase):
    def test_own_source_is_registered_only_for_its_own_site(self):
        self.assertEqual(content_policy.AZ_SOURCES.get(OWN), ["8ulduz.az"])
        self.assertNotIn(OWN, content_policy.WORLD_SOURCES)
        self.assertNotIn(OWN, content_policy.SPORT_SOURCES)
        self.assertTrue(content_policy.source_allowed(OWN, "https://8ulduz.az/xeber/0123456789abcdef/"))
        for url in ("https://evil.example/xeber/0123456789abcdef/", "https://8ulduz.az.evil.example/x", "https://evil.example\\@8ulduz.az/x",
                    "javascript://8ulduz.az/%0aalert(1)", "http://127.0.0.1/xeber/1/", ""):
            self.assertFalse(content_policy.source_allowed(OWN, url), url)
        self.assertNotIn(OWN, {f[0] for f in updater.FEEDS}, "öz xəbər lent deyil: yalnız dərc faylından gəlir")
        import oz_xeber
        self.assertEqual((updater.OWN_SOURCE, oz_xeber.SOURCE), (OWN, OWN))
        self.assertIn('"8ULDUZ": ["8ulduz.az"]', (ROOT / "assets" / "content-policy.js").read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
