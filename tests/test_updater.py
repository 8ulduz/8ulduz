import contextlib
import datetime
import io
import json
import pathlib
import tempfile
import unittest
from unittest.mock import patch

import updater


class RemovedSourceTest(unittest.TestCase):
    def test_removed_feed_and_retained_alternatives(self):
        self.assertFalse(any('azadliq.org' in feed[1] for feed in updater.FEEDS))
        articles = [{'source': 'Azadlıq', 'sourceUrl': 'https://www.azadliq.org/a/1'},
                    {'source': 'Other', 'sourceUrl': 'https://other.az/1', 'alts': [{'source': 'Azadlıq', 'sourceUrl': 'https://www.azadliq.org/a/1'}, {'source': 'Keep', 'sourceUrl': 'https://keep.az/1'}]}]
        clean = updater.prune_removed_sources(articles)
        self.assertEqual(len(clean), 1)
        self.assertEqual([a['source'] for a in clean[0]['alts']], ['Keep'])
        self.assertTrue(updater.removed_source({'sourceUrl': 'https://www.azadliq.org/a/2'}))
        self.assertFalse(updater.removed_source({'sourceUrl': 'https://azadliq.org.example.com/a/2'}))


class CategoriesTest(unittest.TestCase):
    def test_spectator_word_does_not_force_culture(self):
        self.assertEqual(updater.categorize('Qarabağ matçına 30 min tamaşaçı gəlib', 'futbol oyunu', 'az'), 'İdman')
        self.assertEqual(updater.categorize('Futbol tamaşaçıları oyunu izləyib', '', 'az'), 'İdman')
        self.assertEqual(updater.categorize('Yeni tamaşanın premyerası olacaq', '', 'az'), 'Mədəniyyət')

    def test_title_topic_beats_incidental_region_and_digital_words(self):
        self.assertEqual(updater.categorize('Naxçıvan Dövlət Kukla Teatrının tamaşasının Bakı premyerası olacaq', '', 'az'), 'Mədəniyyət')
        self.assertEqual(updater.categorize('Media savadlılığı dini dözümsüzlüklə mübarizədə əsas vasitədir', 'Rəqəmsal mühit imkanlar yaradır', 'az'), 'Cəmiyyət')

    def test_turkish_company_revenue_is_economy(self):
        self.assertEqual(updater.label_for("Çimsa'dan 9 ayda 41,8 milyar TL gelir", "", "tr"), "İqtisadiyyat")

    def test_regions_section(self):
        self.assertEqual(updater.label_for("Gəncədə yeni park istifadəyə verilib", "", "az"), "Bölgələr")
        self.assertEqual(updater.label_for("Lənkəran rayonunda yol təmir olunur", "", "az"), "Bölgələr")
        self.assertEqual(updater.label_for("Qarabağ Sabahla heç-heçə etdi", "futbol", "az"), "İdman")
        self.assertEqual(updater.SLUGS["Bölgələr"], "bolgeler")

    def test_regions_are_only_azerbaijani_places(self):
        # Yer adı ölkə/başqa söz kimi davam edirsə uyğun deyil; hal şəkilçiləri ilə uyğundur
        self.assertNotEqual(updater.label_for("Tokayev Qazaxıstanı belə dəyişir", "", "az"), "Bölgələr")
        self.assertNotEqual(updater.label_for("Şəkildə görünən şəxs tapılıb", "", "az"), "Bölgələr")
        self.assertEqual(updater.label_for("Şəkidə yeni park istifadəyə verilib", "", "az"), "Bölgələr")
        self.assertEqual(updater.label_for("Qazaxın mərkəzində yeni park istifadəyə verilib", "", "az"), "Bölgələr")
        self.assertEqual(updater.label_for("Şuşaya gedən yolda yeni park istifadəyə verilib", "", "az"), "Bölgələr")
        # xarici mənbədə Bölgələr yoxdur
        self.assertNotEqual(updater.label_for("Naxçıvanda sərgi açılıb", "", "az", world=True), "Bölgələr")

    def test_azertag_regions_page_parser(self):
        html = ('<h1> REGİONLAR </h1><div class="latest-news"><div class="sa-post mid-post"><a href="/xeber/berdede_terror-4484583">'
                "<img data-src='/files/2026/3/1200x630/a.jpg?v=1' alt='Bərdədə terror qurbanlarının xatirəsi anılıb' class='lazyload'></a>"
                '<ul class="global-list"><li>28.10.2026 [14:19]</li></ul><h2 class="entry-title"><a href="/xeber/berdede_terror-4484583">x</a></h2>'
                '<div class="sa-post mid-post"><a href="/xeber/no_date-1"><img alt="Tarixsiz"></a><h2 class="entry-title"></h2>')
        items = updater.parse_azertag_regions(html)
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0]["title"], "Bərdədə terror qurbanlarının xatirəsi anılıb")
        self.assertEqual(items[0]["link"], "https://azertag.az/xeber/berdede_terror-4484583")
        self.assertEqual(items[0]["pubDate"], "2026-10-28T14:19:00+04:00")
        self.assertTrue(items[0]["image"].startswith("https://azertag.az/files/"))

    def test_education_and_health_sections(self):
        self.assertEqual(updater.label_for("Məktəblərdə buraxılış imtahanının tarixi açıqlandı", "", "az"), "Təhsil")
        self.assertEqual(updater.label_for("Xəstəxanada yeni cərrahiyyə şöbəsi açılıb", "Həkimlər pasiyentləri qəbul edir.", "az"), "Səhiyyə")
        self.assertEqual(updater.SLUGS["Təhsil"], "tehsil")
        self.assertEqual(updater.SLUGS["Səhiyyə"], "heyat")

    def test_ai_news_is_technology(self):
        self.assertEqual(updater.label_for("Azərbaycanda süni intellekt üzrə milli dil modelləri hazırlanır", "", "az"), "Texnologiya")
        self.assertEqual(updater.SLUGS["Texnologiya"], "tehsil")

    def test_summary_is_shortened_at_a_word_boundary(self):
        s = updater._short("söz " * 100)
        self.assertTrue(s.endswith("…") and len(s) <= updater.SUMMARY_MAX + 1)
        self.assertEqual(updater._short("qısa"), "qısa")

    def test_raw_link_is_stripped_from_title(self):
        self.assertEqual(updater._plain("Harri Keyn mükafat qazanıb https://report.az/futbol/abc", title=True), "Harri Keyn mükafat qazanıb")


