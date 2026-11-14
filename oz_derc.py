"""8ulduz-un öz xəbərlərinin dərc hissəsi (sahib, 2026-11-12: «Dərc hissəsini hazırla», sonra «Sayta qoşmağa başla»).
Sayta QOŞULUB və açarı YANILIDIR (sahib, 2026-11-12: «Bəli, yandır»): çağırış, lentə qatılma və bayraq yerindədir.

On iki şablon modulu (oz_xeber.FAZA1 + FAZA2) və oz_xeber.items-in baza xəbərləri («Bu gün tarixdə», AMB məzənnələri,
neft, zəlzələ, Premyer Liqa oyununun hesabatı) xəbər qurur; bu fayl onları lent sətrinə və statik səhifəyə çevirir:
növbə, gündəlik və saatlıq hədlər, mövzu hədləri, vaciblik sırası və məzmun qapısı ilə.

Üç kilid (üçü də açılmayınca heç nə dərc olunmur). 2026-11-12-dən vəziyyət: üçü də AÇIQDIR.
1. Çağırış (AÇIQ): updater.slow_cycle-ın update_own_news addımı cycle(ROOT)-u çağırır, pipeline.sh bu faylı və modulları kod
   qovluğuna köçürür (CODE_FILES). Addım bayrağı import-dan ƏVVƏL yoxlayır: bayraqsız bu fayl heç yüklənmir.
2. Bayraq (AÇIQ): OZ_DERC=1 mühit dəyişəni; onu yalnız pipeline.sh qoyur (tests/test_oz_xeber.py::WiredSwitchedOnTest yoxlayır,
   yalnız sahibin sözü ilə dəyişir). Onsuz cycle() dərhal qayıdır: modul çağırılmır, sorğu getmir, fayl yazılmır; updater.py
   də sətir faylını oxumur.
3. Məzmun qapısı (qırmızı xətt 2; mənbə AÇIQ, qapı həmişə işləyir): «8ULDUZ» assets/content-policy.js-in azSources
   siyahısındadır (yalnız 8ulduz.az ünvanı ilə). Hər sətir yenə content_policy.violation-dan keçir, başqa sayta aparan və ya
   sahibin çıxardığı sətir rədd edilir. Üstəlik: ox.needs_owner (başlıq + giriş + mətn),
   updater.is_negative_about_leadership, mənbə keçidi üçün content_policy.safe_url.

Bir dövrə, cycle(root): vəziyyət faylı -> modullardan xəbərlər -> növbə -> seçim -> qapı -> səhifə, sətir faylı, vəziyyət.
- data/oz/derc.json: vəziyyət (start, done, queue, out, blocked, errors, closes; üstəlik reqs, shut, next).
- data/oz/xeberler.json: son 48 saatın öz sətirləri, təzədən köhnəyə. Lent birləşməsi (updater.read_own_rows) bunun main-ə
  çatmış nüsxəsini oxuyur (pipeline.sh own_rows_live): sətir lentə yalnız səhifəsi saytda olandan sonra düşür.
- xeber/<id>/index.html: xəbərin öz səhifəsi, 30 gün. Tam mətn yalnız buradadır: sətirdə 220 hərflik xülasə var
  (qırmızı xətt 1: news.json böyüməsin). Yalnız «out» siyahısındakı səhifələr silinir.

Modulların `done` qaydası iki cürdür (QAYDA cədvəli):
- «hamisi» (mərhələ 2, oz_xeber və oz_icmal): sorğu pəncərə ilə gedir, qayıdan HƏR açar done-a yazılır (worth=False, «-gozle»,
  «-cehd1», saatlıq «…-sorgu-…» də), yoxsa modul hər dövrədə yenə sorğu göndərər. Slotu hələ çatmamış dəyərli xəbər
  dərhal növbəyə düşür, vaxtı (due) slotudur.
- «novbe» (mərhələ 1): modul günün siyahısını slot saatı ilə qaytarır, worth=False olan xəbər sonra eyni açarla dəyərli
  ola bilər (bitməmiş tur). Yalnız NÖVBƏYƏ düşən açar done-a yazılır. Slotu hələ çatmamış xəbərə toxunulmur.
Üç modul tapşırıqdakı ümumi qaydadan fərqlənir, ona görə cədvəldə ayrıca sətirləri var:
- oz_icmal sorğu göndərir və «gündə bir dəfə, 08:00-da» çağırılmalıdır: 08:00-dan əvvəl çağırılmır, qaydası «hamisi»dir
  (bazar günü 12:00-ın xəbəri də 08:00-da qurulur və növbədə gözləyir).
- oz_bazar-ın `done` parametri yoxdur və 09:40-dan sonra hər çağırışda AMB-yə 2 sorğu göndərir: xəbəri növbəyə düşən
  gün bir də çağırılmır («bir»).
- oz_futbol_az slotu hadisənin hazır olduğu saat kimi yazır (tarixsiz): saat «gələcəkdə» görünürsə, dünənin hadisəsidir
  və dərhal növbəyə düşür («indi»).
Hər modulun gündəlik sorğu həddi var («sorgu»): modul onu keçəndə sorğu funksiyası xəta verir, modul xəbərsiz qayıdır.

Növbə: xəbər öz Bakı gününün sonunadək və ya 6 saat ərzində dərc oluna bilmirsə, «gecikdi» kimi düşür (heç vaxt gec
dərc olunmur: «bu gün…» mətni sabah səhv olar).
Seçim: gündəlik tavan başlanğıcdan (start) həftə-həftə artır: 15, 25, 35, sonra 40. İstənilən bir saatda ən çox 4,
bir dövrədə ən çox 2 xəbər. Eyni mövzu ardıcıl gəlmir (növbədə yalnız o mövzu varsa, 20 dəqiqədən sonra gəlir).
Mövzu hədləri MOVZU_HEDD-dədir (iş günü / həftə sonu); heç bir mövzu tavanın üçdə birindən çox yer tutmur (ən azı 3).
Növbədəki xəbər günün qalan yerindən çoxdursa, sıra vacibliyə görədir (ONCELIK: 3 hadisə və xidmət, 2 adi, 1 nazik şablon).

oz_bazar üçün nüsxələr: hər dövrədə data/markets.json oxunur; ABŞ seansının bağlanışından sonrakı 1 saatlıq fasilədə
götürülmüş son nüsxə və şənbə 10:00-dan sonrakı nüsxə (neft, qızıl, gümüş, bitkoin sətirləri) vəziyyətin «closes»
hissəsində 9 gün saxlanır və oz_bazar.items(history=...) kimi ötürülür.

Sayta qoşulma (mərhələ 2, 2026-11-12): nə edilib, nə qalıb.
1. EDİLİB. assets/content-policy.js: azSources-də «8ULDUZ»: ["8ulduz.az"] (3-cü kilid).
2. EDİLİB. updater.slow_cycle: update_own_news addımı `oz_derc.cycle(ROOT)` çağırır (1-ci kilid), yalnız bayraqla.
   Yavaş dövrə ən azı 30 dəqiqədən bir işləməlidir: mərhələ 2 modullarının sorğu pəncərəsi 30–45 dəqiqədir.
3. EDİLİB. updater.main: data/oz/xeberler.json-un main-ə çatmış nüsxəsi content_policy.enforce-dan ƏVVƏL xəbər siyahısına qatılır (yalnız bayraqla;
   fayl oxunur, sorğu yoxdur). Öz sətir yenidən təsnif edilmir, qruplaşmır, linki yoxlanmır; write_story_pages mənbəyi
   «8ULDUZ» olan sətri buraxır: onun xeber/<id>/ səhifəsini bu fayl yazıb, ümumi şablon üstündən yazmır.
4. EDİLİB (mərhələ 3, sahib 2026-11-12: «Bəli, yandır»): pipeline.sh-də `export OZ_DERC=1` (2-ci kilid) və onu qoruyan test.
5. EDİLİB (sahib 2026-11-13: «Bəli, əlavə et»): updater.write_sitemap və write_news_sitemap lentdəki öz xəbərlərin səhifələrini də
   yazır (updater._own_page_rows). Yalnız lentdə olan (səhifəsi saytda olan) sətirlər; lentdən çıxan səhifə xəritədən də çıxır.

Sınaq: python oz_derc.py --sinaq --root DIR [--now 2026-11-12T09:00+04:00]
"""
import contextlib
import datetime
import hashlib
import html
import importlib
import inspect
import json
import os
import pathlib
import re
import sys
import tempfile
import time

