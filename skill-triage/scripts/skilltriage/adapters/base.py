from __future__ import annotations

from pathlib import Path

from skilltriage.frontmatter import parse_skill_markdown
from skilltriage.models import DetectionResult, SkillRoot


class RuntimeAdapter:
    runtime_id = "base"

    def __init__(self, project_dir: Path, home: Path | None = None) -> None:
        self.project_dir = project_dir
        self.home = home or Path.home()
        self.coverage_notes: list[str] = []

    def detect(self) -> DetectionResult:
        return DetectionResult(self.runtime_id, False, [])

    def skill_roots(self) -> list[SkillRoot]:
        return []

    def classify_source(self, path: Path) -> dict[str, object]:
        return {"source_type": "unknown", "writable": False, "managed": False}

    def active_state(self, path: Path) -> str:
        return "unknown"

    def is_self_skill(self, path: Path) -> bool:
        if path.name != "SKILL.md":
            return False
        try:
            parsed = parse_skill_markdown(path.read_text(encoding="utf-8", errors="replace"))
        except OSError:
            return False
        return parsed.name == "skill-triage"

    def default_output_dir(self) -> Path:
        return self.home / ".skilltriage" / "runs" / self.runtime_id
