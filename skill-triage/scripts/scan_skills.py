#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path

from skilltriage.adapters.registry import choose_adapter
from skilltriage.capabilities import build_capability_groups
from skilltriage.constants import BACKUP_POLICIES
from skilltriage.filesystem import walk_skill_files
from skilltriage.identity import deduplicate_skill_ids
from skilltriage.models import SkillRoot
from skilltriage.preferences import PreferenceError, load_preference_hints
from skilltriage.screening import analyze_skill_file, build_similarity_candidates
from skilltriage.run_writer import write_run_artifacts


def _source_dict(runtime: str, root, index: int) -> dict[str, object]:
    return {
        "source_id": f"{runtime}-{root.source_type}-{index}",
        "source_type": root.source_type,
        "root": str(root.root),
        "writable": root.writable,
        "managed": root.managed,
        "coverage": root.coverage,
        "recursive": root.recursive,
    }


def _mark_duplicate_names(skills: list[dict[str, object]], checks: dict[str, object]) -> None:
    by_name: dict[str, list[dict[str, object]]] = {}
    for skill in skills:
        by_name.setdefault(str(skill["name"]), []).append(skill)
    for group in by_name.values():
        if len(group) < 2:
            continue
        hashes = {str(skill["hash"]) for skill in group}
        if len(hashes) < 2:
            continue
        for skill in group:
            skill_id = str(skill["skill_id"])
            checks.setdefault(skill_id, {})["duplicate_across_roots"] = True
            if not skill.get("is_self") and skill.get("writable") and not skill.get("managed"):
                skill["candidate_for_agent_evaluation"] = True


def _add_plugin_coverage_note(adapter, roots, skills: list[dict[str, object]]) -> None:
    has_plugin_root = any(root.source_type == "plugin-managed" for root in roots)
    has_plugin_skill = any(skill.get("source_type") == "plugin-managed" for skill in skills)
    if has_plugin_root and not has_plugin_skill:
        adapter.coverage_notes.append("未发现 plugin-managed skill 文件；插件覆盖范围可能不完整。")


def _selected_skill_ids(skills: list[dict[str, object]], selected: list[str]) -> tuple[list[str], list[str]]:
    selected_set = set(selected)
    matched: list[str] = []
    unmatched = sorted(selected_set)
    for skill in skills:
        if skill.get("is_self"):
            continue
        names = {
            str(skill.get("skill_id") or ""),
            str(skill.get("name") or ""),
            Path(str(skill.get("skill_dir") or "")).name,
        }
        if selected_set.intersection(names):
            matched.append(str(skill["skill_id"]))
            unmatched = [value for value in unmatched if value not in names]
    return sorted(set(matched)), unmatched


def _agent_evaluation_skill_ids(
    skills: list[dict[str, object]],
    *,
    evaluation_scope: str,
    selected: list[str],
) -> tuple[list[str], list[str]]:
    selected_ids, unmatched = _selected_skill_ids(skills, selected)
    if evaluation_scope == "full":
        ids = [str(skill["skill_id"]) for skill in skills if not skill.get("is_self")]
        return sorted(set(ids + selected_ids)), unmatched
    if evaluation_scope == "selected":
        return selected_ids, unmatched
    ids = [str(skill["skill_id"]) for skill in skills if skill.get("candidate_for_agent_evaluation") and not skill.get("is_self")]
    return sorted(set(ids + selected_ids)), unmatched


