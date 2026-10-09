"""Test logic/offline; không khẳng định Gemini hoặc Qdrant đã chạy thật."""
from pathlib import Path
import pytest
from app.services.chunking import clean_text, split_units
from app.services.document_loader import extract_document
from app.services.llm_service import parse_generation_result
from app.services.rag_service import (
    UNVERIFIABLE_ANSWER_MESSAGE,
    Evidence,
    answer_requires_verified_citation,
    citations_from_supported_chunk_ids,
    has_sufficient_evidence,
)

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


def test_chat_citations_include_only_chunks_selected_as_support():
    retrieved = [
        Evidence("amendment", 0.9, "kb.md", "11. Amendments", "11. Amendments", "10"),
        Evidence("library", 0.8, "kb.md", "5. Library", "5. Library", "4"),
        Evidence("tuition", 0.7, "kb.md", "3. Paying Tuition", "3. Paying Tuition", "2"),
        Evidence("exam", 0.7, "kb.md", "7. Exam Rules", "7. Exam Rules", "6"),
    ]
    citations = citations_from_supported_chunk_ids(retrieved, ["10", "4"])
    assert [citation["section"] for citation in citations] == ["11. Amendments", "5. Library"]


def test_chat_citations_reject_unknown_or_unrelated_retrieved_chunks():
    retrieved = [
        Evidence("library", 0.8, "kb.md", "5. Library", "5. Library", "4"),
        Evidence("tuition", 0.7, "kb.md", "3. Paying Tuition", "3. Paying Tuition", "2"),
    ]
    citations = citations_from_supported_chunk_ids(retrieved, ["4", "made-up"])
    assert [citation["chunk_id"] for citation in citations] == ["4"]


def test_generation_parser_removes_source_line_and_keeps_only_ids():
    result = parse_generation_result("Phí là 2.000 VND.\nSOURCE_CHUNK_IDS: 10, 4")
    assert result.answer == "Phí là 2.000 VND."
    assert result.source_chunk_ids == ["10", "4"]


def test_answer_is_withheld_when_generation_has_no_verified_citation():
    assert answer_requires_verified_citation("Một câu trả lời chưa kiểm chứng", []) == UNVERIFIABLE_ANSWER_MESSAGE


def test_answer_is_returned_when_at_least_one_qdrant_citation_is_verified():
    citation = {"filename": "kb.md", "section": "5. Library", "chunk_id": "4"}
    assert answer_requires_verified_citation("Phí là 2.000 VND", [citation]) == "Phí là 2.000 VND"
