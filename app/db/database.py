"""SQLite giữ registry tài liệu và lịch sử; Qdrant chỉ giữ vector/chunk để truy xuất."""
import sqlite3
from datetime import datetime, timezone
from uuid import uuid4
from app.core.config import settings

def connection() -> sqlite3.Connection:
    """Mở kết nối theo thao tác để tránh chia sẻ connection giữa request FastAPI."""
    settings.db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(settings.db_path)
    conn.row_factory = sqlite3.Row
    return conn

def init_db() -> None:
    """Tạo bảng idempotent; gọi lúc FastAPI khởi động, không xóa dữ liệu cũ."""
    with connection() as conn:
        conn.executescript("""
        CREATE TABLE IF NOT EXISTS documents (
          id TEXT PRIMARY KEY, filename TEXT NOT NULL, status TEXT NOT NULL,
          chunk_count INTEGER DEFAULT 0, error_message TEXT, file_hash TEXT,
          source_path TEXT, created_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS conversations (
          id TEXT PRIMARY KEY, title TEXT NOT NULL, created_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS messages (
          id TEXT PRIMARY KEY, conversation_id TEXT NOT NULL, role TEXT NOT NULL,
          content TEXT NOT NULL, citations_json TEXT, created_at TEXT NOT NULL,
          FOREIGN KEY(conversation_id) REFERENCES conversations(id)
        );
        """)

def now() -> str:
    return datetime.now(timezone.utc).isoformat()

def create_document(filename: str, file_hash: str, source_path: str) -> str:
    document_id = str(uuid4())
    with connection() as conn:
        conn.execute("INSERT INTO documents(id, filename, status, file_hash, source_path, created_at) VALUES(?,?,?,?,?,?)",
                     (document_id, filename, "PROCESSING", file_hash, source_path, now()))
    return document_id

def set_document_status(document_id: str, status: str, chunk_count: int = 0, error: str | None = None) -> None:
    with connection() as conn:
        conn.execute("UPDATE documents SET status=?, chunk_count=?, error_message=? WHERE id=?",
                     (status, chunk_count, error, document_id))

def list_documents() -> list[dict]:
    with connection() as conn:
        return [dict(row) for row in conn.execute("SELECT * FROM documents ORDER BY created_at DESC")]

def get_document(document_id: str) -> dict | None:
    with connection() as conn:
        row = conn.execute("SELECT * FROM documents WHERE id=?", (document_id,)).fetchone()
        return dict(row) if row else None

def find_document_hash(file_hash: str) -> dict | None:
    with connection() as conn:
        row = conn.execute("SELECT * FROM documents WHERE file_hash=? AND status='READY'", (file_hash,)).fetchone()
        return dict(row) if row else None

def delete_document_record(document_id: str) -> None:
    with connection() as conn:
        conn.execute("DELETE FROM documents WHERE id=?", (document_id,))


def delete_conversation(conversation_id: str) -> bool:
    """Xóa message rồi xóa conversation; không ảnh hưởng tài liệu/Qdrant."""
    with connection() as conn:
        exists = conn.execute(
            "SELECT 1 FROM conversations WHERE id=?", (conversation_id,)
        ).fetchone()
        if not exists:
            return False
        conn.execute("DELETE FROM messages WHERE conversation_id=?", (conversation_id,))
        conn.execute("DELETE FROM conversations WHERE id=?", (conversation_id,))
        return True


def rename_document(document_id: str, filename: str) -> None:
    """Đổi tên hiển thị trong registry; vectors được cập nhật payload ở service Qdrant."""
    with connection() as conn:
        conn.execute("UPDATE documents SET filename=? WHERE id=?", (filename, document_id))

def create_conversation(title: str = "Cuộc trò chuyện mới") -> dict:
    value = {"id": str(uuid4()), "title": title, "created_at": now()}
    with connection() as conn:
        conn.execute("INSERT INTO conversations(id,title,created_at) VALUES(:id,:title,:created_at)", value)
    return value

def list_conversations() -> list[dict]:
    """Trả cuộc chat mới nhất kèm câu hỏi đầu để sidebar có tên dễ nhận ra."""
    with connection() as conn:
        rows = conn.execute(
            """
            SELECT conversations.*,
                   COALESCE(
                       (
                           SELECT content
                           FROM messages
                           WHERE messages.conversation_id = conversations.id
                             AND messages.role = 'user'
                           ORDER BY created_at ASC
                           LIMIT 1
                       ),
                       conversations.title
                   ) AS display_title
            FROM conversations
            ORDER BY created_at DESC
            """
        ).fetchall()
        return [dict(row) for row in rows]

def add_message(conversation_id: str, role: str, content: str, citations_json: str = "[]") -> None:
    with connection() as conn:
        conn.execute("INSERT INTO messages(id,conversation_id,role,content,citations_json,created_at) VALUES(?,?,?,?,?,?)",
                     (str(uuid4()), conversation_id, role, content, citations_json, now()))

def get_messages(conversation_id: str, limit: int = 12) -> list[dict]:
    with connection() as conn:
        rows = conn.execute("SELECT * FROM messages WHERE conversation_id=? ORDER BY created_at DESC LIMIT ?", (conversation_id, limit)).fetchall()
        return [dict(row) for row in reversed(rows)]
