#!/usr/bin/env python3
"""Lets the sample's APK see the system's text-to-speech engines: since Android 11 an app sees no
other app's service unless its manifest asks (<queries>), so the speech plugin found no engine
and reading lines aloud was missing from Config. kagex-release adds the same query to a game's
APK (platforms.android.ttsQuery). Usage: kit-android-tts.py <the kit's AndroidManifest.xml>"""
import sys

path = sys.argv[1]
text = open(path, encoding="utf-8").read()
action = "android.intent.action.TTS_SERVICE"
if action not in text:
    at = text.index("<application")
    query = ("<!-- kagex: the system's text-to-speech engines (the speech plugin) -->\n"
             "    <queries>\n        <intent>\n            <action android:name=\"%s\" />\n"
             "        </intent>\n    </queries>\n\n    " % action)
    text = text[:at] + query + text[at:]
    open(path, "w", encoding="utf-8").write(text)
print("%s: %s" % (path, "has the TTS query" if action in text else "no TTS query"))
