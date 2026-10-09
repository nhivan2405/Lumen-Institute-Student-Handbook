"""Một pipeline dùng chung cho upload UI và scripts/index_documents.py."""
from hashlib import sha256
from pathlib import Path
import shutil
from app.core.config import settings
from app.db import database
from app.services.document_loader import extract_document, SUPPORTED_EXTENSIONS
from app.services.chunking import split_units
from app.services.embedding_service import embedding_service
from app.services.vector_store import VectorStore


def index_folder(folder: Path) -> list[dict]:
    """Index toàn bộ file hợp lệ trong một thư mục bằng cùng pipeline upload.

    Dùng cho Knowledge Base đặt sẵn tại data/documents. Mỗi file lỗi được trả
    thành kết quả FAILED riêng, không làm dừng các file khác trong thư mục.
    """
    folder.mkdir(parents=True, exist_ok=True)
    results: list[dict] = []

    for source in sorted(folder.iterdir()):
        if not source.is_file() or source.suffix.lower() not in SUPPORTED_EXTENSIONS:
            continue
        try:
            results.append(index_file(source, copy_to_uploads=False))
        except Exception as error:
            results.append({"filename": source.name, "status": "FAILED", "error_message": str(error)})
    return results

def index_file(
    source: Path,
    copy_to_uploads: bool = True,
    original_filename: str | None = None,
) -> dict:
    """Index một file theo pipeline extract → chunk → embed → Qdrant.

    READY chỉ được gán sau Qdrant upsert thành công. Nếu một bước lỗi, registry
    SQLite được đổi sang FAILED để UI không đánh lừa người dùng.
    """
    display_filename = original_filename or source.name
    if Path(display_filename).suffix.lower() not in SUPPORTED_EXTENSIONS:
        raise ValueError("Định dạng không được hỗ trợ.")
    if not source.is_file() or source.stat().st_size == 0:
        raise ValueError("Tệp không tồn tại hoặc rỗng.")
    maximum_size_bytes = settings.max_upload_mb * 1024 * 1024
    if source.stat().st_size > maximum_size_bytes:
        raise ValueError(f"Tệp vượt quá giới hạn {settings.max_upload_mb} MB.")

    # Hash file dùng phát hiện duplicate, không dùng filename vì tên có thể trùng.
    digest = sha256(source.read_bytes()).hexdigest()
    duplicate = database.find_document_hash(digest)
    if duplicate:
        return {**duplicate, "duplicate": True}
    # Lưu bản gốc vào uploads để re-index được sau restart.
    settings.upload_dir.mkdir(parents=True, exist_ok=True)
    stored = settings.upload_dir / f"{digest[:12]}_{display_filename}"
    if copy_to_uploads and source.resolve() != stored.resolve():
        shutil.copy2(source, stored)
    else:
        stored = source
    document_id = database.create_document(display_filename, digest, str(stored))

    try:
        # Loader giữ metadata vị trí (trang/slide) để citation không do LLM bịa.
        units = extract_document(stored)
        chunks = split_units(units, document_id, display_filename)
        if not chunks:
            raise ValueError("Không trích xuất được text; PDF scan/ảnh cần OCR (chưa triển khai).")
        chunk_texts = [chunk["text"] for chunk in chunks]
        vectors = embedding_service.embed_passages(chunk_texts)

        vector_store = VectorStore()
        vector_store.upsert(chunks, vectors)

        database.set_document_status(document_id, "READY", len(chunks))
        return database.get_document(document_id) or {}
    except Exception as error:
        # Lỗi loader/model/Qdrant phải hiện lý do, nhưng không làm hỏng document cũ.
        database.set_document_status(document_id, "FAILED", error=str(error))
        raise
