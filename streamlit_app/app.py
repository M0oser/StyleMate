import os
import re
import sqlite3
import random
from dataclasses import dataclass
from typing import List, Optional, Dict, Tuple

import streamlit as st

DB_PATH = "products.db"

# -----------------------------
# Heuristics: color extraction
# -----------------------------
COLOR_SYNONYMS = {
    "black": ["black", "dark", "noir", "nero", "черн", "чёрн"],
    "white": ["white", "ivory", "snow", "бел"],
    "gray": ["gray", "grey", "silver", "сер", "графит"],
    "navy": ["navy", "midnight", "темно-син", "тёмно-син"],
    "blue": ["blue", "denim", "син", "голуб"],
    "beige": ["beige", "camel", "sand", "cream", "беж", "песоч"],
    "brown": ["brown", "chocolate", "кофе", "корич"],
    "red": ["red", "burgundy", "wine", "красн", "бордо"],
    "green": ["green", "olive", "khaki", "зел", "олив", "хаки"],
    "pink": ["pink", "rose", "fuchsia", "роз", "фукс"],
    "purple": ["purple", "lilac", "violet", "фиол", "лилов"],
    "yellow": ["yellow", "mustard", "желт", "горч"],
    "orange": ["orange", "terracotta", "оранж", "терракот"],
}

NEUTRALS = {"black", "white", "gray", "navy", "beige", "brown"}
BRIGHTS = {"red", "yellow", "orange", "pink", "purple", "green", "blue"}

def infer_color(title: str, fallback: Optional[str]) -> Optional[str]:
    if fallback and isinstance(fallback, str) and fallback.strip():
        return fallback.strip().lower()

    t = (title or "").lower()
    for color, keys in COLOR_SYNONYMS.items():
        if any(k in t for k in keys):
            return color
    return None

# -----------------------------
# Category normalization
# -----------------------------
WARDROBE_CATS = [
    "tshirt","shirt","hoodie","sweater",
    "jeans","trousers","pants","shorts","skirt",
    "sneakers","boots","loafers","shoes",
    "jacket","coat","blazer",
    "accessory"
]

def normalize_category(raw_category: Optional[str], title: str) -> str:
    """
    Пытаемся привести category магазина к нашим типам.
    Если category в БД не “одежная” (как в dummyjson), вытаскиваем по title.
    """
    rc = (raw_category or "").lower().strip()
    t = (title or "").lower()

    # 1) по title (надежнее для одежды)
    if any(k in t for k in ["t-shirt", "tshirt", "tee", "футбол", "футб"]):
        return "tshirt"
    if any(k in t for k in ["shirt", "рубаш", "сороч"]):
        return "shirt"
    if any(k in t for k in ["hoodie", "худи"]):
        return "hoodie"
    if any(k in t for k in ["sweater", "jumper", "свитер", "джемпер"]):
        return "sweater"

    if any(k in t for k in ["jean", "джинс", "denim"]):
        return "jeans"
    if any(k in t for k in ["trouser", "slacks", "брюк"]):
        return "trousers"
    if any(k in t for k in ["pants", "штаны"]):
        return "pants"
    if any(k in t for k in ["shorts", "шорт"]):
        return "shorts"
    if any(k in t for k in ["skirt", "юбк"]):
        return "skirt"

    if any(k in t for k in ["sneaker", "кросс", "runner"]):
        return "sneakers"
    if any(k in t for k in ["boot", "ботин", "сапог"]):
        return "boots"
    if any(k in t for k in ["loafer", "лофер"]):
        return "loafers"
    if any(k in t for k in ["shoe", "туфл", "дерби", "оксфорд"]):
        return "shoes"

    if any(k in t for k in ["coat", "пальто", "trench", "тренч", "overcoat"]):
        # тренч/пальто обычно coat
        return "coat"
    if any(k in t for k in ["jacket", "куртк", "ветровк", "бомбер"]):
        return "jacket"
    if any(k in t for k in ["blazer", "пиджак", "жакет"]):
        return "blazer"

    if any(k in t for k in ["belt", "ремень", "cap", "hat", "шапк", "bag", "сумк", "scarf", "шарф"]):
        return "accessory"

    # 2) по raw category (если оно хотя бы что-то значит)
    # (для других магазинов можно расширить)
    if rc in WARDROBE_CATS:
        return rc

    return "accessory"  # безопасный дефолт

