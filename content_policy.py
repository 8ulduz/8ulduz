"""QIRMIZI XƏTT 2 (docs/qirmizi-xetler.md): məzmun qaydası bir yerdədir.

Qaydalar assets/content-policy.js faylındadır (brauzer də onu oxuyur). Üç yoxlama:
- icazəli siyahı: mənbə siyahıda deyilsə və ya keçid onun saytına aparmırsa xəbər düşmür;
- qadağan olunmuş saytlar heç vaxt düşmür;
- xarici mənbələrin Azərbaycan və rəhbərliyi haqqında xəbərləri düşmür. İstisna yalnız idman saytlarıdır (sportSources), rəhbərlik adı keçmirsə.
"""
import ipaddress
import json
import pathlib
import re
import urllib.parse

_FILE = pathlib.Path(__file__).resolve().parent / "assets" / "content-policy.js"


def _load():
    text = _FILE.read_text(encoding="utf-8")
    return json.loads(text[text.index("{"):text.rindex("}") + 1])


POLICY = _load()
AZ_SOURCES = POLICY["azSources"]
WORLD_SOURCES = POLICY["worldSources"]
SPORT_SOURCES = frozenset(POLICY["sportSources"])
VIDEO_CHANNELS = frozenset(POLICY["videoChannels"])
BLOCKED_HOSTS = tuple(POLICY["blockedHosts"])
AZ_TERMS = re.compile(POLICY["azTerms"], re.I)
LEADER_TERMS = re.compile(POLICY["leaderTerms"], re.I)


def host_of(url):
    try:
        host = (urllib.parse.urlparse(url or "").hostname or "").lower()
    except ValueError:
        return ""
    return host[4:] if host.startswith("www.") else host


def _on(host, domains):
    return any(host == d or host.endswith("." + d) for d in domains)


def safe_url(url):
    """Yalnız açıq internetdəki http(s) ünvanı: daxili ünvana sorğu getməsin, «evil.com\@sayt.az» saytımızda başqa sayt açmasın."""
    text = str(url or "").strip()
    if not text.lower().startswith(("http://", "https://")) or "\\" in text or any(ord(c) < 32 or ord(c) == 127 for c in text):
        return False
    try:
        parts = urllib.parse.urlsplit(text)
        host = (parts.hostname or "").lower().rstrip(".")
    except ValueError:
        return False
    if not host or parts.username is not None or host == "localhost" or host.endswith((".localhost", ".local", ".internal")):
        return False
    last = host.rsplit(".", 1)[-1]
    if ":" in host or last.isdigit() or last.startswith("0x"):  # 127.1 və 0x7f.1 də ünvandır
        try:
            return ipaddress.ip_address(host).is_global
        except ValueError:
            return False
    return True


def is_blocked(url):
    return _on(host_of(url), BLOCKED_HOSTS)


def source_registered(name):
    return name in AZ_SOURCES or name in WORLD_SOURCES


def source_allowed(name, url):
    """Mənbə icazəli siyahıdadır və keçid onun öz saytına aparır."""
    domains = AZ_SOURCES.get(name) or WORLD_SOURCES.get(name)
    host = host_of(url)
    # javascript://sayt.az/... ünvanının da «host»u olur: yalnız açıq internetdəki http(s) keçidi qəbul edilir.
    secure = safe_url(url)
    return secure and bool(domains) and bool(host) and _on(host, domains) and not is_blocked(url)


def foreign_about_azerbaijan(source, category, title, desc=""):
    if source not in WORLD_SOURCES:
        return False
    text = f"{title} {desc or ''}"
    # Bölmə avtomatik təyin olunur, səhv ola bilər: istisna bölməyə yox, idman saytının özünə verilir.
    if category == "idman" and source in SPORT_SOURCES:
        return bool(LEADER_TERMS.search(text))
    return bool(AZ_TERMS.search(text))


def violation(article):
    """Qayda pozulubsa səbəb, pozulmayıbsa None."""
    source, url = article.get("source"), article.get("sourceUrl")
    if is_blocked(url):
        return "qadağan olunmuş sayt"
    if not source_allowed(source, url):
        return "icazəli siyahıda deyil"
    if foreign_about_azerbaijan(source, article.get("category"), article.get("title", ""), article.get("summary", "")):
        return "xarici mənbə, Azərbaycan mövzusu"
    return None


def clean_alts(article):
    """Eyni xəbərin digər mənbələri də yoxlanır. Xəbər Azərbaycan haqqındadırsa xarici mənbə ona bağlanmır."""
    if not article.get("alts"):
        return article
    about_az = bool(AZ_TERMS.search(f"{article.get('title', '')} {article.get('summary', '')}"))
    category = article.get("category")
    def keep(alt):
        source = alt.get("source")
        if not source_allowed(source, alt.get("sourceUrl")):
            return False
        if foreign_about_azerbaijan(source, category, alt.get("title", "")):
            return False
        return not (about_az and source in WORLD_SOURCES and not (category == "idman" and source in SPORT_SOURCES))
    alts = [alt for alt in article["alts"] if keep(alt)]
    return article if len(alts) == len(article["alts"]) else {**article, "alts": alts}


def enforce(articles):
    """Son qapı: (təmiz siyahı, {səbəb: say}). Yazılan hər fayl bundan keçir."""
    clean, dropped = [], {}
    for article in articles:
        reason = violation(article)
        if reason:
            dropped[reason] = dropped.get(reason, 0) + 1
            continue
        clean.append(clean_alts(article))
    return clean, dropped