class StateSitesTest(unittest.TestCase):
    """RSS-siz iqtidar/dövlət saytları: Cross Media, Xalq qəzeti, Yeni Azərbaycan (HTML) və Baku TV (Google News sitemap)."""

    def test_crossmedia_listing_parser(self):
        page = ('<div class="category-card"><div class="img"><a href="https://crossmedia.az/az/article/114262">'
                '<img src="https://crossmedia.az/storage/news/2026_10_29/a.jpeg" alt="x"></a></div>'
                '<a href="https://crossmedia.az/az/article/114262"><div class="description"><p class="review">Cəmiyyət</p>'
                '<h3><strong>Bakıda Atatürkün heykəli ziyarət olunub</strong></h3><p class="date"><i></i><span>10:35 29.10.2026</span></p></div></a></div>'
                '<div class="category-card"><a href="https://crossmedia.az/az/article/114262"><h3>Təkrar</h3></a></div>'
                '<div class="category-card"><a href="https://crossmedia.az/az/article/114261"><h3>Şəkilsiz və saatsız</h3></a></div>')
        items = updater.parse_crossmedia(page)
        self.assertEqual([i["link"].rsplit("/", 1)[1] for i in items], ["114262", "114261"])
        self.assertEqual(items[0]["title"], "Bakıda Atatürkün heykəli ziyarət olunub")
        self.assertEqual(items[0]["pubDate"], "2026-10-29T10:35:00+04:00")
        self.assertEqual(items[0]["image"], "https://crossmedia.az/storage/news/2026_10_29/a.jpeg")
        self.assertEqual(items[1]["pubDate"], "")
        self.assertIsNone(items[1]["image"])

    def test_xalqqazeti_home_parser(self):
        page = ('<div class="rt-post-grid grid-meta"><div class="post-img"><a href="/az/resmi-xronika/286683-prezident-ilham-eliyev-icesco-nun">'
                '<img src="https://xalqqazeti.az/uploads/news/272156/1.jpg" alt="Prezident İlham Əliyev ICESCO-nun Baş direktorunu qəbul edib"></a></div>'
                '<div class="post-content"><h3 class="post-title"><a href="/az/resmi-xronika/286683-prezident-ilham-eliyev-icesco-nun">'
                'Prezident İlham Əliyev ICESCO-nun Baş direktorunu qəbul edib</a></h3><div class="post-meta"><ul><li><span class="rt-meta">'
                '<i class="far fa-calendar-alt icon"></i> 14:13 27.10.2026 </span></li></ul></div></div></div>'
                '<div class="rt-post-grid"><a href="/az/siyaset/">bölmə keçidi, xəbər deyil</a></div>')
        items = updater.parse_xalqqazeti(page)
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0]["link"], "https://xalqqazeti.az/az/resmi-xronika/286683-prezident-ilham-eliyev-icesco-nun")
        self.assertEqual(items[0]["title"], "Prezident İlham Əliyev ICESCO-nun Baş direktorunu qəbul edib")
        self.assertEqual(items[0]["pubDate"], "2026-10-27T14:13:00+04:00")
        self.assertEqual(items[0]["image"], "https://xalqqazeti.az/uploads/news/272156/1.jpg")

    def test_yeniazerbaycan_home_parser_takes_time_from_image_stamp(self):
        page = ('<li><div class="news-post image-post"><img src="https://yeniazerbaycan.com/thumb/575/2026/20261029103456-1793251414390132569_1200x630.jpg" alt="">'
                '<div class="hover-box"><h2 style="font-size: 20px"><a\n       href="https://yeniazerbaycan.com/az/Gundem/mehriban-eliyeva-tebrik-edib-156131">'
                'Birinci vitse-prezident Mehriban Əliyeva Türkiyə xalqının Cümhuriyyət Bayramını təbrik edib</a></h2>'
                '<ul class="post-tags"><li>29-oktyabr-2026</li></ul></div></div></li>'
                '<li><div class="news-post image-post"><img src="https://yeniazerbaycan.com/thumb/575/2026/no-stamp.jpg"><h2><a href="https://yeniazerbaycan.com/az/gundem/mehriban-eliyeva-tebrik-edib-156131">Eyni yazı, kiçik hərflə</a></h2></div></li>'
                '<li><div class="news-post image-post"><h2><a href="https://yeniazerbaycan.com/az/elm/sagirdler-156058">Şagirdlərin elektron yerdəyişməsinə başlanılır</a></h2></div></li>')
        items = updater.parse_yeniazerbaycan(page)
        self.assertEqual(len(items), 2)
        self.assertEqual(items[0]["link"], "https://yeniazerbaycan.com/az/gundem/mehriban-eliyeva-tebrik-edib-156131")
        self.assertEqual(items[0]["pubDate"], "2026-10-29T10:34:56+04:00")
        self.assertTrue(items[0]["image"].endswith("_1200x630.jpg"))
        self.assertEqual(items[1]["pubDate"], "")  # vaxt yoxdur: updater səhifə/ilk görülmə qaydası ilə doldurur
        self.assertIsNone(items[1]["image"])

    def test_google_news_sitemap_is_read_as_a_feed(self):
        xml = ('<?xml version="1.0" encoding="UTF-8"?><urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9" '
               'xmlns:news="http://www.google.com/schemas/sitemap-news/0.9" xmlns:image="http://www.google.com/schemas/sitemap-image/1.1">'
               '<url><loc>https://baku.tv/siyaset/prezident-qebul-etdi</loc><news:news><news:publication><news:name>Baku.tv</news:name>'
               '<news:language>az</news:language></news:publication><news:publication_date>2026-10-29T09:28:27+04:00</news:publication_date>'
               '<news:title>Prezident İlham Əliyev nazirləri qəbul etdi - Baku TV</news:title></news:news>'
               '<image:image><image:loc>https://baku.tv/storage/posts/list/1.webp</image:loc></image:image></url>'
               '<url><loc>https://baku.tv/sehife</loc><lastmod>2026-10-29T00:00:00+04:00</lastmod></url></urlset>').encode("utf-8")
        items = updater.parse_feed(xml)
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0]["title"], "Prezident İlham Əliyev nazirləri qəbul etdi - Baku TV")
        self.assertEqual(items[0]["image"], "https://baku.tv/storage/posts/list/1.webp")
        self.assertEqual(updater.to_iso(items[0]["pubDate"]), "2026-10-29T05:28:27+00:00")

    def test_html_sources_go_through_the_page_parser_and_are_in_the_feed_list(self):
        names = {f[0]: f[1] for f in updater.AZ_FEEDS}
        for name in ("Cross Media", "Xalq qəzeti", "Yeni Azərbaycan", "Baku TV", "Azərbaycan qəzeti"):
            self.assertIn(name, names)
        self.assertIn(names["Cross Media"], updater.PAGE_PARSERS)
        page = ('<div class="category-card"><a href="https://crossmedia.az/az/article/1"><h3>Prezident İlham Əliyev fərman imzalayıb</h3>'
                '<p class="date"><span>10:00 29.10.2026</span></p></a></div>')
        with patch.object(updater, "fetch", return_value=page.encode("utf-8")):
            source, items, err, used = updater.fetch_feed(("Cross Media", names["Cross Media"], "az", None))
        self.assertIsNone(err)
        self.assertEqual([i["title"] for i in items], ["Prezident İlham Əliyev fərman imzalayıb"])


class PresidentPageTest(unittest.TestCase):
    PAGE = """
    <article class="news-photo"><div class="news-photo_category"><span class="category_date">27 oktyabr 2026<br>13:50</span></div>
      <a class="news-photo_body" href="/az/articles/view/74332"><div class="news-photo_photo"><img src="https://static.president.az/a.jpg" alt=""></div>
      <div class="news-photo_label"><span class="label-title">İlham Əliyev ICESCO-nun Baş direktorunu qəbul edib</span></div></a></article>
    <article class="news-video news-photo"><div class="news-video_category"><span class="category_date">27 oktyabr 2026<br>10:00</span></div>
      <div class="news-video_body"><div class="news-video_video"><iframe src="https://www.youtube.com/embed/WO5xn-6-IQI?rel=0"></iframe></div>
      <a class="news-video_label" href="/az/articles/view/74324"> İlham Əliyev Forumun açılışında çıxış edib <span class="news-video_duration"></span></a></div></article>
    <article class="news-text"><div class="news-text_category"><span class="category_date">21 oktyabr 2026<br>19:35</span></div>
      <a class="news-text_body" href="/az/articles/view/74257"><span>Ərdoğan İlham Əliyevə zəng edib</span><p>Oktyabrın 21-də zəng edib.</p></a></article>
    """

    def test_all_three_block_types_are_parsed(self):
        items = updater.parse_president_page(self.PAGE)
        self.assertEqual([i["link"].rsplit("/", 1)[1] for i in items], ["74332", "74324", "74257"])
        self.assertEqual(items[0]["pubDate"], "2026-10-27T09:50:00+00:00")  # Bakı 13:50 → UTC
        self.assertEqual(items[1]["title"], "İlham Əliyev Forumun açılışında çıxış edib")
        self.assertEqual(items[1]["image"], "https://i.ytimg.com/vi/WO5xn-6-IQI/hqdefault.jpg")
        self.assertTrue(items[1]["video"])
        self.assertEqual(items[2]["description"], "Oktyabrın 21-də zəng edib.")
        self.assertEqual(items[2]["pubDate"], "2026-10-21T15:35:00+00:00")


