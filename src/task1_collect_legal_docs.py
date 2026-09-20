"""
Task 1 — Thu thập tài liệu chính sách/quy định.

Chủ đề nhóm: học bổng đại học Việt Nam.

Ba văn bản công khai, tất cả đều là PDF có text trích xuất được
(đã loại các bản scan và các file danh sách sinh viên chứa dữ liệu cá nhân):

    1. Nghị định 84/2020/NĐ-CP, Chương IV — học bổng khuyến khích học tập.
    2. Quy định HBKKHT của Trường ĐH Công nghệ Thông tin (ĐHQG-HCM).
    3. Quy định HBKKHT của Trường ĐH Luật TP.HCM.

Chạy:
    python -m src.task1_collect_legal_docs
"""

import csv
import sys
from pathlib import Path

import requests


# Console Windows mac dinh cp1252 khong in duoc tieng Viet.
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")


DATA_DIR = Path(__file__).parent.parent / "data" / "landing" / "legal"
SOURCES_CSV = DATA_DIR / "sources.csv"

MIN_BYTES = 1024
TIMEOUT = 60

SOURCES: list[dict] = [
    {
        "doc_id": "nghi-dinh-84-2020-nd-cp",
        "file_name": "nghi-dinh-84-2020-nd-cp-hoc-bong.pdf",
        "title": "Nghị định 84/2020/NĐ-CP — Chương IV: Học bổng khuyến khích học tập",
        "source_url": (
            "https://hvnh.edu.vn/medias/qlnh/vi/10.2021/system/archivedate/"
            "bb5ff579_Ngh%E1%BB%8B%20%C4%91%E1%BB%8Bnh%2084-%20HBKKHT%20m%E1%BB%9Bi%20n%C4%83m%202021.pdf"
        ),
        "document_version": "84/2020/NĐ-CP",
        "audience": "all",
        "institution": "chinh-phu",
        "category": "van-ban-phap-quy",
    },
    {
        "doc_id": "uit-548-qd-hbkkht",
        "file_name": "uit-548-qd-quy-dinh-hbkkht.pdf",
        "title": "Quy định học bổng khuyến khích học tập Trường Đại học Công nghệ Thông tin (ĐHQG-HCM)",
        "source_url": "https://ctsv.uit.edu.vn/sites/default/files/202109/548_qd-dhcntt-quy-dinh-hbkkht.pdf",
        "document_version": "548/QĐ-ĐHCNTT",
        "audience": "student",
        "institution": "uit",
        "category": "merit-scholarship",
    },
    {
        "doc_id": "hcmulaw-quy-dinh-hbkkht",
        "file_name": "hcmulaw-quy-dinh-hbkkht.pdf",
        "title": "Quy định về học bổng khuyến khích học tập cho sinh viên đại học Trường Đại học Luật TP.HCM",
        "source_url": (
            "https://pctsv.hcmulaw.edu.vn/Resources/Docs/SubDomain/pctsv/uoloadNewFolder/"
            "B%E1%BB%98%20C%C3%94NG%20C%E1%BB%A4%20C%E1%BB%90%20V%E1%BA%A4N%20H%E1%BB%8CC%20T%E1%BA%ACP/"
            "Quy%20%C4%91%E1%BB%8Bnh%20V%E1%BB%81%20h%E1%BB%8Dc%20b%E1%BB%95ng%20khuy%E1%BA%BFn%20"
            "kh%C3%ADch%20h%E1%BB%8Dc%20t%E1%BA%ADp%20cho%20sinh%20vi%C3%AAn.pdf"
        ),
        "document_version": "46/QĐ-ĐHL (2019-01-09)",
        "audience": "student",
        "institution": "hcmulaw",
        "category": "merit-scholarship",
    },
]

CSV_FIELDS = (
    "doc_id",
    "file_name",
    "title",
    "source_url",
    "retrieved_at",
    "document_version",
    "audience",
    "institution",
    "category",
    "language",
    "license_or_permission",
)


def setup_directory() -> None:
    """Tạo thư mục lưu tài liệu gốc."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    print(f"Ready: {DATA_DIR}")


def download_documents() -> None:
    """Tải ít nhất 3 PDF/DOCX từ nguồn công khai và ghi lại provenance."""
    from datetime import date

    setup_directory()
    rows: list[dict] = []
    downloads: list[tuple[Path, bytes]] = []
    failures: list[str] = []

    session = requests.Session()
    session.headers.update(
        {"User-Agent": "K4-L3A-RAG-Pipeline/1.0 (educational corpus collector)"}
    )

    for source in SOURCES:
        target = DATA_DIR / source["file_name"]
        try:
            response = session.get(source["source_url"], timeout=TIMEOUT)
            response.raise_for_status()
            content = response.content
        except Exception as error:
            print(f"Failed: {source['file_name']} — {error}")
            failures.append(source["file_name"])
            continue

        if not content.startswith(b"%PDF") or len(content) < MIN_BYTES:
            print(
                f"Failed: {source['file_name']} — không phải PDF hợp lệ "
                f"({len(content)} bytes)"
            )
            failures.append(source["file_name"])
            continue

        downloads.append((target, content))
        rows.append(
            {
                **{key: source.get(key, "") for key in CSV_FIELDS},
                "retrieved_at": date.today().isoformat(),
                "language": "vi",
                "license_or_permission": "public-source",
            }
        )
        print(f"Validated: {target.name} ({len(content)} bytes)")

    if failures:
        raise RuntimeError(
            "Không cập nhật corpus vì tải thất bại: " + ", ".join(failures)
        )

    # Chỉ thay corpus sau khi toàn bộ nguồn đã tải và validate thành công,
    # tránh trạng thái nửa cũ nửa mới khi mạng lỗi giữa chừng.
    for target, content in downloads:
        temp = target.with_suffix(f"{target.suffix}.tmp")
        temp.write_bytes(content)
        temp.replace(target)
        print(f"Saved: {target.name} ({len(content)} bytes)")

    csv_temp = SOURCES_CSV.with_suffix(".csv.tmp")
    with csv_temp.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=CSV_FIELDS)
        writer.writeheader()
        writer.writerows(rows)
    csv_temp.replace(SOURCES_CSV)
    print(f"Provenance: {SOURCES_CSV.name} ({len(rows)} dòng)")

    print(f"\n{len(rows)}/{len(SOURCES)} tài liệu đã tải")


if __name__ == "__main__":
    download_documents()
