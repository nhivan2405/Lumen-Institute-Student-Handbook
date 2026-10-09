"""Cấu hình tập trung; tách secrets khỏi source code để an toàn khi demo."""
from dataclasses import dataclass
from pathlib import Path
import os

ROOT = Path(__file__).resolve().parents[2]

def _load_env_file() -> None:
    """Đọc `.env` tối thiểu, không cần thêm dependency và không ghi đè biến hệ thống."""
    env_file = ROOT / ".env"
    if not env_file.exists():
        return
    for line in env_file.read_text(encoding="utf-8").splitlines():
        if "=" in line and not line.lstrip().startswith("#"):
            key, value = line.split("=", 1)
            os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))

_load_env_file()

@dataclass(frozen=True)
class Settings:
    """Các giá trị runtime. API key chỉ được đọc ở backend, không gửi về Streamlit."""
    embedding_model: str = os.getenv("EMBEDDING_MODEL", "intfloat/multilingual-e5-small")
    gemini_model: str = os.getenv("GEMINI_MODEL", "gemini-2.5-flash-lite")
    gemini_api_key: str | None = os.getenv("GEMINI_API_KEY")
    top_k: int = int(os.getenv("RAG_TOP_K", "4"))
    evidence_min_score: float = float(os.getenv("RAG_EVIDENCE_MIN_SCORE", "0.45"))
    chunk_size: int = int(os.getenv("CHUNK_SIZE", "900"))
    chunk_overlap: int = int(os.getenv("CHUNK_OVERLAP", "150"))
    max_upload_mb: int = int(os.getenv("MAX_UPLOAD_MB", "20"))
    db_path: Path = ROOT / "data" / "database" / "ro_ai.db"
    upload_dir: Path = ROOT / "data" / "uploads"
    documents_dir: Path = ROOT / "data" / "documents"
    qdrant_dir: Path = ROOT / "data" / "qdrant"

settings = Settings()
