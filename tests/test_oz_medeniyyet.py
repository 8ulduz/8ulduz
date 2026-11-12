"""Mədəniyyət və bilik xəbərləri (oz_medeniyyet.py, mərhələ 2): afişa, kino, Vikipediyada ən çox oxunanlar, yubileylər.
Şəbəkə yoxdur: tests/fixtures/oz_medeniyyet/ — mənbələrin 2026-11-10 – 2026-11-12 tarixli real cavablarından kəsiklər."""
import contextlib
import datetime
import io
import json
import pathlib
import unittest
import urllib.error
import urllib.parse
from unittest.mock import patch

import oz_medeniyyet as m
import oz_xeber as ox

ROOT = pathlib.Path(__file__).resolve().parent.parent
FIX = ROOT / "tests" / "fixtures" / "oz_medeniyyet"
D = datetime.date
KEYS = {"kind", "key", "title", "lead", "body", "credit", "link", "topic", "slot", "worth"}
LEADER = "Prezident İlham Əliyev"
UA = "8ulduz-bot/1.0 (+https://8ulduz.az)"
WIKI_HOSTS = ("wikipedia.org", "wikidata.org", "wikimedia.org")


def at(y, mo, d, hh, mm=0):
    return datetime.datetime(y, mo, d, hh, mm, tzinfo=m.BAKU)


def raw(name):
    return (FIX / name).read_bytes()


def load(name):
    return json.loads(raw(name).decode("utf-8"))


def info_doc(url, extra=None):
    """action=query cavabı (formatversion=2) istənən adlar üçün: real cavablardan (ext-*.json), yoxdursa lentin öz
    təsviri və girişindən. extra: {ad: (təsvir, giriş)} — testin öz səhifələri."""
    titles = urllib.parse.parse_qs(urllib.parse.urlsplit(url).query)["titles"][0].split("|")
    known = {p["title"]: p for name in ("ext-2026-10.json", "ext-leads.json", "ext-2026-11-11.json")
             for p in load(name)["query"]["pages"]}
    feed = {}
    for name in ("wiki-feed-2026-11-09.json", "wiki-feed-2026-11-10.json", "wiki-feed-2026-11-11-ready.json"):
        for a in load(name)["mostread"]["articles"]:
            feed[a["titles"]["normalized"]] = a
    pages = []
    for t in titles:
        t = t.replace("_", " ")
        if extra and t in extra:
            pages.append({"title": t, "description": extra[t][0], "extract": extra[t][1]})
        elif t in known:
            pages.append(known[t])
        elif t in feed:
            pages.append({"title": t, "description": feed[t].get("description", ""), "extract": feed[t].get("extract", "")})
        else:
            pages.append({"title": t, "missing": True})
    return json.dumps({"batchcomplete": True, "query": {"pages": pages}}).encode("utf-8")


def it_url(cat, a, b=None, page=1):
    return m.IT_API.format(cat=cat, a=a, b=b or a, page=page)


INFO = m.API_URL + "action=query*"


def table(**over):
    """Bütün mənbələrin saxta cavabları: ünvan -> bayt."""
    t = {}
    for day in (10, 11, 12, 13):
        for cat in ("theatre", "concerts"):
            t[it_url(cat, D(2026, 11, day))] = raw(f"it-{cat}-2026-11-{day}-1.json")
    sat, sun = D(2026, 11, 14), D(2026, 11, 15)
    for p in (1, 2, 3):
        t[it_url("theatre", sat, sun, p)] = raw(f"it-theatre-2026-11-14-15-{p}.json")
    t[it_url("concerts", sat, sun)] = raw("it-concerts-2026-11-14-15-1.json")
    t[it_url("exhibitions", sat, sun)] = raw("it-exhibitions-2026-11-14-15-1.json")
    t[m.CINEMA_URL] = raw("cinema-2026-11-10.html")
    for day in (9, 10, 11):
        t[m.FEED_URL.format(D(2026, 11, day))] = raw(f"wiki-feed-2026-11-{day:02d}.json")
    t[m.TOP_URL.format(2026, 10)] = raw("top-2026-10.json")
    t[INFO] = info_doc
    for day in (9, 10):
        t[m.sparql_url(D(2026, 11, day))] = raw(f"wdqs-2026-11-{day:02d}.json")
        t[ox.WIKI_API.format(f"{day}_noyabr")] = raw(f"day-{day}_noyabr.json")
    t.update(over)
    return t


class Fake:
    """Saxta fetch: ünvan -> bayt, Exception və ya funksiya(ünvan). «*» ilə bitən açar ünvanın başlanğıcıdır.
    Cədvəldə olmayan ünvan xəta verir. Çağırışlar calls-dadır: (ünvan, timeout, başlıqlar)."""

    def __init__(self, tbl=None):
        self.table = table() if tbl is None else dict(tbl)
        self.calls = []

    def __call__(self, url, timeout=None, headers=None):
        self.calls.append((url, timeout, dict(headers or {})))
        hit = self.table.get(url)
        if hit is None:
            for k, v in self.table.items():
                if k.endswith("*") and url.startswith(k[:-1]):
                    hit = v
                    break
        if hit is None:
            raise urllib.error.URLError("testdə bu ünvan yoxdur")
        if isinstance(hit, Exception):
            raise hit
        return hit(url) if callable(hit) else hit

    @property
    def urls(self):
        return [c[0] for c in self.calls]


def text(item):
    return "\n".join([item["title"], item["lead"], *item["body"]])


def event(name, venue="Akademik Milli Dram Teatrı", hh=19, day=D(2026, 11, 12), eid=1, state=1, kind="theatre"):
    when = datetime.datetime(day.year, day.month, day.day, hh, 0, tzinfo=m.BAKU)
    return {"id": eid, "name": name, "when": when, "venue": venue, "cat": kind, "state": state, "kind": kind}


def wd(qid, name, born, desc="Azərbaycan bəstəkarı", occ="bəstəkar", sl=3, posn=0, dead="", title=None):
    b = {"p": {"value": "http://www.wikidata.org/entity/" + qid}, "name": {"value": name},
         "b": {"value": born + "T00:00:00Z"}, "sl": {"value": str(sl)}, "title": {"value": title or name},
         "occ": {"value": occ}, "posn": {"value": str(posn)}}
    if desc:
        b["desc"] = {"value": desc}
    if dead:
        b["dead"] = {"value": dead + "T00:00:00Z"}
    return b


def sparql(*bindings):
    return json.dumps({"results": {"bindings": list(bindings)}}).encode("utf-8")


class HelpersTest(unittest.TestCase):
    def test_number_suffix_follows_the_spoken_word(self):
        self.assertEqual(m.num_abl(70), "70-dən")       # yetmiş
        self.assertEqual(m.num_abl(690), "690-dan")     # doxsan
        self.assertEqual(m.num_abl(56), "56-dan")       # altı
        self.assertEqual(m.num_dat(690), "690-a")
        self.assertEqual(m.num_dat(62), "62-yə")        # iki
        self.assertEqual(m.num_dat(731), "731-ə")       # bir
        self.assertEqual(m.num_dat(1066), "1 066-ya")   # altı

    def test_quotes(self):
        self.assertEqual(m._q("Xanuma"), "«Xanuma»")
        self.assertEqual(m._q("“Uçan xalça” marionet kukla teatr tamaşası"), "«Uçan xalça» marionet kukla teatr tamaşası")
        self.assertEqual(m._q('"Pişiyin evi"'), "«Pişiyin evi»")
        self.assertEqual(m._q("İmroz&#039;da Bahar"), "«İmroz'da Bahar»")
        self.assertEqual(m._q("İblis və..."), "«İblis və...»")
        self.assertEqual(m._q("P.A.N.D.A."), "«P.A.N.D.A.»")

    def test_dates(self):
        self.assertEqual(m._days_loc(D(2026, 11, 14), D(2026, 11, 15)), "14 və 15 noyabrda")
        self.assertEqual(m._days_loc(D(2026, 10, 31), D(2026, 11, 1)), "31 oktyabr və 1 noyabrda")
        self.assertEqual(m._day_abl(D(2026, 11, 12)), "12 noyabrdan")
        self.assertEqual(m._day_abl(D(2026, 4, 3)), "3 apreldən")
        self.assertEqual(m._month_loc(10), "oktyabrda")
        self.assertEqual(m._month_loc(4), "apreldə")

    def test_iticket_time_is_utc_and_becomes_baku(self):
        when = m._utc("2026-11-12T15:00:00.000000Z")
        self.assertEqual((when.date(), when.hour, when.minute), (D(2026, 11, 12), 19, 0))
        self.assertEqual(m._utc("2026-11-12T21:30:00.000000Z").date(), D(2026, 11, 13))
        for bad in (None, "", "yox", "2026-13-45T10:00:00Z", 5):
            self.assertIsNone(m._utc(bad))

    def test_window(self):
        self.assertTrue(m._due(at(2026, 11, 12, 10, 0), "10:00"))
        self.assertTrue(m._due(at(2026, 11, 12, 10, 44), "10:00"))
        self.assertFalse(m._due(at(2026, 11, 12, 10, 45), "10:00"))
        self.assertFalse(m._due(at(2026, 11, 12, 9, 59), "10:00"))

    def test_net_asks_each_url_once_and_keeps_the_error(self):
        fake = Fake({"https://a.test/x": b"1", "https://a.test/y": urllib.error.URLError("yox")})
        net = m._net(fake)
        self.assertEqual(net("https://a.test/x", timeout=60), b"1")
        self.assertEqual(net("https://a.test/x"), b"1")
        for _ in range(2):
            with self.assertRaises(urllib.error.URLError):
                net("https://a.test/y")
        self.assertEqual(len(fake.calls), 2)
        self.assertEqual(net.count, 2)
        self.assertTrue(all(c[1] <= 15 for c in fake.calls))
        with self.assertRaises(LookupError):
            m._Net(None)("https://a.test/z")


