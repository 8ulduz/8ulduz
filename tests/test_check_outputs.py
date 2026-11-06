import json
import pathlib
import sys
import tempfile
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent / ".github" / "scripts"))
from check_outputs import bad_outputs  # noqa: E402


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
