#!/usr/bin/env bash
# Run the tool's container for one leg, and say plainly how it ended.
#
#   harness/run_container.sh <name> <minutes> <log> <docker run args...>
#
# Why not `docker run` straight from the step. When a step hit its
# `timeout-minutes`, Actions killed the docker CLI and the container kept
# going: bash was PID 1 and ignored the signal. It went on writing into
# /data/out after the Runs gate had failed, competed with the next leg for the
# CPU, and the report said "the tool exited with an error". And a process our
# own memory ceiling killed left no line in the log at all, so it was
# published as the tool failing rather than as the ceiling it is.
#
# So: the time limit is enforced here, before the step's own; the container
# always dies with the script; and two lines of our own go into the log for
# diagnose_log to read, one for the time limit and one for the memory ceiling.
# The exit status is the container's, or 124 when the limit stopped it.
set -uo pipefail
source "$(dirname "${BASH_SOURCE[0]}")/record_terminal.sh"

name=$1; minutes=$2; log=$3; shift 3
max_out_kb="${STRHUB_MAX_OUT_KB:-2097152}"
max_out_files="${STRHUB_MAX_OUT_FILES:-10000}"
quota_flag=$(mktemp "${TMPDIR:-/tmp}/strhub-quota.XXXXXX")
rm -f "$quota_flag"
watchdog_pid=""

cleanup() {
  if [ -n "$watchdog_pid" ]; then
    kill "$watchdog_pid" >/dev/null 2>&1 || true
    wait "$watchdog_pid" >/dev/null 2>&1 || true
  fi
  rm -f "$quota_flag"
  docker rm -f "$name" >/dev/null 2>&1 || true
}
trap cleanup EXIT

out_host=""
prev=""
for arg in "$@"; do
  if [ "$prev" = "-v" ]; then
    case "$arg" in
      *:/data/out|*:/data/out:*)
        out_host="${arg%%:/data/out*}"
        ;;
    esac
  fi
  prev="$arg"
done

if [ -n "$out_host" ] && [ -d "$out_host" ]; then
  (
    while sleep 2; do
      [ -d "$out_host" ] || continue
      used_kb=$(du -sk "$out_host" 2>/dev/null | awk '{print $1}')
      file_count=$(find "$out_host" -maxdepth 6 2>/dev/null | wc -l | tr -d ' ')
      if [ -n "$used_kb" ] && [ "$used_kb" -gt "$max_out_kb" ]; then
        printf 'size_kb=%s\n' "$used_kb" > "$quota_flag"
        docker kill "$name" >/dev/null 2>&1 || true
        exit 0
      fi
      if [ -n "$file_count" ] && [ "$file_count" -gt "$max_out_files" ]; then
        printf 'files=%s\n' "$file_count" > "$quota_flag"
        docker kill "$name" >/dev/null 2>&1 || true
        exit 0
      fi
    done
  ) &
  watchdog_pid=$!
fi

limit=$(( minutes * 60 ))
start=$SECONDS
# --init: signals reach the tool's processes instead of stopping at bash.
rc=0
record_terminal "$log" timeout --kill-after=20 "$limit" docker run --init --name "$name" "$@" || rc=$?
elapsed=$(( SECONDS - start ))

if [ -n "$watchdog_pid" ]; then
  kill "$watchdog_pid" >/dev/null 2>&1 || true
  wait "$watchdog_pid" >/dev/null 2>&1 || true
  watchdog_pid=""
fi

if [ -f "$quota_flag" ]; then
  docker kill "$name" >/dev/null 2>&1 || true
  echo "STRhub: the container exceeded the /data/out output ceiling ($(cat "$quota_flag")); Disk quota exceeded." | tee -a "$log"
  exit 125
fi
if [ "$elapsed" -ge "$limit" ]; then
  docker kill "$name" >/dev/null 2>&1 || true
  echo "STRhub: the run was stopped at the time limit of ${minutes} minutes." | tee -a "$log"
  exit 124
fi
if [ "$(docker inspect -f '{{.State.OOMKilled}}' "$name" 2>/dev/null)" = "true" ]; then
  echo "STRhub: the container was killed on reaching its memory limit (out of memory)." | tee -a "$log"
fi
exit "$rc"
