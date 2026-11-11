"""8ulduz-un öz xəbərləri, mərhələ 2: gündəlik həyat (sahib, 2026-11-10: «Mərhələ 2-ni qur»). Sayta hələ qoşulmayıb.

Şablon xəbərlər, süni intellektsiz: hər rəqəm, ad, tarix və yer mənbənin özündəndir, vaxt Bakı vaxtıdır.

1. «DİM təqvimi» (dim.gov.az/az/teqvim, 09:00).
   - Bazar ertəsi: həftənin (bazar ertəsi–bazar) icmalı: qeydiyyatın son günləri, imtahan günləri, başlayan qeydiyyatlar.
   - Qalan günlər, həftə sonu da: qeydiyyatın son günü olan səhər xəbər. Bazar ertəsinin son günü həftənin icmalındadır.
   - Yalnız «Qeydiyyat» və «İmtahan» növləri oxunur. Status sözünə («Keçirilir», «Keçiriləcək») baxılmır: səhifə onu gec
     yeniləyir (7 noyabrın SAT imtahanı 10 noyabrda da «Keçiriləcək» idi). Hər şey tarixlərdən hesablanır.
   - Siyahı başlanğıc tarixinə görə sıralanıb, səhifədə 12 tədbir var (2026-11-10: 161 səhifə, sonu keçmiş tədbirlərdir).
     Lazım olan günə çatanadək ən çox 3 səhifə oxunur; çatmasa xəbər dərc olunmur. Kateqoriya xanası boş ola bilər
     (taksi sürücüləri): sətirlər yerinə görə yox, quruluşa görə oxunur.
2. «Səyyar ASAN xidmət» (asan.gov.az/mobile-service, 10:00): sabah yeni məntəqədə işə başlayan avtobuslar, bir xəbərdə.
   Məlumat yalnız data-place və data-date atributlarındadır. Hər məntəqə başlanğıcından bir gün əvvəl bir dəfə xəbər olur:
   uzun müddətli açar yaddaşı olmasa da təkrar yoxdur. Artıq işləyən məntəqə yazılmır.
3. «ASAN müraciət» (bazar ertəsi 11:00): ötən həftə «ASAN müraciət» sistemi ilə göndərilən problemlər, regionlar üzrə.
   VXSİDA-nın Publik Data Portalındakı CSV (Google Drive, UTF-16). Məlumat yalnız iş günləri üçündür. Həftənin son iş
   günü (oz_teqvim.qeyri_is_gunu) məlumatda yoxdursa, xəbər dərc olunmur. Bir həftə əvvəlki say yalnız iş günlərinin
   sayı eyni olanda yazılır. CSV alınmasa, oxunmasa və ya köhnə olsa, faylın ünvanı portalın səhifəsindən təzədən götürülür.
4. «Polisin gündəlik icmalı» (bazar ertəsi–şənbə 12:00, t.me/s/polisazerbaycan): yalnız «... polis tərəfindən:» icmalı.
   Ayrı cinayət xəbərləri sonrakı (Haiku) mərhələsinindir. Xəbər icmalın öz tarixi ilə yazılır, dərc gününün yox: bazar
   ertəsi icması şənbə və bazarı birlikdə verir. Üç əsas rəqəm (açılan cinayətlər, saxlanılan axtarışdakılar və
   şübhəlilər) yoxdursa, icmal dərc olunmur. Bu gün dərc olunmayan icmal köhnədir. Bazar günü və bayramlarda sorğu getmir.

Sorğular yalnız fetch ilə (15 saniyə), hər mənbəyə öz 30 dəqiqəlik pəncərəsində: DİM 09:00, ASAN 10:00, müraciət 11:00,
polis 11:45 (icmal adətən 10:30–11:30-da çıxır). Pəncərə başına bir sorğu turu ilə gündə: adi gün 3–4, bazar günü 2–3,
bazar ertəsi 4–7 sorğu (DİM 1–3 səhifə, ASAN 1, polis 1, müraciət 1–2). done: bu gün dərc olunmuş və ya qurulmuş açarlar. Açar
qabaqcadan bilinir (dim-gun-<gün>, dim-hefte-<bazar ertəsi>, seyyar-asan-<sabah>, asan-muraciet-<həftə>,
polis-icmal-<dünən>): done-da olan mənbəyə sorğu getmir. «Bu gün xəbər yoxdur» nəticəsi də (müraciət məlumatının bazar
ertəsi 11:00-da hələ yenilənməməsi daxil) həmin açarla, worth=False qayıdır: canlı onu da done-a yazsa, pəncərədə ikinci
sorğu getmir. Müvəqqəti hal (şəbəkə xətası, polisin icmalı hələ çıxmayıb) başqa açarla qayıdır, növbəti dövrədə yenə
yoxlanır. Gündə ən çox 8 sorğu iki halda təmin olunur: çağırış 30 dəqiqədən bir olanda (pəncərə başına bir tur) və ya
canlı qaytarılan bütün açarları (worth=False olanları da) done-a yazanda. Çağırış 10 dəqiqədən bir olsa və done-a yalnız
dərc olunanlar yazılsa, pəncərə ən çox 3 tur deməkdir: sorğuların sayı 3 dəfəyədək artır.
Sınaq: python oz_gundelik.py --sinaq --root DIR [--now 2026-11-10T09:00+04:00]
"""
import csv
import datetime
import html
import io
import pathlib
import re
import sys
import time
import urllib.parse

import oz_teqvim as tq
import oz_xeber as ox

BAKU = ox.BAKU
DAY = datetime.timedelta(days=1)
TITLE_MAX = 110
TIMEOUT = 15
PAUSE = 1.0                                # eyni sayta iki sorğu arasında ən azı bu qədər saniyə
WINDOW = datetime.timedelta(minutes=30)    # mənbənin gündəlik sorğu pəncərəsi
WEEKDAYS = tq.WEEKDAYS

DIM_URL = "https://dim.gov.az/az/teqvim"
DIM_CREDIT = "Dövlət İmtahan Mərkəzi"
DIM_FROM = "Dövlət İmtahan Mərkəzinin (DİM) təqviminə görə"
DIM_AT = (9, 0)
DIM_PAGES = 3
DIM_LINES = 12

ASAN_URL = "https://asan.gov.az/mobile-service"
ASAN_CREDIT = "ASAN xidmət"
ASAN_AT = (10, 0)

MUR_PAGE = "https://opendata.vxsida.gov.az/statistic-detail/6"
MUR_ANCHOR = "ASAN_Appeal__Number_of_problems_by_region__csv"
MUR_CSV = "https://drive.google.com/uc?export=download&id=1mWGq3GUXTrAHSw3IXq3T6KOJzBQzOye_"
MUR_CREDIT = "VXSİDA, Publik Data Portalı"
MUR_FROM = "VXSİDA-nın Publik Data Portalındakı məlumata görə"
MUR_AT = (11, 0)
MUR_REGIONS = 15

TG_URL = "https://t.me/s/polisazerbaycan"
POLIS_CREDIT = "Daxili İşlər Nazirliyi"
POLIS_FROM = "Daxili İşlər Nazirliyinin məlumatına görə"
POLIS_AT = (11, 45)
POLIS_LAG = 4   # icmalın son günü dərc günündən ən çox bu qədər gün əvvəl ola bilər (bayramdan sonra bir neçə gün birlikdə)


# --- Yazı köməkçiləri -------------------------------------------------------------------------------------------------------

_ONES = ("sıfır", "bir", "iki", "üç", "dörd", "beş", "altı", "yeddi", "səkkiz", "doqquz")
_TENS = ("", "on", "iyirmi", "otuz", "qırx", "əlli", "altmış", "yetmiş", "səksən", "doxsan")


