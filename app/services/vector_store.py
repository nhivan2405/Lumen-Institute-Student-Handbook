"""Qdrant Local: lưu vector cùng payload metadata và filter theo document_id."""
from uuid import uuid4
from qdrant_client import QdrantClient, models
from app.core.config import settings

COLLECTION = "ro_ai_chunks"

class VectorStore:
    """Repository giao tiếp Qdrant; các service khác không cần biết Qdrant API chi tiết."""

    def __init__(self) -> None:
        # Qdrant Local ghi dữ liệu vào project, không cần Docker hay cloud account.
        settings.qdrant_dir.mkdir(parents=True, exist_ok=True)
        self.client = QdrantClient(path=str(settings.qdrant_dir))

    def _ensure_collection(self, vector_size: int) -> None:
        """Tạo collection một lần với cosine vì vector E5 đã được normalize."""
        if not self.client.collection_exists(COLLECTION):
            vector_config = models.VectorParams(
                size=vector_size,
                distance=models.Distance.COSINE,
            )
            self.client.create_collection(
                COLLECTION,
                vectors_config=vector_config,
            )

    def upsert(self, chunks: list[dict], vectors: list[list[float]]) -> None:
        """Lưu mỗi vector kèm payload chunk để sau này tạo citation từ metadata thật."""
        self._ensure_collection(len(vectors[0]))
        points = [
            models.PointStruct(
                id=str(uuid4()),
                vector=vector,
                payload=chunk,
            )
            for chunk, vector in zip(chunks, vectors)
        ]
        self.client.upsert(collection_name=COLLECTION, points=points, wait=True)

    def search(self, vector: list[float], document_ids: list[str], limit: int) -> list[dict]:
        """Tìm Top-K nhưng chỉ trong các document ID do người dùng chọn."""
        if not self.client.collection_exists(COLLECTION):
            return []
        document_condition = models.FieldCondition(
            key="document_id",
            match=models.MatchAny(any=document_ids),
        )
        query_filter = models.Filter(must=[document_condition])
        result = self.client.query_points(
            collection_name=COLLECTION,
            query=vector,
            query_filter=query_filter,
            limit=limit,
            with_payload=True,
        )
        return [{**point.payload, "score": point.score} for point in result.points]

    def delete_document(self, document_id: str) -> None:
        """Xóa toàn bộ vectors mang document ID, không đụng vectors tài liệu khác."""
        if not self.client.collection_exists(COLLECTION):
            return
        document_condition = models.FieldCondition(
            key="document_id",
            match=models.MatchValue(value=document_id),
        )
        delete_filter = models.Filter(must=[document_condition])
        self.client.delete(
            collection_name=COLLECTION,
            points_selector=models.FilterSelector(filter=delete_filter),
            wait=True,
        )

    def rename_document_payload(self, document_id: str, filename: str) -> None:
        """Đổi filename trong payload mọi chunk để chat/debug/citation dùng tên mới."""
        if not self.client.collection_exists(COLLECTION):
            return
        document_filter = models.Filter(
            must=[models.FieldCondition(key="document_id", match=models.MatchValue(value=document_id))]
        )
        self.client.set_payload(
            collection_name=COLLECTION,
            payload={"filename": filename},
            points=models.FilterSelector(filter=document_filter),
            wait=True,
        )
