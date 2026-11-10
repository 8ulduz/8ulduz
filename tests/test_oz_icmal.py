"""İcmal xəbərləri (oz_icmal.py, faza 1): «Günün bələdçisi» və «Həftənin rəqəmləri». Şəbəkə yoxdur: sorğular saxta fetch ilə.
Real məlumat (tests/fixtures/oz_icmal/): main-in 2026-11-10 tarixli data/futbol fayllarından kəsiklər; Open-Meteo-nun 6 şəhər
üçün 10 noyabr və 1–8 noyabr cavabları, AMB-nin 06.11.2026 və 30.10.2026 bülletenləri (kəsik), seismology.az siyahısının
cədvəli — hamısı 2026-11-10-da alınıb."""
import contextlib
import datetime
import io
import json
import pathlib
import re
import tempfile
import unittest
import urllib.parse
from types import SimpleNamespace
from unittest.mock import patch

import oz_icmal as ic
import oz_xeber as ox

ROOT = pathlib.Path(__file__).resolve().parent.parent
FIX = ROOT / "tests" / "fixtures" / "oz_icmal"
NET = FIX / "net"
BAKU = ic.BAKU
D = datetime.date
UTC = datetime.timezone.utc


def at(y, m, d, hh=8, mm=0):
    return datetime.datetime(y, m, d, hh, mm, tzinfo=BAKU)


def net(name):
    return (NET / name).read_bytes()


def amb_xml(day, usd, eur):
    return (f'<?xml version="1.0" encoding="UTF-8"?><ValCurs Date="{day:%d.%m.%Y}" Name="AZN məzənnələri">'
            f'<ValType Type="Xarici valyutalar"><Valute Code="USD"><Nominal>1</Nominal><Name>1 ABŞ dolları</Name>'
            f'<Value>{usd}</Value></Valute><Valute Code="EUR"><Nominal>1</Nominal><Name>1 Avro</Name>'
            f'<Value>{eur}</Value></Valute></ValType></ValCurs>').encode("utf-8")


def om_doc(start, days, lat=40.4093, lon=49.8671):
    """Bir yerin Open-Meteo cavabı. days: [(kod, ən aşağı, ən yüksək, yağıntı ehtimalı, külək)]."""
    return {"latitude": lat, "longitude": lon, "daily": {
        "time": [(start + datetime.timedelta(days=i)).isoformat() for i in range(len(days))],
        "weather_code": [x[0] for x in days], "temperature_2m_min": [x[1] for x in days],
        "temperature_2m_max": [x[2] for x in days], "precipitation_probability_max": [x[3] for x in days],
        "wind_speed_10m_max": [x[4] for x in days]}}


def write(root, name, doc):
    path = pathlib.Path(root) / "data" / "futbol"
    path.mkdir(parents=True, exist_ok=True)
    (path / f"{name}.json").write_text(json.dumps(doc, ensure_ascii=False), encoding="utf-8")


class Net:
    """Saxta fetch: ünvan -> cavab (və ya xəta); olmayan ünvan şəbəkə xətasıdır. calls bütün sorğuları saxlayır."""

    def __init__(self, routes):
        self.routes, self.calls = dict(routes), []

    def __call__(self, url, timeout=None, headers=None):
        self.calls.append(url)
        value = self.routes.get(url, OSError(f"şəbəkə yoxdur: {url}"))
        if isinstance(value, Exception):
            raise value
        return value


def real_net():
    return Net({
        ic.om_url(D(2026, 11, 10)): net("om-2026-11-10.json"),
        ic.om_url(D(2026, 11, 8), 7): net("om-2026-11-01_2026-11-08.json"),
        ox.AMB_URL.format(D(2026, 11, 10)): net("amb-06.11.2026.xml"),
        ox.AMB_URL.format(D(2026, 11, 8)): net("amb-06.11.2026.xml"),
        ox.AMB_URL.format(D(2026, 10, 30)): net("amb-30.10.2026.xml"),
        ox.SEYS_LIST: net("seys.html"),
    })


class FlexNet:
    """İstənilən gün üçün saxta cavab: Open-Meteo sorğudakı aralıq üçün, AMB bülleteni sorğu günündən bir gün əvvəlindir."""

    def __init__(self, code=3, lo=-3.5, hi=4.2):
        self.code, self.lo, self.hi, self.calls = code, lo, hi, []

    def __call__(self, url, timeout=None, headers=None):
        self.calls.append(url)
        if url.startswith("https://api.open-meteo.com/"):
            q = urllib.parse.parse_qs(urllib.parse.urlparse(url).query)
            start, end = D.fromisoformat(q["start_date"][0]), D.fromisoformat(q["end_date"][0])
            days = [(self.code, self.lo, self.hi, 40, 9.5)] * ((end - start).days + 1)
            return json.dumps([om_doc(start, days, lat, lon) for _, lat, lon in ic.CITIES]).encode("utf-8")
        m = re.search(r"/currencies/(\d\d)\.(\d\d)\.(\d{4})\.xml$", url)
        if m:
            d = D(int(m.group(3)), int(m.group(2)), int(m.group(1))) - datetime.timedelta(days=1)
            return amb_xml(d, 1.7, round(1.9 + d.day / 1000, 4))
        if url == ox.SEYS_LIST:
            return net("seys.html")
        raise OSError(url)


def seys_row(qid, ml, area, utc, depth=10):
    return (f'<tr> <td> <div class="score scoreBlue">ML {ml}</div> </td> <td> <h4 class="tableLink">'
            f'<a href="https://seismology.az/az/zelzele/{qid}">{area}</a></h3> </td> <td class="white-space-nowrap">'
            f'{utc:%d.%m.%Y} | {utc:%H:%M:%S} UTC</td> <td class="white-space-nowrap"> <div class="coordinates"> '
            f'<span>40.00 N</span> <span>48.00 E</span> </div> </td> <td>{depth}km</td> </tr>')


