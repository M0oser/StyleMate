from __future__ import annotations

from dataclasses import dataclass, field

from normalizers.products import NormalizedShopProduct
from normalizers.sizes import is_probable_junior_footwear_range
from vocab.fashion import BLOCKED_CURATION_KEYWORDS


@dataclass
class CurationDecision:
    keep: bool
    reasons: list[str] = field(default_factory=list)


def evaluate_curated_subset(product: NormalizedShopProduct) -> CurationDecision:
    reasons: list[str] = []
    text = " ".join(
        filter(
            None,
            [
                product.title.lower(),
                (product.description_raw or "").lower(),
                (product.subcategory or "").lower(),
            ],
        )
    )

    if any(keyword in text for keyword in BLOCKED_CURATION_KEYWORDS):
        return CurationDecision(False, ["out_of_scope_keyword"])

    if product.role not in {
        "top",
        "bottom",
        "shoes",
        "outerwear",
        "dress",
        "active_top",
        "active_bottom",
        "running_shoes",
    }:
        return CurationDecision(False, ["unsupported_role"])

    if not product.primary_image_url:
        return CurationDecision(False, ["missing_primary_image"])
    if not product.current_price:
        return CurationDecision(False, ["missing_price"])
    if not product.sizes:
        return CurationDecision(False, ["missing_sizes"])
    if product.gender_target not in {"women", "unisex", "broad"}:
        return CurationDecision(False, ["unsupported_gender_target"])
    if product.role in {"shoes", "running_shoes"} and is_probable_junior_footwear_range(product.sizes):
        return CurationDecision(False, ["junior_shoe_range"])

    if len(product.images) < 2:
        reasons.append("limited_image_set")
    if len(product.sizes) <= 2:
        reasons.append("limited_size_depth")

    price = product.current_price or 0
    if product.role == "outerwear" and price > 60000:
        return CurationDecision(False, ["price_outlier_for_mass_market"])
    if product.role != "outerwear" and price > 40000:
        return CurationDecision(False, ["price_outlier_for_mass_market"])

    if any(keyword in text for keyword in {"карнавал", "costume", "bridal", "свадеб", "latex", "корсет"}):
        return CurationDecision(False, ["too_editorial_for_completion_flow"])

    return CurationDecision(True, reasons)
