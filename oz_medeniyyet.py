"""8ulduz-un öz xəbərləri, mərhələ 2: mədəniyyət və bilik (sahib, 2026-11-10: «Mərhələ 2-ni qur»). Sayta hələ qoşulmayıb.

Şablon xəbərlərdir, süni intellekt yoxdur: hər ad, rəqəm və tarix mənbənin öz cavabındandır.

1. «Günün afişası» (hər gün 10:00, cümədən başqa). iTicket-in açıq API-sindən bu günün tamaşa və konsertləri, yalnız
   Bakının dövlət teatrları və konsert salonlarında (adla seçilir: tədbirdə yalnız məkanın adı var). 3–6 tədbir: ad «»
   içində, məkan, saat. Qiymət, «şam işığında» kimi kommersiya seriyaları və kiril adlı tamaşalar yazılmır. 3-dən az
   tədbir varsa xəbər yoxdur.
2. «Həftəsonu afişası» (cümə 12:00): şənbə və bazarın tamaşa, konsert və muzey sərgiləri. Cümə günü gündəlik afişa
   verilmir (planın qaydası: gündə bir afişa).
3. «Həftənin kino premyeraları» (çərşənbə 12:00): CineMastercard-ın «Tezliklə» siyahısından sabah (cümə axşamı)
   ekrana çıxan filmlər, dili ilə (yaş həddi yazılmır: kartdakı hədd buraxılış günü dəyişə bilir). Tapşırıqda cümə axşamı 11:00 yazılıb, amma sayt filmi buraxılış günü
   «Tezliklə»dən çıxarır: web.archive.org-un 2026-03-05 11:44 və 2026-09-03 03:13 (cümə axşamı) nüsxələrində həmin
   günün filmləri yoxdur, 2026-01-07 17:29 (çərşənbə) nüsxəsində sabahkı filmlər tarixləri ilə var; canlı səhifədə də
   belədir (12.11.2026, cümə axşamı: 12.11 filmləri artıq tarixsiz «SEANSLAR» kartlarıdır). cinemaplus.az
   GitHub-dan 403 qaytarır, cinemastercard.az 200.
4. «Dünən Vikipediyada ən çox oxunanlar» (13:00; siyahı hazır deyilsə 15:00): az.wikipedia-nın «featured» lentinin
   «mostread» hissəsi, yalnız tarixi dünən olanda. Ana və xüsusi səhifələri lent özü çıxarır. Biz də çıxarırıq:
   18+ mövzular, rəhbərlik (ox.needs_owner başlıqda, təsvirdə və girişdə, üstəlik ailə adları), Azərbaycanın
   vəzifəli şəxsləri və siyasətçiləri, son bir ildə vəfat edənlər, cinayət və hadisə məqalələri (şübhədə də).
   Lentin girişlərində mötərizə (doğum və ölüm tarixi) olmur, ona görə süzgəcdən keçən ilk 12 məqalənin tam girişi
   ikinci sorğu ilə alınır və süzgəc bir də işləyir; girişi alınmayan məqalə yazılmır.
   İlk 5 məqalə baxış sayı ilə. «Ən çox» yalnız birinci yerdəki məqalə süzgəcdən keçibsə yazılır.
5. «Ayın ən çox oxunanları» (ayın 2-si 13:30; 2-si çərşənbə və ya cüməyə düşsə 1-i): Wikimedia pageviews API-nin
   aylıq siyahısı, ilk 20 məqalənin təsviri və girişi bir sorğu ilə alınır və eyni süzgəcdən keçir.
6. «Yubileylər» (09:00, tapılanda, gündə ən çox bir xəbər): Wikidata-da Azərbaycan vətəndaşı (Q227, Q130229,
   Q503586) olan, az.wikipedia məqaləsi olan və bu gün doğulan şəxslər, ildönümü 25-ə bölünən və 50-dən az olmayan.
   Siyasətçi və vəzifəli şəxslər (peşə, təsvir və ya P39) düşür. Gün səhifəsinin «Doğumlar» siyahısında olanlar düşür:
   onları «Bu gün tarixdə» xəbəri yazır (ox.WIKI_API + ox.tarix_parse). Doğum tarixi az.wikipedia girişində
   yoxlanır: Wikidata səhv ola bilər (Süleyman Rüstəm: Wikidata 27.11.1906, Vikipediya 12 mart 1906).
   Girişin mətni xəbərə köçürülmür: yalnız ad, peşə (Wikidata təsviri), doğum yeri və tarixlər yazılır.
   Sağ şəxsin girişində siyasət, müxalifət, məhkəmə və ya hadisə sözləri varsa, yubiley yazılmır.

Şəbəkə: hər sorğu yalnız `fetch` ilə gedir (timeout 15 s), hər xəbərin vaxt pəncərəsində (45 dəqiqə) və `done`-da
açarı yoxdursa. Sorğudan sonra, nəticəsi nə olursa olsun, xəbərin açarı qayıdır (xəbər yoxdursa worth=False və
«why» ilə): canlı onu done-a yazır və pəncərədə ikinci sorğu getmir. Yalnız Vikipediyanın 13:00 cəhdi siyahı hazır
olmayanda başqa açar («…-gozle») qaytarır ki, 15:00 cəhdi bağlanmasın. Sorğular gündə ən çox 10-dur: yubiley 1–3,
afişa 2–3 (cümə həftəsonu 5), kino 1 (çərşənbə), Vikipediya 2–3 (cümə və aylıq xəbərin günü tək cəhd, 15:00: 2),
aylıq 2 (çərşənbə və cüməyə düşmür).
Wikimedia hostlarına sorğu «8ulduz-bot/1.0 (+https://8ulduz.az)» User-Agent-i ilə gedir.

Sınaq: python oz_medeniyyet.py --sinaq --root DIR [--now 2026-11-10T09:00+04:00]
"""
import datetime
import html
import json
import pathlib
import re
import sys
import time
import urllib.parse

import oz_xeber as ox

BAKU = ox.BAKU
UTC = datetime.timezone.utc
DAY = datetime.timedelta(days=1)
MONTHS = ox.MONTHS
WEEKDAYS = ("bazar ertəsi", "çərşənbə axşamı", "çərşənbə", "cümə axşamı", "cümə", "şənbə", "bazar")
TOPIC = "mədəniyyət"
TITLE_MAX = 110
TIMEOUT = 15
WINDOW = datetime.timedelta(minutes=45)  # canlı dövrə 10–30 dəqiqədən birdir: 45 dəqiqəlik pəncərə buraxılmır
SLOT = {"yubiley": "09:00", "afisa": "10:00", "hefte": "12:00", "kino": "12:00", "vikipediya": "13:00", "vikipediya-ay": "13:30"}
WIKI_TRIES = ("13:00", "15:00")
WAIT = "-gozle"  # Vikipediyanın ilk cəhdi siyahı hazır olmayanda bu sonluqlu açar qaytarır (ikinci cəhd bağlanmasın)
WIKI_HEADERS = {"User-Agent": "8ulduz-bot/1.0 (+https://8ulduz.az)"}
SPARQL_HEADERS = {"User-Agent": WIKI_HEADERS["User-Agent"], "Accept": "application/sparql-results+json"}
JSON_HEADERS = {"Accept": "application/json"}


# --- Ümumi köməkçilər --------------------------------------------------------------------------------

def _now(now):
    if now is None:
        return datetime.datetime.now(BAKU)
    if isinstance(now, str):
        now = datetime.datetime.fromisoformat(now)
    if now.tzinfo is None:
        return now.replace(tzinfo=BAKU)
    return now.astimezone(BAKU)


def _due(now, hhmm):
    """now hhmm-dən başlayan pəncərədədirmi (WINDOW)."""
    h, m = (int(x) for x in hhmm.split(":"))
    start = now.replace(hour=h, minute=m, second=0, microsecond=0)
    return start <= now < start + WINDOW


def _err(e):
    code = getattr(e, "code", None)
    return f"{type(e).__name__}{' ' + str(code) if code else ''}"


def _low(s):
    return ox._low(s or "")


def _cap(s):
    if not s:
        return s
    return ("İ" if s[0] == "i" else s[0].upper()) + s[1:]


def _join(parts):
    """«A», «A və B», «A, B və C»."""
    parts = [p for p in parts if p]
    if len(parts) <= 1:
        return "".join(parts)
    return ", ".join(parts[:-1]) + " və " + parts[-1]


def _fit(options):
    """Uzunluğu TITLE_MAX-dan çox olmayan ilk başlıq (sonuncu həmişə qısadır)."""
    for t in options:
        if t and len(t) <= TITLE_MAX:
            return t
    return options[-1][:TITLE_MAX]


def _month_loc(month):
    """«oktyabrda», «apreldə»."""
    name = MONTHS[month - 1]
    return name + ("də" if month == 4 else "da")


def _day_abl(d):
    """«12 noyabrdan», «3 apreldən»."""
    return f"{d.day} {MONTHS[d.month - 1]}{'dən' if d.month == 4 else 'dan'}"


def _days_loc(a, b):
    """İki ardıcıl gün: «14 və 15 noyabrda», «31 oktyabr və 1 noyabrda»."""
    if a.month == b.month:
        return f"{a.day} və {ox.day_loc(b)}"
    return f"{ox.day_text(a)} və {ox.day_loc(b)}"


_UNITS = ("", "bir", "iki", "üç", "dörd", "beş", "altı", "yeddi", "səkkiz", "doqquz")
_TENS = ("", "on", "iyirmi", "otuz", "qırx", "əlli", "altmış", "yetmiş", "səksən", "doxsan")


