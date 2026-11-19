"""X-dən videolu xəbərlər: türk dilli rəsmi hesabların videolu paylaşımları əsasında ƏVVƏLCƏDƏN YAZILMIŞ xəbərlərin növbəsi
(sahib, 2026-11-18: «x la iş qura bilsək belə özəl 8ulduz xəbərləri verə bilərik saytda hətta videolu», «əsas türk dilində
olsun mənbələr», yerləşmə: Video bölməsi, «Son xəbərlər» lenti, xəbərin öz səhifəsi — «Bəli, başla»).

Niyə növbə faylı (oz_dunya ilə eyni səbəb): açarsız maşın tərcüməsi GitHub-dan işləmir. Mətni planlı Claude tapşırığı
yazır: X-in açıq məlumatından (API-siz: api.fxtwitter.com hesab lenti) HESABLAR-dakı hesabların videolu paylaşımlarını
götürür, Azərbaycan dilində qısa xəbər yazır və bu faylın yanındakı oz_x.json-a qoyur. Modul yalnız həmin faylı oxuyur:
sorğu göndərmir (gündə 0 sorğu), süni intellekt çağırmır.

Video saytda saxlanmır: X-in öz serverindən (video.twimg.com) oynayır, yalnız oxucu basanda. X videonu başqa saytdan
gələn sorğuya vermir (403), mənbə ünvanı göndərilməyəndə verir: tətbiq onu referrer göndərməyən iframe-də (srcdoc),
statik səhifə isə <meta name="referrer" content="no-referrer"> ilə açır. X-in skripti heç yerdə yüklənmir.

Növbə faylı: {"v": 1, "items": [sətir, ...]}. Sətir:
  id      paylaşımın nömrəsi (yalnız rəqəm; açar «x-<id>» olur)
  date    ilk dərc günü (Bakı), until: son gün (yazılmasa date + 1 gün; ən çoxu date + 3 gün)
  slot    «SS:DD», 07:00–23:59
  kind    NOVLER-dən biri (bölməni o təyin edir)
  title, lead, body (1–4 abzas)
  handle  HESABLAR-dakı hesab (credit cədvəldəki addır)
  post    paylaşımın ünvanı: https://x.com/<handle>/status/<id>
  video   https://video.twimg.com/...mp4 (paylaşımın mp4 variantı, 720p-dən böyük olmayan)
  poster  https://pbs.twimg.com/... (videonun öz şəkli)
  w, h    videonun ölçüsü (piksel)
  src     paylaşımın orijinal mətni (türkcə): xəbərdəki HƏR RƏQƏM burada olmalıdır. Dərc olunmur.

Qapılar (qırmızı xətt 2 və 4): check() sətri rədd edir, əgər oz_dunya-nın mətn qapıları pozulub (uzunluq, nisbi gün sözü,
kiril, nida, keçid, mənbədə olmayan rəqəm, rəhbərliyin adı) və ya
- hesab cədvəldə yoxdur, post/video/poster ünvanı göstərilən formada deyil, ölçü yararsızdır;
- mətndə və ya mənbə mətnində Azərbaycan mövzusu var (content_policy.AZ_TERMS, LEADER_TERMS): xarici mənbədən Azərbaycan
  haqqında xəbər düşmür. İdman hesabı da istisna deyil (məsələn «Karabağ» oyunu da düşür).
Dərc hissəsinin öz qapısı (oz_derc.gate) bundan sonra yenə işləyir.

Sınaq: python oz_x.py --sinaq --root DIR [--now 2026-11-19T12:00+04:00]
"""
import datetime
import json
import pathlib
import re
import sys
import urllib.parse

import content_policy
import oz_dunya as dn
import oz_xeber as ox

BAKU = ox.BAKU
NOVBE = pathlib.Path(__file__).resolve().with_suffix(".json")
KEY = "x-"
BODY_MAX = 4
SRC_MAX = 2
SRC_LEN = (10, 1200)
SLOT_FROM, SLOT_TO = "07:00", "23:59"
SIZE = (120, 4096)
TEKRAR = "id təkrarlanır"

