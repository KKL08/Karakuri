from __future__ import annotations

from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class ParsedSkill:
    name: str | None
    description: str | None
    body: str
    body_lines: int
    body_token_estimate: int
    frontmatter_malformed: bool
    raw_frontmatter: dict[str, str] = field(default_factory=dict)
    description_status: str = "absent"
    description_raw: str | None = None
    frontmatter_notes: list[str] = field(default_factory=list)


@dataclass(frozen=True, kw_only=True)
class SkillRoot:
    root: Path
    source_type: str
    writable: bool
    managed: bool
    coverage: str = "complete"
    recursive: bool = False


@dataclass(frozen=True)
class DetectionResult:
    runtime_id: str
    detected: bool
    evidence: list[str]


def to_jsonable(value: Any) -> Any:
    if isinstance(value, Path):
        return str(value)
    if hasattr(value, "__dataclass_fields__"):
        return {key: to_jsonable(item) for key, item in asdict(value).items()}
    if isinstance(value, list):
        return [to_jsonable(item) for item in value]
    if isinstance(value, dict):
        return {key: to_jsonable(item) for key, item in value.items()}
    return value
