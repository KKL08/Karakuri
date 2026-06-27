from __future__ import annotations

import argparse
import json
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path


def _claude_code_session_files() -> list[Path]:
    root = Path.home() / ".claude" / "projects"
    if not root.exists():
        return []
    # Each project dir contains <session-uuid>.jsonl directly (no sessions/ subdir).
    return sorted(root.glob("*/*.jsonl"))


def _codex_session_files() -> list[Path]:
    root = Path.home() / ".codex" / "sessions"
    if not root.exists():
        return []
    return sorted(list(root.rglob("*.json")) + list(root.rglob("*.jsonl")))


def _session_files(runtime: str) -> list[Path]:
    return _claude_code_session_files() if runtime == "claude-code" else _codex_session_files()


def _parse_ts(value) -> datetime | None:
    if not value:
        return None
    if isinstance(value, (int, float)):
        raw = float(value)
        if raw > 10_000_000_000:
            raw /= 1000
        return datetime.fromtimestamp(raw, tz=timezone.utc)
    text = str(value)
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    try:
        dt = datetime.fromisoformat(text)
    except ValueError:
        return None
    return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)


def _iter_records(path: Path):
    """Yield records from a JSONL session file, tolerating bad lines."""
    try:
        with path.open("r", encoding="utf-8", errors="replace") as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                try:
                    yield json.loads(line)
                except json.JSONDecodeError:
                    continue
    except OSError:
        return


def _match_tool_use(entry: dict, by_path: dict[str, str], by_name: dict[str, str]) -> str | None:
    name = entry.get("name")
    inp = entry.get("input") or {}
    if name == "Read":
        fp = inp.get("file_path")
        if fp in by_path:
            return by_path[fp]
    elif name == "Skill":
        skill_arg = inp.get("skill") or ""
        # Strip "<plugin>:" namespace prefix (e.g. "superpowers:writing-plans")
        # so inventory lookups by bare skill name still match.
        short = skill_arg.split(":", 1)[-1] if ":" in skill_arg else skill_arg
        if short in by_name:
            return by_name[short]
    return None


def _match_skill(rec: dict, by_path: dict[str, str], by_name: dict[str, str]) -> str | None:
    """Return skill_id if this record references a known skill, else None.

    Handles two shapes:
    - flat tool_use record (test fixture style)
    - message.content[] wrapping (real Claude Code session records)
    """
    if not isinstance(rec, dict):
        return None
    if rec.get("type") == "tool_use":
        return _match_tool_use(rec, by_path, by_name)
    content = (rec.get("message") or {}).get("content")
    if isinstance(content, list):
        for entry in content:
            if isinstance(entry, dict) and entry.get("type") == "tool_use":
                hit = _match_tool_use(entry, by_path, by_name)
                if hit:
                    return hit
    return None


def scan(runtime: str, inventory: dict, window_days: int = 30) -> dict:
    by_path = {s["skill_md_path"]: s["skill_id"] for s in inventory["skills"]}
    by_name = {s["name"]: s["skill_id"] for s in inventory["skills"]}
    id_to_name = {s["skill_id"]: s["name"] for s in inventory["skills"]}

    counts: dict[str, dict] = defaultdict(
        lambda: {"calls_total": 0, "calls_30d": 0,
                 "sessions": set(), "last_used": None}
    )
    window_start = datetime.now(timezone.utc) - timedelta(days=window_days)

    for sess_file in _session_files(runtime):
        session_id = sess_file.stem
        for rec in _iter_records(sess_file):
            skill_id = _match_skill(rec, by_path, by_name)
            if not skill_id:
                continue
            slot = counts[skill_id]
            slot["calls_total"] += 1
            slot["sessions"].add(session_id)
            ts = _parse_ts(rec.get("timestamp"))
            if ts is None:
                continue
            if ts >= window_start:
                slot["calls_30d"] += 1
            if slot["last_used"] is None or ts > slot["last_used"]:
                slot["last_used"] = ts

    rows: list[dict] = []
    for skill_id, slot in counts.items():
        rows.append({
            "skill_id": skill_id,
            "name": id_to_name.get(skill_id, ""),
            "calls_total": slot["calls_total"],
            "calls_30d": slot["calls_30d"],
            "sessions": len(slot["sessions"]),
            "last_used_iso": slot["last_used"].isoformat() if slot["last_used"] else None,
        })

    # Make sure every inventoried skill appears, even with zero usage —
    # this keeps downstream join-by-skill_id simple.
    seen = {row["skill_id"] for row in rows}
    for s in inventory["skills"]:
        if s["skill_id"] not in seen:
            rows.append({
                "skill_id": s["skill_id"],
                "name": s["name"],
                "calls_total": 0,
                "calls_30d": 0,
                "sessions": 0,
                "last_used_iso": None,
            })

    return {
        "runtime": runtime,
        "scan_window_days": window_days,
        "scanned_at": datetime.now(timezone.utc).isoformat(),
        "usage": rows,
        "scan_notes": [],
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Count confirmed skill usage from local session logs.")
    parser.add_argument("--runtime", required=True, choices=("claude-code", "codex"))
    parser.add_argument("--inventory", required=True)
    parser.add_argument("--window-days", type=int, default=30)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    inv = json.loads(Path(args.inventory).read_text(encoding="utf-8"))
    result = scan(args.runtime, inv, args.window_days)
    Path(args.output).write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(f"wrote {args.output} with {len(result['usage'])} rows")


if __name__ == "__main__":
    main()
