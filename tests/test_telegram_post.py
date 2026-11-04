"""Telegram kanalı (.github/scripts/telegram_post.py): nə, nə vaxt və necə gedir."""
import datetime
import json
import pathlib
import re
import sys
import unittest
from unittest import mock

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / ".github" / "scripts"))
import telegram_post as tg  # noqa: E402

UTC = datetime.timezone.utc
NOON = datetime.datetime(2026, 11, 3, 8, 0, tzinfo=UTC)  # Bakı: 12:00


def ago(now, minutes):
    return (now - datetime.timedelta(minutes=minutes)).isoformat()


def story(n, title, now=NOON, minutes=10, sources=("APA", "Report", "Trend"), category="gundem"):
    hosts = {"APA": "apa.az", "Report": "report.az", "Trend": "trend.az", "Oxu.az": "oxu.az", "Qafqazinfo": "qafqazinfo.az"}
    main, *rest = sources
    return {"id": f"id{n}", "title": title, "summary": "", "category": category, "lang": "az", "source": main,
            "sourceUrl": f"https://{hosts[main]}/{n}", "publishedAt": ago(now, minutes),
            "alts": [{"source": s, "sourceUrl": f"https://{hosts[s]}/{n}", "publishedAt": ago(now, minutes + 1), "title": title}
                     for s in rest]}


class AlertTest(unittest.TestCase):
    def test_only_multi_source_fresh_stories_go(self):
        news = {"articles": [story(1, "Tək mənbəli xəbər", sources=("APA",)), story(2, "Bakıda yeni metro stansiyası açıldı")]}
        msg, state = tg.plan(news, {}, {}, NOON)
        self.assertIn("Bakıda yeni metro stansiyası açıldı", msg["text"])
        self.assertIn("və daha 2 mənbə", msg["text"])
        self.assertIn("https://8ulduz.az/?ref=tg#/xeber/id2?b=gundem", msg["text"])
        self.assertEqual(msg["link_preview_options"]["url"], "https://apa.az/2")
        self.assertFalse(msg["disable_notification"])
        self.assertIn(tg.url_key("https://report.az/2"), state["keys"])

    def test_nothing_twice_and_a_gap_between_posts(self):
        news = {"articles": [story(1, "Bakıda yeni metro stansiyası açıldı"), story(2, "Neftin qiyməti kəskin bahalaşdı")]}
        _msg, state = tg.plan(news, {}, {}, NOON)
        self.assertEqual(tg.plan(news, {}, state, NOON + datetime.timedelta(minutes=5)), (None, None))
        later = NOON + datetime.timedelta(minutes=21)
        news = {"articles": [story(1, "Bakıda yeni metro stansiyası açıldı", now=later), story(2, "Neftin qiyməti kəskin bahalaşdı", now=later)]}
        msg, state = tg.plan(news, {}, state, later)
        self.assertIn("Neftin", msg["text"])
        self.assertEqual(tg.plan(news, {}, state, later + datetime.timedelta(minutes=30)), (None, None))

    def test_regrouped_story_or_same_topic_is_not_repeated(self):
        _msg, state = tg.plan({"articles": [story(1, "Bakıda yeni metro stansiyası açıldı")]}, {}, {}, NOON)
        later = NOON + datetime.timedelta(minutes=40)
        regrouped = story(9, "Metro stansiyası açıldı", now=later, sources=("Report", "APA", "Oxu.az"))
        regrouped["alts"][0]["sourceUrl"] = "https://apa.az/1"
        same_topic = story(8, "Bakıda yeni metro stansiyası açıldı — fotolar", now=later, sources=("Oxu.az", "Trend", "Qafqazinfo"))
        self.assertEqual(tg.plan({"articles": [regrouped, same_topic]}, {}, state, later), (None, None))

    def test_old_stories_and_president_section_stay_off(self):
        old = story(1, "Dünənki hadisə", minutes=3 * 60)
        pres = story(2, "Prezident qəbul etdi", category="prezident")
        self.assertEqual(tg.plan({"articles": [old, pres]}, {}, {}, NOON), (None, None))

    def test_night_needs_many_sources_and_is_silent(self):
        night = datetime.datetime(2026, 11, 2, 22, 0, tzinfo=UTC)  # Bakı: 02:00
        news = {"articles": [story(1, "Gecə yanğın baş verdi", now=night)]}
        self.assertEqual(tg.plan(news, {}, {}, night), (None, None))
        many = story(2, "Güclü zəlzələ oldu", now=night, sources=("APA", "Report", "Trend", "Oxu.az", "Qafqazinfo"))
        with mock.patch.object(tg, "NIGHT_SOURCES", 5):
            msg, _state = tg.plan({"articles": [many]}, {}, {}, night)
        self.assertTrue(msg["disable_notification"])

    def test_text_is_escaped(self):
        msg, _ = tg.plan({"articles": [story(1, "<b>Başlıq</b> & «sitat»")]}, {}, {}, NOON)
        self.assertIn("&lt;b&gt;Başlıq&lt;/b&gt; &amp; «sitat»", msg["text"])


