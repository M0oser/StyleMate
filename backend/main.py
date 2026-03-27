import os
import uuid
from typing import Optional

import httpx
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, File, UploadFile, Request, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from backend.contracts import (
    CompletionRequestDTO,
    build_error_response,
    build_meta_response,
    serialize_completion_response,
)
from backend.examples import build_completion_examples_payload
from backend.services.pg_wardrobe_bridge import (
    clear_pg_wardrobe,
    create_pg_wardrobe_item,
    delete_pg_wardrobe_items,
    list_pg_wardrobe,
    update_pg_wardrobe_item,
)
from backend.services.profile_service import (
    bootstrap_session,
    get_profile,
    record_feedback,
    save_profile,
)
from backend.services.image_preprocess import normalize_upload_image
from backend.services.vision_service import analyze_uploaded_clothing
from database.db import (
    get_repository,
    init_postgres_db,
    stable_user_id_from_owner_token,
)
from services.completion_errors import CompletionAPIError
from services.completion_service import CompletionService

load_dotenv(override=False)

app = FastAPI(title="StyleMate API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class WardrobeItemUpdateRequest(BaseModel):
    title: str
    category: str
    color: str
    style: str = "unknown"


class WardrobeDeleteRequest(BaseModel):
    item_ids: list[int]


class ProfileUpdateRequest(BaseModel):
    display_name: Optional[str] = None
    gender: Optional[str] = None
    style_preferences: Optional[list[str]] = None
    onboarding_completed: Optional[bool] = None


class FeedbackItemPayload(BaseModel):
    title: Optional[str] = None
    category: Optional[str] = None
    color: Optional[str] = None
    style: Optional[str] = None
    warmth: Optional[str] = None
    source: Optional[str] = None


class FeedbackRequest(BaseModel):
    feedback: str
    items: list[FeedbackItemPayload]
    scenario: Optional[str] = None
    style: Optional[str] = None


def _get_owner_token(request: Request, required: bool = True) -> Optional[str]:
    owner_token = str(request.headers.get("X-Owner-Token") or "").strip() or None

    if required and not owner_token:
        raise HTTPException(status_code=400, detail="Missing X-Owner-Token header")

    return owner_token


app.mount("/static", StaticFiles(directory="frontend_tma"), name="static")


def _safe_init_postgres_completion_stack() -> None:
    try:
        init_postgres_db()
        print("[PG_COMPLETION] PostgreSQL completion stack initialized")
    except Exception as e:
        print(f"[PG_COMPLETION] PostgreSQL completion stack unavailable: {e}")


@app.on_event("startup")
async def startup_event():
    _safe_init_postgres_completion_stack()


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


def _build_completion_public_response(
    request: CompletionRequestDTO,
    *,
    include_debug: bool,
) -> dict:
    internal_payload = CompletionService(repository=get_repository()).generate_completion(**request.model_dump())
    return serialize_completion_response(
        internal_payload,
        include_debug=include_debug,
    )


@app.get("/api/v1/meta")
async def api_v1_meta():
    return build_meta_response()


@app.get("/api/v1/meta/scenarios")
async def api_v1_meta_scenarios():
    payload = build_meta_response()
    return {"api_version": payload["api_version"], "scenarios": payload["scenarios"]}


@app.get("/api/v1/meta/roles")
async def api_v1_meta_roles():
    payload = build_meta_response()
    return {"api_version": payload["api_version"], "roles": payload["roles"]}


@app.get("/api/v1/examples/completion")
async def api_v1_completion_examples():
    return build_completion_examples_payload()


@app.post("/api/v1/completion")
@app.post("/api/completion", include_in_schema=False)
async def api_v1_completion(
    req: CompletionRequestDTO,
    request: Request,
    include_debug: bool = Query(default=False),
):
    try:
        owner_token = _get_owner_token(request, required=False)
        resolved_user_id = req.user_id
        if owner_token:
            resolved_user_id = stable_user_id_from_owner_token(owner_token)
        elif resolved_user_id is None:
            raise HTTPException(status_code=400, detail="Missing X-Owner-Token header or user_id")

        resolved_req = req.model_copy(update={"user_id": resolved_user_id})
        return _build_completion_public_response(resolved_req, include_debug=include_debug)
    except HTTPException:
        raise
    except CompletionAPIError as e:
        return JSONResponse(
            status_code=e.status_code,
            content=build_error_response(
                code=e.code,
                message=e.message,
                details=e.details,
            ),
        )
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content=build_error_response(
                code="INTERNAL_ERROR",
                message="Unexpected backend error.",
                details={"reason": str(e)},
            ),
        )


@app.post("/api/generate_outfits")
async def api_generate_outfits():
    return JSONResponse(
        status_code=410,
        content={
            "status": "deprecated",
            "message": "Legacy full outfit generation has been retired. Use completion-first flow via /api/v1/completion.",
        },
    )

@app.post("/api/auth/session")
async def api_auth_session(request: Request):
    owner_token = _get_owner_token(request)
    return bootstrap_session(owner_token)


@app.get("/api/profile")
async def api_get_profile(request: Request):
    owner_token = _get_owner_token(request)
    return {"profile": get_profile(owner_token)}


