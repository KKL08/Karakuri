from __future__ import annotations

from .hermes import MissingHermesProfile, load_memory_files
from .ids import new_id
from .models import SCHEMA_VERSION, dataclass_to_json
from .parser import parse_memory_entries
from .rules import detect_issues
from .store import write_artifact


def scan_hermes() -> tuple[int, dict]:
    try:
        hermes_home, memory_files, missing = load_memory_files()
    except MissingHermesProfile as exc:
        return 3, {
            "schema_version": SCHEMA_VERSION,
            "system": "hermes",
            "status": "missing_profile",
            "message": "Hermes profile not found. Set HERMES_HOME or confirm Hermes is installed.",
            "path": str(exc),
        }

    entries = []
    source_files = []
    for memory_file in memory_files:
        if not memory_file.exists:
            continue
        source_files.append(str(memory_file.path))
        entries.extend(parse_memory_entries(memory_file.target, memory_file.path, memory_file.text))

    issues = detect_issues(entries)
    scan_id = new_id("scan")
    status = "partial" if missing else "ok"
    artifact_payload = {
        "schema_version": SCHEMA_VERSION,
        "scan_id": scan_id,
        "system": "hermes",
        "status": status,
        "hermes_home": str(hermes_home),
        "source_files": source_files,
        "files_scanned": len(source_files),
        "missing_files": missing,
        "entries": len(entries),
        "issues": len(issues),
        "needs_user": sum(1 for issue in issues if issue.needs_user),
        "memory_entries": [dataclass_to_json(entry) for entry in entries],
        "issue_items": [dataclass_to_json(issue) for issue in issues],
    }
    summary_path = write_artifact("scans", scan_id, artifact_payload)
    artifact_payload["summary_path"] = str(summary_path)
    write_artifact("scans", scan_id, artifact_payload)

    public_payload = {
        "schema_version": SCHEMA_VERSION,
        "scan_id": scan_id,
        "system": "hermes",
        "status": status,
        "hermes_home": str(hermes_home),
        "source_files": source_files,
        "files_scanned": len(source_files),
        "missing_files": missing,
        "entries": len(entries),
        "issues": len(issues),
        "needs_user": sum(1 for issue in issues if issue.needs_user),
        "summary_path": str(summary_path),
    }
    return 0, public_payload
