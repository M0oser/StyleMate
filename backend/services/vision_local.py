import colorsys
import json
import os
from dataclasses import dataclass, asdict
from functools import lru_cache
from typing import Dict, List, Optional, Tuple

try:
    import numpy as np
except Exception:
    np = None


try:
    import torch
    from PIL import Image
    import open_clip
except Exception:
    torch = None
    Image = None
    open_clip = None


CATEGORY_PROMPTS = {
    "tshirt": "a studio photo of a t-shirt or tee top",
    "top": "a studio photo of a top, tank top, camisole or blouse top",
    "shirt": "a studio photo of a shirt or overshirt",
    "sweater": "a studio photo of a sweater, cardigan, knit jumper or pullover",
    "hoodie": "a studio photo of a hoodie or sweatshirt",
    "jeans": "a studio photo of jeans or denim pants",
    "trousers": "a studio photo of trousers, pants or slacks",
    "shorts": "a studio photo of shorts",
    "skirt": "a studio photo of a skirt",
    "dress": "a studio photo of a dress",
    "sneakers": "a studio photo of sneakers or trainers",
    "boots": "a studio photo of boots",
    "shoes": "a studio photo of dress shoes or leather shoes",
    "loafers": "a studio photo of loafers",
    "jacket": "a studio photo of a jacket",
    "coat": "a studio photo of a coat or trench coat",
    "blazer": "a studio photo of a blazer or suit jacket",
    "accessory": "a studio photo of an accessory like bag, belt, scarf or hat",
}

STYLE_PROMPTS = {
    "minimal": "minimal clean simple clothing",
    "casual": "casual everyday clothing",
    "sport": "sporty athletic activewear clothing",
    "classic": "classic elegant timeless clothing",
    "formal": "formal dressy polished clothing",
    "streetwear": "streetwear urban trendy clothing",
    "romantic": "romantic soft refined clothing",
    "technical": "technical outdoor functional clothing",
    "old_money": "old money quiet luxury classic clothing",
}

COLOR_PALETTE = {
    "black": (35, 35, 35),
    "white": (235, 235, 235),
    "gray": (150, 150, 150),
    "navy": (45, 60, 100),
    "blue": (70, 110, 180),
    "beige": (214, 197, 164),
    "brown": (116, 84, 58),
    "red": (176, 61, 61),
    "green": (82, 120, 78),
    "pink": (214, 146, 164),
    "purple": (128, 98, 164),
    "yellow": (214, 190, 88),
    "orange": (214, 136, 67),
}


class LocalVisionUnavailable(RuntimeError):
    pass


@dataclass
class VisionAnalysis:
    title: str
    category: str
    color: str
    style: str
    category_confidence: float
    style_confidence: float
    dominant_rgb: Tuple[int, int, int]
    source: str

    def to_dict(self) -> Dict:
        return asdict(self)


def _device_name() -> str:
    if torch is None:
        raise LocalVisionUnavailable("torch is not available")

    if hasattr(torch.backends, "mps") and torch.backends.mps.is_available():
        return "mps"
    return "cpu"


def _normalize_text_label(value: str) -> str:
    return value.lower().strip().replace(" ", "_")


