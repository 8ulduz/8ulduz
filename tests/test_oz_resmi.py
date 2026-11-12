"""Rəsmi məlumat xəbərləri (oz_resmi.py, mərhələ 3): Nazirlər Kabinetinin sənədləri, tikinti icazələri, ANAMA-nın aylıq
statistikası, dissertasiya müdafiələri, Əmlak Xidmətinin hərrac elanları və nəticələri.
Şəbəkə yoxdur: tests/fixtures/oz_resmi/ — mənbələrin 2026-11-10 və 2026-11-12 tarixli real cavablarından kəsiklər
(tikinti reyestrində fiziki şəxslərin adları əvəz olunub)."""
import contextlib
import datetime
import io
import json
import pathlib
import re
import unittest
from unittest.mock import patch

import oz_derc
import oz_gundelik as og
import oz_resmi as r
import oz_xeber as ox

ROOT = pathlib.Path(__file__).resolve().parent.parent
FIX = ROOT / "tests" / "fixtures" / "oz_resmi"
D = datetime.date
KEYS = {"kind", "key", "title", "lead", "body", "credit", "link", "topic", "slot", "worth"}
LEADER = "Prezident İlham Əliyev"
NETICE_URL = r.EMLAK_SITE + "/az/news/view/10629-novbeti-herracda-67-neqliyyat-vasitesi-satilib"
W1, W2 = D(2026, 11, 2), D(2026, 11, 8)
_PAUSE = og.PAUSE


def setUpModule():
    og.PAUSE = 0  # testdə saytlar arasında gözləmə yoxdur


def tearDownModule():
    og.PAUSE = _PAUSE


def at(y, m, d, hh, mm=0):
    return datetime.datetime(y, m, d, hh, mm, tzinfo=r.BAKU)


def raw(name):
    return (FIX / name).read_bytes()


def text(name):
    return raw(name).decode("utf-8")


def pages(emlak="emlak-2026-11-12.html"):
    return {
        r.NK_URL: raw("nk-2026-11-12.html"),
        r.tik_url(0, W1, W2): raw("tik-2026-11-02-p0.json"),
        r.tik_url(1, W1, W2): raw("tik-2026-11-02-p1.json"),
        r.tik_url(2, W1, W2): raw("tik-2026-11-02-p2.json"),
        r.tik_url(0, D(2026, 10, 26), D(2026, 11, 1)): raw("tik-2026-10-26-p0.json"),
        r.ANAMA_URL: raw("anama-2026-11-12.json"),
        r.AAK_URL: raw("aak-2026-11-12.html"),
        r.EMLAK_URL: raw(emlak),
        NETICE_URL: raw("emlak-10629.html"),
    }


class Fake:
    """Saxta fetch: ünvan -> bayt; siyahıda olmayan ünvan və Exception dəyəri xəta verir. Çağırışlar calls-dadır."""

    def __init__(self, table):
        self.table, self.calls, self.headers = table, [], []

    def __call__(self, url, timeout=None, headers=None):
        self.calls.append(url)
        self.headers.append(headers)
        value = self.table.get(url)
        if value is None:
            raise OSError("ünvan yoxdur")
        if isinstance(value, Exception):
            raise value
        return value


def blob(item):
    return "\n".join([item["title"], item["lead"], *item["body"]])


def nk():
    return r.nk_docs(text("nk-2026-11-12.html"))


def week():
    rows = r.tik_page(raw("tik-2026-11-02-p0.json"))[0] + r.tik_page(raw("tik-2026-11-02-p1.json"))[0]
    return rows, 37


def aak():
    return r.aak_rows(text("aak-2026-11-12.html"))


def posts(name="emlak-2026-11-12.html"):
    return r.emlak_posts(text(name))


def netice_row():
    return next(x for x in r.emlak_news(text("emlak-2026-11-12.html")) if x["id"] == 10629)


class FormatTest(unittest.TestCase):
    def test_small_helpers(self):
        self.assertEqual([r._month("Noyabr"), r._month("dekabr"), r._month("İyun"), r._month("Noy"), r._month("")], [11, 12, 6, None, None])
        self.assertEqual([r._lower1("İqtisad elmləri"), r._lower1("Kimya"), r._lower1("")], ["iqtisad elmləri", "kimya", ""])
        self.assertEqual(r._cut("bir iki üç", 20), "bir iki üç")
        self.assertEqual(r._cut("bir iki, üç dörd", 9), "bir iki…")
        self.assertEqual(r._tally(["b", "a", "b", "ç", "c"]), [("b", 2), ("a", 1), ("c", 1), ("ç", 1)])
        self.assertEqual(r._tally([("x", "b"), ("x", "a"), ("x", "b")]), [(("x", "b"), 2), (("x", "a"), 1)])
        self.assertEqual([r._md_date(3, 11, D(2026, 11, 12)), r._md_date(3, 11, D(2026, 11, 2)), r._md_date(31, 2, D(2026, 11, 2))],
                         [D(2026, 11, 3), D(2025, 11, 3), None])

    def test_title_rotation_skips_forms_that_do_not_fit(self):
        forms = ["a", "b", "c"]
        self.assertEqual([r._pick(forms, n) for n in range(4)], ["a", "b", "c", "a"])
        self.assertEqual(r._pick(["x" * 111, "qısa", "y" * 120], 0), "qısa")
        self.assertEqual(r._pick(["x" * 111, "qısa", "y" * 120], 2), "qısa")
        self.assertEqual(r._pick(["x" * 111, "y" * 120], 1), "y" * 120)

    def test_leadership_filter_is_stricter_than_the_publisher(self):
        decree = ("“Azərbaycan Respublikası Maliyyə Nazirliyinin fəaliyyətinin təkmilləşdirilməsi ilə bağlı əlavə tədbirlər haqqında” "
                  "Azərbaycan Respublikası Prezidentinin 2025-ci il 30 dekabr tarixli 572 nömrəli Fərmanının icrası ilə əlaqədar")
        for bad in (decree, LEADER, "Birinci vitse-prezident", "Heydər Əliyev adına Azərbaycan Ali Hərbi Məktəbi", "DÖVLƏT BAŞÇISI"):
            self.assertTrue(r._leader(bad), bad)
        for good in ("Əliyeva Samirə Əmiraslan qızı", "Əliyev Cavad Rasim oğlu", "Nazirlər Kabinetinin 374 nömrəli qərarı", ""):
            self.assertFalse(r._leader(good), good)


