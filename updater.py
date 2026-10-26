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
    ("AZƏRTAC",      "https://azertag.az/rss"),
    ("APA",          "https://apa.az/rss"),
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
    "mehriban", "məhriban", "мехрибан",
]
# Zəif göstəricilər: yalnız xarici kontekst olmadıqda sayılır
# "X prezidenti" (məs. "Azercell prezidenti", "FIFA prezidenti") başqasının prezidentidir — sayılmır.
PRESIDENT_WEAK_RX = re.compile(r"(?<!\w)(?:prezident(?!i(?!\w)|inin|liy)|dövlət başçısı)")
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
    "Siyasət": ["səfir", "parlament", "milli məclis", "seçki", "səfirlik",
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
    "Cəmiyyət": ["yol qəzası", "hadisə", "qəza", "yanğın", "hava", "təhsil", "məktəb", "universitet",
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
              "kəşf", "kosmos", "texnologiya", "smartfon", "süni intellekt",
              "doktor", "kanser", "kalp", "hastalık", "yemek tarifi", "burç",
              "врач", "здоров", "болезн", "диет", "витамин", "сон ", "ученые", "учёные",
              "исследован", "астроном", "космос", "смартфон", "искусственн", "рецепт",
              "health", "doctor", "diet", "study finds", "scientists", "space", "smartphone", "fiziki məşq", "əhval-ruhiyyə", "tənhalıq", "windows", "ixtira"],
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
BOOST = {"İdman": 2, "Prezident": 3}
SLUGS = {"Prezident": "prezident", "Gündəm": "gundem", "Siyasət": "siyaset", "Cəmiyyət": "cemiyyet",
         "İqtisadiyyat": "iqtisadiyyat", "Dünya": "dunya", "İdman": "idman", "Mədəniyyət": "medeniyyet",
         "Həyat": "heyat"}
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
VIDEO_FILE = OUT_DIR / "video.json"
FOOTBALL_FILE = OUT_DIR / "football.json"
# YouTube RSS, açarsız. Kanal adları lentin öz başlığı ilə yoxlanıb.
YT_NEWS = [
    ("İctimai TV", "https://www.youtube.com/feeds/videos.xml?channel_id=UCDVpJfSc-RCGSCfGE2MFGAg"),
    ("Xezer TV", "https://www.youtube.com/feeds/videos.xml?channel_id=UCUsYwCUHsMQcuEm8cOCAuFQ"),
    ("ARB 24", "https://www.youtube.com/feeds/videos.xml?channel_id=UC44ToFclJwakpqw1Wh6iW-A"),
    ("Report.az", "https://www.youtube.com/feeds/videos.xml?channel_id=UC4Cx3XB6y7oPYOE5yUhyXKg"),
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
MAX_ITEMS = 800
MAX_PER_SOURCE = 50   # bir mənbə lenti doldurmasın
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
        if u and (t.startswith("image") or (not t and IMG_EXT.search(u))):
            return _abs_img(u, link)
    for tag in ("content", "thumbnail"):
        for m in item.iter(MEDIA + tag):
            u, t, med = m.get("url"), (m.get("type") or ""), (m.get("medium") or "")
            if u and (tag == "thumbnail" or med == "image" or t.startswith("image") or IMG_EXT.search(u)):
                return _abs_img(u, link)
    for le in item.findall("{http://www.w3.org/2005/Atom}link"):
        if le.get("rel") == "enclosure" and (le.get("type") or "").startswith("image"):
            return _abs_img(le.get("href"), link)
    blobs = [raw_desc, text_of(item, ["{http://purl.org/rss/1.0/modules/content/}encoded"])]
    for b in blobs:
        m = IMG_RE.search(b or "")
        if m:
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
            return now.isoformat()
    except Exception:
        pass
    return iso

def _to_iso(pub):
    if not pub:
        return datetime.datetime.now(datetime.timezone.utc).isoformat()
    pub = re.sub(r"\s+", " ", pub.strip())
    try:
        dt = email.utils.parsedate_to_datetime(pub)
        if dt is None:
            raise ValueError
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=datetime.timezone.utc)
        return dt.isoformat()
    except Exception:
        pass
    try:
        dt = datetime.datetime.fromisoformat(pub.replace("Z", "+00:00"))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=datetime.timezone.utc)
        return dt.isoformat()
    except Exception:
        return datetime.datetime.now(datetime.timezone.utc).isoformat()

