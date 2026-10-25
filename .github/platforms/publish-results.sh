#!/bin/bash
# Force-pushes ./results as the single commit of branch ci/platform-results-<name>, so logs
# and screenshots can be read through the API (GH_TOKEN, GITHUB_REPOSITORY).
set -e
name=$1; msg=$2
cd "$GITHUB_WORKSPACE/results"
# what the smoke test kept (--keep), also when its step was cut off
for d in /tmp/kagex-smoke-* "${TMPDIR:-/tmp}"/kagex-smoke-*; do
  [ -d "$d" ] || continue
  for f in "$d"/*.png "$d"/console.txt "$d"/logcat.txt "$d"/simulator.log "$d"/engine.log; do
    [ -f "$f" ] && cp "$f" . 2>/dev/null || true
  done
done
# macOS's crash reports of the engine: a native crash leaves its stack only there
for f in "$HOME"/Library/Logs/DiagnosticReports/*.ips; do
  [ -f "$f" ] && grep -q -i -E 'krkrz|kagex' "$f" 2>/dev/null && cp "$f" . 2>/dev/null || true
done
for f in *.log; do
  [ -f "$f" ] || continue
  # The error lines of every log, with some context, before long logs lose their middle
  grep -n -E -B 3 -A 12 'error:|error [A-Z]+[0-9]+|Error [0-9]+|FAILED|CMake Error|fatal:|undefined (symbol|reference)|What went wrong|\*\* BUILD FAILED' "$f" \
    | grep -v -E 'warning:|-Werror|Wno-error' | head -n 400 > "${f%.log}.errors" || true
  [ -s "${f%.log}.errors" ] || rm -f "${f%.log}.errors"
  [ "$(wc -l < "$f")" -gt 600 ] && { head -n 100 "$f"; echo "..."; tail -n 500 "$f"; } > "$f.cut" && mv "$f.cut" "$f"
done
rm -f *.tail
git init -q -b results .
git config user.name "kagex-ci"
git config user.email "kagex-ci@users.noreply.github.com"
git add -A
git commit -q -m "$msg"
git push -q -f "https://x-access-token:${GH_TOKEN}@github.com/${GITHUB_REPOSITORY}.git" "HEAD:refs/heads/ci/platform-results-$name"