# Növ -> mövzu. Hamısı bir mövzudur («video»): dərc hissəsində X xəbərlərinin öz gündəlik həddi var (oz_derc.MOVZU_HEDD),
# futbol modullarının «idman» yerini tutmur. Bölmə oz_derc.BOLME_NOV-dadır.
NOVLER = {"x-idman": "video", "x-dunya": "video", "x-elm": "video", "x-maraqli": "video"}

# Hesab -> xəbərdə göstərilən ad. Yalnız ilkin mənbələr: agentliklər, yayımçılar, klublar, federasiya, qurumlar.
# Başqasının videosunu yenidən paylaşan «xəbər» hesabları (məsələn THS Haber) yoxdur: video ilə başlıq çox vaxt uyğun gəlmir.
HESABLAR = {
    "anadoluajansi": "Anadolu Agentliyi",
    "aa_spor": "AA İdman",
    "trthaber": "TRT Haber",
    "trtspor": "TRT Spor",
    "ntvspor": "NTV Spor",
    "beINSPORTS_TR": "beIN SPORTS Türkiyə",
    "dhainternet": "Demirören Xəbər Agentliyi (DHA)",
    "ihacomtr": "İhlas Xəbər Agentliyi (İHA)",
    "euronews_tr": "Euronews Türkçe",
    "TFF_Org": "Türkiyə Futbol Federasiyası",
    "MilliTakimlar": "Türkiyə millisi",
    "GalatasaraySK": "Qalatasaray",
    "Fenerbahce": "Fənərbağça",
    "Besiktas": "Beşiktaş",
    "Trabzonspor": "Trabzonspor",
    "TUBITAK": "TÜBİTAK",
    # Sahib, 2026-11-19 («Bəli, 10-u əlavə et»): videosu çox olan xəbər və maraqlı hesablar. Münaqişə hesabları ağır kadr
    # verə bilər: yazıcının təlimatı (x_yazici.PROMPT) onları seçmir, təsdiqlənməmiş iddianı hesabın adı ilə verir.
    "TamirveTadilat": "Tamir & Tadilat",
    "clashreport": "Clash Report",
    "ConflictTR": "Conflict",
    "gusholderhaber": "Gusholder Haber",
    "Pars_Pluss": "Pars Plus",
    "avionot": "Avionot",
    "Derinkuvvet": "Derin Kuvvetler",
    "gdhdijital": "GDH",
    "ozetgechaber": "Özet Geç",
    "VoiceOfLevant": "Voice of Levant",
    # Sahib, 2026-11-19: «Azərbaycanda ən çox hansı tip qısa videolara baxıldığını araşdırıb x da o mənbələri tap» — Videolent üçün
    # vizual hesablar (idman, elm/maraqlı, oyun); FxTwitter ilə yoxlanıb, gündə 3+ video (research_notes/qisa-video-menbeleri.md).
    # Əlavə olunmayıb: siyasi şərh (TheFigen_, Pirat_Nation), mərc/kazino reklamı, qan riski (ufc), danışıq videoları (ClutchPoints).
    "Rainmaker1973": "Massimo (Rainmaker1973)",
    "LaLiga": "LaLiga",
    "premierleague": "Premyer Liqa",
    "aspor": "A Spor",
    "buitengebieden": "Buitengebieden",
    "IGN": "IGN",
    "ChampionsLeague": "UEFA Çempionlar Liqası",
    "Ballislife": "Ballislife",
    "Fotomac": "Fotomaç",
    "Yoda4ever": "Yoda4ever",
    "wonderofscience": "Wonder of Science",
    "DAZNFootball": "DAZN Football",
    "atptour": "ATP Tour",
    "F1": "Formula 1",
    "NBA": "NBA",
    "TivibuSpor": "Tivibu Spor",
    "ESPNUK": "ESPN UK",
    "TansuYegen": "Tansu Yegen",
    "ESPNNBA": "ESPN NBA",
    "WWE": "WWE",
    "EuropaLeague": "UEFA Avropa Liqası",
    "LFC": "Liverpul",
    "GameSpot": "GameSpot",
    "Discovery": "Discovery",
    "ajansspor": "Ajansspor",
    "MLS": "MLS",
    "Olympics": "Olimpiya Oyunları",
    "overtime": "Overtime",
}
_HANDLE = {h.lower(): h for h in HESABLAR}

