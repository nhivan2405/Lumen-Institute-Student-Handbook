# Hướng dẫn đọc code và demo ngày mai

## Mở đầu

> “Đây là khung RAG Chat Assistant. Tôi tách UI, API, xử lý tài liệu, embedding, vector database, LLM và history để mỗi bước đều truy được xuống code. Knowledge Base hiện chưa có tài liệu thật nên hệ thống báo đúng KB trống, không bịa câu trả lời hay nguồn.”

Không nói đã index hay Gemini đã trả lời nếu chưa có tài liệu/key thật.

## Mở file nào khi thầy hỏi gì

| Câu hỏi | File cần mở | Trả lời ngắn |
|---|---|---|
| Nút Chat mới làm gì? | `frontend/streamlit_app.py` | Gọi `POST /api/conversations`, tạo ID SQLite; không xóa KB. |
| Chat đi đâu? | `frontend/streamlit_app.py` → `app/api/chat.py` | UI chỉ gọi API; FastAPI validate rồi gọi RAG service. |
| Đọc PDF/DOCX/PPTX/TXT? | `app/services/document_loader.py` | Trích text và metadata trang/slide thật. |
| Chunk? | `app/services/chunking.py` | Chia theo ký tự, có overlap, giữ metadata. |
| Embedding? | `app/services/embedding_service.py` | E5 local: `passage:` cho chunks, `query:` cho question. |
| Vector DB? | `app/services/vector_store.py` | Qdrant Local vector + payload, filter `document_id`, Top-K cosine. |
| Gemini ở đâu? | `app/services/llm_service.py` | `client.models.generate_content()` là generation inference cloud. |
| Không trả lời ngoài KB? | `app/services/rag_service.py` | `if not retrieved` chặn trước Gemini. |
| History? | `app/db/database.py` | SQLite lưu conversations/messages. |

## Luồng index tài liệu: đọc từng khối

### 1. `app/api/documents.py`, `upload()`

`UploadFile` là file HTTP chưa tin cậy. `Path(file.filename).name` bỏ path do người dùng gửi để giảm path traversal. File vào temporary file rồi gọi `index_file()`: upload UI và script folder dùng **cùng một pipeline**. `finally` xóa temp file; `ValueError` trả HTTP 400, lỗi khác trả 500.

### 2. `app/services/ingestion_service.py`, `index_file()`

1. Kiểm extension, tệp tồn tại, rỗng và size.
2. `sha256(source.read_bytes())` tạo fingerprint; trùng hash với READY thì không index lại.
3. `create_document()` ghi `PROCESSING` SQLite.
4. `extract_document()` trả `{text, location}`.
5. `split_units()` chia chunks và copy `document_id/filename/location` vào payload.
6. `embedding_service.embed_passages()` gọi E5 local với prefix `passage:`.
7. `VectorStore.upsert()` ghi vector + payload vào Qdrant, `wait=True`.
8. Chỉ sau upsert thành công mới `READY`; exception đổi thành `FAILED` kèm lý do.

### 3. `app/services/document_loader.py`, `extract_document()`

- PDF: `fitz.open()` và `page.get_text("text")`; location là `trang N`.
- DOCX: `Document(path)` lấy paragraphs; không bịa page number, dùng `nội dung DOCX`.
- PPTX: lặp slide/text shape; location là `slide N`.
- TXT: `read_text(..., errors="replace")` tránh crash encoding.
- PDF scan không text trả list rỗng → `FAILED`, báo cần OCR; OCR chưa triển khai.

### 4. `app/services/chunking.py`, `split_units()`

`RecursiveCharacterTextSplitter` của LangChain Text Splitters ưu tiên cắt tại `\n\n`, `\n`, câu rồi đến space; vì vậy ít làm đứt ý hơn cắt index cứng. `chunk_size=900`, `chunk_overlap=150` là **ký tự**, không phải token. Mẩu nhỏ dưới 30 ký tự bị bỏ. Overlap ≥ size ném lỗi để tránh cấu hình sai.

