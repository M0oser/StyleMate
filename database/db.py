import json
import os
import sqlite3
import hashlib

DB_PATH = os.path.join(os.path.dirname(__file__), "wardrobe.db")
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


def ensure_shop_catalog_schema(db_path=DB_PATH):
    if not os.path.exists(db_path):
        return

    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    cur.execute("PRAGMA table_info(shop_catalog)")
    columns = {row[1] for row in cur.fetchall()}

    migrations = {
        "currency": "ALTER TABLE shop_catalog ADD COLUMN currency TEXT DEFAULT 'RUB'",
        "source": "ALTER TABLE shop_catalog ADD COLUMN source TEXT DEFAULT 'unknown'",
        "external_id": "ALTER TABLE shop_catalog ADD COLUMN external_id TEXT",
        "gender": "ALTER TABLE shop_catalog ADD COLUMN gender TEXT DEFAULT 'unisex'",
        "style": "ALTER TABLE shop_catalog ADD COLUMN style TEXT DEFAULT 'casual'",
        "warmth": "ALTER TABLE shop_catalog ADD COLUMN warmth TEXT DEFAULT 'mid'",
        "water_resistant": "ALTER TABLE shop_catalog ADD COLUMN water_resistant INTEGER DEFAULT 0",
        "weather_tags": "ALTER TABLE shop_catalog ADD COLUMN weather_tags TEXT DEFAULT ''",
        "weather_rain": "ALTER TABLE shop_catalog ADD COLUMN weather_rain INTEGER DEFAULT 0",
        "weather_wind": "ALTER TABLE shop_catalog ADD COLUMN weather_wind INTEGER DEFAULT 0",
        "weather_snow": "ALTER TABLE shop_catalog ADD COLUMN weather_snow INTEGER DEFAULT 0",
        "weather_heat": "ALTER TABLE shop_catalog ADD COLUMN weather_heat INTEGER DEFAULT 0",
        "weather_profiles": "ALTER TABLE shop_catalog ADD COLUMN weather_profiles TEXT DEFAULT ''",
        "purpose_tags": "ALTER TABLE shop_catalog ADD COLUMN purpose_tags TEXT DEFAULT ''",
        "subcategory": "ALTER TABLE shop_catalog ADD COLUMN subcategory TEXT DEFAULT ''",
        "material_tags": "ALTER TABLE shop_catalog ADD COLUMN material_tags TEXT DEFAULT ''",
        "fit_tags": "ALTER TABLE shop_catalog ADD COLUMN fit_tags TEXT DEFAULT ''",
        "feature_tags": "ALTER TABLE shop_catalog ADD COLUMN feature_tags TEXT DEFAULT ''",
        "usecase_tags": "ALTER TABLE shop_catalog ADD COLUMN usecase_tags TEXT DEFAULT ''",
        "hooded": "ALTER TABLE shop_catalog ADD COLUMN hooded INTEGER DEFAULT 0",
        "waterproof": "ALTER TABLE shop_catalog ADD COLUMN waterproof INTEGER DEFAULT 0",
        "windproof": "ALTER TABLE shop_catalog ADD COLUMN windproof INTEGER DEFAULT 0",
        "insulated": "ALTER TABLE shop_catalog ADD COLUMN insulated INTEGER DEFAULT 0",
        "technical": "ALTER TABLE shop_catalog ADD COLUMN technical INTEGER DEFAULT 0",
        "many_pockets": "ALTER TABLE shop_catalog ADD COLUMN many_pockets INTEGER DEFAULT 0",
        "pocket_level": "ALTER TABLE shop_catalog ADD COLUMN pocket_level TEXT DEFAULT 'low'",
    }

    for column, sql in migrations.items():
        if column not in columns:
            cur.execute(sql)

    conn.commit()
    conn.close()


