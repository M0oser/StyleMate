import re
from typing import Optional, Dict, Any
from db import init_db, search_products

# супер-простой парсер запроса (черновик)
COLORS = ["black", "white", "gray", "navy", "beige", "brown", "red", "blue", "green", "pink", "purple", "yellow", "orange"]
RU_COLOR_MAP = {
    "черн": "black",
    "бел": "white",
    "сер": "gray",
    "син": "blue",
    "темно-син": "navy",
    "беж": "beige",
    "корич": "brown",
    "красн": "red",
    "зел": "green",
    "роз": "pink",
    "фиол": "purple",
    "желт": "yellow",
    "оранж": "orange",
}

CATEGORIES = {
    "trench": ["тренч", "плащ"],
    "loafers": ["лоферы"],
    "jeans": ["джинс"],
    "coat": ["пальто"],
    "sneakers": ["кросс"],
    "boots": ["ботин", "сапог"],
}

def extract_color_ru(text: str) -> Optional[str]:
    t = text.lower()
    for k, v in RU_COLOR_MAP.items():
        if k in t:
            return v
    return None

def extract_category(text: str) -> Optional[str]:
    t = text.lower()
    for cat, keys in CATEGORIES.items():
        if any(k in t for k in keys):
            return cat
    return None

def extract_price_bounds(text: str):
    # "до 10000", "от 5000 до 12000"
    t = text.lower()
    min_p = None
    max_p = None

    m = re.search(r"до\s+(\d+)", t)
    if m:
        max_p = int(m.group(1))

    m = re.search(r"от\s+(\d+)", t)
    if m:
        min_p = int(m.group(1))

    m = re.search(r"от\s+(\d+)\s+до\s+(\d+)", t)
    if m:
        min_p = int(m.group(1))
        max_p = int(m.group(2))

    return min_p, max_p

def agent_shopper(user_request: str, topk: int = 3) -> Dict[str, Any]:
    """
    Возвращает: распарсенные параметры + найденные товары.
    """
    color = extract_color_ru(user_request)
    category = extract_category(user_request)
    price_min, price_max = extract_price_bounds(user_request)

    # Для MVP: query = весь запрос (или только ключевое слово)
    # Можно оставить весь запрос — но лучше вытащить сущность.
    query = user_request

    rows = search_products(
        query=query,
        category=category,
        color=color,
        price_min=price_min,
        price_max=price_max,
        limit=topk
    )

    items = []
    for (pid, source, title, price, url, image_url, cat, col) in rows:
        items.append({
            "id": pid,
            "source": source,
            "title": title,
            "price": price,
            "url": url,
            "image_url": image_url,
            "category": cat,
            "color": col
        })

    return {
        "parsed": {
            "query": query,
            "category": category,
            "color": color,
            "price_min": price_min,
            "price_max": price_max
        },
        "results": items
    }

def main():
    init_db()

    while True:
        q = input("\nЗапрос (или enter чтобы выйти): ").strip()
        if not q:
            break

        res = agent_shopper(q, topk=3)
        print("PARSED:", res["parsed"])
        if not res["results"]:
            print("Ничего не найдено. Попробуй проще или добавь товаров в базу.")
            continue

        print("\nTOP-3:")
        for i, it in enumerate(res["results"], 1):
            price = f"{it['price']} ₽" if it["price"] is not None else "—"
            print(f"{i}) {it['title']} | {price} | {it['url']}")

if __name__ == "__main__":
    main()