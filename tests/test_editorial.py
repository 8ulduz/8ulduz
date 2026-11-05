import base64
import importlib.util
import io
import json
import pathlib
import tempfile
import unittest

import content_policy

ROOT = pathlib.Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("editorial_sync", ROOT / ".github/scripts/editorial_sync.py")
sync = importlib.util.module_from_spec(spec)
spec.loader.exec_module(sync)


class EditorialTest(unittest.TestCase):
    def test_the_requested_story_and_changed_slug_are_blocked_but_its_neighbour_is_allowed(self):
        self.assertTrue(content_policy.removed_article({"sourceUrl":"https://www.nocomment.az/another-title-555222?utm_source=x"}))
        self.assertTrue(content_policy.removed_article({"id":"5e6cc2e84ced07dd"}))
        self.assertFalse(content_policy.removed_article({"sourceUrl":"https://nocomment.az/another-title-555223"}))
        self.assertFalse(content_policy.removed_article({"sourceUrl":"https://apa.az/another-title-555222"}))

    def test_archive_and_alternative_sources_cannot_reintroduce_the_withdrawn_story(self):
        withdrawn={"source":"Nocomment.az","sourceUrl":"https://nocomment.az/new-title-555222","title":"Changed title"}
        kept={"source":"APA","sourceUrl":"https://apa.az/other-12345","title":"Other story","alts":[withdrawn]}
        clean,dropped=content_policy.enforce([withdrawn,kept])
        self.assertEqual(len(clean),1)
        self.assertEqual(clean[0]['alts'],[])
        self.assertEqual(sum(dropped.values()),1)

    def test_background_sync_uses_only_the_fixed_github_endpoint_and_keeps_the_last_good_list(self):
        row={"key":"apa.az#12345","urls":["https://apa.az/story-12345"],"keys":["apa.az#12345"],"ids":["id"]}
        def opener(records):
            def get(request,timeout):
                self.assertEqual(request.full_url,"https://api.github.com/repos/8ulduz/8ulduz/contents/assets/content-policy.js?ref=main")
                value='window.CONTENT_POLICY = '+json.dumps({"removedArticles":records})+';'
                return io.BytesIO(json.dumps({"encoding":"base64","content":base64.b64encode(value.encode()).decode()}).encode())
            return get
        with tempfile.TemporaryDirectory() as tmp:
            self.assertTrue(sync.sync_once(tmp,"8ulduz/8ulduz","test-only",opener({row['key']:row})))
            self.assertFalse(sync.sync_once(tmp,"8ulduz/8ulduz","test-only",opener({})))
            path=pathlib.Path(tmp)/'.cache/editorial-removals.json'
            before=path.read_text()
            with self.assertRaises(ValueError):sync.sync_once(tmp,"8ulduz/8ulduz","test-only",opener({"bad":{"urls":None}}))
            self.assertEqual(path.read_text(),before)

    def test_the_site_keeps_content_sources_and_the_fast_cycle_independent_of_admin_network_calls(self):
        self.assertIn('EDITORIAL_PID=$!',(ROOT/'.github/scripts/pipeline.sh').read_text())
        self.assertNotIn('editorial_sync', (ROOT/'updater.py').read_text())
        self.assertNotIn('api.github.com',(ROOT/'assets/app.js').read_text())
