"""Giao diện Streamlit của Trợ Lý Rô AI.

File này chỉ hiển thị UI và gọi FastAPI. Không đặt API key, embedding model hay
logic Qdrant ở frontend để luồng bảo mật và trách nhiệm từng tầng rõ ràng.
"""
import json
import os
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen
from uuid import uuid4

import streamlit as st

# 8123 đã được kiểm tra bind thành công trên Windows của project này.
# Có thể đổi mà không sửa source: $env:RO_AI_API_URL="http://127.0.0.1:9000/api"
API_BASE_URL = os.getenv("RO_AI_API_URL", "http://127.0.0.1:8123/api")
PAGE_CHAT = "Trò chuyện"
PAGE_DOCUMENTS = "Tài liệu của tôi"
PAGE_DEBUG = "Kiểm tra câu trả lời"
ROLE_STUDENT = "Sinh viên"
ROLE_ADMIN = "Quản trị viên"


def error_detail(error: HTTPError) -> str:
    """Đọc error body an toàn, kể cả khi proxy/server trả HTML hoặc body rỗng.

    Không dùng `json.loads()` trực tiếp vì HTTP 500 đôi khi chỉ trả text rỗng;
    chính điều đó đã từng làm UI hiển thị JSONDecodeError thay vì lỗi thật.
    """
    raw_body = error.read().decode("utf-8", errors="replace").strip()
    if not raw_body:
        return f"Backend trả HTTP {error.code} nhưng không có chi tiết lỗi."

    try:
        payload = json.loads(raw_body)
    except json.JSONDecodeError:
        return f"Backend trả HTTP {error.code}: {raw_body[:300]}"

    if isinstance(payload, dict):
        return str(payload.get("detail", raw_body))
    return raw_body


def api_request(
    path: str,
    method: str = "GET",
    payload: dict[str, Any] | None = None,
    timeout_seconds: int = 60,
) -> Any:
    """Gọi FastAPI và đổi lỗi kỹ thuật thành thông báo có thể đọc trên UI.

    Input: đường dẫn API, HTTP method và JSON payload (nếu có).
    Output: JSON response đã đổi thành dict/list Python.
    Nơi gọi: các thao tác Chat mới, load document, chat và debug phía dưới.
    """
    request_body = json.dumps(payload).encode("utf-8") if payload else None
    request = Request(
        url=f"{API_BASE_URL}{path}",
        data=request_body,
        method=method,
        headers={"Content-Type": "application/json"},
    )

    try:
        with urlopen(request, timeout=timeout_seconds) as response:
            response_text = response.read().decode("utf-8").strip()
            # DELETE trả HTTP 204 với body rỗng; đây vẫn là một request thành công.
            return json.loads(response_text) if response_text else {}
    except HTTPError as error:
        raise RuntimeError(error_detail(error)) from error
    except URLError as error:
        raise RuntimeError(f"Không kết nối được FastAPI tại {API_BASE_URL}.") from error


def api_upload_document(filename: str, content: bytes) -> dict[str, Any]:
    """Gửi file Streamlit lên FastAPI bằng multipart/form-data.

    FastAPI route `/api/documents/upload` nhận UploadFile nên không thể dùng JSON.
    Hàm này tự tạo multipart body, còn validate/size/type vẫn được kiểm tra lại ở
    backend; frontend không phải lớp bảo mật duy nhất.
    """
    boundary = f"----RoAiBoundary{uuid4().hex}"
    part_headers = (
        f"--{boundary}\r\n"
        f'Content-Disposition: form-data; name="file"; filename="{filename}"\r\n'
        "Content-Type: application/octet-stream\r\n\r\n"
    ).encode("utf-8")
    request_body = part_headers + content + f"\r\n--{boundary}--\r\n".encode("utf-8")
    request = Request(
        url=f"{API_BASE_URL}/documents/upload",
        data=request_body,
        method="POST",
        headers={"Content-Type": f"multipart/form-data; boundary={boundary}"},
    )

    try:
        with urlopen(request, timeout=180) as response:
            return json.loads(response.read().decode("utf-8"))
    except HTTPError as error:
        raise RuntimeError(error_detail(error)) from error
    except URLError as error:
        raise RuntimeError(f"Không kết nối được FastAPI tại {API_BASE_URL}.") from error


@st.cache_data(ttl=5)
def load_documents() -> list[dict[str, Any]]:
    """Đọc registry document từ backend; cache 5 giây để giảm request lặp lại."""
    return api_request("/documents")


