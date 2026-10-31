# -*- coding: utf-8 -*-
"""
8ulduz — avtomatik xəbər yeniləyici v6
- RSS mənbələri: aşağıdakı AZ_FEEDS və WORLD_FEEDS siyahılarına baxın
  (sayları skript özü çap edir; şərhlərdə rəqəm saxlamırıq ki, köhnəlməsin)
- Paralel yükləmə (ThreadPoolExecutor), hər mənbə üçün ayrıca xəta tolerantlığı
- Şəkillər: enclosure, media:content, media:thumbnail, təsvirdəki ilk <img>
- Dil ayrımı: az / ru / en / tr
- "Prezident gündəliyi" (Zuğulba Xronikası) əsas bölməsi
- Video nişanı (saytdakı video səhifələrinə keçid üçün)
- Bazar məlumatları (valyuta, neft, qızıl, gümüş, bitcoin) -> data/markets.json
"""
import json, re, pathlib, hashlib, datetime, email.utils, html, sys, os, time, gzip
import urllib.request, urllib.parse, urllib.error
import xml.etree.ElementTree as ET
import content_policy
from reader_content import update_reader
from concurrent.futures import ThreadPoolExecutor, wait


def _write_atomic(path, text, encoding="utf-8"):
    """Fayl ya tam yazılır, ya heç: sürətli və yavaş proses eyni qovluqda işləyir, timeout da yazını yarıda kəsə bilər."""
    path = pathlib.Path(path)
    tmp = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    tmp.write_text(text, encoding=encoding)
    os.replace(tmp, path)

# (ad, url[, kateqoriya ipucu]) — Azərbaycan mənbələri, default dil "az"
# AZƏRTAC, Report və News.az GitHub runner IP-lərindən 403 alır.
# Birbaşa lent alınmayanda Google News RSS (və lazım olanda Telegram önizləməsi) ehtiyatdır.
AZ_FEEDS = [
    ("AZƏRTAC",      "https://azertag.az/rss"),
    ("APA",          "https://apa.az/rss"),
    ("APA Sport",    "https://apasport.az/rss", "İdman"),
    # «?»: sayt əsasən bu mövzudadır, amma hər xəbəri yox (categorize). Burada hava proqnozu, şou-biznes da var.
    ("Sportinfo",    "https://www.sportinfo.az/rss/", "İdman?"),
    ("Qol.az",       "https://www.qol.az/rss/", "İdman"),
    ("Fanat.az",     "https://fanat.az/feed", "İdman"),
    ("Oxu.az",       "https://oxu.az/feed"),
    ("Publika.az",   "https://publika.az/rss/"),
    ("Lent.az",      "https://lent.az/rss"),
    ("Axar.az",      "https://axar.az/rss/"),
    ("Olke.az",      "https://olke.az/rss"),
    ("Yenicag.az",   "https://yenicag.az/feed"),
    ("AzVision.az",  "https://azvision.az/rss.xml"),
    ("Moderator.az", "https://moderator.az/rss"),
    ("Bizim.Media",  "https://bizim.media/rss"),
    ("Reyting.az",   "https://reyting.az/rss.xml"),
    ("News24.az",    "https://news24.az/feed/rss"),
    ("Anews.az",     "https://anews.az/rss"),
    ("Aznews.az",    "https://aznews.az/rss/"),
    ("Zim.az",       "https://zim.az/rss.xml"),
    ("Konkret.az",   "https://konkret.az/rss"),
    ("525.az",       "https://525.az/rss_goster.php", "Mədəniyyət?"),
    ("İki Sahil",    "https://ikisahil.az/rss"),
    ("Femida.az",    "https://femida.az/rss.xml"),
    ("Ordu.az",      "https://ordu.az/rss.xml", "Siyasət?"),
    ("Azpolitika.info", "https://azpolitika.info/rss", "Siyasət?"),
    ("Marja.az",     "https://marja.az/rss.php", "İqtisadiyyat"),
    ("Banco.az",     "https://banco.az/rss.xml", "İqtisadiyyat"),
    ("Media.az",     "https://media.az/rss"),
    ("Report",       "https://report.az/rss"),
    ("Trend",        "https://www.trend.az/rss/"),
    ("Milli.az",     "https://www.milli.az/rss/"),
    ("Qafqazinfo",   "https://www.qafqazinfo.az/rss"),
    ("Modern.az",    "https://modern.az/rss"),
    ("Teleqraf",     "https://teleqraf.az/rss/"),
    ("Day.Az",       "https://news.day.az/rss/"),
    ("Azernews",     "https://www.azernews.az/rss/"),
    ("News.az",      "https://news.az/rss.xml"),
    ("Vesti.az",     "https://vesti.az/rss"),
    ("İnterPress",   "https://interpress.az/feed"),
    ("Kulis.az",     "https://kulis.az/rss"),
    ("Sia.az",       "https://sia.az/az/rss/"),
    ("Haqqin.az",    "https://haqqin.az/rss.xml"),
    ("Metbuat",      "https://metbuat.az/rss.xml"),
    ("Tia.az",       "https://www.tia.az/feed/"),
    ("Günün Səsi",   "https://www.gununsesi.info/feed/"),
    ("Xezerxeber",   "https://xezerxeber.az/rss.xml"),
    ("Trend RU",     "https://ru.trend.az/rss/"),
    ("Minval",       "https://minval.az/feed"),
    ("Bakupost",     "https://www.bakupost.az/rss"),
    ("Banker.az",    "https://banker.az/feed/", "İqtisadiyyat"),
    # Dövlət və iqtidar saytları (Zuğulba xronikası üçün də): RSS-i olmayanlar HTML səhifə ilə oxunur (PAGE_PARSERS),
    # Baku TV Google News sitemap-ı ilə. Caliber.az (yalnız rus/ingilis, Yandex Turbo lenti) və Baku.ws (GitHub-dan 403) yoxdur.
    ("Cross Media",  "https://crossmedia.az/az/all-news"),
    ("Xalq qəzeti",  "https://xalqqazeti.az/az"),
    ("Yeni Azərbaycan", "https://yeniazerbaycan.com/"),
    ("Azərbaycan qəzeti", "https://azerbaijan-news.az/az/feed"),
    ("Baku TV",      "https://baku.tv/sitemap-news-az.xml"),
    # Sosial müdafiə: nazirlik və tabeli qurumlar (lentləri yoxdur, PAGE_PARSERS). sosial.gov.az xarici IP-yə açılmır, TG_FALLBACK.
    ("ƏƏSMN",        "https://sosial.gov.az/az/media/xeberler", "Sosial müdafiə"),
    ("DSMF",         "https://dsmf.gov.az/az/media/xeberler", "Sosial müdafiə"),
    ("DOST Agentliyi", "https://dost.gov.az/news", "Sosial müdafiə"),
    ("Məşğulluq Agentliyi", "https://dma.gov.az/media/xeberler", "Sosial müdafiə"),
    # Bölgələr: rayon və şəhər icra hakimiyyətləri, Naxçıvan televiziyası.
    ("Gəncə ŞİH", "https://ganja-ih.gov.az/news.html", "Bölgələr"),
    ("Ağdaş RİH", "https://agdash-ih.gov.az/news.html", "Bölgələr"),
    ("Beyləqan RİH", "https://beyleqan-ih.gov.az/news.html", "Bölgələr"),
    ("Daşkəsən RİH", "https://dashkesen-ih.gov.az/news.html", "Bölgələr"),
    ("Göygöl RİH", "https://goygol-ih.gov.az/news.html", "Bölgələr"),
    ("İmişli RİH", "https://imishli-ih.gov.az/news.html", "Bölgələr"),
    ("Naftalan ŞİH", "https://naftalan-ih.gov.az/news.html", "Bölgələr"),
    ("Oğuz RİH", "https://oguz-ih.gov.az/news.html", "Bölgələr"),
    ("Qəbələ RİH", "https://qebele-ih.gov.az/news.html", "Bölgələr"),
    ("Xocavənd RİH", "https://xocavend-ih.gov.az/news.html", "Bölgələr"),
    ("Babək RİH", "https://babek-ih.gov.az/xeberler", "Bölgələr"),
    ("Culfa RİH", "https://culfa-ih.gov.az/xeberler", "Bölgələr"),
    ("Ordubad RİH", "https://ordubad-ih.gov.az/xeberler", "Bölgələr"),
    ("Sədərək RİH", "https://sederek-ih.gov.az/xeberler", "Bölgələr"),
    ("Naxçıvan TV",  "https://ntv.az/news", "Bölgələr?"),
    # Özəl saytlar: müxalifət olmadığını sahibi yoxlayıb (2026-10-31). Lenti olmayanlar PAGE_PARSERS ilə oxunur.
    ("Narnews.az",   "https://narnews.az/rss.xml", "Bölgələr?"),
    ("Cenub.az",     "https://cenub.az/rss.xml", "Bölgələr?"),
    ("Gəncəxəbər",   "https://gencexeber.az/butun-xeberler", "Bölgələr?"),
    ("Qarabağ Media", "https://qarabag.media/feed/", "Bölgələr?"),
    ("Yurd.Media",   "https://yurd.media/"),
    ("Region Plus",  "https://regionplus.az/allnews"),
    ("Gündəlik.az",  "https://gundelik.az/rss"),
]
# Xarici mənbələr: (ad, url, dil[, kateqoriya ipucu])
WORLD_FEEDS = [
    ("BBC News",     "https://feeds.bbci.co.uk/news/world/rss.xml",           "en"),
    ("Al Jazeera",   "https://www.aljazeera.com/xml/rss/all.xml",             "en"),
    ("Daily Sabah",  "https://www.dailysabah.com/rss/all",                    "en"),
    ("Euronews",     "https://www.euronews.com/rss",                          "en"),
    ("Hürriyet",     "https://www.hurriyet.com.tr/rss/anasayfa",              "tr"),
    ("Sabah TR",     "https://www.sabah.com.tr/rss/anasayfa.xml",             "tr"),
    ("Habertürk",    "https://www.haberturk.com/rss",                         "tr"),
    ("Milliyet",     "https://www.milliyet.com.tr/rss/rssnew/sondakikarss.xml", "tr"),
    ("CNN Türk",     "https://www.cnnturk.com/feed/rss/all/news",             "tr"),
    ("TRT Haber",    "https://www.trthaber.com/manset_articles.rss",          "tr"),
    ("Yeni Şafak",   "https://www.yenisafak.com/rss",                         "tr"),
    ("AA",           "https://www.aa.com.tr/tr/rss/default?cat=guncel",       "tr"),
    ("TRT Spor",     "https://www.trthaber.com/spor_articles.rss",            "tr", "İdman"),
    ("NTV Spor",     "https://www.ntvspor.net/rss/anasayfa",                  "tr", "İdman"),
    ("TASS",         "https://tass.ru/rss/v2.xml",                            "ru"),
    ("Interfax",     "https://www.interfax.ru/rss",                           "ru"),
    ("Championat",   "https://www.championat.com/rss/news/",                  "ru", "İdman"),
    ("Sport.ru",     "https://www.sport.ru/rssfeeds/news.rss",                "ru", "İdman"),
    ("Match TV",     "https://matchtv.ru/news/rss",                           "ru", "İdman"),
    # İdman bölməsi: komanda, Avroliqa, NBA, Formula 1 və digər idman növləri üzrə (2026-10-31 GitHub-dan sınanıb)
    ("A Spor",       "https://www.aspor.com.tr/rss/anasayfa.xml",             "tr", "İdman"),
    ("Sporx",        "https://www.sporx.com/_xml/rss.php",                    "tr", "İdman"),
    ("Ajansspor",    "https://ajansspor.com/rss",                             "tr", "İdman"),
    ("Hürriyet Spor", "https://www.hurriyet.com.tr/rss/spor",                 "tr", "İdman"),
    ("BBC Futbol",   "https://feeds.bbci.co.uk/sport/football/rss.xml",       "en", "İdman"),
    ("Guardian Futbol", "https://www.theguardian.com/football/rss",           "en", "İdman"),
    ("Motorsport F1", "https://www.motorsport.com/rss/f1/news/",              "en", "İdman"),
    ("The Race",     "https://the-race.com/category/formula-1/feed/",         "en", "İdman"),
    ("F1News",       "https://www.f1news.ru/export/news.xml",                 "ru", "İdman"),
    ("Eurohoops",    "https://www.eurohoops.net/en/feed/",                    "en", "İdman"),
    ("Sportando",    "https://sportando.basketball/en/feed/",                 "en", "İdman"),
    ("TalkBasket",   "https://www.talkbasket.net/feed",                       "en", "İdman"),
    ("BBC Tennis",   "https://feeds.bbci.co.uk/sport/tennis/rss.xml",         "en", "İdman"),
    ("MMA Fighting", "https://www.mmafighting.com/rss/index.xml",             "en", "İdman"),
    ("Chess.com",    "https://www.chess.com/rss/news",                        "en", "İdman"),
]
FEEDS = [(f[0], f[1], "az", f[2] if len(f) > 2 else None) for f in AZ_FEEDS] + \
        [(f[0], f[1], f[2], f[3] if len(f) > 3 else None) for f in WORLD_FEEDS]
FEEDS = [f for f in FEEDS if content_policy.source_registered(f[0]) and not content_policy.is_blocked(f[1])]
WORLD_SOURCES = {f[0] for f in WORLD_FEEDS}

SKIP_URL_PARTS = ["/resmi-ilanlar/", "/lezizz/", "/emlak-ilanlari/"]
STOPWORDS = ["neftçala", "neftchala", "ceyran", "xəzər"]

# --- Prezident bölməsi -------------------------------------------------------
# Güclü göstəricilər: birbaşa Azərbaycan rəhbərliyinə aiddir.
PRESIDENT_STRONG = [
    "ilham əliyev", "mehriban əliyeva", "birinci xanım", "prezident aparatı",
    "azərbaycan prezidenti", "prezident ilham", "azərbaycan respublikasının prezidenti",
    "birinci vitse-prezident", "ali baş komandan",
    "ilham aliyev", "mehriban aliyeva", "president of azerbaijan", "azerbaijani president",
    "president ilham", "first lady of azerbaijan",
    "ильхам алиев", "ильхама алиева", "ильхаму алиеву", "ильхамом алиевым",
    "мехрибан алиев", "президент азербайджана", "президента азербайджана",
    "президентом азербайджана", "первой леди", "первая леди", "первый вице-президент",
    "ilham aliyev'", "azerbaycan cumhurbaşkanı",
    # Birinci xanım: saytlar adı qısaldır və ya ə-siz yazır
    "birinci xanim", "birinci xanımlar", "məhriban əliyeva", "məhriban aliyeva",
    "xanım mehriban", "first vice-president", "first vice president", "lady mehriban",
]
# Zəif göstəricilər: yalnız xarici kontekst olmadıqda sayılır
# "X prezidenti" (məs. "Azercell prezidenti", "FIFA prezidenti") başqasının prezidentidir — sayılmır.
PRESIDENT_WEAK_RX = re.compile(r"(?<!\w)(?:prezident(?!i(?!\w)|inin|liy)|dövlət başçısı|ölkə başçısı)")
PRESIDENT_WEAK_EXTRA = ["sərəncam", "fərman", "təltif"]
# Xarici kontekst: "Braziliyada prezident seçkiləri" kimi xəbərlər Prezident bölməsinə düşməsin
FOREIGN_MARKERS = [
    "abş", "amerika", "braziliya", "bolqarıstan", "rusiya", "türkiyə", "fransa", "almaniya",
    "ukrayna", "gürcüstan", "ermənistan", "iran", "qazaxıstan", "özbəkistan", "qırğızıstan",
    "tacikistan", "türkmənistan", "belarus", "polşa", "serbiya", "rumıniya", "moldova",
    "çin", "hindistan", "pakistan", "misir", "suriya", "israil", "fələstin", "argentina",
    "meksika", "venesuela", "kolumbiya", "cənubi koreya", "koreya", "yaponiya", "italiya",
    "ispaniya", "portuqaliya", "macarıstan", "çexiya", "slovakiya", "avstriya", "finlandiya",
    "litva", "latviya", "estoniya", "əfqanıstan", "iraq", "liviya", "tunis", "əlcəzair",
    "nigeriya", "keniya", "cənubi afrika", "kanada", "avstraliya", "filippin", "indoneziya",
    "bolsonaro", "bolsonaru", "keçmiş prezident", "sabiq prezident", "eks-prezident", "eks prezident", "prezident təqaüd",
    "tramp", "trump", "putin", "ərdoğan", "makron", "zelenski", "paşinyan", "tokayev",
    "mirziyoyev", "lukaşenko", "pezeşkiyan", "si szinpin", "lula", "milei", "bayden",
    "fifa prezidenti", "uefa prezidenti", "federasiyasının prezidenti", "klubun prezidenti",
    "prezidentliyə namizəd", "prezident seçki",
]
# --- Digər bölmələr ------------------------------------------------------------
# Açar sözlər söz başlanğıcına görə uyğunlaşdırılır (məs. "bank" -> "bankı", "banklar"),
# söz ortasında isə tutulmur (məs. "qol" "protokol" içində sayılmır).
IDMAN_WORDS = [
    "futbol", "affa", "milli komanda", "qarabağ fk", "kuboku", "avropa liqası",
    "çempion", "matç", "məşqçi", "qol ", "qolla", "turnir", "cüdo", "neftçi",
    "formula 1", "formula-1", "grand prix", "basketbol", "voleybol", "transfer", "konfrans liqası",
    "fenerbahçe", "galatasaray", "beşiktaş", "trabzonspor", "maç", "sabah fk",
    "şampiyon", "süper lig", "premier league", "champions league", "uefa", "fifa", "zirə", "turan tovuz",
    "idman", "yığma", "medal", "çempionat", "premyer liqa", "derbi", "penalti",
    "azərbaycan kuboku", "olimpiya", "güləş", "boks", "atletika",
    "üzgüçülük", "badminton", "şahmat", "gimnastika", "atıcılıq", "voleybolçu",
    "sumqayıt fk", "tofiq bəhramov", "el klasiko", "real madrid", "barselona", "barcelona",
    "mançester", "manchester", "liverpul", "liverpool", "arsenal", "çelsi", "chelsea", "bavariya",
    "yuventus", "qapıçı", "hücumçu", "müdafiəçi", "futbolçu", "tennis", "tennisçi", "güləşçi",
    "boksçu", "cüdoçu", "döyüşçü ufc", "ufc", "nba", "liqası", "teknik direktör", "futbolcu",
    "golcü", "milli takım", "süper kupa", "basketbolcu",
    "футбол", "матч", "сборн", "чемпионат", "чемпион", "тренер", "гол ", "турнир", "рпл",
    "кхл", "нхл", "хоккей", "теннис", "бокс", "борец", "борьб", "олимпи", "медал",
    "спартак", "цска", "зенит", "локомотив", "динамо", "краснодар", "лига чемпионов",
    "формула-1", "биатлон", "фигурист", "шайб", "нападающ", "вратар", "полузащитник",
    "football", "soccer", "tennis", "olympic", "goalkeeper", "striker", "athlete", "qarşılaşma", "azarkeş",
    "avroliqa", "euroleague", "евролиг", "баскетбол", "нба", "basketball", "qran pri", "qran-pri", "гран-при",
    "шахмат", "satranç", "chess", "tenisçi",
]
CATEGORIES = {
    "Prezident": [],  # xüsusi qayda ilə hesablanır (categorize-ə baxın)
    "İdman": IDMAN_WORDS,
    "Sosial müdafiə": ["sosial müdafiə", "əəsmn", "dsmf", "pensiya", "pensiyaçı", "təqaüdçü", "müavinət", "ünvanlı sosial", "ünvanlı dövlət sosial",
                        "sosial yardım", "sosial sığorta", "sosial paket", "sosial təminat", "əlillik", "əlilliyi", "şəhid ailə", "müharibə əlil",
                        "məşğulluq agentliyi", "dövlət məşğulluq", "özünüməşğulluq", "işsizlik", "işsiz", "əmək yarmarka", "dost mərkəzi", "dost agentliyi",
                        "minimum əmək haqqı", "yaşayış minimumu"],
    "Bölgələr": ["gəncə", "sumqayıt", "mingəçevir", "lənkəran", "şəki", "naxçıvan", "şirvan", "yevlax", "xankəndi", "şuşa",
                 "quba", "qusar", "xaçmaz", "şabran", "siyəzən", "xızı", "abşeron rayonu", "ismayıllı", "ağsu", "şamaxı", "qobustan",
                 "göyçay", "ucar", "zərdab", "kürdəmir", "ağdaş", "hacıqabul", "salyan", "neftçala", "biləsuvar", "saatlı",
                 "sabirabad", "imişli", "beyləqan", "ağcabədi", "bərdə", "tərtər", "ağdam", "füzuli", "cəbrayıl", "zəngilan",
                 "qubadlı", "laçın", "kəlbəcər", "xocalı", "xocavənd", "ağdərə", "goranboy", "göygöl", "naftalan", "samux",
                 "daşkəsən", "gədəbəy", "şəmkir", "tovuz", "qazax", "ağstafa", "balakən", "zaqatala", "qax", "oğuz", "qəbələ",
                 "masallı", "yardımlı", "lerik", "astara", "cəlilabad", "ordubad", "culfa", "şərur", "babək", "sədərək",
                 "kəngərli", "şahbuz", "rayon icra hakimiyyəti", "rayonunda", "rayonunun", "kəndində", "kəndinin", "bölgələr", "regionlar"],
    "Təhsil": ["təhsil", "məktəb", "məktəbli", "şagird", "müəllim", "universitet", "tələbə", "abituriyent", "imtahan",
               "dövlət imtahan mərkəzi", "dim ", "magistr", "bakalavr", "doktorant", "kollec", "lisey", "gimnaziya",
               "dərs ili", "bakı dövlət universiteti", "elm və təhsil nazirliyi", "qəbul imtahan", "buraxılış imtahan",
               "məzun", "diplom", "təhsil proqramı", "dərslik", "olimpiada", "təqaüd proqramı",
               "eğitim", "okul", "öğrenci", "öğretmen", "üniversite", "sınav", "yks", "lgs", "meb ", "ösym",
               "школ", "студент", "учител", "университет", "экзамен", "образован", "егэ", "вуз",
               "school", "student", "university", "teacher", "exam", "education"],
    "Səhiyyə": ["səhiyyə", "xəstəxana", "həkim", "xəstəlik", "tibb ", "tibbi", "klinika", "dərman", "əczaçı", "aptek",
                "virus", "qrip", "epidemiya", "pandemiya", "peyvənd", "vaksin", "cərrah", "cərrahiyyə", "diaqnoz",
                "sağlamlıq", "təbib", "icbari tibbi sığorta", "diabet", "xərçəng", "infarkt", "insult", "ürək-damar",
                "koronavirus", "allergiya", "ambulator", "təcili yardım", "reanimasiya", "pasiyent",
                "sağlık", "hastane", "doktor", "hastalık", "aşı", "ilaç", "kanser", "kalp", "salgın", "ameliyat", "hekim",
                "врач", "здоров", "болезн", "больниц", "лекарств", "вакцин", "эпидем", "онколог", "медицин", "пациент",
                "health", "hospital", "doctor", "vaccine", "disease", "cancer", "clinic", "patient", "medical"],
    "Siyasət": ["leyla əliyeva", "heydər əliyev fondu", "лейла алиева", "фонд гейдара алиева",
                "səfir", "parlament", "milli məclis", "seçki", "səfirlik",
                "nazir", "bəyanat", "zəngəzur", "diplomat", "media və yayım şurası",
                "dışişleri", "seçim", "bakan", "politics", "siyasi", "siyasət",
                "election", "minister", "summit", "məsləhətləşmə",
                "qarabağda", "qarabağın", "qarabağ münaqişəsi", "dəhliz", "sülh müqaviləsi", "məclis",
                "hökumət", "nazirlik", "konstitusiya", "ərdoğan", "erdoğan", "erdogan",
                "deputat", "partiya", "müxalifət", "xarici işlər", "danışıqlar", "sammit",
                "tbmm", "chp", "ak parti", "mhp", "cumhurbaşkan", "milletvekili", "muhalefet",
                "выбор", "госдум", "депутат", "министр", "кремл", "мид ", "переговор", "саммит",
                "посол", "парламент", "партия", "правительств", "дипломат", "санкци", "песков", "лавров",
                "government", "parliament", "diplomat", "sanction", "talks", "ceasefire", "senate", "congress", "party", "partiyası", "cooperation"],
    "İqtisadiyyat": ["neft", "oil", "qiymət", "manat", "dollar", "valyuta", "büdcə",
                     "inflyasiya", "maliyyə", "bank", "vergi", "sahibkar", "ixrac", "idxal",
                     "qaz ", "qazın", "enerji", "faiz", "maaş", "pensiya", "borsa", "dotasiya", "məzənnə",
                     "ekonomi", "merkez bankası", "enflasyon", "economy", "market", "dövlət büdcəsi",
                     "mühasibat", "gömrük", "investisiya", "kredit", "ticarət", "socar", "bp ",
                     "kənd təsərrüfatı", "aqrar", "turizm", "biznes", "şirkət", "istehsal", "dolar",
                     "altın", "akaryakıt", "benzin", "asgari ücret", "kripto", "bitcoin", "ihracat",
                     "milyar tl", "milyon tl", "gelir", "kâr", "ciro", "ihale", "zam ", "emekli", "tcmb", "borsa istanbul", "bist", "hisse", "sanayi", "şirket", "ekonomik",
                     "нефт", "газ ", "газа", "рубл", "доллар", "курс", "банк", "инфляц", "экономик",
                     "бюджет", "налог", "экспорт", "импорт", "инвестиц", "бирж", "цен", "тариф", "ввп",
                     "компани", "бизнес", "торгов",
                     "gdp", "inflation", "tariff", "stocks", "trade", "investment", "prices", "tender", "invest", "million", "billion", "milyon manat", "milyard", "kombi", "depozit"],
    "Mədəniyyət": ["film", "kino", "sərgi", "muzey", "teatr", "musiqi", "konsert", "kitab",
                   "şair", "yazıçı", "əsər", "incəsənət", "festival", "mükafat", "şarkı",
                   "sinema", "kitap", "romanı", "romanın", "sanat", "sergi", "concert", "culture", "albüm", "oyuncu",
                   "aktyor", "aktrisa", "müğənni", "rejissor", "serial", "tamaşa", "xalq artisti",
                   "əməkdar artist", "mədəniyyət", "dizi", "şarkıcı", "sanatçı", "oyuncu",
                   "фильм", "кино", "сериал", "театр", "музе", "выставк", "концерт", "певиц", "певец",
                   "актер", "актрис", "режиссер", "книг", "писател", "фестивал", "музык",
                   "movie", "music", "museum", "actor", "singer", "album", "səhnə", "şeir", "rəssam", "ekranlara", "ədəbiyyat", "opera", "mütəfəkkir", "poeziya"],
    "Cəmiyyət": ["hökm", "yandır", "dava", "драка", "драки", "инцидент", "yol qəzası", "hadisə", "qəza", "yanğın", "hava", "təhsil", "məktəb", "universitet",
                 "tələbə", "məhkəmə", "polis", "xəstəxana", "yağış", "sel", "fəsad",
                 "köçkün", "insident", "kaza", "yangın", "eğitim", "təcili tibbi", "bərk", "duman",
                 "saxlanıl", "öldürü", "yaralan", "həlak", "ölüb", "cinayət", "oğurl", "narkotik",
                 "dələduz", "zəlzələ", "sürücü", "piyada", "avtobus", "metro", "kommunal",
                 "işıq", "su təchizatı", "qaz təchizatı", "sosial", "əhali", "abituriyent", "imtahan",
                 "gözaltı", "tutuklandı", "cinayet", "deprem", "trafik", "öğrenci", "okul", "sınav",
                 "hayatını kaybetti", "can verdi", "yaralandı", "operasyon", "hava durumu",
                 "дтп", "авари", "пожар", "погиб", "пострада", "суд ", "суда", "полиц", "задерж",
                 "школ", "студент", "погод", "землетряс", "мошенни", "убийств", "пропавш",
                 "police", "court", "killed", "crash", "fire", "school", "weather", "earthquake", "bıçaql", "ölü", "öldürdü", "canından oldu", "həbs cəzası", "dolu", "sakin", "aşdı", "aşırdı", "xilas", "cərəyan", "видимость", "дорог"],
    "Həyat": ["sağlıq", "sağlamlıq", "həkim", "xəstəlik", "tibbi", "vitamin", "pəhriz", "psixologiya",
              "sağlık", "beslenme", "diyet", "həyat tərzi", "məsləhət", "profilaktika",
              "qidalanma", "yuxu", "orqanizm", "immunitet", "ürək", "qan təzyiqi", "şəkərli diabet",
              "xərçəng", "arıqla", "gözəllik", "dəri",
              "resept", "yemək", "qəhvə", "çay ", "faydası", "zərəri", "tədqiqat",
              "doktor", "kanser", "kalp", "hastalık", "yemek tarifi", "burç",
              "sağlığı", "sağlıklı", "egzersiz", "uyku", "kilo", "stres", "beyin", "yaşlanma", "ömrü",
              "врач", "здоров", "болезн", "диет", "витамин", "сон ", "ученые", "учёные",
              "исследован", "рецепт",
              "health", "doctor", "diet", "study finds", "scientists", "fiziki məşq", "əhval-ruhiyyə", "tənhalıq"],
    "Texnologiya": ["texnologiya", "texnoloji", "smartfon", "süni intellekt", "kosmos", "kəşf", "ixtira", "startap",
                    "proqram təminatı", "kibertəhlükəsizlik", "haker", "rəqəmsal", "internet",
                    "robot", "peyk", "chatgpt", "openai", "google", "apple", "iphone", "android", "windows", "microsoft",
                    "yapay zeka", "teknoloji", "akıllı telefon", "uygulama", "siber", "uzay", "yazılım",
                    "искусственн", "смартфон", "астроном", "космос", "технолог", "приложени", "хакер", "нейросет", "гаджет",
                    "artificial intelligence", " ai ", "space", "smartphone", "tech", "software", "app ", "cyber", "chip", "nasa", "spacex", "rocket"],
    "Dünya": ["bmt", "nato", "rusiya", "çin", "fransa", "almaniya", "iran", "israil", "ukrayna",
              "dəməşq", "suriya", "livan", "ərəb", "abş", "ingiltərə", "pakistan", "hindistan",
              "qüds", "beynəlxalq", "ermənistan", "gürcüstan", "avropa ittifaqı",
              "tramp", "putin", "zelenski", "netanyahu", "qəzza", "yaponiya", "koreya",
              "dış politika", "world", "middle east", "europe",
              "путин", "трамп", "зеленский", "байден", "макрон", "эрдоган", "сша", "нато", "оон",
              "украин", "всу", "израил", "иран", "китай", "европ", "сирии", "газа", "нетаньяху",
              "abd", "rusya", "ukrayna", "israil", "gazze", "avrupa", "almanya", "çin",
              "ukraine", "gaza", "israel", "russia", "china", "iran", "trump", "nato", "un ", "husi", "moskva", "kiyev", "киев", "paşinyan", "uqanda", "ebola", "türkiyədə", "kyrgyzstan", "freedom house"],
}
# İdman bölməsi gücləndirilib: xallar 2 qat sayılır
BOOST = {"İdman": 2, "Prezident": 3, "Təhsil": 1.5, "Səhiyyə": 1.5, "Bölgələr": 1.5, "Sosial müdafiə": 3}
SLUGS = {"Prezident": "prezident", "Gündəm": "gundem", "Siyasət": "siyaset", "Cəmiyyət": "cemiyyet",
         "İqtisadiyyat": "iqtisadiyyat", "Dünya": "dunya", "İdman": "idman", "Mədəniyyət": "medeniyyet",
         "Həyat": "heyat", "Texnologiya": "tehsil", "Təhsil": "tehsil", "Səhiyyə": "heyat", "Bölgələr": "bolgeler", "Sosial müdafiə": "sosial"}
