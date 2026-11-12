#!/usr/bin/env python3
"""«Dinlə» yoxlaması: hər Azərbaycan mənbəsindən N son xəbər, ses.py ilə eyni sorğu və reader_content.extract_article.
İşlədilmə: python3 olc.py <çıxış qovluğu> [hər mənbədən neçə xəbər]"""
import json
import os
import sys
import time
import urllib.request
from concurrent.futures import ThreadPoolExecutor

sys.path.insert(0, os.getcwd())
from reader_content import extract_article  # noqa: E402

UA = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36 8ulduz-bot"
OUT = sys.argv[1]
N = int(sys.argv[2]) if len(sys.argv) > 2 else 3
os.makedirs(os.path.join(OUT, "raw"), exist_ok=True)


def fetch(url, timeout=12):
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "text/html,application/json,*/*"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read(3_000_000).decode("utf-8", errors="replace")


feed = json.loads(fetch("https://8ulduz.az/data/news.json?t=%d" % time.time(), 30))["articles"]
by = {}
for a in feed:
    rows = [a] + [dict(x, id=a["id"] + "-alt") for x in (a.get("alts") or [])]
    for r in rows:
        if (r.get("lang") or a.get("lang") or "az") != "az" or not str(r.get("sourceUrl", "")).startswith("https://"):
            continue
        by.setdefault(r.get("source") or "?", []).append(r)


def one(item):
    src, rows = item
    out = []
    for k, a in enumerate(rows[:N]):
        rec = {"source": src, "url": a["sourceUrl"], "title": a.get("title", ""), "summary": len(a.get("summary") or "")}
        try:
            raw = fetch(a["sourceUrl"])
            rec["raw"] = len(raw)
            body = extract_article(raw)
            rec["len"] = len(body)
            rec["head"], rec["tail"] = body[:220], body[-160:]
            name = "%s-%d.html" % ("".join(c if c.isalnum() else "_" for c in src), k)
            with open(os.path.join(OUT, "raw", name), "w", encoding="utf-8") as f:
                f.write(raw)
            rec["file"] = name
        except Exception as e:
            rec["err"] = "%s %s" % (type(e).__name__, str(e)[:100])
        out.append(rec)
        time.sleep(0.5)
    return out


with ThreadPoolExecutor(max_workers=8) as pool:
    res = [r for rows in pool.map(one, sorted(by.items())) for r in rows]
with open(os.path.join(OUT, "netice.json"), "w", encoding="utf-8") as f:
    json.dump(res, f, ensure_ascii=False, indent=1)
print("mənbə", len(by), "xəbər", len(res), "xəta", sum(1 for r in res if "err" in r), "mətnsiz", sum(1 for r in res if r.get("len") == 0))
