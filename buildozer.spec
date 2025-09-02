[app]
# Display name under the icon
title = Dual Clocks

# Internal identifiers
package.name = dualclocks
package.domain = org.example       # you can change later, e.g., org.robbertolini

# Your source lives in the repo root
source.dir = .
source.include_exts = py,kv,png,jpg,ttf,txt

# Read version from main.py: __version__ = "0.1.0"
version.regex = __version__ = '"['"]
version.filename = %(source.dir)s/main.py

# Pin Kivy 2.3.0 (your KV requires it), and include tzdata for ZoneInfo
requirements = python3,kivy==2.3.0,tzdata

# Orientation and window
orientation = portrait
fullscreen = 0

# If you add an icon later:
# icon.filename = %(source.dir)s/icon.png

# No special Android permissions needed for clocks
# android.permissions =

[buildozer]
log_level = 2
