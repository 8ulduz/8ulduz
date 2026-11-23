"""SARA səs modeli üçün Azərbaycan mətninin hazırlanması (sahib, 2026-11-08: «sara»; 2026-11-23: «tam normal insan kimi oxunsun»).

SARA (BHOSAI/SARA_TTS, VITS) yalnız kiçik Azərbaycan hərflərini, boşluğu və tireni tanıyır: rəqəm, faiz, valyuta, tarix,
böyük hərf və durğu işarələri modelə çatmazdan əvvəl sözə çevrilməlidir, yoxsa səssizcə buraxılır («2-1» hesabı, «15%»,
«7 noyabr 2026» eşidilməz). Durğu işarələri cümlə/hissə sərhədidir: server hər hissəni ayrıca səsləndirib arasına fasilə qoyur.

İnsan kimi oxunuş üçün (2026-11-23):
  - qısaltma hərf-hərf oxunur: «ABŞ-nin» → «a-be-şenin», «FHN» → «fe-he-en»; söz kimi oxunanlar (NATO, UEFA) söz qalır;
  - rəqəmin şəkilçisi rəqəmə yapışır: «21-də» → «iyirmi birdə», «18:00-dək» → «on səkkizədək», «29-na» → «iyirmi doqquza»;
  - sayt adı və inisial cümləni bölmür: «Modern.az» → «modern nöqtə az», «S.Orucov» → «es orucov»;
  - rum rəqəmi sıra sayıdır: «XII əsr» → «on ikinci əsr»; «+12°…+17°» → «on iki-on yeddi dərəcə»;
  - cümlə bütöv səslənir (vergüldə bölmək aydınlığı azaldır — Whisper ölçməsi); çox uzun cümlə vergüldə bölünür;
  - qısaltma, xarici ad: əvvəl oxunuş lüğəti (ses-lugat.json), sonra qaydalar.
"""
import json
import os
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

UP = "A-ZÇƏĞIİÖŞÜ"          # Azərbaycan böyük hərfləri (Latın + ç ə ğ ı/İ ö ş ü)
LO = "a-zçəğıiöşü"
SP = "\N{NO-BREAK SPACE}\N{NARROW NO-BREAK SPACE}"  # rəqəm qruplarında işlənən boşluqlar
VOWELS = set("aıoueəiöü")
BACK = set("aıou")

# Hərflərin adı (qısaltma hərf-hərf oxunanda): ABŞ → a-be-şe, FHN → fe-he-en.
LETTERS = {"a": "a", "b": "be", "c": "ce", "ç": "çe", "d": "de", "e": "e", "ə": "ə", "f": "fe", "g": "ge", "ğ": "ğe",
           "h": "he", "x": "xe", "ı": "ı", "i": "i", "j": "je", "k": "ka", "q": "qe", "l": "el", "m": "em", "n": "en",
           "o": "o", "ö": "ö", "p": "pe", "r": "er", "s": "es", "ş": "şe", "t": "te", "u": "u", "ü": "ü", "v": "ve",
           "y": "ye", "z": "ze", "w": "dubl ve"}