class NkTest(unittest.TestCase):
    def test_documents_from_real_page(self):
        docs = nk()
        self.assertEqual(len(docs), 18)
        self.assertEqual([d["id"] for d in docs], list(range(9877, 9859, -1)))
        first = docs[0]
        self.assertEqual((first["kind"], first["num"], first["when"]), ("qərar", "377", at(2026, 11, 12, 15, 5)))
        self.assertEqual(first["path"], "/az/senedler/qerarlar/azerbaycan-respublikasinin-nazirler-kabineti-yanin-9877")
        self.assertTrue(first["title"].startswith("“Azərbaycan Respublikasının Nazirlər Kabineti yanında uşaq hüquqlarının"))
        order = next(d for d in docs if d["id"] == 9870)
        self.assertEqual((order["kind"], order["num"], order["when"]), ("sərəncam", "826s", at(2026, 11, 3, 16, 12)))
        self.assertEqual(sum(1 for d in docs if d["kind"] == "sərəncam"), 5)

    def test_day_with_decisions_one_title_withheld(self):
        item = r.nk_item(nk(), D(2026, 11, 5))
        self.assertTrue(item["worth"])
        self.assertEqual(item["key"], "nk-sened-2026-11-05")
        self.assertEqual(item["title"], "Hökumətin yeni sənədləri: noyabrın 5-də 5 qərar dərc olunub")
        self.assertEqual(item["lead"], "Nazirlər Kabinetinin saytında noyabrın 5-də 5 qərar yerləşdirilib. "
                                       "Aşağıda onlardan 4 sənədin adı verilir.")
        self.assertEqual([b.split(":")[0] for b in item["body"]], ["371 nömrəli qərar", "372 nömrəli qərar", "373 nömrəli qərar", "374 nömrəli qərar"])
        self.assertEqual(item["body"][3], "374 nömrəli qərar: Azərbaycan Respublikası Nazirlər Kabinetinin 2024-cü il 1 avqust tarixli 372 "
                                          "nömrəli Qərarı ilə təsdiq edilmiş “Təbii inhisar subyektlərinin Siyahısı”nda dəyişiklik edilməsi haqqında")
        self.assertNotIn("rezident", blob(item))
        self.assertEqual((item["link"], item["topic"], item["slot"], item["list"]), (r.NK_URL, "rəsmi", "09:30", True))
        self.assertEqual(r._guard(item), item)

    def test_day_with_decisions_and_orders(self):
        item = r.nk_item(nk(), D(2026, 11, 3))
        self.assertEqual(item["title"], "Nazirlər Kabinetinin saytında noyabrın 3-də 4 qərar və 5 sərəncam yerləşdirilib")
        self.assertEqual(item["lead"], "Nazirlər Kabinetinin saytında noyabrın 3-də 9 sənəd yerləşdirilib: 4 qərar və 5 sərəncam. "
                                       "Aşağıda onlardan 6 sənədin adı verilir.")
        self.assertEqual([b.split(":")[0] for b in item["body"]],
                         ["367 nömrəli qərar", "368 nömrəli qərar", "369 nömrəli qərar", "370 nömrəli qərar",
                          "821s nömrəli sərəncam", "826s nömrəli sərəncam"])
        long = item["body"][2]   # 369: 600 hərfdən uzun ad kəsilir
        self.assertTrue(long.endswith("…") and len(long) < r.NK_TITLE + 30, long)
        self.assertNotIn("rezident", blob(item))
        self.assertTrue(r._guard(item)["worth"])

    def test_single_document(self):
        item = r.nk_item(nk(), D(2026, 11, 6))
        self.assertEqual(item["title"], "Nazirlər Kabinetinin 376 nömrəli qərarı dərc olunub")
        self.assertEqual(item["lead"], "Nazirlər Kabinetinin saytında noyabrın 6-da 376 nömrəli qərar yerləşdirilib. Sənədin adı aşağıdadır.")
        self.assertEqual(item["body"], ["376 nömrəli qərar: Azərbaycan Respublikası Nazirlər Kabinetinin 2023-cü il 2 may tarixli 140 nömrəli "
                                        "Qərarı ilə təsdiq edilmiş “Məhkəmə Ekspertlərinin Reyestrinin aparılması Qaydaları”nda dəyişiklik edilməsi haqqında"])
        self.assertEqual(item["link"], "https://nk.gov.az/az/senedler/qerarlar/azerbaycan-respublikasi-nazirler-kabinetinin-2023-9876")
        full = r.nk_item([d for d in nk() if d["id"] != 9875], D(2026, 11, 5))
        self.assertTrue(full["lead"].endswith("4 qərar yerləşdirilib. Sənədlərin adları aşağıdadır."), full["lead"])

    def test_no_documents_incomplete_list_or_only_leadership(self):
        docs = nk()
        for day, why in ((D(2026, 11, 8), "yerləşdirilməyib"), (D(2026, 10, 30), "siyahının sonu"), (D(2026, 10, 1), "siyahının sonu")):
            item = r.nk_item(docs, day)
            self.assertFalse(item["worth"], day)
            self.assertIn(why, item["why"])
            self.assertEqual(item["key"], f"nk-sened-{day.isoformat()}")
        self.assertIn("natamamdır", r.nk_item(docs[:5], D(2026, 11, 5))["why"])
        self.assertIn("natamamdır", r.nk_item(docs + docs[:1], D(2026, 11, 5))["why"])
        only = [d for d in docs if d["when"].date() != D(2026, 11, 3) or r._leader(d["title"])]
        self.assertEqual(sum(1 for d in only if d["when"].date() == D(2026, 11, 3)), 3)
        item = r.nk_item(only, D(2026, 11, 3))
        self.assertFalse(item["worth"])
        self.assertIn("rəhbərlik", item["why"])
        self.assertNotIn("rezident", blob(item))

    def test_broken_pages(self):
        page = text("nk-2026-11-12.html")
        self.assertEqual(r.nk_docs("<html><body>boş</body></html>"), [])
        for bad in (page.replace("№ 377", "№ 377s"), page.replace("12 Noyabr 2026 - 15:05", "12 Noyabr 2026"),
                    page.replace("12 Noyabr 2026 - 15:05", "12 Brumaire 2026 - 15:05"),
                    page.replace('<span class="doc-type">Qərarlar</span>', '<span class="doc-type">Sərəncamlar</span>', 1),
                    page.replace('href="/az/senedler/qerarlar/azerbaycan-respublikasinin-nazirler-kabineti-yanin-9877"', 'href="#"')):
            with self.assertRaises(ValueError):
                r.nk_docs(bad)
        letters = page.replace("/az/senedler/qerarlar/azerbaycan-respublikasinin-nazirler-kabineti-yanin-9877", "/az/senedler/mektublar/mektub-9877")
        self.assertEqual(len(r.nk_docs(letters)), 17, "başqa növ sənəd buraxılır")


