#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."

APP_HOST="${APP_HOST:-0.0.0.0}"
APP_PORT="${APP_PORT:-8000}"

exec venv/bin/uvicorn backend.main:app --host "$APP_HOST" --port "$APP_PORT"