class AfisaTest(unittest.TestCase):
    def test_today_from_real_responses(self):
        fake = Fake()
        item, why = m.afisa_day(m._net(fake), D(2026, 11, 12))
        self.assertEqual(why, "")
        self.assertEqual(item["key"], "afisa-2026-11-12")
        self.assertEqual(item["body"], [
            "19:00 — Akademik Milli Dram Teatrı: «Xanuma»",
            "19:00 — Azərbaycan Dövlət Akademik Filarmoniyası: «Qara Qarayev adına Azərbaycan Dövlət Kamera Orkestri»",
            "19:00 — Azərbaycan Dövlət Akademik Musiqili Teatrı: «Şahmaran»",
            "19:00 — Beynəlxalq Muğam Mərkəzi: «Leyla Noir və musiqi qrupu — Etno-caz»"])
        self.assertEqual(item["title"], "Bu gün Bakı səhnələrində: «Xanuma», «Şahmaran» və daha 2 tədbir")
        self.assertEqual(item["lead"], "iTicket-in afişasına görə, bu gün, 12 noyabrda, Bakının dövlət teatrlarında və konsert "
                                       "salonlarında tamaşalar göstəriləcək və konsertlər keçiriləcək.")
        self.assertTrue(KEYS <= set(item))
        self.assertTrue(item["worth"] and item["list"])
        self.assertEqual((item["slot"], item["credit"], item["topic"]), ("10:00", "iTicket.az", "mədəniyyət"))
        self.assertEqual(fake.urls, [it_url("theatre", D(2026, 11, 12)), it_url("concerts", D(2026, 11, 12))])
        blob = text(item)
        for banned in ("Candlelight", "Şam İşığında", "Show Gallery", "AZN", "₼", "bilet"):
            self.assertNotIn(banned, blob)

    def test_fewer_than_three_events_is_no_item(self):
        item, why = m.afisa_day(m._net(Fake()), D(2026, 11, 10))
        self.assertIsNone(item)
        self.assertIn("3-dən azdır", why)

    def test_venues(self):
        self.assertEqual(m._venue_rank("Akademik Milli Dram Teatrı"), 1)
        self.assertEqual(m._venue_rank("Azərbaycan Dövlət Pantomim Teatrı"), 3)
        self.assertEqual(m._venue_rank("Azərbaycan Dövlət Mahnı Teatrı"), 3)
        for other in ("Pray Teatrı", "Show Gallery", "Gəncə Dövlət Milli Dram Teatrı", "Şuşa Dövlət Musiqili Dram Teatrı",
                      "Cəlil Məmmədquluzadə adına Naxçıvan Dövlət Milli Dram Teatrı", "Azərbaycan Milli Xalça Muzeyi"):
            self.assertIsNone(m._venue_rank(other), other)
        self.assertEqual(m._venue_rank("Muzey Mərkəzi", True), 2)
        self.assertIsNone(m._venue_rank("Show Gallery", True))

    def test_events_that_are_never_listed(self):
        self.assertEqual(m._skip_event(event("Xanuma")), "")
        self.assertEqual(m._skip_event(event("Кармен история Хосе")), "adı kirillədir")
        self.assertEqual(m._skip_event(event("Şam İşığında Vals axşamı")), "kommersiya seriyası")
        self.assertEqual(m._skip_event(event("Stand-up show - Qadınlar üçün")), "kommersiya seriyası")
        self.assertEqual(m._skip_event(event("Xanuma", state=3)), "satış vəziyyəti bilinmir")
        self.assertEqual(m._skip_event(event("Xanuma", venue="Pray Teatrı")), "Bakının dövlət səhnəsi deyil")
        self.assertEqual(m._skip_event(event(LEADER + "ə həsr olunmuş gecə")), "rəhbərliyin adı keçir")
        self.assertEqual(m._skip_event(event("Mehriban Əliyevanın sərgisi")), "rəhbərliyin adı keçir")

    def test_leader_event_never_reaches_the_item(self):
        venues = list(m.STAGES)[:4]
        rows = [event(f"Tamaşa {i}", venue=v, eid=i) for i, v in enumerate(venues)]
        rows.append(event(LEADER + "ə həsr olunmuş konsert", venue=venues[0], eid=99))
        item, _ = m.afisa_item(D(2026, 11, 12), rows)
        self.assertTrue(item["worth"])
        self.assertEqual(len(item["body"]), 4)
        self.assertNotIn("Əliyev", text(item))

    def test_caps_dedupe_and_premiere(self):
        venues = list(m.STAGES)
        rows = [event(f"Tamaşa {i}", venue=venues[0], hh=12 + i, eid=i) for i in range(4)]
        rows += [event("Tamaşa 0", venue=venues[0], hh=12, eid=50)]            # eyni tədbir ikinci dəfə
        rows += [event(f"Konsert {i}", venue=v, eid=100 + i, kind="concerts") for i, v in enumerate(venues[3:11])]
        rows += [event("Əli və Nino – premyera", venue=venues[1], eid=77)]
        item, _ = m.afisa_item(D(2026, 11, 12), rows)
        self.assertEqual(len(item["body"]), m.AFISA_MAX)
        self.assertEqual(sum(venues[0] in line for line in item["body"]), m.PER_VENUE)
        self.assertEqual(len(set(item["body"])), len(item["body"]))
        self.assertIn(f"19:00 — {venues[1]}: «Əli və Nino» (premyera)", item["body"])
        self.assertIn("Afişada «Əli və Nino» premyera kimi qeyd olunub.", item["lead"])
        self.assertLessEqual(len(item["title"]), m.TITLE_MAX)
        self.assertEqual(item["body"], sorted(item["body"], key=lambda s: s[:5]))

    def test_other_days_events_are_ignored(self):
        rows = [event(f"Tamaşa {i}", venue=v, eid=i, day=D(2026, 11, 13)) for i, v in enumerate(list(m.STAGES)[:5])]
        item, why = m.afisa_item(D(2026, 11, 12), rows)
        self.assertIsNone(item)
        self.assertIn("0 tədbir", why)

    def test_garbage_and_errors(self):
        for bad in (None, [], {}, {"response": []}, load("it-422.json"), {"response": {"events": {"data": "x"}}}):
            with self.assertRaises(ValueError):
                m.it_events(bad)
        rows, more = m.it_events({"response": {"events": {"data": [None, {}, {"name": "A"}, {"name": "B", "venues": [{"name": "V"}],
                                                                      "event_starts_at": "yox"}]}}})
        self.assertEqual((rows, more), ([], False))
        day = D(2026, 11, 12)
        for bad in (b"<html>", b"{}", raw("it-422.json"), urllib.error.URLError("x"), TimeoutError()):
            item, why = m.afisa_day(m._net(Fake({it_url("theatre", day): bad, it_url("concerts", day): bad})), day)
            self.assertIsNone(item)
            self.assertIn("iTicket alınmadı", why)

    def test_weekend_from_real_responses(self):
        fake = Fake()
        item, why = m.hefte_days(m._net(fake), D(2026, 11, 14))
        self.assertEqual(why, "")
        self.assertEqual(item["key"], "afisa-hefte-2026-11-14")
        self.assertEqual(item["body"], [
            "Şənbə, 12:00 — Azərbaycan Dövlət Akademik Musiqili Teatrı: «İki küpəgirən qarı»",
            "Şənbə, 12:00 — Azərbaycan Dövlət Milli Gənc Tamaşaçılar Teatrı: «Çirkin ördək balası»",
            "Şənbə, 17:00 — Azərbaycan Dövlət Akademik Filarmoniyası: «Səsimiz səsindir, Humay!»",
            "Şənbə, 19:00 — Akademik Milli Dram Teatrı: «Sənsiz»",
            "Şənbə, 19:00 — Azərbaycan Dövlət Akademik Musiqili Teatrı: «Şahmaran»",
            "Bazar, 11:00 — Akademik Milli Dram Teatrı: «Gözəl və Bedheybət»",
            "Bazar, 12:00 — Azərbaycan Dövlət Akademik Musiqili Teatrı: «Buratino»",
            "Bazar, 19:00 — Akademik Milli Dram Teatrı: «İblis və...»",
            "Bazar, 19:00 — Azərbaycan Dövlət Akademik Musiqili Teatrı: «Əliqulu bu gün evlənir»",
            "Bazar, 19:00 — Azərbaycan Dövlət Milli Gənc Tamaşaçılar Teatrı: «III Riçard»",
            "Sərgi — Muzey Mərkəzi: «Lətif Kərimovun 120 illiyinə həsr olunmuş sərgi»",
            "Sərgi — Azərbaycan Milli Xalça Muzeyi: «Azərbaycan Milli Xalça Muzeyi Zərgərlik fondu»",
            "Sərgi — Azərbaycan Milli Xalça Muzeyi: «Faiq Əhməd: 2011–2024-cü illər dövrü» adlı sərgi"])
        self.assertEqual(item["title"],
                         "Həftəsonu Bakı səhnələrində: «İki küpəgirən qarı», «Səsimiz səsindir, Humay!» və daha 11 tədbir")
        self.assertEqual(item["lead"], "iTicket-in afişasına görə, 14 və 15 noyabrda Bakının dövlət teatrlarında və konsert "
                                       "salonlarında tamaşalar göstəriləcək və konsertlər keçiriləcək. Muzeylərdə 3 sərgi açıqdır.")
        self.assertEqual(item["slot"], "12:00")
        self.assertEqual(len(fake.calls), 5)
        blob = text(item)
        for banned in ("Gəncə", "Şuşa", "Naxçıvan", "Pray", "Komedium", "Şam", "Stand-up"):
            self.assertNotIn(banned, blob)
        self.assertFalse(m.CYRILLIC.search(blob))

    def test_weekend_needs_three_shows(self):
        item, why = m.hefte_item(D(2026, 11, 14), [event("A", day=D(2026, 11, 14)), event("B", day=D(2026, 11, 15))], [])
        self.assertIsNone(item)
        self.assertIn("3-dən azdır", why)


