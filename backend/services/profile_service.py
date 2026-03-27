from __future__ import annotations

from typing import Any, Dict, Optional

from database.db import get_repository, stable_user_id_from_owner_token


PROFILE_STYLE_OPTIONS = {
    "minimal",
    "casual",
    "sport",
    "classic",
    "formal",
    "streetwear",
    "romantic",
    "technical",
    "old_money",
}
PROFILE_GENDERS = {"male", "female", "unisex"}
FEEDBACK_SIGNALS = {"like", "dislike"}


def _normalize_profile_gender(gender: Optional[str]) -> str:
    value = str(gender or "").strip().lower()
    if value in PROFILE_GENDERS:
        return value
    return "male"


def _normalize_style_preferences(style_preferences: Optional[list[str]]) -> Optional[list[str]]:
    if style_preferences is None:
        return None

    if not isinstance(style_preferences, list):
        raise ValueError("style_preferences must be a list")

    normalized: list[str] = []
    seen: set[str] = set()
    for value in style_preferences:
        style = str(value or "").strip().lower()
        if style not in PROFILE_STYLE_OPTIONS or style in seen:
            continue
        normalized.append(style)
        seen.add(style)

    if len(normalized) > 3:
        raise ValueError("style_preferences must contain at most 3 styles")

    return normalized


def _normalize_feedback_signal(feedback: str) -> str:
    value = str(feedback or "").strip().lower()
    if value not in FEEDBACK_SIGNALS:
        raise ValueError("feedback must be 'like' or 'dislike'")
    return value


def _normalize_feedback_items(items: list[dict[str, Any]]) -> list[dict[str, str]]:
    if not isinstance(items, list) or not items:
        raise ValueError("items must be a non-empty list")

    normalized_items: list[dict[str, str]] = []
    for item in items:
        if not isinstance(item, dict):
            raise ValueError("items must contain objects")
        normalized_items.append(
            {
                "style": str(item.get("style") or "").strip().lower() or "unknown",
                "category": str(item.get("category") or "").strip().lower() or "unknown",
                "color": str(item.get("color") or "").strip().lower() or "unknown",
                "warmth": str(item.get("warmth") or "").strip().lower() or "unknown",
                "source": str(item.get("source") or "").strip().lower() or "unknown",
            }
        )
    return normalized_items


def _feedback_weight_from_counts(likes: int, dislikes: int) -> int:
    net = int(likes) - int(dislikes)
    if net > 0:
        return min(2, net)
    if net < 0:
        return max(-1, net)
    return 0


def _serialize_profile(row: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "display_name": row.get("display_name") or "",
        "gender": _normalize_profile_gender(row.get("gender")),
        "style_preferences": _normalize_style_preferences(list(row.get("style_preferences") or [])) or [],
        "onboarding_completed": bool(row.get("onboarding_completed")),
        "created_at": row.get("created_at"),
        "updated_at": row.get("updated_at"),
        "last_active_at": row.get("last_active_at"),
    }


def _ensure_profile(owner_token: str) -> Dict[str, Any]:
    repository = get_repository()
    user_id = stable_user_id_from_owner_token(owner_token)
    row = repository.get_or_create_user_profile(user_id=user_id, owner_token=owner_token)
    return _serialize_profile(row)


def _build_feedback_summary(rows: list[dict[str, Any]]) -> Dict[str, Any]:
    style_signals: dict[str, dict[str, int]] = {}
    category_signals: dict[str, dict[str, int]] = {}
    trait_totals: dict[str, dict[str, int]] = {
        "styles": {},
        "categories": {},
        "colors": {},
        "warmth": {},
        "sources": {},
    }

    def _bump_counter(bucket: dict[str, int], key: str) -> None:
        if not key or key == "unknown":
            return
        bucket[key] = bucket.get(key, 0) + 1

    for row in rows:
        signal = _normalize_feedback_signal(str(row.get("feedback") or ""))
        styles = [str(style or "").strip().lower() for style in row.get("item_styles") or []]
        categories = [str(category or "").strip().lower() for category in row.get("item_categories") or []]
        colors = [str(color or "").strip().lower() for color in row.get("item_colors") or []]
        warmth_values = [str(warmth or "").strip().lower() for warmth in row.get("item_warmth") or []]
        sources = [str(source or "").strip().lower() for source in row.get("item_sources") or []]

        normalized_styles = {style for style in styles if style and style != "unknown"}
        for style in normalized_styles:
            current = style_signals.setdefault(style, {"likes": 0, "dislikes": 0})
            current["likes" if signal == "like" else "dislikes"] += 1
        for style in styles:
            _bump_counter(trait_totals["styles"], style)

        normalized_categories = {category for category in categories if category and category != "unknown"}
        for category in normalized_categories:
            current = category_signals.setdefault(category, {"likes": 0, "dislikes": 0})
            current["likes" if signal == "like" else "dislikes"] += 1
        for category in categories:
            _bump_counter(trait_totals["categories"], category)

        for color in colors:
            _bump_counter(trait_totals["colors"], color)
        for warmth in warmth_values:
            _bump_counter(trait_totals["warmth"], warmth)
        for source in sources:
            _bump_counter(trait_totals["sources"], source)

    style_weights: dict[str, int] = {}
    detailed_style_signals: dict[str, dict[str, int]] = {}
    for style, counts in style_signals.items():
        weight = _feedback_weight_from_counts(counts["likes"], counts["dislikes"])
        style_weights[style] = weight
        detailed_style_signals[style] = {
            "likes": counts["likes"],
            "dislikes": counts["dislikes"],
            "net": counts["likes"] - counts["dislikes"],
            "weight": weight,
        }

    return {
        "feedback_count": len(rows),
        "style_weights": style_weights,
        "style_signals": detailed_style_signals,
        "category_signals": {
            category: {
                "likes": counts["likes"],
                "dislikes": counts["dislikes"],
                "net": counts["likes"] - counts["dislikes"],
            }
            for category, counts in category_signals.items()
        },
        "trait_totals": trait_totals,
    }


