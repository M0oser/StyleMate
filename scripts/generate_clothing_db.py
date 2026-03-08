import sqlite3
import random

DB_PATH = "products.db"

categories = {
    "tshirt": ["T-Shirt", "Oversized T-Shirt", "Basic Tee"],
    "shirt": ["Oxford Shirt", "Linen Shirt", "Casual Shirt"],
    "hoodie": ["Hoodie", "Zip Hoodie"],
    "sweater": ["Sweater", "Wool Sweater"],
    "jeans": ["Slim Jeans", "Regular Jeans", "Denim Jeans"],
    "trousers": ["Classic Trousers", "Chinos"],
    "pants": ["Cargo Pants"],
    "shorts": ["Summer Shorts"],
    "skirt": ["Mini Skirt", "Midi Skirt"],
    "sneakers": ["Sneakers", "Running Sneakers"],
    "boots": ["Leather Boots", "Chelsea Boots"],
    "loafers": ["Loafers"],
    "shoes": ["Formal Shoes", "Derby Shoes"],
    "jacket": ["Bomber Jacket", "Denim Jacket"],
    "coat": ["Coat", "Trench Coat"],
    "blazer": ["Blazer"]
}

colors = [
    "Black","White","Gray","Blue","Navy",
    "Beige","Brown","Red","Green"
]

brands = [
    "Nike","Adidas","Zara","H&M","Uniqlo",
    "Levis","Puma","Arket","COS","Massimo Dutti"
]


def generate_item(i):
    cat = random.choice(list(categories.keys()))
    name = random.choice(categories[cat])
    color = random.choice(colors)
    brand = random.choice(brands)

    title = f"{brand} {color} {name}"
    price = random.randint(30, 300)

    return {
        "title": title,
        "price": price,
        "url": f"https://store.example/item/{i}",
        "image_url": None,
        "category": cat,
        "color": color.lower()
    }


def main():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    cur.execute("""
    CREATE TABLE IF NOT EXISTS products (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        source TEXT,
        title TEXT,
        price INTEGER,
        url TEXT UNIQUE,
        image_url TEXT,
        category TEXT,
        color TEXT
    )
    """)

    inserted = 0

    for i in range(500):
        item = generate_item(i)

        cur.execute("""
        INSERT OR IGNORE INTO products
        (source,title,price,url,image_url,category,color)
        VALUES (?,?,?,?,?,?,?)
        """, (
            "generated",
            item["title"],
            item["price"],
            item["url"],
            item["image_url"],
            item["category"],
            item["color"]
        ))

        inserted += 1

    conn.commit()
    conn.close()

    print("Inserted items:", inserted)


if __name__ == "__main__":
    main()