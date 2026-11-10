#!/usr/bin/env bash
# Redeploy OpenDF on this machine. Intended to be run on vpsjy from /data/opendf:
#   ./deploy.sh                  # origin/main
#   ./deploy.sh deploy/vpsjy-docker
#
# This script only talks to the `opendf` compose project. It does not stop,
# restart, or prune any other container, network, or volume.
set -euo pipefail

DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$DIR"

REF="${1:-main}"

echo "== 1/5 fetch $REF"
if git rev-parse --git-dir >/dev/null 2>&1; then
  # vpsjy currently cannot reach github.com:443; keep a short timeout so redeploy does not stall.
  timeout 15 git fetch -q --all --tags --prune || true
  TARGET="$(git rev-parse --verify -q "origin/$REF" || git rev-parse --verify -q "$REF^{commit}" || true)"
  if [ -n "${TARGET:-}" ]; then
    # reset --hard only affects tracked files; ./data (runtime db/storage) is gitignored.
    git reset -q --hard "$TARGET"
    echo "   now at $(git rev-parse --short HEAD)"
  else
    echo "   could not resolve $REF, continuing with the working tree as-is ($(git rev-parse --short HEAD 2>/dev/null || echo unversioned))"
  fi
else
  echo "   not a git checkout, continuing with the files in $DIR"
fi

echo "== 2/5 prepare persistent data dir"
mkdir -p data/storage/raw data/storage/export
# SQLite and its journal/WAL files all live in this directory (OPENDF_DATA_DIR=/data).

echo "== 3/5 build and start (opendf project only)"
docker compose -p opendf up -d --build

echo "== 4/5 wait for the public entry on 127.0.0.1:18090"
for i in $(seq 1 60); do
  if curl -sf -o /dev/null http://127.0.0.1:18090/ && curl -sf http://127.0.0.1:18090/api/v1/dashboard/stats >/dev/null; then
    echo "   ready"
    break
  fi
  if [ "$i" -eq 60 ]; then
    echo "   timed out. logs:"
    docker compose -p opendf logs --tail=80
    exit 1
  fi
  sleep 3
done

echo "== 5/5 seed a mock capture if none has video yet"
SESSIONS_JSON="$(curl -sf http://127.0.0.1:18090/api/v1/sessions || true)"
if ! printf '%s' "$SESSIONS_JSON" | grep -q 'video_url'; then
  echo "   no session video found, POST /api/v1/sessions/mock-sample"
  curl -sf -X POST http://127.0.0.1:18090/api/v1/sessions/mock-sample
  echo
else
  echo "   existing session already has a video, skipping mock-sample"
fi

echo
echo "OpenDF is up at http://127.0.0.1:18090  (public: https://opendf.20000427.xyz)"
echo "version: $(git rev-parse --short HEAD 2>/dev/null || echo unknown)"
