import json
import pathlib
import tempfile
import unittest
from reader_content import extract_article, update_reader

BODY = 'Bu, Azərbaycan dilində mənbədən alınmış məqalənin səsli oxuma üçün nəzərdə tutulmuş mətnidir. ' * 5

class ReaderContentTest(unittest.TestCase):
    def test_structured_article_and_paywall(self):
        def page(free):
            return '<script type="application/ld+json">' + json.dumps({'@type':'NewsArticle','articleBody':BODY,'isAccessibleForFree':free}) + '</script>'
        self.assertEqual(extract_article(page(True)),BODY.strip())
        self.assertEqual(extract_article(page(False)),'')

    def test_only_article_paragraphs_not_navigation_or_related_news(self):
        page=f'<nav><p>{BODY}</p></nav><article><p>{BODY}</p><p>İkinci abzas: {BODY}</p><aside><p>Reklam məlumatı</p></aside></article>'
        text=extract_article(page)
        self.assertIn('İkinci abzas',text)
        self.assertNotIn('Reklam',text)
        self.assertEqual(text.count('İkinci abzas'),1)
        # 2026-11-12: sinifsiz səhifədə də nəsr bloku oxunur (dense_text); menyu və yan panel yenə oxunmur
        self.assertEqual(extract_article('<p>'+BODY+'</p>'),BODY.strip())
        self.assertEqual(extract_article('<nav><p>'+BODY+'</p></nav><aside><p>'+BODY+'</p></aside>'),'')

    def test_junk_under_the_article_is_not_read(self):
        # Sahib, 2026-11-08: «xəbərin altındakı lazımsız şeyləri də oxuyur».
        page = ('<article><p>Bakıda bu gün g&amp;uuml;n ərzində yağış yağıb. ' + BODY + '</p><p>İkinci abzas: ' + BODY + '</p>'
                '<p>Xəbər xoşunuza gəldi? Sosial şəbəkələrdə paylaşın</p><p>Ən son xəbərləri bizim WhatsApp kanalımızda izləyin @media</p>'
                '<p>Mətndə səhv varsa, onu qeyd edib Ctrl+Enter düyməsini basaraq bizə göndərin.</p>'
                '<p class="bold-title">Dövlət və hökumət rəsmiləri Zəfər Tağı abidəsini ziyarət etdilər</p>'
                '<p>Nazir: Ərazi bütövlüyünün bərpası Azərbaycanın qüdrətini daha da artırdı</p>'
                '<p>Oxşar xəbərlər</p><p>Bu abzas oxşar xəbərlər bölməsindədir və oxunmamalıdır, çünki xəbərin özü deyil. ' + BODY + '</p>'
                '<p>{{photo-big-1}} Məlumatdan istifadə etdikdə istinad mütləqdir.</p></article>')
        text = extract_article(page)
        self.assertIn('İkinci abzas', text)
        self.assertIn('gün ərzində', text, 'HTML işarəsi hərfə çevrilir')
        for junk in ('paylaşın', 'WhatsApp', 'Ctrl', 'Zəfər Tağı', 'Ərazi bütövlüyünün', 'oxunmamalıdır', 'photo', 'istinad'):
            self.assertNotIn(junk, text)
        ld = '<script type="application/ld+json">' + json.dumps({'@type': 'NewsArticle', 'articleBody': BODY + 'Hörmətli istifadəçi, ödənişli xəbərləri əldə etmək üçün qeydiyyatdan keçin.'}) + '</script>'
        self.assertEqual(extract_article(ld), BODY.strip())

    def test_audio_cache_only_fetches_azerbaijani_and_reuses_success(self):
        with tempfile.TemporaryDirectory() as tmp:
            file=pathlib.Path(tmp)/'reader.json';seen=[]
            rows=[{'lang':lang,'sourceUrl':'https://example.com/'+lang,'source':'Example'} for lang in ['az','en']]
            def fetch(url):
                seen.append(url)
                return '<script type="application/ld+json">'+json.dumps({'@type':'Article','articleBody':BODY})+'</script>'
            update_reader(rows,file,fetch)
            update_reader(rows,file,fetch)
            self.assertEqual(seen,['https://example.com/az'])
            self.assertEqual(len(json.loads(file.read_text(encoding='utf-8'))['articles']),1)


