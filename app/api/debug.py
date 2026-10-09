"""Debug chỉ trả metadata/context lần chạy thật, không chứa API key hoặc prompt bí mật."""
from fastapi import APIRouter
from app.core.config import settings
from app.db import database

router = APIRouter(prefix="/api/debug", tags=["debug"])

@router.get("/configuration")
def configuration():
    return {"embedding_model": settings.embedding_model, "generation_model": settings.gemini_model,
            "top_k": settings.top_k, "gemini_configured": bool(settings.gemini_api_key),
            "ready_documents": len([doc for doc in database.list_documents() if doc["status"] == "READY"])}
