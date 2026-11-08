"""8ulduz-un öz xəbərləri (oz_xeber.py, sahib 2026-11-08): şablonlar, fakt qapısı, relizin mətni, Claude çağırışı və sınaq.
Şəbəkə yoxdur: AMB, pfl.az, rəsmi sayt və Claude saxta cavablarla əvəz olunur."""
import datetime
import json
import os
import pathlib
import tempfile
import unittest
from types import SimpleNamespace
from unittest.mock import patch

import oz_xeber as oz
import updater

ROOT = pathlib.Path(__file__).resolve().parent.parent
BAKU = oz.BAKU


def _amb(day, rows):
    vals = "".join(f'<Valute Code="{c}"><Nominal>{n.split()[0]}</Nominal><Name>{n}</Name><Value>{v}</Value></Valute>' for c, n, v in rows)
    return (f'<?xml version="1.0" encoding="UTF-8"?>\n<ValCurs Date="{day}" Name="AZN məzənnələri">'
            f'<ValType Type="Xarici valyutalar">{vals}</ValType></ValCurs>').encode("utf-8")


AMB_CUR = _amb("06.11.2026", [("USD", "1 ABŞ dolları", "1.7"), ("EUR", "1 Avro", "1.9037"),
                              ("RUB", "100 Rusiya rublu", "2.084"), ("TRY", "1 Türk lirəsi", "0.0339")])
AMB_PREV = _amb("05.11.2026", [("USD", "1 ABŞ dolları", "1.7"), ("EUR", "1 Avro", "1.9148"),
                               ("RUB", "100 Rusiya rublu", "2.0782"), ("TRY", "1 Türk lirəsi", "0.0339")])


def _game(gid, home, away, hs, as_, when, stadium, status=3):
    return {"id": gid, "club_score_1": hs, "club_score_2": as_, "club_1": {"title": home}, "club_2": {"title": away},
            "status": status, "start_date": when, "stadion": {"title": stadium}}


TOURS = [
    {"title": "10", "games": [_game(6841, "Neftçi", "Qarabağ", 1, 1, "31/10/2026 19:00", "Palms Sports Arena"),
                              _game(6842, "Kəpəz", "Sabah", 0, 2, "01/11/2026 16:00", "Gəncə şəhər stadionu")]},
    {"title": "11", "games": [_game(6851, "Neftçi", "Kəpəz", 1, 0, "06/11/2026 20:00", "Palms Sports Arena"),
                              _game(6852, "Qarabağ", "Turan Tovuz", 0, 1, "06/11/2026 18:00", "Azersun Arena"),
                              _game(6853, "Sabah", "Şamaxı", 2, 2, "08/11/2026 17:30", "Sabah Arena"),
                              _game(6854, "İmişli", "Sumqayıt", 0, 0, "08/11/2026 15:00", "Yevlax şəhər stadionu"),
                              _game(6855, "Zirə", "Qəbələ", None, None, "09/11/2026 18:30", "Zirə İK stadionu", status=1)]},
    {"title": "12", "games": [_game(6861, "Qəbələ", "Neftçi", None, None, "15/11/2026 18:00", "Qəbələ şəhər stadionu", status=1)]},
]
GRID = [{"title": "Qarabağ", "rate": {"ordering": 1, "o": 1, "x": 25, "tf": 10}},   # cədvəl gecikib: 2 oyunu var, 1 sayılıb
        {"title": "Neftçi", "rate": {"ordering": 3, "o": 2, "x": 24, "tf": 5}},
        {"title": "Kəpəz", "rate": {"ordering": 11, "o": 2, "x": 9, "tf": -4}}]

DOST_TEXT = ("8 Noyabr – Zəfər Günü münasibətilə “Zəfərdən Zəfərə” adlı intellektual turnir keçirilib. "
             "Yarışın əsas məqsədi DOST mərkəzləri arasında komanda ruhunun gücləndirilməsi olub. Turnirdə 1.200 nəfər iştirak edib.")
DOST_PAGE = ('<html><body><nav><p>Ana səhifə, Haqqımızda, Xəbərlər, Xidmətlər, Əlaqə</p></nav>'
             '<h1>Zəfər Günü münasibətilə intellektual turnir keçirilib</h1><div class="xeber-metn" data-size="16">'
             f'<div class="sekil-con"><img src="x.jpg" alt=""></div><p>{DOST_TEXT}</p></div>'
             '<footer><p>Bütün hüquqlar qorunur. DOST Agentliyi, 2026-cı il</p></footer></body></html>').encode("utf-8")
