"""Müvəqqəti sınaq: açıq xarici lentlər və açarsız tərcümə GitHub-dan açılırmı. Sayta heç nə yazmır."""
import json
import re
import time
import urllib.parse

import updater

FEEDS = (
    ("nasa", "https://www.nasa.gov/news-release/feed/"),
    ("nasa-elm", "https://science.nasa.gov/feed/"),
    ("jpl", "https://www.jpl.nasa.gov/feeds/news"),
    ("yer", "https://earthobservatory.nasa.gov/feeds/image-of-the-day.rss"),
    ("eso", "https://www.eso.org/public/news/feed/"),
    ("webb", "https://esawebb.org/news/feed/"),
    ("hubble", "https://esahubble.org/news/feed/"),
    ("esa", "https://www.esa.int/rssfeed/TopNews"),
    ("noirlab", "https://noirlab.edu/public/news/feed/"),
    ("owid", "https://ourworldindata.org/atom-data-insights.xml"),
    ("usgs", "https://www.usgs.gov/news/all/feed"),
    ("fda", "https://www.fda.gov/about-fda/contact-fda/stay-informed/rss-feeds/press-releases/rss.xml"),
    ("noaa", "https://www.noaa.gov/news-release/feed"),
    ("nobel", "https://www.nobelprize.org/feed/"),
)
TR = "https://translate.googleapis.com/translate_a/single?client=gtx&sl={}&tl={}&dt=t&q={}"
TAG = re.compile(r"<[^>]+>")
SPLIT = re.compile(r"<item[\s>]|<entry[\s>]")
TITLE = re.compile(r"<title[^>]*>(.*?)</title>", re.S)
DESC = (re.compile(r"<description[^>]*>(.*?)</description>", re.S), re.compile(r"<summary[^>]*>(.*?)</summary>", re.S),
        re.compile(r"<content[^>]*>(.*?)</content>", re.S))


def clean(s):
    s = s.replace("<![CDATA[", "").replace("]]>", "")
    for a, b in (("&lt;", "<"), ("&gt;", ">")):
        s = s.replace(a, b)
    s = TAG.sub(" ", s)
    for a, b in (("&amp;", "&"), ("&#8217;", "'"), ("&rsquo;", "'"), ("&nbsp;", " "), ("&quot;", '"'), ("&#8211;", "-")):
        s = s.replace(a, b)
    return " ".join(s.split())


def first_item(xml):
    parts = SPLIT.split(xml)
    if len(parts) < 2:
        return "", ""
    it = parts[1]
    t = TITLE.search(it)
    d = None
    for rx in DESC:
        d = rx.search(it)
        if d:
            break
    return (clean(t.group(1)) if t else ""), (clean(d.group(1))[:600] if d else "")


def translate(text, sl, tl):
    url = TR.format(sl, tl, urllib.parse.quote(text, safe=""))
    raw = updater.fetch(url, timeout=15, headers={"Accept": "application/json"})
    data = json.loads(raw.decode("utf-8"))
    return "".join(p[0] for p in data[0] if p and p[0])


def main():
    samples = []
    print("== 1. Lentlər")
    for name, url in FEEDS:
        t0 = time.time()
        try:
            raw = updater.fetch(url, timeout=20)
            xml = raw.decode("utf-8", "replace")
            title, desc = first_item(xml)
            n = len(SPLIT.split(xml)) - 1
            print("%-9s OK   %7d bayt %3d maddə %.1f s | %s" % (name, len(raw), n, time.time() - t0, title[:90]))
            if title and desc:
                samples.append((name, title, desc))
        except Exception as e:  # noqa: BLE001
            print("%-9s XƏTA %.1f s | %s" % (name, time.time() - t0, str(e)[:120]))
    print()
    print("== 2. Tərcümə (en -> az) və geri (az -> en)")
    ok = bad = 0
    for name, title, desc in samples[:8]:
        text = (title + ". " + desc)[:900]
        try:
            t0 = time.time()
            az = translate(text, "en", "az")
            t1 = time.time()
            time.sleep(1)
            back = translate(az, "az", "en")
            ok += 1
            print("--- %s (%.1f s)" % (name, t1 - t0))
            print("EN:   " + text)
            print("AZ:   " + az)
            print("GERİ: " + back)
        except Exception as e:  # noqa: BLE001
            bad += 1
            print("--- %s XƏTA %s" % (name, str(e)[:160]))
        time.sleep(1)
    print()
    print("tərcümə: %d uğurlu, %d xəta" % (ok, bad))
    print()
    print("== 3. Ardıcıl 40 qısa sorğu (0,5 s fasilə): məhdudiyyət varmı")
    ok = bad = 0
    first_err = ""
    t0 = time.time()
    for i in range(40):
        try:
            out = translate("The telescope found %d new planets around a nearby star." % (i + 2), "en", "az")
            ok += 1
            if i in (0, 39):
                print("  %d: %s" % (i, out))
        except Exception as e:  # noqa: BLE001
            bad += 1
            if not first_err:
                first_err = "%d-ci sorğu: %s" % (i, str(e)[:160])
        time.sleep(0.5)
    print("ardıcıl: %d uğurlu, %d xəta, %.0f s %s" % (ok, bad, time.time() - t0, first_err))


if __name__ == "__main__":
    main()