class Oxu24Test(unittest.TestCase):
    def test_oxu24_news_detail_body_is_read(self):
        # Sahib, 2026-11-09: «Vasif Talıbovun oğlu xəbər yaydı — Dinlə tam oxumur», «gündəmdə Oxu24 hamısı belədir».
        page = ('<div class="news-detail"><h1><b>Vasif Talıbovun oğlu <span>AÇIQLAMA YAYDI</span></b></h1>'
                '<div class="category"><div><p>CƏMİYYƏT</p><p>623</p></div></div>'
                '<div class="google-source"><div class="google-source__title">Xəbərlərimizi Google-da izləyin</div></div>'
                '<div class="description"><p><b>Naxçıvan Ali Məclisinin keçmiş sədri Vasif Talıbovun oğlu Rza Talıbov açıqlama yayıb.</b></p>'
                '<p><b><div><script async src="//x/slot.js"></script><ins class="ainsyndication"></ins></div></b></p>'
                '<p><a href="https://oxu24.com/az">Oxu24.com</a> xəbər verir ki, Rza Talıbov açıqlamasında adına saxta TikTok hesabı açıldığını bildirib.</p>'
                '<p>"Diqqətinizə çatdırmaq istəyirəm ki, TikTok sosial şəbəkəsində fəaliyyət göstərən səhifə mənim icazəm olmadan açılmış saxta profildir.</p>'
                '<p>' + BODY + '</p><p>Xəbər xoşunuza gəldi? Sosial şəbəkələrdə paylaşın</p><p>Bizə yazın: (+99450) 247 90 86</p></div></div>')
        text = extract_article(page)
        self.assertIn('Rza Talıbov açıqlama yayıb', text)
        self.assertIn('saxta profildir', text)
        for junk in ('CƏMİYYƏT', 'Google-da', 'paylaşın', 'Bizə yazın', 'AÇIQLAMA YAYDI'):
            self.assertNotIn(junk, text)


class DenseTextTest(unittest.TestCase):
    """Sahib, 2026-11-12: «dinləməni tam düzəlt hər bir saytda» — mətn blokunun sinif adı tanınmayan saytlar yalnız başlıqla oxunurdu."""
    P1 = 'Dövlət Sosial Müdafiə Fondu noyabrın 25-də Ucar rayonunda sığortaedənlər üçün təlim keçirəcək. Təlimdə yeni qaydalar izah olunacaq.'
    P2 = 'Tədbirdə iştirak etmək istəyənlər Fondun qəbul şöbəsinə yaxınlaşa bilərlər. Qeydiyyat noyabrın 24-dək davam edir.'
    P3 = 'Fonddan bildirilib ki, belə görüşlər digər rayonlarda da keçiriləcək və vətəndaşların sualları yerində cavablandırılacaq.'

    def test_unknown_class_names_are_read_from_the_block_with_most_prose(self):
        # DSMF, Teleqraf, Reyting, icra hakimiyyətləri: <div class="inner__text"><p>…
        page = ('<header><p>' + self.P1 + ' menyu.</p></header><div class="tarih">12 NOYABR 2026</div><h1>Başlıq oxunmur</h1>'
                '<div class="inner__text"><p>' + self.P1 + '</p><p>' + self.P2 + '</p><div class="ads"></div><p>' + self.P3 + '</p>'
                '<p>Teqlər: DSMF   Ucar   təlim</p></div>'
                '<div class="widget"><p>' + BODY + '</p></div><div class="related"><p>' + BODY + '</p></div>')
        text = extract_article(page)
        self.assertTrue(text.startswith('Dövlət Sosial Müdafiə Fondu'))
        self.assertTrue(text.endswith('cavablandırılacaq.'))
        for junk in ('NOYABR 2026', 'Başlıq oxunmur', 'Teqlər', 'menyu', 'səsli oxuma'):
            self.assertNotIn(junk, text)

    def test_text_separated_by_line_breaks_without_paragraph_tags(self):
        # Aia.az: <span class="short">mətn<br>mətn</span>
        page = ('<div class="xeber"><span class="short" style="text-align: justify">' + self.P1 + '<br><br>' + self.P2 + '<br>' + self.P3 + '</span></div>'
                '<div class="altyazi1">© Copyright 2015. Bütün hüquqlar qorunur.</div>')
        text = extract_article(page)
        self.assertIn('yaxınlaşa bilərlər', text)
        self.assertNotIn('Copyright', text)

    def test_block_matching_the_page_description_beats_a_longer_block(self):
        # Ordu.az: məqalədən uzun «digər xəbərlər» bloku seçilirdi; səhifənin öz təsviri (og:description) məqaləni göstərir.
        page = ('<meta property="og:description" content="' + self.P1 + '">'
                '<div class="other"><p>' + BODY + '</p><p>' + BODY + '</p></div><div class="project_info"><p>' + self.P1 + '</p><p>' + self.P2 + '</p></div>')
        text = extract_article(page)
        self.assertTrue(text.startswith('Dövlət Sosial Müdafiə Fondu'))
        self.assertNotIn('səsli oxuma', text)

    def test_dates_view_counts_and_headline_feeds_are_not_read(self):
        # Baku TV video səhifəsi, Sportinfo: mətn yoxdur — əvvəl tarix, baxış sayı və digər xəbərlərin başlıqları oxunurdu.
        feed = ''.join('<li>1%d:40 Premyer Liqanın %d-ci turunda mübahisəli anlar çox olub. Səhv kimdədir?</li>' % (i, i) for i in range(1, 7))
        self.assertEqual(extract_article('<div class="news-content"><div>12 noyabr 2026 Xəbərlərimizi Google-da izləyin. Abunə ol. 254 baxış.</div><ul>' + feed + '</ul></div>'), '')
        self.assertEqual(extract_article('<div class="news-content"><ul>' + feed.replace('<li>1', '<li>11 Noyabr 1') + '</ul></div>'), '')

    def test_short_story_is_read_only_when_it_is_the_page_description(self):
        short = 'Aktyor Natiq Fərzəliyevin səhhətində problem yaranıb. Onun əməliyyat olunduğu və özünü yaxşı hiss etdiyi bildirilib.'
        self.assertEqual(extract_article('<div class="x"><p>' + short + '</p></div>'), '')
        self.assertEqual(extract_article('<meta name="description" content="' + short + '"><div class="x"><p>' + short + '</p></div>'), short)


