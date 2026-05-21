from __future__ import annotations

import hashlib
import re
from pathlib import Path


MAX_SUFFIX_LENGTH = 96


def _slug(value: str) -> str:
    normalized = value.replace("\\", "/").strip("/")
    slug = re.sub(r"[^A-Za-z0-9_.-]+", "-", normalized)
    slug = re.sub(r"-+", "-", slug).strip("-").lower()
    return slug or "skill"


def skill_identity_suffix(skill: dict[str, object]) -> str:
    source_root = Path(str(skill.get("source_root") or ""))
    skill_dir = Path(str(skill.get("skill_dir") or ""))
    try:
        identity_path = skill_dir.relative_to(source_root)
    except ValueError:
        identity_path = skill_dir

    raw_path = str(identity_path)
    digest = hashlib.sha256(str(skill_dir).encode("utf-8")).hexdigest()[:8]
    base = _slug(raw_path)
    max_base = MAX_SUFFIX_LENGTH - len(digest) - 1
    if len(base) > max_base:
        base = base[:max_base].rstrip("-")
    return f"{base}-{digest}"


def deduplicate_skill_ids(skills: list[dict[str, object]]) -> int:
    by_id: dict[str, list[dict[str, object]]] = {}
    for skill in skills:
        by_id.setdefault(str(skill["skill_id"]), []).append(skill)

    changed = 0
    for original_id, group in by_id.items():
        if len(group) < 2:
            continue
        for skill in group:
            suffix = skill_identity_suffix(skill)
            skill["skill_id_base"] = original_id
            skill["identity_suffix"] = suffix
            skill["skill_id"] = f"{original_id}#{suffix}"
            changed += 1
    return changed