@st.cache_data(ttl=5)
def load_conversations() -> list[dict[str, Any]]:
    """Lấy danh sách lịch sử chat SQLite để hiển thị trên sidebar."""
    return api_request("/conversations")


def initialize_session_state() -> None:
    """Khởi tạo state UI một lần cho từng browser session, không thay SQLite."""
    st.session_state.setdefault("page", PAGE_CHAT)
    # Query parameter giữ ID khi người dùng refresh trang. Nội dung chat thật vẫn
    # nằm ở SQLite, không nằm trong URL hay chỉ ở bộ nhớ của Streamlit.
    saved_conversation_id = st.query_params.get("conversation")
    st.session_state.setdefault("conversation_id", saved_conversation_id)
    st.session_state.setdefault("messages", [])
    st.session_state.setdefault("last_debug", None)
    # Đây là role mô phỏng để trình bày use case khi thi, không phải đăng nhập/RBAC.
    st.session_state.setdefault("demo_role", ROLE_STUDENT)


def chat_messages() -> list[dict[str, Any]]:
    """Trả list chat an toàn trên mọi rerun/reconnect của Streamlit.

    Streamlit có thể tạo session mới khi browser refresh hoặc WebSocket reconnect.
    Không truy cập ``st.session_state.messages`` trực tiếp để một lượt reconnect
    đúng lúc response về không làm UI vỡ với AttributeError.
    """
    return st.session_state.setdefault("messages", [])


def start_new_chat() -> None:
    """Tạo conversation mới trong SQLite và reset phần lịch sử đang hiển thị.

    Hàm này không xóa document, vectors Qdrant hay các conversation cũ.
    """
    conversation = api_request(
        "/conversations",
        method="POST",
        payload={"title": "Cuộc trò chuyện mới"},
    )
    st.session_state.conversation_id = conversation["id"]
    st.session_state["messages"] = []
    st.query_params["conversation"] = conversation["id"]


def load_conversation_messages(conversation_id: str) -> list[dict[str, Any]]:
    """Đọc lại lịch sử từ SQLite để refresh trang không làm mất hội thoại."""
    stored_messages = api_request(f"/conversations/{conversation_id}/messages")
    messages: list[dict[str, Any]] = []

    for message in stored_messages:
        try:
            citations = json.loads(message.get("citations_json") or "[]")
        except json.JSONDecodeError:
            # Một bản ghi cũ bị lỗi citation vẫn không được phép làm hỏng cả chat.
            citations = []

        messages.append(
            {
                "role": message["role"],
                "content": message["content"],
                "citations": citations,
            }
        )
    return messages


def restore_chat_history() -> None:
    """Khôi phục chat một lần khi Streamlit vừa reload hoặc reconnect browser."""
    conversation_id = st.session_state.conversation_id
    if conversation_id and not chat_messages():
        st.session_state["messages"] = load_conversation_messages(conversation_id)


def open_conversation(conversation_id: str) -> None:
    """Chuyển sang một hội thoại cũ và nạp tất cả message của hội thoại đó."""
    st.session_state["conversation_id"] = conversation_id
    st.session_state["messages"] = load_conversation_messages(conversation_id)
    st.session_state["page"] = PAGE_CHAT
    st.query_params["conversation"] = conversation_id


def delete_conversation(conversation_id: str) -> None:
    """Xóa một lịch sử chat qua API; tài liệu và Qdrant hoàn toàn không bị chạm."""
    api_request(f"/conversations/{conversation_id}", method="DELETE")
    if st.session_state.get("conversation_id") == conversation_id:
        # Không giữ ID đã xóa, tránh refresh URL rồi cố tải lại conversation cũ.
        st.session_state["conversation_id"] = None
        st.session_state["messages"] = []
        if "conversation" in st.query_params:
            del st.query_params["conversation"]
    load_conversations.clear()


def show_citations(citations: list[dict[str, Any]]) -> None:
    """Hiển thị citation từ metadata Qdrant; UI không tự tạo số trang/slide."""
    for citation in citations:
        st.caption(
            f"Nguồn: {citation['filename']} · {citation.get('section', citation['location'])} "
            f"· chunk {citation['chunk_id']}"
        )


def render_chat_message(
    role: str,
    content: str,
    citations: list[dict[str, Any]],
) -> None:
    """Hiển thị một tin nhắn bằng component Streamlit chuẩn, không CSS tùy biến."""
    speaker = "Bạn" if role == "user" else "Rô"
    with st.container(border=True):
        st.caption(speaker)
        st.markdown(content)
        show_citations(citations)


