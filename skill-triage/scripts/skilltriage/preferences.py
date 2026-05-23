from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any


class PreferenceError(RuntimeError):
    """Raised when decision or preference artifacts are invalid."""


SUPPORTED_DECISION_TYPES = {
    "general_entry_vs_specialized_workflow",
    "provider_preference",
    "local_copy_vs_managed_copy",
    "description_boundary_unclear",
    "personal_workflow_preference",
}

SUPPORTED_DECISION_CHOICES = {
    "keep_all",
    "prefer_general_entry",
    "prefer_specialized_workflow",
    "prefer_managed_copy",
    "prefer_local_copy",
    "clarify_description",
    "archive_candidate",
    "defer",
}

SUPPORTED_PREFERENCE_SCOPES = {
    "global",
    "runtime",
    "service",
    "skill_group",
}

DECISION_ITEM_REQUIRED_FIELDS = {
    "decision_id",
    "decision_type",
    "title",
    "skills",
    "why_user_decides",
    "recommended_default",
    "can_create_preference",
    "preference_scope",
    "options",
}

DECISION_OPTION_REQUIRED_FIELDS = {"choice", "label", "effect"}
USER_DECISION_REQUIRED_FIELDS = {
    "decision_id",
    "choice",
    "remember_preference",
    "created_from_explicit_user_choice",
}
PREFERENCE_UPDATE_REQUIRED_FIELDS = {
    "preference_id",
    "decision_type",
    "choice",
    "scope",
    "runtime",
    "source_run_id",
    "note",
    "created_from_explicit_user_choice",
}


def _safe_preference_id_part(value: Any) -> str:
    text = str(value or "unknown").strip()
    safe = "".join(char if char.isalnum() or char in ("-", "_", ".") else "-" for char in text)
    safe = "-".join(part for part in safe.split("-") if part)
    return safe or "unknown"


def _preference_id(manifest: dict[str, Any], decision: dict[str, Any]) -> str:
    parts = [
        "pref",
        _safe_preference_id_part(manifest.get("runtime")),
        _safe_preference_id_part(manifest.get("run_id")),
        _safe_preference_id_part(decision.get("decision_id")),
        _safe_preference_id_part(decision.get("choice")),
    ]
    return "-".join(parts)


def _now() -> str:
    return datetime.now().astimezone().isoformat()


def _read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def decisions_dir(run_dir: Path) -> Path:
    return Path(run_dir) / "decisions"


def preference_store_path(home: Path | None = None) -> Path:
    return (home or Path.home()) / ".skilltriage" / "preferences" / "user_preferences.json"


