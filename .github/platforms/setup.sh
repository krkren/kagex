#!/bin/bash
# Clones krkrz_dev at $ENGINE_SHA (with its submodules) and, when given, a platform kit at a
# fixed commit, next to the kagex checkout:
#   $KRKRZ_BASE/krkrz_dev, $KRKRZ_BASE/<kit>, $KRKRZ_BASE/kagex (actions/checkout)
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
if [ $# -ge 2 ]; then
  git clone -q "https://github.com/wamsoft/$1.git" "$1"
  git -C "$1" checkout -q "$2"
fi
{
  echo "kagex $(git -C kagex rev-parse HEAD) ($(git -C kagex log -1 --format=%s))"
  echo "engine krkrz_dev @ $(git -C krkrz_dev rev-parse HEAD)"
  [ $# -ge 2 ] && echo "kit $1 @ $(git -C "$1" rev-parse HEAD)"
  echo "runner ${ImageOS:-?} ${ImageVersion:-?}"
} | tee "$GITHUB_WORKSPACE/results/versions.txt"
