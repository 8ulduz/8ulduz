"""Səma xəbərləri (oz_sema.py): hesablama USNO və JPL Horizons cədvəllərinə qarşı, statik cədvəllər IMO və NASA-ya qarşı,
şablonlar və kənar hallar. Şəbəkə yoxdur: fixture-lər bir dəfə alınıb (tests/fixtures/oz_sema/)."""
import datetime
import io
import json
import math
import pathlib
import re
import unittest
from contextlib import redirect_stdout
from unittest.mock import patch

import oz_sema as sema
import oz_xeber as ox

FIX = pathlib.Path(__file__).resolve().parent / "fixtures" / "oz_sema"
ROOT = pathlib.Path(__file__).resolve().parent.parent
UTC = datetime.timezone.utc
BAKU = ox.BAKU
D = datetime.date
_MON = {m: i + 1 for i, m in enumerate(("Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"))}


def _load(name):
    return json.loads((FIX / name).read_text(encoding="utf-8"))


def _jpl_time(s):
    """«2026-Nov-24 14:53» və ya «2026-Jan-03 21:00:00.000» -> UTC datetime."""
    day, hms = s.strip().split(" ")
    y, mon, d = day.split("-")
    parts = hms.split(":")
    sec = float(parts[2]) if len(parts) > 2 else 0.0
    return (datetime.datetime(int(y), _MON[mon], int(d), int(parts[0]), int(parts[1]), tzinfo=UTC)
            + datetime.timedelta(seconds=sec))


def _cells(line):
    return [c.strip() for c in line.split(",")]


def _root(t0, f0, t1, f1):
    return t0 + (t1 - t0) * (-f0 / (f1 - f0))


def _wrap(x):
    return (x + 180.0) % 360.0 - 180.0


def _baku(y, m, d, hh=0, mm=0):
    return datetime.datetime(y, m, d, hh, mm, tzinfo=BAKU)


def _kind(day, kind, now=None):
    return [i for i in sema.day_items(day, now) if i["kind"] == kind]


class UsnoReferenceTest(unittest.TestCase):
    """Brifin dözümləri: fazalar və fəsillər 3 dəqiqə, doğma və batma 2 dəqiqə."""

    def test_moon_phases_match_usno(self):
        names = {"New Moon": 0, "First Quarter": 1, "Full Moon": 2, "Last Quarter": 3}
        ref = [p for r in _load("usno-phases.json")["responses"] for p in r["phasedata"]]
        self.assertEqual(len(ref), 100)
        mine = sema.phases(datetime.datetime(2025, 12, 25, tzinfo=UTC), datetime.datetime(2028, 2, 10, tzinfo=UTC))
        worst = 0.0
        times = []
        for p in ref:
            h, m = map(int, p["time"].split(":"))
            t = datetime.datetime(p["year"], p["month"], p["day"], h, m, tzinfo=UTC)
            times.append(t)
            best = min((w for q, w in mine if q == names[p["phase"]]), key=lambda w: abs((w - t).total_seconds()))
            diff = abs((best - t).total_seconds())
            worst = max(worst, diff)
            self.assertLess(diff, 180, p)
        self.assertLess(worst, 60)  # faktiki ən böyük fərq 47 saniyədir (USNO dəqiqəni yuvarlaq verir)
        window = [w for q, w in mine if times[0] - datetime.timedelta(minutes=5) <= w <= times[-1] + datetime.timedelta(minutes=5)]
        self.assertEqual(len(window), 100)  # nə artıq, nə əskik faza

    def test_seasons_match_usno(self):
        idx = {3: 0, 6: 1, 9: 2, 12: 3}
        n = 0
        for r in _load("usno-seasons.json")["responses"]:
            for s in r["data"]:
                if s["phenom"] not in ("Equinox", "Solstice"):
                    continue
                h, m = map(int, s["time"].split(":"))
                t = datetime.datetime(s["year"], s["month"], s["day"], h, m, tzinfo=UTC)
                i = idx[s["month"]]
                meeus = sema.dt_of(sema.season_jde(s["year"], i) - sema.DELTA_T / 86400.0)
                self.assertLess(abs((meeus - t).total_seconds()), 180, s)
                self.assertLess(abs((sema.season(s["year"], i) - t).total_seconds()), 60, s)
                n += 1
        self.assertEqual(n, 8)

    def test_sunrise_sunset_match_usno(self):
        days = _load("usno-rstt-baku.json")["responses"]
        self.assertEqual(len(days), 10)
        for day, doc in days.items():
            d = D.fromisoformat(day)
            data = doc["properties"]["data"]
            self.assertEqual((data["tz"], doc["geometry"]["coordinates"]), (4.0, [sema.LON, sema.LAT]))
            ref = {x["phen"]: x["time"] for x in data["sundata"]}
            info = sema.day_info(d)
            for rise, phen in ((True, "Rise"), (False, "Set")):
                h, m = map(int, ref[phen].split(":"))
                exact = sema.sun_event(d, rise)
                self.assertLess(abs((exact - _baku(d.year, d.month, d.day, h, m)).total_seconds()), 120, (day, phen))
                self.assertEqual(f"{info['rise' if rise else 'set']:%H:%M}", ref[phen], (day, phen))

    def test_day_length_is_the_difference_of_the_shown_times(self):
        info = sema.day_info(D(2026, 11, 10))
        self.assertEqual((f"{info['rise']:%H:%M}", f"{info['set']:%H:%M}", sema.dur_text(info["length"])),
                         ("07:20", "17:28", "10 saat 8 dəqiqə"))
        self.assertEqual(sema.dur_text(datetime.timedelta(hours=12)), "12 saat")


