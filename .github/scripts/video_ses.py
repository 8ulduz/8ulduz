#!/usr/bin/env python3
"""Video xəbərin səsi: Babək (saytın «Dinlə» səsi, Microsoft Edge, edge-tts — açarsız, pulsuz), alınmasa SARA.

Babək (sahib, 2026-11-25: «edge-tts ilə (açarsız)»). SARA hərfləri udur və səhv oxuyurdu (sahib: «iyirmibeş sözünü dinlə.
azərtacdan sonra … anlamaq olmur», «hərfin deyilişdə az qala itməsidir»). Whisper large-v3 ilə eyni cümlələr: SARA «AZƏRTAC
xəbər verir ki, bu səbəbdən rayonun … qaz təchizatında» → «Azərtaçı istinad əbər verir ki, bu səbəbdən rayının … də
səcizatında», Babək → düz; layihənin 81 cümləlik ölçüsündə hərf xətası Babəkdə 2–3%, SARA-da 10–11% (PR #311, ses_yoxla.py).
Babək vergüldə, iki nöqtədə özü nəfəs alır, cümlənin intonasiyasını özü qurur — mətn durğu ilə gedir (az_text.for_voice, saytın
hazır səsi ilə eyni yol). Söz sərhədləri (WordBoundary) altyazı hissələrinin vaxtını verir. Edge-in xidməti cavab verməsə (rəsmi
olmayan yoldur, Microsoft dəyişə bilər) səs SARA ilə hazırlanır (VIDEO_SES_MOTOR=sara — həmişə SARA).

SARA (BHOSAI/SARA_TTS — «Dinlə» serverinin açıq Azərbaycan modeli; sahib, 2026-11-08: səs seçimi «sara», «pullu heç nə
olmasın»): ehtiyat. Model GitHub Actions-da işləyir. Aşağıdakı qruplaşma və nəfəs qaydaları onundur.

İşlədilmə: python3 video_ses.py <hissələr.json> <çıxış.wav> <vaxtlar.json>
  hissələr.json  {"parts": ["altyazı 1", …, "sonluq"], "davam": [false, …]}  (video-xeber.cjs prepare().say, .davam — başlıq
                 oxunmur, sahib 2026-11-24/25; hava videosunda birinci hissə giriş cümləsidir;
                 davam istəyə bağlıdır: davam[i] — i-ci hissə əvvəlkinin cümləsinin davamıdır)
  çıxış.wav      mono 16 bit PCM, modelin tezliyi
  vaxtlar.json   {"sr": …, "duration": …, "parts": [[başlanğıc, son], …]} saniyə; hər hissə öz sonrakı fasiləsi ilə
Mətn «Dinlə» serveri ilə eyni qayda ilə səsə hazırlanır (az_text.phrases: rəqəm, tarix, faiz sözə çevrilir).
Xəta olsa video-xeber.cjs videonu səssiz hazırlayır.

Cümlə bir nəfəsdə səslənir (sahib, 2026-11-25: «sətirdən sətrə keçəndə mənasız pauza verir»). Altyazı uzun cümləni bir neçə
hissəyə bölür («…yol-nəqliyyat hadisəsi» | «nəticəsində Ərçivan…»). Əvvəl hər hissə ayrıca səslənirdi: parçanın öz başında və
sonunda sükut olurdu, intonasiya cümlə sonu kimi düşürdü. İndi eyni cümlənin ardıcıl hissələri (qrup) bir mətn kimi bir dəfə
səslənir, qrupun vaxtı hissələrə bölünür: modelin hər hərfə verdiyi müddətlə (VITS duration predictor), alınmasa tələffüz
uzunluğu ilə. Hissənin sonu növbəti hissənin ilk sözündən əvvəlki boşluqdur.

Cümlənin içində nəfəs (sahib, 2026-11-25: «Abunə ol deyib pauza vermir. belə oxuyanda nə dediyini tam başa düşmək olmur»).
Model durğu işarəsini tanımır (az_text.fold onu boşluq edir), cümlə isə bütöv səslənir — ona görə vergül, iki nöqtə, nöqtəli
vergül, boşluqlu tire və mötərizə səsdə heç yox idi: «Sabah, 25 noyabr, çərşənbə, hava belə olacaq» bir nəfəsdə gedirdi.
Cümləni vergüldə ayrıca səsləndirmək olmaz (hər parça cümlə sonu kimi bitir; Whisper ölçməsi, az_text.phrases). İndi cümlə
yenə bir dəfə səslənir (intonasiya davam edir), sonra səsin içinə, işarənin yerinə sükut qoyulur: yer modelin öz
müddətlərindən (əvvəlki sözün son hərfinin ortasından növbəti sözün ilk hərfinin ortasına qədər), orada ən sakit an; kəsimin
iki tərəfində sönmə və açılma (sakit yerdə qısa, səsin içində uzun — breath_cuts, splice).
Model müddət vermirsə nəfəs qoyulmur (hərf payı ilə təxmin sözün içinə düşə bilər).
vaxtlar.json: əvvəlki sahələr dəyişmir, «motor» (babek | sara), «nefes» (SARA: qoyulan nəfəslər — an, uzunluq, kəsim yerinin
səs səviyyəsi) və «qisaldilan_herf» əlavə olunub.
"""
import array
import asyncio
import json
import math
import os
import re
import subprocess
import sys
import time
import wave

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "ses-server"))
from az_text import CLAUSE, PAUSE_CLAUSE, PAUSE_SENTENCE, fold, for_voice, lower_az, tune, verbalize  # noqa: E402

