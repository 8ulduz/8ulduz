"""oz_xeber.items(): baza xəbərlərinin pəncərələri və done dəsti («Bu gün tarixdə», AMB, neft, zəlzələ, Premyer Liqa oyunu).
Şəbəkə yoxdur: sorğular saxtadır, cavablar tests/test_oz_xeber.py-dəki nümunələrdir."""
import datetime
import json
import pathlib
import tempfile
import unittest
from unittest.mock import patch

import oz_xeber as oz
import test_oz_xeber as base

BAKU = oz.BAKU
WIKI = json.dumps({"parse": {"wikitext": base.WIKI_9_NOV}}, ensure_ascii=False)
AMB_OLD = base._amb("04.11.2026", [("USD", "1 ABŞ dolları", "1.7"), ("EUR", "1 Avro", "1.9200")])
PFL_PAGES = [("/seasons", json.dumps({"data": [{"id": 76, "leagues": [{"id": 52}]}]})),
             ("/tours/", json.dumps({"data": base.TOURS}, ensure_ascii=False)),
             ("/games/show/6851", json.dumps({"data": {"refeerer_main": {"name": "İnqilab", "surname": "Məmmədov"}, "fan": "550"}},
                                             ensure_ascii=False))]
LOCAL = {
    "key": "2026",
    "teams": {"neftci": {"name": "Neftçi"}, "kepez": {"name": "Kəpəz"}, "qarabag": {"name": "Qarabağ"},
              "turan-tovuz": {"name": "Turan Tovuz"}, "zire": {"name": "Zirə"}, "qebele": {"name": "Qəbələ"}},
    "groups": [{"name": "", "rows": [{"pos": 1, "team": "neftci", "p": 1, "pts": 24}, {"pos": 2, "team": "qarabag", "p": 5, "pts": 19},
                                     {"pos": 3, "team": "turan-tovuz", "p": 1, "pts": 21}, {"pos": 11, "team": "kepez", "p": 1, "pts": 9}]}],
    "games": [
        {"home": "neftci", "away": "kepez", "hs": 1, "as": 0, "date": "2026-11-06T20:00+04:00", "played": True,
         "stadium": "Palms Sports Arena", "round": "11"},
        {"home": "qarabag", "away": "turan-tovuz", "hs": 0, "as": 1, "date": "2026-11-06T18:00+04:00", "played": True,
         "stadium": "Tovuz şəhər st.", "round": "11"},
        {"home": "zire", "away": "qebele", "hs": None, "as": None, "date": "2026-11-09T18:30+04:00", "played": False,
         "stadium": "Zirə İK stadionu", "round": "11"},
    ],
}
FIELDS = ("kind", "key", "title", "lead", "body", "credit", "link", "topic", "slot", "worth")


def at(day, h, m=0, month=11):
    """2026: 6 noyabr cümə, 7 noyabr şənbə, 9 noyabr bazar ertəsi (Dövlət Bayrağı Günü), 19 oktyabr bazar ertəsi."""
    return datetime.datetime(2026, month, day, h, m, tzinfo=BAKU)


class Net:
    """Saxta sorğu: ünvanın bir hissəsinə görə cavab (sıra ilə baxılır); tapılmayan ünvan OSError."""

    def __init__(self, pages=()):
        self.pages, self.urls = list(pages), []

    def __call__(self, url, timeout=None, headers=None):
        self.urls.append(url)
        for part, body in self.pages:
            if part in url:
                return body if isinstance(body, bytes) else body.encode("utf-8")
        raise OSError(url)


def head(item):
    return item["kind"], item["key"], item["topic"], item["slot"], item["worth"]


class Base(unittest.TestCase):
    def setUp(self):
        nap = patch.object(oz, "_nap")
        nap.start()
        self.addCleanup(nap.stop)
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root = pathlib.Path(tmp.name)

    def write(self, rel, doc):
        path = self.root / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(doc, ensure_ascii=False), encoding="utf-8")

    def markets(self, change=0.56, stamp="2026-11-06T13:10:00+00:00"):
        self.write("data/markets.json", {"updatedAt": stamp, "items": [
            {"id": "BRENT", "value": 98.32, "change": change, "changePct": 0.57, "src": "Yahoo Finance", "at": stamp}]})