_ID = re.compile(r"[1-9]\d{5,24}")
_POST = re.compile(r"https://x\.com/([A-Za-z0-9_]{1,15})/status/(\d+)")
_SLOT = re.compile(r"(?:[01]\d|2[0-3]):[0-5]\d")


def _line(s):
    return " ".join(str(s or "").split())


def _url_ok(url, host, suffix=""):
    """Yalnız verilən host, https, ASCII, boşluqsuz, sorğu hissəsi sadə."""
    text = str(url or "")
    if not text.isascii() or any(c in text for c in ' "\'<>\\`') or not content_policy.safe_url(text):
        return False
    try:
        parts = urllib.parse.urlsplit(text)
    except ValueError:
        return False
    return parts.scheme == "https" and parts.hostname == host and not parts.port and parts.path.lower().endswith(suffix) and not parts.fragment


def _size(v):
    return isinstance(v, int) and not isinstance(v, bool) and SIZE[0] <= v <= SIZE[1]


def about_azerbaijan(text):
    return bool(content_policy.AZ_TERMS.search(text) or content_policy.LEADER_TERMS.search(text))


def check(row):
    """Sətir dərc oluna bilməzsə səbəbi, yoxsa None."""
    if not isinstance(row, dict):
        return "sətir lüğət deyil"
    ident = row.get("id")
    if not isinstance(ident, str) or not _ID.fullmatch(ident):
        return "id yararsızdır (paylaşımın nömrəsi)"
    if dn.window(row) is None:
        return "date / until yararsızdır"
    slot = str(row.get("slot") or "")
    if not _SLOT.fullmatch(slot) or not SLOT_FROM <= slot <= SLOT_TO:
        return "slot yararsızdır (07:00–23:59)"
    if row.get("kind") not in NOVLER:
        return "növ cədvəldə yoxdur"
    handle = _HANDLE.get(str(row.get("handle") or "").lower())
    if not handle:
        return "hesab cədvəldə yoxdur"
    m = _POST.fullmatch(str(row.get("post") or ""))
    if not m or m.group(1).lower() != handle.lower() or m.group(2) != ident:
        return "post ünvanı https://x.com/<hesab>/status/<id> olmalıdır"
    if not _url_ok(row.get("video"), "video.twimg.com", ".mp4"):
        return "video ünvanı video.twimg.com-da mp4 olmalıdır"
    if not _url_ok(row.get("poster"), "pbs.twimg.com"):
        return "poster ünvanı pbs.twimg.com-da olmalıdır"
    if not (_size(row.get("w")) and _size(row.get("h"))):
        return f"w və h {SIZE[0]}–{SIZE[1]} arası tam ədəd olmalıdır"
    title, lead, body = _line(row.get("title")), _line(row.get("lead")), dn._body(row)
    if not dn.TITLE_LEN[0] <= len(title) <= dn.TITLE_LEN[1]:
        return f"başlığın uzunluğu {dn.TITLE_LEN[0]}–{dn.TITLE_LEN[1]} hərf olmalıdır"
    if title[-1] in ".?!…":
        return "başlıq nöqtə və ya sual ilə bitir"
    if not dn.LEAD_LEN[0] <= len(lead) <= dn.LEAD_LEN[1]:
        return f"girişin uzunluğu {dn.LEAD_LEN[0]}–{dn.LEAD_LEN[1]} hərf olmalıdır"
    if not 1 <= len(body) <= BODY_MAX or len(body) != len(row.get("body") or []):
        return f"mətn 1–{BODY_MAX} dolu abzas olmalıdır"
    if any(not dn.PARA_LEN[0] <= len(p) <= dn.PARA_LEN[1] for p in body):
        return f"abzasın uzunluğu {dn.PARA_LEN[0]}–{dn.PARA_LEN[1]} hərf olmalıdır"
    text = "\n".join([title, lead, *body])
    if dn._KIRIL.search(text):
        return "kiril hərfi var"
    if "!" in text or "http" in text.lower() or "www." in text.lower():
        return "nida işarəsi və ya keçid var"
    found = dn._NISBI.search(text)
    if found:
        return f"nisbi gün sözü var: «{found.group(0)}»"
    src = row.get("src")
    if not isinstance(src, list) or not 1 <= len(src) <= SRC_MAX or any(
            not isinstance(s, str) or not SRC_LEN[0] <= len(_line(s)) <= SRC_LEN[1] for s in src):
        return f"src: 1–{SRC_MAX} çıxarış, hər biri {SRC_LEN[0]}–{SRC_LEN[1]} hərf"
    corpus = "\n".join(src)
    if about_azerbaijan(text) or about_azerbaijan(corpus):
        return "xarici mənbə, Azərbaycan mövzusu"
    missing = sorted(ox._nums(text) - ox._nums(corpus) - dn.en_nums(corpus))
    if missing:
        return "mətndəki rəqəm mənbə mətnində yoxdur: " + ", ".join(missing)
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


