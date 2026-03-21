import re
from typing import Any, Dict, Optional

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

PRICE_PATTERNS = [
    r"\d[\d\s\xa0\u202f.,]*\s*₽",
    r"₽\s*\d[\d\s\xa0\u202f.,]*",
    r"\d[\d\s\xa0\u202f.,]*\s*руб\.?",
    r"\d[\d\s\xa0\u202f.,]*\s*р\.?",
    r"\d[\d\s\xa0\u202f.,]*\s*TL",
    r"\d[\d\s\xa0\u202f.,]*\s*TRY",
    r"\d[\d\s\xa0\u202f.,]*\s*€",
    r"€\s*\d[\d\s\xa0\u202f.,]*",
    r"\d[\d\s\xa0\u202f.,]*\s*\$",
    r"\$\s*\d[\d\s\xa0\u202f.,]*",
]

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

HARD_BLOCKED_WORDS = {
    "аксессуар",
    "белье",
    "берет",
    "бижутер",
    "браслет",
    "брелок",
    "бюстгальтер",
    "вареж",
    "галстук",
    "головной убор",
    "колгот",
    "кольцо",
    "комплект белья",
    "кошелек",
    "космет",
    "крем",
    "купаль",
    "маска",
    "набор носков",
    "носки",
    "ожерель",
    "очки",
    "парфюм",
    "перчат",
    "плавки",
    "платок",
    "ремень",
    "рюкзак",
    "сабо",
    "сандали",
    "серьг",
    "сланц",
    "сумка",
    "тапочки",
    "трус",
    "украшен",
    "шапк",
    "шарф",
    "шлепан",
    "gift card",
    "bag",
    "backpack",
    "belt",
    "beanie",
    "bikini",
    "boxer",
    "boxers",
    "briefs",
    "bracelet",
    "cap",
    "cosmetic",
    "earring",
    "flip flops",
    "fragrance",
    "gift certificate",
    "giftcard",
    "glasses",
    "hat",
    "jewelry",
    "keychain",
    "lingerie",
    "mask",
    "necklace",
    "panties",
    "perfume",
    "ring",
    "sandals",
    "scarf",
    "slides",
    "slippers",
    "socks",
    "sunglasses",
    "swim",
    "underwear",
    "wallet",
}

SPORT_KEYWORDS = {
    "active",
    "athletic",
    "basketball",
    "fitness",
    "gym",
    "jogger",
    "jogging",
    "outdoor",
    "performance",
    "pilates",
    "running",
    "sport",
    "sportiv",
    "sporty",
    "sweatpant",
    "technical",
    "tennis",
    "training",
    "trail",
    "workout",
    "йога",
    "бег",
    "джоггер",
    "спортив",
    "трениров",
    "фитнес",
}

HOT_WEATHER_KEYWORDS = {
    "breathable",
    "lightweight",
    "linen",
    "summer",
    "воздуш",
    "дышащ",
    "льня",
    "летн",
    "лёгк",
}

COLD_WEATHER_KEYWORDS = {
    "down",
    "fleece",
    "insulated",
    "merino",
    "padded",
    "puffer",
    "quilted",
    "thermal",
    "warm",
    "wool",
    "утепл",
    "пух",
    "стеган",
    "тепл",
    "термо",
    "флис",
    "шерст",
}

RAIN_KEYWORDS = {
    "dry",
    "gore",
    "membrane",
    "rain",
    "rubber",
    "shell",
    "water repellent",
    "water-repellent",
    "waterproof",
    "weatherproof",
    "влаг",
    "дожд",
    "мембран",
    "непромока",
    "прорезин",
    "водоотталк",
    "водонепрониц",
}

WIND_KEYWORDS = {
    "anorak",
    "hood",
    "shell",
    "wind",
    "ветро",
    "капюшон",
    "шторм",
}

SNOW_KEYWORDS = {
    "apres",
    "cold",
    "down",
    "fleece",
    "insulated",
    "puffer",
    "ski",
    "snow",
    "thermal",
    "winter",
    "зим",
    "лыж",
    "мороз",
    "пух",
    "снег",
    "термо",
    "утепл",
}

