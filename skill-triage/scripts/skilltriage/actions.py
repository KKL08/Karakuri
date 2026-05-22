from __future__ import annotations

import hashlib
import json
import os
import shutil
from datetime import datetime
from pathlib import Path
from typing import Any

from .constants import (
    ACTION_TYPE_ARCHIVE_SKILL,
    ACTION_TYPE_REPLACE_SKILL_FILE,
    RUN_STATUS_APPLIED,
    RUN_STATUS_PARTIALLY_APPLIED,
    RUN_STATUS_PARTIALLY_ROLLED_BACK,
    RUN_STATUS_ROLLED_BACK,
    RUN_STATUS_STAGED,
    SUPPORTED_EXECUTION_ACTION_TYPES,
)
from .manifest import update_execution_status
from .snapshots import _safe_path_part


class ActionError(RuntimeError):
    """Raised when an execution action cannot be safely completed."""


ACTION_BINDING_EXCLUDED_FIELDS = {
    "applied_at",
    "reason",
    "rolled_back_at",
    "status",
    "validated_at",
}
BASE_ACTION_BINDING_FIELDS = ("action_id", "type", "skill_id", "source_path", "source_hash")
ARCHIVE_ACTION_BINDING_FIELDS = BASE_ACTION_BINDING_FIELDS + ("backup_path", "archive_path")
REPLACE_ACTION_BINDING_FIELDS = BASE_ACTION_BINDING_FIELDS + (
    "backup_path",
    "proposal_path",
    "proposal_hash",
    "proposed_backup_path",
)


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def _now() -> str:
    return datetime.now().astimezone().isoformat()


def _hash_file(path: Path) -> str:
    return "sha256:" + hashlib.sha256(path.read_bytes()).hexdigest()


def _lexical_absolute_path(value: object, field_name: str) -> Path:
    path = Path(str(value)).expanduser()
    if not path.is_absolute():
        raise ActionError(f"{field_name} must be absolute")
    return Path(os.path.abspath(os.fspath(path)))


def _lexical_run_dir(run_dir: Path) -> Path:
    return Path(os.path.abspath(os.fspath(Path(run_dir).expanduser())))


def _validate_run_path_components(run_dir: Path, absolute_path: Path, field_name: str) -> None:
    base = _lexical_run_dir(run_dir)
    try:
        relative_path = absolute_path.relative_to(base)
    except ValueError as exc:
        raise ActionError(f"{field_name} escapes run_dir") from exc

    current = base
    parts = relative_path.parts
    for index, part in enumerate(parts):
        current = current / part
        if current.is_symlink():
            raise ActionError(f"{field_name} contains symlinked execution path component: {current}")
        if index < len(parts) - 1 and current.exists() and not current.is_dir():
            raise ActionError(f"{field_name} contains non-directory execution path component: {current}")

    try:
        resolved_base = base.resolve(strict=True)
    except FileNotFoundError as exc:
        raise ActionError(f"run_dir does not exist: {base}") from exc

    resolved_path = absolute_path.resolve(strict=False)
    try:
        resolved_path.relative_to(resolved_base)
    except ValueError as exc:
        raise ActionError(f"{field_name} resolves outside run_dir") from exc


def _run_relative_path(
    run_dir: Path,
    value: object,
    field_name: str,
    *,
    expected_parts: tuple[str, ...] | None = None,
) -> Path:
    path = Path(str(value))
    if path.is_absolute():
        raise ActionError(f"{field_name} must be relative to run_dir")
    if ".." in path.parts:
        raise ActionError(f"{field_name} must not contain '..'")

    base = _lexical_run_dir(run_dir)
    absolute_path = Path(os.path.abspath(os.fspath(base / path)))
    try:
        absolute_path.relative_to(base)
    except ValueError as exc:
        raise ActionError(f"{field_name} escapes run_dir") from exc

    if expected_parts is not None:
        expected_base = Path(os.path.abspath(os.fspath(base.joinpath(*expected_parts))))
        try:
            absolute_path.relative_to(expected_base)
        except ValueError as exc:
            expected = "/".join(expected_parts)
            raise ActionError(f"{field_name} must be under {expected}") from exc
    _validate_run_path_components(run_dir, absolute_path, field_name)
    return absolute_path


def _execution_dir(run_dir: Path) -> Path:
    execution_dir = _run_relative_path(
        run_dir,
        "execution",
        "execution_dir",
        expected_parts=("execution",),
    )
    if execution_dir.exists() and not execution_dir.is_dir():
        raise ActionError(f"execution_dir is not a directory: {execution_dir}")
    return execution_dir


def _write_execution_status(
    run_dir: Path,
    manifest_path: Path,
    manifest: dict[str, Any],
    *,
    status: str,
    execution_status: str,
    action_ids: list[str],
    details: dict[str, Any] | None = None,
) -> None:
    status_data: dict[str, Any] = {
        "run_id": manifest.get("run_id"),
        "execution_status": execution_status,
        "updated_at": _now(),
    }
    if details:
        status_data.update(details)

    execution_dir = _execution_dir(run_dir)
    _write_json(execution_dir / "status.json", status_data)
    update_execution_status(
        manifest_path,
        status=status,
        execution_status=execution_status,
        action_ids=action_ids,
    )
    if details:
        updated_manifest = _read_json(manifest_path)
        execution = updated_manifest.setdefault("execution", {})
        execution.update(details)
        _write_json(manifest_path, updated_manifest)


def _skill_by_id(inventory: dict[str, Any], skill_id: str) -> dict[str, Any]:
    for skill in inventory.get("skills", []):
        if str(skill.get("skill_id")) == skill_id:
            return skill
    raise ActionError(f"skill not found in inventory: {skill_id}")


def _require_backup(manifest: dict[str, Any]) -> None:
    if manifest.get("backup_policy") == "off":
        raise ActionError("backup_policy is off; rerun with targeted or full backup before execution")


def _validate_action_schema(action: dict[str, Any]) -> None:
    required = {"action_id", "type", "skill_id", "source_path", "source_hash", "reason"}
    missing = sorted(required - set(action))
    if missing:
        raise ActionError("action missing required fields: " + ", ".join(missing))
    if action["type"] not in SUPPORTED_EXECUTION_ACTION_TYPES:
        raise ActionError(f"unsupported action type: {action['type']}")


def _validate_selected_actions_metadata(selected: dict[str, Any], manifest: dict[str, Any]) -> None:
    if selected.get("run_id") != manifest.get("run_id"):
        raise ActionError("selected_actions run_id does not match manifest run_id")
    if selected.get("runtime") != manifest.get("runtime"):
        raise ActionError("selected_actions runtime does not match manifest runtime")


def _approval_confirmation_text(manifest: dict[str, Any], action_ids: list[str]) -> str:
    count = len(action_ids)
    return f"执行 SkillTriage {manifest.get('run_id')} 的 {count} 项整理动作"


def _write_approval_request(
    run_dir: Path,
    manifest: dict[str, Any],
    staged_actions: list[dict[str, Any]],
) -> Path:
    action_ids = [str(action["action_id"]) for action in staged_actions]
    approval_request = {
        "run_id": manifest.get("run_id"),
        "runtime": manifest.get("runtime"),
        "status": "approval_required",
        "created_at": _now(),
        "action_ids": action_ids,
        "confirmation_text": _approval_confirmation_text(manifest, action_ids),
    }
    approval_request_path = _execution_dir(run_dir) / "approval_request.json"
    _write_json(approval_request_path, approval_request)
    approval_path = _execution_dir(run_dir) / "approval.json"
    if approval_path.exists() or approval_path.is_symlink():
        if approval_path.is_dir() and not approval_path.is_symlink():
            raise ActionError("approval path is not a file")
        approval_path.unlink()
    return approval_request_path