import content_policy
import oz_xeber as ox

BAKU = ox.BAKU
FLAG = "OZ_DERC"
STATE = ("data", "oz", "derc.json")
ROWS = ("data", "oz", "xeberler.json")
TELEGRAM = "https://t.me/sekkizulduz_az"

RAMP = ((7, 15), (14, 25), (21, 35))   # başlanğıcdan neçə günədək, gündəlik tavan
CEILING = 40
PER_HOUR = 4
PER_CYCLE = 2
HOUR = datetime.timedelta(hours=1)
SAME_TOPIC_GAP = datetime.timedelta(minutes=20)
LATE = datetime.timedelta(hours=6)
ROWS_KEEP = datetime.timedelta(hours=48)
PAGE_KEEP = datetime.timedelta(days=30)
DONE_KEEP = datetime.timedelta(days=8)
CLOSES_KEEP = datetime.timedelta(days=9)
OUT_FULL = datetime.timedelta(days=2)   # bundan köhnə «out» sətrində yalnız id, key, ts qalır (fayl kiçik qalsın)
BUDGET_S = 60                           # bir dövrənin vaxt büdcəsi: bitəndə qalan modullar növbəti dövrəyə keçir
SINAQ_SORGU = 20                        # sınağın quru sınaq hissəsinin ən çox sorğusu
SINAQ_BAZA = 14                         # baza xəbərlərinin pəncərə nümunələri üçün ən çox sorğu
SINAQ_S = 35                            # sınaqda keçmiş saatların addımlarına ayrılan vaxt

_clock = time.monotonic

# Mövzu hədləri, Bakı günü üçün: (iş günü, həftə sonu).
MOVZU_HEDD = {"idman": (10, 10), "iqtisadiyyat": (8, 5), "təbiət": (5, 5), "kosmos": (2, 2), "təqvim": (3, 3),
              "mədəniyyət": (3, 3), "icmal": (3, 5)}
BASQA_HEDD = (4, 3)

# Modul qaydaları. done: «hamisi» / «novbe»; gelecek (slotu hələ çatmamış dəyərli xəbər): «gozle» toxunulmur,
# «indi» dərhal növbəyə, «vaxtinda» növbəyə, vaxtı slotudur; sorgu: gündəlik sorğu həddi (modulun öz sənədindəki
# rəqəmdən bir az çox); basla: bundan əvvəl çağırılmır; bir: xəbəri növbəyə düşən gün bir də çağırılmır.
QAYDA = {
    "oz_futbol_az": {"done": "novbe", "gelecek": "indi", "sorgu": 6},
    "oz_futbol_dunya": {"done": "novbe", "gelecek": "gozle", "sorgu": 0},
    "oz_bazar": {"done": "novbe", "gelecek": "gozle", "sorgu": 4, "bir": True},
    "oz_teqvim": {"done": "novbe", "gelecek": "gozle", "sorgu": 0},
    "oz_sema": {"done": "novbe", "gelecek": "gozle", "sorgu": 0},
    "oz_icmal": {"done": "hamisi", "gelecek": "vaxtinda", "sorgu": 5, "basla": "08:00"},
    "oz_hava": {"done": "hamisi", "gelecek": "vaxtinda", "sorgu": 12},
    "oz_yer_kosmos": {"done": "hamisi", "gelecek": "vaxtinda", "sorgu": 40},
    "oz_maliyye": {"done": "hamisi", "gelecek": "vaxtinda", "sorgu": 20},
    "oz_medeniyyet": {"done": "hamisi", "gelecek": "vaxtinda", "sorgu": 15},
    "oz_idman2": {"done": "hamisi", "gelecek": "vaxtinda", "sorgu": 9},
    "oz_gundelik": {"done": "hamisi", "gelecek": "vaxtinda", "sorgu": 14},
    "oz_dunya": {"done": "hamisi", "gelecek": "vaxtinda", "sorgu": 0},
    "oz_tixac": {"done": "hamisi", "gelecek": "vaxtinda", "sorgu": 40},   # pəncərə ərzində dövrədə bir sorğu (4 dəq × 75 dəq × 2)
    "oz_xeber": {"done": "hamisi", "gelecek": "vaxtinda", "sorgu": 45},
}
QAYDA_ADI = {"done": "hamisi", "gelecek": "vaxtinda", "sorgu": 20}

# Vaciblik: modul -> (adi dəyər, {növ: dəyər}). 3 hadisə və xidmət (zəlzələ, təhlükəli hava, maqnit qasırğası, DİM-in
# son günləri, polisin icmalı, ASAN, oyun nəticələri), 2 adi, 1 nazik şablon (təqvim günləri, asteroid icmalı,
# Vikipediya siyahıları, yubileylər, icmallar).
ONCELIK = {
    "oz_futbol_az": (2, {"pfl-tur": 3, "liqa-tur": 3, "avro-netice": 3, "milli-netice": 3, "kubok-merhele": 3}),
    "oz_futbol_dunya": (2, {"liqa-tur": 3, "avrokubok": 3, "klub-oyunu": 3, "liqa-diger": 1, "liqa-liderler": 1}),
    "oz_bazar": (2, {}),
    "oz_teqvim": (1, {"is-gunleri": 2, "istirahet": 2}),
    "oz_sema": (1, {"tutulma": 2, "meteor": 2, "fesil": 2}),
    "oz_icmal": (1, {"beledci": 2}),
    "oz_hava": (2, {"hava-hedd": 3, "maqnit-qasirgasi": 3, "xezer-su": 1}),
    "oz_yer_kosmos": (2, {"zelzele-region": 3, "asteroid-hefte": 1, "buraxilis-hefte": 1}),
    "oz_maliyye": (2, {}),
    "oz_medeniyyet": (2, {"vikipediya-gun": 1, "vikipediya-ay": 1, "yubiley": 1}),
    "oz_idman2": (2, {"f1-yaris": 3, "f1-siralama": 3, "cudo": 3}),
    "oz_gundelik": (3, {"dim-hefte": 2, "asan-muraciet": 2}),
    "oz_dunya": (2, {}),
    "oz_tixac": (3, {}),   # xidmət: pik saat bülleteni
    "oz_xeber": (2, {"zelzele": 3, "futbol": 3, "tarix": 1}),   # amb və neft: 2
}

