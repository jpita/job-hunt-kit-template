"""Focused regressions for scanner persistence and partial-run handling."""
import atexit
import json
import os
import pathlib
import sys
import tempfile
import unittest
from concurrent.futures import ThreadPoolExecutor
from unittest import mock


_test_root = tempfile.TemporaryDirectory(prefix="jobkit-tests-")
atexit.register(_test_root.cleanup)
_me = pathlib.Path(_test_root.name) / "me"
_me.mkdir()
(_me / "search.py").write_text(
    'NAME = ""\n'
    'TIMEZONE = "UTC"\n'
    'PORT = 8777\n'
    'ROLE_NOUN = "role"\n'
    'TARGET_LABEL = "target"\n'
    'HOME_LABEL = "home"\n'
    'ROLE_GATE = r".*"\n'
    'TARGET_TITLE = r".*"\n'
    'EXCLUDE_TITLES = r"(?!)"\n'
    'LOWER_LEVEL = r"(?!)"\n'
    'HOME_PLACES = r"Exampleland"\n'
    'HOME_COUNTRY_CODES = ["ZZ"]\n'
    'GOOGLE_QUERIES = []\n',
    encoding="utf-8")
os.environ["JOBKIT_ME"] = str(_me)
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

import discover
import google_scan
import report
import runlog


class RunLogTests(unittest.TestCase):
    def test_concurrent_records_are_not_lost(self):
        with tempfile.TemporaryDirectory() as directory:
            path = pathlib.Path(directory) / "runs.json"
            with mock.patch.object(runlog, "F", path), \
                 mock.patch.object(runlog, "LOCK", path.with_name(".runs.lock")):
                with ThreadPoolExecutor(max_workers=8) as pool:
                    list(pool.map(
                        lambda _: runlog.record("report", ok=True), range(24)))
                self.assertEqual(len(runlog.load()), 24)

    def test_harvest_success_is_not_a_completed_google_scan(self):
        with tempfile.TemporaryDirectory() as directory:
            path = pathlib.Path(directory) / "runs.json"
            path.write_text(json.dumps([
                {"kind": "google", "ok": True, "when": "2026-10-01T09:00:00+00:00",
                 "found": 12},
                {"kind": "google", "ok": True, "when": "2026-10-01T09:01:00+00:00",
                 "urls_in": 12, "read_ok": 12},
            ]), encoding="utf-8")
            with mock.patch.object(runlog, "F", path):
                self.assertEqual(runlog.last("google", completed_only=True)["urls_in"], 12)
                self.assertEqual(runlog.last("google", ok_only=False,
                                             completed_only=True)["urls_in"], 12)

    def test_report_does_not_call_a_harvest_a_completed_google_scan(self):
        with tempfile.TemporaryDirectory() as directory:
            root = pathlib.Path(directory)
            path = root / "runs.json"
            path.write_text(json.dumps([
                {"kind": "google", "ok": True, "when": "2026-10-02T09:00:00+00:00",
                 "found": 12},
            ]), encoding="utf-8")
            with mock.patch.object(runlog, "F", path), \
                 mock.patch.object(report, "BOARD_LOG", root / "boards-read.json"):
                items, _ = report.health("2026-10-02")
        google = next(item for item in items if item["label"] == "Google scan")
        self.assertEqual(google["state"], "bad")
        self.assertEqual(google["when"], "never completed")


