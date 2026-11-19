"""Səhifə ilə təsdiq (mənbə xronologiyası sınağı, PR 2): updater.xron_group, page_times, xron_verdict, verify_source_times.
Şəbəkə yoxdur (fetch əvəz olunur); yalnız yavaş dövrədə işləyir və sayta yazmır (.cache/xron.json)."""
import datetime
import inspect
import pathlib
import tempfile
import unittest
from unittest import mock

import updater

UTC = datetime.timezone.utc
NOW = datetime.datetime(2026, 11, 19, 10, 0, tzinfo=UTC)
FEED = "2026-11-19T08:29:00+00:00"   # Bakı 12:29


def page(pub="", zoned=True, mod=""):
    return {"pub": pub, "zoned": zoned, "mod": mod}


class GroupTest(unittest.TestCase):
    def test_split_by_first_hex_digit(self):
        self.assertEqual({updater.xron_group(h + "123") for h in "02468ace"}, {"B"})
        self.assertEqual({updater.xron_group(h + "123") for h in "13579bdf"}, {"A"})
        self.assertEqual(updater.xron_group(""), "A")


class PageTimesTest(unittest.TestCase):
    def test_published_and_modified_are_separate(self):
        html = ('<script type="application/ld+json">{"datePublished":"2026-11-19T12:29:00+04:00","dateModified":"2026-11-19T13:05:00+04:00"}</script>')
        self.assertEqual(updater.page_times(html, NOW), {"pub": "2026-11-19T08:29:00+00:00", "zoned": True, "mod": "2026-11-19T09:05:00+00:00"})

    def test_meta_and_zoneless(self):
        html = '<meta property="article:published_time" content="2026-11-19 02:02:00"><meta property="article:modified_time" content="2026-11-19T03:00:00+04:00">'
        got = updater.page_times(html, NOW)
        self.assertEqual((got["pub"], got["zoned"]), ("2026-11-18T22:02:00+00:00", False), "zonasız: Bakı vaxtı, işarələnir")
        self.assertEqual(got["mod"], "2026-11-18T23:00:00+00:00")

    def test_1970_and_future_are_ignored(self):
        html = '{"datePublished":"1970-01-01T00:00:00+00:00"}<time datetime="2026-11-19T12:29:00+04:00">'
        self.assertEqual(updater.page_times(html, NOW)["pub"], "2026-11-19T08:29:00+00:00", "1970 atlanır, növbəti namizəd götürülür")
        self.assertEqual(updater.page_times('{"datePublished":"2027-01-01T00:00:00Z"}', NOW)["pub"], "")


class VerdictTest(unittest.TestCase):
    def test_rules(self):
        cases = [
            (page("2026-11-19T08:31:00+00:00"), ("təsdiq", "2026-11-19T08:31:00+00:00")),
            (page("2026-11-19T04:29:00+00:00"), ("qurşaq", "2026-11-19T04:29:00+00:00")),
            (page("2026-11-19T04:29:00+00:00", zoned=False), ("uyğunsuz", "")),
            (page("2026-11-19T06:00:00+00:00", mod="2026-11-19T08:30:00+00:00"), ("yeniləmə", "2026-11-19T06:00:00+00:00")),
            (page("2026-11-19T06:00:00+00:00"), ("uyğunsuz", "")),
            (page("2026-11-16T08:29:00+00:00"), ("yararsız", "")),
            (page("2026-11-19T09:00:00+00:00"), ("yararsız", "")),
            (page(""), ("səhifədə vaxt yoxdur", "")),
        ]
        for p, want in cases:
            self.assertEqual(updater.xron_verdict(FEED, p), want, p)
        self.assertEqual(updater.xron_verdict("", page(FEED)), ("lentdə vaxt yoxdur", ""))

    def test_never_after_first_seen(self):
        self.assertEqual(updater.xron_verdict(FEED, page("2026-11-19T08:35:00+00:00"), first_seen="2026-11-19T08:20:00+00:00"),
                         ("ilk görülmədən sonra", ""))


class VerifyTest(unittest.TestCase):
    def art(self, sid, n, **kw):
        alts = [{"source": f"S{i}", "sourceUrl": f"https://s{i}.az/{sid}", "publishedAt": FEED} for i in range(1, n)]
        return {"id": sid, "title": "Başlıq", "lang": "az", "category": "gundem", "source": "S0", "sourceUrl": f"https://s0.az/{sid}",
                "publishedAt": FEED, "alts": alts, **kw}

    def test_only_b_group_once_within_budget(self):
        calls = []

        def fetch(url):
            calls.append(url)
            return (403, {}) if "s2." in url else (200, page("2026-11-19T08:30:00+00:00"))

        arts = [self.art("0" + "a" * 15, 3), self.art("1" + "a" * 15, 5), self.art("2" + "b" * 15, 2)]
        with tempfile.TemporaryDirectory() as d:
            root = pathlib.Path(d)
            with mock.patch.object(updater, "XRON_FILE", root / "xron.json"), mock.patch.object(updater, "VAXT_FILE", root / "vaxt.json"), \
                 mock.patch.object(updater, "CACHE_DIR", root):
                done = updater.verify_source_times(arts, NOW, fetch)
                self.assertEqual(sorted(calls), sorted(f"https://s{i}.az/0{'a' * 15}" for i in range(3)), "yalnız B qrupu, 3+ mənbə")
                self.assertEqual(done[f"https://s0.az/0{'a' * 15}"]["v"], "təsdiq")
                self.assertEqual(done[f"https://s2.az/0{'a' * 15}"], {"v": "açılmadı", "t": "", "s": 403, "at": "2026-11-19T10:00:00+00:00"})
                calls.clear()
                updater.verify_source_times(arts, NOW, fetch)
                self.assertEqual(calls, [], "hər səhifə bir dəfə açılır, 403 də təkrar soruşulmur")
                with mock.patch.object(updater, "XRON_BUDGET", 1):
                    updater.verify_source_times([self.art("4" + "c" * 15, 4)], NOW, fetch)
                self.assertEqual(len(calls), 1, "dövrədə büdcədən çox sorğu yoxdur")
                gone = updater.verify_source_times([], NOW + datetime.timedelta(days=4), fetch)
                self.assertEqual(gone, {}, "3 gündən köhnə hökmlər silinir")

    def test_placement(self):
        self.assertIn("verify_source_times", inspect.getsource(updater.slow_cycle))
        self.assertNotIn("verify_source_times", inspect.getsource(updater.run_fast), "sürətli dövrəyə sorğu əlavə olunmur")
        self.assertEqual(updater.XRON_FILE.parent, updater.CACHE_DIR, "sayta (data/) yazılmır")
        self.assertLessEqual(updater.XRON_BUDGET, 60, "sahibin təsdiq etdiyi büdcə")


if __name__ == "__main__":
    unittest.main()