@lru_cache(maxsize=1)
def _load_clip_bundle():
    if torch is None or Image is None or open_clip is None:
        raise LocalVisionUnavailable("local vision dependencies are not installed")

    model_name = os.getenv("VISION_LOCAL_MODEL", "ViT-B-32")
    pretrained = os.getenv("VISION_LOCAL_PRETRAINED", "openai")
    explicit_checkpoint = os.getenv("VISION_LOCAL_CHECKPOINT", "").strip()
    default_checkpoint = os.path.abspath(
        os.path.join(os.getcwd(), "models", "vit_base_patch32_clip_224.openai.safetensors")
    )
    checkpoint_path = explicit_checkpoint or (default_checkpoint if os.path.exists(default_checkpoint) else "")

    if checkpoint_path:
        pretrained = checkpoint_path

    device = _device_name()

    model, _, preprocess = open_clip.create_model_and_transforms(
        model_name,
        pretrained=pretrained,
        device=device,
    )
    tokenizer = open_clip.get_tokenizer(model_name)
    model.eval()

    category_labels = list(CATEGORY_PROMPTS.keys())
    category_prompts = [CATEGORY_PROMPTS[label] for label in category_labels]
    style_labels = list(STYLE_PROMPTS.keys())
    style_prompts = [STYLE_PROMPTS[label] for label in style_labels]

    with torch.no_grad():
        category_tokens = tokenizer(category_prompts).to(device)
        style_tokens = tokenizer(style_prompts).to(device)

        category_features = model.encode_text(category_tokens)
        style_features = model.encode_text(style_tokens)

        category_features = category_features / category_features.norm(dim=-1, keepdim=True)
        style_features = style_features / style_features.norm(dim=-1, keepdim=True)

    return {
        "model": model,
        "preprocess": preprocess,
        "device": device,
        "category_labels": category_labels,
        "category_features": category_features,
        "style_labels": style_labels,
        "style_features": style_features,
    }


def _distance(a: Tuple[int, int, int], b: Tuple[int, int, int]) -> float:
    return ((a[0] - b[0]) ** 2 + (a[1] - b[1]) ** 2 + (a[2] - b[2]) ** 2) ** 0.5


def _foreground_bbox(image: "Image.Image") -> Optional[Tuple[int, int, int, int]]:
    if np is None:
        return None

    rgb_image = image.convert("RGB")
    width, height = rgb_image.size
    if width < 48 or height < 48:
        return None

    preview = rgb_image.copy()
    preview.thumbnail((256, 256))
    arr = np.asarray(preview).astype(np.float32)
    h, w, _ = arr.shape
    edge = max(4, int(min(h, w) * 0.08))

    top = arr[:edge, :, :].reshape(-1, 3)
    bottom = arr[-edge:, :, :].reshape(-1, 3)
    left = arr[:, :edge, :].reshape(-1, 3)
    right = arr[:, -edge:, :].reshape(-1, 3)
    border = np.concatenate([top, bottom, left, right], axis=0)

    bg = np.median(border, axis=0)
    border_sat = (border.max(axis=1) - border.min(axis=1)) / 255.0
    bg_sat = float(np.median(border_sat))

    dist = np.linalg.norm(arr - bg, axis=2)
    sat = (arr.max(axis=2) - arr.min(axis=2)) / 255.0

    yy, xx = np.mgrid[0:h, 0:w]
    cx = (w - 1) / 2.0
    cy = (h - 1) / 2.0
    center_weight = 1.0 - np.sqrt(((xx - cx) / max(cx, 1)) ** 2 + ((yy - cy) / max(cy, 1)) ** 2)

    dist_threshold = max(26.0, float(np.percentile(dist, 68)))
    sat_threshold = max(0.16, bg_sat + 0.08)
    mask = (dist > dist_threshold) | (sat > sat_threshold)
    refined_mask = mask & ((center_weight > 0.08) | (dist > dist_threshold * 1.2))

    ys, xs = np.where(refined_mask)
    if xs.size < 24 or ys.size < 24:
        ys, xs = np.where(mask)

    if xs.size < 24 or ys.size < 24:
        return None

    x0_small = int(xs.min())
    y0_small = int(ys.min())
    x1_small = int(xs.max())
    y1_small = int(ys.max())

    bbox_area_ratio = ((x1_small - x0_small + 1) * (y1_small - y0_small + 1)) / float(w * h)
    if bbox_area_ratio < 0.04 or bbox_area_ratio > 0.94:
        return None

    scale_x = width / float(w)
    scale_y = height / float(h)
    x0 = int(x0_small * scale_x)
    y0 = int(y0_small * scale_y)
    x1 = int((x1_small + 1) * scale_x)
    y1 = int((y1_small + 1) * scale_y)

    pad_x = int((x1 - x0) * 0.12)
    pad_y = int((y1 - y0) * 0.12)
    x0 = max(0, x0 - pad_x)
    y0 = max(0, y0 - pad_y)
    x1 = min(width, x1 + pad_x)
    y1 = min(height, y1 + pad_y)

    if (x1 - x0) < width * 0.18 or (y1 - y0) < height * 0.18:
        return None

    return x0, y0, x1, y1


