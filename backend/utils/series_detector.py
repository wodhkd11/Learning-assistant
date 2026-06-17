import re
from urllib.parse import urlparse


def extract_book_title(document_title: str | None) -> str | None:
    """
    브라우저 탭 제목에서 책/시리즈 제목 추출.
    " - " 구분자로 분리하여 마지막 부분 반환.
    예: "02. 입문 - Just Do Rust" → "Just Do Rust"
    " - "가 없으면 None 반환.
    """
    if not document_title or " - " not in document_title:
        return None
    return document_title.split(" - ")[-1].strip()


def make_series_slug(book_title: str, url: str) -> str:
    """
    책 제목 + URL 도메인으로 고유 슬러그 생성.
    예: "Just Do Rust" + "wikidocs.net" → "just-do-rust-wikidocs"
    """
    slug = book_title.lower()
    slug = re.sub(r"[^\w\s-]", "", slug)
    slug = re.sub(r"\s+", "-", slug).strip("-")

    try:
        domain = urlparse(url).netloc.replace("www.", "")
        domain_short = domain.split(".")[0]
    except Exception:
        domain_short = "web"

    return f"{slug}-{domain_short}"
