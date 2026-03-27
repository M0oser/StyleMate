from __future__ import annotations

from typing import Any, Literal, Mapping, Sequence

from pydantic import BaseModel, Field

from services.scenario_rules import SEASON_PRESETS
from vocab.fashion import (
    COMPLETION_SCENARIOS,
    CONTROLLED_FORMALITY,
    CONTROLLED_WEATHER_TAGS,
    STORE_DEFINITIONS,
    SUPPORTED_COMPLETION_ROLES,
)


API_VERSION = "v1"


class CompletionRequestDTO(BaseModel):
    user_id: int | None = None
    anchor_item_ids: list[int]
    scenario: str
    season: str | None = None
    budget: float | None = Field(default=None, ge=0)
    gender_target: str | None = None
    limit_per_role: int = Field(default=8, ge=1, le=50)
    include_optional_fills: bool = True
    excluded_product_ids: list[int] = Field(default_factory=list)


class MatchReasonDTO(BaseModel):
    code: str
    value: Any | None = None
    weight: float | None = None


class FillDebugDTO(BaseModel):
    score_breakdown: dict[str, float]
    selection_trace: dict[str, Any]
    source_preference_score: float
    image_quality_score: float
    metadata_completeness_score: float


class AnchorDTO(BaseModel):
    id: int
    title: str
    category: str
    subcategory: str | None = None
    role: str | None = None
    gender_target: str | None = None
    primary_image_url: str | None = None
    color_raw: str | None = None
    color_family: str | None = None
    fit_raw: str | None = None
    material_raw: str | None = None
    style_primary: str | None = None
    style_secondary: list[str] = Field(default_factory=list)
    formality: str | None = None
    season_tags: list[str] = Field(default_factory=list)
    weather_tags: list[str] = Field(default_factory=list)
    occasion_tags: list[str] = Field(default_factory=list)
    warmth_level: int = 0


class FillDTO(BaseModel):
    product_id: int
    source_product_id: str | None = None
    store_key: str | None = None
    store_name: str | None = None
    title: str | None = None
    brand: str | None = None
    category: str | None = None
    subcategory: str | None = None
    role: str | None = None
    matched_missing_role: str | None = None
    gender_target: str | None = None
    current_price: float | None = None
    old_price: float | None = None
    currency: str | None = None
    product_url: str | None = None
    primary_image_url: str | None = None
    color_raw: str | None = None
    color_family: str | None = None
    style_primary: str | None = None
    style_secondary: list[str] = Field(default_factory=list)
    formality: str | None = None
    budget_tier: str | None = None
    season_tags: list[str] = Field(default_factory=list)
    weather_tags: list[str] = Field(default_factory=list)
    occasion_tags: list[str] = Field(default_factory=list)
    scenario_tags: list[str] = Field(default_factory=list)
    warmth_level: int = 0
    body_size_relevance: list[str] = Field(default_factory=list)
    pairing_tags: list[str] = Field(default_factory=list)
    avoid_pairing_tags: list[str] = Field(default_factory=list)
    score: float
    match_reasons: list[MatchReasonDTO] = Field(default_factory=list)
    debug: FillDebugDTO | None = None


class CompletionStateDTO(BaseModel):
    code: Literal["ALREADY_COMPLETE", "FILLS_FOUND", "OPTIONAL_ONLY", "NO_REQUIRED_FILLS_FOUND"]
    message: str
    is_complete: bool
    required_fills_found: bool
    optional_fills_found: bool
    missing_required_roles_without_results: list[str] = Field(default_factory=list)


class CompletionResponseDTO(BaseModel):
    api_version: str = API_VERSION
    anchors: list[AnchorDTO]
    covered_roles: list[str]
    required_roles: list[str]
    optional_roles: list[str]
    missing_roles: list[str]
    optional_missing_roles: list[str]
    fill_role_order: list[str]
    optional_fill_role_order: list[str]
    fills: dict[str, list[FillDTO]]
    optional_fills: dict[str, list[FillDTO]]
    completion_state: CompletionStateDTO
    scenario: str
    season: str | None = None
    season_tags: list[str] = Field(default_factory=list)
    weather_tags: list[str] = Field(default_factory=list)
    budget: float | None = None
    budget_tiers: list[str] = Field(default_factory=list)
    gender_target: str


class ErrorBodyDTO(BaseModel):
    code: str
    message: str
    details: dict[str, Any] = Field(default_factory=dict)


class ErrorResponseDTO(BaseModel):
    api_version: str = API_VERSION
    error: ErrorBodyDTO


