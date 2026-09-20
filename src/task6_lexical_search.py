"""
Task 6 — Lexical search bằng BM25.

Dùng cùng corpus chunks với Task 5. BM25 phù hợp với từ khóa chính xác, mã tài
liệu và tên riêng. Output phải theo SearchResult và sort score giảm dần.
"""

import re
import unicodedata

from .contracts import validate_search_results


CORPUS: list[dict] = []

# Giữ chữ cái (kể cả chữ có dấu), chữ số và dấu chấm trong số như 2.050.000.
_TOKEN_RE = re.compile(r"[0-9]+(?:[.,][0-9]+)*|\w+", re.UNICODE)

_CACHE: dict = {"corpus_signature": None, "bm25": None}


def tokenize(text: str) -> list[str]:
    """Tách token đủ dùng cho tiếng Việt.

    .split() thuần sẽ dính dấu câu vào từ ("học bổng," != "học bổng") và cắt
    vụn các mức tiền như "2.050.000đ", làm BM25 trượt đúng những truy vấn
    hỏi con số mà BM25 lẽ ra mạnh nhất.
    """
    folded = unicodedata.normalize("NFD", text.casefold().replace("đ", "d"))
    folded = "".join(char for char in folded if unicodedata.category(char) != "Mn")
    return _TOKEN_RE.findall(folded)


def _lexical_text(item: dict) -> str:
    """Ghép body với ID/title/source để BM25 tìm được tên riêng."""
    metadata = item.get("metadata") or {}
    return "\n".join(
        (
            str(item.get("id", "")),
            str(metadata.get("source", "")),
            str(metadata.get("title", "")),
            str(item.get("content", "")),
        )
    )


def load_corpus() -> list[dict]:
    """Nạp CORPUS từ chính chunks của Task 4 nếu chưa có.

    Phải cùng corpus và cùng ID với ChromaDB, nếu không RRF ở Task 7 sẽ
    không gộp được hai bảng xếp hạng theo ID.
    """
    global CORPUS

    if not CORPUS:
        from .task4_chunking_indexing import chunk_documents, load_documents

        CORPUS = chunk_documents(load_documents())
    return CORPUS


def build_bm25_index(corpus: list[dict]):
    """Tạo BM25 index từ cùng corpus chunks của Task 4."""
    from rank_bm25 import BM25Okapi

    if not corpus:
        return None

    # epsilon=0: term xuất hiện trong hơn nửa corpus không bị IDF âm.
    # Điều này quan trọng với title lặp trên nhiều chunk của cùng document.
    return BM25Okapi(
        [tokenize(_lexical_text(item)) for item in corpus],
        epsilon=0.0,
    )


def _get_index(corpus: list[dict]):
    """Cache index theo nội dung corpus, kể cả khi list bị mutate in-place."""
    signature = tuple(
        (item.get("id", ""), _lexical_text(item))
        for item in corpus
    )
    if _CACHE["corpus_signature"] != signature or _CACHE["bm25"] is None:
        _CACHE["corpus_signature"] = signature
        _CACHE["bm25"] = build_bm25_index(corpus)
    return _CACHE["bm25"]


def lexical_search(query: str, top_k: int = 10) -> list[dict]:
    """Trả về BM25 SearchResult theo score giảm dần."""
    corpus = CORPUS or load_corpus()
    if not corpus or not query.strip() or top_k <= 0:
        return []

    bm25 = _get_index(corpus)
    if bm25 is None:
        return []

    query_tokens = tokenize(query)
    scores = bm25.get_scores(query_tokens)

    # Trên corpus rất nhỏ, BM25 idf có thể bằng 0 cho mọi term (term xuất
    # hiện ở 1 trong 2 document => log(1) = 0), khiến lọc theo score > 0
    # loại sạch cả kết quả đúng. Dùng thêm số token trùng làm tín hiệu phụ
    # để vẫn giữ được document thực sự khớp.
    wanted = set(query_tokens)
    overlaps = [len(wanted & set(tokenize(_lexical_text(item)))) for item in corpus]

    order = sorted(
        range(len(scores)),
        key=lambda i: (scores[i], overlaps[i]),
        reverse=True,
    )

    results = []
    for index in order[:top_k]:
        if scores[index] <= 0 and overlaps[index] == 0:
            continue
        item = corpus[index]
        results.append(
            {
                "id": item["id"],
                "content": item["content"],
                "score": float(scores[index]),
                "metadata": dict(item["metadata"]),
                "retrieval_method": "bm25",
            }
        )

    validate_search_results(results, top_k=top_k, expected_method="bm25")
    return results


if __name__ == "__main__":
    import sys

    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    for result in lexical_search("học bổng khuyến khích học tập", top_k=3):
        print(f"{result['score']:.4f}  {result['id']}")
        print(f"        {' '.join(result['content'].split())[:110]}")
