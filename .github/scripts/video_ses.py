#!/usr/bin/env python3
"""Video xəbərin səsi: SARA (BHOSAI/SARA_TTS — «Dinlə» serverinin açıq Azərbaycan modeli; sahib, 2026-11-08: səs seçimi «sara»,
«pullu heç nə olmasın»). Microsoft-dan və pullu xidmətdən asılılıq yoxdur; model GitHub Actions-da işləyir.

İşlədilmə: python3 video_ses.py <hissələr.json> <çıxış.wav> <vaxtlar.json>
  hissələr.json  {"parts": ["başlıq", "altyazı 1", …, "sonluq"]}  (video-xeber.cjs prepare().say)
  çıxış.wav      mono 16 bit PCM, modelin tezliyi
  vaxtlar.json   {"sr": …, "duration": …, "parts": [[başlanğıc, son], …]} saniyə; hər hissə öz sonrakı fasiləsi ilə
Mətn «Dinlə» serveri ilə eyni qayda ilə səsə hazırlanır (az_text.phrases: rəqəm, tarix, faiz sözə çevrilir).
Xəta olsa video-xeber.cjs videonu səssiz hazırlayır.
"""
import json
import os
import re
import sys
import wave

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "ses-server"))
from az_text import PAUSE_CLAUSE, phrases, tune  # noqa: E402

MODEL = os.environ.get("SES_MODEL", "BHOSAI/SARA_TTS")


def breath(text, nxt):
    """Hissənin səsləndirmə parçaları. Altyazı uzun cümləni iki hissəyə bölür («…həyata keçirilən» | «təcili tədbirlər…»):
    cümlə davam edirsə (növbəti hissə kiçik hərflə başlayır) hissə sonunda cümlə fasiləsi yox, nəfəs qədər sükut olur —
    insan ortada dayanmır (vergüldən sonra vergül fasiləsi, vergülsüz yerdə 0,1 s)."""
    out = phrases(text)
    if out and re.match(r"\s*[«\"“]?[a-zçəğıöşü]", nxt) and not re.search(r"[.!?…][\"»”)]*\s*$", text):
        out[-1] = (out[-1][0], PAUSE_CLAUSE if re.search(r"[,;:–—][\"»”)]*\s*$", text) else 0.1)
    return out


def main(src, wav_out, json_out):
    import numpy as np
    import torch
    from transformers import AutoTokenizer, VitsModel

    torch.set_num_threads(max(1, os.cpu_count() or 1))
    torch.manual_seed(8)  # eyni mətn — eyni səs
    tok, model = AutoTokenizer.from_pretrained(MODEL), tune(VitsModel.from_pretrained(MODEL).eval())
    sr = model.config.sampling_rate
    with open(src, encoding="utf-8") as f:
        parts = json.load(f)["parts"]
    pcm, spans, pos = [], [], 0
    for idx, text in enumerate(parts):
        start = pos
        for said, pause in breath(text, parts[idx + 1] if idx + 1 < len(parts) else "") or [("", 0.3)]:  # söz yoxdursa qısa sükut
            chunk = b""
            if said:
                with torch.no_grad():
                    wave_ = model(**tok(said, return_tensors="pt")).waveform[0].numpy()
                chunk = (np.clip(wave_, -1, 1) * 32767).astype("<i2").tobytes()
            gap = int(sr * pause)
            pcm += [chunk, b"\x00\x00" * gap]
            pos += len(chunk) // 2 + gap
        spans.append([round(start / sr, 3), round(pos / sr, 3)])
    with wave.open(wav_out, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(sr)
        w.writeframes(b"".join(pcm))
    with open(json_out, "w", encoding="utf-8") as f:
        json.dump({"sr": sr, "duration": round(pos / sr, 3), "parts": spans}, f)


if __name__ == "__main__":
    if len(sys.argv) != 4:
        sys.exit("İşlədilmə: video_ses.py <hissələr.json> <çıxış.wav> <vaxtlar.json>")
    main(*sys.argv[1:])
