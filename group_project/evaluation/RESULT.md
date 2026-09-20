# RAG evaluation results

## Run information

| Field                              | Value |
| ---------------------------------- | ----- |
| Evaluation date                    | 20/09/2026 |
| Framework and version              | RAGAS 0.4.3 (`ragas.metrics.collections`) |
| Evaluator model                    | `gpt-4o-mini` + `text-embedding-3-small` (answer relevancy) |
| Generator model                    | `gpt-4o-mini` (temperature 0.3, top_p 0.9, max_tokens 1024) |
| Embedding model                    | `text-embedding-3-small`, 1536 chiều |
| Corpus version/commit              | `717c17c` — 10 tài liệu, 203 chunks (recursive 500 / overlap 50) |
| Golden dataset size                | 20 câu |
| `top_k`                            | 5 (mỗi nhánh lấy 10 ứng viên trước khi fuse) |
| Fallback threshold and calibration | **0.44** — hiệu chỉnh trên 20 câu in-domain (min 0.5290) và 5 câu out-of-domain (max 0.3466), chọn điểm giữa hai vùng |

Script tái lập: `python -m scripts.run_evaluation` → `group_project/evaluation/evaluation_raw.json`.

## Configurations

- **Config A — dense-only:** `retrieve(use_reranking=False)`. Chỉ dùng dense search từ ChromaDB, lấy thẳng top-5 theo cosine similarity, không chạy BM25 và không fuse.
- **Config B — hybrid + RRF:** `retrieve(use_reranking=True)`. Dense search và BM25 mỗi nhánh trả 10 ứng viên, gộp bằng RRF `sum(1/(60+rank))` rồi lấy top-5.

Hai config dùng chung golden dataset, generator, evaluator, prompt và `top_k`; chỉ thay đúng một biến `use_reranking`. Ngưỡng fallback giống nhau và PageIndex không được cấu hình nên nhánh fallback không kích hoạt ở cả hai.

## Overall scores

| Metric            | Config A | Config B | Delta B−A |
| ----------------- | -------: | -------: | --------: |
| Faithfulness      |   0.4917 |   0.7042 |  **+0.2125** |
| Answer relevance  |   0.2438 |   0.2940 |  +0.0502 |
| Context recall    |   0.5000 |   0.6500 |  **+0.1500** |
| Context precision |   0.5203 |   0.5510 |  +0.0307 |
| **Average**       |   0.4389 |   0.5498 |  **+0.1109** |

Chỉ số phụ:

| Chỉ số | Config A | Config B |
| --- | ---: | ---: |
| Số câu bị từ chối trả lời | 12/20 | 11/20 |
| Số câu lấy đúng tài liệu nguồn | 17/20 | 16/20 |

## A/B comparison

- **Cấu hình tốt hơn:** Config B — hybrid + RRF. Thắng trên **cả 4 metric**, trung bình cao hơn 0.1109 (+25.3% tương đối).

- **Evidence:** Mức chênh tập trung ở faithfulness (+0.2125) và context recall (+0.1500) — hai chỉ số phản ánh trực tiếp việc context có chứa đáp án hay không. Ca điển hình là câu *"Học bổng loại Giỏi của UET khóa QH-2021 là bao nhiêu mỗi tháng?"*: chunk chứa bảng mức tiền xếp **hạng #2 trong BM25** nhưng **không nằm trong top-20 của dense search** vì nó là bảng markdown toàn con số, gần như không có ngữ nghĩa cho embedding bám vào. Config A do đó không bao giờ thấy chunk này và buộc phải từ chối; Config B được RRF kéo nó lên top-5 và trả lời đúng `1.950.000đ mỗi tháng [Document 3]`.

  Đây chính là lý do tồn tại của hybrid retrieval: BM25 bắt được khớp từ khoá và con số chính xác mà dense bỏ sót, còn RRF gộp theo thứ hạng nên không phải chuẩn hoá cosine score với BM25 score về cùng thang.