GOOD = {"title": "DOST mərkəzləri arasında «Zəfərdən Zəfərə» intellektual turniri keçirilib",
        "lead": "8 Noyabr – Zəfər Günü münasibətilə keçirilən turnirdə 1200 nəfər iştirak edib.",
        "body": ["Yarışın məqsədi DOST mərkəzlərinin komanda ruhunu gücləndirmək olub."]}


class FormatTest(unittest.TestCase):
    def test_numbers_ordinals_and_suffixes(self):
        self.assertEqual([oz.az_num(1.9037, 4), oz.az_num(1.7, 4), oz.az_num(4072.1, 2), oz.az_num(-0.0111, 4)],
                         ["1,9037", "1,7000", "4 072,10", "0,0111"])
        self.assertEqual([oz.ordinal(n) for n in (11, 3, 6, 9, 10, 40, 100, 2026, 1000)],
                         ["11-ci", "3-cü", "6-cı", "9-cu", "10-cu", "40-cı", "100-cü", "2026-cı", "1000-ci"])
        self.assertEqual([oz.acc(n) for n in ("Kəpəz", "Şamaxı", "Turan Tovuz", "Qarabağ", "Zirə", "İmişli", "Sumqayıt")],
                         ["«Kəpəz»i", "«Şamaxı»nı", "«Turan Tovuz»u", "«Qarabağ»ı", "«Zirə»ni", "«İmişli»ni", "«Sumqayıt»ı"])
        self.assertEqual([oz.gen(n) for n in ("Neftçi", "Qarabağ", "Turan Tovuz")], ["«Neftçi»nin", "«Qarabağ»ın", "«Turan Tovuz»un"])
        self.assertEqual(oz.day_loc(datetime.date(2026, 11, 6)), "6 noyabrda")
        self.assertEqual(oz.day_loc(datetime.date(2026, 4, 3)), "3 apreldə")
        self.assertEqual(oz.pub_text("2026-11-08T17:52:00+00:00"), "8 noyabr 2026, 21:52")