# Qısaltmanın oxunuşu (kiçik hərflə). Burada olmayan 2–3 hərfli qısaltma hərf-hərf, uzun və oxunaqlı olan söz kimi oxunur.
ACRONYMS = {
    "nato": "nato", "uefa": "uefa", "fifa": "fifa", "socar": "sokar", "azal": "azal", "opec": "opek", "tass": "tass",
    "apa": "apa", "yap": "yap", "covid": "kovid", "unesco": "yunesko", "unicef": "yunisef", "nasa": "nasa", "xin": "xin",
    "din": "din", "cop": "kop", "asan": "asan", "kvan": "kvan", "sima": "sima", "azərtac": "azərtac", "azertac": "azərtac",
    "cnn": "si-en-en", "bbc": "bi-bi-si", "aiib": "a-i-i-be", "noaa": "en-o-a-a", "eevza": "e-e-ve-ze-a", "usa": "yu-es-ey",
    "ok": "okey", "pr": "piar", "it": "ay-ti", "sms": "es-em-es", "gps": "ci-pi-es", "vip": "vip", "dj": "di-cey",
}
# Böyük hərflə yazılmış qısa Azərbaycan sözləri (başlıqda vurğu üçün: «BU», «VƏ», «BEŞ») — qısaltma deyil, söz kimi oxunur.
SHORT_WORDS = set("""a ə o u bu o nə kim var yox son ilk hər biz siz onu ona bəs ya da də ki mən sən gün ay il su od yol ev baş göz
əl qan can tez çox az üç iki bir on beş ana ata qız ər ad yaş iş dil şər xoş pis isti qar buz yağ dağ daş bağ qol ayaq ölü
yeni sağ sol ağ boz göy qəm dəm vay oh ah hə yox biz ilə ola oldu ki və qaz vaz ram ege yaz qış""".split())
# Tez-tez gələn xarici sözlər Azərbaycan oxunuşu ilə (kiçik hərflə). Qalan «w»-lu sözə sadə qayda (foreign) işləyir.
FOREIGN = {
    "google": "qugl", "youtube": "yutub", "whatsapp": "vatsap", "instagram": "instaqram", "facebook": "feysbuk",
    "iphone": "ayfon", "ipad": "aypad", "apple": "eppl", "microsoft": "maykrosoft", "windows": "vindovs",
    "washington": "vaşinqton", "trump": "tramp", "news": "nyus", "bloomberg": "blumberq", "wall": "uoll",
    "street": "strit", "reels": "rils", "photos": "fotos", "group": "qrup", "steel": "stil", "philadelphia": "filadelfiya",
    "milwaukee": "miluoki", "bucks": "baks", "anthropic": "entropik", "telegram": "teleqram", "twitter": "tvitter",
    "tiktok": "tiktok", "openai": "open ay ay", "chatgpt": "çat ci-pi-ti", "samsung": "samsunq", "huawei": "huavey",
    "playstation": "pleysteyşn", "netflix": "netfliks", "nvidia": "nvidiya", "manchester": "mançester",
    "chelsea": "çelsi", "liverpool": "liverpul", "barcelona": "barselona", "juventus": "yuventus", "psj": "pe-es-je",
    "airways": "eyrveyz", "online": "onlayn", "show": "şou",
}
DOMAIN_TLD = {"com": "kom", "gov": "qov", "org": "orq", "edu": "edu", "net": "net", "info": "info", "io": "ay-o"}
ROMAN = {"I": 1, "V": 5, "X": 10, "L": 50, "C": 100}

# Oxunuş lüğəti (.github/scripts/ses-lugat.cjs): qısaltmalar və orijinal yazılışlı xarici adlar, söz → oxunuş. Repodakı baxılmış
# ses-lugat.json üstündür; ses-lugat-elave.json — «ses-lugat» budağından həftəlik əlavələr (video işi və server özü gətirir),
# yalnız yeni söz verir. Lüğət qaydalardan (ACRONYMS, FOREIGN, hərf-hərf) əvvəl yoxlanır.
LEXICON_FILES = ("ses-lugat.json", "ses-lugat-elave.json")
LEXICON = {}


def load_lexicon(folder=None):
    folder = folder or os.path.dirname(os.path.abspath(__file__))
    words = {}
    for name in reversed(LEXICON_FILES):                      # əlavə əvvəl, baza onun üstünə yazılır
        try:
            with open(os.path.join(folder, name), encoding="utf-8") as f:
                data = json.load(f)
        except (OSError, ValueError):
            continue
        for k, v in (data.get("sozler") or {}).items() if isinstance(data, dict) else []:
            if isinstance(k, str) and isinstance(v, str) and v.strip() and set(v) <= ALLOWED:
                words[k] = v.strip()
    LEXICON.clear()
    LEXICON.update(words)
    return len(words)


def upper_az(text):
    return text.replace("i", "İ").replace("ı", "I").upper()


def lexicon_word(token):
    """Lüğətdəki oxunuş: dəqiq forma (ABŞ, Google) və başlıqdakı böyük yazılış (GOOGLE → Google). Əksinə axtarılmır:
    cümlə başındakı «Din» sözü «DİN» qısaltması sayılmasın."""
    if token in LEXICON:
        return LEXICON[token]
    if len(token) > 1 and token == upper_az(token) and token != lower_az(token):
        return LEXICON.get(token[0] + lower_az(token[1:]))
    return None


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


