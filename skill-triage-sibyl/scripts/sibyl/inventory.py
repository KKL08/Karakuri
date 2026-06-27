from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

FRONTMATTER_LIMIT = 4000
BODY_SNIPPET_CHARS = 600


def _claude_code_roots() -> list[tuple[Path, str, bool, bool]]:
    home = Path.home()
    candidates = [
        (home / ".claude" / "skills", "user", True, False),
        (home / ".claude" / "plugins" / "cache", "plugin-managed", False, True),
        (Path.cwd() / ".claude" / "skills", "project", True, False),
    ]
    return [(root, kind, writable, managed)
            for root, kind, writable, managed in candidates if root.exists()]


def _codex_roots() -> list[tuple[Path, str, bool, bool]]:
    home = Path.home()
    candidates = [
        (home / ".codex" / "skills", "user", True, False),
        (home / ".agents" / "skills", "user", True, False),
    ]
    return [(r, k, w, m) for r, k, w, m in candidates if r.exists()]


def _iter_skill_md(root: Path):
    for path in root.rglob("SKILL.md"):
        if path.is_file():
            yield path


def _parse_frontmatter(text: str) -> dict:
    """Parse YAML-ish frontmatter. Handles:
    - flat `key: value` pairs
    - block scalars `key: |` (literal) and `key: >` (folded)
    - implicit continuation: `key:` followed by indented lines

    Stays stdlib-only by hand-rolling — frontmatter shape is narrow enough not
    to need a full YAML parser, but we must handle multi-line description
    fields because skills in the wild commonly use them.
    """
    if not text.startswith("---"):
        return {}
    end = text.find("\n---", 3)
    if end == -1:
        return {}
    block = text[3:end]
    lines = block.splitlines()
    out: dict = {}
    i = 0
    while i < len(lines):
        line = lines[i]
        if not line.strip() or line.lstrip().startswith("#"):
            i += 1
            continue
        # Only consume top-level keys (no leading whitespace) so nested
        # mappings like `metadata:\n  author: ...` don't pollute the top dict.
        if line[:1] in (" ", "\t") or ":" not in line:
            i += 1
            continue
        key, rest = line.split(":", 1)
        key = key.strip()
        rest = rest.strip()

        if rest in ("|", ">", "|-", ">-", "|+", ">+"):
            # Block scalar. Collect all subsequent indented (or blank) lines.
            style = rest[0]
            block_lines: list[str] = []
            i += 1
            while i < len(lines) and (not lines[i].strip() or lines[i][:1] in (" ", "\t")):
                block_lines.append(lines[i].lstrip())
                i += 1
            if style == "|":
                out[key] = "\n".join(block_lines).rstrip()
            else:
                out[key] = " ".join(s for s in block_lines if s).strip()
            continue

        if rest == "":
            # Implicit continuation: `key:` followed by indented lines, joined
            # as folded (single-line). This is the shape `description:\n  ...`
            # uses, common across community skills.
            block_lines = []
            i += 1
            while i < len(lines) and (not lines[i].strip() or lines[i][:1] in (" ", "\t")):
                if lines[i].strip():
                    block_lines.append(lines[i].strip())
                i += 1
            out[key] = " ".join(block_lines)
            continue

        out[key] = rest.strip("'\"")
        i += 1
    return out


def _split_body(text: str) -> str:
    if text.startswith("---"):
        end = text.find("\n---", 3)
        if end != -1:
            return text[end + 4:]
    return text


def _body_snippet(text: str) -> str:
    return _split_body(text).strip()[:BODY_SNIPPET_CHARS]


def _body_metrics(text: str) -> tuple[int, int]:
    body = _split_body(text)
    words = len(body.split())
    h2 = sum(1 for line in body.splitlines() if line.startswith("## "))
    return words, h2


def _version_from_path(skill_dir: Path) -> str | None:
    parts = skill_dir.parts
    if "plugins" not in parts or "cache" not in parts:
        return None
    try:
        idx = parts.index("skills")
    except ValueError:
        return None
    return parts[idx - 1] if idx > 0 else None


def _parse_version(fm: dict, skill_dir: Path) -> str | None:
    return fm.get("version") or _version_from_path(skill_dir)


def _skill_id(source_type: str, runtime: str, name: str, path: Path) -> str:
    h = hashlib.sha1(str(path).encode("utf-8")).hexdigest()[:8]
    return f"{source_type}:{runtime}:{name}:{h}"


def _last_modified_iso(path: Path) -> str:
    return datetime.fromtimestamp(path.stat().st_mtime, tz=timezone.utc).isoformat()


def scan(runtime: str) -> dict:
    roots = _claude_code_roots() if runtime == "claude-code" else _codex_roots()
    skills: list[dict] = []
    for root, source_type, writable, managed in roots:
        for skill_md in _iter_skill_md(root):
            text = skill_md.read_text(encoding="utf-8", errors="replace")
            fm = _parse_frontmatter(text[:FRONTMATTER_LIMIT])
            name = fm.get("name") or skill_md.parent.name
            desc = fm.get("description", "")
            skill_dir = skill_md.parent
            words, h2 = _body_metrics(text)
            skills.append({
                "skill_id": _skill_id(source_type, runtime, name, skill_dir),
                "name": name,
                "description": desc,
                "description_len": len(desc),
                "source_type": source_type,
                "source_root": str(root),
                "skill_path": str(skill_dir),
                "skill_md_path": str(skill_md),
                "writable": writable,
                "managed": managed,
                "last_modified": _last_modified_iso(skill_md),
                "body_snippet": _body_snippet(text),
                "body_word_count": words,
                "body_h2_count": h2,
                "version": _parse_version(fm, skill_dir),
            })
    return {
        "runtime": runtime,
        "scanned_at": datetime.now(timezone.utc).isoformat(),
        "skills": skills,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Scan installed skills for skill-triage-sibyl.")
    parser.add_argument("--runtime", choices=("claude-code", "codex"), required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    data = scan(args.runtime)
    Path(args.output).write_text(
        json.dumps(data, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(f"wrote {args.output} with {len(data['skills'])} skills")


if __name__ == "__main__":
    main()
