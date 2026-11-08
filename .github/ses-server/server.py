#!/usr/bin/env python3
"""8ULDUZ «Dinlə» səs serveri — SARA (Azərbaycan dili, açıq model), öz Hetzner serverimizdə.

Sahib, 2026-11-08: «anında istəyirəm», «pullu heç nə olmasın», səs seçimi «sara».
«Dinlə» basılan anda: xəbərin TAM mətni mənbə səhifəsindən götürülür (reader_content.extract_article; ödənişli xəbər
götürülmür), SARA ilə cümlə-cümlə səsləndirilir və mp3 axını kimi dərhal göndərilir — ilk cümlə ~1 saniyəyə çalır. Hazır
səs diskdə saxlanır (KEEP_DAYS), eyni xəbəri növbəti dinləyən dərhal alır. Arxa planda saytın dəqiqəlik lentindəki yeni
xəbərlər əvvəlcədən səsləndirilir; dinləyici gələndə o iş ona yol verir. Mətnin özü heç yerdə yayımlanmır, yalnız səs.
Microsoft-dan, pullu xidmətdən asılılıq yoxdur. Quraşdırma: install.sh.

GET /dinle?u=<mənbə ünvanı>&t=<başlıq>&s=<mənbə adı>  → audio/mpeg (yalnız 8ulduz.az səhifəsindən gələn sorğu)
GET /saglam                                          → «ok» (yoxlama)
"""
import hashlib
import json
import os
import re
import subprocess
import sys
import threading
import time
import urllib.parse
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(1, os.path.dirname(os.path.dirname(HERE)))  # repodan işə salınanda reader_content.py kökdədir
from az_text import phrases  # noqa: E402
from reader_content import extract_article  # noqa: E402

PORT = int(os.environ.get("SES_PORT", "8790"))
CACHE = os.environ.get("SES_CACHE", os.path.join(HERE, "cache"))
MODEL = os.environ.get("SES_MODEL", "BHOSAI/SARA_TTS")
KEEP_DAYS, MAX_CHARS, BITRATE = 3, 6000, "48k"
SITE = "https://8ulduz.az/"
LIVE = "https://raw.githubusercontent.com/8ulduz/8ulduz/live/m/"
ALLOWED_REF = re.compile(r"^https://(?:www\.)?8ulduz\.az(?:/|$)")
UA = "Mozilla/5.0 (Linux; Android 14) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0 Mobile Safari/537.36 8ulduz-dinle"

os.makedirs(CACHE, exist_ok=True)
_model = _tok = None
_model_lock = threading.Lock()      # model bir anda bir hissə səsləndirir
_listeners = 0                      # canlı dinləyici varsa arxa plan işi gözləyir
_listeners_lock = threading.Lock()
_inflight = {}                      # eyni xəbər eyni anda iki dəfə hazırlanmasın


def model():
    global _model, _tok
    if _model is None:
        import torch
        from transformers import AutoTokenizer, VitsModel
        torch.set_num_threads(max(1, os.cpu_count() or 1))
        _tok, _model = AutoTokenizer.from_pretrained(MODEL), VitsModel.from_pretrained(MODEL).eval()
    return _tok, _model


def synth(text, background=False):
    """Bir hissə → 16 bit PCM baytları. Arxa plan işi hər hissədən əvvəl canlı dinləyiciyə yol verir."""
    import numpy as np
    import torch
    tok, m = model()
    while background and _listeners:
        time.sleep(0.05)
    with _model_lock, torch.no_grad():
        wave = m(**tok(text, return_tensors="pt")).waveform[0].numpy()
    return (np.clip(wave, -1, 1) * 32767).astype("<i2").tobytes()


def silence(seconds):
    return b"\x00\x00" * int(model()[1].config.sampling_rate * seconds)


def fetch(url, timeout=12, limit=3_000_000):
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "text/html,application/json,*/*"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read(limit).decode("utf-8", errors="replace")


def clip(text, limit=MAX_CHARS):
    text = re.sub(r"\s+", " ", text or "").strip()
    if len(text) <= limit:
        return text
    cut = text[:limit]
    end = max(cut.rfind(". "), cut.rfind("! "), cut.rfind("? "))
    return cut[: end + 1] if end > limit // 2 else cut