class TikTest(unittest.TestCase):
    def test_page_and_paging(self):
        rows, count = r.tik_page(raw("tik-2026-11-02-p0.json"))
        self.assertEqual((len(rows), count), (25, 37))
        self.assertEqual(rows[0], {"id": 23634, "status": "Tikintiyə İcazə", "name": "Yaşayış binaları", "date": D(2026, 11, 5),
                                   "address": "Gəncə şəhəri, Nizami prospekti ilə Kimyaçılar küçəsinin kəsişməsinin şimal-qərbi"})
        fake = Fake(pages())
        rows, count = r.tik_get(og._Net(fake), W1, W2)
        self.assertEqual((len(rows), count, len({x["id"] for x in rows})), (37, 37, 37))
        self.assertEqual(fake.calls, [r.tik_url(0, W1, W2), r.tik_url(1, W1, W2)])
        self.assertIn("registerDateBegin=2026-11-02&registerDateEnd=2026-11-08", fake.calls[0])

    def test_area_keeps_only_city_district_village(self):
        for address, area in (
                ("Gəncə şəhəri, Nizami prospekti ilə Kimyaçılar küçəsinin kəsişməsinin şimal-qərbi", "Gəncə şəhəri"),
                ("AZ 6619, Yevlax şəhəri, Yuxarı Salamabad kəndi, Alı Mustafayev küçəsi, giriş 47", "Yevlax şəhəri, Yuxarı Salamabad kəndi"),
                ("Bakı şəhəri, Xətai rayonu, 8 Noyabr prospekti, 36 (PD-045/046/047 saylı ərazi)", "Bakı şəhəri, Xətai rayonu"),
                ("Bakı şəhəri, Qaradağ rayonu, Lökbatan qəsəbəsi, 28 May küçəsi", "Bakı şəhəri, Qaradağ rayonu, Lökbatan qəsəbəsi"),
                ("Qubadlı və Laçın rayonları", "Qubadlı və Laçın rayonları"), ("Şuşa şəhəri", "Şuşa şəhəri"),
                ("Məhəmməd Füzuli küçəsi, ev 87", ""), ("", "")):
            self.assertEqual(r.tik_area(address), area, address)

    def test_weekly_item(self):
        rows, count = week()
        item = r.tik_item(rows, count, W1, W2, 25)
        self.assertTrue(item["worth"])
        self.assertEqual(item["key"], "tikinti-hefte-2026-11-02")
        self.assertEqual(item["title"], "2–8 noyabr tarixlərində 37 tikinti icazəsi reyestrə daxil edilib")
        self.assertEqual(item["lead"], "Tikintilərin Dövlət Reyestrinin məlumatına görə, 2–8 noyabr tarixlərində reyestrə 37 tikinti icazəsi "
                                       "daxil edilib. Bir həftə əvvəl (26 oktyabr – 1 noyabr) bu say 25 olub. İcazələrin obyekt adı və ərazi "
                                       "üzrə bölgüsü aşağıdadır.")
        self.assertEqual(item["body"][:5], [
            "Zəngilan kənd yaşayış məntəqəsi (II mərhələ) (Zəngilan rayonu, Zəngilan kəndi) – 16 icazə",
            "Yaşayış binaları (Gəncə şəhəri) – 4 icazə",
            "\"İşğal və Zəfər\" Muzeyləri Kompleksi (Zəngilan şəhəri) – 3 icazə",
            "110/10 kV-luq \"Xankəndi-2\" yarımstansiyası (Xankəndi şəhəri) – 3 icazə",
            "Qeyri-yaşayış (soyuducu anbar və məişət) binası (Cəlilabad şəhəri) – 2 icazə"])
        self.assertEqual((len(item["body"]), item["body"][-1]), (11, "Digər obyektlər – 4 icazə"))
        self.assertEqual(sum(int(re.search(r"– (\d+) icazə$", b).group(1)) for b in item["body"]), 37, "siyahının cəmi saya bərabərdir")
        for private in ("oğlu", "qızı", "Filankəs", "küçəsi", "giriş", "prospekti"):
            self.assertNotIn(private, blob(item))
        self.assertEqual((item["topic"], item["slot"], item["link"], item["credit"]), ("gündəlik", "10:00", r.TIK_PAGE, r.TIK_CREDIT))
        self.assertNotIn("Bir həftə əvvəl", r.tik_item(rows, count, W1, W2)["lead"])

    def test_count_must_confirm_itself(self):
        rows, count = week()
        for bad_rows, bad_count, why in ((rows[:-1], 37, "təsdiqləmir"), (rows, 38, "təsdiqləmir"), ([], 0, "daxil edilməyib"),
                                         ([dict(rows[0], status="Tikinti niyyəti")] + rows[1:], 37, "uyğun deyil"),
                                         ([dict(rows[0], date=D(2026, 11, 9))] + rows[1:], 37, "uyğun deyil")):
            item = r.tik_item(bad_rows, bad_count, W1, W2, 25)
            self.assertFalse(item["worth"])
            self.assertIn(why, item["why"])
            self.assertEqual(item["key"], "tikinti-hefte-2026-11-02")

    def test_leadership_line_goes_to_the_remainder(self):
        rows, count = week()
        rows = [dict(x, name="Heydər Əliyev Mərkəzi") if x["name"] == "Yaşayış binaları" else x for x in rows]
        item = r.tik_item(rows, count, W1, W2)
        self.assertFalse(r._leader(blob(item)))
        self.assertEqual(item["body"][-1], "Digər obyektlər – 7 icazə")
        self.assertTrue(r._guard(item)["worth"])

    def test_garbage_is_an_error(self):
        for bad in (b"<html>", b"[]", b'{"data": {}, "count": "1"}', b'{"data": [], "count": null}', b'{"data": [{"id": "x"}], "count": "1"}',
                    b'{"data": [{"id": 1, "name": "", "reyestrDate": "2026-11-05"}], "count": "1"}',
                    b'{"data": [{"id": 1, "name": "Bina", "reyestrDate": "05.11.2026"}], "count": "1"}'):
            with self.assertRaises(ValueError):
                r.tik_page(bad)
        changed = json.loads(raw("tik-2026-11-02-p1.json"))
        changed["count"] = "38"
        with self.assertRaises(ValueError):
            r.tik_get(og._Net(Fake(dict(pages(), **{r.tik_url(1, W1, W2): json.dumps(changed).encode()}))), W1, W2)