def _last_vowel(word):
    for ch in reversed(word):
        if ch in VOWELS:
            return ch
    return "ə"


def attach(word, suffix, harmony=False):
    """Şəkilçini oxunan sözə yapışdırır: «iyirmi bir» + «də» → «iyirmi birdə».
    Yazıda rəqəmdən sonra şəkilçi qısa yazılır, oxunuşda düzəlir:
      - «-dək» yönlük halı istəyir: 18-dək → on səkkizədək, 20-dək → iyirmiyədək;
      - samitlə bitən sözdə «n» ilə başlayan şəkilçinin «n»-i düşür: 10-nun → onun, 29-na → iyirmi doqquza;
      - saitlə bitən sözdə saitlə başlayan şəkilçidən əvvəl «y» gəlir: 2-ə → ikiyə.
    harmony=True (qısaltma): yazan şəkilçini «abş» kimi yazıb, oxunuş «a-be-şe»-dir — saitlər oxunuşa uyğunlaşır.
    Rəqəmdə yazan şəkilçini onsuz da oxunuşa görə yazır («10-illik» → «onillik», ahəng toxunulmur)."""
    suffix = lower_az(suffix)
    if not suffix:
        return word
    end = word[-1:]
    if suffix.startswith(("dək", "dəkki")):
        dat = "a" if _last_vowel(word) in BACK else "ə"
        return word + ("y" if end in VOWELS else "") + dat + suffix
    if end not in VOWELS and len(suffix) > 1 and suffix[0] == "n" and suffix[1] in VOWELS:
        suffix = suffix[1:]
    elif harmony and end in VOWELS and suffix[0] in "ıiuü":
        suffix = "n" + suffix            # ABŞ-ın → a-be-şenin, ABŞ-ı → a-be-şeni
    elif end in VOWELS and suffix[0] in VOWELS:
        suffix = "y" + suffix            # 2-ə → ikiyə, ABŞ-a → a-be-şeyə
    return word + (harmonize(word, suffix) if harmony else suffix)


INVARIANT = ("ki", "kən", "dək", "sa", "sə", "ca", "cə")


def harmonize(word, suffix):
    """Şəkilçinin saitlərini oxunan sözün son saitinə uyğunlaşdırır (ahəng qanunu): yazıda «ABŞ-da» (abş kimi),
    oxunuşda «a-be-şedə»; «2026-da» → «iki min iyirmi altıda». a/ə iki, ı/i/u/ü dörd variantlıdır."""
    if suffix.startswith(INVARIANT):
        return suffix
    last = _last_vowel(word)
    out = []
    for ch in suffix:
        if ch in "aə":
            ch = "a" if last in BACK else "ə"
        elif ch in "ıiuü":
            ch = {"a": "ı", "ı": "ı", "o": "u", "u": "u", "e": "i", "ə": "i", "i": "i", "ö": "ü", "ü": "ü"}[last]
        if ch in VOWELS:
            last = ch
        out.append(ch)
    return "".join(out)


def roman_value(s):
    """XII → 12; düzgün rum rəqəmi deyilsə None (yalnız I V X L C; «CD», «MD» qısaltma sayılır)."""
    if not s or any(c not in ROMAN for c in s):
        return None
    total, prev = 0, 0
    for c in reversed(s):
        v = ROMAN[c]
        total = total - v if v < prev else total + v
        prev = max(prev, v)
    canon = ""
    n = total
    for v, sym in [(100, "C"), (90, "XC"), (50, "L"), (40, "XL"), (10, "X"), (9, "IX"), (5, "V"), (4, "IV"), (1, "I")]:
        while n >= v:
            canon += sym
            n -= v
    return total if canon == s and 0 < total < 40 else None


def spell(token):
    """Hərf-hərf: «abş» → «a-be-şe»."""
    return "-".join(LETTERS.get(c, c) for c in token)


