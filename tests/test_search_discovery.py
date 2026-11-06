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


class StoryPagesTest(unittest.TestCase):
    """Sahib, 2026-11-06: Google bizi yalnız «8 ulduz» sorğusu ilə tapırdı (28 gündə 33 göstəriş); /x/ səhifələri noindex idi."""

    def story(self, sid, alts=3, hours=2, **kw):
        import datetime
        at = (datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(hours=hours)).isoformat()
        names = [('Report', 'report.az'), ('Trend', 'trend.az'), ('Axar.az', 'axar.az')]
        alt = [{'source': names[i][0], 'sourceUrl': f'https://{names[i][1]}/x/{sid}-{i}', 'title': f'Başlıq {i}', 'lang': 'az'} for i in range(alts)]
        return {'id': sid, 'title': 'Zəfər Günü ilə bağlı hərbi yürüşlər olacaq', 'summary': 'Bakının müxtəlif yerlərində hərbi orkestrlər çıxış edəcək.',
                'category': 'bolgeler', 'source': 'APA', 'sourceUrl': f'https://apa.az/news/{sid}', 'publishedAt': at, 'lang': 'az', 'alts': alt, **kw}

    def test_only_main_azerbaijani_stories_get_a_search_page(self):
        self.assertTrue(updater.story_worthy(self.story('a' * 16)))
        self.assertFalse(updater.story_worthy(self.story('b' * 16, alts=2)), '3 mənbə: yox')
        self.assertTrue(updater.story_worthy(self.story('c' * 16, alts=0, category='prezident')), 'Zuğulba həmişə')
        self.assertFalse(updater.story_worthy(self.story('d' * 16, lang='ru')))
        self.assertFalse(updater.story_worthy(self.story('not-an-id')))

    def test_story_page_is_indexable_lists_every_source_and_opens_the_app(self):
        with tempfile.TemporaryDirectory() as tmp:
            with patch.object(updater, 'STORY_DIR', pathlib.Path(tmp) / 'xeber'):
                stories = updater.write_story_pages([self.story('1' * 16), self.story('2' * 16, alts=1), self.story('3' * 16, hours=31 * 24)])
                self.assertEqual(sorted(stories), ['1' * 16], '3 mənbəli və 30 gündən köhnə xəbərin səhifəsi yoxdur')
                page = (pathlib.Path(tmp) / 'xeber' / ('1' * 16) / 'index.html').read_text(encoding='utf-8')
                self.assertNotIn('noindex', page)
                self.assertIn(f'<link rel="canonical" href="{updater.SITE}xeber/{"1" * 16}/" />', page)
                self.assertIn('<h1>Zəfər Günü ilə bağlı hərbi yürüşlər olacaq</h1>', page)
                self.assertIn('4 mənbə', page)
                for i, host in enumerate(('report.az', 'trend.az', 'axar.az')):
                    self.assertIn(f'href="https://{host}/x/{"1" * 16}-{i}"', page)
                self.assertIn(f'#/xeber/{"1" * 16}?b=bolgeler', page)
                self.assertIn('href="../../bolme/bolgeler/">Bölgələr', page)
                self.assertIn('"@type": "BreadcrumbList"', page)
                self.assertNotIn('NewsArticle', page, 'aqreqator xəbərin müəllifi kimi görünmür')
                self.assertNotIn('<img', page, 'QIRMIZI XƏTT 3: tətbiq yüklənənə qədər əlavə şəkil sorğusu yoxdur')
                self.assertLess(len(page.encode('utf-8')), 9000)
                stamp = (pathlib.Path(tmp) / 'xeber' / ('1' * 16) / 'index.html').stat().st_mtime_ns
                again = updater.write_story_pages([self.story('1' * 16)])
                self.assertEqual(stamp, (pathlib.Path(tmp) / 'xeber' / ('1' * 16) / 'index.html').stat().st_mtime_ns, 'dəyişməyən səhifə təzədən yazılmır')
                self.assertEqual(sorted(again), ['1' * 16], 'lentdən çıxan xəbərin səhifəsi 30 gün qalır')
                updater.write_story_pages([], now=updater.time.time() + 31 * 86400)
                self.assertFalse((pathlib.Path(tmp) / 'xeber' / ('1' * 16)).exists(), '30 gündən sonra silinir')

    def test_story_pages_are_in_the_sitemap_and_linked_from_their_section(self):
        sid = '4' * 16
        with tempfile.TemporaryDirectory() as tmp:
            target = pathlib.Path(tmp) / 'sitemap.xml'
            with patch.object(updater, 'SITEMAP_FILE', target):
                updater.write_sitemap({sid: [1793950000, 4, 'bolgeler']})
            locs = [e.text for e in ET.parse(target).getroot().iter('{http://www.sitemaps.org/schemas/sitemap/0.9}loc')]
            self.assertIn(f'{updater.SITE}xeber/{sid}/', locs)
        page = updater.section_page('bolgeler', 'Bölgələr', 'x', [self.story(sid), self.story('5' * 16, alts=0)], stories={sid: [0, 4, 'bolgeler']})
        self.assertIn(f'href="../../xeber/{sid}/"', page)
        self.assertIn('href="https://apa.az/news/' + '5' * 16 + '"', page, 'səhifəsi olmayan xəbər mənbəyə aparır')

    def test_pipeline_publishes_and_keeps_story_pages(self):
        sh = (ROOT / '.github/scripts/pipeline.sh').read_text(encoding='utf-8')
        self.assertIn('cp -a "$WORK/xeber" "$REPO_DIR/xeber"', sh)
        self.assertIn('git -C "$REPO_DIR" add xeber', sh)
        self.assertIn('cp -a "$REPO_DIR/xeber" "$WORK/xeber"', sh)
