from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from normalizers.categories import determine_category_fields
from normalizers.sizes import normalize_sizes
from parsers.models import ParsedImage, ParsedProduct, ParsedSize


@dataclass
class NormalizedShopProduct:
    source_store: str
    source_product_id: str
    title: str
    brand: str | None
    category: str
    subcategory: str | None
    role: str
    gender_target: str
    current_price: float | None
    old_price: float | None
    currency: str
    product_url: str
    primary_image_url: str | None
    description_raw: str | None
    material_raw: str | None
    fit_raw: str | None
    color_raw: str | None
    availability_raw: str | None
    images: list[ParsedImage]
    sizes: list[ParsedSize]
    raw_payload: dict[str, Any]


def normalize_shop_product(product: ParsedProduct) -> NormalizedShopProduct | None:
    category_info = determine_category_fields(
        product.title,
        source_category=product.category,
        source_subcategory=product.subcategory,
    )
    if not category_info["category"] or not category_info["role"]:
        return None

    return NormalizedShopProduct(
        source_store=product.source_store,
        source_product_id=product.source_product_id,
        title=" ".join(product.title.split()),
        brand=product.brand,
        category=category_info["category"],
        subcategory=category_info["subcategory"],
        role=category_info["role"],
        gender_target=product.gender_target or "women",
        current_price=product.current_price,
        old_price=product.old_price,
        currency=product.currency or "RUB",
        product_url=product.product_url,
        primary_image_url=product.primary_image_url,
        description_raw=product.description_raw,
        material_raw=product.material_raw,
        fit_raw=product.fit_raw,
        color_raw=product.color_raw,
        availability_raw=product.availability_raw,
        images=product.images,
        sizes=normalize_sizes(product.sizes),
        raw_payload=product.raw_payload,
    )