class JplReferenceTest(unittest.TestCase):
    def setUp(self):
        self.jpl = _load("jpl-horizons.json")

    def test_moon_illumination_close_to_jpl(self):
        rows = self.jpl["illum"]["rows"]
        self.assertEqual(len(rows), 15)
        for line in rows:
            c = _cells(line)
            self.assertLess(abs(sema.moon_illum(_jpl_time(c[0])) * 100 - float(c[3])), 0.5, line)

    def test_meeus_phases_close_to_jpl(self):
        rows = self.jpl["phases"]["rows"]
        self.assertEqual(len(rows), 8)
        for key, r in rows.items():
            q = int(key[-1])
            (m0, m1), (s0, s1) = r["moon"], r["sun"]
            f0 = _wrap(float(_cells(m0)[3]) - float(_cells(s0)[3]) - 90 * q)
            f1 = _wrap(float(_cells(m1)[3]) - float(_cells(s1)[3]) - 90 * q)
            true = _root(_jpl_time(_cells(m0)[0]), f0, _jpl_time(_cells(m1)[0]), f1)
            mine = [w for qq, w in sema.phases(true - datetime.timedelta(days=1), true + datetime.timedelta(days=1)) if qq == q]
            self.assertEqual(len(mine), 1, key)
            self.assertLess(abs((mine[0] - true).total_seconds()), 15, key)

    def test_season_table_is_jpl_and_close_to_meeus(self):
        rows = self.jpl["seasons"]["rows"]
        self.assertEqual(sorted(rows), sorted(f"{y}-{i}" for y in sema.SEASONS_JPL for i in range(4)))
        for key, (a, b) in rows.items():
            year, i = map(int, key.split("-"))
            ca, cb = _cells(a), _cells(b)
            true = _root(_jpl_time(ca[0]), _wrap(float(ca[1]) - 90 * i), _jpl_time(cb[0]), _wrap(float(cb[1]) - 90 * i))
            self.assertLess(abs((sema.season(year, i) - true).total_seconds()), 2, key)
            meeus = sema.dt_of(sema.season_jde(year, i) - sema.DELTA_T / 86400.0)
            self.assertLess(abs((meeus - true).total_seconds()), 40, key)
        self.assertEqual(f"{sema.dt_of(sema.season_jde(2031, 0)):%Y-%m-%d}", "2031-03-20")  # cədvəldən sonra Meeus

    def _solar(self, date):
        r = self.jpl["solar"]["rows"][date]
        out = []
        for sl, ml in zip(r["sun"], r["moon"]):
            s, m = [float(x) for x in _cells(sl)[3:8]], [float(x) for x in _cells(ml)[3:8]]
            ra1, de1, ra2, de2 = (math.radians(v) for v in (s[0], s[1], m[0], m[1]))
            c = math.sin(de1) * math.sin(de2) + math.cos(de1) * math.cos(de2) * math.cos(ra1 - ra2)
            sep = math.degrees(math.acos(min(1.0, c))) * 3600
            out.append({"t": _jpl_time(_cells(sl)[0]), "sep": sep, "rs": s[4] / 2, "rm": m[4] / 2, "el": s[3],
                        "f": sep - (s[4] + m[4]) / 2})
        return out

    def test_baku_partial_solar_eclipse_2027_from_jpl(self):
        rows = self._solar("2027-08-02")
        loc = next(b for d, *_, b in sema.SOLAR if d == "2027-08-02")
        cross = [(a, b) for a, b in zip(rows, rows[1:]) if (a["f"] > 0) != (b["f"] > 0)]
        self.assertEqual(len(cross), 2)
        c1, c4 = (_root(a["t"], a["f"], b["t"], b["f"]) for a, b in cross)
        self.assertLess(abs((c1 - sema._utc(loc["start"])).total_seconds()), 5)
        self.assertLess(abs((c4 - sema._utc(loc["end"])).total_seconds()), 5)
        i = min(range(len(rows)), key=lambda k: rows[k]["sep"])
        y0, y1, y2 = rows[i - 1]["sep"], rows[i]["sep"], rows[i + 1]["sep"]
        tmax = rows[i]["t"] + datetime.timedelta(seconds=60 * 0.5 * (y0 - y2) / (y0 - 2 * y1 + y2))
        self.assertLess(abs((tmax - sema._utc(loc["max"])).total_seconds()), 10)
        best = rows[i]
        self.assertAlmostEqual((best["rs"] + best["rm"] - best["sep"]) / (2 * best["rs"]), loc["mag"], delta=0.002)
        self.assertTrue(all(r["el"] > 50 for r in rows))  # Günəş bütün tutulma boyu yüksəkdədir

    def test_solar_eclipses_not_seen_from_baku_per_jpl(self):
        for date, *_, baku in sema.SOLAR:
            rows = self._solar(date)
            if baku == "zona":  # ən yaxın an da kontakt yoxdur
                self.assertTrue(all(r["f"] > 0 for r in rows), date)
                self.assertEqual(min(rows, key=lambda r: r["f"]), rows[1], date)
            elif baku == "gecə":  # örtülmə yalnız Günəş üfüqdən aşağı olanda
                over = [r for r in rows if r["f"] < 0]
                self.assertTrue(over and all(r["el"] < -6 for r in over), date)
                self.assertLess(over[-1]["el"], over[0]["el"], date)  # Günəş batmaqdadır

    def test_lunar_eclipse_moon_altitude_from_jpl(self):
        for date, td, typ, mag, region_en, region, alt in sema.LUNAR:
            a, b = self.jpl["lunar"]["rows"][date]
            g = sema._utc(f"{date}T{td}") - datetime.timedelta(seconds=sema.DELTA_T)
            ta, tb = _jpl_time(_cells(a)[0]), _jpl_time(_cells(b)[0])
            ea, eb = float(_cells(a)[4]), float(_cells(b)[4])
            self.assertLess(abs(ea + (eb - ea) * ((g - ta) / (tb - ta)) - alt), 0.2, date)
            self.assertLess(abs(-sema.sun_alt(g) - alt), 3.5, date)  # yerli hesab: Ay Günəşin əks nöqtəsinə yaxındır


