from __future__ import annotations

import hashlib
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import requests
from PySide6.QtCore import QObject, QStandardPaths, Signal
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import QApplication


class ImageLoader(QObject):
    image_loaded = Signal(str, QPixmap)
    image_failed = Signal(str, str)
    _image_bytes_ready = Signal(str, bytes)

    def __init__(self) -> None:
        super().__init__()
        self._memory_cache: dict[str, QPixmap] = {}
        self._pending: set[str] = set()
        self._executor = ThreadPoolExecutor(max_workers=8, thread_name_prefix="stylemate-image")
        self._cache_dir = self._build_cache_dir()
        self._image_bytes_ready.connect(self._on_image_bytes_ready)

        app = QApplication.instance()
        if app is not None:
            app.aboutToQuit.connect(self.shutdown)

    def load(self, url: str | None, kind: str = "thumb") -> None:
        normalized_url = self.normalize_url(url, kind=kind)
        if not normalized_url:
            return

        cached = self._memory_cache.get(normalized_url)
        if cached is not None:
            self.image_loaded.emit(normalized_url, cached)
            return

        cache_path = self._cache_path(normalized_url)
        if cache_path.exists():
            try:
                data = cache_path.read_bytes()
            except OSError:
                data = b""
            if data:
                self._image_bytes_ready.emit(normalized_url, data)
                return

        if normalized_url in self._pending:
            return

        self._pending.add(normalized_url)
        self._executor.submit(self._download_image, normalized_url)

    def _download_image(self, url: str) -> None:
        try:
            response = requests.get(
                url,
                timeout=20,
                headers={
                    "User-Agent": "Mozilla/5.0",
                    "Accept": "image/avif,image/webp,image/apng,image/*,*/*;q=0.8",
                    "Referer": "https://www.zara.com/",
                },
            )
            response.raise_for_status()
            data = response.content
            if data:
                try:
                    self._cache_path(url).write_bytes(data)
                except OSError:
                    pass
                self._image_bytes_ready.emit(url, data)
            else:
                self.image_failed.emit(url, "Empty image data")
        except Exception as error:
            self.image_failed.emit(url, str(error))

    def _on_image_bytes_ready(self, url: str, data: bytes) -> None:
        self._pending.discard(url)

        pixmap = QPixmap()
        pixmap.loadFromData(data)

        if pixmap.isNull():
            self.image_failed.emit(url, "Invalid image data")
            return

        self._memory_cache[url] = pixmap
        self.image_loaded.emit(url, pixmap)

    @staticmethod
    def normalize_url(url: str | None, kind: str = "thumb") -> str | None:
        if not url:
            return None
        width = 220 if kind == "thumb" else 1100
        return url.replace("w={width}", f"w={width}")

    @staticmethod
    def _build_cache_dir() -> Path:
        base = QStandardPaths.writableLocation(QStandardPaths.CacheLocation)
        root = Path(base) if base else Path.cwd() / ".cache"
        cache_dir = root / "stylemate_images"
        cache_dir.mkdir(parents=True, exist_ok=True)
        return cache_dir

    def _cache_path(self, url: str) -> Path:
        suffix = Path(url.split("?", 1)[0]).suffix or ".img"
        key = hashlib.sha256(url.encode("utf-8")).hexdigest()
        return self._cache_dir / f"{key}{suffix}"

    def shutdown(self) -> None:
        self._executor.shutdown(wait=False, cancel_futures=True)


_image_loader: ImageLoader | None = None


def get_image_loader() -> ImageLoader:
    global _image_loader
    if _image_loader is None:
        _image_loader = ImageLoader()
    return _image_loader