def bootstrap_session(owner_token: str) -> Dict[str, Any]:
    profile = _ensure_profile(owner_token)
    return {
        "session_token": owner_token,
        "user_id": stable_user_id_from_owner_token(owner_token),
        "profile": profile,
        "onboarding_required": not profile["onboarding_completed"],
    }


def get_profile(owner_token: str) -> Dict[str, Any]:
    return _ensure_profile(owner_token)


def get_style_preference_context(owner_token: str) -> Dict[str, Any]:
    repository = get_repository()
    user_id = stable_user_id_from_owner_token(owner_token)
    _ensure_profile(owner_token)
    feedback_summary = _build_feedback_summary(repository.list_user_feedback(user_id=user_id))
    return {
        "explicit": get_profile(owner_token).get("style_preferences", []),
        "learned_weights": feedback_summary.get("style_weights", {}),
    }


def save_profile(
    owner_token: str,
    *,
    display_name: Optional[str] = None,
    gender: Optional[str] = None,
    style_preferences: Optional[list[str]] = None,
    onboarding_completed: Optional[bool] = None,
) -> Dict[str, Any]:
    repository = get_repository()
    user_id = stable_user_id_from_owner_token(owner_token)
    current = _ensure_profile(owner_token)

    next_display_name = current["display_name"] if display_name is None else str(display_name).strip()[:80]
    next_gender = current["gender"] if gender is None else _normalize_profile_gender(gender)
    normalized_preferences = _normalize_style_preferences(style_preferences)
    next_preferences = current["style_preferences"] if normalized_preferences is None else normalized_preferences
    next_onboarding_completed = current["onboarding_completed"] if onboarding_completed is None else bool(onboarding_completed)

    row = repository.update_user_profile(
        user_id=user_id,
        owner_token=owner_token,
        display_name=next_display_name,
        gender=next_gender,
        style_preferences=next_preferences,
        onboarding_completed=next_onboarding_completed,
    )
    return _serialize_profile(row)


def record_feedback(
    owner_token: str,
    *,
    feedback: str,
    items: list[dict[str, Any]],
    scenario: Optional[str] = None,
    requested_style: Optional[str] = None,
) -> Dict[str, Any]:
    repository = get_repository()
    user_id = stable_user_id_from_owner_token(owner_token)
    profile = _ensure_profile(owner_token)

    normalized_feedback = _normalize_feedback_signal(feedback)
    normalized_items = _normalize_feedback_items(items)

    saved_feedback = repository.save_user_feedback(
        user_id=user_id,
        owner_token=owner_token,
        feedback=normalized_feedback,
        scenario=str(scenario or "").strip(),
        requested_style=str(requested_style or "").strip(),
        item_styles=[item["style"] for item in normalized_items],
        item_categories=[item["category"] for item in normalized_items],
        item_colors=[item["color"] for item in normalized_items],
        item_warmth=[item["warmth"] for item in normalized_items],
        item_sources=[item["source"] for item in normalized_items],
    )
    feedback_summary = _build_feedback_summary(repository.list_user_feedback(user_id=user_id))

    return {
        "saved_feedback": {
            "id": saved_feedback["id"],
            "feedback": saved_feedback["feedback"],
            "scenario": saved_feedback["scenario"],
            "requested_style": saved_feedback["requested_style"],
            "item_styles": list(saved_feedback.get("item_styles") or []),
            "item_categories": list(saved_feedback.get("item_categories") or []),
            "item_colors": list(saved_feedback.get("item_colors") or []),
            "item_warmth": list(saved_feedback.get("item_warmth") or []),
            "item_sources": list(saved_feedback.get("item_sources") or []),
        },
        "feedback_summary": feedback_summary,
        "style_preference_context": {
            "explicit": profile.get("style_preferences", []),
            "learned_weights": feedback_summary.get("style_weights", {}),
        },
    }
