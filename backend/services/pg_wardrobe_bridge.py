from __future__ import annotations

from typing import Any, Dict, List, Optional, Sequence

from psycopg.types.json import Jsonb

from database.db import get_repository, stable_user_id_from_owner_token


LEGACY_TO_PG_CATEGORY_ROLE = {
    "tshirt": ("t_shirt", "top"),
    "top": ("top", "top"),
    "shirt": ("shirt", "top"),
    "sweater": ("knitwear", "top"),
    "hoodie": ("hoodie", "top"),
    "jeans": ("jeans", "bottom"),
    "trousers": ("trousers", "bottom"),
    "shorts": ("shorts", "bottom"),
    "skirt": ("skirt", "bottom"),
    "dress": ("dress", "dress"),
    "sneakers": ("sneakers", "shoes"),
    "boots": ("boots", "shoes"),
    "shoes": ("loafers", "shoes"),
    "loafers": ("loafers", "shoes"),
    "jacket": ("jacket", "outerwear"),
    "coat": ("coat", "outerwear"),
    "blazer": ("blazer", "outerwear"),
    "unknown": ("top", "top"),
}

PG_TO_LEGACY_CATEGORY = {
    "t_shirt": "tshirt",
    "top": "top",
    "shirt": "shirt",
    "knitwear": "sweater",
    "hoodie": "hoodie",
    "jeans": "jeans",
    "trousers": "trousers",
    "shorts": "shorts",
    "skirt": "skirt",
    "dress": "dress",
    "sneakers": "sneakers",
    "boots": "boots",
    "loafers": "loafers",
    "heels": "shoes",
    "flats": "shoes",
    "jacket": "jacket",
    "coat": "coat",
    "blazer": "blazer",
    "trench": "coat",
    "vest": "jacket",
}

LEGACY_STYLE_TO_PRIMARY = {
    "minimal": "minimal",
    "casual": "casual",
    "sport": "activewear",
    "classic": "smart casual",
    "formal": "office casual",
    "streetwear": "street casual",
    "romantic": "feminine casual",
    "technical": "activewear",
    "old_money": "office casual",
    "unknown": None,
}

PRIMARY_TO_LEGACY_STYLE = {
    "minimal": "minimal",
    "casual": "casual",
    "activewear": "sport",
    "smart casual": "classic",
    "office casual": "formal",
    "street casual": "streetwear",
    "feminine casual": "romantic",
}


def _normalize_category(category: Optional[str]) -> str:
    value = str(category or "").strip().lower()
    return value or "unknown"


def _normalize_style(style: Optional[str]) -> str:
    value = str(style or "").strip().lower()
    return value or "unknown"


def _style_primary(style: Optional[str]) -> Optional[str]:
    return LEGACY_STYLE_TO_PRIMARY.get(_normalize_style(style))


def _warmth_level(category: str, style: str) -> int:
    if category in {"coat", "boots"}:
        return 2
    if style in {"technical", "sport"}:
        return 1
    return 1


def _season_tags(category: str) -> list[str]:
    if category in {"coat", "boots"}:
        return ["autumn", "winter"]
    if category in {"shorts", "skirt", "tshirt", "top"}:
        return ["spring", "summer"]
    return ["spring", "autumn", "all_season"]


def _weather_tags(category: str) -> list[str]:
    if category in {"coat", "boots"}:
        return ["cold", "windy"]
    if category in {"shorts", "skirt", "tshirt", "top"}:
        return ["warm"]
    return ["mild"]


def _serialize_pg_item(row: Dict[str, Any]) -> Dict[str, Any]:
    notes = row.get("notes") or {}
    return {
        "id": int(row["id"]),
        "title": row.get("title") or "Новая вещь",
        "category": notes.get("legacy_category") or PG_TO_LEGACY_CATEGORY.get(str(row.get("category") or "").strip().lower(), "unknown"),
        "color": row.get("color_raw") or "unknown",
        "image_url": row.get("primary_image_url"),
        "style": notes.get("legacy_style") or PRIMARY_TO_LEGACY_STYLE.get(str(row.get("style_primary") or "").strip().lower(), "unknown"),
        "vision_source": notes.get("vision_source") or "pg",
        "manually_edited": bool(notes.get("manually_edited", False)),
    }


