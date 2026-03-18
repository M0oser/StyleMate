#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."

APP_PORT="${APP_PORT:-8000}"
TUNNEL_URL="${TUNNEL_URL:-http://localhost:${APP_PORT}}"

exec cloudflared tunnel \
  --url "$TUNNEL_URL" \
  --protocol http2 \
  --edge-ip-version 4
