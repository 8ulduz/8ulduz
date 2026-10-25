# -*- coding: utf-8 -*-
"""
8ulduz — avtomatik xəbər yeniləyici v5
- 15 Azərbaycan + 5 xarici mənbə
- Dil ayrımı: az / ru / en
- "Prezident gündəliyi" əsas bölməsi
- Video nişanı (saytdakı video səhifələrinə keçid üçün)
"""
import json, re, pathlib, hashlib, datetime, email.utils
import urllib.request
import xml.etree.ElementTree as ET

# 15 Azərbaycan mənbəsi
AZ_FEEDS = [
    ("AZƏRTAC",      "https://azertag.az/rss"),
    ("APA",          "https://apa.az/rss"),
    ("Report",       "https://report.az/rss/"),
    ("Trend",        "https://www.trend.az/rss/"),
    ("Milli.az",     "https://www.milli.az/rss"),
    ("Oxu.az",       "https://www.oxu.az/rss"),
    ("Qafqazinfo",   "https://www.qafqazinfo.az/rss"),
    ("Modern.az",    "https://www.modern.az/rss"),
    ("AzVision",     "https://www.azvision.az/rss"),
    ("Sputnik AZ",   "https://az.sputniknews.ru/rss/"),
    ("Teleqraf",     "https://www.teleqraf.com/rss"),
    ("Day.Az",       "https://news.day.az/rss/"),
    ("1news.az",     "https://1news.az/rss/"),
    ("Ayna.az",      "https://www.ayna.az/rss"),
    ("Crossmedia",   "https://crossmedia.az/rss"),
    ("Azernews",     "https://www.azernews.az/rss/"),
    ("News.az",      "https://www.news.az/rss/"),
    ("Vesti.az",     "https://www.vesti.az/rss/"),
    ("Medianews",    "https://www.medianews.az/rss/"),
    ("İnterPress",   "https://www.interpress.az/rss/"),
    ("Kulis.az",     "https://www.kulis.az/rss/"),
    ("A24.az",       "https://a24.az/rss/"),
    ("Azadlıq",      "https://www.azadliq.org/rss/"),
    ("Meydan TV",    "https://www.meydan.tv/rss/"),
    ("Virtual AZ",   "https://www.virtualaz.org/rss/"),
    ("Sia.az",       "https://sia.az/rss/"),
    ("Şərq",         "https://www.sherg.az/rss/"),
    ("Baku TV",      "https://www.baku.tv/rss/"),
    ("Xəzər TV",     "https://www.xezertv.az/rss/"),
    ("İctimai TV",   "https://itv.az/rss/"),
    ("ARB",          "https://arb24.az/rss/"),
    ("CBC",          "https://cbc.az/rss/"),
    ("AzTV",         "https://aztv.az/rss/"),
    ("Haqqin.az",    "https://haqqin.az/rss/"),
    ("Marja.az",     "https://www.marja.az/rss/"),
    ("Metbuat",      "https://www.metbuat.az/rss/"),
    ("ABC.az",       "https://www.abc.az/rss/"),
    ("Kaspi",        "https://www.kaspi.az/rss/"),
    ("Cebhe.info",   "https://cebhe.info/rss/"),
    ("Pravda.az",    "https://pravda.az/rss/"),
    ("Tia.az",       "https://www.tia.az/rss/"),
    ("Xural",        "https://www.xural.az/rss/"),
    ("Günün Səsi",   "https://gununsesi.info/rss/"),
    ("Novator.az",   "https://www.novator.az/rss/"),
    ("Bizim Yol",    "https://www.bizimyol.info/rss/"),
    ("Yeni Müsavat", "https://www.yenimusavat.com/rss/"),
    ("Müsavat",      "https://www.musavat.com/rss/"),
    ("Aztag.az",     "https://www.aztag.az/rss/"),
    ("Diaspor",      "https://www.diaspora.az/rss/"),
    ("Xezerxeber",   "https://www.xezerxeber.az/rss/"),
    ("İnfoqrafiya",  "https://www.infoqrafiya.az/rss/"),
    ("Day.Az RU",    "https://ru.day.az/rss/"),
    ("Trend RU",     "https://ru.trend.az/rss/"),
    ("AzVision RU",  "https://ru.azvision.az/rss/"),
]
# 5 xarici mənbə
WORLD_FEEDS = [
    ("BBC News",     "https://feeds.bbci.co.uk/news/world/rss.xml", "en"),
    ("Al Jazeera",   "https://www.aljazeera.com/xml/rss/all.xml",   "en"),
    ("Daily Sabah",  "https://www.dailysabah.com/rss",              "en"),
    ("Hürriyet",     "https://www.hurriyet.com.tr/rss/anasayfa",    "tr"),
    ("Sabah TR",     "https://www.sabah.com.tr/rss",                "tr"),
    ("Habertürk",    "https://www.haberturk.com/rss",               "tr"),
    ("Milliyet",     "https://www.milliyet.com.tr/rss",             "tr"),
    ("CNN Türk",     "https://www.cnnturk.com/rss",                 "tr"),
    ("TRT Haber",    "https://www.trthaber.com/rss",                "tr"),
    ("Yeni Şafak",   "https://www.yenisafak.com/rss",               "tr"),
    ("TRT Spor",     "https://www.trtspor.com.tr/rss",              "tr"),
    ("Fanatik",      "https://www.fanatik.com.tr/rss",              "tr"),
    ("NTV Spor",     "https://www.ntvspor.net/rss",                 "tr"),
    ("TASS",         "https://tass.ru/rss/v2.xml",                  "ru"),
    ("Championat",   "https://www.championat.com/rss",              "ru"),
    ("Sport.ru",     "https://www.sport.ru/rss",                    "ru"),
    ("Match TV",     "https://matchtv.ru/rss",                      "ru"),
]
FEEDS = [(s, u, "az") for s, u in AZ_FEEDS] + WORLD_FEEDS

