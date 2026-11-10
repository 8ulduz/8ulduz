"""«Dinlə» səsləri (.github/scripts/ses.py): hansı xəbər səslənir, oxunan mətn necə qurulur."""
import datetime
import importlib.util
import pathlib
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("ses", ROOT / ".github" / "scripts" / "ses.py")
ses = importlib.util.module_from_spec(spec)
spec.loader.exec_module(ses)


class SesTest(unittest.TestCase):
    def test_pick_az_recent_newest_first(self):
        now = datetime.datetime(2026, 11, 7, 12, tzinfo=datetime.timezone.utc)
        at = lambda h: (now - datetime.timedelta(hours=h)).isoformat()
        row = lambda i, title, h, **kw: {"id": i * 16, "title": title, "source": "APA", "sourceUrl": f"https://apa.az/{i}",
                                         "category": "iqtisadiyyat", "publishedAt": at(h), "lang": "az", **kw}
        rows = [row("a", "Bakıda yeni park açıldı", 1), row("b", "Neft qiyməti artdı", 2, alts=[{"source": "Report", "title": "Neft qiyməti artdı", "sourceUrl": "https://report.az/1"}]),
                row("c", "Rus xəbəri", 1, lang="ru"), row("d", "Köhnə xəbər", 40), row("e", "Artıq səslənib", 1),
                {**row("f", "Keçidsiz", 1), "sourceUrl": "http://x.az/1"}]
        got = [a["title"] for a in ses.pick(rows, {"e" * 16}, now)]
        self.assertEqual(got, ["Bakıda yeni park açıldı", "Neft qiyməti artdı"])

    def test_script_starts_with_title_and_source_then_full_text(self):
        a = {"title": "Bakıda yağış.", "source": "APA", "summary": "Qısa"}
        self.assertEqual(ses.script_of(a, "Bakıda yağış. Sabah  güclü yağış gözlənilir."), "Bakıda yağış. APA xəbər verir. Sabah güclü yağış gözlənilir.")
        self.assertEqual(ses.script_of(a, ""), "Bakıda yağış. APA xəbər verir. Qısa", "tam mətn alınmasa saytdakı xülasə")

    def test_minute_feed_stories_are_added_once(self):
        feed = [{"id": "a" * 16, "title": "Köhnə"}]
        live = [{"id": "b" * 16, "title": "Təzə"}, {"id": "a" * 16, "title": "Köhnə"}]
        self.assertEqual([a["title"] for a in ses.merged(feed, live)], ["Təzə", "Köhnə"])

    def test_small_batches_so_a_new_story_is_voiced_within_a_minute(self):
        # Sahib, 2026-11-08: «bizim hədəf anında dinləyə bilməkdir». 40-lıq dəstədə təzə xəbər ~5 dəqiqə gözləyirdi.
        self.assertLessEqual(ses.PER_RUN, 8)
        wf = (ROOT / ".github" / "ses-reposu" / "ses.yml").read_text(encoding="utf-8")
        self.assertIn('cron: "*/10 * * * *"', wf)
        self.assertIn("sleep 15", wf)
        # Cədvəl gecikir/buraxılır: iş bitəndə növbətini özü işə salır.
        self.assertIn("actions: write", wf)
        self.assertIn('gh workflow run ses.yml -R "${{ github.repository }}"', wf)

    def test_voices_made_before_the_text_cleanup_are_made_again(self):
        a, b = "a" * 16, "b" * 16
        self.assertEqual(ses.stale({a: 1, b: 1}, {a: ses.CLEAN_AT - 60, b: ses.CLEAN_AT + 60}), {a})

    def test_full_store_makes_room_for_newer_stories_only(self):
        now = 1_800_000_000
        a, b, c = "a" * 16, "b" * 16, "c" * 16
        pub = {a: now - 20 * 3600, c: now - 3600}
        born = {a: now - 3600, b: now - 2 * 3600, c: now - 600}
        self.assertEqual(ses.evict({a: 1, b: 1, c: 1}, {a, c}, pub, born, now), b, "əvvəl lentdən çıxmış səs")
        self.assertEqual(ses.evict({a: 1, c: 1}, {a, c}, pub, born, now - 1800), a, "sonra ən köhnə xəbər")
        self.assertIsNone(ses.evict({c: 1}, {c}, pub, born, now - 5 * 3600), "təzə xəbər köhnə xəbər üçün silinmir")

    def test_long_text_is_cut_at_a_sentence(self):
        text = ("Bir cümlə budur. " * 400).strip()
        out = ses.clip(text, 1000)
        self.assertLessEqual(len(out), 1000)
        self.assertTrue(out.endswith("."))


if __name__ == "__main__":
    unittest.main()