def _validate_apply_approval(
    run_dir: Path,
    manifest: dict[str, Any],
    staged_actions: list[dict[str, Any]],
) -> None:
    execution_dir = _execution_dir(run_dir)
    approval_request_path = execution_dir / "approval_request.json"
    approval_path = execution_dir / "approval.json"
    if not approval_request_path.exists() or not approval_path.exists():
        raise ActionError("approval required before apply")

    approval_request = _read_json(approval_request_path)
    approval = _read_json(approval_path)
    expected_action_ids = [str(action["action_id"]) for action in staged_actions]
    expected_confirmation = _approval_confirmation_text(manifest, expected_action_ids)

    if approval_request.get("status") != "approval_required":
        raise ActionError("approval_request status must be approval_required")
    if approval_request.get("run_id") != manifest.get("run_id"):
        raise ActionError("approval_request run_id does not match manifest run_id")
    if approval_request.get("runtime") != manifest.get("runtime"):
        raise ActionError("approval_request runtime does not match manifest runtime")
    if approval_request.get("action_ids") != expected_action_ids:
        raise ActionError("approval_request action_ids do not match staged_actions")
    if approval_request.get("confirmation_text") != expected_confirmation:
        raise ActionError("approval_request confirmation_text does not match staged_actions")

    if approval.get("status") != "approved":
        raise ActionError("approval status must be approved")
    if approval.get("run_id") != manifest.get("run_id"):
        raise ActionError("approval run_id does not match manifest run_id")
    if approval.get("runtime") != manifest.get("runtime"):
        raise ActionError("approval runtime does not match manifest runtime")
    if approval.get("action_ids") != expected_action_ids:
        raise ActionError("approval action_ids do not match staged_actions")
    if approval.get("confirmation_text") != expected_confirmation:
        raise ActionError("approval confirmation_text does not match required confirmation")


def _validate_execution_artifact_metadata(
    artifact: dict[str, Any],
    manifest: dict[str, Any],
    artifact_name: str,
    expected_status: str | tuple[str, ...],
) -> None:
    if artifact.get("run_id") != manifest.get("run_id"):
        raise ActionError(f"{artifact_name} run_id does not match manifest run_id")
    if artifact.get("runtime") != manifest.get("runtime"):
        raise ActionError(f"{artifact_name} runtime does not match manifest runtime")
    allowed_statuses = (expected_status,) if isinstance(expected_status, str) else expected_status
    if artifact.get("status") not in allowed_statuses:
        if len(allowed_statuses) == 1:
            expected = allowed_statuses[0]
        else:
            expected = " or ".join(allowed_statuses)
        raise ActionError(f"{artifact_name} status must be {expected}")


def _validate_skill_is_writable(skill: dict[str, Any]) -> None:
    if bool(skill.get("is_self")):
        raise ActionError("refusing to modify SkillTriage self skill")
    if bool(skill.get("managed")):
        raise ActionError("refusing to modify managed skill")
    if not bool(skill.get("writable")):
        raise ActionError("refusing to modify read-only skill")
    if str(skill.get("source_type")) == "unknown":
        raise ActionError("refusing to modify unknown-source skill")


def _validate_skill_hash(skill_file: Path, expected_hash: str) -> None:
    if not skill_file.exists():
        raise ActionError(f"source skill file does not exist: {skill_file}")
    if not skill_file.is_file():
        raise ActionError(f"source skill file is not a file: {skill_file}")
    actual_hash = _hash_file(skill_file)
    if actual_hash != expected_hash:
        raise ActionError(f"hash mismatch for {skill_file}: expected {expected_hash}, got {actual_hash}")


def _validate_file_hash(path: Path, expected_hash: str, label: str) -> None:
    if not path.exists():
        raise ActionError(f"{label} missing: {path}")
    if not path.is_file():
        raise ActionError(f"{label} is not a file: {path}")
    actual_hash = _hash_file(path)
    if actual_hash != expected_hash:
        raise ActionError(f"{label} hash mismatch for {path}: expected {expected_hash}, got {actual_hash}")


def _validate_one_action_per_skill(actions: list[dict[str, Any]], artifact_name: str) -> None:
    seen_by_skill_id: dict[str, str] = {}
    for action in actions:
        if action.get("type") not in SUPPORTED_EXECUTION_ACTION_TYPES:
            continue
        skill_id = str(action.get("skill_id") or "")
        action_id = str(action.get("action_id") or "")
        if skill_id in seen_by_skill_id:
            raise ActionError(
                f"{artifact_name} contains multiple actions for skill_id: "
                f"{skill_id} ({seen_by_skill_id[skill_id]}, {action_id})"
            )
        seen_by_skill_id[skill_id] = action_id


def _physical_skill_target_key(target_dir: Path) -> str:
    try:
        return os.fspath(target_dir.resolve(strict=False))
    except OSError:
        return os.fspath(target_dir)


def _physical_skill_target_dir(action: dict[str, Any]) -> Path:
    if action["type"] == ACTION_TYPE_ARCHIVE_SKILL:
        return _lexical_absolute_path(action["source_path"], "source_path")
    if action["type"] == ACTION_TYPE_REPLACE_SKILL_FILE:
        return _lexical_absolute_path(action["source_path"], "source_path").parent
    raise ActionError(f"unsupported action type: {action['type']}")


def _remember_physical_skill_target(
    seen_by_target: dict[str, str],
    artifact_name: str,
    action: dict[str, Any],
    target_dir: Path,
) -> None:
    target_key = _physical_skill_target_key(target_dir)
    action_id = str(action.get("action_id") or "")
    existing_action_id = seen_by_target.get(target_key)
    if existing_action_id is not None:
        raise ActionError(
            f"{artifact_name} contains multiple actions for physical skill directory: "
            f"{target_dir} ({existing_action_id}, {action_id})"
        )
    seen_by_target[target_key] = action_id


def _validate_one_action_per_physical_skill_dir(actions: list[dict[str, Any]], artifact_name: str) -> None:
    seen_by_target: dict[str, str] = {}
    for action in actions:
        if action.get("type") not in SUPPORTED_EXECUTION_ACTION_TYPES:
            continue
        _remember_physical_skill_target(
            seen_by_target,
            artifact_name,
            action,
            _physical_skill_target_dir(action),
        )


def _validate_replace_proposal_registered(
    manifest: dict[str, Any],
    action: dict[str, Any],
    source_file: Path,
) -> None:
    proposals = manifest.get("proposals")
    if not isinstance(proposals, list):
        raise ActionError("manifest proposals must be a list")

    expected = {
        "action": ACTION_TYPE_REPLACE_SKILL_FILE,
        "status": "proposed",
        "skill_id": str(action["skill_id"]),
        "source_path": str(source_file),
        "source_hash": str(action["source_hash"]),
        "proposal_path": str(action.get("proposal_path") or ""),
    }
    for proposal in proposals:
        if not isinstance(proposal, dict):
            raise ActionError("manifest proposal must be an object")
        if all(str(proposal.get(field) or "") == value for field, value in expected.items()):
            return
    raise ActionError("replace_skill_file proposal is not registered in manifest")


def _copy_file_atomically(source_path: Path, target_path: Path, action_id: object) -> None:
    temp_path = target_path.with_name(f".{target_path.name}.{_safe_path_part(str(action_id))}.tmp")
    if temp_path.exists():
        raise ActionError(f"temporary replace path already exists: {temp_path}")
    try:
        shutil.copy2(source_path, temp_path)
        os.replace(temp_path, target_path)
    finally:
        if temp_path.exists():
            temp_path.unlink()