class SourceTableTest(unittest.TestCase):
    def test_eclipse_table_matches_nasa_rows(self):
        html = (FIX / "nasa-eclipses-2026-2027.html").read_text(encoding="utf-8")
        for tag, table in (("solar", sema.SOLAR), ("lunar", sema.LUNAR)):
            part = html.split(f'<table class="{tag}">')[1].split("</table>")[0]
            rows = []
            for tr in re.split(r"<tr", part)[1:]:
                cells = [" ".join(re.sub(r"<[^>]+>", " ", c).split()) for c in re.findall(r"<td[^>]*>(.*?)</td>", tr, re.S)]
                y, mon, d = cells[0].split()
                rows.append((f"{y}-{_MON[mon]:02d}-{int(d):02d}", cells[1], cells[2], float(cells[4]), cells[-1]))
            self.assertEqual(rows, [(r[0], r[1], r[2], r[3], r[4]) for r in table], tag)

    def test_meteor_table_matches_imo_calendar(self):
        text = (FIX / "imo-2026-2027.txt").read_text(encoding="utf-8")
        table5, prose = {}, {}
        for line in text.splitlines():
            m = re.match(r"cal(\d{4}) table5 (\w{3}) \| (\w{3} \d\d)–(\w{3}) ?(\d\d) \| (\w{3} \d\d) \| (.+)$", line)
            if m:
                table5[(m.group(2), int(m.group(1)))] = (m.group(3), f"{m.group(4)} {m.group(5)}", m.group(6), m.group(7).split())
            m = re.match(r"cal(\d{4}) text \| (.+)$", line)
            if m:
                prose.setdefault(int(m.group(1)), []).append(m.group(2))
        self.assertEqual(len(table5), 8)
        md = lambda s: (_MON[s[:3]], int(s[-2:]))
        full = ("January", "February", "March", "April", "May", "June", "July", "August", "September", "October",
                "November", "December")
        for row in sema.METEORS:
            m = sema.meteor(row)
            a, b, mx, tok = table5[(m["code"], m["year"])]
            self.assertEqual((md(a), md(b)), ((m["from"].month, m["from"].day), (m["to"].month, m["to"].day)), row)
            day_utc = D.fromisoformat(row[4][:10])
            self.assertEqual(md(mx), (day_utc.month, day_utc.day), row)
            self.assertEqual((int(tok[5].rstrip("+")), tok[5].endswith("+")), (m["zhr"], m["plus"]), row)
            if "T" in row[4]:
                t = sema._utc(row[4])
                want = f"{t.hour:02d} h" + (f" {t.minute:02d} m" if t.minute else "")
                if row[5]:
                    want += f" to {sema._utc(row[5]).hour:02d} h"
                self.assertTrue(any(f"{full[t.month - 1]} {t.day}" in p and want in p for p in prose[m["year"]]), row)

    def test_meteor_night_is_the_evening_before_the_closest_03_00(self):
        for row in sema.METEORS:
            m = sema.meteor(row)
            if not m["max"]:
                self.assertEqual(m["night"], m["max_day"] - datetime.timedelta(days=1))
                continue
            mid = m["max"] + ((m["max_end"] - m["max"]) / 2 if m["max_end"] else datetime.timedelta(0))
            cands = (mid.date() - datetime.timedelta(days=1), mid.date())
            best = min(cands, key=lambda d: abs((sema._at(d + datetime.timedelta(days=1), "03:00") - mid).total_seconds()))
            self.assertEqual(best, m["night"], row)
        self.assertEqual(sorted(sema.SHOWER_NAME), ["ETA", "GEM", "PER", "QUA"])  # yalnız «böyük dördlük»


class MeeusInternalsTest(unittest.TestCase):
    def test_argument_tables_have_25_terms(self):
        args = sema._args_nf(1, 2, 3, 4), sema._args_q(1, 2, 3, 4)
        self.assertEqual([len(a) for a in args] + [len(sema._NEW), len(sema._FULL), len(sema._QUARTER)], [25] * 5)

    def test_meeus_worked_examples(self):
        self.assertAlmostEqual(sema.phase_jde(-283, 0), 2443192.65118, delta=2e-5)   # 49.a
        self.assertAlmostEqual(sema.phase_jde(544, 3), 2467636.49186, delta=2e-5)    # 49.b
        self.assertAlmostEqual(sema.season_jde(1962, 1), 2437837.39245, delta=2e-5)  # 27.a