class RedLineTest(unittest.TestCase):
    def test_policy_runs_again_before_posting(self):
        bad = story(1, "Azərbaycan haqqında xarici xəbər", sources=("APA", "Report", "Trend"))
        bad["source"], bad["sourceUrl"] = "BBC", "https://bbc.com/1"
        self.assertEqual(tg.plan({"articles": [bad]}, {}, {}, NOON), (None, None))
        stranger = story(2, "Qeydiyyatsız sayt", sources=("APA", "Report", "Trend"))
        stranger["source"], stranger["sourceUrl"] = "APA", "https://example.com/2"
        self.assertEqual(tg.plan({"articles": [stranger]}, {}, {}, NOON), (None, None))

    def test_pipeline_keeps_the_channel_apart_from_the_news_flow(self):
        pipeline = (ROOT / ".github" / "scripts" / "pipeline.sh").read_text(encoding="utf-8")
        start = pipeline.split("# --------------------------------------------------------------------- başlanğıc")[1]
        self.assertIn('if [ -n "${TELEGRAM_BOT_TOKEN:-}" ] && [ -n "${TELEGRAM_CHAT:-}" ]; then\n  tg_loop &', start)
        self.assertNotIn("tg_round", pipeline.split("while :; do\n  began=$SECONDS\n  touch")[1])
        self.assertIn("-u TELEGRAM_BOT_TOKEN", pipeline.split("py_t() {")[1].split("\n")[0])
        self.assertIn("--force-with-lease", pipeline.split("tg_round() {")[1].split("\n}\n")[0])
        round_ = pipeline.split("tg_round() {")[1].split("\n}\n")[0]
        self.assertLess(round_.index("push -q --force-with-lease"), round_.index(" send "))

    def test_every_code_file_is_in_the_last_good_cache_key(self):
        # Açarda olmayan fayl keşə heç vaxt düşmür: hər iş «kod dəyişib» sanır, sürətli dövrə xətada boş yerə ikinci cəhd edir.
        pipeline = (ROOT / ".github" / "scripts" / "pipeline.sh").read_text(encoding="utf-8")
        workflow = (ROOT / ".github" / "workflows" / "update.yml").read_text(encoding="utf-8")
        files = re.search(r'^CODE_FILES="([^"]+)"', pipeline, re.M).group(1).split()
        restore = re.search(r"key: updater-lkg2-\$\{\{ hashFiles\(([^)]*)\)", workflow).group(1)
        save = re.findall(r"key: updater-lkg2-\$\{\{ hashFiles\(([^)]*)\)", workflow)[1]
        for f in files:
            self.assertIn(f"'{f}'", restore)
            self.assertIn(f"'.lkg/{f}'", save)


class DigestTest(unittest.TestCase):
    MARKETS = {"items": [{"id": "USD", "label": "Dollar", "value": 1.7, "src": "AMB"},
                         {"id": "EUR", "label": "Avro", "value": 1.9763, "src": "AMB"}]}

    def news(self, now):
        titles = ["Bakıda yeni metro stansiyası açıldı", "Neftin qiyməti kəskin bahalaşdı", "Qarabağ Avropada qalib gəldi",
                  "Pensiyalar yanvardan artırılacaq", "Gəncədə yeni xəstəxana tikilir", "Bölgələrdə qar yağdı"]
        return {"articles": [story(i, t, now=now, minutes=60 + i * 30, sources=("APA",) if i == 5 else ("APA", "Report"))
                             for i, t in enumerate(titles)]}

    def test_morning_digest_once_a_day_with_rates(self):
        morning = datetime.datetime(2026, 11, 3, 4, 45, tzinfo=UTC)  # Bakı: 08:45
        msg, state = tg.plan(self.news(morning), self.MARKETS, {}, morning)
        self.assertTrue(msg["text"].startswith("<b>Səhər xülasəsi — 3 noyabr</b>"))
        self.assertEqual(msg["text"].count("\n1. "), 1)
        self.assertIn("\n5. ", msg["text"])
        self.assertIn("Dollar 1.7000 · Avro 1.9763 AZN (AMB)", msg["text"])
        self.assertTrue(msg["link_preview_options"]["is_disabled"])
        self.assertEqual(state["digests"]["morning"], "2026-11-03")
        msg, _ = tg.plan(self.news(morning), self.MARKETS, state, morning + datetime.timedelta(minutes=10))
        self.assertIsNone(msg)

    def test_late_digest_is_skipped_and_evening_has_no_rates(self):
        late = datetime.datetime(2026, 11, 3, 6, 15, tzinfo=UTC)  # Bakı: 10:15
        msg, _ = tg.plan(self.news(late), self.MARKETS, {}, late)
        self.assertIsNone(msg)
        evening = datetime.datetime(2026, 11, 3, 17, 5, tzinfo=UTC)  # Bakı: 21:05
        msg, _ = tg.plan(self.news(evening), self.MARKETS, {}, evening)
        self.assertTrue(msg["text"].startswith("<b>Günün yekunu — 3 noyabr</b>"))
        self.assertNotIn("AZN", msg["text"])

    def test_thin_day_skips_the_digest_but_records_it(self):
        morning = datetime.datetime(2026, 11, 3, 4, 45, tzinfo=UTC)
        msg, state = tg.plan({"articles": [story(1, "Tək xəbər", now=morning, sources=("APA",))]}, {}, {}, morning)
        self.assertIsNone(msg)
        self.assertEqual(state["digests"]["morning"], "2026-11-03")


class CommandTest(unittest.TestCase):
    def test_plan_writes_files_and_says_when_nothing_is_due(self):
        import tempfile
        with tempfile.TemporaryDirectory() as d:
            p = pathlib.Path(d)
            (p / "news.json").write_text(json.dumps({"articles": []}), encoding="utf-8")
            args = ["x", "plan", str(p / "news.json"), str(p / "none.json"), str(p / "old.json"), str(p / "new.json"), str(p / "msg.json")]
            with mock.patch.object(tg, "due_digest", return_value=None):
                self.assertEqual(tg.main(args), 1)
            self.assertFalse((p / "new.json").exists())

    def test_send_without_secrets_does_nothing(self):
        with mock.patch.dict("os.environ", {"TELEGRAM_BOT_TOKEN": "", "TELEGRAM_CHAT": ""}):
            self.assertEqual(tg.main(["x", "send", "/yoxdur.json"]), 0)


if __name__ == "__main__":
    unittest.main()
