import json
import re
from typing import Optional
from urllib.parse import urljoin

import requests

from .utils import build_retry_session, finalize_product, normalize_price


BASE_SITE = "https://www.zara.com"
HEADERS = {
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9,ru;q=0.8",
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)",
}

SECTION_CONFIGS = [
    {
        "url": "https://www.zara.com/tr/en/man-all-products-l7465.html",
        "gender": "male",
        "style": "casual",
        "category_hint": "men all products",
    },
    {
        "url": "https://www.zara.com/tr/en/man-tracksuits-l17522.html",
        "gender": "male",
        "style": "sport",
        "category_hint": "men sport tracksuits",
    },
    {
        "url": "https://www.zara.com/tr/en/zara-athleticz-l4651.html?v1=2436591",
        "gender": "male",
        "style": "sport",
        "category_hint": "men sport athleticz",
    },
    {
        "url": "https://www.zara.com/tr/en/woman-jackets-l1114.html",
        "gender": "female",
        "style": "casual",
        "category_hint": "women jackets",
    },
    {
        "url": "https://www.zara.com/tr/en/woman-tshirts-l1362.html",
        "gender": "female",
        "style": "casual",
        "category_hint": "women tshirts",
    },
    {
        "url": "https://www.zara.com/tr/en/woman-shirts-l1217.html",
        "gender": "female",
        "style": "casual",
        "category_hint": "women shirts blouses",
    },
    {
        "url": "https://www.zara.com/tr/en/woman-trousers-l1335.html",
        "gender": "female",
        "style": "casual",
        "category_hint": "women trousers",
    },
    {
        "url": "https://www.zara.com/tr/en/woman-dresses-l1066.html",
        "gender": "female",
        "style": "casual",
        "category_hint": "women dresses",
    },
    {
        "url": "https://www.zara.com/tr/en/woman-sweatshirts-l1320.html",
        "gender": "female",
        "style": "casual",
        "category_hint": "women sweatshirts hoodies",
    },
    {
        "url": "https://www.zara.com/tr/en/woman-cardigans-sweaters-l8322.html",
        "gender": "female",
        "style": "casual",
        "category_hint": "women cardigans sweaters",
    },
    {
        "url": "https://www.zara.com/tr/en/woman-tops-l1322.html",
        "gender": "female",
        "style": "casual",
        "category_hint": "women tops",
    },
]

INTERSTITIAL_TOKEN_RE = re.compile(r'"bm-verify":\s*"([^"]+)"')
INTERSTITIAL_POW_RE = re.compile(
    r"var i = (\d+);\s*var j = i \+ Number\(\"(\d+)\" \+ \"(\d+)\"\);"
)


def slugify_title(title: str) -> str:
    value = (title or "").lower().strip()
    value = value.replace("&", " and ")
    value = re.sub(r"['’]", "", value)
    value = re.sub(r"[^a-z0-9]+", "-", value)
    return re.sub(r"-+", "-", value).strip("-")


def solve_interstitial(session: requests.Session, url: str, html: str) -> str:
    token_match = INTERSTITIAL_TOKEN_RE.search(html)
    pow_match = INTERSTITIAL_POW_RE.search(html)
    if not token_match or not pow_match:
        return html

    base_value = int(pow_match.group(1))
    pow_value = base_value + int(pow_match.group(2) + pow_match.group(3))
    payload = {
        "bm-verify": token_match.group(1),
        "pow": pow_value,
    }

    verify_headers = dict(HEADERS)
    verify_headers["Content-Type"] = "application/json"
    verify_headers["Referer"] = url

    response = session.post(
        f"{BASE_SITE}/_sec/verify?provider=interstitial",
        headers=verify_headers,
        json=payload,
        timeout=75,
    )
    response.raise_for_status()

    data = response.json()
    next_url = urljoin(BASE_SITE, data.get("location") or url)
    retry_response = session.get(next_url, headers=HEADERS, timeout=75)
    retry_response.raise_for_status()
    return retry_response.text


