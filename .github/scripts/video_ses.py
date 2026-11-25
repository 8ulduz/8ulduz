#!/usr/bin/env python3
"""Video xəbərin səsi: SARA (BHOSAI/SARA_TTS — «Dinlə» serverinin açıq Azərbaycan modeli; sahib, 2026-11-08: səs seçimi «sara»,
«pullu heç nə olmasın»). Microsoft-dan və pullu xidmətdən asılılıq yoxdur; model GitHub Actions-da işləyir.

İşlədilmə: python3 video_ses.py <hissələr.json> <çıxış.wav> <vaxtlar.json>
  hissələr.json  {"parts": ["başlıq", "altyazı 1", …, "sonluq"], "davam": [false, …]}  (video-xeber.cjs prepare().say, .davam;
                 davam istəyə bağlıdır: davam[i] — i-ci hissə əvvəlkinin cümləsinin davamıdır)
  çıxış.wav      mono 16 bit PCM, modelin tezliyi
  vaxtlar.json   {"sr": …, "duration": …, "parts": [[başlanğıc, son], …]} saniyə; hər hissə öz sonrakı fasiləsi ilə
Mətn «Dinlə» serveri ilə eyni qayda ilə səsə hazırlanır (az_text.phrases: rəqəm, tarix, faiz sözə çevrilir).
Xəta olsa video-xeber.cjs videonu səssiz hazırlayır.

Cümlə bir nəfəsdə səslənir (sahib, 2026-11-25: «sətirdən sətrə keçəndə mənasız pauza verir»). Altyazı uzun cümləni bir neçə
hissəyə bölür («…yol-nəqliyyat hadisəsi» | «nəticəsində Ərçivan…»). Əvvəl hər hissə ayrıca səslənirdi: parçanın öz başında və
sonunda sükut olurdu, intonasiya cümlə sonu kimi düşürdü. İndi eyni cümlənin ardıcıl hissələri (qrup) bir mətn kimi bir dəfə
səslənir, qrupun vaxtı hissələrə bölünür: modelin hər hərfə verdiyi müddətlə (VITS duration predictor), alınmasa tələffüz
uzunluğu ilə. Hissənin sonu növbəti hissənin ilk sözündən əvvəlki boşluqdur. vaxtlar.json-un formatı dəyişmir.
"""
import json
import os
import re
import sys
import wave

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "ses-server"))
from az_text import phrases, tune  # noqa: E402

MODEL = os.environ.get("SES_MODEL", "BHOSAI/SARA_TTS")
# phrases-in max_len həddi: video səsi cümlənin içində bölünmür (06ba2c78ef, «cümlə bütöv səslənir»). Qrupun mətni bir cümlədir,
# 220 simvoldan uzun olsa da vergüldə bölünmür — bölünsə hər parça yenə ayrıca cümlə kimi bitərdi.
WHOLE = 10 ** 6
EMPTY_PAUSE = 0.3   # söz yoxdursa (yalnız durğu) qısa sükut
LOWER_START = re.compile(r"\s*[«\"“]?[a-zçəğıöşü]")
SENT_END = re.compile(r"[.!?…][\"»”)]*\s*$")


def say_items(text):
    """Model mətni və sonrakı fasilə: [(mətn, saniyə)]. Cümlə sonunda fasilə, cümlənin içində bölmə yoxdur."""
    return phrases(text, max_len=WHOLE)


def continues(text, nxt):
    """Cümlə növbəti hissədə davam edir: növbəti hissə kiçik hərflə başlayır, bu hissə cümlə sonu işarəsi ilə bitmir
    (başlıq nöqtəsizdir, amma izah böyük hərflə başlayır — birləşmir)."""
    return bool(nxt and LOWER_START.match(nxt) and not SENT_END.search(text) and say_items(text))


def groups(parts, davam=None):
    """Eyni cümlənin ardıcıl hissələri bir qrupdur: ["Başlıq", "Uzun cümlənin", "davamı.", "Sonluq."] → [[0], [1, 2], [3]].
    davam[i] (video-xeber.cjs prepare): i-ci hissə əvvəlkinin cümləsinin davamıdır — cümləni altyazı özü bölüb, dəqiqdir
    («Xudat | Məmmədovun» kimi böyük hərflə başlayan davamı da tutur). Verilməyibsə (hava videosu) mətndən: continues()."""
    known = isinstance(davam, list) and len(davam) == len(parts)
    out = []
    for i, text in enumerate(parts):
        if out and (davam[i] is True if known else continues(parts[i - 1], text)):
            out[-1].append(i)
        else:
            out.append([i])
    return out


def spoken(text):
    """Hissənin oxunan mətni (rəqəm, qısaltma sözlə) — qrupun içində hissənin payı."""
    return " ".join(s for s, _ in say_items(text))


def cut_offsets(texts, items):
    """Qrupun səs mətnində (items, boşluqla birləşmiş) hər daxili sərhədin yeri: [(item nömrəsi, simvol)], simvol növbəti
    hissənin ilk hərfindən əvvəlki boşluqdur. Hissələrin oxunan mətni ayrıca hesablanır; qrupun mətni ondan fərqlənsə
    (ayrıca oxunuş birləşmədə dəyişirsə) yer uzunluq nisbəti ilə köçürülür."""
    lens = [len(spoken(t)) for t in texts]
    total_p = sum(lens) + len(lens) - 1
    said = [s for s, _ in items]
    total_g = sum(len(s) for s in said) + len(said) - 1
    out, acc = [], 0
    for n in lens[:-1]:
        acc += n
        c = round(acc * total_g / total_p) if total_p > 0 else 0
        q = 0
        while q < len(said) - 1 and c >= len(said[q]):   # sərhəd iki səsləndirmənin arasındadır: fasilə əvvəlki hissənindir
            c -= len(said[q]) + 1
            q += 1
        out.append((q, max(0, min(c, len(said[q])))))
        acc += 1
    return out


