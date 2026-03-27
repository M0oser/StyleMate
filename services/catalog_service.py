from database.db import count_catalog_items, get_catalog_items, list_catalog_sources


ALLOWED_CATEGORIES = {
    "tshirt",
    "top",
    "shirt",
    "hoodie",
    "sweater",
    "jeans",
    "trousers",
    "shorts",
    "skirt",
    "dress",
    "jacket",
    "coat",
    "sneakers",
    "boots",
    "shoes",
}


def get_catalog(
    limit=None,
    offset=0,
    category=None,
    source=None,
    query=None,
    gender=None,
    style=None,
    warmth=None,
    weather_tag=None,
    weather_profile=None,
    water_resistant=None,
    weather_rain=None,
    weather_wind=None,
    weather_snow=None,
    weather_heat=None,
    purpose_tag=None,
    usecase_tag=None,
    feature_tag=None,
    material_tag=None,
    subcategory=None,
    hooded=None,
    waterproof=None,
    windproof=None,
    insulated=None,
    technical=None,
    many_pockets=None,
    pocket_level=None,
):
    if category and category not in ALLOWED_CATEGORIES:
        raise ValueError("Unsupported category")

    return get_catalog_items(
        limit=limit,
        offset=offset,
        category=category,
        source=source,
        query=query,
        gender=gender,
        style=style,
        warmth=warmth,
        weather_tag=weather_tag,
        weather_profile=weather_profile,
        water_resistant=water_resistant,
        weather_rain=weather_rain,
        weather_wind=weather_wind,
        weather_snow=weather_snow,
        weather_heat=weather_heat,
        purpose_tag=purpose_tag,
        usecase_tag=usecase_tag,
        feature_tag=feature_tag,
        material_tag=material_tag,
        subcategory=subcategory,
        hooded=hooded,
        waterproof=waterproof,
        windproof=windproof,
        insulated=insulated,
        technical=technical,
        many_pockets=many_pockets,
        pocket_level=pocket_level,
    )


def get_catalog_total(
    category=None,
    source=None,
    query=None,
    gender=None,
    style=None,
    warmth=None,
    weather_tag=None,
    weather_profile=None,
    water_resistant=None,
    weather_rain=None,
    weather_wind=None,
    weather_snow=None,
    weather_heat=None,
    purpose_tag=None,
    usecase_tag=None,
    feature_tag=None,
    material_tag=None,
    subcategory=None,
    hooded=None,
    waterproof=None,
    windproof=None,
    insulated=None,
    technical=None,
    many_pockets=None,
    pocket_level=None,
):
    if category and category not in ALLOWED_CATEGORIES:
        raise ValueError("Unsupported category")
    return count_catalog_items(
        category=category,
        source=source,
        query=query,
        gender=gender,
        style=style,
        warmth=warmth,
        weather_tag=weather_tag,
        weather_profile=weather_profile,
        water_resistant=water_resistant,
        weather_rain=weather_rain,
        weather_wind=weather_wind,
        weather_snow=weather_snow,
        weather_heat=weather_heat,
        purpose_tag=purpose_tag,
        usecase_tag=usecase_tag,
        feature_tag=feature_tag,
        material_tag=material_tag,
        subcategory=subcategory,
        hooded=hooded,
        waterproof=waterproof,
        windproof=windproof,
        insulated=insulated,
        technical=technical,
        many_pockets=many_pockets,
        pocket_level=pocket_level,
    )


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
        or (item.get("weather_tags") and q in item["weather_tags"].lower())
        or (item.get("weather_profiles") and q in item["weather_profiles"].lower())
        or (item.get("warmth") and q in item["warmth"].lower())
        or (item.get("purpose_tags") and q in item["purpose_tags"].lower())
        or (item.get("subcategory") and q in item["subcategory"].lower())
        or (item.get("material_tags") and q in item["material_tags"].lower())
        or (item.get("fit_tags") and q in item["fit_tags"].lower())
        or (item.get("feature_tags") and q in item["feature_tags"].lower())
        or (item.get("usecase_tags") and q in item["usecase_tags"].lower())
    ]
