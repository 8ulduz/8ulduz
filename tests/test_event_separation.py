"""Təməlqoyma, stadion açılışı və Şuşa açılışı eyni səfərin ayrı xəbərləridir."""
import copy
import datetime
import json
import pathlib
import tempfile
import unittest
from unittest.mock import patch

import updater


class EventSeparationTest(unittest.TestCase):
    NOW = datetime.datetime(2026, 11, 7, 10, tzinfo=datetime.timezone.utc)
    INTRO = "Azərbaycan Respublikasının Prezidenti İlham Əliyev noyabrın 7-də "

    def row(self, source, title, detail="", minutes=1):
        return {"id": source, "source": source, "sourceUrl": f"https://example.org/{source}", "title": title,
                "summary": self.INTRO + detail if detail else "", "category": "tehsil", "lang": "az",
                "publishedAt": (self.NOW - datetime.timedelta(minutes=minutes)).isoformat()}

    def fixture(self):
        return [
            self.row("Bizim.Media", "Qarabağ Universitetində iki binanın təməli qoyulub - Foto",
                     "Xankəndidə Qarabağ Universitetinin Kitabxanasının və İnnovasiya Mərkəzinin binalarının təməlqoyma mərasimlərində iştirak edib."),
            self.row("Metbuat", "Prezident iki binanın təməlini qoydu",
                     "Xankəndidə Qarabağ Universitetinin Kitabxanasının və İnnovasiya Mərkəzinin binalarının təməlqoyma mərasimlərində iştirak edib.", 2),
            self.row("Modern.az", "Xankəndi Stadionunun açılışı oldu - FOTOLAR",
                     "Xankəndi Stadionunun əsaslı təmir və yenidənqurmadan sonra açılışında iştirak edib.", 3),
            self.row("Günün Səsi", "Xankəndi Stadionunun açılışı oldu - Foto",
                     "Xankəndi Stadionunun əsaslı təmir və yenidənqurmadan sonra açılışında iştirak edib.", 4),
            self.row("News24.az", "Prezident Şuşada açılışda - Fotolar",
                     "Şuşada Peşə Təhsil Mərkəzinin açılışında iştirak edib.", 5),
            self.row("Aia.az", "Prezident Şuşada açılışda - FOTO",
                     "Şuşada Peşə Təhsil Mərkəzinin açılışında iştirak edib.", 6),
        ]

    def test_three_events_stay_separate_but_each_copy_still_joins(self):
        expected = [{"Bizim.Media", "Metbuat"}, {"Modern.az", "Günün Səsi"}, {"News24.az", "Aia.az"}]
        for rows in (self.fixture(), list(reversed(self.fixture()))):
            cards = updater.group_duplicates(rows)
            sites = [{a["source"], *(x["source"] for x in a.get("alts", []))} for a in cards]
            self.assertCountEqual(sites, expected)

    def test_summary_boilerplate_cannot_override_explicit_event_phase(self):
        a, _, b, *_ = self.fixture()
        self.assertEqual(updater._same_event(a, b), 0)

    def test_identical_generic_headlines_cannot_override_different_locations(self):
        title = "Prezident yeni təhsil mərkəzinin açılışında iştirak edib"
        a = self.row("A", title, "Xankəndidə yeni təhsil mərkəzinin açılışında iştirak edib.")
        b = self.row("B", title, "Şuşada yeni təhsil mərkəzinin açılışında iştirak edib.")
        self.assertEqual(len(updater.group_duplicates([a, b])), 2)
        self.assertEqual(len(updater.attach_fresh([a, b], now=self.NOW)), 2)

    def test_opening_spellings_do_not_join_foundation(self):
        foundation = self.row("A", "Xankəndidə yeni təhsil mərkəzinin təməli qoyulub")
        for title in ("Xankəndidə yeni təhsil mərkəzi açılıb", "Xankəndidə yeni təhsil mərkəzi açıldı",
                      "Xankəndidə yeni təhsil mərkəzi istifadəyə verilib",
                      "Xankəndidə təhsil mərkəzi açılıb və yeni məktəbin təməli qoyulub"):
            with self.subTest(title=title):
                opening = self.row("B", title)
                self.assertEqual(len(updater.group_duplicates(copy.deepcopy([foundation, opening]))), 2)
                self.assertEqual(len(updater.attach_fresh([foundation, opening], now=self.NOW)), 2)
        copy_row = self.row("C", foundation["title"] + " - FOTO")
        self.assertEqual(len(updater.attach_fresh([foundation, copy_row], now=self.NOW)), 1)

    def test_remembered_wrong_sources_are_removed_and_valid_copy_survives(self):
        a, valid, stadium, _, shusha, _ = self.fixture()
        valid["title"] = "Qarabağ Universitetinin Kitabxanasının və İnnovasiya Mərkəzinin binalarının təməli qoyulub"
        a["alts"] = [updater._compact_alt(x) for x in (valid, stadium, shusha)]
        cards = updater.group_duplicates([a])
        self.assertEqual([x["source"] for x in cards[0]["alts"]], [valid["source"]])

    def test_cached_group_does_not_absorb_a_different_event(self):
        a, valid, stadium, *_ = self.fixture()
        cached = {a["sourceUrl"]: [updater._compact_alt(x) for x in (valid, stadium)]}
        with tempfile.TemporaryDirectory() as tmp, patch.object(updater, "GROUPS_FILE", pathlib.Path(tmp) / "groups.json"):
            updater.GROUPS_FILE.write_text(json.dumps(cached), encoding="utf-8")
            cards = updater.apply_groups([a, valid, stadium])
        self.assertEqual(len(cards), 2)
        self.assertEqual([x["source"] for x in cards[0]["alts"]], [valid["source"]])
        self.assertEqual(cards[1]["source"], stadium["source"])

    def test_first_cycle_without_cache_drops_wrong_alternatives(self):
        a, valid, stadium, *_ = self.fixture()
        a["alts"] = [updater._compact_alt(x) for x in (valid, stadium)]
        with tempfile.TemporaryDirectory() as tmp, patch.object(updater, "GROUPS_FILE", pathlib.Path(tmp) / "absent.json"):
            cards = updater.apply_groups([a])
        self.assertEqual([x["source"] for x in cards[0]["alts"]], [valid["source"]])

    def test_recompute_does_not_restore_conflicting_legacy_alternative(self):
        a, valid, stadium, *_ = self.fixture()
        a["alts"] = [updater._compact_alt(x) for x in (valid, stadium)]
        with tempfile.TemporaryDirectory() as tmp, patch.object(updater, "GROUPS_FILE", pathlib.Path(tmp) / "groups.json"), \
                patch.object(updater, "read_feed", return_value=[a]):
            updater.compute_groups()
            cards = updater.apply_groups([a])
        self.assertEqual([x["source"] for x in cards[0]["alts"]], [valid["source"]])

    def test_cached_same_site_repetition_does_not_hide_different_locations(self):
        title = "Prezident yeni təhsil mərkəzinin açılışında iştirak edib"
        a = self.row("A", title, "Xankəndidə yeni təhsil mərkəzinin açılışında iştirak edib.")
        b = dict(self.row("A", title, "Şuşada yeni təhsil mərkəzinin açılışında iştirak edib."), sourceUrl="https://example.org/A2")
        with tempfile.TemporaryDirectory() as tmp, patch.object(updater, "GROUPS_FILE", pathlib.Path(tmp) / "groups.json"):
            updater.GROUPS_FILE.write_text(json.dumps({a["sourceUrl"]: []}), encoding="utf-8")
            updater.GROUPS_FILE.with_name("group_same.json").write_text(json.dumps({b["sourceUrl"]: a["sourceUrl"]}), encoding="utf-8")
            cards = updater.apply_groups([a, b])
        self.assertEqual(len(cards), 2)


