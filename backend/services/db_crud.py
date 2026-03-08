import sqlite3
from dataclasses import dataclass
from typing import Iterable, Optional, List, Tuple

DB_PATH = "products.db"

@dataclass
class Product:
    source: str
    title: str
    price: Optional[int]
    url: str
    image_url: Optional[str]
    category: Optional[str] = None
    color: Optional[str] = None


def init_db(db_path: str = DB_PATH) -> None:
    con = sqlite3.connect(db_path)
    cur = con.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS products (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            source TEXT NOT NULL,
            title TEXT NOT NULL,
            price INTEGER,
            url TEXT NOT NULL UNIQUE,
            image_url TEXT,
            category TEXT,
            color TEXT
        )
    """)
    cur.execute("CREATE INDEX IF NOT EXISTS idx_products_title ON products(title)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_products_category ON products(category)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_products_color ON products(color)")
    con.commit()
    con.close()


def upsert_products(products: Iterable[Product], db_path: str = DB_PATH) -> int:
    con = sqlite3.connect(db_path)
    cur = con.cursor()
    inserted = 0
    for p in products:
        try:
            cur.execute("""
                INSERT OR IGNORE INTO products
                (source, title, price, url, image_url, category, color)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (p.source, p.title, p.price, p.url, p.image_url, p.category, p.color))
            inserted += cur.rowcount
        except sqlite3.Error:
            pass
    con.commit()
    con.close()
    return inserted


def search_products(
    query: str,
    category: Optional[str] = None,
    color: Optional[str] = None,
    price_min: Optional[int] = None,
    price_max: Optional[int] = None,
    limit: int = 3,
    db_path: str = DB_PATH
) -> List[Tuple]:
    con = sqlite3.connect(db_path)
    cur = con.cursor()

    q = f"%{query.lower()}%"
    where = ["LOWER(title) LIKE ?"]
    params = [q]

    if category:
        where.append("LOWER(category) = LOWER(?)")
        params.append(category)

    if color:
        where.append("LOWER(color) = LOWER(?)")
        params.append(color)

    if price_min is not None:
        where.append("price >= ?")
        params.append(price_min)

    if price_max is not None:
        where.append("price <= ?")
        params.append(price_max)

    sql = f"""
        SELECT id, source, title, price, url, image_url, category, color
        FROM products
        WHERE {' AND '.join(where)}
        ORDER BY
            CASE WHEN price IS NULL THEN 1 ELSE 0 END,
            price ASC
        LIMIT ?
    """
    params.append(limit)

    cur.execute(sql, params)
    rows = cur.fetchall()
    con.close()
    return rows