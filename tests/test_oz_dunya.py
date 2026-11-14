"""Dünyadan xəbərlər (oz_dunya.py): növbə faylının qapıları (qırmızı xətt 4), vaxt pəncərəsi və dərc hissəsi ilə uyğunluq.
Şəbəkə yoxdur: modul yalnız fayl oxuyur. Repodakı növbə faylının (oz_dunya.json) hər sətri də burada yoxlanır."""
import datetime
import html
import io
import json
import pathlib
import tempfile
import unittest
from contextlib import redirect_stdout

import oz_derc as d
import oz_dunya as dn
import oz_xeber as ox

ROOT = pathlib.Path(__file__).resolve().parent.parent
BAKU = ox.BAKU
ON = {"OZ_DERC": "1"}
DAY = datetime.timedelta(days=1)


def at(day, h=12, m=0):
    return datetime.datetime(2026, 11, day, h, m, tzinfo=BAKU)


def no_net(url, **kw):
    raise OSError("şəbəkə yoxdur")


def row(**kw):
    base = {"id": "sinaq-xeber", "date": "2026-11-13", "slot": "10:20", "kind": "dunya-kosmos",
            "title": "Zond asteroidi 56 kilometr məsafədən çəkib",
            "lead": "Avropa Kosmik Agentliyinin zondu asteroidin yeni şəklini 56 kilometr məsafədən çəkib. Bu barədə agentlik məlumat yayıb.",
            "body": ["Asteroidin diametri 780 metrdir, onun peyki isə 151 metrlikdir."],
            "credit": "Avropa Kosmik Agentliyi (ESA)", "link": "https://www.esa.int/articles/x", "image": "",
            "src": ["Acquired from 56 km away, this image shows the 780-m-diameter asteroid and its 151-m-diameter moonlet."]}
    base.update(kw)
    return base


