from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from typing import Iterable

import requests

from parsers.models import ParsedProduct


LOGGER = logging.getLogger(__name__)


class ParserUnavailable(RuntimeError):
    """Raised when a source is intentionally disabled or currently unstable."""


class BaseStoreParser(ABC):
    store_key: str
    base_url: str

    def __init__(self) -> None:
        self.session = requests.Session()
        self.session.headers.update(
            {
                "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)",
                "Accept": "application/json, text/plain, */*",
                "Accept-Language": "ru-RU,ru;q=0.9,en;q=0.8",
            }
        )

    @abstractmethod
    def fetch_products(self, limit: int | None = None) -> Iterable[ParsedProduct]:
        """Return curated raw products from one store."""


class UnavailableStoreParser(BaseStoreParser):
    def __init__(self, *, store_key: str, base_url: str, reason: str) -> None:
        super().__init__()
        self.store_key = store_key
        self.base_url = base_url
        self.reason = reason

    def fetch_products(self, limit: int | None = None) -> Iterable[ParsedProduct]:
        raise ParserUnavailable(f"{self.store_key} parser is disabled: {self.reason}")
