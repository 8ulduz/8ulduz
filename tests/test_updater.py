import contextlib
import datetime
import io
import json
import pathlib
import tempfile
import unittest
from unittest.mock import patch

import updater


class CategoriesTest(unittest.TestCase):
    def test_turkish_company_revenue_is_economy(self):
        self.assertEqual(updater.label_for("Çimsa'dan 9 ayda 41,8 milyar TL gelir", "", "tr"), "İqtisadiyyat")

    def test_ai_news_is_technology(self):
        self.assertEqual(updater.label_for("Azərbaycanda süni intellekt üzrə milli dil modelləri hazırlanır", "", "az"), "Texnologiya")
        self.assertEqual(updater.SLUGS["Texnologiya"], "texnologiya")

    def test_raw_link_is_stripped_from_title(self):
        self.assertEqual(updater._plain("Harri Keyn mükafat qazanıb https://report.az/futbol/abc", title=True), "Harri Keyn mükafat qazanıb")


class FootballTest(unittest.TestCase):
    def test_parse_pfl_builds_table_rounds_and_scorers(self):
        seasons = {"data": [{"id": 76, "title": "2026-2027", "leagues": [{"id": 52, "title": "Misli Premyer Liqası"}]}]}
        grid = {"data": [
            {"title": "Sabah", "logo": "s.png", "rate": {"o": 9, "q": 5, "h": 2, "m": 2, "vq": 12, "bq": 8, "tf": 4, "x": 17, "ordering": 2}},
            {"title": "Qarabağ", "logo": "q.png", "rate": {"o": 9, "q": 7, "h": 1, "m": 1, "vq": 18, "bq": 6, "tf": 12, "x": 22, "ordering": 1}},
        ]}
        tours = {"data": [
            {"title": "9", "is_current": 0, "games": [{"club_1": {"title": "Sabah"}, "club_2": {"title": "Qarabağ"}, "club_score_1": 0, "club_score_2": 0, "status": 3, "start_date": "25/10/2026 18:00", "stadion": {"title": "Bank Respublika Arena"}}]},
            {"title": "10", "is_current": 1, "games": [{"club_1": {"title": "Qəbələ"}, "club_2": {"title": "Qarabağ"}, "club_score_1": 0, "club_score_2": 0, "status": 0, "start_date": "31/10/2026 17:30", "stadion": None}]},
        ]}
        scorers = {"data": {"data": [{"club": {"title": "Şamaxı"}, "player": {"name": "Rikardo", "surname": "Apolinario"}, "value": "3"}]}}
        d = updater.parse_pfl(seasons, grid, tours, scorers)
        self.assertEqual([t["team"] for t in d["table"]], ["Qarabağ", "Sabah"])
        self.assertEqual(d["table"][0]["pos"], 1)
        self.assertEqual(d["table"][0]["pts"], 22)
        self.assertEqual(d["roundPlayed"], "9")
        self.assertEqual(d["roundNext"], "10")
        self.assertTrue(d["results"][0]["played"])
        self.assertEqual(d["results"][0]["date"], "2026-10-25T18:00+04:00")
        self.assertFalse(d["fixtures"][0]["played"])
        self.assertEqual(d["fixtures"][0]["home"], "Qəbələ")
        self.assertEqual(d["scorers"], [{"name": "Rikardo Apolinario", "club": "Şamaxı", "goals": 3}])
        self.assertEqual(d["league"], "Misli Premyer Liqası")