class DataNewsTest(unittest.TestCase):
    def test_amb_bulletin_news_uses_amb_names_and_changes(self):
        day, rates = oz.parse_amb(AMB_CUR)
        self.assertEqual((day, rates["RUB"]), (datetime.date(2026, 11, 6), ("100 Rusiya rublu", 2.084)))
        item = oz.amb_item(day, rates, oz.parse_amb(AMB_PREV)[1])
        self.assertEqual(item["title"], "AMB 6 noyabr üçün rəsmi məzənnələri açıqlayıb: avro 1,9037 manat")
        self.assertEqual(item["lead"], "Azərbaycan Mərkəzi Bankı (AMB) xarici valyutaların manata qarşı 6 noyabr üçün rəsmi məzənnələrini "
                                       "açıqlayıb. ABŞ dollarının rəsmi məzənnəsi dəyişməyib və 1,7000 manat təşkil edir.")
        self.assertEqual(item["body"], ["1 avro: 1,9037 manat (0,0111 manat ucuzlaşıb)",
                                        "100 Rusiya rublu: 2,0840 manat (0,0058 manat bahalaşıb)",
                                        "1 Türk lirəsi: 0,0339 manat (dəyişməyib)"])
        self.assertEqual((item["credit"], item["key"]), ("Azərbaycan Mərkəzi Bankı", "amb-2026-11-06"))

    def test_amb_latest_reads_tomorrow_then_the_previous_bulletin(self):
        asked = []

        def fetch(url, timeout=None):
            asked.append(url)
            return AMB_CUR if "07.11.2026" in url else AMB_PREV
        day, rates, prev = oz.amb_latest(fetch, datetime.date(2026, 11, 6))
        self.assertEqual((day, prev["EUR"][1]), (datetime.date(2026, 11, 6), 1.9148))
        self.assertEqual(asked, ["https://www.cbar.az/currencies/07.11.2026.xml", "https://www.cbar.az/currencies/05.11.2026.xml"])

    def test_oil_news_on_working_days(self):
        markets = {"updatedAt": "2026-11-09T06:00:05+00:00", "items": [
            {"id": "BRENT", "value": 98.32, "change": 0.03, "changePct": 0.03, "src": "Yahoo Finance"},
            {"id": "WTI", "value": 90.83, "change": -0.31, "changePct": -0.34, "src": "Yahoo Finance"}]}
        item = oz.oil_item(markets, datetime.datetime(2026, 11, 9, 10, 0, tzinfo=BAKU))
        self.assertEqual(item["title"], "Brent nefti bahalaşıb: bareli 98,32 dollar")
        self.assertEqual(item["lead"], "Dünya bazarında Brent markalı neftin bir bareli 98,32 dollara satılır (Bakı vaxtı ilə saat 10:00). "
                                       "Bu, əvvəlki bağlanış qiymətindən 0,03 dollar (0,03%) çoxdur.")
        self.assertEqual(item["body"], ["WTI markalı neftin bir bareli 90,83 dollardır, əvvəlki bağlanışdan 0,31 dollar (0,34%) ucuzdur."])
        sunday = datetime.datetime(2026, 11, 8, 10, 0, tzinfo=BAKU)
        self.assertIsNone(oz.oil_item(markets, sunday), "həftə sonu birja bağlıdır: qiymət cümənindir")
        self.assertIsNotNone(oz.oil_item(markets, sunday, force=True))

    def test_football_results(self):
        games = {g["id"]: g for g in oz.pfl_games(TOURS)}
        self.assertEqual(sorted(games), [6851, 6852, 6853, 6854], "son oynanan tur, bitməyən oyun yoxdur")
        table = oz.pfl_table(GRID, TOURS)
        self.assertEqual(table, {"Neftçi": (2, 24), "Kəpəz": (3, 9)}, "Qarabağın 2 oyunu var, cədvəl 1 sayıb: yeri yazılmır")
        win = oz.pfl_item(oz.pfl_detail(games[6851], {"refeerer_main": {"name": "İnqilab", "surname": "Məmmədov"}, "fan": 550}),
                          {"Neftçi": (3, 24), "Kəpəz": (11, 9)})
        self.assertEqual(win["title"], "«Neftçi» «Kəpəz»i 1:0 hesabı ilə məğlub edib")
        self.assertEqual(win["lead"], "Misli Premyer Liqasının 11-ci turunda «Neftçi» doğma meydanda «Kəpəz»i qəbul edib. "
                                      "Görüş «Neftçi»nin 1:0 hesablı qələbəsi ilə başa çatıb.")
        self.assertEqual(win["body"], ["Oyun 6 noyabrda Palms Sports Arena stadionunda keçirilib. Görüşü İnqilab Məmmədov idarə edib. "
                                       "Oyunu 550 azarkeş izləyib. Bu nəticədən sonra «Neftçi» 24 xalla 3-cü, «Kəpəz» 9 xalla 11-ci yerdədir."])
        away = oz.pfl_item(games[6852])
        self.assertEqual(away["title"], "«Turan Tovuz» səfərdə «Qarabağ»ı 1:0 hesabı ilə məğlub edib")
        self.assertIn("Görüş «Turan Tovuz»un 1:0 hesablı qələbəsi ilə başa çatıb.", away["lead"])
        self.assertEqual(oz.pfl_item(games[6853])["title"], "«Sabah» ilə «Şamaxı» 2:2 hesabı ilə heç-heçə edib")
        nil = oz.pfl_item(games[6854])
        self.assertEqual(nil["title"], "«İmişli» ilə «Sumqayıt» qolsuz heç-heçə edib")
        self.assertEqual(nil["body"], ["Oyun 8 noyabrda Yevlax şəhər stadionunda keçirilib."])


