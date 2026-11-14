"""Dünyadan xəbərlər: xarici açıq mənbələrin məlumatı əsasında ƏVVƏLCƏDƏN YAZILMIŞ xəbərlərin növbəsi
(sahib, 2026-11-12: «xarici mənbələrdən … xəbər tapıb dilimizə çevirib verə bilərik. bunu et», «insanların duymaq istədiyi
xəbərlər hazırla ki maraqla qarşılansın»).

Niyə növbə faylı. Açarsız maşın tərcüməsi GitHub-dan işləmir: Google hər sorğuya 429 qaytarır (2026-11-12, PR #197-nin
sınağı), Vikimediyanın tərcüməsi məna səhvi edir («qum təpələri» əvəzinə «quşlar»), GitHub Models isə 2026-07-30-da
bağlanıb (PR #198). Ona görə mətn əvvəlcədən yazılır, mənbə səhifəsi ilə tutuşdurulur və bu faylın yanındakı
oz_dunya.json-a qoyulur. Modul yalnız həmin faylı oxuyur: sorğu göndərmir (gündə 0 sorğu), süni intellekt çağırmır.

Növbə faylı: {"v": 1, "items": [sətir, ...]}. Sətir:
  id      kiçik latın hərfləri, rəqəm və tire (açar «dunya-<id>» olur; id heç vaxt təkrar işlənmir)
  date    ilk dərc günü (Bakı), until: son gün (yazılmasa date + 1 gün; ən çoxu date + 3 gün)
  slot    «SS:DD», 07:00–22:59
  kind    NOVLER-dən biri (mövzunu və bölməni o təyin edir)
  title, lead, body (1–6 abzas)
  link    mənbə səhifəsi; saytı MENBELER-də olmalıdır, credit həmin cədvəldəki addır
  image   boş və ya SEKIL_SAYTLARI-ndakı ünvan (yalnız heç bir şərtsiz istifadə olunan şəkillər)
  src     mənbə səhifəsindən hərfi çıxarışlar (ingiliscə): mətndəki HƏR RƏQƏM burada olmalıdır. Dərc olunmur.

Qapılar (qırmızı xətt 4, «Məlumat dəqiq olmalıdır»): check() sətri rədd edir, əgər
- sahə çatmır, uzunluq hədləri pozulub, mənbə saytı və ya şəkil saytı cədvəldə yoxdur, credit cədvəllə düz gəlmir;
- mətndə mənbə çıxarışında olmayan rəqəm var (ölçü vahidi çevrilmir, yuvarlaqlaşdırılmır);
- mətndə nisbi gün sözü var («bu gün», «dünən», «sabah»): xəbər ertəsi gün də dərc oluna bilər, tarix açıq yazılır;
- kiril hərfi, nida işarəsi, keçid var və ya başlıq nöqtə/sual ilə bitir;
- rəhbərliyin adı keçir (ox.needs_owner): belə xəbər bu növbə ilə verilmir.
Rədd edilən sətir worth=False ilə qayıdır (açarı done-a yazılır, sınaqda səbəbi görünür). Dərc hissəsinin öz qapısı
(oz_derc.gate: məzmun siyasəti, rəhbərlik süzgəci) bundan sonra yenə işləyir.

Vaxt: sətir date–until aralığındakı hər gün, açarı done-da deyilsə, bu günün tarixi və öz slotu ilə qayıdır. Yəni fayl
main-ə gec çatsa da (slot keçibsə) xəbər itmir: dərc hissəsi onu həmin gün, hədləri gözləyərək verir.

Sınaq: python oz_dunya.py --sinaq --root DIR [--now 2026-11-13T12:00+04:00]
"""
import datetime
import json
import pathlib
import re
import sys
import urllib.parse

import oz_xeber as ox

BAKU = ox.BAKU
NOVBE = pathlib.Path(__file__).resolve().with_suffix(".json")
KEY = "dunya-"
TITLE_LEN = (25, 110)
LEAD_LEN = (60, 420)
PARA_LEN = (40, 800)
BODY_MAX = 6
SRC_LEN = (15, 500)
SRC_MAX = 12
CREDIT_MAX = 80
UNTIL_MAX = 3                              # until ən çoxu date + 3 gün
SLOT_FROM, SLOT_TO = "07:00", "22:59"
TEKRAR = "id təkrarlanır"

