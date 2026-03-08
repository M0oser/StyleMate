from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse
from pydantic import BaseModel
from typing import List

# Импортируем функции из наших сервисов
from backend.services.db_crud import search_products
from backend.services.outfit_generator import load_wardrobe_from_db, generate_outfits, SCENARIOS, STYLES

app = FastAPI(title="StyleMate API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Модель запроса для генерации лука
class OutfitRequest(BaseModel):
    scenario: str
    style: str
    count: int = 3

# Монтируем папку с фронтендом как статику
app.mount("/static", StaticFiles(directory="frontend_tma"), name="static")

@app.get("/", response_class=HTMLResponse)
async def root():
    # Читаем и отдаем наш index.html прямо из корня
    with open("frontend_tma/index.html", "r", encoding="utf-8") as f:
        return f.read()


@app.get("/health")
async def health_check():
    return {"status": "ok", "message": "StyleMate Backend is running!"}

@app.get("/api/wardrobe", response_model=List[dict])
async def get_wardrobe(limit: int = 50):
    try:
        rows = search_products(query="", limit=limit, db_path="products.db")
        items = []
        for (pid, source, title, price, url, image_url, cat, col) in rows:
            items.append({
                "id": pid, "title": title, "price": price, 
                "url": url, "image_url": image_url, 
                "category": cat, "color": col
            })
        return items
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/upload_clothing")
async def upload_clothing():
    # Заглушка для Артема
    return {"status": "success", "item_type": "jeans", "color": "blue"}

@app.post("/api/generate_outfits")
async def api_generate_outfits(req: OutfitRequest):
    if req.scenario not in SCENARIOS or req.style not in STYLES:
        raise HTTPException(status_code=400, detail="Invalid scenario or style. Проверьте правильность написания.")

    # Берем гардероб из БД
    wardrobe = load_wardrobe_from_db(db_path="products.db")
    if not wardrobe:
        raise HTTPException(status_code=404, detail="Wardrobe is empty")

    # Убираем аксессуары, чтобы они не ломали базовую логику Зи
    wardrobe_view = [x for x in wardrobe if x.cat != "accessory"]

    # Генерируем луки
    outfits = generate_outfits(wardrobe_view, req.scenario, req.style, k=req.count)

    # Преобразуем ответ для фронтенда
    result = []
    for score, outfit_items in outfits:
        items_dict = [{"id": i.id, "title": i.title, "category": i.cat, "color": i.color, "price": i.price} for i in outfit_items]
        result.append({
            "score": score,
            "items": items_dict
        })

    return {"scenario": req.scenario, "style": req.style, "outfits": result}