@app.patch("/api/profile")
async def api_patch_profile(req: ProfileUpdateRequest, request: Request):
    owner_token = _get_owner_token(request)

    try:
        profile = save_profile(
            owner_token,
            display_name=req.display_name,
            gender=req.gender,
            style_preferences=req.style_preferences,
            onboarding_completed=req.onboarding_completed,
        )
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))

    return {"profile": profile}


@app.post("/api/feedback")
async def api_feedback(req: FeedbackRequest, request: Request):
    owner_token = _get_owner_token(request)

    try:
        payload_items = [
            item.model_dump() if hasattr(item, "model_dump") else item.dict()
            for item in req.items
        ]
        result = record_feedback(
            owner_token,
            feedback=req.feedback,
            items=payload_items,
            scenario=req.scenario,
            requested_style=req.style,
        )
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))

    return {
        "status": "success",
        "saved_feedback": result["saved_feedback"],
        "feedback_summary": result["feedback_summary"],
        "style_preference_context": result["style_preference_context"],
    }


@app.get("/api/my_wardrobe")
async def get_my_wardrobe(request: Request):
    owner_token = _get_owner_token(request)

    try:
        return list_pg_wardrobe(owner_token)
    except Exception as e:
        print(f"[WARDROBE] Ошибка при получении гардероба: {e}")
        return []


@app.put("/api/my_wardrobe/{item_id}")
async def update_my_wardrobe_item(item_id: int, req: WardrobeItemUpdateRequest, request: Request):
    owner_token = _get_owner_token(request)
    updated = update_pg_wardrobe_item(
        owner_token=owner_token,
        item_id=item_id,
        title=req.title,
        category=req.category,
        color=req.color,
        style=req.style,
    )

    if not updated:
        raise HTTPException(status_code=404, detail="Wardrobe item not found")

    return {"status": "success"}


@app.delete("/api/my_wardrobe/{item_id}")
async def delete_my_wardrobe_item(item_id: int, request: Request):
    owner_token = _get_owner_token(request)
    deleted_count = delete_pg_wardrobe_items(item_ids=[item_id], owner_token=owner_token)

    if deleted_count == 0:
        raise HTTPException(status_code=404, detail="Wardrobe item not found")

    return {"status": "success", "deleted_count": deleted_count}


@app.post("/api/my_wardrobe/bulk_delete")
async def bulk_delete_my_wardrobe_items(req: WardrobeDeleteRequest, request: Request):
    owner_token = _get_owner_token(request)
    deleted_count = delete_pg_wardrobe_items(item_ids=req.item_ids, owner_token=owner_token)
    return {"status": "success", "deleted_count": deleted_count}


@app.delete("/api/my_wardrobe")
async def delete_all_my_wardrobe_items(request: Request):
    owner_token = _get_owner_token(request)
    deleted_count = clear_pg_wardrobe(owner_token=owner_token)
    return {"status": "success", "deleted_count": deleted_count}


def _safe_insert_unknown_item(
    image_url: str,
    owner_token: str,
    vision_payload_path: Optional[str] = None,
) -> None:
    try:
        create_pg_wardrobe_item(
            owner_token=owner_token,
            title="Новая вещь",
            category="unknown",
            color="unknown",
            style="unknown",
            image_url=image_url,
            vision_source="fallback",
            vision_payload_path=vision_payload_path,
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

        normalized_bytes, normalized_filename, normalized_content_type = normalize_upload_image(
            image_bytes=image_bytes,
            filename=file.filename or "upload.jpg",
            content_type=file.content_type or "image/jpeg",
        )

        file_ext = normalized_filename.split(".")[-1].lower() if "." in normalized_filename else "jpg"
        unique_filename = f"{uuid.uuid4().hex}.{file_ext}"
        os.makedirs(os.path.join("frontend_tma", "uploads"), exist_ok=True)
        save_path = os.path.join("frontend_tma", "uploads", unique_filename)

        with open(save_path, "wb") as f:
            f.write(normalized_bytes)

        public_image_url = f"/static/uploads/{unique_filename}"
        meta_dir = os.path.join("frontend_tma", "uploads", "meta")
        os.makedirs(meta_dir, exist_ok=True)
        vision_json_path = os.path.join(meta_dir, f"{os.path.splitext(unique_filename)[0]}.json")

        print(f"[UPLOAD] Анализирую '{unique_filename}' локально/через fallback vision")

        ai_data, vision_source = await analyze_uploaded_clothing(
            image_path=save_path,
            image_bytes=normalized_bytes,
            filename=normalized_filename,
            content_type=normalized_content_type,
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

        new_id = create_pg_wardrobe_item(
            owner_token=owner_token,
            title=new_title,
            category=cat,
            color=col,
            style=style,
            image_url=public_image_url,
            vision_source=vision_source,
            vision_payload_path=vision_json_path,
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
        if vision_json_path:
            print(f"[UPLOAD] vision_json_path={vision_json_path}")
        if public_image_url:
            print(f"[UPLOAD] public_image_url={public_image_url}")
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
