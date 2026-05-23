from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

from .constants import RUN_STATUS_PROPOSED
from .snapshots import snapshot_skill


def _write_json(path: Path, data: dict[str, object]) -> None:
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def _needs_snapshot(skill: dict[str, object], backup_policy: str, agent_eval_ids: set[str]) -> bool:
    if backup_policy == "off":
        return False
    if not bool(skill.get("writable")) or bool(skill.get("managed")):
        return False
    if backup_policy == "full":
        return True
    return str(skill.get("skill_id")) in agent_eval_ids


def _unique_skill_ids(skills: list[dict[str, object]]) -> list[str]:
    ids = {str(skill["skill_id"]) for skill in skills if skill.get("candidate_for_agent_evaluation")}
    return sorted(ids)


def write_run_artifacts(
    *,
    run_dir: Path,
    runtime: str,
    run_id: str,
    backup_policy: str,
    skill_roots: list[dict[str, object]],
    skills: list[dict[str, object]],
    checks: dict[str, object],
    similarity_candidates: list[dict[str, object]],
    coverage_notes: list[str],
    evaluation_scope: str,
    selected_skills: list[str],
    agent_evaluation_skill_ids: list[str],
    capability_groups: list[dict[str, object]],
    preference_hints: list[dict[str, object]],
) -> None:
    run_dir.mkdir(parents=True, exist_ok=False)
    for dirname in ("originals", "proposals", "diffs", "decisions"):
        (run_dir / dirname).mkdir()

    agent_eval_id_set = set(agent_evaluation_skill_ids)
    snapshots = [snapshot_skill(run_dir, skill) for skill in skills if _needs_snapshot(skill, backup_policy, agent_eval_id_set)]

    inventory = {
        "run_id": run_id,
        "runtime": runtime,
        "scope": "current-agent",
        "skill_roots": [root["root"] for root in skill_roots],
        "coverage_notes": coverage_notes,
        "skills": skills,
    }
    basic_screening = {
        "run_id": run_id,
        "runtime": runtime,
        "checks": checks,
        "similarity_candidates": similarity_candidates,
        "capability_groups": capability_groups,
        "candidate_skill_ids": _unique_skill_ids(skills),
        "evaluation_scope": evaluation_scope,
        "selected_skills": selected_skills,
        "agent_evaluation_skill_ids": agent_evaluation_skill_ids,
        "preference_hints": preference_hints,
    }
    manifest = {
        "run_id": run_id,
        "runtime": runtime,
        "scope": "current-agent",
        "created_at": datetime.now().astimezone().isoformat(),
        "status": RUN_STATUS_PROPOSED,
        "backup_policy": backup_policy,
        "output_dir": str(run_dir),
        "sources": skill_roots,
        "skills": [
            {
                "skill_id": skill["skill_id"],
                "source_id": skill.get("source_id", f"{runtime}-{skill['source_type']}"),
                "name": skill["name"],
                "skill_file": skill["skill_file"],
                "hash": skill["hash"],
                "is_self": skill["is_self"],
                "active_state": skill["active_state"],
            }
            for skill in skills
        ],
        "snapshots": snapshots,
        "proposals": [],
        "preference_hints": preference_hints,
    }
    _write_json(run_dir / "inventory.json", inventory)
    _write_json(run_dir / "basic_screening.json", basic_screening)
    _write_json(run_dir / "manifest.json", manifest)
