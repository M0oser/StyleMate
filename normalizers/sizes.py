from __future__ import annotations

import re

from parsers.models import ParsedSize


def normalize_sizes(sizes: list[ParsedSize]) -> list[ParsedSize]:
    normalized: list[ParsedSize] = []
    seen: set[tuple[str, str | None]] = set()
    for size in sizes:
        label = (size.size_label or "").strip().upper()
        if not label:
            continue
        size_system = (size.size_system or "").strip().upper() or None
        key = (label, size_system)
        if key in seen:
            continue
        seen.add(key)
        normalized.append(
            ParsedSize(
                size_label=label,
                size_system=size_system,
                size_value=(size.size_value or label).strip(),
                availability=size.availability or "unknown",
                size_notes=size.size_notes,
            )
        )
    return normalized


def derive_size_range_notes(sizes: list[ParsedSize]) -> list[str]:
    labels = {size.size_label.upper() for size in sizes}
    notes: list[str] = []
    numeric_values = extract_numeric_sizes(sizes)

    if len(labels) >= 6:
        notes.append("extended_size_range")
    elif len(labels) <= 3 and labels:
        notes.append("limited_size_range")

    if labels & {"XXL", "3XL", "4XL", "50", "52", "54", "56"}:
        notes.append("plus_size_friendly")
    if any("PETITE" in label for label in labels):
        notes.append("petite_friendly")
    if any("TALL" in label for label in labels):
        notes.append("tall_friendly")
    if numeric_values and max(numeric_values) >= 39:
        notes.append("adult_numeric_range")
    if numeric_values and max(numeric_values) <= 34:
        notes.append("junior_numeric_range")

    return notes


def extract_numeric_sizes(sizes: list[ParsedSize]) -> list[int]:
    values: list[int] = []
    for size in sizes:
        label = (size.size_label or "").upper()
        if label.isdigit():
            values.append(int(label))
            continue
        matches = re.findall(r"\d+", label)
        if matches:
            values.extend(int(match) for match in matches)
    return sorted(set(values))


def is_probable_junior_footwear_range(sizes: list[ParsedSize]) -> bool:
    numeric_values = extract_numeric_sizes(sizes)
    if not numeric_values:
        return False
    return max(numeric_values) <= 34