class ReleaseTextTest(unittest.TestCase):
    def test_text_block_of_district_site(self):
        page = ('<html><body><header><p>Azərbaycan Respublikası Qəbələ Rayon İcra Hakimiyyəti rəsmi saytı</p></header>'
                '<main><h1>Qəbələ rayonunda bayram tədbiri təşkil edilmişdir</h1><span>08 noyabr 2026 | 21:47</span>'
                '<div class="metn"> <p style="text-align: left;">Qəbələ rayon Mədəniyyət Mərkəzində 8 Noyabr-&ldquo;Zəfər Günü&rdquo;nə '
                'həsr edilmiş konsert proqramı təşkil edilmişdir.</p> </div><div class="row"><img src="x.jpg" alt="foto"></div></main>'
                '<footer><p>Bütün hüquqlar qorunur. Qəbələ Rayon İcra Hakimiyyəti, 2026</p></footer></body></html>')
        self.assertEqual(oz.release_text(page), "Qəbələ rayon Mədəniyyət Mərkəzində 8 Noyabr-“Zəfər Günü”nə həsr edilmiş konsert proqramı təşkil edilmişdir.")

    def test_other_news_after_the_article_is_not_part_of_it(self):
        page = ('<body><nav><p>Menyu: Haqqımızda, Xəbərlər, Əlaqə və digər bölmələr</p></nav>'
                '<h1>"PeşəFest-2026"nın Bakıda yekun tədbiri keçirilib</h1><div class="content__block">'
                '<p>Dövlət Məşğulluq Agentliyi tərəfindən keçirilən "PeşəFest-2026" festivalının Bakıda yekun tədbiri keçirilib.</p>'
                '<p>Rəşad Mustafayev builki tədbirlərdə 176 minə yaxın iştirakçının olduğunu bildirib.</p></div>'
                '<div class="others"><h3>Xızı və Sabirabadda keçirilmiş yarmarkalarda 134 vakansiya təqdim olunub</h3>'
                '<p>Digər xəbərin qısa xülasəsi burada yazılıb, uzundur.</p></div></body>')
        self.assertEqual(oz.release_text(page).split("\n\n"), [
            'Dövlət Məşğulluq Agentliyi tərəfindən keçirilən "PeşəFest-2026" festivalının Bakıda yekun tədbiri keçirilib.',
            "Rəşad Mustafayev builki tədbirlərdə 176 minə yaxın iştirakçının olduğunu bildirib."])

    def test_page_without_h1_starts_at_the_title(self):
        page = ('<html><head><title>Qələbənin əbədiləşdirilməsi</title></head><body>'
                '<div class="menu"><p>Naxçıvan Muxtar Respublikası Ordubad Rayon İcra Hakimiyyəti</p></div>'
                '<div class="container"><h3 class="text-center">Qələbənin əbədiləşdirilməsi</h3><div class="">'
                '<p>Prezident İlham Əliyevin 2020-ci il 3 dekabr tarixli Sərəncamı ilə Zəfər G&uuml;n&uuml; təsis edilmişdir.</p></div></div></body></html>')
        self.assertEqual(oz.release_text(page, "Qələbənin əbədiləşdirilməsi"),
                         "Prezident İlham Əliyevin 2020-ci il 3 dekabr tarixli Sərəncamı ilə Zəfər Günü təsis edilmişdir.")


class FactGateTest(unittest.TestCase):
    corpus = "Zəfər Günü münasibətilə intellektual turnir keçirilib\n" + DOST_TEXT + "\nDOST Agentliyi"

    def test_faithful_text_passes(self):
        self.assertEqual(oz.fact_gate("\n".join([GOOD["title"], GOOD["lead"], *GOOD["body"]]), self.corpus), [])

    def test_invented_number_name_and_quote_are_caught(self):
        bad = (GOOD["lead"] + " Turnirdə 12 komanda yarışıb. Nazir Sahil Babayev çıxış edib. "
               "«Bu turnir çox uğurlu keçdi» deyə bildirilib.")
        self.assertEqual(oz.fact_gate(bad, self.corpus), ["12", "Nazir", "Sahil", "Babayev", "«Bu turnir çox uğurlu keçdi»"])

    def test_case_endings_count_but_other_words_do_not(self):
        corpus = "Tədbir Bakı şəhərində keçirilib. Prezident İlham Əliyev iştirak edib. Bayraq qaldırılıb. Qara rəngli lövhə."
        self.assertEqual(oz.fact_gate("Bakıda keçirilən tədbirdə İlham Əliyevin iştirakı ilə Bayrağı qaldırılıb.", corpus), [])
        self.assertEqual(oz.fact_gate("Tədbir Qarabağda keçirilib.", corpus), ["Qarabağda"])
        self.assertEqual(oz.fact_gate("Tədbir 9 dekabrda keçirilib.", "Tədbir 8 noyabrda keçirilib."), ["9", "dekabr"])

    def test_number_forms(self):
        self.assertEqual(oz._nums("08 noyabr, 1 200 nəfər, 3,5 milyon, 2026-cı il, 1.200 manat"), {"8", "1200", "3.5", "2026"})

    def test_leadership_waits_for_the_owner(self):
        self.assertTrue(oz.needs_owner("Prezident İlham Əliyevin Sərəncamı ilə Zəfər Günü təsis edilib"))
        self.assertTrue(oz.needs_owner("Birinci vitse-prezident Mehriban Əliyeva tədbirdə iştirak edib"))
        self.assertFalse(oz.needs_owner("Qəbələdə Zəfər Gününə həsr olunmuş konsert proqramı təşkil edilib"))