class TarixTest(Base):
    def test_window_and_done(self):
        net = Net([("az.wikipedia.org", WIKI)])
        self.assertEqual(oz.tarix_now(at(9, 7, 29), net, set()), [])
        self.assertEqual(net.urls, [], "pəncərədən əvvəl sorğu yoxdur")
        item = oz.tarix_now(at(9, 7, 30), net, set())[0]
        self.assertEqual(head(item), ("tarix", "tarix-2026-11-09", "təqvim", "07:30", True))
        self.assertEqual(item["title"], "Bu gün tarixdə: 9 noyabr — Dövlət Bayrağı Günü")
        self.assertNotIn("skipped", item)
        self.assertEqual(len(net.urls), 1)
        self.assertIn("page=9_noyabr", net.urls[0])
        self.assertEqual(oz.tarix_now(at(9, 7, 50), net, {"tarix-2026-11-09"}), [])
        self.assertEqual(oz.tarix_now(at(9, 8, 10), net, set()), [], "iki cəhdin arası")
        self.assertEqual(len(net.urls), 1, "done-dakı açar üçün və pəncərədən kənar sorğu yoxdur")

    def test_failed_first_try_keeps_the_second_open(self):
        net = Net()
        first = oz.tarix_now(at(9, 7, 35), net, set())[0]
        self.assertEqual((first["key"], first["worth"]), ("tarix-2026-11-09-cehd1", False))
        self.assertIn("Vikipediya alınmadı: OSError; növbəti cəhd saat 08:30-da", first["why"])
        self.assertEqual(oz.tarix_now(at(9, 7, 55), net, {first["key"]}), [])
        self.assertEqual(len(net.urls), 1, "pəncərədə bir sorğu turu")
        second = oz.tarix_now(at(9, 8, 31), net, {first["key"]})[0]
        self.assertEqual((second["key"], second["worth"], second["why"]), ("tarix-2026-11-09", False, "Vikipediya alınmadı: OSError"))
        self.assertEqual(oz.tarix_now(at(9, 8, 50), net, {first["key"], second["key"]}), [])
        self.assertEqual(len(net.urls), 2)
        empty = Net([("az.wikipedia.org", json.dumps({"parse": {"wikitext": "== Bayramlar ==\n"}}))])
        none = oz.tarix_now(at(9, 8, 31), empty, set())[0]
        self.assertEqual((none["key"], none["worth"]), ("tarix-2026-11-09", False))
        self.assertIn("tapılmadı", none["why"])


class AmbTest(Base):
    def test_bulletin_of_today(self):
        net = Net([("07.11.2026", base.AMB_CUR), ("cbar.az", base.AMB_PREV)])
        self.assertEqual(oz.amb_now(at(6, 9, 24), net, set()), [])
        self.assertEqual(net.urls, [])
        item = oz.amb_now(at(6, 9, 30), net, set())[0]
        self.assertEqual(head(item), ("amb", "amb-2026-11-06", "iqtisadiyyat", "09:25", True))
        self.assertEqual(item["title"], "AMB 6 noyabr üçün rəsmi məzənnələri açıqlayıb: avro 1,9037 manat")
        self.assertEqual(len(net.urls), 2, "bu günün və əvvəlki bülleten")
        self.assertEqual(oz.amb_now(at(6, 9, 45), net, {"amb-2026-11-06"}), [])
        self.assertEqual(oz.amb_now(at(6, 10, 10), net, set()), [], "iki cəhdin arası")
        self.assertEqual(len(net.urls), 2)

    def test_bulletin_not_out_yet_then_second_try(self):
        net = Net([("04.11.2026", AMB_OLD), ("cbar.az", base.AMB_PREV)])  # sabahın tarixinə sorğu hələ dünənki bülleteni verir
        first = oz.amb_now(at(6, 9, 30), net, set())[0]
        self.assertEqual((first["key"], first["worth"]), ("amb-2026-11-06-cehd1", False))
        self.assertIn("son bülleten 5 noyabr üçündür; növbəti cəhd saat 10:30-da", first["why"])
        self.assertEqual(oz.amb_now(at(6, 9, 50), net, {first["key"]}), [])
        self.assertEqual(len(net.urls), 2)
        second = oz.amb_now(at(6, 10, 35), net, {first["key"]})[0]
        self.assertEqual((second["key"], second["worth"]), ("amb-2026-11-06", False))
        self.assertEqual(len(net.urls), 4)
        down = oz.amb_now(at(6, 9, 30), Net(), set())[0]
        self.assertEqual((down["key"], down["worth"]), ("amb-2026-11-06-cehd1", False))
        self.assertIn("alınmadı", down["why"])

    def test_weekend_holiday_and_unchanged_rates(self):
        net = Net([("07.11.2026", base.AMB_CUR), ("cbar.az", base.AMB_PREV)])
        self.assertEqual(oz.amb_now(at(7, 9, 30), net, set()), [], "şənbə")
        self.assertEqual(oz.amb_now(at(9, 9, 30), net, set()), [], "9 noyabr iş günü deyil")
        self.assertEqual(net.urls, [])
        rows = [("USD", "1 ABŞ dolları", "1.7"), ("EUR", "1 Avro", "1.9037")]
        same = Net([("07.11.2026", base._amb("06.11.2026", rows)), ("cbar.az", base._amb("05.11.2026", rows))])
        item = oz.amb_now(at(6, 9, 30), same, set())[0]
        self.assertEqual((item["key"], item["worth"], item["why"]), ("amb-2026-11-06", False, "məzənnələr əvvəlki bülletendən fərqlənmir"))