def pronounceable(word):
    """Uzun böyük hərfli sözü söz kimi oxumaq olarmı: sait var və üç samit dalbadal deyil (FOTO, SİYAHI, NATO — bəli;
    KXDR, ESPN, DSMF — yox)."""
    vowels = sum(c in VOWELS for c in word)
    if not vowels:
        return False
    run = best = 0
    for c in word:
        run = 0 if c in VOWELS else run + 1
        best = max(best, run)
    if best >= 3 and vowels <= 1:
        return False
    onset = re.match(r"[^aıoueəiöü]+", word)
    if onset and len(onset.group(0)) >= 2 and onset.group(0)[:2] not in {"tr", "dr", "kr", "qr", "pr", "br", "fr", "st", "sp", "sk", "kl", "pl", "bl", "fl", "kv", "sm", "sn", "şt", "sv", "tv"}:
        return False
    return True


def acronym(token):
    """Böyük hərfli söz necə oxunur: rum rəqəmi → sıra sayı, lüğətdə olan → lüğətdəki kimi, qısa → hərf-hərf,
    uzun və oxunaqlı → söz kimi («VİDEO», «SİYAHI»)."""
    r = roman_value(token)
    if r and len(token) >= 2:
        return ordinal_words(r)
    low = lower_az(token)
    for key in (low, low.replace("ı", "i")):   # ingilis qısaltmasında «I» nöqtəlidir: COVID → covid
        if key in ACRONYMS:
            return ACRONYMS[key]
        if key in FOREIGN:
            return FOREIGN[key]
    if low in SHORT_WORDS:
        return low
    if len(low) <= 3 or not pronounceable(low):
        return spell(low)
    return low


def foreign(word):
    """Xarici (ingilis) söz Azərbaycan oxunuşu ilə: əvvəlcə lüğət, sonra «w»-lu sözlər üçün sadə qayda
    (sh → ş, ch → ç, th → t, ph → f, ck → k, oo → u, ee → i, w → v). Azərbaycan sözündə «w» olmur, ona görə qayda
    yalnız «w»-lu sözə işləyir; qalan Latın sözlər olduğu kimi oxunur."""
    low = lower_az(word)
    for key in (low, low.replace("ı", "i")):
        if key in FOREIGN:
            return FOREIGN[key]
    if "w" not in low:
        return word
    s = low
    for a, b in [("sh", "ş"), ("ch", "ç"), ("th", "t"), ("ph", "f"), ("ck", "k"), ("oo", "u"), ("ee", "i"), ("wh", "v"), ("w", "v")]:
        s = s.replace(a, b)
    return s


# Rəqəmə/qısaltmaya tire (və ya apostrof) ilə yazılan şəkilçi: «21-də», «ABŞ-nin», «Trump’ın».
SUFFIX = rf"(?:-|[’'])([{LO}]+)\b"
# Şəkilçi bu hərflərlə başlayır; «3-otaqlı», «5-mərtəbəli», «3-günlük» kimi mürəkkəb sözlər yapışdırılmır.
SUFFIX_START = set("dnlysıiuüaətc")


NUMBER_WORDS = tuple(w for w in ONES + TENS + ["yüz", "min", "milyon", "milyard", "trilyon", "sıfır"] if w)


def glue(word, suffix, harmony=False):
    """Şəkilçi kimi görünürsə yapışdırır, yoxsa (mürəkkəb söz və ya sözə çevrilmiş rəqəmdir: «2026-2027-ci») tire ilə saxlayır."""
    if suffix[:1] in SUFFIX_START and len(suffix) <= 7 and not suffix.startswith(NUMBER_WORDS):
        return attach(word, suffix, harmony)
    return word + "-" + suffix


def is_foreign(word):
    low = lower_az(word)
    return low in FOREIGN or low.replace("ı", "i") in FOREIGN or "w" in low


def known_word(word, suffix):
    """Lüğət və ya xarici söz qaydası: oxunuş (şəkilçisi ilə) və ya None."""
    said = lexicon_word(word)
    if said is None and is_foreign(word):
        said = foreign(word)
    if said is None:
        return None
    return glue(said, suffix, True) if suffix else said