def script(title, source, body, summary=""):
    """Oxunan mətn: başlıq, «<mənbə> xəbər verir», tam mətn (alınmayıbsa saytdakı xülasə)."""
    title = re.sub(r"[.!?…\s]+$", "", re.sub(r"\s+", " ", title or "").strip())
    rest = clip(body or re.sub(r"<[^>]+>", " ", summary or ""))
    if title and rest.startswith(title):
        rest = rest[len(title):].lstrip(" .")
    return " ".join(x for x in [title + "." if title else "", f"{source} xəbər verir." if source else "", rest] if x)


def key_of(url):
    return hashlib.sha1(url.encode()).hexdigest()[:20]


def cached(url):
    p = os.path.join(CACHE, key_of(url) + ".mp3")
    return p if os.path.exists(p) and os.path.getsize(p) > 2000 else None


def article_text(url, title, source, summary=""):
    try:
        body = extract_article(fetch(url))
    except Exception:
        body = ""
    return script(title, source, body, summary)


def produce(url, text, sink=None, background=False):
    """Mətni səsləndirir; mp3 baytları axınla sink-ə (dinləyici) verilir və sonda keşə yazılır."""
    tok, m = model()
    sr = m.config.sampling_rate
    enc = subprocess.Popen(["ffmpeg", "-loglevel", "error", "-f", "s16le", "-ar", str(sr), "-ac", "1", "-i", "pipe:0",
                            "-b:a", BITRATE, "-f", "mp3", "pipe:1"], stdin=subprocess.PIPE, stdout=subprocess.PIPE)
    chunks, failed = [], []

    def pump():
        while True:
            b = enc.stdout.read(4096)
            if not b:
                break
            chunks.append(b)
            if sink and not failed:
                try:
                    sink(b)
                except Exception:
                    failed.append(1)   # dinləyici getdi; səs yenə hazırlanıb keşə yazılır
    reader = threading.Thread(target=pump, daemon=True)
    reader.start()
    try:
        for said, pause in phrases(text):
            enc.stdin.write(synth(said, background) + silence(pause))
            enc.stdin.flush()
    finally:
        enc.stdin.close()
        enc.wait()
        reader.join()
    data = b"".join(chunks)
    if len(data) > 2000:
        tmp = os.path.join(CACHE, key_of(url) + ".tmp")
        with open(tmp, "wb") as f:
            f.write(data)
        os.replace(tmp, os.path.join(CACHE, key_of(url) + ".mp3"))
    return data


