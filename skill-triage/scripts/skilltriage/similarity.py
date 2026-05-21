from __future__ import annotations

import re

from .constants import SIMILARITY_THRESHOLD


TOKEN_RE = re.compile(r"[A-Za-z0-9_\-一-鿿]+")
STOPWORDS = {
    "a",
    "an",
    "and",
    "for",
    "in",
    "of",
    "on",
    "or",
    "skill",
    "the",
    "this",
    "to",
    "use",
    "when",
    "with",
}


def tokenize(text: str | None) -> set[str]:
    if not text:
        return set()
    tokens = {token.lower().replace("_", "-") for token in TOKEN_RE.findall(text)}
    return {token for token in tokens if token not in STOPWORDS}


def jaccard(left: str | None, right: str | None) -> float:
    left_tokens = tokenize(left)
    right_tokens = tokenize(right)
    if not left_tokens or not right_tokens:
        return 0.0
    return len(left_tokens & right_tokens) / len(left_tokens | right_tokens)


def is_similar(left: str | None, right: str | None) -> bool:
    return jaccard(left, right) >= SIMILARITY_THRESHOLD
