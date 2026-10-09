"""Ranh giới generation inference: Gemini chạy trên hạ tầng Google qua API."""
from time import sleep

from app.core.config import settings


class LlmUnavailable(RuntimeError):
    """Lỗi có thể hiển thị cho người dùng mà không làm lộ lỗi provider thô."""
    pass


def _is_temporary_provider_error(error: Exception) -> bool:
    """Nhận diện lỗi tạm thời của Gemini để retry, không retry lỗi cấu hình/key."""
    message = str(error).upper()
    return "503" in message or "UNAVAILABLE" in message or "HIGH DEMAND" in message


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

    # 503 là lỗi quá tải tạm thời phía Gemini. Retry ngắn giúp demo không hỏng
    # ngay khi provider có một spike; không retry các lỗi key/model sai.
    for attempt in range(3):
        try:
            response = client.models.generate_content(
                model=settings.gemini_model,
                contents=prompt,
            )
            return response.text or "Tôi chưa tạo được câu trả lời từ evidence."
        except Exception as error:
            if not _is_temporary_provider_error(error):
                raise LlmUnavailable(
                    "Gemini không thể xử lý yêu cầu. Hãy kiểm tra GEMINI_API_KEY và GEMINI_MODEL."
                ) from error
            if attempt < 2:
                sleep(attempt + 1)

    raise LlmUnavailable(
        "Gemini đang quá tải tạm thời. Rô đã thử lại 3 lần; hãy gửi lại câu hỏi sau ít phút."
    )
