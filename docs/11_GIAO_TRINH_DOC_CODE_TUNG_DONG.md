# Giáo trình đọc toàn bộ code Rô AI

Đây là file ôn vấn đáp. Khi thầy chỉ một dòng, không cần học thuộc máy móc. Hãy trả lời theo 4 ý: cú pháp, lý do, input/output và ai gọi ai.

## 1. Cú pháp Python phải hiểu

| Cú pháp | Nghĩa dễ hiểu | Dùng trong project |
|---|---|---|
| def | Khai báo hàm, tức một việc có tên để gọi lại. | def index_file(...) |
| return | Trả kết quả về nơi gọi hàm. | return result |
| class | Khuôn tạo object có dữ liệu và hàm. | class EmbeddingService |
| self | Object hiện tại của một class. | self._model |
| __init__ | Hàm chạy khi tạo object bằng ClassName(). | EmbeddingService() |
| str / int / float | Chuỗi / số nguyên / số thực. | filename: str |
| list[str] | Danh sách chuỗi. | chunks |
| dict | Dữ liệu key-value. | filename, location |
| str \| None | Chuỗi hoặc chưa có giá trị. | conversation_id |
| -> dict | Type hint, hàm dự kiến trả dict. | index_file |
| try / except / finally | Thử chạy / bắt lỗi / luôn dọn dẹp. | upload temp file |
| with | Mở tài nguyên và tự đóng khi xong. | with connection() |
| @router.post | Gắn hàm Python thành URL API. | POST chat |

### self và lớp cha

    class EmbeddingService:
        def __init__(self) -> None:
            self._model = None

- EmbeddingService là class do project viết để gom model E5 và hàm embedding.
- self chính là object đang chạy. Khi tạo embedding_service = EmbeddingService(), Python truyền object đó vào self.
- self._model là dữ liệu của riêng object này. Lúc đầu None nghĩa chưa nạp model.
- Class này không khai báo class cha riêng; lớp cha mặc định là object của Python.
- Dấu gạch dưới trong _model là quy ước dùng nội bộ, không phải bảo mật.

Trả lời thầy: Em dùng class để giữ model đã load trong RAM. self giữ model nên mỗi request không cần nạp lại weights.

## 2. Bản đồ ai gọi ai

    Browser
      -> frontend/streamlit_app.py
         -> POST documents upload -> app/api/documents.py
            -> ingestion_service.index_file()
               -> document_loader -> chunking -> E5 local -> Qdrant Local

         -> POST chat -> app/api/chat.py
            -> rag_service.answer_question()
               -> E5 local -> Qdrant Local -> evidence gate -> Gemini API

SQLite lưu documents, conversations, messages.
Qdrant lưu vector chunks và payload metadata.

Khi thầy hỏi hàm này từ đâu ra, lần ngược mũi tên: UI gọi API, API gọi service, service gọi model/database.

---

## 3. Khởi động và config

### app/main.py

    app = FastAPI(title="Trợ Lý Rô AI", version="0.1.0")
    app.include_router(chat_router)
    app.include_router(document_router)
    app.include_router(debug_router)

- FastAPI(...) tạo object web application.
- include_router gắn các URL đã viết ở file API vào app chính. Thiếu chat_router thì API chat trả 404.

    @app.on_event("startup")
    def startup() -> None:
        init_db()

- Decorator báo FastAPI chạy startup khi server mở.
- init_db tạo bảng SQLite nếu chưa có, không xóa dữ liệu cũ.
- Lệnh chạy uvicorn import file này và lấy object tên app.

### app/core/config.py

    ROOT = Path(__file__).resolve().parents[2]

- __file__ là path file đang chạy.
- resolve đổi thành absolute path.
- parents[2] đi từ config.py -> core -> app -> project root.
- Mục đích: luôn tìm đúng data folder dù terminal chạy ở đâu.

    env_file = ROOT / ".env"
    if not env_file.exists():
        return

- Path / tên là ghép path.
- Không có .env thì return; backend vẫn mở nhưng Gemini chưa có key.

    key, value = line.split("=", 1)
    os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))

- split ở dấu bằng đầu tiên, tránh làm hỏng secret.
- setdefault không ghi đè environment có sẵn trên máy.

    @dataclass(frozen=True)
    class Settings:
        embedding_model: str = os.getenv("EMBEDDING_MODEL", "intfloat/multilingual-e5-small")
        gemini_model: str = os.getenv("GEMINI_MODEL", "gemini-3.1-flash-lite")
        gemini_api_key: str | None = os.getenv("GEMINI_API_KEY")