# Növ -> mövzu (dərc hissəsinin mövzu hədləri üçün). Bölmə oz_derc.BOLME_NOV-dadır.
NOVLER = {"dunya-kosmos": "kosmos", "dunya-elm": "elm", "dunya-saglamliq": "sağlamlıq", "dunya-tebiet": "təbiət",
          "dunya-texno": "texnologiya", "dunya-maraqli": "dünya"}

# Mənbə saytı (son hissəsi) -> xəbərdə göstərilən ad. Yalnız ilkin mənbələr: qurumların öz səhifələri.
MENBELER = {
    "nasa.gov": "NASA",
    "esa.int": "Avropa Kosmik Agentliyi (ESA)",
    "eso.org": "Avropa Cənub Rəsədxanası (ESO)",
    "esawebb.org": "ESA/Webb",
    "esahubble.org": "ESA/Hubble",
    "noirlab.edu": "NOIRLab",
    "ourworldindata.org": "Our World in Data",
    "usgs.gov": "ABŞ Geoloji Xidməti (USGS)",
    "fda.gov": "ABŞ Qida və Dərman Administrasiyası (FDA)",
    "noaa.gov": "ABŞ Milli Okean və Atmosfer Administrasiyası (NOAA)",
    "who.int": "Ümumdünya Səhiyyə Təşkilatı",
    "nobelprize.org": "Nobel Mükafatı Komitəsi",
}
# Şəkil yalnız bu saytlardan götürülür (heç bir şərtsiz istifadə olunan şəkillər); başqa mənbənin xəbəri şəkilsiz gedir.
SEKIL_SAYTLARI = ("nasa.gov",)

_ID = re.compile(r"[a-z0-9]+(?:-[a-z0-9]+)*")
_SLOT = re.compile(r"(?:[01]\d|2[0-3]):[0-5]\d")
# Şəkilçili formalar da («dünənki», «bu günə»), amma «bu Günəş» yox: sözün sonu hərflə davam etməməlidir.
_NISBI = re.compile(r"(?<![^\W\d_])(?:bu\s?gün(?:kü|ün|ə|dən|də)?|dünən(?:ki)?|sabah(?:kı)?|srağagün|birisigün|bu səhər|bu axşam|bu gecə|ötən gün)"
                    r"(?![^\W\d_])", re.I)
_KIRIL = re.compile(r"[А-Яа-яЁё]")
_EN_NUM = re.compile(r"\d{1,3}(?:[,    ]\d{3})+(?:\.\d+)?(?!\d)|\d+(?:\.\d+)?")


def _line(s):
    return " ".join(str(s or "").split())


def _host(url):
    try:
        return (urllib.parse.urlsplit(str(url or "")).hostname or "").lower().rstrip(".")
    except ValueError:
        return ""


def _site(url, table):
    """Ünvanın saytı cədvəldədirsə onun açarı (alt domen də sayılır: science.nasa.gov -> nasa.gov), yoxsa ''."""
    if not str(url or "").startswith("https://"):
        return ""
    host = _host(url)
    for site in table:
        if host == site or host.endswith("." + site):
            return site
    return ""


def en_nums(text):
    """İngiliscə mətnin rəqəmləri, ox._nums ilə eyni formada: «25.9» -> 25.9, «12,327» və «10 000» -> 12327, 10000."""
    out = set()
    for n in _EN_NUM.findall(str(text or "")):
        whole, _, frac = re.sub(r"[,    ]", "", n).partition(".")
        out.add((whole.lstrip("0") or "0") + ("." + frac if frac else ""))
    return out


def _day(text):
    try:
        return datetime.date.fromisoformat(str(text))
    except (TypeError, ValueError):
        return None


def window(row):
    """(ilk gün, son gün) və ya None."""
    start = _day(row.get("date"))
    if start is None:
        return None
    until = _day(row["until"]) if row.get("until") not in (None, "") else start + datetime.timedelta(days=1)
    if until is None or not start <= until <= start + datetime.timedelta(days=UNTIL_MAX):
        return None
    return start, until


