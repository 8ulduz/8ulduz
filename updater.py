# -*- coding: utf-8 -*-
"""
8ulduz — avtomatik xəbər yeniləyici (süni intellektsiz, kvotasız)
"""
import json, re, pathlib
import urllib.request
import xml.etree.ElementTree as ET

FEEDS = {
    "AZƏRTAC":       "https://azertag.az/rss",
    "APA":           "https://apa.az/rss",
    "Report":        "https://report.az/rss/",
    "Trend":         "https://www.trend.az/rss/",
    "BBC News":      "https://feeds.bbci.co.uk/news/world/rss.xml",
    "Al Jazeera":    "https://www.aljazeera.com/xml/rss/all.xml",
    "Daily Sabah":   "https://www.dailysabah.com/rss",
    "Hürriyet":      "https://www.hurriyet.com.tr/rss/anasayfa",
}

SKIP_URL_PARTS = ["/resmi-ilanlar/", "/lezizz/", "/emlak-ilanlari/"]
STOPWORDS = ["neftçala", "neftchala", "ceyran", "xəzər"]

CATEGORIES = {'Siyasət': ['prezident', 'ilham əliyev', 'mehriban əliyeva', 'ərdoğan', 'erdogan', 'sərəncam', 'səfir', 'parlament', 'milli məclis', 'seçki', 'səfirlik', 'nazir', 'bəyanat', 'zəngəzur', 'türkiyə', 'diplomat', 'media və yayım şurası', 'dışişleri', 'seçim', 'bakan', 'cumhurbaşkanı', 'politics', 'siyasi', 'election', 'minister', 'summit', 'ukraine', 'gaza', 'israel', 'məsləhətləşmə', 'qarabağda', 'qarabağın', 'qarabağ münaqişəsi', 'dəhliz', 'sülh müqaviləsi', 'məclis'], 'İqtisadiyyat': ['neft', 'oil', 'qiymət', 'manat', 'dollar', 'valyuta', 'büdcə', 'inflyasiya', 'maliyyə', 'bank', 'vergi', 'sahibkar', 'ixrac', 'idxal', 'qaz', 'enerji', 'faiz', 'maaş', 'pensiya', 'borsa', 'dotasiya', 'məzənnə', 'ekonomi', 'merkez bankası', 'enflasyon', 'economy', 'market', 'dövlət büdcəsi'], 'İdman': ['futbol', 'affa', 'milli komanda', 'qarabağ fk', 'kuboku', 'avropa liqası', 'çempion', 'oyun', 'matç', 'məşqçi', 'qol', 'turnir', 'cüdo', 'neftçi', 'formula', 'grand prix', 'basketbol', 'voleybol', 'transfer', 'konfrans liqası', 'fenerbahçe', 'galatasaray', 'beşiktaş', 'trabzonspor', 'maç', 'sabah fk', 'şampiyon', 'süper lig', 'premier league', 'champions', 'uefa', 'fifa', 'zirə', 'turan'], 'Mədəniyyət': ['film', 'kino', 'sərgi', 'muzey', 'teatr', 'musiqi', 'konsert', 'kitab', 'şair', 'yazıçı', 'əsər', 'incəsənət', 'festival', 'mükafat', 'şarkı', 'sinema', 'kitap', 'roman', 'sanat', 'sergi', 'concert', 'culture', 'albüm', 'oyuncu'], 'Cəmiyyət': ['yol qəzası', 'hadisə', 'qəza', 'yanğın', 'hava', 'təhsil', 'məktəb', 'universitet', 'tələbə', 'məhkəmə', 'polis', 'həkim', 'xəstəxana', 'yağış', 'sel', 'fəsad', 'köçkün', 'insident', 'kaza', 'yangın', 'eğitim', 'sağlık', 'təcili tibbi', 'bərk', 'duman'], 'Dünya': ['bmt', 'nato', 'rusiya', 'çin', 'fransa', 'almanya', 'iran', 'israil', 'ukrayna', 'dəməşq', 'suriya', 'lebnon', 'ərəb', 'abş', 'ingiltərə', 'pakistan', 'hindistan', 'trump', 'putin', 'zelenski', 'qüds', 'beynəlxalq', 'ermənistan', 'gürcüstan', 'dış politika', 'world', 'middle east', 'europe']}

DOUBLE = ['abş', 'almanya', 'ermənistan', 'fransa', 'gürcüstan', 'ingiltərə', 'iran', 'israil', 'rusiya', 'türkiyə', 'ukrayna', 'çin']
FALLBACK = "Gündəm"
NEWS_FILE = pathlib.Path(__file__).parent / "news.json"
MAX_ITEMS = 250

def norm_az(s):
    return s.lower().replace("i\u0307", "i")

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
        if title and link:
            items.append({"title": title, "link": link,
                          "description": re.sub(r"<[^>]+>", "", desc)[:400], "pubDate": pub})
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

def categorize(title, desc):
    blob = norm_az(title + " " + desc)
    best, best_hits = FALLBACK, 0
    scores = {}
    for cat, words in CATEGORIES.items():
        hits = 0
        for w in words:
            if norm_az(w) in blob:
                hits += 2 if (" " in w or w in DOUBLE) else 1
        scores[cat] = hits
        if hits > best_hits:
            best, best_hits = cat, hits
    if any(norm_az(s) in blob for s in STOPWORDS) and best == "İqtisadiyyat":
        scores.pop("İqtisadiyyat")
        m = max(scores.values())
        best = max(scores, key=scores.get) if m > 0 else FALLBACK
    return best

def is_junk(link):
    l = norm_az(link)
    return any(p in l for p in SKIP_URL_PARTS)

def main():
    try:
        old = json.loads(NEWS_FILE.read_text(encoding="utf-8"))
    except Exception:
        old = []
    old = [n for n in old if not is_junk(n.get("link", ""))]
    seen = {n["link"] for n in old}
    new_items, errors = [], []
    for source, url in FEEDS.items():
        try:
            for it in parse_feed(fetch(url)):
                if it["link"] in seen or is_junk(it["link"]):
                    continue
                seen.add(it["link"])
                it["category"] = categorize(it["title"], it["description"])
                it["source"] = source
                it["isVideo"] = "video" in norm_az(it["link"] + it["title"])
                new_items.append(it)
        except Exception as e:
            errors.append(f"{source}: {e}")
    uniq, dseen = [], set()
    for n in (new_items + old):
        if n["link"] not in dseen:
            dseen.add(n["link"]); uniq.append(n)
    all_news = uniq[:MAX_ITEMS]
    NEWS_FILE.write_text(json.dumps(all_news, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"Yeni: {len(new_items)} | Ümumi: {len(all_news)} | Xətalı mənbə: {len(errors)}")
    for e in errors:
        print("  !", e)

if __name__ == "__main__":
    main()