- dataclass tự sinh constructor.
- frozen=True ngăn sửa config nhầm.
- getenv lấy .env/environment trước, thiếu mới lấy default.
- Runtime demo dùng GEMINI_MODEL=gemini-3.1-flash-lite trong .env. Default trong source chỉ là fallback.

    settings = Settings()

Tạo một config object dùng chung. Không viết model/key nhiều nơi.

### app/schemas.py

    class ChatRequest(BaseModel):
        question: str = Field(min_length=1, max_length=4000)
        selected_document_ids: list[str] = []
        conversation_id: str | None = None

- BaseModel là lớp cha Pydantic, parse JSON và validate.
- Field chặn câu hỏi rỗng/quá dài trước khi RAG chạy.
- Câu hỏi đầu chưa có conversation nên ID là None.
- Dùng schema để API không nhận dict thô rồi tự kiểm tra từng key.

---

## 4. Luồng Documents: upload -> chunk -> vector -> READY

### frontend/streamlit_app.py: UI upload

    uploaded_file = st.file_uploader(
        "Chọn tệp để index",
        type=["pdf", "docx", "pptx", "txt"],
    )

- st.file_uploader trả UploadedFile hoặc None.
- type chỉ là UX. Backend vẫn validate vì client có thể gọi API trực tiếp.

    result = api_upload_document(uploaded_file.name, uploaded_file.getvalue())

- name là filename hiển thị.
- getvalue là bytes file.
- api_upload_document gửi multipart form-data, nhận JSON FastAPI thành dict.

### app/api/documents.py: route upload

    @router.post("/upload", status_code=201)
    def upload(file: UploadFile = File(...)):

- Router prefix là api/documents nên URL là POST api/documents/upload.
- UploadFile là object file HTTP FastAPI.
- File(...) nghĩa file bắt buộc.
- 201 nghĩa tạo resource mới.

    filename = Path(file.filename or "untitled").name
    suffix = Path(filename).suffix.lower()

- or untitled chống filename rỗng.
- name bỏ path do client gửi, giảm path traversal.
- suffix.lower lấy extension chuẩn hóa.

    with NamedTemporaryFile(delete=False, suffix=suffix) as temp:
        temp.write(file.file.read())
        temp_path = Path(temp.name)

- with tự đóng temp file.
- delete=False vì pipeline cần path sau block.
- read lấy bytes upload; write ghi ra temp file.

    return index_file(temp_path, copy_to_uploads=True, original_filename=filename)

- Route không tự embed/chunk, chỉ chuyển business logic vào service.
- original_filename giữ tên người dùng thấy, không dùng tên temp ngẫu nhiên.

    finally:
        if temp_path and temp_path.exists():
            temp_path.unlink()

- finally luôn chạy cả lúc lỗi.
- unlink xóa file tạm. Bản gốc đã copy vào data/uploads.

### app/services/ingestion_service.py: pipeline index

    def index_file(source: Path, copy_to_uploads: bool = True,
                   original_filename: str | None = None) -> dict:

- source là file path thực.
- UI upload đặt copy_to_uploads=True để còn re-index.
- script batch dùng False vì file đã ở data/documents.
- Một pipeline chung giúp UI upload và batch index không cho kết quả khác nhau.

    display_filename = original_filename or source.name
    if Path(display_filename).suffix.lower() not in SUPPORTED_EXTENSIONS:
        raise ValueError("Định dạng không được hỗ trợ.")

- Ưu tiên tên file gốc upload.
- raise ValueError dừng hàm; API chuyển thành HTTP 400.

    digest = sha256(source.read_bytes()).hexdigest()
    duplicate = database.find_document_hash(digest)
    if duplicate:
        return {**duplicate, "duplicate": True}

- SHA-256 tạo fingerprint theo nội dung file.
- Hash trùng là cùng bytes dù tên khác.
- Cú pháp {**duplicate,...} copy dict cũ rồi thêm field.
- Không dùng filename để chống trùng vì cùng tên chưa chắc cùng nội dung.

    document_id = database.create_document(display_filename, digest, str(stored))
    units = extract_document(stored)
    chunks = split_units(units, document_id, display_filename)
    chunk_texts = [chunk["text"] for chunk in chunks]
    vectors = embedding_service.embed_passages(chunk_texts)
    VectorStore().upsert(chunks, vectors)
    database.set_document_status(document_id, "READY", len(chunks))

