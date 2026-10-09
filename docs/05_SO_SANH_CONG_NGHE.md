# Lý do chọn công nghệ

| Tầng | Chọn baseline | Vì sao | Khi nên thay |
|---|---|---|---|
| UI | Streamlit | Python thuần, demo nhanh | React khi cần UX phức tạp/team frontend |
| API | FastAPI | Schema, docs API, tách UI/service rõ | Flask cho demo cực nhỏ; Django cho web nghiệp vụ lớn |
| Embedding | multilingual-e5-small | Đa ngôn ngữ, chạy local nhẹ | BGE-M3 khi cần retrieval mạnh hơn và đủ tài nguyên |
| Vector DB | Qdrant Local | Filter payload/document ID, persistence local | pgvector khi đã có PostgreSQL; Pinecone khi cần managed cloud |
| Generation | Gemini Flash-Lite API | Không phải host LLM lớn | Flash/GPT/Claude khi chất lượng hoặc ecosystem quan trọng hơn baseline |
| History | SQLite | Không dịch vụ ngoài, restart vẫn còn | PostgreSQL khi concurrent/multi-user thật |

Không dùng React, Docker, OCR, LangChain hoặc OmniRoute trong baseline để giảm bề mặt lỗi. Đây là đánh đổi phạm vi, không có nghĩa chúng kém hơn trong mọi hệ thống.

