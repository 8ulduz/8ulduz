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
import json, re, pathlib, hashlib, datetime, email.utils, html, sys
import urllib.request, urllib.parse
import xml.etree.ElementTree as ET
from concurrent.futures import ThreadPoolExecutor

# (ad, url[, kateqoriya ipucu]) — Azərbaycan mənbələri, default dil "az"
# AZƏRTAC, Report və News.az GitHub runner IP-lərindən 403 alır.
# Birbaşa lent alınmayanda Google News RSS (və lazım olanda Telegram önizləməsi) ehtiyatdır.
AZ_FEEDS = [
    ("AZƏRTAC Regionlar", "https://azertag.az/rss?cat=regionlar", "Bölgələr"),  # əsas lentdən əvvəl: eyni keçid Bölgələr sayılsın
    ("AZƏRTAC",      "https://azertag.az/rss"),
    ("APA",          "https://apa.az/rss"),
    ("APA Sport",    "https://apasport.az/rss", "İdman"),
    ("Sportinfo",    "https://www.sportinfo.az/rss/", "İdman"),
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
    ("525.az",       "https://525.az/rss_goster.php", "Mədəniyyət"),
    ("İki Sahil",    "https://ikisahil.az/rss"),
    ("Femida.az",    "https://femida.az/rss.xml"),
    ("Ordu.az",      "https://ordu.az/rss.xml", "Siyasət"),
    ("Azpolitika.info", "https://azpolitika.info/rss", "Siyasət"),
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
    ("Azadlıq",      "https://www.azadliq.org/rss/"),
    ("Meydan TV",    "https://www.meydan.tv/feed/"),
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
]
FEEDS = [(f[0], f[1], "az", f[2] if len(f) > 2 else None) for f in AZ_FEEDS] + \
        [(f[0], f[1], f[2], f[3] if len(f) > 3 else None) for f in WORLD_FEEDS]
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
]
CATEGORIES = {
    "Prezident": [],  # xüsusi qayda ilə hesablanır (categorize-ə baxın)
    "İdman": IDMAN_WORDS,
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
                   "sinema", "kitap", "roman", "sanat", "sergi", "concert", "culture", "albüm", "oyuncu",
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
              "ukraine", "gaza", "israel", "russia", "china", "iran", "trump", "nato", "un ", "husi", "moskva", "paşinyan", "uqanda", "ebola", "türkiyədə", "kyrgyzstan", "freedom house"],
}
# İdman bölməsi gücləndirilib: xallar 2 qat sayılır
BOOST = {"İdman": 2, "Prezident": 3, "Təhsil": 1.5, "Səhiyyə": 1.5, "Bölgələr": 1.5}
SLUGS = {"Prezident": "prezident", "Gündəm": "gundem", "Siyasət": "siyaset", "Cəmiyyət": "cemiyyet",
         "İqtisadiyyat": "iqtisadiyyat", "Dünya": "dunya", "İdman": "idman", "Mədəniyyət": "medeniyyet",
         "Həyat": "heyat", "Texnologiya": "texnologiya", "Təhsil": "tehsil", "Səhiyyə": "sehiyye", "Bölgələr": "bolgeler"}
DOUBLE = {"iran", "rusiya", "çin", "fransa", "israil", "ukrayna", "abş", "ingiltərə", "almaniya",
          "türkiyə", "ermənistan", "gürcüstan"}
FALLBACK = "Gündəm"
ROOT = pathlib.Path(__file__).parent
OUT_DIR = ROOT / "data"
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
SITE = "https://8ulduz.github.io/8ulduz/"
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
DATE_LOOKUPS = 30     # tarixsiz lent elementləri üçün bir dövrədə ən çox səhifə sorğusu
TIMEOUT = 10
WORKERS = 16
UA = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36 8ulduz-bot"

def norm_az(s):
    return s.lower().replace("i̇", "i")

def detect_lang(title, desc, default):
    """Dil təyini: kiril→ru, 'ə'→az (türkdə yoxdur), ı/ğ/İ→tr, əks halda mənbə dili.
    Azərbaycan mənbələrində ə-siz qısa başlıqlar türkcə sayılmasın deyə default "az" üstündür."""
    blob = title + " " + desc
    if re.search(r"[а-яА-Я]", blob):
        return "ru"
    if "ə" in blob or "Ə" in blob:
        return "az"
    if default == "az":
        # AZ mənbəsində ə-siz, lakin ı/ş/ç/ğ/ö/ü olan mətn azərbaycancadır; təmiz ASCII isə ingiliscə
        if re.search(r"[ıİşŞçÇğĞöÖüÜ]", blob) or not re.search(r"[A-Za-z]{3}", blob):
            return "az"
        return "en"
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

