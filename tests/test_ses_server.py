"""«Dinlə» SARA səs serveri (.github/ses-server): mətnin modelə hazırlanması və oxunan mətn (sahib, 2026-11-08: «sara»)."""
import importlib.util
import json
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
        # 2026-11-24: tam tarix ili ilə oxunur («… iki min iyirmi altıncı il tarixində»; əvvəl «iki min iyirmi altı tarixində»)
        self.assertEqual(v("07.11.2026 tarixində"), "yeddi noyabr iki min iyirmi altıncı il tarixində")
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
        # Sahib, 2026-11-27: «V tur — 5-ci tur yerinə v tur deyir videoda». Tək hərfli rum rəqəmi sıra sözündən əvvəl sıra sayıdır;
        # başqa yerdə (Vitamin V, Pyotr I) hərf olaraq qalır.
        self.assertEqual(az_text.for_voice("Avropa Liqasının V turunda, I yer, X əsr, V Respublika"),
                         "Avropa Liqasının beşinci turunda, birinci yer, onuncu əsr, beşinci Respublika")
        self.assertNotIn("beşinci", az_text.for_voice("Vitamin V və Pyotr I"))

    def test_number_suffix_is_attached(self):
        # Sahib, 2026-11-24: ayın günü mənsubiyyətlə — «noyabrın on doqquzunda» («on doqquzda» idi)
        self.assertEqual(said("Noyabrın 19-da, 900-dən çox, 29-na qədər, 10-nun, 22-si, 3-ü, 42-yə, 300-ə, 160-la"),
                         "noyabrın on doqquzunda | doqquz yüzdən çox | iyirmi doqquza qədər | onun | iyirmi ikisi | üçü | qırx ikiyə | üç yüzə | yüz altmışla")
        self.assertEqual(said("saat 18:00-dək, 10:00-da, 21:45-də, 15%-ə, 10-illik"),
                         "saat on səkkizədək | onda | iyirmi bir qırx beşdə | on beş faizə | onillik")
        self.assertEqual(said("3-otaqlı mənzil, 2026-2027-ci tədris ili"), "üç-otaqlı mənzil | iki min iyirmi altı-iki min iyirmi yeddinci tədris ili")

    def test_sites_initials_and_links_do_not_break_sentences(self):
        self.assertEqual(said("Modern.az xəbər verir. 8ulduz.az-ın ölçüsünə görə"), "modern nöqtə az xəbər verir | səkkiz ulduz nöqtə azın ölçüsünə görə")
        self.assertEqual(said("portal mib.media.gov.az vasitəsilə"), "portal mib nöqtə media nöqtə qov nöqtə az vasitəsilə")
        self.assertEqual(said("S.Orucov küçəsi"), "es orucov küçəsi")
        self.assertEqual(said("ölüb.News24.az xəbər verir"), "ölüb | nyus iyirmi dörd nöqtə az xəbər verir")
        self.assertEqual(said("Şəkil: https://ordu.az/photos/2026/11/1.jpg"), "şəkil")
        # Mənbə adları (hər səs «<mənbə> xəbər verir» ilə başlayır, 2026-11-23): «səkkizULDUZ», «Baku.vs» idi
        self.assertEqual(said("8ULDUZ xəbər verir. Bizim.Media və Baku.ws"), "səkkiz ulduz xəbər verir | bizim nöqtə media və baku nöqtə ve-es")

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

    def test_day_of_month_takes_the_possessive(self):
        # Sahib, 2026-11-24: «"noyabrın 25-də" yazısını oxuyanda "noyabrın iyirmibeşdə" oxuyur» — düzgünü «iyirmi beşində»
        v = az_text.verbalize
        for text, want in [
            ("Tədbir noyabrın 25-də keçiriləcək.", "Tədbir noyabrın iyirmi beşində keçiriləcək."),
            ("Noyabrın 25-dən etibarən", "Noyabrın iyirmi beşindən etibarən"),
            ("Qeydiyyat dekabrın 31-dək davam edir", "Qeydiyyat dekabrın otuz birinədək davam edir"),
            ("İyulun 20-si bayramdır", "İyulun iyirmisi bayramdır"),
            ("martın 1-də, aprelin 30-u, mayın 9-u, oktyabrın 2-si", "martın birində, aprelin otuzu, mayın doqquzu, oktyabrın ikisi"),
            ("ayın 15-nə qədər, noyabrın 25-ində, noyabrın 3-ündə, iyunun 6-sı", "ayın on beşinə qədər, noyabrın iyirmi beşində, noyabrın üçündə, iyunun altısı"),
            ("sentyabrın 10-dakı görüş, fevralın 4-nü", "sentyabrın onundakı görüş, fevralın dördünü"),
            ("noyabrın 25-26-da forum", "noyabrın iyirmi beş-iyirmi altısında forum"),
            ("noyabrın 25-ci günü", "noyabrın iyirmi beşinci günü"),          # sıra sayı öz qaydası ilə
            ("saat 15-də, 25-də", "saat on beşdə, iyirmi beşdə"),               # ay yoxdursa adi şəkilçi
        ]:
            self.assertEqual(v(text), want, text)

    def test_full_dates_are_read_with_the_year(self):
        v = az_text.verbalize
        for text, want in [
            ("25 noyabr 2026", "iyirmi beş noyabr iki min iyirmi altıncı il"),
            ("25.11.2026 tarixində", "iyirmi beş noyabr iki min iyirmi altıncı il tarixində"),
            ("25 noyabr 2026-cı il", "iyirmi beş noyabr iki min iyirmi altıncı il"),
            ("25 Noyabr 2026 ildə", "iyirmi beş Noyabr iki min iyirmi altıncı ildə"),
            ("25.11.2026-da imzalanıb.", "iyirmi beş noyabr iki min iyirmi altıncı ildə imzalanıb."),
            ("25 noyabr 2026.", "iyirmi beş noyabr iki min iyirmi altıncı il."),
            ("1990-cı illər, 300 il əvvəl", "min doqquz yüz doxsanıncı illər, üç yüz il əvvəl"),
        ]:
            self.assertEqual(v(text), want, text)

    def test_clock_times_and_ranges(self):
        v = az_text.verbalize
        self.assertEqual(v("14:30-da, 14:05-də, 00:30"), "on dörd otuzda, on dörd sıfır beşdə, sıfır otuz")
        self.assertEqual(v("14:00-dan 18:00-dək"), "on dörddən on səkkizədək")
        self.assertEqual(v("10:00-18:00 işləyir"), "ondan on səkkizədək işləyir")
        self.assertEqual(v("10:00-18:00 arası"), "on ilə on səkkiz arası")
        self.assertEqual(v("09:00-13:00-a qədər"), "doqquzdan on üçə qədər")

    def test_dotted_abbreviations_do_not_end_the_sentence(self):
        v = az_text.verbalize
        self.assertEqual(v("Alma, armud və s. satılır."), "Alma, armud və sairə satılır.")
        self.assertEqual(v("Alma və s. Sonra"), "Alma və sairə. Sonra")
        self.assertEqual(v("kitablar və b."), "kitablar və başqaları.")
        self.assertEqual(v("Bakı ş., Xətai r., Azadlıq pr. 10"), "Bakı şəhəri, Xətai rayonu, Azadlıq prospekti on")
        self.assertEqual(v("prof. Əliyev, Dr. Smith, akad. Məmmədov"), "professor Əliyev, doktor Smith, akademik Məmmədov")
        self.assertEqual(v("5 mln. manat, 2 mlrd. dollar"), "beş milyon manat, iki milyard dollar")
        self.assertEqual([s for s, _ in az_text.phrases("Bakı ş. Nizami r. ərazisində və s. yerlərdə qəza olub.")],
                         ["bakı şəhəri", "nizami rayonu ərazisində və sairə yerlərdə qəza olub"])

    def test_units_money_and_signs(self):
        v = az_text.verbalize
        self.assertEqual(v("$1,5 mlrd, €200 mln, 1 000 000 manat"), "bir tam onda beş milyard dollar, iki yüz milyon avro, bir milyon manat")
        self.assertEqual(v("100 AZN-ə, 50 AZN-dən çox, 3 km-dən"), "yüz manata, əlli manatdan çox, üç kilometrdən")
        self.assertEqual(v("80 m², 120 kv. m, 100 m2 mənzil, 5 ha"), "səksən kvadrat metr, yüz iyirmi kvadrat metr, yüz kvadrat metr mənzil, beş hektar")
        self.assertEqual(v("10 MVt, 20 kVt-lıq, 100 m məsafə, 3 m³"), "on meqavat, iyirmi kilovatlıq, yüz metr məsafə, üç kub metr")
        self.assertEqual(v("Qiymət 15% artıb, 0,5%-ə qədər, %20"), "Qiymət on beş faiz artıb, sıfır tam onda beş faizə qədər, iyirmi faiz")
        self.assertEqual(" ".join(v("№5 məktəb, 3-5 gün, 3,14").split()), "nömrə beş məktəb, üç-beş gün, üç tam yüzdə on dörd")
        self.assertEqual(v("AzTV, ABŞ, AB-nin, NATO-ya, BMT"), "Az te-ve, a-be-şe, a-benin, natoya, be-em-te")
        self.assertEqual(v("10 USD-yə, 5 AZN-ni"), "on dollara, beş manatı")       # yazanın «y»/«n» bitişdiricisi «u-es-de»yə görədir
        self.assertEqual(v("oyun (2:1) bitdi, 0:0, saat 2:05"), "oyun (iki-bir) bitdi, sıfır-sıfır, saat iki sıfır beş")

    def test_parentheses_and_dashes_become_pauses_for_babek(self):
        f = az_text.for_voice
        self.assertEqual(f("Prezident (Azərbaycan) bildirib - əməkdaşlıq davam edəcək."), "Prezident, Azərbaycan, bildirib, əməkdaşlıq davam edəcək.")
        self.assertEqual(f("Bakı – Azərbaycanın paytaxtıdır."), "Bakı, Azərbaycanın paytaxtıdır.")
        self.assertEqual(f("O dedi: «Biz gələcəyik (inşallah).»"), "O dedi: «Biz gələcəyik, inşallah.»")
        self.assertEqual(f("(APA) Xəbər. Necə? Niyə belə oldu?"), "apa, Xəbər. Necə? Niyə belə oldu?")   # sual işarəsi qalır
        self.assertEqual(f("+12° – +17° olacaq, 10 - 15 nəfər."), "on iki on yeddi dərəcə olacaq, on - on beş nəfər.")   # rəqəm aralığı qalır

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
            data = json.load(f)
        for k, v in data["sozler"].items():
            self.assertTrue(v and set(v) <= az_text.ALLOWED, (k, v))


