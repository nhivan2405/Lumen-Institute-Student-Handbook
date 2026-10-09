"""Test thuần Python, không tải model."""
from app.services.chunking import clean_text, split_units

def test_clean_text_removes_extra_spaces():
    # Khoảng trắng cuối dòng không mang nghĩa, nên được loại bỏ trước khi chunk.
    assert clean_text(" A   B \n\n\n C ") == "A B\n\nC"

def test_chunks_preserve_source_metadata():
    chunks = split_units([{"text": "x" * 100, "location": "trang 2"}], "doc-1", "demo.pdf")
    assert chunks[0]["document_id"] == "doc-1"
    assert chunks[0]["location"] == "trang 2"
