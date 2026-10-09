# Sổ tay ôn vấn đáp: đọc code Rô AI theo từng file

Tài liệu này để **mở song song với code**. Không cần học thuộc từng ký tự; hãy nắm: *file này nhận gì, gọi file nào, trả gì và vì sao cần nó*. Khi thầy chỉ vào một dòng, xem mục của file đó bên dưới.

## 1. Nói trong 30 giây

> “Đồ án là RAG Chat Assistant cho tài liệu nội bộ. Khi upload, hệ thống trích text, chia chunk, dùng multilingual-E5-small tạo vector local và lưu Qdrant Local. Khi hỏi, câu hỏi được E5 biến thành vector, Qdrant lấy Top-K đoạn liên quan trong đúng tài liệu đã chọn. Chỉ khi có evidence thì Gemini 3.5 Flash mới sinh câu trả lời. SQLite lưu danh sách tài liệu và lịch sử chat; citation lấy từ metadata thật, không để LLM tự bịa nguồn.”

## 2. Hai luồng phải thuộc

```text
UPLOAD
Streamlit → POST /api/documents/upload → documents.py
→ ingestion_service.index_file
→ document_loader.extract_document → chunking.split_units
→ embedding_service.embed_passages (E5 local)
→ vector_store.upsert (Qdrant Local) → SQLite: READY

CHAT
Streamlit → POST /api/chat → chat.py
→ SQLite lấy hội thoại gần → rag_service.answer_question
→ embedding_service.embed_query (E5 local)
→ vector_store.search (Qdrant Top-K + filter document ID)
→ evidence gate → llm_service.generate_answer (Gemini cloud)
→ SQLite lưu user/assistant/citation → Streamlit hiển thị lịch sử
```

Điểm quan trọng: **E5 không trả lời bằng chữ. E5 chỉ trả vector số. Gemini mới sinh câu văn.**

## 3. Thứ tự mở file khi thầy hỏi

1. Mở `frontend/streamlit_app.py`: nút trên giao diện gọi API nào.
2. Mở `app/api/chat.py` hoặc `app/api/documents.py`: API nhận request và gọi service nào.
3. Mở service tương ứng: đây mới là nơi có thuật toán RAG.
4. Mở `app/core/config.py`: model ID, Top-K, chunk size lấy từ đâu.
5. Mở `app/db/database.py`: dữ liệu nào được lưu lâu dài.

## 4. Giải thích từng file

### `app/main.py` — cửa vào backend

- `app = FastAPI(...)` tạo ứng dụng HTTP.
- Ba dòng `include_router(...)` gắn các nhóm API chat, tài liệu và debug vào app.
- Hàm `startup()` gọi `init_db()` trước request đầu tiên. `CREATE TABLE IF NOT EXISTS` nên restart không xóa dữ liệu cũ.
- `GET /health` dùng để biết backend sống, model embedding nào đang cấu hình và Gemini key có tồn tại hay không. Nó không trả API key.

**Câu trả lời thi:** `main.py` chỉ khởi động và nối route; nó không chứa retrieval hay Gemini để kiến trúc không bị dồn vào một file.

### `app/core/config.py` — một nơi cấu hình

- `ROOT = Path(__file__).resolve().parents[2]` tìm thư mục gốc project, không phụ thuộc bạn chạy lệnh ở đâu.
- `_load_env_file()` đọc `.env`; `os.environ.setdefault` không ghi đè biến môi trường đã đặt sẵn.
- `Settings` là `@dataclass(frozen=True)`: các thông số runtime chỉ đọc, như `embedding_model`, `gemini_model`, `top_k`, đường dẫn SQLite/Qdrant.
- `settings = Settings()` là một object dùng chung, để model ID không bị viết rải rác.

**Chỉ Gemini ở đâu:** `.env` có `GEMINI_MODEL=gemini-3.1-flash-lite` → `settings.gemini_model` → `llm_service.py`. Giá trị mặc định trong source chỉ là phương án dự phòng nếu `.env` chưa có.

### `app/schemas.py` — kiểm tra request trước business logic

- `ChatRequest.question = Field(min_length=1, max_length=4000)` chặn câu hỏi rỗng/quá dài ngay ở FastAPI.
- `selected_document_ids` là danh sách ID, không tin filename do browser gửi.
- `conversation_id` có thể `None` ở câu hỏi đầu tiên.
- `ConversationRequest` và `RenameDocumentRequest` là schema cho hai API còn lại.

**Vì sao cần:** route nhận object đã validate thay vì tự `if` mọi trường trong route.

### `app/db/database.py` — SQLite cho dữ liệu nghiệp vụ

