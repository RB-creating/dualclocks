[app]
title = Dual Clocks
package.name = dualclocks
package.domain = org.robbertolini

source.dir = .
source.include_exts = py,kv,png,jpg,ttf,txt

version.regex = __version__ = '"['"]
version.filename = %(source.dir)s/main.py

requirements = python3,kivy==2.3.0,tzdata

# One arch for fast CI
android.archs = arm64-v8a

# Match a stable toolchain (p4a currently recommends NDK r25b; your log shows it downloads 25b)
android.api = 31
android.minapi = 24
android.ndk = 25b

orientation = portrait
fullscreen = 0

[buildozer]
log_level = 2
