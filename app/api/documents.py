"""Upload/list/delete/re-index. File bytes chỉ được ghi vào thư mục uploads nội bộ."""
from pathlib import Path
from tempfile import NamedTemporaryFile
from fastapi import APIRouter, File, HTTPException, UploadFile
from app.db import database
from app.core.config import settings
from app.services.ingestion_service import index_file, index_folder
from app.services.vector_store import VectorStore
from app.schemas import RenameDocumentRequest

router = APIRouter(prefix="/api/documents", tags=["documents"])

@router.get("")
def documents() -> list[dict]:
    """Trả registry cho Streamlit; không trả hash/path nội bộ ở UI layer."""
    return database.list_documents()

@router.post("/upload", status_code=201)
def upload(file: UploadFile = File(...)):
    """Nhận upload HTTP, dùng một temp file rồi chuyển toàn bộ việc cho ingestion service."""
    filename = Path(file.filename or "untitled").name
    suffix = Path(filename).suffix.lower()
    temp_path: Path | None = None

    try:
        with NamedTemporaryFile(delete=False, suffix=suffix) as temp:
            temp.write(file.file.read())
            temp_path = Path(temp.name)

        return index_file(
            temp_path,
            copy_to_uploads=True,
            original_filename=filename,
        )
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
    except Exception as error:
        raise HTTPException(status_code=500, detail=f"Index thất bại: {error}") from error
    finally:
        # Chỉ file tạm bị xóa; bản gốc trong data/uploads vẫn giữ để re-index.
        if temp_path and temp_path.exists():
            temp_path.unlink()


@router.post("/index-folder")
def index_documents_folder() -> list[dict]:
    """Index file được đặt sẵn trong data/documents cho kịch bản Knowledge Base cố định."""
    try:
        return index_folder(settings.documents_dir)
    except Exception as error:
        raise HTTPException(status_code=500, detail=f"Không thể index thư mục documents: {error}") from error

@router.delete("/{document_id}", status_code=204)
def delete_document(document_id: str):
    """Xóa vector, registry và bản gốc upload của đúng tài liệu được chọn."""
    document = database.get_document(document_id)
    if not document:
        raise HTTPException(status_code=404, detail="Không tìm thấy tài liệu.")

    # Chỉ cho phép xóa file nằm *bên trong* data/uploads. Tài liệu index từ
    # data/documents của script được giữ lại, vì đó là thư mục input của project.
    source_path = Path(document["source_path"]).resolve()
    upload_directory = settings.upload_dir.resolve()
    VectorStore().delete_document(document_id)
    if source_path.is_relative_to(upload_directory) and source_path.is_file():
        source_path.unlink()
    database.delete_document_record(document_id)

@router.patch("/{document_id}")
def rename_document(document_id: str, payload: RenameDocumentRequest):
    """Đổi tên hiển thị ở SQLite và Qdrant để citation nhất quán."""
    document = database.get_document(document_id)
    if not document:
        raise HTTPException(status_code=404, detail="Không tìm thấy tài liệu.")
    filename = Path(payload.filename).name
    VectorStore().rename_document_payload(document_id, filename)
    database.rename_document(document_id, filename)
    return database.get_document(document_id)

@router.post("/{document_id}/reindex")
def reindex(document_id: str):
    """Xóa vectors của phiên bản cũ và chạy lại đúng ingestion pipeline từ file đã lưu."""
    document = database.get_document(document_id)
    if not document:
        raise HTTPException(status_code=404, detail="Không tìm thấy tài liệu.")
    VectorStore().delete_document(document_id)
    database.delete_document_record(document_id)
    return index_file(Path(document["source_path"]), copy_to_uploads=False)
