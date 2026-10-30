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
