"""8ulduz-un öz xəbərləri, mərhələ 3: rəsmi məlumat — elanlar və reyestrlər (sahib, 2026-11-12: «5 qat genişləndir
çeşidliliyi»). Dərc hissəsi (oz_derc.py) çağırır və açar yanılıdır: buradan qayıdan dəyərli xəbər sayta düşür.

Şablon xəbərlər, süni intellektsiz. Qırmızı xətt 4 («Məlumat dəqiq olmalıdır»): hər rəqəm, ad və tarix həmin gün oxunan
rəsmi mənbədəndir, mənbə özünü təsdiqləməlidir (sıra nömrələri, say, tarix aralığı, başlıqla mətnin eyni rəqəmi). Şübhəli,
natamam və ya köhnə cavabdan xəbər yazılmır: worth=False, səbəbi why-dadır. Vaxt Bakı vaxtıdır.

1. «Nazirlər Kabinetinin sənədləri» (nk-sened, 09:30; nk.gov.az/az/senedler/hamisi): DÜNƏN saytda yerləşdirilən qərar və
   sərəncamlar, bir xəbərdə. Səhər yazılır ki, günün siyahısı tam olsun (sənədlər 18:30-dək yerləşdirilir). Siyahıdakı
   tarix yerləşdirmə vaxtıdır, ona görə «yerləşdirilib» yazılır, «qəbul edilib» yox. Adında Prezident keçən sənədin adı
   yazılmır (sayda qalır); hamısı belədirsə xəbər yoxdur. Sənədin adı mənbədəki kimidir, 300 hərfdən uzunu kəsilir.
2. «Tikinti icazələri» (tikinti-hefte, bazar ertəsi 10:00; tdr.e-tikinti.gov.az API): ötən həftə (bazar ertəsi–bazar)
   Tikintilərin Dövlət Reyestrinə daxil edilən icazələrin sayı, obyekt adı və ərazi üzrə. Say API-nin «count» xanası ilə
   oxunan sətirlərin sayı eyni olanda yazılır. Sifarişçi (fiziki şəxslərin adı) və küçə ünvanı yazılmır: yalnız şəhər,
   rayon, qəsəbə, kənd.
3. «Minatəmizləmənin aylıq statistikası» (anama-ay, ayın 1–20-si 11:00; api.anama.gov.az): ANAMA-nın aylıq bloku. Yalnız blok
   son 2 gündə yenilənibsə və ayın adı yenilənmə tarixindən əvvəlki aydırsa yazılır. Həftəlik xanalar (1, 1, 0, 1) yer
   tutucudur, illik blok keçən ilindir: işlənmir.
4. «Dissertasiya müdafiələri» (aak-mudafie, 16:00; aak.gov.az/elanView): SABAH keçiriləcək müdafiələr, elm sahələri üzrə
   say və siyahı. Cədvəlin sütun adları və sıra nömrələri (1..N) yoxlanır; dəyişibsə xəbər yoxdur.
5. «Hərrac elanları» (herrac-elan) və «Hərracın nəticəsi» (herrac-netice), 17:30, emlak.gov.az/az-ın bir sorğusu:
   - «Hərraclar» blokundakı yeni elanlar (tarix və saat başlıqdandır, hərrac gələcəkdə olmalıdır). Blokda yerləşdirmə
     tarixi yoxdur, ona görə son görülən elanın nömrəsi done-dakı gündəlik nişan açarında saxlanır
     (emlak-son-<gün>-<nömrə>). Nişan yoxdursa (ilk çağırış, 8 gündən uzun fasilə) heç nə dərc olunmur: yalnız nişan qoyulur.
   - «Növbəti hərracda N nəqliyyat vasitəsi satılıb» xəbəri (son 3 gün): xəbərin öz səhifəsi oxunur (1 sorğu), saydakı
     rəqəm başlıqla mətndə eyni olmalıdır; hərracın tarixi mətndəndir.

Buraxılanlar (2026-11-12): «Azərişıq»ın planlı məhdudiyyətləri (azerishiq.az GitHub-dan açılmır: TLS bağlantısı kəsilir, 10 və
12 noyabr yoxlamaları), İpoteka Fondunun sayğacı (rəqəmin tarixi yoxdur, bağlantı qırılır), un qiymətləri (yalnız PDF).

Sorğular yalnız fetch ilə (15 saniyə), hər mənbəyə öz 30 dəqiqəlik pəncərəsində, pəncərədə bir tur. Gündə: Nazirlər
Kabineti 1, AAK 1, Əmlak Xidməti 1–2, ANAMA 0–1 (ayın 1–20-si), bazar ertəsi tikinti reyestri 2–7. Adi gün 3–5, bazar ertəsi
5–12 sorğu; bağlantı qırılanda ünvan ən çox 3 dəfə yoxlanır (oz_gundelik._Net). Hər qayıdan açar (worth=False olan da) done-a
yazılmalıdır: açarı done-da olan mənbəyə sorğu getmir. Müvəqqəti hal (şəbəkə xətası) başqa açarla qayıdır, növbəti dövrədə
yenə yoxlanır.
Sınaq: python oz_resmi.py --sinaq --root DIR [--now 2026-11-12T16:00+04:00]
"""
import datetime
import html
import json
import pathlib
import re
import sys

import oz_gundelik as og
import oz_xeber as ox

BAKU = ox.BAKU
DAY = datetime.timedelta(days=1)
TITLE_MAX = 110

NK_URL = "https://nk.gov.az/az/senedler/hamisi"
NK_SITE = "https://nk.gov.az"
NK_CREDIT = "Nazirlər Kabineti"
NK_AT = (9, 30)
NK_MIN = 10       # siyahıda ən azı bu qədər sənəd olmalıdır (2026-11-12: 38)
NK_TITLE = 300    # sənədin adı bundan uzundursa kəsilir
NK_KINDS = {"qerarlar": ("qərar", "Qərarlar"), "serencamlar": ("sərəncam", "Sərəncamlar")}

TIK_API = ("https://tdr.e-tikinti.gov.az/api/search?category=permission&current={page}&pageSize=25"
           "&registerDateBegin={a}&registerDateEnd={b}")
TIK_PAGE = "https://tdr.e-tikinti.gov.az/"
TIK_CREDIT = "Tikintilərin Dövlət Reyestri"
TIK_FROM = "Tikintilərin Dövlət Reyestrinin məlumatına görə"
TIK_AT = (10, 0)
TIK_PAGES = 6     # bir həftə üçün ən çox bu qədər səhifə (səhifədə 25 icazə)
TIK_STATUS = "Tikintiyə İcazə"
TIK_LINES = 10

