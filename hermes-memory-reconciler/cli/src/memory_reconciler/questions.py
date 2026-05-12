from __future__ import annotations

from .models import SCHEMA_VERSION
from .rules import CATEGORY_PRIORITY, SEVERITY_PRIORITY


def _choices_for(issue: dict) -> list[dict]:
    category = issue["category"]
    if category == "preference_conflict":
        return [
            {
                "decision_id": "decision_default_concise_expand_complex",
                "label": "Default concise; expand for complex engineering or product tradeoffs",
                "content": "User defaults to concise answers; for complex engineering, product judgment, or tradeoffs, include reasoning and detail.",
            },
            {
                "decision_id": "decision_prefer_detailed",
                "label": "Prefer detailed answers by default",
                "content": "User prefers detailed answers with reasoning and tradeoffs by default.",
            },
            {"decision_id": "decision_no_change", "label": "Do not change memory", "content": ""},
        ]
    if category == "scope_ambiguity":
        return [
            {
                "decision_id": "decision_add_scope",
                "label": "Keep both and clarify their scope",
                "content": "Keep the global preference and repository-specific rule, with explicit scope.",
            },
            {"decision_id": "decision_no_change", "label": "Do not change memory", "content": ""},
        ]
    if category == "instruction_injection_memory":
        return [
            {"decision_id": "decision_remove_unsafe", "label": "Remove the unsafe memory", "content": ""},
            {"decision_id": "decision_no_change", "label": "Do not change memory", "content": ""},
        ]
    if category == "profile_conflict":
        return [
            {"decision_id": "decision_keep_first", "label": "Keep the first profile statement", "content": ""},
            {"decision_id": "decision_keep_second", "label": "Keep the second profile statement", "content": ""},
            {"decision_id": "decision_no_change", "label": "Do not change memory", "content": ""},
        ]
    return [{"decision_id": "decision_no_change", "label": "Do not change memory", "content": ""}]


def sorted_issues(scan: dict) -> list[dict]:
    return sorted(
        scan.get("issue_items", []),
        key=lambda issue: (
            SEVERITY_PRIORITY[issue["severity"]],
            CATEGORY_PRIORITY[issue["category"]],
            issue["issue_id"],
        ),
    )


def build_report(scan: dict, limit: int, severity: str) -> dict:
    allowed = {"critical": 0, "high": 1, "medium": 2, "low": 3}
    max_rank = allowed.get(severity, 3)
    issues = [
        issue
        for issue in sorted_issues(scan)
        if allowed.get(issue["severity"], 3) <= max_rank
    ][:limit]
    counts: dict[str, int] = {}
    for issue in scan.get("issue_items", []):
        counts[issue["category"]] = counts.get(issue["category"], 0) + 1
    return {
        "schema_version": SCHEMA_VERSION,
        "scan_id": scan["scan_id"],
        "status": scan["status"],
        "counts": counts,
        "issues": [
            {
                "issue_id": issue["issue_id"],
                "category": issue["category"],
                "severity": issue["severity"],
                "summary": issue["summary"],
                "needs_user": issue["needs_user"],
            }
            for issue in issues
        ],
    }


def build_next_question(scan: dict) -> tuple[int, dict]:
    for issue in sorted_issues(scan):
        if not issue["needs_user"]:
            continue
        choices = _choices_for(issue)
        return 0, {
            "schema_version": SCHEMA_VERSION,
            "scan_id": scan["scan_id"],
            "conflict_id": issue["issue_id"],
            "topic": issue["topic"],
            "reason": issue["summary"],
            "choices": choices,
        }
    return 1, {
        "schema_version": SCHEMA_VERSION,
        "scan_id": scan["scan_id"],
        "status": "no_user_question",
        "message": "No user decision is needed for this scan.",
    }


def choices_for_issue(issue: dict) -> list[dict]:
    return _choices_for(issue)
