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
        self.assertEqual(extract_article('<p>'+BODY+'</p>'),'')

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
