import colorsys
import math
import os
from functools import lru_cache
from typing import Dict, List, Optional, Tuple


try:
    import torch
    from PIL import Image, ImageFilter
    import open_clip
except Exception:
    torch = None
    Image = None
    ImageFilter = None
    open_clip = None


CATEGORY_PROMPTS = {
    "tshirt": "a studio photo of a t-shirt or tee top",
    "shirt": "a studio photo of a shirt or overshirt",
    "top": "a studio photo of a top or tank top",
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
    "jacket": "a studio photo of a jacket",
    "coat": "a studio photo of a coat or trench coat",
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
    "black": (30, 30, 30),
    "white": (236, 236, 232),
    "gray": (148, 148, 148),
    "beige": (214, 198, 165),
    "brown": (116, 82, 56),
    "red": (178, 61, 65),
    "orange": (214, 132, 66),
    "yellow": (214, 188, 90),
    "green": (78, 122, 86),
    "blue": (67, 114, 188),
    "navy": (45, 60, 100),
    "purple": (128, 96, 164),
    "pink": (216, 150, 176),
}

MIN_DOMINANT_SHARE = 0.42
MIN_SECONDARY_SHARE = 0.08
MIN_CLUSTER_SHARE = 0.015


class LocalVisionUnavailable(RuntimeError):
    pass


def _normalize_text_label(value: str) -> str:
    return str(value or "").lower().strip().replace(" ", "_")


def _device_name() -> str:
    if torch is None:
        raise LocalVisionUnavailable("torch is not available")
    if hasattr(torch.backends, "mps") and torch.backends.mps.is_available():
        return "mps"
    return "cpu"


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
    style_labels = list(STYLE_PROMPTS.keys())

    with torch.no_grad():
        category_tokens = tokenizer([CATEGORY_PROMPTS[label] for label in category_labels]).to(device)
        style_tokens = tokenizer([STYLE_PROMPTS[label] for label in style_labels]).to(device)

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
    return labels[best_idx], round(float(logits[best_idx].item()), 4)


def _resampling():
    return getattr(Image, "Resampling", Image).LANCZOS


def _color_distance(a: Tuple[int, int, int], b: Tuple[int, int, int]) -> float:
    return math.sqrt(sum((x - y) ** 2 for x, y in zip(a, b)))


def _median_channel(values: List[int]) -> int:
    ordered = sorted(values)
    if not ordered:
        return 255
    mid = len(ordered) // 2
    if len(ordered) % 2:
        return ordered[mid]
    return int((ordered[mid - 1] + ordered[mid]) / 2)


def _estimate_background_color(image: "Image.Image") -> Tuple[int, int, int]:
    width, height = image.size
    border_x = max(2, int(width * 0.08))
    border_y = max(2, int(height * 0.08))
    samples: List[Tuple[int, int, int]] = []

    for y in range(height):
        for x in range(width):
            if x < border_x or x >= width - border_x or y < border_y or y >= height - border_y:
                samples.append(image.getpixel((x, y)))

    return (
        _median_channel([pixel[0] for pixel in samples]),
        _median_channel([pixel[1] for pixel in samples]),
        _median_channel([pixel[2] for pixel in samples]),
    )


def _build_foreground_mask(image: "Image.Image") -> Optional["Image.Image"]:
    working = image.convert("RGB").copy()
    working.thumbnail((384, 384), _resampling())
    bg_color = _estimate_background_color(working)
    bg_h, bg_s, bg_v = colorsys.rgb_to_hsv(*(channel / 255 for channel in bg_color))

    mask = Image.new("L", working.size, 0)
    pixels = []
    for r, g, b in working.getdata():
        h, s, v = colorsys.rgb_to_hsv(r / 255, g / 255, b / 255)
        distance = _color_distance((r, g, b), bg_color)

        is_foreground = (
            distance > 42
            or (s > 0.18 and abs(v - bg_v) > 0.06)
            or (v < 0.22 and bg_v > 0.35)
        )
        pixels.append(255 if is_foreground else 0)

    mask.putdata(pixels)
    mask = mask.filter(ImageFilter.MedianFilter(5))
    mask = mask.filter(ImageFilter.MaxFilter(5))
    mask = mask.filter(ImageFilter.MedianFilter(3))

    if not mask.getbbox():
        return None

    original_mask = mask.resize(image.size, _resampling())
    original_mask = original_mask.point(lambda value: 255 if value > 90 else 0)
    return original_mask