class YouTubeTest(unittest.TestCase):
    def test_channel_page_parser(self):
        page = ('x{"contentId":"nckqYOoK5lw","contentType":"LOCKUP_CONTENT_TYPE_VIDEO","a":1,"metadata":{"lockupMetadataViewModel":'
                '{"title":{"content":"Kiyev problemi \\u2014 test"},"metadata":{"metadataParts":[{"text":{"content":"64"},"accessibilityLabel":"64 views"},'
                '{"text":{"content":"21 min ago"},"accessibilityLabel":"21 minutes ago"}]}}}'
                '{"contentId":"trDnnGEAkRk","contentType":"LOCKUP_CONTENT_TYPE_VIDEO","metadata":{"lockupMetadataViewModel":{"title":{"content":"İkinci"}}}}')
        now = datetime.datetime(2026, 10, 28, 12, 0, tzinfo=datetime.timezone.utc)
        items = updater.parse_yt_channel_page(page, now=now)
        self.assertEqual([i["link"][-11:] for i in items], ["nckqYOoK5lw", "trDnnGEAkRk"])
        self.assertEqual(items[0]["title"], "Kiyev problemi — test")
        self.assertEqual(items[0]["pubDate"], "2026-10-28T11:39:00+00:00")
        self.assertEqual(items[1]["pubDate"], "2026-10-28T12:00:00+00:00")
        self.assertTrue(items[0]["image"].endswith("/nckqYOoK5lw/hqdefault.jpg"))


class SocialFromNewsTest(unittest.TestCase):
    def test_first_seen_time_is_kept_for_known_videos(self):
        old = [{"url": "https://y/1", "publishedAt": "2026-10-27T10:00:00+00:00"}]
        items = [{"url": "https://y/1", "publishedAt": "2026-10-28T05:33:00+00:00"},
                 {"url": "https://y/2", "publishedAt": "2026-10-28T05:33:00+00:00"}]
        updater._keep_first_seen(items, old)
        self.assertEqual(items[0]["publishedAt"], "2026-10-27T10:00:00+00:00")
        self.assertEqual(items[1]["publishedAt"], "2026-10-28T05:33:00+00:00")

    def test_leadership_posts_are_taken_from_news_and_deduplicated(self):
        arts = [
            {"id": "1", "title": "Prezidentin sosial şəbəkə hesablarında forumun açılışına dair video paylaşılıb",
             "source": "Modern.az", "sourceUrl": "https://m/1", "publishedAt": "2026-10-27T11:57:00+00:00", "alts": []},
            {"id": "2", "title": "Mehriban Əliyeva bugünkü sərgidən paylaşım etdi - Video",
             "source": "Azpolitika.info", "sourceUrl": "https://a/2", "publishedAt": "2026-10-27T15:35:00+00:00", "alts": []},
            {"id": "3", "title": "Mehriban Əliyevanın Instagram hesabında sərgidən videoçarx paylaşıldı",
             "source": "Teleqraf", "sourceUrl": "https://t/3", "publishedAt": "2026-10-27T15:50:00+00:00", "alts": [{}, {}]},
            {"id": "4", "title": "Zəfər xronikası. 28 oktyabr 2020: Mehriban Əliyeva paylaşım edib",
             "source": "Ordu.az", "sourceUrl": "https://o/4", "publishedAt": "2026-10-28T03:05:00+00:00", "alts": []},
            {"id": "5", "title": "Nazir paylaşım edib", "source": "X", "sourceUrl": "https://x/5", "publishedAt": "2026-10-28T03:05:00+00:00"},
        ]
        posts = updater.social_from_news(arts)
        self.assertEqual([p["who"] for p in posts], ["prezident", "birinci-xanim"])
        self.assertEqual(posts[0]["network"], "X")
        self.assertEqual(posts[0]["via"], "Modern.az")
        # eyni paylaşım: 3 mənbəli başlıq qalır, vaxt ilk xəbərinki, şəbəkə Instagram
        self.assertEqual(posts[1]["id"], "3")
        self.assertEqual(posts[1]["publishedAt"], "2026-10-27T15:35:00+00:00")
        self.assertEqual(posts[1]["network"], "Instagram")
        self.assertNotIn("_t", posts[1])


