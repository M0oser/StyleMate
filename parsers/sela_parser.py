import html
import json
import re
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

from .utils import extract_price_from_text, finalize_product


BASE_URL = "https://www.sela.ru"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)",
    "Accept-Language": "ru-RU,ru;q=0.9,en;q=0.8",
    "Referer": BASE_URL,
}

SECTION_CONFIGS = [
    {
        "name": "women",
        "url": f"{BASE_URL}/eshop/women/",
        "gender": "female",
        "style": "casual",
        "category_hint": "women",
    },
    {
        "name": "women_sport",
        "url": f"{BASE_URL}/eshop/women/sportivnaya-odezhda/",
        "gender": "female",
        "style": "sport",
        "category_hint": "women sport",
    },
    {
        "name": "men",
        "url": f"{BASE_URL}/eshop/men/",
        "gender": "male",
        "style": "casual",
        "category_hint": "men",
    },
]


def get_max_page(soup: BeautifulSoup) -> int:
    pages = {1}
    for link in soup.select('a[href*="?page="]'):
        href = link.get("href") or ""
        match = re.search(r"page=(\d+)", href)
        if match:
            pages.add(int(match.group(1)))
    return max(pages)


def parse_card(card, config):
    raw_payload = card.get("data-p")
    link = card.select_one("a[href]")
    if not raw_payload or not link:
        return None

    payload = json.loads(html.unescape(raw_payload))
    title = payload.get("name")
    url = urljoin(BASE_URL, link.get("href"))
    image_list = payload.get("image") or []
    image_url = image_list[0] if image_list else None

    price = payload.get("price")
    if price is None:
        price = extract_price_from_text(card.get_text(" ", strip=True))

    return finalize_product(
        {
            "title": title,
            "price": price,
            "currency": "RUB",
            "url": url,
            "image_url": image_url,
            "source": "sela",
            "external_id": str(payload.get("id") or payload.get("url") or "").strip() or None,
            "style": config["style"],
        },
        default_gender=config["gender"],
        default_style=config["style"],
        category_hint=f'{config["category_hint"]} {payload.get("category", "")}',
    )


def get_section_products(session: requests.Session, config: dict) -> list[dict]:
    result = []
    seen = set()

    first_response = session.get(config["url"], headers=HEADERS, timeout=30)
    first_response.raise_for_status()
    first_soup = BeautifulSoup(first_response.text, "html.parser")
    max_page = get_max_page(first_soup)

    for page in range(1, max_page + 1):
        page_url = config["url"] if page == 1 else f'{config["url"]}?page={page}'
        response = session.get(page_url, headers=HEADERS, timeout=30)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, "html.parser")
        cards = soup.select(".product-thumb[data-p]")

        if not cards:
            break

        added = 0
        for card in cards:
            item = parse_card(card, config)
            if not item or item["url"] in seen:
                continue
            seen.add(item["url"])
            result.append(item)
            added += 1

        print(f'sela section {config["name"]} page {page}: added {added}')

        if added == 0:
            break

    return result


def get_sela_products():
    result = []
    seen = set()

    with requests.Session() as session:
        for config in SECTION_CONFIGS:
            try:
                section_items = get_section_products(session=session, config=config)
                for item in section_items:
                    if item["url"] in seen:
                        continue
                    seen.add(item["url"])
                    result.append(item)
            except Exception as e:
                print(f'sela section error {config["name"]}:', e)

    return result