- `connection()` mở kết nối mới cho từng thao tác; tránh chia sẻ một SQLite connection giữa nhiều request.
- `init_db()` tạo ba bảng: `documents`, `conversations`, `messages`.
- `documents` giữ trạng thái `PROCESSING/READY/FAILED`, filename, hash, đường dẫn gốc.
- `conversations` là một phiên chat; `messages` là từng message user/assistant và citations JSON.
- `get_messages()` lấy tối đa các message gần, rồi `reversed()` để trả đúng thứ tự thời gian.

**Phân biệt:** SQLite không tìm ngữ nghĩa. Qdrant tìm vector. SQLite lưu registry, hội thoại và trạng thái.

### `app/api/documents.py` — API quản lý Knowledge Base

- `GET /api/documents`: trả danh sách tài liệu cho giao diện.
- `POST /upload`: nhận `UploadFile`, lấy `Path(file.filename).name` để bỏ đường dẫn nguy hiểm, ghi temporary file, rồi gọi **một** pipeline `index_file()`.
- Khối `finally` chỉ xóa file tạm; file gốc đã lưu trong `data/uploads` vẫn còn để re-index.
- `DELETE /{document_id}` xóa vector Qdrant, registry SQLite và bản gốc upload trong `data/uploads/`. Backend chỉ được phép xóa file nằm trong thư mục upload; file input batch ở `data/documents/` không bị động vào.
- `PATCH /{document_id}` đổi filename ở cả SQLite và payload Qdrant; vì vậy citation cũng hiện tên mới.
- `POST /{document_id}/reindex` dùng file đã lưu và chạy lại chính pipeline index, không nhân bản logic.

### `app/services/ingestion_service.py` — điều phối index

Đây là file quan trọng nhất khi thầy hỏi “upload chạy thế nào?”. Đọc `index_file()` theo 8 bước:

1. Kiểm extension, file tồn tại, rỗng, dung lượng.
2. `sha256(...)` tạo fingerprint; cùng nội dung thì phát hiện duplicate dù tên file khác.
3. Chép bản gốc vào `data/uploads` để re-index; tạo record SQLite `PROCESSING`.
4. `extract_document()` lấy text và vị trí thật.
5. `split_units()` biến text thành chunks có metadata.
6. `embed_passages()` biến từng chunk thành vector E5.
7. `VectorStore().upsert()` ghi vector + metadata vào Qdrant.
8. Chỉ sau upsert thành công mới gọi `set_document_status(..., "READY")`. Lỗi thì ghi `FAILED` kèm lý do.

**Ý nghĩa của READY:** không phải chỉ upload xong; nó chứng minh chunks đã vào Qdrant.

### `app/services/document_loader.py` — đọc đúng bốn loại file

- `SUPPORTED_EXTENSIONS` là allowlist PDF/DOCX/PPTX/TXT.
- PDF dùng PyMuPDF (`fitz`), đọc từng `page.get_text("text")`, nên citation ghi `trang N`.
- DOCX dùng `python-docx`, ghép paragraph và ghi `nội dung DOCX`; không bịa số trang vì DOCX không có page cố định khi render.
- PPTX dùng `python-pptx`, duyệt từng slide/shape và ghi `slide N`.
- TXT dùng `errors="replace"` để một ký tự lỗi encoding không làm crash upload.

PDF scan chỉ là ảnh sẽ không có text, chunks rỗng và bị báo cần OCR. Đây là giới hạn được báo thật, không che giấu.

### `app/services/chunking.py` — chia tài liệu nhưng giữ ý

- `clean_text()` xóa space thừa, giữ tối đa một dòng trống để ranh giới đoạn không mất.
- `RecursiveCharacterTextSplitter` ưu tiên ngắt `\n\n`, `\n`, dấu chấm, space rồi mới bắt buộc cắt ký tự.
- `chunk_size=900`, `chunk_overlap=150` là **ký tự**, lấy từ `.env` qua `settings`.
- `chunk_overlap >= chunk_size` bị chặn vì overlap như vậy không hợp lệ.
- Mỗi chunk mang `document_id`, `filename`, `location`, `chunk_index`; những field này đi tới citation sau cùng.

### `app/services/embedding_service.py` — E5 inference local

- `EmbeddingService` giữ `self._model`; `_load()` chỉ nạp model lúc lần đầu cần (lazy loading), không làm FastAPI khởi động chậm.
- `snapshot_download(..., local_files_only=True)` bắt buộc dùng snapshot cache local; ngày demo không cần tải Internet nếu model đã chuẩn bị.
- `embed_passages()` thêm prefix `passage: ` cho chunks.
- `embed_query()` thêm prefix `query: ` cho câu hỏi.
- `encode(..., normalize_embeddings=True)` nhận text và trả vector float. Đây là **embedding inference**, chạy trên máy backend (CPU/GPU), không gọi Gemini.
- `embedding_service = EmbeddingService()` dùng một instance/process để không nạp weights lặp lại mỗi request.