def _body(row):
    body = row.get("body")
    return [_line(p) for p in body if _line(p)] if isinstance(body, list) else []


def check(row):
    """Sətir dərc oluna bilməzsə səbəbi, yoxsa None."""
    if not isinstance(row, dict):
        return "sətir lüğət deyil"
    ident = row.get("id")
    if not isinstance(ident, str) or not _ID.fullmatch(ident) or not 3 <= len(ident) <= 60:
        return "id yararsızdır"
    if window(row) is None:
        return "date / until yararsızdır"
    slot = str(row.get("slot") or "")
    if not _SLOT.fullmatch(slot) or not SLOT_FROM <= slot <= SLOT_TO:
        return "slot yararsızdır (07:00–22:59)"
    if row.get("kind") not in NOVLER:
        return "növ cədvəldə yoxdur"
    title, lead, body = _line(row.get("title")), _line(row.get("lead")), _body(row)
    if not TITLE_LEN[0] <= len(title) <= TITLE_LEN[1]:
        return f"başlığın uzunluğu {TITLE_LEN[0]}–{TITLE_LEN[1]} hərf olmalıdır"
    if title[-1] in ".?!…":
        return "başlıq nöqtə və ya sual ilə bitir"
    if not LEAD_LEN[0] <= len(lead) <= LEAD_LEN[1]:
        return f"girişin uzunluğu {LEAD_LEN[0]}–{LEAD_LEN[1]} hərf olmalıdır"
    if not 1 <= len(body) <= BODY_MAX or len(body) != len(row.get("body") or []):
        return f"mətn 1–{BODY_MAX} dolu abzas olmalıdır"
    if any(not PARA_LEN[0] <= len(p) <= PARA_LEN[1] for p in body):
        return f"abzasın uzunluğu {PARA_LEN[0]}–{PARA_LEN[1]} hərf olmalıdır"
    text = "\n".join([title, lead, *body])
    if _KIRIL.search(text):
        return "kiril hərfi var"
    if "!" in text or "http" in text.lower() or "www." in text.lower():
        return "nida işarəsi və ya keçid var"
    found = _NISBI.search(text)
    if found:
        return f"nisbi gün sözü var: «{found.group(0)}»"
    site = _site(row.get("link"), MENBELER)
    if not site:
        return "mənbə saytı cədvəldə yoxdur"
    credit = _line(row.get("credit"))
    if credit != MENBELER[site] or len(credit) > CREDIT_MAX:
        return f"credit cədvəldəki ad olmalıdır: {MENBELER[site]}"
    image = str(row.get("image") or "").strip()
    if image and (not _site(image, SEKIL_SAYTLARI) or not image.isascii() or " " in image):
        return "şəkil saytı cədvəldə yoxdur və ya ünvan yararsızdır"
    src = row.get("src")
    if not isinstance(src, list) or not 1 <= len(src) <= SRC_MAX or any(
            not isinstance(s, str) or not SRC_LEN[0] <= len(_line(s)) <= SRC_LEN[1] for s in src):
        return f"src: 1–{SRC_MAX} çıxarış, hər biri {SRC_LEN[0]}–{SRC_LEN[1]} hərf"
    corpus = "\n".join(src)
    missing = sorted(ox._nums(text) - en_nums(corpus) - ox._nums(corpus))
    if missing:
        return "mətndəki rəqəm mənbə çıxarışında yoxdur: " + ", ".join(missing)
    try:
        if ox.needs_owner(text):
            return "rəhbərliyin adı keçir: bu növbə ilə verilmir"
    except Exception as e:  # süzgəc işləmirsə xəbər getmir
        return f"rəhbərlik süzgəci xətası: {type(e).__name__}"
    return None


