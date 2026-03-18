from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import QLabel, QVBoxLayout, QWidget

from desktop_app.image_loader import get_image_loader
from desktop_app.widgets.product_row import ThumbnailLabel, _cover_pixmap
from parsers.utils import format_price


class ProductTileWidget(QWidget):
    def __init__(self, item_data: dict) -> None:
        super().__init__()
        self.item_data = item_data
        self._loader = get_image_loader()
        self._loader.image_loaded.connect(self._on_image_loaded)
        self._current_url = self._loader.normalize_url(item_data.get("image_url"), kind="thumb")

        self.setObjectName("productTile")

        layout = QVBoxLayout()
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(8)
        self.setLayout(layout)

        self.image = ThumbnailLabel(item_data.get("category", "?"))
        self.image.setObjectName("tileImage")
        self.image.setFixedSize(220, 240)

        self.title = QLabel(item_data.get("title", "-"))
        self.title.setObjectName("tileTitle")
        self.title.setWordWrap(True)

        meta = f"{item_data.get('category', '-')} • {item_data.get('color') or 'neutral'}"
        self.meta = QLabel(meta)
        self.meta.setObjectName("tileMeta")

        self.price = QLabel(format_price(item_data.get("price"), item_data.get("currency")))
        self.price.setObjectName("tilePrice")

        layout.addWidget(self.image)
        layout.addWidget(self.title)
        layout.addWidget(self.meta)
        layout.addWidget(self.price)
        layout.addStretch()

        if self._current_url:
            self._loader.load(self._current_url, kind="thumb")

    def _on_image_loaded(self, url: str, pixmap: QPixmap) -> None:
        if url != self._current_url:
            return

        self.image._pixmap = _cover_pixmap(pixmap, self.image.width(), self.image.height())
        self.image.update()
        self.image.setText("")