class AnamaTest(unittest.TestCase):
    def stat(self, **change):
        doc = json.loads(raw("anama-2026-11-12.json"))
        doc.update(change)
        return r.anama_stat(json.dumps(doc).encode("utf-8"))

    def test_stat_from_real_answer(self):
        self.assertEqual(r.anama_stat(raw("anama-2026-11-12.json")),
                         {"month": 10, "area": 4898, "pedestrian": 799, "tank": 180, "other": 3070, "updated": at(2026, 11, 3, 16, 10).replace(second=46)})

    def test_fresh_monthly_block(self):
        item = r.anama_item(self.stat(), D(2026, 11, 4))
        self.assertTrue(item["worth"])
        self.assertEqual(item["key"], "anama-ay-2026-10")
        self.assertEqual(item["title"], "ANAMA oktyabr ayının statistikasını açıqlayıb: 4 898 hektar ərazi təmizlənib")
        self.assertEqual(item["lead"], "Minatəmizləmə Agentliyinin (ANAMA) statistikasına görə, 2026-cı ilin oktyabr ayında 4 898 hektar ərazi "
                                       "təmizlənib. Aylıq göstəricilərdə 799 piyada əleyhinə mina, 180 tank əleyhinə mina və 3 070 digər "
                                       "partlayıcı sursat qeyd olunub.")
        self.assertEqual((item["body"], item["topic"], item["slot"], item["link"]), ([], "rəsmi", "11:00", r.ANAMA_PAGE))
        self.assertTrue(r.anama_item(self.stat(), D(2026, 11, 3))["worth"])
        self.assertTrue(r.anama_item(self.stat(), D(2026, 11, 5))["worth"])

    def test_other_title_forms_and_january(self):
        nov = r.anama_item(self.stat(monthly_interval="Noyabr", updated_at="2026-12-02T08:00:00.000000Z"), D(2026, 12, 3))
        self.assertEqual(nov["title"], "ANAMA-nın noyabr statistikası: 4 898 hektar təmizlənmiş ərazi, 979 mina")
        dec = r.anama_item(self.stat(monthly_interval="Dekabr", updated_at="2027-01-04T08:00:00.000000Z"), D(2027, 1, 5))
        self.assertEqual((dec["key"], dec["title"]), ("anama-ay-2026-12", "Minatəmizləmə Agentliyi: dekabrda 4 898 hektar ərazi təmizlənib"))
        self.assertIn("2026-cı ilin dekabr ayında", dec["lead"])
        apr = r.anama_item(self.stat(monthly_interval="Aprel", updated_at="2027-05-04T08:00:00.000000Z"), D(2027, 5, 5))
        self.assertEqual(apr["title"], "ANAMA aprel ayının statistikasını açıqlayıb: 4 898 hektar ərazi təmizlənib")

    def test_stale_or_mismatched_block_is_not_news(self):
        for item, why in ((r.anama_item(self.stat(), D(2026, 11, 12)), "təzə deyil"), (r.anama_item(self.stat(), D(2026, 11, 6)), "təzə deyil"),
                          (r.anama_item(self.stat(), D(2026, 11, 2)), "təzə deyil"),
                          (r.anama_item(self.stat(monthly_interval="Sentyabr"), D(2026, 11, 4)), "əvvəlki ay deyil"),
                          (r.anama_item(self.stat(monthly_interval="Noyabr"), D(2026, 11, 4)), "əvvəlki ay deyil")):
            self.assertFalse(item["worth"])
            self.assertIn(why, item["why"])
            self.assertTrue(item["key"].startswith("anama-yoxla-2026-11-"), item["key"])

    def test_broken_answers(self):
        for change in ({"monthly_interval": "October"}, {"monthly_interval": None}, {"clean_area_monthly": "4898"}, {"clean_area_monthly": 0},
                       {"tank_monthly": -1}, {"pedestrian_monthly": None}, {"unexplosive_monthly": 3070.5}, {"updated_at": "dünən"},
                       {"updated_at": None}):
            with self.assertRaises(ValueError, msg=str(change)):
                self.stat(**change)
        for bad in (b"<html>", b"[]", b""):
            with self.assertRaises(ValueError):
                r.anama_stat(bad)


class AakTest(unittest.TestCase):
    def test_rows_from_real_page(self):
        rows = aak()
        self.assertEqual(len(rows), 12)
        self.assertEqual(rows[0], {"date": D(2026, 11, 12), "name": "Hüseynova Gülnar Adıgözəl qızı", "field": "Kimya", "degree": "Fəlsəfə doktoru",
                                   "title": "Fəza-çətinlikli metiltsikloalkilfenolların aminometil törəmələrinin sintezi və onların bəzi ağır "
                                            "metalların analizində tətbiqi",
                                   "place": "ETN akademik Y.H.Məmmədəliyev adına Neft-Kimya Prosesləri İnstitutu, Bakı şəh., Xocalı pr., 30."})
        self.assertEqual([x["date"].day for x in rows], [12, 13, 13, 13, 17, 17, 17, 17, 17, 20, 20, 20])

    def test_day_with_two_fields(self):
        item = r.aak_item(aak(), D(2026, 11, 13), D(2026, 11, 12))
        self.assertTrue(item["worth"])
        self.assertEqual(item["key"], "aak-mudafie-2026-11-13")
        self.assertEqual(item["title"], "3 dissertasiya noyabrın 13-də müdafiə olunacaq: filologiya elmləri üzrə 2, kimya üzrə 1")
        self.assertEqual(item["lead"], "Ali Attestasiya Komissiyasının elanlarına görə, noyabrın 13-də 3 dissertasiya müdafiəsi keçiriləcək: "
                                       "filologiya elmləri üzrə 2, kimya üzrə 1. İddia olunan elmi dərəcə: fəlsəfə doktoru.")
        self.assertEqual(item["body"], [
            "Eyyubova Esmira Cəlil qızı — «Dəmirin (III) yeni qatılaşdırma metodikalarının işlənilməsi və analitik tətbiqi» (kimya). "
            "Müdafiə yeri: Bakı Dövlət Universiteti, Bakı şəh. Z.Xəlilov küç. 33",
            "Əliyeva Samirə Əmiraslan qızı — «Nizami Gəncəvinin “Xosrov və Şirin” əsəri Fəxrəddin Yaqub İbn Məhəmməd Fəxrinin tərcüməsində: "
            "orijinallıq və bədiilik» (filologiya elmləri). Müdafiə yeri: AMEA Nizami Gəncəvi adına Ədəbiyyat İnstitutu, Bakı şəh. H.Cavid pr. 117",
            "Ələkbərova Nuranə Ramiz qızı — «Məcruh Muğani “Divan”ının tekstoloji tədqiqi və leksikası» (filologiya elmləri). Müdafiə yeri: "
            "Nizami Gəncəvi adına Milli Azərbaycan Ədəbiyyatı Muzeyi, Bakı şəh. İstiqlaliyyət küç. 53"])
        self.assertEqual((item["topic"], item["slot"], item["link"], item["credit"]), ("təhsil", "16:00", r.AAK_URL, "Ali Attestasiya Komissiyası"))
        self.assertEqual(r._guard(item), item, "namizədin soyadı «Əliyeva» rəhbərlik deyil")

    def test_one_field_and_three_fields(self):
        one = r.aak_item(aak(), D(2026, 11, 12), D(2026, 11, 11))
        self.assertEqual(one["title"], "Noyabrın 12-də kimya üzrə 1 dissertasiya müdafiə olunacaq")
        self.assertEqual(one["lead"], "Ali Attestasiya Komissiyasının elanlarına görə, noyabrın 12-də kimya üzrə 1 dissertasiya müdafiəsi "
                                      "keçiriləcək. İddia olunan elmi dərəcə: fəlsəfə doktoru.")
        self.assertEqual(len(one["body"]), 1)
        three = r.aak_item(aak(), D(2026, 11, 17), D(2026, 11, 16))
        self.assertEqual(three["title"], "AAK: noyabrın 17-də 3 elm sahəsi üzrə 5 dissertasiya müdafiəsi keçiriləcək")
        self.assertIn("5 dissertasiya müdafiəsi keçiriləcək: filologiya elmləri üzrə 2, sənətşünaslıq üzrə 2, texnika elmləri üzrə 1.", three["lead"])
        self.assertEqual(len(three["body"]), 5)
        rows = [dict(x, degree="Elmlər doktoru") if x["name"].startswith("Əliyev Cavad") else x for x in aak()]
        mixed = r.aak_item(rows, D(2026, 11, 17), D(2026, 11, 16))
        self.assertTrue(mixed["lead"].endswith("İddia olunan elmi dərəcələr: fəlsəfə doktoru – 4, elmlər doktoru – 1."), mixed["lead"])

    def test_cap_on_the_list(self):
        rows = [dict(aak()[0], name=f"Namizəd {n}") for n in range(15)]
        item = r.aak_item(rows, D(2026, 11, 12), D(2026, 11, 11))
        self.assertEqual((len(item["body"]), item["body"][-1]), (13, "Elanlarda həmin gün üçün daha 3 müdafiə var."))
        self.assertIn("kimya üzrə 15 dissertasiya", item["title"])

    def test_no_defence_stale_or_empty_table(self):
        rows = aak()
        for item, why in ((r.aak_item(rows, D(2026, 11, 14), D(2026, 11, 13)), "müdafiəsi yoxdur"),
                          (r.aak_item(rows, D(2026, 12, 2), D(2026, 12, 1)), "köhnədir"), (r.aak_item([], D(2026, 11, 13), D(2026, 11, 12)), "boşdur")):
            self.assertFalse(item["worth"])
            self.assertIn(why, item["why"])
        self.assertEqual(r.aak_item(rows, D(2026, 11, 14), D(2026, 11, 13))["key"], "aak-mudafie-2026-11-14")
        page = text("aak-2026-11-12.html")
        self.assertEqual(r.aak_rows(re.sub(r"<tbody>.*</tbody>", "<tbody></tbody>", page, flags=re.S)), [])

    def test_changed_table_is_an_error(self):
        page = text("aak-2026-11-12.html")
        self.assertIn("<!--", page.split("</thead>")[0], "real səhifədə şərhə alınmış sütun var: oxunmamalıdır")
        for bad in ("<html>", page.replace("Elm sahəsi</th>", "Sahə</th>"), page.replace("<td>5</td>", "<td>55</td>"),
                    page.replace("<td>12.11.2026</td>", "<td>12.11</td>"), page.replace("<td>Kimya</td>", "<td></td>", 1),
                    page.replace('id="table_id"', 'id="basqa"'), page.replace("<td>Fəlsəfə doktoru</td>", "", 1)):
            with self.assertRaises(ValueError):
                r.aak_rows(bad)

    def test_leadership_in_a_topic_leaves_only_counts(self):
        rows = aak()
        rows[1] = dict(rows[1], title=f"{LEADER}in dövründə kimya sənayesi")
        item = r.aak_item(rows, D(2026, 11, 13), D(2026, 11, 12))
        self.assertEqual(item["body"], [])
        self.assertIn("3 dissertasiya", item["title"])
        self.assertTrue(r._guard(item)["worth"])
        self.assertNotIn("rezident", blob(item))


