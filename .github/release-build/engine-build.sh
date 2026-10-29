#!/usr/bin/env bash
# A release of kagex whose engine did not change reuses an earlier release's build of it instead
# of compiling krkrz_dev (with xp3crypt and scnfile built into it) all over again: about an hour
# of the release run for each desktop job, and for Linux as well. Nothing else is asked about, so
# an engine package of an earlier release is the same engine only if these three commits are.
#
#   engine-build.sh find [asset]            prints the tag of the newest release whose marker says
#                                           its engine came from ENGINE_SHA, XP3CRYPT_SHA and
#                                           SCNFILE_SHA and which has that engine package asset,
#                                           or nothing when no release does
#   engine-build.sh unpack <tag> <asset> <dir>
#                                           downloads that release's engine package and unpacks it
#
# The marker (kagex-engine-build.json, which publish adds to a release) names the commits a
# release's engine packages were built from. Releases published before that have no marker, and
# this script refuses to guess what engine they hold.
set -u

REPO=${REPO:-$GITHUB_REPOSITORY}
marker=kagex-engine-build.json
note() { echo "$*"; [ -n "${GITHUB_STEP_SUMMARY:-}" ] && echo "$*" >> "$GITHUB_STEP_SUMMARY"; }

case "$1" in
  find)
    asset=${2:-}
    rm -rf .engine-build
    for tag in $(gh api "repos/$REPO/releases" --jq '.[] | [.created_at, .tag_name] | @tsv' |
                  sort -r | cut -f2); do
      # only a release carrying the marker can say which engine its packages hold
      gh release download "$tag" -R "$REPO" -p "$marker" -D .engine-build --clobber 2> /dev/null || continue
      if [ -n "$asset" ] && ! gh release view "$tag" -R "$REPO" --json assets --jq '.assets[].name' |
           grep -qx -- "$asset"; then
        continue
      fi
      if ENGINE=$ENGINE_SHA XP3=$XP3CRYPT_SHA SCN=$SCNFILE_SHA python3 - .engine-build/$marker <<'EOF'
import json, os, sys
try:
    m = json.load(open(sys.argv[1]))
except (OSError, ValueError):
    sys.exit(1)
sys.exit(0 if m.get("engine") == os.environ["ENGINE"] and m.get("xp3crypt") == os.environ["XP3"]
         and m.get("scnfile") == os.environ["SCN"] else 1)
EOF
      then
        echo "$tag"
        note "Reusing the engine built for $tag: krkrz_dev $ENGINE_SHA, xp3crypt $XP3CRYPT_SHA, scnfile $SCNFILE_SHA."
        break
      fi
      rm -rf .engine-build
    done
    rm -rf .engine-build
    ;;
  unpack)
    tag=$2 asset=$3 dir=$4
    rm -rf .engine-build "$dir"
    gh release download "$tag" -R "$REPO" -p "$asset" -D .engine-build --clobber
    mkdir -p "$dir"
    unzip -q ".engine-build/$asset" -d "$dir"
    rm -rf .engine-build
    note "Unpacked $asset of release $tag into $dir."
    find "$dir" -maxdepth 2 -type f | sort | head -20
    ;;
  *)
    echo "usage: $0 find [asset] | unpack <tag> <asset> <dir>" >&2
    exit 2
    ;;
esac