class MoonPhaseItemTest(unittest.TestCase):
    def test_first_quarter_item(self):
        (item,) = _kind(D(2026, 11, 17), "ay-faza")
        self.assertEqual(item["title"], "Ay bu gün saat 15:48-də birinci rübə çatacaq")
        self.assertEqual(item["lead"], "Hesablamalara görə, Ay 17 noyabrda Bakı vaxtı ilə saat 15:48-də birinci rübə çatacaq.")
        self.assertEqual(item["body"], ["Bədirlənmə: 24 noyabr, saat 18:54", "Son rüb: 1 dekabr, saat 10:09",
                                        "Yeni Ay: 9 dekabr, saat 04:52"])
        self.assertEqual((item["key"], item["slot"], item["topic"], item["worth"], item["list"]),
                         ("sema-ay-2026-11-17-birinci-rub", "08:15", "kosmos", True, True))

    def test_new_moon_and_full_moon_wording(self):
        (new,) = _kind(D(2026, 11, 9), "ay-faza")
        self.assertEqual(new["title"], "Bu gün saat 11:02-də yeni Ay olacaq")
        self.assertEqual(new["lead"], "Hesablamalara görə, 9 noyabrda Bakı vaxtı ilə saat 11:02-də yeni Ay olacaq.")
        (full,) = _kind(D(2026, 11, 24), "ay-faza")
        self.assertEqual(full["title"], "Ay bu gün saat 18:54-də bədirlənəcək")
        self.assertTrue(full["lead"].endswith("Bu, 2026-cı ilin 12-ci bədirlənməsidir."), full["lead"])

    def test_phase_before_publication_is_past_tense(self):
        (item,) = _kind(D(2026, 12, 24), "ay-faza")  # bədir 05:28-də, xəbər 08:15-də
        self.assertEqual(item["title"], "Ay bu gün saat 05:28-də bədirlənib")
        self.assertIn("13-cü bədirlənməsidir", item["lead"])
        late = sema.items(ROOT, _baku(2026, 11, 17, 16, 0))  # dərc gecikib: 15:48 keçib
        self.assertEqual([i["title"] for i in late if i["kind"] == "ay-faza"], ["Ay bu gün saat 15:48-də birinci rübə çatıb"])

    def test_no_phase_no_item(self):
        self.assertEqual(_kind(D(2026, 11, 10), "ay-faza"), [])
        self.assertEqual(sum(len(_kind(D(2026, 11, 1) + datetime.timedelta(days=n), "ay-faza")) for n in range(30)), 4)

    def test_phase_near_midnight_belongs_to_the_rounded_baku_day(self):
        t = datetime.datetime(2026, 1, 1, 19, 59, 45, tzinfo=UTC)  # Bakıda 23:59:45 -> 2 yanvar 00:00
        self.assertEqual(sema.baku_minute(t), _baku(2026, 1, 2, 0, 0))
        fake = lambda a, b: [(2, t)] if a <= t < b else []
        with patch.object(sema, "phases", fake):
            self.assertEqual([x[1] for x in sema.baku_phases(D(2026, 1, 2), 1)], [_baku(2026, 1, 2, 0, 0)])
            self.assertEqual(sema.baku_phases(D(2026, 1, 1), 1), [])

    def test_new_moon_of_a_solar_eclipse_is_not_a_second_item(self):
        (moon,) = _kind(D(2027, 8, 2), "ay-faza")
        self.assertFalse(moon["worth"])
        self.assertIn("tam Günəş tutulması xəbərində var", moon["why"])
        (full,) = _kind(D(2027, 2, 21), "ay-faza")  # yarımkölgəli tutulmanın gecəsi
        self.assertFalse(full["worth"])
        (shallow,) = _kind(D(2027, 7, 18), "ay-faza")  # dayaz tutulma xəbər deyil: bədir xəbəri qalır
        self.assertTrue(shallow["worth"])


