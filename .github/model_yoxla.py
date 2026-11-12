"""Müvəqqəti sınaq: GitHub Models iş axınının öz icazəsi ilə açılırmı və Azərbaycan dilində xəbər mətnini necə yazır.
Sayta heç nə yazmır. Açar çap olunmur."""
import html
import json
import os
import re
import time
import urllib.error
import urllib.request

TOKEN = os.environ.get("GITHUB_TOKEN", "")
API = "https://models.github.ai"
HEAD = {"Authorization": "Bearer " + TOKEN, "Accept": "application/vnd.github+json", "X-GitHub-Api-Version": "2022-11-28",
        "Content-Type": "application/json", "User-Agent": "model-check"}
UA = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"
PAGES = (
    ("voyager", "NASA, Nov 10, 2026", "https://www.nasa.gov/news-release/nasa-invites-media-public-to-join-voyager-1-one-light-day-activities/"),
    ("dunes", "USGS, Nov 10, 2026", "https://www.usgs.gov/programs/cmhrp/news/california-has-lost-60-its-coastal-dunes-1800s-new-study-finds"),
)
EXACT = ("openai/gpt-4.1", "openai/gpt-4o", "openai/gpt-5", "openai/gpt-5-chat", "openai/gpt-4.1-mini", "openai/gpt-5-mini", "openai/gpt-4o-mini")
OTHERS = ("meta", "mistral-ai", "deepseek", "xai", "cohere", "microsoft")
HINTS = ("large", "maverick", "70b", "v3", "grok-3", "command-a", "medium")
SYSTEM = """You are a news editor at an Azerbaijani news website. From the SOURCE text (English) write a short news item in Azerbaijani (Latin script) for general readers.
Rules:
- Use ONLY facts stated in the SOURCE. Do not add background, causes, forecasts or opinions.
- Keep every number exactly as in the SOURCE (when both miles and kilometres are given, use the metric value; write decimals with a comma: 25,9). Do not convert units and do not round.
- Neutral news style. Reported events take the news perfect form (edib, olub, açıqlayıb). No exclamation marks, no clickbait, no question in the title.
- title: at most 90 characters, starts with the main fact, sentence case.
- lead: 1-2 sentences with the key fact and who reported it.
- body: 2-3 short paragraphs (each 1-3 sentences) with the most interesting details. No direct quotes.
- Proper names keep their original Latin spelling (Voyager 1, Alba Mons); countries, planets and well-known organisations take their established Azerbaijani names (ABŞ, Mars, NASA, Avropa Kosmik Agentliyi).
- Never use relative day words (bu gün, dünən, sabah); write dates as in the SOURCE (noyabrın 18-də).
- maraq: 1-5, how interesting this is for a general reader in Azerbaijan (5 = most people would want to read it).
Return ONLY a JSON object: {"title": str, "lead": str, "body": [str], "maraq": int}."""


def call(method, url, body=None, headers=None, timeout=120):
    data = json.dumps(body).encode("utf-8") if body is not None else None
    req = urllib.request.Request(url, data=data, headers=headers or HEAD, method=method)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.status, dict(r.headers), r.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as e:
        return e.code, dict(e.headers), e.read().decode("utf-8", "replace")
    except Exception as e:  # noqa: BLE001
        return 0, {}, str(e)


def page_text(url):
    code, _, raw = call("GET", url, headers={"User-Agent": UA, "Accept": "text/html,*/*"}, timeout=30)
    if code != 200:
        return "", code
    raw = re.sub(r"(?is)<(script|style|noscript|svg)\b.*?</\1\s*>", " ", raw)
    raw = re.sub(r"(?i)</(p|h[1-6]|li|div|figcaption|section|article)>", "\n", raw)
    raw = re.sub(r"(?s)<[^>]+>", " ", raw)
    lines = [" ".join(html.unescape(l).split()) for l in raw.split("\n")]
    keep = [l for l in lines if len(l) > 90 and "cookies" not in l.lower() and "Federal government websites" not in l and "https:// ensures" not in l]
    return "\n".join(keep)[:3200], code


def limits(headers):
    return " ".join("%s=%s" % (k, v) for k, v in sorted(headers.items()) if "ratelimit" in k.lower())


def ask(model, source):
    body = {"model": model, "messages": [{"role": "system", "content": SYSTEM}, {"role": "user", "content": source}],
            "temperature": 0.2, "max_tokens": 1100}
    t0 = time.time()
    code, head, raw = call("POST", API + "/inference/chat/completions", body)
    if code == 400:
        body.pop("temperature", None)
        body["max_completion_tokens"] = body.pop("max_tokens", 1100) + 2000
        code, head, raw = call("POST", API + "/inference/chat/completions", body)
    took = time.time() - t0
    text = raw
    try:
        doc = json.loads(raw)
        text = doc["choices"][0]["message"]["content"]
        usage = doc.get("usage") or {}
        text += "\n   [tokens: giriş %s, çıxış %s]" % (usage.get("prompt_tokens"), usage.get("completion_tokens"))
    except Exception:  # noqa: BLE001
        text = raw[:500]
    return code, took, limits(head), text


def main():
    print("açar var:", bool(TOKEN))
    print("== 1. Kataloq")
    code, head, raw = call("GET", API + "/catalog/models")
    print("HTTP", code, limits(head))
    ids = []
    try:
        for m in json.loads(raw):
            ids.append(m.get("id", ""))
            lim = m.get("limits") or {}
            print("  %-46s %-10s giriş %-8s çıxış %-7s %s" % (m.get("id"), m.get("rate_limit_tier"), lim.get("max_input_tokens"),
                                                          lim.get("max_output_tokens"), ",".join(m.get("supported_output_modalities") or [])))
    except Exception as e:  # noqa: BLE001
        print("kataloq oxunmadı:", str(e)[:200], raw[:400])
    picked = [i for i in EXACT if i in ids][:4]
    for pub in OTHERS:
        own = [i for i in ids if i.startswith(pub + "/") and "embed" not in i.lower()]
        best = [i for i in own if any(h in i.lower() for h in HINTS)] or own
        if best:
            picked.append(best[0])
    if not picked:
        picked = list(EXACT[:2])
    print("seçilən modellər:", picked)
    print()
    print("== 2. Mənbə mətnləri")
    sources = []
    for name, by, url in PAGES:
        text, code = page_text(url)
        print("%s: HTTP %s, %d hərf" % (name, code, len(text)))
        if text:
            sources.append((name, "SOURCE (publisher and date: %s):\n%s" % (by, text)))
    print()
    print("== 3. Yazı")
    for model in picked:
        for name, source in sources:
            code, took, lim, text = ask(model, source)
            print("--- %s | %s | HTTP %s | %.1f s | %s" % (model, name, code, took, lim))
            print(text)
            print()
            time.sleep(7)


if __name__ == "__main__":
    main()
