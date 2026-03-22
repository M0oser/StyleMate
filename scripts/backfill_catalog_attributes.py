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

from backend.services.catalog_attribute_service import derive_item_attributes
from database.db import DB_PATH, ensure_shop_catalog_schema


ATTRIBUTE_FIELDS = [
    "subcategory",
    "material_tags",
    "fit_tags",
    "feature_tags",
    "usecase_tags",
    "hooded",
    "waterproof",
    "windproof",
    "insulated",
    "technical",
    "many_pockets",
    "pocket_level",
]


def make_backup(db_path: str) -> str:
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = db_path.replace(".db", f".before_attribute_backfill_{timestamp}.db")
    shutil.copy2(db_path, backup_path)
    return backup_path


def _row_snapshot(row: sqlite3.Row) -> dict:
    return {
        "subcategory": row["subcategory"] or "",
        "material_tags": row["material_tags"] or "",
        "fit_tags": row["fit_tags"] or "",
        "feature_tags": row["feature_tags"] or "",
        "usecase_tags": row["usecase_tags"] or "",
        "hooded": bool(row["hooded"]),
        "waterproof": bool(row["waterproof"]),
        "windproof": bool(row["windproof"]),
        "insulated": bool(row["insulated"]),
        "technical": bool(row["technical"]),
        "many_pockets": bool(row["many_pockets"]),
        "pocket_level": row["pocket_level"] or "low",
    }


def backfill_catalog_attributes(db_path: str, limit: int = None, only_missing: bool = False) -> dict:
    ensure_shop_catalog_schema(db_path)

    con = sqlite3.connect(db_path)
    con.row_factory = sqlite3.Row
    cur = con.cursor()

    query = """
        SELECT
            id, title, category, style, source, weather_tags, purpose_tags,
            subcategory, material_tags, fit_tags, feature_tags, usecase_tags,
            hooded, waterproof, windproof, insulated, technical, many_pockets, pocket_level
        FROM shop_catalog
        WHERE title IS NOT NULL AND category IS NOT NULL
    """
    params = []

    if only_missing:
        query += """
            AND (
                COALESCE(subcategory, '') = ''
                OR COALESCE(feature_tags, '') = ''
                OR COALESCE(usecase_tags, '') = ''
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
        derived = derive_item_attributes(
            title=row["title"],
            category=row["category"],
            style=row["style"],
            source=row["source"],
            weather_tags=row["weather_tags"],
            purpose_tags=row["purpose_tags"],
        )

        comparable = dict(derived)
        for key in {"hooded", "waterproof", "windproof", "insulated", "technical", "many_pockets"}:
            comparable[key] = bool(comparable[key])

        current = _row_snapshot(row)
        if current == comparable:
            unchanged += 1
            continue

        cur.execute(
            """
            UPDATE shop_catalog
            SET subcategory = ?,
                material_tags = ?,
                fit_tags = ?,
                feature_tags = ?,
                usecase_tags = ?,
                hooded = ?,
                waterproof = ?,
                windproof = ?,
                insulated = ?,
                technical = ?,
                many_pockets = ?,
                pocket_level = ?
            WHERE id = ?
            """,
            (
                derived["subcategory"],
                derived["material_tags"],
                derived["fit_tags"],
                derived["feature_tags"],
                derived["usecase_tags"],
                int(bool(derived["hooded"])),
                int(bool(derived["waterproof"])),
                int(bool(derived["windproof"])),
                int(bool(derived["insulated"])),
                int(bool(derived["technical"])),
                int(bool(derived["many_pockets"])),
                derived["pocket_level"],
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
    parser = argparse.ArgumentParser(description="Backfill rich catalog attributes for existing shop_catalog items.")
    parser.add_argument("--db-path", default=str(DB_PATH), help="Path to wardrobe.db")
    parser.add_argument("--limit", type=int, default=None, help="Process only first N rows")
    parser.add_argument("--only-missing", action="store_true", help="Update only rows with missing attribute metadata")
    parser.add_argument("--no-backup", action="store_true", help="Skip DB backup")
    args = parser.parse_args()

    if not os.path.exists(args.db_path):
        raise FileNotFoundError(args.db_path)

    if not args.no_backup:
        backup_path = make_backup(args.db_path)
        print(f"backup_created={backup_path}")

    result = backfill_catalog_attributes(
        db_path=args.db_path,
        limit=args.limit,
        only_missing=args.only_missing,
    )
    for key, value in result.items():
        print(f"{key}={value}")


if __name__ == "__main__":
    main()
