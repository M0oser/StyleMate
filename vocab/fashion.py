from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class StoreDefinition:
    parser_key: str
    name: str
    base_url: str
    is_active: bool
    notes: str = ""


STORE_DEFINITIONS: tuple[StoreDefinition, ...] = (
    StoreDefinition("lime", "LIME", "https://lime-shop.com", True, "Live JSON API adapter"),
    StoreDefinition(
        "lime_sport",
        "LIME Sport Feed",
        "https://lime-shop.com",
        True,
        "Live sportswear search feed via /api/product/search",
    ),
    StoreDefinition("lamoda", "Lamoda", "https://www.lamoda.ru", False, "Protected by anti-bot; adapter intentionally disabled"),
    StoreDefinition("befree", "Befree", "https://befree.ru", False, "Pending stable API discovery"),
    StoreDefinition("zarina", "Zarina", "https://zarina.ru", False, "Pending stable API discovery"),
    StoreDefinition("gloria_jeans", "Gloria Jeans", "https://www.gloria-jeans.ru", False, "Pending stable API discovery"),
    StoreDefinition("ostin", "O'STIN", "https://ostin.com", False, "Pending stable API discovery"),
    StoreDefinition("sela", "Sela", "https://sela.ru", False, "Pending stable API discovery"),
    StoreDefinition("love_republic", "Love Republic", "https://loverepublic.ru", False, "Pending stable API discovery"),
    StoreDefinition("sportmaster", "Sportmaster", "https://www.sportmaster.ru", False, "Pending stable sportswear adapter"),
)


CATEGORY_ROLE_REFERENCE: tuple[tuple[str, str, str], ...] = (
    ("blouse", "top", "structured_top"),
    ("shirt", "top", "structured_top"),
    ("t_shirt", "top", "basic_top"),
    ("top", "top", "light_top"),
    ("hoodie", "top", "casual_top"),
    ("sweatshirt", "top", "casual_top"),
    ("track_jacket", "active_top", "performance_top"),
    ("knitwear", "top", "knit_top"),
    ("blazer", "outerwear", "tailored_outerwear"),
    ("jacket", "outerwear", "casual_outerwear"),
    ("coat", "outerwear", "warm_outerwear"),
    ("trench", "outerwear", "transitional_outerwear"),
    ("vest", "outerwear", "light_layer"),
    ("trousers", "bottom", "structured_bottom"),
    ("jeans", "bottom", "casual_bottom"),
    ("skirt", "bottom", "feminine_bottom"),
    ("shorts", "bottom", "summer_bottom"),
    ("sports_shorts", "active_bottom", "performance_bottom"),
    ("leggings", "active_bottom", "performance_bottom"),
    ("dress", "dress", "single_piece"),
    ("sneakers", "shoes", "casual_shoes"),
    ("running_shoes", "running_shoes", "performance_shoes"),
    ("boots", "shoes", "cold_weather_shoes"),
    ("loafers", "shoes", "smart_shoes"),
    ("heels", "shoes", "dressy_shoes"),
    ("flats", "shoes", "light_shoes"),
    ("active_top", "active_top", "performance_top"),
    ("active_bottom", "active_bottom", "performance_bottom"),
)


SUPPORTED_COMPLETION_ROLES = {
    "top",
    "bottom",
    "shoes",
    "outerwear",
    "dress",
    "active_top",
    "active_bottom",
    "running_shoes",
}

CONTROLLED_ROLE_SET = frozenset(SUPPORTED_COMPLETION_ROLES)
CONTROLLED_STYLE_PRIMARY = frozenset(
    {
        "activewear",
        "casual",
        "minimal",
        "smart casual",
        "street casual",
        "office casual",
        "feminine casual",
    }
)
CONTROLLED_FORMALITY = frozenset({"sport", "casual", "smart_casual", "smart"})
CONTROLLED_SEASON_TAGS = frozenset({"spring", "summer", "autumn", "winter", "all_season"})
CONTROLLED_WEATHER_TAGS = frozenset({"warm", "mild", "cold", "windy", "indoor"})
CONTROLLED_OCCASION_TAGS = frozenset(
    {
        "casual_daily",
        "weekend",
        "office",
        "date",
        "evening_casual",
        "travel",
        "sport",
        "gym",
        "running",
        "hiking_light",
    }
)
CONTROLLED_SCENARIO_TAGS = frozenset({"casual_daily", "office", "date", "street", "gym", "running", "outdoor_light"})
CONTROLLED_BODY_SIZE_RELEVANCE = frozenset(
    {
        "extended_size_range",
        "limited_size_range",
        "plus_size_friendly",
        "petite_friendly",
        "tall_friendly",
        "adult_numeric_range",
        "junior_numeric_range",
        "adult_shoe_range",
        "junior_shoe_range",
        "relaxed_fit_accessible",
    }
)
SPORT_COMPLETION_ROLES = frozenset({"active_top", "active_bottom", "running_shoes"})


