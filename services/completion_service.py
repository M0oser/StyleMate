from __future__ import annotations

from typing import Any, Mapping, Sequence

from database.db import get_repository
from database.repositories import CompletionDataRepository
from normalizers.colors import normalize_color_family
from services.completion_errors import AnchorsNotFoundError
from services.scenario_rules import (
    NormalizedCompletionRequest,
    SPORT_SCENARIOS,
    build_anchor_profile,
    derive_missing_roles,
    detect_covered_roles,
    infer_request_gender,
    is_allowed_candidate_category,
    is_allowed_candidate_formality,
    is_allowed_candidate_role,
    item_base_score,
    normalize_user_request,
)


class CompletionService:
    """Backend completion flow: anchors first, shop fills only for uncovered roles."""

    def __init__(self, repository: CompletionDataRepository | None = None) -> None:
        self.repository = repository or get_repository()

    def generate_completion(
        self,
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
    ) -> dict[str, Any]:
        request = normalize_user_request(
            user_id=user_id,
            anchor_item_ids=anchor_item_ids,
            scenario=scenario,
            season=season,
            budget=budget,
            gender_target=gender_target,
            limit_per_role=limit_per_role,
            include_optional_fills=include_optional_fills,
            excluded_product_ids=excluded_product_ids,
        )
        anchors = self._load_anchor_items(request)
        scenario_profile = self.repository.get_scenario_profile(request.scenario_key)
        covered_roles = detect_covered_roles(anchors)
        missing_roles, optional_missing_roles = derive_missing_roles(
            required_roles=scenario_profile["required_roles"],
            optional_roles=scenario_profile["optional_roles"],
            covered_roles=covered_roles,
        )
        effective_gender = infer_request_gender(anchors, request.gender_target)
        anchor_profile = build_anchor_profile(anchors)

        used_shop_product_ids = set(request.excluded_product_ids)
        fills = self._retrieve_fills_for_roles(
            request=request,
            roles=missing_roles,
            covered_roles=covered_roles,
            anchor_profile=anchor_profile,
            gender_target=effective_gender,
            used_shop_product_ids=used_shop_product_ids,
        )

        optional_fills: dict[str, list[dict[str, Any]]] = {}
        if request.include_optional_fills:
            optional_fills = self._retrieve_fills_for_roles(
                request=request,
                roles=optional_missing_roles,
                covered_roles=covered_roles,
                anchor_profile=anchor_profile,
                gender_target=effective_gender,
                used_shop_product_ids=used_shop_product_ids,
            )

        return {
            "anchors": [self._serialize_anchor(anchor) for anchor in anchors],
            "covered_roles": covered_roles,
            "required_roles": list(scenario_profile["required_roles"]),
            "optional_roles": list(scenario_profile["optional_roles"]),
            "missing_roles": missing_roles,
            "optional_missing_roles": optional_missing_roles,
            "fills": fills,
            "optional_fills": optional_fills,
            "scenario": request.scenario_key,
            "season": request.season_key,
            "season_tags": request.season_tags,
            "weather_tags": request.weather_tags,
            "budget": request.budget_ceiling,
            "budget_tiers": request.budget_tiers,
            "gender_target": effective_gender,
        }

    def _load_anchor_items(self, request: NormalizedCompletionRequest) -> list[dict[str, Any]]:
        anchors = self.repository.list_user_wardrobe_items(
            user_id=request.user_id,
            item_ids=request.anchor_item_ids,
        )
        loaded_ids = {int(anchor["id"]) for anchor in anchors}
        missing_ids = [item_id for item_id in request.anchor_item_ids if item_id not in loaded_ids]
        if missing_ids:
            raise AnchorsNotFoundError(
                details={
                    "user_id": request.user_id,
                    "anchor_item_ids": list(request.anchor_item_ids),
                    "missing_anchor_item_ids": missing_ids,
                }
            )
        return anchors

    def _retrieve_fills_for_roles(
        self,
        *,
        request: NormalizedCompletionRequest,
        roles: Sequence[str],
        covered_roles: Sequence[str],
        anchor_profile: Mapping[str, Any],
        gender_target: str,
        used_shop_product_ids: set[int],
    ) -> dict[str, list[dict[str, Any]]]:
        fills: dict[str, list[dict[str, Any]]] = {}
        scenario_profile = self.repository.get_scenario_profile(request.scenario_key)
        profile_metadata = scenario_profile.get("metadata") or {}

        for missing_role in roles:
            raw_candidates = self.repository.find_completion_candidates(
                missing_roles=[missing_role],
                gender_target=gender_target,
                season_tags=request.season_tags or _profile_season_tags(scenario_profile),
                weather_tags=request.weather_tags or list(profile_metadata.get("weather_tags") or []),
                scenario_tags=self._scenario_filters(request.scenario_key, missing_role),
                budget_tiers=request.budget_tiers,
                max_price=request.budget_ceiling,
                excluded_product_ids=list(used_shop_product_ids),
                limit=request.limit_per_role * 4,
            )
            ranked_candidates = self._rank_role_candidates(
                raw_candidates,
                request=request,
                missing_role=missing_role,
                covered_roles=covered_roles,
                anchor_profile=anchor_profile,
            )
            selected_candidates = ranked_candidates[: request.limit_per_role]
            used_shop_product_ids.update(candidate["product_id"] for candidate in selected_candidates)
            fills[missing_role] = selected_candidates
        return fills

    def _rank_role_candidates(
        self,
        candidates: Sequence[Mapping[str, Any]],
        *,
        request: NormalizedCompletionRequest,
        missing_role: str,
        covered_roles: Sequence[str],
        anchor_profile: Mapping[str, Any],
    ) -> list[dict[str, Any]]:
        ranked: list[dict[str, Any]] = []
        for candidate in candidates:
            if not is_allowed_candidate_role(candidate.get("role"), missing_role=missing_role, covered_roles=covered_roles):
                continue
            if not is_allowed_candidate_category(candidate, scenario_key=request.scenario_key, missing_role=missing_role):
                continue
            if not is_allowed_candidate_formality(candidate.get("formality"), scenario_key=request.scenario_key):
                continue

            scenario_preferences = self._scenario_filters(request.scenario_key, missing_role)
            base_score, breakdown, match_reasons = item_base_score(
                candidate,
                request=request,
                anchor_profile=anchor_profile,
                missing_role=missing_role,
                scenario_preferences=scenario_preferences,
            )
            ranked.append(
                {
                    **self._serialize_fill(candidate),
                    "completion_score": base_score,
                    "score_breakdown": breakdown,
                    "match_reasons": match_reasons,
                    "matched_missing_role": missing_role,
                    "requested_scenario": request.scenario_key,
                    "selection_trace": {
                        "matched_missing_role": missing_role,
                        "requested_scenario": request.scenario_key,
                        "scenario_preferences": list(scenario_preferences),
                        "applied_season_tags": list(request.season_tags),
                        "applied_weather_tags": list(request.weather_tags),
                        "applied_budget_ceiling": request.budget_ceiling,
                        "reason_codes": [reason["code"] for reason in match_reasons],
                    },
                }
            )

        ranked.sort(
            key=lambda row: (
                row["completion_score"],
                float(row.get("source_preference_score") or 0),
                float(row.get("metadata_completeness_score") or 0),
                float(row.get("image_quality_score") or 0),
            ),
            reverse=True,
        )
        return self._diversify_ranked_candidates(ranked)

    @staticmethod
    def _serialize_anchor(anchor: Mapping[str, Any]) -> dict[str, Any]:
        return {
            "id": int(anchor["id"]),
            "title": anchor["title"],
            "category": anchor["category"],
            "subcategory": anchor.get("subcategory"),
            "role": anchor.get("role"),
            "gender_target": anchor.get("gender_target"),
            "primary_image_url": anchor.get("primary_image_url"),
            "color_raw": anchor.get("color_raw"),
            "color_family": normalize_color_family(anchor.get("color_raw"), title=anchor.get("title") or ""),
            "fit_raw": anchor.get("fit_raw"),
            "material_raw": anchor.get("material_raw"),
            "style_primary": anchor.get("style_primary"),
            "style_secondary": list(anchor.get("style_secondary") or []),
            "formality": anchor.get("formality"),
            "season_tags": list(anchor.get("season_tags") or []),
            "weather_tags": list(anchor.get("weather_tags") or []),
            "occasion_tags": list(anchor.get("occasion_tags") or []),
            "warmth_level": int(anchor.get("warmth_level") or 0),
        }

    @staticmethod
    def _serialize_fill(candidate: Mapping[str, Any]) -> dict[str, Any]:
        return {
            "product_id": int(candidate["id"]),
            "source_product_id": candidate.get("source_product_id"),
            "store_key": candidate.get("store_key"),
            "store_name": candidate.get("store_name"),
            "title": candidate.get("title"),
            "brand": candidate.get("brand"),
            "category": candidate.get("category"),
            "subcategory": candidate.get("subcategory"),
            "role": candidate.get("role"),
            "gender_target": candidate.get("gender_target"),
            "current_price": float(candidate["current_price"]) if candidate.get("current_price") is not None else None,
            "old_price": float(candidate["old_price"]) if candidate.get("old_price") is not None else None,
            "currency": candidate.get("currency"),
            "product_url": candidate.get("product_url"),
            "primary_image_url": candidate.get("primary_image_url"),
            "color_raw": candidate.get("color_raw"),
            "color_family": candidate.get("color_family"),
            "style_primary": candidate.get("style_primary"),
            "style_secondary": list(candidate.get("style_secondary") or []),
            "formality": candidate.get("formality"),
            "budget_tier": candidate.get("budget_tier"),
            "season_tags": list(candidate.get("season_tags") or []),
            "weather_tags": list(candidate.get("weather_tags") or []),
            "occasion_tags": list(candidate.get("occasion_tags") or []),
            "scenario_tags": list(candidate.get("scenario_tags") or []),
            "warmth_level": int(candidate.get("warmth_level") or 0),
            "body_size_relevance": list(candidate.get("body_size_relevance") or []),
            "pairing_tags": list(candidate.get("pairing_tags") or []),
            "avoid_pairing_tags": list(candidate.get("avoid_pairing_tags") or []),
            "source_preference_score": float(candidate.get("source_preference_score") or 0),
            "image_quality_score": float(candidate.get("image_quality_score") or 0),
            "metadata_completeness_score": float(candidate.get("metadata_completeness_score") or 0),
        }

    @staticmethod
    def _scenario_filters(scenario_key: str, missing_role: str) -> list[str]:
        filters = [scenario_key]
        if scenario_key in SPORT_SCENARIOS:
            filters.append("outdoor_light")
            if missing_role in {"active_top", "active_bottom", "running_shoes"}:
                filters.append("gym")
            if scenario_key == "gym":
                filters.append("running")
        return list(dict.fromkeys(filters))

    @staticmethod
    def _diversify_ranked_candidates(ranked: Sequence[dict[str, Any]]) -> list[dict[str, Any]]:
        title_seen: dict[str, int] = {}
        diversified: list[dict[str, Any]] = []
        for row in ranked:
            title_key = " ".join(str(row.get("title") or "").lower().split())
            seen_count = title_seen.get(title_key, 0)
            if seen_count >= 2:
                continue
            title_seen[title_key] = seen_count + 1
            diversified.append(row)
        return diversified


def build_completion_response(**kwargs: Any) -> dict[str, Any]:
    return CompletionService().generate_completion(**kwargs)


def _profile_season_tags(profile: Mapping[str, Any]) -> list[str] | None:
    season_tags = list(profile.get("season_tags") or [])
    return [] if season_tags == ["all_season"] else season_tags
