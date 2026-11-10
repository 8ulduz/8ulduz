"""Search discovery must describe the aggregator honestly and stay lightweight."""
import pathlib
import re
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
        self.assertTrue(updater.story_worthy(self.story('b' * 16, alts=2)), 'sahib 2026-11-07: 3 mənbə artıq bəs edir')
        self.assertFalse(updater.story_worthy(self.story('e' * 16, alts=1)), '2 mənbə: yox')
        self.assertTrue(updater.story_worthy(self.story('c' * 16, alts=0, category='prezident')), 'Zuğulba həmişə')
        self.assertFalse(updater.story_worthy(self.story('d' * 16, lang='ru')))
        self.assertFalse(updater.story_worthy(self.story('not-an-id')))

    def test_story_page_is_indexable_lists_every_source_and_opens_the_app(self):
        with tempfile.TemporaryDirectory() as tmp:
            with patch.object(updater, 'STORY_DIR', pathlib.Path(tmp) / 'xeber'):
                stories = updater.write_story_pages([self.story('1' * 16), self.story('2' * 16, alts=1), self.story('3' * 16, hours=31 * 24)])
                self.assertEqual(sorted(stories), ['1' * 16], '2 mənbəli və 30 gündən köhnə xəbərin səhifəsi yoxdur')
                page = (pathlib.Path(tmp) / 'xeber' / ('1' * 16) / 'index.html').read_text(encoding='utf-8')
                self.assertNotIn('noindex', page)
                self.assertIn('<meta name="robots" content="max-image-preview:large" />', page, 'Google Discover: böyük şəkil')
                self.assertIn(f'<link rel="canonical" href="{updater.SITE}xeber/{"1" * 16}/" />', page)
                self.assertIn('<h1>Zəfər Günü ilə bağlı hərbi yürüşlər olacaq</h1>', page)
                self.assertIn('«Bakının müxtəlif yerlərində hərbi orkestrlər çıxış edəcək.» — APA', page, 'xülasə bir sitat sətridir')
                self.assertIn('Telegram-a qoşul', page)
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
                # köhnə şablonla yazılmış səhifə (index-də versiya yoxdur) yenidən yazılır, sonra versiya qeyd olunur
                idx = pathlib.Path(tmp) / 'xeber' / 'index.json'
                raw = updater.json.loads(idx.read_text(encoding='utf-8')); raw['1' * 16] = raw['1' * 16][:3]; idx.write_text(updater.json.dumps(raw), encoding='utf-8')
                self.assertEqual(updater.write_story_pages([self.story('1' * 16)])['1' * 16][3], updater.STORY_VER)
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
        extra = 'ab' * 8
        linked = updater.section_page('bolgeler', 'Bölgələr', 'x', [self.story(sid)], stories={sid: [1, 4, 'bolgeler'], extra: [2, 4, 'bolgeler']}, titles={extra: ('Köhnə bölgə xəbəri', 'APA')})
        self.assertIn(f'href="../../xeber/{extra}/"', linked, 'ilk 30-da olmayan xəbər səhifəsi də keçid alır')
        self.assertIn('Köhnə bölgə xəbəri', linked)
        self.assertIn('Telegram-a qoşul', linked)
        self.assertIn('https://t.me/sekkizulduz_az', linked)

    def test_related_stories_are_same_category_story_links(self):
        a, b, other = self.story('1' * 16), self.story('2' * 16), self.story('3' * 16, category='idman')
        page = updater.story_page(a, None, [a, b, other])
        self.assertIn(f'href="../../xeber/{"2" * 16}/"', page)
        self.assertNotIn(f'href="../../xeber/{"3" * 16}/"', page, 'başqa bölmə düşmür')
        self.assertIn('Əlaqəli xəbərlər', page)

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

    def test_one_event_gives_one_story(self):
        # Sahib (2026-11-06): «1 hadisədən yalnız 1 xəbər» — ilk axşam icmalında 10 xəbərdən 7-si bir səfər idi
        start = updater.datetime.datetime(2026, 11, 5, 21, tzinfo=updater.BAKU).timestamp()
        trip = 'Prezident və birinci xanım Zəngilan Şəhər Təhsil Kompleksinin açılışında iştirak ediblər'
        arts = [self.art('a' * 16, 5, 1, title=trip, summary='İlham Əliyev noyabrın 6-da Zəngilan rayonuna səfər edib, təhsil kompleksi açılıb.'),
                self.art('b' * 16, 5, 2, title='Zəngilan Şəhər Təhsil Kompleksi istifadəyə verildi', summary='Zəngilan rayonunda təhsil kompleksi açılıb.'),
                self.art('c' * 16, 4, 3, title='Prezident: "Köçkünlərin doğma torpaqlara qayıtması böyük arzu idi"', summary='Bu barədə dövlət başçısı deyib.'),
                self.art('d' * 16, 3, 4, title='Güclü külək əsəcək - XƏBƏRDARLIQ', summary='Milli Hidrometeorologiya xidməti küləklə bağlı xəbərdarlıq edib.'),
                self.art('e' * 16, 2, 5, title='Naxçıvanın Bakıdakı nümayəndəliyi ləğv olundu', summary='Müvafiq fərman imzalanıb, nümayəndəlik bağlanır.'),
                self.art('f' * 16, 2, 6, title='Bakıda yeni metro stansiyası açıldı', summary='Stansiya sərnişinlərin istifadəsinə verilib.')]
        picked = updater.digest_pick(arts, start, start + 86400)
        self.assertEqual([a['id'] for a in picked], ['a' * 16, 'd' * 16, 'e' * 16, 'f' * 16],
                         'səfərin ikinci xəbəri və Prezidentin sitatı düşür, ayrı hadisələr qalır')

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
        arts = [self.art(f'{i:016x}', 5, -1 - i * 0.5) for i in range(12)] + [self.art(f'{i:016x}', 5, i - 99) for i in range(100, 112)]
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


