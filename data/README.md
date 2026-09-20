# Corpus: học bổng và hỗ trợ tài chính đại học

Corpus tập trung vào quy định học bổng khuyến khích học tập, học bổng
tuyển sinh/duy trì và một chính sách hỗ trợ nhân sự tại các trường đại
học Việt Nam.

## Provenance

- `landing/legal/sources.csv`: danh sách ba PDF, URL gốc, ngày tải và số
  hiệu văn bản.
- `sources_urls.csv`: danh sách bảy trang công khai và metadata thiết kế.
- `landing/news/*.json`: snapshot crawl; mỗi file có `url`, `title`,
  `date_crawled` và `content_markdown`.

Không thu thập danh sách người nhận học bổng, tài khoản ngân hàng hay dữ
liệu cá nhân. Các nguồn đều là trang hoặc tài liệu công khai của cơ quan,
trường đại.

## Truy ngược dữ liệu

- `standardized/legal/<name>.md` → `landing/legal/<name>.pdf` → dòng có
  `file_name` tương ứng trong `landing/legal/sources.csv` → `source_url`.
- `standardized/news/<doc_id>.md` → `landing/news/<doc_id>.json` → trường
  `url`.

Frontmatter của mỗi Markdown cũng lưu `doc_id`, tiêu đề, URL, ngày thu
thập và metadata phân loại để debug chunk/index về sau.

## Tái tạo

```bash
python -m src.task1_collect_legal_docs
python -m src.task2_crawl_news
python -m src.task3_convert_markdown
pytest tests/test_acceptance.py -q
```

Các script ghi đè đúng tên file ổn định; chạy lại không sinh bản sao
có hậu tố thời gian.
