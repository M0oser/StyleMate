import re
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

from .utils import build_retry_session, extract_price_from_text, finalize_product


BASE_URL = "https://pavelmazko.com"
CATALOG_URL = "https://pavelmazko.com/catalog"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)",
    "Accept-Language": "ru-RU,ru;q=0.9,en;q=0.8",
    "Referer": BASE_URL,
}


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

    url = urljoin(BASE_URL, href)
    external_id = href.strip("/").split("/")[-1]

    return finalize_product({
        "title": title,
        "color": None,
        "price": price,
        "currency": "RUB",
        "url": url,
        "image_url": extract_image_url(link_el),
        "source": "pavel_mazko",
        "external_id": external_id,
    }, default_gender="male", default_style="casual", category_hint="men")


def get_pavel_mazko_products():
    with build_retry_session() as session:
        response = session.get(CATALOG_URL, headers=HEADERS, timeout=75)
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
