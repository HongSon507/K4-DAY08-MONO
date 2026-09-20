# Day 8 — RAG Pipeline

> ## Sản phẩm của nhóm K4-L3A — Chatbot Học bổng Đại học
>
> **Đề tài:** học bổng đại học Việt Nam. Corpus gồm 3 văn bản chính sách (PDF)
> và 7 bài crawl từ nguồn công khai của VinUni, UEH, UET, RMIT Việt Nam,
> ĐH Luật TP.HCM, ĐH Công nghệ Thông tin và Nghị định 84/2020/NĐ-CP.
> Provenance đầy đủ trong `data/landing/legal/sources.csv` và `data/sources_urls.csv`.
>
> ### Cấu hình đang dùng
>
> | Thành phần | Giá trị | Ghi chú |
> | --- | --- | --- |
> | Generator | `gpt-4o-mini` | `LLM_PROVIDER=openai` |
> | Embedding | `text-embedding-3-small` (1536 chiều) | `EMBEDDING_PROVIDER=openai` |
> | Vector store | ChromaDB, cosine | 203 chunks |
> | Chunking | recursive, 500 / overlap 50 | |
> | `SCORE_THRESHOLD` | **0.44** | đã hiệu chỉnh, xem bên dưới |
>
> `.env.example` mặc định dùng `BAAI/bge-m3`. Nhóm đổi sang OpenAI embedding —
> `.env.example` liệt kê `openai` là provider hợp lệ nên thay đổi nằm trong phạm
> vi cho phép. Lý do và bằng chứng ghi trong `reports/2A202602945-hieu.md`.
>
> ### Hiệu chỉnh ngưỡng fallback
>
> Đo trên 20 câu golden (in-domain) và 5 câu out-of-domain:
>
> | Nhóm | min | max | mean |
> | --- | ---: | ---: | ---: |
> | In-domain | 0.5290 | 0.7513 | 0.6281 |
> | Out-of-domain | 0.2806 | 0.3466 | 0.3133 |
>
> Hai vùng tách bạch, không chồng lấn → chọn điểm giữa **0.44**. Mặc định `0.3`
> của đề bài quá thấp với corpus này: câu *"Thời tiết Hà Nội ngày mai thế nào?"*
> đạt 0.3466 nên sẽ không kích hoạt fallback. Ngưỡng phụ thuộc cả corpus lẫn
> embedding model — đổi model là phải đo lại.
>
> ### Chạy lại từ đầu
>
> ```bash
> python -m pip install -e ".[dev]"
> cp .env.example .env          # điền OPENAI_API_KEY, đặt EMBEDDING_PROVIDER=openai
> python -m src.task1_collect_legal_docs   # tải 3 PDF chính sách
> python -m src.task2_crawl_news           # crawl 7 bài (cần: playwright install chromium)
> python -m src.task3_convert_markdown     # chuẩn hoá sang data/standardized/
> python -m src.task4_chunking_indexing    # BẮT BUỘC: dựng ChromaDB
> pytest -q
> streamlit run app.py
> ```
>
> **`chroma_db/` không được commit** (nằm trong `.gitignore`), nên sau khi clone
> phải chạy `python -m src.task4_chunking_indexing` thì chatbot mới hoạt động.
> Bước này gọi OpenAI embedding cho 203 chunk.
>
> Chạy đánh giá: `python -m scripts.run_evaluation` → ghi
> `group_project/evaluation/evaluation_raw.json`, số liệu tổng hợp trong
> `group_project/evaluation/RESULT.md`.
>
> ### Demo
>
> Sidebar có sẵn 3 nút câu hỏi mẫu và checkbox **Hiện so sánh A/B** (chạy
> `retrieve()` hai lần, chỉ khác `use_reranking`):
>
> | Câu hỏi | Mục đích |
> | --- | --- |
> | Học bổng loại Giỏi của UET khóa QH-2021 là bao nhiêu mỗi tháng? | in-domain, đáp án là con số |
> | UEH hỗ trợ bao nhiêu tiền để thu hút giảng viên có học hàm Giáo sư? | in-domain, `audience=faculty` dễ lẫn |
> | Cách nấu phở bò ngon? | ngoài domain → safe refusal |

