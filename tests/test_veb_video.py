"""Öz videolarımızın veb nüsxəsi (sahib, 2026-11-25: «video xəbərlərdə bəzi videolar (əsasən azərbaycan) 1-2 saniyəyə açılır …
gözqırpımı»): update_video R2-dəki index.json-u oxuyub öz kanalımızın videosuna «mp4» sahəsi verir (assets/vlent.js onu adi <video>
ilə oynadır). Telekanallara heç vaxt; siyahı oxunmasa əvvəlki sahə qalır; öz videomuz yoxdursa siyahı soruşulmur."""
import json
import unittest
from unittest.mock import patch

import updater
from test_yoxlama_2026_11_13 import TempFiles, iso


def rss(vid, mins=5):
    return {"title": f"Video {vid}", "link": f"https://www.youtube.com/shorts/{vid}", "description": "", "pubDate": iso(mins), "image": ""}


class VebVideoTest(TempFiles):
    OWN = "OWNVIDEO001"
    TV = "TVVIDEO0001"

    def run_video(self, index, own=True):
        """index: dict (index.json), Exception (oxunmadı) və ya None (soruşulmamalıdır)."""
        tv_name, tv_url = next((n, u) for n, u in updater.YT_NEWS if n != updater.VEB_VIDEO_KANAL)
        own_url = dict(updater.YT_NEWS)[updater.VEB_VIDEO_KANAL]
        def channels(url, limit):
            if url == own_url and own:
                return [rss(self.OWN), rss("OWNVIDEO002", 30)]
            if url == tv_url:
                return [rss(self.TV)]
            raise OSError("şəbəkə")
        asked = []
        def fetch(url, timeout=None, **kw):
            asked.append(url)
            if isinstance(index, Exception):
                raise index
            return json.dumps(index).encode()
        with patch.object(updater, "yt_items", side_effect=channels), patch.object(updater, "fetch", side_effect=fetch):
            updater.update_video()
        rows = {v["videoId"]: v for v in self.read("video.json")["items"]}
        return rows, asked, tv_name

    def test_own_video_with_a_web_copy_gets_its_mp4_and_tv_never_does(self):
        index = {"items": [{"v": self.OWN, "t": iso()}, {"v": self.TV, "t": iso()}, {"v": "../x", "t": iso()}]}
        rows, asked, tv_name = self.run_video(index)
        self.assertEqual(asked, [updater.VEB_VIDEO_URL + "index.json"], "siyahı bir dəfə, R2-nin öz domenindən")
        self.assertEqual(rows[self.OWN]["mp4"], f"https://video.8ulduz.az/{self.OWN}.mp4")
        self.assertNotIn("mp4", rows["OWNVIDEO002"], "veb nüsxəsi olmayan öz video YouTube-dan oynayır")
        self.assertEqual(rows[self.TV]["channel"], tv_name)
        self.assertNotIn("mp4", rows[self.TV], "telekanalın videosu YouTube oynadıcısında qalır")

    def test_unread_index_keeps_the_previous_mp4_and_adds_none(self):
        self.run_video({"items": [{"v": self.OWN, "t": iso()}]})
        rows, _, _ = self.run_video(OSError("şəbəkə"))
        self.assertEqual(rows[self.OWN]["mp4"], f"https://video.8ulduz.az/{self.OWN}.mp4", "siyahı oxunmayanda əvvəlki ünvan qalır")
        self.assertNotIn("mp4", rows["OWNVIDEO002"])
        rows, _, _ = self.run_video({"items": []})
        self.assertNotIn("mp4", rows[self.OWN], "siyahıdan çıxan videonun (silinmiş fayl) ünvanı da çıxır")

    def test_no_own_video_no_request(self):
        rows, asked, _ = self.run_video(None, own=False)
        self.assertEqual(asked, [], "öz videomuz yoxdursa R2 soruşulmur")
        self.assertTrue(rows and all("mp4" not in v for v in rows.values()))


if __name__ == "__main__":
    unittest.main()