class HostRedoTest(unittest.TestCase):
    def test_only_listed_source_audio_written_before_the_fix_is_redone(self):
        t = ses.REDO_HOSTS["oxu24.com"]
        feed = [{"id": "a" * 16, "sourceUrl": "https://oxu24.com/az/cemiyyet/1/x"}, {"id": "b" * 16, "sourceUrl": "https://www.oxu24.com/az/2"},
                {"id": "c" * 16, "sourceUrl": "https://apa.az/3"}, {"id": "d" * 16, "sourceUrl": "https://oxu24.com/az/4"}]
        have = {"a" * 16: "h", "b" * 16: "h", "c" * 16: "h", "d" * 16: "h"}
        born = {"a" * 16: t - 60, "b" * 16: t - 60, "c" * 16: t - 60, "d" * 16: t + 60}
        self.assertEqual(ses.host_redo(have, born, feed), {"a" * 16, "b" * 16}, "yalnız Oxu24, yalnız düzəlişdən əvvəlki səs")


class SpokenTextTest(unittest.TestCase):
    """Sahib, 2026-11-10: «ikincidə ortada video sözü keçir — lazımsız yerlər oxunmasın»."""

    def test_cop_is_read_as_a_word(self):
        """Sahib, 2026-11-10: «kop 31 yerinə co o p deyir»."""
        self.assertEqual(ses.spoken_text("ölkənin COP31 hazırlıqlarına və COP-29 irsinə"), "ölkənin Kop 31 hazırlıqlarına və Kop 29 irsinə")
        self.assertEqual(ses.spoken_title("COP iclası Bakıda"), "Kop iclası Bakıda")
        self.assertEqual(ses.spoken_text("ABŞ və BMT COPE"), "ABŞ və BMT COPE")
        feed = [{"id": "a" * 16, "title": "X", "summary": "COP31 hazırlığı"}, {"id": "b" * 16, "title": "Y", "summary": "adi"},
                {"id": "c" * 16, "title": "COP31", "summary": ""}]
        have = {"a" * 16: 1, "b" * 16: 1, "c" * 16: 1}
        born = {"a" * 16: ses.SAY_AT - 60, "b" * 16: ses.SAY_AT - 60, "c" * 16: ses.SAY_AT + 60}
        self.assertEqual(ses.say_redo(have, born, feed), {"a" * 16})

    def test_title_markers_are_not_read(self):
        cases = {
            'Cevdet Yılmaz: "Ərdoğanla Əliyevin görüşü yayılan dezinformasiyalara ən yaxşı cavab oldu" - Video':
                'Cevdet Yılmaz: "Ərdoğanla Əliyevin görüşü yayılan dezinformasiyalara ən yaxşı cavab oldu"',
            "Cəbrayılda Meşə Təlim Mərkəzi açıldı - Foto": "Cəbrayılda Meşə Təlim Mərkəzi açıldı",
            "Anıtqəbirdə böyük izdiham (FOTO)": "Anıtqəbirdə böyük izdiham",
            "Bakıda güclü yağış [VİDEO]": "Bakıda güclü yağış",
            "VİDEO: Qəzanın anı kameraya düşdü": "Qəzanın anı kameraya düşdü",
            "Yeni körpü açıldı - FOTO/VİDEO": "Yeni körpü açıldı",
            "Yeni körpü (Foto+Video)": "Yeni körpü",
            "Prezident tədbirdə iştirak edib - YENİLƏNİB": "Prezident tədbirdə iştirak edib",
        }
        for raw, want in cases.items():
            with self.subTest(raw=raw):
                self.assertEqual(ses.spoken_title(raw), want)

    def test_ordinary_words_stay(self):
        for t in ("Qəzanın videosu yayıldı", "Videoda polis görünür", "Foto sərgisi açıldı", "Video oyunlar bazarı böyüyür"):
            with self.subTest(t=t):
                self.assertEqual(ses.spoken_title(t), t)

    def test_body_marker_sentences_and_credits_are_dropped(self):
        body = "Görüş Ankarada keçirilib. Video. Tərəflər əməkdaşlığı müzakirə edib. Foto: APA. Videoda nazir danışır."
        self.assertEqual(ses.spoken_text(body), "Görüş Ankarada keçirilib. Tərəflər əməkdaşlığı müzakirə edib. Videoda nazir danışır.")

    def test_script_reads_clean_title(self):
        a = {"title": "Cəbrayılda mərkəz açıldı - Foto", "source": "Oxu.az", "summary": "Mərkəz açıldı. Foto: Oxu.az"}
        self.assertEqual(ses.script_of(a, ""), "Cəbrayılda mərkəz açıldı. Oxu.az xəbər verir. Mərkəz açıldı.")

    def test_old_audio_of_marked_titles_is_redone_once(self):
        at = ses.MARK_AT
        feed = [{"id": "a" * 16, "title": "Görüş keçirildi - Video"}, {"id": "b" * 16, "title": "Görüş keçirildi"},
                {"id": "c" * 16, "title": "Körpü açıldı (FOTO)"}]
        have = {"a" * 16: "h", "b" * 16: "h", "c" * 16: "h"}
        born = {"a" * 16: at - 60, "b" * 16: at - 60, "c" * 16: at + 60}
        self.assertEqual(ses.marker_redo(have, born, feed), {"a" * 16}, "yalnız nişanlı və düzəlişdən əvvəlki səs")