B10 = [
    "Bakı: buludlu hava, temperatur 6–9,8 dərəcə, yağıntı ehtimalı 5%, külək saniyədə 7,1 metrə qədər",
    "Gəncə: buludlu hava, temperatur 2,3–9,1 dərəcə, yağıntı ehtimalı 0%, külək saniyədə 4,1 metrə qədər",
    "Sumqayıt: buludlu hava, temperatur 5,6–10,1 dərəcə, yağıntı ehtimalı 8%, külək saniyədə 7,8 metrə qədər",
    "Lənkəran: arabir zəif yağış, temperatur 4,3–12 dərəcə, yağıntı ehtimalı 8%, külək saniyədə 3,3 metrə qədər",
    "Şəki: buludlu hava, temperatur 2–6,9 dərəcə, yağıntı ehtimalı 0%, külək saniyədə 2 metrə qədər",
    "Naxçıvan: əsasən açıq hava, temperatur -1,2 ilə 8,3 dərəcə, yağıntı ehtimalı 0%, külək saniyədə 1,9 metrə qədər",
    "AMB-nin son rəsmi məzənnələri (6 noyabr üçün): 1 ABŞ dolları 1,7000 manat, 1 avro 1,9037 manat",
    "II Liqa, 10-cu tur: «Difai» – «Zəngəzur» (14:00), «Şirvan» – «Marafon» (15:00), «Şəki» – «Dinamo» (15:00)",
    "Bu gün Sülh və İnkişaf Naminə Ümumdünya Elm Günüdür. 10 noyabr iş günü deyil.",
]
B8 = [
    "Bakı: zəif yağış, temperatur 9,2–13,4 dərəcə, yağıntı ehtimalı 78%, külək saniyədə 12,9 metrə qədər",
    "Gəncə: zəif yağış, temperatur 6,8–10,3 dərəcə, yağıntı ehtimalı 70%, külək saniyədə 6,6 metrə qədər",
    "Sumqayıt: zəif yağış, temperatur 9,4–14,1 dərəcə, yağıntı ehtimalı 75%, külək saniyədə 14,3 metrə qədər",
    "Lənkəran: zəif yağış, temperatur 10,2–15,1 dərəcə, yağıntı ehtimalı 100%, külək saniyədə 6,2 metrə qədər",
    "Şəki: arabir zəif yağış, temperatur 5,9–9,1 dərəcə, yağıntı ehtimalı 100%, külək saniyədə 5,1 metrə qədər",
    "Naxçıvan: arabir zəif yağış, temperatur 5,6–10,4 dərəcə, yağıntı ehtimalı 80%, külək saniyədə 3,1 metrə qədər",
    "AMB-nin son rəsmi məzənnələri (6 noyabr üçün): 1 ABŞ dolları 1,7000 manat, 1 avro 1,9037 manat",
    "Premyer Liqa, 11-ci tur: «İmişli» – «Sumqayıt» (15:00), «Sabah» – «Şamaxı» (17:30)",
    "II Liqa, 10-cu tur: «Şəmkir» – «Ağstafa Gəncləri» (14:00)",
    "Türkiyə Super Liqası: «Çorum» – «Fenerbahçe» (17:00), «Alanyaspor» – «Trabzonspor» (19:30), "
    "«Beşiktaş» – «Gençlerbirliği» (22:00)",
    "İspaniya La Liqası: «Atlético Madrid» – «Barcelona» (gecə 00:00)",
    "İngiltərə Premyer Liqası: «Crystal Palace» – «Liverpool» (18:00), «Sunderland» – «Chelsea» (18:00), "
    "«Manchester United» – «Aston Villa» (20:30)",
    "Bu gün Zəfər Günüdür.",
]
R8 = [
    "AMB-nin rəsmi məzənnəsinə görə, 1 avro 30 oktyabrda 1,9019, 6 noyabrda 1,9037 manat olub: avro bir həftədə 0,0018 manat "
    "(0,09%) bahalaşıb. Dolların rəsmi məzənnəsi dəyişməyib: 1,7000 manat.",
    "Open-Meteo-nun model məlumatına görə, Bakıda son 7 günün ən yüksək temperaturu 20,5 dərəcə (2 noyabr), ən aşağı "
    "temperaturu 8,9 dərəcə (6 noyabr) olub.",
    "Premyer Liqada 7 oyunda 17 qol vurulub (10-cu və 11-ci turlar). Ən çox qol «Şamaxı» – «Neftçi» oyununda vurulub: 2:3.",
]


class FormatTest(unittest.TestCase):
    def test_numbers_dates_and_rounds(self):
        self.assertEqual([ic._n1(x) for x in (9.8, 10.0, 6, -1.2, -0.04, 7.07, 1.97, 7.75)],
                         ["9,8", "10", "6", "-1,2", "0", "7,1", "2", "7,8"])
        self.assertEqual([ic._rng(6, 9.8), ic._rng(-1.2, 8.3), ic._rng(-5, -1), ic._rng(3, 3)],
                         ["6–9,8", "-1,2 ilə 8,3", "-5 ilə -1", "3"])
        self.assertEqual(ic._span(D(2026, 11, 1), D(2026, 11, 7)), "1–7 noyabr")
        self.assertEqual(ic._span(D(2026, 10, 26), D(2026, 11, 1)), "26 oktyabr – 1 noyabr")
        self.assertEqual(ic._days_text([D(2026, 11, 4), D(2026, 11, 2)]), "2 və 4 noyabr")
        self.assertEqual(ic._days_text([D(2026, 10, 31), D(2026, 11, 2)]), "31 oktyabr və 2 noyabr")
        self.assertEqual([ic._tur("10"), ic._tur("Qrup 2"), ic._tur("1/8 final"), ic._tur("")],
                         ["10-cu tur", "2-ci qrup", "1/8 final", ""])
        self.assertEqual(ic._join(["A", "B", "C"]), "A, B və C")

    def test_weather_codes_are_fixed_phrases(self):
        wmo = {0, 1, 2, 3, 45, 48, 51, 53, 55, 56, 57, 61, 63, 65, 66, 67, 71, 73, 75, 77, 80, 81, 82, 85, 86, 95, 96, 99}
        self.assertEqual(set(ic.SKY), wmo, "Open-Meteo-nun bütün WMO kodları cədvəldədir")
        for phrase in ic.SKY.values():
            self.assertRegex(phrase, r"^[a-zçəğıöşü ]+$")
        self.assertEqual(ic._city_line("Bakı", {"code": 4, "tmin": 1, "tmax": 2, "rain": None, "wind": None}),
                         "Bakı: temperatur 1–2 dərəcə", "bilinməyən kod üçün təsvir uydurulmur")
        self.assertEqual(ic._weather_frag({"code": 71, "tmin": -2, "tmax": 1}), "Bakıda zəif qar gözlənilir, -2 ilə 1 dərəcə")
        self.assertEqual(ic._weather_frag({"code": 2, "tmin": 5, "tmax": 9}), "Bakıda dəyişkən buludlu hava, 5–9 dərəcə")
        self.assertEqual(ic._weather_frag({"code": None, "tmin": 5, "tmax": 9}), "Bakıda 5–9 dərəcə")


