from datetime import datetime, timezone
from math import sin, cos, pi

# Try to import ZoneInfo; if unavailable, we fall back gracefully to UTC.
try:
    from zoneinfo import ZoneInfo  # Python 3.9+
except Exception:
    ZoneInfo = None

from kivy.app import App
from kivy.uix.widget import Widget
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.anchorlayout import AnchorLayout
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.uix.spinner import Spinner, SpinnerOption
from kivy.clock import Clock as KivyClock
from kivy.properties import StringProperty, ListProperty, NumericProperty, BooleanProperty
from kivy.graphics import Color, Ellipse, Line
from kivy.core.window import Window
from kivy.metrics import dp
from kivy.logger import Logger

# Global white background
Window.clearcolor = (1, 1, 1, 1)

# A curated set of common IANA time zones (add/remove as needed)
COMMON_TZS = (
    # Americas
    "America/Los_Angeles", "America/Denver", "America/Chicago", "America/New_York",
    "America/Phoenix", "America/Anchorage", "America/Adak", "Pacific/Honolulu",
    "America/Tijuana", "America/Mexico_City", "America/Bogota", "America/Lima",
    "America/Caracas", "America/Santiago", "America/Argentina/Buenos_Aires",
    "America/Sao_Paulo",
    # Europe
    "Europe/London", "Europe/Dublin", "Europe/Lisbon", "Europe/Madrid",
    "Europe/Paris", "Europe/Berlin", "Europe/Rome", "Europe/Zurich",
    "Europe/Amsterdam", "Europe/Stockholm", "Europe/Copenhagen",
    "Europe/Warsaw", "Europe/Athens", "Europe/Helsinki",
    "Europe/Bucharest", "Europe/Moscow",
    # Africa
    "Africa/Casablanca", "Africa/Accra", "Africa/Lagos", "Africa/Johannesburg",
    "Africa/Nairobi",
    # Middle East / Asia
    "Asia/Jerusalem", "Asia/Dubai", "Asia/Tehran", "Asia/Karachi", "Asia/Kolkata",
    "Asia/Dhaka", "Asia/Bangkok", "Asia/Singapore", "Asia/Hong_Kong",
    "Asia/Shanghai", "Asia/Tokyo", "Asia/Seoul",
    # Oceania / Australia
    "Australia/Perth", "Australia/Adelaide", "Australia/Sydney",
    "Pacific/Auckland",
)

def friendly_label_from_tz(tzname: str) -> str:
    """Human-friendly name from tz (last segment, underscores→spaces)."""
    if not tzname:
        return "UTC"
    last = tzname.split("/")[-1]
    return last.replace("_", " ")


def build_friendly_lists(tzs):
    """
    Build mappings so Spinner shows city-only names.
    If a city name appears multiple times, disambiguate with the region in parentheses.
    """
    entries = []
    for tz in tzs:
        parts = tz.split("/")
        city = parts[-1].replace("_", " ")
        region = parts[-2].replace("_", " ") if len(parts) > 1 else ""
        entries.append((tz, city, region))

    # Count city occurrences
    counts = {}
    for _, city, _ in entries:
        counts[city] = counts.get(city, 0) + 1

    # Create final friendly labels (city or "City (Region)" if duplicate)
    items = []
    for tz, city, region in entries:
        label = f"{city} ({region})" if counts[city] > 1 and region else city
        items.append((tz, label))

    tz_to_friendly = {tz: label for tz, label in items}
    friendly_to_tz = {label: tz for tz, label in items}
    friendly_values = tuple(label for _, label in items)
    return tz_to_friendly, friendly_to_tz, friendly_values


TZ_TO_FRIENDLY, FRIENDLY_TO_TZ, FRIENDLY_VALUES = build_friendly_lists(COMMON_TZS)


def _resolve_tz(name: str):
    """Return a tzinfo or None if not available."""
    if ZoneInfo is not None:
        try:
            return ZoneInfo(name)
        except Exception as e:
            Logger.warning(f"AnalogClock: ZoneInfo could not resolve '{name}': {e}")
    return None  # means use UTC fallback


def _offset_seconds_for_tz(tzname: str) -> int:
    """Return the current UTC offset in seconds for the given tz name, or 0 if unknown."""
    tz = _resolve_tz(tzname)
    try:
        if tz is None:
            return 0
        now = datetime.now(tz)
        off = now.utcoffset()
        return int(off.total_seconds()) if off else 0
    except Exception as e:
        Logger.exception(f"AnalogClock: failed to get offset for '{tzname}': {e}")
        return 0


