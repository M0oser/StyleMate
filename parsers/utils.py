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

    if any(word in text for word in ("пальто", "плащ", "тренч", "coat", "trench", "puffer")):
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

    if not is_valid_catalog_item(normalized):
        return None

    return normalized
