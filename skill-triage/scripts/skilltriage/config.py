from __future__ import annotations

import json
from pathlib import Path


def config_path(home: Path | None = None) -> Path:
    return (home or Path.home()) / ".skilltriage" / "config.json"


def load_backup_policy(runtime: str, home: Path | None = None) -> str | None:
    path = config_path(home)
    if not path.exists():
        return None
    data = json.loads(path.read_text(encoding="utf-8"))
    return data.get("backup_policy", {}).get(runtime)


def save_backup_policy(runtime: str, policy: str, home: Path | None = None) -> None:
    path = config_path(home)
    path.parent.mkdir(parents=True, exist_ok=True)
    data = json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}
    backup_policy = data.setdefault("backup_policy", {})
    backup_policy[runtime] = policy
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
