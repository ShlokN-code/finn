#!/usr/bin/env bash
# Confirm Render is serving a given commit (default: local HEAD). Polls /version until it matches or times out.
#   scripts/check_deploy.sh [commit] [timeout_seconds]
# API base comes from API_PUBLIC_URL (env or .env); defaults to the production Render URL.
set -euo pipefail
want="${1:-$(git rev-parse HEAD)}"
timeout="${2:-900}"
base="${API_PUBLIC_URL:-$(grep -E '^API_PUBLIC_URL=' "$(dirname "$0")/../.env" 2>/dev/null | cut -d= -f2- || true)}"
base="${base:-https://finn-api-4ejm.onrender.com}"
base="${base%/}"
deadline=$(( $(date +%s) + timeout ))
while :; do
  live=$(curl -fsS --max-time 30 "$base/version" 2>/dev/null | python3 -c 'import json,sys; print(json.load(sys.stdin).get("commit") or "")' 2>/dev/null || true)
  if [[ -n "$live" && "$want" == "$live"* || -n "$live" && "$live" == "$want"* ]]; then
    echo "live: ${live:0:7} ✓ (matches ${want:0:7})"; exit 0
  fi
  if (( $(date +%s) >= deadline )); then
    echo "NOT live after ${timeout}s: Render serves '${live:-unknown}', wanted ${want:0:7}. Check the Render deploy log." >&2
    exit 1
  fi
  sleep 20
done