class ImageTest(unittest.TestCase):
    def test_failed_photo_lookup_is_retried_then_backed_off(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder = pathlib.Path(tmp)
            cache = folder / 'og.json'
            url = 'https://example.com/article'
            cache.write_text(json.dumps({url: ''}), encoding='utf-8')
            with patch.object(updater, 'OG_FILE', cache), patch.object(updater, 'OUT_DIR', folder), patch.object(updater, '_fetch_og', return_value='') as fetch:
                updater.fill_og_images([{'sourceUrl': url}])
                self.assertEqual(fetch.call_count, 1)
                updater.fill_og_images([{'sourceUrl': url}])
                self.assertEqual(fetch.call_count, 1)
                stored = json.loads(cache.read_text(encoding='utf-8'))
                stored['_meta']['retryAfter'][url] = 0
                cache.write_text(json.dumps(stored), encoding='utf-8')
                fetch.return_value = 'https://example.com/photo.jpg'
                article = {'sourceUrl': url}
                updater.fill_og_images([article])
                self.assertEqual(fetch.call_count, 2)
                self.assertEqual(article['imageUrl'], 'https://example.com/photo.jpg')

    def test_generic_share_images_are_rejected_and_real_ones_kept(self):
        self.assertTrue(updater._is_generic_img("https://azertag.az/resources/images/social.jpg"))
        self.assertTrue(updater._is_generic_img("https://img.piri.net/resim/imagecrop/2026/04/01/09/50/tr_son_dakika_530x530.jpg"))
        self.assertFalse(updater._is_generic_img("https://static.president.az/upload/960x572/2026/10/27/a.jpg"))
        page = b'<html><head><meta property="og:image" content="https://azertag.az/resources/images/social.jpg"/>' \
               b'<link rel="image_src" href="/files/2026/real.jpg"></head></html>'
        self.assertEqual(updater._og_from_html(page, "https://azertag.az/xeber/1"), "https://azertag.az/files/2026/real.jpg")
        ld = b'<script type="application/ld+json">{"@type":"NewsArticle","image":{"@type":"ImageObject","url":"https://x.az/p.jpg"}}</script>'
        self.assertEqual(updater._og_from_html(ld, "https://x.az/a"), "https://x.az/p.jpg")


class DateAndFilterTest(unittest.TestCase):
    def test_dates_are_normalised_to_utc_and_naive_means_baku(self):
        self.assertEqual(updater._to_iso("Mon, 27 Oct 2026 13:50:00 +0400"), "2026-10-27T09:50:00+00:00")
        self.assertEqual(updater._to_iso("2026-10-27T13:50:00"), "2026-10-27T09:50:00+00:00")
        self.assertEqual(updater._to_iso("2026-10-27T09:50:00Z"), "2026-10-27T09:50:00+00:00")
        self.assertIsNotNone(updater._parse_dt("2026-10-27T13:50:00").tzinfo)

    def test_foreign_sources_do_not_cover_the_azerbaijani_state(self):
        world = next(iter(updater.WORLD_SOURCES))
        self.assertTrue(updater.foreign_about_azerbaijan(world, "siyaset", "Bahçeli'den Azerbaycan-Türkiye mesajı"))
        self.assertTrue(updater.foreign_about_azerbaijan(world, "dunya", "Президент Азербайджана принял делегацию"))
        self.assertFalse(updater.foreign_about_azerbaijan("Match TV", "idman", "Qarabağ Avropa Liqasında qalib gəldi"))
        self.assertFalse(updater.foreign_about_azerbaijan("APA", "siyaset", "Azərbaycan Prezidenti qəbul edib"))
        self.assertFalse(updater.foreign_about_azerbaijan(world, "dunya", "Bakırköy'de kaza"))

    def test_negative_filter_needs_an_explicit_name_and_skips_official_sources(self):
        self.assertTrue(updater.is_negative_about_leadership("İlham Əliyev tənqid olundu", "", "Trend"))
        self.assertFalse(updater.is_negative_about_leadership("Fransa prezidenti etiraz aksiyası ilə üzləşdi", "", "Trend"))
        self.assertFalse(updater.is_negative_about_leadership("Prezident tənqid olundu", "", "Trend"))  # ümumi «prezident» sözü kifayət deyil
        self.assertFalse(updater.is_negative_about_leadership("İlham Əliyev korrupsiyaya qarşı fərman imzalayıb", "", "Prezident.az"))

    def test_strong_filter_covers_state_institutions_and_opposition_framing(self):
        neg = updater.is_negative_about_leadership
        self.assertTrue(neg("Hakimiyyət jurnalistlərə təzyiq göstərir", "", "Trend"))
        self.assertTrue(neg("Milli Məclisin qərarı tənqid olundu", "", "APA"))
        self.assertTrue(neg("Birinci vitse-prezidentin fondu ittiham edildi", "", "Oxu.az"))
        self.assertTrue(neg("Hüquq müdafiəçiləri siyasi məhbusların azadlığını tələb edir", "", "Trend"))  # rəhbərlik adı olmadan da
        self.assertTrue(neg("Милли Шура провела митинг", "Оппозиция", "Vesti.az"))
        self.assertTrue(neg("Baku authorities accused of crackdown", "", "Azernews"))
        self.assertTrue(neg("Aliyev yönetimi eleştirildi", "", "Hürriyet"))
        self.assertFalse(neg("Hakimiyyət yeni sosial paketi təsdiqlədi", "", "Trend"))
        self.assertFalse(neg("Fransa hökuməti istefaya çağırılıb", "", "Trend"))
        self.assertFalse(neg("Milli Məclis yeni qanun qəbul etdi", "", "APA"))
        self.assertNotIn("Meydan TV", [f[0] for f in updater.FEEDS])

    def test_same_event_with_different_headlines_becomes_one_card(self):
        # 28.10.2026: eyni istefa 7 mənbədə 7 fərqli başlıqla (ad da fərqli yazılıb) — bir kart olmalıdır
        base = {"category": "gundem", "lang": "az", "imageUrl": None}
        rows = [
            ("Olke.az", "16:52", "Pərviz Abubəkirov İŞDƏN ÇIXARILDI", "Səhiyyə Nazirliyinin mətbuat xidmətinin rəhbəri Pərviz Abubəkirov vəzifəsindən ayrılıb."),
            ("Metbuat", "16:47", "Pərviz Abubəkirov işdən ayrıldı", "Səhiyyə Nazirliyinin mətbuat xidmətinin rəhbəri Pərviz Abubəkirov vəzifəsindən ayrılıb."),
            ("Reyting.az", "16:26", "Səhiyyə Nazirliyinin mətbuat katibi vəzifədən çıxarılıb", ""),
            ("Axar.az", "15:12", "Bu nazirliyin mətbuat xidmətinin rəhbəri işdən çıxarıldı", "Pərviz Abubəkirov"),
            ("Aznews.az", "15:03", "Pərviz Əbubəkirov vəzifəsindən çıxarıldı", ""),
            ("Anews.az", "14:49", "Səhiyyə Nazirliyinin mətbuat xidmətinin rəhbəri vəzifəsindən azad edilib", "Səhiyyə Nazirliyinin mətbuat xidmətinin rəhbəri Pərviz Abubəkirov vəzifəsindən azad edilib."),
            ("Bizim.Media", "14:32", "Pərviz Abubəkirov 8 ildən sonra vəzifəsindən AYRILDI", "Səhiyyə Nazirliyinin mətbuat xidmətinin rəhbəri Pərviz Abubəkirov vəzifəsindən ayrılıb."),
        ]
        arts = [dict(base, source=s, title=t, summary=d, sourceUrl=f"https://{s}/{i}", publishedAt=f"2026-10-28T{hm}:00+00:00")
                for i, (s, hm, t, d) in enumerate(rows)]
        out = updater.group_duplicates(arts)
        self.assertEqual(len(out), 1)
        self.assertEqual(len(out[0]["alts"]), 6)
        # fərqli hadisələr birləşmir: başqa şəxsin təyinatı, eyni nazirlikdə başqa xəbər
        other = [dict(base, source="APA", title="Elçin Məmmədov Səhiyyə Nazirliyinə müavin təyin edilib", summary="",
                      sourceUrl="https://apa/1", publishedAt="2026-10-28T15:30:00+00:00"),
                 dict(base, source="Report", title="Səhiyyə Nazirliyi qrip mövsümü ilə bağlı xəbərdarlıq edib", summary="",
                      sourceUrl="https://report/1", publishedAt="2026-10-28T15:40:00+00:00")]
        self.assertEqual(len(updater.group_duplicates(arts + other)), 3)
        self.assertTrue(updater._edits1("abubekirov", "ebubekirov") and not updater._edits1("abubekirov", "memmedov"))

    def test_paraphrased_school_stories_merge_but_generic_daily_events_do_not(self):
        # 28.10.2026, Təhsil: eyni hücum 6 mənbədə 6 başlıqla (sinonimlər: jurnalist/media, döydü/hücum/zorakılıq)
        base = {"category": "tehsil", "lang": "az", "imageUrl": None}
        summ = "Bakının Yasamal rayonunda yerləşən 225 saylı orta məktəbdə REAL TV-nin əməkdaşlarına hücum olub."
        rows = [
            ("Lent.az", "18:08", "Bakıda intihar edən məktəblinin yaxınları jurnalistləri döydü, saxlanılanlar var", ""),
            ("Bizim.Media", "18:00", "Bakıda məktəbdə jurnalistlərə hücum oldu - ANBAAN VİDEO", summ),
            ("News24.az", "17:58", "“Real TV”nin əməkdaşlarını həmin məktəbin önündə döydülər - Video", summ),
            ("Teleqraf", "17:55", "Bakıda məktəbdə media nümayəndələrinə qarşı zorakılıq edildi", ""),
            ("Qafqazinfo", "17:48", "“Real TV”nin əməkdaşlarını həmin məktəbin öndündə döydülər", ""),
            ("Modern.az", "17:38", "225 nömrəli məktəbdə REAL TV-nin əməkdaşlarına hücum oldu - VİDEO", summ),
        ]
        arts = [dict(base, source=s, title=ti, summary=d, sourceUrl=f"https://{s}/{i}", publishedAt=f"2026-10-28T{hm}:00+00:00")
                for i, (s, hm, ti, d) in enumerate(rows)]
        out = updater.group_duplicates(arts)
        dump = [(o["source"], [x.get("source") for x in o.get("alts") or []]) for o in out]
        self.assertLessEqual(len(out), 3, dump)
        self.assertGreaterEqual(max(len(o.get("alts") or []) for o in out), 2, dump)
        # şagirdin ölümü: ortaq lövbər/anlayışlar olanlar birləşir
        death = [dict(base, source="Olke.az", title="Məktəbdə yıxılaraq həyatını itirən şagirdin anası da faciəli şəkildə ölübmüş",
                      summary="Bakının Yasamal rayonunda yerləşən 225 nömrəli tam orta məktəbdə həyatını itirən 7-ci sinif şagirdi.",
                      sourceUrl="https://olke/1", publishedAt="2026-10-28T17:42:00+00:00"),
                 dict(base, source="Xezerxeber", title="Faciəvi şəkildə həyatını itirən 7-ci sinif şagirdinin məktəb yoldaşları DANIŞDILAR - VİDEO",
                      summary="", sourceUrl="https://xezer/1", publishedAt="2026-10-28T16:45:00+00:00")]
        self.assertEqual(len(updater.group_duplicates(death)), 1)
        # eyni şagird haqqında lövbərsiz rakurslar (2+ xüsusi anlayış: şagird + məktəb / yıxılma) və hücum xəbərləri
        # (ortaq lövbərlər: Yasamal + 225) hamısı bir hadisə zənciridir — bir kart
        angles = [dict(base, source="Axar.az", title="Məktəbdə həyatını itirən şagirdlə bağlı yeni detallar", summary="Dadaşova",
                       sourceUrl="https://axar/1", publishedAt="2026-10-28T17:47:00+00:00"),
                  dict(base, source="Axar.az", title="Şagird pəncərədən yıxılıb öldü, psixoloqlar cəlb olundu", summary="Təhsil İdarəsi",
                       sourceUrl="https://axar/2", publishedAt="2026-10-28T17:05:00+00:00")]
        self.assertLessEqual(len(updater.group_duplicates(death + angles)), 2)
        self.assertLessEqual(len(updater.group_duplicates(arts + death + angles)), 4)
        # gündəlik ümumi hadisələr (qəza, həbs) lövbərsiz birləşmir
        generic = [dict(base, source="APA", title="Bakıda qəza: 2 nəfər ölüb", summary="", sourceUrl="https://apa/q1", publishedAt="2026-10-28T10:00:00+00:00"),
                   dict(base, source="Report", title="Bakıda avtobus qəzası: sürücü həlak olub", summary="", sourceUrl="https://report/q2", publishedAt="2026-10-28T11:00:00+00:00"),
                   dict(base, source="APA", title="Bakıda narkotik satan şəxs saxlanılıb", summary="", sourceUrl="https://apa/h1", publishedAt="2026-10-28T12:00:00+00:00"),
                   dict(base, source="Report", title="Bakıda oğurluq edən şəxs saxlanılıb", summary="", sourceUrl="https://report/h2", publishedAt="2026-10-28T12:30:00+00:00")]
        self.assertEqual(len(updater.group_duplicates(generic)), 4)
        self.assertEqual(" ".join(updater._concepts("Jurnalistlər döyüldü, şagird öldü").split()), "media zorakılıq , şagird ölüm")

    def test_event_grouping_does_not_snowball_unrelated_deaths_and_accidents(self):
        # 28.10.2026 canlıda «Ağır qəza» kartı 120 alternativ udmuşdu (İspaniya qatar qəzası + başsağlığı + Türkiyə qəzası +
        # məktəb hadisəsi + Şəmkir bıçaqlanma ...). Fərqli hadisələr ayrı qalmalı, rəsmi reaksiya hadisədən ayrı olmalıdır.
        base = {"category": "gundem", "lang": "az", "imageUrl": None}
        rows = [
            ("Sia.az", "14:54", "İspaniyada qatarlar toqquşdu: 68 nəfər öldü", ""),
            ("Bizim.Media", "15:07", "İspaniyada qatar qəzasında ölənlərin sayı 68-ə çatdı", ""),
            ("Olke.az", "15:30", "İlham Əliyev qatar qəzasına görə İspaniyaya başsağlığı verib", ""),
            ("Report", "15:35", "Prezident İlham Əliyev İspaniyada baş verən qatar qəzası ilə bağlı başsağlığı verib", ""),
            ("Moderator.az", "16:20", "Ağır qəza baş verdi - Ölən və yaralananlar var", "Türkiyənin Çorum şəhərinin Alaca rayonunda iki avtomobilin toqquşması nəticəsində 4 nəfər ölüb."),
            ("Qafqazinfo", "16:40", "Şəmkirdə 67 yaşlı kişi bıçaqlandı, şübhəli qonşusudur", ""),
            ("Konkret.az", "16:48", "Göygöldə evdən meyit tapıldı", "Göygöldə 62 yaşlı kişi bədbəxt hadisə nəticəsində ölüb."),
            ("Olke.az", "18:12", "Bakıda kişi evində ölü tapıldı", ""),
            ("Xezerxeber", "16:45", "Faciəvi şəkildə həyatını itirən 7-ci sinif şagirdinin məktəb yoldaşları DANIŞDILAR", ""),
        ]
        arts = [dict(base, source=s, title=ti, summary=d, sourceUrl=f"https://{s}/{i}", publishedAt=f"2026-10-28T{hm}:00+00:00")
                for i, (s, hm, ti, d) in enumerate(rows)]
        self.assertIn("reaksi", updater._event_sig(arts[2])[3])
        pairs = [(3, 1), (2, 1), (2, 0), (1, 0)]
        self.assertEqual([updater._same_event(arts[i], arts[j]) for i, j in pairs], [0, 0, 0, 1],
                         [sorted(updater._event_sig(arts[k])[3]) for k in (2, 1)])
        out = updater.group_duplicates(arts)
        dump = [(o["title"][:28], [x.get("title", "")[:28] for x in o.get("alts") or []]) for o in out]
        self.assertGreaterEqual(len(out), 7, dump)  # İspaniya qəzası, başsağlığı, Türkiyə, Şəmkir, Göygöl, Bakı, məktəb
        self.assertLessEqual(max(len(o.get("alts") or []) for o in out), 1, dump)
        crash = next(o for o in out if "68" in o["title"])
        self.assertFalse(any("başsağlığı" in (x.get("title") or "") for x in crash.get("alts") or []))
        self.assertTrue(any("başsağlığı" in o["title"] for o in out))
        self.assertEqual(updater._places("Göygöldə evdən meyit tapıldı. Məktəbdə hadisə"), {"goygol"})

    def test_unrelated_remembered_headlines_are_removed_but_verified_ones_survive(self):
        stamp = "2026-10-29T18:00:00+00:00"
        title = "Ceyhun Bayramov jesti ilə diqqət mərkəzinə düşdü"
        article = {"source": "Moderator.az", "sourceUrl": "https://moderator.az/a", "title": title,
                   "publishedAt": stamp, "alts": [
                       {"source": "Yenicag", "sourceUrl": "https://yenicag.az/b", "title": "Trampla Ərdoğan arasında telefon danışığı oldu", "publishedAt": stamp},
                       {"source": "Olke.az", "sourceUrl": "https://olke.az/c", "title": title, "publishedAt": stamp}]}
        result = updater.group_duplicates([article])[0]
        self.assertEqual([a["source"] for a in result["alts"]], ["Olke.az"])
        self.assertEqual(updater.detect_lang("Why President Ilham Aliyev skips the OTS Summit in Türkiye", "Azərbaycan Prezidenti haqqında xəbər", "az"), "en")

    def test_remembered_alternatives_are_bounded(self):
        # Əvvəlki dövrdən gələn 300 alternativ (köhnə qar topu) yenidən qoşulmur; pəncərə daxilindəkilər 20-yə qədər qalır
        base = {"category": "gundem", "lang": "az", "imageUrl": None, "summary": ""}
        old_alts = [{"source": f"S{i}", "sourceUrl": f"https://s{i}/x", "publishedAt": "2026-10-28T10:00:00+00:00"} for i in range(300)]
        a = dict(base, source="Azernews", title="President Ilham Aliyev visited the exhibition with family", sourceUrl="https://az/1",
                 publishedAt="2026-10-28T12:00:00+00:00", alts=old_alts)
        out = updater.group_duplicates([a])
        self.assertLessEqual(len(out[0].get("alts") or []), 20)
        self.assertNotIn("alts", out[0], "Opaque legacy alternatives cannot prove they report the same event")
        stale = [{"source": "T", "sourceUrl": "https://t/x", "publishedAt": "2026-10-20T10:00:00+00:00"}]
        b = dict(base, source="Report", title="Bakıda yeni metro stansiyası açıldı", sourceUrl="https://r/1",
                 publishedAt="2026-10-28T12:00:00+00:00", alts=stale)
        self.assertNotIn("alts", updater.group_duplicates([b])[0])

    def test_official_template_titles_do_not_merge_and_alts_never_repeat_a_primary(self):
        base = {"summary": "", "imageUrl": None, "category": "prezident", "lang": "az"}
        a = dict(base, source="Prezident.az", title="İlham Əliyev Niderlandın xarici işlər nazirini qəbul edib",
                 sourceUrl="https://president.az/az/articles/view/1", publishedAt="2026-10-26T08:05:00+00:00")
        b = dict(base, source="Prezident.az", title="İlham Əliyev Hindistanın xarici işlər nazirini qəbul edib",
                 sourceUrl="https://president.az/az/articles/view/2", publishedAt="2026-10-26T07:05:00+00:00")
        c = dict(base, source="APA", title="İlham Əliyev Niderlandın xarici işlər nazirini qəbul edib",
                 sourceUrl="https://apa.az/1", publishedAt="2026-10-26T08:30:00+00:00", imageUrl="x.jpg",
                 alts=[{"source": "Trend", "sourceUrl": "https://president.az/az/articles/view/2", "publishedAt": ""}])
        out = updater.group_duplicates([a, b, c])
        self.assertEqual(len(out), 2)  # Niderland və Hindistan ayrı qalır
        nid = next(x for x in out if "Niderland" in x["title"])
        self.assertEqual(nid["source"], "Prezident.az")  # rəsmi mənbə əsasdır
        self.assertEqual([x["sourceUrl"] for x in nid.get("alts", [])], ["https://apa.az/1"])  # əsas kartın ünvanı alt-da təkrarlanmır


class OfficialPrimaryTest(unittest.TestCase):
    def test_official_source_stays_primary_over_agency_copy(self):
        official = {"source": "Prezident.az", "imageUrl": None, "summary": "", "publishedAt": "2026-10-27T13:50:00+04:00"}
        agency = {"source": "Modern.az", "imageUrl": "x.jpg", "summary": "uzun xülasə " * 10, "publishedAt": "2026-10-27T14:00:00+04:00"}
        self.assertIs(updater._prefer_primary(agency, official), official)
        self.assertIs(updater._prefer_primary(official, agency), official)


class FootballTest(unittest.TestCase):
    def test_parse_pfl_builds_table_rounds_and_scorers(self):
        seasons = {"data": [{"id": 76, "title": "2026-2027", "leagues": [{"id": 52, "title": "Misli Premyer Liqası"}]}]}
        grid = {"data": [
            {"title": "Sabah", "logo": "s.png", "rate": {"o": 9, "q": 5, "h": 2, "m": 2, "vq": 12, "bq": 8, "tf": 4, "x": 17, "ordering": 2}},
            {"title": "Qarabağ", "logo": "q.png", "rate": {"o": 9, "q": 7, "h": 1, "m": 1, "vq": 18, "bq": 6, "tf": 12, "x": 22, "ordering": 1}},
        ]}
        tours = {"data": [
            {"title": "9", "is_current": 0, "games": [{"club_1": {"title": "Sabah"}, "club_2": {"title": "Qarabağ"}, "club_score_1": 0, "club_score_2": 0, "status": 3, "start_date": "25/10/2026 18:00", "stadion": {"title": "Bank Respublika Arena"}}]},
            {"title": "10", "is_current": 1, "games": [{"club_1": {"title": "Qəbələ"}, "club_2": {"title": "Qarabağ"}, "club_score_1": 0, "club_score_2": 0, "status": 0, "start_date": "31/10/2026 17:30", "stadion": None}]},
        ]}
        scorers = {"data": {"data": [{"club": {"title": "Şamaxı"}, "player": {"name": "Rikardo", "surname": "Apolinario"}, "value": "3"}]}}
        d = updater.parse_pfl(seasons, grid, tours, scorers)
        self.assertEqual([t["team"] for t in d["table"]], ["Qarabağ", "Sabah"])
        self.assertEqual(d["table"][0]["pos"], 1)
        self.assertEqual(d["table"][0]["pts"], 22)
        self.assertEqual(d["roundPlayed"], "9")
        self.assertEqual(d["roundNext"], "10")
        self.assertTrue(d["results"][0]["played"])
        self.assertEqual(d["results"][0]["date"], "2026-10-25T18:00+04:00")
        self.assertFalse(d["fixtures"][0]["played"])
        self.assertEqual(d["fixtures"][0]["home"], "Qəbələ")
        self.assertEqual(d["scorers"], [{"name": "Rikardo Apolinario", "club": "Şamaxı", "goals": 3}])
        self.assertEqual(d["league"], "Misli Premyer Liqası")


class EspnTest(unittest.TestCase):
    def test_parse_espn_soccer_and_basketball(self):
        soccer = {"children": [{"name": "Premier League", "standings": {"entries": [
            {"team": {"displayName": "Manchester City", "shortDisplayName": "Man City", "logos": [{"href": "mc.png"}]},
             "note": {"description": "Champions League", "color": "#81D6AC"},
             "stats": [{"name": "rank", "value": 1}, {"name": "gamesPlayed", "value": 8}, {"name": "wins", "value": 7}, {"name": "ties", "value": 0},
                       {"name": "losses", "value": 1}, {"name": "pointsFor", "value": 20}, {"name": "pointsAgainst", "value": 9},
                       {"name": "pointDifferential", "value": 11}, {"name": "points", "value": 21}]},
            {"team": {"displayName": "Arsenal", "shortDisplayName": "Arsenal", "logos": []},
             "stats": [{"name": "rank", "value": 2}, {"name": "gamesPlayed", "value": 8}, {"name": "wins", "value": 6}, {"name": "ties", "value": 1},
                       {"name": "losses", "value": 1}, {"name": "pointsFor", "value": 15}, {"name": "pointsAgainst", "value": 5},
                       {"name": "pointDifferential", "value": 10}, {"name": "points", "value": 19}]},
        ]}}]}
        g = updater.parse_espn(soccer, "soccer")
        self.assertEqual(len(g), 1)
        self.assertEqual([r["team"] for r in g[0]["rows"]], ["Man City", "Arsenal"])
        self.assertEqual(g[0]["rows"][0]["pts"], 21)
        self.assertEqual(g[0]["rows"][0]["note"], "Champions League")
        nba = {"children": [{"name": "Eastern Conference", "standings": {"entries": [
            {"team": {"displayName": "Miami Heat", "shortDisplayName": "Heat", "logos": []},
             "stats": [{"name": "wins", "value": 0}, {"name": "losses", "value": 4}, {"name": "winPercent", "value": 0.0}, {"name": "gamesBehind", "displayValue": "3.5"}, {"name": "playoffSeed", "value": 15}]},
            {"team": {"displayName": "Boston Celtics", "shortDisplayName": "Celtics", "logos": []},
             "stats": [{"name": "wins", "value": 4}, {"name": "losses", "value": 0}, {"name": "winPercent", "value": 1.0}, {"name": "gamesBehind", "displayValue": "-"}, {"name": "playoffSeed", "value": 1}]},
        ]}}, {"name": "Western Conference", "standings": {"entries": []}}]}
        b = updater.parse_espn(nba, "basketball")
        self.assertEqual(len(b), 1)  # boş konfrans atılır
        self.assertEqual(b[0]["rows"][0]["team"], "Celtics")
        self.assertEqual(b[0]["rows"][1]["gb"], "3.5")


class SectionPagesTest(unittest.TestCase):
    def test_section_pages_and_sitemap_are_written(self):
        articles = [
            {"id": "1", "title": "Qarabağ <b>qalib</b> gəldi", "category": "idman", "lang": "az", "source": "APA", "sourceUrl": "https://apa.az/1", "publishedAt": "2026-10-27T10:00:00+00:00"},
            {"id": "2", "title": "Galatasaray kazandı", "category": "idman", "lang": "tr", "source": "NTV", "sourceUrl": "https://ntv.com.tr/2", "publishedAt": "2026-10-27T11:00:00+00:00"},
        ]
        with tempfile.TemporaryDirectory() as tmp:
            root = pathlib.Path(tmp)
            with patch.object(updater, "SECTIONS_DIR", root / "bolme"), patch.object(updater, "SITEMAP_FILE", root / "sitemap.xml"):
                updater.write_sections(articles)
                updater.write_sitemap()
                page = (root / "bolme" / "idman" / "index.html").read_text(encoding="utf-8")
                sitemap = (root / "sitemap.xml").read_text(encoding="utf-8")
                pages = [d for d in (root / "bolme").iterdir() if (d / "index.html").exists()]
        self.assertIn("Qarabağ &lt;b&gt;qalib&lt;/b&gt; gəldi", page)
        self.assertNotIn("Galatasaray", page)  # yalnız Azərbaycan dilində başlıqlar
        self.assertIn('src="../../assets/app.js"', page)
        self.assertIn('"../../#/bolme/idman"', page)
        self.assertIn(updater.SITE + "bolme/idman/", sitemap)
        self.assertEqual(len(pages), len(updater.SECTIONS))

    def test_site_url_follows_the_cname_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = pathlib.Path(tmp)
            self.assertEqual(updater.site_url(root), "https://8ulduz.github.io/8ulduz/")
            (root / "CNAME").write_text("8ulduz.az\n", encoding="utf-8")
            self.assertEqual(updater.site_url(root), "https://8ulduz.az/")

    def test_background_reference_is_not_chronicle(self):
        for title in ("2027-ci il nə ilidir?", "Keçmiş köçkünlər Laçında qəbul edildi"):
            with self.subTest(title=title):
                self.assertNotEqual(updater.label_for(title, "Prezident İlham Əliyev sərəncam imzalayıb.", "az"), "Prezident")

    def test_actual_chronicle_in_multiple_languages(self):
        for title, lang in (("İlham Əliyev qonağı qəbul edib", "az"),
                            ("Prezidentin sosial şəbəkə hesablarında paylaşım", "az"),
                            ("Mehriban Əliyeva rəssamı təbrik edib", "az"),
                            ("Ильхам Алиев принял делегацию", "ru"),
                            ("President Ilham Aliyev meets delegation", "en")):
            with self.subTest(title=title):
                self.assertEqual(updater.label_for(title, "", lang), "Prezident")

    def test_absheron_is_not_usa(self):
        self.assertEqual(updater.label_for("Abşeronda oğula hökm oxundu", "məhkəmə qərarı", "az"), "Cəmiyyət")
        self.assertTrue(updater.has_any(updater.norm_az("ABŞ-da görüş keçirildi"), ["abş"]))
        self.assertTrue(updater.has_any(updater.norm_az("ABŞ"), ["abş"]))
        self.assertFalse(updater.has_any(updater.norm_az("Abşeron"), ["abş"]))

    def test_real_crime_headlines_are_society(self):
        self.assertEqual(updater.label_for("Abşeronda anasının üstünə benzin töküb yandıran oğula hökm oxundu",
                                          "Abdurrəhman Həsənlinin məhkəmə prosesi başa çatıb.", "az"), "Cəmiyyət")
        self.assertEqual(updater.label_for("Еще одна массовая драка в Баку",
                                          "Инцидент случился перед банкетным залом.", "ru"), "Cəmiyyət")
        self.assertNotEqual(updater.label_for("Mehribanlıq nədir?", "", "az"), "Prezident")


class UndatedFeedTest(unittest.TestCase):
    NOW = datetime.datetime(2026, 10, 28, 9, 0, tzinfo=datetime.timezone.utc)

    def test_page_date_is_read_from_json_ld_meta_or_time(self):
        now = self.NOW
        self.assertEqual(updater.parse_page_date(b'<script type="application/ld+json">{"datePublished": "2026-10-28 11:32"}</script>', now),
                         "2026-10-28T07:32:00+00:00")  # zonasız: Bakı vaxtı
        self.assertEqual(updater.parse_page_date('<meta content="2026-10-27T13:50:00+04:00" property="article:published_time">', now),
                         "2026-10-27T09:50:00+00:00")
        self.assertEqual(updater.parse_page_date('<time datetime="2026-10-26T08:00:00Z">dünən</time>', now), "2026-10-26T08:00:00+00:00")
        self.assertEqual(updater.parse_page_date('<meta property="article:published_time" content="2030-01-01T00:00:00Z">', now), "")  # gələcək
        self.assertEqual(updater.parse_page_date("<html><body>tarix yoxdur</body></html>", now), "")

    def test_url_date_hint(self):
        self.assertEqual(updater.url_date_hint("https://ikisahil.az/post/x", "https://ikisahil.az/photo/600x0_2/upload/2026/10/28/a.jpg"),
                         datetime.date(2026, 10, 28))
        self.assertEqual(updater.url_date_hint("https://x.az/news/2026-09-16/abc"), datetime.date(2026, 9, 16))
        self.assertIsNone(updater.url_date_hint("https://x.az/news/123456", ""))

    def test_undated_items_use_page_date_once_and_old_ones_are_dropped(self):
        now, cache = self.NOW, {}
        fresh = {"link": "https://ikisahil.az/post/a", "image": "https://ikisahil.az/photo/upload/2026/10/28/x.jpg"}
        old = {"link": "https://ikisahil.az/post/b", "image": "https://ikisahil.az/photo/upload/2026/09/16/y.jpg"}
        with patch.object(updater, "_fetch_page_date", return_value="2026-10-28T07:32:00+00:00") as fetched:
            iso, budget = updater.undated_date(fresh, cache, 30, now=now)
            self.assertEqual((iso, budget), ("2026-10-28T07:32:00+00:00", 29))
            self.assertEqual(updater.undated_date(fresh, cache, budget, now=now), (iso, 29))  # keşdən, sorğusuz
            self.assertEqual(updater.undated_date(old, cache, budget, now=now), ("", 29))  # köhnə yazı: sorğusuz atılır
            self.assertEqual(fetched.call_count, 1)
        with patch.object(updater, "_fetch_page_date", return_value=""):
            self.assertEqual(updater.undated_date({"link": "https://x.az/n"}, cache, 0, now=now), ("", 0))  # büdcə bitib
            self.assertEqual(updater.undated_date({"link": "https://x.az/n"}, cache, 1, now=now), ("2026-10-28T09:00:00+00:00", 0))  # ilk görülmə
            self.assertEqual(updater.undated_date({"link": "https://x.az/d", "image": "https://x.az/i/2026/10/27/p.jpg"}, cache, 1, now=now),
                             ("2026-10-27T08:00:00+00:00", 0))  # ünvan tarixi, Bakı 12:00
        self.assertEqual(set(cache), {"https://ikisahil.az/post/a", "https://x.az/n", "https://x.az/d"})

    def test_date_cache_is_pruned_and_saved(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = pathlib.Path(tmp)
            with patch.object(updater, "OUT_DIR", root), patch.object(updater, "DATES_FILE", root / "dates.json"):
                updater.save_dates({"https://a": "2026-10-28T07:00:00+00:00", "https://b": "2026-10-01T07:00:00+00:00", "bad": None}, now=self.NOW)
                self.assertEqual(updater.load_dates(), {"https://a": "2026-10-28T07:00:00+00:00"})


class UpdateHealthTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(dir=pathlib.Path(__file__).parent)
        self.root = pathlib.Path(self.tmp.name)
        self.patches = []
        for name, value in {"OUT_DIR": self.root, "OUT_FILE": self.root / "news.json",
                            "STATUS_FILE": self.root / "status.json", "SOURCES_FILE": self.root / "sources.json",
                            "DATES_FILE": self.root / "dates.json", "LATEST_FILE": self.root / "latest.json",
                            "RECENT_FILE": self.root / "recent.json", "CACHE_DIR": self.root,
                            "FEEDS": [("Test", "https://example.com/rss", "az", None)]}.items():
            p = patch.object(updater, name, value)
            p.start()
            self.patches.append(p)
        # Bu testlər tarix və status məntiqi üçündür; məzmun qaydası test_red_lines.py-dadır.
        p = patch.object(updater.content_policy, "enforce", lambda articles: (articles, {}))
        p.start()
        self.patches.append(p)
        self.article = {"id": "old", "sourceUrl": "https://example.com/old", "source": "Test",
                        "title": "Məktəb açıldı", "summary": "", "lang": "az", "category": "cemiyyet",
                        "publishedAt": datetime.datetime.now(datetime.timezone.utc).isoformat()}
        updater.OUT_FILE.write_text(json.dumps({"articles": [self.article]}), encoding="utf-8")

    def tearDown(self):
        for p in reversed(self.patches):
            p.stop()
        self.tmp.cleanup()

    def cycle(self, feed_result):
        with patch.object(updater, "fetch_feed", return_value=feed_result), \
             patch.object(updater, "official_items", return_value=([], [])), \
             patch.object(updater, "official_source_rows", return_value=[]), \
             patch.object(updater, "fill_og_images", return_value=0), \
             contextlib.redirect_stdout(io.StringIO()):
            return updater.main()

    def test_all_sources_fail_preserves_news_and_success_time(self):
        before = updater.OUT_FILE.read_bytes()
        updater.STATUS_FILE.write_text('{"checkedAt":"2026-10-01T00:00:00+00:00","ok":true}')
        result = self.cycle(("Test", [], "timeout", "https://example.com/rss"))
        self.assertFalse(result["ok"])
        self.assertEqual(updater.OUT_FILE.read_bytes(), before)
        updater.write_status(**result)
        status = json.loads(updater.STATUS_FILE.read_text())
        self.assertFalse(status["ok"])
        self.assertEqual(status["checkedAt"], "2026-10-01T00:00:00+00:00")
        self.assertIn("attemptedAt", status)

    def test_success_without_new_articles_is_success(self):
        item = {"link": self.article["sourceUrl"], "title": self.article["title"], "description": ""}
        result = self.cycle(("Test", [item], None, "https://example.com/rss"))
        self.assertTrue(result["ok"])
        self.assertEqual(result["successful"], 1)

    def test_fast_cycle_adds_undated_item_once_the_slow_process_dated_it(self):
        # İki Sahil lentində tarix yoxdur: tarixi yavaş proses tapır, sürətli dövrə dates.json-dan oxuyur.
        link = "https://example.com/new"
        day = datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds")
        updater.DATES_FILE.write_text(json.dumps({link: day}), encoding="utf-8")
        item = {"link": link, "title": "Yeni məktəb binası açıldı", "description": "", "image": None}
        with patch.object(updater, "collect_fast", return_value=([("Test", [item], None, "https://example.com/rss")], [], [])), \
             patch.object(updater, "RELABEL_MARK", self.root / "relabeled"), patch.object(updater, "UNDATED_FILE", self.root / "undated.json"), \
             patch.object(updater, "GROUPS_FILE", self.root / "groups.json"), patch.object(updater, "OG_FILE", self.root / "og.json"), \
             contextlib.redirect_stdout(io.StringIO()):
            updater.main(fast=True)
        urls = [a["sourceUrl"] for a in json.loads(updater.OUT_FILE.read_text(encoding="utf-8"))["articles"]]
        self.assertIn(link, urls)

    def test_known_undated_article_gets_its_real_date_fixed(self):
        # Köhnə xəbər «indi» damğası ilə siyahıdadır; lent onu tarixsiz verir — səhifə tarixi tapılanda qeyd düzəlir
        item = {"link": self.article["sourceUrl"], "title": self.article["title"], "description": "", "image": None}
        when = updater._norm_iso(datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(hours=5))
        with patch.object(updater, "_fetch_page_date", return_value=when) as fetched:
            result = self.cycle(("Test", [item], None, "https://example.com/rss"))
        self.assertTrue(result["ok"])
        self.assertEqual(fetched.call_count, 1)
        data = json.loads(updater.OUT_FILE.read_text(encoding="utf-8"))
        self.assertEqual([a["sourceUrl"] for a in data["articles"]], [item["link"]])  # təkrar yaranmır
        self.assertEqual(data["articles"][0]["publishedAt"], when)
        self.assertEqual(result["stats"]["undated"], 0)
        with patch.object(updater, "_fetch_page_date", return_value="") as fetched:  # ikinci dövrə: keşdən, sorğusuz
            self.cycle(("Test", [item], None, "https://example.com/rss"))
        self.assertEqual(fetched.call_count, 0)

    def test_undated_feed_item_gets_page_date_and_is_cached(self):
        item = {"link": "https://example.com/new", "title": "Yeni məktəb açıldı", "description": "", "image": None}
        when = updater._norm_iso(datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(hours=3))  # keş 10 gün saxlayır
        with patch.object(updater, "_fetch_page_date", return_value=when) as fetched:
            result = self.cycle(("Test", [item], None, "https://example.com/rss"))
        self.assertTrue(result["ok"])
        self.assertEqual(fetched.call_count, 1)
        data = json.loads(updater.OUT_FILE.read_text(encoding="utf-8"))
        new = next(a for a in data["articles"] if a["sourceUrl"] == item["link"])
        self.assertEqual(new["publishedAt"], when)
        self.assertEqual(json.loads(updater.DATES_FILE.read_text(encoding="utf-8")), {item["link"]: when})
        self.assertEqual(result["stats"]["undated"], 1)

    def test_cli_failure_has_nonzero_exit_and_no_public_rewrite(self):
        with patch.object(updater, "main", return_value={"ok": False, "successful": 0, "total": 1}), \
             patch.object(updater, "write_public") as public, \
             patch.object(updater.sys, "argv", ["updater.py", "--no-markets", "--no-social"]):
            self.assertEqual(updater.run(), 1)
            public.assert_not_called()

    def test_unexpected_error_has_nonzero_exit(self):
        with patch.object(updater, "main", side_effect=RuntimeError("test")), \
             patch.object(updater.sys, "argv", ["updater.py", "--no-markets", "--no-social"]), \
             contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(updater.run(), 1)


if __name__ == "__main__":
    unittest.main()
