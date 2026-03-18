from database.db import save_to_shop_catalog
from .zara_parser import get_zara_products
from .pavel_mazko import get_pavel_mazko_products
from .lime_parser import get_lime_products
from .sneakerhead import get_sneakerhead_products


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

    try:
        sneakerhead_products = get_sneakerhead_products()
        print("sneakerhead found:", len(sneakerhead_products))
        all_products.extend(sneakerhead_products)
    except Exception as e:
        print("sneakerhead parser error:", e)

    try:
        zara_products = get_zara_products()
        print("zara found:", len(zara_products))
        all_products.extend(zara_products)
    except Exception as e:
        print("zara parser error:", e)

    try:
        pavel_products = get_pavel_mazko_products()
        print("pavel_mazko found:", len(pavel_products))
        all_products.extend(pavel_products)
    except Exception as e:
        print("pavel_mazko parser error:", e)

    try:
        lime_products = get_lime_products()
        print("lime found:", len(lime_products))
        all_products.extend(lime_products)
    except Exception as e:
        print("lime parser error:", e)


    saved, skipped = save_products(all_products)

    print("total collected:", len(all_products))
    print("saved:", saved)
    print("skipped:", skipped)


if __name__ == "__main__":
    run_all_parsers()