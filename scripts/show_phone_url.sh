#!/usr/bin/env bash
set -euo pipefail

PORT="${APP_PORT:-8000}"

get_ip() {
  ipconfig getifaddr en0 2>/dev/null || \
  ipconfig getifaddr en1 2>/dev/null || \
  ifconfig | awk '/inet / && $2 != "127.0.0.1" {print $2; exit}'
}

IP="$(get_ip)"

if [[ -z "${IP:-}" ]]; then
  echo "Не удалось определить локальный IP."
  exit 1
fi

echo "Открой на телефоне:"
echo "http://${IP}:${PORT}"
