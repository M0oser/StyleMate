import random

from database.db import create_outfit_generation
from services.wardrobe_service import get_active_wardrobe_for_user


TOP = {"tshirt", "shirt", "hoodie", "sweater"}
BOTTOM = {"jeans", "trousers", "shorts"}
SHOES = {"sneakers", "boots", "shoes"}
OUTER = {"jacket", "coat"}

BRIGHT = {"red", "yellow", "orange", "green", "pink", "purple"}


def _pick(items, allowed):
    pool = [x for x in items if x["category"] in allowed]
    return random.choice(pool) if pool else None


def _score(items, occasion, style):
    score = 0
    colors = [x.get("color") for x in items if x.get("color")]

    bright_count = sum(1 for c in colors if c in BRIGHT)
    score -= max(0, bright_count - 1) * 2

    if style == "minimal":
        score += sum(
            1 for c in colors
            if c in {"black", "white", "gray", "beige", "navy", "brown"}
        )
    elif style == "street":
        score += sum(
            1 for c in colors
            if c in {"black", "white", "gray", "blue", "green", "red"}
        )
    elif style == "smart":
        score += sum(
            1 for c in colors
            if c in {"black", "white", "gray", "navy", "brown", "beige"}
        )

    if occasion == "office":
        score += sum(1 for x in items if x["category"] in {"shirt", "trousers", "shoes", "jacket", "coat"})
    elif occasion == "date":
        score += sum(1 for x in items if x["category"] in {"shirt", "jeans", "jacket", "coat", "shoes"})
    elif occasion == "casual":
        score += sum(1 for x in items if x["category"] in {"tshirt", "hoodie", "jeans", "sneakers", "shorts"})

    return score


def _build_single_candidate(wardrobe, occasion):
    top = _pick(wardrobe, TOP)
    bottom = _pick(wardrobe, BOTTOM)
    shoes = _pick(wardrobe, SHOES)
    outer = _pick(wardrobe, OUTER)

    selected = [x for x in [top, bottom, shoes] if x]

    if occasion in {"office", "date"} and outer:
        selected.append(outer)

    uniq = {}
    for item in selected:
        uniq[item["id"]] = item
    selected = list(uniq.values())

    if len(selected) < 3:
        return None

    return selected


def _role_for_category(category):
    if category in TOP:
        return "top"
    if category in BOTTOM:
        return "bottom"
    if category in SHOES:
        return "shoes"
    if category in OUTER:
        return "outerwear"
    return None


def _outfit_signature(items):
    ids = sorted(item["id"] for item in items)
    return tuple(ids)


def generate_outfit_options_for_user(user_id, occasion, style, limit=3):
    wardrobe = get_active_wardrobe_for_user(user_id)

    if not wardrobe:
        raise ValueError("Wardrobe is empty")

    candidates = []
    seen = set()

    # генерируем побольше, чтобы было из чего выбрать
    for _ in range(60):
        items = _build_single_candidate(wardrobe, occasion)
        if not items:
            continue

        signature = _outfit_signature(items)
        if signature in seen:
            continue
        seen.add(signature)

        score = _score(items, occasion, style)
        candidates.append((score, items))

    if not candidates:
        raise ValueError("Not enough wardrobe items to generate outfit")

    candidates.sort(key=lambda x: x[0], reverse=True)
    candidates = candidates[:limit]

    result = []

    for score, items in candidates:
        payload_items = []
        for item in items:
            payload_items.append({
                "catalog_id": item["id"],
                "role": _role_for_category(item["category"]),
            })

        outfit_id = create_outfit_generation(
            user_id=user_id,
            occasion=occasion,
            style=style,
            score=score,
            items=payload_items,
        )

        result.append({
            "outfit_id": outfit_id,
            "user_id": user_id,
            "occasion": occasion,
            "style": style,
            "score": score,
            "items": items,
        })

    return result


def generate_outfit_for_user(user_id, occasion, style):
    outfits = generate_outfit_options_for_user(
        user_id=user_id,
        occasion=occasion,
        style=style,
        limit=1,
    )
    return outfits[0]