VOICE_FIXTURE = ROOT / "tests" / "fixtures" / "ses-oxunus.json"
VOICE_EXTRA = [
    "ABŞ-nin, ABŞ-da, ABŞ-ın, ABŞ-a, BMT-nin və NATO-ya, MMA, KİV, USGS.", "COVID-19 və COP31, AzTV-də, İctimai TV-nin.",
    "VİDEO: Bakıda QƏZA OLDU - FOTOLAR", "XII turda, II Dünya müharibəsi, XV əsr.", "Saat 19:30-da, 18:00-dək, 10:00-da, 21:45-də.",
    "Noyabrın 19-da, 900-dən çox, 29-na qədər, 10-nun, 22-si, 3-ü, 42-yə, 300-ə, 160-la.", "15%-ə, 10-illik, 3-otaqlı, 2026-2027-ci.",
    "Modern.az xəbər verir. 8ulduz.az-ın ölçüsünə görə portal mib.media.gov.az vasitəsilə.", "S.Orucov küçəsi, ölüb.News24.az xəbər verir.",
    "Şəkil: https://ordu.az/photos/2026/11/1.jpg və www.Report.az", "Bakıda +12°…+17° olacaq, gecə -5°, gündüz 3 °C, 1 654,23 dollar.",
    "Hesab 2-1 oldu, qiymət 15% artdı, 07.11.2026 tarixində, 11-ci tur, dollar 1.70 manat, 2 500 nəfər, $100 və 50 AZN.",
    "Google, WhatsApp və YouTube; Washington-da Trump’ın çıxışı, KVAN Group şirkəti.", "Milli Hidrometeorologiya Xidmətindən bildirilib […] Source",
    "«Napoli»nin prezidenti Aurelio De Laurentis görüşüb. 2026-cı ildə 15% artım! Necə?", "№5 məktəb, Tom & Jerry, 2 km, 5 kq, 3 mln, 7 mlrd.",
    "Din və dövlət, DİN-in açıqlaması, BLOOMBERG xəbər verir.", "Gündüz Sumqayıtda 21, Gəncədə 16 dərəcə isti olacaq.",
    "8ULDUZ xəbər verir. Bizim.Media, Baku.ws, Day.Az, Oxu24.com, 525.az, AzVision.az, Ordubad RİH.",
    "Qiymət 1 000 000 manat, 1.500 nəfər, 12,5 faiz, 0,75 bal, 1234567890123456 nömrəli hesab.", "edib.Gundelik.az xəbər verir.",
    # Sahib, 2026-11-24: ayın günü, tam tarix, saat, ixtisar, ölçü, mötərizə və tire (Python və JavaScript eyni oxumalıdır)
    "Tədbir noyabrın 25-də keçiriləcək. Noyabrın 25-dən etibarən, dekabrın 31-dək, iyulun 20-si, martın 1-də, aprelin 30-u.",
    "Ayın 15-nə qədər, noyabrın 25-ində, noyabrın 3-ündə, iyunun 6-sı, sentyabrın 10-dakı görüş, fevralın 4-nü, mayın 9-u.",
    "Noyabrın 25-26-da forum, noyabrın 25-ci günü, saat 15-də, Yanvarın 1-i, avqustun 12-nin, oktyabrın 7-sinə.",
    "25 noyabr 2026, 25.11.2026 tarixində, 25 noyabr 2026-cı il, 25 Noyabr 2026 ildə, 25.11.2026-da imzalanıb. 25 noyabr 2026.",
    "1990-cı illər, 300 il əvvəl, 1 dekabr 2025 ilin sonu, 3 mart 2026-dan, 9 may 1945 ilk dəfə.",
    "Saat 14:30-da, 14:05-də, 00:30, 14:00-dan 18:00-dək, 10:00-18:00 işləyir, 10:00-18:00 arası, 09:00-13:00-a qədər, 20:00–22:00.",
    "Alma, armud və s. satılır. Alma və s. Sonra kitablar və b. Bakı ş., Xətai r., Azadlıq pr. 10, Mərdəkan qəs. ərazisi.",
    "Bakı ş. Nizami r. ərazisində prof. Əliyev, Dr. Smith, akad. Məmmədov, dos. Quliyev və St. Peterburq.",
    "5 mln. manat, 2 mlrd. dollar, $1,5 mlrd, €200 mln, $5 min, 100 AZN-ə, 50 AZN-dən çox, 3 km-dən, 10 USD-yə.",
    "80 m², 120 kv. m, 100 m2 mənzil, 5 ha, 10 MVt, 20 kVt-lıq, 100 m məsafə, 3 m³, 2 km², 1 m-dən.",
    "Prezident (Azərbaycan) bildirib - əməkdaşlıq davam edəcək. Bakı – Azərbaycanın paytaxtıdır. O dedi: «Biz gələcəyik (inşallah).»",
    "(APA) Xəbər. Necə? Niyə belə oldu? +12° – +17° olacaq, 10 - 15 nəfər, Qarabağ - Neftçi oyunu (2:1) bitdi.",
]


