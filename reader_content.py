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
    return re.sub(r'\s+', ' ', html.unescape(html.unescape(re.sub(r'<[^>]+>', ' ', text or '')))).strip()


# Xəbərin altındakı lazımsız hissələr (sahib, 2026-11-08: «xəbərin altındakı lazımsız şeyləri də oxuyur»); .github/ses-worker/worker.js-də eynisi.
# JUNK: paylaşım/abunə çağırışları, hüquq qeydləri, ödənişli xəbər yazısı, xəta səhifəsi. STOP: «Oxşar xəbərlər»dən sonra heç nə.
# Azərbaycan hərfi olmayan abzas (ingiliscə xəta səhifəsi) və abzas rejimində durğu işarəsiz qısa sətir (oxşar xəbər başlığı) oxunmur.
JUNK = re.compile(r'sosial şəbəkələrdə paylaş|xəbər (xoşunuza gəldi|maraqlı gəlib)|kanalımız(da|a)? (izləy|abunə)|abunə olun|ctrl\s*\+\s*enter|mətndə (səhv|xəta)|qeydiyyatdan keçin|ödənişli (xəbər|video|foto)|bizi (facebook|[iİ]nstagram|telegram|whatsapp|youtube|tiktok)|xəbəri paylaş|©|bütün (müəllif )?hüquqlar|hüquqları qorunur|[iİ]stinad (mütləqdir|edilməlidir|vacibdir|zəruridir)|(materiallar(ın|dan)|məlumatdan) [iİ]stifadə|cloudflare ray id|[iİ]zləyin @|^(müəllif|foto|video|mənbə|reklam)\s*:', re.I)
STOP = re.compile(r'^((oxşar|digər|əlaqəli|son) xəbərlər|mövzu(ya aid| ilə bağlı)|ən çox oxunan|xəbər lenti|bölmənin digər)( xəbərləri)?\s*:?$', re.I)
AZ = re.compile(r'[əğışçöüƏĞŞÇÖÜİ]')


def tidy(parts, paragraphs=False):
    out = []
    for p in parts:
        p = re.sub(r'\s+', ' ', re.sub(r'\((unikal|eksklüziv)\)', ' ', re.sub(r'\{\{[^}]*\}\}', ' ', p), flags=re.I)).strip()
        if not p:
            continue
        if STOP.search(p):
            break
        if JUNK.search(p) or not AZ.search(p):
            continue
        if paragraphs and len(p) < 220 and not re.search(r'[.!?…]["”»’]?\s', p) and not re.search(r'[.!?:;"”»)’\']$', re.sub(r'(\.\.\.|…)$', '', p)):
            continue
        out.append(p)
    return out


def sentences(text):
    return ' '.join(tidy(re.split(r'(?<=[.!?…])\s+(?=[A-ZÇƏĞİÖŞÜ"“«])', text)))


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
        scoped = parent[1] or tag == 'article' or attrs.get('itemprop') == 'articleBody' or attrs.get('id') == 'font_size' or bool(re.search(r'(?:article|news|entry|post|detail)[-_ ](?:body|content|text|desc)|fullstory|full-post-article|\btext-one\b|\bzoomtext\b|\bnews-detail\b', marker, re.I))  # news-detail: Oxu24.com (2026-11-09)
        blocked = parent[2] or tag in ('nav', 'aside', 'footer', 'header', 'h1', 'script', 'style', 'form') or bool(re.search(r'related|recommend|advert|comment|social|paywall', marker, re.I))
        if tag not in ('br', 'img', 'hr', 'meta', 'link', 'input', 'source', 'wbr'):
            self.stack.append((tag, scoped, blocked))
        if tag == 'p' and scoped and not blocked and not re.search(r'title|info|caption|date|share|foot|copyright|author|subscribe|banner', attrs.get('class', ''), re.I):
            self.paragraph = []

    def handle_data(self, data):
        if self.stack and self.stack[-1][1] and not self.stack[-1][2]:
            self.fragments.append(data)
        if self.paragraph is not None and self.stack and not self.stack[-1][2]:
            self.paragraph.append(data)

    def handle_endtag(self, tag):
        if tag == 'p' and self.paragraph is not None:
            text = clean(' '.join(self.paragraph))
            if text:  # qısa sətir də saxlanır: «Oxşar xəbərlər» başlığı tidy-də dayanma nöqtəsidir; uzunluq sonra yoxlanır
                self.rows.append(text)
            self.paragraph = None
        for i in range(len(self.stack) - 1, -1, -1):
            if self.stack[i][0] == tag:
                self.stack = self.stack[:i]
                break


