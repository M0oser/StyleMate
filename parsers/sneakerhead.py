from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

from .utils import extract_price_from_text


BASE_URL = "https://sneakerhead.ru"
CATALOG_URL = "https://sneakerhead.ru/men"

HEADERS = {
    "User-Agent": "Mozilla/5.0",
    "Accept-Language": "ru-RU,ru;q=0.9",
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

HARD_BLOCKED_WORDS = {
    "брелок", "брелки", "keychain",
    "значок", "значки", "pin",
    "бутылка", "bottle",
    "стакан", "cup", "mug",
    "браслет", "bracelet",
    "ожерелье", "necklace",
    "кольцо", "ring",
    "серьги", "earrings",
    "сумка", "bag",
    "рюкзак", "backpack",
    "кошелек", "wallet",
    "кепка", "cap",
    "шапка", "hat", "beanie",
    "носки", "socks",
    "белье", "underwear", "boxers", "briefs",
    "маска", "mask",
    "краска", "paint",
    "краситель",
    "уход", "care",
    "очиститель", "cleaner",
    "журнал", "magazine",
    "игрушка", "toy",
    "сертификат", "gift card",
    "ковёр", "ковер", "rug",
    "полотенце", "towel",
    "сланцы", "slides", "flip flops",
    "сандалии", "sandals",
}

def is_hard_blocked(title: str) -> bool:
    t = (title or "").lower()
    return any(word in t for word in HARD_BLOCKED_WORDS)


def detect_category(text: str) -> str:
    t = (text or "").lower()

    if "футбол" in t or "t-shirt" in t or "tee" in t:
        return "tshirt"
    if "рубаш" in t or "shirt" in t or "polo" in t:
        return "shirt"
    if "худи" in t or "hoodie" in t:
        return "hoodie"
    if "свитер" in t or "свитшот" in t or "jumper" in t or "sweatshirt" in t:
        return "sweater"

    if "шорт" in t:
        return "shorts"
    if "джинс" in t or "jeans" in t:
        return "jeans"
    if "брюк" in t or "брюки" in t or "pants" in t or "trouser" in t:
        return "trousers"

    if "жилет" in t or "куртк" in t or "jacket" in t:
        return "jacket"
    if "пальто" in t or "пуховик" in t or "coat" in t:
        return "coat"

    if "кроссов" in t or "кед" in t or " sneaker " in f" {t} ":
        return "sneakers"
    if "ботин" in t or "boot" in t:
        return "boots"
    if "туфл" in t or "shoe" in t or "loafer" in t:
        return "shoes"

    return "other"


def extract_price_from_card(card):
    price_nodes = card.find_all(
        lambda tag: tag.name in ("div", "span", "p")
        and tag.get("class")
        and any("price" in cls.lower() for cls in tag.get("class"))
    )

    candidates = []
    for node in price_nodes:
        text = node.get_text(" ", strip=True)
        price = extract_price_from_text(text)
        if price is not None:
            candidates.append(price)

    if candidates:
        return min(candidates)

    text_nodes = []
    for node in card.find_all(string=True):
        txt = str(node).strip()
        if "₽" in txt:
            text_nodes.append(txt)

    candidates = []
    for txt in text_nodes:
        price = extract_price_from_text(txt)
        if price is not None:
            candidates.append(price)

    if candidates:
        return min(candidates)

    return None


def extract_image(card):
    source = card.select_one("picture source")
    if source:
        srcset = source.get("srcset") or source.get("data-srcset")
        if srcset:
            first_src = srcset.split(",")[0].strip().split(" ")[0]
            if first_src:
                return urljoin(BASE_URL, first_src)

    noscript_img = card.select_one("noscript img")
    if noscript_img and noscript_img.get("src"):
        return urljoin(BASE_URL, noscript_img.get("src"))

    img = card.select_one("img")
    if img:
        src = img.get("data-src") or img.get("src")
        if src and "blank.gif" not in src:
            return urljoin(BASE_URL, src)

    image_wrap = card.select_one(".product-card__image")
    if image_wrap:
        style = image_wrap.get("style", "")
        marker = "url("
        if marker in style:
            raw_url = style.split(marker, 1)[1].split(")", 1)[0].strip("'\"")
            if raw_url:
                return urljoin(BASE_URL, raw_url)

    return None


def get_title_link(card):
    selectors = [
        "a.product-card__title-link",
        "a.product-card__link",
        "a.product-card_title",
        "h5 a",
        "h4 a",
        "h3 a",
    ]

    for selector in selectors:
        el = card.select_one(selector)
        if el and el.get("href") and el.get_text(" ", strip=True):
            return el

    for el in card.select("a[href]"):
        href = el.get("href")
        text = el.get_text(" ", strip=True)
        if href and text and href != "#":
            return el

    return None


def normalize_product(card):
    title_link = get_title_link(card)
    if not title_link:
        return None

    href = title_link.get("href")
    title = title_link.get_text(" ", strip=True)

    if not href or not title:
        return None

    if is_hard_blocked(title):
        return None

    category = detect_category(title)
    if category not in ALLOWED_CATEGORIES:
        return None

    price = extract_price_from_card(card)
    if price is None:
        return None

    return {
        "title": title,
        "category": category,
        "color": None,
        "price": price,
        "currency": "RUB",
        "url": urljoin(BASE_URL, href),
        "image_url": extract_image(card),
        "source": "sneakerhead",
        "external_id": href.strip("/"),
    }


def get_sneakerhead_products(max_pages=30):
    result = []
    seen = set()
    session = requests.Session()

    with session:
        for page in range(1, max_pages + 1):
            url = CATALOG_URL if page == 1 else f"{CATALOG_URL}/?PAGEN_2={page}"
            print(f"sneakerhead page {page}: {url}")

            response = session.get(url, headers=HEADERS, timeout=30)
            response.raise_for_status()

            soup = BeautifulSoup(response.text, "html.parser")
            cards = soup.select(".product-card")

            print(f"cards on page {page}: {len(cards)}")

            if not cards:
                break

            added = 0
            for card in cards:
                item = normalize_product(card)
                if not item:
                    continue

                if item["external_id"] in seen:
                    continue

                seen.add(item["external_id"])
                result.append(item)
                added += 1

            print(f"added from page {page}: {added}")

            if added == 0:
                break

    return result