class WeatherTest(unittest.TestCase):
    def test_url_is_one_request_for_six_cities(self):
        url = ic.om_url(D(2026, 11, 10))
        self.assertIn("latitude=40.4093,40.6828,40.5897,38.7529,41.1919,39.2089", url)
        self.assertIn("longitude=49.8671,46.3606,49.6686,48.8475,47.1706,45.4122", url)
        self.assertIn("&timezone=Asia%2FBaku&wind_speed_unit=ms&start_date=2026-11-10&end_date=2026-11-10", url)
        self.assertTrue(ic.om_url(D(2026, 11, 8), 7).endswith("start_date=2026-11-01&end_date=2026-11-08"))

    def test_real_forecast(self):
        om = ic.parse_om(net("om-2026-11-10.json"))
        self.assertEqual(list(om), [c[0] for c in ic.CITIES])
        self.assertEqual(om["Naxçıvan"][D(2026, 11, 10)], {"code": 1, "tmax": 8.3, "tmin": -1.2, "rain": 0.0, "wind": 1.92})
        self.assertEqual(om["Lənkəran"][D(2026, 11, 10)]["code"], 80)
        week = ic.parse_om(net("om-2026-11-01_2026-11-08.json"))
        self.assertEqual(len(week["Bakı"]), 8)
        self.assertEqual(week["Bakı"][D(2026, 11, 2)]["tmax"], 20.5)

    def test_bad_or_shuffled_answers(self):
        self.assertEqual(ic.parse_om(b"{pozuq"), {})
        self.assertEqual(ic.parse_om(b'{"error": true, "reason": "Parameter start_date is out of range"}'), {})
        docs = json.loads(net("om-2026-11-10.json").decode("utf-8"))
        shuffled = ic.parse_om(json.dumps(docs[::-1]).encode("utf-8"))
        self.assertNotIn("Bakı", shuffled, "sıra qarışıbsa Bakının yerinə Naxçıvanın proqnozu yazılmır")
        one = ic.parse_om(json.dumps(docs[0]).encode("utf-8"))
        self.assertEqual(list(one), ["Bakı"], "bir yerin cavabı obyektdir")
        self.assertIsNone(ic._weather({"Gəncə": one["Bakı"]}, D(2026, 11, 10)), "Bakısız hava hissəsi yoxdur")


