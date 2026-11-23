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
        self.assertEqual(v("Saat 19:30-da"), "Saat on doqquz otuzda")
        self.assertEqual(v("$100 və 50 AZN"), "yüz dollar və əlli manat")

    def test_azerbaijani_case_and_model_alphabet(self):
        self.assertEqual(az_text.lower_az("İLHAM ƏLİYEV BAKI"), "ilham əliyev bakı")
        out = az_text.phrases("«Napoli»nin prezidenti Aurelio De Laurentis görüşüb. 2026-cı ildə 15% artım! Necə?")
        self.assertTrue(all(set(s) <= az_text.ALLOWED for s, _ in out), out)
        self.assertEqual([s for s, _ in out], ["napolinin prezidenti aurelio de laurentis görüşüb", "iki min iyirmi altıncı ildə on beş faiz artım", "necə"])
        self.assertTrue(all(p > 0 for _, p in out))


def said(text):
    """Modelə gedən mətn (vergüldə bölünmüş hissələr « | » ilə — burada oxunuş yoxlanır, bölünmə yox)."""
    return " | ".join(s for s, _ in az_text.phrases(text, commas=True))


class HumanReadingTest(unittest.TestCase):
    """Sahib, 2026-11-23: «tam normal insan kimi oxunsun» — xəbər mətnində tez-tez gələn və anlaşılmaz oxunan hallar.
    Burada lüğətsiz qaydalar yoxlanır (lüğət Gemini-dən gəlir və dəyişə bilər): LEXICON test vaxtı boşalır."""

    def setUp(self):
        self.saved = dict(az_text.LEXICON)
        az_text.LEXICON.clear()

    def tearDown(self):
        az_text.LEXICON.clear()
        az_text.LEXICON.update(self.saved)

    def test_source_leftovers_are_not_read(self):
        self.assertEqual(said("Milli Hidrometeorologiya Xidmətindən bildirilib […] Source"), "milli hidrometeorologiya xidmətindən bildirilib")

    def test_acronyms_are_spelled_with_their_suffix(self):
        self.assertEqual(said("ABŞ-nin, ABŞ-da, ABŞ-ın, ABŞ-a"), "a-be-şenin | a-be-şedə | a-be-şenin | a-be-şeyə")
        self.assertEqual(said("FHN ötən həftə 34 nəfəri xilas edib"), "fe-he-en ötən həftə otuz dörd nəfəri xilas edib")
        self.assertEqual(said("BMT-nin və NATO-ya, MMA, KİV, USGS"), "be-em-tenin və natoya | em-em-a | ka-i-ve | u-es-ge-es")
        self.assertEqual(said("COVID-19 və COP31, AzTV-də, İctimai TV-nin"), "kovid-on doqquz və kop otuz bir | az te-vedə | ictimai te-venin")

    def test_capitalised_words_and_roman_numerals(self):
        self.assertEqual(said("VİDEO: Bakıda QƏZA OLDU - FOTOLAR"), "video | bakıda qəza oldu | fotolar")
        self.assertEqual(said("XII turda, II Dünya müharibəsi, XV əsr"), "on ikinci turda | ikinci dünya müharibəsi | on beşinci əsr")

    def test_number_suffix_is_attached(self):
        self.assertEqual(said("Noyabrın 19-da, 900-dən çox, 29-na qədər, 10-nun, 22-si, 3-ü, 42-yə, 300-ə, 160-la"),
                         "noyabrın on doqquzda | doqquz yüzdən çox | iyirmi doqquza qədər | onun | iyirmi ikisi | üçü | qırx ikiyə | üç yüzə | yüz altmışla")
        self.assertEqual(said("saat 18:00-dək, 10:00-da, 21:45-də, 15%-ə, 10-illik"),
                         "saat on səkkizədək | onda | iyirmi bir qırx beşdə | on beş faizə | onillik")
        self.assertEqual(said("3-otaqlı mənzil, 2026-2027-ci tədris ili"), "üç-otaqlı mənzil | iki min iyirmi altı-iki min iyirmi yeddinci tədris ili")

    def test_sites_initials_and_links_do_not_break_sentences(self):
        self.assertEqual(said("Modern.az xəbər verir. 8ulduz.az-ın ölçüsünə görə"), "modern nöqtə az xəbər verir | səkkiz ulduz nöqtə azın ölçüsünə görə")
        self.assertEqual(said("portal mib.media.gov.az vasitəsilə"), "portal mib nöqtə media nöqtə qov nöqtə az vasitəsilə")
        self.assertEqual(said("S.Orucov küçəsi"), "es orucov küçəsi")
        self.assertEqual(said("ölüb.News24.az xəbər verir"), "ölüb | nyus iyirmi dörd nöqtə az xəbər verir")
        self.assertEqual(said("Şəkil: https://ordu.az/photos/2026/11/1.jpg"), "şəkil")

    def test_weather_and_money(self):
        self.assertEqual(said("Bakıda buludlu hava, +12°…+17°"), "bakıda buludlu hava | on iki-on yeddi dərəcə")
        self.assertEqual(said("Gecə -5°, gündüz 3 °C"), "gecə mənfi beş dərəcə | gündüz üç dərəcə")
        # 2026-11-23: dərəcədən sonrakı söz yapışırdı («dərəcəolacaq»)
        self.assertEqual(said("Gündüz +12°…+17° olacaq, gecə -2° şaxta"), "gündüz on iki-on yeddi dərəcə olacaq | gecə mənfi iki dərəcə şaxta")
        self.assertEqual(said("1 654,23 dollar"), "min altı yüz əlli dörd tam yüzdə iyirmi üç dollar")

    def test_foreign_names(self):
        self.assertEqual(said("Google, WhatsApp və YouTube; Washington-da Trump’ın çıxışı"), "qugl | vatsap və yutub | vaşinqtonda trampın çıxışı")
        self.assertEqual(said("KVAN Group şirkəti"), "kvan qrup şirkəti")

    def test_sentence_is_read_whole_long_one_breathes_at_commas(self):
        # Whisper ölçməsi (2026-11-23): vergüldə bölmək aydınlığı azaldır — qısa cümlə bütöv səslənir.
        out = az_text.phrases("Gündüz Sumqayıtda 21, Gəncədə 16 dərəcə isti olacaq. Sabah yağış yoxdur.")
        self.assertEqual([s for s, _ in out], ["gündüz sumqayıtda iyirmi bir gəncədə on altı dərəcə isti olacaq", "sabah yağış yoxdur"])
        long = ", ".join(["Bakıda və Abşeron yarımadasında hava dəyişkən buludlu olacaq"] * 4) + "."
        parts = az_text.phrases(long)
        self.assertEqual(len(parts), 4)
        self.assertLess(parts[0][1], parts[-1][1])
        self.assertEqual(len(az_text.phrases("Bir, iki, üç.", commas=True)), 3)

    def test_everything_reaches_the_model_alphabet(self):
        text = "ABŞ-ın 2026-cı il «Real Madrid» 2:1, 5,54% artıb (COP31) – XII tur; FHN-in məlumatı: 58 822 dollar!"
        self.assertTrue(all(set(s) <= az_text.ALLOWED for s, _ in az_text.phrases(text)))

    def test_voice_settings_apply_to_model(self):
        class M:
            pass
        m = az_text.tune(M(), speaking_rate=0.9)
        self.assertEqual(m.speaking_rate, 0.9)
        self.assertEqual(m.noise_scale, az_text.VOICE["noise_scale"])