# ---- Light green Spinner styles ----
LIGHT_GREEN_BTN = (0.88, 1.00, 0.88, 1.0)  # button face
LIGHT_GREEN_OPT = (0.92, 1.00, 0.92, 1.0)  # dropdown options
DARK_TEXT = (0.10, 0.10, 0.10, 1.0)
BRIGHT_GREEN = (0.00, 0.80, 0.00, 1.0)
BRIGHT_RED = (0.95, 0.00, 0.00, 1.0)


class LightSpinnerOption(SpinnerOption):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.background_normal = ''
        self.background_down = ''
        self.background_color = LIGHT_GREEN_OPT
        self.color = DARK_TEXT


def style_spinner(sp: Spinner):
    """Apply light green style to a Spinner."""
    sp.background_normal = ''
    sp.background_down = ''
    sp.background_color = LIGHT_GREEN_BTN
    sp.color = DARK_TEXT
    sp.option_cls = LightSpinnerOption


# ---- Arrow widget (canvas-drawn, scalable) ----
class ArrowWidget(Widget):
    direction = StringProperty('right')  # 'right', 'left' (we'll keep it 'right')
    color = ListProperty(BRIGHT_GREEN)
    thickness = NumericProperty(dp(2.0))

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        with self.canvas:
            self._color = Color(rgba=self.color)
            self._shaft = Line(points=[], width=self.thickness, cap='round')
            self._head1 = Line(points=[], width=self.thickness, cap='round')
            self._head2 = Line(points=[], width=self.thickness, cap='round')

        self.bind(
            pos=self._update, size=self._update,
            color=self._apply_color, thickness=self._apply_thickness,
            direction=lambda *_: self._update()
        )

    def _apply_color(self, *_):
        self._color.rgba = self.color

    def _apply_thickness(self, *_):
        self._shaft.width = self.thickness
        self._head1.width = self.thickness
        self._head2.width = self.thickness
        self._update()

    def _update(self, *_):
        if self.width <= 0 or self.height <= 0:
            return
        pad = dp(6)
        head = min(dp(14), self.width * 0.28)
        y = self.y + self.height / 2.0
        xL = self.x + pad
        xR = self.right - pad

        if self.direction == 'right':
            # Shaft
            self._shaft.points = [xL, y, xR - head, y]
            # Head (V-shaped)
            self._head1.points = [xR, y, xR - head, y + head * 0.6]
            self._head2.points = [xR, y, xR - head, y - head * 0.6]
        else:  # 'left'
            self._shaft.points = [xR, y, xL + head, y]
            self._head1.points = [xL, y, xL + head, y + head * 0.6]
            self._head2.points = [xL, y, xL + head, y - head * 0.6]


