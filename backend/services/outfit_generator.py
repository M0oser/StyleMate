import os
import json
import sqlite3
from dataclasses import dataclass
from typing import List, Optional, Dict, Any


@dataclass
class WardrobeItem:
    id: int
    title: str
    price: Optional[float]
    currency: Optional[str]
    url: str
    image_url: Optional[str]
    cat: str
    color: Optional[str]
    source: str
    style: Optional[str] = None
    gender: Optional[str] = None
    warmth: Optional[str] = None
    weather_tags: Optional[str] = None
    weather_profiles: Optional[str] = None
    purpose_tags: Optional[str] = None
    subcategory: Optional[str] = None
    material_tags: Optional[str] = None
    fit_tags: Optional[str] = None
    feature_tags: Optional[str] = None
    usecase_tags: Optional[str] = None
    hooded: bool = False
    waterproof: bool = False
    windproof: bool = False
    insulated: bool = False
    technical: bool = False
    many_pockets: bool = False
    pocket_level: Optional[str] = None
    vision_source: Optional[str] = None
    manually_edited: bool = False
    vision_payload_path: Optional[str] = None


def normalize_category(category: Optional[str]) -> str:
    if not category:
        return "unknown"

    c = category.lower().strip()

    mapping = {
        "t-shirt": "tshirt",
        "tee": "tshirt",
        "top": "tshirt",
        "tank top": "top",
        "pants": "trousers",
        "trouser": "trousers",
        "leggings": "trousers",
        "sneaker": "sneakers",
        "boot": "boots",
        "shoe": "shoes",
        "jean": "jeans",
        "blouse": "shirt",
        "sweatshirt": "sweater",
        "cardigan": "sweater",
    }

    return mapping.get(c, c)


def normalize_color(color: Optional[str]) -> str:
    if not color:
        return "unknown"
    return color.lower().strip()


def normalize_style(style: Optional[str]) -> str:
    if not style:
        return "unknown"

    value = style.lower().strip()
    mapping = {
        "minimalist": "minimal",
        "sporty": "sport",
        "classic": "classic",
        "formal": "formal",
        "casual": "casual",
        "streetwear": "streetwear",
        "romantic": "romantic",
        "technical": "technical",
        "old money": "old_money",
    }
    return mapping.get(value, value)


def ensure_user_wardrobe_schema(db_path: str = "database/wardrobe.db") -> None:
    if not os.path.exists(db_path):
        return

    con = sqlite3.connect(db_path)
    cur = con.cursor()

    cur.execute("PRAGMA table_info(user_wardrobe)")
    columns = {row[1] for row in cur.fetchall()}

    migrations = {
        "style": "ALTER TABLE user_wardrobe ADD COLUMN style TEXT",
        "vision_source": "ALTER TABLE user_wardrobe ADD COLUMN vision_source TEXT",
        "vision_payload": "ALTER TABLE user_wardrobe ADD COLUMN vision_payload TEXT",
        "vision_payload_path": "ALTER TABLE user_wardrobe ADD COLUMN vision_payload_path TEXT",
        "manually_edited": "ALTER TABLE user_wardrobe ADD COLUMN manually_edited INTEGER DEFAULT 0",
        "owner_token": "ALTER TABLE user_wardrobe ADD COLUMN owner_token TEXT",
    }

    for column, sql in migrations.items():
        if column not in columns:
            cur.execute(sql)

    con.commit()
    con.close()


def normalize_owner_token(owner_token: Optional[str]) -> Optional[str]:
    if owner_token is None:
        return None

    normalized = str(owner_token).strip()
    if not normalized:
        return None

    return normalized[:128]


def get_shop_catalog_columns(db_path: str = "database/wardrobe.db") -> set:
    if not os.path.exists(db_path):
        return set()

    con = sqlite3.connect(db_path)
    cur = con.cursor()
    try:
        cur.execute("PRAGMA table_info(shop_catalog)")
        return {row[1] for row in cur.fetchall()}
    finally:
        con.close()


