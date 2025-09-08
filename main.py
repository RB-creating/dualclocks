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
from kivy.clock import Clock as KivyClock, Clock
from kivy.properties import StringProperty, ListProperty, NumericProperty, BooleanProperty
from kivy.graphics import Color, Ellipse, Line
from kivy.core.window import Window
from kivy.metrics import dp
from kivy.logger import Logger

# -------- Global UI constants --------
Window.clearcolor = (1, 1, 1, 1)   # white background
COMPACT_BREAKPOINT_DP = 740        # ~phones in landscape

# ---- Time zone list & helpers ----
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
    if not tzname:
        return "UTC"
    last = tzname.split("/")[-1]
    return last.replace("_", " ")

def build_friendly_lists(tzs):
    entries = []
    for tz in tzs:
        parts = tz.split("/")
        city = parts[-1].replace("_", " ")
        region = parts[-2].replace("_", " ") if len(parts) > 1 else ""
        entries.append((tz, city, region))

    counts = {}
    for _, city, _ in entries:
        counts[city] = counts.get(city, 0) + 1

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
    if ZoneInfo is not None:
        try:
            return ZoneInfo(name)
        except Exception as e:
            Logger.warning(f"AnalogClock: ZoneInfo could not resolve '{name}': {e}")
    return None  # use UTC fallback

def _offset_seconds_for_tz(tzname: str) -> int:
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
LIGHT_GREEN_BTN = (0.88, 1.00, 0.88, 1.0)
LIGHT_GREEN_OPT = (0.92, 1.00, 0.92, 1.0)
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
    sp.background_normal = ''
    sp.background_down = ''
    sp.background_color = LIGHT_GREEN_BTN
    sp.color = DARK_TEXT
    sp.option_cls = LightSpinnerOption
    # Avoid features that may differ by Kivy version on Android (e.g., shorten)
    # Keep text within spinner width if supported
    try:
        sp.text_size = (sp.width - dp(8), None)
        sp.bind(size=lambda s, *_: setattr(s, "text_size", (s.width - dp(8), None)))
    except Exception:
        pass

# ---- Arrow widget ----
class ArrowWidget(Widget):
    direction = StringProperty('right')  # keep 'right'
    color = ListProperty(BRIGHT_GREEN)
    thickness = NumericProperty(dp(2.0))

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        with self.canvas:
            self._color = Color(rgba=self.color)
            self._shaft = Line(points=[], width=self.thickness, cap='round')
            self._head1 = Line(points=[], width=self.thickness, cap='round')
            self._head2 = Line(points=[], width=self.thickness, cap='round')
        self.bind(pos=self._update, size=self._update,
                  color=self._apply_color, thickness=self._apply_thickness)

    def _apply_color(self, *_): self._color.rgba = self.color
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
        self._shaft.points = [xL, y, xR - head, y]
        self._head1.points = [xR, y, xR - head, y + head * 0.6]
        self._head2.points = [xR, y, xR - head, y - head * 0.6]

