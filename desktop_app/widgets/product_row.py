from __future__ import annotations

from PySide6.QtCore import QRectF, Qt
from PySide6.QtGui import QPainter, QPainterPath, QPixmap
from PySide6.QtWidgets import QWidget, QHBoxLayout, QVBoxLayout, QLabel

from desktop_app.image_loader import get_image_loader
from parsers.utils import format_price


def _cover_pixmap(pixmap: QPixmap, width: int, height: int) -> QPixmap:
    scaled = pixmap.scaled(width, height, Qt.KeepAspectRatioByExpanding, Qt.SmoothTransformation)
    x = max(0, (scaled.width() - width) // 2)
    y = max(0, (scaled.height() - height) // 2)
    return scaled.copy(x, y, width, height)


class ThumbnailLabel(QLabel):
    def __init__(self, category: str) -> None:
        self._placeholder = (category[:2] or "?").upper()
        super().__init__(self._placeholder)
        self._current_url: str | None = None
        self._pixmap = QPixmap()
        self._loader = get_image_loader()
        self._loader.image_loaded.connect(self._on_image_loaded)

        self.setObjectName("thumbLabel")
        self.setFixedSize(72, 88)
        self.setAlignment(Qt.AlignCenter)

    def set_image_from_url(self, url: str | None) -> None:
        self._current_url = self._loader.normalize_url(url, kind="thumb")
        if not self._current_url:
            self._reset()
            return
        self._reset(show_text=False)
        self._loader.load(self._current_url, kind="thumb")

    def _on_image_loaded(self, url: str, pixmap: QPixmap) -> None:
        if url != self._current_url:
            return

        self._pixmap = _cover_pixmap(pixmap, self.width(), self.height())
        self.update()
        self.setText("")

    def _reset(self, show_text: bool = True) -> None:
        self._pixmap = QPixmap()
        self.update()
        if show_text:
            self.setText(self._placeholder)

    def paintEvent(self, event) -> None:
        super().paintEvent(event)

        if self._pixmap.isNull():
            return

        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        path = QPainterPath()
        path.addRoundedRect(QRectF(self.rect()), 18, 18)
        painter.setClipPath(path)
        painter.drawPixmap(self.rect(), self._pixmap)


class ProductRowWidget(QWidget):
    def __init__(self, item_data):
        super().__init__()
        self.item_data = item_data
        self.setObjectName("productRow")

        layout = QHBoxLayout()
        layout.setContentsMargins(12, 10, 12, 10)
        layout.setSpacing(14)
        self.setLayout(layout)

        thumb = ThumbnailLabel(item_data.get("category", "?"))
        thumb.set_image_from_url(item_data.get("image_url"))

        title = QLabel(item_data.get("title", "-"))
        title.setObjectName("rowTitle")
        title.setWordWrap(True)

        category = item_data.get("category", "-")
        color = item_data.get("color") or "neutral"
        source = (item_data.get("source") or "").replace("_", " ")

        meta = QLabel(f"{category} • {color}")
        meta.setObjectName("rowMeta")

        source_label = QLabel(source)
        source_label.setObjectName("rowSource")

        price = QLabel(format_price(item_data.get("price"), item_data.get("currency")))
        price.setObjectName("rowPrice")

        text_layout = QVBoxLayout()
        text_layout.setContentsMargins(0, 0, 0, 0)
        text_layout.setSpacing(3)
        text_layout.addWidget(title)
        text_layout.addWidget(meta)
        text_layout.addWidget(source_label)
        text_layout.addWidget(price)

        layout.addWidget(thumb, 0, Qt.AlignTop)
        layout.addLayout(text_layout, 1)
