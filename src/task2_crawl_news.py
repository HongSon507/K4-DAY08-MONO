"""
Task 2 — Crawl bài viết/thông báo về học bổng đại học.

7 URL công khai được kế thừa từ lab Day 7 (K4-L3A-Data-Foundations),
provenance gốc nằm ở data/sources_urls.csv.

Cài browser trước khi chạy:
    python -m playwright install chromium
"""

import asyncio
import json
import re
import sys
from datetime import datetime
from pathlib import Path


# Console Windows mac dinh cp1252 khong in duoc tieng Viet.
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")


DATA_DIR = Path(__file__).parent.parent / "data" / "landing" / "news"

# Dưới ngưỡng này coi như bộ lọc đã cắt nhầm hết nội dung.
MIN_CONTENT_CHARS = 500
MIN_ARTICLES = 5

# Thử hai vùng semantic phổ biến trước khi fallback về toàn trang.
# Mỗi lần crawl chỉ dùng một selector: nếu truyền nhiều selector
# lồng nhau cho target_elements, Crawl4AI sẽ ghép cùng nội dung nhiều lần.
CONTENT_SELECTORS = (
    "main",
    "article",
)

EXCLUDED_SELECTOR = ", ".join(
    (
        ".breadcrumb",
        ".breadcrumbs",
        ".related-posts",
        ".post-related",
        ".sidebar",
        ".social-share",
    )
)

# doc_id giữ nguyên từ Day 7 để ID ổn định xuyên suốt pipeline.
ARTICLES: list[dict] = [
    {
        "doc_id": "undergraduate-scholarships",
        "url": "https://admissions.vinuni.edu.vn/scholarship-and-financial-aid/undergraduate-programs/scholarships/",
        "audience": "student",
        "institution": "vinuni",
        "department": "admissions",
        "category": "merit-scholarship",
    },
    {
        "doc_id": "scholarship-renewal-policy",
        "url": "https://policy.vinuni.edu.vn/all-policies/criteria-to-maintain-the-entry-scholarship-and-financial-aid-support/",
        "audience": "student",
        "institution": "vinuni",
        "department": "student-affairs",
        "category": "renewal-policy",
    },
    {
        "doc_id": "ueh-learning-support-scholarship",
        "url": "https://dsa.ueh.edu.vn/chuyen-trang-chinh-sach-ho-tro-tai-chinh/hoc-bong/",
        "audience": "student",
        "institution": "ueh",
        "department": "student-affairs",
        "category": "need-based-scholarship",
    },
    {
        "doc_id": "ueh-faculty-support",
        "url": "https://ueh.edu.vn/college/cob/vi/ueh-ban-hanh-chinh-sach-dai-ngo-dot-pha-chieu-mo-giu-chan-nhan-tai-kien-tao-vi-the-quoc-te-76541",
        "audience": "faculty",
        "institution": "ueh",
        "department": "human-resources",
        "category": "faculty-funding",
        "stop_pattern": r"^\*\*Cơ quan báo chí đưa tin:\*\*",
    },
    {
        "doc_id": "uet-merit-scholarship-2025-2026",
        "url": "https://uet.edu.vn/cap-hoc-bong-khuyen-khich-hoc-tap-trong-hoc-ky-i-nam-hoc-2025-2026-cho-sinh-vien/",
        "audience": "student",
        "institution": "uet",
        "department": "student-affairs",
        "category": "merit-scholarship",
        "stop_pattern": r"^#####\s+\[",
    },
    {
        "doc_id": "rmit-business-scholarship-2026",
        "url": "https://www.rmit.edu.vn/study-at-rmit/scholarships/future-undergraduate-student-scholarships/bachelor-of-business-scholarship",
        "audience": "student",
        "institution": "rmit-vietnam",
        "department": "scholarship-office",
        "category": "merit-scholarship",
        "start_pattern": r"^## Bachelor of Business Scholarship\s*$",
        "stop_pattern": r"^\s*\* Copyright ©",
    },
    {
        "doc_id": "rmit-current-student-scholarship-2026",
        "url": "https://www.rmit.edu.vn/study-at-rmit/scholarships/current-student-scholarships",
        "audience": "student",
        "institution": "rmit-vietnam",
        "department": "scholarship-office",
        "category": "current-student-scholarship",
        "start_pattern": r"^## Academic Achievement Scholarship for Current Students\s*$",
        "stop_pattern": r"^\s*\* Copyright ©",
    },
]

ARTICLE_URLS = [article["url"] for article in ARTICLES]


