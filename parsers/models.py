from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class ParsedImage:
    url: str
    sort_order: int = 0


@dataclass
class ParsedSize:
    size_label: str
    size_system: str | None = None
    size_value: str | None = None
    availability: str = "unknown"
    size_notes: str | None = None


@dataclass
class ParsedProduct:
    source_store: str
    source_product_id: str
    title: str
    brand: str | None
    category: str | None
    subcategory: str | None
    gender_target: str
    current_price: float | None
    old_price: float | None
    currency: str
    product_url: str
    primary_image_url: str | None
    description_raw: str | None = None
    material_raw: str | None = None
    fit_raw: str | None = None
    color_raw: str | None = None
    availability_raw: str | None = None
    images: list[ParsedImage] = field(default_factory=list)
    sizes: list[ParsedSize] = field(default_factory=list)
    raw_payload: dict[str, Any] = field(default_factory=dict)