class LexiconTest(unittest.TestCase):
    """Oxunuş lüğəti (ses-lugat.json + budaqdan əlavə): qaydalardan əvvəl gəlir, şəkilçini ahəngə uyğun yapışdırır."""

    def setUp(self):
        self.saved = dict(az_text.LEXICON)
        az_text.LEXICON.clear()
        az_text.LEXICON.update({"Celta": "selta", "Sacramento": "sakramento", "DİN": "de-i-en", "Bloomberg": "blumberq"})

    def tearDown(self):
        az_text.LEXICON.clear()
        az_text.LEXICON.update(self.saved)

    def test_lexicon_words_with_suffix_and_headline_caps(self):
        self.assertEqual(said("«Celta Vigo»nu, Sacramento-nun, BLOOMBERG xəbər verir"), "selta vigonu | sakramentonun | blumberq xəbər verir")
        self.assertEqual(said("DİN-in açıqlaması"), "de-i-enin açıqlaması")

    def test_ordinary_words_are_not_taken_for_acronyms(self):
        self.assertEqual(said("Din və dövlət, din xadimi"), "din və dövlət | din xadimi")

    def test_files_merge_base_over_branch(self):
        d = tempfile.mkdtemp()
        with open(os.path.join(d, "ses-lugat.json"), "w", encoding="utf-8") as f:
            f.write('{"sozler": {"Google": "qugl", "Bad": "B@d"}}')
        with open(os.path.join(d, "ses-lugat-elave.json"), "w", encoding="utf-8") as f:
            f.write('{"sozler": {"Google": "quqıl", "Axios": "aksios"}}')
        self.assertEqual(az_text.load_lexicon(d), 2)
        self.assertEqual(az_text.LEXICON, {"Google": "qugl", "Axios": "aksios"})

    def test_repository_lexicon_is_valid(self):
        with open(SRV / "ses-lugat.json", encoding="utf-8") as f:
            data = __import__("json").load(f)
        for k, v in data["sozler"].items():
            self.assertTrue(v and set(v) <= az_text.ALLOWED, (k, v))


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
