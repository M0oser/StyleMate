from database.db import count_catalog_items, get_catalog_items, list_catalog_sources


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


def get_catalog(limit=None, offset=0, category=None, source=None, query=None):
    if category and category not in ALLOWED_CATEGORIES:
        raise ValueError("Unsupported category")

    return get_catalog_items(
        limit=limit,
        offset=offset,
        category=category,
        source=source,
        query=query,
    )


def get_catalog_total(category=None, source=None, query=None):
    if category and category not in ALLOWED_CATEGORIES:
        raise ValueError("Unsupported category")
    return count_catalog_items(category=category, source=source, query=query)


def get_catalog_sources():
    return list_catalog_sources()


def search_catalog(items, query):
    if not query:
        return items

    q = query.lower().strip()

    return [
        item for item in items
        if q in item["title"].lower()
        or q in item["category"].lower()
        or (item.get("color") and q in item["color"].lower())
    ]
