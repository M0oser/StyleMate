import re
import time
import requests
from urllib.parse import quote_plus
from typing import Optional

from database.db import save_to_shop_catalog

ALLOWED_CATEGORIES = {
    "tshirt",
    "shirt",
    "hoodie",
    "sweater",
    "jeans",
    "trousers",
    "shorts",
    "jacket",
    "coat",
    "sneakers",
    "boots",
    "shoes",
}

URL = "https://www.zara.com/nl/en/category/2443335/products?ajax=true"

HEADERS = {
    "Referer": "https://www.zara.com/nl/en/man-all-products-l7465.html?v1=2443335",
    "Accept": "*/*",
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)",
}

BASE_SITE = "https://www.zara.com"
LOCALE_PATH = "nl/en"

def slugify_title(title: str) -> str:
    s = (title or "").lower().strip()
    s = s.replace("&", " and ")
    s = re.sub(r"['’]", "", s)
    s = re.sub(r"[^a-z0-9]+", "-", s)
    s = re.sub(r"-+", "-", s).strip("-")
    return s

def extract_article_from_reference(reference: Optional[str]) -> Optional[str]:
    """
    '04302212-V2026' -> '04302212'
    """
    if not reference:
        return None
    return reference.split("-")[0].strip() or None

def build_zara_url(title: str, reference: Optional[str]) -> str:
    """
    Пытаемся собрать реальную карточку Zara.
    Формат:
    https://www.zara.com/nl/en/<slug>-p<article>.html

    Если reference нет, fallback на Google site search.
    """
    article = extract_article_from_reference(reference)
    slug = slugify_title(title)

    if article and slug:
        return f"{BASE_SITE}/{LOCALE_PATH}/{slug}-p{article}.html"

    # fallback: рабочая ссылка на поиск в Google по Zara
    query = quote_plus(f"site:zara.com {title}")
    return f"https://www.google.com/search?q={query}"

def detect_category(name: str) -> str:
    n = (name or "").lower()

    if "t-shirt" in n or "t shirt" in n or "tee" in n:
        return "tshirt"
    if "shirt" in n or "polo" in n:
        return "shirt"
    if "hoodie" in n:
        return "hoodie"
    if "sweater" in n or "jumper" in n or "knit" in n:
        return "sweater"
    if "jeans" in n:
        return "jeans"
    if "trouser" in n or "pants" in n:
        return "trousers"
    if "shorts" in n:
        return "shorts"
    if "jacket" in n or "blazer" in n or "gilet" in n or "vest" in n:
        return "jacket"
    if "coat" in n or "trench" in n or "puffer" in n:
        return "coat"
    if "sneaker" in n:
        return "sneakers"
    if "boot" in n:
        return "boots"
    if "shoe" in n:
        return "shoes"

    return "other"

def extract_color(name: str) -> Optional[str]:
    colors = [
        "black", "white", "blue", "navy", "gray", "grey",
        "beige", "brown", "red", "green", "pink",
        "charcoal", "chocolate"
    ]
    n = (name or "").lower()

    for c in colors:
        if c in n:
            if c == "grey":
                return "gray"
            if c == "charcoal":
                return "gray"
            if c == "chocolate":
                return "brown"
            return c

    return None

def find_products(payload: dict) -> list:
    products = []
    for group in payload.get("productGroups", []):
        for element in group.get("elements", []):
            products.append(element)
    return products

def walk_products(obj, found: list):
    if isinstance(obj, dict):
        if obj.get("type") == "Product" and obj.get("name") and obj.get("reference"):
            found.append(obj)
            return

        for value in obj.values():
            walk_products(value, found)

    elif isinstance(obj, list):
        for item in obj:
            walk_products(item, found)

def extract_real_product_nodes(elements: list) -> list:
    real_products = []
    seen = set()

    for el in elements:
        temp = []
        walk_products(el, temp)

        for p in temp:
            ref = p.get("reference")
            if not ref or ref in seen:
                continue
            seen.add(ref)
            real_products.append(p)

    return real_products

def normalize_product(p: dict) -> Optional[dict]:
    title = p.get("name")
    reference = p.get("reference")
    price = p.get("price")

    if not title or not reference:
        return None

    if isinstance(price, int):
        price = price / 100

    category = detect_category(title)

    if category not in ALLOWED_CATEGORIES:
        return None

    url = build_zara_url(title, reference)
    image_url = None

    detail = p.get("detail", {})
    colors = detail.get("colors", [])

    if colors and isinstance(colors, list):
        first_color = colors[0]
        media = first_color.get("xmedia", [])
        if media and isinstance(media, list):
            first_media = media[0]
            if isinstance(first_media, dict):
                image_url = first_media.get("url")

    if not image_url:
        media = p.get("xmedia", [])
        if media and isinstance(media, list):
            first_media = media[0]
            if isinstance(first_media, dict):
                image_url = first_media.get("url")

    return {
        "title": title,
        "category": category,
        "color": extract_color(title),
        "price": price,
        "url": url,
        "image_url": image_url,
    }

def run_parser():
    session = requests.Session()

    print("getting cookies...")
    session.get("https://www.zara.com", headers=HEADERS)
    time.sleep(2)

    response = session.get(URL, headers=HEADERS)

    print("status:", response.status_code)

    if response.status_code != 200:
        print(response.text[:500])
        return

    data = response.json()

    print("top-level keys:", list(data.keys()))

    elements = find_products(data)
    print("raw elements found:", len(elements))

    products = extract_real_product_nodes(elements)
    print("real products found:", len(products))

    saved = 0

    for i, product in enumerate(products):
        item = normalize_product(product)

        if i < 3:
            print("DEBUG:", item)

        if not item:
            continue

        save_to_shop_catalog(item)
        saved += 1
        time.sleep(0.05)

    print("saved total:", saved)

if __name__ == "__main__":
    run_parser()