class ZugulbaMeetingTest(unittest.TestCase):
    """2026-11-12 Dublin (sahib: «zuğulba xronikasında mənbələr birləşdirilmir»): şablon başlıqlı ayrı görüşlər bir kartda idi,
    eyni görüşün müxtəlif başlıqları isə 3–5 kartda."""
    NOW = datetime.datetime(2026, 11, 12, 20, tzinfo=datetime.timezone.utc)

    def row(self, source, title, minutes, summary="", n=""):
        return {"id": source + n, "source": source, "sourceUrl": f"https://example.org/{source}{n}", "title": title, "summary": summary,
                "category": "prezident", "lang": "az", "publishedAt": (self.NOW - datetime.timedelta(minutes=minutes)).isoformat()}

    def cards(self, rows):
        out = updater.group_duplicates(copy.deepcopy(rows))
        return sorted(sorted({a["source"], *(x["source"] for x in a.get("alts") or [])}) for a in out), out

    def test_template_meetings_with_different_counterparts_stay_separate(self):
        # Kart agentlik surəti ilə başlayır (rəsmi səhifənin vaxtı əvvəldir): rəsmi mənbənin sərt qaydası işləmirdi,
        # 6 ortaq kök (azərbaycan, prezident, ilham, əliyev, dublin, görüş) «eyni hadisə» sayılırdı.
        rows = [
            self.row("Sesqazeti.az", "Azərbaycan Prezidenti İlham Əliyev Dublində Rumıniya Prezidenti ilə görüşüb", 1),
            self.row("Azərbaycan qəzeti", "Azərbaycan Prezidenti İlham Əliyev Dublində Böyük Britaniyanın Baş naziri ilə görüşüb", 2),
            self.row("Report", "Azərbaycan Prezidenti İlham Əliyev Dublində Böyük Britaniyanın Baş naziri ilə görüşüb", 3),
            self.row("APA", "Azərbaycan Prezidenti İlham Əliyev Dublində Rumıniya Prezidenti ilə görüşüb", 4),
            self.row("Day.Az", "Prezident İlham Əliyevin Dublində Litva Prezidenti ilə görüşü olub", 5),
            self.row("Sia.az", "Azərbaycan Prezidenti İlham Əliyevin Dublində Çexiyanın Baş naziri ilə görüşü olub", 6),
            self.row("Teleqraf", "Prezident İlham Əliyevin Dublində Litva Prezidenti ilə görüşü olub", 7),
            self.row("Xezerxeber", "Azərbaycan Prezidenti İlham Əliyevin Dublində Çexiyanın Baş naziri ilə görüşü olub", 8),
        ]
        expected = sorted([["APA", "Sesqazeti.az"], ["Azərbaycan qəzeti", "Report"], ["Day.Az", "Teleqraf"], ["Sia.az", "Xezerxeber"]])
        for order in (rows, list(reversed(rows))):
            self.assertEqual(self.cards(order)[0], expected)

    def test_lowercase_country_names_separate_meetings_too(self):
        rows = [self.row("Axar.az", "İlham Əliyev rumıniyalı həmkarı ilə görüşdü", 1),
                self.row("Metbuat", "İlham Əliyev polşalı həmkarı ilə görüşdü", 2)]
        self.assertEqual(len(self.cards(rows)[1]), 2)

    def test_one_meeting_under_different_headlines_is_one_card(self):
        official = self.row("Prezident.az", "Azərbaycan Prezidenti İlham Əliyev Dublində Rumıniya Prezidenti ilə görüşüb VİDEO", 30,
                            "Noyabrın 12-də Azərbaycan Respublikasının Prezidenti İlham Əliyev Dublində Rumıniya Prezidenti Nikuşor Dan ilə görüşüb.")
        rows = [
            self.row("Axar.az", "İlham Əliyev rumıniyalı həmkarı ilə görüşdü", 5),
            self.row("Metbuat", "Azərbaycan Prezidenti Dublində rumıniyalı həmkarı ilə görüşdü", 8),
            self.row("Baku.ws", "Prezident İlham Əliyev Dublində Rumıniya Prezidenti Nikuşor Dan ilə görüşüb", 12),
            official,
            self.row("Day.Az", "Prezident İlham Əliyevin Dublində Litva Prezidenti ilə görüşü olub", 40),
        ]
        groups, out = self.cards(rows)
        self.assertEqual(groups, [["Axar.az", "Baku.ws", "Metbuat", "Prezident.az"], ["Day.Az"]])
        self.assertEqual(next(a for a in out if a.get("alts"))["source"], "Prezident.az")  # rəsmi mənbə əsasdır

    def test_name_and_country_headlines_join_through_the_official_summary(self):
        # «Endi Börnhemlə görüşüb» və «Britaniyanın Baş naziri ilə görüşüb» xülasəsiz bir-birini tanımır: iki kart yaranır,
        # hər ikisini tanıyan rəsmi xəbər gələndə kartlar birləşir, sonrakı surətlər də ora düşür.
        rows = [
            self.row("Sesqazeti.az", "İlham Əliyev Endi Börnhemlə görüşüb", 1),
            self.row("Azərbaycan qəzeti", "Azərbaycan Prezidenti İlham Əliyev Dublində Böyük Britaniyanın Baş naziri ilə görüşüb", 2),
            self.row("Axar.az", "İlham Əliyev Endi Börnhemlə görüşdü", 3),
            self.row("Prezident.az", "Azərbaycan Prezidenti İlham Əliyev Dublində Böyük Britaniyanın Baş naziri ilə görüşüb VİDEO", 10,
                     "Azərbaycan Respublikasının Prezidenti İlham Əliyev noyabrın 12-də Dublində Böyük Britaniya və Şimali İrlandiya "
                     "Birləşmiş Krallığının Baş naziri Endi Börnhem ilə görüşüb."),
            self.row("Anews.az", "Prezident Endi Börnhemlə görüşdü", 20),
            self.row("Publika.az", "İlham Əliyev Dublində Böyük Britaniyanın Baş naziri ilə görüşdü", 25),
        ]
        groups, _out = self.cards(rows)
        self.assertEqual(groups, [sorted(r["source"] for r in rows)])

    def test_two_parts_of_one_visit_stay_separate(self):
        # Eyni qonaqla iki rəsmi xəbər: adlar eynidir, məzmun ayrıdır. Ümumi «görüşüb» başlığı onları bir karta yığmır.
        rows = [
            self.row("APA", "İlham Əliyev Ərdoğanla görüşüb", 1),
            self.row("Report", "İlham Əliyevin Ərdoğanla təkbətək görüşü olub", 5),
            self.row("Trend", "İlham Əliyevin Ərdoğanla geniş tərkibdə görüşü olub", 9),
        ]
        self.assertEqual(len(self.cards(rows)[1]), 2)

    def test_consultation_and_talk_headlines_are_the_same_meeting(self):
        # «məsləhətləşdi», «söhbətləşdi», «danışdı»: görüş sözü yoxdur, adın yazılışı da fərqlidir (Corciya / Ciorcia).
        rows = [
            self.row("Bizim.Media", "İlham Əliyev Ciorcia Meloni ilə danışdı - Foto", 1),
            self.row("Metbuat", "Meloni İlham Əliyevlə məsləhətləşdi", 5),
            self.row("Moderator.az", "Meloni İlham Əliyevlə məsləhətləşmə apardı", 8),
            self.row("Lent.az", "İtaliyanın baş naziri İlham Əliyevlə məsləhətləşdi", 12,
                     "İtaliyanın baş naziri Corciya Meloni Dublində İlham Əliyevlə məsləhətləşib."),
            self.row("Axar.az", "İlham Əliyev Corciya Meloni ilə söhbətləşdi - Foto", 15),
            self.row("Anews.az", "İlham Əliyev və Kiriakos Miçotakis Azərbaycanın Avropaya qaz ixracını müzakirə ediblər", 20),
            self.row("Bakupost", "İlham Əliyev Kiriakos Miçotakislə görüşdü", 25),
        ]
        for order in (rows, list(reversed(rows))):
            self.assertEqual(self.cards(order)[0], [["Anews.az", "Bakupost"], ["Axar.az", "Bizim.Media", "Lent.az", "Metbuat", "Moderator.az"]])

    def test_the_venue_and_the_continent_do_not_bridge_meetings(self):
        # «Dublindəki», «Dublin», «Avropa» hər görüşün mətnində var: qarşı tərəf deyil.
        rows = [
            self.row("Bizim.Media", "İlham Əliyev və Paşinyanın Dublindəki görüşündən videoçarx", 1),
            self.row("Baku TV", "İlham Əliyev Dublində Avropa ilə əməkdaşlığın perspektivlərini müzakirə edir", 2),
            self.row("Konkret.az", "İlham Əliyevin Dublin görüşləri", 3),
            self.row("525.az", "Prezident İlham Əliyev Dublində Böyük Britaniyanın Baş naziri ilə görüşüb", 4),
            self.row("Milli.az", "Prezident İlham Əliyevin Dublində Avropa İttifaqı Şurasının Prezidenti ilə görüşü olub", 5),
            self.row("AzVision.az", "İlham Əliyev Paşinyanla görüşüb", 6),
        ]
        for order in (rows, list(reversed(rows))):
            self.assertEqual(self.cards(order)[0], [["525.az"], ["AzVision.az", "Bizim.Media"], ["Baku TV"], ["Konkret.az"], ["Milli.az"]])

    def test_a_visit_roundup_in_the_summary_does_not_join_two_meetings(self):
        # Xülasənin ikinci cümləsi səfərin başqa görüşünü çəkir: Börnhem xəbəri Paşinyan kartını Britaniya kartına bağlamır.
        rows = [
            self.row("Anews.az", "Prezident Endi Börnhemlə görüşdü", 1,
                     "Azərbaycan Prezidenti İlham Əliyev Dublinə səfər edib. Anews.az xəbər verir ki, o, Nikol Paşinyanla da görüşüb."),
            self.row("AzVision.az", "İlham Əliyev Paşinyanla görüşüb", 3),
            self.row("Axar.az", "İlham Əliyev Endi Börnhemlə görüşdü", 5),
            self.row("Yurd.Media", "Dublində İlham Əliyevin Nikol Paşinyanla görüşü olub", 7),
        ]
        for order in (rows, list(reversed(rows))):
            self.assertEqual(self.cards(order)[0], [["Anews.az", "Axar.az"], ["AzVision.az", "Yurd.Media"]])

    def test_official_page_takes_its_own_headline_back(self):
        # 2026-11-12: əlavə mənbənin başlığı rəsmi sətrin üstünə yazılmışdı və sətir özü düzəlmirdi.
        link = "https://president.az/az/articles/view/74693"
        known = dict(self.row("Prezident.az", "Prezident İlham Əliyevin Antonio Koşta ilə görüşü olub", 30, "Dublin, 12 noyabr, AZƏRTAC ..."),
                     sourceUrl=link, id="15efd40596b12287")
        it = {"title": "İlham Əliyevin Dublində Litva Prezidenti ilə görüşü olub", "link": link,
              "description": "Azərbaycan Prezidentinin rəsmi səhifəsindən."}
        self.assertTrue(updater.restore_official_row(known, it, "Prezident.az"))
        self.assertEqual((known["title"], known["summary"]), (it["title"], it["description"]))
        self.assertEqual((known["id"], known["sourceUrl"], known["source"]), ("15efd40596b12287", link, "Prezident.az"))  # nömrə və keçid qalır
        self.assertFalse(updater.restore_official_row(known, it, "Prezident.az"))  # başlıq eynidirsə toxunulmur
        # Başqa mənbənin sətri, başqa keçid və agentlik lenti rəsmi başlıqla dəyişmir.
        for other, src in ((dict(known, source="APA", title="x"), "Prezident.az"), (dict(known, sourceUrl=link + "1", title="x"), "Prezident.az"),
                           (dict(known, source="APA", title="x"), "APA"), (None, "Prezident.az")):
            self.assertFalse(updater.restore_official_row(other, it, src))
            self.assertIn((other or {}).get("title"), ("x", None))

    PAGE = ('<div class="news_heading">x</div><div class="news_paragraph-block"> <p>Azərbaycan Respublikasının Prezidenti İlham Əliyevin '
            'noyabrın 12-də Dublində Avropa İttifaqı Şurasının Prezidenti Antonio Koşta ilə görüşü olub.</p> <p>Avropa İttifaqı '
            'Şurasının Prezidenti Antonio Koşta ölkəmizə səfərini xatırladı. Nikol Paşinyan da sammitdə idi.</p></div>')
    EU = "İlham Əliyevin Dublində Avropa İttifaqı Şurasının Prezidenti ilə görüşü olub"

    def test_official_lead_is_read_only_when_it_is_surely_this_story(self):
        lead = updater.parse_official_lead(self.PAGE, self.EU)
        self.assertEqual(lead, "Azərbaycan Respublikasının Prezidenti İlham Əliyevin noyabrın 12-də Dublində Avropa İttifaqı Şurasının "
                               "Prezidenti Antonio Koşta ilə görüşü olub.")  # yalnız ilk cümlə: ikinci abzasdakı Paşinyan yoxdur
        # Başqa xəbərin səhifəsi (şablon başlıq oxşardır), quruluşu dəyişmiş səhifə, boş səhifə: cümlə götürülmür.
        self.assertEqual(updater.parse_official_lead(self.PAGE, "İlham Əliyev Dublində Moldova Prezidenti ilə görüşüb"), "")
        self.assertEqual(updater.parse_official_lead(self.PAGE.replace("news_paragraph-block", "text"), self.EU), "")
        self.assertEqual(updater.parse_official_lead("", self.EU), "")
        # «Çexiyanın» başlıqda, «Çex Respublikasının» cümlədə: eyni xəbərdir.
        czech = self.PAGE.replace("Avropa İttifaqı Şurasının Prezidenti Antonio Koşta", "Çex Respublikasının Baş naziri Andrey Babişlə")
        self.assertIn("Babişlə", updater.parse_official_lead(czech, "İlham Əliyevin Dublində Çexiyanın Baş naziri ilə görüşü olub"))

    def test_office_and_name_cards_join_only_through_the_official_sentence(self):
        # «Antonio Koşta ilə görüşü olub» və «Avropa İttifaqı Şurasının Prezidenti ilə görüşü olub»: başlıqdan bilmək olmur.
        official = dict(self.row("Prezident.az", self.EU, 30, "Azərbaycan Prezidentinin rəsmi səhifəsindən."),
                        sourceUrl="https://president.az/az/articles/view/74692")
        rows = [
            self.row("Sesqazeti.az", "Prezident İlham Əliyev Dublində Antonio Koşta ilə görüşüb", 1),
            self.row("Milli.az", "Prezident İlham Əliyevin Dublində Avropa İttifaqı Şurasının Prezidenti ilə görüşü olub", 3),
            self.row("Qafqazinfo", "İlham Əliyev Antonio Koşta ilə görüşdü", 5),
            self.row("Day.Az", "Prezident İlham Əliyevin Dublində Litva Prezidenti ilə görüşü olub", 8),
            official,
            self.row("Lent.az", "Prezidenti İlham Əliyevin Antonio Koşta ilə görüşü olub", 40),
        ]
        apart = [["Day.Az"], ["Lent.az", "Qafqazinfo", "Sesqazeti.az"], ["Milli.az", "Prezident.az"]]
        together = [["Day.Az"], ["Lent.az", "Milli.az", "Prezident.az", "Qafqazinfo", "Sesqazeti.az"]]
        self.assertEqual(self.cards(rows)[0], apart)  # cümlə oxunmayıb: təxmin edilmir
        with patch.dict(updater._OFFICIAL_LEAD, {official["sourceUrl"]: updater.parse_official_lead(self.PAGE, self.EU)}):
            for order in (rows, list(reversed(rows))):
                groups, out = self.cards(order)
                self.assertEqual(groups, together)
                self.assertEqual(next(a for a in out if a.get("alts"))["source"], "Prezident.az")
        # Agentlik xəbərinin xülasəsi eyni cümləni yazsa da kartları birləşdirmir: yalnız rəsmi mənbə və ya başlıq dəlildir.
        agency = [dict(r, source="APA", sourceUrl="https://example.org/APA", summary=updater.parse_official_lead(self.PAGE, self.EU))
                  if r is official else r for r in rows]
        self.assertEqual(len(self.cards(agency)[1]), 3)

    def test_a_headline_listing_two_guests_does_not_join_their_cards(self):
        rows = [
            self.row("APA", "İlham Əliyev Paşinyan və Miçotakislə görüşüb", 1),
            self.row("AzVision.az", "İlham Əliyev Paşinyanla görüşüb", 3),
            self.row("Bakupost", "İlham Əliyev Kiriakos Miçotakislə görüşdü", 5),
            self.row("Yurd.Media", "Dublində İlham Əliyevin Nikol Paşinyanla görüşü olub", 7),
            self.row("Reyting.az", "Prezident Dublində Kiriakos Miçotakislə görüşüb", 9),
        ]
        for order in (rows, list(reversed(rows))):
            groups = self.cards(order)[0]
            self.assertFalse(any({"AzVision.az", "Yurd.Media"} & set(g) and {"Bakupost", "Reyting.az"} & set(g) for g in groups), groups)

    def test_official_leads_are_fetched_in_small_batches_and_remembered(self):
        feed = [dict(self.row("Prezident.az", self.EU, i), sourceUrl=f"https://president.az/az/articles/view/7469{i}") for i in range(6)]
        feed.append(self.row("APA", "İlham Əliyev Antonio Koşta ilə görüşdü", 9))
        calls = []
        def fake_fetch(url, timeout=0, **_kw):
            calls.append(url)
            if url.endswith("0"):
                raise OSError("şəbəkə")
            return self.PAGE.encode("utf-8")
        with tempfile.TemporaryDirectory() as tmp, patch.object(updater, "OFFICIAL_LEAD_FILE", pathlib.Path(tmp) / "leads.json"), \
                patch.object(updater, "CACHE_DIR", pathlib.Path(tmp)), patch.object(updater, "read_feed", lambda: copy.deepcopy(feed)), \
                patch.object(updater, "fetch", fake_fetch):
            now = datetime.datetime(2026, 11, 12, 21, tzinfo=datetime.timezone.utc)
            self.assertEqual(updater.update_official_leads(now), updater.OFFICIAL_LEAD_BATCH)  # bir dövrədə 4 səhifə
            self.assertTrue(all(u.startswith("https://president.az/") for u in calls))       # agentlik səhifəsi oxunmur
            self.assertEqual(updater.update_official_leads(now), 2)                            # qalan ikisi
            self.assertEqual(updater.update_official_leads(now), 0)                            # tapılan da, alınmayan da təkrar soruşulmur
            self.assertEqual(updater.update_official_leads(now + datetime.timedelta(minutes=31)), 1)  # alınmayan yarım saatdan sonra
            feed[1]["title"] = "İlham Əliyev Dublində Moldova Prezidenti ilə görüşüb"          # başlıq dəyişdi: köhnə cümlə işlənmir
            updater.load_official_leads(feed)
            self.assertNotIn(feed[1]["sourceUrl"], updater._OFFICIAL_LEAD)
            self.assertIn(feed[2]["sourceUrl"], updater._OFFICIAL_LEAD)
            updater._OFFICIAL_LEAD.clear()

    def test_other_sections_are_not_affected(self):
        a = dict(self.row("APA", "Tramp İrana xəbərdarlıq etdi", 1), category="dunya")
        b = dict(self.row("Report", "ABŞ Prezidenti İrana xəbərdarlıq etdi", 2), category="dunya")
        self.assertFalse(updater._other_counterpart(a, b))
        self.assertFalse(updater._same_meeting(a, b))

    def test_fast_cycle_keeps_a_meeting_card_built_by_the_slow_process(self):
        # Kartın əsas sətri xülasəsizdir: sürətli dövrə «Endi Börnhemlə» mənbəsini adına görə kartdan çıxarmır.
        head = self.row("Azərbaycan qəzeti", "Azərbaycan Prezidenti İlham Əliyev Dublində Böyük Britaniyanın Baş naziri ilə görüşüb", 2)
        alt = updater._compact_alt(self.row("Axar.az", "İlham Əliyev Endi Börnhemlə görüşdü", 3))
        with tempfile.TemporaryDirectory() as tmp, patch.object(updater, "GROUPS_FILE", pathlib.Path(tmp) / "groups.json"):
            updater.GROUPS_FILE.write_text(json.dumps({head["sourceUrl"]: [alt]}), encoding="utf-8")
            out = updater.apply_groups([dict(head)])
        self.assertEqual([x["source"] for x in out[0].get("alts") or []], ["Axar.az"])


if __name__ == "__main__":
    unittest.main()