class KinoTest(unittest.TestCase):
    def test_parse_real_pages(self):
        films = m.kino_parse(raw("cinema-2026-11-10.html").decode("utf-8"))
        self.assertEqual(len(films), 12)
        self.assertEqual([(f["title"], f["age"], f["langs"]) for f in films if f["date"] == D(2026, 11, 12)],
                         [("Gupi ve Gülmeyen Kral", "6+", ["Türk"]), ("Dune: 1-ci hissə", "12+", ["Rus"]), ("Ebenezer", "", ["Rus"])])
        self.assertNotIn("44", [f["title"] for f in films])  # indi göstərilən filmin tarixi yoxdur
        self.assertEqual(m.kino_parse(""), [])
        self.assertEqual(m.kino_parse("<html><h2>yox</h2></html>"), [])
        self.assertEqual(m.kino_parse(None), [])

    def test_item_from_the_wednesday_page(self):
        films = m.kino_parse(raw("cinema-2026-11-10.html").decode("utf-8"))
        item, why = m.kino_item(D(2026, 11, 12), films)
        self.assertEqual(why, "")
        self.assertEqual(item["key"], "kino-2026-11-12")
        self.assertEqual(item["title"], "12 noyabrdan kinoteatrlarda: «Gupi ve Gülmeyen Kral», «Dune: 1-ci hissə» və «Ebenezer»")
        self.assertEqual(item["lead"], "CineMastercard kinoteatrlarının «Tezliklə» siyahısına görə, 12 noyabrdan «Gupi ve Gülmeyen Kral» "
                                       "(türk dilində), «Dune: 1-ci hissə» (rus dilində) və «Ebenezer» (rus dilində) "
                                       "filmləri nümayiş olunacaq.")
        self.assertNotRegex(text(item), r"\d\+")  # yaş həddi yazılmır: kartdakı hədd buraxılış günü dəyişə bilir
        self.assertEqual(item["body"], ["Siyahıya görə, 19 noyabrdan «Aclıq Oyunları: Biçimin Şəfəqi» və "
                                        "«Bankı necə soymaq olar» nümayiş olunacaq."])
        self.assertTrue(KEYS <= set(item))
        self.assertTrue(item["worth"])
        self.assertEqual((item["credit"], item["link"], item["slot"]), ("CineMastercard", "https://cinemastercard.az/", "12:00"))

    def test_january_page_and_single_film(self):
        films = m.kino_parse(raw("cinema-2026-01-07.html").decode("utf-8"))
        item, _ = m.kino_item(D(2026, 1, 8), films)
        self.assertEqual(item["title"], "8 yanvardan kinoteatrlarda: «Kardeş Takımı 3», «Primat» və «Xadimə»")
        one = [f for f in films if f["title"] == "Primat"]
        item, _ = m.kino_item(D(2026, 1, 8), one)
        self.assertEqual(item["title"], "8 yanvardan kinoteatrlarda: «Primat»")
        self.assertIn("«Primat» (rus dilində) filmi nümayiş olunacaq.", item["lead"])
        self.assertEqual(item["body"], [])

    def test_sport_broadcasts_and_empty_days_are_not_premieres(self):
        films = m.kino_parse(raw("cinema-2026-03-05.html").decode("utf-8"))
        self.assertTrue(all(f["sport"] for f in films if f["date"] in (D(2026, 3, 7), D(2026, 3, 8), D(2026, 3, 10))))
        for day in (D(2026, 3, 5), D(2026, 3, 7), D(2026, 3, 8)):  # 5 mart cümə axşamıdır: o günün filmləri siyahıda yoxdur
            item, why = m.kino_item(day, films)
            self.assertIsNone(item)
            self.assertIn("tarixli film yoxdur", why)
        item, _ = m.kino_item(D(2026, 3, 12), films)
        self.assertNotIn("Galatasaray", text(item))
        self.assertIn("«Marsupilami»", item["title"])

    def test_long_list_keeps_the_title_short(self):
        day = D(2026, 11, 12)
        films = [{"title": f"Çox uzun adlı yeni bədii film nömrə {i}", "date": day, "age": "", "langs": [], "sport": False, "link": "/"}
                 for i in range(6)]
        item, _ = m.kino_item(day, films)
        self.assertLessEqual(len(item["title"]), m.TITLE_MAX)
        self.assertIn("və daha", item["title"])

    def test_leader_in_a_film_title_blocks_the_item(self):
        day = D(2026, 11, 12)
        films = [{"title": LEADER + " haqqında film", "date": day, "age": "", "langs": [], "sport": False, "link": "/"}]
        item, _ = m.kino_item(day, films)
        self.assertFalse(item["worth"])
        self.assertIn("rəhbərliyin adı", item["why"])

    def test_network_and_garbage(self):
        day = D(2026, 11, 12)
        self.assertEqual(m.kino_day(m._net(Fake({m.CINEMA_URL: b"<html></html>"})), day), (None, "«Tezliklə» siyahısı oxunmadı"))
        item, why = m.kino_day(m._net(Fake({m.CINEMA_URL: urllib.error.HTTPError(m.CINEMA_URL, 403, "x", None, None)})), day)
        self.assertIsNone(item)
        self.assertIn("403", why)