def detect_item_region(image_path: str) -> Optional[Dict]:
    """Detect a likely clothing object region using foreground-vs-background separation."""
    if Image is None:
        raise LocalVisionUnavailable("Pillow is not available")
    if not os.path.exists(image_path):
        raise FileNotFoundError(image_path)

    with Image.open(image_path) as img:
        image = img.convert("RGB")
        mask = _build_foreground_mask(image)
        if mask is None:
            return None

        bbox = mask.getbbox()
        if bbox is None:
            return None

        left, top, right, bottom = bbox
        width, height = image.size
        object_area = max(1, (right - left) * (bottom - top))
        image_area = max(1, width * height)
        coverage = object_area / image_area
        if coverage < 0.08:
            return None

        pad_x = int((right - left) * 0.06)
        pad_y = int((bottom - top) * 0.06)
        padded_bbox = (
            max(0, left - pad_x),
            max(0, top - pad_y),
            min(width, right + pad_x),
            min(height, bottom + pad_y),
        )
        return {
            "bbox": padded_bbox,
            "mask": mask,
            "confidence": round(min(0.98, 0.45 + coverage * 1.4), 4),
        }


def crop_item_region(image: "Image.Image", bbox: Tuple[int, int, int, int]) -> "Image.Image":
    """Crop the detected object region from the image."""
    return image.crop(bbox)


def _mask_crop(crop: "Image.Image", mask_crop: Optional["Image.Image"]) -> "Image.Image":
    if mask_crop is None:
        return crop.convert("RGBA")

    rgba = crop.convert("RGBA")
    rgba.putalpha(mask_crop.resize(crop.size, _resampling()))
    return rgba


def _closest_palette_name(rgb: Tuple[int, int, int]) -> str:
    return min(COLOR_PALETTE.items(), key=lambda item: _color_distance(rgb, item[1]))[0]


