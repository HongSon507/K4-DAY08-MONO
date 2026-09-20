# Individual contribution report

## Thông tin

- Họ và tên: Trần Hồng Sơn
- Mã học viên: 2A202602475
- Nhóm: Mono
- Repository/branch: https://github.com/HongSon507/K4-L3A-RAG-Pipeline.git — `main`

## Phần việc đã thực hiện

| Module/deliverable | Việc tôi trực tiếp làm | File/commit/PR | Trạng thái |
|---|---|---|---|
| Golden Dataset | Thiết kế và kiểm chuẩn 15 grounded test cases có đủ `question`, `expected_answer`, `expected_context` dựa trên corpus thực tế (VinUni, UEH, UET, RMIT, NĐ 84, UIT, HCMULAW). | `group_project/evaluation/golden_dataset.json` | Done |
| Đánh giá A/B (A/B Testing) | Tổ chức thử nghiệm so sánh 2 cấu hình (Config A: Dense-only vs Config B: Hybrid + RRF) trên cùng golden dataset, cùng model `gpt-4o-mini`, `top_k=5`. | `group_project/evaluation/RESULT.md` | Done |
| RAGAS Metrics Analysis | Phân tích 4 chỉ số (Faithfulness, Answer Relevance, Context Recall, Context Precision) theo từng tầng, tính toán Delta B−A (+9.75%). | `group_project/evaluation/RESULT.md` | Done |
| Failure Analysis & Recommendations | Phân tích 3 Worst Performers, phân loại stage lỗi (Data/Retrieval/Generation), tìm Root Cause và đề xuất phương án cải tiến kèm cách kiểm chứng. | `group_project/evaluation/RESULT.md` | Done |
| Acceptance Testing Evaluation | Kiểm tra và đảm bảo báo cáo đánh giá thỏa mãn 100% tiêu chí của `test_acceptance.py`. | `tests/test_acceptance.py` | Done |

## Quyết định kỹ thuật quan trọng

1. **Quyết định:** Chọn Cấu hình B (Hybrid Retrieval + RRF) làm cấu hình chuẩn nhờ mức cải thiện vượt trội ở chỉ số Context Recall (+13%).  
   **Lý do/evidence:** Đánh giá A/B 4 metric theo tầng cho thấy Dense-only (Config A) hay bỏ sót thông tin khi câu hỏi chứa từ khóa số hiệu văn bản (như 548/QĐ-ĐHCNTT). Hybrid RRF giúp Context Recall tăng từ 0.80 lên 0.93 và Faithfulness tăng từ 0.88 lên 0.96.  
   **Trade-off:** Tăng thời gian xử lý khoảng 5-10ms cho việc tính BM25 và RRF score, nhưng đảm bảo không bỏ sót bằng chứng quan trọng.

2. **Quyết định:** Xác lập ngưỡng Dense Cosine Similarity `SCORE_THRESHOLD = 0.60` cho cơ chế Fallback.  
   **Lý do/evidence:** Thực nghiệm phân tích điểm số trên các query mẫu trong domain (best score ~0.67) và query ngoài domain (best score ~0.55) cho thấy mốc 0.60 giúp phân định rõ ranh giới, kích hoạt fallback/safe refusal đúng lúc để chống hallucination.  
   **Trade-off:** Một số câu hỏi biến thể xa trong domain có thể tiệm cận ngưỡng này, nhưng giúp bảo vệ mô hình không bịa thông tin khi gặp câu hỏi không có trong corpus.

## Kiểm thử và kết quả

- Test hoặc query tôi đã dùng:
  - `pytest tests/test_acceptance.py -q` (5/5 passed)
  - `pytest -q` (20/20 tests passed)
  - Bộ 15 câu hỏi trong `golden_dataset.json` kiểm tra 4 chỉ số RAGAS.
- Kết quả trước/sau nếu có:
  - **Config A (Dense-only):** Faithfulness 0.88, Answer Relevance 0.85, Context Recall 0.80, Context Precision 0.82 (Trung bình: 0.8375).
  - **Config B (Hybrid + RRF):** Faithfulness 0.96, Answer Relevance 0.94, Context Recall 0.93, Context Precision 0.91 (Trung bình: 0.9350).
  - **Mức cải thiện (Delta B−A):** +0.0975 (+9.75%).
- Lỗi đã phát hiện và cách xử lý:
  - *Lỗi 1:* Dense-only rớt rank các chunk chứa mã số hiệu văn bản (như 548/QĐ-ĐHCNTT) do embedding không biểu diễn tốt từ khóa viết tắt $\rightarrow$ Xử lý bằng cách bổ sung BM25 Lexical Search và gộp thứ hạng RRF.
  - *Lỗi 2:* Thông tin bị phân mảnh do tiêu đề bị tách khỏi nội dung $\rightarrow$ Khuyến nghị điều chỉnh chunking overlap và giữ metadata title xuyên suốt.

## Điều còn hạn chế

- Một hạn chế cụ thể của phần tôi làm: Số lượng 15 golden cases tập trung vào quy chế học bổng đại học, chưa mở rộng ra các câu hỏi dạng đa bước (multi-hop reasoning) phức tạp giữa nhiều trường.
- Nếu có thêm thời gian, thay đổi đầu tiên tôi sẽ thực hiện: Xây dựng bộ dataset 50+ cases và tự động hóa kịch bản chạy RAGAS evaluation framework tự động trong pipeline CI.

## Xác nhận đóng góp

Tôi xác nhận nội dung trên phản ánh đúng phần việc của mình và có thể giải thích hoặc chạy lại trong buổi demo.

- Ngày: 20/09/2026
- Tên thành viên: Trần Hồng Sơn
