import tempfile
import unittest
from app.calculations import evaluate, number
from app.storage import Store, load_config, validate_identifier


class AcceptanceTests(unittest.TestCase):
    def setUp(self):
        self.steps = {s["id"]: s for s in load_config("test_steps.json")}
        self.limits = load_config("acceptance_limits.json")

    def decay(self, key, initial, final, seconds=60):
        step = self.steps[key]
        values = {f["id"]: initial if f["id"].endswith("_initial") else final for f in step["fields"]}
        values["elapsed_seconds"] = seconds
        return evaluate(step, values, self.limits)

    def test_strict_decay_boundary_and_elapsed_time(self):
        self.assertTrue(self.decay("cda1", 10, 9.5)[1])
        self.assertFalse(self.decay("cda1", 10, 9.5, 120)[1])
        with self.assertRaises(ValueError):
            self.decay("cda1", 10, 9.9, 59)

    def test_signed_vacuum_decay(self):
        values, failures = self.decay("vac1", -100, -96)
        self.assertEqual(values["QDF3_decay"], 4)
        self.assertFalse(failures)
        self.assertTrue(self.decay("vac1", -100, -95)[1])
        self.assertTrue(self.decay("vac1", -100, -101)[1])
        with self.assertRaises(ValueError):
            self.decay("vac1", 100, 96)

    def test_er1_range_and_correct_sensor(self):
        self.assertIn("QDF22", self.steps["er1"]["sensors"])
        self.assertEqual(self.limits["decay"]["QDF22"], 2)
        self.assertEqual(self.limits["decay"]["QDM7"], 0.5)
        self.assertFalse(self.decay("er1", 3.0, 2.9)[1])
        self.assertTrue(self.decay("er1", 2.5, 2.4)[1])

    def test_voltage_boundaries_and_required_zero(self):
        step = self.steps["vac2"]
        values = {s + "_" + v + "V": bounds[0] for s in step["sensors"] for v, bounds in self.limits["voltage"].items()}
        values["return_zero"] = True
        self.assertFalse(evaluate(step, values, self.limits)[1])
        values["QDM1_10V"] = -761
        self.assertTrue(evaluate(step, values, self.limits)[1])
        values["return_zero"] = False
        self.assertIn("Vacuum returns to zero at 0 V", evaluate(step, values, self.limits)[1])

    def test_cv3_strict_bounds(self):
        values = {"CV5_pressure": 1.2, "CV3_airflow": True, "CV5_stable": True}
        self.assertTrue(evaluate(self.steps["cv3"], values, self.limits)[1])
        values["CV5_pressure"] = 0.8
        self.assertFalse(evaluate(self.steps["cv3"], values, self.limits)[1])

    def test_reject_nonfinite(self):
        for text in ("nan", "inf", "-inf"):
            with self.assertRaises(ValueError):
                number(text)


class PersistenceTests(unittest.TestCase):
    def test_retest_retains_attempts_and_progress(self):
        with tempfile.TemporaryDirectory() as destination:
            store = Store(destination)
            data = store.load("123")
            first = store.new_run(data, "SN001", "2026-10-10")
            first.update(status="Complete", decision="Fail")
            first["attempts"].append({"step": "cda1", "passed": False})
            store.save(data)
            second = store.new_run(data, "sn001", "2026-10-11")
            second.update(step_index=2, pending_failure=True)
            store.save(data)
            loaded = store.load("123")
            self.assertNotEqual(first["id"], second["id"])
            self.assertEqual(second["test_number"], 2)
            self.assertIn("re-test", second["notes"][0])
            self.assertEqual(len(loaded["runs"][0]["attempts"]), 1)
            self.assertEqual(loaded["runs"][1]["step_index"], 2)
            self.assertTrue(loaded["runs"][1]["pending_failure"])

    def test_reject_path_traversal_and_reserved_names(self):
        for name in ("../escape", "a/b", "CON", "NUL.txt", "job."):
            with self.assertRaises(ValueError):
                validate_identifier(name, "Job")


if __name__ == "__main__":
    unittest.main()