SKIP_URL_PARTS = ["/resmi-ilanlar/", "/lezizz/", "/emlak-ilanlari/"]
STOPWORDS = ["neftçala", "neftchala", "ceyran", "xəzər"]

PRESIDENT_WORDS = [
    "ilham əliyev", "mehriban əliyeva", "birinci xanım", "prezident aparatı",
    "azərbaycan prezidenti", "prezident", "sərəncam", "fərman", "təltif",
    "президент азербайджана", "ильхам алиев", "мехрибан алиева", "первой леди",
]
IDMAN_WORDS = [
    "futbol", "affa", "milli komanda", "qarabağ fk", "kuboku", "avropa liqası",
    "çempion", "oyun", "matç", "məşqçi", "qol", "turnir", "cüdo", "neftçi",
    "formula", "grand prix", "basketbol", "voleybol", "transfer", "konfrans liqası",
    "fenerbahçe", "galatasaray", "beşiktaş", "trabzonspor", "maç", "sabah fk",
    "şampiyon", "süper lig", "premier league", "champions", "uefa", "fifa", "zirə", "turan",
    "idman", "yığma", "yarış", "medal", "çempionat", "liqa", "derbi", "penalti",
    "azərbaycan kuboku", "premyer liqa", "olimpiya", "güləş", "boks", "atletika",
    "üzgüçülük", "badminton", "şahmat", "gimnastika", "atıcılıq", "təkərli", "voleybolçu",
    "keşlə", "sumqayıt fk", "tofiq bəhramov",
]
CATEGORIES = {
    "Prezident": PRESIDENT_WORDS,
    "İdman": IDMAN_WORDS,
    "Siyasət": ["sərəncam", "səfir", "parlament", "milli məclis", "seçki", "səfirlik",
                "nazir", "bəyanat", "zəngəzur", "türkiyə", "diplomat", "media və yayım şurası",
                "dışişleri", "seçim", "bakan", "politics", "siyasi",
                "election", "minister", "summit", "ukraine", "gaza", "israel", "məsləhətləşmə",
                "qarabağda", "qarabağın", "qarabağ münaqişəsi", "dəhliz", "sülh müqaviləsi", "məclis",
                "hökumət", "nazirlik", "vəkillər", "konstitusiya", "ərdoğan", "erdoğan", "erdogan"],
    "İqtisadiyyat": ["neft", "oil", "qiymət", "manat", "dollar", "valyuta", "büdcə",
                     "inflyasiya", "maliyyə", "bank", "vergi", "sahibkar", "ixrac", "idxal",
                     "qaz", "enerji", "faiz", "maaş", "pensiya", "borsa", "dotasiya", "məzənnə",
                     "ekonomi", "merkez bankası", "enflasyon", "economy", "market", "dövlət büdcəsi",
                     "mühasibat", "gömrük"],
    "Mədəniyyət": ["film", "kino", "sərgi", "muzey", "teatr", "musiqi", "konsert", "kitab",
                   "şair", "yazıçı", "əsər", "incəsənət", "festival", "mükafat", "şarkı",
                   "sinema", "kitap", "roman", "sanat", "sergi", "concert", "culture", "albüm", "oyuncu"],
    "Cəmiyyət": ["yol qəzası", "hadisə", "qəza", "yanğın", "hava", "təhsil", "məktəb", "universitet",
                 "tələbə", "məhkəmə", "polis", "həkim", "xəstəxana", "yağış", "sel", "fəsad",
                 "köçkün", "insident", "kaza", "yangın", "eğitim", "sağlık", "təcili tibbi", "bərk", "duman"],
    "Həyat": ["sağlıq","həkim","xəstəlik","tibbi","vitamin","pəhriz","psixologiya",
              "sağlamlıq","sağlık","beslenme","diyet","həyat tərzi","məsləhət","profilaktika"],
    "Dünya": ["bmt", "nato", "rusiya", "çin", "fransa", "almanya", "iran", "israil", "ukrayna",
              "dəməşq", "suriya", "lebnon", "ərəb", "abş", "ingiltərə", "pakistan", "hindistan",
              "qüds", "beynəlxalq", "ermənistan", "gürcüstan",
              "dış politika", "world", "middle east", "europe", "путин", "трамп", "зеленский", "байден", "макрон", "эрдоган"],
}
# İdman bölməsi gücləndirilib: xallar 2 qat sayılır
BOOST = {"İdman": 2, "Prezident": 3}
SLUGS = {"Prezident":"prezident","Gündəm":"gundem","Siyasət":"siyaset","Cəmiyyət":"cemiyyet",
         "İqtisadiyyat":"iqtisadiyyat","Dünya":"dunya","İdman":"idman","Mədəniyyət":"medeniyyet"}
