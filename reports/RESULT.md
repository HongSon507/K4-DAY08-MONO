# RAG evaluation results

## Run information

| Field                              | Value |
| ---------------------------------- | ----- |
| Evaluation date                    | 2026-09-20 |
| Framework and version              | Ragas 0.4.3 / LangChain 0.4.1 |
| Evaluator model                    | gpt-4o-mini |
| Generator model                    | gpt-4o-mini |
| Embedding model                    | BAAI/bge-m3 (dim=1024) |
| Corpus version/commit              | 10 documents (3 legal PDFs, 7 news articles, 203 chunks) |
| Golden dataset size                | 20 grounded cases |
| `top_k`                            | 5 |
| Fallback threshold and calibration | `SCORE_THRESHOLD = 0.50` (in-domain ~0.73, out-of-domain ~0.43) |

## Configurations

- **Config A — dense-only:** Sử dụng `BAAI/bge-m3` embedding và ChromaDB với cosine similarity, lấy top-5 chunks theo thứ tự điểm tương đồng giảm dần.
- **Config B — hybrid + RRF:** Kết hợp dense search (`BAAI/bge-m3`) và lexical search (`BM25Okapi` với tokenizer tiếng Việt) thông qua Reciprocal Rank Fusion ($k=60$) đúng một lần, lấy top-5 chunks.

Hai config sử dụng chung golden dataset, generator (`gpt-4o-mini`), evaluator, prompt và `top_k=5`; chỉ thay đổi chiến lược retrieval.

## Overall scores

| Metric            | Config A (Dense-only) | Config B (Hybrid + RRF) | Delta B−A |
| ----------------- | --------------------: | ----------------------: | --------: |
| Faithfulness      |                0.9200 |                  0.9650 |   +0.0450 |
| Answer relevance  |                0.8950 |                  0.9450 |   +0.0500 |
| Context recall    |                0.9000 |                  0.9500 |   +0.0500 |
| Context precision |                0.8250 |                  0.8333 |   +0.0083 |
| **Average**       |            **0.8850** |              **0.9233** |**+0.0383**|

## A/B comparison

- **Cấu hình tốt hơn:** **Config B (Hybrid + RRF)** vượt trội hơn Config A trên tất cả các tiêu chí đánh giá, đặc biệt là Context Recall (+5.0%) và Answer Relevance (+5.0%).
- **Evidence:** 
  - Ở các câu hỏi chứa mã văn bản, niên khóa hoặc con số đặc thù (ví dụ: Case Q05 về khóa `QH-2021` của UET), Config A hoàn toàn bỏ lỡ context (Recall = 0.0), dẫn đến model từ chối trả lời; trong khi Config B đưa đúng chunk liên quan lên vị trí Rank 1 nhờ khả năng khớp từ khóa chính xác của BM25.
  - Khả năng lọc nhiễu và định vị ngữ cảnh của Hybrid + RRF giúp tăng tỷ lệ sinh câu trả lời có bằng chứng rõ ràng (`[Document N]`), giảm thiểu hallucination.
- **Trade-off về latency/cost:**
  - **Latency:** Config B bổ sung bước tính BM25 và RRF (thêm ~15ms trên tập 203 chunks), tuy nhiên tổng thời gian retrieval vẫn duy trì ở mức dưới 150ms.
  - **Cost:** Chi phí embedding không tăng vì chỉ thực hiện 1 lần encode query; token đầu vào LLM được tối ưu hóa tốt hơn nhờ context cô đọng và thứ tự reorder hợp lý.

## Worst performers

|   # | Question | Config | Faithfulness | Relevance | Recall | Precision | Failure stage | Root cause |
| --: | -------- | ------ | -----------: | --------: | -----: | --------: | ------------- | ---------- |
|   1 | Ở UET, học bổng loại Giỏi cho sinh viên chương trình chuẩn khóa QH-2021 là bao nhiêu mỗi tháng? (Q05) | Config A (Dense) | 0.8000 | 0.4000 | 0.0000 | 0.0000 | Retrieval | Dense embedding không bắt được mã khóa học đặc thù `QH-2021` trong bảng biểu số liệu, làm mất context cần thiết. |
|   2 | Trường Đại học Công nghệ Thông tin yêu cầu tối thiểu bao nhiêu tín chỉ để xét học bổng khuyến khích học tập? (Q19) | Cả hai Config | 0.8500 | 0.5000 | 0.0000 | 0.0000 | Data & Retrieval | Mismatch tên viết tắt: Tài liệu gốc dùng `UIT` và `STC tối thiểu là 14`, trong khi query dùng `Trường Đại học Công nghệ Thông tin`, khiến retrieval nhầm sang UET (`15 tín chỉ`). |
|   3 | Học bổng Cử nhân Kinh doanh của RMIT Việt Nam trị giá bao nhiêu và yêu cầu GPA lớp 12 thế nào? (Q09) | Config B (Hybrid) | 0.9500 | 0.9000 | 1.0000 | 0.3333 | Retrieval | Từ khóa `RMIT` và `Kinh doanh` xuất hiện ở nhiều bài viết chung của RMIT khiến BM25 trả về nhiều chunk cạnh tranh, đẩy chunk mục tiêu từ Rank 1 xuống Rank 3 trong RRF. |

## Recommendations

| Priority | Action | Evidence from failure analysis | Expected impact | How to verify |
| -------: | ------ | ------------------------------ | --------------- | ------------- |
|        1 | Bổ sung từ điển đồng nghĩa (Synonyms/Aliases) cho tên trường và thuật ngữ viết tắt (UIT $\leftrightarrow$ ĐH Công nghệ Thông tin, STC $\leftrightarrow$ Số tín chỉ). | Case Q19 bị fail do tài liệu chỉ chứa viết tắt `UIT`, dẫn tới nhầm lẫn với `UET`. | Nâng Context Recall của các câu hỏi viết tắt lên 100%, loại bỏ nhầm lẫn giữa các trường cùng khối. | Chạy lại `pytest tests/test_acceptance.py` và eval case Q19. |
|        2 | Nâng cấp Document Pre-processing để giữ nguyên cấu trúc bảng học phí và niên khóa dưới dạng Markdown Table chuẩn. | Case Q05 cho thấy bảng số liệu học phí phân theo khóa dễ bị xé vụn khi chunking theo số ký tự thuần túy. | Cải thiện Context Precision cho các câu hỏi tra cứu hạn mức tiền và niên khóa. | Kiểm tra điểm số của nhóm câu hỏi bảng số liệu (Q05, Q12, Q16). |
|        3 | Tối ưu hóa trọng số candidate pool cho Dense vs BM25 hoặc thêm Cross-Encoder Re-ranker nhẹ trước khi đưa vào LLM. | Case Q09 bị loãng thứ hạng do BM25 khớp từ khóa quá rộng trên cùng một thực thể (RMIT). | Cải thiện Context Precision từ 0.83 lên > 0.90 trên các trường có nhiều trang bài viết tương đồng. | Đánh giá lại MRR trên toàn bộ 20 golden cases. |

## Bonus experiments

| Experiment | Baseline | Metric delta | Latency/cost delta | Conclusion |
| ---------- | -------- | -----------: | -----------------: | ---------- |
| Reorder context (Lost-in-the-middle mitigation) | Thứ tự score giảm dần tuần tự | Faithfulness +3.2%, Citation accuracy +5.0% | +0ms latency / $0 cost | Đặt các chunk quan trọng nhất ở đầu và cuối context giúp LLM định vị dẫn chứng chính xác hơn mà không tốn thêm chi phí tính toán. |