class Tmp(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.tmp = pathlib.Path(tmp.name)

    def queue(self, rows, v=1, name="novbe.json"):
        path = self.tmp / name
        path.write_text(json.dumps({"v": v, "items": rows}, ensure_ascii=False), encoding="utf-8")
        return path


class NumbersTest(unittest.TestCase):
    def test_english_numbers_take_the_same_form_as_azerbaijani_ones(self):
        text = "enrolled 12,327 adults; 25.9 billion kilometers; 10 000 km of space; November 09; down to -120°C; 1,625 km coastline; almost 300 km2"
        self.assertEqual(dn.en_nums(text), {"12327", "25.9", "10000", "9", "120", "1625", "300", "2"})
        self.assertEqual(ox._nums("12 327 böyük; 25,9 milyard; 10 000 kilometr; noyabrın 9-da; mənfi 120; 1625 kilometr; 300 kvadrat"),
                         {"12327", "25.9", "10000", "9", "120", "1625", "300"})
        self.assertEqual(dn.en_nums("Nov. 18 2026 and 2,2"), {"18", "2026", "2"}, "gün və il birləşmir; vergüllü kəsr ingiliscə deyil")

    def test_a_number_that_is_not_in_the_source_excerpts_blocks_the_row(self):
        self.assertIsNone(dn.check(row()))
        why = dn.check(row(body=["Asteroidin diametri 790 metrdir, onun peyki isə 151 metrlikdir."]))
        self.assertEqual(why, "mətndəki rəqəm mənbə çıxarışında yoxdur: 790")
        why = dn.check(row(title="Zond asteroidi 65 kilometr məsafədən çəkib"))
        self.assertEqual(why, "mətndəki rəqəm mənbə çıxarışında yoxdur: 65")
        # Yuvarlaqlaşdırma və vahid çevirmə də rəddir: mənbədə 2.2 var, 2 yoxdur.
        src = ["The asteroid rotates every 2.2 hours and is 56 km away, 780-m and 151-m wide."]
        self.assertIsNone(dn.check(row(body=["Asteroid öz oxu ətrafında 2,2 saata bir dövr edir, diametri 780 metrdir."], src=src)))
        self.assertEqual(dn.check(row(body=["Asteroid öz oxu ətrafında 2 saata bir dövr edir, diametri 780 metrdir."], src=src)),
                         "mətndəki rəqəm mənbə çıxarışında yoxdur: 2")

    def test_thousands_and_decimals_match_across_the_two_notations(self):
        src = ["The study enrolled 12,327 adults over a median treatment of 14.2 months, 56 km, 780 and 151."]
        body = ["Tədqiqatda 12 327 böyük iştirak edib, müalicənin median müddəti 14,2 ay olub."]
        self.assertIsNone(dn.check(row(body=body, src=src)))
        self.assertEqual(dn.check(row(body=[body[0].replace("12 327", "12 372")], src=src)), "mətndəki rəqəm mənbə çıxarışında yoxdur: 12372")


class GateTest(unittest.TestCase):
    def bad(self, start, **kw):
        why = dn.check(row(**kw))
        self.assertIsNotNone(why, kw)
        self.assertTrue(why.startswith(start), f"{kw}: {why}")

    def test_good_row_and_item(self):
        r = row(image="https://www.nasa.gov/wp-content/uploads/2026/11/x.jpg")
        self.assertIsNone(dn.check(r))
        it = dn.item(r, datetime.date(2026, 11, 14))
        self.assertEqual(it["key"], "dunya-sinaq-xeber")
        self.assertEqual((it["kind"], it["topic"], it["slot"], it["date"], it["worth"]), ("dunya-kosmos", "kosmos", "10:20", "2026-11-14", True))
        self.assertEqual(it["credit"], "Avropa Kosmik Agentliyi (ESA)")
        self.assertEqual(it["image"], "https://www.nasa.gov/wp-content/uploads/2026/11/x.jpg")
        self.assertNotIn("src", it, "mənbə çıxarışları dərc olunmur")

    def test_id_dates_slot_kind(self):
        for ident in ("Böyük", "ab", "x--y", "-x", "x-", "a" * 61, 5, None):
            self.bad("id yararsızdır", id=ident)
        for kw in ({"date": "13.11.2026"}, {"date": ""}, {"until": "2026-11-12"}, {"until": "2026-11-17"}, {"until": "sabah"}):
            self.bad("date / until", **kw)
        self.assertIsNone(dn.check(row(until="2026-11-16")), "ən çoxu date + 3 gün")
        self.assertEqual(dn.window(row()), (datetime.date(2026, 11, 13), datetime.date(2026, 11, 14)), "until yazılmasa date + 1 gün")
        for slot in ("25:00", "06:59", "23:00", "9:30", "", None):
            self.bad("slot yararsızdır", slot=slot)
        self.bad("növ cədvəldə yoxdur", kind="dunya-siyaset")
        self.assertEqual(set(dn.NOVLER.values()), {"kosmos", "elm", "sağlamlıq", "təbiət", "texnologiya", "dünya"})

    def test_lengths_and_marks(self):
        self.bad("başlığın uzunluğu", title="Zond asteroidi çəkib")
        self.bad("başlığın uzunluğu", title="Zond asteroidi 56 kilometr məsafədən çəkib " + "və " * 30)
        self.bad("başlıq nöqtə", title="Zond asteroidi 56 kilometr məsafədən çəkib.")
        self.bad("başlıq nöqtə", title="Zond asteroidi 56 kilometr məsafədən çəkibmi?")
        self.bad("girişin uzunluğu", lead="Zond asteroidi 56 kilometrdən çəkib.")
        self.bad("mətn 1–6", body=[])
        self.bad("mətn 1–6", body="Asteroidin diametri 780 metrdir, onun peyki isə 151 metrlikdir.")
        self.bad("mətn 1–6", body=["Asteroidin diametri 780 metrdir, onun peyki isə 151 metrlikdir.", "  "])
        self.bad("mətn 1–6", body=["Asteroidin diametri 780 metrdir, onun peyki isə 151 metrlikdir."] * 7)
        self.bad("abzasın uzunluğu", body=["Diametri 780 metrdir."])
        self.bad("kiril hərfi", body=["Asteroidin диаметри 780 metrdir, onun peyki isə 151 metrlikdir."])
        self.bad("nida işarəsi", body=["Asteroidin diametri 780 metrdir, onun peyki isə 151 metrlikdir!"])
        self.bad("nida işarəsi", body=["Asteroidin diametri 780 metrdir, ətraflı: https://www.esa.int/articles/x ünvanında."])

    def test_relative_day_words_are_refused(self):
        for phrase in ("Bu gün zond", "Dünən zond", "Sabah zond", "bugün zond", "dünənki şəkildə zond", "Bu günə qədər zond", "Bu səhər zond"):
            self.bad("nisbi gün sözü", body=[f"{phrase} asteroidin 780 metrlik gövdəsini və 151 metrlik peykini çəkib."])
        ok = "Bu Günəş sistemində 780 metrlik asteroidin 151 metrlik peyki var, sabahlar orada qısadır."
        self.assertIsNone(dn.check(row(body=[ok])), "«bu Günəş» və «sabahlar» nisbi gün deyil")

    def test_source_site_credit_and_image(self):
        for link in ("https://example.org/x", "http://www.esa.int/articles/x", "https://esa.int.evil.org/x", "https://evilesa.int/x", "", None):
            self.bad("mənbə saytı cədvəldə yoxdur", link=link)
        self.assertIsNone(dn.check(row(link="https://esa.int/x")))
        self.bad("credit cədvəldəki ad olmalıdır: Avropa Kosmik Agentliyi (ESA)", credit="ESA")
        self.bad("credit cədvəldəki ad olmalıdır: NASA", link="https://science.nasa.gov/x")
        self.assertIsNone(dn.check(row(link="https://science.nasa.gov/x", credit="NASA")))
        for image in ("https://www.esa.int/var/x.jpg", "http://www.nasa.gov/x.jpg", "https://nasa.gov.evil.org/x.jpg",
                      "https://www.nasa.gov/scotland’s.jpg", "https://www.nasa.gov/a b.jpg"):
            self.bad("şəkil saytı", image=image)
        self.assertIsNone(dn.check(row(image="https://assets.science.nasa.gov/content/x%E2%80%99s.jpg/jcr:content/renditions/a.jpeg")))
        for site, name in dn.MENBELER.items():
            self.assertTrue(name and len(name) <= dn.CREDIT_MAX and site == site.lower(), site)
        self.assertEqual(dn.SEKIL_SAYTLARI, ("nasa.gov",), "şəkil yalnız şərtsiz istifadə olunan mənbədən")

    def test_source_excerpts_are_required(self):
        for src in (None, [], "Acquired from 56 km away", ["qısa"], ["x" * 501], [5], ["Acquired from 56 km away, 780 and 151."] * 13):
            self.bad("src:", src=src)

    def test_leadership_is_never_published_from_the_queue(self):
        why = dn.check(row(body=["Prezident İlham Əliyev 780 metrlik asteroidin və onun 151 metrlik peykinin şəklinə baxıb."]))
        self.assertEqual(why, "rəhbərliyin adı keçir: bu növbə ilə verilmir")


class WindowTest(Tmp):
    def test_item_comes_on_its_days_only_and_once(self):
        path = self.queue([row()])
        self.assertEqual(dn.items(self.tmp, at(12), path=path), [], "gündən əvvəl yox")
        first = dn.items(self.tmp, at(13, 9), path=path)
        self.assertEqual([(i["key"], i["date"], i["slot"], i["worth"]) for i in first], [("dunya-sinaq-xeber", "2026-11-13", "10:20", True)])
        late = dn.items(self.tmp, at(14, 23, 30), path=path)
        self.assertEqual([(i["key"], i["date"]) for i in late], [("dunya-sinaq-xeber", "2026-11-14")], "fayl gec çatsa ertəsi gün də verilir")
        self.assertEqual(dn.items(self.tmp, at(15), path=path), [], "until keçəndən sonra yox")
        self.assertEqual(dn.items(self.tmp, at(13), done={"dunya-sinaq-xeber"}, path=path), [], "done-dakı açar qayıtmır")
        naive = datetime.datetime(2026, 11, 13, 9, 0)
        self.assertEqual(len(dn.items(self.tmp, naive, path=path)), 1, "saat qurşaqsız vaxt Bakı vaxtı sayılır")
        utc = datetime.datetime(2026, 11, 12, 21, 0, tzinfo=datetime.timezone.utc)
        self.assertEqual(len(dn.items(self.tmp, utc, path=path)), 1, "UTC 21:00 Bakıda ertəsi gündür")

    def test_bad_rows_come_back_as_not_worth_inside_their_window(self):
        rows = [row(id="pis-reqem", title="Zond asteroidi 65 kilometr məsafədən çəkib", slot="09:00"),
                row(id="yaxsi", slot="18:00"), row(id="yaxsi", slot="11:00"), row(id="Yararsız id"), "sətir deyil",
                row(id="sabahki", date="2026-11-20", title="Zond asteroidi 65 kilometr məsafədən çəkib")]
        got = dn.items(self.tmp, at(13), path=self.queue(rows))
        self.assertEqual([(i["key"], i["worth"], i["slot"]) for i in got], [("dunya-pis-reqem", False, "09:00"), ("dunya-yaxsi", True, "18:00")],
                         "təkrar id-nin ikinci sətri qayıtmır, birincisi dərc olunur")
        self.assertEqual(got[0]["why"], "mətndəki rəqəm mənbə çıxarışında yoxdur: 65")
        self.assertEqual(got[0]["body"], [], "dərc olunmayan nəticədə mətn yoxdur")
        states = [(r["id"], why) for r, why in dn.rows(self.queue(rows))]
        self.assertEqual(states, [("pis-reqem", "mətndəki rəqəm mənbə çıxarışında yoxdur: 65"), ("yaxsi", None), ("yaxsi", "id təkrarlanır"),
                                  ("sabahki", "mətndəki rəqəm mənbə çıxarışında yoxdur: 65")], "id-siz sətir sayılmır")

    def test_items_are_sorted_by_slot(self):
        rows = [row(id="uc", slot="19:05"), row(id="bir", slot="08:10"), row(id="iki", slot="12:00")]
        self.assertEqual([i["key"] for i in dn.items(self.tmp, at(13), path=self.queue(rows))], ["dunya-bir", "dunya-iki", "dunya-uc"])

    def test_missing_or_broken_file_gives_nothing(self):
        self.assertEqual(dn.items(self.tmp, at(13), path=self.tmp / "yoxdur.json"), [])
        broken = self.tmp / "pozuq.json"
        broken.write_text("{\"v\": 1, \"items\": [", encoding="utf-8")
        self.assertEqual(dn.items(self.tmp, at(13), path=broken), [])
        self.assertEqual(dn.items(self.tmp, at(13), path=self.queue([row()], v=2)), [], "başqa versiya oxunmur")
        other = self.tmp / "siyahi.json"
        other.write_text("[1, 2]", encoding="utf-8")
        self.assertEqual(dn.items(self.tmp, at(13), path=other), [])
        self.assertEqual(dn.load(self.queue({"a": 1})), [], "items siyahı deyil")

    def test_sinaq_and_cli(self):
        rows = [row(), row(id="pis-reqem", title="Zond asteroidi 65 kilometr məsafədən çəkib"), row(id="kohne", date="2026-11-01")]
        md = "\n".join(dn.sinaq(self.tmp, at(13), path=self.queue(rows)))
        self.assertIn("### Zond asteroidi 56 kilometr məsafədən çəkib", md)
        self.assertIn("Mənbə: [Avropa Kosmik Agentliyi (ESA)](https://www.esa.int/articles/x)", md)
        self.assertIn("> **Dərc olunmur** (dunya-pis-reqem): mətndəki rəqəm mənbə çıxarışında yoxdur: 65", md)
        self.assertIn("| sinaq-xeber | 13.11–14.11 | 10:20 | dunya-kosmos | növbədə |", md)
        self.assertIn("| kohne | 01.11–02.11 | 10:20 | dunya-kosmos | keçib |", md)
        self.assertNotIn("Acquired from", md, "çıxarışlar sınaqda da göstərilmir")
        empty = "\n".join(dn.sinaq(self.tmp, at(13), path=self.tmp / "yoxdur.json"))
        self.assertIn("növbədə xəbər yoxdur", empty)
        self.assertIn("| (boşdur) |", empty)
        out = io.StringIO()
        with redirect_stdout(out):
            self.assertEqual(dn.main(["--sinaq", "--root", str(self.tmp), "--now", "2026-11-13T12:00+04:00"]), 0)
        self.assertIn("## Dünyadan xəbərlər: sınaq", out.getvalue())
        out = io.StringIO()
        with redirect_stdout(out):
            self.assertEqual(dn.main([]), 0)
        self.assertIn("Növbə faylı", out.getvalue())


class RealQueueTest(Tmp):
    """Repodakı oz_dunya.json: hər yeni dəst bu testlərdən keçməlidir."""

    def setUp(self):
        super().setUp()
        reg = d.registered()
        reg.__enter__()
        self.addCleanup(reg.__exit__, None, None, None)
        self.rows = dn.rows()

    def test_file_is_valid_and_every_row_passes_the_gates(self):
        doc = json.loads(dn.NOVBE.read_text(encoding="utf-8"))
        self.assertEqual(doc.get("v"), 1)
        self.assertEqual(len(self.rows), len(doc["items"]), "hər sətrin yararlı id-si var")
        self.assertEqual(len({r["id"] for r, _ in self.rows}), len(self.rows), "id təkrarlanmır")
        for r, why in self.rows:
            self.assertIsNone(why, r["id"])
            self.assertLessEqual(len(r["src"]), dn.SRC_MAX)

    def test_every_row_passes_the_publisher_gate_and_renders(self):
        for r, _ in self.rows:
            start, _until = dn.window(r)
            it = dn.item(r, start)
            h, m = r["slot"].split(":")
            line = d.row(it, datetime.datetime.combine(start, datetime.time(int(h), int(m)), BAKU))
            self.assertIsNone(d.gate(it, line), r["id"])
            self.assertEqual(line["source"], ox.SOURCE)
            self.assertIn(line["category"], {"tehsil", "heyat", "dunya"}, r["id"])
            self.assertEqual(line["imageUrl"], it["image"] or None, "şəkil ünvanı məzmun siyasətindən keçir")
            page = d.page(it, line)
            self.assertIn(f"<h1>{html.escape(it['title'], quote=True)}</h1>", page)
            self.assertIn(f'<a href="{html.escape(it["link"], quote=True)}" rel="noopener">{html.escape(it["credit"], quote=True)}</a>', page)
            for s in r["src"]:
                self.assertNotIn(html.escape(s, quote=True)[:60], page, "çıxarış səhifəyə düşmür")

    def test_first_day_of_the_queue_goes_out_through_the_publisher(self):
        if not self.rows:
            self.skipTest("növbə boşdur")
        day = min(dn.window(r)[0] for r, _ in self.rows)
        todays = sorted((r for r, _ in self.rows if dn.window(r)[0] == day), key=lambda r: r["slot"])
        published = []
        for r in todays:
            h, m = r["slot"].split(":")
            now = datetime.datetime.combine(day, datetime.time(int(h), int(m)), BAKU) + datetime.timedelta(minutes=5)
            res = d.cycle(self.tmp, now, fetch=no_net, env=ON, mods=[("oz_dunya", dn)])
            self.assertEqual(res["errors"], [], r["id"])
            self.assertEqual(res["blocked"], [], r["id"])
            published += [p["title"] for p in res["published"]]
        self.assertTrue(published, "ən azı bir xəbər dərc olunur")
        for r in todays:
            out = dn._line(r["title"]) in published
            if out:
                page = self.tmp / "xeber" / d.item_id(dn.KEY + r["id"]) / "index.html"
                self.assertTrue(page.exists(), r["id"])
                self.assertIn(html.escape(dn._line(r["title"]), quote=True), page.read_text(encoding="utf-8"))
        rows = json.loads((self.tmp / "data" / "oz" / "xeberler.json").read_text(encoding="utf-8"))
        rows = rows.get("articles", rows) if isinstance(rows, dict) else rows
        self.assertEqual(len(rows), len(published))
        again = d.cycle(self.tmp, datetime.datetime.combine(day, datetime.time(23, 50), BAKU), fetch=no_net, env=ON, mods=[("oz_dunya", dn)])
        self.assertEqual([p["title"] for p in again["published"] if p["title"] in published], [], "eyni xəbər ikinci dəfə dərc olunmur")


class TablesTest(unittest.TestCase):
    def test_module_is_in_the_publisher_tables(self):
        self.assertIn(("oz_dunya", "Dünyadan: əvvəlcədən yazılmış xəbərlərin növbəsi"), ox.FAZA3)
        self.assertIn("oz_dunya", d.modules())
        self.assertEqual(d.QAYDA["oz_dunya"], {"done": "hamisi", "gelecek": "vaxtinda", "sorgu": 0})
        self.assertEqual(d.priority("oz_dunya", {"kind": "dunya-kosmos"}), 2)
        want = {"dunya-kosmos": "tehsil", "dunya-elm": "tehsil", "dunya-saglamliq": "heyat", "dunya-tebiet": "dunya",
                "dunya-texno": "tehsil", "dunya-maraqli": "dunya"}
        self.assertEqual({k: d.category({"kind": k, "topic": t}) for k, t in dn.NOVLER.items()}, want)
        sh = (ROOT / ".github" / "scripts" / "pipeline.sh").read_text(encoding="utf-8")
        line = [l for l in sh.splitlines() if "oz_dunya" in l]
        self.assertEqual(len(line), 1)
        self.assertTrue(line[0].startswith("CODE_FILES=") and "oz_dunya.py oz_dunya.json" in line[0], "modul və növbə faylı birlikdə köçürülür")
        self.assertEqual(dn.NOVBE, ROOT / "oz_dunya.json")

    def test_module_sends_no_requests(self):
        src = (ROOT / "oz_dunya.py").read_text(encoding="utf-8")
        self.assertNotIn("urlopen", src)
        self.assertNotIn("fetch(", src, "sorğu funksiyası heç vaxt çağırılmır")
        calls = []
        dn.items(ROOT, at(13), fetch=lambda *a, **k: calls.append(a))
        self.assertEqual(calls, [])


if __name__ == "__main__":
    unittest.main()