class EmlakTest(unittest.TestCase):
    def test_blocks_from_real_page(self):
        ps = posts()
        self.assertEqual([p["id"] for p in ps], [10648, 10647, 10646, 10645, 10644, 10639, 10638, 10637])
        self.assertEqual((ps[0]["when"], ps[0]["rest"]), (at(2026, 12, 16, 11), "gömrük hərracına çıxarılan dövlət mülkiyyətinə keçirilmiş malların siyahısı"))
        self.assertEqual(ps[0]["href"], "/az/news/view/10648-16-dekabr-2026-ci-il-tarixinde-saat-1100-da-gomruk-herracina-cixarilan-dovlet-"
                                        "mulkiyyetine-kecirilmis-mallarin-siyahisi")
        self.assertEqual(ps[-1]["when"], at(2026, 12, 9, 15))
        self.assertEqual([p["id"] for p in posts("emlak-2026-11-10.html")], [10639, 10638, 10637, 10626, 10625, 10622, 10618, 10616])
        news = r.emlak_news(text("emlak-2026-11-12.html"))
        self.assertEqual(len(news), 10)
        self.assertEqual(netice_row(), {"id": 10629, "href": "/az/news/view/10629-novbeti-herracda-67-neqliyyat-vasitesi-satilib",
                                        "title": "Növbəti hərracda 67 nəqliyyat vasitəsi satılıb", "day": 3, "month": 11})
        self.assertTrue(all(x["href"].startswith("/az/news/view/") for x in news), "başında «/» olmayan keçid də düzəlir")

    def test_memory_through_done_keys(self):
        self.assertIsNone(r.emlak_seen(set()))
        self.assertIsNone(r.emlak_seen({"dim-gun-2026-11-10", "herrac-netice-10629", "emlak-son-yanlis", "herrac-xeta-2026-11-10"}))
        self.assertEqual(r.emlak_seen({"emlak-son-2026-11-10-10639", "emlak-son-2026-11-09-10626", "herrac-elan-10637", "nk-sened-2026-11-05"}), 10639)
        self.assertEqual(r.emlak_seen({"emlak-son-2026-11-10-10639", "herrac-elan-10648"}), 10648)

    def test_new_announcements_since_the_last_seen(self):
        seen = max(p["id"] for p in posts("emlak-2026-11-10.html"))
        item = r.elan_item(posts(), seen, at(2026, 11, 12, 17, 30))
        self.assertTrue(item["worth"])
        self.assertEqual(item["key"], "herrac-elan-10648")
        self.assertEqual(item["title"], "Dekabrın 9-da və 16-da keçiriləcək hərraclarla bağlı 5 elan dərc olunub")
        self.assertEqual(item["lead"], "Əmlak Məsələləri Dövlət Xidmətinin saytında dekabrın 9-da və 16-da keçiriləcək hərraclarla bağlı 5 elan "
                                       "yerləşdirilib.")
        self.assertEqual(item["body"], [
            "9 dekabr, saat 10:00: hərraca çıxarılan \"Aqrarkredit\" Qapalı Səhmdar Cəmiyyəti Bank olmayan Kredit Təşkilatının balansında olan "
            "əmlakların siyahısı",
            "9 dekabr, saat 10:30: hərraca çıxarılan \"Aqrarkredit\" Qapalı Səhmdar Cəmiyyəti Bank olmayan Kredit Təşkilatının balansında olan "
            "əmlakların siyahısı",
            "16 dekabr, saat 10:00: gömrük hərracına çıxarılan dövlət mülkiyyətinə keçirilmiş malların siyahısı",
            "16 dekabr, saat 10:30: gömrük hərracına çıxarılan dövlət mülkiyyətinə keçirilmiş malların siyahısı",
            "16 dekabr, saat 11:00: gömrük hərracına çıxarılan dövlət mülkiyyətinə keçirilmiş malların siyahısı"])
        self.assertEqual((item["link"], item["topic"], item["slot"], item["list"]), (r.EMLAK_LIST, "iqtisadiyyat", "17:30", True))
        self.assertEqual(r._guard(item), item)

    def test_one_new_announcement(self):
        item = r.elan_item(posts(), 10647, at(2026, 11, 12, 17, 30))
        self.assertEqual(item["title"], "Dekabrın 16-da keçiriləcək hərracla bağlı elan dərc olunub")
        self.assertEqual(item["lead"], "Əmlak Məsələləri Dövlət Xidmətinin saytında dekabrın 16-da saat 11:00-da keçiriləcək hərracla bağlı elan "
                                       "yerləşdirilib.")
        self.assertEqual(item["body"], ["16 dekabr, saat 11:00: gömrük hərracına çıxarılan dövlət mülkiyyətinə keçirilmiş malların siyahısı"])
        self.assertEqual(item["link"], r.EMLAK_SITE + posts()[0]["href"])

    def test_nothing_new_no_memory_past_or_unreadable(self):
        now = at(2026, 11, 12, 17, 30)
        self.assertIsNone(r.elan_item(posts(), None, now), "yaddaş yoxdur: ilk oxunuşda köhnə elanlar «yeni» sayılmır")
        self.assertIsNone(r.elan_item(posts(), 10648, now))
        self.assertIsNone(r.elan_item(posts(), 99999, now))
        past = r.elan_item(posts(), 10639, at(2026, 12, 20, 12))
        self.assertEqual((past["worth"], past["key"]), (False, "herrac-elan-10648"))
        partly = r.elan_item(posts(), 10639, at(2026, 12, 10, 12))
        self.assertIn("3 elan", partly["title"])
        odd = [dict(p, when=None, rest="") if p["id"] == 10648 else p for p in posts()]
        self.assertEqual(len(r.elan_item(odd, 10646, now)["body"]), 1, "tarixi oxunmayan elan yazılmır")
        named = [dict(p, title=p["title"] + f" ({LEADER})") if p["id"] == 10648 else p for p in posts()]
        self.assertNotIn("rezident", blob(r.elan_item(named, 10646, now)))

    def test_broken_block(self):
        page = text("emlak-2026-11-12.html")
        two = '<div class="post-item">'.join(page.split('<div class="post-item">')[:3])
        for bad in ("<html>", page.replace("Hərraclar</h3>", "Elanlar</h3>"), two):
            with self.assertRaises(ValueError):
                r.emlak_posts(bad)
        odd = r.emlak_posts(page.replace("16 dekabr 2026-cı il tarixində saat 11:00-da", "Dekabrın 16-da"))
        self.assertEqual((odd[0]["when"], odd[0]["rest"]), (None, ""))
        self.assertIsNone(r.emlak_posts(page.replace("16 dekabr 2026-cı il tarixində saat 11:00-da", "31 noyabr 2026-cı il tarixində saat 11:00-da"))[0]["when"])
        self.assertEqual(r.emlak_news("<html>"), [])

    def test_result_item(self):
        item = r.netice_item(netice_row(), text("emlak-10629.html"), D(2026, 11, 3))
        self.assertTrue(item["worth"])
        self.assertEqual(item["key"], "herrac-netice-10629")
        self.assertEqual(item["title"], "Əmlak Xidmətinin noyabrın 3-də keçirdiyi hərracda 67 nəqliyyat vasitəsi satılıb")
        self.assertEqual(item["lead"], "Əmlak Məsələləri Dövlət Xidmətinin məlumatına görə, noyabrın 3-də keçirilən hərracda 67 nəqliyyat vasitəsi "
                                       "satılıb. Nəqliyyat vasitələri üzrə növbəti hərraclar noyabrın 11-də, 17-də və 24-də keçiriləcək.")
        self.assertEqual((item["body"], item["link"], item["topic"], item["slot"]), ([], NETICE_URL, "iqtisadiyyat", "17:30"))
        self.assertEqual(r._guard(item), item)

    def test_result_must_confirm_itself(self):
        row, page = netice_row(), text("emlak-10629.html")
        for item, why in ((r.netice_item(dict(row, title="Növbəti hərracda 68 nəqliyyat vasitəsi satılıb"), page, D(2026, 11, 3)), "təsdiqləmir"),
                          (r.netice_item(row, '<div id="blogcontent"><p>Mətn yoxdur.</p></div>', D(2026, 11, 3)), "oxunmadı"),
                          (r.netice_item(row, "<html>", D(2026, 11, 3)), "oxunmadı"),
                          (r.netice_item(dict(row, title="Hərrac keçirilib"), page, D(2026, 11, 3)), "oxunmadı"),
                          (r.netice_item(row, page.replace("noyabrın 3-də", "brumerin 3-də"), D(2026, 11, 3)), "oxunmadı"),
                          (r.netice_item(row, page, D(2026, 11, 20)), "uyğun deyil")):
            self.assertFalse(item["worth"])
            self.assertIn(why, item["why"])
            self.assertEqual(item["key"], "herrac-netice-10629")

    def test_next_auctions_sentence_only_when_it_is_clear(self):
        row, page = netice_row(), text("emlak-10629.html")
        end = "67 nəqliyyat vasitəsi satılıb."
        for changed in (page.replace("növbəti hərraclar 11, 17 və 24 noyabr", "növbəti hərrac 11 noyabr"),
                        page.replace("11, 17 və 24 noyabr", "24, 17 və 11 noyabr"), page.replace("11, 17 və 24 noyabr", "11, 17 və 31 noyabr"),
                        page.replace("11, 17 və 24 noyabr", "1, 2 və 3 noyabr"), page.replace("11, 17 və 24 noyabr", "11, 17 və 24 brumer")):
            self.assertTrue(r.netice_item(row, changed, D(2026, 11, 3))["lead"].endswith(end), changed[-600:])
        january = r.netice_item(dict(row, day=29, month=12), page.replace("noyabrın 3-də", "dekabrın 29-da").replace("11, 17 və 24 noyabr", "12, 19 və 26 yanvar"),
                                D(2026, 12, 29))
        self.assertTrue(january["lead"].endswith("növbəti hərraclar yanvarın 12-də, 19-da və 26-da keçiriləcək."), january["lead"])


