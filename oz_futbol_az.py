"""8ulduz-un öz futbol xəbərləri: Azərbaycan futbolu (faza 1, şablon, süni intellektsiz). Sahib, 2026-11-10: «Bəli, başla».

Mənbə saytın artıq topladığı data/futbol/*.json-dur, hər rəqəm və ad oradandır:
- Premyer Liqa, I Liqa, II Liqa, Azərbaycan Kuboku: pfl.az (premyer-liqa.json, i-liqa.json, ii-liqa.json, kubok.json;
  qarşılıqlı oyunlar üçün keçən mövsümlər: premyer-liqa-2025.json, premyer-liqa-2024.json).
- Azərbaycan millisi: Vikipediya (data/milli-menyu.json-da Azərbaycanın olduğu yarışlar, məsələn ml-d.json).
- Avrokubokda Premyer Liqa klubu («Sabah»): OpenLigaDB (cl.json; al.json, kl.json).

Xəbərlər (bu moduldan gündə ən çox 5):
1. Premyer Liqanın tur icmalı: turun əsas günlərinin bütün oyunları oynanandan sonra, son oyunun başlamasından 2 saat
   15 dəqiqə sonra (gecə yarısından sonraya düşürsə, səhər 09:00-da). Sonraya salınmış oyun turu saxlamır, qeyd olunur.
2. Premyer Liqanın növbəti turuna baxış: turdan bir gün əvvəl 12:00-da, yalnız bütün oyunların saatı bəllidirsə (00:00 deyil).
3. Bombardirlər: turdan sonrakı gün 10:00-da. pfl.az-dan /bombarders/list (fetch parametri ilə; mövsümün liqa nömrəsi üçün
   /seasons). Siyahı 20 sətirdən uzundursa (səhifəlidir), bütün siyahını verən /bombarders. Qola görə azalan, bərabərdə
   Azərbaycan əlifbası ilə ada görə. data/football.json-dakı «scorers» səhvdir (pfl.az mətn kimi artan sıra verir): baxılmır.
4. I və II Liqanın qısa tur icmalı.
5. Azərbaycan Kuboku: mərhələ bitəndə nəticələr, növbəti mərhələnin cütləri bəlli olanda cütlər (yer tutucu tarix yazılmır).
6. Azərbaycan millisi: oyundan bir gün əvvəl və nəticə (qrupdakı yeri ilə).
7. Avrokubokda Azərbaycan klubu: oyundan bir gün əvvəl və nəticə (cədvəldəki yeri ilə).
Oyun-oyun hesabat oz_xeber.pfl_item-dədir: burada təkrarlanmır.

Sayta qoşulmayıb: updater.py və pipeline bu faylı çağırmır. Nümunələr: `python oz_futbol_az.py --sinaq --root DIR`.
items() hər çağırışda ~10 JSON faylı oxuyur: pipeline-da hər dövrədə yox, futbol dövrəsində (10 dəqiqədən bir) çağırılmalıdır.
"""
import datetime
import functools
import json
import pathlib
import re
import sys

import oz_xeber as ox

BAKU = ox.BAKU
CREDIT_PFL = "Peşəkar Futbol Liqası"
LINK_PFL = "https://pfl.az/"
DAY_CAP = 5             # bu moduldan gündə ən çox xəbər
CORE_DAYS = 6           # turun əsas günləri: tarixə görə ortadakı oyundan ±6 gün; ondan sonrakı oyun sonraya salınıb
TITLE_MAX = 110
PAST_PL = ("premyer-liqa-2024", "premyer-liqa-2025")  # qarşılıqlı oyunlar üçün, köhnədən yeniyə
EURO = ("cl", "al", "kl")
DAY = datetime.timedelta(days=1)
HOUR = datetime.timedelta(hours=1)

# Eyni gündə hədd aşılarsa vacib olan qalır (kiçik rəqəm = vacib).
PRIO = {"pfl-tur": 1, "avro-netice": 2, "milli-netice": 3, "pfl-tur-oncesi": 4, "milli-oncesi": 5, "avro-oncesi": 6,
        "kubok-merhele": 7, "kubok-cutler": 8, "pfl-bombardir": 9, "liqa-tur": 10}

# --- Yazı: şəkilçi, ad, tarix ------------------------------------------------------------------------------

# Şəkilçi yazıya yox, oxunuşa görə seçilir. Qısaltma və yazıldığı kimi oxunmayan xarici adlar.
SAY = {
    "Qaradağ L.": "Qaradağ Lökbatan",
    "Slavia Prague": "Slavia Praq", "Manchester City": "Mançester Siti", "Lille": "Lil", "Lens": "Lans", "Nice": "Nis",
    "Paris Saint-Germain": "Pari Sen-Jermen", "Sporting CP": "Sportinq Si-Pi", "Marseille": "Marsel",
}
_TWO = {"dat": ("y", "a", "ə"), "ins": ("y", "la", "lə"), "loc": ("", "da", "də"), "abl": ("", "dan", "dən")}
_FOUR = {"acc": ("n", ("ı", "i", "u", "ü")), "gen": ("n", ("ın", "in", "un", "ün"))}
# Mənsubiyyət şəkilçili son söz (Çempionlar Liqası, Ağstafa Gəncləri): yönlük, yerlik, çıxışlıqda «n» gəlir — Liqasında.
_POSS = ("liqası", "kuboku", "çempionatı", "stadionu", "mərhələsi", "finalı", "yarımfinalı")
_AZ_ABC = "abcçdeəfgğhxıijkqlmnoöprsştuüvyz"
_PLACE = ("birinci", "ikinci", "üçüncü", "dördüncü", "beşinci", "altıncı", "yeddinci", "səkkizinci", "doqquzuncu", "onuncu")
_ASCII = str.maketrans("əıöüşçğ", "eiouscg")


def sx(name, case, quote=True):
    """Hal şəkilçisi: acc «Zirə»ni, gen «Neftçi»nin, dat «Sabah»a, ins «Şamaxı»yla, loc «Rheinpark Stadion»da,
    abl «Kəpəz»dən. quote=False: «Litvanı», «Lixtenşteynə», «Premyer Liqada»."""
    said = SAY.get(name, name)
    if case in _FOUR:
        buf, forms = _FOUR[case]
        end = ox._four(said, forms)
    else:
        buf, back, front = _TWO[case]
        end = back if ox._last_vowel(said) in "aıou" else front
        words = ox._low(said).split()
        if case != "ins" and len(words) > 1 and (words[-1] in _POSS or words[-1].endswith(("ları", "ləri"))):
            buf = "n"
    return (f"«{name}»" if quote else name) + (buf if ox._vowel_end(said) else "") + end


def _q(name):
    return f"«{name}»"


def _and(parts):
    parts = list(parts)
    return parts[0] if len(parts) == 1 else ", ".join(parts[:-1]) + " və " + parts[-1]


def _place(n):
    """Yer sözlə: 1 -> «birinci»; 11-dən sonra rəqəmlə."""
    return _PLACE[n - 1] if 1 <= n <= len(_PLACE) else ox.ordinal(n)


def _az_key(s):
    """Azərbaycan əlifbası sırası (updater-in bombardir düzümü ilə eyni)."""
    s = str(s or "").replace("I", "ı").replace("İ", "i").lower()
    return [(_AZ_ABC.index(c) if c in _AZ_ABC else (len(_AZ_ABC) if c.isalnum() else -1), c) for c in s]


def _slug(s):
    return re.sub(r"[^a-z0-9]+", "-", ox._low(s).translate(_ASCII)).strip("-")


def _baku(d):
    return (d if d.tzinfo else d.replace(tzinfo=BAKU)).astimezone(BAKU)


def _when(s):
    try:
        return _baku(datetime.datetime.fromisoformat(str(s)))
    except ValueError:
        return None


def _at(day, hour, minute=0):
    return datetime.datetime(day.year, day.month, day.day, hour, minute, tzinfo=BAKU)


def _ready_after(kick, morning=9):
    """Oyundan sonra dərc vaxtı: başlama + 2 saat 15 dəqiqə (pfl.az nəticəni bitdikdən ~15 dəqiqə sonra yazır).
    Gecə 00:30-dan sonraya düşürsə, səhər saat «morning»-da."""
    t = kick + datetime.timedelta(minutes=135)
    if datetime.time(0, 30) < t.time() < datetime.time(morning):
        return _at(t.date(), morning)
    return t


def _span(a, b):
    """«6–8 noyabr», «30 oktyabr – 2 noyabr», «6 noyabr»."""
    if a.date() == b.date():
        return ox.day_text(a)
    if (a.year, a.month) == (b.year, b.month):
        return f"{a.day}–{ox.day_text(b)}"
    return f"{ox.day_text(a)} – {ox.day_text(b)}"


def _span_loc(a, b):
    return _span(a, b) + ("də" if b.month == 4 else "da")


def _stamp(d):
    return f"{ox.day_text(d)} {d.year}, {d:%H:%M}"


