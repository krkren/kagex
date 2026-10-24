#!/bin/bash
# Force-pushes ./results as the single commit of branch ci/<name> (GH_TOKEN, GITHUB_REPOSITORY).
set -e
name=$1; msg=$2
cd results
for f in configure.log build.log build2.log; do
  [ -f "$f" ] && tail -n 400 "$f" > "$f.tail" && rm "$f"
done
git init -q -b results .
git config user.name "kagex-ci"
git config user.email "kagex-ci@users.noreply.github.com"
git add -A
git commit -q -m "$msg"
git push -q -f "https://x-access-token:${GH_TOKEN}@github.com/${GITHUB_REPOSITORY}.git" "HEAD:refs/heads/ci/$name"
