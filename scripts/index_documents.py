"""Index data/documents bằng cùng pipeline với upload UI."""
from app.db.database import init_db
from app.core.config import settings
from app.services.ingestion_service import index_folder

def main() -> None:
    init_db()
    for result in index_folder(settings.documents_dir):
        print(f"{result['filename']}: {result['status']}")

if __name__ == "__main__": main()
