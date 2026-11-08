"""SARA səs modeli üçün Azərbaycan mətninin hazırlanması (sahib, 2026-11-08: «sara»).

SARA (BHOSAI/SARA_TTS, VITS) yalnız kiçik Azərbaycan hərflərini, boşluğu və tireni tanıyır: rəqəm, faiz, valyuta, tarix,
böyük hərf və durğu işarələri modelə çatmazdan əvvəl sözə çevrilməlidir, yoxsa səssizcə buraxılır («2-1» hesabı, «15%»,
«7 noyabr 2026» eşidilməz). Durğu işarələri cümlə/hissə sərhədidir: server hər hissəni ayrıca səsləndirib arasına fasilə qoyur.
"""
import re
import unicodedata

ONES = ["", "bir", "iki", "üç", "dörd", "beş", "altı", "yeddi", "səkkiz", "doqquz"]
TENS = ["", "on", "iyirmi", "otuz", "qırx", "əlli", "altmış", "yetmiş", "səksən", "doxsan"]
SCALES = [(10 ** 12, "trilyon"), (10 ** 9, "milyard"), (10 ** 6, "milyon"), (1000, "min")]
MONTHS = ["yanvar", "fevral", "mart", "aprel", "may", "iyun", "iyul", "avqust", "sentyabr", "oktyabr", "noyabr", "dekabr"]
# Sıra sayı şəkilçisi son sözə görə (on bir → on birinci, iyirmi → iyirminci).
ORDINAL = {"bir": "birinci", "iki": "ikinci", "üç": "üçüncü", "dörd": "dördüncü", "beş": "beşinci", "altı": "altıncı",
           "yeddi": "yeddinci", "səkkiz": "səkkizinci", "doqquz": "doqquzuncu", "on": "onuncu", "iyirmi": "iyirminci",
           "otuz": "otuzuncu", "qırx": "qırxıncı", "əlli": "əllinci", "altmış": "altmışıncı", "yetmiş": "yetmişinci",
           "səksən": "səksəninci", "doxsan": "doxsanıncı", "yüz": "yüzüncü", "min": "mininci", "milyon": "milyonuncu",
           "milyard": "milyardıncı", "trilyon": "trilyonuncu", "sıfır": "sıfırıncı"}
UNITS = {"%": "faiz", "₼": "manat", "$": "dollar", "€": "avro", "£": "funt", "₽": "rubl"}
WORD_UNITS = {"azn": "manat", "usd": "dollar", "eur": "avro", "km": "kilometr", "kq": "kiloqram", "kg": "kiloqram",
              "mln": "milyon", "mlrd": "milyard", "min.": "min", "sm": "santimetr", "mm": "millimetr", "°c": "dərəcə"}
ALLOWED = set("abcçdeəfgğhxıijkqlmnoöprsştuüvyz -")


def under_thousand(n):
    h, r = divmod(n, 100)
    t, o = divmod(r, 10)
    words = []
    if h:
        words += ([] if h == 1 else [ONES[h]]) + ["yüz"]
    if t:
        words.append(TENS[t])
    if o:
        words.append(ONES[o])
    return words


def number_words(n):
    """Tam ədəd sözlə: 2026 → «iki min iyirmi altı», 1000 → «min», 1500000 → «bir milyon beş yüz min»."""
    if n == 0:
        return "sıfır"
    words = []
    for value, name in SCALES:
        q, n = divmod(n, value)
        if q:
            words += ([] if q == 1 and name == "min" else (number_words(q).split())) + [name]
    words += under_thousand(n)
    return " ".join(words)


def ordinal_words(n):
    words = number_words(n).split()
    words[-1] = ORDINAL.get(words[-1], words[-1])
    return " ".join(words)


def decimal_words(whole, frac):
    """1,5 → «bir tam onda beş»; 1,70 → «bir tam yüzdə yetmiş»."""
    denom = {1: "onda", 2: "yüzdə", 3: "mində"}.get(len(frac))
    if not denom:
        return number_words(int(whole)) + " " + " ".join(number_words(int(d)) for d in frac)
    return f"{number_words(int(whole))} tam {denom} {number_words(int(frac))}"


