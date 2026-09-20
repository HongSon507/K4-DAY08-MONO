"""
Chạy RAGAS 4 metric trên golden dataset, so sánh A/B giữa hai cấu hình
retrieval và ghi kết quả thô ra JSON để dựng RESULT.md.

    Config A — dense-only   : retrieve(use_reranking=False)
    Config B — hybrid + RRF : retrieve(use_reranking=True)

Hai config dùng chung golden dataset, generator, evaluator, prompt và top_k;
chỉ khác đúng một biến use_reranking.

Chạy:
    python -m scripts.run_evaluation
"""

import asyncio
import json
import sys
import time
from pathlib import Path

from dotenv import load_dotenv

from src.task9_retrieval_pipeline import SCORE_THRESHOLD, retrieve
from src.task10_generation import (
    LLM_MODEL,
    SYSTEM_PROMPT,
    call_llm,
    format_context,
    reorder_for_llm,
)


if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

load_dotenv()

ROOT = Path(__file__).parent.parent
GOLDEN = ROOT / "group_project" / "evaluation" / "golden_dataset.json"
OUTPUT = ROOT / "group_project" / "evaluation" / "evaluation_raw.json"

TOP_K = 5
EVALUATOR_MODEL = "gpt-4o-mini"

CONFIGS = {
    "A_dense_only": False,
    "B_hybrid_rrf": True,
}


def answer_for(question: str, use_reranking: bool) -> tuple[str, list[str], list[dict]]:
    """Sinh câu trả lời cho một cấu hình retrieval.

    Không gọi generate_with_citation vì hàm đó không nhận use_reranking
    (chữ ký bị contract test khoá), nên lặp lại đúng các bước của nó.
    """
    chunks = retrieve(question, top_k=TOP_K, use_reranking=use_reranking)
    if not chunks:
        return "Không tìm thấy thông tin trong bộ tài liệu hiện có.", [], []

    reordered = reorder_for_llm(chunks)
    context = format_context(reordered)
    try:
        answer = call_llm(SYSTEM_PROMPT, f"Context:\n{context}\n\nQuestion: {question}")
    except Exception as error:
        answer = f"[Lỗi provider: {error}]"

    contexts = [chunk["content"] for chunk in reordered]
    return answer, contexts, reordered


async def score_all(rows: list[dict]) -> list[dict]:
    """Chấm 4 metric cho từng dòng bằng RAGAS."""
    from openai import AsyncOpenAI
    from ragas.embeddings.base import embedding_factory
    from ragas.llms import llm_factory
    from ragas.metrics.collections import (
        AnswerRelevancy,
        ContextPrecision,
        ContextRecall,
        Faithfulness,
    )

    # RAGAS gọi agenerate() nên client phải là async, client đồng bộ sẽ raise.
    client = AsyncOpenAI()
    llm = llm_factory(EVALUATOR_MODEL, client=client)
    embeddings = embedding_factory(
        "openai", model="text-embedding-3-small", client=client
    )

    faithfulness = Faithfulness(llm=llm)
    relevancy = AnswerRelevancy(llm=llm, embeddings=embeddings)
    precision = ContextPrecision(llm=llm)
    recall = ContextRecall(llm=llm)

    async def score_row(row: dict) -> dict:
        question = row["question"]
        answer = row["answer"]
        contexts = row["contexts"]
        reference = row["reference"]

        async def safe(coro):
            try:
                result = await coro
                value = getattr(result, "value", result)
                return float(value)
            except Exception as error:
                print(f"    metric lỗi: {error}")
                return None

        if not contexts:
            return {**row, "faithfulness": 0.0, "answer_relevancy": 0.0,
                    "context_precision": 0.0, "context_recall": 0.0}

        scores = await asyncio.gather(
            safe(faithfulness.ascore(user_input=question, response=answer,
                                     retrieved_contexts=contexts)),
            safe(relevancy.ascore(user_input=question, response=answer)),
            safe(precision.ascore(user_input=question, reference=reference,
                                  retrieved_contexts=contexts)),
            safe(recall.ascore(user_input=question, retrieved_contexts=contexts,
                               reference=reference)),
        )
        return {
            **row,
            "faithfulness": scores[0],
            "answer_relevancy": scores[1],
            "context_precision": scores[2],
            "context_recall": scores[3],
        }

    scored = []
    for index, row in enumerate(rows, 1):
        print(f"  [{index}/{len(rows)}] {row['config']} · {row['id']}")
        scored.append(await score_row(row))
    return scored


def main() -> None:
    golden = json.loads(GOLDEN.read_text(encoding="utf-8"))
    print(f"Golden dataset: {len(golden)} câu · top_k={TOP_K} · threshold={SCORE_THRESHOLD}")
    print(f"Generator: {LLM_MODEL} · Evaluator: {EVALUATOR_MODEL}\n")

    rows: list[dict] = []
    for config_name, use_reranking in CONFIGS.items():
        print(f"--- Sinh câu trả lời: {config_name}")
        for case in golden:
            answer, contexts, chunks = answer_for(case["question"], use_reranking)
            rows.append(
                {
                    "id": case["id"],
                    "config": config_name,
                    "question": case["question"],
                    "answer": answer,
                    "contexts": contexts,
                    "reference": case["expected_answer"],
                    "expected_context": case["expected_context"],
                    "expected_doc_id": case["expected_doc_id"],
                    "retrieved_sources": [c["metadata"]["source"] for c in chunks],
                    "retrieval_method": chunks[0]["retrieval_method"] if chunks else "none",
                }
            )
        print(f"    xong {len(golden)} câu\n")

    print("--- Chấm điểm RAGAS")
    started = time.time()
    scored = asyncio.run(score_all(rows))
    print(f"\nChấm xong trong {time.time() - started:.0f}s")

    OUTPUT.write_text(
        json.dumps(
            {
                "top_k": TOP_K,
                "score_threshold": SCORE_THRESHOLD,
                "generator_model": LLM_MODEL,
                "evaluator_model": EVALUATOR_MODEL,
                "rows": scored,
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    print(f"Đã ghi {OUTPUT}")

    for config_name in CONFIGS:
        subset = [r for r in scored if r["config"] == config_name]
        print(f"\n{config_name}:")
        for metric in ("faithfulness", "answer_relevancy", "context_precision", "context_recall"):
            values = [r[metric] for r in subset if r[metric] is not None]
            mean = sum(values) / len(values) if values else 0.0
            print(f"  {metric:20s} {mean:.4f}  (n={len(values)})")


if __name__ == "__main__":
    main()
