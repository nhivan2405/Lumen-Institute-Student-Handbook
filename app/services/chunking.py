"""Làm sạch và chia text bằng LangChain Text Splitters, giữ metadata nguồn."""
import re
from langchain_text_splitters import RecursiveCharacterTextSplitter
from app.core.config import settings

def clean_text(text: str) -> str:
    """Chuẩn hóa khoảng trắng nhưng vẫn giữ một dòng trống làm ranh giới đoạn."""
    text_without_extra_spaces = re.sub(r"[ \t]+", " ", text)
    text_without_trailing_line_spaces = re.sub(r" *\n *", "\n", text_without_extra_spaces)
    return re.sub(r"\n{3,}", "\n\n", text_without_trailing_line_spaces).strip()

def split_units(units: list[dict], document_id: str, filename: str) -> list[dict]:
    """Chia bằng RecursiveCharacterTextSplitter; size/overlap là ký tự, không phải token.

    Splitter ưu tiên ranh giới đoạn/câu trước khi buộc phải cắt, nên ngữ nghĩa ít bị
    đứt hơn việc cắt cố định theo index. Payload metadata được chép cho từng chunk.
    """
    chunks: list[dict] = []
    if settings.chunk_overlap >= settings.chunk_size:
        raise ValueError("CHUNK_OVERLAP phải nhỏ hơn CHUNK_SIZE.")
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=settings.chunk_size,
        chunk_overlap=settings.chunk_overlap,
        separators=["\n\n", "\n", ". ", " ", ""],
    )
    for unit in units:
        text = clean_text(unit["text"])
        for content in splitter.split_text(text):
            if len(content.strip()) >= 30:
                chunks.append({"text": content, "document_id": document_id, "filename": filename,
                               "location": unit["location"], "chunk_index": len(chunks)})
    return chunks
