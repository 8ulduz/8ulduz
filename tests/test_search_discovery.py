"""Search discovery must describe the aggregator honestly and stay lightweight."""
import pathlib
import tempfile
import unittest
import xml.etree.ElementTree as ET
from unittest.mock import patch
import updater

ROOT = pathlib.Path(__file__).resolve().parents[1]


class SearchDiscoveryTest(unittest.TestCase):
    def test_information_pages_are_in_the_generated_sitemap_without_fake_dates(self):
        with tempfile.TemporaryDirectory() as tmp:
            target = pathlib.Path(tmp) / 'sitemap.xml'
            with patch.object(updater, 'SITEMAP_FILE', target):
                updater.write_sitemap()
            ns = {'s': 'http://www.sitemaps.org/schemas/sitemap/0.9'}
            rows = ET.parse(target).getroot().findall('s:url', ns)
            for path in ('haqqinda/', 'mexfilik/'):
                row = next(r for r in rows if r.find('s:loc', ns).text == updater.SITE + path)
                self.assertIsNone(row.find('s:lastmod', ns))

    def test_about_is_crawlable_without_scripts_and_does_not_claim_original_reporting(self):
        page = (ROOT / 'haqqinda/index.html').read_text(encoding='utf-8')
        self.assertIn('href="https://8ulduz.az/haqqinda/"', page)
        for text in ('xəbər aqreqatorudur', 'orijinal xəbərlərin müəllifi deyil',
                     'Düzəliş və hüquq müraciətləri', 'Müxalifət mənbələri',
                     'mailto:8ulduz.az@gmail.com', '../feed.xml'):
            self.assertIn(text, page)
        for forbidden in ('<script', 'NewsArticle', 'noindex', 'vm6666', 'v.z.muradov'):
            self.assertNotIn(forbidden, page)
        self.assertLess(len(page.encode('utf-8')), 8500)
        self.assertIn('href="./haqqinda/">Haqqımızda', (ROOT / 'assets/app.js').read_text(encoding='utf-8'))
