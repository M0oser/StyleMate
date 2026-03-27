from __future__ import annotations

from typing import Any, Mapping

from normalizers.colors import infer_pattern, normalize_color_family
from normalizers.products import NormalizedShopProduct
from normalizers.sizes import derive_size_range_notes
from vocab.fashion import STORE_SOURCE_PREFERENCE


def enrich_normalized_product(product: NormalizedShopProduct) -> dict[str, Any]:
    image_count = len(product.images)
    size_notes = derive_size_range_notes(product.sizes)
    return _build_tags(
        source_store=product.source_store,
        title=product.title,
        category=product.category,
        role=product.role,
        price=product.current_price,
        description=product.description_raw,
        material=product.material_raw,
        fit=product.fit_raw,
        color_raw=product.color_raw,
        image_count=image_count,
        size_notes=size_notes,
    )


def enrich_catalog_record(record: Mapping[str, Any]) -> dict[str, Any]:
    size_notes = derive_size_range_notes(
        [
            _SizeProxy(size["size_label"])
            for size in record.get("sizes", [])
            if size.get("size_label")
        ]
    )
    return _build_tags(
        source_store=record["source_store"],
        title=record["title"],
        category=record["category"],
        role=(record.get("role") or _role_from_category(record["category"])),
        price=float(record["current_price"]) if record.get("current_price") is not None else None,
        description=record.get("description_raw"),
        material=record.get("material_raw"),
        fit=record.get("fit_raw"),
        color_raw=record.get("color_raw"),
        image_count=len(record.get("images", [])),
        size_notes=size_notes,
    )


def _build_tags(
    *,
    source_store: str,
    title: str,
    category: str,
    role: str,
    price: float | None,
    description: str | None,
    material: str | None,
    fit: str | None,
    color_raw: str | None,
    image_count: int,
    size_notes: list[str],
) -> dict[str, Any]:
    text = " ".join(filter(None, [title, description, material, fit])).lower()
    color_family = normalize_color_family(color_raw, title=title, description=description or "")
    style_primary = _infer_style_primary(role, category, text)
    style_secondary = _infer_style_secondary(role, text)
    formality = _infer_formality(role, category, text)
    season_tags = _infer_season_tags(role, category, material, text)
    warmth_level = _infer_warmth_level(role, category, material, text)
    weather_tags = _infer_weather_tags(season_tags, warmth_level)
    occasion_tags, scenario_tags = _infer_occasion_and_scenario(role, style_primary, formality, text)
    fit_type = _infer_fit_type(text)
    silhouette = _infer_silhouette(role, fit_type, text)
    pattern = infer_pattern(title, description)
    body_fit_notes = _infer_body_fit_notes(role, fit_type, text, size_notes)
    body_size_relevance = _infer_body_size_relevance(role, size_notes, text)
    pairing_tags = _build_pairing_tags(role, style_primary)
    avoid_pairing_tags = _build_avoid_pairing_tags(role, formality)
    source_preference_score = STORE_SOURCE_PREFERENCE.get(source_store, 0.75)
    image_quality_score = min(1.0, 0.35 + 0.1 * image_count)
    metadata_completeness_score = _metadata_completeness_score(
        price=price,
        description=description,
        material=material,
        fit=fit,
        color_raw=color_raw,
        image_count=image_count,
        size_notes=size_notes,
    )

    return {
        "role": role,
        "style_primary": style_primary,
        "style_secondary": style_secondary,
        "formality": formality,
        "budget_tier": _infer_budget_tier(price),
        "season_tags": season_tags,
        "weather_tags": weather_tags,
        "occasion_tags": occasion_tags,
        "scenario_tags": scenario_tags,
        "warmth_level": warmth_level,
        "fit_type": fit_type,
        "silhouette": silhouette,
        "color_family": color_family,
        "pattern": pattern,
        "body_fit_notes": body_fit_notes,
        "body_size_relevance": body_size_relevance,
        "pairing_tags": pairing_tags,
        "avoid_pairing_tags": avoid_pairing_tags,
        "source_preference_score": round(source_preference_score, 2),
        "image_quality_score": round(image_quality_score, 2),
        "metadata_completeness_score": round(metadata_completeness_score, 2),
    }


def _infer_style_primary(role: str, category: str, text: str) -> str:
    if role in {"active_top", "active_bottom", "running_shoes"}:
        return "activewear"
    if any(keyword in text for keyword in {"oversize", "деним", "cargo", "street", "streetwear"}):
        return "street casual"
    if category in {"blazer", "trousers", "loafers"} or any(keyword in text for keyword in {"tailored", "office", "пиджак"}):
        return "office casual"
    if category in {"dress", "skirt", "blouse", "heels"}:
        return "feminine casual"
    if any(keyword in text for keyword in {"basic", "minimal", "однотон"}):
        return "minimal"
    if role == "outerwear":
        return "smart casual"
    return "casual"


