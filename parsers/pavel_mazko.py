import re
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

from .utils import extract_price_from_text


BASE_URL = "https://pavelmazko.com"
CATALOG_URL = "https://pavelmazko.com/catalog"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)",
    "Accept-Language": "ru-RU,ru;q=0.9,en;q=0.8",
    "Referer": BASE_URL,
}

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

BLOCKED_WORDS = {
    "сумка",
    "bag",
    "ремень",
    "belt",
    "кошелек",
    "wallet",
    "шапка",
    "hat",
    "cap",
    "носки",
    "socks",
    "белье",
    "underwear",
    "парфюм",
    "perfume",
}


def detect_category(text: str) -> str:
    n = (text or "").lower()

    if any(word in n for word in BLOCKED_WORDS):
        return "other"

    if "джинс" in n or "jeans" in n:
        return "jeans"
    if "брюк" in n or "брюки" in n or "штаны" in n or "trouser" in n or "pants" in n:
        return "trousers"
    if "шорт" in n or "short" in n:
        return "shorts"

    if "кроссов" in n or "sneaker" in n:
        return "sneakers"
    if "ботин" in n or "boot" in n:
        return "boots"
    if "туфл" in n or "лофер" in n or "shoe" in n or "loafer" in n:
        return "shoes"

    if "футбол" in n or "майка" in n or "t-shirt" in n or "t shirt" in n or "tee" in n:
        return "tshirt"
    if "рубаш" in n or "лонгслив" in n or "гольф" in n or "shirt" in n or "polo" in n:
        return "shirt"
    if "худи" in n or "hoodie" in n:
        return "hoodie"
    if "свитер" in n or "свитшот" in n or "джемпер" in n or "knit" in n or "jumper" in n:
        return "sweater"

    if "жакет" in n or "пиджак" in n or "бомбер" in n or "куртк" in n or "jacket" in n or "blazer" in n:
        return "jacket"
    if "пальто" in n or "плащ" in n or "тренч" in n or "coat" in n or "trench" in n:
        return "coat"

    return "other"


def extract_image_url(link_el):
    images = link_el.select("img")
    for image in images:
        srcset = image.get("srcset")
        if srcset:
            first_src = srcset.split(",")[0].strip().split(" ")[0]
            if first_src:
                return urljoin(BASE_URL, first_src)

        src = image.get("src")
        if src:
            return urljoin(BASE_URL, src)

    return None


def extract_title(link_el):
    title_parts = []

    type_node = link_el.select_one(".product-item__title h4")
    name_node = link_el.select_one(".product-item__title h3")

    if type_node:
        title_parts.append(type_node.get_text(" ", strip=True))
    if name_node:
        title_parts.append(name_node.get_text(" ", strip=True))

    if title_parts:
        return " ".join(part for part in title_parts if part)

    fallback = " ".join(link_el.stripped_strings).strip()
    fallback = re.sub(r"₽\s*[\d\.\s,]+", "", fallback).strip()
    return re.sub(r"\s+", " ", fallback)


def normalize_product(link_el):
    text = " ".join(link_el.stripped_strings).strip()
    href = link_el.get("href")
    title = extract_title(link_el)

    if not text or not href or not title:
        return None

    price = extract_price_from_text(text)
    if price is None:
        return None

    category = detect_category(title)
    if category not in ALLOWED_CATEGORIES:
        return None

    url = urljoin(BASE_URL, href)
    external_id = href.strip("/").split("/")[-1]

    return {
        "title": title,
        "category": category,
        "color": None,
        "price": price,
        "currency": "RUB",
        "url": url,
        "image_url": extract_image_url(link_el),
        "source": "pavel_mazko",
        "external_id": external_id,
    }


def get_pavel_mazko_products():
    with requests.Session() as session:
        response = session.get(CATALOG_URL, headers=HEADERS, timeout=30)
        response.raise_for_status()

        soup = BeautifulSoup(response.text, "html.parser")

        result = []
        seen = set()

        for link_el in soup.select('a[href^="/catalog/"]'):
            href = link_el.get("href")

            if not href or href == "/catalog" or href in seen:
                continue

            item = normalize_product(link_el)
            if not item:
                continue

            seen.add(href)
            result.append(item)

        return result
