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
        external_id TEXT
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
    (title, category, color, price, url, image_url, currency, source, external_id)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
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
    ))

    conn.commit()
    conn.close()


if __name__ == "__main__":

    init_db()
    print("Database created (empty).")