class DiscoverImageTest(unittest.TestCase):
    """Sahib, 2026-11-07: Google Discover. og:image 1200+ px olmalıdır; əsas şəkil dardırsa eyni xəbərin başqa mənbəsinin şəkli."""

    def test_image_width_is_read_from_the_first_bytes(self):
        png = b'\x89PNG\r\n\x1a\n' + b'\x00\x00\x00\rIHDR' + (1280).to_bytes(4, 'big') + (720).to_bytes(4, 'big')
        self.assertEqual(updater._image_size(png), 1280)
        jpeg = b'\xff\xd8' + b'\xff\xe0' + (16).to_bytes(2, 'big') + b'J' * 14 + b'\xff\xc0' + (17).to_bytes(2, 'big') + b'\x08' + (630).to_bytes(2, 'big') + (1200).to_bytes(2, 'big') + b'\x00' * 12
        self.assertEqual(updater._image_size(jpeg), 1200)
        webp = b'RIFF' + b'\x00' * 4 + b'WEBPVP8X' + b'\x00' * 8 + (1599).to_bytes(3, 'little') + (899).to_bytes(3, 'little')
        self.assertEqual(updater._image_size(webp), 1600)
        self.assertEqual(updater._image_size(b'<html>'), 0)
        self.assertEqual(updater._image_size(b'\xff\xd8\xff\xe0'), 0, 'kəsik fayl xəta vermir')

    def test_the_widest_source_image_is_used_when_the_main_one_is_small(self):
        a = {'imageUrl': 'https://apa.az/small.jpg', 'alts': [{'imageUrl': 'https://report.az/big.jpg'}, {'imageUrl': 'https://axar.az/mid.jpg'},
                                                             {'imageUrl': 'https://x.az/logo.png'}, {'imageUrl': 'http://y.az/huge.jpg'}]}
        sizes = {'https://apa.az/small.jpg': 640, 'https://report.az/big.jpg': 1280, 'https://axar.az/mid.jpg': 900, 'https://x.az/logo.png': 4000}
        self.assertEqual(updater.discover_image(a, sizes), 'https://report.az/big.jpg', 'loqo və https olmayan ünvan seçilmir')
        self.assertEqual(updater.discover_image(a, {**sizes, 'https://apa.az/small.jpg': 1200}), 'https://apa.az/small.jpg', 'əsas şəkil kifayət qədər böyükdürsə o qalır')
        self.assertEqual(updater.discover_image(a, {}), 'https://apa.az/small.jpg', 'ölçü bilinmirsə əsas şəkil')
        self.assertEqual(updater.discover_image({'alts': [{'imageUrl': 'https://report.az/big.jpg'}]}, sizes), 'https://report.az/big.jpg', 'əsas şəkil yoxdursa mənbənin şəkli')
        self.assertEqual(updater.discover_image({}, sizes), '')

    def test_story_page_carries_its_own_row_so_an_old_shared_link_still_opens(self):
        """Sahib 2026-11-07 (paylaşma yoxlaması): lentdən və 200 xəbərlik arxivdən çıxmış xəbərin keçidi «Xəbər artıq lentdə yoxdur» deyirdi.
        Səhifə xəbərin sətrini özündə gətirir (#row), sayt onu oxuyur; skript deyil (CSP), </script> ilə qırılmır."""
        import datetime, json
        at = datetime.datetime.now(datetime.timezone.utc).isoformat()
        a = {'id': 'e' * 16, 'title': 'Başlıq </script><!-- x', 'summary': 'Xülasə', 'category': 'gundem', 'source': 'APA', 'sourceUrl': 'https://apa.az/1',
             'publishedAt': at, 'lang': 'az', 'imageUrl': 'https://apa.az/i.jpg', 'secret': 'yox',
             'alts': [{'id': 'a1', 'title': 'Alt', 'source': 'Report', 'sourceUrl': 'https://report.az/1', 'imageUrl': 'https://report.az/i.jpg'}]}
        page = updater.story_page(a)
        raw = re.search(r'<script type="application/json" id="row">(.*?)</script>', page, re.S).group(1)
        self.assertNotIn('</', raw)
        self.assertNotIn('<!--', raw)
        row = json.loads(raw)
        self.assertEqual(row['id'], a['id'])
        self.assertEqual(row['title'], a['title'])
        self.assertEqual(row['sourceUrl'], 'https://apa.az/1')
        self.assertEqual(row['alts'], [{'id': 'a1', 'title': 'Alt', 'source': 'Report', 'sourceUrl': 'https://report.az/1'}])
        self.assertNotIn('secret', row)
        self.assertGreaterEqual(updater.STORY_VER, 4, 'köhnə səhifələr sətirlə yenidən yazılır')

    def test_story_page_carries_the_chosen_image_and_still_loads_no_image(self):
        import datetime
        at = datetime.datetime.now(datetime.timezone.utc).isoformat()
        a = {'id': 'f' * 16, 'title': 'Başlıq', 'summary': 'Xülasə', 'category': 'gundem', 'source': 'APA', 'sourceUrl': 'https://apa.az/1', 'publishedAt': at, 'lang': 'az',
             'imageUrl': 'https://apa.az/small.jpg', 'alts': [{'source': 'Report', 'sourceUrl': 'https://report.az/1', 'imageUrl': 'https://report.az/big.jpg', 'lang': 'az'}]}
        page = updater.story_page(a, {'https://apa.az/small.jpg': 640, 'https://report.az/big.jpg': 1280})
        self.assertIn('<meta property="og:image" content="https://report.az/big.jpg" />', page)
        self.assertNotIn('<img', page, 'QIRMIZI XƏTT 3: tətbiq yüklənənə qədər əlavə şəkil sorğusu yoxdur')
        self.assertIn('content="https://apa.az/small.jpg"', updater.story_page(a), 'ölçü yoxdursa əvvəlki kimi')
        with patch.object(updater, '_image_width', side_effect=lambda u: 1280 if 'big' in u else 640) as probe, tempfile.TemporaryDirectory() as tmp, \
                patch.object(updater, 'IMG_SIZE_FILE', pathlib.Path(tmp) / 's.json'):
            rows = [{**a, 'alts': a['alts'] * 1 + [{'source': 'Trend', 'sourceUrl': 'https://trend.az/1', 'imageUrl': 'https://trend.az/x.jpg'}]}]
            self.assertEqual(updater.story_image_widths(rows), {'https://apa.az/small.jpg': 640, 'https://report.az/big.jpg': 1280, 'https://trend.az/x.jpg': 640})
            self.assertEqual(probe.call_count, 3)
            updater.story_image_widths(rows)
            self.assertEqual(probe.call_count, 3, 'hər ünvan bir dəfə soruşulur')