def _num_word(n):
    """Ədədin oxunuşunun son sözü: şəkilçi ona görə seçilir (690 «altı yüz doxsan» -> doxsan)."""
    n = abs(int(n))
    if n == 0:
        return "sıfır"
    if n % 10:
        return _UNITS[n % 10]
    if n % 100:
        return _TENS[(n % 100) // 10]
    if n % 1000:
        return "yüz"
    if n % 1000000:
        return "min"
    return "milyon"


def num_abl(n):
    """Çıxışlıq hal: «70-dən», «690-dan», «1 066-dan»."""
    return f"{ox.az_num(n, 0)}-{'dan' if ox._last_vowel(_num_word(n)) in 'aıou' else 'dən'}"


def num_dat(n):
    """Yönlük hal: «690-a», «62-yə», «731-ə», «1 066-ya»."""
    w = _num_word(n)
    back = ox._last_vowel(w) in "aıou"
    return f"{ox.az_num(n, 0)}-{'y' if ox._vowel_end(w) else ''}{'a' if back else 'ə'}"


def _q(name):
    """Ad «» içində. Mənbənin öz dırnaqları («“Uçan xalça” marionet tamaşası») «» olur, ikinci dəfə dırnaq qoyulmur."""
    s = " ".join(html.unescape(name or "").split())
    s = re.sub(r"[“„\"]([^“”„\"«»]+)[”“\"]", r"«\1»", s)
    return s if "«" in s else f"«{s}»"


FAMILY = re.compile(r"(?<![^\W\d_])(?:heydər əliyev|ilham əliyev|mehriban əliyeva|məhriban əliyeva|zərifə əliyeva|"
                    r"leyla əliyeva|arzu əliyeva|alena əliyeva|alyona əliyeva|mehriban paşayeva|arif paşayev|"
                    r"nərgiz paşayeva|aida imanquliyeva)|vitse-prezident|prezidentinin (?:oğlu|qızı|həyat yoldaşı|"
                    r"nəvəsi|kürəkəni|gəlini|köməkçisi|administrasiya)")


def _leader(text):
    """Rəhbərliyin adı və ya vəzifəsi keçirmi (ox.needs_owner). updater yüklənməsə, sadə yoxlama."""
    try:
        return bool(ox.needs_owner(text or ""))
    except Exception:
        return bool(re.search(r"prezident|birinci xanım|vitse-prezident|əliyev", _low(text)))


def _family(text):
    """Rəhbərlik ailəsinin adı (needs_owner bəzilərini tanımır: «Heydər Əliyev», «Alena Əliyeva»)."""
    return bool(FAMILY.search(_low(text)))


def _guard(item):
    """Rəhbərliyin adı keçən xəbər dərc olunmur (sahibin qaydası)."""
    if _leader("\n".join([item["title"], item["lead"], *item["body"]])):
        return dict(item, worth=False, why="rəhbərliyin adı keçir: dərc olunmur")
    return item


def _stub(kind, key, slot, why, topic=TOPIC):
    """Sorğu gedib, amma xəbər yoxdur: açar yenə qayıdır (worth=False) ki, canlı həmin pəncərədə bir də sorğu göndərməsin."""
    return {"kind": kind, "key": key, "topic": topic, "slot": slot, "title": "", "lead": "", "body": [],
            "credit": "", "link": "", "worth": False, "why": why or "səbəb yazılmayıb"}


def _default_fetch():
    try:
        return ox._u().fetch
    except Exception:
        return None


def _status(err):
    if err is None:
        return "200"
    code = getattr(err, "code", None)
    if code:
        return str(code)
    reason = getattr(err, "reason", "")
    return f"{type(err).__name__}{(': ' + str(reason)[:60]) if reason else ''}"


class _Net:
    """fetch-in üstündə: bir çağırışda hər ünvana bir sorğu (xəta da yadda qalır), eyni hosta ardıcıl sorğular arasında
    fasilə (sınaqda 1 s), hər sorğunun qeydi (host, ünvan, nəticə, bayt, saniyə)."""

    def __init__(self, fetch, pause=0.0):
        self.fetch, self.pause = fetch, pause
        self.cache, self.log, self.last = {}, [], {}

    def __call__(self, url, timeout=TIMEOUT, headers=None):
        if url not in self.cache:
            if self.fetch is None:
                raise LookupError("sorğu funksiyası verilməyib")
            host = urllib.parse.urlsplit(url).hostname or ""
            if self.pause and host in self.last:
                wait = self.pause - (time.monotonic() - self.last[host])
                if wait > 0:
                    time.sleep(wait)
            began = time.monotonic()
            data, err = None, None
            try:
                data = self.fetch(url, timeout=min(timeout or TIMEOUT, TIMEOUT), headers=dict(headers or {}))
            except Exception as e:  # şəbəkə xətası yalnız həmin mənbəni saxlayır
                err = e
            self.last[host] = time.monotonic()
            self.log.append((host, url, _status(err), len(data or b""), round(time.monotonic() - began, 2)))
            self.cache[url] = (data, err)
        data, err = self.cache[url]
        if err is not None:
            raise err
        return data

    @property
    def count(self):
        return len(self.log)


def _net(fetch, pause=0.0):
    if isinstance(fetch, _Net):
        return fetch
    return _Net(fetch if fetch is not None else _default_fetch(), pause)


def _json(net, url, headers=None):
    return json.loads(net(url, headers=headers).decode("utf-8"))


# --- 1–2. iTicket: günün və həftəsonunun afişası ---------------------------------------------------------

IT_API = "https://api.iticket.az/az/v6/events?client=web&category_slug={cat}&start_date={a:%d.%m.%Y}&end_date={b:%d.%m.%Y}&page={page}"
IT_LINK = "https://iticket.az/events/theatre"
IT_CREDIT = "iTicket.az"
AFISA_PAGES = (("theatre", 2), ("concerts", 1))
HEFTE_PAGES = (("theatre", 3), ("concerts", 1))
EX_PAGES = 1
AFISA_MIN, AFISA_MAX, PER_VENUE = 3, 6, 2
HEFTE_PER_DAY, HEFTE_EX = 5, 3

# Bakının dövlət teatrları və konsert salonları, iTicket-in yazdığı adla; rəqəm siyahıda yeri (1 = əsas səhnə).
STAGES = {
    "Azərbaycan Dövlət Akademik Opera və Balet Teatrı": 1,
    "Akademik Milli Dram Teatrı": 1,
    "Azərbaycan Dövlət Akademik Milli Dram Teatrı": 1,
    "Azərbaycan Dövlət Akademik Musiqili Teatrı": 1,
    "Azərbaycan Dövlət Akademik Filarmoniyası": 1,
    "Beynəlxalq Muğam Mərkəzi": 2,
    "Heydər Əliyev Sarayı": 2,
    "Azərbaycan Dövlət Milli Gənc Tamaşaçılar Teatrı": 2,
    "Akademik Rus Dram Teatrı": 2,
    "Azərbaycan Dövlət Kukla Teatrı": 3,
    "Azərbaycan Dövlət Yuğ Teatrı (Kukla Teatrının binasında)": 3,
    "Azərbaycan Dövlət Pantomim Teatrı": 3,
    "Kamera və orqan musiqisi zalı": 3,
    "Bakı Musiqi Akademiyası nəzdində Opera Studiyasının Konsert salonu": 3,
}
# Sərgilər üçün dövlət muzeyləri.
MUSEUMS = {"Muzey Mərkəzi": 2, "Azərbaycan Milli Xalça Muzeyi": 2, "Azərbaycan Milli İncəsənət Muzeyi": 2,
           "Azərbaycan Milli Tarix Muzeyi": 2}
# Bakıdan kənar şəhər və rayonlar: adında bunlar olan məkan Bakı deyil (iTicket-in city_id-si də səhvdir: Şuşa = Bakı).
REGION = re.compile(r"gəncə|sumqayıt|şuşa|lənkəran|naxçıvan|mingəçevir|şəki|quba|qəbələ|şamaxı|zaqatala|neftçala|"
                    r"qazax|balakən|(?<![^\W\d_])qax|şirvan|ağdam|füzuli|xankəndi|tovuz|şəmkir|bərdə|ismayıllı|qusar|"
                    r"xaçmaz|masallı|astara|lerik|salyan|göyçay|kürdəmir|ağdaş|yevlax|gədəbəy|şahdağ")
PROMO = re.compile(r"candlelight|şam işığında|şam nurunda|şamlar əhatəsində|şamların əhatəsində|stand-?up|komedium")
CYRILLIC = re.compile(r"[А-Яа-яЁё]")
OK_STATES = (None, 1, 5)  # 1 və 5 iTicket-də satışda görünən tədbirlərdir; başqa (bilinməyən) hal yazılmır


def _utc(s):
    """«2026-11-12T15:00:00.000000Z» -> Bakı vaxtı."""
    m = re.match(r"(\d{4})-(\d\d)-(\d\d)[T ](\d\d):(\d\d)(?::(\d\d))?(?:\.\d+)?(Z|[+-]\d\d:?\d\d)?$", (s or "").strip()) \
        if isinstance(s, str) else None
    if not m:
        return None
    y, mo, d, hh, mi, ss, tz = m.groups()
    try:
        dt = datetime.datetime(int(y), int(mo), int(d), int(hh), int(mi), int(ss or 0))
    except ValueError:
        return None
    if tz and tz != "Z":
        digits = tz[1:].replace(":", "")
        off = datetime.timedelta(hours=int(digits[:2]), minutes=int(digits[2:]))
        dt = dt.replace(tzinfo=datetime.timezone(off if tz[0] == "+" else -off))
    else:
        dt = dt.replace(tzinfo=UTC)
    return dt.astimezone(BAKU)


def it_events(doc):
    """iTicket cavabı -> ([{id, name, when, venue, cat, state}], növbəti səhifə varmı)."""
    ev = ((doc or {}).get("response") or {}) if isinstance(doc, dict) else {}
    ev = ev.get("events") if isinstance(ev, dict) else None
    rows = ev.get("data") if isinstance(ev, dict) else None
    if not isinstance(rows, list):
        raise ValueError("iTicket cavabında events.data yoxdur")
    out = []
    for e in rows:
        if not isinstance(e, dict):
            continue
        when = _utc(e.get("event_starts_at"))
        venues = [v.get("name") for v in e.get("venues") or [] if isinstance(v, dict) and isinstance(v.get("name"), str)]
        name = " ".join(str(e.get("name") or "").split())
        if not when or not venues or not name:
            continue
        out.append({"id": e.get("id"), "name": name, "when": when, "venue": " ".join(venues[0].split()),
                    "cat": str(e.get("category_slug") or ""), "state": e.get("public_state")})
    return out, bool(ev.get("next_page_url"))


def it_fetch(net, cat, a, b, pages):
    """Kateqoriyanın a..b günləri üçün səhifələr (ən çox `pages`). Qaytarır (tədbirlər, sorğu sayı)."""
    out, n = [], 0
    for page in range(1, pages + 1):
        n += 1
        rows, more = it_events(_json(net, IT_API.format(cat=cat, a=a, b=b, page=page), JSON_HEADERS))
        out += [dict(r, kind=cat) for r in rows]
        if not more:
            break
    return out, n


def _venue_rank(venue, museums=False):
    table = MUSEUMS if museums else STAGES
    if venue in table:
        return table[venue]
    low = _low(venue)
    if REGION.search(low):
        return None
    if museums:
        return 3 if "muzey" in low else None
    if "dövlət" in low and re.search(r"teatr|filarmoniya", low):
        return 3
    return None


def _skip_event(e, museums=False):
    """Tədbir niyə yazılmır (boşdursa yazılır)."""
    if _venue_rank(e["venue"], museums) is None:
        return "Bakının dövlət səhnəsi deyil"
    if e.get("state") not in OK_STATES:
        return "satış vəziyyəti bilinmir"
    if CYRILLIC.search(e["name"]):
        return "adı kirillədir"
    if PROMO.search(_low(e["name"])):
        return "kommersiya seriyası"
    if _leader(e["name"]) or _family(e["name"]) or _leader(e["venue"]):
        return "rəhbərliyin adı keçir"
    return ""


def _pick(events, start, end, museums=False):
    """start..end günlərinin yazıla bilən tədbirləri, vaxt sırası ilə; eyni tədbir bir dəfə."""
    out, seen = [], set()
    for e in sorted(events, key=lambda e: (e["when"], str(e.get("id")))):
        if not (start <= e["when"].date() <= end) or _skip_event(e, museums):
            continue
        key = (_low(e["name"]), e["venue"], e["when"].date())
        if key in seen or ("id", e.get("id"), e["when"].date()) in seen:
            continue
        seen.update({key, ("id", e.get("id"), e["when"].date())})
        out.append(dict(e, rank=_venue_rank(e["venue"], museums)))
    return out


def _choose(rows, limit, per_venue=PER_VENUE):
    """Əvvəl əsas səhnələr; bir məkandan ən çox per_venue tədbir. Nəticə vaxt sırası ilə."""
    chosen, used = [], {}
    for e in sorted(rows, key=lambda e: (e["rank"], e["when"], e["name"])):
        if len(chosen) >= limit:
            break
        if used.get(e["venue"], 0) >= per_venue:
            continue
        used[e["venue"]] = used.get(e["venue"], 0) + 1
        chosen.append(e)
    return sorted(chosen, key=lambda e: (e["when"], e["rank"], e["venue"]))


def _premiere(name):
    return bool(re.search(r"premyera", _low(name)))


def _event_name(name):
    """«Əli və Nino – premyera» -> «Əli və Nino»; premyera ayrıca qeyd olunur."""
    return _q(re.sub(r"\s*[–—-]\s*premyera\s*$", "", name, flags=re.I))


def _event_line(e, prefix=""):
    return f"{prefix}{e['when']:%H:%M} — {e['venue']}: {_event_name(e['name'])}{' (premyera)' if _premiere(e['name']) else ''}"


def _what(rows):
    kinds = {e.get("kind") for e in rows}
    if kinds == {"concerts"}:
        return "konsertlər keçiriləcək"
    if "concerts" in kinds:
        return "tamaşalar göstəriləcək və konsertlər keçiriləcək"
    return "tamaşalar göstəriləcək"


def _title_names(rows, k=2, longest=45):
    """Başlıq üçün ən əsas səhnələrin ilk k adı (çox uzun ad başlığa düşmür)."""
    out = []
    for e in sorted(rows, key=lambda e: (e["rank"], e["when"])):
        n = _event_name(e["name"])
        if len(n) <= longest and n not in out:
            out.append(n)
        if len(out) >= k:
            break
    return out


def afisa_item(day, events):
    """Bu günün afişası. events: iTicket-in o gün üçün tamaşa və konsertləri. Qaytarır (xəbər və ya None, səbəb)."""
    rows = _pick(events, day, day)
    if len(rows) < AFISA_MIN:
        return None, f"Bakının dövlət səhnələrində {len(rows)} tədbir var: {AFISA_MIN}-dən azdır"
    show = _choose(rows, AFISA_MAX)
    names = _title_names(show)
    rest = len(show) - len(names)
    tail = f" və daha {rest} tədbir" if rest else ""
    variants = [f"Bu gün Bakı səhnələrində: {', '.join(names)}{tail}",
                f"{_cap(ox.day_loc(day))} Bakı səhnələrində: {', '.join(names)}{tail}",
                f"Günün afişası: {', '.join(names)}{tail}"]
    start = day.toordinal() % len(variants)
    # Seçilən adların hamısı uzundursa (45+ simvol) siyahı boş qalır: «Günün afişası:  və daha 3 tədbir» çıxırdı
    title = _fit((variants[start:] + variants[:start] if names else []) + [f"Bu gün Bakı səhnələrində {len(show)} tədbir"])
    lead = f"iTicket-in afişasına görə, bu gün, {ox.day_loc(day)}, Bakının dövlət teatrlarında və konsert salonlarında {_what(show)}."
    prem = [_event_name(e["name"]) for e in show if _premiere(e["name"])]
    if prem:
        lead += f" Afişada {_join(prem)} premyera kimi qeyd olunub."
    item = {"kind": "afisa", "key": f"afisa-{day.isoformat()}", "topic": TOPIC, "slot": SLOT["afisa"], "list": True,
            "title": title, "lead": lead, "body": [_event_line(e) for e in show],
            "credit": IT_CREDIT, "link": IT_LINK, "worth": True}
    return _guard(item), ""


def hefte_item(sat, events, exhibitions):
    """Həftəsonu afişası: şənbə və bazar (sat, sat+1). Qaytarır (xəbər və ya None, səbəb)."""
    sun = sat + DAY
    days = [(sat, _choose(_pick(events, sat, sat), HEFTE_PER_DAY)), (sun, _choose(_pick(events, sun, sun), HEFTE_PER_DAY))]
    ex, seen = [], set()
    for e in _pick(exhibitions, sat, sun, museums=True):
        if _low(e["name"]) not in seen:
            seen.add(_low(e["name"]))
            ex.append(e)
    ex = ex[:HEFTE_EX]
    shows = [e for _, rows in days for e in rows]
    if len(shows) < AFISA_MIN:
        return None, f"həftəsonu Bakının dövlət səhnələrində {len(shows)} tədbir var: {AFISA_MIN}-dən azdır"
    names = _title_names(shows)
    rest = len(shows) + len(ex) - len(names)
    tail = f" və daha {rest} tədbir" if rest else ""
    title = _fit(([f"Həftəsonu Bakı səhnələrində: {', '.join(names)}{tail}",
                   f"Həftəsonu afişası: {', '.join(names)}{tail}"] if names else [])
                 + [f"Həftəsonu Bakı səhnələrində {len(shows)} tədbir"])
    lead = (f"iTicket-in afişasına görə, {_days_loc(sat, sun)} Bakının dövlət teatrlarında və konsert salonlarında "
            f"{_what(shows)}.")
    if ex:
        lead += f" Muzeylərdə {len(ex)} sərgi açıqdır."
    body = [_event_line(e, f"{_cap(WEEKDAYS[d.weekday()])}, ") for d, rows in days for e in rows]
    body += [f"Sərgi — {e['venue']}: {_q(e['name'])}" for e in ex]
    item = {"kind": "afisa-hefte", "key": f"afisa-hefte-{sat.isoformat()}", "topic": TOPIC, "slot": SLOT["hefte"],
            "list": True, "title": title, "lead": lead, "body": body, "credit": IT_CREDIT, "link": IT_LINK, "worth": True}
    return _guard(item), ""


def afisa_day(net, day):
    """Bir günün afişası şəbəkədən: tamaşalar (ən çox 2 səhifə) və konsertlər (1 səhifə)."""
    events = []
    try:
        for cat, pages in AFISA_PAGES:
            events += it_fetch(net, cat, day, day, pages)[0]
    except Exception as e:
        return None, f"iTicket alınmadı: {_err(e)}"
    return afisa_item(day, events)


def hefte_days(net, sat):
    """Həftəsonu afişası şəbəkədən: tamaşalar (3 səhifə), konsertlər (1) və sərgilər (1) — 5 sorğu."""
    events, ex = [], []
    try:
        for cat, pages in HEFTE_PAGES:
            events += it_fetch(net, cat, sat, sat + DAY, pages)[0]
        ex = it_fetch(net, "exhibitions", sat, sat + DAY, EX_PAGES)[0]
    except Exception as e:
        return None, f"iTicket alınmadı: {_err(e)}"
    return hefte_item(sat, events, ex)


def afisa(now, net, done=()):
    day = now.date()
    key = f"afisa-{day.isoformat()}"
    if day.weekday() == 4:
        return None, "cümə günü həftəsonu afişası verilir"
    if key in done:
        return None, "artıq dərc olunub"
    if not _due(now, SLOT["afisa"]):
        return None, f"vaxtı deyil ({SLOT['afisa']})"
    item, why = afisa_day(net, day)
    return item or _stub("afisa", key, SLOT["afisa"], why), why


def hefte(now, net, done=()):
    day = now.date()
    if day.weekday() != 4:
        return None, "yalnız cümə günü"
    sat = day + DAY
    key = f"afisa-hefte-{sat.isoformat()}"
    if key in done:
        return None, "artıq dərc olunub"
    if not _due(now, SLOT["hefte"]):
        return None, f"vaxtı deyil ({SLOT['hefte']})"
    item, why = hefte_days(net, sat)
    return item or _stub("afisa-hefte", key, SLOT["hefte"], why), why


# --- 3. Kino: CineMastercard-ın «Tezliklə» siyahısı ---------------------------------------------------------

CINEMA_URL = "https://cinemastercard.az/"
CINEMA_CREDIT = "CineMastercard"
_CARD = re.compile(r'<h2><a href="(/az/(?:coming-soon|films)/[^"]+)">([^<]+)</a></h2>(.*?)<div class="go_film"[^>]*>(.*?)</div>', re.S)
_TIP = re.compile(r"<b></b>([^<]+)</span>")
_LANG = re.compile(r"^Film (\S+) dilində nümayiş olunur")
_SPORT = re.compile(r"^(?:ufc|bellator|wwe|pfl|one championship)(?![^\W\d_])")


def kino_parse(page):
    """«Tezliklə» kartları -> [{title, date, age, langs, sport, link}]. Tarixsiz kart (indi göstərilən film) düşür."""
    out, seen = [], set()
    for link, title, body, tail in _CARD.findall(page or ""):
        m = re.search(r"(\d\d)\.(\d\d)\.(\d{4})", tail)
        if not m:
            continue
        try:
            day = datetime.date(int(m.group(3)), int(m.group(2)), int(m.group(1)))
        except ValueError:
            continue
        name = " ".join(html.unescape(title).split())
        tips = [" ".join(html.unescape(t).split()) for t in _TIP.findall(body)]
        langs = []
        for t in tips:
            lm = _LANG.match(t)
            if lm and lm.group(1) not in langs:
                langs.append(lm.group(1))
        age = re.search(r'class="movie_class">\s*(\d{1,2}\+)\s*<', body)
        sport = any(_low(t) == "futbol" for t in tips) or bool(_SPORT.search(_low(name)))
        key = (_low(name), day)
        if not name or key in seen:
            continue
        seen.add(key)
        out.append({"title": name, "date": day, "age": age.group(1) if age else "", "langs": langs, "sport": sport,
                    "link": link})
    return out


def _lang(word):
    low = _low(word)
    return "Azərbaycan" if low == "azərbaycan" else low


def _film_info(f):
    """Yalnız dil. Yaş həddi yazılmır: «Tezliklə» kartındakı hədd buraxılış günü dəyişə bilir
    («Dune: 1-ci hissə» 10.11.2026-da 12+, 12.11.2026-da 16+; «Ebenezer» boş, sonra 16+)."""
    if not f["langs"]:
        return ""
    langs = [_lang(x) for x in f["langs"]]
    return f"{_join(langs)} {'dilində' if len(langs) == 1 else 'dillərində'}"


def kino_item(release, films):
    """release günü ekrana çıxan filmlər (xəbər bir gün əvvəl, çərşənbə dərc olunur). Qaytarır (xəbər, səbəb)."""
    films = [f for f in films or [] if not f["sport"]]
    new = [f for f in films if f["date"] == release]
    if not new:
        return None, f"«Tezliklə» siyahısında {ox.day_text(release)} tarixli film yoxdur"
    names = [_q(f["title"]) for f in new]
    options = [f"{_day_abl(release)} kinoteatrlarda: {_join(names[:k])}{f' və daha {len(names) - k} film' if k < len(names) else ''}"
               for k in range(len(names), 0, -1)]
    title = _fit(options + [f"{_day_abl(release)} kinoteatrlarda {len(names)} film nümayiş olunacaq"])
    listed = _join([f"{_q(f['title'])} ({_film_info(f)})" if _film_info(f) else _q(f["title"]) for f in new])
    lead = (f"CineMastercard kinoteatrlarının «Tezliklə» siyahısına görə, {_day_abl(release)} {listed} "
            f"{'filmləri' if len(new) > 1 else 'filmi'} nümayiş olunacaq.")
    later = {}
    for f in films:
        if release < f["date"] <= release + 7 * DAY:
            later.setdefault(f["date"], []).append(_q(f["title"]))
    body = []
    if later:
        parts = [f"{_day_abl(d)} {_join(later[d])}" for d in sorted(later)]
        body.append(f"Siyahıya görə, {', '.join(parts)} nümayiş olunacaq.")
    item = {"kind": "kino", "key": f"kino-{release.isoformat()}", "topic": TOPIC, "slot": SLOT["kino"],
            "title": title, "lead": lead, "body": body, "credit": CINEMA_CREDIT, "link": CINEMA_URL, "worth": True}
    return _guard(item), ""


def kino_day(net, release):
    try:
        films = kino_parse(net(CINEMA_URL).decode("utf-8", "replace"))
    except Exception as e:
        return None, f"cinemastercard.az alınmadı: {_err(e)}"
    if not films:
        return None, "«Tezliklə» siyahısı oxunmadı"
    return kino_item(release, films)


def kino(now, net, done=()):
    day = now.date()
    if day.weekday() != 2:
        return None, "yalnız çərşənbə günü (filmlər cümə axşamı çıxır)"
    release = day + DAY
    key = f"kino-{release.isoformat()}"
    if key in done:
        return None, "artıq dərc olunub"
    if not _due(now, SLOT["kino"]):
        return None, f"vaxtı deyil ({SLOT['kino']})"
    item, why = kino_day(net, release)
    return item or _stub("kino", key, SLOT["kino"], why), why


# --- 4–5. Vikipediyada ən çox oxunanlar -------------------------------------------------------------------

FEED_URL = "https://az.wikipedia.org/api/rest_v1/feed/featured/{:%Y/%m/%d}"
TOP_URL = "https://wikimedia.org/api/rest_v1/metrics/pageviews/top/az.wikipedia/all-access/{}/{:02d}/all-days"
API_URL = "https://az.wikipedia.org/w/api.php?"
TOPVIEWS = "https://pageviews.wmcloud.org/topviews/?project=az.wikipedia.org&platform=all-access&date={}&excludes="
WIKI_PAGE = "https://az.wikipedia.org/wiki/{}"
WIKI_CREDIT = "Vikimedia Fondu"
WIKI_MIN, WIKI_TOP, INFO_N = 3, 5, 20
MAIN_PAGES = {"ana səhifə", "main page", "-"}
_NS = re.compile(r"(?:xüsusi|vikipediya|kateqoriya|şablon|fayl|istifadəçi|portal|kömək|modul|mediawiki|müzakirə|special|"
                 r"wikipedia|file|category|template|user|help|talk|media)[^:]{0,20}:")
ADULT = re.compile(r"(?<![^\W\d_])(?:seks(?!iya)|cinsi (?:əlaqə|həyat|orqan|münasibət|zorakılıq|təcavüz|akt)|porno|erotik|"
                   r"fahişə|orqazm|masturbasiya|genital|penis|vagin|anal |anus|klitor|sperma|ereksiya|fetiş|bdsm|"
                   r"prostitu|minet|pedofil|zoofil|insest|incest|cinsiyyət orqan)")
OFFICIAL = re.compile(r"siyasətçi|siyasi xadim|siyasi və dövlət|ictimai-siyasi|dövlət xadimi|nazir|deputat|milli məclis|"
                      r"parlament|səfir|prezident|administrasiya|prokuror|hakim(?!iyyət)|ombudsman|icra başçısı|general|"
                      r"komandan|rəisi|xidmətinin|komitəsinin sədri|partiyasının sədri|köməkçisi|müşaviri|məmur|"
                      r"dövlət qulluqçusu")
CRIME = re.compile(r"qətl|öldürül|cinayət|terror|partlayış|zorla|təcavüz|intihar|qaçırıl|oğurla|soyğun|atışma|qırğın|"
                   r"qəzası|fəlakəti|yanğın|itkin düş|həbs|məhkum|narkotik|korrupsiya|rüşvət")
DIED = re.compile(r"vəfat edib|vəfat etmişdir|dünyasını dəyiş|həlak olub|öldürülüb|qətlə yetiril")
_SENT = re.compile(r"(?<=[^\W\d_]{2})\.\s+(?=[A-ZÇƏĞİÖŞÜ«\"„“0-9])")
_MON = "|".join(MONTHS)
_DATE = re.compile(r"(\d{1,2})(?:\s*\((\d{1,2})\))?\s+(" + _MON + r")\s+(\d{3,4})")


def _sentences(text):
    return [s.strip() for s in _SENT.split(" ".join((text or "").split())) if s.strip()]


def _first(text):
    s = _sentences(text)
    return s[0] if s else ""


def _died_recently(text, day):
    """Girişin mötərizələrində son bir ildəki ölüm tarixi («– 29 oktyabr 2026») və ya ölüm sözləri ilə bu il."""
    head = (text or "")[:500]
    for m in re.finditer(r"\(((?:[^()]|\([^()]*\))*)\)", head):  # adın başqa dildə yazılışı da mötərizədə olur
        parts = re.split(r"\s+[-–—]\s*|[–—]|(?<=\d)-(?=\d)", _low(m.group(1)), maxsplit=1)
        if len(parts) != 2:
            continue
        after = parts[1]
        dm = _DATE.search(after)
        if dm:
            try:
                died = datetime.date(int(dm.group(4)), MONTHS.index(dm.group(3)) + 1, int(dm.group(1)))
            except ValueError:
                continue
            if day - 365 * DAY <= died <= day + DAY:
                return True
            continue
        born = re.search(r"\b(\d{4})\b", parts[0])
        ym = re.search(r"\b(\d{4})\b", after)
        if born and ym and int(born.group(1)) <= day.year - 5 and int(ym.group(1)) >= day.year - 1:
            return True  # «(1952–2026)»; «(2025–2026 mövsümü)» ömür deyil
    low = _low(head)
    return bool(DIED.search(low)) and (str(day.year) in low or str(day.year - 1) in low)


_YEARS = re.compile(r"(\d{4})\s*[–—-]\s*(\d{4})\s*[>)]")


def _desc_died(desc, day):
    """Wikidata təsvirindəki illər («Azərbaycan bəstəkarı (1952–2026)», «<1975–2020>»): ölüm ili bu il və ya keçən il."""
    m = _YEARS.search(desc or "")
    return bool(m) and int(m.group(2)) >= day.year - 1


def wiki_skip(title, desc, extract, day, disamb=False):
    """Məqalə siyahıya niyə düşmür (boş = düşür). day: xəbərin dərc günü (son bir il ondan sayılır)."""
    low_title = _low(title).replace("_", " ").strip()
    if low_title in MAIN_PAGES:
        return "ana səhifə"
    if _NS.match(low_title):
        return "xüsusi səhifə"
    if disamb:
        return "dəqiqləşdirmə səhifəsi"
    first = _first(extract)
    blob = _low(" ".join([title, desc or "", first]))
    if ADULT.search(blob) or low_title in {"seks", "anal seks", "oral seks"}:
        return "18+ mövzu"
    if _leader("\n".join([title, desc or "", extract or ""])) or _family(" ".join([title, desc or "", extract or ""])):
        return "rəhbərlik"
    if OFFICIAL.search(_low((desc or "") + " " + first)) and "azərbaycan" in _low((desc or "") + " " + first):
        return "vəzifəli şəxs və ya siyasətçi"
    if _died_recently(extract, day) or _desc_died(desc, day):
        return "son bir ildə vəfat edib"
    if CRIME.search(blob) and (str(day.year) in blob or str(day.year - 1) in blob):
        return "cinayət və ya hadisə"
    return ""


def _short_desc(desc):
    d = " ".join((desc or "").split())
    return d if 0 < len(d) <= 90 else ""


def _entry(r):
    line = f"{_q(r['title'])} — {ox.az_num(r['views'], 0)} baxış"
    d = _short_desc(r.get("desc"))
    return line + (f" ({d})" if d else "")


def _jump(rows):
    """Siyahıdakı məqalələrdən baxışı bir gündə ən çox artan (ən az 3 dəfə, əvvəl ən az 10 baxış)."""
    best = None
    for r in rows:
        prev = r.get("prev")
        if isinstance(prev, int) and prev >= 10 and r["views"] >= 3 * prev:
            if best is None or r["views"] / prev > best["views"] / best["prev"]:
                best = r
    if not best:
        return ""
    return (f"Siyahıdakı məqalələr arasında bir gündə ən çox artım: {_q(best['title'])} məqaləsinə baxışların sayı "
            f"{num_abl(best['prev'])} {num_dat(best['views'])} qalxıb.")


def _wiki_date(s):
    m = re.match(r"(\d{4})-(\d\d)-(\d\d)", s or "") if isinstance(s, str) else None
    if not m:
        return None
    try:
        return datetime.date(int(m.group(1)), int(m.group(2)), int(m.group(3)))
    except ValueError:
        return None


def gun_rows(doc):
    """Lentin «mostread» hissəsi -> (gün, [{title, views, prev, desc, extract, link, disamb}]), çox baxılandan aza."""
    mr = doc.get("mostread") if isinstance(doc, dict) else None
    if not isinstance(mr, dict):
        return None, []
    day = _wiki_date(mr.get("date"))
    if not day:
        return None, []
    prev_key = (day - DAY).isoformat()
    rows = []
    for a in mr.get("articles") or []:
        if not isinstance(a, dict):
            continue
        titles = a.get("titles") if isinstance(a.get("titles"), dict) else {}
        title = titles.get("normalized") or a.get("normalizedtitle") or str(a.get("title") or "").replace("_", " ")
        views = a.get("views")
        if not title or not isinstance(views, int) or isinstance(views, bool) or views <= 0:
            continue
        prev = None
        for h in a.get("view_history") or []:
            if isinstance(h, dict) and str(h.get("date") or "").startswith(prev_key) and isinstance(h.get("views"), int):
                prev = h["views"]
        ns = a.get("namespace") if isinstance(a.get("namespace"), dict) else {}
        rows.append({"title": " ".join(str(title).split()), "views": views, "prev": prev,
                     "desc": str(a.get("description") or ""), "extract": str(a.get("extract") or ""),
                     "disamb": a.get("type") == "disambiguation" or ns.get("id") not in (None, 0)})
    rows.sort(key=lambda r: -r["views"])
    return day, rows


INFO_GUN = 12


def gun_check(net, rows, ref):
    """Süzgəc iki pillədə: əvvəl lentin öz təsviri və girişi ilə, sonra keçən ilk INFO_GUN məqalənin tam girişi ilə
    (1 sorğu; lentin girişində doğum və ölüm tarixləri olmur). Hər sətrə «skip» yazır. Qaytarır: xəta mətni və ya ''."""
    for r in rows:
        r["skip"] = wiki_skip(r["title"], r["desc"], r["extract"], ref, r.get("disamb"))
    cand = [r for r in rows if not r["skip"]]
    for r in cand[INFO_GUN:]:
        r["skip"] = "girişi yoxlanmayıb"
    cand = cand[:INFO_GUN]
    if len(cand) < WIKI_MIN:
        return ""
    try:
        find = wiki_info(_json(net, info_url([r["title"] for r in cand]), WIKI_HEADERS))
    except Exception as e:
        return f"məqalələrin girişi alınmadı: {_err(e)}"
    for r in cand:
        info = find(r["title"])
        if not info or not info["extract"]:
            r["skip"] = "girişi alınmadı"
        else:
            r["skip"] = wiki_skip(r["title"], info["desc"] or r["desc"], info["extract"], ref, info["disamb"])
    return ""


def gun_item(day, rows, today=None):
    """Bir günün ən çox oxunanları. rows: gun_rows-un nəticəsi (gun_check-dən sonra). today verilib və day dünəndirsə
    başlıqda «Dünən» yazılır."""
    ref = today or day + DAY
    for r in rows:
        if "skip" not in r:
            r["skip"] = wiki_skip(r["title"], r["desc"], r["extract"], ref, r.get("disamb"))
    ok = [r for r in rows if not r["skip"]]
    if len(ok) < WIKI_MIN:
        return None, f"süzgəcdən sonra {len(ok)} məqalə qalıb: {WIKI_MIN}-dən azdır"
    top = ok[:WIKI_TOP]
    when = "Dünən" if today is not None and day == today - DAY else _cap(ox.day_loc(day))
    first = top[0] is rows[0]
    names = [_q(r["title"]) for r in top]
    if first:
        title = _fit([f"{when} Azərbaycan Vikipediyasında ən çox {names[0]} məqaləsi oxunub",
                      f"{when} Vikipediyada ən çox {names[0]} oxunub",
                      f"{when} Azərbaycan Vikipediyasında ən çox oxunan {len(top)} məqalə"])
        lead = (f"Vikimedia Fondunun məlumatına görə, {ox.day_loc(day)} Azərbaycandilli Vikipediyada ən çox {names[0]} "
                f"məqaləsi oxunub: {ox.az_num(top[0]['views'], 0)} baxış.")
        if isinstance(top[0].get("prev"), int):
            lead += f" Bir gün əvvəl bu məqaləyə {ox.az_num(top[0]['prev'], 0)} dəfə baxılmışdı."
    else:
        title = _fit([f"{when} Azərbaycan Vikipediyasında çox oxunanlar: {_join(names[:3])}",
                      f"{when} Azərbaycan Vikipediyasında çox oxunanlar: {_join(names[:2])}",
                      f"{when} Azərbaycan Vikipediyasında çox oxunan {len(top)} məqalə"])
        shown = [f"{names[i]} ({ox.az_num(top[i]['views'], 0)} baxış)" for i in range(min(3, len(top)))]
        lead = (f"Vikimedia Fondunun məlumatına görə, {ox.day_loc(day)} Azərbaycandilli Vikipediyada çox oxunan məqalələr "
                f"arasında {_join(shown)} var.")
    jump = _jump(top)
    if jump:
        lead += " " + jump
    body = [_entry(r) for r in top]
    item = {"kind": "vikipediya-gun", "key": f"vikipediya-gun-{day.isoformat()}", "topic": "icmal",
            "slot": SLOT["vikipediya"], "list": True, "title": title, "lead": lead, "body": body,
            "credit": WIKI_CREDIT, "link": TOPVIEWS.format(day.isoformat()), "worth": True}
    return _guard(item), ""


def gun_day(net, today):
    """Bu günün lenti: «mostread» dünənindirsə xəbər, deyilsə səbəb. Qaytarır (xəbər, səbəb, qətidirmi): siyahı hələ
    hazır deyilsə və ya lent alınmayıbsa qəti deyil (sonrakı cəhd mənalıdır)."""
    try:
        doc = _json(net, FEED_URL.format(today), WIKI_HEADERS)
    except Exception as e:
        return None, f"Vikipediya lenti alınmadı: {_err(e)}", False
    day, rows = gun_rows(doc)
    if not day:
        return None, "lentdə «ən çox oxunanlar» hələ yoxdur", False
    if day != today - DAY:
        return None, f"lentdəki siyahı {ox.day_text(day)} günü üçündür: dünənki hələ hazır deyil", False
    bad = gun_check(net, rows, today)
    if bad:
        return None, bad, True
    item, why = gun_item(day, rows, today)
    return item, why, True


def _ay_day(d):
    """Aylıq xəbərin günü: ayın 2-si; 2-si çərşənbə (kino) və ya cüməyə (həftəsonu afişası) düşürsə 1-i:
    o günlərin sorğuları onsuz da 10-a çatır."""
    if d.day == 2:
        return d.weekday() not in (2, 4)
    return d.day == 1 and (d + DAY).weekday() in (2, 4)


def _wiki_tries(d):
    """Cümə (həftəsonu afişası 5 sorğu aparır) və aylıq xəbərin günü tək cəhd, 15:00; başqa günlər 13:00 və 15:00."""
    return WIKI_TRIES[1:] if d.weekday() == 4 or _ay_day(d) else WIKI_TRIES


def vikipediya_gun(now, net, done=()):
    today = now.date()
    key = f"vikipediya-gun-{(today - DAY).isoformat()}"
    if key in done:
        return None, "artıq dərc olunub"
    tries = _wiki_tries(today)
    slot = next((t for t in tries if _due(now, t)), None)
    if not slot:
        return None, f"vaxtı deyil ({', '.join(tries)})"
    last = slot == tries[-1]
    if not last and key + WAIT in done:
        return None, f"siyahı hazır deyildi: növbəti cəhd {tries[-1]}"
    item, why, final = gun_day(net, today)
    if item:
        return dict(item, slot=slot), why
    return _stub("vikipediya-gun", key if final or last else key + WAIT, slot, why, "icmal"), why


def info_url(titles):
    q = {"action": "query", "format": "json", "formatversion": "2", "prop": "extracts|description|pageprops",
         "exintro": "1", "explaintext": "1", "exsentences": "3", "exlimit": "20", "redirects": "1",
         "titles": "|".join(titles)}
    return API_URL + urllib.parse.urlencode(q, quote_via=urllib.parse.quote)


def wiki_info(doc):
    """action=query cavabı -> funksiya: istənən ad -> {title, desc, extract, disamb} və ya None."""
    q = (doc or {}).get("query") if isinstance(doc, dict) else None
    q = q if isinstance(q, dict) else {}
    pages = {}
    for p in q.get("pages") or []:
        if isinstance(p, dict) and p.get("title") and not p.get("missing") and not p.get("invalid"):
            pages[p["title"]] = {"title": p["title"], "desc": str(p.get("description") or ""),
                                 "extract": str(p.get("extract") or ""),
                                 "disamb": isinstance(p.get("pageprops"), dict) and "disambiguation" in p["pageprops"]}
    alias = {}
    for n in list(q.get("normalized") or []) + list(q.get("redirects") or []):
        if isinstance(n, dict) and n.get("from") and n.get("to"):
            alias[n["from"]] = n["to"]

    def find(title):
        t = title
        for _ in range(4):
            if t in pages:
                return pages[t]
            t = alias.get(t)
            if t is None:
                break
        return pages.get(str(title).replace("_", " "))
    return find


def ay_rows(doc):
    """Aylıq siyahı -> (il, ay, [{title, views}]), ana və xüsusi səhifələr çıxarılıb, çox baxılandan aza."""
    items = (doc or {}).get("items") if isinstance(doc, dict) else None
    if not isinstance(items, list) or not items or not isinstance(items[0], dict):
        return None, None, []
    it = items[0]
    try:
        year, month = int(it.get("year")), int(it.get("month"))
    except (TypeError, ValueError):
        return None, None, []
    rows = []
    for a in it.get("articles") or []:
        if not isinstance(a, dict) or not isinstance(a.get("views"), int) or a["views"] <= 0:
            continue
        title = " ".join(str(a.get("article") or "").replace("_", " ").split())
        low = _low(title)
        if not title or low in MAIN_PAGES or _NS.match(low):
            continue
        rows.append({"title": title, "views": a["views"]})
    rows.sort(key=lambda r: -r["views"])
    return year, month, rows


def ay_item(year, month, rows, find, today=None):
    """Ayın ən çox oxunanları. find: wiki_info-nun nəticəsi (ilk INFO_N məqalənin təsviri və girişi).
    today: dərc günü («son bir ildə vəfat edib» ondan sayılır); verilməyibsə növbəti ayın 2-si."""
    ref = today or (datetime.date(year, month, 28) + 5 * DAY).replace(day=2)
    for r in rows[:INFO_N]:
        info = find(r["title"]) if find else None
        if not info:
            r["skip"] = "təsviri və girişi alınmadı"
            continue
        r["desc"] = info["desc"]
        r["skip"] = wiki_skip(r["title"], info["desc"], info["extract"], ref, info["disamb"])
    ok = [r for r in rows[:INFO_N] if not r.get("skip")]
    if len(ok) < WIKI_MIN:
        return None, f"süzgəcdən sonra {len(ok)} məqalə qalıb: {WIKI_MIN}-dən azdır"
    top = ok[:WIKI_TOP]
    when = _cap(_month_loc(month))
    names = [_q(r["title"]) for r in top]
    if top[0] is rows[0]:
        title = _fit([f"{when} Azərbaycan Vikipediyasında ən çox {names[0]} oxunub",
                      f"{when} Azərbaycan Vikipediyasında ən çox oxunan {len(top)} məqalə"])
        lead = (f"Vikimedia Fondunun məlumatına görə, {_month_loc(month)} Azərbaycandilli Vikipediyada ən çox {names[0]} "
                f"məqaləsinə baxılıb: {ox.az_num(top[0]['views'], 0)} dəfə.")
    else:
        title = _fit([f"{when} Azərbaycan Vikipediyasında çox oxunanlar: {_join(names[:3])}",
                      f"{when} Azərbaycan Vikipediyasında çox oxunanlar: {_join(names[:2])}",
                      f"{when} Azərbaycan Vikipediyasında çox oxunan {len(top)} məqalə"])
        shown = [f"{names[i]} ({ox.az_num(top[i]['views'], 0)} baxış)" for i in range(min(3, len(top)))]
        lead = (f"Vikimedia Fondunun məlumatına görə, {_month_loc(month)} Azərbaycandilli Vikipediyada çox oxunan "
                f"məqalələr arasında {_join(shown)} var.")
    item = {"kind": "vikipediya-ay", "key": f"vikipediya-ay-{year}-{month:02d}", "topic": "icmal",
            "slot": SLOT["vikipediya-ay"], "list": True, "title": title, "lead": lead, "body": [_entry(r) for r in top],
            "credit": WIKI_CREDIT, "link": TOPVIEWS.format(f"{year}-{month:02d}"), "worth": True}
    return _guard(item), ""


def ay_month(net, year, month, today=None):
    """Aylıq xəbər şəbəkədən: siyahı (1 sorğu) və ilk 20 məqalənin təsviri və girişi (1 sorğu)."""
    try:
        y, m, rows = ay_rows(_json(net, TOP_URL.format(year, month), WIKI_HEADERS))
    except Exception as e:
        return None, f"aylıq siyahı alınmadı: {_err(e)}"
    if (y, m) != (year, month) or not rows:
        return None, "aylıq siyahı boşdur və ya başqa ayındır"
    try:
        find = wiki_info(_json(net, info_url([r["title"] for r in rows[:INFO_N]]), WIKI_HEADERS))
    except Exception as e:
        return None, f"məqalələrin girişi alınmadı: {_err(e)}"
    return ay_item(year, month, rows, find, today)


def _prev_month(d):
    first = d.replace(day=1) - DAY
    return first.year, first.month


def vikipediya_ay(now, net, done=()):
    today = now.date()
    if not _ay_day(today):
        return None, "ayın 2-si deyil"
    year, month = _prev_month(today)
    key = f"vikipediya-ay-{year}-{month:02d}"
    if key in done:
        return None, "artıq dərc olunub"
    if not _due(now, SLOT["vikipediya-ay"]):
        return None, f"vaxtı deyil ({SLOT['vikipediya-ay']})"
    item, why = ay_month(net, year, month, today)
    return item or _stub("vikipediya-ay", key, SLOT["vikipediya-ay"], why, "icmal"), why


# --- 6. Yubileylər: Wikidata + az.wikipedia ----------------------------------------------------------------

SPARQL_URL = "https://query.wikidata.org/sparql?format=json&query={}"
YUB_MIN, YUB_CHECK = 50, 5
POLITICAL = re.compile(r"siyasətçi|siyasi xadim|ictimai-siyasi|dövlət xadimi|dövlət qulluqçusu|diplomat|deputat|nazir|"
                       r"səfir|hakim(?!iyyət)|prokuror|polis|kriminal|qanuni oğru|terror|casus|işgəncə|məmur|bürokrat")
# Sağ şəxsin (Wikidata-da ölüm tarixi yoxdur) girişində bunlardan biri varsa, yubiley yazılmır (şübhədə yazmırıq).
SENSITIVE = re.compile(r"müxalif|məhbus|mühacir|sığınacaq|axtarış|dissident|hüquq müdafiəçi|ictimai fəal|siyasi fəal|aktivist|"
                       r"bloger|partiya|hərəkatı|cəbhəsi|" + CRIME.pattern)
CITIES = {"bakı", "gəncə", "sumqayıt", "şuşa", "şəki", "naxçıvan", "lənkəran", "quba", "şamaxı", "mingəçevir", "ağdam",
          "tbilisi", "təbriz", "dərbənd", "irəvan", "moskva", "zaqatala", "qazax", "göyçay", "ordubad", "culfa", "füzuli",
          "salyan", "qəbələ", "xankəndi", "ərdəbil", "tiflis"}


def yub_query(month, day):
    return ("SELECT ?p ?name ?b ?sl ?title ?desc ?dead (GROUP_CONCAT(DISTINCT ?occL; separator=\"|\") AS ?occ) "
            "(COUNT(DISTINCT ?pos) AS ?posn) WHERE {\n"
            "  VALUES ?c { wd:Q227 wd:Q130229 wd:Q503586 }\n"
            "  ?p wdt:P27 ?c; wdt:P31 wd:Q5; p:P569/psv:P569 ?bv.\n"
            "  ?bv wikibase:timeValue ?b; wikibase:timePrecision ?prec.\n"
            f"  FILTER(?prec >= 11 && MONTH(?b) = {month} && DAY(?b) = {day})\n"
            "  ?art schema:about ?p; schema:isPartOf <https://az.wikipedia.org/>; schema:name ?title.\n"
            "  ?p wikibase:sitelinks ?sl; rdfs:label ?name. FILTER(LANG(?name) = \"az\")\n"
            "  OPTIONAL { ?p schema:description ?desc. FILTER(LANG(?desc) = \"az\") }\n"
            "  OPTIONAL { ?p wdt:P570 ?dead }\n"
            "  OPTIONAL { ?p wdt:P106 ?o. ?o rdfs:label ?occL. FILTER(LANG(?occL) = \"az\") }\n"
            "  OPTIONAL { ?p wdt:P39 ?pos }\n"
            "} GROUP BY ?p ?name ?b ?sl ?title ?desc ?dead ORDER BY DESC(?sl)")


def sparql_url(day):
    return SPARQL_URL.format(urllib.parse.quote(yub_query(day.month, day.day), safe=""))


def yub_rows(doc, day):
    """Wikidata cavabı -> bu gün ildönümü 25-ə bölünən (50 və daha çox) şəxslər, «why» ilə (boş = namizəddir).
    Sıra: daha çox dildə məqaləsi olan birinci."""
    bindings = (((doc or {}).get("results") or {}).get("bindings") or []) if isinstance(doc, dict) else []
    rows = {}
    for b in bindings:
        if not isinstance(b, dict):
            continue

        def get(k):
            v = b.get(k)
            return str(v.get("value") or "").strip() if isinstance(v, dict) else ""
        qid = get("p").rsplit("/", 1)[-1]
        m = re.match(r"^(\d{3,4})-(\d\d)-(\d\d)T", get("b"))
        if not qid.startswith("Q") or not m or qid in rows:
            continue
        year, month, dd = (int(x) for x in m.groups())
        years = day.year - year
        if (month, dd) != (day.month, day.day) or years < YUB_MIN or years % 25:
            continue
        name = re.sub(r"\s*\([^)]*\)", "", get("name")).strip()
        occ = [o for o in get("occ").split("|") if o]
        try:
            sl, pos = int(get("sl") or 0), int(get("posn") or 0)
        except ValueError:
            sl, pos = 0, 0
        if not name or not get("title"):
            continue
        why = ""
        if pos or POLITICAL.search(_low(" ".join([get("desc")] + occ))):
            why = "siyasətçi və ya vəzifəli şəxs"
        elif not get("desc") and not occ:
            why = "peşəsi məlum deyil"
        rows[qid] = {"qid": qid, "name": name, "title": get("title"), "year": year, "years": years, "sl": sl,
                     "desc": get("desc"), "occ": occ, "dead": get("dead")[:10], "why": why}
    return sorted(rows.values(), key=lambda r: (-r["sl"], r["year"], r["name"]))


def _name_key(s):
    return " ".join(re.sub(r"\([^)]*\)", " ", _low(s)).split())


def born_names(parsed):
    """ox.tarix_parse-in «born» siyahısındakı adlar («Davud Kazımov, Azərbaycan boyakarı» -> «davud kazımov»)."""
    return {_name_key(text.partition(", ")[0]) for _, text in (parsed or {}).get("born") or []}


def lead_ok(extract, day, year):
    """az.wikipedia girişindəki ilk tarix doğum tarixidir: «9 noyabr 1926», «4 (17) noyabr 1906» (köhnə və yeni təqvim)."""
    m = _DATE.search(_low(extract)[:300])
    if not m or m.group(3) != MONTHS[day.month - 1] or int(m.group(4)) != year:
        return False
    return day.day in (int(m.group(1)), int(m.group(2) or 0))


def _birth_match(extract, day, year):
    low = _low(extract)[:300]
    m = _DATE.search(low)
    return (m, low) if m and lead_ok(extract, day, year) else (None, low)


def _birthplace(extract, day, year):
    m, low = _birth_match(extract, day, year)
    if not m:
        return ""
    pm = re.match(r"\s*,\s*([^\W\d_]+)(?=\s*[,)–—-])", low[m.end():])
    if not pm or pm.group(1) not in CITIES:
        return ""
    start = m.end() + pm.start(1)
    return extract[start:start + len(pm.group(1))]


def _death(extract, r, day):
    """Girişdəki ölüm tarixi, Wikidata-nın ölüm ili ilə eynidirsə."""
    m, low = _birth_match(extract, day, r["year"])
    if not m or not r.get("dead"):
        return None
    dm = re.match(r"[^()]{0,80}?[–—-]\s*(?:ö\.\s*)?(\d{1,2})\s+(" + _MON + r")\s+(\d{4})", low[m.end():])
    if not dm or dm.group(3) != r["dead"][:4]:
        return None
    try:
        return datetime.date(int(dm.group(3)), MONTHS.index(dm.group(2)) + 1, int(dm.group(1)))
    except ValueError:
        return None


def _role(r, extract=""):
    """«Azərbaycan bəstəkarı»: Wikidata təsviri, yoxdursa girişin «—»-dən sonrakı ilk sözləri, o da yoxdursa peşə."""
    desc = re.split(r"[;(]", r.get("desc") or "")[0].strip(" ,.")
    if desc and _low(desc).startswith("azərbaycan") and len(desc) <= 60:
        return desc
    dm = re.search(r"\s[—–]\s([^,.;()]{3,60})", (extract or "")[:400])
    if dm and _low(dm.group(1)).startswith("azərbaycan"):
        return dm.group(1).strip()
    return r["occ"][0] if r.get("occ") else ""


def _person(role, name):
    return f"{role} {name}".strip()


def yub_item(day, r, others=()):
    """Yubiley xəbəri: r yoxlanmış namizəddir (extract = az.wikipedia girişi; mətni xəbərə köçürülmür)."""
    extract = r.get("extract") or ""
    role = _role(r, extract)
    name = r["name"]
    title = _fit([f"{_cap(_person(role, ox._gen_plain(name)))} anadan olmasından {r['years']} il keçir",
                  f"{_cap(ox._gen_plain(name))} anadan olmasından {r['years']} il keçir"])
    place = _birthplace(extract, day, r["year"])
    lead = (f"{_cap(_person(role, name))} {day.day} {MONTHS[day.month - 1]} {ox.ordinal(r['year'])} ildə"
            f"{' ' + ox.place_loc(place) if place else ''} anadan olub.")
    died = _death(extract, r, day)
    if died:
        age = died.year - r["year"] - ((died.month, died.day) < (day.month, day.day))
        lead += f" O, {died.day} {MONTHS[died.month - 1]} {ox.ordinal(died.year)} ildə, {age} yaşında vəfat edib."
    body = []
    for o in others:
        body.append(f"Bu gün həmçinin {_person(_role(o, o.get('extract') or ''), ox._gen_plain(o['name']))} anadan "
                    f"olmasından {o['years']} il keçir.")
    item = {"kind": "yubiley", "key": f"yubiley-{day.isoformat()}", "topic": TOPIC, "slot": SLOT["yubiley"],
            "title": title, "lead": lead, "body": body, "credit": "Vikipediya",
            "link": WIKI_PAGE.format(urllib.parse.quote(r["title"].replace(" ", "_"))), "worth": True}
    return _guard(item), ""


def yubiley_day(net, day, report=None):
    """Bu günün yubileyi: Wikidata (1 sorğu), namizəd varsa gün səhifəsi (1) və girişlər (1).
    report verilərsə (siyahı), hər namizədin taleyi ora yazılır: (ad, il, səbəb)."""
    report = report if report is not None else []
    try:
        rows = yub_rows(_json(net, sparql_url(day), SPARQL_HEADERS), day)
    except Exception as e:
        return None, f"Wikidata alınmadı: {_err(e)}"
    for r in rows:
        if r["why"]:
            report.append((r["name"], r["years"], r["why"]))
    cands = [r for r in rows if not r["why"]]
    if not cands:
        return None, "bu gün 25-ə bölünən yubiley yoxdur" if not rows else "namizədlər siyasətçi və ya vəzifəli şəxsdir"
    try:
        page = _json(net, ox.WIKI_API.format(f"{day.day}_{MONTHS[day.month - 1]}"), WIKI_HEADERS)
        born = born_names(ox.tarix_parse(str((page.get("parse") or {}).get("wikitext") or "")))
    except Exception as e:
        return None, f"gün səhifəsi alınmadı: {_err(e)}"
    left = []
    for r in cands:
        if _name_key(r["name"]) in born or _name_key(r["title"]) in born:
            report.append((r["name"], r["years"], "«Bu gün tarixdə» xəbərindədir (gün səhifəsinin doğumlar siyahısı)"))
        else:
            left.append(r)
    if not left:
        return None, "namizədlər «Bu gün tarixdə» xəbərindədir"
    left = left[:YUB_CHECK]
    try:
        find = wiki_info(_json(net, info_url([r["title"] for r in left]), WIKI_HEADERS))
    except Exception as e:
        return None, f"Vikipediya girişləri alınmadı: {_err(e)}"
    good = []
    for r in left:
        info = find(r["title"])
        extract = (info or {}).get("extract") or ""
        if not lead_ok(extract, day, r["year"]):
            report.append((r["name"], r["years"], "az.wikipedia girişində bu doğum tarixi yoxdur"))
        elif _leader(extract) or _family(extract):
            report.append((r["name"], r["years"], "girişdə rəhbərliyin adı keçir"))
        elif not r.get("dead") and (POLITICAL.search(_low(extract)) or SENSITIVE.search(_low(extract))):
            report.append((r["name"], r["years"], "sağ şəxsin girişində siyasət, məhkəmə və ya hadisə mövzusu var"))
        else:
            good.append(dict(r, extract=extract))
            report.append((r["name"], r["years"], ""))
    if not good:
        return None, "namizədlər az.wikipedia girişinin yoxlamasından keçmədi"
    return yub_item(day, good[0], good[1:3])


def yubiley(now, net, done=()):
    day = now.date()
    key = f"yubiley-{day.isoformat()}"
    if key in done:
        return None, "artıq dərc olunub"
    if not _due(now, SLOT["yubiley"]):
        return None, f"vaxtı deyil ({SLOT['yubiley']})"
    item, why = yubiley_day(net, day)
    return item or _stub("yubiley", key, SLOT["yubiley"], why), why


# --- İstehsal və sınaq ------------------------------------------------------------------------------------

BUILDERS = (yubiley, afisa, hefte, kino, vikipediya_gun, vikipediya_ay)


def items(root, now, fetch=None, done=None):
    """now anında (Bakı) dərc olunacaq xəbərlər. Sorğu yalnız xəbərin vaxt pəncərəsində və açarı done-da yoxdursa gedir.
    worth=False olanlar da qaytarılır (səbəbi «why»-dadır). Şəbəkə və ya cavab xətası həmin xəbəri buraxır."""
    now = _now(now)
    done = set(done or ())
    net = _net(fetch)
    out = []
    for build in BUILDERS:
        try:
            item, _ = build(now, net, done)
        except Exception:
            item = None
        if item:
            out.append(item)
    return out


def _verdict(item, why=""):
    if not item:
        return f"⏭ Dərc olunmazdı: {why or 'səbəb yazılmayıb'}"
    return "✅ Dərc olunardı" if item.get("worth") else f"⏭ Dərc olunmazdı: {item.get('why') or 'səbəb yazılmayıb'}"


def _label(d, today):
    rel = {0: "bu gün", -1: "dünən", 1: "sabah"}.get((d - today).days, "")
    return f"{ox.day_text(d)} {d.year}, {WEEKDAYS[d.weekday()]}" + (f" ({rel})" if rel else "")


def _show(label, item, why):
    head = f"**{label}" + (f", saat {item['slot']}:**" if item else ":**")
    return [head, ""] + (ox.render(item) if item else []) + [_verdict(item, why), ""]


def _safe(fn, *args):
    try:
        return fn(*args)
    except Exception as e:  # sınaq heç vaxt yıxılmır
        return None, f"gözlənilməz xəta: {_err(e)}"


def _sinaq_wiki(net, today):
    md = ["## 4. «Dünən Vikipediyada ən çox oxunanlar» (hər gün 13:00; hazır deyilsə 15:00; cümə yalnız 15:00)", ""]
    shown = None
    for back in (0, 1):
        try:
            doc = _json(net, FEED_URL.format(today - back * DAY), WIKI_HEADERS)
        except Exception as e:
            md += [f"> {ox.day_text(today - back * DAY)} lenti alınmadı: {_err(e)}", ""]
            continue
        day, rows = gun_rows(doc)
        if not day:
            md += [f"> {ox.day_text(today - back * DAY)} lentində «ən çox oxunanlar» hələ yoxdur.", ""]
            continue
        bad = gun_check(net, rows, today)
        item, why = (None, bad) if bad else _safe(gun_item, day, rows, today)
        label = f"{ox.day_text(day)} {day.year} siyahısı, {ox.day_text(day + DAY)} dərc olunardı"
        if day != today - DAY:
            label += " — ən son real hal"
        md += _show(label, item, why)
        shown = rows
        break
    if shown:
        bad = [r for r in shown[:15] if r.get("skip")]
        if bad:
            md += ["Süzgəcdən keçməyənlər (ilk 15 məqalədən):", ""]
            md += [f"- {_q(r['title'])} — {ox.az_num(r['views'], 0)} baxış: {r['skip']}" for r in bad] + [""]
    return md


def _sinaq_ay(net, today):
    year, month = _prev_month(today)
    md = ["## 5. «Ayın ən çox oxunanları» (ayın 2-si 13:30; 2-si çərşənbə və ya cümədirsə 1-i)", ""]
    try:
        y, m, rows = ay_rows(_json(net, TOP_URL.format(year, month), WIKI_HEADERS))
    except Exception as e:
        return md + [f"> {MONTHS[month - 1]} siyahısı alınmadı: {_err(e)}", ""]
    if (y, m) != (year, month) or not rows:
        return md + ["> Aylıq siyahı boşdur.", ""]
    try:
        find = wiki_info(_json(net, info_url([r["title"] for r in rows[:INFO_N]]), WIKI_HEADERS))
    except Exception as e:
        return md + [f"> Məqalələrin girişi alınmadı: {_err(e)}", ""]
    item, why = _safe(ay_item, year, month, rows, find, today)
    md += _show(f"{MONTHS[month - 1]} {year} siyahısı — ən son real hal", item, why)
    bad = [r for r in rows[:INFO_N] if r.get("skip")]
    if bad:
        md += ["Süzgəcdən keçməyənlər (ilk 20 məqalədən):", ""]
        md += [f"- {_q(r['title'])} — {ox.az_num(r['views'], 0)} baxış: {r['skip']}" for r in bad] + [""]
    return md


def _sinaq_yub(net, today, budget=20):
    md = ["## 6. «Yubileylər» (hər gün 09:00, tapılanda; gündə ən çox bir xəbər)", ""]
    for back in range(0, 4):
        day = today - back * DAY
        if back and net.count >= budget - 3:
            md += ["> Sınağın sorğu həddi: daha əvvəlki günlərə baxılmadı.", ""]
            break
        report = []
        item, why = _safe(yubiley_day, net, day, report)
        label = _label(day, today) + ("" if not back else " — ən son real hal")
        md += _show(label, item, why)
        if report:
            md += ["Namizədlər:", ""]
            md += [f"- {n} ({y} il): {w or '✅ yoxlamadan keçdi'}" for n, y, w in report] + [""]
        if item:
            break
    return md


def _reach(net):
    md = ["## Sorğular və GitHub-dan əlçatanlıq", "", "| Host | Nəticə | Bayt | Saniyə |", "|---|---|---|---|"]
    md += [f"| {h} | {s} | {n} | {t} |" for h, _, s, n, t in net.log]
    hosts = {}
    for h, _, s, _, _ in net.log:
        hosts.setdefault(h, set()).add(s)
    md += ["", "Xülasə: " + "; ".join(f"{h} — {', '.join(sorted(v))}" for h, v in sorted(hosts.items())), ""]
    return md


def _sinaq_afisa(net, today):
    md = ["## 1. «Günün afişası» (hər gün 10:00, cümədən başqa)", ""]
    days = [d for d in (today + k * DAY for k in range(3)) if d.weekday() != 4][:2]
    for d in days:
        item, why = _safe(afisa_day, net, d)
        md += _show(_label(d, today), item, why)
    sat = today + DAY * ((5 - today.weekday()) % 7)
    if today.weekday() == 6:
        sat = today - DAY
    md += ["## 2. «Həftəsonu afişası» (cümə 12:00)", ""]
    item, why = _safe(hefte_days, net, sat)
    md += _show(f"{ox.day_text(sat)} – {ox.day_text(sat + DAY)} (cümə, {ox.day_text(sat - DAY)} dərc olunardı)", item, why)
    return md


def _sinaq_kino(net, today):
    md = ["## 3. «Həftənin kino premyeraları» (çərşənbə 12:00; filmlər cümə axşamı çıxır)", ""]
    try:
        films = kino_parse(net(CINEMA_URL).decode("utf-8", "replace"))
    except Exception as e:
        return md + [f"> cinemastercard.az alınmadı: {_err(e)}", ""]
    dates = sorted({f["date"] for f in films if not f["sport"] and f["date"] > today})
    if not dates:
        return md + ["> «Tezliklə» siyahısında gələcək tarixli film tapılmadı.", ""]
    release = dates[0]
    item, why = _safe(kino_item, release, films)
    return md + _show(f"{ox.day_text(release)} {release.year} buraxılışı, {ox.day_text(release - DAY)} dərc olunardı", item, why)


def _part(fn, *args):
    try:
        return fn(*args)
    except Exception as e:  # sınaq heç vaxt yıxılmır
        return [f"> gözlənilməz xəta: {_err(e)}", ""]


def sinaq(root, now=None, fetch=None):
    """Nümunələr (Markdown), real sorğularla (~20). Bugünkü hallar, yoxdursa ən son real hal, adı ilə. Heç nə yazmır."""
    root = pathlib.Path(root)
    now = _now(now)
    today = now.date()
    net = _net(fetch, pause=1.0)
    md = ["# Mədəniyyət və bilik xəbərləri (oz_medeniyyet.py): sınaq", "",
          f"{now:%d.%m.%Y %H:%M} (Bakı vaxtı). Sayta heç nə yazılmır. İstehsalda gündə ən çox 10 sorğu gedir.", "",
          "## Bu an dərc olunacaqlar", ""]
    todays = items(root, now, net)
    md += [f"- {i['slot']} · {i['key']} · {'✅' if i['worth'] else '⏭ ' + str(i.get('why') or '')}" for i in todays] \
        or [f"- Saat {now:%H:%M}-da heç bir xəbərin vaxtı deyil (pəncərələr: "
            f"{', '.join(sorted(set(SLOT.values()) | set(WIKI_TRIES)))}, hər biri 45 dəqiqə)."]
    md += [""]
    for fn in (_sinaq_afisa, _sinaq_kino, _sinaq_wiki, _sinaq_ay, _sinaq_yub):
        md += _part(fn, net, today)
    md += _part(_reach, net)
    md += [f"Bu sınaqda {net.count} sorğu göndərilib.", ""]
    return md


def _arg(argv, name):
    return argv[argv.index(name) + 1] if name in argv and argv.index(name) + 1 < len(argv) else None


def main(argv):
    if "--sinaq" not in argv:
        print(__doc__)
        return 0
    root = pathlib.Path(_arg(argv, "--root") or pathlib.Path(__file__).parent)
    when = _arg(argv, "--now")
    now = datetime.datetime.fromisoformat(when) if when else None
    sys.stdout.write("\n".join(sinaq(root, now)) + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
