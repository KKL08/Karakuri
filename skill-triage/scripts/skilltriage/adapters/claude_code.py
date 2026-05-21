from __future__ import annotations

import os
from pathlib import Path

from skilltriage.models import DetectionResult, SkillRoot

from .base import RuntimeAdapter


class ClaudeCodeAdapter(RuntimeAdapter):
    runtime_id = "claude-code"

    def detect(self) -> DetectionResult:
        evidence = sorted(
            key for key in ("CLAUDECODE", "CLAUDE_CODE", "CLAUDE_PROJECT_DIR") if os.environ.get(key)
        )
        return DetectionResult(self.runtime_id, bool(evidence), evidence)

    def skill_roots(self) -> list[SkillRoot]:
        self.coverage_notes = []
        roots = [
            SkillRoot(root=self.home / ".claude" / "skills", source_type="user", writable=True, managed=False),
            SkillRoot(root=self.project_dir / ".claude" / "skills", source_type="project", writable=True, managed=False),
        ]
        plugin_root = self.home / ".claude" / "plugins"
        if plugin_root.exists():
            roots.append(
                SkillRoot(
                    root=plugin_root,
                    source_type="plugin-managed",
                    writable=False,
                    managed=True,
                    coverage="best-effort",
                    recursive=True,
                )
            )
        else:
            self.coverage_notes.append("未能可靠定位 Claude Code plugin-managed skill 来源；插件覆盖范围已标记为不完整。")
        return roots

    def classify_source(self, path: Path) -> dict[str, object]:
        text = str(path)
        if "/.claude/plugins/" in text:
            return {"source_type": "plugin-managed", "writable": False, "managed": True}
        if f"{self.project_dir}/.claude/skills/" in text:
            return {"source_type": "project", "writable": True, "managed": False}
        if "/.claude/skills/" in text:
            return {"source_type": "user", "writable": True, "managed": False}
        return {"source_type": "unknown", "writable": False, "managed": False}
