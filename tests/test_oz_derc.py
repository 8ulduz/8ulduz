"""Dərc hissəsinin (oz_derc.py) testləri. Şəbəkə yoxdur: modullar saxtadır (mods=), sorğu funksiyası saxtadır."""
import contextlib
import datetime
import hashlib
import io
import json
import os
import pathlib
import re
import sys
import tempfile
import unittest
from types import SimpleNamespace
from unittest.mock import patch

import content_policy
import oz_derc as d
import oz_xeber as ox
import updater

ROOT = pathlib.Path(__file__).resolve().parent.parent
BAKU = ox.BAKU
ON = {"OZ_DERC": "1"}
NOVBE = {"done": "novbe", "gelecek": "gozle", "sorgu": 5}
HAMISI = {"done": "hamisi", "gelecek": "vaxtinda", "sorgu": 5}
MOVZU = ("idman", "iqtisadiyyat", "təbiət", "mədəniyyət", "təqvim", "icmal", "kosmos")
DAY = datetime.timedelta(days=1)


def at(h, m=0, day=12):
    """2026-cı il noyabrın 12-si cümə axşamıdır, 14-ü şənbə."""
    return datetime.datetime(2026, 11, day, h, m, tzinfo=BAKU)


def xeber(key, topic="idman", slot="00:00", worth=True, **kw):
    out = {"kind": "sinaq", "key": key, "title": f"Başlıq {key}", "lead": f"{key} xəbərinin girişi.",
           "body": ["Birinci abzas.", "İkinci abzas."], "credit": "Mənbənin adı", "link": "https://example.org/x",
           "topic": topic, "slot": slot, "worth": worth}
    if not worth:
        out["why"] = "səbəb"
    out.update(kw)
    return out


class Mod:
    """Saxta modul: items(root, now, fetch, done)."""

    def __init__(self, found=(), fail=None, tick=None):
        self.found, self.fail, self.tick, self.calls = list(found), fail, tick, []

    def items(self, root, now, fetch=None, done=None):
        self.calls.append({"now": now, "done": set(done or ()), "fetch": fetch})
        if self.tick:
            self.tick()
        if self.fail:
            raise self.fail
        return [dict(i) for i in self.found]


def no_net(url, **kw):
    raise OSError("şəbəkə yoxdur")


def keys(res):
    return [r["title"].replace("Başlıq ", "") for r in res["published"]]


def out_row(key, when, topic):
    return {"id": d.item_id(key), "key": key, "ts": d._iso(when), "topic": topic, "title": f"Başlıq {key}"}


class Base(unittest.TestCase):
    registered = True

    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.tmp = pathlib.Path(tmp.name)
        if self.registered:
            reg = d.registered()
            reg.__enter__()
            self.addCleanup(reg.__exit__, None, None, None)

    def run_cycle(self, now, mods, **kw):
        return d.cycle(self.tmp, now, env=ON, mods=mods, **kw)

    def state(self):
        return d.load(self.tmp)


class FlagTest(Base):
    registered = False

    def test_flag_off_does_nothing_at_all(self):
        mod = Mod([xeber("a")])
        for env in ({}, {"OZ_DERC": "0"}, {"OZ_DERC": ""}, {"OZ_DERC": "true"}):
            res = d.cycle(self.tmp, at(10), fetch=no_net, env=env, mods=[("m", mod, HAMISI)])
            self.assertEqual(res, {"enabled": False, "published": [], "queued": 0, "held": [], "blocked": [], "errors": []})
        with patch.dict(os.environ, {"OZ_DERC": ""}):
            self.assertFalse(d.cycle(self.tmp, at(10), mods=[("m", mod, HAMISI)])["enabled"])
        self.assertEqual(mod.calls, [], "modul çağırılmır")
        self.assertEqual(list(self.tmp.iterdir()), [], "fayl yazılmır")

    def test_site_calls_the_module_and_only_the_pipeline_sets_the_flag(self):
        """Sahib 2026-11-12: «Sayta qoşmağa başla», sonra «Bəli, yandır». Çağırış yerindədir, açarı yalnız pipeline.sh qoyur (tests/test_oz_xeber.py::WiredSwitchedOnTest)."""
        up = (ROOT / "updater.py").read_text(encoding="utf-8")
        sh = (ROOT / ".github/scripts/pipeline.sh").read_text(encoding="utf-8")
        self.assertEqual(up.count("oz_derc.cycle("), 1, "bir çağırış: yavaş addım")
        self.assertEqual(sh.count("OZ_DERC"), 1, "açar bir yerdə qoyulur")
        self.assertRegex(sh, r"(?m)^export OZ_DERC=1[ \t]+#", "açarı pipeline qoyur")
        self.assertEqual([l for l in sh.splitlines() if "oz_derc" in l and not l.startswith("CODE_FILES=")], [], "pipeline faylı yalnız köçürür")

    def test_tables_cover_every_module(self):
        names = [n for n, _ in ox.FAZA1 + ox.FAZA2 + ox.FAZA3]
        self.assertEqual(d.modules()[:len(names)], names)
        for n in names:
            self.assertIn(n, d.QAYDA)
            self.assertIn(n, d.ONCELIK)
        for n, _ in ox.FAZA2 + ox.FAZA3:
            self.assertEqual(d.QAYDA[n]["done"], "hamisi", n)
        slugs = {s[0] for s in updater.SECTIONS}
        for slug in list(d.BOLME.values()) + list(d.BOLME_NOV.values()):
            self.assertIn(slug, slugs)
        for base, kinds in d.ONCELIK.values():
            self.assertTrue(all(v in (1, 2, 3) for v in [base, *kinds.values()]))
        self.assertEqual(d.priority("oz_gundelik", {"kind": "polis-icmal"}), 3)
        self.assertEqual(d.priority("oz_yer_kosmos", {"kind": "zelzele-region"}), 3)
        self.assertEqual(d.priority("oz_teqvim", {"kind": "gun"}), 1)
        self.assertEqual(d.priority("naməlum", {"kind": "x"}), 2)
        self.assertEqual(d.modules()[len(names):], ["oz_xeber"], "baza xəbərləri (oz_xeber.items) də çağırılır")
        self.assertEqual(d.QAYDA["oz_xeber"]["done"], "hamisi")
        self.assertEqual([d.priority("oz_xeber", {"kind": k}) for k in ("zelzele", "futbol", "amb", "neft", "tarix")], [3, 3, 2, 2, 1])
        self.assertEqual([d.category({"kind": k, "topic": t}) for k, t in (("zelzele", "təbiət"), ("futbol", "idman"), ("amb", "iqtisadiyyat"),
                                                                           ("neft", "iqtisadiyyat"), ("tarix", "təqvim"))],
                         ["gundem", "idman", "iqtisadiyyat", "iqtisadiyyat", "cemiyyet"])
        self.assertEqual(d.category({"topic": "idman", "kind": "liqa-tur"}), "idman")
        self.assertEqual(d.category({"topic": "təqvim", "kind": "dim-gun"}), "tehsil")
        self.assertEqual(d.category({"topic": "mədəniyyət", "kind": "afisa"}), "medeniyyet")
        self.assertEqual(d.category({"topic": "iqtisadiyyat", "kind": "birja"}), "iqtisadiyyat")
        self.assertEqual(d.category({"topic": "bilinməyən"}), "gundem")