class BeledciTest(unittest.TestCase):
    def test_real_day_10_november(self):
        n = real_net()
        rows = ic.items(FIX, at(2026, 11, 10, 8, 0), fetch=n)
        self.assertEqual([i["key"] for i in rows], ["beledci-2026-11-10"])
        item = rows[0]
        self.assertEqual(item["body"], B10)
        self.assertEqual(item["title"], "Günün bələdçisi, 10 noyabr: Bakıda buludlu hava, 6–9,8 dərəcə; II Liqada 3 oyun")
        self.assertEqual(item["lead"], "Open-Meteo-nun proqnozuna görə, bu gün Bakıda buludlu hava gözlənilir, temperatur "
                                       "6–9,8 dərəcə arasında olacaq. Bu gün II Liqada 3 oyun keçiriləcək.")
        self.assertEqual((item["credit"], item["link"]),
                         ("Open-Meteo, Azərbaycan Mərkəzi Bankı, Peşəkar Futbol Liqası", "https://open-meteo.com/"))
        self.assertEqual((item["topic"], item["slot"], item["kind"], item["worth"], item["list"]),
                         ("icmal", "08:00", "beledci", True, True))
        self.assertEqual(item["missing"], {})
        self.assertEqual(n.calls, [ic.om_url(D(2026, 11, 10)), ox.AMB_URL.format(D(2026, 11, 10))], "gündə 2 sorğu")
        self.assertNotIn("10 noyabr üçün", " ".join(item["body"]), "AMB-nin günü bülletenin özündəndir, sorğunun günü deyil")

    def test_real_sunday_8_november_with_five_game_lines(self):
        n = real_net()
        rows = ic.items(FIX, at(2026, 11, 8, 8, 0), fetch=n)
        self.assertEqual([i["key"] for i in rows], ["beledci-2026-11-08", "reqemler-2026-11-08"])
        item = rows[0]
        self.assertEqual(item["body"], B8)
        self.assertEqual(item["title"], "Günün bələdçisi, 8 noyabr: Bakıda zəif yağış gözlənilir, 9,2–13,4 dərəcə; "
                                        "Azərbaycan futbolunda 3 oyun")
        self.assertEqual(item["lead"], "Open-Meteo-nun proqnozuna görə, bu gün Bakıda zəif yağış gözlənilir, temperatur "
                                       "9,2–13,4 dərəcə arasında olacaq. Bu gün Premyer Liqada 2 və II Liqada 1 oyun "
                                       "keçiriləcək. Xarici klublardan «Fenerbahçe», «Trabzonspor», «Beşiktaş» və «Barcelona» "
                                       "meydana çıxacaq.")
        self.assertEqual(item["credit"], "Open-Meteo, Azərbaycan Mərkəzi Bankı, Peşəkar Futbol Liqası, TheSportsDB")
        self.assertEqual(len(n.calls), 4, "bazar günü iki xəbər: Open-Meteo və AMB bir dəfə soruşulur")
        self.assertEqual(set(n.calls), {ic.om_url(D(2026, 11, 8), 7), ox.AMB_URL.format(D(2026, 11, 8)),
                                        ox.AMB_URL.format(D(2026, 10, 30)), ox.SEYS_LIST})

    def test_national_team_day_without_requests(self):
        item, _ = ic.beledci_item(FIX, D(2026, 11, 13), ic._Get(None))
        self.assertEqual(item["body"], ["Millətlər Liqası D, 2-ci qrup: Lixtenşteyn – Azərbaycan (23:45)"])
        self.assertEqual(item["title"], "Günün bələdçisi, 13 noyabr: Azərbaycan millisi Lixtenşteyn ilə oynayacaq")
        self.assertEqual(item["lead"], "Azərbaycan millisi bu gün Millətlər Liqası D çərçivəsində səfərdə Lixtenşteyn ilə "
                                       "oynayacaq (Bakı vaxtı ilə saat 23:45-də).")
        self.assertTrue(item["worth"])
        self.assertIn("sorğu funksiyası verilməyib", item["missing"]["hava"])
        self.assertIn("sorğu funksiyası verilməyib", item["missing"]["AMB"])
        self.assertEqual((item["credit"], item["link"]),
                         ("Vikipediya", "https://en.wikipedia.org/wiki/2026%E2%80%9327_UEFA_Nations_League_D"))
        night = ic.day_games(FIX, D(2026, 11, 12))
        self.assertEqual(night, [], "Avroliqa basketboldur: «Real Madrid» – «Crvena zvezda» yazılmır")

    def test_azerbaijani_club_in_europe_and_night_games(self):
        item, _ = ic.beledci_item(FIX, D(2026, 11, 25), ic._Get(None))
        self.assertEqual(item["body"], [
            "Çempionlar Liqası, 5-ci tur: «Sabah» – «Barcelona» (21:45)",
            "Çempionlar Liqası: «Club Brugge» – «Liverpool» (gecə 00:00), «Inter Milan» – «VfB Stuttgart» (gecə 00:00), "
            "«Shakhtar Donetsk» – «Fenerbahçe» (gecə 00:00)",
            "Bu gün Qadınlara Qarşı Zorakılığın Aradan Qaldırılması Beynəlxalq Günüdür.",
        ], "«Sabah»ın oyunu xarici sətirdə təkrarlanmır; xarici sətirdə 3 oyun, əvvəl Türkiyə klubu")
        self.assertEqual(item["title"], "Günün bələdçisi, 25 noyabr: «Sabah» Çempionlar Liqasında «Barcelona» ilə oynayacaq")
        self.assertEqual(item["lead"], "«Sabah» bu gün Çempionlar Liqasında doğma meydanda «Barcelona» ilə qarşılaşacaq "
                                       "(Bakı vaxtı ilə saat 21:45-də). Xarici klublardan «Liverpool», «Inter Milan» və "
                                       "«Fenerbahçe» meydana çıxacaq.")
        lines = [g["text"] for g in ic.day_games(FIX, D(2026, 11, 24))]
        self.assertEqual(lines, ["Çempionlar Liqası: «Galatasaray» – «Aston Villa» (21:45), «Arsenal» – «Borussia Dortmund» "
                                 "(gecə 00:00), «Real Madrid» – «PSV Eindhoven» (gecə 00:00)"])

    def test_placeholder_and_nominal_schedules(self):
        lines = [g["text"] for g in ic.day_games(FIX, D(2026, 11, 22))]
        self.assertEqual(lines, ["Premyer Liqa, 12-ci tur: «Araz-Naxçıvan» – «Neftçi» (14:30), «Kəpəz» – «Qarabağ» (17:00)",
                                 "Türkiyə Super Liqası: «Konyaspor» – «Beşiktaş» (17:00)",
                                 "İngiltərə Premyer Liqası: «Liverpool» – «Manchester United» (20:30)"],
                         "La Liqanın 13-cü turunun 10 oyunu 16:00Z-dədir (yer tutucu): «Barcelona» və «Real Madrid» yazılmır")
        lines = [g["text"] for g in ic.day_games(FIX, D(2026, 11, 21))]
        self.assertIn("İngiltərə Premyer Liqası: «Manchester City» – «Fulham» (16:30), «Chelsea» – «Leeds United» (19:00), "
                      "«Newcastle United» – «Arsenal» (21:30)", lines, "5 oyunun eyni saatda olması yer tutucu deyil")
        for day in (D(2026, 11, 27), D(2026, 11, 15), D(2026, 12, 1)):
            self.assertEqual(ic.day_games(FIX, day), [], f"{day}: pfl.az-da saatsız və stadionsuz tur yazılmır")
        item, why = ic.beledci_item(FIX, D(2026, 11, 27), ic._Get(None))
        self.assertFalse(item["worth"])
        self.assertIn("nə hava proqnozu, nə də bu günün oyunları var", why)

    def test_window_postponed_and_placeholder_rules(self):
        teams = {t: {"name": n} for t, n in (("galatasaray", "Galatasaray"), ("goztepe", "Göztepe"), ("rizespor", "Rizespor"),
                                              ("konyaspor", "Konyaspor"), ("samsunspor", "Samsunspor"), ("kasimpasa", "Kasımpaşa"))}
        with tempfile.TemporaryDirectory() as tmp:
            write(tmp, "turkiye", {"name": "Süper Liq", "sport": "football", "source": "TheSportsDB",
                                   "source_url": "https://www.thesportsdb.com/", "teams": teams, "games": [
                {"date": "2026-12-05T03:00:00+00:00", "home": "galatasaray", "away": "goztepe", "played": False, "round": "14"},
                {"date": "2026-12-06T03:59+04:00", "home": "rizespor", "away": "galatasaray", "played": False, "round": "15"},
                {"date": "2026-12-06T04:00+04:00", "home": "konyaspor", "away": "galatasaray", "played": False, "round": "16"},
                {"date": "2026-12-05T13:00:00+00:00", "home": "galatasaray", "away": "samsunspor", "played": False,
                 "round": "17", "state": "off"},
                {"date": "2026-12-05T16:00:00+00:00", "home": "kasimpasa", "away": "galatasaray", "played": False, "round": "18"}]})
            self.assertEqual([g["text"] for g in ic.day_games(tmp, D(2026, 12, 5))],
                             ["Türkiyə Super Liqası: «Kasımpaşa» – «Galatasaray» (20:00), «Rizespor» – «Galatasaray» (gecə 03:59)"],
                             "07:00 və sabahkı 04:00 pəncərədən kənardır, təxirə salınan oyun yazılmır")
            same = [{"date": "2026-12-05T16:00:00+00:00", "home": h, "away": "galatasaray", "played": False, "round": "19"}
                    for h in ("goztepe", "rizespor", "konyaspor")]
            write(tmp, "turkiye", {"name": "Süper Liq", "sport": "football", "source": "TheSportsDB", "teams": teams,
                                   "games": same})
            self.assertEqual(ic.day_games(tmp, D(2026, 12, 5)), [], "turun 3 oynanmamış oyunu eyni saatdadır: yer tutucu")
            same[0] = dict(same[0], date="2026-12-05T13:00:00+00:00")
            write(tmp, "turkiye", {"name": "Süper Liq", "sport": "football", "source": "TheSportsDB", "teams": teams,
                                   "games": same})
            self.assertEqual(len(ic.day_games(tmp, D(2026, 12, 5))[0]["games"]), 3, "saatlar fərqlidir: cədvəl realdır")
            write(tmp, "premyer-liqa", {"source": "pfl.az", "teams": {"sabah": {"name": "Sabah"}, "neftci": {"name": "Neftçi"}},
                                        "games": [{"home": "sabah", "away": "neftci", "date": "2026-12-05T18:00+04:00",
                                                   "played": False, "round": "15"}]})
            self.assertNotIn("Premyer Liqa", " ".join(g["text"] for g in ic.day_games(tmp, D(2026, 12, 5))),
                             "pfl.az-da stadionsuz oyunun günü şərtidir")

    def test_five_lines_and_their_order(self):
        with tempfile.TemporaryDirectory() as tmp:
            day = "2026-12-05T"
            write(tmp, "premyer-liqa", {"source": "pfl.az", "teams": {"sabah": {"name": "Sabah"}, "neftci": {"name": "Neftçi"}},
                                        "games": [{"home": "neftci", "away": "sabah", "date": day + "17:00+04:00",
                                                   "played": False, "stadium": "Neftçi Arena", "round": "15"}]})
            for fid, home, away in (("kubok", "zire", "kepez"), ("i-liqa", "moik", "sebail"), ("ii-liqa", "seki", "difai")):
                write(tmp, fid, {"source": "pfl.az", "teams": {home: {"name": home.title()}, away: {"name": away.title()}},
                                 "games": [{"home": home, "away": away, "date": day + "13:00+04:00", "played": False,
                                            "stadium": "Stadion", "round": "5"}]})
            write(tmp, "ml-x", {"name": "Yoldaşlıq oyunları", "nat": True, "sport": "football", "source": "Vikipediya",
                                "url": "https://en.wikipedia.org/wiki/x",
                                "teams": {"azerbaycan": {"name": "Azərbaycan"}, "qazaxistan": {"name": "Qazaxıstan"}},
                                "games": [{"date": day + "14:00:00+00:00", "home": "azerbaycan", "away": "qazaxistan",
                                           "played": False}]})
            write(tmp, "cl", {"name": "Çempionlar Liqası", "sport": "football", "source": "OpenLigaDB (www.openligadb.de)",
                              "source_url": "https://www.openligadb.de/",
                              "teams": {"sabah": {"name": "Sabah"}, "porto": {"name": "Porto"}},
                              "games": [{"date": day + "17:45:00+00:00", "home": "porto", "away": "sabah", "played": False,
                                         "round": "6"}]})
            write(tmp, "turkiye", {"name": "Süper Liq", "sport": "football", "source": "TheSportsDB",
                                   "teams": {"galatasaray": {"name": "Galatasaray"}, "goztepe": {"name": "Göztepe"}},
                                   "games": [{"date": day + "16:00:00+00:00", "home": "galatasaray", "away": "goztepe",
                                              "played": False, "round": "14"}]})
            groups = ic.day_games(tmp, D(2026, 12, 5))
            self.assertEqual([g["text"] for g in groups], [
                "Yoldaşlıq oyunları: Azərbaycan – Qazaxıstan (18:00)",
                "Çempionlar Liqası, 6-cı tur: «Porto» – «Sabah» (21:45)",
                "Premyer Liqa, 15-ci tur: «Neftçi» – «Sabah» (17:00)",
                "Azərbaycan Kuboku, 5-ci tur: «Zire» – «Kepez» (13:00)",
                "I Liqa, 5-ci tur: «Moik» – «Sebail» (13:00)",
            ], "ən çox 5 sətir: II Liqa və xarici klub düşür")
            item, _ = ic.beledci_item(tmp, D(2026, 12, 5), ic._Get(None))
            self.assertTrue(item["lead"].startswith(
                "Azərbaycan millisi bu gün Yoldaşlıq oyunları çərçivəsində doğma meydanda Qazaxıstan ilə oynayacaq "
                "(Bakı vaxtı ilə saat 18:00-də). «Sabah» bu gün Çempionlar Liqasında səfərdə «Porto» ilə qarşılaşacaq "
                "(Bakı vaxtı ilə saat 21:45-də). Bu gün Premyer Liqada 1, Azərbaycan Kubokunda 1 və I Liqada 1 oyun keçiriləcək."),
                item["lead"])
            self.assertEqual(item["title"], "Günün bələdçisi, 5 dekabr: Azərbaycan millisi Qazaxıstan ilə oynayacaq")

    def test_amb_uses_the_bulletins_own_date(self):
        def brief(xml):
            n = Net({ic.om_url(D(2026, 11, 10)): net("om-2026-11-10.json"), ox.AMB_URL.format(D(2026, 11, 10)): xml})
            return ic.beledci_item(FIX, D(2026, 11, 10), ic._Get(n))[0]
        self.assertIn("AMB-nin son rəsmi məzənnələri (6 noyabr üçün): 1 ABŞ dolları 1,7000 manat, 1 avro 1,9037 manat",
                      brief(net("amb-06.11.2026.xml"))["body"])
        old = brief(amb_xml(D(2026, 10, 20), 1.7, 1.95))
        self.assertFalse([b for b in old["body"] if b.startswith("AMB")])
        self.assertEqual(old["missing"]["AMB"], "son bülleten köhnədir (20 oktyabr)")
        for bad in (amb_xml(D(2026, 11, 11), 1.7, 1.95), b"<html>xeta</html>", b"<ValCurs Date='pozuq'></ValCurs>"):
            item = brief(bad)
            self.assertIn("AMB bülleteni alınmadı", item["missing"]["AMB"])
            self.assertTrue(item["worth"], "AMB-siz də hava və oyunlar var")
        usd_only = brief(b'<ValCurs Date="06.11.2026"><Valute Code="USD"><Value>1.7</Value></Valute></ValCurs>')
        self.assertIn("AMB-nin son rəsmi məzənnəsi (6 noyabr üçün): 1 ABŞ dolları 1,7000 manat", usd_only["body"])

    def test_missing_parts_and_broken_files(self):
        with tempfile.TemporaryDirectory() as tmp:
            write(tmp, "premyer-liqa", {"games": "pozuq"})
            (pathlib.Path(tmp) / "data" / "futbol" / "ml-d.json").write_text("{pozuq", encoding="utf-8")
            n = Net({ic.om_url(D(2026, 11, 10)): b"<html>503</html>"})
            item, why = ic.beledci_item(tmp, D(2026, 11, 10), ic._Get(n))
            self.assertFalse(item["worth"])
            self.assertEqual(set(item["missing"]), {"hava", "AMB", "oyunlar"})
            self.assertEqual(item["missing"]["hava"], "Open-Meteo-nun cavabında bu gün üçün Bakının proqnozu yoxdur")
            self.assertTrue(item["missing"]["AMB"].startswith("AMB bülleteni alınmadı: OSError"))
            self.assertEqual(item["body"], ["Bu gün Sülh və İnkişaf Naminə Ümumdünya Elm Günüdür. 10 noyabr iş günü deyil."])
            self.assertTrue(why)
            n = Net({ic.om_url(D(2026, 11, 10)): net("om-2026-11-10.json")})
            item, _ = ic.beledci_item(tmp, D(2026, 11, 10), ic._Get(n))
            self.assertTrue(item["worth"], "yalnız hava da xəbərdir")
            self.assertEqual(item["title"], "Günün bələdçisi, 10 noyabr: Bakıda buludlu hava, 6–9,8 dərəcə")

    def test_observance_lines(self):
        self.assertEqual(ic._observance(D(2026, 11, 9)), "Bu gün Dövlət Bayrağı Günüdür. Beynəlxalq Elm və Sülh Həftəsi "
                                                         "başlayır. 9 noyabr iş günü deyil.")
        self.assertEqual(ic._observance(D(2026, 11, 8)), "Bu gün Zəfər Günüdür.", "bazar gününün iş günü olmaması yazılmır")
        self.assertEqual(ic._observance(D(2026, 11, 12)), "Bu gün Konstitusiya Günüdür.")
        self.assertEqual(ic._observance(D(2026, 11, 18)),
                         "Bu gün Antimikrob Müqavimət Barədə Ümumdünya Maarifləndirmə Həftəsi başlayır.")
        self.assertEqual(ic._observance(D(2026, 11, 13)), "")
        self.assertEqual(ic._observance(D(2026, 11, 22)), "Bu gün ədliyyə işçilərinin peşə bayramıdır.")

    def test_titles_fit_and_leads_end(self):
        for code in (0, 45, 95, 71):
            fetch = FlexNet(code=code)
            day = D(2026, 11, 1)
            while day <= D(2027, 1, 31):
                for item in ic.items(FIX, at(day.year, day.month, day.day), fetch=fetch):
                    self.assertLessEqual(len(item["title"]), ic.TITLE_MAX, item["title"])
                    self.assertFalse(item["title"].endswith("."), item["title"])
                    self.assertTrue(item["lead"].endswith("."), item["lead"])
                    self.assertNotRegex(" ".join([item["title"], item["lead"], *item["body"]]), r"[А-Яа-яЁё]|\bNone\b|\{")
                day += ic.DAY