def render_sidebar() -> None:
    """Hiển thị điều hướng chung; trả page qua session state để rerun vẫn giữ trang."""
    with st.sidebar:
        st.title("Học cùng Rô", icon=":material/smart_toy:")
        st.caption("Trợ lý học tập từ tài liệu của bạn")

        role = st.selectbox(
            "Chế độ demo",
            options=[ROLE_STUDENT, ROLE_ADMIN],
            key="demo_role",
            help="Mô phỏng hai nhóm người dùng cho phần trình bày; chưa phải đăng nhập thật.",
        )

        with st.container(border=True):
            if role == ROLE_STUDENT:
                st.subheader("Xin chào, mình là Rô", icon=":material/waving_hand:")
                st.write("Hôm nay bạn muốn cùng Rô tìm hiểu điều gì?")
                st.caption("Chọn tài liệu, đặt câu hỏi, Rô sẽ tìm nguồn liên quan.")
            else:
                st.subheader("Khu vực quản trị", icon=":material/admin_panel_settings:")
                st.write("Quản lý Knowledge Base và kiểm tra chất lượng câu trả lời.")
                st.caption("Chỉ dùng để mô phỏng vai trò Admin khi demo.")

        if role == ROLE_STUDENT and st.button(
            "Chat mới", icon=":material/add:", type="primary", width="stretch"
        ):
            try:
                start_new_chat()
                load_conversations.clear()
                st.rerun()
            except RuntimeError as error:
                st.error(str(error))

        st.divider()
        st.subheader("Không gian học tập", icon=":material/menu_book:")

        # Sinh viên dùng chatbot; Admin chỉ quản lý KB và kiểm tra trace RAG.
        page_labels = (
            {PAGE_CHAT: ":material/chat_bubble:  Hỏi Rô"}
            if role == ROLE_STUDENT
            else {
                PAGE_DOCUMENTS: ":material/folder_open:  Quản lý tài liệu",
                PAGE_DEBUG: ":material/fact_check:  Kiểm tra câu trả lời",
            }
        )
        pages = list(page_labels)
        if st.session_state.page not in pages:
            st.session_state.page = pages[0]
        selected_page = st.radio(
            "Điều hướng chính",
            options=pages,
            index=pages.index(st.session_state.page),
            format_func=page_labels.get,
            label_visibility="collapsed",
        )
        st.session_state.page = selected_page

        if role == ROLE_STUDENT:
            st.space("small")
            st.caption("Các cuộc trò chuyện gần đây")
            try:
                conversations = load_conversations()
            except RuntimeError as error:
                conversations = []
                st.caption(f"Chưa tải được lịch sử: {error}")

            if not conversations:
                st.caption(":material/forum: Chưa có cuộc trò chuyện nào.")
            else:
                for conversation in conversations[:8]:
                    title = conversation["display_title"].strip() or "Cuộc trò chuyện mới"
                    label = title if len(title) <= 36 else f"{title[:36]}…"
                    is_active = conversation["id"] == st.session_state.get("conversation_id")
                    open_column, delete_column = st.columns([5, 1])
                    with open_column:
                        if st.button(
                            label,
                            icon=":material/forum:" if is_active else ":material/chat_bubble_outline:",
                            type="primary" if is_active else "secondary",
                            width="stretch",
                            key=f"open_conversation_{conversation['id']}",
                        ):
                            try:
                                open_conversation(conversation["id"])
                                st.rerun()
                            except RuntimeError as error:
                                st.error(f"Không thể mở cuộc trò chuyện: {error}")
                    with delete_column:
                        if st.button(
                            "Xóa",
                            icon=":material/delete:",
                            width="stretch",
                            key=f"delete_conversation_{conversation['id']}",
                            help="Xóa cuộc trò chuyện này. Tài liệu và Knowledge Base không bị xóa.",
                        ):
                            try:
                                delete_conversation(conversation["id"])
                                st.rerun()
                            except RuntimeError as error:
                                st.error(f"Không thể xóa cuộc trò chuyện: {error}")

                if len(conversations) > 8:
                    st.caption(f"Hiển thị 8/{len(conversations)} cuộc trò chuyện gần nhất.")

        st.divider()
        st.subheader("Thư viện của Rô")
        with st.container(border=True):
            st.markdown(":material/menu_book: **Tài liệu → tri thức**")
            st.caption("PDF, DOCX, PPTX, TXT được chia chunks và lưu Qdrant.")
            st.markdown(":material/psychology: **E5 local**")
            st.caption("Biến tài liệu và câu hỏi thành vector.")
            st.markdown(":material/find_in_page: **Evidence trước**")
            st.caption("Không có bằng chứng thì Rô từ chối trả lời.")

        st.space("small")
        st.caption("Rô chỉ trả lời từ tài liệu đã chọn")


