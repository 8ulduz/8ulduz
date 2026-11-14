"""8ulduz-un öz xəbərləri: pik saat tıxac bülletenləri (sahib, 2026-11-14: «2 öz xəbərimizi geniş edək», «pik saat bülletenləri
gündə 2–3 dəfə səkkiz əsas yol üzrə»).

Məlumat: .github/scripts/tixac.cjs-in avtomatik ölçüsü (Mapbox tıxac məlumatı), «tixac» budağındakı tarix.json — hər ölçünün qısa
nüsxəsi (30 saat): marşrutların vaxtı [id, dəqiqə, adi dəqiqə], tıxaclı küçələr [ad, istiqamət, dərəcə, km], səkkiz əsas yol
[ad, dərəcə, km] və həmin ölçüdə yeni yol hadisələri. Şablon xəbər, süni intellektsiz: hər rəqəm ölçüdəndir.

İki bülleten:
- «Səhər pik saatı» (açar tixac-seher-<gün>): 07:00–08:45 ölçüləri, 08:45-dən 10:00-dək dərc olunur (şəhərə doğru).
- «Axşam pik saatı» (açar tixac-axsam-<gün>): 17:00–18:45 ölçüləri, 18:45-dən 20:00-dək (şəhərdən çıxış).
Hər bülletendə: başlıq (neçə küçədə tıxac olub, ən uzunu harada — 35 marşrutun ölçüsü), giriş, rayonlar üzrə tıxac balı,
ən uzun tıxaclar, səkkiz əsas yolun vəziyyəti (indi və pik ərzində ən pis), marşrutlarda gediş vaxtı
(indi, adi halda, pik ərzində ən uzun və saatı), tıxacın təxminən neçə dəqiqə sürdüyü, yol hadisələri, dünənin eyni saatları ilə
müqayisə və canlı səhifəyə keçid.
Dərc olunmur (worth=False): pəncərənin sonunadək ölçü azdır və ya təzə deyil; həftə sonu heç bir tıxac yoxdur (boş xəbər olmasın).
Sorğu: pəncərə ərzində tarix.json-a bir sorğu (dərc olunanda açar done-a düşür); ölçü hələ gəlməyibsə növbəti dövrədə yenə.
Sınaq: python oz_tixac.py --sinaq [--now 2026-11-16T08:50+04:00]
"""
import datetime
import json
import sys
import time

import oz_xeber as ox

BAKU = ox.BAKU
TARIX_URL = "https://raw.githubusercontent.com/8ulduz/8ulduz/tixac/tarix.json"
PAGE = "https://8ulduz.az/#/tixac"
CREDIT = "8ulduz.az avtomatik ölçüsü (Mapbox tıxac məlumatı)"
TITLE_MAX = 110
MIN_SNAPS = 6                       # pəncərədə bundan az ölçü varsa bülleten yazılmır
FRESH = datetime.timedelta(minutes=25)
STEP_MAX = datetime.timedelta(minutes=12)   # tıxacın müddəti: ardıcıl ölçülər arası, ən çoxu bu qədər

BULLETINS = (
    {"id": "seher", "ad": "Səhər", "start": "07:00", "slot": "08:45", "end": "10:00", "dir": "şəhərə doğru"},
    {"id": "axsam", "ad": "Axşam", "start": "17:00", "slot": "18:45", "end": "20:00", "dir": "şəhərdən çıxış"},
)
ROUTE_AD = {
    "seher": {"simal": "Bakı–Sumqayıt yolundan Tbilisi prospektinə", "qerb": "Binəqədidən Moskva prospekti ilə Ziya Bünyadov prospektinə",
              "aeroport": "Aeroport yolundan Heydər Əliyev prospekti ilə Gəncliyə", "cenub": "Zığ şossesindən Babək prospekti ilə Neftçilər prospektinə"},
    "axsam": {"simal": "Tbilisi prospektindən Bakı–Sumqayıt yoluna", "qerb": "Ziya Bünyadov prospektindən Moskva prospekti ilə Binəqədiyə",
              "aeroport": "Gənclikdən Heydər Əliyev prospekti ilə aeroport yoluna", "cenub": "Neftçilər prospektindən Babək prospekti ilə Zığ şossesinə"},
}
LEVEL = {"sixtixac": "sıx tıxac", "tixac": "tıxac", "leng": "hərəkət ləngdir", "serbest": "hərəkət sərbəstdir", "?": "ölçülməyib"}
RANK = {"?": -1, "serbest": 0, "leng": 1, "tixac": 2, "sixtixac": 3}
BAD = ("tixac", "sixtixac")


