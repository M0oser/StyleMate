import json
import sqlite3
from contextlib import contextmanager
from pathlib import Path


DB_PATH = Path(__file__).resolve().parent / "wardrobe.db"


@contextmanager
def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_db():
    with get_conn() as conn:
        cur = conn.cursor()

        # 1. tables first
        cur.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        )
        """)

        cur.execute("""
        CREATE TABLE IF NOT EXISTS shop_catalog (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            category TEXT NOT NULL,
            color TEXT,
            price REAL,
            currency TEXT NOT NULL DEFAULT 'RUB',
            url TEXT NOT NULL UNIQUE,
            image_url TEXT,
            source TEXT DEFAULT 'unknown',
            external_id TEXT,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        )
        """)

        columns = {row["name"] for row in cur.execute("PRAGMA table_info(shop_catalog)").fetchall()}
        if "currency" not in columns:
            cur.execute("ALTER TABLE shop_catalog ADD COLUMN currency TEXT NOT NULL DEFAULT 'RUB'")
        cur.execute("UPDATE shop_catalog SET currency = 'RUB' WHERE currency IS NULL OR trim(currency) = ''")
        cur.execute("UPDATE shop_catalog SET currency = 'EUR' WHERE source = 'zara'")

        cur.execute("""
        CREATE TABLE IF NOT EXISTS wardrobe_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            catalog_id INTEGER NOT NULL,
            added_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            is_active INTEGER NOT NULL DEFAULT 1,
            FOREIGN KEY (user_id) REFERENCES users(id),
            FOREIGN KEY (catalog_id) REFERENCES shop_catalog(id)
        )
        """)

        cur.execute("""
        CREATE TABLE IF NOT EXISTS outfit_generations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            occasion TEXT NOT NULL,
            style TEXT NOT NULL,
            score REAL,
            version INTEGER NOT NULL DEFAULT 1,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
        """)

        cur.execute("""
        CREATE TABLE IF NOT EXISTS outfit_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            outfit_id INTEGER NOT NULL,
            catalog_id INTEGER NOT NULL,
            role TEXT,
            FOREIGN KEY (outfit_id) REFERENCES outfit_generations(id),
            FOREIGN KEY (catalog_id) REFERENCES shop_catalog(id)
        )
        """)

        cur.execute("""
        CREATE TABLE IF NOT EXISTS wardrobe_versions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            version INTEGER NOT NULL,
            snapshot_json TEXT NOT NULL,
            comment TEXT,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
        """)

        # 2. indexes after tables
        cur.execute("CREATE INDEX IF NOT EXISTS idx_shop_catalog_category ON shop_catalog(category)")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_shop_catalog_color ON shop_catalog(color)")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_shop_catalog_source ON shop_catalog(source)")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_wardrobe_items_user_id ON wardrobe_items(user_id)")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_wardrobe_items_catalog_id ON wardrobe_items(catalog_id)")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_outfit_generations_user_id ON outfit_generations(user_id)")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_outfit_items_outfit_id ON outfit_items(outfit_id)")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_wardrobe_versions_user_id ON wardrobe_versions(user_id)")

        # anti-duplicates in wardrobe
        cur.execute("""
        CREATE UNIQUE INDEX IF NOT EXISTS idx_unique_active_wardrobe_item
        ON wardrobe_items(user_id, catalog_id, is_active)
        """)


def reset_db():
    if DB_PATH.exists():
        DB_PATH.unlink()
    init_db()


def save_to_shop_catalog(item):
    with get_conn() as conn:
        conn.execute("""
        INSERT OR IGNORE INTO shop_catalog
        (title, category, color, price, currency, url, image_url, source, external_id)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            item.get("title"),
            item.get("category"),
            item.get("color"),
            item.get("price"),
            item.get("currency", "RUB"),
            item.get("url"),
            item.get("image_url"),
            item.get("source", "unknown"),
            item.get("external_id")
        ))


def create_user(name):
    with get_conn() as conn:
        cur = conn.execute(
            "INSERT INTO users (name) VALUES (?)",
            (name,)
        )
        user_id = cur.lastrowid
        row = conn.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
        return dict(row)


def list_users():
    with get_conn() as conn:
        rows = conn.execute("SELECT * FROM users ORDER BY id").fetchall()
        return [dict(r) for r in rows]


def add_item_to_wardrobe(user_id, catalog_id):
    with get_conn() as conn:
        cur = conn.execute("""
        INSERT OR IGNORE INTO wardrobe_items (user_id, catalog_id, is_active)
        VALUES (?, ?, 1)
        """, (user_id, catalog_id))
        return cur.lastrowid


def remove_item_from_wardrobe(user_id, catalog_id):
    with get_conn() as conn:
        conn.execute("""
        UPDATE wardrobe_items
        SET is_active = 0
        WHERE user_id = ? AND catalog_id = ? AND is_active = 1
        """, (user_id, catalog_id))


