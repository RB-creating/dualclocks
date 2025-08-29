[app]
title = My Kivy App
package.name = mykivyapp
package.domain = org.example
source.dir = .
source.include_exts = py,kv,png,jpg,ttf,wav,txt,md
requirements = python3,kivy
version = 0.1
android.numeric_version = 1
orientation = portrait
fullscreen = 0
android.archs = arm64-v8a
android.allow_backup = False
# Use stable, non-preview Android API (avoid preview build-tools)
android.api = 34
android.minapi = 23

# Auto-accept Android SDK licenses (for CI)
android.accept_sdk_license = True

[buildozer]
log_level = 2
warn_on_root = 1
