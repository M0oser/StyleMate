import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(__file__), "wardrobe.db")


def init_db():

    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    cur.execute("""
    CREATE TABLE IF NOT EXISTS user_wardrobe(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT,
        category TEXT,
        color TEXT,
        image_url TEXT
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
        image_url TEXT
    )
    """)

    conn.commit()
    conn.close()


def save_to_shop_catalog(item_dict):

    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    cur.execute("""
    INSERT OR IGNORE INTO shop_catalog
    (title, category, color, price, url, image_url)
    VALUES (?, ?, ?, ?, ?, ?)
    """, (
        item_dict.get("title"),
        item_dict.get("category"),
        item_dict.get("color"),
        item_dict.get("price"),
        item_dict.get("url"),
        item_dict.get("image_url")
    ))

    conn.commit()
    conn.close()


if __name__ == "__main__":

    init_db()
    print("Database created (empty).")