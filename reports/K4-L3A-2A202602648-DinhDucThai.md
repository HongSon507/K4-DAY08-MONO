# Individual contribution report

Mỗi thành viên copy template này thành:

```text
reports/<student-id>-<short-name>.md
```

Giới hạn khuyến nghị: 1 trang, không chép lại README hoặc mô tả lý thuyết chung. Báo cáo không phải một bài pipeline cá nhân; mục đích là ghi nhận ownership và bằng chứng đóng góp trong sản phẩm nhóm.

---

## Thông tin

- Họ và tên: Đinh Đức Thái
- Mã học viên: K4-L3-2A202602648
- Nhóm: Mono
- Repository: `HongSon507/K4-L3A-RAG-Pipeline` 
- Branch: ducthais
## Phần việc đã thực hiện 

| Module/deliverable | Việc tôi trực tiếp làm | File/commit/PR | Trạng thái |
|---|---|---|---|
| **Chunking & Indexing (Task 4)** | Thiết kế chunking đệ quy (`CHUNK_SIZE=500`, `CHUNK_OVERLAP=50`), embedding vector bằng `BAAI/bge-m3` và upsert 203 chunks vào ChromaDB | `src/task4_chunking_indexing.py` | Done |
| **Dense & BM25 Search (Task 5, 6)** | Xây dựng tìm kiếm ngữ nghĩa cosine similarity và BM25Okapi với tokenizer tiếng Việt giữ nguyên dấu và mã định danh | `src/task5_semantic_search.py`, `src/task6_lexical_search.py` | Done |
| **Hybrid RRF & Fallback (Task 7, 8, 9)** | Hiện thực Reciprocal Rank Fusion ($k=60$), cơ chế fallback theo ngưỡng cosine dense score và xử lý lỗi dịch vụ ngoài | `src/task7_reranking.py`, `src/task8_pageindex_vectorless.py`, `src/task9_retrieval_pipeline.py` | Done |
| **Generation & A/B Evaluation (Task 10, 11)** | Hiện thực sinh câu trả lời kèm citation `[Document N]`, reorder context giảm lost-in-the-middle, benchmark 20 golden cases và hoàn thiện báo cáo | `src/task10_generation.py`, `group_project/evaluation/RESULT.md` | Done |
| **Streamlit Interface & Tests** | Vận hành ứng dụng Streamlit tra cứu học bổng, fix lỗi watcher `torchvision`, kiểm thử 100% acceptance & contract tests | `app.py`, `tests/test_acceptance.py`, `tests/test_contracts.py` | Done |
Trên branch: ducthais

## Quyết định kỹ thuật quan trọng

1. **Quyết định:** Sử dụng Reciprocal Rank Fusion (RRF) thay vì cộng gộp có trọng số (Weighted Score Sum) giữa Dense và BM25.  
   **Lý do/evidence:** Cosine similarity ($[0, 1]$) và BM25 score ($[0, +\infty)$) nằm ở hai thang đo hoàn toàn khác nhau. RRF dựa trên thứ hạng vị trí giúp tránh việc một điểm số BM25 quá lớn lấn át hoàn toàn độ tương đồng ngữ nghĩa. Thực nghiệm trên 20 golden cases cho thấy RRF tăng Context Recall từ 0.90 lên 0.95 và khắc phục triệt để lỗi mất context đối với các mã số khóa học (case Q05).  
   **Trade-off:** RRF score chỉ biểu thị độ ưu tiên tương đối, không phản ánh độ tin cậy tuyệt đối (confidence score) của retrieval. Do đó, quyết định Fallback phải được tách biệt và căn cứ theo cosine score gốc của dense retrieval.

2. **Quyết định:** Áp dụng chiến lược Reorder Context (Lost-in-the-middle mitigation) trước khi đưa vào LLM Prompt.  
   **Lý do/evidence:** Các mô hình ngôn ngữ lớn (LLM) thường chú ý tốt nhất vào phần đầu và cuối của ngữ cảnh dài. Việc đưa các chunk có điểm RRF cao nhất về 2 đầu giúp model trích dẫn citation chính xác hơn.  
   **Trade-off:** Cần bảo đảm mapping giữa nhãn `[Document N]` trong prompt và mảng `sources` trả về cho UI được đồng bộ hoàn toàn để citation luôn kiểm chứng được.

## Kiểm thử và kết quả

- Test hoặc query tôi đã dùng:
  - Contract tests: `pytest tests/test_contracts.py -q` (15/15 passed).
  - Acceptance tests: `pytest tests/test_acceptance.py -q` (5/5 passed).
  - Benchmark A/B: Thực hiện trên 20 ground-truth cases trong `golden_dataset.json`.
- Kết quả trước/sau nếu có:
  - Context Recall: 0.9000 (Dense-only) $\rightarrow$ 0.9500 (Hybrid + RRF, $+5.0\%$).
  - Answer Relevance: 0.8950 $\rightarrow$ 0.9450 ($+5.0\%$).
  - Average Score: 0.8850 $\rightarrow$ 0.9233 ($+3.83\%$).
- Lỗi đã phát hiện và cách xử lý:
  - Lỗi `ModuleNotFoundError: No module named 'torchvision'` khi chạy Streamlit watcher $\rightarrow$ cài đặt `torchvision` tương thích vào `.venv`.
  - Lỗi mismatch từ khóa viết tắt (Case Q19: `UIT` vs `Đại học Công nghệ Thông tin`) $\rightarrow$ đề xuất giải pháp thêm synonym dictionary trong kế hoạch cải tiến.

## Điều còn hạn chế

- Một hạn chế cụ thể của phần tôi làm: Hiện tại pipeline chưa có bước Query Expansion/Rewriting, dẫn đến việc các câu hỏi sử dụng tên viết tắt không đồng nhất với tài liệu gốc có thể làm giảm độ chính xác của BM25.
- Nếu có thêm thời gian, thay đổi đầu tiên tôi sẽ thực hiện: Tích hợp một module tiền xử lý truy vấn (Query Reformulation) nhẹ để tự động giải nghĩa các từ viết tắt của trường đại học trước khi chuyển vào Dense và BM25.

## Xác nhận đóng góp

Tôi xác nhận nội dung trên phản ánh đúng phần việc của mình và có thể giải thích hoặc chạy lại trong buổi demo.

- Ngày: 20/09/2026
- Tên thành viên: Đinh Đức Thái

