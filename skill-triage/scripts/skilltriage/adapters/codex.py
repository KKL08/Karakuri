from __future__ import annotations

import os
from pathlib import Path

from skilltriage.models import DetectionResult, SkillRoot

from .base import RuntimeAdapter


class CodexAdapter(RuntimeAdapter):
    runtime_id = "codex"

    def detect(self) -> DetectionResult:
        evidence = [key for key in ("CODEX_HOME", "CODEX_SANDBOX", "CODEX_ENV_PWD", "CODEX_CLI") if os.environ.get(key)]
        return DetectionResult(self.runtime_id, bool(evidence), evidence)

    def skill_roots(self) -> list[SkillRoot]:
        self.coverage_notes = []
        roots = [
            SkillRoot(root=self.home / ".codex" / "skills", source_type="user", writable=True, managed=False),
            SkillRoot(root=self.home / ".agents" / "skills", source_type="shared", writable=True, managed=False),
        ]
        plugin_root = self.home / ".codex" / "plugins" / "cache"
        if not plugin_root.exists():
            self.coverage_notes.append("未能可靠定位 Codex plugin-managed skill 来源；插件覆盖范围已标记为不完整。")
        roots.append(
            SkillRoot(
                root=plugin_root,
                source_type="plugin-managed",
                writable=False,
                managed=True,
                coverage="best-effort" if plugin_root.exists() else "missing",
                recursive=True,
            )
        )
        return roots

    def classify_source(self, path: Path) -> dict[str, object]:
        text = str(path)
        if "/.codex/plugins/cache/" in text:
            return {"source_type": "plugin-managed", "writable": False, "managed": True}
        if "/.agents/skills/" in text:
            return {"source_type": "shared", "writable": True, "managed": False}
        if "/.codex/skills/" in text:
            return {"source_type": "user", "writable": True, "managed": False}
        return {"source_type": "unknown", "writable": False, "managed": False}