# -----------------------------
# Outfit rules + scenarios + style
# -----------------------------
SCENARIOS = {
    "Офис": {
        "required_any": [["shirt","blazer"], ["trousers","pants","skirt"], ["loafers","shoes"]],
        "avoid": ["shorts","hoodie"],
        "outer_bias": ["blazer", "coat"],
        "note": "Формальнее: рубашка/пиджак, спокойные цвета, закрытая обувь."
    },
    "Свидание": {
        "required_any": [["tshirt","shirt","sweater","hoodie"], ["jeans","trousers","pants","skirt"]],
        "avoid": [],
        "outer_bias": ["jacket", "coat"],
        "note": "Аккуратный силуэт; можно 1 яркий акцент."
    },
    "Прогулка в дождь": {
        "required_any": [["jacket","coat"], ["boots","sneakers"]],
        "avoid": ["loafers"],
        "outer_bias": ["coat", "jacket"],
        "note": "Верхняя одежда обязательна, обувь лучше закрытая."
    },
}

STYLES = {
    "Minimal": {
        "prefer_colors": ["black","white","gray","navy","beige"],
        "allow_bright_accents": 0,
        "note": "Минимализм: нейтралы, без лишних акцентов."
    },
    "Casual": {
        "prefer_colors": None,  # любой
        "allow_bright_accents": 1,
        "note": "Кэжуал: нейтралы + 1 яркий акцент допустим."
    },
    "Street": {
        "prefer_colors": None,
        "allow_bright_accents": 2,
        "note": "Стрит: допускается больше контраста и акцентов."
    },
}

def color_score(colors: List[Optional[str]], style_key: str) -> int:
    colors = [c for c in colors if c]
    if not colors:
        return 0

    rule = STYLES[style_key]
    allow = rule["allow_bright_accents"]

    bright_count = sum(1 for c in colors if c in BRIGHTS and c != "navy")
    neutral_count = sum(1 for c in colors if c in NEUTRALS)

    score = neutral_count * 2
    score -= max(0, bright_count - allow) * 3

    prefer = rule["prefer_colors"]
    if prefer:
        score += sum(1 for c in colors if c in prefer)

    return score

@dataclass
class WardrobeItem:
    id: int
    title: str
    price: Optional[int]
    url: str
    image_url: Optional[str]
    raw_category: Optional[str]
    raw_color: Optional[str]
    cat: str
    color: Optional[str]

def load_wardrobe_from_db(limit: int = 2000) -> List[WardrobeItem]:
    if not os.path.exists(DB_PATH):
        return []

    con = sqlite3.connect(DB_PATH)
    cur = con.cursor()

    # ожидаем таблицу products как в нашем предыдущем db.py
    cur.execute("""
        SELECT id, title, price, url, image_url, category, color
        FROM products
        LIMIT ?
    """, (limit,))
    rows = cur.fetchall()
    con.close()

    items: List[WardrobeItem] = []
    for (pid, title, price, url, image_url, category, color) in rows:
        cat = normalize_category(category, title)
        col = infer_color(title, color)
        items.append(WardrobeItem(
            id=pid,
            title=title,
            price=price,
            url=url,
            image_url=image_url,
            raw_category=category,
            raw_color=color,
            cat=cat,
            color=col
        ))
    return items

def pick_one(pool: List[WardrobeItem], cats: List[str]) -> Optional[WardrobeItem]:
    candidates = [x for x in pool if x.cat in cats]
    return random.choice(candidates) if candidates else None

