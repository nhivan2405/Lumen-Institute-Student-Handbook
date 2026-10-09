"""Schema request/response giúp FastAPI kiểm tra dữ liệu trước khi vào service."""
from pydantic import BaseModel, Field

class ChatRequest(BaseModel):
    question: str = Field(min_length=1, max_length=4000)
    selected_document_ids: list[str] = []
    conversation_id: str | None = None

class ConversationRequest(BaseModel):
    title: str = "Cuộc trò chuyện mới"

class RenameDocumentRequest(BaseModel):
    filename: str = Field(min_length=1, max_length=255)
