import streamlit as st
from dotenv import load_dotenv

from src.task10_generation import generate_with_citation


load_dotenv()

st.set_page_config(
    page_title="Chatbot Học bổng Đại học",
    page_icon="🎓",
    layout="wide",
)

if "messages" not in st.session_state:
    st.session_state.messages = []


def render_sources(sources: list[dict], retrieval_source: str) -> None:
    """Hiển thị nguồn kèm retrieval method và score.

    Nhãn [Document N] trong câu trả lời map đúng theo thứ tự danh sách này,
    nên không được sắp xếp lại ở đây.
    """
    if not sources:
        st.info("Không có nguồn nào được dùng cho câu trả lời này.")
        return

    st.caption(f"Retrieval: `{retrieval_source}` · {len(sources)} nguồn")

    for index, source in enumerate(sources, 1):
        metadata = source.get("metadata", {})
        title = metadata.get("title") or metadata.get("source", "Không rõ")
        method = source.get("retrieval_method", "?")
        score = source.get("score", 0.0)

        with st.expander(f"[Document {index}] {title} — {method} · {score:.4f}"):
            url = metadata.get("url")
            if url:
                st.markdown(f"**Nguồn:** [{metadata.get('source', url)}]({url})")
            else:
                st.markdown(f"**Nguồn:** {metadata.get('source', 'Không rõ')}")
            st.markdown(
                f"**Loại:** {metadata.get('doc_type', '?')} · "
                f"**Chunk:** {metadata.get('chunk_index', '?')} · "
                f"**ID:** `{source.get('id', '')}`"
            )
            st.markdown("---")
            st.markdown(source.get("content", ""))


with st.sidebar:
    st.title("🎓 Chatbot Học bổng")
    st.caption(
        "Hỏi đáp về học bổng đại học Việt Nam dựa trên quy định chính thức "
        "của VinUni, UEH, UET, RMIT, ĐH Luật TP.HCM, ĐH CNTT và Nghị định "
        "84/2020/NĐ-CP."
    )
    top_k = st.slider("Số chunks", 3, 10, 5)

    st.markdown("---")
    st.caption("Thử một câu ngoài phạm vi tài liệu để xem chatbot từ chối:")
    st.code("Cách nấu phở bò ngon?", language=None)

    if st.button("Xoá lịch sử"):
        st.session_state.messages = []
        st.rerun()

st.title("Chatbot Học bổng Đại học")
st.caption(
    "Mọi câu trả lời đều trích từ tài liệu đã thu thập và có trích dẫn "
    "kiểm chứng được. Chatbot từ chối trả lời khi không tìm thấy căn cứ."
)

for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])
        if message["role"] == "assistant":
            render_sources(
                message.get("sources", []),
                message.get("retrieval_source", "none"),
            )

query = st.chat_input("Nhập câu hỏi...")

if query:
    st.session_state.messages.append({"role": "user", "content": query})

    with st.chat_message("user"):
        st.markdown(query)

    with st.chat_message("assistant"):
        with st.spinner("Đang tìm trong tài liệu..."):
            try:
                result = generate_with_citation(query, top_k=top_k)
            except Exception as error:
                # Pipeline lỗi vẫn phải giữ UI sống, không để traceback
                # nổ ra giữa cuộc hội thoại.
                result = {
                    "answer": f"Đã xảy ra lỗi khi xử lý câu hỏi: {error}",
                    "sources": [],
                    "retrieval_source": "none",
                }

        answer = result.get("answer", "")
        sources = result.get("sources", [])
        retrieval_source = result.get("retrieval_source", "none")

        st.markdown(answer)
        render_sources(sources, retrieval_source)

    st.session_state.messages.append(
        {
            "role": "assistant",
            "content": answer,
            "sources": sources,
            "retrieval_source": retrieval_source,
        }
    )