# Ümumi yol (sahib, 2026-11-12: «dinləməni tam düzəlt hər bir saytda»): mətn blokunun sinif adı tanınmayan saytlar (Teleqraf,
# Reyting, Ordu.az, DSMF, icra hakimiyyətləri, Aia.az …) yalnız başlıqla oxunurdu. Səhifədə ən çox nəsr (cümlə) olan blok tapılır:
# blokun öz sətirləri (<br> ilə ayrılmış) və birbaşa içindəki abzaslar. Səhifənin öz təsviri (og:description) olan blok önə keçir.
VOID = frozenset('br img hr meta link input source wbr area base col embed track param'.split())
INLINE = frozenset('a b strong em i u span font small sup sub mark abbr time label s del ins cite q code big strike nobr'.split())
SKIP = frozenset('nav aside footer header script style form noscript button select textarea iframe svg figcaption h1 h2 h3 h4 h5 h6 title head'.split())
SKIP_CLASS = re.compile(r'related|recommend|advert|comment|social|paywall|share|breadcrumb|sidebar|cookie|popup|modal|(?:^|[\s_-])(?:tags?|teq|menu|footer|banner|widget|date|time|tarix|author|views?|counter)(?:$|[\s_-])', re.I)
PROSE = re.compile(r'[.!?…]["”»’)]?(\s|$)')
STAMP = re.compile(r'^\s*(\d{1,2}[:.]\d{2}\b|\d{1,2}[./-]\d{1,2}[./-]\d{2,4}\b|\d{1,2}\s+(yanvar|fevral|mart|aprel|may|iyun|iyul|avqust|sentyabr|oktyabr|noyabr|dekabr)\s+(\d{4}\s+)?\d{1,2}:\d{2}\b)', re.I)  # «17:40 Başlıq …»: xəbər lenti sətri, mətn deyil
META = re.compile(r'^\s*(teqlər|etiketlər|açar sözlər|mənbə|müəllif|foto|oxunub|baxış(lar)?( sayı)?|tarix|bölmə|şriftin ölçüsü)\s*:', re.I)


