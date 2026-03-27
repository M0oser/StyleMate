from __future__ import annotations

import re

from vocab.fashion import BLOCKED_CURATION_KEYWORDS


def determine_category_fields(
    title: str,
    source_category: str | None = None,
    source_subcategory: str | None = None,
) -> dict[str, str | None]:
    text = " ".join(filter(None, [title, source_category, source_subcategory])).lower()
    normalized = re.sub(r"[_./-]+", " ", text)

    if any(keyword in normalized for keyword in BLOCKED_CURATION_KEYWORDS):
        return {"category": None, "subcategory": None, "role": None}

    def contains(*words: str) -> bool:
        return any(word in normalized for word in words)

    sports_signal = contains(
        "sport",
        "спортив",
        "running",
        "run",
        "бег",
        "trail",
        "fitness",
        "training",
        "gym",
        "interlock",
        ".sport",
    )

    category = None
    role = None

    if contains("running shoes", "running shoe", "trail shoe", "бег", "run shoe") or (source_category or "").upper() == "RUNNING SHOES":
        category, role = "running_shoes", "running_shoes"
    elif sports_signal and contains("windbreaker", "ветровк", "track jacket", "олимпийк", "training jacket"):
        category, role = "track_jacket", "outerwear"
    elif sports_signal and contains("sports bra", "топ для фитнеса", "training top", "running top", "спортивный топ"):
        category, role = "active_top", "active_top"
    elif sports_signal and contains("legging", "тайтс", "велосипедк", "jogger", "джоггер", "training pant", "sport pant", "спортивные брюки"):
        category, role = "active_bottom", "active_bottom"
    elif sports_signal and contains("shorts", "шорт"):
        category, role = "sports_shorts", "active_bottom"
    elif sports_signal and contains("hoodie", "худи", "sweatshirt", "свитшот", "толстовк", "polo", "футбол", "майк", "t-shirt", "tee", "top"):
        category, role = "active_top", "active_top"
    elif contains("sneaker", "кроссов"):
        category, role = "sneakers", "shoes"
    elif contains("boot", "ботин", "сапог"):
        category, role = "boots", "shoes"
    elif contains("loafer", "лофер"):
        category, role = "loafers", "shoes"
    elif contains("heel", "туфл", "лодочк"):
        category, role = "heels", "shoes"
    elif contains("flat", "балетк"):
        category, role = "flats", "shoes"
    elif contains("dress", "плать"):
        category, role = "dress", "dress"
    elif contains("skirt", "юбк"):
        category, role = "skirt", "bottom"
    elif contains("jeans", "джинс"):
        category, role = "jeans", "bottom"
    elif contains("trous", "брюк", "pants", "slacks"):
        category, role = "trousers", "bottom"
    elif contains("shorts", "шорт"):
        category, role = "shorts", "bottom"
    elif contains("legging", "тайтс", "велосипедк"):
        category, role = "leggings", "active_bottom"
    elif contains("blazer", "пиджак", "жакет"):
        category, role = "blazer", "outerwear"
    elif contains("trench", "тренч"):
        category, role = "trench", "outerwear"
    elif contains("coat", "пальт", "пуховик"):
        category, role = "coat", "outerwear"
    elif contains("vest", "жилет"):
        category, role = "vest", "outerwear"
    elif contains("jacket", "куртк"):
        category, role = "jacket", "outerwear"
    elif contains("hoodie", "худи"):
        category, role = "hoodie", "top"
    elif contains("sweatshirt", "свитшот"):
        category, role = "sweatshirt", "top"
    elif contains("sweater", "джемпер", "кардиган", "свитер", "knit"):
        category, role = "knitwear", "top"
    elif contains("t-shirt", "t shirt", "tee", "футбол", "майк"):
        category, role = "t_shirt", "top"
    elif contains("blouse", "блуз"):
        category, role = "blouse", "top"
    elif contains("shirt", "рубаш", "polo"):
        category, role = "shirt", "top"
    elif contains("top"):
        category, role = "top", "top"

    return {
        "category": category,
        "subcategory": source_subcategory.lower() if source_subcategory else None,
        "role": role,
    }