# Birləşmiş bölmələr (2026-10-31): açar sözlər ayrı qalır, saytda bir başlıqdır. Köhnə ünvanlar yeni bölməyə yönəlir.
SECTION_ALIASES = {"sehiyye": "heyat", "texnologiya": "tehsil"}
DOUBLE = {"iran", "rusiya", "çin", "fransa", "israil", "ukrayna", "abş", "ingiltərə", "almaniya",
          "türkiyə", "ermənistan", "gürcüstan"}
FALLBACK = "Gündəm"
# UPDATER_ROOT: məlumat qovluğu koddan ayrı ola bilər (pipeline.sh son işlək kodu eyni məlumatla işlədir).
ROOT = pathlib.Path(os.environ.get("UPDATER_ROOT") or pathlib.Path(__file__).parent)
OUT_DIR = ROOT / "data"
LATEST_FILE = OUT_DIR / "latest.json"
CACHE_DIR = ROOT / ".cache"  # yalnız runner-də, repoya düşmür
FEED_CACHE = CACHE_DIR / "feeds.json"
SLOW_FEED_CACHE = CACHE_DIR / "feeds-slow.json"
OFFICIAL_CACHE = CACHE_DIR / "official.json"
UNDATED_FILE = CACHE_DIR / "undated.json"
RECENT_FILE = CACHE_DIR / "recent.json"
GNEWS_CACHE = CACHE_DIR / "gnews.json"
GROUPS_FILE = CACHE_DIR / "groups.json"
RELABEL_MARK = CACHE_DIR / "relabeled"
OUT_FILE = OUT_DIR / "news.json"
MARKETS_FILE = OUT_DIR / "markets.json"
SOCIAL_FILE = OUT_DIR / "social.json"
STATUS_FILE = OUT_DIR / "status.json"
SOURCES_FILE = OUT_DIR / "sources.json"
OG_FILE = OUT_DIR / "og.json"
DATES_FILE = OUT_DIR / "dates.json"   # tarixsiz lent elementləri üçün səhifədən oxunan dərc vaxtı
VIDEO_FILE = OUT_DIR / "video.json"
FOOTBALL_FILE = OUT_DIR / "football.json"
SPORTS_FILE = OUT_DIR / "sports.json"
# YouTube RSS, açarsız. Kanal adları lentin öz başlığı ilə yoxlanıb.
YT_NEWS = [
    ("İctimai TV", "https://www.youtube.com/feeds/videos.xml?channel_id=UCDVpJfSc-RCGSCfGE2MFGAg"),
    ("Xezer TV", "https://www.youtube.com/feeds/videos.xml?channel_id=UCUsYwCUHsMQcuEm8cOCAuFQ"),
    ("ARB 24", "https://www.youtube.com/feeds/videos.xml?channel_id=UC44ToFclJwakpqw1Wh6iW-A"),
    ("Report.az", "https://www.youtube.com/feeds/videos.xml?channel_id=UCPSpgPJwGhr5uB0Uui8Lj8g"),
    ("Trend TV", "https://www.youtube.com/feeds/videos.xml?channel_id=UCcgI4-HdktIoAaRLOPgY9qQ"),
]
def site_url(root=None):
    """Saytın əsas ünvanı. Kökdə CNAME faylı varsa (GitHub Pages xüsusi domeni, məs. 8ulduz.az) ona görə,
    yoxsa github.io alt yolu. Bölmə səhifələri, sitemap, robots və feed buna görə yazılır; index.html-dəki
    canonical/og ünvanları əl ilə dəyişdirilir (README: «Domen»)."""
    try:
        name = ((root or ROOT) / "CNAME").read_text(encoding="utf-8").strip().split()[0].strip("/")
        if name:
            return f"https://{name}/"
    except Exception:
        pass
    return "https://8ulduz.github.io/8ulduz/"

SITE = site_url()
FEED_FILE = ROOT / "feed.xml"
SITEMAP_FILE = ROOT / "sitemap.xml"
ROBOTS_FILE = ROOT / "robots.txt"
BAKU = datetime.timezone(datetime.timedelta(hours=4))
AZ_MONTHS = {
    "yanvar": 1, "fevral": 2, "mart": 3, "aprel": 4, "may": 5, "iyun": 6,
    "iyul": 7, "avqust": 8, "sentyabr": 9, "oktyabr": 10, "noyabr": 11, "dekabr": 12,
}
MAX_ITEMS = 1200
MAX_PER_SOURCE = 40   # bir mənbə lenti doldurmasın
MAX_PER_WORLD_SOURCE = 20  # xarici mənbələr Azərbaycan xəbərlərini lentdən sıxışdırıb çıxarmasın
MAX_PER_SPORT_SOURCE = 25
MAX_WORLD = 150            # xarici ümumi mənbələr
MAX_WORLD_SPORT = 200      # xarici idman mənbələri: cəmi 35%, qalan yer Azərbaycan xəbərlərinindir

def source_cap(name):
    if name in content_policy.SPORT_SOURCES:
        return MAX_PER_SPORT_SOURCE
    return MAX_PER_WORLD_SOURCE if name in WORLD_SOURCES else MAX_PER_SOURCE
DATE_LOOKUPS = 30     # tarixsiz lent elementləri üçün bir dövrədə ən çox səhifə sorğusu
TIMEOUT = 10
WORKERS = 16
UA = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36 8ulduz-bot"

def norm_az(s):
    return s.lower().replace("i̇", "i")

def detect_lang(title, desc, default):
    """Dil təyini: kiril→ru, 'ə'→az (türkdə yoxdur), ı/ğ/İ→tr, əks halda mənbə dili.
    Azərbaycan mənbələrində ə-siz qısa başlıqlar türkcə sayılmasın deyə default "az" üstündür."""
    # A translated summary must not label an English headline as Azerbaijani.
    english = set(re.findall(r"[a-z]+", title.lower())) & {"the", "why", "with", "from", "for", "and", "says", "after", "before", "in", "of", "to"}
    if "ə" not in title.lower() and len(english) >= 2:
        return "en"
    blob = title + " " + desc
    if re.search(r"[а-яА-Я]", blob):
        return "ru"
    if "ə" in blob or "Ə" in blob:
        return "az"
    if default == "az":
        # AZ mənbəsində ə-siz, lakin ı/ş/ç/ğ/ö/ü olan mətn azərbaycancadır; təmiz ASCII isə ingiliscə
        if re.search(r"[ıİşŞçÇğĞöÖüÜ]", blob) or not re.search(r"[A-Za-z]{3}", blob):
            return "az"
        # ASCII ilə yazılmış Azərbaycan başlığı: «Tehrandan Avropaya», «Zaqatalada qaz olmayacaq»
        words = re.findall(r"[a-z]+", title.lower())
        endings = sum(1 for w in words if re.search(r"(?:ada|ade|dan|den|aya|eye|acaq|ecek|yib|nin|nun)$", w))
        return "az" if words and endings * 2 >= len(words) else "en"
    if "ı" in blob or "ğ" in blob or "İ" in blob:
        return "tr"
    return default if default else "en"

def fetch(url, timeout=TIMEOUT, data=None, headers=None):
    h = {"User-Agent": UA, "Accept": "application/rss+xml, application/xml, text/xml, text/html, */*"}
    if headers:
        h.update(headers)
    req = urllib.request.Request(url, data=data, headers=h)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read()

def text_of(el, names):
    for n in names:
        node = el.find(n)
        if node is not None and node.text:
            return node.text.strip()
    return ""

MEDIA = "{http://search.yahoo.com/mrss/}"
IMG_RE = re.compile(r"""<img[^>]+src\s*=\s*["']([^"']+)["']""", re.I)
IMG_EXT = re.compile(r"\.(jpe?g|png|webp|gif|avif)(\?|$)", re.I)

# Saytın ümumi paylaşım şəkli (loqo) xəbərin şəkli deyil: azertag social.jpg, «son dakika» lövhəsi və s.
GENERIC_IMG = re.compile(r"azertag\.az/resources/images/|/logo|placeholder|default[-_]?(?:image|img|og)|no[-_]?image|tr_son_dakika|/social\.(?:jpe?g|png)$", re.I)

def _is_generic_img(u):
    return bool(u) and bool(GENERIC_IMG.search(u))

def _abs_img(u, base):
    if not u:
        return None
    u = html.unescape(u.strip())
    if u.startswith("//"):
        u = "https:" + u
    u = urllib.parse.urljoin(base or "", u)
    return u if u.startswith(("http://", "https://")) else None

def image_of(item, link, raw_desc):
    """Elementdən şəkil URL-i: enclosure, media:content, media:thumbnail, ilk <img>."""
    for enc in item.findall("enclosure"):
        t, u = (enc.get("type") or ""), enc.get("url")
        if u and (t.startswith("image") or (not t and IMG_EXT.search(u))) and not _is_generic_img(u):
            return _abs_img(u, link)
    for tag in ("content", "thumbnail"):
        for m in item.iter(MEDIA + tag):
            u, t, med = m.get("url"), (m.get("type") or ""), (m.get("medium") or "")
            if u and (tag == "thumbnail" or med == "image" or t.startswith("image") or IMG_EXT.search(u)) and not _is_generic_img(u):
                return _abs_img(u, link)
    for le in item.findall("{http://www.w3.org/2005/Atom}link"):
        if le.get("rel") == "enclosure" and (le.get("type") or "").startswith("image"):
            return _abs_img(le.get("href"), link)
    blobs = [raw_desc, text_of(item, ["{http://purl.org/rss/1.0/modules/content/}encoded"])]
    for b in blobs:
        for m in IMG_RE.finditer(b or ""):
            if not _is_generic_img(m.group(1)) and not re.search(r"\.(?:gif|svg)(?:\?|$)|1x1|pixel|counter", m.group(1), re.I):
                return _abs_img(m.group(1), link)
    return None

def _local(tag):
    return tag.rsplit("}", 1)[-1]

_SM_NS = "{http://www.sitemaps.org/schemas/sitemap/0.9}"
_NEWS_NS = "{http://www.google.com/schemas/sitemap-news/0.9}"
_IMG_NS = "{http://www.google.com/schemas/sitemap-image/1.1}"

def parse_news_sitemap(root, limit=80):
    """Google News sitemap-ı (baku.tv/sitemap-news-az.xml): <url><loc/><news:news><news:title/><news:publication_date/></news:news>
    <image:image><image:loc/></image:image></url>. Başlıqsız <url> (adi sitemap) buraxılır."""
    items = []
    for url in root.iter(_SM_NS + "url"):
        link = (url.findtext(_SM_NS + "loc") or "").strip()
        title = (url.findtext(f"{_NEWS_NS}news/{_NEWS_NS}title") or "").strip()
        pub = (url.findtext(f"{_NEWS_NS}news/{_NEWS_NS}publication_date") or url.findtext(_SM_NS + "lastmod") or "").strip()
        img = (url.findtext(f"{_IMG_NS}image/{_IMG_NS}loc") or "").strip()
        if not (link and title):
            continue
        items.append({"title": html.unescape(title), "link": link, "description": "", "pubDate": pub,
                      "author": "", "image": _abs_img(img, link) if img else None})
        if len(items) >= limit:
            break
    return items

def parse_feed(xml_bytes):
    items = []
    xml_bytes = xml_bytes.lstrip(b"\xef\xbb\xbf \t\r\n")
    try:
        root = ET.fromstring(xml_bytes)
    except ET.ParseError:
        return parse_feed_lenient(xml_bytes)
    if _local(root.tag) == "urlset":  # Google News sitemap-ı (Baku TV) — RSS-siz saytın lenti
        return parse_news_sitemap(root)
    # RSS 2.0 və RSS 1.0 (RDF) elementləri
    rss_items = list(root.iter("item")) or [e for e in root.iter() if _local(e.tag) == "item"]
    for item in rss_items:
        if item.tag != "item":  # RDF: ad məkanını sadələşdir
            for e in item.iter():
                if e.tag.startswith("{http://purl.org/rss/1.0/}"):
                    e.tag = _local(e.tag)
        title = text_of(item, ["title"])
        link = text_of(item, ["link"])
        if not link:
            le = item.find("{http://www.w3.org/2005/Atom}link")
            if le is not None:
                link = le.get("href", "")
        if not link:
            g = item.find("guid")
            if g is not None and g.text and g.text.strip().startswith("http"):
                link = g.text.strip()
        desc = text_of(item, ["description"])
        pub = text_of(item, ["pubDate", "date", "published", "updated", "{http://purl.org/dc/elements/1.1/}date"])
        author = text_of(item, ["{http://purl.org/dc/elements/1.1/}creator", "author"])
        if title and link:
            items.append({"title": title, "link": link,
                          "description": re.sub(r"<[^>]+>", "", desc)[:400], "pubDate": pub,
                          "author": author, "image": image_of(item, link, desc)})
    ns = {"a": "http://www.w3.org/2005/Atom"}
    for entry in root.findall(".//a:entry", ns):
        title = text_of(entry, ["a:title", "{http://www.w3.org/2005/Atom}title"])
        link = ""
        le = entry.find("a:link", ns)
        if le is not None:
            link = le.get("href", "")
        A = "{http://www.w3.org/2005/Atom}"
        # (əvvəlki versiyada prefiksli adlar ns-siz axtarılırdı və summary/tarix heç vaxt tapılmırdı)
        desc = text_of(entry, [A + "summary", A + "content"])
        content = text_of(entry, [A + "content"])
        pub = text_of(entry, [A + "published", A + "updated"])
        if title and link:
            items.append({"title": title, "link": link,
                          "description": re.sub(r"<[^>]+>", "", desc)[:400], "pubDate": pub,
                          "image": image_of(entry, link, content or desc)})
    return items

def parse_feed_lenient(xml_bytes):
    """Pozuq XML üçün (məs. elan olunmamış prefiks) sadə regex əsaslı ehtiyat oxuyucu."""
    s = xml_bytes.decode("utf-8", "ignore")
    def tag(block, name):
        m = re.search(r"<%s(?:\s[^>]*)?>(.*?)</%s>" % (name, name), block, re.S)
        if not m:
            return ""
        v = m.group(1).strip()
        cd = re.match(r"<!\[CDATA\[(.*?)\]\]>$", v, re.S)
        return (cd.group(1) if cd else html.unescape(v)).strip()
    items = []
    for block in re.findall(r"<item[\s>].*?</item>", s, re.S):
        title, link = tag(block, "title"), tag(block, "link")
        desc = tag(block, "description")
        if title and link:
            m = IMG_RE.search(desc) or re.search(r"""<(?:enclosure|media:content|media:thumbnail)[^>]+url=["']([^"']+)""", block)
            items.append({"title": title, "link": link,
                          "description": re.sub(r"<[^>]+>", "", desc)[:400], "pubDate": tag(block, "pubDate"),
                          "author": tag(block, "dc:creator"), "image": _abs_img(m.group(1), link) if m else None})
    return items

def to_iso(pub):
    iso = _to_iso(pub)
    now = datetime.datetime.now(datetime.timezone.utc)
    try:  # gələcək tarixləri (səhv saat qurşağı) indiki vaxta endir
        if datetime.datetime.fromisoformat(iso) > now + datetime.timedelta(minutes=5):
            return _norm_iso(now)
    except Exception:
        pass
    return iso

def _norm_iso(dt):
    """Bütün publishedAt dəyərləri eyni formada (UTC, saniyə) olsun — sətir kimi sıralama düzgün işləsin.
    Əvvəl +04:00 və +00:00 qarışıq idi, UTC-li xəbərlər 4 saat aşağı düşürdü."""
    return dt.astimezone(datetime.timezone.utc).isoformat(timespec="seconds")

def fix_source_link(link):
    """Reyting.az lenti /haber/x.html yazır, o ünvan 404 verir; xəbərin əsl ünvanı /xeber/x-dir."""
    return re.sub(r"^(https?://(?:www\.)?reyting\.az)/haber/(.+?)\.html$", r"\1/xeber/\2", link or "")


def fixed_source_date(link, now=None):
    """This publisher's RSS stamps every item with request time (+0000 for local time).
    Its own article URL contains a stable creation timestamp; use that fallback instead
    of promoting yesterday's story on every fetch. Do not infer epochs on other sites.
    """
    parsed = urllib.parse.urlparse(link or "")
    if (parsed.hostname or "").lower().removeprefix("www.") != "azerbaijan-news.az":
        return ""
    match = re.search(r"-(\d{10})/\d+/?$", parsed.path)
    if not match:
        return ""
    try:
        dt = datetime.datetime.fromtimestamp(int(match.group(1)), datetime.timezone.utc)
        current = now or datetime.datetime.now(datetime.timezone.utc)
        return _norm_iso(dt) if 2000 <= dt.year and dt <= current + datetime.timedelta(minutes=5) else ""
    except (ValueError, OverflowError, OSError):
        return ""

def _to_iso(pub):
    now = datetime.datetime.now(datetime.timezone.utc)
    if not pub:
        return _norm_iso(now)
    pub = re.sub(r"\s+", " ", pub.strip())
    try:
        dt = email.utils.parsedate_to_datetime(pub)
        if dt is None:
            raise ValueError
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=BAKU)  # zonasız tarix: Azərbaycan lentləri Bakı vaxtı yazır
        return _norm_iso(dt)
    except Exception:
        pass
    try:
        dt = datetime.datetime.fromisoformat(pub.replace("Z", "+00:00"))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=BAKU)
        return _norm_iso(dt)
    except Exception:
        return _norm_iso(now)

_RX = {}
# Bölgələr siyahısındakı yer adları: söz sonu və ya Azərbaycan hal/mənsubiyyət şəkilçisi ilə bitməlidir
# («qazax» Qazaxıstanı, «şəki» şəkili, «şirvan» Şirvanşahları tutmasın).
PLACE_WORDS = {w for w in CATEGORIES["Bölgələr"] if " " not in w and w not in ("rayonunda", "rayonunun", "kəndində", "kəndinin", "bölgələr", "regionlar")}
_PLACE_SUF = r"(?:n?[ıiuü]n|n?[ıiuü]|[dt][aə]n?|y?[aə]|l[ıiuü](?:lar|lər)?)?(?=$|[^\w])"

# Qısa kök başqa sözün içində tutulmasın: «dava» — «davam», «kəşf» — «kəşfiyyat», «dəri» — «dərin», «kilo» — «kilometr», «цен» — «центр».
_WORD_GUARD = {"dava": r"(?!m)", "kəşf": r"(?!iyyat)", "dəri": r"(?!n)", "kilo": r"(?!metr)", "цен": r"(?!тр|ност)",
               "hava": r"(?!limanı|dar|lim|yol)", "sel": r"(?:[iı]n?|ə|də|dən)?(?!\w)", "dolu": r"(?!\w)"}

def _rx(w):
    """Söz başlanğıcına bağlı axtarış (sonu sərbəst: şəkilçilər üçün)."""
    r = _RX.get(w)
    if r is None and w in PLACE_WORDS:
        r = _RX[w] = re.compile(r"(?<!\w)" + re.escape(norm_az(w)) + _PLACE_SUF)
    if r is None:
        # ABŞ sözünü Abşeron kimi yer adları ilə qarışdırma.
        suffix = r"(?=$|[^\w]|[-’'])" if w in ("abş", "abd") else r"(?!et|ет)" if w in ("bank", "банк") else _WORD_GUARD.get(w, "")
        r = _RX[w] = re.compile(r"(?<!\w)" + re.escape(norm_az(w)) + suffix)
    return r

def has_any(blob, words):
    return any(_rx(w).search(blob) for w in words)

# Vəzifə adı təkbaşına Azərbaycan demək deyil: «Özbəkistanın birinci xanımı», «Первая леди Франции».
PRESIDENT_ROLES = {"birinci xanım", "birinci xanim", "birinci xanımlar", "birinci vitse-prezident", "первой леди", "первая леди",
                   "первый вице-президент", "first vice-president", "first vice president"}
_ROLE_FOREIGN = re.compile(r"(?<!\w)(?:" + "|".join(map(re.escape, FOREIGN_MARKERS)) + r")\w*\s+(?:prezidentinin\s+)?(?:birinci xan[ıi]m|birinci vitse-prezident)")
_AZ_CONTEXT = re.compile(r"əliyev|aliyev|алиев|azərbaycan|azerbaycan|azerbaijan|азербайдж")

def president_score(blob, lang):
    hits = [w for w in PRESIDENT_STRONG if _rx(w).search(blob)]
    if hits and all(w in PRESIDENT_ROLES for w in hits):
        if _ROLE_FOREIGN.search(blob) if lang == "az" else not _AZ_CONTEXT.search(blob):
            hits = []
    if hits:
        return 4 + 2 * len(hits)
    if lang != "az" or has_any(blob, FOREIGN_MARKERS):
        return 0
    weak = len(PRESIDENT_WEAK_RX.findall(blob))
    return weak + sum(1 for w in PRESIDENT_WEAK_EXTRA if _rx(w).search(blob)) if weak else 0

