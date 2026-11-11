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

    def test_calendar_headlines_still_combine_the_same_news(self):
        # Canlı lent: «Dekabrda» şəhər sayılıb Azərbaycandakı 9 qeyri-iş günü xəbərindən ayrılırdı.
        a = self.row("A", "Azərbaycanda 9 gün iş olmayacaq")
        b = self.row("B", "Dekabrda 9 qeyri-iş günü olacaq")
        a["summary"] = b["summary"] = "Azərbaycanda dekabr ayında doqquz qeyri-iş günü olacaq. Dekabrın 31-i Dünya Azərbaycanlılarının Həmrəyliyi Günüdür."
        self.assertEqual(len(updater.group_duplicates([a, b])), 1)

    def test_month_or_generic_location_is_not_a_different_construction_city(self):
        for when in ("Yanvarda", "Fevralda", "Martda", "Apreldə", "Mayda", "İyunda", "İyulda", "Avqustda",
                     "Sentyabrda", "Oktyabrda", "Noyabrda", "Dekabrda", "Dünyada", "Ölkədə", "Universitetində"):
            with self.subTest(when=when):
                a = self.row("A", "Azərbaycanda yeni məktəb binası açılıb")
                b = self.row("B", f"{when} yeni məktəb binası açılıb")
                a["summary"] = b["summary"] = "Yeni məktəb binası 500 şagird üçün nəzərdə tutulub."
                self.assertEqual(len(updater.group_duplicates(copy.deepcopy([a, b]))), 1)
                self.assertEqual(len(updater.attach_fresh([a, b], now=self.NOW)), 1)

    def test_other_news_keeps_exact_title_matching_across_datelines(self):
        title = "Makron və Zelenski arasında telefon danışığı olub"
        a = self.row("A", title, "Parisdə Makron Zelenski ilə telefonla danışıb.")
        b = self.row("B", title, "Kiyevdə Zelenski Makron ilə telefonla danışıb.")
        self.assertEqual(len(updater.group_duplicates(copy.deepcopy([a, b]))), 1)
        self.assertEqual(len(updater.attach_fresh([a, b], now=self.NOW)), 1)


if __name__ == "__main__":
    unittest.main()