class ItemsTest(unittest.TestCase):
    def run_at(self, now, done=(), table=None):
        fake = Fake(pages() if table is None else table)
        return r.items(ROOT, now, fake, set(done)), fake

    def test_no_request_outside_the_windows(self):
        for now in (at(2026, 11, 12, 0), at(2026, 11, 12, 9, 29), at(2026, 11, 12, 10), at(2026, 11, 12, 13), at(2026, 11, 12, 18), at(2026, 11, 9, 10, 30)):
            got, fake = self.run_at(now)
            self.assertEqual((got, fake.calls), ([], []), now)

    def test_each_source_in_its_window(self):
        got, fake = self.run_at(at(2026, 11, 6, 9, 30))
        self.assertEqual(([(i["key"], i["worth"]) for i in got], fake.calls), ([("nk-sened-2026-11-05", True)], [r.NK_URL]))
        got, fake = self.run_at(at(2026, 11, 9, 10, 5))
        self.assertEqual([(i["key"], i["worth"]) for i in got], [("tikinti-hefte-2026-11-02", True)])
        self.assertEqual(fake.calls, [r.tik_url(0, W1, W2), r.tik_url(1, W1, W2), r.tik_url(0, D(2026, 10, 26), D(2026, 11, 1))])
        self.assertIn("bu say 25 olub", got[0]["lead"])
        got, fake = self.run_at(at(2026, 11, 10, 10, 5))
        self.assertEqual((got, fake.calls), ([], []), "tikinti reyestri yalnız bazar ertəsi")
        got, fake = self.run_at(at(2026, 11, 4, 11, 0))
        self.assertEqual(([(i["key"], i["worth"]) for i in got], fake.calls, fake.headers), ([("anama-ay-2026-10", True)], [r.ANAMA_URL], [{"lang": "az"}]))
        got, fake = self.run_at(at(2026, 11, 12, 11, 29))
        self.assertEqual([(i["key"], i["worth"]) for i in got], [("anama-yoxla-2026-11-12", False)])
        got, fake = self.run_at(at(2026, 11, 21, 11, 0))
        self.assertEqual((got, fake.calls), ([], []), "ayın 20-sindən sonra ANAMA-ya sorğu getmir")
        got, fake = self.run_at(at(2026, 11, 12, 16, 10))
        self.assertEqual(([(i["key"], i["worth"]) for i in got], fake.calls), ([("aak-mudafie-2026-11-13", True)], [r.AAK_URL]))
        got, fake = self.run_at(at(2026, 11, 13, 16, 0))
        self.assertEqual([(i["key"], i["worth"]) for i in got], [("aak-mudafie-2026-11-14", False)])

    def test_emlak_cold_start_only_sets_the_marker(self):
        got, fake = self.run_at(at(2026, 11, 12, 17, 30))
        self.assertEqual([(i["key"], i["worth"]) for i in got], [("emlak-son-2026-11-12-10648", False)])
        self.assertIn("ilk oxunuş", got[0]["why"])
        self.assertEqual(fake.calls, [r.EMLAK_URL], "köhnə nəticə xəbərinin səhifəsi istənmir")

    def test_emlak_with_memory_publishes_new_announcements(self):
        got, fake = self.run_at(at(2026, 11, 12, 17, 45), {"emlak-son-2026-11-10-10639", "herrac-elan-10637"})
        self.assertEqual([(i["key"], i["worth"]) for i in got], [("emlak-son-2026-11-12-10648", False), ("herrac-elan-10648", True)])
        self.assertEqual(len(got[1]["body"]), 5)
        again, fake = self.run_at(at(2026, 11, 12, 17, 55), {i["key"] for i in got})
        self.assertEqual((again, fake.calls), ([], []), "bu günün nişanı done-dadır: sorğu getmir")
        tomorrow, fake = self.run_at(at(2026, 11, 13, 17, 30), {i["key"] for i in got})
        self.assertEqual([(i["key"], i["worth"]) for i in tomorrow], [("emlak-son-2026-11-13-10648", False)], "eyni elan iki dəfə yazılmır")

    def test_emlak_fresh_result_reads_its_page(self):
        table = pages("emlak-2026-11-10.html")
        got, fake = self.run_at(at(2026, 11, 4, 17, 30), {"emlak-son-2026-11-03-10639"}, table)
        self.assertEqual([(i["key"], i["worth"]) for i in got], [("emlak-son-2026-11-04-10639", False), ("herrac-netice-10629", True)])
        self.assertEqual(fake.calls, [r.EMLAK_URL, NETICE_URL])
        got, fake = self.run_at(at(2026, 11, 4, 17, 30), {"emlak-son-2026-11-03-10639", "herrac-netice-10629"}, table)
        self.assertEqual(fake.calls, [r.EMLAK_URL], "dərc olunmuş nəticənin səhifəsi bir də istənmir")
        got, fake = self.run_at(at(2026, 11, 7, 17, 30), {"emlak-son-2026-11-06-10639"}, table)
        self.assertEqual(fake.calls, [r.EMLAK_URL], "3 gündən köhnə nəticə xəbəri yazılmır")
        del table[NETICE_URL]
        got, fake = self.run_at(at(2026, 11, 4, 17, 30), {"emlak-son-2026-11-03-10639"}, table)
        self.assertEqual([(i["key"], i["worth"]) for i in got], [("emlak-son-2026-11-04-10639", False), ("herrac-netice-10629-xeta-2026-11-04", False)])

    def test_done_keys_cost_no_request(self):
        for now, key in ((at(2026, 11, 6, 9, 30), "nk-sened-2026-11-05"), (at(2026, 11, 9, 10, 0), "tikinti-hefte-2026-11-02"),
                         (at(2026, 11, 4, 11, 0), "anama-ay-2026-10"), (at(2026, 11, 4, 11, 0), "anama-yoxla-2026-11-04"),
                         (at(2026, 11, 12, 16, 0), "aak-mudafie-2026-11-13"), (at(2026, 11, 12, 17, 30), "emlak-son-2026-11-12-10648")):
            got, fake = self.run_at(now, {key})
            self.assertEqual((got, fake.calls), ([], []), key)

    def test_network_failure_and_garbage_never_raise(self):
        for now, key in ((at(2026, 11, 6, 9, 30), "nk-sened-xeta-2026-11-06"), (at(2026, 11, 9, 10, 0), "tikinti-hefte-xeta-2026-11-09"),
                         (at(2026, 11, 4, 11, 0), "anama-ay-xeta-2026-11-04"), (at(2026, 11, 12, 16, 0), "aak-mudafie-xeta-2026-11-12"),
                         (at(2026, 11, 12, 17, 30), "herrac-xeta-2026-11-12")):
            for table in ({}, {u: b"<html>bos</html>" for u in pages()}, {u: OSError("qırıldı") for u in pages()}):
                got, _ = self.run_at(now, (), table)
                self.assertTrue(got and not any(i["worth"] for i in got), (now, got))
                if not table:
                    self.assertEqual([i["key"] for i in got], [key])
                for i in got:
                    self.assertTrue(i["why"])
        self.assertEqual(r.items(ROOT, at(2026, 11, 6, 9, 30), lambda *a, **k: 1 / 0)[0]["key"], "nk-sened-xeta-2026-11-06")
        self.assertEqual(r.items(ROOT, "saat deyil", Fake(pages())), [])

    def test_missing_previous_week_does_not_block_the_item(self):
        table = pages()
        del table[r.tik_url(0, D(2026, 10, 26), D(2026, 11, 1))]
        got, _ = self.run_at(at(2026, 11, 9, 10, 0), (), table)
        self.assertEqual([(i["key"], i["worth"]) for i in got], [("tikinti-hefte-2026-11-02", True)])
        self.assertNotIn("Bir həftə əvvəl", got[0]["lead"])

    def test_item_shape_determinism_and_naive_time(self):
        seen = []
        for now, done in ((at(2026, 11, 6, 9, 30), ()), (at(2026, 11, 9, 10, 0), ()), (at(2026, 11, 4, 11, 0), ()), (at(2026, 11, 12, 16, 0), ()),
                          (at(2026, 11, 12, 17, 30), {"emlak-son-2026-11-10-10639"})):
            got, _ = self.run_at(now, done)
            self.assertEqual(got, self.run_at(now, done)[0])
            self.assertEqual(got, self.run_at(now.replace(tzinfo=None), done)[0], "saat qurşağı olmayan vaxt Bakı vaxtıdır")
            seen += got
        self.assertEqual(sorted({i["kind"] for i in seen if i["worth"]}), ["aak-mudafie", "anama-ay", "herrac-elan", "nk-sened", "tikinti-hefte"])
        for i in seen:
            self.assertLessEqual(KEYS, set(i), i["key"])
            self.assertRegex(i["slot"], r"^\d\d:\d\d$")
            self.assertTrue(i["title"] and i["lead"] and i["credit"] and i["link"].startswith("https://"))
            self.assertIsInstance(i["body"], list)
            self.assertNotIn("image", i)
            if i["worth"]:
                self.assertLessEqual(len(i["title"]), r.TITLE_MAX, i["title"])
                self.assertFalse(i["title"].endswith("."))
                self.assertFalse(r._leader(blob(i)), i["key"])
                self.assertNotRegex(blob(i), r"[А-Яа-яЁё]{2}")
            else:
                self.assertTrue(i["why"])

    def test_guard_blocks_leadership_and_long_titles(self):
        item = r.nk_item(nk(), D(2026, 11, 6))
        self.assertTrue(r._guard(item)["worth"])
        for change in ({"title": f"{LEADER} sərəncam imzalayıb"}, {"lead": "Azərbaycan Respublikası Prezidentinin Fərmanı."}, {"body": ["Birinci vitse-prezident"]},
                       {"title": "x" * 111}):
            held = r._guard(dict(item, **change))
            self.assertFalse(held["worth"], change)
            self.assertTrue(held["why"])
        skipped = r.nk_item(nk(), D(2026, 11, 8))
        self.assertIs(r._guard(skipped), skipped)

    def test_daily_request_budget(self):
        for day, most in ((D(2026, 11, 9), 7), (D(2026, 11, 12), 4), (D(2026, 11, 22), 3)):
            fake, done = Fake(pages()), set()
            now = datetime.datetime.combine(day, datetime.time(0, 0), r.BAKU)
            for step in range(144):
                for i in r.items(ROOT, now + datetime.timedelta(minutes=10 * step), fake, done):
                    done.add(i["key"])
            self.assertLessEqual(len(fake.calls), most, (day, fake.calls))
            self.assertLessEqual(len(fake.calls), oz_derc.QAYDA["oz_resmi"]["sorgu"])
        dead, done = Fake({}), set()
        for step in range(144):
            for i in r.items(ROOT, at(2026, 11, 9, 0) + datetime.timedelta(minutes=10 * step), dead, done):
                done.add(i["key"])
        self.assertLessEqual(len(dead.calls), oz_derc.QAYDA["oz_resmi"]["sorgu"], "mənbələr açılmayan gün də hədd keçilmir")


