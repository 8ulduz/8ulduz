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
    def test_pick_az_recent_most_sources_first(self):
        now = datetime.datetime(2026, 11, 7, 12, tzinfo=datetime.timezone.utc)
        at = lambda h: (now - datetime.timedelta(hours=h)).isoformat()
        row = lambda i, title, h, **kw: {"id": i * 16, "title": title, "source": "APA", "sourceUrl": f"https://apa.az/{i}",
                                         "category": "iqtisadiyyat", "publishedAt": at(h), "lang": "az", **kw}
        rows = [row("a", "Bakıda yeni park açıldı", 1), row("b", "Neft qiyməti artdı", 2, alts=[{"source": "Report", "title": "Neft qiyməti artdı", "sourceUrl": "https://report.az/1"}]),
                row("c", "Rus xəbəri", 1, lang="ru"), row("d", "Köhnə xəbər", 40), row("e", "Artıq səslənib", 1),
                {**row("f", "Keçidsiz", 1), "sourceUrl": "http://x.az/1"}]
        got = [a["title"] for a in ses.pick(rows, {"e" * 16}, now)]
        self.assertEqual(got, ["Neft qiyməti artdı", "Bakıda yeni park açıldı"])

    def test_script_starts_with_title_and_source_then_full_text(self):
        a = {"title": "Bakıda yağış.", "source": "APA", "summary": "Qısa"}
        self.assertEqual(ses.script_of(a, "Bakıda yağış. Sabah  güclü yağış gözlənilir."), "Bakıda yağış. APA xəbər verir. Sabah güclü yağış gözlənilir.")
        self.assertEqual(ses.script_of(a, ""), "Bakıda yağış. APA xəbər verir. Qısa", "tam mətn alınmasa saytdakı xülasə")

    def test_long_text_is_cut_at_a_sentence(self):
        text = ("Bir cümlə budur. " * 400).strip()
        out = ses.clip(text, 1000)
        self.assertLessEqual(len(out), 1000)
        self.assertTrue(out.endswith("."))


if __name__ == "__main__":
    unittest.main()
