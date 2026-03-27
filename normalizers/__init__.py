"""Normalization helpers for shop and wardrobe products."""

from .categories import determine_category_fields
from .colors import infer_pattern, normalize_color_family
from .products import NormalizedShopProduct, normalize_shop_product
from .sizes import derive_size_range_notes, normalize_sizes

__all__ = [
    "NormalizedShopProduct",
    "derive_size_range_notes",
    "determine_category_fields",
    "infer_pattern",
    "normalize_color_family",
    "normalize_shop_product",
    "normalize_sizes",
]