def load(path=None):
    """Növbə faylının sətirləri. Fayl yoxdursa və ya pozulubsa boş siyahı."""
    try:
        doc = json.loads(pathlib.Path(path or NOVBE).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return []
    rows = doc.get("items") if isinstance(doc, dict) and doc.get("v") == 1 else None
    return rows if isinstance(rows, list) else []


def rows(path=None):
    """[(sətir, səbəb və ya None)]: id-si olan sətirlər, fayldakı sıra ilə. Təkrar id-nin ikinci sətri rədd edilir."""
    out, seen = [], set()
    for row in load(path):
        if not isinstance(row, dict) or not isinstance(row.get("id"), str) or not _ID.fullmatch(row["id"]):
            continue
        why = check(row)
        if row["id"] in seen:
            why = TEKRAR
        seen.add(row["id"])
        out.append((row, why))
    return out


def item(row, day):
    """Yoxlamadan keçmiş sətirdən dərc hissəsinin xəbəri (bu günün tarixi ilə)."""
    site = _site(row["link"], MENBELER)
    return {"kind": row["kind"], "key": KEY + row["id"], "title": _line(row["title"]), "lead": _line(row["lead"]),
            "body": _body(row), "credit": MENBELER[site], "link": row["link"].strip(),
            "image": str(row.get("image") or "").strip(), "topic": NOVLER[row["kind"]], "slot": row["slot"],
            "date": day.isoformat(), "worth": True}


def items(root, now, fetch=None, done=None, path=None):
    """Bu günün növbədəki xəbərləri. Sorğu yoxdur; root, fetch istifadə olunmur (imza başqa modullarla eynidir)."""
    now = now.astimezone(BAKU) if now.tzinfo else now.replace(tzinfo=BAKU)
    today, done, out = now.date(), set(done or ()), []
    for row, why in rows(path):
        key = KEY + row["id"]
        span = window(row)
        if key in done or why == TEKRAR or span is None or not span[0] <= today <= span[1]:
            continue   # təkrar id-nin ikinci sətri qayıtmır: eyni açar birincini də bağlayardı
        if why:
            out.append(ox._no(str(row.get("kind") or "dunya"), key, _line(row.get("title")) or row["id"], why,
                              _line(row.get("credit")), str(row.get("link") or ""), NOVLER.get(row.get("kind"), "dünya"),
                              str(row.get("slot") or "12:00")))
        else:
            out.append(item(row, today))
    return sorted(out, key=lambda x: (x["slot"], x["key"]))


def sinaq(root, now=None, fetch=None, path=None):
    """Nümunələr (Markdown): bu günün xəbərləri və növbə faylının bütün sətirləri. Sorğu yoxdur."""
    now = now or datetime.datetime.now(BAKU)
    now = now.replace(tzinfo=BAKU) if now.tzinfo is None else now.astimezone(BAKU)
    today = now.date()
    md = ["## Dünyadan xəbərlər: sınaq", "",
          f"{now:%d.%m.%Y %H:%M} (Bakı vaxtı). Növbə faylı oxunur, sorğu yoxdur; sayta heç nə yazılmır.", "",
          f"### Bu gün, {ox.day_text(today)}", ""]
    todays = items(root, now, path=path)
    for it in todays:
        if it.get("worth"):
            md += ox.render(it) + [f"> Növ: {it['kind']}, mövzu: {it['topic']}, slot: {it['slot']}.", ""]
        else:
            md += [f"> **Dərc olunmur** ({it['key']}): {it['why']}", ""]
    if not todays:
        md += [f"> {ox.day_text(today)} üçün növbədə xəbər yoxdur.", ""]
    md += ["### Növbə faylı", "", "| id | günlər | slot | növ | vəziyyət |", "|---|---|---|---|---|"]
    all_rows = rows(path)
    for row, why in all_rows:
        span = window(row)
        days = f"{span[0]:%d.%m}–{span[1]:%d.%m}" if span else "?"
        state = why or ("keçib" if span and span[1] < today else "növbədə")
        md.append(f"| {row['id']} | {days} | {row.get('slot', '')} | {row.get('kind', '')} | {state} |")
    if not all_rows:
        md.append("| (boşdur) | | | | |")
    return md + [""]


def _arg(argv, name):
    return argv[argv.index(name) + 1] if name in argv and argv.index(name) + 1 < len(argv) else None


def main(argv):
    if "--sinaq" not in argv:
        print(__doc__)
        return 0
    root = pathlib.Path(_arg(argv, "--root") or pathlib.Path(__file__).parent)
    now = _arg(argv, "--now")
    now = datetime.datetime.fromisoformat(now) if now else None
    sys.stdout.write("\n".join(sinaq(root, now)) + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
