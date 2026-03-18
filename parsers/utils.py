import re
from typing import Any


PRICE_PATTERNS = [
    r"\d[\d\s\xa0\u202f.,]*\s*₽",
    r"₽\s*\d[\d\s\xa0\u202f.,]*",
    r"\d[\d\s\xa0\u202f.,]*\s*руб\.?",
    r"\d[\d\s\xa0\u202f.,]*\s*р\.?",
]


def normalize_price(value: Any) -> float | None:
    if value is None:
        return None

    if isinstance(value, bool):
        return None

    if isinstance(value, (int, float)):
        return float(value)

    text = str(value).strip()
    if not text:
        return None

    # убираем валюты и мусор
    text = (
        text.replace("₽", "")
        .replace("руб.", "")
        .replace("руб", "")
        .replace("р.", "")
        .replace("р", "")
        .replace("\xa0", "")
        .replace("\u202f", "")  # narrow no-break space
        .replace(" ", "")
    )

    # оставляем только цифры, точки и запятые
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


def format_price(value: Any, currency: str | None = "RUB") -> str:
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


def extract_price_from_text(text: str) -> float | None:
    if not text:
        return None

    text = str(text)

    matches = []
    for pattern in PRICE_PATTERNS:
        matches.extend(re.findall(pattern, text, flags=re.IGNORECASE))

    if not matches:
        return None

    # обычно последняя цена — актуальная, если рядом есть старая/новая
    return normalize_price(matches[-1])
