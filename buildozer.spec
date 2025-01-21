[app]
title = DigiCollect
package.name = digicollect
package.domain = com.digicollect

source.dir = .
source.include_exts = py,png,jpg,kv,atlas,json,xml

version = 1.0
requirements = python3,kivy,kivymd,requests,beautifulsoup4,plyer,pillow,jnius

orientation = portrait
fullscreen = 0

android.permissions = INTERNET,SYSTEM_ALERT_WINDOW,ACTION_MANAGE_OVERLAY_PERMISSION,RECEIVE_BOOT_COMPLETED
android.api = 29
android.minapi = 21
android.sdk = 29
android.ndk = 21e
android.private_storage = True
android.accept_sdk_license = True

[buildozer]
log_level = 2
warn_on_root = 1
