"""Extract public article text for audio only; never render it in news cards."""
import datetime
import html
import json
import os
import re
from html.parser import HTMLParser
from concurrent.futures import ThreadPoolExecutor
from urllib.parse import urlparse


def clean(text):
    return re.sub(r'\s+', ' ', html.unescape(re.sub(r'<[^>]+>', ' ', text or ''))).strip()


class ArticleParagraphs(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.stack = []
        self.paragraph = None
        self.rows = []
        self.fragments = []

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        marker = attrs.get('class', '') + ' ' + attrs.get('id', '')
        parent = self.stack[-1] if self.stack else ('', False, False)
        scoped = parent[1] or tag == 'article' or attrs.get('itemprop') == 'articleBody' or attrs.get('id') == 'font_size' or bool(re.search(r'(?:article|news|entry|post|detail)[-_ ](?:body|content|text|desc)|fullstory|full-post-article|\btext-one\b|\bzoomtext\b', marker, re.I))
        blocked = parent[2] or tag in ('nav', 'aside', 'footer', 'header', 'h1', 'script', 'style', 'form') or bool(re.search(r'related|recommend|advert|comment|social|paywall', marker, re.I))
        if tag not in ('br', 'img', 'hr', 'meta', 'link', 'input', 'source', 'wbr'):
            self.stack.append((tag, scoped, blocked))
        if tag == 'p' and scoped and not blocked:
            self.paragraph = []

    def handle_data(self, data):
        if self.stack and self.stack[-1][1] and not self.stack[-1][2]:
            self.fragments.append(data)
        if self.paragraph is not None and self.stack and not self.stack[-1][2]:
            self.paragraph.append(data)

    def handle_endtag(self, tag):
        if tag == 'p' and self.paragraph is not None:
            text = clean(' '.join(self.paragraph))
            if len(text) >= 30:
                self.rows.append(text)
            self.paragraph = None
        for i in range(len(self.stack) - 1, -1, -1):
            if self.stack[i][0] == tag:
                self.stack = self.stack[:i]
                break


def extract_article(raw):
    def nodes(value):
        if isinstance(value, list):
            for row in value:
                yield from nodes(row)
        elif isinstance(value, dict):
            yield value
            for row in value.values():
                if isinstance(row, (dict, list)):
                    yield from nodes(row)
    candidates = []
    for script in re.findall(r'<script\b[^>]*type=[\"\x27]application/ld\+json[\"\x27][^>]*>(.*?)</script>', raw, re.I | re.S):
        try:
            candidates.extend(nodes(json.loads(script)))
        except (ValueError, TypeError):
            continue
    articles = [node for node in candidates if any('Article' in str(kind) for kind in (node.get('@type') if isinstance(node.get('@type'), list) else [node.get('@type')]))]
    if any(node.get('isAccessibleForFree') in (False, 'false') for node in articles):
        return ''
    for node in articles:
        text = clean(node.get('articleBody')) if isinstance(node.get('articleBody'), str) else ''
        if 200 <= len(text) <= 24000:
            return text
    parser = ArticleParagraphs()
    parser.feed(raw)
    text = '\n\n'.join(dict.fromkeys(parser.rows))
    if len(parser.rows) >= 2 and 200 <= len(text) <= 24000:
        return text
    text = clean(' '.join(parser.fragments))
    return text if 200 <= len(text) <= 24000 else ''


def update_reader(articles, path, fetcher, limit=24):
    """Bounded, cached extraction. Failed sources are retried after six hours."""
    now = datetime.datetime.now(datetime.timezone.utc)
    try:
        old = json.loads(path.read_text(encoding='utf-8')).get('articles', {})
    except (OSError, ValueError):
        old = {}
    relevant = [a for a in articles if a.get('lang') == 'az' and urlparse(a.get('sourceUrl', '')).scheme == 'https'][:400]
    output = {a['sourceUrl']: old[a['sourceUrl']] for a in relevant if a['sourceUrl'] in old}
    pending = []
    for article in relevant:
        cached = output.get(article['sourceUrl'], {})
        try:
            elapsed = (now - datetime.datetime.fromisoformat(cached.get('checkedAt', ''))).total_seconds()
        except (ValueError, TypeError):
            elapsed = float('inf')
        if (cached.get('text') and elapsed < 86400) or (not cached.get('text') and elapsed < 21600):
            continue
        pending.append(article)
        if len(pending) >= limit:
            break
    def load(article):
        url = article['sourceUrl']
        try:
            raw = fetcher(url)
            if isinstance(raw, bytes):
                raw = raw.decode('utf-8', errors='replace')
            body = extract_article(raw)
        except Exception:
            body = ''
        return url, {'text': body, 'lang': 'az', 'source': article.get('source', ''), 'checkedAt': now.isoformat()}
    with ThreadPoolExecutor(max_workers=6) as pool:
        output.update(pool.map(load, pending))
    # Follow current feed order, cap storage; only audio data, no article-text HTML page.
    kept = {a['sourceUrl']: output[a['sourceUrl']] for a in relevant[:400] if a['sourceUrl'] in output}
    tmp = path.with_name(f'.{path.name}.{os.getpid()}.tmp')
    tmp.write_text(json.dumps({'updatedAt': now.isoformat(), 'articles': kept}, ensure_ascii=False, separators=(',', ':')), encoding='utf-8')
    os.replace(tmp, path)