_RX = {}
def _rx(w):
    """Söz başlanğıcına bağlı axtarış (sonu sərbəst: şəkilçilər üçün)."""
    r = _RX.get(w)
    if r is None:
        r = _RX[w] = re.compile(r"(?<!\w)" + re.escape(norm_az(w)))
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
            hits = president_score(blob, lang)
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
LEADERSHIP = [
    "ilham əliyev", "mehriban əliyeva", "birinci xanım", "prezident",
    "azərbaycan hökuməti", "azərbaycan rəhbərliyi", "rəhbərlik", "prezident aparatı",
    "ильхам алиев", "алиев", "алиева", "мехрибан алиева",
    "президент азербайджана", "президента азербайджана", "президентом азербайджана",
    "первой леди", "ilham aliyev",
]
NEGATIVE = [
    "tənqid", "etiraz", "protest", "korrupsiya", "rüşvət", "yolsuzluq",
    "qalmaqal", "mübahisə", "həbs", "tutuklama", "gözaltı", "qanunsuz",
    "insan haqları", "repressiya", "təzyiq", "itiraz", "boykot", "işgəncə",
    "təqsirləndir", "məhkəmə hökmü", "cinayət", "satınalma qalmaqalı",
    "критик", "протест", "коррупц", "арест", "задержан", "незаконн", "обвин",
    "eleştiri", "protesto", "yolsuzluk", "rüşvet", "eleştirmek", "tutuklandı",
]

def is_negative_about_leadership(title, desc):
    """Rəhbərlikdən bəhs edən və neqativ çağrışım daşıyan xəbərləri tutur."""
    blob = norm_az(title + " " + desc)
    if not any(norm_az(w) in blob for w in LEADERSHIP):
        return False
    return any(norm_az(w) in blob for w in NEGATIVE)

def is_video(it):
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
        "summary": desc,
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

def cbar_rates(day):
    """AMB (CBAR) rəsmi məzənnələri: {kod: AZN qiyməti bir vahid üçün}."""
    xml = fetch(f"https://www.cbar.az/currencies/{day:%d.%m.%Y}.xml")
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
    for back in range(0, 6):
        d = baku - datetime.timedelta(days=back)
        try:
            r = cbar_rates(d)
            if r.get("USD"):
                if cur is None:
                    cur = (d, r)
                elif r != cur[1]:
                    prev = (d, r); break
        except Exception:
            if back == 0:
                continue
            break
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
    if items and strip(items) == strip(old.values()) and len(items) == len(old):
        print("Bazar: dəyişiklik yoxdur"); return
    if items:
        MARKETS_FILE.write_text(json.dumps({"updatedAt": now, "items": items}, ensure_ascii=False,
                                           separators=(",", ":")), encoding="utf-8")
    print(f"Bazar: {sum(1 for i in items if not i.get('stale'))}/{len(MARKET_DEFS)} təzə")

def _clean_text(s):
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", s or ""))).strip()

def parse_az_date(s):
    """'24.10.2026' və '24 oktyabr 2026, 19:15' — Bakı vaxtı."""
    raw = _clean_text(s).lower()
    hm = re.search(r"(\d{1,2}):(\d{2})", raw)
    hour, minute = (int(hm.group(1)), int(hm.group(2))) if hm else (12, 0)
    m = re.search(r"(\d{1,2})[.](\d{1,2})[.](\d{4})", raw)
    if not m:
        w = re.search(r"(\d{1,2})\s+([a-zəöüğışç]+)\s+(\d{4})", raw)
        if w and w.group(2) in AZ_MONTHS:
            m = (int(w.group(1)), AZ_MONTHS[w.group(2)], int(w.group(3)))
        else:
            return datetime.datetime.now(datetime.timezone.utc).isoformat()
    else:
        m = (int(m.group(1)), int(m.group(2)), int(m.group(3)))
    return datetime.datetime(m[2], m[1], m[0], hour, minute, tzinfo=BAKU).isoformat()

def fetch_text(url, tries=3, timeout=20):
    last = None
    for _ in range(tries):
        try:
            return fetch(url, timeout=timeout).decode("utf-8", "replace")
        except Exception as e:
            last = e
    raise last