class VikipediyaTest(unittest.TestCase):
    DAY = D(2026, 11, 12)

    def skip(self, title, desc="", extract="", **kw):
        return m.wiki_skip(title, desc, extract, kw.pop("day", self.DAY), **kw)

    def test_blocklists(self):
        self.assertEqual(self.skip("Ana səhifə"), "ana səhifə")
        self.assertEqual(self.skip("Xüsusi:Axtar"), "xüsusi səhifə")
        self.assertEqual(self.skip("Vikipediya:Kənd meydanı"), "xüsusi səhifə")
        self.assertEqual(self.skip("Bakı", "şəhər", "Bakı — şəhər.", disamb=True), "dəqiqləşdirmə səhifəsi")
        self.assertEqual(self.skip("Seks", "cinsi məmnuniyyət (həzz) və nəsil artırma məqsədini daşıyan genital əlaqə",
                                   "Cinsi əlaqə və ya seks — genital əlaqə."), "18+ mövzu")
        self.assertEqual(self.skip("Anal seks"), "18+ mövzu")
        self.assertEqual(self.skip("Fahişəlik", "", "Fahişəlik — pul müqabilində cinsi xidmət."), "18+ mövzu")
        self.assertEqual(self.skip("İlham Əliyev", "2003-cü ildən Azərbaycan prezidenti",
                                   "İlham Heydər oğlu Əliyev — Azərbaycan Respublikasının Prezidenti."), "rəhbərlik")
        self.assertEqual(self.skip("Zəfər Günü (Azərbaycan)", "rəsmi bayram",
                                   "Zəfər Günü — dövlət bayramı. Bayram " + LEADER + "in sərəncamı ilə təsis edilib."), "rəhbərlik")
        self.assertEqual(self.skip("Alena Əliyeva", "", "Alena Əliyeva — ictimai xadim."), "rəhbərlik")
        self.assertEqual(self.skip("Heydər Əliyev", "", "Heydər Əlirza oğlu Əliyev — Azərbaycan siyasətçisi."), "rəhbərlik")
        self.assertEqual(self.skip("Qız qalası", "Bakıdakı memarlıq abidəsi", "Qız qalası — Bakıda yerləşən qədim memarlıq abidəsi."), "")
        self.assertEqual(self.skip("Rəcəb Tayyib Ərdoğan", "2014-cü ildən Türkiyə prezidenti",
                                   "Rəcəb Tayyib Ərdoğan — Türkiyə siyasətçisi, Türkiyə Respublikasının 12-ci prezidenti."), "")

    def test_officials_of_azerbaijan_are_left_out(self):
        for title, desc, extract in (
                ("Vilayət Eyvazov", "Azərbaycan daxili işlər naziri (2019-cu ildən)",
                 "Vilayət Süleyman oğlu Eyvazov — Azərbaycanın hərbi və siyasi xadimi, general-polkovnik."),
                ("Ramiz Mehdiyev", "Azərbaycan ictimai-siyasi və elm xadimi (1938 təvəllüdlü)",
                 "Ramiz Ənvər oğlu Mehdiyev (17 aprel 1938, Bakı) — Azərbaycan ictimai-siyasi və elm xadimi."),
                ("Arzuxan Əlizadə", "Azərbaycan siyasətçisi", "Arzuxan Əlizadə (18 mart 1965, Bakı) — Milli Məclisinin deputatı.")):
            self.assertTrue(self.skip(title, desc, extract), title)

    def test_recent_deaths_and_crimes(self):
        lead = "Zaur Əlihüseyn oğlu Rzayev (28 yanvar 1952, Karrar, Kürdəmir rayonu – 29 oktyabr 2026, Bakı) — Azərbaycan müğənnisi."
        self.assertEqual(self.skip("Zaur Rzayev", "Azərbaycan müğənnisi", lead, day=D(2026, 11, 2)), "son bir ildə vəfat edib")
        self.assertEqual(self.skip("Zaur Rzayev", "Azərbaycan müğənnisi", lead, day=D(2026, 10, 30)), "son bir ildə vəfat edib")
        self.assertEqual(self.skip("Zaur Rzayev", "Azərbaycan müğənnisi", lead, day=D(2028, 1, 5)), "")
        self.assertEqual(self.skip("Zaur Rzayev", "Azərbaycan müğənnisi (1952–2026)", "Zaur Rzayev — Azərbaycan müğənnisi."),
                         "son bir ildə vəfat edib")
        self.assertEqual(self.skip("Polad Həşimov", "Azərbaycan hərbçisi <1975–2020>", "Polad Həşimov — Azərbaycan hərbçisi."), "")
        self.assertEqual(self.skip("Davud Kazımov", "Azərbaycan rəssamı",
                                   "Davud Mehdi oğlu Kazımov (9 noyabr 1926, Bakı – 14 fevral 2015, Bakı) — Azərbaycan boyakarı."), "")
        self.assertEqual(self.skip("Filankəs", "Azərbaycan aktyoru", "Filankəs — aktyor. O, 2026-cı ildə vəfat edib."),
                         "son bir ildə vəfat edib")
        self.assertEqual(self.skip("Filan küçəsindəki qətl", "2026-cı ildə Bakıda baş vermiş cinayət",
                                   "Filan küçəsindəki qətl — 2026-cı ildə baş vermiş hadisə."), "cinayət və ya hadisə")

    def test_feed_rows(self):
        day, rows = m.gun_rows(load("wiki-feed-2026-11-10.json"))
        self.assertEqual(day, D(2026, 11, 9))
        self.assertEqual(len(rows), 25)
        self.assertEqual((rows[0]["title"], rows[0]["views"], rows[0]["prev"]), ("Dövlət Bayrağı Günü (Azərbaycan)", 1199, 601))
        self.assertEqual([r["views"] for r in rows], sorted((r["views"] for r in rows), reverse=True))
        for bad in (None, [], {}, {"mostread": []}, {"mostread": {"date": "yox", "articles": []}}, load("wiki-feed-2026-11-11.json")):
            self.assertEqual(m.gun_rows(bad), (None, []))
        day, rows = m.gun_rows({"mostread": {"date": "2026-11-09Z", "articles": [None, {"views": "5"}, {"titles": {"normalized": "A"}},
                                                                                {"titles": {"normalized": "B"}, "views": True}]}})
        self.assertEqual((day, rows), (D(2026, 11, 9), []))

    def test_day_item_from_real_feed(self):
        fake = Fake()
        item, why, final = m.gun_day(m._net(fake), D(2026, 11, 10))
        self.assertTrue(final)
        self.assertEqual(item["key"], "vikipediya-gun-2026-11-09")
        self.assertTrue(KEYS <= set(item))
        self.assertTrue(item["worth"], item.get("why"))
        self.assertEqual(item["body"], [
            "«Dövlət Bayrağı Günü (Azərbaycan)» — 1 199 baxış (Azərbaycan Respublikasının rəsmi dövlət bayramı)",
            "«44 (film)» — 731 baxış (2026-cı ildə istehsal olunmuş Azərbaycan tammetrajlı bədii müharibə filmi)",
            "«Azərbaycan bayrağı» — 524 baxış (Azərbaycan Respublikasının Dövlət bayrağı)",
            "«Rəcəb Tayyib Ərdoğan» — 470 baxış (2014-cü ildən Türkiyə prezidenti)",
            "«Azərbaycan» — 404 baxış (Cənubi Qafqazda ölkə)"])
        self.assertEqual(item["title"], "Dünən Azərbaycan Vikipediyasında ən çox «Dövlət Bayrağı Günü (Azərbaycan)» məqaləsi oxunub")
        self.assertEqual(item["lead"], "Vikimedia Fondunun məlumatına görə, 9 noyabrda Azərbaycandilli Vikipediyada ən çox "
                                       "«Dövlət Bayrağı Günü (Azərbaycan)» məqaləsi oxunub: 1 199 baxış. Bir gün əvvəl bu məqaləyə "
                                       "601 dəfə baxılmışdı.")
        blob = text(item)
        for banned in ("Seks", "İlham", "Heydər Əliyev", "Alena", "Eyvazov", "Mirzəyev", "Həsənov", "Nağıyev"):
            self.assertNotIn(banned, blob)
        self.assertEqual(len(fake.calls), 2)
        self.assertEqual(fake.urls[0], m.FEED_URL.format(D(2026, 11, 10)))
        self.assertTrue(fake.urls[1].startswith(INFO[:-1]))
        self.assertLessEqual(fake.urls[1].count("%7C") - 2, m.INFO_GUN - 1)

    def test_first_place_filtered_means_no_superlative(self):
        day, rows = m.gun_rows(load("wiki-feed-2026-11-09.json"))
        item, why = m.gun_item(day, rows, D(2026, 11, 9))
        self.assertEqual(rows[0]["skip"], "rəhbərlik")  # «Zəfər Günü»: girişdə Prezidentin adı var
        self.assertEqual(item["title"], "Dünən Azərbaycan Vikipediyasında çox oxunanlar: «44 (film)», «Rəcəb Tayyib Ərdoğan» və «Murad Əliyev»")
        self.assertEqual(item["lead"], "Vikimedia Fondunun məlumatına görə, 8 noyabrda Azərbaycandilli Vikipediyada çox oxunan məqalələr "
                                       "arasında «44 (film)» (1 256 baxış), «Rəcəb Tayyib Ərdoğan» (1 066 baxış) və «Murad Əliyev» "
                                       "(690 baxış) var. Siyahıdakı məqalələr arasında bir gündə ən çox artım: «Rəcəb Tayyib Ərdoğan» "
                                       "məqaləsinə baxışların sayı 56-dan 1 066-ya qalxıb.")
        self.assertEqual(len(item["body"]), 5)
        self.assertEqual(item["body"][3], "«Dövlət Bayrağı Günü (Azərbaycan)» — 601 baxış (Azərbaycan Respublikasının rəsmi dövlət bayramı)")
        self.assertNotIn("ən çox «", item["title"] + item["lead"])
        self.assertNotIn("Zəfər Günü", text(item))
        older, _ = m.gun_item(day, m.gun_rows(load("wiki-feed-2026-11-09.json"))[1], D(2026, 11, 12))
        self.assertTrue(older["title"].startswith("8 noyabrda Azərbaycan Vikipediyasında çox oxunanlar"))

    def test_real_list_of_10_november_drops_the_actor_who_died_that_day(self):
        """Lentdə «Aslan Fətullayev — Azərbaycan aktyoru.» (1 488 baxış, birinci yer) yazılıb, ölüm tarixi yalnız tam
        girişdədir: «(20 oktyabr 1956, … – 10 noyabr 2026, Moskva)»."""
        tbl = table(**{m.FEED_URL.format(D(2026, 11, 11)): raw("wiki-feed-2026-11-11-ready.json")})
        fake = Fake(tbl)
        item, why, final = m.gun_day(m._net(fake), D(2026, 11, 11))
        self.assertTrue(item["worth"])
        self.assertEqual(item["key"], "vikipediya-gun-2026-11-10")
        self.assertNotIn("Fətullayev", text(item))
        self.assertEqual(item["title"], "Dünən Azərbaycan Vikipediyasında çox oxunanlar: «44 (film)», «Azərbaycan» və «Uzun Həsən»")
        self.assertEqual(item["body"], [
            "«44 (film)» — 533 baxış (2026-cı ildə istehsal olunmuş Azərbaycan tammetrajlı bədii müharibə filmi)",
            "«Azərbaycan» — 405 baxış (Cənubi Qafqazda ölkə)",
            "«Uzun Həsən» — 249 baxış (Ağqoyunluların IX hökmdarı və ilk sultanı (padşah))",
            "«Mustafa Kamal Atatürk» — 248 baxış (Türkiyə Respublikasının qurucusu və ilk prezidenti)",
            "«Rəcəb Tayyib Ərdoğan» — 223 baxış (2014-cü ildən Türkiyə prezidenti)"])
        self.assertTrue(item["lead"].endswith("«Uzun Həsən» məqaləsinə baxışların sayı 55-dən 249-a qalxıb."))
        day, rows = m.gun_rows(load("wiki-feed-2026-11-11-ready.json"))
        self.assertEqual((rows[0]["title"], rows[0]["views"]), ("Aslan Fətullayev", 1488))
        self.assertEqual(m.wiki_skip(rows[0]["title"], rows[0]["desc"], rows[0]["extract"], D(2026, 11, 11)), "")  # lent bilmir
        self.assertEqual(m.gun_check(m._net(Fake(tbl)), rows, D(2026, 11, 11)), "")
        self.assertEqual(rows[0]["skip"], "son bir ildə vəfat edib")

    def test_death_date_in_a_later_bracket_and_seasons(self):
        day = D(2026, 11, 12)
        self.assertTrue(m._died_recently("Filankəs (rus. Иван Иванов) (1 yanvar 1950, Bakı – 8 noyabr 2026, Bakı) — aktyor.", day))
        self.assertTrue(m._died_recently("Filankəs (1950, Bakı – 2026, Bakı) — aktyor.", day))
        self.assertFalse(m._died_recently("Filankəs (1 yanvar 1950, Bakı – 8 noyabr 2020, Bakı) — aktyor.", day))
        self.assertFalse(m._died_recently("Çempionlar Liqası (2025–2026 mövsümü) — futbol turniri.", day))
        self.assertFalse(m._died_recently("Mustafa Kamal Atatürk (türk. Mustafa Kemal Atatürk) (ən tezi 1879 və ən geci 1881, Saloniki – "
                                          "10 noyabr 1938, Beşiktaş) — Türkiyə Respublikasının qurucusu.", day))
        self.assertFalse(m._died_recently("", day))
        self.assertFalse(m._died_recently(None, day))

    def test_jump_line(self):
        rows = [{"title": "A", "views": 1066, "prev": 56}, {"title": "B", "views": 690, "prev": 70},
                {"title": "C", "views": 900, "prev": 5}, {"title": "D", "views": 500, "prev": None}]
        self.assertEqual(m._jump(rows), "Siyahıdakı məqalələr arasında bir gündə ən çox artım: «A» məqaləsinə baxışların sayı "
                                        "56-dan 1 066-ya qalxıb.")
        self.assertEqual(m._jump([{"title": "A", "views": 100, "prev": 50}]), "")

    def test_too_few_articles_left(self):
        rows = [{"title": "Seks", "views": 9, "prev": None, "desc": "", "extract": "", "disamb": False},
                {"title": "Qız qalası", "views": 8, "prev": None, "desc": "", "extract": "Qız qalası — abidə.", "disamb": False},
                {"title": "Bakı", "views": 7, "prev": None, "desc": "", "extract": "Bakı — şəhər.", "disamb": False}]
        item, why = m.gun_item(D(2026, 11, 9), rows, D(2026, 11, 10))
        self.assertIsNone(item)
        self.assertIn("3-dən azdır", why)

    def test_lead_check_catches_a_death_the_feed_does_not_show(self):
        dead = {"Azərbaycan bayrağı": ("Azərbaycan Respublikasının Dövlət bayrağı",
                                       "Sınaq Sınaqov (1 yanvar 1950, Bakı – 8 noyabr 2026, Bakı) — Azərbaycan müğənnisi.")}
        fake = Fake(table(**{INFO: lambda url: info_doc(url, dead)}))
        item, _, _ = m.gun_day(m._net(fake), D(2026, 11, 10))
        self.assertNotIn("«Azərbaycan bayrağı»", text(item))
        self.assertEqual(len(item["body"]), 5)

    def test_missing_leads_drop_the_article_and_a_failed_request_drops_the_item(self):
        gone = Fake(table(**{INFO: lambda url: json.dumps({"query": {"pages": []}}).encode()}))
        item, why, final = m.gun_day(m._net(gone), D(2026, 11, 10))
        self.assertIsNone(item)
        self.assertTrue(final)
        self.assertIn("3-dən azdır", why)
        down = Fake(table(**{INFO: urllib.error.URLError("x")}))
        item, why, final = m.gun_day(m._net(down), D(2026, 11, 10))
        self.assertIsNone(item)
        self.assertTrue(final)
        self.assertIn("girişi alınmadı", why)

    def test_feed_not_ready_or_down_is_not_final(self):
        item, why, final = m.gun_day(m._net(Fake()), D(2026, 11, 11))          # lentdə hələ yalnız «image» var
        self.assertEqual((item, final), (None, False))
        self.assertIn("hələ yoxdur", why)
        old = Fake(table(**{m.FEED_URL.format(D(2026, 11, 11)): raw("wiki-feed-2026-11-09.json")}))
        item, why, final = m.gun_day(m._net(old), D(2026, 11, 11))            # siyahı srağagünündür
        self.assertEqual((item, final), (None, False))
        self.assertIn("hələ hazır deyil", why)
        self.assertEqual(len(old.calls), 1)
        for bad in (b"<html>", urllib.error.URLError("x")):
            item, why, final = m.gun_day(m._net(Fake({m.FEED_URL.format(D(2026, 11, 11)): bad})), D(2026, 11, 11))
            self.assertEqual((item, final), (None, False))

    def test_month_rows(self):
        year, month, rows = m.ay_rows(load("top-2026-10.json"))
        self.assertEqual((year, month), (2026, 10))
        self.assertEqual((rows[0]["title"], rows[0]["views"]), ("Seks", 17197))
        self.assertEqual((rows[1]["title"], rows[1]["views"]), ("Qız qalası", 14166))
        self.assertFalse([r for r in rows if r["title"].startswith(("Ana səhifə", "Xüsusi:"))])
        for bad in (None, {}, {"items": []}, {"items": [None]}, {"items": [{"year": "x", "month": "10"}]}):
            self.assertEqual(m.ay_rows(bad), (None, None, []))

    def test_month_item_from_real_responses(self):
        fake = Fake()
        item, why = m.ay_month(m._net(fake), 2026, 10, D(2026, 11, 2))
        self.assertEqual(item["key"], "vikipediya-ay-2026-10")
        self.assertTrue(KEYS <= set(item))
        self.assertTrue(item["worth"], item.get("why"))
        self.assertEqual(item["body"], [
            "«Qız qalası» — 14 166 baxış (Bakıdakı memarlıq abidəsi)",
            "«44 (film)» — 9 925 baxış (2026-cı ildə istehsal olunmuş Azərbaycan tammetrajlı bədii müharibə filmi)",
            "«Azərbaycan» — 9 599 baxış (Cənubi Qafqazda ölkə)",
            "«Müstəqilliyin Bərpası Günü (Azərbaycan)» — 7 503 baxış",
            "«Böyük ipək yolu» — 6 564 baxış (Şərqi Asiya ilə Aralıq dənizi arasında dünyanın ən qədim ticarət yollarından biri)"])
        self.assertEqual(item["title"], "Oktyabrda Azərbaycan Vikipediyasında çox oxunanlar: «Qız qalası», «44 (film)» və «Azərbaycan»")
        self.assertEqual(item["lead"], "Vikimedia Fondunun məlumatına görə, oktyabrda Azərbaycandilli Vikipediyada çox oxunan məqalələr "
                                       "arasında «Qız qalası» (14 166 baxış), «44 (film)» (9 925 baxış) və «Azərbaycan» (9 599 baxış) var.")
        self.assertNotIn("ən çox", item["title"] + item["lead"])  # birinci yerdəki məqalə süzgəcdən keçməyib
        self.assertLessEqual(len(item["title"]), m.TITLE_MAX)
        self.assertEqual(len(item["body"]), 5)
        blob = text(item)
        for banned in ("Seks", "Əliyev", "Mehdiyev", "Rzayev", "Əlizadə", "Seyidov", "Bayramov"):
            self.assertNotIn(banned, blob)
        self.assertEqual(len(fake.calls), 2)

    def test_month_death_is_counted_from_the_publish_day(self):
        _, _, rows = m.ay_rows(load("top-2026-10.json"))
        find = m.wiki_info(load("ext-2026-10.json"))
        m.ay_item(2026, 10, rows, find, D(2026, 11, 2))
        skip = {r["title"]: r.get("skip") for r in rows[:m.INFO_N]}
        self.assertEqual(skip["Zaur Rzayev"], "son bir ildə vəfat edib")
        self.assertEqual(skip["Qız qalası"], "")
        self.assertTrue(skip["Ramiz Mehdiyev"])
        late = {"query": {"pages": [{"title": "Qız qalası", "description": "müğənni",
                                     "extract": "Sınaq Sınaqov (1 yanvar 1950, Bakı – 1 noyabr 2026, Bakı) — müğənni."}]}}
        _, _, rows = m.ay_rows(load("top-2026-10.json"))
        m.ay_item(2026, 10, rows, m.wiki_info(late), D(2026, 11, 2))
        self.assertEqual(rows[1]["skip"], "son bir ildə vəfat edib")  # ay bitəndən sonra, dərcdən əvvəl

    def test_month_errors(self):
        top = m.TOP_URL.format(2026, 10)
        for tbl, word in (({top: urllib.error.URLError("x")}, "aylıq siyahı alınmadı"),
                          ({top: b"{}"}, "boşdur"),
                          ({top: raw("top-2026-10.json"), INFO: urllib.error.URLError("x")}, "girişi alınmadı"),
                          ({top: raw("top-2026-10.json"), INFO: b'{"query": {"pages": []}}'}, "3-dən azdır")):
            item, why = m.ay_month(m._net(Fake(tbl)), 2026, 10, D(2026, 11, 2))
            self.assertIsNone(item)
            self.assertIn(word, why)
        item, why = m.ay_month(m._net(Fake({top: raw("top-2026-10.json")})), 2026, 9, D(2026, 10, 2))
        self.assertIsNone(item)

    def test_month_day(self):
        self.assertTrue(m._ay_day(D(2026, 11, 2)))    # bazar ertəsi
        self.assertFalse(m._ay_day(D(2026, 11, 1)))
        self.assertFalse(m._ay_day(D(2026, 12, 2)))   # çərşənbə: kino günü
        self.assertTrue(m._ay_day(D(2026, 12, 1)))
        self.assertFalse(m._ay_day(D(2026, 10, 2)))   # cümə: həftəsonu afişası
        self.assertTrue(m._ay_day(D(2026, 10, 1)))
        self.assertFalse(m._ay_day(D(2026, 11, 3)))
        self.assertEqual(m._prev_month(D(2027, 1, 2)), (2026, 12))


