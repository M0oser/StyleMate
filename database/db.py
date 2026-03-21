import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(__file__), "wardrobe.db")


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
    }

    for column, sql in migrations.items():
        if column not in columns:
            cur.execute(sql)

    conn.commit()
    conn.close()


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
        purpose_tags TEXT DEFAULT ''
    )
    """)

    conn.commit()
    conn.close()
    ensure_shop_catalog_schema()


def save_to_shop_catalog(item_dict, db_path=DB_PATH):
    ensure_shop_catalog_schema(db_path)

    conn = sqlite3.connect(db_path)
    cur = conn.cursor()

    cur.execute("""
    INSERT OR IGNORE INTO shop_catalog
    (title, category, color, price, url, image_url, currency, source, external_id, gender, style, warmth, water_resistant, weather_tags, weather_rain, weather_wind, weather_snow, weather_heat, weather_profiles, purpose_tags)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
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
    ))

    conn.commit()
    conn.close()


def _build_catalog_where(category=None, source=None, query=None, gender=None, style=None, warmth=None, weather_tag=None, weather_profile=None, water_resistant=None, weather_rain=None, weather_wind=None, weather_snow=None, weather_heat=None, purpose_tag=None):
    where = []
    params = []

    if category:
        where.append("LOWER(category) = LOWER(?)")
        params.append(category)
    if source:
        where.append("LOWER(source) = LOWER(?)")
        params.append(source)
    if gender:
        where.append("LOWER(COALESCE(gender, 'unisex')) = LOWER(?)")
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
    if query:
        where.append(
            "("
            "LOWER(title) LIKE LOWER(?) OR "
            "LOWER(COALESCE(color, '')) LIKE LOWER(?) OR "
            "LOWER(COALESCE(category, '')) LIKE LOWER(?)"
            ")"
        )
        like = f"%{query}%"
        params.extend([like, like, like])

    return where, params


def get_catalog_items(limit=None, offset=0, category=None, source=None, query=None, gender=None, style=None, warmth=None, weather_tag=None, weather_profile=None, water_resistant=None, weather_rain=None, weather_wind=None, weather_snow=None, weather_heat=None, purpose_tag=None, db_path=DB_PATH):
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
    )

    sql = """
    SELECT id, title, category, color, price, url, image_url, currency, source, external_id, gender, style, warmth, water_resistant, weather_tags, weather_rain, weather_wind, weather_snow, weather_heat, weather_profiles, purpose_tags
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


def count_catalog_items(category=None, source=None, query=None, gender=None, style=None, warmth=None, weather_tag=None, weather_profile=None, water_resistant=None, weather_rain=None, weather_wind=None, weather_snow=None, weather_heat=None, purpose_tag=None, db_path=DB_PATH):
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