class AnalogClock(Widget):
    # Public properties
    tzname = StringProperty("UTC")
    label = StringProperty("Zone")

    # Colors
    face_color = ListProperty([1, 1, 1, 1])  # clock face fill
    tick_color = ListProperty([0.1, 0.1, 0.1, 1])  # hour tick color (dark)
    hour_hand_color = ListProperty([0.1, 0.1, 0.1, 1])
    minute_hand_color = ListProperty([0.1, 0.1, 0.1, 1])
    second_hand_color = ListProperty([0.8, 0.0, 0.0, 1])

    # Time state (floats for stepped motion)
    hour = NumericProperty(0.0)
    minute = NumericProperty(0.0)
    second = NumericProperty(0.0)

    # Flag to log tz fallback warning once
    _warned_tz = BooleanProperty(False)

    def __init__(self, **kwargs):
        # Ensure a visible default size if none provided
        if "size" not in kwargs and ("size_hint" not in kwargs or kwargs.get("size_hint") is None):
            kwargs.setdefault("size_hint", (None, None))
            kwargs.setdefault("size", (dp(260), dp(260)))
        super().__init__(**kwargs)

        # --- FACE (behind) ---
        with self.canvas.before:
            self._face_color_instr = Color(rgba=self.face_color)
            self._face_ellipse = Ellipse()

        # --- TICKS + HANDS (main) ---
        with self.canvas:
            # Minute ticks (60) - light gray, thin
            self._minute_tick_color_instr = Color(rgba=(0.7, 0.7, 0.7, 1))
            self._minute_ticks = [Line(points=[0, 0, 0, 0], width=dp(1)) for _ in range(60)]

            # Hour ticks (12) - darker, thicker
            self._tick_color_instr = Color(rgba=self.tick_color)
            self._tick_marks = [Line(points=[0, 0, 0, 0], width=dp(2)) for _ in range(12)]

            # Hands: hour, minute, second
            self._hour_color_instr = Color(rgba=self.hour_hand_color)
            self._hour_hand = Line(points=[], width=dp(4), cap='round')

            self._minute_color_instr = Color(rgba=self.minute_hand_color)
            self._minute_hand = Line(points=[], width=dp(3), cap='round')

            self._second_color_instr = Color(rgba=self.second_hand_color)
            self._second_hand = Line(points=[], width=dp(1.5), cap='round')

        # --- Center hub (top) ---
        with self.canvas.after:
            self._hub_color_instr = Color(rgba=(0.1, 0.1, 0.1, 1))
            self._hub = Ellipse(size=(dp(10), dp(10)))

        # --- Numerals (12 / 3 / 6 / 9) as child Labels ---
        self._lbl12 = Label(text='12', color=DARK_TEXT, font_size='20sp', size_hint=(None, None))
        self._lbl3 = Label(text='3', color=DARK_TEXT, font_size='20sp', size_hint=(None, None))
        self._lbl6 = Label(text='6', color=DARK_TEXT, font_size='20sp', size_hint=(None, None))
        self._lbl9 = Label(text='9', color=DARK_TEXT, font_size='20sp', size_hint=(None, None))
        for lbl in (self._lbl12, self._lbl3, self._lbl6, self._lbl9):
            lbl.texture_update()
            lbl.size = lbl.texture_size
            self.add_widget(lbl)

        # Bind updates
        self.bind(
            pos=self._update_geometry,
            size=self._update_geometry,
            face_color=self._apply_face_color,
            tick_color=self._apply_tick_color,
            hour_hand_color=self._apply_hour_color,
            minute_hand_color=self._apply_minute_color,
            second_hand_color=self._apply_second_color,
            hour=self._update_hands,
            minute=self._update_hands,
            second=self._update_hands,
        )

        # Resolve timezone
        self._tz = _resolve_tz(self.tzname)

        # Start timer: STEP ONCE PER SECOND
        self._evt = KivyClock.schedule_interval(self._update_time, 1.0)

        # Initial draw
        self._update_geometry()
        self._update_time(0)

    # ----- Color updaters -----
    def _apply_face_color(self, *_):
        self._face_color_instr.rgba = self.face_color

    def _apply_tick_color(self, *_):
        self._tick_color_instr.rgba = self.tick_color

    def _apply_hour_color(self, *_):
        self._hour_color_instr.rgba = self.hour_hand_color

    def _apply_minute_color(self, *_):
        self._minute_color_instr.rgba = self.minute_hand_color

    def _apply_second_color(self, *_):
        self._second_color_instr.rgba = self.second_hand_color

    # ----- Geometry (face, ticks, hub, numerals) -----
    def _update_geometry(self, *_):
        inset = dp(6)
        d = max(0.0, min(self.width, self.height) - 2 * inset)
        cx, cy = self.center
        radius = d / 2.0

        # Face
        self._face_ellipse.size = (d, d)
        self._face_ellipse.pos = (cx - radius, cy - radius)

        # Minute ticks (skip where hour ticks will be)
        for j, mt in enumerate(self._minute_ticks):
            angle = 2 * pi * j / 60.0
            if j % 5 == 0:
                # Hide minute tick at hour positions (set zero-length)
                x = cx + 0.90 * radius * sin(angle)
                y = cy + 0.90 * radius * cos(angle)
                mt.points = [x, y, x, y]
            else:
                x1 = cx + 0.88 * radius * sin(angle)
                y1 = cy + 0.88 * radius * cos(angle)
                x2 = cx + 0.97 * radius * sin(angle)
                y2 = cy + 0.97 * radius * cos(angle)
                mt.points = [x1, y1, x2, y2]

        # Hour ticks (12)
        for i, tick in enumerate(self._tick_marks):
            angle = 2 * pi * i / 12.0
            x1 = cx + 0.80 * radius * sin(angle)
            y1 = cy + 0.80 * radius * cos(angle)
            x2 = cx + 0.98 * radius * sin(angle)
            y2 = cy + 0.98 * radius * cos(angle)
            tick.points = [x1, y1, x2, y2]

        # Hub circle
        hub_r = dp(5)
        self._hub.size = (2 * hub_r, 2 * hub_r)
        self._hub.pos = (cx - hub_r, cy - hub_r)

        # Numeral positions
        r_numeral = 0.72 * radius
        self._lbl12.center = (cx, cy + r_numeral)
        self._lbl3.center = (cx + r_numeral, cy)
        self._lbl6.center = (cx, cy - r_numeral)
        self._lbl9.center = (cx - r_numeral, cy)

        # Update hands with new geometry
        self._update_hands()

    # ----- Time & hands -----
    def on_tzname(self, *_):
        self._tz = _resolve_tz(self.tzname)
        self._warned_tz = False  # allow warning again if needed

    def on_parent(self, *args):
        # Stop the timer if widget is removed from the tree
        if self.parent is None and getattr(self, "_evt", None):
            self._evt.cancel()
            self._evt = None

    def _update_time(self, dt):
        try:
            if self._tz is not None:
                now = datetime.now(self._tz)
            else:
                if not self._warned_tz:
                    Logger.warning(
                        f"AnalogClock: Falling back to UTC for '{self.tzname}'. "
                        f"Install 'tzdata' to enable IANA timezones."
                    )
                self._warned_tz = True
                now = datetime.now(timezone.utc)
        except Exception as e:
            # Absolute safety net—never crash the app
            Logger.exception(f"AnalogClock: time update failed for '{self.tzname}': {e}")
            now = datetime.now(timezone.utc)

        # Stepped second hand (updates once per second)
        self.second = now.second
        self.minute = now.minute + self.second / 60.0
        self.hour = (now.hour % 12) + self.minute / 60.0

    def _update_hands(self, *_):
        inset = dp(6)
        d = max(0.0, min(self.width, self.height) - 2 * inset)
        if d <= 0:
            return
        cx, cy = self.center
        radius = d / 2.0

        # Angles (0 at 12 o'clock, clockwise)
        a_h = 2 * pi * (self.hour / 12.0)
        a_m = 2 * pi * (self.minute / 60.0)
        a_s = 2 * pi * (self.second / 60.0)

        # Endpoints
        hx = cx + 0.50 * radius * sin(a_h)
        hy = cy + 0.50 * radius * cos(a_h)
        mx = cx + 0.75 * radius * sin(a_m)
        my = cy + 0.75 * radius * cos(a_m)
        sx = cx + 0.85 * radius * sin(a_s)
        sy = cy + 0.85 * radius * cos(a_s)

        self._hour_hand.points = [cx, cy, hx, hy]
        self._minute_hand.points = [cx, cy, mx, my]
        self._second_hand.points = [cx, cy, sx, sy]


