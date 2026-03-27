import base64
import json
import os
from typing import Dict

import httpx

from backend.services.vision_llm import (
    ALLOWED_CATEGORIES,
    ALLOWED_COLORS,
    ALLOWED_STYLES,
    _build_title,
    _extract_json,
    _normalize_category,
    _normalize_color,
    _normalize_style,
)


class VisionOllamaUnavailable(RuntimeError):
    pass


def _schema() -> Dict:
    return {
        "type": "object",
        "properties": {
            "title": {"type": "string"},
            "category": {"type": "string", "enum": sorted(ALLOWED_CATEGORIES)},
            "color": {"type": "string", "enum": sorted(ALLOWED_COLORS)},
            "style": {"type": "string", "enum": sorted(ALLOWED_STYLES)},
        },
        "required": ["title", "category", "color", "style"],
        "additionalProperties": False,
    }


async def analyze_image_ollama(
    *,
    image_bytes: bytes,
    filename: str,
    content_type: str,
) -> Dict:
    base_url = os.getenv("VISION_OLLAMA_BASE_URL", "http://127.0.0.1:11434").rstrip("/")
    model = os.getenv("VISION_OLLAMA_MODEL", "qwen3-vl:8b").strip()
    timeout = float(os.getenv("VISION_OLLAMA_TIMEOUT", "180").strip() or "180")

    if not model:
        raise VisionOllamaUnavailable("VISION_OLLAMA_MODEL is not configured")

    system_prompt = """
You are a strict fashion vision classifier for a wardrobe app.
Return only valid JSON.
Choose exactly one category, one color and one style from the allowed lists.
Focus on the main garment in the image.
Use the dominant garment color, not the background.
If patterned trousers are mostly green, return green instead of gray.
If a garment is winter or ski oriented, prefer technical or sport when appropriate.
"""

    user_prompt = f"""
Analyze the garment in this image.

Allowed categories:
unknown, tshirt, top, shirt, sweater, hoodie, jeans, trousers, shorts, skirt, dress,
sneakers, boots, shoes, loafers, jacket, coat, blazer, accessory

Allowed colors:
unknown, black, white, gray, navy, blue, beige, brown, red, green, pink, purple, yellow, orange

Allowed styles:
unknown, minimal, casual, sport, classic, formal, streetwear, romantic, technical, old_money

Return JSON only in this shape:
{{
  "title": "short human-readable title",
  "category": "one allowed category",
  "color": "one allowed color",
  "style": "one allowed style"
}}

Filename: {filename}
Content type: {content_type or "image/jpeg"}
"""

    payload = {
        "model": model,
        "stream": False,
        "format": _schema(),
        "options": {
            "temperature": 0,
        },
        "messages": [
            {"role": "system", "content": system_prompt.strip()},
            {
                "role": "user",
                "content": user_prompt.strip(),
                "images": [base64.b64encode(image_bytes).decode("ascii")],
            },
        ],
    }

    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.post(
                f"{base_url}/api/chat",
                json=payload,
            )
        response.raise_for_status()
    except httpx.RequestError as exc:
        raise VisionOllamaUnavailable(f"Ollama is unavailable at {base_url}: {exc}") from exc
    except httpx.HTTPStatusError as exc:
        raise VisionOllamaUnavailable(
            f"Ollama request failed with {exc.response.status_code}: {exc.response.text}"
        ) from exc

    data = response.json()
    message = data.get("message") or {}
    content = (message.get("content") or "").strip()
    parsed = _extract_json(content)

    category = _normalize_category(parsed.get("category", "unknown"))
    color = _normalize_color(parsed.get("color", "unknown"))
    style = _normalize_style(parsed.get("style", "unknown"))
    title = str(parsed.get("title") or "").strip() or _build_title(color, category)

    return {
        "title": title,
        "category": category,
        "color": color,
        "style": style,
        "source": "ollama",
    }
