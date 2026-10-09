# Thông tin bài nộp RAG Chatbot

## Sinh viên

- Họ và tên: Văn Phạm Thảo Nhi
- MSSV: 23110049
- Học phần: New Technologies in Software Engineering

## Chủ đề

Xây dựng chatbot RAG trả lời câu hỏi chỉ từ Knowledge Base `KB-A_Lumen-Institute-Student-Handbook.md`.

## Công nghệ sử dụng

| Thành phần | Công nghệ |
|---|---|
| Giao diện | Streamlit |
| Backend | FastAPI và Uvicorn |
| LLM | Gemini API `gemini-3.1-flash-lite` |
| Embedding | `intfloat/multilingual-e5-small` |
| Vector database | Qdrant Local |
| Chunking | LangChain RecursiveCharacterTextSplitter |
| Lưu lịch sử | SQLite |
| Kiểm thử | pytest |

## Điểm chính của hệ thống

- Chia Knowledge Base thành chunks, tạo embedding và lưu vào Qdrant Local.
- Trả lời dựa trên chunks retrieve được; không có evidence phù hợp thì từ chối trả lời.
- Mỗi câu trả lời có nội dung phải có citation lấy từ metadata thật của Qdrant: tên tài liệu, Section và chunk ID.
- Debug View hiển thị các chunks Top-K, score và nội dung retrieve để kiểm tra.

## Chạy ứng dụng

```powershell
python -m uvicorn app.main:app --host 127.0.0.1 --port 8123
python -m streamlit run frontend\streamlit_app.py
```
