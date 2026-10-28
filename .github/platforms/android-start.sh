#!/bin/bash
# Starts a release APK on the running emulator and checks it by the engine's log in logcat
# (SDL/APP). Only debuggable builds open the REPL socket smoketest.py drives (krkrz_android's
# KrkrzActivity), so an APK kagex-release builds is checked by what it logs: it passes when the
# engine loads the static plugins named, the framework gets through Initialize.tjs to the game's
# window, nothing raises a script exception or crashes, and the game still runs 20 seconds later.
# usage: android-start.sh <apk> <applicationId> <logcat file> [plugin...]
set -u
apk=$1; pkg=$2; log=$3; shift 3
fail() { echo "::error title=Release APK::$*"; echo "FAIL: $*"; exit 1; }

adb install -r "$apk" || fail "adb install $apk failed"
adb shell pm clear "$pkg" > /dev/null
adb logcat -c
adb shell monkey -p "$pkg" -c android.intent.category.LAUNCHER 1 > /dev/null 2>&1
started=""
for _ in $(seq 1 120); do
  if adb logcat -d 2>/dev/null | grep -q "KAGMainWindow constructor took"; then started=1; break; fi
  sleep 1
done
[ -n "$started" ] && sleep 20
adb logcat -d > "$log" 2>&1
alive=$(adb shell pidof "$pkg" | tr -d '\r')

grep "SDL/APP" "$log" | grep -E "Kirikiri Z Executable|Selected project directory|KAGMainWindow constructor" | sed 's/^.*SDL\/APP *: //'
ok=1
[ -n "$started" ] || { echo "the game's window wasn't made (no \"KAGMainWindow constructor took\" in 120 s)"; ok=""; }
for p in "$@"; do
  if grep -qE "Static Plugin:$p([^A-Za-z0-9_]|\$)" "$log"; then echo "static plugin $p: loaded"
  else echo "static plugin $p: not loaded"; ok=""; fi
done
if grep -E "Script exception raised|スクリプトで例外が発生しました" "$log"; then echo "a script exception"; ok=""; fi
# a crash of the game's processes (the kit restarts the first one on purpose, with System.exit)
pids=$(grep -oE "Start proc [0-9]+:$pkg/" "$log" | grep -oE "[0-9]+" | sort -u)
for p in $pids; do
  if grep -E "Fatal signal .* pid $p " "$log"; then echo "process $p crashed"; ok=""; fi
done
if grep -A1 "FATAL EXCEPTION" "$log" | grep -F "Process: $pkg"; then echo "a Java exception"; ok=""; fi
if [ -n "$alive" ]; then echo "still running: pid $alive"; else echo "not running after 20 s"; ok=""; fi
adb shell am force-stop "$pkg"
[ -n "$ok" ] || fail "$pkg didn't start cleanly (see $(basename "$log"))"
echo "$pkg started cleanly"
