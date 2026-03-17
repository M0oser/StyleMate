from fastapi import FastAPI, HTTPException, File, UploadFile
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List
import httpx
import sqlite3
import os
import uuid
from dotenv import load_dotenv
load_dotenv()

# Импортируем функции из наших сервисов
from backend.services.outfit_generator import load_wardrobe_from_db, insert_user_wardrobe_item
from backend.services.rag_agent import generate_outfit_via_llm

app = FastAPI(title="StyleMate API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class OutfitRequest(BaseModel):
    scenario: str
    style: str
    count: int = 1

app.mount("/static", StaticFiles(directory="frontend_tma"), name="static")

@app.get("/", response_class=HTMLResponse)
async def root():
    with open("frontend_tma/index.html", "r", encoding="utf-8") as f:
        return f.read()

@app.get("/health")
async def health_check():
    return {"status": "ok", "message": "StyleMate Backend is running!"}

@app.post("/api/generate_outfits")
async def api_generate_outfits(req: OutfitRequest):
    wardrobe = load_wardrobe_from_db(db_path="database/wardrobe.db")
    if not wardrobe:
        raise HTTPException(status_code=404, detail="Wardrobe is empty")

    wardrobe_view = [{"id": x.id, "title": x.title, "category": x.cat, "color": x.color, "price": x.price, "image_url": x.image_url} for x in wardrobe if x.cat != "accessory"][:100]

    print(f"Отправляю запрос в Qwen... Сценарий: {req.scenario}")
    llm_response = generate_outfit_via_llm(wardrobe_view, req.scenario, req.style)
    
    selected_ids = llm_response.get("item_ids", [])
    outfit_items = [item for item in wardrobe_view if item["id"] in selected_ids]
    
    if not outfit_items:
        print("Внимание: Нейросеть не смогла собрать лук, отдаем fallback")
        outfit_items = wardrobe_view[:3]
        explanation = "Нейросеть устала, вот случайные вещи из твоего гардероба."
    else:
        explanation = llm_response.get("explanation", "Мой выбор для тебя")

    result = [{
        "score": 100, 
        "explanation": explanation,
        "items": outfit_items
    }]

    return {"scenario": req.scenario, "style": req.style, "outfits": result}
@app.get("/api/my_wardrobe")
async def get_my_wardrobe():
    """Возвращает вещи, которые пользователь загрузил сам."""
    try:
        con = sqlite3.connect("database/wardrobe.db")
        cur = con.cursor()
        # Берем данные из личной таблицы пользователя
        cur.execute("SELECT id, title, category, color, image_url FROM user_wardrobe ORDER BY id DESC")
        rows = cur.fetchall()
        con.close()
        
        items = []
        for r in rows:
            items.append({
                "id": r[0],
                "title": r[1],
                "category": r[2],
                "color": r[3],
                "image_url": r[4]
            })
        return items
    except Exception as e:
        print(f"Ошибка при получении гардероба: {e}")
        return []
    
import os
import uuid # Добавь в импорты наверху, если нет

@app.post("/api/upload_clothing")
async def upload_clothing(file: UploadFile = File(...)):
    ARTEM_MICROSERVICE_URL = "http://rysgm-185-122-185-121.a.free.pinggy.link/"
    
    try:
        # 1. Читаем файл
        image_bytes = await file.read()
        
        # 2. Сохраняем файл локально, чтобы его можно было показать во фронтенде!
        # Генерируем уникальное имя, чтобы файлы не перезаписывали друг друга
        file_ext = file.filename.split('.')[-1] if '.' in file.filename else 'jpg'
        unique_filename = f"{uuid.uuid4().hex}.{file_ext}"
        save_path = os.path.join("frontend_tma", "uploads", unique_filename)
        
        with open(save_path, "wb") as f:
            f.write(image_bytes)
            
        # Формируем публичную ссылку, по которой фронтенд сможет открыть эту картинку
        public_image_url = f"/static/uploads/{unique_filename}"
        
        # 3. Отправляем картинку Артему для анализа
        print(f"Отправляю картинку '{unique_filename}' на 5070 Ti Артему...")
        async with httpx.AsyncClient() as client:
            files = {'file': (file.filename, image_bytes, file.content_type)}
            response = await client.post(
                ARTEM_MICROSERVICE_URL, 
                files=files, 
                timeout=60.0,
                follow_redirects=True
            )
            
            if response.status_code != 200:
                print(f"Сервер Артема вернул ошибку: {response.text}")
                # Даже если Артем недоступен, мы всё равно сохраняем вещь с картинкой!
                insert_user_wardrobe_item(title="Новая вещь", category="unknown", color="unknown", image_url=public_image_url)
                return {"status": "success", "message": "Сохранено без ИИ"}
                
            ai_data = response.json()
            
            # 4. Сохраняем в БД ВМЕСТЕ С КАРТИНКОЙ
            cat = ai_data.get('category', 'clothes')
            col = ai_data.get('color', 'unknown')
            new_title = f"{str(col).capitalize()} {str(cat).capitalize()}"
            
            insert_user_wardrobe_item(title=new_title, category=cat, color=col, image_url=public_image_url)
            print("Вещь с картинкой успешно сохранена в базу!")
            
            return {
                "status": "success",
                "message": "Успешно распознано и добавлено!",
                "ai_analysis": ai_data
            }
            
    except Exception as e:
        print(f"Ошибка: {e}")
        return {"status": "error", "message": "Сбой сервера."}
