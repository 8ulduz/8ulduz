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