class ProcessingTests(unittest.TestCase):
    def test_google_partial_failure_preserves_the_previous_snapshot(self):
        old_url = (
            "https://jobs.lever.co/example/"
            "11111111-1111-1111-1111-111111111111")
        new_urls = [
            "https://jobs.lever.co/example/"
            "00000001-1111-1111-1111-111111111111",
            "https://jobs.lever.co/example/"
            "00000002-1111-1111-1111-111111111111",
        ]
        with tempfile.TemporaryDirectory() as directory:
            root = pathlib.Path(directory)
            seen = root / "google-seen.json"
            old_rows = [{"url": old_url, "title": "Existing role",
                         "bucket": "clean", "first_seen": "2026-10-01"}]
            seen.write_text(json.dumps(old_rows), encoding="utf-8")
            harvest = root / "harvest.json"
            harvest.write_text(json.dumps({"jobs": new_urls}), encoding="utf-8")
            with mock.patch.object(google_scan, "SEEN", seen), \
                 mock.patch.object(google_scan, "OUT", root / "google-report.html"), \
                 mock.patch.object(google_scan, "FETCH", {"lever": lambda *args: None}), \
                 mock.patch.object(google_scan, "read_page",
                                   return_value=("unknown", "")), \
                 mock.patch.object(google_scan.bodies, "load", return_value={}), \
                 mock.patch.object(google_scan.runlog, "record") as record, \
                 mock.patch.object(google_scan.sys, "argv",
                                   ["google_scan.py", str(harvest)]):
                self.assertEqual(google_scan.main(), 1)

            self.assertEqual(json.loads(seen.read_text()), old_rows)
            self.assertFalse((root / "google-report.html").exists())
            self.assertFalse(record.call_args.kwargs["ok"])
            self.assertEqual(record.call_args.kwargs["read_ok"], 0)

    def test_google_api_remote_flags_are_preserved(self):
        with mock.patch.object(google_scan, "get", return_value={
            "text": "Example role",
            "categories": {"location": "Remote - Exampleland"},
            "country": "ZZ",
            "workplaceType": "remote",
        }):
            lever_job = google_scan.fetch_lever(
                "example", "posting", "https://jobs.lever.co/example/posting")
        self.assertTrue(lever_job["remote"])

        google_scan._ashby_cache.clear()
        with mock.patch.object(google_scan, "get", return_value={"jobs": [{
            "title": "Example role",
            "jobUrl": "https://jobs.ashbyhq.com/example/posting",
            "isRemote": True,
        }]}):
            ashby_job = google_scan.fetch_ashby(
                "example", "posting", "https://jobs.ashbyhq.com/example/posting")
        self.assertTrue(ashby_job["remote"])

    def test_discovery_marks_failed_search_as_incomplete(self):
        with mock.patch.object(discover, "PAGES", 1), \
             mock.patch.object(discover, "gh_search", return_value=None):
            slugs, complete = discover.harvest(
                "jobs.lever.co", discover.BOARDS["lever"][1])
        self.assertEqual(slugs, set())
        self.assertFalse(complete)

    def test_greenhouse_host_aliases_share_the_saved_mark(self):
        old_url = "https://boards.greenhouse.io/example/jobs/1001"
        new_url = "https://job-boards.greenhouse.io/example/jobs/1001"
        with tempfile.TemporaryDirectory() as directory:
            root = pathlib.Path(directory)
            board = root / "board-seen.json"
            google = root / "google-seen.json"
            board.write_text(json.dumps({old_url: {
                "company": "example", "title": "Example role",
                "date": "2026-10-01", "blocked": [], "check": [],
            }}), encoding="utf-8")
            google.write_text(json.dumps([{
                "url": new_url, "company": "example", "title": "Example role",
                "first_seen": "2026-10-01", "hard": [], "soft": [],
                "bucket": "clean",
            }]), encoding="utf-8")
            with mock.patch.object(report, "BOARD", board), \
                 mock.patch.object(report, "GOOGLE", google), \
                 mock.patch.object(report.feedback, "load", return_value={
                     old_url: {"verdict": "good", "state": "applied", "note": ""}
                 }), \
                 mock.patch.object(report.rule_reports, "load", return_value=[]):
                rows = report.load()
        self.assertEqual(len(rows), 2)
        self.assertEqual({row["bucket"] for row in rows}, {"handled"})
        self.assertEqual({row["state"] for row in rows}, {"applied"})


if __name__ == "__main__":
    unittest.main()
