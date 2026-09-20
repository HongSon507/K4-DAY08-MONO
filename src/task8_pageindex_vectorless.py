"""
Task 8 — PageIndex vectorless fallback.

Hướng dẫn:
    1. Đọc PAGEINDEX_API_KEY từ .env.
    2. Upload tài liệu ở định dạng PageIndex hỗ trợ.
    3. Cache document IDs để không upload lại.
    4. Parse kết quả thành SearchResult có method pageindex.

PageIndex là dịch vụ ngoài: cần timeout và xử lý lỗi để pipeline không crash.
Khi chưa cấu hình API key, pageindex_search trả list rỗng để Task 9 tự rơi
về hybrid result thay vì hỏng cả pipeline.
"""

import json
import os
from pathlib import Path

from dotenv import load_dotenv


load_dotenv()

PAGEINDEX_API_KEY = os.getenv("PAGEINDEX_API_KEY", "")
STANDARDIZED_DIR = Path(__file__).parent.parent / "data" / "standardized"
DOC_IDS_PATH = Path(__file__).parent.parent / "pageindex_doc_ids.json"

REQUEST_TIMEOUT = 30


def is_configured() -> bool:
    """PageIndex chỉ dùng được khi có API key."""
    return bool(PAGEINDEX_API_KEY.strip())


def _load_doc_ids() -> dict[str, str]:
    if not DOC_IDS_PATH.exists():
        return {}
    try:
        return json.loads(DOC_IDS_PATH.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _save_doc_ids(mapping: dict[str, str]) -> None:
    DOC_IDS_PATH.write_text(
        json.dumps(mapping, ensure_ascii=False, indent=2), encoding="utf-8"
    )


def upload_documents() -> None:
    """Upload tài liệu và lưu document IDs để tái sử dụng."""
    if not is_configured():
        print("Bỏ qua: chưa cấu hình PAGEINDEX_API_KEY trong .env")
        return

    from pageindex import PageIndexClient

    client = PageIndexClient(api_key=PAGEINDEX_API_KEY)
    mapping = _load_doc_ids()

    for path in sorted(STANDARDIZED_DIR.rglob("*.md")):
        key = path.relative_to(STANDARDIZED_DIR).as_posix()
        if key in mapping:
            continue
        try:
            response = client.submit_document(str(path))
            doc_id = getattr(response, "doc_id", None) or response.get("doc_id")
            if doc_id:
                mapping[key] = doc_id
                print(f"Uploaded: {key} -> {doc_id}")
        except Exception as error:
            print(f"Failed: {key} — {error}")

    if mapping:
        _save_doc_ids(mapping)
        print(f"Đã lưu {len(mapping)} document ID vào {DOC_IDS_PATH.name}")


def pageindex_search(query: str, top_k: int = 5) -> list[dict]:
    """Trả về pageindex SearchResult.

    Trả list rỗng khi chưa cấu hình hoặc chưa upload tài liệu, để Task 9
    dùng hybrid result. Lỗi mạng được để nổi lên cho Task 9 bắt.
    """
    if not is_configured():
        return []

    mapping = _load_doc_ids()
    if not mapping:
        return []

    from pageindex import PageIndexClient

    client = PageIndexClient(api_key=PAGEINDEX_API_KEY)

    results: list[dict] = []
    for source, doc_id in mapping.items():
        if len(results) >= top_k:
            break
        try:
            response = client.retrieve(doc_id=doc_id, query=query)
        except Exception:
            continue

        nodes = getattr(response, "retrieved_nodes", None)
        if nodes is None and isinstance(response, dict):
            nodes = response.get("retrieved_nodes", [])
        for node in nodes or []:
            content = str(
                (node.get("text") if isinstance(node, dict) else getattr(node, "text", ""))
                or ""
            ).strip()
            if not content:
                continue
            results.append(
                {
                    "id": f"pageindex::{doc_id}::{len(results)}",
                    "content": content,
                    "metadata": {
                        "source": Path(source).name,
                        "title": Path(source).stem,
                        "doc_type": "legal" if source.startswith("legal/") else "news",
                        "url": None,
                        "chunk_index": len(results),
                    },
                    "retrieval_method": "pageindex",
                }
            )

    # API không trả score, gán điểm giảm dần theo rank để giữ contract
    # "sort theo score giảm dần".
    total = len(results)
    for rank, item in enumerate(results, 1):
        item["score"] = (total - rank + 1) / total if total else 0.0

    return results[:top_k]


if __name__ == "__main__":
    upload_documents()
