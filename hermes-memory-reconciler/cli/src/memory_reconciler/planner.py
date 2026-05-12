from __future__ import annotations

from .ids import new_id
from .models import SCHEMA_VERSION
from .questions import choices_for_issue
from .redaction import redact_secret_like_values
from .store import iter_artifacts, read_artifact, write_artifact


class ResolutionError(Exception):
    pass


def find_issue(conflict_id: str) -> tuple[dict, dict]:
    for scan in iter_artifacts("scans"):
        for issue in scan.get("issue_items", []):
            if issue["issue_id"] == conflict_id:
                return scan, issue
    raise ResolutionError(f"Unknown conflict_id: {conflict_id}")


def resolve_conflict(conflict_id: str, decision_id: str, note: str) -> dict:
    scan, issue = find_issue(conflict_id)
    choices = choices_for_issue(issue)
    choice = next((item for item in choices if item["decision_id"] == decision_id), None)
    if choice is None:
        raise ResolutionError(f"Unknown decision_id for conflict: {decision_id}")
    resolution_id = new_id("res")
    payload = {
        "schema_version": SCHEMA_VERSION,
        "resolution_id": resolution_id,
        "scan_id": scan["scan_id"],
        "conflict_id": conflict_id,
        "decision_id": decision_id,
        "decision": choice,
        "note": note,
    }
    path = write_artifact("resolutions", resolution_id, payload)
    payload["summary_path"] = str(path)
    write_artifact("resolutions", resolution_id, payload)
    return payload


def _anchor(entry: dict) -> dict:
    return {
        "entry_id": entry["entry_id"],
        "target": entry["target"],
        "source_path": entry["source_path"],
        "start_line": entry["start_line"],
        "end_line": entry["end_line"],
        "old_text": entry["text"],
    }


def _plan_actions(issue: dict, decision: dict) -> list[dict]:
    decision_id = decision["decision_id"]
    entries = issue.get("entries", [])
    if decision_id == "decision_no_change":
        return []
    if issue["category"] == "preference_conflict" and entries:
        primary = entries[0]
        actions = [
            {
                "action": "replace",
                **_anchor(primary),
                "content": decision["content"],
            }
        ]
        if len(entries) > 1:
            actions.append({"action": "remove", **_anchor(entries[1])})
        return actions
    if issue["category"] == "instruction_injection_memory" and decision_id == "decision_remove_unsafe" and entries:
        return [{"action": "remove", **_anchor(entries[0])}]
    if issue["category"] == "scope_ambiguity" and decision_id == "decision_add_scope":
        return [
            {
                "action": "add",
                "target": "memory",
                "content": decision["content"],
            }
        ]
    if issue["category"] == "profile_conflict" and entries:
        if decision_id == "decision_keep_first" and len(entries) > 1:
            return [{"action": "remove", **_anchor(entries[1])}]
        if decision_id == "decision_keep_second":
            return [{"action": "remove", **_anchor(entries[0])}]
    return []


def build_plan(resolution_id: str) -> dict:
    resolution = read_artifact("resolutions", resolution_id)
    _scan, issue = find_issue(resolution["conflict_id"])
    actions = _plan_actions(issue, resolution["decision"])
    plan_id = new_id("plan")
    payload = {
        "schema_version": SCHEMA_VERSION,
        "plan_id": plan_id,
        "resolution_id": resolution_id,
        "scan_id": resolution["scan_id"],
        "conflict_id": resolution["conflict_id"],
        "decision_id": resolution["decision_id"],
        "actions": actions,
        "state": "planned",
    }
    path = write_artifact("plans", plan_id, payload)
    payload["summary_path"] = str(path)
    write_artifact("plans", plan_id, payload)
    return redact_secret_like_values(payload)