def official_items():
    """Prezident və birinci xanımın rəsmi səhifələri.

    president.az/az/rss əsasən vətəndaş məktublarıdır; xəbərlər /az/news HTML-indədir.
    mehriban-aliyeva.az-da RSS yoxdur, xronika /site/catalogNews-dədir.
    AZƏRTAC (rss-official-chronicle) bir çox şəbəkədən 403 qaytarır, ona görə burada yoxdur.
    """
    items, errors = [], []
    try:
        page = fetch_text("https://president.az/az/news")
        for block in re.findall(r'<article class="news-photo">(.*?)</article>', page, re.S):
            href = re.search(r'href="([^"]+)"', block)
            title = re.search(r'class="label-title">(.*?)</span>', block, re.S)
            date = re.search(r'class="category_date">(.*?)</span>', block, re.S)
            img = re.search(r'<img[^>]+src="([^"]+)"', block)
            t = _clean_text(title.group(1)) if title else ""
            if not (href and t):
                continue
            link = urllib.parse.urljoin("https://president.az", href.group(1))
            items.append(("Prezident.az", "az", "Prezident", "Prezident", {
                "title": t, "link": link,
                "description": "Azərbaycan Prezidentinin rəsmi səhifəsindən.",
                "pubDate": parse_az_date(date.group(1) if date else ""),
                "image": _abs_img(img.group(1), link) if img else None, "author": "",
            }))
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
            got = parse_feed(fetch(url))[:4]
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
    if failed:
        posts.extend(p for p in old if p.get("who") in failed)
    posts.sort(key=lambda p: p.get("publishedAt") or "", reverse=True)
    now = datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds")
    OUT_DIR.mkdir(exist_ok=True)
    SOCIAL_FILE.write_text(json.dumps({"updatedAt": now, "posts": posts[:8]}, ensure_ascii=False,
                                       separators=(",", ":")), encoding="utf-8")
    merge_sources(yt_rows)
    print(f"Sosial: {min(8, len(posts))} yazı")

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

