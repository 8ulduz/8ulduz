# -*- coding: utf-8 -*-
"""
8ulduz — avtomatik xəbər yeniləyici (süni intellektsiz, kvotasız)
Mənbələrdən RSS xəbərlərini oxuyur, 8 bölməyə açar sözlərlə ayırır,
news.json faylını yeniləyir. GitHub Actions hər 15 dəqiqədə işə salır.
"""
import json, re, sys, datetime, pathlib
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

CATEGORIES = {
    "Siyasət":      ["prezident", "ilham əliyev", "mehriban əliyeva", "ərdoğan", "erdogan",
                     "təyinat", "sərəncam", "səfir", "parlament", "milli məclis", "seçki",
                     "nazir", "bəyanat", "zəngəzur", "qarabağ", "türkiyə", "diplomat",
                     "tccb", "dışişleri", "seçim", "bakan", "cumhurbaşkanı", "politics",
                     "election", "minister", "summit", "ukraine", "gaza", "israel"],
    "İqtisadiyyat": ["neft", "oil", "qiymət", "manat", " dollar", "valyuta", "tərəvəz",
                     "inflyasiya", "maliyyə", "bank", "vergi", "sahibkar", "ixrac", "idxal",
                     "qaz", "enerji", "faiz", "maaş", "pensiya", "büdcə", "ifa", "borsa",
                     "ekonomi", "merkez bankası", "enflasyon", "faiz", "economy", "market"],
    "İdman":        ["futbol", " AFFA", "milli komanda", "qarabağ fk", "azərbaycan kuboku",
                     "çempion", "oyun", "matç", "məşqçi", "qol", "turnir", "cüdo", "idman",
                     "formula", "grand prix", "tennis", "basketbol", "voleybol", "transfer",
                     "fenerbahçe", "galatasaray", "beşiktaş", "trabzonspor", "maç", "gol",
                     "şampiyon", "süper lig", "la liga", "premier league", "champions"],
    "Mədəniyyət":   ["film", "kino", "sərgi", "muzey", "teatr", "musiqi", "konsert", "kitab",
                     "şair", "yazıçı", "əsər", "incəsənət", "sənətkar", "festival", "mükafat",
                     "sinema", "kitap", "roman", "sanat", "sergi", "concert", "culture"],
    "Cəmiyyət":     ["yol", "hadisə", "qəza", "yanğın", "hava", "təhsil", "məktəb", "universitet",
                     "tələbə", "məhkum", "məhkəmə", "polis", "həkim", "xəstəxana", "təcili",
                     "köçkün", "məişət", "insident", "kaza", "yangın", "eğitim", "sağlık"],
    "Dünya":        ["bmt", "ab", "nato", "rusiya", "çin", "amerika", "fransa", "almanya",
                     "iran", "israil", "dəməşq", "suriya", "lebnon", "ərəb", "bayden",
                     "trump", "putin", "zelenski", "orusalem", "dünya", "beynəlxalq",
                     "dunya", "dış politika", "world", "middle east", "europe", "asia"],
}
FALLBACK = "Gündəm"

NEWS_FILE = pathlib.Path(__file__).parent / "news.json"
MAX_ITEMS = 250
VIDEO_SOURCES_HINT = ["youtube", "video", "youtu.be"]

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
    # Atom formatı üçün
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
    blob = (title + " " + desc).lower()
    best, best_hits = FALLBACK, 0
    for cat, words in CATEGORIES.items():
        hits = sum(1 for w in words if w.lower() in blob)
        if hits > best_hits:
            best, best_hits = cat, hits
    return best

def normalize_date(pub):
    if not pub:
        return ""
    return pub  # RSS formatını olduğu kimi saxlayırıq; saytda qısa formaya salınır

def main():
    try:
        old = json.loads(NEWS_FILE.read_text(encoding="utf-8"))
    except Exception:
        old = []
    seen = {n["link"] for n in old}
    new_items, errors = [], []
    for source, url in FEEDS.items():
        try:
            for it in parse_feed(fetch(url)):
                if it["link"] in seen:
                    continue
                it["category"] = categorize(it["title"], it["description"])
                it["source"] = source
                it["pubDate"] = normalize_date(it["pubDate"])
                it["isVideo"] = any(h in (it["link"] + it["title"]).lower() for h in VIDEO_SOURCES_HINT)
                new_items.append(it)
        except Exception as e:
            errors.append(f"{source}: {e}")
    all_news = (new_items + old)[:MAX_ITEMS]
    NEWS_FILE.write_text(json.dumps(all_news, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"Yeni: {len(new_items)} | Ümumi: {len(all_news)} | Xətalı mənbə: {len(errors)}")
    for e in errors:
        print("  !", e)

if __name__ == "__main__":
    main()