def voice_inputs():
    """az_text.for_voice ilə JavaScript nüsxəsinin (.github/ses-worker/az-text.js) eyni nəticə verdiyi yoxlanılan girişlər:
    dinləmə korpusu, qaydaların testləri, mənbə adları və cədvəllərin (ACRONYMS, FOREIGN, SHORT_WORDS, lüğət) hər sözü."""
    with open(ROOT / "tests" / "fixtures" / "ses-korpus.json", encoding="utf-8") as f:
        items = list(json.load(f)["items"])
    items += VOICE_EXTRA
    items += [f"{az_text.upper_az(k)}-da və {az_text.upper_az(k)}" for k in az_text.ACRONYMS]
    items += [f"{k.capitalize()}-da, {k.upper()}" for k in az_text.FOREIGN]
    items += [az_text.upper_az(w) + " oldu" for w in sorted(az_text.SHORT_WORDS)]
    items += [f"{k}-da və {k}" for k in sorted(az_text.LEXICON)]
    return items


class VoiceTextTest(unittest.TestCase):
    """Saytın «Dinlə» səsi (Babək) Saranın qaydaları ilə oxuyur (sahib, 2026-11-23: «saytda da düzgün oxunsun»): hazır səs
    Python-da (ses.py → for_voice), canlı səs Cloudflare işçisində (az-text.js). İkisi eyni mətni verməlidir."""

    def setUp(self):
        self.saved = dict(az_text.LEXICON)
        d = tempfile.mkdtemp()
        with open(SRV / "ses-lugat.json", encoding="utf-8") as src, open(os.path.join(d, "ses-lugat.json"), "w", encoding="utf-8") as dst:
            dst.write(src.read())
        az_text.load_lexicon(d)   # yalnız repodakı lüğət (budaq əlavəsi testə düşməsin)

    def tearDown(self):
        az_text.LEXICON.clear()
        az_text.LEXICON.update(self.saved)

    def test_voice_text_keeps_punctuation_and_case(self):
        self.assertEqual(az_text.for_voice("ABŞ-da 19-da seçki. Gündüz +17° olacaq!"), "a be şedə on doqquzda seçki. Gündüz on yeddi dərəcə olacaq!")
        self.assertEqual(az_text.for_voice("ABŞ-da seçki", hyphens=True), "a-be-şedə seçki")

    def test_javascript_copy_gives_the_same_text(self):
        cases = [[x, az_text.for_voice(x)] for x in voice_inputs()]
        if os.environ.get("SES_OXUNUS_YENILE"):
            with open(VOICE_FIXTURE, "w", encoding="utf-8") as f:
                json.dump({"izah": "az_text.for_voice girişi → nəticəsi (repodakı lüğətlə). JavaScript nüsxəsi (.github/ses-worker/az-text.js) "
                                   "eyni nəticəni verməlidir (tests/ses-worker.test.cjs). Yeniləmə: SES_OXUNUS_YENILE=1 python3 -m unittest tests.test_ses_server",
                           "hallar": cases}, f, ensure_ascii=False, indent=0)
                f.write("\n")
        with open(VOICE_FIXTURE, encoding="utf-8") as f:
            saved = json.load(f)["hallar"]
        stale = [c for c, s in zip(cases, saved) if c != s] or (["say"] if len(cases) != len(saved) else [])
        self.assertEqual(stale, [], "qayda dəyişib, fikstur köhnədir: SES_OXUNUS_YENILE=1 python3 -m unittest tests.test_ses_server")


class ScriptTest(unittest.TestCase):
    def test_source_then_full_text_without_the_title(self):
        # Sahib, 2026-11-24: «başlıqları oxumasın» — başlıq yalnız mətn də, xülasə də yoxdursa
        self.assertEqual(server.script("Bakıda yağış.", "APA", "Bakıda yağış. Sabah  güclü yağış, şimşək çaxacaq."), "APA xəbər verir. Sabah güclü yağış, şimşək çaxacaq.")
        self.assertEqual(server.script("Başlıq", "APA", "", "<p>Sabah paytaxtda güclü yağış gözlənilir.</p>"), "APA xəbər verir. Sabah paytaxtda güclü yağış gözlənilir.")
        self.assertEqual(server.script("Başlıq", "APA", "", ""), "APA xəbər verir. Başlıq.")

    def test_only_https_public_sources_and_site_referer(self):
        self.assertTrue(server.ALLOWED_REF.match("https://8ulduz.az/#/xeber/1"))
        self.assertFalse(server.ALLOWED_REF.match("https://8ulduz.az.evil.com/"))
        self.assertEqual(server.key_of("https://apa.az/1"), server.key_of("https://apa.az/1"))


if __name__ == "__main__":
    unittest.main()