def _validate_archive_action_targets(
    action: dict[str, Any],
    skill: dict[str, Any],
    *,
    symlink_message: str = "refusing to stage symlinked skill directory",
) -> tuple[Path, Path]:
    source_dir = _lexical_absolute_path(action["source_path"], "source_path")
    inventory_skill_dir = _lexical_absolute_path(skill.get("skill_dir", ""), "inventory skill_dir")
    if source_dir != inventory_skill_dir:
        raise ActionError("source_path does not match inventory skill_dir")

    if source_dir.is_symlink():
        raise ActionError(symlink_message)

    skill_file = _lexical_absolute_path(source_dir / "SKILL.md", "source SKILL.md")
    inventory_skill_file = _lexical_absolute_path(skill.get("skill_file", ""), "inventory skill_file")
    if inventory_skill_file != skill_file:
        raise ActionError("skill_file does not match source SKILL.md")

    inventory_hash = str(skill.get("hash") or "")
    if str(action["source_hash"]) != inventory_hash:
        raise ActionError("source_hash does not match inventory hash")

    return source_dir, skill_file


def _validate_replace_action_targets(
    action: dict[str, Any],
    skill: dict[str, Any],
    *,
    symlink_message: str = "refusing to stage symlinked skill directory",
) -> Path:
    source_file = _lexical_absolute_path(action["source_path"], "source_path")
    if source_file.name != "SKILL.md":
        raise ActionError(f"replace_skill_file source must be SKILL.md: {source_file}")

    inventory_skill_file = _lexical_absolute_path(skill.get("skill_file", ""), "inventory skill_file")
    if source_file != inventory_skill_file:
        raise ActionError("source_path does not match inventory skill_file")

    inventory_skill_dir = _lexical_absolute_path(skill.get("skill_dir", ""), "inventory skill_dir")
    if source_file.parent != inventory_skill_dir:
        raise ActionError("source_path does not match inventory skill_dir")
    if inventory_skill_dir.is_symlink():
        raise ActionError(symlink_message)
    if source_file.is_symlink():
        raise ActionError("refusing to modify symlinked SKILL.md")

    inventory_hash = str(skill.get("hash") or "")
    if str(action["source_hash"]) != inventory_hash:
        raise ActionError("source_hash does not match inventory hash")

    return source_file


def _prepare_archive_action(run_dir: Path, action: dict[str, Any], skill: dict[str, Any]) -> dict[str, Any]:
    source_dir, skill_file = _validate_archive_action_targets(action, skill)
    if not source_dir.is_dir():
        raise ActionError(f"archive source directory does not exist: {source_dir}")
    _validate_skill_hash(skill_file, str(action["source_hash"]))

    action_id = _safe_path_part(str(action["action_id"]))
    backup_path = Path("execution") / "backups" / action_id / "original"
    archive_path = Path("execution") / "archive" / action_id / source_dir.name
    absolute_backup_path = _run_relative_path(
        run_dir,
        backup_path,
        "backup_path",
        expected_parts=("execution", "backups"),
    )
    absolute_archive_path = _run_relative_path(
        run_dir,
        archive_path,
        "archive_path",
        expected_parts=("execution", "archive"),
    )
    if absolute_backup_path.exists():
        raise ActionError(f"backup path already exists: {absolute_backup_path}")
    if absolute_archive_path.exists():
        raise ActionError(f"archive path already exists: {absolute_archive_path}")

    return {
        "action_id": action["action_id"],
        "type": ACTION_TYPE_ARCHIVE_SKILL,
        "status": "staged",
        "skill_id": action["skill_id"],
        "source_path": str(source_dir),
        "source_hash": action["source_hash"],
        "backup_path": str(backup_path),
        "archive_path": str(archive_path),
        "reason": action["reason"],
        "validated_at": _now(),
    }


def _stage_replace_action(
    run_dir: Path,
    manifest: dict[str, Any],
    action: dict[str, Any],
    skill: dict[str, Any],
) -> dict[str, Any]:
    source_file = _validate_replace_action_targets(action, skill)
    _validate_skill_hash(source_file, str(action["source_hash"]))
    proposal_path = _proposal_path_from_action(run_dir, action)
    _validate_replace_proposal_registered(manifest, action, source_file)
    if not proposal_path.exists():
        raise ActionError(f"proposal file missing: {proposal_path}")
    if not proposal_path.is_file():
        raise ActionError(f"proposal file is not a file: {proposal_path}")

    action_id = _safe_path_part(str(action["action_id"]))
    backup_path = Path("execution") / "backups" / action_id / "original.SKILL.md"
    proposed_backup_path = Path("execution") / "backups" / action_id / "proposed.SKILL.md"
    absolute_backup_path = _run_relative_path(
        run_dir,
        backup_path,
        "backup_path",
        expected_parts=("execution", "backups"),
    )
    absolute_proposed_backup_path = _run_relative_path(
        run_dir,
        proposed_backup_path,
        "proposed_backup_path",
        expected_parts=("execution", "backups"),
    )
    if absolute_backup_path.exists() or absolute_proposed_backup_path.exists():
        raise ActionError(f"replace backup path already exists for action: {action_id}")

    return {
        "action_id": action["action_id"],
        "type": ACTION_TYPE_REPLACE_SKILL_FILE,
        "status": "staged",
        "skill_id": action["skill_id"],
        "source_path": str(source_file),
        "source_hash": action["source_hash"],
        "proposal_path": str(action["proposal_path"]),
        "proposal_hash": _hash_file(proposal_path),
        "backup_path": str(backup_path),
        "proposed_backup_path": str(proposed_backup_path),
        "reason": action["reason"],
        "validated_at": _now(),
    }


def _proposal_path_from_action(run_dir: Path, action: dict[str, Any]) -> Path:
    proposal_value = action.get("proposal_path")
    if not proposal_value:
        raise ActionError("replace_skill_file action requires proposal_path")
    return _run_relative_path(
        run_dir,
        proposal_value,
        "proposal_path",
        expected_parts=("proposals",),
    )


def _copy_archive_backup(run_dir: Path, staged_action: dict[str, Any]) -> None:
    source_dir = Path(str(staged_action["source_path"]))
    backup_path = _backup_path_from_action(run_dir, staged_action)
    shutil.copytree(source_dir, backup_path, symlinks=True)


def _copy_replace_backups(run_dir: Path, staged_action: dict[str, Any]) -> None:
    source_path, backup_path, proposed_backup_path = _replace_paths_from_action(run_dir, staged_action)
    proposal_path = _proposal_path_from_action(run_dir, staged_action)
    if backup_path.exists() or proposed_backup_path.exists():
        raise ActionError(f"replace backup path already exists for action: {staged_action['action_id']}")
    if source_path.is_symlink():
        raise ActionError("refusing to stage symlinked SKILL.md")
    _validate_skill_hash(source_path, str(staged_action["source_hash"]))
    _validate_file_hash(proposal_path, str(staged_action["proposal_hash"]), "proposal file")

    backup_path.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source_path, backup_path)
    shutil.copy2(proposal_path, proposed_backup_path)