def _say_number(s):
    """Rəqəm yazısı sözlə: «21:45» → saat, «1,5» → kəsr, «2 500» / «2.500» → min, qalan → tam ədəd."""
    m = re.fullmatch(r"(\d{1,2}):(\d{2})", s)
    if m:
        h, mi = int(m.group(1)), int(m.group(2))
        return f"{number_words(h)} {number_words(mi) if mi else ''}".strip()
    if re.fullmatch(rf"\d{{1,3}}(?:[ {SP}.]\d{{3}})+", s):
        return number_words(int(re.sub(rf"[ {SP}.]", "", s)))
    m = re.fullmatch(r"(\d+)[.,](\d{1,3})", s)
    if m:
        return decimal_words(m.group(1), m.group(2))
    return number_words(int(s)) if len(s) <= 15 else " ".join(number_words(int(d)) for d in s)


def verbalize(text):
    """Rəqəmlər, tarixlər, saat, faiz, valyuta, sıra sayları, qısaltma, sayt adı və inisiallar sözə çevrilir;
    nəticə hələ böyük hərf və durğu saxlayır."""
    t = re.sub(f"[{SP}]", " ", text)
    # Mənbə saytlarının qalığı: «[…]» və xülasə sonundakı «Source» oxunmur.
    t = re.sub(r"\s*\[(?:…|\.\.\.)\]", " ", t)
    t = re.sub(r"(?:^|\s)Source\s*$", "", t)
    # 07.11.2026 → 7 noyabr 2026
    t = re.sub(r"\b(\d{1,2})[./](\d{1,2})[./](\d{4})\b",
               lambda m: f"{int(m.group(1))} {MONTHS[int(m.group(2)) - 1]} {m.group(3)}" if 1 <= int(m.group(2)) <= 12 else m.group(0), t)
    # Sayt ünvanı cümləni bölməsin: https://www.Modern.az → modern nöqtə az; «edib.Gundelik.az» (boşluqsuz cümlə sonu) əvvəl ayrılır.
    t = re.sub(r"https?://\S+", " ", t)                     # tam keçid (şəkil, səhifə) oxunmur
    t = re.sub(rf"\b([{LO}]{{2,}})\.([{UP}][{LO}A-Za-z0-9]+\.(?:az|com|ru|org|net|tr|info)\b)", r"\1. \2", t)
    t = re.sub(r"(?i)\bwww\.", "", t)
    t = re.sub(rf"(?i)\b((?:[{LO}0-9-]+\.)+)(az|com|ru|org|net|gov|tr|edu|io|info|tv|uk|de|ge|ua|kz)\b(?:{SUFFIX})?",
               lambda m: glue(" nöqtə ".join(DOMAIN_TLD.get(x.lower(), x) for x in m.group(1).rstrip(".").split(".") + [m.group(2)]), m.group(3), True)
               if m.group(3) else " nöqtə ".join(DOMAIN_TLD.get(x.lower(), x) for x in m.group(1).rstrip(".").split(".") + [m.group(2)]), t)
    # İnisial: S.Orucov → es Orucov (nöqtə cümlə sonu deyil)
    t = re.sub(rf"\b([{UP}])\.\s?(?=[{UP}][{LO}])", lambda m: spell(lower_az(m.group(1))) + " ", t)
    # Hərf+rəqəm bitişik: COP31 → COP 31, 8ulduz → 8 ulduz, M1 → M 1
    t = re.sub(rf"(?<=[{UP}{LO}A-Za-z])(?=\d)", " ", t)
    t = re.sub(rf"\b(\d+)([{LO}]{{3,}})\b", lambda m: m.group(0) if re.fullmatch(r"(?:ci|cı|cu|cü|nci|ncı|ncu|ncü|inci|ıncı|uncu|üncü)", m.group(2)) else f"{m.group(1)} {m.group(2)}", t)
    # 1 654,23 → bir min altı yüz əlli dörd tam yüzdə iyirmi üç (qruplu tam hissə + kəsr)
    t = re.sub(rf"\b(\d{{1,3}}(?:[ {SP}]\d{{3}})+),(\d{{1,3}})\b", lambda m: decimal_words(re.sub(rf"[ {SP}]", "", m.group(1)), m.group(2)), t)
    # Oxunuş lüğəti və xarici sözlər, şəkilçisi ilə: Washington-da → vaşinqtonda, Trump’ın → trampın, ABŞ-nin → a-be-şenin
    t = re.sub(rf"\b([{UP}{LO}A-Za-z]+)(?:{SUFFIX})?", lambda m: known_word(m.group(1), m.group(2)) or m.group(0), t)
    # CamelCase: AzTV → Az TV, İnterPress → İnter Press
    t = re.sub(rf"(?<=[{LO}])(?=[{UP}])", " ", t)
    # Qısaltma + şəkilçi (rəqəmlərdən əvvəl: «COVID-19»-da rəqəm sözü şəkilçi sayılmasın): ABŞ-nin → a-be-şenin, NATO-ya → natoya
    t = re.sub(rf"\b([{UP}]{{2,7}}){SUFFIX}", lambda m: glue(acronym(m.group(1)), m.group(2), True), t)
    # Temperatur: +12°…+17° → 12-17 dərəcə; −5° → mənfi 5 dərəcə. «°»-dən sonrakı boşluq yalnız «C» gələndə udulur
    # (2026-11-23: «+17° olacaq» → «dərəcəolacaq» idi).
    t = re.sub(r"([+−-]?)(\d+)\s*°(?:\s*C\b)?\s*(?:…|\.\.\.|–|—|-)\s*([+−-]?)(\d+)\s*°(?:\s*C\b)?",
               lambda m: f"{'mənfi ' if m.group(1) in '−-' and m.group(1) else ''}{m.group(2)}-{'mənfi ' if m.group(3) in '−-' and m.group(3) else ''}{m.group(4)} dərəcə", t)
    t = re.sub(r"(?<![\w\d])[−-](\d+)\s*°(?:\s*C\b)?", r"mənfi \1 dərəcə", t)
    t = re.sub(r"\+?(\d+)\s*°(?:\s*C\b)?", r"\1 dərəcə", t)
    # %15, 15% → on beş faiz; 15%-ə → on beş faizə
    t = re.sub(r"%\s?(\d+(?:[.,]\d+)?)", r"\1%", t)
    t = re.sub(rf"(\d+(?:[.,]\d+)?)\s?%(?:{SUFFIX})?", lambda m: attach(_say_number(m.group(1)) + " faiz", m.group(2) or ""), t)
    # $100, ₼5 → 100 dollar
    t = re.sub(r"([$€£₼₽])\s?(\d[\d .,]*\d|\d)", r"\2 \1", t)
    # 11-ci, 3-cü, 2-nci → sıra sayı
    t = re.sub(r"\b(\d+)\s?-?\s?(?:ci|cı|cu|cü|nci|ncı|ncu|ncü|inci|ıncı|uncu|üncü)\b", lambda m: ordinal_words(int(m.group(1))), t)
    # 21-də, 18:00-dək, 1,5-ə, 2 500-dən → rəqəm sözlə + şəkilçi yapışıq
    t = re.sub(rf"\b(\d{{1,2}}:\d{{2}}|\d{{1,3}}(?:[ {SP}.]\d{{3}})+|\d+[.,]\d{{1,3}}|\d+){SUFFIX}",
               lambda m: glue(_say_number(m.group(1)), m.group(2)), t)
    # 19:30 → on doqquz otuz
    t = re.sub(r"\b(\d{1,2}):(\d{2})\b", lambda m: _say_number(m.group(0)), t)
    # 1,5 / 1.70 (2-3 rəqəmli kəsr) → kəsr; 1.500 / 1 500 (3-lü qruplar) → min
    t = re.sub(rf"\b\d{{1,3}}(?:[ {SP}.]\d{{3}})+(?![.,]?\d)", lambda m: _say_number(m.group(0)), t)
    t = re.sub(r"\b(\d+)[.,](\d{1,3})\b", lambda m: decimal_words(m.group(1), m.group(2)), t)
    t = re.sub(r"\d+", lambda m: _say_number(m.group(0)), t)
    t = re.sub(r"\s*([%₼$€£₽])", lambda m: " " + UNITS[m.group(1)], t)
    t = re.sub(r"\b(AZN|USD|EUR|azn|usd|eur|km|kq|kg|mln|mlrd|sm|mm)\b", lambda m: WORD_UNITS[m.group(1).lower()], t)
    t = re.sub(r"\s*°\s*C\b", " dərəcə", t)
    t = t.replace("№", " nömrə ").replace("&", " və ")
    # Tək böyük hərfli sözlər (ABŞ, FHN, XII, VİDEO)
    t = re.sub(rf"\b[{UP}]{{2,}}\b", lambda m: acronym(m.group(0)), t)
    return t