class StoryTemplateVersionTest(unittest.TestCase):
    """xeber/<id>/ şablonu dəyişəndə STORY_VER artmalıdır (sürət, 2026-11-09): 2026-11-08-də şablon app.js → app.min.js keçdi, versiya
    artmadı və ~3 400 köhnə səhifə kiçildilməmiş kodu (+16,5 KB gzip, +56 KB mənbə) yükləməkdə qaldı — index.json onları «cari» sayırdı."""
    TEMPLATE_SHA = {6: '47e7e28b315b'}  # yeni STORY_VER: hashlib.sha1(updater._STORY_HTML.encode('utf-8')).hexdigest()[:12] sətrini əlavə edin

    def test_story_template_change_bumps_story_ver(self):
        import hashlib
        sha = hashlib.sha1(updater._STORY_HTML.encode('utf-8')).hexdigest()[:12]
        self.assertIn(updater.STORY_VER, self.TEMPLATE_SHA, 'yeni STORY_VER: şablonun hash-ını TEMPLATE_SHA-ya yazın')
        self.assertEqual(sha, self.TEMPLATE_SHA[updater.STORY_VER], 'xeber/<id>/ şablonu dəyişib, STORY_VER artmayıb: köhnə səhifələr yenidən yazılmayacaq (write_story_pages versiya qapısı)')
        self.assertGreaterEqual(updater.STORY_REWRITE * 144, 5000, 'versiya artımı bir gündə (144 dövrə) bütün səhifələri yenidən yazmalıdır')

    def test_story_template_loads_only_the_startup_scripts(self):
        scripts = re.findall(r'<script[^>]*\bsrc="[^"]*?([\w.-]+\.js)"', updater._STORY_HTML)
        self.assertEqual(sorted(scripts), ['app.min.js', 'config.js', 'content-policy.js'], 'xəbər səhifəsi ilk açılışın üç faylını yükləyir, başqa heç nə')
        self.assertNotIn('assets/app.js', updater._STORY_HTML, 'oxucuya mənbə kodu getməz')


