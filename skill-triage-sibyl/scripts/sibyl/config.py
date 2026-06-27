from __future__ import annotations

import json
import os
from pathlib import Path

PLUGIN_NAME = "skill-triage-sibyl"


def plugin_data_dir() -> Path:
    """Resolve the per-plugin data directory.

    Prefers $CLAUDE_PLUGIN_DATA when set so plugin-managed installs land in the
    location Claude Code expects. Falls back to ~/.claude/plugin-data/<name>/
    for the standalone use case (skill installed without a plugin wrapper).
    """
    base = os.environ.get("CLAUDE_PLUGIN_DATA")
    root = Path(base) if base else Path.home() / ".claude" / "plugin-data" / PLUGIN_NAME
    root.mkdir(parents=True, exist_ok=True)
    return root


def _config_path() -> Path:
    return plugin_data_dir() / "config.json"


def load_config() -> dict:
    path = _config_path()
    if not path.exists():
        return {
            "version": 1,
            "review_mode": None,
            "schedule": None,
            "onboarding_completed_at": None,
        }
    return json.loads(path.read_text(encoding="utf-8"))


def save_config(cfg: dict) -> None:
    path = _config_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(cfg, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def is_first_run() -> bool:
    return load_config().get("onboarding_completed_at") is None
