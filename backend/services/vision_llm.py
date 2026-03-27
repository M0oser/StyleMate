import base64
import json
import os
import re
from typing import Dict

import httpx


ALLOWED_CATEGORIES = {
    "unknown",
    "tshirt",
    "top",
    "shirt",
    "sweater",
    "hoodie",
    "jeans",
    "trousers",
    "shorts",
    "skirt",
    "dress",
    "sneakers",
    "boots",
    "shoes",
    "loafers",
    "jacket",
    "coat",
    "blazer",
    "accessory",
}

ALLOWED_COLORS = {
    "unknown",
    "black",
    "white",
    "gray",
    "navy",
    "blue",
    "beige",
    "brown",
    "red",
    "green",
    "pink",
    "purple",
    "yellow",
    "orange",
}

ALLOWED_STYLES = {
    "unknown",
    "minimal",
    "casual",
    "sport",
    "classic",
    "formal",
    "streetwear",
    "romantic",
    "technical",
    "old_money",
}

CATEGORY_ALIASES = {
    "t-shirt": "tshirt",
    "tee": "tshirt",
    "tee shirt": "tshirt",
    "tank_top": "top",
    "tank-top": "top",
    "tank top": "top",
    "blouse": "shirt",
    "cardigan": "sweater",
    "sweatshirt": "sweater",
    "pants": "trousers",
    "pant": "trousers",
    "legging": "trousers",
    "leggings": "trousers",
    "trainers": "sneakers",
    "sneaker": "sneakers",
    "boot": "boots",
    "loafer": "loafers",
    "shoe": "shoes",
    "trench": "coat",
    "parka": "coat",
    "windbreaker": "jacket",
}

COLOR_ALIASES = {
    "grey": "gray",
    "charcoal": "gray",
    "olive": "green",
    "khaki": "green",
    "cream": "beige",
    "tan": "beige",
}

STYLE_ALIASES = {
    "minimalist": "minimal",
    "sporty": "sport",
    "athleisure": "sport",
    "smart_casual": "classic",
    "old money": "old_money",
}


class VisionLLMUnavailable(RuntimeError):
    pass


def _normalize_token(value: str) -> str:
    return re.sub(r"[^a-z0-9_ -]+", "", str(value or "").strip().lower()).replace(" ", "_")


def _normalize_category(value: str) -> str:
    token = _normalize_token(value)
    token = CATEGORY_ALIASES.get(token, token)
    return token if token in ALLOWED_CATEGORIES else "unknown"


def _normalize_color(value: str) -> str:
    token = _normalize_token(value)
    token = COLOR_ALIASES.get(token, token)
    return token if token in ALLOWED_COLORS else "unknown"


def _normalize_style(value: str) -> str:
    token = _normalize_token(value)
    token = STYLE_ALIASES.get(token, token)
    return token if token in ALLOWED_STYLES else "unknown"


def _extract_json(text: str) -> Dict:
    text = (text or "").strip()
    if not text:
        raise ValueError("Empty vision LLM response")

    try:
        return json.loads(text)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", text, flags=re.DOTALL)
        if not match:
            raise
        return json.loads(match.group(0))


def _build_title(color: str, category: str) -> str:
    if color == "unknown" and category == "unknown":
        return "Unknown item"
    if color == "unknown":
        return category.capitalize()
    return f"{color.capitalize()} {category.capitalize()}"


async def analyze_image_llm(
    *,
    image_bytes: bytes,
    filename: str,
    content_type: str,
) -> Dict:
    api_key = (
        os.getenv("VISION_LLM_API_KEY")
        or os.getenv("OPENROUTER_API_KEY")
        or ""
    ).strip()
    if not api_key:
        raise VisionLLMUnavailable("VISION_LLM_API_KEY/OPENROUTER_API_KEY is not configured")

    base_url = os.getenv("VISION_LLM_BASE_URL", "https://openrouter.ai/api/v1").rstrip("/")
    model = os.getenv("VISION_LLM_MODEL", "qwen/qwen2.5-vl-72b-instruct").strip()
    timeout = float(os.getenv("VISION_LLM_TIMEOUT", "90").strip() or "90")

    media_type = content_type or "image/jpeg"
    data_uri = f"data:{media_type};base64,{base64.b64encode(image_bytes).decode('ascii')}"

    system_prompt = """
You are a strict fashion vision classifier.
Return only valid JSON.
You must identify the clothing item in the image as accurately as possible.
Choose exactly one value for each field from the allowed lists.

Allowed categories:
unknown, tshirt, top, shirt, sweater, hoodie, jeans, trousers, shorts, skirt, dress,
sneakers, boots, shoes, loafers, jacket, coat, blazer, accessory

Allowed colors:
unknown, black, white, gray, navy, blue, beige, brown, red, green, pink, purple, yellow, orange

Allowed styles:
unknown, minimal, casual, sport, classic, formal, streetwear, romantic, technical, old_money

Use the dominant visible garment color, not background color.
If a patterned item is mostly green, output green, not gray.
If the item is winter/outdoor wear, prefer technical/classic/casual according to appearance.
"""

    user_prompt = f"""
Analyze the garment in this image.

Return JSON only:
{{
  "title": "short human-readable title",
  "category": "one allowed category",
  "color": "one allowed color",
  "style": "one allowed style"
}}

Filename: {filename}
"""

    payload = {
        "model": model,
        "temperature": 0,
        "response_format": {"type": "json_object"},
        "messages": [
            {"role": "system", "content": system_prompt.strip()},
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": user_prompt.strip()},
                    {"type": "image_url", "image_url": {"url": data_uri}},
                ],
            },
        ],
    }

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    if "openrouter.ai" in base_url:
        headers["HTTP-Referer"] = os.getenv("WEBAPP_URL", "https://stylemate.local")
        headers["X-Title"] = "StyleMate Vision"

    async with httpx.AsyncClient(timeout=timeout) as client:
        response = await client.post(
            f"{base_url}/chat/completions",
            headers=headers,
            json=payload,
        )

    response.raise_for_status()
    data = response.json()
    content = data["choices"][0]["message"]["content"]
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
        "source": "llm",
    }
