#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# =====================================================================
# === Crash popup installer (put this at the VERY TOP of main.py) =====
# Shows a scrollable popup with the traceback for any uncaught exception.
# Also writes the traceback to <app.user_data_dir>/last_crash.txt.
# Remove when you're done debugging.
# =====================================================================

import sys, os, traceback, threading

def _install_crash_popup():
    from kivy.clock import Clock

    # Resolve a writable path early (before App is created)
    def _get_user_data_dir_fallback():
        try:
            from kivy.app import App
            app = App.get_running_app()
            if app and getattr(app, "user_data_dir", None):
                return app.user_data_dir
        except Exception:
            pass
        # Fallback to HOME; on Android this is under /data/data/<pkg>/files after App init
        return os.path.expanduser("~")

    def _write_last_crash(msg: str):
        try:
            base = _get_user_data_dir_fallback()
            os.makedirs(base, exist_ok=True)
            path = os.path.join(base, "last_crash.txt")
            with open(path, "w", encoding="utf-8") as f:
                f.write(msg)
        except Exception:
            # Don't let logging failures crash the app
            pass

    def _show_popup_async(msg: str):
        # Defer UI creation to the next frame (ensures Window/UI exists)
        def _do_show(_dt):
            try:
                from kivy.uix.popup import Popup
                from kivy.uix.label import Label
                from kivy.uix.scrollview import ScrollView
                from kivy.uix.boxlayout import BoxLayout
                from kivy.uix.button import Button
                from kivy.metrics import dp
                from kivy.core.clipboard import Clipboard

                # Root container
                root = BoxLayout(orientation="vertical", spacing=dp(8), padding=dp(8))

                # Scrollable traceback text
                lbl = Label(
                    text=msg,
                    font_size="12sp",
                    size_hint=(1, None),
                    markup=False,
                    halign="left",
                    valign="top",
                )
                # Make label tall so it can scroll
                def _sync_height(*_):
                    # Ensure we don't end up with 0 height before first texture update
                    h = lbl.texture_size[1] if lbl.texture_size[1] > 0 else dp(400)
                    lbl.height = max(h, dp(1200))
                    lbl.text_size = (lbl.width - dp(16), None)
                lbl.bind(texture_size=_sync_height, size=_sync_height)

                scroller = ScrollView(size_hint=(1, 1), bar_width=dp(6))
                scroller.add_widget(lbl)

                # Buttons
                btns = BoxLayout(size_hint=(1, None), height=dp(48), spacing=dp(8))
                copy_btn = Button(text="Copy", size_hint=(1, 1))
                close_btn = Button(text="Close", size_hint=(1, 1))
                btns.add_widget(copy_btn)
                btns.add_widget(close_btn)

                root.add_widget(scroller)
                root.add_widget(btns)

                popup = Popup(
                    title="Python Error",
                    content=root,
                    size_hint=(0.95, 0.95),
                    auto_dismiss=False,
                )

                def _copy(_):
                    try:
                        Clipboard.copy(msg)
                    except Exception:
                        pass

                copy_btn.bind(on_release=_copy)
                close_btn.bind(on_release=lambda *_: popup.dismiss())

                popup.open()
            except Exception:
                # Last resort: print to stdout (visible in logcat)
                print(msg)
        Clock.schedule_once(_do_show, 0)

    def _format_exc(exc_type, exc, tb):
        msg = "".join(traceback.format_exception(exc_type, exc, tb))
        # Trim super long traces
        return msg[-8000:]

    # --- Global excepthook (main thread) ---
    def _global_excepthook(exc_type, exc, tb):
        msg = _format_exc(exc_type, exc, tb)
        _write_last_crash(msg)
        _show_popup_async(msg)
        print(msg)

    sys.excepthook = _global_excepthook

    # --- Thread excepthook (Python 3.8+) ---
    if hasattr(threading, "excepthook"):
        def _thread_excepthook(args):
            _global_excepthook(args.exc_type, args.exc_value, args.exc_traceback)
        threading.excepthook = _thread_excepthook

    # --- Catch many Kivy callback errors via ExceptionManager ---
    try:
        from kivy.base import ExceptionManager, ExceptionHandler

        class _PopupExceptionHandler(ExceptionHandler):
            def handle_exception(self, inst):
                _global_excepthook(type(inst), inst, inst.__traceback__)
                # Allow Kivy to continue handling as usual
                return ExceptionManager.PASS

        ExceptionManager.add_handler(_PopupExceptionHandler())
    except Exception:
        # If Kivy isn't ready yet, it's fine—global hooks still work
        pass

# Install immediately when this file is imported
_install_crash_popup()

# ========================= End crash popup installer ==========================


