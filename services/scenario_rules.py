from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from typing import Any, Iterable, Mapping, Sequence

from normalizers.colors import normalize_color_family
from services.completion_errors import (
    InvalidRequestError,
    InvalidScenarioError,
    InvalidSeasonError,
    NoAnchorsSelectedError,
)


SCENARIO_ALIASES = {
    "casual": "casual_daily",
    "casual_daily": "casual_daily",
    "office": "office",
    "date": "date",
    "street": "street",
    "gym": "gym",
    "running": "running",
    "outdoor": "outdoor_light",
    "outdoor-light": "outdoor_light",
    "outdoor_light": "outdoor_light",
}

SEASON_PRESETS = {
    "summer": {"season_tags": ["summer"], "weather_tags": ["warm"]},
    "winter": {"season_tags": ["winter"], "weather_tags": ["cold", "windy"]},
    "spring": {"season_tags": ["spring"], "weather_tags": ["mild", "windy"]},
    "autumn": {"season_tags": ["autumn"], "weather_tags": ["mild", "windy"]},
    "midseason": {"season_tags": ["spring", "autumn"], "weather_tags": ["mild", "windy"]},
    "all_season": {"season_tags": [], "weather_tags": []},
}

ROLE_COVERAGE = {
    "dress": {"dress", "top", "bottom"},
    "top": {"top"},
    "bottom": {"bottom"},
    "shoes": {"shoes"},
    "outerwear": {"outerwear"},
    "active_top": {"active_top"},
    "active_bottom": {"active_bottom"},
    "running_shoes": {"running_shoes"},
}

NEUTRAL_COLORS = {"black", "white", "gray", "beige", "brown", "blue"}
SPORT_SCENARIOS = {"gym", "running", "outdoor_light"}
FORMALITY_SCALE = {
    "sport": 0,
    "casual": 1,
    "smart_casual": 2,
    "smart": 3,
}
SCENARIO_FORMALITY = {
    "casual_daily": "casual",
    "street": "casual",
    "office": "smart_casual",
    "date": "smart_casual",
    "gym": "sport",
    "running": "sport",
    "outdoor_light": "sport",
}
OFFICE_BOTTOM_CATEGORIES = {"trousers", "skirt"}
OFFICE_SHOE_CATEGORIES = {"loafers", "heels", "flats", "boots"}
DATE_BOTTOM_BLOCKLIST = {"sports_shorts", "leggings"}


@dataclass(frozen=True)
class NormalizedCompletionRequest:
    user_id: int
    anchor_item_ids: list[int]
    scenario_key: str
    season_key: str | None
    season_tags: list[str]
    weather_tags: list[str]
    budget_ceiling: float | None
    budget_tiers: list[str] | None
    gender_target: str | None
    limit_per_role: int
    include_optional_fills: bool
    excluded_product_ids: list[int]


def normalize_user_request(
    *,
    user_id: int,
    anchor_item_ids: Sequence[int],
    scenario: str,
    season: str | None = None,
    budget: float | None = None,
    gender_target: str | None = None,
    limit_per_role: int = 8,
    include_optional_fills: bool = True,
    excluded_product_ids: Sequence[int] | None = None,
) -> NormalizedCompletionRequest:
    if not user_id:
        raise InvalidRequestError(
            "user_id is required",
            details={"field": "user_id"},
        )
    anchor_ids = [int(item_id) for item_id in anchor_item_ids if item_id]
    if not anchor_ids:
        raise NoAnchorsSelectedError(
            details={"field": "anchor_item_ids"},
        )

    scenario_key = SCENARIO_ALIASES.get((scenario or "").strip().lower())
    if not scenario_key:
        raise InvalidScenarioError(
            f"Unsupported scenario: {scenario}",
            details={"scenario": scenario},
        )

    season_key, season_tags, weather_tags = _normalize_season(season)
    budget_ceiling = float(budget) if budget is not None else None

    return NormalizedCompletionRequest(
        user_id=int(user_id),
        anchor_item_ids=anchor_ids,
        scenario_key=scenario_key,
        season_key=season_key,
        season_tags=season_tags,
        weather_tags=weather_tags,
        budget_ceiling=budget_ceiling,
        budget_tiers=derive_budget_tiers(budget_ceiling),
        gender_target=(gender_target or "").strip().lower() or None,
        limit_per_role=max(1, int(limit_per_role)),
        include_optional_fills=bool(include_optional_fills),
        excluded_product_ids=[int(product_id) for product_id in (excluded_product_ids or [])],
    )


