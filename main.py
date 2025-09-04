# main.py

__version__ = "0.1.0"

from datetime import datetime
from zoneinfo import ZoneInfo

from kivy.app import App
from kivy.lang import Builder
from kivy.properties import StringProperty, ListProperty, NumericProperty
from kivy.clock import Clock as KivyClock
from kivy.uix.widget import Widget

# Drawing + sizing helpers
from kivy.graphics import Color, Ellipse
from kivy.metrics import dp
from kivy.core.window import Window

# Optional: dark app background so the pastel faces pop
Window.clearcolor = (0.06, 0.07, 0.09, 1)  # change or remove if you prefer white


class AnalogClock(Widget):
    """
    Simple analog clock drawn via canvas instructions.
    - tzname: IANA time zone (e.g., 'America/Los_Angeles', 'Europe/London')
    - label:  text shown under the clock (e.g., 'San Francisco', 'London')
    - face_color: RGBA tuple for the clock face background
    """
    tzname = StringProperty("UTC")
    label = StringProperty("Zone")
    face_color = ListProperty([0.10, 0.11, 0.13, 1.0])  # default face (dark gray)

    # Use Kivy properties so the canvas reacts to changes
    hour = NumericProperty(0.0)
    minute = NumericProperty(0.0)
    second = NumericProperty(0.0)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        # --- draw the filled face behind everything (background of the clock) ---
        with self.canvas.before:
            self._face_color_instr = Color(rgba=self.face_color)
            self._face_ellipse = Ellipse()  # size/pos set in _update_face()

        # Keep the face ellipse centered & sized to the widget
        self.bind(pos=self._update_face, size=self._update_face, face_color=self._apply_face_color)

        # Timezone & periodic update
        self._tz = ZoneInfo(self.tzname)
        self._evt = KivyClock.schedule_interval(self._update_time, 0.1)

    def _update_face(self, *args):
        """
        Size the face to sit slightly inside the ring so the ring stays crisp on top.
        Set inset=0 for full-bleed face (edge-to-edge).
        """
        inset = dp(6)  # try dp(4) for tighter fit, or 0 for full-bleed
        d = max(0.0, min(self.width, self.height) - 2 * inset)
        self._face_ellipse.size = (d, d)
        self._face_ellipse.pos = (self.center_x - d / 2.0, self.center_y - d / 2.0)

    def _apply_face_color(self, *args):
        self._face_color_instr.rgba = self.face_color

    def on_tzname(self, *_):
        self._tz = ZoneInfo(self.tzname)

    def on_parent(self, *args):
        # Clean up the timer if the widget is removed
        if self.parent is None and self._evt is not None:
            self._evt.cancel()
            self._evt = None

    def _update_time(self, dt):
        now = datetime.now(self._tz)
        self.second = now.second + now.microsecond / 1e6
        self.minute = now.minute + self.second / 60.0
        self.hour = (now.hour % 12) + self.minute / 60.0


class DualClocksApp(App):
    def build(self):
        return Builder.load_file("dualclocks.kv")


if __name__ == "__main__":
    DualClocksApp().run()
