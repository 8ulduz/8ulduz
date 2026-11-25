"""Video səsi (.github/scripts/video_ses.py): altyazı cümləni bölürsə cümlə bir nəfəsdə səslənir (sahib, 2026-11-25: «yeni
videolarda sətirdən sətrə keçəndə mənasız pauza verir oxunuşda»). Model yüklənmir: qruplaşma və vaxt bölgüsü saxta səslə yoxlanır."""
import importlib.util
import json
import pathlib
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("video_ses", ROOT / ".github" / "scripts" / "video_ses.py")
vs = importlib.util.module_from_spec(spec)
spec.loader.exec_module(vs)
from az_text import PAUSE_CLAUSE, PAUSE_SENTENCE, VOICE  # noqa: E402  (video_ses.py ses-server qovluğunu sys.path-ə əlavə edir)

# Videonun cümlə sonu fasiləsi (sahib, 2026-11-25: «oxunuş sürətlidir»): «Dinlə»nin PAUSE_SENTENCE-dən uzundur.
SENT = vs.VIDEO_PAUSE[PAUSE_SENTENCE]

# Qruplaşma üçün hissələr (tests/fixtures/video-xeber.json-dan; başlıq artıq oxunmur — prepare().say izahla başlayır, amma
# qruplaşma qaydası hər siyahıya eynidir): 1 və 2 eyni cümlədir.
SAY = [
    "Astarada qəza nəticəsində 5 kəndin qaz təchizatı dayandırılıb",
    "Astara rayonunda baş verən yol-nəqliyyat hadisəsi",
    "nəticəsində Ərçivan qəsəbəsindən keçən qaz xətti zədələnib.",
    "AZƏRTAC xəbər verir ki, bu səbəbdən rayonun beş kəndinin qaz təchizatında müvəqqəti fasilə yaranıb.",
    "Ətraflı məlumat səkkiz ulduz nöqtə az saytında.",
]


class FakeVoice:
    """Hər hərf bir token; sait 4 kadr, boşluq 3, qalan 1 (müddət hərfə görə fərqlidir — bölgü hərf sayı ilə yox, müddətlə
    getməlidir); kadr SPF nümunə. frames=False — model müddəti vermir (hərf payı)."""

    SPF = 10
    VOWELS = set("aeəıioöuü")

    def __init__(self, frames=True):
        self.frames, self.calls = frames, []
        self.used = {"müddət": 0, "pay": 0}

    def dur(self, ch):
        return 4 if ch in self.VOWELS else 3 if ch == " " else 1

    def tokens(self, text):
        return len(text.strip())

    def wave(self, said):
        self.calls.append(said)
        fr = [self.dur(c) for c in said]
        return b"\x01\x00" * (sum(fr) * self.SPF), (fr if self.frames else None)


class GroupsTest(unittest.TestCase):
    def test_fixture_sentence_split_by_captions_is_one_group(self):
        self.assertEqual(vs.groups(SAY), [[0], [1, 2], [3], [4]])
        # video-xeber.cjs prepare().davam eyni nəticəni dəqiq verir
        self.assertEqual(vs.groups(SAY, [False, False, True, False, False]), [[0], [1, 2], [3], [4]])

    def test_davam_catches_capital_and_digit_continuations(self):
        # «təqsirləndirilən Xudat | Məmmədovun …», «azalaraq | 3 565,2 dollar» — mətndən təxmin bunları tutmur, davam tutur
        parts = ["Başlıq", "Məhkəmə təqsirləndirilən Xudat", "Məmmədovun barəsindəki qərardan şikayət edilib.",
                 "Qiymət 12 dollar azalaraq", "3 565,2 dollar olub.", "Sonluq."]
        self.assertEqual(vs.groups(parts), [[0], [1], [2], [3], [4], [5]])
        self.assertEqual(vs.groups(parts, [False, False, True, False, True, False]), [[0], [1, 2], [3, 4], [5]])
        # uyğun gəlməyən davam (uzunluq) nəzərə alınmır — mətndən təxmin
        self.assertEqual(vs.groups(parts, [False, True]), vs.groups(parts))

    def test_continues_rule(self):
        c = vs.continues
        self.assertTrue(c("Dövlət ümumi təhsil müəssisələrində vakant direktor vəzifələrinə işə", "qəbul üçün elektron sənəd qəbulu başlayacaq."))
        self.assertTrue(c("Kələm tərəvəzlərdən biri olmaqla yanaşı,", "zəngin vitamin tərkibi ilə faydalıdır."), "vergüldən sonra da davam")
        self.assertTrue(c("O dedi:", "«biz hazırıq»."), "dırnaqla başlayan davam")
        self.assertFalse(c("Qaz xətti zədələnib.", "nəticədə kəndlər qazsız qalıb."), "cümlə sonu")
        self.assertFalse(c("Başlıq nöqtəsizdir", "Astara rayonunda qəza olub."), "böyük hərf: başlıq izaha qoşulmur")
        self.assertFalse(c("Sual?", "bəli."))
        self.assertFalse(c("Bəs…", "davam edir."), "üç nöqtə cümlə sonudur")
        self.assertFalse(c("Son hissə", ""))