Đây là thứ tự phải thuộc:

1. SQLite tạo document PROCESSING.
2. Loader trích text và vị trí thật.
3. Chunking chia text, giữ metadata.
4. List comprehension lấy text của mỗi chunk.
5. E5 local tạo vectors.
6. Qdrant upsert vector + payload.
7. Chỉ Qdrant thành công mới set READY.

Nếu một bước lỗi, except đổi status thành FAILED. READY không có nghĩa chỉ upload xong, mà là vector đã ghi xong.

### app/services/document_loader.py

    with fitz.open(path) as pdf:
        return [{"text": page.get_text("text"), "location": f"trang {index + 1}"}
                for index, page in enumerate(pdf) if page.get_text("text").strip()]

- fitz là PyMuPDF.
- enumerate trả index và page.
- index + 1 để trang hiển thị bắt đầu từ 1.
- List comprehension chỉ giữ page có text.
- location là citation metadata thật, Gemini không tự đoán trang.

DOCX dùng python-docx lấy paragraph. PPTX dùng python-pptx duyệt slide/shape. TXT dùng errors=replace để lỗi encoding không crash. PDF scan chỉ là ảnh không có text, hệ thống báo cần OCR.

### app/services/chunking.py

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=settings.chunk_size,
        chunk_overlap=settings.chunk_overlap,
        separators=["\n\n", "\n", ". ", " ", ""],
    )

- Đây là class của thư viện LangChain Text Splitters, không phải class project.
- Nó ưu tiên cắt đoạn rồi dòng, câu, space, cuối cùng mới cắt ký tự.
- chunk size 900 và overlap 150 là ký tự.
- Overlap giữ ý ở ranh giới chunk.

    chunks.append({"text": content, "document_id": document_id, "filename": filename,
                   "location": unit["location"], "chunk_index": len(chunks)})

- Mỗi chunk là dict text + metadata.
- document_id dùng filter Qdrant.
- filename/location/chunk_index đi đến citation UI.

---

## 5. E5 embedding: chỗ thầy hay hỏi kỹ

### app/services/embedding_service.py

    def _load(self):
        if self._model is None:
            from huggingface_hub import snapshot_download
            from sentence_transformers import SentenceTransformer

- _load là helper nội bộ.
- is None kiểm tra chưa nạp model.
- Lazy loading giúp FastAPI mở nhanh; chỉ load E5 khi upload/chat đầu tiên.
- Lần sau self._model đã có, không nạp weights lại.

    local_model_path = snapshot_download(
        settings.embedding_model,
        local_files_only=True,
    )
    self._model = SentenceTransformer(local_model_path, local_files_only=True)
    return self._model

- Model ID lấy từ config.
- local_files_only=True ép dùng snapshot local, tránh treo do Internet khi demo.
- SentenceTransformer tạo object model.
- return self._model trả model đang cache RAM.

    def embed_passages(self, chunks: list[str]) -> list[list[float]]:
        return self._load().encode(
            ["passage: " + text for text in chunks],
            normalize_embeddings=True,
        ).tolist()

- Input là list text chunks.
- passage: là prefix E5 cho document.
- encode là embedding inference: text vào, vector số ra; không sinh câu trả lời.
- tolist đổi numpy array sang list Python cho Qdrant.

    def embed_query(self, question: str) -> list[float]:
        return self._load().encode(
            "query: " + question,
            normalize_embeddings=True,
        ).tolist()

- Query là một string, nên output một vector.
- query: khác passage: do quy ước E5 query-document.

### Đáp án normalize_embeddings=True

“Normalization đưa vector về độ dài 1. Qdrant dùng cosine similarity nên so hướng ngữ nghĩa ổn định hơn, không bị độ dài vector ảnh hưởng. E5 document và query đều normalize cùng cách.”

### Tại sao multilingual-e5-small?

“Dữ liệu tiếng Việt nên cần embedding đa ngôn ngữ. Bản small nhẹ, chạy local tốt trên laptop. Model lớn có thể tốt hơn nhưng nặng RAM/GPU và tăng rủi ro demo.”

---

## 6. Qdrant: vector database

### app/services/vector_store.py

    class VectorStore:
        def __init__(self) -> None:
            settings.qdrant_dir.mkdir(parents=True, exist_ok=True)
            self.client = QdrantClient(path=str(settings.qdrant_dir))

