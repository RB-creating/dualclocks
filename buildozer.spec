[app]
title = Dual Clocks
package.name = dualclocks
package.domain = org.example
source.dir = .
source.include_exts = py,kv,png,jpg,ttf,otf,wav,txt,md
requirements = python3,kivy==2.3.1,pytz
version = 0.1.0
android.numeric_version = 1
orientation = landscape
fullscreen = 0
android.archs = arm64-v8a
android.allow_backup = False
# Use stable, non-preview Android API (avoid preview build-tools)
# Use stable, non-preview Android API (prevents preview build-tools)
# --- Android configuration (stable & CI-safe) ---
android.api = 34
android.minapi = 23

# Use the SDK we install in GitHub Actions (not Buildozer's private copy)
android.sdk_path = /usr/local/lib/android/sdk

# Auto-accept SDK licenses in CI
android.accept_sdk_license = True

[buildozer]
log_level = 2
warn_on_root = 1