class PublisherTest(unittest.TestCase):
    """Modul dərc hissəsinə qoşulub: qayda, vaciblik, bölmə və məzmun qapısı."""

    def real_items(self):
        rows, count = week()
        return [r.nk_item(nk(), D(2026, 11, 5)), r.nk_item(nk(), D(2026, 11, 3)), r.tik_item(rows, count, W1, W2, 25),
                r.anama_item(r.anama_stat(raw("anama-2026-11-12.json")), D(2026, 11, 4)), r.aak_item(aak(), D(2026, 11, 13), D(2026, 11, 12)),
                r.elan_item(posts(), 10639, at(2026, 11, 12, 17, 30)), r.netice_item(netice_row(), text("emlak-10629.html"), D(2026, 11, 3))]

    def test_tables(self):
        self.assertIn(("oz_resmi", "Rəsmi məlumat: elanlar və reyestrlər"), ox.FAZA3)
        self.assertIn("oz_resmi", oz_derc.modules())
        self.assertEqual(oz_derc.QAYDA["oz_resmi"], {"done": "hamisi", "gelecek": "vaxtinda", "sorgu": 18})
        self.assertEqual([oz_derc.priority("oz_resmi", {"kind": k}) for k in ("nk-sened", "tikinti-hefte", "anama-ay", "herrac-netice", "herrac-elan", "aak-mudafie")],
                         [2, 2, 2, 2, 1, 1])
        self.assertEqual([oz_derc.category(i) for i in self.real_items()],
                         ["gundem", "gundem", "cemiyyet", "gundem", "tehsil", "iqtisadiyyat", "iqtisadiyyat"])

    def test_real_items_pass_the_content_gate(self):
        now = at(2026, 11, 12, 18)
        for item in self.real_items():
            self.assertTrue(item["worth"], item["key"])
            row = oz_derc.row(item, now)
            self.assertIsNone(oz_derc.gate(item, row), item["key"])
            self.assertEqual((row["source"], row["title"]), (ox.SOURCE, item["title"]))
            self.assertIn(item["title"], oz_derc.page(item, row))


