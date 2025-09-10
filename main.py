# main.py
from datetime import datetime, timezone
from math import sin, cos, radians, pi
from zoneinfo import ZoneInfo

from kivy.config import Config
Config.set('input', 'mouse', 'mouse,disable_multitouch')  # Disable red dot on click
from kivy.app import App
from kivy.clock import Clock
from kivy.uix.spinner import Spinner
from kivy.core.window import Window
from kivy.properties import StringProperty, ObjectProperty, ListProperty, BooleanProperty
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.widget import Widget
from kivy.graphics import Color, Ellipse, Line, Rectangle
from kivy.utils import platform
from kivy.core.text import Label as CoreLabel
from kivy.metrics import sp

class StableSpinner(Spinner):
    """Opens the dropdown on next frame to avoid immediate auto-dismiss on touch devices."""
    def on_release(self):
        # Defer the default toggle to the next frame
        Clock.schedule_once(lambda dt: super(StableSpinner, self).on_release(), 0)

# Make the app background white
Window.clearcolor = (0.8, 0.8, 0.8, 1)

# Display names map to IANA time zones (Spinners show only these city names)
CITY_TIMEZONES = {
    "Los Angeles": "America/Los_Angeles",
    "San Francisco": "America/Los_Angeles",
    "New York": "America/New_York",
    "London": "Europe/London",
    "Paris": "Europe/Paris",
    "Berlin": "Europe/Berlin",
    "Dubai": "Asia/Dubai",
    "Delhi": "Asia/Kolkata",
    "Beijing": "Asia/Shanghai",
    "Tokyo": "Asia/Tokyo",
    "Sydney": "Australia/Sydney",
    "Auckland": "Pacific/Auckland",
    "Johannesburg": "Africa/Johannesburg",
    "São Paulo": "America/Sao_Paulo",
    "Honolulu": "Pacific/Honolulu",
}

CITY_LIST = list(CITY_TIMEZONES.keys())


def hours_diff_between(tz_left: str, tz_right: str) -> float:
    """
    Returns RIGHT - LEFT in hours using current UTC offsets.
    This properly reflects DST and odd offsets (e.g., +5:30).
    """
    now_utc = datetime.now(timezone.utc)
    left_offset = now_utc.astimezone(ZoneInfo(tz_left)).utcoffset()
    right_offset = now_utc.astimezone(ZoneInfo(tz_right)).utcoffset()
    # Safety: utcoffset() can be None for weird zones; treat as 0.
    left_secs = 0 if left_offset is None else left_offset.total_seconds()
    right_secs = 0 if right_offset is None else right_offset.total_seconds()
    return (right_secs - left_secs) / 3600.0


def fmt_hours(h: float) -> str:
    """Format hours compactly, dropping trailing .0 (handles half-hours cleanly)."""
    # Round to 2 decimals to avoid floating noise, but display cleanly
    rounded = round(h + 0.0, 2)
    # Use 'g' to strip trailing zeros; still show .5, .25, etc.
    return f"{rounded:g}"


class AnalogClock(Widget):
    tz_name = StringProperty("UTC")  # IANA TZ string
    label = StringProperty("Clock")
    face_color = ObjectProperty((1, 1, 1, 1))  # Default white

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # Update once per second to keep it light and consistent
        Clock.schedule_interval(self.update_clock, 1)
        # Also redraw when size/pos changes to avoid blank rendering on first layout
        self.bind(size=self._redraw, pos=self._redraw)

    def _get_now(self):
        try:
            return datetime.now(ZoneInfo(self.tz_name))
        except Exception:
            # Fallback: if tz loading fails, use UTC
            return datetime.now(timezone.utc)

    def _redraw(self, *args):
        # Draw once when layout changes
        self.update_clock(0)

    def update_clock(self, dt):
        self.canvas.clear()
        if self.width <= 2 or self.height <= 2:
            return  # avoid drawing when not laid out yet

        cx, cy = self.center
        radius = 0.45 * min(self.width, self.height)  # margin

        now = self._get_now()
        h = now.hour % 12
        m = now.minute
        s = now.second

        # Hand angles (0 at 12 o'clock, positive clockwise)
        angle_hour = (h + m / 60.0 + s / 3600.0) * 30.0  # deg
        angle_min = (m + s / 60.0) * 6.0
        angle_sec = s * 6.0

        def polar_to_xy(center_x, center_y, angle_deg, length):
            # Convert to screen coords; subtract 90° so 0° is at 12 o'clock.
            rad = radians(-angle_deg) + pi / 2
            return (center_x + length * cos(rad), center_y + length * sin(rad))

        with self.canvas:
            # Face fill (white) and outline (black)
            Color(*self.face_color)
            Ellipse(pos=(cx - radius, cy - radius), size=(2 * radius, 2 * radius))
            Color(0, 0, 0, 1)
            Line(circle=(cx, cy, radius), width=1.5)

            # Hour tick marks (12)
            tick_outer = radius * 0.95
            tick_inner = radius * 0.82
            for i in range(12):
                deg = i * 30.0
                x1, y1 = polar_to_xy(cx, cy, deg, tick_outer)
                # Make cardinal ticks longer and thicker
                if i in [0, 3, 6, 9]:  # 12, 3, 6, 9
                    x2, y2 = polar_to_xy(cx, cy, deg, radius * 0.78)
                    Line(points=[x1, y1, x2, y2], width=2.4)
                else:
                    x2, y2 = polar_to_xy(cx, cy, deg, tick_inner)
                Line(points=[x1, y1, x2, y2], width=1.6)

                # --- Numerals 12, 3, 6, 9 (inside the face, darker than face color) ---
            # Use a darker shade of the face color for good contrast
            fr, fg, fb, fa = self.face_color
            num_color = (fr * 0.6, fg * 0.6, fb * 0.6, 1)  # 60% of face color

            # Font size scales with the clock size; tweak 0.18 for bigger/smaller
            num_size = max(12, int(radius * 0.18))

            # Place numerals a bit inside the rim; tweak 0.68 to move in/out
            r_fac = 0.68

            def put_num(text: str, angle_deg: float):
                # Render text to a texture in the chosen color
                lbl = CoreLabel(text=text, font_size=num_size, color=num_color)
                lbl.refresh()
                tex = lbl.texture
                tw, th = tex.size

                # Your polar_to_xy uses 0° at 12 o'clock and increases clockwise
                px, py = polar_to_xy(cx, cy, angle_deg, radius * r_fac)

                # Draw the texture; keep Color(1,1,1,1) so texture's own color shows
                Color(1, 1, 1, 1)
                Rectangle(texture=tex, pos=(px - tw / 2, py - th / 2), size=(tw, th))

            # Put the four numerals
            put_num("12", 0)     # top
            put_num("3", 90)     # right
            put_num("6", 180)    # bottom
            put_num("9", 270)    # left

            # Minute hand
            Color(0.2, 0.2, 0.2, 1)
            x_m, y_m = polar_to_xy(cx, cy, angle_min, radius * 0.75)
            Line(points=[cx, cy, x_m, y_m], width=2)

            # Hour hand
            Color(0, 0, 0, 1)
            x_h, y_h = polar_to_xy(cx, cy, angle_hour, radius * 0.55)
            Line(points=[cx, cy, x_h, y_h], width=3)

            # Second hand (red)
            Color(1, 0, 0, 1)
            x_s, y_s = polar_to_xy(cx, cy, angle_sec, radius * 0.85)
            Line(points=[cx, cy, x_s, y_s], width=1.2)