def _load_preference_hints(runtime: str) -> list[dict[str, object]]:
    try:
        return load_preference_hints(runtime)
    except (PreferenceError, OSError, json.JSONDecodeError) as exc:
        print(f"Preference hints unavailable: {exc}", file=sys.stderr)
        return []


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Scan current agent skill space for SkillTriage.")
    parser.add_argument("--runtime", choices=("codex", "claude-code"))
    parser.add_argument("--skill-root", action="append", default=[])
    parser.add_argument("--output-root")
    parser.add_argument("--backup", choices=BACKUP_POLICIES, default="targeted")
    parser.add_argument("--evaluation-scope", choices=("quick", "full", "selected"), default="quick")
    parser.add_argument("--select-skill", action="append", default=[])
    parser.add_argument("--run-id")
    parser.add_argument("--dry-detect-only", action="store_true")
    args = parser.parse_args(argv)

    if args.evaluation_scope == "selected" and not args.select_skill:
        print("--evaluation-scope selected requires at least one --select-skill value.", file=sys.stderr)
        return 2

    project_dir = Path.cwd()
    adapter, message = choose_adapter(args.runtime, project_dir)
    if adapter is None:
        print(message, file=sys.stderr)
        return 2
    if args.dry_detect_only:
        print(adapter.runtime_id)
        return 0

    roots = adapter.skill_roots()
    if args.skill_root:
        roots = [SkillRoot(root=Path(path), source_type="user", writable=True, managed=False) for path in args.skill_root]

    skills: list[dict[str, object]] = []
    skill_checks: list[tuple[dict[str, object], dict[str, object]]] = []
    source_entries = [_source_dict(adapter.runtime_id, root, index) for index, root in enumerate(roots)]
    for root, source_entry in zip(roots, source_entries):
        for skill_file in walk_skill_files(root.root, recursive=root.recursive):
            if args.skill_root:
                source_info = {"source_type": root.source_type, "writable": root.writable, "managed": root.managed}
            else:
                source_info = adapter.classify_source(skill_file)
            source_info["source_id"] = source_entry["source_id"]
            is_self = adapter.is_self_skill(skill_file)
            item, item_checks = analyze_skill_file(skill_file, adapter.runtime_id, source_info, is_self=is_self)
            item["source_root"] = str(root.root)
            item["active_state"] = adapter.active_state(skill_file)
            skills.append(item)
            skill_checks.append((item, item_checks))

    deduplicate_skill_ids(skills)
    checks: dict[str, object] = {str(item["skill_id"]): item_checks for item, item_checks in skill_checks}

    _mark_duplicate_names(skills, checks)
    _add_plugin_coverage_note(adapter, roots, skills)

    similarity_candidates = build_similarity_candidates(skills)
    for candidate in similarity_candidates:
        for skill in skills:
            if skill["skill_id"] in candidate["skill_ids"] and not skill.get("is_self"):
                skill["candidate_for_agent_evaluation"] = True

    capability_groups = build_capability_groups(skills)
    for group in capability_groups:
        if group.get("status") == "too_broad":
            continue
        for skill in skills:
            if skill["skill_id"] in group["skill_ids"] and not skill.get("is_self"):
                skill["candidate_for_agent_evaluation"] = True

    agent_evaluation_skill_ids, unmatched_selected = _agent_evaluation_skill_ids(
        skills,
        evaluation_scope=args.evaluation_scope,
        selected=args.select_skill,
    )
    if unmatched_selected:
        print("Selected skills were not found: " + ", ".join(unmatched_selected), file=sys.stderr)
        return 2

    run_id = args.run_id or datetime.now().strftime("%Y-%m-%d-%H%M%S")
    output_base = Path(args.output_root).expanduser() if args.output_root else adapter.default_output_dir().parent
    run_dir = output_base / adapter.runtime_id / run_id
    preference_hints = _load_preference_hints(adapter.runtime_id)
    write_run_artifacts(
        run_dir=run_dir,
        runtime=adapter.runtime_id,
        run_id=run_id,
        backup_policy=args.backup,
        skill_roots=source_entries,
        skills=skills,
        checks=checks,
        similarity_candidates=similarity_candidates,
        coverage_notes=adapter.coverage_notes,
        evaluation_scope=args.evaluation_scope,
        selected_skills=args.select_skill,
        agent_evaluation_skill_ids=agent_evaluation_skill_ids,
        capability_groups=capability_groups,
        preference_hints=preference_hints,
    )
    print(str(run_dir))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