def infer_request_gender(anchor_items: Sequence[Mapping[str, Any]], explicit_gender_target: str | None) -> str:
    if explicit_gender_target:
        return explicit_gender_target

    gender_counter = Counter(
        (item.get("gender_target") or "").strip().lower()
        for item in anchor_items
        if (item.get("gender_target") or "").strip()
    )
    for gender in ("women", "broad", "unisex", "men"):
        if gender_counter.get(gender):
            return gender
    return "women"


def detect_covered_roles(anchor_items: Sequence[Mapping[str, Any]]) -> list[str]:
    covered: set[str] = set()
    for item in anchor_items:
        covered.update(expand_covered_roles(item.get("role")))
    return sorted(covered)


def expand_covered_roles(role: str | None) -> set[str]:
    if not role:
        return set()
    return set(ROLE_COVERAGE.get(role, {role}))


def derive_missing_roles(
    *,
    required_roles: Sequence[str],
    optional_roles: Sequence[str],
    covered_roles: Sequence[str],
) -> tuple[list[str], list[str]]:
    covered = set(covered_roles)
    missing_required = [role for role in required_roles if role not in covered]
    missing_optional = [role for role in optional_roles if role not in covered]
    return missing_required, missing_optional


def build_anchor_profile(anchor_items: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    style_counter = Counter()
    formality_counter = Counter()
    colors: list[str] = []
    warmth_values: list[int] = []
    roles: set[str] = set()
    categories: set[str] = set()

    for item in anchor_items:
        if item.get("style_primary"):
            style_counter[str(item["style_primary"])] += 3
        for tag in item.get("style_secondary") or []:
            style_counter[str(tag)] += 1
        if item.get("formality"):
            formality_counter[str(item["formality"])] += 1
        if item.get("role"):
            roles.add(str(item["role"]))
        if item.get("category"):
            categories.add(str(item["category"]))
        color_family = normalize_color_family(item.get("color_raw"), title=item.get("title") or "")
        if color_family:
            colors.append(color_family)
        warmth_values.append(int(item.get("warmth_level") or 0))

    return {
        "styles": [style for style, _count in style_counter.most_common(4)],
        "dominant_formality": formality_counter.most_common(1)[0][0] if formality_counter else None,
        "colors": sorted(set(colors)),
        "warmth_level": round(sum(warmth_values) / len(warmth_values), 2) if warmth_values else 0,
        "roles": sorted(roles),
        "categories": sorted(categories),
    }


def is_allowed_candidate_role(candidate_role: str | None, *, missing_role: str, covered_roles: Sequence[str]) -> bool:
    if not candidate_role:
        return False
    if candidate_role in set(covered_roles):
        return False
    return candidate_role == missing_role


def is_allowed_candidate_formality(candidate_formality: str | None, *, scenario_key: str) -> bool:
    if not candidate_formality:
        return True

    expected = SCENARIO_FORMALITY.get(scenario_key)
    if not expected:
        return True
    if scenario_key in SPORT_SCENARIOS:
        return candidate_formality == "sport"

    expected_rank = FORMALITY_SCALE.get(expected)
    candidate_rank = FORMALITY_SCALE.get(candidate_formality)
    if expected_rank is None or candidate_rank is None:
        return True
    return abs(expected_rank - candidate_rank) <= 1


def is_allowed_candidate_category(
    candidate: Mapping[str, Any],
    *,
    scenario_key: str,
    missing_role: str,
) -> bool:
    category = str(candidate.get("category") or "").strip().lower()

    if scenario_key == "office":
        if missing_role == "bottom" and category not in OFFICE_BOTTOM_CATEGORIES:
            return False
        if missing_role == "shoes" and category not in OFFICE_SHOE_CATEGORIES:
            return False
    if scenario_key == "date":
        if missing_role == "bottom" and category in DATE_BOTTOM_BLOCKLIST:
            return False
        if missing_role == "shoes" and category == "running_shoes":
            return False
    if scenario_key in SPORT_SCENARIOS and missing_role == "running_shoes" and category != "running_shoes":
        return False

    return True


def item_base_score(
    candidate: Mapping[str, Any],
    *,
    request: NormalizedCompletionRequest,
    anchor_profile: Mapping[str, Any],
    missing_role: str,
    scenario_preferences: Sequence[str] | None = None,
) -> tuple[float, dict[str, float], list[dict[str, Any]]]:
    breakdown: dict[str, float] = {}
    score = 0.0
    scenario_preferences = list(dict.fromkeys(scenario_preferences or [request.scenario_key]))

    exact_scenario_overlap = _overlap(candidate.get("scenario_tags"), [request.scenario_key])
    preferred_scenario_overlap = _overlap(candidate.get("scenario_tags"), scenario_preferences)
    breakdown["scenario_fit"] = 2.5 if exact_scenario_overlap else 1.3 if preferred_scenario_overlap else 0.0
    score += breakdown["scenario_fit"]

    season_overlap = _overlap(candidate.get("season_tags"), request.season_tags)
    breakdown["season_fit"] = 1.2 if request.season_tags and season_overlap else 0.6 if not request.season_tags else 0.0
    score += breakdown["season_fit"]

    weather_overlap = _overlap(candidate.get("weather_tags"), request.weather_tags)
    breakdown["weather_fit"] = 1.2 if request.weather_tags and weather_overlap else 0.4 if not request.weather_tags else 0.0
    score += breakdown["weather_fit"]

    candidate_styles = {candidate.get("style_primary"), *(candidate.get("style_secondary") or [])}
    anchor_styles = set(anchor_profile.get("styles") or [])
    style_match = len(candidate_styles & anchor_styles)
    if request.scenario_key in SPORT_SCENARIOS and candidate.get("style_primary") == "activewear":
        style_match += 2
    breakdown["style_coherence"] = min(1.5, style_match * 0.5)
    score += breakdown["style_coherence"]

    dominant_formality = anchor_profile.get("dominant_formality")
    candidate_formality = candidate.get("formality")
    formality_fit = 0.0
    if dominant_formality and candidate_formality:
        if dominant_formality == candidate_formality:
            formality_fit = 1.0
        elif is_allowed_candidate_formality(candidate_formality, scenario_key=request.scenario_key):
            formality_fit = 0.5
    elif is_allowed_candidate_formality(candidate_formality, scenario_key=request.scenario_key):
        formality_fit = 0.5
    breakdown["formality_fit"] = formality_fit
    score += formality_fit

    candidate_color = candidate.get("color_family")
    anchor_colors = set(anchor_profile.get("colors") or [])
    if candidate_color and (candidate_color in anchor_colors or candidate_color in NEUTRAL_COLORS):
        breakdown["color_coherence"] = 0.8
    else:
        breakdown["color_coherence"] = 0.2 if not candidate_color else 0.0
    score += breakdown["color_coherence"]

    anchor_warmth = float(anchor_profile.get("warmth_level") or 0)
    candidate_warmth = float(candidate.get("warmth_level") or 0)
    warmth_delta = abs(anchor_warmth - candidate_warmth)
    breakdown["warmth_fit"] = max(0.0, 1.0 - (warmth_delta * 0.25))
    score += breakdown["warmth_fit"]

    breakdown["role_match"] = 1.0 if candidate.get("role") == missing_role else 0.0
    score += breakdown["role_match"]

    anchor_roles = set(anchor_profile.get("roles") or [])
    pairing_overlap = len(set(candidate.get("pairing_tags") or []) & anchor_roles)
    breakdown["pairing_fit"] = min(0.8, pairing_overlap * 0.4)
    score += breakdown["pairing_fit"]

    avoid_overlap = len(set(candidate.get("avoid_pairing_tags") or []) & anchor_roles)
    breakdown["avoidance_penalty"] = -min(0.8, avoid_overlap * 0.4)
    score += breakdown["avoidance_penalty"]

    source_preference = float(candidate.get("source_preference_score") or 0)
    image_quality = float(candidate.get("image_quality_score") or 0)
    metadata_quality = float(candidate.get("metadata_completeness_score") or 0)
    breakdown["catalog_quality"] = round(source_preference * 0.8 + image_quality * 0.5 + metadata_quality * 0.7, 3)
    score += breakdown["catalog_quality"]

    match_reasons = build_match_reasons(
        candidate,
        request=request,
        missing_role=missing_role,
        scenario_preferences=scenario_preferences,
        breakdown=breakdown,
        anchor_profile=anchor_profile,
    )

    return round(score, 3), breakdown, match_reasons


def build_match_reasons(
    candidate: Mapping[str, Any],
    *,
    request: NormalizedCompletionRequest,
    missing_role: str,
    scenario_preferences: Sequence[str],
    breakdown: Mapping[str, float],
    anchor_profile: Mapping[str, Any],
) -> list[dict[str, Any]]:
    reasons: list[dict[str, Any]] = [
        {
            "code": "missing_role_match",
            "value": missing_role,
            "weight": round(float(breakdown.get("role_match") or 0), 3),
        }
    ]

    scenario_tags = set(candidate.get("scenario_tags") or [])
    if request.scenario_key in scenario_tags:
        reasons.append(
            {
                "code": "scenario_match",
                "value": request.scenario_key,
                "weight": round(float(breakdown.get("scenario_fit") or 0), 3),
            }
        )
    elif scenario_tags & set(scenario_preferences):
        reasons.append(
            {
                "code": "scenario_alias_match",
                "value": sorted(scenario_tags & set(scenario_preferences)),
                "weight": round(float(breakdown.get("scenario_fit") or 0), 3),
            }
        )

    if request.season_tags and _overlap(candidate.get("season_tags"), request.season_tags):
        reasons.append(
            {
                "code": "season_match",
                "value": sorted(set(candidate.get("season_tags") or []) & set(request.season_tags)),
                "weight": round(float(breakdown.get("season_fit") or 0), 3),
            }
        )

    if request.weather_tags and _overlap(candidate.get("weather_tags"), request.weather_tags):
        reasons.append(
            {
                "code": "weather_match",
                "value": sorted(set(candidate.get("weather_tags") or []) & set(request.weather_tags)),
                "weight": round(float(breakdown.get("weather_fit") or 0), 3),
            }
        )

    if request.budget_ceiling is not None:
        reasons.append(
            {
                "code": "within_budget",
                "value": request.budget_ceiling,
                "weight": 0.4,
            }
        )

    anchor_styles = set(anchor_profile.get("styles") or [])
    candidate_styles = {candidate.get("style_primary"), *(candidate.get("style_secondary") or [])}
    style_overlap = sorted((candidate_styles & anchor_styles) - {None})
    if style_overlap:
        reasons.append(
            {
                "code": "style_match",
                "value": style_overlap,
                "weight": round(float(breakdown.get("style_coherence") or 0), 3),
            }
        )
    elif candidate.get("style_primary") == "activewear" and request.scenario_key in SPORT_SCENARIOS:
        reasons.append(
            {
                "code": "sport_style_match",
                "value": "activewear",
                "weight": round(float(breakdown.get("style_coherence") or 0), 3),
            }
        )

    if float(breakdown.get("formality_fit") or 0) > 0:
        reasons.append(
            {
                "code": "formality_match",
                "value": candidate.get("formality"),
                "weight": round(float(breakdown.get("formality_fit") or 0), 3),
            }
        )

    if float(breakdown.get("color_coherence") or 0) > 0:
        reasons.append(
            {
                "code": "color_coherence",
                "value": candidate.get("color_family"),
                "weight": round(float(breakdown.get("color_coherence") or 0), 3),
            }
        )

    pairing_overlap = sorted(set(candidate.get("pairing_tags") or []) & set(anchor_profile.get("roles") or []))
    if pairing_overlap:
        reasons.append(
            {
                "code": "pairing_match",
                "value": pairing_overlap,
                "weight": round(float(breakdown.get("pairing_fit") or 0), 3),
            }
        )

    avoid_overlap = sorted(set(candidate.get("avoid_pairing_tags") or []) & set(anchor_profile.get("roles") or []))
    if avoid_overlap:
        reasons.append(
            {
                "code": "avoid_pairing_penalty",
                "value": avoid_overlap,
                "weight": round(float(breakdown.get("avoidance_penalty") or 0), 3),
            }
        )

    if float(candidate.get("metadata_completeness_score") or 0) >= 0.8:
        reasons.append(
            {
                "code": "metadata_quality_boost",
                "value": round(float(candidate.get("metadata_completeness_score") or 0), 3),
                "weight": 0.7,
            }
        )

    if float(candidate.get("source_preference_score") or 0) >= 0.85:
        reasons.append(
            {
                "code": "trusted_source_boost",
                "value": candidate.get("store_key"),
                "weight": 0.5,
            }
        )

    return reasons


def _normalize_season(season: str | None) -> tuple[str | None, list[str], list[str]]:
    if not season:
        return None, [], []
    key = (season or "").strip().lower()
    if key not in SEASON_PRESETS:
        raise InvalidSeasonError(
            f"Unsupported season: {season}",
            details={"season": season},
        )
    preset = SEASON_PRESETS[key]
    return key, list(preset["season_tags"]), list(preset["weather_tags"])


def derive_budget_tiers(budget_ceiling: float | None) -> list[str] | None:
    if budget_ceiling is None:
        return None
    if budget_ceiling < 3000:
        return ["low"]
    if budget_ceiling < 7000:
        return ["low", "lower_mid"]
    if budget_ceiling < 15000:
        return ["low", "lower_mid", "mid"]
    return ["low", "lower_mid", "mid", "upper_mid"]


def _overlap(left: Iterable[str] | None, right: Iterable[str] | None) -> int:
    left_values = set(left or [])
    right_values = set(right or [])
    if not left_values or not right_values:
        return 0
    return len(left_values & right_values)