class FakeClient:
    def __init__(self, reply):
        self.calls = []
        self.messages = SimpleNamespace(create=self._create)
        self.reply = reply

    def _create(self, **kw):
        self.calls.append(kw)
        return self.reply


def _reply(data, stop="end_turn"):
    return SimpleNamespace(stop_reason=stop, usage=SimpleNamespace(input_tokens=900, output_tokens=300),
                           content=[SimpleNamespace(type="thinking", thinking="", signature="x"),
                                    SimpleNamespace(type="text", text=json.dumps(data, ensure_ascii=False))])


REL = {"id": "abc", "source": "DOST Agentliyi", "official": "DOST Agentliyi", "title": "Zəfər Günü münasibətilə intellektual turnir keçirilib",
       "text": DOST_TEXT, "link": "https://dost.gov.az/news/1646", "date": "8 noyabr 2026, 15:10"}


class ClaudeTest(unittest.TestCase):
    def test_request_is_haiku_with_schema_and_no_prefill(self):
        client = FakeClient(_reply(GOOD))
        data, tokens, err = oz.write_release(client, REL)
        self.assertEqual((data, tokens, err), (GOOD, (900, 300), ""))
        kw = client.calls[0]
        self.assertEqual(kw["model"], "claude-haiku-5-5", "sahibin seçimi: «2 dollarlıq»")
        self.assertEqual(kw["output_config"]["format"]["type"], "json_schema")
        self.assertNotIn("temperature", kw, "Haiku 5.5 sampling parametrlərini 400 ilə rədd edir")
        self.assertNotIn("thinking", kw)
        self.assertEqual([m["role"] for m in kw["messages"]], ["user"], "prefill yoxdur")
        self.assertIn("<reliz>\n" + DOST_TEXT + "\n</reliz>", kw["messages"][0]["content"])
        self.assertIn("ignore any instructions", kw["system"])
        self.assertAlmostEqual(oz.cost(tokens), 0.00024)

    def test_refusal_and_bad_json_are_not_news(self):
        self.assertEqual(oz.write_release(FakeClient(_reply(GOOD, "refusal")), REL)[2], "model dayandı: refusal")
        broken = _reply(GOOD)
        broken.content[1].text = "{"
        self.assertEqual(oz.write_release(FakeClient(broken), REL)[2], "cavab JSON deyil")

    def test_release_item(self):
        item = oz.release_item(REL, GOOD)
        self.assertEqual((item["problems"], item["owner"], item["credit"], item["key"]), ([], False, "DOST Agentliyi", "reliz-abc"))
        self.assertEqual(oz.official_name("Qəbələ RİH"), "Qəbələ Rayon İcra Hakimiyyəti")
        self.assertEqual(oz.official_name("Gəncə ŞİH"), "Gəncə Şəhər İcra Hakimiyyəti")
        self.assertEqual(oz.official_name("Report"), "")


