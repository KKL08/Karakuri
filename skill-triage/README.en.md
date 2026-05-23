# SkillTriage

[中文版](./README.md)

SkillTriage helps an agent review the skills installed in its current runtime. It does a lightweight script-based scan first, then asks the current agent to write a human-readable review of duplicates, similar descriptions, and places where skill invocation boundaries may be unclear.

It is designed for skill library maintenance: keeping a smaller, clearer set of skills without letting a script silently delete or rewrite anything. When a choice depends on personal workflow, SkillTriage can ask the user to decide instead of forcing a weak cleanup conclusion.

## What It Does

- Scans the current runtime's skills and records a factual inventory.
- Flags exact duplicates, suspiciously short or broad descriptions, script presence, plugin-managed skills, and related-function groups.
- Routes likely candidates into Agent evaluation so the agent can read descriptions and compare boundaries in context.
- Produces reviewable Markdown reports, proposals, and recovery notes.
- Stops at reports and recommendations by default; it does not change installed skills on its own.
- If you choose to clean up, the agent must ask you to approve specific items first.
- Turns confirmed cleanup decisions into preference-memory drafts, then writes them only after user confirmation.
- Uses confirmed preferences as hints in later reports, so diagnostics and cleanup advice can better match the user over time.
- Before any write, SkillTriage prepares backups and asks for explicit confirmation. Applied changes can be rolled back from the run artifacts.

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
- `decisions/`: user-dependent decisions, the user's current choices, and preference-memory drafts waiting for confirmation.

## Preference Memory

Some cleanup choices cannot be decided from similarity alone. For example, one skill may be a broad entry point while another is a fixed workflow; both can be useful, and the better choice depends on how the user works. SkillTriage puts these cases under `需要你决定`, explains the trade-off, and lets the user choose.

When the user chooses to continue with cleanup decisions, SkillTriage can turn those choices into preference-memory drafts. After confirmation, future reports use those preferences as hints, making diagnostics and cleanup advice better match the user's habits over time. Preferences only affect hints and ordering; they never clean up skills automatically.

## Optional Cleanup

In normal use, SkillTriage stops at a review report. It helps you see which skills are worth keeping, which ones may be duplicates, and which descriptions could confuse the agent.

If you explicitly ask the agent to continue, SkillTriage can guide a small cleanup flow for items you approve one by one. Today, executable actions are limited to archiving a writable skill or replacing a writable `SKILL.md` with a prepared proposal.

The first step only prepares backups and the selected actions; it does not modify installed skills. Before anything is applied, the agent must ask you to repeat an exact confirmation phrase. That confirmation is valid only for the current prepared set, so preparing a new set invalidates the old confirmation.

After changes are applied, the run directory keeps recovery artifacts. You can ask the agent to roll back an applied action; rollback still checks paths and file hashes, so it stops if files changed after the original action.

## Safety

Plugin-managed, system-managed, read-only, unknown-source, and SkillTriage's own files are not executable cleanup targets. Merge and dedupe suggestions remain report-only and are not automatically executed. Preference memory is not execution approval and cannot bypass backup, confirmation, or recovery checks.
