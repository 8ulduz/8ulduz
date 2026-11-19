"""Mənbə xronologiyası sınağı, PR 3: statik xəbər səhifəsinin bölməsi (updater.xron_on, xron_block, story_page, write_story_pages).
Şablonun mətni (_STORY_HTML) dəyişmir: STORY_VER qalxmır, köhnə səhifələr yenidən yazılmır."""
import pathlib
import tempfile
import unittest
from unittest import mock

import updater

AT = "2026-11-21T08:00:00+00:00"   # sınaq başlayandan sonra (XRON_START = 2026-11-20 00:00 Bakı)


def art(sid, n=4, at=AT):
    names = {"report.az": "Report", "trend.az": "Trend", "axar.az": "Axar.az", "oxu.az": "Oxu.az"}
    hosts = ["apa.az", "report.az", "trend.az", "axar.az", "oxu.az"][:n]
    alts = [{"source": names[h], "sourceUrl": f"https://{h}/x/{sid}", "title": f"Başlıq {h}"} for h in hosts[1:]]
    return {"id": sid, "title": "Sürət həddinin aşılması səbəbindən 256 nəfər ölüb", "summary": "Yol polisi məlumat yayıb.",
            "category": "gundem", "source": "APA", "sourceUrl": f"https://apa.az/x/{sid}", "publishedAt": at, "lang": "az", "alts": alts}


def cache(sid, times):
    """{host: vaxt və ya None} -> verify_source_times keşi."""
    return {f"https://{h}/x/{sid}": {"v": "təsdiq" if t else "açılmadı", "t": t or "", "s": 200 if t else 403, "at": AT} for h, t in times.items()}


B, A = "0" + "a" * 15, "1" + "a" * 15


class OnTest(unittest.TestCase):
    def test_only_b_group_after_the_start(self):
        self.assertTrue(updater.xron_on(art(B)))
        self.assertFalse(updater.xron_on(art(A)), "A qrupu (nəzarət)")
        self.assertFalse(updater.xron_on(art(B, at="2026-11-19T08:00:00+00:00")), "sınaqdan əvvəlki səhifə dəyişmir")


class BlockTest(unittest.TestCase):
    def test_section_sorted_first_publisher_and_undetermined(self):
        c = cache(B, {"report.az": "2026-11-21T08:29:00+00:00", "apa.az": "2026-11-21T08:34:00+00:00", "trend.az": None,
                      "axar.az": "2026-11-21T09:20:00+00:00"})
        page = updater.story_page(art(B), xron=c)
        self.assertIn("<h2>Xəbərin yayılma xronologiyası</h2>", page)
        self.assertIn("3 mənbənin dərc vaxtı mənbənin öz səhifəsi ilə təsdiqlənib · ilk və son dərc arasında 51 dəq", page)
        first = page.index('<time datetime="2026-11-21T08:29:00+00:00">12:29</time> <a href="https://report.az/x/')
        self.assertLess(first, page.index(">12:34</time>"), "vaxta görə sıralanır")
        self.assertIn("Report</a> <small>— izlənilən mənbələr arasında ilk dərc edən</small>", page, "əsas mənbə (APA) ilk olmaya bilər")
        self.assertIn("<small>+51 dəq</small>", page)
        self.assertIn('<h3>Dərc vaxtı dəqiqləşdirilməyib</h3><ul><li><a href="https://trend.az/x/', page)
        self.assertLess(page.index("Bu xəbəri yazan mənbələr"), page.index("Xəbərin yayılma xronologiyası"), "mənbə siyahısından sonra")

    def test_no_section_for_control_group_old_pages_or_single_time(self):
        c = cache(B, {"report.az": "2026-11-21T08:29:00+00:00", "apa.az": "2026-11-21T08:34:00+00:00"})
        self.assertNotIn("xronologiyası", updater.story_page(art(A), xron=cache(A, {"apa.az": AT, "report.az": AT})))
        self.assertNotIn("xronologiyası", updater.story_page(art(B, at="2026-11-19T08:00:00+00:00"), xron=c))
        self.assertNotIn("xronologiyası", updater.story_page(art(B), xron=cache(B, {"apa.az": AT})), "1 təsdiqlənmiş vaxt: bölmə yoxdur")

    def test_multi_day_shows_the_day(self):
        c = cache(B, {"apa.az": "2026-11-21T19:50:00+00:00", "report.az": "2026-11-22T07:10:00+00:00"})
        page = updater.story_page(art(B, at="2026-11-21T19:50:00+00:00"), xron=c)
        self.assertIn(">21 noyabr, 23:50</time>", page)
        self.assertIn("11 saat 20 dəq", page)

    def test_times_survive_a_rewrite_from_the_page(self):
        c = cache(B, {"report.az": "2026-11-21T08:29:00+00:00", "apa.az": "2026-11-21T08:34:00+00:00"})
        page = updater.story_page(art(B), xron=c)
        row, _ = updater.story_row_from_page(B, [0, 4, "gundem"], page)
        self.assertEqual(set(row["xr"]), {f"https://report.az/x/{B}", f"https://apa.az/x/{B}"})
        again = updater.story_page(row)   # keş 3 gündən sonra silinib: səhifə öz vaxtlarını saxlayır
        self.assertIn("<h2>Xəbərin yayılma xronologiyası</h2>", again)

    def test_template_text_is_unchanged(self):
        self.assertNotIn("xron", updater._STORY_HTML, "şablon dəyişmir: STORY_VER qalxmır, köhnə səhifələr yenidən yazılmır")


class RewriteTest(unittest.TestCase):
    def test_b_page_is_rewritten_when_new_confirmations_arrive(self):
        a = art(B)
        with tempfile.TemporaryDirectory() as tmp:
            root = pathlib.Path(tmp)
            xron = root / "xron.json"
            with mock.patch.object(updater, "STORY_DIR", root / "xeber"), mock.patch.object(updater, "XRON_FILE", xron), \
                 mock.patch.object(updater, "time", wraps=updater.time) as t:
                t.time.return_value = 1795255200.0   # 2026-11-21 10:00 UTC: AT-dan 2 saat sonra
                xron.write_text(updater.json.dumps(cache(B, {"apa.az": "2026-11-21T08:34:00+00:00"})), encoding="utf-8")
                idx = updater.write_story_pages([a])
                self.assertEqual(idx[B][4], 1)
                page = root / "xeber" / B / "index.html"
                self.assertNotIn("xronologiyası", page.read_text(encoding="utf-8"))
                xron.write_text(updater.json.dumps(cache(B, {"apa.az": "2026-11-21T08:34:00+00:00", "report.az": "2026-11-21T08:29:00+00:00"})), encoding="utf-8")
                idx = updater.write_story_pages([a])
                self.assertEqual(idx[B][4], 2)
                self.assertIn("<h2>Xəbərin yayılma xronologiyası</h2>", page.read_text(encoding="utf-8"), "yeni təsdiq: səhifə yenidən yazılır")
                stamp = page.stat().st_mtime_ns
                updater.write_story_pages([a])
                self.assertEqual(stamp, page.stat().st_mtime_ns, "dəyişiklik yoxdursa yazılmır")
                c = updater.write_story_pages([art(A)])
                self.assertEqual(len(c[A]), 4, "A qrupunun siyahı sətri əvvəlki kimi")


if __name__ == "__main__":
    unittest.main()
