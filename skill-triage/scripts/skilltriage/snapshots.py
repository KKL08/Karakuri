from __future__ import annotations

import re
import shutil
from pathlib import Path


def _safe_path_part(value: str) -> str:
    safe = re.sub(r"[^A-Za-z0-9_.-]+", "-", value).strip("-")
    return safe or "skill"


def snapshot_skill(run_dir: Path, skill: dict[str, object]) -> dict[str, object]:
    source_path = Path(str(skill["skill_file"]))
    source_id = str(skill["source_id"])
    name = str(skill["name"])
    identity_suffix = str(skill.get("identity_suffix") or "")
    snapshot_name = name if not identity_suffix else f"{name}__{identity_suffix}"
    snapshot_dir = run_dir / "originals" / _safe_path_part(source_id) / _safe_path_part(snapshot_name)
    snapshot_dir.mkdir(parents=True, exist_ok=True)
    snapshot_path = snapshot_dir / source_path.name
    shutil.copy2(source_path, snapshot_path)
    snapshot_id_suffix = f"{source_id}-{snapshot_name}"
    return {
        "snapshot_id": f"snap-{_safe_path_part(snapshot_id_suffix)}",
        "skill_id": skill["skill_id"],
        "source_path": str(source_path),
        "source_hash": skill["hash"],
        "snapshot_path": str(snapshot_path.relative_to(run_dir)),
    }
