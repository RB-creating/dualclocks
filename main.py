# main.py
from datetime import datetime
from zoneinfo import ZoneInfo  # stdlib (Python 3.9+); pairs with 'tzdata' package

from kivy.app import App
from kivy.lang import Builder
from kivy.properties import StringProperty
from kivy.clock import Clock as KivyClock
from kivy.uix.widget import Widget


class AnalogClock(Widget):
    """
    Simple analog clock drawn via canvas instructions.
    - tzname: IANA time zone (e.g., 'America/Los_Angeles', 'Europe/London')
    - label:  text shown under the clock (e.g., 'San Francisco', 'London')
    """
    tzname = StringProperty("UTC")
    label = StringProperty("Zone")

    # Angle sources for the hands (updated ~10x/sec)
    # We keep them as attributes so KV can bind to them.
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._tz = ZoneInfo(self.tzname)

        # Update a little after KV is applied to ensure sizes are known
        self._evt = KivyClock.schedule_interval(self._update_time, 0.1)

    def on_tzname(self, *_):
        # If tzname changes, refresh the ZoneInfo
        self._tz = ZoneInfo(self.tzname)

    def on_parent(self, *args):
        # Stop updates if removed from the tree
        if self.parent is None and self._evt is not None:
            self._evt.cancel()
            self._evt = None

    # values read by canvas (we store them on self to read in KV)
    hour = 0.0
    minute = 0.0
    second = 0.0

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
