"""
Task 10 — Generation có citation.

Hướng dẫn:
    1. Retrieve top-k chunks.
    2. Reorder để giảm lost-in-the-middle.
    3. Format context kèm title và source.
    4. Gọi provider được chọn trong .env.
    5. Trả answer, sources và retrieval_source.

Nếu context không đủ hoặc provider lỗi, trả safe refusal; không bịa thông tin.
"""

import os

from dotenv import load_dotenv

from .task9_retrieval_pipeline import retrieve


load_dotenv()

TOP_K = 5
TOP_P = 0.9
TEMPERATURE = 0.3
MAX_TOKENS = 1024

LLM_PROVIDER = os.getenv("LLM_PROVIDER", "openai")
LLM_MODEL = os.getenv("LLM_MODEL", "")

DEFAULT_MODELS = {
    "openai": "gpt-4o-mini",
    "gemini": "gemini-2.5-flash",
    "anthropic": "claude-sonnet-5",
}

REFUSAL = (
    "Tôi không tìm thấy thông tin này trong bộ tài liệu hiện có, "
    "nên không thể trả lời một cách chắc chắn."
)

SYSTEM_PROMPT = """Trả lời chỉ từ context được cung cấp.
Mỗi khẳng định phải có citation dạng [Document N] trỏ tới document đã dùng.
Nếu context không chứa thông tin cần thiết, hãy nói rõ là không tìm thấy
thay vì suy đoán. Trả lời bằng tiếng Việt."""


def reorder_for_llm(chunks: list[dict]) -> list[dict]:
    """Đưa chunks quan trọng về đầu và cuối context.

    LLM đọc kém phần giữa context dài (lost-in-the-middle), nên chunk điểm
    cao nhất được đặt ở hai đầu. Không sửa list gốc và không đổi ID.
    """
    if len(chunks) <= 2:
        return list(chunks)

    front = chunks[::2]
    back = chunks[1::2]
    return front + back[::-1]


def format_context(chunks: list[dict]) -> str:
    """Tạo context có title và source label.

    Nhãn [Document N] là thứ LLM trích dẫn, và N ánh xạ đúng về phần tử
    thứ N trong danh sách sources nên citation kiểm chứng được.
    """
    parts = []
    for index, chunk in enumerate(chunks, 1):
        metadata = chunk.get("metadata", {})
        parts.append(
            f"[Document {index} | Title: {metadata.get('title', '')} | "
            f"Source: {metadata.get('source', '')}]\n{chunk['content']}"
        )
    return "\n\n---\n\n".join(parts)


def call_llm(system_prompt: str, user_message: str) -> str:
    """Gọi OpenAI, Gemini hoặc Anthropic theo cấu hình."""
    provider = LLM_PROVIDER.strip().lower()
    model = LLM_MODEL.strip() or DEFAULT_MODELS.get(provider, "")

    if provider == "openai":
        from openai import OpenAI

        client = OpenAI()
        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message},
            ],
            temperature=TEMPERATURE,
            top_p=TOP_P,
            max_tokens=MAX_TOKENS,
        )
        return (response.choices[0].message.content or "").strip()

    if provider == "gemini":
        from google import genai
        from google.genai import types

        client = genai.Client()
        response = client.models.generate_content(
            model=model,
            contents=user_message,
            config=types.GenerateContentConfig(
                system_instruction=system_prompt,
                temperature=TEMPERATURE,
                top_p=TOP_P,
                max_output_tokens=MAX_TOKENS,
            ),
        )
        return (response.text or "").strip()

    if provider == "anthropic":
        import anthropic

        client = anthropic.Anthropic()
        response = client.messages.create(
            model=model,
            system=system_prompt,
            messages=[{"role": "user", "content": user_message}],
            temperature=TEMPERATURE,
            top_p=TOP_P,
            max_tokens=MAX_TOKENS,
        )
        return "".join(
            block.text for block in response.content if getattr(block, "type", "") == "text"
        ).strip()

    raise ValueError(f"LLM_PROVIDER không hỗ trợ: {provider}")


def generate_with_citation(query: str, top_k: int = TOP_K) -> dict:
    """Trả về GenerationResult."""
    chunks = retrieve(query, top_k=top_k)
    if not chunks:
        return {"answer": REFUSAL, "sources": [], "retrieval_source": "none"}

    reordered = reorder_for_llm(chunks)
    context = format_context(reordered)
    user_message = f"Context:\n{context}\n\nQuestion: {query}"

    try:
        answer = call_llm(SYSTEM_PROMPT, user_message)
    except Exception as error:
        # Provider lỗi vẫn phải trả GenerationResult hợp lệ, kèm sources đã
        # retrieve được để người dùng tự đối chiếu.
        return {
            "answer": f"{REFUSAL} (Lỗi provider: {error})",
            "sources": chunks,
            "retrieval_source": chunks[0]["retrieval_method"],
        }

    if not answer:
        return {
            "answer": REFUSAL,
            "sources": chunks,
            "retrieval_source": chunks[0]["retrieval_method"],
        }

    # Citation trỏ theo thứ tự context đã reorder, nên sources phải trả về
    # đúng thứ tự đó thì [Document N] mới map được.
    return {
        "answer": answer,
        "sources": reordered,
        "retrieval_source": reordered[0]["retrieval_method"],
    }


if __name__ == "__main__":
    import sys

    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    print(generate_with_citation("Học bổng khuyến khích học tập của UET là bao nhiêu?"))
