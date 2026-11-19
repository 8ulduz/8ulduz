"""X yazıcısı (.github/scripts/x_yazici.py): namizəd süzgəci, mp4 seçimi, iş axınının icazələri. Şəbəkə və Claude yoxdur."""
import datetime
import importlib.util
import pathlib
import unittest

ROOT = pathlib.Path(__file__).resolve().parent.parent
_spec = importlib.util.spec_from_file_location("x_yazici", ROOT / ".github" / "scripts" / "x_yazici.py")
xy = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(xy)

NOW = datetime.datetime(2026, 11, 19, 10, 0, tzinfo=datetime.timezone.utc)


def post(**kw):
    base = {"id": "2123096874748186946", "text": "Yeni transferlerimiz ilk antrenmanına çıktı. 3 grup halinde çalışma yapıldı.",
            "author": {"screen_name": "GalatasaraySK"}, "created_timestamp": NOW.timestamp() - 3600,
            "reposted_by": None, "replying_to": None, "likes": 100, "reposts": 10,
            "media": {"videos": [{"thumbnail_url": "https://pbs.twimg.com/amplify_video_thumb/1/img/a.jpg", "width": 720, "height": 1280,
                                  "formats": [{"url": "https://video.twimg.com/a/pl/x.m3u8", "container": "m3u8"},
                                              {"url": "https://video.twimg.com/a/vid/320x568/a.mp4?tag=29", "bitrate": 632000, "container": "mp4"},
                                              {"url": "https://video.twimg.com/a/vid/480x852/b.mp4?tag=29", "bitrate": 950000, "container": "mp4"},
                                              {"url": "https://video.twimg.com/a/vid/720x1280/c.mp4?tag=29", "bitrate": 2176000, "container": "mp4"}]}]}}
    base.update(kw)
    return base


class CandidateTest(unittest.TestCase):
    def test_good_post_becomes_a_row_without_text(self):
        c = xy.candidate("GalatasaraySK", post(), set(), NOW)
        self.assertEqual(c["video"], "https://video.twimg.com/a/vid/480x852/b.mp4?tag=29", "≤ 1 Mbit/s olanların ən yaxşısı")
        self.assertEqual((c["w"], c["h"], c["handle"]), (720, 1280, "GalatasaraySK"))
        self.assertEqual(c["post"], "https://x.com/GalatasaraySK/status/2123096874748186946")
        self.assertNotIn("title", c)

    def test_filtered_posts(self):
        cases = [post(reposted_by={"screen_name": "x"}), post(replying_to="a"), post(created_timestamp=NOW.timestamp() - 7 * 3600),
                 post(media={}), post(author={"screen_name": "thshaber"}),
                 post(text="Bakü'de oynanacak Karabağ maçı öncesi son antrenman."), post(text="Azerbaycan ile 2 anlaşma imzalandı."),
                 post(media={"videos": [{**post()["media"]["videos"][0], "formats": [{"url": "https://video.twimg.com/a.mp4", "bitrate": 5000000, "container": "mp4"}]}]})]
        for p in cases:
            self.assertIsNone(xy.candidate("GalatasaraySK", p, set(), NOW), p)
        self.assertIsNone(xy.candidate("GalatasaraySK", post(), {"2123096874748186946"}, NOW), "növbədə olan təkrar götürülmür")


class GeminiTest(unittest.TestCase):
    def test_timeout_moves_to_next_model_instead_of_crashing(self):
        import io
        import json
        from unittest import mock
        calls = []

        def fake_urlopen(req, timeout=None):
            calls.append(req.full_url)
            if "slow" in req.full_url:
                raise TimeoutError("The read operation timed out")
            return io.BytesIO(json.dumps({"candidates": [{"content": {"parts": [{"text": "[]"}]}}]}).encode("utf-8"))

        with mock.patch.object(xy, "_safe_models", return_value=["slow-flash", "ok-flash"]), \
             mock.patch.object(xy.urllib.request, "urlopen", fake_urlopen), mock.patch.object(xy.time, "sleep"):
            self.assertEqual(xy.ask_gemini("p", "k"), "[]")
        self.assertEqual(len(calls), 2, "gecikən model bir dəfə soruşulur, sonra növbəti")
        self.assertIn("ok-flash", calls[1])