class MetaRoleDTO(BaseModel):
    key: str
    label: str


class MetaSeasonDTO(BaseModel):
    key: str
    label: str
    season_tags: list[str]
    weather_tags: list[str]


class MetaBudgetTierDTO(BaseModel):
    key: str
    label: str
    min_price: float | None = None
    max_price: float | None = None


class MetaScenarioDTO(BaseModel):
    key: str
    label: str
    required_roles: list[str]
    optional_roles: list[str]
    season_tags: list[str]
    occasion_tags: list[str]
    weather_tags: list[str]


class MetaStoreDTO(BaseModel):
    key: str
    label: str
    active: bool


class MetaResponseDTO(BaseModel):
    api_version: str = API_VERSION
    roles: list[MetaRoleDTO]
    scenarios: list[MetaScenarioDTO]
    seasons: list[MetaSeasonDTO]
    budget_tiers: list[MetaBudgetTierDTO]
    weather_tags: list[str]
    formality_levels: list[str]
    stores: list[MetaStoreDTO]


def serialize_completion_response(
    payload: Mapping[str, Any],
    *,
    include_debug: bool = False,
) -> dict[str, Any]:
    missing_roles = list(payload.get("missing_roles") or [])
    optional_missing_roles = list(payload.get("optional_missing_roles") or [])
    fills = {
        role: [
            _serialize_fill(item, include_debug=include_debug)
            for item in _stable_fill_order(payload.get("fills", {}).get(role, []))
        ]
        for role in missing_roles
    }
    optional_fills = {
        role: [
            _serialize_fill(item, include_debug=include_debug)
            for item in _stable_fill_order(payload.get("optional_fills", {}).get(role, []))
        ]
        for role in optional_missing_roles
    }
    response = CompletionResponseDTO(
        anchors=[AnchorDTO.model_validate(anchor) for anchor in payload.get("anchors") or []],
        covered_roles=list(payload.get("covered_roles") or []),
        required_roles=list(payload.get("required_roles") or []),
        optional_roles=list(payload.get("optional_roles") or []),
        missing_roles=missing_roles,
        optional_missing_roles=optional_missing_roles,
        fill_role_order=missing_roles,
        optional_fill_role_order=optional_missing_roles,
        fills=fills,
        optional_fills=optional_fills,
        completion_state=_derive_completion_state(
            missing_roles=missing_roles,
            fills=fills,
            optional_fills=optional_fills,
        ),
        scenario=str(payload.get("scenario") or ""),
        season=payload.get("season"),
        season_tags=list(payload.get("season_tags") or []),
        weather_tags=list(payload.get("weather_tags") or []),
        budget=payload.get("budget"),
        budget_tiers=list(payload.get("budget_tiers") or []),
        gender_target=str(payload.get("gender_target") or "women"),
    )
    return response.model_dump(mode="json", exclude_none=True)


def build_meta_response() -> dict[str, Any]:
    response = MetaResponseDTO(
        roles=[
            MetaRoleDTO(key=role, label=_humanize_key(role))
            for role in sorted(SUPPORTED_COMPLETION_ROLES)
        ],
        scenarios=[
            MetaScenarioDTO(
                key=key,
                label=str(config["label"]),
                required_roles=list(config["required_roles"]),
                optional_roles=list(config["optional_roles"]),
                season_tags=list(config["season_tags"]),
                occasion_tags=list(config["occasion_tags"]),
                weather_tags=list(config.get("weather_tags") or []),
            )
            for key, config in COMPLETION_SCENARIOS.items()
        ],
        seasons=[
            MetaSeasonDTO(
                key=key,
                label=_humanize_key(key),
                season_tags=list(values["season_tags"]),
                weather_tags=list(values["weather_tags"]),
            )
            for key, values in SEASON_PRESETS.items()
        ],
        budget_tiers=[
            MetaBudgetTierDTO(key="low", label="Low", min_price=None, max_price=2999),
            MetaBudgetTierDTO(key="lower_mid", label="Lower Mid", min_price=3000, max_price=6999),
            MetaBudgetTierDTO(key="mid", label="Mid", min_price=7000, max_price=14999),
            MetaBudgetTierDTO(key="upper_mid", label="Upper Mid", min_price=15000, max_price=None),
        ],
        weather_tags=sorted(CONTROLLED_WEATHER_TAGS),
        formality_levels=sorted(CONTROLLED_FORMALITY),
        stores=[
            MetaStoreDTO(key=store.parser_key, label=store.name, active=store.is_active)
            for store in STORE_DEFINITIONS
        ],
    )
    return response.model_dump(mode="json")


