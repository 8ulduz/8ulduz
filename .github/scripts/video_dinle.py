#!/usr/bin/env python3
"""Nümunə videonun səsini Whisper ilə «dinləyir» (sahib, 2026-11-25: «iyirmibeş sözünü dinlə. azərtacdan sonra nə deyir dinlə.
… sən tapmadın?»). Oxunmalı mətn (video.json «oxunan» — video_ses.py-yə gedən hissələr) eşidilənlə müqayisə olunur: səhv
eşidilən, itən və artıq sözlər xülasəyə yazılır. Whisper özü də səhv edir (ad yazılışı, «çərşəmbə»), ona görə rəqəmin özü yox,
siyahı vacibdir: söz itirsə və ya başqa söz eşidilirsə, qulaqla yoxlamaq lazımdır.

İşlədilmə (sosial-video.yml, yalnız PR): python3 video_dinle.py <video.mp4> <video.json>  → markdown (stdout)
  ASR_MODEL  Whisper modeli (default large-v3)
Müqayisə ses_yoxla.py-nin qaydası ilədir: hər iki tərəf az_text.phrases-dən keçir («25» ≡ «iyirmi beş», «ABŞ» ≡ «a be şe»).
"""
import importlib.util
import json
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
SES = os.path.join(os.path.dirname(HERE), "ses-server")
sys.path.insert(0, SES)
import az_text  # noqa: E402


def words(text):
    """Müqayisə üçün sözlər: az_text.phrases (rəqəm, qısaltma sözlə; kiçik hərf, durğusuz), tire boşluq."""
    return " ".join(s for s, _ in az_text.phrases(text)).replace("-", " ").split()


def edits(ref, hyp):
    """Levenshtein: (məsafə, [(növ, gözlənən, eşidilən, gözlənənin yeri)]); növ S — başqa söz, D — itən, I — artıq."""
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
                ops.append(("S", ref[i - 1], hyp[j - 1], i - 1))
            i, j = i - 1, j - 1
        elif i > 0 and d[i][j] == d[i - 1][j] + 1:
            ops.append(("D", ref[i - 1], "", i - 1))
            i -= 1
        else:
            ops.append(("I", "", hyp[j - 1], i))
            j -= 1
    return d[n][m], ops[::-1]


def report(ref, hyp, heard, meta, model):
    dist, ops = edits(ref, hyp)
    ses = {"babek": "Babək", "sara": "SARA"}.get(meta.get("ses"), meta.get("ses") or "?")
    lines = [f"#### Səsi dinləmə (Whisper {model}, səs: {ses})", "",
             f"Söz xətası: **{dist}/{len(ref)}** ({100 * dist / max(1, len(ref)):.0f}%). Eşidilən: «{heard}»", ""]
    if ops:
        lines += ["| | Gözlənən | Eşidilən | Yer |", "|---|---|---|---|"]
        kind = {"S": "başqa söz", "D": "itib", "I": "artıq"}
        for k, a, b, at in ops[:25]:
            ctx = " ".join(ref[max(0, at - 3):at + 3])
            lines.append(f"| {kind[k]} | {a or '—'} | {b or '—'} | …{ctx}… |")
    else:
        lines.append("Bütün sözlər düz eşidildi.")
    return "\n".join(lines) + "\n"


def main(mp4, meta_path):
    import numpy as np
    from faster_whisper import WhisperModel

    meta = json.load(open(meta_path, encoding="utf-8"))
    said = [str(x) for x in meta.get("oxunan") or []]
    if not said:
        print("#### Səsi dinləmə\n\nvideo.json-da «oxunan» yoxdur.\n")
        return
    pcm = subprocess.run(["ffmpeg", "-loglevel", "error", "-i", mp4, "-vn", "-f", "s16le", "-ac", "1", "-ar", "16000", "pipe:1"],
                         capture_output=True, check=True).stdout
    audio = np.frombuffer(pcm, dtype="<i2").astype(np.float32) / 32768.0
    model = os.environ.get("ASR_MODEL", "large-v3")
    asr = WhisperModel(model, device="cpu", compute_type="int8", cpu_threads=os.cpu_count() or 2)
    segs, _ = asr.transcribe(audio, language="az", beam_size=5, temperature=0.0, condition_on_previous_text=False, vad_filter=False)
    heard = " ".join(s.text.strip() for s in segs).strip()
    # Whisper bəzən bütün hissəni böyük hərflə yazır («ANİ KÜLƏKLƏRİN»): kiçildilir, yoxsa qayda onu qısaltma kimi hərf-hərf açar
    ref, hyp = words(" ".join(said)), words(az_text.lower_az(heard))
    out = report(ref, hyp, heard, meta, model)
    with open(os.path.join(os.path.dirname(meta_path), "dinleme.md"), "w", encoding="utf-8") as f:
        f.write(out)
    print(out)


if __name__ == "__main__":
    if len(sys.argv) != 3:
        sys.exit("İşlədilmə: video_dinle.py <video.mp4> <video.json>")
    main(*sys.argv[1:])
