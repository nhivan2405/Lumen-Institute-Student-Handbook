# Giải thích code để vấn đáp

Tài liệu này mô tả đúng khung hiện có, không khẳng định các phần chưa có Knowledge Base/model API đã chạy. Học theo hai tài liệu bổ sung: `08_HUONG_DAN_DOC_CODE_VA_DEMO_MAI.md` (đọc luồng) và `09_KICH_BAN_DEMO_UI_XUONG_CODE.md` (UI xuống code).

## `app/core/config.py`

`Settings` đọc `EMBEDDING_MODEL`, `GEMINI_MODEL`, `GEMINI_API_KEY` từ biến môi trường. Lý do: source code có thể commit nhưng secret không được commit. `settings` được các service import dùng chung. Nếu bỏ module này, model ID/key dễ bị rải rác trong code và khó đổi khi demo.

## `app/services/embedding_service.py`

`_load()` lazy-load `SentenceTransformer`: model chỉ nạp lúc cần, tránh khởi động FastAPI chậm. `embed_passages()` thêm chuỗi `passage: ` trước đoạn tài liệu; `embed_query()` thêm `query: ` trước câu hỏi. Đây là quy ước E5 để hai loại văn bản vào đúng vai trò khi model tính vector.

`encode(..., normalize_embeddings=True)` là embedding inference: input text, output là danh sách số thực. Normalization giúp dot product/cosine được so sánh ổn định. Hàm này chạy local trên CPU hoặc GPU của máy chạy backend, không gọi Gemini và không tạo câu văn. Nếu đổi model, tất cả vectors đã lưu có thể không còn cùng không gian/chiều; phải re-index.

## `app/services/llm_service.py`

`generate_answer(question, evidence)` chỉ nhận câu hỏi và evidence Top-K đã chọn. Nếu thiếu key, `LlmUnavailable` được ném ra thay vì tạo output giả. Dòng `client.models.generate_content(...)` là **generation inference**: request đến Google, model Gemini tạo token câu trả lời trên hạ tầng Google. `GEMINI_MODEL` trong `.env` xác định đúng model đang gọi; giá trị mẫu hiện là cấu hình đề xuất, cần xác nhận model/key khả dụng trong tài khoản trước demo.

## `app/services/rag_service.py`

`answer_question()` là điều phối viên, không phải agent tự trị. Nó kiểm tra tài liệu được chọn, embedding query, truy xuất Qdrant (TODO ở khung) và evidence gate. Gate là điểm chống trả lời ngoài KB: retrieval rỗng thì trả từ chối và **không gọi Gemini**. `Evidence` giữ `filename`, `location`, `chunk_id`; citation sau này lấy các trường này, không để LLM tự nghĩ ra trang/slide.

## `app/db/database.py`

SQLite gồm `documents` (registry/trạng thái index), `conversations` và `messages`. SQLite phù hợp lab vì local, không cần server riêng và giữ được lịch sử sau restart. Qdrant khác SQLite: Qdrant tìm vector tương tự; SQLite lưu dữ liệu nghiệp vụ/lịch sử. `init_db()` dùng `CREATE ... IF NOT EXISTS`, nên restart không xóa dữ liệu.

## `app/api/chat.py` và `app/schemas.py`

`ChatRequest` kiểm tra `question` không rỗng, tối đa 4,000 ký tự trước khi vào service. Route `POST /api/chat` không chứa thuật toán RAG: nó chỉ nhận HTTP rồi gọi `answer_question`. Cách tách này giúp thầy đổi UI mà không chạm logic retrieval, hoặc test API độc lập.

## `frontend/streamlit_app.py`

`st.session_state` giữ trang hiện hành và chat tạm trong browser session. Nút **Chat mới** chỉ reset UI messages, không có lệnh xóa SQLite/Qdrant. Upload đang disabled có chủ ý: không báo READY giả khi ingestion chưa tồn tại. Trang Debug chỉ nêu model/luồng dự kiến và trạng thái chưa chạy; ở lab Qdrant/Gemini nó phải hiển thị trace thật (score, payload, context, latency).