class SaidTest(unittest.TestCase):
    def test_group_is_one_sentence_even_past_220_chars(self):
        # 06ba2c78ef: cümlə bütöv səslənir. Qrupun mətni 220 simvoldan uzun olsa da vergüldə bölünmür.
        long = ["Birinci hissədə nazirlik, agentlik, komitə, xidmət və digər qurumların nümayəndələri,",
                "habelə rayon icra hakimiyyətlərinin, bələdiyyələrin və ictimai birliklərin təmsilçiləri,",
                "eləcə də ekspertlər və jurnalistlər iştirak edib, müzakirələr axşama qədər davam edib."]
        text = " ".join(long)
        self.assertGreater(len(text), 220)
        items = vs.say_items(text)
        self.assertEqual(len(items), 1, items)
        self.assertEqual(items[0][1], SENT)
        self.assertEqual(vs.groups(["Başlıq"] + long + ["Sonluq."]), [[0], [1, 2, 3], [4]])


class RenderTest(unittest.TestCase):
    SR = 1000

    def spans(self, parts, voice, davam=None):
        pcm, spans, total = vs.render(parts, voice, self.SR, davam)
        self.assertEqual(len(pcm) // 2, total)
        return spans, total

    def test_group_is_voiced_once_and_parts_follow_each_other(self):
        v = FakeVoice()
        spans, total = self.spans(SAY, v)
        self.assertEqual(len(v.calls), 4, "5 hissə, 4 səsləndirmə: 1 və 2 bir mətndir")
        joined = v.calls[1]
        self.assertTrue(joined.startswith("astara rayonunda") and joined.endswith("zədələnib"), joined)
        self.assertEqual(len(spans), len(SAY), "vaxtlar.json: hər hissəyə bir cüt")
        self.assertEqual(spans[0][0], 0)
        self.assertEqual(spans[-1][1], total)
        for (s1, e1), (s2, e2) in zip(spans, spans[1:]):
            self.assertEqual(e1, s2, "hissələr ardıcıldır, arada boşluq və üst-üstə düşmə yoxdur")
            self.assertLess(s1, e1)
        # cümlənin ortasında sükut əlavə edilmir: 1-in sonu 2-nin başlanğıcıdır və qrupun səsinin içindədir
        self.assertLess(spans[1][1], spans[2][1] - int(self.SR * SENT))

    def test_cut_is_at_the_space_before_the_next_part_by_model_durations(self):
        v = FakeVoice()
        spans, _ = self.spans(SAY, v)
        said = v.calls[1]
        first = vs.spoken(SAY[1])
        self.assertEqual(said[len(first)], " ", "sərhəd boşluqdadır")
        self.assertTrue(said.startswith(first))
        # 1-ci hissə: öz hərflərinin müddəti (boşluq növbəti hissəyə düşür)
        self.assertEqual(spans[1][1] - spans[1][0], sum(v.dur(c) for c in first) * v.SPF)

    def test_cut_without_model_durations_by_letter_share(self):
        v = FakeVoice(frames=False)
        spans, _ = self.spans(SAY, v)
        said = v.calls[1]
        n = sum(v.dur(c) for c in said) * v.SPF
        self.assertEqual(spans[1][1] - spans[1][0], round(n * len(vs.spoken(SAY[1])) / len(said)))

    def test_numbers_are_measured_as_spoken(self):
        # «15:00-da», «27-də» sözlə oxunur — pay oxunan mətnə görədir, yazılana görə yox
        parts = ["Başlıq", "Qəbul noyabrın 27-də saat 15:00-da", "başlayacaq.", "Sonluq."]
        v = FakeVoice()
        spans, _ = self.spans(parts, v)
        first = vs.spoken(parts[1])
        self.assertNotRegex(first, r"[0-9]")
        self.assertIn("iyirmi yeddi", first)
        self.assertTrue(v.calls[1].startswith(first + " "), v.calls[1])
        self.assertEqual(spans[1][1] - spans[1][0], sum(v.dur(c) for c in first) * v.SPF)

    def test_three_parts_and_davam(self):
        parts = ["Başlıq", "Məhkəmə təqsirləndirilən Xudat", "Məmmədovun barəsindəki qərardan", "şikayət edilib.", "Sonluq."]
        v = FakeVoice()
        spans, total = self.spans(parts, v, [False, False, True, True, False])
        self.assertEqual(len(v.calls), 3)
        a, b, c = (vs.spoken(p) for p in parts[1:4])
        self.assertEqual(v.calls[1], f"{a} {b} {c}")
        self.assertEqual(spans[1][1] - spans[1][0], sum(v.dur(x) for x in a) * v.SPF)
        self.assertEqual(spans[2][1] - spans[2][0], sum(v.dur(x) for x in " " + b) * v.SPF)
        self.assertEqual(spans[-1][1], total)

    def test_ungrouped_parts_keep_their_own_pause(self):
        # cümlə sonu fasiləsi yerindədir: hər qrupun sonunda videonun cümlə fasiləsi (SENT)
        v = FakeVoice()
        spans, _ = self.spans(SAY, v)
        head = sum(v.dur(c) for c in v.calls[0]) * v.SPF
        self.assertEqual(spans[0][1], head + int(self.SR * SENT))

    def test_cut_offsets_maps_across_sentences_inside_a_group(self):
        # qrupun içində phrases cümləni bölsə (iki səsləndirmə), sərhəd ikincinin başlanğıcına düşür, fasilə əvvəlkinindir
        items = [("bir iki.", 0.38), ("üç dörd.", 0.38)]
        self.assertEqual(vs.cut_offsets(["bir iki.", "üç dörd."], items), [(1, 0)])
        self.assertEqual(vs.offset_samples("üç dörd.", 0, 500, [1] * 8, len), 0)

    def test_offset_samples_survives_tokenizer_errors(self):
        def bad(_):
            raise ValueError("tokenizer")
        self.assertEqual(vs.offset_samples("abcd", 2, 400, [1, 1, 1, 1], bad), 200, "hərf payına keçir")
        self.assertEqual(vs.offset_samples("abcd", 2, 400, [1, 1, 1, 1], lambda _: 99), 200, "uyğunsuz token sayı da")


class TempoTest(unittest.TestCase):
    """Sahib, 2026-11-25: «oxunuş sürətlidir. oxunuşu normal et». Ölçü: modelin öz sürəti və «Dinlə»nin fasilələri ilə 155 söz/dəq."""

    def test_video_reads_slower_than_the_model_and_pauses_longer_than_dinle(self):
        self.assertLess(vs.VIDEO_RATE, VOICE["speaking_rate"], "video modelin öz sürətindən yavaş oxuyur")
        self.assertGreaterEqual(vs.VIDEO_RATE, 0.8, "çox yavaş deyil: səs uzanıb sürünmür")
        self.assertGreater(vs.VIDEO_PAUSE[PAUSE_SENTENCE], PAUSE_SENTENCE)
        self.assertGreater(vs.VIDEO_PAUSE[PAUSE_CLAUSE], PAUSE_CLAUSE)
        # vergül fasiləsi cümlə fasiləsindən qısa qalır (intonasiya: vergül davam, nöqtə son)
        self.assertLess(vs.VIDEO_PAUSE[PAUSE_CLAUSE], vs.VIDEO_PAUSE[PAUSE_SENTENCE])
        pauses = [p for _, p in vs.say_items("Bakıda, Gəncədə və Sumqayıtda hava açıq olacaq. Külək zəifləyəcək.")]
        self.assertTrue(pauses and set(pauses) <= set(vs.VIDEO_PAUSE.values()), pauses)
        self.assertEqual(pauses[-1], vs.VIDEO_PAUSE[PAUSE_SENTENCE], "cümlə sonu videonun fasiləsi ilə")
        src = (ROOT / ".github" / "scripts" / "video_ses.py").read_text(encoding="utf-8")
        self.assertIn("tune(VitsModel.from_pretrained(name).eval(), speaking_rate=VIDEO_RATE)", src, "model video tempi ilə qurulur")
        # «Dinlə» (ses-server) dəyişmir: ortaq ayar modelin öz sürətidir
        self.assertEqual(VOICE["speaking_rate"], 1.0)


class ContractTest(unittest.TestCase):
    def test_video_xeber_sends_davam(self):
        src = (ROOT / ".github" / "scripts" / "video-xeber.cjs").read_text(encoding="utf-8")
        self.assertIn("davam: p.davam", src, "voice() hissələr faylına davam yazır")
        self.assertIn('data.get("davam")', (ROOT / ".github" / "scripts" / "video_ses.py").read_text(encoding="utf-8"))

    def test_main_writes_one_span_per_part(self):
        # vaxtlar.json formatı dəyişmir: {"sr", "duration", "parts": [[s, e], …]} saniyə ilə (video-xeber.cjs wordTimes, timeline)
        import tempfile

        class Stub(FakeVoice):
            sr = 1000

        real = vs.Sara
        vs.Sara = lambda: Stub()
        try:
            with tempfile.TemporaryDirectory() as d:
                src, wav, out = (pathlib.Path(d) / n for n in ("h.json", "s.wav", "v.json"))
                src.write_text(json.dumps({"parts": SAY, "davam": [False, False, True, False, False]}), encoding="utf-8")
                vs.main(str(src), str(wav), str(out))
                v = json.loads(out.read_text(encoding="utf-8"))
        finally:
            vs.Sara = real
        self.assertEqual(set(v), {"sr", "duration", "parts"})
        self.assertEqual(len(v["parts"]), len(SAY))
        self.assertTrue(all(len(p) == 2 and p[0] <= p[1] for p in v["parts"]))
        self.assertEqual(v["parts"][-1][1], v["duration"])


if __name__ == "__main__":
    unittest.main()
