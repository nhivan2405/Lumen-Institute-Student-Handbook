"""Điểm khởi động backend FastAPI."""
from fastapi import FastAPI
from app.api.chat import router as chat_router
from app.api.documents import router as document_router
from app.api.debug import router as debug_router
from app.db.database import init_db
from app.core.config import settings

app = FastAPI(title="Trợ Lý Rô AI", version="0.1.0")
app.include_router(chat_router)
app.include_router(document_router)
app.include_router(debug_router)

@app.on_event("startup")
def startup() -> None:
    init_db()

@app.get("/health")
def health() -> dict:
    """Không lộ secret; chỉ báo khả năng cấu hình để kiểm tra lúc demo."""
    return {"status": "ok", "gemini_configured": bool(settings.gemini_api_key),
            "embedding_model": settings.embedding_model}
