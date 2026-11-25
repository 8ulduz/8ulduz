"""Səsi dinləmə (video_dinle.py) videonun dili ilə (dil profili, 2026-11-26): Whisper-in dili və müqayisə qaydası profildəndir."""
import os
import pathlib
import sys
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / ".github" / "scripts"))
import video_dinle as vd  # noqa: E402


class DinleTest(unittest.TestCase):
    def test_azerbaijani_words_are_spoken_forms(self):
        self.assertEqual(vd.words("Qubada 25 nəfər."), ["qubada", "iyirmi", "beş", "nəfər"], "az_text: rəqəm sözlə (Whisper sözlə yazır)")

    def test_other_language_words_are_plain(self):
        self.assertEqual(vd.words("Привет, мир — 25!", "plain"), ["привет", "мир", "25"])

    def test_report_names_the_voice_from_the_profile(self):
        az = vd.profil("az")
        self.assertEqual(az["dinle"], {"whisper": "az", "metn": "az_text"})
        out = vd.report(["a", "b"], ["a", "c"], "a c", {"ses": "babek"}, "large-v3", az)
        self.assertIn("səs: Babək", out)
        self.assertIn("**1/2**", out)
        keep = os.environ.get("VIDEO_DIL_QOVLUQ")
        os.environ["VIDEO_DIL_QOVLUQ"] = str(ROOT / "tests" / "fixtures" / "video-dil")
        try:
            xx = vd.profil("xx")
        finally:
            os.environ.pop("VIDEO_DIL_QOVLUQ", None)
            if keep is not None:
                os.environ["VIDEO_DIL_QOVLUQ"] = keep
        self.assertIn("səs: XX-voice", vd.report(["a"], ["a"], "a", {"ses": "edgexx"}, "large-v3", xx))
        self.assertEqual(xx["dinle"]["metn"], "plain")


if __name__ == "__main__":
    unittest.main()