def categorize(title, desc, lang="az", hint=None, world=False):
    # A clear title topic takes precedence over incidental location words.
    title_text = norm_az(title)
    if president_score(title_text, lang) < 6:
        if re.search(r"(?<!\w)(?:bürc|qoroskop|гороскоп|burç)", title_text):
            return "Həyat"
        if re.search(r"\b(?:teatr\w*|tamaşa(?:sı(?:nın|na|nı|nda|ndan)?|lar(?:ı|ın|a|da|dan)?)?|premyera\w*|romanı|muzey\w*|mədəniyyətlərarası dialoq)\b", title_text):
            return "Mədəniyyət"
        if re.search(r"dini dözümsüzlük|dini tolerantlıq|media savadlılığı", title_text) and not re.search(r"süni intellekt|kibertəhlükəsizlik|proqram təminatı", title_text):
            return "Cəmiyyət"
    blob = norm_az(title + " " + desc)
    scores, in_title = {}, {}
    for cat, words in CATEGORIES.items():
        if cat == "Prezident":
            # Xronikada xəbər özü rəhbərlik haqqında olmalıdır; xülasədəki
            # tarixi arayış və əlaqəli xəbərlərin mətni bunun üçün kifayət deyil.
            hits = president_score(norm_az(title), lang)
        else:
            hits = 0
            for w in words:
                if _rx(w).search(blob):
                    hits += 2 if (" " in w.strip() or w in DOUBLE) else 1
            # başlıqdakı uyğunluqlar daha vacibdir
            tb = norm_az(title)
            in_title[cat] = sum(1 for w in words if _rx(w).search(tb))
            hits += in_title[cat]
        hits *= BOOST.get(cat, 1)
        scores[cat] = hits
    if any(norm_az(s) in blob for s in STOPWORDS):
        scores["İqtisadiyyat"] = 0
    # «Kiyevin doqquz rayonunda»: yer adı yoxdursa və söhbət başqa ölkədən gedirsə, Bölgələr deyil.
    if scores["Bölgələr"] and (scores["Dünya"] or has_any(blob, FOREIGN_MARKERS)) and not has_any(blob, PLACE_WORDS):
        scores["Bölgələr"] = 0
    # «Finlandiyada işsizlik»: bölmə Azərbaycanın sosial müdafiəsidir (qurumların öz lentləri ipucu ilə gəlir).
    if scores["Sosial müdafiə"] and (scores["Dünya"] or has_any(blob, FOREIGN_MARKERS)) and "azərbaycan" not in blob:
        scores["Sosial müdafiə"] = 0
    if world:
        scores["Bölgələr"] = 0  # Bölgələr yalnız Azərbaycanın bölgələridir; xarici mənbə ora düşmür
        scores["Prezident"] = 0  # Zuğulba yalnız Azərbaycan mənbələrindəndir
    # «Siyasət?»: saytın mövzusu üstünlük verir, amma məcbur etmir. Azpolitika-nın hava proqnozu Siyasət deyil (2026-10-31).
    soft = hint[:-1] if hint and hint.endswith("?") else None
    if soft:
        hint = None
        if scores[soft] > 0:
            scores[soft] += 1
    if hint and scores.get("Prezident", 0) < 6:
        return hint
    best = max(scores, key=lambda cat: (scores[cat], in_title.get(cat, 0)))  # bərabərlikdə başlıqdakı söz üstündür
    if scores[best] <= 0:
        if soft and soft != "İdman":  # idman sözü yoxdursa idman deyil; siyasət saytının adi yazısı isə siyasətdir
            return soft
        return "Dünya" if world else FALLBACK
    # xarici mənbələrdə prezident bölməsi yalnız güclü göstərici ilə
    return best

def is_junk(link):
    return any(p in norm_az(link) for p in SKIP_URL_PARTS)

# Rəhbərlik/ölkə haqqında NEGATİV xəbərlər göstərilmir (redaksiya qərarı)
# Yalnız açıq adlar: «prezident», «rəhbərlik», «алиев» kimi ümumi sözlər xarici dövlət başçıları
# haqqında xəbərləri və rəsmi xronikanı da süzürdü.
# Rəhbərlik və dövlət: açıq adlar, vəzifələr və qurumlar (az/ru/en/tr). Ümumi «prezident» sözü xarici dövlət
# başçılarını da tutduğu üçün tək başına kifayət deyil; «hakimiyyət»/«iqtidar» Azərbaycan mənbələrində demək olar
# həmişə Azərbaycan hakimiyyətidir. Xarici mənbələrdə Azərbaycan dövləti haqqında xəbərlər onsuz da dərc edilmir.
LEADERSHIP = [
    "ilham əliyev", "ilham əliyevin", "ilham əliyevə", "mehriban əliyeva", "birinci xanım", "birinci vitse-prezident",
    "azərbaycan prezidenti", "prezident ilham", "cənab prezident", "dövlət başçısı", "əliyevlər", "əliyev ailəsi", "heydər əliyev",
    "azərbaycan hökuməti", "azərbaycan rəhbərliyi", "azərbaycan hakimiyyəti", "azərbaycan dövləti", "hakimiyyət", "iqtidar",
    "prezident aparatı", "prezident administrasiyası", "milli məclis", "nazirlər kabineti", "yeni azərbaycan partiyası", "yap-",
    "ильхам алиев", "ильхама алиева", "мехрибан алиева", "первой леди", "первый вице-президент", "президент азербайджана",
    "президента азербайджана", "президентом азербайджана", "власти азербайджана", "правительство азербайджана",
    "правительства азербайджана", "алиев", "алиева",
    "ilham aliyev", "mehriban aliyeva", "aliyev", "azerbaijani government", "azerbaijani authorities", "azerbaijan's government",
    "baku authorities", "azerbaycan cumhurbaşkanı", "aliyev yönetimi", "azerbaycan hükümeti", "azerbaycan yönetimi",
]
# Neqativ çağrışım (rəhbərlik/dövlət adı ilə birlikdə). Söz başlanğıcına görə axtarılır.
NEGATIVE = [
    "tənqid", "etiraz", "protest", "korrupsiya", "rüşvət", "yolsuzluq",
    "qalmaqal", "mübahisə", "həbs", "tutuklama", "gözaltı", "qanunsuz",
    "insan haqları", "repressiya", "təzyiq", "itiraz", "boykot", "işgəncə",
    "təqsirləndir", "məhkəmə hökmü", "cinayət", "satınalma qalmaqalı",
    "ittiham", "istefaya çağır", "istefa tələb", "sanksiya", "qınad", "qınam", "pisləd", "pisləy", "skandal", "rüsvay",
    "yalan", "aldad", "dələduz", "oğurl", "talan", "fırıldaq", "saxtakar", "saxta", "özbaşınalıq", "zorakılıq",
    "təhqir", "ələ sal", "karikatura", "nifrət", "qəzəb", "narazılıq", "uğursuz", "iflas", "günahkar", "məsuliyyət daşıyır",
    "diktator", "diktatura", "avtoritar", "monarx", "nepotizm", "oliqarx", "klan", "müxalif", "hakim rejim",
    "критик", "протест", "коррупц", "арест", "задержан", "незаконн", "обвин", "отставк", "санкци", "осудил", "осужда",
    "скандал", "ложь", "лжив", "мошенн", "фальсифик", "диктат", "авторитар", "олигарх", "клан", "непотизм",
    "политзаключ", "репресс", "преследован", "правозащит", "цензур",
    "accus", "resign", "sanction", "condemn", "scandal", "fraud", "rigged", "regime", "dictator", "authoritarian",
    "oligarch", "nepotism", "political prisoner", "repression", "crackdown", "persecut", "human rights", "censorship",
    "jailed", "imprison", "dynasty", "corrupt", "abuse",
    "eleştiri", "protesto", "yolsuzluk", "rüşvet", "eleştirmek", "tutuklandı", "suçla", "yaptırım", "kınad", "dolandır",
    "hile", "diktatör", "otoriter", "oligark", "siyasi tutuklu", "baskı", "zulüm", "sansür",
]
# Müxalif/tənqidi çərçivə: rəhbərlik adı çəkilməsə də dərc edilmir (Azərbaycan siyasi kontekstinin ifadələri,
# müxalif partiya/media adları). Rəsmi mənbələr istisnadır.
OPPOSITION = [
    "əliyev rejimi", "əliyevlər rejimi", "aliyev rejimi", "aliyev regime", "aliyev's regime", "режим алиев", "диктатура алиев",
    "diktator əliyev", "hakim rejim", "avtoritar rejim", "siyasi məhbus", "vicdan məhbusu", "məhbus jurnalist", "jurnalist həbs",
    "repressiya", "saxta seçki", "seçki saxtakarlığı", "seçkilərin saxtalaşdırılması", "siyasi təqib", "siyasi həbs",
    "insan haqları pozuntu", "insan hüquqları pozuntu", "mətbuat azadlığı sıralama", "söz azadlığı pozul",
    "политзаключенн", "политический заключенн", "репрессии в азербайджане", "азербайджанский режим",
    "political prisoner", "crackdown in azerbaijan", "azerbaijan crackdown", "azerbaijani regime", "authoritarian azerbaijan",
    "azerbaijan's authoritarian", "jailed journalist", "human rights in azerbaijan", "azerbaijan human rights",
    "press freedom in azerbaijan", "siyasi tutuklu", "azerbaycan rejimi", "aliyev diktatörlüğü",
    "milli şura", "axcp", "müsavat partiyası", "əli kərimli", "cəmil həsənli", "meydan tv", "abzas media", "toplum tv",
    "azadlıq radiosu", "mikroskop media", "turan informasiya agentliyi", "милли шура", "али керимли", "джамиль гасанли",
]

# Xarici mənbələrin Azərbaycan dövləti və rəhbərliyi haqqında xəbərləri dərc edilmir (redaksiya qərarı): content_policy.py.
foreign_about_azerbaijan = content_policy.foreign_about_azerbaijan

def is_negative_about_leadership(title, desc, source=None):
    """Rəhbərlikdən bəhs edən və neqativ çağrışım daşıyan xəbərləri tutur (redaksiya qərarı).
    Rəsmi mənbələr süzülmür; sözlər söz başlanğıcında axtarılır («qan təzyiqi» tutulmur)."""
    if source in ("Prezident.az", "Mehriban Əliyeva"):
        return False
    blob = norm_az(title + " " + desc)
    if any(_rx(w).search(blob) for w in OPPOSITION):
        return True
    if not any(_rx(w).search(blob) for w in LEADERSHIP):
        return False
    return any(_rx(w).search(blob) for w in NEGATIVE)

def is_video(it):
    if it.get("video"):  # rəsmi səhifədə video bloku
        return True
    l = norm_az(it["link"])
    return "/video/" in l or "video" in norm_az(it["title"])

def label_for(title, summary, lang, hint=None, world=False):
    label = categorize(title, summary, lang, hint, world)
    if label == "Prezident" and lang in ("tr", "en") and not has_any(norm_az(title + " " + summary), PRESIDENT_STRONG):
        label = "Siyasət"
    return label

def _plain(s, title=False):
    """HTML entity və etiketləri təmizlə. Başlığın sonundakı boş tire mənbədən gəlir."""
    cur = s or ""
    for _ in range(3):
        nxt = html.unescape(cur)
        if nxt == cur:
            break
        cur = nxt
    cur = re.sub(r"<[^>]+>", " ", cur).replace("\xa0", " ")
    cur = re.sub(r"\s+", " ", cur).strip()
    if title:
        # Telegram lentlərində başlığın sonuna mənbə ünvanı yapışır
        cur = re.sub(r"\s*https?://\S+", "", cur)
        cur = re.sub(r"(?:\s*[-–—|])+\s*$", "", cur).strip()
    return cur

def display_source(source, link):
    host = (urllib.parse.urlparse(link or "").hostname or "").lower()
    if host.startswith("www."):
        host = host[4:]
    # Sia.az lentinə sesqazeti.az ünvanlı xəbərlər də düşür; keçidin saytı göstərilsin.
    if host == "sesqazeti.az":
        return "Sesqazeti.az"
    return source

SUMMARY_MAX = 220  # kartda 2 sətir görünür; uzun xülasə news.json-u ağırlaşdırırdı (26% həcm)

def _short(desc, n=SUMMARY_MAX):
    if len(desc) <= n:
        return desc
    cut = desc[:n].rsplit(" ", 1)[0]
    return cut + "…"

def make_article(it, source, default_lang, hint=None, force_label=None):
    title = _plain(it["title"], title=True)
    desc = _plain(it["description"])
    lang = detect_lang(title, desc, default_lang)
    # Rəsmi xronika səhifələri birbaşa Prezident bölməsinə gedir (məs. FIFA xəbəri idmana düşməsin)
    if force_label:
        label = force_label
    else:
        label = label_for(title, desc, lang, hint, source in WORLD_SOURCES)
    image = it.get("image") or ""
    if image.endswith("/") or image.rstrip("/").endswith("/resize"):
        image = ""
    return {
        "id": hashlib.sha1(it["link"].encode()).hexdigest()[:16],
        "title": title,
        "summary": _short(desc),
        "category": SLUGS.get(label, "gundem"),
        "source": display_source(source, it["link"]),
        "sourceUrl": it["link"],
        "publishedAt": fixed_source_date(it["link"]) or to_iso(it["pubDate"]),
        "imageUrl": image or None,
        "lang": lang,
        "author": _plain(it.get("author", "")),
        "video": is_video(it),
    }

# Birbaşa RSS 403 olanda eyni redaksiyanın ehtiyat ünvanı. Təsadüfi proksi yoxdur.
DIRECT_ALT = {
    "AZƏRTAC": ["https://www.azertag.az/rss"],
    "Report": ["https://www.report.az/rss"],
    "News.az": ["https://www.news.az/rss.xml"],
}
# Google News `site:` axtarışı məqaləni öz saytına açır (decoder ilə).
# News.az üçün az/AZ lokalı boş qayıdır; en-US/when:2d işlək olan sorğudur.
GNEWS_FALLBACK = {
    "AZƏRTAC": [("https://news.google.com/rss/search?q=site:azertag.az+when:2d&hl=az&gl=AZ&ceid=AZ:az", "azertag.az")],
    "Report": [("https://news.google.com/rss/search?q=site:report.az+when:2d&hl=az&gl=AZ&ceid=AZ:az", "report.az")],
    "News.az": [("https://news.google.com/rss/search?q=site:news.az/news+when:2d&hl=en-US&gl=US&ceid=US:en", "news.az")],
    # xalqqazeti.az GitHub-dan 403 qaytarır (bot qoruması); Telegram kanalında sayt keçidi yoxdur
    "Xalq qəzeti": [("https://news.google.com/rss/search?q=site:xalqqazeti.az+when:2d&hl=az&gl=AZ&ceid=AZ:az", "xalqqazeti.az")],
}
# Rəsmi Telegram veb önizləməsi. Yazıdakı keçid həmin saytadırsa qəbul edilir.
TG_FALLBACK = {
    "AZƏRTAC": ("azertacnews", "azertag.az"),
    "Report": ("reportnewsaz", "report.az"),
    "ƏƏSMN": ("sosialgovaz", "sosial.gov.az"),
    "DOST Agentliyi": ("dostagentliyi", "dost.gov.az"),
}
GNEWS_LIMIT = 12

def _host(url):
    host = (urllib.parse.urlparse(url or "").hostname or "").lower()
    return host[4:] if host.startswith("www.") else host

def _article_on(url, host):
    if _host(url) != host:
        return False
    path = urllib.parse.urlparse(url).path.strip("/")
    if not path or path in {"rss", "feed", "news", "az", "ru", "en", "xeber"}:
        return False
    if "/tag/" in f"/{path}/" or "/page/" in f"/{path}/":
        return False
    return "/" in path or path.rsplit("/", 1)[-1].split("?")[0].replace("-", "").isalnum()

def _blocked(exc):
    if isinstance(exc, urllib.error.HTTPError):
        return exc.code in (401, 403, 429, 503)
    return isinstance(exc, (urllib.error.URLError, TimeoutError))

def _err(exc):
    return f"{type(exc).__name__}: {str(exc)[:80]}"

def _load_direct(url):
    parser = PAGE_PARSERS.get(url)  # RSS-siz saytlar: HTML siyahı səhifəsi oxunur (Cross Media, Xalq qəzeti, Yeni Azərbaycan)
    if parser:
        return parser(fetch(url).decode("utf-8", "replace"))
    return parse_feed(fetch(url))

def _gnews_decode(art_id):
    page = fetch(f"https://news.google.com/rss/articles/{art_id}", timeout=15).decode("utf-8", "replace")
    sig = re.search(r'data-n-a-sg="([^"]+)"', page)
    ts = re.search(r'data-n-a-ts="([^"]+)"', page)
    if not sig or not ts:
        return ""
    sig_s = sig.group(1).replace("\\", "\\\\").replace('"', '\\"')
    inner = (
        '["garturlreq",[["X","X",["X","X"],null,null,1,1,"US:en",null,1,null,null,null,null,null,0,1],'
        f'"X","X",1,[1,1,1],1,1,null,0,0,null,0],"{art_id}",{ts.group(1)},"{sig_s}"]'
    )
    body = urllib.parse.urlencode({"f.req": json.dumps([[["Fbv4je", inner]]])}).encode()
    raw = fetch(
        "https://news.google.com/_/DotsSplashUi/data/batchexecute?rpcids=Fbv4je",
        timeout=15, data=body,
        headers={"Content-Type": "application/x-www-form-urlencoded;charset=UTF-8"},
    ).decode("utf-8", "replace")
    found = re.findall(r"https?://[^\"\\\s]+", raw)
    return found[0].rstrip("]).,;>") if found else ""

def _fresh(pub, days=3):
    if not pub:
        return True
    try:
        dt = email.utils.parsedate_to_datetime(re.sub(r"\s+", " ", pub.strip()))
        if dt is None:
            return True
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=datetime.timezone.utc)
        age = datetime.datetime.now(datetime.timezone.utc) - dt
        return datetime.timedelta(days=-1) <= age <= datetime.timedelta(days=days)
    except Exception:
        return True

def _strip_outlet(title):
    title = re.sub(r"\s+[-–—|]\s+Latest news from Azerbaijan\s*$", "", title or "", flags=re.I)
    return re.sub(r"\s+[-–—|]\s+(?:Report\.az|Azərtac|Azertag|AZERTAC|News\.az|News\.Az)\s*$", "", title, flags=re.I).strip()

_GNEWS_DECODED = {}  # keçid dekodu 2 sorğudur; eyni xəbər hər dövrədə yenidən açılmasın

def gnews_items(rss_url, host, limit=GNEWS_LIMIT):
    parsed = parse_feed(fetch(rss_url, timeout=15))
    todo = []
    for it in parsed:
        link = it.get("link") or ""
        m = re.search(r"/articles/([^?]+)", link)
        if not m:
            continue
        todo.append((m.group(1), it))
        if len(todo) >= limit * 2:
            break
    decoded = {art_id: _GNEWS_DECODED[art_id] for art_id, _ in todo if art_id in _GNEWS_DECODED}
    ids = [art_id for art_id, _ in todo if art_id not in decoded]
    if ids:
        with ThreadPoolExecutor(max_workers=4) as ex:
            for art_id, url in zip(ids, ex.map(_gnews_decode, ids)):
                decoded[art_id] = url
                if url:
                    _GNEWS_DECODED[art_id] = url
    out = []
    seen = set()
    for art_id, it in todo:
        url = decoded.get(art_id) or ""
        if not _article_on(url, host) or url in seen:
            continue
        seen.add(url)
        title = _strip_outlet(it.get("title") or "")
        if len(title) < 20 or not _fresh(it.get("pubDate") or ""):
            continue
        out.append({
            "title": title, "link": url, "description": it.get("description") or "",
            "pubDate": it.get("pubDate") or "", "author": it.get("author") or "",
            "image": it.get("image"),
        })
        if len(out) >= limit:
            break
    return out

def telegram_items(channel, host, pages=3, limit=20):
    """Rəsmi kanalın veb önizləməsi. Son səhifələr, eyni saytın məqalə keçidi olan yazılar."""
    url = f"https://t.me/s/{channel}"
    out, seen, visited = [], set(), set()
    for _ in range(pages):
        if url in visited:
            break
        visited.add(url)
        page = fetch(url, timeout=15).decode("utf-8", "replace")
        for part in re.split(r'class="tgme_widget_message_wrap', page)[1:]:
            link = ""
            for href in re.findall(r'href="(https?://[^"]+)"', part):
                if _article_on(href, host):
                    link = href.split("?")[0]
                    break
            if not link or link in seen:
                continue
            seen.add(link)
            text_m = re.search(r'tgme_widget_message_text[^>]*>(.*?)</div>', part, re.S)
            body = re.split(r"<br\s*/?>", text_m.group(1), maxsplit=1) if text_m else [""]
            # Nazirlik kanalında yazı uzundur: başlıq ilk sətirdir. Qısa sətir tək qalmasın.
            raw = re.sub(r"<[^>]+>", " ", body[0] if len(re.sub(r"<[^>]+>", "", body[0]).strip()) >= 25 else (text_m.group(1) if text_m else ""))
            title = re.sub(r"\s+", " ", html.unescape(raw)).strip()
            title = re.sub(r"\s*Ətraflı\s*:.*$", "", title, flags=re.I).strip()
            title = re.sub(r"^[^\wƏəİıÖöÜüĞğŞşÇç]+", "", title).strip()
            if len(title) < 12:
                continue
            when = re.search(r'datetime="([^"]+)"', part)
            out.append({
                "title": title, "link": link, "description": "",
                "pubDate": when.group(1) if when else "", "author": "", "image": None,
            })
            if len(out) >= limit:
                return out
        more = re.search(rf'href="(/s/{re.escape(channel)}\?before=\d+)"[^>]*tme_messages_more', page)
        if not more:
            more = re.search(rf'tme_messages_more[^>]*href="(/s/{re.escape(channel)}\?before=\d+)"', page)
        if not more:
            break
        url = "https://t.me" + more.group(1)
    return out

def fetch_feed(feed):
    """(mənbə, elementlər, xəta, istifadə olunan url). Xəta qalırsa mənbə uğursuz sayılır."""
    source, url = feed[0], feed[1]
    errors = []
    for candidate in [url] + DIRECT_ALT.get(source, []):
        try:
            items = _load_direct(candidate)
        except Exception as e:
            errors.append(_err(e))
            if not _blocked(e):
                return source, [], errors[-1], url
            continue
        if items:
            return source, items, None, candidate
        errors.append("birbaşa lent boşdur")
    # Google News bu saytları çox vaxt rus/ingilis versiya ilə verir.
    # Rəsmi Telegram kanalı azərbaycan dilindəki məqalə keçidini saxlayır, ona görə əvvəl gəlir.
    order = ("telegram", "google") if source in TG_FALLBACK else ("google",)
    for step in order:
        if step == "google":
            for rss_url, host in GNEWS_FALLBACK.get(source) or []:
                try:
                    items = gnews_items(rss_url, host)
                    if items:
                        return source, items, None, rss_url
                    errors.append("Google News boş qayıtdı")
                except Exception as e:
                    errors.append("Google News: " + _err(e))
        else:
            channel, host = TG_FALLBACK[source]
            try:
                items = telegram_items(channel, host)
                if items:
                    return source, items, None, f"https://t.me/s/{channel}"
                errors.append("Telegram boş qayıtdı")
            except Exception as e:
                errors.append("Telegram: " + _err(e))
    return source, [], "; ".join(errors)[:180], url

# ------------------------------------------------------------ sürətli dövrə ---
# QIRMIZI XƏTT 1 (docs/qirmizi-xetler.md): dövrə 60 saniyəyə sığmalıdır. Vaxtında cavab verməyən lent dövrəni
# gözlətmir: sonuncu nəticəsi işlədilir, yavaş proses (--slow) onu ayrıca təzələyir.
FAST_BUDGET_S = 20       # bütün lentlər üçün ümumi vaxt
FAST_WORKERS = 40
FAST_FETCH_TIMEOUT = 8
FEED_FAILS_BEFORE_PAUSE = 3   # ardıcıl bu qədər alınmayan lent dövrəni saxlamasın (Femida.az hər dəqiqə 18 saniyə aparırdı)
FEED_RETRY_S = 300       # dayandırılan lent bu qədərdən bir yoxlanır, arada onu yavaş proses oxuyur
FEED_PAUSE_MAX_SHARE = 0.2    # lentlərin bu qədərindən çoxu birdən alınmırsa problem bizim şəbəkədir: heç nə dayandırılmır
FEED_KEEP = 120          # lentdən yalnız ən yeni elementlər (İki Sahil 2000 element verir)
FAST_MAX_ITEMS = 1000    # qruplaşdırma açdığı yer köhnə xəbərlə dolmasın, news.json böyüməsin
FALLBACK_EVERY_S = 180   # Google News və Telegram ehtiyatını dəqiqədə bir yormayaq
STALE_FEED_S = 900       # bundan köhnə nəticə «mənbə işləmir» sayılır
LATEST_WINDOW_S = 1800   # latest.json main-dəki news.json-un gecikməsini örtməlidir
LATEST_TOP = 40
LATEST_MAX = 200


def _read_json(path, default):
    try:
        return json.loads(pathlib.Path(path).read_text(encoding="utf-8"))
    except Exception:
        return default


def _save_cache(path, value):
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    _write_atomic(path, json.dumps(value, ensure_ascii=False, separators=(",", ":")))


def _fetch_conditional(url, entry):
    """Lent dəyişməyibsa (304) None. entry-yə ETag və Last-Modified yazılır: sayt da, dövrə də az yüklənir."""
    headers = {"User-Agent": UA, "Accept": "application/rss+xml, application/xml, text/xml, text/html, */*", "Accept-Encoding": "gzip"}
    if entry.get("etag"):
        headers["If-None-Match"] = entry["etag"]
    if entry.get("modified"):
        headers["If-Modified-Since"] = entry["modified"]
    try:
        with urllib.request.urlopen(urllib.request.Request(url, headers=headers), timeout=FAST_FETCH_TIMEOUT) as r:
            raw = r.read()
            if (r.headers.get("Content-Encoding") or "").lower() == "gzip":
                raw = gzip.decompress(raw)
            entry["etag"], entry["modified"] = r.headers.get("ETag") or "", r.headers.get("Last-Modified") or ""
    except urllib.error.HTTPError as e:
        if e.code == 304:
            return None
        raise
    parser = PAGE_PARSERS.get(url)
    return parser(raw.decode("utf-8", "replace")) if parser else parse_feed(raw)


def fetch_feed_fast(feed, old=None):
    """Bir lentin təzə nəticəsi: {items, url, at, err, etag, modified}."""
    source, url = feed[0], feed[1]
    old, started = old or {}, time.time()
    if source in SLOW_ONLY_FEEDS:
        return {"items": [], "url": url, "at": 0, **old, "err": None}
    if started - old.get("pausedAt", 0) < FEED_RETRY_S:
        return {**old, "late": True}
    used = old.get("url") or url
    if used not in [url] + DIRECT_ALT.get(source, []):  # bu mənbə Google News və ya Telegram ilə gəlir
        if old.get("items") and started - old.get("at", 0) < FALLBACK_EVERY_S:
            return {**old, "err": None}
    else:
        entry = {"etag": old.get("etag"), "modified": old.get("modified")}
        try:
            items = _fetch_conditional(used, entry)
            if items is None and old.get("items"):
                return {**old, "at": started, "err": None, "fails": 0, "pausedAt": 0}
            if items:
                return {**entry, "items": items[:FEED_KEEP], "url": used, "at": started, "err": None}
        except Exception:
            pass
    _, items, err, final = fetch_feed(feed)
    fails = old.get("fails", 0) + 1 if err else 0
    paused = started if fails >= FEED_FAILS_BEFORE_PAUSE else 0
    if err and old.get("items"):
        return {**old, "err": err, "fails": fails, "pausedAt": paused}
    return {"items": items[:FEED_KEEP], "url": final or url, "at": started, "err": err, "fails": fails, "pausedAt": paused}