class OilTest(Base):
    def test_window_freshness_and_done(self):
        self.markets()
        self.assertEqual(oz.oil_now(self.root, at(6, 16, 59), set()), [])
        item = oz.oil_now(self.root, at(6, 17, 20), set())[0]
        self.assertEqual(head(item), ("neft", "neft-2026-11-06", "iqtisadiyyat", "17:00", True))
        self.assertEqual(item["title"], "Brent nefti bahalaşıb: bareli 98,32 dollar")
        self.assertEqual(oz.oil_now(self.root, at(6, 17, 30), {"neft-2026-11-06"}), [])
        self.assertEqual(oz.oil_now(self.root, at(6, 18, 30), set()), [], "fayl 1 saatdan köhnədir: növbəti dövrədə yenə baxılır")
        self.assertEqual(oz.oil_now(self.root, at(6, 19, 0), set()), [])
        self.assertEqual(oz.oil_now(self.root / "yoxdur", at(6, 17, 20), set()), [])
        self.markets(stamp="2026-11-06T08:00:00+00:00")
        self.assertEqual(oz.oil_now(self.root, at(6, 12, 1), set()), [])
        self.assertEqual(len(oz.oil_now(self.root, at(6, 12, 1), set(), window=False)), 1, "sınaq pəncərəyə baxmır")

    def test_flat_price_weekend_and_broken_file(self):
        self.markets(change=0)
        flat = oz.oil_now(self.root, at(6, 17, 20), set())[0]
        self.assertEqual((flat["key"], flat["worth"], flat["why"]), ("neft-2026-11-06", False, "qiymət əvvəlki bağlanışdan fərqlənmir"))
        self.markets(stamp="2026-11-07T13:10:00+00:00")
        self.assertEqual(oz.oil_now(self.root, at(7, 17, 20), set()), [], "şənbə")
        (self.root / "data" / "markets.json").write_text("{", encoding="utf-8")
        self.assertEqual(oz.oil_now(self.root, at(6, 17, 20), set()), [])


class SeysTest(Base):
    def test_hourly_check_details_and_done(self):
        net = Net([("/zelzele/536", base.SEYS_536), ("/zelzeleler", base.SEYS_LIST_PAGE)])
        got = oz.seys_now(at(19, 12, 0, month=10), net, set())
        self.assertEqual([i["key"] for i in got], ["seys-sorgu-2026-10-19T12", "zelzele-536"])
        self.assertEqual((got[0]["worth"], got[0]["why"]), (False, "yeni təkan: 2"))
        self.assertEqual(head(got[1]), ("zelzele", "zelzele-536", "təbiət", "12:00", True))
        self.assertEqual(got[1]["title"], "İsmayıllıda 3,0 maqnitudalı zəlzələ olub")
        self.assertEqual(net.urls, [oz.SEYS_LIST, "https://seismology.az/az/zelzele/536", "https://seismology.az/az/zelzele/535"])
        seen = {i["key"] for i in got}
        self.assertEqual(oz.seys_now(at(19, 12, 30, month=10), net, seen), [])
        self.assertEqual(len(net.urls), 3, "saatda bir yoxlama")
        nxt = oz.seys_now(at(19, 13, 5, month=10), net, seen)
        self.assertEqual([i["key"] for i in nxt], ["seys-sorgu-2026-10-19T13"], "səhifəsi alınmayan təkan yenə yoxlanır, açarı qayıtmır")
        self.assertEqual(net.urls[3:], [oz.SEYS_LIST, "https://seismology.az/az/zelzele/535"])

    def test_old_quakes_and_dead_site(self):
        late = Net([("/zelzeleler", base.SEYS_LIST_PAGE)])
        got = oz.seys_now(at(19, 18, 0, month=10), late, set())
        self.assertEqual([(i["key"], i["why"]) for i in got], [("seys-sorgu-2026-10-19T18", "yeni təkan: 0")])
        self.assertEqual(len(late.urls), 1, "6 saatdan köhnə təkanın səhifəsi açılmır")
        down = oz.seys_now(at(19, 12, 0, month=10), Net(), set())
        self.assertEqual([(i["key"], i["worth"]) for i in down], [("seys-sorgu-2026-10-19T12", False)])
        self.assertIn("alınmadı", down[0]["why"])