class SeasonAndSunsetItemTest(unittest.TestCase):
    def test_winter_solstice_belongs_to_baku_date(self):
        self.assertEqual(_kind(D(2026, 12, 21), "fesil"), [])  # 20:50 UT = 22 dekabr 00:50 Bakı vaxtı
        (item,) = _kind(D(2026, 12, 22), "fesil")
        self.assertEqual(item["title"], "Bu gün saat 00:50-də qış gündönümü olub: Bakıda gündüz 9 saat 18 dəqiqə çəkir")
        self.assertEqual(item["lead"], "Hesablamalara görə, qış gündönümü 22 dekabrda Bakı vaxtı ilə saat 00:50-də olub.")
        self.assertEqual(item["body"], ["Bakıda bu gün Günəş saat 08:00-də doğur, 17:18-də batır; gündüz 9 saat 18 dəqiqə çəkir.",
                                        "Bir həftə sonra, 29 dekabrda gündüz 9 saat 19 dəqiqə çəkəcək."])
        self.assertEqual((item["key"], item["slot"]), ("sema-fesil-2026-qis-gundonumu", "09:30"))

    def test_equinox_and_solstice_wording(self):
        (spring,) = _kind(D(2027, 3, 21), "fesil")
        self.assertEqual(spring["title"], "Bu gün saat 00:25-də yaz bərabərliyi olub: Bakıda gündüz 12 saat 10 dəqiqə çəkir")
        (summer,) = _kind(D(2027, 6, 21), "fesil")
        self.assertEqual(summer["title"], "Bu gün saat 18:11-də yay gündönümü olacaq: Bakıda gündüz 15 saat 4 dəqiqə çəkir")
        (autumn,) = _kind(D(2027, 9, 23), "fesil")  # Meeus 10:01 deyərdi; JPL anı 10:01:44
        self.assertTrue(autumn["title"].startswith("Bu gün saat 10:02-də payız bərabərliyi olacaq"), autumn["title"])

    def test_sunset_crossings(self):
        (up,) = _kind(D(2027, 2, 3), "gun-batimi")
        self.assertEqual(up["slot"], "16:30")
        self.assertEqual(up["title"], "Bakıda Günəş bu gündən etibarən saat 18:00-dən sonra batacaq")
        self.assertEqual(up["lead"], "Hesablamalara görə, Bakıda Günəş bu gün saat 18:01-də batacaq; dünən 17:59-da batmışdı.")
        # Rejimin sonu öz cümləsidir: «Bu, ... davam edəcək» doğma vaxtı və gündüzün uzunluğundan sonra gələndə onlara aid oxunurdu.
        self.assertEqual(up["body"], ["Günəş 15 oktyabradək hər gün saat 18:00-dən sonra batacaq.",
                                      "Bu gün Günəş saat 07:48-də doğur, gündüz 10 saat 13 dəqiqə çəkir."])
        (down,) = _kind(D(2026, 7, 29), "gun-batimi")
        self.assertEqual(down["title"], "Bakıda Günəş bu gündən etibarən saat 20:00-dən əvvəl batacaq")
        self.assertEqual(down["body"][0], "Günəş 2027-ci il 25 mayadək hər gün saat 20:00-dən əvvəl batacaq.")
        (oct26,) = _kind(D(2026, 10, 16), "gun-batimi")
        self.assertEqual(oct26["body"][0], "Günəş 2027-ci il 2 fevraladək hər gün saat 18:00-dən əvvəl batacaq.")
        self.assertFalse(any(p.startswith("Bu, ") for d in (D(2027, 2, 3), D(2026, 7, 29)) for i in _kind(d, "gun-batimi")
                             for p in i["body"]))
        self.assertEqual(_kind(D(2027, 2, 4), "gun-batimi"), [])
        days = [D(2027, 1, 1) + datetime.timedelta(days=n) for n in range(365)]
        found = [(d.isoformat(), i["key"][-2:]) for d in days for i in _kind(d, "gun-batimi")]
        self.assertEqual(found, [("2027-02-03", "18"), ("2027-05-28", "20"), ("2027-07-29", "20"), ("2027-10-17", "18")])


class MeteorItemTest(unittest.TestCase):
    def test_geminids_preview_and_peak(self):
        self.assertEqual(_kind(D(2026, 12, 11), "meteor") + _kind(D(2026, 12, 13), "meteor"), [])
        (pre,) = _kind(D(2026, 12, 12), "meteor")
        self.assertEqual(pre["title"], "Geminid meteor axını 14 dekabrda zirvəyə çatacaq")
        self.assertEqual(pre["lead"], "Beynəlxalq Meteor Təşkilatının (IMO) təqviminə görə, 4–20 dekabr tarixlərində aktiv olan "
                                      "Geminid meteor axını 14 dekabrda Bakı vaxtı ilə saat 18:00 radələrində zirvəyə çatacaq.")
        self.assertEqual(pre["body"], ["IMO-nun proqnozuna görə, zirvədə ZHR göstəricisi (ideal şəraitdə saatda görünə biləcək "
                                       "meteor sayı): 150.", "Hesablamaya görə, zirvə vaxtı Ayın 25%-i işıqlı olacaq.",
                                       "Zirvə vaxtı Bakıda hava qaranlıq olacaq."])  # 18:00, Günəş −8,5°: axşamdır, «gecə» deyil
        self.assertEqual((pre["key"], pre["slot"], pre["credit"], pre["link"]),
                         ("sema-meteor-gem-2026-onizleme", "12:15", "Beynəlxalq Meteor Təşkilatı (IMO)",
                          "https://www.imo.net/files/meteor-shower/cal2026.pdf"))
        (peak,) = _kind(D(2026, 12, 14), "meteor")
        self.assertEqual(peak["title"], "Geminid meteor axını bu gün saat 18:00 radələrində zirvəyə çatacaq")
        self.assertEqual((peak["key"], peak["slot"]), ("sema-meteor-gem-2026-zirve", "17:15"))

    def test_other_big_showers(self):
        (qua,) = _kind(D(2027, 1, 3), "meteor")
        self.assertEqual(qua["title"], "Kvadrantid meteor axını sabah saat 07:25 radələrində zirvəyə çatacaq")
        self.assertIn("28 dekabr – 12 yanvar tarixlərində", qua["lead"])
        self.assertIn("80 (daha çox ola bilər)", qua["body"][0])
        self.assertIn("Ayın 12%-i işıqlı olacaq", qua["body"][1])
        self.assertEqual(qua["body"][2], "Zirvə vaxtı Bakıda hava qaranlıq olacaq.")  # 07:25, Günəş −7,4°: dan yeri, gecə deyil
        (eta,) = _kind(D(2027, 5, 5), "meteor")
        self.assertEqual(eta["title"], "Eta-Akvarid meteor axını sabah saat 13:00 radələrində zirvəyə çatacaq")
        self.assertIn("Ayın işıqlı hissəsi 1%-dən az olacaq", eta["body"][1])
        self.assertEqual(eta["body"][2], "Zirvə vaxtı Bakıda gündüz olacaq.")
        (per,) = _kind(D(2027, 8, 12), "meteor")
        self.assertEqual(per["title"], "Perseid meteor axını sabah saat 12:00–14:00 arasında zirvəyə çatacaq")
        (qua26,) = _kind(D(2026, 1, 3), "meteor")
        self.assertEqual(qua26["title"], "Kvadrantid meteor axını bu gecə saat 01:00 radələrində zirvəyə çatacaq")
        (eta26,) = _kind(D(2026, 5, 5), "meteor")  # IMO yalnız tarix verib
        self.assertEqual(eta26["title"], "Eta-Akvarid meteor axını sabah zirvəyə çatacaq")
        self.assertIn("zirvə günü Ayın 85%-i", eta26["body"][1])

    def test_only_big_four_and_table_years(self):
        found = [i["key"] for y in (2026, 2027) for n in range(365) for i in _kind(D(y, 1, 1) + datetime.timedelta(days=n), "meteor")]
        self.assertEqual(len(found), 16)
        self.assertEqual(_kind(D(2026, 11, 16), "meteor"), [])  # Leonidlər «böyük dördlük»dən deyil
        (note,) = _kind(D(2028, 6, 1), "sema-cedvel")
        self.assertEqual((note["worth"], note["key"]), (False, "sema-cedvel-2028"))
        self.assertIn("2028-ci il", note["why"])

    def test_missing_table_is_flagged_before_the_year_starts(self):
        # 2028-in ilk xəbərləri (Kvadrantidlərin önizləməsi və zirvəsi) 1-3 yanvardadır. Qeyd yalnız 1 yanvarda çıxsaydı,
        # cədvəli əlavə etməyə vaxt qalmazdı: xəbərdarlıq cədvəlin son ilinin 1 noyabrından başlayır.
        self.assertEqual(_kind(D(2027, 10, 31), "sema-cedvel"), [])
        (early,) = _kind(D(2027, 11, 1), "sema-cedvel")
        self.assertEqual((early["worth"], early["key"]), (False, "sema-cedvel-2028"))
        self.assertEqual(early["title"], "2028-ci il üçün meteor və tutulma cədvəli yoxdur")
        self.assertIn("2028-ci il yoxdur", early["why"])
        (late,) = _kind(D(2027, 12, 31), "sema-cedvel")
        self.assertEqual(late["key"], "sema-cedvel-2028")
        self.assertEqual([i["kind"] for i in sema.day_items(D(2027, 12, 14)) if i["worth"]], ["meteor"])  # cədvəl hələ işləyir


