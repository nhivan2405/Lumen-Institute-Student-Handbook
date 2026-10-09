# Kịch bản ứng biến khi thầy đưa Knowledge Base

Tài liệu này không giả định trước thầy sẽ đưa PDF hay nội dung nào. Nó dùng đúng khung Rô AI hiện tại để xử lý tài liệu thật trong giờ thi.

## 1. Nguyên tắc đầu tiên

Không sửa Gemini trước khi biết lỗi ở đâu. Luồng kiểm tra luôn là:

    File -> extraction -> chunks -> embedding -> retrieval -> context -> Gemini -> answer

Nếu câu trả lời sai, kiểm tra từ trái sang phải. Nếu chunk đúng chưa từng được retrieve thì sửa prompt Gemini không giải quyết gốc lỗi.

## 2. Khi thầy đưa file, làm gì trong 60 giây?

1. Nhìn extension: PDF, DOCX, PPTX hay TXT.
2. Vào Kho tài liệu (Admin), chọn một trong hai hướng: upload trực tiếp hoặc chép file thầy đưa vào data/documents rồi bấm Index thư mục documents.
3. Nếu READY: qua Hỏi Rô, tick đúng tên file, hỏi một câu có đáp án rõ trong tài liệu.
4. Mở Góc kiểm tra câu trả lời: chỉ cho thầy Top-K chunks, score, filename, location và citation.
5. Chỉ khi evidence đúng mà answer chưa tốt mới xem prompt/model.

## 3. Ma trận các tình huống thầy có thể kiểm tra

| Tình huống | Khung hiện tại làm gì? | Bạn nói gì với thầy? | File code nên mở |
|---|---|---|---|
| Thầy đưa DOCX thay PDF | Loader detect suffix và đưa DOCX vào python-docx; pipeline phía sau không đổi. | “Em tách extraction theo format. Sau khi có normalized text, chunking/embedding/retrieval dùng chung.” | app/services/document_loader.py |
| Thầy đưa PPTX | Duyệt từng slide/text shape và giữ location là slide N. | “Metadata slide đi cùng chunk nên citation không do LLM tự bịa.” | document_loader.py |
| Thầy đưa TXT | Đọc text với errors=replace để không crash encoding. | “TXT chỉ khác extraction. Sau đó dùng chung ingestion pipeline.” | document_loader.py |
| PDF có text thật | PyMuPDF extract text từng page, citation là trang N. | “Page metadata được tạo ở loader trước RAG.” | document_loader.py |
| PDF scan chỉ là ảnh | Không có text, chunks rỗng, document thành FAILED và báo cần OCR. | “Em nhận diện failure nằm ở extraction, không đổ lỗi Gemini. OCR là hướng mở rộng đã tách boundary sẵn.” | document_loader.py, ingestion_service.py |
| File rất dài/xấu | Cleaning và RecursiveCharacterTextSplitter chia theo đoạn/dòng/câu, có overlap. | “Chunk size/overlap là config cần đánh giá trên corpus, không phải con số thần thánh.” | chunking.py, .env |
| Hỏi ngoài tài liệu | Qdrant không có evidence, gate return trước Gemini. | “Đây là closed-domain RAG; em từ chối thay vì dùng kiến thức nền model.” | rag_service.py |
| Hỏi có vẻ liên quan nhưng KB không nói | Evidence không đủ thì phải từ chối; không suy diễn chính sách mới. | “Citation không đủ để suy ra kết luận, nên em không hallucinate.” | rag_service.py |
| Thầy hỏi Top-K là gì | Qdrant lấy tối đa K chunks rồi đưa chúng vào context. | “K nhỏ có thể thiếu evidence; K quá lớn tăng noise, latency và token cost.” | config.py, vector_store.py |
| Thầy hỏi đổi Gemini | Chỉ đổi GEMINI_MODEL/.env hoặc LLM adapter, không re-index. | “Generation model không đổi vector space.” | config.py, llm_service.py |
| Thầy hỏi đổi E5 | Phải re-embed và re-index KB. | “Embedding model mới có vector space/dimension khác.” | embedding_service.py |

## 4. Những gì project này đã có sẵn để ứng biến

### A. Multi-format loader

Project đã hỗ trợ PDF, DOCX, PPTX, TXT. Không có tên file hard-code. Hàm index_file nhận Path bất kỳ, loader dựa vào suffix.

### B. Closed-domain evidence gate

Trong rag_service.py có nhánh:

    if not retrieved:
        return refusal

Đây là bằng chứng Gemini không được gọi khi Qdrant không tìm được chunk. Hãy chỉ đúng dòng này nếu thầy hỏi chống hallucination.

### C. Debug RAG

Góc kiểm tra câu trả lời hiển thị:

- model embedding và generation thực tế;
- Top-K;
- retrieval question;
- từng chunk source/location/score;
- đoạn text nguồn.

Đây là chứng cứ RAG hoạt động, không phải chỉ nói “em đã dùng AI”.

### D. Admin/User flow

- Admin upload, re-index, đổi tên hoặc xóa KB.
- User chọn tài liệu READY rồi chat.
- Chưa có authentication/RBAC vì scope lab local; đây là phân tách luồng chức năng. Nếu production, thêm login và kiểm tra quyền ở backend API.

## 5. Giới hạn phải nói thật

| Giới hạn hiện tại | Không được nói sai | Hướng mở rộng đúng |
|---|---|---|
| PDF scan | Không nói hệ thống đã OCR. | Thêm OCR sau khi extraction không có text. |
| Table phức tạp | Không khẳng định bảo toàn mọi cell/bảng. | Thêm table-aware extraction theo corpus. |
| Evaluation | Có service/evaluation dataset cơ bản, chưa là dashboard chấm điểm lớn. | Mở rộng dataset có expected source/chunk và retrieval metrics. |
| Authentication | Không có login thật. | Thêm RBAC tại FastAPI trước route quản trị. |

Nói giới hạn rõ ràng được điểm hơn là hứa tính năng không có.

## 6. Khi câu trả lời sai, debug theo thứ tự

1. Có chọn đúng tài liệu READY không?
2. Upload có thành READY hay FAILED?
3. Loader extract được text chưa? PDF scan thì chưa.
4. Chunk có bị quá lớn/quá nhỏ hoặc mất section quan trọng không?
5. Góc kiểm tra có retrieve đúng chunk không?
6. Score/evidence có thật sự đủ để trả lời không?
7. Context gửi Gemini có đúng không?
8. Cuối cùng mới đánh giá Gemini/prompt.

## 7. Câu trả lời kiến trúc khi thầy đổi đề

> “Dù thầy đổi PDF sang Word, đổi Gemini sang provider khác, hoặc đổi Qdrant sang vector database khác, data flow vẫn là extract -> chunk -> embed -> index -> query embed -> retrieve -> augment -> generate. Em tách loader, embedding, vector store và LLM service thành các boundary riêng nên thay đổi một dependency không làm em xây lại toàn bộ UI hoặc pipeline.”

## 8. Checklist mang vào thi

- Không hard-code tên file.
- Chọn đúng tài liệu trước khi hỏi.
- Không trả lời ngoài evidence.
- Khi answer sai, mở Góc kiểm tra trước.
- Nói rõ E5 local là embedding, Gemini cloud là generation.
- Đổi E5 phải re-index; đổi Gemini thường không phải.
- Với PDF scan: nói đúng là cần OCR, không đổ lỗi LLM.