- **Trade-off về latency/cost:** Config B thêm một lượt BM25 trên 203 chunk và một lượt fuse RRF. Cả hai chạy local trên CPU, chi phí không đáng kể so với một lượt gọi embedding API và một lượt gọi LLM vốn chiếm gần hết thời gian mỗi truy vấn. BM25 index được cache theo danh tính corpus nên chỉ dựng một lần cho cả phiên. Về tiền, hai config tốn như nhau: cùng 1 lượt embedding query + 1 lượt generation. Toàn bộ vòng chấm 40 dòng × 4 metric mất 723 giây.

## Worst performers

|   # | Question | Config | Faithfulness | Relevance | Recall | Precision | Failure stage             | Root cause |
| --: | -------- | ------ | -----------: | --------: | -----: | --------: | ------------------------- | ---------- |
|   1 | Trường ĐH Công nghệ Thông tin yêu cầu tối thiểu bao nhiêu tín chỉ để xét học bổng KKHT? (Q19) | B | 0.00 | 0.00 | 0.00 | 0.00 | retrieval | Tài liệu đúng `uit-548-qd-hbkkht` có lọt vào context nhưng bị chunk của UET chiếm phần lớn slot; câu "14 tín chỉ" nằm ở chunk không được lấy. Chunking recursive cắt ngang Điều 2 khoản 2 nên mệnh đề "STC tối thiểu là 14 tín chỉ" bị tách khỏi ngữ cảnh "xét học bổng". |
|   2 | RMIT Việt Nam cấp bao nhiêu suất học bổng thành tích cho sinh viên đang học năm 2026? (Q12) | B | 0.50 | 0.00 | 0.00 | 0.00 | retrieval | Toàn bộ 5 chunk lấy về đều từ `uet-merit-scholarship-2025-2026`, **không có chunk nào** từ tài liệu RMIT cần thiết. Hai tài liệu cùng nói về "suất học bổng" và "mức học bổng" nên dense bị hút về tài liệu có mật độ chunk cao hơn. |
|   3 | Sinh viên RMIT Việt Nam đang học cần bao nhiêu tín chỉ và GPA để xin học bổng thành tích 2026? (Q11) | B | 0.33 | 0.00 | 0.00 | 0.50 | retrieval | Cùng nguyên nhân với Q12: context gồm UET và UIT, không có RMIT. Câu hỏi chứa "tín chỉ" và "GPA" là từ khoá xuất hiện dày đặc trong quy định của UET và UIT, kéo retrieval sai hướng. |

### Phân tích lỗi hệ thống

**Mọi lỗi nặng đều ở tầng retrieval, không phải tầng generation.** Khi context chứa đáp án, LLM trả lời đúng và có citation; khi không chứa, LLM từ chối thay vì bịa — safe refusal hoạt động đúng thiết kế. Faithfulness 0.7042 của Config B bị kéo xuống chủ yếu bởi các câu mà RAGAS chấm 0 vì câu trả lời là lời từ chối.

**Nguyên nhân gốc: phân bố chunk lệch do nội dung crawl bị trùng lặp.**

| Tài liệu | Tỷ lệ chunk trong corpus | Tỷ lệ slot retrieve chiếm được (Config B) |
| --- | ---: | ---: |
| `uet-merit-scholarship-2025-2026` | 15.8% | **34%** |
| `ueh-learning-support-scholarship` | 7.9% | 24% |
| `rmit-current-student-scholarship-2026` | 6.4% | 0% ở Q11, Q12 |

Tài liệu UET chiếm gấp **2.2 lần** thị phần retrieval so với thị phần chunk. Kiểm tra file nguồn cho thấy trang `uet.edu.vn` render nội dung lặp: bảng mức học bổng xuất hiện **3 lần**, tiêu đề `Điều 1` xuất hiện **3 lần**, 30 dòng dài bị trùng. Task 3 hiện không có bước khử trùng lặp, nên cùng một nội dung sinh ra 3 chunk gần như giống hệt, vừa làm phình thị phần của tài liệu này vừa chia nhỏ thứ hạng RRF của chính chunk đúng.