# Dövlət saytları xarici şəbəkəyə gah açılır, gah 12 saniyə susur (2026-10-31 ölçülüb). Rayon xəbəri dəqiqə gözləyə bilər,
# xəbər axını isə onları gözləməməlidir: bu lentlər yalnız yavaş dövrədə oxunur, sürətli dövrə onların son nəticəsini götürür.
# Narnews, Cenub, Region Plus və Qarabağ Media gündə bir neçə dəfədən az yazır: dəqiqəlik oxumağa dəyməz, risk də olmasın.
SLOW_ONLY_FEEDS = {f[0] for f in AZ_FEEDS if ".gov.az/" in f[1]} | {"Narnews.az", "Cenub.az", "Region Plus", "Qarabağ Media"}

LATE_FEEDS = set()  # bu dövrədə cavab verməyən, köhnə nəticəsi işlədilən lentlər: statusda uğurlu sayılmır

def collect_fast():
    """(results, official items, official errors). Heç bir lent dövrəni FAST_BUDGET_S-dən çox saxlamır."""
    cache = _read_json(FEED_CACHE, {})
    for name, entry in _read_json(SLOW_FEED_CACHE, {}).items():
        if entry.get("at", 0) > (cache.get(name) or {}).get("at", 0):
            cache[name] = entry
    _GNEWS_DECODED.update(_read_json(GNEWS_CACHE, {}))
    pool = ThreadPoolExecutor(max_workers=FAST_WORKERS)
    futures = [(feed, pool.submit(fetch_feed_fast, feed, cache.get(feed[0]))) for feed in FEEDS]
    official = pool.submit(official_items)
    wait([future for _, future in futures] + [official], timeout=FAST_BUDGET_S)
    pool.shutdown(wait=False, cancel_futures=True)
    now, results = time.time(), []
    LATE_FEEDS.clear()
    for feed, future in futures:
        old = cache.get(feed[0]) or {}
        if future.done() and not future.cancelled() and future.exception() is None:
            entry = dict(future.result())
            if entry.pop("late", False):
                LATE_FEEDS.add(feed[0])
        else:
            usable = old.get("items") and now - old.get("at", 0) < STALE_FEED_S
            fails = old.get("fails", 0) + 1
            entry = {**old, "err": None if usable else "vaxt bitdi", "fails": fails, "pausedAt": now if fails >= FEED_FAILS_BEFORE_PAUSE else 0}
            LATE_FEEDS.add(feed[0])
        cache[feed[0]] = entry
    # Hamısı birdən alınmırsa səbəb bizdədir (DNS, şəbəkə): növbəti dövrə hamısını yenidən oxumalıdır.
    paused = [name for name, entry in cache.items() if now - entry.get("pausedAt", 0) < FEED_RETRY_S]
    if len(paused) > len(FEEDS) * FEED_PAUSE_MAX_SHARE:
        print(f"  ! {len(paused)} lent birdən cavab vermir: dayandırılmır", flush=True)
        for name in paused:
            cache[name] = {**cache[name], "pausedAt": 0, "fails": 0}
    for feed, _ in futures:
        entry = cache[feed[0]]
        results.append((feed[0], entry.get("items") or [], entry.get("err"), entry.get("url") or feed[1]))
    saved = _read_json(OFFICIAL_CACHE, [])
    if official.done() and not official.cancelled() and official.exception() is None:
        off_items, off_errors = official.result()
        if off_items and not off_errors:
            _save_cache(OFFICIAL_CACHE, off_items)
    else:
        off_items, off_errors = saved, []
    _save_cache(FEED_CACHE, cache)
    _save_cache(GNEWS_CACHE, dict(list(_GNEWS_DECODED.items())[-2000:]))
    return results, off_items, off_errors


def compute_groups():
    """Eyni hadisənin qruplaşdırılması ağırdır (bütün cütlər): yavaş prosesdə hesablanır, sürətli dövrə nəticəni tətbiq edir."""
    articles = _read_json(OUT_FILE, {}).get("articles") or []
    if articles:
        grouped = group_duplicates([dict(a, alts=list(a.get("alts") or [])) for a in articles])
        _save_cache(GROUPS_FILE, {a["sourceUrl"]: a["alts"] for a in grouped if a.get("alts")})


def apply_groups(articles):
    """Yavaş prosesin qruplarını lentə tətbiq edir. Yeni xəbərlər növbəti hesablamaya qədər ayrı qalır, brauzer onları da birləşdirir."""
    # Qrup faylı dəyişiklikdən əvvəl yazılıb ola bilər: köhnə keçid buradan lentə qayıtmasın.
    groups = {fix_source_link(url): [{**alt, "sourceUrl": fix_source_link(alt.get("sourceUrl"))} for alt in alts] for url, alts in _read_json(GROUPS_FILE, {}).items()}
    present = {a.get("sourceUrl") for a in articles}
    absorbed = {alt.get("sourceUrl") for url, alts in groups.items() if url in present for alt in alts}
    out = []
    for a in articles:
        url = a.get("sourceUrl")
        if url in absorbed and url not in groups:
            continue
        # Yavaş prosesin nəticəsi köhnəni əvəz edir: birləşmə sonradan səhv çıxsa kartda qalmasın.
        # Qrup faylı hələ yoxdursa (işin ilk dəqiqəsi) xəbərin öz siyahısı qalır.
        if groups:
            alts = [alt for alt in groups.get(url, []) if alt.get("sourceUrl") != url]
            a = {**a, "alts": alts} if alts else {k: v for k, v in a.items() if k != "alts"}
        out.append(a)
    return out


BULK_MIN_ITEMS, BULK_SPAN_S = 50, 1800

def bulk_dated(items):
    """Lentin tarixi yazının tarixi deyil: 50+ elementin 80%-i yarım saata sığır (Marja.az 2016-cı il xəbərlərini təzə tarixlə verir)."""
    if len(items) < BULK_MIN_ITEMS:
        return False
    times = []
    for it in items:
        try:
            # Keçiddə sabit tarix varsa lentin tarixi işlənmir (Azərbaycan qəzeti): belə lent problemli deyil.
            fixed = fixed_source_date(it.get("link"))
            dt = _parse_dt(fixed) if fixed else email.utils.parsedate_to_datetime(re.sub(r"\s+", " ", (it.get("pubDate") or "").strip()))
            times.append(dt.timestamp())
        except Exception:
            continue
    keep = int(len(items) * 0.8)
    if len(times) < keep:
        return False
    times.sort()
    return min(times[i + keep - 1] - times[i] for i in range(len(times) - keep + 1)) <= BULK_SPAN_S


def _older_than(pub, floor):
    """Lent elementi lentdəki ən köhnə xəbərdən də köhnədirsə True. Tarix oxunmursa False."""
    try:
        dt = email.utils.parsedate_to_datetime(re.sub(r"\s+", " ", (pub or "").strip()))
        return (dt if dt.tzinfo else dt.replace(tzinfo=datetime.timezone.utc)) < floor
    except Exception:
        return False


def apply_og_cache(articles):
    """Sürətli dövrə şəkil sorğusu göndərmir; yavaş prosesin tapdığı şəkillər işlədilir."""
    cache = _read_json(OG_FILE, {})
    for a in articles:
        image = cache.get(a.get("sourceUrl") or "") if isinstance(cache, dict) else None
        if not a.get("imageUrl") and isinstance(image, str) and image and not _is_generic_img(image):
            a["imageUrl"] = image


def write_latest(articles, previous):
    """latest.json: son yarım saatda lentə düşənlər və ən yeni xəbərlər. Sayt onu tam lentin üstünə qoyur."""
    now, known = time.time(), {a.get("sourceUrl") for a in previous}
    recent = {u: t for u, t in _read_json(RECENT_FILE, {}).items() if now - t < LATEST_WINDOW_S}
    for a in articles:
        if a.get("sourceUrl") not in known:
            recent.setdefault(a.get("sourceUrl"), now)
    ordered = sorted(articles, key=lambda a: a.get("publishedAt") or "", reverse=True)
    top = {a.get("sourceUrl") for a in ordered[:LATEST_TOP]}
    rows = [a for a in ordered if a.get("sourceUrl") in top or a.get("sourceUrl") in recent][:LATEST_MAX]
    stamp = datetime.datetime.now(datetime.timezone.utc).isoformat()
    OUT_DIR.mkdir(exist_ok=True)
    _write_atomic(LATEST_FILE, json.dumps({"updatedAt": stamp, "count": len(rows), "articles": rows}, ensure_ascii=False, separators=(",", ":")))
    _save_cache(RECENT_FILE, recent)


def refresh_slow_feeds(limit_s=150):
    """Sürətli dövrəyə sığmayan lentlər burada, daha çox vaxtla oxunur."""
    cache, now = _read_json(FEED_CACHE, {}), time.time()
    todo = [feed for feed in FEEDS if now - (cache.get(feed[0]) or {}).get("at", 0) > 120]
    if not todo:
        return
    pool = ThreadPoolExecutor(max_workers=16)
    futures = [(feed, pool.submit(fetch_feed, feed)) for feed in todo]
    wait([future for _, future in futures], timeout=limit_s)
    pool.shutdown(wait=False, cancel_futures=True)
    fresh = {}
    for feed, future in futures:
        if future.done() and not future.cancelled() and future.exception() is None:
            _, items, err, used = future.result()
            if items and not err:
                fresh[feed[0]] = {"items": items[:FEED_KEEP], "url": used or feed[1], "at": now, "err": None}
    _save_cache(SLOW_FEED_CACHE, fresh)


def resolve_undated():
    """Tarixsiz lent elementləri: səhifə tarixi yavaş prosesdə tapılır, sürətli dövrə dates.json-dan oxuyur."""
    dates, lookups = load_dates(), DATE_LOOKUPS
    for it in _read_json(UNDATED_FILE, []):
        if lookups <= 0:
            break
        _, lookups = undated_date(it, dates, lookups)
    save_dates(dates)


# Bölmə arxivi: lent gündüz 2-3 saat əhatə edir, bölmə səhifəsi isə günlərlə xəbər göstərməlidir.
# Saatda bir yazılır: main-in tarixçəsi şişməsin. Lentdən çıxan xəbər ən azı 2 saat lentdə olduğu üçün heç nə itmir.
ARCHIVE_DIR = OUT_DIR / "arxiv"
ARCHIVE_DAYS, ARCHIVE_MAX, ARCHIVE_EVERY_S = 5, 200, 3600
ARCHIVE_MAX_BY_SECTION = {"idman": 800, "bolgeler": 600}  # komanda və rayon düyməsi bu siyahıdan süzür: az yazılana da xəbər qalsın
BACKLOG_SECTIONS = {"bolgeler", "sosial"}
ARCHIVE_FIELDS = ("id", "title", "summary", "source", "sourceUrl", "publishedAt", "category", "lang", "imageUrl", "video")

def feed_backlog(cutoff):
    """Lent 3-4 saat əhatə edir: rayon və qurum xəbəri çox vaxt ondan köhnədir, lentdən keçmədiyi üçün arxivə də düşmürdü.
    Azərbaycan lentlərinin Bölgələr və Sosial müdafiə xəbərləri arxivə birbaşa gəlir, süzgəclər lentdəki ilə eynidir."""
    cache = _read_json(FEED_CACHE, {})
    for name, entry in _read_json(SLOW_FEED_CACHE, {}).items():
        if entry.get("at", 0) > (cache.get(name) or {}).get("at", 0):
            cache[name] = entry
    az, rows = {f[0] for f in AZ_FEEDS}, []
    for source, _url, dlang, hint in FEEDS:
        items = (cache.get(source) or {}).get("items") or []
        if source not in az or bulk_dated(items):
            continue
        for it in items:
            try:
                if not it.get("pubDate") or _older_than(it["pubDate"], cutoff) or is_junk(it["link"]):
                    continue
                if is_negative_about_leadership(it["title"], it["description"], source):
                    continue
                art = make_article(it, source, dlang, hint)
                if art["category"] in BACKLOG_SECTIONS and not foreign_about_azerbaijan(source, art["category"], art["title"], it.get("description") or art["summary"]):
                    rows.append(art)
            except Exception:
                continue
    return rows

def update_archive(now=None):
    now = now or time.time()
    articles = _read_json(OUT_FILE, {}).get("articles") or []
    missing = any(not (ARCHIVE_DIR / f"{s[0]}.json").exists() for s in SECTIONS if s[0] != "prezident")  # yeni bölmə bir saat boş qalmasın
    if not articles or (not missing and now - _read_json(ARCHIVE_DIR / "gundem.json", {}).get("at", 0) < ARCHIVE_EVERY_S):
        return
    cutoff = datetime.datetime.fromtimestamp(now - ARCHIVE_DAYS * 86400, datetime.timezone.utc)
    merged = {alt.get("sourceUrl") for a in articles for alt in a.get("alts") or []}
    backlog = feed_backlog(cutoff)
    for slug, _label, _desc in SECTIONS:
        if slug == "prezident":  # Zuğulba lentdə 60 gün qalır
            continue
        path, rows = ARCHIVE_DIR / f"{slug}.json", {}
        aliases = [ARCHIVE_DIR / f"{old}.json" for old, new in SECTION_ALIASES.items() if new == slug]
        saved = [row for p in [path, *aliases] for row in _read_json(p, {}).get("articles") or []]
        names = {slug, *(old for old, new in SECTION_ALIASES.items() if new == slug)}
        for a in [*saved, *(a for a in backlog if a["category"] in names), *(a for a in articles if a.get("category") in names)]:
            url = fix_source_link(a.get("sourceUrl"))
            if url and url not in merged:
                rows[url] = {**{k: a[k] for k in ARCHIVE_FIELDS if a.get(k)}, "sourceUrl": url, "category": slug}
        # Tarixi oxunmayan xəbər arxivdə qalmır.
        kept = [a for a in rows.values() if (_parse_dt(a.get("publishedAt")) or cutoff - datetime.timedelta(1)) >= cutoff
                and not is_junk(a.get("sourceUrl", "")) and not removed_source(a)
                and not is_negative_about_leadership(a.get("title", ""), a.get("summary", ""), a.get("source"))]
        kept, _ = content_policy.enforce(kept)
        kept.sort(key=lambda a: a.get("publishedAt") or "", reverse=True)
        ARCHIVE_DIR.mkdir(parents=True, exist_ok=True)
        _write_atomic(path, json.dumps({"at": now, "articles": kept[:ARCHIVE_MAX_BY_SECTION.get(slug, ARCHIVE_MAX)]}, ensure_ascii=False, separators=(",", ":")))
        for old in aliases:  # köhnə fayl boşalır: növbəti dəfə eyni xəbər yenidən köçürülməsin
            if old.exists():
                _write_atomic(old, json.dumps({"at": now, "articles": []}, separators=(",", ":")))


# Səsli oxu söndürülüb, reader.json-u işlədən yoxdur: 400 xəbərin tam mətni açıq yayımlanmasın (müəllif hüququ).
# Sürücü rejimi qayıdanda (config.js, driver) True yazılır.
READER_ENABLED = False

def retire_reader():
    if READER_ENABLED:
        update_reader(_read_json(OUT_FILE, {}).get("articles") or [], OUT_DIR / "reader.json", lambda url: fetch(url, timeout=6))
    else:
        (OUT_DIR / "reader.json").unlink(missing_ok=True)


def slow_cycle():
    """Xəbər axınını gözlətməməli olan hər şey. Hər addım müstəqildir: biri düşsə digərləri işləyir."""
    articles = _read_json(OUT_FILE, {}).get("articles") or []
    steps = [compute_groups, update_markets, resolve_undated, update_social, update_video, update_football, update_sports,
             lambda: fill_og_images(articles), retire_reader, refresh_slow_feeds, write_public, update_archive]
    for step in steps:
        try:
            step()
        except Exception as e:
            print("  ! yavaş addım:", getattr(step, "__name__", "?"), type(e).__name__, e)
    return 0

# ---------------------------------------------------------------- bazarlar ---
MARKET_DEFS = [
    # id, ad (UI), vahid, onluq
    ("USD", "Dollar", "AZN", 4), ("EUR", "Avro", "AZN", 4), ("RUB100", "100 Rubl", "AZN", 4),
    ("TRY100", "100 Lirə", "AZN", 4), ("BRENT", "Brent", "USD", 2), ("WTI", "Neft (WTI)", "USD", 2),
    ("XAU", "Qızıl", "USD", 1), ("XAG", "Gümüş", "USD", 2), ("BTC", "Bitcoin", "USD", 0),
]

def fetch_json(url, timeout=TIMEOUT):
    return json.loads(fetch(url, timeout).decode("utf-8"))

# AMB GitHub Actions-dan alınmayanda səbəb markets.json-a yazılır (cbarError) — loglara girişsiz görmək üçün.
CBAR_HOSTS = ("https://www.cbar.az", "https://cbar.az")
_cbar_errors = []

def cbar_rates(day):
    """AMB (CBAR) rəsmi məzənnələri: {kod: AZN qiyməti bir vahid üçün}. İki host sınanır."""
    xml, last = None, None
    for host in CBAR_HOSTS:
        try:
            xml = fetch(f"{host}/currencies/{day:%d.%m.%Y}.xml", timeout=15,
                        headers={"Accept": "application/xml,text/xml;q=0.9,*/*;q=0.8", "Accept-Language": "az,en;q=0.8"})
            break
        except Exception as e:
            last = e
            _cbar_errors.append(f"{day:%d.%m} {host.split('//')[1]}: {type(e).__name__}: {str(e)[:120]}")
    if xml is None:
        raise last or RuntimeError("cbar: cavab yoxdur")
    root = ET.fromstring(xml)
    out = {}
    for v in root.iter("Valute"):
        code = v.get("Code")
        try:
            nom = float(re.match(r"\s*([\d.]+)", v.findtext("Nominal") or "1").group(1))
            out[code] = float(v.findtext("Value")) / (nom or 1)
        except Exception:
            continue
    return out

def get_currencies():
    baku = datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=4))).date()
    cur, prev = None, None
    failed = 0  # ardıcıl alınmayan günlər; şəbəkə bağlıdırsa 6 günü gözləməyək
    for back in range(0, 6):
        d = baku - datetime.timedelta(days=back)
        try:
            r = cbar_rates(d)
        except Exception:
            r = None
        if not r or not r.get("USD"):
            failed += 1
            if failed >= 2 and cur is None:
                break
            continue  # bülleten hələ yoxdur və ya şəbəkə xətası: növbəti günə bax
        failed = 0
        if cur is None:
            cur = (d, r)
        elif r != cur[1]:
            prev = (d, r); break
    res = {}
    if cur:
        r, p = cur[1], (prev[1] if prev else {})
        for mid, code, mult in (("USD", "USD", 1), ("EUR", "EUR", 1), ("RUB100", "RUB", 100), ("TRY100", "TRY", 100)):
            if code in r:
                res[mid] = {"value": r[code] * mult, "prev": p[code] * mult if code in p else None,
                            "src": "AMB", "asOf": cur[0].isoformat()}
        return res
    # Ehtiyat: open.er-api.com (açarsız, gündəlik)
    g = fetch_json("https://open.er-api.com/v6/latest/USD")
    azn = g["rates"]["AZN"]
    for mid, code, mult in (("USD", "USD", 1), ("EUR", "EUR", 1), ("RUB100", "RUB", 100), ("TRY100", "TRY", 100)):
        if code in g["rates"]:
            res[mid] = {"value": azn / g["rates"][code] * mult, "prev": None, "src": "ExchangeRate-API"}
    return res

def get_commodities():
    res = {}
    syms = {"BZ=F": "BRENT", "CL=F": "WTI", "GC=F": "XAU", "SI=F": "XAG", "BTC-USD": "BTC"}
    try:
        q = urllib.parse.quote(",".join(syms))
        d = fetch_json(f"https://query1.finance.yahoo.com/v7/finance/spark?symbols={q}&range=1d&interval=1d")
        for r in d["spark"]["result"]:
            m = r["response"][0]["meta"]
            mid = syms.get(r["symbol"])
            if mid and m.get("regularMarketPrice"):
                res[mid] = {"value": m["regularMarketPrice"], "prev": m.get("previousClose") or m.get("chartPreviousClose"),
                            "src": "Yahoo Finance"}
    except Exception as e:
        print("  ! yahoo:", type(e).__name__)
    if "BRENT" not in res or "WTI" not in res:
        try:
            u = ("https://quote.cnbc.com/quote-html-webservice/restQuote/symbolType/symbol?symbols=%40LCO.1%7C%40CL.1"
                 "&requestMethod=itv&noform=1&partnerId=2&fund=1&exthrs=1&output=json&events=1")
            for q in fetch_json(u)["FormattedQuoteResult"]["FormattedQuote"]:
                mid = {"@LCO.1": "BRENT", "@CL.1": "WTI"}.get(q.get("symbol"))
                if mid and mid not in res:
                    num = lambda s: float(str(s).replace(",", "")) if s not in (None, "", "UNCH") else None
                    res[mid] = {"value": num(q.get("last")), "prev": num(q.get("previous_day_closing")), "src": "CNBC"}
        except Exception as e:
            print("  ! cnbc:", type(e).__name__)
    # Qızıl/gümüş: spot qiymət (sayt əvvəl də bunu göstərirdi)
    for mid in ("XAU", "XAG"):
        try:
            p = fetch_json(f"https://api.gold-api.com/price/{mid}")["price"]
            res[mid] = {"value": p, "prev": (res.get(mid) or {}).get("prev"), "src": "gold-api.com"}
        except Exception:
            pass
    if "BTC" not in res:
        try:
            g = fetch_json("https://api.coingecko.com/api/v3/simple/price?ids=bitcoin&vs_currencies=usd&include_24hr_change=true")["bitcoin"]
            res["BTC"] = {"value": g["usd"], "prev": g["usd"] / (1 + g["usd_24h_change"] / 100), "src": "CoinGecko"}
        except Exception:
            pass
    return res

