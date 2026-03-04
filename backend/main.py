from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="StyleMate API")

# Разрешаем запросы с фронтенда (CORS)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # Для продакшена поменяем на конкретные домены
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/health")
async def health_check():
    return {"status": "ok", "message": "StyleMate Backend is running!"}

@app.post("/api/upload_clothing")
async def upload_clothing():
    # Заглушка: сюда позже добавим обработку фото и вызов Vision-модели
    return {"status": "success", "item_type": "jeans", "color": "blue"}
