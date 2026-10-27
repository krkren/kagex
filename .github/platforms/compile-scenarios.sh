#!/bin/bash
# Compiles the sample's scenarios (the scripts in data/scenario/!scnlist.txt, doc/scn.txt) and
# packs the compiled files into a tarball the platform jobs unpack into the project before they
# package it. The web, Android and iOS packages hold data the engine can't write, so it can't
# compile them as it plays (the desktop packages' debug mode does): without them their demos
# played from the scripts, and going back, the Replay pictures and Search found nothing.
#
# The engine is the newest release's Linux package (as smoke.yml takes it), run on this commit's
# data and framework (data/startup.tjs uses ../template/system).
# usage: compile-scenarios.sh <project dir> <output .tgz>
set -euo pipefail
proj=$(cd "$1" && pwd)
out=$2
tag=$(gh api "repos/$GITHUB_REPOSITORY/releases" --jq '[.[] | select(.draft | not) | select(any(.assets[]; .name == "kagex_sdl3_linux_release.zip"))][0].tag_name')
if [ -z "$tag" ] || [ "$tag" = "null" ]; then
  echo "::error title=No engine::No release has kagex_sdl3_linux_release.zip to compile the scenarios with"
  exit 1
fi
echo "Compiling the scenarios with the engine of release $tag"
dl="$RUNNER_TEMP/scn-engine"
rm -rf "$dl"; mkdir -p "$dl"
gh release download "$tag" --repo "$GITHUB_REPOSITORY" --pattern kagex_sdl3_linux_release.zip --dir "$dl"
unzip -q "$dl/kagex_sdl3_linux_release.zip" -d "$dl/pkg"
chmod +x "$dl/pkg/krkrz"
find "$proj/data" \( -name '*.scn' -o -name '*.scn.json' \) -delete
save=$(mktemp -d)
set +e
(cd "$dl/pkg" && SDL_VIDEO_DRIVER=offscreen SDL_AUDIO_DRIVER=dummy timeout 300 ./krkrz "$proj/data" "-datapath=$save/" -scncompile=all) > "$RUNNER_TEMP/scncompile.log" 2>&1
code=$?
set -e
summary=$(grep -a "Compiled scenarios:" "$RUNNER_TEMP/scncompile.log" | tail -1 || true)
echo "exit code $code; ${summary:-no summary}"
if [ "$code" != 0 ] || [ -z "$summary" ] || ! grep -q " 0 failed" <<< "$summary"; then
  tail -40 "$RUNNER_TEMP/scncompile.log"
  echo "::error title=Compiling the scenarios failed::${summary:-the engine stopped (exit code $code)}"
  exit 1
fi
(cd "$proj" && find data \( -name '*.scn' -o -name '*.scn.json' \) | sort > "$RUNNER_TEMP/scn-files.txt")
cat "$RUNNER_TEMP/scn-files.txt"
[ -s "$RUNNER_TEMP/scn-files.txt" ] || { echo "::error title=No compiled scenarios::the engine wrote none"; exit 1; }
tar czf "$out" -C "$proj" -T "$RUNNER_TEMP/scn-files.txt"
