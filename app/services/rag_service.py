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
    chunk_id: str

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
                          location=item["location"], chunk_id=str(item["chunk_index"]))
                 for item in VectorStore().search(query_vector, selected_document_ids, settings.top_k)]
    if not retrieved:
        return {"answer": "Tôi chưa tìm thấy đủ thông tin trong tài liệu đã chọn.", "citations": [],
                "debug": {"embedding_model": settings.embedding_model, "top_k": settings.top_k,
                          "retrieval_question": retrieval_question, "retrieved": []}}
    context = "\n\n".join(item.text for item in retrieved)
    citations = [{"filename": x.filename, "location": x.location, "chunk_id": x.chunk_id} for x in retrieved]
    return {"answer": generate_answer(question, context, conversation_context), "citations": citations,
            "debug": {"embedding_model": settings.embedding_model, "generation_model": settings.gemini_model,
                      "top_k": settings.top_k, "retrieval_question": retrieval_question,
                      "retrieved": [{**citation, "score": evidence.score, "text": evidence.text} for citation, evidence in zip(citations, retrieved)]}}