def parse_feed(xml_bytes):
    items = []
    xml_bytes = xml_bytes.lstrip(b"\xef\xbb\xbf \t\r\n")
    try:
        root = ET.fromstring(xml_bytes)
    except ET.ParseError:
        return parse_feed_lenient(xml_bytes)
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
def _rx(w):
    """Söz başlanğıcına bağlı axtarış (sonu sərbəst: şəkilçilər üçün)."""
    r = _RX.get(w)
    if r is None:
        # ABŞ sözünü Abşeron kimi yer adları ilə qarışdırma.
        suffix = r"(?=$|[^\w]|[-’'])" if w in ("abş", "abd") else r"(?!et|ет)" if w in ("bank", "банк") else ""
        r = _RX[w] = re.compile(r"(?<!\w)" + re.escape(norm_az(w)) + suffix)
    return r

def has_any(blob, words):
    return any(_rx(w).search(blob) for w in words)

def president_score(blob, lang):
    strong = sum(1 for w in PRESIDENT_STRONG if _rx(w).search(blob))
    if strong:
        return 4 + 2 * strong
    if lang != "az" or has_any(blob, FOREIGN_MARKERS):
        return 0
    weak = len(PRESIDENT_WEAK_RX.findall(blob))
    return weak + sum(1 for w in PRESIDENT_WEAK_EXTRA if _rx(w).search(blob)) if weak else 0

def categorize(title, desc, lang="az", hint=None, world=False):
    blob = norm_az(title + " " + desc)
    scores = {}
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
            hits += sum(1 for w in words if _rx(w).search(tb))
        hits *= BOOST.get(cat, 1)
        scores[cat] = hits
    if any(norm_az(s) in blob for s in STOPWORDS):
        scores["İqtisadiyyat"] = 0
    if hint and scores.get("Prezident", 0) < 6:
        return hint
    best = max(scores, key=scores.get)
    if scores[best] <= 0:
        return "Dünya" if world else FALLBACK
    # xarici mənbələrdə prezident bölməsi yalnız güclü göstərici ilə
    return best

def is_junk(link):
    return any(p in norm_az(link) for p in SKIP_URL_PARTS)

# Rəhbərlik/ölkə haqqında NEGATİV xəbərlər göstərilmir (redaksiya qərarı)
# Yalnız açıq adlar: «prezident», «rəhbərlik», «алиев» kimi ümumi sözlər xarici dövlət başçıları
# haqqında xəbərləri və rəsmi xronikanı da süzürdü.
LEADERSHIP = [
    "ilham əliyev", "ilham əliyevin", "mehriban əliyeva", "birinci xanım", "azərbaycan prezidenti",
    "azərbaycan hökuməti", "azərbaycan rəhbərliyi", "prezident aparatı",
    "ильхам алиев", "мехрибан алиева", "президент азербайджана", "президента азербайджана",
    "президентом азербайджана", "первой леди", "ilham aliyev", "mehriban aliyeva",
]
NEGATIVE = [
    "tənqid", "etiraz", "protest", "korrupsiya", "rüşvət", "yolsuzluq",
    "qalmaqal", "mübahisə", "həbs", "tutuklama", "gözaltı", "qanunsuz",
    "insan haqları", "repressiya", "təzyiq", "itiraz", "boykot", "işgəncə",
    "təqsirləndir", "məhkəmə hökmü", "cinayət", "satınalma qalmaqalı",
    "критик", "протест", "коррупц", "арест", "задержан", "незаконн", "обвин",
    "eleştiri", "protesto", "yolsuzluk", "rüşvet", "eleştirmek", "tutuklandı",
]

