# Trợ Lý Rô AI

> Hỏi tài liệu, Rô tìm giúp bạn.

Khung lab RAG phục vụ demo và vấn đáp: tài liệu được tải lên, tách đoạn, embedding local, truy xuất Qdrant và chỉ khi có bằng chứng mới gọi Gemini để sinh câu trả lời. Hiện repository là **khung mã nguồn chưa cài dependency/chưa tải model/chưa gọi Gemini**.

## Chạy sau khi đã duyệt cài đặt

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env
python -m uvicorn app.main:app --host 127.0.0.1 --port 8123
# Một PowerShell khác:
streamlit run frontend/streamlit_app.py
```

Xem [kế hoạch môi trường](docs/00_MOI_TRUONG_VA_THU_VIEN.md) trước khi cài. Không commit `.env`, vector database, file upload hoặc model weights.