class EclipseItemTest(unittest.TestCase):
    def test_partial_solar_eclipse_seen_from_baku(self):
        (pre,) = _kind(D(2027, 7, 31), "tutulma")
        self.assertEqual(pre["title"], "2 avqustda tam Günəş tutulması olacaq: Bakıdan qismən görünəcək")
        (day,) = _kind(D(2027, 8, 2), "tutulma")
        self.assertEqual(day["title"], "Bu gün tam Günəş tutulması olacaq: Bakıdan qismən görünəcək")
        self.assertEqual(day["lead"], "NASA-nın məlumatına görə, 2 avqustda tam Günəş tutulması baş verəcək; tutulmanın Yer "
                                      "kürəsində ən böyük fazası Bakı vaxtı ilə saat 14:07-də olacaq.")
        self.assertEqual(day["body"][:2], ["Bakıda tutulma saat 13:13-də başlayacaq, 14:11-də ən böyük fazaya çatacaq və "
                                           "15:07-də bitəcək.",
                                           "Bakıda tutulmanın maksimal fazası 0,38 olacaq: Günəş diskinin 27%-i örtüləcək."])
        self.assertIn("Səudiyyə Ərəbistanı, Yəmən və Somalidən keçəcək.", day["body"][2])
        self.assertEqual((day["credit"], day["slot"], day["key"]), ("NASA", "08:30", "sema-tutulma-2027-08-02-gunes-gun"))

    def test_eclipses_not_seen_from_baku(self):
        self.assertEqual(_kind(D(2027, 2, 4), "tutulma"), [])  # görünməyən tutulmanın önizləməsi yoxdur
        (ann,) = _kind(D(2027, 2, 6), "tutulma")
        self.assertEqual(ann["title"], "Bu gün həlqəvi Günəş tutulması olacaq: Bakıdan görünməyəcək")
        self.assertIn("Günəş batandan sonra", ann["body"][0])
        (zone,) = _kind(D(2026, 2, 17), "tutulma")
        self.assertEqual(zone["body"][0], "Bakı tutulmanın görünmə zonasından kənardadır.")
        (part,) = _kind(D(2026, 8, 27), "tutulma")  # 28 avqust 08:13-dəki tutulma: xəbər əvvəlki axşam
        self.assertEqual(part["title"], "Sabah qismən Ay tutulması olacaq: ən böyük fazası Bakıdan görünməyəcək")
        self.assertEqual(part["slot"], "18:30")
        self.assertIn("Ən böyük fazada Ay diametrinin 93%-i Yerin tam kölgəsinə girəcək.", part["body"])

    def test_partial_solar_eclipse_has_no_central_path_line(self):
        # Qismən Günəş tutulmasının mərkəzi zolağı yoxdur (NASA cədvəlində mötərizə yoxdur); 2029-da belə dörd tutulma var.
        # Cədvələ əlavə olunanda mərkəzi zolaq None olur: abzasda None və ya boş sətir qalmamalıdır.
        row = ("2029-01-14", "17:13:47", "Partial", 0.871, "N. America, C. America", "Şimali Amerikada və Mərkəzi Amerikada",
               None, "zona")  # NASA SEdecade2021; JPL Horizons: Bakıdan kontakt yoxdur (ən yaxın an 827″ aralı)
        with patch.object(sema, "SOLAR", sema.SOLAR + (row,)):
            (item,) = _kind(D(2029, 1, 14), "tutulma")
            md = "\n".join(ox.render(item))
        self.assertEqual(item["title"], "Bu gün qismən Günəş tutulması olacaq: Bakıdan görünməyəcək")
        self.assertIn("Bakı vaxtı ilə saat 21:13-də olacaq", item["lead"])
        self.assertEqual(item["body"], ["Bakı tutulmanın görünmə zonasından kənardadır.",
                                        "Qismən tutulma Şimali Amerikada və Mərkəzi Amerikada görünəcək.",
                                        "Bakıdan görünmə NASA JPL-in Horizons efemeridləri ilə yoxlanıb."])
        self.assertNotIn("None", md)

    def test_americas_are_both_continents(self):
        # NASA-nın «Americas» sözü Şimali və Cənubi Amerikadır; təkcə «Amerikada» oxucuya ABŞ kimi gələ bilər.
        rows = [(r[4], r[5]) for r in sema.SOLAR] + [(r[4], r[5]) for r in sema.LUNAR]
        for en, az in rows:
            if "Americas" in en:
                self.assertIn("Şimali və Cənubi Amerikada", az, en)
            self.assertFalse(az.startswith("Amerika"), az)
            for word in re.findall(r"(\S+) Amerika", az):
                self.assertIn(word, ("Şimali", "Cənubi"), az)
        (part,) = _kind(D(2026, 8, 27), "tutulma")
        self.assertIn("Tutulma Sakit okeanın şərqində, Şimali və Cənubi Amerikada, Avropada və Afrikada görünəcək.", part["body"])
        (night,) = _kind(D(2027, 2, 20), "tutulma")
        self.assertIn("Tutulma Şimali və Cənubi Amerikada, Avropada, Afrikada və Asiyada görünəcək.", night["body"])

    def test_penumbral_eclipses(self):
        (night,) = _kind(D(2027, 2, 20), "tutulma")
        self.assertEqual(night["title"], "Bu gecə yarımkölgəli Ay tutulması olacaq: Bakıdan görünəcək")
        self.assertEqual(night["body"][0], "Ən böyük faza anında Ay Bakıda üfüqdən təxminən 46° yüksəklikdə olacaq.")
        self.assertIn("saat 03:13-də", night["lead"])
        (pre,) = _kind(D(2027, 2, 18), "tutulma")
        self.assertFalse(pre["worth"])
        (shallow,) = _kind(D(2027, 7, 18), "tutulma")
        self.assertFalse(shallow["worth"])
        self.assertIn("dayaz yarımkölgəli tutulma", shallow["why"])