# Babək. Temp: Edge-in öz sürəti cümlənin içində 154 söz/dəq (2026-11-25, 5 mətn, 79 söz) — SARA-nın düzəldilməmiş tempi kimi
# tez (sahib: «oxunuş sürətlidir»); −10% → 138, cümlə fasilələri ilə ~125–130 söz/dəq (SARA-nın indiki tempi ilə eyni).
BABEK_VOICE = "az-AZ-BabekNeural"
BABEK_RATE = "-10%"
BABEK_SR = 24000          # Edge mp3-ü 24 kHz-dir; ffmpeg ilə 16 bit PCM-ə açılır
BABEK_HEAD = 0.05         # birinci sözdən əvvəl saxlanan səs (s): nəfəs və hücum kəsilməsin
BABEK_TAIL = 0.12         # sonuncu sözdən sonra saxlanan səs (s): sözün sönməsi (Edge-in söz müddəti onu tam əhatə etmir)
BABEK_TRIES = (0, 3, 8)   # şəbəkə xətasında yenidən sınama (gözləmə, s)
from az_text import SENT_END as TEXT_SENT_END  # noqa: E402  (cümlələri bölən; bu fayldakı SENT_END hissənin sonunu yoxlayır)

MODEL = os.environ.get("SES_MODEL", "BHOSAI/SARA_TTS")
# Videonun oxu tempi (sahib, 2026-11-25: «oxunuş sürətlidir. oxunuşu normal et»). Ölçü (2026-11-25, 40,8 s-lik xəbər videosu):
# modelin öz sürəti (1,0) və «Dinlə»nin fasilələri (vergül 0,16 s, cümlə 0,38 s) ilə dəqiqədə 155 söz, fasilələr daxil — xəbər
# diktoru üçün tezdir (normal ~115–125). Sürət 0,85 (hər səs 1/0,85 ≈ 1,18 dəfə uzun) və uzun fasilələr: ~125 söz/dəq. Yalnız
# video; saytın «Dinlə» səsi (ses-server, az_text.VOICE) dəyişmir.
VIDEO_RATE = 0.85
VIDEO_PAUSE = {PAUSE_CLAUSE: 0.28, PAUSE_SENTENCE: 0.65}
# Nəfəsin uzunluğu: iki nöqtə, nöqtəli vergül, tire və uzun hissədən sonrakı vergül — VIDEO_PAUSE[PAUSE_CLAUSE]; qısa hissədən
# (SHORT_CLAUSE simvoldan az: «Sabah,», «çərşənbə,», mötərizədəki söz) sonra BREATH_SHORT — sadalama doğranmış kimi səslənməsin.
BREATH_SHORT = 0.18
SHORT_CLAUSE = 14
# Kəsim (2026-11-25, SARA ilə yerli ölçü). Kəsim yalnız iki sözün arasındadır: əvvəlki sözün son hərfi bitəndən növbəti sözün
# ilk hərfi başlayana qədər (modelin öz müddətləri ilə), orada ən sakit an. Sönmə və açılma da bu aralıqdan çıxmır — hərfə
# toxunmur. Əvvəlki variant (sahib, 2026-11-25: «iyirmibeş sözünü dinlə. azərtacdan sonra nə deyir dinlə») son hərfin ortasından
# axtarır və 50 ms söndürürdü: qısa söz yeyilirdi — «ki,» → «k», «Qubada 10,» → «Qubada o». Modelin özünə fasilə etdirmək
# alınmadı: boşluq, boş token, «–», «_» uzadılanda model sükut yox, uzanmış səs verir (14 yerdən 2-də sakit).
FADE_S = 0.012      # sakit kəsimdə (QUIET_DB-dən aşağı) hər tərəfdə sönmə/açılma: çıqqıltı olmasın
FADE_OUT_SOFT = 0.03   # səsin içində kəsimdə (saitdən saitə keçid): keçid yavaşca sönür
FADE_IN_SOFT = 0.015   # və növbəti söz qısa açılma ilə başlayır
FADE_MIN = 0.004       # aralıq dar olanda da ən azı bu qədər (çıqqıltı olmasın)
QUIET_DB = -30.0
QUIET_S = 0.010     # ən sakit an bu uzunluqda pəncərə ilə (dörddə bir addımla) axtarılır
EMPTY_PAUSE = 0.3   # söz yoxdursa (yalnız durğu) qısa sükut
LETTER_MAX = 6      # hərfin ən uzun müddəti, kadr (16 ms; video tempində) — Sara, cap_letters
LOWER_START = re.compile(r"\s*[«\"“]?[a-zçəğıöşü]")
SENT_END = re.compile(r"[.!?…][\"»”)]*\s*$")