def _now(now):
    if now is None:
        return datetime.datetime.now(BAKU)
    return now.astimezone(BAKU) if now.tzinfo else now.replace(tzinfo=BAKU)


def _at(day, hm):
    h, m = map(int, hm.split(":"))
    return datetime.datetime.combine(day, datetime.time(h, m), BAKU)


def _t(ms):
    return datetime.datetime.fromtimestamp(ms / 1000, BAKU)


def _km(text):
    try:
        return float(str(text).replace(",", "."))
    except ValueError:
        return 0.0


def _kmt(x):
    return f"{x:.1f}".replace(".", ",")


def _min(n):
    return f"{n} dəq"


def _window(snaps, start, end):
    return [s for s in snaps if isinstance(s, dict) and isinstance(s.get("t"), (int, float)) and start <= _t(s["t"]) <= end]


def _durations(snaps):
    """Hər ölçünün «payı» dəqiqə ilə: sonrakı ölçüyədək olan vaxt (ən çoxu STEP_MAX), sonuncu üçün əvvəlkilərin ortası."""
    out = []
    for i, s in enumerate(snaps):
        if i + 1 < len(snaps):
            gap = _t(snaps[i + 1]["t"]) - _t(s["t"])
        else:
            gap = (_t(s["t"]) - _t(snaps[0]["t"])) / max(1, len(snaps) - 1) if len(snaps) > 1 else datetime.timedelta(minutes=6)
        out.append(min(gap, STEP_MAX).total_seconds() / 60)
    return out


def summarize(snaps):
    """Pəncərənin ölçülərindən: yollar (indi, ən pis, tıxac dəqiqəsi, ən uzun tıxac km), marşrutlar və hadisələr."""
    mins = _durations(snaps)
    roads, routes, incidents = {}, {}, []
    streets, rayons = {}, {}
    for s, dur in zip(snaps, mins):
        # bütün şəhər (35 marşrut, 2026-11-14): tıxaclı küçələr (istiqamətdən asılı olmayaraq bir dəfə) və rayon balı
        seen = set()
        for row in s.get("s") or []:
            if len(row) < 4 or row[2] not in BAD:
                continue
            st = streets.setdefault(row[0], {"name": row[0], "jam_min": 0.0, "max_km": 0.0, "worst": "tixac"})
            st["max_km"] = max(st["max_km"], _km(row[3]))
            if RANK[row[2]] > RANK[st["worst"]]:
                st["worst"] = row[2]
            if row[0] not in seen:
                seen.add(row[0])
                st["jam_min"] += dur
        for row in s.get("z") or []:
            z = rayons.setdefault(row[0], [0, 0])
            z[0] += row[1]
            z[1] += 1
        for row in s.get("w") or []:
            name, level, km = row[0], row[1], _km(row[2])
            r = roads.setdefault(name, {"name": name, "worst": "?", "jam_min": 0.0, "max_km": 0.0, "now": "?", "now_km": 0.0})
            if RANK.get(level, -1) > RANK[r["worst"]]:
                r["worst"] = level
            if level in BAD:
                r["jam_min"] += dur
                r["max_km"] = max(r["max_km"], km)
        for rid, m, typ in s.get("r") or []:
            r = routes.setdefault(rid, {"id": rid, "max": 0, "max_at": None, "sum": 0, "n": 0, "typ": typ})
            if m > r["max"]:
                r["max"], r["max_at"] = m, _t(s["t"])
            r["sum"] += m
            r["n"] += 1
        for text in s.get("i") or []:
            if text not in incidents:
                incidents.append(text)
    last = snaps[-1]
    for row in last.get("w") or []:
        if row[0] in roads:
            roads[row[0]]["now"], roads[row[0]]["now_km"] = row[1], _km(row[2])
    for rid, m, typ in last.get("r") or []:
        if rid in routes:
            routes[rid]["now"], routes[rid]["typ"] = m, typ
    return roads, routes, incidents, streets, rayons


def _avg_extra(routes):
    vals = [r["sum"] / r["n"] - r["typ"] for r in routes.values() if r["n"]]
    return sum(vals) / len(vals) if vals else None


