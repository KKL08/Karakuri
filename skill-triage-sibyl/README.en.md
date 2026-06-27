# Skill Triage: Sibyl Scope

[中文](./README.md)

Description quality audit for Claude Code / Codex agents with many installed skills.

## What it solves

Install dozens of skills and the agent's routing accuracy noticeably drops:

- Two skills with similar descriptions — the agent guesses between them
- A skill's description over-promises capabilities the body can't deliver
- A skill's body can do more than the description advertises — the agent never sees the extra capability
- Skills installed but never used, sitting idle for months
- Descriptions too short or too vague — the agent forgets they exist

## Core features

- **Five-class semantic diagnosis**: the agent reads full descriptions and judges semantically — not by token overlap. Synonyms, length asymmetry, and namespace-prefix dilution that defeat lexical matching are caught by direct reading.
- **Two-layer filtering**: coarse scan picks candidates, deep read makes the judgement. Saves tokens without relying on a single pass.
- **Fixed four-part report structure**: each finding is presented as **judgement → evidence → recommended action → reason**. "Recommended action" and "reason" are bolded standalone lines — the two fields you actually act on, never buried in prose.
- **Cross-run preferences**: cleanup suggestions you've rejected don't come back. Preferences auto-expire when descriptions or body content change materially.
- **Fully reversible**: git snapshot plus content-hash check. Every archive / rewrite has a one-command rollback; conflicting files refuse to be overwritten by default, `--force` required to override.
- **Stdlib only**: Python standard library plus system git. No third-party packages.

## Install

```bash
# Claude Code
git clone https://github.com/KKL08/Karakuri.git
cp -r Karakuri/skill-triage-sibyl ~/.claude/skills/

# Codex
cp -r Karakuri/skill-triage-sibyl ~/.codex/skills/
```

Requires Python 3 stdlib + system git. No third-party packages.

## Use

Inside Claude Code or Codex:

```
audit my installed skills
```

Or directly:

```
use skill-triage-sibyl
```

## Name and inspiration

Named after the **Sibyl System** from *PSYCHO-PASS*. In the anime, the Sibyl System scans citizens' mental states and assigns tiered handling based on their Crime Coefficient. Sibyl Scope borrows the same paradigm — **scan → quantify → tiered action** — scanning every skill's description quality, diagnosing against five classes, and proposing archive / rewrite / keep.

Unlike the original: **you decide**. Sibyl Scope reports and proposes; every archive / rewrite requires your per-item confirmation, and every action is reversible.

## Workflow

After triggering, you go through these steps:

1. First run: confirm review mode and cadence
2. Automatic scan of all installed skills and 30-day call frequency
3. Review the diagnostic report; choose archive / rewrite / keep / defer per item
4. Confirm execution (archive moves the directory aside with a manifest; rewrite snapshots via git then overwrites)
5. Optional: set up a monthly scheduled run

Every step requires your confirmation — nothing executes without approval.

## Run the scripts directly

If you just want the raw facts:

```bash
SKILL_ROOT=~/.claude/skills/skill-triage-sibyl
RUN_DIR=~/sibyl-test/runs/$(date +%Y-%m-%d-%H%M%S)
mkdir -p $RUN_DIR

PYTHONPATH=$SKILL_ROOT/scripts python3 -m sibyl.inventory \
  --runtime claude-code --output $RUN_DIR/inventory.json

PYTHONPATH=$SKILL_ROOT/scripts python3 -m sibyl.usage \
  --runtime claude-code --inventory $RUN_DIR/inventory.json \
  --window-days 30 --output $RUN_DIR/usage.json
```

The JSON outputs are deterministic facts. Diagnostic recommendations require an agent to read and reason over them.

## Rollback

Any archive / rewrite executed during a run can be undone:

```bash
PYTHONPATH=$SKILL_ROOT/scripts python3 -m sibyl.apply rollback --run-id <run-id>
```

Rollback runs a content-hash consistency check. If you edited a file after the rewrite, the default behavior is to refuse the overwrite; pass `--force` to override.

## Data layout

```
$CLAUDE_PLUGIN_DATA/skill-triage-sibyl/         # defaults to ~/.claude/plugin-data/skill-triage-sibyl/
├── config.json                # onboarding mode + cadence
├── preferences.json           # accumulated user preferences across runs
├── runs/<run-id>/
│   ├── inventory.json
│   ├── usage.json
│   ├── report.md
│   └── actions.jsonl          # executed actions, read in reverse for rollback
├── keeper/repo/               # internal git repo: snapshots before rewrites
└── archive/<run-id>/<runtime>/<skill-name>/   # archived skill directories
```

## How preferences affect the next scan

Preferences influence whether a suggestion is raised again — they do not authorize execution. When descriptions or body content change materially, the corresponding preferences auto-expire and the next scan re-evaluates. Staleness rules vary by diagnosis type; see [`references/preference-merge.md`](./references/preference-merge.md) for details.

## Safety boundaries

- Plugin-managed skills get suggestions only, no direct archive/rewrite (avoid being overwritten by plugin updates)
- Project-scope skills trigger a "this affects your collaborators" prompt before changes
- Sibyl Scope skips itself during diagnosis — validate this skill via `tests/`
- User edits are respected by default — rollback refuses to overwrite when hashes don't match; `--force` to override

## Further reading

- [`SKILL.md`](./SKILL.md) — workflow the agent follows
- [`references/diagnosis-rubric.md`](./references/diagnosis-rubric.md) — the five diagnosis types
- [`references/preference-merge.md`](./references/preference-merge.md) — preference rules
- [`references/action-flow.md`](./references/action-flow.md) — wording and flow for each action
- [`references/rollback-model.md`](./references/rollback-model.md) — rollback semantics
