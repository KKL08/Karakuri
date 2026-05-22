# SkillTriage

[中文版](./README.md)

SkillTriage helps an agent review the skills installed in its current runtime. It does a lightweight script-based scan first, then asks the current agent to write a human-readable review of duplicates, similar descriptions, and places where skill invocation boundaries may be unclear.

It is designed for skill library maintenance: keeping a smaller, clearer set of skills without letting a script silently delete or rewrite anything.

## What It Does

- Scans the current runtime's skills and records a factual inventory.
- Flags exact duplicates, suspiciously short or broad descriptions, script presence, plugin-managed skills, and related-function groups.
- Routes likely candidates into Agent evaluation so the agent can read descriptions and compare boundaries in context.
- Produces reviewable Markdown reports, proposals, and recovery notes.
- Leaves installed skills unchanged by default; executable cleanup actions require the user to explicitly enter the execution flow and approve each staged action.
- Creates backups and a confirmation phrase before apply; applied actions can be rolled back from the run's recovery artifacts.

## Supported Runtimes

Version 1 supports these current-runtime flows:

- Codex: scans the Codex skill directories visible to the current Codex environment.
- Claude Code: scans the Claude Code skill and plugin layouts visible to Claude Code.

The same SkillTriage folder is used in both environments. Each runtime runs SkillTriage against its own active skill space.

## Install

From this repository:

```bash
git clone https://github.com/KKL08/Skill.git

# Codex
mkdir -p ~/.codex/skills
cp -r Skill/skill-triage ~/.codex/skills/

# Claude Code
mkdir -p ~/.claude/skills
cp -r Skill/skill-triage ~/.claude/skills/
```

Restart or reload the target agent if it does not hot-load newly copied skills.

## Use

Ask the agent to run SkillTriage, for example:

```text
Use skill-triage to review my installed skills.
```

The skill will ask for two choices when they are not already clear:

- Evaluation scope: `quick`, `full`, or `selected`.
- Backup policy: `off`, `targeted`, or `full`.

Recommended first run: `full` evaluation with `targeted` backup. Recommended routine run: `quick` evaluation with `targeted` backup.

## Direct Scanner Command

Codex quick scan:

```bash
PYTHONPATH=~/.codex/skills/skill-triage/scripts \
python3 ~/.codex/skills/skill-triage/scripts/scan_skills.py \
  --runtime codex \
  --evaluation-scope quick \
  --backup targeted
```

Claude Code quick scan:

```bash
PYTHONPATH=~/.claude/skills/skill-triage/scripts \
python3 ~/.claude/skills/skill-triage/scripts/scan_skills.py \
  --runtime claude-code \
  --evaluation-scope quick \
  --backup targeted
```

Direct scanner output is not the final recommendation. The scanner creates factual inputs for Agent evaluation; the user-facing cleanup decision should come from the final Agent-written report.

## Output

Run artifacts are written under:

```text
~/.skilltriage/runs/<runtime>/<run-id>/
```

Important files:

- `inventory.json`: factual inventory of discovered skills.
- `basic_screening.json`: script-based screening and routing evidence.
- `agent_evaluation.md`: the agent's detailed comparison and boundary reasoning.
- `report.md`: the main user-facing report to read first.
- `recovery.md`: what was backed up and how recovery would work if future cleanup actions are taken.

## Optional Execution Flow

SkillTriage generates review materials by default. It does not automatically delete, archive, overwrite, or rewrite installed skills.

If the user explicitly chooses the execution flow, the current agent presents executable candidates first and writes only user-approved actions to `execution/selected_actions.json`. Execution then happens in three steps:

1. `stage`: prepare backups and staged actions without modifying installed skills.
2. The user replies with the exact confirmation phrase from `execution/approval_request.json`.
3. `apply`: execute only when `approval.json` exactly matches the current staged actions.

Re-staging invalidates any previous approval, so stale approvals cannot be reused. After apply, the user can ask the agent to run rollback; rollback still checks paths, hashes, and recovery artifacts before restoring files.

## Safety

Plugin-managed and system-managed skills are treated as read-only. Merge and dedupe proposals remain review-only and are not automatically executed.
