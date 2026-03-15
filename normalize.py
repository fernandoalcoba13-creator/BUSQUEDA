import re
from urllib.parse import quote_plus

STOPWORDS = {"stl", "3d", "model", "modelo", "print", "printable"}


def normalize_text(text: str) -> str:
    text = (text or "").strip().lower()
    text = re.sub(r"\s+", " ", text)
    return text


def tokenize_query(query: str) -> list[str]:
    words = re.findall(r"[a-zA-Z0-9áéíóúñü]+", normalize_text(query))
    return [w for w in words if w not in STOPWORDS]


def build_query_variants(query: str) -> list[str]:
    base = normalize_text(query)
    tokens = tokenize_query(query)
    variants = [base]
    if tokens:
        joined = " ".join(tokens)
        if joined not in variants:
            variants.append(joined)
        if len(tokens) == 1:
            variants.append(f"{tokens[0]} stl")
            variants.append(f"{tokens[0]} 3d print")
        else:
            variants.append(f"{joined} stl")
    seen = set()
    ordered = []
    for item in variants:
        item = item.strip()
        if item and item not in seen:
            seen.add(item)
            ordered.append(item)
    return ordered


def normalize_title_for_dedupe(title: str) -> str:
    title = normalize_text(title)
    title = re.sub(r"[^a-z0-9áéíóúñü ]+", "", title)
    return title.strip()


def encode_q(query: str) -> str:
    return quote_plus(query.strip())
