import re
import time
from urllib.parse import quote_plus, urljoin

import requests

from .utils import normalize_price


URL = "https://www.zara.com/nl/en/category/2443335/products?ajax=true"

HEADERS = {
    "Referer": "https://www.zara.com/nl/en/man-all-products-l7465.html?v1=2443335",
    "Accept": "*/*",
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)",
}

BASE_SITE = "https://www.zara.com"
LOCALE_PATH = "nl/en"

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


def slugify_title(title):
    s = (title or "").lower().strip()
    s = s.replace("&", " and ")
    s = re.sub(r"['’]", "", s)
    s = re.sub(r"[^a-z0-9]+", "-", s)
    s = re.sub(r"-+", "-", s).strip("-")
    return s


def extract_article_from_reference(reference):
    if not reference:
        return None
    return reference.split("-")[0].strip() or None


def build_zara_url(title, reference):
    article = extract_article_from_reference(reference)
    slug = slugify_title(title)

    if article and slug:
        return "{}/{}/{}-p{}.html".format(BASE_SITE, LOCALE_PATH, slug, article)

    query = quote_plus("site:zara.com {}".format(title))
    return "https://www.google.com/search?q={}".format(query)


def detect_category(name):
    n = (name or "").lower()

    blocked_words = {
        "perfume", "fragrance", "parfum", "candle",
        "bag", "wallet", "belt", "cap", "hat",
        "glasses", "sunglasses", "watch", "ring",
        "necklace", "bracelet", "earring",
        "laptop", "phone", "tablet", "computer",
    }

    if any(word in n for word in blocked_words):
        return "other"

    if "jeans" in n:
        return "jeans"
    if "trouser" in n or "trousers" in n or "pants" in n:
        return "trousers"
    if "shorts" in n:
        return "shorts"
    if "sneaker" in n:
        return "sneakers"
    if "boot" in n:
        return "boots"
    if "shoe" in n or "loafer" in n:
        return "shoes"

    if "t-shirt" in n or "t shirt" in n or "tee" in n:
        return "tshirt"
    if "shirt" in n or "polo" in n:
        return "shirt"
    if "hoodie" in n:
        return "hoodie"
    if "jacket" in n or "blazer" in n or "gilet" in n or "vest" in n or "waistcoat" in n:
        return "jacket"
    if "coat" in n or "trench" in n or "puffer" in n:
        return "coat"
    if "sweater" in n or "jumper" in n or "knit" in n:
        return "sweater"

    return "other"


def normalize_color_name(color_name):
    if not color_name:
        return None

    c = color_name.lower().strip()

    mapping = {
        "black": "black",
        "white": "white",
        "blue": "blue",
        "navy": "navy",
        "grey": "gray",
        "gray": "gray",
        "charcoal": "gray",
        "beige": "beige",
        "brown": "brown",
        "chocolate": "brown",
        "red": "red",
        "green": "green",
        "pink": "pink",
        "khaki": "green",
        "ecru": "beige",
        "camel": "brown",
    }

    return mapping.get(c, c)


def extract_color_from_title(title):
    colors = [
        "black", "white", "blue", "navy", "gray", "grey",
        "beige", "brown", "red", "green", "pink",
        "charcoal", "chocolate", "khaki", "camel", "ecru"
    ]
    n = (title or "").lower()

    for c in colors:
        if c in n:
            return normalize_color_name(c)

    return None


def extract_color_from_product(product):
    detail = product.get("detail", {})
    colors = detail.get("colors", [])

    if colors and isinstance(colors, list):
        first_color = colors[0]
        color_name = first_color.get("name")
        if color_name:
            return normalize_color_name(color_name)

    return extract_color_from_title(product.get("name"))


def find_products(payload):
    products = []
    for group in payload.get("productGroups", []):
        for element in group.get("elements", []):
            products.append(element)
    return products


def walk_products(obj, found):
    if isinstance(obj, dict):
        if obj.get("type") == "Product" and obj.get("name") and obj.get("reference"):
            found.append(obj)
            return

        for value in obj.values():
            walk_products(value, found)

    elif isinstance(obj, list):
        for item in obj:
            walk_products(item, found)


def extract_real_product_nodes(elements):
    real_products = []
    seen = set()

    for el in elements:
        temp = []
        walk_products(el, temp)

        for product in temp:
            ref = product.get("reference")
            if not ref or ref in seen:
                continue
            seen.add(ref)
            real_products.append(product)

    return real_products


def extract_image_url(product):
    detail = product.get("detail", {})
    colors = detail.get("colors", [])

    if colors and isinstance(colors, list):
        first_color = colors[0]
        media = first_color.get("xmedia", [])
        if media and isinstance(media, list):
            first_media = media[0]
            if isinstance(first_media, dict):
                return first_media.get("url") or first_media.get("path")

    media = product.get("xmedia", [])
    if media and isinstance(media, list):
        first_media = media[0]
        if isinstance(first_media, dict):
            return first_media.get("url") or first_media.get("path")

    return None


def extract_price(product):
    candidates = [product.get("price"), product.get("oldPrice")]

    detail = product.get("detail", {})
    colors = detail.get("colors", [])
    if colors and isinstance(colors, list):
        first_color = colors[0]
        if isinstance(first_color, dict):
            candidates.extend([first_color.get("price"), first_color.get("oldPrice")])

    for candidate in candidates:
        if isinstance(candidate, int):
            return candidate / 100.0

        price = normalize_price(candidate)
        if price is not None:
            return price

    return None


def normalize_product(product):
    title = product.get("name")
    reference = product.get("reference")

    if not title or not reference:
        return None

    category = detect_category(title)
    if category not in ALLOWED_CATEGORIES:
        return None

    image_url = extract_image_url(product)
    if image_url:
        image_url = urljoin(BASE_SITE, image_url)

    color = extract_color_from_product(product)
    price = extract_price(product)
    url = build_zara_url(title, reference)

    return {
        "title": title,
        "category": category,
        "color": color,
        "price": price,
        "currency": "EUR",
        "url": url,
        "image_url": image_url,
        "source": "zara",
        "external_id": reference,
    }


def get_zara_products():
    with requests.Session() as session:
        session.get("https://www.zara.com", headers=HEADERS, timeout=30)
        time.sleep(2)

        response = session.get(URL, headers=HEADERS, timeout=30)
        response.raise_for_status()

        data = response.json()
        elements = find_products(data)
        products = extract_real_product_nodes(elements)

        result = []
        for product in products:
            item = normalize_product(product)
            if item:
                result.append(item)

        return result
