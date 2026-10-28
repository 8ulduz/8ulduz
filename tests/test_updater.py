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
        self.assertEqual(updater.SLUGS["Səhiyyə"], "sehiyye")

    def test_ai_news_is_technology(self):
        self.assertEqual(updater.label_for("Azərbaycanda süni intellekt üzrə milli dil modelləri hazırlanır", "", "az"), "Texnologiya")
        self.assertEqual(updater.SLUGS["Texnologiya"], "texnologiya")

    def test_summary_is_shortened_at_a_word_boundary(self):
        s = updater._short("söz " * 100)
        self.assertTrue(s.endswith("…") and len(s) <= updater.SUMMARY_MAX + 1)
        self.assertEqual(updater._short("qısa"), "qısa")

    def test_raw_link_is_stripped_from_title(self):
        self.assertEqual(updater._plain("Harri Keyn mükafat qazanıb https://report.az/futbol/abc", title=True), "Harri Keyn mükafat qazanıb")


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
        self.assertFalse(updater.foreign_about_azerbaijan(world, "idman", "Qarabağ Avropa Liqasında qalib gəldi"))
        self.assertFalse(updater.foreign_about_azerbaijan("APA", "siyaset", "Azərbaycan Prezidenti qəbul edib"))
        self.assertFalse(updater.foreign_about_azerbaijan(world, "dunya", "Bakırköy'de kaza"))

    def test_negative_filter_needs_an_explicit_name_and_skips_official_sources(self):
        self.assertTrue(updater.is_negative_about_leadership("İlham Əliyev tənqid olundu", "", "Trend"))
        self.assertFalse(updater.is_negative_about_leadership("Fransa prezidenti etiraz aksiyası ilə üzləşdi", "", "Trend"))
        self.assertFalse(updater.is_negative_about_leadership("Prezident tənqid olundu", "", "Trend"))  # ümumi «prezident» sözü kifayət deyil
        self.assertFalse(updater.is_negative_about_leadership("İlham Əliyev korrupsiyaya qarşı fərman imzalayıb", "", "Prezident.az"))

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
                            "DATES_FILE": self.root / "dates.json",
                            "FEEDS": [("Test", "https://example.com/rss", "az", None)]}.items():
            p = patch.object(updater, name, value)
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