DEMI_KEYWORDS = {
    "demi",
    "midseason",
    "transition",
    "демисез",
    "межсезон",
}

FORMAL_KEYWORDS = {
    "blazer",
    "classic",
    "formal",
    "office",
    "oxford",
    "smart",
    "suit",
    "tailored",
    "вечер",
    "делов",
    "классич",
    "костюм",
    "офис",
    "пиджак",
    "формаль",
}

COLOR_ALIASES = {
    "бежевый": "beige",
    "белый": "white",
    "бордовый": "red",
    "голубой": "blue",
    "желтый": "yellow",
    "жёлтый": "yellow",
    "зеленый": "green",
    "зелёный": "green",
    "коричневый": "brown",
    "красный": "red",
    "молочный": "white",
    "оливковый": "green",
    "розовый": "pink",
    "серый": "gray",
    "синий": "blue",
    "сиреневый": "purple",
    "фиолетовый": "purple",
    "хаки": "green",
    "черный": "black",
    "чёрный": "black",
    "black": "black",
    "blue": "blue",
    "brown": "brown",
    "camel": "brown",
    "charcoal": "gray",
    "ecru": "beige",
    "green": "green",
    "gray": "gray",
    "grey": "gray",
    "khaki": "green",
    "navy": "navy",
    "pink": "pink",
    "purple": "purple",
    "red": "red",
    "white": "white",
    "yellow": "yellow",
}


def normalize_text(value: Any) -> str:
    return re.sub(r"\s+", " ", str(value or "").strip()).lower()


def build_retry_session(
    *,
    total_retries: int = 4,
    backoff_factor: float = 1.2,
    pool_connections: int = 10,
    pool_maxsize: int = 10,
) -> requests.Session:
    session = requests.Session()
    retry = Retry(
        total=total_retries,
        connect=total_retries,
        read=total_retries,
        status=total_retries,
        backoff_factor=backoff_factor,
        status_forcelist=(408, 429, 500, 502, 503, 504),
        allowed_methods=frozenset({"GET", "HEAD", "OPTIONS"}),
        raise_on_status=False,
    )
    adapter = HTTPAdapter(
        max_retries=retry,
        pool_connections=pool_connections,
        pool_maxsize=pool_maxsize,
    )
    session.mount("https://", adapter)
    session.mount("http://", adapter)
    return session


def normalize_price(value: Any) -> Optional[float]:
    if value is None or isinstance(value, bool):
        return None

    if isinstance(value, (int, float)):
        return float(value)

    text = str(value).strip()
    if not text:
        return None

    text = (
        text.replace("₽", "")
        .replace("руб.", "")
        .replace("руб", "")
        .replace("р.", "")
        .replace("р", "")
        .replace("TL", "")
        .replace("TRY", "")
        .replace("€", "")
        .replace("$", "")
        .replace("\xa0", "")
        .replace("\u202f", "")
        .replace(" ", "")
    )
    text = re.sub(r"[^0-9.,]", "", text)
    if not text:
        return None

    separators = [char for char in text if char in ",."]
    if len(separators) == 1:
        separator = separators[0]
        left, right = text.split(separator, 1)
        if right.isdigit() and len(right) in (1, 2):
            text = f"{left}.{right}"
        else:
            text = text.replace(separator, "")
    elif len(separators) > 1:
        last_separator_index = max(text.rfind(","), text.rfind("."))
        integer_part = re.sub(r"[.,]", "", text[:last_separator_index])
        fraction_part = text[last_separator_index + 1:]
        if fraction_part.isdigit() and len(fraction_part) in (1, 2):
            text = f"{integer_part}.{fraction_part}"
        else:
            text = re.sub(r"[.,]", "", text)

    try:
        return float(text)
    except ValueError:
        return None


