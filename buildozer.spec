[app]
title = Dual Clocks
package.name = dualclocks
package.domain = org.robbertolini

source.dir = .
# Important: no spaces around the commas; include common asset types
source.include_exts = py,kv,png,jpg,jpeg,ttf,otf,txt,json
# If you keep assets in folders, uncomment and adjust as needed:
# source.include_patterns = images/*, assets/*, fonts/*

version = 0.1.0

# Choose ONE requirement line depending on your code:
# If you use zoneinfo (Python 3.9+):
requirements = python3,kivy==2.3.0,tzdata
# If you use pytz instead, replace the above with:
# requirements = python3,kivy==2.3.0,pytz

# One arch for fast CI
android.archs = arm64-v8a

# Stable toolchain pins (these worked well in many projects)
android.api = 31
android.minapi = 24
android.ndk = 25b

orientation = portrait
fullscreen = 0

# Easier to capture Python errors in logcat
android.logcat_filters = *:S python:D

[buildozer]
log_level = 2
