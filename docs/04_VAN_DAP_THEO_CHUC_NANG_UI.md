# Từ nút UI đến backend

| Chức năng | Frontend | API | Backend/service | Model/DB | Kết quả hiện tại |
|---|---|---|---|---|---|
| Chat mới | `streamlit_app.py` session state | Chưa cần | Xóa state hiển thị, không xóa KB | SQLite ở lab history | Có khung UI |
| Gửi câu hỏi | `st.chat_input` | `POST /api/chat` | `chat.py` → `answer_question` | E5 → Qdrant → Gemini | API route có sẵn; Qdrant chưa nối |
| Upload | Trang Tài liệu | Chưa tạo | ingestion pipeline | loader/E5/Qdrant/SQLite | Disabled, không giả chạy |
| Debug | Trang Kiểm tra | Debug endpoint ở lab sau | Trace retrieval | E5/Qdrant/Gemini | Hiển thị design và trạng thái thật |

**Câu dễ bị hỏi:** Gemini không “đọc PDF” trực tiếp. App chỉ gửi các chunks Top-K đã truy xuất sau evidence gate. Điều này giảm token và giúp citation kiểm chứng được.