# --- Qısa videolar ---------------------------------------------------------------------------------------------------
# Sahib, 2026-11-19: «tiktok stilini düzəlt. videoların bəzilərinə yazı tərcümə ehtiyac olmaya bilər… gündə 40».
# Növbə faylının "reels" siyahısı: yazısız videolar (mətn yazılmır, tərcümə yoxdur). Yazıcı (x_yazici.py) doldurur,
# yeniləyici (updater.update_reels) reels() ilə data/reels.json-a yazır, sayt yalnız «Qısa videolar» açılanda oxuyur.
# Sətir: id, handle, post, video, poster, w, h (xəbər sətri ilə eyni qaydalar), at (paylaşımın vaxtı, ISO UTC),
# src (orijinal mətn: yalnız Azərbaycan süzgəci üçün, sayta çıxmır).
REELS_DAYS = 7    # sahib, 2026-11-19: «günə 100 yeni video et» — lentdə ən təzə 200 video (~2 gün), ən çox 7 günlük
REELS_MAX = 200


def _at(value):
    try:
        at = datetime.datetime.fromisoformat(str(value or ""))
    except ValueError:
        return None
    return at if at.tzinfo else None


def reel_check(row):
    """Qısa video sətri göstərilə bilməzsə səbəbi, yoxsa None (qırmızı xətt 2: Azərbaycan mövzusu düşür)."""
    if not isinstance(row, dict):
        return "sətir lüğət deyil"
    ident = row.get("id")
    if not isinstance(ident, str) or not _ID.fullmatch(ident):
        return "id yararsızdır (paylaşımın nömrəsi)"
    handle = _HANDLE.get(str(row.get("handle") or "").lower())
    if not handle:
        return "hesab cədvəldə yoxdur"
    m = _POST.fullmatch(str(row.get("post") or ""))
    if not m or m.group(1).lower() != handle.lower() or m.group(2) != ident:
        return "post ünvanı https://x.com/<hesab>/status/<id> olmalıdır"
    if not _url_ok(row.get("video"), "video.twimg.com", ".mp4"):
        return "video ünvanı video.twimg.com-da mp4 olmalıdır"
    if not _url_ok(row.get("poster"), "pbs.twimg.com"):
        return "poster ünvanı pbs.twimg.com-da olmalıdır"
    if not (_size(row.get("w")) and _size(row.get("h"))):
        return f"w və h {SIZE[0]}–{SIZE[1]} arası tam ədəd olmalıdır"
    if _at(row.get("at")) is None:
        return "at: paylaşımın vaxtı (ISO, saat qurşağı ilə)"
    src = row.get("src")
    if not isinstance(src, list) or not 1 <= len(src) <= SRC_MAX or any(not isinstance(s, str) or len(s) > SRC_LEN[1] for s in src):
        return f"src: 1–{SRC_MAX} çıxarış"
    if about_azerbaijan("\n".join(src)):
        return "xarici mənbə, Azərbaycan mövzusu"
    return None


