import unittest
from types import SimpleNamespace
from unittest.mock import Mock, patch

try:
    from app.wizard import Wizard
except ModuleNotFoundError:
    Wizard = None


@unittest.skipIf(Wizard is None, "Tkinter is unavailable")
class TimerTests(unittest.TestCase):
    def test_testing_toggle_skips_wait_and_timer_button(self):
        screen = SimpleNamespace(body=Mock(), button=Mock(), set_continue=Mock())
        with patch("app.wizard.LOCK_FINAL_READINGS_UNTIL_TIMER_FINISHES", False), patch("app.wizard.ttk.Label"):
            Wizard.setup_timer(screen)
        self.assertTrue(screen.timer_complete)
        self.assertIsNone(screen.started)
        screen.button.assert_not_called()

    def test_initial_stays_editable_and_final_unlocks_after_interval(self):
        initial, final = Mock(), Mock()
        screen = SimpleNamespace(
            started=None, timer_complete=False, timer_token=None,
            timer_button=Mock(), timer_label=Mock(), submit=Mock(),
            set_continue=Mock(),
            field_widgets={"QDF6_initial": initial, "QDF6_final": final},
            after=Mock(return_value="scheduled"),
        )
        screen.timer_tick = lambda: Wizard.timer_tick(screen)
        with patch("app.wizard.time.monotonic", return_value=100):
            Wizard.start_timer(screen)
        self.assertEqual(screen.started, 100)
        initial.configure.assert_not_called()
        final.configure.assert_not_called()
        with patch("app.wizard.time.monotonic", return_value=159.9):
            Wizard.timer_tick(screen)
        self.assertFalse(screen.timer_complete)
        final.configure.assert_not_called()
        with patch("app.wizard.time.monotonic", return_value=160):
            Wizard.timer_tick(screen)
        self.assertTrue(screen.timer_complete)
        final.configure.assert_called_once_with(state="normal")
        initial.configure.assert_not_called()
        screen.submit.configure.assert_called_once_with(state="normal")
        self.assertIsNone(screen.timer_token)
        with patch("app.wizard.time.monotonic", return_value=200):
            Wizard.start_timer(screen)
        self.assertEqual(screen.started, 100)


if __name__ == "__main__":
    unittest.main()
