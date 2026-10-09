# Bộ câu hỏi vấn đáp cốt lõi

1. **Embedding khác Gemini generation thế nào?** Embedding trả vector số để tìm đoạn gần nghĩa; Gemini tạo văn bản. Trong code lần lượt là `model.encode()` và `generate_content()`.
2. **E5 chạy ở đâu?** Trong process backend trên thiết bị local chạy Python; CPU/GPU tùy môi trường.
3. **Gemini chạy ở đâu?** Request API rời backend đến hạ tầng Google; API key chỉ tồn tại ở backend `.env`.
4. **Tại sao `query:` và `passage:`?** E5 được huấn luyện theo hai vai trò; bỏ prefix có thể làm retrieval kém hơn.
5. **Vì sao normalize vector?** Để phép đo cosine/dot product không bị độ dài vector chi phối.
6. **Đổi Gemini có phải re-index?** Thường không, vì Qdrant chứa embedding. Đổi embedding model thì phải re-index.
7. **Top-K có phải xác suất đúng?** Không. Đó là số chunks gần nhất; score similarity không phải xác suất correctness.
8. **Citation lấy ở đâu?** Metadata lúc loader đọc file (tên, trang/slide/section) được giữ trong Qdrant payload và gửi ra từ `Evidence`.
9. **Vì sao không gửi cả PDF Gemini?** Tốn token, chậm, khó kiểm tra nguồn; RAG chỉ gửi bằng chứng liên quan.
10. **Evidence gate làm gì?** Nếu evidence trống/yếu, từ chối trước generation để giữ closed-domain.
11. **Tại sao Qdrant và SQLite cùng tồn tại?** Qdrant tối ưu nearest-neighbor vector; SQLite tối ưu registry/hội thoại/transaction đơn giản.
12. **Vì sao chọn Gemini Flash-Lite?** Mục tiêu baseline là latency/chi phí nhẹ qua API. Cần kiểm tra model ID, quota và chính sách tài khoản thật trước khi khẳng định khả dụng.
13. **Vì sao không dùng LLM local?** Tăng yêu cầu RAM/VRAM và thời gian setup, không phù hợp baseline phòng thi; embedding local vẫn giúp phần retrieval chạy trên máy.
14. **Gemini API hỏng thì sao?** Không mất index/lịch sử; API trả lỗi rõ, người dùng thử lại sau. Không thay bằng câu trả lời giả.
15. **OmniRoute có dùng không?** Không. Khung hiện gọi Gemini trực tiếp để luồng inference dễ giải thích. Chỉ thêm router khi có yêu cầu đổi/so sánh nhiều provider cụ thể.