def _build_configs():
    """Hai cấu hình theo thứ tự ưu tiên: khoanh vùng nội dung, rồi chỉ lọc rác.

    target_elements cho kết quả sạch nhất nhưng rỗng trên site không dùng
    <main>/<article> (ví dụ rmit.edu.vn), nên cần bậc fallback.
    """
    from crawl4ai import CrawlerRunConfig
    from crawl4ai.content_filter_strategy import PruningContentFilter
    from crawl4ai.markdown_generation_strategy import DefaultMarkdownGenerator

    excluded = ["nav", "footer", "header", "aside", "form", "script", "style"]

    def generator():
        return DefaultMarkdownGenerator(
            content_filter=PruningContentFilter(threshold=0.5, threshold_type="dynamic")
        )

    scoped = [
        CrawlerRunConfig(
            markdown_generator=generator(),
            target_elements=[selector],
            excluded_tags=excluded,
            excluded_selector=EXCLUDED_SELECTOR,
        )
        for selector in CONTENT_SELECTORS
    ]
    scoped.append(
        CrawlerRunConfig(
            markdown_generator=generator(),
            excluded_tags=excluded,
            excluded_selector=EXCLUDED_SELECTOR,
        )
    )
    return scoped


def _normalize_markdown(markdown: str) -> str:
    """Chuẩn hóa khoảng trắng mà không làm thay đổi nội dung."""
    markdown = markdown.replace("\r\n", "\n").replace("\r", "\n")
    markdown = re.sub(r"[ \t]+\n", "\n", markdown)
    markdown = re.sub(r"\n{3,}", "\n\n", markdown)
    return markdown.strip()


def _trim_source_boilerplate(markdown: str, url: str) -> str:
    """Cắt menu/footer theo ranh giới ổn định của từng nguồn."""
    source = next((item for item in ARTICLES if item["url"] == url), {})
    trimmed = markdown

    start_pattern = source.get("start_pattern")
    if start_pattern:
        match = re.search(start_pattern, trimmed, flags=re.MULTILINE)
        if match:
            trimmed = trimmed[match.start() :]

    stop_pattern = source.get("stop_pattern")
    if stop_pattern:
        match = re.search(stop_pattern, trimmed, flags=re.MULTILINE)
        if match:
            trimmed = trimmed[: match.start()]

    trimmed = trimmed.strip()
    return trimmed if len(trimmed) >= MIN_CONTENT_CHARS else markdown


async def crawl_article(url: str) -> dict:
    """Crawl một URL và trả về payload theo contract của Task 2.

    Thử lần lượt: nội dung đã khoanh vùng -> chỉ lọc rác -> markdown thô.
    Trang học bổng thường có menu và footer dài hơn cả nội dung, để nguyên
    sẽ làm hỏng context precision khi retrieve.
    """
    from crawl4ai import AsyncWebCrawler

    last_error = "no config produced content"

    async with AsyncWebCrawler() as crawler:
        for config in _build_configs():
            try:
                result = await crawler.arun(url=url, config=config)
            except Exception as error:
                last_error = str(error)
                continue

            if not result.success:
                last_error = result.error_message or "crawl failed"
                # Không thử liên tiếp nhiều selector khi website đã chặn;
                # việc đó chỉ tạo thêm request và không thể cải thiện nội dung.
                if "anti-bot" in last_error.lower() or "cloudflare" in last_error.lower():
                    break
                continue

            markdown = _normalize_markdown(
                str(getattr(result.markdown, "fit_markdown", "") or "")
            )
            if len(markdown) < MIN_CONTENT_CHARS:
                markdown = _normalize_markdown(
                    str(getattr(result.markdown, "raw_markdown", "") or "")
                )
            if len(markdown) < MIN_CONTENT_CHARS:
                last_error = f"nội dung quá ngắn ({len(markdown)} ký tự)"
                continue

            markdown = _trim_source_boilerplate(markdown, url)

            metadata = result.metadata or {}
            return {
                "url": url,
                "title": (metadata.get("title") or url).strip(),
                "date_crawled": datetime.now()
                .astimezone()
                .isoformat(timespec="seconds"),
                "content_markdown": markdown,
            }

    raise RuntimeError(last_error)


async def crawl_all() -> None:
    """Crawl và lưu từng bài thành một file JSON đặt tên theo doc_id."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)

    saved = 0
    for article in ARTICLES:
        try:
            payload = await crawl_article(article["url"])
        except Exception as error:
            print(f"Failed: {article['url']} — {error}")
            continue

        payload.update(
            {
                "doc_id": article["doc_id"],
                "audience": article["audience"],
                "institution": article["institution"],
                "department": article["department"],
                "category": article["category"],
                "language": "vi",
            }
        )
        output = DATA_DIR / f"{article['doc_id']}.json"
        output.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        saved += 1
        print(f"Saved: {output.name} ({len(payload['content_markdown'])} chars)")

    print(f"\n{saved}/{len(ARTICLES)} bài đã lưu vào {DATA_DIR}")
    if saved < MIN_ARTICLES:
        raise RuntimeError(
            f"Corpus chỉ crawl được {saved} bài; yêu cầu tối thiểu {MIN_ARTICLES}"
        )


if __name__ == "__main__":
    asyncio.run(crawl_all())