def _preflight_actions(
    run_dir: Path,
    selected: dict[str, Any],
    inventory: dict[str, Any],
    manifest: dict[str, Any],
) -> list[dict[str, Any]]:
    actions = selected.get("actions", [])
    if not isinstance(actions, list):
        raise ActionError("selected_actions actions must be a list")

    staged_actions: list[dict[str, Any]] = []
    seen_action_ids: set[str] = set()
    seen_backup_paths: set[str] = set()
    for action in actions:
        if not isinstance(action, dict):
            raise ActionError("selected_actions action must be an object")
        _validate_action_schema(action)
        action_id = str(action["action_id"])
        if action_id in seen_action_ids:
            raise ActionError(f"duplicate action_id: {action_id}")
        seen_action_ids.add(action_id)

    for action in actions:
        action_id = str(action["action_id"])
        skill = _skill_by_id(inventory, str(action["skill_id"]))
        _validate_skill_is_writable(skill)
        if action["type"] == ACTION_TYPE_ARCHIVE_SKILL:
            staged_action = _prepare_archive_action(run_dir, action, skill)
        elif action["type"] == ACTION_TYPE_REPLACE_SKILL_FILE:
            staged_action = _stage_replace_action(run_dir, manifest, action, skill)
        staged_actions.append(staged_action)

        backup_path = str(staged_action.get("backup_path", ""))
        if backup_path:
            if backup_path in seen_backup_paths:
                raise ActionError(f"duplicate backup path for action_id: {action_id}")
            seen_backup_paths.add(backup_path)

    _validate_one_action_per_skill(staged_actions, "selected_actions")
    _validate_one_action_per_physical_skill_dir(staged_actions, "selected_actions")
    return staged_actions


def _execution_actions(artifact: dict[str, Any], artifact_name: str) -> list[dict[str, Any]]:
    actions = artifact.get("actions", [])
    if not isinstance(actions, list):
        raise ActionError(f"{artifact_name} actions must be a list")
    for action in actions:
        if not isinstance(action, dict):
            raise ActionError(f"{artifact_name} action must be an object")
        _validate_action_schema(action)
    return actions


def _required_action_binding_fields(action_type: object) -> tuple[str, ...]:
    if action_type == ACTION_TYPE_ARCHIVE_SKILL:
        return ARCHIVE_ACTION_BINDING_FIELDS
    if action_type == ACTION_TYPE_REPLACE_SKILL_FILE:
        return REPLACE_ACTION_BINDING_FIELDS
    return BASE_ACTION_BINDING_FIELDS


def _action_binding_for_action(action: dict[str, Any], artifact_name: str) -> dict[str, Any]:
    required_fields = _required_action_binding_fields(action.get("type"))
    missing = sorted(field for field in required_fields if field not in action)
    if missing:
        raise ActionError(f"{artifact_name} action missing binding fields: " + ", ".join(missing))
    return {
        field: action[field]
        for field in sorted(action)
        if field not in ACTION_BINDING_EXCLUDED_FIELDS
    }


def _manifest_action_bindings_by_id(manifest: dict[str, Any]) -> dict[str, dict[str, Any]]:
    execution = manifest.get("execution")
    if not isinstance(execution, dict):
        raise ActionError("manifest execution action_bindings must be a list")
    bindings = execution.get("action_bindings")
    if not isinstance(bindings, list):
        raise ActionError("manifest execution action_bindings must be a list")

    bindings_by_id: dict[str, dict[str, Any]] = {}
    for binding in bindings:
        if not isinstance(binding, dict):
            raise ActionError("manifest execution action_binding must be an object")
        missing = sorted(
            field
            for field in _required_action_binding_fields(binding.get("type"))
            if field not in binding
        )
        if missing:
            raise ActionError("manifest execution action_binding missing fields: " + ", ".join(missing))
        action_id = str(binding["action_id"])
        if action_id in bindings_by_id:
            raise ActionError(f"duplicate manifest execution action_binding: {action_id}")
        bindings_by_id[action_id] = binding
    return bindings_by_id


def _validate_staged_action_bindings_against_manifest(
    staged_actions: list[dict[str, Any]],
    manifest: dict[str, Any],
) -> None:
    expected_by_id = _manifest_action_bindings_by_id(manifest)
    actual_by_id: dict[str, dict[str, Any]] = {}
    for action in staged_actions:
        binding = _action_binding_for_action(action, "staged_actions")
        action_id = str(binding["action_id"])
        if action_id in actual_by_id:
            raise ActionError(f"duplicate staged action_id: {action_id}")
        actual_by_id[action_id] = binding

    expected_ids = set(expected_by_id)
    actual_ids = set(actual_by_id)
    if actual_ids != expected_ids:
        missing = sorted(expected_ids - actual_ids)
        extra = sorted(actual_ids - expected_ids)
        details: list[str] = []
        if missing:
            details.append("missing: " + ", ".join(missing))
        if extra:
            details.append("extra: " + ", ".join(extra))
        suffix = f" ({'; '.join(details)})" if details else ""
        raise ActionError("staged_actions action IDs must match manifest execution action_bindings" + suffix)

    for action_id in sorted(actual_by_id):
        expected = expected_by_id[action_id]
        actual = actual_by_id[action_id]
        for field in sorted(set(expected) | set(actual)):
            if field not in expected or field not in actual or expected[field] != actual[field]:
                raise ActionError(
                    "staged_actions action binding does not match manifest execution action_bindings "
                    f"for action_id: {action_id} ({field})"
                )


def _validate_staged_action_ids_against_manifest(
    staged_actions: list[dict[str, Any]],
    manifest: dict[str, Any],
) -> None:
    execution = manifest.get("execution")
    if not isinstance(execution, dict):
        raise ActionError("manifest execution action_ids must be a list")
    expected_action_ids = execution.get("action_ids")
    if not isinstance(expected_action_ids, list):
        raise ActionError("manifest execution action_ids must be a list")

    expected_ids = [str(action_id) for action_id in expected_action_ids]
    staged_ids = [str(action["action_id"]) for action in staged_actions]

    seen_expected_ids: set[str] = set()
    for action_id in expected_ids:
        if action_id in seen_expected_ids:
            raise ActionError(f"duplicate manifest execution action_id: {action_id}")
        seen_expected_ids.add(action_id)

    seen_staged_ids: set[str] = set()
    for action_id in staged_ids:
        if action_id in seen_staged_ids:
            raise ActionError(f"duplicate staged action_id: {action_id}")
        seen_staged_ids.add(action_id)

    expected_set = set(expected_ids)
    staged_set = set(staged_ids)
    if staged_set != expected_set:
        missing = sorted(expected_set - staged_set)
        extra = sorted(staged_set - expected_set)
        details: list[str] = []
        if missing:
            details.append("missing: " + ", ".join(missing))
        if extra:
            details.append("extra: " + ", ".join(extra))
        suffix = f" ({'; '.join(details)})" if details else ""
        raise ActionError("staged_actions action IDs must match manifest execution action_ids" + suffix)


def _validate_execution_action_ids_against_manifest(
    actions: list[dict[str, Any]],
    manifest: dict[str, Any],
    artifact_name: str,
) -> None:
    execution = manifest.get("execution")
    if not isinstance(execution, dict):
        raise ActionError("manifest execution action_ids must be a list")
    expected_action_ids = execution.get("action_ids")
    if not isinstance(expected_action_ids, list):
        raise ActionError("manifest execution action_ids must be a list")

    expected_ids = [str(action_id) for action_id in expected_action_ids]
    actual_ids = [str(action["action_id"]) for action in actions]

    seen_expected_ids: set[str] = set()
    for action_id in expected_ids:
        if action_id in seen_expected_ids:
            raise ActionError(f"duplicate manifest execution action_id: {action_id}")
        seen_expected_ids.add(action_id)

    seen_actual_ids: set[str] = set()
    for action_id in actual_ids:
        if action_id in seen_actual_ids:
            raise ActionError(f"duplicate {artifact_name} action_id: {action_id}")
        seen_actual_ids.add(action_id)

    expected_set = set(expected_ids)
    actual_set = set(actual_ids)
    if actual_set != expected_set:
        missing = sorted(expected_set - actual_set)
        extra = sorted(actual_set - expected_set)
        details: list[str] = []
        if missing:
            details.append("missing: " + ", ".join(missing))
        if extra:
            details.append("extra: " + ", ".join(extra))
        suffix = f" ({'; '.join(details)})" if details else ""
        raise ActionError(f"{artifact_name} action IDs must match manifest execution action_ids" + suffix)


