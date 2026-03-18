import colorsys
import json
import os
from dataclasses import dataclass, asdict
from functools import lru_cache
from typing import Dict, List, Optional, Tuple


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
    "shirt": "a studio photo of a shirt or overshirt",
    "sweater": "a studio photo of a sweater, cardigan, knit jumper or pullover",
    "hoodie": "a studio photo of a hoodie or sweatshirt",
    "jeans": "a studio photo of jeans or denim pants",
    "trousers": "a studio photo of trousers, pants or slacks",
    "shorts": "a studio photo of shorts",
    "skirt": "a studio photo of a skirt",
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


def _dominant_color(image: "Image.Image") -> Tuple[str, Tuple[int, int, int]]:
    cropped = image.convert("RGB")
    width, height = cropped.size
    left = int(width * 0.15)
    top = int(height * 0.15)
    right = int(width * 0.85)
    bottom = int(height * 0.85)
    cropped = cropped.crop((left, top, right, bottom))
    cropped.thumbnail((120, 120))

    weighted: List[Tuple[Tuple[int, int, int], float]] = []
    for pixel in cropped.getdata():
        r, g, b = pixel
        h, s, v = colorsys.rgb_to_hsv(r / 255, g / 255, b / 255)

        # Skip likely background pixels.
        if v > 0.97 and s < 0.08:
            continue

        weight = 1.0 + s * 2.5
        if v < 0.18:
            weight += 0.8
        weighted.append(((r, g, b), weight))

    if not weighted:
        rgb = (180, 180, 180)
    else:
        total = sum(weight for _, weight in weighted)
        rgb = (
            int(sum(color[0] * weight for color, weight in weighted) / total),
            int(sum(color[1] * weight for color, weight in weighted) / total),
            int(sum(color[2] * weight for color, weight in weighted) / total),
        )

    color_name = min(COLOR_PALETTE.items(), key=lambda item: _distance(rgb, item[1]))[0]
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
        color_name, dominant_rgb = _dominant_color(image)
        category, category_conf = _predict_label(image, "category")
        style, style_conf = _predict_label(image, "style")

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