def generate_outfits(pool: List[WardrobeItem], scenario: str, style: str, k: int = 5) -> List[Tuple[int, List[WardrobeItem]]]:
    rules = SCENARIOS[scenario]
    results: List[Tuple[int, List[WardrobeItem]]] = []

    for _ in range(350):
        outfit: List[WardrobeItem] = []

        top = pick_one(pool, ["tshirt","shirt","hoodie","sweater"])
        bottom = pick_one(pool, ["jeans","trousers","pants","shorts","skirt"])
        shoes = pick_one(pool, ["sneakers","boots","loafers","shoes"])

        if top: outfit.append(top)
        if bottom: outfit.append(bottom)
        if shoes: outfit.append(shoes)

        # outerwear bias
        outer = pick_one(pool, ["jacket","coat","blazer"])
        if scenario in ("Офис", "Прогулка в дождь"):
            if outer:
                outfit.append(outer)
        else:
            if outer and random.random() < 0.35:
                outfit.append(outer)

        if len(outfit) < 3:
            continue

        # avoid
        if any(it.cat in rules["avoid"] for it in outfit):
            continue

        # required_any
        ok = True
        for group in rules["required_any"]:
            if not any(it.cat in group for it in outfit):
                ok = False
                break
        if not ok:
            continue

        # scoring
        colors = [it.color for it in outfit]
        score = color_score(colors, style)

        # diversity bonus
        score += len(set(it.cat for it in outfit))

        # outer bias bonus
        score += sum(1 for it in outfit if it.cat in rules.get("outer_bias", []))

        results.append((score, outfit))

    # dedup by product ids
    seen = set()
    uniq: List[Tuple[int, List[WardrobeItem]]] = []
    for score, outfit in sorted(results, key=lambda x: x[0], reverse=True):
        key = tuple(sorted(it.id for it in outfit))
        if key in seen:
            continue
        seen.add(key)
        uniq.append((score, outfit))
        if len(uniq) >= k:
            break
    return uniq

# -----------------------------
# Streamlit UI
# -----------------------------
st.set_page_config(page_title="Wardrobe MVP (DB-only)", layout="wide")
st.title("👔 Гардероб из БД → генерация образов (без загрузки фото)")

if not os.path.exists(DB_PATH):
    st.error(f"Не найден файл {DB_PATH} рядом с app.py. Положи products.db в папку проекта.")
    st.stop()

wardrobe = load_wardrobe_from_db(limit=5000)
if not wardrobe:
    st.error("В products.db нет строк в таблице products, либо структура другая.")
    st.stop()

# quick stats
cats_count: Dict[str, int] = {}
for it in wardrobe:
    cats_count[it.cat] = cats_count.get(it.cat, 0) + 1

with st.expander("📊 Что программа видит в твоём гардеробе (из БД)", expanded=False):
    st.write(f"Всего вещей: **{len(wardrobe)}**")
    st.write("Категории (нормализованные):")
    st.json(dict(sorted(cats_count.items(), key=lambda x: -x[1])))

st.subheader("Выбор мероприятия и стиля")
col1, col2, col3 = st.columns([1,1,1])
with col1:
    scenario = st.selectbox("Мероприятие", list(SCENARIOS.keys()), index=0)
with col2:
    style = st.selectbox("Стиль", list(STYLES.keys()), index=1)
with col3:
    n = st.slider("Сколько образов", 1, 10, 5)

st.caption(f"Сценарий: {SCENARIOS[scenario]['note']}  |  Стиль: {STYLES[style]['note']}")

# optional filter to make demo nicer
with st.expander("Фильтр гардероба для демо (необязательно)", expanded=False):
    allow_accessory = st.checkbox("Разрешить аксессуары в подборе", value=False)
    max_items = st.slider(
        "Ограничить размер гардероба (ускорить)",
        50,
        min(2000, len(wardrobe)),
        min(800, len(wardrobe))
    )

    if not allow_accessory:
        wardrobe_view = [x for x in wardrobe if x.cat != "accessory"]
    else:
        wardrobe_view = wardrobe[:]

    wardrobe_view = wardrobe_view[:max_items]
    st.write(f"В подборе участвует: **{len(wardrobe_view)}** вещей")

# значение по умолчанию (если пользователь не открывал expander)
if "wardrobe_view" not in locals():
    wardrobe_view = [x for x in wardrobe if x.cat != "accessory"]

if st.button("✨ Сгенерировать образы"):
    outfits = generate_outfits(wardrobe_view, scenario, style, k=n)

    if not outfits:
        st.warning(
            "Не удалось собрать образы по правилам. "
            "Скорее всего в гардеробе мало нужных категорий (например обуви/верхней одежды)."
        )
    else:
        for idx, (score, outfit) in enumerate(outfits, 1):
            st.markdown(f"### Образ {idx} — score `{score}`")
            for it in outfit:
                price_txt = f"{it.price}" if it.price is not None else "—"
                st.write(f"- **{it.title}**  · `{it.cat}` · цвет: `{it.color or 'unknown'}` · цена: `{price_txt}`")
                # ссылку оставим как "товар"
                if it.url:
                    st.write(it.url)
            st.divider()