import os
import sys


PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from database.db import save_to_shop_catalog
from parsers.pavel_mazko import get_pavel_mazko_products
from parsers.lime_parser import get_lime_products
from parsers.sela_parser import get_sela_products
from parsers.zara_parser import get_zara_products
from parsers.sneakerhead import get_sneakerhead_products

SOURCE_PARSERS = [
    ("sneakerhead", get_sneakerhead_products),
    ("pavel_mazko", get_pavel_mazko_products),
    ("zara", get_zara_products),
    ("lime", get_lime_products),
    ("sela", get_sela_products),
]


def save_products(products):
    saved = 0
    skipped = 0

    for item in products:
        try:
            save_to_shop_catalog(item)
            saved += 1
        except Exception as e:
            skipped += 1
            print("save error:", item.get("source"), item.get("title"), e)

    return saved, skipped


def collect_products_from_sources(source_parsers=None):
    all_products = []
    seen_urls = set()
    source_parsers = source_parsers or SOURCE_PARSERS

    def extend_unique(products):
        for item in products:
            url = item.get("url")
            if not url or url in seen_urls:
                continue
            seen_urls.add(url)
            all_products.append(item)

    for source_name, parser_fn in source_parsers:
        try:
            products = parser_fn()
            print(f"{source_name} found:", len(products))
            extend_unique(products)
        except Exception as e:
            print(f"{source_name} parser error:", e)

    return all_products


def run_all_parsers():
    all_products = collect_products_from_sources()

    saved, skipped = save_products(all_products)

    print("total collected:", len(all_products))
    print("saved:", saved)
    print("skipped:", skipped)


if __name__ == "__main__":
    run_all_parsers()