ANAMA_URL = "https://api.anama.gov.az/api/client/generalStatistics"
ANAMA_PAGE = "https://anama.gov.az/"
ANAMA_CREDIT = "Minatəmizləmə Agentliyi (ANAMA)"
ANAMA_AT = (11, 0)
ANAMA_DAYS = 20   # ayın bu günündən sonra sorğu getmir
ANAMA_FRESH = 2   # blok ən çoxu bu qədər gün əvvəl yenilənməlidir

AAK_URL = "https://aak.gov.az/elanView"
AAK_CREDIT = "Ali Attestasiya Komissiyası"
AAK_FROM = "Ali Attestasiya Komissiyasının elanlarına görə"
AAK_AT = (16, 0)
AAK_HEAD = ("№", "Müdafiə tarixi", "Soyad, ad, ata adı", "Dissertasiyanın adı", "Avtoreferat", "Elm sahəsi",
            "İxtisasın şifri və adı", "İddia olunan elmi dərəcə", "Müdafiənin keçiriləcəyi yer")
AAK_LINES = 12

EMLAK_URL = "https://emlak.gov.az/az"
EMLAK_SITE = "https://emlak.gov.az"
EMLAK_LIST = "https://emlak.gov.az/az/cat/3"
EMLAK_CREDIT = "Əmlak Məsələləri Dövlət Xidməti"
EMLAK_FROM = "Əmlak Məsələləri Dövlət Xidmətinin məlumatına görə"
EMLAK_AT = (17, 30)
EMLAK_MIN = 3     # «Hərraclar» blokunda ən azı bu qədər elan olmalıdır (2026-11-12: 8)
NETICE_FRESH = 3  # nəticə xəbəri ən çoxu bu qədər gün əvvəl dərc olunmalıdır
NETICE_LAG = 7    # hərracla xəbər arasında ən çox bu qədər gün


# --- Köməkçilər -------------------------------------------------------------------------------------------------------------

_MONTH_NO = {name: i for i, name in enumerate(ox.MONTHS, 1)}
_LEADER_RX = re.compile(r"prezident|birinci xanım|vitse-prezident|dövlət başçısı|ölkə başçısı|ali baş komandan|"
                        r"(?:ilham|mehriban|heydər)\s+əliyev")


def _month(word):
    """Ayın adı («Noyabr», «dekabr») -> 1..12 və ya None."""
    return _MONTH_NO.get(ox._low(word or "").strip())


def _leader(text):
    """Rəhbərlik süzgəci, ox.needs_owner-dən sərt: «Prezidentinin ... Fərmanı» kimi yazılışı da tutur."""
    if _LEADER_RX.search(ox._low(text or "")):
        return True
    try:
        return bool(ox.needs_owner(text))
    except Exception:
        return False


def _lower1(text):
    """Yalnız ilk hərf kiçilir: «İqtisad elmləri» -> «iqtisad elmləri»."""
    if not text:
        return text
    return {"İ": "i", "I": "ı"}.get(text[0], text[0].lower()) + text[1:]


def _cut(text, limit):
    """limit-dən uzun mətn son tam sözdə kəsilir, sonuna «…»."""
    if len(text) <= limit:
        return text
    return text[:limit].rsplit(" ", 1)[0].rstrip(" ,;:") + "…"


def _pick(forms, seed):
    """Başlığın forması: seed-ə görə növbə ilə (ardıcıl xəbərlər eyni görünməsin); 110 hərfə sığmayan forma atlanır."""
    k = seed % len(forms)
    order = list(forms[k:]) + list(forms[:k])
    for title in order:
        if len(title) <= TITLE_MAX:
            return title
    return order[0]


def _tally(values):
    """Dəyərlər (mətn və ya mətnlər dəsti) -> [(dəyər, say)], çoxdan aza, sonra əlifba ilə."""
    count = {}
    for v in values:
        count[v] = count.get(v, 0) + 1
    return sorted(count.items(), key=lambda x: (-x[1], og._az_key(x[0] if isinstance(x[0], str) else " ".join(x[0])), x[0]))


def _skip(kind, key, title, tail, why):
    return og._item(kind, key, title, f"Xəbər yazılmadı: {why}.", [], *tail, worth=False, why=why)


def _guard(item):
    """Rəhbərliyin adı keçən xəbər dərc olunmur (sahibin qaydası); başlıq 110 hərfdən uzun olmamalıdır."""
    if not item.get("worth"):
        return item
    if _leader("\n".join([item["title"], item["lead"], *item["body"]])):
        return dict(item, worth=False, why="rəhbərliyin adı keçir: avtomatik dərc olunmur")
    if len(item["title"]) > TITLE_MAX:
        return dict(item, worth=False, why=f"başlıq {TITLE_MAX} hərfdən uzundur")
    return item


# --- 1. Nazirlər Kabinetinin sənədləri ----------------------------------------------------------------------------------------

_NK_SPLIT = re.compile(r'<div\s+class="[^"]*\bdoc-item\b[^"]*"')
_NK_LINK = re.compile(r'<a\s+href="(/az/senedler/([a-z]+)/[^"\s]*?-(\d+))"')
_NK_HEAD = re.compile(r'<p\s+class="doc-header[^"]*"\s*>(.*?)</p>', re.S)
_NK_SPAN = re.compile(r'<span\s+class="doc-(type|date|num)"\s*>(.*?)</span>', re.S)
_NK_DATE = re.compile(r"^(\d{1,2})\s+([^\W\d_]+)\s+(\d{4})\s*-\s*(\d{1,2}):(\d\d)$")
_NK_NUM = re.compile(r"^№\s*(\d+)(s?)$")