---

## Mục tiêu

Mỗi nhóm xây dựng một chatbot RAG trả lời câu hỏi từ bộ tài liệu do nhóm thu thập. Sản phẩm phải có hybrid retrieval, citation, giao diện chat và báo cáo đánh giá.

Nhóm tự chọn bài toán và thu thập dữ liệu phù hợp; repo không cung cấp dữ liệu mẫu.

## Sản phẩm phải nộp

- Repository nhóm chạy được.
- Tối thiểu 3 tài liệu chính sách và 5 bài viết/page do nhóm tự thu thập.
- Pipeline: convert → chunk → index → dense + BM25 → RRF → fallback → generation có citation.
- Chatbot Streamlit hiển thị câu trả lời và nguồn đã dùng.
- Golden dataset tối thiểu 15 câu; đánh giá 4 metric và so sánh A/B.
- `group_project/evaluation/RESULT.md`.
- Mỗi thành viên nộp báo cáo cá nhân theo template trong `group_project/ịndividual/INDIVIDUAL_REPORT.md`.

## Quick start

```bash
python -m venv .venv
source .venv/bin/activate       # Windows: .venv\Scripts\activate
python -m pip install --upgrade pip setuptools wheel
python -m pip install -e ".[dev]"
python -m playwright install chromium
cp .env.example .env
```

Điền API key cần dùng trong `.env`; không commit file này.

```bash
# 1. Thu thập và chuẩn hoá
python -m src.task1_collect_legal_docs
python -m src.task2_crawl_news
python -m src.task3_convert_markdown

# 2. Index và kiểm tra contract
python -m src.task4_chunking_indexing
pytest -q

# 3. Chạy sản phẩm
streamlit run app.py
```

## Lộ trình 3 giờ

| Mốc                  | Thời gian | Kết quả cần có                           |
| -------------------- | --------: | ---------------------------------------- |
| 0. Setup             |   10 phút | Môi trường và `.env` sẵn sàng            |
| 1. Data              |   25 phút | ≥3 legal, ≥5 news, Markdown đã chuẩn hoá |
| 2. Index & search    |   30 phút | ChromaDB, dense search và BM25 chạy được |
| 3. Fusion & fallback |   25 phút | RRF và fallback tuân thủ contract        |
| 4. Generation & UI   |   30 phút | Chatbot trả lời có citation              |
| 5. Evaluation        |   30 phút | 15+ Q&A, 4 metric, A/B comparison        |
| 6. Demo & handoff    |   30 phút | Test, report, demo và push repository    |

## Lưu ý quy tắc để có code quality tốt:

- Dense và BM25 nên cùng trả về `SearchResult` theo một schema.
- RRF chỉ nên dùng để gộp thứ hạng và chỉ chạy một lần.
- Fallback dùng cosine score gốc của dense retrieval.
- Threshold phải được hiệu chỉnh trên query in domain và out of domain, không có một con số đúng cho mọi corpus.

## Tài liệu

- [Module contracts](docs/MODULE_CONTRACTS.md): schema, interface và invariant mà code/test nên tuân theo.
- [Step-by-step guide](docs/STEP_BY_STEP.md): thứ tự triển khai và tiêu chí hoàn thành từng bước.
- [Grading rubric](docs/GRADING_RUBRIC.md): Rubric thang điểm.
- [Individual report](group_project/ịndividual/INDIVIDUAL_REPORT.md): template báo cáo cá nhân.
- [Suggested topics](docs/SUGGESTED_TOPICS.md): danh sách chủ đề tham khảo, không bắt buộc.

## Kiểm tra

```bash
# Contract tests
pytest tests/test_contracts.py -q

# Acceptance tests
pytest tests/test_acceptance.py -q

# Toàn bộ
pytest -q
```