class NewsSitemapTest(unittest.TestCase):
    """Google News sitemap: son 48 saat, ən çoxu 1000, nəşr adı və tam ISO vaxt."""

    def story(self, sid, hours, title='Başlıq'):
        import datetime
        at = (datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(hours=hours)).isoformat()
        return {'id': sid, 'title': title, 'category': 'gundem', 'lang': 'az', 'publishedAt': at, 'source': 'APA'}

    def test_news_sitemap_lists_recent_story_pages_only(self):
        import datetime
        fresh, old, missing = 'a' * 16, 'b' * 16, 'c' * 16
        articles = [self.story(fresh, 3, 'Təzə xəbər'), self.story(old, 72, 'Köhnə xəbər'), self.story(missing, 1, 'Səhifəsiz')]
        stories = {fresh: [1, 3, 'gundem'], old: [1, 3, 'gundem']}
        with tempfile.TemporaryDirectory() as tmp:
            target = pathlib.Path(tmp) / 'sitemap-news.xml'
            sm = pathlib.Path(tmp) / 'sitemap.xml'
            with patch.object(updater, 'NEWS_SITEMAP_FILE', target), patch.object(updater, 'SITEMAP_FILE', sm):
                updater.write_news_sitemap(articles, stories)
                updater.write_sitemap({fresh: [1793950000, 3, 'gundem']})
            ns = {'s': 'http://www.sitemaps.org/schemas/sitemap/0.9', 'n': 'http://www.google.com/schemas/sitemap-news/0.9'}
            root = ET.parse(target).getroot()
            urls = root.findall('s:url', ns)
            self.assertEqual(len(urls), 1, '48 saatdan köhnə və səhifəsiz xəbər düşmür')
            url = urls[0]
            self.assertEqual(url.find('s:loc', ns).text, f'{updater.SITE}xeber/{fresh}/')
            news = url.find('n:news', ns)
            self.assertEqual(news.find('n:publication/n:name', ns).text, '8 Ulduz')
            self.assertEqual(news.find('n:publication/n:language', ns).text, 'az')
            self.assertEqual(news.find('n:title', ns).text, 'Təzə xəbər')
            pub = news.find('n:publication_date', ns).text
            self.assertRegex(pub, r'^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\+00:00$')
            datetime.datetime.fromisoformat(pub)
            lastmod = ET.parse(sm).getroot().find('s:url/s:lastmod', ns).text
            self.assertRegex(lastmod, r'^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\+00:00$')
        self.assertIn('Sitemap: " + SITE + "sitemap-news.xml\\n"', (ROOT / 'updater.py').read_text(encoding='utf-8'))
        self.assertIn('Sitemap: https://8ulduz.az/sitemap-news.xml', (ROOT / 'robots.txt').read_text(encoding='utf-8'))

    def test_news_sitemap_stops_at_one_thousand(self):
        articles = [self.story(f'{i:016x}', 1, f'Xəbər {i}') for i in range(1005)]
        stories = {a['id']: [1, 3, 'gundem'] for a in articles}
        with tempfile.TemporaryDirectory() as tmp:
            target = pathlib.Path(tmp) / 'news.xml'
            with patch.object(updater, 'NEWS_SITEMAP_FILE', target):
                updater.write_news_sitemap(articles, stories)
            text = target.read_text(encoding='utf-8')
        self.assertEqual(text.count('<loc>'), 1000)
        self.assertIn('xmlns:news="http://www.google.com/schemas/sitemap-news/0.9"', text)

    def test_copied_summary_is_one_attributed_line(self):
        long = 'Birinci cümlə buradadır. İkinci cümlə köçürülməməlidir. Üçüncü də yox.'
        line = updater._quote_line(long, 'APA')
        self.assertEqual(line, '«Birinci cümlə buradadır.» — APA')
        self.assertNotIn('İkinci', line)
