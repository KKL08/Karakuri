from __future__ import annotations

from .models import SCHEMA_VERSION
from .redaction import redact_secret_like_values
from .store import read_artifact


def preview_item(item_id: str) -> tuple[int, dict]:
    if item_id.startswith("plan_"):
        plan = read_artifact("plans", item_id)
        return 0, {
            "schema_version": SCHEMA_VERSION,
            "plan_id": item_id,
            "state": plan.get("state", "planned"),
            "actions": redact_secret_like_values(plan.get("actions", [])),
            "message": "Plan preview only. Hermes source memory has not been modified.",
        }
    if item_id.startswith("run_"):
        return 2, {
            "schema_version": SCHEMA_VERSION,
            "run_id": item_id,
            "status": "not_implemented",
            "message": "Run preview belongs to the staged-run milestone and is not implemented in M1/M2.",
        }
    return 2, {
        "schema_version": SCHEMA_VERSION,
        "status": "unknown_preview_id",
        "message": "Preview IDs must start with plan_ or run_.",
    }
