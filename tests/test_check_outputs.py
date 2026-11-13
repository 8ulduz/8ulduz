import json
import pathlib
import sys
import tempfile
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent / ".github" / "scripts"))
from check_outputs import bad_outputs, enforce_policy  # noqa: E402
import content_policy  # noqa: E402
from unittest.mock import patch  # noqa: E402


class CheckOutputsTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = pathlib.Path(self.tmp.name)
        (self.root / "data").mkdir()
        (self.root / "data" / "news.json").write_text(json.dumps({"articles": [{"id": 1}]}), encoding="utf-8")
        (self.root / "data" / "status.json").write_text("{}", encoding="utf-8")
        (self.root / "feed.xml").write_text("<rss><channel/></rss>", encoding="utf-8")

    def tearDown(self):
        self.tmp.cleanup()

    def test_removed_story_leaves_the_social_block_and_its_archive(self):
        gone = {"id": "a" * 16, "who": "prezident", "text": "Paylaşım", "url": "https://apa.az/siyaset/x-555222", "via": "APA"}
        kept = {"id": "b" * 16, "who": "prezident", "text": "Başqa", "url": "https://apa.az/siyaset/y-777111", "via": "APA"}
        own = {"id": "c" * 16, "who": "prezident", "text": "Video", "url": "https://www.youtube.com/watch?v=VIDEO000001"}
        for name in ("social.json", "social-arxiv.json"):
            (self.root / "data" / name).write_text(json.dumps({"posts": [gone, kept, own]}), encoding="utf-8")
        self.assertNotIn("social-arxiv.json", enforce_policy(self.root), "çıxarılma yoxdursa fayla toxunulmur")
        with patch.object(content_policy, "_REMOVED_URLS", {gone["url"]}):
            removed = enforce_policy(self.root)
        for name in ("social.json", "social-arxiv.json"):
            self.assertIn(name, removed)
            ids = [p["id"] for p in json.loads((self.root / "data" / name).read_text(encoding="utf-8"))["posts"]]
            self.assertEqual(ids, [kept["id"], own["id"]], name)

    def test_valid_outputs_pass(self):
        self.assertEqual(bad_outputs(self.root), [])

    def test_truncated_json_and_xml_are_reported(self):
        (self.root / "data" / "og.json").write_text('{"a": "b', encoding="utf-8")
        (self.root / "feed.xml").write_text("<rss><channel>", encoding="utf-8")
        self.assertEqual(bad_outputs(self.root), ["data/og.json", "feed.xml"])

    def test_empty_news_feed_is_reported(self):
        (self.root / "data" / "news.json").write_text('{"articles": []}', encoding="utf-8")
        self.assertEqual(bad_outputs(self.root), ["data/news.json"])

    def test_language_feed_files_need_an_article_list_but_may_be_empty(self):
        (self.root / "data" / "news.en.json").write_text('{"articles": []}', encoding="utf-8")
        self.assertEqual(bad_outputs(self.root), [])
        (self.root / "data" / "news.ru.json").write_text('{"count": 1}', encoding="utf-8")
        self.assertEqual(bad_outputs(self.root), ["data/news.ru.json"])


if __name__ == "__main__":
    unittest.main()