def _archive_paths_from_action(run_dir: Path, action: dict[str, Any]) -> tuple[Path, Path]:
    if "archive_path" not in action:
        raise ActionError("archive action missing archive_path")
    source_path = _lexical_absolute_path(action["source_path"], "source_path")
    archive_path = _run_relative_path(
        run_dir,
        action["archive_path"],
        "archive_path",
        expected_parts=("execution", "archive"),
    )
    return source_path, archive_path


def _backup_path_from_action(run_dir: Path, action: dict[str, Any]) -> Path:
    if "backup_path" not in action:
        raise ActionError("action missing backup_path")
    return _run_relative_path(
        run_dir,
        action["backup_path"],
        "backup_path",
        expected_parts=("execution", "backups"),
    )


def _proposed_backup_path_from_action(run_dir: Path, action: dict[str, Any]) -> Path:
    if "proposed_backup_path" not in action:
        raise ActionError("replace action missing proposed_backup_path")
    return _run_relative_path(
        run_dir,
        action["proposed_backup_path"],
        "proposed_backup_path",
        expected_parts=("execution", "backups"),
    )


def _replace_paths_from_action(run_dir: Path, action: dict[str, Any]) -> tuple[Path, Path, Path]:
    source_path = _lexical_absolute_path(action["source_path"], "source_path")
    backup_path = _backup_path_from_action(run_dir, action)
    proposed_backup_path = _proposed_backup_path_from_action(run_dir, action)
    return source_path, backup_path, proposed_backup_path


def _validate_archive_backup(run_dir: Path, action: dict[str, Any]) -> None:
    backup_path = _backup_path_from_action(run_dir, action)
    if not backup_path.exists():
        raise ActionError(f"backup path missing for apply: {backup_path}")
    if not backup_path.is_dir():
        raise ActionError(f"backup path is not a directory: {backup_path}")


def _validate_archived_skill_file(archive_path: Path, expected_hash: str) -> None:
    _validate_file_hash(archive_path / "SKILL.md", expected_hash, "archived SKILL.md")


def _raise_directory_mismatch(directory_label: str, relative_path: Path, reason: str) -> None:
    display_path = os.fspath(relative_path)
    raise ActionError(f"{directory_label} directory does not match backup at {display_path}: {reason}")


def _directory_entries(path: Path, relative_path: Path, label: str, mismatch_label: str) -> dict[str, Path]:
    try:
        return {entry.name: entry for entry in path.iterdir()}
    except OSError as exc:
        _raise_directory_mismatch(mismatch_label, relative_path, f"could not read {label} directory: {exc}")


def _validate_directory_matches_backup(
    directory_path: Path,
    backup_path: Path,
    *,
    directory_label: str,
    backup_missing_context: str,
) -> None:
    if not backup_path.exists():
        raise ActionError(f"backup path missing for {backup_missing_context}: {backup_path}")
    if backup_path.is_symlink():
        raise ActionError(f"refusing to {backup_missing_context} from symlinked backup path")
    if not backup_path.is_dir():
        raise ActionError(f"backup path is not a directory: {backup_path}")

    def mismatch(relative_path: Path, reason: str) -> None:
        _raise_directory_mismatch(directory_label, relative_path, reason)

    def compare_entries(directory_entry: Path, backup_entry: Path, relative_path: Path) -> None:
        directory_is_symlink = directory_entry.is_symlink()
        backup_is_symlink = backup_entry.is_symlink()
        if directory_is_symlink or backup_is_symlink:
            if not directory_is_symlink or not backup_is_symlink:
                mismatch(relative_path, "entry type differs")
            if os.readlink(directory_entry) != os.readlink(backup_entry):
                mismatch(relative_path, "symlink target mismatch")
            return

        if not directory_entry.exists():
            mismatch(relative_path, f"{directory_label} entry missing")
        if not backup_entry.exists():
            mismatch(relative_path, "backup entry missing")

        directory_is_dir = directory_entry.is_dir()
        backup_is_dir = backup_entry.is_dir()
        if directory_is_dir or backup_is_dir:
            if not directory_is_dir or not backup_is_dir:
                mismatch(relative_path, "entry type differs")
            directory_entries = _directory_entries(directory_entry, relative_path, directory_label, directory_label)
            backup_entries = _directory_entries(backup_entry, relative_path, "backup", directory_label)
            directory_names = set(directory_entries)
            backup_names = set(backup_entries)
            if directory_names != backup_names:
                details: list[str] = []
                missing = sorted(backup_names - directory_names)
                extra = sorted(directory_names - backup_names)
                if missing:
                    details.append("missing: " + ", ".join(missing))
                if extra:
                    details.append("extra: " + ", ".join(extra))
                mismatch(relative_path, "directory entries differ (" + "; ".join(details) + ")")
            for name in sorted(directory_names):
                compare_entries(directory_entries[name], backup_entries[name], relative_path / name)
            return

        directory_is_file = directory_entry.is_file()
        backup_is_file = backup_entry.is_file()
        if directory_is_file or backup_is_file:
            if not directory_is_file or not backup_is_file:
                mismatch(relative_path, "entry type differs")
            if _hash_file(directory_entry) != _hash_file(backup_entry):
                mismatch(relative_path, "file content hash mismatch")
            return

        mismatch(relative_path, "unsupported entry type")

    compare_entries(directory_path, backup_path, Path("."))


def _validate_archive_directory_matches_backup(archive_path: Path, backup_path: Path) -> None:
    _validate_directory_matches_backup(
        archive_path,
        backup_path,
        directory_label="archive",
        backup_missing_context="rollback",
    )


def _validate_replace_backups(run_dir: Path, action: dict[str, Any]) -> None:
    _source_path, backup_path, proposed_backup_path = _replace_paths_from_action(run_dir, action)
    _validate_file_hash(backup_path, str(action["source_hash"]), "original backup")
    _validate_file_hash(proposed_backup_path, str(action["proposal_hash"]), "proposed backup")


def _preflight_apply_replace_action(
    run_dir: Path,
    action: dict[str, Any],
    inventory: dict[str, Any],
) -> Path:
    if action.get("status") != "staged":
        raise ActionError("staged_actions replace action status must be staged")

    skill = _skill_by_id(inventory, str(action["skill_id"]))
    _validate_skill_is_writable(skill)
    source_path = _validate_replace_action_targets(
        action,
        skill,
        symlink_message="refusing to apply symlinked skill directory",
    )
    staged_source_path, _backup_path, _proposed_backup_path = _replace_paths_from_action(run_dir, action)
    if staged_source_path != source_path:
        raise ActionError("source_path does not match inventory skill_file")
    _proposal_path_from_action(run_dir, action)
    _validate_skill_hash(source_path, str(action["source_hash"]))
    _validate_replace_backups(run_dir, action)
    return source_path


