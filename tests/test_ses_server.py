"""«Dinlə» SARA səs serveri (.github/ses-server): mətnin modelə hazırlanması və oxunan mətn (sahib, 2026-11-08: «sara»)."""
import importlib.util
import os
import pathlib
import sys
import tempfile
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
SRV = ROOT / ".github" / "ses-server"
sys.path.insert(0, str(SRV))
import az_text  # noqa: E402

os.environ["SES_CACHE"] = tempfile.mkdtemp()
spec = importlib.util.spec_from_file_location("ses_server", SRV / "server.py")
server = importlib.util.module_from_spec(spec)
spec.loader.exec_module(server)


class NumbersTest(unittest.TestCase):
    def test_cardinals(self):
        for n, words in [(0, "sıfır"), (7, "yeddi"), (11, "on bir"), (105, "yüz beş"), (1000, "min"), (2026, "iki min iyirmi altı"),
                         (1500000, "bir milyon beş yüz min"), (300000000, "üç yüz milyon")]:
            self.assertEqual(az_text.number_words(n), words)

    def test_ordinals_decimals(self):
        self.assertEqual(az_text.ordinal_words(11), "on birinci")
        self.assertEqual(az_text.ordinal_words(3), "üçüncü")
        self.assertEqual(az_text.decimal_words("1", "70"), "bir tam yüzdə yetmiş")
        self.assertEqual(az_text.decimal_words("2", "5"), "iki tam onda beş")


class VerbalizeTest(unittest.TestCase):
    def test_news_patterns(self):
        v = az_text.verbalize
        self.assertEqual(v("Hesab 2-1 oldu"), "Hesab iki-bir oldu")
        self.assertEqual(v("Qiymət 15% artdı"), "Qiymət on beş faiz artdı")
        self.assertEqual(v("07.11.2026 tarixində"), "yeddi noyabr iki min iyirmi altı tarixində")
        self.assertEqual(v("11-ci tur"), "on birinci tur")
        self.assertEqual(v("Dollar 1.70 manat"), "Dollar bir tam yüzdə yetmiş manat")
        self.assertEqual(v("2 500 nəfər"), "iki min beş yüz nəfər")
        self.assertEqual(v("Saat 19:30-da"), "Saat on doqquz otuz-da")
        self.assertEqual(v("$100 və 50 AZN"), "yüz dollar və əlli manat")

    def test_azerbaijani_case_and_model_alphabet(self):
        self.assertEqual(az_text.lower_az("İLHAM ƏLİYEV BAKI"), "ilham əliyev bakı")
        out = az_text.phrases("«Napoli»nin prezidenti Aurelio De Laurentis görüşüb. 2026-cı ildə 15% artım! Necə?")
        self.assertTrue(all(set(s) <= az_text.ALLOWED for s, _ in out), out)
        self.assertEqual([s for s, _ in out], ["napolinin prezidenti aurelio de laurentis görüşüb", "iki min iyirmi altıncı ildə on beş faiz artım", "necə"])
        self.assertTrue(all(p > 0 for _, p in out))


class ScriptTest(unittest.TestCase):
    def test_title_source_then_full_text(self):
        self.assertEqual(server.script("Bakıda yağış.", "APA", "Bakıda yağış. Sabah  güclü yağış."), "Bakıda yağış. APA xəbər verir. Sabah güclü yağış.")
        self.assertEqual(server.script("Başlıq", "APA", "", "<p>Xülasə</p>"), "Başlıq. APA xəbər verir. Xülasə")

    def test_only_https_public_sources_and_site_referer(self):
        self.assertTrue(server.ALLOWED_REF.match("https://8ulduz.az/#/xeber/1"))
        self.assertFalse(server.ALLOWED_REF.match("https://8ulduz.az.evil.com/"))
        self.assertEqual(server.key_of("https://apa.az/1"), server.key_of("https://apa.az/1"))


if __name__ == "__main__":
    unittest.main()