class FeedArticleTest(unittest.TestCase):
    def test_full_text_from_the_source_feed_for_the_matching_link_only(self):
        from reader_content import feed_article
        body = '<p>' + DenseTextTest.P1 + '</p><p>' + DenseTextTest.P2 + '</p><p>Xəbər xoşunuza gəldi? Sosial şəbəkələrdə paylaşın</p>'
        xml = ('<rss><channel><item><title>Başqa</title><link>https://report.az/a/1</link><content:encoded><![CDATA[<p>' + BODY + '</p>]]></content:encoded></item>'
               '<item><title>Bu</title><link><![CDATA[https://www.report.az/a/2/]]></link><description>qısa</description><content:encoded><![CDATA[' + body + ']]></content:encoded></item></channel></rss>')
        text = feed_article(xml, 'https://report.az/a/2')
        self.assertTrue(text.startswith('Dövlət Sosial Müdafiə Fondu') and text.endswith('davam edir.'))
        self.assertEqual(feed_article(xml, 'https://report.az/a/3'), '')
        self.assertEqual(feed_article('', 'https://report.az/a/2'), '')
        self.assertEqual(feed_article('<item><link>https://report.az/a/2</link><description>qısa</description></item>', 'https://report.az/a/2'), '')


class SkipClassTest(unittest.TestCase):
    """2026-11-12: düzən sarğıları («with-sidebar», «b-footer--black--white») bütün səhifəni bloklayırdı; ses-worker skipClass ilə eyni."""

    def test_layout_wrappers_are_not_blocked_but_real_side_blocks_are(self):
        from reader_content import skip_class
        for c in ('t-content__with-sidebar', 'news_in_page with_sidebar_block', 'b-header--white b-footer--black--white', 'p-default-layout--window-view-x'):
            self.assertFalse(skip_class('div', c), c)
        self.assertFalse(skip_class('body', 'single tag-news sidebar'))
        for c in ('sidebar', 'right-sidebar', 'post-tags', 'news-date', 'author-box', 'related-news', 'social-share', 'comments-area', 'views'):
            self.assertTrue(skip_class('div', c), c)
        page = ('<html class="b-footer--black--white"><body class="u-header-with-tag-list"><div class="news_in_page with_sidebar_block"><div class="texts">'
                '<p>' + DenseTextTest.P1 + '</p><p>' + DenseTextTest.P2 + '</p></div><div class="sidebar"><p>' + BODY + '</p></div></div></body></html>')
        text = extract_article(page)
        self.assertTrue(text.startswith('Dövlət Sosial Müdafiə Fondu'))
        self.assertNotIn('səsli oxuma', text)
