import streamlit as st
from dotenv import load_dotenv

from src.task9_retrieval_pipeline import SCORE_THRESHOLD, retrieve
from src.task10_generation import generate_with_citation


load_dotenv()

st.set_page_config(
    page_title="Chatbot Học bổng Đại học",
    page_icon="🎓",
    layout="wide",
)

# Câu hỏi demo: hai câu in-domain (một câu dễ, một câu dễ lẫn audience) và
# một câu ngoài domain để cho thấy safe refusal.
SAMPLE_QUESTIONS = [
    "Học bổng loại Giỏi của UET khóa QH-2021 là bao nhiêu mỗi tháng?",
    "UEH hỗ trợ bao nhiêu tiền để thu hút giảng viên có học hàm Giáo sư?",
    "Cách nấu phở bò ngon?",
]

if "messages" not in st.session_state:
    st.session_state.messages = []
if "pending" not in st.session_state:
    st.session_state.pending = None


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


def render_ab_comparison(query: str, top_k: int) -> None:
    """Chạy lại retrieval ở hai cấu hình để demo A/B ngay trên UI.

    Hai cột chỉ khác nhau đúng một biến use_reranking, mọi thứ còn lại giữ
    nguyên — đúng điều kiện so sánh mà RESULT.md yêu cầu.
    """
    left, right = st.columns(2)

    for column, use_reranking, label in (
        (left, False, "Config A — dense-only"),
        (right, True, "Config B — hybrid + RRF"),
    ):
        with column:
            st.markdown(f"**{label}**")
            try:
                results = retrieve(query, top_k=top_k, use_reranking=use_reranking)
            except Exception as error:
                st.error(f"Lỗi: {error}")
                continue

            if not results:
                st.info("Không có kết quả.")
                continue

            for rank, item in enumerate(results, 1):
                metadata = item.get("metadata", {})
                st.markdown(
                    f"{rank}. `{item.get('score', 0.0):.4f}` "
                    f"[{item.get('retrieval_method', '?')}] "
                    f"{metadata.get('source', '?')}"
                )
                st.caption(" ".join(item.get("content", "").split())[:120])


with st.sidebar:
    st.title("🎓 Chatbot Học bổng")
    st.caption(
        "Hỏi đáp về học bổng đại học Việt Nam dựa trên quy định chính thức "
        "của VinUni, UEH, UET, RMIT, ĐH Luật TP.HCM, ĐH CNTT và Nghị định "
        "84/2020/NĐ-CP."
    )

    top_k = st.slider("Số chunks", 3, 10, 5)
    show_ab = st.checkbox("Hiện so sánh A/B", value=False)

    st.markdown("---")
    st.markdown("**Câu hỏi mẫu**")
    for sample in SAMPLE_QUESTIONS:
        if st.button(sample, use_container_width=True):
            st.session_state.pending = sample

    st.markdown("---")
    st.caption(f"Ngưỡng fallback hiện tại: `{SCORE_THRESHOLD}`")

    if st.button("Xoá lịch sử", use_container_width=True):
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

query = st.chat_input("Nhập câu hỏi...") or st.session_state.pending
st.session_state.pending = None

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

        if show_ab:
            st.markdown("---")
            st.markdown("#### So sánh A/B")
            render_ab_comparison(query, top_k)

    st.session_state.messages.append(
        {
            "role": "assistant",
            "content": answer,
            "sources": sources,
            "retrieval_source": retrieval_source,
        }
    )