def offset_samples(said, o, samples, frames, tokens):
    """Səs parçasında (said → samples nümunə) o simvoldan əvvəlki hissənin uzunluğu, nümunə ilə. frames: modelin hər tokenə
    verdiyi kadr sayı (VITS durations); tokens(mətn) — tokenizerin tokenləri. Müddət yoxdursa hərf payı ilə."""
    if not said or samples <= 0 or o <= 0:
        return 0
    if frames and sum(frames) > 0:
        try:
            b = tokens(said[:o])
        except Exception:  # noqa: BLE001 — tokenizer xətası bölgünü dayandırmasın, hərf payına keçir
            b = -1
        if 0 <= b <= len(frames):
            return round(samples * sum(frames[:b]) / sum(frames))
    return round(samples * min(o, len(said)) / len(said))


def render(parts, voice, sr, davam=None):
    """Hissələr → (PCM baytları, hər hissənin [başlanğıc, son] nümunə ilə, cəmi nümunə). voice.wave(mətn) → (PCM, frames və ya None),
    voice.tokens(mətn) → token sayı. Qrup bir dəfə səslənir, sərhədləri cut_offsets + offset_samples verir."""
    pcm, spans, pos = [], [None] * len(parts), 0
    for idx in groups(parts, davam):
        start = pos
        texts = [parts[i] for i in idx]
        items = say_items(" ".join(t.strip() for t in texts)) or [("", EMPTY_PAUSE)]
        marks = []
        for said, pause in items:
            chunk, frames = voice.wave(said) if said else (b"", None)
            n = len(chunk) // 2
            marks.append((pos, n, frames))
            gap = int(sr * pause)
            pcm += [chunk, b"\x00\x00" * gap]
            pos += n + gap
        edges = [start]
        for q, o in (cut_offsets(texts, items) if len(idx) > 1 else []):
            at, n, frames = marks[q]
            edges.append(max(edges[-1], min(pos, at + offset_samples(items[q][0], o, n, frames, voice.tokens))))
        edges.append(pos)
        for j, i in enumerate(idx):
            spans[i] = [edges[j], edges[j + 1]]
    return b"".join(pcm), spans, pos


class Sara:
    """SARA (VITS). Hər səsləndirmədə modelin hərf müddətləri (duration_predictor-un çıxışı) götürülür: qrupun vaxtını hissələrə
    bölmək üçün. Alınmasa (model quruluşu başqadır) frames None olur, bölgü hərf payı ilə gedir."""

    def __init__(self, name=MODEL):
        import torch
        from transformers import AutoTokenizer, VitsModel

        self.torch = torch
        torch.set_num_threads(max(1, os.cpu_count() or 1))
        torch.manual_seed(8)  # eyni mətn — eyni səs
        self.tok, self.model = AutoTokenizer.from_pretrained(name), tune(VitsModel.from_pretrained(name).eval())
        self.sr = self.model.config.sampling_rate
        self.log_dur = []
        dp = getattr(self.model, "duration_predictor", None)
        if dp is not None:
            dp.register_forward_hook(lambda _m, _i, out: self.log_dur.append(out))
        self.used = {"müddət": 0, "pay": 0}

    def tokens(self, text):
        return int(self.tok(text, return_tensors="pt")["input_ids"].shape[-1])

    def wave(self, said):
        import numpy as np

        torch = self.torch
        inputs = self.tok(said, return_tensors="pt")
        self.log_dur.clear()
        with torch.no_grad():
            w = self.model(**inputs).waveform[0].numpy()
        chunk = (np.clip(w, -1, 1) * 32767).astype("<i2").tobytes()
        frames = None
        if len(self.log_dur) == 1 and torch.is_tensor(self.log_dur[0]):
            # VitsModel.forward ilə eyni: duration = ceil(exp(log_duration) * mask * (1 / speaking_rate)); batch 1, maska 1.
            d = torch.ceil(torch.exp(self.log_dur[0]) * (1.0 / self.model.speaking_rate)).flatten().long().tolist()
            n = len(chunk) // 2
            if len(d) == inputs["input_ids"].shape[-1] and sum(d) > 0 and n % sum(d) == 0:
                frames = d
        self.used["müddət" if frames else "pay"] += 1
        return chunk, frames


def main(src, wav_out, json_out):
    with open(src, encoding="utf-8") as f:
        data = json.load(f)
    parts, davam = data["parts"], data.get("davam")
    voice = Sara()
    sr = voice.sr
    pcm, spans, pos = render(parts, voice, sr, davam)
    with wave.open(wav_out, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(sr)
        w.writeframes(pcm)
    with open(json_out, "w", encoding="utf-8") as f:
        json.dump({"sr": sr, "duration": round(pos / sr, 3), "parts": [[round(s / sr, 3), round(e / sr, 3)] for s, e in spans]}, f)
    g = groups(parts, davam)
    print(f"video_ses: {len(parts)} hissə, {len(g)} qrup ({sum(len(x) - 1 for x in g)} sərhəd cümlənin içində); "
          f"modelin müddətləri {voice.used['müddət']}/{voice.used['müddət'] + voice.used['pay']} səsləndirmədə alındı", file=sys.stderr)


if __name__ == "__main__":
    if len(sys.argv) != 4:
        sys.exit("İşlədilmə: video_ses.py <hissələr.json> <çıxış.wav> <vaxtlar.json>")
    main(*sys.argv[1:])