def _preflight_apply_actions(run_dir: Path, actions: list[dict[str, Any]], inventory: dict[str, Any]) -> None:
    _validate_one_action_per_skill(actions, "staged_actions")
    _validate_one_action_per_physical_skill_dir(actions, "staged_actions")

    seen_sources: set[str] = set()
    seen_archives: set[str] = set()
    seen_replace_sources: set[str] = set()
    for action in actions:
        if action["type"] == ACTION_TYPE_REPLACE_SKILL_FILE:
            source_path = _preflight_apply_replace_action(run_dir, action, inventory)
            source_key = os.fspath(source_path)
            if source_key in seen_replace_sources:
                raise ActionError(f"duplicate replace source path: {source_path}")
            seen_replace_sources.add(source_key)
            continue
        if action["type"] != ACTION_TYPE_ARCHIVE_SKILL:
            continue
        if action.get("status") != "staged":
            raise ActionError("staged_actions archive action status must be staged")

        skill = _skill_by_id(inventory, str(action["skill_id"]))
        _validate_skill_is_writable(skill)
        source_path, skill_file = _validate_archive_action_targets(
            action,
            skill,
            symlink_message="refusing to apply symlinked skill directory",
        )
        staged_source_path, archive_path = _archive_paths_from_action(run_dir, action)
        if staged_source_path != source_path:
            raise ActionError("source_path does not match inventory skill_dir")
        _validate_archive_backup(run_dir, action)
        backup_path = _backup_path_from_action(run_dir, action)

        source_key = os.fspath(source_path)
        archive_key = os.fspath(archive_path)
        if source_key in seen_sources:
            raise ActionError(f"duplicate archive source path: {source_path}")
        if archive_key in seen_archives:
            raise ActionError(f"duplicate archive destination path: {archive_path}")
        seen_sources.add(source_key)
        seen_archives.add(archive_key)

        if not source_path.exists():
            raise ActionError(f"archive source no longer exists: {source_path}")
        if source_path.is_symlink():
            raise ActionError("refusing to apply symlinked skill directory")
        if not source_path.is_dir():
            raise ActionError(f"archive source is not a directory: {source_path}")
        _validate_skill_hash(skill_file, str(action["source_hash"]))
        _validate_directory_matches_backup(
            source_path,
            backup_path,
            directory_label="source",
            backup_missing_context="apply",
        )
        if archive_path.exists():
            raise ActionError(f"archive destination already exists: {archive_path}")
    _validate_one_action_per_skill(actions, "staged_actions")


def _preflight_rollback_replace_action(run_dir: Path, action: dict[str, Any]) -> Path:
    if action.get("status") != "applied":
        raise ActionError("applied_actions replace action status must be applied")

    source_path, _backup_path, _proposed_backup_path = _replace_paths_from_action(run_dir, action)
    if not source_path.exists():
        raise ActionError(f"rollback source missing: {source_path}")
    if source_path.is_symlink():
        raise ActionError(f"refusing to rollback symlinked SKILL.md: {source_path}")
    if not source_path.is_file():
        raise ActionError(f"rollback source is not a file: {source_path}")

    _proposal_path_from_action(run_dir, action)
    _validate_replace_backups(run_dir, action)
    expected_applied_hash = str(action.get("applied_hash") or "")
    if not expected_applied_hash:
        raise ActionError("applied_actions replace action missing applied_hash")
    expected_proposal_hash = str(action.get("proposal_hash") or "")
    if expected_applied_hash != expected_proposal_hash:
        raise ActionError("applied_hash does not match proposal_hash")
    current_hash = _hash_file(source_path)
    if current_hash != expected_applied_hash:
        raise ActionError(f"source file changed after apply: {source_path}")
    return source_path


def _preflight_rollback_actions(run_dir: Path, actions: list[dict[str, Any]]) -> None:
    _validate_one_action_per_skill(actions, "applied_actions")
    _validate_one_action_per_physical_skill_dir(actions, "applied_actions")

    seen_sources: set[str] = set()
    seen_archives: set[str] = set()
    seen_replace_sources: set[str] = set()
    for action in actions:
        if action["type"] == ACTION_TYPE_REPLACE_SKILL_FILE:
            source_path = _preflight_rollback_replace_action(run_dir, action)
            source_key = os.fspath(source_path)
            if source_key in seen_replace_sources:
                raise ActionError(f"duplicate rollback replace target path: {source_path}")
            seen_replace_sources.add(source_key)
            continue
        if action["type"] != ACTION_TYPE_ARCHIVE_SKILL:
            continue
        if action.get("status") != "applied":
            raise ActionError("applied_actions archive action status must be applied")

        source_path, archive_path = _archive_paths_from_action(run_dir, action)
        source_key = os.fspath(source_path)
        archive_key = os.fspath(archive_path)
        if source_key in seen_sources:
            raise ActionError(f"duplicate rollback target path: {source_path}")
        if archive_key in seen_archives:
            raise ActionError(f"duplicate rollback archive path: {archive_path}")
        seen_sources.add(source_key)
        seen_archives.add(archive_key)

        source_parent = source_path.parent
        if source_parent.is_symlink():
            raise ActionError(f"refusing to rollback into symlinked parent directory: {source_parent}")
        if not source_parent.exists():
            raise ActionError(f"rollback parent missing: {source_parent}")
        if not source_parent.is_dir():
            raise ActionError(f"rollback parent is not a directory: {source_parent}")
        if source_path.exists():
            raise ActionError(f"rollback target already exists: {source_path}")
        if not archive_path.exists():
            raise ActionError(f"archive path missing for rollback: {archive_path}")
        if archive_path.is_symlink():
            raise ActionError("refusing to rollback symlinked archive path")
        if not archive_path.is_dir():
            raise ActionError(f"archive path is not a directory: {archive_path}")


def _validate_rollback_actions_against_staged(
    run_dir: Path,
    applied_actions: list[dict[str, Any]],
    staged_actions: list[dict[str, Any]],
    inventory: dict[str, Any],
    *,
    allow_partial: bool = False,
) -> None:
    staged_by_id: dict[str, dict[str, Any]] = {}
    staged_archive_ids: set[str] = set()
    for staged_action in staged_actions:
        action_id = str(staged_action["action_id"])
        if action_id in staged_by_id:
            raise ActionError(f"duplicate staged action_id: {action_id}")
        staged_by_id[action_id] = staged_action
        if staged_action["type"] == ACTION_TYPE_ARCHIVE_SKILL:
            staged_archive_ids.add(action_id)

    seen_applied_ids: set[str] = set()
    applied_archive_ids: set[str] = set()
    for action in applied_actions:
        action_id = str(action["action_id"])
        if action_id in seen_applied_ids:
            raise ActionError(f"duplicate applied action_id: {action_id}")
        seen_applied_ids.add(action_id)
        if action["type"] == ACTION_TYPE_ARCHIVE_SKILL:
            applied_archive_ids.add(action_id)

    if allow_partial:
        archive_ids_valid = applied_archive_ids <= staged_archive_ids
    else:
        archive_ids_valid = applied_archive_ids == staged_archive_ids
    if not archive_ids_valid:
        missing = sorted(staged_archive_ids - applied_archive_ids)
        extra = sorted(applied_archive_ids - staged_archive_ids)
        details: list[str] = []
        if missing and not allow_partial:
            details.append("missing: " + ", ".join(missing))
        if extra:
            details.append("extra: " + ", ".join(extra))
        suffix = f" ({'; '.join(details)})" if details else ""
        raise ActionError("applied_actions archive action IDs must match staged_actions" + suffix)

    staged_ids = set(staged_by_id)
    applied_ids = set(seen_applied_ids)
    if allow_partial:
        action_ids_valid = applied_ids <= staged_ids
    else:
        action_ids_valid = applied_ids == staged_ids
    if not action_ids_valid:
        missing = sorted(staged_ids - applied_ids)
        extra = sorted(applied_ids - staged_ids)
        details: list[str] = []
        if missing and not allow_partial:
            details.append("missing: " + ", ".join(missing))
        if extra:
            details.append("extra: " + ", ".join(extra))
        suffix = f" ({'; '.join(details)})" if details else ""
        raise ActionError("applied_actions action IDs must match staged_actions" + suffix)

    _validate_one_action_per_skill(staged_actions, "staged_actions")
    _validate_one_action_per_skill(applied_actions, "applied_actions")
    _validate_one_action_per_physical_skill_dir(staged_actions, "staged_actions")
    _validate_one_action_per_physical_skill_dir(applied_actions, "applied_actions")

    for action in applied_actions:
        action_id = str(action["action_id"])
        staged_action = staged_by_id.get(action_id)
        if staged_action is None:
            raise ActionError(f"applied_actions action_id not found in staged_actions: {action_id}")
        if staged_action.get("status") != "staged":
            raise ActionError("staged_actions action status must be staged")
        if action["type"] == ACTION_TYPE_ARCHIVE_SKILL:
            required_matches = ("type", "skill_id", "source_path", "source_hash", "archive_path", "backup_path")
        elif action["type"] == ACTION_TYPE_REPLACE_SKILL_FILE:
            required_matches = (
                "type",
                "skill_id",
                "source_path",
                "source_hash",
                "backup_path",
                "proposal_path",
                "proposal_hash",
                "proposed_backup_path",
            )
        else:
            continue
        for field in required_matches:
            if action.get(field) != staged_action.get(field):
                raise ActionError(f"{field} does not match staged_actions for action_id: {action_id}")
        if action["type"] == ACTION_TYPE_REPLACE_SKILL_FILE:
            applied_hash = str(action.get("applied_hash") or "")
            expected_proposal_hash = str(staged_action.get("proposal_hash") or "")
            if not applied_hash:
                raise ActionError("applied_actions replace action missing applied_hash")
            if applied_hash != expected_proposal_hash:
                raise ActionError(f"applied_hash does not match staged proposal_hash for action_id: {action_id}")

        skill = _skill_by_id(inventory, str(action["skill_id"]))
        _validate_skill_is_writable(skill)
        if action["type"] == ACTION_TYPE_ARCHIVE_SKILL:
            _validate_archive_action_targets(
                action,
                skill,
                symlink_message="refusing to rollback symlinked skill directory",
            )
            _backup_path_from_action(run_dir, action)
        elif action["type"] == ACTION_TYPE_REPLACE_SKILL_FILE:
            _validate_replace_action_targets(
                action,
                skill,
                symlink_message="refusing to rollback symlinked skill directory",
            )
            _proposal_path_from_action(run_dir, action)
            _replace_paths_from_action(run_dir, action)


