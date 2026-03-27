from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


DEFAULT_DATABASE_URL = "postgresql://postgres:postgres@localhost:5432/stylemate"


@dataclass(frozen=True)
class DatabaseSettings:
    dsn: str
    migrations_dir: Path


def get_database_settings() -> DatabaseSettings:
    root_dir = Path(__file__).resolve().parent.parent
    return DatabaseSettings(
        dsn=os.getenv("STYLIST_DATABASE_URL", DEFAULT_DATABASE_URL),
        migrations_dir=root_dir / "migrations",
    )
