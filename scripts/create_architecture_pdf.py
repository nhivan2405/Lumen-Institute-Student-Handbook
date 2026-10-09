"""Tạo PDF ôn thi mô tả kiến trúc và công nghệ của Rô AI RAG Assistant."""
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (
    KeepTogether,
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "output" / "pdf" / "RO_AI_KIEN_TRUC_HE_THONG_VA_CONG_NGHE.pdf"

# Palette chốt của đồ án.
FOREST = colors.HexColor("#123F36")
GREEN = colors.HexColor("#2A6B5C")
GOLD = colors.HexColor("#C49A45")
CREAM = colors.HexColor("#E8DCC4")
LIGHT = colors.HexColor("#F6F0E3")
INK = colors.HexColor("#1D342E")


def register_fonts() -> None:
    """Arial có đủ ký tự tiếng Việt, giúp PDF mở tốt trên Windows."""
    pdfmetrics.registerFont(TTFont("RoSans", "C:/Windows/Fonts/arial.ttf"))
    pdfmetrics.registerFont(TTFont("RoSansBold", "C:/Windows/Fonts/arialbd.ttf"))


def styles() -> dict[str, ParagraphStyle]:
    base = getSampleStyleSheet()
    return {
        "title": ParagraphStyle(
            "title", parent=base["Title"], fontName="RoSansBold", fontSize=26,
            leading=31, textColor=FOREST, alignment=TA_CENTER, spaceAfter=8,
        ),
        "subtitle": ParagraphStyle(
            "subtitle", parent=base["BodyText"], fontName="RoSans", fontSize=11,
            leading=16, textColor=GREEN, alignment=TA_CENTER,
        ),
        "h1": ParagraphStyle(
            "h1", parent=base["Heading1"], fontName="RoSansBold", fontSize=17,
            leading=22, textColor=FOREST, spaceBefore=4, spaceAfter=9,
        ),
        "h2": ParagraphStyle(
            "h2", parent=base["Heading2"], fontName="RoSansBold", fontSize=12,
            leading=16, textColor=FOREST, spaceBefore=5, spaceAfter=5,
        ),
        "body": ParagraphStyle(
            "body", parent=base["BodyText"], fontName="RoSans", fontSize=9.5,
            leading=14, textColor=INK, spaceAfter=4,
        ),
        "small": ParagraphStyle(
            "small", parent=base["BodyText"], fontName="RoSans", fontSize=8,
            leading=11, textColor=GREEN,
        ),
        "box": ParagraphStyle(
            "box", parent=base["BodyText"], fontName="RoSansBold", fontSize=9.5,
            leading=13, alignment=TA_CENTER, textColor=FOREST,
        ),
        "table_head": ParagraphStyle(
            "table_head", parent=base["BodyText"], fontName="RoSansBold", fontSize=8.5,
            leading=11, textColor=colors.white,
        ),
        "table": ParagraphStyle(
            "table", parent=base["BodyText"], fontName="RoSans", fontSize=8.2,
            leading=11, textColor=INK,
        ),
        "answer": ParagraphStyle(
            "answer", parent=base["BodyText"], fontName="RoSans", fontSize=9,
            leading=13, textColor=INK,
        ),
    }


def p(text: str, style: ParagraphStyle) -> Paragraph:
    return Paragraph(text, style)


def section_box(title: str, content: str, s: dict[str, ParagraphStyle]) -> Table:
    table = Table([[p(title, s["h2"])], [p(content, s["body"])]], colWidths=[17.2 * cm])
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), LIGHT),
        ("BOX", (0, 0), (-1, -1), 0.7, GOLD),
        ("LEFTPADDING", (0, 0), (-1, -1), 10),
        ("RIGHTPADDING", (0, 0), (-1, -1), 10),
        ("TOPPADDING", (0, 0), (-1, -1), 7),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
    ]))
    return table


def footer(canvas, doc) -> None:
    canvas.saveState()
    width, _ = A4
    canvas.setStrokeColor(GOLD)
    canvas.setLineWidth(0.6)
    canvas.line(1.5 * cm, 1.25 * cm, width - 1.5 * cm, 1.25 * cm)
    canvas.setFont("RoSans", 8)
    canvas.setFillColor(GREEN)
    canvas.drawString(1.5 * cm, 0.8 * cm, "Rô AI RAG Assistant - Tài liệu ôn vấn đáp")
    canvas.drawRightString(width - 1.5 * cm, 0.8 * cm, f"Trang {doc.page}")
    canvas.restoreState()


