"""X yazıcısı (.github/scripts/x_yazici.py): namizəd süzgəci, mp4 seçimi, iş axınının icazələri. Şəbəkə və Claude yoxdur."""
import json
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
                 mock.patch.object(xy, "write", side_effect=AssertionError("gec saatda xəbər yazılmamalıdır")), \
                 mock.patch.object(xy, "ask_gemini", return_value="[]"), \
                 mock.patch.dict(xy.os.environ, {"GEMINI_API_KEY": "k"}):
                self.assertEqual(xy.main(), 0)
            doc = json.loads((root / "oz_x.json").read_text(encoding="utf-8"))
            self.assertEqual(doc["items"], [], "gec saatda xəbər yoxdur; qısa video gecə də yığılır")

    def test_cron_every_20_minutes_news_only_in_the_day(self):
        wf = (ROOT / ".github" / "workflows" / "x-yazici.yml").read_text(encoding="utf-8")
        self.assertIn('cron: "5,25,45 * * * *"', wf, "qısa videolar gecə-gündüz 20 dəqiqədən bir (sahib: «daima təzələnsin»)")
        src = (ROOT / ".github" / "scripts" / "x_yazici.py").read_text(encoding="utf-8")
        self.assertEqual(src.count("baku.hour % 2 and baku.minute < 20"), 2, "xəbər və transfer saatda bir dəfə, 3 dəfə yox")
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
        self.assertGreaterEqual(xy.REELS_PER_RUN * 72 // 2, 100, "72 işin yarısı belə işləsə gündə ≥100 yeni video (sahib)")
        self.assertGreaterEqual(xy.xm.REELS_MAX, 200, "gündə ~100 gəlir: lent ən azı 2 günü tutur")
        self.assertIn("izah", xy.REELS_PROMPT, "sahib 2026-11-22: «mənası başa düşülməyən videolar olmasın» — qısa izah")


class VideolentSourcesTest(unittest.TestCase):
    def test_visual_accounts_added_and_risky_ones_left_out(self):
        for h in ("Rainmaker1973", "LaLiga", "premierleague", "aspor", "buitengebieden", "IGN", "NBA", "F1", "wonderofscience", "Olympics"):
            self.assertIn(h, xy.xm.HESABLAR)
        for h in ("TheFigen_", "Pirat_Nation", "ufc", "ClutchPoints", "CrazyClipsOnly", "FootballFunnys", "theScore", "NBATV", "Onedio"):
            self.assertNotIn(h, xy.xm.HESABLAR, "siyasət, mərc/kazino, qan riski və ya danışıq videosu")
        self.assertTrue(xy.REELS_SAFE <= set(xy.xm.HESABLAR), "ehtiyat siyahının hər hesabı cədvəldədir")
        self.assertIn("Rainmaker1973", xy.REELS_SAFE, "Gemini cavab verməyəndə vizual hesablar")


class TransferCandidateTest(unittest.TestCase):
    def test_transfer_posts_without_video(self):
        p = post(id="2123096874748186951", author={"screen_name": "FabrizioRomano"}, media={"photos": [{"url": "https://pbs.twimg.com/media/x.jpg"}]},
                 text="Here we go! Tchouameni signs new deal at Real Madrid until June 2030.")
        c = xy.transfer_candidate("FabrizioRomano", p, set(), NOW)
        self.assertEqual((c["poster"], c["handle"]), ("https://pbs.twimg.com/media/x.jpg", "FabrizioRomano"))
        self.assertNotIn("video", c, "video tələb olunmur")
        for bad in (post(id="2123096874748186952", author={"screen_name": "FabrizioRomano"}, text="Great atmosphere at the stadium tonight with fans."),
                    post(id="2123096874748186953", author={"screen_name": "FabrizioRomano"}, text="Qarabağ signs a new striker, here we go."),
                    post(id="2123096874748186954", author={"screen_name": "FabrizioRomano"}, text="Here we go deal done.", reposted_by={"screen_name": "x"})):
            self.assertIsNone(xy.transfer_candidate("FabrizioRomano", bad, set(), NOW), bad["text"])
        self.assertIsNone(xy.transfer_candidate("GalatasaraySK", post(text="Transfer deal agreed with new striker."), set(), NOW), "yalnız transfer hesabları")
        self.assertIn("transfer", xy.TRANSFER_PROMPT.format(n=3, items="- x"))


class WorkflowTest(unittest.TestCase):
    def test_workflow_writes_only_the_queue_to_main_and_keeps_the_key_in_env(self):
        wf = (ROOT / ".github" / "workflows" / "x-yazici.yml").read_text(encoding="utf-8")
        self.assertIn("contents: write", wf)
        self.assertEqual(wf.count("git add"), 1)
        self.assertIn("git add oz_x.json\n", wf)
        self.assertIn("git push -q origin HEAD:main", wf)
        self.assertIn("git config user.name 8ulduz-bot", wf, "pull --rebase üçün də ad: main irəli gedəndə iş düşməsin")
        self.assertNotIn("OZ_DERC", wf)
        self.assertNotIn("echo \"$ANTHROPIC_API_KEY", wf)
        self.assertIn("GEMINI_API_KEY: ${{ secrets.GEMINI_API_KEY }}", wf)
        src = (ROOT / ".github" / "scripts" / "x_yazici.py").read_text(encoding="utf-8")
        self.assertIn('"x-goog-api-key": key', src, "açar başlıqda gedir")
        self.assertNotIn("?key=", src, "açar ünvana (loqa) düşmür")


if __name__ == "__main__":
    unittest.main()


class VideolentTenfoldTest(unittest.TestCase):
    """Sahib, 2026-11-19: «maraqlı video mənbəyini 10 qat artır. video axını tiktok kimi olsun»."""

    def test_many_reel_only_sources_rotate_through_runs(self):
        hs = list(xy.xm.VIDEOLENT_HESABLAR)
        self.assertGreaterEqual(len(hs), 150, "Videolent mənbələri əvvəlkinin (~30) bir neçə qatı")
        self.assertFalse(set(hs) & set(xy.xm.HESABLAR), "Videolent hesabları xəbər hesablarından ayrıdır")
        seen = set()
        t0 = datetime.datetime(2026, 11, 20, tzinfo=datetime.timezone.utc)
        per = xy.VL_PER_RUN // len(xy.xm.VIDEOLENT_QRUPLAR)
        for k in range(2 * (max(map(len, xy.xm.VIDEOLENT_QRUPLAR.values())) // per + 2)):   # birinci dərəcəli mənbələr hər işdə, qalanı bir az yavaş dövr edir
            part = xy.videolent_slice(t0 + datetime.timedelta(minutes=20 * k))
            self.assertLessEqual(len(part), xy.VL_PER_RUN)
            seen.update(part)
        self.assertEqual(seen, set(hs), "bir neçə saatda hər hesab yoxlanır")

    def test_reel_only_rows_pass_the_reel_check_but_never_become_news(self):
        h = next(iter(xy.xm.VIDEOLENT_HESABLAR))
        row = {"id": "2123096874748186941", "handle": h, "post": f"https://x.com/{h}/status/2123096874748186941",
               "video": "https://video.twimg.com/ext_tw_video/1/pu/vid/720x1280/a.mp4", "poster": "https://pbs.twimg.com/a.jpg",
               "w": 720, "h": 1280, "at": "2026-11-19T10:00:00+00:00", "src": ["Amazing goal from the halfway line"]}
        self.assertIsNone(xy.xm.reel_check(row))
        news = {**row, "kind": "x-maraqli", "date": "2026-11-19", "slot": "12:00", "title": "Başlıq", "lead": "Giriş", "body": ["Mətn"]}
        self.assertTrue(xy.xm.check(news), "Videolent hesabından xəbər keçmir")
        src = (ROOT / ".github" / "scripts" / "x_yazici.py").read_text(encoding="utf-8")
        self.assertIn('[c for c in cands if not c.get("reel_only")][:MAX_CANDIDATES]', src)

    def test_each_run_spreads_videos_over_topics(self):
        """Sahib: «videoların əksəriyyəti futboldur. belə olmasın proporsional olsun müxtəlif mövzular»."""
        q = xy.xm.VIDEOLENT_QRUPLAR
        for m in ("idman", "tebiet", "elm", "texnika", "yemek", "oyun", "kino", "maraqli"):
            self.assertGreaterEqual(len(q[m]), 40, f"{m}: hər mövzuda çoxlu mənbə")
        self.assertLess(len(q["idman"]) / len(xy.xm.VIDEOLENT_HESABLAR), 0.35, "idman mənbələrin üçdə birindən azdır")
        self.assertGreaterEqual(len(xy.xm.VIDEOLENT_HESABLAR), 1000, "sahib: «1000 olsun»")
        sport = [{"id": str(i), "handle": h} for i, h in enumerate(list(q["idman"])[:10])]
        other = [{"id": f"9{i}", "handle": h} for i, h in enumerate([next(iter(q["tebiet"])), next(iter(q["elm"])), next(iter(q["kino"]))])]
        got = xy.by_topic(sport + other, lambda c: c["handle"], 4)
        self.assertEqual([xy.xm.movzu(c["handle"]) for c in got], ["idman", "tebiet", "elm", "kino"], "bir işdə mövzular növbə ilə")
        part = xy.videolent_slice(datetime.datetime(2026, 11, 20, tzinfo=datetime.timezone.utc))
        self.assertGreaterEqual(len({xy.xm.movzu(h) for h in part}), 8, "hər iş bütün mövzulardan hesab yoxlayır")
        self.assertIn("MÜXTƏLİF", xy.REELS_PROMPT)
        self.assertIn("erotik", xy.REELS_PROMPT)


class RetryPassTest(unittest.TestCase):
    def test_rate_limited_videolent_accounts_are_asked_once_more_slowly(self):
        """Sahib 2026-11-20 («tiktokdan geri qalmasın»): həddə düşən Videolent hesabı keçidin sonunda bir dəfə də soruşulur."""
        from unittest import mock
        vl = ["SmithsonianZoo", "VisitNorway", "visitlondon"]
        seen = {}

        def fake(url):
            h = url.split("/profile/")[1].split("/")[0]
            seen[h] = seen.get(h, 0) + 1
            if h in xy.xm.HESABLAR or (h != "visitlondon" and seen[h] == 1):
                raise OSError("404")
            return {"results": []}

        sleeps = []
        with mock.patch.object(xy, "videolent_slice", return_value=vl), mock.patch.object(xy, "fetch_json", fake), \
             mock.patch.object(xy.time, "sleep", sleeps.append):
            _, failed = xy.collect(set(), NOW)
        self.assertEqual([seen[h] for h in vl], [2, 2, 1], "düşən Videolent hesabı ikinci dəfə, alınan bir dəfə")
        self.assertTrue(all(seen[h] == 2 for h in xy.xm.HESABLAR), "xəbər hesabı əvvəlki kimi iki cəhd")
        self.assertIn(xy.RETRY_PAUSE, sleeps)
        self.assertFalse(any(f.startswith(("SmithsonianZoo", "VisitNorway")) for f in failed), "ikinci cəhddə alınan düşmüş sayılmır")
        self.assertLessEqual(xy.RETRY_BUDGET, 10 * 60, "iş 20 dəqiqəlik limitə sığır")


class VideolentOndeTest(unittest.TestCase):
    """Sahib 2026-11-20: «1-ci dərəcədə maraqlı hadisələr olan videoları olan mənbələr tap, onlara üstünlük ver»."""

    def test_first_degree_sources_are_known_checked_every_run_and_ranked_first(self):
        onde = xy.xm.VIDEOLENT_ONDE
        self.assertGreaterEqual(len(onde), 15)
        for h in onde:
            self.assertIn(h, xy.xm.ADLAR, f"{h}: hesab cədvəldədir")
            self.assertTrue(xy.xm.onde(h.lower()))
        self.assertFalse(xy.xm.onde("UMG"))
        reel_only = [h for h in onde if h in xy.xm.VIDEOLENT_HESABLAR]
        t0 = datetime.datetime(2026, 11, 20, tzinfo=datetime.timezone.utc)
        for k in range(5):
            part = xy.videolent_slice(t0 + datetime.timedelta(minutes=20 * k))
            self.assertTrue(set(reel_only) <= set(part), "birinci dərəcəli mənbələr hər işdə yoxlanır")
            self.assertEqual(len(part), len(set(part)), "hesab bir işdə iki dəfə soruşulmur")
            self.assertLessEqual(len(part), xy.VL_PER_RUN)
        self.assertIn("birinci dərəcəli", xy.REELS_PROMPT)
        self.assertIn("baxış", xy.REELS_PROMPT)
        src = (ROOT / ".github" / "scripts" / "x_yazici.py").read_text(encoding="utf-8")
        self.assertIn('key=lambda c: (not xm.onde(c["handle"]), -c["_score"])', src, "hər mövzuda əvvəl birinci dərəcəli, sonra çox baxılan")
        self.assertIn('int(post.get("views") or 0) // 100', src, "baxış sayı xala daxildir")


class SixtyFortyTest(unittest.TestCase):
    """Sahib 2026-11-22: «videoların 60%-i … hadisələr …, Təmir-tadilatdakı videolar bənzəri videolar (çox fərqli mövzularda) təşkil
    etsin. Mənası başa düşülməyən videolar olmasın»."""

    def setUp(self):
        xy.REEL_META.clear()
        self.addCleanup(xy.REEL_META.clear)

    def test_gemini_gives_class_and_caption_old_answers_still_work(self):
        from unittest import mock
        tamir = xy.candidate("TamirveTadilat", post(author={"screen_name": "TamirveTadilat"}, id="2123096874748186941"), set(), NOW)
        gs = xy.candidate("GalatasaraySK", post(id="2123096874748186942"), set(), NOW)
        answer = json.dumps([{"id": "2123096874748186941", "s": "usta", "c": "  Usta qırılmış plastik borunu   lehimlə bərpa edir  "},
                             {"id": "2123096874748186942", "s": "hadise", "c": "Qalatasaray futbolçuları yeni mövsümün ilk məşqində"},
                             {"id": "999", "s": "usta", "c": "Namizəd deyil"}], ensure_ascii=False)
        with mock.patch.dict(xy.os.environ, {"GEMINI_API_KEY": "k"}), mock.patch.object(xy, "ask_gemini", return_value=answer):
            self.assertEqual(xy.pick_reels([tamir, gs], 6), [tamir["id"], gs["id"]])
        self.assertEqual(xy.REEL_META[tamir["id"]], {"sinif": "u", "c": "Usta qırılmış plastik borunu lehimlə bərpa edir"})
        self.assertEqual(xy.REEL_META[gs["id"]]["sinif"], "h")
        with mock.patch.dict(xy.os.environ, {"GEMINI_API_KEY": "k"}), mock.patch.object(xy, "ask_gemini", return_value='["2123096874748186942"]'):
            self.assertEqual(xy.pick_reels([tamir, gs], 6), [gs["id"]], "köhnə biçim (yalnız id) də oxunur")
        for word in ("hadise", "usta", "60%", "40%", "Tamir & Tadilat", "xilasetmə", "yolsuzluq", "kadr arxası", "Ermənistan", "özünə qəsd"):
            self.assertIn(word, xy.REELS_PROMPT, word)
        self.assertIn('[{"id": "<id>"', xy.REELS_PROMPT.format(n=3, items="- x"), "JSON nümunəsi format-dan sağ çıxır")

    def test_caption_is_one_short_line(self):
        self.assertEqual(xy.izah('«Robot  itin\nyeni modeli»'), "Robot itin yeni modeli")
        long = xy.izah("söz " * 60)
        self.assertLessEqual(len(long), xy.xm.IZAH_LEN[1])
        self.assertTrue(long.endswith("…"))
        self.assertEqual(xy.izah(None), "")

    def test_each_run_takes_sixty_percent_events_forty_percent_craft(self):
        q = xy.xm.VIDEOLENT_QRUPLAR
        hs = [list(q[m])[:6] for m in ("tebiet", "elm", "texnika", "yemek", "kino", "maraqli")]
        ids, handle = [], {}
        for k, group in enumerate(hs):
            for j, h in enumerate(group):
                pid = f"{k}{j}"
                ids.append(pid)
                handle[pid] = h
                xy.REEL_META[pid] = {"sinif": "u" if j % 2 else "h"}
        got = xy.split_reels(ids, handle.get, 12)
        self.assertEqual(len(got), 12)
        self.assertEqual(sum(xy.REEL_META[i]["sinif"] == "u" for i in got), round(12 * xy.xm.USTA_PAY), "12-dən 5-i usta işi")
        self.assertEqual(xy.xm.USTA_PAY, 0.4)
        only_h = [i for i in ids if xy.REEL_META[i]["sinif"] == "h"]
        self.assertEqual(len(xy.split_reels(only_h, handle.get, 12)), 12, "usta işi çatmasa yer hadisə ilə dolur")
        self.assertEqual(xy.xm.sinif({"handle": "TamirveTadilat"}), "u", "Gemini sinif verməyibsə hesabın əsas sinfi")
        self.assertEqual(xy.xm.sinif({"handle": "CollinRugg"}), "h")

    def test_news_and_backstage_sources_exist_and_stay_apart_from_news_writing(self):
        q = xy.xm.VIDEOLENT_QRUPLAR
        self.assertIn("xeber", q)
        for h in ("CollinRugg", "FoxNews", "AP", "Breaking911", "EmmanuelMacron"):
            self.assertIn(h, q["xeber"])
            self.assertNotIn(h, xy.xm.HESABLAR, "bu hesablardan xəbər yazılmır, yalnız video")
        for h in ("ufc", "baykartech", "TUSAS_TR"):
            self.assertIn(h, xy.xm.VIDEOLENT_HESABLAR)
        src = (ROOT / ".github" / "scripts" / "x_yazici.py").read_text(encoding="utf-8")
        self.assertIn("split_reels(pick_reels(pool, REELS_PER_RUN * 3)", src)
        self.assertIn('if "c" in row and xm.izah_check(row["c"]) and not xm.forbidden_topic(row["c"])', src, "biçimi pis izah düşür, video qalır")