class YubileyTest(unittest.TestCase):
    def leads(self):
        return {p["title"]: p["extract"] for p in load("ext-leads.json")["query"]["pages"]}

    def test_rows_from_real_answers(self):
        rows = m.yub_rows(load("wdqs-2026-11-10.json"), D(2026, 11, 10))
        self.assertEqual([(r["name"], r["years"], r["why"]) for r in rows], [("Rəhilə Həsənova", 75, "")])
        rows = m.yub_rows(load("wdqs-2026-11-09.json"), D(2026, 11, 9))
        self.assertEqual([(r["name"], r["years"], r["why"]) for r in rows], [("Davud Kazımov", 100, "")])
        misc = load("wdqs-2026-11-misc.json")
        self.assertEqual([(r["name"], r["years"], r["why"]) for r in m.yub_rows(misc, D(2026, 11, 7))],
                         [("Lalə Şövkət", 75, "siyasətçi və ya vəzifəli şəxs")])
        self.assertEqual([(r["name"], r["years"], r["why"]) for r in m.yub_rows(misc, D(2026, 11, 14))], [("Kamal Quliyev", 50, "")])
        self.assertEqual([(r["name"], r["years"], r["why"]) for r in m.yub_rows(misc, D(2026, 11, 21))], [("Nadir Vəlixanov", 100, "")])
        self.assertEqual(m.yub_rows(misc, D(2026, 11, 8)), [])

    def test_thresholds_and_garbage(self):
        day = D(2026, 11, 10)
        doc = json.loads(sparql(wd("Q1", "İyirmi Beş", "2001-11-10"), wd("Q2", "Əlli", "1976-11-10"), wd("Q3", "Əlli Bir", "1975-11-10"),
                                wd("Q4", "Yüz İyirmi Beş", "1901-11-10", sl=9), wd("Q5", "Başqa Gün", "1951-11-11"),
                                wd("Q6", "Peşəsiz", "1951-11-10", desc="", occ=""), wd("Q7", "Vəzifəli", "1951-11-10", posn=2),
                                wd("Q8", "Deputat", "1951-11-10", desc="Azərbaycan deputatı"), wd("Q2", "Əlli", "1976-11-10"),
                                {"p": {"value": "yox"}}, None))
        got = {r["name"]: (r["years"], r["why"]) for r in m.yub_rows(doc, day)}
        self.assertEqual(got, {"Əlli": (50, ""), "Yüz İyirmi Beş": (125, ""), "Peşəsiz": (75, "peşəsi məlum deyil"),
                               "Vəzifəli": (75, "siyasətçi və ya vəzifəli şəxs"), "Deputat": (75, "siyasətçi və ya vəzifəli şəxs")})
        self.assertEqual(m.yub_rows(doc, day)[0]["name"], "Yüz İyirmi Beş")  # daha çox dildə məqaləsi olan birinci
        for bad in (None, [], {}, {"results": None}, {"results": {"bindings": "x"}}):
            self.assertEqual(m.yub_rows(bad, day), [])

    def test_birth_date_must_be_in_the_wikipedia_lead(self):
        leads = self.leads()
        self.assertTrue(m.lead_ok(leads["Davud Kazımov"], D(2026, 11, 9), 1926))
        self.assertFalse(m.lead_ok(leads["Davud Kazımov"], D(2026, 11, 9), 1927))
        self.assertFalse(m.lead_ok(leads["Davud Kazımov"], D(2026, 11, 10), 1926))
        self.assertTrue(m.lead_ok(leads["Lətif Kərimov"], D(2026, 11, 17), 1906))   # «4 (17) noyabr 1906»
        self.assertTrue(m.lead_ok(leads["Lətif Kərimov"], D(2026, 11, 4), 1906))
        self.assertFalse(m.lead_ok(leads["Lətif Kərimov"], D(2026, 11, 5), 1906))
        self.assertFalse(m.lead_ok(leads["Süleyman Rüstəm"], D(2026, 11, 27), 1906))  # Wikidata 27.11.1906, Vikipediya 12 mart
        self.assertTrue(m.lead_ok(leads["Süleyman Rüstəm"], D(2026, 3, 12), 1906))
        self.assertFalse(m.lead_ok("", D(2026, 11, 9), 1926))
        self.assertFalse(m.lead_ok("Filankəs — Azərbaycan rəssamı.", D(2026, 11, 9), 1926))

    def test_place_and_death_from_the_lead(self):
        leads = self.leads()
        self.assertEqual(m._birthplace(leads["Davud Kazımov"], D(2026, 11, 9), 1926), "Bakı")
        self.assertEqual(m._birthplace(leads["Lətif Kərimov"], D(2026, 11, 17), 1906), "Şuşa")
        self.assertEqual(m._birthplace(leads["Firudin Hüseynov (dilçi)"], D(2026, 11, 10), 1937), "")
        r = {"year": 1926, "dead": "2015-02-14"}
        self.assertEqual(m._death(leads["Davud Kazımov"], r, D(2026, 11, 9)), D(2015, 2, 14))
        self.assertIsNone(m._death(leads["Davud Kazımov"], dict(r, dead=""), D(2026, 11, 9)))
        self.assertIsNone(m._death(leads["Davud Kazımov"], dict(r, dead="2016-02-14"), D(2026, 11, 9)))

    def test_item_text(self):
        day = D(2026, 11, 9)
        r = m.yub_rows(load("wdqs-2026-11-09.json"), day)[0]
        item, _ = m.yub_item(day, dict(r, extract=self.leads()["Davud Kazımov"]))
        self.assertEqual(item["title"], "Azərbaycan rəssamı Davud Kazımovun anadan olmasından 100 il keçir")
        self.assertEqual(item["lead"], "Azərbaycan rəssamı Davud Kazımov 9 noyabr 1926-cı ildə Bakıda anadan olub. "
                                       "O, 14 fevral 2015-ci ildə, 88 yaşında vəfat edib.")
        self.assertEqual(item["body"], [])
        self.assertEqual((item["key"], item["slot"], item["credit"]), ("yubiley-2026-11-09", "09:00", "Vikipediya"))
        self.assertEqual(item["link"], "https://az.wikipedia.org/wiki/Davud_Kaz%C4%B1mov")
        self.assertTrue(KEYS <= set(item))

    def test_today_from_real_responses(self):
        fake = Fake()
        report = []
        item, why = m.yubiley_day(m._net(fake), D(2026, 11, 10), report)
        self.assertEqual(why, "")
        self.assertEqual(item["title"], "Azərbaycan bəstəkarı Rəhilə Həsənovanın anadan olmasından 75 il keçir")
        self.assertEqual(item["lead"], "Azərbaycan bəstəkarı Rəhilə Həsənova 10 noyabr 1951-ci ildə anadan olub. "
                                       "O, 10 avqust 2024-cü ildə, 72 yaşında vəfat edib.")
        self.assertTrue(item["worth"])
        self.assertEqual(report, [("Rəhilə Həsənova", 75, "")])
        self.assertEqual(len(fake.calls), 3)
        self.assertEqual(fake.urls[:2], [m.sparql_url(D(2026, 11, 10)), ox.WIKI_API.format("10_noyabr")])
        self.assertNotIn("sufi", text(item))  # Vikipediyanın mətni xəbərə köçürülmür

    def test_person_already_in_the_day_page_is_left_to_bu_gun_tarixde(self):
        fake = Fake()
        report = []
        item, why = m.yubiley_day(m._net(fake), D(2026, 11, 9), report)
        self.assertIsNone(item)
        self.assertEqual(why, "namizədlər «Bu gün tarixdə» xəbərindədir")
        self.assertEqual(len(fake.calls), 2)
        self.assertIn("Bu gün tarixdə", report[0][2])
        self.assertIn("davud kazımov", m.born_names(ox.tarix_parse(load("day-9_noyabr.json")["parse"]["wikitext"])))

    def two(self, extra=None, **over):
        day = D(2026, 11, 10)
        pages = {"Birinci Sınaqov": ("", "Birinci Sınaqov (10 noyabr 1926, Şuşa – 3 mart 1990, Bakı) — Azərbaycan rəssamı."),
                 "İkinci Sınaqov": ("", "İkinci Sınaqov (10 noyabr 1951, Gəncə) — Azərbaycan şairi.")}
        pages.update(extra or {})
        tbl = table(**{m.sparql_url(day): sparql(wd("Q1", "Birinci Sınaqov", "1926-11-10", desc="Azərbaycan rəssamı", sl=8, dead="1990-03-03"),
                                                 wd("Q2", "İkinci Sınaqov", "1951-11-10", desc="Azərbaycan şairi", sl=2)),
                       INFO: lambda url: info_doc(url, pages)})
        tbl.update(over)
        fake = Fake(tbl)
        report = []
        item, why = m.yubiley_day(m._net(fake), day, report)
        return item, why, report, fake

    def test_one_item_a_day_mentions_the_second_person(self):
        item, why, report, fake = self.two()
        self.assertEqual(item["key"], "yubiley-2026-11-10")
        self.assertEqual(item["title"], "Azərbaycan rəssamı Birinci Sınaqovun anadan olmasından 100 il keçir")
        self.assertEqual(item["lead"], "Azərbaycan rəssamı Birinci Sınaqov 10 noyabr 1926-cı ildə Şuşada anadan olub. "
                                       "O, 3 mart 1990-cı ildə, 63 yaşında vəfat edib.")
        self.assertEqual(item["body"], ["Bu gün həmçinin Azərbaycan şairi İkinci Sınaqovun anadan olmasından 75 il keçir."])
        self.assertEqual(len(fake.calls), 3)

    def test_wrong_wikidata_date_and_leader_in_the_lead_drop_the_person(self):
        item, why, report, _ = self.two({"Birinci Sınaqov": ("", "Birinci Sınaqov (12 mart 1926, Şuşa) — Azərbaycan rəssamı.")})
        self.assertEqual(item["title"], "Azərbaycan şairi İkinci Sınaqovun anadan olmasından 75 il keçir")
        self.assertIn(("Birinci Sınaqov", 100, "az.wikipedia girişində bu doğum tarixi yoxdur"), report)
        item, why, report, _ = self.two({"Birinci Sınaqov": ("", "Birinci Sınaqov (10 noyabr 1926, Şuşa) — Azərbaycan rəssamı, "
                                                                 + LEADER + "in sərəncamı ilə təltif edilib.")})
        self.assertNotIn("Birinci", text(item))
        self.assertIn(("Birinci Sınaqov", 100, "girişdə rəhbərliyin adı keçir"), report)
        item, why, report, _ = self.two({"Birinci Sınaqov": ("", ""), "İkinci Sınaqov": ("", "")})
        self.assertIsNone(item)
        self.assertIn("yoxlamasından keçmədi", why)

    def test_living_person_with_a_sensitive_lead_is_left_out(self):
        for lead in ("İkinci Sınaqov (10 noyabr 1951, Gəncə) — Azərbaycan jurnalisti, müxalifət partiyasının üzvü.",
                     "İkinci Sınaqov (10 noyabr 1951, Gəncə) — Azərbaycan jurnalisti. 2024-cü ildə həbs edilib.",
                     "İkinci Sınaqov (10 noyabr 1951, Gəncə) — Azərbaycan alimi, Milli Məclisin deputatı."):
            item, why, report, _ = self.two({"İkinci Sınaqov": ("", lead)})
            self.assertEqual(item["body"], [], lead)
            self.assertIn(("İkinci Sınaqov", 75, "sağ şəxsin girişində siyasət, məhkəmə və ya hadisə mövzusu var"), report)
        # vəfat etmiş şəxsin tarixi girişi (repressiya, Ali Sovet deputatı) yubileyə mane deyil
        item, why, report, _ = self.two({"Birinci Sınaqov": ("", "Birinci Sınaqov (10 noyabr 1926, Şuşa – 3 mart 1990, Bakı) — Azərbaycan "
                                                                 "rəssamı, Ali Sovetin deputatı. 1949-cu ildə həbs edilib.")})
        self.assertEqual(item["title"], "Azərbaycan rəssamı Birinci Sınaqovun anadan olmasından 100 il keçir")

    def test_real_living_person_of_12_november(self):
        lead = {p["title"]: p for p in load("ext-2026-11-11.json")["query"]["pages"]}["Seymur Nəsirov"]["extract"]
        day = D(2026, 11, 12)
        self.assertTrue(m.lead_ok(lead, day, 1976))
        self.assertEqual(m._birthplace(lead, day, 1976), "")  # «Şuvi, Astara rayonu»: şəhər siyahısında yoxdur
        self.assertFalse(m.POLITICAL.search(m._low(lead)) or m.SENSITIVE.search(m._low(lead)))
        r = {"qid": "Q1", "name": "Seymur Nəsirov", "title": "Seymur Nəsirov", "year": 1976, "years": 50, "sl": 4,
             "desc": "Azərbaycan alimi və tədqiqatçısı", "occ": ["alim", "ərəbşünas"], "dead": "", "why": "", "extract": lead}
        item, _ = m.yub_item(day, r)
        self.assertEqual(item["title"], "Azərbaycan alimi və tədqiqatçısı Seymur Nəsirovun anadan olmasından 50 il keçir")
        self.assertEqual(item["lead"], "Azərbaycan alimi və tədqiqatçısı Seymur Nəsirov 12 noyabr 1976-cı ildə anadan olub.")
        self.assertNotIn("Misir", text(item))  # girişin mətni köçürülmür

    def test_network_errors_mean_no_item(self):
        day = D(2026, 11, 10)
        down = urllib.error.URLError("x")
        for over, word, calls in (({m.sparql_url(day): down}, "Wikidata alınmadı", 1),
                                  ({m.sparql_url(day): b"<html>"}, "Wikidata alınmadı", 1),
                                  ({ox.WIKI_API.format("10_noyabr"): down}, "gün səhifəsi alınmadı", 2),
                                  ({INFO: down}, "girişləri alınmadı", 3)):
            item, why, _, fake = self.two(**over)
            self.assertIsNone(item)
            self.assertIn(word, why)
            self.assertEqual(len(fake.calls), calls)
        item, why = m.yubiley_day(m._net(Fake(table(**{m.sparql_url(day): sparql()}))), day)
        self.assertEqual((item, why), (None, "bu gün 25-ə bölünən yubiley yoxdur"))