def load_user_wardrobe(
    db_path: str = "database/wardrobe.db",
    limit: int = 200,
    owner_token: Optional[str] = None,
) -> List[WardrobeItem]:
    if not os.path.exists(db_path):
        print(f"[OUTFIT_GENERATOR] user db not found: {db_path}")
        return []

    ensure_user_wardrobe_schema(db_path=db_path)
    normalized_owner_token = normalize_owner_token(owner_token)

    if not normalized_owner_token:
        return []

    con = sqlite3.connect(db_path)
    cur = con.cursor()

    cur.execute("""
        SELECT id, title, category, color, image_url, style, vision_source, manually_edited, vision_payload_path
        FROM user_wardrobe
        WHERE category IS NOT NULL AND owner_token = ?
        ORDER BY id DESC
        LIMIT ?
    """, (normalized_owner_token, limit))
    rows = cur.fetchall()
    con.close()

    items: List[WardrobeItem] = []
    for pid, title, category, color, image_url, style, vision_source, manually_edited, vision_payload_path in rows:
        items.append(
            WardrobeItem(
                id=pid,
                title=title,
                price=None,
                currency=None,
                url="",
                image_url=image_url,
                cat=normalize_category(category),
                color=normalize_color(color),
                source="user",
                style=normalize_style(style),
                gender="unisex",
                vision_source=(vision_source or "").strip() or None,
                manually_edited=bool(manually_edited),
                vision_payload_path=(vision_payload_path or "").strip() or None,
            )
        )

    print("[OUTFIT_GENERATOR] user categories:", [item.cat for item in items])
    return items


def load_shop_wardrobe(db_path: str = "database/wardrobe.db", limit: int = 300) -> List[WardrobeItem]:
    if not os.path.exists(db_path):
        print(f"[OUTFIT_GENERATOR] shop db not found: {db_path}")
        return []

    con = sqlite3.connect(db_path)
    cur = con.cursor()

    table_name = None
    for candidate in ["shop_catalog", "products"]:
        try:
            cur.execute(f"SELECT 1 FROM {candidate} LIMIT 1")
            table_name = candidate
            break
        except sqlite3.Error:
            continue

    if not table_name:
        con.close()
        print("[OUTFIT_GENERATOR] neither shop_catalog nor products found")
        return []

    table_columns = get_shop_catalog_columns(db_path=db_path) if table_name == "shop_catalog" else set()
    source_expr = "source" if "source" in table_columns else "'shop'"
    currency_expr = "currency" if "currency" in table_columns else "'RUB'"
    gender_expr = "gender" if "gender" in table_columns else "'unisex'"
    style_expr = "style" if "style" in table_columns else "'casual'"
    warmth_expr = "warmth" if "warmth" in table_columns else "NULL"
    weather_tags_expr = "weather_tags" if "weather_tags" in table_columns else "NULL"
    weather_profiles_expr = "weather_profiles" if "weather_profiles" in table_columns else "NULL"
    purpose_tags_expr = "purpose_tags" if "purpose_tags" in table_columns else "NULL"
    subcategory_expr = "subcategory" if "subcategory" in table_columns else "NULL"
    material_tags_expr = "material_tags" if "material_tags" in table_columns else "NULL"
    fit_tags_expr = "fit_tags" if "fit_tags" in table_columns else "NULL"
    feature_tags_expr = "feature_tags" if "feature_tags" in table_columns else "NULL"
    usecase_tags_expr = "usecase_tags" if "usecase_tags" in table_columns else "NULL"
    hooded_expr = "hooded" if "hooded" in table_columns else "0"
    waterproof_expr = "waterproof" if "waterproof" in table_columns else "0"
    windproof_expr = "windproof" if "windproof" in table_columns else "0"
    insulated_expr = "insulated" if "insulated" in table_columns else "0"
    technical_expr = "technical" if "technical" in table_columns else "0"
    many_pockets_expr = "many_pockets" if "many_pockets" in table_columns else "0"
    pocket_level_expr = "pocket_level" if "pocket_level" in table_columns else "'low'"

    try:
        cur.execute(f"""
            SELECT
                id, title, price, {currency_expr} as currency, url, image_url, category, color,
                {source_expr} as source, {gender_expr} as gender, {style_expr} as style,
                {warmth_expr} as warmth, {weather_tags_expr} as weather_tags,
                {weather_profiles_expr} as weather_profiles, {purpose_tags_expr} as purpose_tags,
                {subcategory_expr} as subcategory, {material_tags_expr} as material_tags,
                {fit_tags_expr} as fit_tags, {feature_tags_expr} as feature_tags,
                {usecase_tags_expr} as usecase_tags, {hooded_expr} as hooded,
                {waterproof_expr} as waterproof, {windproof_expr} as windproof,
                {insulated_expr} as insulated, {technical_expr} as technical,
                {many_pockets_expr} as many_pockets, {pocket_level_expr} as pocket_level
            FROM {table_name}
            WHERE category IS NOT NULL
            ORDER BY id DESC
            LIMIT ?
        """, (limit,))
        rows = cur.fetchall()
    finally:
        con.close()

    items: List[WardrobeItem] = []
    for (
        pid, title, price, currency, url, image_url, category, color, source, gender, style,
        warmth, weather_tags, weather_profiles, purpose_tags, subcategory, material_tags,
        fit_tags, feature_tags, usecase_tags, hooded, waterproof, windproof, insulated,
        technical, many_pockets, pocket_level,
    ) in rows:
        cat = normalize_category(category)

        if cat in {"unknown", "accessory"}:
            continue

        items.append(
            WardrobeItem(
                id=pid,
                title=title,
                price=price,
                currency=(currency or "RUB").strip().upper() if isinstance(currency, str) else "RUB",
                url=url or "",
                image_url=image_url,
                cat=cat,
                color=normalize_color(color),
                source=(source or "").strip().lower() or "shop",
                style=normalize_style(style),
                gender=(gender or "unisex").strip().lower() if isinstance(gender, str) else "unisex",
                warmth=(warmth or "").strip().lower() if isinstance(warmth, str) else None,
                weather_tags=(weather_tags or "").strip() if isinstance(weather_tags, str) else None,
                weather_profiles=(weather_profiles or "").strip() if isinstance(weather_profiles, str) else None,
                purpose_tags=(purpose_tags or "").strip() if isinstance(purpose_tags, str) else None,
                subcategory=(subcategory or "").strip() if isinstance(subcategory, str) else None,
                material_tags=(material_tags or "").strip() if isinstance(material_tags, str) else None,
                fit_tags=(fit_tags or "").strip() if isinstance(fit_tags, str) else None,
                feature_tags=(feature_tags or "").strip() if isinstance(feature_tags, str) else None,
                usecase_tags=(usecase_tags or "").strip() if isinstance(usecase_tags, str) else None,
                hooded=bool(hooded),
                waterproof=bool(waterproof),
                windproof=bool(windproof),
                insulated=bool(insulated),
                technical=bool(technical),
                many_pockets=bool(many_pockets),
                pocket_level=(pocket_level or "").strip().lower() if isinstance(pocket_level, str) else None,
            )
        )

    print("[OUTFIT_GENERATOR] shop categories:", [item.cat for item in items[:30]])
    return items