# Bölmə: mövzu -> saytın bölməsi (updater.SECTIONS), mövzu kobud olanda növə görə.
BOLME = {"idman": "idman", "iqtisadiyyat": "iqtisadiyyat", "mədəniyyət": "medeniyyet", "təbiət": "cemiyyet",
         "kosmos": "tehsil", "təqvim": "cemiyyet", "icmal": "gundem"}
BOLME_NOV = {"dim-gun": "tehsil", "dim-hefte": "tehsil", "seyyar-asan": "bolgeler", "asan-muraciet": "cemiyyet",
             "dunya-elm": "tehsil", "dunya-saglamliq": "heyat", "dunya-tebiet": "dunya", "dunya-texno": "tehsil", "dunya-maraqli": "dunya",   # oz_dunya; dunya-kosmos -> tehsil (mövzudan)
             "polis-icmal": "cemiyyet", "tixac-seher": "cemiyyet", "tixac-axsam": "cemiyyet", "zelzele-region": "dunya", "meteohessas": "heyat", "maqnit-qasirgasi": "heyat",
             "zelzele": "gundem"}   # ölkədəki zəlzələ günün hadisəsidir; amb, neft -> iqtisadiyyat, futbol -> idman, tarix -> cemiyyet (mövzudan)
BOLME_AD = {"gundem": "Gündəm", "cemiyyet": "Cəmiyyət", "iqtisadiyyat": "İqtisadiyyat", "idman": "İdman",
            "medeniyyet": "Mədəniyyət", "tehsil": "Təhsil və elm", "heyat": "Sağlamlıq və həyat", "bolgeler": "Bölgələr",
            "dunya": "Dünya"}


# --- Vaxt, yol, fayl -------------------------------------------------------------------------------------------

def _baku(now):
    if now is None:
        return datetime.datetime.now(BAKU)
    return now.astimezone(BAKU) if now.tzinfo else now.replace(tzinfo=BAKU)


def _iso(dt):
    """updater.make_article-in forması (_norm_iso): UTC, saniyə. Sətir kimi sıralananda vaxt sırası alınır."""
    return dt.astimezone(datetime.timezone.utc).isoformat(timespec="seconds")


def _when(text):
    """ISO vaxt -> Bakı vaxtı (aware) və ya None."""
    try:
        t = datetime.datetime.fromisoformat(str(text))
    except (TypeError, ValueError):
        return None
    return t.astimezone(BAKU) if t.tzinfo else t.replace(tzinfo=BAKU)


def _path(root, parts):
    return pathlib.Path(root).joinpath(*parts)


def _write(path, text):
    """Fayl ya tam yazılır, ya heç: müvəqqəti fayl + os.replace."""
    path = pathlib.Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    tmp.write_text(text, encoding="utf-8")
    os.replace(tmp, path)


def site():
    return str(getattr(ox._u(), "SITE", "") or "https://8ulduz.az/")


# --- Vəziyyət faylı --------------------------------------------------------------------------------------------

def fresh():
    return {"v": 1, "start": "", "done": {}, "queue": [], "out": [], "blocked": [], "errors": [], "closes": {},
            "reqs": {}, "shut": {}, "next": ""}