def format_price(value: Any, currency: Optional[str] = "RUB") -> str:
    normalized = normalize_price(value)
    if normalized is None:
        return "-"

    currency = (currency or "RUB").upper()
    if currency == "RUB":
        if normalized.is_integer():
            amount = f"{int(normalized):,}".replace(",", " ")
            return f"{amount} ₽"
        amount = f"{normalized:,.2f}".replace(",", " ").replace(".", ",")
        return f"{amount} ₽"
    if currency == "USD":
        return f"${normalized:,.2f}"
    if currency == "EUR":
        return f"€{normalized:,.2f}"
    return f"{normalized:,.2f} {currency}"


def extract_price_from_text(text: str) -> Optional[float]:
    if not text:
        return None

    matches = []
    for pattern in PRICE_PATTERNS:
        matches.extend(re.findall(pattern, str(text), flags=re.IGNORECASE))

    if not matches:
        return None

    return normalize_price(matches[-1])


def normalize_color_name(color_name: Any) -> Optional[str]:
    color = normalize_text(color_name)
    if not color:
        return None
    return COLOR_ALIASES.get(color, color)


def contains_blocked_words(*parts: Any) -> bool:
    haystack = " ".join(normalize_text(part) for part in parts if part)
    return any(word in haystack for word in HARD_BLOCKED_WORDS)


def detect_category(*parts: Any) -> str:
    text = " ".join(normalize_text(part) for part in parts if part)

    if not text or contains_blocked_words(text):
        return "other"

    if any(word in text for word in ("плать", "сарафан", "dress")):
        return "dress"
    if any(word in text for word in ("юбк", "skirt")):
        return "skirt"

    if any(word in text for word in ("джинс", "jeans", "denim")):
        return "jeans"
    if any(word in text for word in ("брюк", "брюки", "pants", "trouser", "legging", "леггин", "джоггер")):
        return "trousers"
    if any(word in text for word in ("шорт", "short")):
        return "shorts"

    if any(word in text for word in ("кроссов", "кед", "sneaker", "trainer", "running shoe")):
        return "sneakers"
    if any(word in text for word in ("ботин", "сапог", "boot")):
        return "boots"
    if any(word in text for word in ("туф", "лофер", "балетк", "мокас", "derby", "oxford", "shoe", "loafer")):
        return "shoes"

    if any(word in text for word in ("футбол", "майк", "tank top", "t-shirt", "t shirt", "tee", "лонгслив")):
        return "tshirt"
    if any(word in text for word in ("топ", "top", "body", "боди")):
        return "top"
    if any(word in text for word in ("рубаш", "блуз", "shirt", "blouse", "polo")):
        return "shirt"
    if any(word in text for word in ("худи", "толстов", "hoodie")):
        return "hoodie"
    if any(word in text for word in ("свитер", "свитшот", "джемпер", "кардиган", "knit", "jumper", "sweater", "cardigan", "sweatshirt")):
        return "sweater"

    if any(word in text for word in ("пальто", "плащ", "тренч", "парка", "parka", "coat", "trench", "puffer")):
        return "coat"
    if any(word in text for word in ("куртк", "бомбер", "жакет", "пиджак", "блейзер", "ветров", "jacket", "blazer", "bomber")):
        return "jacket"

    return "other"


def infer_gender(*parts: Any, default: Optional[str] = None) -> Optional[str]:
    text = " ".join(normalize_text(part) for part in parts if part)
    if any(word in text for word in ("женщин", "женск", "female", "women", "woman", "girls")):
        return "female"
    if any(word in text for word in ("мужчин", "мужск", "male", "men", "man", "boys")):
        return "male"
    if default in {"female", "male", "unisex"}:
        return default
    return "unisex"


def infer_style(*parts: Any, default: Optional[str] = None) -> str:
    text = " ".join(normalize_text(part) for part in parts if part)
    if any(word in text for word in SPORT_KEYWORDS):
        return "sport"
    if any(word in text for word in FORMAL_KEYWORDS):
        return "formal"
    if default in {"sport", "formal", "casual"}:
        return default
    return "casual"


def contains_any_keyword(text: str, keywords: set) -> bool:
    return any(word in text for word in keywords)


