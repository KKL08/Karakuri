from __future__ import annotations

import re
from typing import Any


_SECRET_PATTERNS = [
    re.compile(r"sk-[A-Za-z0-9_-]{16,}"),
    re.compile(r"(?i)bearer\s+[A-Za-z0-9._~+/=-]{16,}"),
    re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----.*?-----END [A-Z ]*PRIVATE KEY-----", re.DOTALL),
    re.compile(r"\b[A-Za-z0-9_-]{32,}\b"),
]


def redact_secret_like_text(text: str) -> str:
    value = text
    for pattern in _SECRET_PATTERNS:
        value = pattern.sub("[REDACTED_SECRET]", value)
    return value


def redact_secret_like_values(value: Any) -> Any:
    if isinstance(value, str):
        return redact_secret_like_text(value)
    if isinstance(value, list):
        return [redact_secret_like_values(item) for item in value]
    if isinstance(value, dict):
        return {key: redact_secret_like_values(item) for key, item in value.items()}
    return value