def _infer_style_secondary(role: str, text: str) -> list[str]:
    secondary: list[str] = []
    if role in {"active_top", "active_bottom", "running_shoes"}:
        secondary.extend(["sporty casual", "activewear"])
        if any(keyword in text for keyword in {"running", "бег", "trail"}):
            secondary.append("outdoor casual")
    if any(keyword in text for keyword in {"basic", "капсул", "wardrobe"}):
        secondary.append("basic wardrobe")
    if any(keyword in text for keyword in {"trend", "studio", "fashion"}):
        secondary.append("trendy mainstream")
    if any(keyword in text for keyword in {"outdoor", "trail", "hiking"}):
        secondary.append("outdoor casual")
    return list(dict.fromkeys(secondary))


def _infer_formality(role: str, category: str, text: str) -> str:
    if role in {"active_top", "active_bottom", "running_shoes"}:
        return "sport"
    if category in {"blazer", "loafers", "heels"}:
        return "smart"
    if category in {"dress", "blouse", "shirt", "trousers"}:
        return "smart_casual"
    if category in {"hoodie", "sweatshirt", "jeans", "sneakers"}:
        return "casual"
    if any(keyword in text for keyword in {"tailored", "structured"}):
        return "smart_casual"
    return "casual"


def _infer_budget_tier(price: float | None) -> str:
    if price is None:
        return "mid"
    if price < 3000:
        return "low"
    if price < 7000:
        return "lower_mid"
    if price < 15000:
        return "mid"
    return "upper_mid"


def _infer_season_tags(role: str, category: str, material: str | None, text: str) -> list[str]:
    tags: list[str] = []
    material_text = (material or "").lower()
    if category in {"coat", "boots"} or any(keyword in material_text for keyword in {"шерст", "wool", "утепл"}):
        tags.extend(["autumn", "winter"])
    if category in {"trench", "blazer", "jacket"}:
        tags.extend(["spring", "autumn"])
    if category in {"dress", "skirt", "t_shirt", "top", "shorts", "flats"} or any(keyword in material_text for keyword in {"лен", "linen", "хлоп"}):
        tags.extend(["spring", "summer"])
    if role in {"active_top", "active_bottom", "running_shoes"}:
        tags.extend(["spring", "summer", "autumn"])
        if any(keyword in text for keyword in {"windproof", "ветров", "термо", "утепл"}):
            tags.append("winter")
    if not tags:
        tags.append("all_season")
    return list(dict.fromkeys(tags))


def _infer_warmth_level(role: str, category: str, material: str | None, text: str) -> int:
    blob = " ".join(filter(None, [material or "", text]))
    if category in {"coat", "boots"} or any(keyword in blob for keyword in {"шерст", "утепл", "puffer"}):
        return 4
    if category in {"jacket", "blazer", "knitwear"}:
        return 3
    if role == "running_shoes":
        return 1
    if role in {"active_top", "active_bottom"}:
        return 3 if any(keyword in blob for keyword in {"brush", "термо", "утепл"}) else 2
    return 1


def _infer_weather_tags(season_tags: list[str], warmth_level: int) -> list[str]:
    tags: list[str] = []
    if "summer" in season_tags:
        tags.append("warm")
    if "spring" in season_tags or "autumn" in season_tags:
        tags.append("mild")
    if "winter" in season_tags or (warmth_level >= 4 and "summer" not in season_tags):
        tags.append("cold")
    if warmth_level >= 3:
        tags.append("windy")
    if warmth_level <= 2:
        tags.append("indoor")
    return list(dict.fromkeys(tags))


def _infer_occasion_and_scenario(role: str, style_primary: str, formality: str, text: str) -> tuple[list[str], list[str]]:
    occasion_tags = ["casual_daily"]
    scenario_tags = ["casual_daily"]

    if role in {"active_top", "active_bottom", "running_shoes"}:
        occasion_tags = ["sport", "gym"]
        scenario_tags = ["gym", "outdoor_light"]
        if any(keyword in text for keyword in {"trail", "forest", "outdoor", "ветров", "windproof"}):
            occasion_tags.append("hiking_light")
            scenario_tags.append("outdoor_light")
        if "trail" in text or "forest" in text:
            occasion_tags.append("hiking_light")
            scenario_tags.append("running")
            scenario_tags.append("outdoor_light")
        if any(keyword in text for keyword in {"running", "бег", "run"}):
            occasion_tags.append("running")
            scenario_tags.append("running")
        if role == "running_shoes":
            occasion_tags.append("running")
            occasion_tags.append("hiking_light")
            scenario_tags.append("running")
        return list(dict.fromkeys(occasion_tags)), list(dict.fromkeys(scenario_tags))

    if formality in {"smart", "smart_casual"} or style_primary == "office casual":
        occasion_tags.append("office")
        scenario_tags.append("office")
    if style_primary in {"feminine casual", "smart casual"} or role in {"dress"}:
        occasion_tags.append("date")
        scenario_tags.append("date")
    if style_primary == "street casual":
        occasion_tags.extend(["weekend", "travel"])
        scenario_tags.append("street")

    return list(dict.fromkeys(occasion_tags)), list(dict.fromkeys(scenario_tags))