class DoneTest(Base):
    def test_phase2_marks_every_returned_key(self):
        mod = Mod([xeber("a1"), xeber("a-yox", worth=False), xeber("zelzele-sorgu-2026-11-12T10", worth=False)])
        res = self.run_cycle(at(10), [("f2", mod, HAMISI)])
        self.assertEqual(keys(res), ["a1"])
        self.assertEqual(set(self.state()["done"]), {"a1", "a-yox", "zelzele-sorgu-2026-11-12T10"})
        self.run_cycle(at(10, 10), [("f2", mod, HAMISI)])
        self.assertEqual(mod.calls[0]["done"], set())
        self.assertEqual(mod.calls[1]["done"], {"a1", "a-yox", "zelzele-sorgu-2026-11-12T10"})

    def test_phase1_marks_only_queued_keys(self):
        mod = Mod([xeber("b1"), xeber("b-natamam", "iqtisadiyyat", worth=False)])
        res = self.run_cycle(at(10), [("f1", mod, NOVBE)])
        self.assertEqual(keys(res), ["b1"])
        self.assertEqual(set(self.state()["done"]), {"b1"})
        mod.found[1] = xeber("b-natamam", "iqtisadiyyat")  # tur bitdi: eyni açar indi dəyərlidir
        self.assertEqual(keys(self.run_cycle(at(10, 10), [("f1", mod, NOVBE)])), ["b-natamam"])
        self.assertEqual(keys(self.run_cycle(at(10, 40), [("f1", mod, NOVBE)])), [], "bir açar bir dəfə dərc olunur")
        self.assertEqual(mod.calls[2]["done"], {"b1", "b-natamam"})

    def test_future_slot_is_left_alone_for_phase1(self):
        mod = Mod([xeber("s1", slot="15:00")])
        res = self.run_cycle(at(10), [("f1", mod, NOVBE)])
        self.assertEqual((res["published"], res["queued"]), ([], 0))
        self.assertEqual(self.state()["done"], {})
        self.assertEqual(keys(self.run_cycle(at(15), [("f1", mod, NOVBE)])), ["s1"])

    def test_future_slot_is_queued_with_its_time_for_phase2(self):
        res = self.run_cycle(at(10), [("f2", Mod([xeber("s2", slot="15:00")]), HAMISI)])
        self.assertEqual((res["published"], res["queued"]), ([], 1))
        st = self.state()
        self.assertIn("s2", st["done"])
        self.assertEqual(st["queue"][0]["due"], d._iso(at(15)))
        self.assertEqual(keys(self.run_cycle(at(14, 59), [])), [])
        self.assertEqual(keys(self.run_cycle(at(15), [])), ["s2"])

    def test_slot_of_yesterday_and_the_date_field(self):
        rule = dict(NOVBE, gelecek="indi")
        self.assertEqual(keys(self.run_cycle(at(9), [("f1", Mod([xeber("s3", slot="23:15")]), rule)])), ["s3"])
        dated = Mod([xeber("s4", "iqtisadiyyat", slot="23:00", date="2026-11-11"),
                     xeber("s5", "təbiət", slot="08:00", date="2026-11-13")])
        self.assertEqual(keys(self.run_cycle(at(9, 30), [("f1", dated, NOVBE)])), ["s4"])
        self.assertNotIn("s5", self.state()["done"])

    def test_start_hour_rule(self):
        mod = Mod([xeber("beledci-2026-11-12", "icmal", slot="08:00"), xeber("reqemler-2026-11-12", "icmal", slot="12:00")])
        rule = dict(HAMISI, basla="08:00")
        self.run_cycle(at(7, 50), [("i", mod, rule)])
        self.assertEqual(mod.calls, [])
        self.assertEqual(keys(self.run_cycle(at(8), [("i", mod, rule)])), ["beledci-2026-11-12"])
        self.assertEqual(self.state()["queue"][0]["due"], d._iso(at(12)))
        self.assertEqual(keys(self.run_cycle(at(12), [])), ["reqemler-2026-11-12"])

    def test_module_without_done_is_not_called_again_that_day(self):
        calls = []

        def bazar(root, now, fetch=None, history=None):
            calls.append(now)
            return [xeber("amb-metal-2026-11-12", "iqtisadiyyat", slot="09:40")]

        rule = dict(NOVBE, bir=True)
        for now in (at(9, 30), at(9, 40), at(10), at(10, 20)):
            self.run_cycle(now, [("b", bazar, rule)])
        self.assertEqual(calls, [at(9, 30), at(9, 40)])
        self.run_cycle(at(9, 40, day=13), [("b", bazar, rule)])
        self.assertEqual(len(calls), 3)

    def test_signatures_are_adapted_and_closes_are_stored(self):
        seen = {}

        def plain(root, now):
            seen["plain"] = root
            return []

        def with_fetch(root, now, fetch=None):
            seen["fetch"] = fetch
            return []

        def with_done(root, now, fetch=None, done=()):
            seen["done"] = done
            return []

        def with_history(root, now, fetch=None, history=None):
            seen["history"] = history
            return []

        (self.tmp / "data").mkdir()
        (self.tmp / "data" / "markets.json").write_text(json.dumps({"updatedAt": "2026-11-11T22:30:00+00:00", "items": [
            {"id": "XAU", "value": 4100.5, "src": "gold-api.com"}, {"id": "USD", "value": 1.7, "src": "AMB"}]}), encoding="utf-8")
        res = self.run_cycle(at(10), [("p", plain), ("f", with_fetch), ("d", with_done), ("h", with_history)])
        self.assertEqual(res["errors"], [])
        self.assertEqual(seen["plain"], self.tmp)
        self.assertTrue(callable(seen["fetch"]))
        self.assertEqual(seen["done"], set())
        self.assertEqual(list(seen["history"]), ["b-2026-11-11"], "ABŞ seansının bağlanışından sonrakı fasilənin nüsxəsi")
        self.assertEqual([i["id"] for i in seen["history"]["b-2026-11-11"]["items"]], ["XAU"])
        self.assertEqual(self.state()["closes"], seen["history"])

    def test_daily_request_cap(self):
        urls = []

        def fetch(url, timeout=15, headers=None):
            urls.append(url)
            return b"ok"

        def greedy(root, now, fetch=None):
            for i in range(5):
                fetch(f"https://example.org/{i}", timeout=15)
            return []

        mods = [("ac", greedy, dict(HAMISI, sorgu=3))]
        res = self.run_cycle(at(10), mods, fetch=fetch)
        self.assertEqual(len(urls), 3)
        self.assertIn("gündəlik sorğu həddi (3)", res["errors"][0])
        self.assertEqual(self.state()["reqs"], {"day": "2026-11-12", "n": {"ac": 3}})
        self.run_cycle(at(10, 10), mods, fetch=fetch)
        self.assertEqual(len(urls), 3)
        self.run_cycle(at(10, day=13), mods, fetch=fetch)
        self.assertEqual(len(urls), 6, "yeni gün, yeni hədd")


