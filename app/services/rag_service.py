"""Điều phối RAG: retrieval trước, evidence gate sau, generation cuối cùng."""
from dataclasses import dataclass
from app.core.config import settings
from app.services.embedding_service import embedding_service
from app.services.llm_service import generate_answer
from app.services.vector_store import VectorStore

@dataclass
class Evidence:
    """Metadata gốc đi cùng chunk, dùng làm citation thay vì để LLM tự bịa nguồn."""
    text: str
    score: float
    filename: str
    location: str
    section: str
    chunk_id: str


NO_EVIDENCE_MESSAGE = "Tôi không tìm thấy thông tin này trong Knowledge Base."
UNVERIFIABLE_ANSWER_MESSAGE = "Tôi không thể xác minh nguồn cho câu trả lời này trong Knowledge Base."


def has_sufficient_evidence(retrieved: list[Evidence]) -> bool:
    """Gate độc lập với Gemini; score cosine không phải xác suất câu trả lời đúng."""
    return bool(retrieved) and max(item.score for item in retrieved) >= settings.evidence_min_score


def citations_from_supported_chunk_ids(retrieved: list[Evidence], supported_ids: list[str]) -> list[dict]:
    """Tạo citation duy nhất từ payload Qdrant của những chunk model đã dùng.

    `supported_ids` chỉ là lựa chọn; metadata hiển thị luôn lấy từ Evidence. ID lạ
    hoặc chunk Top-K không được model chọn đều bị bỏ qua khỏi phần Chat.
    """
    allowed = set(supported_ids)
    return [
        {"filename": item.filename, "location": item.location, "section": item.section,
         "chunk_id": item.chunk_id}
        for item in retrieved if item.chunk_id in allowed
    ]


def answer_requires_verified_citation(answer: str, citations: list[dict]) -> str:
    """Không để Chat hiển thị một khẳng định có vẻ đúng nhưng không có nguồn thật.

    Câu từ chối là phản hồi an toàn, không phải một khẳng định kiến thức từ KB. Mọi
    câu trả lời nội dung chỉ qua guard này khi ít nhất một citation Qdrant hợp lệ.
    """
    return answer if citations else UNVERIFIABLE_ANSWER_MESSAGE

def answer_question(question: str, selected_document_ids: list[str], conversation_context: list[dict] | None = None) -> dict:
    """Điều phối một lượt RAG từ câu hỏi tới citation/answer.

    Input là câu hỏi, document IDs người dùng đã chọn và history gần. Output gồm
    answer, citations và debug trace. Không có evidence thì từ chối trước Gemini.
    """
    if not selected_document_ids:
        return {"answer": "Hãy chọn ít nhất một tài liệu đã index.", "citations": [], "debug": {}}
    # Chỉ thêm 2 lượt gần nhất vào retrieval khi câu hỏi là follow-up ngắn.
    retrieval_question = question
    if conversation_context and len(question.split()) < 12:
        recent = " ".join(item["content"] for item in conversation_context[-2:] if item["role"] == "user")
        retrieval_question = f"{recent} {question}".strip()
    query_vector = embedding_service.embed_query(retrieval_question)
    retrieved = [Evidence(text=item["text"], score=float(item["score"]), filename=item["filename"],
                          location=item["location"], section=item.get("section", item["location"]),
                          chunk_id=str(item["chunk_index"]))
                 for item in VectorStore().search(query_vector, selected_document_ids, settings.top_k)]
    if not has_sufficient_evidence(retrieved):
        return {"answer": NO_EVIDENCE_MESSAGE, "citations": [],
                "debug": {"embedding_model": settings.embedding_model, "top_k": settings.top_k,
                          "evidence_min_score": settings.evidence_min_score,
                          "retrieval_question": retrieval_question,
                          "retrieved": [item.__dict__ for item in retrieved]}}
    # ID trong context cho phép Gemini chọn evidence đã dùng; metadata citation vẫn
    # được lấy lại từ retrieved payload, không tin section/filename model sinh ra.
    context = "\n\n".join(f"[CHUNK_ID: {item.chunk_id}]\n{item.text}" for item in retrieved)
    generated = generate_answer(question, context, conversation_context)
    citations = citations_from_supported_chunk_ids(retrieved, generated.source_chunk_ids)
    debug_citations = [{"filename": x.filename, "location": x.location, "section": x.section,
                        "chunk_id": x.chunk_id} for x in retrieved]
    return {"answer": answer_requires_verified_citation(generated.answer, citations), "citations": citations,
            "debug": {"embedding_model": settings.embedding_model, "generation_model": settings.gemini_model,
                      "top_k": settings.top_k, "evidence_min_score": settings.evidence_min_score,
                      "retrieval_question": retrieval_question,
                      "used_chunk_ids": generated.source_chunk_ids,
                      "retrieved": [{**citation, "score": evidence.score, "text": evidence.text}
                                    for citation, evidence in zip(debug_citations, retrieved)]}}
