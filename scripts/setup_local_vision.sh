#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."

TARGET="${VISION_LOCAL_CHECKPOINT:-models/vit_base_patch32_clip_224.openai.safetensors}"
URL="https://huggingface.co/timm/vit_base_patch32_clip_224.openai/resolve/main/open_clip_model.safetensors"

mkdir -p "$(dirname "$TARGET")"

if [[ -s "$TARGET" ]]; then
  echo "Локальный checkpoint уже существует: $TARGET"
  exit 0
fi

echo "Скачиваю local vision checkpoint..."
curl -L --fail --progress-bar "$URL" -o "$TARGET"

if [[ ! -s "$TARGET" ]]; then
  echo "Checkpoint не скачался корректно."
  exit 1
fi

echo "Готово: $TARGET"
echo "Теперь можно использовать VISION_MODE=local или VISION_MODE=auto."
