#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from skilltriage.preferences import (
    PreferenceError,
    append_preference_updates,
    generate_preference_updates,
    load_user_preferences,
)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Preview, apply, or list SkillTriage user preferences.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    preview_parser = subparsers.add_parser(
        "preview-updates",
        help="Generate preference_updates.json from remembered user decisions.",
    )
    preview_parser.add_argument("--run-dir", required=True)

    apply_parser = subparsers.add_parser(
        "apply-updates",
        help="Append preference_updates.json to the user preference store.",
    )
    apply_parser.add_argument("--run-dir", required=True)
    apply_parser.add_argument("--home")

    list_parser = subparsers.add_parser("list", help="Print the user preference store.")
    list_parser.add_argument("--home")

    args = parser.parse_args(argv)

    try:
        if args.command == "preview-updates":
            output = generate_preference_updates(Path(args.run_dir))
            print(f"preference_updates: {output}")
            return 0
        if args.command == "apply-updates":
            run_dir = Path(args.run_dir)
            output = append_preference_updates(
                run_dir / "decisions" / "preference_updates.json",
                home=Path(args.home) if args.home else None,
            )
            print(f"preferences: {output}")
            return 0
        if args.command == "list":
            data = load_user_preferences(home=Path(args.home) if args.home else None)
            print(json.dumps(data, indent=2, ensure_ascii=False))
            return 0
    except (PreferenceError, OSError, json.JSONDecodeError) as exc:
        print(f"blocked: {exc}", file=sys.stderr)
        return 2

    print(f"unknown command: {args.command}", file=sys.stderr)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
