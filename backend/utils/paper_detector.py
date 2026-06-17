import re
from urllib.parse import urlparse

_PAPER_DOMAINS = [
    "arxiv.org",
    "scholar.google.com",
    "pubmed.ncbi.nlm.nih.gov",
    "semanticscholar.org",
    "researchgate.net",
    "acm.org",
    "ieee.org",
    "springer.com",
    "nature.com",
    "sciencedirect.com",
    "openreview.net",
    "aclanthology.org",
]


def detect_paper_site(url: str) -> bool:
    """논문/학술 사이트 여부 판단."""
    try:
        domain = urlparse(url).netloc.replace("www.", "")
    except Exception:
        return False
    return any(d in domain for d in _PAPER_DOMAINS)


def extract_arxiv_id(url: str) -> str | None:
    """arXiv URL에서 논문 ID 추출. https://arxiv.org/abs/2301.12345 → '2301.12345'"""
    match = re.search(r"arxiv\.org/(?:abs|pdf)/(\d+\.\d+)", url)
    return match.group(1) if match else None
