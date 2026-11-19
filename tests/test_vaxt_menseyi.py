"""Vaxtın mənşəyi (mənbə xronologiyası sınağı, PR 1): updater.time_origin, time_ok, record_time_origins.
Şəbəkə yoxdur; yalnız yavaş dövrədə işləyir və sayta yazmır (.cache/vaxt.json)."""
import datetime
import inspect
import json
import pathlib
import tempfile
import unittest
from unittest import mock

import updater

UTC = datetime.timezone.utc
NOW = datetime.datetime(2026, 11, 19, 10, 0, tzinfo=UTC)


class OriginTest(unittest.TestCase):
    def test_origins(self):
        cases = {
            "lent": {"link": "https://apa.az/a/1", "pubDate": "Thu, 19 Nov 2026 12:29:00 +0400"},
            "lent-zonasız": {"link": "https://iki-sahil.az/a/1", "pubDate": "2026-11-19 02:02:00"},
            "tarixsiz": {"link": "https://x.az/a/1", "pubDate": ""},
            "oxunmadı": {"link": "https://x.az/a/2", "pubDate": "dünən axşam"},
            "gələcək": {"link": "https://x.az/a/3", "pubDate": "Thu, 19 Nov 2026 13:30:00 +0000"},
        }
        for want, it in cases.items():
            self.assertEqual(updater.time_origin(it, NOW)[1], want, it)
        iso, _ = updater.time_origin(cases["lent"], NOW)
        self.assertEqual(iso, "2026-11-19T08:29:00+00:00", "UTC-yə normallaşır")
        self.assertEqual(updater.time_origin(cases["lent-zonasız"], NOW)[0], "2026-11-18T22:02:00+00:00", "zonasız: Bakı vaxtı")

    def test_url_stamp_wins_like_make_article(self):
        it = {"link": "https://azerbaijan-news.az/az/posts/detail/xeber-1763540000/1", "pubDate": "Thu, 19 Nov 2026 09:00:00 +0000"}
        with mock.patch.object(updater, "fixed_source_date", return_value="2026-11-19T07:33:20+00:00"):
            self.assertEqual(updater.time_origin(it, NOW), ("2026-11-19T07:33:20+00:00", "url-möhürü"))

    def test_plausibility(self):
        f = "2026-11-19T10:00:00+00:00"
        self.assertTrue(updater.time_ok({"t": "2026-11-19T09:40:00+00:00", "o": "lent", "f": f}))
        self.assertTrue(updater.time_ok({"t": "2026-11-19T10:09:00+00:00", "o": "lent", "f": f}), "10 dəqiqəyə qədər dözüm")
        self.assertFalse(updater.time_ok({"t": "2026-11-19T14:00:00+00:00", "o": "lent", "f": f}), "ilk görülmədən sonra: qurşaq səhvi")
        for o in ("tarixsiz", "oxunmadı", "gələcək"):
            self.assertFalse(updater.time_ok({"t": "2026-11-19T09:40:00+00:00", "o": o, "f": f}), o)
        self.assertFalse(updater.time_ok({"t": "", "o": "lent", "f": f}))


class RecordTest(unittest.TestCase):
    def run_cycle(self, path, feeds, now):
        with mock.patch.object(updater, "VAXT_FILE", path), mock.patch.object(updater, "_feed_cache", return_value=feeds), \
             mock.patch.object(updater, "CACHE_DIR", path.parent):
            return updater.record_time_origins(now)

    def test_first_seen_is_kept_and_old_rows_pruned(self):
        with tempfile.TemporaryDirectory() as d:
            path = pathlib.Path(d) / "vaxt.json"
            feeds = {"APA": {"items": [{"link": "https://apa.az/a/1", "pubDate": "Thu, 19 Nov 2026 12:29:00 +0400"}]}}
            rows = self.run_cycle(path, feeds, NOW)
            self.assertEqual(rows["https://apa.az/a/1"], {"t": "2026-11-19T08:29:00+00:00", "o": "lent", "f": "2026-11-19T10:00:00+00:00", "ok": True})
            later = NOW + datetime.timedelta(hours=1)
            rows = self.run_cycle(path, feeds, later)
            self.assertEqual(rows["https://apa.az/a/1"]["f"], "2026-11-19T10:00:00+00:00", "ilk görülmə dəyişmir")
            rows = self.run_cycle(path, {}, NOW + datetime.timedelta(days=4))
            self.assertEqual(rows, {}, "3 gündən köhnə sətirlər silinir")
            self.assertEqual(json.loads(path.read_text(encoding="utf-8")), {})

    def test_link_is_fixed_like_the_feed(self):
        with tempfile.TemporaryDirectory() as d:
            path = pathlib.Path(d) / "vaxt.json"
            feeds = {"Reyting": {"items": [{"link": "https://reyting.az/haber/abc.html", "pubDate": "Thu, 19 Nov 2026 12:00:00 +0400"}]}}
            rows = self.run_cycle(path, feeds, NOW)
            self.assertIn("https://reyting.az/xeber/abc", rows, "açar xəbərin sourceUrl-i ilə eynidir (fix_source_link)")


class PlacementTest(unittest.TestCase):
    def test_only_in_the_slow_cycle_and_never_in_data(self):
        self.assertIn("record_time_origins", inspect.getsource(updater.slow_cycle))
        self.assertNotIn("record_time_origins", inspect.getsource(updater.run_fast), "sürətli dövrəyə iş əlavə olunmur")
        self.assertEqual(updater.VAXT_FILE.parent, updater.CACHE_DIR, "sayta (data/) yazılmır")


if __name__ == "__main__":
    unittest.main()
