"""Endpoint chat mỏng: nhận/validate HTTP, giao việc RAG cho service."""
from fastapi import APIRouter, HTTPException
from app.schemas import ChatRequest, ConversationRequest
from app.services.rag_service import answer_question
from app.services.llm_service import LlmUnavailable
from app.services import history_service
from app.db import database

router = APIRouter(prefix="/api", tags=["chat"])

@router.post("/chat")
def chat(payload: ChatRequest):
    """Nhận câu hỏi từ UI, gọi RAG service và lưu lịch sử vào SQLite."""
    conversation = payload.conversation_id or history_service.new_conversation()["id"]
    try:
        result = answer_question(payload.question, payload.selected_document_ids, database.get_messages(conversation))
    except LlmUnavailable as error:
        raise HTTPException(status_code=503, detail=str(error)) from error
    except Exception as error:
        # Tránh FastAPI trả HTML/body rỗng khiến frontend không thể giải mã lỗi.
        raise HTTPException(
            status_code=502,
            detail=f"Không thể tạo câu trả lời: {error}",
        ) from error
    history_service.save_turn(conversation, payload.question, result["answer"], result.get("citations", []))
    return {**result, "conversation_id": conversation}

@router.post("/conversations")
def create_conversation(payload: ConversationRequest):
    return database.create_conversation(payload.title)

@router.get("/conversations")
def conversations():
    return database.list_conversations()

@router.get("/conversations/{conversation_id}/messages")
def messages(conversation_id: str):
    return database.get_messages(conversation_id, limit=100)


@router.delete("/conversations/{conversation_id}", status_code=204)
def delete_conversation(conversation_id: str):
    """Xóa một lịch sử chat SQLite; không ảnh hưởng Knowledge Base/Qdrant."""
    if not database.delete_conversation(conversation_id):
        raise HTTPException(status_code=404, detail="Không tìm thấy cuộc trò chuyện.")