class DualClocksApp(App):
    def build(self):
        # ---- Root: vertical layout with a top bar + content (prevents overlap) ----
        root = BoxLayout(orientation='vertical')

        # ---- Top bar (dedicated area for the close button) ----
        top_bar = AnchorLayout(
            anchor_x='right', anchor_y='top',
            size_hint=(1, None),
            height=dp(56)  # standard toolbar height
        )
        close_button = Button(
            text='X',
            size_hint=(None, None),
            size=(dp(40), dp(40)),
        )
        close_button.bind(on_release=lambda *_: App.get_running_app().stop())
        top_bar.add_widget(close_button)

        # ---- The row of clocks and center difference column ----
        row = BoxLayout(
            orientation='horizontal',
            size_hint=(1, 1),   # fill remaining space below the top bar
            padding=dp(16),
            spacing=dp(24),
        )

        # LEFT clock (defaults to Los Angeles)
        self.left_clock = AnalogClock(
            tzname="America/Los_Angeles",
            label="San Francisco",
            face_color=[1.00, 0.82, 0.60, 1.0],
            size_hint=(1, 1),  # responsive
        )
        left_col = BoxLayout(orientation='vertical', spacing=dp(8))
        left_anchor = AnchorLayout(anchor_x='center', anchor_y='center')
        left_anchor.add_widget(self.left_clock)
        left_initial_label = TZ_TO_FRIENDLY.get(
            self.left_clock.tzname, friendly_label_from_tz(self.left_clock.tzname)
        )
        self.left_spinner = Spinner(
            text=left_initial_label,
            values=FRIENDLY_VALUES,
            size_hint=(1, None),  # responsive width
            height=dp(38)
        )
        self.left_spinner.bind(text=self._on_left_city_change)
        style_spinner(self.left_spinner)
        left_col.add_widget(left_anchor)
        left_col.add_widget(self.left_spinner)

        # RIGHT clock (defaults to London)
        self.right_clock = AnalogClock(
            tzname="Europe/London",
            label="London",
            face_color=[0.78, 0.86, 1.00, 1.0],
            size_hint=(1, 1),  # responsive
        )
        right_col = BoxLayout(orientation='vertical', spacing=dp(8))
        right_anchor = AnchorLayout(anchor_x='center', anchor_y='center')
        right_anchor.add_widget(self.right_clock)
        right_initial_label = TZ_TO_FRIENDLY.get(
            self.right_clock.tzname, friendly_label_from_tz(self.right_clock.tzname)
        )
        self.right_spinner = Spinner(
            text=right_initial_label,
            values=FRIENDLY_VALUES,
            size_hint=(1, None),  # responsive width
            height=dp(38)
        )
        self.right_spinner.bind(text=self._on_right_city_change)
        style_spinner(self.right_spinner)
        right_col.add_widget(right_anchor)
        right_col.add_widget(self.right_spinner)

        # CENTER column: signed difference text + arrow
        center_col = BoxLayout(orientation='vertical', size_hint=(None, 1), width=dp(220))
        center_col.add_widget(Widget())  # spacer to align with spinners row
        center_box = BoxLayout(orientation='horizontal', size_hint=(1, None), height=dp(38), spacing=dp(8))
        self.center_diff_label = Label(
            text="", color=BRIGHT_GREEN,
            font_size='16sp',
            size_hint=(1, 1),
            halign='right', valign='middle'
        )
        self.center_diff_label.bind(size=lambda lbl, _:
                                    setattr(lbl, "text_size", (lbl.width, None)))
        self.center_arrow = ArrowWidget(size_hint=(None, 1), width=dp(42))
        center_box.add_widget(self.center_diff_label)
        center_box.add_widget(self.center_arrow)
        center_col.add_widget(center_box)

        # Assemble row (left | center | right)
        row.add_widget(left_col)
        row.add_widget(center_col)
        row.add_widget(right_col)

        # Add bar and content to root
        root.add_widget(top_bar)
        root.add_widget(row)

        # Initial difference + periodic updates
        self._update_diff_label(0)
        KivyClock.schedule_interval(self._update_diff_label, 1.0)

        return root

    # Spinner handlers: map friendly text back to IANA tz, update clock + diff UI
    def _on_left_city_change(self, spinner, friendly_label):
        tz = FRIENDLY_TO_TZ.get(friendly_label)
        if not tz:
            return
        self.left_clock.tzname = tz
        self.left_clock.label = friendly_label
        self._update_diff_label(0)

    def _on_right_city_change(self, spinner, friendly_label):
        tz = FRIENDLY_TO_TZ.get(friendly_label)
        if not tz:
            return
        self.right_clock.tzname = tz
        self.right_clock.label = friendly_label
        self._update_diff_label(0)

    def _format_signed_diff_text(self, seconds_b_minus_a: int) -> str:
        # Signed left→right: positive means right is ahead of left
        secs = int(seconds_b_minus_a)
        sign = "+" if secs > 0 else "-" if secs < 0 else ""
        secs = abs(secs)
        hours = secs // 3600
        minutes = (secs % 3600) // 60
        if minutes == 0:
            return f"{sign}{hours} Hours"
        else:
            return f"{sign}{hours} Hours {minutes} Minutes"

    def _update_diff_label(self, dt):
        # Compute current UTC offsets
        off_left = _offset_seconds_for_tz(self.left_clock.tzname)
        off_right = _offset_seconds_for_tz(self.right_clock.tzname)

        # Right minus left (signed)
        delta = off_right - off_left

        # Text (e.g., "+8 Hours" or "-3 Hours 30 Minutes")
        text = self._format_signed_diff_text(delta)
        self.center_diff_label.text = text

        # Color + arrow (arrow always points RIGHT; color communicates lead/lag)
        if delta > 0:
            self.center_diff_label.color = BRIGHT_GREEN
            self.center_arrow.color = BRIGHT_GREEN
            self.center_arrow.direction = 'right'
            self.center_arrow.opacity = 1.0
        elif delta < 0:
            self.center_diff_label.color = BRIGHT_RED
            self.center_arrow.color = BRIGHT_RED
            # Keep the arrow pointing right even when negative
            self.center_arrow.direction = 'right'
            self.center_arrow.opacity = 1.0
        else:
            # Same time: neutral (hide arrow)
            self.center_diff_label.color = DARK_TEXT
            self.center_arrow.opacity = 0.0


if __name__ == "__main__":
    DualClocksApp().run()
