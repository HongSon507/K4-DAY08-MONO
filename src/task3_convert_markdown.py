"""
Task 3 — Chuẩn hóa dữ liệu sang Markdown.

- legal: PDF/DOCX trong landing/legal -> Markdown, metadata lấy từ sources.csv.
- news : JSON trong landing/news      -> Markdown, metadata lấy từ chính JSON.

Mỗi file output có YAML frontmatter để Task 4 dựng Document metadata mà không
phải đoán title/url.
"""

import csv
import json
import sys
from pathlib import Path


# Console Windows mac dinh cp1252 khong in duoc tieng Viet.
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")


LANDING_DIR = Path(__file__).parent.parent / "data" / "landing"
OUTPUT_DIR = Path(__file__).parent.parent / "data" / "standardized"

FRONTMATTER_FIELDS = (
    "doc_id",
    "title",
    "source_url",
    "retrieved_at",
    "document_version",
    "audience",
    "institution",
    "department",
    "category",
    "language",
)


def _frontmatter(values: dict) -> str:
    """Dựng khối YAML frontmatter, bỏ qua field rỗng."""
    lines = ["---"]
    for key in FRONTMATTER_FIELDS:
        value = str(values.get(key, "") or "").strip()
        if value:
            lines.append(f'{key}: "{value}"' if ":" in value else f"{key}: {value}")
    lines.append("---")
    return "\n".join(lines)


def _load_legal_sources() -> dict[str, dict]:
    """Đọc sources.csv, trả về mapping file_name -> metadata."""
    path = LANDING_DIR / "legal" / "sources.csv"
    if not path.exists():
        return {}
    with path.open(encoding="utf-8", newline="") as handle:
        return {row["file_name"]: row for row in csv.DictReader(handle)}


def convert_legal_docs() -> None:
    """Convert PDF/DOCX vào standardized/legal."""
    from markitdown import MarkItDown

    legal_dir = LANDING_DIR / "legal"
    output_dir = OUTPUT_DIR / "legal"
    output_dir.mkdir(parents=True, exist_ok=True)

    sources = _load_legal_sources()
    converter = MarkItDown()

    for path in sorted(legal_dir.iterdir()):
        if path.suffix.lower() not in {".pdf", ".doc", ".docx"}:
            continue
        try:
            text = (converter.convert(str(path)).text_content or "").strip()
        except Exception as error:
            print(f"Failed: {path.name} — {error}")
            continue

        if len(text) < 200:
            print(f"Skipped: {path.name} — chỉ trích được {len(text)} ký tự (PDF scan?)")
            continue

        meta = dict(sources.get(path.name, {}))
        meta.setdefault("doc_id", path.stem)
        meta.setdefault("title", path.stem)
        meta["source_url"] = meta.get("source_url", "")

        output = output_dir / f"{path.stem}.md"
        output.write_text(
            f"{_frontmatter(meta)}\n\n# {meta['title']}\n\n{text}\n",
            encoding="utf-8",
        )
        print(f"Saved: legal/{output.name} ({len(text)} chars)")


def convert_news_articles() -> None:
    """Convert JSON vào standardized/news."""
    news_dir = LANDING_DIR / "news"
    output_dir = OUTPUT_DIR / "news"
    output_dir.mkdir(parents=True, exist_ok=True)

    for path in sorted(news_dir.glob("*.json")):
        data = json.loads(path.read_text(encoding="utf-8"))
        content = str(data.get("content_markdown", "")).strip()
        if len(content) < 200:
            print(f"Skipped: {path.name} — content quá ngắn ({len(content)} ký tự)")
            continue

        meta = {
            "doc_id": data.get("doc_id", path.stem),
            "title": data.get("title", path.stem),
            "source_url": data.get("url", ""),
            "retrieved_at": data.get("date_crawled", ""),
            "audience": data.get("audience", ""),
            "institution": data.get("institution", ""),
            "department": data.get("department", ""),
            "category": data.get("category", ""),
            "language": data.get("language", "vi"),
        }

        output = output_dir / f"{meta['doc_id']}.md"
        output.write_text(
            f"{_frontmatter(meta)}\n\n# {meta['title']}\n\n{content}\n",
            encoding="utf-8",
        )
        print(f"Saved: news/{output.name} ({len(content)} chars)")


def convert_all() -> None:
    """Convert toàn bộ dữ liệu landing."""
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    convert_legal_docs()
    convert_news_articles()
    print(f"Saved Markdown to: {OUTPUT_DIR}")


if __name__ == "__main__":
    convert_all()
