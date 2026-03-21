#!/usr/bin/env python3
import argparse
import os
import shutil
import sqlite3
import sys
from datetime import datetime

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from database.db import DB_PATH, ensure_shop_catalog_schema
from parsers.utils import derive_catalog_metadata


def make_backup(db_path: str) -> str:
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = db_path.replace(".db", f".before_weather_backfill_{timestamp}.db")
    shutil.copy2(db_path, backup_path)
    return backup_path


def backfill_catalog_weather(db_path: str, limit: int = None, only_missing: bool = False) -> dict:
    ensure_shop_catalog_schema(db_path)

    con = sqlite3.connect(db_path)
    con.row_factory = sqlite3.Row
    cur = con.cursor()

    query = """
        SELECT id, title, category, style, gender, source,
               warmth, water_resistant, weather_tags,
               weather_rain, weather_wind, weather_snow, weather_heat,
               weather_profiles, purpose_tags
        FROM shop_catalog
        WHERE title IS NOT NULL AND category IS NOT NULL
    """
    params = []

    if only_missing:
        query += """
            AND (
                COALESCE(weather_tags, '') = ''
                OR COALESCE(weather_profiles, '') = ''
                OR COALESCE(purpose_tags, '') = ''
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
        metadata = derive_catalog_metadata(
            title=row["title"],
            category=row["category"],
            style=row["style"],
            gender=row["gender"],
            source=row["source"],
        )

        current = {
            "warmth": row["warmth"] or "mid",
            "water_resistant": bool(row["water_resistant"]),
            "weather_tags": row["weather_tags"] or "",
            "weather_rain": bool(row["weather_rain"]),
            "weather_wind": bool(row["weather_wind"]),
            "weather_snow": bool(row["weather_snow"]),
            "weather_heat": bool(row["weather_heat"]),
            "weather_profiles": row["weather_profiles"] or "",
            "purpose_tags": row["purpose_tags"] or "",
        }

        comparable_metadata = dict(metadata)
        comparable_metadata["water_resistant"] = bool(comparable_metadata["water_resistant"])
        comparable_metadata["weather_rain"] = bool(comparable_metadata["weather_rain"])
        comparable_metadata["weather_wind"] = bool(comparable_metadata["weather_wind"])
        comparable_metadata["weather_snow"] = bool(comparable_metadata["weather_snow"])
        comparable_metadata["weather_heat"] = bool(comparable_metadata["weather_heat"])

        if current == comparable_metadata:
            unchanged += 1
            continue

        cur.execute(
            """
            UPDATE shop_catalog
            SET warmth = ?,
                water_resistant = ?,
                weather_tags = ?,
                weather_rain = ?,
                weather_wind = ?,
                weather_snow = ?,
                weather_heat = ?,
                weather_profiles = ?,
                purpose_tags = ?
            WHERE id = ?
            """,
            (
                metadata["warmth"],
                int(bool(metadata["water_resistant"])),
                metadata["weather_tags"],
                int(bool(metadata["weather_rain"])),
                int(bool(metadata["weather_wind"])),
                int(bool(metadata["weather_snow"])),
                int(bool(metadata["weather_heat"])),
                metadata["weather_profiles"],
                metadata["purpose_tags"],
                row["id"],
            ),
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
    parser = argparse.ArgumentParser(description="Backfill weather and purpose metadata for existing shop_catalog items.")
    parser.add_argument("--db-path", default=str(DB_PATH), help="Path to wardrobe.db")
    parser.add_argument("--limit", type=int, default=None, help="Process only first N rows")
    parser.add_argument("--only-missing", action="store_true", help="Update only rows with missing derived metadata")
    parser.add_argument("--no-backup", action="store_true", help="Skip DB backup")
    args = parser.parse_args()

    if not os.path.exists(args.db_path):
        raise FileNotFoundError(args.db_path)

    if not args.no_backup:
        backup_path = make_backup(args.db_path)
        print(f"backup_created={backup_path}")

    result = backfill_catalog_weather(
        db_path=args.db_path,
        limit=args.limit,
        only_missing=args.only_missing,
    )
    for key, value in result.items():
        print(f"{key}={value}")


if __name__ == "__main__":
    main()