## Luồng hỏi đáp: đọc từng khối

### `frontend/streamlit_app.py`

1. `API_BASE` chỉ backend local. UI không import E5/Qdrant/Gemini nên không lộ key.
2. `api_request()` đổi payload sang JSON, gọi API và đổi HTTP/network errors thành tiếng Việt.
3. `@st.cache_data(ttl=5)` giảm gọi list documents liên tục.
4. `st.session_state` giữ page/conversation/message cho browser session; SQLite mới là persistence.
5. `multiselect` đổi filename thành `selected_document_ids`; filter này tới Qdrant.
6. `st.status()` chỉ báo retrieval, không hiển thị reasoning nội bộ model.
7. Citation render từ API result, không tự tạo page/slide.

### `app/api/chat.py`, `chat()`

`ChatRequest` trong `schemas.py` chặn question rỗng/quá dài. Nếu không có ID, tạo conversation SQLite. `get_messages()` lấy context gần (không phải full history). `LlmUnavailable` thành HTTP 503 nếu key/quota thiếu. `save_turn()` lưu user/assistant/citations JSON.

### `app/services/rag_service.py`, `answer_question()`

1. Không có document được chọn → dừng.
2. Follow-up ngắn ghép câu user gần nhất chỉ để retrieval rõ nghĩa.
3. `embed_query()` thêm `query:` và `encode(normalize_embeddings=True)` trên máy local, output vector số.
4. Qdrant search Top-K + filter document ID.
5. `if not retrieved`: evidence gate, từ chối và **không gọi Gemini**.
6. Có evidence: chỉ nối Top-K chunks thành context; citation lấy payload metadata.
7. Sau cùng `generate_answer()` mới gọi Gemini.

### `app/services/llm_service.py`, `generate_answer()`

`if not GEMINI_API_KEY` chặn request nếu cấu hình thiếu. `genai.Client` tạo client. `client.models.generate_content(...)` là **generation inference** trên cloud Google. Prompt nhận evidence + question; `response.text` là output.

## Database và model

| Thành phần | Chạy/lưu ở đâu | Input | Output |
|---|---|---|---|
| E5-small | Máy backend | `passage:` chunk / `query:` question | vector (model chuẩn: 384 chiều) |
| Qdrant Local | `data/qdrant/` | vector + payload | Top-K chunk + score |
| Gemini Flash-Lite | Google API | prompt evidence Top-K | text answer |
| SQLite | `data/database/ro_ai.db` | document/conversation/message | persistence restart |

Đổi Gemini thường không cần re-index. Đổi embedding model **phải re-index**, vì vector cũ/mới có thể khác không gian hoặc dimension.

## Kịch bản demo không có Knowledge Base

1. Chạy FastAPI rồi Streamlit.
2. Mở Chat: KB trống là đúng thiết kế closed-domain.
3. Mở Tài liệu: mô tả pipeline caption; không upload nếu chưa muốn tải E5 model lần đầu.
4. Mở Kiểm tra: chỉ đường tới embedding/vector/Gemini services.
5. Mở `rag_service.py`, đọc `if not retrieved`: evidence rỗng nên Gemini không chạy.
6. Nếu thầy hỏi upload, mở `ingestion_service.py` và đọc tám bước index phía trên.

## Lệnh chạy

```powershell
cd E:\NewTech\RAG_Assistant
.\.venv\Scripts\Activate.ps1
python -m uvicorn app.main:app --host 127.0.0.1 --port 8123
# PowerShell khác
.\.venv\Scripts\Activate.ps1
streamlit run frontend\streamlit_app.py
```

## Trả lời nhanh

- Model ID: `.env` → `Settings.gemini_model` → `llm_service.generate_answer()`.
- E5 inference local; Gemini inference cloud.
- Không dùng OmniRoute vì chỉ một provider Gemini là đủ baseline; multi-provider router tăng độ phức tạp.
- Không trả lời khi KB rỗng để chống hallucination, đúng RAG closed-domain.
