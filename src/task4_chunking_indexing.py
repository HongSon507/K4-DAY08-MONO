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

from .contracts import validate_document


if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

load_dotenv()

STANDARDIZED_DIR = Path(__file__).parent.parent / "data" / "standardized"
CHROMA_DIR = Path(__file__).parent.parent / "chroma_db"

# Giải thích lựa chọn tham số trong báo cáo nhóm.
CHUNK_SIZE = 500
CHUNK_OVERLAP = 50
CHUNKING_METHOD = "recursive"

EMBEDDING_MODEL = "local-tfidf-svd-128"
EMBEDDING_DIM = 128

COLLECTION_NAME = "rag_documents"

EMBED_BATCH_SIZE = 32

_MODEL = None


def _provider() -> str:
    return os.getenv("EMBEDDING_PROVIDER", "local_tfidf").strip().lower()


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

    if provider == "local_tfidf":
        from sklearn.decomposition import TruncatedSVD
        from sklearn.feature_extraction.text import TfidfVectorizer
        from sklearn.pipeline import FeatureUnion
        from sklearn.preprocessing import normalize

        if _MODEL is None:
            # Fit trên corpus chuẩn, không fit trên `texts`: Task 4 và Task 5
            # có thể chạy ở hai process khác nhau nhưng vẫn tạo đúng
            # cùng vocabulary/SVD nhờ corpus và random_state cố định.
            training_texts = [
                chunk["content"]
                for chunk in chunk_documents(load_documents())
            ]
            if len(training_texts) < 2:
                raise ValueError("Cần ít nhất hai chunks để fit local embedding")

            features = FeatureUnion(
                (
                    (
                        "word",
                        TfidfVectorizer(
                            ngram_range=(1, 2),
                            min_df=1,
                            max_features=20_000,
                            strip_accents="unicode",
                            sublinear_tf=True,
                        ),
                    ),
                    (
                        "char",
                        TfidfVectorizer(
                            analyzer="char_wb",
                            ngram_range=(3, 5),
                            min_df=2,
                            max_features=20_000,
                            strip_accents="unicode",
                            sublinear_tf=True,
                        ),
                    ),
                )
            )
            training_matrix = features.fit_transform(training_texts)
            dimensions = min(
                EMBEDDING_DIM,
                training_matrix.shape[0] - 1,
                training_matrix.shape[1] - 1,
            )
            if dimensions < 1:
                raise ValueError("Corpus không đủ feature để fit local embedding")

            reducer = TruncatedSVD(n_components=dimensions, random_state=42)
            reducer.fit(training_matrix)
            _MODEL = (features, reducer)

        features, reducer = _MODEL
        vectors = reducer.transform(features.transform(texts))
        vectors = normalize(vectors, norm="l2")
        return vectors.tolist()

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

    import yaml

    try:
        meta = yaml.safe_load(parts[1]) or {}
    except yaml.YAMLError as error:
        raise ValueError(f"Frontmatter YAML không hợp lệ: {error}") from error

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

        document = {
            "id": path.relative_to(STANDARDIZED_DIR).as_posix(),
            "content": body,
            "metadata": {
                "source": path.name,
                "title": str(meta.get("title", "") or path.stem).strip(),
                "doc_type": doc_type,
                "url": url,
            },
        }
        validate_document(document)
        documents.append(document)

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
        validate_document(document)
        index = 0
        for text in splitter.split_text(document["content"]):
            text = text.strip()
            if not text:
                continue
            chunk = {
                "id": f"{document['id']}::chunk-{index}",
                "content": text,
                "metadata": {**document["metadata"], "chunk_index": index},
            }
            validate_document(chunk, require_chunk=True)
            chunks.append(chunk)
            index += 1

    return chunks


def embed_chunks(chunks: list[dict]) -> list[dict]:
    """Thêm embedding vào từng chunk."""
    for chunk in chunks:
        validate_document(chunk, require_chunk=True)

    vectors = embed_texts([chunk["content"] for chunk in chunks])
    if len(vectors) != len(chunks):
        raise ValueError(
            f"Embedding provider trả {len(vectors)} vector cho {len(chunks)} chunks"
        )

    dimensions = {len(vector) for vector in vectors}
    if vectors and (0 in dimensions or len(dimensions) != 1):
        raise ValueError(f"Embedding dimension không hợp lệ: {sorted(dimensions)}")

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
    """Upsert chunks và xóa ID cũ không còn thuộc corpus."""
    if not chunks:
        print("Không có chunk nào để index")
        return

    ids = [chunk["id"] for chunk in chunks]
    if len(ids) != len(set(ids)):
        raise ValueError("Chunk IDs phải duy nhất trước khi index")
    for chunk in chunks:
        validate_document(chunk, require_chunk=True)
        if not isinstance(chunk.get("embedding"), list) or not chunk["embedding"]:
            raise ValueError(f"Chunk chưa có embedding: {chunk['id']}")

    collection = get_collection()
    for start in range(0, len(chunks), 100):
        batch = chunks[start : start + 100]
        collection.upsert(
            ids=[chunk["id"] for chunk in batch],
            documents=[chunk["content"] for chunk in batch],
            embeddings=[chunk["embedding"] for chunk in batch],
            metadatas=[_chroma_metadata(chunk["metadata"]) for chunk in batch],
        )

    # Upsert ngăn nhân bản khi ID không đổi. Bước prune này còn
    # loại chunk mồ côi khi tài liệu bị xóa hoặc ngắn đi sau lần index trước.
    existing_ids = set(collection.get(include=[]).get("ids") or [])
    stale_ids = sorted(existing_ids - set(ids))
    if stale_ids:
        collection.delete(ids=stale_ids)
        print(f"Pruned {len(stale_ids)} stale chunks")


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