# pfl.az stadion adlarını qısaldır: tam yazılış. Baş hərflərlə yazılan şəxs adı (H.Ə., Y.M.) açılmır.
VENUES = {
    "Bank Respublika A.": "Bank Respublika Arena",
    "M.H. Sumqayıt ş. st.": "Mehdi Hüseynzadə adına Sumqayıt şəhər stadionu",
    "T.B. - Respublika st.": "Tofiq Bəhramov adına Respublika stadionu",
    "Kapital B.A. (e.m)": "Kapital Bank Arena (ehtiyat meydança)",
    "Palms Sports FM (IV m.)": "Palms Sports FM (IV meydança)",
    "Gəncə şəhər st. (e.m.)": "Gəncə şəhər stadionu (ehtiyat meydança)",
    "H.Ə. adına İmişli ş. st.": "İmişli şəhər stadionu",
    "Y.M. Mingəçevir ş. st.": "Mingəçevir şəhər stadionu",
    "Y.M. Mingəçevir ş. st. (e.m.)": "Mingəçevir şəhər stadionu (ehtiyat meydança)",
}
# Millinin oyunlarında stadion ingiliscədir (Vikipediya): Azərbaycandakılar Azərbaycan dilində.
NAT_VENUES = {"Tofiq Bahramov Republican Stadium": "Tofiq Bəhramov adına Respublika stadionu",
              "Baku Olympic Stadium": "Bakı Olimpiya Stadionu", "Dalga Arena": "Dalğa Arena", "Neftchi Arena": "Neftçi Arena"}


def venue(name):
    """«Tovuz şəhər st.» -> «Tovuz şəhər stadionu», «M.H. Sumqayıt ş. st.» -> «Mehdi Hüseynzadə adına ...»."""
    name = " ".join(str(name or "").split())
    if name in VENUES:
        return VENUES[name]
    name = re.sub(r" ş\. st\.$", " şəhər stadionu", name)
    return re.sub(r" st\.$", " stadionu", name)


def _venue_loc(name):
    """«Yevlax şəhər stadionunda», «Azersun Arenada»; başqa cür bitən ad üçün boş (cümlədə yazılmır)."""
    low = ox._low(name)
    if low.endswith("stadionu"):
        return name + "nda"
    if low.endswith("arena"):
        return name + "da"
    return ""


def _at_venue(g):
    where = _venue_loc(venue(g["stadium"]))
    return f" {where}" if where else ""


def _nat_loc(name):
    if not name:
        return ""
    if name in NAT_VENUES:
        return _venue_loc(NAT_VENUES[name])
    if ox._low(name).endswith(("stadionu", "arena")):
        return _venue_loc(name)
    return sx(name, "loc")


# --- Məlumat ------------------------------------------------------------------------------------------------

def _read(root, name, folder="futbol"):
    base = pathlib.Path(root) / "data"
    path = (base / folder if folder else base) / f"{name}.json"
    try:
        doc = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    return doc if isinstance(doc, dict) else None


def _games(doc):
    """Oyunlar vaxt sırası ilə, Bakı vaxtı. tbc: saat 00:00 yer tutucusudur (pfl.az uzaq turlara belə yazır)."""
    out = []
    for g in (doc or {}).get("games") or []:
        if not isinstance(g, dict):
            continue
        when = _when(g.get("date"))
        if when is None or not g.get("home") or not g.get("away"):
            continue
        hs, as_ = g.get("hs"), g.get("as")
        played = bool(g.get("played")) and isinstance(hs, int) and isinstance(as_, int)
        out.append({"home": str(g["home"]), "away": str(g["away"]), "hs": hs if played else None,
                    "as": as_ if played else None, "when": when, "played": played, "tbc": "T00:00" in str(g.get("date")),
                    "stadium": str(g.get("stadium") or ""), "round": str(g.get("round") or "")})
    out.sort(key=lambda x: x["when"])
    return out


def _rows(group):
    rows = group.get("rows") if isinstance(group, dict) else None
    return {str(r["team"]): r for r in rows or [] if isinstance(r, dict) and r.get("team")}


def _league(root, lid):
    """Liqa faylı: ad, komandalar, oyunlar və rəsmi cədvəl (groups[0].rows)."""
    doc = _read(root, lid)
    if not doc:
        return None
    teams = doc.get("teams") if isinstance(doc.get("teams"), dict) else {}
    names = {str(k): str(v.get("name") or k) if isinstance(v, dict) else str(k) for k, v in teams.items()}
    known = set(names)
    games = _games(doc)
    for g in games:
        for k in (g["home"], g["away"]):
            names.setdefault(k, k)
    groups = doc.get("groups") if isinstance(doc.get("groups"), list) else []
    return {"id": lid, "name": str(doc.get("name") or lid), "short": str(doc.get("short") or doc.get("name") or lid),
            "season": str(doc.get("season") or ""), "key": str(doc.get("key") or ""), "names": names, "known": known,
            "games": games, "official": _rows(groups[0]) if groups else {}, "groups": groups, "doc": doc}


def _nm(L, k):
    return L["names"].get(k, k)


def _credit(D):
    return str(D["doc"].get("source") or "").split(" (")[0] or CREDIT_PFL


def _link(D):
    return str(D["doc"].get("source_url") or D["doc"].get("url") or LINK_PFL)


# --- Cədvəl -------------------------------------------------------------------------------------------------

def _zero():
    return {"p": 0, "w": 0, "d": 0, "l": 0, "gf": 0, "ga": 0, "pts": 0}


def _table(games, teams=()):
    """Bitmiş oyunlardan cədvəl: {komanda: {p, w, d, l, gf, ga, pts}}."""
    t = {k: _zero() for k in teams}
    for g in games:
        if not g["played"]:
            continue
        for k, gf, ga in ((g["home"], g["hs"], g["as"]), (g["away"], g["as"], g["hs"])):
            r = t.setdefault(k, _zero())
            r["p"] += 1
            r["gf"] += gf
            r["ga"] += ga
            if gf > ga:
                r["w"] += 1
                r["pts"] += 3
            elif gf == ga:
                r["d"] += 1
                r["pts"] += 1
            else:
                r["l"] += 1
    return t


def _rank_key(r):
    return (r["pts"], r["gf"] - r["ga"], r["gf"])


def _order(table, names):
    """Sıra: xal, qol fərqi, vurulan qol (pfl.az cədvəli belə düzür), sonra ad."""
    return sorted(table, key=lambda k: (tuple(-x for x in _rank_key(table[k])), _az_key(names.get(k, k))))


def _pos(table):
    """Yer: xalı, qol fərqi və qolu ondan tam üstün olanların sayı + 1. Hamısı bərabər olanlar yeri bölüşür (shared)."""
    keys = {k: _rank_key(r) for k, r in table.items()}
    pos = {k: 1 + sum(1 for v in keys.values() if v > keys[k]) for k in keys}
    shared = {k for k in keys if sum(1 for v in keys.values() if v == keys[k]) > 1}
    return pos, shared


def _bad_rows(official, table):
    """Rəsmi cədvəldə oyun sayı və ya xalı oyunlardan hesablanana uyğun gəlməyən komandalar."""
    bad = [k for k, r in official.items()
           if (table.get(k) or _zero())["p"] != int(r.get("p") or 0) or (table.get(k) or _zero())["pts"] != int(r.get("pts") or 0)]
    return bad + [k for k, r in table.items() if r["p"] and k not in official]


def _table_ok(official, table):
    return bool(official) and not _bad_rows(official, table)


def _positions(L):
    """Hazırkı yerlər: rəsmi cədvəl oyunlarla uyğundursa ondan, deyilsə hesablanmış. Heç oyun yoxdursa, yer yoxdur."""
    played = [g for g in L["games"] if g["played"]]
    table = _table(played, L["names"])
    if not played:
        return table, {}, set(table)
    if _table_ok(L["official"], table):
        pos = {k: int(r.get("pos") or 0) for k, r in L["official"].items()}
        return table, pos, {k for k, v in pos.items() if not v}
    pos, shared = _pos(table)
    return table, pos, shared


def _pl_pos(L):
    table, pos, shared = _positions(L)
    return {k: v for k, v in pos.items() if v and k not in shared}


# --- Mətn parçaları ------------------------------------------------------------------------------------------

def _pair(g, nm):
    return f"«{nm(g['home'])}» – «{nm(g['away'])}»"


def _score(g, nm):
    return f"«{nm(g['home'])}» – «{nm(g['away'])}» – {g['hs']}:{g['as']}"


def _win(g, nm):
    """Oyunun nəticəsi başlıq üçün: «Neftçi» «Kəpəz»i 1:0 hesabı ilə məğlub edib."""
    h, a, hs, as_ = nm(g["home"]), nm(g["away"]), g["hs"], g["as"]
    if hs > as_:
        return f"«{h}» {sx(a, 'acc')} {hs}:{as_} hesabı ilə məğlub edib"
    if as_ > hs:
        return f"«{a}» səfərdə {sx(h, 'acc')} {as_}:{hs} hesabı ilə məğlub edib"
    return f"«{h}» ilə «{a}» {hs}:{as_} hesabı ilə heç-heçə edib" if hs else f"«{h}» ilə «{a}» qolsuz heç-heçə edib"


