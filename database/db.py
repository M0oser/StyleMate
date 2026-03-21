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
        style TEXT DEFAULT 'casual'
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
    (title, category, color, price, url, image_url, currency, source, external_id, gender, style)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
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
    ))

    conn.commit()
    conn.close()


def _build_catalog_where(category=None, source=None, query=None, gender=None, style=None):
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


def get_catalog_items(limit=None, offset=0, category=None, source=None, query=None, gender=None, style=None, db_path=DB_PATH):
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
    )

    sql = """
    SELECT id, title, category, color, price, url, image_url, currency, source, external_id, gender, style
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


def count_catalog_items(category=None, source=None, query=None, gender=None, style=None, db_path=DB_PATH):
    ensure_shop_catalog_schema(db_path)
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    where, params = _build_catalog_where(
        category=category,
        source=source,
        query=query,
        gender=gender,
        style=style,
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
