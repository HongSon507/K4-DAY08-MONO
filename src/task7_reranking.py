"""
Task 7 — Reciprocal Rank Fusion.

RRF gộp nhiều bảng xếp hạng mà không cộng trực tiếp cosine score với BM25
score. Công thức: RRF(d) = sum(1 / (k + rank)), rank bắt đầu từ 1.

Lưu ý: RRF score chỉ phản ánh thứ hạng, không dùng để quyết định fallback.
"""


def rerank_rrf(
    ranked_lists: list[list[dict]],
    top_k: int = 5,
    k: int = 60,
) -> list[dict]:
    """Fuse nhiều ranked lists và trả hybrid SearchResult.

    Chỉ cộng theo thứ hạng nên không cần chuẩn hoá cosine score và BM25
    score về cùng thang — đó chính là lý do dùng RRF thay vì cộng điểm.
    """
    scores: dict[str, float] = {}
    items: dict[str, dict] = {}

    for ranked_list in ranked_lists:
        seen: set[str] = set()
        for rank, item in enumerate(ranked_list, 1):
            item_id = item["id"]
            # Một ID xuất hiện hai lần trong cùng một list chỉ được tính
            # thứ hạng tốt nhất, tránh tự cộng điểm cho chính nó.
            if item_id in seen:
                continue
            seen.add(item_id)

            scores[item_id] = scores.get(item_id, 0.0) + 1.0 / (k + rank)
            items.setdefault(item_id, item)

    ranked_ids = sorted(scores, key=lambda item_id: scores[item_id], reverse=True)

    results = []
    for item_id in ranked_ids[:top_k]:
        result = dict(items[item_id])
        result["metadata"] = dict(result.get("metadata", {}))
        result["score"] = scores[item_id]
        result["retrieval_method"] = "hybrid"
        results.append(result)

    return results


if __name__ == "__main__":
    import sys

    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    from .task5_semantic_search import semantic_search
    from .task6_lexical_search import lexical_search

    query = "Học bổng khuyến khích học tập của UET"
    dense_results = semantic_search(query, top_k=5)
    lexical_results = lexical_search(query, top_k=5)

    fused = rerank_rrf([dense_results, lexical_results], top_k=5)
    print(f"Query: {query}")
    print(f"RRF Hybrid Results (top {len(fused)}):")
    for r in fused:
        print(f"  {r['score']:.5f}  [{r['retrieval_method']}]  {r['id']}")
        print(f"         {' '.join(r['content'].split())[:100]}")