class SinaqTest(unittest.TestCase):
    def test_sample_run_with_saved_pages(self):
        fake = Fake(pages())
        md = "\n".join(r.sinaq(ROOT, at(2026, 11, 12, 20), fake))
        for part in ("## Rəsmi məlumat: elanlar və reyestrlər (12.11.2026 20:00, Bakı vaxtı)", "- yoxdur (heç bir mənbənin pəncərəsi açıq deyil)",
                     "## 1. Nazirlər Kabinetinin sənədləri", "### Nazirlər Kabinetinin 376 nömrəli qərarı dərc olunub",
                     "### Hökumətin yeni sənədləri: noyabrın 5-də 5 qərar dərc olunub",
                     "## 2. Tikinti icazələri", "### 2–8 noyabr tarixlərində 37 tikinti icazəsi reyestrə daxil edilib",
                     "## 3. ANAMA-nın aylıq statistikası", "_Aylıq blok 03.11.2026 16:10-də (Bakı vaxtı) yenilənib._",
                     "### ANAMA oktyabr ayının statistikasını açıqlayıb: 4 898 hektar ərazi təmizlənib",
                     "## 4. Dissertasiya müdafiələri", "### 3 dissertasiya noyabrın 13-də müdafiə olunacaq: filologiya elmləri üzrə 2, kimya üzrə 1",
                     "## 5. Əmlak Xidməti", "### Dekabrın 16-da keçiriləcək hərraclarla bağlı 2 elan dərc olunub",
                     "### Əmlak Xidmətinin noyabrın 3-də keçirdiyi hərracda 67 nəqliyyat vasitəsi satılıb", "3 gündən köhnədir",
                     "✅ Dərc olunardı", "⏭ Dərc olunmazdı: həmin gün saytda qərar və ya sərəncam yerləşdirilməyib",
                     "⏭ Dərc olunmazdı: aylıq blok təzə deyil", "## Mənbələrə çıxış (bu sınaqda)", f"- {r.NK_URL} — "):
            self.assertIn(part, md)
        self.assertNotIn("xətası", md)
        self.assertNotIn("alınmadı", md)
        self.assertLessEqual(len(fake.calls), 9)
        self.assertEqual(len(fake.calls), len(set(fake.calls)), "sınaqda hər ünvan bir dəfə istənir")
        live = "\n".join(r.sinaq(ROOT, at(2026, 11, 12, 16, 5), Fake(pages())))
        self.assertIn("- `aak-mudafie-2026-11-13` (16:00): 3 dissertasiya noyabrın 13-də müdafiə olunacaq", live)

    def test_sample_run_survives_dead_network(self):
        md = "\n".join(r.sinaq(ROOT, at(2026, 11, 12, 16, 5), Fake({})))
        self.assertIn("## Rəsmi məlumat: elanlar və reyestrlər", md)
        self.assertEqual(md.count("mənbə alınmadı və ya oxunmadı"), 5)
        self.assertIn("aak-mudafie-xeta-2026-11-12", md)
        self.assertIn("## Mənbələrə çıxış (bu sınaqda)", md)

    def test_cli(self):
        out = io.StringIO()
        with patch.object(og, "_default_fetch", return_value=Fake(pages())), contextlib.redirect_stdout(out):
            self.assertEqual(r.main(["--sinaq", "--root", str(ROOT), "--now", "2026-11-12T20:00+04:00"]), 0)
        self.assertIn("## 4. Dissertasiya müdafiələri", out.getvalue())
        self.assertIn("✅ Dərc olunardı", out.getvalue())
        doc = io.StringIO()
        with contextlib.redirect_stdout(doc):
            self.assertEqual(r.main([]), 0)
        self.assertIn("oz_resmi.py --sinaq", doc.getvalue())


if __name__ == "__main__":
    unittest.main()
