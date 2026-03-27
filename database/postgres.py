from __future__ import annotations

from contextlib import contextmanager
from typing import Iterator

import psycopg
from psycopg.rows import dict_row


class PostgresDatabase:
    """Lightweight PostgreSQL connection helper."""

    def __init__(self, dsn: str) -> None:
        self.dsn = dsn

    @contextmanager
    def connection(self, *, autocommit: bool = False) -> Iterator[psycopg.Connection]:
        conn = psycopg.connect(self.dsn, row_factory=dict_row, autocommit=autocommit)
        try:
            yield conn
            if not autocommit:
                conn.commit()
        except Exception:
            if not autocommit:
                conn.rollback()
            raise
        finally:
            conn.close()
