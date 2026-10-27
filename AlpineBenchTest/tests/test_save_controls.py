import unittest
from types import SimpleNamespace
from unittest.mock import Mock, patch
from app.wizard import Wizard


class SaveControlsTests(unittest.TestCase):
    def test_save_precedes_exit_prompt(self):
        events = []
        screen = SimpleNamespace(save_draft=Mock(),
            mutate=lambda action: events.append("save"),
            saved_exit_prompt=lambda: events.append("prompt"))
        Wizard.save_quit(screen)
        self.assertEqual(events, ["save", "prompt"])

    def test_failed_save_does_not_offer_exit(self):
        screen = SimpleNamespace(save_draft=Mock(), mutate=Mock(side_effect=OSError("offline")), saved_exit_prompt=Mock())
        with self.assertRaises(OSError):
            Wizard.save_quit(screen)
        screen.saved_exit_prompt.assert_not_called()

    def test_exit_choice(self):
        for choice in (True, False):
            screen = SimpleNamespace(destroy=Mock())
            with patch("app.wizard.messagebox.askyesno", return_value=choice):
                self.assertEqual(Wizard.saved_exit_prompt(screen), choice)
            self.assertEqual(screen.destroy.called, choice)

    def test_saves_unsubmitted_fields_without_evaluation(self):
        value = Mock()
        value.get.return_value = "unfinished reading"
        screen = SimpleNamespace(entry_step="cda1", run={}, variables={"QDF6_initial": value})
        Wizard.save_draft(screen)
        self.assertEqual(screen.run["draft"]["values"]["QDF6_initial"], "unfinished reading")

    def test_yellow_tag_can_close_nonfailed_stage(self):
        run = {"status": "In progress", "step_index": 1, "notes": []}
        screen = SimpleNamespace(run=run, steps=[{}, {"title": "CDA 1"}],
            save_draft=Mock(), mutate=lambda action: action(),
            saved_exit_prompt=Mock(return_value=False), home=Mock())
        with patch("app.wizard.messagebox.askyesno", return_value=True):
            Wizard.yellow_tag(screen)
        self.assertEqual(run["decision"], "Fail")
        self.assertEqual(run["status"], "Complete")
        self.assertIn("CDA 1", run["notes"][-1])
        screen.home.assert_called_once()
