import os
import uuid
import sqlite3
from typing import Optional

import httpx
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, File, UploadFile, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from backend.services.outfit_generator import (
    clear_user_wardrobe,
    delete_user_wardrobe_items,
    ensure_user_wardrobe_schema,
    normalize_owner_token,
    load_wardrobe_from_db,
    insert_user_wardrobe_item,
    update_user_wardrobe_item,
)
from backend.services.rag_agent import generate_outfit_via_llm
from backend.services.vision_service import analyze_uploaded_clothing

load_dotenv(override=True)
ensure_user_wardrobe_schema()

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
    gender: str = "male"
    count: int = 1
    source_mode: str = "mixed"


class WardrobeItemUpdateRequest(BaseModel):
    title: str
    category: str
    color: str
    style: str = "unknown"


class WardrobeDeleteRequest(BaseModel):
    item_ids: list[int]


def _get_owner_token(request: Request, required: bool = True) -> Optional[str]:
    owner_token = normalize_owner_token(request.headers.get("X-Owner-Token"))

    if required and not owner_token:
        raise HTTPException(status_code=400, detail="Missing X-Owner-Token header")

    return owner_token


app.mount("/static", StaticFiles(directory="frontend_tma"), name="static")


@app.get("/", response_class=HTMLResponse)
async def root():
    with open("frontend_tma/index.html", "r", encoding="utf-8") as f:
        return HTMLResponse(
            content=f.read(),
            headers={
                "Cache-Control": "no-store, no-cache, must-revalidate, max-age=0",
                "Pragma": "no-cache",
                "Expires": "0",
            },
        )


@app.get("/health")
async def health_check():
    return {"status": "ok", "message": "StyleMate Backend is running!"}


@app.post("/api/generate_outfits")
async def api_generate_outfits(req: OutfitRequest, request: Request):
    owner_token = _get_owner_token(request, required=req.source_mode in {"user", "mixed"})

    wardrobe = load_wardrobe_from_db(
        db_path="database/wardrobe.db",
        source_mode=req.source_mode,
        limit=2000,
        owner_token=owner_token,
    )

    if not wardrobe:
        raise HTTPException(status_code=404, detail="Wardrobe is empty")

    wardrobe_view = [
        {
            "id": x.id,
            "title": x.title,
            "category": x.cat,
            "color": x.color,
            "price": x.price,
            "image_url": x.image_url,
            "url": x.url,
            "source": x.source,
        }
        for x in wardrobe
        if x.cat != "accessory"
    ]

    print(
        f"[API] generate_outfits scenario={req.scenario} "
        f"style={req.style} gender={req.gender} source_mode={req.source_mode}"
    )
    print("[API] wardrobe_view categories:", [item["category"] for item in wardrobe_view])

    llm_response = generate_outfit_via_llm(wardrobe_view, req.scenario, req.style, req.gender)

    outfit_items = llm_response.get("items", [])
    explanation = llm_response.get("explanation", "Мой выбор для тебя")

    if not outfit_items:
        print("[API] Подходящий лук не найден. Возвращаем пустой результат без случайного fallback.")
        return {
            "scenario": req.scenario,
            "style": req.style,
            "gender": req.gender,
            "source_mode": req.source_mode,
            "outfits": [{
                "score": 0,
                "explanation": explanation,
                "items": []
            }]
        }

    result = [{
        "score": 100,
        "explanation": explanation,
        "items": outfit_items
    }]

    return {
        "scenario": req.scenario,
        "style": req.style,
        "gender": req.gender,
        "source_mode": req.source_mode,
        "outfits": result
    }


@app.get("/api/my_wardrobe")
async def get_my_wardrobe(request: Request):
    owner_token = _get_owner_token(request)

    try:
        ensure_user_wardrobe_schema()
        con = sqlite3.connect("database/wardrobe.db")
        cur = con.cursor()
        cur.execute("""
            SELECT id, title, category, color, image_url, style, vision_source, manually_edited
            FROM user_wardrobe
            WHERE owner_token = ?
            ORDER BY id DESC
        """, (owner_token,))
        rows = cur.fetchall()
        con.close()

        items = []
        for r in rows:
            items.append({
                "id": r[0],
                "title": r[1],
                "category": r[2],
                "color": r[3],
                "image_url": r[4],
                "style": r[5],
                "vision_source": r[6],
                "manually_edited": bool(r[7]),
            })
        return items
    except Exception as e:
        print(f"[WARDROBE] Ошибка при получении гардероба: {e}")
        return []


@app.put("/api/my_wardrobe/{item_id}")
async def update_my_wardrobe_item(item_id: int, req: WardrobeItemUpdateRequest, request: Request):
    owner_token = _get_owner_token(request)
    updated = update_user_wardrobe_item(
        item_id=item_id,
        title=req.title,
        category=req.category,
        color=req.color,
        style=req.style,
        owner_token=owner_token,
        db_path="database/wardrobe.db",
    )

    if not updated:
        raise HTTPException(status_code=404, detail="Wardrobe item not found")

    return {"status": "success"}


@app.delete("/api/my_wardrobe/{item_id}")
async def delete_my_wardrobe_item(item_id: int, request: Request):
    owner_token = _get_owner_token(request)
    deleted_count = delete_user_wardrobe_items([item_id], owner_token=owner_token, db_path="database/wardrobe.db")

    if deleted_count == 0:
        raise HTTPException(status_code=404, detail="Wardrobe item not found")

    return {"status": "success", "deleted_count": deleted_count}


