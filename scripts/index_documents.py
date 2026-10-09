"""Index data/documents bằng cùng pipeline với upload UI."""
from pathlib import Path
import sys

# Khi chạy trực tiếp `python scripts/index_documents.py`, Python chỉ tự thêm thư
# mục scripts vào import path. Thêm project root để vẫn import được package app.
PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.db.database import init_db
from app.core.config import settings
from app.services.ingestion_service import index_folder

def main() -> None:
    init_db()
    for result in index_folder(settings.documents_dir):
        print(f"{result['filename']}: {result['status']}")

if __name__ == "__main__": main()
