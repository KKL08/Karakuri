from __future__ import annotations

import re
from collections import defaultdict

from .ids import stable_suffix
from .models import Issue, MemoryEntry, dataclass_to_json
from .redaction import redact_secret_like_text


CATEGORY_PRIORITY = {
    "instruction_injection_memory": 0,
    "preference_conflict": 1,
    "profile_conflict": 2,
    "scope_ambiguity": 3,
    "exact_duplicate": 4,
    "low_signal_memory": 5,
    "possible_stale": 6,
}

SEVERITY_BY_CATEGORY = {
    "instruction_injection_memory": "critical",
    "preference_conflict": "high",
    "profile_conflict": "high",
    "scope_ambiguity": "medium",
    "exact_duplicate": "low",
    "low_signal_memory": "low",
    "possible_stale": "low",
}

SEVERITY_PRIORITY = {"critical": 0, "high": 1, "medium": 2, "low": 3}


def _issue_id(category: str, entries: list[MemoryEntry]) -> str:
    prefix = "conflict" if category in {
        "instruction_injection_memory",
        "preference_conflict",
        "profile_conflict",
        "scope_ambiguity",
    } else "issue"
    return f"{prefix}_{category}_{stable_suffix(*(entry.entry_id for entry in entries), length=8)}"


def _issue(category: str, summary: str, entries: list[MemoryEntry], needs_user: bool, topic: str = "") -> Issue:
    return Issue(
        issue_id=_issue_id(category, entries),
        category=category,
        severity=SEVERITY_BY_CATEGORY[category],
        summary=summary,
        needs_user=needs_user,
        topic=topic or category,
        entry_ids=[entry.entry_id for entry in entries],
        entries=[dataclass_to_json(entry) for entry in entries],
    )


def _is_low_signal(text: str) -> bool:
    normalized = text.strip().lower().rstrip(".")
    generic = {
        "need debug",
        "needs debug",
        "project has files",
        "user asked about python",
    }
    if normalized in generic:
        return True
    words = re.findall(r"[\w']+", normalized)
    return len(words) <= 3 and len(normalized) < 24


def _is_instruction_injection(text: str) -> bool:
    lowered = text.lower()
    has_instruction_bypass = (
        ("ignore" in lowered and ("system instruction" in lowered or "previous instruction" in lowered))
        or "bypass approval" in lowered
        or "disable safety" in lowered
        or "reveal the api key" in lowered
        or "leak secret" in lowered
    )
    imperative = any(word in lowered for word in ["ignore", "reveal", "leak", "bypass", "disable"])
    return has_instruction_bypass and imperative


def _answer_depth(entries: list[MemoryEntry], tokens: list[str]) -> list[MemoryEntry]:
    return [entry for entry in entries if any(token in entry.normalized_text for token in tokens)]


def _detect_preference_conflict(entries: list[MemoryEntry]) -> list[Issue]:
    concise = _answer_depth(entries, ["concise", "brief", "short", "简洁", "简短"])
    detailed = _answer_depth(entries, ["detailed", "verbose", "tradeoff", "tradeoffs", "explanations", "详细", "展开"])
    if concise and detailed:
        chosen = [concise[0], detailed[0]]
        return [
            _issue(
                "preference_conflict",
                "Answer-depth preference conflict: concise and detailed-answer preferences both appear without scope.",
                chosen,
                needs_user=True,
                topic="answer_depth",
            )
        ]
    return []


def _detect_profile_conflict(entries: list[MemoryEntry]) -> list[Issue]:
    locations: dict[str, MemoryEntry] = {}
    for entry in entries:
        match = re.search(r"\b(?:based in|lives in|located in)\s+([a-zA-Z ]+)", entry.text, re.I)
        if match:
            locations[match.group(1).strip().lower()] = entry
    if len(locations) > 1:
        chosen = list(locations.values())[:2]
        return [
            _issue(
                "profile_conflict",
                "Profile conflict: multiple long-term location statements appear.",
                chosen,
                needs_user=True,
                topic="profile_location",
            )
        ]
    return []


def _detect_scope_ambiguity(entries: list[MemoryEntry]) -> list[Issue]:
    uv_entries = [entry for entry in entries if "prefers uv" in entry.normalized_text or "prefer uv" in entry.normalized_text]
    pnpm_entries = [entry for entry in entries if "repository uses pnpm" in entry.normalized_text or "repo uses pnpm" in entry.normalized_text]
    if uv_entries and pnpm_entries:
        return [
            _issue(
                "scope_ambiguity",
                "Scope ambiguity: a global tool preference and repository-specific package manager may both be valid.",
                [uv_entries[0], pnpm_entries[0]],
                needs_user=True,
                topic="tool_scope",
            )
        ]
    return []


def detect_issues(entries: list[MemoryEntry]) -> list[Issue]:
    issues: list[Issue] = []

    by_normalized: dict[str, list[MemoryEntry]] = defaultdict(list)
    for entry in entries:
        if entry.normalized_text:
            by_normalized[entry.normalized_text].append(entry)

    for duplicates in by_normalized.values():
        if len(duplicates) > 1:
            issues.append(
                _issue(
                    "exact_duplicate",
                    f"Exact duplicate memory appears {len(duplicates)} times.",
                    duplicates,
                    needs_user=False,
                    topic="duplicate",
                )
            )

    for entry in entries:
        if _is_low_signal(entry.text):
            issues.append(
                _issue(
                    "low_signal_memory",
                    f"Low-signal memory candidate: {entry.text}",
                    [entry],
                    needs_user=False,
                    topic="low_signal",
                )
            )
        if _is_instruction_injection(entry.text):
            issues.append(
                _issue(
                    "instruction_injection_memory",
                    f"Potential unsafe instruction memory: {redact_secret_like_text(entry.text)}",
                    [entry],
                    needs_user=True,
                    topic="unsafe_instruction",
                )
            )
        if re.search(r"\btemporary\b|\blast week\b|\byesterday\b|\b20[0-2][0-9]\b", entry.normalized_text):
            issues.append(
                _issue(
                    "possible_stale",
                    f"Possible stale memory candidate: {entry.text}",
                    [entry],
                    needs_user=False,
                    topic="possible_stale",
                )
            )

    issues.extend(_detect_preference_conflict(entries))
    issues.extend(_detect_profile_conflict(entries))
    issues.extend(_detect_scope_ambiguity(entries))

    return sorted(
        issues,
        key=lambda issue: (
            SEVERITY_PRIORITY[issue.severity],
            CATEGORY_PRIORITY[issue.category],
            issue.issue_id,
        ),
    )
