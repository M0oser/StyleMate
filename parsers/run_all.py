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


def run_all_parsers():
    all_products = []
    seen_urls = set()

    def extend_unique(products):
        for item in products:
            url = item.get("url")
            if not url or url in seen_urls:
                continue
            seen_urls.add(url)
            all_products.append(item)

    try:
        sneakerhead_products = get_sneakerhead_products()
        print("sneakerhead found:", len(sneakerhead_products))
        extend_unique(sneakerhead_products)
    except Exception as e:
        print("sneakerhead parser error:", e)

    try:
        pavel_products = get_pavel_mazko_products()
        print("pavel_mazko found:", len(pavel_products))
        extend_unique(pavel_products)
    except Exception as e:
        print("pavel_mazko parser error:", e)

    try:
        zara_products = get_zara_products()
        print("zara found:", len(zara_products))
        extend_unique(zara_products)
    except Exception as e:
        print("zara parser error:", e)

    try:
        lime_products = get_lime_products()
        print("lime found:", len(lime_products))
        extend_unique(lime_products)
    except Exception as e:
        print("lime parser error:", e)

    try:
        sela_products = get_sela_products()
        print("sela found:", len(sela_products))
        extend_unique(sela_products)
    except Exception as e:
        print("sela parser error:", e)

    saved, skipped = save_products(all_products)

    print("total collected:", len(all_products))
    print("saved:", saved)
    print("skipped:", skipped)


if __name__ == "__main__":
    run_all_parsers()