def for_voice(text, hyphens=True):
    """Saytın «Dinlə» səsi (Babək: .github/scripts/ses.py və ses-worker) üçün mətn: verbalize qaydaları (rəqəm, qısaltma,
    sayt, lüğət), amma durğu və böyük hərf qalır — o səs intonasiyanı onlardan qurur. hyphens=False: sözün içindəki tire
    boşluq olur («a-be-şenin» → «a be şenin»)."""
    t = verbalize(text)
    if not hyphens:
        t = re.sub(rf"(?<=[{LO}])-(?=[{LO}])", " ", t)
    return re.sub(r"\s+", " ", t).strip()


# Cümlə sonu: nöqtə/nida/sual/üç nöqtə, sonra (dırnaq/mötərizə ola bilər) boşluq və ya mətn sonu.
SENT_END = re.compile(r"(?<=[.!?…])[\"»”)\]]*\s+")
# Cümlə içində nəfəs yeri: vergül, nöqtəli vergül, iki nöqtə, boşluqlu tire, mötərizə.
CLAUSE = re.compile(r"(?<=[,;:])\s+|\s+[–—-]\s+|\s*[()]\s*")
PAUSE_CLAUSE = 0.16
PAUSE_SENTENCE = 0.38


def phrases(text, max_len=220, commas=False):
    """Mətn səsləndirmə hissələrinə bölünür: cümlə sonu uzun fasilə; max_len-dən uzun cümlə vergül/iki nöqtə/tiredə bölünür.
    commas=True: hər vergüldə bölünür. Whisper ölçməsi (2026-11-23, iki dəfə) göstərdi ki, bu aydınlığı azaldır: hərf xətası
    11,4% (bölünəndə) / 10,0% (bölünməyəndə). Model vergülü tanımır, hər qısa parçanı ayrıca cümlə kimi bitirir.
    Qaytarır: [(model mətni, fasilə saniyəsi)]."""
    out = []
    for sentence in SENT_END.split(verbalize(text).strip()):
        sentence = sentence.strip()
        if not sentence:
            continue
        parts = CLAUSE.split(sentence) if commas or len(sentence) > max_len else [sentence]
        parts = [p for p in parts if p and p.strip()]
        for i, part in enumerate(parts):
            said = re.sub(r"\s+", " ", fold(lower_az(part))).strip(" -")
            said = re.sub(r"\s*-\s*-+\s*", "-", said)
            if said:
                out.append((said, PAUSE_CLAUSE if i < len(parts) - 1 else PAUSE_SENTENCE))
    return out


# Səs modelinin oxuma ayarları (VITS): noise_scale — tələffüzün dəyişkənliyi (az → aydın, çox az → robot kimi),
# noise_scale_duration — ritmin dəyişkənliyi, speaking_rate — sürət (1 — modelin öz sürəti). ses_yoxla.py ilə seçilib:
# 2026-11-23, 81 cümlə, Whisper large-v3 hərf xətası — modelin öz ayarı (0,667/0,8) 14,2%, 0,45/0,6 — 11,1%, 0,92 sürət — 12,4%.
VOICE = {"noise_scale": 0.45, "noise_scale_duration": 0.6, "speaking_rate": 1.0}


def tune(model, **over):
    """Modelə VOICE ayarlarını tətbiq edir (VitsModel bu sahələri forward-da oxuyur)."""
    for k, v in {**VOICE, **over}.items():
        setattr(model, k, v)
    return model


load_lexicon()
