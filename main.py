# main.py
from datetime import datetime

from kivy.app import App
from kivy.lang import Builder
from kivy.properties import BooleanProperty, NumericProperty, StringProperty
from kivy.clock import Clock as KivyClock
from kivy.uix.widget import Widget


class AnalogClock(Widget):
    """
    Simple analog clock drawn with canvas instructions.
    - mode: 'local' or 'utc'
    - label: text shown under the clock (e.g., 'Local', 'UTC')
    - use_24: digital readout uses 24h if True, otherwise 12h
    """
    label = StringProperty("Local")
    mode = StringProperty("local")          # 'local' | 'utc'
    use_24 = BooleanProperty(True)

    # Values used by the canvas and label (updated ~10x/sec)
    hour = NumericProperty(0.0)             # 0..12 (analog hand)
    minute = NumericProperty(0.0)           # 0..60
    second = NumericProperty(0.0)           # 0..60
    d_hour = NumericProperty(0)             # digital
    d_min = NumericProperty(0)
    d_sec = NumericProperty(0)

    _evt = None

    def on_kv_post(self, base_widget):
        # Start updates after the widget is in the tree
        if not self._evt:
            self._evt = KivyClock.schedule_interval(self.update_time, 0.1)

    def on_parent(self, *args):
        # Stop updates if widget is removed
        if self.parent is None and self._evt:
            self._evt.cancel()
            self._evt = None

    def update_time(self, dt):
        now = datetime.utcnow() if self.mode == "utc" else datetime.now()

        # analog
        self.second = now.second + now.microsecond / 1e6
        self.minute = now.minute + self.second / 60.0
        self.hour = (now.hour % 12) + self.minute / 60.0

        # digital
        self.d_hour = now.hour if self.use_24 else (now.hour % 12 or 12)
        self.d_min = now.minute
        self.d_sec = now.second


class DualClocksApp(App):
    def build(self):
        return Builder.load_file("dualclocks.kv")


if __name__ == "__main__":
    DualClocksApp().run()