class PflTest(Base):
    def test_reports_after_the_game_with_referee_from_pfl(self):
        self.write("data/futbol/premyer-liqa.json", LOCAL)
        net = Net(PFL_PAGES)
        self.assertEqual(oz.pfl_now(self.root, at(6, 19, 49), net, set()), [])
        self.assertEqual(net.urls, [], "bitmiş oyun pəncərəyə düşməyibsə sorğu yoxdur")
        one = oz.pfl_now(self.root, at(6, 21, 49), Net(PFL_PAGES), set())
        self.assertEqual([i["key"] for i in one], ["pfl-2026-t11-qarabag-turan-tovuz"])
        got = oz.pfl_now(self.root, at(6, 22, 10), net, set())
        self.assertEqual([i["key"] for i in got], ["pfl-2026-t11-neftci-kepez", "pfl-2026-t11-qarabag-turan-tovuz"])
        self.assertEqual(head(got[0]), ("futbol", "pfl-2026-t11-neftci-kepez", "idman", "21:50", True))
        self.assertEqual((got[0]["date"], got[1]["slot"]), ("2026-11-06", "19:50"))
        self.assertEqual(got[0]["title"], "«Neftçi» «Kəpəz»i 1:0 hesabı ilə məğlub edib")
        self.assertEqual(got[0]["body"], ["Oyun 6 noyabrda Palms Sports Arena stadionunda keçirilib. Görüşü İnqilab Məmmədov idarə edib. "
                                          "Oyunu 550 azarkeş izləyib. Bu nəticədən sonra «Neftçi» 24 xalla 1-ci, «Kəpəz» 9 xalla 11-ci yerdədir."])
        self.assertEqual(got[1]["title"], "«Turan Tovuz» səfərdə «Qarabağ»ı 1:0 hesabı ilə məğlub edib")
        self.assertEqual(got[1]["body"], ["Oyun 6 noyabrda Tovuz şəhər stadionunda keçirilib."],
                         "«st.» açılır; hakim alınmayıb; Qarabağın cədvəl sətri bütün oyunlarını saymır, yer yazılmır")
        self.assertEqual([u[len(oz.PFL_API):].split("?")[0] for u in net.urls], ["/seasons", "/tours/get-games", "/games/show/6851", "/games/show/6852"])
        self.assertEqual(oz.pfl_now(self.root, at(6, 22, 20), net, {i["key"] for i in got}), [])
        self.assertEqual(len(net.urls), 4, "done-dakı oyun üçün sorğu yoxdur")
        self.assertEqual(oz.pfl_now(self.root, at(7, 2, 0), net, set()), [], "6 saatdan sonra hesabat yoxdur")

    def test_pfl_down_and_score_mismatch(self):
        self.write("data/futbol/premyer-liqa.json", LOCAL)
        down = Net()
        got = oz.pfl_now(self.root, at(6, 22, 10), down, set())
        self.assertEqual([(i["key"], i["worth"]) for i in got], [("pfl-2026-t11-neftci-kepez", True), ("pfl-2026-t11-qarabag-turan-tovuz", True)])
        self.assertEqual(got[0]["body"], ["Oyun 6 noyabrda Palms Sports Arena stadionunda keçirilib. "
                                          "Bu nəticədən sonra «Neftçi» 24 xalla 1-ci, «Kəpəz» 9 xalla 11-ci yerdədir."])
        self.assertEqual(len(down.urls), 1, "pfl.az alınmayanda hesabat saytın öz məlumatı ilə çıxır")
        other = json.loads(json.dumps(LOCAL))
        other["games"][0]["hs"] = 2
        self.write("data/futbol/premyer-liqa.json", other)
        bad = oz.pfl_now(self.root, at(6, 22, 10), Net(PFL_PAGES), set())[0]
        self.assertEqual((bad["key"], bad["worth"]), ("pfl-2026-t11-neftci-kepez", False))
        self.assertIn("fərqlidir", bad["why"])
        self.assertEqual(oz._pfl_stadium("Zirə İK stadionu"), "Zirə İK stadionu")
        self.assertEqual(oz._pfl_stadium("T. Bəhramov ad. Respublika st."), "", "başqa qısaltması olan ad yazılmır")