def nk_docs(page):
    """Siyahı səhifəsi -> [{id, kind, path, title, when, num}], səhifədəki sıra ilə. Başqa növ (məktublar) buraxılır.
    Qərar və ya sərəncamın bir xanası oxunmasa, növü nömrəsinə uyğun gəlməsə (sərəncamın nömrəsi «s» ilə bitir) ValueError:
    yarımçıq siyahıdan xəbər yazılmır."""
    out = []
    for part in _NK_SPLIT.split(page)[1:]:
        m = _NK_LINK.search(part)
        if not m:
            raise ValueError("sənədin keçidi oxunmadı")
        if m.group(2) not in NK_KINDS:
            continue
        word, label = NK_KINDS[m.group(2)]
        head = _NK_HEAD.search(part)
        spans = {k: ox._clean(v) for k, v in _NK_SPAN.findall(part)}
        title = ox._clean(head.group(1)) if head else ""
        d = _NK_DATE.match(spans.get("date", ""))
        n = _NK_NUM.match(spans.get("num", ""))
        month = _month(d.group(2)) if d else None
        if not (title and d and n and month and spans.get("type") == label and bool(n.group(2)) == (word == "sərəncam")):
            raise ValueError(f"{m.group(3)} nömrəli səhifədəki sənəd oxunmadı")
        when = datetime.datetime(int(d.group(3)), month, int(d.group(1)), int(d.group(4)), int(d.group(5)), tzinfo=BAKU)
        out.append({"id": int(m.group(3)), "kind": word, "path": m.group(1), "title": title, "when": when,
                    "num": n.group(1) + n.group(2)})
    return out


def _nk_count(docs):
    q = sum(1 for d in docs if d["kind"] == "qərar")
    s = len(docs) - q
    return og._join([f"{q} qərar" if q else "", f"{s} sərəncam" if s else ""]), q, s


def nk_item(docs, day):
    """day günü saytda yerləşdirilən qərar və sərəncamlar (istehsalda day dünəndir)."""
    key = f"nk-sened-{day.isoformat()}"
    tail = (NK_CREDIT, NK_URL, "rəsmi", "09:30")
    args = ("nk-sened", key, f"Nazirlər Kabinetinin sənədləri: {ox.day_text(day)}", tail)
    if len(docs) < NK_MIN or len({d["id"] for d in docs}) != len(docs):
        return _skip(*args, f"siyahı natamamdır: {len(docs)} sənəd oxundu")
    if min(d["when"].date() for d in docs) >= day:
        return _skip(*args, "siyahının sonu həmin günə çatmır: günün sənədləri natamam ola bilər")
    todays = sorted((d for d in docs if d["when"].date() == day), key=lambda d: (d["when"], d["id"]))
    if not todays:
        return _skip(*args, "həmin gün saytda qərar və ya sərəncam yerləşdirilməyib")
    shown = [d for d in todays if not _leader(d["title"])]
    if not shown:
        return _skip(*args, "sənədlərin hamısının adında rəhbərlik keçir: avtomatik dərc olunmur")
    when, n = og.date_loc(day), len(todays)
    count, q, s = _nk_count(todays)
    body = [f"{d['num']} nömrəli {d['kind']}: {_cut(d['title'], NK_TITLE)}" for d in shown]
    if n == 1:
        d = todays[0]
        word = "qərarı" if d["kind"] == "qərar" else "sərəncamı"
        title = _pick([f"Nazirlər Kabinetinin {d['num']} nömrəli {word} dərc olunub",
                       f"Nazirlər Kabinetinin saytında {when} {d['num']} nömrəli {d['kind']} yerləşdirilib",
                       f"Hökumətin yeni sənədi: {d['num']} nömrəli {d['kind']} dərc olunub"], day.toordinal())
        lead = (f"Nazirlər Kabinetinin saytında {when} {d['num']} nömrəli {d['kind']} yerləşdirilib. "
                f"Sənədin adı aşağıdadır.")
        return og._item("nk-sened", key, title, lead, body, NK_CREDIT, NK_SITE + d["path"], "rəsmi", "09:30", lst=True)
    title = _pick([f"Nazirlər Kabinetinin saytında {when} {count} yerləşdirilib",
                   f"Nazirlər Kabineti {when} {count} dərc edib",
                   f"Hökumətin yeni sənədləri: {when} {count} dərc olunub"], day.toordinal())
    lead = (f"Nazirlər Kabinetinin saytında {when} {n} sənəd yerləşdirilib: {count}." if q and s
            else f"Nazirlər Kabinetinin saytında {when} {count} yerləşdirilib.")
    lead += (" Sənədlərin adları aşağıdadır." if len(shown) == n
             else f" Aşağıda onlardan {len(shown)} sənədin adı verilir.")
    return og._item("nk-sened", key, title, lead, body, *tail, lst=True)


def nk_items(now, net, done):
    day = now.date() - DAY
    if not og._open(now, NK_AT) or f"nk-sened-{day.isoformat()}" in done:
        return []
    return [nk_item(nk_docs(og._text(net(NK_URL))), day)]


# --- 2. Tikinti icazələri (həftəlik) ------------------------------------------------------------------------------------------

_TIK_AREA = re.compile(r"(?:şəhəri|şəhərləri|rayonu|rayonları|qəsəbəsi|kəndi)$")
_TIK_POST = re.compile(r"^AZ\s?\d{4}$")


def tik_url(page, first, last):
    return TIK_API.format(page=page, a=first.isoformat(), b=last.isoformat())


def tik_page(raw):
    """API cavabı -> (sətirlər, say). Sətir: {id, status, name, address, date}. Quruluş gözlənilən kimi deyilsə ValueError."""
    doc = json.loads(og._text(raw))
    if not isinstance(doc, dict) or not isinstance(doc.get("data"), list):
        raise ValueError("cavabın quruluşu gözlənilən kimi deyil")
    count = int(str(doc.get("count")).strip())
    rows = []
    for r in doc["data"]:
        if not isinstance(r, dict) or type(r.get("id")) is not int:
            raise ValueError("sətir oxunmadı")
        name = " ".join(str(r.get("name") or "").split())
        if not name:
            raise ValueError("obyektin adı boşdur")
        rows.append({"id": r["id"], "status": " ".join(str(r.get("statusName") or "").split()), "name": name,
                     "address": " ".join(str(r.get("address") or "").split()),
                     "date": datetime.date.fromisoformat(str(r.get("reyestrDate"))[:10])})
    return rows, count


def tik_get(net, first, last):
    """Həftənin icazələri: (sətirlər, API-nin sayı). Səhifələr say dolanadək oxunur (ən çox TIK_PAGES)."""
    rows, seen, count = [], set(), None
    for page in range(TIK_PAGES):
        got, n = tik_page(net(tik_url(page, first, last)))
        if count is None:
            count = n
        elif n != count:
            raise ValueError("say səhifələr arasında dəyişdi")
        for r in got:
            if r["id"] not in seen:
                seen.add(r["id"])
                rows.append(r)
        if len(rows) >= count or not got:
            break
    return rows, count


