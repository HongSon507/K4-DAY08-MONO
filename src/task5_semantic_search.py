"""
Task 5 — Semantic search.

Embed query bằng chính hàm của Task 4, query ChromaDB và đổi cosine distance
thành similarity. Output phải theo SearchResult, sort giảm dần và không quá top_k.
"""

from .task4_chunking_indexing import embed_texts, get_collection


def semantic_search(query: str, top_k: int = 10) -> list[dict]:
    """Trả về dense SearchResult theo score giảm dần.

    score là cosine similarity gốc (1 - distance), không phải RRF score.
    Task 9 dùng chính giá trị này để quyết định fallback, nên không được
    chuẩn hoá lại hay trộn với thang điểm khác ở đây.
    """
    if not query.strip():
        return []

    query_vector = embed_texts([query])[0]
    response = get_collection().query(
        query_embeddings=[query_vector],
        n_results=top_k,
        include=["documents", "metadatas", "distances"],
    )

    ids = (response.get("ids") or [[]])[0]
    documents = (response.get("documents") or [[]])[0]
    metadatas = (response.get("metadatas") or [[]])[0]
    distances = (response.get("distances") or [[]])[0]

    results = []
    seen: set[str] = set()
    for item_id, content, metadata, distance in zip(ids, documents, metadatas, distances):
        if item_id in seen:
            continue
        seen.add(item_id)
        results.append(
            {
                "id": item_id,
                "content": content,
                "score": max(0.0, 1.0 - float(distance)),
                "metadata": dict(metadata or {}),
                "retrieval_method": "dense",
            }
        )

    results.sort(key=lambda item: item["score"], reverse=True)
    return results[:top_k]


if __name__ == "__main__":
    import sys

    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    for result in semantic_search("Học bổng khuyến khích học tập", top_k=3):
        print(f"{result['score']:.4f}  {result['id']}")
        print(f"        {' '.join(result['content'].split())[:110]}")
