from __future__ import annotations

import math
import sys
import webbrowser

from PySide6.QtCore import QSize, Qt
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import (
    QAbstractItemView,
    QApplication,
    QComboBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QSplitter,
    QTabWidget,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from desktop_app.image_loader import get_image_loader
from desktop_app.widgets.product_row import ProductRowWidget
from desktop_app.widgets.product_tile import ProductTileWidget
from parsers.utils import format_price
from database.db import init_db
from services.catalog_service import get_catalog, get_catalog_sources, get_catalog_total
from services.history_service import get_outfit_details, get_user_outfit_history
from services.outfit_service import generate_outfit_options_for_user
from services.user_service import create_new_user, get_all_users
from services.wardrobe_service import (
    add_catalog_item_to_user_wardrobe,
    get_active_wardrobe_for_user,
    remove_catalog_item_from_user_wardrobe,
)


CATEGORIES = [
    "all",
    "tshirt",
    "shirt",
    "hoodie",
    "sweater",
    "jeans",
    "trousers",
    "shorts",
    "jacket",
    "coat",
    "sneakers",
    "boots",
    "shoes",
]

CATALOG_PAGE_SIZE = 48


class AsyncImageLabel(QLabel):
    def __init__(self, width: int = 360, height: int = 460) -> None:
        super().__init__()
        self._loader = get_image_loader()
        self._loader.image_loaded.connect(self._on_image_loaded)
        self._current_url: str | None = None

        self.setObjectName("productImage")
        self.setFixedSize(width, height)
        self.setAlignment(Qt.AlignCenter)
        self.setText("Preview")

    def set_image_from_url(self, url: str | None) -> None:
        self._current_url = self._loader.normalize_url(url, kind="detail")
        self.setPixmap(QPixmap())

        if not self._current_url:
            self.setText("Preview")
            return

        self.setText("Loading...")
        self._loader.load(self._current_url, kind="detail")

    def _on_image_loaded(self, url: str, pixmap: QPixmap) -> None:
        if url != self._current_url:
            return

        scaled = pixmap.scaled(
            self.width(),
            self.height(),
            Qt.KeepAspectRatio,
            Qt.SmoothTransformation,
        )
        self.setPixmap(scaled)
        self.setText("")


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()

        self.setWindowTitle("Stylemate Desktop")
        self.resize(1680, 980)
        self.setMinimumSize(1380, 860)

        self.current_user = None
        self.catalog_items: list[dict] = []
        self.catalog_total = 0
        self.catalog_offset = 0
        self.catalog_has_more = True
        self.catalog_loading_more = False
        self.catalog_sources = []

        self.wardrobe_items = []
        self.generated_outfits = []
        self.current_outfit_items = []

        self.selected_catalog_item = None
        self.selected_explore_item = None
        self.selected_wardrobe_item = None
        self.selected_outfit_item = None
        self.selected_history_item = None

        self._build_ui()
        self._apply_styles()
        self.statusBar().showMessage("Ready")

        init_db()
        self._load_users()
        self._load_catalog_sources()
        self._refresh_catalog()

    def _build_ui(self) -> None:
        root = QWidget()
        root.setObjectName("appRoot")
        self.setCentralWidget(root)

        shell = QVBoxLayout()
        shell.setContentsMargins(24, 18, 24, 18)
        shell.setSpacing(14)
        root.setLayout(shell)

        shell.addWidget(self._build_header())

        self.tabs = QTabWidget()
        self.tabs.setObjectName("mainTabs")
        shell.addWidget(self.tabs, 1)

        self._build_catalog_tab()
        self._build_explore_tab()
        self._build_wardrobe_tab()
        self._build_outfit_tab()
        self._build_history_tab()

    def _build_header(self) -> QWidget:
        header = QFrame()
        header.setObjectName("heroPanel")

        layout = QVBoxLayout()
        layout.setContentsMargins(22, 18, 22, 18)
        layout.setSpacing(12)
        header.setLayout(layout)

        top_row = QHBoxLayout()
        top_row.setSpacing(14)

        title_block = QVBoxLayout()
        title_block.setSpacing(2)

        title = QLabel("Stylemate")
        title.setObjectName("heroTitle")
        subtitle = QLabel("Fast wardrobe browsing, softer rhythm, less interface friction.")
        subtitle.setObjectName("heroSubtitle")

        title_block.addWidget(title)
        title_block.addWidget(subtitle)
        top_row.addLayout(title_block, 1)

        stats_row = QHBoxLayout()
        stats_row.setSpacing(10)
        self.total_items_badge = self._create_stat_badge("Catalog", "0 items")
        self.sources_badge = self._create_stat_badge("Sources", "0 brands")
        self.page_badge = self._create_stat_badge("Loaded", "0")
        stats_row.addWidget(self.total_items_badge)
        stats_row.addWidget(self.sources_badge)
        stats_row.addWidget(self.page_badge)
        top_row.addLayout(stats_row, 0)

        layout.addLayout(top_row)

        toolbar = QFrame()
        toolbar.setObjectName("toolbarCard")
        toolbar_layout = QHBoxLayout()
        toolbar_layout.setContentsMargins(14, 14, 14, 14)
        toolbar_layout.setSpacing(12)
        toolbar.setLayout(toolbar_layout)

        user_block = QVBoxLayout()
        user_block.setSpacing(6)
        user_block.addWidget(self._label("Current user"))
        self.user_select = QComboBox()
        self.user_select.currentIndexChanged.connect(self._on_user_changed)
        self.user_select.setMinimumWidth(220)
        user_block.addWidget(self.user_select)

        name_block = QVBoxLayout()
        name_block.setSpacing(6)
        name_block.addWidget(self._label("Create profile"))
        self.new_user_input = QLineEdit()
        self.new_user_input.setPlaceholderText("Name your wardrobe profile")
        name_block.addWidget(self.new_user_input)

        self.create_user_button = QPushButton("Create user")
        self.create_user_button.setProperty("variant", "primary")
        self.create_user_button.clicked.connect(self._create_user)
        self.create_user_button.setFixedWidth(150)

        toolbar_layout.addLayout(user_block, 2)
        toolbar_layout.addLayout(name_block, 4)
        toolbar_layout.addWidget(self.create_user_button, 0, Qt.AlignBottom)

        layout.addWidget(toolbar)
        return header

    def _build_catalog_tab(self) -> None:
        tab = QWidget()
        layout = QHBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(18)
        tab.setLayout(layout)

        splitter = QSplitter(Qt.Horizontal)
        splitter.setChildrenCollapsible(False)
        layout.addWidget(splitter)

        left = QWidget()
        left_layout = QVBoxLayout()
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(14)
        left.setLayout(left_layout)

        filters_card = self._make_panel("Catalog browser")
        filters_layout = filters_card.layout()

        self.catalog_summary = QLabel("0 items")
        self.catalog_summary.setObjectName("summaryText")
        filters_layout.addWidget(self.catalog_summary)

        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Search by title, color, category or source")
        self.search_input.textChanged.connect(self._on_catalog_filters_changed)

        self.category_filter = QComboBox()
        self.category_filter.addItems(CATEGORIES)
        self.category_filter.currentIndexChanged.connect(self._on_catalog_filters_changed)

        self.source_filter = QComboBox()
        self.source_filter.currentIndexChanged.connect(self._on_catalog_filters_changed)

        filters_row = QHBoxLayout()
        filters_row.setSpacing(10)
        filters_row.addWidget(self.search_input, 4)
        filters_row.addWidget(self.category_filter, 1)
        filters_row.addWidget(self.source_filter, 1)
        filters_layout.addLayout(filters_row)

        left_layout.addWidget(filters_card)

        list_card = self._make_panel("All pieces")
        list_layout = list_card.layout()

        self.catalog_page_text = QLabel("Loaded 0 of 0")
        self.catalog_page_text.setObjectName("subtleText")
        list_layout.addWidget(self.catalog_page_text)

        self.catalog_list = self._make_product_list()
        self.catalog_list.currentRowChanged.connect(self._on_catalog_item_selected)
        self.catalog_list.verticalScrollBar().valueChanged.connect(self._on_catalog_scrolled)
        list_layout.addWidget(self.catalog_list, 1)

        actions = QHBoxLayout()
        actions.setSpacing(10)
        self.add_to_wardrobe_button = QPushButton("Add to wardrobe")
        self.add_to_wardrobe_button.setProperty("variant", "primary")
        self.add_to_wardrobe_button.clicked.connect(self._add_selected_catalog_item)
        self.open_catalog_item_button = QPushButton("Open in browser")
        self.open_catalog_item_button.setProperty("variant", "secondary")
        self.open_catalog_item_button.clicked.connect(self._open_selected_catalog_item_url)
        actions.addWidget(self.add_to_wardrobe_button)
        actions.addWidget(self.open_catalog_item_button)
        list_layout.addLayout(actions)

        left_layout.addWidget(list_card, 1)

        right = self._build_detail_panel("Selected item", "catalog", self._open_selected_catalog_item_url)

        splitter.addWidget(left)
        splitter.addWidget(right)
        splitter.setSizes([730, 860])

        self.tabs.addTab(tab, "Catalog")

    def _build_explore_tab(self) -> None:
        tab = QWidget()
        layout = QHBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(18)
        tab.setLayout(layout)

        splitter = QSplitter(Qt.Horizontal)
        splitter.setChildrenCollapsible(False)
        layout.addWidget(splitter)

        left_card = self._make_panel("Explore")
        left_layout = left_card.layout()

        self.explore_summary = QLabel("Visual browse of the active catalog selection.")
        self.explore_summary.setObjectName("summaryText")
        left_layout.addWidget(self.explore_summary)

        self.explore_grid = QListWidget()
        self.explore_grid.setObjectName("exploreGrid")
        self.explore_grid.setViewMode(QListWidget.IconMode)
        self.explore_grid.setResizeMode(QListWidget.Adjust)
        self.explore_grid.setMovement(QListWidget.Static)
        self.explore_grid.setWrapping(True)
        self.explore_grid.setSpacing(14)
        self.explore_grid.setGridSize(QSize(258, 352))
        self.explore_grid.setVerticalScrollMode(QAbstractItemView.ScrollPerPixel)
        self.explore_grid.currentRowChanged.connect(self._on_explore_item_selected)
        self.explore_grid.verticalScrollBar().valueChanged.connect(self._on_explore_scrolled)
        left_layout.addWidget(self.explore_grid, 1)

        right = self._build_detail_panel("Explore item", "explore", self._open_selected_explore_item_url)

        splitter.addWidget(left_card)
        splitter.addWidget(right)
        splitter.setSizes([980, 640])

        self.tabs.addTab(tab, "Explore")

    def _build_wardrobe_tab(self) -> None:
        tab = QWidget()
        layout = QHBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(18)
        tab.setLayout(layout)

        splitter = QSplitter(Qt.Horizontal)
        splitter.setChildrenCollapsible(False)
        layout.addWidget(splitter)

        left_card = self._make_panel("My wardrobe")
        left_layout = left_card.layout()

        self.wardrobe_summary = QLabel("Select a user to start building a wardrobe.")
        self.wardrobe_summary.setObjectName("summaryText")
        left_layout.addWidget(self.wardrobe_summary)

        self.wardrobe_list = self._make_product_list()
        self.wardrobe_list.currentRowChanged.connect(self._on_wardrobe_item_selected)
        left_layout.addWidget(self.wardrobe_list, 1)

        actions = QHBoxLayout()
        actions.setSpacing(10)
        self.remove_from_wardrobe_button = QPushButton("Remove")
        self.remove_from_wardrobe_button.setProperty("variant", "secondary")
        self.remove_from_wardrobe_button.clicked.connect(self._remove_selected_wardrobe_item)
        self.open_wardrobe_item_button = QPushButton("Open in browser")
        self.open_wardrobe_item_button.setProperty("variant", "secondary")
        self.open_wardrobe_item_button.clicked.connect(self._open_selected_wardrobe_item_url)
        actions.addWidget(self.remove_from_wardrobe_button)
        actions.addWidget(self.open_wardrobe_item_button)
        left_layout.addLayout(actions)

        right = self._build_detail_panel("Wardrobe piece", "wardrobe", self._open_selected_wardrobe_item_url)

        splitter.addWidget(left_card)
        splitter.addWidget(right)
        splitter.setSizes([720, 860])

        self.tabs.addTab(tab, "My wardrobe")

    def _build_outfit_tab(self) -> None:
        tab = QWidget()
        layout = QHBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(18)
        tab.setLayout(layout)

        splitter = QSplitter(Qt.Horizontal)
        splitter.setChildrenCollapsible(False)
        layout.addWidget(splitter)

        control_card = self._make_panel("Outfit generator")
        control_layout = control_card.layout()

        self.outfit_summary = QLabel("Generate outfit sets from the current wardrobe.")
        self.outfit_summary.setObjectName("summaryText")
        control_layout.addWidget(self.outfit_summary)

        selectors = QHBoxLayout()
        selectors.setSpacing(10)
        self.occasion_select = QComboBox()
        self.occasion_select.addItems(["office", "date", "casual"])
        self.style_select = QComboBox()
        self.style_select.addItems(["minimal", "street", "smart"])
        selectors.addWidget(self.occasion_select)
        selectors.addWidget(self.style_select)
        control_layout.addLayout(selectors)

        self.generate_button = QPushButton("Generate outfits")
        self.generate_button.setProperty("variant", "primary")
        self.generate_button.clicked.connect(self._generate_outfit)
        control_layout.addWidget(self.generate_button)

        self.outfit_variants_list = QListWidget()
        self.outfit_variants_list.setObjectName("variantList")
        self.outfit_variants_list.currentRowChanged.connect(self._on_outfit_variant_selected)
        control_layout.addWidget(self.outfit_variants_list, 1)

        items_card = self._make_panel("Items in selected outfit")
        items_layout = items_card.layout()
        self.outfit_items_list = self._make_product_list()
        self.outfit_items_list.currentRowChanged.connect(self._on_outfit_item_selected)
        items_layout.addWidget(self.outfit_items_list, 1)
        self.open_outfit_item_button = QPushButton("Open in browser")
        self.open_outfit_item_button.setProperty("variant", "secondary")
        self.open_outfit_item_button.clicked.connect(self._open_selected_outfit_item_url)
        items_layout.addWidget(self.open_outfit_item_button)

        right = self._build_detail_panel("Outfit item", "outfit", self._open_selected_outfit_item_url)

        splitter.addWidget(control_card)
        splitter.addWidget(items_card)
        splitter.addWidget(right)
        splitter.setSizes([360, 500, 700])

        self.tabs.addTab(tab, "Outfit generator")

    def _build_history_tab(self) -> None:
        tab = QWidget()
        layout = QHBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(18)
        tab.setLayout(layout)

        splitter = QSplitter(Qt.Horizontal)
        splitter.setChildrenCollapsible(False)
        layout.addWidget(splitter)

        left_card = self._make_panel("Outfit history")
        left_layout = left_card.layout()

        self.history_summary = QLabel("History appears after outfit generation.")
        self.history_summary.setObjectName("summaryText")
        left_layout.addWidget(self.history_summary)

        self.history_list = QListWidget()
        self.history_list.setObjectName("variantList")
        self.history_list.currentRowChanged.connect(self._on_history_selected)
        self.history_items_list = self._make_product_list()
        self.history_items_list.currentRowChanged.connect(self._on_history_item_selected)

        left_layout.addWidget(self._label("Saved outfits"))
        left_layout.addWidget(self.history_list, 1)
        left_layout.addWidget(self._label("Pieces"))
        left_layout.addWidget(self.history_items_list, 1)

        self.open_history_item_button = QPushButton("Open in browser")
        self.open_history_item_button.setProperty("variant", "secondary")
        self.open_history_item_button.clicked.connect(self._open_selected_history_item_url)
        left_layout.addWidget(self.open_history_item_button)

        right = self._build_detail_panel("History item", "history", self._open_selected_history_item_url)

        splitter.addWidget(left_card)
        splitter.addWidget(right)
        splitter.setSizes([760, 820])

        self.tabs.addTab(tab, "Outfit history")

    def _build_detail_panel(self, title: str, prefix: str, open_handler) -> QWidget:
        panel = self._make_panel(title)
        layout = panel.layout()

        content = QHBoxLayout()
        content.setSpacing(20)

        image = AsyncImageLabel()
        setattr(self, f"{prefix}_product_image", image)
        content.addWidget(image, 0, Qt.AlignTop)

        info = QVBoxLayout()
        info.setSpacing(10)

        title_label = QLabel("Title: -")
        title_label.setObjectName("detailTitle")
        setattr(self, f"{prefix}_product_title", title_label)

        category_label = QLabel("Category: -")
        category_label.setObjectName("detailLabel")
        setattr(self, f"{prefix}_product_category", category_label)

        color_label = QLabel("Color: -")
        color_label.setObjectName("detailLabel")
        setattr(self, f"{prefix}_product_color", color_label)

        price_label = QLabel("Price: -")
        price_label.setObjectName("detailPrice")
        setattr(self, f"{prefix}_product_price", price_label)

        source_label = QLabel("Source: -")
        source_label.setObjectName("detailLabel")
        setattr(self, f"{prefix}_product_source", source_label)

        url_box = QTextEdit()
        url_box.setObjectName("urlBox")
        url_box.setReadOnly(True)
        url_box.setFixedHeight(108)
        setattr(self, f"{prefix}_product_url", url_box)

        info.addWidget(title_label)
        info.addWidget(category_label)
        info.addWidget(color_label)
        info.addWidget(price_label)
        info.addWidget(source_label)
        info.addWidget(self._label("URL"))
        info.addWidget(url_box)
        info.addStretch()

        open_button = QPushButton("Open in browser")
        open_button.setProperty("variant", "secondary")
        open_button.clicked.connect(open_handler)
        info.addWidget(open_button, 0, Qt.AlignLeft)

        content.addLayout(info, 1)
        layout.addLayout(content)
        return panel

    def _make_panel(self, title: str) -> QFrame:
        frame = QFrame()
        frame.setObjectName("panel")
        layout = QVBoxLayout()
        layout.setContentsMargins(18, 18, 18, 18)
        layout.setSpacing(14)
        frame.setLayout(layout)

        title_label = QLabel(title)
        title_label.setObjectName("panelTitle")
        layout.addWidget(title_label)
        return frame

    def _make_product_list(self) -> QListWidget:
        widget = QListWidget()
        widget.setObjectName("productList")
        widget.setVerticalScrollMode(QAbstractItemView.ScrollPerPixel)
        widget.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        widget.setSpacing(6)
        return widget

    def _create_stat_badge(self, title: str, value: str) -> QFrame:
        badge = QFrame()
        badge.setObjectName("statBadge")
        layout = QVBoxLayout()
        layout.setContentsMargins(14, 11, 14, 11)
        layout.setSpacing(2)
        badge.setLayout(layout)

        title_label = QLabel(title)
        title_label.setObjectName("statTitle")
        value_label = QLabel(value)
        value_label.setObjectName("statValue")
        layout.addWidget(title_label)
        layout.addWidget(value_label)

        badge.value_label = value_label
        return badge

    def _set_badge_value(self, badge: QFrame, value: str) -> None:
        badge.value_label.setText(value)

    def _label(self, text: str) -> QLabel:
        label = QLabel(text)
        label.setObjectName("fieldLabel")
        return label

    def _apply_styles(self) -> None:
        self.setStyleSheet("""
            QMainWindow, QWidget#appRoot {
                background: qlineargradient(
                    x1: 0, y1: 0, x2: 1, y2: 1,
                    stop: 0 #f8fafc,
                    stop: 0.48 #eef4fb,
                    stop: 1 #f6f8fb
                );
                color: #0f172a;
                font-family: "SF Pro Display", "Helvetica Neue", "Segoe UI", "Arial";
                font-size: 14px;
            }

            QFrame#heroPanel {
                background: qlineargradient(
                    x1: 0, y1: 0, x2: 1, y2: 1,
                    stop: 0 #ffffff,
                    stop: 0.62 #f8fbff,
                    stop: 1 #eef5ff
                );
                border: 1px solid rgba(206, 218, 232, 0.95);
                border-radius: 26px;
            }

            QLabel#heroTitle {
                font-size: 34px;
                font-weight: 700;
                color: #0f172a;
                background: transparent;
            }

            QLabel#heroSubtitle {
                font-size: 14px;
                color: #5b6472;
                background: transparent;
            }

            QFrame#toolbarCard, QFrame#panel, QFrame#statBadge {
                background: rgba(255, 255, 255, 0.84);
                border: 1px solid rgba(214, 223, 233, 0.96);
                border-radius: 24px;
            }

            QFrame#statBadge {
                border-radius: 18px;
            }

            QLabel#statTitle {
                color: #64748b;
                font-size: 12px;
                background: transparent;
            }

            QLabel#statValue {
                color: #0f172a;
                font-size: 18px;
                font-weight: 650;
                background: transparent;
            }

            QLabel#panelTitle {
                font-size: 22px;
                font-weight: 650;
                color: #0f172a;
                background: transparent;
            }

            QLabel#summaryText {
                color: #667085;
                background: transparent;
                font-size: 14px;
            }

            QLabel#subtleText, QLabel#fieldLabel {
                color: #667085;
                background: transparent;
                font-size: 13px;
            }

            QLabel#detailTitle {
                color: #0f172a;
                font-size: 24px;
                font-weight: 650;
                background: transparent;
            }

            QLabel#detailLabel {
                color: #475467;
                font-size: 15px;
                background: transparent;
            }

            QLabel#detailPrice {
                color: #1d4ed8;
                font-size: 22px;
                font-weight: 700;
                background: transparent;
            }

            QLineEdit, QComboBox, QTextEdit {
                background: rgba(252, 253, 255, 0.97);
                color: #0f172a;
                border: 1px solid #d7e0ea;
                border-radius: 18px;
                padding: 11px 14px;
                selection-background-color: #dbeafe;
            }

            QComboBox {
                padding-right: 34px;
            }

            QComboBox::drop-down {
                subcontrol-origin: padding;
                subcontrol-position: top right;
                width: 30px;
                border: none;
                background: transparent;
                border-top-right-radius: 18px;
                border-bottom-right-radius: 18px;
            }

            QComboBox::down-arrow {
                image: none;
                width: 0px;
                height: 0px;
                border-left: 5px solid transparent;
                border-right: 5px solid transparent;
                border-top: 7px solid #64748b;
                margin-right: 10px;
            }

            QComboBox QAbstractItemView {
                background: #ffffff;
                color: #0f172a;
                border: 1px solid #d7e0ea;
                selection-background-color: #dbeafe;
                outline: none;
            }

            QTextEdit#urlBox {
                border-radius: 20px;
            }

            QListWidget#productList, QListWidget#variantList, QListWidget#exploreGrid {
                background: rgba(252, 253, 255, 0.96);
                border: 1px solid #dbe3ec;
                border-radius: 24px;
                padding: 10px;
                outline: none;
            }

            QListWidget::item {
                border: none;
                background: transparent;
                margin: 4px 0;
            }

            QListWidget::item:selected {
                background: #e3efff;
                border-radius: 18px;
            }

            QWidget#productRow {
                background: transparent;
            }

            QWidget#productTile {
                background: rgba(255, 255, 255, 0.88);
                border: 1px solid #dde5ee;
                border-radius: 24px;
            }

            QLabel#thumbLabel {
                background: qlineargradient(
                    x1: 0, y1: 0, x2: 1, y2: 1,
                    stop: 0 #eef5ff,
                    stop: 1 #dcecff
                );
                border: 1px solid #cadcf5;
                border-radius: 22px;
                color: #315789;
                font-size: 12px;
                font-weight: 700;
                letter-spacing: 0.7px;
            }

            QLabel#rowTitle {
                color: #0f172a;
                font-size: 14px;
                font-weight: 650;
                background: transparent;
            }

            QLabel#rowMeta, QLabel#rowSource {
                color: #667085;
                font-size: 12px;
                background: transparent;
            }

            QLabel#rowPrice {
                color: #0f4fd6;
                font-size: 14px;
                font-weight: 700;
                background: transparent;
            }

            QLabel#tileImage {
                background: rgba(247, 250, 252, 0.92);
                border: 1px solid #e1e8f0;
                border-radius: 18px;
                color: #94a3b8;
            }

            QLabel#tileTitle {
                color: #0f172a;
                font-size: 13px;
                font-weight: 650;
                background: transparent;
            }

            QLabel#tileMeta {
                color: #667085;
                font-size: 12px;
                background: transparent;
            }

            QLabel#tilePrice {
                color: #0f4fd6;
                font-size: 14px;
                font-weight: 700;
                background: transparent;
            }

            QLabel#productImage {
                background: rgba(255, 255, 255, 0.92);
                border: 1px solid #dbe3ec;
                border-radius: 30px;
                color: #94a3b8;
            }

            QPushButton {
                border-radius: 18px;
                padding: 12px 18px;
                font-weight: 650;
                border: 1px solid transparent;
            }

            QPushButton[variant="primary"] {
                background: qlineargradient(
                    x1: 0, y1: 0, x2: 1, y2: 0,
                    stop: 0 #0f172a,
                    stop: 1 #334155
                );
                color: white;
            }

            QPushButton[variant="primary"]:hover {
                background: qlineargradient(
                    x1: 0, y1: 0, x2: 1, y2: 0,
                    stop: 0 #111827,
                    stop: 1 #1f2937
                );
            }

            QPushButton[variant="secondary"] {
                background: rgba(255, 255, 255, 0.76);
                color: #0f172a;
                border-color: #d7e0ea;
            }

            QPushButton[variant="secondary"]:hover {
                background: rgba(248, 250, 252, 0.98);
            }

            QPushButton:disabled {
                background: #eaedf2;
                color: #9aa4b2;
                border-color: #e2e8f0;
            }

            QTabWidget::pane {
                border: none;
                top: 0px;
                background: transparent;
            }

            QTabWidget#mainTabs {
                background: transparent;
            }

            QTabWidget#mainTabs > QWidget {
                background: transparent;
            }

            QTabBar::tab {
                background: rgba(255, 255, 255, 0.55);
                color: #64748b;
                border: 1px solid #d6e0ea;
                border-radius: 18px;
                padding: 9px 16px;
                margin-right: 8px;
                margin-bottom: 0px;
            }

            QTabBar::tab:selected {
                background: #ffffff;
                color: #0f172a;
                border-color: #cfd9e5;
            }

            QTabWidget::tab-bar {
                alignment: center;
            }

            QTabBar {
                background: transparent;
            }

            QStatusBar {
                background: rgba(255, 255, 255, 0.72);
                color: #64748b;
                border-top: 1px solid #e2e8f0;
            }
        """)

    def _load_users(self) -> None:
        self.user_select.blockSignals(True)
        self.user_select.clear()

        users = get_all_users()
        for user in users:
            self.user_select.addItem(user["name"], user)

        self.user_select.blockSignals(False)
        self.current_user = users[0] if users else None

        if users:
            self.user_select.setCurrentIndex(0)

        self._load_wardrobe()
        self._load_history()

    def _load_catalog_sources(self) -> None:
        self.catalog_sources = get_catalog_sources()
        self.source_filter.blockSignals(True)
        self.source_filter.clear()
        self.source_filter.addItem("all sources", None)
        for item in self.catalog_sources:
            self.source_filter.addItem(f"{item['source']} ({item['total']})", item["source"])
        self.source_filter.blockSignals(False)
        self._set_badge_value(self.sources_badge, f"{len(self.catalog_sources)} sources")

    def _catalog_filters(self):
        category = self.category_filter.currentText()
        if category == "all":
            category = None
        source = self.source_filter.currentData()
        query = self.search_input.text().strip() or None
        return category, source, query

    def _on_catalog_filters_changed(self) -> None:
        self._refresh_catalog()

    def _refresh_catalog(self) -> None:
        category, source, query = self._catalog_filters()
        self.catalog_total = get_catalog_total(category=category, source=source, query=query)
        self.catalog_items = []
        self.catalog_offset = 0
        self.catalog_has_more = True
        self.catalog_loading_more = False

        self.catalog_list.clear()
        self.explore_grid.clear()

        self.catalog_summary.setText(f"{self.catalog_total} items found")
        self.explore_summary.setText(f"{self.catalog_total} pieces in visual browse")
        self._set_badge_value(self.total_items_badge, f"{self.catalog_total} items")

        self._load_more_catalog_items()

    def _load_more_catalog_items(self) -> None:
        if self.catalog_loading_more or not self.catalog_has_more:
            return

        category, source, query = self._catalog_filters()
        self.catalog_loading_more = True

        batch = get_catalog(
            limit=CATALOG_PAGE_SIZE,
            offset=self.catalog_offset,
            category=category,
            source=source,
            query=query,
        )

        self.catalog_loading_more = False

        if not batch:
            self.catalog_has_more = False
            self.catalog_page_text.setText(f"Loaded {len(self.catalog_items)} of {self.catalog_total}")
            self._set_badge_value(self.page_badge, "complete")
            return

        old_count = len(self.catalog_items)
        self.catalog_items.extend(batch)
        self.catalog_offset += len(batch)
        self.catalog_has_more = self.catalog_offset < self.catalog_total

        for item in batch:
            self._add_product_row(self.catalog_list, item)
            self._add_explore_tile(item)

        self._prefetch_items(batch[:12])

        self.catalog_page_text.setText(f"Loaded {len(self.catalog_items)} of {self.catalog_total}")
        self._set_badge_value(self.page_badge, f"{math.ceil(len(self.catalog_items) / CATALOG_PAGE_SIZE)} chunks")

        if old_count == 0 and self.catalog_items:
            self.catalog_list.setCurrentRow(0)
            self.explore_grid.setCurrentRow(0)

    def _prefetch_items(self, items: list[dict]) -> None:
        loader = get_image_loader()
        for item in items:
            loader.load(item.get("image_url"), kind="thumb")

    def _load_wardrobe(self) -> None:
        self.wardrobe_list.clear()
        self.wardrobe_items = []

        if not self.current_user:
            self.wardrobe_summary.setText("Create or select a user profile to start curating looks.")
            self._clear_wardrobe_details()
            return

        self.wardrobe_items = get_active_wardrobe_for_user(self.current_user["id"])
        self.wardrobe_summary.setText(
            f"{len(self.wardrobe_items)} pieces saved" if self.wardrobe_items else "No saved pieces yet. Add items from Catalog or Explore."
        )

        for item in self.wardrobe_items:
            self._add_product_row(self.wardrobe_list, item)

        if self.wardrobe_items:
            self.wardrobe_list.setCurrentRow(0)
        else:
            self._clear_wardrobe_details()

    def _load_history(self) -> None:
        self.history_list.clear()
        self.history_items_list.clear()

        if not self.current_user:
            self.history_summary.setText("History appears after outfit generation.")
            self._clear_history_details()
            return

        outfits = get_user_outfit_history(self.current_user["id"], limit=20)
        self.history_summary.setText(
            f"{len(outfits)} generated outfits" if outfits else "No history yet. Generate looks to build a timeline."
        )

        for outfit in outfits:
            text = f"v{outfit['version']} • {outfit['occasion']} • {outfit['style']} • score {outfit['score']}"
            row = QListWidgetItem(text)
            row.setData(Qt.UserRole, outfit)
            self.history_list.addItem(row)

        if outfits:
            self.history_list.setCurrentRow(0)
        else:
            self._clear_history_details()

    def _add_product_row(self, list_widget: QListWidget, item: dict) -> None:
        widget = ProductRowWidget(item)
        row = QListWidgetItem()
        row.setSizeHint(QSize(0, 116))
        row.setData(Qt.UserRole, item)
        list_widget.addItem(row)
        list_widget.setItemWidget(row, widget)

    def _add_explore_tile(self, item: dict) -> None:
        widget = ProductTileWidget(item)
        row = QListWidgetItem()
        row.setSizeHint(QSize(248, 336))
        row.setData(Qt.UserRole, item)
        self.explore_grid.addItem(row)
        self.explore_grid.setItemWidget(row, widget)

    def _open_url(self, item: dict | None) -> None:
        if not item:
            QMessageBox.warning(self, "Error", "No item selected")
            return
        if not item.get("url"):
            QMessageBox.warning(self, "Error", "Item has no URL")
            return
        webbrowser.open(item["url"])
        self.statusBar().showMessage(f"Opened: {item.get('title', '-')}", 4000)

    def _open_selected_catalog_item_url(self) -> None:
        self._open_url(self.selected_catalog_item)

    def _open_selected_explore_item_url(self) -> None:
        self._open_url(self.selected_explore_item)

    def _open_selected_wardrobe_item_url(self) -> None:
        self._open_url(self.selected_wardrobe_item)

    def _open_selected_outfit_item_url(self) -> None:
        self._open_url(self.selected_outfit_item)

    def _open_selected_history_item_url(self) -> None:
        self._open_url(self.selected_history_item)

    def _on_user_changed(self, index: int) -> None:
        self.current_user = self.user_select.itemData(index) if index >= 0 else None
        self._load_wardrobe()
        self._load_history()

    def _create_user(self) -> None:
        name = self.new_user_input.text().strip()
        if not name:
            QMessageBox.warning(self, "Error", "Enter user name")
            return

        try:
            create_new_user(name)
        except Exception as error:
            QMessageBox.warning(self, "Error", str(error))
            return

        self.new_user_input.clear()
        self._load_users()
        self.statusBar().showMessage(f"User created: {name}", 4000)

    def _add_selected_catalog_item(self) -> None:
        item = self.selected_catalog_item or self.selected_explore_item
        if not self.current_user:
            QMessageBox.warning(self, "Error", "Select user first")
            return
        if not item:
            QMessageBox.warning(self, "Error", "Select catalog item")
            return

        try:
            add_catalog_item_to_user_wardrobe(self.current_user["id"], item["id"])
        except Exception as error:
            QMessageBox.warning(self, "Error", str(error))
            return

        self._load_wardrobe()
        self.statusBar().showMessage(f"Added: {item['title']}", 4000)

    def _remove_selected_wardrobe_item(self) -> None:
        if not self.current_user or not self.selected_wardrobe_item:
            QMessageBox.warning(self, "Error", "Select wardrobe item")
            return

        try:
            remove_catalog_item_from_user_wardrobe(self.current_user["id"], self.selected_wardrobe_item["id"])
        except Exception as error:
            QMessageBox.warning(self, "Error", str(error))
            return

        self._load_wardrobe()
        self.statusBar().showMessage(f"Removed: {self.selected_wardrobe_item['title']}", 4000)

    def _on_catalog_item_selected(self, row: int) -> None:
        self.selected_catalog_item = self.catalog_items[row] if 0 <= row < len(self.catalog_items) else None
        if self.selected_catalog_item:
            self._show_item_details("catalog", self.selected_catalog_item)
        else:
            self._clear_catalog_details()

    def _on_explore_item_selected(self, row: int) -> None:
        self.selected_explore_item = self.catalog_items[row] if 0 <= row < len(self.catalog_items) else None
        if self.selected_explore_item:
            self._show_item_details("explore", self.selected_explore_item)
        else:
            self._clear_explore_details()

    def _on_wardrobe_item_selected(self, row: int) -> None:
        self.selected_wardrobe_item = self.wardrobe_items[row] if 0 <= row < len(self.wardrobe_items) else None
        if self.selected_wardrobe_item:
            self._show_item_details("wardrobe", self.selected_wardrobe_item)
        else:
            self._clear_wardrobe_details()

    def _on_outfit_item_selected(self, row: int) -> None:
        self.selected_outfit_item = self.current_outfit_items[row] if 0 <= row < len(self.current_outfit_items) else None
        if self.selected_outfit_item:
            self._show_item_details("outfit", self.selected_outfit_item)
        else:
            self._clear_outfit_details()

    def _on_history_selected(self, row: int) -> None:
        self.history_items_list.clear()
        if row < 0:
            self._clear_history_details()
            return

        row_item = self.history_list.item(row)
        outfit = row_item.data(Qt.UserRole) if row_item else None
        if not outfit:
            self._clear_history_details()
            return

        items = get_outfit_details(outfit["id"])
        for item in items:
            self._add_product_row(self.history_items_list, item)

        if items:
            self.history_items_list.setCurrentRow(0)
        else:
            self._clear_history_details()

    def _on_history_item_selected(self, row: int) -> None:
        if row < 0:
            self.selected_history_item = None
            self._clear_history_details()
            return

        row_item = self.history_items_list.item(row)
        self.selected_history_item = row_item.data(Qt.UserRole) if row_item else None
        if self.selected_history_item:
            self._show_item_details("history", self.selected_history_item)
        else:
            self._clear_history_details()

    def _on_outfit_variant_selected(self, row: int) -> None:
        self.outfit_items_list.clear()
        self.current_outfit_items = []

        if row < 0 or row >= len(self.generated_outfits):
            self._clear_outfit_details()
            return

        outfit = self.generated_outfits[row]
        self.current_outfit_items = outfit["items"]

        for item in self.current_outfit_items:
            self._add_product_row(self.outfit_items_list, item)

        if self.current_outfit_items:
            self.outfit_items_list.setCurrentRow(0)

    def _on_catalog_scrolled(self, value: int) -> None:
        scrollbar = self.catalog_list.verticalScrollBar()
        if value >= scrollbar.maximum() - 120:
            self._load_more_catalog_items()

    def _on_explore_scrolled(self, value: int) -> None:
        scrollbar = self.explore_grid.verticalScrollBar()
        if value >= scrollbar.maximum() - 180:
            self._load_more_catalog_items()

    def _generate_outfit(self) -> None:
        if not self.current_user:
            QMessageBox.warning(self, "Error", "Select user first")
            return

        try:
            outfits = generate_outfit_options_for_user(
                self.current_user["id"],
                self.occasion_select.currentText(),
                self.style_select.currentText(),
                limit=3,
            )
        except Exception as error:
            QMessageBox.warning(self, "Error", str(error))
            return

        self.generated_outfits = outfits
        self.outfit_variants_list.clear()
        self.outfit_items_list.clear()

        for index, outfit in enumerate(outfits, start=1):
            preview = ", ".join(item["category"] for item in outfit["items"][:4])
            row = QListWidgetItem(f"Look {index} • score {outfit['score']} • {preview}")
            row.setData(Qt.UserRole, outfit)
            self.outfit_variants_list.addItem(row)

        if outfits:
            self.outfit_variants_list.setCurrentRow(0)
            self.outfit_summary.setText(f"{len(outfits)} outfit options generated")
        else:
            self.outfit_summary.setText("No outfits generated")

        self._load_history()

    def _show_item_details(self, prefix: str, item: dict) -> None:
        getattr(self, f"{prefix}_product_title").setText(item.get("title") or "-")
        getattr(self, f"{prefix}_product_category").setText(f"Category: {item.get('category') or '-'}")
        getattr(self, f"{prefix}_product_color").setText(f"Color: {item.get('color') or '-'}")
        getattr(self, f"{prefix}_product_price").setText(format_price(item.get("price"), item.get("currency")))
        getattr(self, f"{prefix}_product_source").setText(f"Source: {item.get('source') or '-'}")
        getattr(self, f"{prefix}_product_url").setPlainText(item.get("url") or "")
        getattr(self, f"{prefix}_product_image").set_image_from_url(item.get("image_url"))

    def _clear_item_details(self, prefix: str) -> None:
        getattr(self, f"{prefix}_product_title").setText("Title: -")
        getattr(self, f"{prefix}_product_category").setText("Category: -")
        getattr(self, f"{prefix}_product_color").setText("Color: -")
        getattr(self, f"{prefix}_product_price").setText("Price: -")
        getattr(self, f"{prefix}_product_source").setText("Source: -")
        getattr(self, f"{prefix}_product_url").setPlainText("")
        getattr(self, f"{prefix}_product_image").set_image_from_url(None)

    def _clear_catalog_details(self) -> None:
        self._clear_item_details("catalog")

    def _clear_explore_details(self) -> None:
        self._clear_item_details("explore")

    def _clear_wardrobe_details(self) -> None:
        self._clear_item_details("wardrobe")

    def _clear_outfit_details(self) -> None:
        self._clear_item_details("outfit")

    def _clear_history_details(self) -> None:
        self._clear_item_details("history")


def main() -> None:
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