def render_chat_page() -> None:
    """Trang hỏi đáp: chọn tài liệu → gửi API → render answer/citation trả về."""
    st.title("Hỏi Rô về tài liệu")
    st.caption("Chọn tài liệu, hỏi điều bạn chưa rõ. Rô sẽ trả lời kèm nguồn tham khảo.")

    try:
        documents = load_documents()
    except RuntimeError as error:
        documents = []
        st.error(str(error))

    ready_documents = [document for document in documents if document["status"] == "READY"]
    selected_filenames = st.multiselect(
        "Tài liệu dùng để trả lời",
        options=[document["filename"] for document in ready_documents],
    )
    selected_document_ids = [
        document["id"]
        for document in ready_documents
        if document["filename"] in selected_filenames
    ]

    if not ready_documents:
        st.info("Knowledge Base đang trống. Đây là trạng thái đúng khi chưa index tài liệu.")

    try:
        restore_chat_history()
    except RuntimeError as error:
        st.warning(f"Không thể mở lại lịch sử trò chuyện: {error}")

    messages = chat_messages()
    for message in messages:
        render_chat_message(
            message["role"],
            message["content"],
            message.get("citations", []),
        )

    suggested_question: str | None = None
    if not messages:
        with st.container(border=True):
            st.subheader(
                "Hôm nay Rô có thể giúp gì cho bạn?",
                icon=":material/smart_toy:",
            )
            if selected_filenames:
                st.caption(f"Đang học cùng: {', '.join(selected_filenames)}")
            else:
                st.caption("Hãy chọn tài liệu ở phía trên, rồi chọn một cách học bên dưới.")

            # Nút dọc dễ nhận ra như menu trợ lý học tập, thay vì để người dùng
            # phải tự nghĩ câu đầu tiên. Bấm nút sẽ dùng prompt tương ứng.
            suggestions = [
                (
                    "Tóm tắt tài liệu này",
                    "Hãy tóm tắt nội dung chính của tài liệu.",
                    ":material/format_align_left:",
                ),
                (
                    "Giải thích một khái niệm",
                    "Hãy giải thích các khái niệm quan trọng trong tài liệu một cách dễ hiểu.",
                    ":material/lightbulb:",
                ),
                (
                    "Tìm ý quan trọng nhất",
                    "Những ý quan trọng nhất trong tài liệu là gì?",
                    ":material/search:",
                ),
            ]
            for index, (label, prompt, icon) in enumerate(suggestions):
                if st.button(
                    label,
                    icon=icon,
                    width="stretch",
                    key=f"study_suggestion_{index}",
                ):
                    suggested_question = prompt

    question = suggested_question or st.chat_input(
        "Nhập câu hỏi cho Rô...", submit_mode="disable"
    )
    if not question:
        return

    current_messages = chat_messages()
    current_messages.append({"role": "user", "content": question})
    render_chat_message("user", question, [])

    with st.container(border=True):
        st.caption("Rô")
        with st.status("Rô đang tìm trong tài liệu...", expanded=False, type="compact") as status:
            try:
                result = api_request(
                    "/chat",
                    method="POST",
                    payload={
                        "question": question,
                        "selected_document_ids": selected_document_ids,
                        "conversation_id": st.session_state.conversation_id,
                    },
                )
                st.session_state.conversation_id = result["conversation_id"]
                # Ghi ID vào URL, để F5/reconnect vẫn tải lại đúng hội thoại SQLite.
                st.query_params["conversation"] = result["conversation_id"]
                # Debug là trace backend trả về từ lần hỏi thật, không hard-code score.
                st.session_state.last_debug = result.get("debug", {})
                load_conversations.clear()
                status.update(label="Rô đã tìm được nguồn liên quan", state="complete")
                st.markdown(result["answer"])
                show_citations(result.get("citations", []))
                current_messages.append(
                    {
                        "role": "assistant",
                        "content": result["answer"],
                        "citations": result.get("citations", []),
                    }
                )
            except RuntimeError as error:
                status.update(label="Không thể tạo câu trả lời", state="error")
                st.error(str(error))