def build_pdf() -> None:
    register_fonts()
    s = styles()
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    document = SimpleDocTemplate(
        str(OUTPUT), pagesize=A4,
        leftMargin=1.7 * cm, rightMargin=1.7 * cm,
        topMargin=1.55 * cm, bottomMargin=1.65 * cm,
        title="Rô AI - Kiến trúc hệ thống và công nghệ",
        author="Nhóm Rô AI",
    )
    story = []

    # Page 1 - cover + architecture map.
    story += [Spacer(1, 1.2 * cm), p("RÔ AI RAG ASSISTANT", s["title"])]
    story += [p("Kiến trúc hệ thống, bộ công nghệ và kịch bản trình bày", s["subtitle"])]
    story += [Spacer(1, 0.65 * cm)]
    story += [section_box(
        "Mục tiêu của đồ án",
        "Hệ thống trả lời câu hỏi từ tài liệu do Admin quản lý. Rô chỉ dùng evidence tìm được trong Knowledge Base, sau đó mới gọi Gemini để sinh câu trả lời và hiển thị nguồn tham khảo.",
        s,
    ), Spacer(1, 0.45 * cm)]
    story += [p("Bản đồ kiến trúc", s["h1"])]
    architecture = [
        [p("1. Người dùng<br/>Streamlit", s["box"]), p("2. FastAPI<br/>API layer", s["box"]), p("3. RAG service<br/>Điều phối", s["box"])],
        [p("Chọn tài liệu<br/>Đặt câu hỏi", s["small"]), p("Validate request<br/>Route đúng service", s["small"]), p("Evidence gate<br/>Citation", s["small"])],
        [p("4. E5 local<br/>Embedding vector", s["box"]), p("5. Qdrant Local<br/>Top-K semantic search", s["box"]), p("6. Gemini 3.5 Flash<br/>Generation cloud", s["box"])],
        [p("Tài liệu: passage:<br/>Câu hỏi: query:", s["small"]), p("Filter document ID<br/>Payload metadata", s["small"]), p("Chỉ nhận Top-K evidence<br/>Sinh text answer", s["small"])],
    ]
    diagram = Table(architecture, colWidths=[5.65 * cm] * 3, rowHeights=[1.1 * cm, 0.7 * cm, 1.1 * cm, 0.7 * cm])
    diagram.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), CREAM),
        ("BACKGROUND", (0, 2), (-1, 2), CREAM),
        ("BOX", (0, 0), (-1, -1), 0.8, GOLD),
        ("INNERGRID", (0, 0), (-1, -1), 0.45, GOLD),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), 7),
        ("RIGHTPADDING", (0, 0), (-1, -1), 7),
    ]))
    story += [diagram, Spacer(1, 0.45 * cm)]
    story += [section_box(
        "Dữ liệu lưu ở đâu?",
        "E5 model chạy local trên máy backend. Qdrant Local lưu vector/chunk tại data/qdrant. SQLite lưu documents, conversations và messages tại data/database. Gemini chạy generation inference trên hạ tầng Google qua API. File gốc upload nằm tại data/uploads.",
        s,
    )]
    story += [PageBreak()]

    # Page 2 - tech choices.
    story += [p("Bộ công nghệ đã chốt", s["h1"])]
    tech_rows = [[p("Thành phần", s["table_head"]), p("Công nghệ", s["table_head"]), p("Vai trò và lý do chọn", s["table_head"])]]
    rows = [
        ("Ngôn ngữ", "Python", "Một ngôn ngữ cho UI, API, xử lý tài liệu và AI pipeline."),
        ("Frontend", "Streamlit", "Tạo UI chat/upload nhanh, trực quan, phù hợp lab và demo."),
        ("Backend", "FastAPI", "Route rõ ràng, validate schema, tách UI khỏi business logic."),
        ("PDF / DOCX / PPTX", "PyMuPDF / python-docx / python-pptx", "Trích text, giữ trang PDF và slide PPTX làm citation."),
        ("Chunking", "LangChain Text Splitters", "Cắt theo đoạn/câu trước khi cắt cứng, có overlap giữ ngữ cảnh."),
        ("Embedding", "intfloat/multilingual-e5-small", "Đa ngôn ngữ, nhẹ, chạy local; phù hợp tài liệu tiếng Việt."),
        ("Vector DB", "Qdrant Local", "Semantic search Top-K, filter theo document ID, không cần cloud/Docker."),
        ("LLM", "Gemini 3.5 Flash API", "Sinh câu trả lời từ evidence; inference cloud qua Google API."),
        ("History", "SQLite", "Local, không cần server riêng, giữ chat qua restart."),
        ("Testing", "pytest", "Kiểm tra chunk metadata và các chức năng cốt lõi nhanh."),
    ]
    for component, technology, reason in rows:
        tech_rows.append([p(component, s["table"]), p(technology, s["table"]), p(reason, s["table"])])
    tech_table = Table(tech_rows, colWidths=[3.15 * cm, 4.35 * cm, 9.7 * cm], repeatRows=1)
    tech_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), FOREST),
        ("BACKGROUND", (0, 1), (-1, -1), LIGHT),
        ("GRID", (0, 0), (-1, -1), 0.35, GOLD),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
    ]))
    story += [tech_table, Spacer(1, 0.35 * cm)]
    story += [section_box(
        "Lý do không làm kiến trúc phình to",
        "Đây là baseline RAG local có một provider LLM. Không dùng multi-provider router như OmniRoute vì tăng cấu hình, chi phí test và điểm lỗi nhưng không cần thiết cho yêu cầu demo. Khi mở rộng thật, có thể thêm authentication/RBAC, OCR, reranker, monitoring và multi-provider.",
        s,
    )]
    story += [PageBreak()]

    # Page 3 - processing flows.
    story += [p("Hai luồng hoạt động cần trình bày", s["h1"])]
    story += [p("A. Luồng Admin: index tài liệu", s["h2"])]
    index_steps = [
        "1. Admin upload PDF/DOCX/PPTX/TXT trên Streamlit.",
        "2. documents.py nhận UploadFile, tạo temp file rồi gọi chung ingestion_service.index_file().",
        "3. Loader trích text và metadata vị trí: trang PDF, slide PPTX hoặc nội dung DOCX/TXT.",
        "4. Chunking làm sạch, chia đoạn 900 ký tự, overlap 150 ký tự, giữ document_id/filename/location.",
        "5. E5 local encode passage: + chunk thành vector normalized.",
        "6. Qdrant upsert vector + payload. Chỉ sau thành công SQLite mới đổi trạng thái thành READY.",
    ]
    for step in index_steps:
        story += [p(step, s["body"])]
    story += [Spacer(1, 0.15 * cm), p("B. Luồng User: hỏi đáp RAG", s["h2"])]
    chat_steps = [
        "1. User chọn tài liệu READY và gửi câu hỏi từ Streamlit.",
        "2. chat.py validate ChatRequest, lấy history gần trong SQLite và gọi rag_service.answer_question().",
        "3. E5 local encode query: + câu hỏi. Với follow-up ngắn, thêm câu user gần để retrieval hiểu chủ đề.",
        "4. Qdrant tìm Top-K vector tương tự, chỉ trong document IDs user đã chọn.",
        "5. Evidence gate: nếu không có chunk thì từ chối, Gemini không chạy.",
        "6. Có evidence: Gemini 3.5 Flash nhận question + vài turn gần + Top-K chunks, sinh answer. Citation lấy metadata thật và UI lưu history SQLite.",
    ]
    for step in chat_steps:
        story += [p(step, s["body"])]
    story += [Spacer(1, 0.25 * cm)]
    story += [section_box(
        "Điểm bảo vệ quan trọng",
        "Citation không do Gemini bịa. Metadata đi theo chuỗi: document_loader - chunking - Qdrant payload - Evidence - Streamlit. Không có evidence thì Rô nói chưa tìm thấy đủ thông tin, thay vì trả lời ngoài Knowledge Base.",
        s,
    )]
    story += [PageBreak()]

    # Page 4 - viva answers and checklist.
    story += [p("Câu trả lời vấn đáp và checklist demo", s["h1"])]
    qa_rows = [[p("Thầy hỏi", s["table_head"]), p("Trả lời ngắn, đúng trọng tâm", s["table_head"])]]
    questions = [
        ("Embedding chạy ở đâu?", "Trong embedding_service.py. multilingual-e5-small chạy local trên backend, biến text thành vector số, không sinh câu trả lời."),
        ("Gemini dùng tại đâu?", "Trong llm_service.py: client.models.generate_content(model=settings.gemini_model, ...). Đây là generation inference cloud Google."),
        ("Tại sao dùng E5-small?", "Hỗ trợ tiếng Việt/đa ngôn ngữ, nhẹ cho laptop. Prefix passage: và query: đúng quy ước E5."),
        ("Qdrant khác SQLite thế nào?", "Qdrant tìm vector giống nghĩa. SQLite lưu document registry, trạng thái và lịch sử chat."),
        ("Vì sao không gọi Gemini ngay?", "Phải retrieval evidence trước. Nếu rỗng, evidence gate chặn để hạn chế hallucination và bảo đảm câu trả lời có nguồn."),
        ("Đổi model cần làm gì?", "Đổi Gemini thường không cần re-index. Đổi embedding model phải re-index vì vector space/dimension có thể khác."),
    ]
    for question, answer in questions:
        qa_rows.append([p(question, s["table"]), p(answer, s["answer"])])
    qa_table = Table(qa_rows, colWidths=[5.2 * cm, 12 * cm], repeatRows=1)
    qa_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), FOREST),
        ("BACKGROUND", (0, 1), (-1, -1), LIGHT),
        ("GRID", (0, 0), (-1, -1), 0.35, GOLD),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
    ]))
    story += [qa_table, Spacer(1, 0.35 * cm)]
    story += [section_box(
        "Checklist 60 giây trước demo",
        "1. Chạy FastAPI cổng 8123. 2. Chạy Streamlit cổng 8501. 3. Kiểm tra /health. 4. Mở Kho tài liệu để thấy document READY. 5. Vào Hỏi Rô, chọn tài liệu và hỏi. 6. Mở Góc kiểm tra để chỉ Top-K evidence, model và citation. 7. Nếu Gemini lỗi mạng/key, vẫn trình bày đúng luồng đến evidence gate, không bịa kết quả.",
        s,
    )]

    document.build(story, onFirstPage=footer, onLaterPages=footer)
    print(OUTPUT)


if __name__ == "__main__":
    build_pdf()
