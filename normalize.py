import re
from urllib.parse import quote_plus


def normalize_text(text: str) -> str:
    if not text:
        return ""
    text = text.lower().strip()
    text = re.sub(r"\s+", " ", text)
    return text


def normalize_query(query: str) -> str:
    return normalize_text(query)


def normalize_title_for_dedupe(title: str) -> str:
    if not title:
        return ""
    title = normalize_text(title)
    title = re.sub(r"[^a-z0-9\s]", "", title)
    title = re.sub(r"\s+", " ", title).strip()
    return title


def build_query_variants(query: str):
    q = normalize_query(query)

    variants = [q]

    if "stl" not in q:
        variants.append(f"{q} stl")

    if "3d" not in q:
        variants.append(f"{q} 3d")

    # deduplicar conservando orden
    seen = set()
    clean = []
    for v in variants:
        if v and v not in seen:
            seen.add(v)
            clean.append(v)

    return clean


def encode_q(query: str) -> str:
    return quote_plus(query or "")
