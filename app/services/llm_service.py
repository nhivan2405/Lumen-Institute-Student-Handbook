"""Ranh giới generation inference: Gemini chạy trên hạ tầng Google qua API."""
from app.core.config import settings

class LlmUnavailable(RuntimeError):
    pass

def generate_answer(
    question: str,
    evidence: str,
    conversation_context: list[dict] | None = None,
) -> str:
    """Gửi đúng evidence Top-K, không gửi toàn bộ PDF hay API key ra UI.

    generate_content là vị trí generation inference. Chỉ được gọi sau evidence gate.
    """
    if not settings.gemini_api_key:
        raise LlmUnavailable("Chưa cấu hình GEMINI_API_KEY ở backend.")
    from google import genai
    client = genai.Client(api_key=settings.gemini_api_key)
    # Chỉ lấy vài lượt gần nhất để câu hỏi nối tiếp ("còn điều kiện nào?") có
    # chủ ngữ, nhưng không gửi toàn bộ lịch sử khiến prompt ngày càng dài.
    recent_history = (conversation_context or [])[-4:]
    history_text = "\n".join(
        f"{'Người dùng' if item['role'] == 'user' else 'Rô'}: {item['content']}"
        for item in recent_history
    ) or "(Đây là câu hỏi đầu tiên.)"

    prompt = f"""Bạn là Trợ Lý Rô AI. Chỉ trả lời từ EVIDENCE bên dưới.
Nếu evidence không đủ, trả lời: 'Tôi chưa tìm thấy đủ thông tin trong tài liệu đã chọn.'
LỊCH SỬ GẦN ĐÂY (chỉ để hiểu câu hỏi nối tiếp):
{history_text}

EVIDENCE:\n{evidence}\n\nCÂU HỎI HIỆN TẠI: {question}"""
    response = client.models.generate_content(model=settings.gemini_model, contents=prompt)
    return response.text or "Tôi chưa tạo được câu trả lời từ evidence."
