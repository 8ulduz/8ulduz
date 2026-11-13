"""2026-11-13 kod yoxlamasında tapılan updater.py xətaları: hər test düzəlişdən əvvəl düşürdü."""
import contextlib
import datetime
import hashlib
import io
import json
import pathlib
import tempfile
import time
import unittest
import xml.etree.ElementTree as ET
from unittest.mock import patch

import content_policy
import updater


def iso(minutes_ago=0):
    return (datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(minutes=minutes_ago)).isoformat(timespec="seconds")


class TempFiles(unittest.TestCase):
    """Fayl yolları müvəqqəti qovluğa yönəlir: test repoya heç nə yazmır."""
    NAMES = {"OUT_DIR": "data", "SOURCES_FILE": "data/sources.json", "VIDEO_FILE": "data/video.json", "SOCIAL_FILE": "data/social.json",
             "SOCIAL_ARCHIVE_FILE": "data/social-arxiv.json", "FEED_FILE": "feed.xml", "NEWS_SITEMAP_FILE": "sitemap-news.xml",
             "STORY_DIR": "xeber", "SECTIONS_DIR": "bolme"}

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = pathlib.Path(self.tmp.name)
        (self.root / "data").mkdir()
        self.patches = [patch.object(updater, "ROOT", self.root)]
        self.patches += [patch.object(updater, name, self.root / rel) for name, rel in self.NAMES.items() if hasattr(updater, name)]
        for p in self.patches:
            p.start()
        self.quiet = contextlib.redirect_stdout(io.StringIO())
        self.quiet.__enter__()

    def tearDown(self):
        self.quiet.__exit__(None, None, None)
        for p in reversed(self.patches):
            p.stop()
        self.tmp.cleanup()

    def read(self, name):
        return json.loads((self.root / "data" / name).read_text(encoding="utf-8"))


class TextRulesTest(unittest.TestCase):
    def test_story_key_ignores_date_codes_and_reads_the_real_number(self):
        today = datetime.datetime.now(updater.BAKU)
        for code in (today.strftime("%d%m%y"), today.strftime("%d%m%Y"), f"{today.day}{today:%m%y}", (today - datetime.timedelta(days=40)).strftime("%d%m%y")):
            if len(code) >= 5:
                self.assertIsNone(updater.story_key(f"https://www.aljazeera.com/video/2026/11/12/some-story-{code}"), code)
        self.assertEqual(updater.story_key("https://qafqazinfo.az/news/detail/nazir-528168"), "qafqazinfo.az#528168")
        self.assertEqual(updater.story_key("https://metbuat.az/news/1566209/kohne-basliq.html"), "metbuat.az#1566209")
        self.assertEqual(updater.story_key("https://timesofindia.indiatimes.com/x-pay-sellers-35000/articleshow/125123456.cms"), "timesofindia.indiatimes.com#125123456")
        # çıxarılma açarı (content_policy.removal_key) dəyişməyib: sahibin siyahısı ondan asılıdır
        self.assertEqual(content_policy.removal_key("https://nocomment.az/x-555222"), "nocomment.az#555222")

    def test_unreadable_feed_date_is_not_now(self):
        self.assertIsNone(updater._pub_dt("13/11/2026 saat 10:00"))
        self.assertIsNone(updater._pub_dt(""))
        self.assertEqual(updater._to_iso("Thu, 12 Nov 2026 10:00:00 +0400"), "2026-11-12T06:00:00+00:00")
        self.assertEqual(updater._to_iso("2026-11-12T10:00:00"), "2026-11-12T06:00:00+00:00", "zonasız tarix Bakı vaxtıdır")

    def test_months_starting_with_capital_i_are_read(self):
        self.assertEqual(updater._list_date("İyun 30, 2026 11:00"), "2026-06-30T07:00:00+00:00")
        self.assertEqual(updater.parse_az_date("2 İyul 2026, 11:00"), "2026-07-02T07:00:00+00:00")
        self.assertEqual(updater._list_date("Oktyabr 30, 2026 11:00"), "2026-10-30T07:00:00+00:00")

    def test_leadership_filter_reads_upper_case_azerbaijani(self):
        for title in ("MÜSAVAT PARTİYASI bəyanat yaydı", "Müsavat Partiyası bəyanat yaydı", "MİLLİ MƏCLİSDƏ ZORAKILIQ", "Milli Məclisdə zorakılıq"):
            self.assertTrue(updater.is_negative_about_leadership(title, ""), title)
        for title in ("Bakıda yağış yağıb", "SUMQAYITDA yeni park açıldı", "ILHAM ALIYEV visits Ankara"):
            self.assertFalse(updater.is_negative_about_leadership(title, ""), title)

    def test_language_detection_uses_whole_words(self):
        self.assertEqual(updater.detect_lang("Çin “Game of Thrones” serialını qadağan etdi", "", "az"), "az")
        self.assertEqual(updater.detect_lang("Seçim için 'Call of Duty' benzetmesi", "", "tr"), "tr")
        self.assertEqual(updater.detect_lang("Why the rate is up in the US", "", "az"), "en")

    def test_control_characters_never_reach_the_feed_or_xml(self):
        self.assertEqual(updater._plain("Bakıda yeni yol\x08 açıldı\x00"), "Bakıda yeni yol açıldı")
        self.assertEqual(updater._xml("a\x0bb & c 🙂 ə"), "ab &amp; c 🙂 ə")
        ET.fromstring("<t>" + updater._xml("Bakıda\x08 yeni\x1f yol ə İ 🙂 &amp; <b>") + "</t>")