# ---- Analog clock widget ----
class AnalogClock(Widget):
    tzname = StringProperty("UTC")
    label = StringProperty("Zone")
    face_color = ListProperty([1, 1, 1, 1])
    tick_color = ListProperty([0.1, 0.1, 0.1, 1])
    hour_hand_color = ListProperty([0.1, 0.1, 0.1, 1])
    minute_hand_color = ListProperty([0.1, 0.1, 0.1, 1])
    second_hand_color = ListProperty([0.8, 0.0, 0.0, 1])

    hour = NumericProperty(0.0)
    minute = NumericProperty(0.0)
    second = NumericProperty(0.0)
    _warned_tz = BooleanProperty(False)

    def __init__(self, **kwargs):
        if "size" not in kwargs and ("size_hint" not in kwargs or kwargs.get("size_hint") is None):
            kwargs.setdefault("size_hint", (None, None))
            kwargs.setdefault("size", (dp(240), dp(240)))  # slightly smaller default
        super().__init__(**kwargs)

        with self.canvas.before:
            self._face_color_instr = Color(rgba=self.face_color)
            self._face_ellipse = Ellipse()

        with self.canvas:
            self._minute_tick_color_instr = Color(rgba=(0.7, 0.7, 0.7, 1))
            self._minute_ticks = [Line(points=[0, 0, 0, 0], width=dp(1)) for _ in range(60)]
            self._tick_color_instr = Color(rgba=self.tick_color)
            self._tick_marks = [Line(points=[0, 0, 0, 0], width=dp(2)) for _ in range(12)]
            self._hour_color_instr = Color(rgba=self.hour_hand_color)
            self._hour_hand = Line(points=[], width=dp(4), cap='round')
            self._minute_color_instr = Color(rgba=self.minute_hand_color)
            self._minute_hand = Line(points=[], width=dp(3), cap='round')
            self._second_color_instr = Color(rgba=self.second_hand_color)
            self._second_hand = Line(points=[], width=dp(1.5), cap='round')

        with self.canvas.after:
            self._hub_color_instr = Color(rgba=(0.1, 0.1, 0.1, 1))
            self._hub = Ellipse(size=(dp(10), dp(10)))

        # Numerals
        self._lbl12 = Label(text='12', color=DARK_TEXT, font_size='18sp', size_hint=(None, None))
        self._lbl3  = Label(text='3',  color=DARK_TEXT, font_size='18sp', size_hint=(None, None))
        self._lbl6  = Label(text='6',  color=DARK_TEXT, font_size='18sp', size_hint=(None, None))
        self._lbl9  = Label(text='9',  color=DARK_TEXT, font_size='18sp', size_hint=(None, None))
        for lbl in (self._lbl12, self._lbl3, self._lbl6, self._lbl9):
            lbl.texture_update()
            lbl.size = lbl.texture_size
            self.add_widget(lbl)

        self.bind(pos=self._update_geometry, size=self._update_geometry,
                  face_color=self._apply_face_color, tick_color=self._apply_tick_color,
                  hour_hand_color=self._apply_hour_color, minute_hand_color=self._apply_minute_color,
                  second_hand_color=self._apply_second_color,
                  hour=self._update_hands, minute=self._update_hands, second=self._update_hands)

        self._tz = _resolve_tz(self.tzname)
        self._evt = KivyClock.schedule_interval(self._update_time, 1.0)
        self._update_geometry()
        self._update_time(0)

    def _apply_face_color(self, *_):   self._face_color_instr.rgba = self.face_color
    def _apply_tick_color(self, *_):   self._tick_color_instr.rgba = self.tick_color
    def _apply_hour_color(self, *_):   self._hour_color_instr.rgba = self.hour_hand_color
    def _apply_minute_color(self, *_): self._minute_color_instr.rgba = self.minute_hand_color
    def _apply_second_color(self, *_): self._second_color_instr.rgba = self.second_hand_color

    def _update_geometry(self, *_):
        inset = dp(6)
        d = max(0.0, min(self.width, self.height) - 2 * inset)
        cx, cy = self.center
        radius = d / 2.0

        self._face_ellipse.size = (d, d)
        self._face_ellipse.pos = (cx - radius, cy - radius)

        for j, mt in enumerate(self._minute_ticks):
            angle = 2 * pi * j / 60.0
            if j % 5 == 0:
                x = cx + 0.90 * radius * sin(angle)
                y = cy + 0.90 * radius * cos(angle)
                mt.points = [x, y, x, y]
            else:
                x1 = cx + 0.88 * radius * sin(angle)
                y1 = cy + 0.88 * radius * cos(angle)
                x2 = cx + 0.97 * radius * sin(angle)
                y2 = cy + 0.97 * radius * cos(angle)
                mt.points = [x1, y1, x2, y2]

        for i, tick in enumerate(self._tick_marks):
            angle = 2 * pi * i / 12.0
            x1 = cx + 0.80 * radius * sin(angle)
            y1 = cy + 0.80 * radius * cos(angle)
            x2 = cx + 0.98 * radius * sin(angle)
            y2 = cy + 0.98 * radius * cos(angle)
            tick.points = [x1, y1, x2, y2]

        hub_r = dp(5)
        self._hub.size = (2 * hub_r, 2 * hub_r)
        self._hub.pos = (cx - hub_r, cy - hub_r)

        r_numeral = 0.72 * radius
        self._lbl12.center = (cx,            cy + r_numeral)
        self._lbl3.center  = (cx + r_numeral, cy)
        self._lbl6.center  = (cx,            cy - r_numeral)
        self._lbl9.center  = (cx - r_numeral, cy)

        self._update_hands()

    def on_tzname(self, *_):
        self._tz = _resolve_tz(self.tzname)
        self._warned_tz = False

    def on_parent(self, *args):
        if self.parent is None and getattr(self, "_evt", None):
            self._evt.cancel()
            self._evt = None

    def _update_time(self, dt):
        try:
            if self._tz is not None:
                now = datetime.now(self._tz)
            else:
                if not self._warned_tz:
                    Logger.warning(f"AnalogClock: Falling back to UTC for '{self.tzname}'. "
                                   f"Install 'tzdata' to enable IANA timezones.")
                self._warned_tz = True
                now = datetime.now(timezone.utc)
        except Exception as e:
            Logger.exception(f"AnalogClock: time update failed for '{self.tzname}': {e}")
            now = datetime.now(timezone.utc)

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

        a_h = 2 * pi * (self.hour / 12.0)
        a_m = 2 * pi * (self.minute / 60.0)
        a_s = 2 * pi * (self.second / 60.0)

        hx = cx + 0.50 * radius * sin(a_h)
        hy = cy + 0.50 * radius * cos(a_h)
        mx = cx + 0.75 * radius * sin(a_m)
        my = cy + 0.75 * radius * cos(a_m)
        sx = cx + 0.85 * radius * sin(a_s)
        sy = cy + 0.85 * radius * cos(a_s)

        self._hour_hand.points = [cx, cy, hx, hy]
        self._minute_hand.points = [cx, cy, mx, my]
        self._second_hand.points = [cx, cy, sx, sy]

