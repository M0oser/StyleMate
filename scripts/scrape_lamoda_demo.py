import os
import re
import time
import random
from typing import List, Optional
import requests
from bs4 import BeautifulSoup

from db import Product, init_db, upsert_products

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"
}

def parse_price(text: str) -> Optional[int]:
    # "12 990 ₽" -> 12990
    digits = re.sub(r"[^\d]", "", text)
    return int(digits) if digits else None

def parse_lamoda_listing_html(html: str, source: str = "lamoda") -> List[Product]:
    soup = BeautifulSoup(html, "lxml")
    products: List[Product] = []

    # 1) Найдём все узлы, где встречается ₽ (обычно это цена в карточке)
    price_nodes = soup.find_all(string=lambda s: isinstance(s, str) and "₽" in s)

    def norm_url(href: str) -> str:
        href = href.strip()
        if href.startswith("http"):
            return href
        return "https://www.lamoda.ru" + href

    seen_urls = set()

    # ограничим, чтобы не схватить мусор с футера/хедера
    for pn in price_nodes:
        # 2) Поднимаемся вверх по DOM, пытаемся найти "контейнер карточки"
        container = pn.parent
        for _ in range(8):
            if container is None:
                break
            # карточка обычно содержит и img и ссылку
            has_link = container.select_one("a[href]") is not None
            has_img = container.select_one("img") is not None
            if has_link and has_img:
                break
            container = container.parent

        if container is None:
            continue

        # 3) URL: берём самую "похожую" ссылку (эвристика: длина href, наличие 'product')
        links = container.select("a[href]")
        if not links:
            continue

        # выберем лучшую ссылку
        best_a = None
        best_score = -1
        for a in links:
            href = a.get("href", "")
            if not href:
                continue
            score = 0
            h = href.lower()
            if "product" in h:
                score += 5
            if "catalogsearch" in h:
                score -= 3
            score += min(len(href), 120) / 60  # длиннее = чаще конкретный товар
            # если внутри есть картинка — скорее всего это карточка
            if a.select_one("img"):
                score += 2
            if score > best_score:
                best_score = score
                best_a = a

        if best_a is None:
            continue

        url = norm_url(best_a.get("href"))
        if url in seen_urls:
            continue

        # 4) Title: сначала aria-label/title, потом текст контейнера
        title = (best_a.get("aria-label") or best_a.get("title") or "").strip()
        if not title:
            # попробуем найти любой "плотный" текст в контейнере
            text = container.get_text(" ", strip=True)
            # выкинем саму цену из текста
            text = text.replace(str(pn).strip(), "").strip()
            # чистка
            title = text[:120].strip()

        if not title or len(title) < 5:
            continue

        # 5) Price: берём ближайший текст с ₽ из контейнера (обычно первый нормальный)
        text_blob = container.get_text(" ", strip=True)
        price = parse_price(text_blob) if "₽" in text_blob else None

        # 6) Image
        img = container.select_one("img")
        image_url = None
        if img:
            image_url = img.get("src") or img.get("data-src")
            # иногда srcset: "url 1x, url 2x"
            if not image_url and img.get("srcset"):
                image_url = img.get("srcset").split(",")[0].split()[0]

        products.append(Product(
            source=source,
            title=title,
            price=price,
            url=url,
            image_url=image_url,
            category=None,
            color=None
        ))
        seen_urls.add(url)

    return products
def fetch(url: str) -> str:
    r = requests.get(url, headers=HEADERS, timeout=20)
    r.raise_for_status()
    return r.text

def main():
    init_db()

    mode = os.environ.get("MODE", "offline")  # offline | online
    collected = 0

    if mode == "offline":
        # Самый надежный путь: заранее сохрани HTML страниц в папку html_pages/
        folder = os.environ.get("HTML_DIR", "html_pages")
        if not os.path.isdir(folder):
            raise SystemExit(f"Нет папки {folder}. Создай её и положи туда .html файлы.")

        for fn in os.listdir(folder):
            if not fn.endswith(".html"):
                continue
            path = os.path.join(folder, fn)
            with open(path, "r", encoding="utf-8", errors="ignore") as f:
                html = f.read()

            products = parse_lamoda_listing_html(html)
            inserted = upsert_products(products)
            collected += inserted
            print(f"[{fn}] parsed={len(products)} inserted={inserted} total_inserted={collected}")

    else:
        # Онлайн режим — только для "один раз собрать" и не для защиты
        # Пример: парсим несколько поисковых страниц
        queries = ["тренч бежевый", "лоферы черные", "джинсы синие"]
        pages_per_query = 2

        for q in queries:
            for page in range(1, pages_per_query + 1):
                # ВАЖНО: URL поиска тут примерный. Подставь реальный.
                url = f"https://www.lamoda.ru/catalogsearch/result/?q={requests.utils.quote(q)}&page={page}"
                try:
                    html = fetch(url)
                except Exception as e:
                    print("fetch failed:", url, e)
                    continue

                products = parse_lamoda_listing_html(html)
                inserted = upsert_products(products)
                collected += inserted
                print(f"[{q} p{page}] parsed={len(products)} inserted={inserted} total_inserted={collected}")

                time.sleep(random.uniform(1.0, 2.5))

    print("DONE. Inserted:", collected)
    print("DB:", "products.db")

if __name__ == "__main__":
    main()