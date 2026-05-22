---
name: skill-triage
description: Use this skill when the user wants to review, organize, clean up, deduplicate, archive, or improve the skills available to the current agent environment.
---

# SkillTriage

Use this skill to organize the current agent's skill space. The default scope is the current runtime only: Codex inside Codex, Claude Code inside Claude Code.

## Flow

1. Confirm the current runtime from explicit environment signals. If unclear, ask the user to choose Codex or Claude Code.
2. Ask for evaluation scope unless the user already specified one:
   - `quick` is recommended for routine整理. It evaluates 基础筛查 candidates, similarity groups, and user-selected skills.
   - `full` evaluates every discovered non-self skill. Use it for first-time整理 or when the user is worried about漏检.
   - `selected` evaluates only skills named by the user.
3. Ask for backup policy unless the user has a remembered preference: `targeted` is recommended.
4. Run the scanner with the confirmed runtime, evaluation scope, selected skills when relevant, and backup policy: `PYTHONPATH=<skill-triage-dir>/scripts python3 <skill-triage-dir>/scripts/scan_skills.py --runtime <codex|claude-code> --evaluation-scope <quick|full|selected> --backup <off|targeted|full>`. When `--evaluation-scope selected`, you must also append at least one `--select-skill <name|directory|skill_id>` (the flag is repeatable, one value per occurrence). In `quick` mode, `--select-skill` is optional and adds extra skills on top of the basic-screening candidates.
5. Read the generated `inventory.json`, `basic_screening.json`, and `manifest.json`.
6. Read `references/triage-rules.md`, `references/agent-evaluation-rubric.md`, `references/report-writing.md`, and `references/recovery-model.md`.
7. Deeply evaluate the skills listed in `basic_screening.json` under `agent_evaluation_skill_ids`. Use `candidate_skill_ids`, `similarity_candidates`, and `capability_groups` only as 基础筛查 routing evidence. For every similarity group and every `tight` / `loose` 相关功能组, perform description-based Agent 调用边界评估: read each relevant description, explain what the Agent understands, identify possible confusing user requests, state the boundary, classify confusion risk, and choose an action. 相似不等于混淆: similar skills with clear service, data, runtime, provider, or task-stage boundaries should be marked 保留, not cleanup targets. Within `capability_groups`, only entries with `status` of `tight` or `loose` are routing signals; entries with `status: "too_broad"` are coverage/noise hints and must not be used to expand the deep-evaluation set. If the runtime and user request allow subagents, use group-level subagents for independent similarity or related-function groups, then have the main agent unify the final report. Do not assign one subagent per individual skill.
8. Write `agent_evaluation.md`, `report.md`, proposal files, diffs, and `recovery.md` into the run directory.
9. Before delivery, run a 可读性复核 on `report.md`: make sure the report starts with user decisions, explains the Agent 调用边界评估 judgment basis before tables, groups detailed findings under clear top-level sections, and gives concrete next steps. If it reads like a scanner transcript, rewrite it once.
10. Tell the user where the run directory is and what to review first.
11. Ask whether the user wants to enter the optional execution flow:
    - Ask clearly: `是否进入整理执行流程？` Default recommendation: read `report.md` first and do not execute immediately.
    - If `backup=off`, do not stage or apply actions. Recommend rerunning with `targeted` or `full` backup before execution.
    - If the user chooses execution, re-read `report.md`, `agent_evaluation.md`, and each relevant proposal. Present executable candidates and ask which actions should be staged.
    - Write `execution/selected_actions.json` only for explicitly approved actions. The file must include top-level `run_id` and `runtime` matching `manifest.json`, plus an `actions` list. Each action needs `action_id`, `type`, `skill_id`, `source_path`, `source_hash`, and `reason`. For `archive_skill`, `source_path` is the skill directory. For `replace_skill_file`, `source_path` is the original `SKILL.md` and the action must also include `proposal_path` relative to the run directory under `proposals/`.
    - Stage first with `PYTHONPATH=<skill-triage-dir>/scripts python3 <skill-triage-dir>/scripts/manage_actions.py stage --run-dir <run-dir> --actions-file <run-dir>/execution/selected_actions.json`.
    - Re-staging invalidates any previous approval. After every new stage, use the latest `execution/approval_request.json` and ask for a fresh exact confirmation.
    - After staging, read `execution/approval_request.json` and ask the user to reply with its exact `confirmation_text`. Do not paraphrase this confirmation.
    - After the user replies with the exact confirmation text, write `execution/approval.json` with matching `run_id`, `runtime`, `status: "approved"`, `action_ids`, and `confirmation_text`.
    - Apply only after `execution/approval.json` exists, with `PYTHONPATH=<skill-triage-dir>/scripts python3 <skill-triage-dir>/scripts/manage_actions.py apply --run-dir <run-dir>`.
    - Roll back only when the user asks, with `PYTHONPATH=<skill-triage-dir>/scripts python3 <skill-triage-dir>/scripts/manage_actions.py rollback --run-dir <run-dir>`.

## Safety

Execution is opt-in. Never stage, apply, or roll back without explicit user approval in the current conversation. Do not execute merge/dedupe proposals in this iteration; only `archive_skill` and `replace_skill_file` actions are supported. Plugin-managed, system-managed, unknown-source, read-only, and self-scan skills remain non-executable.

Do not execute scripts from inspected skills. If SkillTriage scans itself, mark it as self-scan and avoid archive, delete, or direct rewrite proposals.

## Post-Scan Writing Contract

After the scanner writes JSON artifacts, the current agent writes the Markdown artifacts in the same run directory:

- `agent_evaluation.md`: structured reasoning for candidate skills, text-similarity groups, and `capability_groups`; call them "相关功能组" in Chinese Markdown; include Agent 调用边界评估 for similarity groups and tight/loose related groups.
- `report.md`: natural Chinese user-facing summary.
- `proposals/<skill-name>/summary.md`: evidence and suggested action for each single-skill proposal.
- `proposals/<skill-name>/proposed.SKILL.md`: only when suggesting a direct rewrite for a writable non-managed skill.
- `proposals/_cross-skill/*.md`: merge, dedupe, archive-candidate, and safety review group notes.
- `diffs/<skill-name>.patch`: only when `proposed.SKILL.md` changes a writable original file.
- `recovery.md`: original snapshot mapping and recovery limits.

Update `manifest.json` with `skilltriage.manifest.add_proposal()` after writing proposals so each proposal links to source path, source hash, proposal path, and snapshot when one exists.