def _require_object(value: Any, artifact_name: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise PreferenceError(f"{artifact_name} must be an object")
    return value


def _validate_run_metadata(document: dict[str, Any], manifest: dict[str, Any], document_name: str) -> None:
    if document.get("run_id") != manifest.get("run_id"):
        raise PreferenceError(f"{document_name} run_id does not match manifest run_id")
    if document.get("runtime") != manifest.get("runtime"):
        raise PreferenceError(f"{document_name} runtime does not match manifest runtime")


def _require_fields(data: dict[str, Any], required_fields: set[str], object_name: str) -> None:
    missing = sorted(required_fields - set(data))
    if missing:
        raise PreferenceError(f"{object_name} missing required fields: {', '.join(missing)}")


def _validate_supported_decision_type(value: Any) -> None:
    if value not in SUPPORTED_DECISION_TYPES:
        raise PreferenceError(f"unsupported decision_type: {value}")


def _validate_supported_choice(value: Any) -> None:
    if value not in SUPPORTED_DECISION_CHOICES:
        raise PreferenceError(f"unsupported decision choice: {value}")


def _validate_supported_scope(value: Any) -> None:
    if value not in SUPPORTED_PREFERENCE_SCOPES:
        raise PreferenceError(f"unsupported preference_scope: {value}")


def _validate_decision_item(item: dict[str, Any]) -> set[str]:
    _require_fields(item, DECISION_ITEM_REQUIRED_FIELDS, "decision item")
    _validate_supported_decision_type(item.get("decision_type"))
    _validate_supported_scope(item.get("preference_scope"))
    _validate_supported_choice(item.get("recommended_default"))

    skills = item.get("skills")
    if not isinstance(skills, list) or not skills:
        raise PreferenceError("decision item skills must be a non-empty list")

    options = item.get("options")
    if not isinstance(options, list) or not options:
        raise PreferenceError("decision item options must be a non-empty list")

    offered_choices: set[str] = set()
    for option in options:
        if not isinstance(option, dict):
            raise PreferenceError("decision item option must be an object")
        _require_fields(option, DECISION_OPTION_REQUIRED_FIELDS, "decision option")
        choice = option.get("choice")
        _validate_supported_choice(choice)
        offered_choices.add(str(choice))

    if item.get("recommended_default") not in offered_choices:
        raise PreferenceError("recommended_default must be one of the offered choices")

    if not isinstance(item.get("can_create_preference"), bool):
        raise PreferenceError("can_create_preference must be bool")

    return offered_choices


def validate_decision_items_document(document: dict[str, Any], manifest: dict[str, Any]) -> None:
    document = _require_object(document, "decision_items")
    _validate_run_metadata(document, manifest, "decision_items")
    items = document.get("items")
    if not isinstance(items, list):
        raise PreferenceError("decision_items items must be a list")

    seen_ids: set[str] = set()
    for item in items:
        if not isinstance(item, dict):
            raise PreferenceError("decision item must be an object")
        decision_id = str(item.get("decision_id"))
        if decision_id in seen_ids:
            raise PreferenceError(f"duplicate decision_id: {decision_id}")
        seen_ids.add(decision_id)
        _validate_decision_item(item)


def _items_by_id(decision_items_document: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {str(item["decision_id"]): item for item in decision_items_document.get("items", [])}


def _offered_choices(item: dict[str, Any]) -> set[str]:
    return {str(option["choice"]) for option in item.get("options", [])}


def validate_user_decisions_document(
    document: dict[str, Any],
    manifest: dict[str, Any],
    decision_items_document: dict[str, Any],
) -> None:
    document = _require_object(document, "user_decisions")
    _validate_run_metadata(document, manifest, "user_decisions")
    validate_decision_items_document(decision_items_document, manifest)

    decisions = document.get("decisions")
    if not isinstance(decisions, list):
        raise PreferenceError("user_decisions decisions must be a list")

    items_by_id = _items_by_id(decision_items_document)
    seen_ids: set[str] = set()
    for decision in decisions:
        if not isinstance(decision, dict):
            raise PreferenceError("user decision must be an object")
        _require_fields(decision, USER_DECISION_REQUIRED_FIELDS, "user decision")

        decision_id = str(decision.get("decision_id"))
        if decision_id in seen_ids:
            raise PreferenceError(f"duplicate user decision_id: {decision_id}")
        seen_ids.add(decision_id)

        if decision_id not in items_by_id:
            raise PreferenceError(f"unknown decision_id: {decision_id}")

        choice = decision.get("choice")
        _validate_supported_choice(choice)
        if choice not in _offered_choices(items_by_id[decision_id]):
            raise PreferenceError(f"choice was not offered by item: {choice}")

        if decision.get("created_from_explicit_user_choice") is not True:
            raise PreferenceError("user decision must be created from explicit user choice")
        if not isinstance(decision.get("remember_preference"), bool):
            raise PreferenceError("remember_preference must be bool")


def write_decision_items(run_dir: Path, manifest: dict[str, Any], items: list[dict[str, Any]]) -> Path:
    document = {
        "run_id": manifest.get("run_id"),
        "runtime": manifest.get("runtime"),
        "items": items,
    }
    validate_decision_items_document(document, manifest)
    path = decisions_dir(run_dir) / "decision_items.json"
    _write_json(path, document)
    return path


def read_decision_items(run_dir: Path) -> dict[str, Any]:
    return _read_json(decisions_dir(run_dir) / "decision_items.json")


def write_user_decisions(run_dir: Path, manifest: dict[str, Any], decisions: list[dict[str, Any]]) -> Path:
    document = {
        "run_id": manifest.get("run_id"),
        "runtime": manifest.get("runtime"),
        "decisions": decisions,
    }
    validate_user_decisions_document(document, manifest, read_decision_items(run_dir))
    path = decisions_dir(run_dir) / "user_decisions.json"
    _write_json(path, document)
    return path


def generate_preference_updates(run_dir: Path) -> Path:
    manifest = _read_json(Path(run_dir) / "manifest.json")
    decision_items_document = read_decision_items(run_dir)
    user_decisions_document = _read_json(decisions_dir(run_dir) / "user_decisions.json")
    validate_user_decisions_document(user_decisions_document, manifest, decision_items_document)

    items_by_id = _items_by_id(decision_items_document)
    updates: list[dict[str, Any]] = []
    for decision in user_decisions_document["decisions"]:
        if not decision["remember_preference"]:
            continue

        item = items_by_id[str(decision["decision_id"])]
        if item.get("can_create_preference") is not True:
            raise PreferenceError(f"decision cannot create preference: {decision['decision_id']}")

        updates.append(
            {
                "preference_id": _preference_id(manifest, decision),
                "decision_type": item["decision_type"],
                "choice": decision["choice"],
                "scope": item["preference_scope"],
                "runtime": manifest.get("runtime"),
                "source_run_id": manifest.get("run_id"),
                "note": decision.get("note") or item["why_user_decides"],
                "created_from_explicit_user_choice": True,
            }
        )

    path = decisions_dir(run_dir) / "preference_updates.json"
    _write_json(
        path,
        {
            "run_id": manifest.get("run_id"),
            "runtime": manifest.get("runtime"),
            "updates": updates,
        },
    )
    return path


def load_user_preferences(home: Path | None = None) -> dict[str, Any]:
    path = preference_store_path(home)
    if not path.exists():
        return {"version": 1, "updated_at": None, "preferences": []}

    store = _require_object(_read_json(path), "preference store")
    if store.get("version") != 1:
        raise PreferenceError(f"unsupported preference store version: {store.get('version')}")
    if not isinstance(store.get("preferences"), list):
        raise PreferenceError("preference store preferences must be a list")
    return store


def _validate_preference_update(update: dict[str, Any]) -> None:
    _require_fields(update, PREFERENCE_UPDATE_REQUIRED_FIELDS, "preference update")
    _validate_supported_decision_type(update.get("decision_type"))
    _validate_supported_choice(update.get("choice"))
    _validate_supported_scope(update.get("scope"))
    if update.get("created_from_explicit_user_choice") is not True:
        raise PreferenceError("preference update must be created from explicit user choice")


def append_preference_updates(updates_path: Path, home: Path | None = None) -> Path:
    updates_document = _require_object(_read_json(updates_path), "preference_updates")
    updates = updates_document.get("updates")
    if not isinstance(updates, list):
        raise PreferenceError("preference_updates updates must be a list")

    for update in updates:
        if not isinstance(update, dict):
            raise PreferenceError("preference update must be an object")
        _validate_preference_update(update)

    store = load_user_preferences(home)
    now = _now()
    for update in updates:
        stored_update = dict(update)
        stored_update.setdefault("created_at", now)
        store["preferences"].append(stored_update)
    store["updated_at"] = now

    path = preference_store_path(home)
    _write_json(path, store)
    return path


def _preference_applies(preference: dict[str, Any], runtime: str) -> bool:
    preference_runtime = preference.get("runtime")
    scope = preference.get("scope")
    if scope == "global":
        return True
    if scope == "runtime":
        return preference_runtime in (None, "", runtime)
    return False


def load_preference_hints(runtime: str, home: Path | None = None) -> list[dict[str, Any]]:
    store = load_user_preferences(home)
    grouped: dict[str, list[dict[str, Any]]] = {}
    for preference in store["preferences"]:
        if not isinstance(preference, dict):
            continue
        if not _preference_applies(preference, runtime):
            continue
        decision_type = preference.get("decision_type")
        if decision_type not in SUPPORTED_DECISION_TYPES:
            continue
        grouped.setdefault(str(decision_type), []).append(preference)

    hints: list[dict[str, Any]] = []
    for decision_type in sorted(grouped):
        preferences = grouped[decision_type]
        choices = [str(preference.get("choice")) for preference in preferences if preference.get("choice") in SUPPORTED_DECISION_CHOICES]
        distinct_choices = sorted(set(choices))
        hints.append(
            {
                "decision_type": decision_type,
                "choices": distinct_choices,
                "count": len(preferences),
                "conflict": len(set(choices)) > 1,
                "latest": preferences[-1],
            }
        )
    return hints