class QueueTest(Base):
    def test_late_item_is_dropped_and_never_published(self):
        mod = Mod([xeber("e1", "idman"), xeber("e2", "iqtisadiyyat"), xeber("e3", "təbiət")])
        res = self.run_cycle(at(10), [("f2", mod, HAMISI)])
        self.assertEqual((keys(res), res["queued"]), (["e1", "e2"], 1))
        self.assertIn("dövrədə", res["held"][0]["why"])
        res = self.run_cycle(at(16, 1), [])
        self.assertEqual((res["published"], res["queued"]), ([], 0))
        self.assertEqual([(b["key"], b["why"]) for b in res["blocked"]], [("e3", "gecikdi")])
        self.assertEqual(self.state()["blocked"][-1]["key"], "e3")
        self.assertEqual(keys(self.run_cycle(at(16, 30), [("f2", mod, HAMISI)])), [], "düşən xəbər geri qayıtmır")

    def test_item_does_not_cross_midnight(self):
        mod = Mod([xeber("n1", "idman"), xeber("n2", "iqtisadiyyat"), xeber("n3", "təbiət")])
        self.assertEqual(keys(self.run_cycle(at(23, 50), [("f2", mod, HAMISI)])), ["n1", "n2"])
        res = self.run_cycle(at(0, 10, day=13), [])
        self.assertEqual(res["published"], [])
        self.assertEqual([(b["key"], b["why"]) for b in res["blocked"]], [("n3", "gecikdi")])

    def test_ramp_by_week(self):
        start = datetime.date(2026, 11, 12)
        got = [d.ceiling(start.isoformat(), start + n * DAY) for n in (0, 6, 7, 13, 14, 20, 21, 200)]
        self.assertEqual(got, [15, 15, 25, 25, 35, 35, 40, 40])
        self.assertEqual(d.ceiling("", start), 15)
        self.assertEqual(d.ceiling("pozuq", start), 15)

    def test_hourly_and_per_cycle_caps(self):
        mod = Mod([xeber(f"h{i}", MOVZU[i]) for i in range(6)])
        mods = [("f2", mod, HAMISI)]
        self.assertEqual(keys(self.run_cycle(at(10), mods)), ["h0", "h1"])
        self.assertEqual(keys(self.run_cycle(at(10, 10), mods)), ["h2", "h3"])
        res = self.run_cycle(at(10, 20), mods)
        self.assertEqual(keys(res), [])
        self.assertIn("saatlıq hədd", res["held"][0]["why"])
        self.assertEqual(keys(self.run_cycle(at(10, 59), mods)), [])
        self.assertEqual(keys(self.run_cycle(at(11), mods)), ["h4", "h5"], "10:00-ın iki xəbəri bir saatlıq pəncərədən çıxdı")

    def test_same_topic_is_not_back_to_back(self):
        mod = Mod([xeber("a", "idman"), xeber("b", "idman"), xeber("c", "iqtisadiyyat")])
        res = self.run_cycle(at(10), [("f2", mod, HAMISI)])
        self.assertEqual(keys(res), ["a", "c"])
        self.assertIn("ardıcıl eyni mövzu", res["held"][0]["why"])
        self.assertEqual(keys(self.run_cycle(at(10, 10), [])), ["b"])

    def test_single_topic_waits_twenty_minutes(self):
        mod = Mod([xeber("a", "idman"), xeber("b", "idman")])
        self.assertEqual(keys(self.run_cycle(at(10), [("f2", mod, HAMISI)])), ["a"])
        self.assertEqual(keys(self.run_cycle(at(10, 10), [])), [])
        self.assertEqual(keys(self.run_cycle(at(10, 20), [])), ["b"])

    def test_topic_caps_weekday_weekend_and_third_of_ceiling(self):
        thu, sat = datetime.date(2026, 11, 12), datetime.date(2026, 11, 14)
        names = ("idman", "iqtisadiyyat", "təbiət", "kosmos", "təqvim", "mədəniyyət", "icmal", "başqa")
        self.assertEqual([d.topic_cap(t, thu, 40) for t in names], [10, 8, 5, 2, 3, 3, 3, 4])
        self.assertEqual([d.topic_cap(t, sat, 40) for t in names], [10, 5, 5, 2, 3, 3, 5, 3])
        self.assertEqual([d.topic_cap(t, thu, 15) for t in names], [5, 5, 5, 2, 3, 3, 3, 4], "tavanın üçdə biri")
        self.assertEqual(d.topic_cap("idman", thu, 25), 8)
        self.assertEqual(d.topic_cap("idman", thu, 6), 3, "ən azı 3")

    def test_topic_cap_holds_the_item(self):
        st = d.fresh()
        st["start"] = "2026-10-01"
        st["out"] = [out_row("k1", at(1), "kosmos"), out_row("k2", at(2), "kosmos"), out_row("i1", at(3), "idman")]
        d.save(self.tmp, st)
        res = self.run_cycle(at(10), [("f2", Mod([xeber("k9", "kosmos"), xeber("q9", "iqtisadiyyat")]), HAMISI)])
        self.assertEqual(keys(res), ["q9"])
        self.assertEqual([(h["key"], "mövzu həddi" in h["why"]) for h in res["held"]], [("k9", True)])

    def _full_day(self, start):
        st = d.fresh()
        st["start"] = start
        st["out"] = [out_row(f"o{i}", at(1 + i // 2, 30 * (i % 2)), MOVZU[i % 7]) for i in range(14)]
        d.save(self.tmp, st)
        return [("oz_teqvim", Mod([xeber("a-zeif", "təqvim", slot="06:00")]), HAMISI),
                ("oz_gundelik", Mod([xeber("z-vacib", "təbiət", slot="07:00")]), HAMISI)]

    def test_priority_decides_under_pressure(self):
        res = self.run_cycle(at(10), self._full_day("2026-11-12"))   # tavan 15, 14-ü dərc olunub: bir yer qalıb
        self.assertEqual(keys(res), ["z-vacib"])
        self.assertEqual([(h["key"], h["why"]) for h in res["held"]], [("a-zeif", "gündəlik hədd: 15 xəbər")])

    def test_time_order_without_pressure(self):
        res = self.run_cycle(at(10), self._full_day("2026-10-01"))   # tavan 40
        self.assertEqual(keys(res), ["a-zeif", "z-vacib"], "yer çatanda sıra vaxta görədir: slot 06:00, sonra 07:00")


class GateTest(Base):
    registered = False

    def test_unregistered_source_blocks_everything(self):
        # 2026-11-12-dən «8ULDUZ» icazəli siyahıdadır (yalnız öz ünvanı ilə). Siyahıdan çıxarılsa qapı yenə hər sətri rədd edir.
        self.assertEqual(content_policy.AZ_SOURCES.get(ox.SOURCE), ["8ulduz.az"])
        with patch.dict(content_policy.AZ_SOURCES):
            del content_policy.AZ_SOURCES[ox.SOURCE]
            res = self.run_cycle(at(10), [("f2", Mod([xeber("g1"), xeber("g2", "iqtisadiyyat")]), HAMISI)])
            with d.registered():
                self.assertIn(ox.SOURCE, content_policy.AZ_SOURCES)
            self.assertNotIn(ox.SOURCE, content_policy.AZ_SOURCES, "sınaq qeydiyyatı olmayan mənbəni siyahıda saxlamır")
        self.assertEqual(res["published"], [])
        self.assertEqual([b["why"] for b in res["blocked"]], ["icazəli siyahıda deyil"] * 2)
        self.assertFalse((self.tmp / "xeber").exists())
        self.assertFalse((self.tmp / "data" / "oz" / "xeberler.json").exists())
        self.assertEqual(self.state()["out"], [])

    def test_registered_source_passes_and_writes_page_and_rows(self):
        with d.registered():
            res = self.run_cycle(at(10), [("f2", Mod([xeber("g1"), xeber("g2", "iqtisadiyyat")]), HAMISI)])
        self.assertEqual(content_policy.AZ_SOURCES.get(ox.SOURCE), ["8ulduz.az"], "sınaq qeydiyyatı siyahını əvvəlki halına qaytarır")
        self.assertEqual(keys(res), ["g1", "g2"])
        ids = [d.item_id("g1"), d.item_id("g2")]
        for i in ids:
            self.assertIn("<h1>Başlıq g", (self.tmp / "xeber" / i / "index.html").read_text(encoding="utf-8"))
        doc = json.loads((self.tmp / "data" / "oz" / "xeberler.json").read_text(encoding="utf-8"))
        self.assertEqual([r["id"] for r in doc["articles"]], ids)
        self.assertEqual(doc["articles"], res["published"])
        self.assertNotIn("Birinci abzas", json.dumps(doc, ensure_ascii=False), "tam mətn sətirdə yoxdur")
        self.assertEqual([(o["id"], o["key"], o["topic"]) for o in self.state()["out"]],
                         [(ids[0], "g1", "idman"), (ids[1], "g2", "iqtisadiyyat")])
        self.assertEqual(list(self.tmp.rglob("*.tmp")), [])

    def test_leadership_text_and_unsafe_link_are_blocked(self):
        mod = Mod([xeber("r1", title="Prezident İlham Əliyev yeni sərəncam imzalayıb"),
                   xeber("r2", "iqtisadiyyat", link="javascript:alert(1)"),
                   xeber("r3", "təbiət", link="http://127.0.0.1/x"),
                   xeber("r4", "mədəniyyət", body=["Tədbirdə Mehriban Əliyeva iştirak edib."]),
                   xeber("r5", "təqvim", lead=""),
                   xeber("ok", "icmal")])
        with d.registered():
            res = self.run_cycle(at(10), [("f2", mod, HAMISI)])
        self.assertEqual(keys(res), ["ok"])
        why = {b["key"]: b["why"] for b in res["blocked"]}
        self.assertEqual(sorted(why), ["r1", "r2", "r3", "r4", "r5"])
        self.assertIn("rəhbərliyin adı", why["r1"])
        self.assertIn("rəhbərliyin adı", why["r4"])
        self.assertIn("keçidi", why["r2"])
        self.assertIn("keçidi", why["r3"])
        self.assertIn("boşdur", why["r5"])
        bad = xeber("r6", title="Milli Məclisdə korrupsiya qalmaqalı")
        with d.registered():
            self.assertIsNotNone(d.gate(bad, d.row(bad, at(10))))
            good = xeber("r7")
            self.assertIsNone(d.gate(good, d.row(good, at(10))))
        self.assertIsNone(d.gate(good, d.row(good, at(10))), "mənbə 2026-11-12-dən siyahıdadır")
        with patch.dict(content_policy.AZ_SOURCES):
            del content_policy.AZ_SOURCES[ox.SOURCE]
            self.assertEqual(d.gate(good, d.row(good, at(10))), "icazəli siyahıda deyil")

    def test_sinaq_with_fake_modules(self):
        def items(root, now, fetch=None):
            return [xeber(f"t{i:02d}-{now:%d}", MOVZU[i % 6], slot=f"{1 + i // 4:02d}:{15 * (i % 4):02d}") for i in range(20)]

        with patch.dict(sys.modules, {"oz_saxta": SimpleNamespace(items=items)}), \
                patch.object(d, "modules", return_value=["oz_saxta"]), patch.dict(d.QAYDA, {"oz_saxta": NOVBE}):
            md = "\n".join(d.sinaq(self.tmp, at(9, 10), fetch=no_net))
        self.assertNotIn("xəta ilə bitdi", md)
        # Kilidlərin 2026-11-12-dən vəziyyəti: üçü də açıqdır.
        self.assertIn("- Çağırış: updater.py-ın yavaş dövrəsi bu faylı çağırır (yalnız bayraqla). **AÇIQDIR.**", md)
        self.assertIn("mühit dəyişənini qoyur. **AÇIQDIR.**", md)
        self.assertNotIn("Bağlıdır.", md)
        self.assertIn("icazəli mənbələr siyahısında (assets/content-policy.js) var. **AÇIQDIR.**", md)
        self.assertNotIn("yoxdur. Bağlıdır.", md)
        self.assertIn("### İlk həftənin tavanı ilə (gündə 15): 15 xəbər", md)
        self.assertIn("### Tam tavanla (gündə 40): 20 xəbər", md)
        self.assertIn("| 01:00 | İdman | Başlıq t00-12 |", md)
        self.assertIn("- Başlıq t15-12: gündəlik hədd: 15 xəbər", md)
        self.assertIn("### Dünən, ilk həftənin tavanı ilə (gündə 15): 15 xəbər", md)
        self.assertIn("### Dünən, tam tavanla (gündə 40): 20 xəbər", md)
        self.assertIn("| 01:00 | İdman | Başlıq t00-11 |", md)
        self.assertIn("### 8 noyabr (bazar), ilk həftənin tavanı ilə (gündə 15): 15 xəbər", md)
        self.assertIn("### 8 noyabr (bazar), tam tavanla (gündə 40): 20 xəbər", md)
        self.assertIn("- Başlıq t15-11: gecikdi", md)
        self.assertNotIn("t00-10", md, "isinmə dövrəsinin nəticəsi göstərilmir")
        self.assertIn("Yoxlanan sətir: 20. Keçən: 20. Rədd edilən: 0.", md)
        self.assertEqual(md.count("```json"), 2)
        self.assertIn("<!-- OZ-DERC-SEHIFE-BASLADI t00-12 -->", md)
        self.assertEqual(md.count("<!-- OZ-DERC-SEHIFE-BITDI -->"), 2)
        self.assertEqual(list(self.tmp.iterdir()), [], "sınaq root-a heç nə yazmır")
        self.assertEqual(content_policy.AZ_SOURCES.get(ox.SOURCE), ["8ulduz.az"])
        with patch.dict(content_policy.AZ_SOURCES), patch.dict(sys.modules, {"oz_saxta": SimpleNamespace(items=items)}), \
                patch.object(d, "modules", return_value=["oz_saxta"]), patch.dict(d.QAYDA, {"oz_saxta": NOVBE}):
            del content_policy.AZ_SOURCES[ox.SOURCE]   # mənbə siyahıdan çıxarılsa əsl qapı hamısını rədd edir
            md = "\n".join(d.sinaq(self.tmp, at(9, 10), fetch=no_net))
            self.assertNotIn(ox.SOURCE, content_policy.AZ_SOURCES)
        self.assertIn("Rədd edilən: 20 («icazəli siyahıda deyil»: 20)", md)
        self.assertIn("icazəli mənbələr siyahısında (assets/content-policy.js) yoxdur. Bağlıdır.", md)

    def test_sinaq_with_the_real_modules_offline(self):
        with patch("time.sleep"), patch("oz_maliyye._sleep"):
            md = "\n".join(d.sinaq(self.tmp, at(9, 10), fetch=no_net))
        self.assertNotIn("xəta ilə bitdi", md)
        for head in ("## 1. Üç kilid", "## 2. Bu gün nə dərc olunardı", "## 3. Əsl qapının bu günkü qərarı", "gündə 15", "gündə 40"):
            self.assertIn(head, md)
        self.assertEqual(list(self.tmp.iterdir()), [])
        self.assertEqual(content_policy.AZ_SOURCES.get(ox.SOURCE), ["8ulduz.az"])

    def test_cli_and_the_section_in_oz_xeber(self):
        out = io.StringIO()
        with patch.object(d, "_default_fetch", side_effect=OSError("şəbəkə yoxdur")), patch.object(d, "modules", return_value=[]):
            with contextlib.redirect_stdout(out):
                self.assertEqual(d.main(["--sinaq", "--root", str(self.tmp), "--now", "2026-11-12T09:00+04:00"]), 0)
            md = "\n".join(ox.derc_sinaq(self.tmp, at(9), no_net))
        self.assertIn("# Dərc hissəsi (oz_derc.py): sınaq", out.getvalue())
        self.assertIn("12.11.2026 09:00 (Bakı vaxtı)", out.getvalue())
        self.assertIn("Yoxlanacaq sətir yoxdur.", out.getvalue())
        self.assertTrue(md.startswith("## 5. Dərc hissəsi"))
        self.assertIn("#### 1. Üç kilid", md)
        self.assertIn("#### 6. Baza xəbərləri (oz_xeber.items): pəncərə nümunələri", md)


class RowPageTest(Base):
    registered = False

    def test_row_has_make_article_keys_and_16_hex_id(self):
        art = updater.make_article({"link": "https://example.org/a", "title": "Başlıq", "description": "Mətn",
                                    "pubDate": "Thu, 12 Nov 2026 06:00:00 +0000"}, "Report", "az")
        r = d.row(xeber("k1", image="https://example.org/a.jpg"), at(10))
        self.assertEqual(set(r), set(art))
        self.assertEqual(list(r), list(art), "açarların sırası da eynidir")
        self.assertRegex(r["id"], r"^[0-9a-f]{16}$")
        self.assertEqual(r["id"], hashlib.sha1("8ulduz:k1".encode("utf-8")).hexdigest()[:16])
        self.assertEqual(r["sourceUrl"], f"{updater.SITE}xeber/{r['id']}/")
        self.assertEqual((r["source"], r["lang"], r["author"], r["video"]), ("8ULDUZ", "az", "", False))
        self.assertEqual(r["publishedAt"], "2026-11-12T06:00:00+00:00")
        self.assertEqual(r["imageUrl"], "https://example.org/a.jpg")
        self.assertIsNone(d.row(xeber("k1"), at(10))["imageUrl"])
        self.assertIsNone(d.row(xeber("k1", image="http://example.org/a.jpg"), at(10))["imageUrl"])
        self.assertEqual(r["category"], "idman")

    def test_summary_is_cut_like_short(self):
        lead = "söz  " * 100
        r = d.row(xeber("k2", lead=lead), at(10))
        self.assertEqual(r["summary"], updater._short(" ".join(lead.split())))
        self.assertTrue(r["summary"].endswith("…"))
        self.assertLessEqual(len(r["summary"]), updater.SUMMARY_MAX + 1)
        self.assertEqual(d.row(xeber("k3", lead="Qısa giriş."), at(10))["summary"], "Qısa giriş.")

    def test_page_escapes_everything_and_has_only_the_json_ld_script(self):
        it = xeber("p1", title='<script>alert(1)</script> «Neftçi» & "Kəpəz"', lead="Giriş <b>mətn</b>.",
                   body=["Birinci <i>bənd</i>.", "İkinci bənd."], credit="Mənbə <x>",
                   link='https://example.org/a?b=1&c="2"', image="https://example.org/s.jpg", list=True)
        r = d.row(it, at(10))
        p = d.page(it, r)
        self.assertEqual(p.count("<script"), 1)
        self.assertIn('<script type="application/ld+json">', p)
        for raw in ("<script>alert", "<b>", "<i>", "<x>"):
            self.assertNotIn(raw, p)
        self.assertIn("<h1>&lt;script&gt;alert(1)&lt;/script&gt; «Neftçi» &amp; &quot;Kəpəz&quot;</h1>", p)
        self.assertIn(f'<link rel="canonical" href="{updater.SITE}xeber/{r["id"]}/" />', p)
        self.assertIn("<ul><li>Birinci &lt;i&gt;bənd&lt;/i&gt;.</li><li>İkinci bənd.</li></ul>", p)
        self.assertIn('Mənbə: <a href="https://example.org/a?b=1&amp;c=&quot;2&quot;" rel="noopener">Mənbə &lt;x&gt;</a>', p)
        self.assertIn('<meta name="robots" content="max-image-preview:large" />', p)
        self.assertIn('<meta property="og:image" content="https://example.org/s.jpg" />', p)
        self.assertIn('<img src="https://example.org/s.jpg"', p)
        self.assertIn('<time datetime="2026-11-12T06:00:00+00:00">12 noyabr 2026, 10:00</time>', p)
        self.assertIn(f'<a href="{updater.SITE}">8ULDUZ</a> › <a href="{updater.SITE}bolme/idman/">İdman</a>', p)
        self.assertIn("https://t.me/sekkizulduz_az", p)
        self.assertIn("Bu xəbəri 8ULDUZ mənbənin məlumatı əsasında hazırlayıb.", p)
        ld = json.loads(re.search(r'<script type="application/ld\+json">(.*?)</script>', p, re.S).group(1))
        self.assertEqual((ld["@type"], ld["headline"], ld["datePublished"]), ("NewsArticle", r["title"], r["publishedAt"]))
        self.assertEqual(ld["image"], ["https://example.org/s.jpg"])
        self.assertEqual(ld["publisher"]["name"], "8ulduz")
        self.assertEqual(ld["mainEntityOfPage"], r["sourceUrl"])

    def test_page_paragraphs_default_image_and_placeholder_words(self):
        it = xeber("p2", title="__SITE__ və __LD__ sözləri")
        r = d.row(it, at(10))
        p = d.page(it, r)
        self.assertIn("<h1>__SITE__ və __LD__ sözləri</h1>", p)
        self.assertIn("<p>Birinci abzas.</p>\n<p>İkinci abzas.</p>", p)
        self.assertNotIn("<ul>", p)
        self.assertNotIn("<img", p)
        self.assertIn(f'<meta property="og:image" content="{updater.SITE}assets/og-default.png" />', p)
        self.assertNotRegex(p.replace("__SITE__ və __LD__ sözləri", ""), r"__[A-Z]+__")


class StateTest(Base):
    def test_round_trip_and_corrupt_file(self):
        st = d.fresh()
        st.update(start="2026-11-01", done={"a": d._iso(at(9))}, next="oz_hava",
                  queue=[{"key": "q", "mod": "m", "due": d._iso(at(9)), "pri": 2, "item": d._clean(xeber("q"))}],
                  out=[out_row("o", at(8), "idman")])
        d.save(self.tmp, st)
        self.assertEqual(d.load(self.tmp), st)
        path = self.tmp / "data" / "oz" / "derc.json"
        for junk in ("{yarımçıq", '{"v": 2, "start": "2026-01-01"}', "[1, 2]", ""):
            path.write_text(junk, encoding="utf-8")
            self.assertEqual(d.load(self.tmp), d.fresh(), junk)
        path.write_text('{"v": 1, "start": 5, "done": [], "queue": [1, {"key": "x"}], "out": [{"id": 1}]}', encoding="utf-8")
        self.assertEqual(d.load(self.tmp), d.fresh(), "yanlış tipli sahələr atılır")
        path.write_text("{yarımçıq", encoding="utf-8")
        res = self.run_cycle(at(10), [("f2", Mod([xeber("c1")]), HAMISI)])
        self.assertEqual(keys(res), ["c1"])
        self.assertEqual(self.state()["start"], "2026-11-12")

    def test_page_on_disk_stops_a_second_publication_after_state_loss(self):
        mods = [("f2", Mod([xeber("c1")]), HAMISI)]
        self.assertEqual(keys(self.run_cycle(at(10), mods)), ["c1"])
        (self.tmp / "data" / "oz" / "derc.json").unlink()
        res = self.run_cycle(at(10, 30), mods)
        self.assertEqual(res["published"], [])
        self.assertIn("artıq var", res["blocked"][0]["why"])

    def test_old_pages_done_keys_and_rows_are_pruned(self):
        now = at(10)
        ids = {k: d.item_id(k) for k in ("kohne", "orta", "teze")}
        for i in [*ids.values(), "feedfacefeedface"]:
            (self.tmp / "xeber" / i).mkdir(parents=True)
            (self.tmp / "xeber" / i / "index.html").write_text("x", encoding="utf-8")
        st = d.fresh()
        st["start"] = "2026-10-01"
        st["out"] = [out_row("kohne", now - 31 * DAY, "idman"), out_row("orta", now - 5 * DAY, "idman"), out_row("teze", at(9), "idman")]
        st["done"] = {"kohne-acar": d._iso(now - 9 * DAY), "teze-acar": d._iso(now - DAY)}
        d.save(self.tmp, st)
        old_row, new_row = d.row(xeber("kohne"), now - datetime.timedelta(hours=49)), d.row(xeber("teze"), at(9))
        rows = self.tmp / "data" / "oz" / "xeberler.json"
        rows.write_text(json.dumps({"v": 1, "articles": [new_row, old_row]}, ensure_ascii=False), encoding="utf-8")
        res = self.run_cycle(now, [])
        self.assertEqual(res["errors"], [])
        self.assertFalse((self.tmp / "xeber" / ids["kohne"]).exists(), "30 gündən köhnə öz səhifəmiz silinir")
        self.assertTrue((self.tmp / "xeber" / ids["orta"] / "index.html").exists())
        self.assertTrue((self.tmp / "xeber" / ids["teze"] / "index.html").exists())
        self.assertTrue((self.tmp / "xeber" / "feedfacefeedface" / "index.html").exists(), "siyahımızda olmayan səhifəyə toxunulmur")
        out = self.state()["out"]
        self.assertEqual([o["id"] for o in out], [ids["orta"], ids["teze"]])
        self.assertEqual(sorted(out[0]), ["id", "key", "ts"], "köhnə sətir yığcam saxlanır")
        self.assertEqual(out[1]["title"], "Başlıq teze")
        self.assertEqual(list(self.state()["done"]), ["teze-acar"])
        self.assertEqual([r["id"] for r in json.loads(rows.read_text(encoding="utf-8"))["articles"]], [ids["teze"]])

    def test_one_failing_module_does_not_stop_the_others(self):
        junk = lambda root, now: ["sətir", {"key": 5}, None, {"worth": True}]
        mods = [("pis", Mod(fail=ValueError("pozuq")), HAMISI), ("oz_yoxdur", None), ("qarisiq", junk),
                ("yaxsi", Mod([xeber("ok")]), HAMISI)]
        res = self.run_cycle(at(10), mods)
        self.assertEqual(keys(res), ["ok"])
        self.assertEqual(len(res["errors"]), 2)
        self.assertTrue(res["errors"][0].startswith("pis: ValueError: pozuq"), res["errors"])
        self.assertTrue(res["errors"][1].startswith("oz_yoxdur: ModuleNotFoundError"), res["errors"])
        self.assertEqual([e["msg"] for e in self.state()["errors"]], res["errors"])

    def test_time_budget_and_rotation(self):
        clock = [0.0]

        def tick():
            clock[0] += 40

        a, b, c = Mod(tick=tick), Mod(tick=tick), Mod(tick=tick)
        mods = [("a", a, HAMISI), ("b", b, HAMISI), ("c", c, HAMISI)]
        count = lambda: (len(a.calls), len(b.calls), len(c.calls))
        with patch.object(d, "_clock", lambda: clock[0]):
            res = self.run_cycle(at(10), mods)
            self.assertEqual(count(), (1, 1, 0))
            self.assertIn("vaxt büdcəsi", res["errors"][0])
            self.assertEqual(self.state()["next"], "c")
            self.run_cycle(at(10, 10), mods)
            self.assertEqual(count(), (2, 1, 1), "növbəti dövrə qalan moduldan başlayır")
            self.assertEqual(self.state()["next"], "b")
            self.run_cycle(at(10, 20), mods)
            self.assertEqual(count(), (2, 2, 2))
            self.assertEqual(self.state()["next"], "a")

    def test_cycle_never_raises(self):
        cases = (("vaxt deyil", []), (at(10), "??"), (at(10), [("m", object())]), (at(10), [(1,)]), (at(10), 5))
        for now, mods in cases:
            res = d.cycle(self.tmp, now, env=ON, mods=mods)
            self.assertTrue(res["enabled"])
            self.assertEqual(res["published"], [])
            self.assertTrue(res["errors"], mods)
        blocker = self.tmp / "fayl"
        blocker.write_text("x", encoding="utf-8")
        res = d.cycle(blocker, at(10), env=ON, mods=[("f2", Mod([xeber("z")]), HAMISI)])
        self.assertEqual(res["published"], [])
        self.assertTrue(res["errors"])


if __name__ == "__main__":
    unittest.main()
