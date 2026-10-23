#!/bin/bash
# Force-pushes ./results as the single commit of branch ci/platform-results-<name>, so logs
# and screenshots can be read through the API (GH_TOKEN, GITHUB_REPOSITORY).
set -e
name=$1; msg=$2
cd "$GITHUB_WORKSPACE/results"
for f in *.log; do
  [ -f "$f" ] && [ "$(wc -l < "$f")" -gt 600 ] && { head -n 100 "$f"; echo "..."; tail -n 500 "$f"; } > "$f.cut" && mv "$f.cut" "$f"
done
rm -f *.tail
git init -q -b results .
git config user.name "kagex-ci"
git config user.email "kagex-ci@users.noreply.github.com"
git add -A
git commit -q -m "$msg"
git push -q -f "https://x-access-token:${GH_TOKEN}@github.com/${GITHUB_REPOSITORY}.git" "HEAD:refs/heads/ci/platform-results-$name"
