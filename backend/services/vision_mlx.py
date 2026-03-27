import asyncio
import os
from io import BytesIO
from threading import Lock
from typing import Dict, Optional, Tuple

import mlx_vlm.tokenizer_utils as tokenizer_utils
from mlx_vlm import apply_chat_template, generate, load
from mlx_vlm.utils import load_config
from PIL import Image

from backend.services.vision_llm import (
    _build_title,
    _extract_json,
    _normalize_category,
    _normalize_color,
    _normalize_style,
)
from backend.services.vision_local import _dominant_color, _focus_on_subject, _footwear_base_color_hint
from backend.services.image_preprocess import load_normalized_image


class VisionMLXUnavailable(RuntimeError):
    pass


_MODEL_LOCK = Lock()
_MODEL_CACHE: Optional[Tuple[object, object, Dict]] = None
_PATCHED_DETOKENIZER = False


def _mlx_model_name() -> str:
    return (
        os.getenv("VISION_MLX_MODEL", "mlx-community/Qwen2.5-VL-3B-Instruct-4bit").strip()
    )


def _ensure_xet_disabled() -> None:
    os.environ.setdefault("HF_HUB_DISABLE_XET", "1")
    os.environ.setdefault("HUGGINGFACE_HUB_DISABLE_XET", "1")


def _patch_detokenizer() -> None:
    global _PATCHED_DETOKENIZER

    if _PATCHED_DETOKENIZER:
        return

    def patched_init(self, tokenizer, trim_space=False):
        self.trim_space = trim_space
        vocab = getattr(tokenizer, "vocab", None) or tokenizer.get_vocab()
        self.tokenmap = [None] * len(vocab)
        for value, token_id in vocab.items():
            self.tokenmap[token_id] = value
        self.reset()
        self.make_byte_decoder()

    tokenizer_utils.BPEStreamingDetokenizer.__init__ = patched_init
    _PATCHED_DETOKENIZER = True


def _get_model_bundle() -> Tuple[object, object, Dict]:
    global _MODEL_CACHE

    if _MODEL_CACHE is not None:
        return _MODEL_CACHE

    with _MODEL_LOCK:
        if _MODEL_CACHE is not None:
            return _MODEL_CACHE

        _ensure_xet_disabled()
        _patch_detokenizer()
        model_name = _mlx_model_name()
        if not model_name:
            raise VisionMLXUnavailable("VISION_MLX_MODEL is not configured")

        model, processor = load(
            model_name,
            lazy=False,
            trust_remote_code=True,
            use_fast=False,
        )
        config = load_config(model_name, trust_remote_code=True)
        _MODEL_CACHE = (model, processor, config)
        return _MODEL_CACHE


def _prompt(filename: str) -> str:
    return f"""
Analyze the garment in this image.

Return JSON only:
{{
  "title": "short human-readable title",
  "category": "one allowed category",
  "color": "one allowed color",
  "style": "one allowed style"
}}

Allowed categories:
unknown, tshirt, top, shirt, sweater, hoodie, jeans, trousers, shorts, skirt, dress,
sneakers, boots, shoes, loafers, jacket, coat, blazer, accessory

Allowed colors:
unknown, black, white, gray, navy, blue, beige, brown, red, green, pink, purple, yellow, orange

Allowed styles:
unknown, minimal, casual, sport, classic, formal, streetwear, romantic, technical, old_money

Rules:
- Focus on the main visible garment.
- Use the dominant garment color, not the background.
- If patterned trousers are mostly green, return green, not gray.
- For winter or ski outerwear, prefer technical or sport when appropriate.

Filename: {filename}
""".strip()


def _analyze_sync(
    *,
    image_bytes: bytes,
    filename: str,
    content_type: str,
) -> Dict:
    model, processor, config = _get_model_bundle()
    original_image = load_normalized_image(image_bytes, filename, content_type)
    focused_image = _focus_on_subject(original_image)
    dominant_color, _ = _dominant_color(original_image)
    image = focused_image.resize((448, 448))
    prompt = apply_chat_template(
        processor,
        config,
        _prompt(filename),
        num_images=1,
    )
    text = generate(
        model,
        processor,
        prompt,
        image=image,
        resize_shape=(448, 448),
        temperature=0,
        max_tokens=int(os.getenv("VISION_MLX_MAX_TOKENS", "120").strip() or "120"),
        verbose=False,
    )
    parsed = _extract_json(text)

    category = _normalize_category(parsed.get("category", "unknown"))
    color = _normalize_color(parsed.get("color", "unknown"))
    style = _normalize_style(parsed.get("style", "unknown"))
    title = str(parsed.get("title") or "").strip() or _build_title(color, category)
    footwear_hint = None

    if category in {"sneakers", "boots", "shoes", "loafers"}:
        footwear_hint = _footwear_base_color_hint(original_image)

    if color in {"gray", "unknown", "white"} and dominant_color not in {"gray", "unknown", "white"}:
        color = dominant_color
        title = _build_title(color, category)

    if footwear_hint and category in {"sneakers", "boots", "shoes", "loafers"}:
        if color in {"orange", "yellow", "green", "red", "pink", "purple"}:
            color = footwear_hint
            title = _build_title(color, category)
        elif color == "black" and footwear_hint == "gray":
            color = footwear_hint
            title = _build_title(color, category)
        elif color == "blue" and footwear_hint == "navy":
            color = footwear_hint
            title = _build_title(color, category)

    return {
        "title": title,
        "category": category,
        "color": color,
        "style": style,
        "source": "mlx",
    }


async def analyze_image_mlx(
    *,
    image_bytes: bytes,
    filename: str,
    content_type: str,
) -> Dict:
    try:
        return await asyncio.to_thread(
            _analyze_sync,
            image_bytes=image_bytes,
            filename=filename,
            content_type=content_type,
        )
    except Exception as exc:
        raise VisionMLXUnavailable(f"MLX vision inference failed: {exc}") from exc
