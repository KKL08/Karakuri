from __future__ import annotations

from pathlib import Path

from .claude_code import ClaudeCodeAdapter
from .codex import CodexAdapter


ADAPTERS = {
    "codex": CodexAdapter,
    "claude-code": ClaudeCodeAdapter,
}


def choose_adapter(runtime: str | None, project_dir: Path):
    if runtime:
        adapter_cls = ADAPTERS.get(runtime)
        if adapter_cls is None:
            return None, f"Unsupported runtime: {runtime}. Use codex or claude-code."
        return adapter_cls(project_dir), ""

    detected = []
    for adapter_cls in ADAPTERS.values():
        adapter = adapter_cls(project_dir)
        result = adapter.detect()
        if result.detected:
            detected.append(adapter)

    if len(detected) == 1:
        return detected[0], ""

    return (
        None,
        "无法明确判断当前运行环境。请重新运行并传入 --runtime codex 或 --runtime claude-code。",
    )
