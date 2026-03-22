import json
import os
from dataclasses import asdict, dataclass
from typing import Dict, List, Optional, Tuple

from backend.services.vision_color_service import (
    LocalVisionUnavailable,
    analyze_item_image,
)


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
    confidence: float
    used_crop: bool
    bbox: Optional[List[int]] = None
    secondary_colors: Optional[List[str]] = None
    raw_detected_colors: Optional[List[Dict]] = None

    def to_dict(self) -> Dict:
        return asdict(self)


def analyze_image_local(image_path: str) -> VisionAnalysis:
    analysis = analyze_item_image(image_path)
    raw_colors = analysis.get("raw_detected_colors") or []
    dominant_rgb = tuple(raw_colors[0]["rgb"]) if raw_colors else (180, 180, 180)

    title = f'{analysis["dominant_color"].capitalize()} {analysis["item_type"].capitalize()}'
    return VisionAnalysis(
        title=title,
        category=analysis["category"],
        color=analysis["color"],
        style=analysis["style"],
        category_confidence=float(analysis.get("category_confidence", 0.0)),
        style_confidence=float(analysis.get("style_confidence", 0.0)),
        dominant_rgb=dominant_rgb,
        source=str(analysis.get("source", "local")),
        confidence=float(analysis.get("confidence", 0.0)),
        used_crop=bool(analysis.get("used_crop", False)),
        bbox=analysis.get("bbox"),
        secondary_colors=analysis.get("secondary_colors") or [],
        raw_detected_colors=raw_colors,
    )


def save_analysis_json(analysis: Dict, output_path: str) -> None:
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(analysis, f, ensure_ascii=False, indent=2)
