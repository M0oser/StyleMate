#!/usr/bin/env python3
import argparse
import os
import shutil
import sqlite3
import sys
from datetime import datetime
from typing import Dict, Iterable, List, Optional

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from database.db import DB_PATH, ensure_shop_catalog_schema, save_to_shop_catalog


SPORT_FOOTWEAR_KEYWORDS = (
    "кроссов", "кеды", "runner", "jordan", "nike", "adidas",
    "new balance", "puma", "asics", "salomon", "reebok", "samba",
    "gazelle", "dunk", "vomero", "air max", "air force", "v2k",
)

APPAREL_BLOCKLIST = (
    "футбол", "t-shirt", "shirt", "shorts", "шорты", "брюк", "джинс",
    "hoodie", "sweater", "свитер", "куртк", "пальто", "jacket", "coat",
)

ACCESSORY_BLOCKLIST = (
    "аромат", "автоаромат", "шнурк", "мешок", "bag", "рюкзак", "носки",
    "socks", "lace", "брелок", "keychain", "wallet", "сумка",
)

RAIN_ZARA_KEYWORDS = (
    "waterproof", "water-repellent", "water repellent", "recco",
    "shell", "mountain", "outdoor", "gore", "lug", "commuter", "rubber",
)

RAIN_ZARA_BLOCKLIST = (
    "waistcoat", "gilet", "shorts", "training", "running", "football",
)

GYM_ZARA_KEYWORDS = (
    "training", "running", "workout", "jogging", "trail", "dry",
)

GYM_ZARA_BOTTOM_BLOCKLIST = (
    "wide-leg suit", "non-iron", "football", "cargo", "shell",
)


def make_backup(db_path: str) -> str:
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = db_path.replace(".db", f".before_safe_import_{timestamp}.db")
    shutil.copy2(db_path, backup_path)
    return backup_path


def row_to_item(row: sqlite3.Row) -> Dict:
    return {
        "title": row["title"],
        "category": row["category"],
        "color": row["color"],
        "price": row["price"],
        "currency": row["currency"] if "currency" in row.keys() else "RUB",
        "url": row["url"],
        "image_url": row["image_url"],
        "source": row["source"] if "source" in row.keys() else "unknown",
        "external_id": row["external_id"] if "external_id" in row.keys() else None,
    }


def is_sneakerhead_sport_footwear(row: sqlite3.Row) -> bool:
    title = (row["title"] or "").lower()
    category = (row["category"] or "").lower()

    if row["source"] != "sneakerhead" or category != "sneakers":
        return False

    if any(word in title for word in APPAREL_BLOCKLIST):
        return False
    if any(word in title for word in ACCESSORY_BLOCKLIST):
        return False

    return any(word in title for word in SPORT_FOOTWEAR_KEYWORDS)


def is_zara_rain_safe(row: sqlite3.Row) -> bool:
    title = (row["title"] or "").lower()
    category = (row["category"] or "").lower()

    if row["source"] != "zara":
        return False

    if category not in {"jacket", "coat", "trousers"}:
        return False

    if any(word in title for word in RAIN_ZARA_BLOCKLIST):
        return False

    return any(word in title for word in RAIN_ZARA_KEYWORDS)


def is_zara_gym_safe(row: sqlite3.Row) -> bool:
    title = (row["title"] or "").lower()
    category = (row["category"] or "").lower()

    if row["source"] != "zara":
        return False

    if category not in {"tshirt", "hoodie", "trousers", "shorts"}:
        return False

    if not any(word in title for word in GYM_ZARA_KEYWORDS):
        return False

    if category in {"trousers", "shorts"} and any(word in title for word in GYM_ZARA_BOTTOM_BLOCKLIST):
        return False

    return True


def collect_candidates(rows: Iterable[sqlite3.Row]) -> List[Dict]:
    selected = []

    for row in rows:
        if is_sneakerhead_sport_footwear(row) or is_zara_rain_safe(row) or is_zara_gym_safe(row):
            selected.append(row_to_item(row))

    return selected


def existing_urls(db_path: str) -> set:
    ensure_shop_catalog_schema(db_path)
    con = sqlite3.connect(db_path)
    cur = con.cursor()
    cur.execute("SELECT url FROM shop_catalog WHERE url IS NOT NULL")
    urls = {row[0] for row in cur.fetchall() if row[0]}
    con.close()
    return urls


def import_subset(source_db: str, target_db: str) -> Dict[str, int]:
    if not os.path.exists(source_db):
        raise FileNotFoundError(source_db)

    ensure_shop_catalog_schema(target_db)

    source_con = sqlite3.connect(source_db)
    source_con.row_factory = sqlite3.Row
    source_cur = source_con.cursor()
    source_cur.execute("""
        SELECT title, category, color, price, currency, url, image_url, source, external_id
        FROM shop_catalog
    """)
    candidates = collect_candidates(source_cur.fetchall())
    source_con.close()

    known_urls = existing_urls(target_db)
    inserted = 0
    skipped = 0
    by_source: Dict[str, int] = {}

    for item in candidates:
        if not item["url"] or item["url"] in known_urls:
            skipped += 1
            continue

        save_to_shop_catalog(item, db_path=target_db)
        inserted += 1
        known_urls.add(item["url"])
        by_source[item["source"]] = by_source.get(item["source"], 0) + 1

    return {
        "candidates": len(candidates),
        "inserted": inserted,
        "skipped": skipped,
        **{f"inserted_{source}": count for source, count in sorted(by_source.items())},
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Import safe subset of external catalog into current shop_catalog.")
    parser.add_argument(
        "--source-db",
        default="/tmp/stylemate_remote_wardrobe.db",
        help="Path to friend's wardrobe.db with extended shop_catalog",
    )
    parser.add_argument(
        "--target-db",
        default=str(DB_PATH),
        help="Path to current project wardrobe.db",
    )
    parser.add_argument(
        "--no-backup",
        action="store_true",
        help="Skip creating a DB backup before import",
    )
    args = parser.parse_args()

    if not args.no_backup:
        backup_path = make_backup(args.target_db)
        print(f"backup_created={backup_path}")

    result = import_subset(args.source_db, args.target_db)
    for key, value in result.items():
        print(f"{key}={value}")


if __name__ == "__main__":
    main()