class Handler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"
    server_version = "8ulduz-ses"

    def log_message(self, fmt, *args):
        pass

    def _headers(self, code, ctype, extra=None):
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Access-Control-Allow-Origin", "https://8ulduz.az")
        self.send_header("Cache-Control", "public, max-age=86400" if code in (200, 206) else "no-store")
        for k, v in (extra or {}).items():
            self.send_header(k, v)
        self.end_headers()

    def _plain(self, code, text):
        body = text.encode()
        self._headers(code, "text/plain; charset=utf-8", {"Content-Length": str(len(body))})
        self.wfile.write(body)

    def _file(self, path):
        """Hazır səs: Range dəstəyi ilə (iPhone Safari səsi hissə-hissə istəyir)."""
        size = os.path.getsize(path)
        m = re.match(r"bytes=(\d*)-(\d*)", self.headers.get("Range") or "")
        start, end = 0, size - 1
        if m and (m.group(1) or m.group(2)):
            start = int(m.group(1)) if m.group(1) else max(0, size - int(m.group(2)))
            end = min(size - 1, int(m.group(2))) if m.group(1) and m.group(2) else size - 1
        extra = {"Content-Length": str(end - start + 1), "Accept-Ranges": "bytes"}
        if m:
            extra["Content-Range"] = f"bytes {start}-{end}/{size}"
        self._headers(206 if m else 200, "audio/mpeg", extra)
        with open(path, "rb") as f:
            f.seek(start)
            self.wfile.write(f.read(end - start + 1))

    def do_GET(self):
        global _listeners
        url = urllib.parse.urlparse(self.path)
        if url.path == "/saglam":
            return self._plain(200, "ok")
        if url.path != "/dinle":
            return self._plain(404, "yoxdur")
        if not ALLOWED_REF.match(self.headers.get("Origin") or self.headers.get("Referer") or ""):
            return self._plain(403, "yalnız 8ulduz.az")
        q = urllib.parse.parse_qs(url.query)
        src = (q.get("u") or [""])[0]
        p = urllib.parse.urlparse(src)
        if p.scheme != "https" or not p.hostname or re.match(r"^[\d.]+$|^\[|(^|\.)(localhost|internal|local)$", p.hostname):
            return self._plain(400, "ünvan")
        path = cached(src)
        if path:
            return self._file(path)
        title, source = (q.get("t") or [""])[0][:300], (q.get("s") or [""])[0][:80]
        # Eyni xəbər artıq hazırlanırsa (arxa plan və ya başqa dinləyici) onun bitməsini gözlə, sonra fayl ver.
        ev = _inflight.get(src)
        if ev:
            ev.wait(120)
            path = cached(src)
            return self._file(path) if path else self._plain(503, "sonra")
        ev = _inflight[src] = threading.Event()
        with _listeners_lock:
            _listeners += 1
        try:
            text = article_text(src, title, source)
            if not text:
                return self._plain(422, "mətn yoxdur")
            self._headers(200, "audio/mpeg", {"Transfer-Encoding": "chunked"})

            def sink(b):
                self.wfile.write(f"{len(b):X}\r\n".encode() + b + b"\r\n")
                self.wfile.flush()
            produce(src, text, sink)
            try:
                self.wfile.write(b"0\r\n\r\n")
            except Exception:
                pass
        finally:
            with _listeners_lock:
                _listeners -= 1
            ev.set()
            _inflight.pop(src, None)


def feed_rows():
    """Saytın Azərbaycan xəbərləri: dəqiqəlik canlı lent + əsas lent (ikisi də saytda qaydadan keçib)."""
    rows, now = [], time.time()
    slot = int(now - 45) // 60
    for minute in (slot, slot - 1, slot - 2):
        try:
            rows = json.loads(fetch(f"{LIVE}{minute}/latest.az.json", 15)).get("articles") or []
            break
        except Exception:
            continue
    try:
        rows += json.loads(fetch(f"{SITE}data/news.json?t={int(now)}", 30)).get("articles") or []
    except Exception:
        pass
    seen, out = set(), []
    for a in rows:
        if a.get("id") in seen or (a.get("lang") or "az") != "az" or not str(a.get("sourceUrl", "")).startswith("https://"):
            continue
        seen.add(a.get("id"))
        out.append(a)
    return sorted(out, key=lambda a: str(a.get("publishedAt") or ""), reverse=True)


def prefetch_loop():
    """Yeni xəbərlər əvvəlcədən səslənir (ən yenisi birinci); dinləyici varsa gözləyir."""
    while True:
        try:
            for a in feed_rows()[:300]:
                src = a["sourceUrl"]
                if cached(src) or src in _inflight:
                    continue
                while _listeners:
                    time.sleep(1)
                ev = _inflight[src] = threading.Event()
                try:
                    text = article_text(src, a.get("title", ""), a.get("source", ""), a.get("summary", ""))
                    if text:
                        produce(src, text, background=True)
                finally:
                    ev.set()
                    _inflight.pop(src, None)
        except Exception as e:
            print("prefetch:", type(e).__name__, e, flush=True)
        cleanup()
        time.sleep(30)


def cleanup():
    limit = time.time() - KEEP_DAYS * 86400
    for name in os.listdir(CACHE):
        p = os.path.join(CACHE, name)
        try:
            if os.path.getmtime(p) < limit:
                os.remove(p)
        except OSError:
            pass


def main():
    model()   # model açılışda yüklənir: ilk dinləyici gözləməsin
    if os.environ.get("SES_PREFETCH", "1") == "1":
        threading.Thread(target=prefetch_loop, daemon=True).start()
    print(f"8ulduz ses: 127.0.0.1:{PORT}, keş {CACHE}", flush=True)
    ThreadingHTTPServer((os.environ.get("SES_HOST", "127.0.0.1"), PORT), Handler).serve_forever()


if __name__ == "__main__":
    main()