class SectionPagesTest(unittest.TestCase):
    def test_section_pages_and_sitemap_are_written(self):
        articles = [
            {"id": "1", "title": "Qarabağ <b>qalib</b> gəldi", "category": "idman", "lang": "az", "source": "APA", "sourceUrl": "https://apa.az/1", "publishedAt": "2026-10-27T10:00:00+00:00"},
            {"id": "2", "title": "Galatasaray kazandı", "category": "idman", "lang": "tr", "source": "NTV", "sourceUrl": "https://ntv.com.tr/2", "publishedAt": "2026-10-27T11:00:00+00:00"},
        ]
        with tempfile.TemporaryDirectory() as tmp:
            root = pathlib.Path(tmp)
            with patch.object(updater, "SECTIONS_DIR", root / "bolme"), patch.object(updater, "SITEMAP_FILE", root / "sitemap.xml"):
                updater.write_sections(articles)
                updater.write_sitemap()
                page = (root / "bolme" / "idman" / "index.html").read_text(encoding="utf-8")
                sitemap = (root / "sitemap.xml").read_text(encoding="utf-8")
                pages = [d for d in (root / "bolme").iterdir() if (d / "index.html").exists()]
        self.assertIn("Qarabağ &lt;b&gt;qalib&lt;/b&gt; gəldi", page)
        self.assertNotIn("Galatasaray", page)  # yalnız Azərbaycan dilində başlıqlar
        self.assertIn('src="../../assets/app.js"', page)
        self.assertIn('"../../#/bolme/idman"', page)
        self.assertIn(updater.SITE + "bolme/idman/", sitemap)
        self.assertEqual(len(pages), len(updater.SECTIONS))

    def test_background_reference_is_not_chronicle(self):
        for title in ("2027-ci il nə ilidir?", "Keçmiş köçkünlər Laçında qəbul edildi"):
            with self.subTest(title=title):
                self.assertNotEqual(updater.label_for(title, "Prezident İlham Əliyev sərəncam imzalayıb.", "az"), "Prezident")

    def test_actual_chronicle_in_multiple_languages(self):
        for title, lang in (("İlham Əliyev qonağı qəbul edib", "az"),
                            ("Prezidentin sosial şəbəkə hesablarında paylaşım", "az"),
                            ("Mehriban Əliyeva rəssamı təbrik edib", "az"),
                            ("Ильхам Алиев принял делегацию", "ru"),
                            ("President Ilham Aliyev meets delegation", "en")):
            with self.subTest(title=title):
                self.assertEqual(updater.label_for(title, "", lang), "Prezident")

    def test_absheron_is_not_usa(self):
        self.assertEqual(updater.label_for("Abşeronda oğula hökm oxundu", "məhkəmə qərarı", "az"), "Cəmiyyət")
        self.assertTrue(updater.has_any(updater.norm_az("ABŞ-da görüş keçirildi"), ["abş"]))
        self.assertTrue(updater.has_any(updater.norm_az("ABŞ"), ["abş"]))
        self.assertFalse(updater.has_any(updater.norm_az("Abşeron"), ["abş"]))

    def test_real_crime_headlines_are_society(self):
        self.assertEqual(updater.label_for("Abşeronda anasının üstünə benzin töküb yandıran oğula hökm oxundu",
                                          "Abdurrəhman Həsənlinin məhkəmə prosesi başa çatıb.", "az"), "Cəmiyyət")
        self.assertEqual(updater.label_for("Еще одна массовая драка в Баку",
                                          "Инцидент случился перед банкетным залом.", "ru"), "Cəmiyyət")
        self.assertNotEqual(updater.label_for("Mehribanlıq nədir?", "", "az"), "Prezident")


class UpdateHealthTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(dir=pathlib.Path(__file__).parent)
        self.root = pathlib.Path(self.tmp.name)
        self.patches = []
        for name, value in {"OUT_DIR": self.root, "OUT_FILE": self.root / "news.json",
                            "STATUS_FILE": self.root / "status.json", "SOURCES_FILE": self.root / "sources.json",
                            "FEEDS": [("Test", "https://example.com/rss", "az", None)]}.items():
            p = patch.object(updater, name, value)
            p.start()
            self.patches.append(p)
        self.article = {"id": "old", "sourceUrl": "https://example.com/old", "source": "Test",
                        "title": "Məktəb açıldı", "summary": "", "lang": "az", "category": "cemiyyet",
                        "publishedAt": datetime.datetime.now(datetime.timezone.utc).isoformat()}
        updater.OUT_FILE.write_text(json.dumps({"articles": [self.article]}), encoding="utf-8")

    def tearDown(self):
        for p in reversed(self.patches):
            p.stop()
        self.tmp.cleanup()

    def cycle(self, feed_result):
        with patch.object(updater, "fetch_feed", return_value=feed_result), \
             patch.object(updater, "official_items", return_value=([], [])), \
             patch.object(updater, "official_source_rows", return_value=[]), \
             patch.object(updater, "fill_og_images", return_value=0), \
             contextlib.redirect_stdout(io.StringIO()):
            return updater.main()

    def test_all_sources_fail_preserves_news_and_success_time(self):
        before = updater.OUT_FILE.read_bytes()
        updater.STATUS_FILE.write_text('{"checkedAt":"2026-10-01T00:00:00+00:00","ok":true}')
        result = self.cycle(("Test", [], "timeout", "https://example.com/rss"))
        self.assertFalse(result["ok"])
        self.assertEqual(updater.OUT_FILE.read_bytes(), before)
        updater.write_status(**result)
        status = json.loads(updater.STATUS_FILE.read_text())
        self.assertFalse(status["ok"])
        self.assertEqual(status["checkedAt"], "2026-10-01T00:00:00+00:00")
        self.assertIn("attemptedAt", status)

    def test_success_without_new_articles_is_success(self):
        item = {"link": self.article["sourceUrl"], "title": self.article["title"], "description": ""}
        result = self.cycle(("Test", [item], None, "https://example.com/rss"))
        self.assertTrue(result["ok"])
        self.assertEqual(result["successful"], 1)

    def test_cli_failure_has_nonzero_exit_and_no_public_rewrite(self):
        with patch.object(updater, "main", return_value={"ok": False, "successful": 0, "total": 1}), \
             patch.object(updater, "write_public") as public, \
             patch.object(updater.sys, "argv", ["updater.py", "--no-markets", "--no-social"]):
            self.assertEqual(updater.run(), 1)
            public.assert_not_called()

    def test_unexpected_error_has_nonzero_exit(self):
        with patch.object(updater, "main", side_effect=RuntimeError("test")), \
             patch.object(updater.sys, "argv", ["updater.py", "--no-markets", "--no-social"]), \
             contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(updater.run(), 1)


if __name__ == "__main__":
    unittest.main()