def extract_dominant_colors(cropped_image: "Image.Image") -> List[Dict]:
    """Extract dominant colors from the object crop, ignoring transparent/background pixels."""
    image = cropped_image.convert("RGBA").copy()
    image.thumbnail((160, 160), _resampling())

    bins: Dict[Tuple[int, int, int], Dict[str, float]] = {}
    valid_pixels = 0

    for r, g, b, a in image.getdata():
        if a < 24:
            continue

        h, s, v = colorsys.rgb_to_hsv(r / 255, g / 255, b / 255)
        if a < 70 and v > 0.96 and s < 0.08:
            continue

        key = (r // 32, g // 32, b // 32)
        if key not in bins:
            bins[key] = {"count": 0, "r": 0.0, "g": 0.0, "b": 0.0}

        bins[key]["count"] += 1
        bins[key]["r"] += r
        bins[key]["g"] += g
        bins[key]["b"] += b
        valid_pixels += 1

    if valid_pixels == 0:
        return []

    raw_clusters: List[Dict] = []
    for value in bins.values():
        share = value["count"] / valid_pixels
        if share < MIN_CLUSTER_SHARE:
            continue
        rgb = (
            int(value["r"] / value["count"]),
            int(value["g"] / value["count"]),
            int(value["b"] / value["count"]),
        )
        raw_clusters.append(
            {
                "color": _closest_palette_name(rgb),
                "rgb": list(rgb),
                "share": round(share, 4),
            }
        )

    aggregated: Dict[str, Dict] = {}
    for cluster in raw_clusters:
        label = cluster["color"]
        entry = aggregated.setdefault(label, {"color": label, "share": 0.0, "weighted_rgb": [0.0, 0.0, 0.0]})
        entry["share"] += cluster["share"]
        for index, channel in enumerate(cluster["rgb"]):
            entry["weighted_rgb"][index] += channel * cluster["share"]

    result = []
    for value in aggregated.values():
        share = value["share"]
        if share <= 0:
            continue
        rgb = [int(channel / share) for channel in value["weighted_rgb"]]
        result.append(
            {
                "color": value["color"],
                "rgb": rgb,
                "share": round(share, 4),
            }
        )

    result.sort(key=lambda item: item["share"], reverse=True)
    return result


def classify_item_color(cropped_image: "Image.Image") -> Dict:
    """Classify main and secondary colors from the cropped item region."""
    aggregated = extract_dominant_colors(cropped_image)
    if not aggregated:
        return {
            "dominant_color": "unknown",
            "secondary_colors": [],
            "raw_detected_colors": [],
            "color_confidence": 0.0,
        }

    dominant = aggregated[0]
    second = aggregated[1] if len(aggregated) > 1 else None
    dominant_color = dominant["color"]

    if second and dominant["share"] < MIN_DOMINANT_SHARE and (dominant["share"] - second["share"]) < 0.08:
        dominant_color = "multicolor"

    secondary = [
        item["color"]
        for item in aggregated[1:]
        if item["share"] >= MIN_SECONDARY_SHARE and item["color"] != dominant_color
    ][:3]

    confidence = 0.45 + min(0.45, dominant["share"]) + (0.08 if not second else min(0.12, dominant["share"] - second["share"]))
    if dominant_color == "multicolor":
        confidence -= 0.12

    return {
        "dominant_color": dominant_color,
        "secondary_colors": secondary,
        "raw_detected_colors": aggregated,
        "color_confidence": round(max(0.0, min(0.99, confidence)), 4),
    }


def analyze_item_image(image_path: str) -> Dict:
    """Analyze item type and color using crop-first localization and object-only color statistics."""
    if Image is None:
        raise LocalVisionUnavailable("Pillow is not available")
    if not os.path.exists(image_path):
        raise FileNotFoundError(image_path)

    with Image.open(image_path) as img:
        image = img.convert("RGB")
        region = detect_item_region(image_path)

        used_crop = bool(region)
        bbox = region["bbox"] if region else None
        crop = crop_item_region(image, bbox) if bbox else image.copy()
        mask_crop = region["mask"].crop(bbox) if region and region.get("mask") is not None else None
        masked_crop = _mask_crop(crop, mask_crop)

        item_type, category_confidence = _predict_label(crop if used_crop else image, "category")
        style, style_confidence = _predict_label(crop if used_crop else image, "style")
        color_info = classify_item_color(masked_crop if used_crop else _mask_crop(image, _build_foreground_mask(image)))

    combined_confidence = (
        category_confidence * 0.55
        + color_info["color_confidence"] * 0.35
        + (0.10 if used_crop else 0.0)
    )

    return {
        "item_type": _normalize_text_label(item_type),
        "category": _normalize_text_label(item_type),
        "dominant_color": _normalize_text_label(color_info["dominant_color"]),
        "color": _normalize_text_label(color_info["dominant_color"]),
        "secondary_colors": [_normalize_text_label(value) for value in color_info["secondary_colors"]],
        "raw_detected_colors": color_info["raw_detected_colors"],
        "style": _normalize_text_label(style),
        "confidence": round(min(0.99, combined_confidence), 4),
        "category_confidence": category_confidence,
        "style_confidence": style_confidence,
        "used_crop": used_crop,
        "bbox": list(bbox) if bbox else None,
        "source": "local",
    }