def bulletin(b, day, snaps, now):
    """Bir bülleten (xəbər lüğəti) və ya None (ölçü azdır)."""
    start, slot = _at(day, b["start"]), _at(day, b["slot"])
    win = _window(snaps, start, now)
    if len(win) < MIN_SNAPS or now - _t(win[-1]["t"]) > FRESH:
        return None
    roads, routes, incidents, streets, rayons = summarize(win)
    city = sorted(streets.values(), key=lambda r: (-r["jam_min"], -r["max_km"]))
    measured = max([(s.get("n") or [0])[0] for s in win] or [0])
    order = [n for n in (win[-1].get("w") or [])]
    jams = sorted((r for r in roads.values() if r["jam_min"] > 0), key=lambda r: (-RANK[r["worst"]], -r["jam_min"], -r["max_km"]))
    key = f"tixac-{b['id']}-{day.isoformat()}"
    weekend = day.weekday() >= 5
    ad = b["ad"]
    if city and measured:
        top = city[0]
        title = f"{ad} pik saatı: Bakıda {len(city)} küçədə tıxac olub, ən uzunu {top['name']}"
        lead = (f"8ulduz.az-ın avtomatik ölçüsünə görə bu gün saat {b['start']}–{slot:%H:%M} arası {b['dir']} hərəkətdə ölçülən "
                f"{measured} küçədən {len(city)} küçədə tıxac olub. Ən uzun tıxac {top['name']} üzərindədir: "
                f"{_kmt(top['max_km'])} km, təxminən {round(top['jam_min'])} dəqiqə.")
        if len(title) > TITLE_MAX:
            title = f"{ad} pik saatı: Bakıda {len(city)} küçədə tıxac olub"
    elif jams:
        top = jams[0]
        title = f"{ad} pik saatı: Bakıda {len(jams)} əsas yolda tıxac, ən sıxı {top['name']}" if len(jams) > 1 else \
            f"{ad} pik saatı: Bakıda {top['name']} tıxacdadır"
        lead = (f"8ulduz.az-ın avtomatik ölçüsünə görə bu gün saat {b['start']}–{slot:%H:%M} arası {b['dir']} hərəkətdə ən uzun tıxac "
                f"{top['name']} üzərində olub: {_kmt(top['max_km'])} km, təxminən {round(top['jam_min'])} dəqiqə.")
    else:
        title = f"{ad} pik saatı: Bakının səkkiz əsas yolunda ciddi tıxac yoxdur"
        lead = (f"8ulduz.az-ın avtomatik ölçüsünə görə bu gün saat {b['start']}–{slot:%H:%M} arası {b['dir']} hərəkətdə ölçülən səkkiz "
                f"əsas yolun heç birində ciddi tıxac olmayıb.")
    body = []
    lines = []
    for name, *_ in order:
        r = roads.get(name)
        if not r:
            continue
        line = f"{name}: indi {LEVEL.get(r['now'], 'ölçülməyib')}"
        if r["now"] in BAD and r["now_km"]:
            line += f" ({_kmt(r['now_km'])} km)"
        if r["jam_min"] > 0 and (r["worst"] != r["now"] or r["now"] not in BAD):
            line += f"; pik ərzində {LEVEL[r['worst']]}, təxminən {round(r['jam_min'])} dəq"
        elif r["jam_min"] > 0:
            line += f"; tıxac təxminən {round(r['jam_min'])} dəq davam edir"
        lines.append(line + ".")
    if lines:
        body.append("Səkkiz əsas yolun vəziyyəti (" + b["dir"] + "):")
        body += lines
    if rayons:
        avg = sorted(((n, round(v[0] / v[1])) for n, v in rayons.items() if v[1]), key=lambda x: (-x[1], x[0]))
        body.append("Rayonlar üzrə tıxac balı (pik ərzində orta, 0–10): " + ", ".join(f"{n} {v}" for n, v in avg) + ".")
    if len(city) > 1:
        body.append("Ən uzun tıxaclar:")
        body += [f"{r['name']}: {_kmt(r['max_km'])} km, təxminən {round(r['jam_min'])} dəq." for r in city[:6]]
    names = ROUTE_AD[b["id"]]
    times = []
    for rid, r in routes.items():
        if rid not in names or not r.get("now"):
            continue
        t = f"{names[rid][0].upper()}{names[rid][1:]}: indi {_min(r['now'])}, adi halda {_min(r['typ'])}"
        if r["max"] > r["now"] and r["max_at"]:
            t += f"; ən uzunu {_min(r['max'])} (saat {r['max_at']:%H:%M})"
        times.append(t + ".")
    if times:
        body.append("Marşrutlarda gediş vaxtı:")
        body += times
    if incidents:
        body.append("Pik ərzində qeydə alınan yol hadisələri: " + " ".join(incidents[:5]))
    y = _window(snaps, start - datetime.timedelta(days=1), slot - datetime.timedelta(days=1))
    if len(y) >= MIN_SNAPS:
        y_routes = summarize(y)[1]
        a, b2 = _avg_extra(routes), _avg_extra(y_routes)
        if a is not None and b2 is not None:
            diff = round(a - b2)
            body.append("Dünənin eyni saatları ilə müqayisədə marşrutlar orta hesabla " +
                        (f"{abs(diff)} dəqiqə {'çox' if diff > 0 else 'az'} vaxt aparıb." if diff else "eyni vaxt aparıb."))
    body.append("Canlı vəziyyət 8ulduz.az-ın «Tıxac» bölməsində pik saatlarda 6 dəqiqədən bir yenilənir.")
    body.append("Ölçü Mapbox-un tıxac məlumatı əsasında avtomatik aparılır, rəsmi məlumat deyil.")
    item = {"kind": f"tixac-{b['id']}", "key": key, "title": title, "lead": lead, "body": body, "credit": CREDIT, "link": PAGE,
            "topic": "yol", "slot": b["slot"], "worth": True, "list": False}
    if weekend and not jams and len(city) < 5:
        item.update(worth=False, why="həftə sonu, tıxac yoxdur")
    elif len(title) > TITLE_MAX:
        item.update(worth=False, why=f"başlıq {TITLE_MAX} hərfdən uzundur")
    else:
        try:
            if ox.needs_owner("\n".join([title, lead, *body])):
                item.update(worth=False, why="rəhbərliyin adı keçir: avtomatik dərc olunmur")
        except Exception:
            pass
    return item


