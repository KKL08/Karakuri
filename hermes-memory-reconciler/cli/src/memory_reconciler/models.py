from __future__ import annotations

from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Literal


SCHEMA_VERSION = 1
Target = Literal["user", "memory"]


@dataclass(frozen=True)
class MemoryFile:
    target: Target
    path: Path
    exists: bool
    text: str = ""


@dataclass(frozen=True)
class MemoryEntry:
    entry_id: str
    target: Target
    source_path: str
    start_line: int
    end_line: int
    text: str
    normalized_text: str


@dataclass(frozen=True)
class Issue:
    issue_id: str
    category: str
    severity: str
    summary: str
    needs_user: bool
    topic: str
    entry_ids: list[str]
    entries: list[dict[str, Any]] = field(default_factory=list)


@dataclass(frozen=True)
class Choice:
    decision_id: str
    label: str
    content: str = ""


def dataclass_to_json(value: Any) -> Any:
    if isinstance(value, Path):
        return str(value)
    if hasattr(value, "__dataclass_fields__"):
        return asdict(value)
    if isinstance(value, list):
        return [dataclass_to_json(item) for item in value]
    if isinstance(value, dict):
        return {key: dataclass_to_json(item) for key, item in value.items()}
    return value