def _preflight_rollback_archive_contents(run_dir: Path, actions: list[dict[str, Any]]) -> None:
    for action in actions:
        if action["type"] != ACTION_TYPE_ARCHIVE_SKILL:
            continue
        _source_path, archive_path = _archive_paths_from_action(run_dir, action)
        backup_path = _backup_path_from_action(run_dir, action)
        _validate_archived_skill_file(archive_path, str(action["source_hash"]))
        _validate_archive_directory_matches_backup(archive_path, backup_path)


def stage_actions(run_dir: Path, actions_file: Path) -> Path:
    run_dir = Path(run_dir)
    actions_file = Path(actions_file)
    manifest_path = run_dir / "manifest.json"
    manifest = _read_json(manifest_path)
    inventory = _read_json(run_dir / "inventory.json")
    selected = _read_json(actions_file)
    _validate_selected_actions_metadata(selected, manifest)
    _require_backup(manifest)
    staged_actions = _preflight_actions(run_dir, selected, inventory, manifest)

    execution_dir = _execution_dir(run_dir)
    execution_dir.mkdir(exist_ok=True)
    for action in staged_actions:
        if action["type"] == ACTION_TYPE_ARCHIVE_SKILL:
            _copy_archive_backup(run_dir, action)
        elif action["type"] == ACTION_TYPE_REPLACE_SKILL_FILE:
            _copy_replace_backups(run_dir, action)

    staged = {
        "run_id": manifest.get("run_id"),
        "runtime": manifest.get("runtime"),
        "status": "staged",
        "created_at": _now(),
        "actions": staged_actions,
    }
    staged_path = execution_dir / "staged_actions.json"
    _write_json(staged_path, staged)
    _write_approval_request(run_dir, manifest, staged_actions)
    _write_execution_status(
        run_dir,
        manifest_path,
        manifest,
        status=RUN_STATUS_STAGED,
        execution_status="staged",
        action_ids=[str(action["action_id"]) for action in staged_actions],
        details={
            "action_bindings": [
                _action_binding_for_action(action, "staged_actions")
                for action in staged_actions
            ],
        },
    )
    return staged_path


def _apply_archive_action(run_dir: Path, action: dict[str, Any]) -> dict[str, Any]:
    source_path, archive_path = _archive_paths_from_action(run_dir, action)
    archive_path.parent.mkdir(parents=True, exist_ok=True)
    shutil.move(str(source_path), str(archive_path))
    applied = dict(action)
    applied["status"] = "applied"
    applied["applied_at"] = _now()
    return applied


def _apply_replace_action(run_dir: Path, action: dict[str, Any]) -> dict[str, Any]:
    source_path, _backup_path, proposed_backup_path = _replace_paths_from_action(run_dir, action)
    if source_path.parent.is_symlink():
        raise ActionError(f"refusing to apply replace into symlinked parent directory: {source_path.parent}")
    if source_path.is_symlink():
        raise ActionError(f"refusing to apply replace into symlinked SKILL.md: {source_path}")
    _validate_skill_hash(source_path, str(action["source_hash"]))
    _validate_file_hash(proposed_backup_path, str(action["proposal_hash"]), "proposed backup")
    _copy_file_atomically(proposed_backup_path, source_path, action["action_id"])
    applied = dict(action)
    applied["status"] = "applied"
    applied["applied_hash"] = _hash_file(source_path)
    applied["applied_at"] = _now()
    return applied


def _compensate_apply_actions(run_dir: Path, applied_actions: list[dict[str, Any]]) -> None:
    for action in reversed(applied_actions):
        if action["type"] == ACTION_TYPE_ARCHIVE_SKILL:
            source_path, archive_path = _archive_paths_from_action(run_dir, action)
            shutil.move(str(archive_path), str(source_path))
        elif action["type"] == ACTION_TYPE_REPLACE_SKILL_FILE:
            source_path, backup_path, _proposed_backup_path = _replace_paths_from_action(run_dir, action)
            _copy_file_atomically(backup_path, source_path, action["action_id"])


def apply_actions(run_dir: Path) -> Path:
    run_dir = Path(run_dir)
    manifest_path = run_dir / "manifest.json"
    manifest = _read_json(manifest_path)
    inventory = _read_json(run_dir / "inventory.json")
    staged = _read_json(run_dir / "execution" / "staged_actions.json")
    _require_backup(manifest)
    _validate_execution_artifact_metadata(staged, manifest, "staged_actions", "staged")
    actions = _execution_actions(staged, "staged_actions")
    _validate_staged_action_ids_against_manifest(actions, manifest)
    _validate_staged_action_bindings_against_manifest(actions, manifest)
    _validate_apply_approval(run_dir, manifest, actions)
    _preflight_apply_actions(run_dir, actions, inventory)

    applied_actions: list[dict[str, Any]] = []
    current_action: dict[str, Any] | None = None
    try:
        for action in actions:
            current_action = action
            if action["type"] == ACTION_TYPE_ARCHIVE_SKILL:
                applied_actions.append(_apply_archive_action(run_dir, action))
            elif action["type"] == ACTION_TYPE_REPLACE_SKILL_FILE:
                applied_actions.append(_apply_replace_action(run_dir, action))
    except Exception as exc:
        action_id = str((current_action or {}).get("action_id", "unknown"))
        try:
            _compensate_apply_actions(run_dir, applied_actions)
        except Exception as compensation_exc:
            completed_action_ids = [str(action["action_id"]) for action in applied_actions]
            partial_details = {
                "failed_action_id": action_id,
                "error": str(exc),
                "compensation_status": "failed",
                "compensation_error": str(compensation_exc),
                "completed_action_ids": completed_action_ids,
            }
            partial_applied = {
                "run_id": manifest.get("run_id"),
                "runtime": manifest.get("runtime"),
                "status": RUN_STATUS_PARTIALLY_APPLIED,
                "created_at": _now(),
                "actions": applied_actions,
                **partial_details,
            }
            _write_json(_execution_dir(run_dir) / "applied_actions.json", partial_applied)
            _write_execution_status(
                run_dir,
                manifest_path,
                manifest,
                status=RUN_STATUS_PARTIALLY_APPLIED,
                execution_status=RUN_STATUS_PARTIALLY_APPLIED,
                action_ids=completed_action_ids,
                details=partial_details,
            )
            raise ActionError(
                f"failed to apply action {action_id}: {exc}; compensation failed: {compensation_exc}"
            ) from exc
        raise ActionError(f"failed to apply action {action_id}: {exc}") from exc

    applied = {
        "run_id": manifest.get("run_id"),
        "runtime": manifest.get("runtime"),
        "status": "applied",
        "created_at": _now(),
        "actions": applied_actions,
    }
    execution_dir = _execution_dir(run_dir)
    applied_path = execution_dir / "applied_actions.json"
    _write_json(applied_path, applied)
    _write_execution_status(
        run_dir,
        manifest_path,
        manifest,
        status=RUN_STATUS_APPLIED,
        execution_status="applied",
        action_ids=[str(action["action_id"]) for action in applied_actions],
    )
    return applied_path