class ReqemlerTest(unittest.TestCase):
    def test_real_sunday_8_november(self):
        n = real_net()
        item, why = ic.reqemler_item(FIX, D(2026, 11, 8), ic._Get(n))
        self.assertTrue(item["worth"], why)
        self.assertEqual(item["body"], R8)
        self.assertEqual(item["title"], "Həftənin rəqəmləri, 1–7 noyabr: Premyer Liqada 17 qol, Bakıda ən yüksək temperatur "
                                        "20,5 dərəcə")
        self.assertEqual(item["lead"], "Son 7 gündə (1–7 noyabr) Premyer Liqada 7 oyunda 17 qol vurulub, Bakıda temperatur "
                                       "Open-Meteo-nun model məlumatına görə 8,9–20,5 dərəcə arasında olub.")
        self.assertEqual((item["credit"], item["link"]),
                         ("Azərbaycan Mərkəzi Bankı, Open-Meteo, Peşəkar Futbol Liqası", "https://www.cbar.az/"))
        self.assertEqual(item["missing"], {"zəlzələ": "bu həftə 3,0 və daha güclü zəlzələ qeydə alınmayıb"},
                         "zəlzələ olmayan həftə üçün boş sətir yazılmır")
        self.assertEqual((item["kind"], item["key"], item["slot"], item["topic"]), ("reqemler", "reqemler-2026-11-08", "12:00", "icmal"))
        text = " ".join([item["title"], item["lead"], *item["body"]])
        self.assertNotRegex(text, r"Brent|WTI|[Qq]ızıl|[Bb]itkoin", "bazarın həftəlik dəyişməsi şənbə xəbərindədir")

    def test_quakes_from_the_real_list(self):
        page = net("seys.html").decode("utf-8")
        fact, _ = ic._quakes(page, D(2026, 9, 27), D(2026, 10, 3))
        self.assertEqual(fact["body"], "Respublika Seysmoloji Xidmət Mərkəzinin məlumatına görə, son 7 gündə 3,0 və daha güclü 4 "
                                       "zəlzələ qeydə alınıb: 27 sentyabrda saat 11:14-də Lerikdə (3,2); 29 sentyabrda saat "
                                       "15:50-də Lənkəranda (3,4); 30 sentyabrda saat 01:47-də Xəzər dənizində (3,3); 1 oktyabrda "
                                       "saat 14:51-də Zaqatalada (4,1). Ən güclüsü Zaqatalada qeydə alınan 4,1 maqnitudalı "
                                       "zəlzələ olub.", "29.09 21:47 UTC Bakıda 30 sentyabrdır")
        self.assertEqual((fact["frag"], fact["prio"]), ("Zaqatalada 4,1 maqnitudalı zəlzələ", 1))
        fact, _ = ic._quakes(page, D(2026, 10, 1), D(2026, 10, 1))
        self.assertEqual(fact["body"], "Respublika Seysmoloji Xidmət Mərkəzinin məlumatına görə, 1 oktyabrda Bakı vaxtı ilə "
                                       "saat 14:51-də Zaqatalada 4,1 maqnitudalı zəlzələ qeydə alınıb. Zəlzələnin ocağı 6 km "
                                       "dərinlikdə olub.")
        fact, _ = ic._quakes(page, D(2026, 10, 18), D(2026, 10, 24))
        self.assertTrue(fact["body"].endswith("Ən güclüsü Xəzər dənizində qeydə alınan 3,5 maqnitudalı zəlzələ olub."))
        self.assertEqual((fact["frag"], fact["prio"]), ("3,0 və daha güclü 2 zəlzələ", 6))
        self.assertEqual(ic._quakes(page, D(2026, 11, 1), D(2026, 11, 7)),
                         (None, "bu həftə 3,0 və daha güclü zəlzələ qeydə alınmayıb"))
        tie = "".join(seys_row(900 + i, "3.4", area, datetime.datetime(2026, 11, 2 + i, 8, 0, tzinfo=UTC))
                      for i, area in enumerate(("Şamaxı", "Quba")))
        fact, _ = ic._quakes(f"<table>{tie}</table>", D(2026, 11, 1), D(2026, 11, 7))
        self.assertNotIn("Ən güclüsü", fact["body"], "bərabər güclü təkanlardan biri «ən güclü» adlanmır")

    def test_full_first_page_is_not_counted(self):
        rows = "".join(seys_row(800 + i, "3.1", "Xəzər dənizi", datetime.datetime(2026, 11, 2, 0, 30 + i, tzinfo=UTC))
                       for i in range(20))
        self.assertEqual(ic._quakes(f"<table>{rows}</table>", D(2026, 11, 1), D(2026, 11, 7)),
                         (None, "seismology.az siyahısının birinci səhifəsi bütünlüklə bu həftədəndir: say tam olmaya bilər"))
        self.assertEqual(ic._quakes("<html>boş</html>", D(2026, 11, 1), D(2026, 11, 7)), (None, "seismology.az siyahısı oxunmadı"))

    def test_week_with_quakes_and_a_big_euro_move(self):
        start = D(2026, 10, 18)
        days = [(3, lo, lo + 10, 10, 5.0) for lo in (10, 11, 12, 13, 15, 14, 11, 9)]
        n = Net({ox.AMB_URL.format(D(2026, 10, 25)): amb_xml(D(2026, 10, 23), 1.7, 1.98),
                 ox.AMB_URL.format(D(2026, 10, 16)): amb_xml(D(2026, 10, 16), 1.7, 1.96),
                 ox.SEYS_LIST: net("seys.html"), ic.om_url(D(2026, 10, 25), 7): json.dumps(om_doc(start, days)).encode("utf-8")})
        item, why = ic.reqemler_item(FIX, D(2026, 10, 25), ic._Get(n))
        self.assertTrue(item["worth"], why)
        self.assertEqual(item["title"], "Həftənin rəqəmləri, 18–24 oktyabr: avro 1,02% bahalaşıb, Bakıda ən yüksək temperatur 25 dərəcə")
        self.assertEqual(item["body"][0], "AMB-nin rəsmi məzənnəsinə görə, 1 avro 16 oktyabrda 1,9600, 23 oktyabrda 1,9800 manat "
                                          "olub: avro bir həftədə 0,0200 manat (1,02%) bahalaşıb. Dolların rəsmi məzənnəsi "
                                          "dəyişməyib: 1,7000 manat.")
        self.assertEqual(item["body"][2], "Open-Meteo-nun model məlumatına görə, Bakıda son 7 günün ən yüksək temperaturu 25 "
                                          "dərəcə (22 oktyabr), ən aşağı temperaturu 10 dərəcə (18 oktyabr) olub.")
        self.assertIn("19 oktyabrda saat 11:27-də Xəzər dənizində (3,5); 19 oktyabrda saat 11:35-də İsmayıllıda (3,0)",
                      item["body"][1])
        self.assertEqual(item["missing"], {"futbol": "Premyer Liqada bu həftə oyun olmayıb"})

    def test_premyer_liqa_round_wording(self):
        teams = {t: {"name": t.title()} for t in ("a", "b", "c", "d", "e", "f")}

        def week(games):
            with tempfile.TemporaryDirectory() as tmp:
                write(tmp, "premyer-liqa", {"source": "pfl.az", "teams": teams, "games": games})
                return ic._pl_week(tmp, D(2026, 11, 15), D(2026, 11, 21))

        g = lambda h, a, hs, as_, day=16, played=True, rnd="12": dict(
            home=h, away=a, hs=hs, date=f"2026-11-{day}T18:00+04:00", played=played, stadium="S", round=rnd, **{"as": as_})
        fact, _ = week([g("a", "b", 4, 0), g("c", "d", 1, 1), g("e", "f", 2, 1, day=17)])
        self.assertEqual(fact["body"], "Premyer Liqanın 12-ci turu başa çatıb: 3 oyunda 9 qol vurulub. Ən böyük hesab: «A» – «B» 4:0.")
        fact, _ = week([g("a", "b", 3, 3), g("c", "d", 1, 1), g("e", "f", 0, 0, played=False)])
        self.assertEqual(fact["body"], "Premyer Liqanın 12-ci turunun 2 oyununda 8 qol vurulub. Ən çox qol «A» – «B» oyununda "
                                       "vurulub: 3:3.", "təxirə salınan oyun sayılmır və tur «başa çatıb» yazılmır")
        fact, _ = week([g("a", "b", 3, 0), g("c", "d", 0, 3), g("e", "f", 0, 0, day=30)])
        self.assertEqual(fact["body"], "Premyer Liqanın 12-ci turunun 2 oyununda 6 qol vurulub.",
                         "bərabər ən böyük hesab adlanmır; 30 noyabrın oyunu bu həftəyə düşmür")
        fact, _ = week([g("a", "b", 0, 0), g("c", "d", 0, 0, rnd="13")])
        self.assertEqual(fact["body"], "Premyer Liqada 2 oyunda qol vurulmayıb (12-ci və 13-cü turlar).")
        self.assertEqual((fact["frag"], fact["prio"]), ("", 9))
        self.assertEqual(week([g("a", "b", 1, 0, day=10)]), (None, "Premyer Liqada bu həftə oyun olmayıb"))

    def test_unchanged_rates_and_too_few_parts(self):
        self.assertIsNone(ic._manat(D(2026, 10, 30), {"USD": 1.7, "EUR": 1.9}, D(2026, 11, 6), {"USD": 1.7, "EUR": 1.9}))
        item, why = ic.reqemler_item(FIX, D(2026, 11, 8), ic._Get(None))
        self.assertFalse(item["worth"])
        self.assertEqual(why, "həftənin rəqəmlərindən yalnız 1 hissə alındı (ən azı 2 lazımdır)")
        self.assertEqual(item["body"], [R8[2]])
        self.assertEqual(ic.reqemler_item(FIX, D(2026, 11, 10), ic._Get(None)), (None, "bazar günü deyil"))
        n = Net({ox.AMB_URL.format(D(2026, 11, 8)): amb_xml(D(2026, 10, 30), 1.7, 1.9)})
        item, _ = ic.reqemler_item(FIX, D(2026, 11, 8), ic._Get(n))
        self.assertIn("bu həftə bülleten olmayıb", item["missing"]["manat"])