# Xarici mənbələrin Azərbaycan dövləti və rəhbərliyi haqqında xəbərləri dərc edilmir (redaksiya qərarı);
# bu mövzuda yalnız Azərbaycan mənbələri qalır. İdman xəbərləri (Qarabağ FK, idmançılar) istisnadır.
AZ_STATE_RX = re.compile(
    r"azerbaijan|azerbaycan|азербайджан|aliyev|алиев|əliyev|\bbaku\b|bakü|баку|\bbakı(?:da|dan|nın|ya|nı|\b)|nakhchivan|нахичеван|naxçıvan|"
    r"karabakh|karabağ|карабах|qarabağ|\bazeri\b|milli məclis|milli mejlis", re.I)

def foreign_about_azerbaijan(source, category, title, desc=""):
    if source not in WORLD_SOURCES or category == "idman":
        return False
    return bool(AZ_STATE_RX.search(f"{title} {desc or ''}"))

def is_negative_about_leadership(title, desc, source=None):
    """Rəhbərlikdən bəhs edən və neqativ çağrışım daşıyan xəbərləri tutur (redaksiya qərarı).
    Rəsmi mənbələr süzülmür; sözlər söz başlanğıcında axtarılır («qan təzyiqi» tutulmur)."""
    if source in ("Prezident.az", "Mehriban Əliyeva"):
        return False
    blob = norm_az(title + " " + desc)
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
        "publishedAt": to_iso(it["pubDate"]),
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
}
# Rəsmi Telegram veb önizləməsi. Yazıdakı keçid həmin saytadırsa qəbul edilir.
TG_FALLBACK = {
    "AZƏRTAC": ("azertacnews", "azertag.az"),
    "Report": ("reportnewsaz", "report.az"),
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
    decoded = {}
    if todo:
        with ThreadPoolExecutor(max_workers=4) as ex:
            ids = [art_id for art_id, _ in todo]
            for art_id, url in zip(ids, ex.map(_gnews_decode, ids)):
                decoded[art_id] = url
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
            raw = re.sub(r"<[^>]+>", " ", text_m.group(1) if text_m else "")
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
        MARKETS_FILE.write_text(json.dumps(out, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
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

def official_items():
    """Prezident və birinci xanımın rəsmi səhifələri.

    president.az/az/rss əsasən vətəndaş məktublarıdır; xəbərlər /az/news HTML-indədir.
    mehriban-aliyeva.az-da RSS yoxdur, xronika /site/catalogNews-dədir.
    AZƏRTAC (rss-official-chronicle) bir çox şəbəkədən 403 qaytarır, ona görə burada yoxdur.
    """
    items, errors = [], []
    try:
        page = fetch_text("https://president.az/az/news")
        for it in parse_president_page(page):
            items.append(("Prezident.az", "az", "Prezident", "Prezident", it))
    except Exception as e:
        errors.append(f"Prezident.az: {type(e).__name__}: {str(e)[:80]}")
    try:
        page = fetch_text("https://mehriban-aliyeva.az/site/catalogNews")
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
    except Exception as e:
        errors.append(f"Mehriban Əliyeva: {type(e).__name__}: {str(e)[:80]}")
    return items, errors

# X paylaşımları: X-in açıq lenti/embed-i 2026-da çıxışsız istifadəçiyə bağlıdır (syndication 429, embed boş iframe).
# Ona görə rəhbərliyin X/Instagram/Facebook paylaşımları onları xəbər verən rəsmi və agentlik xəbərlərindən götürülür
# («Prezidentin sosial şəbəkə hesablarında ... paylaşılıb», «Mehriban Əliyeva ... paylaşım edib»).
_SOC_SHARE_RX = re.compile(r"paylaş", re.I)
_SOC_WHO = [
    ("prezident", "Prezident İlham Əliyev", re.compile(r"prezident|ilham əliyev", re.I)),
    ("birinci-xanim", "Mehriban Əliyeva", re.compile(r"mehriban əliyeva|birinci xanım|birinci vitse-prezident", re.I)),
]
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
        who = next(((w, n) for w, n, rx in _SOC_WHO if rx.search(title)), None)
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
    SOCIAL_FILE.write_text(json.dumps({"updatedAt": now, "posts": posts[:16]}, ensure_ascii=False,
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
    VIDEO_FILE.write_text(json.dumps({"updatedAt": now, "items": items[:24]}, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
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
    SPORTS_FILE.write_text(json.dumps({"updatedAt": now_dt.isoformat(timespec="seconds"), "source": "ESPN", "leagues": leagues},
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
    FOOTBALL_FILE.write_text(json.dumps(data, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
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
    alt = {"source": a.get("source") or "", "sourceUrl": url, "publishedAt": a.get("publishedAt") or ""}
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
        placed = False
        if dt is not None and len(toks) >= 3:
            for members in clusters:
                head = members[0][0]
                if head is None or abs(dt - head) > GROUP_WINDOW:
                    continue
                key = _norm_title(a.get("title") or "")
                exact = len(key) >= 12 and any(_norm_title(m[3].get("title") or "") == key for m in members)
                if not exact and a.get("source") in {m[3].get("source") for m in members}:
                    continue
                official = a.get("source") in OFFICIAL_SOURCES or any(m[3].get("source") in OFFICIAL_SOURCES for m in members)
                if official and not exact:
                    # rəsmi şablon başlıqlar («X-in nazirini qəbul edib») fərqli hadisələrdə oxşar görünür — çox yaxın olmalıdır
                    if not any(mt is not None and abs(dt - mt) <= GROUP_WINDOW and _jaccard(set(toks), set(mtks)) >= 0.85
                               for mt, mtks, msh, _ma in members):
                        continue
                if exact or any(mt is not None and abs(dt - mt) <= GROUP_WINDOW and _titles_similar(toks, sh, mtks, msh)
                       for mt, mtks, msh, _ma in members):
                    members.append((dt, toks, sh, a))
                    placed = True
                    break
        if not placed:
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
        alts.extend(extra)
        alts.sort(key=lambda x: x.get("publishedAt") or "", reverse=True)
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
    SOURCES_FILE.write_text(json.dumps({"updatedAt": now, "sources": out}, ensure_ascii=False,
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
    SOURCES_FILE.write_text(json.dumps({
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
    items = sorted(articles, key=lambda a: a.get("publishedAt") or "", reverse=True)[:50]
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
    FEED_FILE.write_text("".join(parts), encoding="utf-8")
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
    ("heyat", "Həyat", "Həyat tərzi, qidalanma, psixologiya"),
    ("bolgeler", "Bölgələr", "Rayonlardan və şəhərlərdən xəbərlər"),
    ("tehsil", "Təhsil", "Məktəb, universitet, imtahanlar"),
    ("sehiyye", "Səhiyyə", "Tibb, xəstəxanalar, sağlamlıq"),
    ("texnologiya", "Texnologiya", "Elm, texnologiya və süni intellekt"),
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
    <script type="module" src="../../assets/app.js"></script>
    <!-- Resurslar yuxarıda nisbi yolla yükləndi; tətbiq kök ünvanda işləyir, ona görə ünvan kökə keçirilir -->
    <script>history.replaceState(null, "", new URL("../../#/bolme/__SLUG__", location.href));</script>
  </head>
  <body>
    <div id="app">
      <main class="wrap"><h1>__LABEL__</h1><p>__DESC__</p><ul>__ITEMS__</ul>
      <p><a href="../../">8ulduz — baş səhifə</a></p><noscript>Tam sayt üçün JavaScript-i aktiv edin.</noscript></main>
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
    return (_SECTION_HTML.replace("__ITEMS__", lis).replace("__LABEL__", _xml(label)).replace("__DESC__", _xml(desc))
            .replace("__URL__", url).replace("__SITE__", SITE).replace("__SLUG__", slug))

def write_sections(articles):
    for slug, label, desc in SECTIONS:
        d = SECTIONS_DIR / slug
        d.mkdir(parents=True, exist_ok=True)
        (d / "index.html").write_text(section_page(slug, label, desc, articles), encoding="utf-8")
    print(f"Bölmə səhifələri: {len(SECTIONS)}")

def write_sitemap():
    today = datetime.datetime.now(datetime.timezone.utc).date().isoformat()
    locs = [SITE, SITE + "feed.xml"] + [f"{SITE}bolme/{slug}/" for slug, _l, _d in SECTIONS]
    body = ['<?xml version="1.0" encoding="UTF-8"?>',
            '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">']
    for loc in locs:
        body.append(f"<url><loc>{_xml(loc)}</loc><lastmod>{today}</lastmod><changefreq>hourly</changefreq></url>")
    body.append("</urlset>\n")
    SITEMAP_FILE.write_text("".join(body), encoding="utf-8")

def write_robots():
    ROBOTS_FILE.write_text(
        "User-agent: *\nAllow: /\n\nSitemap: " + SITE + "sitemap.xml\n",
        encoding="utf-8")

def write_public():
    try:
        articles = json.loads(OUT_FILE.read_text(encoding="utf-8")).get("articles") or []
    except Exception:
        articles = []
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
        DATES_FILE.write_text(json.dumps(dict(rows), ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
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
    cache.pop("_meta", None)
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
                    a["imageUrl"] = img
    except Exception as e:
        err = f"{type(e).__name__}: {str(e)[:80]}"
        print("  ! og:image:", err)
    keep = {a.get("sourceUrl") for a in articles if a.get("sourceUrl")}
    trimmed = {k: v for k, v in cache.items() if k in keep}
    # Diaqnostika (loglara girişsiz): neçə xəbər şəkilsizdir, bu dövrədə neçəsi sorğulandı və tapıldı
    trimmed["_meta"] = {"at": datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds"),
                        "todo": len(todo), "batch": len(batch), "found": sum(1 for i in found if i), "error": err}
    try:
        OUT_DIR.mkdir(exist_ok=True)
        OG_FILE.write_text(json.dumps(trimmed, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
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
    STATUS_FILE.write_text(json.dumps({"checkedAt": now if ok else previous.get("checkedAt"),
                                       "attemptedAt": now, "ok": ok,
                                       "successfulSources": successful, "totalSources": total,
                                       "degraded": ok and successful < total, "stats": stats or previous.get("stats")}, ensure_ascii=False,
                                       separators=(",", ":")), encoding="utf-8")
    print(f"Yoxlama: {now}")

# --------------------------------------------------------------------- main ---
def main():
    try:
        old = json.loads(OUT_FILE.read_text(encoding="utf-8"))["articles"]
    except Exception:
        old = []
    prev_articles = [dict(a) for a in old]
    old = [a for a in old if not is_junk(a.get("sourceUrl", ""))]
    old = [a for a in old if not is_negative_about_leadership(a.get("title", ""), a.get("summary", ""), a.get("source"))]
    hints = {f[0]: f[3] for f in FEEDS}
    for a in old:
        # köhnə xəbərlərin dili yoxdursa — avtomatik təyin et (süzgəcin düzgün işləməsi üçün)
        if not a.get("lang"):
            a["lang"] = detect_lang(a.get("title", ""), a.get("summary", ""), "")
        # köhnə xəbərləri də yenilənmiş qaydalarla yenidən kateqoriyalaşdır
        lbl = label_for(a.get("title", ""), a.get("summary", ""), a["lang"],
                        hints.get(a.get("source")), a.get("source") in WORLD_SOURCES)
        if a.get("source") in ("Prezident.az", "Mehriban Əliyeva"):
            lbl = "Prezident"
        a["category"] = SLUGS.get(lbl, "gundem")
    old = [a for a in old if not foreign_about_azerbaijan(a.get("source"), a.get("category"), a.get("title", ""), a.get("summary", ""))]
    for a in old:
        dt = _parse_dt(a.get("publishedAt"))
        if dt is not None:
            a["publishedAt"] = _norm_iso(dt)
        for alt in a.get("alts") or []:
            adt = _parse_dt(alt.get("publishedAt"))
            if adt is not None:
                alt["publishedAt"] = _norm_iso(adt)
    now_utc = datetime.datetime.now(datetime.timezone.utc)
    cutoff, cutoff_prez = now_utc - datetime.timedelta(days=5), now_utc - datetime.timedelta(days=60)
    old = [a for a in old if (_parse_dt(a.get("publishedAt")) or now_utc) >= (cutoff_prez if a.get("category") == "prezident" else cutoff)]
    seen = {a["sourceUrl"] for a in old}
    new_items, errors, empty = [], [], []
    dates, lookups, undated = load_dates(), DATE_LOOKUPS, 0
    source_rows = []
    with ThreadPoolExecutor(max_workers=WORKERS) as ex:
        results = list(ex.map(fetch_feed, FEEDS))  # sıra FEEDS ilə eynidir
    for (source, url, dlang, hint), (_, items, err, used_url) in zip(FEEDS, results):
        source_rows.append({"name": source, "url": used_url or url, "count": 0 if err else len(items), "error": err})
        if err:
            errors.append(f"{source}: {err}")
            continue
        if not items:
            empty.append(source)
        for it in items:
            try:
                if it["link"] in seen or is_junk(it["link"]):
                    continue
                seen.add(it["link"])
                if not it.get("pubDate"):
                    iso, lookups = undated_date(it, dates, lookups)
                    if not iso:
                        continue
                    it = dict(it, pubDate=iso)
                    undated += 1
                if is_negative_about_leadership(it["title"], it["description"], source):
                    continue
                art = make_article(it, source, dlang, hint)
                if foreign_about_azerbaijan(source, art["category"], art["title"], art["summary"]):
                    continue
                new_items.append(art)
            except Exception as e:
                errors.append(f"{source} (element): {type(e).__name__}")
    off_items, off_errors = official_items()
    errors.extend(off_errors)
    source_rows.extend(official_source_rows(off_items, off_errors))
    for source, dlang, hint, force, it in off_items:
        try:
            if it["link"] in seen or is_junk(it["link"]):
                continue
            seen.add(it["link"])
            if is_negative_about_leadership(it["title"], it["description"], source):
                continue
            new_items.append(make_article(it, source, dlang, hint, force_label=force))
        except Exception as e:
            errors.append(f"{source} (rəsmi): {type(e).__name__}")
    save_dates(dates)
    new_items.sort(key=lambda a: a["publishedAt"], reverse=True)
    old = sorted(old, key=lambda a: a.get("publishedAt", ""), reverse=True)
    uniq, dseen = [], set()
    per_src = {}
    # Tarixə görə birgə sıralama. Əvvəl «yeni» (bu dövrədə ilk dəfə görülən) xəbərlər köhnələrdən qabaq gəlirdi;
    # limitdən kənarda qalan köhnə xəbərlər növbəti dövrədə yenidən «yeni» sayılıb siyahını hər dəfə dəyişirdi
    # (813-dən yalnız ~50 xəbər dövrədən dövrəyə qalırdı; og keşi və qruplar daim sıfırlanırdı).
    for a in sorted(new_items + old, key=lambda x: x.get("publishedAt") or "", reverse=True):
        if a["sourceUrl"] in dseen:
            continue
        n = per_src.get(a.get("source"), 0)
        if n >= MAX_PER_SOURCE:
            continue
        per_src[a.get("source")] = n + 1
        dseen.add(a["sourceUrl"]); uniq.append(a)
    # Prezident bölməsi ümumi limitdən asılı deyil: rəsmi xronika (60 gün) həmişə saxlanılır.
    # Əvvəl yalnız 800-dən kənarda qalanlar əlavə olunurdu; siyahı 800-dən qısa olanda heç nə əlavə olunmurdu.
    prez_items = [a for a in uniq if a["category"] == "prezident"][:120]
    articles = [a for a in uniq if a["category"] != "prezident"][:MAX_ITEMS] + prez_items
    stats = {"old": len(old), "new": len(new_items), "uniq": len(uniq), "prez": len(prez_items), "articles": len(articles),
             "undated": undated, "dateLookups": DATE_LOOKUPS - lookups}
    articles = group_duplicates(articles)
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
    try:
        n_og = fill_og_images(articles)
        if n_og:
            print(f"og:image sorğusu: {n_og}")
    except Exception as e:
        print("  ! og:image:", type(e).__name__)
    save_sources(source_rows)
    successful = sum(1 for row in source_rows if not row.get("error") and row.get("count", 0) > 0)
    result = {"ok": successful > 0 and bool(articles), "successful": successful, "total": len(source_rows), "stats": stats}
    if not successful:
        print("Heç bir xəbər mənbəyi işləmədi — əvvəlki xəbər lenti saxlanıldı")
        return result
    if not articles:
        print("Xəbər yoxdur — fayl dəyişdirilmədi"); return result
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
    OUT_FILE.write_text(json.dumps(data, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    ok = len(FEEDS) - len(errors) - len(empty)
    print(f"Mənbə işlədi: {ok}/{len(FEEDS)} | Yeni: {len(new_items)} | Ümumi: {len(articles)}")
    for e in errors:
        print("  !", e)
    for e in empty:
        print("  ∅", e, "(boş lent)")
    return result

def run():
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
    sys.exit(run())