**Vì sao multilingual-e5-small:** hỗ trợ nhiều ngôn ngữ, nhẹ hơn model lớn nên chạy local phù hợp laptop/demo; hai prefix là quy ước huấn luyện của E5. Đổi E5 phải re-index vì vectors cũ thuộc không gian ngữ nghĩa khác.

### `app/services/vector_store.py` — Qdrant Local

- `QdrantClient(path=...)` chạy local ở `data/qdrant`, không cần Docker/cloud.
- `_ensure_collection(vector_size)` tạo collection lần đầu; vector size lấy trực tiếp từ output E5, không hard-code.
- `Distance.COSINE` so độ giống vector. Vì E5 đã normalize, cosine là cách so sánh phù hợp.
- `upsert()` biến từng `chunk + vector` thành một `PointStruct`; `payload=chunk` giữ text và metadata cùng vector.
- `search()` tạo filter `document_id` từ tài liệu người dùng tick, sau đó `query_points(... limit=top_k)` trả các chunk điểm cao nhất.
- `delete_document()` và `rename_document_payload()` chỉ tác động point có đúng `document_id`.

### `app/api/chat.py` — API cho một lượt chat

- Route `POST /api/chat` nhận `ChatRequest` đã validate.
- `payload.conversation_id or new_conversation()` tạo chat SQLite cho câu đầu, còn câu sau dùng đúng ID cũ.
- `database.get_messages(conversation)` lấy ngữ cảnh cũ trước khi gọi RAG.
- `answer_question(...)` trả answer/citations/debug.
- `history_service.save_turn(...)` chỉ lưu khi RAG đã trả kết quả.
- `LlmUnavailable` thành HTTP 503 (thiếu key/quota); lỗi khác thành HTTP 502 với message JSON để UI không vỡ `JSONDecodeError`.

### `app/services/rag_service.py` — bộ não điều phối RAG

Đọc `answer_question()` theo đúng thứ tự:

1. Nếu chưa chọn tài liệu, trả message hướng dẫn và dừng.
2. Nếu câu hỏi ngắn (ví dụ “còn gì nữa?”), ghép các câu user gần nhất vào `retrieval_question` để retrieval hiểu chủ đề.
3. `embed_query(retrieval_question)` dùng E5 local tạo query vector.
4. `VectorStore().search(...)` lấy Top-K evidence trong document IDs đã chọn.
5. `if not retrieved`: **evidence gate**. Trả từ chối, Gemini không được gọi. Đây là hàng rào chống hallucination.
6. Có evidence: ghép chỉ các chunks tìm được thành `context`; citations lấy `filename/location/chunk_id` từ metadata.
7. Gọi `generate_answer(question, context, conversation_context)` ở bước cuối.

`@dataclass Evidence` làm dữ liệu retrieval có kiểu rõ ràng thay vì truyền dict lộn xộn.

### `app/services/llm_service.py` — Gemini generation inference

- `if not settings.gemini_api_key` chặn trước nếu server chưa có key.
- `from google import genai` và `genai.Client(api_key=...)` tạo client Google GenAI trong backend.
- `recent_history = ...[-4:]` chỉ lấy bốn message gần; nó giúp Gemini hiểu câu nối tiếp nhưng không làm prompt phình vô hạn.
- Prompt ghi rõ: chỉ trả lời từ `EVIDENCE`; history chỉ để hiểu đại từ/chủ đề, không là nguồn sự thật.
- Dòng quan trọng nhất là `client.models.generate_content(model=settings.gemini_model, contents=prompt)`.

**Trả lời chuẩn:** Gemini chạy inference tạo câu trên hạ tầng Google qua API. Model ID lấy từ `.env`; backend gửi question, vài turn gần và Top-K evidence, nhận `response.text`. API key không đi tới Streamlit.

### `app/services/history_service.py` — lớp mỏng cho lịch sử

- `new_conversation()` gọi database tạo conversation.
- `save_turn()` lưu lần lượt message user rồi assistant. `json.dumps(... ensure_ascii=False)` giữ citation tiếng Việt đúng dấu.

Tách file này để route không phụ thuộc chi tiết SQLite.

### `app/api/debug.py` và `app/services/evaluation_service.py`

- `/api/debug/configuration` chỉ cho xem model, Top-K, số document READY và key đã được cấu hình hay chưa; không lộ key/prompt.
- `evaluate_case()` chạy một case thật, đo `perf_counter`, so `should_answer` với hệ thống có trả lời hay từ chối. Đây là test hành vi RAG, không so sánh tuyệt đối câu văn của LLM.

