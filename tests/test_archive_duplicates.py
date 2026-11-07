"""2026-11-07: eyni universitet təməlqoyması Təhsildə çoxsaylı kartla görünürdü."""
import copy
import datetime
import json
import pathlib
import tempfile
import unittest
from unittest.mock import patch

import updater


FIXTURE = pathlib.Path(__file__).parent / "fixtures" / "education-duplicates.json"


class ArchiveDuplicatesTest(unittest.TestCase):
    def test_candidate_index_matches_full_comparison_including_fuzzy_names(self):
        fixture = json.loads(FIXTURE.read_text(encoding="utf-8"))
        rows = [*fixture["archive"], *fixture["live"]]
        base = {"category": "gundem", "lang": "az", "publishedAt": "2026-11-07T07:00:00Z"}
        titles = ["Pərviz Abubəkirov işdən çıxarıldı", "Pərviz Əbubəkirov vəzifəsindən azad edilib",
                  "Bakıda avtobus qəzasında iki nəfər yaralanıb", "Göygöldə minik avtomobili qəzaya uğrayıb",
                  "Bakıda avtobus sürücüsü həbs olunub", "Bakıda avtobus sürücüsü qəza törədib və saxlanılıb",
                  "Şuşada məktəbin yeni binası açılıb", "Bakı Bakı Bakı Bakı", "Bakı Bakı Bakı Bakı"]
        rows += [dict(base, id=str(i), source=f"S{i}", sourceUrl=f"https://example.org/{i}", title=t) for i, t in enumerate(titles)]
        for ordered in (rows, list(reversed(rows))):
            actual = updater.group_duplicates(copy.deepcopy(ordered), same_source_exact=False)
            # Independent reference path: run the same matching rules against every existing cluster.
            with patch.object(updater, "_group_candidates", side_effect=lambda *args: set().union(*args[-1].values())):
                expected = updater.group_duplicates(copy.deepcopy(ordered), same_source_exact=False)
            self.assertEqual(actual, expected)

    def test_existing_archive_is_grouped_and_keeps_sources_across_refreshes(self):
        fixture = json.loads(FIXTURE.read_text(encoding="utf-8"))
        now = datetime.datetime(2026, 11, 7, 8, tzinfo=datetime.timezone.utc).timestamp()
        with tempfile.TemporaryDirectory() as tmp:
            root = pathlib.Path(tmp)
            path = root / "tehsil.json"
            # Fresh timestamps must not postpone the one-time migration for an hour.
            path.write_text(json.dumps({"at": now, "articles": fixture["archive"]}), encoding="utf-8")
            (root / "gundem.json").write_text(json.dumps({"at": now, "articles": []}), encoding="utf-8")
            with patch.object(updater, "ARCHIVE_DIR", root), \
                 patch.object(updater, "ARCHIVE_OG_FILE", root / "og.json"), \
                 patch.object(updater, "SECTIONS", [("gundem", "Gündəm", ""), ("tehsil", "Təhsil", "")]), \
                 patch.object(updater, "read_feed", return_value=copy.deepcopy(fixture["live"])) as feed, \
                 patch.object(updater, "feed_backlog", return_value=[]), \
                 patch.object(updater, "bulk_dated_sources", return_value=set()), \
                 patch.object(updater, "dead_links", return_value=set()), \
                 patch.object(updater, "update_share_index"):
                updater.update_archive(now)
                doc = json.loads(path.read_text(encoding="utf-8"))
                self.assertEqual(doc["grouped"], 1)
                self.assertEqual(len(doc["articles"]), 1)
                card = doc["articles"][0]
                sources = {x["source"] for x in [card, *card.get("alts", [])]}
                expected = {x["source"] for a in fixture["groupedArchive"] for x in [a, *a.get("alts", [])]}
                self.assertEqual(sources, expected)
                self.assertTrue(all(x.get("title") for x in card["alts"]))
                # A later ungrouped live copy of the primary must not erase archive alternatives.
                feed.return_value = [{k: v for k, v in card.items() if k != "alts"}]
                updater.update_archive(now + updater.ARCHIVE_EVERY_S + 1)
                again = json.loads(path.read_text(encoding="utf-8"))["articles"]
                self.assertEqual(len(again), 1)
                self.assertEqual({x["source"] for x in [again[0], *again[0].get("alts", [])]}, sources)
                # Already migrated archives keep the hourly write interval.
                with patch.object(updater, "group_duplicates", side_effect=AssertionError("hourly archive not due")):
                    updater.update_archive(now + updater.ARCHIVE_EVERY_S + 2)


if __name__ == "__main__":
    unittest.main()