def infer_warmth(*parts: Any, category: Optional[str] = None) -> str:
    text = " ".join(normalize_text(part) for part in parts if part)

    if contains_any_keyword(text, COLD_WEATHER_KEYWORDS | SNOW_KEYWORDS):
        return "warm"

    if category in {"coat", "jacket", "hoodie", "sweater", "boots"}:
        if any(word in text for word in HOT_WEATHER_KEYWORDS):
            return "light"
        if any(word in text for word in DEMI_KEYWORDS | WIND_KEYWORDS):
            return "mid"
        return "mid"

    if category in {"shorts", "tshirt", "top", "skirt", "dress", "sneakers", "shoes"}:
        return "light"

    return "mid"


def infer_water_resistant(*parts: Any, category: Optional[str] = None) -> bool:
    text = " ".join(normalize_text(part) for part in parts if part)
    if contains_any_keyword(text, RAIN_KEYWORDS):
        return True
    return category in {"boots"} and any(word in text for word in WIND_KEYWORDS)


def infer_weather_flags(*parts: Any, category: Optional[str] = None, style: Optional[str] = None) -> Dict[str, bool]:
    text = " ".join(normalize_text(part) for part in parts if part)
    warmth = infer_warmth(text, category=category)

    rain = infer_water_resistant(text, category=category)
    wind = (
        contains_any_keyword(text, WIND_KEYWORDS)
        or category in {"jacket", "coat"}
        or (rain and category in {"jacket", "coat", "boots"})
    )
    snow = (
        contains_any_keyword(text, SNOW_KEYWORDS)
        or (warmth == "warm" and category in {"coat", "jacket", "boots"})
    )
    heat = (
        contains_any_keyword(text, HOT_WEATHER_KEYWORDS)
        or (warmth == "light" and category in {"tshirt", "top", "shirt", "shorts", "skirt", "dress"})
    )

    if style == "sport" and category in {"boots", "jacket", "coat"} and contains_any_keyword(text, {"outdoor", "trail", "technical"}):
        rain = True
        wind = True

    return {
        "rain": bool(rain),
        "wind": bool(wind),
        "snow": bool(snow),
        "heat": bool(heat),
    }


def infer_weather_profiles(flags: Dict[str, bool], category: Optional[str] = None) -> list[str]:
    profiles = set()

    if flags["wind"] and flags["snow"]:
        profiles.add("bad_weather")
        profiles.add("winter_weather")
    if flags["rain"] and flags["wind"]:
        profiles.add("bad_weather")
        profiles.add("wet_weather")
    if flags["heat"] and flags["wind"]:
        profiles.add("hot_weather")
    if flags["heat"] and not flags["snow"]:
        profiles.add("summer_weather")
    if flags["snow"] and not flags["heat"]:
        profiles.add("winter_weather")
    if flags["wind"] and not flags["heat"]:
        profiles.add("windy_weather")
    if category in {"jacket", "coat", "boots"} and not flags["heat"]:
        profiles.add("transitional_weather")

    return sorted(profiles)


def infer_weather_tags(flags: Dict[str, bool], warmth: str, category: Optional[str] = None) -> list[str]:
    tags = set()
    if flags["rain"]:
        tags.add("rain")
    if flags["wind"]:
        tags.add("wind")
    if flags["snow"]:
        tags.add("snow")
        tags.add("cold")
    if flags["heat"]:
        tags.add("hot")

    if warmth == "warm":
        tags.add("cold")
    elif warmth == "light":
        tags.add("hot")
    else:
        tags.add("mild")

    if category in {"jacket", "coat", "boots"}:
        tags.add("demi")

    return sorted(tags)


def infer_purpose_tags(*parts: Any, category: Optional[str] = None, style: Optional[str] = None) -> list[str]:
    text = " ".join(normalize_text(part) for part in parts if part)
    tags = set()

    if style == "sport" or contains_any_keyword(text, SPORT_KEYWORDS):
        tags.add("sport")
        tags.add("gym")
    if style == "formal" or contains_any_keyword(text, FORMAL_KEYWORDS):
        tags.add("office")
        tags.add("formal")
    if category in {"coat", "jacket", "boots"}:
        tags.add("outerwear")
        tags.add("street")
    if category in {"tshirt", "top", "shirt", "shorts", "jeans", "skirt", "dress"}:
        tags.add("casual")
    if contains_any_keyword(text, {"outdoor", "trail", "hiking", "technical", "utility", "туризм"}) or category in {"boots"}:
        tags.add("outdoor")
    if contains_any_keyword(text, RAIN_KEYWORDS | WIND_KEYWORDS | SNOW_KEYWORDS):
        tags.add("weather")

    return sorted(tags)


