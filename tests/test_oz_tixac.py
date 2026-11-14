"""oz_tixac: pik saat tıxac bülletenləri (sahib, 2026-11-14: «2 öz xəbərimizi geniş edək», «səkkiz əsas yol üzrə»)."""
import datetime
import json
import pathlib
import sys
import unittest

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import oz_derc  # noqa: E402
import oz_tixac as ot  # noqa: E402
import oz_xeber as ox  # noqa: E402

BAKU = ot.BAKU
WATCH = ["Moskva prospekti", "Heydər Əliyev prospekti", "Ziya Bünyadov prospekti", "Tbilisi prospekti", "Babək prospekti",
         "Neftçilər prospekti", "Binəqədi şosesi", "Koroğlu Rəhimov küçəsi"]


def at(day, h, m):
    return datetime.datetime(day.year, day.month, day.day, h, m, tzinfo=BAKU)


def snaps_for(day, h0, h1, jam=None, extra=0, incident_at=None):
    """h0:00–h1:00 arası hər 6 dəqiqə; jam: (ad, başlanğıc dəqiqə, son dəqiqə, km)."""
    out, t = [], at(day, h0, 0)
    while t <= at(day, h1, 0):
        mins = (t - at(day, h0, 0)).seconds // 60
        w = []
        for name in WATCH:
            level, km = "serbest", "0,0"
            if jam and name == jam[0] and jam[1] <= mins <= jam[2]:
                level, km = "tixac", jam[3]
            w.append([name, level, km])
        hot = jam and jam[1] <= mins <= jam[2]
        out.append({"t": int(t.timestamp() * 1000), "r": [["simal", 40 + (15 if hot else 0) + extra, 38], ["aeroport", 41 + extra, 39],
                                                          ["qerb", 30 + extra, 28], ["cenub", 35 + extra, 33]],
                    "s": [], "w": w, "i": ["Qəza: Babək prospekti."] if incident_at and mins == incident_at else []})
        t += datetime.timedelta(minutes=6)
    return out


class Fetch:
    def __init__(self, snaps):
        self.doc, self.calls = json.dumps({"snaps": snaps}).encode("utf-8"), 0

    def __call__(self, url, *a, **k):
        self.calls += 1
        assert url.startswith(ot.TARIX_URL)
        return self.doc


