"""Namaz, hava və məzənnə səhifələri (updater.write_subpages; sahib 2026-11-13: Google-da gündəlik axtarılan sorğuların öz ünvanı olsun)."""
import datetime
import hashlib
import base64
import json
import pathlib
import re
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
import updater  # noqa: E402

NOW = datetime.datetime(2026, 11, 13, 15, 0, tzinfo=updater.BAKU)


def aladhan_month(year, month, days=None):
    days = days or updater._month_days(year, month)
    return {"data": [{"timings": {"Fajr": f"05:{d:02d} (+04)", "Sunrise": "07:03 (+04)", "Dhuhr": "12:29 (+04)", "Asr": "15:19 (+04)",
                                  "Sunset": "17:45 (+04)", "Maghrib": "17:45 (+04)", "Isha": "19:05 (+04)"},
                      "date": {"gregorian": {"day": f"{d:02d}"}}} for d in range(1, days + 1)]}


def meteo(first_day="2026-11-13"):
    start = datetime.date.fromisoformat(first_day)
    days = [(start + datetime.timedelta(days=i)).isoformat() for i in range(7)]
    one = {"current": {"time": first_day + "T14:30", "temperature_2m": 15.4, "apparent_temperature": -0.4, "relative_humidity_2m": 57, "weathercode": 1, "wind_speed_10m": 7.9},
           "daily": {"time": days, "weather_code": [2, 3, 3, 61, 61, 80, 3], "temperature_2m_max": [16.5] * 7, "temperature_2m_min": [-2.6] * 7,
                     "precipitation_sum": [0, 0, 0, 3.5, 0.6, None, 0.3], "wind_speed_10m_max": [9.6] * 7}}
    return [one for _ in updater.CITIES]