def _infer_fit_type(text: str) -> str:
    if any(keyword in text for keyword in {"oversize", "оверсайз"}):
        return "oversized"
    if any(keyword in text for keyword in {"relaxed", "свобод"}):
        return "relaxed"
    if any(keyword in text for keyword in {"slim", "притал"}):
        return "slim"
    return "regular"


def _infer_silhouette(role: str, fit_type: str, text: str) -> str:
    if role == "dress":
        return "single_column"
    if fit_type == "oversized":
        return "adds_volume"
    if fit_type == "slim":
        return "elongated"
    if role == "outerwear":
        return "layering_ready"
    return "balanced"


def _infer_body_fit_notes(role: str, fit_type: str, text: str, size_notes: list[str]) -> list[str]:
    notes = list(size_notes)
    if fit_type == "oversized":
        notes.append("works_for_oversize_preference")
        notes.append("works_for_layering")
    if fit_type == "relaxed":
        notes.append("works_for_relaxed_fit_preference")
    if fit_type == "slim":
        notes.append("slim_visual_effect")
        notes.append("elongates_silhouette")
    if role in {"outerwear", "dress"}:
        notes.append("works_for_layering")
    if any(keyword in text for keyword in {"high waist", "high-rise", "высокая посадка"}):
        notes.append("elongates_silhouette")
    return list(dict.fromkeys(notes))


def _infer_body_size_relevance(role: str, size_notes: list[str], text: str) -> list[str]:
    notes = list(size_notes)
    if role == "running_shoes" and "adult_numeric_range" in size_notes:
        notes.append("adult_shoe_range")
    if role == "running_shoes" and "junior_numeric_range" in size_notes:
        notes.append("junior_shoe_range")
    if role == "running_shoes" and "junior_shoe_range" not in notes and "adult_shoe_range" not in notes:
        notes.append("adult_shoe_range")
    if any(keyword in text for keyword in {"oversize", "оверсайз", "relaxed", "свобод"}):
        notes.append("relaxed_fit_accessible")
    return list(dict.fromkeys(notes))


def _build_pairing_tags(role: str, style_primary: str) -> list[str]:
    if role in {"top", "active_top"}:
        return ["bottom", "shoes"]
    if role in {"bottom", "active_bottom"}:
        return ["top", "shoes"]
    if role in {"shoes", "running_shoes"}:
        return ["top", "bottom"]
    if role == "outerwear":
        return ["top", "bottom", "shoes"]
    if role == "dress":
        return ["shoes", "outerwear"]
    return [style_primary]


def _build_avoid_pairing_tags(role: str, formality: str) -> list[str]:
    if role == "running_shoes":
        return ["office_only"]
    if role == "outerwear" and formality == "smart":
        return ["gym"]
    if role == "dress":
        return ["running"]
    return []


def _metadata_completeness_score(
    *,
    price: float | None,
    description: str | None,
    material: str | None,
    fit: str | None,
    color_raw: str | None,
    image_count: int,
    size_notes: list[str],
) -> float:
    score = 0.0
    score += 0.15 if price else 0
    score += 0.15 if description else 0
    score += 0.15 if material else 0
    score += 0.15 if fit else 0
    score += 0.10 if color_raw else 0
    score += min(0.20, image_count * 0.04)
    score += 0.10 if size_notes or image_count else 0
    return min(score, 1.0)


def _role_from_category(category: str) -> str:
    if category in {"trousers", "jeans", "skirt", "shorts"}:
        return "bottom"
    if category in {"sports_shorts", "leggings", "active_bottom"}:
        return "active_bottom"
    if category in {"coat", "jacket", "blazer", "trench", "vest", "track_jacket"}:
        return "outerwear"
    if category in {"active_top"}:
        return "active_top"
    if category in {"dress"}:
        return "dress"
    if category in {"running_shoes"}:
        return "running_shoes"
    if category in {"sneakers", "boots", "loafers", "heels", "flats"}:
        return "shoes"
    return "top"


class _SizeProxy:
    def __init__(self, label: str) -> None:
        self.size_label = label
