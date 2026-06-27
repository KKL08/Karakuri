"""Apply user-approved actions and roll them back later.

Two action types in v1:
- `archive`: move a skill directory into $CLAUDE_PLUGIN_DATA/skill-triage-sibyl/
  archive/<run-id>/<runtime>/<basename>/ so the runtime stops discovering it.
- `rewrite`: snap the original SKILL.md via keeper, then overwrite with new text.

Each action is appended to runs/<run-id>/actions.jsonl. Rollback reads that
log in reverse and undoes each action with a conflict check:

- archive rollback: original path must be vacant. If something now occupies it,
  refuse unless force=True.
- rewrite rollback: hash current file content against the post_content_hash we
  recorded at rewrite time. If they match (no one touched our rewrite since),
  restore from keeper. If they differ, the file has been edited externally;
  refuse unless force=True.

The hash check exists because keeper's built-in mtime check doesn't fit our
order of operations — we snap *before* writing, so by rollback time the file's
mtime is always later than the snap. The hash tells us whether our written
content is still intact.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
from datetime import datetime, timezone
from pathlib import Path

from sibyl import keeper
from sibyl.config import plugin_data_dir


MANIFEST_NAME = "_sibyl_origin.json"


def _runs_dir() -> Path:
    return plugin_data_dir() / "runs"


def _archive_dir() -> Path:
    return plugin_data_dir() / "archive"


def _actions_log(run_id: str) -> Path:
    p = _runs_dir() / run_id / "actions.jsonl"
    p.parent.mkdir(parents=True, exist_ok=True)
    return p


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _sha256(data: bytes) -> str:
    return "sha256:" + hashlib.sha256(data).hexdigest()


def _append_action(run_id: str, action: dict) -> None:
    action.setdefault("at", _now())
    with _actions_log(run_id).open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(action, ensure_ascii=False) + "\n")


def archive(run_id: str, skill_path: Path, runtime: str) -> dict:
    skill_path = Path(skill_path).expanduser().resolve()
    if not skill_path.is_dir():
        return {"status": "error", "error": f"not a directory: {skill_path}"}
    dest_root = _archive_dir() / run_id / runtime
    dest_root.mkdir(parents=True, exist_ok=True)
    dest = dest_root / skill_path.name
    if dest.exists():
        return {"status": "error", "error": f"archive target exists: {dest}"}

    shutil.move(str(skill_path), str(dest))
    manifest = {
        "type": "archive",
        "original_path": str(skill_path),
        "archived_path": str(dest),
        "runtime": runtime,
    }
    (dest / MANIFEST_NAME).write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8",
    )
    _append_action(run_id, manifest)
    return {"status": "ok", **manifest}


def rewrite(run_id: str, skill_md_path: Path, new_text: str) -> dict:
    skill_md_path = Path(skill_md_path).expanduser().resolve()
    if not skill_md_path.is_file():
        return {"status": "error", "error": f"not a file: {skill_md_path}"}

    snapped = keeper.snap([skill_md_path], message=f"pre-rewrite {run_id} {skill_md_path}")
    if snapped["status"] == "ok":
        pre_commit = snapped["commit"]
    elif snapped["status"] == "no_changes":
        # Content already matched a prior snap — reuse that commit as the
        # rollback target. (Original content lives in that commit's tree.)
        pre_commit = keeper.head_commit_for(skill_md_path)
        if pre_commit is None:
            return {"status": "error",
                    "error": "snap reported no_changes but keeper has no prior commit for this file"}
    else:
        return {"status": "error", "error": f"snapshot failed: {snapped}"}

    new_bytes = new_text.encode("utf-8")
    skill_md_path.write_bytes(new_bytes)
    action = {
        "type": "rewrite",
        "skill_md_path": str(skill_md_path),
        "pre_commit": pre_commit,
        "post_content_hash": _sha256(new_bytes),
    }
    _append_action(run_id, action)
    return {"status": "ok", **action}


def rollback(run_id: str, force: bool = False) -> dict:
    log = _actions_log(run_id)
    if not log.exists() or log.stat().st_size == 0:
        return {"status": "error", "error": f"no actions log for run {run_id}"}

    actions = [json.loads(line) for line in log.read_text(encoding="utf-8").splitlines() if line.strip()]
    undone: list[dict] = []
    conflicts: list[dict] = []
    skipped: list[dict] = []

    for act in reversed(actions):
        if act["type"] == "rewrite":
            target = Path(act["skill_md_path"])
            if not target.exists():
                skipped.append({"file": str(target), "reason": "target missing"})
                continue
            current_hash = _sha256(target.read_bytes())
            if current_hash != act["post_content_hash"] and not force:
                conflicts.append({
                    "file": str(target),
                    "reason": "file content changed after our rewrite",
                    "expected_hash": act["post_content_hash"],
                    "current_hash": current_hash,
                })
                continue
            res = keeper.restore(act["pre_commit"], dry_run=False, force=True)
            if res.get("conflicts"):
                conflicts.extend(res["conflicts"])
            else:
                undone.append(act)

        elif act["type"] == "archive":
            origin = Path(act["original_path"])
            archived = Path(act["archived_path"])
            if origin.exists():
                if not force:
                    conflicts.append({
                        "original_path": str(origin),
                        "reason": "original path is occupied (another file/dir lives there now)",
                    })
                    continue
                # With --force the user accepts that we may overwrite whatever
                # sits at the original path. Move it aside to a sibling so it's
                # not lost outright.
                aside = origin.with_name(origin.name + ".sibyl-conflict")
                shutil.move(str(origin), str(aside))
            if not archived.exists():
                skipped.append({"archived_path": str(archived), "reason": "archive missing"})
                continue
            shutil.move(str(archived), str(origin))
            (origin / MANIFEST_NAME).unlink(missing_ok=True)
            undone.append(act)

    return {
        "status": "ok" if not conflicts else "partial",
        "undone": undone,
        "conflicts": conflicts,
        "skipped": skipped,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Apply or roll back skill-triage-sibyl actions.")
    sub = parser.add_subparsers(dest="cmd", required=True)

    a = sub.add_parser("archive")
    a.add_argument("--run-id", required=True)
    a.add_argument("--skill-path", required=True)
    a.add_argument("--runtime", required=True)

    r = sub.add_parser("rewrite")
    r.add_argument("--run-id", required=True)
    r.add_argument("--skill-md-path", required=True)
    r.add_argument("--new-text-file", required=True)

    b = sub.add_parser("rollback")
    b.add_argument("--run-id", required=True)
    b.add_argument("--force", action="store_true")

    args = parser.parse_args()
    if args.cmd == "archive":
        out = archive(args.run_id, Path(args.skill_path), args.runtime)
    elif args.cmd == "rewrite":
        text = Path(args.new_text_file).read_text(encoding="utf-8")
        out = rewrite(args.run_id, Path(args.skill_md_path), text)
    else:
        out = rollback(args.run_id, args.force)
    print(json.dumps(out, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