class Sandbox(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = pathlib.Path(self.tmp.name)
        (self.root / "data").mkdir()
        self.patches = [patch.object(updater, "SECTIONS_DIR", self.root / "bolme"), patch.object(updater, "NAMAZ_FILE", self.root / "data" / "namaz.json"),
                        patch.object(updater, "HAVA_CACHE", self.root / ".cache" / "hava.json"), patch.object(updater, "CACHE_DIR", self.root / ".cache"),
                        patch.object(updater, "MARKETS_FILE", self.root / "data" / "markets.json"), patch.object(updater, "SITEMAP_FILE", self.root / "sitemap.xml")]
        for p in self.patches:
            p.start()

    def tearDown(self):
        for p in self.patches:
            p.stop()
        self.tmp.cleanup()

    def page(self, path):
        return (self.root / "bolme" / path / "index.html").read_text(encoding="utf-8")


class NamazTest(Sandbox):
    def test_one_cycle_fetches_a_few_cities_and_never_refetches_saved_ones(self):
        calls = []
        fetcher = lambda url, timeout=0: calls.append(url) or aladhan_month(2026, 11)
        updater.update_namaz(NOW, fetcher)
        self.assertEqual(len(calls), updater.NAMAZ_FETCH_MAX, "yavaş dövrə bir dəfəyə 46 sorğu göndərmir")
        self.assertIn("method=13", calls[0], "saytdakı namaz göstəricisi ilə eyni üsul")
        self.assertIn("/calendar/2026/11?", calls[0])
        for _ in range(10):
            updater.update_namaz(NOW, fetcher)
        self.assertEqual(len(calls), len(updater.CITIES), "hər şəhər ayda bir dəfə soruşulur")
        saved = json.loads(updater.NAMAZ_FILE.read_text(encoding="utf-8"))["months"]["2026-11"]
        self.assertEqual(saved["baki"][12][0], "05:13")
        self.assertEqual(len(saved["baki"]), 30)

    def test_failed_or_partial_answer_is_not_saved_and_stops_the_cycle(self):
        calls = []

        def broken(url, timeout=0):
            calls.append(url)
            raise OSError("şəbəkə yoxdur")
        updater.update_namaz(NOW, broken)
        self.assertEqual(len(calls), 1, "API cavab vermirsə dövrə qalan şəhərləri gözləmir")
        updater.update_namaz(NOW, lambda url, timeout=0: aladhan_month(2026, 11, days=12))
        self.assertFalse(updater.NAMAZ_FILE.exists() and json.loads(updater.NAMAZ_FILE.read_text(encoding="utf-8"))["months"]["2026-11"])

    def test_next_month_is_fetched_from_the_25th_and_old_month_is_dropped(self):
        late = datetime.datetime(2026, 12, 26, 9, 0, tzinfo=updater.BAKU)
        with patch.object(updater, "NAMAZ_FETCH_MAX", 200):
            updater.update_namaz(NOW, lambda url, timeout=0: aladhan_month(2026, 11))
            seen = []
            updater.update_namaz(late, lambda url, timeout=0: seen.append(url) or aladhan_month(*map(int, re.search(r"/calendar/(\d+)/(\d+)", url).groups())))
        months = json.loads(updater.NAMAZ_FILE.read_text(encoding="utf-8"))["months"]
        self.assertEqual(sorted(months), ["2026-12", "2027-01"])
        self.assertEqual(len(months["2027-01"]["baki"]), 31)

    def test_pages_show_today_month_table_and_fix_stale_copy_without_network(self):
        with patch.object(updater, "NAMAZ_FETCH_MAX", 200):
            updater.update_namaz(NOW, lambda url, timeout=0: aladhan_month(2026, 11))
        self.assertEqual(updater.write_namaz_pages(NOW), len(updater.CITIES))
        page = self.page("namaz/baki")
        self.assertIn("<title>Bakı namaz vaxtları bu gün — 13 noyabr 2026 — 8ulduz</title>", page)
        self.assertIn(f'<link rel="canonical" href="{updater.SITE}bolme/namaz/baki/">', page)
        self.assertIn('<tr data-d="2026-11-13" data-t="13 noyabr 2026, cümə" class="bu"><td>13 noyabr</td><td>05:13</td>', page)
        self.assertEqual(page.count("<tr data-d="), 30)
        self.assertIn("<div>Sübh<b>05:13</b></div>", page)
        self.assertIn('href="../../hava/baki/"', page)
        self.assertIn('href="../gence/"', page)
        # Yeganə skript CSP-də öz hash-i ilə icazəlidir və şəbəkəyə getmir.
        scripts = re.findall(r"<script>(.*?)</script>", page, re.S)
        self.assertEqual(scripts, [updater._NAMAZ_JS])
        self.assertIn("'sha256-" + base64.b64encode(hashlib.sha256(scripts[0].encode()).digest()).decode() + "'", page)
        self.assertNotRegex(scripts[0], r"fetch|XMLHttp|import|src=")
        self.assertNotIn("app.min.js", page, "tətbiq yüklənmir: bir HTML, daxili CSS")
        self.assertNotIn("<link rel=\"stylesheet\"", page)
        index = self.page("namaz")
        self.assertIn('<a href="baki/">Bakı</a></td><td>05:13</td>', index)
        self.assertEqual(index.count('<tr><td><a href="'), len(updater.CITIES))

    def test_city_without_a_full_month_gets_no_page(self):
        updater.NAMAZ_FILE.write_text(json.dumps({"months": {"2026-11": {"baki": [["05:00"] * 6] * 30, "gence": [["05:00"] * 6] * 29, "seki": [["5"] * 6] * 30}}}), encoding="utf-8")
        self.assertEqual(updater.write_namaz_pages(NOW), 1)
        self.assertFalse((self.root / "bolme" / "namaz" / "gence").exists())
        self.assertFalse((self.root / "bolme" / "namaz" / "seki").exists())


class HavaTest(Sandbox):
    def test_one_request_for_all_cities_and_at_most_hourly(self):
        calls = []
        fetcher = lambda url, timeout=0: calls.append(url) or meteo()
        updater.update_hava(1000.0, fetcher)
        updater.update_hava(1000.0 + 600, fetcher)
        self.assertEqual(len(calls), 1, "saatda bir sorğu")
        self.assertEqual(calls[0].split("latitude=")[1].split("&")[0].count(","), len(updater.CITIES) - 1)
        updater.update_hava(1000.0 + 3600, fetcher)
        self.assertEqual(len(calls), 2)

    def test_too_few_cities_keeps_previous_data(self):
        updater.update_hava(1000.0, lambda url, timeout=0: meteo())
        with self.assertRaises(ValueError):
            updater.update_hava(9000.0, lambda url, timeout=0: meteo()[:3])
        self.assertEqual(len(json.loads(updater.HAVA_CACHE.read_text(encoding="utf-8"))["cities"]), len(updater.CITIES))

    def test_pages(self):
        updater.update_hava(1000.0, lambda url, timeout=0: meteo())
        self.assertEqual(updater.write_hava_pages(NOW), len(updater.CITIES))
        page = self.page("hava/gence")
        self.assertIn("<title>Gəncədə hava — bu gün və 7 günlük proqnoz — 8ulduz</title>", page)
        self.assertIn('<p class="iri">+15° <span class="qeyd">Əsasən açıq</span></p>', page)
        self.assertIn("Hiss olunan<b>0°</b>", page, "−0,4 «-0°» yazılmır")
        self.assertIn("<tr><td>Bu gün, 13 noyabr</td><td>Qismən buludlu</td><td>+16°</td><td>-3°</td><td>0 mm</td><td>10 m/san</td></tr>", page)
        self.assertIn("<td>Sabah, 14 noyabr</td>", page)
        self.assertIn("<td>Bazar ertəsi, 16 noyabr</td><td>Yağışlı</td>", page)
        self.assertIn("Ölçü vaxtı: 13 noyabr 2026, 14:30", page)
        self.assertNotIn("<script>", page)
        self.assertIn('<a href="gence/">Gəncə</a>', self.page("hava"))

    def test_stale_forecast_drops_past_days_and_fully_stale_writes_nothing(self):
        updater.update_hava(1000.0, lambda url, timeout=0: meteo("2026-11-11"))
        updater.write_hava_pages(NOW)
        page = self.page("hava/baki")
        self.assertNotIn("11 noyabr</td>", page)
        self.assertIn("Bakıda 5 günlük hava proqnozu", page)
        self.assertIn("Ölçü vaxtı: 11 noyabr 2026", page, "köhnə ölçü öz tarixi ilə göstərilir")
        self.assertEqual(updater.write_hava_pages(NOW + datetime.timedelta(days=30)), 0)


class CurrencyTest(Sandbox):
    def markets(self, **over):
        items = [{"id": "USD", "label": "Dollar", "unit": "AZN", "dec": 4, "value": 1.7, "change": 0, "src": "AMB", "asOf": "2026-11-13"},
                 {"id": "RUB100", "label": "100 Rubl", "unit": "AZN", "dec": 4, "value": 2.0511, "change": -0.0038, "src": "AMB", "asOf": "2026-11-13"},
                 {"id": "EUR", "label": "Avro", "unit": "AZN", "dec": 4, "value": None}]
        updater.MARKETS_FILE.write_text(json.dumps({"items": items}), encoding="utf-8")

    def test_pages_use_official_rate_and_nominal(self):
        self.markets()
        self.assertEqual(updater.write_currency_pages(), 2)
        usd = self.page("mezenne/dollar")
        self.assertIn("<title>Dollar məzənnəsi bu gün — 1 USD = 1.7000 AZN — 8ulduz</title>", usd)
        self.assertIn("<b>13 noyabr 2026</b>", usd)
        self.assertIn("1 ABŞ dolları dəyişməyib", usd)
        self.assertIn("<tr><td>1 000 USD</td><td>1 700.00 AZN</td></tr>", usd)
        self.assertIn("<tr><td>100 AZN</td><td>58.82 USD</td></tr>", usd)
        rub = self.page("mezenne/rubl")
        self.assertIn("100 RUB = 2.0511 AZN", rub)
        self.assertIn("100 Rusiya rublu 0.0038 AZN ucuzlaşıb", rub)
        self.assertIn("<tr><td>1 000 RUB</td><td>20.51 AZN</td></tr>", rub)
        self.assertIn("<tr><td>100 AZN</td><td>4 875.43 RUB</td></tr>", rub)
        self.assertIn('<a href="../dollar/">Dollar məzənnəsi</a>', rub)
        self.assertNotIn("avro", rub, "qiyməti olmayan valyutaya keçid verilmir")
        self.assertFalse((self.root / "bolme" / "mezenne" / "avro").exists())

    def test_rates_page_links_to_currency_pages(self):
        self.markets()
        body = updater.service_body("valyuta", [])
        self.assertIn('<a href="../mezenne/dollar/">Dollar məzənnəsi</a>', body)
        self.assertNotIn("mezenne/avro", body)


class WiringTest(Sandbox):
    def test_sitemap_lists_written_subpages_only(self):
        CurrencyTest.markets(self)
        updater.write_subpages(NOW)
        updater.write_sitemap()
        sitemap = (self.root / "sitemap.xml").read_text(encoding="utf-8")
        self.assertIn(f"<loc>{updater.SITE}bolme/mezenne/dollar/</loc><lastmod>", sitemap)
        self.assertNotIn("bolme/namaz/", sitemap, "məlumatı olmayan səhifə sitemap-ə düşmür")
        self.assertNotIn("bolme/hava/", sitemap)

    def test_unchanged_page_is_not_rewritten(self):
        CurrencyTest.markets(self)
        updater.write_currency_pages()
        target = self.root / "bolme" / "mezenne" / "dollar" / "index.html"
        with patch.object(updater, "_write_atomic", side_effect=AssertionError("yenidən yazıldı")):
            updater.write_currency_pages()
        self.assertTrue(target.exists())

    def test_network_stays_in_the_slow_cycle(self):
        src = pathlib.Path(updater.__file__).read_text(encoding="utf-8")
        slow = src[src.index("def slow_cycle():"):src.index("# ---------------------------------------------------------------- bazarlar ---")]
        self.assertIn("update_city_data, write_public", slow)
        self.assertEqual(len(re.findall(r"^[^#\n]*\bupdate_city_data\b", src, re.M)), 2, "yalnız tərif və yavaş dövrə (qırmızı xətt 1)")
        public = src[src.index("def write_public():"):src.index("_OG_META = ")]
        self.assertIn("write_subpages()", public)
        with patch.object(updater, "fetch", side_effect=AssertionError("şəbəkə")), patch.object(updater, "fetch_json", side_effect=AssertionError("şəbəkə")):
            updater.write_subpages(NOW)

    def test_slugs_and_locative(self):
        slugs = [updater.city_slug(c[0]) for c in updater.CITIES]
        self.assertEqual(len(set(slugs)), len(slugs))
        self.assertTrue(all(re.fullmatch(r"[a-z]+", s) for s in slugs), slugs)
        self.assertEqual([updater.city_slug(n) for n in ("Bakı", "İsmayıllı", "Şəki", "Göyçay", "Ağdaş")], ["baki", "ismayilli", "seki", "goycay", "agdas"])
        self.assertEqual([updater._locative(n) for n in ("Bakı", "Gəncə", "Şəki", "Qax", "Göygöl", "İmişli")], ["Bakıda", "Gəncədə", "Şəkidə", "Qaxda", "Göygöldə", "İmişlidə"])


if __name__ == "__main__":
    unittest.main()