@app.post("/api/my_wardrobe/bulk_delete")
async def bulk_delete_my_wardrobe_items(req: WardrobeDeleteRequest, request: Request):
    owner_token = _get_owner_token(request)
    deleted_count = delete_user_wardrobe_items(req.item_ids, owner_token=owner_token, db_path="database/wardrobe.db")
    return {"status": "success", "deleted_count": deleted_count}


@app.delete("/api/my_wardrobe")
async def delete_all_my_wardrobe_items(request: Request):
    owner_token = _get_owner_token(request)
    deleted_count = clear_user_wardrobe(db_path="database/wardrobe.db", owner_token=owner_token)
    return {"status": "success", "deleted_count": deleted_count}


def _safe_insert_unknown_item(
    image_url: str,
    owner_token: str,
    vision_payload_path: Optional[str] = None,
) -> None:
    try:
        insert_user_wardrobe_item(
            title="Новая вещь",
            category="unknown",
            color="unknown",
            style="unknown",
            image_url=image_url,
            vision_source="fallback",
            vision_payload={"category": "unknown", "color": "unknown", "style": "unknown"},
            vision_payload_path=vision_payload_path,
            owner_token=owner_token,
        )
    except Exception as e:
        print(f"[UPLOAD] Не удалось сохранить unknown item: {e}")


@app.post("/api/upload_clothing")
async def upload_clothing(request: Request, file: UploadFile = File(...)):
    owner_token = _get_owner_token(request)
    public_image_url = None
    vision_json_path = None

    try:
        image_bytes = await file.read()

        if not image_bytes:
            return {"status": "error", "message": "Файл пустой"}

        file_ext = file.filename.split(".")[-1].lower() if file.filename and "." in file.filename else "jpg"
        unique_filename = f"{uuid.uuid4().hex}.{file_ext}"
        os.makedirs(os.path.join("frontend_tma", "uploads"), exist_ok=True)
        save_path = os.path.join("frontend_tma", "uploads", unique_filename)

        with open(save_path, "wb") as f:
            f.write(image_bytes)

        public_image_url = f"/static/uploads/{unique_filename}"
        meta_dir = os.path.join("frontend_tma", "uploads", "meta")
        os.makedirs(meta_dir, exist_ok=True)
        vision_json_path = os.path.join(meta_dir, f"{os.path.splitext(unique_filename)[0]}.json")

        print(f"[UPLOAD] Анализирую '{unique_filename}' локально/через fallback vision")

        ai_data, vision_source = await analyze_uploaded_clothing(
            image_path=save_path,
            image_bytes=image_bytes,
            filename=file.filename or f"upload.{file_ext}",
            content_type=file.content_type or "image/jpeg",
            json_output_path=vision_json_path,
        )

        cat = str(ai_data.get("category", "unknown")).strip().lower()
        col = str(ai_data.get("color", "unknown")).strip().lower()
        style = str(ai_data.get("style", "unknown")).strip().lower()
        title = str(ai_data.get("title", "")).strip()

        if not cat:
            cat = "unknown"
        if not col:
            col = "unknown"
        if not style:
            style = "unknown"

        new_title = title or f"{col.capitalize()} {cat.capitalize()}"

        new_id = insert_user_wardrobe_item(
            title=new_title,
            category=cat,
            color=col,
            style=style,
            image_url=public_image_url,
            vision_source=vision_source,
            vision_payload=ai_data,
            vision_payload_path=vision_json_path,
            owner_token=owner_token,
        )

        print(f"[UPLOAD] ✅ Успешно: {new_title} ({cat}, {col}, {style})")
        return {
            "status": "success",
            "message": "Распознано и добавлено!",
            "ai_analysis": ai_data,
            "item": {
                "id": new_id,
                "title": new_title,
                "category": cat,
                "color": col,
                "style": style,
                "image_url": public_image_url,
                "vision_source": vision_source,
                "manually_edited": False,
            }
        }

    except httpx.TimeoutException:
        print("[VISION] ⏰ Таймаут соединения с vision-сервисом")
        if public_image_url:
            _safe_insert_unknown_item(public_image_url, owner_token, vision_json_path)
        return {
            "status": "success",
            "message": "Таймаут vision-сервиса, сохранено как unknown"
        }

    except httpx.RequestError as e:
        print(f"[VISION] 🌐 Ошибка запроса к vision-сервису: {type(e).__name__}: {e}")
        if public_image_url:
            _safe_insert_unknown_item(public_image_url, owner_token, vision_json_path)
        return {
            "status": "success",
            "message": "Vision-сервис недоступен, сохранено как unknown"
        }

    except Exception as e:
        print(f"[UPLOAD] Критическая ошибка: {type(e).__name__}: {e}")
        if public_image_url:
            _safe_insert_unknown_item(public_image_url, owner_token, vision_json_path)
        return {
            "status": "error",
            "message": "Сбой сервера при загрузке"
        }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "backend.main:app",
        host=os.getenv("APP_HOST", "0.0.0.0"),
        port=int(os.getenv("APP_PORT", "8000")),
        reload=False,
    )
