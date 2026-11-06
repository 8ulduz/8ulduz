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


class DigestTest(unittest.TestCase):
    """Sahib, 2026-11-06: daimi oxucu üçün 1-ci addım — gündə iki dəfə «günün 10 əsas xəbəri»."""

    def art(self, sid, n, hours, title=None, **kw):
        import datetime
        at = (datetime.datetime(2026, 11, 6, 9, tzinfo=updater.BAKU) - datetime.timedelta(hours=hours)).isoformat()
        names = [('Report', 'report.az'), ('Trend', 'trend.az'), ('Axar.az', 'axar.az'), ('Oxu.az', 'oxu.az'), ('Olke.az', 'olke.az')]
        alts = [{'source': names[i][0], 'sourceUrl': f'https://{names[i][1]}/{sid}', 'title': 't', 'lang': 'az'} for i in range(n - 1)]
        return {'id': sid, 'title': title or f'Xəbər {sid}', 'summary': 'Qısa xülasə.', 'category': 'gundem', 'source': 'APA',
                'sourceUrl': f'https://apa.az/news/{sid}', 'publishedAt': at, 'lang': 'az', 'alts': alts, **kw}

    def test_morning_edition_lists_the_ten_most_covered_stories_once(self):
        import datetime
        nine = datetime.datetime(2026, 11, 6, 9, 5, tzinfo=updater.BAKU).timestamp()
        arts = [self.art(f'{i:016x}', 1 + i % 5, 1 + i) for i in range(14)]
        arts.append(self.art('f' * 16, 5, 30))                                   # 24 saatdan köhnə: yox
        arts.append(self.art('e' * 16, 5, 2, lang='ru'))                          # rus dilində: yox
        arts.append(self.art('d' * 16, 5, 20, title='Xəbər 0000000000000004'))     # eyni başlıq, köhnə nüsxə: bir dəfə
        with tempfile.TemporaryDirectory() as tmp:
            with patch.object(updater, 'DIGEST_DIR', pathlib.Path(tmp) / 'icmal'):
                self.assertEqual(updater.write_digest(arts, {}, now=nine - 600), [], '09:00-dan əvvəl buraxılış yoxdur')
                index = updater.write_digest(arts, {'0000000000000004': [0, 5, 'gundem']}, now=nine)
                self.assertEqual([e['slug'] for e in index], ['2026-11-06-seher'])
                ed = index[0]
                self.assertEqual(len(ed['items']), 10)
                self.assertEqual(ed['items'][0]['n'], 5)
                self.assertNotIn('f' * 16, ed['ids'])
                self.assertNotIn('e' * 16, ed['ids'])
                self.assertEqual(sum(1 for t in ed['items'] if t['t'] == 'Xəbər 0000000000000004'), 1)
                self.assertEqual(ed['title'], 'Səhər icmalı · 6 noyabr 2026')
                page = (pathlib.Path(tmp) / 'icmal' / '2026-11-06-seher' / 'index.html').read_text(encoding='utf-8')
                self.assertIn(f'<link rel="canonical" href="{updater.SITE}icmal/2026-11-06-seher/" />', page)
                self.assertIn(f'href="{updater.SITE}xeber/0000000000000004/"', page, 'öz səhifəsi olan xəbər ora aparır')
                self.assertIn('t.me/sekkizulduz_az', page)
                self.assertNotIn('<script>', page, 'icmal səhifəsi skriptsizdir')
                self.assertNotIn('<img', page)
                self.assertLess(len(page.encode('utf-8')), 12000)
                again = updater.write_digest(arts, {}, now=nine + 600)
                self.assertEqual(len(again), 1, 'buraxılış bir dəfə yazılır')
                archive = (pathlib.Path(tmp) / 'icmal' / 'index.html').read_text(encoding='utf-8')
                self.assertIn(f'<link rel="canonical" href="{updater.SITE}icmal/" />', archive)
                self.assertIn('icmal/2026-11-06-seher/', archive)

    def test_evening_edition_does_not_repeat_the_morning(self):
        import datetime
        nine = datetime.datetime(2026, 11, 6, 9, 5, tzinfo=updater.BAKU).timestamp()
        seven = datetime.datetime(2026, 11, 6, 19, 5, tzinfo=updater.BAKU).timestamp()
        arts = [self.art(f'{i:016x}', 5, -1 - i * 0.5) for i in range(12)] + [self.art(f'{i:016x}', 5, 1 + i) for i in range(100, 112)]
        with tempfile.TemporaryDirectory() as tmp:
            with patch.object(updater, 'DIGEST_DIR', pathlib.Path(tmp) / 'icmal'):
                morning = updater.write_digest(arts, {}, now=nine)[0]
                index = updater.write_digest(arts, {}, now=seven)
                self.assertEqual([e['slug'] for e in index], ['2026-11-06-axsam', '2026-11-06-seher'])
                self.assertFalse(set(index[0]['ids']) & set(morning['ids']))
                self.assertIn('Axşam icmalı', index[0]['title'])

    def test_digest_pages_are_published_and_in_the_sitemap(self):
        with tempfile.TemporaryDirectory() as tmp:
            target = pathlib.Path(tmp) / 'sitemap.xml'
            with patch.object(updater, 'SITEMAP_FILE', target):
                updater.write_sitemap({}, [{'slug': '2026-11-06-seher', 'date': '2026-11-06', 'at': 1793941200}])
            locs = [e.text for e in ET.parse(target).getroot().iter('{http://www.sitemaps.org/schemas/sitemap/0.9}loc')]
            self.assertIn(f'{updater.SITE}icmal/', locs)
            self.assertIn(f'{updater.SITE}icmal/2026-11-06-seher/', locs)
        sh = (ROOT / '.github/scripts/pipeline.sh').read_text(encoding='utf-8')
        for line in ('cp -a "$WORK/icmal" "$REPO_DIR/icmal"', 'git -C "$REPO_DIR" add icmal', 'cp -a "$REPO_DIR/icmal" "$WORK/icmal"'):
            self.assertIn(line, sh)