def model_text(part):
    """Modelə gedən mətn (az_text.phrases ilə eyni qayda): kiçik hərf, yalnız modelin tanıdığı hərflər, tək boşluq."""
    said = re.sub(r"\s+", " ", fold(lower_az(part))).strip(" -")
    return re.sub(r"\s*-\s*-+\s*", "-", said)


def sentences(text):
    """Cümlələr və hər cümlədə nəfəs yerləri: [(model mətni, [(simvol, saniyə), …])]. Cümlə bütöv bir mətndir (bir dəfə
    səslənir); simvol — nəfəsdən sonrakı hissənin ilk hərfindən əvvəlki boşluğun yeridir, saniyə — nəfəsin uzunluğu."""
    out = []
    for sentence in TEXT_SENT_END.split(verbalize(text).strip()):
        pieces, last = [], 0
        for m in CLAUSE.finditer(sentence):
            # güclü ayırıcı: tire, iki nöqtə, nöqtəli vergül (vergül və mötərizə zəifdir)
            strong = bool(m.group(0).strip(" \t\n()")) or sentence[max(0, m.start() - 1):m.start()] in (":", ";")
            pieces.append((sentence[last:m.start()], strong))
            last = m.end()
        pieces.append((sentence[last:], False))
        said, marks, before, strong_before = "", [], 0, False
        for raw, strong in pieces:
            part = model_text(raw)
            if not part:
                strong_before = strong_before or strong   # boş hissə (ardıcıl işarələr): ayırıcıların güclüsü qalır
                continue
            if said:
                long = strong_before or before >= SHORT_CLAUSE
                marks.append((len(said), VIDEO_PAUSE[PAUSE_CLAUSE] if long else BREATH_SHORT))
                said += " " + part
            else:
                said = part
            before, strong_before = len(part), strong
        if said:
            out.append((said, marks))
    return out


def say_items(text):
    """Model mətni və sonrakı fasilə: [(mətn, saniyə)]. Hər cümlə bir mətndir, sonunda videonun cümlə fasiləsi.
    Cümlənin içindəki nəfəslər ayrıca verilir (sentences) və səsin içinə qoyulur (render)."""
    return [(said, VIDEO_PAUSE[PAUSE_SENTENCE]) for said, _ in sentences(text)]


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


