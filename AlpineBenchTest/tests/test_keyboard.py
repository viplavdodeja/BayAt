import unittest
from types import SimpleNamespace
from unittest.mock import Mock
from app.wizard import Wizard


class KeyboardTests(unittest.TestCase):
    def test_enter_only_invokes_enabled_continue(self):
        for disabled in (True, False):
            button = Mock()
            button.winfo_exists.return_value = True
            button.instate.return_value = disabled
            screen = SimpleNamespace(continue_button=button)
            widget = Mock()
            widget.winfo_toplevel.return_value = screen
            result = Wizard.continue_from_keyboard(screen, SimpleNamespace(widget=widget))
            self.assertEqual(result, "break")
            self.assertEqual(button.invoke.called, not disabled)

    def test_dialog_enter_does_not_advance_wizard(self):
        screen = SimpleNamespace(continue_button=Mock())
        widget = Mock()
        widget.winfo_toplevel.return_value = object()
        Wizard.continue_from_keyboard(screen, SimpleNamespace(widget=widget))
        screen.continue_button.invoke.assert_not_called()