class ItemsTest(Base):
    def test_every_part_runs_and_done_stops_requests(self):
        net = Net([("az.wikipedia.org", WIKI), ("/zelzeleler", base.SEYS_LIST_PAGE)])
        got = oz.items(self.root, at(9, 7, 31), net, set())
        self.assertEqual([i["key"] for i in got], ["tarix-2026-11-09", "seys-sorgu-2026-11-09T07"])
        self.assertEqual([i["worth"] for i in got], [True, False])
        for i in got:
            self.assertEqual([f for f in FIELDS if f not in i], [], i["key"])
            self.assertTrue(i["worth"] or i["why"])
        self.assertEqual(len(net.urls), 2)
        self.assertEqual(oz.items(self.root, at(9, 7, 40), net, {i["key"] for i in got}), [])
        self.assertEqual(len(net.urls), 2)
        self.assertEqual(oz.items(self.root, "vaxt deyil", net), [])
        naive = oz.items(self.root, datetime.datetime(2026, 11, 9, 7, 45), Net(), None)
        self.assertEqual([i["key"] for i in naive], ["tarix-2026-11-09-cehd1", "seys-sorgu-2026-11-09T07"])

    def test_a_failing_part_and_the_leadership_guard(self):
        with patch.object(oz, "tarix_now", side_effect=RuntimeError("pozuq")):
            got = oz.items(self.root, at(9, 7, 31), Net(), set())
        self.assertEqual([(i["key"], i["worth"]) for i in got], [("baza-xeta-tarix-2026-11-09T07", False), ("seys-sorgu-2026-11-09T07", False)])
        page = base.SEYS_536.replace("Zəlzələ Zərnəva", "Prezident İlham Əliyev bölgəyə gedib. Zəlzələ Zərnəva")
        net = Net([("/zelzele/536", page), ("/zelzeleler", base.SEYS_LIST_PAGE)])
        quake = oz.items(self.root, at(19, 12, 0, month=10), net, set())[1]
        self.assertEqual((quake["key"], quake["worth"]), ("zelzele-536", False))
        self.assertIn("rəhbərliyin adı", quake["why"])

    def test_window_samples(self):
        self.markets()
        self.write("data/futbol/premyer-liqa.json", LOCAL)
        net = Net([("az.wikipedia.org", WIKI), ("07.11.2026", base.AMB_CUR), ("cbar.az", base.AMB_PREV),
                   ("/zelzele/536", base.SEYS_536), ("/zelzeleler", base.SEYS_LIST_PAGE), *PFL_PAGES])
        md = "\n".join(oz.baza_sinaq(self.root, at(6, 12, 0), net))
        for title in ("### Bu gün tarixdə: 6 noyabr — Dövlət Bayrağı Günü", "### AMB 6 noyabr üçün rəsmi məzənnələri açıqlayıb: avro 1,9037 manat",
                      "### Brent nefti bahalaşıb: bareli 98,32 dollar", "### İsmayıllıda 3,0 maqnitudalı zəlzələ olub",
                      "### «Neftçi» «Kəpəz»i 1:0 hesabı ilə məğlub edib", "### «Turan Tovuz» səfərdə «Qarabağ»ı 1:0 hesabı ilə məğlub edib"):
            self.assertIn(title, md)
        self.assertIn("✅ Dərc olunardı (`amb-2026-11-06`, mövzu: iqtisadiyyat, slot: 10:30)", md)
        dead = "\n".join(oz.baza_sinaq(self.root / "yoxdur", at(6, 12, 0), Net()))
        self.assertIn("⏭ Dərc olunmazdı (`tarix-2026-11-06`): Vikipediya alınmadı: OSError", dead)
        self.assertIn("Saytın faylında bitmiş oyun yoxdur.", dead)


if __name__ == "__main__":
    unittest.main()
