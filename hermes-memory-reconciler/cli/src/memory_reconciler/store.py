from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any


class ArtifactNotFound(Exception):
    pass


def artifact_root() -> Path:
    configured = os.environ.get("MEMORY_RECONCILER_HOME")
    if configured:
        return Path(configured).expanduser()
    return Path.home() / ".memory-reconciler"


def artifact_dir(kind: str) -> Path:
    path = artifact_root() / kind
    path.mkdir(parents=True, exist_ok=True)
    return path


def write_artifact(kind: str, artifact_id: str, payload: dict[str, Any]) -> Path:
    path = artifact_dir(kind) / f"{artifact_id}.json"
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return path


def read_artifact(kind: str, artifact_id: str) -> dict[str, Any]:
    path = artifact_root() / kind / f"{artifact_id}.json"
    if not path.exists():
        raise ArtifactNotFound(f"{kind}/{artifact_id}")
    return json.loads(path.read_text(encoding="utf-8"))


def iter_artifacts(kind: str) -> list[dict[str, Any]]:
    path = artifact_root() / kind
    if not path.exists():
        return []
    results: list[dict[str, Any]] = []
    for item in sorted(path.glob("*.json")):
        results.append(json.loads(item.read_text(encoding="utf-8")))
    return results