### `frontend/streamlit_app.py` — giao diện và giữ chat liên tục

- `API_BASE_URL` đọc biến môi trường, mặc định FastAPI local cổng 8123.
- `api_request()` đóng JSON request và đọc lỗi an toàn. Nếu backend trả body rỗng/HTML, `error_detail()` vẫn đưa lỗi dễ đọc thay vì JSON decode error.
- `api_upload_document()` tự tạo multipart request vì upload file không phải JSON.
- `load_documents()` có `@st.cache_data(ttl=5)` để không gọi list API liên tục.
- `initialize_session_state()` tạo `page`, `conversation_id`, `messages`, `last_debug` riêng cho mỗi browser tab.
- `start_new_chat()` tạo conversation mới, reset **màn hình chat** nhưng không xóa SQLite/Qdrant; `conversation_id` nằm trong URL để refresh vẫn quay về đúng chat.
- `restore_chat_history()` gọi `GET /api/conversations/{id}/messages` và nạp lại SQLite nếu Streamlit rerun/reconnect làm memory state trống.
- `render_chat_page()` render lịch sử trước, rồi nhận `st.chat_input`. Khi hỏi: append user → gọi `/chat` → append assistant/citations. Vì vậy câu đầu vẫn hiện khi gửi câu thứ hai.
- `render_documents_page()` upload, index, đổi tên, xóa, re-index; tất cả qua API, UI không tự sửa Qdrant.
- Trang **Quản trị Knowledge Base** mô tả rõ Admin upload/quản lý tài liệu, còn User chỉ chọn tài liệu READY để chat. Bản demo chưa cài login/RBAC, nên đây là phân tách luồng chức năng chứ chưa phải phân quyền bảo mật.
- `render_debug_page()` cho thầy xem config và trace thật của câu hỏi gần nhất.

### `scripts/index_documents.py` — index hàng loạt

Lệnh `python scripts/index_documents.py` duyệt `data/documents/`, chỉ nhận extension được hỗ trợ và gọi lại `index_file()`. Nó **không có pipeline riêng**, tránh tình trạng upload UI và batch index cho kết quả khác nhau.

### `tests/test_rag.py` — test nhỏ, chạy nhanh

- Test `clean_text` kiểm tra chuẩn hóa whitespace.
- Test `split_units` kiểm tra chunk vẫn giữ `document_id` và `location`.
- Test không tải E5/Gemini nên chạy nhanh, phù hợp kiểm tra regression cơ bản.

## 5. Câu hỏi thầy thường hỏi và câu trả lời ngắn

| Thầy hỏi | Trả lời | Mở file |
|---|---|---|
| Embedding chạy thế nào? | E5 local encode `passage:` cho chunk và `query:` cho câu hỏi, normalize vector rồi Qdrant so cosine. | `embedding_service.py` |
| Gemini dùng ở đâu? | `llm_service.generate_answer()`, dòng `generate_content`; model lấy từ `.env`. | `llm_service.py`, `.env` |
| Model chạy ở đâu? | E5 chạy local backend; Qdrant/SQLite local; Gemini generation chạy cloud Google API. | `embedding_service.py`, `llm_service.py` |
| Vì sao không gọi Gemini luôn? | RAG lấy evidence trước, gate khi không có evidence để chống hallucination và có citation. | `rag_service.py` |
| Citation có phải Gemini tự tạo? | Không. Nó đi từ loader → chunk payload → Qdrant → `Evidence` → UI. | `document_loader.py`, `chunking.py`, `rag_service.py` |
| Vì sao dùng SQLite + Qdrant? | SQLite giữ state/lịch sử; Qdrant tối ưu semantic vector search. Hai nhiệm vụ khác nhau. | `database.py`, `vector_store.py` |
| Khi đổi model gì phải làm? | Đổi Gemini: không cần re-index. Đổi E5: phải re-index toàn bộ vì vector space/dimension có thể khác. | `config.py`, `embedding_service.py` |

## 6. Cách tự luyện trong 10 phút

1. Mở `frontend/streamlit_app.py`, tìm `"/chat"`.
2. Ctrl+P mở `app/api/chat.py`, đọc route `chat()`.
3. Ctrl+P mở `app/services/rag_service.py`, đọc `answer_question()` từ trên xuống.
4. Nhảy vào `embed_query`, `search`, `generate_answer` theo đúng thứ tự gọi.
5. Quay lại `ingestion_service.py`, kể lại luồng index 8 bước.
6. Chỉ cho thầy thấy `if not retrieved` và nói: “Đây là evidence gate, nên không đủ bằng chứng thì Gemini không chạy.”

Đó là phần quan trọng nhất của đồ án; không cần đọc thuộc toàn bộ import hay CSS giao diện.
