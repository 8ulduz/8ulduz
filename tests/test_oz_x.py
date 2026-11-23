"""X-dən videolu xəbərlər (oz_x.py): növbə faylının qapıları (qırmızı xətt 2 və 4), video sətri və səhifəsi, dərc hissəsi ilə
uyğunluq. Şəbəkə yoxdur: modul yalnız fayl oxuyur. Repodakı növbə faylının (oz_x.json) hər sətri də burada yoxlanır."""
import datetime
import html
import json
import pathlib
import tempfile
import unittest
import unittest.mock

import oz_derc as d
import oz_xeber as ox
import oz_x as xm

ROOT = pathlib.Path(__file__).resolve().parent.parent
BAKU = ox.BAKU
ON = {"OZ_DERC": "1"}
VIDEO = "https://video.twimg.com/amplify_video/2113713055204831233/vid/avc1/720x1280/F4uJ5K30z0ONv8ck.mp4?tag=29"
POSTER = "https://pbs.twimg.com/amplify_video_thumb/2113713055204831233/img/dHETMcQ37j8Te88z.jpg"


def at(day, h=12, m=0):
    return datetime.datetime(2026, 11, day, h, m, tzinfo=BAKU)


def no_net(url, **kw):
    raise OSError("şəbəkə yoxdur")


def row(**kw):
    base = {"id": "2113713074157164306", "date": "2026-11-19", "slot": "14:10", "kind": "x-idman",
            "title": "Qalatasaray məşqində yeni transferlər ilk dəfə topa toxunub",
            "lead": "Qalatasarayın yeni transferləri komandanın məşqinə ilk dəfə qatılıb. Klub məşqdən 2 dəqiqəlik video paylaşıb.",
            "body": ["Məşq 3 qrupda keçib, futbolçular sonda kiçik meydanda oynayıblar."],
            "handle": "GalatasaraySK", "post": "https://x.com/GalatasaraySK/status/2113713074157164306",
            "video": VIDEO, "poster": POSTER, "w": 720, "h": 1280,
            "src": ["Yeni transferlerimiz ilk antrenmanına çıktı. 3 grup halinde yapılan çalışmanın 2 dakikalık özeti."]}
    base.update(kw)
    return base