def _focus_on_subject(image: "Image.Image") -> "Image.Image":
    bbox = _foreground_bbox(image)
    if not bbox:
        return image.convert("RGB")
    return image.convert("RGB").crop(bbox)


def _footwear_base_color_hint(image: "Image.Image") -> Optional[str]:
    rgb_image = image.convert("RGB")
    width, height = rgb_image.size
    if width < 80 or height < 80:
        return None

    crop = rgb_image.crop(
        (
            int(width * 0.28),
            int(height * 0.40),
            int(width * 0.78),
            int(height * 0.92),
        )
    )
    crop.thumbnail((180, 180))

    neutral_pixels: List[Tuple[int, int, int, float, float, float]] = []
    vivid_pixels: List[Tuple[float, float, float]] = []

    for r, g, b in crop.getdata():
        h, s, v = colorsys.rgb_to_hsv(r / 255, g / 255, b / 255)
        if v < 0.12 or v > 0.97:
            continue

        # De-emphasize skin-like warm tones from legs/background.
        if r > 120 and g > 80 and b > 55 and r > g > b and (r - b) > 25:
            continue

        if s <= 0.30:
            neutral_pixels.append((r, g, b, h, s, v))
        else:
            vivid_pixels.append((h, s, v))

    if len(neutral_pixels) < 200:
        return None

    avg_r = sum(pixel[0] for pixel in neutral_pixels) / len(neutral_pixels)
    avg_g = sum(pixel[1] for pixel in neutral_pixels) / len(neutral_pixels)
    avg_b = sum(pixel[2] for pixel in neutral_pixels) / len(neutral_pixels)
    avg_h = sum(pixel[3] for pixel in neutral_pixels) / len(neutral_pixels)
    avg_s = sum(pixel[4] for pixel in neutral_pixels) / len(neutral_pixels)
    avg_v = sum(pixel[5] for pixel in neutral_pixels) / len(neutral_pixels)

    if avg_s < 0.08:
        if avg_v < 0.25:
            return "black"
        if avg_v > 0.82:
            return "white"
        return "gray"

    if avg_h >= 0.52 and avg_h <= 0.74 and avg_v < 0.48:
        return "navy"

    warm_balance = avg_r - avg_b
    if warm_balance > 18:
        if avg_v >= 0.60:
            return "beige"
        return "brown"

    if avg_v < 0.32:
        return "black"
    if avg_v < 0.72:
        return "gray"
    return "white"