def render_documents_page() -> None:
    """Trang upload/index và registry Knowledge Base."""
    st.title("Quản trị Knowledge Base")
    st.caption("Khu vực Admin: PDF/DOCX/PPTX/TXT/Markdown → extract → chunk → E5 → Qdrant → READY.")

    with st.container(border=True):
        st.subheader("Luồng Admin và User", icon=":material/account_tree:")
        admin_column, user_column = st.columns(2)
        with admin_column:
            st.markdown(":material/admin_panel_settings: **Admin**")
            st.caption("Upload, đổi tên, re-index hoặc xóa tài liệu khỏi Knowledge Base.")
        with user_column:
            st.markdown(":material/person: **User**")
            st.caption("Chỉ vào Trò chuyện, chọn tài liệu READY và gửi câu hỏi.")
        st.caption(
            "Bản demo chưa có đăng nhập/RBAC; đây là phân tách vai trò theo luồng hệ thống."
        )

    with st.container(border=True):
        st.subheader("Hai cách đưa tài liệu vào Knowledge Base", icon=":material/folder_copy:")
        upload_column, folder_column = st.columns(2)
        with upload_column:
            st.markdown(":material/upload_file: **Cách 1 - Admin upload**")
            st.caption("Chọn file ở phần bên dưới. Bản gốc được lưu trong data/uploads.")
        with folder_column:
            st.markdown(":material/folder_open: **Cách 2 - Knowledge Base cố định**")
            st.caption("Chép file thầy đưa vào data/documents rồi bấm index thư mục.")
            if st.button(
                "Index thư mục documents",
                icon=":material/library_add:",
                key="index_documents_folder",
            ):
                with st.spinner("Đang index các file trong data/documents..."):
                    try:
                        results = api_request(
                            "/documents/index-folder",
                            method="POST",
                            timeout_seconds=300,
                        )
                        load_documents.clear()
                        if not results:
                            st.info("Thư mục data/documents chưa có PDF, DOCX, PPTX, TXT hoặc Markdown.")
                        else:
                            ready_count = sum(item.get("status") == "READY" for item in results)
                            failed_count = sum(item.get("status") == "FAILED" for item in results)
                            st.success(f"Đã xử lý {len(results)} file: {ready_count} READY, {failed_count} FAILED.")
                        st.rerun()
                    except RuntimeError as error:
                        st.error(f"Không thể index thư mục: {error}")

    with st.container(border=True):
        uploaded_file = st.file_uploader(
            "Chọn tệp để index",
            type=["pdf", "docx", "pptx", "txt", "md"],
            max_upload_size=20,
            key="document_upload",
            help="Backend kiểm tra lại định dạng và dung lượng trước khi index.",
        )
        st.caption("READY chỉ xuất hiện sau Qdrant upsert. PDF scan không text sẽ FAILED.")

        if uploaded_file and st.button(
            "Index tài liệu",
            icon=":material/upload_file:",
            type="primary",
        ):
            with st.spinner("Đang extract, chunk, embedding và lưu Qdrant..."):
                try:
                    result = api_upload_document(
                        uploaded_file.name,
                        uploaded_file.getvalue(),
                    )
                    load_documents.clear()
                    if result.get("duplicate"):
                        st.warning("Tài liệu trùng nội dung với một tài liệu READY đã có.")
                    else:
                        st.success(
                            f"Đã index {result['filename']} với "
                            f"{result['chunk_count']} chunks."
                        )
                    st.rerun()
                except RuntimeError as error:
                    st.error(f"Không thể index tài liệu: {error}")

    try:
        documents = load_documents()
        if not documents:
            st.info("Chưa có tài liệu.")
            return

        # UUID/hash/path là thông tin kỹ thuật, không hiển thị trong bảng người dùng.
        table_rows = [
            {
                "Tên tài liệu": document["filename"],
                "Trạng thái": document["status"],
                "Số chunks": document["chunk_count"],
                "Ngày index": document["created_at"][:10],
            }
            for document in documents
        ]
        st.dataframe(table_rows, hide_index=True)

        st.subheader("Quản lý tài liệu")
        document_by_name = {document["filename"]: document for document in documents}
        selected_name = st.selectbox("Chọn tài liệu", options=list(document_by_name))
        selected_document = document_by_name[selected_name]

        new_name = st.text_input(
            "Tên hiển thị",
            value=selected_document["filename"],
            key=f"rename_{selected_document['id']}",
        )
        rename_column, delete_column = st.columns(2)

        if rename_column.button("Lưu tên", icon=":material/edit:"):
            try:
                api_request(
                    f"/documents/{selected_document['id']}",
                    method="PATCH",
                    payload={"filename": new_name},
                )
                load_documents.clear()
                st.success("Đã đổi tên; citation và Qdrant payload cũng được cập nhật.")
                st.rerun()
            except RuntimeError as error:
                st.error(str(error))

        if delete_column.button(
            "Xóa tài liệu",
            icon=":material/delete:",
            type="secondary",
        ):
            try:
                api_request(f"/documents/{selected_document['id']}", method="DELETE")
                load_documents.clear()
                st.success("Đã xóa file gốc upload, registry và toàn bộ vectors của tài liệu.")
                st.rerun()
            except RuntimeError as error:
                st.error(str(error))
    except RuntimeError as error:
        st.error(str(error))


