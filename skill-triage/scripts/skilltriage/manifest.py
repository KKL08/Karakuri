from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path


REQUIRED_PROPOSAL_FIELDS = {
    "proposal_id",
    "skill_id",
    "action",
    "status",
    "source_path",
    "source_hash",
    "proposal_path",
}


def add_proposal(manifest_path: Path, proposal: dict[str, object]) -> None:
    missing = sorted(REQUIRED_PROPOSAL_FIELDS - set(proposal))
    if missing:
        raise ValueError(f"Proposal is missing required fields: {', '.join(missing)}")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    proposals = manifest.setdefault("proposals", [])
    proposals.append(proposal)
    manifest_path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def update_execution_status(
    manifest_path: Path,
    *,
    status: str,
    execution_status: str,
    action_ids: list[str],
) -> None:
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["status"] = status
    execution = manifest.setdefault("execution", {})
    execution["status"] = execution_status
    execution["action_ids"] = action_ids
    execution["updated_at"] = datetime.now().astimezone().isoformat()
    manifest_path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
