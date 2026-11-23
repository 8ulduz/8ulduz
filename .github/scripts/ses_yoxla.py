#!/usr/bin/env python3
"""SARA səsinin anlaşıqlığını ölçür (sahib, 2026-11-23: «dəfələrlə dinlə… tam normal insan kimi oxunsun»).

Hər mətn bir neçə ayarla səsləndirilir, sonra Whisper (səsdən mətnə) onu «dinləyib» yazır və yazılan gözlənən oxunuşla
müqayisə olunur: WER — səhv eşidilən sözlərin, CER — hərflərin payı. Rəqəm nə qədər kiçikdirsə, səs o qədər aydındır.
Whisper özü də səhv edir, ona görə rəqəmin özü yox, ayarlar arasındakı fərq və tez-tez səhv eşidilən sözlər əhəmiyyətlidir.

İşlədilmə (.github/workflows/ses-yoxla.yml; hər ayar ayrıca paralel işdə, sonda hesabat):
  python3 ses_yoxla.py dinle <korpus.json> <çıxış qovluğu> [köhnə az_text.py]
  python3 ses_yoxla.py hesabat <netice-*.json olan qovluq>
  korpus.json  {"items": ["mətn", …], "numune": [indekslər]} — «numune» hissələri hər ayar üçün bir faylda dinlənir
  VARIANTS     JSON siyahı: [{"ad", "motor": "sara"|"babek", "metn": "yeni"|"kohne", "noise_scale", "noise_scale_duration",
               "speaking_rate", "commas", "tire"}]; babek — saytın «Dinlə» səsi (edge-tts), kohne üçün OLD_SES=köhnə ses.py
  OLD_SES      köhnə .github/scripts/ses.py (Babək üçün indiki mətn yolu: spoken_text)
  ASR_MODEL    Whisper modeli (default large-v3)
Nəticə: <çıxış>/netice-<ad>.json, <ad>/NNN.wav, <ad>-numune.wav; hesabat — markdown (stdout).
"""
import importlib.util
import json
import os
import sys
import time
import wave
from collections import Counter

HERE = os.path.dirname(os.path.abspath(__file__))
SES = os.path.join(os.path.dirname(HERE), "ses-server")
MODEL = os.environ.get("SES_MODEL", "BHOSAI/SARA_TTS")
BABEK = "az-AZ-BabekNeural"
DEFAULT_VARIANTS = [
    {"ad": "kohne", "metn": "kohne"},
    {"ad": "yeni", "metn": "yeni"},
    {"ad": "yeni-vergulsuz", "metn": "yeni", "commas": False},
    {"ad": "yeni-sakit", "metn": "yeni", "noise_scale": 0.45, "noise_scale_duration": 0.6},
    {"ad": "yeni-sakit-yavas", "metn": "yeni", "noise_scale": 0.45, "noise_scale_duration": 0.6, "speaking_rate": 0.92},
]