class ItemsTest(unittest.TestCase):
    def run_at(self, now, done=None, tbl=None):
        fake = Fake(tbl)
        return m.items(ROOT, now, fake, done), fake

    def test_nothing_is_fetched_outside_the_windows(self):
        for now in (at(2026, 11, 12, 8, 0), at(2026, 11, 12, 9, 50), at(2026, 11, 12, 11, 0), at(2026, 11, 12, 16, 0), at(2026, 11, 12, 23, 59)):
            out, fake = self.run_at(now)
            self.assertEqual((out, fake.calls), ([], []))

    def test_daily_afisa_window_and_done(self):
        out, fake = self.run_at(at(2026, 11, 12, 10, 5))
        self.assertEqual([(i["key"], i["worth"]) for i in out], [("afisa-2026-11-12", True)])
        self.assertEqual(len(fake.calls), 2)
        out, fake = self.run_at(at(2026, 11, 12, 10, 20), done={"afisa-2026-11-12"})
        self.assertEqual((out, fake.calls), ([], []))

    def test_friday_has_the_weekend_list_instead(self):
        out, fake = self.run_at(at(2026, 11, 13, 10, 5))
        self.assertEqual((out, fake.calls), ([], []))
        out, fake = self.run_at(at(2026, 11, 13, 12, 10))
        self.assertEqual([(i["key"], i["worth"]) for i in out], [("afisa-hefte-2026-11-14", True)])
        self.assertEqual(len(fake.calls), 5)
        out, fake = self.run_at(at(2026, 11, 13, 12, 30), done={"afisa-hefte-2026-11-14"})
        self.assertEqual((out, fake.calls), ([], []))
        out, fake = self.run_at(at(2026, 11, 12, 12, 10))  # cümə axşamı
        self.assertEqual((out, fake.calls), ([], []))

    def test_kino_on_wednesday_only(self):
        out, fake = self.run_at(at(2026, 11, 11, 12, 5))
        self.assertEqual([(i["key"], i["worth"]) for i in out], [("kino-2026-11-12", True)])
        self.assertEqual(fake.urls, [m.CINEMA_URL])
        out, fake = self.run_at(at(2026, 11, 11, 12, 15), done={"kino-2026-11-12"})
        self.assertEqual((out, fake.calls), ([], []))

    def test_a_failed_round_returns_the_key_so_the_window_is_not_retried(self):
        day = D(2026, 11, 12)
        down = {it_url("theatre", day): urllib.error.URLError("x")}
        out, fake = self.run_at(at(2026, 11, 12, 10, 5), tbl=down)
        self.assertEqual([(i["key"], i["worth"]) for i in out], [("afisa-2026-11-12", False)])
        self.assertIn("iTicket alınmadı", out[0]["why"])
        self.assertTrue(KEYS <= set(out[0]))
        out, fake = self.run_at(at(2026, 11, 12, 10, 25), done={i["key"] for i in out}, tbl=down)
        self.assertEqual((out, fake.calls), ([], []))
        out, fake = self.run_at(at(2026, 11, 10, 10, 5))  # 3-dən az tədbir
        self.assertEqual([(i["key"], i["worth"]) for i in out], [("afisa-2026-11-10", False)])
        self.assertIn("3-dən azdır", out[0]["why"])
        out, fake = self.run_at(at(2026, 11, 9, 9, 5))    # yubiley namizədi «Bu gün tarixdə» xəbərindədir
        self.assertEqual([(i["key"], i["worth"]) for i in out], [("yubiley-2026-11-09", False)])
        self.assertEqual(len(fake.calls), 2)

    def test_yubiley_window(self):
        out, fake = self.run_at(at(2026, 11, 10, 9, 5))
        self.assertEqual([(i["key"], i["worth"]) for i in out], [("yubiley-2026-11-10", True)])
        self.assertEqual(len(fake.calls), 3)
        out, fake = self.run_at(at(2026, 11, 10, 9, 20), done={"yubiley-2026-11-10"})
        self.assertEqual((out, fake.calls), ([], []))

    def test_wikipedia_first_try_and_retry(self):
        out, fake = self.run_at(at(2026, 11, 10, 13, 5))
        self.assertEqual([(i["key"], i["worth"], i["slot"]) for i in out], [("vikipediya-gun-2026-11-09", True, "13:00")])
        self.assertEqual(len(fake.calls), 2)
        out, fake = self.run_at(at(2026, 11, 10, 15, 5), done={"vikipediya-gun-2026-11-09"})
        self.assertEqual((out, fake.calls), ([], []))
        # 11 noyabr: 13:00-da siyahı hələ yoxdur -> «-gozle» açarı; pəncərədə ikinci sorğu yoxdur; 15:00-da bir də yoxlanır
        out, fake = self.run_at(at(2026, 11, 11, 13, 5))
        self.assertEqual([(i["key"], i["worth"]) for i in out], [("vikipediya-gun-2026-11-10-gozle", False)])
        self.assertEqual(len(fake.calls), 1)
        waiting = {i["key"] for i in out}
        out, fake = self.run_at(at(2026, 11, 11, 13, 25), done=waiting)
        self.assertEqual((out, fake.calls), ([], []))
        out, fake = self.run_at(at(2026, 11, 11, 15, 5), done=waiting)
        self.assertEqual([(i["key"], i["worth"]) for i in out], [("vikipediya-gun-2026-11-10", False)])
        self.assertEqual(len(fake.calls), 1)
        ready = table(**{m.FEED_URL.format(D(2026, 11, 11)): raw("wiki-feed-2026-11-10.json").replace(b"2026-11-09Z", b"2026-11-10Z")})
        out, fake = self.run_at(at(2026, 11, 11, 15, 5), done=waiting, tbl=ready)
        self.assertEqual([(i["key"], i["worth"], i["slot"]) for i in out], [("vikipediya-gun-2026-11-10", True, "15:00")])

    def test_wikipedia_single_try_on_friday_and_on_the_month_day(self):
        feed = raw("wiki-feed-2026-11-10.json")
        fri = table(**{m.FEED_URL.format(D(2026, 11, 13)): feed.replace(b"2026-11-09Z", b"2026-11-12Z")})
        out, fake = self.run_at(at(2026, 11, 13, 13, 5), tbl=fri)
        self.assertEqual((out, fake.calls), ([], []))
        out, fake = self.run_at(at(2026, 11, 13, 15, 5), tbl=fri)
        self.assertEqual([(i["key"], i["worth"]) for i in out], [("vikipediya-gun-2026-11-12", True)])
        mon = table(**{m.FEED_URL.format(D(2026, 11, 2)): feed.replace(b"2026-11-09Z", b"2026-11-01Z")})
        out, fake = self.run_at(at(2026, 11, 2, 13, 5), tbl=mon)
        self.assertEqual((out, fake.calls), ([], []))
        out, fake = self.run_at(at(2026, 11, 2, 13, 35), tbl=mon)
        self.assertEqual([(i["key"], i["worth"]) for i in out], [("vikipediya-ay-2026-10", True)])
        self.assertEqual(len(fake.calls), 2)
        out, fake = self.run_at(at(2026, 11, 2, 13, 50), done={"vikipediya-ay-2026-10"}, tbl=mon)
        self.assertEqual((out, fake.calls), ([], []))
        out, fake = self.run_at(at(2026, 11, 2, 15, 5), tbl=mon)
        self.assertEqual([i["key"] for i in out], ["vikipediya-gun-2026-11-01"])
        out, fake = self.run_at(at(2026, 11, 3, 13, 35), tbl=mon)   # ayın 3-ü: aylıq xəbər yoxdur
        self.assertNotIn("vikipediya-ay-2026-10", [i["key"] for i in out])

    def test_requests_per_day_stay_within_ten(self):
        """Hər 10 dəqiqədən bir çağırış, canlı qaytarılan bütün açarları done-a yazır: ən ağır günlər."""
        feed = raw("wiki-feed-2026-11-10.json")
        for day, label in ((D(2026, 11, 10), "çərşənbə axşamı"), (D(2026, 11, 11), "çərşənbə: kino, Vikipediya iki cəhd"),
                           (D(2026, 11, 13), "cümə: həftəsonu afişası"), (D(2026, 11, 2), "aylıq xəbərin günü")):
            tbl = table()
            tbl.setdefault(m.FEED_URL.format(day), feed.replace(b"2026-11-09Z", (day - m.DAY).isoformat().encode() + b"Z"))
            tbl[m.sparql_url(day)] = sparql(wd("Q1", "Birinci Sınaqov", f"1926-{day:%m-%d}", sl=8), wd("Q2", "İkinci Sınaqov", f"1951-{day:%m-%d}"))
            tbl[ox.WIKI_API.format(f"{day.day}_{ox.MONTHS[day.month - 1]}")] = raw("day-10_noyabr.json")
            done, total = set(), 0
            for minute in range(0, 24 * 60, 10):
                fake = Fake(tbl)
                for i in m.items(ROOT, at(day.year, day.month, day.day, minute // 60, minute % 60), fake, done):
                    done.add(i["key"])
                total += len(fake.calls)
            self.assertLessEqual(total, 10, label)
            self.assertGreaterEqual(total, 5, label)

    def test_garbage_from_every_source_never_raises(self):
        for bad in (b"", b"<html>", b"[]", b"null", b"\xff\xfe", TimeoutError(), urllib.error.URLError("x")):
            for now in (at(2026, 11, 12, 9, 5), at(2026, 11, 12, 10, 5), at(2026, 11, 13, 12, 5), at(2026, 11, 11, 12, 5),
                        at(2026, 11, 12, 13, 5), at(2026, 11, 12, 15, 5), at(2026, 11, 2, 13, 35)):
                out = m.items(ROOT, now, Fake({"https://*": bad}))
                self.assertTrue(out)
                for i in out:
                    self.assertFalse(i["worth"])
                    self.assertTrue(i["why"])
                    self.assertTrue(KEYS <= set(i))

    def test_headers_timeouts_and_no_email(self):
        fake = Fake()
        for now in (at(2026, 11, 10, 9, 5), at(2026, 11, 12, 10, 5), at(2026, 11, 11, 12, 5), at(2026, 11, 10, 13, 5), at(2026, 11, 2, 13, 35)):
            m.items(ROOT, now, fake)
        self.assertGreaterEqual(len(fake.calls), 10)
        for url, timeout, headers in fake.calls:
            self.assertLessEqual(timeout, 15)
            self.assertNotIn("@", url + json.dumps(headers))
            host = urllib.parse.urlsplit(url).hostname
            if host.endswith(WIKI_HOSTS):
                self.assertEqual(headers.get("User-Agent"), UA, url)

    def test_deterministic_and_naive_or_text_time(self):
        a = m.items(ROOT, at(2026, 11, 12, 10, 5), Fake())
        b = m.items(ROOT, "2026-11-12T10:05:00+04:00", Fake())
        c = m.items(ROOT, datetime.datetime(2026, 11, 12, 6, 5, tzinfo=datetime.timezone.utc), Fake())
        self.assertEqual(a, b)
        self.assertEqual(a, c)


class SinaqTest(unittest.TestCase):
    def test_sample_run_with_saved_responses(self):
        fake = Fake()
        with patch.object(m.time, "sleep") as sleep:
            md = m.sinaq(ROOT, at(2026, 11, 10, 13, 10), fake)
        out = "\n".join(md)
        for head in ("## Bu an dərc olunacaqlar", "## 1. «Günün afişası»", "## 2. «Həftəsonu afişası»", "## 3. «Həftənin kino premyeraları»",
                     "## 4. «Dünən Vikipediyada ən çox oxunanlar»", "## 5. «Ayın ən çox oxunanları»", "## 6. «Yubileylər»",
                     "## Sorğular və GitHub-dan əlçatanlıq"):
            self.assertIn(head, out)
        self.assertIn("- 13:00 · vikipediya-gun-2026-11-09 · ✅", out)
        self.assertIn("### Həftəsonu Bakı səhnələrində:", out)
        self.assertIn("### 12 noyabrdan kinoteatrlarda:", out)
        self.assertIn("### Azərbaycan bəstəkarı Rəhilə Həsənovanın anadan olmasından 75 il keçir", out)
        self.assertIn("✅ Dərc olunardı", out)
        self.assertIn("⏭ Dərc olunmazdı:", out)
        self.assertNotIn("gözlənilməz xəta", out)
        self.assertNotIn("Əliyev\n", out)
        self.assertLessEqual(len(fake.calls), 20)
        self.assertTrue(sleep.called)

    def test_sample_run_survives_a_dead_network(self):
        with patch.object(m.time, "sleep"):
            md = m.sinaq(ROOT, at(2026, 11, 13, 12, 10), Fake({}))
        out = "\n".join(md)
        self.assertIn("## 6. «Yubileylər»", out)
        self.assertNotIn("✅ Dərc olunardı", out)
        self.assertNotIn("Traceback", out)

    def test_cli(self):
        buf = io.StringIO()
        with patch.object(m, "_default_fetch", return_value=Fake()), patch.object(m.time, "sleep"), contextlib.redirect_stdout(buf):
            code = m.main(["--sinaq", "--root", str(ROOT), "--now", "2026-11-10T13:10+04:00"])
        self.assertEqual(code, 0)
        self.assertTrue(buf.getvalue().startswith("# Mədəniyyət və bilik xəbərləri"))
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            self.assertEqual(m.main([]), 0)
        self.assertIn("--sinaq", buf.getvalue())


if __name__ == "__main__":
    unittest.main()
