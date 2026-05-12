from __future__ import annotations

import hashlib
import re
from datetime import datetime
from secrets import token_hex


def new_id(prefix: str) -> str:
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    return f"{prefix}_{stamp}_{token_hex(3)}"


def stable_suffix(*parts: object, length: int = 10) -> str:
    digest = hashlib.sha1("|".join(str(part) for part in parts).encode("utf-8")).hexdigest()
    return digest[:length]


def slug(text: str, fallback: str = "item") -> str:
    value = re.sub(r"[^a-z0-9]+", "_", text.lower()).strip("_")
    return value or fallback