def _result_of(team, g, nm):
    """Komandanın nəticəsi: «Kəpəz»i 1:0 hesabı ilə məğlub edib / səfərdə «X»ə 0:1 hesabı ilə uduzub."""
    home = g["home"] == team
    opp = nm(g["away"] if home else g["home"])
    gf, ga = (g["hs"], g["as"]) if home else (g["as"], g["hs"])
    where = "" if home else "səfərdə "
    if gf > ga:
        return f"{where}{sx(opp, 'acc')} {gf}:{ga} hesabı ilə məğlub edib"
    if gf < ga:
        return f"{where}{sx(opp, 'dat')} {gf}:{ga} hesabı ilə uduzub"
    if gf:
        return f"{where}{sx(opp, 'ins')} {gf}:{ga} hesabı ilə heç-heçə edib"
    return f"{where}{sx(opp, 'ins')} qolsuz heç-heçə edib"


def _pending(gs, nm, since):
    """Oynanmamış oyunlar: tarixi bəllidirsə «... 17 dekabrda keçiriləcək», deyilsə «... hələ keçirilməyib»."""
    word = "oyunu" if len(gs) == 1 else "oyunları"
    pairs = _and([_pair(g, nm) for g in gs])
    if len({g["when"].date() for g in gs}) == 1 and all(g["when"] > since and not g["tbc"] for g in gs):
        return f"{pairs} {word} {ox.day_loc(gs[0]['when'])} keçiriləcək"
    return f"{pairs} {word} hələ keçirilməyib"


# --- Hadisələr: hər xəbərin dərc pəncərəsi ------------------------------------------------------------------

def _ev(kind, key, ready, expires, make, fetch=False, fam=None):
    return {"kind": kind, "key": key, "ready": ready, "expires": expires, "prio": PRIO[kind], "make": make,
            "fetch": fetch, "fam": fam or kind}


def _rounds(games):
    """Rəqəmli turlar sıra ilə: [(tur, oyunlar)]. «p/o» (keçid oyunu) tur sayılmır."""
    out = {}
    for g in games:
        if g["round"].isdigit():
            out.setdefault(g["round"], []).append(g)
    return [(r, out[r]) for r in sorted(out, key=int)]