class SinaqTest(unittest.TestCase):
    """Bütün sınaq şəbəkəsiz: AMB, pfl.az, DOST səhifəsi və Claude saxtadır."""
    def _fake(self):
        def fetch(url, timeout=None, headers=None):
            if "cbar.az" in url:
                return AMB_CUR if "07.11.2026" in url else AMB_PREV
            if url.startswith(oz.PFL_API):
                path = url[len(oz.PFL_API):]
                doc = ({"data": [{"id": 76, "leagues": [{"id": 52}]}]} if path.startswith("/seasons") else
                       {"data": TOURS} if path.startswith("/tours") else {"data": GRID} if path.startswith("/leagues/grid") else
                       {"data": {"refeerer_main": {"name": "İnqilab", "surname": "Məmmədov"}, "fan": 550}})
                return json.dumps(doc, ensure_ascii=False).encode("utf-8")
            if url == REL["link"]:
                return DOST_PAGE
            raise OSError(url)
        return SimpleNamespace(fetch=fetch, president_score=updater.president_score, norm_az=updater.norm_az)

    def _root(self, tmp):
        data = pathlib.Path(tmp) / "data"
        data.mkdir()
        (data / "markets.json").write_text(json.dumps({"updatedAt": "2026-11-06T06:00:00+00:00", "items": [
            {"id": "BRENT", "value": 98.32, "change": 0.03, "changePct": 0.03, "src": "Yahoo Finance"}]}), encoding="utf-8")
        (data / "news.json").write_text(json.dumps({"articles": [
            {"id": "abc", "title": REL["title"], "summary": "", "source": "DOST Agentliyi", "sourceUrl": REL["link"],
             "publishedAt": "2026-11-08T11:10:00+00:00"},
            {"id": "x1", "title": "Başqa saytın xəbəri", "source": "Report", "sourceUrl": "https://report.az/1",
             "publishedAt": "2026-11-08T12:00:00+00:00"}]}, ensure_ascii=False), encoding="utf-8")
        return pathlib.Path(tmp)

    def test_without_key_data_news_only(self):
        now = datetime.datetime(2026, 11, 6, 10, 0, tzinfo=BAKU)
        with tempfile.TemporaryDirectory() as tmp, patch.object(oz, "_u", return_value=self._fake()), \
                patch.dict(os.environ, {"ANTHROPIC_API_KEY": ""}):
            md = "\n".join(oz.sinaq(self._root(tmp), now=now))
        self.assertIn("### AMB 6 noyabr üçün rəsmi məzənnələri açıqlayıb: avro 1,9037 manat", md)
        self.assertIn("### Brent nefti bahalaşıb: bareli 98,32 dollar", md)
        self.assertIn("### «Neftçi» «Kəpəz»i 1:0 hesabı ilə məğlub edib", md)
        self.assertIn("Görüşü İnqilab Məmmədov idarə edib.", md)
        self.assertIn("ANTHROPIC_API_KEY yoxdur", md)
        self.assertIn("### Reliz: " + REL["title"], md)
        self.assertNotIn("Başqa saytın xəbəri", md, "yalnız rəsmi qurumların relizləri")
        notes = oz.notices(md, 0) + oz.notices(md, 1)
        self.assertTrue(notes[0].startswith("::notice title=1. AMB 6 noyabr üçün rəsmi məzənnələri açıqlayıb%3A avro 1%2C9037 manat::"), notes[0])
        self.assertTrue(any(n.startswith("::notice title=") and "Reliz%3A " in n for n in notes), notes)

    def test_notices_are_split_and_escaped(self):
        md = "\n".join(["# Başlıq", "", "tarix", "", "## 1. Bölmə", "", "### AMB: 1,7 manat", "", "Giriş 100%.", "", "- sətir", "",
                        "## 2. Relizlər", "", "> açar yoxdur", "", "### Reliz: X", "", "Reliz: «X»", "",
                        "<details><summary>m</summary>", "", "uzun mətn", "", "</details>", ""])
        self.assertEqual(oz.notices(md, 0), ["::notice title=1. AMB%3A 1%2C7 manat::Giriş 100%25.%0A- sətir",
                                             "::notice title=2. 2. Relizlər::> açar yoxdur",
                                             "::notice title=3. Reliz%3A X::Reliz: «X»"])
        self.assertEqual(oz.notices(md, 1), [])

    def test_with_claude_release_news_passes_the_gate(self):
        now = datetime.datetime(2026, 11, 6, 10, 0, tzinfo=BAKU)
        client = FakeClient(_reply(GOOD))
        with tempfile.TemporaryDirectory() as tmp, patch.object(oz, "_u", return_value=self._fake()), \
                patch.object(oz, "_client", return_value=(client, "")):
            md = "\n".join(oz.sinaq(self._root(tmp), now=now))
        self.assertIn("### " + GOOD["title"], md)
        self.assertIn("✅ Fakt qapısından keçdi", md)
        self.assertIn("Mənbə: [DOST Agentliyi](https://dost.gov.az/news/1646)", md)
        self.assertIn("## Xərc", md)
        self.assertIn("Dərc vaxtı: 8 noyabr 2026, 15:10", client.calls[0]["messages"][0]["content"])


class NotOnTheSiteTest(unittest.TestCase):
    """Sahib 2026-11-08: «hələ sayta tətbiq etmə baxaq sonra». Sayta qoşulanda bu test sahibin göstərişi ilə dəyişir."""
    def test_site_pipeline_does_not_use_it_and_trial_writes_nothing(self):
        self.assertNotIn("oz_xeber", (ROOT / "updater.py").read_text(encoding="utf-8"))
        self.assertNotIn("oz_xeber", (ROOT / ".github" / "scripts" / "pipeline.sh").read_text(encoding="utf-8"))
        wf = (ROOT / ".github" / "workflows" / "oz-xeber.yml").read_text(encoding="utf-8")
        self.assertIn("contents: read", wf)
        self.assertNotIn("contents: write", wf)
        self.assertNotIn("git push", wf)
        self.assertIn("GITHUB_STEP_SUMMARY", wf)


if __name__ == "__main__":
    unittest.main()
