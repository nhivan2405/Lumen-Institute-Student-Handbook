# Môi trường và thư viện

## Trạng thái kiểm chứng ngày 09/10/2026

Project: `E:\NewTech\RAG_Assistant`. Thư mục không phải Git repository. `.venv` hiện có Streamlit 1.65.0, FastAPI 0.143.0, Uvicorn 0.54.0, Qdrant-client 1.19.1, sentence-transformers 3.4.1, google-genai 1.75.0, PyMuPDF 1.28.2, python-docx 1.2.0, python-pptx 1.0.2. Chưa tải/chạy E5-small, chưa đọc/in giá trị `GEMINI_API_KEY`, chưa có Knowledge Base. `pytest` chưa có nên test chưa chạy.

| Nhóm | Dùng để | Cài ở đâu | Tài nguyên/rủi ro | Lệnh dự kiến |
|---|---|---|---|---|
| Streamlit | UI | `.venv` | Nhẹ; không dùng cho secrets | `pip install streamlit` |
| FastAPI/Uvicorn | API backend | `.venv` | Nhẹ | `pip install fastapi uvicorn` |
| sentence-transformers + E5 | embedding local 384D | `.venv` + model cache | Tải model, dùng RAM/CPU | `pip install sentence-transformers` |
| Qdrant local | vector/chunk persistence | `.venv` | Dữ liệu nằm trong project | `pip install qdrant-client` |
| google-genai | Gemini generation API | `.venv` | Cần API key/quota | `pip install google-genai` |
| PyMuPDF/docx/pptx | trích xuất file | `.venv` | Không OCR scan | `pip install pymupdf python-docx python-pptx` |
| LangChain Text Splitters | chia chunks có ranh giới đoạn/câu | `.venv` | Nhẹ, không dùng toàn bộ LangChain | `pip install langchain-text-splitters` |
| pytest | test tự động | `.venv` | Chỉ phục vụ test | `pip install pytest` |

Không cần Docker, OCR, React, PostgreSQL, LangChain hay model LLM local cho baseline. Trước khi cài phải duyệt `requirements.txt` và tạo `.venv` riêng.