def _rollback_archive_action(run_dir: Path, action: dict[str, Any]) -> dict[str, Any]:
    source_path, archive_path = _archive_paths_from_action(run_dir, action)
    shutil.move(str(archive_path), str(source_path))
    rolled_back = dict(action)
    rolled_back["status"] = "rolled_back"
    rolled_back["rolled_back_at"] = _now()
    return rolled_back


def _rollback_replace_action(run_dir: Path, action: dict[str, Any]) -> dict[str, Any]:
    source_path, backup_path, _proposed_backup_path = _replace_paths_from_action(run_dir, action)
    if source_path.parent.is_symlink():
        raise ActionError(f"refusing to rollback replace into symlinked parent directory: {source_path.parent}")
    if source_path.is_symlink():
        raise ActionError(f"refusing to rollback symlinked SKILL.md: {source_path}")
    expected_applied_hash = str(action.get("applied_hash") or "")
    if not expected_applied_hash:
        raise ActionError("applied_actions replace action missing applied_hash")
    expected_proposal_hash = str(action.get("proposal_hash") or "")
    if expected_applied_hash != expected_proposal_hash:
        raise ActionError("applied_hash does not match proposal_hash")
    current_hash = _hash_file(source_path)
    if current_hash != expected_applied_hash:
        raise ActionError(f"source file changed after apply: {source_path}")
    _validate_file_hash(backup_path, str(action["source_hash"]), "original backup")
    _copy_file_atomically(backup_path, source_path, action["action_id"])
    rolled_back = dict(action)
    rolled_back["status"] = "rolled_back"
    rolled_back["rolled_back_at"] = _now()
    return rolled_back


def _compensate_rollback_actions(run_dir: Path, rolled_back_actions: list[dict[str, Any]]) -> None:
    for action in reversed(rolled_back_actions):
        if action["type"] == ACTION_TYPE_ARCHIVE_SKILL:
            source_path, archive_path = _archive_paths_from_action(run_dir, action)
            shutil.move(str(source_path), str(archive_path))
        elif action["type"] == ACTION_TYPE_REPLACE_SKILL_FILE:
            source_path, _backup_path, proposed_backup_path = _replace_paths_from_action(run_dir, action)
            _copy_file_atomically(proposed_backup_path, source_path, action["action_id"])


def rollback_actions(run_dir: Path) -> Path:
    run_dir = Path(run_dir)
    manifest_path = run_dir / "manifest.json"
    manifest = _read_json(manifest_path)
    applied = _read_json(run_dir / "execution" / "applied_actions.json")
    _validate_execution_artifact_metadata(
        applied,
        manifest,
        "applied_actions",
        ("applied", RUN_STATUS_PARTIALLY_APPLIED),
    )
    is_partially_applied = applied.get("status") == RUN_STATUS_PARTIALLY_APPLIED
    actions = _execution_actions(applied, "applied_actions")
    inventory = _read_json(run_dir / "inventory.json")
    staged = _read_json(run_dir / "execution" / "staged_actions.json")
    _validate_execution_artifact_metadata(staged, manifest, "staged_actions", "staged")
    staged_actions = _execution_actions(staged, "staged_actions")
    if is_partially_applied:
        _validate_execution_action_ids_against_manifest(actions, manifest, "applied_actions")
    else:
        _validate_staged_action_ids_against_manifest(staged_actions, manifest)
    _validate_staged_action_bindings_against_manifest(staged_actions, manifest)
    _preflight_rollback_actions(run_dir, actions)
    _validate_rollback_actions_against_staged(
        run_dir,
        actions,
        staged_actions,
        inventory,
        allow_partial=is_partially_applied,
    )
    _preflight_rollback_archive_contents(run_dir, actions)

    rollback_order: list[dict[str, Any]] = []
    current_action: dict[str, Any] | None = None
    try:
        for action in reversed(actions):
            current_action = action
            if action["type"] == ACTION_TYPE_ARCHIVE_SKILL:
                rollback_order.append(_rollback_archive_action(run_dir, action))
            elif action["type"] == ACTION_TYPE_REPLACE_SKILL_FILE:
                rollback_order.append(_rollback_replace_action(run_dir, action))
    except Exception as exc:
        action_id = str((current_action or {}).get("action_id", "unknown"))
        try:
            _compensate_rollback_actions(run_dir, rollback_order)
        except Exception as compensation_exc:
            completed_action_ids = [str(action["action_id"]) for action in rollback_order]
            partial_rolled_back_actions = list(reversed(rollback_order))
            partial_details = {
                "failed_action_id": action_id,
                "error": str(exc),
                "compensation_status": "failed",
                "compensation_error": str(compensation_exc),
                "completed_action_ids": completed_action_ids,
            }
            partial_rolled_back = {
                "run_id": manifest.get("run_id"),
                "runtime": manifest.get("runtime"),
                "status": RUN_STATUS_PARTIALLY_ROLLED_BACK,
                "created_at": _now(),
                "actions": partial_rolled_back_actions,
                **partial_details,
            }
            _write_json(_execution_dir(run_dir) / "rolled_back_actions.json", partial_rolled_back)
            _write_execution_status(
                run_dir,
                manifest_path,
                manifest,
                status=RUN_STATUS_PARTIALLY_ROLLED_BACK,
                execution_status=RUN_STATUS_PARTIALLY_ROLLED_BACK,
                action_ids=completed_action_ids,
                details=partial_details,
            )
            raise ActionError(
                f"failed to rollback action {action_id}: {exc}; compensation failed: {compensation_exc}"
            ) from exc
        raise ActionError(f"failed to rollback action {action_id}: {exc}") from exc
    rolled_back_actions = list(reversed(rollback_order))

    rolled_back = {
        "run_id": manifest.get("run_id"),
        "runtime": manifest.get("runtime"),
        "status": "rolled_back",
        "created_at": _now(),
        "actions": rolled_back_actions,
    }
    execution_dir = _execution_dir(run_dir)
    rolled_back_path = execution_dir / "rolled_back_actions.json"
    _write_json(rolled_back_path, rolled_back)
    _write_execution_status(
        run_dir,
        manifest_path,
        manifest,
        status=RUN_STATUS_ROLLED_BACK,
        execution_status="rolled_back",
        action_ids=[str(action["action_id"]) for action in rolled_back_actions],
    )
    return rolled_back_path
