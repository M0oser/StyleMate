#!/usr/bin/env python3
import argparse
import os
import sqlite3
import sys
from typing import Any, Dict

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from database.db import DB_PATH, ensure_shop_catalog_schema, save_to_shop_catalog


def normalize_text(value: Any) -> str:
    return str(value or "").strip().lower()


def repair_category(title: str, current_category: str) -> str:
    text = normalize_text(title)
    category = normalize_text(current_category) or "unknown"

    if any(word in text for word in ("dress", "плать", "сарафан")):
        return "dress"
    if any(word in text for word in ("skirt", "юбк")):
        return "skirt"

    if any(word in text for word in ("coat", "trench", "parka", "пальто", "плащ", "тренч")):
        return "coat"
    if any(word in text for word in ("jacket", "blazer", "бомбер", "куртк", "жакет", "пиджак")):
        return "jacket"

    if "jeans" in text or "джинс" in text:
        return "jeans"
    if any(word in text for word in ("trouser", "брюк", "брюки", "pants", "leggings", "legging", "джоггер")):
        return "trousers"
    if any(word in text for word in ("shorts", "шорты", "шорт")):
        return "shorts"

    if any(word in text for word in ("t-shirt", "t shirt", "tee", "футбол", "майк", "short sleeve t-shirt")):
        return "tshirt"
    if any(word in text for word in ("tank top", "cami", "cami top", "топ")):
        return "top"
    if any(word in text for word in ("shirt", "рубаш", "блуз", "polo")):
        return "shirt"
    if any(word in text for word in ("hoodie", "худи", "толстов")):
        return "hoodie"
    if any(word in text for word in ("sweater", "jumper", "cardigan", "свитер", "джемпер", "кардиган", "knit")):
        return "sweater"

    if any(word in text for word in ("boots", "boot", "ботин", "сапог")):
        return "boots"
    if any(word in text for word in ("sneaker", "trainer", "кроссов", "кеды")):
        return "sneakers"
    if any(word in text for word in ("loafer", "лофер", "derby shoes", "oxford shoes", "туф", "shoe")):
        return "shoes"

    return category


def row_to_item(row: sqlite3.Row) -> Dict[str, Any]:
    title = row["title"]
    category = repair_category(title, row["category"])

    return {
        "title": title,
        "category": category,
        "color": row["color"],
        "price": row["price"],
        "url": row["url"],
        "image_url": row["image_url"],
        "currency": row["currency"] if "currency" in row.keys() else "RUB",
        "source": row["source"] if "source" in row.keys() else "unknown",
        "external_id": row["external_id"] if "external_id" in row.keys() else None,
        "gender": row["gender"] if "gender" in row.keys() else "unisex",
        "style": row["style"] if "style" in row.keys() else "casual",
        "warmth": row["warmth"] if "warmth" in row.keys() else "mid",
        "water_resistant": row["water_resistant"] if "water_resistant" in row.keys() else 0,
        "weather_tags": row["weather_tags"] if "weather_tags" in row.keys() else "",
        "weather_rain": row["weather_rain"] if "weather_rain" in row.keys() else 0,
        "weather_wind": row["weather_wind"] if "weather_wind" in row.keys() else 0,
        "weather_snow": row["weather_snow"] if "weather_snow" in row.keys() else 0,
        "weather_heat": row["weather_heat"] if "weather_heat" in row.keys() else 0,
        "weather_profiles": row["weather_profiles"] if "weather_profiles" in row.keys() else "",
        "purpose_tags": row["purpose_tags"] if "purpose_tags" in row.keys() else "",
    }


def sync_catalog(source_db: str, target_db: str) -> Dict[str, int]:
    ensure_shop_catalog_schema(target_db)

    source = sqlite3.connect(source_db)
    source.row_factory = sqlite3.Row
    cur = source.cursor()
    cur.execute("SELECT * FROM shop_catalog WHERE url IS NOT NULL AND TRIM(url) != '' ORDER BY id ASC")
    rows = cur.fetchall()
    source.close()

    total = 0
    saved = 0
    skipped = 0

    for row in rows:
        total += 1
        try:
            save_to_shop_catalog(row_to_item(row), db_path=target_db)
            saved += 1
        except Exception:
            skipped += 1

    return {"total": total, "saved": saved, "skipped": skipped}


def main() -> None:
    parser = argparse.ArgumentParser(description="Sync shop_catalog from another SQLite DB into the local StyleMate DB.")
    parser.add_argument("--source-db", default="/tmp/stylemate_remote_wardrobe.db")
    parser.add_argument("--target-db", default=DB_PATH)
    args = parser.parse_args()

    if not os.path.exists(args.source_db):
        raise SystemExit(f"Source DB not found: {args.source_db}")

    stats = sync_catalog(args.source_db, args.target_db)
    print(stats)


if __name__ == "__main__":
    main()
