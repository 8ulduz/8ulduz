import datetime
import unittest
import updater

class RepeatedFeedDateTest(unittest.TestCase):
    def test_publisher_request_time_cannot_promote_an_old_article(self):
        url='https://azerbaijan-news.az/az/posts/detail/goygolde-44-filmi-1793263885/405663'
        first={'link':url,'title':'Göygöldə filmin nümayişi keçirilib','description':'','pubDate':'Fri, 30 Oct 2026 06:47:00 +0000'}
        second=dict(first,pubDate='Fri, 30 Oct 2026 07:00:00 +0000')
        a=updater.make_article(first,'Azərbaycan qəzeti','az')
        b=updater.make_article(second,'Azərbaycan qəzeti','az')
        self.assertEqual(a['publishedAt'],'2026-10-29T08:51:25+00:00')
        self.assertEqual(a['publishedAt'],b['publishedAt'])

    def test_epochs_are_not_inferred_for_unrelated_hosts_or_future_urls(self):
        self.assertEqual(updater.fixed_source_date('https://example.com/story-1793263885/405663'),'')
        self.assertEqual(updater.fixed_source_date('https://azerbaijan-news.az/story-1999999999/1',datetime.datetime(2026,10,30,tzinfo=datetime.timezone.utc)),'')


class SectionFeedLeakTest(unittest.TestCase):
    def test_a_sport_feed_that_leaks_other_news_does_not_put_them_in_sport(self):
        # 2026-11-07: TASS-ın idman lenti hadisə xəbərlərini də verir; İdman bölməsində «Kiyevdə partlayışlar» çıxırdı.
        when = 'Fri, 06 Nov 2026 20:50:00 +0000'
        leak = updater.make_article({'link': 'https://tass.ru/proisshestviya/28293735', 'title': 'В Киеве и Киевской области произошла серия взрывов',
                                     'description': 'Воздушная тревога объявлена в Киеве.', 'pubDate': when}, 'TASS Sport', 'ru', 'İdman')
        sport = updater.make_article({'link': 'https://tass.ru/sport/28293729', 'title': 'Брылин не против, если стычки на льду способны перерасти в драку',
                                      'description': 'Хоккеист высказался о матче КХЛ.', 'pubDate': when}, 'TASS Sport', 'ru', 'İdman')
        self.assertNotEqual(leak['category'], 'idman')
        self.assertEqual(sport['category'], 'idman')