STORE_SOURCE_PREFERENCE = {
    "lime": 0.86,
    "lime_sport": 0.9,
    "lamoda": 0.84,
    "befree": 0.82,
    "zarina": 0.82,
    "gloria_jeans": 0.79,
    "ostin": 0.81,
    "sela": 0.80,
    "love_republic": 0.83,
    "sportmaster": 0.85,
}


COMPLETION_SCENARIOS = {
    "casual_daily": {
        "label": "Casual Daily",
        "required_roles": ["top", "bottom", "shoes"],
        "optional_roles": ["outerwear"],
        "season_tags": ["spring", "summer", "autumn"],
        "occasion_tags": ["casual_daily", "weekend"],
        "weather_tags": ["warm", "mild"],
        "completion_roles": ["top", "bottom", "shoes", "outerwear"],
    },
    "office": {
        "label": "Office",
        "required_roles": ["top", "bottom", "shoes"],
        "optional_roles": ["outerwear"],
        "season_tags": ["all_season"],
        "occasion_tags": ["office"],
        "weather_tags": ["mild", "cold"],
        "completion_roles": ["top", "bottom", "shoes", "outerwear"],
    },
    "date": {
        "label": "Date",
        "required_roles": ["top", "bottom", "shoes"],
        "optional_roles": ["outerwear", "dress"],
        "season_tags": ["all_season"],
        "occasion_tags": ["date", "evening_casual"],
        "weather_tags": ["warm", "mild", "cold"],
        "completion_roles": ["top", "bottom", "shoes", "outerwear", "dress"],
    },
    "street": {
        "label": "Street Casual",
        "required_roles": ["top", "bottom", "shoes"],
        "optional_roles": ["outerwear"],
        "season_tags": ["all_season"],
        "occasion_tags": ["weekend", "travel"],
        "weather_tags": ["warm", "mild", "cold"],
        "completion_roles": ["top", "bottom", "shoes", "outerwear"],
    },
    "gym": {
        "label": "Gym",
        "required_roles": ["active_top", "active_bottom", "running_shoes"],
        "optional_roles": [],
        "season_tags": ["all_season"],
        "occasion_tags": ["gym", "sport"],
        "weather_tags": ["indoor", "mild"],
        "completion_roles": ["active_top", "active_bottom", "running_shoes"],
        "sport_context": "indoor_training",
    },
    "running": {
        "label": "Running",
        "required_roles": ["active_top", "active_bottom", "running_shoes"],
        "optional_roles": ["outerwear"],
        "season_tags": ["spring", "summer", "autumn"],
        "occasion_tags": ["running", "sport", "hiking_light"],
        "weather_tags": ["warm", "mild", "windy"],
        "completion_roles": ["active_top", "active_bottom", "running_shoes", "outerwear"],
        "sport_context": "urban_run",
    },
    "outdoor_light": {
        "label": "Outdoor Light",
        "required_roles": ["active_top", "active_bottom", "running_shoes"],
        "optional_roles": ["outerwear"],
        "season_tags": ["spring", "summer", "autumn"],
        "occasion_tags": ["sport", "travel", "hiking_light"],
        "weather_tags": ["mild", "windy", "cold"],
        "completion_roles": ["active_top", "active_bottom", "running_shoes", "outerwear"],
        "sport_context": "light_trail_or_walk",
    },
}


BLOCKED_CURATION_KEYWORDS = {
    "белье",
    "нижнее белье",
    "underwear",
    "lingerie",
    "bra",
    "brief",
    "thong",
    "socks",
    "носки",
    "колгот",
    "bag",
    "сумк",
    "belt",
    "ремень",
    "jewelry",
    "ring",
    "bracelet",
    "earring",
    "perfume",
    "парфюм",
    "fragrance",
    "swim",
    "купаль",
    "бикини",
    "homewear",
    "пижам",
    "плед",
    "phone",
    "кейс",
    "cap",
    "hat",
    "шапк",
    "шарф",
}