class LateEveningTest(unittest.TestCase):
    def test_no_writing_after_the_last_slot(self):
        import tempfile
        from unittest import mock
        late = datetime.datetime(2026, 11, 19, 19, 30, tzinfo=datetime.timezone.utc)   # Bakı 23:30

        class FakeDT(datetime.datetime):
            @classmethod
            def now(cls, tz=None):
                return late

        with tempfile.TemporaryDirectory() as d:
            root = pathlib.Path(d)
            (root / "oz_x.json").write_text('{"v": 1, "items": []}\n', encoding="utf-8")
            with mock.patch.object(xy, "ROOT", root), mock.patch.object(xy.datetime, "datetime", FakeDT), \
                 mock.patch.object(xy, "collect", return_value=([xy.candidate("GalatasaraySK", post(), set(), NOW)], [])), \
                 mock.patch.object(xy, "write", side_effect=AssertionError("gec saatda Gemini soruşulmamalıdır")), \
                 mock.patch.dict(xy.os.environ, {"GEMINI_API_KEY": "k"}):
                self.assertEqual(xy.main(), 0)
            self.assertEqual((root / "oz_x.json").read_text(encoding="utf-8"), '{"v": 1, "items": []}\n')

    def test_cron_ends_before_the_last_slot(self):
        wf = (ROOT / ".github" / "workflows" / "x-yazici.yml").read_text(encoding="utf-8")
        self.assertIn('cron: "5 3-17/2 * * *"', wf, "son iş Bakı 21:05")
        self.assertLessEqual(xy.LAST_SLOT, "22:00")


class SourcesTest(unittest.TestCase):
    def test_owner_added_accounts_and_prompt_guards(self):
        for h in ("TamirveTadilat", "clashreport", "ConflictTR", "gusholderhaber", "Pars_Pluss", "avionot",
                  "Derinkuvvet", "gdhdijital", "ozetgechaber", "VoiceOfLevant"):
            self.assertIn(h, xy.xm.HESABLAR)
        for h in ("misvakcaps", "temmuz1919", "huseyinkanturk"):   # yumor və şəxsi şərh hesabları: sahib əlavə etmədi
            self.assertNotIn(h, xy.xm.HESABLAR)
        self.assertIn("Qan, meyit", xy.PROMPT, "ağır müharibə kadrı seçilmir")
        self.assertIn("fakt kimi yox", xy.PROMPT, "rəsmi olmayan hesabın xəbəri onun məlumatı kimi yazılır")
        c = xy.candidate("clashreport", post(author={"screen_name": "clashreport"}, text="Azerbaijan and Türkiye signed 2 deals."), set(), NOW)
        self.assertIsNone(c, "yeni hesabda da Azərbaycan mövzusu düşmür")
        PROMPT_OK = xy.PROMPT.format(n=3, items="- x")
        self.assertIn("ən çox 3", PROMPT_OK)


class ReelsPickTest(unittest.TestCase):
    def test_without_gemini_only_safe_accounts_and_known_ids(self):
        from unittest import mock
        tamir = xy.candidate("TamirveTadilat", post(author={"screen_name": "TamirveTadilat"}, id="2123096874748186941"), set(), NOW)
        clash = xy.candidate("clashreport", post(author={"screen_name": "clashreport"}, id="2123096874748186942"), set(), NOW)
        self.assertTrue(tamir and clash)
        self.assertIn("at", tamir, "qısa video üçün paylaşımın vaxtı")
        with mock.patch.dict(xy.os.environ, {}, clear=True):
            self.assertEqual(xy.pick_reels([tamir, clash], 6), [tamir["id"]], "açar yoxdursa müharibə hesabı düşmür")
        with mock.patch.dict(xy.os.environ, {"GEMINI_API_KEY": "k"}), \
             mock.patch.object(xy, "ask_gemini", return_value='["2123096874748186942", "999", "2123096874748186942"]'):
            self.assertEqual(xy.pick_reels([tamir, clash], 6), [clash["id"]], "Gemini yalnız namizədlərdən, təkrarsız")
        self.assertEqual(xy.REELS_PER_RUN * 7, 42, "7 iş × 6 ≈ gündə 40 (sahib)")
        self.assertIn("YAZISIZ", xy.REELS_PROMPT)


class WorkflowTest(unittest.TestCase):
    def test_workflow_writes_only_the_queue_to_main_and_keeps_the_key_in_env(self):
        wf = (ROOT / ".github" / "workflows" / "x-yazici.yml").read_text(encoding="utf-8")
        self.assertIn("contents: write", wf)
        self.assertEqual(wf.count("git add"), 1)
        self.assertIn("git add oz_x.json\n", wf)
        self.assertIn("git push -q origin HEAD:main", wf)
        self.assertNotIn("OZ_DERC", wf)
        self.assertNotIn("echo \"$ANTHROPIC_API_KEY", wf)
        self.assertIn("GEMINI_API_KEY: ${{ secrets.GEMINI_API_KEY }}", wf)
        src = (ROOT / ".github" / "scripts" / "x_yazici.py").read_text(encoding="utf-8")
        self.assertIn('"x-goog-api-key": key', src, "açar başlıqda gedir")
        self.assertNotIn("?key=", src, "açar ünvana (loqa) düşmür")


if __name__ == "__main__":
    unittest.main()