def get_user_wardrobe(user_id):
    with get_conn() as conn:
        rows = conn.execute("""
        SELECT
            sc.id,
            sc.title,
            sc.category,
            sc.color,
            sc.price,
            sc.currency,
            sc.url,
            sc.image_url,
            sc.source,
            wi.added_at
        FROM wardrobe_items wi
        JOIN shop_catalog sc ON sc.id = wi.catalog_id
        WHERE wi.user_id = ? AND wi.is_active = 1
        ORDER BY wi.id DESC
        """, (user_id,)).fetchall()
        return [dict(r) for r in rows]


def create_wardrobe_snapshot(user_id, comment=""):
    wardrobe = get_user_wardrobe(user_id)

    with get_conn() as conn:
        row = conn.execute("""
        SELECT COALESCE(MAX(version), 0) + 1 AS next_version
        FROM wardrobe_versions
        WHERE user_id = ?
        """, (user_id,)).fetchone()

        version = row["next_version"]

        cur = conn.execute("""
        INSERT INTO wardrobe_versions (user_id, version, snapshot_json, comment)
        VALUES (?, ?, ?, ?)
        """, (
            user_id,
            version,
            json.dumps(wardrobe, ensure_ascii=False),
            comment
        ))

        return cur.lastrowid


def list_wardrobe_versions(user_id):
    with get_conn() as conn:
        rows = conn.execute("""
        SELECT id, user_id, version, comment, created_at
        FROM wardrobe_versions
        WHERE user_id = ?
        ORDER BY version DESC
        """, (user_id,)).fetchall()
        return [dict(r) for r in rows]


def create_outfit_generation(user_id, occasion, style, score, items):
    with get_conn() as conn:
        row = conn.execute("""
        SELECT COALESCE(MAX(version), 0) + 1 AS next_version
        FROM outfit_generations
        WHERE user_id = ?
        """, (user_id,)).fetchone()

        version = row["next_version"]

        cur = conn.execute("""
        INSERT INTO outfit_generations (user_id, occasion, style, score, version)
        VALUES (?, ?, ?, ?, ?)
        """, (user_id, occasion, style, score, version))

        outfit_id = cur.lastrowid

        for item in items:
            conn.execute("""
            INSERT INTO outfit_items (outfit_id, catalog_id, role)
            VALUES (?, ?, ?)
            """, (
                outfit_id,
                item["catalog_id"],
                item.get("role")
            ))

        return outfit_id
def get_outfit_history(user_id, limit=20):
    with get_conn() as conn:
        rows = conn.execute("""
        SELECT id, user_id, occasion, style, score, version, created_at
        FROM outfit_generations
        WHERE user_id = ?
        ORDER BY id DESC
        LIMIT ?
        """, (user_id, limit)).fetchall()
        return [dict(r) for r in rows]


def get_outfit_items(outfit_id):
    with get_conn() as conn:
        rows = conn.execute("""
        SELECT
            sc.id,
            sc.title,
            sc.category,
            sc.color,
            sc.price,
            sc.currency,
            sc.url,
            sc.image_url,
            sc.source,
            oi.role
        FROM outfit_items oi
        JOIN shop_catalog sc ON sc.id = oi.catalog_id
        WHERE oi.outfit_id = ?
        ORDER BY oi.id ASC
        """, (outfit_id,)).fetchall()
        return [dict(r) for r in rows]


def _build_catalog_where(category=None, source=None, query=None):
    where = []
    params = []

    if category:
        where.append("category = ?")
        params.append(category)

    if source:
        where.append("source = ?")
        params.append(source)

    if query:
        like_query = f"%{query.strip().lower()}%"
        where.append("""
        (
            lower(title) LIKE ?
            OR lower(category) LIKE ?
            OR lower(COALESCE(color, '')) LIKE ?
            OR lower(COALESCE(source, '')) LIKE ?
        )
        """)
        params.extend([like_query, like_query, like_query, like_query])

    return where, params


def count_catalog_items(category=None, source=None, query=None):
    with get_conn() as conn:
        where, params = _build_catalog_where(category=category, source=source, query=query)
        sql = "SELECT COUNT(*) AS total FROM shop_catalog"
        if where:
            sql += " WHERE " + " AND ".join(where)
        row = conn.execute(sql, params).fetchone()
        return row["total"]


def list_catalog_sources():
    with get_conn() as conn:
        rows = conn.execute("""
        SELECT source, COUNT(*) AS total
        FROM shop_catalog
        GROUP BY source
        ORDER BY total DESC, source ASC
        """).fetchall()
        return [dict(r) for r in rows]


def get_catalog_items(limit=None, offset=0, category=None, source=None, query=None):
    with get_conn() as conn:
        where, params = _build_catalog_where(category=category, source=source, query=query)
        sql = """
        SELECT *
        FROM shop_catalog
        """
        if where:
            sql += " WHERE " + " AND ".join(where)
        sql += " ORDER BY id DESC"

        if limit is not None:
            sql += " LIMIT ? OFFSET ?"
            params.extend([limit, offset])

        rows = conn.execute(sql, params).fetchall()
        return [dict(r) for r in rows]


if __name__ == "__main__":
    init_db()
    print("DB ready:", DB_PATH)