def render_debug_page() -> None:
    """Hiển thị luồng trả lời thật theo cách dễ hiểu, không lộ API key."""
    st.title("Góc kiểm tra câu trả lời", icon=":material/fact_check:")
    st.caption("Xem Rô đã tìm tài liệu và tạo câu trả lời như thế nào.")

    try:
        config = api_request("/debug/configuration")

        with st.container(border=True):
            st.subheader("Rô trả lời theo 3 bước", icon=":material/route:")
            read_column, search_column, answer_column = st.columns(3)
            with read_column:
                st.markdown(":material/question_mark: **1. Hiểu câu hỏi**")
                st.caption("E5 local biến câu hỏi thành vector ngữ nghĩa.")
            with search_column:
                st.markdown(":material/search: **2. Tìm đúng đoạn**")
                st.caption("Qdrant tìm Top-K trong tài liệu bạn đã chọn.")
            with answer_column:
                st.markdown(":material/auto_awesome: **3. Trả lời có nguồn**")
                st.caption("Gemini tạo câu trả lời từ các đoạn Rô đã tìm được.")

        model_column, document_column, gate_column = st.columns(3)
        model_column.metric("Tài liệu đã sẵn sàng", config["ready_documents"])
        document_column.metric("Số đoạn Rô đọc", f"Top {config['top_k']}")
        gate_column.metric(
            "Trạng thái Gemini",
            "Sẵn sàng" if config["gemini_configured"] else "Chưa có API key",
        )

        with st.expander("Thông số kỹ thuật để trình bày với thầy", icon=":material/code:"):
            st.markdown(f"- **Embedding local:** `{config['embedding_model']}`")
            st.markdown(f"- **Generation cloud:** `{config['generation_model']}`")
            st.markdown(f"- **Retrieval:** Top-{config['top_k']} + filter theo document ID")
            st.caption("Không có evidence thì Rô từ chối trước khi gọi Gemini.")

        last_debug = st.session_state.last_debug
        if last_debug:
            st.subheader("Lần Rô trả lời gần nhất", icon=":material/history:")
            st.caption(f"Câu hỏi Rô dùng để tìm: “{last_debug.get('retrieval_question', '')}”")
            retrieved = last_debug.get("retrieved", [])
            st.badge(f"Tìm được {len(retrieved)} đoạn nguồn", icon=":material/check_circle:", color="green")
            trace_rows = [
                {
                    "Tên tài liệu": item["filename"],
                "Section": item.get("section", item["location"]),
                    "Chunk": item["chunk_id"],
                    "Score": round(item["score"], 4),
                }
                for item in retrieved
            ]
            st.dataframe(trace_rows, hide_index=True)
            for index, item in enumerate(retrieved, start=1):
                with st.expander(
                    f"Đoạn nguồn {index}: {item['filename']} · {item['location']}",
                    icon=":material/article:",
                ):
                    st.text(item["text"])
        else:
            with st.container(border=True):
                st.subheader("Chưa có bài làm để kiểm tra", icon=":material/menu_book:")
                st.write("Hãy chọn một tài liệu ở trang Hỏi Rô và gửi một câu hỏi.")
                st.caption("Sau đó, nơi này sẽ hiện các đoạn nguồn Rô đã dùng để trả lời.")
    except RuntimeError as error:
        st.error(str(error))


st.set_page_config(
    page_title="Trợ Lý Rô AI",
    page_icon=":material/psychology:",
    layout="wide",
)
initialize_session_state()
render_sidebar()

if st.session_state.page == PAGE_CHAT:
    render_chat_page()
elif st.session_state.page == PAGE_DOCUMENTS:
    render_documents_page()
else:
    render_debug_page()
