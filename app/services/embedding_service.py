"""Ranh giới embedding local: không sinh câu trả lời và không gọi Gemini."""
from app.core.config import settings

class EmbeddingService:
    """Bọc E5 để index/query luôn cùng model, chiều vector và normalization."""
    def __init__(self) -> None:
        self._model = None

    def _load(self):
        """Load E5 một lần từ cache local; không treo upload vì thử gọi Internet.

        `local_files_only=True` đúng với baseline lab: model phải được tải sẵn trước
        ngày demo. Nếu thiếu cache, SentenceTransformers báo lỗi ngay để UI ghi FAILED.
        """
        if self._model is None:
            from huggingface_hub import snapshot_download
            from sentence_transformers import SentenceTransformer

            # Resolve repo ID thành đường dẫn snapshot local trước. Nếu đưa repo ID
            # thẳng cho SentenceTransformer, một số phiên bản vẫn HEAD Hugging Face.
            local_model_path = snapshot_download(
                settings.embedding_model,
                local_files_only=True,
            )
            self._model = SentenceTransformer(
                local_model_path,
                local_files_only=True,
            )
        return self._model

    def embed_passages(self, chunks: list[str]) -> list[list[float]]:
        """Tạo vector document với prefix E5 `passage:` để upsert Qdrant."""
        return self._load().encode(
            ["passage: " + text for text in chunks], normalize_embeddings=True
        ).tolist()

    def embed_query(self, question: str) -> list[float]:
        """Tạo vector câu hỏi với `query:`; prefix sai làm giảm chất lượng retrieval."""
        return self._load().encode("query: " + question, normalize_embeddings=True).tolist()

# Một instance/process để model weights không bị nạp lại ở mỗi request.
embedding_service = EmbeddingService()
