"""Test logic/offline; không khẳng định Gemini hoặc Qdrant đã chạy thật."""
from pathlib import Path
import pytest
from app.services.chunking import clean_text, split_units
from app.services.document_loader import extract_document
from app.services.rag_service import Evidence, has_sufficient_evidence

def test_clean_text_removes_extra_spaces():
    # Khoảng trắng cuối dòng không mang nghĩa, nên được loại bỏ trước khi chunk.
    assert clean_text(" A   B \n\n\n C ") == "A B\n\nC"

def test_chunks_preserve_source_metadata():
    chunks = split_units([{"text": "x" * 100, "location": "trang 2"}], "doc-1", "demo.pdf")
    assert chunks[0]["document_id"] == "doc-1"
    assert chunks[0]["location"] == "trang 2"


def test_lumen_markdown_keeps_all_numbered_sections():
    path = Path("data/documents/KB-A_Lumen-Institute-Student-Handbook.md")
    units = extract_document(path)
    assert [unit["section"].split(".")[0] for unit in units] == [str(n) for n in range(1, 13)]


def test_section_11_stays_separate_from_section_7():
    units = extract_document(Path("data/documents/KB-A_Lumen-Institute-Student-Handbook.md"))
    chunks = split_units(units, "lumen", "KB-A_Lumen-Institute-Student-Handbook.md")
    amendment = next(chunk for chunk in chunks if chunk["section"].startswith("11."))
    assert "200,000 VND" in amendment["text"]
    assert amendment["section"].startswith("11.")


@pytest.mark.parametrize(("needle", "section"), [
    ("200,000 VND", "11."),             # Section 11 overrides exam fee
    ("3,000 VND", "11."),               # Section 11 overrides library fine
    ("no longer available to Honors", "11."),  # installment amendment
    ("may not use credit overload", "4."),
    ("not eligible for any scholarship", "6."),
    ("up to 10 books", "5."),
    ("English level B2", "10."),
])
def test_lumen_required_knowledge_is_in_expected_section(needle, section):
    units = extract_document(Path("data/documents/KB-A_Lumen-Institute-Student-Handbook.md"))
    unit = next(item for item in units if item["section"].startswith(section))
    assert needle in unit["text"]


def test_evidence_gate_rejects_empty_retrieval():
    assert not has_sufficient_evidence([])


def test_evidence_gate_rejects_low_similarity():
    evidence = Evidence("unrelated", 0.2, "kb.md", "Section 1", "Section 1", "0")
    assert not has_sufficient_evidence([evidence])