# ---- App ----
class DualClocksApp(App):
    def build(self):
        # Root vertical: top bar + content
        root = BoxLayout(orientation='vertical')

        # Top bar with some internal padding so X isn’t under the status bar
        top_bar = AnchorLayout(anchor_x='right', anchor_y='top',
                               size_hint=(1, None), height=dp(56))
        top_inner = BoxLayout(size_hint=(1, 1), padding=[0, dp(8), dp(8), 0])
        close_button = Button(text='X', size_hint=(None, None), size=(dp(40), dp(40)))
        close_button.bind(on_release=lambda *_: App.get_running_app().stop())
        right_holder = AnchorLayout(anchor_x='right', anchor_y='top')
        right_holder.add_widget(close_button)
        top_inner.add_widget(right_holder)
        top_bar.add_widget(top_inner)

        # Content container – we rebuild into landscape/portrait AFTER first frame
        self.content = BoxLayout(orientation='vertical', size_hint=(1, 1))

        # Make UI pieces
        self._make_columns()

        # Assemble
        root.add_widget(top_bar)
        root.add_widget(self.content)

        # Start timers/labels
        self._update_diff_label(0)
        KivyClock.schedule_interval(self._update_diff_label, 1.0)

        # Defer layout wiring until window is ready (avoids early-creation issues on Android)
        Clock.schedule_once(self._post_build_init, 0)

        return root

    def _post_build_init(self, dt):
        # Build first layout and then react to size/orientation changes
        self._rebuild_content()
        Window.bind(size=lambda *_: self._rebuild_content())

    # Build reusable left/right/center pieces once
    def _make_columns(self):
        # LEFT
        self.left_clock = AnalogClock(
            tzname="America/Los_Angeles",
            label="San Francisco",
            face_color=[1.00, 0.82, 0.60, 1.0],
            size_hint=(1, 1),
        )
        left_initial_label = TZ_TO_FRIENDLY.get(
            self.left_clock.tzname, friendly_label_from_tz(self.left_clock.tzname)
        )
        self.left_spinner = Spinner(
            text=left_initial_label, values=FRIENDLY_VALUES,
            size_hint=(1, None), height=dp(36)
        )
        self.left_spinner.bind(text=self._on_left_city_change)
        style_spinner(self.left_spinner)
        self.left_col = BoxLayout(orientation='vertical', spacing=dp(8))
        left_anchor = AnchorLayout(anchor_x='center', anchor_y='center')
        left_anchor.add_widget(self.left_clock)
        self.left_col.add_widget(left_anchor)
        self.left_col.add_widget(self.left_spinner)

        # RIGHT
        self.right_clock = AnalogClock(
            tzname="Europe/London",
            label="London",
            face_color=[0.78, 0.86, 1.00, 1.0],
            size_hint=(1, 1),
        )
        right_initial_label = TZ_TO_FRIENDLY.get(
            self.right_clock.tzname, friendly_label_from_tz(self.right_clock.tzname)
        )
        self.right_spinner = Spinner(
            text=right_initial_label, values=FRIENDLY_VALUES,
            size_hint=(1, None), height=dp(36)
        )
        self.right_spinner.bind(text=self._on_right_city_change)
        style_spinner(self.right_spinner)
        self.right_col = BoxLayout(orientation='vertical', spacing=dp(8))
        right_anchor = AnchorLayout(anchor_x='center', anchor_y='center')
        right_anchor.add_widget(self.right_clock)
        self.right_col.add_widget(right_anchor)
        self.right_col.add_widget(self.right_spinner)

        # CENTER (diff + arrow)
        self.center_diff_label = Label(
            text="", color=BRIGHT_GREEN, font_size='16sp',
            size_hint=(1, 1), halign='right', valign='middle'
        )
        self.center_diff_label.bind(size=lambda lbl, _:
                                    setattr(lbl, "text_size", (lbl.width, None)))
        self.center_arrow = ArrowWidget(size_hint=(None, 1), width=dp(42))
        self.center_box = BoxLayout(orientation='horizontal', size_hint=(None, None),
                                    height=dp(36), spacing=dp(8), width=dp(150))
        self.center_box.add_widget(self.center_diff_label)
        self.center_box.add_widget(self.center_arrow)

        # For landscape we place center_box inside a column to center vertically
        self.center_col = BoxLayout(orientation='vertical', size_hint=(None, 1), width=dp(150))
        self.center_col.add_widget(Widget())        # spacer
        self.center_col.add_widget(self.center_box)

    # Rebuild content when orientation changes
    def _rebuild_content(self):
        if not hasattr(self, "content") or self.content is None:
            return
        self.content.clear_widgets()
        w, h = Window.size
        landscape = w >= h

        if landscape:
            row = BoxLayout(orientation='horizontal', size_hint=(1, 1),
                            padding=dp(12), spacing=dp(16))
            # Keep center fairly narrow so clocks have space
            self.center_col.width = dp(140)
            self.center_box.width = dp(140)
            row.add_widget(self.left_col)
            row.add_widget(self.center_col)
            row.add_widget(self.right_col)
            self.content.add_widget(row)
        else:
            col = BoxLayout(orientation='vertical', size_hint=(1, 1),
                            padding=dp(12), spacing=dp(12))
            # Portrait: just place the center row between the clocks
            self.center_box.size_hint = (1, None)
            self.center_box.width = 0
            col.add_widget(self.left_col)
            col.add_widget(self.center_box)
            col.add_widget(self.right_col)
            self.content.add_widget(col)

        # Apply compact tweaks
        self._apply_responsive()

    # Spinner handlers
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

    # Time difference / arrow
    def _format_signed_diff_text(self, seconds_b_minus_a: int) -> str:
        secs = int(seconds_b_minus_a)
        sign = "+" if secs > 0 else "-" if secs < 0 else ""
        secs = abs(secs)
        hours = secs // 3600
        minutes = (secs % 3600) // 60
        return f"{sign}{hours} Hours" if minutes == 0 else f"{sign}{hours} Hours {minutes} Minutes"

    def _update_diff_label(self, dt):
        off_left = _offset_seconds_for_tz(self.left_clock.tzname)
        off_right = _offset_seconds_for_tz(self.right_clock.tzname)
        delta = off_right - off_left

        self.center_diff_label.text = self._format_signed_diff_text(delta)

        if delta > 0:
            self.center_diff_label.color = BRIGHT_GREEN
            self.center_arrow.color = BRIGHT_GREEN
            self.center_arrow.direction = 'right'
            self.center_arrow.opacity = 1.0
        elif delta < 0:
            self.center_diff_label.color = BRIGHT_RED
            self.center_arrow.color = BRIGHT_RED
            self.center_arrow.direction = 'right'
            self.center_arrow.opacity = 1.0
        else:
            self.center_diff_label.color = DARK_TEXT
            self.center_arrow.opacity = 0.0

    # Compact tweaks
    def _apply_responsive(self):
        try:
            w, _ = Window.size
            compact = w <= dp(COMPACT_BREAKPOINT_DP)
            for sp in (getattr(self, "left_spinner", None), getattr(self, "right_spinner", None)):
                if sp:
                    sp.height = dp(34) if compact else dp(36)
                    sp.font_size = '14sp' if compact else '16sp'
        except Exception as e:
            Logger.warning(f"Responsive tweak skipped: {e}")

if __name__ == "__main__":
    DualClocksApp().run()