class DenseBlocks(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.root = {'buf': [], 'own': [], 'seq': []}
        self.stack = [('', False, self.root)]
        self.found = []  # (nəsr uzunluğu, sətirlər)

    def flush(self, node):
        text = clean(' '.join(node['buf']))
        node['buf'] = []
        if text:
            node['own'].append(text)
            node['seq'].append(text)

    def close(self, node):
        self.flush(node)
        prose = sum(len(p) for p in node['seq'] if len(p) >= 60 and AZ.search(p) and PROSE.search(p) and not STAMP.search(p))
        if prose >= 100:
            self.found.append((prose, node['seq']))

    def handle_starttag(self, tag, attrs):
        if tag in VOID:
            if tag == 'br':
                self.flush(self.stack[-1][2])
            return
        attrs = dict(attrs)
        _, blocked, node = self.stack[-1]
        blocked = blocked or tag in SKIP or bool(SKIP_CLASS.search((attrs.get('class') or '') + ' ' + (attrs.get('id') or '')))
        if tag not in INLINE:
            self.flush(node)
            node = {'buf': [], 'own': [], 'seq': [], 'up': node}
        self.stack.append((tag, blocked, node))

    def handle_data(self, data):
        if not self.stack[-1][1]:
            self.stack[-1][2]['buf'].append(data)

    def handle_endtag(self, tag):
        for i in range(len(self.stack) - 1, 0, -1):
            if self.stack[i][0] == tag:
                gone, self.stack = self.stack[i:], self.stack[:i]
                for t, _, node in reversed(gone):
                    if t not in INLINE:
                        self.close(node)
                        node['up']['seq'].extend(node['own'])  # valideyn blok yalnız birbaşa abzasları görür
                break

    def finish(self):
        for t, _, node in reversed(self.stack[1:]):
            if t not in INLINE:
                self.close(node)
                node['up']['seq'].extend(node['own'])
        self.close(self.root)


def dense_text(raw):
    """Səhifədə ən çox nəsr olan blokun mətni (sinif adından asılı deyil)."""
    parser = DenseBlocks()
    try:
        parser.feed(raw)
        parser.finish()
    except Exception:
        return ''
    m = re.search(r'<meta\b[^>]*?(?:property|name)=["\'](?:og:)?description["\'][^>]*?content=["\']([^"\']{40,})', raw, re.I) or \
        re.search(r'<meta\b[^>]*?content=["\']([^"\']{40,})["\'][^>]*?(?:property|name)=["\'](?:og:)?description["\']', raw, re.I)
    key = re.sub(r'\W+', '', clean(m.group(1)))[:40].lower() if m else ''
    # Təsvir başlığın özüdürsə (Naxçıvan TV) mətni göstərmir: «çox oxunan» siyahısındakı başlıq məqalə sayılmasın.
    head = re.search(r'<title\b[^>]*>(.*?)</title>', raw, re.I | re.S)
    if key and head and re.sub(r'\W+', '', clean(head.group(1))).lower().startswith(key):
        key = ''
    best, top = [], 0
    for prose, seq in parser.found:
        hit = bool(key and key in re.sub(r'\W+', '', ' '.join(seq)).lower())
        if prose < 200 and not hit:  # qısa xəbər (2–3 cümlə) yalnız səhifənin öz təsviri ilə üst-üstə düşəndə
            continue
        score = prose + (10 ** 6 if hit else 0)  # təsviri olan blok həmişə öndədir, aralarında ən çox nəsr olan
        if score > top:
            best, top = seq, score
    rows = [row for row in tidy([p for p in dict.fromkeys(best) if not (META.search(p) and len(p) < 200) and not STAMP.search(p)], paragraphs=True) if len(row) >= 30]
    return sentences(' '.join(rows))


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
        text = sentences(clean(node.get('articleBody'))) if isinstance(node.get('articleBody'), str) else ''
        if 200 <= len(text) <= 24000:
            return text
    parser = ArticleParagraphs()
    parser.feed(raw)
    rows = [row for row in tidy(dict.fromkeys(parser.rows), paragraphs=True) if len(row) >= 30]
    text = sentences(' '.join(rows))
    if len(rows) >= 2 and 200 <= len(text) <= 24000:
        return text
    # Əvvəl burada blokun bütün mətni (tarix, baxış sayı, «Google-da izləyin», oxşar xəbərlərin başlıqları ilə birlikdə) götürülürdü:
    # video səhifəsində səs rəqəm və tarix oxuyurdu (sahib, 2026-11-12). İndi yalnız nəsr bloku; yoxdursa mətn boşdur (xülasə oxunur).
    text = dense_text(raw)
    return text if 100 <= len(text) <= 24000 else ''


def feed_article(xml, url):
    """Mənbənin öz RSS lentindəki tam mətn (content:encoded, yandex:full-text): səhifəsi serverimizə verilməyən mənbə (Report) üçün."""
    def norm(u):
        return re.sub(r'^https?://(www\.)?', '', html.unescape(re.sub(r'<!\[CDATA\[|\]\]>', '', u or '')).strip()).rstrip('/')
    want = norm(url)
    for item in re.split(r'<item\b[^>]*>', xml or '')[1:]:
        link = re.search(r'<link>(.*?)</link>', item, re.S)
        if not link or norm(link.group(1)) != want:
            continue
        m = re.search(r'<(content:encoded|yandex:full-text|turbo:content)\b[^>]*>(.*?)</\1>', item, re.S)
        if not m:
            return ''
        body = html.unescape(m.group(2)) if '<![CDATA[' not in m.group(2) else re.sub(r'<!\[CDATA\[|\]\]>', '', m.group(2))
        parts = [clean(p) for p in re.split(r'</p\s*>|<br\s*/?>|</div\s*>', re.sub(r'<(script|style|figure)\b.*?</\1>', ' ', body, flags=re.S | re.I), flags=re.I)]
        text = sentences(' '.join(row for row in tidy(dict.fromkeys(parts), paragraphs=True) if len(row) >= 30))
        return text if 100 <= len(text) <= 24000 else ''
    return ''


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
