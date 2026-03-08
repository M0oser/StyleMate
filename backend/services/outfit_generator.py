import os
import sqlite3
import random
from dataclasses import dataclass
from typing import List, Optional, Dict, Tuple

# === Правила и константы Зи ===
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
    price: Optional[int]
    url: str
    image_url: Optional[str]
    cat: str
    color: Optional[str]

# === Функции ===
def load_wardrobe_from_db(db_path: str = "products.db", limit: int = 2000) -> List[WardrobeItem]:
    if not os.path.exists(db_path):
        return []
    con = sqlite3.connect(db_path)
    cur = con.cursor()
    cur.execute("SELECT id, title, price, url, image_url, category, color FROM products LIMIT ?", (limit,))
    rows = cur.fetchall()
    con.close()

    items = []
    for (pid, title, price, url, image_url, category, color) in rows:
        # Для простоты MVP считаем, что категория и цвет уже нормализованы в базе
        items.append(WardrobeItem(id=pid, title=title, price=price, url=url, image_url=image_url, cat=category, color=color))
    return items

def pick_one(pool: List[WardrobeItem], cats: List[str]) -> Optional[WardrobeItem]:
    candidates = [x for x in pool if x.cat in cats]
    return random.choice(candidates) if candidates else None

def color_score(colors: List[Optional[str]], style_key: str) -> int:
    colors = [c for c in colors if c]
    if not colors: return 0
    rule = STYLES[style_key]
    bright_count = sum(1 for c in colors if c in BRIGHTS and c != "navy")
    neutral_count = sum(1 for c in colors if c in NEUTRALS)
    score = neutral_count * 2 - max(0, bright_count - rule["allow_bright_accents"]) * 3
    if rule["prefer_colors"]:
        score += sum(1 for c in colors if c in rule["prefer_colors"])
    return score

def generate_outfits(pool: List[WardrobeItem], scenario: str, style: str, k: int = 3) -> List[Tuple[int, List[WardrobeItem]]]:
    rules = SCENARIOS[scenario]
    results = []

    for _ in range(300):
        outfit = []
        top = pick_one(pool, ["tshirt","shirt","hoodie","sweater"])
        bottom = pick_one(pool, ["jeans","trousers","pants","shorts","skirt"])
        shoes = pick_one(pool, ["sneakers","boots","loafers","shoes"])

        if top: outfit.append(top)
        if bottom: outfit.append(bottom)
        if shoes: outfit.append(shoes)

        outer = pick_one(pool, ["jacket","coat","blazer"])
        if scenario in ("Офис", "Прогулка в дождь") and outer:
            outfit.append(outer)
        elif outer and random.random() < 0.35:
            outfit.append(outer)

        if len(outfit) < 3: continue
        if any(it.cat in rules["avoid"] for it in outfit): continue

        ok = True
        for group in rules["required_any"]:
            if not any(it.cat in group for it in outfit):
                ok = False; break
        if not ok: continue

        score = color_score([it.color for it in outfit], style) + len(set(it.cat for it in outfit))
        results.append((score, outfit))

    seen = set()
    uniq = []
    for score, outfit in sorted(results, key=lambda x: x[0], reverse=True):
        key = tuple(sorted(it.id for it in outfit))
        if key in seen: continue
        seen.add(key)
        uniq.append((score, outfit))
        if len(uniq) >= k: break
    return uniq
