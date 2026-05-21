from __future__ import annotations

import hashlib
import re
from pathlib import Path

from .capabilities import extract_capability_fingerprint
from .constants import DESCRIPTION_MAX_CHARS, DESCRIPTION_MIN_CHARS, LONG_SKILL_LINES, LONG_SKILL_TOKEN_ESTIMATE
from .frontmatter import parse_skill_markdown
from .similarity import jaccard


REFERENCE_RE = re.compile(r"(references/[A-Za-z0-9_.\-/]+\.md)")


def _sha256(text: str) -> str:
    return "sha256:" + hashlib.sha256(text.encode("utf-8")).hexdigest()


def _missing_references(path: Path, text: str) -> list[str]:
    missing: list[str] = []
    for reference in sorted(set(REFERENCE_RE.findall(text))):
        if not (path.parent / reference).exists():
            missing.append(reference)
    return missing


def analyze_skill_file(path: Path, runtime: str, source_info: dict[str, object], is_self: bool = False) -> tuple[dict[str, object], dict[str, object]]:
    text = path.read_text(encoding="utf-8", errors="replace")
    parsed = parse_skill_markdown(text)
    fingerprint_input = {
        "name": parsed.name or path.parent.name,
        "skill_dir": str(path.parent),
        "description": parsed.description or "",
    }
    capability_fingerprint = extract_capability_fingerprint(fingerprint_input)
    description = parsed.description or ""
    has_scripts = (path.parent / "scripts").exists()
    has_references = (path.parent / "references").exists()
    has_assets = (path.parent / "assets").exists()
    name = parsed.name or path.parent.name
    checks = {
        "frontmatter_malformed": parsed.frontmatter_malformed,
        "missing_name": parsed.name is None,
        "description_absent": parsed.description_status == "absent",
        "description_empty": parsed.description_status == "empty",
        "description_parse_incomplete": parsed.description_status == "parse_incomplete",
        "description_parsed": parsed.description_status == "parsed",
        "missing_description": parsed.description_status == "absent",
        "directory_name_mismatch": parsed.name is not None and parsed.name != path.parent.name,
        "description_too_short": bool(description) and len(description) < DESCRIPTION_MIN_CHARS,
        "description_too_long": len(description) > DESCRIPTION_MAX_CHARS,
        "long_skill": parsed.body_lines > LONG_SKILL_LINES or parsed.body_token_estimate > LONG_SKILL_TOKEN_ESTIMATE,
        "has_scripts": has_scripts,
        "has_references": has_references,
        "has_assets": has_assets,
        "broken_references": _missing_references(path, text),
        "read_only_source": not bool(source_info.get("writable")),
    }
    source_id = str(source_info.get("source_id") or f"{source_info.get('source_type', 'unknown')}-0")
    candidate = (not is_self) and any(
        bool(checks[key])
        for key in (
            "frontmatter_malformed",
            "missing_name",
            "description_absent",
            "description_empty",
            "description_parse_incomplete",
            "directory_name_mismatch",
            "description_too_short",
            "description_too_long",
            "long_skill",
            "broken_references",
        )
    )
    item = {
        "skill_id": f"{runtime}:{source_info.get('source_type', 'unknown')}:{name}@{source_id}",
        "runtime": runtime,
        "source_id": source_id,
        "source_type": source_info.get("source_type", "unknown"),
        "source_root": "",
        "skill_dir": str(path.parent),
        "skill_file": str(path),
        "name": name,
        "description": parsed.description,
        "hash": _sha256(text),
        "writable": bool(source_info.get("writable")),
        "managed": bool(source_info.get("managed")),
        "is_self": is_self,
        "discovered": True,
        "active_state": "unknown",
        "body_lines": parsed.body_lines,
        "body_token_estimate": parsed.body_token_estimate,
        "has_scripts": has_scripts,
        "has_references": has_references,
        "has_assets": has_assets,
        "needs_security_note": has_scripts,
        "candidate_for_agent_evaluation": candidate,
        "description_status": parsed.description_status,
        "description_raw": parsed.description_raw,
        "frontmatter_notes": parsed.frontmatter_notes,
        "capability_fingerprint": capability_fingerprint,
    }
    return item, checks


def build_similarity_candidates(skills: list[dict[str, object]]) -> list[dict[str, object]]:
    candidates: list[dict[str, object]] = []
    seen_pairs: set[tuple[str, str]] = set()
    for left_index, left in enumerate(skills):
        for right in skills[left_index + 1 :]:
            left_id = str(left["skill_id"])
            right_id = str(right["skill_id"])
            if left_id == right_id:
                continue
            pair_key = tuple(sorted((left_id, right_id)))
            if pair_key in seen_pairs:
                continue
            score = max(
                jaccard(str(left.get("name") or ""), str(right.get("name") or "")),
                jaccard(str(left.get("description") or ""), str(right.get("description") or "")),
            )
            if score >= 0.42:
                seen_pairs.add(pair_key)
                candidates.append(
                    {
                        "skill_ids": [left_id, right_id],
                        "score": round(score, 3),
                        "reason": "name_or_description_overlap",
                    }
                )
    return sorted(candidates, key=lambda item: item["score"], reverse=True)
