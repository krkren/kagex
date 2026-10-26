#!/bin/bash
# Clones krkrz_dev at $ENGINE_SHA (with its submodules), xp3crypt and scnfile at $XP3CRYPT_SHA
# and $SCNFILE_SHA, and, when given, a platform kit at a fixed commit, next to the kagex checkout:
#   $KRKRZ_BASE/krkrz_dev, $KRKRZ_BASE/xp3crypt, $KRKRZ_BASE/scnfile, $KRKRZ_BASE/<kit>,
#   $KRKRZ_BASE/kagex (actions/checkout)
# usage: setup.sh [kit kit_sha]
set -euo pipefail
cd "$KRKRZ_BASE"
mkdir -p "$GITHUB_WORKSPACE/results"
git clone -q --depth 1 --recursive --shallow-submodules -j 8 -b master https://github.com/wamsoft/krkrz_dev.git krkrz_dev
if [ "$(git -C krkrz_dev rev-parse HEAD)" != "$ENGINE_SHA" ]; then
  rm -rf krkrz_dev
  git clone -q --recursive -j 8 https://github.com/wamsoft/krkrz_dev.git krkrz_dev
  git -C krkrz_dev checkout -q "$ENGINE_SHA"
  git -C krkrz_dev submodule update -q --init --recursive
fi
# kagex's own plugins, next to krkrz_dev (the kit configs' pluginFolders name them):
# xp3crypt (encrypted data.xp3, built into the engine) and scnfile (compiled scenarios)
for p in xp3crypt:"${XP3CRYPT_SHA:-}" scnfile:"${SCNFILE_SHA:-}"; do
  name=${p%%:*} sha=${p#*:}
  [ -n "$sha" ] || continue
  git clone -q "https://github.com/krkren/$name.git" "$name"
  git -C "$name" checkout -q "$sha"
done
if [ $# -ge 2 ]; then
  git clone -q "https://github.com/wamsoft/$1.git" "$1"
  git -C "$1" checkout -q "$2"
  # Some of the kits' scripts have Windows line endings (krkrz_android's Makefile and
  # install-sdl-aar.sh), which bash and make take as part of the commands
  find "$1" -maxdepth 2 -type f \( -name Makefile -o -name '*.sh' \) -exec perl -pi -e 's/\r$//' {} +
fi
{
  echo "kagex $(git -C kagex rev-parse HEAD) ($(git -C kagex log -1 --format=%s))"
  echo "engine krkrz_dev @ $(git -C krkrz_dev rev-parse HEAD)"
  for name in xp3crypt scnfile; do [ -d "$name" ] && echo "$name @ $(git -C "$name" rev-parse HEAD)"; done
  [ $# -ge 2 ] && echo "kit $1 @ $(git -C "$1" rev-parse HEAD)"
  echo "runner ${ImageOS:-?} ${ImageVersion:-?}"
} | tee "$GITHUB_WORKSPACE/results/versions.txt"