# =====================================================================
# === Timezone helper (zoneinfo with pytz fallback; never crashes) ====
# Keep tzdata in buildozer.spec requirements if you use zoneinfo:
#   requirements = python3,kivy==2.3.0,tzdata
# Optionally add pytz for extra fallback:
#   requirements = python3,kivy==2.3.0,tzdata,pytz
# =====================================================================

try:
    from zoneinfo import ZoneInfo  # Python 3.9+
    _ZONEINFO_OK = True
except Exception:
    ZoneInfo = None
    _ZONEINFO_OK = False

def get_tz(name: str):
    """Return a tzinfo for 'name' using zoneinfo or pytz; fallback to UTC."""
    if _ZONEINFO_OK:
        try:
            return ZoneInfo(name)
        except Exception:
            pass
    try:
        import pytz
        return pytz.timezone(name)
    except Exception:
        pass
    from datetime import timezone
    return timezone.utc


# =====================================================================
# === Demo Kivy app (you can replace this section with your own) ======
# This minimal UI proves the crash popup + timezone helper work.
# =====================================================================

import kivy
kivy.require("2.3.0")

from datetime import datetime
from kivy.app import App
from kivy.core.window import Window
from kivy.clock import Clock
from kivy.logger import Logger
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.lang import Builder
import os

# Optional: white background so black-screen vs. crash is obvious
Window.clearcolor = (1, 1, 1, 1)

# If you keep a KV file, we can autoload it safely if present.
# If your App class is DualClocksApp, Kivy would auto-load dualclocks.kv.
# This explicit loader only runs if the file exists, so it won't crash.
for kv_name in ("dualclocks.kv", "main.kv"):
    if os.path.isfile(kv_name):
        try:
            Builder.load_file(kv_name)
            Logger.info(f"KV: Loaded {kv_name}")
            break
        except Exception as e:
            Logger.exception(f"KV: Failed to load {kv_name}: {e}")

class Root(BoxLayout):
    """Simple vertical box with two time labels (demo)."""
    pass

class DualClocksApp(App):
    title = "Dual Clocks (Demo with Crash Popup)"

    def build(self):
        # Log where last_crash.txt will be written
        Logger.info(f"UserDataDir: {self.user_data_dir}")

        root = Root(orientation="vertical", padding=16, spacing=12)

        self.lbl_sf = Label(text="San Francisco: --:--:--", color=(0, 0, 0, 1), font_size="24sp", halign="center")
        self.lbl_ldn = Label(text="London: --:--:--", color=(0, 0, 0, 1), font_size="24sp", halign="center")
        self.lbl_diff = Label(text="Δ Time: -- hours", color=(0, 0, 0, 1), font_size="18sp", halign="center")

        # The Label default size doesn't stretch; make them fill width
        for lbl in (self.lbl_sf, self.lbl_ldn, self.lbl_diff):
            lbl.size_hint = (1, None)
            lbl.height = self._sp_to_px(lbl.font_size) * 1.8 if isinstance(lbl.font_size, (int, float)) else 48

        root.add_widget(self.lbl_sf)
        root.add_widget(self.lbl_ldn)
        root.add_widget(self.lbl_diff)

        # Update every second
        Clock.schedule_interval(self.update_times, 1)

        # Optional: demonstrate a handled exception inside a scheduled callback
        # Uncomment to see the popup working without crashing the app:
        # Clock.schedule_once(lambda dt: 1/0, 2)  # divide by zero after 2 sec

        return root

    def _sp_to_px(self, sp_value):
        # Helper to approximate label height; avoids importing metrics widely
        try:
            from kivy.metrics import sp
            return sp(sp_value)
        except Exception:
            return 24

    def update_times(self, _dt=0):
        try:
            sf_tz = get_tz("America/Los_Angeles")
            ldn_tz = get_tz("Europe/London")
            now_sf = datetime.now(sf_tz)
            now_ldn = datetime.now(ldn_tz)
            self.lbl_sf.text = f"San Francisco: {now_sf:%Y-%m-%d %H:%M:%S} ({now_sf.tzname()})"
            self.lbl_ldn.text = f"London: {now_ldn:%Y-%m-%d %H:%M:%S} ({now_ldn.tzname()})"

            # Show whole-hour difference (rounded to nearest hour)
            diff_hours = round((now_ldn - now_sf).total_seconds() / 3600.0)
            self.lbl_diff.text = f"Δ Time: {diff_hours:+d} hours"
        except Exception as e:
            # Any error here will also show in the popup via ExceptionManager,
            # but we log it to be explicit.
            Logger.exception(f"update_times failed: {e}")

if __name__ == "__main__":
    DualClocksApp().run()
