#!/usr/bin/env python3
import argparse
import os
import shutil
import sqlite3
import sys
from datetime import datetime
from urllib.parse import urlparse

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from database.db import DB_PATH, ensure_shop_catalog_schema


def make_backup(db_path: str) -> str:
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = db_path.replace(".db", f".before_currency_backfill_{timestamp}.db")
    shutil.copy2(db_path, backup_path)
    return backup_path


def infer_source_currency(url: str, source: str, currency: str):
    parsed = urlparse(url or "")
    host = (parsed.netloc or "").lower()
    path = (parsed.path or "").lower()

    normalized_source = (source or "unknown").strip().lower() or "unknown"
    normalized_currency = (currency or "RUB").strip().upper() or "RUB"

    if "zara.com" in host:
        normalized_source = "zara"
        if "/tr/" in path:
            normalized_currency = "TRY"
        elif "/nl/" in path:
            normalized_currency = "EUR"
        elif normalized_currency == "RUB":
            normalized_currency = "EUR"
        return normalized_source, normalized_currency

    if "limestore.com" in host:
        return "lime", "RUB"
    if "sela.ru" in host:
        return "sela", "RUB"
    if "sneakerhead.ru" in host:
        return "sneakerhead", "RUB"
    if "pavelmazko.com" in host:
        return "pavel_mazko", "RUB"

    return normalized_source, normalized_currency


def backfill_catalog_currency(db_path: str, limit: int = None, only_suspicious: bool = False) -> dict:
    ensure_shop_catalog_schema(db_path)
    con = sqlite3.connect(db_path)
    con.row_factory = sqlite3.Row
    cur = con.cursor()

    query = """
        SELECT id, source, currency, url, price
        FROM shop_catalog
        WHERE url IS NOT NULL AND TRIM(url) != ''
    """
    params = []

    if only_suspicious:
        query += """
            AND (
                source = 'unknown'
                OR (source = 'zara' AND currency NOT IN ('EUR', 'TRY'))
                OR (currency = 'RUB' AND url LIKE '%zara.com/%')
            )
        """

    query += " ORDER BY id ASC"

    if limit is not None:
        query += " LIMIT ?"
        params.append(limit)

    rows = cur.execute(query, params).fetchall()

    updated = 0
    unchanged = 0

    for row in rows:
        new_source, new_currency = infer_source_currency(row["url"], row["source"], row["currency"])
        current_source = (row["source"] or "unknown").strip().lower() or "unknown"
        current_currency = (row["currency"] or "RUB").strip().upper() or "RUB"

        if new_source == current_source and new_currency == current_currency:
            unchanged += 1
            continue

        cur.execute(
            """
            UPDATE shop_catalog
            SET source = ?, currency = ?
            WHERE id = ?
            """,
            (new_source, new_currency, row["id"]),
        )
        updated += 1

    con.commit()
    con.close()

    return {
        "scanned": len(rows),
        "updated": updated,
        "unchanged": unchanged,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Backfill source/currency for existing catalog rows using store URL.")
    parser.add_argument("--db-path", default=str(DB_PATH), help="Path to wardrobe.db")
    parser.add_argument("--limit", type=int, default=None, help="Process only first N rows")
    parser.add_argument("--only-suspicious", action="store_true", help="Update only suspicious rows")
    parser.add_argument("--no-backup", action="store_true", help="Skip DB backup")
    args = parser.parse_args()

    if not os.path.exists(args.db_path):
        raise FileNotFoundError(args.db_path)

    if not args.no_backup:
        backup_path = make_backup(args.db_path)
        print(f"backup_created={backup_path}")

    result = backfill_catalog_currency(
        db_path=args.db_path,
        limit=args.limit,
        only_suspicious=args.only_suspicious,
    )
    for key, value in result.items():
        print(f"{key}={value}")


if __name__ == "__main__":
    main()
