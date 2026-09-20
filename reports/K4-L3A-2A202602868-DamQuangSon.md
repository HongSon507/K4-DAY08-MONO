# Báo cáo đóng góp cá nhân — Đàm Quang Sơn

## Thông tin

- Họ và tên: Đàm Quang Sơn
- Mã học viên: 2A202602868
- Nhóm: Mono
- Repository/branch: https://github.com/HongSon507/K4-L3A-RAG-Pipeline — `main`

## Phần việc đã thực hiện

| Module/deliverable | Việc tôi trực tiếp làm | Bằng chứng trong repo | Trạng thái |
| --- | --- | --- | --- |
| Thu thập tài liệu chính sách | Tập hợp 3 PDF về học bổng khuyến khích học tập: Nghị định 84/2020/NĐ-CP, quy định của UIT và quy định của Trường ĐH Luật TP.HCM. | `TEAMMATE.md`; `data/landing/legal/`; `data/landing/legal/sources.csv` | Done |
| Thu thập bài viết và trang web | Tập hợp 7 trang/bài về học bổng của VinUni, UEH, UET và RMIT cho corpus nhóm. | `data/sources_urls.csv`; 7 JSON trong `data/landing/news/` | Done |
| Ghi nhận nguồn gốc | Giữ URL, tên tài liệu và thông tin thu thập trong danh mục nguồn để có thể kiểm tra lại từng tài liệu. | `data/landing/legal/sources.csv`; `data/sources_urls.csv`; trường `url`, `title`, `date_crawled` trong JSON | Done |

Phân công cá nhân được ghi tại commit `48b892f` (`TEAMMATE.md`). Các commit đưa corpus và mã thu thập vào repo đứng tên tài khoản của thành viên khác; tôi không nhận là tác giả của các commit hoặc các module code đó. Chuyển đổi Markdown, chunking, retrieval, fallback, UI và evaluation là phần việc của nhóm ở các bước sau.

## Quyết định kỹ thuật quan trọng

1. **Quyết định:** Dùng các trang công khai của trường và tài liệu chính sách có URL nguồn rõ ràng cho chủ đề học bổng đại học Việt Nam.
   **Lý do/evidence:** Hai danh mục `sources.csv` và `sources_urls.csv` ghi nguồn cho đủ 10 tài liệu; JSON bài viết giữ `url`, `title`, `date_crawled`, `content_markdown`. Nhờ đó có thể truy lại nguồn khi chatbot dẫn chứng.
   **Trade-off:** Các trang web có thể thay đổi sau ngày thu thập; bản dữ liệu trong repo cần được làm mới và đối chiếu lại định kỳ.

## Kiểm thử và kết quả

- Chạy `python -m pytest tests/test_acceptance.py -q`: 4 kiểm tra về số lượng và cấu trúc dữ liệu đạt; kiểm tra thứ năm chưa đạt vì báo cáo đánh giá nhóm `group_project/evaluation/RESULT.md` chưa hoàn thành, ngoài phạm vi thu thập dữ liệu.
- Bộ dữ liệu đầu vào hiện có 3 PDF chính sách và 7 JSON bài viết; quy trình của nhóm tạo ra 10 Markdown chuẩn hóa. Các JSON có đủ trường bắt buộc `url`, `title`, `date_crawled`, `content_markdown`.
- Kiểm tra nguồn cụ thể: văn bản UIT có `source_url` và mã `548/QĐ-ĐHCNTT`; trang học bổng VinUni giữ URL gốc và nội dung chính sách hỗ trợ 35% học phí.

## Điều còn hạn chế

- Một số trang crawl chứa nội dung điều hướng hoặc đoạn lặp, có thể làm loãng kết quả truy xuất sau khi chunk.
- Nếu tiếp tục cải thiện, tôi sẽ rà và loại đoạn lặp trong dữ liệu bài viết, sau đó chạy lại kiểm tra dữ liệu và đánh giá truy xuất.

## Xác nhận đóng góp

Tôi xác nhận nội dung trên phản ánh đúng phần việc mình phụ trách và có thể giải thích nguồn dữ liệu trong buổi demo.

- Ngày: 20/09/2026
- Tên thành viên: Đàm Quang Sơn