def load(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def expected_words(new, text):
    """Gözlənən oxunuş (yeni qayda ilə): Whisper-in yazdığı da eyni qaydadan keçir, ona görə «ABŞ» ≡ «a-be-şe»."""
    said = " ".join(s for s, _ in new.phrases(text))
    return said.replace("-", " ").split()


def edits(ref, hyp):
    """Levenshtein məsafəsi və səhvlər: [(növ, gözlənən, eşidilən)], növ S — əvəz, D — itən, I — artıq."""
    n, m = len(ref), len(hyp)
    d = [[0] * (m + 1) for _ in range(n + 1)]
    for i in range(n + 1):
        d[i][0] = i
    for j in range(m + 1):
        d[0][j] = j
    for i in range(1, n + 1):
        for j in range(1, m + 1):
            d[i][j] = min(d[i - 1][j] + 1, d[i][j - 1] + 1, d[i - 1][j - 1] + (ref[i - 1] != hyp[j - 1]))
    ops, i, j = [], n, m
    while i > 0 or j > 0:
        if i > 0 and j > 0 and d[i][j] == d[i - 1][j - 1] + (ref[i - 1] != hyp[j - 1]):
            if ref[i - 1] != hyp[j - 1]:
                ops.append(("S", ref[i - 1], hyp[j - 1]))
            i, j = i - 1, j - 1
        elif i > 0 and d[i][j] == d[i - 1][j] + 1:
            ops.append(("D", ref[i - 1], ""))
            i -= 1
        else:
            ops.append(("I", "", hyp[j - 1]))
            j -= 1
    return d[n][m], ops[::-1]


def synth(tok, model, parts, sr):
    import numpy as np
    import torch
    pcm = []
    for said, pause in parts or [("", 0.3)]:
        if said:
            with torch.no_grad():
                w = model(**tok(said, return_tensors="pt")).waveform[0].numpy()
            pcm.append((np.clip(w, -1, 1) * 32767).astype("<i2").tobytes())
        pcm.append(b"\x00\x00" * int(sr * pause))
    return b"".join(pcm)


def write_wav(path, pcm, sr):
    with wave.open(path, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(sr)
        w.writeframes(pcm)


def babek(text, sr=16000, tries=3):
    """Saytın «Dinlə» səsi (Babək, edge-tts — .github/scripts/ses.py ilə eyni yol) → 16 bit PCM."""
    import asyncio
    import subprocess
    import tempfile
    import edge_tts
    with tempfile.TemporaryDirectory() as d:
        mp3 = os.path.join(d, "s.mp3")
        for attempt in range(tries):
            try:
                asyncio.run(edge_tts.Communicate(text, BABEK).save(mp3))
                break
            except Exception:
                if attempt == tries - 1:
                    raise
                time.sleep(5 * (attempt + 1))
        return subprocess.run(["ffmpeg", "-loglevel", "error", "-i", mp3, "-f", "s16le", "-ac", "1", "-ar", str(sr), "pipe:1"],
                              capture_output=True, check=True).stdout


def main(corpus_path, out, old_path=None):
    import numpy as np
    from faster_whisper import WhisperModel

    new = load(os.path.join(SES, "az_text.py"), "az_text_yeni")
    old = load(old_path, "az_text_kohne") if old_path and os.path.exists(old_path) else None
    old_ses = os.environ.get("OLD_SES")
    old_ses = load(old_ses, "ses_kohne") if old_ses and os.path.exists(old_ses) else None
    with open(corpus_path, encoding="utf-8") as f:
        corpus = json.load(f)
    items, sample = corpus["items"], corpus.get("numune", [])
    variants = json.loads(os.environ.get("VARIANTS") or "null") or DEFAULT_VARIANTS
    variants = [v for v in variants if v.get("metn") != "kohne" or (old_ses if v.get("motor") == "babek" else old)]

    tok = model = None
    sr = 16000
    if any(v.get("motor", "sara") == "sara" for v in variants):
        import torch
        from transformers import AutoTokenizer, VitsModel
        torch.set_num_threads(max(1, os.cpu_count() or 1))
        tok, model = AutoTokenizer.from_pretrained(MODEL), VitsModel.from_pretrained(MODEL).eval()
        sr = model.config.sampling_rate
    base = dict(new.VOICE)   # ayarı verilməyən variant az_text.VOICE ilə oxuyur (video və server kimi)
    asr = WhisperModel(os.environ.get("ASR_MODEL", "large-v3"), device="cpu", compute_type="int8", cpu_threads=os.cpu_count() or 2)
    os.makedirs(out, exist_ok=True)

    results = []
    for v in variants:
        name = v["ad"]
        os.makedirs(os.path.join(out, name), exist_ok=True)
        is_babek = v.get("motor") == "babek"
        if not is_babek:
            for k, default in base.items():
                setattr(model, k, v.get(k, default))
        mod = old if v.get("metn") == "kohne" else new
        rows, t_synth, t_asr, audio = [], 0.0, 0.0, 0.0
        sample_pcm = []
        for i, text in enumerate(items):
            t0 = time.time()
            if is_babek:
                # Babək bütöv mətni alır (durğu və böyük hərf intonasiya üçün qalır): köhnə — ses.py-nin indiki yolu, yeni — az_text.for_voice
                said = old_ses.spoken_text(text) if v.get("metn") == "kohne" else new.for_voice(text, hyphens=v.get("tire", True))
                pcm = babek(said, sr)
            else:
                import torch
                torch.manual_seed(8)
                parts = mod.phrases(text) if mod is old else mod.phrases(text, commas=v.get("commas", False))
                said = " | ".join(s for s, _ in parts)
                pcm = synth(tok, model, parts, sr)
            t_synth += time.time() - t0
            path = os.path.join(out, name, f"{i:03d}.wav")
            write_wav(path, pcm, sr)
            dur = len(pcm) / 2 / sr
            audio += dur
            if i in sample:
                sample_pcm += [pcm, b"\x00\x00" * int(sr * 0.7)]
            t0 = time.time()
            # Səs birbaşa massiv kimi verilir (faylı oxuyan PyAV-ın yeni versiyası faster-whisper ilə uyğun gəlmir).
            pcm16k = np.frombuffer(pcm, dtype="<i2").astype(np.float32) / 32768.0
            if sr != 16000:
                pcm16k = np.interp(np.arange(0, len(pcm16k), sr / 16000), np.arange(len(pcm16k)), pcm16k).astype(np.float32)
            segs, _ = asr.transcribe(pcm16k, language="az", beam_size=5, temperature=0.0, condition_on_previous_text=False,
                                     vad_filter=False, without_timestamps=True)
            heard = " ".join(s.text.strip() for s in segs).strip()
            t_asr += time.time() - t0
            ref, hyp = expected_words(new, text), expected_words(new, heard)
            wd, ops = edits(ref, hyp)
            cd, _ = edits(list("".join(ref)), list("".join(hyp)))
            rows.append({"i": i, "text": text, "said": said, "ref": " ".join(ref), "heard": heard, "hyp": " ".join(hyp),
                         "words": len(ref), "werr": wd, "chars": len("".join(ref)), "cerr": cd, "dur": round(dur, 2),
                         "ops": ops})
            print(f"[{name}] {i:03d} WER {wd}/{len(ref)}  «{heard}»", flush=True)
        if sample_pcm:
            write_wav(os.path.join(out, f"{name}-numune.wav"), b"".join(sample_pcm), sr)
        W = sum(r["werr"] for r in rows) / max(1, sum(r["words"] for r in rows))
        C = sum(r["cerr"] for r in rows) / max(1, sum(r["chars"] for r in rows))
        result = {"variant": v, "wer": round(W, 4), "cer": round(C, 4), "audio_s": round(audio, 1),
                  "synth_s": round(t_synth, 1), "asr_s": round(t_asr, 1), "rows": rows}
        results.append(result)
        with open(os.path.join(out, f"netice-{name}.json"), "w", encoding="utf-8") as f:
            json.dump(result, f, ensure_ascii=False, indent=1)
    print(report(results))


def collect(folder):
    """Paralel işlərin netice-*.json faylları; «kohne» birinci, qalanı ada görə."""
    out = []
    for root, _, files in os.walk(folder):
        for fn in files:
            if fn.startswith("netice-") and fn.endswith(".json"):
                with open(os.path.join(root, fn), encoding="utf-8") as f:
                    out.append(json.load(f))
    return sorted(out, key=lambda r: (r["variant"].get("metn") != "kohne", r["variant"]["ad"]))


def report(results):
    lines = ["### SARA səsinin anlaşıqlığı (Whisper ilə)", "",
             "| Ayar | Söz xətası (WER) | Hərf xətası (CER) | Səs, s | Ayarlar |", "|---|---|---|---|---|"]
    for r in results:
        v = {k: x for k, x in r["variant"].items() if k != "ad"}
        lines.append(f"| {r['variant']['ad']} | {r['wer'] * 100:.1f}% | {r['cer'] * 100:.1f}% | {r['audio_s']} | `{json.dumps(v, ensure_ascii=False)}` |")
    best = min(results, key=lambda r: (r["cer"], r["wer"]))
    lines += ["", f"Ən aydın: **{best['variant']['ad']}**", ""]
    for r in results:
        bad = Counter()
        for row in r["rows"]:
            for op, a, b in row["ops"]:
                if op in "SD":
                    bad[f"{a} → {b or '∅'}"] += 1
        lines += [f"#### {r['variant']['ad']}: tez-tez səhv eşidilən sözlər", "",
                  ", ".join(f"{k} ×{n}" for k, n in bad.most_common(30)) or "—", ""]
    first = results[0]
    lines += [f"#### Cümlələr: {first['variant']['ad']} ↔ {best['variant']['ad']}", ""]
    for a, b in zip(first["rows"], best["rows"]):
        if a["werr"] or b["werr"]:
            lines += [f"- **{a['i']:03d}** {a['text']}", f"  - gözlənən: {a['ref']}",
                      f"  - {first['variant']['ad']} ({a['werr']}/{a['words']}): {a['heard']}",
                      f"  - {best['variant']['ad']} ({b['werr']}/{b['words']}): {b['heard']}"]
    return "\n".join(lines) + "\n"


if __name__ == "__main__":
    if len(sys.argv) in (4, 5) and sys.argv[1] == "dinle":
        main(*sys.argv[2:])
    elif len(sys.argv) == 3 and sys.argv[1] == "hesabat":
        found = collect(sys.argv[2])
        if not found:
            sys.exit("netice-*.json tapılmadı")
        print(report(found))
    else:
        sys.exit("İşlədilmə: ses_yoxla.py dinle <korpus.json> <çıxış> [köhnə az_text.py] | hesabat <qovluq>")