def samples_of(chunk):
    """PCM baytları (16 bit, kiçik uclu) → array('h')."""
    a = array.array("h")
    a.frombytes(chunk[:len(chunk) // 2 * 2])
    if sys.byteorder == "big":
        a.byteswap()
    return a


def bytes_of(a):
    if sys.byteorder == "big":
        a = array.array("h", a)
        a.byteswap()
    return a.tobytes()


def level(a, lo, hi):
    """[lo, hi) nümunələrinin orta kvadratı (səs səviyyəsi)."""
    lo, hi = max(0, lo), min(len(a), hi)
    return sum(x * x for x in a[lo:hi]) / (hi - lo) if hi > lo else 0.0


def quietest(a, lo, hi, sr):
    """[lo, hi) aralığında ən sakit an: QUIET_S-lik pəncərənin ortası; bərabərdirsə aralığın ortasına ən yaxını."""
    mid, w = (lo + hi) // 2, max(1, int(sr * QUIET_S))
    if hi - lo <= w:
        return mid
    best, at = None, mid
    for s in range(lo, hi - w + 1, max(1, w // 4)):
        e, c = level(a, s, s + w), s + w // 2
        if best is None or e < best or (e == best and abs(c - mid) < abs(at - mid)):
            best, at = e, c
    return at


def breath_cuts(said, breaths, a, frames, tokens, sr):
    """Nəfəslərin səsdəki yeri: [(simvol, nümunə, sükutun nümunəsi, səviyyə dB, sönmə, açılma)], artan sıra ilə. Yalnız modelin
    öz müddətləri ilə (frames). b — işarədən sonrakı boşluğun tokeni (işarəyə qədərki mətnin token sayı); tokenizer hərflərin
    arasına boş token qoyursa (SARA: «ab» → [boş, a, boş, b, boş]) qonşu hərf iki addım uzaqdadır. Axtarış yalnız iki sözün
    arasındadır: əvvəlki sözün son hərfi bitəndən növbəti sözün ilk hərfi başlayana qədər, ən sakit an. Sönmə (nümunə ilə)
    kəsimdən geriyə, açılma irəliyə — hər ikisi bu aralığın içində qalır (hərfə toxunmur), ən azı FADE_MIN. Səviyyə — kəsim
    yerinin səsi bütün səsləndirmənin ortasına görə (mənfi — sakit). Müddət yoxdursa boş siyahı."""
    n = len(a)
    if not breaths or not frames or sum(frames) <= 0 or n <= 0 or n % sum(frames):
        return []
    spf, out, whole, w = n // sum(frames), [], max(level(a, 0, n), 1e-9), max(1, int(sr * QUIET_S))
    try:
        step = max(1, tokens("a") - 1)
    except Exception:  # noqa: BLE001
        step = 1
    at = lambda i: sum(frames[:i]) * spf                # noqa: E731 — i-ci tokenin başlanğıcı (nümunə)
    least = max(1, int(sr * FADE_MIN))
    for o, pause in breaths:
        try:
            b = tokens(said[:o])
        except Exception:  # noqa: BLE001 — tokenizer xətası səsi dayandırmasın: bu nəfəs qoyulmur
            continue
        if not step <= b < len(frames) - step:
            continue
        lo, hi = at(b - step + 1), at(b + step)          # son hərfin sonu … ilk hərfin başlanğıcı
        cut = quietest(a, lo, hi, sr)
        if out and cut <= out[-1][1]:
            continue
        db = round(10 * math.log10(max(level(a, cut - w // 2, cut + w // 2), 1e-9) / whole), 1)
        f_out, f_in = (FADE_S, FADE_S) if db < QUIET_DB else (FADE_OUT_SOFT, FADE_IN_SOFT)
        out.append((o, cut, int(sr * pause), db, max(least, min(int(sr * f_out), cut - lo)), max(least, min(int(sr * f_in), hi - cut))))
    return out


def splice(a, cuts, sr):
    """Nəfəs yerlərinə sükut qoyur; kəsimdən əvvəl səs sönür, sonra açılır (breath_cuts-un verdiyi uzunluqla) — çıqqıltı
    olmasın. Qaytarır: PCM baytları."""
    out, last = array.array("h"), 0
    for _, cut, gap, _db, f_out, f_in in cuts:
        k = min(f_out, cut - last)
        for i in range(k):
            a[cut - 1 - i] = a[cut - 1 - i] * i // k
        m = min(f_in, len(a) - cut)
        for i in range(m):
            a[cut + i] = a[cut + i] * i // m
        out.extend(a[last:cut])
        out.extend(array.array("h", bytes(2 * gap)))
        last = cut
    out.extend(a[last:])
    return bytes_of(out)


def render(parts, voice, sr, davam=None, log=None):
    """Hissələr → (PCM baytları, hər hissənin [başlanğıc, son] nümunə ilə, cəmi nümunə). voice.wave(mətn) → (PCM, frames və ya None),
    voice.tokens(mətn) → token sayı. Qrup bir dəfə səslənir, sərhədləri cut_offsets + offset_samples verir; cümlənin içindəki
    nəfəslər (sentences) səsin içinə sükut kimi qoyulur (breath_cuts, splice). log (siyahı) verilərsə hər nəfəs yazılır:
    qoyulan — [an, sükut (nümunə ilə), kəsim yerinin səviyyəsi dB], qoyula bilməyən (model müddət verməyib) — None."""
    pcm, spans, pos = [], [None] * len(parts), 0
    for idx in groups(parts, davam):
        start = pos
        texts = [parts[i] for i in idx]
        sents = sentences(" ".join(t.strip() for t in texts))
        items = [(said, VIDEO_PAUSE[PAUSE_SENTENCE]) for said, _ in sents] or [("", EMPTY_PAUSE)]
        marks = []
        for k, (said, pause) in enumerate(items):
            chunk, frames = voice.wave(said) if said else (b"", None)
            n = len(chunk) // 2
            breaths, cuts = (sents[k][1] if sents else []), []
            if breaths:
                a = samples_of(chunk)
                cuts = breath_cuts(said, breaths, a, frames, voice.tokens, sr)
                if cuts:
                    chunk = splice(a, cuts, sr)
                if log is not None:
                    shift = 0
                    for _, cut, gap, db, *_ in cuts:
                        log.append([pos + cut + shift, gap, db])
                        shift += gap
                    log.extend([None] * (len(breaths) - len(cuts)))
            marks.append((pos, n, frames, cuts))
            gap = int(sr * pause)
            pcm += [chunk, b"\x00\x00" * gap]
            pos += len(chunk) // 2 + gap
        edges = [start]
        for q, o in (cut_offsets(texts, items) if len(idx) > 1 else []):
            at, n, frames, cuts = marks[q]
            # Nəfəslərin sükutu sərhədi sürüşdürür. Sərhəd nəfəsin öz yerindədirsə (altyazı vergüldə bölünüb) sükut əvvəlki
            # hissənindir: vergüllü söz fasilədə seçili qalır (video-xeber.cjs wordTimes).
            here = [c for c in cuts if c[0] == o]
            if here:
                off = here[0][1] + sum(c[2] for c in cuts if c[1] <= here[0][1])
            else:
                off = offset_samples(items[q][0], o, n, frames, voice.tokens)
                off += sum(c[2] for c in cuts if c[1] <= off)
            edges.append(max(edges[-1], min(pos, at + off)))
        edges.append(pos)
        for j, i in enumerate(idx):
            spans[i] = [edges[j], edges[j + 1]]
    return b"".join(pcm), spans, pos


def cap_letters(log_dur, ids, skip, cap):
    """Hərf tokenlərinin log-müddətini cap-dən yuxarı qaldırmır (boş token və boşluq — skip — toxunulmur). log_dur: tensor
    (…, n), ids: n token. Qaytarır: (yeni tensor, neçə hərf qısaldıldı)."""
    import torch

    if not torch.is_tensor(log_dur) or log_dur.shape[-1] != len(ids):
        return log_dur, 0
    letter = torch.tensor([i not in skip for i in ids], dtype=torch.bool)
    over = letter & (log_dur > cap)
    n = int(over.sum())
    return (torch.where(over, torch.full_like(log_dur, cap), log_dur) if n else log_dur), n


class Sara:
    """SARA (VITS). Hər səsləndirmədə modelin hərf müddətləri (duration_predictor-un çıxışı) götürülür: qrupun vaxtını hissələrə
    bölmək üçün. Alınmasa (model quruluşu başqadır) frames None olur, bölgü hərf payı ilə gedir.
    Hərfin müddəti LETTER_MAX kadrdan uzun olmur (sahib, 2026-11-25: «azərtacdan sonra … anlamaq olmur»): model «AZƏRTAC xəbər
    verir» cümləsində «xəbər»in «b»-sini hər dəfə 19–22 kadr (0,30–0,35 s) uzadırdı, söz tanınmırdı. Ölçü (2026-11-25, 5 mətn,
    3 toxum, 1770 hərf): median 2 kadr, 99% — 5, yeganə uzun hərf həmin «b» idi. Boş token və boşluq toxunulmur (keçid və fasilə)."""

    def __init__(self, name=MODEL):
        import torch
        from transformers import AutoTokenizer, VitsModel

        self.torch = torch
        torch.set_num_threads(max(1, os.cpu_count() or 1))
        torch.manual_seed(8)  # eyni mətn — eyni səs
        self.tok, self.model = AutoTokenizer.from_pretrained(name), tune(VitsModel.from_pretrained(name).eval(), speaking_rate=VIDEO_RATE)
        self.sr = self.model.config.sampling_rate
        self.log_dur, self.ids = [], None
        ids = self.tok("a").input_ids
        self.skip = {ids[0], self.tok.convert_tokens_to_ids(" ")} if len(ids) == 3 else {self.tok.convert_tokens_to_ids(" ")}
        self.capped = 0
        dp = getattr(self.model, "duration_predictor", None)
        if dp is not None:
            dp.register_forward_hook(self._durations)
        self.used = {"müddət": 0, "pay": 0}

    def _durations(self, _m, _i, out):
        # forward hook: qaytarılan tensor modelin öz çıxışını əvəz edir. Müddət = ceil(exp(log) / sürət) ≤ LETTER_MAX.
        if self.ids is not None:
            out, n = cap_letters(out, self.ids, self.skip, math.log(LETTER_MAX * self.model.speaking_rate))
            self.capped += n
        self.log_dur.append(out)
        return out

    def tokens(self, text):
        return int(self.tok(text, return_tensors="pt")["input_ids"].shape[-1])

    def wave(self, said):
        import numpy as np

        torch = self.torch
        inputs = self.tok(said, return_tensors="pt")
        self.ids = inputs["input_ids"][0].tolist()
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


def babek_words(text):
    """Babəkə gedən mətndə (for_voice) sözlər — Edge hər birinə bir WordBoundary verir (2026-11-25: 5 mətn, 79 söz, say eynidir;
    durğu ayrıca söz deyil)."""
    return [w for w in for_voice(text).split() if re.search(r"\w", w)]


class Babek:
    """Edge-in Babək səsi (edge-tts). say(mətn) → (PCM baytları BABEK_SR-də, [(söz, başlanğıc s, müddət s)])."""

    sr = BABEK_SR

    def __init__(self):
        import edge_tts  # noqa: F401 — yalnız iş axınında quraşdırılır; yoxdursa main SARA-ya keçir

        self.calls = 0

    async def _stream(self, text):
        import edge_tts

        c = edge_tts.Communicate(text, BABEK_VOICE, rate=BABEK_RATE, boundary="WordBoundary")
        audio, words = bytearray(), []
        async for ch in c.stream():
            if ch["type"] == "audio":
                audio += ch["data"]
            elif ch["type"] == "WordBoundary":
                words.append((ch["text"], ch["offset"] / 1e7, ch["duration"] / 1e7))
        return bytes(audio), words

    def say(self, text):
        err = None
        for wait in BABEK_TRIES:
            time.sleep(wait)
            try:
                mp3, words = asyncio.run(self._stream(text))
                if not mp3 or not words:
                    raise RuntimeError("boş cavab")
                pcm = subprocess.run(["ffmpeg", "-loglevel", "error", "-i", "pipe:0", "-f", "s16le", "-ac", "1", "-ar", str(self.sr), "pipe:1"],
                                     input=mp3, capture_output=True, check=True).stdout
                self.calls += 1
                return pcm, words
            except Exception as e:  # noqa: BLE001 — şəbəkə, Edge, ffmpeg: yenidən sınanır, sonra main SARA-ya keçir
                err = e
        raise RuntimeError(f"Babək: {err}")


def render_babek(parts, voice, davam=None):
    """Hissələr → (PCM, hər hissənin [başlanğıc, son] nümunə ilə, cəmi nümunə). Qruplar (eyni cümlənin hissələri, groups) bir
    mətn kimi səslənir; qrupun səsi birinci sözdən BABEK_HEAD əvvəl, sonuncudan BABEK_TAIL sonra kəsilir, arxasınca videonun
    cümlə fasiləsi. Qrupun içində hissənin sonu növbəti hissənin birinci sözünün başlanğıcıdır (Edge-in söz sərhədi); söz sayı
    uyğun gəlməsə hərf payı ilə."""
    sr, out, spans, pos = voice.sr, [], [None] * len(parts), 0
    for idx in groups(parts, davam):
        texts = [parts[i].strip() for i in idx]
        text = " ".join(texts)
        start = pos
        if not babek_words(text):
            gap = int(sr * EMPTY_PAUSE)
            out.append(b"\x00\x00" * gap)
            pos += gap
            for i in idx:
                spans[i] = [start, pos]
            continue
        pcm, words = voice.say(for_voice(text))
        n = len(pcm) // 2
        lo = max(0, int(sr * (words[0][1] - BABEK_HEAD)))
        hi = min(n, max(lo, int(sr * (words[-1][1] + words[-1][2] + BABEK_TAIL))))
        counts = [len(babek_words(t)) for t in texts]
        edges, acc = [], 0
        for c in counts[:-1]:
            acc += c
            if sum(counts) == len(words):
                t = words[acc][1]
            else:   # say uyğun deyil: hərf payı ilə birinci sözdən sonuncunun sonuna qədər
                total = sum(len(" ".join(babek_words(x))) for x in texts) or 1
                share = sum(len(" ".join(babek_words(x))) for x in texts[:len(edges) + 1]) / total
                t = words[0][1] + share * (words[-1][1] + words[-1][2] - words[0][1])
            edges.append(min(hi, max(lo, int(sr * t))) - lo)
        gap = int(sr * VIDEO_PAUSE[PAUSE_SENTENCE])
        out += [pcm[2 * lo:2 * hi], b"\x00\x00" * gap]
        pos += (hi - lo) + gap
        cuts = [start] + [start + e for e in edges] + [pos]
        for j, i in enumerate(idx):
            spans[i] = [cuts[j], max(cuts[j], cuts[j + 1])]
    return b"".join(out), spans, pos


def main(src, wav_out, json_out):
    with open(src, encoding="utf-8") as f:
        data = json.load(f)
    parts, davam = data["parts"], data.get("davam")
    motor, voice, nefes = os.environ.get("VIDEO_SES_MOTOR", "babek").strip().lower() or "babek", None, []
    if motor == "babek":
        try:
            voice = Babek()
            pcm, spans, pos = render_babek(parts, voice, davam)
        except Exception as e:  # noqa: BLE001 — edge-tts yoxdur, Edge cavab vermir: video SARA ilə səslənir
            print(f"::warning::video_ses: Babək alınmadı ({str(e)[:200]}) — SARA ilə", file=sys.stderr)
            motor = "sara"
    if motor != "babek":
        motor, voice = "sara", Sara()
        pcm, spans, pos = render(parts, voice, voice.sr, davam, nefes)
    sr = voice.sr
    qoyulan = [x for x in nefes if x]
    with wave.open(wav_out, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(sr)
        w.writeframes(pcm)
    with open(json_out, "w", encoding="utf-8") as f:
        json.dump({"sr": sr, "duration": round(pos / sr, 3), "parts": [[round(s / sr, 3), round(e / sr, 3)] for s, e in spans],
                   "motor": motor,
                   "nefes": {"yer": [[round(t / sr, 3), round(g / sr, 3), db] for t, g, db in qoyulan], "buraxilan": len(nefes) - len(qoyulan)},
                   "qisaldilan_herf": getattr(voice, "capped", 0)}, f)
    g = groups(parts, davam)
    if motor == "babek":
        print(f"video_ses: Babək ({BABEK_VOICE}, {BABEK_RATE}) — {len(parts)} hissə, {len(g)} qrup, {voice.calls} səsləndirmə", file=sys.stderr)
        return
    print(f"video_ses: SARA — {len(parts)} hissə, {len(g)} qrup ({sum(len(x) - 1 for x in g)} sərhəd cümlənin içində); "
          f"modelin müddətləri {voice.used['müddət']}/{voice.used['müddət'] + voice.used['pay']} səsləndirmədə alındı; "
          f"cümlə içində {len(qoyulan)} nəfəs qoyuldu, {len(nefes) - len(qoyulan)} buraxıldı; "
          f"{getattr(voice, 'capped', 0)} hərf {LETTER_MAX} kadra qısaldıldı", file=sys.stderr)


if __name__ == "__main__":
    if len(sys.argv) != 4:
        sys.exit("İşlədilmə: video_ses.py <hissələr.json> <çıxış.wav> <vaxtlar.json>")
    main(*sys.argv[1:])