def extract_assigned_json(text: str, name: str):
    marker = f"{name} = "
    start = text.find(marker)
    if start == -1:
        return None

    index = start + len(marker)
    if index >= len(text) or text[index] != "{":
        return None

    depth = 0
    in_string = False
    escaped = False

    for position in range(index, len(text)):
        char = text[position]
        if in_string:
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == '"':
                in_string = False
        else:
            if char == '"':
                in_string = True
            elif char == "{":
                depth += 1
            elif char == "}":
                depth -= 1
                if depth == 0:
                    return json.loads(text[index:position + 1])

    return None


def extract_payload(html: str):
    return extract_assigned_json(html, "window.zara.viewPayload")


def extract_image_url(component: dict) -> Optional[str]:
    detail = component.get("detail") or {}
    colors = detail.get("colors") or []

    for color in colors:
        for media in color.get("xmedia") or []:
            url = media.get("url")
            if url and "transparent-background" not in url and "loader.gif" not in url:
                return url.replace("{width}", "563")

    return None


def extract_price(component: dict):
    detail = component.get("detail") or {}
    colors = detail.get("colors") or []

    for color in colors:
        price = color.get("price")
        if price is not None:
            return float(price) / 100.0

    price = component.get("price")
    if price is not None:
        return float(price) / 100.0

    return None


def build_product_url(title: str, reference: str) -> Optional[str]:
    if not title or not reference:
        return None

    article = reference.split("-")[0].strip()
    if not article:
        return None

    slug = slugify_title(title)
    if not slug:
        return None

    return f"{BASE_SITE}/tr/en/{slug}-p{article}.html"


def iter_components(payload: dict):
    for group in payload.get("productGroups") or []:
        for element in group.get("elements") or []:
            for component in element.get("commercialComponents") or []:
                if component.get("type") == "Product" and component.get("name"):
                    yield component


def normalize_component(component: dict, config: dict):
    title = component.get("name")
    reference = component.get("reference")
    url = build_product_url(title, reference)
    if not url:
        return None

    return finalize_product(
        {
            "title": title,
            "price": extract_price(component),
            "currency": "TRY",
            "url": url,
            "image_url": extract_image_url(component),
            "source": "zara",
            "external_id": reference.split("-")[0].strip() if reference else None,
            "style": config["style"],
        },
        default_gender=config["gender"],
        default_style=config["style"],
        category_hint=config["category_hint"],
    )


def get_section_products(session: requests.Session, config: dict):
    response = session.get(config["url"], headers=HEADERS, timeout=75)
    response.raise_for_status()

    html = response.text
    if "/_sec/verify?provider=interstitial" in html:
        html = solve_interstitial(session, config["url"], html)

    payload = extract_payload(html)
    if not payload:
        print(f'zara section payload missing {config["category_hint"]}')
        return []

    result = []
    seen = set()

    for component in iter_components(payload):
        item = normalize_component(component, config)
        if not item or item["url"] in seen:
            continue
        seen.add(item["url"])
        result.append(item)

    print(f'zara section {config["category_hint"]}: found {len(result)}')
    return result


def _collect_zara_products(gender: Optional[str] = None):
    result = []
    seen = set()

    with build_retry_session(total_retries=3, backoff_factor=1.0) as session:
        for config in SECTION_CONFIGS:
            if gender and config["gender"] != gender:
                continue

            try:
                section_items = get_section_products(session, config)
            except Exception as e:
                print(f'zara section error {config["category_hint"]}:', e)
                continue

            for item in section_items:
                if item["url"] in seen:
                    continue
                seen.add(item["url"])
                result.append(item)

    return result


def get_zara_products():
    return _collect_zara_products()


def get_zara_men_products():
    return _collect_zara_products(gender="male")


def get_zara_women_products():
    return _collect_zara_products(gender="female")