class BulletinTest(unittest.TestCase):
    MON = datetime.date(2026, 11, 16)

    def data(self):
        y = self.MON - datetime.timedelta(days=1)
        return snaps_for(y, 7, 9) + snaps_for(self.MON, 7, 9, jam=("Moskva prospekti", 30, 90, "2,4"), extra=3, incident_at=42)

    def test_morning_bulletin_names_the_worst_road_lists_all_eight_and_compares_with_yesterday(self):
        f = Fetch(self.data())
        got = ot.items(None, at(self.MON, 8, 50), fetch=f)
        self.assertEqual(f.calls, 1)
        self.assertEqual(len(got), 1)
        b = got[0]
        self.assertEqual(b["key"], "tixac-seher-2026-11-16"); self.assertTrue(b["worth"], b.get("why"))
        self.assertEqual(b["title"], "Səhər pik saatı: Bakıda Moskva prospekti tıxacdadır")
        self.assertLessEqual(len(b["title"]), ot.TITLE_MAX)
        self.assertIn("Moskva prospekti üzərində olub: 2,4 km, təxminən", b["lead"])
        self.assertIn("saat 07:00–08:45 arası şəhərə doğru", b["lead"])
        body = "\n".join(b["body"])
        for name in WATCH:
            self.assertIn(name + ":", body, "səkkiz yolun hamısı")
        self.assertIn("Moskva prospekti: indi hərəkət sərbəstdir; pik ərzində tıxac, təxminən 6", body)
        self.assertIn("Bakı–Sumqayıt yolundan Tbilisi prospektinə: indi 43 dəq, adi halda 38 dəq; ən uzunu 58 dəq (saat 07:30)", body)
        self.assertIn("Qəza: Babək prospekti.", body)
        self.assertIn("Dünənin eyni saatları ilə müqayisədə marşrutlar orta hesabla", body)
        self.assertIn("rəsmi məlumat deyil", body)
        self.assertEqual(b["link"], ot.PAGE); self.assertEqual(oz_derc.BOLME_NOV[b["kind"]], "cemiyyet")
        self.assertFalse(ox.needs_owner("\n".join([b["title"], b["lead"], *b["body"]])), "«Heydər Əliyev prospekti» küçə adıdır, rəhbərlik qaydasına düşmür")

    def test_no_request_outside_the_window_or_after_publishing(self):
        f = Fetch(self.data())
        self.assertEqual(ot.items(None, at(self.MON, 8, 30), fetch=f), [])
        self.assertEqual(ot.items(None, at(self.MON, 12, 0), fetch=f), [])
        self.assertEqual(ot.items(None, at(self.MON, 8, 50), fetch=f, done={"tixac-seher-2026-11-16"}), [])
        self.assertEqual(f.calls, 0)

    def test_stale_or_thin_data_waits_then_gives_up_at_the_end_of_the_window(self):
        thin = snaps_for(self.MON, 7, 8)   # son ölçü 08:00
        self.assertEqual(ot.items(None, at(self.MON, 8, 50), fetch=Fetch(thin)), [], "ölçü təzə deyil: gözləyir")
        late = ot.items(None, at(self.MON, 9, 55), fetch=Fetch(thin))
        self.assertEqual([(i["key"], i["worth"]) for i in late], [("tixac-seher-2026-11-16", False)])

    def test_evening_and_weekend(self):
        mon_eve = snaps_for(self.MON, 17, 19, jam=("Heydər Əliyev prospekti", 0, 100, "3,1"))
        b = ot.items(None, at(self.MON, 18, 50), fetch=Fetch(mon_eve))[0]
        self.assertEqual(b["key"], "tixac-axsam-2026-11-16"); self.assertIn("şəhərdən çıxış", b["lead"])
        self.assertIn("Gənclikdən Heydər Əliyev prospekti ilə aeroport yoluna", "\n".join(b["body"]))
        self.assertTrue(b["worth"], b.get("why"))
        sat = datetime.date(2026, 11, 21)
        quiet = ot.items(None, at(sat, 8, 50), fetch=Fetch(snaps_for(sat, 7, 9)))[0]
        self.assertFalse(quiet["worth"]); self.assertEqual(quiet["why"], "həftə sonu, tıxac yoxdur")
        self.assertEqual(quiet["title"], "Səhər pik saatı: Bakının səkkiz əsas yolunda ciddi tıxac yoxdur")
        weekday_quiet = ot.items(None, at(self.MON, 8, 50), fetch=Fetch(snaps_for(self.MON, 7, 9)))[0]
        self.assertTrue(weekday_quiet["worth"], "iş günü «tıxac yoxdur» da xəbərdir")

    def test_network_error_returns_nothing(self):
        def broken(url, *a, **k):
            raise OSError("şəbəkə")
        self.assertEqual(ot.items(None, at(self.MON, 8, 50), fetch=broken), [])

    def test_wired_into_own_news(self):
        self.assertIn("oz_tixac", [n for n, _ in ox.FAZA3])
        self.assertEqual(oz_derc.QAYDA["oz_tixac"]["done"], "hamisi")
        self.assertEqual(oz_derc.ONCELIK["oz_tixac"][0], 3)
        self.assertIn("oz_tixac.py", (ROOT / ".github" / "scripts" / "pipeline.sh").read_text(encoding="utf-8"))
        js = (ROOT / ".github" / "scripts" / "tixac.cjs").read_text(encoding="utf-8")
        for name in WATCH:
            self.assertIn(f'"{name}"', js, "bülletenin səkkiz yolu ölçünün WATCH siyahısındadır")


class StaticPageTest(unittest.TestCase):
    """«Bakıda tıxac indi» (bolme/tixac/): Google-un oxuduğu mətn — səkkiz yol və avtomatik xəbərlər; köhnə ölçü yazılmır."""

    def test_status_block(self):
        import updater
        now = datetime.datetime(2026, 11, 16, 5, 0, tzinfo=datetime.timezone.utc).timestamp()
        doc = {"updatedAt": "2026-11-16T04:54:00+00:00", "watch": [["Moskva prospekti", "tixac", "2,4"], ["Babək prospekti", "serbest", "0,0"]],
               "events": [{"t": int((now - 600) * 1000), "text": "Moskva prospekti (şəhərə doğru): tıxac, <b>2,4</b> km."}]}
        html = updater.tixac_status(doc, now)
        self.assertIn("<h2>Səkkiz əsas yolun vəziyyəti (08:54)</h2>", html)
        self.assertIn("<td>Moskva prospekti</td><td>tıxac</td><td>2,4 km</td>", html)
        self.assertIn("<td>Babək prospekti</td><td>hərəkət sərbəstdir</td><td></td>", html)
        self.assertIn("08:50 — Moskva prospekti (şəhərə doğru): tıxac, &lt;b&gt;2,4&lt;/b&gt; km.", html, "mətn qaçırılır")
        self.assertEqual(updater.tixac_status(doc, now + 4 * 3600), "", "3 saatdan köhnə ölçü yazılmır")
        self.assertEqual(updater.tixac_status({}, now), "")
        self.assertIn(("tixac", "Bakıda tıxac indi"), [(s, l) for s, l, _ in updater.SERVICE_PAGES])


if __name__ == "__main__":
    unittest.main()