class Tmp(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.tmp = pathlib.Path(tmp.name)

    def queue(self, rows, v=1, name="novbe.json"):
        path = self.tmp / name
        path.write_text(json.dumps({"v": v, "items": rows}, ensure_ascii=False), encoding="utf-8")
        return path


class CheckTest(unittest.TestCase):
    def test_good_row_passes(self):
        self.assertIsNone(xm.check(row()))
        self.assertIsNone(xm.check(row(handle="galatasaraysk")), "hesab adı böyük-kiçik hərfə həssas deyil")

    def test_account_post_and_media_must_be_the_known_forms(self):
        cases = {
            "hesab cədvəldə yoxdur": [row(handle="thshaber", post="https://x.com/thshaber/status/2113713074157164306")],
            "post ünvanı": [row(post="https://x.com/Fenerbahce/status/2113713074157164306"),
                            row(post="https://x.com/GalatasaraySK/status/2113713074157164307"),
                            row(post="https://twitter.com/GalatasaraySK/status/2113713074157164306"),
                            row(post="https://x.com/GalatasaraySK/status/2113713074157164306?s=20")],
            "video ünvanı": [row(video="https://video.twimg.com/a/b.m3u8"), row(video="http://video.twimg.com/a/b.mp4"),
                             row(video="https://evil.example/video.twimg.com/a.mp4"), row(video='https://video.twimg.com/a"onerror=x.mp4'),
                             row(video="https://video.twimg.com:8443/a/b.mp4"), row(video="")],
            "poster ünvanı": [row(poster="https://example.org/a.jpg"), row(poster="https://pbs.twimg.com/a b.jpg")],
            "w və h": [row(w=0), row(h=99999), row(w="720"), row(h=True)],
            "id yararsızdır": [row(id="abc"), row(id="0123456")],
        }
        for want, rows in cases.items():
            for r in rows:
                why = xm.check(r)
                self.assertIsNotNone(why, r)
                self.assertIn(want, why, r)

    def test_red_line_azerbaijan_topic_from_a_foreign_account_is_dropped(self):
        for kw in ({"src": ["Is your nation competing in Baku? Karabağ maçı öncesi son antrenman."]},
                   {"src": ["Azerbaycan Cumhurbaşkanı Aliyev ile görüştü, 2 ülke anlaştı."]},
                   {"body": ["Komanda Bakıda 3 qrupda məşq edib, sonda kiçik meydanda oynayıb."]},
                   {"lead": "Qalatasarayın yeni transferləri Azərbaycandan gələn qonaqlarla 2 dəqiqəlik məşq keçib."}):
            self.assertEqual(xm.check(row(**kw)), "xarici mənbə, Azərbaycan mövzusu", kw)

    def test_text_gates_of_the_world_queue_apply(self):
        self.assertIn("rəqəm", xm.check(row(body=["Məşq 4 qrupda keçib, futbolçular sonda kiçik meydanda oynayıblar."])))
        self.assertIn("nisbi gün", xm.check(row(body=["Məşq bu gün 3 qrupda keçib, futbolçular sonda kiçik meydanda oynayıb."])))
        self.assertIn("nida", xm.check(row(body=["Məşq 3 qrupda keçib! Futbolçular sonda kiçik meydanda oynayıblar."])))
        self.assertIn("nöqtə", xm.check(row(title="Qalatasaray məşqində yeni transferlər ilk dəfə topa toxunub!")))
        self.assertIn("başlığın", xm.check(row(title="Qısa")))
        self.assertIn("mətn 1–4", xm.check(row(body=["Məşq 3 qrupda keçib və futbolçular sonda oynayıb."] * 5)))
        self.assertIn("src", xm.check(row(src=[])))
        self.assertIn("slot", xm.check(row(slot="06:59")))
        self.assertIn("növ", xm.check(row(kind="dunya-kosmos")))


class ItemsTest(Tmp):
    def test_item_carries_video_poster_size_and_credit(self):
        path = self.queue([row()])
        got = xm.items(ROOT, at(19), path=path)
        self.assertEqual(len(got), 1)
        it = got[0]
        self.assertTrue(it["worth"])
        self.assertEqual(it["key"], "x-2113713074157164306")
        self.assertEqual((it["video"], it["image"], it["vw"], it["vh"]), (VIDEO, POSTER, "720", "1280"))
        self.assertEqual(it["credit"], "Qalatasaray (X, @GalatasaraySK)")
        self.assertEqual(it["link"], "https://x.com/GalatasaraySK/status/2113713074157164306")
        self.assertEqual(it["topic"], "video")
        self.assertEqual(xm.items(ROOT, at(21), path=path), [], "pəncərədən sonra qayıtmır")
        self.assertEqual(xm.items(ROOT, at(19), done={"x-2113713074157164306"}, path=path), [])

    def test_rejected_and_duplicate_rows(self):
        path = self.queue([row(handle="thshaber"), row(id="2113713074157164399", post="https://x.com/GalatasaraySK/status/2113713074157164399"),
                           row(id="2113713074157164399", post="https://x.com/GalatasaraySK/status/2113713074157164399")])
        got = xm.items(ROOT, at(19), path=path)
        self.assertEqual([g["worth"] for g in got], [False, True])
        self.assertIn("hesab", got[0]["why"])

    def test_row_and_page_play_the_video_without_a_referrer(self):
        it = xm.items(ROOT, at(19), path=self.queue([row()]))[0]
        r = d.row(it, at(19, 14, 10))
        self.assertTrue(r["video"])
        self.assertEqual(r["xv"], {"u": VIDEO, "w": 720, "h": 1280})
        self.assertEqual(r["imageUrl"], POSTER)
        self.assertEqual(r["category"], "idman")
        p = d.page(it, r)
        self.assertIn('<meta name="referrer" content="no-referrer" />', p)
        self.assertIn(f'<video controls playsinline preload="none" width="720" height="1280" src="{html.escape(VIDEO, quote=True)}" poster="{POSTER}"></video>', p)
        self.assertNotIn("<img", p)
        self.assertEqual(p.count("<script"), 1, "X skripti yoxdur, yalnız JSON-LD")
        self.assertIn('Mənbə: <a href="https://x.com/GalatasaraySK/status/2113713074157164306" rel="noopener">Qalatasaray (X, @GalatasaraySK)</a>', p)

    def test_rows_without_a_safe_video_stay_plain(self):
        base = {"key": "k", "title": "Başlıq", "lead": "Giriş.", "body": ["Mətn."], "topic": "idman", "credit": "c", "link": "https://example.org/"}
        for bad in ({"video": "https://example.org/a.mp4", "vw": "720", "vh": "1280"}, {"video": VIDEO, "vw": "x", "vh": "1"},
                    {"video": VIDEO, "vw": "720", "vh": "99999"}, {"video": VIDEO.replace("?tag", '"?tag'), "vw": "720", "vh": "1280"}, {}):
            r = d.row({**base, **bad}, at(19))
            self.assertFalse(r["video"], bad)
            self.assertNotIn("xv", r)
            self.assertNotIn('name="referrer"', d.page({**base, **bad}, r))

    def test_publisher_cycle_keeps_the_video_fields(self):
        q = self.queue([row()])
        orig = xm.NOVBE
        xm.NOVBE = q
        try:
            res = d.cycle(self.tmp, at(19, 14, 15), fetch=no_net, env=ON, mods=[("oz_x", xm)])
        finally:
            xm.NOVBE = orig
        self.assertEqual((res["errors"], res["blocked"]), ([], []))
        self.assertEqual([p["title"] for p in res["published"]], [row()["title"]])
        rows = json.loads((self.tmp / "data" / "oz" / "xeberler.json").read_text(encoding="utf-8"))["articles"]
        self.assertEqual(rows[0]["xv"]["u"], VIDEO)
        page = (self.tmp / "xeber" / rows[0]["id"] / "index.html").read_text(encoding="utf-8")
        self.assertIn("<video ", page)


class RepoQueueTest(unittest.TestCase):
    def test_every_row_in_the_repo_queue_passes_its_gates(self):
        doc = json.loads((ROOT / "oz_x.json").read_text(encoding="utf-8"))
        self.assertEqual(doc.get("v"), 1)
        for r, why in xm.rows():
            self.assertIsNone(why, r.get("id"))


class TablesTest(unittest.TestCase):
    def test_module_is_in_the_publisher_tables(self):
        self.assertIn("oz_x", [n for n, _ in ox.FAZA3])
        self.assertIn("oz_x", d.modules())
        self.assertEqual(d.QAYDA["oz_x"], {"done": "hamisi", "gelecek": "vaxtinda", "sorgu": 0})
        self.assertEqual(d.MOVZU_HEDD["video"], (8, 8))
        want = {"x-idman": "idman", "x-dunya": "dunya", "x-elm": "tehsil", "x-maraqli": "dunya", "x-transfer": "idman"}   # x-transfer: sahib 2026-11-19
        self.assertEqual({k: d.category({"kind": k, "topic": t}) for k, t in xm.NOVLER.items()}, want)
        sh = (ROOT / ".github" / "scripts" / "pipeline.sh").read_text(encoding="utf-8")
        line = [l for l in sh.splitlines() if "oz_x.py" in l]
        self.assertEqual(len(line), 1)
        self.assertTrue(line[0].startswith("CODE_FILES=") and "oz_x.py oz_x.json" in line[0], "modul və növbə faylı birlikdə köçürülür")
        self.assertEqual(xm.NOVBE, ROOT / "oz_x.json")

    def test_module_sends_no_requests_and_lists_only_primary_accounts(self):
        src = (ROOT / "oz_x.py").read_text(encoding="utf-8")
        self.assertNotIn("urlopen", src)
        self.assertNotIn("fetch(", src)
        calls = []
        xm.items(ROOT, at(19), fetch=lambda *a, **k: calls.append(a))
        self.assertEqual(calls, [])
        self.assertNotIn("thshaber", {h.lower() for h in xm.HESABLAR}, "başqasının videosunu paylaşan hesab yoxdur")



CAP = "Usta plastik borulardan rəf düzəldir"


def media(when, n=0):
    """X videosunun ünvanı: media nömrəsi «when» vaxtında yüklənmiş kimi (snowflake)."""
    mid = ((int(when.timestamp() * 1000) - 1288834974657) << 22) + n
    return f"https://video.twimg.com/amplify_video/{mid}/vid/avc1/720x1280/F4uJ5K30z0ONv8ck.mp4?tag=29"


def reel(**kw):
    base = {"id": "2123096874748186946", "handle": "TamirveTadilat", "post": "https://x.com/TamirveTadilat/status/2123096874748186946",
            "video": VIDEO, "poster": POSTER, "w": 720, "h": 1280, "at": "2026-11-19T08:00:00+00:00",
            "src": ["Pvc borulardan yapabilecekleriniz sınırlı değildir."], "c": CAP}
    base.update(kw)
    return base


def event(n, when, **kw):
    """Hadisə videosu (FoxNews): n — paylaşımın sıra nömrəsi, when — paylaşımın və videonun vaxtı."""
    pid = str(2123096874748186000 + n)
    return reel(id=pid, handle="FoxNews", post=f"https://x.com/FoxNews/status/{pid}", video=media(when, n), at=when.isoformat(),
                src=["Storm hits the coast, thousands without power."], c="Sahilə güclü fırtına çatıb, minlərlə ev işıqsız qalıb", **kw)


class ReelsTest(unittest.TestCase):
    """Qısa videolar (sahib, 2026-11-19): yazısız video lenti. Qırmızı xətt 2: Azərbaycan mövzusu düşür."""
    NOW = datetime.datetime(2026, 11, 19, 10, 0, tzinfo=datetime.timezone.utc)

    def write(self, rows):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        path = pathlib.Path(tmp.name) / "oz_x.json"
        path.write_text(json.dumps({"v": 1, "items": [], "reels": rows}), encoding="utf-8")
        return path

    def test_good_reel_and_gates(self):
        self.assertIsNone(xm.reel_check(reel()))
        bad = {"hesab": reel(handle="thshaber", post="https://x.com/thshaber/status/2123096874748186946"),
               "post": reel(post="https://x.com/TamirveTadilat/status/1"),
               "video": reel(video="https://evil.example/a.mp4"), "poster": reel(poster="https://evil.example/a.jpg"),
               "ölçü": reel(w=True), "vaxt": reel(at="2026-11-19 08:00"),
               "Azərbaycan": reel(src=["Bakü'de çekilen görüntüler"]), "Azərbaycan 2": reel(src=["Azerbaijan team arrives"])}
        for name, row in bad.items():
            self.assertIsNotNone(xm.reel_check(row), name)

    def test_reels_output_is_text_free_newest_first_and_recent(self):
        rows = [reel(), reel(id="2123096874748186947", post="https://x.com/TamirveTadilat/status/2123096874748186947", at="2026-11-19T09:00:00+00:00"),
                reel(id="2123096874748186948", post="https://x.com/TamirveTadilat/status/2123096874748186948", at="2026-11-10T09:00:00+00:00"),
                reel(id="2123096874748186949", post="https://x.com/TamirveTadilat/status/2123096874748186949", src=["Karabağ maçı"]), reel()]
        rows[1]["video"] = VIDEO.replace("2113713055204831233", "2113713055204831234")   # başqa video: açar media nömrəsidir
        out = xm.reels(self.NOW, path=self.write(rows))
        self.assertEqual([r["id"] for r in out], ["2123096874748186947", "2123096874748186946"], "köhnə, Azərbaycan mövzulu və təkrar düşür")
        self.assertEqual(set(out[0]), {"id", "a", "n", "m", "u", "i", "w", "h", "t", "q", "c"}, "mətn (src) sayta çıxmır; m: mövzu, q: sinif, c: izah")
        self.assertEqual(out[0]["n"], "Tamir & Tadilat")

    def test_first_degree_sources_are_marked_in_the_reels(self):
        """Sahib 2026-11-20: birinci dərəcəli maraqlı hadisə mənbələri lentdə «p» ilə (lent.js hər mövzuda əvvəl göstərir)."""
        row = reel(id="2123096874748186950", handle="TheFigen_", post="https://x.com/TheFigen_/status/2123096874748186950", src=["Silky smooth turn."],
                   video=media(self.NOW - datetime.timedelta(hours=3)), c="Sürücü dar döngəni maşınla hamar keçir")
        out = {r["id"]: r for r in xm.reels(self.NOW, path=self.write([reel(), row]))}
        self.assertEqual(out["2123096874748186950"].get("p"), 1)
        self.assertNotIn("p", out["2123096874748186946"])

    def test_class_and_caption_reach_the_site_azerbaijan_and_armenia_never(self):
        """Sahib 2026-11-22: 60% hadisə, 40% usta işi; «mənası başa düşülməyən videolar olmasın» — qısa izah."""
        cap = reel(id="2123096874748186951", post="https://x.com/TamirveTadilat/status/2123096874748186951", sinif="u",
                   c="Usta qırılmış plastik borunu lehimlə bərpa edir")
        old = reel(id="2123096874748186952", post="https://x.com/TamirveTadilat/status/2123096874748186952",
                   video=media(self.NOW - datetime.timedelta(days=40)))
        out = {r["id"]: r for r in xm.reels(self.NOW, path=self.write([cap, old]))}
        self.assertEqual(out["2123096874748186951"]["c"], "Usta qırılmış plastik borunu lehimlə bərpa edir")
        self.assertEqual(out["2123096874748186951"]["q"], "u")
        self.assertEqual(out["2123096874748186952"]["q"], "u", "sinifsiz köhnə sətir: hesabın əsas sinfi; usta işinin videosu köhnə ola bilər")
        self.assertNotIn("src", out["2123096874748186951"], "paylaşımın mətni sayta çıxmır")
        bad = {"Azərbaycan izahda": reel(c="Bakıda çəkilmiş maraqlı görüntülər"),
               "Ermənistan izahda": reel(c="Yerevanda keçirilən paraddan görüntülər"),
               "Ermənistan mətndə": reel(src=["Armenian army parade footage"]),
               "qısa izah": reel(c="Bax"), "keçid": reel(c="Ətraflı: https://example.com/a burada"),
               "sinif": reel(sinif="x")}
        for name, row in bad.items():
            self.assertIsNotNone(xm.reel_check(row), name)
        self.assertIsNone(xm.reel_check(reel(sinif="h", c="Yeni elektromobil ilk dəfə yolda sınaqdan keçirilir")))

    def test_news_videos_without_a_caption_stay_off_the_site(self):
        """Sahib 2026-11-22: «mənası başa düşülməyən videolar olmasın» — xəbər videosu izahsız lentə çıxmır."""
        fresh = self.NOW - datetime.timedelta(hours=2)
        bare = event(53, fresh)
        bare.pop("c")
        ids = [r["id"] for r in xm.reels(self.NOW, path=self.write([bare, event(54, fresh)]))]
        self.assertEqual(ids, ["2123096874748186054"])

    def test_every_video_has_a_caption(self):
        """Sahib 2026-11-22: hər videoya izah. 2026-11-23: Gemini kvotası bitəndə yazıcı izahsız idman videoları yığırdı və lentin ilk
        10 videosunun 7-si izahsız idi — izahsız video heç bir mövzuda sayta çıxmır."""
        for h in ("GalatasaraySK", "LFC", "Rainmaker1973", "TamirveTadilat"):
            row = reel(id="2123096874748186960", handle=h, post=f"https://x.com/{h}/status/2123096874748186960",
                       video=media(self.NOW - datetime.timedelta(hours=1)), at=(self.NOW - datetime.timedelta(hours=1)).isoformat())
            row.pop("c")
            self.assertEqual(xm.reels(self.NOW, path=self.write([row])), [], h)

    def test_an_old_clip_reposted_today_is_not_a_fresh_event(self):
        """Sahib 2026-11-22: «həm yeni, həm maraqlı hadisələr». X media nömrəsi videonun yüklənmə vaxtıdır: 2026-11-23 lentində
        videoların 9%-i illər əvvəlki klipin təzə paylaşımı idi (wonderofscience, 2022-07-13). Usta işinə bu hədd yoxdur."""
        now, today = self.NOW, (self.NOW - datetime.timedelta(hours=1)).isoformat()
        self.assertEqual(xm.video_at(media(now - datetime.timedelta(days=2))).date(), (now - datetime.timedelta(days=2)).date())
        old_event = event(61, now - datetime.timedelta(hours=1))
        old_event["video"] = media(now - datetime.timedelta(days=xm.REEL_VIDEO_DAYS, hours=1), 61)
        new_event = event(62, now - datetime.timedelta(hours=1))
        old_craft = reel(id="2123096874748186063", post="https://x.com/TamirveTadilat/status/2123096874748186063", at=today,
                         video=media(now - datetime.timedelta(days=400), 63))
        ids = [r["id"] for r in xm.reels(now, path=self.write([old_event, new_event, old_craft]))]
        self.assertEqual(sorted(ids), ["2123096874748186062", "2123096874748186063"])
        self.assertGreaterEqual(xm.REEL_VIDEO_DAYS, 1)
        self.assertLessEqual(xm.REEL_VIDEO_DAYS, xm.REELS_DAYS)

    def test_the_same_video_in_two_posts_or_sizes_is_one_video(self):
        """2026-11-23: lentdə 32 video iki dəfə idi (eyni media başqa paylaşımda). Açar media nömrəsidir (lent.js vkey ilə eyni)."""
        when = self.NOW - datetime.timedelta(hours=2)
        a, b = event(71, when), event(72, when + datetime.timedelta(minutes=5))
        b["video"] = a["video"].replace("720x1280", "480x852").replace("?tag=29", "?tag=12")
        self.assertEqual(xm.video_key(a["video"]), xm.video_key(b["video"]))
        self.assertEqual([r["id"] for r in xm.reels(self.NOW, path=self.write([a, b]))], ["2123096874748186072"], "ən təzə paylaşım qalır")
        self.assertEqual(xm.video_key("https://video.twimg.com/a/vid/1.mp4?tag=1"), "https://video.twimg.com/a/vid/1.mp4")

    def test_craft_is_forty_percent_of_the_feed_when_there_is_enough(self):
        """Sahib 2026-11-22: 60% hadisə, 40% usta işi. 2026-11-23: lentin 1000 videosunun 109-u (11%) usta işi idi — fayl ən təzə 1000
        videonu götürürdü, usta işi isə az gəlir. İndi usta işi bütün həftədən, hadisə ən təzəsindən."""
        now = self.NOW
        events = [event(i, now - datetime.timedelta(minutes=i)) for i in range(1, 1301)]
        crafts = [reel(id=str(2123096874748190000 + i), post=f"https://x.com/TamirveTadilat/status/{2123096874748190000 + i}",
                       at=(now - datetime.timedelta(hours=12 + i)).isoformat(), video=media(now - datetime.timedelta(days=30), 9000 + i)) for i in range(150)]
        out = xm.reels(now, path=self.write(events + crafts))
        self.assertEqual(len(out), xm.REELS_MAX)
        self.assertEqual(sum(r["q"] == "u" for r in out), 150, "az olan usta işinin hamısı qalır, 2 gündən köhnə olsa da")
        many = crafts + [reel(id=str(2123096874748195000 + i), post=f"https://x.com/TamirveTadilat/status/{2123096874748195000 + i}",
                              at=(now - datetime.timedelta(hours=1, minutes=i)).isoformat(), video=media(now, 20000 + i)) for i in range(600)]
        out = xm.reels(now, path=self.write(events + many))
        self.assertEqual(sum(r["q"] == "u" for r in out), round(xm.REELS_MAX * xm.USTA_PAY), "çox olanda 40%")
        self.assertEqual([r["t"] for r in out], sorted((r["t"] for r in out), reverse=True), "ən yenisi əvvəl")
        self.assertEqual(len(xm.reels(now, path=self.write(crafts))), 150, "hadisə yoxdursa usta işi tək qalır")

    def test_the_queue_keeps_craft_for_the_whole_week_and_drops_uncaptioned_rows(self):
        """x_yazici növbə faylını keep_reels ilə kəsir: əvvəl son 1000 sətir qalırdı və usta işi 2 günə silinirdi."""
        now = self.NOW
        events = [event(i, now - datetime.timedelta(minutes=i)) for i in range(1, 1501)]
        craft = reel(id="2123096874748199999", post="https://x.com/TamirveTadilat/status/2123096874748199999",
                     at=(now - datetime.timedelta(days=6)).isoformat())
        bare = event(1501, now)
        bare.pop("c")
        old = event(1502, now - datetime.timedelta(days=xm.REELS_DAYS, hours=1))
        kept = xm.keep_reels([craft, old, bare] + events, now)
        self.assertIn(craft, kept, "6 günlük usta işi qalır")
        self.assertNotIn(bare, kept, "izahsız sətir saxlanmır: paylaşım yenə namizəd olur")
        self.assertNotIn(old, kept)
        self.assertEqual(len(kept), xm.REELS_KEEP)
        self.assertEqual(kept[0], craft, "sıra qorunur")
        self.assertEqual(kept[1:], events[:xm.REELS_KEEP - 1], "ən köhnə hadisələr düşür")

    def test_updater_writes_reels_through_the_policy_gate(self):
        import updater
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        out_dir = pathlib.Path(tmp.name)
        path = self.write([reel(at=datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds"))])
        orig = xm.NOVBE
        try:
            xm.NOVBE = path
            with unittest.mock.patch.object(updater, "ROOT", out_dir), unittest.mock.patch.object(updater.content_policy, "enforce", wraps=updater.content_policy.enforce) as gate:
                updater.write_reels(xm.reels(datetime.datetime.now(datetime.timezone.utc)))
            self.assertTrue(gate.called, "qırmızı xətt 2: sətirlər content_policy.enforce-dan keçir")
        finally:
            xm.NOVBE = orig
        doc = json.loads((out_dir / "data" / "reels.json").read_text(encoding="utf-8"))
        self.assertEqual([r["id"] for r in doc["items"]], ["2123096874748186946"])

    def test_repo_reels_are_valid(self):
        for row in xm.load_reels():
            self.assertIsNone(xm.reel_check(row), row.get("id"))



def transfer_row(**kw):
    base = {"id": "2123096874748186950", "date": "2026-11-19", "slot": "15:10", "kind": "x-transfer",
            "title": "Transfer: Real Madrid Çuameni ilə müqaviləni 2030-cu ilədək uzadıb",
            "lead": "Fabrizio Romano-nun məlumatına görə, Real Madrid Orelyen Çuameni ilə yeni uzunmüddətli müqavilə imzalayıb.",
            "body": ["Bildirilir ki, yeni müqavilə 2030-cu ilin iyununadək qüvvədə olacaq."],
            "handle": "FabrizioRomano", "post": "https://x.com/FabrizioRomano/status/2123096874748186950",
            "src": ["Aurelien Tchouameni has signed new long term deal at Real Madrid until June 2030."]}
    base.update(kw)
    return base


class TransferTest(unittest.TestCase):
    """Sahib, 2026-11-19: X-in transfer xəbərləri (Romano, Moretto …) Transfer bölməsinə: videosuz, başlıqda «transfer»."""

    def test_text_only_transfer_row_is_valid_and_lands_in_sport(self):
        self.assertIsNone(xm.check(transfer_row()))
        self.assertIsNone(xm.check(transfer_row(poster=POSTER)), "şəkil varsa pbs.twimg.com")
        it = xm.item(transfer_row(), at(19).date())
        self.assertEqual((it["video"], it["image"], it["topic"]), ("", "", "transfer"))
        self.assertIn("x-transfer", d.BOLME_NOV)
        self.assertEqual(d.BOLME_NOV["x-transfer"], "idman")
        self.assertIn("transfer", d.MOVZU_HEDD)

    def test_gates(self):
        bad = {"başlıqda transfer yoxdur": transfer_row(title="Real Madrid Çuameni ilə müqaviləni 2030-cu ilədək uzadıb"),
               "yad şəkil": transfer_row(poster="https://evil.example/a.jpg"),
               "Azərbaycan mövzusu": transfer_row(src=["Qarabağ signs a new striker until June 2030."]),
               "mənbədə olmayan rəqəm": transfer_row(body=["Bildirilir ki, müqavilə 2031-ci ilədək qüvvədə olacaq."]),
               "video hesabı videosuz": transfer_row(kind="x-idman")}
        for name, r in bad.items():
            self.assertIsNotNone(xm.check(r), name)
        self.assertEqual(xm.credit("FabrizioRomano"), "Fabrizio Romano (X, @FabrizioRomano)")


if __name__ == "__main__":
    unittest.main()
