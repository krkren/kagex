#!/bin/bash
# Runs a command with its output in results/<name>.log. On failure, the last lines go to the
# job's annotations too (they can be read without the job log) and the step fails.
# usage: run-logged.sh <name> <command...>
name=$1; shift
log="$GITHUB_WORKSPACE/results/$name.log"
mkdir -p "$GITHUB_WORKSPACE/results"
echo "::group::$name: $*"
set -o pipefail
if "$@" 2>&1 | tee "$log"; then echo "::endgroup::"; exit 0; fi
code=$?
echo "::endgroup::"
# one annotation with the tail; GitHub keeps up to 10 per step
tail -n 40 "$log" | sed 's/%/%25/g' | awk 'BEGIN{ORS="%0A"} {print}' > "$log.tail"
echo "::error title=$name failed ($code)::$(cat "$log.tail")"
exit $code
