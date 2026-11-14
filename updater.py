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
import collections, json, re, pathlib, hashlib, datetime, email.utils, html, sys, os, time, unicodedata, math
import urllib.request, urllib.parse, urllib.error, base64, zlib
import xml.etree.ElementTree as ET
import content_policy
from reader_content import update_reader
from concurrent.futures import ThreadPoolExecutor, wait
import threading
from zoneinfo import ZoneInfo


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
    # Baku TV Google News sitemap-ı ilə. Caliber.az (yalnız rus/ingilis, Yandex Turbo lenti) yoxdur.
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
    ("Nocomment.az", "https://nocomment.az/feed"),
    ("Mia.az",       "https://mia.az/feed"),
    ("Aia.az",       "https://aia.az/rss.xml"),
    ("Oxu24.com",    "https://oxu24.com/sitemap-news.xml"),  # /feed 2 MB-dır, bu 70 KB
    ("Baku.ws",      "https://baku.ws/rss"),
    ("Naxçıvan Xəbərləri", "https://naxcivanxeberleri.az/"),
]
# Xarici mənbələr: (ad, url, dil[, kateqoriya ipucu])
WORLD_FEEDS = [
    ("BBC News",     "https://feeds.bbci.co.uk/news/world/rss.xml",           "en"),
    ("Al Jazeera",   "https://www.aljazeera.com/xml/rss/all.xml",             "en"),
    ("Daily Sabah",  "https://www.dailysabah.com/rss/all",                    "en"),
    ("Euronews",     "https://www.euronews.com/rss",                          "en"),
    ("DW",           "https://rss.dw.com/xml/rss-en-all",                     "en"),
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
    ("Sports.kz",    "https://www.sports.kz/rss",                             "ru", "İdman"),
    # İngilis və rus dilində mənbələr (2026-11-04, sahibin istəyi: xaricdən gələn oxucu üçün geniş və şaxəli lent).
    # Hamısı həmin gün yoxlanıb: 200 cavab, təzə elementlər. Ağır lentlər (RBC 256 KB, Tengrinews 715 KB, Спорт-Экспресс 521 KB,
    # Daryo 265 KB, NASA 270 KB, iXBT 235 KB, Naked Science 171 KB) SLOW_ONLY_FEEDS-dədir: dəqiqəlik dövrə onları oxumur.
    # Yoxlanıb götürülməyənlər: CNN (lent 2023-dən yenilənmir), RIA (açılmır), Reuters/AP (açıq RSS yoxdur), Al Arabiya,
    # Arab News, ATP (403), ESPN, Goal, UEFA, Gulf News, Kyodo, Kazinform, TRT World, Zakon.kz (404), Forbes.ru (HTML).
    ("Guardian World", "https://www.theguardian.com/world/rss",                "en"),
    ("NYT World",    "https://rss.nytimes.com/services/xml/rss/nyt/World.xml", "en"),
    ("Sky News",     "https://feeds.skynews.com/feeds/rss/world.xml",         "en"),
    ("France 24",    "https://www.france24.com/en/rss",                       "en"),
    ("NPR",          "https://feeds.npr.org/1004/rss.xml",                    "en"),
    ("CBS News",     "https://www.cbsnews.com/latest/rss/world",              "en"),
    ("ABC News",     "https://abcnews.go.com/abcnews/internationalheadlines", "en"),
    ("The Independent", "https://www.independent.co.uk/news/world/rss",       "en"),
    ("AA English",   "https://www.aa.com.tr/en/rss/default?cat=politics",     "en"),
    ("AA Economy",   "https://www.aa.com.tr/en/rss/default?cat=economy",      "en", "İqtisadiyyat"),
    ("AA Sport",     "https://www.aa.com.tr/en/rss/default?cat=sports",       "en", "İdman"),
    ("TASS English", "https://tass.com/rss/v2.xml",                           "en"),
    ("Times of India", "https://timesofindia.indiatimes.com/rssfeeds/296589292.cms", "en"),
    ("Politico Europe", "https://www.politico.eu/feed/",                      "en"),
    ("Euractiv",     "https://www.euractiv.com/feed/",                        "en"),
    ("Foreign Policy", "https://foreignpolicy.com/feed/",                     "en"),
    ("The Diplomat", "https://thediplomat.com/feed/",                         "en"),
    ("The Economist", "https://www.economist.com/latest/rss.xml",             "en"),
    ("Vox",          "https://www.vox.com/rss/index.xml",                     "en"),
    ("The Astana Times", "https://astanatimes.com/feed/",                     "en"),
    ("Daryo",        "https://daryo.uz/en/feed",                              "en"),
    ("Kun.uz English", "https://kun.uz/en/news/rss",                          "en"),
    ("BBC Business", "https://feeds.bbci.co.uk/news/business/rss.xml",        "en", "İqtisadiyyat"),
    ("BBC Technology", "https://feeds.bbci.co.uk/news/technology/rss.xml",    "en", "Texnologiya"),
    ("BBC Science",  "https://feeds.bbci.co.uk/news/science_and_environment/rss.xml", "en", "Təhsil"),
    ("BBC Health",   "https://feeds.bbci.co.uk/news/health/rss.xml",          "en", "Həyat"),
    ("BBC Culture",  "https://feeds.bbci.co.uk/news/entertainment_and_arts/rss.xml", "en", "Mədəniyyət"),
    ("Guardian Business", "https://www.theguardian.com/uk/business/rss",      "en", "İqtisadiyyat"),
    ("Guardian Technology", "https://www.theguardian.com/uk/technology/rss",  "en", "Texnologiya"),
    ("Guardian Science", "https://www.theguardian.com/science/rss",           "en", "Təhsil"),
    ("Guardian Culture", "https://www.theguardian.com/uk/culture/rss",        "en", "Mədəniyyət"),
    ("Daily Sabah Business", "https://www.dailysabah.com/rss/business",       "en", "İqtisadiyyat"),
    ("Daily Sabah Sports", "https://www.dailysabah.com/rss/sports",           "en", "İdman"),
    ("CNBC",         "https://www.cnbc.com/id/100727362/device/rss/rss.html", "en", "İqtisadiyyat"),
    ("MarketWatch",  "https://feeds.content.dowjones.io/public/rss/mw_topstories", "en", "İqtisadiyyat"),
    ("Fortune",      "https://fortune.com/feed/",                             "en", "İqtisadiyyat"),
    ("OilPrice",     "https://oilprice.com/rss/main",                         "en", "İqtisadiyyat"),
    ("Bloomberg",    "https://feeds.bloomberg.com/markets/news.rss",          "en", "İqtisadiyyat"),
    ("Financial Times", "https://www.ft.com/rss/home",                        "en", "İqtisadiyyat"),
    ("TechCrunch",   "https://techcrunch.com/feed/",                          "en", "Texnologiya"),
    ("The Verge",    "https://www.theverge.com/rss/index.xml",                "en", "Texnologiya"),
    ("Ars Technica", "https://feeds.arstechnica.com/arstechnica/index",       "en", "Texnologiya"),
    ("Wired",        "https://www.wired.com/feed/rss",                        "en", "Texnologiya"),
    ("Engadget",     "https://www.engadget.com/rss.xml",                      "en", "Texnologiya"),
    ("ScienceDaily", "https://www.sciencedaily.com/rss/all.xml",              "en", "Təhsil"),
    ("New Scientist", "https://www.newscientist.com/feed/home/",              "en", "Təhsil"),
    ("NASA",         "https://www.nasa.gov/news-release/feed/",               "en", "Təhsil"),
    ("Phys.org",     "https://phys.org/rss-feed/",                            "en", "Təhsil"),
    ("Nature",       "https://www.nature.com/nature.rss",                     "en", "Təhsil"),
    ("Variety",      "https://variety.com/feed/",                             "en", "Mədəniyyət"),
    ("Hollywood Reporter", "https://www.hollywoodreporter.com/feed/",         "en", "Mədəniyyət"),
    ("Rolling Stone", "https://www.rollingstone.com/feed/",                   "en", "Mədəniyyət"),
    ("Deadline",     "https://deadline.com/feed/",                            "en", "Mədəniyyət"),
    ("Sky Sports",   "https://www.skysports.com/rss/12040",                   "en", "İdman"),
    ("РБК",          "https://rssexport.rbc.ru/rbcnews/news/30/full.rss",     "ru"),
    ("Коммерсантъ",  "https://www.kommersant.ru/RSS/main.xml",                "ru"),
    ("Lenta.ru",     "https://lenta.ru/rss/top7",                             "ru"),
    ("Известия",     "https://iz.ru/xml/rss/all.xml",                         "ru"),
    ("Ведомости",    "https://www.vedomosti.ru/rss/news",                     "ru", "İqtisadiyyat"),
    ("AA Русский",   "https://www.aa.com.tr/ru/rss/default?cat=guncel",       "ru"),
    ("DW Русский",   "https://rss.dw.com/xml/rss-ru-all",                     "ru"),
    ("Euronews Русский", "https://ru.euronews.com/rss",                       "ru"),
    ("BBC Русская служба", "https://feeds.bbci.co.uk/russian/rss.xml",        "ru"),
    ("24.kg",        "https://24.kg/rss/",                                    "ru"),
    ("Tengrinews",   "https://tengrinews.kz/news.rss",                        "ru"),
    ("Газета.uz",    "https://www.gazeta.uz/ru/rss/",                         "ru"),
    ("Kun.uz Русский", "https://kun.uz/ru/news/rss",                          "ru"),
    ("Habr",         "https://habr.com/ru/rss/news/?fl=ru",                   "ru", "Texnologiya"),
    ("3DNews",       "https://3dnews.ru/news/rss/",                           "ru", "Texnologiya"),
    ("iXBT",         "https://www.ixbt.com/export/news.rss",                  "ru", "Texnologiya"),
    ("N+1",          "https://nplus1.ru/rss",                                 "ru", "Təhsil"),
    ("Naked Science", "https://naked-science.ru/feed",                        "ru", "Təhsil"),
    ("Афиша Daily",  "https://daily.afisha.ru/rss/",                          "ru", "Mədəniyyət"),
    ("Sports.ru",    "https://www.sports.ru/rss/all_news.xml",                "ru", "İdman"),
    ("Спорт-Экспресс", "https://www.sport-express.ru/services/materials/news/se/", "ru", "İdman"),
    ("TASS Sport",   "https://tass.ru/rss/v2.xml?sections=sport",             "ru", "İdman"),
    ("Interfax Sport", "https://www.sport-interfax.ru/rss",                   "ru", "İdman"),
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
    "birinci vitse-prezident", "ali baş komandan", "azərbaycan lideri",
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
# "X prezidenti" (məs. "Azercell prezidenti", "Fənərbağçanın prezidentinə") başqasının prezidentidir — bütün hallarda sayılmır.
# «Prezidentlər», «prezidentlə», «prezidentlik» də kimin olduğunu demir. «Prezidentin tapşırığı» isə qalır.
PRESIDENT_WEAK_RX = re.compile(r"(?<!\w)(?:prezident(?!i(?!\w)|in[iəd]|l)|dövlət başçısı|ölkə başçısı)")
PRESIDENT_WEAK_EXTRA = ["sərəncam", "fərman", "təltif"]
# Xarici kontekst: "Braziliyada prezident seçkiləri" kimi xəbərlər Prezident bölməsinə düşməsin
SOCIAL_FOREIGN = ["dünyada", "в мире", "росси", "москв", "сша", "европ", "турци", "украин", "грузи", "армени", "казахстан", "герман", "франц", "китай"]
FOREIGN_MARKERS = [
    "abş", "amerika", "braziliya", "bolqarıstan", "rusiya", "türkiyə", "fransa", "almaniya",
    "ukrayna", "gürcüstan", "ermənistan", "iran", "qazaxıstan", "özbəkistan", "qırğızıstan",
    "tacikistan", "türkmənistan", "belarus", "polşa", "serbiya", "rumıniya", "moldova",
    "çin", "hindistan", "pakistan", "misir", "suriya", "israil", "fələstin", "argentina",
    "meksika", "venesuela", "kolumbiya", "cənubi koreya", "koreya", "yaponiya", "italiya",
    "ispaniya", "portuqaliya", "macarıstan", "çexiya", "slovakiya", "avstriya", "finlandiya",
    "litva", "latviya", "estoniya", "əfqanıstan", "iraq", "liviya", "tunis", "əlcəzair",
    "nigeriya", "keniya", "cənubi afrika", "kanada", "avstraliya", "filippin", "indoneziya",
    "yəmən", "husi", "çex respublika", "səudiyyə", "livan", "iordaniya", "qətər", "yunanıstan", "albaniya", "xorvatiya",
    "bolsonaro", "bolsonaru", "keçmiş prezident", "sabiq prezident", "eks-prezident", "eks prezident", "prezident təqaüd",
    "tramp", "trump", "putin", "ərdoğan", "makron", "zelenski", "paşinyan", "tokayev",
    "mirziyoyev", "lukaşenko", "pezeşkiyan", "si szinpin", "lula", "milei", "bayden",
    "fifa prezidenti", "uefa prezidenti", "federasiyasının prezidenti", "klubun prezidenti",
    "prezidentliyə namizəd", "prezident seçki",
    # «Vaşinqtonda hansı partiyanın namizədi prezident ola biləcək?» (Baku TV, 2026-11-09): ölkə adı yox, paytaxt və seçki dili var.
    # Bizim Prezident artıq prezidentdir: «prezident ola(caq)», «namizədi prezident» başqa ölkənin seçkisidir.
    "vaşinqton", "ağ ev", "prezident ola", "namizədi prezident", "prezident namizəd",
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
                        "minimum əmək haqqı", "yaşayış minimumu",
                        # Maaş, iş yeri, əmək hüququ: millət vəkili və ekspert müsahibələri əsasən bu sözlərlə gəlir.
                        "əməkhaqq", "əmək haqq", "maaşlar", "maaşların", "maaş artım", "maaşı artır", "minimum maaş", "ehtiyac meyar",
                        "əmək bazar", "əmək müqavilə", "əmək məcəllə", "əmək staj", "əmək kitabça", "əmək mübahisə", "əmək hüquq",
                        "işaxtaran", "vakansiya", "yeni iş yeri", "iş yeri açıl", "iş yerləri açıl", "iş yeri yaradıl", "iş yerləri yaradıl", "işdən çıxan",
                        "təqaüdə çıx", "təqaüd yaşı", "sosial siyasət", "sosial xidmət", "sosial dəstək", "sosial müavinət", "sosial mənzil",
                        "uşaq pulu", "uşaqpulu", "əlillər", "müharibə veteran", "məcburi köçkün", "dost evi", "əmək və əhalinin",
                        "musa quliyev", "anar əliyev",
                        "пенси", "пособи", "безработ", "прожиточн", "соцзащит", "зарплат", "минтруд", "муса гулиев"],
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
                    "artificial intelligence", " ai ", "space", "smartphone", "tech", "software", "app ", "cyber", "chip", "nasa", "spacex", "rocket",
                    # 2026-11-14: «WhatsApp ve Telegram sesli aramalarını kaydetme özelliği geliyor» (CNN Türk) texnologiya sözü tapmayıb İdmana düşmüşdü.
                    "whatsapp", "samsung", "xiaomi", "huawei", "mesajlaşma", "voip", "мессенджер"],
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
FIRST_FILE = OUT_DIR / "first.json"
CACHE_DIR = ROOT / ".cache"  # yalnız runner-də, repoya düşmür
FEED_CACHE = CACHE_DIR / "feeds.json"
SLOW_FEED_CACHE = CACHE_DIR / "feeds-slow.json"
OFFICIAL_CACHE = CACHE_DIR / "official.json"
UNDATED_FILE = CACHE_DIR / "undated.json"
RECENT_FILE = CACHE_DIR / "recent.json"
LINK_HEALTH_FILE = CACHE_DIR / "link_health.json"
GNEWS_CACHE = CACHE_DIR / "gnews.json"
GROUPS_FILE = CACHE_DIR / "groups.json"  # yanında group_rows.json (alt mənbələrin tam sətri) və group_same.json (saytın təkrar yazıları), compute_groups
RELABEL_MARK = CACHE_DIR / "relabeled"
OUT_FILE = OUT_DIR / "news.json"
MARKETS_FILE = OUT_DIR / "markets.json"
SOCIAL_FILE = OUT_DIR / "social.json"
STATUS_FILE = OUT_DIR / "status.json"
SOURCES_FILE = OUT_DIR / "sources.json"
OG_FILE = OUT_DIR / "og.json"
IMG_CHECK_FILE = CACHE_DIR / "img_check.json"
ARCHIVE_OG_FILE = CACHE_DIR / "archive_og.json"
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
NEWS_SITEMAP_FILE = ROOT / "sitemap-news.xml"
ROBOTS_FILE = ROOT / "robots.txt"
BAKU = datetime.timezone(datetime.timedelta(hours=4))
AZ_MONTHS = {
    "yanvar": 1, "fevral": 2, "mart": 3, "aprel": 4, "may": 5, "iyun": 6,
    "iyul": 7, "avqust": 8, "sentyabr": 9, "oktyabr": 10, "noyabr": 11, "dekabr": 12,
}
MAX_ITEMS = 1600
MAX_PER_SOURCE = 40   # bir mənbə lenti doldurmasın
MAX_PER_WORLD_SOURCE = 10  # xarici mənbələr Azərbaycan xəbərlərini lentdən sıxışdırıb çıxarmasın: çox mənbə, hərəsindən az
MAX_PER_SPORT_SOURCE = 15
# Xarici ümumi mənbələr dil üzrə: ingilis və rus lentləri bir-birini və türk lentini sıxışdırmasın (2026-11-04: sahibin
# istəyi ilə ingilis və rus mənbələri artırıldı). İdmanla birlikdə lentin 40%-dən azdır, qalan yer Azərbaycan xəbərlərinindir.
MAX_WORLD_LANG = {"en": 160, "ru": 130, "tr": 60}
MAX_WORLD = sum(MAX_WORLD_LANG.values())
MAX_WORLD_SPORT = 200      # xarici idman mənbələri

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

_EN_WORDS = frozenset("the why with from for and says after before in of to has is its between by into his this that are was will be over amid".split())

def detect_lang(title, desc, default):
    """Dil təyini: kiril→ru, 'ə'→az (türkdə yoxdur), ı/ğ/İ→tr, əks halda mənbə dili.
    Azərbaycan mənbələrində ə-siz qısa başlıqlar türkcə sayılmasın deyə default "az" üstündür."""
    # A translated summary must not label an English headline as Azerbaijani.
    english = set(re.findall(r"[^\W\d_]+", title.lower())) & {"the", "why", "with", "from", "for", "and", "says", "after", "before", "in", "of", "to"}
    if "ə" not in title.lower() and len(english) >= 2:
        return "en"
    blob = title + " " + desc
    if re.search(r"[а-яА-Я]", blob):
        return "ru"
    if "ə" in blob or "Ə" in blob:
        return "az"
    if default == "az":
        # «Erdoğan», «Türkiye», «Özgür Özel» ingilis xəbərini azərbaycanca etmir (2026-11-11: Azernews xəbəri AZ lentə düşdü):
        # ə-siz mətndə ingilis köməkçi sözləri varsa, ingiliscədir.
        if len(set(re.findall(r"[^\W\d_]+", blob.lower())) & _EN_WORDS) >= 2:
            return "en"
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

MAX_RESPONSE_BYTES = 32 * 1024 * 1024  # bundan böyük cavab oxunmur: dövrə 60 saniyəyə sığmalıdır

class _SafeRedirect(urllib.request.HTTPRedirectHandler):
    """Xəbər keçidi daxili ünvana yönləndirsə sorğu getmir."""
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        if not content_policy.safe_url(newurl):
            raise urllib.error.HTTPError(newurl, 403, "daxili ünvana yönləndirmə", headers, fp)
        return super().redirect_request(req, fp, code, msg, headers, newurl)

urllib.request.install_opener(urllib.request.build_opener(_SafeRedirect))

def _read_capped(r):
    raw = r.read(MAX_RESPONSE_BYTES + 1)
    if len(raw) > MAX_RESPONSE_BYTES:
        raise urllib.error.URLError("cavab çox böyükdür")
    return raw

def _gunzip_capped(raw):
    out = b""
    while raw:  # gzip bir neçə hissədən ola bilər
        box = zlib.decompressobj(16 + zlib.MAX_WBITS)
        out += box.decompress(raw, MAX_RESPONSE_BYTES - len(out) + 1)
        if len(out) > MAX_RESPONSE_BYTES or not box.eof:  # kəsilmiş cavab da xətadır: lent ehtiyat yola keçir
            raise urllib.error.URLError("gzip cavabı kəsilib və ya çox böyükdür")
        raw = box.unused_data.lstrip(b"\0")
    return out

def fetch(url, timeout=TIMEOUT, data=None, headers=None):
    h = {"User-Agent": UA, "Accept": "application/rss+xml, application/xml, text/xml, text/html, */*"}
    if headers:
        h.update(headers)
    req = urllib.request.Request(url, data=data, headers=h)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return _read_capped(r)

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
# «/logo» yalnız saytın öz loqosudur: Modern.az xəbər fotosunu tarixli «/2026/11/10/logo/1794304049_...png» qovluğunda saxlayır
# (loqo damğalı foto), əvvəl belə xəbər həm lentdə, həm səhifədə «loqo» sayılıb şəkilsiz qalırdı (2026-11-10, «Molla rejimi...»).
GENERIC_IMG = re.compile(r"azertag\.az/resources/images/|/logo(?!/\d{6,})|placeholder|default[-_]?(?:image|img|og)|no[-_]?image|tr_son_dakika|/social\.(?:jpe?g|png)$|/site/assets/|/assets/images/|static\.president\.az/assets/president-administration-|lent\.az/storage/news/.*/middle/", re.I)

def _is_generic_img(u):
    return bool(u) and bool(GENERIC_IMG.search(u))

# Xəbər fotosu kimi görünən ünvan (tarixli və ya uzun nömrəli yükləmə yolu) bir neçə xəbərdə təkrarlansa da loqo sayılmır:
# AZƏRTAC bir tədbirin 3-5 xəbərinə eyni fotonu qoyur, TASS idman xəbərlərinə arxiv fotosunu (2026-11-04, sahibin «şəkilsiz
# xəbər» qeydi). Saytın loqo və ümumi lövhə yolları GENERIC_IMG-dədir; onlar üçün 3 təkrar kifayətdir.
_PHOTO_PATH = re.compile(r"/(?:files|uploads?|storage|media|photos?|images?)/.*\d{6,}|/20\d\d/\d{1,2}/", re.I)

def _is_logo(u, n):
    """n fərqli xəbərdə eyni şəkil: 3 və daha çoxdursa loqodur; xəbər fotosu kimi görünən ünvan üçün 8 və daha çox."""
    return bool(u) and n >= (8 if _PHOTO_PATH.search(u) else 3)

# Lentin verdiyi şəkil ünvanı saytda olmayan yoldur, eyni fayl başqa yoldadır. Modern.az RSS-i (2026-11-10 ölçüsü: 30 elementin
# 30-u) «files.modern.az/file/articles/...» verir: hamısı 404, wsrv.nl da 404; səhifənin og:image-i eyni faylı
# «/photo/orginal/...» yolunda verir (200). Ölü şəkli yavaş dövrə 4-5 dəqiqədə tapırdı, tapmayanda (sayt GitHub-a cavab
# verməyəndə) xəbər həmişəlik şəkilsiz qalırdı: canlı lentdə Modern.az-ın 42 sətrindən 17-si ölü şəkilli idi.
_IMAGE_FIXES = ((re.compile(r"^https?://files\.modern\.az/file/articles/", re.I), "https://files.modern.az/photo/orginal/"),)


def fix_image_url(u):
    """Məlum ölü şəkil yolunu işlək yola çevirir (şəbəkə sorğusu yoxdur, sürətli dövrədə də işləyir)."""
    if not isinstance(u, str) or not u:
        return u
    for rx, good in _IMAGE_FIXES:
        u = rx.sub(good, u)
    return u