def is_valid_catalog_item(item: Dict[str, Any]) -> bool:
    title = re.sub(r"\s+", " ", str(item.get("title") or "").strip())
    url = str(item.get("url") or "").strip()
    image_url = str(item.get("image_url") or "").strip()
    source = str(item.get("source") or "").strip().lower()
    category = str(item.get("category") or "").strip().lower()
    price = normalize_price(item.get("price"))

    if len(title) < 4 or len(title) > 180:
        return False
    if category not in ALLOWED_CATEGORIES:
        return False
    if contains_blocked_words(title, item.get("style"), item.get("gender")):
        return False
    if not url.startswith("http"):
        return False
    if source != "zara" and not image_url.startswith("http"):
        return False
    if price is None or price < 300 or price > 500000:
        return False
    return True


def derive_catalog_metadata(
    *,
    title: Any,
    category: Any,
    style: Any = None,
    gender: Any = None,
    source: Any = None,
    extra_context: Any = None,
) -> Dict[str, Any]:
    normalized_category = str(category or "").strip().lower()
    normalized_style = infer_style(style, extra_context, title, default=(style or None))
    normalized_gender = infer_gender(gender, extra_context, title, default=(gender or None))

    context = " ".join(
        part for part in [
            str(title or "").strip(),
            normalized_category,
            str(style or "").strip(),
            str(gender or "").strip(),
            str(source or "").strip(),
            str(extra_context or "").strip(),
        ] if part
    )

    warmth = infer_warmth(context, category=normalized_category)
    flags = infer_weather_flags(
        context,
        category=normalized_category,
        style=normalized_style,
    )

    return {
        "gender": normalized_gender,
        "style": normalized_style,
        "warmth": warmth,
        "water_resistant": flags["rain"],
        "weather_rain": flags["rain"],
        "weather_wind": flags["wind"],
        "weather_snow": flags["snow"],
        "weather_heat": flags["heat"],
        "weather_tags": ",".join(
            infer_weather_tags(flags, warmth, category=normalized_category)
        ),
        "weather_profiles": ",".join(
            infer_weather_profiles(flags, category=normalized_category)
        ),
        "purpose_tags": ",".join(
            infer_purpose_tags(
                context,
                category=normalized_category,
                style=normalized_style,
            )
        ),
    }


def finalize_product(
    item: Dict[str, Any],
    *,
    default_gender: Optional[str] = None,
    default_style: Optional[str] = None,
    category_hint: Optional[str] = None,
) -> Optional[Dict[str, Any]]:
    title = re.sub(r"\s+", " ", str(item.get("title") or "").strip())
    category_source = " ".join(
        part for part in [title, category_hint, item.get("category"), item.get("style")] if part
    )
    category = detect_category(category_source)

    normalized = {
        "title": title,
        "category": category,
        "color": normalize_color_name(item.get("color")),
        "price": normalize_price(item.get("price")),
        "currency": (item.get("currency") or "RUB").upper(),
        "url": str(item.get("url") or "").strip(),
        "image_url": str(item.get("image_url") or "").strip(),
        "source": str(item.get("source") or "unknown").strip().lower(),
        "external_id": str(item.get("external_id") or "").strip() or None,
        "gender": infer_gender(category_hint, item.get("gender"), title, default=default_gender),
        "style": infer_style(category_hint, item.get("style"), title, default=default_style),
    }
    normalized.update(
        derive_catalog_metadata(
            title=title,
            category=normalized["category"],
            style=normalized["style"],
            gender=normalized["gender"],
            source=normalized["source"],
            extra_context=category_hint,
        )
    )

    if not is_valid_catalog_item(normalized):
        return None

    return normalized