def load_wardrobe_from_db(
    db_path: str = "database/wardrobe.db",
    limit: int = 200,
    source_mode: str = "user",
    owner_token: Optional[str] = None,
) -> List[WardrobeItem]:
    source_mode = (source_mode or "user").lower().strip()
    normalized_owner_token = normalize_owner_token(owner_token)

    if source_mode == "user":
        return load_user_wardrobe(db_path=db_path, limit=limit, owner_token=normalized_owner_token)

    if source_mode == "shop":
        return load_shop_wardrobe(db_path=db_path, limit=limit)

    if source_mode == "mixed":
        user_items = load_user_wardrobe(db_path=db_path, limit=limit, owner_token=normalized_owner_token)
        shop_items = load_shop_wardrobe(db_path=db_path, limit=limit)

        mixed = user_items + shop_items

        print(
            f"[OUTFIT_GENERATOR] mixed mode: "
            f"user={len(user_items)}, shop={len(shop_items)}, total={len(mixed)}"
        )
        return mixed

    print(f"[OUTFIT_GENERATOR] unknown source_mode={source_mode}, fallback to user")
    return load_user_wardrobe(db_path=db_path, limit=limit, owner_token=normalized_owner_token)


def insert_user_wardrobe_item(
    title: str,
    category: str,
    color: str,
    style: str = "unknown",
    image_url: str = None,
    vision_source: str = None,
    vision_payload: Optional[Dict[str, Any]] = None,
    vision_payload_path: str = None,
    manually_edited: bool = False,
    owner_token: Optional[str] = None,
    db_path: str = "database/wardrobe.db"
):
    if not os.path.exists(db_path):
        print(f"Ошибка: База {db_path} не найдена!")
        return False

    ensure_user_wardrobe_schema(db_path=db_path)

    normalized_category = normalize_category(category)
    normalized_color = normalize_color(color)
    normalized_style = normalize_style(style)
    normalized_owner_token = normalize_owner_token(owner_token)
    payload_json = json.dumps(vision_payload, ensure_ascii=False) if vision_payload else None

    con = sqlite3.connect(db_path)
    cur = con.cursor()

    cur.execute("""
        INSERT INTO user_wardrobe (
            title, category, color, image_url, style, vision_source,
            vision_payload, vision_payload_path, manually_edited, owner_token
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        title,
        normalized_category,
        normalized_color,
        image_url,
        normalized_style,
        vision_source,
        payload_json,
        vision_payload_path,
        1 if manually_edited else 0,
        normalized_owner_token,
    ))

    con.commit()
    new_id = cur.lastrowid
    con.close()
    return new_id


def update_user_wardrobe_item(
    item_id: int,
    title: str,
    category: str,
    color: str,
    style: str,
    owner_token: Optional[str] = None,
    db_path: str = "database/wardrobe.db"
) -> bool:
    if not os.path.exists(db_path):
        return False

    ensure_user_wardrobe_schema(db_path=db_path)
    normalized_owner_token = normalize_owner_token(owner_token)

    if not normalized_owner_token:
        return False

    con = sqlite3.connect(db_path)
    cur = con.cursor()
    cur.execute("""
        UPDATE user_wardrobe
        SET title = ?, category = ?, color = ?, style = ?, manually_edited = 1
        WHERE id = ? AND owner_token = ?
    """, (
        title.strip() or "Новая вещь",
        normalize_category(category),
        normalize_color(color),
        normalize_style(style),
        item_id,
        normalized_owner_token,
    ))
    con.commit()
    updated = cur.rowcount > 0
    con.close()
    return updated


def _remove_file_if_exists(path: Optional[str]) -> None:
    if not path:
        return

    try:
        if os.path.exists(path):
            os.remove(path)
    except OSError as e:
        print(f"[OUTFIT_GENERATOR] failed to remove file {path}: {e}")


def _image_url_to_local_path(image_url: Optional[str]) -> Optional[str]:
    if not image_url:
        return None

    image_url = image_url.strip()
    prefix = "/static/"
    if not image_url.startswith(prefix):
        return None

    relative_path = image_url[len(prefix):]
    local_path = os.path.abspath(os.path.join("frontend_tma", relative_path))
    uploads_root = os.path.abspath(os.path.join("frontend_tma", "uploads"))

    if os.path.commonpath([uploads_root, local_path]) != uploads_root:
        return None

    return local_path


def delete_user_wardrobe_items(
    item_ids: List[int],
    owner_token: Optional[str] = None,
    db_path: str = "database/wardrobe.db"
) -> int:
    if not os.path.exists(db_path) or not item_ids:
        return 0

    normalized_ids = []
    for item_id in item_ids:
        try:
            normalized_ids.append(int(item_id))
        except (TypeError, ValueError):
            continue

    if not normalized_ids:
        return 0

    ensure_user_wardrobe_schema(db_path=db_path)
    normalized_owner_token = normalize_owner_token(owner_token)

    if not normalized_owner_token:
        return 0

    con = sqlite3.connect(db_path)
    cur = con.cursor()

    placeholders = ", ".join("?" for _ in normalized_ids)
    cur.execute(
        f"""
        SELECT image_url, vision_payload_path
        FROM user_wardrobe
        WHERE owner_token = ? AND id IN ({placeholders})
        """,
        (normalized_owner_token, *normalized_ids),
    )
    assets = cur.fetchall()

    cur.execute(
        f"DELETE FROM user_wardrobe WHERE owner_token = ? AND id IN ({placeholders})",
        (normalized_owner_token, *normalized_ids),
    )
    deleted_count = cur.rowcount
    con.commit()
    con.close()

    for image_url, vision_payload_path in assets:
        _remove_file_if_exists(_image_url_to_local_path(image_url))
        _remove_file_if_exists(vision_payload_path)

    return deleted_count


def clear_user_wardrobe(
    db_path: str = "database/wardrobe.db",
    owner_token: Optional[str] = None,
) -> int:
    if not os.path.exists(db_path):
        return 0

    ensure_user_wardrobe_schema(db_path=db_path)
    normalized_owner_token = normalize_owner_token(owner_token)

    if not normalized_owner_token:
        return 0

    con = sqlite3.connect(db_path)
    cur = con.cursor()
    cur.execute("SELECT id FROM user_wardrobe WHERE owner_token = ?", (normalized_owner_token,))
    item_ids = [row[0] for row in cur.fetchall()]
    con.close()

    return delete_user_wardrobe_items(item_ids, owner_token=normalized_owner_token, db_path=db_path)
