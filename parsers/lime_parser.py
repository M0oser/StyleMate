from urllib.parse import urljoin

import requests

from .utils import normalize_price


BASE_URL = "https://limestore.com"
SECTION_SLUGS = [
    "men_view_all",
    "men_new",
    "outerwear",
    "trousers",
    "knitwear",
    "t_shirts",
    "sweatshirts",
    "all_shoes",
]

API_URL_TEMPLATE = "https://limestore.com/api/section/{slug}"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)",
    "Accept": "application/json, text/plain, */*",
    "Referer": "https://limestore.com/ru_ru/catalog/men_view_all",
    "Origin": "https://limestore.com",
    "Accept-Language": "ru-RU,ru;q=0.9,en;q=0.8",
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
    "boxer",
    "boxers",
    "боксер",
    "боксеров",
    "белье",
    "трусы",
    "briefs",
    "panties",
    "underwear",
    "носки",
    "socks",
    "ремень",
    "belt",
    "сумка",
    "bag",
    "парфюм",
    "perfume",
    "wallet",
    "кошелек",
    "шапка",
    "hat",
    "cap",
}


def detect_category(text: str) -> str:
    n = (text or "").lower()

    if any(word in n for word in BLOCKED_WORDS):
        return "other"

    if "джинс" in n or "jeans" in n:
        return "jeans"
    if "брюк" in n or "брюки" in n or "trouser" in n or "pants" in n:
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
    if "рубаш" in n or "shirt" in n or "polo" in n:
        return "shirt"
    if "худи" in n or "hoodie" in n:
        return "hoodie"
    if "свитер" in n or "кардиган" in n or "джемпер" in n or "knit" in n or "jumper" in n:
        return "sweater"

    if "пиджак" in n or "блейзер" in n or "жакет" in n or "jacket" in n or "blazer" in n:
        return "jacket"
    if "пальто" in n or "пуховик" in n or "плащ" in n or "coat" in n or "trench" in n:
        return "coat"

    return "other"


def normalize_color_name(color_name):
    if not color_name:
        return None

    c = color_name.lower().strip()

    mapping = {
        "черный": "black",
        "чёрный": "black",
        "black": "black",
        "white": "white",
        "белый": "white",
        "blue": "blue",
        "синий": "blue",
        "navy": "navy",
        "темно-синий": "navy",
        "grey": "gray",
        "gray": "gray",
        "серый": "gray",
        "beige": "beige",
        "бежевый": "beige",
        "brown": "brown",
        "коричневый": "brown",
        "red": "red",
        "красный": "red",
        "green": "green",
        "зеленый": "green",
        "зелёный": "green",
        "pink": "pink",
        "розовый": "pink",
    }

    return mapping.get(c, c)


def extract_items(payload):
    found = []

    def walk(obj):
        if isinstance(obj, dict):
            if obj.get("type") == "product" and isinstance(obj.get("entity"), dict):
                found.append(obj)
                return

            for value in obj.values():
                walk(value)

        elif isinstance(obj, list):
            for item in obj:
                walk(item)

    walk(payload)
    return found


def extract_product_url(entity):
    direct_url = entity.get("url") or entity.get("link")
    if direct_url:
        return urljoin(BASE_URL, direct_url)

    code = entity.get("code")
    article = entity.get("article")
    product_id = entity.get("id")

    if code:
        return f"{BASE_URL}/ru_ru/product/{code}"
    if article:
        return f"{BASE_URL}/ru_ru/product/{article}"
    if product_id:
        return f"{BASE_URL}/ru_ru/product/{product_id}"

    return None


def extract_model(entity):
    models = entity.get("models") or []
    if models and isinstance(models[0], dict):
        return models[0]

    return {}


def extract_image_url(entity, model):
    candidates = []

    for source in (model, entity):
        if not isinstance(source, dict):
            continue

        photo = source.get("photo") or {}
        if isinstance(photo, dict):
            candidates.append(photo.get("url"))

        medias = source.get("medias") or []
        if medias and isinstance(medias[0], dict):
            candidates.append(medias[0].get("url"))

        image = source.get("image") or {}
        if isinstance(image, dict):
            candidates.append(image.get("url"))

        gallery = source.get("gallery") or []
        if gallery and isinstance(gallery[0], dict):
            candidates.append(gallery[0].get("url"))

    for image_url in candidates:
        if image_url:
            return urljoin(BASE_URL, image_url)

    return None


def extract_color(entity, model):
    color_sources = [
        model.get("color"),
        entity.get("color"),
    ]

    for color_obj in color_sources:
        if isinstance(color_obj, dict):
            normalized = normalize_color_name(color_obj.get("name"))
            if normalized:
                return normalized

    return None


def extract_price(entity, model):
    price_candidates = []

    skus = model.get("skus") or []
    if skus and isinstance(skus[0], dict):
        sku = skus[0]
        price_candidates.extend([
            sku.get("price"),
            sku.get("current_price"),
            sku.get("old_price"),
        ])

    for source in (model, entity):
        if not isinstance(source, dict):
            continue
        price_candidates.extend([
            source.get("price"),
            source.get("current_price"),
            source.get("final_price"),
            source.get("min_price"),
        ])

    for candidate in price_candidates:
        price = normalize_price(candidate)
        if price is not None:
            return price

    return None


def normalize_product(raw):
    entity = raw.get("entity", {})
    if not entity:
        return None

    title = entity.get("name")
    if not title:
        return None

    category = detect_category(title)
    if category not in ALLOWED_CATEGORIES:
        return None

    first_model = extract_model(entity)
    color = extract_color(entity, first_model)
    image_url = extract_image_url(entity, first_model)
    price = extract_price(entity, first_model)

    url = extract_product_url(entity)

    external_id = entity.get("id") or entity.get("code") or entity.get("article")
    if not external_id:
        return None

    return {
        "title": title,
        "category": category,
        "color": color,
        "price": price,
        "currency": "RUB",
        "url": url,
        "image_url": image_url,
        "source": "lime",
        "external_id": str(external_id),
    }


def fetch_page(session: requests.Session, section_slug: str, page: int, page_size: int = 100):
    params = {
        "page": page,
        "page_size": page_size,
    }

    url = API_URL_TEMPLATE.format(slug=section_slug)
    headers = dict(HEADERS)
    headers["Referer"] = f"https://limestore.com/ru_ru/catalog/{section_slug}"

    response = session.get(url, headers=headers, params=params, timeout=30)
    response.raise_for_status()
    return response.json()


def get_section_products(session: requests.Session, section_slug: str):
    page = 1
    result = []
    seen = set()

    while True:
        payload = fetch_page(session=session, section_slug=section_slug, page=page, page_size=100)
        raw_items = extract_items(payload)

        if not raw_items:
            break

        added_this_page = 0

        for raw in raw_items:
            item = normalize_product(raw)
            if not item:
                continue

            if item["external_id"] in seen:
                continue

            seen.add(item["external_id"])
            result.append(item)
            added_this_page += 1

        if len(raw_items) < 100:
            break

        if added_this_page == 0:
            break

        page += 1

        if page > 100:
            break

    return result


def get_lime_products():
    result = []
    seen = set()
    with requests.Session() as session:
        for slug in SECTION_SLUGS:
            try:
                section_items = get_section_products(session=session, section_slug=slug)
                print(f"lime section {slug}: {len(section_items)}")

                for item in section_items:
                    if item["external_id"] in seen:
                        continue
                    seen.add(item["external_id"])
                    result.append(item)

            except Exception as e:
                print(f"lime section error {slug}:", e)

    return result