- Đây là class wrapper/repository; lớp cha ngầm định object.
- mkdir tạo folder nếu thiếu, không lỗi nếu đã có.
- QdrantClient path nghĩa Qdrant Local tại data/qdrant, không cần Docker/cloud.

    vector_config = models.VectorParams(
        size=vector_size,
        distance=models.Distance.COSINE,
    )

- vector_size lấy từ output E5, không hard-code.
- COSINE phù hợp vectors E5 normalized.

    points = [
        models.PointStruct(id=str(uuid4()), vector=vector, payload=chunk)
        for chunk, vector in zip(chunks, vectors)
    ]
    self.client.upsert(collection_name=COLLECTION, points=points, wait=True)

- zip ghép chunk i với vector i.
- UUID là ID point Qdrant.
- payload=chunk giữ text và metadata cùng vector.
- wait=True nghĩa ghi xong mới trả control, nên READY đáng tin.

    document_condition = models.FieldCondition(
        key="document_id",
        match=models.MatchAny(any=document_ids),
    )
    query_filter = models.Filter(must=[document_condition])

- Filter bắt buộc chunk thuộc một trong document IDs user chọn.

    result = self.client.query_points(
        collection_name=COLLECTION,
        query=vector,
        query_filter=query_filter,
        limit=limit,
        with_payload=True,
    )

- query là vector câu hỏi.
- limit là Top-K.
- with_payload lấy text/location/filename để RAG tạo answer và citation.

Qdrant không thay SQLite: Qdrant tìm vector giống nghĩa; SQLite lưu registry, status và chat history.

---

## 7. Luồng Chat: question -> answer

### app/api/chat.py

    conversation = payload.conversation_id or history_service.new_conversation()["id"]

- payload là ChatRequest đã validate.
- Có ID thì dùng chat cũ, chưa có thì tạo conversation mới.

    result = answer_question(
        payload.question,
        payload.selected_document_ids,
        database.get_messages(conversation),
    )

- SQLite lấy history trước current turn.
- Route chỉ validate/chuyển giao; RAG logic ở service.

    history_service.save_turn(conversation, payload.question, result["answer"],
                              result.get("citations", []))
    return {**result, "conversation_id": conversation}

- Lưu user, assistant và citation sau khi có result.
- Response trả conversation ID để Streamlit dùng ở câu tiếp.

### app/services/rag_service.py

    if not selected_document_ids:
        return {"answer": "Hãy chọn ít nhất một tài liệu đã index.",
                "citations": [], "debug": {}}

Guard clause: user chưa chọn tài liệu thì dừng, không search toàn KB và không gọi Gemini.

    if conversation_context and len(question.split()) < 12:
        recent = " ".join(item["content"] for item in conversation_context[-2:]
                         if item["role"] == "user")
        retrieval_question = f"{recent} {question}".strip()

- Câu follow-up ngắn như “còn gì nữa?” thiếu chủ ngữ.
- Ghép câu user gần nhất giúp retrieval hiểu chủ đề.
- Chỉ lấy hai message, tránh query dài vô hạn.

    query_vector = embedding_service.embed_query(retrieval_question)
    retrieved = [Evidence(...) for item in VectorStore().search(
        query_vector, selected_document_ids, settings.top_k)]

- E5 local tạo vector câu hỏi.
- Qdrant search Top-K và document filter.
- Evidence là dataclass giúp các field text/score/filename/location/chunk_id rõ ràng.

    if not retrieved:
        return {"answer": "Tôi chưa tìm thấy đủ thông tin...", "citations": [], ...}

Đây là evidence gate. Hàm return ngay nên Gemini phía dưới không thể chạy. Đây là hàng rào chống hallucination.

    context = "\n\n".join(item.text for item in retrieved)
    citations = [{"filename": x.filename, "location": x.location,
                  "chunk_id": x.chunk_id} for x in retrieved]
    return {"answer": generate_answer(question, context, conversation_context),
            "citations": citations, "debug": {...}}

- Context chỉ là Top-K chunks, không gửi cả PDF cho Gemini.
- Citation lấy payload metadata, không để Gemini bịa nguồn.
- Debug dùng trang Góc kiểm tra.

---

## 8. Gemini: gắn model ở đâu, inference ở đâu?

### app/services/llm_service.py

    if not settings.gemini_api_key:
        raise LlmUnavailable("Chưa cấu hình GEMINI_API_KEY ở backend.")

