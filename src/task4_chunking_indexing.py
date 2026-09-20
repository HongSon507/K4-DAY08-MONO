"""
Task 4 — Chunking, embedding và indexing.

Đọc Markdown trong data/standardized/, chunk, embed rồi upsert vào ChromaDB.

ID chunk có dạng "<legal|news>/<file>.md::chunk-<n>" nên ổn định giữa các lần
chạy: upsert lại cùng corpus không sinh bản ghi trùng.

Task 5 import embed_texts() từ đây để query và index luôn dùng chung model,
đúng yêu cầu trong docs/MODULE_CONTRACTS.md.
"""

import os
import sys
from pathlib import Path

from dotenv import load_dotenv


if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

load_dotenv()

STANDARDIZED_DIR = Path(__file__).parent.parent / "data" / "standardized"
CHROMA_DIR = Path(__file__).parent.parent / "chroma_db"

# Giải thích lựa chọn tham số trong báo cáo nhóm.
CHUNK_SIZE = 500
CHUNK_OVERLAP = 50
CHUNKING_METHOD = "recursive"

EMBEDDING_MODEL = "text-embedding-3-small"
EMBEDDING_DIM = 1536

COLLECTION_NAME = "rag_documents"

EMBED_BATCH_SIZE = 32

_MODEL = None


def _provider() -> str:
    return os.getenv("EMBEDDING_PROVIDER", "sentence_transformers").strip().lower()


def _model_name() -> str:
    return os.getenv("EMBEDDING_MODEL", "").strip() or EMBEDDING_MODEL


def embed_texts(texts: list[str]) -> list[list[float]]:
    """Embed danh sách text bằng provider khai báo trong .env.

    Dùng chung cho cả indexing (Task 4) và query (Task 5) để vector cùng
    không gian; lệch model giữa hai bên sẽ làm cosine score vô nghĩa.
    """
    global _MODEL

    if not texts:
        return []

    provider = _provider()
    model_name = _model_name()

    if provider == "sentence_transformers":
        from sentence_transformers import SentenceTransformer

        if _MODEL is None:
            _MODEL = SentenceTransformer(model_name)
        vectors = _MODEL.encode(
            texts,
            batch_size=EMBED_BATCH_SIZE,
            normalize_embeddings=True,
            show_progress_bar=False,
        )
        return [vector.tolist() for vector in vectors]

    if provider == "openai":
        from openai import OpenAI

        client = OpenAI()
        response = client.embeddings.create(
            model=model_name or "text-embedding-3-small", input=texts
        )
        return [item.embedding for item in response.data]

    if provider == "gemini":
        from google import genai

        client = genai.Client()
        response = client.models.embed_content(
            model=model_name or "gemini-embedding-001", contents=texts
        )
        return [list(item.values) for item in response.embeddings]

    raise ValueError(f"EMBEDDING_PROVIDER không hỗ trợ: {provider}")


def get_collection():
    """Mở Chroma collection dùng cosine distance."""
    import chromadb

    CHROMA_DIR.mkdir(parents=True, exist_ok=True)
    client = chromadb.PersistentClient(path=str(CHROMA_DIR))
    return client.get_or_create_collection(
        name=COLLECTION_NAME,
        metadata={"hnsw:space": "cosine"},
    )


def _split_frontmatter(text: str) -> tuple[dict, str]:
    """Tách YAML frontmatter khỏi phần thân.

    Frontmatter là metadata, không phải nội dung để trả lời; embed cả khối
    đó sẽ làm nhiễu vector.
    """
    if not text.startswith("---"):
        return {}, text

    parts = text.split("---", 2)
    if len(parts) < 3:
        return {}, text

    try:
        import yaml

        meta = yaml.safe_load(parts[1]) or {}
    except Exception:
        meta = {}

    if not isinstance(meta, dict):
        meta = {}
    return meta, parts[2].strip()


def load_documents() -> list[dict]:
    """Đọc Markdown và trả về danh sách Document."""
    documents: list[dict] = []

    for path in sorted(STANDARDIZED_DIR.rglob("*.md")):
        raw = path.read_text(encoding="utf-8")
        meta, body = _split_frontmatter(raw)
        if not body.strip():
            continue

        doc_type = "legal" if "legal" in path.parts else "news"
        url = str(meta.get("source_url", "") or "").strip() or None

        documents.append(
            {
                "id": path.relative_to(STANDARDIZED_DIR).as_posix(),
                "content": body,
                "metadata": {
                    "source": path.name,
                    "title": str(meta.get("title", "") or path.stem).strip(),
                    "doc_type": doc_type,
                    "url": url,
                },
            }
        )

    return documents


def chunk_documents(documents: list[dict]) -> list[dict]:
    """Chia Document thành chunks có id và chunk_index."""
    from langchain_text_splitters import RecursiveCharacterTextSplitter

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=CHUNK_SIZE,
        chunk_overlap=CHUNK_OVERLAP,
        separators=["\n\n", "\n", ". ", " ", ""],
    )

    chunks: list[dict] = []
    for document in documents:
        index = 0
        for text in splitter.split_text(document["content"]):
            text = text.strip()
            if not text:
                continue
            chunks.append(
                {
                    "id": f"{document['id']}::chunk-{index}",
                    "content": text,
                    "metadata": {**document["metadata"], "chunk_index": index},
                }
            )
            index += 1

    return chunks


def embed_chunks(chunks: list[dict]) -> list[dict]:
    """Thêm embedding vào từng chunk."""
    vectors = embed_texts([chunk["content"] for chunk in chunks])
    for chunk, vector in zip(chunks, vectors):
        chunk["embedding"] = vector
    return chunks


def _chroma_metadata(metadata: dict) -> dict:
    """Chroma chỉ nhận str/int/float/bool, url=None phải đổi thành chuỗi rỗng."""
    cleaned: dict = {}
    for key, value in metadata.items():
        if value is None:
            cleaned[key] = ""
        elif isinstance(value, (str, int, float, bool)):
            cleaned[key] = value
        else:
            cleaned[key] = str(value)
    return cleaned


def index_to_vectorstore(chunks: list[dict]) -> None:
    """Upsert chunks vào ChromaDB."""
    if not chunks:
        print("Không có chunk nào để index")
        return

    collection = get_collection()
    for start in range(0, len(chunks), 100):
        batch = chunks[start : start + 100]
        collection.upsert(
            ids=[chunk["id"] for chunk in batch],
            documents=[chunk["content"] for chunk in batch],
            embeddings=[chunk["embedding"] for chunk in batch],
            metadatas=[_chroma_metadata(chunk["metadata"]) for chunk in batch],
        )


def run_pipeline() -> None:
    """Chạy load, chunk, embed và index."""
    documents = load_documents()
    print(f"Loaded {len(documents)} documents")

    chunks = chunk_documents(documents)
    print(f"Chunked into {len(chunks)} chunks")

    embedded_chunks = embed_chunks(chunks)
    if embedded_chunks:
        print(f"Embedded dim = {len(embedded_chunks[0]['embedding'])}")

    index_to_vectorstore(embedded_chunks)
    print(f"Indexed {len(embedded_chunks)} chunks")
    print(f"Collection count = {get_collection().count()}")


if __name__ == "__main__":
    run_pipeline()