def _say(n):
    """Ədədin oxunuşunun son sözü, şəkilçi ona görə seçilir: 64 «altmış dörd» -> «dörd», 30 -> «otuz», 100 -> «yüz»."""
    n = abs(int(n))
    if n == 0:
        return "sıfır"
    if n % 10:
        return _ONES[n % 10]
    if n % 100:
        return _TENS[n % 100 // 10]
    if n % 1000:
        return "yüz"
    if n % 1000000:
        return "min"
    if n % 1000000000:
        return "milyon"
    return "milyard"


def _back(word):
    return ox._last_vowel(word) in "aıou"


def _n(n):
    return ox.az_num(n, 0)


def num_loc(n):
    """Yerlik hal: «4-də», «30-da», «19-da»."""
    return f"{_n(n)}-{'da' if _back(_say(n)) else 'də'}"


def num_abl(n):
    """Çıxışlıq hal: «12-dən», «6-dan», «1-dən»."""
    return f"{_n(n)}-{'dan' if _back(_say(n)) else 'dən'}"


def num_poss(n):
    """Mənsubiyyət: «67-si», «6-sı», «53-ü», «30-u», «11-i»."""
    word = _say(n)
    return f"{_n(n)}-{'s' if ox._vowel_end(word) else ''}{ox._four(word, ('ı', 'i', 'u', 'ü'))}"


def month_gen(month):
    """«noyabrın», «aprelin», «iyunun»."""
    name = ox.MONTHS[month - 1]
    return name + ox._four(name, ("ın", "in", "un", "ün"))


def date_loc(d):
    """«noyabrın 12-də»."""
    return f"{month_gen(d.month)} {num_loc(d.day)}"


def date_abl(d):
    """«noyabrın 12-dən»."""
    return f"{month_gen(d.month)} {num_abl(d.day)}"


def _cap(text):
    """Cümlənin ilk hərfi: «i» -> «İ» (Python-un upper()-i «I» verir)."""
    if not text:
        return text
    return ("İ" if text[0] == "i" else text[0].upper()) + text[1:]


def _join(parts):
    parts = [p for p in parts if p]
    if len(parts) <= 1:
        return "".join(parts)
    return ", ".join(parts[:-1]) + " və " + parts[-1]


def _span(a, b):
    """«12–26 noyabr», «30 noyabr – 6 dekabr», «31 dekabr 2026 – 4 yanvar 2027»."""
    if a == b:
        return ox.day_text(a)
    if (a.year, a.month) == (b.year, b.month):
        return f"{a.day}–{b.day} {ox.MONTHS[a.month - 1]}"
    if a.year == b.year:
        return f"{ox.day_text(a)} – {ox.day_text(b)}"
    return f"{ox.day_text(a)} {a.year} – {ox.day_text(b)} {b.year}"


def days_loc(days):
    """İcmalın günləri: «noyabrın 4-də», «oktyabrın 31-də və noyabrın 1-də», «noyabrın 6-dan 10-dək»,
    «noyabrın 7-də, 8-də və 10-da»."""
    days = sorted(days)
    if len(days) == 1:
        return date_loc(days[0])
    if len(days) >= 3 and (days[-1] - days[0]).days == len(days) - 1:
        a, b = days[0], days[-1]
        end = f"{_n(b.day)}-dək" if (a.year, a.month) == (b.year, b.month) else f"{month_gen(b.month)} {_n(b.day)}-dək"
        return f"{month_gen(a.month)} {num_abl(a.day)} {end}"
    parts, month = [], None
    for d in days:
        parts.append(num_loc(d.day) if d.month == month else date_loc(d))
        month = d.month
    return _join(parts)


def _dat(name):
    """Yönlük hal: «Bakıya», «Gəncəyə», «Abşerona», «Sumqayıta»."""
    return name + ("y" if ox._vowel_end(name) else "") + ("a" if _back(name) else "ə")


def _gen_place(name):
    """Yiyəlik hal: «Binəqədi rayonunun», «Bakının», «Ağstafa şəhərinin»."""
    return name + ("n" if ox._vowel_end(name) else "") + ox._four(name, ("ın", "in", "un", "ün"))


def _dmy(text):
    m = re.search(r"(\d\d)\.(\d\d)\.(\d{4})", text or "")
    if not m:
        return None
    try:
        return datetime.date(int(m.group(3)), int(m.group(2)), int(m.group(1)))
    except ValueError:
        return None


def _wd(d):
    return WEEKDAYS[d.weekday()]


def _now(now):
    if now is None:
        return datetime.datetime.now(BAKU)
    if now.tzinfo is None:
        return now.replace(tzinfo=BAKU)
    return now.astimezone(BAKU)


def _open(now, at):
    """Mənbənin gündəlik pəncərəsi: at (saat, dəqiqə) -dan 30 dəqiqə."""
    start = now.replace(hour=at[0], minute=at[1], second=0, microsecond=0)
    return start <= now < start + WINDOW


def _leader(text):
    try:
        return bool(ox.needs_owner(text))
    except Exception:
        return bool(re.search(r"prezident|birinci xanım|vitse-prezident|əliyev", ox._low(text)))


def _guard(item):
    """Rəhbərliyin adı keçən xəbər avtomatik dərc olunmur (sahibin qaydası); başlıq 110 hərfdən uzun olmamalıdır."""
    if not item.get("worth"):
        return item
    if _leader("\n".join([item["title"], item["lead"], *item["body"]])):
        return dict(item, worth=False, why="rəhbərliyin adı keçir: avtomatik dərc olunmur")
    if len(item["title"]) > TITLE_MAX:
        return dict(item, worth=False, why=f"başlıq {TITLE_MAX} hərfdən uzundur")
    return item


def _item(kind, key, title, lead, body, credit, link, topic, slot, worth=True, why="", lst=False):
    out = {"kind": kind, "key": key, "title": title, "lead": lead, "body": list(body), "credit": credit, "link": link,
           "topic": topic, "slot": slot, "worth": bool(worth)}
    if lst:
        out["list"] = True
    if not worth:
        out["why"] = why or "səbəb yazılmayıb"
    return out


# --- Şəbəkə -----------------------------------------------------------------------------------------------------------------

class _Net:
    """fetch-in üstündə: bir çağırışda hər ünvana bir sorğu (xəta da yadda qalır), eyni sayta iki sorğu arasında PAUSE saniyə.
    count göndərilən sorğuları, log hər sorğunun nəticəsini saxlayır (sınaqda GitHub-dan çıxışı göstərmək üçün)."""

    def __init__(self, fetch):
        self.fetch, self.cache, self.count, self.last, self.log = fetch, {}, 0, {}, []

    def __call__(self, url, timeout=None, headers=None):
        if url not in self.cache:
            if self.fetch is None:
                raise LookupError("sorğu funksiyası yoxdur")
            host = urllib.parse.urlsplit(url).hostname or ""
            if not isinstance(self.fetch, _Net):
                wait = self.last.get(host, -1e9) + PAUSE - time.monotonic()
                if wait > 0:
                    time.sleep(wait)
            self.count += 1
            try:
                kw = {"timeout": TIMEOUT}
                if headers:
                    kw["headers"] = headers
                data = self.fetch(url, **kw)
                self.cache[url] = (data, None)
                self.log.append((url, f"{len(data)} bayt"))
            except Exception as e:
                self.cache[url] = (None, e)
                self.log.append((url, f"{type(e).__name__}: {getattr(e, 'reason', '') or e}"[:160]))
            self.last[host] = time.monotonic()
        data, err = self.cache[url]
        if err is not None:
            raise err
        return data


def _default_fetch():
    try:
        return ox._u().fetch
    except Exception:
        return None


def _text(raw):
    return raw.decode("utf-8", "replace") if isinstance(raw, bytes) else str(raw)


# --- 1. DİM təqvimi ---------------------------------------------------------------------------------------------------------

_DIM_SPLIT = re.compile(r'<div\s+class="item\s+shadow\b')
_DIM_NAME = re.compile(r'<a\s+href="([^"]*)"\s+class="dark-color"\s*>(.*?)</a>', re.S)
_DIM_SPAN = re.compile(r'<span\s+class="label\b([^"]*)"\s*>(.*?)</span>', re.S)


def dim_events(page):
    """Təqvim səhifəsi -> [{name, link, status, kind, cat, start, end}], səhifədəki sıra ilə. Başlanğıc tarixi olmayan sətir
    götürülmür. Xanalar quruluşa görə oxunur: boş kateqoriya xanası növbəti tədbirin gün nişanını («07») götürmür."""
    out = []
    for part in _DIM_SPLIT.split(page)[1:]:
        m = _DIM_NAME.search(part)
        if not m:
            continue
        i = part.find('class="inner-wrapper"')
        j = part.find("</div>", i) if i >= 0 else -1
        status, start, end, rest = "", None, None, []
        for cls, inner in _DIM_SPAN.findall(part[i:j] if j > i else ""):
            text = ox._clean(inner)
            if "label-primary" in cls:
                status = text
            elif text.startswith("Başlanğıc tarixi"):
                start = _dmy(text)
            elif text.startswith("Bitmə tarixi"):
                end = _dmy(text)
            elif text:
                rest.append(text)
        name = ox._clean(m.group(2))
        if not name or not start:
            continue
        link = html.unescape(m.group(1)).strip()
        out.append({"name": name, "link": link if link.startswith("https://dim.gov.az/") else "",
                    "status": status, "kind": rest[0] if rest else "", "cat": rest[1] if len(rest) > 1 else "",
                    "start": start, "end": end})
    return out


def dim_get(net, need):
    """Təqvimin səhifələri, başlanğıc tarixi need-dən sonra olan tədbirə çatanadək (ən çox DIM_PAGES).
    Qaytarır (tədbirlər, tam): tam=False — need-ə qədərki tədbirlərin hamısı oxunmayıb."""
    events, seen = [], set()
    for n in range(1, DIM_PAGES + 1):
        rows = dim_events(_text(net(DIM_URL if n == 1 else f"{DIM_URL}?page={n}")))
        if not rows:
            if n == 1:
                raise ValueError("təqvimdə tədbir tapılmadı")
            return events, False  # davam səhifəsi oxunmadı: natamam təqvimdən icmal yazılmır
        for e in rows:
            k = (e["name"], e["start"], e["end"], e["kind"])
            if k not in seen:
                seen.add(k)
                events.append(e)
        if max(e["start"] for e in rows) > need:
            return events, True
    return events, False


def _exam_name(name):
    """«GRE, 09:00» -> «GRE (saat 09:00)», «TOEFL iBT,9:00» -> «TOEFL iBT (saat 09:00)»."""
    m = re.match(r"^(.*?)\s*,\s*(\d{1,2}):(\d\d)$", name)
    return f"{m.group(1)} (saat {int(m.group(2)):02d}:{m.group(3)})" if m else name


def _stem(name):
    """Qeydiyyatın adı imtahanın adına çevrilir: «X imtahanına qeydiyyat (Y)» -> «x imtahanı (y)»,
    «X imtahana qeydiyyat» -> «x imtahan», «X imtahanına (Y) qeydiyyat» -> «x imtahanı (y)»."""
    s = " ".join(ox._low(name).split())
    s = re.sub(r"imtahanına\s+(\([^)]*\)\s+)?qeydiyyatı?", lambda m: "imtahanı" + (" " + m.group(1).strip() if m.group(1) else ""), s)
    s = re.sub(r"imtahana\s+(\([^)]*\)\s+)?qeydiyyatı?", lambda m: "imtahan" + (" " + m.group(1).strip() if m.group(1) else ""), s)
    return " ".join(s.split())


def _exam_of(reg, events):
    """Qeydiyyatın öz imtahanı: adı qeydiyyatın adından alınanla eyni olan, son gündən sonrakı ilk imtahan."""
    stem = _stem(reg["name"])
    if stem == " ".join(ox._low(reg["name"]).split()):
        return None
    found = [e for e in events if e["kind"] == "İmtahan" and e["start"] >= reg["end"]
             and " ".join(ox._low(e["name"]).split()) == stem]
    return min(found, key=lambda e: e["start"]) if found else None


def _dim_rows(events, first, last):
    """Həftənin sətirləri: (gün, sıra, növ, tədbir). Sıra: son gün 0, imtahan 1, başlayan qeydiyyat 2.
    Rəhbərliyin adı keçən tədbir yazılmır (ikinci siyahıda qaytarılır)."""
    rows, skipped = [], []
    for e in events:
        if _leader(e["name"]):
            skipped.append(e["name"])
            continue
        if e["kind"] == "Qeydiyyat":
            if e["end"] and first <= e["end"] <= last:
                rows.append((e["end"], 0, "son", e))
            if first <= e["start"] <= last and e["start"] != e["end"]:
                rows.append((e["start"], 2, "başla", e))
        elif e["kind"] == "İmtahan":
            end = e["end"] or e["start"]
            if e["start"] <= last and end >= first:
                rows.append((max(e["start"], first), 1, "imtahan", e))
    rows.sort(key=lambda r: (r[0], r[1], r[3]["name"]))
    return rows, skipped


def _dim_line(row):
    d, _, what, e = row
    when = f"{ox.day_text(d)}, {_wd(d)}"
    if what == "son":
        return f"{when} — qeydiyyatın son günü: {e['name']}"
    if what == "başla":
        end = f" (son gün: {ox.day_text(e['end'])})" if e["end"] else ""
        return f"{when} — qeydiyyat başlayır: {e['name']}{end}"
    days = f" ({_span(e['start'], e['end'])})" if e["end"] and e["end"] != e["start"] else ""
    return f"{when} — imtahan: {_exam_name(e['name'])}{days}"


def dim_week_item(events, monday, complete=True):
    """Bazar ertəsinin həftəlik icmalı: həftənin (bazar ertəsi–bazar) son günləri, imtahanları və başlayan qeydiyyatları."""
    sunday = monday + 6 * DAY
    week = _span(monday, sunday)
    key = f"dim-hefte-{monday.isoformat()}"
    args = ("dim-hefte", key, f"DİM-in bu həftəki təqvimi ({week})")
    tail = (DIM_CREDIT, DIM_URL, "təqvim", "09:00")
    if not complete:
        return _item(*args, f"{DIM_FROM}: həftənin tədbirləri oxunmadı.", [], *tail, worth=False,
                     why=f"təqvimin ilk {DIM_PAGES} səhifəsində həftənin sonuna çatılmadı")
    rows, skipped = _dim_rows(events, monday, sunday)
    if not rows:
        return _item(*args, f"{DIM_FROM}, {week} tarixlərində tədbir yoxdur.", [], *tail, worth=False,
                     why="bu həftə qeydiyyatın son günü, imtahan və ya yeni qeydiyyat yoxdur")
    count = {w: sum(1 for r in rows if r[2] == w) for w in ("son", "imtahan", "başla")}
    short = [f"{count['son']} qeydiyyatın son günü" if count["son"] else "",
             f"{count['imtahan']} imtahan" if count["imtahan"] else "",
             f"{count['başla']} yeni qeydiyyat" if count["başla"] else ""]
    verbs = [f"{count['son']} qeydiyyat başa çatır" if count["son"] else "",
             f"{count['imtahan']} imtahan keçirilir" if count["imtahan"] else "",
             f"{count['başla']} qeydiyyat başlayır" if count["başla"] else ""]
    body = [_dim_line(r) for r in rows[:DIM_LINES]]
    if len(rows) > DIM_LINES:
        body.append(f"Təqvimdə bu həftə daha {len(rows) - DIM_LINES} tədbir var.")
    item = _item("dim-hefte", key, f"DİM-in bu həftəki təqvimi: {_join(short)}",
                 f"{DIM_FROM}, {week} tarixlərində {_join(verbs)}.", body, *tail, lst=True)
    if skipped:
        item["skipped"] = skipped
    return item


def _deadline_title(e, when):
    name = e["name"]
    title = (f"{name} {when} başa çatır" if "qeydiyyat" in ox._low(name) else f"«{name}» üzrə qeydiyyat {when} başa çatır")
    if len(title) <= TITLE_MAX:
        return title
    if e["cat"]:
        title = f"{e['cat']} üzrə qeydiyyat {when} başa çatır"
        if len(title) <= TITLE_MAX:
            return title
    return f"DİM-in təqvimi: bir qeydiyyat {when} başa çatır"


def dim_day_item(events, day, complete=True):
    """Qeydiyyatın son günü olan səhərin xəbəri (bazar ertəsindən başqa). Son gün yoxdursa worth=False."""
    key = f"dim-gun-{day.isoformat()}"
    tail = (DIM_CREDIT, DIM_URL, "təqvim", "09:00")
    if not complete:
        return _item("dim-gun", key + "-natamam", f"DİM-in təqvimi: {ox.day_text(day)}", f"{DIM_FROM}: təqvim oxunmadı.", [],
                     *tail, worth=False, why=f"təqvimin ilk {DIM_PAGES} səhifəsində bu günə çatılmadı")
    ends = [e for e in events if e["kind"] == "Qeydiyyat" and e["end"] == day and not _leader(e["name"])]
    if not ends:
        return _item("dim-gun", key, f"DİM-in təqvimi: {ox.day_text(day)}",
                     f"{DIM_FROM}, bu gün qeydiyyatın son günü yoxdur.", [], *tail, worth=False,
                     why="bu gün qeydiyyatın son günü yoxdur")
    when = date_loc(day)
    if len(ends) == 1:
        e = ends[0]
        lead = f"{DIM_FROM}, «{e['name']}» bu gün, {when} başa çatır."
        if e["start"] < day:
            lead += f" Qeydiyyat {date_loc(e['start'])} başlayıb."
        exam = _exam_of(e, events)
        if exam:
            lead += f" İmtahan {date_loc(exam['start'])} keçiriləcək."
        return _item("dim-gun", key, _deadline_title(e, when), lead, [], DIM_CREDIT, e["link"] or DIM_URL, "təqvim", "09:00")
    body = []
    for e in sorted(ends, key=lambda x: (x["start"], x["name"])):
        exam = _exam_of(e, events)
        body.append(f"{e['name']}: {_span(e['start'], e['end'])}" + (f"; imtahan: {ox.day_text(exam['start'])}" if exam else ""))
    return _item("dim-gun", key, f"DİM-in təqvimi: {when} {len(ends)} qeydiyyat başa çatır",
                 f"{DIM_FROM}, bu gün, {when} {len(ends)} qeydiyyatın son günüdür.", body, *tail, lst=True)


def dim_items(now, net, done):
    day = now.date()
    if not _open(now, DIM_AT):
        return []
    if day.weekday() == 0:
        if f"dim-hefte-{day.isoformat()}" in done:
            return []
        events, complete = dim_get(net, day + 6 * DAY)
        return [dim_week_item(events, day, complete)]
    if f"dim-gun-{day.isoformat()}" in done:
        return []
    events, complete = dim_get(net, day)
    return [dim_day_item(events, day, complete)]


# --- 2. Səyyar ASAN xidmət ----------------------------------------------------------------------------------------------------

_SETTLEMENT = ("qəsəbəsi", "kəndi", "şəhərciyi")
_ADMIN = ("rayonu", "şəhəri", "qəsəbəsi", "kəndi", "şəhərciyi")


def _one_extra(long, short):
    """long sözü short-dan yalnız bir artıq hərflə fərqlənir: «Netftçala» / «Neftçala»."""
    return len(long) == len(short) + 1 and any(long[:i] + long[i + 1:] == short for i in range(len(long)))


def _fix_place(place, short):
    """Ünvanın ilk sözü avtobusun bu məntəqə üçün qısa adından yalnız bir artıq və ya əskik hərflə fərqlənirsə, mənbədə səhv
    yazılıb («Netftçala rayonu», qısa adı «Neftçala»): qısa addakı yazılış götürülür. Hərfi dəyişən fərq («Ağdam» / «Ağdaş»)
    başqa rayon ola bilər: ona toxunulmur."""
    head, sep, rest = place.partition(",")
    words = head.split()
    if (short and " " not in short and len(short) >= 4 and words
            and (_one_extra(words[0], short) or _one_extra(short, words[0]))):
        words[0] = short
        return " ".join(words) + sep + rest
    return place


def asan_stops(page):
    """Səhifə -> [{bus, place, short, start, end, days, link}]. Məlumat yalnız atributlardadır (data-place, data-date),
    görünən span-lar boşdur. Mənbədəki gün sayı tarixlərə uyğun deyilsə, say yazılmır."""
    out = []
    for art in re.split(r"<article\b", page)[1:]:
        art = art.split("</article>", 1)[0]
        h = re.search(r'<h3[^>]*>\s*<a\b[^>]*href="([^"]*)"[^>]*>(.*?)</a>', art, re.S)
        if not h:
            continue
        bus, link = ox._clean(h.group(2)), html.unescape(h.group(1)).strip()
        for tag, inner in re.findall(r"<a\b([^>]*\bdata-place=[^>]*)>(.*?)</a>", art, re.S):
            attrs = dict(re.findall(r'([\w-]+)="([^"]*)"', tag))
            short = ox._clean(inner)
            place = _fix_place(ox._clean(attrs.get("data-place", "")), short)
            m = re.match(r"\s*(\d\d\.\d\d\.\d{4})\s*-\s*(\d\d\.\d\d\.\d{4})(?:\s*,\s*(\d+)\s*-?\s*gün)?",
                         html.unescape(attrs.get("data-date", "")))
            if not (bus and place and m):
                continue
            start, end = _dmy(m.group(1)), _dmy(m.group(2))
            if not start or not end or end < start:
                continue
            days = (end - start).days + 1
            out.append({"bus": bus, "place": place, "short": short, "start": start, "end": end,
                        "days": days if m.group(3) and int(m.group(3)) == days else None,
                        "link": link if link.startswith("https://asan.gov.az/") else ""})
    return out


def _place_texts(place):
    """Məntəqənin yeri: (başlıq üçün, giriş üçün, siyahı üçün qısa ad).
    «Binəqədi rayonu, Biləcəri qəsəbəsi» -> «Biləcəri qəsəbəsində», «Binəqədi rayonunun Biləcəri qəsəbəsində», «Biləcəri»;
    «Ağstafa şəhəri, Hüseyn Arif küçəsi 8 (İcra nümayəndəliyinin binası)» -> «Ağstafa şəhərində»,
    «Ağstafa şəhərində (Hüseyn Arif küçəsi 8, İcra nümayəndəliyinin binası)», «Ağstafa»."""
    head, _, rest = place.partition(",")
    head, rest = head.strip(), rest.strip()
    if rest and "(" not in rest and ox._low(rest).split()[-1] in _SETTLEMENT:
        return ox.place_loc(rest), f"{_gen_place(head)} {ox.place_loc(rest)}", _plain(rest)
    if rest:
        inner = rest.replace(" (", ", ").replace("(", "").replace(")", "")
        return ox.place_loc(head), f"{ox.place_loc(head)} ({inner})", _plain(head)
    return ox.place_loc(head), ox.place_loc(head), _plain(head)


def _plain(name):
    words = name.split()
    return " ".join(words[:-1]) if len(words) > 1 and ox._low(words[-1]) in _ADMIN else name


def _bus_short(bus):
    return re.sub(r"\s*Səyyar\s+ASAN\s+xidmət\s+avtobusu\s*$", "", bus) or bus


def asan_item(stops, day):
    """Sabah (day + 1) yeni məntəqədə işə başlayan səyyar avtobuslar. Yoxdursa worth=False."""
    start = day + DAY
    new = sorted((s for s in stops if s["start"] == start), key=lambda s: (_az_key(s["bus"]), s["bus"], s["place"]))
    key = f"seyyar-asan-{start.isoformat()}"
    tail = (ASAN_CREDIT, ASAN_URL, "təqvim", "10:00")
    when = date_abl(start)
    if not new:
        return _item("seyyar-asan", key, f"Səyyar ASAN xidmət: {ox.day_text(start)}",
                     f"«ASAN xidmət»in cədvəlinə görə, {when} yeni məntəqədə işə başlayan səyyar avtobus yoxdur.", [],
                     *tail, worth=False, why="sabah yeni məntəqədə işə başlayan səyyar avtobus yoxdur")
    texts = [_place_texts(s["place"]) for s in new]

    def sentence(s, lead_loc, also=""):
        days = f" ({s['days']} gün)" if s["days"] else ""
        return f"{s['bus']}{also} {_span(s['start'], s['end'])} tarixlərində{days} {lead_loc} xidmət göstərəcək."

    if len(new) == 1:
        return _item("seyyar-asan", key, f"Səyyar ASAN xidmət avtobusu {when} {texts[0][0]} olacaq",
                     f"«ASAN xidmət»in cədvəlinə görə, {sentence(new[0], texts[0][1])}", [], ASAN_CREDIT,
                     new[0]["link"] or ASAN_URL, "təqvim", "10:00")
    names = [t[2] for t in texts]
    title = f"Səyyar ASAN xidmət avtobusları {when} {_join(names[:-1] + [ox.place_loc(names[-1])])} olacaq"
    if len(title) > TITLE_MAX:
        title = f"Səyyar ASAN xidmət avtobusları {when} {len(new)} məntəqədə xidmət göstərəcək"
    if len(new) == 2:
        lead = (f"«ASAN xidmət»in cədvəlinə görə, {sentence(new[0], texts[0][1])} "
                f"{sentence(new[1], texts[1][1], ' isə')}")
        return _item("seyyar-asan", key, title, lead, [], *tail)
    lead = (f"«ASAN xidmət»in cədvəlinə görə, {when} {len(new)} Səyyar ASAN xidmət avtobusu aşağıdakı məntəqələrdə "
            f"xidmət göstərəcək.")
    body = [f"{_bus_short(s['bus'])} avtobusu: {s['place']}, {_span(s['start'], s['end'])}"
            + (f" ({s['days']} gün)" if s["days"] else "") for s in new]
    return _item("seyyar-asan", key, title, lead, body, *tail, lst=True)


def asan_items(now, net, done):
    day = now.date()
    if not _open(now, ASAN_AT) or f"seyyar-asan-{(day + DAY).isoformat()}" in done:
        return []
    stops = asan_stops(_text(net(ASAN_URL)))
    if not stops:
        raise ValueError("cədvəldə məntəqə tapılmadı")
    return [asan_item(stops, day)]


# --- 3. «ASAN müraciət» -------------------------------------------------------------------------------------------------------

def mur_rows(raw):
    """CSV (UTF-16, BOM ilə; UTF-8 də olar) -> [(gün, region, problem sayı)]. Sütunlar adla tapılır."""
    if raw[:2] == b"\xff\xfe":
        text = raw[2:].decode("utf-16-le")
    elif raw[:2] == b"\xfe\xff":
        text = raw[2:].decode("utf-16-be")
    else:
        text = raw.decode("utf-8-sig")
    table = list(csv.reader(io.StringIO(text)))
    if not table:
        raise ValueError("CSV boşdur")
    head = [h.strip().lower() for h in table[0]]
    if not {"problem_count", "date", "region"} <= set(head):
        raise ValueError("CSV-nin sütunları gözlənilən kimi deyil")
    i_n, i_d, i_r = head.index("problem_count"), head.index("date"), head.index("region")
    out = []
    for row in table[1:]:
        if len(row) <= max(i_n, i_d, i_r):
            continue
        try:
            n = int(row[i_n].strip())
            d = datetime.date.fromisoformat(row[i_d].strip()[:10])
        except ValueError:
            continue
        region = " ".join(row[i_r].split())
        if n >= 0 and region:
            out.append((d, region, n))
    if not out:
        raise ValueError("CSV-də məlumat sətri yoxdur")
    return out


def mur_link(page):
    """Portalın səhifəsindən CSV-nin ünvanı (bağlantının id-si ilə)."""
    for tag in re.findall(r"<a\b[^>]*>", page):
        if MUR_ANCHOR in tag:
            m = re.search(r'href="([^"]+)"', tag)
            url = html.unescape(m.group(1)).strip() if m else ""
            return url if url.startswith("https://") else ""
    return ""


def mur_get(net, need=None):
    """CSV-nin sətirləri. Əvvəl bilinən ünvan; alınmasa, oxunmasa və ya son günü need-dən əvvəl olsa, portalın səhifəsindəki
    ünvan (Drive faylı dəyişə bilər). Köhnə də olsa oxunan məlumat qaytarılır: qərarı mur_item verir."""
    rows, err = None, None
    try:
        rows = mur_rows(net(MUR_CSV))
        if need is None or max(r[0] for r in rows) >= need:
            return rows
    except Exception as e:
        err = e
    try:
        url = mur_link(_text(net(MUR_PAGE)))
    except Exception:
        url = ""
    if url and url != MUR_CSV:
        try:
            fresh = mur_rows(net(url))
            if rows is None or max(r[0] for r in fresh) > max(r[0] for r in rows):
                return fresh
        except Exception as e:
            err = err or e
    if rows is not None:
        return rows
    raise err or ValueError("CSV alınmadı")


def _work_days(first, last):
    """Beşgünlük həftənin iş günləri (oz_teqvim); ili bilinməyən gün həftə içidirsə iş günü sayılır."""
    out, d = [], first
    while d <= last:
        if tq.qeyri_is_gunu(d) is not True:
            out.append(d)
        d += DAY
    return out


_ALPHA = "abcçdeəfgğhxıijkqlmnoöprsştuüvyz"


def _az_key(name):
    """Azərbaycan əlifbası ilə sıra: «Qəbələ» «Quba»dan, «Şirvan» «Tovuz»dan əvvəl."""
    return [_ALPHA.find(ch) if ch in _ALPHA else len(_ALPHA) for ch in ox._low(name)]


def mur_item(rows, monday):
    """Bazar ertəsinin xəbəri: ötən həftənin (bazar ertəsi–bazar) problemləri regionlar üzrə."""
    first, last = monday - 7 * DAY, monday - DAY
    key = f"asan-muraciet-{first.isoformat()}"
    tail = (MUR_CREDIT, MUR_PAGE, "icmal", "11:00")
    title0 = f"«ASAN müraciət»: {_span(first, last)}"
    work = _work_days(first, last)
    if not work:
        return _item("asan-muraciet", key, title0, f"{MUR_FROM}: ötən həftə iş günü olmayıb.", [], *tail, worth=False,
                     why="ötən həftə iş günü olmayıb")
    newest = max(r[0] for r in rows)
    if newest < work[-1]:
        return _item("asan-muraciet", key, title0, f"{MUR_FROM}: məlumat hələ yenilənməyib.", [], *tail,
                     worth=False, why=f"məlumat hələ yenilənməyib: son gün {ox.day_text(newest)} {newest.year}, "
                                      f"həftənin son iş günü {ox.day_text(work[-1])}")
    week = [r for r in rows if first <= r[0] <= last]
    total = sum(r[2] for r in week)
    if not total:
        return _item("asan-muraciet", key, title0, f"{MUR_FROM}: ötən həftə problem göndərilməyib.", [], *tail,
                     worth=False, why="ötən həftə problem göndərilməyib")
    by = {}
    for _, region, n in week:
        by[region] = by.get(region, 0) + n
    top = sorted(by.items(), key=lambda x: (-x[1], _az_key(x[0]), x[0]))
    days = sorted({r[0] for r in week if r[2]})
    title = f"Ötən həftə «ASAN müraciət» vasitəsilə {_n(total)} problem göndərilib"
    if top[0][1] == total:
        title += f", hamısı {_dat(top[0][0])} aiddir"
    elif len(top) == 1 or top[0][1] > top[1][1]:
        title += f", {num_poss(top[0][1])} {_dat(top[0][0])} aiddir"
    lead = (f"{MUR_FROM}, {_span(days[0], days[-1])} tarixlərində «ASAN müraciət» informasiya sistemi vasitəsilə "
            f"{_n(total)} problem göndərilib.")
    if len(top) > 1:
        lead += f" Ən çox problem {_join([f'{r} ({_n(n)})' for r, n in top[:4]])} üzrə qeydə alınıb."
    p_first, p_last = first - 7 * DAY, last - 7 * DAY
    prev = [r for r in rows if p_first <= r[0] <= p_last]
    if prev and len(_work_days(p_first, p_last)) == len(work):
        p_days = sorted({r[0] for r in prev})
        lead += f" Bir həftə əvvəl ({_span(p_days[0], p_days[-1])}) bu say {_n(sum(r[2] for r in prev))} olub."
    shown = ", ".join(f"{r} – {_n(n)}" for r, n in top[:MUR_REGIONS])
    if len(top) > MUR_REGIONS:
        rest = top[MUR_REGIONS:]
        shown += f", digər {len(rest)} region – {_n(sum(n for _, n in rest))}"
    body = [f"Problemlər {len(top)} regiona aiddir: {shown}."]
    return _item("asan-muraciet", key, title, lead, body, *tail)


def mur_items(now, net, done):
    day = now.date()
    if day.weekday() != 0 or not _open(now, MUR_AT):
        return []
    first = day - 7 * DAY
    if f"asan-muraciet-{first.isoformat()}" in done:
        return []
    work = _work_days(first, day - DAY)
    if not work:
        return [mur_item([], day)]  # bütün həftə bayram olub: sorğu getmir
    return [mur_item(mur_get(net, work[-1]), day)]


# --- 4. Polisin gündəlik icmalı ---------------------------------------------------------------------------------------------

_MON_GEN = {month_gen(m): m for m in range(1, 13)}
_DAY_TOK = re.compile(r"(\d{1,2})\s*[–—-]\s*(\d{1,2})\s*-\s*([^\W\d_]+)|(\d{1,2})\s*-\s*([^\W\d_]+)|([^\W\d_]+)|(\d{1,2})")
_NUM = r"(\d{1,3}(?:[   ]\d{3})+|\d+)"
_CORE = (
    ("crimes", re.compile(_NUM + r"\s+cinayətin açılması təmin (?:olunub|edilib)\s*(?:\((.*?)\))?\s*\.?$")),
    ("wanted", re.compile(_NUM + r"\s+axtarışda olan (?:şəxs|nəfər) saxlanılıb\s*(?:\((\d+)-[^\W\d_]+\s+borclu şəxs\))?\s*\.?$")),
    ("suspects", re.compile(_NUM + r"\s+cinayət törətməkdə şübhəli bilinən (?:şəxs|nəfər) saxlanılıb\s*\.?$")),
    ("missing", re.compile(_NUM + r"\s+itkin (?:kimi axtarılan|düşmüş) (?:şəxs|nəfər) tapılıb\s*\.?$")),
)
_SPLIT = re.compile(r"(\d+)-[^\W\d_]+\s+cari,\s*(\d+)-[^\W\d_]+\s+əvvəlki dövrlərdən$")


def _int(text):
    return int(re.sub(r"\D", "", text))


def tg_posts(page):
    """t.me/s səhifəsi -> [{id, url, when (Bakı vaxtı), text}], səhifədəki sıra ilə (köhnədən yeniyə)."""
    out = []
    for part in re.split(r'<div class="tgme_widget_message_wrap', page)[1:]:
        pid = re.search(r'data-post="([^"/]+)/(\d+)"', part)
        when = re.search(r'<time[^>]*\bdatetime="([^"]+)"', part)
        txt = re.search(r'<div class="tgme_widget_message_text[^"]*"[^>]*>(.*?)</div>', part, re.S)
        if not (pid and when and txt):
            continue
        try:
            dt = datetime.datetime.fromisoformat(when.group(1)).astimezone(BAKU)
        except ValueError:
            continue
        text = html.unescape(re.sub(r"<[^>]+>", "", re.sub(r"<br\s*/?>", "\n", txt.group(1))))
        out.append({"id": int(pid.group(2)), "url": f"https://t.me/{pid.group(1)}/{pid.group(2)}", "when": dt, "text": text})
    return out


def tg_before(page):
    """Səhifədəki köhnə yazılara keçid: «?before=6940» -> 6940 (yoxdursa None)."""
    m = re.search(r'href="/s/[^"?]+\?before=(\d+)"', page)
    return int(m.group(1)) if m else None


def _mk(posted, month, day):
    year = posted.year if month <= posted.month else posted.year - 1
    try:
        return datetime.date(year, month, day)
    except ValueError:
        return None


def phrase_days(phrase, posted):
    """«Oktyabrın 31-də və noyabrın 1-də» -> [31 okt, 1 noy]; «noyabrın 6-dan 10-dək», «noyabrın 6–10-da» -> 6..10 noyabr.
    İl dərc günündən götürülür (yanvarda yazılan dekabr keçən ildir). Tanınmayan söz varsa None."""
    month, out, start = None, [], None
    for m in _DAY_TOK.finditer(ox._low(phrase)):
        a, b, _, num, suf, word, bare = m.groups()
        if word is not None:
            if word in _MON_GEN:
                month = _MON_GEN[word]
            elif word != "və":
                return None
            continue
        if month is None:
            return None
        if a is not None:
            d1, d2 = _mk(posted, month, int(a)), _mk(posted, month, int(b))
            if not d1 or not d2 or d2 < d1:
                return None
            out += [d1 + DAY * i for i in range((d2 - d1).days + 1)]
            continue
        d = _mk(posted, month, int(num if num is not None else bare))
        if not d:
            return None
        if suf in ("dan", "dən"):
            start = d
            continue
        if suf in ("dək", "dak"):
            if not start or d < start:
                return None
            out += [start + DAY * i for i in range((d - start).days + 1)]
            start = None
            continue
        out.append(d)
    if start is not None or not out:
        return None
    return sorted(set(out))


def _bullets(lines):
    """Sətirlər -> bəndlər: yalnız «-» ilə başlayan sətir bənddir. «-» tək qalıbsa, mətn növbəti sətirdədir (28 oktyabr
    icmalı). Bənd olmayan başqa sətir (heşteq, əlavə qeyd) götürülmür: mənbənin bəndinə yad mətn qoşulmur."""
    out = []
    for line in lines:
        line = line.strip()
        if not line:
            continue
        if line[0] in "-–—":
            out.append(line[1:].strip())
        elif out and not out[-1]:
            out[-1] = line
    return [" ".join(b.split()) for b in out if b.strip()]


def polis_parse(text, posted):
    """İcmal yazısı -> {days, crimes, split, wanted, debt, suspects, missing, rest} və ya (None, səbəb).
    rest: əsas rəqəmlərdən başqa rəqəmli bəndlər, mənbədəki kimi."""
    lines = text.replace(" ", " ").split("\n")
    head = next((i for i, line in enumerate(lines) if re.search(r"polis tərəfindən\s*:\s*$", ox._low(line))), None)
    if head is None:
        return None, "icmal deyil"
    m = re.search(r"([^\W\d_].*?)\s+polis tərəfindən\s*:", " ".join(lines[head].split()), re.I)
    days = phrase_days(m.group(1), posted) if m else None
    if not days:
        return None, "icmalın tarixi oxunmadı"
    core, rest = {}, []
    for b in _bullets(lines[head + 1:]):
        for name, rx in _CORE:
            hit = rx.match(b)
            if hit and name not in core:
                core[name] = hit
                break
        else:
            if re.search(r"\d", b) and not b.startswith("#"):
                rest.append(b if b.endswith(".") else b + ".")
    if not all(k in core for k in ("crimes", "wanted", "suspects")):
        return None, "icmalda üç əsas rəqəm (açılan cinayətlər, axtarışda olanlar, şübhəlilər) yoxdur"
    out = {"days": days, "rest": rest, "split": None, "debt": None, "missing": None}
    for k in ("crimes", "wanted", "suspects"):
        out[k] = _int(core[k].group(1))
    sp = _SPLIT.match(" ".join((core["crimes"].group(2) or "").split()))
    if sp and int(sp.group(1)) + int(sp.group(2)) == out["crimes"]:
        out["split"] = (int(sp.group(1)), int(sp.group(2)))
    debt = core["wanted"].group(2)
    if debt and int(debt) <= out["wanted"]:
        out["debt"] = int(debt)
    if "missing" in core:
        out["missing"] = _int(core["missing"].group(1))
    return out, ""


def polis_item(post, p):
    phrase = days_loc(p["days"])
    split = f" ({num_poss(p['split'][0])} cari, {num_poss(p['split'][1])} əvvəlki dövrlərdən)" if p["split"] else ""
    debt = f" ({num_poss(p['debt'])} borclu şəxs)" if p["debt"] is not None else ""
    lead = (f"{POLIS_FROM}, {phrase} polis {_n(p['crimes'])} cinayətin açılmasını təmin edib{split}. "
            f"Axtarışda olan {_n(p['wanted'])} nəfər{debt} və cinayət törətməkdə şübhəli bilinən {_n(p['suspects'])} "
            f"nəfər saxlanılıb")
    lead += f", itkin kimi axtarılan {_n(p['missing'])} nəfər tapılıb." if p["missing"] is not None else "."
    item = _item("polis-icmal", f"polis-icmal-{p['days'][-1].isoformat()}",
                 f"{_cap(phrase)} polis {_n(p['crimes'])} cinayətin açılmasını təmin edib", lead, p["rest"],
                 POLIS_CREDIT, post["url"], "icmal", "12:00", lst=True)
    if _leader(post["text"]):
        item.update(worth=False, why="yazıda rəhbərliyin adı keçir: avtomatik dərc olunmur")
    return item


def polis_find(posts, day):
    """Bu gün (Bakı vaxtı) dərc olunan icmal: (yazı, rəqəmlər, səbəb). Bir neçə varsa ən yenisi."""
    why = "bu gün polisin gündəlik icmalı hələ dərc olunmayıb"
    for post in sorted(posts, key=lambda x: -x["id"]):
        if post["when"].date() != day:
            continue
        p, bad = polis_parse(post["text"], post["when"].date())
        if not p:
            if bad != "icmal deyil":
                why = f"{bad} ({post['url']})"
            continue
        if not day - POLIS_LAG * DAY <= p["days"][-1] <= day:
            why = f"icmalın tarixi köhnədir: {days_loc(p['days'])} ({post['url']})"
            continue
        return post, p, ""
    return None, None, why


def _state_holiday(d):
    return d in tq.IL_BAYRAM or any(off and (m, dd) == (d.month, d.day) for m, dd, _, off, _ in tq.DOVLET)


def polis_day(d):
    """İcmal gözlənilən gün: iş günü və bayram olmayan şənbə (kanal bazar və bayram günləri icmal vermir)."""
    if d.weekday() == 6:
        return False
    if d.weekday() == 5:
        return not _state_holiday(d)
    return tq.qeyri_is_gunu(d) is not True


def polis_items(now, net, done):
    day = now.date()
    if not polis_day(day) or not _open(now, POLIS_AT) or f"polis-icmal-{(day - DAY).isoformat()}" in done:
        return []
    posts = tg_posts(_text(net(TG_URL)))
    if not posts:
        raise ValueError("kanalın səhifəsində yazı tapılmadı")
    post, p, why = polis_find(posts, day)
    if not post:
        return [_item("polis-icmal", f"polis-icmal-gozlenilir-{day.isoformat()}", f"Polisin gündəlik icmalı: {ox.day_text(day)}",
                      f"{POLIS_FROM}: icmal yoxdur.", [], POLIS_CREDIT, TG_URL, "icmal", "12:00", worth=False, why=why)]
    return [polis_item(post, p)]


# --- İstehsal ---------------------------------------------------------------------------------------------------------------

PARTS = (
    ("dim", dim_items, DIM_CREDIT, DIM_URL, "təqvim", "09:00"),
    ("seyyar-asan", asan_items, ASAN_CREDIT, ASAN_URL, "təqvim", "10:00"),
    ("asan-muraciet", mur_items, MUR_CREDIT, MUR_PAGE, "icmal", "11:00"),
    ("polis-icmal", polis_items, POLIS_CREDIT, TG_URL, "icmal", "12:00"),
)


def _failed(kind, credit, link, topic, slot, day, err):
    host = urllib.parse.urlsplit(link).hostname or link
    return _item(kind, f"{kind}-xeta-{day.isoformat()}", f"{credit}: məlumat alınmadı", f"{host} oxunmadı.", [], credit, link,
                 topic, slot, worth=False, why=f"{host} alınmadı və ya oxunmadı: {type(err).__name__}")


def _run(now, net, done):
    out = []
    for kind, build, credit, link, topic, slot in PARTS:
        try:
            out += build(now, net, done)
        except Exception as e:  # bir mənbənin xətası digərlərini saxlamır
            out.append(_failed(kind, credit, link, topic, slot, now.date(), e))
    return out


def items(root, now, fetch=None, done=None):
    """now anında (Bakı vaxtı) pəncərəsi açıq olan mənbələrin xəbərləri. worth=False olanların səbəbi why-dadır.
    done: bu gün dərc olunmuş (və ya qurulmuş) açarlar; onların mənbəyinə sorğu getmir. root işlənmir: məlumat mənbələrdəndir.
    Heç vaxt xəta qaldırmır."""
    try:
        now = _now(now)
        done = set(done or ())
        net = _Net(fetch if fetch is not None else _default_fetch())
        return [_guard(i) for i in _run(now, net, done) if i.get("key") not in done]
    except Exception:
        return []


# --- Sınaq ------------------------------------------------------------------------------------------------------------------

def _verdict(item):
    return "✅ Dərc olunardı" if item.get("worth") else f"⏭ Dərc olunmazdı: {item.get('why') or 'səbəb yazılmayıb'}"


def _case(label, item):
    item = _guard(item)
    md = [f"_{label}; açar `{item['key']}`, saat {item['slot']}_", ""] + ox.render(item)
    if item.get("skipped"):
        md += ["> Rəhbərliyin adı keçdiyi üçün yazılmayan tədbirlər: " + " | ".join(item["skipped"]), ""]
    return md + [_verdict(item), ""]


def _label(d, today):
    rel = {0: "bu gün", -1: "dünən", 1: "sabah"}.get((d - today).days, "")
    return f"{ox.day_text(d)} {d.year}, {_wd(d)}" + (f" ({rel})" if rel else "")


def _dim_sinaq(now, net):
    today = now.date()
    monday = today - today.weekday() * DAY
    md = ["## 1. DİM təqvimi (bazar ertəsi icmal, digər günlər qeydiyyatın son günü, 09:00)", ""]
    try:
        events, complete = dim_get(net, monday + 13 * DAY)
    except Exception as e:
        return md + [f"> dim.gov.az alınmadı: {type(e).__name__}", ""]
    latest = max(e["start"] for e in events)
    md += [f"_Təqvimdən {len(events)} tədbir oxundu (son başlanğıc: {ox.day_text(latest)} {latest.year})._", ""]

    def full(need):
        return complete or latest > need

    for mon, tag in ((monday, "bu həftənin icmalı"), (monday + 7 * DAY, "gələn həftənin icmalı")):
        md += _case(f"{_label(mon, today)}: {tag}, bugünkü təqvimlə", dim_week_item(events, mon, full(mon + 6 * DAY)))
    ends = sorted({e["end"] for e in events if e["kind"] == "Qeydiyyat" and e["end"] and e["end"].weekday()})
    past = [d for d in ends if d <= today]
    nxt = [d for d in ends if d > today]
    if past:
        md += _case(f"{_label(past[-1], today)}: qeydiyyatın son günü, ən son real hal", dim_day_item(events, past[-1]))
    if nxt:
        md += _case(f"{_label(nxt[0], today)}: qeydiyyatın son günü, növbəti hal", dim_day_item(events, nxt[0], full(nxt[0])))
    if not past and not nxt:
        md += ["> Təqvimdə qeydiyyatın son günü yoxdur.", ""]
    return md


def _asan_sinaq(now, net):
    today = now.date()
    md = ["## 2. Səyyar ASAN xidmət (məntəqədə işə başlamazdan bir gün əvvəl, 10:00)", ""]
    try:
        stops = asan_stops(_text(net(ASAN_URL)))
    except Exception as e:
        return md + [f"> asan.gov.az alınmadı: {type(e).__name__}", ""]
    if not stops:
        return md + ["> Cədvəldə məntəqə tapılmadı.", ""]
    md += [f"_Cədvəldə {len(stops)} məntəqə, {len({s['bus'] for s in stops})} avtobus._", ""]
    starts = sorted({s["start"] for s in stops})
    past = [d for d in starts if d <= today + DAY]
    nxt = [d for d in starts if d > today + DAY]
    md += _case(f"{_label(today, today)}: sabah başlayanlar", asan_item(stops, today))
    if past and past[-1] != today + DAY:
        md += _case(f"{_label(past[-1] - DAY, today)}: ən son real hal, bugünkü cədvəllə", asan_item(stops, past[-1] - DAY))
    if nxt:
        md += _case(f"{_label(nxt[0] - DAY, today)}: növbəti hal", asan_item(stops, nxt[0] - DAY))
    return md


def _mur_sinaq(now, net):
    today = now.date()
    monday = today - today.weekday() * DAY
    md = ["## 3. «ASAN müraciət»: ötən həftənin problemləri (bazar ertəsi 11:00)", ""]
    work = _work_days(monday - 7 * DAY, monday - DAY)
    try:
        rows = mur_get(net, work[-1] if work else None)
    except Exception as e:
        return md + [f"> CSV alınmadı (Google Drive / portal): {type(e).__name__}: {e}"[:300], ""]
    newest = max(r[0] for r in rows)
    md += [f"_CSV-də {len(rows)} sətir, son gün: {ox.day_text(newest)} {newest.year}._", ""]
    md += _case(f"{_label(monday, today)}: ən son bazar ertəsi", mur_item(rows, monday))
    md += _case(f"{_label(monday + 7 * DAY, today)}: növbəti bazar ertəsi, bugünkü məlumatla", mur_item(rows, monday + 7 * DAY))
    return md


def _polis_sinaq(now, net, pages=3):
    today = now.date()
    md = ["## 4. Polisin gündəlik icmalı (bazar ertəsi–şənbə, 11:45–12:15 yoxlanır, 12:00)", ""]
    posts, url = [], TG_URL
    for n in range(pages):
        try:
            page = _text(net(url))
        except Exception as e:
            md += [f"> {url} alınmadı: {type(e).__name__}", ""]
            break
        posts += tg_posts(page)
        found = [x for x in posts if polis_parse(x["text"], x["when"].date())[0]]
        before = tg_before(page)
        if len(found) >= 2 or not before:
            break
        url = f"{TG_URL}?before={before}"
    if not posts:
        return md + ["> Kanalın yazıları oxunmadı.", ""]
    post, p, why = polis_find(posts, today)
    if post:
        md += _case(f"{_label(today, today)}: bu günün icmalı", polis_item(post, p))
    else:
        md += [f"**{_label(today, today)}:** ⏭ Dərc olunmazdı: {why}" +
               ("" if polis_day(today) else " (bu gün icmal gözlənilmir: bazar və ya bayram günü)"), ""]
    shown = 0
    for x in sorted(posts, key=lambda y: -y["id"]):
        p, _ = polis_parse(x["text"], x["when"].date())
        if not p or (post and x["id"] == post["id"]):
            continue
        item = polis_item(x, p)
        at = x["when"]
        start = at.replace(hour=POLIS_AT[0], minute=POLIS_AT[1], second=0, microsecond=0)
        if item["worth"] and at >= start + WINDOW:
            item = dict(item, worth=False, why=f"saat {at:%H:%M}-da dərc olunub: yoxlama pəncərəsindən sonradır")
        elif item["worth"] and not polis_day(at.date()):
            item = dict(item, worth=False, why="bazar və ya bayram günü dərc olunub: o gün sorğu getmir")
        md += _case(f"{_label(at.date(), today)}, saat {at:%H:%M}-da dərc olunub: son real hal", item)
        shown += 1
        if shown >= 2:
            break
    if not shown and not post:
        md += ["> Oxunan səhifələrdə icmal tapılmadı.", ""]
    return md


def sinaq(root, now=None, fetch=None):
    """Nümunələr (Markdown): bu an dərc olunacaqlar və hər mənbənin ən son real halları. Sayta heç nə yazmır.
    Sorğular: DİM 2–3, ASAN 1, Drive 1 (portal 1), t.me 1–3."""
    try:
        now = _now(now)
        net = _Net(fetch if fetch is not None else _default_fetch())
        md = [f"## Gündəlik həyat: öz xəbərlər ({now:%d.%m.%Y %H:%M}, Bakı vaxtı)", "",
              "Şablon xəbərlər, süni intellektsiz: hər rəqəm, ad, tarix və yer mənbənin özündəndir. Sayta heç nə yazılmır.", ""]
        live = items(root, now, net)
        md += ["**Bu an dərc olunacaqlar:**", ""]
        md += [f"- `{i['key']}` ({i['slot']}): {i['title']} — " + ("✅" if i["worth"] else f"⏭ {i.get('why')}")
               for i in live] or ["- yoxdur (heç bir mənbənin pəncərəsi açıq deyil)"]
        md += [""]
        for part in (_dim_sinaq, _asan_sinaq, _mur_sinaq, _polis_sinaq):
            try:
                md += part(now, net)
            except Exception as e:
                md += [f"> {part.__name__} xətası: {type(e).__name__}: {e}"[:300], ""]
        md += ["## Mənbələrə çıxış (bu sınaqda)", ""]
        md += [f"- {url} — {result}" for url, result in net.log] or ["- sorğu getməyib"]
        return md + [""]
    except Exception as e:
        return [f"> Sınaq xətası: {type(e).__name__}: {e}"[:300], ""]


def _arg(argv, name):
    return argv[argv.index(name) + 1] if name in argv and argv.index(name) + 1 < len(argv) else None


def main(argv):
    if "--sinaq" not in argv:
        print(__doc__)
        return 0
    root = pathlib.Path(_arg(argv, "--root") or pathlib.Path(__file__).resolve().parent)
    when = _arg(argv, "--now")
    now = datetime.datetime.fromisoformat(when) if when else None
    sys.stdout.write("\n".join(sinaq(root, now)) + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