**Answer relevance thấp ở cả hai config (0.2438 và 0.2940)** là hệ quả đo lường chứ không hoàn toàn là lỗi hệ thống: RAGAS chấm metric này bằng cách sinh ngược câu hỏi từ câu trả lời rồi so với câu hỏi gốc, nên một lời từ chối hợp lệ vẫn bị chấm 0. Với 11/20 câu bị từ chối ở Config B, trần lý thuyết của metric này chỉ khoảng 0.45. Con số này nên đọc kèm tỷ lệ từ chối chứ không đọc độc lập.

## Recommendations

| Priority | Action | Evidence from failure analysis | Expected impact | How to verify |
| -------: | ------ | ------------------------------ | --------------- | ------------- |
|        1 | Thêm bước khử trùng lặp vào `task3_convert_markdown`: phát hiện và loại các đoạn lặp trước khi ghi Markdown | Bảng mức học bổng UET lặp 3 lần, 30 dòng dài trùng; UET chiếm 34% slot retrieve trên 15.8% chunk | Giảm thị phần UET về sát 15%, giải phóng slot cho RMIT và UIT ở Q11, Q12, Q19 | Chạy lại `run_evaluation.py`, so bảng phân bố slot và context recall của 3 câu tệ nhất |
|        2 | Đổi chunking từ recursive sang cắt theo heading/Điều cho tài liệu `legal` | Q19 thất bại vì mệnh đề "STC tối thiểu là 14 tín chỉ" bị cắt khỏi ngữ cảnh "xét học bổng"; văn bản pháp quy có cấu trúc Điều/Khoản rõ ràng mà recursive splitter cắt ngang | Tăng context precision, giảm số chunk vụn không đủ nghĩa | So context precision trước/sau trên 4 câu thuộc nhóm `doc_type=legal` |
|        3 | Bổ sung metadata filter theo `institution` khi câu hỏi nêu rõ tên trường | Q11 và Q12 hỏi RMIT nhưng context toàn UET và UIT; metadata `institution` đã có sẵn trong frontmatter nhưng chưa được dùng để lọc | Loại hẳn nhiễu chéo giữa các trường cho nhóm câu hỏi nêu đích danh tên trường | Đo riêng context recall trên các câu có tên trường trong `question`, trước và sau khi bật filter |

## Bonus experiments

| Experiment | Baseline | Metric delta | Latency/cost delta | Conclusion |
| ---------- | -------- | -----------: | -----------------: | ---------- |
| Đổi embedding `paraphrase-multilingual-MiniLM-L12-v2` (384 chiều) → `text-embedding-3-small` (1536 chiều) | MiniLM chạy local | Không chấm RAGAS cho MiniLM; kiểm chứng định tính: câu hỏi mức học bổng UET chuyển từ **từ chối sai** sang **trả lời đúng** `1.950.000đ [Document 3]` | Mất khả năng chạy offline, phát sinh chi phí embedding cho 203 chunk mỗi lần index lại; bù lại không phải tải model 2.2 GB | Nhận. MiniLM xếp chunk đúng ngoài top-20 dense ở cả câu đã thử, không đủ chất lượng cho corpus tiếng Việt này |
| Hiệu chỉnh `SCORE_THRESHOLD` 0.3 → 0.44 | Mặc định 0.3 của đề bài | In-domain min 0.5290 vs out-of-domain max 0.3466 — hai vùng tách bạch, không chồng lấn | Không đổi | Nhận. Với ngưỡng 0.3, câu ngoài domain *"Thời tiết Hà Nội ngày mai thế nào?"* đạt 0.3466 nên **không** kích hoạt fallback; ngưỡng 0.44 phân loại đúng cả 25 query đã thử |
| Cascade lọc nội dung 3 bậc khi crawl (`target_elements` → pruning → raw) | Crawl thô bằng `raw_markdown` | `rmit-business`: 29854 → 5291 ký tự, 256 → 10 link. `ueh-learning-support`: 22379 → 5797 ký tự, 254 → 2 link | Thêm tối đa 2 lượt crawl mỗi URL khi bậc đầu trả rỗng | Nhận. Bậc fallback là bắt buộc: `target_elements` trả **rỗng hoàn toàn** trên `rmit.edu.vn` vì trang không dùng `<main>`/`<article>` |
