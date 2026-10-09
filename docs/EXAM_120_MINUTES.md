# Midterm Build a RAG Chatbot

## Quy trình 120 phút

1. Phút 0-10: kiểm tra `.env`, cache E5, đặt KB Lumen vào `data/documents`.
2. Phút 10-25: chạy `python scripts/index_documents.py`; xác nhận `READY` và số chunks.
3. Phút 25-50: chạy FastAPI, Streamlit, hỏi một câu có đáp án và mở Debug.
4. Phút 50-90: chạy các câu Section 11 và câu ngoài KB; sửa một dòng comment/threshold khi giảng viên yêu cầu.
5. Phút 90-120: chạy pytest, xem `git status`, commit và push nhánh.

## Luồng cần giải thích

- `document_loader.py`: Markdown UTF-8 được tách theo heading `##`, nên giữ Section 1-12.
- `chunking.py`: `RecursiveCharacterTextSplitter`, size 900, overlap 150; payload có `document_id`, `filename`, `section`, `chunk_index`.
- `embedding_service.py`: E5 dùng `passage:` khi index và `query:` khi tìm; normalize embeddings.
- `vector_store.py`: Qdrant Local lưu payload, search Top-K có filter `document_id`.
- `rag_service.py`: evidence gate chạy trước Gemini; citation lấy từ payload thật. Score cosine không phải xác suất đúng.
- `llm_service.py`: Gemini chỉ nhận question và evidence; Section 11 được ưu tiên nếu evidence nói rõ quy tắc ghi đè.

## 10 câu kiểm tra

| Câu hỏi | Kỳ vọng từ KB |
|---|---|
| Phí thi bù hiện hành? | 200,000 VND, Section 11 |
| Thi bù vì bệnh có giấy bệnh viện? | Miễn phí, Section 11 và 7 |
| Phí trả sách muộn trước 01/01/2027? | 2,000 VND/sách/ngày, Section 5 |
| Từ 01/01/2027 phí trả sách muộn? | 3,000 VND/sách/ngày, Section 11 |
| Honors có trả góp học phí không? | Không, Section 11 ghi đè Section 3 |
| Standard GPA 3.5 overload bao nhiêu? | Tối đa 27 credits, Section 4 |
| Probation có overload không? | Không, Section 4 |
| Điều kiện Aurora? | GPA 3.8 và conduct 90; 100% tuition, Section 6 |
| Honors mượn sách thế nào? | 10 sách trong 28 ngày, Section 5 |
| Điều kiện tốt nghiệp? | Credits chương trình, B2/IELTS 5.5, GPA 2.0, Section 10 |

Hỏi thêm một câu không nằm trong handbook (ví dụ dự báo thời tiết). Bot phải trả lời: `Tôi không tìm thấy thông tin này trong Knowledge Base.`

## Khi Gemini hết quota

Không mất Qdrant/SQLite hay lịch sử chat. Kiểm tra `GEMINI_MODEL` và API key trong `.env`, dùng model/provider dự phòng chỉ khi đã được cấu hình hợp lệ, hoặc chờ quota rồi gửi lại câu hỏi. Debug retrieval vẫn giúp chứng minh chunks đã tìm được.

## Checklist trước khi push

- [ ] Chỉ chọn KB Lumen khi demo.
- [ ] KB index `READY`.
- [ ] Debug hiển thị chunks, score, filename, Section và chunk ID.
- [ ] Câu ngoài KB bị từ chối.
- [ ] Test Section 11 đúng.
- [ ] `pytest tests -q -p no:cacheprovider` đã chạy.
- [ ] `.env`, `data/qdrant`, database và uploads không được commit.
