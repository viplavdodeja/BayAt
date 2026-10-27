import unittest
from types import SimpleNamespace
from unittest.mock import Mock

try:
    from app.wizard import Wizard
except ModuleNotFoundError:
    Wizard = None


@unittest.skipIf(Wizard is None, "Tkinter is unavailable")
class ScrollTests(unittest.TestCase):
    def screen(self, platform):
        canvas = Mock()
        canvas.bbox.return_value = (0, 0, 800, 1800)
        canvas.winfo_height.return_value = 600
        screen = SimpleNamespace(canvas=canvas, wheel_remainder=0, touchpad_remainder=0, tk=Mock())
        screen.tk.call.return_value = platform
        widget = Mock()
        widget.winfo_toplevel.return_value = screen
        return screen, widget

    def test_mac_trackpad_scrolls_both_directions(self):
        screen, widget = self.screen("aqua")
        for delta, expected in ((-2, 2), (3, -3)):
            Wizard.scroll_window(screen, SimpleNamespace(widget=widget, delta=delta))
            screen.canvas.yview_scroll.assert_called_with(expected, "units")

    def test_windows_accumulates_small_wheel_deltas(self):
        screen, widget = self.screen("win32")
        event = SimpleNamespace(widget=widget, delta=-60)
        Wizard.scroll_window(screen, event)
        screen.canvas.yview_scroll.assert_not_called()
        Wizard.scroll_window(screen, event)
        screen.canvas.yview_scroll.assert_called_once_with(3, "units")

    def test_linux_wheel_and_short_screen(self):
        screen, widget = self.screen("x11")
        Wizard.scroll_window(screen, SimpleNamespace(widget=widget, num=4))
        screen.canvas.yview_scroll.assert_called_once_with(-3, "units")
        screen.canvas.yview_scroll.reset_mock()
        screen.canvas.bbox.return_value = (0, 0, 800, 400)
        Wizard.scroll_window(screen, SimpleNamespace(widget=widget, num=5))
        screen.canvas.yview_scroll.assert_not_called()

    def test_popup_does_not_scroll_main_screen(self):
        screen, widget = self.screen("aqua")
        widget.winfo_toplevel.return_value = object()
        Wizard.scroll_window(screen, SimpleNamespace(widget=widget, delta=-2))
        screen.canvas.yview_scroll.assert_not_called()

    def test_tk9_packed_touchpad_delta_and_small_gestures(self):
        screen, widget = self.screen("aqua")
        for _ in range(3):
            Wizard.scroll_touchpad(screen, SimpleNamespace(widget=widget, delta=(7 << 16) | 0xfffc))
        screen.canvas.yview_scroll.assert_called_once_with(1, "units")
        Wizard.scroll_touchpad(screen, SimpleNamespace(widget=widget, delta=12))
        screen.canvas.yview_scroll.assert_called_with(-1, "units")

    def test_tk9_horizontal_gesture_does_not_scroll_vertically(self):
        screen, widget = self.screen("aqua")
        Wizard.scroll_touchpad(screen, SimpleNamespace(widget=widget, delta=20 << 16))
        screen.canvas.yview_scroll.assert_not_called()
