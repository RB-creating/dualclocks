

[app]
# What shows under the app icon
title = Dual Clocks

# Internal identifiers
package.name = dualclocks
package.domain = org.robbertolini

# Your source lives in the repo root
source.dir = .
source.include_exts = py,kv,png,jpg,ttf,txt

# Read version from main.py: __version__ = "0.1.0"
version.regex = __version__ = ['"](]
version.filename = %(source.dir)s/main.py

# Pin Kivy to match your KV header; include tzdata so ZoneInfo works on-device
requirements = python3,kivy==2.3.0,tzdata


# Build just one arch for now (simpler/faster; matches the YAML env)
android.archs = arm64-v8a

# Orientation and window
orientation = portrait
fullscreen = 0

# (Optional) Add an icon later:
# icon.filename = %(source.dir)s/icon.png

# No special Android permissions needed for clocks
# android.permissions =

[buildozer]
log_level = 2