class ItemsAndSinaqTest(unittest.TestCase):
    def test_items_contract_and_requests(self):
        required = {"kind", "key", "title", "lead", "body", "credit", "link", "topic", "slot", "worth"}
        for now, keys, calls in ((at(2026, 11, 10), ["beledci-2026-11-10"], 2),
                                 (at(2026, 11, 8), ["beledci-2026-11-08", "reqemler-2026-11-08"], 4)):
            n = real_net()
            rows = ic.items(FIX, now, fetch=n)
            self.assertEqual([i["key"] for i in rows], keys)
            self.assertEqual(len(n.calls), calls)
            self.assertEqual(rows, ic.items(FIX, now, fetch=real_net()), "eyni məlumat və vaxt: eyni nəticə")
            for item in rows:
                self.assertTrue(required <= set(item), item.keys())
                self.assertRegex(item["slot"], r"^\d\d:\d\d$")
                self.assertIn(item["topic"], ("idman", "iqtisadiyyat", "təqvim", "kosmos", "icmal"))
        n = real_net()
        self.assertEqual(ic.items(FIX, at(2026, 11, 8), fetch=n, done={"beledci-2026-11-08", "reqemler-2026-11-08"}), [])
        self.assertEqual(n.calls, [], "qurulmuş açar üçün sorğu getmir")
        self.assertEqual([i["key"] for i in ic.items(FIX, datetime.datetime(2026, 11, 9, 21, 0, tzinfo=UTC))],
                         ["beledci-2026-11-10"], "21:00 UTC Bakıda artıq 10 noyabrdır")
        week = FlexNet()
        day = D(2026, 11, 9)
        while day <= D(2026, 11, 22):
            before = len(week.calls)
            ic.items(FIX, at(day.year, day.month, day.day), fetch=week)
            self.assertLessEqual(len(week.calls) - before, 4, day)
            day += ic.DAY

    def test_leadership_is_never_published(self):
        with patch.object(ox, "needs_owner", return_value=True):
            rows = ic.items(FIX, at(2026, 11, 8), fetch=real_net())
        self.assertTrue(rows and all(not i["worth"] and "rəhbərliyin" in i["why"] for i in rows))

    def test_sinaq_and_cli(self):
        now = at(2026, 11, 10, 9, 0)
        md = "\n".join(ic.sinaq(FIX, now, fetch=real_net()))
        for text in ("# İcmal xəbərləri (oz_icmal.py): sınaq", "## 1. «Günün bələdçisi» (hər gün 08:00)",
                     "**10 noyabr 2026, çərşənbə axşamı (bu gün), saat 08:00:**",
                     "### Günün bələdçisi, 10 noyabr: Bakıda buludlu hava, 6–9,8 dərəcə; II Liqada 3 oyun",
                     "- Naxçıvan: əsasən açıq hava, temperatur -1,2 ilə 8,3 dərəcə",
                     "### Növbəti 7 günün oyun hissəsi", "**13 noyabr 2026, cümə:**",
                     "- Millətlər Liqası D, 2-ci qrup: Lixtenşteyn – Azərbaycan (23:45)",
                     "## 2. «Həftənin rəqəmləri» (bazar 12:00)", "**8 noyabr 2026, bazar — ən son real hal, saat 12:00:**",
                     "### Həftənin rəqəmləri, 1–7 noyabr: Premyer Liqada 17 qol",
                     "> Yazılmayan hissələr: zəlzələ — bu həftə 3,0 və daha güclü zəlzələ qeydə alınmayıb",
                     "✅ Dərc olunardı", "Bu sınaqda 6 sorğu göndərilib."):
            self.assertIn(text, md)
        self.assertNotIn("⏭", md)
        import updater
        fake = SimpleNamespace(fetch=real_net(), president_score=updater.president_score, norm_az=updater.norm_az)
        out = io.StringIO()
        with patch.object(ox, "_u", return_value=fake), contextlib.redirect_stdout(out):
            self.assertEqual(ic.main(["--sinaq", "--root", str(FIX), "--now", "2026-11-10T09:00+04:00"]), 0)
        self.assertEqual(out.getvalue().strip(), md.strip())
        self.assertFalse(re.search(r"https?://(?!open-meteo\.com|www\.cbar\.az|pfl\.az|seismology\.az|www\.thesportsdb\.com|"
                                   r"www\.openligadb\.de|en\.wikipedia\.org)", md), "yalnız mənbə keçidləri")


class NotOnTheSiteTest(unittest.TestCase):
    def test_site_pipeline_does_not_use_it(self):
        self.assertNotIn("oz_icmal", (ROOT / "updater.py").read_text(encoding="utf-8"))
        self.assertNotIn("oz_icmal", (ROOT / ".github" / "scripts" / "pipeline.sh").read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