DOUBLE = {"iran","rusiya","çin","fransa","israil","ukrayna","abş","ingiltərə","almanya","türkiyə","ermənistan","gürcüstan"}
FALLBACK = "Gündəm"
ROOT = pathlib.Path(__file__).parent
OUT_DIR = ROOT / "data"
OUT_FILE = OUT_DIR / "news.json"
MAX_ITEMS = 500

def norm_az(s):
    return s.lower().replace("i̇", "i")

def detect_lang(title, desc, default):
    """Dil təyini: kiril→ru, 'ə'→az (türkdə yoxdur), ı/ğ/İ→tr, əks halda mənbə dili."""
    blob = title + " " + desc
    if re.search(r"[а-яА-Я]", blob):
        return "ru"
    if "ə" in blob or "Ə" in blob:
        return "az"
    if "ı" in blob or "ğ" in blob or "İ" in blob:
        return "tr"
    return default if default else "en"

def fetch(url):
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (8ulduz bot)"})
    with urllib.request.urlopen(req, timeout=20) as r:
        return r.read()

def text_of(el, names):
    for n in names:
        node = el.find(n)
        if node is not None and node.text:
            return node.text.strip()
    return ""

def parse_feed(xml_bytes):
    items = []
    try:
        root = ET.fromstring(xml_bytes)
    except ET.ParseError:
        return items
    for item in root.iter("item"):
        title = text_of(item, ["title"])
        link = text_of(item, ["link"])
        desc = text_of(item, ["description"])
        pub = text_of(item, ["pubDate", "date", "published", "updated"])
        author = text_of(item, ["{http://purl.org/dc/elements/1.1/}creator", "author"])
        if title and link:
            items.append({"title": title, "link": link,
                          "description": re.sub(r"<[^>]+>", "", desc)[:400], "pubDate": pub,
                          "author": author})
    ns = {"a": "http://www.w3.org/2005/Atom"}
    for entry in root.findall(".//a:entry", ns):
        title = text_of(entry, ["a:title", "{http://www.w3.org/2005/Atom}title"])
        link = ""
        le = entry.find("a:link", ns)
        if le is not None:
            link = le.get("href", "")
        desc = text_of(entry, ["a:summary", "a:content"])
        pub = text_of(entry, ["a:published", "a:updated"])
        if title and link:
            items.append({"title": title, "link": link,
                          "description": re.sub(r"<[^>]+>", "", desc)[:400], "pubDate": pub})
    return items