def _dominant_color(image: "Image.Image") -> Tuple[str, Tuple[int, int, int]]:
    cropped = _focus_on_subject(image)
    width, height = cropped.size
    left = int(width * 0.08)
    top = int(height * 0.08)
    right = int(width * 0.92)
    bottom = int(height * 0.92)
    cropped = cropped.crop((left, top, right, bottom))
    cropped.thumbnail((180, 180))

    weighted: List[Tuple[Tuple[int, int, int], float]] = []
    hue_votes = {name: 0.0 for name in COLOR_PALETTE.keys()}

    for pixel in cropped.getdata():
        r, g, b = pixel
        value_max = max(r, g, b)
        value_min = min(r, g, b)
        mean_value = (r + g + b) / 3

        # Ignore near-white studio background.
        if value_max >= 242 and (value_max - value_min) <= 18 and mean_value >= 236:
            continue

        h, s, v = colorsys.rgb_to_hsv(r / 255, g / 255, b / 255)
        base_weight = 1.0 + s * 3.0
        weighted.append(((r, g, b), base_weight))

        if s < 0.12:
            if v < 0.22:
                hue_votes["black"] += 1.3
            elif v > 0.88:
                hue_votes["white"] += 1.0
            else:
                hue_votes["gray"] += 1.1
            continue

        vote = 1.0 + s * 2.0
        if (0.20 <= h <= 0.45) or (g > r + 10 and g > b + 10):
            hue_votes["green"] += vote * 1.5
        elif 0.52 <= h <= 0.75:
            hue_votes["blue" if v > 0.35 else "navy"] += vote
        elif 0.08 <= h < 0.20:
            hue_votes["yellow" if v > 0.72 else "orange"] += vote
        elif h >= 0.90 or h < 0.04:
            hue_votes["red"] += vote
        elif 0.04 <= h < 0.08:
            hue_votes["orange"] += vote
        elif 0.75 < h < 0.90:
            hue_votes["purple" if v < 0.75 else "pink"] += vote
        elif r > g + 18 and r > b + 18:
            hue_votes["red"] += vote
        elif b > r + 12 and b > g + 12:
            hue_votes["blue"] += vote
        else:
            hue_votes["gray"] += 0.4

    if not weighted:
        rgb = (180, 180, 180)
    else:
        total = sum(weight for _, weight in weighted)
        rgb = (
            int(sum(color[0] * weight for color, weight in weighted) / total),
            int(sum(color[1] * weight for color, weight in weighted) / total),
            int(sum(color[2] * weight for color, weight in weighted) / total),
        )

    palette_match = min(COLOR_PALETTE.items(), key=lambda item: _distance(rgb, item[1]))[0]
    voted_color = max(hue_votes.items(), key=lambda item: item[1])[0]

    if hue_votes[voted_color] >= max(hue_votes.get("gray", 0.0) * 1.15, 2.5):
        color_name = voted_color
    else:
        color_name = palette_match

    return color_name, rgb


def _predict_label(image: "Image.Image", labels_key: str) -> Tuple[str, float]:
    bundle = _load_clip_bundle()
    model = bundle["model"]
    preprocess = bundle["preprocess"]
    device = bundle["device"]
    labels = bundle[f"{labels_key}_labels"]
    text_features = bundle[f"{labels_key}_features"]

    image_input = preprocess(image).unsqueeze(0).to(device)

    with torch.no_grad():
        image_features = model.encode_image(image_input)
        image_features = image_features / image_features.norm(dim=-1, keepdim=True)
        logits = (100.0 * image_features @ text_features.T).softmax(dim=-1)[0]

    best_idx = int(logits.argmax().item())
    confidence = float(logits[best_idx].item())
    return labels[best_idx], round(confidence, 4)


def analyze_image_local(image_path: str) -> VisionAnalysis:
    if Image is None:
        raise LocalVisionUnavailable("Pillow is not available")

    if not os.path.exists(image_path):
        raise FileNotFoundError(image_path)

    with Image.open(image_path) as img:
        image = img.convert("RGB")
        focused_image = _focus_on_subject(image)
        color_name, dominant_rgb = _dominant_color(focused_image)
        category, category_conf = _predict_label(focused_image, "category")
        style, style_conf = _predict_label(focused_image, "style")
        footwear_hint = None

        if _normalize_text_label(category) in {"sneakers", "boots", "shoes", "loafers"}:
            footwear_hint = _footwear_base_color_hint(image)

        if footwear_hint:
            if color_name in {"orange", "yellow", "green", "red", "pink", "purple"}:
                color_name = footwear_hint
            elif color_name == "black" and footwear_hint == "gray":
                color_name = footwear_hint
            elif color_name == "blue" and footwear_hint == "navy":
                color_name = footwear_hint

    title = f"{color_name.capitalize()} {category.capitalize()}"
    return VisionAnalysis(
        title=title,
        category=_normalize_text_label(category),
        color=_normalize_text_label(color_name),
        style=_normalize_text_label(style),
        category_confidence=category_conf,
        style_confidence=style_conf,
        dominant_rgb=dominant_rgb,
        source="local",
    )


def save_analysis_json(analysis: Dict, output_path: str) -> None:
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(analysis, f, ensure_ascii=False, indent=2)