class OutputsTest(TempFiles):
    def test_youtube_rows_survive_the_fast_cycle(self):
        name = f"YouTube · {updater.YT_NEWS[0][0]}"
        updater.save_sources([{"name": "Oxu.az", "url": "u", "count": 3, "error": None}])
        updater.merge_sources([{"name": name, "url": "y", "count": 5, "error": None}, {"name": "YouTube · Köhnə kanal", "url": "z", "count": 1, "error": None}])
        updater.save_sources([{"name": "Oxu.az", "url": "u", "count": 4, "error": None}])
        names = [s["name"] for s in self.read("sources.json")["sources"]]
        self.assertEqual(names, ["Oxu.az", name], "siyahıdakı YouTube mənbəyi qalır, siyahıdan çıxmış kanal qalmır")
        updater.merge_sources([{"name": name, "url": "y", "count": 0, "error": "HTTPError: 404"}])
        row = next(s for s in self.read("sources.json")["sources"] if s["name"] == name)
        self.assertTrue(row["okAt"] and row["count"] == 5 and row["error"], "xəta olanda son uğur qalır")

    def test_a_failed_video_channel_keeps_its_previous_videos(self):
        def video(n, channel):
            link = f"https://www.youtube.com/watch?v=VIDEO{n:06d}"
            return {"id": hashlib.sha1(link.encode()).hexdigest()[:16], "title": f"Video {n}", "channel": channel, "videoId": f"VIDEO{n:06d}", "url": link, "publishedAt": iso(n * 10), "imageUrl": "i"}
        first, second = updater.YT_NEWS[0][0], updater.YT_NEWS[1][0]
        updater.VIDEO_FILE.write_text(json.dumps({"items": [video(1, first), video(2, second), video(3, "Siyahıda olmayan kanal")]}), encoding="utf-8")
        fresh = {"title": "Yeni video", "link": "https://www.youtube.com/watch?v=VIDEO000009", "description": "", "pubDate": iso(1), "image": "i"}
        def fake(url, limit):
            if url == updater.YT_NEWS[0][1]:
                return [fresh]
            raise OSError("şəbəkə")
        with patch.object(updater, "yt_items", side_effect=fake):
            updater.update_video()
        got = {(v["channel"], v["videoId"]) for v in self.read("video.json")["items"]}
        self.assertEqual(got, {(first, "VIDEO000009"), (second, "VIDEO000002")}, "alınan kanal təzələnir, alınmayan kanalın videosu qalır")
        with patch.object(updater, "yt_items", side_effect=OSError("şəbəkə")):
            updater.update_video()
        self.assertEqual(len(self.read("video.json")["items"]), 2, "bütün kanallar alınmayanda blok boşalmır")

    def test_a_new_short_stays_until_rss_has_it(self):
        mine = updater.YT_ACCOUNTS[1][1]
        def rss(v, mins, short=False):
            return {"title": v, "link": f"https://www.youtube.com/{'shorts/' if short else 'watch?v='}{v}", "description": "", "pubDate": iso(mins), "image": "", "author": ""}
        state = {"rss": [rss("VIDEO000001", 300), rss("SHORT000001", 200, True)], "shorts": [{"title": "s1", "link": "https://www.youtube.com/shorts/SHORT000001"}]}
        def pages(accounts):
            out = {}
            for url, who, _ in accounts:
                out[(url, "rss")] = list(state["rss"]) if who == mine else [rss("VIDEO000009", 900)]
                out[(url, "videos")], out[(url, "streams")] = [], []
                out[(url, "shorts")] = list(state["shorts"]) if who == mine else []
            return out
        def cycle():
            with patch.object(updater, "yt_account_pages", side_effect=pages), patch.object(updater, "read_feed", return_value=[]), \
                    patch.object(updater, "write_social_share_pages", return_value=0):
                updater.update_social()
            return [p["url"].rsplit("/", 1)[-1].replace("watch?v=", "") for p in self.read("social.json")["posts"] if p["who"] == mine]
        self.assertEqual(cycle(), ["SHORT000001", "VIDEO000001"])
        state["shorts"].insert(0, {"title": "s2", "link": "https://www.youtube.com/shorts/SHORT000002"})  # səhifədə var, RSS-də hələ yox
        self.assertEqual(cycle(), ["SHORT000002", "SHORT000001", "VIDEO000001"])
        stamp = self.read("social.json")["posts"][0]["publishedAt"]
        for _ in range(3):
            self.assertEqual(cycle(), ["SHORT000002", "SHORT000001", "VIDEO000001"], "növbəti dövrələrdə də qalır (əvvəl bir dəqiqədən sonra itirdi)")
        self.assertEqual(self.read("social.json")["posts"][0]["publishedAt"], stamp, "ilk görüldüyü vaxt dəyişmir")
        state["shorts"] = state["shorts"][1:]  # kanal Short-u silib
        self.assertEqual(cycle(), ["SHORT000001", "VIDEO000001"], "səhifədən çıxan yazı saxlanmır")

    def test_an_owner_removal_reaches_the_social_archive_and_url_variant_pages(self):
        url_a, url_b = "https://apa.az/siyaset/xeber-555222", "https://apa.az/siyaset/xeber-yeni-basliq-555222"
        id_a, id_b = (hashlib.sha1(u.encode()).hexdigest()[:16] for u in (url_a, url_b))
        post = {"id": id_a, "who": "prezident", "name": "Prezident İlham Əliyev", "network": "X", "text": "Paylaşım", "url": url_a, "publishedAt": iso(600), "imageUrl": None, "via": "APA"}
        keep = dict(post, id="b" * 16, url="https://apa.az/siyaset/basqa-777111")
        own = {"id": "c" * 16, "who": "prezident", "name": "Prezident İlham Əliyev", "network": "YouTube", "text": "Video", "url": "https://www.youtube.com/watch?v=VIDEO000001", "publishedAt": iso(700)}
        self.assertEqual(len(updater.write_social_archive([post, keep, own])), 3)
        with patch.object(content_policy, "_REMOVED_IDS", {id_a}), patch.object(content_policy, "_REMOVED_URLS", {url_a, url_b}):
            self.assertEqual({p["id"] for p in updater.write_social_archive([])}, {keep["id"], own["id"]}, "çıxarılan xəbərin paylaşımı arxivdə qalmır")
            self.assertEqual(updater.removed_ids() & {id_a, id_b}, {id_a, id_b}, "qeyddəki hər ünvanın id-si də çıxarılır")
            now = time.time()
            for sid in (id_a, id_b, "d" * 16):
                (updater.STORY_DIR / sid).mkdir(parents=True)
                (updater.STORY_DIR / sid / "index.html").write_text("<h1>x</h1>", encoding="utf-8")
            (updater.STORY_DIR / "index.json").write_text(json.dumps({sid: [int(now) - 3600, 1, "siyaset", updater.STORY_VER] for sid in (id_a, id_b, "d" * 16)}), encoding="utf-8")
            index = updater.write_story_pages([], now=now)
            self.assertEqual(list(index), ["d" * 16])
            self.assertFalse((updater.STORY_DIR / id_b / "index.html").exists(), "ikinci ünvanın səhifəsi də silinir")


if __name__ == "__main__":
    unittest.main()