def _snaps(fetch, now):
    raw = fetch(f"{TARIX_URL}?t={int(now.timestamp()) // 120}")
    doc = json.loads(raw.decode("utf-8") if isinstance(raw, (bytes, bytearray)) else raw)
    snaps = [s for s in doc.get("snaps") or [] if isinstance(s, dict) and isinstance(s.get("t"), (int, float))]
    return sorted(snaps, key=lambda s: s["t"])


def items(root, now, fetch=None, done=None):
    """Açıq pəncərənin bülleteni. Pəncərə xaricində sorğu getmir. Heç vaxt xəta qaldırmır."""
    try:
        now = _now(now)
        done = set(done or ())
        day = now.date()
        open_ = [b for b in BULLETINS if _at(day, b["slot"]) <= now < _at(day, b["end"])
                 and f"tixac-{b['id']}-{day.isoformat()}" not in done]
        if not open_:
            return []
        if fetch is None:
            fetch = ox._u().fetch
        snaps = _snaps(fetch, now)
        out = []
        for b in open_:
            item = bulletin(b, day, snaps, now)
            if item is None and now >= _at(day, b["end"]) - datetime.timedelta(minutes=10):
                item = {"kind": f"tixac-{b['id']}", "key": f"tixac-{b['id']}-{day.isoformat()}", "topic": "yol", "slot": b["slot"],
                        "worth": False, "why": "ölçü azdır və ya təzə deyil"}
            if item:
                out.append(item)
        return out
    except Exception:
        return []


if __name__ == "__main__":
    if "--sinaq" in sys.argv:
        at = sys.argv[sys.argv.index("--now") + 1] if "--now" in sys.argv else None
        base = datetime.datetime.fromisoformat(at) if at else datetime.datetime.now(BAKU)
        try:
            snaps = _snaps(ox._u().fetch, base)
        except Exception as e:
            print(f"> tarix.json alınmadı: {type(e).__name__}")
            sys.exit(0)
        print(f"## Tıxac bülletenləri ({len(snaps)} ölçü)\n")
        for b in BULLETINS:
            when = base if at else _at(base.date(), b["slot"])
            item = bulletin(b, when.date(), snaps, when)
            if not item:
                print(f"> {b['ad']}: ölçü azdır\n")
                continue
            print("\n".join(ox.render(item)))
            print("✅ Dərc olunardı\n" if item["worth"] else f"⏭ Dərc olunmazdı: {item['why']}\n")
