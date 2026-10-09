"""Chạy test cases thật và lưu actual result, không chấm câu tự nhiên bằng so sánh tuyệt đối."""
from time import perf_counter
from app.services.rag_service import answer_question

def evaluate_case(case: dict, selected_document_ids: list[str]) -> dict:
    start = perf_counter()
    result = answer_question(case["question"], selected_document_ids)
    has_answer = not result["answer"].startswith("Tôi chưa tìm thấy")
    return {**case, "actual_answer": result["answer"], "actual_citations": result.get("citations", []),
            "pass": has_answer == case["should_answer"], "latency_ms": round((perf_counter() - start) * 1000, 2)}
