import importlib.util
import pathlib
import unittest

ROOT=pathlib.Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location("finish_rollout",ROOT/".github/scripts/finish_rollout.py")
rollout=importlib.util.module_from_spec(spec)
spec.loader.exec_module(rollout)


class RolloutTest(unittest.TestCase):
    def test_only_older_active_main_runs_are_retired(self):
        current={"id":20,"created_at":"2026-11-05T14:00:00Z"}
        def row(ident,at,status="in_progress",branch="main"):
            return {"id":ident,"created_at":at,"status":status,"head_branch":branch}
        runs=[row(10,"2026-11-05T13:00:00Z"),row(20,current['created_at']),row(30,"2026-11-05T15:00:00Z"),row(5,"2026-11-05T12:00:00Z","completed"),row(6,"2026-11-05T12:00:00Z",branch="other")]
        self.assertEqual(rollout.previous_runs(current,runs),[10])

    def test_no_api_or_cancellation_is_allowed_before_the_first_successful_live_write(self):
        def forbidden(*args):raise AssertionError("must not contact API")
        with self.assertRaises(ValueError):rollout.finish(20,forbidden,False)

    def test_the_current_and_newer_workers_survive_the_handoff(self):
        calls=[]
        def api(path,method="GET"):
            calls.append((path,method))
            if path=="actions/runs/20":return {"id":20,"created_at":"2026-11-05T14:00:00Z"}
            if "workflows/" in path:return {"workflow_runs":[{"id":10,"created_at":"2026-11-05T13:00:00Z","head_branch":"main","status":"in_progress"},{"id":30,"created_at":"2026-11-05T15:00:00Z","head_branch":"main","status":"in_progress"}]}
            return {}
        self.assertEqual(rollout.finish(20,api,True),[10])
        self.assertEqual([p for p,m in calls if m=="POST"],["actions/runs/10/cancel"])