def to_iso(pub):
    if not pub:
        return datetime.datetime.now(datetime.timezone.utc).isoformat()
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
        return datetime.datetime.fromisoformat(pub.replace("Z", "+00:00")).isoformat()
    except Exception:
        return datetime.datetime.now(datetime.timezone.utc).isoformat()

def categorize(title, desc):
    blob = norm_az(title + " " + desc)
    best, best_hits = FALLBACK, 0
    scores = {}
    for cat, words in CATEGORIES.items():
        hits = 0
        for w in words:
            if norm_az(w) in blob:
                hits += 2 if (" " in w or w in DOUBLE) else 1
        hits *= BOOST.get(cat, 1)
        scores[cat] = hits
        if hits > best_hits:
            best, best_hits = cat, hits
    if any(norm_az(s) in blob for s in STOPWORDS) and best == "İqtisadiyyat":
        scores.pop("İqtisadiyyat")
        m = max(scores.values())
        best = max(scores, key=scores.get) if m > 0 else FALLBACK
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

def make_article(it, source, default_lang):
    lang = detect_lang(it["title"], it["description"], default_lang)
    label = categorize(it["title"], it["description"])
    if label == "Prezident" and lang in ("tr", "en"):
        label = "Siyasət"
    return {
        "id": hashlib.sha1(it["link"].encode()).hexdigest()[:16],
        "title": it["title"],
        "summary": it["description"],
        "category": SLUGS.get(label, "gundem"),
        "source": source,
        "sourceUrl": it["link"],
        "publishedAt": to_iso(it["pubDate"]),
        "imageUrl": None,
        "lang": lang,
        "author": it.get("author", ""),
        "video": is_video(it),
    }

def main():
    try:
        old = json.loads(OUT_FILE.read_text(encoding="utf-8"))["articles"]
    except Exception:
        old = []
    old = [a for a in old if not is_junk(a.get("sourceUrl", ""))]
    old = [a for a in old if not is_negative_about_leadership(a.get("title", ""), a.get("summary", ""))]
    # köhnə xəbərlərin dili yoxdursa — avtomatik təyin et (süzgəcin düzgün işləməsi üçün)
    for a in old:
        if not a.get("lang"):
            a["lang"] = detect_lang(a.get("title", ""), a.get("summary", ""), "")
        # Zuğulba-ya səhv düşmüş köhnə xəbərləri yenidən kateqoriyalaşdır
        if a.get("category") == "prezident":
            lbl = categorize(a.get("title", ""), a.get("summary", ""))
            if lbl != "Prezident":
                a["category"] = SLUGS.get(lbl, "gundem")
    seen = {a["sourceUrl"] for a in old}
    new_items, errors = [], []
    for source, url, dlang in FEEDS:
        try:
            for it in parse_feed(fetch(url)):
                if it["link"] in seen or is_junk(it["link"]):
                    continue
                seen.add(it["link"])
                if is_negative_about_leadership(it["title"], it["description"]):
                    continue
                new_items.append(make_article(it, source, dlang))
        except Exception as e:
            errors.append(f"{source}: {type(e).__name__}")
    new_items.sort(key=lambda a: a["publishedAt"], reverse=True)
    old = sorted(old, key=lambda a: a.get("publishedAt", ""), reverse=True)
    uniq, dseen = [], set()
    for a in (new_items + old):
        if a["sourceUrl"] not in dseen:
            dseen.add(a["sourceUrl"]); uniq.append(a)
    articles = uniq[:MAX_ITEMS]
    data = {
        "updatedAt": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "count": len(articles),
        "articles": articles,
    }
    OUT_DIR.mkdir(exist_ok=True)
    OUT_FILE.write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")
    ok = len(FEEDS) - len(errors)
    print(f"Mənbə işlədi: {ok}/{len(FEEDS)} | Yeni: {len(new_items)} | Ümumi: {len(articles)}")
    for e in errors:
        print("  !", e)

if __name__ == "__main__":
    main()
