# Individual contribution report

## Thông tin

- Họ và tên: Bùi Tùng Dương
- Mã học viên: 2A202602775
- Nhóm: Mono
- Repository/branch: https://github.com/HongSon507/K4-L3A-RAG-Pipeline.git — `DuongBT` (commit `3eecae8`, đã được tích hợp vào lịch sử `main`)

## Phần việc đã thực hiện

| Module/deliverable | Việc tôi trực tiếp làm | Bằng chứng trong repo | Trạng thái |
| --- | --- | --- | --- |
| Thiết kế fallback retrieval | Thiết kế luồng quyết định dùng dense cosine score gốc để kích hoạt PageIndex fallback; không dùng RRF score làm confidence vì RRF chỉ biểu diễn thứ hạng. | `TEAMMATE.md`; `src/task9_retrieval_pipeline.py`; `tests/test_contracts.py::test_retrieve_uses_dense_score_for_fallback` | Done |
| PageIndex vectorless fallback | Hoàn thiện luồng upload/caching document ID, parse node trả về thành `SearchResult` với `retrieval_method="pageindex"`, giới hạn `top_k` và giữ thứ tự score giảm dần. | `src/task8_pageindex_vectorless.py`; `pageindex_doc_ids.json` được git-ignore | Done |
| Safe degradation | Bảo đảm khi không có `PAGEINDEX_API_KEY`, chưa upload tài liệu hoặc provider ngoài bị lỗi thì pipeline không crash; hệ thống quay lại hybrid result hoặc safe refusal. | `src/task8_pageindex_vectorless.py`; `src/task9_retrieval_pipeline.py`; `tests/test_contracts.py::test_retrieve_survives_fallback_provider_error` | Done |
| Tích hợp hybrid retrieval | Nối dense và BM25 qua RRF đúng một lần, lấy rộng candidate trước fusion và duy trì schema/ID/metadata xuyên suốt pipeline. | `src/task7_reranking.py`; `src/task9_retrieval_pipeline.py`; `tests/test_contracts.py::test_retrieve_fuses_once_when_dense_is_confident` | Done |
| Tích hợp và kiểm chứng branch | Tạo branch `DuongBT`, củng cố corpus và các module retrieval để có đầu vào ổn định cho fallback; kiểm tra ID deterministic, upsert Chroma và contract test. | Commit `3eecae8`; `data/README.md`; `src/task4_chunking_indexing.py` đến `src/task6_lexical_search.py` | Done |

Phân công cá nhân được ghi trong `TEAMMATE.md`. Một số thay đổi tích hợp trên `main` do trưởng nhóm commit; tôi không nhận là tác giả của UI, generation hay báo cáo evaluation A/B.

## Quyết định kỹ thuật quan trọng

1. **Quyết định:** So sánh `SCORE_THRESHOLD` với cosine similarity cao nhất của dense retrieval, không so sánh với RRF score.  
   **Lý do/evidence:** Dense score phản ánh độ gần giữa query và corpus trong cùng không gian embedding, trong khi RRF score phụ thuộc vị trí xếp hạng và tham số `k`. Contract test `test_retrieve_uses_dense_score_for_fallback` khóa invariant này.  
   **Trade-off:** Threshold phải được hiệu chỉnh lại khi thay corpus hoặc embedding model; không thể dùng một giá trị cố định cho mọi cấu hình.

2. **Quyết định:** Fallback là cơ chế bổ sung, không phải điểm lỗi đơn của pipeline.  
   **Lý do/evidence:** `pageindex_search()` trả danh sách rỗng khi chưa cấu hình; `retrieve()` bắt exception từ provider và trả hybrid result. Nhờ đó UI vẫn hoạt động khi mạng, API key hoặc dịch vụ ngoài gặp sự cố.  
   **Trade-off:** Khi PageIndex không khả dụng, câu hỏi confidence thấp có thể chỉ nhận hybrid result yếu; generation phải tiếp tục giữ safe-refusal policy.

3. **Quyết định:** Chỉ fuse dense và BM25 một lần, đồng thời lấy `2 * top_k` candidate ở mỗi nhánh trước khi RRF.  
   **Lý do/evidence:** Candidate pool rộng cho phép RRF đẩy lên các chunk xuất hiện ổn định trong cả hai danh sách, trong khi fuse nhiều lần sẽ làm sai ý nghĩa rank.  
   **Trade-off:** Tăng nhẹ chi phí truy xuất và số candidate cần xử lý, nhưng không làm tăng số context cuối cùng gửi cho LLM.

## Kiểm thử và kết quả

- Các lệnh kiểm thử đã dùng:
  - `pytest tests/test_contracts.py -q`
  - `pytest -q -p no:cacheprovider`
  - `python -m src.task4_chunking_indexing` trên branch `DuongBT`.
- Kết quả:
  - Contract tests cho schema, thứ tự score, ID và fallback: **15/15 passed**.
  - Toàn bộ test suite hiện tại: **20/20 passed**.
  - Lần kiểm tra indexing trên branch `DuongBT`: 10 documents → 130 chunks → 130 records trong Chroma; chạy lại vẫn giữ collection count 130, không nhân bản.
- Lỗi/edge case đã kiểm tra:
  - Dense score thấp nhưng BM25 cao không được dùng để vượt qua cơ chế fallback.
  - PageIndex ném exception không làm retrieval pipeline crash.
  - Khi dense đủ confidence, RRF chỉ được gọi một lần và PageIndex không bị gọi thừa.

## Điều còn hạn chế

- PageIndex là dịch vụ ngoài cần API key; phần xử lý lỗi đã có contract test nhưng vẫn cần benchmark end-to-end với tài khoản PageIndex thật để đo latency và chất lượng node trả về.
- `SCORE_THRESHOLD` phụ thuộc corpus và embedding model. Nếu corpus thay đổi hoặc nhóm chuyển model, cần chạy lại tập query in-domain/out-of-domain thay vì giữ nguyên ngưỡng cũ.
- Nếu có thêm thời gian, thay đổi đầu tiên tôi sẽ thực hiện là tự động hóa calibration threshold và bổ sung telemetry cho tỷ lệ fallback, latency và safe refusal.

## Xác nhận đóng góp

Tôi xác nhận nội dung trên phản ánh đúng phần việc của mình và có thể giải thích hoặc chạy lại trong buổi demo.

- Ngày: 20/09/2026
- Tên thành viên: Bùi Tùng Dương