def _split(games):
    """Turun əsas günləri (tarixə görə ortadakı oyundan ±6 gün), ondan xeyli əvvəl oynanmışlar və sonraya qalanlar."""
    mid = sorted(g["when"] for g in games)[(len(games) - 1) // 2]
    span = datetime.timedelta(days=CORE_DAYS)
    main, early, later = [], [], []
    for g in games:
        d = g["when"] - mid
        if abs(d) <= span:
            main.append(g)
        elif d < -span and g["played"]:
            early.append(g)
        else:
            later.append(g)
    return main, early, later


def _league_events(L, past=None):
    """Tur icmalı (hər liqa), Premyer Liqada həm də tura baxış və bombardirlər. past: qarşılıqlı oyunlar üçün mövsümlər."""
    pl = past is not None
    kind = "pfl-tur" if pl else "liqa-tur"
    evs = []
    for rnd, games in _rounds(L["games"]):
        main, early, later = _split(games)
        first, last = min(g["when"] for g in main), max(g["when"] for g in main)
        tag = f"{L['id']}-{L['key']}-t{rnd}"
        ready = _ready_after(last, 9)
        evs.append(_ev(kind, f"tur-{tag}", ready, ready + 36 * HOUR,
                       functools.partial(_summary, L, rnd, main, early, later, not pl),
                       fam=kind if pl else f"{kind}:{L['id']}"))
        if pl:
            evs.append(_ev("pfl-tur-oncesi", f"tur-oncesi-{tag}", _at((first - DAY).date(), 12), first,
                           functools.partial(_preview, L, past, rnd, main)))
            sc = _at((last + DAY).date(), 10)
            evs.append(_ev("pfl-bombardir", f"bombardir-{tag}", sc, sc + 24 * HOUR,
                           functools.partial(_scorers, L, rnd, main), fetch=True))
    return evs


# --- 1, 4. Tur icmalı ----------------------------------------------------------------------------------------

def _moves(after, before, nm):
    """Ən çox yer dəyişənlər (qalxan və düşən, ən çoxu ikişər). Yeri bölüşülən komanda sayılmır."""
    pa, sa = _pos(after)
    pb, sb = _pos(before)
    ok = [k for k in after if k in pb and k not in sa and k not in sb]
    up = sorted((k for k in ok if pb[k] > pa[k]), key=lambda k: (pa[k] - pb[k], pa[k]))[:2]
    down = sorted((k for k in ok if pb[k] < pa[k]), key=lambda k: (pb[k] - pa[k], pa[k]))[:2]

    def move(k):
        return f"«{nm(k)}» {ox.ordinal(pb[k])} yerdən {ox.ordinal(pa[k])} yerə"
    parts = []
    if up:
        parts.append(", ".join(move(k) for k in up) + " qalxıb")
    if down:
        parts.append(", ".join(move(k) for k in down) + " düşüb")
    return f"Cədvəldə {'; '.join(parts)}." if parts else ""


def _in_hand(after, order, nm):
    """Az oyun keçirənlər: «Sabah», «Qarabağ» 10 oyun keçirib, digər komandalar isə 11 oyun."""
    most = max(after[k]["p"] for k in order)
    groups = {}
    for k in order:
        if after[k]["p"] < most:
            groups.setdefault(after[k]["p"], []).append(_q(nm(k)))
    if not groups:
        return ""
    parts = [f"{_and(ks)} {p}" for p, ks in sorted(groups.items())]
    return f"{', '.join(parts)} oyun keçirib, digər komandalar isə {most} oyun."


def _same_order(L, order):
    off = sorted(L["official"], key=lambda k: int(L["official"][k].get("pos") or 99))
    return off == list(order)


def _summary(L, rnd, main, early, later, short, fetch=None):
    """Turun icmalı: bütün nəticələr, qollar, lider və fərq, yer dəyişmələri, az oyun keçirənlər, sonraya qalan oyunlar.
    short: I və II Liqa üçün qısa (yer dəyişmələri və az oyun keçirənlər yazılmır)."""
    nm = functools.partial(_nm, L)
    head = f"{sx(L['short'], 'loc', False)} {ox.ordinal(rnd)} tur"
    games = sorted(main + early, key=lambda g: g["when"])
    played = [g for g in L["games"] if g["played"]]
    missing = [g for g in main if not g["played"]]
    if missing:
        pairs = _and([_pair(g, nm) for g in missing])
        why = f"tur bitməyib: {pairs} {'oyununun' if len(missing) == 1 else 'oyunlarının'} nəticəsi yoxdur"
        now_table = _table(played, L["names"])
        if any(int((L["official"].get(t) or {}).get("p") or 0) > now_table.get(t, _zero())["p"]
               for g in missing for t in (g["home"], g["away"])):
            why += " (rəsmi cədvəl isə bu oyunu sayıb)"
        return {"title": f"{head}: tur bitməyib", "lead": f"Turda {len(main)} oyun var, nəticəsi bəlli olan: {len(main) - len(missing)}.",
                "body": [], "worth": False, "why": why}
    first, last = min(g["when"] for g in main), max(g["when"] for g in main)
    after = _table([g for g in played if g["when"] <= last], L["names"])
    before = _table([g for g in played if g["when"] < first], L["names"])
    current = not any(g["when"] > last for g in played)
    if len(after) < 2:
        return {"title": f"{head}: cədvəl yoxdur", "lead": "Cədvəl qurulmadı.", "body": [], "worth": False, "why": "cədvəl yoxdur"}
    if current and L["official"] and not _table_ok(L["official"], after):
        bad = _and([_q(nm(k)) for k in _bad_rows(L["official"], after)])
        return {"title": f"{head}: cədvəl uyğun gəlmir", "lead": f"Rəsmi cədvəl oyunların nəticələri ilə uyğun gəlmir: {bad}.",
                "body": [], "worth": False, "why": f"rəsmi cədvəl oyunların nəticələri ilə uyğun gəlmir: {bad}"}
    order = _order(after, L["names"])
    had_before = any(r["p"] for r in before.values())
    leader, top = order[0], after[order[0]]["pts"]
    lname = _q(nm(leader))
    tied = [k for k in order if after[k]["pts"] == top]
    rest = [k for k in order if after[k]["pts"] < top]
    second = after[rest[0]]["pts"] if rest else top
    seconds = [k for k in rest if after[k]["pts"] == second]
    gap = top - second
    order_b = _order(before, L["names"]) if had_before else []
    tied_b = [k for k in order_b if before[k]["pts"] == before[order_b[0]]["pts"]] if order_b else []
    others_b = [before[k]["pts"] for k in order_b if k != leader]
    gap_b = before[leader]["pts"] - max(others_b) if order_b and others_b else 0

    if len(tied) > 1:
        phrase = f"{_and([_q(nm(k)) for k in tied])} {top} xalla öndədir" if len(tied) <= 3 else ""
    elif not had_before:
        phrase = f"{lname} {top} xalla liderdir"
    elif leader not in tied_b:
        phrase = f"{lname} liderliyə yüksəlib"
    elif gap > gap_b:
        phrase = f"{lname} fərqi {gap} xala çatdırıb"
    elif gap < gap_b:
        phrase = f"{sx(nm(leader), 'gen')} fərqi {gap} xala enib"
    else:
        phrase = f"{lname} {gap} xal fərqlə liderliyini qoruyub"
    total = sum(g["hs"] + g["as"] for g in games)
    big = max(games, key=lambda g: (abs(g["hs"] - g["as"]), g["hs"] + g["as"]))
    margin = abs(big["hs"] - big["as"])
    win = _win(big, nm) if margin >= 3 else ""
    goals = f"{len(games)} oyunda {total} qol vurulub"
    parts = [p for p in ([win, phrase] if margin >= 5 else [phrase, win or goals]) if p]
    title = f"{head}: {', '.join(parts)}"
    if len(title) > TITLE_MAX:
        title = f"{head}: {parts[0]}"

    lead = f"{sx(L['name'], 'gen', False)} {ox.ordinal(rnd)} turu {_span_loc(first, last)} keçirilib."
    if len(tied) == 1:
        lg = next((g for g in games if leader in (g["home"], g["away"])), None)
        if lg:
            lead += f" Lider {lname} {_result_of(leader, lg, nm)} və {top} xal toplayıb."
        else:
            lead += f" {lname} {top} xalla liderdir."
        if len(seconds) == 1:
            lead += f" {_q(nm(seconds[0]))} {second} xalla ikinci yerdədir."
        elif seconds:
            lead += f" {_and([_q(nm(k)) for k in seconds])} {second} xal toplayıb."
        if had_before and leader not in tied_b:
            lead += f" Turdan əvvəl cədvəlin başında {_and([_q(nm(k)) for k in tied_b])} idi."
        elif had_before and gap != gap_b:
            if gap_b:
                lead += f" Liderin fərqi {gap_b} xaldan {gap} xala {'çatıb' if gap > gap_b else 'enib'}."
            else:
                lead += f" Turdan əvvəl {_and([_q(nm(k)) for k in tied_b])} xal sayında bərabər idi."
    elif len(tied) <= 3:
        lead += f" {_and([_q(nm(k)) for k in tied])} {top} xalla cədvəlin başındadır."
    lead += f" Turun {len(games)} oyununda {total} qol vurulub."

    body = [_score(g, nm) for g in games]
    if not short:
        if had_before and (not current or _same_order(L, order)):
            moves = _moves(after, before, nm)
            if moves:
                body.append(moves)
        hand = _in_hand(after, order, nm)
        if hand:
            body.append(hand)
        prev = [g for g in L["games"] if not g["played"] and g["round"].isdigit() and int(g["round"]) < int(rnd)]
        for r in sorted({g["round"] for g in prev}, key=int):
            body.append(f"{ox.ordinal(r)} turun {_pending([g for g in prev if g['round'] == r], nm, last)}.")
    pend = [g for g in later if not g["played"]]
    if pend:
        body.append(f"Turun {_pending(pend, nm, last)}.")
    return {"title": title, "lead": lead, "body": body, "list": True, "credit": CREDIT_PFL, "link": LINK_PFL}


# --- 2. Növbəti tura baxış -----------------------------------------------------------------------------------

def _h2h(past, a, b):
    """İki komandanın Premyer Liqa oyunları saxlanan mövsümlərdə: say, qələbələr, heç-heçələr, ilk mövsüm, son oyun."""
    rec = {"n": 0, "wa": 0, "wb": 0, "d": 0, "since": "", "last": None}
    for season, games in past or []:
        for g in games:
            if not g["played"] or {g["home"], g["away"]} != {a, b}:
                continue
            ga, gb = (g["hs"], g["as"]) if g["home"] == a else (g["as"], g["hs"])
            rec["n"] += 1
            rec["wa" if ga > gb else "wb" if gb > ga else "d"] += 1
            rec["since"] = rec["since"] or season
            if rec["last"] is None or g["when"] > rec["last"]["when"]:
                rec["last"] = g
    return rec


def _h2h_text(rec, a, b, nm):
    parts = []
    if rec["wa"] and rec["wb"]:
        parts.append(f"«{nm(a)}» {rec['wa']}, «{nm(b)}» {rec['wb']} dəfə qalib gəlib")
    elif rec["wa"] or rec["wb"]:
        k, n = (a, rec["wa"]) if rec["wa"] else (b, rec["wb"])
        parts.append(f"«{nm(k)}» {n} dəfə qalib gəlib")
    if rec["d"]:
        parts.append(f"{rec['d']} oyun heç-heçə bitib")
    return f"Komandalar Premyer Liqada {rec['since']} mövsümündən bəri {rec['n']} dəfə qarşılaşıb: {', '.join(parts)}."


def _tag(k, table, pos, shared):
    if not table.get(k, _zero())["p"]:
        return ""
    if k in shared or not pos.get(k):
        return f" ({table[k]['pts']} xal)"
    return f" ({ox.ordinal(pos[k])} yer, {table[k]['pts']} xal)"


def _preview(L, past, rnd, main, fetch=None):
    """Turdan bir gün əvvəl: oyunlar Bakı vaxtı və stadionla, cədvəldəki yerlər, son qarşılaşma; liderin oyunu öndə."""
    nm = functools.partial(_nm, L)
    head = f"{sx(L['short'], 'loc', False)} {ox.ordinal(rnd)} tur"
    games = [g for g in main if not g["played"]]
    if not games or len(games) < len(main):
        return {"title": f"{head}: tur başlayıb", "lead": "Turun oyunları artıq başlayıb.", "body": [],
                "worth": False, "why": "tur artıq başlayıb"}
    if any(g["tbc"] for g in games):
        return {"title": f"{head}: oyun saatları bəlli deyil", "lead": "Turun oyunlarının saatı hələ 00:00 yazılıb.",
                "body": [], "worth": False, "why": "oyun saatları hələ bəlli deyil (00:00)"}
    table, pos, shared = _positions(L)
    first, last = games[0]["when"], games[-1]["when"]
    leader = next((k for k in table if pos.get(k) == 1 and k not in shared), None)
    lg = next((g for g in games if leader in (g["home"], g["away"])), None) if leader else None
    title = f"{head} {ox.day_loc(first)} başlayır"
    lead = f"{sx(L['name'], 'gen', False)} {ox.ordinal(rnd)} turu {_span_loc(first, last)} keçiriləcək."
    starters = [g for g in games if g["when"] == first]
    if len(starters) > 1:
        lead += f" Tur {ox.day_loc(first)} {ox.time_loc(first)} {len(starters)} oyunla başlayacaq."
    elif starters[0] is not lg:
        lead += f" Tur {ox.day_loc(first)} {ox.time_loc(first)}{_at_venue(starters[0])} {_pair(starters[0], nm)} oyunu ilə başlayacaq."
    if lg:
        home = lg["home"] == leader
        opp = lg["away"] if home else lg["home"]
        desc = ""
        if opp not in shared and pos.get(opp) == len(table):
            desc = "sonuncu "
        elif opp not in shared and pos.get(opp) == 2:
            desc = "ikinci yerdəki "
        act = f"{sx(nm(opp), 'acc')} qəbul edəcək" if home else f"{sx(nm(opp), 'dat')} qonaq gedəcək"
        longer = f"{title}: lider {_q(nm(leader))} {desc}{act}"
        if len(longer) <= TITLE_MAX:
            title = longer
        w = lg["when"]
        act = f"{sx(nm(opp), 'acc')} qəbul edəcək" if home else f"{sx(nm(opp), 'dat')} qonaq olacaq"
        lead += f" {table[leader]['pts']} xalla lider olan {_q(nm(leader))} {ox.day_loc(w)} {ox.time_loc(w)}{_at_venue(lg)} {act}."
        if len(starters) == 1 and starters[0] is lg:
            lead += " Bu, turun ilk oyunudur."
        rec = _h2h(past, leader, opp)
        if rec["n"] >= 2:
            lead += " " + _h2h_text(rec, leader, opp, nm)
    body = []
    for g in games:
        w, v = g["when"], venue(g["stadium"])
        where = f", {v}" if v else ""
        line = (f"{ox.day_text(w)}, {w:%H:%M}{where}: {_q(nm(g['home']))}{_tag(g['home'], table, pos, shared)} – "
                f"{_q(nm(g['away']))}{_tag(g['away'], table, pos, shared)}")
        prev = _h2h(past, g["home"], g["away"])["last"]
        if prev:
            line += f". Son qarşılaşma: {ox.day_text(prev['when'])} {prev['when'].year}, {_score(prev, nm)}"
        body.append(line + ".")
    return {"title": title, "lead": lead, "body": body, "list": True, "credit": CREDIT_PFL, "link": LINK_PFL}


# --- 3. Bombardirlər -----------------------------------------------------------------------------------------

def _pfl_get(fetch, path):
    return json.loads(fetch(ox.PFL_API + path, timeout=15, headers={"Accept": "application/json"}).decode("utf-8"))


def scorer_rows(doc):
    """pfl.az cavabı -> ([{name, club, goals}], başqa səhifə varmı).
    /bombarders/list: {"data": {"data": [...], "last_page": 1, "total": 13}}; /bombarders: {"data": [...]}."""
    data = (doc or {}).get("data") if isinstance(doc, dict) else None
    more = False
    if isinstance(data, dict):
        rows = data.get("data") or []
        more = int(data.get("last_page") or 1) > 1 or int(data.get("total") or 0) > len(rows)
    else:
        rows = data or []
    out = []
    for r in rows:
        if not isinstance(r, dict):
            continue
        p = r.get("player") or {}
        name = " ".join(x for x in (str(p.get("name") or "").strip(), str(p.get("surname") or "").strip()) if x)
        try:
            goals = int(str(r.get("value")).strip())  # pfl.az qolu mətn kimi verir: "9"
        except ValueError:
            continue
        if name and goals > 0:
            out.append({"name": name, "club": str((r.get("club") or {}).get("title") or ""), "goals": goals})
    return out, more


def sorted_scorers(rows):
    """Qola görə azalan; bərabərdə ad, sonra klub (Azərbaycan əlifbası): hər dəfə eyni sıra."""
    return sorted(rows, key=lambda r: (-r["goals"], _az_key(r["name"]), _az_key(r["club"])))


def pfl_scorers(fetch, season):
    """Premyer Liqanın bombardirləri: /seasons (liqa nömrəsi) + /bombarders/list; siyahı səhifəlidirsə /bombarders."""
    seasons = _pfl_get(fetch, "/seasons?project_id=1")
    s = ((seasons or {}).get("data") or [{}])[0] or {}
    if season and not str(s.get("title") or "").startswith(season[:4]):
        raise ValueError(f"mövsüm uyğun gəlmir: {s.get('title')}")
    lid = ((s.get("leagues") or [{}])[0] or {}).get("id")
    if not lid:
        raise ValueError("liqa tapılmadı")
    rows, more = scorer_rows(_pfl_get(fetch, f"/bombarders/list?league_id={lid}"))
    if more:
        rows, more = scorer_rows(_pfl_get(fetch, f"/bombarders?league_id={lid}"))
    return sorted_scorers(rows)


def _who(r, case=None):
    if not r["club"]:
        return r["name"]
    if case == "gen":
        return f"{sx(r['club'], 'gen')} futbolçusu {r['name']}"
    if case == "abl":
        return f"{sx(r['club'], 'abl')} {r['name']}"
    return f"{r['name']} ({_q(r['club'])})"


def _scorers(L, rnd, main, fetch=None):
    """Turdan sonrakı səhər bombardirlər siyahısı (pfl.az). Turdan sonra yeni oyun oynanıbsa, siyahı bu tura aid deyil."""
    head = f"{sx(L['short'], 'gen', False)} bombardirlər yarışı"

    def skip(why):
        return {"title": f"{head}: {ox.ordinal(rnd)} turdan sonra", "lead": f"Siyahı yazılmadı: {why}.", "body": [],
                "worth": False, "why": why}
    if any(not g["played"] for g in main):
        return skip("tur bitməyib")
    last = max(g["when"] for g in main)
    if any(g["played"] and g["when"] > last for g in L["games"]):
        return skip("turdan sonra yeni oyunlar oynanıb, siyahı artıq bu tura aid deyil")
    if fetch is None:
        return skip("pfl.az sorğusu verilməyib")
    try:
        rows = pfl_scorers(fetch, L["season"])
    except Exception as e:  # şəbəkə, JSON, mövsüm uyğunsuzluğu: xəbər yoxdur
        return skip(f"pfl.az alınmadı ({type(e).__name__})")
    if not rows:
        return skip("bombardirlər siyahısı boşdur")
    top = rows[0]["goals"]
    leaders = [r for r in rows if r["goals"] == top]
    cut = rows[min(4, len(rows) - 1)]["goals"]
    shown = [r for r in rows if r["goals"] >= cut][:12]
    if len(leaders) == 1:
        who = _who(leaders[0], "gen")
        title = f"{head}nda {who} {top} qolla öndədir"
        if len(title) > TITLE_MAX:
            title = f"{head}nda {leaders[0]['name']} {top} qolla öndədir"
    else:
        who = _and([_who(r) for r in leaders])
        title = f"{head}nda {_and([r['name'] for r in leaders])} {top} qolla öndədir"
        if len(title) > TITLE_MAX:
            title = f"{head}nda {len(leaders)} futbolçu {top} qolla öndədir"
    lead = (f"{sx(L['name'], 'gen', False)} {ox.ordinal(rnd)} turundan sonra bombardirlər siyahısına {who} "
            f"{top} qolla başçılıq edir.")
    nxt = rows[len(leaders):len(leaders) + 2]
    if nxt:
        lead += " " + ", ".join(f"{_who(r, 'abl')} {r['goals']}" for r in nxt) + " qol vurub."
    body = [f"{_who(r)} – {r['goals']} qol" for r in shown]
    return {"title": title, "lead": lead, "body": body, "list": True, "credit": CREDIT_PFL, "link": LINK_PFL}


# --- 5. Azərbaycan Kuboku ------------------------------------------------------------------------------------

STAGE_DONE = {"I təsnifat": "I təsnifat mərhələsi", "II təsnifat": "II təsnifat mərhələsi",
              "III təsnifat": "III təsnifat mərhələsi", "1/16 final": "1/16 final mərhələsi", "1/8 final": "1/8 final mərhələsi",
              "1/4 ilk": "1/4 final mərhələsinin ilk oyunları", "1/4 cavab": "1/4 final mərhələsinin cavab oyunları",
              "1/2 ilk": "yarımfinalının ilk oyunları", "1/2 cavab": "yarımfinalının cavab oyunları", "Final": "finalı"}
STAGE_PAIRS = {"1/4 ilk": "1/4 final mərhələsi", "1/2 ilk": "yarımfinalı", "Final": "finalı"}


def _cup_events(K, pl_pos):
    """Hər mərhələ: bitəndə nəticələr; cütlər əvvəlki mərhələ bitəndən 10 gün ərzində (və ya ilk mərhələdən 7 gün əvvəl)."""
    stages = {}
    for g in K["games"]:
        stages.setdefault(g["round"], []).append(g)
    order = sorted(stages, key=lambda s: min(g["when"] for g in stages[s]))
    evs, prev_ready = [], None
    for i, s in enumerate(order):
        gs = stages[s]
        first, last = min(g["when"] for g in gs), max(g["when"] for g in gs)
        tag = f"kubok-{K['key']}-{_slug(s)}"
        ready = _ready_after(last, 9)
        evs.append(_ev("kubok-merhele", f"{tag}-yekun", ready, ready + 36 * HOUR,
                       functools.partial(_cup_results, K, stages, order, i)))
        if "cavab" not in s:
            start = prev_ready or first - 7 * DAY
            end = min(first, start + 10 * DAY)
            if start < end:
                evs.append(_ev("kubok-cutler", f"{tag}-cutler", start, end,
                               functools.partial(_cup_pairs, K, stages, order, i, pl_pos)))
        prev_ready = ready
    return evs


def _cup_results(K, stages, order, i, fetch=None):
    """Mərhələ bitdi: nəticələr, qollar; heç-heçədə növbəti mərhələyə keçən növbəti mərhələnin cütlərindən."""
    s = order[i]
    gs = sorted(stages[s], key=lambda g: g["when"])
    nm = functools.partial(_nm, K)
    cup = sx(K["name"], "gen", False)
    text = STAGE_DONE.get(s, f"{s} mərhələsi")
    missing = [g for g in gs if not g["played"]]
    if missing:
        return {"title": f"{cup} {text}: mərhələ bitməyib", "lead": f"Mərhələdə {len(gs)} oyun var, nəticəsi bəlli olan: {len(gs) - len(missing)}.",
                "body": [], "worth": False, "why": "mərhələ bitməyib"}
    first, last = gs[0]["when"], gs[-1]["when"]
    total = sum(g["hs"] + g["as"] for g in gs)
    big = max(gs, key=lambda g: (abs(g["hs"] - g["as"]), g["hs"] + g["as"]))
    title = f"{cup} {text}: {_win(big, nm)}"
    if len(title) > TITLE_MAX:
        title = f"{cup} {text} başa çatıb"
    lead = f"{cup} {text} {_span_loc(first, last)} keçirilib."
    final = s.lower() == "final"
    if final and big["hs"] != big["as"]:
        winner = big["home"] if big["hs"] > big["as"] else big["away"]
        lead += f" {_q(nm(winner))} {sx(K['name'], 'acc', False)} qazanıb."
    elif not final:
        lead += f" Mərhələnin {len(gs)} oyununda {total} qol vurulub."
    nxt = stages.get(order[i + 1], []) if i + 1 < len(order) else []
    ahead = {t for g in nxt for t in (g["home"], g["away"])}
    legs = {}
    if "cavab" in s:
        for g1 in stages.get(s.replace("cavab", "ilk"), []):
            if g1["played"]:
                legs[(g1["away"], g1["home"])] = g1  # cavab oyununda ev sahibi ilk oyunun qonağıdır
    body = []
    for g in gs:
        line, level = _score(g, nm), g["hs"] == g["as"]
        g1 = legs.get((g["home"], g["away"]))
        if g1:
            x, y = g["hs"] + g1["as"], g["as"] + g1["hs"]
            line += f"; iki oyunun cəmi {x}:{y}"
            level = x == y
        went = [t for t in (g["home"], g["away"]) if t in ahead]
        if "ilk" not in s and (level or g1) and len(went) == 1:
            line += f" (növbəti mərhələyə {_q(nm(went[0]))} keçib)"
        body.append(line)
    return {"title": title, "lead": lead, "body": body, "list": True, "credit": CREDIT_PFL, "link": LINK_PFL}


def _cup_pairs(K, stages, order, i, pl_pos, fetch=None):
    """Mərhələnin cütləri. Başlıqda Premyer Liqanın ən güclü cütləri (cədvəldəki yerlərin cəmi ən kiçik olan)."""
    s = order[i]
    gs = sorted(stages[s], key=lambda g: g["when"])
    nm = functools.partial(_nm, K)
    cup = sx(K["name"], "gen", False)
    text = STAGE_PAIRS.get(s) or STAGE_DONE.get(s, f"{s} mərhələsi")
    if any(g["played"] for g in gs):
        return {"title": f"{cup} {text}: mərhələ başlayıb", "lead": "Mərhələnin oyunları artıq başlayıb.", "body": [],
                "worth": False, "why": "mərhələ başlayıb"}
    if any(t not in K["known"] for g in gs for t in (g["home"], g["away"])):
        return {"title": f"{cup} {text}: cütlər bəlli deyil", "lead": "Cütlərin bəzi komandaları hələ bəlli deyil.", "body": [],
                "worth": False, "why": "cütlər tam bəlli deyil"}
    # Bütün oyunlar eyni anda və ya 00:00-da: tarix yer tutucudur (pfl.az 1/8 finalı belə yazıb), yazılmır.
    real = not any(g["tbc"] for g in gs) and not (len(gs) >= 3 and len({g["when"] for g in gs}) == 1)
    first, last = gs[0]["when"], gs[-1]["when"]
    if s.lower() == "final":
        g = gs[0]
        title = f"{cup} finalında {_q(nm(g['home']))} və {_q(nm(g['away']))} qarşılaşacaq"
        lead = f"{cup} finalının iştirakçıları bəllidir: {_q(nm(g['home']))} və {_q(nm(g['away']))}."
    else:
        def strength(g):
            ps = [pl_pos[t] for t in (g["home"], g["away"]) if t in pl_pos]
            return (-len(ps), sum(ps), min(ps) if ps else 99)
        ranked = sorted(gs, key=strength)
        hosts = ", ".join(f"{_q(nm(g['home']))} {sx(nm(g['away']), 'acc')}" for g in ranked[:2])
        title = f"{cup} {text}: {hosts} qəbul edəcək"
        if len(title) > TITLE_MAX:
            title = f"{cup} {text}: {_q(nm(ranked[0]['home']))} {sx(nm(ranked[0]['away']), 'acc')} qəbul edəcək"
        lead = f"{sx(cup + ' ' + text, 'gen', False)} cütləri bəllidir."
        top = [g for g in ranked if g["home"] in pl_pos and g["away"] in pl_pos]
        if top:
            lead += f" Premyer Liqa komandaları {len(top)} cütdə bir-biri ilə qarşılaşacaq: {', '.join(_pair(g, nm) for g in top)}."
    if real and len(gs) == 1:
        lead += f" Oyun {ox.day_loc(first)} {ox.time_loc(first)} keçiriləcək."
    elif real:
        lead += f" Oyunlar {_span_loc(first, last)} keçiriləcək."
    body = []
    for g in gs:
        line = _pair(g, nm)
        if real:
            v = venue(g["stadium"])
            line += f" ({ox.day_text(g['when'])}, {g['when']:%H:%M}{', ' + v if v else ''})"
        body.append(line)
    return {"title": title, "lead": lead, "body": body, "list": True, "credit": CREDIT_PFL, "link": LINK_PFL}


# --- 6. Azərbaycan millisi -----------------------------------------------------------------------------------

def _menu_ids(root):
    """Azərbaycanın olduğu yarışların faylları (data/milli-menyu.json); menyu yoxdursa Millətlər Liqası faylları."""
    try:
        menu = json.loads((pathlib.Path(root) / "data" / "milli-menyu.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return ["ml-a", "ml-b", "ml-c", "ml-d"]
    comps = menu.get("comps") if isinstance(menu, dict) else None
    return [str(c.get("id")) for c in comps or [] if isinstance(c, dict) and "Azərbaycan" in (c.get("teams") or [])
            and re.fullmatch(r"[a-z0-9-]+", str(c.get("id")))]


def _milli_events(root):
    evs = []
    for cid in _menu_ids(root):
        D = _league(root, cid)
        if not D:
            continue
        az = next((k for k, v in D["names"].items() if v == "Azərbaycan"), None)
        if not az:
            continue
        for g in D["games"]:
            if az not in (g["home"], g["away"]):
                continue
            tag = f"milli-{cid}-{D['key']}-{g['when']:%Y%m%d}"
            if g["played"]:
                ready = _ready_after(g["when"], 8)
                evs.append(_ev("milli-netice", f"{tag}-netice", ready, ready + 36 * HOUR,
                               functools.partial(_milli_result, D, az, g)))
            elif not g["tbc"]:
                evs.append(_ev("milli-oncesi", f"{tag}-oncesi", _at((g["when"] - DAY).date(), 12), g["when"],
                               functools.partial(_milli_preview, D, az, g)))
    return evs


def _comp(D):
    """(«UEFA Millətlər Liqasının D liqasında», «Millətlər Liqasında»)."""
    m = re.fullmatch(r"Millətlər Liqası ([A-D])", D["name"])
    if m:
        return f"UEFA Millətlər Liqasının {m.group(1)} liqasında", "Millətlər Liqasında"
    return f"«{D['name']}» turnirində", f"«{D['name']}» turnirində"


def _group_gen(grp):
    """«Qrup 2» -> «2-ci qrupun», «Qrup A» -> «A qrupunun»."""
    m = re.fullmatch(r"Qrup (\d+)", grp)
    if m:
        return f"{ox.ordinal(m.group(1))} qrupun"
    m = re.fullmatch(r"Qrup ([A-Z])", grp)
    return f"{m.group(1)} qrupunun" if m else ""


def _standing(D, grp, until):
    """Qrup cədvəli «until» anına: rəsmi cədvəl yalnız oyunlarla uyğundursa və sonra oyun oynanmayıbsa."""
    gs = [x for x in D["games"] if x["round"] == grp]
    rows = next((_rows(gr) for gr in D["groups"] if isinstance(gr, dict) and gr.get("name") == grp), {})
    teams = list(rows) or sorted({t for x in gs for t in (x["home"], x["away"])})
    table = _table([x for x in gs if x["played"] and x["when"] <= until], teams)
    later = any(x["played"] and x["when"] > until for x in gs)
    if rows and not later and _table_ok(rows, table):
        order = sorted(rows, key=lambda k: int(rows[k].get("pos") or 99))
        return table, order, {k: int(rows[k].get("pos") or 0) for k in order}, set()
    pos, shared = _pos(table)
    return table, _order(table, D["names"]), pos, shared


def _standing_text(D, table, order, pos, shared):
    if shared or any(not pos.get(k) for k in order):
        return "Qrupda " + ", ".join(f"{D['names'].get(k, k)} {table[k]['p']} oyunda {table[k]['pts']}" for k in order) + " xal toplayıb"
    return "Qrupda " + ", ".join(f"{D['names'].get(k, k)} {table[k]['p']} oyunda {table[k]['pts']} xalla {_place(pos[k])}"
                                 for k in order) + " yerdədir"


def _milli_preview(D, az, g, fetch=None):
    """Millinin oyunundan bir gün əvvəl: rəqib, stadion, Bakı vaxtı, qrupdakı vəziyyət."""
    home = g["home"] == az
    opp = D["names"].get(g["away"] if home else g["home"], "")
    full, short = _comp(D)
    grp = _group_gen(g["round"])
    w = g["when"]
    act = f"{sx(opp, 'acc', False)} qəbul edəcək" if home else f"{sx(opp, 'dat', False)} qonaq gedəcək"
    title = f"Azərbaycan millisi {short} {ox.day_loc(w)} {act}"
    where = _nat_loc(g["stadium"])
    lead = (f"Azərbaycan millisi {full} {grp + ' ' if grp else ''}növbəti oyununu {ox.day_loc(w)}{' ' + where if where else ''} "
            f"{opp} millisinə qarşı keçirəcək. Görüş Bakı vaxtı ilə {ox.time_loc(w)} başlayacaq.")
    table, order, pos, shared = _standing(D, g["round"], w)
    if any(table[k]["p"] for k in order):
        lead += f" {_standing_text(D, table, order, pos, shared)}."
    if grp and not any(az in (x["home"], x["away"]) and x["round"] == g["round"] and x["when"] > w for x in D["games"]):
        lead += " Bu, Azərbaycanın qrupdakı son oyunudur."
    body = [f"{ox.day_text(x['when'])}: {D['names'].get(x['home'])} – {D['names'].get(x['away'])} – {x['hs']}:{x['as']}"
            for x in D["games"] if az in (x["home"], x["away"]) and x["round"] == g["round"] and x["played"] and x["when"] < w]
    return {"title": title, "lead": lead, "body": body, "list": True, "credit": _credit(D), "link": _link(D)}


def _milli_result(D, az, g, fetch=None):
    """Millinin oyununun nəticəsi və qrupdakı yeri."""
    home = g["home"] == az
    opp = D["names"].get(g["away"] if home else g["home"], "")
    gf, ga = (g["hs"], g["as"]) if home else (g["as"], g["hs"])
    full, short = _comp(D)
    grp = _group_gen(g["round"])
    away = "" if home else "səfərdə "
    if gf > ga:
        act, res = f"{sx(opp, 'acc', False)} {gf}:{ga} hesabı ilə məğlub edib", f"{opp} millisini {gf}:{ga} hesabı ilə məğlub edib"
    elif gf < ga:
        act, res = f"{sx(opp, 'dat', False)} {gf}:{ga} hesabı ilə uduzub", f"{opp} millisinə {gf}:{ga} hesabı ilə uduzub"
    elif gf:
        act, res = f"{opp} ilə {gf}:{ga} hesabı ilə heç-heçə edib", f"{opp} millisi ilə {gf}:{ga} hesabı ilə heç-heçə edib"
    else:
        act, res = f"{opp} ilə qolsuz heç-heçə edib", f"{opp} millisi ilə qolsuz heç-heçə edib"
    title = f"Azərbaycan millisi {short} {away}{act}"
    where = _nat_loc(g["stadium"])
    lead = f"Azərbaycan millisi {full} {grp + ' ' if grp else ''}oyununda{' ' + where if where else ''} {res}."
    table, order, pos, shared = _standing(D, g["round"], g["when"])
    me = table.get(az)
    if me:
        lead += f" Bu nəticədən sonra Azərbaycan {me['p']} oyunda {me['pts']} xal toplayıb"
        lead += f" və qrupda {_place(pos[az])} yerdədir." if az not in shared and pos.get(az) else "."
    nxt = next((x for x in D["games"] if az in (x["home"], x["away"]) and not x["played"] and x["when"] > g["when"]
                and not x["tbc"]), None)
    if nxt:
        o2 = D["names"].get(nxt["away"] if nxt["home"] == az else nxt["home"], "")
        lead += (f" Komanda növbəti oyununu {ox.day_loc(nxt['when'])} Bakı vaxtı ilə {ox.time_loc(nxt['when'])} "
                 f"{sx(o2, 'dat', False)} qarşı keçirəcək.")
    elif grp and not any(az in (x["home"], x["away"]) and x["round"] == g["round"] and x["when"] > g["when"] for x in D["games"]):
        lead += " Bu, Azərbaycanın qrupdakı son oyunu idi."
    numbered = not shared and all(pos.get(k) for k in order)
    body = [f"{ox.ordinal(pos[k]) + ' yer: ' if numbered else ''}{D['names'].get(k, k)} – {table[k]['p']} oyun, {table[k]['pts']} xal"
            for k in order]
    return {"title": title, "lead": lead, "body": body, "list": True, "credit": _credit(D), "link": _link(D)}


# --- 7. Avrokubokda Azərbaycan klubu -------------------------------------------------------------------------

def _euro_events(root, clubs):
    evs = []
    for fid in EURO:
        E = _league(root, fid)
        if not E:
            continue
        for c in [k for k in E["names"] if k in clubs]:
            for g in E["games"]:
                if c not in (g["home"], g["away"]):
                    continue
                tag = f"avro-{fid}-{E['key']}-{c}-{g['when']:%Y%m%d}"
                if g["played"]:
                    ready = _ready_after(g["when"], 8)
                    evs.append(_ev("avro-netice", f"{tag}-netice", ready, ready + 36 * HOUR,
                                   functools.partial(_euro_result, E, c, g)))
                elif not g["tbc"]:
                    evs.append(_ev("avro-oncesi", f"{tag}-oncesi", _at((g["when"] - DAY).date(), 12), g["when"],
                                   functools.partial(_euro_preview, E, c, g)))
    return evs


def _stage(g):
    return f"liqa mərhələsinin {ox.ordinal(g['round'])} turunda" if g["round"].isdigit() else f"«{g['round']}» mərhələsində"


def _club(E, c, until):
    """Klubun «until» anına qədər oyunları, xalları və cədvəldəki yeri (yer yalnız cədvəl oyunlarla uyğundursa)."""
    mine = [x for x in E["games"] if c in (x["home"], x["away"]) and x["played"] and x["when"] <= until]
    t = _table(mine, [c])[c]
    row = E["official"].get(c)
    later = any(x["played"] and x["when"] > until for x in E["games"] if c in (x["home"], x["away"]))
    ok = row and not later and int(row.get("p") or 0) == t["p"] and int(row.get("pts") or 0) == t["pts"]
    return mine, t, int(row.get("pos") or 0) if ok else 0


def _euro_result(E, c, g, fetch=None):
    home = g["home"] == c
    club, opp = E["names"].get(c, c), E["names"].get(g["away"] if home else g["home"], "")
    gf, ga = (g["hs"], g["as"]) if home else (g["as"], g["hs"])
    if gf > ga:
        act, verb = f"{sx(opp, 'acc')} {gf}:{ga} hesabı ilə məğlub edib", "qalib gəlib"
    elif gf < ga:
        act, verb = f"{sx(opp, 'dat')} {gf}:{ga} hesabı ilə uduzub", "məğlub olub"
    else:
        act, verb = f"{sx(opp, 'ins')} {gf}:{ga} hesabı ilə heç-heçə edib", "heç-heçə edib"
    title = f"{_q(club)} {sx(E['name'], 'loc', False)} {act}"
    lead = (f"{sx(E['name'], 'gen', False)} {_stage(g)} {_q(club)} {'doğma meydanda' if home else 'səfərdə'} "
            f"{sx(opp, 'ins')} qarşılaşıb və {gf}:{ga} hesabı ilə {verb}.")
    mine, t, pos = _club(E, c, g["when"])
    wdl = ", ".join(x for x in (f"{t['w']} qələbə" if t["w"] else "", f"{t['d']} heç-heçə" if t["d"] else "",
                                f"{t['l']} məğlubiyyət" if t["l"] else "") if x)
    lead += f" Azərbaycan təmsilçisi {t['p']} oyunda {t['pts']} xal toplayıb ({wdl})"
    lead += f" və {len(E['official'])} komanda arasında {ox.ordinal(pos)} yerdədir." if pos else "."
    nxt = next((x for x in E["games"] if c in (x["home"], x["away"]) and not x["played"] and x["when"] > g["when"]
                and not x["tbc"]), None)
    if nxt:
        h2 = nxt["home"] == c
        o2 = E["names"].get(nxt["away"] if h2 else nxt["home"], "")
        lead += (f" {_q(club)} növbəti oyununu {ox.day_loc(nxt['when'])} Bakı vaxtı ilə {ox.time_loc(nxt['when'])} "
                 f"{'doğma meydanda' if h2 else 'səfərdə'} {sx(o2, 'dat')} qarşı keçirəcək.")
    body = [_score(x, functools.partial(_nm, E)) for x in mine]
    return {"title": title, "lead": lead, "body": body, "list": True, "credit": _credit(E), "link": _link(E)}


def _euro_preview(E, c, g, fetch=None):
    home = g["home"] == c
    other = g["away"] if home else g["home"]
    club, opp = E["names"].get(c, c), E["names"].get(other, other)
    w = g["when"]
    act = f"{sx(opp, 'acc')} qəbul edəcək" if home else f"{sx(opp, 'dat')} qonaq gedəcək"
    title = f"{_q(club)} {sx(E['name'], 'loc', False)} {ox.day_loc(w)} {act}"
    lead = (f"{sx(E['name'], 'gen', False)} {_stage(g)} {_q(club)} {ox.day_loc(w)} Bakı vaxtı ilə {ox.time_loc(w)} "
            f"{'doğma meydanda' if home else 'səfərdə'} {sx(opp, 'ins')} qarşılaşacaq.")
    mine, t, pos = _club(E, c, w)
    if t["p"]:
        lead += f" {_q(club)} {t['p']} oyunda {t['pts']} xal toplayıb"
        lead += f" və {len(E['official'])} komanda arasında {ox.ordinal(pos)} yerdədir." if pos else "."
    _, to, po = _club(E, other, w)
    if to["p"] and po:
        lead += f" {_q(opp)} {to['p']} oyunda {to['pts']} xalla {ox.ordinal(po)} yerdədir."
    body = [_score(x, functools.partial(_nm, E)) for x in mine]
    return {"title": title, "lead": lead, "body": body, "list": True, "credit": _credit(E), "link": _link(E)}


# --- Yığım və dərc --------------------------------------------------------------------------------------------

def _events(root):
    """Bütün hadisələr (hər birinin dərc pəncərəsi) və məlumat xətaları. Bir fayl pozulubsa, qalanları işləyir."""
    root = pathlib.Path(root)
    evs, errors = [], []

    def run(fn, *args):
        try:
            return fn(*args)
        except Exception as e:
            errors.append(f"{fn.__name__}: {type(e).__name__}: {e}"[:300])
            return None
    pl = run(_league, root, "premyer-liqa")
    pl_pos, clubs = {}, set()
    if pl:
        past = [(str(d.get("season") or ""), _games(d)) for d in (_read(root, n) for n in PAST_PL) if d]
        past.append((pl["season"], pl["games"]))
        evs += run(_league_events, pl, past) or []
        pl_pos = run(_pl_pos, pl) or {}
        clubs = set(pl["names"])
    for lid in ("i-liqa", "ii-liqa"):
        L = run(_league, root, lid)
        if L:
            evs += run(_league_events, L) or []
    K = run(_league, root, "kubok")
    if K:
        evs += run(_cup_events, K, pl_pos) or []
    evs += run(_milli_events, root) or []
    evs += run(_euro_events, root, clubs) or []
    return evs, errors


def _owner(item):
    """Rəhbərliyin adı keçirsə (updater.president_score) xəbər avtomatik dərc olunmur."""
    blob = "\n".join([item.get("title") or "", item.get("lead") or ""] + [str(b) for b in item.get("body") or []])
    try:
        return bool(ox.needs_owner(blob))
    except Exception:  # updater yüklənmədi: sadə yoxlama
        low = ox._low(blob)
        return any(w in low for w in ("prezident", "ilham əliyev", "mehriban əliyeva", "vitse-prezident", "birinci xanım"))


def _build(ev, fetch):
    try:
        made = ev["make"](fetch)
    except Exception as e:  # pozulmuş məlumat yalnız bu xəbəri saxlayır
        made = {"title": ev["key"], "lead": "Məlumat oxunmadı.", "body": [], "worth": False,
                "why": f"xəta: {type(e).__name__}: {e}"[:200]}
    item = {"kind": ev["kind"], "key": ev["key"], "title": "", "lead": "", "body": [], "credit": CREDIT_PFL,
            "link": LINK_PFL, "topic": "idman", "slot": ev["ready"].strftime("%H:%M"), "worth": True}
    item.update(made)
    if item["worth"] and _owner(item):
        item.update(worth=False, why="rəhbərliyin adı keçir: avtomatik dərc olunmur")
    return item


def _allowed(evs, day):
    """Günün (dərc vaxtına görə) ilk DAY_CAP dərc olunası hadisəsi, vaciblik sırası ilə."""
    keys = []
    for e in sorted((e for e in evs if e["ready"].date() == day), key=lambda e: (e["prio"], e["ready"], e["key"])):
        if e["fetch"] or _build(e, None)["worth"]:
            keys.append(e["key"])
    return set(keys[:DAY_CAP])


def items(root, now, fetch=None):
    """«now» anında (Bakı vaxtı) dərc pəncərəsi açıq olan xəbərlər. worth=False olanın səbəbi why-dadır.
    fetch yalnız bombardirlər üçündür (pəncərəsi açıq olanda, bir tura bir dəfə)."""
    now = _baku(now)
    evs, _ = _events(root)
    live = sorted((e for e in evs if e["ready"] <= now < e["expires"]), key=lambda e: (e["ready"], e["prio"], e["key"]))
    allowed, out = {}, []
    for e in live:
        day = e["ready"].date()
        if day not in allowed:
            allowed[day] = _allowed(evs, day)
        item = _build(e, fetch)
        if item["worth"] and e["key"] not in allowed[day]:
            item.update(worth=False, why=f"gündəlik hədd: bu moduldan gündə ən çox {DAY_CAP} xəbər")
        out.append(item)
    return out


# --- Sınaq ----------------------------------------------------------------------------------------------------

SECTIONS = (
    ("pfl-tur", "Premyer Liqa: tur icmalı", "past"),
    ("pfl-tur-oncesi", "Premyer Liqa: növbəti tura baxış", "next"),
    ("pfl-bombardir", "Premyer Liqa: bombardirlər", "past"),
    ("liqa-tur:i-liqa", "I Liqa: tur icmalı", "past"),
    ("liqa-tur:ii-liqa", "II Liqa: tur icmalı", "past"),
    ("kubok-merhele", "Azərbaycan Kuboku: mərhələnin nəticələri", "past"),
    ("kubok-cutler", "Azərbaycan Kuboku: cütlər", "both"),
    ("milli-oncesi", "Azərbaycan millisi: oyundan bir gün əvvəl", "next"),
    ("milli-netice", "Azərbaycan millisi: nəticə", "past"),
    ("avro-oncesi", "Avrokubok: oyundan bir gün əvvəl", "next"),
    ("avro-netice", "Avrokubok: nəticə", "past"),
)


def _real_fetch():
    try:
        return ox._u().fetch
    except Exception:
        return None


def _memo(fetch):
    """Bir sınaqda eyni ünvan bir dəfə soruşulur."""
    if fetch is None:
        return None
    seen = {}

    def get(url, **kw):
        if url not in seen:
            seen[url] = fetch(url, **kw)
        return seen[url]
    return get


def _verdict(item, ev, now):
    if not item["worth"]:
        return f"⏭ Dərc olunmazdı: {item.get('why') or '-'}"
    if ev["ready"] <= now < ev["expires"]:
        return f"✅ Dərc olunardı (indi; növbəsi {_stamp(ev['ready'])})"
    return f"✅ Dərc olunardı ({_stamp(ev['ready'])})"


def _cases(mine, now, mode, fetch):
    """Bölmənin göstəriləcək halları: son real hal (dərc olunmazdısa, ondan əvvəlki dərc olunası da), növbəti hal."""
    out = []
    if mode in ("past", "both"):
        past = [e for e in mine if e["ready"] <= now]
        if past:
            item = _build(past[-1], fetch)
            out.append(("son real hal", past[-1], item))
            if not item["worth"]:
                for e in reversed(past[-7:-1]):
                    older = _build(e, fetch)
                    if older["worth"]:
                        out.append(("ondan əvvəlki dərc olunası hal", e, older))
                        break
    if mode in ("next", "both"):
        shown = {c[1]["key"] for c in out}
        nxt = [e for e in mine if e["expires"] > now and e["key"] not in shown]
        if nxt:
            out.append(("növbəti hal", nxt[0], _build(nxt[0], fetch)))
    return out


def sinaq(root, now=None, fetch=None):
    """Nümunələr (Markdown): bu an dərc olunacaqlar və hər xəbər növünün son (və ya növbəti) real halı."""
    now = _baku(now) if now else datetime.datetime.now(BAKU)
    root = pathlib.Path(root)
    fetch = _memo(fetch if fetch is not None else _real_fetch())
    evs, errors = _events(root)
    md = [f"## Azərbaycan futbolu: öz xəbərlər ({now:%d.%m.%Y %H:%M}, Bakı vaxtı)", "",
          "Şablon xəbərlər, süni intellektsiz: hər rəqəm və ad data/futbol məlumatındandır. Sayta heç nə yazılmır.", ""]
    md += [f"> Məlumat xətası: {e}" for e in errors] + ([""] if errors else [])
    live = items(root, now, fetch)
    md += ["**Bu an dərc olunacaqlar:**", ""]
    md += [f"- `{i['key']}` ({i['slot']}): {i['title']} — " + ("✅" if i["worth"] else f"⏭ {i.get('why')}") for i in live] or ["- yoxdur"]
    md += [""]
    for fam, label, mode in SECTIONS:
        md += [f"## {label}", ""]
        mine = sorted((e for e in evs if e["fam"] == fam), key=lambda e: (e["ready"], e["key"]))
        cases = _cases(mine, now, mode, fetch)
        if not cases:
            md += ["> Məlumatda belə hal yoxdur.", ""]
        for tag, e, item in cases:
            md += [f"_{tag}: dərc vaxtı {_stamp(e['ready'])}, açar `{e['key']}`_", ""]
            md += ox.render(item)
            md += [_verdict(item, e, now), ""]
    return md


def _arg(argv, name):
    return argv[argv.index(name) + 1] if name in argv and argv.index(name) + 1 < len(argv) else None


def main(argv):
    if "--sinaq" not in argv:
        print(__doc__)
        return 0
    root = pathlib.Path(_arg(argv, "--root") or pathlib.Path(__file__).resolve().parent)
    raw = _arg(argv, "--now")
    sys.stdout.write("\n".join(sinaq(root, _when(raw) if raw else None)) + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