def tik_area(address):
    """Ünvanın ərazi hissəsi: əvvəldəki şəhər, rayon, qəsəbə, kənd adları. Küçə və ev yazılmır (fiziki şəxsin ünvanı ola bilər).
    «AZ 6619, Yevlax şəhəri, Yuxarı Salamabad kəndi, Alı Mustafayev küçəsi, giriş 47» -> «Yevlax şəhəri, Yuxarı Salamabad kəndi»."""
    out = []
    for part in address.split(","):
        part = " ".join(part.split())
        if not out and _TIK_POST.match(part):
            continue
        if not _TIK_AREA.search(part) or "(" in part:
            break
        out.append(part)
    return ", ".join(out)


def tik_item(rows, count, first, last, prev=None):
    """Bazar ertəsinin xəbəri: first–last həftəsində reyestrə daxil edilən tikinti icazələri. prev: bir həftə əvvəlin sayı."""
    key = f"tikinti-hefte-{first.isoformat()}"
    tail = (TIK_CREDIT, TIK_PAGE, "gündəlik", "10:00")
    week = og._span(first, last)
    args = ("tikinti-hefte", key, f"Tikinti icazələri: {week}", tail)
    if count != len(rows):
        return _skip(*args, f"say özünü təsdiqləmir: reyestr {count} deyir, {len(rows)} icazə oxundu")
    if not count:
        return _skip(*args, "ötən həftə reyestrə tikinti icazəsi daxil edilməyib")
    if any(r["status"] != TIK_STATUS or not first <= r["date"] <= last for r in rows):
        return _skip(*args, "sətirlərin növü və ya tarixi sorğuya uyğun deyil")
    n = og._n(count)
    title = _pick([f"Ötən həftə Tikintilərin Dövlət Reyestrinə {n} tikinti icazəsi daxil edilib",
                   f"{week} tarixlərində {n} tikinti icazəsi reyestrə daxil edilib",
                   f"Tikinti icazələri: reyestrə bir həftədə {n} icazə daxil edilib"], first.toordinal() // 7)
    lead = f"{TIK_FROM}, {week} tarixlərində reyestrə {n} tikinti icazəsi daxil edilib."
    if prev is not None:
        lead += f" Bir həftə əvvəl ({og._span(first - 7 * DAY, last - 7 * DAY)}) bu say {og._n(prev)} olub."
    lead += " İcazələrin obyekt adı və ərazi üzrə bölgüsü aşağıdadır."
    groups = _tally((r["name"], tik_area(r["address"])) for r in rows)
    body, used = [], 0
    for (name, area), k in groups:
        line = f"{name} ({area}) – {k} icazə" if area else f"{name} – {k} icazə"
        if len(body) < TIK_LINES and not _leader(line):
            body.append(line)
            used += k
    if used < count:
        body.append(f"Digər obyektlər – {og._n(count - used)} icazə" if body else f"Cəmi – {n} icazə")
    return og._item("tikinti-hefte", key, title, lead, body, *tail, lst=True)


def tik_items(now, net, done):
    day = now.date()
    first = day - 7 * DAY
    if day.weekday() != 0 or not og._open(now, TIK_AT) or f"tikinti-hefte-{first.isoformat()}" in done:
        return []
    last = day - DAY
    rows, count = tik_get(net, first, last)
    try:
        prev = tik_page(net(tik_url(0, first - 7 * DAY, last - 7 * DAY)))[1]
    except Exception:
        prev = None
    return [tik_item(rows, count, first, last, prev)]


# --- 3. ANAMA-nın aylıq statistikası ------------------------------------------------------------------------------------------

_ANAMA_NUM = ("clean_area_monthly", "pedestrian_monthly", "tank_monthly", "unexplosive_monthly")


def anama_stat(raw):
    """API cavabı -> {month, area, pedestrian, tank, other, updated (Bakı vaxtı)}. Xanalar gözlənilən kimi deyilsə ValueError."""
    doc = json.loads(og._text(raw))
    if not isinstance(doc, dict):
        raise ValueError("cavabın quruluşu gözlənilən kimi deyil")
    month = _month(str(doc.get("monthly_interval") or ""))
    vals = [doc.get(k) for k in _ANAMA_NUM]
    if not month or any(type(v) is not int or v < 0 for v in vals) or not vals[0]:
        raise ValueError("aylıq blok oxunmadı")
    updated = datetime.datetime.fromisoformat(str(doc.get("updated_at")).replace("Z", "+00:00"))
    if updated.tzinfo is None:
        updated = updated.replace(tzinfo=datetime.timezone.utc)
    return {"month": month, "area": vals[0], "pedestrian": vals[1], "tank": vals[2], "other": vals[3],
            "updated": updated.astimezone(BAKU)}


def anama_item(stat, day):
    """Aylıq blok təzə yenilənibsə (son ANAMA_FRESH gün) və yenilənmə tarixindən əvvəlki ayındırsa xəbər; yoxsa worth=False."""
    tail = (ANAMA_CREDIT, ANAMA_PAGE, "rəsmi", "11:00")
    up = stat["updated"].date()
    month = stat["month"]
    year = up.year if month < up.month else up.year - 1
    name = ox.MONTHS[month - 1]
    args = ("anama-ay", f"anama-yoxla-{day.isoformat()}", f"ANAMA-nın aylıq statistikası: {name} {year}", tail)
    if (up.month - 2) % 12 + 1 != month:
        return _skip(*args, f"blokdakı ay ({name}) yenilənmə tarixindən ({ox.day_text(up)} {up.year}) əvvəlki ay deyil")
    age = (day - up).days
    if not 0 <= age <= ANAMA_FRESH:
        return _skip(*args, f"aylıq blok təzə deyil: {ox.day_text(up)} {up.year} tarixində yenilənib")
    area, mines = og._n(stat["area"]), og._n(stat["pedestrian"] + stat["tank"])
    loc = f"{name}{'də' if month == 4 else 'da'}"
    title = _pick([f"Minatəmizləmə Agentliyi: {loc} {area} hektar ərazi təmizlənib",
                   f"ANAMA {name} ayının statistikasını açıqlayıb: {area} hektar ərazi təmizlənib",
                   f"ANAMA-nın {name} statistikası: {area} hektar təmizlənmiş ərazi, {mines} mina"], month)
    lead = (f"Minatəmizləmə Agentliyinin (ANAMA) statistikasına görə, {ox.ordinal(year)} ilin {name} ayında {area} hektar "
            f"ərazi təmizlənib. Aylıq göstəricilərdə {og._n(stat['pedestrian'])} piyada əleyhinə mina, "
            f"{og._n(stat['tank'])} tank əleyhinə mina və {og._n(stat['other'])} digər partlayıcı sursat qeyd olunub.")
    return og._item("anama-ay", f"anama-ay-{year}-{month:02d}", title, lead, [], *tail)


def anama_items(now, net, done):
    day = now.date()
    period = day.replace(day=1) - DAY
    if (day.day > ANAMA_DAYS or not og._open(now, ANAMA_AT) or f"anama-ay-{period.year}-{period.month:02d}" in done
            or f"anama-yoxla-{day.isoformat()}" in done):
        return []
    return [anama_item(anama_stat(net(ANAMA_URL, headers={"lang": "az"})), day)]


# --- 4. Dissertasiya müdafiələri ------------------------------------------------------------------------------------------------

_AAK_TABLE = re.compile(r'<table\b[^>]*\bid="table_id"[^>]*>(.*?)</table>', re.S)
_AAK_CELL = re.compile(r"<td\b[^>]*>(.*?)(?=<td\b|</tr>|\Z)", re.S)
_AAK_DATE = re.compile(r"^\d\d\.\d\d\.\d{4}$")


def aak_rows(page):
    """Elanlar səhifəsi -> [{date, name, title, field, degree, place}]. Sütun adları AAK_HEAD-dən fərqlidirsə, sətirdə 9 xana
    yoxdursa, sıra nömrələri 1..N deyilsə və ya tarix oxunmursa ValueError (cədvəl dəyişib: xəbər yazılmır)."""
    m = _AAK_TABLE.search(re.sub(r"<!--.*?-->", "", page, flags=re.S))
    if not m:
        raise ValueError("müdafiələr cədvəli tapılmadı")
    head = re.search(r"<thead\b[^>]*>(.*?)</thead>", m.group(1), re.S)
    body = re.search(r"<tbody\b[^>]*>(.*?)</tbody>", m.group(1), re.S)
    if not head or not body:
        raise ValueError("cədvəlin quruluşu dəyişib")
    if tuple(ox._clean(h) for h in re.findall(r"<th\b[^>]*>(.*?)</th>", head.group(1), re.S)) != AAK_HEAD:
        raise ValueError("cədvəlin sütunları dəyişib")
    out = []
    for n, tr in enumerate(re.split(r"<tr\b[^>]*>", body.group(1))[1:], 1):
        cells = [ox._clean(c) for c in _AAK_CELL.findall(tr)]
        date = og._dmy(cells[1]) if len(cells) == len(AAK_HEAD) and _AAK_DATE.match(cells[1]) else None
        if not date or cells[0] != str(n) or not (cells[2] and cells[3] and cells[5] and cells[7]):
            raise ValueError(f"cədvəlin {n}-ci sətri oxunmadı")
        out.append({"date": date, "name": cells[2], "title": cells[3], "field": cells[5], "degree": cells[7],
                    "place": cells[8]})
    return out


def aak_item(rows, day, today):
    """day günü keçiriləcək müdafiələr (istehsalda day sabahdır). Müdafiə yoxdursa və ya cədvəl köhnədirsə worth=False."""
    key = f"aak-mudafie-{day.isoformat()}"
    tail = (AAK_CREDIT, AAK_URL, "təhsil", "16:00")
    args = ("aak-mudafie", key, f"Dissertasiya müdafiələri: {ox.day_text(day)}", tail)
    if not rows:
        return _skip(*args, "elanlar cədvəli boşdur")
    if max(r["date"] for r in rows) < today:
        return _skip(*args, "cədvəl köhnədir: bütün müdafiə tarixləri keçib")
    mine = [r for r in rows if r["date"] == day]
    if not mine:
        return _skip(*args, "həmin gün dissertasiya müdafiəsi yoxdur")
    n, when = len(mine), og.date_loc(day)
    fields = _tally(_lower1(r["field"]) for r in mine)
    degrees = _tally(_lower1(r["degree"]) for r in mine)
    if len(fields) == 1:
        f = fields[0][0]
        title = _pick([f"{og._cap(when)} {f} üzrə {n} dissertasiya müdafiə olunacaq",
                       f"{og._cap(f)} üzrə {n} dissertasiya {when} müdafiə olunacaq",
                       f"AAK: {when} {f} üzrə {n} dissertasiya müdafiəsi keçiriləcək"], day.toordinal())
        lead = f"{AAK_FROM}, {when} {f} üzrə {n} dissertasiya müdafiəsi keçiriləcək."
    else:
        parts = ", ".join(f"{f} üzrə {c}" for f, c in fields)
        title = _pick([f"{og._cap(when)} {n} dissertasiya müdafiə olunacaq: {parts}",
                       f"{n} dissertasiya {when} müdafiə olunacaq: {parts}",
                       f"AAK: {when} {len(fields)} elm sahəsi üzrə {n} dissertasiya müdafiəsi keçiriləcək"], day.toordinal())
        lead = f"{AAK_FROM}, {when} {n} dissertasiya müdafiəsi keçiriləcək: {parts}."
    if len(degrees) == 1:
        lead += f" İddia olunan elmi dərəcə: {degrees[0][0]}."
    else:
        lead += " İddia olunan elmi dərəcələr: " + ", ".join(f"{g} – {c}" for g, c in degrees) + "."
    body = []
    for r in mine[:AAK_LINES]:
        place = r["place"].rstrip(" .")
        body.append(f"{r['name']} — «{r['title']}» ({_lower1(r['field'])})" + (f". Müdafiə yeri: {place}" if place else ""))
    if n > AAK_LINES:
        body.append(f"Elanlarda həmin gün üçün daha {n - AAK_LINES} müdafiə var.")
    if any(_leader(line) for line in body):
        body = []  # mövzuda və ya yerin adında rəhbərlik keçir: yalnız saylar yazılır
    return og._item("aak-mudafie", key, title, lead, body, *tail, lst=True)


def aak_items(now, net, done):
    day = now.date() + DAY
    if not og._open(now, AAK_AT) or f"aak-mudafie-{day.isoformat()}" in done:
        return []
    return [aak_item(aak_rows(og._text(net(AAK_URL))), day, now.date())]


# --- 5. Əmlak Xidməti: hərrac elanları və hərracın nəticəsi -------------------------------------------------------------------

_EM_BLOCK = re.compile(r'<h3\s+class="section-title"\s*>\s*Hərraclar\s*</h3>(.*?)(?=<h3\s+class="section-title"|<footer\b|\Z)', re.S)
_EM_POST = re.compile(r'<p\s+class="text-color2"\s*>(.*?)</p>\s*<a\s+href="(/?az/news/view/(\d+)-[^"]*)"', re.S)
_EM_NEWS = re.compile(r'<div\s+class="event-day"\s*>\s*(\d{1,2})\s*</div>\s*<div\s+class="event-month"\s*>\s*(\d{1,2})\s*</div>'
                      r'.*?<a\s+href="(/?az/news/view/(\d+)-[^"]*)"\s*>(.*?)</a>', re.S)
_EM_WHEN = re.compile(r"^(\d{1,2})\s+([^\W\d_]+)\s+(\d{4})-c[iıuü]\s+il\s+tarixində\s+saat\s+(\d{1,2}):(\d\d)-d[aə]\s+(.+)$")
_EM_SEEN = re.compile(r"^emlak-son-\d{4}-\d\d-\d\d-(\d+)$")
_EM_ELAN = re.compile(r"^herrac-elan-(\d+)$")
_NETICE = re.compile(r"^Növbəti hərracda (\d+) nəqliyyat vasitəsi satılıb\.?$")
_NETICE_BODY = re.compile(r"([^\W\d_]+)\s+(\d{1,2})-[^\W\d_]+\s+keçirilən hərracda\s+(\d+)\s+nəqliyyat vasitəsi satılıb")
_NETICE_NEXT = re.compile(r"nəqliyyat vasitələri üzrə növbəti hərraclar\s+((?:\d{1,2}\s*,\s*)*\d{1,2}\s+və\s+\d{1,2})\s+"
                          r"([^\W\d_]+)\s+tarixlərində keçiriləcək")


def emlak_posts(page):
    """Ana səhifənin «Hərraclar» bloku -> [{id, href, title, when, rest}], səhifədəki sıra ilə. when: hərracın vaxtı (başlıqdan),
    oxunmasa None. Blok tapılmasa və ya EMLAK_MIN-dən az elan varsa ValueError."""
    m = _EM_BLOCK.search(page)
    out = []
    for inner, href, ident in _EM_POST.findall(m.group(1) if m else ""):
        title = ox._clean(inner)
        w = _EM_WHEN.match(title)
        when, rest = None, ""
        if w and _month(w.group(2)):
            try:
                when = datetime.datetime(int(w.group(3)), _month(w.group(2)), int(w.group(1)), int(w.group(4)),
                                         int(w.group(5)), tzinfo=BAKU)
                rest = w.group(6)
            except ValueError:
                when = None
        if title:
            out.append({"id": int(ident), "href": "/" + html.unescape(href).lstrip("/"), "title": title, "when": when,
                        "rest": rest})
    if len(out) < EMLAK_MIN or len({p["id"] for p in out}) != len(out):
        raise ValueError("«Hərraclar» bloku oxunmadı")
    return out


def emlak_news(page):
    """Ana səhifənin «Xəbərlər» bloku -> [{id, href, title, day, month}] (ilsiz tarix: gün və ay)."""
    return [{"id": int(ident), "href": "/" + html.unescape(href).lstrip("/"), "title": ox._clean(inner), "day": int(d),
             "month": int(mo)} for d, mo, href, ident, inner in _EM_NEWS.findall(page)]


def emlak_seen(done):
    """done-dakı açarlardan son görülən elan nömrəsi (gündəlik nişan və dərc olunmuş elan açarları); yoxdursa None."""
    ids = []
    for key in done:
        m = _EM_SEEN.match(key) or _EM_ELAN.match(key)
        if m:
            ids.append(int(m.group(1)))
    return max(ids) if ids else None


def elan_item(posts, seen, now):
    """Son görülən nömrədən (seen) sonrakı elanlar, bir xəbərdə. Yeni elan yoxdursa və ya yaddaş yoxdursa None."""
    if seen is None:
        return None
    new = [p for p in posts if p["id"] > seen]
    if not new:
        return None
    top = max(p["id"] for p in new)
    key = f"herrac-elan-{top}"
    tail = (EMLAK_CREDIT, EMLAK_LIST, "iqtisadiyyat", "17:30")
    good = sorted((p for p in new if p["when"] and p["when"] > now and not _leader(p["title"])),
                  key=lambda p: (p["when"], p["id"]))
    if not good:
        return _skip("herrac-elan", key, f"Hərrac elanları: {ox.day_text(now.date())}", tail,
                     "yeni elanların hərrac tarixi oxunmadı və ya keçib")
    n = len(good)
    days = og.days_loc(sorted({p["when"].date() for p in good}))
    body = [f"{ox.day_text(p['when'].date())}, saat {p['when']:%H:%M}: {p['rest']}" for p in good]
    if n == 1:
        p = good[0]
        title = _pick([f"Əmlak Xidməti {days} keçiriləcək hərracla bağlı elan dərc edib",
                       f"{og._cap(days)} keçiriləcək hərracla bağlı elan dərc olunub",
                       f"Hərrac elanı: Əmlak Xidməti {days} keçiriləcək hərracın məlumatını yerləşdirib"], top)
        lead = (f"Əmlak Məsələləri Dövlət Xidmətinin saytında {days} {ox.time_loc(p['when'])} keçiriləcək hərracla bağlı "
                f"elan yerləşdirilib.")
        return og._item("herrac-elan", key, title, lead, body, EMLAK_CREDIT, EMLAK_SITE + p["href"], "iqtisadiyyat", "17:30",
                        lst=True)
    title = _pick([f"Əmlak Xidməti {days} keçiriləcək hərraclarla bağlı {n} elan dərc edib",
                   f"{og._cap(days)} keçiriləcək hərraclarla bağlı {n} elan dərc olunub",
                   f"Hərrac elanları: Əmlak Xidməti {days} keçiriləcək hərraclar üzrə {n} elan yerləşdirib"], top)
    lead = f"Əmlak Məsələləri Dövlət Xidmətinin saytında {days} keçiriləcək hərraclarla bağlı {n} elan yerləşdirilib."
    return og._item("herrac-elan", key, title, lead, body, *tail, lst=True)


def _md_date(day, month, today):
    """İlsiz tarix (gün, ay) -> bu günə qədərki ən yaxın tarix; düzgün deyilsə None."""
    for year in (today.year, today.year - 1):
        try:
            d = datetime.date(year, month, day)
        except ValueError:
            return None
        if d <= today:
            return d
    return None


def netice_item(row, page, posted):
    """«Növbəti hərracda N nəqliyyat vasitəsi satılıb» xəbəri. Say başlıqla mətndə eyni olmalıdır, hərracın tarixi mətndəndir."""
    key = f"herrac-netice-{row['id']}"
    link = EMLAK_SITE + row["href"]
    tail = (EMLAK_CREDIT, link, "iqtisadiyyat", "17:30")
    args = ("herrac-netice", key, f"Hərracın nəticəsi: {ox.day_text(posted)}", tail)
    head = _NETICE.match(row["title"])
    box = re.search(r'<div\s+id="blogcontent"[^>]*>(.*?)</div>', page, re.S)
    text = ox._clean(box.group(1)) if box else ""
    m = _NETICE_BODY.search(text)
    month = og._MON_GEN.get(ox._low(m.group(1))) if m else None
    if not head or not m or not month:
        return _skip(*args, "xəbərin mətnində hərracın tarixi və sayı oxunmadı")
    n = int(head.group(1))
    if int(m.group(3)) != n:
        return _skip(*args, f"say özünü təsdiqləmir: başlıqda {n}, mətndə {m.group(3)}")
    held = _md_date(int(m.group(2)), month, posted)
    if not held or (posted - held).days > NETICE_LAG:
        return _skip(*args, "hərracın tarixi xəbərin tarixinə uyğun deyil")
    when = og.date_loc(held)
    title = _pick([f"Əmlak Xidmətinin {when} keçirdiyi hərracda {n} nəqliyyat vasitəsi satılıb",
                   f"{og._cap(when)} keçirilən hərracda {n} nəqliyyat vasitəsi satılıb",
                   f"Hərracda {n} nəqliyyat vasitəsi satılıb: Əmlak Xidməti {when} keçirilən hərracın nəticəsini açıqlayıb"],
                  row["id"])
    lead = f"{EMLAK_FROM}, {when} keçirilən hərracda {n} nəqliyyat vasitəsi satılıb."
    nxt = _NETICE_NEXT.search(ox._low(text))
    nxt_month = _month(nxt.group(2)) if nxt else None
    if nxt_month:
        try:
            year = posted.year + (1 if nxt_month < posted.month else 0)
            dates = [datetime.date(year, nxt_month, int(x)) for x in re.findall(r"\d+", nxt.group(1))]
        except ValueError:
            dates = []
        if dates and dates == sorted(set(dates)) and dates[0] > held:
            lead += f" Nəqliyyat vasitələri üzrə növbəti hərraclar {og.days_loc(dates)} keçiriləcək."
    return og._item("herrac-netice", key, title, lead, [], *tail)


def emlak_items(now, net, done):
    day = now.date()
    mark = f"emlak-son-{day.isoformat()}-"
    if not og._open(now, EMLAK_AT) or any(k.startswith(mark) for k in done):
        return []
    page = og._text(net(EMLAK_URL))
    posts = emlak_posts(page)
    top = max(p["id"] for p in posts)
    seen = emlak_seen(done)
    out = [_skip("herrac-elan", f"{mark}{top}", f"Hərrac elanları: {ox.day_text(day)}",
                 (EMLAK_CREDIT, EMLAK_LIST, "iqtisadiyyat", "17:30"),
                 "bu günün yoxlaması aparılıb: nişan açarı" if seen is not None
                 else "ilk oxunuş: yeni elanları ayırmaq üçün əvvəlki nişan yoxdur")]
    item = elan_item(posts, seen, now)
    if item:
        out.append(item)
    for row in emlak_news(page):
        posted = _md_date(row["day"], row["month"], day)
        key = f"herrac-netice-{row['id']}"
        if not _NETICE.match(row["title"]) or key in done or not posted or (day - posted).days > NETICE_FRESH:
            continue
        try:
            out.append(netice_item(row, og._text(net(EMLAK_SITE + row["href"])), posted))
        except Exception as e:  # xəbərin səhifəsi alınmadı: sabah bir də yoxlanır (təzəlik həddi daxilində)
            out.append(_skip("herrac-netice", f"{key}-xeta-{day.isoformat()}", f"Hərracın nəticəsi: {ox.day_text(posted)}",
                             (EMLAK_CREDIT, EMLAK_SITE + row["href"], "iqtisadiyyat", "17:30"),
                             f"xəbərin səhifəsi alınmadı: {type(e).__name__}"))
    return out


# --- İstehsal ---------------------------------------------------------------------------------------------------------------

PARTS = (
    ("nk-sened", nk_items, NK_CREDIT, NK_URL, "rəsmi", "09:30"),
    ("tikinti-hefte", tik_items, TIK_CREDIT, TIK_PAGE, "gündəlik", "10:00"),
    ("anama-ay", anama_items, ANAMA_CREDIT, ANAMA_PAGE, "rəsmi", "11:00"),
    ("aak-mudafie", aak_items, AAK_CREDIT, AAK_URL, "təhsil", "16:00"),
    ("herrac", emlak_items, EMLAK_CREDIT, EMLAK_URL, "iqtisadiyyat", "17:30"),
)


def _run(now, net, done):
    out = []
    for kind, build, credit, link, topic, slot in PARTS:
        try:
            out += build(now, net, done)
        except Exception as e:  # bir mənbənin xətası digərlərini saxlamır
            out.append(og._failed(kind, credit, link, topic, slot, now.date(), e))
    return out


def items(root, now, fetch=None, done=None):
    """now anında (Bakı vaxtı) pəncərəsi açıq olan mənbələrin xəbərləri. worth=False olanların səbəbi why-dadır.
    done: dərc olunmuş (və ya qurulmuş) açarlar; onların mənbəyinə sorğu getmir, Əmlak Xidmətinin son görülən elanı da
    oradan oxunur. root işlənmir: məlumat mənbələrdəndir. Heç vaxt xəta qaldırmır."""
    try:
        now = og._now(now)
        done = set(done or ())
        net = og._Net(fetch if fetch is not None else og._default_fetch())
        return [_guard(i) for i in _run(now, net, done) if i.get("key") not in done]
    except Exception:
        return []


# --- Sınaq ------------------------------------------------------------------------------------------------------------------

def _case(label, item):
    item = _guard(item)
    return [f"_{label}; açar `{item['key']}`, saat {item['slot']}_", ""] + ox.render(item) + [og._verdict(item), ""]


def _nk_sinaq(now, net):
    today = now.date()
    md = ["## 1. Nazirlər Kabinetinin sənədləri (dünənin sənədləri, 09:30)", ""]
    docs = nk_docs(og._text(net(NK_URL)))
    md += [f"_Siyahıda {len(docs)} qərar və sərəncam oxundu._", ""]
    days = sorted({d["when"].date() for d in docs if d["when"].date() < today}, reverse=True)
    for day in [today - DAY] + [d for d in days if d != today - DAY][:2]:
        md += _case(f"{og._label(day, today)}: həmin günün sənədləri, bugünkü siyahı ilə", nk_item(docs, day))
    return md


def _tik_sinaq(now, net):
    today = now.date()
    monday = today - today.weekday() * DAY
    first, last = monday - 7 * DAY, monday - DAY
    md = ["## 2. Tikinti icazələri (ötən həftə, bazar ertəsi 10:00)", ""]
    rows, count = tik_get(net, first, last)
    try:
        prev = tik_page(net(tik_url(0, first - 7 * DAY, last - 7 * DAY)))[1]
    except Exception:
        prev = None
    return md + _case(f"{og._label(monday, today)}: son bazar ertəsinin xəbəri, bugünkü reyestrlə",
                      tik_item(rows, count, first, last, prev))


def _anama_sinaq(now, net):
    today = now.date()
    md = ["## 3. ANAMA-nın aylıq statistikası (ayın 1–20-si, 11:00)", ""]
    stat = anama_stat(net(ANAMA_URL, headers={"lang": "az"}))
    up = stat["updated"]
    md += [f"_Aylıq blok {up:%d.%m.%Y %H:%M}-də (Bakı vaxtı) yenilənib._", ""]
    md += _case(f"{og._label(today, today)}: bugünkü cavabla", anama_item(stat, today))
    if (today - up.date()).days > ANAMA_FRESH:
        md += _case(f"{og._label(up.date() + DAY, today)}: son real hal (yenilənmənin səhəri)", anama_item(stat, up.date() + DAY))
    return md


def _aak_sinaq(now, net):
    today = now.date()
    md = ["## 4. Dissertasiya müdafiələri (sabahın müdafiələri, 16:00)", ""]
    rows = aak_rows(og._text(net(AAK_URL)))
    md += [f"_Cədvəldə {len(rows)} müdafiə elanı oxundu._", ""]
    later = sorted({r["date"] for r in rows if r["date"] > today + DAY})
    for day in [today + DAY] + later[:2]:
        md += _case(f"{og._label(day, today)}: həmin günün müdafiələri, bugünkü cədvəllə", aak_item(rows, day, today))
    return md


def _emlak_sinaq(now, net):
    today = now.date()
    md = ["## 5. Əmlak Xidməti: hərrac elanları və hərracın nəticəsi (17:30)", ""]
    page = og._text(net(EMLAK_URL))
    posts = emlak_posts(page)
    ids = sorted((p["id"] for p in posts), reverse=True)
    md += [f"_«Hərraclar» blokunda {len(posts)} elan, ən yenisi {ids[0]}._", ""]
    item = elan_item(posts, ids[min(2, len(ids) - 1)], now)
    if item:
        md += _case("Nümunə: blokdakı ən yeni 2 elan yeni olsaydı (istehsalda yalnız son görüləndən sonrakılar)", item)
    rows = [r for r in emlak_news(page) if _NETICE.match(r["title"])]
    if not rows:
        return md + ["> «Xəbərlər» blokunda hərrac nəticəsi yoxdur.", ""]
    row = max(rows, key=lambda r: r["id"])
    posted = _md_date(row["day"], row["month"], today)
    if not posted:
        return md + ["> Nəticə xəbərinin tarixi oxunmadı.", ""]
    item = netice_item(row, og._text(net(EMLAK_SITE + row["href"])), posted)
    if item["worth"] and (today - posted).days > NETICE_FRESH:
        item = dict(item, worth=False, why=f"xəbər {ox.day_text(posted)} tarixlidir: {NETICE_FRESH} gündən köhnədir")
    return md + _case(f"{og._label(posted, today)} dərc olunan nəticə xəbəri: son real hal", item)


def sinaq(root, now=None, fetch=None):
    """Nümunələr (Markdown): bu an dərc olunacaqlar və hər mənbənin ən son real halları. Sayta heç nə yazmır.
    Sorğular: Nazirlər Kabineti 1, tikinti reyestri 2–7, ANAMA 1, AAK 1, Əmlak Xidməti 1–2."""
    try:
        now = og._now(now)
        net = og._Net(fetch if fetch is not None else og._default_fetch())
        md = [f"## Rəsmi məlumat: elanlar və reyestrlər ({now:%d.%m.%Y %H:%M}, Bakı vaxtı)", "",
              "Şablon xəbərlər, süni intellektsiz: hər rəqəm, ad və tarix rəsmi mənbənin özündəndir. Bu sınaq sayta heç nə yazmır.", ""]
        live = items(root, now, net)
        md += ["**Bu an dərc olunacaqlar (done boşdur):**", ""]
        md += [f"- `{i['key']}` ({i['slot']}): {i['title']} — " + ("✅" if i["worth"] else f"⏭ {i.get('why')}")
               for i in live] or ["- yoxdur (heç bir mənbənin pəncərəsi açıq deyil)"]
        md += [""]
        for part in (_nk_sinaq, _tik_sinaq, _anama_sinaq, _aak_sinaq, _emlak_sinaq):
            try:
                md += part(now, net)
            except Exception as e:
                md += [f"> {part.__name__}: mənbə alınmadı və ya oxunmadı: {type(e).__name__}: {e}"[:300], ""]
        md += ["## Mənbələrə çıxış (bu sınaqda)", ""]
        md += [f"- {url} — {result}" for url, result in net.log] or ["- sorğu getməyib"]
        return md + [""]
    except Exception as e:
        return [f"> Sınaq xətası: {type(e).__name__}: {e}"[:300], ""]


def main(argv):
    if "--sinaq" not in argv:
        print(__doc__)
        return 0
    root = pathlib.Path(og._arg(argv, "--root") or pathlib.Path(__file__).resolve().parent)
    when = og._arg(argv, "--now")
    now = datetime.datetime.fromisoformat(when) if when else None
    sys.stdout.write("\n".join(sinaq(root, now)) + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
