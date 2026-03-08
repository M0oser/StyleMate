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
from backend.services.rag_agent import generate_outfit_via_llm

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
    # 1. Берем гардероб из БД
    wardrobe = load_wardrobe_from_db(db_path="products.db")
    if not wardrobe:
        raise HTTPException(status_code=404, detail="Wardrobe is empty")

    # Убираем аксессуары, берем только основные вещи (ограничиваем до 100)
    wardrobe_view = [{"id": x.id, "title": x.title, "category": x.cat, "color": x.color, "price": x.price, "image_url": x.image_url} for x in wardrobe if x.cat != "accessory"][:100]

    # 2. ПРОСИМ НЕЙРОСЕТЬ СОБРАТЬ ЛУК (RAG)
    print(f"Отправляю запрос в Qwen... Сценарий: {req.scenario}")
    llm_response = generate_outfit_via_llm(wardrobe_view, req.scenario, req.style)
    
    # 3. Достаем вещи по ID, которые вернула нейросеть
    selected_ids = llm_response.get("item_ids", [])
    outfit_items = [item for item in wardrobe_view if item["id"] in selected_ids]
    
    # Если нейросеть ничего не вернула (сбой), отдаем хотя бы одну заглушку, чтобы фронт не падал
    if not outfit_items:
        print("Внимание: Нейросеть не смогла собрать лук, отдаем fallback")
        # Берем первые 3 вещи из базы просто как резервный вариант
        outfit_items = wardrobe_view[:3]
        explanation = "Нейросеть устала, вот случайные вещи из твоего гардероба."
    else:
        explanation = llm_response.get("explanation", "Мой выбор для тебя")

    # 4. Формируем ответ для фронтенда
    result = [{
        "score": 100, 
        "explanation": explanation, # Добавили поле с текстом нейросети
        "items": outfit_items       # Фронтенд Ильяса ждет массив словарей именно здесь
    }]

    return {"scenario": req.scenario, "style": req.style, "outfits": result}