class ClockPanel(BoxLayout):
    spinner = ObjectProperty(None)
    clock = ObjectProperty(None)

    def set_city(self, city_name: str):
        """Update spinner text and the clock's timezone."""
        self.spinner.text = city_name
        self.clock.tz_name = CITY_TIMEZONES[city_name]


class DualClockApp(App):
    is_android = BooleanProperty(False)  

    def build(self):
        from kivy.lang import Builder
        self.is_android = (platform == "android")  
        from kivy.properties import ListProperty
        return Builder.load_file("dualclocks.kv")

    def on_start(self):
        # Set default cities (same as you already had)
        self.root.ids.left_panel.set_city("Los Angeles")
        self.root.ids.right_panel.set_city("London")

        # Set the clock face colors AFTER the UI is built (safe place to do it)
        self.root.ids.left_panel.ids.clock.face_color = (1.0, 0.95, 0.85, 1)  # very light orange
        self.root.ids.right_panel.ids.clock.face_color = (0.85, 0.92, 1.0, 1)  # light blue

        # Keep your delta updates
        Clock.schedule_interval(self.update_delta, 1)
        self.update_delta(0)
        
    def request_close(self):              # <-- ADD
        """Close the app (works on Android and desktop)."""
        # Simple and reliable:
        self.stop()

    def update_delta(self, dt):
        left_city = self.root.ids.left_panel.spinner.text
        right_city = self.root.ids.right_panel.spinner.text
        tz_left = CITY_TIMEZONES[left_city]
        tz_right = CITY_TIMEZONES[right_city]

        diff = hours_diff_between(tz_left, tz_right)  # RIGHT - LEFT in hours
        sign = "+" if diff >= 0 else "-"
       
        text = f"{sign}{fmt_hours(abs(diff))} Hours ->"
        self.root.ids.delta_label.text = text

        # Set color based on sign
        if diff >= 0:
            self.root.ids.delta_label.color = (0.2, 0.6, 0.2, 1)  # light green
        else:
            self.root.ids.delta_label.color = (0.8, 0.3, 0.3, 1)  # light red

    def fit_spinner_font(self, spn, min_sp=12, max_sp=24, padding=16):
        """
        Shrink spinner font so the text fits within its width.
        min_sp / max_sp are in 'sp' units; we convert to pixels.
        """
        # Target drawable width (account for a bit of horizontal padding)
        target_w = max(0, spn.width - padding)
        if target_w <= 0 or not spn.text:
            return

        # Convert sp -> pixels for CoreLabel
        lo = sp(min_sp)
        hi = sp(max_sp)
        best = lo

        # Binary search for the largest font that fits
        while lo <= hi:
            mid = (lo + hi) / 2.0
            lbl = CoreLabel(text=spn.text, font_size=mid)
            lbl.refresh()
            tw, th = lbl.texture.size
            if tw <= target_w:
                best = mid
                lo = mid + 0.5
            else:
                hi = mid - 0.5

        # Apply and keep it centered
        spn.font_size = best          # pixels are fine here
        spn.text_size = (spn.width, None)
        spn.halign = 'center'
        spn.valign = 'middle'

if __name__ == "__main__":
    DualClockApp().run()