def list_pg_wardrobe(owner_token: str) -> List[Dict[str, Any]]:
    repository = get_repository()
    user_id = stable_user_id_from_owner_token(owner_token)
    rows = repository.list_user_wardrobe_items(user_id=user_id)
    return [_serialize_pg_item(row) for row in rows]


def create_pg_wardrobe_item(
    *,
    owner_token: str,
    title: str,
    category: str,
    color: str,
    style: str,
    image_url: Optional[str] = None,
    vision_source: Optional[str] = None,
    vision_payload_path: Optional[str] = None,
    manually_edited: bool = False,
) -> int:
    repository = get_repository()
    user_id = stable_user_id_from_owner_token(owner_token)
    legacy_category = _normalize_category(category)
    legacy_style = _normalize_style(style)
    pg_category, role = LEGACY_TO_PG_CATEGORY_ROLE.get(legacy_category, ("top", "top"))

    return repository.upsert_user_wardrobe_item(
        {
            "user_id": user_id,
            "title": str(title or "Новая вещь").strip() or "Новая вещь",
            "category": pg_category,
            "role": role,
            "gender_target": "unisex",
            "primary_image_url": image_url,
            "color_raw": str(color or "unknown").strip().lower() or "unknown",
            "fit_raw": None,
            "material_raw": None,
            "style_primary": _style_primary(legacy_style),
            "style_secondary": [],
            "formality": "sport" if legacy_style == "sport" else "smart_casual" if legacy_style in {"classic", "formal", "old_money"} else "casual",
            "season_tags": _season_tags(legacy_category),
            "weather_tags": _weather_tags(legacy_category),
            "occasion_tags": [],
            "warmth_level": _warmth_level(legacy_category, legacy_style),
            "notes": {
                "owner_token": owner_token,
                "legacy_category": legacy_category,
                "legacy_style": legacy_style,
                "vision_source": vision_source,
                "vision_payload_path": vision_payload_path,
                "manually_edited": manually_edited,
            },
        }
    )


def update_pg_wardrobe_item(
    *,
    owner_token: str,
    item_id: int,
    title: str,
    category: str,
    color: str,
    style: str,
) -> bool:
    repository = get_repository()
    user_id = stable_user_id_from_owner_token(owner_token)
    legacy_category = _normalize_category(category)
    legacy_style = _normalize_style(style)
    pg_category, role = LEGACY_TO_PG_CATEGORY_ROLE.get(legacy_category, ("top", "top"))

    with repository.database.connection() as conn:
        row = conn.execute(
            """
            SELECT id, notes, primary_image_url
            FROM user_wardrobe_items
            WHERE id = %s AND user_id = %s
            """,
            (item_id, user_id),
        ).fetchone()
        if not row:
            return False

        notes = dict(row.get("notes") or {})
        notes.update(
            {
                "owner_token": owner_token,
                "legacy_category": legacy_category,
                "legacy_style": legacy_style,
                "manually_edited": True,
            }
        )

        conn.execute(
            """
            UPDATE user_wardrobe_items
            SET title = %s,
                category = %s,
                color_raw = %s,
                role = %s,
                style_primary = %s,
                formality = %s,
                season_tags = %s,
                weather_tags = %s,
                warmth_level = %s,
                notes = %s,
                updated_at = NOW()
            WHERE id = %s AND user_id = %s
            """,
            (
                str(title or "Новая вещь").strip() or "Новая вещь",
                pg_category,
                str(color or "unknown").strip().lower() or "unknown",
                role,
                _style_primary(legacy_style),
                "sport" if legacy_style == "sport" else "smart_casual" if legacy_style in {"classic", "formal", "old_money"} else "casual",
                _season_tags(legacy_category),
                _weather_tags(legacy_category),
                _warmth_level(legacy_category, legacy_style),
                Jsonb(notes),
                item_id,
                user_id,
            ),
        )
        return True


def delete_pg_wardrobe_items(*, owner_token: str, item_ids: Sequence[int]) -> int:
    repository = get_repository()
    user_id = stable_user_id_from_owner_token(owner_token)
    return repository.delete_user_wardrobe_items(user_id=user_id, item_ids=item_ids)


def clear_pg_wardrobe(*, owner_token: str) -> int:
    repository = get_repository()
    user_id = stable_user_id_from_owner_token(owner_token)
    return repository.delete_user_wardrobe_items(user_id=user_id)
