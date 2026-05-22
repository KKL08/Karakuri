#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from skilltriage.actions import ActionError, apply_actions, rollback_actions, stage_actions


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Stage, apply, or rollback approved SkillTriage actions.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    stage_parser = subparsers.add_parser("stage", help="Stage approved actions without modifying active skills.")
    stage_parser.add_argument("--run-dir", required=True)
    stage_parser.add_argument("--actions-file", required=True)

    apply_parser = subparsers.add_parser("apply", help="Apply staged actions after approval.json is present.")
    apply_parser.add_argument("--run-dir", required=True)

    rollback_parser = subparsers.add_parser("rollback", help="Rollback applied actions.")
    rollback_parser.add_argument("--run-dir", required=True)

    args = parser.parse_args(argv)

    try:
        if args.command == "stage":
            output = stage_actions(Path(args.run_dir), Path(args.actions_file))
            print(f"staged: {output}")
            return 0
        if args.command == "apply":
            output = apply_actions(Path(args.run_dir))
            print(f"applied: {output}")
            return 0
        if args.command == "rollback":
            output = rollback_actions(Path(args.run_dir))
            print(f"rolled_back: {output}")
            return 0
    except (ActionError, OSError, json.JSONDecodeError) as exc:
        print(f"blocked: {exc}", file=sys.stderr)
        return 2

    print(f"unknown command: {args.command}", file=sys.stderr)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