def lower_az(text):
    """Azərbaycan böyük/kiçik hərf qaydası: I → ı, İ → i (Pythonun lower() «I»-ni «i» edir)."""
    return text.replace("I", "ı").replace("İ", "i").lower()


def fold(text):
    """Modelin tanımadığı hərflər ən yaxın Azərbaycan hərfinə (é → e, w → v, ä → ə), qalanı boşluq."""
    out = []
    for ch in text:
        if ch in ALLOWED:
            out.append(ch)
            continue
        base = {"w": "v", "ä": "ə", "â": "a", "î": "i", "û": "u", "–": "-", "—": "-", "'": "", "’": "", "`": "", "«": "", "»": "", "“": "", "”": "", '"': "", "„": ""}.get(ch)
        if base is None:
            base = "".join(c for c in unicodedata.normalize("NFKD", ch) if not unicodedata.combining(c))
            base = base if base and all(c in ALLOWED for c in base) else " "
        out.append(base)
    return "".join(out)


def _num(m):
    return number_words(int(re.sub(r"[ . ]", "", m.group(0))))


def verbalize(text):
    """Rəqəmlər, tarixlər, saat, faiz, valyuta və sıra sayları sözə çevrilir; nəticə hələ böyük hərf və durğu saxlayır."""
    t = text
    # 07.11.2026 → 7 noyabr 2026
    t = re.sub(r"\b(\d{1,2})[./](\d{1,2})[./](\d{4})\b",
               lambda m: f"{int(m.group(1))} {MONTHS[int(m.group(2)) - 1]} {m.group(3)}" if 1 <= int(m.group(2)) <= 12 else m.group(0), t)
    # 19:30 → on doqquz otuz
    t = re.sub(r"\b(\d{1,2}):(\d{2})\b", lambda m: f"{number_words(int(m.group(1)))} {number_words(int(m.group(2))) if int(m.group(2)) else ''}".strip(), t)
    # %15, 15% → on beş faiz
    t = re.sub(r"%\s?(\d+(?:[.,]\d+)?)", r"\1%", t)
    # $100, ₼5 → 100 dollar
    t = re.sub(r"([$€£₼₽])\s?(\d[\d .,]*\d|\d)", r"\2 \1", t)
    # 11-ci, 3-cü, 2-nci → sıra sayı
    t = re.sub(r"\b(\d+)\s?-?\s?(?:ci|cı|cu|cü|nci|ncı|ncu|ncü|inci|ıncı|uncu|üncü)\b", lambda m: ordinal_words(int(m.group(1))), t)
    # 1,5 / 1.70 (2-3 rəqəmli kəsr) → kəsr; 1.500 / 1 500 (3-lü qruplar) → min
    t = re.sub(r"\b\d{1,3}(?:[ . ]\d{3})+(?![.,]?\d)", _num, t)
    t = re.sub(r"\b(\d+)[.,](\d{1,3})\b", lambda m: decimal_words(m.group(1), m.group(2)), t)
    t = re.sub(r"\d+", lambda m: number_words(int(m.group(0))) if len(m.group(0)) <= 15 else " ".join(number_words(int(d)) for d in m.group(0)), t)
    t = re.sub(r"\s*([%₼$€£₽])", lambda m: " " + UNITS[m.group(1)], t)
    t = re.sub(r"\b(AZN|USD|EUR|azn|usd|eur|km|kq|kg|mln|mlrd|sm|mm)\b", lambda m: WORD_UNITS[m.group(1).lower()], t)
    t = re.sub(r"\s*°\s*C\b", " dərəcə", t)
    return t


def phrases(text, max_len=220):
    """Mətn səsləndirmə hissələrinə bölünür: cümlə sonu uzun, vergül/iki nöqtə qısa fasilə.
    Qaytarır: [(model mətni, fasilə saniyəsi)]."""
    out = []
    for sentence in re.findall(r"[^.!?…]+[.!?…]*", verbalize(text)):
        parts = re.split(r"(?<=[,;:])\s+", sentence.strip()) if len(sentence) > max_len else [sentence.strip()]
        for i, part in enumerate(parts):
            said = re.sub(r"\s+", " ", fold(lower_az(part))).strip(" -")
            if said:
                out.append((said, 0.18 if i < len(parts) - 1 else 0.35))
    return out