def ensure_user_profile_schema(db_path=DB_PATH):
    if not os.path.exists(db_path):
        return

    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    cur.execute("""
    CREATE TABLE IF NOT EXISTS user_profiles(
        owner_token TEXT PRIMARY KEY,
        display_name TEXT DEFAULT '',
        gender TEXT DEFAULT 'male',
        style_preferences TEXT DEFAULT '[]',
        onboarding_completed INTEGER DEFAULT 0,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
        last_active_at TEXT DEFAULT CURRENT_TIMESTAMP
    )
    """)

    cur.execute("PRAGMA table_info(user_profiles)")
    columns = {row[1] for row in cur.fetchall()}
    migrations = {
        "display_name": "ALTER TABLE user_profiles ADD COLUMN display_name TEXT DEFAULT ''",
        "gender": "ALTER TABLE user_profiles ADD COLUMN gender TEXT DEFAULT 'male'",
        "style_preferences": "ALTER TABLE user_profiles ADD COLUMN style_preferences TEXT DEFAULT '[]'",
        "onboarding_completed": "ALTER TABLE user_profiles ADD COLUMN onboarding_completed INTEGER DEFAULT 0",
        "created_at": "ALTER TABLE user_profiles ADD COLUMN created_at TEXT DEFAULT CURRENT_TIMESTAMP",
        "updated_at": "ALTER TABLE user_profiles ADD COLUMN updated_at TEXT DEFAULT CURRENT_TIMESTAMP",
        "last_active_at": "ALTER TABLE user_profiles ADD COLUMN last_active_at TEXT DEFAULT CURRENT_TIMESTAMP",
    }

    for column, sql in migrations.items():
        if column not in columns:
            cur.execute(sql)

    conn.commit()
    conn.close()


def ensure_user_feedback_schema(db_path=DB_PATH):
    if not os.path.exists(db_path):
        return

    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    cur.execute("""
    CREATE TABLE IF NOT EXISTS user_outfit_feedback(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        owner_token TEXT NOT NULL,
        feedback TEXT NOT NULL,
        scenario TEXT DEFAULT '',
        requested_style TEXT DEFAULT '',
        item_styles TEXT DEFAULT '[]',
        item_categories TEXT DEFAULT '[]',
        item_colors TEXT DEFAULT '[]',
        item_warmth TEXT DEFAULT '[]',
        item_sources TEXT DEFAULT '[]',
        created_at TEXT DEFAULT CURRENT_TIMESTAMP
    )
    """)

    cur.execute("PRAGMA table_info(user_outfit_feedback)")
    columns = {row[1] for row in cur.fetchall()}
    migrations = {
        "owner_token": "ALTER TABLE user_outfit_feedback ADD COLUMN owner_token TEXT NOT NULL DEFAULT ''",
        "feedback": "ALTER TABLE user_outfit_feedback ADD COLUMN feedback TEXT NOT NULL DEFAULT 'like'",
        "scenario": "ALTER TABLE user_outfit_feedback ADD COLUMN scenario TEXT DEFAULT ''",
        "requested_style": "ALTER TABLE user_outfit_feedback ADD COLUMN requested_style TEXT DEFAULT ''",
        "item_styles": "ALTER TABLE user_outfit_feedback ADD COLUMN item_styles TEXT DEFAULT '[]'",
        "item_categories": "ALTER TABLE user_outfit_feedback ADD COLUMN item_categories TEXT DEFAULT '[]'",
        "item_colors": "ALTER TABLE user_outfit_feedback ADD COLUMN item_colors TEXT DEFAULT '[]'",
        "item_warmth": "ALTER TABLE user_outfit_feedback ADD COLUMN item_warmth TEXT DEFAULT '[]'",
        "item_sources": "ALTER TABLE user_outfit_feedback ADD COLUMN item_sources TEXT DEFAULT '[]'",
        "created_at": "ALTER TABLE user_outfit_feedback ADD COLUMN created_at TEXT DEFAULT CURRENT_TIMESTAMP",
    }

    for column, sql in migrations.items():
        if column not in columns:
            cur.execute(sql)

    conn.commit()
    conn.close()


def _normalize_profile_gender(gender):
    value = str(gender or "").strip().lower()
    if value in PROFILE_GENDERS:
        return value
    return "male"


def _normalize_style_preferences(style_preferences):
    if style_preferences is None:
        return None

    if not isinstance(style_preferences, list):
        raise ValueError("style_preferences must be a list")

    normalized = []
    seen = set()
    for value in style_preferences:
        style = str(value or "").strip().lower()
        if style not in PROFILE_STYLE_OPTIONS or style in seen:
            continue
        normalized.append(style)
        seen.add(style)

    if len(normalized) > 3:
        raise ValueError("style_preferences must contain at most 3 styles")

    return normalized


