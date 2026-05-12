from __future__ import annotations

import argparse
import json
import sys
from typing import Any

from .models import SCHEMA_VERSION
from .planner import ResolutionError, build_plan, resolve_conflict
from .preview import preview_item
from .questions import build_next_question, build_report
from .scanner import scan_hermes
from .store import ArtifactNotFound, read_artifact


def _print_json(payload: dict[str, Any]) -> None:
    print(json.dumps(payload, ensure_ascii=False, indent=None, sort_keys=True))


def _print_text(payload: dict[str, Any]) -> None:
    if "message" in payload:
        print(payload["message"])
    elif "scan_id" in payload:
        print(f"scan_id: {payload['scan_id']}")
        print(f"status: {payload.get('status', 'ok')}")
        if "issues" in payload:
            print(f"issues: {payload['issues']}")
    elif "plan_id" in payload:
        print(f"plan_id: {payload['plan_id']}")
        print(f"actions: {len(payload.get('actions', []))}")
    elif "resolution_id" in payload:
        print(f"resolution_id: {payload['resolution_id']}")
    else:
        print(json.dumps(payload, ensure_ascii=False, indent=2))


def _emit(payload: dict[str, Any], as_json: bool) -> None:
    if as_json:
        _print_json(payload)
    else:
        _print_text(payload)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="memory-reconciler")
    subparsers = parser.add_subparsers(dest="command", required=True)

    scan = subparsers.add_parser("scan")
    scan.add_argument("--system", default="hermes")
    scan.add_argument("--read-only", action="store_true", help="Accepted for explicitness; scan is read-only by default.")
    scan.add_argument("--json", action="store_true")

    report = subparsers.add_parser("report")
    report.add_argument("scan_id")
    report.add_argument("--limit", type=int, default=5)
    report.add_argument("--severity", default="low", choices=["critical", "high", "medium", "low"])
    report.add_argument("--json", action="store_true")

    question = subparsers.add_parser("next-question")
    question.add_argument("scan_id")
    question.add_argument("--json", action="store_true")

    resolve = subparsers.add_parser("resolve")
    resolve.add_argument("conflict_id")
    resolve.add_argument("--decision", required=True)
    resolve.add_argument("--note", default="")
    resolve.add_argument("--json", action="store_true")

    plan = subparsers.add_parser("plan")
    plan.add_argument("resolution_id")
    plan.add_argument("--json", action="store_true")

    preview = subparsers.add_parser("preview")
    preview.add_argument("item_id")
    preview.add_argument("--json", action="store_true")

    for command in ["stage", "apply", "rollback"]:
        item = subparsers.add_parser(command)
        item.add_argument("item_id")
        item.add_argument("--dry-run", action="store_true")
        item.add_argument("--yes", action="store_true")
        item.add_argument("--json", action="store_true")

    return parser


def run(args: argparse.Namespace) -> int:
    as_json = getattr(args, "json", False)
    try:
        if args.command == "scan":
            if args.system != "hermes":
                _emit({"schema_version": SCHEMA_VERSION, "status": "unsupported_system", "system": args.system}, as_json)
                return 2
            code, payload = scan_hermes()
            payload["read_only"] = True
            _emit(payload, as_json)
            return code

        if args.command == "report":
            scan = read_artifact("scans", args.scan_id)
            payload = build_report(scan, args.limit, args.severity)
            _emit(payload, as_json)
            return 0

        if args.command == "next-question":
            scan = read_artifact("scans", args.scan_id)
            code, payload = build_next_question(scan)
            _emit(payload, as_json)
            return code

        if args.command == "resolve":
            payload = resolve_conflict(args.conflict_id, args.decision, args.note)
            _emit(payload, as_json)
            return 0

        if args.command == "plan":
            payload = build_plan(args.resolution_id)
            _emit(payload, as_json)
            return 0

        if args.command == "preview":
            code, payload = preview_item(args.item_id)
            _emit(payload, as_json)
            return code

        if args.command in {"stage", "apply", "rollback"}:
            _emit(
                {
                    "schema_version": SCHEMA_VERSION,
                    "status": "not_implemented",
                    "command": args.command,
                    "message": f"{args.command} belongs to a later staged-run milestone.",
                },
                as_json,
            )
            return 2
    except ArtifactNotFound as exc:
        _emit({"schema_version": SCHEMA_VERSION, "status": "artifact_not_found", "message": str(exc)}, as_json)
        return 2
    except ResolutionError as exc:
        _emit({"schema_version": SCHEMA_VERSION, "status": "resolution_error", "message": str(exc)}, as_json)
        return 2

    _emit({"schema_version": SCHEMA_VERSION, "status": "unknown_command"}, as_json)
    return 2


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return run(args)


if __name__ == "__main__":
    sys.exit(main())