class LatePublicationTest(unittest.TestCase):
    """Dərc slotdan gec olanda (məsələn, iş saatlarla dayanıb) mətn keçmiş hadisəni gələcək zamanda yazmamalıdır."""

    def test_sunset_after_sunset_is_past_tense(self):
        (late,) = [i for i in sema.items(ROOT, _baku(2027, 2, 3, 19, 0)) if i["kind"] == "gun-batimi"]
        self.assertEqual(late["lead"], "Hesablamalara görə, Bakıda Günəş bu gün saat 18:01-də batıb; dünən 17:59-da batmışdı.")
        (on_time,) = [i for i in sema.items(ROOT, _baku(2027, 2, 3, 9, 0)) if i["kind"] == "gun-batimi"]
        self.assertIn("bu gün saat 18:01-də batacaq;", on_time["lead"])

    def test_eclipse_after_it_began_is_not_published(self):
        (before,) = [i for i in sema.items(ROOT, _baku(2027, 8, 2, 13, 0)) if i["kind"] == "tutulma"]
        self.assertTrue(before["worth"])  # Bakıda tutulma 13:13-də başlayır
        for now in (_baku(2027, 8, 2, 13, 30), _baku(2027, 8, 2, 16, 0)):
            (late,) = [i for i in sema.items(ROOT, now) if i["kind"] == "tutulma"]
            self.assertFalse(late["worth"], now)
            self.assertEqual(late["why"], "gecikmiş xəbər: tutulma artıq başlayıb")
        (hidden,) = [i for i in sema.items(ROOT, _baku(2027, 2, 6, 20, 30)) if i["kind"] == "tutulma"]  # ən böyük faza 20:00
        self.assertFalse(hidden["worth"])
        (night,) = [i for i in sema.items(ROOT, _baku(2027, 2, 20, 23, 0)) if i["kind"] == "tutulma"]  # tutulma 03:13-də
        self.assertTrue(night["worth"])

    def test_morning_solar_eclipse_is_announced_the_evening_before(self):
        # Cədvələ hər il sətir əlavə olunur. NASA SEdecade2021: 2028 Jul 22 02:56:39 TD, tam, UT 02:55:30, Bakıda 06:55 (görünmür).
        # Səhər 08:30-da «Bu gün ... olacaq» yazılsaydı, hadisə artıq keçmiş olardı.
        row = ("2028-07-22", "02:56:39", "Total", 1.056, "SE Asia, E. Indies, Australia, N.Z. [Total: Australia, N. Z.]",
               "Cənub-Şərqi Asiyada, Şərqi Hindistan adalarında, Avstraliyada və Yeni Zelandiyada",
               "Tam tutulma zolağı Avstraliya və Yeni Zelandiyadan keçəcək.", "zona")
        with patch.object(sema, "SOLAR", sema.SOLAR + (row,)):
            self.assertEqual(_kind(D(2028, 7, 22), "tutulma"), [])
            (eve,) = _kind(D(2028, 7, 21), "tutulma")
            (moon,) = _kind(D(2028, 7, 22), "ay-faza")
        self.assertEqual((eve["slot"], eve["worth"]), ("18:30", True))
        self.assertEqual(eve["title"], "Sabah tam Günəş tutulması olacaq: Bakıdan görünməyəcək")
        self.assertIn("Bakı vaxtı ilə saat 06:55-də olacaq", eve["lead"])
        self.assertFalse(moon["worth"])  # yeni Ay həmin tutulmadır