- Chặn trước nếu thiếu key.
- chat.py bắt exception này và trả HTTP 503.

    from google import genai
    client = genai.Client(api_key=settings.gemini_api_key)

- Google Gen AI SDK.
- API key chỉ ở backend environment, không đi tới Streamlit/browser.

    recent_history = (conversation_context or [])[-4:]

- Nếu history None thì dùng list rỗng.
- Chỉ lấy 4 messages gần để prompt không phình vô hạn.

    response = client.models.generate_content(
        model=settings.gemini_model,
        contents=prompt,
    )
    return response.text or "Tôi chưa tạo được câu trả lời từ evidence."

- Đây là dòng Gemini generation inference.
- Model ID đi: .env -> Settings.gemini_model -> generate_content.
- Gemini chạy trên hạ tầng Google cloud. E5 chạy local.
- Prompt có instruction, history ngắn, Top-K evidence và câu hỏi.

### Tại sao Gemini Flash?

“Bài RAG cần phản hồi nhanh và scope demo. Flash cân bằng latency/chi phí. Chất lượng phụ thuộc retrieval evidence trước, không chỉ model lớn. Một provider giúp baseline dễ test; OmniRoute/multi-provider là hướng mở rộng.”

---

## 9. SQLite, history và Streamlit

### app/db/database.py

    def connection() -> sqlite3.Connection:
        settings.db_path.parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(settings.db_path)
        conn.row_factory = sqlite3.Row
        return conn

- Mỗi thao tác có connection mới, tránh chia sẻ giữa request.
- row_factory cho phép đọc row theo tên cột.

Ba bảng:

- documents: filename, hash, source path, PROCESSING/READY/FAILED.
- conversations: mỗi cuộc chat một ID.
- messages: role, content, citations JSON.

### frontend/streamlit_app.py

    def chat_messages() -> list[dict[str, Any]]:
        return st.session_state.setdefault("messages", [])

- session_state là memory theo browser tab.
- setdefault tạo list nếu Streamlit reconnect/refresh làm key mất, tránh AttributeError.
- SQLite mới là persistence lâu dài.

    if conversation_id and not chat_messages():
        st.session_state["messages"] = load_conversation_messages(conversation_id)

- UI reload thì API đọc messages từ SQLite và nạp lại chat.
- Đó là lý do câu đầu không mất khi chat tiếp.

    for message in messages:
        with st.chat_message(message["role"], avatar=avatar):
            st.markdown(message["content"])
            show_citations(message.get("citations", []))

- Render toàn history trước.
- Sau đó input mới append user, API trả result, rồi append assistant.

Delete document xóa theo thứ tự: Qdrant points đúng document ID, file gốc nếu nằm an toàn trong data/uploads, sau đó SQLite record. Nó không xóa source code hay file batch data/documents.

## 10. File còn lại

| File | Vai trò | Ai gọi |
|---|---|---|
| history_service.py | Tạo conversation và lưu turn, che SQL khỏi route. | chat.py |
| api/debug.py | Trả model/Top-K/docs READY, không lộ API key. | Góc kiểm tra |
| evaluation_service.py | Chạy case, đo latency, so should_answer. | evaluation |
| scripts/index_documents.py | Index batch bằng đúng index_file pipeline. | Terminal |
| tests/test_rag.py | Test clean text và metadata chunk, không tải model. | pytest |

## 11. Luyện vấn đáp 15 phút

1. Mở frontend/streamlit_app.py, tìm đường dẫn chat: UI chỉ gọi API.
2. Mở app/api/chat.py, chỉ answer_question: route validate và chuyển giao.
3. Mở rag_service.py, chỉ if not retrieved: evidence gate.
4. Mở embedding_service.py: query, passage, normalize, local inference.
5. Mở vector_store.py: cosine, Top-K, document filter, payload.
6. Mở llm_service.py: generate_content là Gemini cloud inference.
7. Mở ingestion_service.py: kể pipeline upload -> READY.
8. Mở Góc kiểm tra: chứng minh evidence/citation thật.

### Câu chốt

“Em tách UI, API, service và data layer. Streamlit hiển thị; FastAPI nhận/validate HTTP; ingestion tạo Knowledge Base; E5 tạo vector local; Qdrant retrieval; evidence gate chống hallucination; Gemini chỉ sinh answer sau evidence; SQLite giữ trạng thái và history. Vì vậy em lần được input, hàm gọi tiếp theo và output của từng đoạn code.”
