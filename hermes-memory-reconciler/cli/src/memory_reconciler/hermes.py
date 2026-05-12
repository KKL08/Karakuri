from __future__ import annotations

import os
from pathlib import Path

from .models import MemoryFile


class MissingHermesProfile(Exception):
    pass


def resolve_hermes_home() -> Path:
    configured = os.environ.get("HERMES_HOME")
    if configured:
        return Path(configured).expanduser()
    return Path.home() / ".hermes"


def load_memory_files() -> tuple[Path, list[MemoryFile], list[str]]:
    hermes_home = resolve_hermes_home()
    if not hermes_home.exists():
        raise MissingHermesProfile(str(hermes_home))

    memories = hermes_home / "memories"
    if not memories.exists():
        raise MissingHermesProfile(str(memories))

    specs = [
        ("user", memories / "USER.md"),
        ("memory", memories / "MEMORY.md"),
    ]
    files: list[MemoryFile] = []
    missing: list[str] = []
    for target, path in specs:
        if path.exists():
            files.append(MemoryFile(target=target, path=path, exists=True, text=path.read_text(encoding="utf-8-sig")))
        else:
            missing.append(path.name)
            files.append(MemoryFile(target=target, path=path, exists=False, text=""))
    return hermes_home, files, missing