class DayRulesTest(unittest.TestCase):
    def test_daily_cap_of_two_space_items(self):
        fake = [dict(sema.moon_item(0, _baku(2026, 11, 9, 11, 2), [], _baku(2026, 11, 9, 8, 15)), kind="meteor",
                     key=f"x{n}", slot=f"1{n}:00") for n in range(3)]
        with patch.object(sema, "meteor_items", lambda day, now: [dict(f) for f in fake]):
            out = sema.day_items(D(2026, 11, 9))
        self.assertEqual(sum(i["worth"] for i in out), 2)
        dropped = [i for i in out if not i["worth"]]
        self.assertEqual([i["why"] for i in dropped], ["gündə 2 kosmos xəbəri həddi"] * 2)  # yeni Ay və üçüncü meteor

    def test_content_rules_over_two_years(self):
        keys = set()
        counts = {}
        for n in range(730):
            day = D(2026, 1, 1) + datetime.timedelta(days=n)
            out = sema.day_items(day)
            self.assertLessEqual(sum(i["worth"] for i in out), sema.DAY_CAP, day)
            for i in out:
                for k in ("kind", "key", "title", "lead", "body", "credit", "link", "topic", "slot", "worth"):
                    self.assertIn(k, i, (day, i.get("key")))
                if i["kind"] != "sema-cedvel":  # dərc olunmayan cədvəl qeydi hər gün eyni açarla təkrarlanır
                    self.assertNotIn(i["key"], keys)
                    keys.add(i["key"])
                self.assertLessEqual(len(i["title"]), 110, i["title"])
                self.assertFalse(i["title"].endswith("."), i["title"])
                self.assertTrue(re.fullmatch(r"\d\d:\d\d", i["slot"]), i)
                self.assertEqual(i["topic"], "kosmos")
                if not i["worth"]:
                    self.assertTrue(i.get("why"), i["key"])
                text = " ".join([i["title"], i["lead"], *i["body"]])
                self.assertIsNone(re.search(r"[А-Яа-яЁё]|Prezident|vitse-prezident|Əliyev|Mehriban|  ", text), text)
                self.assertIsNone(re.search(r"\d\.\d", text), text)  # onluq kəsr vergüllə yazılır
                if i["worth"]:
                    counts[i["kind"]] = counts.get(i["kind"], 0) + 1
        self.assertEqual((counts["fesil"], counts["gun-batimi"], counts["meteor"]), (8, 8, 16))
        self.assertTrue(85 <= counts["ay-faza"] <= 99, counts)
        self.assertEqual(counts["tutulma"], 8)

    def test_percent_rounds_half_up(self):
        # Python-un round() funksiyası yarımı cüt ədədə yuvarlayır (86,5 -> 86, 12,5 -> 12). NASA maqnitudaları üç rəqəmlidir:
        # 0,865 kimi dəyər faizdə yarım verir və adi qaydaya görə yuxarı yuvarlanmalıdır.
        self.assertEqual([sema._pct(x) for x in (0.865, 0.125, 0.269, 0.93, 0.0249, 0.5)],
                         ["87%", "13%", "27%", "93%", "2%", "50%"])

    def test_no_network_and_cli(self):
        def boom(*a, **k):
            raise AssertionError("şəbəkə sorğusu olmamalıdır")
        with patch("urllib.request.urlopen", boom), patch.object(ox, "_u", boom):
            got = sema.items(ROOT, _baku(2026, 11, 17, 9, 0), fetch=boom)
            md = sema.sinaq(ROOT, _baku(2026, 11, 10, 9, 0), fetch=boom)
            buf = io.StringIO()
            with redirect_stdout(buf):
                self.assertEqual(sema.main(["--sinaq", "--root", str(ROOT), "--now", "2026-11-10T09:00+04:00"]), 0)
        self.assertEqual([i["key"] for i in got], ["sema-ay-2026-11-17-birinci-rub"])
        text = "\n".join(md)
        for part in ("## Ay fazaları", "## Gündönümü və bərabərlik", "## Bakıda gün batımı", "## Meteor axınları",
                     "## Tutulmalar", "Sonuncu real hal", "Növbəti hal", "✅ Dərc olunardı", "⏭ Dərc olunmazdı",
                     "Bakıdan görünən tutulma"):
            self.assertIn(part, text)
        self.assertIn("> 10 noyabr üçün səma xəbəri yoxdur.", text)
        self.assertIn("## Səma xəbərləri: sınaq", buf.getvalue())


if __name__ == "__main__":
    unittest.main()
