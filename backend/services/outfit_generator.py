import os
import sqlite3
import random
from dataclasses import dataclass
from typing import List, Optional, Dict, Tuple

NEUTRALS = {"black", "white", "gray", "navy", "beige", "brown"}
BRIGHTS = {"red", "yellow", "orange", "pink", "purple", "green", "blue"}

SCENARIOS = {
    "Офис": {
        "required_any": [["shirt","blazer"], ["trousers","pants","skirt"], ["loafers","shoes"]],
        "avoid": ["shorts","hoodie"],
        "outer_bias": ["blazer", "coat"]
    },
    "Свидание": {
        "required_any": [["tshirt","shirt","sweater","hoodie"], ["jeans","trousers","pants","skirt"]],
        "avoid": [],
        "outer_bias": ["jacket", "coat"]
    },
    "Прогулка в дождь": {
        "required_any": [["jacket","coat"], ["boots","sneakers"]],
        "avoid": ["loafers"],
        "outer_bias": ["coat", "jacket"]
    },
}

STYLES = {
    "Minimal": {"prefer_colors": ["black","white","gray","navy","beige"], "allow_bright_accents": 0},
    "Casual": {"prefer_colors": None, "allow_bright_accents": 1},
    "Street": {"prefer_colors": None, "allow_bright_accents": 2},
}

@dataclass
class WardrobeItem:
    id: int
    title: str
    price: Optional[float]
    url: str
    image_url: Optional[str]
    cat: str
    color: Optional[str]

def load_wardrobe_from_db(db_path: str = "database/wardrobe.db", limit: int = 200) -> List[WardrobeItem]:
    if not os.path.exists(db_path):
        db_path = "products.db"
        table_name = "products"
    else:
        table_name = "shop_catalog" 
        
    con = sqlite3.connect(db_path)
    cur = con.cursor()
    
    query = f"""
        SELECT id, title, price, url, image_url, category, color 
        FROM {table_name}
        WHERE category NOT IN ('laptops', 'smartphones', 'fragrances', 'skincare', 'groceries', 'home-decoration')
        AND category NOT LIKE '%watches%'
        AND category NOT LIKE '%jewellery%'
        AND category IS NOT NULL
        LIMIT ?
    """
    
    cur.execute(query, (limit,))
    rows = cur.fetchall()
    con.close()

    items = []
    for (pid, title, price, url, image_url, category, color) in rows:
        items.append(WardrobeItem(
            id=pid, 
            title=title, 
            price=price, 
            url=url, 
            image_url=image_url, 
            cat=category.lower() if category else 'unknown',
            color=color
        ))
    return items

def insert_user_wardrobe_item(title: str, category: str, color: str, image_url: str = None, db_path: str = "database/wardrobe.db"):
    """
    Сохраняет загруженную пользователем вещь в его личный гардероб (user_wardrobe).
    """
    if not os.path.exists(db_path):
        print(f"Ошибка: База {db_path} не найдена!")
        return False
        
    con = sqlite3.connect(db_path)
    cur = con.cursor()
    
    cur.execute("""
        INSERT INTO user_wardrobe (title, category, color, image_url)
        VALUES (?, ?, ?, ?)
    """, (title, category, color, image_url))
    
    con.commit()
    con.close()
    return True

# Остальные функции (color_score, pick_one, generate_outfits) можно оставить, если они есть в файле, 
# но для RAG они нам уже не нужны, так как логику собирает Qwen.