def _normalize_feedback_signal(feedback):
    value = str(feedback or "").strip().lower()
    if value not in FEEDBACK_SIGNALS:
        raise ValueError("feedback must be 'like' or 'dislike'")
    return value


def _normalize_feedback_items(items):
    if not isinstance(items, list) or not items:
        raise ValueError("items must be a non-empty list")

    normalized_items = []
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


def _feedback_weight_from_counts(likes, dislikes):
    net = int(likes) - int(dislikes)
    if net > 0:
        return min(2, net)
    if net < 0:
        return max(-1, net)
    return 0


def _row_to_profile(row):
    if not row:
        return None

    try:
        style_preferences = json.loads(row[2] or "[]")
        if not isinstance(style_preferences, list):
            style_preferences = []
    except json.JSONDecodeError:
        style_preferences = []

    return {
        "display_name": row[0] or "",
        "gender": _normalize_profile_gender(row[1]),
        "style_preferences": _normalize_style_preferences(style_preferences) or [],
        "onboarding_completed": bool(row[3]),
        "created_at": row[4],
        "updated_at": row[5],
        "last_active_at": row[6],
    }


def get_or_create_user_profile(owner_token, db_path=DB_PATH):
    if not owner_token:
        raise ValueError("owner_token is required")

    ensure_user_profile_schema(db_path)
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    cur.execute(
        "INSERT OR IGNORE INTO user_profiles (owner_token) VALUES (?)",
        (owner_token,),
    )
    cur.execute(
        "UPDATE user_profiles SET last_active_at = CURRENT_TIMESTAMP WHERE owner_token = ?",
        (owner_token,),
    )
    cur.execute(
        """
        SELECT display_name, gender, style_preferences, onboarding_completed,
               created_at, updated_at, last_active_at
        FROM user_profiles
        WHERE owner_token = ?
        """,
        (owner_token,),
    )
    row = cur.fetchone()
    conn.commit()
    conn.close()
    return _row_to_profile(row)


def update_user_profile(
    owner_token,
    display_name=None,
    gender=None,
    style_preferences=None,
    onboarding_completed=None,
    db_path=DB_PATH,
):
    if not owner_token:
        raise ValueError("owner_token is required")

    current = get_or_create_user_profile(owner_token, db_path=db_path)

    next_display_name = current["display_name"] if display_name is None else str(display_name).strip()[:80]
    next_gender = current["gender"] if gender is None else _normalize_profile_gender(gender)
    normalized_preferences = _normalize_style_preferences(style_preferences)
    next_preferences = current["style_preferences"] if normalized_preferences is None else normalized_preferences
    next_onboarding_completed = current["onboarding_completed"] if onboarding_completed is None else bool(onboarding_completed)

    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    cur.execute(
        """
        UPDATE user_profiles
        SET display_name = ?,
            gender = ?,
            style_preferences = ?,
            onboarding_completed = ?,
            updated_at = CURRENT_TIMESTAMP,
            last_active_at = CURRENT_TIMESTAMP
        WHERE owner_token = ?
        """,
        (
            next_display_name,
            next_gender,
            json.dumps(next_preferences, ensure_ascii=False),
            1 if next_onboarding_completed else 0,
            owner_token,
        ),
    )
    conn.commit()
    conn.close()

    return get_or_create_user_profile(owner_token, db_path=db_path)