def load_reels(path=None):
    try:
        doc = json.loads(pathlib.Path(path or NOVBE).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return []
    rows = doc.get("reels") if isinstance(doc, dict) and doc.get("v") == 1 else None
    return rows if isinstance(rows, list) else []


def reels(now, path=None):
    """Saytın qısa video lenti: yoxlamadan keçən, son REELS_DAYS günün videoları, ən yenisi əvvəl. Mətn çıxmır.
    Sətir: id, a (hesab), n (hesabın adı), u (mp4), i (poster), w, h, t (vaxt)."""
    floor, out, seen = now - datetime.timedelta(days=REELS_DAYS), [], set()
    for row in load_reels(path):
        if reel_check(row) or row["id"] in seen or _at(row["at"]) < floor or _at(row["at"]) > now + datetime.timedelta(hours=1):
            continue
        seen.add(row["id"])
        h = _HANDLE[row["handle"].lower()]
        out.append({"id": row["id"], "a": h, "n": HESABLAR[h], "u": row["video"], "i": row["poster"],
                    "w": row["w"], "h": row["h"], "t": _at(row["at"]).astimezone(datetime.timezone.utc).isoformat(timespec="seconds")})
    out.sort(key=lambda r: r["t"], reverse=True)
    return out[:REELS_MAX]


def credit(handle):
    h = _HANDLE[str(handle).lower()]
    return f"{HESABLAR[h]} (X, @{h})"


def item(row, day):
    """Yoxlamadan keçmiş sətirdən dərc hissəsinin xəbəri (bu günün tarixi ilə)."""
    return {"kind": row["kind"], "key": KEY + row["id"], "title": _line(row["title"]), "lead": _line(row["lead"]),
            "body": dn._body(row), "credit": credit(row["handle"]), "link": row["post"],
            "image": row["poster"], "video": row["video"], "vw": str(row["w"]), "vh": str(row["h"]),
            "topic": NOVLER[row["kind"]], "slot": row["slot"], "date": day.isoformat(), "worth": True}


def items(root, now, fetch=None, done=None, path=None):
    """Bu günün növbədəki xəbərləri. Sorğu yoxdur; root, fetch istifadə olunmur (imza başqa modullarla eynidir)."""
    now = now.astimezone(BAKU) if now.tzinfo else now.replace(tzinfo=BAKU)
    today, done, out = now.date(), set(done or ()), []
    for row, why in rows(path):
        key = KEY + row["id"]
        span = dn.window(row)
        if key in done or why == TEKRAR or span is None or not span[0] <= today <= span[1]:
            continue
        if why:
            out.append(ox._no(str(row.get("kind") or "x-maraqli"), key, _line(row.get("title")) or row["id"], why,
                              _line(row.get("handle")), str(row.get("post") or ""), "video", str(row.get("slot") or "12:00")))
        else:
            out.append(item(row, today))
    return sorted(out, key=lambda x: (x["slot"], x["key"]))


def sinaq(root, now=None, fetch=None, path=None):
    """Nümunələr (Markdown): bu günün xəbərləri və növbə faylının bütün sətirləri. Sorğu yoxdur."""
    now = now or datetime.datetime.now(BAKU)
    now = now.replace(tzinfo=BAKU) if now.tzinfo is None else now.astimezone(BAKU)
    today = now.date()
    md = ["## X-dən videolu xəbərlər: sınaq", "",
          f"{now:%d.%m.%Y %H:%M} (Bakı vaxtı). Növbə faylı oxunur, sorğu yoxdur; sayta heç nə yazılmır.", "",
          f"### Bu gün, {ox.day_text(today)}", ""]
    todays = items(root, now, path=path)
    for it in todays:
        if it.get("worth"):
            md += ox.render(it) + [f"> Növ: {it['kind']}, video: {it['video']}, slot: {it['slot']}.", ""]
        else:
            md += [f"> **Dərc olunmur** ({it['key']}): {it['why']}", ""]
    if not todays:
        md += [f"> {ox.day_text(today)} üçün növbədə xəbər yoxdur.", ""]
    md += ["### Növbə faylı", "", "| id | günlər | slot | hesab | vəziyyət |", "|---|---|---|---|---|"]
    all_rows = rows(path)
    for row, why in all_rows:
        span = dn.window(row)
        days = f"{span[0]:%d.%m}–{span[1]:%d.%m}" if span else "?"
        state = why or ("keçib" if span and span[1] < today else "növbədə")
        md.append(f"| {row['id']} | {days} | {row.get('slot', '')} | {row.get('handle', '')} | {state} |")
    if not all_rows:
        md.append("| (boşdur) | | | | |")
    return md + [""]


def main(argv):
    if "--sinaq" not in argv:
        print(__doc__)
        return 0
    root = pathlib.Path(dn._arg(argv, "--root") or pathlib.Path(__file__).parent)
    now = dn._arg(argv, "--now")
    now = datetime.datetime.fromisoformat(now) if now else None
    sys.stdout.write("\n".join(sinaq(root, now)) + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