def _abs_img(u, base):
    if not u:
        return None
    u = html.unescape(u.strip())
    doubled = re.match(r"https?://[^/]*?(https?://.+)$", u)  # «https://azpolitika.infohttps://static...»: ünvan iki dəfə yazılıb
    if doubled:
        u = doubled.group(1)
    if u.startswith("//"):
        u = "https:" + u
    u = urllib.parse.urljoin(base or "", u)
    return fix_image_url(u) if u.startswith(("http://", "https://")) else None

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
        items.append({"title": html.unescape(title).strip(), "link": link, "description": "", "pubDate": pub,
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
    """Reyting.az lenti /haber/x.html yazır, o ünvan 404 verir; xəbərin əsl ünvanı /xeber/x-dir.
    Lent.az lenti .../basliq-123/1 yazır, o ünvan ana səhifəyə atır; xəbərin özü .../basliq-123-dədir."""
    link = re.sub(r"^(https?://(?:www\.)?reyting\.az)/haber/(.+?)\.html$", r"\1/xeber/\2", link or "")
    return re.sub(r"^(https?://(?:www\.)?lent\.az/xeber/.+-\d+)/1/?$", r"\1", link)


_STORY_ID = re.compile(r"(?:/|[-_])(\d{5,})(?=\.(?:html?|cms)\b|/|$)")  # sonrakı ayırıcı udulmur: ardıcıl nömrələrin hamısı tapılır (skysports /12040/13607905/); .cms: Times of India-nın əsl nömrəsi
_DATE_CODES = {}

def _date_codes(today=None):
    """Son 62 günün (Zuğulba arxivi 60 gündür) və sabahın tarix yazılışları: 111126, 11112026, 91126, 261111, 111126 (ay-gün) …
    Slugun sonundakı belə rəqəm xəbərin nömrəsi deyil, günün tarixidir (Al Jazeera «…-pinochet-111126», ntv.az «…-12112026»,
    mia.az «…-91126»): eyni günün iki ayrı xəbəri bir açar alırdı və birinin başlığı o birinin keçidinə yazılırdı (2026-11-12)."""
    today = today or datetime.datetime.now(BAKU).date()
    if today not in _DATE_CODES:
        codes = set()
        for back in range(-1, 63):
            d = today - datetime.timedelta(days=back)
            dd, mm, yy, yyyy = f"{d.day:02d}", f"{d.month:02d}", f"{d.year % 100:02d}", str(d.year)
            codes.update((dd + mm + yy, dd + mm + yyyy, str(d.day) + mm + yy, str(d.day) + mm + yyyy, yy + mm + dd, mm + dd + yy, mm + dd + yyyy))
        _DATE_CODES.clear()
        _DATE_CODES[today] = frozenset(c for c in codes if len(c) >= 5)
    return _DATE_CODES[today]

def story_key(link):
    """Mənbə domeni + xəbərin sabit nömrəsi («metbuat.az#1566209»). Sayt başlığı dəyişəndə keçidin slug hissəsi də dəyişir
    (/news/1566209/kohne-basliq.html → /news/1566209/yeni-basliq.html), nömrə eyni qalır; belə xəbər ikinci dəfə lentə düşməsin
    (2026-11-04, sahibin «pensiya» qeydi). Yalnız öz seqmentində və ya seqmentin sonunda duran 5+ rəqəmli nömrə sayılır
    (yoldakı 20261104 tarixi və slugdakı «100000-manat» məbləği yox); bir neçə nömrədən sonuncusu (skysports: /news/12040/13607905/).
    Nömrəsiz keçid üçün None: belə xəbər əvvəlki kimi keçidlə tanınır."""
    try:
        u = urllib.parse.urlparse(link or "")
    except ValueError:
        return None
    host = (u.hostname or "").lower().removeprefix("www.")
    dates = _date_codes()
    nums = [n for n in _STORY_ID.findall(u.path or "") if not re.fullmatch(r"(?:19|20)\d{6}", n) and n not in dates]
    return f"{host}#{nums[-1]}" if host and nums else None


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

def _pub_dt(pub):
    """Lentin tarix sətri -> datetime; oxunmursa None (RFC 822 və ISO 8601)."""
    if not pub or not isinstance(pub, str):
        return None
    pub = re.sub(r"\s+", " ", pub.strip())
    try:
        dt = email.utils.parsedate_to_datetime(pub)
        if dt is None:
            raise ValueError
    except Exception:
        try:
            dt = datetime.datetime.fromisoformat(pub.replace("Z", "+00:00"))
        except Exception:
            return None
    return dt if dt.tzinfo else dt.replace(tzinfo=BAKU)  # zonasız tarix: Azərbaycan lentləri Bakı vaxtı yazır

def _to_iso(pub):
    return _norm_iso(_pub_dt(pub) or datetime.datetime.now(datetime.timezone.utc))

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
# Ölkə adı defis və şəkilçi ilə də gəlir («ABŞ-nin birinci xanımı», «Fransa'nın birinci xanımı»): \w* defisdə dayanırdı və
# Baku.ws-in «ABŞ-nin birinci xanımı Oleşkidə...» xəbəri Zuğulbaya düşmüşdü (2026-11-04).
_ROLE_FOREIGN = re.compile(r"(?<!\w)(?:" + "|".join(map(re.escape, FOREIGN_MARKERS)) + r")[\w'’-]*\s+(?:prezidentinin\s+)?(?:birinci xan[ıi]m|birinci vitse-prezident)")
# Yiyəlik şəkilçili vəzifə («birinci xanımı», «birinci xanımına») kiminsə xanımıdır: ad və ya Azərbaycan yoxdursa başqa ölkənindir.
_ROLE_POSSESSED = re.compile(r"birinci xan[ıi]m(?:[ıi]|[ıi]n|[ıi]n[ıi]n|[ıi]na|[ıi]n[ıi]|[ıi]nda|[ıi]ndan)(?!\w)")
_AZ_CONTEXT = re.compile(r"əliyev|aliyev|алиев|azərbaycan|azerbaycan|azerbaijan|азербайдж")

def president_score(blob, lang):
    """Rəhbərlik balı: şəxs (ad) > vəzifə > ümumi söz. Vəzifə adı («birinci xanım», «birinci vitse-prezident») yalnız
    Azərbaycanla əlaqə aydın olanda sayılır: yanında və ya mətndə başqa ölkənin adı, yiyəlik şəkilçisi ilə kiminsə xanımı
    və Azərbaycan/ad yoxdursa — başqa ölkənin rəhbəridir. Ad varsa («Birinci xanım Mehriban Əliyeva Türkiyədə») həmişə bizimdir."""
    hits = [w for w in PRESIDENT_STRONG if _rx(w).search(blob)]
    if hits and all(w in PRESIDENT_ROLES for w in hits):
        if lang == "az":
            foreign = bool(_ROLE_FOREIGN.search(blob)) or ((bool(_ROLE_POSSESSED.search(blob)) or has_any(blob, FOREIGN_MARKERS)) and not _AZ_CONTEXT.search(blob))
        else:
            foreign = not _AZ_CONTEXT.search(blob)
        if foreign:
            hits = []
    if hits:
        return 4 + 2 * len(hits)
    if lang != "az" or has_any(blob, FOREIGN_MARKERS):
        return 0
    weak = len(PRESIDENT_WEAK_RX.findall(blob))
    return weak + sum(1 for w in PRESIDENT_WEAK_EXTRA if _rx(w).search(blob)) if weak else 0

SPORT_SITE_RX = re.compile(r"(?<!\w)(?:fənərba[ğx]ça|\w+spor(?!\w)|[\"“«](?:sabah|qarabağ|kəpəz|neftçi|zirə|inter|göztəpə)|legioner|heç-heçə|stadion|avrokubok|"
                           r"komandası|klub|meydan[aı]|uduzdu|oyunu|millinin|heyətim|ehtiyatda qaldı|şans aldı|texniki məğlubiyyət|böyük dəbilqə|federasiya)")

# «Transfer» idman sözüdür, amma «ses transferi», «para transferi», «məlumat transferi», «hava limanı transferi» futbol deyil:
# CNN Türk-ün WhatsApp xəbəri «(IP üzerinden ses transferi)» ifadəsinə görə İdmana düşmüşdü (sahib, 2026-11-14).
_NOT_SPORT_TRANSFER = re.compile(r"(?<!\w)((?:ses|səs|veri|data|bilgi|dosya|fayl|para|pul|məlumat|melumat|bilet|enerji|elektrik|ödəniş|ödeme|"
                                 r"texnologiya|teknoloji|technology|bank|money|wire|file|limanı|havalimanı|otel|hotel|kripto|crypto)\w{0,4}\s+)transfer")

def _sport_free(text):
    return _NOT_SPORT_TRANSFER.sub(r"\1trans-fer", text)

def categorize(title, desc, lang="az", hint=None, world=False):
    title, desc = _sport_free(norm_az(title)), _sport_free(norm_az(desc))
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
            # Başlıqda yalnız ümumi «prezident» sözü var, ölkəni xülasə deyir: «Husilər prezident sarayına...» — «Yəməndə...».
            if 0 < hits < 6 and has_any(blob, FOREIGN_MARKERS) and not _AZ_CONTEXT.search(blob):
                hits = 0
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
    # «Finlandiyada işsizlik», «futbolçunun maaşı»: bölmə Azərbaycanın sosial müdafiəsidir (qurumların öz lentləri ipucu ilə gəlir).
    foreign_topic = (scores["Dünya"] or has_any(blob, FOREIGN_MARKERS) or has_any(blob, SOCIAL_FOREIGN)) and "azərbaycan" not in blob and "азербайджан" not in blob
    # Başlıqda söz yoxdursa xülasədəki bir ötəri ifadə kifayət deyil (BOOST onu güclü edir): ədəbi yubiley, partiya müşavirəsi.
    if world or scores["İdman"] or foreign_topic or (not in_title.get("Sosial müdafiə") and scores["Sosial müdafiə"] < 12):
        scores["Sosial müdafiə"] = 0
    if world:
        scores["Bölgələr"] = 0  # Bölgələr yalnız Azərbaycanın bölgələridir; xarici mənbə ora düşmür
        scores["Prezident"] = 0  # Zuğulba yalnız Azərbaycan mənbələrindəndir
    # «Siyasət?»: saytın mövzusu üstünlük verir, amma məcbur etmir. Azpolitika-nın hava proqnozu Siyasət deyil (2026-10-31).
    soft = hint[:-1] if hint and hint.endswith("?") else None
    if soft:
        hint = None
        # İdman saytının dili: «Rüfət meydana çıxdı», «"Sabah"ın yolu». Bu sözlər başqa saytda idman demək deyil («gecə klubu»), ona görə ümumi siyahıda deyil.
        if soft == "İdman" and scores["Prezident"] < 6 and SPORT_SITE_RX.search(norm_az(title)):
            return soft
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
    # İki oxunuş: «I» ingiliscə «i», azərbaycanca «ı»dır. Birincisi «ILHAM ALIYEV»i, ikincisi «PARTİYASI», «ZORAKILIQ»ı tutur
    # (əvvəl böyük hərflə yazılmış başlıq süzgəcdən keçirdi). Hər hansı oxunuşda uyğunluq kifayətdir: yalnız sərtləşir.
    text = title + " " + desc
    blobs = (norm_az(text), norm_az(text.replace("I", "ı")))
    hit = lambda words: any(_rx(w).search(b) for b in blobs for w in words)
    if hit(OPPOSITION):
        return True
    return hit(LEADERSHIP) and hit(NEGATIVE)

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

_CTRL = re.compile("[\x00-\x08\x0b\x0c\x0e-\x1f\x7f\ufffe\uffff]")  # XML 1.0-da yasaq işarələr: biri feed.xml və sitemap-ı «zədəli» edir, guard_outputs onları 48 saatadək köhnə saxlayırdı

def _plain(s, title=False):
    """HTML entity və etiketləri təmizlə. Başlığın sonundakı boş tire mənbədən gəlir."""
    cur = s or ""
    for _ in range(3):
        nxt = html.unescape(cur)
        if nxt == cur:
            break
        cur = nxt
    cur = re.sub(r"<[^>]+>", " ", cur).replace("\xa0", " ")
    cur = re.sub(r"\s+", " ", _CTRL.sub("", cur)).strip()
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

# Lentin bölmə süzgəci işləməyən mənbə (2026-11-07: TASS «sections=sport» bütün xəbərləri verir, İdmanda «Kiyevdə partlayışlar» çıxdı):
# yalnız bu ünvanlı xəbər lentin bölməsinə düşür, qalanının bölməsini məzmun müəyyən edir (xəbər itmir).
HINT_URL = {"TASS Sport": "tass.ru/sport/"}

def make_article(it, source, default_lang, hint=None, force_label=None):
    if hint and source in HINT_URL and HINT_URL[source] not in str(it.get("link") or ""):
        hint = None
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
            photo = re.search(r"tgme_widget_message_photo_wrap[^>]*?background-image:url\('([^']+)'", part)
            out.append({
                "title": title, "link": link, "description": "",
                "pubDate": when.group(1) if when else "", "author": "", "image": photo.group(1) if photo else None,
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
FAST_MAX_ITEMS = 1400    # qruplaşdırma açdığı yer köhnə xəbərlə dolmasın, news.json böyüməsin (2026-11-04: 1000 → 1400, xarici dillərə yer)
FALLBACK_EVERY_S = 180   # Google News və Telegram ehtiyatını dəqiqədə bir yormayaq
STALE_FEED_S = 900       # bundan köhnə nəticə «mənbə işləmir» sayılır
LATEST_WINDOW_S = 1800   # latest.json main-dəki news.json-un gecikməsini örtməlidir
LATEST_TOP = 40
LATEST_MAX = 300         # ümumi fayl («Hamısı», ehtiyat, bildirişlər); 2026-11-04: xarici lentlər çoxalanda yarım saatın xəbəri 200-ə sığmırdı
LATEST_LANG_MAX = 200    # latest.<dil>.json: oxucu hər dəqiqə yalnız öz dilinin lentini çəkir (qırmızı xətt 3); azərbaycanca xəbər xarici axınla sıxılmır (qırmızı xətt 1)
FEED_LANGS = ("az", "en", "ru", "tr")
NEWS_LANGS = ("en", "ru", "tr")  # tam lentin dil faylları news.<dil>.json (main-də, write_news); news.json azərbaycanca + xarici idman


def _read_json(path, default):
    try:
        return json.loads(pathlib.Path(path).read_text(encoding="utf-8"))
    except Exception:
        return default


def read_feed(path=None):
    """Tam lent bir siyahıda: news.json və onun «langs» siyahısındakı dil faylları (news.en.json və s., write_news), eyni keçid bir dəfə.
    Bölünməmiş (köhnə) news.json-da «langs» yoxdur: yalnız o oxunur. Lenti oxuyan hər yer (əvvəlki dövrə, arxiv, paylaşma, sitemap/feed,
    qruplar, link yoxlaması) bunu işlədir ki, bölgü onlara görünməsin."""
    path = pathlib.Path(path or OUT_FILE)
    def rows_of(p):
        d = _read_json(p, {})
        return list(d.get("articles") or []) if isinstance(d, dict) else []
    data = _read_json(path, {})
    rows = rows_of(path)
    seen = {a.get("sourceUrl") for a in rows}
    for code in (data.get("langs") if isinstance(data, dict) else None) or []:
        for a in rows_of(path.with_name(f"news.{code}.json")):
            if a.get("sourceUrl") not in seen:
                seen.add(a.get("sourceUrl"))
                rows.append(a)
    return rows


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
            raw = _read_capped(r)
            if (r.headers.get("Content-Encoding") or "").lower() == "gzip":
                raw = _gunzip_capped(raw)
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
# Naxçıvan Xəbərlərinin lenti yoxdur, ana səhifəsi 244 KB-dır.
# Ağır xarici lentlər (170 KB-dan böyük): dəqiqəlik dövrəyə yük olmasın, yavaş dövrə oxuyur (2026-11-04).
SLOW_ONLY_FEEDS = {f[0] for f in AZ_FEEDS if ".gov.az/" in f[1]} | {"Mia.az", "Narnews.az", "Cenub.az", "Region Plus", "Qarabağ Media", "Naxçıvan Xəbərləri"} \
    | {"РБК", "Tengrinews", "Спорт-Экспресс", "Daryo", "NASA", "iXBT", "Naked Science"}

LATE_FEEDS = set()  # bu dövrədə cavab verməyən, köhnə nəticəsi işlədilən lentlər: statusda uğurlu sayılmır

def collect_fast():
    """(results, official items, official errors). Heç bir lent dövrəni FAST_BUDGET_S-dən çox saxlamır."""
    cache = _read_json(FEED_CACHE, {})
    for name, entry in _read_json(SLOW_FEED_CACHE, {}).items():
        if entry.get("at", 0) > (cache.get(name) or {}).get("at", 0):
            cache[name] = entry
    _GNEWS_DECODED.update(_read_json(GNEWS_CACHE, {}))
    # Rəsmi səhifələr (president.az, birinci xanım) öz işçisində və birinci başlayır (sahib, 2026-11-10: «niyə prezident.az-dan
    # əvvəldən çəkmirik?»). Əvvəl 204 lentin növbəsinin sonunda idi: dövrə 20 s-ə çatanda çox vaxt bitmirdi, köhnə nüsxə
    # götürülürdü — Türkiyə səfəri president.az-da 15:10, saytda 15:29; başqa saytların nüsxəsi ondan əvvəl paylaşıldı.
    off_pool = ThreadPoolExecutor(max_workers=1)
    official = off_pool.submit(official_items)
    pool = ThreadPoolExecutor(max_workers=FAST_WORKERS)
    futures = [(feed, pool.submit(fetch_feed_fast, feed, cache.get(feed[0]))) for feed in FEEDS]
    wait([future for _, future in futures] + [official], timeout=FAST_BUDGET_S)
    pool.shutdown(wait=False, cancel_futures=True)
    off_pool.shutdown(wait=False, cancel_futures=True)
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


_GROUP_ROW_FIELDS = ("source", "sourceUrl", "publishedAt", "title", "summary", "category", "lang", "imageUrl")


def compute_groups():
    """Eyni hadisənin qruplaşdırılması ağırdır (bütün cütlər): yavaş prosesdə hesablanır, sürətli dövrə nəticəni tətbiq edir.

    Kartın alt mənbələri də adi sətir kimi yenidən qruplaşdırılır. Əvvəl onlar yalnız «yadda saxlanmış» siyahı idi və yalnız
    kartın əsas başlığı ilə yoxlanırdı: əsas sətir dəyişəndə («Venger qərar verməyə hazırlaşır») eyni başlıqlı 3 alt mənbə
    («Arsen Venger FIFA prezidenti ola bilər») yoxlamadan keçmir, lentdən itir, sürətli dövrə onları RSS-dən yeni xəbər kimi
    qaytarırdı: ayrı kartlar 4 dəqiqə sonra yenə birləşir, sonra yenə ayrılırdı (2026-11-10 canlı lent: 54 artıq kart,
    hər hesablamada ~90 keçid itirdi). İndi nəticə yalnız xəbərlər çoxluğundan asılıdır, əvvəlki qruplaşmadan yox."""
    articles = read_feed()
    if not articles:
        return
    known = _read_json(GROUPS_FILE.with_name("group_rows.json"), {})
    known = known if isinstance(known, dict) else {}
    present = {a.get("sourceUrl") for a in articles if a.get("sourceUrl")}
    rows, seen, origin = [], set(), {}
    for a in articles:
        if a.get("sourceUrl") and a["sourceUrl"] not in seen:
            seen.add(a["sourceUrl"])
            rows.append({k: v for k, v in a.items() if k != "alts"})
    for a in articles:
        for alt in a.get("alts") or []:
            url = alt.get("sourceUrl")
            if not url or url in seen or not alt.get("title"):
                continue  # başlıqsız köhnə alternativ yoxlana bilməz
            seen.add(url)
            origin[url] = a.get("sourceUrl")
            full = known.get(url)
            if isinstance(full, dict) and full.get("title"):
                rows.append(dict(full, sourceUrl=url))  # əvvəl əsas sətir olanda yadda saxlanmış xülasə ilə
            else:
                rows.append({**alt, "category": a.get("category"), "summary": ""})
    # Gizlədilmiş təkrarlar (eyni saytın eyni başlıqlı ikinci yazısı) lentdə yoxdur: yenə hesablansın ki, kart dəyişəndə qayıtsın.
    floor = (datetime.datetime.now(datetime.timezone.utc) - 2 * GROUP_WINDOW).isoformat()
    for url in _read_json(GROUPS_FILE.with_name("group_same.json"), {}) or {}:
        full = known.get(url)
        if url not in seen and isinstance(full, dict) and full.get("title") and (full.get("publishedAt") or "") >= floor:
            seen.add(url)
            rows.append(dict(full, sourceUrl=url))
    by_url = {r["sourceUrl"]: r for r in rows}
    groups, same, moved = {}, {}, {}
    for g in group_duplicates([dict(r) for r in rows], same_out=same):
        alts = g.get("alts") or []
        if not alts:
            continue
        if g["sourceUrl"] not in present:
            # Sürətli dövrə qrupu lentdəki sətrə bağlayır: əsas sətir indi alt mənbədirsə, lentdəki üzv əsas olur.
            pick = next((x for x in alts if x.get("sourceUrl") in present), None)
            if pick is None:
                continue  # üzvlərin heç biri lentdə əsas deyil: növbəti dövrə onları ayrıca qaytarır, sonra yenə qruplanır
            alts = sorted([_compact_alt(g), *(x for x in alts if x is not pick)], key=lambda x: x.get("publishedAt") or "", reverse=True)
            moved[g["sourceUrl"]] = pick["sourceUrl"]
            g = pick
        groups[g["sourceUrl"]] = alts
    # Yenidən hesablama qərar verə bilmədiyi alt mənbə (məs. xülasəsi yoxdur, lentdə əsas üzvü yoxdur) itməsin: əvvəlki kartında qalır.
    key_of = {u: k for k, alts in groups.items() for u in [k, *(x.get("sourceUrl") for x in alts)]}
    for url, card in origin.items():
        if url in key_of or url in same or card not in present:
            continue
        key = key_of.get(card, card)
        alts = groups.setdefault(key, [])
        row = by_url.get(url) or {}
        if _event_conflict(row, by_url.get(key, {})):
            continue  # qərarsız alternativ qalır; açıq fərqli hadisə əvvəlki kartına qaytarılmır
        taken = {by_url.get(key, {}).get("source"), *(x.get("source") for x in alts)}
        alt = _compact_alt(row)
        if alt and row.get("source") not in taken:
            alts.append(alt)
            alts.sort(key=lambda x: x.get("publishedAt") or "", reverse=True)
            key_of[url] = key
    _save_cache(GROUPS_FILE, groups)
    _save_cache(GROUPS_FILE.with_name("group_same.json"), {u: moved.get(p, p) for u, p in same.items()})
    _save_cache(GROUPS_FILE.with_name("group_rows.json"), {u: {k: r[k] for k in _GROUP_ROW_FIELDS if r.get(k)} for u, r in by_url.items()})


def apply_groups(articles):
    """Yavaş prosesin qruplarını lentə tətbiq edir. Ondan sonra gələn təzə xəbərləri attach_fresh qoşur."""
    # Qrup faylı dəyişiklikdən əvvəl yazılıb ola bilər: köhnə keçid buradan lentə qayıtmasın.
    groups = {fix_source_link(url): [{**alt, "sourceUrl": fix_source_link(alt.get("sourceUrl"))} for alt in alts] for url, alts in _read_json(GROUPS_FILE, {}).items()}
    present = {a.get("sourceUrl"): a for a in articles}
    groups = {url: [alt for alt in alts if not _event_conflict(present.get(url, {}), alt)] for url, alts in groups.items()}
    absorbed = {alt.get("sourceUrl") for url, alts in groups.items() if url in present for alt in alts}
    # Saytın eyni xəbəri təkrar dərci: kart lentdədirsə təkrar ayrıca göstərilmir.
    same = _read_json(GROUPS_FILE.with_name("group_same.json"), {}) if groups else {}
    absorbed |= {url for url, head in (same if isinstance(same, dict) else {}).items()
                 if head in present and head != url and not _event_conflict(present.get(url, {}), present[head])}
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
        elif a.get("alts"):
            a = {**a, "alts": [alt for alt in a["alts"] if not _event_conflict(a, alt)]}
        out.append(a)
    try:
        return attach_fresh(out)
    except Exception as e:  # qırmızı xətt 1: birləşmə alınmasa lent olduğu kimi yazılır
        print(f"təzə xəbər qruplanmadı: {e!r}")
        return out


FRESH_GROUP = datetime.timedelta(minutes=30)

def attach_fresh(articles, now=None):
    """Yavaş proses qrupları ~4-9 dəqiqədən bir hesablayır; ondan sonra gələn xəbər (son 30 dəqiqə) eyni hadisənin
    kartına alternativ kimi qoşulur. Əvvəl bunu brauzer edirdi və telefonda ~1 s çəkirdi.
    Qayda group_duplicates kimidir: eyni başlıq və ya oxşar başlıq, fərqli mənbə, 36 saat içində; rəsmi mənbə toxunulmur.
    Namizəd ortaq sözlə tapılır (söz indeksi), hamı hamı ilə müqayisə olunmur."""
    now = now or datetime.datetime.now(datetime.timezone.utc)
    items = []
    for a in articles:
        toks = _title_tokens(a.get("title") or "")
        items.append((a, _parse_dt(a.get("publishedAt")), toks, set(toks)))
    index = collections.defaultdict(list)
    for i, (_a, _dt, _toks, ts) in enumerate(items):
        for t in ts:
            index[t].append(i)
    order = sorted(range(len(items)), key=lambda i: items[i][1] or datetime.datetime.min.replace(tzinfo=datetime.timezone.utc), reverse=True)
    merged, target = set(), {}
    for i in order:
        a, dt, toks, ts = items[i]
        if (i in merged or i in target or dt is None or now - dt > FRESH_GROUP or len(toks) < 3
                or a.get("alts") or a.get("source") in OFFICIAL_SOURCES):
            continue
        key = _norm_title(a.get("title") or "")
        hits = collections.Counter(j for t in ts for j in index[t] if j != i and j not in merged)
        best, best_score = None, 0
        for j, n in hits.items():
            if n < 3:
                continue
            b, bdt, btoks, _bts = items[j]
            b = target.get(j, b)
            srcs = {b.get("source")} | {x.get("source") for x in b.get("alts") or []}
            if bdt is None or abs(dt - bdt) > GROUP_WINDOW or b.get("source") in OFFICIAL_SOURCES or a.get("source") in srcs or _event_conflict(a, b):
                continue
            score = 4 if len(key) >= 12 and key == _norm_title(b.get("title") or "") else 3 if _titles_similar(toks, _shingles(toks), btoks, _shingles(btoks)) else 0
            if score > best_score or score and score == best_score and len(b.get("alts") or []) > len(target.get(best, items[best][0]).get("alts") or []):
                best, best_score = j, score
        if best is None:
            continue
        b = target.get(best, items[best][0])
        alt = _compact_alt(a)
        if not alt:
            continue
        alts = sorted([*(b.get("alts") or []), alt], key=lambda x: x.get("publishedAt") or "", reverse=True)
        target[best] = {**b, "alts": alts, "imageUrl": b.get("imageUrl") or a.get("imageUrl") or ""} if not b.get("imageUrl") and a.get("imageUrl") else {**b, "alts": alts}
        merged.add(i)
    return [target.get(i, a) for i, (a, _dt, _toks, _ts) in enumerate(items) if i not in merged]


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
    checked = _read_json(IMG_CHECK_FILE, {})
    for a in articles:
        # Əvvəlki dövrələrdən qalan sətirlər də (lentdən çıxmış Modern.az xəbərləri) düzəlsin
        if a.get("imageUrl"):
            a["imageUrl"] = fix_image_url(a["imageUrl"])
        for alt in a.get("alts") or []:
            if alt.get("imageUrl"):
                alt["imageUrl"] = fix_image_url(alt["imageUrl"])
                if checked.get(alt["imageUrl"]):
                    alt.pop("imageUrl")
        if checked.get(a.get("imageUrl")):
            a["imageUrl"] = None
        image = cache.get(a.get("sourceUrl") or "") if isinstance(cache, dict) else None
        if not a.get("imageUrl") and isinstance(image, str) and image and not _is_generic_img(image):
            a["imageUrl"] = image


# Ölü linklər: sayt xəbəri lentdə dərc edir, səhifəsi isə bir müddət 404 verir (2026-11-01, Nocomment.az və Modern.az, 15 dəqiqəyə yaxın)
# və ya xəbəri sonradan silir. Yoxlama ayrı prosesdir (--links): xəbər dövrəsi şəbəkə gözləmir, yalnız bu faylın nəticəsini oxuyur.
LINK_TIMEOUT_S, LINK_BUDGET_S, LINK_THREADS, LINK_PER_HOST = 6, 40, 12, 2
LINK_DEAD_RECHECK_S = 60          # ölü link tez-tez yoxlanır: düzələn kimi xəbər qayıdır
LINK_DEAD_KEEP_S = 24 * 3600
LINK_FRESH_S, LINK_FRESH_EVERY_S, LINK_OLD_EVERY_S = 6 * 3600, 20 * 60, 3 * 3600
LINK_ALIVE_PER_RUN = 40
LINK_HOST_OUTAGE = (4, 0.6)       # bir saytda 4+ yoxlamanın 60%-i ölüdürsə sayt özü nasazdır, xəbərləri gizlədilmir
LINK_DEAD_MAX = 30                # bundan çoxu ölü görünürsə yoxlamaya güvənilmir (lent boşalmasın)


def link_status(url):
    """«dead» yalnız sayt özü dedikdə: 404, 410 və ya ana səhifəyə atma. Blok (403), xəta və vaxt keçməsi xəbəri gizlətmir."""
    try:
        target = urllib.parse.quote(url, safe=":/?&=%#+,;@!$'()*~-._")
        req = urllib.request.Request(target, headers={"User-Agent": UA, "Accept": "text/html,application/xhtml+xml"})
        with urllib.request.urlopen(req, timeout=LINK_TIMEOUT_S) as r:
            landed = urllib.parse.urlsplit(r.geturl()).path.strip("/")
        return "dead" if not landed and urllib.parse.urlsplit(url).path.strip("/") else "alive"
    except urllib.error.HTTPError as e:
        return "dead" if e.code in (404, 410) else "unknown"
    except Exception:
        return "unknown"


def check_links(now=None):
    """Bir yoxlama: əvvəl ölü linklər, sonra yeni xəbərlər (ən yenisi birinci), qalan vaxtda köhnələr növbə ilə."""
    now = now or time.time()
    state = _read_json(LINK_HEALTH_FILE, {})
    listed = {}
    for a in read_feed():
        if a.get("source") == OWN_SOURCE:
            continue  # öz səhifəmiz main yazılışı ilə (10 dəqiqəyədək) yayımlanır: o vaxtadək 404 «ölü link» sayılıb öz sətri gizlətməsin
        for row in [a, *(a.get("alts") or [])]:
            if row.get("sourceUrl"):
                listed[row["sourceUrl"]] = row.get("publishedAt") or a.get("publishedAt") or ""
    state = {u: v for u, v in state.items() if u in listed or (v.get("dead") and now - v.get("since", now) < LINK_DEAD_KEEP_S)}
    def age(url):
        dt = _parse_dt(listed.get(url))
        return now - dt.timestamp() if dt else LINK_DEAD_KEEP_S
    dead = [u for u, v in state.items() if v.get("dead") and now - v.get("at", 0) >= LINK_DEAD_RECHECK_S]
    fresh = sorted((u for u in listed if u not in state), key=age)
    due = [u for u, v in state.items() if u in listed and not v.get("dead") and now - v.get("at", 0) >= (LINK_FRESH_EVERY_S if age(u) < LINK_FRESH_S else LINK_OLD_EVERY_S)]
    queue = dead + fresh + sorted(due, key=lambda u: state[u].get("at", 0))[:LINK_ALIVE_PER_RUN]
    hosts = collections.defaultdict(lambda: threading.Semaphore(LINK_PER_HOST))
    host_of = lambda u: urllib.parse.urlsplit(u).hostname or ""
    def one(url):
        with hosts[host_of(url)]:
            return url, link_status(url)
    pool = ThreadPoolExecutor(LINK_THREADS)
    jobs = [pool.submit(one, u) for u in queue]
    finished, _late = wait(jobs, timeout=LINK_BUDGET_S)
    pool.shutdown(wait=False, cancel_futures=True)
    results = [j.result() for j in finished if not j.cancelled() and not j.exception()]
    tally = collections.defaultdict(lambda: [0, 0])
    for url, status in results:
        tally[host_of(url)][0] += 1
        tally[host_of(url)][1] += status == "dead"
    outage = {h for h, (n, d) in tally.items() if n >= LINK_HOST_OUTAGE[0] and d / n >= LINK_HOST_OUTAGE[1]}
    changed = []
    for url, status in results:
        old = state.get(url) or {}
        if status == "dead" and host_of(url) in outage:
            status = "unknown"
        if status == "unknown":
            state[url] = {**old, "at": now}
            continue
        if (status == "dead") != bool(old.get("dead")):
            changed.append(("ölü " if status == "dead" else "düzəldi ") + url)
        state[url] = {"at": now, "dead": True, "since": old.get("since", now)} if status == "dead" else {"at": now}
    _save_cache(LINK_HEALTH_FILE, state)
    print(f"Link yoxlaması: {len(results)}/{len(queue)}, ölü {sum(1 for v in state.values() if v.get('dead'))}", flush=True)
    for line in changed[:20]:
        print(" ", line, flush=True)


def dead_links(total):
    """Hazırda ölü bilinən linklər. Çox görünürsə (yoxlayan tərəf nasazdır) heç nə gizlədilmir: xəbər lenti boşalmamalıdır."""
    urls = {u for u, v in _read_json(LINK_HEALTH_FILE, {}).items() if v.get("dead")}
    if len(urls) > max(LINK_DEAD_MAX, total // 20):
        print(f"  ! ölü link çoxdur ({len(urls)}), gizlədilmir", flush=True)
        return set()
    return urls


def drop_dead_links(articles, dead):
    """Ölü linkli xəbər çıxır. Eyni xəbəri başqa sayt da yazıbsa kart ona keçir."""
    out = []
    for a in articles:
        alts = [alt for alt in a.get("alts") or [] if alt.get("sourceUrl") not in dead]
        if a.get("sourceUrl") not in dead:
            out.append({**a, "alts": alts} if len(alts) != len(a.get("alts") or []) else a)
        elif alts:
            alt, *rest = alts
            out.append({**a, "id": hashlib.sha1(alt["sourceUrl"].encode()).hexdigest()[:16], "source": alt.get("source") or a.get("source"), "sourceUrl": alt["sourceUrl"],
                        "publishedAt": alt.get("publishedAt") or a.get("publishedAt"), "title": alt.get("title") or a.get("title"), "lang": alt.get("lang") or a.get("lang"),
                        "imageUrl": a.get("imageUrl") or alt.get("imageUrl"), "alts": rest})
    return out


def _latest_rows(articles, recent, cap):
    """Ən yeni LATEST_TOP xəbər və son yarım saatda lentə düşənlər, tarix sırası ilə, ən çoxu cap."""
    ordered = sorted(articles, key=lambda a: a.get("publishedAt") or "", reverse=True)
    top = {a.get("sourceUrl") for a in ordered[:LATEST_TOP]}
    return [a for a in ordered if a.get("sourceUrl") in top or a.get("sourceUrl") in recent][:cap]


def write_latest(articles, previous):
    """latest.json: son yarım saatda lentə düşənlər və ən yeni xəbərlər. Sayt onu tam lentin üstünə qoyur.
    latest.<dil>.json: eyni seçim yalnız o dilin xəbərlərindən. QIRMIZI XƏTT 3: oxucu hər dəqiqə yalnız öz dilinin faylını
    çəkir (2026-11-04: ümumi fayl 300 sətirdə 71 KB gzip idi, 2/3-ü xarici dildə). Dil faylları yalnız tarixçəsiz live
    budağına gedir (pipeline.sh push_live; publish_main onları main-ə yazmır), ümumi fayl ehtiyat və «Hamısı» üçün qalır."""
    now, known = time.time(), {a.get("sourceUrl") for a in previous}
    recent = {u: t for u, t in _read_json(RECENT_FILE, {}).items() if now - t < LATEST_WINDOW_S}
    for a in articles:
        if a.get("sourceUrl") not in known:
            recent.setdefault(a.get("sourceUrl"), now)
    rows = _latest_rows(articles, recent, LATEST_MAX)
    stamp = datetime.datetime.now(datetime.timezone.utc).isoformat()
    OUT_DIR.mkdir(exist_ok=True)
    # «dead»: sayt tam lenti 10 dəqiqədən bir alır, ölü link isə ekrandan bir dəqiqəyə çıxmalıdır.
    dead = sorted(dead_links(len(articles)))
    removed = content_policy.REMOVED_ARTICLES
    _write_atomic(LATEST_FILE, json.dumps({"updatedAt": stamp, "count": len(rows), "articles": rows, "dead": dead, "removed": removed}, ensure_ascii=False, separators=(",", ":")))
    try:  # QIRMIZI XƏTT 1: dil faylı alınmasa ümumi fayl və lent yenə yazılır
        for code in FEED_LANGS:
            sub = _latest_rows([a for a in articles if (a.get("lang") or "az") == code], recent, LATEST_LANG_MAX)
            _write_atomic(OUT_DIR / f"latest.{code}.json", json.dumps({"updatedAt": stamp, "count": len(sub), "articles": sub, "dead": dead, "removed": removed}, ensure_ascii=False, separators=(",", ":")))
    except Exception as e:
        print("  ! latest.<dil>.json:", type(e).__name__, flush=True)
    _save_cache(RECENT_FILE, recent)


def write_news(data):
    """news.json. NEWS_LANG_FILES ilə (yeni pipeline.sh; QIRMIZI XƏTT 3): news.json = azərbaycanca sətirlər + xarici idman (sahibin qaydası:
    idman bölməsi bütün dillərdədir), news.<dil>.json = yalnız o dilin sətirləri (rus/ingilis/türk oxucuya azərbaycanca və türkcə xəbər düşmür);
    «langs» hansı dil fayllarının olduğunu deyir (read_feed onları birləşdirir). Hamısı main-ə gedir: bölgü tarixçəyə əlavə yük vermir
    (docs/qirmizi-xetler.md §3). Bayraqsız (köhnə pipeline) əvvəlki kimi bir fayl."""
    # "sharePages": sayt /x/ID paylaşma keçidini yalnız bu işarə ilə verir (write_share_pages; eyni yayımda səhifələr də main-dədir)
    dump = lambda d: json.dumps({**d, **({"sharePages": True} if os.environ.get("SHARE_PAGES") else {})}, ensure_ascii=False, separators=(",", ":"))
    if not os.environ.get("NEWS_LANG_FILES"):
        _write_atomic(OUT_FILE, dump(data), encoding="utf-8")
        return
    articles = data["articles"]
    for code in NEWS_LANGS:  # əvvəl dil faylları, sonra onlara işarə edən news.json
        rows = [a for a in articles if a.get("lang") == code]
        _write_atomic(OUT_FILE.with_name(f"news.{code}.json"), dump({"updatedAt": data["updatedAt"], "count": len(rows), "articles": rows}), encoding="utf-8")
    own = [a for a in articles if (a.get("lang") or "az") not in NEWS_LANGS or a.get("category") == "idman"]
    _write_atomic(OUT_FILE, dump({"updatedAt": data["updatedAt"], "count": len(own), "langs": list(NEWS_LANGS), "articles": own}), encoding="utf-8")


# Sayt baş səhifənin yuxarısını bu xəbərlərdən qurur, tam lent sonra gəlir. Eyni blok alınmalıdır ki, tam lent gələndə ekran dəyişməsin:
# seçim assets/app.js-dəki heroPick, latestBlock, prezHome və collapseExact ilə uyğun qalmalıdır.
FIRST_RANKED, FIRST_NEWEST, FIRST_HERO = 40, 30, 15  # slayder 15 xəbər götürür, oxşarları atır; «Son xəbərlər» 8 kart göstərir
_FIRST_APPOINTMENT = re.compile(r"təyin (?:edil|olun)|vəzifə(?:sin|y)[əd]|(?:vəzifə(?:sin)?|iş)d[əa]n azad|назначен|освобожд[её]н от должности|appointed|dismissed", re.I)


def first_screen_rows(articles, now=None):
    """Azərbaycanca baxışın ilk ekranı üçün sətirlər: ən çox mənbədə çıxan və ən yeni xəbərlər, bütün Zuğulba xronikası."""
    now = now or datetime.datetime.now(datetime.timezone.utc)
    key = lambda a: _norm_title(html.unescape(a.get("title") or ""))
    groups, twins = {}, collections.defaultdict(list)
    for a in articles:
        if a.get("category") != "prezident":
            twins[key(a)].append(a)  # başqa dil kimi işarələnmiş eyni başlıq da: sayt onları birləşdirir
            if (a.get("lang") or "az") == "az":
                groups.setdefault(key(a), twins[key(a)])
    newest = {k: max((a.get("publishedAt") or "") for a in rows) for k, rows in groups.items()}
    weight = {k: sum(1 + len(a.get("alts") or []) for a in rows) + (2 if _FIRST_APPOINTMENT.search(rows[0].get("title") or "") else 0) for k, rows in groups.items()}
    pool = list(groups)
    for hours in (18, 48):
        cut, recent = now - datetime.timedelta(hours=hours), []
        for k in groups:
            dt = _parse_dt(newest[k])
            if dt and cut <= dt <= now + datetime.timedelta(minutes=5):
                recent.append(k)
        if len(recent) >= FIRST_HERO:
            pool = recent
            break
    keep = set(sorted(pool, key=lambda k: (weight[k], newest[k]), reverse=True)[:FIRST_RANKED])
    keep.update(sorted(groups, key=lambda k: newest[k], reverse=True)[:FIRST_NEWEST])
    return [a for a in articles if a.get("category") == "prezident" or key(a) in keep]


def write_first(articles, stamp):
    """first.json: ilk ekranın sətirləri və onların og şəkilləri. Bütöv og.json ekran çəkiləndən sonra gəlir."""
    rows, og = first_screen_rows(articles), _read_json(OG_FILE, {})
    # Xəritəyə yalnız şəkil qazandıran giriş düşür (sürət, 2026-11-09): apply_og_cache şəkli sətrin özünə yazıb — eyni ünvan və boş dəyər
    # 139 girişdən 120-si idi, 27 KB (6 KB gzip) ölü yük. Format dəyişmir (ünvan → şəkil); app.js imageCandidates eyni namizədləri alır.
    have = {}
    for a in rows:
        have[a.get("sourceUrl")] = a.get("imageUrl")
        for alt in a.get("alts") or []:
            have[alt.get("sourceUrl")] = alt.get("imageUrl")
    images = {u: og[u] for u in have if u and og.get(u) and og[u] != have.get(u)}
    _write_atomic(FIRST_FILE, json.dumps({"updatedAt": stamp, "count": len(rows), "articles": rows, "og": images, **({"sharePages": True} if os.environ.get("SHARE_PAGES") else {})}, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")


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
ARCHIVE_FIELDS = ("id", "title", "summary", "source", "sourceUrl", "publishedAt", "category", "lang", "imageUrl", "video", "alts")

def _feed_cache():
    """Lentlərin son cavabı (sürətli və yavaş dövrənin keşi, hansı təzədirsə)."""
    cache = _read_json(FEED_CACHE, {})
    for name, entry in _read_json(SLOW_FEED_CACHE, {}).items():
        if entry.get("at", 0) > (cache.get(name) or {}).get("at", 0):
            cache[name] = entry
    return cache

def bulk_dated_sources():
    """Hazırda tarixi etibarsız lentlər (bulk_dated). Lentdən onsuz da çıxırlar; 2026-11-07: Marja.az-ın əvvəl arxivə düşmüş
    38 şəkilsiz, eyni vaxtlı xəbəri (köhnə reklamlar da) İqtisadiyyat səhifəsinin yarısını tuturdu — arxivdən də çıxırlar."""
    cache = _feed_cache()
    return {source for source, *_ in FEEDS if bulk_dated((cache.get(source) or {}).get("items") or [])}

def feed_backlog(cutoff):
    """Lent 3-4 saat əhatə edir: rayon və qurum xəbəri çox vaxt ondan köhnədir, lentdən keçmədiyi üçün arxivə də düşmürdü.
    Azərbaycan lentlərinin Bölgələr və Sosial müdafiə xəbərləri arxivə birbaşa gəlir, süzgəclər lentdəki ilə eynidir."""
    cache = _feed_cache()
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

def fill_archive_images(rows, images, limit=40):
    """Lentdən keçməyən xəbərin (feed_backlog) og:image sorğusu olmayıb: burada, bir saata 40 səhifə. Tapılan arxivdə qalır."""
    for url in [u for u, img in images.items() if _is_generic_img(img)]:
        del images[url]
    todo = [a["sourceUrl"] for a in rows if not a.get("imageUrl") and a["sourceUrl"] not in images][:limit]
    if todo:
        with ThreadPoolExecutor(max_workers=8) as ex:
            found = list(ex.map(_fetch_og, todo))
        repeats = collections.Counter(img for img in found if img)
        images.update((url, "" if repeats[img] >= 3 else img) for url, img in zip(todo, found) if img is not None)
    for a in rows:
        if not a.get("imageUrl") and images.get(a["sourceUrl"]):
            a["imageUrl"] = images[a["sourceUrl"]]
    return rows

# Paylaşılan keçid (#/xeber/<id>) xəbər lentdən çıxandan sonra ən azı 24 saat açılsın. Bölmə arxivi 200 xəbərlə kəsilir
# (Gündəm gündüz cəmi 3 saat), lenti isə böyütmək olmaz (sürət). Ayrıca siyahı: id-nin ilk iki hex rəqəminə görə 256 fayl, keçid yalnız
# birini yükləyir. 2026-11-09-a qədər 32 fayl idi (id >> 3): hər biri ~160 KB / 54 KB gzip, lazım olan bir sətir ~300 bayt; indi ~20 KB /
# 8 KB gzip (telefonda ~50 ms). Faylın "parts" sahəsi bölgünü deyir: sayt köhnə bölgülü faylı görəndə sətri köhnə hissədə də axtarır
# (app.js shareRow, keçid dövrü üçün).
SHARE_DIR = OUT_DIR / "paylas"
SHARE_KEEP_S, SHARE_PARTS = 25 * 3600, 256   # yazı saatda birdir: 25 saat lentdən çıxandan sonra tam 24 saat deməkdir
SHARE_FIELDS = ("title", "source", "sourceUrl", "publishedAt", "category", "lang", "imageUrl")

def removed_ids():
    """Sahibin çıxardığı xəbərlərin id-ləri: qeyddəki id-lər və qeyddəki hər ünvanın id-si (id = sha1(ünvan)[:16]). Qeyddə iki ünvan,
    bir id ola bilir: yalnız id-yə baxan təmizlik ikinci ünvanın səhifəsini 30 gün saytda və sitemap-da saxlayırdı."""
    return content_policy._REMOVED_IDS | {hashlib.sha1(u.encode()).hexdigest()[:16] for u in content_policy._REMOVED_URLS}

def share_part(sid):
    return int(sid[:2], 16) if re.fullmatch(r"[0-9a-f]{16}", str(sid or "")) else None

def update_share_index(articles, now):
    parts = [{} for _ in range(SHARE_PARTS)]
    # Mövcud fayllar bölgüdən asılı olmayaraq oxunur, sətir öz hissəsinə düşür: 32 → 256 keçidində köhnə fayldakı (lentdən çıxmış) xəbər
    # itmir; eyni id iki faylda olsa təzə yazılan qalır.
    for path in (SHARE_DIR.glob("*.json") if SHARE_DIR.is_dir() else []):
        for row in _read_json(path, {}).get("articles") or []:
            i = share_part(row.get("id"))
            if i is not None and now - row.get("at", 0) < SHARE_KEEP_S and row.get("at", 0) >= parts[i].get(row["id"], {}).get("at", 0):
                parts[i][row["id"]] = row
    rows = [a for a in articles if share_part(a.get("id")) is not None]
    # Qrupa düşən mənbənin öz nömrəsi lentdə yoxdur: onun sətri qrupun əsas xəbərinə yönəlir (of).
    for a in rows:
        for x in a.get("alts") or []:
            if x.get("sourceUrl"):
                sid = hashlib.sha1(x["sourceUrl"].encode()).hexdigest()[:16]
                parts[share_part(sid)][sid] = {"id": sid, "of": a["id"], "source": x.get("source"), "sourceUrl": x["sourceUrl"], "at": int(now)}
    for a in rows:
        row = {"id": a["id"], **{k: a[k] for k in SHARE_FIELDS if a.get(k)}, "at": int(now)}
        alts = [{k: x[k] for k in ("source", "sourceUrl") if x.get(k)} for x in a.get("alts") or [] if x.get("sourceUrl")]
        parts[share_part(a["id"])][a["id"]] = {**row, "alts": alts} if alts else row
    SHARE_DIR.mkdir(parents=True, exist_ok=True)
    keep = {a["id"] for a in rows}  # paylaşma səhifələri (write_share_pages): lentdəki və siyahıdakı xəbərlərinki qalır
    for i, part in enumerate(parts):
        rows = [r for r in part.values() if not removed_source(r) and not is_negative_about_leadership(r.get("title", ""), "", r.get("source"))]
        rows, _ = content_policy.enforce(rows)
        keep.update(r["id"] for r in rows if not r.get("of"))
        _write_atomic(SHARE_DIR / f"{i}.json", json.dumps({"at": now, "parts": SHARE_PARTS, "articles": rows}, ensure_ascii=False, separators=(",", ":")))
    prune_share_pages(keep)

# Paylaşma səhifələri (sahibin qeydi 2026-11-04: «Facebookda paylaşanda hansı xəbəri paylaşdığın görünmür»). Facebook, WhatsApp,
# Telegram önizləməni keçidin og: etiketlərindən oxuyur; #/xeber/ID hash-dır, serverə getmir, hamı saytın ümumi kartını görürdü.
# İndi lentdəki hər xəbərin kiçik statik səhifəsi var: x/<id>.html (~1 KB: başlıq, xülasə, şəkil, og:url), oxucunu dərhal saytın
# xəbər səhifəsinə keçirir (skriptdəki location.replace tarixçədə iz qoymur, geri düyməsi işləyir). Səhifə paylaşma siyahısı qədər (25 saat) qalır,
# sonra silinir; köhnə keçidi 404.html #/xeber/ID-yə yönəldir (arxivdən açılır). Yalnız SHARE_PAGES=1 ilə: pipeline.sh qovluğu main-ə
# yazır və sayt /x/ keçidini yalnız lentin başlığında "sharePages" görəndə verir (köhnə pipeline-da səhifəsiz keçid yaranmasın).
# Sürətli dövrədə yalnız yeni fayllar yazılır (dəqiqədə ~10), silinmə saatlıq update_share_index-dədir. QIRMIZI XƏTT 3-ə toxunmur:
# tətbiqin öz yolu dəyişmir, paylaşılan keçidə ~1 KB-lıq bir sorğu əlavə olunur. QIRMIZI XƏTT 2: sətirlər content_policy.enforce-dan keçir.
SHARE_PAGES_DIR = ROOT / "x"
_LOCALE = {"az": "az_AZ", "ru": "ru_RU", "en": "en_US", "tr": "tr_TR"}
_SHARE_HTML = ('<!doctype html>\n<html lang="{lang}"><head><meta charset="UTF-8" /><meta name="viewport" content="width=device-width, initial-scale=1.0" />\n'
               '<title>{title} — 8ulduz</title><meta name="robots" content="noindex" /><link rel="canonical" href="{url}" />\n'
               '<meta property="og:type" content="article" /><meta property="og:site_name" content="8ulduz" /><meta property="og:title" content="{title}" />\n'
               '<meta property="og:description" content="{desc}" /><meta property="og:url" content="{url}" /><meta property="og:image" content="{image}" />\n'
               '<meta property="og:locale" content="{locale}" /><meta name="twitter:card" content="summary_large_image" />\n'
               '{pre}'
               '</head><body><p><a href="{app}">{title}</a> — <a href="{site}">8ulduz</a></p></body></html>\n')

def share_page(a):
    """Bir xəbərin paylaşma səhifəsi: og etiketləri və dərhal saytın xəbər səhifəsinə keçid."""
    sid, title = a["id"], _xml(re.sub(r"\s+", " ", str(a.get("title") or "")).strip())
    desc = re.sub(r"<[^>]+>|\s+", " ", str(a.get("summary") or "")).strip()
    if len(desc) > 200:
        desc = desc[:197].rsplit(" ", 1)[0] + "…"
    desc = _xml(desc or f'{a.get("source") or "8ulduz"} · {str(a.get("publishedAt") or "")[:10]}')
    image, fallback = str(a.get("imageUrl") or ""), f"{SITE}assets/og-default.png"
    # Önizləmə şəkli proksidən 1200×630 JPEG (~100 KB): WhatsApp 600 KB-dan böyüyü göstərmir; mənbədə silinmiş şəkil yerinə saytın şəkli.
    image = _xml(f"https://wsrv.nl/?url={urllib.parse.quote(image, safe='')}&w=1200&h=630&fit=cover&a=attention&output=jpg&q=78&default={urllib.parse.quote(fallback, safe='')}"
                 if image.startswith("https://") else fallback)
    hm = re.match(r"20(\d\d)-(\d\d)-(\d\d)T(\d\d)", str(a.get("publishedAt") or ""))  # h: arxiv budağının saatı (.github/scripts/arxiv.cjs)
    raw_app = f'{SITE}#/xeber/{sid}?b={a.get("category") or ""}' + (f'&h={"".join(hm.groups())}' if hm else '')
    return _SHARE_HTML.format(lang=_xml(a.get("lang") or "az"), title=title, desc=desc, url=f"{SITE}x/{sid}", image=image,
                              locale=_LOCALE.get(a.get("lang") or "az", "az_AZ"), app=_xml(raw_app), site=SITE, pre=share_jump(a, raw_app))

# Facebook/WhatsApp-dan gələn oxucu (sahib, 2026-11-07: «keçidlər gözqırpımında»): səhifə xəbərin sətrini sessionStorage-a qoyur
# və dərhal sayta keçir; sayt xəbəri heç bir yükləməni (150 KB-lıq paylaşma siyahısı, tam lent) gözləmədən göstərir (app.js açılış).
# Botlar (Facebook, WhatsApp önizləməsi) skripti işlətmir, og etiketlərini oxuyur. Səhifədə meta refresh YOXDUR və canonical səhifənin özüdür:
# Facebook robotu refresh-i izləyib 8ulduz.az/#/… → baş səhifənin kartını («8ulduz — Son xəbərlər») götürürdü (2026-11-08, Worker-in canlı jurnalı).
# Skriptsiz brauzer səhifədəki keçidə basır.
SHARE_ROW_FIELDS = ("id", "title", "summary", "source", "sourceUrl", "imageUrl", "category", "publishedAt", "lang", "video", "author")

def _js(v):
    return json.dumps(v, ensure_ascii=False).replace("</", "<\\/").replace("<!--", "<\\!--")

def share_jump(a, app):
    row = {k: (str(a[k])[:600] if k == "summary" else a[k]) for k in SHARE_ROW_FIELDS if a.get(k)}
    alts = [{k: x[k] for k in ("id", "title", "source", "sourceUrl") if x.get(k)} for x in (a.get("alts") or [])[:20] if x.get("sourceUrl")]
    if alts:
        row["alts"] = alts
    body = json.dumps(row, ensure_ascii=False, separators=(",", ":"))
    return f'<script>try{{sessionStorage.setItem({_js("x:" + a["id"])},{_js(body)})}}catch(e){{}}location.replace({_js(app)})</script>\n'

def write_share_pages(articles):
    """Lentdəki hər xəbər üçün (16 rəqəmli id) hələ olmayan paylaşma səhifəsini yazır; sayını qaytarır. Bayraqsız heç nə etmir."""
    if not os.environ.get("SHARE_PAGES"):
        return 0
    SHARE_PAGES_DIR.mkdir(parents=True, exist_ok=True)
    for ident in removed_ids():
        if re.fullmatch(r"[0-9a-f]{16}", ident):
            (SHARE_PAGES_DIR / f"{ident}.html").unlink(missing_ok=True)
    have = {p.name for p in SHARE_PAGES_DIR.glob("*.html")}
    rows = [a for a in articles if share_part(a.get("id")) is not None and not removed_source(a)
            and not is_negative_about_leadership(a.get("title", ""), a.get("summary", ""), a.get("source"))]
    rows, _ = content_policy.enforce(rows)
    n = 0
    for a in rows:
        if f'{a["id"]}.html' not in have:
            _write_atomic(SHARE_PAGES_DIR / f'{a["id"]}.html', share_page(a), encoding="utf-8")
            n += 1
    return n

def prune_share_pages(keep):
    """Paylaşma siyahısında da, lentdə də olmayan xəbərin səhifəsi silinir (siyahı ilə eyni müddət: 25 saat); sayını qaytarır."""
    if not os.environ.get("SHARE_PAGES") or not SHARE_PAGES_DIR.is_dir():
        return 0
    gone = [p for p in SHARE_PAGES_DIR.glob("*.html") if p.stem not in keep]
    for p in gone:
        try:
            p.unlink()
        except OSError:
            pass
    return len(gone)

# Google üçün xəbər səhifələri (sahib, 2026-11-06: Search Console-da 28 gündə 33 göstəriş, yeganə sorğu «8 ulduz»). /x/ID noindex-dir
# və dərhal #/xeber/ID-yə keçir, hash-ı isə Google ayrıca səhifə saymır: sayt Google üçün 17 səhifə idi. İndi yalnız əsas Azərbaycan
# xəbərlərinin (4+ mənbə və ya Zuğulba) xeber/<id>/ səhifəsi var: başlıq, xülasə və xəbəri yazan bütün mənbələr (aqreqatorun öz
# dəyəri), bölmə keçidi. Bölmə səhifələri kimi tətbiq də yüklənir və ünvan #/xeber/ID olur. Səhifə 30 gün qalır; siyahı bir faylda
# (xeber/index.json), dövrədə yalnız yeni və mənbə sayı dəyişən xəbər yazılır. Şəbəkə sorğusu yoxdur. QIRMIZI XƏTT 2: enforce-dan keçir.
STORY_DIR = ROOT / "xeber"
STORY_KEEP_S = 30 * 86400
STORY_MIN_SOURCES = 3  # sahib 2026-11-07: «sayta gələni artır» — 4-dən 3-ə (gündə ~+300 səhifə, ~7 KB)
STORY_SITEMAP_MAX = 5000
# Şablon dəyişəndə köhnə səhifələr yenidən yazılsın (index-in 4-cü sahəsi); bir dövrədə ən çox STORY_REWRITE, repo birdən böyüməsin.
# 2: Google Discover üçün max-image-preview:large (sahib 2026-11-07).
# 3: og:image mənbələrin ən enli şəkli (Discover 1200+ px istəyir; 2026-11-07 ölçüsü: əsas şəkillərin 13/40-ı 1200+ idi).
# 4: xəbərin sətri səhifənin özündədir (#row): paylaşılan/köhnə keçid lentdən çıxsa da açılır (sahib 2026-11-07, paylaşma yoxlaması).
# 5: səhifə kiçildilmiş app.min.js yükləyir — şablon 2026-11-08-də dəyişmiş, versiya artmamışdı: ~3 400 köhnə səhifə Google-dan gələnə 221 KB-lıq app.js verirdi (sürət, 2026-11-09).
# 6: eyni bölmədən əlaqəli keçidlər (Google, 2026-11-10).
STORY_VER, STORY_REWRITE = 6, 150
IMG_SIZE_FILE = CACHE_DIR / "img_size.json"
IMG_SIZE_KEEP, DISCOVER_MIN_W = 4000, 1200

def _image_size(b):
    """Şəklin eni faylın başından (PNG, GIF, WebP, JPEG); tanınmasa 0."""
    try:
        if b[:8] == b"\x89PNG\r\n\x1a\n":
            return int.from_bytes(b[16:20], "big")
        if b[:4] == b"GIF8":
            return int.from_bytes(b[6:8], "little")
        if b[:4] == b"RIFF" and b[8:12] == b"WEBP":
            kind = b[12:16]
            if kind == b"VP8X":
                return 1 + int.from_bytes(b[24:27], "little")
            if kind == b"VP8 ":
                return int.from_bytes(b[26:28], "little") & 0x3FFF
            if kind == b"VP8L":
                return (int.from_bytes(b[21:25], "little") & 0x3FFF) + 1
        if b[:2] == b"\xff\xd8":
            i = 2
            while i + 9 < len(b):
                if b[i] != 0xFF:
                    i += 1
                    continue
                m = b[i + 1]
                if 0xC0 <= m <= 0xCF and m not in (0xC4, 0xC8, 0xCC):
                    return int.from_bytes(b[i + 7:i + 9], "big")
                i += 2 + int.from_bytes(b[i + 2:i + 4], "big")
    except Exception:
        pass
    return 0

def _image_width(url):
    """Yalnız faylın ilk 64 KB-ı soruşulur (Range): eni oradadır."""
    try:
        req = urllib.request.Request(url, headers={"User-Agent": UA, "Range": "bytes=0-65535"})
        with urllib.request.urlopen(req, timeout=5) as r:
            return _image_size(r.read(65536))
    except Exception:
        return 0

def story_image_widths(articles, limit=80):
    """Xəbər səhifəsi olacaq xəbərlərin (əsas və mənbələrin) şəkillərinin eni; hər ünvan bir dəfə, yavaş dövrədə (write_public)."""
    sizes = _read_json(IMG_SIZE_FILE, {})
    if not isinstance(sizes, dict):
        sizes = {}
    todo = []
    for a in articles:
        if not story_worthy(a):
            continue
        for r in [a, *(a.get("alts") or [])]:
            u = str(r.get("imageUrl") or "")
            if u.startswith("https://") and u not in sizes and u not in todo and not _is_generic_img(u):
                todo.append(u)
    todo = todo[:limit]
    if todo:
        with ThreadPoolExecutor(max_workers=8) as ex:
            sizes.update(zip(todo, ex.map(_image_width, todo)))
        _save_cache(IMG_SIZE_FILE, dict(list(sizes.items())[-IMG_SIZE_KEEP:]))
    return sizes

def discover_image(a, sizes):
    """og:image: əsas şəkil 1200 px-dən dardırsa eyni xəbərin digər mənbələrindən ən enlisi; ölçü bilinmirsə əsas şəkil."""
    main = str(a.get("imageUrl") or "")
    best, width = (main, sizes.get(main) or 0) if main.startswith("https://") else ("", 0)
    if width >= DISCOVER_MIN_W:
        return best
    for r in a.get("alts") or []:
        u = str(r.get("imageUrl") or "")
        if u.startswith("https://") and (sizes.get(u) or 0) > width and not _is_generic_img(u):
            best, width = u, sizes[u]
    return best
_AZ_MONTH_NAMES = ("yanvar", "fevral", "mart", "aprel", "may", "iyun", "iyul", "avqust", "sentyabr", "oktyabr", "noyabr", "dekabr")

def story_worthy(a):
    """Google üçün ayrıca səhifəyə layiq xəbər: Azərbaycan dilində, paylaşma nömrəsi var, 3+ mənbə və ya Zuğulba."""
    return bool(re.fullmatch(r"[0-9a-f]{16}", str(a.get("id") or "")) and (a.get("lang") or "az") == "az"
                and str(a.get("title") or "").strip()
                and (a.get("category") == "prezident" or 1 + len(a.get("alts") or []) >= STORY_MIN_SOURCES))

def _baku_time(iso):
    dt = _parse_dt(iso)
    if not dt:
        return ""
    dt = dt.astimezone(ZoneInfo("Asia/Baku"))
    return f"{dt.day} {_AZ_MONTH_NAMES[dt.month - 1]} {dt.year}, {dt:%H:%M}"

_STORY_HTML = """<!doctype html>
<html lang="az">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0, viewport-fit=cover" />
    <meta http-equiv="Content-Security-Policy" content="__CSP__" />
    <script>if(top!==self)document.documentElement.style.display="none";try{var t=localStorage.getItem("8ulduz-theme");document.documentElement.dataset.theme=t==="light"?"light":"dark";var f=localStorage.getItem("8ulduz-fs");document.documentElement.dataset.fs=/^[0-4]$/.test(f||"")?f:"2";}catch(e){}</script>
    <title>__TITLE__ — 8ulduz</title>
    <script type="application/json" id="row">__ROW__</script>
    <meta name="description" content="__DESC__" />
    <link rel="canonical" href="__URL__" />
    <meta name="robots" content="max-image-preview:large" />
    <meta name="theme-color" content="#15233b" />
    <meta property="og:type" content="article" />
    <meta property="og:site_name" content="8ulduz" />
    <meta property="og:title" content="__TITLE__" />
    <meta property="og:description" content="__DESC__" />
    <meta property="og:url" content="__URL__" />
    <meta property="og:locale" content="az_AZ" />
    <meta property="og:image" content="__IMAGE__" />
    <meta property="article:published_time" content="__ISO__" />
    <meta name="twitter:card" content="summary_large_image" />
    <script type="application/ld+json">__LD__</script>
    <link rel="alternate" type="application/rss+xml" title="8ulduz" href="__SITE__feed.xml" />
    <link rel="manifest" href="__SITE__manifest.webmanifest" />
    <link rel="icon" href="__SITE__assets/icon-192.png" sizes="192x192" />
    <link rel="modulepreload" href="../../assets/app.min.js" />
    <link rel="stylesheet" href="../../assets/app.css" />
    <script src="../../assets/config.js" defer></script>
    <script src="../../assets/content-policy.js" defer></script>
    <script type="module" src="../../assets/app.min.js"></script>
    <script>history.replaceState(null, "", new URL("../../#/xeber/__ID__?b=__SLUG__", location.href));</script>
  </head>
  <body>
    <div id="app">
      <main class="wrap"><p><a href="../../">8ulduz</a> › <a href="../../bolme/__SLUG__/">__LABEL__</a></p><h1>__TITLE__</h1>
      <p><time datetime="__ISO__">__WHEN__</time> · __COUNT__ mənbə</p><p>__SUMMARY__</p>
      <h2>Bu xəbəri yazan mənbələr</h2><ul>__SOURCES__</ul>
      __RELATED__
      <p><a href="../../bolme/__SLUG__/">__LABEL__ bölməsinin digər xəbərləri</a> · <a href="../../">8ulduz — baş səhifə</a> · <a href="../../icmal/">Günün icmalı</a></p><noscript>Tam sayt üçün JavaScript-i aktiv edin.</noscript></main>
    </div>
  </body>
</html>
"""

def _related_block(a, pool, now=None):
    """Eyni bölmənin ən çoxu 8 xəbər səhifəsi. Yalnız səhifəsi qalan xəbərlər."""
    now = now or time.time()
    cat = a.get("category") or "gundem"
    def live(b):
        dt = _parse_dt(b.get("publishedAt"))
        return bool(dt and 0 <= now - dt.timestamp() <= STORY_KEEP_S)
    rows = [b for b in pool or [] if b.get("id") != a.get("id") and (b.get("category") or "gundem") == cat and story_worthy(b) and live(b)]
    rows.sort(key=lambda b: b.get("publishedAt") or "", reverse=True)
    rows = rows[:8]
    if not rows:
        return ""
    lis = "".join(f'<li><a href="../../xeber/{b["id"]}/">{_xml(b.get("title"))}</a></li>' for b in rows)
    return f'<h2>Əlaqəli xəbərlər</h2><ul>{lis}</ul>'

_ROW_RX = re.compile(r'<script type="application/json" id="row">(.*?)</script>', re.S)
_PAGE_LI_RX = re.compile(r'<li><a href="([^"]+)"[^>]*>(.*?)</a>\s*<small>(.*?)</small></li>', re.S)

def story_row_from_page(sid, entry, page):
    """Yazılmış xeber/<id>/ səhifəsindən xəbərin sətri və og:image (köhnə şablonu yenisi ilə yazmaq üçün; şəbəkə sorğusu yoxdur).
    4-cü versiyadan sətir səhifənin özündədir (#row); 1–3-cü versiyalarda başlıq, xülasə, vaxt və mənbə siyahısı mətndən oxunur.
    Oxuna bilməsə (None, "")."""
    text = lambda s: html.unescape(re.sub(r"<[^>]+>", "", s or "")).strip()
    image = html.unescape((re.search(r'<meta property="og:image" content="([^"]*)"', page) or ["", ""])[1])
    if image.endswith("assets/og-default.png"):
        image = ""
    m = _ROW_RX.search(page)
    if m:
        try:
            a = json.loads(m.group(1))
        except ValueError:
            return None, ""
        return (a, image) if isinstance(a, dict) and a.get("id") == sid and a.get("title") else (None, "")
    title = text((re.search(r"<h1>(.*?)</h1>", page, re.S) or ["", ""])[1])
    iso = (re.search(r'<time datetime="([^"]+)"', page) or ["", ""])[1]
    body = page.split("<h2>Bu xəbəri yazan mənbələr</h2>", 1)
    lis = [(html.unescape(u), text(t), text(s)) for u, t, s in _PAGE_LI_RX.findall(body[1].split("</ul>", 1)[0])] if len(body) == 2 else []
    if not title or not _parse_dt(iso) or not lis:
        return None, ""
    summary = text((re.search(r"mənbə</p><p>(.*?)</p>", body[0], re.S) or ["", ""])[1])
    a = {"id": sid, "title": title, "summary": summary, "source": lis[0][2], "sourceUrl": lis[0][0], "imageUrl": image,
         "category": entry[2] if len(entry) > 2 else "gundem", "publishedAt": iso, "lang": "az",
         "alts": [{"title": t, "source": s, "sourceUrl": u} for u, t, s in lis[1:]]}
    return {k: v for k, v in a.items() if v or k == "alts"}, image

def story_page(a, sizes=None, related=(), image=None):
    """Bir əsas xəbərin axtarış üçün səhifəsi (xeber/<id>/index.html). image: köhnə səhifə yenidən yazılanda onun öz og:image-i."""
    sid, slug = a["id"], a.get("category") or "gundem"
    label = {s: l for s, l, _d in SECTIONS}.get(slug, "Xəbərlər")
    title = re.sub(r"\s+", " ", str(a.get("title") or "")).strip()
    summary = re.sub(r"<[^>]+>|\s+", " ", str(a.get("summary") or "")).strip()
    desc = summary if len(summary) <= 160 else summary[:157].rsplit(" ", 1)[0] + "…"
    rows = [a, *(a.get("alts") or [])]
    seen, lis = set(), []
    for r in rows:
        url = fix_source_link(r.get("sourceUrl"))
        if not url or url in seen or not str(url).startswith(("https://", "http://")):
            continue
        seen.add(url)
        lis.append(f'<li><a href="{_xml(url)}" rel="noopener">{_xml(r.get("title") or title)}</a> <small>{_xml(r.get("source"))}</small></li>')
    image = image or discover_image(a, sizes or {}) or f"{SITE}assets/og-default.png"
    url = f"{SITE}xeber/{sid}/"
    ld = json.dumps({"@context": "https://schema.org", "@type": "BreadcrumbList", "itemListElement": [
        {"@type": "ListItem", "position": 1, "name": "8ulduz", "item": SITE},
        {"@type": "ListItem", "position": 2, "name": label, "item": f"{SITE}bolme/{slug}/"},
        {"@type": "ListItem", "position": 3, "name": title, "item": url}]}, ensure_ascii=False).replace("</", "<\\/")
    iso = str(a.get("publishedAt") or "")
    keep = ("id", "title", "summary", "source", "sourceUrl", "imageUrl", "category", "publishedAt", "lang", "video")
    row = {k: a[k] for k in keep if a.get(k)}
    row["alts"] = [{k: r[k] for k in ("id", "title", "source", "sourceUrl") if r.get(k)} for r in (a.get("alts") or [])][:20]
    row = json.dumps(row, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/").replace("<!--", "<\\u0021--")
    page = (_STORY_HTML.replace("__ROW__", row).replace("__LD__", ld).replace("__SOURCES__", "".join(lis))
            .replace("__SUMMARY__", _xml(summary))  # tam xülasə qalır (sahib, 2026-11-11: bir cümləlik sitat qəbul edilmədi)
            .replace("__DESC__", _xml(desc or title)).replace("__TITLE__", _xml(title)).replace("__LABEL__", _xml(label))
            .replace("__IMAGE__", _xml(image)).replace("__WHEN__", _xml(_baku_time(iso))).replace("__ISO__", _xml(iso))
            .replace("__COUNT__", str(len(lis))).replace("__URL__", url).replace("__SITE__", SITE)
            .replace("__ID__", sid).replace("__SLUG__", slug).replace("__RELATED__", _related_block(a, related)))
    return _with_csp(page)

def read_story_index():
    return _read_json(STORY_DIR / "index.json", {})

def write_story_pages(articles, now=None):
    """Əsas xəbərlərin səhifələrini yazır (yalnız yeni və mənbə sayı dəyişən), 30 gündən köhnəni və silinəni götürür.
    Siyahını {id: [vaxt, mənbə sayı, bölmə]} qaytarır."""
    now = now or time.time()
    index = {k: v for k, v in read_story_index().items() if isinstance(v, list) and len(v) >= 2}
    gone = removed_ids()
    # Öz xəbərin (mənbə «8ULDUZ») xeber/<id>/ səhifəsini dərc dövrəsi yazıb: ümumi şablon onun üstünə yazmır, siyahıya da salmır.
    rows = [a for a in articles if story_worthy(a) and a.get("source") != OWN_SOURCE and not removed_source(a)
            and not is_negative_about_leadership(a.get("title", ""), a.get("summary", ""), a.get("source"))]
    rows, _ = content_policy.enforce(rows)
    try:  # şəkil ölçüsü alınmasa səhifələr əsas şəkillə yazılır
        sizes = story_image_widths(rows)
    except Exception as e:
        print("  ! şəkil ölçüsü:", type(e).__name__, e)
        sizes = {}
    changed, redo = False, STORY_REWRITE
    for a in rows:
        dt = _parse_dt(a.get("publishedAt"))
        if not dt or now - dt.timestamp() > STORY_KEEP_S:
            continue
        n = 1 + len(a.get("alts") or [])
        old = index.get(a["id"])
        if old and old[1] == n and (STORY_DIR / a["id"] / "index.html").exists():
            if (old[3] if len(old) > 3 else 1) >= STORY_VER or redo <= 0:
                continue
            redo -= 1  # köhnə şablon: yenidən yazılır
        d = STORY_DIR / a["id"]
        d.mkdir(parents=True, exist_ok=True)
        _write_atomic(d / "index.html", story_page(a, sizes, rows), encoding="utf-8")
        index[a["id"]] = [int(dt.timestamp()), n, a.get("category") or "gundem", STORY_VER]
        changed = True
    # Lentdən çıxmış xəbərin səhifəsi (2026-11-12): yuxarıdakı dövrə yalnız lentdəki xəbəri görür, ona görə 32 saatdan köhnə
    # ~5 600 səhifə köhnə şablonda qalmışdı (əlaqəli keçidlər yox, 1–4-cü versiyalarda kiçildilməmiş app.js). Belə səhifə öz
    # içindəki məlumatdan yenidən yazılır: dövrədə qalan STORY_REWRITE payı qədər, hər dövrə siyahının başqa yerindən
    # (oxunmayan və ya qaydadan keçməyən səhifə növbəni tutmasın). Vaxt, mənbə sayı və og:image dəyişmir.
    stale = sorted((sid for sid, old in index.items() if (old[3] if len(old) > 3 else 1) < STORY_VER
                    and now - old[0] <= STORY_KEEP_S and sid not in gone), key=lambda sid: (-index[sid][0], sid))
    if redo > 0 and stale:
        at = int(now // 600) * STORY_REWRITE % len(stale)
        for sid in (stale[at:] + stale[:at])[:STORY_REWRITE * 2]:
            if redo <= 0:
                break
            try:
                a, image = story_row_from_page(sid, index[sid], (STORY_DIR / sid / "index.html").read_text(encoding="utf-8"))
            except OSError:
                continue
            if (not a or a.get("source") == OWN_SOURCE or removed_source(a) or not content_policy.enforce([a])[0]
                    or is_negative_about_leadership(a.get("title", ""), a.get("summary", ""), a.get("source"))):
                continue
            _write_atomic(STORY_DIR / sid / "index.html", story_page(a, None, rows, image), encoding="utf-8")
            index[sid] = [index[sid][0], index[sid][1], index[sid][2] if len(index[sid]) > 2 else a.get("category") or "gundem", STORY_VER]
            redo -= 1
            changed = True
    for sid in list(index):
        if now - index[sid][0] > STORY_KEEP_S or sid in gone:
            for p in (STORY_DIR / sid / "index.html", STORY_DIR / sid):
                try:
                    p.unlink() if p.is_file() else p.rmdir()
                except OSError:
                    pass
            del index[sid]
            changed = True
    if changed:
        STORY_DIR.mkdir(parents=True, exist_ok=True)
        _write_atomic(STORY_DIR / "index.json", json.dumps(index, separators=(",", ":")))
    return index

# Günün icmalı (sahib, 2026-11-06: «daimi oxucu» planının 1-ci addımı). Bakı vaxtı 09:00 və 19:00-da ən çox mənbənin yazdığı
# 10 Azərbaycan xəbəri bir səhifəyə yığılır: icmal/<tarix>-seher/ və icmal/<tarix>-axsam/ (axşam səhərkini təkrarlamır). Buraxılış
# bir dəfə yazılır və dəyişmir; siyahı icmal/index.json-dadır (sosial iş axını oradan Telegram/Facebook-a göndərir). Səhifə JS-siz,
# tətbiqi yükləmir (~6 KB). Şəbəkə sorğusu yoxdur. QIRMIZI XƏTT 2: xəbərlər enforce və rəhbərlik süzgəcindən keçir.
DIGEST_DIR = ROOT / "icmal"
DIGEST_SIZE = 10
DIGEST_KEEP_DAYS = 90
DIGEST_EDITIONS = (("seher", 9, "Səhər icmalı", 24), ("axsam", 19, "Axşam icmalı", 12))  # (açar, saat, ad, neçə saatlıq xəbər)
DIGEST_LATE_H = 6  # pipeline dayanıbsa buraxılış ən gec bu qədər sonra yazılır, sonra buraxılır

def _title_key(t):
    return re.sub(r"[^\w]+", "", unicodedata.normalize("NFKC", str(t or "")).casefold())

# Sahib (2026-11-06): «1 hadisədən yalnız 1 xəbər». İlk axşam icmalında 10 xəbərdən 7-si Prezidentin bir səfəri idi.
# Eyni hadisə: başlıq + xülasənin əvvəli üzrə nadir sözlər (5 hərflik kök, aralıqdakı xəbərlərə görə ağırlıq) oxşarlığı
# DIGEST_SAME_EVENT-dən böyükdür (6 noyabr: səfər xəbərləri 0.32-0.90, ayrı hadisələr 0.16-0.24). Rəhbərin sözlərindən sitat
# («Prezident: "..."») xülasədə yeri yazılmır: icmalda rəhbərin bir hadisəsi varsa, sitat həmin hadisənin parçası sayılır.
DIGEST_SAME_EVENT = 0.3
_EVENT_STOP = set("ilə üçün olan olub edib edilib ediblər haqqında barədə daha artıq bütün onun onların həm isə kimi sonra əvvəl "
                  "yeni ildə günü foto video yenilənib yeniləndi şərh açıqlama xəbər verir".split())
_LEADER_RE = re.compile(r"prezident|ilham əliyev|dövlət başçısı")
_LEADER_QUOTE_RE = re.compile(r"^\s*(?:prezident|dövlət başçısı|ilham əliyev)[^:]{0,25}:")


def _az_lower(s):
    return str(s or "").replace("İ", "i").replace("I", "ı").lower()


def _event_tokens(a):
    text = _az_lower(f"{a.get('title') or ''} {(a.get('summary') or '')[:220]}")
    return {w[:5] for w in re.findall(r"[^\W\d_]{4,}", text) if w not in _EVENT_STOP}


def _leader_quote(a):
    t = _az_lower(a.get("title"))
    return bool(_LEADER_QUOTE_RE.match(t) or (re.match(r"\s*[\"“«„]", t) and _LEADER_RE.search(_az_lower((a.get("summary") or "")[:300]))))


def digest_pick(articles, start, end, skip=()):
    """[start, end) aralığında ən çox mənbənin yazdığı Azərbaycan xəbərləri (bərabərdə daha yeni); eyni başlıq və eyni hadisə bir dəfə."""
    rows = []
    for a in articles:
        dt = _parse_dt(a.get("publishedAt"))
        if (not dt or not (start <= dt.timestamp() < end) or (a.get("lang") or "az") != "az" or not str(a.get("title") or "").strip()
                or a.get("id") in skip or removed_source(a)
                or is_negative_about_leadership(a.get("title", ""), a.get("summary", ""), a.get("source"))):
            continue
        rows.append(a)
    rows, _ = content_policy.enforce(rows)
    rows.sort(key=lambda a: (1 + len(a.get("alts") or []), a.get("publishedAt") or ""), reverse=True)
    toks = [_event_tokens(a) for a in rows]
    df = collections.Counter(w for t in toks for w in t)
    idf = {w: math.log((len(rows) + 1) / (n + 1)) for w, n in df.items()}
    norm = [math.sqrt(sum(idf[w] ** 2 for w in t)) for t in toks]
    def same_event(i, j):
        if not norm[i] or not norm[j]:
            return False
        return sum(idf[w] ** 2 for w in toks[i] & toks[j]) / (norm[i] * norm[j]) >= DIGEST_SAME_EVENT
    out, picked, seen, leader = [], [], set(), False
    for i, a in enumerate(rows):
        k = _title_key(a.get("title"))
        if k in seen or (leader and _leader_quote(a)) or any(same_event(i, j) for j in picked):
            continue
        seen.add(k)
        picked.append(i)
        out.append(a)
        leader = leader or bool(_LEADER_RE.search(_az_lower(f"{a.get('title') or ''} {(a.get('summary') or '')[:220]}")))
        if len(out) == DIGEST_SIZE:
            break
    return out

_DIGEST_HTML = """<!doctype html>
<html lang="az">
<head>
<meta charset="UTF-8" />
<meta name="viewport" content="width=device-width, initial-scale=1.0" />
<title>__TITLE__ — 8ulduz</title>
<meta name="description" content="__DESC__" />
<link rel="canonical" href="__URL__" />
<meta name="theme-color" content="#0a1120" />
<meta property="og:type" content="article" /><meta property="og:site_name" content="8ulduz" /><meta property="og:title" content="__TITLE__" />
<meta property="og:description" content="__DESC__" /><meta property="og:url" content="__URL__" /><meta property="og:image" content="__IMAGE__" />
<meta property="og:locale" content="az_AZ" /><meta name="twitter:card" content="summary_large_image" />
<link rel="icon" href="__SITE__assets/icon-192.png" sizes="192x192" />
<link rel="alternate" type="application/rss+xml" title="8ulduz" href="__SITE__feed.xml" />
<script type="application/ld+json">__LD__</script>
<style>body{margin:0;font:17px/1.5 system-ui,-apple-system,"Segoe UI",Roboto,sans-serif;background:#0a1120;color:#e8edf5}main{max-width:720px;margin:0 auto;padding:16px}a{color:#7cc4ff}h1{font-size:1.5em;margin:.4em 0 .2em}ol{padding-left:1.4em}li{margin:0 0 1.1em}li>a{font-weight:600;font-size:1.05em;text-decoration:none}small{display:block;color:#9fb0c6}li p{margin:.3em 0 0}.cta{background:#13203a;border-radius:12px;padding:12px 14px;margin:1.4em 0}@media(prefers-color-scheme:light){body{background:#fff;color:#111}small{color:#555}.cta{background:#eef4fb}a{color:#0b5cad}}</style>
</head>
<body><main>
<p><a href="__SITE__">8ULDUZ</a> › <a href="__SITE__icmal/">Günün icmalı</a></p>
<h1>__TITLE__</h1>
<p>__INTRO__</p>
<ol>__ITEMS__</ol>
<p class="cta">Hər səhər və axşam günün 10 əsas xəbəri Telegram kanalımızda: <a href="https://t.me/sekkizulduz_az">t.me/sekkizulduz_az</a></p>
<p>__NAV__<a href="__SITE__icmal/">Bütün icmallar</a> · <a href="__SITE__">8ULDUZ — bütün xəbərlər</a></p>
</main></body>
</html>
"""

def _digest_date(d):
    return f"{d.day} {_AZ_MONTH_NAMES[d.month - 1]} {d.year}"

def digest_page(ed, items, stories, prev=None):
    """Bir buraxılışın səhifəsi. ed: index.json sətri."""
    lis = []
    for i, a in enumerate(items, 1):
        href = f'{SITE}xeber/{a["id"]}/' if a.get("id") in (stories or {}) else f'{SITE}#/xeber/{a.get("id")}?b={a.get("category") or ""}'
        names = list(dict.fromkeys([a.get("source"), *(x.get("source") for x in a.get("alts") or [])]))
        names = [n for n in names if n]
        who = ", ".join(names[:3]) + (f" və daha {len(names) - 3}" if len(names) > 3 else "")
        summary = re.sub(r"<[^>]+>|\s+", " ", str(a.get("summary") or "")).strip()
        summary = summary if len(summary) <= 220 else summary[:217].rsplit(" ", 1)[0] + "…"
        lis.append(f'<li><a href="{_xml(href)}">{_xml(a.get("title"))}</a><small>{1 + len(a.get("alts") or [])} mənbə · {_xml(who)}</small>'
                   + (f"<p>{_xml(summary)}</p>" if summary and summary != a.get("title") else "") + "</li>")
    image = next((str(a.get("imageUrl")) for a in items if str(a.get("imageUrl") or "").startswith("https://")), f"{SITE}assets/og-default.png")
    ld = json.dumps({"@context": "https://schema.org", "@type": "ItemList", "name": ed["title"], "itemListElement": [
        {"@type": "ListItem", "position": i, "name": str(a.get("title") or ""),
         "url": f'{SITE}xeber/{a["id"]}/' if a.get("id") in (stories or {}) else SITE} for i, a in enumerate(items, 1)]},
        ensure_ascii=False).replace("</", "<\\/")
    nav = f'<a href="{SITE}icmal/{prev["slug"]}/">← {_xml(prev["title"])}</a> · ' if prev else ""
    return (_DIGEST_HTML.replace("__LD__", ld).replace("__ITEMS__", "".join(lis)).replace("__NAV__", nav)
            .replace("__INTRO__", _xml(f'{ed["label"]}: son {ed["hours"]} saatda ən çox mənbənin yazdığı {len(items)} xəbər. Sıra xəbəri yazan saytların sayına görədir.'))
            .replace("__DESC__", _xml("; ".join(str(a.get("title") or "") for a in items[:3])[:300]))
            .replace("__TITLE__", _xml(ed["title"])).replace("__IMAGE__", _xml(image))
            .replace("__URL__", f'{SITE}icmal/{ed["slug"]}/').replace("__SITE__", SITE))

def _digest_archive(index):
    lis = "".join(f'<li><a href="{SITE}icmal/{e["slug"]}/">{_xml(e["title"])}</a><small>{_xml(e.get("lead") or "")}</small></li>' for e in index[:60])
    ed = {"title": "Günün icmalı", "label": "8ULDUZ", "hours": 24, "slug": ""}
    page = digest_page(ed, [], {})
    page = page.replace(f'<link rel="canonical" href="{SITE}icmal//" />', f'<link rel="canonical" href="{SITE}icmal/" />')
    page = page.replace(f'content="{SITE}icmal//"', f'content="{SITE}icmal/"')
    page = re.sub(r"<p>8ULDUZ: son 24 saatda.*?</p>", "<p>Hər gün səhər 09:00-da və axşam 19:00-da ən çox mənbənin yazdığı 10 xəbər.</p>", page, count=1, flags=re.S)
    desc = "8ULDUZ: hər gün səhər və axşam ən çox mənbənin yazdığı 10 Azərbaycan xəbəri"
    return page.replace("<ol></ol>", f"<ol>{lis}</ol>").replace('content="" />', f'content="{desc}" />')

def read_digest_index():
    rows = _read_json(DIGEST_DIR / "index.json", [])
    return rows if isinstance(rows, list) else []

def write_digest(articles, stories=None, now=None):
    """Vaxtı çatmış, hələ yazılmamış buraxılışı yazır; buraxılışların siyahısını (ən yenisi birinci) qaytarır."""
    now = now or time.time()
    local = datetime.datetime.fromtimestamp(now, BAKU)
    index = read_digest_index()
    have = {e.get("slug") for e in index}
    changed = False
    for key, hour, label, hours in DIGEST_EDITIONS:
        at = local.replace(hour=hour, minute=0, second=0, microsecond=0)
        slug = f"{at:%Y-%m-%d}-{key}"
        if slug in have or not (0 <= (local - at).total_seconds() < DIGEST_LATE_H * 3600):
            continue
        end = at.timestamp()
        skip = {i for e in index if e.get("date") == f"{at:%Y-%m-%d}" for i in e.get("ids") or []}
        items = digest_pick(articles, end - hours * 3600, end, skip)
        if len(items) < 5:
            continue
        ed = {"slug": slug, "date": f"{at:%Y-%m-%d}", "edition": key, "label": label, "hours": hours, "at": int(end),
              "title": f"{label} · {_digest_date(at)}", "url": f"{SITE}icmal/{slug}/", "ids": [a["id"] for a in items],
              "items": [{"t": re.sub(r"\s+", " ", str(a.get("title") or "")).strip(), "n": 1 + len(a.get("alts") or [])} for a in items],
              "lead": re.sub(r"\s+", " ", str(items[0].get("title") or "")).strip()}
        d = DIGEST_DIR / slug
        d.mkdir(parents=True, exist_ok=True)
        _write_atomic(d / "index.html", digest_page(ed, items, stories, index[0] if index else None), encoding="utf-8")
        index.insert(0, ed)
        have.add(slug)
        changed = True
    keep_from = now - DIGEST_KEEP_DAYS * 86400
    for e in [e for e in index if e.get("at", 0) < keep_from]:
        for p in (DIGEST_DIR / e["slug"] / "index.html", DIGEST_DIR / e["slug"]):
            try:
                p.unlink() if p.is_file() else p.rmdir()
            except OSError:
                pass
        index.remove(e)
        changed = True
    if changed:
        DIGEST_DIR.mkdir(parents=True, exist_ok=True)
        index.sort(key=lambda e: e.get("at", 0), reverse=True)
        _write_atomic(DIGEST_DIR / "index.json", json.dumps(index, ensure_ascii=False, separators=(",", ":")))
        _write_atomic(DIGEST_DIR / "index.html", _digest_archive(index), encoding="utf-8")
    return index

def update_archive(now=None):
    now = now or time.time()
    articles = read_feed()
    missing = any(not (ARCHIVE_DIR / f"{s[0]}.json").exists() for s in SECTIONS if s[0] != "prezident")  # yeni bölmə bir saat boş qalmasın
    stamp = _read_json(ARCHIVE_DIR / "gundem.json", {})
    if not articles or (not missing and stamp.get("grouped") == 2 and now - stamp.get("at", 0) < ARCHIVE_EVERY_S):
        return
    cutoff = datetime.datetime.fromtimestamp(now - ARCHIVE_DAYS * 86400, datetime.timezone.utc)
    merged = {alt.get("sourceUrl") for a in articles for alt in a.get("alts") or []} | dead_links(len(articles))
    backlog = feed_backlog(cutoff)
    bulk = bulk_dated_sources()
    images = _read_json(ARCHIVE_OG_FILE, {})
    update_share_index(articles, now)
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
                previous = rows.get(url) or {}
                known = previous.get("imageUrl")  # lentin şəkilsiz nüsxəsi arxivdə tapılan şəkli silməsin
                rows[url] = {**({"imageUrl": known} if known else {}), **{k: a[k] for k in ARCHIVE_FIELDS if a.get(k)}, "sourceUrl": url, "category": slug}
                if previous.get("alts"):
                    rows[url]["alts"] = [*(a.get("alts") or []), *previous["alts"]]
        # Tarixi oxunmayan xəbər arxivdə qalmır.
        kept = [a for a in rows.values() if (_parse_dt(a.get("publishedAt")) or cutoff - datetime.timedelta(1)) >= cutoff
                and not is_junk(a.get("sourceUrl", "")) and not removed_source(a) and a.get("source") not in bulk
                and not is_negative_about_leadership(a.get("title", ""), a.get("summary", ""), a.get("source"))]
        kept, _ = content_policy.enforce(kept)
        # Köhnə xam arxiv də təmizlənir; ağır hadisə müqayisəsi yalnız yavaş dövrədədir.
        kept = group_duplicates(kept, same_source_exact=False)
        kept.sort(key=lambda a: a.get("publishedAt") or "", reverse=True)
        kept = kept[:ARCHIVE_MAX_BY_SECTION.get(slug, ARCHIVE_MAX)]
        for a in kept:
            if _is_generic_img(a.get("imageUrl")):
                del a["imageUrl"]
        if slug in BACKLOG_SECTIONS:
            kept = fill_archive_images(kept, images)
        ARCHIVE_DIR.mkdir(parents=True, exist_ok=True)
        _write_atomic(path, json.dumps({"at": now, "grouped": 2, "articles": kept}, ensure_ascii=False, separators=(",", ":")))
        for old in aliases:  # köhnə fayl boşalır: növbəti dəfə eyni xəbər yenidən köçürülməsin
            if old.exists():
                _write_atomic(old, json.dumps({"at": now, "articles": []}, separators=(",", ":")))
    _save_cache(ARCHIVE_OG_FILE, images)


# Səsli oxu söndürülüb, reader.json-u işlədən yoxdur: 400 xəbərin tam mətni açıq yayımlanmasın (müəllif hüququ).
# Sürücü rejimi qayıdanda (config.js, driver) True yazılır.
READER_ENABLED = False

def retire_reader():
    if READER_ENABLED:
        update_reader(read_feed(), OUT_DIR / "reader.json", lambda url: fetch(url, timeout=6))
    else:
        (OUT_DIR / "reader.json").unlink(missing_ok=True)


# 8ulduz-un öz xəbərləri (sahib 2026-11-12: «Sayta qoşmağa başla», sonra «Bəli, yandır»: açar pipeline.sh-də qoyulub).
# Açar OZ_DERC=1 mühit dəyişənidir; onu yalnız pipeline.sh qoyur. Açarsız aşağıdakı funksiyalar heç nə etmir: dərc modulu import
# olunmur, fayl oxunmur, yazılan hər fayl əvvəlki ilə bayt-bayt eynidir. Açarla: yavaş dövrə dərc dövrəsini çağırır (sorğu və
# ağır iş yalnız orada), sürətli dövrə yalnız onun yazdığı sətir faylının main-ə çatmış nüsxəsini oxuyur (QIRMIZI XƏTT 1:
# şəbəkə yoxdur) və sətirləri content_policy.enforce-dan ƏVVƏL lentə qatır (QIRMIZI XƏTT 2). Öz sətir lentə olduğu kimi düşür:
# əvvəlki lentdən yox, hər dövrə öz faylından gəlir (main), ona görə yenidən təsnif edilmir, mənbə və lent limitinə düşmür;
# qruplaşmır (group_duplicates), linki yoxlanmır (check_links), ümumi xəbər səhifəsi onun səhifəsinin üstünə yazılmır (write_story_pages).
# Niyə nüsxə (2026-11-12): kart birbaşa xəbərin səhifəsinə aparır. Dərc dövrəsi sətri data/oz/xeberler.json-a yazan kimi lentə
# qatılsaydı, sətir bir dəqiqəyə oxucuda olardı, səhifəsi isə sayta yalnız növbəti main yazılışı ilə (10–18 dəqiqə) çatardı:
# arada karta basan «tapılmadı» görərdi. pipeline.sh (own_rows_live) main-ə yazılmış sətir faylını Pages yayımından sonra bura köçürür.
OWN_SOURCE = "8ULDUZ"
OWN_FLAG = "OZ_DERC"
OWN_ROWS_FILE = CACHE_DIR / "oz-yayimda.json"  # səhifəsi saytda olan sətirlər; dərc dövrəsinin öz faylı: data/oz/xeberler.json
OWN_ROWS_KEEP = datetime.timedelta(days=5)  # lentin ümumi yaş həddi; dərc dövrəsi özü 48 saat saxlayır (dövrə dayansa köhnə sətir lentdə ilişməsin)
_OWN_ROW_KEYS = ("id", "title", "sourceUrl", "publishedAt", "category")


def own_news_on():
    return os.environ.get(OWN_FLAG) == "1"


def update_own_news():
    """Yavaş addım: öz xəbərlərin dərc dövrəsi. Açar yoxdursa import-dan ƏVVƏL qayıdır: xərci yoxdur, xəta verə bilməz."""
    if not own_news_on():
        return None
    import oz_derc  # tənbəl: açarsız proses bu modulu heç yükləmir (köhnə kod qovluğunda fayl olmaya da bilər)
    res = oz_derc.cycle(ROOT)
    print(f"Öz xəbərlər: dərc {len(res.get('published') or [])}, növbədə {res.get('queued', 0)}, saxlanılan {len(res.get('held') or [])}, "
          f"rədd {len(res.get('blocked') or [])}, xəta {len(res.get('errors') or [])}", flush=True)
    return res


def read_own_rows(now=None):
    """Öz xəbərlərin lent sətirləri: yalnız səhifəsi artıq saytda olanlar (OWN_ROWS_FILE, pipeline.sh own_rows_live). Yalnız
    fayl oxunur. Açar yoxdursa, fayl yoxdursa və ya pozulubsa boş siyahı; forması düz olmayan, mənbəyi «8ULDUZ» olmayan,
    tarixi oxunmayan və ya 5 gündən köhnə sətir götürülmür. Sətir dəyişdirilmir."""
    if not own_news_on():
        return []
    doc = _read_json(OWN_ROWS_FILE, {})
    rows = doc.get("articles") if isinstance(doc, dict) else None
    floor = (now or datetime.datetime.now(datetime.timezone.utc)) - OWN_ROWS_KEEP
    out, seen = [], set()
    for r in rows if isinstance(rows, list) else []:
        if not isinstance(r, dict) or r.get("source") != OWN_SOURCE or not all(isinstance(r.get(k), str) and r[k] for k in _OWN_ROW_KEYS):
            continue
        dt = _parse_dt(r["publishedAt"])
        if dt is None or dt < floor or r["sourceUrl"] in seen:
            continue
        seen.add(r["sourceUrl"])
        out.append(r)
    return out


def merge_own_rows(articles, own):
    """Öz sətirləri lentə tarix sırası ilə qatır (hər biri özündən köhnə ilk sətrin qabağına). Öz sətir yoxdursa lentin özü qayıdır."""
    if not own:
        return articles
    have = {a.get("sourceUrl") for a in articles}
    rest = sorted((r for r in own if r["sourceUrl"] not in have), key=lambda r: r["publishedAt"])  # ən yenisi sonda: pop() onu verir
    out = []
    for a in articles:
        while rest and rest[-1]["publishedAt"] >= (a.get("publishedAt") or ""):
            out.append(rest.pop())
        out.append(a)
    return out + rest[::-1]


def slow_cycle():
    """Xəbər axınını gözlətməməli olan hər şey. Hər addım müstəqildir: biri düşsə digərləri işləyir."""
    articles = read_feed()
    # SOCIAL_LOOP: rəsmi hesabların yazıları pipeline.sh-in social_loop-unda hər dəqiqə yığılır (--social), burada yox.
    social = [] if os.environ.get("SOCIAL_LOOP") else [update_social]
    # update_own_news: yalnız OZ_DERC=1 ilə işləyir (yuxarıda); məzənnədən sonra, çünki təzə data/markets.json-u oxuyur.
    steps = [compute_groups, update_markets, update_own_news, resolve_undated, *social, update_video, update_football, update_sports,
             lambda: fill_og_images(drop_dead_images(articles)), retire_reader, refresh_slow_feeds, update_city_data, write_public, update_archive, update_team_pages]
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
    ("TRY100", "100 Lirə", "AZN", 4), ("CNY", "Yuan", "AZN", 4), ("BRENT", "Brent", "USD", 2), ("WTI", "Neft (WTI)", "USD", 2),
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
        for mid, code, mult in (("USD", "USD", 1), ("EUR", "EUR", 1), ("RUB100", "RUB", 100), ("TRY100", "TRY", 100), ("CNY", "CNY", 1)):
            if code in r:
                res[mid] = {"value": r[code] * mult, "prev": p[code] * mult if code in p else None,
                            "src": "AMB", "asOf": cur[0].isoformat()}
        return res
    # Ehtiyat: open.er-api.com (açarsız, gündəlik)
    g = fetch_json("https://open.er-api.com/v6/latest/USD")
    azn = g["rates"]["AZN"]
    for mid, code, mult in (("USD", "USD", 1), ("EUR", "EUR", 1), ("RUB100", "RUB", 100), ("TRY100", "TRY", 100), ("CNY", "CNY", 1)):
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
    raw = norm_az(_clean_text(s))  # «İyun».lower() = «i̇yun» (nöqtə ayrı işarə): ay tanınmır, yazı «bu gün» tarixi alırdı
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
    """«Oktyabr 31, 2026 11:00» (sosial.gov.az) və «Bu gün, 17:00», «Dünən,22:00», «30-10-2026» (Naxçıvan Xəbərləri) parse_az_date-in bildiyi sıraya çevrilir."""
    near = re.fullmatch(r"(bu gün|dünən)\s*,?\s*(\d{1,2}:\d{2})", raw.strip().lower())
    if near:
        day = datetime.datetime.now(BAKU) - datetime.timedelta(days=near.group(1) == "dünən")
        return parse_az_date(f"{day:%d.%m.%Y} {near.group(2)}")
    dashed = re.fullmatch(r"(\d{2})-(\d{2})-(20\d{2})", raw.strip())
    if dashed:
        return parse_az_date(".".join(dashed.groups()))
    iso = re.fullmatch(r"(20\d{2})-(\d{2})-(\d{2})[T ](\d{2}:\d{2}).*", raw.strip())
    if iso:
        return parse_az_date(f"{iso.group(3)}.{iso.group(2)}.{iso.group(1)} {iso.group(4)}")
    swapped = re.fullmatch(r"([^\d\s]+)\s+(\d{1,2}),\s+(20\d{2})(.*)", raw.strip())
    text = f"{swapped.group(2)} {swapped.group(1)} {swapped.group(3)}{swapped.group(4)}" if swapped else raw
    return parse_az_date(text)
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
    "https://naxcivanxeberleri.az/": (r'(?=<li>\s*<div class="thumb">)', r'href="([^"]+/bloq/[^"]+)"', r'<h4>\s*<a[^>]+>(.*?)</a>', r'class="meta">\s*<span[^>]*>([^<]+)</span>'),
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
    """Rəsmi hesabların YouTube yazıları (merge_yt) və xəbərlərdən çıxarılan paylaşımlar -> social.json (son 16).
    pipeline.sh-in social_loop-u bunu hər dəqiqə çağırır (SOCIAL_LOOP), köhnə pipeline-da yavaş dövrə (4-5 dəqiqə)."""
    doc = _read_json(SOCIAL_FILE, {})
    doc = doc if isinstance(doc, dict) else {}
    old = [p for p in doc.get("posts") or [] if isinstance(p, dict)]
    tops = dict(doc["shorts"]) if isinstance(doc.get("shorts"), dict) else {}
    arch = _read_json(SOCIAL_ARCHIVE_FILE, {})
    arch = arch.get("posts") if isinstance(arch, dict) and isinstance(arch.get("posts"), list) else []
    known = {_yt_id(p.get("url")) for p in [*old, *arch] if isinstance(p, dict)} - {""}
    pages = yt_account_pages(YT_ACCOUNTS)
    posts, failed, yt_rows, carried = [], set(), [], []
    for url, who, name in YT_ACCOUNTS:
        got = [pages.get((url, tab)) for tab in ("rss", "videos", "streams", "shorts")]
        rss, videos, streams, shorts = (x if isinstance(x, list) else None for x in got)
        videos = None if videos is None and streams is None else [*(videos or []), *(streams or [])]
        try:
            if not rss and not videos:
                raise next((x for x in got[:3] if isinstance(x, Exception)), ValueError("boş lent"))
            items, top = merge_yt(rss, videos, shorts, known=known, top=tops.get(who))
            if top:
                tops[who] = top
            if not items:
                raise ValueError("boş lent")
            yt_rows.append({"name": f"YouTube · {name}", "url": url, "count": len(items), "error": None})
            # Yeni Short bir dövrə görünür (merge_yt onu yalnız ilk dəfə «təzə» sayır), sonra RSS-ə düşənədək itirdi: Shorts
            # səhifəsində hələ duran əvvəlki yazı saxlanır, ilk görüldüyü vaxtla.
            on_page, got_ids = {_yt_id(x.get("link")) for x in shorts or []} - {""}, {_yt_id(it.get("link")) for it in items}
            carried.extend(p for p in old if p.get("who") == who and p.get("network") == "YouTube" and not p.get("via")
                           and _yt_id(p.get("url")) in on_page - got_ids)
            for it in items:
                posts.append({
                    "id": hashlib.sha1(it["link"].encode()).hexdigest()[:16],
                    "who": who, "name": name, "network": "YouTube",
                    "text": it["title"], "url": it["link"],
                    "publishedAt": to_iso(it.get("pubDate")),
                    "imageUrl": it.get("image"),
                    "_approx": bool(it.get("approx")),
                })
        except Exception as e:
            failed.add(who)
            yt_rows.append({"name": f"YouTube · {name}", "url": url, "count": 0, "error": f"{type(e).__name__}: {str(e)[:80]}"})
            print(f"  ! sosial {name}: {type(e).__name__}: {str(e)[:80]}")
    # Səhifənin vaxtı təxminidir («5 minutes ago»): ilk qeyd olunan saxlanır ki, sıra sürüşməsin. RSS-in vaxtı dəqiqdir, olduğu kimi.
    _keep_first_seen([p for p in posts if p.pop("_approx")], old)
    posts.extend(carried)
    if failed:
        posts.extend(p for p in old if p.get("who") in failed and p.get("network") == "YouTube")
    try:
        arts = read_feed()
        posts.extend(social_from_news(arts))
    except Exception as e:
        print(f"  ! sosial (xəbərdən): {type(e).__name__}: {str(e)[:80]}")
    posts.sort(key=lambda p: p.get("publishedAt") or "", reverse=True)
    now = datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds")
    OUT_DIR.mkdir(exist_ok=True)
    # Əvvəl arxiv və paylaşma səhifələri, sonra social.json (sahib 2026-11-07: «daimi düzəliş, sonra problem olmasın»): saytda görünən
    # hər yazının səhifəsi eyni yayımda artıq var. Səhifə alınmasa 404.html saytın kartını göstərib oxucunu yazıya aparır.
    try:
        write_social_share_pages(write_social_archive(posts))
    except Exception as e:
        print(f"  ! sosial arxiv: {type(e).__name__}: {str(e)[:80]}")
    shown = posts[:16]
    # rev: yazıların möhürü. status.json-a «social» kimi düşür (write_status), sayt social.json-u yalnız möhür dəyişəndə çəkir.
    rev = hashlib.sha1(json.dumps(shown, ensure_ascii=False, sort_keys=True).encode()).hexdigest()[:10]
    _write_atomic(SOCIAL_FILE, json.dumps({"updatedAt": now, "rev": rev, "shorts": tops, "posts": shown}, ensure_ascii=False,
                                       separators=(",", ":")), encoding="utf-8")
    merge_sources(yt_rows)
    print(f"Sosial: {len(shown)} yazı ({sum(1 for p in shown if p.get('via'))} xəbərdən)")

# Sosial yazının paylaşma səhifəsi (sahib 2026-11-07: «sosial şəbəkələrdən paylaşanda kimə aiddirsə adı yazılsın: İlham Əliyev:
# başlıq»). bolme/prezident/s/<id>.html: og başlığı «İlham Əliyev: …» / «Mehriban Əliyeva: …», yazının şəkli, oxucu dərhal
# Zuğulba xronikasında həmin yazıya keçir (#/bolme/prezident?s=<id>). Arxiv qədər (30 gün) qalır; dəyişməyən səhifə yazılmır.
SOCIAL_WHO = {"prezident": "İlham Əliyev", "birinci-xanim": "Mehriban Əliyeva"}

def social_share_title(p):
    text = re.sub(r"\s+", " ", html.unescape(str(p.get("text") or ""))).strip()
    who = SOCIAL_WHO.get(p.get("who"))
    return f"{who}: {text}" if who else text

def social_share_page(p):
    sid = p["id"]
    image, fallback = str(p.get("imageUrl") or ""), f"{SITE}assets/og-default.png"
    image = (f"https://wsrv.nl/?url={urllib.parse.quote(image, safe='')}&w=1200&h=630&fit=cover&a=attention&output=jpg&q=78&default={urllib.parse.quote(fallback, safe='')}"
             if image.startswith("https://") else fallback)
    desc = " · ".join(x for x in (p.get("name"), p.get("network"), p.get("via")) if x) or "8ulduz"
    return _SHARE_HTML.format(lang="az", title=_xml(social_share_title(p)), desc=_xml(desc), url=_xml(f"{SITE}bolme/prezident/s/{sid}"),
                              image=_xml(image), locale="az_AZ", app=_xml(f"{SITE}#/bolme/prezident?s={sid}"), site=SITE,
                              pre=f'<script>location.replace({_js(f"{SITE}#/bolme/prezident?s={sid}")})</script>\n')  # oxucu skriptlə keçir (meta refresh yoxdur)

def write_social_share_pages(rows, root=None):
    """Arxivdəki hər yazının (16 rəqəmli id) paylaşma səhifəsi; arxivdən çıxanın səhifəsi silinir. Yazılan səhifə sayını qaytarır."""
    d = (root or ROOT) / "bolme" / "prezident" / "s"
    d.mkdir(parents=True, exist_ok=True)
    keep, n = set(), 0
    for p in rows:
        if not re.fullmatch(r"[0-9a-f]{16}", str(p.get("id") or "")):
            continue
        keep.add(f'{p["id"]}.html')
        page, f = social_share_page(p), d / f'{p["id"]}.html'
        try:
            if f.read_text(encoding="utf-8") == page:
                continue
        except OSError:
            pass
        _write_atomic(f, page, encoding="utf-8")
        n += 1
    for f in d.glob("*.html"):
        if f.name not in keep:
            f.unlink(missing_ok=True)
    return n

SOCIAL_ARCHIVE_FILE = OUT_DIR / "social-arxiv.json"
SOCIAL_ARCHIVE_DAYS, SOCIAL_ARCHIVE_MAX = 30, 400

def write_social_archive(posts, now=None):
    """Paylaşılan «#/bolme/prezident?s=<id>» keçidi günlər sonra da açılsın (sahib 2026-11-07: «bir neçə saat sonra o xəbər yox
    idi»): social.json yalnız son 16 yazını saxlayır, burada 30 günün yazıları qalır. Sayt bu faylı yalnız keçiddəki yazı
    social.json-da olmayanda yükləyir."""
    old = _read_json(SOCIAL_ARCHIVE_FILE, {})
    old = old.get("posts") if isinstance(old, dict) and isinstance(old.get("posts"), list) else []
    cutoff = (now or time.time()) - SOCIAL_ARCHIVE_DAYS * 86400
    seen, rows = set(), []
    for p in [*posts, *old]:
        pid = p.get("id") if isinstance(p, dict) else None
        dt = _parse_dt(p.get("publishedAt")) if pid else None
        if not pid or pid in seen or not dt or dt.timestamp() < cutoff:
            continue
        # QIRMIZI XƏTT 2: xəbərdən çıxan yazı (via) 30 gün burada qalır — sahibin sonradan çıxardığı və ya mənbəsi siyahıdan
        # çıxan xəbər arxivdə və paylaşma səhifəsində qalmasın (əvvəl arxiv heç vaxt yenidən yoxlanmırdı).
        if p.get("via") and content_policy.violation({"id": pid, "source": p["via"], "sourceUrl": p.get("url"), "title": p.get("text") or "", "category": "prezident"}):
            continue
        seen.add(pid)
        rows.append(p)
    rows.sort(key=lambda p: p.get("publishedAt") or "", reverse=True)
    rows = rows[:SOCIAL_ARCHIVE_MAX]
    if rows != old:
        _write_atomic(SOCIAL_ARCHIVE_FILE, json.dumps({"posts": rows}, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    return rows

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

# YouTube-un RSS lenti (feeds/videos.xml) 2026-cı ilin oktyabrından bəzən 404 qaytarır, işləyəndə də yeni videonu 5-10 dəqiqə
# gec göstərir. Kanal səhifəsində (ytInitialData JSON-u) hər videonun kartı var: contentId, başlıq və nisbi vaxt («21 min ago»).
_YT_MARK = re.compile(r'"contentId":"([A-Za-z0-9_-]{11})","contentType":"LOCKUP_CONTENT_TYPE_VIDEO"')
_YT_TITLE = re.compile(r'"lockupMetadataViewModel":\{"title":\{"content":"((?:[^"\\]|\\.)*)"')
_YT_REL = re.compile(r'"accessibilityLabel":"(?:Streamed )?(\d+) (second|minute|hour|day|week|month|year)s? ago"')
_YT_UNIT = {"second": 1, "minute": 60, "hour": 3600, "day": 86400, "week": 604800, "month": 2592000, "year": 31536000}
_YT_SHORT = re.compile(r'"entityId":"shorts-shelf-item-([A-Za-z0-9_-]{11})"')
_YT_SHORT_TITLE = re.compile(r'"overlayMetadata":\{"primaryText":\{"content":"((?:[^"\\]|\\.)*)"')

def _yt_text(s):
    try:
        return json.loads('"' + s + '"')
    except Exception:
        return s

def parse_yt_channel_page(text, limit=10, now=None):
    """Kanalın «videos» səhifəsi, kart-kart ({"lockupViewModel":…}). Kart başlığı və vaxtı contentId-dən ƏVVƏL yazır: 2026-11-08-ə
    qədər contentId-dən sonrakı mətn oxunurdu və hər videoya növbəti videonun başlığı və vaxtı düşürdü (Prezidentin videoları
    saytda 1-1,5 saat erkən görünürdü)."""
    now = now or datetime.datetime.now(datetime.timezone.utc)
    items, seen = [], set()
    for chunk in text.split('{"lockupViewModel":')[1:]:
        mk, t = _YT_MARK.search(chunk), _YT_TITLE.search(chunk)
        if not mk or not t or mk.group(1) in seen:
            continue
        vid = mk.group(1)
        seen.add(vid)
        rel = _YT_REL.search(chunk)
        pub = now - datetime.timedelta(seconds=int(rel.group(1)) * _YT_UNIT[rel.group(2)]) if rel else now
        items.append({"title": _yt_text(t.group(1)), "link": f"https://www.youtube.com/watch?v={vid}", "description": "",
                      "pubDate": pub.isoformat(timespec="seconds"),
                      "image": f"https://i.ytimg.com/vi/{vid}/hqdefault.jpg", "author": ""})
        if len(items) >= limit:
            break
    return items

def parse_yt_shorts_page(text, limit=20):
    """Kanalın «shorts» səhifəsi: ən yenidən köhnəyə. Vaxt yazılmır (merge_yt yeniliyi sıradan tanıyır)."""
    items, seen = [], set()
    for chunk in text.split('"shortsLockupViewModel":{')[1:]:
        mk, t = _YT_SHORT.search(chunk), _YT_SHORT_TITLE.search(chunk)
        if not mk or not t or mk.group(1) in seen:
            continue
        vid = mk.group(1)
        seen.add(vid)
        items.append({"title": _yt_text(t.group(1)), "link": f"https://www.youtube.com/shorts/{vid}", "description": "",
                      "image": f"https://i.ytimg.com/vi/{vid}/hqdefault.jpg", "author": ""})
        if len(items) >= limit:
            break
    return items

def _yt_page(feed_url, tab):
    """Kanalın «videos»/«streams»/«shorts» səhifəsi, gzip ilə (1,3 MB əvəzinə ~0,3 MB)."""
    m, u = re.search(r"channel_id=([A-Za-z0-9_-]+)", feed_url), re.search(r"user=([A-Za-z0-9_-]+)", feed_url)
    if not m and not u:
        raise ValueError("kanal tapılmadı")
    page = f"https://www.youtube.com/channel/{m.group(1)}/{tab}" if m else f"https://www.youtube.com/user/{u.group(1)}/{tab}"
    req = urllib.request.Request(page, headers={"User-Agent": UA, "Accept-Language": "en-US,en;q=0.9",
                                                "Cookie": "CONSENT=YES+cb; SOCS=CAI", "Accept-Encoding": "gzip"})
    with urllib.request.urlopen(req, timeout=20) as r:
        raw = _read_capped(r)
        if (r.headers.get("Content-Encoding") or "").lower() == "gzip":
            raw = _gunzip_capped(raw)
    return raw.decode("utf-8", "replace")

def yt_channel_videos(feed_url, limit=10):
    items = parse_yt_channel_page(_yt_page(feed_url, "videos"), limit)
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

def yt_account_pages(accounts):
    """Rəsmi hesabların RSS-i, «videos», «streams» (canlı yayımlar: Prezidentin müraciətləri, mərasimlər) və «shorts» səhifəsi
    paralel (ən çox ~20 s): {(url, "rss"|"videos"|"streams"|"shorts"): siyahı və ya xəta}."""
    jobs = {}
    with ThreadPoolExecutor(max_workers=8) as ex:
        for url, _, _ in accounts:
            jobs[(url, "rss")] = ex.submit(lambda u=url: parse_feed(fetch(u)))
            for tab in ("videos", "streams"):
                jobs[(url, tab)] = ex.submit(lambda u=url, t=tab: parse_yt_channel_page(_yt_page(u, t)))
            jobs[(url, "shorts")] = ex.submit(lambda u=url: parse_yt_shorts_page(_yt_page(u, "shorts")))
    out = {}
    for key, job in jobs.items():
        try:
            out[key] = job.result()
        except Exception as e:
            out[key] = e
    return out

def merge_yt(rss, videos, shorts, known=(), top=None, limit=4, now=None):
    """Bir hesabın RSS, «videos» və «shorts» siyahıları (alınmayan None) -> (son yazılar, «shorts»-un ən üstündəki id).
    Sahib 2026-11-08: «1 dəq öncə Mehriban Əliyeva Youtubda paylaşımı bizdə yoxdur» — video kanalda 16:19-da idi, RSS-də 16:27-də.
    - RSS-dəki yazı RSS-in dəqiq vaxtı və başlığı ilə;
    - RSS-də hələ olmayan video «videos» səhifəsindən, nisbi vaxtla (approx: ilk qeyd olunan vaxt saxlanır);
    - «shorts» səhifəsi vaxt yazmır: tanınan Shorts-dan (RSS-də, əvvəlki yazılarda, keçən dəfə ən üstdə olan) yuxarıdakılar yenidir,
      vaxtı ilk görüldüyü an. Tanınan tapılmasa heç biri götürülmür: köhnə Shorts təzə kimi görünməsin."""
    now = now or datetime.datetime.now(datetime.timezone.utc)
    items, have = [], set()
    for it, approx in [*((x, False) for x in rss or []), *((x, True) for x in videos or [])]:
        v = _yt_id(it.get("link"))
        if v and v not in have:
            have.add(v)
            items.append({**it, "approx": approx})
    if shorts:
        anchors, fresh = have | set(known) | {top}, []
        for it in shorts:
            if _yt_id(it.get("link")) in anchors:
                break
            fresh.append(it)
        else:
            fresh = []
        for it in fresh:
            items.append({**it, "pubDate": now.isoformat(timespec="seconds"), "approx": True})
        top = _yt_id(shorts[0].get("link")) or top
    items.sort(key=lambda it: to_iso(it.get("pubDate")) or "", reverse=True)
    return items[:limit], top

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
    try:  # alınmayan kanalın əvvəlki videoları qalır (sosial, futbol, idman blokları kimi): əvvəl bir uğursuz dövrə bloku boşaldırdı
        was = [p for p in json.loads(VIDEO_FILE.read_text(encoding="utf-8")).get("items") or [] if isinstance(p, dict)]
    except Exception:
        was = []
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
            items = [p for p in items if p.get("channel") != name]  # yarımçıq oxunan kanal: köhnə siyahısı bütöv qayıdır
            items.extend(p for p in was if p.get("channel") == name and not is_negative_about_leadership(p.get("title", ""), ""))
    try:
        _keep_first_seen(items, was)
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

# Dünya liqaları: ingiliscə Vikipediyanın cədvəlləri (CC BY-SA), açar tələb etmir. ESPN 2026-10-27-dən sorğumuza 403 verir, bloku keçmirik.
WIKI_API = "https://en.wikipedia.org/w/api.php?format=json&formatversion=2&"
WIKI_UA = "8ulduz.az/1.0 (https://8ulduz.az) standings"
CONFERENCES = ("Eastern Conference", "Western Conference")
WIKI_LEAGUES = [
    # id, idman, ad, qısa ad, səhifə ({s}: 2026–27, {y}: 2026), bir neçə cədvəl varsa onların adı
    ("eng.1", "football", "Premyer Liqa (İngiltərə)", "İngiltərə", "{s} Premier League", ()),
    ("esp.1", "football", "La Liga", "İspaniya", "{s} La Liga", ()),
    ("ita.1", "football", "Seriya A", "İtaliya", "{s} Serie A", ()),
    ("ger.1", "football", "Bundesliqa", "Almaniya", "{s} Bundesliga", ()),
    ("fra.1", "football", "Liqa 1", "Fransa", "{s} Ligue 1", ()),
    ("tur.1", "football", "Süper Liq", "Türkiyə", "{s} Süper Lig", ()),
    ("por.1", "football", "Primeyra Liqa", "Portuqaliya", "{s} Primeira Liga", ()),
    ("ned.1", "football", "Eredivizie", "Hollandiya", "{s} Eredivisie", ()),
    ("bel.1", "football", "Pro Liqa (Belçika)", "Belçika", "{s} Belgian Pro League", ()),
    ("sco.1", "football", "Premyership", "Şotlandiya", "{s} Scottish Premiership", ()),
    ("rus.1", "football", "Premyer Liqa (Rusiya)", "Rusiya", "{s} Russian Premier League", ()),
    ("ksa.1", "football", "Pro Liqa (Səudiyyə)", "Səudiyyə", "{s} Saudi Pro League", ()),
    ("bra.1", "football", "Seriya A (Braziliya)", "Braziliya", "{y} Campeonato Brasileiro Série A", ()),
    ("usa.1", "football", "MLS", "ABŞ", "{y} Major League Soccer season", CONFERENCES),
    ("eng.2", "football", "Çempionşip", "Çempionşip", "{s} EFL Championship", ()),
    ("uefa.champions", "football", "Çempionlar Liqası", "ÇL", "{s} UEFA Champions League league phase", ()),
    ("uefa.europa", "football", "Avropa Liqası", "AL", "{s} UEFA Europa League league phase", ()),
    ("uefa.conference", "football", "Konfrans Liqası", "KL", "{s} UEFA Conference League league phase", ()),
    ("nba", "basketball", "NBA", "NBA", "{s} NBA season", CONFERENCES),
    ("euroleague", "basketball", "Avroliqa", "Avroliqa", "{s} EuroLeague", ()),
]
SPORTS_EVERY = datetime.timedelta(minutes=15)
SPORTS_STALE = datetime.timedelta(hours=3)
SPORTS_BUDGET_S = 25  # bir yavaş dövrədə; çatmayan liqa növbəti dövrəyə qalır (ən köhnə yoxlanan birinci)
WIKI_SHORT = {"Manchester City": "Man City", "Manchester United": "Man United", "Tottenham Hotspur": "Tottenham", "Nottingham Forest": "Nottm Forest",
              "Wolverhampton Wanderers": "Wolves", "Brighton & Hove Albion": "Brighton", "Newcastle United": "Newcastle", "Crystal Palace": "C Palace",
              "Paris Saint-Germain": "PSG", "Bayern Munich": "Bayern", "Borussia Dortmund": "Dortmund", "Bayer Leverkusen": "Leverkusen",
              "Borussia Mönchengladbach": "Gladbach", "Eintracht Frankfurt": "Frankfurt", "Atlético Madrid": "Atlético", "Athletic Bilbao": "Athletic",
              "Internazionale": "İnter", "Inter Milan": "İnter", "Sporting CP": "Sporting", "PSV Eindhoven": "PSV"}
WIKI_NOTE = (("Champions League", "Çempionlar Liqası"), ("Europa League", "Avropa Liqası"), ("Conference League", "Konfrans Liqası"),
             ("Libertadores", "Kopa Libertadores"), ("Sudamericana", "Kopa Sudamerikana"),
             ("round of 16", "1/8 final"), ("playoff", "Pley-off"), ("Promotion", "Yuxarı liqaya keçid"), ("Relegation", "Aşağı liqaya düşmə"), ("Eliminated", "Mübarizədən çıxır"))
_WIKI_NAME = re.compile(r"[\w .'’&/\-]{2,40}", re.U)
_WIKI_MONTHS = ("January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December")
_WIKI_FLAG = re.compile(r"<span class=\"flagicon\">.*?</span>", re.S)

def _num(v, default=0):
    try:
        return int(float(v))
    except Exception:
        return default

def _wiki_text(raw):
    raw = _WIKI_FLAG.sub("", re.sub(r"<sup\b.*?</sup>|<style\b.*?</style>", "", raw, flags=re.S))
    text = html.unescape(re.sub(r"<[^>]+>", "", raw)).replace("‍", "").replace("\xa0", " ")
    return text.replace("−", "-").replace("–", "-").strip()

def _wiki_int(text):
    text = _wiki_text(text)
    if not re.fullmatch(r"[+-]?\d+", text):
        raise ValueError(f"rəqəm deyil: {text[:20]}")
    return int(text)

def _wiki_table(table, sport):
    """Bir cədvəl: sütunları başlığa görə tapır. Komanda sütunu olmayan cədvəl (NBA-nın divizionları) None qaytarır."""
    rows, head = [], None
    note, note_left = "", 0
    for tr in re.findall(r"<tr\b.*?</tr>", table, re.S):
        cells = re.findall(r"<t[dh]\b([^>]*)>(.*?)</t[dh]>", tr, re.S)
        if head is None:
            names = [_wiki_text(c[1]) for c in cells]
            if len(names) >= 4 and any(n.startswith("Team") for n in names):
                head = {("team" if n.startswith("Team") else n): i for i, n in enumerate(names)}
            continue
        if len(cells) <= head.get("L", 99):
            continue
        cell = lambda *keys: next(cells[head[k]][1] for k in keys if k in head)
        attrs = lambda *keys: next(cells[head[k]][0] for k in keys if k in head)
        team = cell("team")
        full = re.sub(r"\s*(?:\([A-Z](?:, ?[A-Z])*\)|\*+)$", "", re.sub(r"^[a-z]{1,2} - ", "", _wiki_text(team)))
        if not _WIKI_NAME.fullmatch(full):
            raise ValueError(f"komanda adı: {full[:20]}")
        link = re.search(r"<a\b[^>]*\btitle=\"([^\"]+)\"", _WIKI_FLAG.sub("", team))
        short = full.split()[-1] if sport == "basketball" and "#" in head and " " in full else full
        row = {"team": WIKI_SHORT.get(full) or ("Trail Blazers" if full.endswith("Trail Blazers") else short), "full": full, "logo": "",
               "_page": html.unescape(link.group(1)) if link else full, "pos": _wiki_int(cell("Pos", "#")),
               "p": _wiki_int(cell("Pld", "GP")), "w": _wiki_int(cell("W")), "l": _wiki_int(cell("L"))}
        if sport == "football":
            row.update({"d": _wiki_int(cell("D", "T")), "gf": _wiki_int(cell("GF")), "ga": _wiki_int(cell("GA")), "pts": _wiki_int(cell("Pts"))})
            row["gd"] = row["gf"] - row["ga"]
            color = re.search(r"background-color:(#[0-9a-fA-F]{6})", attrs("Pos", "#"))
            if color:
                row["color"] = color.group(1)
            # Son sütun birləşmiş xanadır: cədvəlin bir neçə sətrinə aiddir.
            if note_left <= 0 and len(cells) > head["Pts"] + 1:
                span = re.search(r"rowspan=\"(\d+)\"", cells[head["Pts"] + 1][0])
                note_left = int(span.group(1)) if span else 1
                text = _wiki_text(cells[head["Pts"] + 1][1])
                note = next((az for en, az in WIKI_NOTE if en in text), "")
            if note:
                row["note"] = note
            note_left -= 1
        rows.append(row)
    return rows if head else None

def parse_wiki(text, sport, names=()):
    """Vikipediya bölməsi -> qruplar. Cədvəl öz-özünə ziddirsə (səhv redaktə) istisna atır: əvvəlki məlumat qalır."""
    groups = [rows for rows in (_wiki_table(t, sport) for t in re.findall(r"<table\b.*?</table>", text, re.S)) if rows]
    if not groups or (names and len(groups) != len(names)):
        raise ValueError("cədvəl tapılmadı")
    out = []
    for i, rows in enumerate(groups):
        if len(rows) < 8 or len({r["full"] for r in rows}) != len(rows):
            raise ValueError("sətirlər səhvdir")
        top = rows[0]
        for r in rows:
            if r["w"] + r["l"] + r.get("d", 0) != r["p"]:
                raise ValueError(f"oyunların cəmi: {r['full'][:20]}")
            if sport == "football":
                if not 3 * r["w"] + r["d"] - 15 <= r["pts"] <= 3 * r["w"] + r["d"]:
                    raise ValueError(f"xal: {r['full'][:20]}")
            else:
                behind = ((top["w"] - r["w"]) + (r["l"] - top["l"])) / 2
                r["pct"], r["gb"] = round(r["w"] / r["p"], 3) if r["p"] else 0.0, f"{behind:.1f}" if behind else "-"
        out.append({"name": names[i] if names else "", "rows": rows})
    return out

def wiki_asof(text):
    """«Updated to match(es) played on 26 October 2026» -> 2026-10-26: cədvəlin hansı günə qədər olduğu saytda yazılır."""
    m = re.search(r"Updated to match\(es\) played on (?:(\d{1,2}) (\w+)|(\w+) (\d{1,2}),) (\d{4})", text)
    if not m or (m.group(2) or m.group(3)) not in _WIKI_MONTHS:
        return ""
    return f"{m.group(5)}-{_WIKI_MONTHS.index(m.group(2) or m.group(3)) + 1:02d}-{int(m.group(1) or m.group(4)):02d}"

def _wiki_api(query):
    return json.loads(fetch(WIKI_API + query, timeout=12, headers={"User-Agent": WIKI_UA, "Accept": "application/json"}).decode("utf-8"))

def _wiki_title(pattern, now_dt):
    year = now_dt.year if now_dt.month >= 7 else now_dt.year - 1
    return pattern.format(s=f"{year}–{(year + 1) % 100:02d}", y=now_dt.year)

def _wiki_logos(pages):
    """Klub səhifəsinin şəkli (loqo). Bir sorğuda 50 səhifəyədək. NBA-da keçid mövsüm səhifəsinədir: klubun özünə baxılır."""
    plain = {p: re.sub(r"^\d{4}[–-]\d{2} (.+) season$", r"\1", p) for p in pages}
    query = urllib.parse.urlencode({"action": "query", "redirects": 1, "prop": "pageimages", "piprop": "thumbnail", "pithumbsize": 80, "pilicense": "any",
                                    "pilimit": 50, "titles": "|".join(sorted(set(plain.values()))[:50])})
    res = _wiki_api(query).get("query") or {}
    to = {x["from"]: x["to"] for key in ("normalized", "redirects") for x in res.get(key) or []}
    images = {p.get("title"): (p.get("thumbnail") or {}).get("source", "").split("?")[0] for p in res.get("pages") or []}
    def final(title):
        for _ in range(4):
            title = to.get(title, title)
        return title
    return {page: images.get(final(title), "") for page, title in plain.items()}

def _wiki_league(spec, prev, now_dt):
    lid, sport, name, short, pattern, names = spec
    title = _wiki_title(pattern, now_dt)
    page = urllib.parse.quote(title)
    section = lambda index: _wiki_api(f"action=parse&prop=text&page={page}&section={index}")["parse"]["text"]
    sec, text, groups = prev.get("sec"), "", None
    if sec is not None:
        try:
            text = section(sec)
            groups = parse_wiki(text, sport, names)
        except Exception:
            groups = None  # bölmənin nömrəsi dəyişib: siyahıdan təzədən tapılır
    if groups is None:
        sections = _wiki_api(f"action=parse&prop=sections&page={page}")["parse"]["sections"]
        sec = next(s["index"] for s in sections if re.search(r"\b(table|standings)\b", s["line"], re.I))
        text = section(sec)
        groups = parse_wiki(text, sport, names)
    season = title.split()[0].replace("–", "/")
    rows = [r for g in groups for r in g["rows"]]
    known_rows = [r for g in prev.get("groups") or [] for r in g.get("rows") or []]
    # Eyni mövsümdə ikidən çox yeni ad gəlibsə kimsə cədvəli pozub: əvvəlki qalır.
    if prev.get("season") == season and known_rows and len({r["full"] for r in rows} - {r.get("full") or r.get("team") for r in known_rows}) > 2:
        raise ValueError("komanda adları dəyişib")
    logos = {r.get("full") or r.get("team"): r.get("logo") for r in known_rows if "espncdn" not in (r.get("logo") or "")}
    for r in rows:
        r["logo"] = logos.get(r["full"]) or ""
    missing = [r["_page"] for r in rows if not r["logo"]]
    if missing:
        try:
            found = _wiki_logos(missing)
            for r in rows:
                r["logo"] = r["logo"] or found.get(r["_page"], "")
        except Exception as e:
            print(f"  ! {name} loqoları:", type(e).__name__)
    for r in rows:
        del r["_page"]
        if r["team"] == r["full"]:
            del r["full"]
    league = {"id": lid, "sport": sport, "name": name, "short": short, "season": season, "groups": groups, "sec": sec,
              "at": now_dt.isoformat(timespec="seconds"), "url": "https://en.wikipedia.org/wiki/" + urllib.parse.quote(title.replace(" ", "_"))}
    asof = wiki_asof(text)
    if asof:
        league["asof"] = asof
    return league

def update_sports():
    """Dünya liqalarının cədvəlləri (Vikipediya). 15 dəqiqədən bir; alınmayan liqanın əvvəlki cədvəli qalır, 3 saatdan sonra «köhnə» sayılır."""
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
    started, done = time.monotonic(), {}
    for spec in sorted(WIKI_LEAGUES, key=lambda s: old_by.get(s[0], {}).get("at", "")):
        if time.monotonic() - started > SPORTS_BUDGET_S:
            break
        try:
            done[spec[0]] = _wiki_league(spec, old_by.get(spec[0]) or {}, now_dt)
        except Exception as e:
            print(f"  ! {spec[2]}:", type(e).__name__, str(e)[:60])
    leagues = []
    for spec in WIKI_LEAGUES:
        league = done.get(spec[0]) or old_by.get(spec[0])
        if not league:
            continue
        try:
            late = now_dt - datetime.datetime.fromisoformat(league.get("at", "")) > SPORTS_STALE
        except Exception:
            late = True
        leagues.append({k: v for k, v in league.items() if k != "stale"} | ({"stale": True} if late else {}))
    _write_atomic(SPORTS_FILE, json.dumps({"updatedAt": now_dt.isoformat(timespec="seconds"), "source": "Vikipediya", "leagues": leagues},
                                      ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    print(f"Dünya liqaları: {len(done)}/{len(WIKI_LEAGUES)} təzə")

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

# Komanda səhifələri (#/komanda/<liga>/<ad>). Məlumat ayrı fayllardadır (data/futbol/), yalnız o səhifə açılanda yüklənir və
# yalnız slow_cycle-da yazılır: baş səhifəyə də, 60 saniyəlik dövrəyə də ağırlıq gətirmir.
# Dünya liqalarının cədvəli sports.json-dan, Bundesliqa və Çempionlar Liqasının oyunları OpenLigaDB-dən (aşağıda). ESPN bizi 403 ilə rədd edir, blok yan keçilmir.
# Heyət yoxdur: pfl.az-ın /clubs cavabında «players» bütün klublarda boşdur, bəzilərində yalnız PDF var (2026-11-01).
TEAM_DIR = OUT_DIR / "futbol"
TEAM_EVERY = datetime.timedelta(minutes=30)
TEAM_EVERY_LIVE = datetime.timedelta(minutes=10)  # oyun gedəndə nəticə tez çatsın
TEAM_LIVE_WINDOW = datetime.timedelta(hours=3)
TEAM_BUDGET_S = 25         # bir yavaş dövrədə bu addıma ayrılan vaxt; çatmayan liqa növbəti dövrəyə qalır
TEAM_PAST_SEASONS = 2      # cari mövsümdən əvvəlki mövsümlər: bir dəfə yazılır, bir daha dəyişmir
TEAM_PAST_PER_CYCLE = 1

class _NoTeamData(Exception):
    """Bu mövsümdə həmin yarış yoxdur (şəbəkə xətası deyil)."""

def team_slug(name):
    """Komanda və liqa ünvanı. app.js-dəki teamSlug ilə eyni nəticə verir (hər iki test eyni nümunələri yoxlayır)."""
    s = unicodedata.normalize("NFD", str(name or "").lower())
    s = "".join(c for c in s if not unicodedata.combining(c)).replace("ə", "e").replace("ı", "i")
    return re.sub(r"[\W_]+", "-", s).strip("-")

def _team_sources():
    return [{"id": team_slug(short), "project": project, "short": short, "reserve": short == "Əvəzedicilər"} for project, short in PFL_PROJECTS]

def _team_season_label(year):
    return f"{year}-{(year + 1) % 100:02d}"

def parse_pfl_team_league(season, grid, tours):
    """pfl.az cavabları -> (komandalar, qruplar, oyunlar). Cədvəlin sırası parse_pfl-dəndir, oyunlar bütün turlardandır."""
    table = parse_pfl({"data": [season]}, grid, tours, {})["table"]
    teams, rows = {}, []
    for row in table:
        slug = team_slug(row["team"])
        teams[slug] = {"name": row["team"], "logo": row["logo"]}
        row = dict(row, team=slug)
        row.pop("logo", None)
        rows.append(row)
    games = []
    for tour in tours.get("data") or []:
        for g in tour.get("games") or []:
            game = _pfl_game(g)
            if not game["home"] or not game["away"]:
                continue  # püşk hələ atılmayıb
            for side, club in (("home", g.get("club_1") or {}), ("away", g.get("club_2") or {})):
                slug = team_slug(game[side])
                teams.setdefault(slug, {"name": game[side], "logo": club.get("logo") or ""})
                game[side] = slug
            if not game["played"]:
                game.pop("hs")
                game.pop("as")
            if not game["stadium"]:
                game.pop("stadium")
            game["round"] = str(tour.get("title") or "")
            games.append(game)
    games.sort(key=lambda g: g["date"] or "9999")
    return teams, ([{"name": "", "rows": rows}] if rows else []), games

def _team_league(spec, key=None):
    """(sənəd, mövsümlər). pfl.az mövsümləri ən yenisi birinci verir."""
    rows = [s for s in _pfl_json(f"/seasons?project_id={spec['project']}").get("data") or [] if (s.get("leagues") or [{}])[0].get("id")]
    rows = rows[:TEAM_PAST_SEASONS + 1]
    year = lambda s: str(s.get("title") or "")[:4]
    seasons = [{"key": year(s), "label": _team_season_label(_num(year(s)))} for s in rows]
    season = next((s for s in rows if year(s) == key), None) if key else (rows[0] if rows else None)
    if season is None:
        raise _NoTeamData("mövsüm yoxdur")
    league = season["leagues"][0]
    grid = {} if league.get("is_elimination") else _pfl_json(f"/leagues/grid?season_id={season.get('id')}&project_id={spec['project']}")
    tours = _pfl_json(f"/tours/get-games?league_id={league.get('id')}&withGames=true")
    teams, groups, games = parse_pfl_team_league(season, grid, tours)
    if not groups and not games:
        raise _NoTeamData("məlumat boşdur")
    doc = {"id": spec["id"], "name": league.get("title") or spec["short"], "short": spec["short"], "source": "pfl.az",
           "key": year(season), "season": _team_season_label(_num(year(season))), "teams": teams, "groups": groups, "games": games}
    return doc, seasons

def _write_if_changed(path, doc):
    """Məlumat dəyişməyibsə fayla toxunulmur: main-ə lazımsız commit getmir."""
    text = json.dumps(doc, ensure_ascii=False, separators=(",", ":"))
    try:
        if path.read_text(encoding="utf-8") == text:
            return False
    except OSError:
        pass
    _write_atomic(path, text)
    return True

TEAM_GROUP_AZ = {"Eastern Conference": "Şərq konfransı", "Western Conference": "Qərb konfransı"}

def team_world_league(league):
    """Dünya liqasının cədvəli (sports.json) -> komanda faylı. Şəbəkə yoxdur. Bu mənbədə oyun təqvimi yoxdur, «games» boşdur."""
    teams, groups = {}, []
    for group in league.get("groups") or []:
        rows = []
        for row in group.get("rows") or []:
            name = row.get("full") or row.get("team") or ""
            slug = team_slug(name)
            teams[slug] = {"name": name, "logo": row.get("logo") or ""}
            if row.get("team") != name:
                teams[slug]["short"] = row.get("team")
            rows.append(dict({k: v for k, v in row.items() if k not in ("full", "logo")}, team=slug))
        groups.append({"name": TEAM_GROUP_AZ.get(group.get("name"), group.get("name") or ""), "rows": rows})
    season = league.get("season") or ""
    return {"id": team_slug(league.get("short")), "name": league.get("name") or "", "short": league.get("short") or "", "source": "Vikipediya", "url": league.get("url") or "",
            "sport": league.get("sport") or "football", "asof": league.get("asof") or "", "key": season[:4], "season": season, "teams": teams, "groups": groups, "games": []}

def _team_when(s):
    try:
        t = datetime.datetime.fromisoformat(str(s))
    except ValueError:
        return None
    return t if t.tzinfo else None

def _team_due(doc, checked, now_dt, every=TEAM_EVERY, live_every=TEAM_EVERY_LIVE, window=TEAM_LIVE_WINDOW):
    last = _team_when(checked)
    if last is None or now_dt - last >= every:
        return True
    if now_dt - last < live_every:
        return False
    for g in doc.get("games") or []:
        kick = _team_when(g.get("date"))
        if kick and not g.get("played") and kick <= now_dt <= kick + window:
            return True
    return False

# OpenLigaDB: Bundesliqa və Çempionlar Liqasının oyunları. Məlumat ODbL 1.0-dır, açar lazım deyil. Şərtləri (openligadb.de/lizenz, /nutzungsbedingungen, 2026-11-01-də oxunub):
# - mənbə səhifədə göstərilir (doc["source"]); TeamIconUrl və gerblər lisenziyaya daxil deyil, ona görə götürülmür;
# - sakit vaxtda gündə bir neçə sorğu, oyun gedəndə əvvəl ucuz getlastchangedate, 429/5xx-də artan gözləmə, tanınan User-Agent;
# - bu addım yavaş dövrənin sonundadır, başlama vaxtı onsuz da tam dəqiqəyə düşmür.
# Canlı hesab göstərilmir: mənbənin özü oyun gedəndə gecikmə və səhvin olduğunu yazır. Nəticə oyun bitəndən sonra çıxır.
OPENLIGA_API = "https://api.openligadb.de"
OPENLIGA_UA = "8ulduz.az/1.0 (+https://8ulduz.az; https://github.com/8ulduz/8ulduz/issues)"
OPENLIGA_SOURCE = {"source": "OpenLigaDB (www.openligadb.de), ODbL 1.0 lisenziyası", "source_url": "https://www.openligadb.de/"}
OPENLIGA_DUE = {"every": datetime.timedelta(hours=6), "live_every": datetime.timedelta(0), "window": datetime.timedelta(hours=4)}
OPENLIGA_WAIT = datetime.timedelta(minutes=10)
OPENLIGA_WAIT_MAX = datetime.timedelta(hours=6)
_OPENLIGA_LEAGUES = {"almaniya": "bl1", "cl": "ucl"}  # team_world_league-in id-si -> OpenLigaDB qısaltması
# OpenLigaDB teamId -> (sports.json-dakı ad, heyət üçün Vikipediya səhifəsi). Ünvan bu addan gəlir, cədvəlin klubu ilə eyni olur; Sabah həm Premyer Liqada, həm ÇL-dədir.
# Siyahıda olmayan komanda mənbənin adı ilə görünür, heyəti olmur. Eyni klubun mövsümlərə görə id-si fərqli ola bilər (Atlético, PSG, Napoli, Villarreal).
_OPENLIGA_CLUBS = {
    40: ("Bayern Munich", "FC Bayern Munich"), 16: ("VfB Stuttgart", "VfB Stuttgart"), 1635: ("RB Leipzig", "RB Leipzig"), 87: ("Borussia Mönchengladbach", "Borussia Mönchengladbach"),
    81: ("Mainz 05", "1. FSV Mainz 05"), 31: ("SC Paderborn", "SC Paderborn 07"), 80: ("Union Berlin", "1. FC Union Berlin"), 91: ("Eintracht Frankfurt", "Eintracht Frankfurt"),
    65: ("1. FC Köln", "1. FC Köln"), 175: ("TSG Hoffenheim", "TSG 1899 Hoffenheim"), 198: ("SV Elversberg", "SV Elversberg"), 6: ("Bayer Leverkusen", "Bayer 04 Leverkusen"),
    7: ("Borussia Dortmund", "Borussia Dortmund"), 100: ("Hamburger SV", "Hamburger SV"), 112: ("SC Freiburg", "SC Freiburg"), 134: ("Werder Bremen", "SV Werder Bremen"),
    95: ("FC Augsburg", "FC Augsburg"), 9: ("Schalke 04", "FC Schalke 04"), 1210: ("Club Brugge", "Club Brugge KV"), 438: ("Aston Villa", "Aston Villa F.C."),
    1217: ("AEK Athens", "AEK Athens F.C."), 5139: ("LASK", "LASK"), 1133: ("Real Madrid", "Real Madrid CF"), 733: ("Inter Milan", "Inter Milan"), 375: ("Porto", "FC Porto"),
    4244: ("Manchester City", "Manchester City F.C."), 382: ("Villarreal", "Villarreal CF"), 4200: ("Villarreal", "Villarreal CF"), 1204: ("Lille", "Lille OSC"), 1804: ("Real Betis", "Real Betis"),
    356: ("Barcelona", "FC Barcelona"), 1770: ("Feyenoord", "Feyenoord"), 1484: ("Viking", "Viking FK"), 370: ("Liverpool", "Liverpool F.C."), 4241: ("Atlético Madrid", "Atlético Madrid"),
    2549: ("Atlético Madrid", "Atlético Madrid"), 2281: ("Paris Saint-Germain", "Paris Saint-Germain F.C."), 4363: ("Paris Saint-Germain", "Paris Saint-Germain F.C."),
    5699: ("Slovan Bratislava", "ŠK Slovan Bratislava"), 2331: ("Napoli", "SSC Napoli"), 1160: ("Napoli", "SSC Napoli"), 2617: ("Arsenal", "Arsenal F.C."), 1205: ("Sporting CP", "Sporting CP"),
    2554: ("Galatasaray", "Galatasaray S.K. (football)"), 376: ("PSV Eindhoven", "PSV Eindhoven"), 1186: ("Shakhtar Donetsk", "FC Shakhtar Donetsk"), 366: ("Fenerbahçe", "Fenerbahçe S.K. (football)"),
    378: ("Roma", "AS Roma"), 5707: ("Bodø/Glimt", "FK Bodø/Glimt"), 2556: ("Manchester United", "Manchester United F.C."), 8798: ("Sabah", ""), 8787: ("Como", "Como 1907"),
    4578: ("Slavia Prague", "SK Slavia Prague"), 5962: ("Lens", "RC Lens"),
    # Yalnız keçmiş mövsümlərdə olanlar: adları almanca görünməsin.
    4458: ("Qarabağ", ""), 1135: ("Athletic Bilbao", ""), 4825: ("Union Saint-Gilloise", ""), 2557: ("Marseille", ""), 369: ("Juventus", ""), 1179: ("Benfica", ""), 2559: ("Tottenham Hotspur", ""),
    436: ("Olympiacos", ""), 7081: ("Pafos", ""), 364: ("Chelsea", ""), 455: ("Ajax", ""), 1807: ("Atalanta", ""), 453: ("Copenhagen", ""), 2547: ("Monaco", ""), 1075: ("Newcastle United", ""),
    7082: ("Kairat", ""), 199: ("1. FC Heidenheim", ""), 131: ("VfL Wolfsburg", ""), 98: ("FC St. Pauli", ""),
}
_OPENLIGA_ROUNDS = (("Achtelfinale", "1/8 final"), ("Viertelfinale", "1/4 final"), ("Halbfinale", "Yarımfinal"), ("Finale", "Final"), ("Playoffs", "Pley-off"))

def _openliga_json(path):
    return json.loads(fetch(f"{OPENLIGA_API}/{path}", timeout=15, headers={"User-Agent": OPENLIGA_UA, "Accept": "application/json"}).decode("utf-8"))

def _openliga_round(group):
    """Tur nömrəsi və ya pley-off mərhələsi. Tanınmayan almanca ad sayta çıxmır."""
    name = str(group.get("groupName") or "")
    if "Spieltag" in name:
        return str(group.get("groupOrderID") or "")
    for german, az in _OPENLIGA_ROUNDS:
        if german in name:
            return az + (", 1-ci oyun" if "Hinspiel" in name else ", cavab oyunu" if "Rückspiel" in name else "")
    return ""

def _openliga_score(match):
    """(ev, qonaq, penalti) və ya None. Bitməyən oyunun hesabı götürülmür."""
    results = {r.get("resultTypeKind"): r for r in match.get("matchResults") or []}
    end = results.get("AfterExtraTime") or results.get("After90Minutes")
    if not match.get("matchIsFinished") or not end:
        return None
    pen = results.get("AfterPenalties")
    return end.get("pointsTeam1"), end.get("pointsTeam2"), f"{pen.get('pointsTeam1')}:{pen.get('pointsTeam2')}" if pen else ""

def parse_openliga(matches):
    """OpenLigaDB getmatchdata -> (komandalar, oyunlar). Loqo götürülmür: lisenziyaya daxil deyil."""
    teams, games = {}, []
    for m in matches:
        sides = []
        for team in (m.get("team1") or {}, m.get("team2") or {}):
            name = _OPENLIGA_CLUBS.get(team.get("teamId"), (str(team.get("teamName") or "").strip(),))[0]
            slug = team_slug(name)
            if slug:
                teams[slug] = {"name": name, "logo": ""}
                sides.append(slug)
        if len(sides) < 2:
            continue  # püşk hələ atılmayıb
        group = m.get("group") or {}
        game = {"date": str(m.get("matchDateTimeUTC") or "").replace("Z", "+00:00"), "home": sides[0], "away": sides[1], "played": False,
                "round": _openliga_round(group), "g": group.get("groupOrderID")}
        score = _openliga_score(m)
        if score:
            game.update(played=True, hs=score[0], **{"as": score[1]})
            if score[2]:
                game["pen"] = score[2]
        games.append(game)
    games.sort(key=lambda g: g["date"] or "9999")
    return teams, games

def openliga_table(teams, games):
    """Turnir cədvəli liqa turlarının oyunlarından (pley-off sayılmır). Sıra: xal, qol fərqi, vurulan qol, səfərdə vurulan qol, qələbə, səfər qələbəsi, ad."""
    rows, away = {}, collections.defaultdict(lambda: [0, 0])
    for g in games:
        if not g["round"].isdigit():
            continue
        for side in (g["home"], g["away"]):
            rows.setdefault(side, {"team": side, "p": 0, "w": 0, "d": 0, "l": 0, "gf": 0, "ga": 0, "gd": 0, "pts": 0})
        if not g["played"]:
            continue
        for side, mine, other in ((g["home"], g["hs"], g["as"]), (g["away"], g["as"], g["hs"])):
            row = rows[side]
            won = "w" if mine > other else "l" if mine < other else "d"
            row["p"] += 1
            row[won] += 1
            row["gf"] += mine
            row["ga"] += other
            row["gd"] += mine - other
            row["pts"] += {"w": 3, "d": 1, "l": 0}[won]
        away[g["away"]][0] += g["as"]
        away[g["away"]][1] += g["as"] > g["hs"]
    ordered = sorted(rows.values(), key=lambda r: (-r["pts"], -r["gd"], -r["gf"], -away[r["team"]][0], -r["w"], -away[r["team"]][1], teams.get(r["team"], {}).get("name", r["team"])))
    for pos, row in enumerate(ordered, 1):
        row["pos"] = pos
    return ordered

# Dünya liqalarının oyunları: TheSportsDB-nin açıq API-si, tur-tur (eventsround). Açıq açar 123, hesab tələb etmir. Sənədinə görə dəqiqədə 30 sorğu,
# amma ölçüdə (2026-11-01) təxminən 10 sorğudan sonra 429 qaytarır, ona görə dövrədə az soruşulur, 429-da dayanılır. Bütün mövsüm təxminən bir neçə saata dolur.
TSDB_API = "https://www.thesportsdb.com/api/v1/json/123/eventsround.php"
TSDB_SOURCE = {"source": "TheSportsDB", "source_url": "https://www.thesportsdb.com/"}
# team_world_league-in id-si -> (TheSportsDB liqası, turlar). Kuboklarda liqa mərhələsi: pley-off turlarının nömrəsi başlayanda yoxlanmalıdır.
TSDB_LEAGUES = {"ingiltere": (4328, 38), "ispaniya": (4335, 38), "italiya": (4332, 38), "fransa": (4334, 34), "turkiye": (4339, 34), "portuqaliya": (4344, 34), "hollandiya": (4337, 34),
                "belcika": (4338, 30), "sotlandiya": (4330, 38), "rusiya": (4355, 30), "seudiyye": (4668, 34), "braziliya": (4351, 38), "abs": (4346, 34), "cempionsip": (4329, 46),
                "al": (4481, 8), "kl": (5071, 6), "avroliqa": (4546, 38)}
# Kuboklarda seçmə mərhələsinin oyunları eyni tur nömrələrindədir: cədvələ yalnız liqa mərhələsi düşür.
TSDB_SINCE = {"al": "09-01", "kl": "09-01"}
TSDB_PER_CYCLE = 5
TSDB_GAP_S = 2.5
TSDB_BACKOFF = datetime.timedelta(minutes=15)
TSDB_WAITING = datetime.timedelta(minutes=30)  # vaxtı keçib nəticəsi gəlməyən tur
TSDB_SOON = datetime.timedelta(hours=6)        # yaxın 7 gündəki tur: saat dəyişə bilər
TSDB_LATER = datetime.timedelta(days=7)        # uzaq və ya boş tur
TSDB_ALIAS = {"Hamburg": "Hamburger SV", "Amed": "Amedspor"}
_TSDB_STOP = set("fc cf sc ac afc sk fk kv cd ud sv rc rcd ssc us as club bc kk bk jk fsv vfb tsg de of the and 1 04 05 96 1899 sad".split())

def _tsdb_words(name):
    s = "".join(c for c in unicodedata.normalize("NFD", str(name or "").lower()) if not unicodedata.combining(c)).replace("ı", "i").replace("ə", "e")
    return {w for w in re.split(r"[\W_]+", s) if w and w not in _TSDB_STOP}

def tsdb_team(name, teams):
    """TheSportsDB adı -> cədvəldəki klubun ünvanı. Bir mənalı deyilsə None: başqa klubun oyunu göstərilməsin."""
    words = _tsdb_words(TSDB_ALIAS.get(name, name))
    known = {slug: _tsdb_words(t.get("name")) for slug, t in teams.items()}
    for test in (lambda k: k == words, lambda k: words and (words <= k or k <= words), lambda k: words & k):
        hits = [slug for slug, k in known.items() if test(k)]
        if hits:
            return hits[0] if len(hits) == 1 else None
    return None

def tsdb_games(events, teams, since=""):
    """eventsround -> saytın oyun sətirləri. Klubu tanınmayan oyun yazılmır."""
    games = []
    for e in events or []:
        if since and str(e.get("strTimestamp") or "")[:10] < since:
            continue
        home, away = tsdb_team(e.get("strHomeTeam"), teams), tsdb_team(e.get("strAwayTeam"), teams)
        if not home or not away or home == away:
            print("  ! oyun: tanınmayan klub", str(e.get("strEvent"))[:50])
            continue
        stamp = str(e.get("strTimestamp") or "")
        game = {"date": f"{stamp[:19]}+00:00" if stamp else "", "home": home, "away": away, "played": False, "round": str(e.get("intRound") or "")}
        if e.get("strVenue"):
            game["stadium"] = str(e["strVenue"])[:60]
        status = str(e.get("strStatus") or "").upper()
        if e.get("intHomeScore") not in (None, "") and e.get("intAwayScore") not in (None, "") and status in ("FT", "AET", "PEN", "MATCH FINISHED", "AOT"):
            game.update(played=True, hs=int(e["intHomeScore"]), **{"as": int(e["intAwayScore"])})
        elif status in ("PST", "POST", "CANC", "ABD", "MATCH POSTPONED", "POSTPONED", "CANCELLED"):
            game["state"] = "off"
        games.append(game)
    return games

def _tsdb_round_due(games, stamp, now_dt):
    """Tur nə vaxt yenidən soruşulsun. Bitmiş tur bir daha soruşulmur: dəyişməyən məlumata sorğu getmir."""
    asked = _team_when(stamp)
    if not asked:
        return True
    if not games:
        return now_dt - asked >= TSDB_LATER
    open_games = [g for g in games if not g.get("played") and g.get("state") != "off"]
    if not open_games:
        return now_dt - asked >= TSDB_LATER if any(g.get("state") == "off" for g in games) else False
    kicks = [k for k in (_team_when(g.get("date")) for g in open_games) if k]
    if any(k <= now_dt for k in kicks):
        return now_dt - asked >= TSDB_WAITING
    if any(k - now_dt <= datetime.timedelta(days=7) for k in kicks):
        return now_dt - asked >= TSDB_SOON
    return now_dt - asked >= TSDB_LATER

def _tsdb_plan(docs, stamps, now_dt):
    """Bu dövrə soruşulacaq turlar: əvvəl heç soruşulmamış, oyun gedən tura ən yaxın olan; sonra ən çoxdan gözləyən."""
    plan = []
    for doc in docs:
        spec = TSDB_LEAGUES.get(doc["id"])
        if not spec:
            continue
        mine = stamps.get(doc["id"], {}) if stamps.get(doc["id"], {}).get("season") == doc["key"] else {}
        by_round = collections.defaultdict(list)
        for g in doc.get("games") or []:
            by_round[g.get("round")].append(g)
        played = [int(r) for r, rows in by_round.items() if r.isdigit() and any(g.get("played") for g in rows)]
        now_round = max(played) + 1 if played else (doc["groups"][0]["rows"] or [{}])[0].get("p") or 1
        for r in range(1, spec[1] + 1):
            stamp = (mine.get("rounds") or {}).get(str(r))
            if _tsdb_round_due(by_round.get(str(r)) or [], stamp, now_dt):
                plan.append((0 if not stamp else 1, abs(r - now_round) if not stamp else 0, stamp or "", doc["id"], r))
    plan.sort()
    return plan

def tsdb_refresh(docs, stamps, now_dt, out_of_time, sleep=time.sleep):
    """Bu dövrənin sorğuları. Nəticə: {liqa: {tur: oyunlar}}. 429-da qalan sorğular göndərilmir. Xəbər axınına toxunmur: yavaş dövrənin son addımıdır."""
    fresh = collections.defaultdict(dict)
    if (_team_when(stamps.get("until")) or now_dt) > now_dt:
        return fresh
    by_id = {d["id"]: d for d in docs}
    for i, (_new, _near, _stamp, lid, r) in enumerate(_tsdb_plan(docs, stamps, now_dt)[:TSDB_PER_CYCLE]):
        if out_of_time():
            break
        if i:
            sleep(TSDB_GAP_S)
        doc = by_id[lid]
        season = doc["season"].replace("/", "-20") if "/" in doc["season"] else doc["season"]
        url = TSDB_API + "?" + urllib.parse.urlencode({"id": TSDB_LEAGUES[lid][0], "r": r, "s": season})
        try:
            body = fetch(url, timeout=12, headers={"User-Agent": WIKI_UA, "Accept": "application/json"})
        except urllib.error.HTTPError as e:
            if e.code == 429:
                stamps["until"] = (now_dt + TSDB_BACKOFF).isoformat(timespec="seconds")
                print("  ! oyunlar: 429, 15 dəqiqə sorğu yoxdur")
                break
            print(f"  ! oyunlar {lid} {r}:", e.code)
            continue
        except Exception as e:
            print(f"  ! oyunlar {lid} {r}:", type(e).__name__)
            continue
        try:
            events = (json.loads(body) if body.strip() else {}).get("events") or []
        except ValueError:
            print(f"  ! oyunlar {lid} {r}: JSON deyil")
            continue
        mine = stamps.setdefault(lid, {})
        if mine.get("season") != doc["key"]:
            mine.clear()
            mine["season"] = doc["key"]
        mine.setdefault("rounds", {})[str(r)] = now_dt.isoformat(timespec="seconds")
        fresh[lid][str(r)] = tsdb_games(events, doc["teams"], f"{doc['key']}-{TSDB_SINCE[lid]}" if lid in TSDB_SINCE else "")
    return fresh

def tsdb_merge(old, fresh):
    """Təzə soruşulan turlar köhnəsini əvəz edir, qalan turlar yerində qalır."""
    return sorted([g for g in old or [] if str(g.get("round")) not in fresh] + [g for rows in fresh.values() for g in rows], key=lambda g: g.get("date") or "9999")

# NBA: açıq oyun API-si tapılmadı (cdn.nba.com serverdən 403, TheSportsDB gündə 3 oyun verir). Vikipediyada hər komandanın mövsüm səhifəsində 82 oyun var:
# tarix, rəqib, hesab. Saatı yoxdur, ona görə sətirdə «day» işarəsi var və saytda yalnız tarix görünür.
NBA_TEAMS_PER_CYCLE = 5
NBA_EVERY = datetime.timedelta(hours=2)
_NBA_MONTHS = {m: i for i, m in enumerate(_WIKI_MONTHS, 1)}

def nba_team_games(text, me, teams, start_year):
    """Komandanın mövsüm səhifəsinin «Game log» bölməsi -> oyunlar. Hazırlıq oyunları sayılmır. Rəqibi tanınmayan sətir yazılmır."""
    games = []
    for table in re.findall(r"<table\b.*?</table>", text, re.S):
        rows = re.findall(r"<tr\b.*?</tr>", table, re.S)
        if not rows or "preseason" in _wiki_text(rows[0]).lower():
            continue
        for tr in rows:
            cells = [_wiki_text(c) for c in re.findall(r"<t[dh]\b[^>]*>(.*?)</t[dh]>", tr, re.S)]
            if len(cells) < 4 or not cells[0].isdigit():
                continue
            day = re.fullmatch(r"(\w+) (\d{1,2})", cells[1])
            if not day or day.group(1) not in _NBA_MONTHS:
                continue
            away = cells[2].startswith("@")
            other = tsdb_team(cells[2].lstrip("@ ").strip(), teams)
            if not other or other == me:
                continue
            month = _NBA_MONTHS[day.group(1)]
            game = {"date": f"{start_year + (month < 7)}-{month:02d}-{int(day.group(2)):02d}T12:00:00+00:00", "day": True,
                    "home": other if away else me, "away": me if away else other, "played": False, "round": ""}
            score = re.match(r"[WL] (\d+)-(\d+)", cells[3])
            if score:
                mine, theirs = int(score.group(1)), int(score.group(2))
                game.update(played=True, hs=theirs if away else mine, **{"as": mine if away else theirs})
            games.append(game)
    return games

def nba_refresh(doc, stamps, now_dt, out_of_time):
    """Dövrədə bir neçə komanda. Nəticə: {komanda: oyunlar}."""
    mine = stamps.setdefault(doc["id"], {})
    if mine.get("season") != doc["key"]:
        mine.clear()
        mine["season"] = doc["key"]
    asked = mine.setdefault("teams", {})
    order = sorted(doc["teams"], key=lambda slug: asked.get(slug, ""))
    fresh = {}
    for slug in order[:NBA_TEAMS_PER_CYCLE]:
        last = _team_when(asked.get(slug))
        if out_of_time() or (last and now_dt - last < NBA_EVERY):
            break
        asked[slug] = now_dt.isoformat(timespec="seconds")
        page = urllib.parse.quote(_wiki_title("{s} " + doc["teams"][slug]["name"] + " season", now_dt))
        try:
            sections = _wiki_api(f"action=parse&prop=sections&page={page}")["parse"]["sections"]
            sec = next(s["index"] for s in sections if s["line"].lower() == "game log")
            fresh[slug] = nba_team_games(_wiki_api(f"action=parse&prop=text&page={page}&section={sec}")["parse"]["text"], slug, doc["teams"], int(doc["key"]))
        except Exception as e:
            print(f"  ! NBA {slug}:", type(e).__name__)
    return fresh

def nba_merge(old, fresh):
    """Hər oyun iki səhifədə olur. Təzə sətirlər köhnəni əvəz edir; hesabı olan sətir hesabsızdan üstündür."""
    games = {(g["date"][:10], g["home"], g["away"]): g for g in old or [] if not {g["home"], g["away"]} & set(fresh)}
    for rows in fresh.values():
        for g in rows:
            key = (g["date"][:10], g["home"], g["away"])
            if g["played"] or key not in games:
                games[key] = g
    return sorted(games.values(), key=lambda g: g["date"])

def team_world_with_games(doc, teams, games, source=None):
    """sports.json sənədinə oyunlar. Cədvəl Vikipediyadan qalır; OpenLigaDB-də daha çox oyun varsa və klublar üst-üstə düşürsə oyunlardan
    hesablanır, zona qeydləri yerin yanında qalır. Beləcə tur bitəndə nəticə ilə cədvəl bir-birini danmır."""
    merged = dict(doc, **(source or OPENLIGA_SOURCE), teams={**teams, **doc["teams"]}, games=games)
    rows = doc["groups"][0]["rows"] if len(doc["groups"]) == 1 and doc.get("sport") != "basketball" else []
    table = openliga_table(merged["teams"], games)
    if {r["team"] for r in table} == {r["team"] for r in rows} and sum(r["p"] for r in table) > sum(r.get("p", 0) for r in rows):
        zones = {r.get("pos"): {k: r[k] for k in ("note", "color") if k in r} for r in rows}
        merged["groups"] = [{"name": doc["groups"][0].get("name") or "", "rows": [dict(r, **zones.get(r["pos"], {})) for r in table]}]
        merged["asof"] = max(g["date"][:10] for g in games if g["played"])
    return merged

def _openliga_stamps(shortcut, key, games, now_dt):
    """Oyun gedən turların son dəyişmə vaxtı: dəyişməyibsə tam siyahı istənmir (mənbənin xahişi)."""
    groups = set()
    for g in games:
        kick = _team_when(g.get("date"))
        if kick and g.get("g") and not g.get("played") and kick <= now_dt <= kick + OPENLIGA_DUE["window"]:
            groups.add(g["g"])
    return {str(g): _openliga_json(f"getlastchangedate/{shortcut}/{key}/{g}") for g in sorted(groups)}

def _openliga_refresh(shortcut, key, current, mine, now_dt):
    """(komandalar, oyunlar) və ya None (faylda olan qalır). mine: bu liqanın yoxlama vəziyyəti, index.json-da saxlanır."""
    games = current.get("games") or []
    if (_team_when(mine.get("until")) or now_dt) > now_dt or not _team_due({"games": games}, mine.get("checked"), now_dt, **OPENLIGA_DUE):
        return None
    last = _team_when(mine.get("checked"))
    mine["checked"] = now_dt.isoformat(timespec="seconds")
    try:
        # Oyun gedəndə yoxlama tez-tez olur: əvvəl turun son dəyişmə vaxtı, tam siyahı yalnız dəyişibsə.
        seen = _openliga_stamps(shortcut, key, games, now_dt) if games and last and now_dt - last < OPENLIGA_DUE["every"] else {}
        if seen and seen == mine.get("changed"):
            return None
        matches = _openliga_json(f"getmatchdata/{shortcut}/{key}")
    except Exception as e:
        print(f"  ! OpenLigaDB {shortcut}:", type(e).__name__)
        tries = mine.get("n", 0)
        mine.update(n=tries + 1, until=(now_dt + min(OPENLIGA_WAIT * 2 ** tries, OPENLIGA_WAIT_MAX)).isoformat(timespec="seconds"))
        return None
    mine.pop("n", None)
    mine.pop("until", None)
    mine["changed"] = seen
    return parse_openliga(matches) if matches else None

def _openliga_past(doc, shortcut, key):
    """Keçmiş mövsümün faylı. Mənbədə həmin mövsüm yoxdursa _NoTeamData."""
    matches = _openliga_json(f"getmatchdata/{shortcut}/{key}")
    if not matches:
        raise _NoTeamData("məlumat boşdur")
    teams, games = parse_openliga(matches)
    return {"id": doc["id"], "name": doc["name"], "short": doc["short"], "sport": doc.get("sport") or "football", **OPENLIGA_SOURCE, "key": key,
            "season": f"{key}/{(int(key) + 1) % 100:02d}", "teams": teams, "groups": [{"name": "", "rows": openliga_table(teams, games)}], "games": games}

# Heyət: ingilis Vikipediyası (CC BY-SA 4.0, səhifədə keçidlə göstərilir). Yalnız əsas heyət bloku: icarədəkilər və gənclər ayrı başlıqdadır.
# Sayı ağlabatan deyilsə yazılmır: şübhəli siyahıdansa tabın olmaması yaxşıdır. Azərbaycan klublarının Vikipediya keçidi yoxdur.
WIKI_SQUAD_EVERY = datetime.timedelta(days=7)
WIKI_SQUAD_RETRY = datetime.timedelta(days=1)
WIKI_SQUADS_PER_CYCLE = 4
WIKI_SQUAD_SIZE = (15, 45)
_WIKI_SQUAD_HEAD = re.compile(r"^(={2,4})\s*([^=\n]*?)\s*\1\s*$", re.M)
_WIKI_SQUAD_ROW = re.compile(r"\{\{\s*(?:fs|fs2|football squad)\s*player\s*\|(.*?)\}\}(?:\s*\n|\s*(?=\{\{)|$)", re.I | re.S)

def _wiki_cell(value):
    value = re.sub(r"<ref.*?(?:</ref>|/>)", "", value, flags=re.S)
    value = re.sub(r"\[\[(?:[^\]|]*\|)?([^\]]*)\]\]", r"\1", value)
    return re.sub(r"\{\{[^{}]*\}\}", "", value).strip()

def parse_wiki_squad(text):
    """Klub səhifəsinin wikitext-i -> [{no, pos, name}]. Əsas heyət tapılmayanda və ya sayı ağlabatan olmayanda boş siyahı."""
    heads = list(_WIKI_SQUAD_HEAD.finditer(text))
    for i, head in enumerate(heads):
        if not re.search(r"current squad|first[- ]team squad|^squad$|^players$|^first team$", head.group(2), re.I):
            continue
        block = text[head.end():heads[i + 1].start() if i + 1 < len(heads) else len(text)]
        block = re.split(r"\{\{\s*(?:fs|football squad)\s*end", block, maxsplit=1, flags=re.I)[0]  # ikinci cədvəl adətən icarədəkilərdir
        rows = []
        for m in _WIKI_SQUAD_ROW.finditer(block):
            cells = {}
            for part in re.split(r"\|(?![^\[\{]*[\]\}])", m.group(1)):
                if "=" in part:
                    name, value = part.split("=", 1)
                    cells[name.strip().lower()] = value.strip()
            name, pos = _wiki_cell(cells.get("name", "")), _wiki_cell(cells.get("pos", "")).lower()
            if name and pos in ("gk", "df", "mf", "fw"):
                rows.append({"no": _wiki_cell(cells.get("no", "")), "pos": pos, "name": name})
        if rows:
            return rows if WIKI_SQUAD_SIZE[0] <= len(rows) <= WIKI_SQUAD_SIZE[1] else []
    return []

def update_team_squads(league_ids, out_of_time, now_dt):
    """data/futbol/heyet-<liga>.json. Dövrədə bir neçə klub, hər klub həftədə bir; eyni klub iki yarışdadırsa bir dəfə soruşulur.
    Alınmayan klubun köhnə heyəti qalır. Nəticə: {liga: heyəti olan komandalar}."""
    stamps = _read_json(TEAM_DIR / "heyet-yoxlama.json", {})
    titles = {team_slug(name): wiki for name, wiki in _OPENLIGA_CLUBS.values() if wiki}
    pool = {slug: team for league in league_ids for slug, team in (_read_json(TEAM_DIR / f"heyet-{league}.json", {}).get("teams") or {}).items()}
    members = {league: [slug for slug in _read_json(TEAM_DIR / f"{league}.json", {}).get("teams") or {} if slug in titles] for league in league_ids}
    def asked_at(slug):
        return _team_when(stamps.get(slug)) or now_dt - WIKI_SQUAD_EVERY
    wanted = sorted({slug for slugs in members.values() for slug in slugs if now_dt - asked_at(slug) >= WIKI_SQUAD_EVERY}, key=asked_at)
    for slug in wanted[:WIKI_SQUADS_PER_CYCLE]:
        if out_of_time():
            break
        stamps[slug] = now_dt.isoformat(timespec="seconds")
        query = urllib.parse.urlencode({"action": "parse", "prop": "wikitext", "redirects": 1, "page": titles[slug]})
        try:
            rows = parse_wiki_squad(_wiki_api(query)["parse"]["wikitext"])
        except Exception as e:
            print(f"  ! heyət {slug}:", type(e).__name__)
            stamps[slug] = (now_dt - WIKI_SQUAD_EVERY + WIKI_SQUAD_RETRY).isoformat(timespec="seconds")
            continue
        if rows:
            pool[slug] = {"players": rows, "wiki": titles[slug]}
    ready = {}
    for league, slugs in members.items():
        teams = {slug: pool[slug] for slug in slugs if slug in pool}
        if teams:
            _write_if_changed(TEAM_DIR / f"heyet-{league}.json", {"source": "Vikipediya, CC BY-SA 4.0", "teams": teams})
        ready[league] = sorted(teams)
    _write_if_changed(TEAM_DIR / "heyet-yoxlama.json", stamps)
    return ready

# Ölkə kubokları: oyunlar Vikipediyanın kubok səhifəsindəki oyun qutularındandır (CC BY-SA), kubok başına bir sorğu. Yalnız klub səhifəsi açılanda yüklənir.
# (qısa ad, ad, səhifə, saat qurşağı, klubları tanıdan liqalar). Saatsız qurşaq: yalnız tarix (ABŞ-da oyunlar müxtəlif qurşaqdadır). Portuqaliya səhifəsində oyun qutusu yoxdur.
WIKI_CUPS = [
    ("İngiltərə Kuboku", "İngiltərə Kuboku", "{s} FA Cup", "Europe/London", ("ingiltere", "cempionsip")),
    ("Liqa Kuboku", "İngiltərə Liqa Kuboku", "{s} EFL Cup", "Europe/London", ("ingiltere", "cempionsip")),
    ("İspaniya Kuboku", "İspaniya Kral Kuboku", "{s} Copa del Rey", "Europe/Madrid", ("ispaniya",)),
    ("İtaliya Kuboku", "İtaliya Kuboku", "{s} Coppa Italia", "Europe/Rome", ("italiya",)),
    ("Almaniya Kuboku", "Almaniya Kuboku", "{s} DFB-Pokal", "Europe/Berlin", ("almaniya",)),
    ("Fransa Kuboku", "Fransa Kuboku", "{s} Coupe de France", "Europe/Paris", ("fransa",)),
    ("Türkiyə Kuboku", "Türkiyə Kuboku", "{s} Turkish Cup", "Europe/Istanbul", ("turkiye",)),
    ("Hollandiya Kuboku", "Hollandiya Kuboku", "{s} KNVB Cup", "Europe/Amsterdam", ("hollandiya",)),
    ("Belçika Kuboku", "Belçika Kuboku", "{s} Belgian Cup", "Europe/Brussels", ("belcika",)),
    ("Şotlandiya Kuboku", "Şotlandiya Kuboku", "{s} Scottish Cup", "Europe/London", ("sotlandiya",)),
    ("Rusiya Kuboku", "Rusiya Kuboku", "{s} Russian Cup", "Europe/Moscow", ("rusiya",)),
    ("Səudiyyə Kuboku", "Səudiyyə Kral Kuboku", "{s} King's Cup (Saudi Arabia)", "Asia/Riyadh", ("seudiyye",)),
    ("Braziliya Kuboku", "Braziliya Kuboku", "{y} Copa do Brasil", "America/Sao_Paulo", ("braziliya",)),
    ("ABŞ Kuboku", "ABŞ Açıq Kuboku", "{y} U.S. Open Cup", None, ("abs",)),
]
CUP_PER_CYCLE = 3
CUP_DUE = {"every": datetime.timedelta(hours=6), "live_every": datetime.timedelta(hours=1), "window": datetime.timedelta(hours=6)}
_CUP_ORD = {"first": "1-ci", "second": "2-ci", "third": "3-cü", "fourth": "4-cü", "fifth": "5-ci", "sixth": "6-cı", "seventh": "7-ci", "eighth": "8-ci",
            "1": "1-ci", "2": "2-ci", "3": "3-cü", "4": "4-cü", "5": "5-ci", "6": "6-cı", "7": "7-ci", "8": "8-ci"}
_CUP_OF = {"64": "1/32 final", "32": "1/16 final", "16": "1/8 final"}

def _cup_round(head):
    """Bölmə başlığı -> mərhələ. Mərhələ olmayan başlıq (Matches, Draw, Group 1) None: oyun əvvəlki mərhələdə qalır."""
    h = head.strip().lower().replace("-", " ")
    if "qualifying" in h or "preliminary" in h:
        return "Təsnifat"
    m = re.match(r"(first|second|third|fourth|fifth|sixth|seventh|eighth) round\b", h) or re.fullmatch(r"round ([1-8])", h)
    if m:
        return f"{_CUP_ORD[m.group(1)]} mərhələ"
    m = re.match(r"round of (64|32|16)\b", h)
    if m:
        return _CUP_OF[m.group(1)]
    if h.startswith("eighth finals"):
        return "1/8 final"
    if h.startswith(("quarter finals", "quarterfinals")):
        return "1/4 final"
    if h.startswith(("semi finals", "semifinals")):
        return "Yarımfinal"
    if h == "final":
        return "Final"
    return "Qrup mərhələsi" if h.startswith("group stage") else None

def _wiki_box_end(text, start):
    depth, i = 0, start
    while i < len(text) - 1:
        pair = text[i:i + 2]
        if pair == "{{":
            depth, i = depth + 1, i + 2
        elif pair == "}}":
            depth, i = depth - 1, i + 2
            if not depth:
                return i
        else:
            i += 1
    return len(text)

def _wiki_box_params(box):
    """Qutunun sahələri. Keçid və şablonun içindəki | sahəni bölmür."""
    params, depth, last = {}, 0, None
    parts, i = [], 2
    body = box[:-2]
    for i in range(2, len(body)):
        pair = body[i:i + 2]
        if pair in ("{{", "[["):
            depth += 1
        elif pair in ("}}", "]]"):
            depth -= 1
        elif body[i] == "|" and not depth:
            if last is not None:
                parts.append(body[last:i])
            last = i + 1
    if last is not None:
        parts.append(body[last:])
    for part in parts:
        key, sep, value = part.partition("=")
        if sep:
            params[key.strip().lower()] = value.strip()
    return params

def _cup_plain(raw):
    text = re.sub(r"<ref[^>]*/>|<ref.*?</ref>", "", raw or "", flags=re.S).replace("'''", "").replace("''", "")
    return re.sub(r"\{\{\s*efn[^{}]*(?:\{\{[^{}]*\}\}[^{}]*)*\}\}", "", text).strip()

def _cup_name(raw):
    """(göstərilən ad, səhifə adı). Hələ bəlli olmayan tərəf («Winner of Match 5», TBD) boş qaytarılır."""
    text = re.sub(r"\{\{[^{}]*\}\}", "", _cup_plain(raw))
    link = re.search(r"\[\[([^\]|]+)(?:\|([^\]]+))?\]\]", text)
    name = (link.group(2) or link.group(1)) if link else text
    name = html.unescape(re.sub(r"\s*\([^)]*\)\s*$", "", name.strip())).strip()
    if not name or re.fullmatch(r"\d[A-Z](?:\W*\d[A-Z])?", name) or re.search(r"\b(winners?|losers?|tbd|tba|match|bye)\b", name.lower()):
        return "", ""
    return name, link.group(1).strip() if link else ""

def cup_team(name, page, pool):
    """Kubokdakı ad -> liqadakı klubun ünvanı. Yalnız tam uyğunluq və ya adın klubun adının içində olması: «Real Madrid Castilla» Real Madrid deyil."""
    known = {slug: _tsdb_words(t.get("name")) for slug, t in pool.items()}
    for text in (TSDB_ALIAS.get(name, name), page):
        words = _tsdb_words(text)
        hits = [slug for slug, k in known.items() if words and k == words]
        if len(hits) == 1:
            return hits[0]
    words = _tsdb_words(TSDB_ALIAS.get(name, name))
    hits = [slug for slug, k in known.items() if words and words < k]
    return hits[0] if len(hits) == 1 else None

def _cup_kick(params, zone, year=None):
    """(ISO tarix, yalnız gün). Saat və ya qurşaq bəlli deyilsə gün göstərilir. İllik kubokda (ABŞ) tarix ilsiz yazılır: il səhifənin adındandır.
    Bir neçə günlük tarix («4–5 February 2027») boş qalır: oyunun günü hələ bəlli deyil."""
    raw, day = _cup_plain(params.get("date")), None
    tpl = re.search(r"start date\s*\|\s*(\d{4})\s*\|\s*(\d{1,2})\s*\|\s*(\d{1,2})", raw, re.I)
    if tpl:
        day = datetime.date(int(tpl.group(1)), int(tpl.group(2)), int(tpl.group(3)))
    else:
        text = re.sub(r"\s+", " ", re.sub(r"\{\{[^{}]*\}\}|\[\[|\]\]", "", raw)).strip()
        for fmt, spare in (("%d %B %Y", ""), ("%B %d, %Y", ""), ("%Y-%m-%d", ""), ("%Y %B %d", year), ("%Y %d %B", year)):
            try:
                day = datetime.datetime.strptime(f"{spare} {text}" if spare else text, fmt).date()
                break
            except ValueError:
                pass
    if not day:
        return "", False
    hm = re.search(r"(\d{1,2}):(\d{2})", params.get("time") or "")
    if hm and zone and int(hm.group(1)) < 24:
        kick = datetime.datetime(day.year, day.month, day.day, int(hm.group(1)), int(hm.group(2)), tzinfo=ZoneInfo(zone))
        return kick.isoformat(timespec="seconds"), False
    return f"{day.isoformat()}T12:00:00+00:00", True

def cup_games(text, pool, zone, year=None):
    """Kubok səhifəsinin vikimətni -> (klublar, oyunlar). Tərəfi bəlli olmayan qutu yazılmır."""
    heads = [(m.start(), _cup_round(m.group(2))) for m in re.finditer(r"^(={2,4})\s*(.+?)\s*\1\s*$", text, re.M)]
    teams, games = {}, []
    for m in re.finditer(r"\{\{\s*football ?box", text, re.I):
        params = _wiki_box_params(text[m.start():_wiki_box_end(text, m.start())])
        (home, home_page), (away, away_page) = _cup_name(params.get("team1")), _cup_name(params.get("team2"))
        if not home or not away:
            continue
        slugs = []
        for name, page in ((home, home_page), (away, away_page)):
            slug = cup_team(name, page, pool)
            teams[slug or team_slug(name)] = dict(pool[slug]) if slug else {"name": name, "logo": ""}
            slugs.append(slug or team_slug(name))
        if slugs[0] == slugs[1]:
            continue
        date, day = _cup_kick(params, zone, year)
        game = {"date": date, "home": slugs[0], "away": slugs[1], "played": False, "round": next((r for at, r in reversed(heads) if at < m.start() and r), "")}
        if day:
            game["day"] = True
        place = re.search(r"\[\[(?:[^\]|]+\|)?([^\]]+)\]\]", params.get("stadium") or "")
        stadium = place.group(1) if place else re.sub(r"\{\{[^{}]*\}\}", "", params.get("stadium") or "").strip()
        if stadium:
            game["stadium"] = stadium[:60]
        score = _cup_plain(params.get("score"))
        got = re.search(r"(\d+)\s*[–−-]\s*(\d+)", score)
        if got:
            game.update(played=True, hs=int(got.group(1)), **{"as": int(got.group(2))})
            pen = re.search(r"(\d+)\s*[–−-]\s*(\d+)", params.get("penaltyscore") or "")
            if pen:
                game["pen"] = f"{pen.group(1)}–{pen.group(2)}"
        elif re.search(r"cancel|postpon|abandon", score, re.I):
            game["state"] = "off"
        games.append(game)
    return teams, sorted(games, key=lambda g: g.get("date") or "9999")

def update_cups(checked, now_dt, out_of_time):
    """Ölkə kubokları. Dövrədə ən çoxu CUP_PER_CYCLE sorğu, alınmayan kubokun köhnə faylı qalır. Nəticə: index.json sətirləri."""
    rows, asked = [], 0
    for short, name, pattern, zone, leagues in WIKI_CUPS:
        cid, pool = team_slug(short), {}
        for lid in leagues:
            pool.update(_read_json(TEAM_DIR / f"{lid}.json", {}).get("teams") or {})
        if not pool:
            continue
        doc = _read_json(TEAM_DIR / f"{cid}.json", {})
        if asked < CUP_PER_CYCLE and not out_of_time() and _team_due(doc, checked.get(cid), now_dt, **CUP_DUE):
            asked += 1
            checked[cid] = now_dt.isoformat(timespec="seconds")
            title = _wiki_title(pattern, now_dt)
            try:
                text = _wiki_api("action=parse&prop=wikitext&redirects=1&page=" + urllib.parse.quote(title))["parse"]["wikitext"]
                years = re.search(r"(\d{4})(?:–(\d{2}))?", title)
                teams, games = cup_games(text, pool, zone, None if years.group(2) else years.group(1))
                if games:
                    doc = {"id": cid, "name": name, "short": short, "source": "Vikipediya (kubok)", "url": "https://en.wikipedia.org/wiki/" + urllib.parse.quote(title.replace(" ", "_")), "sport": "football", "asof": "",
                           "key": years.group(1), "season": f"{years.group(1)}/{years.group(2)}" if years.group(2) else years.group(1), "teams": teams, "groups": [], "games": games}
                    _write_if_changed(TEAM_DIR / f"{cid}.json", doc)
            except Exception as e:
                print(f"  ! kubok {short}:", type(e).__name__)
        if doc.get("games"):
            seasons = [{"key": doc["key"], "label": doc["season"]}]
            rows.append({"id": cid, "name": doc["name"], "short": short, "source": doc["source"], "sport": "football", "cup": True, "seasons": seasons, "ready": seasons, "teams": sorted(doc["teams"])})
    return rows

# Milli komandaların yarışları (sahib 2026-11-07): faylları .github/scripts/milli.cjs (pipeline slow_loop) Vikipediyadan yazır.
# Burada yalnız siyahıya (index.json) düşür, «nat» işarəsi ilə: sayt «Milli komandalar»dakı ölkənin yarışını buradan tapır. Şəbəkə yoxdur.
NATIONAL_DOCS = ("dc-2026", "avro-2028-secme", "ml-a", "ml-b", "ml-c", "ml-d", "asiya-kuboku", "afrika-secme", "konkakaf-a", "konkakaf-b", "konkakaf-c")

def national_rows():
    rows = []
    for nid in NATIONAL_DOCS:
        doc = _read_json(TEAM_DIR / f"{nid}.json", {})
        if not isinstance(doc, dict) or not doc.get("teams"):
            continue
        seasons = [{"key": str(doc.get("key") or ""), "label": str(doc.get("season") or "")}]
        rows.append({"id": nid, "name": doc.get("name") or nid, "short": doc.get("short") or nid, "source": doc.get("source") or "Vikipediya",
                     "sport": "football", "nat": True, "seasons": seasons, "ready": seasons,
                     "teams": [r["team"] for g in doc.get("groups") or [] for r in g.get("rows") or []] or sorted(doc["teams"])})
    return rows

def update_team_pages():
    """Komanda səhifələrinin faylları: hər liqa üçün data/futbol/<liga>.json (cədvəl və mövsümün bütün oyunları), keçmiş mövsümlər
    <liga>-<il>.json, siyahı index.json. Alınmayan liqanın köhnə faylı qalır."""
    started = time.monotonic()
    out_of_time = lambda: time.monotonic() - started > TEAM_BUDGET_S
    now_dt = datetime.datetime.now(datetime.timezone.utc)
    now = now_dt.isoformat(timespec="seconds")
    TEAM_DIR.mkdir(parents=True, exist_ok=True)
    index = _read_json(TEAM_DIR / "index.json", {})
    checked = index.get("checked") or {}
    known = {l.get("id"): l for l in index.get("leagues") or []}
    empty = set(index.get("empty") or [])
    openliga = index.get("openliga") or {}
    sources = _team_sources()
    fresh = 0
    for spec in sources:
        if out_of_time():
            break
        if not _team_due(_read_json(TEAM_DIR / f"{spec['id']}.json", {}), checked.get(spec["id"]), now_dt):
            continue
        checked[spec["id"]] = now  # alınmayan liqa da növbəsini gözləyir
        try:
            doc, seasons = _team_league(spec)
        except Exception as e:
            print(f"  ! komanda {spec['short']}:", type(e).__name__)
            if isinstance(e, urllib.error.HTTPError) and e.code == 403:
                checked.update({s["id"]: now for s in sources})  # rədd edən sayta bu dövrə başqa sorğu getmir
                break
            continue
        _write_if_changed(TEAM_DIR / f"{spec['id']}.json", doc)
        table = [r["team"] for g in doc["groups"] for r in g["rows"]]
        known[spec["id"]] = {"id": spec["id"], "name": doc["name"], "short": spec["short"], "source": doc["source"], "seasons": seasons, "teams": table or sorted(doc["teams"])}
        if spec["reserve"]:
            known[spec["id"]]["reserve"] = True
        fresh += 1
    past = 0
    for spec in sources:
        for season in (known.get(spec["id"]) or {}).get("seasons", [])[1:]:
            name = f"{spec['id']}-{season['key']}"
            if out_of_time() or past >= TEAM_PAST_PER_CYCLE or name in empty or (TEAM_DIR / f"{name}.json").exists():
                continue
            past += 1
            try:
                doc, _seasons = _team_league(spec, season["key"])
                _write_if_changed(TEAM_DIR / f"{name}.json", doc)
            except _NoTeamData:
                empty.add(name)  # bu mövsümdə həmin yarış yoxdur: bir daha soruşulmur
            except Exception as e:
                print(f"  ! komanda {name}:", type(e).__name__)
    leagues = []
    for spec in sources:
        league = known.get(spec["id"])
        if league:
            # Seçicidə yalnız faylı olan mövsüm.
            ready = [x for i, x in enumerate(league["seasons"]) if i == 0 or (TEAM_DIR / f"{spec['id']}-{x['key']}.json").exists()]
            leagues.append(dict(league, ready=ready))
    world_rows = []
    worlds = _read_json(SPORTS_FILE, {}).get("leagues") or []
    tsdb_stamps = _read_json(TEAM_DIR / "oyun-yoxlama.json", {})
    tsdb_docs = []
    for world in worlds:
        doc = team_world_league(world)
        if doc["id"] in TSDB_LEAGUES and doc["groups"]:
            tsdb_docs.append(dict(doc, games=_read_json(TEAM_DIR / f"{doc['id']}.json", {}).get("games") or []))
    try:
        tsdb_fresh = tsdb_refresh(tsdb_docs, tsdb_stamps, now_dt, out_of_time)
    except Exception as e:
        print("  ! oyunlar:", type(e).__name__)
        tsdb_fresh = {}
    _write_if_changed(TEAM_DIR / "oyun-yoxlama.json", tsdb_stamps)
    tsdb_old = {d["id"]: d["games"] for d in tsdb_docs}
    nba_games = None
    for world in worlds:
        if world.get("id") == "nba" and world.get("groups"):
            doc = team_world_league(world)
            try:
                nba_games = nba_merge(_read_json(TEAM_DIR / f"{doc['id']}.json", {}).get("games") or [], nba_refresh(doc, tsdb_stamps, now_dt, out_of_time))
            except Exception as e:
                print("  ! NBA oyunları:", type(e).__name__)
    _write_if_changed(TEAM_DIR / "oyun-yoxlama.json", tsdb_stamps)
    for world in worlds:
        doc = team_world_league(world)
        if not doc["groups"]:
            continue
        if doc["id"] in tsdb_old:
            games = tsdb_merge(tsdb_old[doc["id"]], tsdb_fresh.get(doc["id"]) or {})
            if games:
                doc = team_world_with_games(doc, {}, games, TSDB_SOURCE)
        elif doc["id"] == "nba" and nba_games:
            doc = team_world_with_games(doc, {}, nba_games, {"source": "Vikipediya"})
        checked[doc["id"]] = world.get("at") or now
        seasons = [{"key": doc["key"], "label": doc["season"]}]
        ready = seasons
        shortcut = _OPENLIGA_LEAGUES.get(doc["id"])
        if shortcut:
            current = _read_json(TEAM_DIR / f"{doc['id']}.json", {})
            mine = openliga.setdefault(doc["id"], {})
            fetched = None if out_of_time() else _openliga_refresh(shortcut, doc["key"], current, mine, now_dt)
            teams, games = fetched or (current.get("teams") or {}, current.get("games") or [])
            if games:
                doc = team_world_with_games(doc, teams, games)
                checked[doc["id"]] = mine.get("checked") or now
                seasons = seasons + [{"key": str(y), "label": f"{y}/{(y + 1) % 100:02d}"} for y in range(int(doc["key"]) - 1, int(doc["key"]) - TEAM_PAST_SEASONS - 1, -1)]
                for season in seasons[1:]:
                    name = f"{doc['id']}-{season['key']}"
                    if out_of_time() or past >= TEAM_PAST_PER_CYCLE or name in empty or "until" in mine or (TEAM_DIR / f"{name}.json").exists():
                        continue
                    past += 1
                    try:
                        _write_if_changed(TEAM_DIR / f"{name}.json", _openliga_past(doc, shortcut, season["key"]))
                    except _NoTeamData:
                        empty.add(name)
                    except Exception as e:
                        print(f"  ! komanda {name}:", type(e).__name__)
                ready = [x for i, x in enumerate(seasons) if i == 0 or (TEAM_DIR / f"{doc['id']}-{x['key']}.json").exists()]
        _write_if_changed(TEAM_DIR / f"{doc['id']}.json", doc)
        world_rows.append({"id": doc["id"], "name": doc["name"], "short": doc["short"], "source": doc["source"], "sport": doc["sport"], "seasons": seasons, "ready": ready,
                           "teams": [r["team"] for g in doc["groups"] for r in g["rows"]]})
    squads = update_team_squads([x["id"] for x in world_rows if x["id"] in _OPENLIGA_LEAGUES], out_of_time, now_dt)
    leagues += [dict(x, heyet=squads[x["id"]]) if squads.get(x["id"]) else x for x in world_rows]
    leagues += update_cups(checked, now_dt, out_of_time)
    leagues += national_rows()
    _write_if_changed(TEAM_DIR / "index.json", {"leagues": leagues, "checked": checked, "empty": sorted(empty), "openliga": openliga})
    print(f"Komanda səhifələri: {fresh} liqa, {past} keçmiş mövsüm, {time.monotonic() - started:.1f} s")

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

# Köməkçi feillər: «verdi/verib», «etdi/edib», «olub/oldu» eyni xəbərin fərqli yazılışıdır, məzmun fərqi deyil.
_AUX_VERB = re.compile(r"(?:ed|et|ol|ver)(?:ib|ir|di|du|ecek|eceq|ecekdir|ilib|ildi|ilir|ilecek|iler|en|me|meyib|diler|ub|ur|unub|undu|unur|unacaq|acaq|ar|an|maz)?|olunacaq|edilmeyib")


def _detail(tok, others):
    """Başlığın o birində olmayan, məzmun daşıyan sözü: köməkçi feil, ümumi ad (Bakı, prezident) və ya
    o birindəki sözün başqa şəkilçili forması (Polşa / polşalı, istehsalı / istehsalını) deyil."""
    if _AUX_VERB.fullmatch(tok) or tok in _EVENT_STOP or _stem(tok) in _GENERIC_ANCHOR:
        return False
    n = min(5, len(tok))
    return not any(o[:n] == tok[:n] and len(o) >= n for o in others)


def _different_details(a, b):
    """Hər iki başlıq öz xüsusi məlumatını verir, ortaq məzmun isə ondan çox deyil: «İlham Əliyev Ərdoğana başsağlığı verdi» /
    «İlham Əliyev polşalı həmkarına başsağlığı verdi» — 4 ortaq söz, amma ortaq məzmun yalnız «başsağlığı»dır (rəhbərin adı və
    köməkçi feil sayılmır): iki ayrı xəbər (2026-11-10 canlıda bir kartda idi). «Qazaxda avtomobil yanıb / yandı» kimi
    başlıqlarda ortaq məzmun fərqdən çoxdur, birləşir."""
    da, db = sum(1 for t in a - b if _detail(t, b)), sum(1 for t in b - a if _detail(t, a))
    if not da or not db:
        return False
    shared = sum(1 for t in a & b if not _AUX_VERB.fullmatch(t) and t not in _EVENT_STOP and _stem(t) not in _GENERIC_ANCHOR | _LEADER_STEMS)
    return shared <= max(da, db)


def _titles_similar(toks, sh, other_toks, other_sh):
    a, b = set(toks), set(other_toks)
    if len(a) < 3 or len(b) < 3:
        return False
    if a != b and _different_details(a, b):
        return False
    # «verdi» / «verib» fərqi oxşarlığı azaltmasın (Gündəlik.az «...Ərdoğana başsağlığı verdi» əsas kartdan ayrı qalırdı)
    a, b = {"~" if _AUX_VERB.fullmatch(t) else t for t in a}, {"~" if _AUX_VERB.fullmatch(t) else t for t in b}
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
# Rəhbərliyin adı onlarla müxtəlif xəbərdə keçir: başlıqların ortaq məzmunu sayılmır («Rusiya mediası Prezident İlham Əliyevin
# Xankəndi çıxışlarını işıqlandırıb» / «İlham Əliyev Ərdoğana başsağlığı verdi» xülasə oxşarlığı ilə bir kartda idi, 2026-11-10).
_LEADER_STEMS = {"ilham", "eliyev", "mehrib", "heyder", "bascis"}
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
_PHASE_CACHE = {}
_PLACE_CACHE = {}
_FOUNDATION_TITLE = re.compile(r"(?<!\w)t[əe]m[əe]l")
_OPENING_TITLE = re.compile(r"(?<!\w)(?:a[çc][ıi]l(?:[ıi][şs]|[ıi]b|d[ıi])|istifad[əe]y[əe]\s+ver)")
# «Xankəndi Stadionu» yerlik halında deyil; şəhər adı məkan bildirən isimdən əvvəl gəlir.
_TITLE_PLACE_RX = re.compile(r"(?<!\w)(?:" + "|".join(re.escape(w) for w in sorted(PLACE_WORDS | {"bakı"}, key=len, reverse=True))
                             + ")" + _PLACE_SUF + r"(?=\s+(?:stadion|peşə|şəhər|rayon|kənd|universitet|məktəb|kitabxana|xəstəxana))", re.I)


def _opening_phase(a):
    title = (a.get("title") or "").lower().replace("i̇", "i")
    if title not in _PHASE_CACHE:
        _PHASE_CACHE[title] = int(bool(_FOUNDATION_TITLE.search(title))) + 2 * int(bool(_OPENING_TITLE.search(title)))
    return _PHASE_CACHE[title]

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
        if not re.search(r"(?:da|də|dan|dən)$", low) or _concepts(low).strip() != low or _ORG_WORDS.search(_norm_title(w)):
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

def _event_conflict(a, b):
    """Təməlqoyma və açılış, yaxud açıq fərqli məkanlar ayrı hadisədir — ümumi səfər xülasəsi onları birləşdirmir."""
    phase_a, phase_b = _opening_phase(a), _opening_phase(b)
    if phase_a and phase_b and phase_a != phase_b:
        return True
    # Sürətli dövrəyə tam hadisə təhlili (şəxs, qurum, bütün köklər) gətirilmir.
    def places(row):
        text = (row.get("title") or "") + ". " + (row.get("summary") or "")[:240]
        if text not in _PLACE_CACHE:
            _PLACE_CACHE[text] = _places(text) | {_stem(_norm_title(m.group())) for m in _TITLE_PLACE_RX.finditer(row.get("title") or "")}
        return _PLACE_CACHE[text]
    places_a, places_b = places(a), places(b)
    return bool(places_a and places_b and not (places_a & places_b))


def _same_event(a, b):
    """0 — fərqli; 1 — zəif uyğunluq (yalnız klaster başı ilə və ya 2 üzvlə təsdiqlənəndə sayılır);
    2 — güclü uyğunluq (eyni şəxs, eyni qurum + məzmun, 2+ lövbər + məzmun, kökləri güclü üst-üstə düşür)."""
    if _event_conflict(a, b):
        return 0
    # Shared boilerplate in summaries must not join unrelated headlines.
    ta, tb = a.get("title") or "", b.get("title") or ""
    title_common = (_event_stems(ta) & _event_stems(tb)) - _GENERIC_ANCHOR - _LEADER_STEMS
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

def _group_candidates(a, toks, title_index, stem_index, event_index, exact_index):
    """Oxşarlıq üçün ən azı 3 ortaq söz/kök lazımdır. Hadisə növü eyni olanlar da saxlanır:
    şəxs adının yazılışı fərqlənəndə (_ent_match) 3 dəqiq kök üst-üstə düşməyə bilər."""
    classes, _persons, _orgs, stems, _anchors_, _places_ = _event_sig(a)
    hits = set(exact_index.get(_norm_title(a.get("title") or ""), ()))
    for words, index in ((set(toks), title_index), (stems, stem_index)):
        counts = collections.Counter(i for word in words for i in index.get(word, ()))
        hits.update(i for i, n in counts.items() if n >= 3)
    for event in classes:
        hits.update(event_index.get(event, ()))
    return hits


def _same_headline(a, b):
    """Eyni başlıq və ya çox yaxın başlıq (eyni saytın təkrar dərci)."""
    ta, tb = a.get("title") or "", b.get("title") or ""
    if len(_norm_title(ta)) >= 12 and _norm_title(ta) == _norm_title(tb):
        return True
    ka, kb = _title_tokens(ta), _title_tokens(tb)
    return _titles_similar(ka, _shingles(ka), kb, _shingles(kb))


def group_duplicates(articles, same_source_exact=True, same_out=None):
    """Yaxın başlıqlı, fərqli mənbəli xəbərləri bir elementdə birləşdirir.

    Əsas xəbər tam qalır; digərləri yığcam `alts` siyahısındadır (mənbə + keçid + vaxt).
    Arxivdə eyni saytın şablon başlıqları ayrı saxlanır (`same_source_exact=False`);
    başqa mənbənin uyğun başlığı nüsxəni təsdiqləyirsə həmin qrupa qoşula bilər.
    `same_out` lüğəti verilsə, kartdakı saytın eyni başlıqlı təkrar yazıları ora yazılır (keçid → kartın əsas keçidi).
    """
    own = [a for a in articles if a.get("source") == OWN_SOURCE]
    if own:  # öz xəbər qruplaşmır: başqa kartın alt mənbəsi olmur, başqa mənbəni də özünə bağlamır (sətir olduğu kimi qalır)
        return group_duplicates([a for a in articles if a.get("source") != OWN_SOURCE], same_source_exact, same_out) + own
    remembered = {}
    _SIG_CACHE.clear()
    _PHASE_CACHE.clear()
    _PLACE_CACHE.clear()
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
    title_index, stem_index, event_index, exact_index = (collections.defaultdict(set) for _ in range(4))
    for dt, toks, sh, a in prepared:
        best, best_score, best_i = None, 0, None
        if dt is not None and len(toks) >= 3:
            key = _norm_title(a.get("title") or "")
            src = a.get("source")
            for ci in sorted(_group_candidates(a, toks, title_index, stem_index, event_index, exact_index)):
                members = clusters[ci]
                head = members[0][0]
                if head is None or abs(dt - head) > GROUP_WINDOW:
                    continue
                near = [(mt, mtks, msh, ma) for mt, mtks, msh, ma in members if mt is not None and abs(dt - mt) <= GROUP_WINDOW]
                if any(_event_conflict(a, ma) for _mt, _k, _s, ma in near):
                    continue  # ümumi başlıqlı vasitəçi iki ayrı hadisəni zəncirlə birləşdirməsin
                if not near:
                    continue
                exact = len(key) >= 12 and any(_norm_title(ma.get("title") or "") == key for _mt, _k, _s, ma in near)
                official = src in OFFICIAL_SOURCES or any(ma.get("source") in OFFICIAL_SOURCES for _mt, _k, _s, ma in members)
                same_src = src in {ma.get("source") for _mt, _k, _s, ma in members}
                score = 0
                if exact and (same_source_exact or not same_src):
                    score = 4
                elif official:
                    # rəsmi şablon başlıqlar («X-in nazirini qəbul edib») fərqli hadisələrdə oxşar görünür — çox yaxın olmalıdır
                    if not same_src and any(_jaccard(set(toks), set(mtks)) >= 0.85 and _titles_similar(toks, sh, mtks, msh)
                                            for _mt, mtks, msh, _ma in near):
                        score = 3
                elif any(ma.get("source") != src and _titles_similar(toks, sh, mtks, msh) for _mt, mtks, msh, ma in near):
                    # Mənbənin klasterdə başqa yazısı olsa da, digər saytın eyni başlığı surəti təsdiqləyir.
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
                    best, best_score, best_i = members, score, ci
        if best is not None:
            best.append((dt, toks, sh, a))
        else:
            best_i = len(clusters)
            clusters.append([(dt, toks, sh, a)])
        for word in set(toks):
            title_index[word].add(best_i)
        sig = _event_sig(a)
        for word in sig[3]:
            stem_index[word].add(best_i)
        for event in sig[0]:
            event_index[event].add(best_i)
        exact_index[_norm_title(a.get("title") or "")].add(best_i)
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
                if title and same and not _event_conflict(alt, primary) and pdt is not None and adt is not None and abs(adt - pdt) <= GROUP_WINDOW:
                    kept.append(alt)
            alts.extend(kept[:max(0, 20 - len(alts))])
        alts.sort(key=lambda x: x.get("publishedAt") or "", reverse=True)
        # Kartdakı «N mənbə» həqiqətən N sayt demək olsun. Bir saytın iki yazısı varsa kartın başlığına yaxın olan qalır:
        # əvvəl ən yenisi qalırdı və Konkret.az-ın «Ərdoğana başsağlığı» xəbəri «polşalı həmkarına» yazısına yer verib ayrı kart olurdu.
        ptitle = primary.get("title") or ""
        pset = set(_title_tokens(ptitle))
        def closeness(x):
            return (_norm_title(x.get("title") or "") == _norm_title(ptitle), _jaccard(set(_title_tokens(x.get("title") or "")), pset))
        best = {}
        for alt in alts:
            src = alt.get("source")
            if src != primary.get("source") and (src not in best or closeness(alt) > closeness(best[src])):
                best[src] = alt
        kept = {id(x) for x in best.values()}
        if same_out is not None:
            # Eyni sayt eyni xəbəri yeni keçidlə təkrar dərc edib: təkrar ayrıca kart olmasın, kartın altında da sayılmasın.
            twins = {primary.get("source"): primary, **best}
            for alt in alts:
                twin = twins.get(alt.get("source"))
                if id(alt) not in kept and twin is not None and _same_headline(alt, twin):
                    same_out[alt["sourceUrl"]] = primary.get("sourceUrl")
        alts = [x for x in alts if id(x) in kept]
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
    # YouTube sətirlərini merge_sources yazır (update_social, update_video): bu siyahıda yoxdurlar, hər sürətli dövrə onları silirdi.
    have, extra = {r["name"] for r in rows}, {f"YouTube · {n}" for n, _ in YT_NEWS} | {f"YouTube · {n}" for _, _, n in YT_ACCOUNTS}
    out.extend(s for s in prev_list if isinstance(s, dict) and s.get("name") in extra - have)
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
    return html.escape(_CTRL.sub("", cur), quote=True)

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
    <meta http-equiv="Content-Security-Policy" content="__CSP__" />
    <script>if(top!==self)document.documentElement.style.display="none";try{var t=localStorage.getItem("8ulduz-theme");document.documentElement.dataset.theme=t==="light"?"light":"dark";var f=localStorage.getItem("8ulduz-fs");document.documentElement.dataset.fs=/^[0-4]$/.test(f||"")?f:"2";}catch(e){}</script>
    <title>__LABEL__ — 8ulduz</title>
    <meta name="description" content="__DESC__ — 8ulduz, Azərbaycan və dünyadan son xəbərlər." />
    <link rel="canonical" href="__URL__" />
    <meta name="theme-color" content="#15233b" />
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
    <link rel="preconnect" href="https://raw.githubusercontent.com" crossorigin />
    <link rel="modulepreload" href="../../assets/app.min.js" />
    <link rel="stylesheet" href="../../assets/app.css" />
    <script src="../../assets/config.js" defer></script>
    <script src="../../assets/content-policy.js" defer></script>
    <script type="module" src="../../assets/app.min.js"></script>
    <!-- Resurslar yuxarıda nisbi yolla yükləndi; tətbiq kök ünvanda işləyir, ona görə ünvan kökə keçirilir -->
    <script>history.replaceState(null, "", new URL("../../#/bolme/__SLUG__", location.href));</script>
  </head>
  <body>
    <div id="app">
      <main class="wrap"><h1>__LABEL__</h1><p>__DESC__</p>__ITEMS__
      <p><a href="../../">8ulduz — baş səhifə</a> · <a href="../valyuta/">Valyuta məzənnəsi</a> · <a href="../cedvel/">Premyer Liqa cədvəli</a> · <a href="../tixac/">Bakıda tıxac indi</a> · <a href="../namaz/">Namaz vaxtları</a> · <a href="../hava/">Hava proqnozu</a> · <a href="../../icmal/">Günün icmalı</a></p><noscript>Tam sayt üçün JavaScript-i aktiv edin.</noscript></main>
    </div>
  </body>
</html>
"""

def _story_titles(stories, articles):
    """Xəbər səhifəsinin başlığı: lentdən, yoxdursa səhifənin <h1>-indən."""
    by_id = {a.get("id"): a for a in articles if a.get("id")}
    titles = {}
    # Lentdən çıxmış xəbərin başlığı bir dəfə səhifədən oxunur, sonra keşdən (əvvəl hər dövrədə ~5 000 fayl açılırdı).
    cache_file = CACHE_DIR / "story_titles.json"
    saved = _read_json(cache_file, {})
    saved = saved if isinstance(saved, dict) else {}
    kept = {}
    for sid, row in (stories or {}).items():
        a = by_id.get(sid)
        if a and str(a.get("title") or "").strip():
            titles[sid] = (a.get("title"), a.get("source") or "")
            continue
        if isinstance(row, list) and len(row) > 4 and row[4]:
            titles[sid] = (row[4], "")
            continue
        if saved.get(sid):
            titles[sid] = (saved[sid], "")
            kept[sid] = saved[sid]
            continue
        try:
            text = (STORY_DIR / sid / "index.html").read_text(encoding="utf-8")[:4000]
            m = re.search(r"<h1>(.*?)</h1>", text)
            if m:
                titles[sid] = (html.unescape(m.group(1)), "")
                kept[sid] = titles[sid][0]
        except Exception:
            pass
    if kept != saved:
        try:
            _save_cache(cache_file, kept)
        except Exception:
            pass
    return titles

def section_page(slug, label, desc, articles, limit=30, stories=(), titles=None):
    items = [a for a in articles if a.get("category") == slug and (a.get("lang") or "az") == "az"]
    items.sort(key=lambda a: a.get("publishedAt") or "", reverse=True)
    # Öz səhifəsi olan xəbər ora keçid verir (Google səhifəni bölmədən də tapır), qalanı mənbəyə.
    href = lambda a: f'../../xeber/{a["id"]}/' if a.get("id") in stories else _xml(a.get("sourceUrl"))
    shown = items[:limit]
    shown_ids = {a.get("id") for a in shown}
    lis = [f'<li><a href="{href(a)}" rel="noopener">{_xml(a.get("title"))}</a> <small>{_xml(a.get("source"))}</small></li>' for a in shown]
    extra = []
    for sid, row in (stories or {}).items():
        if sid in shown_ids or not (isinstance(row, list) and len(row) > 2 and row[2] == slug):
            continue
        title, source = (titles or {}).get(sid, ("", ""))
        if title:
            extra.append((row[0], sid, title, source))
    extra.sort(reverse=True)
    lis.extend(f'<li><a href="../../xeber/{sid}/">{_xml(title)}</a> <small>{_xml(source)}</small></li>' for _, sid, title, source in extra)
    return _page_html(slug, label, desc, f"<ul>{''.join(lis)}</ul>")

# index.html-dəki siyasətlə eynidir (tests/browser-logic.test.cjs). connect-src qəsdən yoxdur: canlı kanala sorğu bloklanmasın.
# connect-src olmayanda sendBeacon 8ulduz.goatcounter.com-a keçir. Skript gc.zgo.at-dandır; hər iki ünvan script-src-dədir.
_CSP = "script-src 'self' {hashes} https://gc.zgo.at https://8ulduz.goatcounter.com; object-src 'none'; base-uri 'self'; form-action 'self'; frame-src https://www.youtube-nocookie.com https://embed.waze.com https://yandex.com"

def _with_csp(page):
    """Səhifənin öz kiçik skriptlərindən başqa daxili skript işləmir."""
    hashes = ("'sha256-" + base64.b64encode(hashlib.sha256(code.encode("utf-8")).digest()).decode() + "'"
              for code in re.findall(r"<script>(.*?)</script>", page, re.S))
    return page.replace("__CSP__", _CSP.format(hashes=" ".join(hashes)))

def _page_html(slug, label, desc, items):
    url = f"{SITE}bolme/{slug}/"
    return _with_csp(_SECTION_HTML.replace("__ITEMS__", items).replace("__LABEL__", _xml(label)).replace("__DESC__", _xml(desc))
            .replace("__URL__", url).replace("__SITE__", SITE).replace("__SLUG__", slug))

# Xidmət səhifələri: axtarış sistemi hash ünvanını ayrıca səhifə saymır. bolme/ altındadır, çünki pipeline.sh main-ə bu qovluğu yazır.
SERVICE_PAGES = [
    ("valyuta", "Valyuta məzənnəsi", "Dollar, avro, rubl və lirənin manatla bugünkü məzənnəsi, neft və qızıl qiyməti"),
    ("cedvel", "Premyer Liqa cədvəli", "Azərbaycan Premyer Liqasının turnir cədvəli"),
    # Sahib 2026-11-14: «Bakıda tıxac indi» səhifəsi — avtomatik ölçü (tixac.yml, Mapbox), pik saat bülletenləri (öz xəbər modulu), yol xəbərləri.
    ("tixac", "Bakıda tıxac indi", "Bakının səkkiz əsas yolunun canlı vəziyyəti, pik saat bülletenləri, qəza və bağlanan yollar haqqında son xəbərlər"),
    # Menyudakı «Son dəqiqə» və alt zolaqdakı «Video» həqiqi keçiddir (/bolme/<ad>/): səhifəsi olmasa Google 404 görür (2026-11-11).
    ("sondeqiqe", "Son dəqiqə", "Son bir saatın xəbərləri"),
    ("video", "Video xəbərlər", "Azərbaycan mətbuatının videolu xəbərləri"),
]
_ROAD_RX = re.compile(r"tıxac|qəza(?!lı)|yol polisi|nəqliyyatın hərəkət|yol bağlı|avtomobil yol|(?:^|[^\w])(?:BNA|DYP)(?:[^\w]|$)", re.I)

def _table(head, rows):
    cells = lambda row, tag: "".join(f"<{tag}>{_xml('' if c is None else str(c))}</{tag}>" for c in row)
    body = "".join("<tr>" + cells(r, "td") + "</tr>" for r in rows)
    return "<table><thead><tr>" + cells(head, "th") + "</tr></thead><tbody>" + body + "</tbody></table>"

def service_body(slug, articles):
    if slug in ("sondeqiqe", "video"):
        rows = [a for a in articles if (a.get("lang") or "az") == "az" and str(a.get("sourceUrl") or "").startswith("https://") and (slug == "sondeqiqe" or a.get("video"))]
        rows.sort(key=lambda a: a.get("publishedAt") or "", reverse=True)
        lis = "".join(f'<li><a href="{_xml(a.get("sourceUrl"))}" rel="noopener">{_xml(a.get("title"))}</a> <small>{_xml(a.get("source"))}</small></li>' for a in rows[:30])
        return f"<ul>{lis}</ul>" if lis else "<p>Hazırda xəbər yoxdur.</p>"
    if slug == "valyuta":
        items = _read_json(MARKETS_FILE, {}).get("items") or []
        rows = [(i.get("label"), f'{float(i["value"]):.{i.get("dec", 2)}f} {i.get("unit") or ""}'.strip(), i.get("src") or "", i.get("asOf") or (i.get("at") or "")[:10])
                for i in items if i.get("value") is not None]
        if not rows:
            return "<p>Məzənnə məlumatı hazırda yoxdur.</p>"
        ids = {i.get("id") for i in items if i.get("value") is not None}
        links = " · ".join(f'<a href="../mezenne/{s}/">{_xml(l)} məzənnəsi</a>' for s, mid, l, *_ in CURRENCY_PAGES if mid in ids)
        return _table(("Ad", "Qiymət", "Mənbə", "Tarix"), rows) + (f"<p>{links}</p>" if links else "")
    if slug == "cedvel":
        fb = _read_json(FOOTBALL_FILE, {})
        rows = [(t.get("pos"), t.get("team"), t.get("p"), t.get("w"), t.get("d"), t.get("l"), t.get("gf"), t.get("ga"), t.get("pts")) for t in fb.get("table") or []]
        title = f'<h2>{_xml(fb.get("league"))} {_xml(fb.get("season"))}</h2>' if fb.get("league") else ""
        return title + _table(("#", "Komanda", "O", "Q", "H", "M", "Vurulan", "Buraxılan", "Xal"), rows) if rows else "<p>Cədvəl hazırda yoxdur.</p>"
    road = [a for a in articles if (a.get("lang") or "az") == "az" and _ROAD_RX.search(a.get("title") or "")]
    road.sort(key=lambda a: a.get("publishedAt") or "", reverse=True)
    lis = "".join(f'<li><a href="{_xml(a.get("sourceUrl"))}" rel="noopener">{_xml(a.get("title"))}</a> <small>{_xml(a.get("source"))}</small></li>' for a in road[:20])
    return f'<p><a href="../../#/tixac">Canlı tıxac xəritəsi</a></p>{tixac_status()}<h2>Yol xəbərləri</h2><ul>{lis}</ul>'

# «Bakıda tıxac indi» səhifəsinin Google-un oxuduğu hissəsi: avtomatik ölçünün son nəticəsi (tixac.yml → «tixac» budağı).
# QIRMIZI XƏTT 1: xəbər axını gözləmir — fayl ən çoxu 5 dəqiqədə bir, 3 saniyəlik sorğu ilə alınır, xəta və gecikmə səhifəni
# ölçüsüz yazır. 3 saatdan köhnə ölçü (gecə) yazılmır.
TIXAC_URL = "https://raw.githubusercontent.com/8ulduz/8ulduz/tixac/tixac.json"
TIXAC_CACHE = CACHE_DIR / "tixac.json"
TIXAC_LEVEL = {"sixtixac": "sıx tıxac", "tixac": "tıxac", "leng": "hərəkət ləngdir", "serbest": "hərəkət sərbəstdir", "?": "ölçülməyib"}

def _tixac_doc(now=None):
    now = now or time.time()
    try:
        if not TIXAC_CACHE.exists() or now - TIXAC_CACHE.stat().st_mtime > 300:
            CACHE_DIR.mkdir(exist_ok=True)
            raw = fetch(f"{TIXAC_URL}?t={int(now) // 300}", timeout=3)
            json.loads(raw)
            _write_atomic(TIXAC_CACHE, raw.decode("utf-8"), encoding="utf-8")
    except Exception as e:
        print("  ! tıxac ölçüsü:", type(e).__name__)
    return _read_json(TIXAC_CACHE, {})

def tixac_status(doc=None, now=None):
    try:
        d = _tixac_doc(now) if doc is None else doc
        at = datetime.datetime.fromisoformat(str(d.get("updatedAt") or "").replace("Z", "+00:00"))
        now_dt = datetime.datetime.fromtimestamp(now or time.time(), datetime.timezone.utc)
        if not (datetime.timedelta(0) <= now_dt - at < datetime.timedelta(hours=3)):
            return ""
        clock = at.astimezone(BAKU).strftime("%H:%M")
        rows = [(w[0], TIXAC_LEVEL.get(w[1], w[1]), (w[2] + " km") if w[1] in ("tixac", "sixtixac") else "") for w in d.get("watch") or [] if len(w) >= 3]
        ev = "".join(f'<li>{_xml(datetime.datetime.fromtimestamp(e["t"] / 1000, BAKU).strftime("%H:%M"))} — {_xml(e.get("text"))}</li>'
                     for e in (d.get("events") or [])[:10] if isinstance(e.get("t"), (int, float)))
        out = ""
        zl = [z for z in d.get("rayons") or [] if len(z) >= 3 and isinstance(z[1], int)]
        if zl:  # 35 marşrut, bütün rayonlar (2026-11-14)
            head = f"Bakıda tıxaclı küçə: {int(d.get('jammed') or 0)} (ölçülən {int(d.get('counted') or 0)} küçədən). " if d.get("counted") else ""
            out += (f"<h2>Rayonlar üzrə tıxac balı ({clock})</h2><p>{head}Bal 0–10: rayonun ölçülən yollarında tıxaclı hissənin payı.</p>"
                    + _table(("Rayon", "Bal", "Tıxac"), [(z[0], f"{z[1]}/10", (z[2] + " km") if z[2] != "0,0" else "") for z in zl]))
        out += f"<h2>Səkkiz əsas yolun vəziyyəti ({clock})</h2>" + (_table(("Yol", "Vəziyyət", "Tıxac"), rows) if rows else "")
        out += f"<h2>Avtomatik xəbərlər</h2><ul>{ev}</ul>" if ev else ""
        return out + "<p><small>Avtomatik ölçü: Mapbox tıxac məlumatı, 8ulduz.az hesablaması. Pik saatlarda 6 dəqiqədən bir yenilənir.</small></p>"
    except Exception as e:
        print("  ! tıxac səhifəsi:", type(e).__name__)
        return ""

def write_sections(articles, stories=()):
    try:
        titles = _story_titles(stories, articles)
    except Exception as e:
        print("  ! bölmə keçidləri:", type(e).__name__, e)
        titles = {}
    for slug, label, desc in SECTIONS:
        d = SECTIONS_DIR / slug
        d.mkdir(parents=True, exist_ok=True)
        _write_atomic(d / "index.html", section_page(slug, label, desc, articles, stories=stories, titles=titles), encoding="utf-8")
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

# ------------------------------------------- namaz, hava və məzənnə səhifələri ---
# Sahibin qərarı (2026-11-13, «Bəli, qur»): Google-da hər gün axtarılan sorğuların (namaz vaxtı, hava, dollar məzənnəsi)
# öz ünvanı olsun. Səhifələr bolme/ altındadır (pipeline.sh main-ə bu qovluğu yazır), tətbiqi yükləmir: bir HTML, daxili CSS.
# Şəbəkə sorğusu yalnız yavaş dövrədədir (update_city_data); səhifələr write_public-də saxlanmış məlumatdan yazılır.
# Şəhər siyahısı assets/app.js CITIES ilə eynidir (tests/xidmet-sehifeleri.test.cjs).
CITIES = [("Bakı", 40.4093, 49.8671), ("Sumqayıt", 40.5897, 49.6686), ("Gəncə", 40.6828, 46.3606), ("Mingəçevir", 40.77, 47.0286),
          ("Şirvan", 39.937, 48.929), ("Naxçıvan", 39.2089, 45.4122), ("Lənkəran", 38.7529, 48.85), ("Şəki", 41.1919, 47.1706),
          ("Quba", 41.3611, 48.5133), ("Xaçmaz", 41.459, 48.802), ("Şamaxı", 40.631, 48.641), ("İsmayıllı", 40.785, 48.15),
          ("Qəbələ", 40.98, 47.86), ("Oğuz", 41.071, 47.465), ("Zaqatala", 41.63, 46.64), ("Balakən", 41.726, 46.404),
          ("Qax", 41.418, 46.92), ("Şuşa", 39.758, 46.75), ("Ağdam", 39.993, 46.93), ("Füzuli", 39.604, 47.15),
          ("Cəbrayıl", 39.399, 47.03), ("Kəlbəcər", 40.106, 46.045), ("Laçın", 39.638, 46.546), ("Zəngilan", 39.088, 46.65),
          ("Qubadlı", 39.344, 46.58), ("Tovuz", 40.992, 45.628), ("Göygöl", 40.585, 46.306), ("Yevlax", 40.617, 47.15),
          ("Bərdə", 40.375, 47.126), ("Ağsu", 40.57, 48.4), ("Kürdəmir", 40.335, 48.16), ("Ucar", 40.52, 47.65),
          ("Göyçay", 40.65, 47.74), ("Ağdaş", 40.65, 47.48), ("Zərdab", 40.22, 47.71), ("İmişli", 39.87, 48.06),
          ("Saatlı", 39.93, 48.37), ("Sabirabad", 40.01, 48.48), ("Salyan", 39.596, 49), ("Neftçala", 39.376, 49.247),
          ("Hacıqabul", 40.04, 48.94), ("Biləsuvar", 39.46, 48.55), ("Masallı", 39.034, 48.665), ("Astara", 38.501, 48.875),
          ("Lerik", 38.775, 48.415), ("Yardımlı", 38.908, 48.24)]
NAMAZ_FILE = OUT_DIR / "namaz.json"   # ayda bir dəfə dəyişir: repoda qalır ki, yeni iş 46 sorğunu təkrar etməsin
HAVA_CACHE = CACHE_DIR / "hava.json"
NAMAZ_FETCH_MAX = 8                   # bir yavaş dövrədə ən çoxu bu qədər şəhər; ilk xəta dövrəni saxlayır
HAVA_EVERY = 55 * 60
PRAY_LABELS = (("Fajr", "Sübh"), ("Sunrise", "Günəş"), ("Dhuhr", "Zöhr"), ("Asr", "Əsr"), ("Maghrib", "Məğrib"), ("Isha", "İşa"))
AZ_MONTH_NAMES = ("yanvar", "fevral", "mart", "aprel", "may", "iyun", "iyul", "avqust", "sentyabr", "oktyabr", "noyabr", "dekabr")
AZ_WEEKDAYS = ("bazar ertəsi", "çərşənbə axşamı", "çərşənbə", "cümə axşamı", "cümə", "şənbə", "bazar")
# ünvan, markets.json id-si, ad, tam ad, kod, id-dəki nominal, çevirmə cədvəlinin məbləğləri
CURRENCY_PAGES = [
    ("dollar", "USD", "Dollar", "ABŞ dolları", "USD", 1, (1, 5, 10, 50, 100, 500, 1000, 5000)),
    ("avro", "EUR", "Avro", "avro", "EUR", 1, (1, 5, 10, 50, 100, 500, 1000, 5000)),
    ("rubl", "RUB100", "Rubl", "Rusiya rublu", "RUB", 100, (100, 500, 1000, 5000, 10000, 50000, 100000)),
    ("lire", "TRY100", "Lirə", "Türkiyə lirəsi", "TRY", 100, (100, 500, 1000, 5000, 10000, 50000)),
    ("yuan", "CNY", "Yuan", "Çin yuanı", "CNY", 1, (1, 10, 100, 500, 1000, 5000)),
]
SUBPAGE_DIRS = ("namaz", "hava", "mezenne")
_SLUG_TR = str.maketrans({"ə": "e", "Ə": "e", "ı": "i", "İ": "i", "ö": "o", "Ö": "o", "ü": "u", "Ü": "u",
                          "ş": "s", "Ş": "s", "ç": "c", "Ç": "c", "ğ": "g", "Ğ": "g"})

def city_slug(name):
    return re.sub(r"[^a-z0-9]+", "-", str(name).translate(_SLUG_TR).lower()).strip("-")

def _locative(name):
    """«Bakıda», «Gəncədə»: şəkilçi son saitə uyğunlaşır."""
    for ch in reversed(str(name).lower()):
        if ch in "aıou":
            return name + "da"
        if ch in "eəiöü":
            return name + "də"
    return name + "da"

def _baku_now(now=None):
    if now is None:
        return datetime.datetime.now(BAKU)
    if isinstance(now, (int, float)):
        return datetime.datetime.fromtimestamp(now, BAKU)
    return now.astimezone(BAKU) if now.tzinfo else now.replace(tzinfo=BAKU)

def _az_date(d, weekday=True):
    text = f"{d.day} {AZ_MONTH_NAMES[d.month - 1]} {d.year}"
    return f"{text}, {AZ_WEEKDAYS[d.weekday()]}" if weekday else text

def _month_days(year, month):
    nxt = datetime.date(year + month // 12, month % 12 + 1, 1)
    return (nxt - datetime.date(year, month, 1)).days

def wx_label(code):
    """assets/app.js wxCode ilə eyni adlar."""
    c = int(code)
    if c <= 3:
        return ("Açıq", "Əsasən açıq", "Qismən buludlu", "Buludlu")[max(c, 0)]
    if c in (45, 48):
        return "Duman"
    if 51 <= c <= 57:
        return "Çiskin"
    if 61 <= c <= 67 or 80 <= c <= 82:
        return "Yağışlı"
    if 71 <= c <= 77 or c in (85, 86):
        return "Qarlı"
    if c >= 95:
        return "İldırımlı"
    return "Dəyişkən"

def _deg(v):
    v = int(v)
    return f"{'+' if v > 0 else ''}{v}°"

def parse_namaz_month(doc):
    """Aladhan /calendar cavabı → {gün: [Sübh, Günəş, Zöhr, Əsr, Məğrib, İşa]}; yarımçıq gün atılır."""
    out = {}
    for row in (doc or {}).get("data") or []:
        try:
            day = int(row["date"]["gregorian"]["day"])
            out[day] = [re.match(r"\s*(\d{2}:\d{2})", row["timings"][key]).group(1) for key, _ in PRAY_LABELS]
        except Exception:
            continue
    return out

def _namaz_rows(saved, month, slug):
    """Saxlanmış ayın sətirləri, yalnız tamdırsa (hər gün 6 vaxt)."""
    year, mon = (int(x) for x in month.split("-"))
    rows = ((saved or {}).get(month) or {}).get(slug)
    ok = (isinstance(rows, list) and len(rows) == _month_days(year, mon)
          and all(isinstance(r, list) and len(r) == 6 and all(re.fullmatch(r"\d{2}:\d{2}", str(t)) for t in r) for r in rows))
    return rows if ok else None

def update_namaz(now=None, fetcher=None):
    """Cari ayın (25-dən sonra növbəti ayın da) cədvəli, şəhər başına ayda bir sorğu. Üsul saytdakı vidcetlə eynidir (method=13)."""
    now = _baku_now(now)
    months = [f"{now.year}-{now.month:02d}"]
    if now.day >= 25:
        nxt = now.date().replace(day=1) + datetime.timedelta(days=32)
        months.append(f"{nxt.year}-{nxt.month:02d}")
    doc = _read_json(NAMAZ_FILE, {})
    saved = doc.get("months") if isinstance(doc, dict) and isinstance(doc.get("months"), dict) else {}
    data = {m: {slug: rows for slug, rows in (saved.get(m) or {}).items() if _namaz_rows(saved, m, slug)} for m in months}
    left = NAMAZ_FETCH_MAX
    for m in months:
        year, mon = (int(x) for x in m.split("-"))
        for name, lat, lon in CITIES:
            slug = city_slug(name)
            if slug in data[m]:
                continue
            if left <= 0:
                break
            left -= 1
            try:
                raw = (fetcher or fetch_json)(f"https://api.aladhan.com/v1/calendar/{year}/{mon}?latitude={lat}&longitude={lon}&method=13&timezonestring=Asia%2FBaku", timeout=8)
                rows = parse_namaz_month(raw)
                if len(rows) != _month_days(year, mon):
                    raise ValueError("ay yarımçıqdır")
                data[m][slug] = [rows[d] for d in sorted(rows)]
            except Exception as e:
                print("  ! namaz:", name, type(e).__name__, e)
                left = 0
                break
    if data != saved and (saved or any(data.values())):  # heç nə alınmayıbsa boş fayl yazılmır
        _write_atomic(NAMAZ_FILE, json.dumps({"method": "Aladhan, method=13 (Diyanet)", "months": data}, ensure_ascii=False, separators=(",", ":")))
    return data

def update_hava(now=None, fetcher=None):
    """Open-Meteo: 46 şəhər bir sorğuda, saatda bir dəfə. Alınmasa əvvəlki səhifələr qalır."""
    stamp = time.time() if now is None else float(now)
    cached = _read_json(HAVA_CACHE, {})
    if isinstance(cached, dict) and cached.get("cities") and 0 <= stamp - float(cached.get("at") or 0) < HAVA_EVERY:
        return cached
    url = ("https://api.open-meteo.com/v1/forecast?latitude=" + ",".join(str(c[1]) for c in CITIES) + "&longitude=" + ",".join(str(c[2]) for c in CITIES)
           + "&current=temperature_2m,apparent_temperature,relative_humidity_2m,weathercode,wind_speed_10m"
           "&daily=weather_code,temperature_2m_max,temperature_2m_min,precipitation_sum,wind_speed_10m_max"
           "&wind_speed_unit=ms&timezone=Asia%2FBaku&forecast_days=7")
    raw = (fetcher or fetch_json)(url, timeout=12)
    raw = [raw] if isinstance(raw, dict) else raw
    cities = {}
    for (name, _lat, _lon), x in zip(CITIES, raw or []):
        try:
            c, d = x["current"], x["daily"]
            days = [[str(d["time"][i]), int(d["weather_code"][i]), round(float(d["temperature_2m_max"][i])), round(float(d["temperature_2m_min"][i])),
                     round(float(d["precipitation_sum"][i] or 0), 1), round(float(d["wind_speed_10m_max"][i]))] for i in range(len(d["time"]))]
            if not days:
                continue
            cities[city_slug(name)] = {"t": round(float(c["temperature_2m"])), "f": round(float(c["apparent_temperature"])), "h": round(float(c["relative_humidity_2m"])),
                                       "w": round(float(c["wind_speed_10m"])), "c": int(c["weathercode"]), "at": str(c["time"]), "days": days}
        except Exception:
            continue
    if len(cities) < len(CITIES) // 2:
        raise ValueError(f"hava: yalnız {len(cities)} şəhər gəldi")
    doc = {"at": stamp, "cities": cities}
    _save_cache(HAVA_CACHE, doc)
    return doc

def update_city_data():
    """Yavaş addım: namaz cədvəli və hava. Biri alınmasa digəri işləyir; səhifələri write_public yazır."""
    for step in (update_namaz, update_hava):
        try:
            step()
        except Exception as e:
            print("  ! şəhər məlumatı:", step.__name__, type(e).__name__, e)

_STATIC_CSS = (":root{color-scheme:light dark}*{box-sizing:border-box}body{margin:0;font:16px/1.6 system-ui,sans-serif;background:#15233b;color:#d5deeb}"
               "main{max-width:760px;margin:auto;padding:20px 16px 48px}a{color:#d6bd80}h1{font-size:1.6rem;line-height:1.25;margin:.7em 0 .2em}h2{font-size:1.15rem;margin-top:28px}"
               "table{border-collapse:collapse;width:100%;font-variant-numeric:tabular-nums}th,td{padding:7px 6px;text-align:left;border-bottom:1px solid #3a4a66}"
               "tr.bu td{font-weight:700;background:#22365a}.kart{display:grid;grid-template-columns:repeat(auto-fit,minmax(92px,1fr));gap:8px;margin:14px 0}"
               ".kart div{border:1px solid #3a4a66;border-radius:10px;padding:10px;text-align:center}.kart b{display:block;font-size:1.35rem}.iri{font-size:2.1rem;font-weight:700;margin:.2em 0}"
               ".cedvel{overflow-x:auto}.sah a{display:inline-block;margin:0 12px 8px 0}.qeyd{opacity:.78;font-size:.88rem;font-weight:400}:focus-visible{outline:3px solid currentColor;outline-offset:3px}"
               "@media(prefers-color-scheme:light){body{background:#fff8d8;color:#172b4d}a{color:#19385f}th,td,.kart div{border-color:#d9cf9f}tr.bu td{background:#f3e7a8}}")
# Xidmət işçisi (sw.js cachedShell) səhifənin saxlanmış nüsxəsini dərhal verir: dünənki nüsxədə «bu gün» köhnə olardı.
# Skript ayın cədvəlindən Bakı vaxtı ilə bugünkü sətri tapıb yuxarıdakı bloku ona görə düzəldir. Şəbəkə sorğusu yoxdur.
_NAMAZ_JS = ('(function(){var d=new Date(Date.now()+144e5).toISOString().slice(0,10),r=document.querySelector(\'tr[data-d="\'+d+\'"]\');if(!r)return;'
             'var o=document.querySelector("tr.bu");if(o)o.className="";r.className="bu";var b=document.querySelectorAll("#bugun b");'
             'for(var i=0;i<b.length;i++)b[i].textContent=r.cells[i+1].textContent;var g=document.getElementById("gun");if(g)g.textContent=r.getAttribute("data-t")})()')

def _static_page(path, title, desc, h1, body, crumbs=(), script=""):
    """bolme/<path> üçün tam səhifə. crumbs: [(ad, bolme/ altındakı yol)] — baş səhifə ilə bu səhifə arasındakılar."""
    url = f"{SITE}bolme/{path}"
    up = "../" * (path.count("/") + 1)
    trail = [("8ulduz", SITE)] + [(n, f"{SITE}bolme/{p}") for n, p in crumbs] + [(h1, url)]
    ld = json.dumps({"@context": "https://schema.org", "@type": "BreadcrumbList", "itemListElement": [
        {"@type": "ListItem", "position": i, "name": n, "item": u} for i, (n, u) in enumerate(trail, 1)]}, ensure_ascii=False).replace("</", "<\\/")
    script_src = "script-src 'sha256-" + base64.b64encode(hashlib.sha256(script.encode("utf-8")).digest()).decode() + "'; " if script else ""
    back = "".join(f' › <a href="{up}bolme/{_xml(p)}">{_xml(n)}</a>' for n, p in crumbs)
    return ("<!doctype html>\n<html lang=\"az\">\n<head>\n<meta charset=\"utf-8\">\n<meta name=\"viewport\" content=\"width=device-width, initial-scale=1\">\n"
            f"<meta http-equiv=\"Content-Security-Policy\" content=\"default-src 'none'; style-src 'unsafe-inline'; {script_src}img-src 'self'; base-uri 'none'; form-action 'none'\">\n"
            f"<title>{_xml(title)} — 8ulduz</title>\n<meta name=\"description\" content=\"{_xml(desc)}\">\n<link rel=\"canonical\" href=\"{url}\">\n"
            "<meta name=\"theme-color\" content=\"#15233b\">\n<meta property=\"og:type\" content=\"website\"><meta property=\"og:site_name\" content=\"8ulduz\">"
            f"<meta property=\"og:title\" content=\"{_xml(title)}\"><meta property=\"og:description\" content=\"{_xml(desc)}\"><meta property=\"og:url\" content=\"{url}\">"
            f"<meta property=\"og:locale\" content=\"az_AZ\"><meta property=\"og:image\" content=\"{SITE}assets/og-default.png\"><meta name=\"twitter:card\" content=\"summary_large_image\">\n"
            f"<link rel=\"icon\" href=\"{up}assets/icon-192.png\" sizes=\"192x192\">\n<script type=\"application/ld+json\">{ld}</script>\n<style>{_STATIC_CSS}</style>\n</head>\n<body><main>\n"
            f"<nav aria-label=\"Yol\"><a href=\"{up}\">8ulduz — son xəbərlər</a>{back}</nav>\n<h1>{_xml(h1)}</h1>\n{body}\n"
            f"<h2>8ulduz-da</h2>\n<p class=\"sah\"><a href=\"{up}\">Son xəbərlər</a><a href=\"{up}bolme/namaz/\">Namaz vaxtları</a><a href=\"{up}bolme/hava/\">Hava proqnozu</a>"
            f"<a href=\"{up}bolme/valyuta/\">Valyuta məzənnəsi</a><a href=\"{up}bolme/cedvel/\">Premyer Liqa cədvəli</a><a href=\"{up}icmal/\">Günün icmalı</a></p>\n"
            + (f"<script>{script}</script>\n" if script else "") + "</main></body>\n</html>\n")

def _write_page(path, page):
    """Dəyişməyən səhifə yenidən yazılmır: faylın vaxtı sitemap-də həqiqi dəyişmə tarixidir."""
    target = SECTIONS_DIR / path / "index.html"
    try:
        if target.read_text(encoding="utf-8") == page:
            return False
    except Exception:
        pass
    target.parent.mkdir(parents=True, exist_ok=True)
    _write_atomic(target, page, encoding="utf-8")
    return True

def _city_links(skip=""):
    return '<p class="sah">' + "".join(f'<a href="../{city_slug(n)}/">{_xml(n)}</a>' for n, _a, _b in CITIES if city_slug(n) != skip) + "</p>"

_NAMAZ_NOTE = ('<p class="qeyd">Vaxtlar Bakı vaxtı ilədir və şəhərin koordinatına görə Diyanət üsulu ilə hesablanır (Aladhan, saytımızdakı namaz göstəricisi ilə eyni mənbə). '
               "Qafqaz Müsəlmanları İdarəsinin təqvimindən fərqlənə bilər.</p>")

def namaz_city_page(name, rows, today):
    slug, month = city_slug(name), AZ_MONTH_NAMES[today.month - 1]
    now = rows[today.day - 1]
    cards = "".join(f"<div>{_xml(lab)}<b>{t}</b></div>" for (_k, lab), t in zip(PRAY_LABELS, now))
    lines = []
    for i, r in enumerate(rows, 1):
        d = today.replace(day=i)
        mark = ' class="bu"' if i == today.day else ""
        lines.append(f'<tr data-d="{d.isoformat()}" data-t="{_xml(_az_date(d))}"{mark}><td>{i} {month}</td>' + "".join(f"<td>{t}</td>" for t in r) + "</tr>")
    head = "<tr><th>Gün</th>" + "".join(f"<th>{_xml(lab)}</th>" for _k, lab in PRAY_LABELS) + "</tr>"
    body = (f'<p><b id="gun">{_xml(_az_date(today))}</b></p>\n<div class="kart" id="bugun">{cards}</div>\n'
            f'<h2>{_xml(name)}: {month} {today.year} namaz təqvimi</h2>\n<div class="cedvel"><table><thead>{head}</thead><tbody>{"".join(lines)}</tbody></table></div>\n'
            f'{_NAMAZ_NOTE}\n<p><a href="../../hava/{slug}/">{_xml(_locative(name))} hava proqnozu</a></p>\n<h2>Başqa şəhərlər</h2>\n{_city_links(slug)}')
    desc = f"{_locative(name)} bu gün namaz vaxtları: " + ", ".join(f"{lab} {t}" for (_k, lab), t in zip(PRAY_LABELS, now)) + f". {month.capitalize()} ayının tam təqvimi."
    return _static_page(f"namaz/{slug}/", f"{name} namaz vaxtları bu gün — {_az_date(today, False)}", desc, f"{name} namaz vaxtları", body,
                        crumbs=[("Namaz vaxtları", "namaz/")], script=_NAMAZ_JS)

def write_namaz_pages(now=None):
    today = _baku_now(now).date()
    month = f"{today.year}-{today.month:02d}"
    doc = _read_json(NAMAZ_FILE, {})
    saved = doc.get("months") if isinstance(doc, dict) and isinstance(doc.get("months"), dict) else {}
    ready = []
    for name, _lat, _lon in CITIES:
        rows = _namaz_rows(saved, month, city_slug(name))
        if rows:
            _write_page(f"namaz/{city_slug(name)}/", namaz_city_page(name, rows, today))
            ready.append((name, rows[today.day - 1]))
    if not ready:
        return 0
    head = "<tr><th>Şəhər</th>" + "".join(f"<th>{_xml(lab)}</th>" for _k, lab in PRAY_LABELS) + "</tr>"
    lines = "".join(f'<tr><td><a href="{city_slug(n)}/">{_xml(n)}</a></td>' + "".join(f"<td>{t}</td>" for t in r) + "</tr>" for n, r in ready)
    body = (f"<p><b>{_xml(_az_date(today))}</b>. Azərbaycanın şəhər və rayonları üzrə bugünkü namaz vaxtları. Şəhərin adına toxunanda ayın tam təqvimi açılır.</p>\n"
            f'<div class="cedvel"><table><thead>{head}</thead><tbody>{lines}</tbody></table></div>\n{_NAMAZ_NOTE}')
    first = ready[0]
    desc = (f"Bu gün namaz vaxtları, {_az_date(today, False)}: {first[0]} — " + ", ".join(f"{lab} {t}" for (_k, lab), t in zip(PRAY_LABELS, first[1]))
            + f". {len(ready)} şəhər və rayon üzrə cədvəl.")
    _write_page("namaz/", _static_page("namaz/", f"Namaz vaxtları bu gün — {_az_date(today, False)}", desc, "Namaz vaxtları", body))
    return len(ready)

def _hava_fresh(row, today):
    """Proqnozun bu gündən başlayan günləri; köhnə keşdə dünənki gün atılır."""
    return [d for d in row.get("days") or [] if isinstance(d, list) and len(d) == 6 and str(d[0]) >= today.isoformat()]

def hava_city_page(name, row, today):
    slug, loc = city_slug(name), _locative(name)
    days = _hava_fresh(row, today)
    stamp = str(row.get("at") or "")
    try:
        when = f"{_az_date(datetime.date.fromisoformat(stamp[:10]), False)}, {stamp[11:16]}"
    except Exception:
        when = stamp
    lines = []
    for d in days:
        day = datetime.date.fromisoformat(d[0])
        label = "Bu gün" if day == today else "Sabah" if day == today + datetime.timedelta(days=1) else AZ_WEEKDAYS[day.weekday()].capitalize()
        lines.append(f"<tr><td>{label}, {day.day} {AZ_MONTH_NAMES[day.month - 1]}</td><td>{wx_label(d[1])}</td><td>{_deg(d[2])}</td><td>{_deg(d[3])}</td><td>{d[4]:g} mm</td><td>{d[5]} m/san</td></tr>")
    body = (f'<p class="iri">{_deg(row["t"])} <span class="qeyd">{wx_label(row["c"])}</span></p>\n'
            f'<div class="kart"><div>Hiss olunan<b>{_deg(row["f"])}</b></div><div>Külək<b>{int(row["w"])} m/san</b></div><div>Rütubət<b>{int(row["h"])}%</b></div></div>\n'
            f'<p class="qeyd">Ölçü vaxtı: {_xml(when)} (Bakı vaxtı). Səhifə saatda bir yenilənir.</p>\n'
            f"<h2>{_xml(loc)} {len(days)} günlük hava proqnozu</h2>\n"
            f'<div class="cedvel"><table><thead><tr><th>Gün</th><th>Hava</th><th>Gündüz</th><th>Gecə</th><th>Yağıntı</th><th>Külək</th></tr></thead><tbody>{"".join(lines)}</tbody></table></div>\n'
            '<p class="qeyd">Mənbə: Open-Meteo model proqnozu. Rəsmi xəbərdarlıq deyil; rəsmi proqnozu Milli Hidrometeorologiya Xidməti verir.</p>\n'
            f'<p><a href="../../namaz/{slug}/">{_xml(name)} namaz vaxtları</a></p>\n<h2>Başqa şəhərlər</h2>\n{_city_links(slug)}')
    t0 = days[0]
    desc = (f"{loc} hava: {_deg(row['t'])}, {wx_label(row['c']).lower()}, külək {int(row['w'])} m/san. Bu gün gündüz {_deg(t0[2])}, gecə {_deg(t0[3])}. "
            f"{len(days)} günlük proqnoz.")
    return _static_page(f"hava/{slug}/", f"{loc} hava — bu gün və {len(days)} günlük proqnoz", desc, f"{loc} hava", body, crumbs=[("Hava proqnozu", "hava/")])

def write_hava_pages(now=None):
    today = _baku_now(now).date()
    doc = _read_json(HAVA_CACHE, {})
    cities = doc.get("cities") if isinstance(doc, dict) and isinstance(doc.get("cities"), dict) else {}
    ready = []
    for name, _lat, _lon in CITIES:
        row = cities.get(city_slug(name))
        try:
            if not row or not _hava_fresh(row, today):
                continue
            _write_page(f"hava/{city_slug(name)}/", hava_city_page(name, row, today))
            ready.append((name, row, _hava_fresh(row, today)[0]))
        except Exception as e:
            print("  ! hava səhifəsi:", name, type(e).__name__, e)
    if not ready:
        return 0
    lines = "".join(f'<tr><td><a href="{city_slug(n)}/">{_xml(n)}</a></td><td>{_deg(r["t"])}</td><td>{wx_label(r["c"])}</td><td>{_deg(d[2])}</td><td>{_deg(d[3])}</td><td>{int(r["w"])} m/san</td></tr>'
                    for n, r, d in ready)
    body = (f"<p><b>{_xml(_az_date(today))}</b>. Azərbaycanın şəhər və rayonlarında hava: son ölçülən temperatur və bugünkü proqnoz. Şəhərin adına toxunanda həftəlik proqnoz açılır.</p>\n"
            f'<div class="cedvel"><table><thead><tr><th>Şəhər</th><th>İndi</th><th>Hava</th><th>Gündüz</th><th>Gecə</th><th>Külək</th></tr></thead><tbody>{lines}</tbody></table></div>\n'
            '<p class="qeyd">Mənbə: Open-Meteo model proqnozu, saatda bir yenilənir. Rəsmi xəbərdarlıq deyil.</p>')
    n0, r0, _d0 = ready[0]
    desc = f"Azərbaycanda hava bu gün, {_az_date(today, False)}: {_locative(n0)} {_deg(r0['t'])}, {wx_label(r0['c']).lower()}. {len(ready)} şəhər və rayon üzrə həftəlik proqnoz."
    _write_page("hava/", _static_page("hava/", f"Hava proqnozu — Azərbaycan, {_az_date(today, False)}", desc, "Hava proqnozu", body))
    return len(ready)

def _spaced(value, dec=2):
    return f"{value:,.{dec}f}".replace(",", " ")

def currency_page(spec, item, others=()):
    slug, _mid, label, full, code, nominal, amounts = spec
    rate = float(item["value"]) / nominal               # bir vahidin manatla qiyməti
    as_of = str(item.get("asOf") or (item.get("at") or "")[:10])
    try:
        day_text = _az_date(datetime.date.fromisoformat(as_of), False)
    except Exception:
        day_text = as_of
    change = float(item.get("change") or 0)
    moved = "dəyişməyib" if not change else f"{abs(change):.4f} AZN {'bahalaşıb' if change > 0 else 'ucuzlaşıb'}"
    to_azn = "".join(f"<tr><td>{_spaced(a, 0)} {code}</td><td>{_spaced(rate * a)} AZN</td></tr>" for a in amounts)
    from_azn = "".join(f"<tr><td>{_spaced(a, 0)} AZN</td><td>{_spaced(a / rate)} {code}</td></tr>" for a in (1, 5, 10, 50, 100, 500, 1000, 5000))
    lead = f"{nominal} {code} = {float(item['value']):.4f} AZN"
    links = "".join(f'<a href="../{s}/">{_xml(l)} məzənnəsi</a>' for s, l in others if s != slug)
    body = (f'<p class="iri">{lead}</p>\n<p>Azərbaycan Mərkəzi Bankının <b>{_xml(day_text)}</b> tarixinə rəsmi məzənnəsi. Əvvəlki bülletenlə müqayisədə {nominal} {_xml(full)} {moved}.</p>\n'
            f'<h2>{code} → AZN</h2>\n<div class="cedvel"><table><thead><tr><th>{_xml(label)}</th><th>Manat</th></tr></thead><tbody>{to_azn}</tbody></table></div>\n'
            f'<h2>AZN → {code}</h2>\n<div class="cedvel"><table><thead><tr><th>Manat</th><th>{_xml(label)}</th></tr></thead><tbody>{from_azn}</tbody></table></div>\n'
            '<p class="qeyd">Mənbə: Azərbaycan Mərkəzi Bankı (AMB). Bankların və mübadilə məntəqələrinin alış-satış qiyməti rəsmi məzənnədən fərqlənir.</p>\n'
            f'<h2>Başqa valyutalar</h2>\n<p class="sah">{links}<a href="../../valyuta/">Bütün məzənnələr, neft və qızıl</a></p>')
    desc = f"{label} məzənnəsi bu gün: {lead} (AMB, {day_text}). {code}–AZN çevirmə cədvəli."
    return _static_page(f"mezenne/{slug}/", f"{label} məzənnəsi bu gün — {lead}", desc, f"{label} məzənnəsi", body, crumbs=[("Valyuta məzənnəsi", "valyuta/")])

def write_currency_pages():
    items = {i.get("id"): i for i in _read_json(MARKETS_FILE, {}).get("items") or [] if isinstance(i, dict)}
    ready = [spec for spec in CURRENCY_PAGES if (items.get(spec[1]) or {}).get("value")]
    others = [(spec[0], spec[2]) for spec in ready]
    for spec in ready:
        try:
            _write_page(f"mezenne/{spec[0]}/", currency_page(spec, items[spec[1]], others))
        except Exception as e:
            print("  ! məzənnə səhifəsi:", spec[0], type(e).__name__, e)
    return len(ready)

def write_subpages(now=None):
    """Namaz, hava və məzənnə səhifələri. Şəbəkə sorğusu yoxdur; biri alınmasa digərləri yazılır."""
    done = {}
    for key, step in (("namaz", lambda: write_namaz_pages(now)), ("hava", lambda: write_hava_pages(now)), ("məzənnə", write_currency_pages)):
        try:
            done[key] = step()
        except Exception as e:
            print("  ! xidmət alt səhifələri:", key, type(e).__name__, e)
    print("Xidmət alt səhifələri:", ", ".join(f"{k} {v}" for k, v in done.items()))
    return done

def subpage_locs():
    """Sitemap üçün: yazılmış alt səhifələr və faylın son dəyişmə vaxtı."""
    out = []
    for kind in SUBPAGE_DIRS:
        base = SECTIONS_DIR / kind
        for page in sorted(base.glob("index.html")) + sorted(base.glob("*/index.html")):
            rel = page.parent.relative_to(SECTIONS_DIR).as_posix() + "/"
            out.append((f"{SITE}bolme/{rel}", _iso_utc(datetime.datetime.fromtimestamp(page.stat().st_mtime, datetime.timezone.utc))))
    return out

def _iso_utc(dt):
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=datetime.timezone.utc)
    return dt.astimezone(datetime.timezone.utc).isoformat(timespec="seconds")

def _own_page_rows(articles):
    """Lentdəki öz xəbərlər (mənbə «8ULDUZ»), ünvanı saytın öz xeber/<id>/ səhifəsi olanlar. Öz sətir lentə yalnız səhifəsi
    saytda olandan sonra düşür (read_own_rows), ona görə sayt xəritəsinə yazıla bilər: Google onu oradan tapır."""
    return [a for a in articles or [] if a.get("source") == OWN_SOURCE and a.get("id")
            and a.get("sourceUrl") == f"{SITE}xeber/{a['id']}/"]

def write_sitemap(stories=None, digests=(), own=()):
    now = _iso_utc(datetime.datetime.now(datetime.timezone.utc))
    locs = [SITE] + [f"{SITE}bolme/{slug}/" for slug, _l, _d in [*SECTIONS, *SERVICE_PAGES]]
    body = ['<?xml version="1.0" encoding="UTF-8"?>',
            '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">']
    for loc in locs:
        body.append(f"<url><loc>{_xml(loc)}</loc><lastmod>{now}</lastmod><changefreq>hourly</changefreq></url>")
    # Sabit məlumat səhifələrinə hər dövrədə saxta dəyişmə tarixi yazılmır.
    for path in ("haqqinda/", "mexfilik/"):
        body.append(f"<url><loc>{_xml(SITE + path)}</loc></url>")
    try:
        for loc, when in subpage_locs():
            body.append(f"<url><loc>{_xml(loc)}</loc><lastmod>{when}</lastmod></url>")
    except Exception as e:
        print("  ! sitemap alt səhifələri:", type(e).__name__, e)
    if digests:
        body.append(f"<url><loc>{SITE}icmal/</loc><lastmod>{_iso_utc(datetime.datetime.fromtimestamp(digests[0]['at'], datetime.timezone.utc))}</lastmod></url>")
    for e in list(digests)[:60]:
        when = _iso_utc(datetime.datetime.fromtimestamp(e["at"], datetime.timezone.utc)) if e.get("at") else str(e.get("date") or "") + "T00:00:00+00:00"
        body.append(f"<url><loc>{SITE}icmal/{e['slug']}/</loc><lastmod>{when}</lastmod></url>")
    newest = sorted((stories or {}).items(), key=lambda kv: kv[1][0], reverse=True)[:STORY_SITEMAP_MAX]
    for sid, row in newest:
        day = _iso_utc(datetime.datetime.fromtimestamp(row[0], datetime.timezone.utc))
        body.append(f"<url><loc>{SITE}xeber/{sid}/</loc><lastmod>{day}</lastmod></url>")
    listed = {sid for sid, _row in newest}
    for a in own or ():  # öz xəbərlərin səhifələri (_own_page_rows): ümumi səhifə siyahısında yoxdur, onları dərc hissəsi yazır
        dt = _parse_dt(a.get("publishedAt"))
        if dt and a["id"] not in listed:
            listed.add(a["id"])
            body.append(f"<url><loc>{_xml(a['sourceUrl'])}</loc><lastmod>{_iso_utc(dt)}</lastmod></url>")
    body.append("</urlset>\n")
    _write_atomic(SITEMAP_FILE, "".join(body), encoding="utf-8")

def write_news_sitemap(articles, stories=None, now=None):
    """Google News sitemap: son 48 saat, ən çoxu 1000 ünvan. Səhifəsi olan xəbərlər: ümumi xəbər səhifələri (stories) və
    lentdəki öz xəbərlər (_own_page_rows; onların səhifəsini dərc hissəsi yazır)."""
    now = now or datetime.datetime.now(datetime.timezone.utc)
    if isinstance(now, (int, float)):
        now = datetime.datetime.fromtimestamp(now, datetime.timezone.utc)
    if now.tzinfo is None:
        now = now.replace(tzinfo=datetime.timezone.utc)
    if stories is None:
        stories = read_story_index()
    cutoff = now - datetime.timedelta(hours=48)
    own = {a["id"] for a in _own_page_rows(articles)}
    rows = []
    for a in articles or []:
        sid = str(a.get("id") or "")
        if sid not in (stories or {}) and sid not in own:
            continue
        dt = _parse_dt(a.get("publishedAt"))
        if not dt or dt < cutoff or dt > now + datetime.timedelta(minutes=15):
            continue
        title = re.sub(r"\s+", " ", str(a.get("title") or "")).strip()
        if not title:
            continue
        rows.append((dt, sid, title))
    rows.sort(key=lambda x: x[0], reverse=True)
    parts = ['<?xml version="1.0" encoding="UTF-8"?>',
             '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9" xmlns:news="http://www.google.com/schemas/sitemap-news/0.9">']
    for dt, sid, title in rows[:1000]:
        parts.append("<url><loc>" + _xml(f"{SITE}xeber/{sid}/") + "</loc><news:news>"
                     "<news:publication><news:name>8 Ulduz</news:name><news:language>az</news:language></news:publication>"
                     "<news:publication_date>" + _xml(_iso_utc(dt)) + "</news:publication_date>"
                     "<news:title>" + _xml(title) + "</news:title></news:news></url>")
    parts.append("</urlset>\n")
    _write_atomic(NEWS_SITEMAP_FILE, "".join(parts), encoding="utf-8")

def write_robots():
    _write_atomic(ROBOTS_FILE, 
        "User-agent: *\nDisallow: /tests/\nDisallow: /docs/\nDisallow: /android/\nDisallow: /.github/\nDisallow: /updater.py\n"
        "Disallow: /reader_content.py\nDisallow: /content_policy.py\nDisallow: /README.md\nAllow: /\n\nSitemap: " + SITE + "sitemap.xml\n"
        "Sitemap: " + SITE + "sitemap-news.xml\n"
        "Sitemap: " + SITE + "sitemap-movzu.xml\n",  # rayon/ və idman/ mövzu səhifələri (.github/scripts/topics.cjs, pipeline publish_main)
        encoding="utf-8")

def write_public():
    articles, _ = content_policy.enforce(read_feed())  # feed.xml və bölmə səhifələri də qapıdan keçir
    write_feed(articles)
    try:  # xəbər səhifələri alınmasa bölmələr və sitemap köhnə qaydada yazılır
        stories = write_story_pages(articles)
    except Exception as e:
        print("  ! xəbər səhifələri:", type(e).__name__, e)
        stories = {}
    try:  # günün icmalı: alınmasa qalan hər şey köhnə qaydada
        digests = write_digest(articles, stories)
    except Exception as e:
        print("  ! icmal:", type(e).__name__, e)
        digests = []
    try:
        write_sections(articles, stories)
    except Exception as e:
        print("  ! bölmə səhifələri:", type(e).__name__, e)
    try:  # namaz, hava, məzənnə: sitemap-dən əvvəl, ünvanları ora düşsün
        write_subpages()
    except Exception as e:
        print("  ! xidmət alt səhifələri:", type(e).__name__, e)
    try:
        write_sitemap(stories, digests, _own_page_rows(articles))
    except Exception as e:
        print("  ! sitemap:", type(e).__name__, e)
    try:  # alınmasa xəbər faylı artıq yazılıb
        write_news_sitemap(articles, stories)
    except Exception as e:
        print("  ! sitemap-news:", type(e).__name__, e)
    try:
        write_robots()
    except Exception as e:
        print("  ! robots:", type(e).__name__, e)

_OG_META = re.compile(r"<meta\b[^>]*>", re.I)
_OG_KEY = re.compile(r"""(?:property|name)\s*=\s*["']([^"']+)["']""", re.I)
_OG_CONTENT = re.compile(r"""content\s*=\s*["']([^"']+)["']""", re.I)
_OG_NAMES = {"og:image", "og:image:url", "twitter:image", "twitter:image:src"}

_LD_IMG = re.compile(r'"image"\s*:\s*(?:\{[^}]*?"url"\s*:\s*)?"(https?://[^"]+)"', re.I)
_IMG_SRC = re.compile(r'<link[^>]+rel=["\']image_src["\'][^>]+href=["\']([^"\']+)', re.I)

_PAGE_IMG = re.compile(r"""<img\b[^>]*?\bsrc\s*=\s*["']([^"']+)""", re.I)
_NOT_PHOTO = re.compile(r"\.(?:gif|svg)(?:\?|$)|icon|avatar|banner|sprite|pixel|^data:", re.I)

def _own_card_img(text, url, skip=()):
    """og:image saytın loqosudursa (Lent.az): səhifədə bu xəbərin öz kartı axtarılır, yəni məhz bu ünvana keçid olan şəkil.
    Səhifənin ilk başlığı olmaz: Lent.az hər səhifədə eyni önə çıxan xəbəri göstərir, xəbər yanlış şəkil alırdı (2026-10-31)."""
    path = urllib.parse.urlparse(url).path
    if len(path) < 12:
        return ""
    # Lent.az lentdə «.../basliq-40694450/1», kartda başqa başlıqla «.../basliq-2-40694450» yazır: ünvanda nömrə varsa o müqayisə olunur.
    number = re.search(r"-(\d{5,})(?:/\d+)?/?$", path)
    target = r"""[^"']*-""" + number.group(1) + r"(?:/\d+)?/?" if number else r"""(?:https?://[^/"']+)?""" + re.escape(path)
    for card in re.finditer(r"""<a\b[^>]*href=["']""" + target + r"""["'][^>]*>(.*?)</a>""", text, re.S):
        src = _PAGE_IMG.search(card.group(1))
        img = _abs_img(src.group(1), url) if src else ""
        if img and img not in skip and not _is_generic_img(img) and not _NOT_PHOTO.search(img):
            return img
    return ""

# AZƏRTAC: og:image ümumi loqodur (social.jpg), xəbərin öz fotosu (img.news-img) və ya videonun kadrı (.news-video img data-src)
# isə səhifədədir (2026-11-08, sahib: «ən önəmli AZƏRTAC xəbərində şəkil yoxdur»). Yalnız azertag.az: başqa saytda bu siniflər
# oxşar xəbər kartında ola bilər, yanlış şəkil şəkilsizlikdən pisdir. «?v=...» hər sorğuda dəyişir: atılır (keş və proksi bir ünvan görsün).
_BODY_IMG = re.compile(r"""<img\b[^>]*\bclass\s*=\s*["'][^"']*\bnews-img\b[^>]*>|<div\b[^>]*\bclass\s*=\s*["'][^"']*\bnews-video\b.{0,1200}?(<img\b[^>]*>)""", re.I | re.S)
_ANY_SRC = re.compile(r"""\b(?:data-src|src)\s*=\s*["']([^"']+)""", re.I)

def _body_img(text, base, skip=()):
    if (urllib.parse.urlparse(base or "").hostname or "").lower().removeprefix("www.") != "azertag.az":
        return ""
    for m in _BODY_IMG.finditer(text):
        for src in _ANY_SRC.findall(m.group(1) or m.group(0)):
            img = _abs_img(re.sub(r"\?v=\w+$", "", src), base)
            if img and img not in skip and not _is_generic_img(img) and not _NOT_PHOTO.search(img):
                return img
    return ""

def _og_from_html(raw, base, skip=()):
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
    # Sporx og:image-də nisbi ünvan verir, əsl şəkil isə başqa hostdadır: tam ünvanlı namizəd üstündür.
    for c in sorted(cands, key=lambda c: not c.startswith(("http://", "https://", "//"))):
        img = _abs_img(c, base)
        if img and img not in skip and not _is_generic_img(img):
            return img
    return _body_img(text, base, skip) or _own_card_img(text, base, skip)

def _fetch_og(url, skip=()):
    """Şəkil ünvanı; səhifədə yoxdursa və ya sayt bizi buraxmırsa "" (403: tez-tez yoxlanmır), şəbəkə xətasında None (tezliklə yenidən)."""
    if not content_policy.safe_url(url):
        return ""
    try:
        req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "text/html,application/xhtml+xml"})
        with urllib.request.urlopen(req, timeout=6) as r:
            ctype = (r.headers.get("Content-Type") or "").lower()
            if ctype and "html" not in ctype and "xml" not in ctype:
                return ""
            return _og_from_html(r.read(300000), url, skip)
    except urllib.error.HTTPError as e:
        return None if e.code >= 500 else ""
    except Exception:
        return None

DEAD_IMG_KEEP = 2000   # lentdən çıxmış ölü şəkil ünvanı: xəbər lentə qayıdanda yenidən göstərilməsin
OG_KEEP_OUTSIDE = 400  # hazırda lentdə olmayan xəbərlərin şəkil cavabı: lent daralıb genişlənəndə xəbər geri qayıdır

def _image_dead(url):
    """Yalnız sayt özü «yoxdur» deyəndə: GitHub IP-sini bloklayan host brauzerdə açıla bilər."""
    try:
        req = urllib.request.Request(url, headers={"User-Agent": UA, "Range": "bytes=0-0"})
        with urllib.request.urlopen(req, timeout=4) as r:
            return "html" in (r.headers.get("Content-Type") or "").lower()
    except urllib.error.HTTPError as e:
        # 403/429/5xx: sayt bu dəfə cavab vermədi — «sağlam» kimi yadda saxlanmasın, növbəti dövrə yenə baxsın
        return True if e.code in (404, 410) else None
    except Exception:
        return None  # vaxt keçdi, şəbəkə xətası: bilinmir

def drop_dead_images(articles, limit=120):
    """Lentin verdiyi şəkil ölüdürsə (Modern.az: /file/articles/... 404) xəbər şəkilsiz sayılır, fill_og_images səhifədən tapır.
    Yalnız dəqiq cavab yadda qalır. Əvvəl vaxt keçməsi və 403 də «sağlam» kimi həmişəlik yazılırdı: o ünvan bir daha
    yoxlanmırdı və ölü şəkilli xəbər səhifənin şəklini heç vaxt almırdı. Ən təzə xəbərlərin şəkli birinci yoxlanır."""
    checked = _read_json(IMG_CHECK_FILE, {})
    rows = sorted((a for a in articles if a.get("imageUrl")), key=lambda a: a.get("publishedAt") or "", reverse=True)
    urls = set()
    todo = []
    for a in rows:
        u = a["imageUrl"] = fix_image_url(a["imageUrl"])
        if u not in urls:
            urls.add(u)
            if u not in checked and len(todo) < limit:
                todo.append(u)
    if todo:
        with ThreadPoolExecutor(max_workers=12) as ex:
            checked.update((u, r) for u, r in zip(todo, ex.map(_image_dead, todo)) if r is not None)
    # Xəbərin ölü şəkli silinəndən sonra ünvan siyahıda olmur, amma xəbər lentdən çıxıb qayıdanda lent onu yenə verir.
    dead = [u for u, is_dead in checked.items() if is_dead and u not in urls][-DEAD_IMG_KEEP:]
    _save_cache(IMG_CHECK_FILE, {**dict.fromkeys(dead, True), **{u: checked[u] for u in urls if u in checked}})
    for a in articles:
        if checked.get(a.get("imageUrl")):
            a["imageUrl"] = None
    return articles

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
    if not content_policy.safe_url(url):
        return ""
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
        if v and _is_logo(v, freq.get(v, 0)):
            cache[k] = ""
    logos = {v for v, n in freq.items() if _is_logo(v, n)}
    todo = []
    for a in articles:
        url = a.get("sourceUrl") or ""
        if not url or a.get("imageUrl") or a.get("source") == OWN_SOURCE:  # öz xəbərin şəkli varsa sətrindədir: səhifəsindəki og:image saytın ümumi lövhəsidir
            continue
        if url in cache:
            if cache[url]:
                a["imageUrl"] = cache[url]
                continue
            # Təzə xəbər 15 dəqiqədən çox gözləmir: əvvəl yazılmış 6 saatlıq qeyd də qısalır (2026-11-08, AZƏRTAC-ın gec yüklənən fotosu).
            if _fresh_story(a, now_ts):
                retry_after[url] = min(retry_after.get(url, 0), now_ts + 900)
            # Temporary network failures must not hide photos forever.
            if retry_after.get(url, 0) > now_ts:
                continue
        todo.append(a)
    batch, found, err = todo[:limit], [], ""
    try:
        if batch:
            with ThreadPoolExecutor(max_workers=12) as ex:
                found = list(ex.map(lambda a: _fetch_og(a.get("sourceUrl") or "", logos), batch))
            for img in found:
                if img:
                    freq[img] = freq.get(img, 0) + 1
            for a, img in zip(batch, found):
                # Şəbəkə xətası və ya yeni üzə çıxan loqo: xəbər lentdə cəmi 3-4 saat qalır, 6 saat gözləsə şəkilsiz çıxıb gedir.
                # Təzə xəbər də: AZƏRTAC fotonu xəbərdən 30-60 dəqiqə sonra yükləyir; 6 saatlıq qeyd 15 dəqiqəlik təzə yoxlamanı (fill_fresh_og) da bağlayırdı.
                soon = img is None or _is_logo(img, freq.get(img, 0)) or _fresh_story(a, now_ts)
                if _is_logo(img, freq.get(img, 0)):
                    img = ""  # bu dövrədə də eyni şəkil təkrarlanır: loqo
                cache[a["sourceUrl"]] = img or ""
                if img:
                    retry_after.pop(a["sourceUrl"], None)
                else:
                    retry_after[a["sourceUrl"]] = now_ts + (900 if soon else 6 * 3600)
                if img:
                    a["imageUrl"] = img
    except Exception as e:
        err = f"{type(e).__name__}: {str(e)[:80]}"
        print("  ! og:image:", err)
    keep = {a.get("sourceUrl") for a in articles if a.get("sourceUrl")}
    # Qruplaşma lenti 150 xəbər daraldır, növbəti dövrə köhnə xəbərlərlə yenidən doldurur. Cavab silinsəydi həmin xəbərlər
    # şəkilsiz qayıdır, hər yavaş dövrədə eyni 50 səhifə yenidən sorğulanırdı (2026-10-31).
    keep |= set([k for k in cache if k not in keep][-OG_KEEP_OUTSIDE:])
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

# Sahib (2026-11-06): «şəkilsiz kart olmamalıdır». Təzə xəbərlərin üçdə biri lentdən şəkilsiz gəlir, şəkli yavaş dövrə
# (4-5 dəqiqədən bir) tapırdı: xəbər 5-15 dəqiqə şəkilsiz görünürdü. Bu yoxlama link prosesində 30 saniyədən bir işləyir (--og):
# yalnız son FRESH_OG_AGE_S içindəki şəkilsiz xəbərlər, ən yenisi birinci. Sürətli dövrə şəbəkə gözləmir, apply_og_cache nəticəni götürür.
FRESH_OG_LIMIT, FRESH_OG_AGE_S, FRESH_OG_RETRY_S = 24, 3 * 3600, 60


def _fresh_story(a, now_ts):
    """Xəbər son FRESH_OG_AGE_S içindədir: şəkli tapılmayıbsa 15 dəqiqədən bir yenidən baxılır."""
    try:
        age = now_ts - datetime.datetime.fromisoformat(str(a.get("publishedAt")).replace("Z", "+00:00")).timestamp()
    except (ValueError, TypeError, OverflowError):
        return False
    return 0 <= age <= FRESH_OG_AGE_S


def fill_fresh_og(now=None, limit=FRESH_OG_LIMIT):
    now_ts = now or time.time()
    cache = _read_json(OG_FILE, {})
    cache = cache if isinstance(cache, dict) else {}
    meta = cache.get("_meta") if isinstance(cache.get("_meta"), dict) else {}
    retry = meta.get("retryAfter") if isinstance(meta.get("retryAfter"), dict) else {}
    freq = {}
    rows = read_feed()
    for v in [v for k, v in cache.items() if k != "_meta"] + [a.get("imageUrl") for a in rows]:
        if isinstance(v, str) and v:
            freq[v] = freq.get(v, 0) + 1
    logos = {v for v, n in freq.items() if _is_logo(v, n)}
    def age(a):
        try:
            return now_ts - datetime.datetime.fromisoformat(str(a.get("publishedAt")).replace("Z", "+00:00")).timestamp()
        except ValueError:
            return FRESH_OG_AGE_S + 1
    todo = []
    for a in rows:
        url = a.get("sourceUrl") or ""
        if not url or a.get("imageUrl") or cache.get(url) or retry.get(url, 0) > now_ts or not 0 <= age(a) <= FRESH_OG_AGE_S:
            continue
        if url in cache and url not in retry:
            continue  # səhifədə şəkil yoxdur (yavaş dövrə 6 saat sonra yenə baxır)
        todo.append(a)
    todo = sorted(todo, key=age)[:limit]
    if not todo:
        return 0
    with ThreadPoolExecutor(max_workers=12) as ex:
        found = list(ex.map(lambda a: _fetch_og(a["sourceUrl"], logos), todo))
    new, again = {}, {}
    for a, img in zip(todo, found):
        if img and not _is_logo(img, freq.get(img, 0) + 1) and not _is_generic_img(img):
            new[a["sourceUrl"]] = img
        else:
            again[a["sourceUrl"]] = now_ts + (FRESH_OG_RETRY_S if img is None else 900)
    # Yavaş dövrə də bu faylı yazır: oxu-yaz arası qısa olsun, onun tapdıqları itməsin.
    latest = _read_json(OG_FILE, {})
    latest = latest if isinstance(latest, dict) else {}
    m = latest.get("_meta") if isinstance(latest.get("_meta"), dict) else {}
    r = dict(m.get("retryAfter") if isinstance(m.get("retryAfter"), dict) else {})
    for url, img in new.items():
        latest[url] = img
        r.pop(url, None)
    for url, t in again.items():
        if not latest.get(url):
            r[url] = t
    latest["_meta"] = {**m, "retryAfter": r, "fresh": {"at": datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds"), "batch": len(todo), "found": len(new)}}
    try:
        OUT_DIR.mkdir(exist_ok=True)
        _write_atomic(OG_FILE, json.dumps(latest, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    except Exception as e:
        print("  ! og (təzə):", type(e).__name__)
    if new:
        print(f"og:image (təzə): {len(new)}/{len(todo)}")
    return len(new)

def write_status(ok=True, successful=0, total=0, stats=None):
    """Son cəhd və son uğur ayrıdır; uğursuz cəhd köhnə xəbəri təzə göstərmir. stats: seçim sayları (diaqnostika)."""
    now = datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds")
    try:
        previous = json.loads(STATUS_FILE.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        previous = {}
    OUT_DIR.mkdir(exist_ok=True)
    status = {"checkedAt": now if ok else previous.get("checkedAt"), "attemptedAt": now, "ok": ok,
              "successfulSources": successful, "totalSources": total,
              "degraded": ok and total - successful > total * FEED_PAUSE_MAX_SHARE, "stats": stats or previous.get("stats")}
    if os.environ.get("LATEST_LANG_FILES"):  # yalnız dil fayllarını live-ə yazan pipeline.sh qoyur: sayt bayraqsız ümumi latest.json çəkir (köhnə iş 404 verməsin)
        status["langs"] = list(FEED_LANGS)
    if os.environ.get("NEWS_LANG_FILES"):  # tam lent dil üzrə (write_news): sayt news.<dil>.json-u yalnız bayraqla istəyir, yoxsa news.json
        status["newsLangs"] = list(NEWS_LANGS)
    if os.environ.get("SOCIAL_LOOP"):  # social.json dəqiqəlik live-ə gedir (pipeline.sh): sayt onu yalnız bu möhür dəyişəndə çəkir
        rev = _read_json(SOCIAL_FILE, {})
        rev = rev.get("rev") if isinstance(rev, dict) else None
        if rev:
            status["social"] = rev
    _write_atomic(STATUS_FILE, json.dumps(status, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
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


PREZ_KEEP, PREZ_TODAY_MAX = 120, 90

def select_prez(rows, now):
    """Zuğulba üçün lentdə qalan prezident xəbərləri (ən yenidən köhnəyə sıralı siyahı).
    Hədd 120 idi və təkrarları da sayırdı: 2026-11-08-də eyni müraciət 30 saytdan gəldi, 120 bugünkü sətirlə doldu, əvvəlki
    günlərin xəbərləri lentdən çıxdı, blok 44-ə çatmadı (sahib: «zuğulba niyə son 40 yazır»). İndi: son 24 saatın xəbərləri
    təkrarı ilə qalır (sayt onları bir karta birləşdirir, mənbələri göstərir) amma ən çox 90 sətir; əvvəlki günlərdən hər
    xəbərin bir nüsxəsi qalır (eyni başlığın təkrarı düşür) ki, 120-lik yerin ən azı 30-u köhnə günlərə çatsın."""
    fresh = now - datetime.timedelta(hours=24)
    today, older, seen = [], [], set()
    for a in rows:
        dt = _parse_dt(a.get("publishedAt"))
        if dt is not None and dt >= fresh:
            if len(today) < PREZ_TODAY_MAX:
                today.append(a)
            continue
        key = _norm_title(a.get("title"))
        if key in seen:
            continue
        seen.add(key)
        older.append(a)
    return (today + older)[:PREZ_KEEP]


def main(fast=False):
    marks, tick = {}, time.time()
    def mark(name):
        nonlocal tick
        marks[name] = round(time.time() - tick, 1)
        tick = time.time()
        if fast:
            print("  ·", name, marks[name], flush=True)
    old = read_feed()  # bölünmüş lent (news.json + dil faylları, write_news) bir siyahıda
    prev_articles = [dict(a) for a in old]
    old = [a for a in old if a.get("source") != OWN_SOURCE]  # öz sətir əvvəlki lentdən yox, hər dövrə öz faylından gəlir (aşağıda merge_own_rows)
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
    # Əvvəlki dövrələrdən qalan eyni nömrəli cütlər (slug dəyişmiş eyni xəbər): yalnız ən yenisi qalır.
    keyed, dedup = set(), []
    for a in old:
        k = story_key(a.get("sourceUrl"))
        if k in keyed:
            continue
        if k:
            keyed.add(k)
        dedup.append(a)
    old = dedup
    seen = {a["sourceUrl"] for a in old}
    if fast:  # başqa xəbərin mənbəsi kimi birləşmiş keçid yenidən «yeni» sayılmasın
        seen |= {alt.get("sourceUrl") for a in old for alt in a.get("alts") or []}
    old_by_url = {a["sourceUrl"]: a for a in old}
    # Eyni mənbənin eyni nömrəli xəbəri (başlıq və slug dəyişəndə) yeni qeyd sayılmasın: nömrə üzrə köhnə qeyd tapılır (story_key).
    old_by_key = {}
    for a in old:
        for u in [a.get("sourceUrl"), *(alt.get("sourceUrl") for alt in a.get("alts") or [])]:
            k = story_key(u)
            if k and k not in old_by_key:
                old_by_key[k] = a
    new_items, errors, empty, new_keys, retired = [], [], [], set(), set()
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
                    # Match TV şəkli lentə sonra əlavə edir: artıq görülmüş xəbər şəkilsiz qalmasın (şəbəkə sorğusu yoxdur).
                    known = old_by_url.get(it["link"])
                    if known is not None and not known.get("imageUrl") and it.get("image"):
                        known["imageUrl"] = it["image"]
                    continue
                key = story_key(it["link"])
                if key and key in old_by_key:
                    # Eyni xəbər yeni başlıq və slug ilə: qeyd birdir, başlığı yenilənir, keçid və nömrə (paylaşma) qalır.
                    known, title = old_by_key[key], _plain(it["title"], title=True)
                    seen.add(it["link"])
                    # Açar qeydin əlavə mənbəsinə (alts) aid ola bilər: onda yeni başlıq o mənbənindir. Əvvəl əsas mənbənin
                    # (başqa saytın) başlığı və xülasəsi üstünə yazılırdı: kartda X saytının başlığı Y saytının adı və keçidi ilə.
                    mine = story_key(known.get("sourceUrl")) == key
                    row = known if mine else next((alt for alt in known.get("alts") or [] if story_key(alt.get("sourceUrl")) == key), None)
                    if row is None or not title or title == row.get("title"):
                        if mine and not known.get("imageUrl") and it.get("image"):
                            known["imageUrl"] = it["image"]
                        continue
                    # QIRMIZI XƏTT 2: yeni başlıq da təzə xəbərin keçdiyi süzgəclərdən keçir (əvvəl bu budaq onlardan yan keçirdi və
                    # sətir bir dövrə lentdə qalırdı). Keçməyən əsas qeyd lentdən çıxır, əlavə mənbə qeyddən çıxır.
                    if is_negative_about_leadership(it["title"], it["description"], source) or \
                            foreign_about_azerbaijan(source, known.get("category"), title, it.get("description") or ""):
                        if mine:
                            retired.add(id(known))
                        else:
                            known["alts"] = [alt for alt in known["alts"] if alt is not row]
                        continue
                    if mine:
                        known["title"] = title
                        known["summary"] = _short(_plain(it["description"])) or known.get("summary", "")
                        if not known.get("imageUrl") and it.get("image"):
                            known["imageUrl"] = it["image"]
                    else:  # yeni siyahı: prev_articles köhnə alts siyahısını saxlayır, yerində dəyişsə «dəyişiklik yoxdur» sayılıb yazılmazdı
                        known["alts"] = [dict(alt, title=title) if alt is row else alt for alt in known["alts"]]
                    continue
                if key:
                    if key in new_keys:  # eyni dövrədə iki lentdən (əsas və bölmə RSS-i) fərqli slug ilə
                        continue
                    new_keys.add(key)
                if floor and it.get("pubDate") and _older_than(it["pubDate"], floor):
                    continue
                if source in source_floor and it.get("pubDate") and _older_than(it["pubDate"], source_floor[source]):
                    continue
                if it["link"] in region_links:  # Regionlar səhifəsindən gələcək; lentin xülasəsi ona verilir
                    region_desc[it["link"]] = it.get("description") or ""
                    continue
                seen.add(it["link"])
                # Oxunmayan tarix də «tarixsiz»dir. Əvvəl belə sətir hər dövrə «indi» damğası alırdı: mənbə limitinə çatanda
                # keçən dəqiqənin sətirləri lentdən çıxıb növbəti dövrədə «yeni» kimi qayıdırdı (CNN Türk, NTV Spor, 2026-11-12).
                if _pub_dt(it.get("pubDate")) is None:
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
    old = sorted((a for a in old if id(a) not in retired), key=lambda a: a.get("publishedAt", ""), reverse=True)
    uniq, dseen = [], set()
    per_src, world_count, sport_count = {}, {}, 0  # world_count dil üzrədir (MAX_WORLD_LANG)
    # Tarixə görə birgə sıralama. Əvvəl «yeni» (bu dövrədə ilk dəfə görülən) xəbərlər köhnələrdən qabaq gəlirdi;
    # limitdən kənarda qalan köhnə xəbərlər növbəti dövrədə yenidən «yeni» sayılıb siyahını hər dəfə dəyişirdi
    # (813-dən yalnız ~50 xəbər dövrədən dövrəyə qalırdı; og keşi və qruplar daim sıfırlanırdı).
    for a in sorted(new_items + old, key=lambda x: x.get("publishedAt") or "", reverse=True):
        if a["sourceUrl"] in dseen:
            continue
        # Zuğulba xronikası mənbə limitinə düşmür: öz limiti var (60 gün, 120 xəbər, aşağıda). Əvvəl APA/Report-un köhnə
        # Zuğulba xəbərləri yeni adi xəbərlərin hesabına lentdən çıxırdı, blok 44-ə çatmırdı (sahib 2026-11-07).
        if a.get("category") == "prezident":
            dseen.add(a["sourceUrl"]); uniq.append(a)
            continue
        n, is_sport = per_src.get(a.get("source"), 0), a.get("source") in content_policy.SPORT_SOURCES
        is_world = a.get("source") in WORLD_SOURCES and not is_sport
        lang = a.get("lang") or "en"
        if n >= source_cap(a.get("source")) or (is_world and world_count.get(lang, 0) >= MAX_WORLD_LANG.get(lang, MAX_WORLD_LANG["en"])) or (is_sport and sport_count >= MAX_WORLD_SPORT):
            continue
        per_src[a.get("source")] = n + 1
        if is_world:
            world_count[lang] = world_count.get(lang, 0) + 1
        sport_count += is_sport
        dseen.add(a["sourceUrl"]); uniq.append(a)
    # Prezident bölməsi ümumi limitdən asılı deyil: rəsmi xronika (60 gün) həmişə saxlanılır.
    # Əvvəl yalnız 800-dən kənarda qalanlar əlavə olunurdu; siyahı 800-dən qısa olanda heç nə əlavə olunmurdu.
    prez_items = select_prez([a for a in uniq if a["category"] == "prezident"], now_utc)
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
        if u and (_is_logo(u, img_count.get(u, 0)) or _is_generic_img(u)):
            a["imageUrl"] = None
        if not a.get("imageUrl"):
            for alt in a.get("alts") or []:
                if alt.get("imageUrl") and not _is_logo(alt["imageUrl"], img_count.get(alt["imageUrl"], 0)) and not _is_generic_img(alt["imageUrl"]):
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
                print(f"  ⊘ {reason}: {a.get('source')!r} {a.get('sourceUrl')!r}", flush=True)  # !r: lentdəki sətir sonu işin əmri olmasın
    try:
        articles = drop_dead_links(articles, dead_links(len(articles)))
    except Exception as e:  # QIRMIZI XƏTT 1: yoxlama alınmasa xəbər əvvəlki kimi yazılır
        print("  ! ölü link:", type(e).__name__, flush=True)
    articles = merge_own_rows(articles, read_own_rows())  # öz xəbərlər (yalnız OZ_DERC=1; fayl oxunur): qapıdan əvvəl qatılır, qapıdan onlar da keçir
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
    try:  # paylaşma səhifələri lentdən əvvəl: lentin dediyi hər /x/ID səhifəsi var (xəta axını dayandırmır)
        write_share_pages(articles)
    except Exception as e:
        print("  ! paylaşma səhifələri:", type(e).__name__, flush=True)
    try:  # QIRMIZI XƏTT 1: bu fayl alınmasa sayt tam lentlə açılır, xəbər axını dayanmır
        write_first(articles, data["updatedAt"])
    except Exception as e:
        print("  ! first.json:", type(e).__name__, flush=True)
    write_news(data)
    try:  # Google News sitemap hər dövrədə; alınmasa lent artıq yazılıb
        write_news_sitemap(articles)
    except Exception as e:
        print("  ! sitemap-news:", type(e).__name__, e)
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
    if "--social" in sys.argv:  # pipeline.sh social_loop: rəsmi hesabların yazıları dəqiqədə bir (sahib 2026-11-08)
        update_social()
        return 0
    if "--links" in sys.argv:
        check_links()
        return 0
    if "--og" in sys.argv:
        fill_fresh_og()
        return 0
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