def build_error_response(
    *,
    code: str,
    message: str,
    details: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return ErrorResponseDTO(
        error=ErrorBodyDTO(
            code=code,
            message=message,
            details=details or {},
        )
    ).model_dump(mode="json")


def _serialize_fill(item: Mapping[str, Any], *, include_debug: bool) -> FillDTO:
    debug = None
    if include_debug:
        debug = FillDebugDTO(
            score_breakdown=dict(item.get("score_breakdown") or {}),
            selection_trace=dict(item.get("selection_trace") or {}),
            source_preference_score=float(item.get("source_preference_score") or 0),
            image_quality_score=float(item.get("image_quality_score") or 0),
            metadata_completeness_score=float(item.get("metadata_completeness_score") or 0),
        )

    return FillDTO(
        product_id=int(item["product_id"]),
        source_product_id=item.get("source_product_id"),
        store_key=item.get("store_key"),
        store_name=item.get("store_name"),
        title=item.get("title"),
        brand=item.get("brand"),
        category=item.get("category"),
        subcategory=item.get("subcategory"),
        role=item.get("role"),
        matched_missing_role=item.get("matched_missing_role"),
        gender_target=item.get("gender_target"),
        current_price=item.get("current_price"),
        old_price=item.get("old_price"),
        currency=item.get("currency"),
        product_url=item.get("product_url"),
        primary_image_url=item.get("primary_image_url"),
        color_raw=item.get("color_raw"),
        color_family=item.get("color_family"),
        style_primary=item.get("style_primary"),
        style_secondary=list(item.get("style_secondary") or []),
        formality=item.get("formality"),
        budget_tier=item.get("budget_tier"),
        season_tags=list(item.get("season_tags") or []),
        weather_tags=list(item.get("weather_tags") or []),
        occasion_tags=list(item.get("occasion_tags") or []),
        scenario_tags=list(item.get("scenario_tags") or []),
        warmth_level=int(item.get("warmth_level") or 0),
        body_size_relevance=list(item.get("body_size_relevance") or []),
        pairing_tags=list(item.get("pairing_tags") or []),
        avoid_pairing_tags=list(item.get("avoid_pairing_tags") or []),
        score=float(item.get("completion_score") or 0),
        match_reasons=[MatchReasonDTO.model_validate(reason) for reason in item.get("match_reasons") or []],
        debug=debug,
    )


def _stable_fill_order(items: Sequence[Mapping[str, Any]]) -> list[Mapping[str, Any]]:
    return sorted(
        items,
        key=lambda row: (
            -float(row.get("completion_score") or 0),
            -float(row.get("source_preference_score") or 0),
            -float(row.get("metadata_completeness_score") or 0),
            -float(row.get("image_quality_score") or 0),
            int(row.get("product_id") or 0),
        ),
    )


def _derive_completion_state(
    *,
    missing_roles: Sequence[str],
    fills: Mapping[str, Sequence[FillDTO]],
    optional_fills: Mapping[str, Sequence[FillDTO]],
) -> CompletionStateDTO:
    missing_without_results = [role for role in missing_roles if not fills.get(role)]
    required_fills_found = any(bool(fills.get(role)) for role in missing_roles)
    optional_fills_found = any(bool(items) for items in optional_fills.values())

    if not missing_roles:
        return CompletionStateDTO(
            code="ALREADY_COMPLETE",
            message="Selected anchors already cover the required outfit roles.",
            is_complete=True,
            required_fills_found=False,
            optional_fills_found=optional_fills_found,
            missing_required_roles_without_results=[],
        )
    if required_fills_found:
        return CompletionStateDTO(
            code="FILLS_FOUND",
            message="Completion fills were found for at least one missing required role.",
            is_complete=False,
            required_fills_found=True,
            optional_fills_found=optional_fills_found,
            missing_required_roles_without_results=missing_without_results,
        )
    if optional_fills_found:
        return CompletionStateDTO(
            code="OPTIONAL_ONLY",
            message="No required fills were found, but optional fill suggestions are available.",
            is_complete=False,
            required_fills_found=False,
            optional_fills_found=True,
            missing_required_roles_without_results=missing_without_results,
        )
    return CompletionStateDTO(
        code="NO_REQUIRED_FILLS_FOUND",
        message="No fill candidates were found for the missing required roles.",
        is_complete=False,
        required_fills_found=False,
        optional_fills_found=False,
        missing_required_roles_without_results=missing_without_results,
    )


def _humanize_key(value: str) -> str:
    return value.replace("_", " ").title()
