#!/usr/bin/env bash
set -euo pipefail

cd "$DEPLOY_PATH"
git fetch origin main
git reset --hard origin/main
docker compose down
docker compose build --no-cache
mkdir -p data/logos &&
chown -R 1000:1000 data/ &&
docker compose up -d
