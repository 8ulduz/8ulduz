"""«Dinlə» səsləri (.github/scripts/ses.py): hansı xəbər səslənir, oxunan mətn necə qurulur."""
import datetime
import importlib.util
import pathlib
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("ses", ROOT / ".github" / "scripts" / "ses.py")
ses = importlib.util.module_from_spec(spec)
spec.loader.exec_module(ses)


class SesTest(unittest.TestCase):
    def test_pick_az_recent_newest_first(self):
        now = datetime.datetime(2026, 11, 7, 12, tzinfo=datetime.timezone.utc)
        at = lambda h: (now - datetime.timedelta(hours=h)).isoformat()
        row = lambda i, title, h, **kw: {"id": i * 16, "title": title, "source": "APA", "sourceUrl": f"https://apa.az/{i}",
                                         "category": "iqtisadiyyat", "publishedAt": at(h), "lang": "az", **kw}
        rows = [row("a", "Bakıda yeni park açıldı", 1), row("b", "Neft qiyməti artdı", 2, alts=[{"source": "Report", "title": "Neft qiyməti artdı", "sourceUrl": "https://report.az/1"}]),
                row("c", "Rus xəbəri", 1, lang="ru"), row("d", "Köhnə xəbər", 40), row("e", "Artıq səslənib", 1),
                {**row("f", "Keçidsiz", 1), "sourceUrl": "http://x.az/1"}]
        got = [a["title"] for a in ses.pick(rows, {"e" * 16}, now)]
        self.assertEqual(got, ["Bakıda yeni park açıldı", "Neft qiyməti artdı"])

    def test_script_starts_with_title_and_source_then_full_text(self):
        a = {"title": "Bakıda yağış.", "source": "APA", "summary": "Qısa"}
        self.assertEqual(ses.script_of(a, "Bakıda yağış. Sabah  güclü yağış gözlənilir."), "Bakıda yağış. APA xəbər verir. Sabah güclü yağış gözlənilir.")
        self.assertEqual(ses.script_of(a, ""), "Bakıda yağış. APA xəbər verir. Qısa", "tam mətn alınmasa saytdakı xülasə")

    def test_minute_feed_stories_are_added_once(self):
        feed = [{"id": "a" * 16, "title": "Köhnə"}]
        live = [{"id": "b" * 16, "title": "Təzə"}, {"id": "a" * 16, "title": "Köhnə"}]
        self.assertEqual([a["title"] for a in ses.merged(feed, live)], ["Təzə", "Köhnə"])

    def test_small_batches_so_a_new_story_is_voiced_within_a_minute(self):
        # Sahib, 2026-11-08: «bizim hədəf anında dinləyə bilməkdir». 40-lıq dəstədə təzə xəbər ~5 dəqiqə gözləyirdi.
        self.assertLessEqual(ses.PER_RUN, 8)
        wf = (ROOT / ".github" / "ses-reposu" / "ses.yml").read_text(encoding="utf-8")
        self.assertIn('cron: "*/10 * * * *"', wf)
        self.assertIn("sleep 15", wf)
        # Cədvəl gecikir/buraxılır: iş bitəndə növbətini özü işə salır.
        self.assertIn("actions: write", wf)
        self.assertIn('gh workflow run ses.yml -R "${{ github.repository }}"', wf)

    def test_full_store_makes_room_for_newer_stories_only(self):
        now = 1_800_000_000
        a, b, c = "a" * 16, "b" * 16, "c" * 16
        pub = {a: now - 20 * 3600, c: now - 3600}
        born = {a: now - 3600, b: now - 2 * 3600, c: now - 600}
        self.assertEqual(ses.evict({a: 1, b: 1, c: 1}, {a, c}, pub, born, now), b, "əvvəl lentdən çıxmış səs")
        self.assertEqual(ses.evict({a: 1, c: 1}, {a, c}, pub, born, now - 1800), a, "sonra ən köhnə xəbər")
        self.assertIsNone(ses.evict({c: 1}, {c}, pub, born, now - 5 * 3600), "təzə xəbər köhnə xəbər üçün silinmir")

    def test_long_text_is_cut_at_a_sentence(self):
        text = ("Bir cümlə budur. " * 400).strip()
        out = ses.clip(text, 1000)
        self.assertLessEqual(len(out), 1000)
        self.assertTrue(out.endswith("."))


if __name__ == "__main__":
    unittest.main()
