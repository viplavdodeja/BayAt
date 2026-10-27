import unittest
from datetime import date
from app.analytics import run_rows
from app.storage import load_config


class AnalyticsTests(unittest.TestCase):
    def test_latest_retry_and_history_are_separate(self):
        run = {"id": "id", "serial": "001", "date": "2026-10-11", "test_number": 2,
               "status": "Complete", "decision": "Pass", "notes": ["Previous failure at CDA 1"],
               "attempts": [{"step": "cda1", "title": "CDA 1", "passed": False, "values": {"QDF6_initial": 10}},
                            {"step": "cda1", "title": "CDA 1", "passed": True, "values": {"QDF6_initial": 11}}]}
        headers, rows = run_rows({"job": "0001", "runs": [run]}, load_config("test_steps.json"))
        row = dict(zip(headers, rows[0]))
        self.assertEqual(row["Job number"], "0001")
        self.assertEqual(row["Run ID"], 1)
        self.assertEqual(row["Serial number"], "001")
        self.assertEqual(row["Test date"], date(2026, 10, 11))
        self.assertEqual(row["Failed attempts"], 1)
        key = next(h for h in headers if h.endswith("| QDF6_initial"))
        self.assertEqual(row[key], 11)
        self.assertEqual(len(headers), len(rows[0]))

    def test_drafts_do_not_become_tested_measurements(self):
        run = {"id": "id", "serial": "001", "date": "2026-10-11", "test_number": 1,
               "status": "In progress", "decision": "", "notes": [], "attempts": [],
               "draft": {"step": "cda1", "values": {"QDF6_initial": "10"}}}
        headers, rows = run_rows({"job": "demo", "runs": [run]}, load_config("test_steps.json"))
        key = next(h for h in headers if h.endswith("| QDF6_initial"))
        self.assertIsNone(rows[0][headers.index(key)])