def load(root):
    """Vəziyyət. Fayl yoxdursa və ya pozulubsa təzə vəziyyət."""
    st = fresh()
    try:
        doc = json.loads(_path(root, STATE).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return st
    if not isinstance(doc, dict) or doc.get("v") != 1:
        return st
    for k, v in st.items():
        if k != "v" and type(doc.get(k)) is type(v):
            st[k] = doc[k]
    st["queue"] = [q for q in st["queue"] if isinstance(q, dict) and isinstance(q.get("key"), str)
                   and isinstance(q.get("item"), dict) and isinstance(q.get("pri"), int) and _when(q.get("due"))]
    st["out"] = [o for o in st["out"] if isinstance(o, dict) and isinstance(o.get("id"), str) and _when(o.get("ts"))]
    st["done"] = {k: v for k, v in st["done"].items() if isinstance(v, str)}
    return st


def _dump(st):
    return json.dumps(st, ensure_ascii=False, separators=(",", ":"), sort_keys=True)


def save(root, st):
    _write(_path(root, STATE), _dump(st))


def _err(st, res, now, msg):
    msg = str(msg)[:240]
    res["errors"].append(msg)
    if not (st["errors"] and st["errors"][-1].get("msg") == msg):  # eyni xəta hər dövrədə faylı dəyişməsin
        st["errors"] = (st["errors"] + [{"ts": _iso(now), "msg": msg}])[-20:]


def _block(st, res, now, q, why):
    row = {"key": q.get("key") or "", "title": str((q.get("item") or {}).get("title") or "")[:140], "why": str(why)[:160],
           "ts": _iso(now)}
    res["blocked"].append(row)
    st["blocked"] = (st["blocked"] + [row])[-50:]


# --- Hədlər ----------------------------------------------------------------------------------------------------

def ceiling(start, day):
    """Günün tavanı: başlanğıcdan (start, ISO tarix) 1-ci həftə 15, 2-ci 25, 3-cü 35, sonra 40."""
    try:
        days = (day - datetime.date.fromisoformat(str(start))).days
    except (TypeError, ValueError):
        days = 0
    for until, cap in RAMP:
        if days < until:
            return cap
    return CEILING


def topic_cap(topic, day, limit):
    """Mövzunun gündəlik həddi: cədvəl (iş günü / həftə sonu), amma tavanın üçdə birindən (ən azı 3) çox deyil."""
    base = MOVZU_HEDD.get(topic, BASQA_HEDD)[1 if day.weekday() >= 5 else 0]
    return min(base, max(3, limit // 3))


def priority(name, item):
    base, kinds = ONCELIK.get(name, (2, {}))
    return kinds.get(item.get("kind"), base)


def category(item):
    slug = BOLME_NOV.get(item.get("kind")) or BOLME.get(item.get("topic")) or "gundem"
    known = {s[0] for s in getattr(ox._u(), "SECTIONS", ()) or () if s}
    return slug if not known or slug in known else "gundem"


def section_name(slug):
    for s in getattr(ox._u(), "SECTIONS", ()) or ():
        if s and s[0] == slug:
            return s[1]
    return BOLME_AD.get(slug, "Gündəm")


# --- Xəbərdən sətir və səhifə ----------------------------------------------------------------------------------

def item_id(key):
    return hashlib.sha1(("8ulduz:" + str(key)).encode("utf-8")).hexdigest()[:16]


def _line(s):
    return " ".join(str(s or "").split())


def _short(text, n):
    """updater._short kimi: n hərfdən uzun mətn son tam sözdə kəsilir, sonuna «…»."""
    if len(text) <= n:
        return text
    return text[:n].rsplit(" ", 1)[0] + "…"


def row(item, when):
    """Lent sətri: updater.make_article-in açarları ilə. Tam mətn sətirdə yoxdur, yalnız xəbərin öz səhifəsində."""
    u = ox._u()
    ident = item_id(item["key"])
    image = str(item.get("image") or "").strip()
    if not (image.lower().startswith("https://") and content_policy.safe_url(image)):
        image = ""
    return {
        "id": ident,
        "title": _line(item.get("title")),
        "summary": _short(_line(item.get("lead")), int(getattr(u, "SUMMARY_MAX", 220) or 220)),
        "category": category(item),
        "source": ox.SOURCE,
        "sourceUrl": f"{site()}xeber/{ident}/",
        "publishedAt": _iso(when),
        "imageUrl": image or None,
        "lang": "az",
        "author": "",
        "video": False,
    }


def _body(item):
    body = item.get("body") or []
    if isinstance(body, str):
        body = [body]
    return [_line(p) for p in body if _line(p)]


def gate(item, r):
    """Məzmun qapısı (3-cü kilid): dərc olunmamağın səbəbi və ya None."""
    title, lead, body = _line(item.get("title")), _line(item.get("lead")), _body(item)
    if not title or not lead:
        return "başlıq və ya giriş boşdur"
    try:
        if ox.needs_owner("\n".join([title, lead, *body])):
            return "rəhbərliyin adı keçir: sahibin təsdiqini gözləyir"
        negative = getattr(ox._u(), "is_negative_about_leadership", None)
        if negative and negative(title, " ".join([lead, *body])):
            return "redaksiya süzgəci: rəhbərlik haqqında neqativ çağrışım"
    except Exception as e:
        return f"qapı xətası: {type(e).__name__}"
    if not content_policy.safe_url(item.get("link")):
        return "mənbə keçidi təhlükəsiz deyil"
    return content_policy.violation(r)


_PAGE = """<!doctype html>
<html lang="az">
<head>
<meta charset="UTF-8" />
<meta name="viewport" content="width=device-width, initial-scale=1.0" />
<title>__TITLE__ — 8ulduz</title>
<meta name="description" content="__DESC__" />
<meta name="robots" content="max-image-preview:large" />
<link rel="canonical" href="__URL__" />
<meta name="theme-color" content="#0a1120" />
<meta property="og:type" content="article" /><meta property="og:site_name" content="8ulduz" /><meta property="og:title" content="__TITLE__" />
<meta property="og:description" content="__DESC__" /><meta property="og:url" content="__URL__" /><meta property="og:image" content="__IMAGE__" />
<meta property="og:locale" content="az_AZ" /><meta property="article:published_time" content="__ISO__" /><meta name="twitter:card" content="summary_large_image" />
<link rel="icon" href="__SITE__assets/icon-192.png" sizes="192x192" />
<link rel="alternate" type="application/rss+xml" title="8ulduz" href="__SITE__feed.xml" />
<script type="application/ld+json">__LD__</script>
<style>body{margin:0;font:17px/1.55 system-ui,-apple-system,"Segoe UI",Roboto,sans-serif;background:#0a1120;color:#e8edf5}main{max-width:720px;margin:0 auto;padding:16px}a{color:#7cc4ff}h1{font-size:1.5em;line-height:1.25;margin:.4em 0 .2em}time,.qeyd{color:#9fb0c6;font-size:.9em}.giris{font-weight:600}ul{padding-left:1.2em}li{margin:0 0 .5em}img{display:block;max-width:100%;height:auto;border-radius:12px;margin:.8em 0}.cta{background:#13203a;border-radius:12px;padding:12px 14px;margin:1.4em 0}@media(prefers-color-scheme:light){body{background:#fff;color:#111}time,.qeyd{color:#555}.cta{background:#eef4fb}a{color:#0b5cad}}</style>
</head>
<body><main>
<p><a href="__SITE__">8ULDUZ</a> › <a href="__SECURL__">__SECTION__</a></p>
<article>
<h1>__TITLE__</h1>
<p><time datetime="__ISO__">__WHEN__</time></p>
__FIGURE__<p class="giris">__LEAD__</p>
__BODY__
<p>Mənbə: <a href="__LINK__" rel="noopener">__CREDIT__</a></p>
<p class="qeyd">Bu xəbəri 8ULDUZ mənbənin məlumatı əsasında hazırlayıb.</p>
</article>
<p class="cta">8ULDUZ-un xəbərləri Telegram kanalımızda: <a href="__TG__">t.me/sekkizulduz_az</a></p>
<p><a href="__SECURL__">__SECTION__ bölməsi</a> · <a href="__SITE__">8ULDUZ — bütün xəbərlər</a> · <a href="__TG__">Telegram kanalı</a></p>
</main></body>
</html>
"""


def page(item, r):
    """Xəbərin statik, skriptsiz səhifəsi (updater._DIGEST_HTML üslubunda). Yeganə <script> JSON-LD-dir."""
    e = lambda s: html.escape(str(s or ""), quote=True)
    base = site()
    when = _when(r["publishedAt"]) or _baku(None)
    body = _body(item)
    if item.get("list"):
        text = "<ul>" + "".join(f"<li>{e(p)}</li>" for p in body) + "</ul>" if body else ""
    else:
        text = "\n".join(f"<p>{e(p)}</p>" for p in body)
    image = r.get("imageUrl") or f"{base}assets/og-default.png"
    ld = {"@context": "https://schema.org", "@type": "NewsArticle", "headline": r["title"][:110],
          "datePublished": r["publishedAt"], "dateModified": r["publishedAt"], "image": [image],
          "mainEntityOfPage": r["sourceUrl"], "inLanguage": "az", "description": r["summary"],
          "author": {"@type": "Organization", "name": "8ulduz", "url": base},
          "publisher": {"@type": "Organization", "name": "8ulduz", "url": base,
                        "logo": {"@type": "ImageObject", "url": f"{base}assets/icon-192.png"}}}
    vals = {
        "TITLE": e(r["title"]), "DESC": e(r["summary"]), "URL": e(r["sourceUrl"]), "IMAGE": e(image), "ISO": e(r["publishedAt"]),
        "SITE": e(base), "SECURL": e(f"{base}bolme/{r['category']}/"), "SECTION": e(section_name(r["category"])),
        "WHEN": e(f"{when.day} {ox.MONTHS[when.month - 1]} {when.year}, {when:%H:%M}"),
        "FIGURE": f'<img src="{e(r["imageUrl"])}" alt="{e(r["title"])}" />\n' if r.get("imageUrl") else "",
        "LEAD": e(_line(item.get("lead"))), "BODY": text, "LINK": e(str(item.get("link") or "").strip()),
        "CREDIT": e(_line(item.get("credit")) or "mənbə"), "TG": TELEGRAM,
        "LD": json.dumps(ld, ensure_ascii=False).replace("<", "\\u003c"),
    }
    # Bir keçid: yerinə qoyulan mətn bir də axtarılmır (başlıqda «__SITE__» yazılsa belə dəyişmir).
    return re.sub(r"__([A-Z]+)__", lambda m: vals.get(m.group(1), m.group(0)), _PAGE)


# --- Modullar --------------------------------------------------------------------------------------------------

class _Sorgusuz(OSError):
    """Sınaqda keçmiş saatların sorğusu: getmir və sayılmır."""


def _no_net(url, *args, **kwargs):
    raise _Sorgusuz("sınaqda keçmiş saata sorğu getmir")


def _default_fetch(url, *args, **kwargs):
    return ox._u().fetch(url, *args, **kwargs)


def _counted(fetch, counts, name, cap):
    """Modulun sorğu funksiyası: gündəlik həddi keçəndə xəta verir (modul xəbərsiz qayıdır)."""
    def get(url, *args, **kwargs):
        n = int(counts.get(name) or 0)
        if n >= cap:
            raise RuntimeError(f"{name}: gündəlik sorğu həddi ({cap})")
        counts[name] = n + 1
        try:
            return fetch(url, *args, **kwargs)
        except _Sorgusuz:
            counts[name] = n
            raise
    return get


def modules():
    names = [n for n, _ in ox.FAZA1 + ox.FAZA2 + ox.FAZA3]
    if callable(getattr(ox, "items", None)):
        names.append("oz_xeber")
    return names


def _rule(name, extra=None):
    return {**QAYDA_ADI, **(QAYDA.get(name) or {}), **(extra or {})}


def _mods(mods):
    """mods: ad (str), (ad, modul) və ya (ad, modul, qayda). Verilməsə FAZA1 + FAZA2 (və items-i varsa oz_xeber)."""
    out = []
    for m in (modules() if mods is None else mods):
        if isinstance(m, str):
            out.append((m, None, _rule(m)))
        else:
            out.append((str(m[0]), m[1], _rule(str(m[0]), m[2] if len(m) > 2 else None)))
    return out


def _call(obj, root, now, fetch, done, history):
    """Modulun items()-i, öz imzasına görə: fetch, done və history yalnız parametri varsa ötürülür."""
    fn = getattr(obj, "items", None) or obj
    params = inspect.signature(fn).parameters
    kwargs = {}
    if "fetch" in params:
        kwargs["fetch"] = fetch
    if "done" in params:
        kwargs["done"] = set(done)
    if "history" in params:
        kwargs["history"] = history
    return fn(root, now, **kwargs)


_KEEP = ("kind", "key", "title", "lead", "credit", "link", "topic", "slot", "date", "image")


def _clean(item):
    """Növbədə saxlanan xəbər: yalnız bilinən sahələr, JSON-a yazıla bilən."""
    out = {k: str(item[k]) for k in _KEEP if item.get(k) not in (None, "")}
    out["body"] = _body(item)
    if item.get("list"):
        out["list"] = True
    return out


def _slot(item, now):
    """Xəbərin slot anı (Bakı): «date» varsa o gün, yoxsa bu gün. Oxunmursa None."""
    try:
        h, m = str(item.get("slot") or "").split(":")
        d = datetime.date.fromisoformat(str(item["date"])) if item.get("date") else now.date()
        return datetime.datetime.combine(d, datetime.time(int(h), int(m)), BAKU)
    except (TypeError, ValueError):
        return None


def _take(st, now, name, rule, item):
    """Modulun bir xəbəri: done qaydası və növbə."""
    if not isinstance(item, dict) or not isinstance(item.get("key"), str) or not item["key"]:
        return
    key = item["key"]
    if key in st["done"]:
        return
    if not item.get("worth"):
        if rule["done"] == "hamisi":
            st["done"][key] = _iso(now)
        return
    due, slot = now, _slot(item, now)
    if slot and slot > now:
        if rule["gelecek"] == "gozle":
            return
        if rule["gelecek"] == "vaxtinda":
            due = slot
    st["done"][key] = _iso(now)
    if any(q["key"] == key for q in st["queue"]) or any(o.get("key") == key for o in st["out"]):
        return
    st["queue"].append({"key": key, "mod": name, "due": _iso(due), "pri": priority(name, item), "item": _clean(item)})
    if rule.get("bir"):
        st["shut"][name] = now.date().isoformat()


def _collect(root, st, now, fetch, mods, res, t0):
    mods = _mods(mods)
    names = [m[0] for m in mods]
    first = names.index(st["next"]) if st["next"] in names else 0
    st["next"] = ""
    day = now.date().isoformat()
    if st["reqs"].get("day") != day or not isinstance(st["reqs"].get("n"), dict):
        st["reqs"] = {"day": day, "n": {}}
    st["shut"] = {k: v for k, v in st["shut"].items() if v == day}
    fetch = fetch or _default_fetch
    for name, obj, rule in mods[first:] + mods[:first]:
        if _clock() - t0 >= BUDGET_S:
            st["next"] = name
            _err(st, res, now, f"vaxt büdcəsi ({BUDGET_S} s) bitdi: {name} və sonrakı modullar növbəti dövrəyə qaldı")
            break
        if rule.get("basla") and f"{now:%H:%M}" < rule["basla"]:
            continue
        if rule.get("bir") and st["shut"].get(name) == day:
            continue
        try:
            if obj is None:
                obj = ox if name == "oz_xeber" else importlib.import_module(name)
            found = _call(obj, root, now, _counted(fetch, st["reqs"]["n"], name, int(rule["sorgu"])), st["done"], st["closes"])
            for item in found or []:
                _take(st, now, name, rule, item)
        except Exception as e:
            _err(st, res, now, f"{name}: {type(e).__name__}: {e}")


def _closes(root, st, now):
    """oz_bazar üçün markets.json nüsxələri: bağlanışdan sonrakı fasilənin son nüsxəsi və şənbənin nüsxəsi."""
    try:
        import oz_bazar as ob
        doc = ob.read_markets(root)
        at = ob._when(doc.get("updatedAt"))
        if at:
            snap = {"updatedAt": doc["updatedAt"],
                    "items": [i for i in doc.get("items") or [] if isinstance(i, dict) and i.get("id") in ob.WEEK_IDS]}
            close = ob.close_time(at)
            if close <= at < close + ob.BREAK:
                st["closes"]["b-" + close.date().isoformat()] = snap
            elif at.weekday() == 5 and at.time() >= ob.SETTLED:
                key = "h-" + at.date().isoformat()
                old = ob._when((st["closes"].get(key) or {}).get("updatedAt"))
                if not old or (old.time() < ob.WEEKLY_SLOT and at > old):
                    st["closes"][key] = snap
    except Exception:
        pass
    keep = {}
    for k, v in st["closes"].items():
        at = _when(v.get("updatedAt")) if isinstance(v, dict) else None
        if at and now - at <= CLOSES_KEEP:
            keep[k] = v
    st["closes"] = keep


# --- Növbə, seçim, dərc ----------------------------------------------------------------------------------------

def _expire(st, now, res):
    keep = []
    for q in st["queue"]:
        due = _when(q.get("due")) or now
        if now.date() > due.date() or now - due > LATE:
            _block(st, res, now, q, "gecikdi")
        else:
            keep.append(q)
    st["queue"] = keep


def _publish(root, st, now, res):
    day = now.date()
    limit = ceiling(st["start"], day)
    stamps = [(o, _when(o.get("ts"))) for o in st["out"]]
    today = [o for o, t in stamps if t and t.date() == day]
    hour = sum(1 for _, t in stamps if t and now - HOUR < t <= now)
    ready = [q for q in st["queue"] if (_when(q.get("due")) or now) <= now]
    if len(ready) > limit - len(today):   # gün hamısını götürmür: vacib olan əvvəl
        ready.sort(key=lambda q: (-q["pri"], q["due"], str(q["item"].get("slot") or ""), q["key"]))
    else:                                 # adi halda vaxt sırası: növbəyə düşmə anı, sonra slot
        ready.sort(key=lambda q: (q["due"], str(q["item"].get("slot") or ""), -q["pri"], q["key"]))
    topics = {}
    for o in today:
        topics[o.get("topic") or ""] = topics.get(o.get("topic") or "", 0) + 1
    last = st["out"][-1] if st["out"] else None
    rows, seen = [], set()
    for q in ready:
        seen.add(q["key"])
        item = q["item"]
        topic = item.get("topic") or ""
        why = ""
        if len(today) + len(rows) >= limit:
            why = f"gündəlik hədd: {limit} xəbər"
        elif hour + len(rows) >= PER_HOUR:
            why = f"saatlıq hədd: bir saatda ən çox {PER_HOUR} xəbər"
        elif len(rows) >= PER_CYCLE:
            why = f"bir dövrədə ən çox {PER_CYCLE} xəbər: növbəti dövrəyə qalır"
        elif topics.get(topic, 0) >= topic_cap(topic, day, limit):
            why = f"mövzu həddi: «{topic}» mövzusundan gündə ən çox {topic_cap(topic, day, limit)} xəbər"
        elif last and (last.get("topic") or "") == topic:
            other = any((x["item"].get("topic") or "") != topic
                        and topics.get(x["item"].get("topic") or "", 0) < topic_cap(x["item"].get("topic") or "", day, limit)
                        for x in ready if x["key"] not in seen)
            if other or now - (_when(last.get("ts")) or now) < SAME_TOPIC_GAP:
                why = f"ardıcıl eyni mövzu («{topic}»): başqa mövzu və ya 20 dəqiqə gözlənir"
        if why:
            res["held"].append({"key": q["key"], "title": str(item.get("title") or ""), "why": why})
            continue
        st["queue"].remove(q)
        try:
            r = row(item, now)
            block = gate(item, r)
            path = _path(root, ("xeber", r["id"], "index.html"))
            if not block and path.exists():
                block = "bu açarın səhifəsi artıq var"   # vəziyyət faylı itsə belə xəbər ikinci dəfə dərc olunmur
            if not block:
                _write(path, page(item, r))
        except Exception as e:
            block = f"xəta: {type(e).__name__}: {e}"
        if block:
            _block(st, res, now, q, block)
            continue
        last = {"id": r["id"], "key": q["key"], "ts": r["publishedAt"], "topic": topic, "title": r["title"]}
        st["out"].append(last)
        topics[topic] = topics.get(topic, 0) + 1
        rows.append(r)
    return rows


def _rows(root, new, now):
    """data/oz/xeberler.json: son 48 saatın sətirləri. Yazılan siyahı content_policy.enforce-dan keçir (qırmızı xətt 2)."""
    path = _path(root, ROWS)
    try:
        old = json.loads(path.read_text(encoding="utf-8")).get("articles") or []
    except (OSError, ValueError, AttributeError):
        old = []
    keep, ids = [], set()
    for r in list(new) + [r for r in old if isinstance(r, dict)]:
        at = _when(r.get("publishedAt"))
        if at and now - at <= ROWS_KEEP and r.get("id") not in ids:
            ids.add(r.get("id"))
            keep.append(r)
    keep, _ = content_policy.enforce(keep)
    keep.sort(key=lambda r: r.get("publishedAt") or "", reverse=True)
    if keep != old and (keep or path.exists()):
        _write(path, json.dumps({"v": 1, "articles": keep}, ensure_ascii=False, separators=(",", ":")))


def _prune(root, st, now):
    st["done"] = {k: v for k, v in st["done"].items() if (_when(v) or now) > now - DONE_KEEP}
    out = []
    for o in st["out"]:
        at = _when(o.get("ts")) or now
        if now - at > PAGE_KEEP:   # yalnız öz siyahımızdakı səhifə silinir
            for p in (_path(root, ("xeber", o["id"], "index.html")), _path(root, ("xeber", o["id"]))):
                try:
                    p.unlink() if p.is_file() else p.rmdir()
                except OSError:
                    pass
            continue
        out.append(o if now - at <= OUT_FULL else {k: o[k] for k in ("id", "key", "ts") if k in o})
    st["out"] = out


def _cycle(root, now, fetch, mods, res):
    t0 = _clock()
    st = load(root)
    before = _dump(st)
    if not st["start"]:
        st["start"] = now.date().isoformat()
    _closes(root, st, now)
    _collect(root, st, now, fetch, mods, res, t0)
    _expire(st, now, res)
    res["published"] = _publish(root, st, now, res)
    _prune(root, st, now)
    _rows(root, res["published"], now)
    res["queued"] = len(st["queue"])
    if _dump(st) != before or not _path(root, STATE).exists():
        save(root, st)
    return res


def cycle(root, now=None, fetch=None, env=None, mods=None):
    """Yavaş dövrənin bir addımı. Heç vaxt xəta atmır. Bayraq (OZ_DERC=1) yoxdursa dərhal qayıdır: heç nə etmir.
    Qaytarır: enabled, published (sətirlər), queued (növbədə qalanların sayı), held (bu dövrədə saxlanılanlar, səbəbi
    ilə), blocked (düşənlər, səbəbi ilə), errors."""
    res = {"enabled": False, "published": [], "queued": 0, "held": [], "blocked": [], "errors": []}
    try:
        env = os.environ if env is None else env
        if str(env.get(FLAG) or "") != "1":
            return res
        res["enabled"] = True
        return _cycle(pathlib.Path(root), _baku(now), fetch, mods, res)
    except Exception as e:
        res["errors"].append(f"oz_derc: {type(e).__name__}: {e}"[:240])
        return res


# --- Sınaq -----------------------------------------------------------------------------------------------------

@contextlib.contextmanager
def registered():
    """YALNIZ sınaq və testlər üçün: «8ULDUZ» icazəli siyahıdaymış kimi. Çıxanda siyahı əvvəlki halına qayıdır."""
    name = ox.SOURCE
    had, old = name in content_policy.AZ_SOURCES, content_policy.AZ_SOURCES.get(name)
    content_policy.AZ_SOURCES[name] = [content_policy.host_of(site())]
    try:
        yield
    finally:
        if had:
            content_policy.AZ_SOURCES[name] = old
        else:
            content_policy.AZ_SOURCES.pop(name, None)


class _Lent:
    """Sınaq üçün modul örtüyü. Xəbərlər əsl qovluqdan (root) qurulur, cycle isə müvəqqəti qovluğa yazır.
    Birinci keçiddə cavablar yadda saxlanır; ikinci keçiddə (başqa tavanla) modul çağırılmır, eyni cavab oxunur."""

    def __init__(self, name, root, tape, replay):
        self.name, self.root, self.tape, self.replay = name, root, tape, replay

    def items(self, root, now, fetch=None, done=None, history=None):
        k = (self.name, now.isoformat())
        if self.replay:
            return [dict(i) for i in self.tape.get(k) or []]
        obj = ox if self.name == "oz_xeber" else importlib.import_module(self.name)
        found = [i for i in _call(obj, self.root, now, fetch, done or (), history) or [] if isinstance(i, dict)]
        self.tape[k] = [dict(i) for i in found]
        return found


def _ticks(now):
    t = datetime.datetime.combine(now.date(), datetime.time(0, 0), BAKU)
    out = []
    while t < now:
        out.append(t)
        t += datetime.timedelta(minutes=30)
    return out + [now]


def _dry(root, now, start, tape, replay, fetch, net=True):
    """Bir günün quru sınağı müvəqqəti qovluqda: günün əvvəlindən now-a qədər 30 dəqiqəlik addımlar. Keçmiş addımlarda
    yalnız «novbe» qaydalı (sorğusuz işləyən) modullar çağırılır və sorğu getmir; son addımda (net) bütün modullar, əsl
    sorğu ilə. Əvvəlcə bir isinmə dövrəsi (əvvəlki gün 23:59): pəncərəsi dünəndən açıq qalan xəbərlərin açarı done-a
    düşür ki, canlıda dünən dərc olunmuş xəbər bu günün siyahısında görünməsin; onun nəticəsi sayılmır."""
    out = {"rows": [], "pages": {}, "blocked": [], "held": [], "errors": [], "queue": 0, "bytes": 0, "cut": False}
    ticks = _ticks(now)
    offline = [name for name in modules() if _rule(name)["done"] == "novbe"]
    t0 = _clock()
    with tempfile.TemporaryDirectory() as tmp:
        tmp = pathlib.Path(tmp)
        save(tmp, dict(fresh(), start=start.isoformat()))
        cycle(tmp, ticks[0] - datetime.timedelta(minutes=1), fetch=_no_net, env={FLAG: "1"},
              mods=[(name, _Lent(name, root, tape, replay)) for name in offline])
        save(tmp, dict(fresh(), start=start.isoformat(), done=load(tmp)["done"]))
        for n, t in enumerate(ticks):
            last = n == len(ticks) - 1
            if not last and not replay and _clock() - t0 > SINAQ_S:
                out["cut"] = True
                continue
            mods = [(name, _Lent(name, root, tape, replay)) for name in (modules() if last and net else offline)]
            res = cycle(tmp, t, fetch=fetch if last else _no_net, env={FLAG: "1"}, mods=mods)
            out["rows"] += res["published"]
            out["blocked"] += res["blocked"]
            out["errors"] += res["errors"]
            if last:
                out["held"], out["queue"] = res["held"], res["queued"]
        for r in out["rows"]:
            try:
                out["pages"][r["id"]] = (tmp / "xeber" / r["id"] / "index.html").read_text(encoding="utf-8")
            except OSError:
                pass
        try:
            out["bytes"] = _path(tmp, STATE).stat().st_size
        except OSError:
            pass
    return out


def _cell(s):
    return str(s or "").replace("|", "/").replace("\n", " ")


def _run_md(title, run):
    md = [f"### {title}: {len(run['rows'])} xəbər", ""]
    if run["rows"]:
        md += ["| Saat | Bölmə | Başlıq |", "|---|---|---|"]
        for r in run["rows"]:
            at = _when(r["publishedAt"])
            md.append(f"| {at:%H:%M} | {_cell(section_name(r['category']))} | {_cell(r['title'])} |")
        md.append("")
    kept = [(h["title"], h["why"]) for h in run["held"]] + [(b["title"], b["why"]) for b in run["blocked"]]
    if kept:
        md += ["Saxlanılanlar və düşənlər:", ""] + [f"- {_cell(t)}: {w}" for t, w in kept] + [""]
    else:
        md += ["Saxlanılan və ya düşən xəbər yoxdur.", ""]
    for e in run["errors"][:5]:
        md.append(f"> Qeyd: {e}")
    return md + ([""] if run["errors"] else [])


def _sinaq(root, now, fetch):
    here = pathlib.Path(__file__).resolve().parent
    code = {}
    for name, p in (("updater", here / "updater.py"), ("pipeline", here / ".github" / "scripts" / "pipeline.sh")):
        try:
            code[name] = p.read_text(encoding="utf-8")
        except OSError:
            code[name] = ""
    # Çağırış: updater.py-ın yavaş addımı; bayraq: saytın pipeline-ı onu qoyurmu (bu prosesin öz mühiti də sayılır).
    wired = "oz_derc.cycle(" in code["updater"]
    flag = bool(re.search(rf"^[ \t]*(?:export[ \t]+)?{FLAG}=1\b", code["pipeline"], re.M)) or str(os.environ.get(FLAG) or "") == "1"
    listed = ox.SOURCE in content_policy.AZ_SOURCES
    md = ["# Dərc hissəsi (oz_derc.py): sınaq", "",
          f"{now:%d.%m.%Y %H:%M} (Bakı vaxtı). Sayta və repoya heç nə yazılmır: sınaq müvəqqəti qovluqda işləyir.", "",
          "## 1. Üç kilid", "",
          "- Çağırış: updater.py-ın yavaş dövrəsi bu faylı " + ("çağırır (yalnız bayraqla). **AÇIQDIR.**" if wired else "çağırmır. Bağlıdır."),
          f"- Bayraq: pipeline.sh `{FLAG}=1` mühit dəyişənini " + ("qoyur. **AÇIQDIR.**" if flag else "qoymur. Bağlıdır."),
          f"- Məzmun qapısı: «{ox.SOURCE}» icazəli mənbələr siyahısında (assets/content-policy.js) "
          + ("var. **AÇIQDIR.**" if listed else "yoxdur. Bağlıdır."), "",
          "Üçü də açılmayınca heç nə dərc olunmur. Aşağıdakı siyahılar «üçü də açıq olsaydı» sınağıdır.", ""]
    box = {"n": 0}
    real = fetch or _default_fetch

    def limited(url, *args, **kwargs):
        if box["n"] >= SINAQ_SORGU:
            raise OSError(f"sınağın sorğu həddi ({SINAQ_SORGU})")
        box["n"] += 1
        return real(url, *args, **kwargs)

    t0 = _clock()
    tape, tape2 = {}, {}
    old = datetime.timedelta(days=28)
    yday = datetime.datetime.combine(now.date(), datetime.time(0, 0), BAKU) - datetime.timedelta(minutes=1)
    sunday = yday - datetime.timedelta(days=(yday.weekday() + 1) % 7)   # dünən və ya ondan əvvəlki son bazar günü
    past = [("Dünən", yday)] + ([(f"{ox.day_text(sunday.date())} (bazar)", sunday)] if sunday != yday else [])
    with registered():
        first = _dry(root, now, now.date(), tape, False, limited)
        full = _dry(root, now, now.date() - old, tape, True, _no_net)
        runs = []
        for label, end in past:
            tape2 = {}
            runs.append((label, _dry(root, end, end.date(), tape2, False, _no_net, net=False),
                         _dry(root, end, end.date() - old, tape2, True, _no_net, net=False), tape2))
    md += ["## 2. Bu gün nə dərc olunardı", "",
           f"Günün əvvəlindən indiyədək ({now:%H:%M}) 30 dəqiqəlik addımlarla {len(_ticks(now))} dövrə. Keçmiş saatlara sorğu "
           f"getmir, ona görə sorğu ilə işləyən modulların xəbəri yalnız son dövrədə ola bilər. Sorğu: {box['n']}, vaxt: "
           f"{_clock() - t0:.0f} saniyə, tam günün sonunda vəziyyət faylı: {max(r[2]['bytes'] for r in runs)} bayt."
           + (" Vaxt çatmadı: keçmiş addımların bir hissəsi buraxıldı." if first["cut"] or any(r[1]["cut"] for r in runs) else ""), ""]
    md += _run_md(f"İlk həftənin tavanı ilə (gündə {RAMP[0][1]})", first)
    md += _run_md(f"Tam tavanla (gündə {CEILING})", full)
    md += ["Müqayisə üçün keçmiş tam günlər (yalnız sorğusuz işləyən modullar: futbol, təqvim, səma; sorğu ilə işləyən "
           "modulların xəbərləri bura düşmür, canlıda siyahı bundan uzun olar).", ""]
    for label, one, many, _ in runs:
        md += _run_md(f"{label}, ilk həftənin tavanı ilə (gündə {RAMP[0][1]})", one)
        md += _run_md(f"{label}, tam tavanla (gündə {CEILING})", many)
    rows, pages, tapes = full["rows"] or first["rows"], dict(first["pages"], **full["pages"]), [tape]
    md += ["## 3. Əsl qapının bu günkü qərarı", ""]
    if not rows:   # günün əvvəlində bu günün siyahısı boşdur: yoxlama və nümunələr keçmiş günün siyahısındandır
        label, _, many, tape2 = max(runs, key=lambda r: len(r[2]["rows"]))
        if many["rows"]:
            rows, pages, tapes = many["rows"], many["pages"], [tape2]
            md += [f"Bu gün hələ dərc olunası xəbər yoxdur: yoxlama və nümunələr «{label}» siyahısındandır.", ""]
    clean, dropped = content_policy.enforce(rows)
    if not rows:
        md += ["Yoxlanacaq sətir yoxdur.", ""]
    else:
        why = ", ".join(f"«{k}»: {v}" for k, v in sorted(dropped.items()))
        md += [f"Yoxlanan sətir: {len(rows)}. Keçən: {len(clean)}. Rədd edilən: {len(rows) - len(clean)}"
               + (f" ({why})." if why else "."), ""]
    keys = {item_id(i["key"]): i["key"] for t in tapes for found in t.values() for i in found if isinstance(i.get("key"), str)}
    pick = []
    for r in rows:   # iki nümunə: mümkünsə başqa-başqa bölmədən
        if len(pick) < 2 and r["category"] not in [p["category"] for p in pick]:
            pick.append(r)
    pick += [r for r in rows if r not in pick][:2 - len(pick)]
    md += ["## 4. Nümunə: lentə düşəcək sətirlər", ""]
    if not pick:
        md += ["Göstəriləsi xəbər yoxdur.", ""]
    for r in pick:
        md += ["```json", json.dumps(r, ensure_ascii=False, indent=1), "```", ""]
    md += ["## 5. Nümunə: xəbərin səhifəsi", ""]
    for r in pick:
        text = pages.get(r["id"]) or ""
        key = str(keys.get(r["id"]) or r["id"]).replace("--", "-")
        md += ["```html", f"<!-- OZ-DERC-SEHIFE-BASLADI {key} -->", text.rstrip("\n"), "<!-- OZ-DERC-SEHIFE-BITDI -->", "```", ""]
    if callable(getattr(ox, "baza_sinaq", None)):
        used = {"n": 0}

        def few(url, *args, **kwargs):
            if used["n"] >= SINAQ_BAZA:
                raise OSError(f"nümunələrin sorğu həddi ({SINAQ_BAZA})")
            used["n"] += 1
            return real(url, *args, **kwargs)

        md += ["## 6. Baza xəbərləri (oz_xeber.items): pəncərə nümunələri", "",
               "Hər xəbər öz pəncərəsinin anı üçün qurulub; canlıda yuxarıdakı siyahıya öz saatında düşür.", ""]
        try:
            md += ox.baza_sinaq(root, now, few)
        except Exception as e:
            md += [f"> nümunələr alınmadı: {type(e).__name__}", ""]
        md += [f"Sorğu: {used['n']}.", ""]
    return md


def sinaq(root, now=None, fetch=None):
    """Sahib üçün nümunə (Markdown). root-a heç nə yazmır, heç vaxt xəta atmır."""
    try:
        return _sinaq(pathlib.Path(root), _baku(now), fetch)
    except Exception as e:
        return [f"> oz_derc sınağı xəta ilə bitdi: {type(e).__name__}: {e}"[:300], ""]


def _arg(argv, name):
    return argv[argv.index(name) + 1] if name in argv and argv.index(name) + 1 < len(argv) else None


def main(argv):
    if "--sinaq" not in argv:
        print(__doc__)
        return 0
    root = pathlib.Path(_arg(argv, "--root") or pathlib.Path(__file__).parent)
    now = _arg(argv, "--now")
    sys.stdout.write("\n".join(sinaq(root, datetime.datetime.fromisoformat(now) if now else None)) + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