def update_video():
    items, rows = [], []
    for name, url in YT_NEWS:
        try:
            got = parse_feed(fetch(url))[:5]
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
    items.sort(key=lambda p: p.get("publishedAt") or "", reverse=True)
    now = datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds")
    OUT_DIR.mkdir(exist_ok=True)
    VIDEO_FILE.write_text(json.dumps({"updatedAt": now, "items": items[:24]}, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    if rows:
        merge_sources(rows)
    print(f"Video: {min(24, len(items))} yazı")

def update_football():
    """Premyer Liqa. Açıq sınaq açarı cədvəli yarımçıq qaytarır — cədvəli saxlamırıq."""
    events, note = [], "Tam turnir cədvəli açıq sınaq mənbəyində yoxdur. Nəticələr və futbol xəbərləri göstərilir."
    try:
        d = fetch_json("https://www.thesportsdb.com/api/v1/json/123/eventspastleague.php?id=4693", timeout=12)
        for e in (d.get("events") or [])[:6]:
            events.append({
                "home": e.get("strHomeTeam") or "",
                "away": e.get("strAwayTeam") or "",
                "hs": e.get("intHomeScore"),
                "as": e.get("intAwayScore"),
                "date": e.get("dateEvent") or "",
            })
    except Exception as e:
        print("  ! futbol:", type(e).__name__)
        note = "Oyun nəticəsi alınmadı. Futbol xəbərləri göstərilir."
    now = datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds")
    OUT_DIR.mkdir(exist_ok=True)
    FOOTBALL_FILE.write_text(json.dumps({
        "updatedAt": now, "league": "Azərbaycan Premyer Liqası",
        "table": [], "events": events, "note": note,
        "link": "https://pfl.az/",
    }, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    print(f"Futbol: {len(events)} oyun")

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
        return datetime.datetime.fromisoformat(iso.replace("Z", "+00:00"))
    except Exception:
        return None

def _compact_alt(a):
    url = a.get("sourceUrl") or ""
    if not url:
        return None
    return {"source": a.get("source") or "", "sourceUrl": url, "publishedAt": a.get("publishedAt") or ""}

def _prefer_primary(a, b):
    """Şəkli və daha dolu xülasəsi olan kart əsas olsun; eyni olanda daha yenisi."""
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
    names = {r["name"] for r in rows}
    out.extend(s for s in prev_list if s.get("name") not in names)
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

def write_sitemap():
    today = datetime.datetime.now(datetime.timezone.utc).date().isoformat()
    locs = [SITE, SITE + "feed.xml"]
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
    write_sitemap()
    write_robots()

_OG_META = re.compile(r"<meta\b[^>]*>", re.I)
_OG_KEY = re.compile(r"""(?:property|name)\s*=\s*["']([^"']+)["']""", re.I)
_OG_CONTENT = re.compile(r"""content\s*=\s*["']([^"']+)["']""", re.I)
_OG_NAMES = {"og:image", "og:image:url", "twitter:image", "twitter:image:src"}

def _og_from_html(raw, base):
    text = raw.decode("utf-8", "replace")
    for tag in _OG_META.findall(text):
        km = _OG_KEY.search(tag)
        if not km or km.group(1).lower() not in _OG_NAMES:
            continue
        cm = _OG_CONTENT.search(tag)
        if not cm:
            continue
        img = _abs_img(html.unescape(cm.group(1)), base)
        if img:
            return img
    return ""

def _fetch_og(url):
    try:
        req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "text/html,application/xhtml+xml"})
        with urllib.request.urlopen(req, timeout=8) as r:
            ctype = (r.headers.get("Content-Type") or "").lower()
            if ctype and "html" not in ctype and "xml" not in ctype:
                return ""
            return _og_from_html(r.read(90000), url)
    except Exception:
        return ""

def fill_og_images(articles, limit=30):
    """Şəkilsiz xəbərlər üçün səhifənin og:image ünvanı. Hər URL bir dəfə sorğulanır."""
    try:
        cache = json.loads(OG_FILE.read_text(encoding="utf-8"))
        if not isinstance(cache, dict):
            cache = {}
    except Exception:
        cache = {}
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
    batch = todo[:limit]
    if batch:
        with ThreadPoolExecutor(max_workers=8) as ex:
            found = list(ex.map(lambda a: _fetch_og(a.get("sourceUrl") or ""), batch))
        for a, img in zip(batch, found):
            cache[a["sourceUrl"]] = img or ""
            if img:
                a["imageUrl"] = img
    keep = {a.get("sourceUrl") for a in articles if a.get("sourceUrl")}
    trimmed = {k: v for k, v in cache.items() if k in keep}
    try:
        OUT_DIR.mkdir(exist_ok=True)
        OG_FILE.write_text(json.dumps(trimmed, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    except Exception as e:
        print("  ! og keşi:", type(e).__name__)
    return len(batch)

def write_status():
    """Hər uğurlu yoxlamada yazılır — xəbər mətni dəyişməsə belə. UI bunu göstərir."""
    now = datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds")
    OUT_DIR.mkdir(exist_ok=True)
    STATUS_FILE.write_text(json.dumps({"checkedAt": now, "ok": True}, ensure_ascii=False,
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
    old = [a for a in old if not is_negative_about_leadership(a.get("title", ""), a.get("summary", ""))]
    hints = {f[0]: f[3] for f in FEEDS}
    for a in old:
        # köhnə xəbərlərin dili yoxdursa — avtomatik təyin et (süzgəcin düzgün işləməsi üçün)
        if not a.get("lang"):
            a["lang"] = detect_lang(a.get("title", ""), a.get("summary", ""), "")
        # köhnə xəbərləri də yenilənmiş qaydalarla yenidən kateqoriyalaşdır
        lbl = label_for(a.get("title", ""), a.get("summary", ""), a["lang"],
                        hints.get(a.get("source")), a.get("source") in WORLD_SOURCES)
        a["category"] = SLUGS.get(lbl, "gundem")
    seen = {a["sourceUrl"] for a in old}
    new_items, errors, empty = [], [], []
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
                if is_negative_about_leadership(it["title"], it["description"]):
                    continue
                new_items.append(make_article(it, source, dlang, hint))
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
            if is_negative_about_leadership(it["title"], it["description"]):
                continue
            new_items.append(make_article(it, source, dlang, hint, force_label=force))
        except Exception as e:
            errors.append(f"{source} (rəsmi): {type(e).__name__}")
    new_items.sort(key=lambda a: a["publishedAt"], reverse=True)
    old = sorted(old, key=lambda a: a.get("publishedAt", ""), reverse=True)
    uniq, dseen = [], set()
    per_src = {}
    for a in (new_items + old):
        if a["sourceUrl"] in dseen:
            continue
        n = per_src.get(a.get("source"), 0)
        if n >= MAX_PER_SOURCE:
            continue
        per_src[a.get("source")] = n + 1
        dseen.add(a["sourceUrl"]); uniq.append(a)
    # Prezident bölməsi üçün xəbərlər limitdən kənarda da (son 60) saxlanılır
    articles = uniq[:MAX_ITEMS] + [a for a in uniq[MAX_ITEMS:] if a["category"] == "prezident"][:60]
    articles = group_duplicates(articles)
    try:
        n_og = fill_og_images(articles)
        if n_og:
            print(f"og:image sorğusu: {n_og}")
    except Exception as e:
        print("  ! og:image:", type(e).__name__)
    save_sources(source_rows)
    if not articles:
        print("Xəbər yoxdur — fayl dəyişdirilmədi"); return
    if articles == prev_articles:
        print(f"Dəyişiklik yoxdur ({len(FEEDS) - len(errors)}/{len(FEEDS)} mənbə)")
        for e in errors:
            print("  !", e)
        return
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

if __name__ == "__main__":
    news_ok = True
    if "--no-markets" not in sys.argv:
        try:
            update_markets()
        except Exception as e:
            print("  ! bazar:", type(e).__name__)
    if "--markets-only" not in sys.argv:
        try:
            main()
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
        if news_ok:
            write_status()
            try:
                write_public()
            except Exception as e:
                print("  ! seo:", type(e).__name__, e)
