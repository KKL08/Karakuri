from __future__ import annotations

import re
import string
from pathlib import Path

from .ids import stable_suffix
from .models import MemoryEntry, Target


_BULLET_RE = re.compile(r"^\s*(?:[-*+]|\d+[.)])\s+(?P<body>.+?)\s*$")
_HEADING_RE = re.compile(r"^\s{0,3}#{1,6}\s+")


def normalize_memory_text(text: str) -> str:
    value = text.strip().lower()
    value = value.translate(str.maketrans("", "", string.punctuation))
    value = re.sub(r"\s+", " ", value)
    return value.strip()


def _make_entry(target: Target, path: Path, start: int, end: int, text: str) -> MemoryEntry:
    normalized = normalize_memory_text(text)
    suffix = stable_suffix(target, start, end, normalized)
    return MemoryEntry(
        entry_id=f"entry_{target}_{start}_{suffix}",
        target=target,
        source_path=str(path),
        start_line=start,
        end_line=end,
        text=text.strip(),
        normalized_text=normalized,
    )


def parse_memory_entries(target: Target, path: Path, text: str) -> list[MemoryEntry]:
    entries: list[MemoryEntry] = []
    paragraph: list[str] = []
    paragraph_start = 0

    def flush_paragraph(end_line: int) -> None:
        nonlocal paragraph, paragraph_start
        if paragraph:
            body = " ".join(part.strip() for part in paragraph).strip()
            if body:
                entries.append(_make_entry(target, path, paragraph_start, end_line, body))
        paragraph = []
        paragraph_start = 0

    lines = text.splitlines()
    for index, line in enumerate(lines, start=1):
        stripped = line.strip()
        if not stripped:
            flush_paragraph(index - 1)
            continue
        if _HEADING_RE.match(line):
            flush_paragraph(index - 1)
            continue
        bullet = _BULLET_RE.match(line)
        if bullet:
            flush_paragraph(index - 1)
            entries.append(_make_entry(target, path, index, index, bullet.group("body")))
            continue
        if not paragraph:
            paragraph_start = index
        paragraph.append(stripped)

    flush_paragraph(len(lines))
    return entries
