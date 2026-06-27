#!/usr/bin/env bash
set -euo pipefail

APP_DIR="${APP_DIR:-/opt/emergency-teams-coordinator}"
cd "$APP_DIR"

git fetch origin main
LOCAL_REVISION="$(git rev-parse HEAD)"
REMOTE_REVISION="$(git rev-parse origin/main)"

if [[ "$LOCAL_REVISION" == "$REMOTE_REVISION" ]] && [[ "${FORCE_DEPLOY:-0}" != "1" ]]; then
  exit 0
fi

git merge --ff-only origin/main
docker compose up -d --build --remove-orphans
docker compose ps