def update_markets():
    try:
        old = {i["id"]: i for i in json.loads(MARKETS_FILE.read_text(encoding="utf-8"))["items"]}
    except Exception:
        old = {}
    got = {}
    for fn in (get_currencies, get_commodities):
        try:
            got.update(fn())
        except Exception as e:
            print(f"  ! {fn.__name__}: {type(e).__name__}")
    now = datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds")
    items = []
    for mid, label, unit, dec in MARKET_DEFS:
        g = got.get(mid)
        if g and g.get("value"):
            v, p = float(g["value"]), g.get("prev")
            it = {"id": mid, "label": label, "unit": unit, "dec": dec, "value": round(v, dec + 2),
                  "change": round(v - p, dec + 2) if p else None,
                  "changePct": round((v - p) / p * 100, 2) if p else None,
                  "src": g.get("src"), "at": now}
            if g.get("asOf"):
                it["asOf"] = g["asOf"]
        elif mid in old:
            it = dict(old[mid], stale=True)  # son məlum qiymət
        else:
            continue
        items.append(it)
    strip = lambda its: [{k: v for k, v in i.items() if k not in ("at", "stale")} for i in its]
    amb_missing = any(i.get("unit") == "AZN" and i.get("src") != "AMB" for i in items)
    cbar_error = "; ".join(_cbar_errors[-4:]) if amb_missing and _cbar_errors else ""
    if cbar_error:
        print("  ! AMB:", cbar_error)
    try:
        old_err = json.loads(MARKETS_FILE.read_text(encoding="utf-8")).get("cbarError", "")
    except Exception:
        old_err = ""
    if items and strip(items) == strip(old.values()) and len(items) == len(old) and old_err == cbar_error:
        print("Bazar: dəyişiklik yoxdur"); return
    if items:
        out = {"updatedAt": now, "items": items}
        if cbar_error:
            out["cbarError"] = cbar_error
        _write_atomic(MARKETS_FILE, json.dumps(out, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    print(f"Bazar: {sum(1 for i in items if not i.get('stale'))}/{len(MARKET_DEFS)} təzə")

def _clean_text(s):
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", s or ""))).strip()

def parse_az_date(s):
    """'24.10.2026' və '24 oktyabr 2026, 19:15' — Bakı vaxtı."""
    raw = _clean_text(s).lower()
    hm = re.search(r"(\d{1,2}):(\d{2})", raw)
    now_baku = datetime.datetime.now(BAKU)
    hour, minute = (int(hm.group(1)), int(hm.group(2))) if hm else (12, 0)
    m = re.search(r"(\d{1,2})[.](\d{1,2})[.](\d{4})", raw)
    if not m:
        w = re.search(r"(\d{1,2})\s+([a-zəöüğışç]+)\s+(\d{4})", raw)
        if w and w.group(2) in AZ_MONTHS:
            m = (int(w.group(1)), AZ_MONTHS[w.group(2)], int(w.group(3)))
        else:
            return _norm_iso(now_baku)
    else:
        m = (int(m.group(1)), int(m.group(2)), int(m.group(3)))
    if not hm and (m[2], m[1], m[0]) == (now_baku.year, now_baku.month, now_baku.day):
        hour, minute = now_baku.hour, now_baku.minute  # bu günün saatsız yazısı gələcəyə düşməsin
    return _norm_iso(datetime.datetime(m[2], m[1], m[0], hour, minute, tzinfo=BAKU))

def fetch_text(url, tries=3, timeout=20):
    last = None
    for _ in range(tries):
        try:
            return fetch(url, timeout=timeout).decode("utf-8", "replace")
        except Exception as e:
            last = e
    raise last

def parse_president_page(page):
    """president.az/az/news siyahısı. Üç blok növü var:
    news-photo (label-title), news-video (news-video_label, YouTube iframe), news-text (news-text_body > span + p).
    Əvvəl yalnız news-photo oxunurdu; çıxışlar (video) və mətbuat xidməti məlumatları (mətn) itirdi."""
    out = []
    for m in re.finditer(r'<article class="([^"]*)">(.*?)</article>', page, re.S):
        cls, block = m.group(1), m.group(2)
        href = re.search(r'<a[^>]+class="news-(?:photo|video|text)_(?:body|label)"[^>]*href="([^"]+)"', block) \
            or re.search(r'href="([^"]+)"', block)
        title = re.search(r'class="label-title">(.*?)</span>', block, re.S)
        if not title:
            title = re.search(r'class="news-video_label"[^>]*>(.*?)<span', block, re.S)
        if not title:
            title = re.search(r'class="news-text_body"[^>]*>\s*<span>(.*?)</span>', block, re.S)
        date = re.search(r'class="category_date">(.*?)</span>', block, re.S)
        t = _clean_text(title.group(1)) if title else ""
        if not (href and t):
            continue
        link = urllib.parse.urljoin("https://president.az", href.group(1))
        img = re.search(r'<img[^>]+src="([^"]+)"', block)
        image = _abs_img(img.group(1), link) if img else None
        yt = re.search(r'youtube\.com/embed/([A-Za-z0-9_-]{6,})', block)
        if not image and yt:
            image = f"https://i.ytimg.com/vi/{yt.group(1)}/hqdefault.jpg"
        desc = re.search(r'<p>(.*?)</p>', block, re.S)
        description = _clean_text(desc.group(1)) if desc else "Azərbaycan Prezidentinin rəsmi səhifəsindən."
        out.append({
            "title": t, "link": link, "description": description,
            "pubDate": parse_az_date(date.group(1) if date else ""),
            "image": image, "author": "", "video": "news-video" in cls,
        })
    return out

AZERTAG_REGIONS = "https://azertag.az/bolme/regionlar"
_AZR_ITEM = re.compile(r'sa-post mid-post(.*?)</h2>', re.S)

def parse_azertag_regions(html):
    """azertag.az/bolme/regionlar: «REGİONLAR» blokundakı kartlar (keçid, başlıq, tarix «28.10.2026 [14:19]», şəkil)."""
    start = html.find("REGİONLAR")
    body = html[start:] if start >= 0 else html
    items = []
    for chunk in _AZR_ITEM.findall(body):
        href = re.search(r'href="(/xeber/[^"]+)"', chunk)
        title = re.search(r"alt='([^']+)'", chunk) or re.search(r'alt="([^"]+)"', chunk)
        if not title:
            title = re.search(r'class="entry-title">\s*<a[^>]*>(.*?)</a>', chunk, re.S)
        date = re.search(r"(\d{2})\.(\d{2})\.(\d{4}) \[(\d{2}):(\d{2})\]", chunk)
        img = re.search(r"data-src='([^']+)'", chunk) or re.search(r'data-src="([^"]+)"', chunk)
        if not (href and title and date):
            continue
        d, m, y, hh, mm = (int(x) for x in date.groups())
        link = "https://azertag.az" + href.group(1)
        items.append({"title": _clean_text(title.group(1)), "link": link, "description": "",
                      "pubDate": datetime.datetime(y, m, d, hh, mm, tzinfo=BAKU).isoformat(timespec="seconds"),
                      "image": _abs_img(img.group(1), link) if img else None, "author": ""})
    return items

# ---- Dövlət və iqtidar saytları (RSS-siz): ana səhifə / siyahı səhifəsi oxunur, Zuğulba xronikası üçün şəkilli ----
def _hm_dmy(s):
    """«10:38 29.10.2026» (Bakı vaxtı) → ISO; tapılmasa ""."""
    m = re.search(r"(\d{1,2}):(\d{2})\s+(\d{2})\.(\d{2})\.(\d{4})", s or "")
    if not m:
        return ""
    hh, mm, d, mo, y = (int(x) for x in m.groups())
    try:
        return datetime.datetime(y, mo, d, hh, mm, tzinfo=BAKU).isoformat(timespec="seconds")
    except ValueError:
        return ""

CROSSMEDIA_URL = "https://crossmedia.az/az/all-news"
XALQQAZETI_URL = "https://xalqqazeti.az/az"
YENIAZERBAYCAN_URL = "https://yeniazerbaycan.com/"

def parse_crossmedia(page):
    """crossmedia.az/az/all-news: <div class="category-card"> kartları — şəkil, keçid /az/article/N, <h3> başlıq, «10:38 29.10.2026».
    Saytın RSS-i yoxdur (/rss, /feed HTML qaytarır); sitemap-news.xml 5000 yazılıqdır və saatsızdır."""
    items, seen = [], set()
    for chunk in page.split('class="category-card"')[1:]:
        href = re.search(r'href="(https?://crossmedia\.az/az/article/\d+)"', chunk)
        title = re.search(r"<h3>(.*?)</h3>", chunk, re.S)
        date = re.search(r'class="date">.*?<span>([^<]+)</span>', chunk, re.S)
        img = re.search(r'<img[^>]+src="([^"]+)"', chunk)
        if not (href and title):
            continue
        link, t = href.group(1), _clean_text(title.group(1))
        if not t or link in seen:
            continue
        seen.add(link)
        items.append({"title": t, "link": link, "description": "", "pubDate": _hm_dmy(date.group(1) if date else ""),
                      "image": _abs_img(img.group(1), link) if img else None, "author": ""})
    return items

def parse_xalqqazeti(page):
    """xalqqazeti.az ana səhifəsi: «rt-post-grid» kartları — şəkil, keçid /az/bölmə/ID-slug, post-title, «14:13 27.10.2026».
    /rss və /az/feed ana səhifəyə yönləndirir."""
    items, seen = [], set()
    for chunk in page.split("rt-post-grid")[1:]:
        href = re.search(r'href="(/az/[\w-]+/\d+-[^"]*)"', chunk)
        title = re.search(r'class="post-title">\s*<a[^>]*>(.*?)</a>', chunk, re.S) or re.search(r'<img[^>]+alt="([^"]+)"', chunk)
        img = re.search(r'<img[^>]+src="([^"]+)"', chunk)
        if not (href and title):
            continue
        link, t = "https://xalqqazeti.az" + href.group(1), _clean_text(title.group(1))
        if not t or link in seen:
            continue
        seen.add(link)
        items.append({"title": t, "link": link, "description": "", "pubDate": _hm_dmy(chunk),
                      "image": _abs_img(img.group(1), link) if img else None, "author": ""})
    return items

def parse_yeniazerbaycan(page):
    """yeniazerbaycan.com ana səhifəsi: «news-post image-post» blokları — şəkil, <h2><a> başlıq-keçid.
    Siyahıda saat yoxdur; vaxt şəkil adındakı möhürdən götürülür (…/20261029103456-…jpg = 29.10.2026 10:34:56 Bakı).
    Möhür yoxdursa tarix boş qalır və updater səhifə/ilk görülmə qaydası ilə doldurur."""
    items, seen = [], set()
    for chunk in page.split("news-post image-post")[1:]:
        href = re.search(r'<h2[^>]*>\s*<a\s[^>]*?href="(https?://yeniazerbaycan\.com/az/[^"]+)"[^>]*>(.*?)</a>', chunk, re.S)  # <a ... href> arasında sətir keçidi var
        img = re.search(r'<img[^>]+src="([^"]+)"', chunk)
        if not href:
            continue
        link, t = href.group(1), _clean_text(href.group(2))
        link = re.sub(r"^(https?://yeniazerbaycan\.com/az/)([^/]+)/", lambda m: m.group(1) + m.group(2).lower() + "/", link)  # /az/Gundem/ = /az/gundem/
        if not t or link in seen:
            continue
        seen.add(link)
        pub = ""
        stamp = re.search(r"/(\d{4})(\d{2})(\d{2})(\d{2})(\d{2})(\d{2})-", img.group(1) if img else "")
        if stamp:
            y, mo, d, hh, mm, ss = (int(x) for x in stamp.groups())
            try:
                pub = datetime.datetime(y, mo, d, hh, mm, ss, tzinfo=BAKU).isoformat(timespec="seconds")
            except ValueError:
                pub = ""
        items.append({"title": t, "link": link, "description": "", "pubDate": pub,
                      "image": _abs_img(img.group(1), link) if img else None, "author": ""})
    return items

_LIST_DATE = re.compile(r"(?:\d{1,2}:\d{2}\s+)?\d{1,2}[.]\d{1,2}[.]20\d{2}|\d{1,2}\s+[a-zəöüğışçA-ZƏÖÜĞİŞÇ]+\s+20\d{2}(?:,?\s+\d{1,2}:\d{2})?"
                        r"|[a-zəöüğışçA-ZƏÖÜĞİŞÇ]+\s+\d{1,2},\s+20\d{2}(?:\s+\d{1,2}:\d{2})?")

def _list_date(raw):
    """«Oktyabr 31, 2026 11:00» (sosial.gov.az) parse_az_date-in bildiyi sıraya çevrilir."""
    iso = re.fullmatch(r"(20\d{2})-(\d{2})-(\d{2})[T ](\d{2}:\d{2}).*", raw.strip())
    if iso:
        return parse_az_date(f"{iso.group(3)}.{iso.group(2)}.{iso.group(1)} {iso.group(4)}")
    swapped = re.fullmatch(r"([^\d\s]+)\s+(\d{1,2}),\s+(20\d{2})(.*)", raw.strip())
    text = f"{swapped.group(2)} {swapped.group(1)} {swapped.group(3)}{swapped.group(4)}" if swapped else raw
    return parse_az_date(text.lower())
_LIST_ANCHOR = re.compile(r'<a\b([^>]*?)href=["\']([^"\']+)["\']([^>]*)>(.*?)</a>', re.S)

def parse_list_page(page, base, link_rx, limit=20):
    """Lenti olmayan rəsmi saytın xəbər siyahısı: keçid, başlıq və ona ən yaxın tarix.
    Eyni xəbərə bir neçə keçid olur (şəkil, başlıq, «Ətraflı»): ən uzun başlıq götürülür."""
    found = {}
    for m in _LIST_ANCHOR.finditer(page):
        link = urllib.parse.urljoin(base, html.unescape(m.group(2)))
        if not re.search(link_rx, link):
            continue
        attrs, inner = m.group(1) + m.group(3), m.group(4)
        named = re.search(r'title=["\']([^"\']+)', attrs) or re.search(r'alt=["\']([^"\']+)', inner)
        title = _clean_text(inner)
        if _LIST_DATE.fullmatch(title):  # tarix də həmin xəbərə keçiddir
            title = ""
        if len(title) < 15:
            title = _clean_text(named.group(1)) if named else ""
        if len(title) < 15:  # «Ətraflı» düyməsi: başlıq yuxarıdakı blokdadır
            heads = re.findall(r"<h\d[^>]*>(.*?)</h\d>", page[max(0, m.start() - 900):m.start()], re.S)
            title = _clean_text(heads[-1]) if heads else ""
        slug_date = re.search(r"(\d{1,2})-(\d{1,2})-(20\d{2})(?:\.html)?$", link)
        near = [d for d in _LIST_DATE.finditer(page, max(0, m.start() - 500), m.end() + 500)]
        near.sort(key=lambda d: min(abs(d.start() - m.start()), abs(d.start() - m.end())))
        raw = f"{slug_date.group(1)}.{slug_date.group(2)}.{slug_date.group(3)}" if slug_date else (near[0].group(0) if near else "")
        row = found.get(link)
        if row and raw and not row["pubDate"]:  # eyni xəbərin vitrindəki keçidində tarix yox idi
            row["pubDate"] = _list_date(raw)
        if len(title) < 15 or (row and len(row["title"]) >= len(title)):
            continue
        imgs = list(re.finditer(r'<img[^>]+src=["\']([^"\']+)', page[max(0, m.start() - 500):m.end()]))
        found[link] = {"title": title, "link": link, "description": "", "pubDate": (row or {}).get("pubDate") or (_list_date(raw) if raw else ""),
                       "image": _abs_img(imgs[-1].group(1), link) if imgs else None, "author": ""}
    return list(found.values())[:limit]

def parse_cards(page, base, start, link_rx, title_rx, date_rx, limit=40):
    """Özəl saytların xəbər kartları: səhifə kartlara bölünür ki, qonşu kartın tarixi və şəkli qarışmasın.
    Kartdakı yer adı (Yurd.Media: «Gəncə») təsvirə yazılır: başlıqda ad olmasa da rayon düyməsi xəbəri tapır."""
    found = {}
    for card in re.split(start, page)[1:]:
        link, title = re.search(link_rx, card), re.search(title_rx, card, re.S)
        text = _clean_text(title.group(1)) if title else ""
        if not link or len(text) < 15:
            continue
        link = urllib.parse.urljoin(base, html.unescape(link.group(1)))
        if link in found:
            continue
        date, img = re.search(date_rx, card), re.search(r'<img[^>]+src=["\']([^"\']+)', card)
        label = re.search(r'class="news__region">(.*?)</', card, re.S)
        place = _clean_text(label.group(1)) if label else ""
        found[link] = {"title": text, "link": link, "pubDate": _list_date(date.group(1)) if date else "", "author": "",
                       "description": place if any(_rx(w).search(norm_az(place)) for w in PLACE_WORDS) else "",
                       "image": _abs_img(img.group(1), base) if img else None}
    return list(found.values())[:limit]

_CARD_DATE = r"(\d{2}[.]\d{2}[.]20\d{2} \d{2}:\d{2})"
_CARD_SITES = {
    "https://gencexeber.az/butun-xeberler": (r'(?=<div class="post__item" data-date=)', r'href="([^"]+/butun-xeberler/[^"]+)"', r'itemprop="headline">(.*?)</span>', r'data-date="([^"]+)"'),
    "https://yurd.media/": (r'(?=<a href="[^"]+" class="news__item)', r'href="([^"]+)"', r'class="news__title">(.*?)</div>', _CARD_DATE),
    "https://regionplus.az/allnews": (r'(?=<div class="nn_item[ "])', r'href="(/posts/view/\d+)"', r'class="article_title">\s*<a[^>]+>(.*?)</a>', _CARD_DATE),
}

_LIST_SITES = {
    "https://sosial.gov.az/az/media/xeberler": r"/az/media/xeberler/.",
    "https://dsmf.gov.az/az/media/xeberler": r"/az/media/xeberler/.|dsmf\.gov\.az/post/.",
    "https://dost.gov.az/news": r"dost\.gov\.az/news/\d+",
    "https://dma.gov.az/media/xeberler": r"/media/xeberler/.",
    "https://ntv.az/news": r"ntv\.az/news/[a-z-]+/\d+",
    **{url: r"/az/news/[^/]+\.html$" for name, url, *_ in AZ_FEEDS if url.endswith("-ih.gov.az/news.html")},
    **{url: r"/xeber/[^/?#]+$" for name, url, *_ in AZ_FEEDS if url.endswith("-ih.gov.az/xeberler")},
}

# Lent ünvanı RSS yox, HTML səhifədirsə, _load_direct bu oxuyucunu işlədir (mənbə sağlamlığı, ehtiyatlar və limitlər eynidir).
PAGE_PARSERS = {
    CROSSMEDIA_URL: parse_crossmedia,
    XALQQAZETI_URL: parse_xalqqazeti,
    YENIAZERBAYCAN_URL: parse_yeniazerbaycan,
    **{url: (lambda page, url=url, rx=rx: parse_list_page(page, url, rx)) for url, rx in _LIST_SITES.items()},
    **{url: (lambda page, url=url, rule=rule: parse_cards(page, url, *rule)) for url, rule in _CARD_SITES.items()},
}

def official_items(tries=1, timeout=12):
    """Prezident və birinci xanımın rəsmi səhifələri.

    president.az/az/rss əsasən vətəndaş məktublarıdır; xəbərlər /az/news HTML-indədir.
    mehriban-aliyeva.az-da RSS yoxdur, xronika /site/catalogNews-dədir.
    AZƏRTAC (rss-official-chronicle) bir çox şəbəkədən 403 qaytarır, ona görə burada yoxdur.
    AZƏRTAC-ın Regionlar bölməsinin RSS-i yoxdur (rss?cat=regionlar ümumi lentdir); HTML səhifəsi oxunur.
    """
    def regions():
        return [("AZƏRTAC (Regionlar)", "az", "Bölgələr", None, it) for it in parse_azertag_regions(fetch_text(AZERTAG_REGIONS, tries, timeout))]

    def president():
        return [("Prezident.az", "az", "Prezident", "Prezident", it) for it in parse_president_page(fetch_text("https://president.az/az/news", tries, timeout))]

    def first_lady():
        items, page = [], fetch_text("https://mehriban-aliyeva.az/site/catalogNews", tries, timeout)
        for td in re.findall(r'<td class="col-\d">(.*?)</td>', page, re.S):
            href = re.search(r'class="view-title" href="([^"]+)"', td)
            date = re.search(r'class="view-date">([^<]+)', td)
            title = re.search(r'class="view-date">[^<]*</span>\s*<br>\s*(.*?)</a>', td, re.S)
            img = re.search(r'<img[^>]+src="([^"]+)"', td)
            t = _clean_text(title.group(1)) if title else ""
            if not (href and t):
                continue
            link = urllib.parse.urljoin("https://mehriban-aliyeva.az", href.group(1))
            items.append(("Mehriban Əliyeva", "az", "Prezident", "Prezident", {
                "title": t, "link": link,
                "description": "Birinci vitse-prezident Mehriban Əliyevanın rəsmi səhifəsindən.",
                "pubDate": parse_az_date(date.group(1) if date else ""),
                "image": _abs_img(img.group(1), link) if img else None, "author": "",
            }))
        return items

    # Hər səhifənin öz vaxtı var: biri asılsa president.az gözləmir, xətası da statusda görünür.
    items, errors = [], []
    with ThreadPoolExecutor(max_workers=3) as ex:
        pages = [("AZƏRTAC (Regionlar)", ex.submit(regions)), ("Prezident.az", ex.submit(president)), ("Mehriban Əliyeva", ex.submit(first_lady))]
    for name, future in pages:
        try:
            items.extend(future.result())
        except Exception as e:
            errors.append(f"{name}: {type(e).__name__}: {str(e)[:80]}")
    return items, errors

# X paylaşımları: X-in açıq lenti/embed-i 2026-da çıxışsız istifadəçiyə bağlıdır (syndication 429, embed boş iframe).
# Ona görə rəhbərliyin X/Instagram/Facebook paylaşımları onları xəbər verən rəsmi və agentlik xəbərlərindən götürülür
# («Prezidentin sosial şəbəkə hesablarında ... paylaşılıb», «Mehriban Əliyeva ... paylaşım edib»).
_SOC_SHARE_RX = re.compile(r"paylaş", re.I)
_SOC_LEADER = ("prezident", "Prezident İlham Əliyev")
_SOC_LADY = ("birinci-xanim", "Mehriban Əliyeva")

def social_author(title):
    """Paylaşımın müəllifi. Dövlət başçısının adına başqasının sözü yazılmasın: «ABŞ prezidenti», «Azercell prezidenti» sayılmır."""
    t = norm_az(title)
    if re.search(r"ilham əliyev|azərbaycan prezident", t):
        return _SOC_LEADER
    if re.search(r"mehriban əliyeva", t):
        return _SOC_LADY
    if re.search(r"birinci xanım|birinci vitse-prezident", t) and not _ROLE_FOREIGN.search(t):
        return _SOC_LADY
    if PRESIDENT_WEAK_RX.search(t) and not has_any(t, FOREIGN_MARKERS):
        return _SOC_LEADER
    return None

_SOC_SKIP_RX = re.compile(r"xronika|bu gün tarixdə|il əvvəl", re.I)
_SOC_NET = [("Instagram", re.compile(r"instagram|instaqram", re.I)), ("Facebook", re.compile(r"facebook|feysbuk", re.I)),
            ("X", re.compile(r"\bX\b|tvit|twitter|sosial (?:şəbəkə|media)|paylaş", re.I))]

def social_from_news(articles, now=None, window_h=3.0):
    """Xəbər lentindən rəhbərliyin sosial paylaşımlarını çıxarır. Eyni hesabın 3 saat içindəki xəbərləri bir paylaşım sayılır."""
    found = []
    for a in articles:
        title = a.get("title") or ""
        if not _SOC_SHARE_RX.search(title) or _SOC_SKIP_RX.search(title):
            continue
        who = social_author(title)
        if not who:
            continue
        net = next((n for n, rx in _SOC_NET if rx.search(title)), "X")
        found.append({"id": a["id"], "who": who[0], "name": who[1], "network": net, "text": title,
                      "url": a.get("sourceUrl"), "publishedAt": a.get("publishedAt"), "imageUrl": a.get("imageUrl"),
                      "via": a.get("source"), "_n": 1 + len(a.get("alts") or [])})
    found.sort(key=lambda p: p.get("publishedAt") or "")
    kept = []
    for p in found:
        t = _parse_dt(p["publishedAt"])
        dup = None
        for q in kept:
            if q["who"] == p["who"] and t and q["_t"] and abs((t - q["_t"]).total_seconds()) <= window_h * 3600:
                dup = q
                break
        if dup:
            if p["_n"] > dup["_n"]:  # daha çox mənbənin yazdığı başlıq qalır, vaxt ilk xəbərinki
                dup.update({k: p[k] for k in ("id", "text", "url", "imageUrl", "via", "_n", "network")})
            continue
        p["_t"] = t
        kept.append(p)
    for p in kept:
        p.pop("_t", None)
        p.pop("_n", None)
    return kept

# Rəsmi YouTube lentləri (Atom). X/Instagram/Facebook/Telegram-ın açıq lenti yoxdur.
YT_ACCOUNTS = [
    ("https://www.youtube.com/feeds/videos.xml?user=presidentaz", "prezident", "Prezident İlham Əliyev"),
    ("https://www.youtube.com/feeds/videos.xml?channel_id=UCdT9CFMpO_o1Sy10Dz2b9DQ", "birinci-xanim", "Mehriban Əliyeva"),
]

def update_social():
    posts, failed = [], set()
    yt_rows = []
    for url, who, name in YT_ACCOUNTS:
        try:
            got = yt_items(url, 4)
            if not got:
                raise ValueError("boş lent")
            yt_rows.append({"name": f"YouTube · {name}", "url": url, "count": len(got), "error": None})
            for it in got:
                posts.append({
                    "id": hashlib.sha1(it["link"].encode()).hexdigest()[:16],
                    "who": who, "name": name, "network": "YouTube",
                    "text": it["title"], "url": it["link"],
                    "publishedAt": to_iso(it.get("pubDate")),
                    "imageUrl": it.get("image"),
                })
        except Exception as e:
            failed.add(who)
            yt_rows.append({"name": f"YouTube · {name}", "url": url, "count": 0, "error": f"{type(e).__name__}: {str(e)[:80]}"})
            print(f"  ! sosial {name}: {type(e).__name__}: {str(e)[:80]}")
    old = []
    try:
        old = json.loads(SOCIAL_FILE.read_text(encoding="utf-8")).get("posts") or []
    except Exception:
        old = []
    _keep_first_seen(posts, old)
    if failed:
        posts.extend(p for p in old if p.get("who") in failed and p.get("network") == "YouTube")
    try:
        arts = json.loads(OUT_FILE.read_text(encoding="utf-8")).get("articles") or []
        posts.extend(social_from_news(arts))
    except Exception as e:
        print(f"  ! sosial (xəbərdən): {type(e).__name__}: {str(e)[:80]}")
    posts.sort(key=lambda p: p.get("publishedAt") or "", reverse=True)
    now = datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds")
    OUT_DIR.mkdir(exist_ok=True)
    _write_atomic(SOCIAL_FILE, json.dumps({"updatedAt": now, "posts": posts[:16]}, ensure_ascii=False,
                                       separators=(",", ":")), encoding="utf-8")
    merge_sources(yt_rows)
    print(f"Sosial: {min(16, len(posts))} yazı ({sum(1 for p in posts[:16] if p.get('via'))} xəbərdən)")

def _yt_id(link):
    try:
        u = urllib.parse.urlparse(link or "")
        q = urllib.parse.parse_qs(u.query).get("v")
        if q:
            return q[0]
        parts = [p for p in u.path.split("/") if p]
        if len(parts) >= 2 and parts[-2] in ("shorts", "embed", "live"):
            return parts[-1]
    except Exception:
        return ""
    return ""

# YouTube-un RSS lenti (feeds/videos.xml) 2026-cı ilin oktyabrından 404 qaytarır. Ehtiyat: kanalın «videos»
# səhifəsindəki ytInitialData JSON-u — hər video üçün contentId, başlıq və nisbi vaxt («21 min ago»).
_YT_MARK = re.compile(r'"contentId":"([A-Za-z0-9_-]{11})","contentType":"LOCKUP_CONTENT_TYPE_VIDEO"')
_YT_TITLE = re.compile(r'"lockupMetadataViewModel":\{"title":\{"content":"((?:[^"\\]|\\.)*)"')
_YT_REL = re.compile(r'"accessibilityLabel":"(\d+) (minute|hour|day|week|month|year)s? ago"')
_YT_UNIT = {"minute": 60, "hour": 3600, "day": 86400, "week": 604800, "month": 2592000, "year": 31536000}

def parse_yt_channel_page(text, limit=10, now=None):
    now = now or datetime.datetime.now(datetime.timezone.utc)
    marks = list(_YT_MARK.finditer(text))
    items = []
    for i, mk in enumerate(marks):
        end = marks[i + 1].start() if i + 1 < len(marks) else mk.end() + 8000
        chunk = text[mk.end():end]
        t = _YT_TITLE.search(chunk)
        if not t:
            continue
        try:
            title = json.loads('"' + t.group(1) + '"')
        except Exception:
            title = t.group(1)
        rel = _YT_REL.search(chunk)
        pub = now - datetime.timedelta(seconds=int(rel.group(1)) * _YT_UNIT[rel.group(2)]) if rel else now
        vid = mk.group(1)
        items.append({"title": title, "link": f"https://www.youtube.com/watch?v={vid}", "description": "",
                      "pubDate": pub.isoformat(timespec="seconds"),
                      "image": f"https://i.ytimg.com/vi/{vid}/hqdefault.jpg", "author": ""})
        if len(items) >= limit:
            break
    return items

def yt_channel_videos(feed_url, limit=10):
    m = re.search(r"channel_id=([A-Za-z0-9_-]+)", feed_url)
    if m:
        page = f"https://www.youtube.com/channel/{m.group(1)}/videos"
    else:
        u = re.search(r"user=([A-Za-z0-9_-]+)", feed_url)
        if not u:
            raise ValueError("kanal tapılmadı")
        page = f"https://www.youtube.com/user/{u.group(1)}/videos"
    text = fetch(page, timeout=20, headers={"Accept-Language": "en-US,en;q=0.9", "Cookie": "CONSENT=YES+cb; SOCS=CAI"}).decode("utf-8", "replace")
    items = parse_yt_channel_page(text, limit)
    if not items:
        raise ValueError("video siyahısı boş")
    return items

def yt_items(url, limit):
    """Əvvəl RSS, alınmayanda kanal səhifəsi."""
    try:
        got = parse_feed(fetch(url))[:limit]
        if got:
            return got
    except Exception:
        pass
    return yt_channel_videos(url, limit)

def _keep_first_seen(items, old):
    """YouTube kanal səhifəsi dəqiq vaxt vermir («1 day ago» → indi − 1 gün); eyni video əvvəl görülübsə, ilk qeyd olunan
    (daha erkən) vaxt saxlanır ki, sıra dövrdən-dövrə sürüşməsin."""
    seen = {}
    for p in old or []:
        if p.get("url") and p.get("publishedAt"):
            seen[p["url"]] = p["publishedAt"]
    for p in items:
        prev = seen.get(p.get("url"))
        if prev and (not p.get("publishedAt") or prev < p["publishedAt"]):
            p["publishedAt"] = prev
    return items

def update_video():
    items, rows = [], []
    for name, url in YT_NEWS:
        try:
            got = yt_items(url, 5)
            if not got:
                raise ValueError("boş lent")
            rows.append({"name": f"YouTube · {name}", "url": url, "count": len(got), "error": None})
            for it in got:
                if is_negative_about_leadership(it.get("title", ""), it.get("description", "")):
                    continue
                vid = _yt_id(it.get("link"))
                if not vid:
                    continue
                items.append({
                    "id": hashlib.sha1(it["link"].encode()).hexdigest()[:16],
                    "title": it["title"], "channel": name, "videoId": vid,
                    "url": it["link"], "publishedAt": to_iso(it.get("pubDate")),
                    "imageUrl": it.get("image") or f"https://i.ytimg.com/vi/{vid}/hqdefault.jpg",
                })
        except Exception as e:
            rows.append({"name": f"YouTube · {name}", "url": url, "count": 0, "error": f"{type(e).__name__}: {str(e)[:80]}"})
            print(f"  ! video {name}: {type(e).__name__}")
    try:
        _keep_first_seen(items, json.loads(VIDEO_FILE.read_text(encoding="utf-8")).get("items"))
    except Exception:
        pass
    items.sort(key=lambda p: p.get("publishedAt") or "", reverse=True)
    now = datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds")
    OUT_DIR.mkdir(exist_ok=True)
    _write_atomic(VIDEO_FILE, json.dumps({"updatedAt": now, "items": items[:24]}, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    if rows:
        merge_sources(rows)
    print(f"Video: {min(24, len(items))} yazı")

# Misli Premyer Liqası: pfl.az saytının öz tətbiqinin istifadə etdiyi açıq JSON API (açar tələb etmir).
PFL_API = "https://pfl.az/api/v1"

def _pfl_json(path, timeout=15):
    return json.loads(fetch(PFL_API + path, timeout=timeout, headers={"Accept": "application/json"}).decode("utf-8"))

def _pfl_date(s):
    """'14/08/2026 19:30' (Bakı vaxtı) -> ISO."""
    try:
        return datetime.datetime.strptime(s, "%d/%m/%Y %H:%M").replace(tzinfo=BAKU).isoformat(timespec="minutes")
    except Exception:
        return ""

def _pfl_game(g):
    c1, c2 = g.get("club_1") or {}, g.get("club_2") or {}
    return {
        "home": c1.get("title") or "", "away": c2.get("title") or "",
        "hs": g.get("club_score_1"), "as": g.get("club_score_2"),
        "date": _pfl_date(g.get("start_date") or ""),
        "played": g.get("status") == 3,
        "stadium": (g.get("stadion") or {}).get("title") or "",
    }

def parse_pfl(seasons, grid, tours, scorers):
    """pfl.az cavablarından football.json məzmunu. Şəbəkəsiz test üçün ayrıca funksiyadır.
    grid: hər klub üçün rate {o: oyun, q: qalibiyyət, h: heç-heçə, m: məğlubiyyət, vq/bq: qollar, tf: fərq, x: xal, ordering: yer}.
    tours: turlar; game.status 3 = oynanıb, is_current = növbəti tur."""
    season = (seasons.get("data") or [{}])[0]
    league = (season.get("leagues") or [{}])[0]
    table = []
    for t in grid.get("data") or []:
        r = t.get("rate") or {}
        table.append({"pos": r.get("ordering") or 0, "team": t.get("title") or "", "logo": t.get("logo") or "",
                      "p": r.get("o") or 0, "w": r.get("q") or 0, "d": r.get("h") or 0, "l": r.get("m") or 0,
                      "gf": r.get("vq") or 0, "ga": r.get("bq") or 0, "gd": r.get("tf") or 0, "pts": r.get("x") or 0})
    table.sort(key=lambda x: (x["pos"] or 99, -x["pts"], -x["gd"]))
    for i, row in enumerate(table, 1):
        row["pos"] = i
    tour_list = tours.get("data") or []
    played = [x for x in tour_list if any(g.get("status") == 3 for g in x.get("games") or [])]
    results, fixtures, round_played, round_next = [], [], "", ""
    if played:
        last = played[-1]
        round_played = str(last.get("title") or "")
        results = [_pfl_game(g) for g in last.get("games") or []]
    nxt = next((x for x in tour_list if x.get("is_current")), None)
    if nxt is None:
        nxt = next((x for x in tour_list if x not in played), None)
    if nxt is not None:
        round_next = str(nxt.get("title") or "")
        fixtures = [_pfl_game(g) for g in nxt.get("games") or []]
    sc = []
    for s in ((scorers.get("data") or {}).get("data") or [])[:5]:
        p = s.get("player") or {}
        sc.append({"name": (f"{p.get('name') or ''} {p.get('surname') or ''}").strip(),
                   "club": (s.get("club") or {}).get("title") or "", "goals": int(s.get("value") or 0)})
    return {"league": league.get("title") or "Misli Premyer Liqası", "season": season.get("title") or "",
            "table": table, "results": results, "fixtures": fixtures,
            "roundPlayed": round_played, "roundNext": round_next, "scorers": sc,
            "link": "https://pfl.az/", "source": "pfl.az"}

# pfl.az «layihələri»: hər biri bir liqa. Sıra saytdakı seçicinin sırasıdır.
PFL_PROJECTS = [(1, "Premyer Liqa"), (2, "I Liqa"), (3, "II Liqa"), (5, "Kubok"), (4, "Əvəzedicilər")]
FOOTBALL_EVERY = datetime.timedelta(minutes=10)  # 5 liqa × 4 sorğu — hər dövrədə yox

def fetch_pfl_league(project_id):
    """Bir liqanın cədvəli, turları və bombardirləri. Kubokda (is_elimination) cədvəl olmur."""
    seasons = _pfl_json(f"/seasons?project_id={project_id}")
    season = (seasons.get("data") or [{}])[0]
    league = (season.get("leagues") or [{}])[0]
    if not league.get("id"):
        raise ValueError("liqa yoxdur")
    elimination = bool(league.get("is_elimination"))
    grid = {} if elimination else _pfl_json(f"/leagues/grid?season_id={season.get('id')}&project_id={project_id}")
    tours = _pfl_json(f"/tours/get-games?league_id={league.get('id')}&withGames=true")
    try:
        scorers = _pfl_json(f"/bombarders/list?league_id={league.get('id')}")
    except Exception:
        scorers = {}
    d = parse_pfl(seasons, grid, tours, scorers)
    d["elimination"] = elimination
    d["project"] = project_id
    return d

# Dünya liqaları: ESPN-in açıq (sənədsiz) cədvəl API-si, açar tələb etmir. Avroliqa orada boş gəlir, ona görə yoxdur.
ESPN_STANDINGS = "https://site.api.espn.com/apis/v2/sports/{sport}/{slug}/standings"
ESPN_LEAGUES = [
    ("eng.1", "soccer", "Premyer Liqa (İngiltərə)", "İngiltərə"),
    ("esp.1", "soccer", "La Liga", "İspaniya"),
    ("ita.1", "soccer", "Seriya A", "İtaliya"),
    ("ger.1", "soccer", "Bundesliqa", "Almaniya"),
    ("fra.1", "soccer", "Liqa 1", "Fransa"),
    ("tur.1", "soccer", "Süper Liq", "Türkiyə"),
    ("uefa.champions", "soccer", "Çempionlar Liqası", "ÇL"),
    ("nba", "basketball", "NBA", "NBA"),
]
SPORTS_EVERY = datetime.timedelta(minutes=30)

def _espn_stat(stats, name):
    for s in stats or []:
        if s.get("name") == name:
            v = s.get("value")
            if v is None:
                v = s.get("displayValue")
            return v
    return None

def _num(v, default=0):
    try:
        return int(float(v))
    except Exception:
        return default

def parse_espn(doc, sport):
    """ESPN cədvəl cavabı -> qruplar və sətirlər. Futbol: O/Q/H/M/qol/xal; basketbol: Q/M/faiz/geridə."""
    groups = doc.get("children") or [doc]
    out = []
    for g in groups:
        entries = ((g.get("standings") or {}).get("entries")) or []
        rows = []
        for e in entries:
            t = e.get("team") or {}
            st = e.get("stats") or []
            logos = t.get("logos") or []
            row = {"team": t.get("shortDisplayName") or t.get("displayName") or "", "full": t.get("displayName") or "",
                   "logo": (logos[0].get("href") if logos else "") or ""}
            if sport == "soccer":
                row.update({"pos": _num(_espn_stat(st, "rank")), "p": _num(_espn_stat(st, "gamesPlayed")), "w": _num(_espn_stat(st, "wins")),
                            "d": _num(_espn_stat(st, "ties")), "l": _num(_espn_stat(st, "losses")), "gf": _num(_espn_stat(st, "pointsFor")),
                            "ga": _num(_espn_stat(st, "pointsAgainst")), "gd": _num(_espn_stat(st, "pointDifferential")), "pts": _num(_espn_stat(st, "points"))})
                note = e.get("note") or {}
                if note.get("description"):
                    row["note"] = note.get("description")
                    row["color"] = note.get("color") or ""
            else:
                w, l = _num(_espn_stat(st, "wins")), _num(_espn_stat(st, "losses"))
                pct = _espn_stat(st, "winPercent")
                try:
                    pct = float(pct)
                except Exception:
                    pct = (w / (w + l)) if (w + l) else 0.0
                row.update({"pos": _num(_espn_stat(st, "playoffSeed")), "w": w, "l": l, "p": w + l, "pct": round(pct, 3),
                            "gb": _espn_stat(st, "gamesBehind")})
            rows.append(row)
        if sport == "soccer":
            rows.sort(key=lambda r: (r["pos"] or 99, -r["pts"], -r["gd"]))
        else:
            rows.sort(key=lambda r: (-r["pct"], -r["w"]))
        for i, r in enumerate(rows, 1):
            if not r.get("pos"):
                r["pos"] = i
        if rows:
            out.append({"name": g.get("name") or "", "rows": rows})
    return out

def update_sports():
    """Dünya futbol liqaları və NBA cədvəlləri (ESPN). 30 dəqiqədən bir; alınmayan liqa üçün köhnə məlumat qalır."""
    now_dt = datetime.datetime.now(datetime.timezone.utc)
    OUT_DIR.mkdir(exist_ok=True)
    try:
        old = json.loads(SPORTS_FILE.read_text(encoding="utf-8"))
    except Exception:
        old = {}
    try:
        if old.get("leagues") and now_dt - datetime.datetime.fromisoformat(old.get("updatedAt", "")) < SPORTS_EVERY:
            print("Dünya liqaları: təzədir"); return
    except Exception:
        pass
    old_by = {l.get("id"): l for l in old.get("leagues") or []}
    leagues, fresh = [], 0
    for slug, sport, name, short in ESPN_LEAGUES:
        try:
            doc = json.loads(fetch(ESPN_STANDINGS.format(sport=sport, slug=slug), timeout=20,
                                   headers={"Accept": "application/json"}).decode("utf-8"))
            groups = parse_espn(doc, sport)
            if not groups:
                raise ValueError("cədvəl boşdur")
            leagues.append({"id": slug, "sport": "football" if sport == "soccer" else "basketball", "name": name, "short": short,
                            "season": str((doc.get("season") or {}).get("year") or ""), "groups": groups})
            fresh += 1
        except Exception as e:
            print(f"  ! {name}:", type(e).__name__)
            if slug in old_by:
                leagues.append(dict(old_by[slug], stale=True))
    _write_atomic(SPORTS_FILE, json.dumps({"updatedAt": now_dt.isoformat(timespec="seconds"), "source": "ESPN", "leagues": leagues},
                                      ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    print(f"Dünya liqaları: {fresh}/{len(ESPN_LEAGUES)} təzə")

def update_football():
    """Bütün liqalar (Premyer, I, II, Kubok, Əvəzedicilər) pfl.az-dan. Üst səviyyədəki sahələr Premyer Liqadır
    (köhnə quruluş), «leagues» siyahısında hamısı var. Alınmayan liqa üçün köhnə məlumat «stale» ilə qalır."""
    now_dt = datetime.datetime.now(datetime.timezone.utc)
    now = now_dt.isoformat(timespec="seconds")
    OUT_DIR.mkdir(exist_ok=True)
    try:
        old = json.loads(FOOTBALL_FILE.read_text(encoding="utf-8"))
    except Exception:
        old = {}
    try:
        last = datetime.datetime.fromisoformat(old.get("updatedAt", ""))
        if old.get("leagues") and now_dt - last < FOOTBALL_EVERY:
            print("Futbol: təzədir"); return
    except Exception:
        pass
    old_leagues = {l.get("project"): l for l in old.get("leagues") or []}
    leagues, fresh = [], 0
    for project_id, short in PFL_PROJECTS:
        try:
            d = fetch_pfl_league(project_id)
            if not d["table"] and not d["results"] and not d["fixtures"]:
                raise ValueError("məlumat boşdur")
            d["short"] = short
            leagues.append(d); fresh += 1
        except Exception as e:
            print(f"  ! futbol {short}:", type(e).__name__)
            if project_id in old_leagues:
                leagues.append(dict(old_leagues[project_id], stale=True))
    if not leagues:
        data = {"league": "Misli Premyer Liqası", "season": "", "table": [], "results": [], "fixtures": [],
                "scorers": [], "leagues": [], "note": "Futbol məlumatı alınmadı.", "link": "https://pfl.az/", "source": "pfl.az"}
    else:
        data = dict(leagues[0])
        data["leagues"] = leagues
    data["updatedAt"] = now
    _write_atomic(FOOTBALL_FILE, json.dumps(data, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    print(f"Futbol: {fresh}/{len(PFL_PROJECTS)} liqa təzə, Premyer: {len(data['table'])} komanda, son tur {data.get('roundPlayed') or '-'}")

# Eyni hadisəni müxtəlif mənbələr yaxın başlıqla verəndə bir kartın altında yığılır.
GROUP_WINDOW = datetime.timedelta(hours=36)
_GROUP_STOP = {
    "ve", "ile", "the", "and", "for", "from", "or", "bir", "bu", "da", "de", "ki", "veya",
    "icin", "olan", "və", "ilə", "də", "o", "üçün", "ya", "news", "xəbər", "xeber",
}

def _norm_title(s):
    s = (s or "").lower().replace("i̇", "i")
    s = s.translate(str.maketrans({"ə": "e", "ı": "i", "ö": "o", "ü": "u", "ş": "s", "ç": "c",
                                   "ğ": "g", "â": "a", "î": "i", "û": "u"}))
    s = re.sub(r"[^\w\s]", " ", s, flags=re.UNICODE)
    return re.sub(r"\s+", " ", s).strip()

def _title_tokens(s):
    return [t for t in _norm_title(s).split() if len(t) > 2 and t not in _GROUP_STOP and not t.isdigit()]

def _shingles(toks):
    if len(toks) < 3:
        return {" ".join(toks)} if toks else set()
    return {" ".join(toks[i:i + 3]) for i in range(len(toks) - 2)}

def _jaccard(a, b):
    if not a or not b:
        return 0.0
    return len(a & b) / len(a | b)

def _titles_similar(toks, sh, other_toks, other_sh):
    a, b = set(toks), set(other_toks)
    if len(a) < 3 or len(b) < 3:
        return False
    inter = len(a & b)
    tj, sj = _jaccard(a, b), _jaccard(sh, other_sh)
    shorter, longer = (a, b) if len(a) <= len(b) else (b, a)
    cont = len(shorter & longer) / len(shorter)
    ratio = min(len(a), len(b)) / max(len(a), len(b))
    if inter >= 4 and tj >= 0.55:
        return True
    if inter >= 3 and (tj >= 0.75 or sj >= 0.45) and ratio >= 0.5:
        return True
    if cont >= 0.86 and inter >= 4 and ratio >= 0.62:
        return True
    return False

# ---- Hadisə əsaslı birləşdirmə ------------------------------------------------------------------------
# Eyni hadisə fərqli başlıqlarla gəlir: «Pərviz Abubəkirov İŞDƏN ÇIXARILDI» / «Səhiyyə Nazirliyinin mətbuat katibi
# vəzifədən çıxarılıb»; «Real TV-nin əməkdaşlarını döydülər» / «Bakıda məktəbdə media nümayəndələrinə qarşı zorakılıq».
# Başlıq sözlərinin oxşarlığı bunu tutmur. Burada:
#   1) sinonimlər anlayışa gətirilir (jurnalist/media nümayəndəsi → media; döydü/hücum/zorakılıq → zorakılıq;
#      öldü/həyatını itirdi/vəfat → ölüm; işdən çıxarıldı/azad edildi/istefa → istefa ...),
#   2) hadisə növləri (istefa, təyinat, ölüm, həbs, zorakılıq, qəza, yanğın, partlayış) müqayisə olunur;
#      gündəlik tez-tez olan növlərdə (ölüm, qəza, həbs, yanğın) əlavə «lövbər» tələb olunur: şəxs/qurum adı,
#      3+ rəqəmli ədəd və ya cümlə ortasındakı xüsusi ad — yoxsa Bakıdakı iki ayrı qəza bir karta düşərdi,
#   3) şəxs/qurum adları yazılış fərqinə dözümlü tutuşdurulur (Abubəkirov / Əbubəkirov),
#   4) başlıq+xülasənin söz kökləri (şəkilçilər atılmış) müqayisə olunur.
#   Keçidli birləşmə: A~B və B~C olanda hər üçü bir kartdadır. Rəsmi mənbələrə tətbiq edilmir (şablon başlıqlar).
# (?<!\w): «dayanıb» yanğın, «bölüb» ölüm sayılmasın.
_CONCEPT_RX = [(re.compile(r"(?<!\w)(?:" + p + ")"), " " + c + " ") for p, c in (
    (r"həyatını itir\w*|dünyasını dəyiş\w*|vəfat\w*|həlak\w*|öl(?:üb|dü|üm|ən|məsi|dürül|ü\b)\w*|intihar\w*|cəsəd\w*|meyit\w*", "ölüm"),
    (r"jurnalist\w*|media nümayəndə\w*|mətbuat nümayəndə\w*|mətbuat əməkdaş\w*|reportyor\w*|müxbir\w*|çəkiliş qrup\w*", "media"),
    (r"döy(?:üb|dü|ül|məsi|ərək)\w*|hücum(?!çu)\w*|zorakılıq\w*|\bdava(?:sı|lar|da|sında)?\b|qətl\w*|bıçaqla\w*|güllələ\w*|vur(?:ub|du|ulub|ulan|ublar)\w*|təpik\w*|yumruq\w*", "zorakılıq"),
    (r"işdən (?:çıxar|azad|ayrıl|uzaqlaş|kənarlaş)\w*|vəzifə\w* (?:azad|çıxar|ayrıl|uzaqlaş|kənarlaş)\w*|azad (?:edil|olun)\w*|istefa\w*", "istefa"),
    (r"təyin (?:edil|olun)\w*|vəzifəyə təyin\w*", "təyinat"),
    (r"həbs\w*|saxlanıl\w*|saxlanan\w*|tutul(?:ub|du|an|ması)\w*|cinayət işi|ittiham\w*", "həbs"),
    (r"yol qəzası|qəza\w*|toqquş\w*|aşırıb\b", "qəza"),
    (r"yanğın\w*|alov\w*|yan(?:ıb|dı|ır)\b", "yanğın"),
    (r"partlayış\w*|partla(?:yıb|dı|yan|ma)\w*", "partlayış"),
    (r"şagird\w*|məktəbli\w*|tələbə\w*", "şagird"),
    (r"məktəb\w*|lisey\w*|gimnaziya\w*", "məktəb"),
    (r"uşaq\w*|azyaşlı\w*|yeniyetmə\w*", "uşaq"),
    (r"sürücü\w*|avtomobil\w*|maşın\w*|avtobus\w*|minik\w*", "nəqliyyat"),
    (r"xəstəxana\w*|klinika\w*|tibb (?:müəssisə|mərkəz)\w*", "xəstəxana"),
    (r"başsağlığı\w*|təbrik\w*|bəyanat\w*|açıqlama\w*|münasibət bildir\w*|şərh ed\w*|reaksiya\w*|xəbərdarlıq\w*", "reaksiya"),
)]
_EVENT_WORDS = ("istefa", "teyinat", "olum", "hebs", "zorakiliq", "qeza", "yangin", "partlayis")
_EVENT_KEYS = {w[:6] for w in _EVENT_WORDS}
# Anlayış sözləri şəkilçi təmizləməsindən keçmir (reaksiya → «reaks» olub tanınmırdı)
_PROTECTED = set(_EVENT_WORDS) | {"reaksiya", "media", "sagird", "mekteb", "usaq", "neqliyyat", "xestexana"}
_STRICT_CLASSES = {"olum", "qeza", "hebs", "yangin"}  # gündəlik tez-tez olan hadisələr: lövbər tələb olunur
_SUFFIX_RX = re.compile(r"(?:lar|ler|dan|den|nin|nun|araq|erek|in|un|da|de|ya|ye|la|le|si|su|ni|nu|ib|ub|di|du|a|e|i|u)$")
_GENERIC_ANCHOR = {"baki", "bakin", "bakid", "azerba", "azerb", "respub", "prezid", "nazirl", "dovlet", "milli", "qarab",
                   "video", "foto", "anbaan", "xeber", "real"}
_ENTITY_SKIP = {"ilham eliyev", "mehriban eliyeva", "heyder eliyev", "prezident ilham", "azerbaycan respublikasi",
                "azerbaycan respublikasinin", "milli meclis", "milli meclisin", "nazirler kabineti"}
_ORG_WORDS = re.compile(r"(?:nazirli|idare|sehe|rayon|respublika|komite|agentli|xidmet|universitet|merkez|sura|partiya|cemiyyet|"
                        r"fond|bank|klub|akademiya|institut|dovlet|prokurorlu|mehkeme|polis|birli|qurum|sirket|holdinq|qrup|"
                        r"prezident|cumhurbas|hokumet|hakimiyyet|sefir|deputat|rektor|general|polkovnik|sedr|direktor|baskan)")
# Hadisə müqayisəsində məzmun daşımayan sözlər (feil köməkçiləri, bağlayıcılar, format nişanları)
_EVENT_STOP = {"eden", "edib", "edir", "etdi", "edildi", "olub", "oldu", "olur", "olan", "olunub", "olundu", "var", "yoxdur",
               "ile", "ucun", "gore", "bagli", "dair", "sonra", "evvel", "hemin", "yeni", "daha", "cox", "nefer", "sayi",
               "video", "foto", "anbaan", "yenilenib", "detal", "detallar", "hadise", "netice", "neticesinde", "barede",
               "melumat", "bildirib", "bildirilib", "deyilir", "deyir", "dedi", "bas", "verib", "verdi", "veren", "qeyd"}
_SIG_CACHE = {}

def _concepts(text):
    t = (text or "").lower().replace("i̇", "i")
    for rx, rep in _CONCEPT_RX:
        t = rx.sub(rep, t)
    return t

def _stem(tok):
    """Ən çox 2 şəkilçi atılır, kök 4 hərfdən qısa olmur (yaxınları → yaxın, bakının → bakı, media → medi)."""
    if tok in _PROTECTED:
        return tok[:6]
    for _ in range(2):
        m = _SUFFIX_RX.search(tok)
        if not m or m.start() < 4:
            break
        tok = tok[:m.start()]
    return tok[:6]

def _event_stems(text):
    """Anlayışa gətirilmiş, sadələşdirilmiş, şəkilçisiz söz kökləri (ilk 6 hərf); 3+ rəqəmli ədədlər də saxlanır."""
    out = set()
    for tok in _norm_title(_concepts(text)).split():
        if tok.isdigit():
            if len(tok) >= 3:
                out.add(tok)
            continue
        if len(tok) <= 2 or tok in _GROUP_STOP or tok in _EVENT_STOP:
            continue
        st = _stem(tok)
        if len(st) >= 3:
            out.add(st)
    return out

def _anchors(text):
    """Lövbərlər: 3+ rəqəmli ədədlər və cümlə ortasında böyük hərflə başlayan xüsusi adlar (Yasamal, Dadaşova);
    ümumi yer adları (Bakı, Azərbaycan) sayılmır."""
    out = set()
    for sent in re.split(r"[.!?:;«»“”\"]+", text or ""):
        words = re.findall(r"[^\W_]+", sent)
        for i, w in enumerate(words):
            if w.isdigit():
                if len(w) >= 3:
                    out.add(w)
                continue
            if i == 0 or len(w) < 4 or not w[0].isupper() or (w.isupper() and len(w) > 3):
                continue
            st = _stem(_norm_title(w))
            if st not in _GENERIC_ANCHOR and len(st) >= 3:
                out.add(st)
    return out

def _places(text):
    """Yerlik halında böyük hərfli sözlər (Bakıda, Göygöldə, İspaniyada) — cümlə başında da sayılır; anlayış sözləri (Məktəbdə) yox."""
    out = set()
    for w in re.findall(r"[^\W\d_]+", text or ""):
        if len(w) < 5 or not w[0].isupper() or (w.isupper() and len(w) > 3):
            continue
        low = w.lower()
        if not re.search(r"(?:da|də|dan|dən)$", low) or _concepts(low).strip() != low:
            continue
        out.add(_stem(_norm_title(w)))
    return out

def _entities(text):
    """Böyük hərflə başlayan ardıcıl 2 söz (şəxs və ya qurum adı), sadələşdirilmiş. Tam böyük hərfli uzun sözlər (İŞDƏN) sayılmır."""
    words = re.findall(r"[^\W\d_]+", text or "")
    persons, orgs = set(), set()
    for w1, w2 in zip(words, words[1:]):
        if len(w1) < 2 or len(w2) < 2 or not (w1[0].isupper() and w2[0].isupper()):
            continue
        if (w1.isupper() and len(w1) > 3) or (w2.isupper() and len(w2) > 3):
            continue
        key = _norm_title(w1 + " " + w2)
        if key in _ENTITY_SKIP:
            continue
        (orgs if _ORG_WORDS.search(key) else persons).add(key)
    return persons, orgs

def _edits1(a, b):
    """Levenşteyn məsafəsi ≤ 1 (Abubəkirov / Əbubəkirov)."""
    if a == b:
        return True
    la, lb = len(a), len(b)
    if abs(la - lb) > 1:
        return False
    i = 0
    while i < min(la, lb) and a[i] == b[i]:
        i += 1
    if la == lb:
        return a[i + 1:] == b[i + 1:]
    if la > lb:
        return a[i + 1:] == b[i:]
    return a[i:] == b[i + 1:]

def _ent_match(e1, e2):
    for x in e1:
        xs = x.split()
        for y in e2:
            ys = y.split()
            if len(xs) == len(ys) and all((_edits1(p, q) if len(p) >= 6 else p == q) for p, q in zip(xs, ys)):
                return True
    return False

def _event_sig(a):
    key = (a.get("sourceUrl") or "", a.get("title") or "")
    sig = _SIG_CACHE.get(key)
    if sig is None:
        title, summ = a.get("title") or "", (a.get("summary") or "")[:240]
        text = title + ". " + summ
        persons, orgs = _entities(text)
        stems = _event_stems(text)
        classes = {w for w in _EVENT_KEYS if w in stems}
        sig = _SIG_CACHE[key] = (classes, persons, orgs, stems, _anchors(text), _places(text))
    return sig

def _same_event(a, b):
    """0 — fərqli; 1 — zəif uyğunluq (yalnız klaster başı ilə və ya 2 üzvlə təsdiqlənəndə sayılır);
    2 — güclü uyğunluq (eyni şəxs, eyni qurum + məzmun, 2+ lövbər + məzmun, kökləri güclü üst-üstə düşür)."""
    # Shared boilerplate in summaries must not join unrelated headlines.
    ta, tb = a.get("title") or "", b.get("title") or ""
    title_common = (_event_stems(ta) & _event_stems(tb)) - _GENERIC_ANCHOR
    people_a, people_b = _entities(ta)[0], _entities(tb)[0]
    if people_a and people_b and len(title_common) < 2 and not _ent_match(people_a, people_b):
        return 0
    ca, pa, oa, sa, na, la = _event_sig(a)
    cb, pb, ob, sb, nb, lb = _event_sig(b)
    if not sa or not sb:
        return 0
    common = sa & sb
    inter = len(common)
    cont = inter / min(len(sa), len(sb))
    anchors = len(na & nb)
    if inter >= 6 and _jaccard(sa, sb) >= 0.5:        # kökləri güclü üst-üstə düşür
        return 2
    if inter >= 8 and cont >= 0.6:
        return 2
    if anchors >= 2 and inter >= 5 and cont >= 0.4:    # iki ortaq lövbər (Yasamal + 225) və ortaq məzmun
        return 2
    shared = ca & cb
    if not shared:
        return 0
    if la and lb and not (la & lb):                   # fərqli yerlər (Bakıda / Göygöldə): fərqli hadisə
        return 0
    if _ent_match(pa, pb):                             # eyni şəxs + eyni hadisə növü
        return 2
    if _ent_match(oa, ob) and inter >= 4:              # eyni qurum + hadisə + ortaq məzmun
        return 2
    # Rəsmi reaksiya (başsağlığı, bəyanat, xəbərdarlıq) hadisənin özü ilə eyni xəbər deyil
    if ("reaksi" in sa) != ("reaksi" in sb):
        return 0
    loose = bool(shared - _STRICT_CLASSES)             # nadir hadisə növü (istefa, təyinat, zorakılıq, partlayış)
    specific = sum(1 for w in common if w not in _EVENT_KEYS and w not in _GENERIC_ANCHOR)
    # gündəlik növlərdə (ölüm, qəza, həbs, yanğın) ümumi sözlər kifayət deyil: lövbər və ya 2+ xüsusi anlayış
    if inter >= 3 and cont >= 0.4 and (loose or anchors or specific >= 2):
        return 1
    if inter >= 5 and cont >= 0.5:
        return 1
    return 0

def _parse_dt(iso):
    if not iso:
        return None
    try:
        dt = datetime.datetime.fromisoformat(iso.replace("Z", "+00:00"))
        return dt if dt.tzinfo else dt.replace(tzinfo=BAKU)  # zonasız qalıb — müqayisədə TypeError olmasın
    except Exception:
        return None

def _compact_alt(a):
    url = a.get("sourceUrl") or ""
    if not url:
        return None
    alt = {"source": a.get("source") or "", "sourceUrl": url, "publishedAt": a.get("publishedAt") or "",
           "title": a.get("title") or "", "lang": a.get("lang") or "az"}
    if a.get("imageUrl"):
        alt["imageUrl"] = a["imageUrl"]  # əsas kartın şəkli yoxdursa brauzer buradan götürür
    return alt

OFFICIAL_SOURCES = ("Prezident.az", "Mehriban Əliyeva")

def _prefer_primary(a, b):
    """Rəsmi mənbə (president.az, mehriban-aliyeva.az) həmişə əsas olsun — agentliyin surəti onu gizlətməsin.
    Sonra şəkli və daha dolu xülasəsi olan; eyni olanda daha yenisi."""
    ao, bo = a.get("source") in OFFICIAL_SOURCES, b.get("source") in OFFICIAL_SOURCES
    if ao != bo:
        return a if ao else b
    if ao and bo and (a.get("source") == "Prezident.az") != (b.get("source") == "Prezident.az"):
        return a if a.get("source") == "Prezident.az" else b
    if bool(a.get("imageUrl")) != bool(b.get("imageUrl")):
        return a if a.get("imageUrl") else b
    if len(a.get("summary") or "") != len(b.get("summary") or ""):
        return a if len(a.get("summary") or "") > len(b.get("summary") or "") else b
    return a if (a.get("publishedAt") or "") >= (b.get("publishedAt") or "") else b

def group_duplicates(articles):
    """Yaxın başlıqlı, fərqli mənbəli xəbərləri bir elementdə birləşdirir.

    Əsas xəbər tam qalır; digərləri yığcam `alts` siyahısındadır (mənbə + keçid + vaxt).
    """
    remembered = {}
    _SIG_CACHE.clear()
    for a in articles:
        for alt in a.get("alts") or []:
            if alt.get("sourceUrl"):
                remembered.setdefault(a.get("sourceUrl"), []).append(dict(alt))
        a.pop("alts", None)
    prepared = []
    for a in articles:
        dt = _parse_dt(a.get("publishedAt"))
        if dt is None:
            prepared.append((None, [], set(), a))
            continue
        toks = _title_tokens(a.get("title") or "")
        prepared.append((dt, toks, _shingles(toks), a))
    prepared.sort(key=lambda x: x[0] or datetime.datetime.min.replace(tzinfo=datetime.timezone.utc), reverse=True)
    clusters = []
    for dt, toks, sh, a in prepared:
        best, best_score = None, 0
        if dt is not None and len(toks) >= 3:
            key = _norm_title(a.get("title") or "")
            src = a.get("source")
            for members in clusters:
                head = members[0][0]
                if head is None or abs(dt - head) > GROUP_WINDOW:
                    continue
                near = [(mt, mtks, msh, ma) for mt, mtks, msh, ma in members if mt is not None and abs(dt - mt) <= GROUP_WINDOW]
                if not near:
                    continue
                exact = len(key) >= 12 and any(_norm_title(ma.get("title") or "") == key for _mt, _k, _s, ma in near)
                official = src in OFFICIAL_SOURCES or any(ma.get("source") in OFFICIAL_SOURCES for _mt, _k, _s, ma in members)
                same_src = src in {ma.get("source") for _mt, _k, _s, ma in members}
                score = 0
                if exact:
                    score = 4
                elif official:
                    # rəsmi şablon başlıqlar («X-in nazirini qəbul edib») fərqli hadisələrdə oxşar görünür — çox yaxın olmalıdır
                    if not same_src and any(_jaccard(set(toks), set(mtks)) >= 0.85 and _titles_similar(toks, sh, mtks, msh)
                                            for _mt, mtks, msh, _ma in near):
                        score = 3
                elif not same_src and any(_titles_similar(toks, sh, mtks, msh) for _mt, mtks, msh, _ma in near):
                    score = 3
                elif not same_src and len(members) < 12:
                    # Eyni saytın iki yazısı hadisə oxşarlığı ilə birləşmir: çox vaxt ayrı xəbərlərdir.
                    # Hadisə əsaslı uyğunluq yalnız klasterin toxumu (ilk, ən yeni üzv) ilə yoxlanır — ulduz topologiyası.
                    # Hər hansı üzvlə müqayisə zəncirvari «qar topu» yaradırdı (canlıda 330 alternativli kart).
                    seed = members[0]
                    if seed[0] is not None and abs(dt - seed[0]) <= GROUP_WINDOW:
                        strength = _same_event(a, seed[3])
                        if strength >= 2:
                            score = 2
                        elif strength == 1:
                            score = 1
                if score > best_score:
                    best, best_score = members, score
        if best is not None:
            best.append((dt, toks, sh, a))
        else:
            clusters.append([(dt, toks, sh, a)])
    out = []
    for members in clusters:
        urls = {m[3].get("sourceUrl") for m in members}
        extra = []
        for _dt, _toks, _sh, member in members:
            for alt in remembered.get(member.get("sourceUrl"), []):
                u = alt.get("sourceUrl")
                if u and u not in urls:
                    urls.add(u)
                    extra.append(alt)
        primary = members[0][3]
        for _dt, _toks, _sh, member in members[1:]:
            primary = _prefer_primary(primary, member)
        alts = []
        for _dt, _toks, _sh, member in members:
            if member is primary:
                continue
            alt = _compact_alt(member)
            if alt:
                alts.append(alt)
        # Yadda saxlanmış (əvvəlki dövrlərin) alternativləri: yalnız 36 saat pəncərəsində, klaster böyük deyilsə, cəmi 20-yə qədər.
        # Əvvəl hamısı qeyd-şərtsiz qaytarılırdı — bir dəfə yaranan «qar topu» (330 alternativ) alqoritm düzəlsə də dağılmırdı.
        pdt = _parse_dt(primary.get("publishedAt"))
        if len(members) < 12:
            kept = []
            for alt in extra:
                adt = _parse_dt(alt.get("publishedAt"))
                title = alt.get("title") or ""
                toks, ptoks = _title_tokens(title), _title_tokens(primary.get("title") or "")
                same = (_norm_title(title) == _norm_title(primary.get("title") or "")
                        or _titles_similar(toks, _shingles(toks), ptoks, _shingles(ptoks))
                        or _same_event(alt, primary) >= 2)
                # Legacy alternatives have no headline: they cannot be verified.
                if title and same and pdt is not None and adt is not None and abs(adt - pdt) <= GROUP_WINDOW:
                    kept.append(alt)
            alts.extend(kept[:max(0, 20 - len(alts))])
        alts.sort(key=lambda x: x.get("publishedAt") or "", reverse=True)
        # Kartdakı «N mənbə» həqiqətən N sayt demək olsun.
        sources_seen, unique = {primary.get("source")}, []
        for alt in alts:
            if alt.get("source") not in sources_seen:
                sources_seen.add(alt.get("source"))
                unique.append(alt)
        alts = unique
        if alts:
            primary["alts"] = alts
        else:
            primary.pop("alts", None)
        out.append(primary)
    prim_urls = {a.get("sourceUrl") for a in out}
    for a in out:
        if a.get("alts"):
            a["alts"] = [x for x in a["alts"] if x.get("sourceUrl") not in prim_urls]
            if not a["alts"]:
                a.pop("alts", None)
    out.sort(key=lambda a: a.get("publishedAt") or "", reverse=True)
    return out

OFFICIAL_FEEDS = (
    ("Prezident.az", "https://president.az/az/news"),
    ("Mehriban Əliyeva", "https://mehriban-aliyeva.az/site/catalogNews"),
    ("AZƏRTAC (Regionlar)", AZERTAG_REGIONS),
)

def official_source_rows(off_items, off_errors):
    counts = {}
    for row in off_items:
        counts[row[0]] = counts.get(row[0], 0) + 1
    err_by = {}
    for e in off_errors:
        err_by[e.split(":", 1)[0].strip()] = e
    return [{"name": name, "url": url, "count": counts.get(name, 0), "error": err_by.get(name)}
            for name, url in OFFICIAL_FEEDS]

def save_sources(rows):
    """Hər mənbə üçün son uğurlu vaxt, say və son xəta. Əvvəlki uğur xəta olanda qalır."""
    prev_list = []
    try:
        prev_list = json.loads(SOURCES_FILE.read_text(encoding="utf-8")).get("sources") or []
    except Exception:
        prev_list = []
    prev = {s.get("name"): s for s in prev_list}
    now = datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds")
    out = []
    for r in rows:
        old = prev.get(r["name"]) or {}
        err = r.get("error") or None
        if err:
            out.append({"name": r["name"], "url": r["url"], "okAt": old.get("okAt"),
                        "count": old.get("count", 0), "error": err})
        else:
            out.append({"name": r["name"], "url": r["url"], "okAt": now,
                        "count": int(r.get("count") or 0), "error": None})
    # Siyahıdan çıxarılan mənbələr vəziyyət səhifəsində qalmasın (əvvəl köhnə sətirlər həmişə saxlanırdı)
    OUT_DIR.mkdir(exist_ok=True)
    _write_atomic(SOURCES_FILE, json.dumps({"updatedAt": now, "sources": out}, ensure_ascii=False,
                                        separators=(",", ":")), encoding="utf-8")
    print(f"Mənbə statusu: {len(out)}")

def merge_sources(rows):
    """Mövcud sources.json-a əlavə mənbələr (məs. YouTube) yazır."""
    if not rows:
        return
    try:
        data = json.loads(SOURCES_FILE.read_text(encoding="utf-8"))
        current = data.get("sources") or []
    except Exception:
        current = []
    fake_prev = current
    prev = {s.get("name"): s for s in fake_prev}
    now = datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds")
    updated = {s.get("name"): s for s in current}
    for r in rows:
        old = prev.get(r["name"]) or {}
        err = r.get("error") or None
        if err:
            updated[r["name"]] = {"name": r["name"], "url": r["url"], "okAt": old.get("okAt"),
                                  "count": old.get("count", 0), "error": err}
        else:
            updated[r["name"]] = {"name": r["name"], "url": r["url"], "okAt": now,
                                  "count": int(r.get("count") or 0), "error": None}
    order = [s.get("name") for s in current if s.get("name") in updated]
    for r in rows:
        if r["name"] not in order:
            order.append(r["name"])
    OUT_DIR.mkdir(exist_ok=True)
    _write_atomic(SOURCES_FILE, json.dumps({
        "updatedAt": now,
        "sources": [updated[n] for n in order if n in updated],
    }, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")

def _xml(s):
    cur = s or ""
    for _ in range(3):
        nxt = html.unescape(cur)
        if nxt == cur:
            break
        cur = nxt
    return html.escape(cur, quote=True)

def write_feed(articles):
    items = sorted(articles, key=lambda a: a.get("publishedAt") or "", reverse=True)[:100]
    now = datetime.datetime.now(datetime.timezone.utc)
    parts = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        '<rss version="2.0"><channel>',
        f"<title>{_xml('8ulduz — son xəbərlər')}</title>",
        f"<link>{SITE}</link>",
        "<description>Azərbaycan və dünyadan son xəbərlər. Qısa xülasə və mənbə keçidi.</description>",
        "<language>az</language>",
        f"<lastBuildDate>{email.utils.format_datetime(now)}</lastBuildDate>",
    ]
    for a in items:
        dt = _parse_dt(a.get("publishedAt")) or now
        desc = re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", a.get("summary") or "")).strip()[:500]
        parts.append("<item>")
        parts.append(f"<title>{_xml(a.get('title'))}</title>")
        parts.append(f"<link>{_xml(a.get('sourceUrl'))}</link>")
        parts.append(f"<guid isPermaLink=\"false\">{_xml(a.get('id'))}</guid>")
        parts.append(f"<pubDate>{email.utils.format_datetime(dt)}</pubDate>")
        parts.append(f"<description>{_xml(desc)}</description>")
        parts.append(f"<source url=\"{_xml(a.get('sourceUrl'))}\">{_xml(a.get('source'))}</source>")
        parts.append(f"<category>{_xml(a.get('category'))}</category>")
        parts.append("</item>")
    parts.append("</channel></rss>\n")
    _write_atomic(FEED_FILE, "".join(parts), encoding="utf-8")
    print(f"RSS: {len(items)} xəbər")

# app.js-dəki CATS ilə eyni: statik bölmə səhifələri (axtarış sistemləri üçün həqiqi ünvanlar) və sitemap
SECTIONS = [
    ("prezident", "Zuğulba Xronikası", "Prezident İlham Əliyev və Birinci xanım Mehriban Əliyevanın gündəliyi"),
    ("gundem", "Gündəm", "Günün əsas hadisələri"),
    ("siyaset", "Siyasət", "Daxili və xarici siyasət"),
    ("cemiyyet", "Cəmiyyət", "Sosial həyatdan xəbərlər"),
    ("iqtisadiyyat", "İqtisadiyyat", "Bazar, maliyyə, enerji"),
    ("dunya", "Dünya", "Beynəlxalq mətbuat"),
    ("idman", "İdman", "İdman aləmindən xəbərlər və nəticələr"),
    ("medeniyyet", "Mədəniyyət", "Kino, musiqi, sənət və mədəni həyat"),
    ("heyat", "Sağlamlıq və həyat", "Tibb, sağlamlıq, qidalanma, psixologiya"),
    ("sosial", "Sosial müdafiə", "Pensiya, müavinət, sosial yardım, əlillik, məşğulluq"),
    ("bolgeler", "Bölgələr", "Rayonlardan və şəhərlərdən xəbərlər"),
    ("tehsil", "Təhsil və elm", "Məktəb, universitet, elm, texnologiya"),
]
SECTIONS_DIR = ROOT / "bolme"

_SECTION_HTML = """<!doctype html>
<html lang="az">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0, viewport-fit=cover" />
    <script>try{var t=localStorage.getItem("8ulduz-theme");document.documentElement.dataset.theme=t==="light"?"light":"dark";var f=localStorage.getItem("8ulduz-fs");if(f==="0"||f==="1"||f==="2")document.documentElement.dataset.fs=f;}catch(e){}</script>
    <title>__LABEL__ — 8ulduz</title>
    <meta name="description" content="__DESC__ — 8ulduz, Azərbaycan və dünyadan son xəbərlər." />
    <link rel="canonical" href="__URL__" />
    <meta name="theme-color" content="#0a1120" />
    <meta property="og:type" content="website" />
    <meta property="og:site_name" content="8ulduz" />
    <meta property="og:title" content="__LABEL__ — 8ulduz" />
    <meta property="og:description" content="__DESC__" />
    <meta property="og:url" content="__URL__" />
    <meta property="og:locale" content="az_AZ" />
    <meta property="og:image" content="__SITE__assets/og-default.png" />
    <meta name="twitter:card" content="summary_large_image" />
    <link rel="alternate" type="application/rss+xml" title="8ulduz" href="__SITE__feed.xml" />
    <link rel="manifest" href="__SITE__manifest.webmanifest" />
    <link rel="icon" href="__SITE__assets/icon-192.png" sizes="192x192" />
    <link rel="preconnect" href="https://fonts.googleapis.com" />
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin />
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800;900&display=swap" rel="stylesheet" />
    <link rel="stylesheet" href="../../assets/app.css" />
    <script src="../../assets/config.js"></script>
    <script src="../../assets/content-policy.js"></script>
    <script type="module" src="../../assets/app.js"></script>
    <!-- Resurslar yuxarıda nisbi yolla yükləndi; tətbiq kök ünvanda işləyir, ona görə ünvan kökə keçirilir -->
    <script>history.replaceState(null, "", new URL("../../#/bolme/__SLUG__", location.href));</script>
  </head>
  <body>
    <div id="app">
      <main class="wrap"><h1>__LABEL__</h1><p>__DESC__</p>__ITEMS__
      <p><a href="../../">8ulduz — baş səhifə</a> · <a href="../valyuta/">Valyuta məzənnəsi</a> · <a href="../cedvel/">Premyer Liqa cədvəli</a> · <a href="../tixac/">Tıxac və yollar</a></p><noscript>Tam sayt üçün JavaScript-i aktiv edin.</noscript></main>
    </div>
  </body>
</html>
"""

def section_page(slug, label, desc, articles, limit=30):
    items = [a for a in articles if a.get("category") == slug and (a.get("lang") or "az") == "az"]
    items.sort(key=lambda a: a.get("publishedAt") or "", reverse=True)
    lis = "".join(
        f'<li><a href="{_xml(a.get("sourceUrl"))}" rel="noopener">{_xml(a.get("title"))}</a> <small>{_xml(a.get("source"))}</small></li>'
        for a in items[:limit])
    url = f"{SITE}bolme/{slug}/"
    return _page_html(slug, label, desc, f"<ul>{lis}</ul>")

def _page_html(slug, label, desc, items):
    url = f"{SITE}bolme/{slug}/"
    return (_SECTION_HTML.replace("__ITEMS__", items).replace("__LABEL__", _xml(label)).replace("__DESC__", _xml(desc))
            .replace("__URL__", url).replace("__SITE__", SITE).replace("__SLUG__", slug))

# Xidmət səhifələri: axtarış sistemi hash ünvanını ayrıca səhifə saymır. bolme/ altındadır, çünki pipeline.sh main-ə bu qovluğu yazır.
SERVICE_PAGES = [
    ("valyuta", "Valyuta məzənnəsi", "Dollar, avro, rubl və lirənin manatla bugünkü məzənnəsi, neft və qızıl qiyməti"),
    ("cedvel", "Premyer Liqa cədvəli", "Azərbaycan Premyer Liqasının turnir cədvəli"),
    ("tixac", "Tıxac və yollar", "Azərbaycanda yol vəziyyəti, qəza və bağlanan yollar haqqında son xəbərlər"),
]
_ROAD_RX = re.compile(r"tıxac|qəza(?!lı)|yol polisi|nəqliyyatın hərəkət|yol bağlı|avtomobil yol|(?:^|[^\w])(?:BNA|DYP)(?:[^\w]|$)", re.I)

def _table(head, rows):
    cells = lambda row, tag: "".join(f"<{tag}>{_xml('' if c is None else str(c))}</{tag}>" for c in row)
    body = "".join("<tr>" + cells(r, "td") + "</tr>" for r in rows)
    return "<table><thead><tr>" + cells(head, "th") + "</tr></thead><tbody>" + body + "</tbody></table>"

def service_body(slug, articles):
    if slug == "valyuta":
        items = _read_json(MARKETS_FILE, {}).get("items") or []
        rows = [(i.get("label"), f'{float(i["value"]):.{i.get("dec", 2)}f} {i.get("unit") or ""}'.strip(), i.get("src") or "", i.get("asOf") or (i.get("at") or "")[:10])
                for i in items if i.get("value") is not None]
        return _table(("Ad", "Qiymət", "Mənbə", "Tarix"), rows) if rows else "<p>Məzənnə məlumatı hazırda yoxdur.</p>"
    if slug == "cedvel":
        fb = _read_json(FOOTBALL_FILE, {})
        rows = [(t.get("pos"), t.get("team"), t.get("p"), t.get("w"), t.get("d"), t.get("l"), t.get("gf"), t.get("ga"), t.get("pts")) for t in fb.get("table") or []]
        title = f'<h2>{_xml(fb.get("league"))} {_xml(fb.get("season"))}</h2>' if fb.get("league") else ""
        return title + _table(("#", "Komanda", "O", "Q", "H", "M", "Vurulan", "Buraxılan", "Xal"), rows) if rows else "<p>Cədvəl hazırda yoxdur.</p>"
    road = [a for a in articles if (a.get("lang") or "az") == "az" and _ROAD_RX.search(a.get("title") or "")]
    road.sort(key=lambda a: a.get("publishedAt") or "", reverse=True)
    lis = "".join(f'<li><a href="{_xml(a.get("sourceUrl"))}" rel="noopener">{_xml(a.get("title"))}</a> <small>{_xml(a.get("source"))}</small></li>' for a in road[:20])
    return f'<p><a href="../../#/tixac">Canlı tıxac xəritəsi</a></p><ul>{lis}</ul>'

def write_sections(articles):
    for slug, label, desc in SECTIONS:
        d = SECTIONS_DIR / slug
        d.mkdir(parents=True, exist_ok=True)
        _write_atomic(d / "index.html", section_page(slug, label, desc, articles), encoding="utf-8")
    for old, new in SECTION_ALIASES.items():
        d = SECTIONS_DIR / old
        d.mkdir(parents=True, exist_ok=True)
        _write_atomic(d / "index.html", f'<!doctype html><html lang="az"><head><meta charset="UTF-8" /><link rel="canonical" href="{SITE}bolme/{new}/" />'
                      f'<meta http-equiv="refresh" content="0;url=../{new}/" /><title>8ulduz</title></head><body><a href="../{new}/">Bölməyə keç</a></body></html>\n', encoding="utf-8")
    for slug, label, desc in SERVICE_PAGES:
        try:  # bir xidmətin zədəli faylı bölmə səhifələrini və sitemap-i saxlamasın
            d = SECTIONS_DIR / slug
            d.mkdir(parents=True, exist_ok=True)
            _write_atomic(d / "index.html", _page_html(slug, label, desc, service_body(slug, articles)), encoding="utf-8")
        except Exception as e:
            print("  ! xidmət səhifəsi:", slug, type(e).__name__, e)
    print(f"Bölmə səhifələri: {len(SECTIONS)}")

def write_sitemap():
    today = datetime.datetime.now(datetime.timezone.utc).date().isoformat()
    locs = [SITE] + [f"{SITE}bolme/{slug}/" for slug, _l, _d in [*SECTIONS, *SERVICE_PAGES]]
    body = ['<?xml version="1.0" encoding="UTF-8"?>',
            '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">']
    for loc in locs:
        body.append(f"<url><loc>{_xml(loc)}</loc><lastmod>{today}</lastmod><changefreq>hourly</changefreq></url>")
    body.append("</urlset>\n")
    _write_atomic(SITEMAP_FILE, "".join(body), encoding="utf-8")

def write_robots():
    _write_atomic(ROBOTS_FILE, 
        "User-agent: *\nDisallow: /tests/\nDisallow: /docs/\nDisallow: /android/\nDisallow: /.github/\nDisallow: /updater.py\n"
        "Disallow: /reader_content.py\nDisallow: /content_policy.py\nDisallow: /README.md\nAllow: /\n\nSitemap: " + SITE + "sitemap.xml\n",
        encoding="utf-8")

def write_public():
    try:
        articles = json.loads(OUT_FILE.read_text(encoding="utf-8")).get("articles") or []
    except Exception:
        articles = []
    articles, _ = content_policy.enforce(articles)  # feed.xml və bölmə səhifələri də qapıdan keçir
    write_feed(articles)
    write_sections(articles)
    write_sitemap()
    write_robots()

_OG_META = re.compile(r"<meta\b[^>]*>", re.I)
_OG_KEY = re.compile(r"""(?:property|name)\s*=\s*["']([^"']+)["']""", re.I)
_OG_CONTENT = re.compile(r"""content\s*=\s*["']([^"']+)["']""", re.I)
_OG_NAMES = {"og:image", "og:image:url", "twitter:image", "twitter:image:src"}

_LD_IMG = re.compile(r'"image"\s*:\s*(?:\{[^}]*?"url"\s*:\s*)?"(https?://[^"]+)"', re.I)
_IMG_SRC = re.compile(r'<link[^>]+rel=["\']image_src["\'][^>]+href=["\']([^"\']+)', re.I)

def _og_from_html(raw, base):
    text = raw.decode("utf-8", "replace")
    cands = []
    for tag in _OG_META.findall(text):
        km = _OG_KEY.search(tag)
        if not km or km.group(1).lower() not in _OG_NAMES:
            continue
        cm = _OG_CONTENT.search(tag)
        if cm:
            cands.append(html.unescape(cm.group(1)))
    m = _IMG_SRC.search(text)
    if m:
        cands.append(html.unescape(m.group(1)))
    m = _LD_IMG.search(text)
    if m:
        cands.append(html.unescape(m.group(1)))
    for c in cands:
        img = _abs_img(c, base)
        if img and not _is_generic_img(img):
            return img
    return ""

def _fetch_og(url):
    try:
        req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "text/html,application/xhtml+xml"})
        with urllib.request.urlopen(req, timeout=6) as r:
            ctype = (r.headers.get("Content-Type") or "").lower()
            if ctype and "html" not in ctype and "xml" not in ctype:
                return ""
            return _og_from_html(r.read(90000), url)
    except Exception:
        return ""

# ---------------------------------------------------------------- tarixsiz lentlər ---
# Bəzi lentlər (İki Sahil) pubDate vermir. Əvvəl belə elementlər hər dövrədə «indi» tarixi alırdı:
# limitdən kənarda qalan yazılar növbəti dövrədə yenidən «yeni» sayılır, 40 köhnə yazı hər 4 dəqiqədən bir
# «N dəqiqə əvvəl» ilə hər bölmənin başına və «Son dəqiqə»yə düşürdü. İndi dərc vaxtı məqalə səhifəsindən
# (JSON-LD datePublished, article:published_time, <time datetime>) oxunur, ünvandakı /2026/10/28/ ipucu köhnə
# yazıları sorğusuz atır, nəticə data/dates.json-da saxlanır ki, hər keçid bir dəfə sorğulansın.
_URL_DATE = re.compile(r"/(20\d\d)[/-](\d\d)[/-](\d\d)(?=[/-]|$)")
_LD_DATE = re.compile(r'"datePublished"\s*:\s*"([^"]+)"')
_DATE_META = {"article:published_time", "og:published_time", "pubdate", "publishdate", "publish-date", "publish_date",
              "date", "dc.date", "dc.date.issued", "sailthru.date", "parsely-pub-date"}
_TIME_TAG = re.compile(r"""<time\b[^>]*\bdatetime\s*=\s*["']([^"']+)["']""", re.I)

def url_date_hint(*urls):
    """Ünvandakı /2026/10/28/ hissəsi (keçid və ya şəkil) — köhnə yazını sorğusuz atmaq və ehtiyat tarix üçün."""
    for u in urls:
        m = _URL_DATE.search(u or "")
        if m:
            try:
                return datetime.date(int(m.group(1)), int(m.group(2)), int(m.group(3)))
            except ValueError:
                continue
    return None

def _page_dt(s, now=None):
    s = html.unescape(str(s or "")).strip()
    if not s:
        return ""
    try:
        dt = datetime.datetime.fromisoformat(s.replace("Z", "+00:00"))
    except ValueError:
        try:
            dt = email.utils.parsedate_to_datetime(s)
        except Exception:
            dt = None
    if dt is None:
        return ""
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=BAKU)  # zonasız yazı: Bakı vaxtı
    now = now or datetime.datetime.now(datetime.timezone.utc)
    if dt.year < 2000 or dt > now + datetime.timedelta(minutes=5):
        return ""
    return _norm_iso(dt)

def parse_page_date(raw, now=None):
    """Məqalə səhifəsindən dərc vaxtı (UTC ISO) və ya boş sətir."""
    text = raw.decode("utf-8", "replace") if isinstance(raw, bytes) else str(raw or "")
    cands = [m.group(1) for m in _LD_DATE.finditer(text)]
    for tag in _OG_META.findall(text):
        km = _OG_KEY.search(tag)
        if not km or km.group(1).lower() not in _DATE_META:
            continue
        cm = _OG_CONTENT.search(tag)
        if cm:
            cands.append(cm.group(1))
    cands.extend(m.group(1) for m in _TIME_TAG.finditer(text))
    for c in cands:
        iso = _page_dt(c, now)
        if iso:
            return iso
    return ""

def _fetch_page_date(url):
    try:
        req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "text/html,application/xhtml+xml"})
        with urllib.request.urlopen(req, timeout=6) as r:
            ctype = (r.headers.get("Content-Type") or "").lower()
            if ctype and "html" not in ctype and "xml" not in ctype:
                return ""
            return parse_page_date(r.read(150000))
    except Exception:
        return ""

def load_dates():
    try:
        d = json.loads(DATES_FILE.read_text(encoding="utf-8"))
        return d if isinstance(d, dict) else {}
    except Exception:
        return {}

def save_dates(cache, now=None, keep_days=10, limit=1500):
    """Keş böyüməsin: 10 gündən köhnə və artıq qeydlər atılır (köhnə yazılar onsuz da ünvan ipucu ilə atılır)."""
    now = now or datetime.datetime.now(datetime.timezone.utc)
    cut = _norm_iso(now - datetime.timedelta(days=keep_days))
    rows = sorted(((k, v) for k, v in cache.items() if isinstance(v, str) and v >= cut),
                  key=lambda kv: kv[1], reverse=True)[:limit]
    try:
        OUT_DIR.mkdir(exist_ok=True)
        _write_atomic(DATES_FILE, json.dumps(dict(rows), ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    except Exception as e:
        print("  ! tarix keşi:", type(e).__name__)

def undated_date(it, cache, budget, now=None, max_age_days=5):
    """Lentdə tarixi olmayan element üçün (ISO, qalan büdcə). Boş ISO — element bu dövrədə buraxılır.
    Sıra: ünvan tarixi köhnədirsə atılır; keş; səhifə sorğusu (büdcə daxilində); ünvan tarixi; ilk görülmə vaxtı."""
    now = now or datetime.datetime.now(datetime.timezone.utc)
    link = it.get("link") or ""
    hint = url_date_hint(link, it.get("image") or "")
    if hint and hint < (now - datetime.timedelta(days=max_age_days)).date():
        return "", budget
    if link in cache:
        return cache[link], budget
    if budget <= 0:
        return "", budget  # büdcə bitdi: növbəti dövrədə
    iso = _fetch_page_date(link)
    if not iso and hint:
        hinted = datetime.datetime(hint.year, hint.month, hint.day, 12, 0, tzinfo=BAKU)
        iso = _norm_iso(min(hinted, now))
    if not iso:
        iso = _norm_iso(now)  # ilk görülmə vaxtı — bir dəfə, sonra keşdən
    cache[link] = iso
    return iso, budget - 1

def fill_og_images(articles, limit=120):
    """Şəkilsiz xəbərlər üçün səhifənin og:image ünvanı. Hər URL bir dəfə sorğulanır."""
    try:
        cache = json.loads(OG_FILE.read_text(encoding="utf-8"))
        if not isinstance(cache, dict):
            cache = {}
    except Exception:
        cache = {}
    previous_meta = cache.pop("_meta", {})
    retry_after = previous_meta.get("retryAfter", {}) if isinstance(previous_meta, dict) else {}
    now_ts = datetime.datetime.now(datetime.timezone.utc).timestamp()
    for k in [k for k, v in cache.items() if v and _is_generic_img(v)]:
        cache[k] = ""  # əvvəlki dövrələrdən qalan ümumi (loqo) şəkillər: yenidən sorğulanmasın, amma istifadə də olunmasın
    # Eyni şəkil 3+ fərqli səhifədə og:image kimi gəlirsə, bu, saytın loqosudur (marja.az, lent.az) — xəbərin şəkli deyil
    freq = {}
    for v in cache.values():
        if v:
            freq[v] = freq.get(v, 0) + 1
    for a in articles:
        if a.get("imageUrl"):
            freq[a["imageUrl"]] = freq.get(a["imageUrl"], 0) + 1
    for k, v in list(cache.items()):
        if v and freq.get(v, 0) >= 3:
            cache[k] = ""
    todo = []
    for a in articles:
        url = a.get("sourceUrl") or ""
        if not url or a.get("imageUrl"):
            continue
        if url in cache:
            if cache[url]:
                a["imageUrl"] = cache[url]
                continue
            # Temporary network failures must not hide photos forever.
            if retry_after.get(url, 0) > now_ts:
                continue
        todo.append(a)
    batch, found, err = todo[:limit], [], ""
    try:
        if batch:
            with ThreadPoolExecutor(max_workers=12) as ex:
                found = list(ex.map(lambda a: _fetch_og(a.get("sourceUrl") or ""), batch))
            for img in found:
                if img:
                    freq[img] = freq.get(img, 0) + 1
            for a, img in zip(batch, found):
                if img and freq.get(img, 0) >= 3:
                    img = ""  # bu dövrədə də eyni şəkil təkrarlanır: loqo
                cache[a["sourceUrl"]] = img or ""
                if img:
                    retry_after.pop(a["sourceUrl"], None)
                else:
                    retry_after[a["sourceUrl"]] = now_ts + 6 * 3600
                if img:
                    a["imageUrl"] = img
    except Exception as e:
        err = f"{type(e).__name__}: {str(e)[:80]}"
        print("  ! og:image:", err)
    keep = {a.get("sourceUrl") for a in articles if a.get("sourceUrl")}
    trimmed = {k: v for k, v in cache.items() if k in keep}
    # Diaqnostika (loglara girişsiz): neçə xəbər şəkilsizdir, bu dövrədə neçəsi sorğulandı və tapıldı
    trimmed["_meta"] = {"at": datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds"),
                        "todo": len(todo), "batch": len(batch), "found": sum(1 for i in found if i), "error": err,
                        "retryAfter": {k: v for k, v in retry_after.items() if k in keep and v > now_ts}}
    try:
        OUT_DIR.mkdir(exist_ok=True)
        _write_atomic(OG_FILE, json.dumps(trimmed, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    except Exception as e:
        print("  ! og keşi:", type(e).__name__)
    return len(batch)

def write_status(ok=True, successful=0, total=0, stats=None):
    """Son cəhd və son uğur ayrıdır; uğursuz cəhd köhnə xəbəri təzə göstərmir. stats: seçim sayları (diaqnostika)."""
    now = datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds")
    try:
        previous = json.loads(STATUS_FILE.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        previous = {}
    OUT_DIR.mkdir(exist_ok=True)
    _write_atomic(STATUS_FILE, json.dumps({"checkedAt": now if ok else previous.get("checkedAt"),
                                       "attemptedAt": now, "ok": ok,
                                       "successfulSources": successful, "totalSources": total,
                                       "degraded": ok and total - successful > total * FEED_PAUSE_MAX_SHARE, "stats": stats or previous.get("stats")}, ensure_ascii=False,
                                       separators=(",", ":")), encoding="utf-8")
    print(f"Yoxlama: {now}")

# --------------------------------------------------------------------- main ---
def removed_source(item):
    if str(item.get('source') or item.get('name') or '').casefold() in ('azadlıq', 'azadliq', 'azadliq.org'):
        return True
    try:
        host = (urllib.parse.urlparse(item.get('sourceUrl') or item.get('url') or '').hostname or '').lower()
        return host == 'azadliq.org' or host.endswith('.azadliq.org')
    except ValueError:
        return False


def prune_removed_sources(articles):
    return [{**a, 'alts': [alt for alt in a.get('alts', []) if not removed_source(alt)]} if 'alts' in a else a
            for a in articles if not removed_source(a)]


def main(fast=False):
    marks, tick = {}, time.time()
    def mark(name):
        nonlocal tick
        marks[name] = round(time.time() - tick, 1)
        tick = time.time()
        if fast:
            print("  ·", name, marks[name], flush=True)
    try:
        old = json.loads(OUT_FILE.read_text(encoding="utf-8"))["articles"]
    except Exception:
        old = []
    prev_articles = [dict(a) for a in old]
    old = prune_removed_sources(old)
    old = [a for a in old if not is_junk(a.get("sourceUrl", ""))]
    old = [a for a in old if not is_negative_about_leadership(a.get("title", ""), a.get("summary", ""), a.get("source"))]
    hints = {f[0]: f[3] for f in FEEDS}
    hints["AZƏRTAC (Regionlar)"] = "Bölgələr"
    # Rəsmi səhifələr (prezident, birinci xanım, AZƏRTAC Regionlar) əvvəlcədən: Regionlar səhifəsindəki keçidlər
    # lentdə də gəlsə Bölgələr sayılır
    mark("oldClean")
    if fast:
        results, off_items, off_errors = collect_fast()
        mark("collect")
    else:
        off_items, off_errors = official_items()
    region_links = {t[4]["link"] for t in off_items if t[2] == "Bölgələr"}
    region_desc = {}
    # Təsnifat qaydaları iş ərzində dəyişmir: sürətli dövrədə köhnə xəbərlər yalnız işin ilk dövrəsində yenidən oxunur.
    relabel = not fast or not RELABEL_MARK.exists()
    if fast:
        CACHE_DIR.mkdir(parents=True, exist_ok=True)
        RELABEL_MARK.touch()
    for a in old if relabel else []:
        if a.get("source") == "AZƏRTAC Regionlar":  # köhnə saxta mənbə adı (lent ümumi lentin eynisi idi)
            a["source"] = "AZƏRTAC"
        # köhnə xəbərlərin dili yoxdursa — avtomatik təyin et (süzgəcin düzgün işləməsi üçün)
        if not a.get("lang") or a.get("lang") == "az":
            a["lang"] = detect_lang(a.get("title", ""), a.get("summary", ""), a.get("lang") or "")
        # köhnə xəbərləri də yenilənmiş qaydalarla yenidən kateqoriyalaşdır
        lbl = label_for(a.get("title", ""), a.get("summary", ""), a["lang"],
                        "Bölgələr" if a.get("sourceUrl") in region_links else hints.get(a.get("source")),
                        a.get("source") in WORLD_SOURCES)
        if a.get("source") in ("Prezident.az", "Mehriban Əliyeva"):
            lbl = "Prezident"
        a["category"] = SLUGS.get(lbl, "gundem")
    old = [a for a in old if not foreign_about_azerbaijan(a.get("source"), a.get("category"), a.get("title", ""), a.get("summary", ""))]
    for a in old:
        a["sourceUrl"] = fix_source_link(a.get("sourceUrl"))
        for alt in a.get("alts") or []:
            alt["sourceUrl"] = fix_source_link(alt.get("sourceUrl"))
        stable = fixed_source_date(a.get("sourceUrl"))
        if stable:
            a["publishedAt"] = stable
        dt = _parse_dt(a.get("publishedAt"))
        if dt is not None:
            a["publishedAt"] = _norm_iso(dt)
        for alt in a.get("alts") or []:
            stable = fixed_source_date(alt.get("sourceUrl"))
            if stable:
                alt["publishedAt"] = stable
            adt = _parse_dt(alt.get("publishedAt"))
            if adt is not None:
                alt["publishedAt"] = _norm_iso(adt)
    now_utc = datetime.datetime.now(datetime.timezone.utc)
    cutoff, cutoff_prez = now_utc - datetime.timedelta(days=5), now_utc - datetime.timedelta(days=60)
    old = [a for a in old if (_parse_dt(a.get("publishedAt")) or now_utc) >= (cutoff_prez if a.get("category") == "prezident" else cutoff)]
    seen = {a["sourceUrl"] for a in old}
    if fast:  # başqa xəbərin mənbəsi kimi birləşmiş keçid yenidən «yeni» sayılmasın
        seen |= {alt.get("sourceUrl") for a in old for alt in a.get("alts") or []}
    old_by_url = {a["sourceUrl"]: a for a in old}
    new_items, errors, empty = [], [], []
    # Sürətli dövrə köhnə xəbərlə lenti geri doldurmur: lentdəki ən köhnədən köhnə element emal olunmur.
    regular = [_parse_dt(a.get("publishedAt")) for a in old if a.get("category") != "prezident"]
    floor = min([d for d in regular if d], default=None) if fast and len(regular) >= 300 else None
    # Sürətli dövrədə səhifə sorğusu yoxdur: tarixi tapılmamış elementlər yavaş prosesə ötürülür.
    budget = 0 if fast else DATE_LOOKUPS
    dates, lookups, undated, unresolved = load_dates(), budget, 0, []
    source_rows = []
    if not fast:
        with ThreadPoolExecutor(max_workers=WORKERS) as ex:
            results = list(ex.map(fetch_feed, FEEDS))  # sıra FEEDS ilə eynidir
    # Əvvəlcə siyahıda olan, lakin «ilk görülmə» vaxtı ilə qalmış tarixsiz xəbərlər (tarix keşi yaranana qədər
    # yığılanlar): büdcəni onlar alır, yoxsa 2000 elementlik lentdə növbə onlara heç çatmır və saatlarla
    # «N saat əvvəl» kimi bölmələrin başında qalırlar. Səhifə tarixi tapılanda köhnə qeydin vaxtı düzəldilir.
    # Tarixi etibarsız lent: elementləri götürülmür, əvvəl düşənlər də çıxır. Lent qoşulu qalır, tarix düzələndə özü qayıdır.
    bulk = {source for source, items, err, _ in results if not err and bulk_dated(items)}
    if bulk:
        print("  ⊘ tarixi etibarsız lent:", ", ".join(sorted(bulk)), flush=True)
        old = [a for a in old if a.get("source") not in bulk]
        for a in old:
            if a.get("alts"):
                a["alts"] = [alt for alt in a["alts"] if alt.get("source") not in bulk]
    # Limiti dolmuş mənbənin kəsiləcək köhnə elementləri hər dəqiqə yenidən emal olunmasın.
    source_floor, by_source = {}, {}
    for a in old if fast else []:
        by_source.setdefault(a.get("source"), []).append(_parse_dt(a.get("publishedAt")))
    for name, published in by_source.items():
        cap = source_cap(name)
        published = sorted((d for d in published if d), reverse=True)
        if len(published) >= cap:
            source_floor[name] = published[cap - 1]
    for _, items, err, _ in results:
        for it in items if not err else []:
            it["link"] = fix_source_link(it.get("link"))
            if not it.get("pubDate") and it.get("link") in old_by_url:
                iso, lookups = undated_date(it, dates, lookups)
                if iso:
                    old_by_url[it["link"]]["publishedAt"] = iso
    for (source, url, dlang, hint), (_, items, err, used_url) in zip(FEEDS, results):
        source_rows.append({"name": source, "url": used_url or url, "count": 0 if err else len(items),
                            "error": err or ("cavab gecikir" if fast and source in LATE_FEEDS else None)})
        if err:
            errors.append(f"{source}: {err}")
            continue
        if not items:
            empty.append(source)
        for it in items if source not in bulk else []:
            try:
                if it["link"] in seen or is_junk(it["link"]):
                    continue
                if floor and it.get("pubDate") and _older_than(it["pubDate"], floor):
                    continue
                if source in source_floor and it.get("pubDate") and _older_than(it["pubDate"], source_floor[source]):
                    continue
                if it["link"] in region_links:  # Regionlar səhifəsindən gələcək; lentin xülasəsi ona verilir
                    region_desc[it["link"]] = it.get("description") or ""
                    continue
                seen.add(it["link"])
                if not it.get("pubDate"):
                    iso, lookups = undated_date(it, dates, lookups)
                    if not iso:
                        unresolved.append({"link": it.get("link"), "image": it.get("image")})
                        continue
                    it = dict(it, pubDate=iso)
                    undated += 1
                if is_negative_about_leadership(it["title"], it["description"], source):
                    continue
                art = make_article(it, source, dlang, hint)
                # xülasə kartda 220 simvola qısalır; qayda tam təsviri oxuyur
                if foreign_about_azerbaijan(source, art["category"], art["title"], it.get("description") or art["summary"]):
                    continue
                new_items.append(art)
            except Exception as e:
                errors.append(f"{source} (element): {type(e).__name__}")
    errors.extend(off_errors)
    source_rows.extend(official_source_rows(off_items, off_errors))
    for source, dlang, hint, force, it in off_items:
        try:
            if it["link"] in seen or is_junk(it["link"]):
                continue
            seen.add(it["link"])
            if is_negative_about_leadership(it["title"], it["description"], source):
                continue
            if hint == "Bölgələr" and not it.get("description"):
                it = dict(it, description=region_desc.get(it["link"], ""))
            new_items.append(make_article(it, source, dlang, hint, force_label=force))
        except Exception as e:
            errors.append(f"{source} (rəsmi): {type(e).__name__}")
    if fast:
        _save_cache(UNDATED_FILE, unresolved[:300])
    else:
        save_dates(dates)
    mark("items")
    new_items.sort(key=lambda a: a["publishedAt"], reverse=True)
    old = sorted(old, key=lambda a: a.get("publishedAt", ""), reverse=True)
    uniq, dseen = [], set()
    per_src, world_count, sport_count = {}, 0, 0
    # Tarixə görə birgə sıralama. Əvvəl «yeni» (bu dövrədə ilk dəfə görülən) xəbərlər köhnələrdən qabaq gəlirdi;
    # limitdən kənarda qalan köhnə xəbərlər növbəti dövrədə yenidən «yeni» sayılıb siyahını hər dəfə dəyişirdi
    # (813-dən yalnız ~50 xəbər dövrədən dövrəyə qalırdı; og keşi və qruplar daim sıfırlanırdı).
    for a in sorted(new_items + old, key=lambda x: x.get("publishedAt") or "", reverse=True):
        if a["sourceUrl"] in dseen:
            continue
        n, is_sport = per_src.get(a.get("source"), 0), a.get("source") in content_policy.SPORT_SOURCES
        is_world = a.get("source") in WORLD_SOURCES and not is_sport
        if n >= source_cap(a.get("source")) or (is_world and world_count >= MAX_WORLD) or (is_sport and sport_count >= MAX_WORLD_SPORT):
            continue
        per_src[a.get("source")] = n + 1
        world_count += is_world
        sport_count += is_sport
        dseen.add(a["sourceUrl"]); uniq.append(a)
    # Prezident bölməsi ümumi limitdən asılı deyil: rəsmi xronika (60 gün) həmişə saxlanılır.
    # Əvvəl yalnız 800-dən kənarda qalanlar əlavə olunurdu; siyahı 800-dən qısa olanda heç nə əlavə olunmurdu.
    prez_items = [a for a in uniq if a["category"] == "prezident"][:120]
    articles = [a for a in uniq if a["category"] != "prezident"][:FAST_MAX_ITEMS if fast else MAX_ITEMS] + prez_items
    stats = {"old": len(old), "new": len(new_items), "uniq": len(uniq), "prez": len(prez_items), "articles": len(articles),
             "undated": undated, "dateLookups": budget - lookups}
    mark("select")
    before_groups = len(articles)
    articles = apply_groups(articles) if fast else group_duplicates(articles)
    for a in articles if bulk else []:
        if a.get("alts"):
            a["alts"] = [alt for alt in a["alts"] if alt.get("source") not in bulk]
    stats["grouped"] = before_groups - len(articles)
    mark("group")
    # Eyni şəkil 3 və daha çox xəbərdə təkrarlanırsa, o, saytın ümumi lövhəsidir — xəbərin şəkli sayılmır
    img_count = {}
    for a in articles:
        if a.get("imageUrl"):
            img_count[a["imageUrl"]] = img_count.get(a["imageUrl"], 0) + 1
    for a in articles:
        u = a.get("imageUrl")
        if u and (img_count.get(u, 0) >= 3 or _is_generic_img(u)):
            a["imageUrl"] = None
        if not a.get("imageUrl"):
            for alt in a.get("alts") or []:
                if alt.get("imageUrl") and img_count.get(alt["imageUrl"], 0) < 3 and not _is_generic_img(alt["imageUrl"]):
                    a["imageUrl"] = alt["imageUrl"]
                    break
    if fast:
        apply_og_cache(articles)
    else:
        try:
            n_og = fill_og_images(articles)
            if n_og:
                print(f"og:image sorğusu: {n_og}")
        except Exception as e:
            print("  ! og:image:", type(e).__name__)
    # QIRMIZI XƏTT 2: yazılan hər şey bu qapıdan keçir.
    if fast:  # kəsilən xəbərlər görünsün: səhvən kəsilən mənbə loglardan dərhal tapılır
        for a in articles:
            reason = content_policy.violation(a)
            if reason:
                print(f"  ⊘ {reason}: {a.get('source')} {a.get('sourceUrl')}", flush=True)
    articles, dropped = content_policy.enforce(articles)
    stats["articles"], stats["policyDropped"] = len(articles), dropped
    save_sources(source_rows)
    successful = sum(1 for row in source_rows if not row.get("error") and row.get("count", 0) > 0)
    result = {"ok": successful > 0 and bool(articles), "successful": successful, "total": len(source_rows), "stats": stats}
    if not successful:
        print("Heç bir xəbər mənbəyi işləmədi — əvvəlki xəbər lenti saxlanıldı")
        return result
    if not articles:
        print("Xəbər yoxdur — fayl dəyişdirilmədi"); return result
    write_latest(articles, prev_articles)
    mark("final")
    stats["timings"] = marks
    if articles == prev_articles:
        print(f"Dəyişiklik yoxdur ({len(FEEDS) - len(errors)}/{len(FEEDS)} mənbə)")
        for e in errors:
            print("  !", e)
        return result
    data = {
        "updatedAt": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "count": len(articles),
        "articles": articles,
    }
    OUT_DIR.mkdir(exist_ok=True)
    # yığcam JSON: repo ölçüsünün böyüməsini azaldır
    _write_atomic(OUT_FILE, json.dumps(data, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    if not fast:
        try:
            retire_reader()
        except Exception as e:
            print('  ! audio mətn:', type(e).__name__)
    ok = len(FEEDS) - len(errors) - len(empty)
    print(f"Mənbə işlədi: {ok}/{len(FEEDS)} | Yeni: {len(new_items)} | Ümumi: {len(articles)}")
    for e in errors:
        print("  !", e)
    for e in empty:
        print("  ∅", e, "(boş lent)")
    return result

def run_fast():
    """Bir sürətli dövrə: lentlər, xəbər seçimi, status. Xəta olsa da status yazılır ki, lentin dayandığı görünsün."""
    started, result = time.time(), {"ok": False, "successful": 0, "total": 0, "stats": {}}
    try:
        result = main(fast=True)
    except Exception as e:
        print("  ! xəbər:", type(e).__name__, e)
    stats = dict(result.get("stats") or {}, cycleSeconds=round(time.time() - started, 1))
    write_status(result["ok"], result["successful"], result["total"], stats)
    print(f"Sürətli dövrə: {stats['cycleSeconds']} san {stats.get('timings')}")
    return 0 if result["ok"] else 1


def run():
    if "--fast" in sys.argv:
        return run_fast()
    if "--slow" in sys.argv:
        return slow_cycle()
    news_ok = True
    result = {"successful": 0, "total": 0}
    if "--no-markets" not in sys.argv:
        try:
            update_markets()
        except Exception as e:
            print("  ! bazar:", type(e).__name__)
    if "--markets-only" not in sys.argv:
        try:
            result = main()
            news_ok = result["ok"]
        except Exception as e:
            news_ok = False
            print("  ! xəbər:", type(e).__name__, e)
        if "--no-social" not in sys.argv:
            try:
                update_social()
            except Exception as e:
                print("  ! sosial:", type(e).__name__)
            try:
                update_video()
            except Exception as e:
                print("  ! video:", type(e).__name__)
            try:
                update_football()
            except Exception as e:
                print("  ! futbol:", type(e).__name__)
            try:
                update_sports()
            except Exception as e:
                print("  ! dünya liqaları:", type(e).__name__)
        write_status(news_ok, result["successful"], result["total"], result.get("stats"))
        if news_ok:
            try:
                write_public()
            except Exception as e:
                print("  ! seo:", type(e).__name__, e)
    return 0 if news_ok else 1

if __name__ == "__main__":
    code = run()
    sys.stdout.flush()
    os._exit(code)  # vaxtı bitmiş lent axınları prosesi saxlamasın
