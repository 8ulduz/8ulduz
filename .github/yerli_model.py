"""Müvəqqəti sınaq: açıq model GitHub maşınının özündə (kənar xidmətsiz, açarsız) Azərbaycan dilində xəbər mətnini
necə yazır və nə qədər vaxt aparır. Sayta heç nə yazmır."""
import html
import os
import re
import shutil
import time
import urllib.request

from llama_cpp import Llama

HF = "https://huggingface.co/ggml-org/{0}-GGUF/resolve/main/{0}-Q4_K_M.gguf"
MODELS = ("gemma-3-4b-it", "gemma-3-12b-it")
UA = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"
PAGES = (
    ("voyager", "NASA, Nov 10, 2026", "https://www.nasa.gov/news-release/nasa-invites-media-public-to-join-voyager-1-one-light-day-activities/"),
    ("dunes", "USGS, Nov 10, 2026", "https://www.usgs.gov/programs/cmhrp/news/california-has-lost-60-its-coastal-dunes-1800s-new-study-finds"),
)
RULES = """You are a news editor at an Azerbaijani news website. From the SOURCE text (English) write a short news item in Azerbaijani (Latin script) for general readers.
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


def page_text(url):
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "text/html,*/*"})
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            raw = r.read().decode("utf-8", "replace")
    except Exception as e:  # noqa: BLE001
        return "", str(e)[:120]
    raw = re.sub(r"(?is)<(script|style|noscript|svg)\b.*?</\1\s*>", " ", raw)
    raw = re.sub(r"(?i)</(p|h[1-6]|li|div|figcaption|section|article)>", "\n", raw)
    raw = re.sub(r"(?s)<[^>]+>", " ", raw)
    lines = [" ".join(html.unescape(l).split()) for l in raw.split("\n")]
    keep = [l for l in lines if len(l) > 90 and "cookies" not in l.lower() and "Federal government websites" not in l and "https:// ensures" not in l]
    return "\n".join(keep)[:3200], "OK"


def download(name):
    path = name + ".gguf"
    req = urllib.request.Request(HF.format(name), headers={"User-Agent": "model-check"})
    with urllib.request.urlopen(req, timeout=60) as r, open(path, "wb") as f:
        shutil.copyfileobj(r, f, 8 * 1024 * 1024)
    return path


def main():
    sources = []
    for name, by, url in PAGES:
        text, note = page_text(url)
        print("%s: %s, %d hərf" % (name, note, len(text)), flush=True)
        if text:
            sources.append((name, "%s\n\nSOURCE (publisher and date: %s):\n%s" % (RULES, by, text)))
    for model in MODELS:
        print(flush=True)
        print("===== MODEL %s" % model, flush=True)
        try:
            t0 = time.time()
            path = download(model)
            print("yükləmə: %.0f s, %.1f GB" % (time.time() - t0, os.path.getsize(path) / 1e9), flush=True)
            t0 = time.time()
            llm = Llama(model_path=path, n_ctx=4096, n_threads=os.cpu_count() or 4, verbose=False)
            print("açılma: %.0f s" % (time.time() - t0), flush=True)
        except Exception as e:  # noqa: BLE001
            print("XƏTA (model): %s" % str(e)[:300], flush=True)
            continue
        for name, prompt in sources:
            t0 = time.time()
            try:
                out = llm.create_chat_completion(messages=[{"role": "user", "content": prompt}], temperature=0.2, max_tokens=800,
                                                 response_format={"type": "json_object"})
                usage = out.get("usage") or {}
                took = time.time() - t0
                print("--- %s | %s | %.0f s | giriş %s token | çıxış %s token (%.1f/s ümumi)" % (
                    model, name, took, usage.get("prompt_tokens"), usage.get("completion_tokens"),
                    (usage.get("completion_tokens") or 0) / took if took else 0), flush=True)
                print(out["choices"][0]["message"]["content"], flush=True)
            except Exception as e:  # noqa: BLE001
                print("--- %s | %s | %.0f s | XƏTA %s" % (model, name, time.time() - t0, str(e)[:300]), flush=True)
            print(flush=True)
        del llm
        os.remove(path)


if __name__ == "__main__":
    main()
