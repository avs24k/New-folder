[app]
title = spyer
package.name = spyer
package.domain = com.example
source.dir = .
source.include_exts = py,png,jpg,kv,ttf
version = 0.1.1
requirements = python3,kivy,aiohttp,pyjnius
orientation = portrait
entrypoint = app.py
services = mdmservice:service.py
fullscreen = 0

android.api = 34
android.minapi = 26
android.archs = arm64-v8a, armeabi-v7a
android.wakelock = True
android.permissions = INTERNET,FOREGROUND_SERVICE,FOREGROUND_SERVICE_DATA_SYNC,WAKE_LOCK,POST_NOTIFICATIONS,CAMERA,READ_EXTERNAL_STORAGE,WRITE_EXTERNAL_STORAGE,READ_MEDIA_IMAGES,READ_MEDIA_VIDEO,READ_MEDIA_AUDIO,RECEIVE_BOOT_COMPLETED
android.preserve_data = True

[buildozer]
log_level = 2
warn_on_root = 1
