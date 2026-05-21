from __future__ import annotations

import os
from pathlib import Path


SKIP_DIRS = {".git", "node_modules", "dist", "build"}


def walk_skill_files(root: Path, recursive: bool) -> list[Path]:
    if not root.exists():
        return []
    if not recursive:
        return sorted(root.glob("*/SKILL.md"))

    found: list[Path] = []
    for current_root, dirnames, filenames in os.walk(root, followlinks=False):
        dirnames[:] = [dirname for dirname in dirnames if dirname not in SKIP_DIRS]
        if "SKILL.md" in filenames:
            found.append(Path(current_root) / "SKILL.md")
    return sorted(found)