def save_user_feedback(
    owner_token,
    feedback,
    items,
    scenario=None,
    requested_style=None,
    db_path=DB_PATH,
):
    if not owner_token:
        raise ValueError("owner_token is required")

    ensure_user_feedback_schema(db_path)
    normalized_feedback = _normalize_feedback_signal(feedback)
    normalized_items = _normalize_feedback_items(items)

    item_styles = [item["style"] for item in normalized_items]
    item_categories = [item["category"] for item in normalized_items]
    item_colors = [item["color"] for item in normalized_items]
    item_warmth = [item["warmth"] for item in normalized_items]
    item_sources = [item["source"] for item in normalized_items]

    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    cur.execute(
        """
        INSERT INTO user_outfit_feedback (
            owner_token, feedback, scenario, requested_style,
            item_styles, item_categories, item_colors, item_warmth, item_sources
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            owner_token,
            normalized_feedback,
            str(scenario or "").strip(),
            str(requested_style or "").strip(),
            json.dumps(item_styles, ensure_ascii=False),
            json.dumps(item_categories, ensure_ascii=False),
            json.dumps(item_colors, ensure_ascii=False),
            json.dumps(item_warmth, ensure_ascii=False),
            json.dumps(item_sources, ensure_ascii=False),
        ),
    )
    feedback_id = cur.lastrowid
    conn.commit()
    conn.close()

    return {
        "id": feedback_id,
        "feedback": normalized_feedback,
        "scenario": str(scenario or "").strip(),
        "requested_style": str(requested_style or "").strip(),
        "item_styles": item_styles,
        "item_categories": item_categories,
        "item_colors": item_colors,
        "item_warmth": item_warmth,
        "item_sources": item_sources,
    }


def get_user_feedback_summary(owner_token, db_path=DB_PATH):
    if not owner_token:
        raise ValueError("owner_token is required")

    ensure_user_feedback_schema(db_path)
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    cur.execute(
        """
        SELECT feedback, item_styles, item_categories, item_colors, item_warmth, item_sources
        FROM user_outfit_feedback
        WHERE owner_token = ?
        ORDER BY id ASC
        """,
        (owner_token,),
    )
    rows = cur.fetchall()
    conn.close()

    style_signals = {}
    category_signals = {}
    trait_totals = {
        "styles": {},
        "categories": {},
        "colors": {},
        "warmth": {},
        "sources": {},
    }

    def _bump_counter(bucket, key):
        if not key or key == "unknown":
            return
        bucket[key] = bucket.get(key, 0) + 1

    for feedback, raw_styles, raw_categories, raw_colors, raw_warmth, raw_sources in rows:
        signal = _normalize_feedback_signal(feedback)
        try:
            styles = json.loads(raw_styles or "[]")
        except json.JSONDecodeError:
            styles = []
        try:
            categories = json.loads(raw_categories or "[]")
        except json.JSONDecodeError:
            categories = []
        try:
            colors = json.loads(raw_colors or "[]")
        except json.JSONDecodeError:
            colors = []
        try:
            warmth_values = json.loads(raw_warmth or "[]")
        except json.JSONDecodeError:
            warmth_values = []
        try:
            sources = json.loads(raw_sources or "[]")
        except json.JSONDecodeError:
            sources = []

        normalized_styles = {
            str(style or "").strip().lower()
            for style in styles
            if str(style or "").strip().lower() and str(style or "").strip().lower() != "unknown"
        }
        for style in normalized_styles:
            current = style_signals.setdefault(style, {"likes": 0, "dislikes": 0})
            current["likes" if signal == "like" else "dislikes"] += 1
        for style in styles:
            normalized_style = str(style or "").strip().lower()
            _bump_counter(trait_totals["styles"], normalized_style)

        normalized_categories = {
            str(category or "").strip().lower()
            for category in categories
            if str(category or "").strip().lower() and str(category or "").strip().lower() != "unknown"
        }
        for category in normalized_categories:
            current = category_signals.setdefault(category, {"likes": 0, "dislikes": 0})
            current["likes" if signal == "like" else "dislikes"] += 1
        for category in categories:
            normalized_category = str(category or "").strip().lower()
            _bump_counter(trait_totals["categories"], normalized_category)

        for color in colors:
            _bump_counter(trait_totals["colors"], str(color or "").strip().lower())
        for warmth in warmth_values:
            _bump_counter(trait_totals["warmth"], str(warmth or "").strip().lower())
        for source in sources:
            _bump_counter(trait_totals["sources"], str(source or "").strip().lower())

    style_weights = {}
    detailed_style_signals = {}
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


def init_db():

    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    cur.execute("""
    CREATE TABLE IF NOT EXISTS user_wardrobe(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT,
        category TEXT,
        color TEXT,
        image_url TEXT,
        style TEXT,
        vision_source TEXT,
        vision_payload TEXT,
        vision_payload_path TEXT,
        manually_edited INTEGER DEFAULT 0,
        owner_token TEXT
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS shop_catalog(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT,
        category TEXT,
        color TEXT,
        price REAL,
        url TEXT UNIQUE,
        image_url TEXT,
        currency TEXT DEFAULT 'RUB',
        source TEXT DEFAULT 'unknown',
        external_id TEXT,
        gender TEXT DEFAULT 'unisex',
        style TEXT DEFAULT 'casual',
        warmth TEXT DEFAULT 'mid',
        water_resistant INTEGER DEFAULT 0,
        weather_tags TEXT DEFAULT '',
        weather_rain INTEGER DEFAULT 0,
        weather_wind INTEGER DEFAULT 0,
        weather_snow INTEGER DEFAULT 0,
        weather_heat INTEGER DEFAULT 0,
        weather_profiles TEXT DEFAULT '',
        purpose_tags TEXT DEFAULT '',
        subcategory TEXT DEFAULT '',
        material_tags TEXT DEFAULT '',
        fit_tags TEXT DEFAULT '',
        feature_tags TEXT DEFAULT '',
        usecase_tags TEXT DEFAULT '',
        hooded INTEGER DEFAULT 0,
        waterproof INTEGER DEFAULT 0,
        windproof INTEGER DEFAULT 0,
        insulated INTEGER DEFAULT 0,
        technical INTEGER DEFAULT 0,
        many_pockets INTEGER DEFAULT 0,
        pocket_level TEXT DEFAULT 'low'
    )
    """)

    conn.commit()
    conn.close()
    ensure_shop_catalog_schema()
    ensure_user_profile_schema()
    ensure_user_feedback_schema()


def stable_user_id_from_owner_token(owner_token):
    if not owner_token:
        raise ValueError("owner_token is required")

    digest = hashlib.sha256(str(owner_token).strip().encode("utf-8")).hexdigest()
    return int(digest[:15], 16)


def get_repository():
    from database.config import get_database_settings
    from database.postgres import PostgresDatabase
    from database.repositories import CompletionDataRepository

    settings = get_database_settings()
    return CompletionDataRepository(PostgresDatabase(settings.dsn))


def init_postgres_db():
    from database.config import get_database_settings
    from database.postgres import PostgresDatabase
    from database.repositories import CompletionDataRepository

    settings = get_database_settings()
    repository = CompletionDataRepository(PostgresDatabase(settings.dsn))
    repository.initialize_schema(settings.migrations_dir)
    repository.seed_reference_data()
    return repository


def save_to_shop_catalog(item_dict, db_path=DB_PATH):
    ensure_shop_catalog_schema(db_path)

    conn = sqlite3.connect(db_path)
    cur = conn.cursor()

    cur.execute("""
    INSERT INTO shop_catalog
    (
        title, category, color, price, url, image_url, currency, source, external_id,
        gender, style, warmth, water_resistant, weather_tags, weather_rain,
        weather_wind, weather_snow, weather_heat, weather_profiles, purpose_tags,
        subcategory, material_tags, fit_tags, feature_tags, usecase_tags,
        hooded, waterproof, windproof, insulated, technical, many_pockets, pocket_level
    )
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ON CONFLICT(url) DO UPDATE SET
        title = excluded.title,
        category = excluded.category,
        color = COALESCE(excluded.color, shop_catalog.color),
        price = COALESCE(excluded.price, shop_catalog.price),
        image_url = COALESCE(excluded.image_url, shop_catalog.image_url),
        currency = COALESCE(excluded.currency, shop_catalog.currency),
        source = COALESCE(excluded.source, shop_catalog.source),
        external_id = COALESCE(excluded.external_id, shop_catalog.external_id),
        gender = COALESCE(excluded.gender, shop_catalog.gender),
        style = COALESCE(excluded.style, shop_catalog.style),
        warmth = COALESCE(excluded.warmth, shop_catalog.warmth),
        water_resistant = COALESCE(excluded.water_resistant, shop_catalog.water_resistant),
        weather_tags = COALESCE(excluded.weather_tags, shop_catalog.weather_tags),
        weather_rain = COALESCE(excluded.weather_rain, shop_catalog.weather_rain),
        weather_wind = COALESCE(excluded.weather_wind, shop_catalog.weather_wind),
        weather_snow = COALESCE(excluded.weather_snow, shop_catalog.weather_snow),
        weather_heat = COALESCE(excluded.weather_heat, shop_catalog.weather_heat),
        weather_profiles = COALESCE(excluded.weather_profiles, shop_catalog.weather_profiles),
        purpose_tags = COALESCE(excluded.purpose_tags, shop_catalog.purpose_tags),
        subcategory = COALESCE(NULLIF(excluded.subcategory, ''), shop_catalog.subcategory),
        material_tags = COALESCE(NULLIF(excluded.material_tags, ''), shop_catalog.material_tags),
        fit_tags = COALESCE(NULLIF(excluded.fit_tags, ''), shop_catalog.fit_tags),
        feature_tags = COALESCE(NULLIF(excluded.feature_tags, ''), shop_catalog.feature_tags),
        usecase_tags = COALESCE(NULLIF(excluded.usecase_tags, ''), shop_catalog.usecase_tags),
        hooded = COALESCE(excluded.hooded, shop_catalog.hooded),
        waterproof = COALESCE(excluded.waterproof, shop_catalog.waterproof),
        windproof = COALESCE(excluded.windproof, shop_catalog.windproof),
        insulated = COALESCE(excluded.insulated, shop_catalog.insulated),
        technical = COALESCE(excluded.technical, shop_catalog.technical),
        many_pockets = COALESCE(excluded.many_pockets, shop_catalog.many_pockets),
        pocket_level = COALESCE(NULLIF(excluded.pocket_level, ''), shop_catalog.pocket_level)
    """, (
        item_dict.get("title"),
        item_dict.get("category"),
        item_dict.get("color"),
        item_dict.get("price"),
        item_dict.get("url"),
        item_dict.get("image_url"),
        item_dict.get("currency", "RUB"),
        item_dict.get("source", "unknown"),
        item_dict.get("external_id"),
        item_dict.get("gender", "unisex"),
        item_dict.get("style", "casual"),
        item_dict.get("warmth", "mid"),
        int(bool(item_dict.get("water_resistant", False))),
        item_dict.get("weather_tags", ""),
        int(bool(item_dict.get("weather_rain", False))),
        int(bool(item_dict.get("weather_wind", False))),
        int(bool(item_dict.get("weather_snow", False))),
        int(bool(item_dict.get("weather_heat", False))),
        item_dict.get("weather_profiles", ""),
        item_dict.get("purpose_tags", ""),
        item_dict.get("subcategory", ""),
        item_dict.get("material_tags", ""),
        item_dict.get("fit_tags", ""),
        item_dict.get("feature_tags", ""),
        item_dict.get("usecase_tags", ""),
        int(bool(item_dict.get("hooded", False))),
        int(bool(item_dict.get("waterproof", False))),
        int(bool(item_dict.get("windproof", False))),
        int(bool(item_dict.get("insulated", False))),
        int(bool(item_dict.get("technical", False))),
        int(bool(item_dict.get("many_pockets", False))),
        item_dict.get("pocket_level", "low"),
    ))

    conn.commit()
    conn.close()


def _build_catalog_where(
    category=None,
    source=None,
    query=None,
    gender=None,
    style=None,
    warmth=None,
    weather_tag=None,
    weather_profile=None,
    water_resistant=None,
    weather_rain=None,
    weather_wind=None,
    weather_snow=None,
    weather_heat=None,
    purpose_tag=None,
    usecase_tag=None,
    feature_tag=None,
    material_tag=None,
    subcategory=None,
    hooded=None,
    waterproof=None,
    windproof=None,
    insulated=None,
    technical=None,
    many_pockets=None,
    pocket_level=None,
):
    where = []
    params = []

    if category:
        where.append("LOWER(category) = LOWER(?)")
        params.append(category)
    if source:
        where.append("LOWER(source) = LOWER(?)")
        params.append(source)
    if gender:
        where.append("(LOWER(COALESCE(gender, 'unisex')) = LOWER(?) OR LOWER(COALESCE(gender, 'unisex')) = 'unisex')")
        params.append(gender)
    if style:
        where.append("LOWER(COALESCE(style, 'casual')) = LOWER(?)")
        params.append(style)
    if warmth:
        where.append("LOWER(COALESCE(warmth, 'mid')) = LOWER(?)")
        params.append(warmth)
    if weather_tag:
        where.append("LOWER(COALESCE(weather_tags, '')) LIKE LOWER(?)")
        params.append(f"%{weather_tag}%")
    if weather_profile:
        where.append("LOWER(COALESCE(weather_profiles, '')) LIKE LOWER(?)")
        params.append(f"%{weather_profile}%")
    if water_resistant is not None:
        where.append("COALESCE(water_resistant, 0) = ?")
        params.append(int(bool(water_resistant)))
    if weather_rain is not None:
        where.append("COALESCE(weather_rain, 0) = ?")
        params.append(int(bool(weather_rain)))
    if weather_wind is not None:
        where.append("COALESCE(weather_wind, 0) = ?")
        params.append(int(bool(weather_wind)))
    if weather_snow is not None:
        where.append("COALESCE(weather_snow, 0) = ?")
        params.append(int(bool(weather_snow)))
    if weather_heat is not None:
        where.append("COALESCE(weather_heat, 0) = ?")
        params.append(int(bool(weather_heat)))
    if purpose_tag:
        where.append("LOWER(COALESCE(purpose_tags, '')) LIKE LOWER(?)")
        params.append(f"%{purpose_tag}%")
    if usecase_tag:
        where.append("LOWER(COALESCE(usecase_tags, '')) LIKE LOWER(?)")
        params.append(f"%{usecase_tag}%")
    if feature_tag:
        where.append("LOWER(COALESCE(feature_tags, '')) LIKE LOWER(?)")
        params.append(f"%{feature_tag}%")
    if material_tag:
        where.append("LOWER(COALESCE(material_tags, '')) LIKE LOWER(?)")
        params.append(f"%{material_tag}%")
    if subcategory:
        where.append("LOWER(COALESCE(subcategory, '')) = LOWER(?)")
        params.append(subcategory)
    if hooded is not None:
        where.append("COALESCE(hooded, 0) = ?")
        params.append(int(bool(hooded)))
    if waterproof is not None:
        where.append("COALESCE(waterproof, 0) = ?")
        params.append(int(bool(waterproof)))
    if windproof is not None:
        where.append("COALESCE(windproof, 0) = ?")
        params.append(int(bool(windproof)))
    if insulated is not None:
        where.append("COALESCE(insulated, 0) = ?")
        params.append(int(bool(insulated)))
    if technical is not None:
        where.append("COALESCE(technical, 0) = ?")
        params.append(int(bool(technical)))
    if many_pockets is not None:
        where.append("COALESCE(many_pockets, 0) = ?")
        params.append(int(bool(many_pockets)))
    if pocket_level:
        where.append("LOWER(COALESCE(pocket_level, 'low')) = LOWER(?)")
        params.append(pocket_level)
    if query:
        where.append(
            "("
            "LOWER(title) LIKE LOWER(?) OR "
            "LOWER(COALESCE(color, '')) LIKE LOWER(?) OR "
            "LOWER(COALESCE(category, '')) LIKE LOWER(?) OR "
            "LOWER(COALESCE(subcategory, '')) LIKE LOWER(?) OR "
            "LOWER(COALESCE(fit_tags, '')) LIKE LOWER(?) OR "
            "LOWER(COALESCE(feature_tags, '')) LIKE LOWER(?) OR "
            "LOWER(COALESCE(usecase_tags, '')) LIKE LOWER(?) OR "
            "LOWER(COALESCE(material_tags, '')) LIKE LOWER(?)"
            ")"
        )
        like = f"%{query}%"
        params.extend([like, like, like, like, like, like, like, like])

    return where, params


def get_catalog_items(
    limit=None,
    offset=0,
    category=None,
    source=None,
    query=None,
    gender=None,
    style=None,
    warmth=None,
    weather_tag=None,
    weather_profile=None,
    water_resistant=None,
    weather_rain=None,
    weather_wind=None,
    weather_snow=None,
    weather_heat=None,
    purpose_tag=None,
    usecase_tag=None,
    feature_tag=None,
    material_tag=None,
    subcategory=None,
    hooded=None,
    waterproof=None,
    windproof=None,
    insulated=None,
    technical=None,
    many_pockets=None,
    pocket_level=None,
    db_path=DB_PATH,
):
    ensure_shop_catalog_schema(db_path)
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    where, params = _build_catalog_where(
        category=category,
        source=source,
        query=query,
        gender=gender,
        style=style,
        warmth=warmth,
        weather_tag=weather_tag,
        weather_profile=weather_profile,
        water_resistant=water_resistant,
        weather_rain=weather_rain,
        weather_wind=weather_wind,
        weather_snow=weather_snow,
        weather_heat=weather_heat,
        purpose_tag=purpose_tag,
        usecase_tag=usecase_tag,
        feature_tag=feature_tag,
        material_tag=material_tag,
        subcategory=subcategory,
        hooded=hooded,
        waterproof=waterproof,
        windproof=windproof,
        insulated=insulated,
        technical=technical,
        many_pockets=many_pockets,
        pocket_level=pocket_level,
    )

    sql = """
    SELECT
        id, title, category, color, price, url, image_url, currency, source, external_id,
        gender, style, warmth, water_resistant, weather_tags, weather_rain,
        weather_wind, weather_snow, weather_heat, weather_profiles, purpose_tags,
        subcategory, material_tags, fit_tags, feature_tags, usecase_tags,
        hooded, waterproof, windproof, insulated, technical, many_pockets, pocket_level
    FROM shop_catalog
    """
    if where:
        sql += " WHERE " + " AND ".join(where)
    sql += " ORDER BY id DESC"

    if limit is not None:
        sql += " LIMIT ? OFFSET ?"
        params.extend([limit, offset])
    elif offset:
        sql += " LIMIT -1 OFFSET ?"
        params.append(offset)

    cur.execute(sql, params)
    rows = [dict(row) for row in cur.fetchall()]
    conn.close()
    return rows


def count_catalog_items(
    category=None,
    source=None,
    query=None,
    gender=None,
    style=None,
    warmth=None,
    weather_tag=None,
    weather_profile=None,
    water_resistant=None,
    weather_rain=None,
    weather_wind=None,
    weather_snow=None,
    weather_heat=None,
    purpose_tag=None,
    usecase_tag=None,
    feature_tag=None,
    material_tag=None,
    subcategory=None,
    hooded=None,
    waterproof=None,
    windproof=None,
    insulated=None,
    technical=None,
    many_pockets=None,
    pocket_level=None,
    db_path=DB_PATH,
):
    ensure_shop_catalog_schema(db_path)
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()

    where, params = _build_catalog_where(
        category=category,
        source=source,
        query=query,
        gender=gender,
        style=style,
        warmth=warmth,
        weather_tag=weather_tag,
        weather_profile=weather_profile,
        water_resistant=water_resistant,
        weather_rain=weather_rain,
        weather_wind=weather_wind,
        weather_snow=weather_snow,
        weather_heat=weather_heat,
        purpose_tag=purpose_tag,
        usecase_tag=usecase_tag,
        feature_tag=feature_tag,
        material_tag=material_tag,
        subcategory=subcategory,
        hooded=hooded,
        waterproof=waterproof,
        windproof=windproof,
        insulated=insulated,
        technical=technical,
        many_pockets=many_pockets,
        pocket_level=pocket_level,
    )

    sql = "SELECT COUNT(*) FROM shop_catalog"
    if where:
        sql += " WHERE " + " AND ".join(where)

    cur.execute(sql, params)
    value = int(cur.fetchone()[0])
    conn.close()
    return value


def list_catalog_sources(db_path=DB_PATH):
    ensure_shop_catalog_schema(db_path)
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    cur.execute("""
        SELECT DISTINCT source
        FROM shop_catalog
        WHERE source IS NOT NULL AND TRIM(source) != ''
        ORDER BY source ASC
    """)
    sources = [row[0] for row in cur.fetchall()]
    conn.close()
    return sources


if __name__ == "__main__":

    init_db()
    print("Database created (empty).")
