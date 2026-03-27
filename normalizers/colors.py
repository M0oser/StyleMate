from __future__ import annotations


COLOR_KEYWORDS = {
    "black": {"black", "черн", "чёрн"},
    "white": {"white", "бел"},
    "gray": {"gray", "grey", "сер"},
    "beige": {"beige", "беж", "молоч", "ecru"},
    "brown": {"brown", "корич", "шоколад", "camel", "карамел"},
    "blue": {"blue", "син", "navy", "деним", "джинс"},
    "red": {"red", "красн", "burgundy", "бордов"},
    "green": {"green", "зелен", "зелён", "khaki", "хаки", "olive"},
    "pink": {"pink", "розов", "fuchsia"},
    "purple": {"purple", "фиолет"},
    "yellow": {"yellow", "желт"},
    "orange": {"orange", "оранж"},
}

PATTERN_KEYWORDS = {
    "striped": {"strip", "полос"},
    "checked": {"check", "клетк", "tartan"},
    "printed": {"print", "принт"},
    "graphic": {"graphic", "лого", "logo"},
    "solid": set(),
}


def normalize_color_family(color_raw: str | None, title: str = "", description: str = "") -> str | None:
    text = " ".join(filter(None, [color_raw, title, description])).lower()
    for family, keywords in COLOR_KEYWORDS.items():
        if any(keyword in text for keyword in keywords):
            return family
    return None


def infer_pattern(title: str, description: str | None = None) -> str:
    text = " ".join(filter(None, [title, description])).lower()
    for pattern, keywords in PATTERN_KEYWORDS.items():
        if keywords and any(keyword in text for keyword in keywords):
            return pattern
    return "solid"
