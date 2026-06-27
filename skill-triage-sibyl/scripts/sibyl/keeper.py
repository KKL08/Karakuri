"""Git-backed snapshot keeper.

Holds an internal git repo under $CLAUDE_PLUGIN_DATA/skill-triage-sibyl/keeper/repo/
that stores copies of files we may want to roll back later. Each snapshot is a
git commit. Files are stored with their original absolute path encoded as a
relative path inside the repo (leading "/" replaced with "_root_/") so multiple
absolute paths don't collide.

Conflict detection here is mtime-based and is meant for human-driven restores
("give me back the snapshot's version unless I've edited since"). When sibyl's
own apply layer drives a rollback, it does a content-hash check first and then
calls restore with force=True — see apply.rollback for the rationale.
"""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
from datetime import datetime, timezone
from pathlib import Path

from sibyl.config import plugin_data_dir


def _repo() -> Path:
    repo = plugin_data_dir() / "keeper" / "repo"
    repo.mkdir(parents=True, exist_ok=True)
    if not (repo / ".git").exists():
        subprocess.run(["git", "init", "-q"], cwd=repo, check=True)
        subprocess.run(["git", "config", "user.email", "skill-triage-sibyl@local"],
                       cwd=repo, check=True)
        subprocess.run(["git", "config", "user.name", "skill-triage-sibyl"],
                       cwd=repo, check=True)
        subprocess.run(["git", "commit", "--allow-empty", "-q", "-m", "init"],
                       cwd=repo, check=True)
    return repo


def _encode_abs(path: Path) -> Path:
    """Turn an absolute path into a repo-relative path by replacing the leading
    "/" with the literal directory name "_root_"."""
    return Path("_root_") / Path(*path.parts[1:])


def _decode_abs(rel: Path) -> Path:
    parts = rel.parts
    if parts and parts[0] == "_root_":
        return Path("/" + "/".join(parts[1:]))
    return rel


def snap(files: list[Path], message: str) -> dict:
    repo = _repo()
    copied: list[str] = []
    for src in files:
        src = Path(src).expanduser().resolve()
        if not src.exists() or not src.is_file():
            continue
        rel = _encode_abs(src)
        dst = repo / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)
        copied.append(str(rel))
    if not copied:
        return {"status": "no_files"}
    subprocess.run(["git", "add", "-A"], cwd=repo, check=True)
    msg = f"{message}\n\nTime: {datetime.now(timezone.utc).isoformat()}"
    res = subprocess.run(["git", "commit", "-q", "-m", msg],
                         cwd=repo, capture_output=True, text=True)
    if res.returncode != 0:
        if "nothing to commit" in (res.stdout + res.stderr):
            return {"status": "no_changes"}
        return {"status": "error", "error": res.stderr.strip()}
    commit = subprocess.run(["git", "rev-parse", "HEAD"], cwd=repo,
                            capture_output=True, text=True, check=True).stdout.strip()
    return {"status": "ok", "commit": commit, "files_copied": copied}


def head_commit_for(path: Path) -> str | None:
    """Return the most recent commit hash that touched the given absolute path,
    or None if the keeper repo has no record of this file. Used by apply.rewrite
    when snap returns no_changes — we still need a pre_commit handle to roll
    back to."""
    repo = _repo()
    rel = _encode_abs(Path(path).expanduser().resolve())
    res = subprocess.run(
        ["git", "log", "-n1", "--format=%H", "--", str(rel)],
        cwd=repo, capture_output=True, text=True,
    )
    out = res.stdout.strip()
    return out or None


def list_snapshots(limit: int = 20) -> list[dict]:
    repo = _repo()
    res = subprocess.run(["git", "log", f"-n{limit}", "--format=%H|%ai|%s"],
                         cwd=repo, capture_output=True, text=True)
    out: list[dict] = []
    for line in res.stdout.strip().splitlines():
        parts = line.split("|", 2)
        if len(parts) == 3:
            out.append({"commit": parts[0], "date": parts[1].strip(), "message": parts[2]})
    return out


def restore(commit: str, dry_run: bool = False, force: bool = False) -> dict:
    repo = _repo()
    verify = subprocess.run(["git", "cat-file", "-t", commit], cwd=repo,
                            capture_output=True, text=True)
    if verify.returncode != 0:
        return {"status": "error", "error": f"unknown commit {commit}"}

    ts_str = subprocess.run(["git", "show", "-s", "--format=%ct", commit],
                            cwd=repo, capture_output=True, text=True).stdout.strip()
    commit_ts = float(ts_str)

    file_listing = subprocess.run(
        ["git", "show", "--name-only", "--format=", commit],
        cwd=repo, capture_output=True, text=True,
    ).stdout.strip().splitlines()

    restored: list[str] = []
    conflicts: list[dict] = []
    skipped: list[dict] = []

    for rel in file_listing:
        rel_path = Path(rel)
        target = _decode_abs(rel_path)
        content = subprocess.run(["git", "show", f"{commit}:{rel}"], cwd=repo,
                                 capture_output=True).stdout
        if not target.exists():
            skipped.append({"file": str(target), "reason": "target missing"})
            continue
        if target.stat().st_mtime > commit_ts and not force:
            conflicts.append({
                "file": str(target),
                "snapshot_ts": commit_ts,
                "current_mtime": target.stat().st_mtime,
            })
            continue
        if not dry_run:
            target.write_bytes(content)
        restored.append(str(target))

    return {
        "status": "dry_run" if dry_run else "ok",
        "commit": commit,
        "restored": restored,
        "conflicts": conflicts,
        "skipped": skipped,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Git-backed snapshot keeper for skill-triage-sibyl.")
    sub = parser.add_subparsers(dest="cmd", required=True)

    snap_p = sub.add_parser("snap")
    snap_p.add_argument("--files", nargs="+", required=True)
    snap_p.add_argument("--message", required=True)

    list_p = sub.add_parser("list")
    list_p.add_argument("--limit", type=int, default=20)

    restore_p = sub.add_parser("restore")
    restore_p.add_argument("--commit", required=True)
    restore_p.add_argument("--dry-run", action="store_true")
    restore_p.add_argument("--force", action="store_true")

    args = parser.parse_args()

    if args.cmd == "snap":
        result = snap([Path(f) for f in args.files], args.message)
    elif args.cmd == "list":
        result = list_snapshots(args.limit)
    else:
        result = restore(args.commit, args.dry_run, args.force)

    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
